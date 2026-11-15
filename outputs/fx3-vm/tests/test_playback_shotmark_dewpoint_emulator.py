#!/usr/bin/env python3
"""Phase 87 Test Suite — Stage 13 Playback/Thumbnail Shuttle, `ShotMark1/2`
`<EssenceMark>` Sync, `Cine EI` `Push Auto Iris` & Dew-Point/PMIC `5V` HIL.

Exercises 36 fast unit, Playback/ShotMark/eMMC p1 isolation, 1/8-stop MHLX
Push Auto Iris S-Log3 convergence, Magnus-Tetens dewpoint TEC / PMIC 5V HIL,
Stage 13 suite integration, CLI, and source-hygiene tests across BOTH Local
Donor (`os.O_RDONLY`) and `FX3_FX6_FORCE_CLEAN_ROOM=1` modes, strictly offline.
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import contextlib
import hashlib
import io
import json
import os
import subprocess
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
FX3_VM_DIR = TESTS_DIR.parent
REPO_ROOT = FX3_VM_DIR.parents[1]
if str(FX3_VM_DIR) not in sys.path:
    sys.path.insert(0, str(FX3_VM_DIR))

import fx3_vm_coemulation_suite as suite  # noqa: E402
import playback_shotmark_dewpoint_emulator as p87  # noqa: E402


_AUDIT_CACHE: dict = {}


def _get_clean_room_audit() -> dict:
    if "clean_room" not in _AUDIT_CACHE:
        _AUDIT_CACHE["clean_room"] = p87.run_phase87_playback_shotmark_dewpoint_audit(force_clean_room=True)
    return _AUDIT_CACHE["clean_room"]


class TestPhase87DonorAuditAndRedlines(unittest.TestCase):
    """Verify O_RDONLY donor audit, clean-room fallback, and zero-mutation redlines."""

    def test_01_clean_room_donor_audit_verifies_all_10_artifacts_and_sha256(self) -> None:
        audit = p87.inspect_playback_shotmark_dewpoint_donors(force_clean_room=True)
        self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(audit.access_mode, "O_RDONLY")
        self.assertEqual(audit.donor_files_inspected, 0)
        self.assertTrue(audit.all_contracts_verified)
        self.assertEqual(len(audit.checked_markers), 10)
        self.assertEqual(audit.missing_markers, ())
        for key, (expected_bytes, expected_sha) in p87.PINNED_DONOR_SHA256.items():
            self.assertEqual(audit.bytes_by_artifact[key], expected_bytes)
            self.assertEqual(audit.sha256_by_artifact[key], expected_sha)

    def test_02_force_clean_room_env_disables_local_donor_paths(self) -> None:
        env = {p87.ENV_FORCE_CLEAN_ROOM: "1"}
        self.assertTrue(p87.is_forced_clean_room(env))
        paths = p87.resolve_phase87_donor_paths(env=env)
        self.assertEqual(len(paths), 10)
        for path in paths.values():
            self.assertIn(p87.CLEAN_ROOM_SENTINEL_DIRNAME, str(path))
        audit = p87.inspect_playback_shotmark_dewpoint_donors(env=env)
        self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_03_local_donor_o_rdonly_audit_when_present_or_clean_room(self) -> None:
        if p87.is_forced_clean_room():
            audit = p87.inspect_playback_shotmark_dewpoint_donors()
            self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")
            return
        paths = p87.resolve_phase87_donor_paths()
        audit = p87.inspect_playback_shotmark_dewpoint_donors()
        self.assertTrue(audit.all_contracts_verified)
        if all(p.is_file() for p in paths.values()):
            self.assertEqual(audit.source_mode, "LOCAL_DONOR_RDONLY")
            self.assertEqual(audit.donor_files_inspected, 10)
            for key, (expected_bytes, expected_sha) in p87.PINNED_DONOR_SHA256.items():
                self.assertEqual(audit.bytes_by_artifact[key], expected_bytes)
                self.assertEqual(audit.sha256_by_artifact[key], expected_sha)
        else:
            self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_04_missing_donor_root_falls_back_to_clean_room(self) -> None:
        env = {
            p87.ENV_MAC_WORK_ROOT: "/nonexistent_phase87_mac_work_root",
            p87.ENV_MAIN_LAB_WORK_ROOT: "/nonexistent_phase87_main_work_root",
        }
        audit = p87.inspect_playback_shotmark_dewpoint_donors(force_clean_room=True, env=env)
        self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(audit.all_contracts_verified)

    def test_05_redlines_zero_mutations_p1_emmc_blocked_and_zero_nd_faults(self) -> None:
        rep = _get_clean_room_audit()
        red = rep["redlines"]
        self.assertTrue(red["p8_cp_mutation_forbidden"])
        self.assertEqual(red["nop_count"], 0)
        self.assertEqual(red["guest_code_modification_bytes"], 0)
        self.assertEqual(red["cp_mutation_bytes"], 0)
        self.assertEqual(red["wbi_mutation_bytes"], 0)
        self.assertEqual(red["calibration_mutation_bytes"], 0)
        self.assertEqual(red["nvram_persistent_writes"], 0)
        self.assertEqual(red["bk4_persistent_nvram_writes"], 0)
        self.assertEqual(red["physical_device_writes"], 0)
        self.assertFalse(red["persistent_emmc_writes_authorized"])
        self.assertTrue(red["internal_emmc_format_blocked"])
        self.assertEqual(red["internal_emmc_writes"], 0)
        self.assertEqual(red["p1_emmc_mutations"], 0)
        self.assertTrue(red["c2pa_license_untouched"])
        self.assertEqual(red["p4_nd_motor_faults"], 0)
        self.assertEqual(red["null_gpio_derefs"], 0)
        self.assertEqual(red["mailbox_stalls"], 0)
        self.assertEqual(red["donor_access_mode"], "O_RDONLY")


class TestPlaybackShuttleShotmarkAndEmmcIsolation(unittest.TestCase):
    """Verify Thumbnail/Playback shuttle, ShotMark1/2 <EssenceMark> XML sync & p1 eMMC blocks."""

    def test_06_clip_catalog_indexes_8_clips_across_slot_a_and_slot_b(self) -> None:
        sess = p87.PlaybackShotmarkMediaSession()
        self.assertEqual(len(sess.clips), 8)
        self.assertEqual(tuple(sorted(sess.clips.keys())), tuple(f"A001C{i:03d}" for i in range(1, 9)))
        self.assertTrue(sess.clips["A001C002"].clip_protected)
        self.assertTrue(sess.clips["A001C006"].clip_protected)
        self.assertFalse(sess.clips["A001C001"].clip_protected)
        self.assertEqual(sess.clips["A001C001"].slot_name, "Slot A")
        self.assertEqual(sess.clips["A001C005"].slot_name, "Slot B")

    def test_07_mode_switching_shooting_thumbnail_playback_transitions(self) -> None:
        sess = p87.PlaybackShotmarkMediaSession()
        self.assertEqual(sess.camera_mode, p87.MODE_SHOOTING_LIVE_VIEW)
        sess.switch_mode(p87.MODE_THUMBNAIL_INDEX, clip_id="A001C003")
        self.assertEqual(sess.camera_mode, p87.MODE_THUMBNAIL_INDEX)
        self.assertEqual(sess.active_clip_id, "A001C003")
        sess.switch_mode(p87.MODE_PLAYBACK_SHUTTLE, clip_id="A001C003")
        self.assertEqual(sess.camera_mode, p87.MODE_PLAYBACK_SHUTTLE)
        sess.switch_mode(p87.MODE_SHOOTING_LIVE_VIEW)
        self.assertEqual(sess.camera_mode, p87.MODE_SHOOTING_LIVE_VIEW)

    def test_08_playback_shuttle_1x_2x_5x_15x_fwd_and_rev_clamp_cleanly(self) -> None:
        sess = p87.PlaybackShotmarkMediaSession()
        sess.switch_mode(p87.MODE_PLAYBACK_SHUTTLE, clip_id="A001C001")
        for spd in (1, 2, 5, 15):
            prev = sess.current_frame
            cur = sess.shuttle_step(spd, steps=2)
            self.assertGreater(cur, prev)
        for spd in (-1, -2, -5, -15):
            prev = sess.current_frame
            cur = sess.shuttle_step(spd, steps=2)
            self.assertLessEqual(cur, prev)
        # Rewind to start clamp = 0
        sess.shuttle_step(-15, steps=50)
        self.assertEqual(sess.current_frame, 0)
        # Forward to end clamp = duration - 1
        sess.shuttle_step(15, steps=50)
        self.assertEqual(sess.current_frame, 479)

    def test_09_invalid_shuttle_mode_or_speed_raises_error(self) -> None:
        sess = p87.PlaybackShotmarkMediaSession()
        with self.assertRaises(p87.PlaybackShotmarkDewpointError):
            sess.shuttle_step(2)  # Still in SHOOTING_LIVE_VIEW
        sess.switch_mode(p87.MODE_PLAYBACK_SHUTTLE)
        with self.assertRaises(p87.PlaybackShotmarkDewpointError):
            sess.shuttle_step(32)  # Unsupported shuttle speed
        with self.assertRaises(p87.PlaybackShotmarkDewpointError):
            sess.switch_mode("INVALID_MODE")

    def test_10_punch_shotmark1_ok_and_shotmark2_keep_in_rec_and_playback(self) -> None:
        sess = p87.PlaybackShotmarkMediaSession()
        m1 = sess.punch_shotmark(p87.SHOTMARK1_NAME, clip_id="A001C001", frame_count=12)
        self.assertEqual(m1.mark_name, "ShotMark1")
        self.assertEqual(m1.status_label, "OK")
        self.assertEqual(m1.source_mode, "REC")

        sess.switch_mode(p87.MODE_PLAYBACK_SHUTTLE, clip_id="A001C001")
        sess.shuttle_step(5, steps=4)
        m2 = sess.punch_shotmark(p87.SHOTMARK2_NAME)
        self.assertEqual(m2.mark_name, "ShotMark2")
        self.assertEqual(m2.status_label, "KEEP")
        self.assertEqual(m2.source_mode, "PLAYBACK_SHUTTLE")
        self.assertEqual(m2.shuttle_speed, 5)
        self.assertEqual(m2.frame_count, 40)

    def test_11_shotmark_blocked_in_thumbnail_mode_and_invalid_mark_rejected(self) -> None:
        sess = p87.PlaybackShotmarkMediaSession()
        sess.switch_mode(p87.MODE_THUMBNAIL_INDEX)
        with self.assertRaises(p87.PlaybackShotmarkDewpointError):
            sess.punch_shotmark(p87.SHOTMARK1_NAME)
        sess.switch_mode(p87.MODE_SHOOTING_LIVE_VIEW)
        with self.assertRaises(p87.PlaybackShotmarkDewpointError):
            sess.punch_shotmark("ShotMark9")

    def test_12_essencemark_xml_roundtrip_100pct_sync_into_nonrealtimemeta(self) -> None:
        res = p87.simulate_playback_shuttle_shotmark_and_emmc_isolation()
        self.assertTrue(res.passed)
        self.assertTrue(res.xml_roundtrip_ok)
        self.assertEqual(res.xml_consistency_pct, 100.0)
        self.assertEqual(res.shotmarks_punched_total, 4)
        self.assertEqual(res.shotmarks_in_rec, 2)
        self.assertEqual(res.shotmarks_in_playback, 2)
        self.assertEqual(res.xml_filename, "A001C001_261114_FX3VM01.XML")

    def test_13_essencemark_xml_contains_exact_tags_and_attributes(self) -> None:
        sess = p87.PlaybackShotmarkMediaSession()
        sess.punch_shotmark(p87.SHOTMARK1_NAME, clip_id="A001C004", frame_count=48)
        sess.switch_mode(p87.MODE_PLAYBACK_SHUTTLE, clip_id="A001C004")
        sess.shuttle_step(15, steps=2)
        sess.punch_shotmark(p87.SHOTMARK2_NAME)
        sync = sess.build_and_verify_essencemark_xml("A001C004")
        self.assertTrue(sync.passed)
        self.assertEqual(sync.essence_mark_count, 2)
        self.assertEqual(sync.roundtrip_matched_count, 2)
        self.assertIn("<EssenceMarkTable>", sync.xml_text)
        self.assertIn('name="ShotMark1" value="OK"', sync.xml_text)
        self.assertIn('name="ShotMark2" value="KEEP"', sync.xml_text)

    def test_14_delete_protected_clip_blocked_fail_closed(self) -> None:
        sess = p87.PlaybackShotmarkMediaSession()
        for cid in ("A001C002", "A001C006"):
            verdict = sess.request_delete_clip(cid)
            self.assertFalse(verdict.allowed)
            self.assertEqual(verdict.status, "BLOCKED_CLIP_PROTECTED")
            self.assertTrue(verdict.clip_protected)
            self.assertTrue(verdict.clip_intact)
            self.assertFalse(sess.clips[cid].deleted_in_shadow)
            self.assertEqual(verdict.physical_device_writes, 0)

    def test_15_delete_unprotected_clip_shadow_only_zero_physical_writes(self) -> None:
        sess = p87.PlaybackShotmarkMediaSession()
        verdict = sess.request_delete_clip("A001C001")
        self.assertTrue(verdict.allowed)
        self.assertEqual(verdict.status, "ALLOWED_VOLATILE_SHADOW_DELETE")
        self.assertTrue(sess.clips["A001C001"].deleted_in_shadow)
        self.assertTrue(verdict.internal_emmc_format_blocked)
        self.assertFalse(verdict.persistent_emmc_writes_authorized)
        self.assertEqual(verdict.physical_device_writes, 0)

    def test_16_format_media_internal_emmc_p1_100pct_blocked_fail_closed(self) -> None:
        sess = p87.PlaybackShotmarkMediaSession()
        for target in (
            "/dev/mmcblk0p1",
            "/dev/mmcblk0",
            "mmcblk0p1",
            "p1",
            "/dev/nflasha15",
            "/dev/cnflasha0",
            "internal_emmc_p1",
        ):
            verdict = sess.request_format_media(target)
            self.assertFalse(verdict.allowed, msg=f"Format target {target} must be blocked")
            self.assertEqual(verdict.status, "BLOCKED_INTERNAL_EMMC_P1_ISOLATED")
            self.assertTrue(verdict.internal_emmc_format_blocked)
            self.assertFalse(verdict.persistent_emmc_writes_authorized)
            self.assertEqual(verdict.p1_emmc_mutations, 0)
            self.assertEqual(verdict.internal_emmc_writes, 0)
            self.assertTrue(verdict.c2pa_license_untouched)
            self.assertEqual(verdict.physical_device_writes, 0)

    def test_17_format_slot_with_protected_clips_blocked_until_unprotected(self) -> None:
        sess = p87.PlaybackShotmarkMediaSession()
        verdict_blocked = sess.request_format_media("Slot A")
        self.assertFalse(verdict_blocked.allowed)
        self.assertEqual(verdict_blocked.status, "BLOCKED_SLOT_CONTAINS_PROTECTED_CLIPS")
        # Clear protection in volatile shadow & re-test removable slot format
        sess.clips["A001C002"].clip_protected = False
        verdict_ok = sess.request_format_media("Slot A")
        self.assertTrue(verdict_ok.allowed)
        self.assertEqual(verdict_ok.status, "ALLOWED_VOLATILE_REMOVABLE_SLOT_FORMAT")
        self.assertTrue(verdict_ok.internal_emmc_format_blocked)
        self.assertEqual(verdict_ok.physical_device_writes, 0)


class TestCineEiPushAutoIrisAndMhlxServo(unittest.TestCase):
    """Verify 1/8-stop MHLX Push Auto Iris convergence to 41.0% / <94.0% IRE without P4 ND faults."""

    def test_18_slog3_18pct_grey_and_t_stop_eighth_step_math(self) -> None:
        self.assertAlmostEqual(p87.slog3_ire_from_linear(0.18), 41.02, places=2)
        self.assertEqual(p87.t_stop_from_eighth_steps(0), 1.4)
        self.assertEqual(p87.t_stop_from_eighth_steps(28), 4.8)

    def test_19_push_auto_iris_plus_3_5_ev_converges_t14_to_t48_at_41pct_ire(self) -> None:
        res = p87.simulate_cine_ei_push_auto_iris(
            base_iso=800,
            shutter_angle_deg=180.0,
            initial_eighth_steps=0,
            scene_ev_shift=3.5,
            metering_mode=p87.METERING_MULTI_GREY_CARD,
        )
        self.assertTrue(res.passed)
        self.assertTrue(res.converged_to_target)
        self.assertEqual(res.initial_t_stop, 1.4)
        self.assertEqual(res.final_t_stop, 4.8)
        self.assertEqual(res.eighth_stop_steps_moved, 28)
        self.assertEqual(res.mhlx_packets_sent, 28)
        self.assertLessEqual(abs(res.final_grey_ire_pct - 41.0), 0.15)
        self.assertEqual(res.cine_ei_base_iso_locked, 800)
        self.assertEqual(res.shutter_angle_locked_deg, 180.0)

    def test_20_push_auto_iris_zero_p4_nd_motor_calls_and_faults(self) -> None:
        res = p87.simulate_cine_ei_push_auto_iris(metering_mode=p87.METERING_MULTI_GREY_CARD)
        self.assertEqual(res.p4_nd_state, "Clear")
        self.assertEqual(res.p4_nd_motor_calls, 0)
        self.assertEqual(res.p4_nd_motor_faults, 0)
        self.assertEqual(res.cp_mutation_bytes, 0)

    def test_21_highlight_metering_mode_keeps_peak_specular_below_94_ire(self) -> None:
        res = p87.simulate_cine_ei_push_auto_iris(
            base_iso=800,
            shutter_angle_deg=180.0,
            initial_eighth_steps=0,
            scene_ev_shift=3.5,
            metering_mode=p87.METERING_HIGHLIGHT_GUARD,
            specular_over_grey_ev=7.0,
        )
        self.assertTrue(res.passed)
        self.assertTrue(res.converged_to_target)
        self.assertGreater(res.initial_highlight_ire_pct, 94.0)
        self.assertLess(res.final_highlight_ire_pct, 94.0)
        self.assertGreater(res.final_highlight_ire_pct, 88.0)
        self.assertEqual(res.p4_nd_motor_calls, 0)
        self.assertEqual(res.p4_nd_motor_faults, 0)

    def test_22_negative_ev_shift_opens_aperture_smoothly_in_12800_cine_ei(self) -> None:
        res = p87.simulate_cine_ei_push_auto_iris(
            base_iso=12800,
            shutter_angle_deg=180.0,
            initial_eighth_steps=28,
            scene_ev_shift=-2.0,
            metering_mode=p87.METERING_MULTI_GREY_CARD,
        )
        self.assertTrue(res.passed)
        self.assertEqual(res.cine_ei_base_iso_locked, 12800)
        self.assertLess(res.final_t_stop, res.initial_t_stop)
        self.assertEqual(res.eighth_stop_steps_moved, 16)
        self.assertLessEqual(abs(res.final_grey_ire_pct - 41.0), 0.15)

    def test_23_push_auto_iris_rejects_invalid_iso_shutter_or_metering_mode(self) -> None:
        with self.assertRaises(p87.PlaybackShotmarkDewpointError):
            p87.simulate_cine_ei_push_auto_iris(base_iso=1600)
        with self.assertRaises(p87.PlaybackShotmarkDewpointError):
            p87.simulate_cine_ei_push_auto_iris(shutter_angle_deg=90.0)
        with self.assertRaises(p87.PlaybackShotmarkDewpointError):
            p87.simulate_cine_ei_push_auto_iris(metering_mode="SPOT_INVALID")
        with self.assertRaises(p87.PlaybackShotmarkDewpointError):
            p87.simulate_cine_ei_push_auto_iris(initial_eighth_steps=99)

    def test_24_push_auto_iris_mhlx_trajectory_monotonic_and_deterministic(self) -> None:
        r1 = p87.simulate_cine_ei_push_auto_iris()
        r2 = p87.simulate_cine_ei_push_auto_iris()
        self.assertEqual(r1, r2)
        t_stops = [s.t_stop for s in r1.trajectory]
        self.assertEqual(len(t_stops), r1.mhlx_packets_sent + 1)
        self.assertTrue(all(t_stops[i] <= t_stops[i + 1] for i in range(len(t_stops) - 1)))
        self.assertTrue(all(s.mhlx_opcode_hex == "0x0220" and s.cp_ack_hex == "0x8220" for s in r1.trajectory))


class TestDewpointTecAndPmic5vHil(unittest.TestCase):
    """Verify tropical dewpoint TEC trap, internal libfan air cooling, and PMIC 5V hot-plug HIL."""

    def test_25_magnus_tetens_dew_point_at_31c_80pct_rh(self) -> None:
        t_dp = p87.compute_magnus_tetens_dew_point_c(31.0, 80.0)
        self.assertAlmostEqual(t_dp, 27.14, places=2)
        with self.assertRaises(p87.PlaybackShotmarkDewpointError):
            p87.compute_magnus_tetens_dew_point_c(75.0, 80.0)
        with self.assertRaises(p87.PlaybackShotmarkDewpointError):
            p87.compute_magnus_tetens_dew_point_c(31.0, 110.0)

    def test_26_sub_dewpoint_external_tec_11c_triggers_hil_warning_and_shed(self) -> None:
        res = p87.evaluate_dewpoint_tec_hil(
            ambient_temp_c=31.0,
            relative_humidity_pct=80.0,
            cooling_method=p87.COOLING_EXTERNAL_PELTIER_TEC,
            tec_cold_plate_c=11.0,
        )
        self.assertTrue(res.passed)
        self.assertEqual(res.status, "BLOCKED_SUB_DEWPOINT_TEC_CONDENSATION_HAZARD")
        self.assertTrue(res.sub_dewpoint_detected)
        self.assertTrue(res.hil_warning_raised)
        self.assertTrue(res.tec_shed_executed)
        self.assertEqual(res.condensation_risk_pct, 0.0)
        self.assertEqual(res.pmic_rail_faults, 0)

    def test_27_internal_libfan_air_cooling_runs_100pct_green_in_tropical_humidity(self) -> None:
        res = p87.evaluate_dewpoint_tec_hil(
            ambient_temp_c=31.0,
            relative_humidity_pct=80.0,
            cooling_method=p87.COOLING_INTERNAL_CENTRIFUGAL_AIR,
            chassis_temp_c=39.5,
        )
        self.assertTrue(res.passed)
        self.assertEqual(res.status, "SAFE_INTERNAL_FAN_AIR_COOLING")
        self.assertFalse(res.sub_dewpoint_detected)
        self.assertFalse(res.hil_warning_raised)
        self.assertFalse(res.tec_shed_executed)
        self.assertTrue(res.libfan_air_cooling_active)
        self.assertEqual(res.condensation_risk_pct, 0.0)

    def test_28_pid_regulated_tec_above_dewpoint_safety_floor_allowed(self) -> None:
        res = p87.evaluate_dewpoint_tec_hil(
            ambient_temp_c=31.0,
            relative_humidity_pct=80.0,
            cooling_method=p87.COOLING_EXTERNAL_PELTIER_TEC,
            tec_cold_plate_c=30.0,
        )
        self.assertTrue(res.passed)
        self.assertEqual(res.status, "SAFE_PID_REGULATED_TEC_ABOVE_DEWPOINT")
        self.assertFalse(res.sub_dewpoint_detected)
        self.assertFalse(res.hil_warning_raised)

    def test_29_pmic_5v_unpowered_hotplug_over_900ma_sheds_before_rail_fault(self) -> None:
        res = p87.evaluate_pmic_5v_hotplug_hil(
            xlr_h1_48v_attached=True,
            active_optical_hdmi_attached=True,
            usbc_lan_bus_powered=True,
            powered_usbc_pd_hub=False,
        )
        self.assertTrue(res.passed)
        self.assertEqual(res.status, "BLOCKED_PMIC_5V_OVERBUDGET_SHED_BEFORE_RAIL_FAULT")
        self.assertGreater(res.raw_5v_draw_ma, 900.0)
        self.assertTrue(res.overbudget_detected)
        self.assertTrue(res.hil_warning_raised)
        self.assertTrue(res.load_shed_executed)
        self.assertLessEqual(res.post_shed_5v_draw_ma, 900.0)
        self.assertEqual(res.pmic_rail_faults, 0)
        self.assertTrue(res.recording_uninterrupted)

    def test_30_pmic_5v_with_powered_usb_pd_hub_runs_100pct_green(self) -> None:
        res = p87.evaluate_pmic_5v_hotplug_hil(
            xlr_h1_48v_attached=True,
            active_optical_hdmi_attached=True,
            usbc_lan_bus_powered=True,
            powered_usbc_pd_hub=True,
        )
        self.assertTrue(res.passed)
        self.assertEqual(res.status, "SAFE_PMIC_5V_WITH_POWERED_PD_HUB_GREEN")
        self.assertLessEqual(res.raw_5v_draw_ma, 900.0)
        self.assertFalse(res.overbudget_detected)
        self.assertFalse(res.hil_warning_raised)
        self.assertFalse(res.load_shed_executed)
        self.assertEqual(res.pmic_rail_faults, 0)
        self.assertTrue(res.recording_uninterrupted)


class TestStage13SuiteIntegrationAndCli(unittest.TestCase):
    """Verify Stage 13 wiring in fx3_vm_coemulation_suite.py, CLI flags, and source hygiene."""

    def test_31_coemulation_suite_includes_stage13_and_skip_phase87_backward_compat(self) -> None:
        rep_full = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig(force_clean_room=True))
        self.assertTrue(rep_full["all_checks_passed"])
        self.assertIn("stage13_phase87_playback_shotmark_dewpoint", rep_full)
        s13 = rep_full["stage13_phase87_playback_shotmark_dewpoint"]
        self.assertTrue(s13["all_checks_passed"])
        self.assertEqual(s13["cp_mutation_bytes"], 0)
        self.assertEqual(s13["bk4_persistent_nvram_writes"], 0)
        self.assertEqual(s13["p1_emmc_mutations"], 0)
        self.assertEqual(s13["internal_emmc_writes"], 0)
        self.assertTrue(s13["internal_emmc_format_blocked"])
        self.assertTrue(s13["c2pa_license_untouched"])
        self.assertEqual(s13["p4_nd_motor_faults"], 0)
        self.assertFalse(s13["persistent_emmc_writes_authorized"])

        rep_skip = suite.run_fx3_vm_coemulation_suite(
            suite.CoEmulationConfig(force_clean_room=True, include_phase87_playback_shotmark_dewpoint=False)
        )
        self.assertTrue(rep_skip["all_checks_passed"])
        self.assertNotIn("stage13_phase87_playback_shotmark_dewpoint", rep_skip)

    def test_32_clean_room_audit_digest_reproducible_and_valid_json(self) -> None:
        rep1 = p87.run_phase87_playback_shotmark_dewpoint_audit(force_clean_room=True)
        rep2 = p87.run_phase87_playback_shotmark_dewpoint_audit(force_clean_room=True)
        self.assertEqual(rep1["audit_digest_sha256"], rep2["audit_digest_sha256"])

        rendered = json.dumps(rep1, allow_nan=False)
        self.assertNotRegex(rendered, r'(?<![0-9A-Za-z_/.-])b[\'"]')

        copy = dict(rep1)
        recorded = copy.pop("audit_digest_sha256")
        expected = hashlib.sha256(
            json.dumps(copy, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        self.assertEqual(recorded, expected)

    def test_33_standalone_cli_flags_emit_valid_outputs(self) -> None:
        for argv in (
            ["--clean-room", "--summary"],
            ["--clean-room", "--playback-matrix"],
            ["--clean-room", "--iris-matrix"],
            ["--clean-room", "--hil-matrix"],
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = p87.main(argv)
            self.assertEqual(rc, 0, msg=f"CLI argv={argv} failed")
            self.assertTrue(buf.getvalue().strip())

    def test_34_suite_cli_summary_and_skip_phase87_flag(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        proc = subprocess.run(
            [
                "/usr/bin/python3",
                "-B",
                str(FX3_VM_DIR / "fx3_vm_coemulation_suite.py"),
                "--clean-room",
                "--summary",
            ],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        self.assertIn("pb_iris_hil=CLEAN_ROOM_SYNTHETIC", proc.stdout)

        proc_skip = subprocess.run(
            [
                "/usr/bin/python3",
                "-B",
                str(FX3_VM_DIR / "fx3_vm_coemulation_suite.py"),
                "--clean-room",
                "--skip-phase87",
                "--summary",
            ],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc_skip.returncode, 0, msg=proc_skip.stderr)
        self.assertNotIn("pb_iris_hil=", proc_skip.stdout)

    def test_35_json_output_determinism_without_bytes_repr_leakage(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = p87.main(["--clean-room", "--json"])
        self.assertEqual(rc, 0)
        rendered = buf.getvalue()
        self.assertNotRegex(rendered, r'(?<![0-9A-Za-z_/.-])b[\'"]')
        parsed = json.loads(rendered)
        self.assertEqual(parsed["schema"], p87.PHASE_87_SCHEMA)
        self.assertTrue(parsed["all_checks_passed"])

    def test_36_source_hygiene_o_rdonly_and_no_forbidden_writes_or_port(self) -> None:
        forbidden_port = "87" + "68"
        emu_src = (FX3_VM_DIR / "playback_shotmark_dewpoint_emulator.py").read_text(encoding="utf-8")
        test_src = Path(__file__).read_text(encoding="utf-8")

        self.assertIn("os.O_RDONLY", emu_src)
        self.assertNotIn("os.O_WRONLY", emu_src)
        self.assertNotIn("os.O_RDWR", emu_src)
        self.assertNotIn(forbidden_port, emu_src)
        self.assertNotIn(forbidden_port, test_src)
        self.assertIn("CP_MUTATION_BYTES = 0", emu_src)
        self.assertIn("BK4_PERSISTENT_NVRAM_WRITES = 0", emu_src)
        self.assertIn("INTERNAL_EMMC_FORMAT_BLOCKED = True", emu_src)
        self.assertIn("P4_ND_MOTOR_FAULTS = 0", emu_src)
        self.assertIn("PERSISTENT_EMMC_WRITES_AUTHORIZED = False", emu_src)


if __name__ == "__main__":
    unittest.main()
