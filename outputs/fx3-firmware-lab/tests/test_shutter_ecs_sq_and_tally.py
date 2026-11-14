"""Unit tests for Phase 60 Shutter Angle (5.6..360 deg), ECS, S&Q (1..240fps), Tally LEDs & FX3 Mechanical Shutter Curtain Protection Auditor.

Designed to execute rapidly in BOTH Local Donor (`os.O_RDONLY`) and
`FX3_FX6_FORCE_CLEAN_ROOM=1` modes while keeping the full `fx3-firmware-lab`
suite (>=241 tests) under 9 seconds.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from typing import Optional
from unittest.mock import patch

from fx3_firmware_lab.__main__ import main as cli_main, run_audit_all
from fx3_firmware_lab.haita_bk4_feature_analyzer import is_forced_clean_room
from fx3_firmware_lab.shutter_ecs_sq_and_tally_auditor import (
    CP_SHARED_ELEC_SHUTTER_MARKERS,
    CP_SHARED_TALLY_MARKERS,
    DEFAULT_SHUTTER_ANGLE_DEG,
    FX3_APPFW_MECH_SHUTTER_MARKERS,
    FX3_APPFW_SQ_HFR_MARKERS,
    FX3_CP_MECH_SHUTTER_MARKERS,
    FX3_CP_SQ_MARKERS,
    FX6_APPFW_ECS_AND_ANGLE_MARKERS,
    FX6_APPFW_SQ_HFR_MARKERS,
    FX6_APPFW_TALLY_MARKERS,
    FX6_CP_SHUTTER_ANGLE_MARKERS,
    FX6_MPR_SHUTTER_RTMD_MARKERS,
    MPR_SHARED_AUDIO_PROXY_MARKERS,
    PHASE_60_SCHEMA,
    PHASE_60_VERSION,
    SHARED_APPFW_REC_LAMP_MARKERS,
    SHARED_APPFW_SHUTTER_ANGLE_MARKERS,
    SHARED_APPFW_SQ_MARKERS,
    VALID_DISCRETE_SHUTTER_ANGLES_DEG,
    ShutterEcsSqAndTallyReport,
    analyze_shutter_ecs_sq_and_tally,
    build_clean_room_shutter_ecs_sq_tally_fixtures,
    evaluate_ecs_anti_flicker,
    evaluate_mech_shutter_curtain_protection,
    evaluate_shutter_angle_exposure,
    evaluate_sq_motion_contract,
    evaluate_tally_lamp_routing,
    shutter_ecs_sq_and_tally_report_to_dict,
)


PKG_ROOT = Path(__file__).resolve().parents[1]


class TestActiveShutterEcsSqAndTally(unittest.TestCase):
    _active_report: Optional[ShutterEcsSqAndTallyReport] = None

    @classmethod
    def setUpClass(cls) -> None:
        cls._active_report = analyze_shutter_ecs_sq_and_tally()

    def test_01_active_mode_passes_with_o_rdonly_and_10_artifacts(self) -> None:
        rep = self._active_report
        assert rep is not None
        self.assertTrue(rep.all_checks_passed, msg=f"Errors: {rep.errors}")
        self.assertEqual(rep.schema_version, PHASE_60_SCHEMA)
        self.assertEqual(rep.phase_version, PHASE_60_VERSION)
        self.assertTrue(rep.o_rdonly_enforced)
        self.assertEqual(len(rep.report_sha256), 64)
        self.assertEqual(len(rep.donor_file_sizes), 10)
        if not is_forced_clean_room() and rep.mode == "LOCAL_DONOR_VERIFIED":
            self.assertGreater(rep.donor_file_sizes["fx3_appfw"], 70_000_000)
            self.assertGreater(rep.donor_file_sizes["fx6_appfw"], 45_000_000)
            self.assertGreater(rep.donor_file_sizes["fx3_cpapp"], 10_000_000)
            self.assertGreater(rep.donor_file_sizes["fx6_cpapp"], 10_000_000)

    def test_02_active_report_json_serializable_without_raw_bytes(self) -> None:
        rep = self._active_report
        assert rep is not None
        payload = shutter_ecs_sq_and_tally_report_to_dict(rep)
        encoded = json.dumps(payload, sort_keys=True)
        self.assertNotIn("b'", encoded)
        decoded = json.loads(encoded)
        self.assertEqual(decoded["report_sha256"], rep.report_sha256)
        self.assertTrue(decoded["all_checks_passed"])

    def test_03_pillar_a_mech_shutter_protection_markers_and_zero_actuations(self) -> None:
        rep = self._active_report
        assert rep is not None
        pa = rep.pillar_a_mech_shutter
        self.assertTrue(pa.passed)
        self.assertEqual(pa.mech_shutter_unintended_actuations, 0)
        self.assertEqual(pa.cp_mutation_bytes, 0)
        self.assertEqual(pa.fx3_appfw_mech_shutter_markers, FX3_APPFW_MECH_SHUTTER_MARKERS)
        self.assertEqual(pa.fx6_appfw_unexpected_mech_pids, ())
        self.assertEqual(pa.fx3_cp_mech_shutter_markers, FX3_CP_MECH_SHUTTER_MARKERS)
        self.assertEqual(pa.fx6_cp_unexpected_mech_markers, ())
        self.assertEqual(pa.fx3_cp_shared_elec_markers, CP_SHARED_ELEC_SHUTTER_MARKERS)
        self.assertEqual(pa.fx6_cp_shared_elec_markers, CP_SHARED_ELEC_SHUTTER_MARKERS)
        self.assertTrue(pa.video_mode_eval.curtains_parked_safely_open)
        self.assertFalse(pa.video_mode_eval.solenoid_energized_in_video)
        self.assertEqual(len(pa.matrix), 3)

    def test_04_pillar_b_shutter_angle_ecs_markers_and_uxc_labels(self) -> None:
        rep = self._active_report
        assert rep is not None
        pb = rep.pillar_b_shutter_angle_ecs
        self.assertTrue(pb.passed)
        self.assertEqual(pb.fx3_shared_angle_markers, SHARED_APPFW_SHUTTER_ANGLE_MARKERS)
        self.assertEqual(pb.fx6_shared_angle_markers, SHARED_APPFW_SHUTTER_ANGLE_MARKERS)
        self.assertEqual(pb.fx6_ecs_and_angle_markers, FX6_APPFW_ECS_AND_ANGLE_MARKERS)
        self.assertEqual(pb.fx6_cp_shutter_markers, FX6_CP_SHUTTER_ANGLE_MARKERS)
        self.assertEqual(pb.fx6_mpr_rtmd_shutter_markers, FX6_MPR_SHUTTER_RTMD_MARKERS)
        self.assertEqual(pb.uxc_shutter_ecs_labels["fx6_ecs"], "ECS")
        self.assertEqual(pb.uxc_shutter_ecs_labels["fx6_ecs_frequency"], "ECS Frequency")
        self.assertEqual(pb.uxc_shutter_ecs_labels["fx6_shutter_angle"], "Shutter Angle")
        self.assertEqual(pb.uxc_shutter_ecs_labels["fx3_slow_shutter"], "Slow Shutter")
        self.assertAlmostEqual(pb.default_180_at_24fps_eval.exposure_time_sec, 1.0 / 48.0, places=7)

    def test_05_pillar_c_sq_motion_markers_and_uxc_labels(self) -> None:
        rep = self._active_report
        assert rep is not None
        pc = rep.pillar_c_sq_motion
        self.assertTrue(pc.passed)
        self.assertEqual(pc.fx3_shared_sq_markers, SHARED_APPFW_SQ_MARKERS)
        self.assertEqual(pc.fx6_shared_sq_markers, SHARED_APPFW_SQ_MARKERS)
        self.assertEqual(pc.fx3_sq_hfr_markers, FX3_APPFW_SQ_HFR_MARKERS)
        self.assertEqual(pc.fx6_sq_hfr_markers, FX6_APPFW_SQ_HFR_MARKERS)
        self.assertEqual(pc.fx3_cp_sq_markers, FX3_CP_SQ_MARKERS)
        self.assertEqual(pc.fx3_mpr_audio_proxy_markers, MPR_SHARED_AUDIO_PROXY_MARKERS)
        self.assertEqual(pc.fx6_mpr_audio_proxy_markers, MPR_SHARED_AUDIO_PROXY_MARKERS)
        self.assertEqual(pc.uxc_sq_labels["fx3_sq_motion"], "S&Q Motion")
        self.assertEqual(pc.uxc_sq_labels["fx3_audio_recording"], "Audio Recording")
        self.assertEqual(pc.uxc_sq_labels["fx6_slow_and_quick_motion"], "Slow & Quick Motion")
        self.assertFalse(pc.sq_4k_120fps_24p_eval.audio_recording_enabled)
        self.assertFalse(pc.sq_fhd_240fps_24p_eval.proxy_allowed)

    def test_06_pillar_d_tally_lamp_markers_and_uxc_labels(self) -> None:
        rep = self._active_report
        assert rep is not None
        pd = rep.pillar_d_tally_lamps
        self.assertTrue(pd.passed)
        self.assertEqual(pd.missing_gpio_faults, 0)
        self.assertEqual(pd.fx3_rec_lamp_markers, SHARED_APPFW_REC_LAMP_MARKERS)
        self.assertEqual(pd.fx6_rec_lamp_markers, SHARED_APPFW_REC_LAMP_MARKERS)
        self.assertEqual(pd.fx6_tally_markers, FX6_APPFW_TALLY_MARKERS)
        self.assertEqual(pd.fx3_cp_tally_markers, CP_SHARED_TALLY_MARKERS)
        self.assertEqual(pd.fx6_cp_tally_markers, CP_SHARED_TALLY_MARKERS)
        self.assertEqual(pd.uxc_tally_labels["fx6_front_tally_lamp"], "Front Tally Lamp")
        self.assertEqual(pd.uxc_tally_labels["fx6_rear_tally_lamp"], "Rear Tally Lamp")
        self.assertEqual(pd.uxc_tally_labels["fx6_tally_lamp_brightness"], "Tally Lamp Brightness")
        self.assertEqual(pd.uxc_tally_labels["fx6_rec_tally_blink"], "Rec Tally Blink")


class TestPillarAMechShutterProtection(unittest.TestCase):
    def test_07_video_and_sq_modes_park_curtains_open_with_zero_actuations(self) -> None:
        for mode in ("VIDEO_ELECTRONIC_SHUTTER", "S_AND_Q_ELECTRONIC_SHUTTER"):
            res = evaluate_mech_shutter_curtain_protection(
                operating_mode=mode,
                shutter_mode_requested="ELECTRONIC_ROLLING",
                fx6_video_ipc_emits_mech_pid=False,
                curtain_parked_open=True,
            )
            self.assertTrue(res.valid)
            self.assertEqual(res.status, "MECH_SHUTTER_CURTAINS_PARKED_OPEN_VIDEO_SAFE")
            self.assertTrue(res.curtains_parked_safely_open)
            self.assertFalse(res.solenoid_energized_in_video)
            self.assertEqual(res.mech_shutter_unintended_actuations, 0)

    def test_08_stills_and_antidust_allowed_only_outside_video_mode(self) -> None:
        stills = evaluate_mech_shutter_curtain_protection(
            operating_mode="STILLS_MECHANICAL_SHUTTER",
            shutter_mode_requested="MECHANICAL_CURTAIN",
            curtain_parked_open=False,
        )
        self.assertTrue(stills.valid)
        self.assertEqual(stills.status, "STILLS_OR_ANTIDUST_MECH_CURTAIN_AUTHORIZED")
        self.assertEqual(stills.mech_shutter_unintended_actuations, 0)

        dust = evaluate_mech_shutter_curtain_protection(
            operating_mode="ANTI_DUST_CLEANING_MODE",
            shutter_mode_requested="ANTI_DUST_BARRIER",
            curtain_parked_open=False,
        )
        self.assertTrue(dust.valid)

    def test_09_blocks_fx6_mech_pid_or_curtain_actuation_or_cp_mutation(self) -> None:
        bad_pid = evaluate_mech_shutter_curtain_protection(
            operating_mode="VIDEO_ELECTRONIC_SHUTTER",
            fx6_video_ipc_emits_mech_pid=True,
        )
        self.assertFalse(bad_pid.valid)
        self.assertEqual(bad_pid.mech_shutter_unintended_actuations, 1)
        self.assertTrue(bad_pid.solenoid_energized_in_video)

        bad_req = evaluate_mech_shutter_curtain_protection(
            operating_mode="VIDEO_ELECTRONIC_SHUTTER",
            shutter_mode_requested="MECHANICAL_CURTAIN",
        )
        self.assertFalse(bad_req.valid)
        self.assertEqual(bad_req.mech_shutter_unintended_actuations, 1)

        bad_park = evaluate_mech_shutter_curtain_protection(
            operating_mode="S_AND_Q_ELECTRONIC_SHUTTER",
            curtain_parked_open=False,
        )
        self.assertFalse(bad_park.valid)

        bad_cp = evaluate_mech_shutter_curtain_protection(cp_mutation_bytes=8)
        self.assertFalse(bad_cp.valid)


class TestPillarBShutterAngleAndEcs(unittest.TestCase):
    def test_10_shutter_angle_180_default_exact_exposure_across_23_976_to_240fps(self) -> None:
        for fps in (23.976, 24.0, 25.0, 29.97, 50.0, 59.94, 120.0, 240.0):
            res = evaluate_shutter_angle_exposure(angle_deg=DEFAULT_SHUTTER_ANGLE_DEG, fps=fps)
            self.assertTrue(res.valid)
            self.assertAlmostEqual(res.exposure_time_sec, (180.0 / 360.0) / fps, places=7)
            self.assertAlmostEqual(res.equivalent_shutter_denom, 2.0 * fps, places=2)
            self.assertTrue(res.fits_within_frame_period)

    def test_11_all_19_discrete_sony_shutter_angles_and_continuous_5_6_to_360(self) -> None:
        self.assertEqual(len(VALID_DISCRETE_SHUTTER_ANGLES_DEG), 19)
        for ang in VALID_DISCRETE_SHUTTER_ANGLES_DEG:
            res = evaluate_shutter_angle_exposure(angle_deg=ang, fps=24.0, continuous=False)
            self.assertTrue(res.valid, msg=f"Failed angle={ang}: {res.errors}")
            self.assertAlmostEqual(res.exposure_time_sec, (ang / 360.0) / 24.0, places=7)

        cont = evaluate_shutter_angle_exposure(angle_deg=172.3, fps=23.976, continuous=True)
        self.assertTrue(cont.valid)
        self.assertAlmostEqual(cont.exposure_time_sec, (172.3 / 360.0) / 23.976, places=7)

    def test_12_rejects_out_of_range_or_non_finite_shutter_angle_or_fps(self) -> None:
        self.assertFalse(evaluate_shutter_angle_exposure(angle_deg=5.5, fps=24.0, continuous=True).valid)
        self.assertFalse(evaluate_shutter_angle_exposure(angle_deg=360.1, fps=24.0, continuous=True).valid)
        self.assertFalse(evaluate_shutter_angle_exposure(angle_deg=172.3, fps=24.0, continuous=False).valid)
        self.assertFalse(evaluate_shutter_angle_exposure(angle_deg=180.0, fps=20.0).valid)
        self.assertFalse(evaluate_shutter_angle_exposure(angle_deg=180.0, fps=250.0).valid)
        self.assertFalse(evaluate_shutter_angle_exposure(angle_deg=float("nan"), fps=24.0).valid)

    def test_13_ecs_anti_flicker_math_led_wall_1920hz_and_mains_100hz(self) -> None:
        led = evaluate_ecs_anti_flicker(ecs_freq_hz=120.0, fps=24.0, light_source_hz=1920.0)
        self.assertTrue(led.valid)
        self.assertTrue(led.flicker_free_locked)
        self.assertEqual(led.status, "ECS_LED_FLICKER_LOCKED")
        self.assertAlmostEqual(led.exposure_time_sec, 1.0 / 120.0, places=7)
        self.assertAlmostEqual(led.equivalent_angle_deg, 72.0, places=4)

        pal = evaluate_ecs_anti_flicker(ecs_freq_hz=50.0, fps=25.0, light_source_hz=100.0)
        self.assertTrue(pal.valid)
        self.assertTrue(pal.flicker_free_locked)

        unsynced = evaluate_ecs_anti_flicker(ecs_freq_hz=67.3, fps=24.0, light_source_hz=120.0)
        self.assertTrue(unsynced.valid)
        self.assertFalse(unsynced.flicker_free_locked)

    def test_14_ecs_rejects_freq_below_fps_or_out_of_bounds(self) -> None:
        self.assertFalse(evaluate_ecs_anti_flicker(ecs_freq_hz=24.0, fps=60.0).valid)
        self.assertFalse(evaluate_ecs_anti_flicker(ecs_freq_hz=20.0, fps=24.0).valid)
        self.assertFalse(evaluate_ecs_anti_flicker(ecs_freq_hz=9000.0, fps=24.0).valid)
        self.assertFalse(evaluate_ecs_anti_flicker(ecs_freq_hz=float("inf"), fps=24.0).valid)


class TestPillarCSqMotionMatrix(unittest.TestCase):
    def test_15_sq_4k_dci_and_qfhd_1_to_120fps_envelope_and_speed_factor(self) -> None:
        ok_120 = evaluate_sq_motion_contract(
            resolution_class="4K_DCI",
            sensor_fps=120,
            rec_fps=24.0,
            codec="XAVC_S_I_DCI_4K",
            card_class="CFEXPRESS_TYPE_A",
            proxy_requested=True,
        )
        self.assertTrue(ok_120.valid)
        self.assertEqual(ok_120.speed_factor, 5.0)
        self.assertTrue(ok_120.off_speed)
        self.assertFalse(ok_120.audio_recording_enabled)

        bad_150 = evaluate_sq_motion_contract(
            resolution_class="QFHD",
            sensor_fps=150,
            rec_fps=24.0,
            codec="XAVC_S_4K",
            card_class="CFEXPRESS_TYPE_A",
        )
        self.assertFalse(bad_150.valid)

    def test_16_sq_fhd_1_to_240fps_envelope_and_hfr_proxy_gating(self) -> None:
        ok_240 = evaluate_sq_motion_contract(
            resolution_class="FHD",
            sensor_fps=240,
            rec_fps=24.0,
            codec="XAVC_S_I_HD",
            card_class="CFEXPRESS_TYPE_A",
            proxy_requested=False,
        )
        self.assertTrue(ok_240.valid)
        self.assertEqual(ok_240.speed_factor, 10.0)
        self.assertFalse(ok_240.proxy_allowed)

        bad_proxy_240 = evaluate_sq_motion_contract(
            resolution_class="FHD",
            sensor_fps=240,
            rec_fps=24.0,
            codec="XAVC_S_I_HD",
            card_class="CFEXPRESS_TYPE_A",
            proxy_requested=True,
        )
        self.assertFalse(bad_proxy_240.valid)
        self.assertFalse(evaluate_sq_motion_contract(resolution_class="FHD", sensor_fps=300, codec="XAVC_S_HD").valid)

    def test_17_sq_off_speed_auto_disables_audio_and_blocks_forced_audio(self) -> None:
        ok_1fps = evaluate_sq_motion_contract(
            resolution_class="QFHD",
            sensor_fps=1,
            rec_fps=24.0,
            codec="XAVC_S_4K",
            card_class="SDXC_V60",
        )
        self.assertTrue(ok_1fps.valid)
        self.assertFalse(ok_1fps.audio_recording_enabled)
        self.assertEqual(ok_1fps.audio_muted_reason, "OFF_SPEED_SQ_AUDIO_AUTO_DISABLED")

        bad_audio = evaluate_sq_motion_contract(
            resolution_class="4K_DCI",
            sensor_fps=120,
            rec_fps=24.0,
            codec="XAVC_S_I_DCI_4K",
            card_class="CFEXPRESS_TYPE_A",
            force_audio_in_off_speed=True,
        )
        self.assertFalse(bad_audio.valid)
        self.assertEqual(bad_audio.status, "BLOCKED_SQ_AUDIO_DESYNC_VIOLATION")

    def test_18_sq_cfexpress_vs_sdxc_v90_v60_v30_sustained_write_coupling(self) -> None:
        # 4K S&Q 120fps XAVC S-I requires 240 * 5 = 1200 Mbps -> V90 (720 Mbps) must fail, CFexpress Type A (1600 Mbps) passes
        bad_v90 = evaluate_sq_motion_contract(
            resolution_class="4K_DCI",
            sensor_fps=120,
            rec_fps=24.0,
            codec="XAVC_S_I_DCI_4K",
            card_class="SDXC_V90",
        )
        self.assertFalse(bad_v90.valid)
        self.assertEqual(bad_v90.estimated_write_mbps, 1200.0)

        ok_cfe = evaluate_sq_motion_contract(
            resolution_class="4K_DCI",
            sensor_fps=120,
            rec_fps=24.0,
            codec="XAVC_S_I_DCI_4K",
            card_class="CFEXPRESS_TYPE_A",
        )
        self.assertTrue(ok_cfe.valid)


class TestPillarDTallyLamps(unittest.TestCase):
    def test_19_tally_front_rear_combinations_map_to_fx3_rec_lamp_cmds(self) -> None:
        self.assertEqual(
            evaluate_tally_lamp_routing(front_tally_on=True, rear_tally_on=True).fx3_rec_lamp_cmd,
            "REC_LAMP_ALL_LIGHTS_UP",
        )
        self.assertEqual(
            evaluate_tally_lamp_routing(front_tally_on=False, rear_tally_on=True).fx3_rec_lamp_cmd,
            "REC_LAMP_ONLY_FRONT_OFF",
        )
        self.assertEqual(
            evaluate_tally_lamp_routing(front_tally_on=True, rear_tally_on=False).fx3_rec_lamp_cmd,
            "REC_LAMP_LIGHT_UP_ONLY_ONE",
        )
        self.assertEqual(
            evaluate_tally_lamp_routing(front_tally_on=False, rear_tally_on=False).fx3_rec_lamp_cmd,
            "REC_LAMP_ALL_LIGHTS_OUT",
        )

    def test_20_tally_brightness_off_and_green_yellow_osd_containment(self) -> None:
        off = evaluate_tally_lamp_routing(front_tally_on=True, rear_tally_on=True, brightness="OFF")
        self.assertTrue(off.valid)
        self.assertEqual(off.fx3_rec_lamp_cmd, "REC_LAMP_ALL_LIGHTS_OUT")

        gy = evaluate_tally_lamp_routing(
            front_tally_on=True,
            rear_tally_on=True,
            brightness="LOW",
            rec_tally_blink=True,
            green_tally_requested=True,
            yellow_tally_requested=True,
        )
        self.assertTrue(gy.valid)
        self.assertTrue(gy.osd_indicator_fallback)
        self.assertEqual(gy.missing_gpio_faults, 0)
        self.assertEqual(gy.status, "FX3_TALLY_MAPPED_WITH_GY_OSD_CONTAINMENT")

    def test_21_tally_rejects_invalid_brightness_and_missing_gpio_writes(self) -> None:
        self.assertFalse(evaluate_tally_lamp_routing(brightness="TURBO").valid)
        bad_gpio = evaluate_tally_lamp_routing(missing_gpio_write_attempted=True)
        self.assertFalse(bad_gpio.valid)
        self.assertEqual(bad_gpio.missing_gpio_faults, 1)


class TestCleanRoomFaultInjectionAndCli(unittest.TestCase):
    def test_22_forced_clean_room_deterministic_equivalence_and_env_fallback(self) -> None:
        r1 = analyze_shutter_ecs_sq_and_tally(clean_room=True)
        r2 = analyze_shutter_ecs_sq_and_tally(clean_room=True)
        self.assertEqual(r1.mode, "CLEAN_ROOM_SYNTHETIC_VERIFIED")
        self.assertTrue(r1.all_checks_passed, msg=f"Errors: {r1.errors}")
        self.assertEqual(r1.report_sha256, r2.report_sha256)

        with patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            r_env = analyze_shutter_ecs_sq_and_tally()
        self.assertEqual(r_env.mode, "CLEAN_ROOM_SYNTHETIC_VERIFIED")
        self.assertTrue(r_env.all_checks_passed)

        with patch(
            "fx3_firmware_lab.shutter_ecs_sq_and_tally_auditor.resolve_donor_file",
            return_value=None,
        ):
            r_missing = analyze_shutter_ecs_sq_and_tally()
        self.assertEqual(r_missing.mode, "CLEAN_ROOM_SYNTHETIC_VERIFIED")
        self.assertTrue(r_missing.all_checks_passed)

    def test_23_fault_inject_fx6_mech_pid_and_cp_mech_handler(self) -> None:
        fx_pid = build_clean_room_shutter_ecs_sq_tally_fixtures(inject_fx6_mech_shutter_pid=True)
        rep_pid = analyze_shutter_ecs_sq_and_tally(clean_room=True, synthetic_overrides=fx_pid)
        self.assertFalse(rep_pid.all_checks_passed)
        self.assertFalse(rep_pid.pillar_a_mech_shutter.passed)
        self.assertGreater(rep_pid.pillar_a_mech_shutter.mech_shutter_unintended_actuations, 0)

        fx_cp = build_clean_room_shutter_ecs_sq_tally_fixtures(inject_fx6_cp_mech_shutter=True)
        rep_cp = analyze_shutter_ecs_sq_and_tally(clean_room=True, synthetic_overrides=fx_cp)
        self.assertFalse(rep_cp.all_checks_passed)
        self.assertFalse(rep_cp.pillar_a_mech_shutter.passed)

    def test_24_fault_drop_shutter_angle_5_6_360_and_fx6_ecs(self) -> None:
        fx_ang = build_clean_room_shutter_ecs_sq_tally_fixtures(drop_shutter_angle_5_6_or_360=True)
        rep_ang = analyze_shutter_ecs_sq_and_tally(clean_room=True, synthetic_overrides=fx_ang)
        self.assertFalse(rep_ang.all_checks_passed)
        self.assertFalse(rep_ang.pillar_b_shutter_angle_ecs.passed)

        fx_ecs = build_clean_room_shutter_ecs_sq_tally_fixtures(drop_fx6_ecs_markers=True)
        rep_ecs = analyze_shutter_ecs_sq_and_tally(clean_room=True, synthetic_overrides=fx_ecs)
        self.assertFalse(rep_ecs.all_checks_passed)
        self.assertFalse(rep_ecs.pillar_b_shutter_angle_ecs.passed)

    def test_25_fault_drop_sq_240fps_and_tally_markers_and_corrupt_uxc(self) -> None:
        fx_sq = build_clean_room_shutter_ecs_sq_tally_fixtures(drop_sq_240fps=True)
        self.assertFalse(
            analyze_shutter_ecs_sq_and_tally(clean_room=True, synthetic_overrides=fx_sq).pillar_c_sq_motion.passed
        )
        fx_lamp = build_clean_room_shutter_ecs_sq_tally_fixtures(drop_fx3_rec_lamp=True)
        self.assertFalse(
            analyze_shutter_ecs_sq_and_tally(clean_room=True, synthetic_overrides=fx_lamp).pillar_d_tally_lamps.passed
        )
        fx_uxc = build_clean_room_shutter_ecs_sq_tally_fixtures(corrupt_uxc_labels=True)
        rep_uxc = analyze_shutter_ecs_sq_and_tally(clean_room=True, synthetic_overrides=fx_uxc)
        self.assertFalse(rep_uxc.all_checks_passed)
        self.assertTrue(any("0x00002077" in e for e in rep_uxc.errors))

    def test_26_run_audit_all_contains_11_unified_auditors(self) -> None:
        payload = run_audit_all(clean_room=True)
        self.assertTrue(payload["all_checks_passed"])
        expected_auditors = {
            "ufu_container_audit",
            "haita_bk4_feature_audit",
            "uxc_ldec_asset_audit",
            "uxc_multilang_and_font_audit",
            "sensor_codec_compatibility_audit",
            "cube_lut_and_rtmd_audit",
            "wbi_hibdrv_and_elf_abi_audit",
            "global_xdb_and_menu_tree_audit",
            "audio_tc_hdmi_sdi_routing_audit",
            "emount_af_breathing_and_ibis_audit",
            "shutter_ecs_sq_and_tally_audit",
        }
        self.assertEqual(len(expected_auditors), 11)
        self.assertTrue(expected_auditors.issubset(set(payload.keys())))
        block = payload["shutter_ecs_sq_and_tally_audit"]
        assert isinstance(block, dict)
        self.assertTrue(block["all_checks_passed"])
        self.assertEqual(block["mode"], "CLEAN_ROOM_SYNTHETIC_VERIFIED")

    def test_27_cli_audit_shutter_tally_in_process_and_subprocess_clean_room(self) -> None:
        buf = StringIO()
        with redirect_stdout(buf):
            rc = cli_main(["audit-shutter-tally", "--clean-room"])
        self.assertEqual(rc, 0)
        parsed = json.loads(buf.getvalue())
        self.assertTrue(parsed["all_checks_passed"])
        self.assertEqual(parsed["schema_version"], PHASE_60_SCHEMA)

        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONPATH"] = str(PKG_ROOT)
        proc = subprocess.run(
            [sys.executable, "-B", "-m", "fx3_firmware_lab", "audit-shutter-tally", "--clean-room"],
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        sub_data = json.loads(proc.stdout)
        self.assertTrue(sub_data["all_checks_passed"])
        self.assertEqual(len(sub_data["report_sha256"]), 64)

    def test_28_module_uses_strict_o_rdonly_and_contains_zero_secrets_or_subprocesses(self) -> None:
        src = (PKG_ROOT / "fx3_firmware_lab" / "shutter_ecs_sq_and_tally_auditor.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("os.O_RDONLY", src)
        self.assertNotIn("os.O_RDWR", src)
        self.assertNotIn("os.O_WRONLY", src)
        self.assertNotIn("subprocess", src)
        self.assertNotIn("socket", src)
        self.assertNotIn("CXD90057_k8", src)
        self.assertNotIn("PRIVATE KEY", src)


if __name__ == "__main__":
    unittest.main()
