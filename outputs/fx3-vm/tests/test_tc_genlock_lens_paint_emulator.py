#!/usr/bin/env python3
"""Phase 67 Test Suite — Stage 9 Multi-Camera SMPTE 12M TC `EXT-LK`,
E-Mount PZ Servo/Breathing/IBIS+OSS & `libpaint` 3x3 Color Matrix Co-Emulator.

Exercises 33 fast unit, protocol, math, Stage 9 integration, CLI, and
source-hygiene tests across BOTH Local Donor (`os.O_RDONLY`) and
`FX3_FX6_FORCE_CLEAN_ROOM=1` modes, strictly offline.
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import contextlib
import hashlib
import io
import json
import math
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
import tc_genlock_lens_paint_emulator as p67  # noqa: E402


_AUDIT_CACHE: dict = {}


def _get_clean_room_audit() -> dict:
    if "clean_room" not in _AUDIT_CACHE:
        _AUDIT_CACHE["clean_room"] = p67.run_phase67_tc_lens_paint_audit(force_clean_room=True)
    return _AUDIT_CACHE["clean_room"]


class TestPhase67DonorAuditAndRedlines(unittest.TestCase):
    """Verify O_RDONLY donor audit, clean-room fallback, and zero-mutation redlines."""

    def test_01_clean_room_donor_audit_verifies_all_10_artifacts_and_sha256(self) -> None:
        audit = p67.inspect_tc_lens_paint_donors(force_clean_room=True)
        self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(audit.access_mode, "O_RDONLY")
        self.assertEqual(audit.donor_files_inspected, 0)
        self.assertTrue(audit.all_contracts_verified)
        self.assertEqual(len(audit.checked_markers), 10)
        self.assertEqual(audit.missing_markers, ())
        for key, (expected_bytes, expected_sha) in p67.PINNED_DONOR_SHA256.items():
            self.assertEqual(audit.bytes_by_artifact[key], expected_bytes)
            self.assertEqual(audit.sha256_by_artifact[key], expected_sha)

    def test_02_force_clean_room_env_disables_local_donor_paths(self) -> None:
        env = {p67.ENV_FORCE_CLEAN_ROOM: "1"}
        self.assertTrue(p67.is_forced_clean_room(env))
        paths = p67.resolve_phase67_donor_paths(env=env)
        self.assertEqual(len(paths), 10)
        for path in paths.values():
            self.assertIn(p67.CLEAN_ROOM_SENTINEL_DIRNAME, str(path))
        audit = p67.inspect_tc_lens_paint_donors(env=env)
        self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_03_local_donor_o_rdonly_audit_when_present_or_clean_room(self) -> None:
        if p67.is_forced_clean_room():
            audit = p67.inspect_tc_lens_paint_donors()
            self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")
            return
        paths = p67.resolve_phase67_donor_paths()
        audit = p67.inspect_tc_lens_paint_donors()
        self.assertTrue(audit.all_contracts_verified)
        if all(p.is_file() for p in paths.values()):
            self.assertEqual(audit.source_mode, "LOCAL_DONOR_RDONLY")
            self.assertEqual(audit.donor_files_inspected, 10)
            for key, (expected_bytes, expected_sha) in p67.PINNED_DONOR_SHA256.items():
                self.assertEqual(audit.bytes_by_artifact[key], expected_bytes)
                self.assertEqual(audit.sha256_by_artifact[key], expected_sha)
        else:
            self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_04_missing_donor_root_falls_back_to_clean_room(self) -> None:
        env = {
            p67.ENV_MAC_WORK_ROOT: "/nonexistent_phase67_mac_work_root",
            p67.ENV_MAIN_LAB_WORK_ROOT: "/nonexistent_phase67_main_work_root",
        }
        audit = p67.inspect_tc_lens_paint_donors(force_clean_room=True, env=env)
        self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(audit.all_contracts_verified)

    def test_05_redlines_zero_mutations_zero_emmc_writes(self) -> None:
        rep = _get_clean_room_audit()
        red = rep["redlines"]
        self.assertTrue(red["p8_cp_mutation_forbidden"])
        self.assertEqual(red["nop_count"], 0)
        self.assertEqual(red["guest_code_modification_bytes"], 0)
        self.assertEqual(red["cp_mutation_bytes"], 0)
        self.assertEqual(red["wbi_mutation_bytes"], 0)
        self.assertEqual(red["calibration_mutation_bytes"], 0)
        self.assertEqual(red["nvram_persistent_writes"], 0)
        self.assertEqual(red["physical_device_writes"], 0)
        self.assertFalse(red["persistent_emmc_writes_authorized"])
        self.assertEqual(red["donor_access_mode"], "O_RDONLY")


class TestSmpte12mLtcAndExtLkGenlock(unittest.TestCase):
    """Verify SMPTE 12M 80-bit LTC framing, DF minute-10 math, TCXO drift & Phase 38 guard."""

    def test_06_2997_drop_frame_minute_1_and_minute_10_boundaries(self) -> None:
        # Minute 1..9 drop ;00 and ;01
        self.assertEqual(p67.frame_index_to_smpte_tc(1799, "29.97 DF").formatted, "00:00:59;29")
        self.assertEqual(p67.frame_index_to_smpte_tc(1800, "29.97 DF").formatted, "00:01:00;02")
        # Minute 10 (and 20, 30, 40, 50, 00) keep ;00 and ;01
        self.assertEqual(p67.frame_index_to_smpte_tc(17981, "29.97 DF").formatted, "00:09:59;29")
        self.assertEqual(p67.frame_index_to_smpte_tc(17982, "29.97 DF").formatted, "00:10:00;00")
        self.assertEqual(p67.frame_index_to_smpte_tc(17983, "29.97 DF").formatted, "00:10:00;01")
        # Minute 20 boundary
        self.assertEqual(p67.frame_index_to_smpte_tc(2 * 17982 - 1, "29.97 DF").formatted, "00:19:59;29")
        self.assertEqual(p67.frame_index_to_smpte_tc(2 * 17982, "29.97 DF").formatted, "00:20:00;00")
        # Hour 1 boundary (60 minutes -> divisible by 10)
        self.assertEqual(p67.frame_index_to_smpte_tc(6 * 17982 - 1, "29.97 DF").formatted, "00:59:59;29")
        self.assertEqual(p67.frame_index_to_smpte_tc(6 * 17982, "29.97 DF").formatted, "01:00:00;00")

    def test_07_2997_drop_frame_bijection_and_invalid_dropped_frame_rejected(self) -> None:
        for idx in (0, 1, 1799, 1800, 3597, 3598, 17981, 17982, 107891, 107892, 250000):
            tc = p67.frame_index_to_smpte_tc(idx, "29.97 DF")
            back = p67.smpte_tc_to_frame_index(tc.hours, tc.minutes, tc.seconds, tc.frames, "29.97 DF")
            self.assertEqual(back, idx)

        # ;00 and ;01 are forbidden at non-10th minutes in 29.97 DF
        with self.assertRaises(p67.SmpteTimecodeError):
            p67.smpte_tc_to_frame_index(0, 1, 0, 0, "29.97 DF")
        with self.assertRaises(p67.SmpteTimecodeError):
            p67.smpte_tc_to_frame_index(0, 9, 0, 1, "29.97 DF")
        # ;00 IS valid at minute 10
        self.assertEqual(p67.smpte_tc_to_frame_index(0, 10, 0, 0, "29.97 DF"), 17982)

    def test_08_5994_drop_frame_and_ndf_timebases(self) -> None:
        # 59.94 DF drops ;00..;03 at minute 1, keeps at minute 10
        self.assertEqual(p67.frame_index_to_smpte_tc(3599, "59.94 DF").formatted, "00:00:59;59")
        self.assertEqual(p67.frame_index_to_smpte_tc(3600, "59.94 DF").formatted, "00:01:00;04")
        self.assertEqual(p67.frame_index_to_smpte_tc(35963, "59.94 DF").formatted, "00:09:59;59")
        self.assertEqual(p67.frame_index_to_smpte_tc(35964, "59.94 DF").formatted, "00:10:00;00")
        with self.assertRaises(p67.SmpteTimecodeError):
            p67.smpte_tc_to_frame_index(0, 1, 0, 3, "59.94 DF")

        # 29.97 NDF and 59.94 NDF never drop frames
        self.assertEqual(p67.frame_index_to_smpte_tc(1800, "29.97 NDF").formatted, "00:01:00:00")
        self.assertEqual(p67.frame_index_to_smpte_tc(3600, "59.94 NDF").formatted, "00:01:00:00")

    def test_09_all_8_timebases_ltc_80bit_0x3ffd_forward_and_0xbffc_reverse(self) -> None:
        for tb_id in p67.SMPTE_TIMEBASE_SPECS:
            tc = p67.frame_index_to_smpte_tc(12345, tb_id)
            fwd_bytes = p67.encode_smpte_12m_ltc_80bit(tc, user_bits=0xCAFEBABE, reverse=False)
            rev_bytes = p67.encode_smpte_12m_ltc_80bit(tc, user_bits=0xCAFEBABE, reverse=True)
            self.assertEqual(len(fwd_bytes), 10)
            self.assertEqual(len(rev_bytes), 10)

            dec_fwd = p67.decode_smpte_12m_ltc_80bit(fwd_bytes, timebase=tb_id)
            dec_rev = p67.decode_smpte_12m_ltc_80bit(rev_bytes, timebase=tb_id)
            self.assertEqual(dec_fwd.direction, "FORWARD")
            self.assertEqual(dec_fwd.sync_word_hex, "0x3ffd")
            self.assertEqual(dec_rev.direction, "REVERSE")
            self.assertEqual(dec_rev.sync_word_hex, "0xbffc")
            self.assertEqual(dec_fwd.formatted, tc.formatted)
            self.assertEqual(dec_rev.formatted, tc.formatted)
            self.assertEqual(dec_fwd.user_bits_hex, "0xcafebabe")
            self.assertEqual(dec_rev.user_bits_hex, "0xcafebabe")
            self.assertTrue(dec_fwd.even_parity_ok)
            self.assertTrue(dec_rev.even_parity_ok)

    def test_10_corrupt_ltc_sync_word_and_bad_length_rejected(self) -> None:
        tc = p67.frame_index_to_smpte_tc(500, "23.98p")
        good = bytearray(p67.encode_smpte_12m_ltc_80bit(tc))
        good[-1] ^= 0xFF
        with self.assertRaises(p67.SmpteTimecodeError):
            p67.decode_smpte_12m_ltc_80bit(bytes(good), timebase="23.98p")
        with self.assertRaises(p67.SmpteTimecodeError):
            p67.decode_smpte_12m_ltc_80bit(bytes(good[:9]), timebase="23.98p")

    def test_11_ext_lk_zero_drift_vs_12h_free_run_tcxo_052_frame_drift(self) -> None:
        locked = p67.simulate_ext_lk_pll_and_drift(mode="EXT_LK_LOCKED", timebase="23.98p", shoot_hours=12.0)
        free_run = p67.simulate_ext_lk_pll_and_drift(mode="FREE_RUN", timebase="23.98p", shoot_hours=12.0)

        self.assertTrue(locked.passed)
        self.assertTrue(locked.pll_locked)
        self.assertEqual(locked.ext_tc_lock_status, "EXT_TC_LOCK_STATUS_LOCK")
        self.assertEqual(locked.ext_lk_drift_frames, 0.0)

        self.assertTrue(free_run.passed)
        self.assertFalse(free_run.pll_locked)
        self.assertAlmostEqual(free_run.free_run_drift_ms, 21.6, places=2)
        self.assertAlmostEqual(free_run.free_run_drift_frames, 0.5179, places=3)

    def test_12_bnc_unplug_6h_holdover_memory_stays_subframe(self) -> None:
        hold = p67.simulate_ext_lk_pll_and_drift(
            mode="BNC_UNPLUG_HOLDOVER",
            timebase="23.98p",
            holdover_hours=6.0,
        )
        self.assertTrue(hold.passed)
        self.assertEqual(hold.ext_tc_lock_status, "EXT_TC_LOCK_STATUS_PSEUDOLOCK")
        self.assertAlmostEqual(hold.holdover_drift_frames, 0.2589, places=3)
        self.assertLess(hold.holdover_drift_frames, 0.5)

    def test_13_phase38_uart_boot_electrical_isolation_blocks_ltc_when_latched(self) -> None:
        blocked_bootrom = p67.simulate_ext_lk_pll_and_drift(
            mode="EXT_LK_LOCKED",
            bootrom_uart_boot_latched=True,
            linux_userspace_ready=False,
        )
        self.assertTrue(blocked_bootrom.passed)
        self.assertEqual(blocked_bootrom.status, "BLOCKED_UART_BOOT_ELECTRICAL_ISOLATION")
        self.assertFalse(blocked_bootrom.ltc_input_enabled)
        self.assertFalse(blocked_bootrom.pll_locked)
        self.assertTrue(blocked_bootrom.uart_boot_isolation_enforced)

        blocked_pre_linux = p67.simulate_ext_lk_pll_and_drift(
            mode="EXT_LK_LOCKED",
            bootrom_uart_boot_latched=False,
            linux_userspace_ready=False,
        )
        self.assertEqual(blocked_pre_linux.status, "BLOCKED_UART_BOOT_ELECTRICAL_ISOLATION")
        self.assertFalse(blocked_pre_linux.ltc_input_enabled)

    def test_14_vmc_bncm1_680k_id_and_05_to_45_vpp_window_enforced(self) -> None:
        bad_id = p67.simulate_ext_lk_pll_and_drift(vmc_bncm1_id_ohm=p67.LANC_ID_RESISTOR_OHM)
        self.assertEqual(bad_id.status, "BLOCKED_WRONG_ID_RESISTOR_KEYING")
        self.assertFalse(bad_id.ltc_input_enabled)

        too_low = p67.simulate_ext_lk_pll_and_drift(ltc_vpp=0.3)
        self.assertEqual(too_low.status, "BLOCKED_LTC_VOLTAGE_OUT_OF_RANGE")
        self.assertFalse(too_low.ltc_input_enabled)

        too_high = p67.simulate_ext_lk_pll_and_drift(ltc_vpp=4.9)
        self.assertEqual(too_high.status, "BLOCKED_LTC_VOLTAGE_OUT_OF_RANGE")
        self.assertFalse(too_high.ltc_input_enabled)

        ok_edge = p67.simulate_ext_lk_pll_and_drift(ltc_vpp=0.5, vmc_bncm1_id_ohm=680_000)
        self.assertTrue(ok_edge.ltc_input_enabled)
        self.assertTrue(ok_edge.pll_locked)

    def test_15_timebase_alias_resolution_and_invalid_rejected(self) -> None:
        self.assertEqual(p67.resolve_timebase("23.976").timebase_id, "23.98p")
        self.assertEqual(p67.resolve_timebase("24p").timebase_id, "24.00p")
        self.assertEqual(p67.resolve_timebase("50p").timebase_id, "50.00p")
        with self.assertRaises(p67.SmpteTimecodeError):
            p67.resolve_timebase("14.98p")


class TestEMountPzBreathingAndIbisOss(unittest.TestCase):
    """Verify 8-speed PZ trapezoidal ramp, Breathing FOV LUT, and IBIS+OSS 5-axis split."""

    def test_16_selp1635g_8speed_pz_trapezoid_zero_overshoot_and_speed_ordering(self) -> None:
        prev_peak = 0.0
        for spd in range(1, 9):
            res = p67.simulate_power_zoom_trapezoid(
                lens_id="SELP1635G",
                start_focal_mm=16.0,
                target_focal_mm=35.0,
                pz_speed=spd,
            )
            self.assertTrue(res.passed, msg=f"PZ speed {spd} failed")
            self.assertTrue(res.monotonic)
            self.assertEqual(res.overshoot_mm, 0.0)
            self.assertAlmostEqual(res.final_focal_mm, 35.0, places=5)
            self.assertEqual(res.cp_mutation_bytes, 0)
            self.assertGreater(res.peak_velocity_mm_s, prev_peak)
            prev_peak = res.peak_velocity_mm_s

    def test_17_pz_zoom_out_reverse_and_zero_delta_trapezoid(self) -> None:
        zoom_out = p67.simulate_power_zoom_trapezoid(
            lens_id="SELP28135G",
            start_focal_mm=135.0,
            target_focal_mm=28.0,
            pz_speed=6,
        )
        self.assertTrue(zoom_out.passed)
        self.assertTrue(zoom_out.monotonic)
        self.assertEqual(zoom_out.overshoot_mm, 0.0)
        self.assertAlmostEqual(zoom_out.final_focal_mm, 28.0, places=5)

        same = p67.simulate_power_zoom_trapezoid(
            lens_id="SELP1635G",
            start_focal_mm=24.0,
            target_focal_mm=24.0,
            pz_speed=3,
        )
        self.assertTrue(same.passed)
        self.assertEqual(same.duration_s, 0.0)

    def test_18_pz_rejects_prime_lens_and_invalid_speed_or_bounds(self) -> None:
        with self.assertRaises(p67.LensEmulatorError):
            p67.simulate_power_zoom_trapezoid(lens_id="SEL35F14GM", start_focal_mm=35.0, target_focal_mm=35.0)
        with self.assertRaises(p67.LensEmulatorError):
            p67.simulate_power_zoom_trapezoid(lens_id="SELP1635G", pz_speed=9)
        with self.assertRaises(p67.LensEmulatorError):
            p67.simulate_power_zoom_trapezoid(lens_id="SELP1635G", start_focal_mm=12.0, target_focal_mm=35.0)

    def test_19_breathing_fov_scale_1000_to_1075_interpolation(self) -> None:
        s_inf = p67.compute_breathing_fov_scale(lens_id="SELP1635G", focal_length_mm=35.0, focus_distance_m=math.inf)
        s_mid = p67.compute_breathing_fov_scale(lens_id="SELP1635G", focal_length_mm=24.0, focus_distance_m=0.70)
        s_near = p67.compute_breathing_fov_scale(lens_id="SELP1635G", focal_length_mm=35.0, focus_distance_m=0.28)
        s_off = p67.compute_breathing_fov_scale(
            lens_id="SELP1635G", focal_length_mm=35.0, focus_distance_m=0.28, enabled=False
        )

        self.assertEqual(s_inf, 1.000)
        self.assertEqual(s_off, 1.000)
        self.assertGreater(s_mid, 1.000)
        self.assertLess(s_mid, s_near)
        self.assertAlmostEqual(s_near, 1.075, places=6)

    def test_20_rtmd_0xe304_breathing_metadata_roundtrip(self) -> None:
        rtmd = p67.encode_rtmd_breathing_metadata(
            lens_id="SELP1635G",
            focal_length_mm=35.0,
            focus_distance_m=0.28,
            enabled=True,
        )
        self.assertTrue(rtmd.rtmd_roundtrip_ok)
        self.assertAlmostEqual(rtmd.rtmd_decoded_scale, 1.075, places=6)
        self.assertTrue(rtmd.rtmd_e304_hex.startswith("e304"))
        self.assertEqual(rtmd.cropped_width % 2, 0)
        self.assertEqual(rtmd.cropped_height % 2, 0)
        self.assertLess(rtmd.cropped_width, 4264)
        self.assertLess(rtmd.cropped_height, 2408)

    def test_21_ibis_non_oss_selp1635g_covers_all_5_body_axes(self) -> None:
        res_act = p67.arbitrate_ibis_oss_fusion(lens_id="SELP1635G", ibis_mode="Active")
        res_std = p67.arbitrate_ibis_oss_fusion(lens_id="SELP1635G", ibis_mode="Standard")
        self.assertTrue(res_act.passed)
        self.assertTrue(res_std.passed)
        self.assertFalse(res_act.lens_has_oss)
        self.assertEqual(res_act.oss_axes, ())
        self.assertEqual(res_act.body_ibis_axes, p67.ALL_IBIS_AXES)
        self.assertEqual(res_act.total_stabilized_axes, 5)
        self.assertEqual(res_act.active_eis_crop_factor, 1.10)
        self.assertEqual(res_std.active_eis_crop_factor, 1.00)

    def test_22_ibis_oss_selp28135g_splits_pitch_yaw_and_roll_xy(self) -> None:
        res = p67.arbitrate_ibis_oss_fusion(lens_id="SELP28135G", ibis_mode="Standard")
        self.assertTrue(res.passed)
        self.assertTrue(res.lens_has_oss)
        self.assertEqual(res.oss_axes, ("pitch", "yaw"))
        self.assertEqual(res.body_ibis_axes, ("roll", "shift_x", "shift_y"))
        self.assertEqual(res.total_stabilized_axes, 5)
        self.assertEqual(res.cp_mutation_bytes, 0)
        self.assertEqual(res.calibration_mutation_bytes, 0)

    def test_23_ibis_off_keeps_0x0400_center_lock_energized_and_rejects_invalid(self) -> None:
        off = p67.arbitrate_ibis_oss_fusion(lens_id="SELP28135G", ibis_mode="Off")
        self.assertTrue(off.passed)
        self.assertEqual(off.cp_opcode_hex, "0x0400")
        self.assertEqual(off.cp_ack_opcode_hex, "0x1400")
        self.assertTrue(off.center_lock_energized)
        self.assertEqual(off.total_stabilized_axes, 0)

        with self.assertRaises(p67.LensEmulatorError):
            p67.arbitrate_ibis_oss_fusion(lens_id="UNKNOWN_LENS", ibis_mode="Active")
        with self.assertRaises(p67.LensEmulatorError):
            p67.arbitrate_ibis_oss_fusion(lens_id="SELP1635G", ibis_mode="Turbo")


class TestLibpaintCinemaColorPipeline(unittest.TestCase):
    """Verify S-Log3 OETF/EOTF, S-Cinetone Knee, 3x3 Paint Matrix, and RAW16 MLUT bypass."""

    def test_24_exact_sony_slog3_oetf_key_points_and_continuity(self) -> None:
        self.assertAlmostEqual(p67.slog3_oetf_encode(0.0) * 1023.0, 95.0, places=6)
        self.assertAlmostEqual(p67.slog3_oetf_encode(0.18) * 1023.0, 420.0, places=6)
        self.assertAlmostEqual(p67.slog3_oetf_encode(0.90) * 1023.0, 597.8952, places=3)

        # Verify exact continuity across the 0.01125000 linear/log piecewise threshold
        below = p67.slog3_oetf_encode(0.01125000 - 1e-9)
        at_thresh = p67.slog3_oetf_encode(0.01125000)
        self.assertAlmostEqual(below, at_thresh, places=7)

    def test_25_slog3_inverse_eotf_roundtrip(self) -> None:
        for lin in (0.0, 0.004, 0.01125, 0.05, 0.18, 0.45, 0.90, 1.0):
            y = p67.slog3_oetf_encode(lin)
            back = p67.slog3_eotf_decode(y)
            self.assertAlmostEqual(back, lin, places=7, msg=f"S-Log3 roundtrip failed at x={lin}")

    def test_26_scinetone_knee_highlight_rolloff(self) -> None:
        no_knee = p67.scinetone_oetf_encode(0.95, knee_enabled=False)
        with_knee = p67.scinetone_oetf_encode(0.95, knee_enabled=True, knee_point_pct=85.0, knee_slope=0.25)
        self.assertLess(with_knee, no_knee)
        self.assertGreater(with_knee, 0.80)

    def test_27_3x3_paint_matrix_white_point_preservation_and_bad_row_rejected(self) -> None:
        for name, mat in p67.PAINT_MATRICES.items():
            sums = mat.validate_white_point()
            for s in sums:
                self.assertAlmostEqual(s, 1.0, places=9, msg=f"{name} row sum != 1.0")
            gray = (0.41055718, 0.41055718, 0.41055718)
            out = p67.apply_3x3_paint_matrix(gray, mat)
            for i in range(3):
                self.assertAlmostEqual(out[i], gray[i], places=9)

        bad_mat = p67.PaintMatrix3x3(
            name="BROKEN_WP",
            rows=((1.05, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
        )
        with self.assertRaises(p67.PaintMatrixError):
            bad_mat.validate_white_point()

    def test_28_hdmi_raw16_bypasses_mlut_and_paint_matrix_exactly(self) -> None:
        raw_px = (12345, 23456, 34567)
        res = p67.run_libpaint_color_pipeline(
            imx510_raw16_rgb=raw_px,
            color_mode=p67.COLOR_MODE_SLOG3,
            output_path=p67.PAINT_OUTPUT_HDMI_RAW16,
            mlut_on=False,
            matrix_name="SGAMUT3_CINE_TO_709_PAINT",
        )
        self.assertTrue(res.passed)
        self.assertTrue(res.raw_bypass_exact)
        self.assertFalse(res.mlut_baked)
        self.assertEqual(res.raw16_passthrough_output, raw_px)
        self.assertEqual(res.calibration_mutation_bytes, 0)
        self.assertFalse(res.persistent_emmc_writes_authorized)

    def test_29_hdmi_422_10bit_mlut_on_vs_off_and_sdi_containment(self) -> None:
        res_off = p67.run_libpaint_color_pipeline(
            imx510_raw16_rgb=(11_796, 11_796, 11_796),
            color_mode=p67.COLOR_MODE_SCINETONE,
            output_path=p67.PAINT_OUTPUT_HDMI_422_10BIT,
            mlut_on=False,
            matrix_name="S_CINETONE_CINEMA",
        )
        res_on = p67.run_libpaint_color_pipeline(
            imx510_raw16_rgb=(11_796, 11_796, 11_796),
            color_mode=p67.COLOR_MODE_SCINETONE,
            output_path=p67.PAINT_OUTPUT_HDMI_422_10BIT,
            mlut_on=True,
            matrix_name="S_CINETONE_CINEMA",
        )
        self.assertTrue(res_off.passed)
        self.assertTrue(res_on.passed)
        self.assertFalse(res_off.mlut_baked)
        self.assertTrue(res_on.mlut_baked)
        self.assertTrue(res_on.sdi_contained_noop)
        self.assertTrue(res_on.white_point_preserved)
        self.assertNotEqual(res_off.encoded_10bit_output, res_on.encoded_10bit_output)


class TestStage9SuiteIntegrationAndCli(unittest.TestCase):
    """Verify Stage 9 wiring in fx3_vm_coemulation_suite.py, CLI flags, and source hygiene."""

    def test_30_coemulation_suite_includes_stage9_and_skip_phase67_backward_compat(self) -> None:
        rep_full = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig(force_clean_room=True))
        self.assertTrue(rep_full["all_checks_passed"])
        self.assertIn("stage9_phase67_tc_lens_paint", rep_full)
        s9 = rep_full["stage9_phase67_tc_lens_paint"]
        self.assertTrue(s9["all_checks_passed"])
        self.assertEqual(s9["cp_mutation_bytes"], 0)
        self.assertEqual(s9["calibration_mutation_bytes"], 0)
        self.assertFalse(s9["persistent_emmc_writes_authorized"])

        rep_skip = suite.run_fx3_vm_coemulation_suite(
            suite.CoEmulationConfig(force_clean_room=True, include_phase67_tc_lens_paint=False)
        )
        self.assertTrue(rep_skip["all_checks_passed"])
        self.assertNotIn("stage9_phase67_tc_lens_paint", rep_skip)

    def test_31_clean_room_audit_digest_reproducible_and_valid_json(self) -> None:
        rep1 = p67.run_phase67_tc_lens_paint_audit(force_clean_room=True)
        rep2 = p67.run_phase67_tc_lens_paint_audit(force_clean_room=True)
        self.assertEqual(rep1["audit_digest_sha256"], rep2["audit_digest_sha256"])

        rendered = json.dumps(rep1, allow_nan=False)
        self.assertNotRegex(rendered, r'(?<![0-9A-Za-z_/.-])b[\'"]')

        copy = dict(rep1)
        recorded = copy.pop("audit_digest_sha256")
        expected = hashlib.sha256(
            json.dumps(copy, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        self.assertEqual(recorded, expected)

    def test_32_standalone_and_suite_cli_flags(self) -> None:
        for argv in (
            ["--clean-room", "--summary"],
            ["--clean-room", "--tc-matrix"],
            ["--clean-room", "--lens-matrix"],
            ["--clean-room", "--paint-matrix"],
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = p67.main(argv)
            self.assertEqual(rc, 0)
            self.assertTrue(buf.getvalue().strip())

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
        self.assertIn("tc_lens_paint=CLEAN_ROOM_SYNTHETIC", proc.stdout)

    def test_33_source_hygiene_o_rdonly_and_no_forbidden_writes_or_port(self) -> None:
        forbidden_port = "87" + "68"
        emu_src = (FX3_VM_DIR / "tc_genlock_lens_paint_emulator.py").read_text(encoding="utf-8")
        test_src = Path(__file__).read_text(encoding="utf-8")

        self.assertIn("os.O_RDONLY", emu_src)
        self.assertNotIn("os.O_WRONLY", emu_src)
        self.assertNotIn("os.O_RDWR", emu_src)
        self.assertNotIn(forbidden_port, emu_src)
        self.assertNotIn(forbidden_port, test_src)
        self.assertIn("CP_MUTATION_BYTES = 0", emu_src)
        self.assertIn("CALIBRATION_MUTATION_BYTES = 0", emu_src)
        self.assertIn("PERSISTENT_EMMC_WRITES_AUTHORIZED = False", emu_src)


if __name__ == "__main__":
    unittest.main()
