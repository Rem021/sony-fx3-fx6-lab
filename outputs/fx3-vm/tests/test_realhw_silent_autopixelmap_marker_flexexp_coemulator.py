#!/usr/bin/env python3
"""Unit tests for Phase 236 Stage 43 (`43/43` Milestone):
Real-Hardware `ILME-FX3` (`0x91030080`, `Ver. 2.00..7.02`) Wave-33 `[Silent Mode Settings]`
(`[Silent Mode]=On` Locking `[Shutter Type]` & `[Shutter Type in Interval]` to
`[Electronic Shutter]`, `[Audio signals]=Off`, & All 5 Disabled Shooting Functions),
`[Target Function Settings]` (`[Aperture Drive in AF]` & `[Auto Pixel Mapping]` Power-Off
Mechanical-Shutter Calibration Suppression vs `[Not Target]`), Hardware Absence Rejection
of `[Shutter When Pwr OFF]` on `ILME-FX3`, `[Marker Display]` (`Center Marker`, `Aspect Marker`
`Off` + All 15 Ver. 3.00+/7.02 Ratios `9:16`..`2.39:1`, `Safety Zone` `Off/80%/90%`,
`Guideframe`) Survival Across `[Camera Settings Reset]` (Cleared Only by `[Initialize]`) &
Strict Local-LCD-Only HDMI Isolation (`0` External HDMI Marker Pixels Even When
`[HDMI Info. Display]=On`), and `[Exposure Ctrl Type]` (`P/A/S/M Mode` vs `Flexible Exp. Mode`)
Asymmetric Reset Split HIL Co-Emulator.
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
import realhw_silent_autopixelmap_marker_flexexp_coemulator as p236  # noqa: E402


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
            p236.run_phase236_realhw_silent_autopixelmap_marker_flexexp_hil(
                force_clean_room=True
            )
        )
    return _CLEAN_ROOM_AUDIT_CACHE


def _get_default_audit():
    global _DEFAULT_AUDIT_CACHE
    if _DEFAULT_AUDIT_CACHE is None:
        _DEFAULT_AUDIT_CACHE = (
            p236.run_phase236_realhw_silent_autopixelmap_marker_flexexp_hil()
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


class TestPhase236SilentAutoPixelMapMarkerFlexExpCoEmulator(unittest.TestCase):
    # ------------------------------------------------------------------
    # Group 1: Schema, Milestone 43/43, Read-Only Donor Inspection (8)
    # ------------------------------------------------------------------
    def test_01_schema_version_stage_43_milestone_and_redline_constants(self) -> None:
        self.assertEqual(
            p236.SCHEMA_ID,
            "realhw_silent_autopixelmap_marker_flexexp_coemulator_v1",
        )
        self.assertEqual(p236.PHASE_236_SCHEMA, p236.SCHEMA_ID)
        self.assertEqual(p236.PHASE_236_VERSION, "236.0.0")
        self.assertEqual(p236.STAGE_INDEX, 43)
        self.assertEqual(p236.STAGE_TOTAL, 43)
        self.assertEqual(p236.MILESTONE_LABEL, "43/43")
        self.assertEqual(
            p236.STAGE_NAME,
            "stage43_realhw_silent_autopixelmap_marker_flexexp_hil",
        )
        self.assertEqual(p236.FX3_MODEL_ID, 0x91030080)
        self.assertTrue(p236.P8_CP_MUTATION_FORBIDDEN)
        self.assertTrue(p236.CNFLASHA_USERSPACE_WRITE_BLOCKED)
        self.assertEqual(p236.CNFLASHA_MUTATION_BYTES, 0)
        self.assertFalse(p236.PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(p236.HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        self.assertFalse(p236.OVERALL_READY_FOR_HARDWARE_ATTACH)
        self.assertFalse(p236.ISP_WRITE_AUTHORIZED)
        self.assertFalse(p236.SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(p236.EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        self.assertEqual(p236.PHYSICAL_USB_PACKETS_EMITTED, 0)
        self.assertEqual(p236.OTP_FUSE_TOUCHES, 0)
        self.assertEqual(p236.RPMB_COUNTER_INCREMENTS, 0)
        self.assertEqual(p236.SILENT_MODE_5FUNC_OR_PWRSHUTTER_BYPASS_EVENTS, 0)
        self.assertEqual(p236.BENCH_SHUTDOWN_UNSUPPRESSED_AUTO_PIXELMAP_EVENTS, 0)
        self.assertEqual(p236.HDMI_MARKER_LEAKED_OVERLAY_PIXELS, 0)
        self.assertEqual(p236.FLEXEXP_OR_MARKER_RESET_SPLIT_DRIFT_EVENTS, 0)
        self.assertEqual(p236.RAW_FIRMWARE_BYTES_LEAKED, 0)
        self.assertEqual(p236.DONOR_ACCESS_MODE, "O_RDONLY")

    def test_02_donor_inspection_fast_bounded_and_cached(self) -> None:
        p236._DONOR_AUDIT_CACHE.clear()
        t0 = time.monotonic()
        da1 = p236.inspect_phase236_donors(force_clean_room=False)
        dt1 = time.monotonic() - t0
        t1 = time.monotonic()
        da2 = p236.inspect_phase236_donors(force_clean_room=False)
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
        da = p236.inspect_phase236_donors(force_clean_room=True)
        self.assertEqual(da.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(da.all_contracts_verified)
        self.assertTrue(da.silent_mode_autopixelmap_no_pwrshutter_proven)
        self.assertTrue(da.marker_15ratio_persistence_and_hdmi_isolation_proven)
        self.assertTrue(da.flexible_exp_and_auto_slow_shutter_reset_split_proven)
        self.assertEqual(da.donor_files_inspected, 12)
        self.assertEqual(da.raw_firmware_bytes_leaked, 0)

    def test_04_env_force_clean_room_flag_variants(self) -> None:
        for truthy in ("1", "true", "TRUE", "yes", "on"):
            self.assertTrue(p236.is_forced_clean_room({p236.ENV_FORCE_CLEAN_ROOM: truthy}))
        for falsy in ("", "0", "false", "no", "off"):
            self.assertFalse(p236.is_forced_clean_room({p236.ENV_FORCE_CLEAN_ROOM: falsy}))

        paths = p236.resolve_phase236_donor_paths(env={p236.ENV_FORCE_CLEAN_ROOM: "1"})
        self.assertEqual(len(paths), 12)
        for p in paths.values():
            self.assertIn(p236.CLEAN_ROOM_SENTINEL_DIRNAME, str(p))

    def test_05_missing_donor_directory_falls_back_cleanly_to_synthetic(self) -> None:
        env = {
            p236.ENV_FORCE_CLEAN_ROOM: "0",
            p236.ENV_MAC_WORK_ROOT: "/nonexistent/fx3_wave33_work_root",
        }
        da = p236.inspect_phase236_donors(env=env)
        self.assertTrue(da.all_contracts_verified)
        self.assertEqual(da.raw_firmware_bytes_leaked, 0)

    def test_06_large_donors_strictly_bounded_window_reads(self) -> None:
        da = p236.inspect_phase236_donors()
        for key in ("fx3_appfw", "fx6_appfw", "fx3_cpapp", "fx6_cpapp", "fx3_libmpr", "fx6_libmpr"):
            summary = getattr(da, key)
            self.assertTrue(summary.bounded_windows_only, msg=key)
            self.assertLessEqual(summary.bytes_read_total, 16 * p236.BOUNDED_WINDOW_MAX_BYTES)
            self.assertEqual(summary.file_bytes, p236.EXPECTED_DONOR_BYTES[key])
            self.assertTrue(all(v == 1 for v in summary.window_hits.values()), msg=key)

    def test_07_compact_uxc_wave33_menu_tokens_verified(self) -> None:
        da = p236.inspect_phase236_donors()
        hits = da.fx3_string_en_f.marker_hits
        for tok in (
            "Silent Mode Settings",
            "Silent Mode",
            "Target Function Settings",
            "Target",
            "Not Target",
            "Aperture Drive in AF",
            "Auto Pixel Mapping",
            "Pixel Mapping",
            "Sensor Cleaning",
            "Shutter Type",
            "Shutter Type in Interval",
            "Electronic Shutter",
            "Long Exposure NR",
            "e-Front Curtain Shut.",
            "Anti-flicker Shoot.",
            "BULB",
            "Flash",
            "Marker Display",
            "Center Marker",
            "Aspect Marker",
            "Safety Zone",
            "Guideframe",
            "HDMI Info. Display",
            "Exposure Ctrl Type",
            "P/A/S/M Mode",
            "Flexible Exp. Mode",
            "Auto/Manual Swt. Set.",
            "Av Auto/Manual Switch",
            "Tv Auto/Manual Switch",
            "ISO Auto/Manual Set",
            "Auto Slow Shutter",
            "Camera Settings Reset",
            "Initialize",
        ):
            self.assertEqual(hits.get(tok), 1, msg=f"Missing token {tok!r}")
        for ratio in p236.ASPECT_MARKER_15_RATIOS:
            self.assertEqual(hits.get(ratio), 1, msg=f"Missing aspect ratio {ratio!r}")

    def test_08_zero_raw_firmware_bytes_leaked_in_serialized_payload(self) -> None:
        rep = _get_default_audit()
        dumped = json.dumps(rep, sort_keys=True)
        self.assertNotIn("\\x7fELF", dumped)
        self.assertNotIn("uxc\\x07", dumped)
        self.assertEqual(rep["redlines"]["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(rep["donor_audit"]["raw_firmware_bytes_leaked"], 0)

    # ------------------------------------------------------------------
    # Group 2: Sub-model A — Silent Mode Settings, Auto Pixel Mapping
    #          Target & Shutter When Pwr OFF Hardware Absence (16)
    # ------------------------------------------------------------------
    def test_09_silent_mode_on_locks_shutter_types_to_electronic_and_audio_off(self) -> None:
        res = p236.probe_silent_mode_autopixelmap_and_no_pwrshutter_hil(
            silent_mode="On",
            configured_shutter_type="Mechanical Shutter",
            configured_shutter_type_in_interval="Mechanical Shutter",
            configured_audio_signals="On",
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.effective_shutter_type, "Electronic Shutter")
        self.assertEqual(res.effective_shutter_type_in_interval, "Electronic Shutter")
        self.assertEqual(res.effective_audio_signals, "Off")
        self.assertEqual(res.disabled_shooting_functions, p236.SILENT_MODE_5_DISABLED_FUNCTIONS)

    def test_10_silent_mode_off_retains_mechanical_shutter_and_audio_signals_on(self) -> None:
        res = p236.probe_silent_mode_autopixelmap_and_no_pwrshutter_hil(
            silent_mode="Off",
            configured_shutter_type="Mechanical Shutter",
            configured_shutter_type_in_interval="Mechanical Shutter",
            configured_audio_signals="On",
            requested_shooting_functions=p236.SILENT_MODE_5_DISABLED_FUNCTIONS,
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.effective_shutter_type, "Mechanical Shutter")
        self.assertEqual(res.effective_shutter_type_in_interval, "Mechanical Shutter")
        self.assertEqual(res.effective_audio_signals, "On")
        self.assertEqual(res.disabled_shooting_functions, ())

    def test_11_silent_mode_on_blocks_flash_shooting_eopnotsupp(self) -> None:
        res = p236.probe_silent_mode_autopixelmap_and_no_pwrshutter_hil(
            silent_mode="On",
            requested_shooting_functions=("Flash",),
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p236.EOPNOTSUPP_ERRNO)
        self.assertIn("Flash", res.blocked_function_requests)

    def test_12_silent_mode_on_blocks_long_exposure_nr_eopnotsupp(self) -> None:
        res = p236.probe_silent_mode_autopixelmap_and_no_pwrshutter_hil(
            silent_mode="On",
            requested_shooting_functions=("Long Exposure NR",),
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p236.EOPNOTSUPP_ERRNO)
        self.assertIn("Long Exposure NR", res.blocked_function_requests)

    def test_13_silent_mode_on_blocks_efront_curtain_shutter_eopnotsupp(self) -> None:
        res = p236.probe_silent_mode_autopixelmap_and_no_pwrshutter_hil(
            silent_mode="On",
            requested_shooting_functions=("e-Front Curtain Shut.",),
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p236.EOPNOTSUPP_ERRNO)
        self.assertIn("e-Front Curtain Shut.", res.blocked_function_requests)

    def test_14_silent_mode_on_blocks_bulb_shooting_eopnotsupp(self) -> None:
        res = p236.probe_silent_mode_autopixelmap_and_no_pwrshutter_hil(
            silent_mode="On",
            requested_shooting_functions=("BULB",),
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p236.EOPNOTSUPP_ERRNO)
        self.assertIn("BULB", res.blocked_function_requests)

    def test_15_silent_mode_on_blocks_antiflicker_shoot_eopnotsupp(self) -> None:
        res = p236.probe_silent_mode_autopixelmap_and_no_pwrshutter_hil(
            silent_mode="On",
            requested_shooting_functions=("Anti-flicker Shoot.",),
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p236.EOPNOTSUPP_ERRNO)
        self.assertIn("Anti-flicker Shoot.", res.blocked_function_requests)

    def test_16_silent_mode_on_blocks_forcing_mech_shutter_or_audio_signals(self) -> None:
        r_sh = p236.probe_silent_mode_autopixelmap_and_no_pwrshutter_hil(
            silent_mode="On",
            attempt_force_mechanical_shutter_in_silent=True,
        )
        self.assertFalse(r_sh.admitted)
        self.assertEqual(r_sh.errno_code, p236.EOPNOTSUPP_ERRNO)

        r_aud = p236.probe_silent_mode_autopixelmap_and_no_pwrshutter_hil(
            silent_mode="On",
            attempt_force_audio_signals_in_silent=True,
        )
        self.assertFalse(r_aud.admitted)
        self.assertEqual(r_aud.errno_code, p236.EOPNOTSUPP_ERRNO)

    def test_17_target_function_settings_target_suppresses_poweroff_auto_pixel_mapping(self) -> None:
        res = p236.probe_silent_mode_autopixelmap_and_no_pwrshutter_hil(
            silent_mode="On",
            aperture_drive_in_af_target="Target",
            configured_aperture_drive_in_af="Standard",
            auto_pixel_mapping_target="Target",
            configured_auto_pixel_mapping="On",
            power_off_event=True,
            periodic_pixelmap_timer_due=True,
            controlled_tier0_bench_shutdown=True,
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.effective_aperture_drive_in_af, "Silent Priority")
        self.assertEqual(res.effective_auto_pixel_mapping, "Off")
        self.assertEqual(res.poweroff_mech_shutter_darkframe_actuations, 0)
        self.assertEqual(res.poweroff_cnflasha_calibration_touches, 0)

    def test_18_target_function_settings_not_target_retains_configured_values(self) -> None:
        res = p236.probe_silent_mode_autopixelmap_and_no_pwrshutter_hil(
            silent_mode="On",
            aperture_drive_in_af_target="Not Target",
            configured_aperture_drive_in_af="Focus Priority",
            auto_pixel_mapping_target="Not Target",
            configured_auto_pixel_mapping="On",
            power_off_event=True,
            periodic_pixelmap_timer_due=True,
            controlled_tier0_bench_shutdown=False,
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.effective_aperture_drive_in_af, "Focus Priority")
        self.assertEqual(res.effective_auto_pixel_mapping, "On")
        self.assertEqual(res.poweroff_mech_shutter_darkframe_actuations, 1)
        self.assertEqual(res.poweroff_cnflasha_calibration_touches, 0)

    def test_19_controlled_tier0_bench_shutdown_blocks_unsuppressed_auto_pixel_mapping(self) -> None:
        r_silent_not_target = p236.probe_silent_mode_autopixelmap_and_no_pwrshutter_hil(
            silent_mode="On",
            auto_pixel_mapping_target="Not Target",
            configured_auto_pixel_mapping="On",
            power_off_event=True,
            periodic_pixelmap_timer_due=True,
            controlled_tier0_bench_shutdown=True,
        )
        self.assertFalse(r_silent_not_target.admitted)
        self.assertEqual(r_silent_not_target.errno_code, p236.EBUSY_ERRNO)
        self.assertEqual(r_silent_not_target.poweroff_mech_shutter_darkframe_actuations, 0)

        r_silent_off = p236.probe_silent_mode_autopixelmap_and_no_pwrshutter_hil(
            silent_mode="Off",
            configured_auto_pixel_mapping="On",
            power_off_event=True,
            periodic_pixelmap_timer_due=True,
            controlled_tier0_bench_shutdown=True,
        )
        self.assertFalse(r_silent_off.admitted)
        self.assertEqual(r_silent_off.errno_code, p236.EBUSY_ERRNO)

    def test_20_controlled_tier0_bench_shutdown_admits_explicit_auto_pixelmap_off(self) -> None:
        res = p236.probe_silent_mode_autopixelmap_and_no_pwrshutter_hil(
            silent_mode="Off",
            configured_auto_pixel_mapping="Off",
            power_off_event=True,
            periodic_pixelmap_timer_due=True,
            controlled_tier0_bench_shutdown=True,
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.effective_auto_pixel_mapping, "Off")
        self.assertEqual(res.poweroff_mech_shutter_darkframe_actuations, 0)

    def test_21_shutter_when_pwr_off_rejected_across_all_fx3_firmware_versions(self) -> None:
        for ver in p236.VALID_FX3_FIRMWARE_VERSIONS:
            res = p236.probe_silent_mode_autopixelmap_and_no_pwrshutter_hil(
                firmware_version=ver,
                request_shutter_when_pwr_off="On",
            )
            self.assertFalse(res.admitted, msg=ver)
            self.assertEqual(res.errno_code, p236.EOPNOTSUPP_ERRNO, msg=ver)
            self.assertFalse(res.shutter_when_pwr_off_hardware_present, msg=ver)
            self.assertEqual(
                res.exposed_anti_dust_items,
                ("Sensor Cleaning", "Auto Pixel Mapping", "Pixel Mapping"),
            )

    def test_22_shutter_when_pwr_off_rejected_when_targeted_or_in_functions_list(self) -> None:
        r_tgt = p236.probe_silent_mode_autopixelmap_and_no_pwrshutter_hil(
            attempt_target_shutter_when_pwr_off=True,
        )
        self.assertFalse(r_tgt.admitted)
        self.assertEqual(r_tgt.errno_code, p236.EOPNOTSUPP_ERRNO)

        r_fn = p236.probe_silent_mode_autopixelmap_and_no_pwrshutter_hil(
            requested_shooting_functions=("Shutter When Pwr OFF",),
        )
        self.assertFalse(r_fn.admitted)
        self.assertEqual(r_fn.errno_code, p236.EOPNOTSUPP_ERRNO)

    def test_23_silent_mode_invalid_inputs_rejected_einval(self) -> None:
        bad_cases = (
            {"body_model": "ILCE-7SM3"},
            {"firmware_version": "1.00"},
            {"silent_mode": "Maybe"},
            {"configured_shutter_type": "Leaf Shutter"},
            {"configured_shutter_type_in_interval": "Auto"},
            {"configured_audio_signals": "Loud"},
            {"aperture_drive_in_af_target": "Always"},
            {"configured_aperture_drive_in_af": "Turbo"},
            {"auto_pixel_mapping_target": "Always"},
            {"configured_auto_pixel_mapping": "Sometimes"},
            {"requested_shooting_functions": ("Nonexistent Mode",)},
        )
        for kwargs in bad_cases:
            res = p236.probe_silent_mode_autopixelmap_and_no_pwrshutter_hil(**kwargs)
            self.assertFalse(res.admitted, msg=str(kwargs))
            self.assertEqual(res.errno_code, p236.EINVAL_ERRNO, msg=str(kwargs))

    def test_24_pillar_a_evaluator_all_scenarios_green(self) -> None:
        pa = p236.evaluate_pillar_a_silent_mode_autopixelmap_and_no_pwrshutter_hil()
        self.assertTrue(pa["passed"])
        self.assertEqual(len(pa["all_5_silent_disabled_functions"]), 5)
        self.assertEqual(
            pa["exposed_fx3_anti_dust_items"],
            ["Sensor Cleaning", "Auto Pixel Mapping", "Pixel Mapping"],
        )

    # ------------------------------------------------------------------
    # Group 3: Sub-model B — Marker Display 15 Ratios, Reset Survival &
    #          Strict Local-LCD-Only HDMI Isolation (14)
    # ------------------------------------------------------------------
    def test_25_all_15_ver702_aspect_marker_ratios_admitted_and_exact_set(self) -> None:
        expected_15 = (
            "9:16",
            "4:5",
            "1:1",
            "4:3",
            "13:9",
            "14:9",
            "15:9",
            "16:9",
            "17:9",
            "1.66:1",
            "1.85:1",
            "1.91:1",
            "2:1",
            "2.35:1",
            "2.39:1",
        )
        self.assertEqual(p236.ASPECT_MARKER_15_RATIOS, expected_15)
        self.assertEqual(len(p236.ASPECT_MARKER_15_RATIOS), 15)
        for ratio in expected_15:
            res = p236.probe_marker_display_15ratio_and_hdmi_isolation_hil(
                firmware_version="7.02",
                configured_marker_display="On",
                configured_aspect_marker=ratio,
                hdmi_connected=True,
                hdmi_info_display="On",
            )
            self.assertTrue(res.admitted, msg=ratio)
            self.assertEqual(res.effective_aspect_marker, ratio)
            self.assertTrue(res.local_lcd_marker_overlay_active)
            self.assertEqual(res.hdmi_marker_leaked_overlay_pixels, 0)

    def test_26_aspect_marker_16_9_rejected_on_ver200_admitted_on_ver300_plus(self) -> None:
        r200 = p236.probe_marker_display_15ratio_and_hdmi_isolation_hil(
            firmware_version="2.00",
            configured_aspect_marker="16:9",
        )
        self.assertFalse(r200.admitted)
        self.assertEqual(r200.errno_code, p236.EOPNOTSUPP_ERRNO)

        for ver in ("3.00", "4.00", "5.00", "6.00", "7.00", "7.02"):
            r_ok = p236.probe_marker_display_15ratio_and_hdmi_isolation_hil(
                firmware_version=ver,
                configured_aspect_marker="16:9",
            )
            self.assertTrue(r_ok.admitted, msg=ver)
            self.assertEqual(r_ok.effective_aspect_marker, "16:9")

    def test_27_marker_display_survives_camera_settings_reset_intact(self) -> None:
        res = p236.probe_marker_display_15ratio_and_hdmi_isolation_hil(
            configured_marker_display="On",
            configured_center_marker="On",
            configured_aspect_marker="2.39:1",
            configured_safety_zone="90%",
            configured_guideframe="On",
            reset_action="Camera Settings Reset",
        )
        self.assertTrue(res.admitted)
        self.assertTrue(res.marker_survived_camera_settings_reset)
        self.assertFalse(res.marker_cleared_by_initialize)
        self.assertEqual(res.effective_marker_display, "On")
        self.assertEqual(res.effective_center_marker, "On")
        self.assertEqual(res.effective_aspect_marker, "2.39:1")
        self.assertEqual(res.effective_safety_zone, "90%")
        self.assertEqual(res.effective_guideframe, "On")

    def test_28_marker_display_cleared_to_off_only_by_initialize(self) -> None:
        res = p236.probe_marker_display_15ratio_and_hdmi_isolation_hil(
            configured_marker_display="On",
            configured_center_marker="On",
            configured_aspect_marker="2.39:1",
            configured_safety_zone="80%",
            configured_guideframe="On",
            reset_action="Initialize",
        )
        self.assertTrue(res.admitted)
        self.assertFalse(res.marker_survived_camera_settings_reset)
        self.assertTrue(res.marker_cleared_by_initialize)
        self.assertEqual(res.effective_marker_display, "Off")
        self.assertEqual(res.effective_center_marker, "Off")
        self.assertEqual(res.effective_aspect_marker, "Off")
        self.assertEqual(res.effective_safety_zone, "Off")
        self.assertEqual(res.effective_guideframe, "Off")
        self.assertEqual(res.local_lcd_marker_overlay_pixels, 0)

    def test_29_hdmi_zero_marker_pixels_even_when_hdmi_info_display_is_on(self) -> None:
        res = p236.probe_marker_display_15ratio_and_hdmi_isolation_hil(
            configured_marker_display="On",
            configured_center_marker="On",
            configured_aspect_marker="1.85:1",
            configured_safety_zone="80%",
            configured_guideframe="On",
            hdmi_connected=True,
            hdmi_info_display="On",
        )
        self.assertTrue(res.admitted)
        self.assertTrue(res.local_lcd_marker_overlay_active)
        self.assertGreater(res.local_lcd_marker_overlay_pixels, 0)
        self.assertTrue(res.hdmi_info_telemetry_osd_active)
        self.assertFalse(res.hdmi_marker_overlay_rendered)
        self.assertEqual(res.hdmi_center_marker_pixels, 0)
        self.assertEqual(res.hdmi_aspect_marker_pixels, 0)
        self.assertEqual(res.hdmi_safety_zone_pixels, 0)
        self.assertEqual(res.hdmi_guideframe_pixels, 0)
        self.assertEqual(res.hdmi_marker_leaked_overlay_pixels, 0)

    def test_30_hdmi_info_display_off_or_disconnected_keeps_zero_hdmi_markers(self) -> None:
        r_info_off = p236.probe_marker_display_15ratio_and_hdmi_isolation_hil(
            configured_marker_display="On",
            configured_aspect_marker="4:3",
            hdmi_connected=True,
            hdmi_info_display="Off",
        )
        self.assertTrue(r_info_off.admitted)
        self.assertFalse(r_info_off.hdmi_info_telemetry_osd_active)
        self.assertEqual(r_info_off.hdmi_marker_leaked_overlay_pixels, 0)

        r_disc = p236.probe_marker_display_15ratio_and_hdmi_isolation_hil(
            configured_marker_display="On",
            configured_aspect_marker="9:16",
            hdmi_connected=False,
            hdmi_info_display="On",
        )
        self.assertTrue(r_disc.admitted)
        self.assertFalse(r_disc.hdmi_info_telemetry_osd_active)
        self.assertEqual(r_disc.hdmi_marker_leaked_overlay_pixels, 0)

    def test_31_forcing_hdmi_marker_overlay_rejected_eopnotsupp(self) -> None:
        res = p236.probe_marker_display_15ratio_and_hdmi_isolation_hil(
            configured_marker_display="On",
            configured_aspect_marker="2.39:1",
            hdmi_connected=True,
            hdmi_info_display="On",
            attempt_force_hdmi_marker_overlay=True,
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p236.EOPNOTSUPP_ERRNO)
        self.assertEqual(res.hdmi_marker_leaked_overlay_pixels, 0)

    def test_32_marker_display_off_suppresses_local_lcd_overlay_even_if_submarkers_on(self) -> None:
        res = p236.probe_marker_display_15ratio_and_hdmi_isolation_hil(
            configured_marker_display="Off",
            configured_center_marker="On",
            configured_aspect_marker="2.39:1",
            configured_safety_zone="90%",
            configured_guideframe="On",
        )
        self.assertTrue(res.admitted)
        self.assertFalse(res.local_lcd_marker_overlay_active)
        self.assertEqual(res.local_lcd_marker_overlay_pixels, 0)

    def test_33_marker_display_all_submarkers_off_yields_zero_local_lcd_pixels(self) -> None:
        res = p236.probe_marker_display_15ratio_and_hdmi_isolation_hil(
            configured_marker_display="On",
            configured_center_marker="Off",
            configured_aspect_marker="Off",
            configured_safety_zone="Off",
            configured_guideframe="Off",
        )
        self.assertTrue(res.admitted)
        self.assertFalse(res.local_lcd_marker_overlay_active)
        self.assertEqual(res.local_lcd_marker_overlay_pixels, 0)

    def test_34_safety_zone_off_80pct_90pct_all_admitted(self) -> None:
        for sz in ("Off", "80%", "90%"):
            res = p236.probe_marker_display_15ratio_and_hdmi_isolation_hil(
                configured_marker_display="On",
                configured_center_marker="Off",
                configured_aspect_marker="Off",
                configured_safety_zone=sz,
                configured_guideframe="Off",
            )
            self.assertTrue(res.admitted, msg=sz)
            self.assertEqual(res.effective_safety_zone, sz)

    def test_35_local_lcd_marker_pixel_budget_additive_across_4_submarkers(self) -> None:
        res = p236.probe_marker_display_15ratio_and_hdmi_isolation_hil(
            configured_marker_display="On",
            configured_center_marker="On",
            configured_aspect_marker="2.35:1",
            configured_safety_zone="80%",
            configured_guideframe="On",
        )
        expected_px = (
            p236.LCD_CENTER_MARKER_PIXELS
            + p236.LCD_ASPECT_MARKER_PIXELS
            + p236.LCD_SAFETY_ZONE_PIXELS
            + p236.LCD_GUIDEFRAME_PIXELS
        )
        self.assertEqual(res.local_lcd_marker_overlay_pixels, expected_px)

    def test_36_marker_invalid_parameters_rejected_einval(self) -> None:
        bad_cases = (
            {"firmware_version": "9.99"},
            {"configured_marker_display": "Auto"},
            {"configured_center_marker": "Crosshair"},
            {"configured_aspect_marker": "3:2"},
            {"configured_safety_zone": "95%"},
            {"configured_guideframe": "Thirds"},
            {"reset_action": "Soft Reboot"},
            {"hdmi_info_display": "Clean"},
        )
        for kwargs in bad_cases:
            res = p236.probe_marker_display_15ratio_and_hdmi_isolation_hil(**kwargs)
            self.assertFalse(res.admitted, msg=str(kwargs))
            self.assertEqual(res.errno_code, p236.EINVAL_ERRNO, msg=str(kwargs))

    def test_37_pillar_b_evaluator_15ratio_matrix_and_hdmi_isolation_green(self) -> None:
        pb = p236.evaluate_pillar_b_marker_15ratio_persistence_and_hdmi_isolation_hil()
        self.assertTrue(pb["passed"])
        self.assertEqual(len(pb["ratio_15_camera_settings_reset_and_hdmi_0px_matrix"]), 15)

    def test_38_vertical_social_aspect_markers_9_16_and_4_5_survive_csr_hdmi_0px(self) -> None:
        for ratio in ("9:16", "4:5", "1:1"):
            res = p236.probe_marker_display_15ratio_and_hdmi_isolation_hil(
                configured_marker_display="On",
                configured_aspect_marker=ratio,
                reset_action="Camera Settings Reset",
                hdmi_connected=True,
                hdmi_info_display="On",
            )
            self.assertTrue(res.admitted)
            self.assertTrue(res.marker_survived_camera_settings_reset)
            self.assertEqual(res.effective_aspect_marker, ratio)
            self.assertEqual(res.hdmi_marker_leaked_overlay_pixels, 0)

    # ------------------------------------------------------------------
    # Group 4: Sub-model C & Redlines — Exposure Ctrl Type, Flexible Exp.
    #          Mode Reset Split, CAMSET Recall & Safety Redlines (13)
    # ------------------------------------------------------------------
    def test_39_flexible_exp_mode_independent_av_tv_iso_switches_and_slow_shutter(self) -> None:
        res = p236.probe_flexible_exp_mode_and_reset_split_hil(
            exposure_ctrl_type="Flexible Exp. Mode",
            configured_av_switch="Auto",
            configured_tv_switch="Manual",
            configured_iso_switch="Auto",
            configured_auto_slow_shutter="Off",
        )
        self.assertTrue(res.admitted)
        self.assertTrue(res.auto_manual_swt_menu_available)
        self.assertEqual(res.effective_av_switch, "Auto")
        self.assertEqual(res.effective_tv_switch, "Manual")
        self.assertEqual(res.effective_iso_switch, "Auto")
        self.assertEqual(res.effective_auto_slow_shutter, "Off")

    def test_40_pasm_4_submodes_effective_av_tv_mapping_and_swt_menu_lock(self) -> None:
        expected = {
            "Program Auto": ("Auto", "Auto"),
            "Aperture Priority": ("Manual", "Auto"),
            "Shutter Priority": ("Auto", "Manual"),
            "Manual Exposure": ("Manual", "Manual"),
        }
        for sub, (exp_av, exp_tv) in expected.items():
            res = p236.probe_flexible_exp_mode_and_reset_split_hil(
                exposure_ctrl_type="P/A/S/M Mode",
                pasm_submode=sub,
                configured_iso_switch="Auto",
            )
            self.assertTrue(res.admitted, msg=sub)
            self.assertFalse(res.auto_manual_swt_menu_available)
            self.assertEqual((res.effective_av_switch, res.effective_tv_switch), (exp_av, exp_tv))

        r_blk = p236.probe_flexible_exp_mode_and_reset_split_hil(
            exposure_ctrl_type="P/A/S/M Mode",
            pasm_submode="Manual Exposure",
            attempt_auto_manual_swt_in_pasm=True,
        )
        self.assertFalse(r_blk.admitted)
        self.assertEqual(r_blk.errno_code, p236.EOPNOTSUPP_ERRNO)

    def test_41_camera_settings_reset_resets_flexexp_manual_and_slow_shutter_on_while_marker_survives(
        self,
    ) -> None:
        res = p236.probe_flexible_exp_mode_and_reset_split_hil(
            exposure_ctrl_type="Flexible Exp. Mode",
            configured_av_switch="Auto",
            configured_tv_switch="Auto",
            configured_iso_switch="Auto",
            configured_auto_slow_shutter="Off",
            configured_marker_display="On",
            configured_aspect_marker="2.39:1",
            reset_action="Camera Settings Reset",
        )
        self.assertTrue(res.admitted)
        self.assertTrue(res.flexexp_switches_reset_by_camera_settings_reset)
        self.assertTrue(res.auto_slow_shutter_reset_by_camera_settings_reset)
        self.assertTrue(res.marker_survived_while_flexexp_reset_split_verified)
        self.assertEqual(res.effective_av_switch, "Manual")
        self.assertEqual(res.effective_tv_switch, "Manual")
        self.assertEqual(res.effective_iso_switch, "Manual")
        self.assertEqual(res.effective_auto_slow_shutter, "On")
        self.assertEqual(res.effective_marker_display, "On")
        self.assertEqual(res.effective_aspect_marker, "2.39:1")

    def test_42_initialize_resets_both_flexexp_and_marker_display_to_factory_defaults(self) -> None:
        res = p236.probe_flexible_exp_mode_and_reset_split_hil(
            exposure_ctrl_type="Flexible Exp. Mode",
            configured_av_switch="Auto",
            configured_tv_switch="Auto",
            configured_iso_switch="Auto",
            configured_auto_slow_shutter="Off",
            configured_marker_display="On",
            configured_aspect_marker="1.85:1",
            reset_action="Initialize",
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.effective_av_switch, "Manual")
        self.assertEqual(res.effective_tv_switch, "Manual")
        self.assertEqual(res.effective_iso_switch, "Manual")
        self.assertEqual(res.effective_auto_slow_shutter, "On")
        self.assertEqual(res.effective_marker_display, "Off")
        self.assertEqual(res.effective_aspect_marker, "Off")

    def test_43_three_step_lifecycle_configured_csr_split_and_initialize(self) -> None:
        lc = p236.simulate_marker_and_flexexp_reset_vs_initialize_lifecycle(
            configured_aspect_marker="2.35:1",
            configured_av_switch="Auto",
            configured_tv_switch="Auto",
            configured_iso_switch="Auto",
            configured_auto_slow_shutter="Off",
        )
        self.assertTrue(lc["lifecycle_verified"])
        self.assertEqual(lc["step2_camera_settings_reset_split"]["effective_av_switch"], "Manual")
        self.assertEqual(
            lc["step2_camera_settings_reset_split"]["effective_auto_slow_shutter"], "On"
        )
        self.assertEqual(
            lc["step2_camera_settings_reset_split"]["effective_aspect_marker"], "2.35:1"
        )
        self.assertEqual(lc["step3_initialize_full_clear"]["effective_aspect_marker"], "Off")

    def test_44_slot1_camset01_to_camset10_restore_flexexp_zero_nvram_writes(self) -> None:
        for idx in range(1, 11):
            fname = f"CAMSET{idx:02d}.DAT"
            res = p236.probe_flexible_exp_mode_and_reset_split_hil(
                reset_action="Camera Settings Reset",
                restore_from_slot1_camset=fname,
                saved_camset_av_switch="Auto",
                saved_camset_tv_switch="Manual",
                saved_camset_iso_switch="Auto",
                saved_camset_auto_slow_shutter="Off",
            )
            self.assertTrue(res.admitted, msg=fname)
            self.assertEqual(res.slot1_camset_restored, fname)
            self.assertEqual(res.effective_av_switch, "Auto")
            self.assertEqual(res.effective_tv_switch, "Manual")
            self.assertEqual(res.effective_iso_switch, "Auto")
            self.assertEqual(res.effective_auto_slow_shutter, "Off")
            self.assertEqual(res.bk4_persistent_nvram_writes, 0)

    def test_45_invalid_slot1_camset_filename_or_payload_rejected_einval(self) -> None:
        for bad_name in ("CAMSET00.DAT", "CAMSET11.DAT", "../CAMSET01.DAT", "BACKUP.BIN"):
            res = p236.probe_flexible_exp_mode_and_reset_split_hil(
                restore_from_slot1_camset=bad_name
            )
            self.assertFalse(res.admitted, msg=bad_name)
            self.assertEqual(res.errno_code, p236.EINVAL_ERRNO, msg=bad_name)

        res_bad_payload = p236.probe_flexible_exp_mode_and_reset_split_hil(
            restore_from_slot1_camset="CAMSET01.DAT",
            saved_camset_av_switch="Invalid",
        )
        self.assertFalse(res_bad_payload.admitted)
        self.assertEqual(res_bad_payload.errno_code, p236.EINVAL_ERRNO)

    def test_46_flexexp_invalid_parameters_rejected_einval(self) -> None:
        bad_cases = (
            {"exposure_ctrl_type": "Cine EI Mode"},
            {"pasm_submode": "Bulb Auto"},
            {"configured_av_switch": "Semi"},
            {"configured_tv_switch": "Locked"},
            {"configured_iso_switch": "Gain"},
            {"configured_auto_slow_shutter": "Auto"},
            {"configured_marker_display": "Invalid"},
            {"configured_aspect_marker": "16:10"},
            {"reset_action": "Factory Wipe"},
        )
        for kwargs in bad_cases:
            res = p236.probe_flexible_exp_mode_and_reset_split_hil(**kwargs)
            self.assertFalse(res.admitted, msg=str(kwargs))
            self.assertEqual(res.errno_code, p236.EINVAL_ERRNO, msg=str(kwargs))

    def test_47_hard_safety_redline_baseline_and_all_10_forbidden_actions_blocked(self) -> None:
        base = p236.probe_hard_safety_redline()
        self.assertTrue(base.valid)
        self.assertFalse(base.persistent_emmc_writes_authorized)
        self.assertFalse(base.hardware_live_attachment_authorized)
        self.assertFalse(base.overall_ready_for_hardware_attach)

        flags = (
            "persistent_emmc_writes_authorized",
            "hardware_live_attachment_authorized",
            "overall_ready_for_hardware_attach",
            "spi_nor_write_authorized",
            "el3_payload_transmit_authorized",
            "isp_write_authorized",
            "cnflasha_userspace_write_attempt",
            "bypass_silent_mode_5func_or_pwrshutter",
            "bypass_bench_shutdown_auto_pixelmap",
            "force_hdmi_marker_leak_or_reset_split_drift",
        )
        for flag in flags:
            r = p236.probe_hard_safety_redline(**{flag: True})
            self.assertFalse(r.valid, msg=flag)
            self.assertIn(flag, r.blocked_action)
            self.assertFalse(r.persistent_emmc_writes_authorized)
            self.assertFalse(r.hardware_live_attachment_authorized)
            self.assertFalse(r.overall_ready_for_hardware_attach)

    def test_48_pillar_cd_evaluator_all_checks_green(self) -> None:
        pcd = p236.evaluate_pillar_c_d_flexexp_reset_split_and_redlines()
        self.assertTrue(pcd["passed"])
        self.assertEqual(len(pcd["blocked_redline_probes"]), 10)

    def test_49_unified_phase236_runner_deterministic_digest_both_modes(self) -> None:
        r1 = p236.run_phase236_realhw_silent_autopixelmap_marker_flexexp_hil(
            force_clean_room=True
        )
        r2 = p236.run_phase236_realhw_silent_autopixelmap_marker_flexexp_hil(
            force_clean_room=True
        )
        self.assertTrue(r1["all_checks_passed"])
        self.assertEqual(r1["stage_index"], 43)
        self.assertEqual(r1["stage_total"], 43)
        self.assertEqual(r1["milestone"], "43/43")
        self.assertEqual(r1["audit_digest_sha256"], r2["audit_digest_sha256"])

        rep = _get_default_audit()
        self.assertTrue(rep["all_checks_passed"])
        self.assertTrue(rep["pillar_a_silent_mode_autopixelmap_and_no_pwrshutter_hil"]["passed"])
        self.assertTrue(rep["pillar_b_marker_15ratio_persistence_and_hdmi_isolation_hil"]["passed"])
        self.assertTrue(rep["pillar_c_d_flexexp_reset_split_and_redlines"]["passed"])
        self.assertFalse(rep["redlines"]["persistent_emmc_writes_authorized"])
        self.assertFalse(rep["redlines"]["hardware_live_attachment_authorized"])
        self.assertFalse(rep["redlines"]["overall_ready_for_hardware_attach"])
        self.assertFalse(rep["redlines"]["isp_write_authorized"])

    # ------------------------------------------------------------------
    # Group 5: CLI, Suite Stage 43 Wiring (>= 43 Forward-Compat) &
    #          Source Hygiene (8)
    # ------------------------------------------------------------------
    def test_50_standalone_cli_self_test_summary_and_clean_room_json(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        script_path = str(
            FX3_VM_DIR / "realhw_silent_autopixelmap_marker_flexexp_coemulator.py"
        )
        p_sum = subprocess.run(
            ["/usr/bin/python3", "-B", script_path, "--self-test", "--summary"],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(p_sum.returncode, 0, msg=p_sum.stderr)
        self.assertIn("[PASS] Phase 236 Stage 43 (43/43)", p_sum.stdout)

        p_json = subprocess.run(
            ["/usr/bin/python3", "-B", script_path, "--self-test", "--clean-room", "--json"],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(p_json.returncode, 0, msg=p_json.stderr)
        parsed = json.loads(p_json.stdout)
        self.assertTrue(parsed["all_checks_passed"])
        self.assertEqual(parsed["schema"], p236.SCHEMA_ID)
        self.assertEqual(parsed["stage_index"], 43)
        self.assertEqual(parsed["milestone"], "43/43")

    def test_51_inprocess_main_summary_and_json_exit_zero(self) -> None:
        buf_sum = io.StringIO()
        with contextlib.redirect_stdout(buf_sum):
            rc_sum = p236.main(["--self-test", "--clean-room", "--summary"])
        self.assertEqual(rc_sum, 0)
        self.assertIn("[PASS] Phase 236 Stage 43 (43/43)", buf_sum.getvalue())

        buf_json = io.StringIO()
        with contextlib.redirect_stdout(buf_json):
            rc_json = p236.main(["--self-test", "--clean-room", "--json"])
        self.assertEqual(rc_json, 0)
        data = json.loads(buf_json.getvalue())
        self.assertEqual(data["source_mode"], "CLEAN_ROOM_SYNTHETIC")

    def test_52_fx3_vm_coemulation_suite_includes_stage43_and_forward_compat_count(self) -> None:
        rep_on, dt_clean = _get_clean_room_suite()
        self.assertTrue(rep_on["all_checks_passed"])
        self.assertLess(dt_clean, 4.0)
        self.assertIn(
            "stage43_realhw_silent_autopixelmap_marker_flexexp_hil",
            rep_on,
        )
        s43 = rep_on["stage43_realhw_silent_autopixelmap_marker_flexexp_hil"]
        self.assertTrue(s43["all_checks_passed"])
        self.assertEqual(s43["schema"], p236.SCHEMA_ID)
        self.assertEqual(s43["milestone"], "43/43")
        self.assertFalse(s43["persistent_emmc_writes_authorized"])
        self.assertFalse(s43["hardware_live_attachment_authorized"])
        self.assertFalse(s43["overall_ready_for_hardware_attach"])
        self.assertFalse(s43["isp_write_authorized"])
        self.assertFalse(s43["spi_nor_write_authorized"])
        self.assertFalse(s43["el3_payload_transmit_authorized"])
        self.assertEqual(s43["silent_mode_5func_or_pwrshutter_bypass_events"], 0)
        self.assertEqual(s43["bench_shutdown_unsuppressed_auto_pixelmap_events"], 0)
        self.assertEqual(s43["hdmi_marker_leaked_overlay_pixels"], 0)
        self.assertEqual(s43["flexexp_or_marker_reset_split_drift_events"], 0)
        self.assertEqual(s43["raw_firmware_bytes_leaked"], 0)

        stage_keys = [k for k in rep_on if re.match(r"^stage\d+_", k)]
        self.assertGreaterEqual(len(stage_keys), 43)

    def test_53_fx3_vm_coemulation_suite_skip_phase236_option(self) -> None:
        rep_skip = suite.run_fx3_vm_coemulation_suite(
            suite.CoEmulationConfig(
                force_clean_room=True,
                include_phase236_realhw_silent_autopixelmap_marker_flexexp_hil=False,
            )
        )
        self.assertTrue(rep_skip["all_checks_passed"])
        self.assertNotIn(
            "stage43_realhw_silent_autopixelmap_marker_flexexp_hil",
            rep_skip,
        )

    def test_54_fx3_vm_coemulation_suite_default_mode_and_cli_summary_stage43(self) -> None:
        rep_def, dt_def = _get_default_suite()
        self.assertTrue(rep_def["all_checks_passed"])
        self.assertLess(dt_def, 8.0)
        s43 = rep_def["stage43_realhw_silent_autopixelmap_marker_flexexp_hil"]
        self.assertTrue(s43["all_checks_passed"])
        stage_keys = [k for k in rep_def if re.match(r"^stage\d+_", k)]
        self.assertGreaterEqual(len(stage_keys), 43)

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = suite.main(["--clean-room", "--summary"])
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("[PASS] Phase 33 FX3-VM Co-Emulation", out)
        self.assertIn(
            "realhw_silent_autopixelmap_marker_flexexp_hil=CLEAN_ROOM_SYNTHETIC("
            "silent_5f=5,pm_act=0,ratios=15,hdmi_px=0,split=1,emmc_wr=0)",
            out,
        )

    def test_55_fx3_vm_coemulation_suite_cli_skip_phase236_flag(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = suite.main(["--clean-room", "--skip-phase236", "--summary"])
        self.assertEqual(rc, 0)
        self.assertNotIn(
            "realhw_silent_autopixelmap_marker_flexexp_hil=",
            buf.getvalue(),
        )

    def test_56_source_hygiene_no_write_flags_no_port_8768_and_readme_documented(self) -> None:
        src = (
            FX3_VM_DIR / "realhw_silent_autopixelmap_marker_flexexp_coemulator.py"
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
            "realhw_silent_autopixelmap_marker_flexexp_coemulator.py",
            readme,
        )
        self.assertIn("43/43", readme)
        self.assertIn("--skip-phase236", readme)

    def test_57_multi_violation_silent_mode_requests_report_all_blocked_items(self) -> None:
        res = p236.probe_silent_mode_autopixelmap_and_no_pwrshutter_hil(
            silent_mode="On",
            attempt_force_mechanical_shutter_in_silent=True,
            attempt_force_audio_signals_in_silent=True,
            requested_shooting_functions=("Flash", "BULB", "Anti-flicker Shoot."),
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p236.EOPNOTSUPP_ERRNO)
        self.assertEqual(
            res.blocked_function_requests,
            (
                "Shutter Type=Mechanical Shutter",
                "Audio signals=On",
                "Flash",
                "BULB",
                "Anti-flicker Shoot.",
            ),
        )


if __name__ == "__main__":
    unittest.main()
