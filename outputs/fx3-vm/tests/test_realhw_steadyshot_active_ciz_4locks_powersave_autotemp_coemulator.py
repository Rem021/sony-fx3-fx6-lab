#!/usr/bin/env python3
"""Unit tests for Phase 226 Stage 41 (`41/41` Milestone):
Real-Hardware `ILME-FX3` (`0x91030080`, `Ver. 7.02`) Wave-31 `[SteadyShot]` (Movie)
`[Active]` `~1.1x` Crop vs `[Standard]`/`[Off]` & 3-Way Cutoffs (`119.88p/100p`,
S&Q `>=100fps/120fps`, HDMI `[RAW Output]=On`), `[Clear Image Zoom]` / `[Digital Zoom]`
(`[Zoom Range]`) RAW/HFR Unavailability & 4-Lock Automatic AF/Metering/Tracking State
Machine with `1.0x` Optical Restoration, and `[Power Save Start Time]` (Default `5 Min`)
9-Condition Bypass Matrix, Air-Gapped `NP-FZ100` Tier-0 `75 MiB` `p3` Sleep-Lock Guard,
& `[Auto Power OFF Temp.]` (`[Standard]` vs `[High]` Tripod Interlock + `[Fan Control]`
Coupling) HIL Co-Emulator.
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import contextlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import time
import unittest

FX3_VM_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = FX3_VM_DIR.parents[1]
if str(FX3_VM_DIR) not in sys.path:
    sys.path.insert(0, str(FX3_VM_DIR))

import fx3_vm_coemulation_suite as suite  # noqa: E402
import realhw_steadyshot_active_ciz_4locks_powersave_autotemp_coemulator as p226  # noqa: E402


_CLEAN_ROOM_AUDIT_CACHE = None
_DEFAULT_AUDIT_CACHE = None
_CLEAN_SUITE_CACHE = None
_CLEAN_SUITE_ELAPSED = None
_DEFAULT_SUITE_CACHE = None
_DEFAULT_SUITE_ELAPSED = None


def _get_clean_room_audit():
    global _CLEAN_ROOM_AUDIT_CACHE
    if _CLEAN_ROOM_AUDIT_CACHE is None:
        _CLEAN_ROOM_AUDIT_CACHE = (
            p226.run_phase226_realhw_steadyshot_active_ciz_4locks_powersave_autotemp_hil(
                force_clean_room=True
            )
        )
    return _CLEAN_ROOM_AUDIT_CACHE


def _get_default_audit():
    global _DEFAULT_AUDIT_CACHE
    if _DEFAULT_AUDIT_CACHE is None:
        _DEFAULT_AUDIT_CACHE = (
            p226.run_phase226_realhw_steadyshot_active_ciz_4locks_powersave_autotemp_hil()
        )
    return _DEFAULT_AUDIT_CACHE


def _get_clean_room_suite():
    global _CLEAN_SUITE_CACHE, _CLEAN_SUITE_ELAPSED
    if _CLEAN_SUITE_CACHE is None:
        t0 = time.monotonic()
        _CLEAN_SUITE_CACHE = suite.run_fx3_vm_coemulation_suite(
            suite.CoEmulationConfig(force_clean_room=True)
        )
        _CLEAN_SUITE_ELAPSED = time.monotonic() - t0
    return _CLEAN_SUITE_CACHE, float(_CLEAN_SUITE_ELAPSED)


def _get_default_suite():
    global _DEFAULT_SUITE_CACHE, _DEFAULT_SUITE_ELAPSED
    if _DEFAULT_SUITE_CACHE is None:
        t0 = time.monotonic()
        _DEFAULT_SUITE_CACHE = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig())
        _DEFAULT_SUITE_ELAPSED = time.monotonic() - t0
    return _DEFAULT_SUITE_CACHE, float(_DEFAULT_SUITE_ELAPSED)


class TestPhase226SteadyShotActiveCiz4LocksPowerSaveAutoTempCoEmulator(unittest.TestCase):
    # ------------------------------------------------------------------
    # Group 1: Schema, Milestone 41/41, Read-Only Donor Inspection (8)
    # ------------------------------------------------------------------
    def test_01_schema_version_stage_41_milestone_and_redline_constants(self) -> None:
        self.assertEqual(
            p226.SCHEMA_ID,
            "realhw_steadyshot_active_ciz_4locks_powersave_autotemp_coemulator_v1",
        )
        self.assertEqual(p226.PHASE_226_SCHEMA, p226.SCHEMA_ID)
        self.assertEqual(p226.PHASE_226_VERSION, "226.0.0")
        self.assertEqual(p226.STAGE_INDEX, 41)
        self.assertEqual(p226.STAGE_TOTAL, 41)
        self.assertEqual(p226.MILESTONE_LABEL, "41/41")
        self.assertEqual(
            p226.STAGE_NAME,
            "stage41_realhw_steadyshot_active_ciz_4locks_powersave_autotemp_hil",
        )
        self.assertEqual(p226.FX3_MODEL_ID, 0x91030080)
        self.assertTrue(p226.P8_CP_MUTATION_FORBIDDEN)
        self.assertTrue(p226.CNFLASHA_USERSPACE_WRITE_BLOCKED)
        self.assertEqual(p226.CNFLASHA_MUTATION_BYTES, 0)
        self.assertFalse(p226.PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(p226.HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        self.assertFalse(p226.OVERALL_READY_FOR_HARDWARE_ATTACH)
        self.assertFalse(p226.ISP_WRITE_AUTHORIZED)
        self.assertFalse(p226.SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(p226.EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        self.assertEqual(p226.PHYSICAL_USB_PACKETS_EMITTED, 0)
        self.assertEqual(p226.OTP_FUSE_TOUCHES, 0)
        self.assertEqual(p226.RPMB_COUNTER_INCREMENTS, 0)
        self.assertEqual(p226.STEADYSHOT_ACTIVE_CUTOFF_BYPASS_EVENTS, 0)
        self.assertEqual(p226.CIZ_4LOCK_UNRESTORED_OR_BYPASS_EVENTS, 0)
        self.assertEqual(p226.TIER0_P3_SLEEP_ABORT_OR_THERMAL_BURN_EVENTS, 0)
        self.assertEqual(p226.RAW_FIRMWARE_BYTES_LEAKED, 0)
        self.assertEqual(p226.DONOR_ACCESS_MODE, "O_RDONLY")

    def test_02_donor_inspection_fast_bounded_and_cached(self) -> None:
        p226._DONOR_AUDIT_CACHE.clear()
        t0 = time.monotonic()
        da1 = p226.inspect_phase226_donors(force_clean_room=False)
        dt1 = time.monotonic() - t0
        t1 = time.monotonic()
        da2 = p226.inspect_phase226_donors(force_clean_room=False)
        dt2 = time.monotonic() - t1

        self.assertTrue(da1.all_contracts_verified)
        self.assertEqual(da1.errors, ())
        self.assertEqual(da1.donor_files_inspected, 12)
        self.assertEqual(da1.raw_firmware_bytes_leaked, 0)
        self.assertEqual(da1.access_mode, "O_RDONLY")
        self.assertIn(da1.source_mode, ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"))
        self.assertEqual(da1, da2)
        self.assertLess(dt1, 0.25)
        self.assertLess(dt2, 0.05)

    def test_03_clean_room_donor_inspection_synthetic_parity(self) -> None:
        da = p226.inspect_phase226_donors(force_clean_room=True)
        self.assertEqual(da.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(da.all_contracts_verified)
        self.assertTrue(da.steadyshot_active_and_3cutoffs_proven)
        self.assertTrue(da.ciz_digital_zoom_4locks_proven)
        self.assertTrue(da.powersave_9cond_and_autotemp_fan_proven)
        self.assertEqual(da.donor_files_inspected, 12)
        self.assertEqual(da.raw_firmware_bytes_leaked, 0)

    def test_04_env_force_clean_room_flag_variants(self) -> None:
        for truthy in ("1", "true", "TRUE", "yes", "on"):
            self.assertTrue(p226.is_forced_clean_room({p226.ENV_FORCE_CLEAN_ROOM: truthy}))
        for falsy in ("", "0", "false", "no", "off"):
            self.assertFalse(p226.is_forced_clean_room({p226.ENV_FORCE_CLEAN_ROOM: falsy}))

        paths = p226.resolve_phase226_donor_paths(env={p226.ENV_FORCE_CLEAN_ROOM: "1"})
        self.assertEqual(len(paths), 12)
        for p in paths.values():
            self.assertIn(p226.CLEAN_ROOM_SENTINEL_DIRNAME, str(p))

    def test_05_missing_donor_directory_falls_back_cleanly_to_synthetic(self) -> None:
        env = {
            p226.ENV_FORCE_CLEAN_ROOM: "0",
            p226.ENV_MAC_WORK_ROOT: "/nonexistent/fx3_wave31_work_root",
        }
        da = p226.inspect_phase226_donors(env=env)
        self.assertTrue(da.all_contracts_verified)
        self.assertEqual(da.raw_firmware_bytes_leaked, 0)

    def test_06_large_donors_strictly_bounded_window_reads(self) -> None:
        da = p226.inspect_phase226_donors()
        for key in ("fx3_appfw", "fx6_appfw", "fx3_cpapp", "fx6_cpapp", "fx3_libmpr", "fx6_libmpr"):
            summary = getattr(da, key)
            self.assertTrue(summary.bounded_windows_only, msg=key)
            self.assertLessEqual(summary.bytes_read_total, 16 * p226.BOUNDED_WINDOW_MAX_BYTES)
            self.assertEqual(summary.file_bytes, p226.EXPECTED_DONOR_BYTES[key])
            self.assertTrue(all(v == 1 for v in summary.window_hits.values()), msg=key)

    def test_07_compact_uxc_wave31_menu_tokens_verified(self) -> None:
        da = p226.inspect_phase226_donors()
        hits = da.fx3_string_en_f.marker_hits
        for tok in (
            "SteadyShot",
            "Active",
            "Standard",
            "RAW Output",
            "119.88p",
            "100p",
            "120fps",
            "Clear Image Zoom",
            "Digital Zoom",
            "Zoom Range",
            "Optical zoom only",
            "Focus Area",
            "Metering Mode",
            "Multi",
            "Face/Eye Prior. in AF",
            "Face Priority in Multi Metering",
            "Tracking",
            "Power Save Start Time",
            "30 Min",
            "10 Sec",
            "IR Remote Ctrl",
            "Bluetooth Rmt Ctrl",
            "Auto Power OFF Temp.",
            "High",
            "Fan Control",
        ):
            self.assertEqual(hits.get(tok), 1, msg=f"Missing token {tok!r}")

    def test_08_local_donor_mode_when_present_uses_exact_local_donor_o_rdonly_label(self) -> None:
        if p226.is_forced_clean_room():
            da = p226.inspect_phase226_donors()
            self.assertEqual(da.source_mode, "CLEAN_ROOM_SYNTHETIC")
            return
        paths = p226.resolve_phase226_donor_paths()
        if all(p.is_file() for p in paths.values()):
            da = p226.inspect_phase226_donors(force_clean_room=False)
            self.assertEqual(da.source_mode, "LOCAL_DONOR_O_RDONLY")

    # ------------------------------------------------------------------
    # Group 2: Sub-model A — [SteadyShot] [Active] ~1.1x Crop & 3 Cutoffs (12)
    # ------------------------------------------------------------------
    def test_09_submodel_a_movie_steadyshot_active_applies_1_10x_crop_across_standard_fps(
        self,
    ) -> None:
        for fps in ("23.98p", "24.00p", "25p", "29.97p", "50p", "59.94p"):
            res = p226.probe_steadyshot_movie_active_cutoffs_hil(
                shooting_mode="Movie",
                requested_steadyshot="Active",
                movie_fps=fps,
            )
            self.assertTrue(res.admitted, msg=fps)
            self.assertEqual(res.effective_steadyshot, "Active")
            self.assertTrue(res.active_mode_available)
            self.assertEqual(res.crop_factor, 1.10)
            self.assertTrue(res.ibis_5axis_sensor_shift_active)
            self.assertTrue(res.electronic_gyro_crop_active)
            self.assertFalse(res.ibis_voice_coil_parked)
            self.assertTrue(res.catalyst_gyro_metadata_recorded)

    def test_10_submodel_a_sq_1_to_60fps_allows_steadyshot_active_1_10x(self) -> None:
        for sq_fps in (1, 2, 4, 8, 15, 25, 30, 50, 60):
            res = p226.probe_steadyshot_movie_active_cutoffs_hil(
                shooting_mode="S&Q",
                requested_steadyshot="Active",
                movie_fps="23.98p",
                sq_sensor_fps=sq_fps,
            )
            self.assertTrue(res.admitted, msg=str(sq_fps))
            self.assertEqual(res.effective_steadyshot, "Active")
            self.assertEqual(res.crop_factor, 1.10)

    def test_11_submodel_a_standard_and_off_preserve_1_00x_full_fov(self) -> None:
        std = p226.probe_steadyshot_movie_active_cutoffs_hil(
            requested_steadyshot="Standard",
            movie_fps="59.94p",
        )
        self.assertTrue(std.admitted)
        self.assertEqual(std.crop_factor, 1.00)
        self.assertTrue(std.ibis_5axis_sensor_shift_active)
        self.assertFalse(std.electronic_gyro_crop_active)
        self.assertFalse(std.ibis_voice_coil_parked)

        off = p226.probe_steadyshot_movie_active_cutoffs_hil(
            requested_steadyshot="Off",
            movie_fps="23.98p",
        )
        self.assertTrue(off.admitted)
        self.assertEqual(off.crop_factor, 1.00)
        self.assertFalse(off.ibis_5axis_sensor_shift_active)
        self.assertTrue(off.ibis_voice_coil_parked)

    def test_12_submodel_a_cutoff_1_normal_movie_11988p_and_100p_block_active(self) -> None:
        for fps in ("119.88p", "100p"):
            blk = p226.probe_steadyshot_movie_active_cutoffs_hil(
                shooting_mode="Movie",
                requested_steadyshot="Active",
                movie_fps=fps,
            )
            self.assertFalse(blk.admitted, msg=fps)
            self.assertFalse(blk.active_mode_available)
            self.assertIn(p226.CUTOFF_NORMAL_HFR_120P_100P, blk.cutoff_reasons)
            self.assertEqual(blk.errno_code, p226.EOPNOTSUPP_ERRNO)
            self.assertEqual(blk.steadyshot_active_cutoff_bypass_events, 0)

            std_hfr = p226.probe_steadyshot_movie_active_cutoffs_hil(
                shooting_mode="Movie",
                requested_steadyshot="Standard",
                movie_fps=fps,
            )
            self.assertTrue(std_hfr.admitted)
            self.assertFalse(std_hfr.active_mode_available)
            self.assertEqual(std_hfr.crop_factor, 1.00)

    def test_13_submodel_a_cutoff_2_sq_ge_100fps_blocks_active(self) -> None:
        for sq_fps in (100, 120, 200, 240):
            blk = p226.probe_steadyshot_movie_active_cutoffs_hil(
                shooting_mode="S&Q",
                requested_steadyshot="Active",
                movie_fps="29.97p",
                sq_sensor_fps=sq_fps,
            )
            self.assertFalse(blk.admitted, msg=str(sq_fps))
            self.assertFalse(blk.active_mode_available)
            self.assertIn(p226.CUTOFF_SQ_SENSOR_FPS_GE_100, blk.cutoff_reasons)
            self.assertEqual(blk.errno_code, p226.EOPNOTSUPP_ERRNO)

    def test_14_submodel_a_cutoff_3_hdmi_raw_output_on_blocks_active(self) -> None:
        blk = p226.probe_steadyshot_movie_active_cutoffs_hil(
            shooting_mode="Movie",
            requested_steadyshot="Active",
            movie_fps="23.98p",
            hdmi_raw_output="On",
        )
        self.assertFalse(blk.admitted)
        self.assertFalse(blk.active_mode_available)
        self.assertIn(p226.CUTOFF_HDMI_RAW_OUTPUT_ON, blk.cutoff_reasons)
        self.assertEqual(blk.errno_code, p226.EOPNOTSUPP_ERRNO)

    def test_15_submodel_a_combined_multi_cutoff_and_auto_fallback_to_standard(self) -> None:
        combo = p226.probe_steadyshot_movie_active_cutoffs_hil(
            shooting_mode="Movie",
            requested_steadyshot="Active",
            movie_fps="119.88p",
            hdmi_raw_output="On",
            auto_fallback_to_standard=True,
        )
        self.assertTrue(combo.admitted)
        self.assertTrue(combo.auto_fell_back_to_standard)
        self.assertFalse(combo.active_mode_available)
        self.assertEqual(combo.effective_steadyshot, "Standard")
        self.assertEqual(combo.crop_factor, 1.00)
        self.assertEqual(len(combo.cutoff_reasons), 2)

    def test_16_submodel_a_suppress_active_1_1x_crop_attempt_blocked(self) -> None:
        blk = p226.probe_steadyshot_movie_active_cutoffs_hil(
            requested_steadyshot="Active",
            attempt_suppress_active_crop=True,
        )
        self.assertFalse(blk.admitted)
        self.assertEqual(blk.errno_code, p226.EOPNOTSUPP_ERRNO)
        self.assertEqual(blk.steadyshot_active_cutoff_bypass_events, 0)

    def test_17_submodel_a_still_mode_has_on_off_only_and_rejects_active(self) -> None:
        still_on = p226.probe_steadyshot_movie_active_cutoffs_hil(
            shooting_mode="Still",
            requested_steadyshot="On",
        )
        self.assertTrue(still_on.admitted)
        self.assertFalse(still_on.active_mode_available)
        self.assertEqual(still_on.crop_factor, 1.00)

        still_act = p226.probe_steadyshot_movie_active_cutoffs_hil(
            shooting_mode="Still",
            requested_steadyshot="Active",
        )
        self.assertFalse(still_act.admitted)
        self.assertEqual(still_act.errno_code, p226.EOPNOTSUPP_ERRNO)

    def test_18_submodel_a_manual_focal_length_8_to_1000mm_bounds(self) -> None:
        for valid_mm in (8, 24, 50, 135, 1000):
            ok = p226.probe_steadyshot_movie_active_cutoffs_hil(
                steadyshot_adjust="Manual",
                focal_length_mm=valid_mm,
            )
            self.assertTrue(ok.admitted, msg=str(valid_mm))
            self.assertEqual(ok.focal_length_mm, valid_mm)

        for bad_mm in (0, 7, 1001, 2500):
            bad = p226.probe_steadyshot_movie_active_cutoffs_hil(
                steadyshot_adjust="Manual",
                focal_length_mm=bad_mm,
            )
            self.assertFalse(bad.admitted, msg=str(bad_mm))
            self.assertEqual(bad.errno_code, p226.EINVAL_ERRNO)

    def test_19_submodel_a_invalid_fps_mode_and_config_errors(self) -> None:
        bad_fps = p226.probe_steadyshot_movie_active_cutoffs_hil(movie_fps="48p")
        self.assertFalse(bad_fps.admitted)
        self.assertEqual(bad_fps.errno_code, p226.EINVAL_ERRNO)

        bad_sq = p226.probe_steadyshot_movie_active_cutoffs_hil(
            shooting_mode="S&Q", sq_sensor_fps=90
        )
        self.assertFalse(bad_sq.admitted)
        self.assertEqual(bad_sq.errno_code, p226.EINVAL_ERRNO)

        bad_ss = p226.probe_steadyshot_movie_active_cutoffs_hil(requested_steadyshot="Dynamic")
        self.assertFalse(bad_ss.admitted)
        self.assertEqual(bad_ss.errno_code, p226.EINVAL_ERRNO)

        with self.assertRaises(p226.RealHwSteadyShotActiveCiz4LocksPowerSaveAutoTempError):
            p226.probe_steadyshot_movie_active_cutoffs_hil(shooting_mode="Panorama")

    def test_20_pillar_a_evaluator_matrix_passes_100pct(self) -> None:
        pa = p226.evaluate_pillar_a_steadyshot_active_cutoffs_hil()
        self.assertTrue(pa["passed"])
        self.assertEqual(pa["active_4k_2398p_1_10x_crop_ok"]["crop_factor"], 1.10)
        self.assertFalse(pa["cutoff_1_normal_11988p_blocked"]["admitted"])
        self.assertFalse(pa["cutoff_2_sq_120fps_blocked"]["admitted"])
        self.assertFalse(pa["cutoff_3_hdmi_raw_output_on_blocked"]["admitted"])

    # ------------------------------------------------------------------
    # Group 3: Sub-model B — CIZ / Digital Zoom 4-Locks & 1.0x Restore (14)
    # ------------------------------------------------------------------
    def test_21_submodel_b_4k_ciz_max_1_5x_cap_vs_hd_and_still_2_0x_cap(self) -> None:
        for res_4k in (p226.RES_4K_QFHD, p226.RES_4K_DCI):
            ok_15 = p226.probe_ciz_digital_zoom_4locks_and_restore_hil(
                video_resolution=res_4k,
                zoom_range_mode="Clear Image Zoom",
                requested_zoom_scale=1.50,
            )
            self.assertTrue(ok_15.admitted, msg=res_4k)
            self.assertEqual(ok_15.max_supported_zoom_scale, 1.50)

            blk_16 = p226.probe_ciz_digital_zoom_4locks_and_restore_hil(
                video_resolution=res_4k,
                zoom_range_mode="Clear Image Zoom",
                requested_zoom_scale=1.60,
            )
            self.assertFalse(blk_16.admitted, msg=res_4k)
            self.assertEqual(blk_16.errno_code, p226.EOPNOTSUPP_ERRNO)

        hd_20 = p226.probe_ciz_digital_zoom_4locks_and_restore_hil(
            video_resolution=p226.RES_HD_1080P,
            zoom_range_mode="Clear Image Zoom",
            requested_zoom_scale=2.00,
        )
        self.assertTrue(hd_20.admitted)
        self.assertEqual(hd_20.effective_zoom_scale, 2.00)

        still_20 = p226.probe_ciz_digital_zoom_4locks_and_restore_hil(
            shooting_mode="Still",
            still_file_format="JPEG",
            zoom_range_mode="Clear Image Zoom",
            requested_zoom_scale=2.00,
        )
        self.assertTrue(still_20.admitted)
        self.assertEqual(still_20.effective_zoom_scale, 2.00)

    def test_22_submodel_b_digital_zoom_4_0x_cap_and_above_4_0x_rejection(self) -> None:
        dz_40 = p226.probe_ciz_digital_zoom_4locks_and_restore_hil(
            video_resolution=p226.RES_4K_QFHD,
            zoom_range_mode="Digital Zoom",
            requested_zoom_scale=4.00,
        )
        self.assertTrue(dz_40.admitted)
        self.assertEqual(dz_40.effective_zoom_scale, 4.00)
        self.assertEqual(dz_40.active_4locks, p226.ALL_4_CIZ_STATE_LOCKS)

        dz_41 = p226.probe_ciz_digital_zoom_4locks_and_restore_hil(
            zoom_range_mode="Digital Zoom",
            requested_zoom_scale=4.10,
        )
        self.assertFalse(dz_41.admitted)
        self.assertEqual(dz_41.errno_code, p226.EOPNOTSUPP_ERRNO)

    def test_23_submodel_b_optical_zoom_only_locks_1_0x_ceiling(self) -> None:
        opt_10 = p226.probe_ciz_digital_zoom_4locks_and_restore_hil(
            zoom_range_mode="Optical zoom only",
            requested_zoom_scale=1.00,
        )
        self.assertTrue(opt_10.admitted)
        self.assertFalse(opt_10.non_optical_zoom_engaged)
        self.assertEqual(opt_10.active_4locks, ())

        opt_11 = p226.probe_ciz_digital_zoom_4locks_and_restore_hil(
            zoom_range_mode="Optical zoom only",
            requested_zoom_scale=1.10,
        )
        self.assertFalse(opt_11.admitted)
        self.assertEqual(opt_11.errno_code, p226.EOPNOTSUPP_ERRNO)

    def test_24_submodel_b_smart_zoom_still_m_s_only_vs_movie_and_l_rejection(self) -> None:
        sz_m = p226.probe_ciz_digital_zoom_4locks_and_restore_hil(
            shooting_mode="Still",
            still_file_format="HEIF",
            still_image_size="M",
            zoom_range_mode="Smart Zoom",
            requested_zoom_scale=1.40,
        )
        self.assertTrue(sz_m.admitted)
        self.assertEqual(sz_m.active_4locks, p226.ALL_4_CIZ_STATE_LOCKS)

        sz_s = p226.probe_ciz_digital_zoom_4locks_and_restore_hil(
            shooting_mode="Still",
            still_file_format="JPEG",
            still_image_size="S",
            zoom_range_mode="Smart Zoom",
            requested_zoom_scale=2.00,
        )
        self.assertTrue(sz_s.admitted)

        sz_l_blk = p226.probe_ciz_digital_zoom_4locks_and_restore_hil(
            shooting_mode="Still",
            still_image_size="L",
            zoom_range_mode="Smart Zoom",
            requested_zoom_scale=1.20,
        )
        self.assertFalse(sz_l_blk.admitted)

        sz_mov_blk = p226.probe_ciz_digital_zoom_4locks_and_restore_hil(
            shooting_mode="Movie",
            zoom_range_mode="Smart Zoom",
            requested_zoom_scale=1.20,
        )
        self.assertFalse(sz_mov_blk.admitted)

    def test_25_submodel_b_unavailability_hdmi_raw_and_still_raw_formats(self) -> None:
        hdmi_raw = p226.probe_ciz_digital_zoom_4locks_and_restore_hil(
            shooting_mode="Movie",
            hdmi_raw_output="On",
            zoom_range_mode="Clear Image Zoom",
            requested_zoom_scale=1.25,
        )
        self.assertFalse(hdmi_raw.admitted)
        self.assertFalse(hdmi_raw.ciz_digital_zoom_available)
        self.assertIn("HDMI_RAW_OUTPUT_ON", hdmi_raw.unavailability_reasons)

        for raw_fmt in ("RAW", "RAW & JPEG", "RAW & HEIF"):
            still_raw = p226.probe_ciz_digital_zoom_4locks_and_restore_hil(
                shooting_mode="Still",
                still_file_format=raw_fmt,
                zoom_range_mode="Digital Zoom",
                requested_zoom_scale=1.50,
            )
            self.assertFalse(still_raw.admitted, msg=raw_fmt)
            self.assertFalse(still_raw.ciz_digital_zoom_available)
            self.assertIn("STILL_RAW_FILE_FORMAT", still_raw.unavailability_reasons)

    def test_26_submodel_b_unavailability_movie_hfr_120p_100p_and_sq_ge_100fps(self) -> None:
        for fps in ("119.88p", "100p"):
            blk = p226.probe_ciz_digital_zoom_4locks_and_restore_hil(
                shooting_mode="Movie",
                movie_fps=fps,
                zoom_range_mode="Clear Image Zoom",
                requested_zoom_scale=1.20,
            )
            self.assertFalse(blk.admitted, msg=fps)
            self.assertIn("NORMAL_MOVIE_HFR_119_88P_OR_100P", blk.unavailability_reasons)

        for sq_fps in (100, 120, 200, 240):
            blk_sq = p226.probe_ciz_digital_zoom_4locks_and_restore_hil(
                shooting_mode="S&Q",
                movie_fps="23.98p",
                sq_sensor_fps=sq_fps,
                zoom_range_mode="Clear Image Zoom",
                requested_zoom_scale=1.30,
            )
            self.assertFalse(blk_sq.admitted, msg=str(sq_fps))
            self.assertIn("SQ_SENSOR_FRAME_RATE_GE_100FPS", blk_sq.unavailability_reasons)

    def test_27_submodel_b_all_4_automatic_camera_state_locks_engaged_above_1_0x(self) -> None:
        zoomed = p226.probe_ciz_digital_zoom_4locks_and_restore_hil(
            zoom_range_mode="Clear Image Zoom",
            requested_zoom_scale=1.35,
            prior_focus_area="Tracking: Expand Spot",
            prior_metering_mode="Center",
            prior_face_eye_prior_af="On",
            prior_face_priority_multi_metering="On",
            prior_realtime_tracking="On",
        )
        self.assertTrue(zoomed.admitted)
        self.assertTrue(zoomed.non_optical_zoom_engaged)
        self.assertEqual(zoomed.active_4locks, p226.ALL_4_CIZ_STATE_LOCKS)
        # Lock 1: [Focus Area] disabled -> Center-priority AF
        self.assertTrue(zoomed.focus_area_menu_locked)
        self.assertEqual(zoomed.effective_focus_area, p226.LOCKED_ZOOM_FOCUS_AREA)
        # Lock 2: [Metering Mode] locked to [Multi]
        self.assertTrue(zoomed.metering_mode_locked_multi)
        self.assertEqual(zoomed.effective_metering_mode, "Multi")
        # Lock 3: [Face/Eye Prior. in AF] & [Face Priority in Multi Metering] unavailable
        self.assertTrue(zoomed.face_eye_af_unavailable)
        self.assertEqual(zoomed.effective_face_eye_prior_af, "Off")
        self.assertTrue(zoomed.face_priority_multi_metering_unavailable)
        self.assertEqual(zoomed.effective_face_priority_multi_metering, "Off")
        # Lock 4: Real-time Tracking unavailable
        self.assertTrue(zoomed.realtime_tracking_unavailable)
        self.assertEqual(zoomed.effective_realtime_tracking, "Off")

    def test_28_submodel_b_override_of_any_4lock_rejected_fail_closed(self) -> None:
        blk = p226.probe_ciz_digital_zoom_4locks_and_restore_hil(
            zoom_range_mode="Digital Zoom",
            requested_zoom_scale=2.50,
            attempt_override_locked_af_or_metering=True,
        )
        self.assertFalse(blk.admitted)
        self.assertEqual(blk.errno_code, p226.EOPNOTSUPP_ERRNO)
        self.assertEqual(blk.ciz_4lock_unrestored_or_bypass_events, 0)
        self.assertEqual(blk.active_4locks, p226.ALL_4_CIZ_STATE_LOCKS)

    def test_29_submodel_b_clean_1_0x_optical_restoration_across_ciz_and_digital_zoom(
        self,
    ) -> None:
        for mode, scale in (("Clear Image Zoom", 1.50), ("Digital Zoom", 3.80)):
            sim = p226.simulate_ciz_zoom_excursion_and_optical_restore(
                video_resolution=p226.RES_4K_QFHD,
                zoom_range_mode=mode,
                excursion_zoom_scale=scale,
                initial_focus_area="Spot: S",
                initial_metering_mode="Entire Screen Avg.",
                initial_face_eye_prior_af="On",
                initial_face_priority_multi_metering="On",
                initial_realtime_tracking="On",
            )
            self.assertTrue(sim["restored_matches_initial"], msg=mode)
            self.assertTrue(sim["locks_cleared_at_1_0x"])
            self.assertEqual(sim["ciz_4lock_unrestored_or_bypass_events"], 0)
            s3 = sim["step3_restored_optical_1_0x"]
            self.assertEqual(s3["effective_focus_area"], "Spot: S")
            self.assertEqual(s3["effective_metering_mode"], "Entire Screen Avg.")
            self.assertEqual(s3["effective_face_eye_prior_af"], "On")
            self.assertEqual(s3["effective_face_priority_multi_metering"], "On")
            self.assertEqual(s3["effective_realtime_tracking"], "On")

    def test_30_submodel_b_ciz_permitted_at_1_0x_even_when_zoom_range_set_to_ciz(self) -> None:
        at_1_0x = p226.probe_ciz_digital_zoom_4locks_and_restore_hil(
            zoom_range_mode="Clear Image Zoom",
            requested_zoom_scale=1.00,
            prior_focus_area="Zone",
            prior_metering_mode="Highlight",
        )
        self.assertTrue(at_1_0x.admitted)
        self.assertFalse(at_1_0x.non_optical_zoom_engaged)
        self.assertEqual(at_1_0x.active_4locks, ())
        self.assertEqual(at_1_0x.effective_focus_area, "Zone")
        self.assertEqual(at_1_0x.effective_metering_mode, "Highlight")

    def test_31_submodel_b_sq_60fps_allows_ciz_with_4locks(self) -> None:
        sq60 = p226.probe_ciz_digital_zoom_4locks_and_restore_hil(
            shooting_mode="S&Q",
            video_resolution=p226.RES_HD_1080P,
            movie_fps="23.98p",
            sq_sensor_fps=60,
            zoom_range_mode="Clear Image Zoom",
            requested_zoom_scale=2.00,
        )
        self.assertTrue(sq60.admitted)
        self.assertEqual(sq60.effective_zoom_scale, 2.00)
        self.assertEqual(sq60.active_4locks, p226.ALL_4_CIZ_STATE_LOCKS)

    def test_32_submodel_b_invalid_zoom_scale_below_1_0x_and_bad_mode_rejected(self) -> None:
        below_1 = p226.probe_ciz_digital_zoom_4locks_and_restore_hil(requested_zoom_scale=0.85)
        self.assertFalse(below_1.admitted)
        self.assertEqual(below_1.errno_code, p226.EINVAL_ERRNO)

        bad_mode = p226.probe_ciz_digital_zoom_4locks_and_restore_hil(zoom_range_mode="SuperZoom")
        self.assertFalse(bad_mode.admitted)
        self.assertEqual(bad_mode.errno_code, p226.EINVAL_ERRNO)

    def test_33_submodel_b_invalid_prior_af_or_metering_raises_value_error(self) -> None:
        with self.assertRaises(p226.RealHwSteadyShotActiveCiz4LocksPowerSaveAutoTempError):
            p226.probe_ciz_digital_zoom_4locks_and_restore_hil(prior_focus_area="3D Matrix")
        with self.assertRaises(p226.RealHwSteadyShotActiveCiz4LocksPowerSaveAutoTempError):
            p226.probe_ciz_digital_zoom_4locks_and_restore_hil(prior_metering_mode="Matrix")

    def test_34_pillar_b_evaluator_matrix_passes_100pct(self) -> None:
        pb = p226.evaluate_pillar_b_ciz_digital_zoom_4locks_and_restore_hil()
        self.assertTrue(pb["passed"])
        self.assertEqual(
            len(pb["ciz_4k_1_5x_all_4_locks_engaged"]["active_4locks"]),
            4,
        )
        self.assertTrue(pb["zoom_excursion_and_1_0x_optical_restore"]["restored_matches_initial"])

    # ------------------------------------------------------------------
    # Group 4: Sub-model C — [Power Save Start Time] 9-Cond, Tier-0 p3 & [Auto Power OFF Temp.] (13)
    # ------------------------------------------------------------------
    def test_35_submodel_c_exact_power_save_start_time_menu_string_and_6_options(self) -> None:
        self.assertEqual(p226.POWER_SAVE_MENU_NAME, "Power Save Start Time")
        self.assertEqual(p226.POWER_SAVE_5_MIN_DEFAULT, "5 Min")
        self.assertEqual(
            p226.VALID_POWER_SAVE_OPTIONS,
            ("Off", "30 Min", "5 Min", "2 Min", "1 Min", "10 Sec"),
        )
        expected_sec = {
            "Off": None,
            "30 Min": 1800,
            "5 Min": 300,
            "2 Min": 120,
            "1 Min": 60,
            "10 Sec": 10,
        }
        for opt, sec in expected_sec.items():
            res = p226.probe_powersave_9cond_and_autotemp_fan_hil(
                power_save_start_time=opt,
                idle_elapsed_sec=5,
            )
            self.assertTrue(res.admitted, msg=opt)
            self.assertEqual(res.power_save_menu_name, "Power Save Start Time")
            self.assertEqual(res.power_save_timeout_sec, sec)
            self.assertFalse(res.camera_entered_power_save_sleep)

    def test_36_submodel_c_all_9_individual_bypass_conditions_deactivate_power_save(self) -> None:
        self.assertEqual(len(p226.POWER_SAVE_9_CONDITION_KEYS), 9)
        for cond_key in p226.POWER_SAVE_9_CONDITION_KEYS:
            res = p226.probe_powersave_9cond_and_autotemp_fan_hil(
                power_save_start_time="10 Sec",
                idle_elapsed_sec=900,
                **{cond_key: True},
            )
            self.assertTrue(res.admitted, msg=cond_key)
            self.assertTrue(res.power_save_auto_deactivated, msg=cond_key)
            self.assertEqual(res.active_bypass_conditions, (cond_key,))
            self.assertEqual(res.active_bypass_count, 1)
            self.assertFalse(res.camera_entered_power_save_sleep, msg=cond_key)

    def test_37_submodel_c_standalone_np_fz100_all_9_false_sleeps_at_timeout_boundary(
        self,
    ) -> None:
        awake_299 = p226.probe_powersave_9cond_and_autotemp_fan_hil(
            power_save_start_time="5 Min",
            idle_elapsed_sec=299,
        )
        self.assertFalse(awake_299.power_save_auto_deactivated)
        self.assertFalse(awake_299.camera_entered_power_save_sleep)

        asleep_300 = p226.probe_powersave_9cond_and_autotemp_fan_hil(
            power_save_start_time="5 Min",
            idle_elapsed_sec=300,
        )
        self.assertTrue(asleep_300.admitted)
        self.assertFalse(asleep_300.power_save_auto_deactivated)
        self.assertTrue(asleep_300.camera_entered_power_save_sleep)

        off_never_sleeps = p226.probe_powersave_9cond_and_autotemp_fan_hil(
            power_save_start_time="Off",
            idle_elapsed_sec=7200,
        )
        self.assertFalse(off_never_sleeps.camera_entered_power_save_sleep)

    def test_38_submodel_c_airgapped_tier0_75mib_p3_vault_sleep_guard_blocks_short_timers(
        self,
    ) -> None:
        for unsafe_opt in ("5 Min", "2 Min", "1 Min", "10 Sec"):
            blk = p226.probe_powersave_9cond_and_autotemp_fan_hil(
                power_save_start_time=unsafe_opt,
                tier0_p3_vault_dump_requested=True,
                battery_charge_pct=85,
                fan_control="Auto",
            )
            self.assertFalse(blk.admitted, msg=unsafe_opt)
            self.assertEqual(blk.errno_code, p226.EOPNOTSUPP_ERRNO)
            self.assertEqual(blk.tier0_p3_vault_bytes, 75 * 1024 * 1024)
            self.assertFalse(blk.persistent_emmc_writes_authorized)

        for safe_opt in ("Off", "30 Min"):
            ok = p226.probe_powersave_9cond_and_autotemp_fan_hil(
                power_save_start_time=safe_opt,
                idle_elapsed_sec=360,
                tier0_p3_vault_dump_requested=True,
                battery_charge_pct=85,
                fan_control="Auto",
            )
            self.assertTrue(ok.admitted, msg=safe_opt)
            self.assertTrue(ok.tier0_sleep_lock_guard_satisfied)
            self.assertFalse(ok.camera_entered_power_save_sleep)
            self.assertFalse(ok.persistent_emmc_writes_authorized)

    def test_39_submodel_c_tier0_p3_vault_enforces_battery_fan_auto_and_airgap(self) -> None:
        low_batt = p226.probe_powersave_9cond_and_autotemp_fan_hil(
            power_save_start_time="Off",
            tier0_p3_vault_dump_requested=True,
            battery_charge_pct=50,
            fan_control="Auto",
        )
        self.assertFalse(low_batt.admitted)
        self.assertEqual(low_batt.errno_code, p226.EOPNOTSUPP_ERRNO)

        bad_fan = p226.probe_powersave_9cond_and_autotemp_fan_hil(
            power_save_start_time="Off",
            tier0_p3_vault_dump_requested=True,
            battery_charge_pct=90,
            fan_control="Off in Rec",
        )
        self.assertFalse(bad_fan.admitted)
        self.assertEqual(bad_fan.errno_code, p226.EOPNOTSUPP_ERRNO)

        for breach_flag in (
            "usb_data_connection_active",
            "ftp_or_smartphone_network_transfer_active",
            "bluetooth_remote_ctrl_on",
            "ir_remote_ctrl_on",
        ):
            breach = p226.probe_powersave_9cond_and_autotemp_fan_hil(
                power_save_start_time="Off",
                tier0_p3_vault_dump_requested=True,
                battery_charge_pct=90,
                fan_control="Auto",
                **{breach_flag: True},
            )
            self.assertFalse(breach.admitted, msg=breach_flag)
            self.assertEqual(breach.errno_code, p226.EOPNOTSUPP_ERRNO)

    def test_40_submodel_c_auto_power_off_temp_standard_handheld_ok_vs_high_handheld_blocked(
        self,
    ) -> None:
        std_handheld = p226.probe_powersave_9cond_and_autotemp_fan_hil(
            auto_power_off_temp="Standard",
            mounting_state="Handheld",
        )
        self.assertTrue(std_handheld.admitted)
        self.assertEqual(std_handheld.thermal_shutoff_ceiling_c, 68.0)
        self.assertFalse(std_handheld.handheld_contact_burn_blocked)

        high_handheld = p226.probe_powersave_9cond_and_autotemp_fan_hil(
            auto_power_off_temp="High",
            mounting_state="Handheld",
        )
        self.assertFalse(high_handheld.admitted)
        self.assertTrue(high_handheld.handheld_contact_burn_blocked)
        self.assertEqual(high_handheld.errno_code, p226.EOPNOTSUPP_ERRNO)
        self.assertEqual(high_handheld.tier0_p3_sleep_abort_or_thermal_burn_events, 0)

    def test_41_submodel_c_auto_power_off_temp_high_tripod_and_cagerig_admitted(self) -> None:
        for mount in ("Tripod", "CageRig"):
            ok = p226.probe_powersave_9cond_and_autotemp_fan_hil(
                auto_power_off_temp="High",
                mounting_state=mount,
                fan_control="Auto",
                internal_temp_c=70.0,
            )
            self.assertTrue(ok.admitted, msg=mount)
            self.assertEqual(ok.thermal_shutoff_ceiling_c, 78.0)
            self.assertFalse(ok.thermal_auto_power_off_triggered)

    def test_42_submodel_c_fan_control_coupling_blocks_high_temp_with_always_off(self) -> None:
        blk = p226.probe_powersave_9cond_and_autotemp_fan_hil(
            auto_power_off_temp="High",
            mounting_state="Tripod",
            fan_control="Always Off",
        )
        self.assertFalse(blk.admitted)
        self.assertEqual(blk.errno_code, p226.EOPNOTSUPP_ERRNO)

        std_always_off = p226.probe_powersave_9cond_and_autotemp_fan_hil(
            auto_power_off_temp="Standard",
            mounting_state="Tripod",
            fan_control="Always Off",
            internal_temp_c=40.0,
        )
        self.assertTrue(std_always_off.admitted)
        self.assertEqual(std_always_off.effective_fan_pwm_pct, 0)

    def test_43_submodel_c_thermal_fan_override_and_graceful_shutoff_ceilings(self) -> None:
        # Off in Rec at normal temp while recording -> 0% PWM
        quiet_rec = p226.probe_powersave_9cond_and_autotemp_fan_hil(
            auto_power_off_temp="Standard",
            fan_control="Off in Rec",
            movie_recording_in_progress=True,
            internal_temp_c=52.0,
        )
        self.assertEqual(quiet_rec.effective_fan_pwm_pct, 0)
        self.assertFalse(quiet_rec.thermal_fan_override_engaged)

        # Off in Rec above 62C Standard override threshold -> 100% emergency PWM
        hot_rec = p226.probe_powersave_9cond_and_autotemp_fan_hil(
            auto_power_off_temp="Standard",
            fan_control="Off in Rec",
            movie_recording_in_progress=True,
            internal_temp_c=63.5,
        )
        self.assertEqual(hot_rec.effective_fan_pwm_pct, 100)
        self.assertTrue(hot_rec.thermal_fan_override_engaged)
        self.assertFalse(hot_rec.thermal_auto_power_off_triggered)

        # Standard ceiling 68C triggers graceful auto power off
        shut_std = p226.probe_powersave_9cond_and_autotemp_fan_hil(
            auto_power_off_temp="Standard",
            internal_temp_c=68.0,
        )
        self.assertTrue(shut_std.thermal_auto_power_off_triggered)

        # High ceiling 78C triggers graceful auto power off
        shut_high = p226.probe_powersave_9cond_and_autotemp_fan_hil(
            auto_power_off_temp="High",
            mounting_state="Tripod",
            internal_temp_c=78.5,
        )
        self.assertTrue(shut_high.thermal_auto_power_off_triggered)

    def test_44_submodel_c_invalid_options_and_argument_validation(self) -> None:
        bad_ps = p226.probe_powersave_9cond_and_autotemp_fan_hil(power_save_start_time="15 Min")
        self.assertFalse(bad_ps.admitted)
        self.assertEqual(bad_ps.errno_code, p226.EINVAL_ERRNO)

        bad_temp = p226.probe_powersave_9cond_and_autotemp_fan_hil(auto_power_off_temp="Extreme")
        self.assertFalse(bad_temp.admitted)
        self.assertEqual(bad_temp.errno_code, p226.EINVAL_ERRNO)

        bad_fan = p226.probe_powersave_9cond_and_autotemp_fan_hil(fan_control="Auto1")
        self.assertFalse(bad_fan.admitted)
        self.assertEqual(bad_fan.errno_code, p226.EINVAL_ERRNO)

        with self.assertRaises(p226.RealHwSteadyShotActiveCiz4LocksPowerSaveAutoTempError):
            p226.probe_powersave_9cond_and_autotemp_fan_hil(battery_charge_pct=105)
        with self.assertRaises(p226.RealHwSteadyShotActiveCiz4LocksPowerSaveAutoTempError):
            p226.probe_powersave_9cond_and_autotemp_fan_hil(idle_elapsed_sec=-1)
        with self.assertRaises(p226.RealHwSteadyShotActiveCiz4LocksPowerSaveAutoTempError):
            p226.probe_powersave_9cond_and_autotemp_fan_hil(mounting_state="DroneUnsecured")

    def test_45_hard_safety_redline_baseline_and_all_9_forbidden_actions(self) -> None:
        base = p226.probe_hard_safety_redline()
        self.assertTrue(base.valid)
        self.assertFalse(base.persistent_emmc_writes_authorized)
        self.assertFalse(base.hardware_live_attachment_authorized)
        self.assertFalse(base.overall_ready_for_hardware_attach)
        self.assertFalse(base.spi_nor_write_authorized)
        self.assertFalse(base.el3_payload_transmit_authorized)
        self.assertFalse(base.isp_write_authorized)
        self.assertTrue(base.cnflasha_userspace_write_blocked)
        self.assertEqual(base.physical_usb_packets_emitted, 0)
        self.assertEqual(base.otp_fuse_touches, 0)
        self.assertEqual(base.rpmb_counter_increments, 0)

        for flag_name in (
            "authorize_persistent_emmc_writes",
            "authorize_hardware_live_attachment",
            "authorize_spi_nor_write",
            "authorize_el3_payload_transmit",
            "authorize_isp_write",
            "emit_physical_usb_packet",
            "touch_otp_fuse",
            "increment_rpmb_counter",
            "bypass_steadyshot_active_or_ciz_4locks_or_tier0_thermal_guard",
        ):
            bad = p226.probe_hard_safety_redline(**{flag_name: True})
            self.assertFalse(bad.valid, msg=flag_name)
            self.assertFalse(bad.persistent_emmc_writes_authorized)
            self.assertFalse(bad.hardware_live_attachment_authorized)
            self.assertFalse(bad.overall_ready_for_hardware_attach)
            self.assertFalse(bad.spi_nor_write_authorized)
            self.assertFalse(bad.el3_payload_transmit_authorized)
            self.assertFalse(bad.isp_write_authorized)
            self.assertTrue(bad.status_code.startswith("FAIL_CLOSED_REDLINE_BLOCKED:"))

    def test_46_combined_multi_redline_violation_blocked(self) -> None:
        combo = p226.probe_hard_safety_redline(
            authorize_persistent_emmc_writes=True,
            authorize_hardware_live_attachment=True,
            authorize_isp_write=True,
            bypass_steadyshot_active_or_ciz_4locks_or_tier0_thermal_guard=True,
        )
        self.assertFalse(combo.valid)
        self.assertIn("PERSISTENT_EMMC_WRITE", combo.blocked_action)
        self.assertIn("HARDWARE_LIVE_ATTACHMENT", combo.blocked_action)
        self.assertIn("ISP_WRITE", combo.blocked_action)

    def test_47_pillar_c_d_evaluator_matrix_passes_100pct(self) -> None:
        pcd = p226.evaluate_pillar_c_d_powersave_9cond_autotemp_and_redlines()
        self.assertTrue(pcd["passed"])
        self.assertEqual(len(pcd["power_save_9condition_bypass_matrix"]), 9)
        self.assertEqual(len(pcd["blocked_redline_probes"]), 9)

    # ------------------------------------------------------------------
    # Group 5: End-to-End Orchestrator, CLI, Suite >=41 & Hygiene (9)
    # ------------------------------------------------------------------
    def test_48_clean_room_audit_deterministic_digest_and_zero_leaks(self) -> None:
        r1 = _get_clean_room_audit()
        r2 = p226.run_phase226_realhw_steadyshot_active_ciz_4locks_powersave_autotemp_hil(
            force_clean_room=True
        )
        self.assertTrue(r1["all_checks_passed"])
        self.assertEqual(r1["schema"], p226.SCHEMA_ID)
        self.assertEqual(r1["source_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(r1["stage_index"], 41)
        self.assertEqual(r1["stage_total"], 41)
        self.assertEqual(r1["milestone"], "41/41")
        self.assertEqual(r1["audit_digest_sha256"], r2["audit_digest_sha256"])
        self.assertEqual(r1["redlines"]["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(r1["donor_audit"]["raw_firmware_bytes_leaked"], 0)

    def test_49_default_mode_audit_passes_all_pillars_and_redlines(self) -> None:
        rep = _get_default_audit()
        self.assertTrue(rep["all_checks_passed"])
        self.assertIn(rep["source_mode"], ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"))
        self.assertTrue(rep["pillar_a_steadyshot_active_cutoffs_hil"]["passed"])
        self.assertTrue(rep["pillar_b_ciz_digital_zoom_4locks_and_restore_hil"]["passed"])
        self.assertTrue(rep["pillar_c_d_powersave_9cond_autotemp_and_redlines"]["passed"])
        self.assertFalse(rep["redlines"]["persistent_emmc_writes_authorized"])
        self.assertFalse(rep["redlines"]["hardware_live_attachment_authorized"])
        self.assertFalse(rep["redlines"]["overall_ready_for_hardware_attach"])
        self.assertFalse(rep["redlines"]["isp_write_authorized"])

    def test_50_standalone_cli_self_test_summary_and_clean_room_json(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        script_path = str(
            FX3_VM_DIR
            / "realhw_steadyshot_active_ciz_4locks_powersave_autotemp_coemulator.py"
        )
        p_sum = subprocess.run(
            [sys.executable, "-B", script_path, "--self-test", "--summary"],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(p_sum.returncode, 0, msg=p_sum.stderr)
        self.assertIn("[PASS] Phase 226 Stage 41 (41/41)", p_sum.stdout)

        p_json = subprocess.run(
            [sys.executable, "-B", script_path, "--self-test", "--clean-room", "--json"],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(p_json.returncode, 0, msg=p_json.stderr)
        parsed = json.loads(p_json.stdout)
        self.assertTrue(parsed["all_checks_passed"])
        self.assertEqual(parsed["schema"], p226.SCHEMA_ID)
        self.assertEqual(parsed["stage_index"], 41)
        self.assertEqual(parsed["milestone"], "41/41")

    def test_51_inprocess_main_summary_and_json_exit_zero(self) -> None:
        buf_sum = io.StringIO()
        with contextlib.redirect_stdout(buf_sum):
            rc_sum = p226.main(["--self-test", "--clean-room", "--summary"])
        self.assertEqual(rc_sum, 0)
        self.assertIn("[PASS] Phase 226 Stage 41 (41/41)", buf_sum.getvalue())

        buf_json = io.StringIO()
        with contextlib.redirect_stdout(buf_json):
            rc_json = p226.main(["--self-test", "--clean-room", "--json"])
        self.assertEqual(rc_json, 0)
        data = json.loads(buf_json.getvalue())
        self.assertEqual(data["source_mode"], "CLEAN_ROOM_SYNTHETIC")

    def test_52_fx3_vm_coemulation_suite_includes_stage41_and_forward_compat_count(self) -> None:
        rep_on, dt_clean = _get_clean_room_suite()
        self.assertTrue(rep_on["all_checks_passed"])
        self.assertLess(dt_clean, 4.0)
        self.assertIn(
            "stage41_realhw_steadyshot_active_ciz_4locks_powersave_autotemp_hil",
            rep_on,
        )
        s41 = rep_on["stage41_realhw_steadyshot_active_ciz_4locks_powersave_autotemp_hil"]
        self.assertTrue(s41["all_checks_passed"])
        self.assertEqual(s41["schema"], p226.SCHEMA_ID)
        self.assertEqual(s41["milestone"], "41/41")
        self.assertFalse(s41["persistent_emmc_writes_authorized"])
        self.assertFalse(s41["hardware_live_attachment_authorized"])
        self.assertFalse(s41["overall_ready_for_hardware_attach"])
        self.assertFalse(s41["isp_write_authorized"])
        self.assertFalse(s41["spi_nor_write_authorized"])
        self.assertFalse(s41["el3_payload_transmit_authorized"])
        self.assertEqual(s41["steadyshot_active_cutoff_bypass_events"], 0)
        self.assertEqual(s41["ciz_4lock_unrestored_or_bypass_events"], 0)
        self.assertEqual(s41["tier0_p3_sleep_abort_or_thermal_burn_events"], 0)
        self.assertEqual(s41["raw_firmware_bytes_leaked"], 0)

        stage_keys = [k for k in rep_on if re.match(r"^stage\d+_", k)]
        self.assertGreaterEqual(len(stage_keys), 41)

    def test_53_fx3_vm_coemulation_suite_skip_phase226_option(self) -> None:
        rep_skip = suite.run_fx3_vm_coemulation_suite(
            suite.CoEmulationConfig(
                force_clean_room=True,
                include_phase226_realhw_steadyshot_active_ciz_4locks_powersave_autotemp_hil=False,
            )
        )
        self.assertTrue(rep_skip["all_checks_passed"])
        self.assertNotIn(
            "stage41_realhw_steadyshot_active_ciz_4locks_powersave_autotemp_hil",
            rep_skip,
        )

    def test_54_fx3_vm_coemulation_suite_default_mode_and_cli_summary_stage41(self) -> None:
        rep_def, dt_def = _get_default_suite()
        self.assertTrue(rep_def["all_checks_passed"])
        self.assertLess(dt_def, 8.0)
        s41 = rep_def["stage41_realhw_steadyshot_active_ciz_4locks_powersave_autotemp_hil"]
        self.assertTrue(s41["all_checks_passed"])
        stage_keys = [k for k in rep_def if re.match(r"^stage\d+_", k)]
        self.assertGreaterEqual(len(stage_keys), 41)

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = suite.main(["--clean-room", "--summary"])
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("[PASS] Phase 33 FX3-VM Co-Emulation", out)
        self.assertIn(
            "realhw_steadyshot_active_ciz_4locks_powersave_autotemp_hil=CLEAN_ROOM_SYNTHETIC("
            "ss_act=1.10x,ciz_locks=4,restore=1,ps_cond=9,t0_p3=1,emmc_wr=0)",
            out,
        )

    def test_55_fx3_vm_coemulation_suite_cli_skip_phase226_flag(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = suite.main(["--clean-room", "--skip-phase226", "--summary"])
        self.assertEqual(rc, 0)
        self.assertNotIn(
            "realhw_steadyshot_active_ciz_4locks_powersave_autotemp_hil=",
            buf.getvalue(),
        )

    def test_56_source_hygiene_no_write_flags_no_port_8768_and_readme_documented(self) -> None:
        src = (
            FX3_VM_DIR / "realhw_steadyshot_active_ciz_4locks_powersave_autotemp_coemulator.py"
        ).read_text(encoding="utf-8")
        forbidden_wronly = "O_" + "WRONLY"
        forbidden_rdwr = "O_" + "RDWR"
        forbidden_port = "87" + "68"
        self.assertNotIn(forbidden_wronly, src)
        self.assertNotIn(forbidden_rdwr, src)
        self.assertNotIn(forbidden_port, src)
        self.assertIn("os.O_RDONLY", src)

        readme = (FX3_VM_DIR / "README.md").read_text(encoding="utf-8")
        self.assertIn(
            "realhw_steadyshot_active_ciz_4locks_powersave_autotemp_coemulator.py",
            readme,
        )
        self.assertIn("41/41", readme)
        self.assertIn("--skip-phase226", readme)


if __name__ == "__main__":
    unittest.main()
