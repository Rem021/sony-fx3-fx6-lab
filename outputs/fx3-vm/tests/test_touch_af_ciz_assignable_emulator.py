#!/usr/bin/env python3
"""Phase 78 Test Suite — Stage 11 Capacitive Multi-Touch 627-pt PDAF Tracking,
`Clear Image Zoom` (`CIZ`) Runtime Arbitrator & Assignable Button Dispatcher.

Exercises 36 fast unit, evdev/MHLX protocol, anamorphic letterbox, CIZ/Zoom,
assignable no-op containment, Stage 11 suite integration, CLI, and source-hygiene
tests across BOTH Local Donor (`os.O_RDONLY`) and `FX3_FX6_FORCE_CLEAN_ROOM=1`
modes, strictly offline.
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
import touch_af_ciz_assignable_emulator as p78  # noqa: E402


_AUDIT_CACHE: dict = {}


def _get_clean_room_audit() -> dict:
    if "clean_room" not in _AUDIT_CACHE:
        _AUDIT_CACHE["clean_room"] = p78.run_phase78_touchaf_ciz_assignable_audit(force_clean_room=True)
    return _AUDIT_CACHE["clean_room"]


class TestPhase78DonorAuditAndRedlines(unittest.TestCase):
    """Verify O_RDONLY donor audit, clean-room fallback, and zero-mutation redlines."""

    def test_01_clean_room_donor_audit_verifies_all_10_artifacts_and_sha256(self) -> None:
        audit = p78.inspect_touch_ciz_assignable_donors(force_clean_room=True)
        self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(audit.access_mode, "O_RDONLY")
        self.assertEqual(audit.donor_files_inspected, 0)
        self.assertTrue(audit.all_contracts_verified)
        self.assertEqual(len(audit.checked_markers), 10)
        self.assertEqual(audit.missing_markers, ())
        for key, (expected_bytes, expected_sha) in p78.PINNED_DONOR_SHA256.items():
            self.assertEqual(audit.bytes_by_artifact[key], expected_bytes)
            self.assertEqual(audit.sha256_by_artifact[key], expected_sha)

    def test_02_force_clean_room_env_disables_local_donor_paths(self) -> None:
        env = {p78.ENV_FORCE_CLEAN_ROOM: "1"}
        self.assertTrue(p78.is_forced_clean_room(env))
        paths = p78.resolve_phase78_donor_paths(env=env)
        self.assertEqual(len(paths), 10)
        for path in paths.values():
            self.assertIn(p78.CLEAN_ROOM_SENTINEL_DIRNAME, str(path))
        audit = p78.inspect_touch_ciz_assignable_donors(env=env)
        self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_03_local_donor_o_rdonly_audit_when_present_or_clean_room(self) -> None:
        if p78.is_forced_clean_room():
            audit = p78.inspect_touch_ciz_assignable_donors()
            self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")
            return
        paths = p78.resolve_phase78_donor_paths()
        audit = p78.inspect_touch_ciz_assignable_donors()
        self.assertTrue(audit.all_contracts_verified)
        if all(p.is_file() for p in paths.values()):
            self.assertEqual(audit.source_mode, "LOCAL_DONOR_RDONLY")
            self.assertEqual(audit.donor_files_inspected, 10)
            for key, (expected_bytes, expected_sha) in p78.PINNED_DONOR_SHA256.items():
                self.assertEqual(audit.bytes_by_artifact[key], expected_bytes)
                self.assertEqual(audit.sha256_by_artifact[key], expected_sha)
        else:
            self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_04_missing_donor_root_falls_back_to_clean_room(self) -> None:
        env = {
            p78.ENV_MAC_WORK_ROOT: "/nonexistent_phase78_mac_work_root",
            p78.ENV_MAIN_LAB_WORK_ROOT: "/nonexistent_phase78_main_work_root",
        }
        audit = p78.inspect_touch_ciz_assignable_donors(force_clean_room=True, env=env)
        self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(audit.all_contracts_verified)

    def test_05_redlines_zero_mutations_zero_nvram_and_zero_gpio_derefs(self) -> None:
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
        self.assertEqual(red["null_gpio_derefs"], 0)
        self.assertEqual(red["mailbox_stalls"], 0)
        self.assertFalse(red["persistent_emmc_writes_authorized"])
        self.assertEqual(red["donor_access_mode"], "O_RDONLY")


class TestEvdevTouchAf627PdafAndAnamorphic(unittest.TestCase):
    """Verify Linux evdev -> IMX510 627-pt (33x19) PDAF mapping, desqueeze & Focus Magnifier."""

    def test_06_evdev_packet_encode_decode_roundtrip(self) -> None:
        pkt = p78.encode_evdev_touch_packet(x_px=640, y_px=216, tracking_id=7, btn_down=True, timestamp_ms=4250)
        self.assertEqual(len(pkt), 5 * 24)
        dec = p78.decode_evdev_touch_packet(pkt)
        self.assertEqual(dec["event_count"], 5)
        self.assertEqual(dec["tracking_id"], 7)
        self.assertEqual(dec["abs_mt_position_x"], 640)
        self.assertEqual(dec["abs_mt_position_y"], 216)
        self.assertEqual(dec["btn_touch"], 1)
        self.assertEqual(dec["syn_report"], 0)
        self.assertEqual(dec["timestamp_ms"], 4250)

    def test_07_center_touch_maps_to_center_627_pdaf_cell_313(self) -> None:
        res = p78.dispatch_evdev_touch_to_pdaf(touch_x_px=480.0, touch_y_px=270.0, event_kind=p78.TOUCH_EVENT_DOWN)
        self.assertTrue(res.accepted)
        self.assertEqual(res.status, "TOUCH_AF_PDAF_LOCKED")
        self.assertEqual(res.pdaf_col, 16)
        self.assertEqual(res.pdaf_row, 9)
        self.assertEqual(res.pdaf_point_index, 313)
        self.assertEqual(res.pdaf_total_points, 627)
        self.assertEqual(res.pdaf_coverage_pct, 95.0)
        self.assertTrue(res.mhlx_dispatched)
        self.assertEqual(res.mhlx_opcode_hex, "0x0310")
        self.assertEqual(res.cp_ack_opcode_hex, "0x8310")
        self.assertEqual(res.mailbox_stalls, 0)
        self.assertEqual(res.cp_mutation_bytes, 0)

    def test_08_pdaf_33x19_grid_boundaries_with_95pct_coverage(self) -> None:
        tl = p78.dispatch_evdev_touch_to_pdaf(touch_x_px=0.0, touch_y_px=0.0)
        br = p78.dispatch_evdev_touch_to_pdaf(touch_x_px=960.0, touch_y_px=540.0)
        self.assertEqual((tl.pdaf_col, tl.pdaf_row, tl.pdaf_point_index), (0, 0, 0))
        self.assertEqual((br.pdaf_col, br.pdaf_row, br.pdaf_point_index), (32, 18, 626))

    def test_09_touch_drag_dispatches_mhlx_0x0311_tracking_update(self) -> None:
        res = p78.dispatch_evdev_touch_to_pdaf(
            touch_x_px=720.0,
            touch_y_px=135.0,
            event_kind=p78.TOUCH_EVENT_DRAG,
        )
        self.assertTrue(res.accepted)
        self.assertEqual(res.status, "TOUCH_TRACKING_UPDATED")
        self.assertEqual(res.mhlx_opcode_hex, "0x0311")
        self.assertEqual(res.cp_ack_opcode_hex, "0x8311")
        self.assertGreater(res.pdaf_col, 16)
        self.assertLess(res.pdaf_row, 9)
        self.assertEqual(res.mailbox_stalls, 0)

    def test_10_double_tap_cancel_clears_tracking_via_mhlx_0x0312(self) -> None:
        res = p78.dispatch_evdev_touch_to_pdaf(
            touch_x_px=640.0,
            touch_y_px=216.0,
            event_kind=p78.TOUCH_EVENT_DOUBLE_TAP_CANCEL,
            tap_interval_ms=150,
        )
        self.assertTrue(res.accepted)
        self.assertEqual(res.status, "TOUCH_TRACKING_CANCELLED")
        self.assertEqual(res.mhlx_opcode_hex, "0x0312")
        self.assertEqual(res.cp_ack_opcode_hex, "0x8312")
        self.assertEqual(res.pdaf_point_index, 313)

    def test_11_anamorphic_1_3x_inverse_mapping_and_letterbox_matte_rejection(self) -> None:
        # 1.3x letterbox active y range inside 540px: [62.3077 .. 477.6923]
        active = p78.dispatch_evdev_touch_to_pdaf(
            touch_x_px=480.0,
            touch_y_px=166.1538,
            desqueeze_factor=1.3,
        )
        self.assertTrue(active.accepted)
        self.assertFalse(active.in_letterbox_matte)
        self.assertAlmostEqual(active.sensor_u, 0.5, places=4)
        self.assertAlmostEqual(active.sensor_v, 0.25, places=3)

        top_matte = p78.dispatch_evdev_touch_to_pdaf(touch_x_px=480.0, touch_y_px=30.0, desqueeze_factor=1.3)
        bot_matte = p78.dispatch_evdev_touch_to_pdaf(touch_x_px=480.0, touch_y_px=510.0, desqueeze_factor=1.3)
        for rej in (top_matte, bot_matte):
            self.assertFalse(rej.accepted)
            self.assertTrue(rej.in_letterbox_matte)
            self.assertEqual(rej.status, "OUTSIDE_ACTIVE_IMAGE_LETTERBOX_IGNORED")
            self.assertFalse(rej.mhlx_dispatched)
            self.assertEqual(rej.pdaf_point_index, -1)

    def test_12_anamorphic_2_0x_inverse_mapping_and_letterbox_matte_rejection(self) -> None:
        # 2.0x letterbox active y range inside 540px: [135.0 .. 405.0]
        active = p78.dispatch_evdev_touch_to_pdaf(
            touch_x_px=720.0,
            touch_y_px=202.5,
            desqueeze_factor=2.0,
        )
        self.assertTrue(active.accepted)
        self.assertFalse(active.in_letterbox_matte)
        self.assertAlmostEqual(active.sensor_u, 0.75, places=6)
        self.assertAlmostEqual(active.sensor_v, 0.25, places=6)

        edge_bottom = p78.dispatch_evdev_touch_to_pdaf(
            touch_x_px=960.0,
            touch_y_px=405.0,
            desqueeze_factor=2.0,
        )
        self.assertTrue(edge_bottom.accepted)
        self.assertAlmostEqual(edge_bottom.sensor_u, 1.0, places=6)
        self.assertAlmostEqual(edge_bottom.sensor_v, 1.0, places=6)

        for y_bad in (0.0, 100.0, 134.0, 406.0, 540.0):
            rej = p78.dispatch_evdev_touch_to_pdaf(
                touch_x_px=480.0,
                touch_y_px=y_bad,
                desqueeze_factor=2.0,
            )
            self.assertFalse(rej.accepted)
            self.assertTrue(rej.in_letterbox_matte)
            self.assertEqual(rej.status, "OUTSIDE_ACTIVE_IMAGE_LETTERBOX_IGNORED")
            self.assertFalse(rej.mhlx_dispatched)

    def test_13_focus_magnifier_4x_composed_with_anamorphic_2_0x(self) -> None:
        res = p78.dispatch_evdev_touch_to_pdaf(
            touch_x_px=720.0,
            touch_y_px=270.0,
            desqueeze_factor=2.0,
            magnifier_scale=4.0,
            magnifier_pan_norm=(0.5, 0.5),
        )
        self.assertTrue(res.accepted)
        # u_disp=0.75 -> pan 0.5 +/- 0.125 -> 0.375 + 0.75*0.25 = 0.5625
        self.assertAlmostEqual(res.sensor_u, 0.5625, places=6)
        self.assertAlmostEqual(res.sensor_v, 0.5, places=6)
        self.assertEqual(res.lcd_gpe0_crop_scale, 4.0)
        self.assertEqual(res.xavc_recorded_crop_scale, 1.0)
        self.assertEqual(res.hdmi_raw16_clean_feed_crop_scale, 1.0)
        self.assertTrue(res.clean_feed_invariant)

    def test_14_focus_magnifier_cycle_x1_x4_pan_x1_preserves_clean_feed(self) -> None:
        cyc = p78.simulate_focus_magnifier_cycle(
            initial_pdaf_norm=(0.62, 0.42),
            pan_target_norm=(0.95, 0.05),
            auto_exit_on_rec_start=True,
        )
        self.assertTrue(cyc.passed)
        self.assertTrue(cyc.magnifier_toggled_x1_to_x4_to_x1)
        self.assertTrue(cyc.pan_clamped_cleanly)
        self.assertTrue(cyc.clean_feed_invariant)
        self.assertEqual(cyc.xavc_recorded_crop_scale, 1.0)
        self.assertEqual(cyc.hdmi_raw16_clean_feed_crop_scale, 1.0)
        self.assertTrue(cyc.auto_exit_on_rec_start_ok)
        self.assertEqual(cyc.states[2]["pan_center_norm"], [0.875, 0.125])
        self.assertEqual(cyc.mailbox_stalls, 0)
        self.assertEqual(cyc.cp_mutation_bytes, 0)

    def test_15_focus_magnifier_manual_toggle_exit_without_rec_auto_exit(self) -> None:
        cyc = p78.simulate_focus_magnifier_cycle(auto_exit_on_rec_start=False)
        self.assertTrue(cyc.passed)
        self.assertEqual(cyc.states[-1]["step"], "MAG_1_0X_EXIT_TOGGLE")
        self.assertEqual(cyc.states[-1]["lcd_gpe0_crop_scale"], 1.0)

    def test_16_invalid_touch_evdev_or_desqueeze_bounds_rejected(self) -> None:
        with self.assertRaises(p78.TouchAfCizEmulatorError):
            p78.dispatch_evdev_touch_to_pdaf(touch_x_px=961.0, touch_y_px=270.0)
        with self.assertRaises(p78.TouchAfCizEmulatorError):
            p78.dispatch_evdev_touch_to_pdaf(touch_x_px=480.0, touch_y_px=-1.0)
        with self.assertRaises(p78.TouchAfCizEmulatorError):
            p78.dispatch_evdev_touch_to_pdaf(touch_x_px=480.0, touch_y_px=270.0, desqueeze_factor=1.8)
        with self.assertRaises(p78.TouchAfCizEmulatorError):
            p78.dispatch_evdev_touch_to_pdaf(touch_x_px=480.0, touch_y_px=270.0, magnifier_scale=3.0)
        with self.assertRaises(p78.TouchAfCizEmulatorError):
            p78.decode_evdev_touch_packet(b"\x00" * 10)


class TestTwZoomRockerAndCizArbitrator(unittest.TestCase):
    """Verify T/W 8-step rocker, Optical->CIZ->Digital transitions, and RAW16/S&Q exclusions."""

    def test_17_optical_pz_to_4k_ciz_1_5x_retains_627_pdaf_and_eye_tracking(self) -> None:
        res = p78.simulate_tw_zoom_rocker_and_ciz(
            lens_id="SELP1635G",
            resolution_mode=p78.ZOOM_RES_4K_QFHD,
            rocker_speed=4,
            target_electronic_scale=1.50,
        )
        self.assertTrue(res.passed)
        self.assertEqual(res.status, "CIZ_SUPER_RES_PDAF_ACTIVE")
        self.assertEqual(res.final_zoom_stage, p78.ZOOM_STAGE_CLEAR_IMAGE_ZOOM)
        self.assertEqual(res.final_optical_focal_mm, 35.0)
        self.assertEqual(res.final_ciz_scale, 1.5)
        self.assertTrue(res.optical_pz_verified)
        self.assertTrue(res.ciz_pdaf_retained_verified)
        self.assertTrue(res.final_pdaf_627_active)
        self.assertTrue(res.final_eye_tracking_retained)
        self.assertEqual(res.mailbox_stalls, 0)

    def test_18_fhd_ciz_2_0x_retains_pdaf_and_eye_tracking(self) -> None:
        res = p78.simulate_tw_zoom_rocker_and_ciz(
            lens_id="SELP1635G",
            resolution_mode=p78.ZOOM_RES_FHD,
            rocker_speed=8,
            target_electronic_scale=2.00,
        )
        self.assertTrue(res.passed)
        self.assertEqual(res.max_ciz_scale, 2.0)
        self.assertEqual(res.final_ciz_scale, 2.0)
        self.assertTrue(res.final_pdaf_627_active)
        self.assertTrue(res.final_eye_tracking_retained)
        self.assertEqual(res.final_af_area_mode, "CIZ_TRACKING_PDAF_RETAINED")

    def test_19_digital_zoom_beyond_ciz_switches_af_area_to_center_spot(self) -> None:
        res = p78.simulate_tw_zoom_rocker_and_ciz(
            lens_id="SELP1635G",
            resolution_mode=p78.ZOOM_RES_4K_DCI,
            rocker_speed=6,
            target_electronic_scale=3.00,
        )
        self.assertTrue(res.passed)
        self.assertEqual(res.status, "DIGITAL_ZOOM_CENTER_SPOT_ACTIVE")
        self.assertEqual(res.final_zoom_stage, p78.ZOOM_STAGE_DIGITAL_ZOOM)
        self.assertEqual(res.final_digital_scale, 3.0)
        self.assertTrue(res.digital_center_spot_switch_verified)
        self.assertFalse(res.final_pdaf_627_active)
        self.assertFalse(res.final_eye_tracking_retained)
        self.assertEqual(res.final_af_area_mode, "CENTER_SPOT_CONTRAST_ONLY")

    def test_20_all_8_tw_rocker_speeds_monotonic_velocities(self) -> None:
        prev_pz = 0.0
        prev_ciz = 0.0
        for spd in range(1, 9):
            res = p78.simulate_tw_zoom_rocker_and_ciz(
                rocker_speed=spd,
                target_electronic_scale=1.50,
            )
            self.assertTrue(res.passed)
            self.assertGreater(res.pz_optical_velocity_mm_s, prev_pz)
            self.assertGreater(res.ciz_rate_per_s, prev_ciz)
            prev_pz = res.pz_optical_velocity_mm_s
            prev_ciz = res.ciz_rate_per_s

    def test_21_hdmi_raw16_toggle_clamps_ciz_smoothly_to_1_00x(self) -> None:
        res = p78.simulate_tw_zoom_rocker_and_ciz(
            resolution_mode=p78.ZOOM_RES_4K_QFHD,
            target_electronic_scale=1.50,
            hdmi_raw16_enabled=True,
        )
        self.assertTrue(res.passed)
        self.assertTrue(res.ciz_clamped_by_mode_exclusion)
        self.assertEqual(res.status, "CIZ_CLAMPED_BY_MODE_EXCLUSION")
        self.assertEqual(res.exclusion_reason, "HDMI_RAW16_ACTIVE")
        self.assertEqual(res.final_ciz_scale, 1.0)
        self.assertEqual(res.final_digital_scale, 1.0)
        self.assertTrue(res.final_pdaf_627_active)
        self.assertEqual(res.mailbox_stalls, 0)

    def test_22_sq_120fps_and_240fps_clamp_ciz_smoothly_to_1_00x(self) -> None:
        for fps in (120.0, 240.0):
            res = p78.simulate_tw_zoom_rocker_and_ciz(
                resolution_mode=p78.ZOOM_RES_FHD,
                target_electronic_scale=2.00,
                sq_active=True,
                sq_fps=fps,
            )
            self.assertTrue(res.passed)
            self.assertTrue(res.ciz_clamped_by_mode_exclusion)
            self.assertEqual(res.status, "CIZ_CLAMPED_BY_MODE_EXCLUSION")
            self.assertIn(f"SQ_{int(fps)}FPS_ACTIVE", res.exclusion_reason or "")
            self.assertEqual(res.final_ciz_scale, 1.0)
            self.assertEqual(res.mailbox_stalls, 0)

    def test_23_sq_60p_does_not_clamp_ciz(self) -> None:
        res = p78.simulate_tw_zoom_rocker_and_ciz(
            resolution_mode=p78.ZOOM_RES_4K_QFHD,
            target_electronic_scale=1.50,
            sq_active=True,
            sq_fps=59.94,
        )
        self.assertTrue(res.passed)
        self.assertFalse(res.ciz_clamped_by_mode_exclusion)
        self.assertEqual(res.final_ciz_scale, 1.5)

    def test_24_invalid_zoom_rocker_parameters_rejected(self) -> None:
        with self.assertRaises(p78.TouchAfCizEmulatorError):
            p78.simulate_tw_zoom_rocker_and_ciz(lens_id="UNKNOWN_LENS")
        with self.assertRaises(p78.TouchAfCizEmulatorError):
            p78.simulate_tw_zoom_rocker_and_ciz(rocker_speed=9)
        with self.assertRaises(p78.TouchAfCizEmulatorError):
            p78.simulate_tw_zoom_rocker_and_ciz(target_electronic_scale=4.5)
        with self.assertRaises(p78.TouchAfCizEmulatorError):
            p78.simulate_tw_zoom_rocker_and_ciz(resolution_mode="8K_RAW")


class TestAssignableButtonAndBig6Dispatcher(unittest.TestCase):
    """Verify Custom 1..6 + Lens Hold + XLR-H1 + Big6 shadow & hardware-absent containment."""

    def test_25_all_fx3_hardware_backed_buttons_update_runtime_state(self) -> None:
        rep = p78.simulate_assignable_dispatcher_suite()
        self.assertTrue(rep.passed)
        st = rep.final_camera_state
        self.assertEqual(st["cine_ei_base_iso"], 12800)
        self.assertTrue(st["zebra_enabled"])
        self.assertTrue(st["peaking_enabled"])
        self.assertTrue(st["sq_enabled"])
        self.assertEqual(st["focus_magnifier_scale"], 4.0)
        self.assertTrue(st["status_check_overlay"])
        self.assertFalse(st["big6_home_visible"])  # toggled from True -> False
        self.assertTrue(st["lens_focus_hold"])
        self.assertTrue(st["xlr_h1_monitor_active"])

    def test_26_xlr_h1_handle_redirects_safely_with_zero_gpio_access(self) -> None:
        ev, st = p78.dispatch_assignable_button(button_id="XLR_H1_HANDLE", action_id="XLR_H1_AUDIO_STATUS")
        self.assertEqual(ev.status, "DISPATCHED_HARDWARE_BACKED")
        self.assertFalse(ev.gpio_access_attempted)
        self.assertEqual(ev.null_gpio_derefs, 0)
        self.assertTrue(st["xlr_h1_monitor_active"])

    def test_27_absent_fx6_actions_return_contained_noop_toast_zero_faults(self) -> None:
        rep = p78.simulate_assignable_dispatcher_suite()
        self.assertEqual(len(rep.absent_hw_contained_dispatches), 3)
        for ev in rep.absent_hw_contained_dispatches:
            self.assertEqual(ev.status, "CONTAINED_NO_OP_TOAST")
            self.assertFalse(ev.hardware_backed)
            self.assertFalse(ev.gpio_access_attempted)
            self.assertEqual(ev.null_gpio_derefs, 0)
            self.assertEqual(ev.bk4_persistent_nvram_writes, 0)
            self.assertEqual(ev.cp_mutation_bytes, 0)
            self.assertFalse(ev.persistent_emmc_writes_authorized)
            self.assertIn("Hardware Absent", ev.toast_message)

    def test_28_big6_volatile_ram_shadow_and_nvram_write_block(self) -> None:
        rep = p78.simulate_assignable_dispatcher_suite()
        self.assertEqual(rep.big6_volatile_shadow_path, p78.VOLATILE_BIG6_SHADOW_PATH)
        self.assertEqual(len(rep.big6_volatile_shadow_sha256), 64)
        self.assertEqual(rep.persistent_write_blocked_status, "BLOCKED_PERSISTENT_BK4_NVRAM_WRITE")
        self.assertEqual(rep.bk4_persistent_nvram_writes, 0)
        self.assertFalse(rep.persistent_emmc_writes_authorized)

        for bad_path in ("/dev/nflasha15", "/dev/cnflasha0", "bk4://persistent/camset"):
            with self.assertRaises(p78.TouchAfCizEmulatorError):
                p78.simulate_assignable_dispatcher_suite(shadow_target_path=bad_path)

    def test_29_base_iso_toggle_roundtrip_800_12800_800(self) -> None:
        ev1, s1 = p78.dispatch_assignable_button(button_id="CUSTOM_5", action_id="BASE_ISO_800_12800")
        ev2, s2 = p78.dispatch_assignable_button(
            button_id="CUSTOM_5", action_id="BASE_ISO_800_12800", camera_state=s1
        )
        self.assertEqual(ev1.status, "DISPATCHED_HARDWARE_BACKED")
        self.assertEqual(s1["cine_ei_base_iso"], 12800)
        self.assertEqual(ev2.status, "DISPATCHED_HARDWARE_BACKED")
        self.assertEqual(s2["cine_ei_base_iso"], 800)

    def test_30_invalid_assignable_button_or_action_rejected(self) -> None:
        with self.assertRaises(p78.TouchAfCizEmulatorError):
            p78.dispatch_assignable_button(button_id="HANDLE_ASSIGN_9", action_id="ZEBRA_TOGGLE")
        with self.assertRaises(p78.TouchAfCizEmulatorError):
            p78.dispatch_assignable_button(button_id="CUSTOM_1", action_id="NONEXISTENT_ACTION")


class TestStage11SuiteIntegrationAndCli(unittest.TestCase):
    """Verify Stage 11 wiring in fx3_vm_coemulation_suite.py, CLI flags, and source hygiene."""

    def test_31_coemulation_suite_includes_stage11_and_skip_phase78_backward_compat(self) -> None:
        rep_full = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig(force_clean_room=True))
        self.assertTrue(rep_full["all_checks_passed"])
        self.assertIn("stage11_phase78_touchaf_ciz_assignable", rep_full)
        s11 = rep_full["stage11_phase78_touchaf_ciz_assignable"]
        self.assertTrue(s11["all_checks_passed"])
        self.assertEqual(s11["cp_mutation_bytes"], 0)
        self.assertEqual(s11["bk4_persistent_nvram_writes"], 0)
        self.assertEqual(s11["null_gpio_derefs"], 0)
        self.assertEqual(s11["mailbox_stalls"], 0)
        self.assertFalse(s11["persistent_emmc_writes_authorized"])

        rep_skip = suite.run_fx3_vm_coemulation_suite(
            suite.CoEmulationConfig(force_clean_room=True, include_phase78_touchaf_ciz_assignable=False)
        )
        self.assertTrue(rep_skip["all_checks_passed"])
        self.assertNotIn("stage11_phase78_touchaf_ciz_assignable", rep_skip)

    def test_32_clean_room_audit_digest_reproducible_and_valid_json(self) -> None:
        rep1 = p78.run_phase78_touchaf_ciz_assignable_audit(force_clean_room=True)
        rep2 = p78.run_phase78_touchaf_ciz_assignable_audit(force_clean_room=True)
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
            ["--clean-room", "--touch-matrix"],
            ["--clean-room", "--ciz-matrix"],
            ["--clean-room", "--assignable-matrix"],
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = p78.main(argv)
            self.assertEqual(rc, 0, msg=f"CLI argv={argv} failed")
            self.assertTrue(buf.getvalue().strip())

    def test_34_suite_cli_summary_and_skip_phase78_flag(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        proc = subprocess.run(
            [
                sys.executable,
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
        self.assertIn("touchaf_ciz=CLEAN_ROOM_SYNTHETIC", proc.stdout)

        proc_skip = subprocess.run(
            [
                sys.executable,
                "-B",
                str(FX3_VM_DIR / "fx3_vm_coemulation_suite.py"),
                "--clean-room",
                "--skip-phase78",
                "--summary",
            ],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc_skip.returncode, 0, msg=proc_skip.stderr)
        self.assertNotIn("touchaf_ciz=", proc_skip.stdout)

    def test_35_json_output_determinism_without_bytes_repr_leakage(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = p78.main(["--clean-room", "--json"])
        self.assertEqual(rc, 0)
        rendered = buf.getvalue()
        self.assertNotRegex(rendered, r'(?<![0-9A-Za-z_/.-])b[\'"]')
        parsed = json.loads(rendered)
        self.assertEqual(parsed["schema"], p78.PHASE_78_SCHEMA)
        self.assertTrue(parsed["all_checks_passed"])

    def test_36_source_hygiene_o_rdonly_and_no_forbidden_writes_or_port(self) -> None:
        forbidden_port = "87" + "68"
        emu_src = (FX3_VM_DIR / "touch_af_ciz_assignable_emulator.py").read_text(encoding="utf-8")
        test_src = Path(__file__).read_text(encoding="utf-8")

        self.assertIn("os.O_RDONLY", emu_src)
        self.assertNotIn("os.O_WRONLY", emu_src)
        self.assertNotIn("os.O_RDWR", emu_src)
        self.assertNotIn(forbidden_port, emu_src)
        self.assertNotIn(forbidden_port, test_src)
        self.assertIn("CP_MUTATION_BYTES = 0", emu_src)
        self.assertIn("BK4_PERSISTENT_NVRAM_WRITES = 0", emu_src)
        self.assertIn("NULL_GPIO_DEREFS = 0", emu_src)
        self.assertIn("PERSISTENT_EMMC_WRITES_AUTHORIZED = False", emu_src)


if __name__ == "__main__":
    unittest.main()
