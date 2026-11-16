"""Phase 230 Dual-Mode Unit Tests (`>=56` tests; 62 tests implemented) for
`fx3_safety.realhw_silent_autopixelmap_marker_flexexp_and_86gate_guard`:

- Gate `G85`: `ILME-FX3` (`Ver. 7.02`) `[Silent Mode Settings]` `[Auto Pixel Mapping]`
  Suppression Target, 5-Function Lockout (`Flash`, `Long Exposure NR`,
  `e-Front Curtain Shut.`, `BULB`, `Anti-flicker Shoot.`) & Hardware
  `[Shutter When Pwr OFF]` Absence Guard (`Ver. 2.00..7.02`).
- Gate `G86`: `ILME-FX3` (`Ver. 7.02`) `[Marker Display]` 15-Ratio Non-Resettable
  Persistence, Local-LCD-Only HDMI Isolation (`0` external HDMI marker output even
  when `[HDMI Info. Display] = [On]`) & `[Flexible Exp. Mode]` `Av`/`Tv`/`ISO` +
  `[Auto Slow Shutter]` Reset Split Guard.
- Unified 86-Gate Master Safety Preflight (`evaluate_86gate_preflight` /
  `verify-86-gates`): `83/86` offline awaiting physical Tier-0 receipt and
  `86/86` in `--simulate-bench-dry-run` with all hardware write/live-attach
  redlines hard-locked `False`.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import fx3_safety
from fx3_safety.__main__ import main as cli_main
from fx3_safety.realhw_silent_autopixelmap_marker_flexexp_and_86gate_guard import (
    ALLOWED_APERTURE_DRIVE_TARGET_SETTINGS,
    ALLOWED_ASPECT_MARKER_SETTINGS,
    ALLOWED_AUDIO_SIGNALS_MODES,
    ALLOWED_AUTO_PIXEL_MAPPING_TARGET_SETTINGS,
    ALLOWED_AUTO_SLOW_SHUTTER_MODES,
    ALLOWED_EXPOSURE_CTRL_TYPES,
    ALLOWED_FLEX_EXP_SW_MODES,
    ALLOWED_GUIDEFRAME_SETTINGS,
    ALLOWED_MARKER_ON_OFF_MODES,
    ALLOWED_NORMAL_APERTURE_DRIVE_MODES,
    ALLOWED_NORMAL_AUTO_PIXEL_MAPPING_MODES,
    ALLOWED_PASM_SUBMODES,
    ALLOWED_RESET_ACTIONS_G86,
    ALLOWED_SAFETY_ZONE_SETTINGS,
    ALLOWED_SHUTTER_TYPES,
    ALLOWED_SILENT_MODES,
    APERTURE_DRIVE_FOCUS_PRIORITY,
    APERTURE_DRIVE_SILENT_PRIORITY,
    APERTURE_DRIVE_STANDARD,
    AUDIO_SIGNALS_OFF,
    AUDIO_SIGNALS_ON_ALL,
    AUDIO_SIGNALS_ON_SHUTTER_ONLY,
    AUTO_PIXEL_MAPPING_OFF,
    AUTO_PIXEL_MAPPING_ON,
    AUTO_SLOW_SHUTTER_FACTORY_DEFAULT,
    AUTO_SLOW_SHUTTER_OFF,
    AUTO_SLOW_SHUTTER_ON,
    DONOR_CHECK_MAX_SECONDS,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    EXPOSURE_CTRL_FLEXIBLE_EXP_MODE,
    EXPOSURE_CTRL_PASM_MODE,
    FABRICATED_SHUTTER_WHEN_PWR_OFF_ITEM,
    FLEX_EXP_AUTO,
    FLEX_EXP_FACTORY_DEFAULT_AV,
    FLEX_EXP_FACTORY_DEFAULT_ISO,
    FLEX_EXP_FACTORY_DEFAULT_TV,
    FLEX_EXP_MANUAL,
    FX3_ASPECT_MARKER_15_RATIOS,
    FX3_ASPECT_MARKER_16_9_MIN_FW_TUPLE,
    FX3_DEFAULT_FW_VERSION_PHASE230,
    FX3_EXPOSED_SENSOR_SETUP_ITEMS,
    FX3_MIN_SUPPORTED_FW_TUPLE_G85,
    FX3_MODEL_ID,
    FX3_MODEL_NAME,
    G85,
    G85_GATE_CODE,
    G85_GATE_ID,
    G86,
    G86_GATE_CODE,
    G86_GATE_ID,
    GATE_G85_SILENT_MODE_AUTOPIXELMAP_TARGET_5LOCK_AND_NO_SHUTTER_WHEN_PWR_OFF_GUARD,
    GATE_G86_MARKER_15RATIO_NONRESET_HDMI_ISOLATION_AND_FLEXIBLE_EXP_RESET_SPLIT_GUARD,
    GUIDEFRAME_OFF,
    GUIDEFRAME_ON,
    HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    HUMAN_HARDWARE_ATTACH_TOKEN,
    MARKER_FACTORY_DEFAULT_ASPECT,
    MARKER_FACTORY_DEFAULT_CENTER,
    MARKER_FACTORY_DEFAULT_DISPLAY,
    MARKER_FACTORY_DEFAULT_GUIDEFRAME,
    MARKER_FACTORY_DEFAULT_SAFETY_ZONE,
    MARKER_OFF,
    MARKER_ON,
    PASM_APERTURE_PRIORITY,
    PASM_MANUAL_EXPOSURE,
    PASM_PROGRAM_AUTO,
    PASM_SHUTTER_PRIORITY,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED,
    PINNED_PHASE230_DONOR_SPECS,
    RAW_FIRMWARE_BYTES_LEAKED,
    REALHW_SILENT_AUTOPIXELMAP_MARKER_FLEXEXP_86GATE_SCHEMA,
    RESET_ACTION_CAMERA_SETTINGS_RESET,
    RESET_ACTION_INITIALIZE,
    RESET_ACTION_NONE,
    SAFETY_ZONE_80_PCT,
    SAFETY_ZONE_90_PCT,
    SAFETY_ZONE_OFF,
    SHUTTER_TYPE_AUTO,
    SHUTTER_TYPE_ELECTRONIC,
    SHUTTER_TYPE_MECHANICAL,
    SILENT_MODE_5_DISABLED_FUNCTIONS,
    SILENT_MODE_DISABLED_FUNC_ANTI_FLICKER,
    SILENT_MODE_DISABLED_FUNC_BULB,
    SILENT_MODE_DISABLED_FUNC_E_FRONT_CURTAIN,
    SILENT_MODE_DISABLED_FUNC_FLASH,
    SILENT_MODE_DISABLED_FUNC_LONG_EXP_NR,
    SILENT_MODE_FACTORY_DEFAULT,
    SILENT_MODE_OFF,
    SILENT_MODE_ON,
    SPI_NOR_WRITE_AUTHORIZED,
    STATUS_BLOCKED_G85_FABRICATED_SHUTTER_WHEN_PWR_OFF_MENU_CLAIM,
    STATUS_BLOCKED_G85_SILENT_MODE_SHUTTER_AUDIO_OR_5FUNC_LOCK_VIOLATION,
    STATUS_BLOCKED_G85_TARGET_FUNCTION_AUTOPIXELMAP_OR_APERTURE_VIOLATION,
    STATUS_BLOCKED_G85_TELEMETRY_INVALID,
    STATUS_BLOCKED_G86_FLEXIBLE_EXP_AV_TV_ISO_OR_AUTOSLOW_RESET_SPLIT_VIOLATION,
    STATUS_BLOCKED_G86_HDMI_MARKER_OVERLAY_LEAK,
    STATUS_BLOCKED_G86_MARKER_CAMERA_SETTINGS_RESET_PERSISTENCE_VIOLATION,
    STATUS_BLOCKED_G86_MARKER_DISPLAY_OR_15RATIO_INVALID,
    STATUS_BLOCKED_G86_TELEMETRY_INVALID,
    STATUS_BLOCKED_PERSISTENT_EMMC_WRITE,
    STATUS_BLOCKED_PHASE230_DONOR_INTEGRITY,
    STATUS_VERIFIED_G85,
    STATUS_VERIFIED_G86,
    TARGET_NOT_TARGET,
    USB_PACKETS_TRANSMITTED,
    audit_phase230_donor_contracts,
    evaluate_86_master_safety_gates,
    evaluate_86gate_preflight,
    evaluate_g85_silent_autopixelmap_no_pwrshutter_guard,
    evaluate_g86_marker_hdmi_and_flexexp_reset_split_guard,
    main as module_main,
    resolve_fx3_flexible_exp_reset_split,
    resolve_fx3_marker_display_hdmi_and_reset,
    resolve_fx3_silent_mode_and_target_functions,
    run_86_gate_preflight,
    verify_marker_15ratio_hdmi_and_flexexp_reset_split_guard,
    verify_silent_mode_autopixelmap_and_no_pwrshutter_guard,
)


class TestPhase230SilentAutoPixelMapMarkerFlexExp86GateGuard(unittest.TestCase):
    """Comprehensive dual-mode tests for Phase 230 Gates G85, G86 & 86-Gate Preflight."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.offline_84 = fx3_safety.evaluate_84gate_preflight()
        cls.dryrun_84 = fx3_safety.evaluate_84gate_preflight(dry_run_simulated=True)
        cls.offline_86 = evaluate_86gate_preflight(master_84_override=cls.offline_84)
        cls.dryrun_86 = evaluate_86gate_preflight(
            simulate_bench_dry_run=True, master_84_override=cls.dryrun_84
        )
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            cls.clean_offline_84 = fx3_safety.evaluate_84gate_preflight(
                force_clean_room=True
            )
            cls.clean_dryrun_84 = fx3_safety.evaluate_84gate_preflight(
                force_clean_room=True, dry_run_simulated=True
            )
            cls.clean_offline_86 = evaluate_86gate_preflight(
                force_clean_room=True, master_84_override=cls.clean_offline_84
            )
            cls.clean_dryrun_86 = evaluate_86gate_preflight(
                force_clean_room=True,
                simulate_bench_dry_run=True,
                master_84_override=cls.clean_dryrun_84,
            )

    # ------------------------------------------------------------------
    # Section A: Package Exports & Bounded Donor Contract Audit (8 tests)
    # ------------------------------------------------------------------

    def test_01_public_package_exports_and_hard_redline_constants(self) -> None:
        self.assertEqual(G85, G85_GATE_ID)
        self.assertEqual(G86, G86_GATE_ID)
        self.assertEqual(
            GATE_G85_SILENT_MODE_AUTOPIXELMAP_TARGET_5LOCK_AND_NO_SHUTTER_WHEN_PWR_OFF_GUARD,
            G85_GATE_CODE,
        )
        self.assertEqual(
            GATE_G86_MARKER_15RATIO_NONRESET_HDMI_ISOLATION_AND_FLEXIBLE_EXP_RESET_SPLIT_GUARD,
            G86_GATE_CODE,
        )
        self.assertFalse(EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        self.assertFalse(SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(PERSISTENT_WRITE_RELEASE)
        self.assertFalse(HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        self.assertFalse(HUMAN_HARDWARE_ATTACH_TOKEN)
        self.assertFalse(PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED)
        self.assertEqual(USB_PACKETS_TRANSMITTED, 0)
        self.assertEqual(RAW_FIRMWARE_BYTES_LEAKED, 0)
        self.assertIs(fx3_safety.evaluate_86gate_preflight, evaluate_86gate_preflight)
        self.assertIs(fx3_safety.run_86_gate_preflight, run_86_gate_preflight)
        self.assertIs(
            fx3_safety.evaluate_86_master_safety_gates, evaluate_86_master_safety_gates
        )
        self.assertIn("evaluate_86gate_preflight", fx3_safety.__all__)
        self.assertIn(
            "realhw_silent_autopixelmap_marker_flexexp_and_86gate_guard",
            fx3_safety.__all__,
        )
        self.assertIn("G85", fx3_safety.__all__)
        self.assertIn("G86", fx3_safety.__all__)

    def test_02_wave33_spec_constants_and_enums(self) -> None:
        self.assertEqual(FX3_MODEL_NAME, "ILME-FX3")
        self.assertEqual(FX3_MODEL_ID, 0x91030080)
        self.assertEqual(FX3_DEFAULT_FW_VERSION_PHASE230, "7.02")
        self.assertEqual(FX3_MIN_SUPPORTED_FW_TUPLE_G85, (2, 0))
        self.assertEqual(FX3_ASPECT_MARKER_16_9_MIN_FW_TUPLE, (3, 0))
        self.assertEqual(SILENT_MODE_FACTORY_DEFAULT, SILENT_MODE_OFF)
        self.assertEqual(ALLOWED_SILENT_MODES, (SILENT_MODE_OFF, SILENT_MODE_ON))
        self.assertEqual(
            ALLOWED_SHUTTER_TYPES,
            (SHUTTER_TYPE_AUTO, SHUTTER_TYPE_MECHANICAL, SHUTTER_TYPE_ELECTRONIC),
        )
        self.assertEqual(
            ALLOWED_AUDIO_SIGNALS_MODES,
            (AUDIO_SIGNALS_ON_ALL, AUDIO_SIGNALS_ON_SHUTTER_ONLY, AUDIO_SIGNALS_OFF),
        )
        self.assertEqual(len(SILENT_MODE_5_DISABLED_FUNCTIONS), 5)
        self.assertEqual(
            SILENT_MODE_5_DISABLED_FUNCTIONS,
            (
                SILENT_MODE_DISABLED_FUNC_FLASH,
                SILENT_MODE_DISABLED_FUNC_LONG_EXP_NR,
                SILENT_MODE_DISABLED_FUNC_E_FRONT_CURTAIN,
                SILENT_MODE_DISABLED_FUNC_BULB,
                SILENT_MODE_DISABLED_FUNC_ANTI_FLICKER,
            ),
        )
        self.assertEqual(len(ALLOWED_NORMAL_APERTURE_DRIVE_MODES), 3)
        self.assertEqual(len(ALLOWED_APERTURE_DRIVE_TARGET_SETTINGS), 4)
        self.assertEqual(
            ALLOWED_NORMAL_AUTO_PIXEL_MAPPING_MODES,
            (AUTO_PIXEL_MAPPING_ON, AUTO_PIXEL_MAPPING_OFF),
        )
        self.assertEqual(
            ALLOWED_AUTO_PIXEL_MAPPING_TARGET_SETTINGS,
            (AUTO_PIXEL_MAPPING_OFF, TARGET_NOT_TARGET),
        )
        self.assertEqual(
            FX3_EXPOSED_SENSOR_SETUP_ITEMS,
            ("Sensor Cleaning", "Auto Pixel Mapping", "Pixel Mapping"),
        )
        self.assertEqual(len(FX3_ASPECT_MARKER_15_RATIOS), 15)
        self.assertEqual(len(ALLOWED_ASPECT_MARKER_SETTINGS), 16)
        self.assertEqual(ALLOWED_MARKER_ON_OFF_MODES, (MARKER_OFF, MARKER_ON))
        self.assertEqual(
            ALLOWED_SAFETY_ZONE_SETTINGS,
            (SAFETY_ZONE_OFF, SAFETY_ZONE_80_PCT, SAFETY_ZONE_90_PCT),
        )
        self.assertEqual(ALLOWED_GUIDEFRAME_SETTINGS, (GUIDEFRAME_OFF, GUIDEFRAME_ON))
        self.assertEqual(
            ALLOWED_EXPOSURE_CTRL_TYPES,
            (EXPOSURE_CTRL_PASM_MODE, EXPOSURE_CTRL_FLEXIBLE_EXP_MODE),
        )
        self.assertEqual(len(ALLOWED_PASM_SUBMODES), 4)
        self.assertEqual(ALLOWED_FLEX_EXP_SW_MODES, (FLEX_EXP_MANUAL, FLEX_EXP_AUTO))
        self.assertEqual(
            ALLOWED_AUTO_SLOW_SHUTTER_MODES,
            (AUTO_SLOW_SHUTTER_ON, AUTO_SLOW_SHUTTER_OFF),
        )
        self.assertEqual(
            (
                FLEX_EXP_FACTORY_DEFAULT_AV,
                FLEX_EXP_FACTORY_DEFAULT_TV,
                FLEX_EXP_FACTORY_DEFAULT_ISO,
                AUTO_SLOW_SHUTTER_FACTORY_DEFAULT,
            ),
            ("Manual", "Manual", "Manual", "On"),
        )
        self.assertEqual(len(ALLOWED_RESET_ACTIONS_G86), 3)

    def test_03_donor_audit_clean_room_forced_via_flag(self) -> None:
        res = audit_phase230_donor_contracts(force_clean_room=True)
        self.assertTrue(res.valid)
        self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(res.access_mode, "O_RDONLY")
        self.assertEqual(res.files_inspected, 0)
        self.assertTrue(res.within_budget_150ms)
        self.assertLess(res.elapsed_seconds, DONOR_CHECK_MAX_SECONDS)
        self.assertEqual(res.raw_firmware_bytes_leaked, 0)
        self.assertEqual(len(res.checked_markers), len(PINNED_PHASE230_DONOR_SPECS))

    def test_04_donor_audit_clean_room_forced_via_env(self) -> None:
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            res = audit_phase230_donor_contracts()
        self.assertTrue(res.valid)
        self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(res.raw_firmware_bytes_leaked, 0)

    def test_05_donor_audit_default_mode_fast_and_zero_leak(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("FX3_FX6_FORCE_CLEAN_ROOM", None)
            res = audit_phase230_donor_contracts()
        self.assertTrue(res.valid)
        self.assertIn(
            res.verification_mode, ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC")
        )
        self.assertEqual(res.access_mode, "O_RDONLY")
        self.assertTrue(res.within_budget_150ms)
        self.assertEqual(res.raw_firmware_bytes_leaked, 0)
        dumped = json.dumps(res.to_dict())
        self.assertNotIn("\\x7fELF", dumped)

    def test_06_donor_audit_nonexistent_work_root_falls_back_clean_room(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            res = audit_phase230_donor_contracts(
                work_root=Path(tmp) / "missing_donor_tree", force_clean_room=False
            )
        self.assertTrue(res.valid)
        self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(res.files_inspected, 0)

    def test_07_donor_audit_corrupted_donor_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for _key, (_body, rel, *_rest) in PINNED_PHASE230_DONOR_SPECS.items():
                p = root / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(b"CORRUPTED_STUB_DATA")
            res = audit_phase230_donor_contracts(work_root=root, force_clean_room=False)
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_PHASE230_DONOR_INTEGRITY)
        self.assertEqual(res.verification_mode, "LOCAL_DONOR_O_RDONLY")
        self.assertGreaterEqual(len(res.errors), 2)

    def test_08_donor_audit_budget_exceeded_fails_closed(self) -> None:
        res = audit_phase230_donor_contracts(
            force_clean_room=True, max_budget_seconds=-1.0
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_PHASE230_DONOR_INTEGRITY)
        self.assertFalse(res.within_budget_150ms)

    # ------------------------------------------------------------------
    # Section B: Gate G85 — [Silent Mode Settings] [Auto Pixel Mapping]
    #            Target, 5-Function Lockout & Hardware [Shutter When Pwr OFF]
    #            Absence Guard (21 tests)
    # ------------------------------------------------------------------

    def test_09_g85_default_silent_on_autopixelmap_targeted_passes(self) -> None:
        res = verify_silent_mode_autopixelmap_and_no_pwrshutter_guard()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_VERIFIED_G85)
        self.assertEqual(res.silent_mode, SILENT_MODE_ON)
        self.assertEqual(res.effective_shutter_type, SHUTTER_TYPE_ELECTRONIC)
        self.assertEqual(res.effective_shutter_type_in_interval, SHUTTER_TYPE_ELECTRONIC)
        self.assertEqual(res.effective_audio_signals, AUDIO_SIGNALS_OFF)
        self.assertTrue(res.all_5_functions_disabled_in_silent)
        self.assertTrue(res.auto_pixel_mapping_targeted_in_silent)
        self.assertFalse(res.effective_power_off_auto_pixel_mapping_active)
        self.assertFalse(res.power_off_mechanical_shutter_sound_expected)
        self.assertFalse(res.power_off_cnflasha_calibration_touch)
        self.assertTrue(res.bench_shutdown_autopixelmap_suppressed)
        self.assertTrue(res.shutter_when_pwr_off_absent_verified)

    def test_10_g85_silent_mode_locks_shutter_type_to_electronic(self) -> None:
        for bad_shutter in (SHUTTER_TYPE_AUTO, SHUTTER_TYPE_MECHANICAL):
            res = verify_silent_mode_autopixelmap_and_no_pwrshutter_guard(
                silent_mode=SILENT_MODE_ON,
                effective_shutter_type=bad_shutter,
            )
            self.assertFalse(res.valid)
            self.assertEqual(
                res.status,
                STATUS_BLOCKED_G85_SILENT_MODE_SHUTTER_AUDIO_OR_5FUNC_LOCK_VIOLATION,
            )

    def test_11_g85_silent_mode_locks_shutter_type_in_interval_to_electronic(
        self,
    ) -> None:
        res = verify_silent_mode_autopixelmap_and_no_pwrshutter_guard(
            silent_mode=SILENT_MODE_ON,
            effective_shutter_type_in_interval=SHUTTER_TYPE_MECHANICAL,
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            res.status,
            STATUS_BLOCKED_G85_SILENT_MODE_SHUTTER_AUDIO_OR_5FUNC_LOCK_VIOLATION,
        )

    def test_12_g85_silent_mode_locks_audio_signals_to_off(self) -> None:
        for bad_audio in (AUDIO_SIGNALS_ON_ALL, AUDIO_SIGNALS_ON_SHUTTER_ONLY):
            res = verify_silent_mode_autopixelmap_and_no_pwrshutter_guard(
                silent_mode=SILENT_MODE_ON,
                effective_audio_signals=bad_audio,
            )
            self.assertFalse(res.valid)
            self.assertEqual(
                res.status,
                STATUS_BLOCKED_G85_SILENT_MODE_SHUTTER_AUDIO_OR_5FUNC_LOCK_VIOLATION,
            )

    def test_13_g85_each_of_5_disabled_functions_omitted_fails_closed(self) -> None:
        for fn in SILENT_MODE_5_DISABLED_FUNCTIONS:
            subset = [x for x in SILENT_MODE_5_DISABLED_FUNCTIONS if x != fn]
            res = verify_silent_mode_autopixelmap_and_no_pwrshutter_guard(
                silent_mode=SILENT_MODE_ON,
                disabled_functions_in_silent=subset,
            )
            self.assertFalse(res.valid, msg=f"Missing disabled function {fn} did not block")
            self.assertEqual(
                res.status,
                STATUS_BLOCKED_G85_SILENT_MODE_SHUTTER_AUDIO_OR_5FUNC_LOCK_VIOLATION,
            )

    def test_14_g85_each_of_5_disabled_functions_attempted_in_silent_fails_closed(
        self,
    ) -> None:
        for fn in SILENT_MODE_5_DISABLED_FUNCTIONS:
            res = verify_silent_mode_autopixelmap_and_no_pwrshutter_guard(
                silent_mode=SILENT_MODE_ON,
                enabled_function_attempted_in_silent=fn,
            )
            self.assertFalse(res.valid, msg=f"Attempted function {fn} did not block")
            self.assertEqual(
                res.status,
                STATUS_BLOCKED_G85_SILENT_MODE_SHUTTER_AUDIO_OR_5FUNC_LOCK_VIOLATION,
            )

    def test_15_g85_target_aperture_drive_in_af_override_vs_not_target_retention(
        self,
    ) -> None:
        targeted = verify_silent_mode_autopixelmap_and_no_pwrshutter_guard(
            silent_mode=SILENT_MODE_ON,
            normal_aperture_drive_in_af=APERTURE_DRIVE_FOCUS_PRIORITY,
            target_aperture_drive_in_af=APERTURE_DRIVE_SILENT_PRIORITY,
        )
        self.assertTrue(targeted.valid)
        self.assertEqual(
            targeted.effective_aperture_drive_in_af, APERTURE_DRIVE_SILENT_PRIORITY
        )
        self.assertFalse(targeted.aperture_drive_not_target_retains_normal)

        retained = verify_silent_mode_autopixelmap_and_no_pwrshutter_guard(
            silent_mode=SILENT_MODE_ON,
            normal_aperture_drive_in_af=APERTURE_DRIVE_FOCUS_PRIORITY,
            target_aperture_drive_in_af=TARGET_NOT_TARGET,
        )
        self.assertTrue(retained.valid)
        self.assertEqual(
            retained.effective_aperture_drive_in_af, APERTURE_DRIVE_FOCUS_PRIORITY
        )
        self.assertTrue(retained.aperture_drive_not_target_retains_normal)

    def test_16_g85_aperture_drive_effective_mismatch_blocks_fail_closed(self) -> None:
        bad = verify_silent_mode_autopixelmap_and_no_pwrshutter_guard(
            silent_mode=SILENT_MODE_ON,
            normal_aperture_drive_in_af=APERTURE_DRIVE_STANDARD,
            target_aperture_drive_in_af=APERTURE_DRIVE_SILENT_PRIORITY,
            effective_aperture_drive_in_af=APERTURE_DRIVE_STANDARD,
        )
        self.assertFalse(bad.valid)
        self.assertEqual(
            bad.status,
            STATUS_BLOCKED_G85_TARGET_FUNCTION_AUTOPIXELMAP_OR_APERTURE_VIOLATION,
        )

    def test_17_g85_autopixelmap_not_target_retains_power_off_shutter_click_and_blocks_bench_shutdown(
        self,
    ) -> None:
        # On bench shutdown requiring suppression, [Not Target] with Auto Pixel Mapping=On blocks!
        blocked_bench = verify_silent_mode_autopixelmap_and_no_pwrshutter_guard(
            silent_mode=SILENT_MODE_ON,
            normal_auto_pixel_mapping=AUTO_PIXEL_MAPPING_ON,
            target_auto_pixel_mapping=TARGET_NOT_TARGET,
            bench_shutdown_require_autopixelmap_suppression=True,
        )
        self.assertFalse(blocked_bench.valid)
        self.assertEqual(
            blocked_bench.status,
            STATUS_BLOCKED_G85_TARGET_FUNCTION_AUTOPIXELMAP_OR_APERTURE_VIOLATION,
        )
        self.assertTrue(blocked_bench.auto_pixel_mapping_not_target_retains_normal)
        self.assertTrue(blocked_bench.effective_power_off_auto_pixel_mapping_active)
        self.assertTrue(blocked_bench.power_off_mechanical_shutter_sound_expected)

        # In non-bench observation mode (bench_shutdown_require_autopixelmap_suppression=False),
        # [Not Target] retention semantics validate cleanly when shutter sound is expected.
        retained_obs = verify_silent_mode_autopixelmap_and_no_pwrshutter_guard(
            silent_mode=SILENT_MODE_ON,
            normal_auto_pixel_mapping=AUTO_PIXEL_MAPPING_ON,
            target_auto_pixel_mapping=TARGET_NOT_TARGET,
            bench_shutdown_require_autopixelmap_suppression=False,
        )
        self.assertTrue(retained_obs.valid)
        self.assertTrue(retained_obs.effective_power_off_auto_pixel_mapping_active)
        self.assertTrue(retained_obs.power_off_mechanical_shutter_sound_expected)

    def test_18_g85_autopixelmap_off_in_setup_safe_even_when_not_target_or_silent_off(
        self,
    ) -> None:
        safe_off = verify_silent_mode_autopixelmap_and_no_pwrshutter_guard(
            silent_mode=SILENT_MODE_OFF,
            normal_auto_pixel_mapping=AUTO_PIXEL_MAPPING_OFF,
            target_auto_pixel_mapping=TARGET_NOT_TARGET,
            bench_shutdown_require_autopixelmap_suppression=True,
        )
        self.assertTrue(safe_off.valid)
        self.assertFalse(safe_off.effective_power_off_auto_pixel_mapping_active)
        self.assertTrue(safe_off.bench_shutdown_autopixelmap_suppressed)

    def test_19_g85_cnflasha_calibration_touch_at_power_off_always_blocks(self) -> None:
        bad_cnflasha = verify_silent_mode_autopixelmap_and_no_pwrshutter_guard(
            silent_mode=SILENT_MODE_ON,
            target_auto_pixel_mapping=AUTO_PIXEL_MAPPING_OFF,
            power_off_cnflasha_calibration_touch=True,
        )
        self.assertFalse(bad_cnflasha.valid)
        self.assertEqual(
            bad_cnflasha.status,
            STATUS_BLOCKED_G85_TARGET_FUNCTION_AUTOPIXELMAP_OR_APERTURE_VIOLATION,
        )

    def test_20_g85_fabricated_shutter_when_pwr_off_menu_claim_rejected_across_all_versions(
        self,
    ) -> None:
        for fw in ("2.00", "3.00", "4.00", "5.00", "6.00", "7.00", "7.02"):
            res = verify_silent_mode_autopixelmap_and_no_pwrshutter_guard(
                firmware_version=fw,
                shutter_when_pwr_off_menu_claimed=True,
            )
            self.assertFalse(res.valid, msg=f"Ver. {fw} did not reject Shutter When Pwr OFF")
            self.assertEqual(
                res.status,
                STATUS_BLOCKED_G85_FABRICATED_SHUTTER_WHEN_PWR_OFF_MENU_CLAIM,
            )

    def test_21_g85_fabricated_shutter_when_pwr_off_in_target_functions_rejected(
        self,
    ) -> None:
        res = verify_silent_mode_autopixelmap_and_no_pwrshutter_guard(
            shutter_when_pwr_off_in_target_functions=True,
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            res.status,
            STATUS_BLOCKED_G85_FABRICATED_SHUTTER_WHEN_PWR_OFF_MENU_CLAIM,
        )

    def test_22_g85_fabricated_shutter_when_pwr_off_setting_on_or_off_rejected(
        self,
    ) -> None:
        for val in ("On", "Off", "Closed"):
            res = verify_silent_mode_autopixelmap_and_no_pwrshutter_guard(
                shutter_when_pwr_off_setting=val,
            )
            self.assertFalse(res.valid)
            self.assertEqual(
                res.status,
                STATUS_BLOCKED_G85_FABRICATED_SHUTTER_WHEN_PWR_OFF_MENU_CLAIM,
            )

    def test_23_g85_claimed_sensor_setup_items_with_shutter_when_pwr_off_rejected(
        self,
    ) -> None:
        res = verify_silent_mode_autopixelmap_and_no_pwrshutter_guard(
            claimed_sensor_setup_items=(
                "Sensor Cleaning",
                FABRICATED_SHUTTER_WHEN_PWR_OFF_ITEM,
                "Auto Pixel Mapping",
                "Pixel Mapping",
            ),
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            res.status,
            STATUS_BLOCKED_G85_FABRICATED_SHUTTER_WHEN_PWR_OFF_MENU_CLAIM,
        )

    def test_24_g85_shutter_when_pwr_off_explicit_absent_marker_accepted(self) -> None:
        for absent_tok in (None, "ABSENT", "NOT_SUPPORTED_ON_FX3"):
            res = verify_silent_mode_autopixelmap_and_no_pwrshutter_guard(
                shutter_when_pwr_off_setting=absent_tok,
            )
            self.assertTrue(res.valid)
            self.assertTrue(res.shutter_when_pwr_off_absent_verified)

    def test_25_g85_silent_mode_off_state_mismatch_blocks(self) -> None:
        bad_off = verify_silent_mode_autopixelmap_and_no_pwrshutter_guard(
            silent_mode=SILENT_MODE_OFF,
            normal_auto_pixel_mapping=AUTO_PIXEL_MAPPING_OFF,
            disabled_functions_in_silent=(SILENT_MODE_DISABLED_FUNC_FLASH,),
        )
        self.assertFalse(bad_off.valid)
        self.assertEqual(
            bad_off.status,
            STATUS_BLOCKED_G85_SILENT_MODE_SHUTTER_AUDIO_OR_5FUNC_LOCK_VIOLATION,
        )

    def test_26_g85_invalid_telemetry_body_fw_and_enums_fail_closed(self) -> None:
        bad_body = verify_silent_mode_autopixelmap_and_no_pwrshutter_guard(
            body_model_name="ILCE-7SM3"
        )
        self.assertFalse(bad_body.valid)
        self.assertEqual(bad_body.status, STATUS_BLOCKED_G85_TELEMETRY_INVALID)

        bad_fw = verify_silent_mode_autopixelmap_and_no_pwrshutter_guard(
            firmware_version="1.00"
        )
        self.assertFalse(bad_fw.valid)
        self.assertEqual(bad_fw.status, STATUS_BLOCKED_G85_TELEMETRY_INVALID)

        bad_enum = verify_silent_mode_autopixelmap_and_no_pwrshutter_guard(
            silent_mode="Half"
        )
        self.assertFalse(bad_enum.valid)
        self.assertEqual(bad_enum.status, STATUS_BLOCKED_G85_TELEMETRY_INVALID)

    def test_27_g85_unknown_disabled_or_attempted_function_fails_closed(self) -> None:
        bad_fn = verify_silent_mode_autopixelmap_and_no_pwrshutter_guard(
            disabled_functions_in_silent=("Imaginary Function",)
        )
        self.assertFalse(bad_fn.valid)
        self.assertEqual(bad_fn.status, STATUS_BLOCKED_G85_TELEMETRY_INVALID)

        bad_att = verify_silent_mode_autopixelmap_and_no_pwrshutter_guard(
            enabled_function_attempted_in_silent="Nonexistent"
        )
        self.assertFalse(bad_att.valid)
        self.assertEqual(bad_att.status, STATUS_BLOCKED_G85_TELEMETRY_INVALID)

    def test_28_g85_resolve_helper_direct_contracts(self) -> None:
        st = resolve_fx3_silent_mode_and_target_functions(
            silent_mode="on",
            normal_shutter_type="mechanical",
            normal_aperture_drive_in_af="standard",
            target_aperture_drive_in_af="focus_priority",
            normal_auto_pixel_mapping="on",
            target_auto_pixel_mapping="target",
        )
        self.assertEqual(st["expected_shutter_type"], SHUTTER_TYPE_ELECTRONIC)
        self.assertEqual(st["expected_audio_signals"], AUDIO_SIGNALS_OFF)
        self.assertEqual(st["expected_aperture_drive_in_af"], APERTURE_DRIVE_FOCUS_PRIORITY)
        self.assertTrue(st["auto_pixel_mapping_targeted_in_silent"])
        self.assertFalse(st["expected_power_off_auto_pixel_mapping_active"])

    def test_29_g85_evaluate_dual_mode_and_persistent_write_block(self) -> None:
        v_donor, r_donor = evaluate_g85_silent_autopixelmap_no_pwrshutter_guard(
            force_clean_room=False
        )
        self.assertTrue(v_donor.passed)
        self.assertTrue(r_donor.valid)
        self.assertEqual(v_donor.gate_id, G85_GATE_ID)
        self.assertFalse(r_donor.persistent_emmc_writes_authorized)

        v_clean, r_clean = evaluate_g85_silent_autopixelmap_no_pwrshutter_guard(
            force_clean_room=True
        )
        self.assertTrue(v_clean.passed)
        self.assertEqual(r_clean.verification_mode, "CLEAN_ROOM_SYNTHETIC")

        v_wr, r_wr = evaluate_g85_silent_autopixelmap_no_pwrshutter_guard(
            force_clean_room=True, request_persistent_emmc_writes=True
        )
        self.assertFalse(v_wr.passed)
        self.assertEqual(r_wr.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)

    # ------------------------------------------------------------------
    # Section C: Gate G86 — [Marker Display] 15-Ratio Persistence,
    #            Local-LCD-Only HDMI Isolation & [Flexible Exp. Mode]
    #            Av/Tv/ISO + [Auto Slow Shutter] Reset Split (21 tests)
    # ------------------------------------------------------------------

    def test_30_g86_default_marker_survival_hdmi_isolation_and_flexexp_reset_split_pass(
        self,
    ) -> None:
        res = verify_marker_15ratio_hdmi_and_flexexp_reset_split_guard()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_VERIFIED_G86)
        self.assertEqual(res.aspect_marker_15_ratio_count, 15)
        self.assertTrue(res.local_lcd_marker_rendered)
        self.assertFalse(res.hdmi_marker_overlay_rendered)
        self.assertEqual(res.external_hdmi_marker_count, 0)
        self.assertTrue(res.hdmi_marker_isolation_enforced)
        self.assertTrue(res.marker_survived_camera_settings_reset)
        self.assertEqual(res.effective_post_reset_aspect_marker, "2.39:1")
        self.assertEqual(res.effective_post_reset_flex_av_mode, FLEX_EXP_MANUAL)
        self.assertEqual(res.effective_post_reset_flex_tv_mode, FLEX_EXP_MANUAL)
        self.assertEqual(res.effective_post_reset_flex_iso_mode, FLEX_EXP_MANUAL)
        self.assertEqual(res.effective_post_reset_auto_slow_shutter, AUTO_SLOW_SHUTTER_ON)
        self.assertTrue(res.flex_exp_reset_by_camera_settings_reset)
        self.assertTrue(res.marker_vs_flexexp_reset_split_verified)

    def test_31_g86_all_15_aspect_marker_ratios_plus_off_verified_on_v702(self) -> None:
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
        self.assertEqual(FX3_ASPECT_MARKER_15_RATIOS, expected_15)
        for ratio in ALLOWED_ASPECT_MARKER_SETTINGS:
            res = verify_marker_15ratio_hdmi_and_flexexp_reset_split_guard(
                firmware_version="7.02",
                pre_reset_aspect_marker=ratio,
                reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
            )
            self.assertTrue(res.valid, msg=f"Aspect Marker {ratio} failed on Ver. 7.02")
            self.assertEqual(res.effective_post_reset_aspect_marker, ratio)
            self.assertTrue(res.marker_survived_camera_settings_reset)

    def test_32_g86_aspect_marker_16_9_requires_ver_300_floor(self) -> None:
        blocked_v200 = verify_marker_15ratio_hdmi_and_flexexp_reset_split_guard(
            firmware_version="2.00",
            pre_reset_aspect_marker="16:9",
        )
        self.assertFalse(blocked_v200.valid)
        self.assertEqual(
            blocked_v200.status, STATUS_BLOCKED_G86_MARKER_DISPLAY_OR_15RATIO_INVALID
        )

        ok_v300 = verify_marker_15ratio_hdmi_and_flexexp_reset_split_guard(
            firmware_version="3.00",
            pre_reset_aspect_marker="16:9",
        )
        self.assertTrue(ok_v300.valid)

    def test_33_g86_incomplete_or_fabricated_aspect_marker_catalog_rejected(self) -> None:
        missing_16_9 = [r for r in FX3_ASPECT_MARKER_15_RATIOS if r != "16:9"]
        res = verify_marker_15ratio_hdmi_and_flexexp_reset_split_guard(
            claimed_aspect_marker_ratios=missing_16_9
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_G86_MARKER_DISPLAY_OR_15RATIO_INVALID)

        bad_ratio = verify_marker_15ratio_hdmi_and_flexexp_reset_split_guard(
            pre_reset_aspect_marker="3.50:1"
        )
        self.assertFalse(bad_ratio.valid)
        self.assertEqual(
            bad_ratio.status, STATUS_BLOCKED_G86_MARKER_DISPLAY_OR_15RATIO_INVALID
        )

    def test_34_g86_safety_zone_80_90_off_and_guideframe_options(self) -> None:
        for sz in ALLOWED_SAFETY_ZONE_SETTINGS:
            for gf in ALLOWED_GUIDEFRAME_SETTINGS:
                res = verify_marker_15ratio_hdmi_and_flexexp_reset_split_guard(
                    pre_reset_safety_zone=sz,
                    pre_reset_guideframe=gf,
                )
                self.assertTrue(res.valid)
                self.assertEqual(res.effective_post_reset_safety_zone, sz)
                self.assertEqual(res.effective_post_reset_guideframe, gf)

        bad_sz = verify_marker_15ratio_hdmi_and_flexexp_reset_split_guard(
            pre_reset_safety_zone="95%"
        )
        self.assertFalse(bad_sz.valid)
        self.assertEqual(
            bad_sz.status, STATUS_BLOCKED_G86_MARKER_DISPLAY_OR_15RATIO_INVALID
        )

    def test_35_g86_hdmi_info_display_on_blanks_local_lcd_and_still_emits_zero_hdmi_markers(
        self,
    ) -> None:
        res = verify_marker_15ratio_hdmi_and_flexexp_reset_split_guard(
            pre_reset_marker_display=MARKER_ON,
            pre_reset_aspect_marker="2.39:1",
            hdmi_info_display_on=True,
        )
        self.assertTrue(res.valid)
        self.assertTrue(res.camera_lcd_blanked_by_hdmi_info)
        self.assertFalse(res.local_lcd_marker_rendered)
        self.assertFalse(res.hdmi_marker_overlay_rendered)
        self.assertEqual(res.external_hdmi_marker_count, 0)

    def test_36_g86_hdmi_marker_overlay_leak_blocks_fail_closed(self) -> None:
        for hdmi_info in (False, True):
            leak_bool = verify_marker_15ratio_hdmi_and_flexexp_reset_split_guard(
                hdmi_info_display_on=hdmi_info,
                hdmi_marker_overlay_rendered=True,
            )
            self.assertFalse(leak_bool.valid)
            self.assertEqual(leak_bool.status, STATUS_BLOCKED_G86_HDMI_MARKER_OVERLAY_LEAK)

            leak_cnt = verify_marker_15ratio_hdmi_and_flexexp_reset_split_guard(
                hdmi_info_display_on=hdmi_info,
                external_hdmi_marker_count=1,
            )
            self.assertFalse(leak_cnt.valid)
            self.assertEqual(leak_cnt.status, STATUS_BLOCKED_G86_HDMI_MARKER_OVERLAY_LEAK)

    def test_37_g86_local_lcd_marker_rendered_when_all_subitems_off_or_lcd_blanked_blocks(
        self,
    ) -> None:
        # All 4 subitems Off -> no marker rendered even if [Marker Display]=On
        no_sub = verify_marker_15ratio_hdmi_and_flexexp_reset_split_guard(
            pre_reset_marker_display=MARKER_ON,
            pre_reset_center_marker=MARKER_OFF,
            pre_reset_aspect_marker=MARKER_OFF,
            pre_reset_safety_zone=SAFETY_ZONE_OFF,
            pre_reset_guideframe=GUIDEFRAME_OFF,
        )
        self.assertTrue(no_sub.valid)
        self.assertFalse(no_sub.any_marker_subitem_enabled)
        self.assertFalse(no_sub.local_lcd_marker_rendered)

        bad_lcd = verify_marker_15ratio_hdmi_and_flexexp_reset_split_guard(
            pre_reset_marker_display=MARKER_ON,
            hdmi_info_display_on=True,
            local_lcd_marker_rendered=True,
        )
        self.assertFalse(bad_lcd.valid)
        self.assertEqual(bad_lcd.status, STATUS_BLOCKED_G86_HDMI_MARKER_OVERLAY_LEAK)

    def test_38_g86_camera_settings_reset_wiping_marker_display_or_aspect_marker_blocks(
        self,
    ) -> None:
        bad_disp = verify_marker_15ratio_hdmi_and_flexexp_reset_split_guard(
            pre_reset_marker_display=MARKER_ON,
            pre_reset_aspect_marker="1.85:1",
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
            post_reset_marker_display=MARKER_OFF,
        )
        self.assertFalse(bad_disp.valid)
        self.assertEqual(
            bad_disp.status,
            STATUS_BLOCKED_G86_MARKER_CAMERA_SETTINGS_RESET_PERSISTENCE_VIOLATION,
        )

        bad_aspect = verify_marker_15ratio_hdmi_and_flexexp_reset_split_guard(
            pre_reset_marker_display=MARKER_ON,
            pre_reset_aspect_marker="1.85:1",
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
            post_reset_aspect_marker=MARKER_OFF,
        )
        self.assertFalse(bad_aspect.valid)
        self.assertEqual(
            bad_aspect.status,
            STATUS_BLOCKED_G86_MARKER_CAMERA_SETTINGS_RESET_PERSISTENCE_VIOLATION,
        )

    def test_39_g86_initialize_wipes_all_marker_settings_and_resets_flexexp(self) -> None:
        init_ok = verify_marker_15ratio_hdmi_and_flexexp_reset_split_guard(
            pre_reset_marker_display=MARKER_ON,
            pre_reset_center_marker=MARKER_ON,
            pre_reset_aspect_marker="2.39:1",
            pre_reset_safety_zone=SAFETY_ZONE_80_PCT,
            pre_reset_guideframe=GUIDEFRAME_ON,
            pre_reset_flex_av_mode=FLEX_EXP_AUTO,
            pre_reset_flex_tv_mode=FLEX_EXP_AUTO,
            pre_reset_flex_iso_mode=FLEX_EXP_AUTO,
            pre_reset_auto_slow_shutter=AUTO_SLOW_SHUTTER_OFF,
            reset_action=RESET_ACTION_INITIALIZE,
        )
        self.assertTrue(init_ok.valid)
        self.assertEqual(
            (
                init_ok.effective_post_reset_marker_display,
                init_ok.effective_post_reset_center_marker,
                init_ok.effective_post_reset_aspect_marker,
                init_ok.effective_post_reset_safety_zone,
                init_ok.effective_post_reset_guideframe,
            ),
            (
                MARKER_FACTORY_DEFAULT_DISPLAY,
                MARKER_FACTORY_DEFAULT_CENTER,
                MARKER_FACTORY_DEFAULT_ASPECT,
                MARKER_FACTORY_DEFAULT_SAFETY_ZONE,
                MARKER_FACTORY_DEFAULT_GUIDEFRAME,
            ),
        )
        self.assertFalse(init_ok.marker_survived_camera_settings_reset)
        self.assertFalse(init_ok.local_lcd_marker_rendered)
        self.assertEqual(init_ok.effective_post_reset_flex_av_mode, FLEX_EXP_MANUAL)
        self.assertEqual(init_ok.effective_post_reset_auto_slow_shutter, AUTO_SLOW_SHUTTER_ON)

    def test_40_g86_initialize_retaining_marker_blocks_fail_closed(self) -> None:
        bad_init = verify_marker_15ratio_hdmi_and_flexexp_reset_split_guard(
            pre_reset_marker_display=MARKER_ON,
            reset_action=RESET_ACTION_INITIALIZE,
            post_reset_marker_display=MARKER_ON,
        )
        self.assertFalse(bad_init.valid)
        self.assertEqual(
            bad_init.status,
            STATUS_BLOCKED_G86_MARKER_CAMERA_SETTINGS_RESET_PERSISTENCE_VIOLATION,
        )

    def test_41_g86_flex_exp_av_tv_iso_retaining_auto_after_camera_settings_reset_blocks(
        self,
    ) -> None:
        for kw in (
            {"post_reset_flex_av_mode": FLEX_EXP_AUTO},
            {"post_reset_flex_tv_mode": FLEX_EXP_AUTO},
            {"post_reset_flex_iso_mode": FLEX_EXP_AUTO},
        ):
            res = verify_marker_15ratio_hdmi_and_flexexp_reset_split_guard(
                reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
                **kw,
            )
            self.assertFalse(res.valid, msg=f"Retained Auto {kw} did not block")
            self.assertEqual(
                res.status,
                STATUS_BLOCKED_G86_FLEXIBLE_EXP_AV_TV_ISO_OR_AUTOSLOW_RESET_SPLIT_VIOLATION,
            )

    def test_42_g86_auto_slow_shutter_retaining_off_after_camera_settings_reset_blocks(
        self,
    ) -> None:
        res = verify_marker_15ratio_hdmi_and_flexexp_reset_split_guard(
            pre_reset_auto_slow_shutter=AUTO_SLOW_SHUTTER_OFF,
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
            post_reset_auto_slow_shutter=AUTO_SLOW_SHUTTER_OFF,
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            res.status,
            STATUS_BLOCKED_G86_FLEXIBLE_EXP_AV_TV_ISO_OR_AUTOSLOW_RESET_SPLIT_VIOLATION,
        )

    def test_43_g86_reset_action_none_preserves_flex_exp_auto_and_auto_slow_off(
        self,
    ) -> None:
        res = verify_marker_15ratio_hdmi_and_flexexp_reset_split_guard(
            pre_reset_flex_av_mode=FLEX_EXP_AUTO,
            pre_reset_flex_tv_mode=FLEX_EXP_MANUAL,
            pre_reset_flex_iso_mode=FLEX_EXP_AUTO,
            pre_reset_auto_slow_shutter=AUTO_SLOW_SHUTTER_OFF,
            reset_action=RESET_ACTION_NONE,
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.effective_post_reset_flex_av_mode, FLEX_EXP_AUTO)
        self.assertEqual(res.effective_post_reset_flex_tv_mode, FLEX_EXP_MANUAL)
        self.assertEqual(res.effective_post_reset_flex_iso_mode, FLEX_EXP_AUTO)
        self.assertEqual(res.effective_post_reset_auto_slow_shutter, AUTO_SLOW_SHUTTER_OFF)
        self.assertFalse(res.flex_exp_reset_by_camera_settings_reset)

    def test_44_g86_pasm_exposure_ctrl_type_and_all_4_submodes_supported(self) -> None:
        for sub in (
            PASM_PROGRAM_AUTO,
            PASM_APERTURE_PRIORITY,
            PASM_SHUTTER_PRIORITY,
            PASM_MANUAL_EXPOSURE,
        ):
            res = verify_marker_15ratio_hdmi_and_flexexp_reset_split_guard(
                exposure_ctrl_type=EXPOSURE_CTRL_PASM_MODE,
                pasm_submode=sub,
            )
            self.assertTrue(res.valid)
            self.assertEqual(res.exposure_ctrl_type, EXPOSURE_CTRL_PASM_MODE)
            self.assertEqual(res.pasm_submode, sub)

    def test_45_g86_invalid_exposure_ctrl_type_or_flex_enum_fails_closed(self) -> None:
        bad_ctrl = verify_marker_15ratio_hdmi_and_flexexp_reset_split_guard(
            exposure_ctrl_type="Shutter Angle Only"
        )
        self.assertFalse(bad_ctrl.valid)
        self.assertEqual(bad_ctrl.status, STATUS_BLOCKED_G86_TELEMETRY_INVALID)

        bad_av = verify_marker_15ratio_hdmi_and_flexexp_reset_split_guard(
            pre_reset_flex_av_mode="SemiAuto"
        )
        self.assertFalse(bad_av.valid)
        self.assertEqual(bad_av.status, STATUS_BLOCKED_G86_TELEMETRY_INVALID)

    def test_46_g86_invalid_body_fw_reset_action_and_hdmi_count_fail_closed(
        self,
    ) -> None:
        bad_body = verify_marker_15ratio_hdmi_and_flexexp_reset_split_guard(
            body_model_id=0x12345678
        )
        self.assertFalse(bad_body.valid)
        self.assertEqual(bad_body.status, STATUS_BLOCKED_G86_TELEMETRY_INVALID)

        bad_fw = verify_marker_15ratio_hdmi_and_flexexp_reset_split_guard(
            firmware_version="not-a-version"
        )
        self.assertFalse(bad_fw.valid)
        self.assertEqual(bad_fw.status, STATUS_BLOCKED_G86_TELEMETRY_INVALID)

        bad_rst = verify_marker_15ratio_hdmi_and_flexexp_reset_split_guard(
            reset_action="FORMAT_EMMC"
        )
        self.assertFalse(bad_rst.valid)
        self.assertEqual(bad_rst.status, STATUS_BLOCKED_G86_TELEMETRY_INVALID)

        bad_cnt = verify_marker_15ratio_hdmi_and_flexexp_reset_split_guard(
            external_hdmi_marker_count=-1
        )
        self.assertFalse(bad_cnt.valid)
        self.assertEqual(bad_cnt.status, STATUS_BLOCKED_G86_TELEMETRY_INVALID)

    def test_47_g86_marker_display_off_suppresses_local_lcd_even_with_subitems_on(
        self,
    ) -> None:
        res = verify_marker_15ratio_hdmi_and_flexexp_reset_split_guard(
            pre_reset_marker_display=MARKER_OFF,
            pre_reset_center_marker=MARKER_ON,
            pre_reset_aspect_marker="9:16",
        )
        self.assertTrue(res.valid)
        self.assertTrue(res.any_marker_subitem_enabled)
        self.assertFalse(res.local_lcd_marker_rendered)
        self.assertFalse(res.hdmi_marker_overlay_rendered)

    def test_48_g86_vertical_and_cinema_aspect_ratios_9_16_4_5_1_1_17_9_2_35_2_39(
        self,
    ) -> None:
        for r in ("9:16", "4:5", "1:1", "17:9", "2.35:1", "2.39:1"):
            res = verify_marker_15ratio_hdmi_and_flexexp_reset_split_guard(
                pre_reset_aspect_marker=r
            )
            self.assertTrue(res.valid)
            self.assertEqual(res.effective_post_reset_aspect_marker, r)

    def test_49_g86_resolve_helpers_direct_contracts(self) -> None:
        m = resolve_fx3_marker_display_hdmi_and_reset(
            pre_reset_marker_display="on",
            pre_reset_aspect_marker="16:9",
            hdmi_info_display_on=False,
            reset_action="camera_settings_reset",
        )
        self.assertTrue(m["expected_local_lcd_marker_rendered"])
        self.assertFalse(m["expected_hdmi_marker_overlay_rendered"])
        self.assertEqual(m["expected_post_reset_aspect_marker"], "16:9")

        f = resolve_fx3_flexible_exp_reset_split(
            exposure_ctrl_type="flexible_exp_mode",
            pre_reset_flex_av_mode="auto",
            pre_reset_flex_tv_mode="auto",
            pre_reset_flex_iso_mode="auto",
            pre_reset_auto_slow_shutter="off",
            reset_action="camera_settings_reset",
        )
        self.assertEqual(f["expected_post_reset_flex_av_mode"], "Manual")
        self.assertEqual(f["expected_post_reset_flex_tv_mode"], "Manual")
        self.assertEqual(f["expected_post_reset_flex_iso_mode"], "Manual")
        self.assertEqual(f["expected_post_reset_auto_slow_shutter"], "On")

    def test_50_g86_evaluate_dual_mode_and_persistent_write_block(self) -> None:
        v_donor, r_donor = evaluate_g86_marker_hdmi_and_flexexp_reset_split_guard(
            force_clean_room=False
        )
        self.assertTrue(v_donor.passed)
        self.assertTrue(r_donor.valid)
        self.assertEqual(v_donor.gate_id, G86_GATE_ID)
        self.assertFalse(r_donor.persistent_emmc_writes_authorized)

        v_clean, r_clean = evaluate_g86_marker_hdmi_and_flexexp_reset_split_guard(
            force_clean_room=True
        )
        self.assertTrue(v_clean.passed)
        self.assertEqual(r_clean.verification_mode, "CLEAN_ROOM_SYNTHETIC")

        v_wr, r_wr = evaluate_g86_marker_hdmi_and_flexexp_reset_split_guard(
            force_clean_room=True, request_persistent_emmc_writes=True
        )
        self.assertFalse(v_wr.passed)
        self.assertEqual(r_wr.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)

    # ------------------------------------------------------------------
    # Section D: Unified 86-Gate Master Preflight (`verify-86-gates`)
    #            Dual-Mode, Fault Propagation & CLI Tests (12 tests)
    # ------------------------------------------------------------------

    def test_51_preflight_86_offline_mode_83_of_86_verified(self) -> None:
        r = self.offline_86
        self.assertEqual(
            r.schema, REALHW_SILENT_AUTOPIXELMAP_MARKER_FLEXEXP_86GATE_SCHEMA
        )
        self.assertEqual(r.summary["total_gates"], 86)
        self.assertEqual(r.summary["verified_gates"], 83)
        self.assertEqual(r.summary["blocked_or_pending_gates"], 3)
        self.assertEqual(r.summary["g01_to_g12_verified"], 9)
        self.assertEqual(r.summary["g13_to_g84_verified"], 72)
        self.assertEqual(r.summary["g85_to_g86_verified"], 2)
        self.assertTrue(r.offline_83_gates_verified)
        self.assertFalse(r.all_86_gates_verified)
        self.assertTrue(r.g13_to_g86_all_passed)
        self.assertTrue(r.g85_to_g86_all_passed)
        self.assertEqual(r.status, "VERIFIED_83_OF_86_AWAITING_PHYSICAL_TIER0")
        self.assertEqual(len(r.gates), 86)
        self.assertEqual(r.gates[-2]["gate_code"], G85_GATE_CODE)
        self.assertEqual(r.gates[-1]["gate_code"], G86_GATE_CODE)

    def test_52_preflight_86_dry_run_mode_86_of_86_verified_redlines_locked(
        self,
    ) -> None:
        r = self.dryrun_86
        self.assertEqual(r.summary["verified_gates"], 86)
        self.assertTrue(r.all_86_gates_verified)
        self.assertTrue(r.offline_83_gates_verified)
        self.assertTrue(r.dry_run_rehearsal_only)
        self.assertEqual(r.status, "VERIFIED_ALL_86_GATES_DRY_RUN_SIMULATED_BACKUP")
        self.assertFalse(r.overall_ready_for_hardware_attach)
        self.assertFalse(r.hardware_live_attachment_authorized)
        self.assertFalse(r.el3_payload_transmit_authorized)
        self.assertFalse(r.spi_nor_write_authorized)
        self.assertFalse(r.persistent_emmc_writes_authorized)
        self.assertFalse(r.persistent_write_release)
        self.assertFalse(r.physical_flash_auto_exec_authorized)
        self.assertTrue(r.agent_auto_flash_blocked)
        self.assertEqual(r.usb_packets_transmitted, 0)
        self.assertEqual(r.raw_firmware_bytes_leaked, 0)

    def test_53_preflight_86_clean_room_offline_and_dry_run_parity(self) -> None:
        self.assertEqual(
            self.clean_offline_86.verification_mode, "CLEAN_ROOM_SYNTHETIC"
        )
        self.assertTrue(self.clean_offline_86.clean_room_forced)
        self.assertEqual(self.clean_offline_86.summary["verified_gates"], 83)
        self.assertTrue(self.clean_offline_86.offline_83_gates_verified)

        self.assertEqual(
            self.clean_dryrun_86.verification_mode, "CLEAN_ROOM_SYNTHETIC"
        )
        self.assertEqual(self.clean_dryrun_86.summary["verified_gates"], 86)
        self.assertTrue(self.clean_dryrun_86.all_86_gates_verified)
        self.assertFalse(self.clean_dryrun_86.overall_ready_for_hardware_attach)

    def test_54_preflight_86_propagates_g85_fabricated_pwr_shutter_violation(
        self,
    ) -> None:
        r = evaluate_86gate_preflight(
            force_clean_room=True,
            master_84_override=self.clean_offline_84,
            silent_autopixelmap_kwargs={"shutter_when_pwr_off_menu_claimed": True},
        )
        self.assertFalse(r.g85_to_g86_all_passed)
        self.assertFalse(r.offline_83_gates_verified)
        self.assertEqual(
            r.status, STATUS_BLOCKED_G85_FABRICATED_SHUTTER_WHEN_PWR_OFF_MENU_CLAIM
        )
        self.assertEqual(r.summary["verified_gates"], 82)

    def test_55_preflight_86_propagates_g86_hdmi_marker_leak_or_flexexp_violation(
        self,
    ) -> None:
        r = evaluate_86gate_preflight(
            force_clean_room=True,
            master_84_override=self.clean_offline_84,
            marker_flexexp_kwargs={"hdmi_marker_overlay_rendered": True},
        )
        self.assertFalse(r.g85_to_g86_all_passed)
        self.assertFalse(r.offline_83_gates_verified)
        self.assertEqual(r.status, STATUS_BLOCKED_G86_HDMI_MARKER_OVERLAY_LEAK)
        self.assertEqual(r.summary["verified_gates"], 82)

    def test_56_preflight_86_persistent_emmc_write_request_blocks_all(self) -> None:
        r = evaluate_86gate_preflight(
            force_clean_room=True,
            master_84_override=self.clean_dryrun_84,
            simulate_bench_dry_run=True,
            request_persistent_emmc_writes=True,
        )
        self.assertEqual(r.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        self.assertFalse(r.offline_83_gates_verified)
        self.assertFalse(r.all_86_gates_verified)
        self.assertFalse(r.h0_h1_trial_entry_allowed)
        self.assertFalse(r.persistent_emmc_writes_authorized)

    def test_57_cli_verify_g85_text_and_json_modes(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cli_main(
                ["verify-g85-silent-autopixelmap-no-pwrshutter", "--force-clean-room"]
            )
        self.assertEqual(rc, 0)
        self.assertIn(f"status={STATUS_VERIFIED_G85}", buf.getvalue())

        buf_json = io.StringIO()
        with contextlib.redirect_stdout(buf_json):
            rc_j = cli_main(
                [
                    "verify-g85-silent-autopixelmap-no-pwrshutter",
                    "--force-clean-room",
                    "--json",
                ]
            )
        self.assertEqual(rc_j, 0)
        payload = json.loads(buf_json.getvalue())
        self.assertTrue(payload["valid"])
        self.assertEqual(payload["verification_mode"], "CLEAN_ROOM_SYNTHETIC")

    def test_58_cli_verify_g86_text_and_json_modes(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cli_main(
                ["verify-g86-marker-hdmi-flexexp-reset", "--force-clean-room"]
            )
        self.assertEqual(rc, 0)
        self.assertIn(f"status={STATUS_VERIFIED_G86}", buf.getvalue())

        buf_json = io.StringIO()
        with contextlib.redirect_stdout(buf_json):
            rc_j = cli_main(
                [
                    "verify-g86-marker-hdmi-flexexp-reset",
                    "--force-clean-room",
                    "--json",
                ]
            )
        self.assertEqual(rc_j, 0)
        payload = json.loads(buf_json.getvalue())
        self.assertTrue(payload["valid"])
        self.assertTrue(
            payload["marker_hdmi_flexexp_reset_guard"][
                "marker_vs_flexexp_reset_split_verified"
            ]
        )

    def test_59_cli_verify_86_gates_offline_text_and_json(self) -> None:
        with mock.patch(
            "fx3_safety.__main__.evaluate_86gate_preflight",
            return_value=self.clean_offline_86,
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = cli_main(["verify-86-gates", "--force-clean-room"])
            self.assertEqual(rc, 0)
            self.assertIn("verified=83/86", buf.getvalue())

            buf_j = io.StringIO()
            with contextlib.redirect_stdout(buf_j):
                rc_j = cli_main(["verify-86-gates", "--force-clean-room", "--json"])
            self.assertEqual(rc_j, 0)
            parsed = json.loads(buf_j.getvalue())
            self.assertEqual(parsed["summary"]["verified_gates"], 83)
            self.assertFalse(parsed["overall_ready_for_hardware_attach"])

    def test_60_cli_verify_86_gates_simulate_bench_dry_run_86_of_86(self) -> None:
        with mock.patch(
            "fx3_safety.__main__.evaluate_86gate_preflight",
            return_value=self.clean_dryrun_86,
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = cli_main(
                    ["verify-86-gates", "--force-clean-room", "--simulate-bench-dry-run"]
                )
            self.assertEqual(rc, 0)
            self.assertIn("verified=86/86", buf.getvalue())
            self.assertIn("overall_ready_for_hardware_attach=False", buf.getvalue())

    def test_61_module_main_entrypoint_text_and_json(self) -> None:
        with mock.patch(
            "fx3_safety.realhw_silent_autopixelmap_marker_flexexp_and_86gate_guard.evaluate_86gate_preflight",
            return_value=self.clean_dryrun_86,
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = module_main(["--force-clean-room", "--simulate-bench-dry-run"])
            self.assertEqual(rc, 0)
            self.assertIn("verified=86/86", buf.getvalue())

            buf_j = io.StringIO()
            with contextlib.redirect_stdout(buf_j):
                rc_j = module_main(
                    ["--force-clean-room", "--simulate-bench-dry-run", "--json"]
                )
            self.assertEqual(rc_j, 0)
            data = json.loads(buf_j.getvalue())
            self.assertEqual(data["summary"]["verified_gates"], 86)

    def test_62_zero_raw_firmware_bytes_leaked_in_serialized_86gate_reports(
        self,
    ) -> None:
        for rep in (
            self.offline_86,
            self.dryrun_86,
            self.clean_offline_86,
            self.clean_dryrun_86,
        ):
            dumped = json.dumps(rep.to_dict(), ensure_ascii=False)
            self.assertEqual(rep.raw_firmware_bytes_leaked, 0)
            self.assertEqual(rep.usb_packets_transmitted, 0)
            self.assertNotIn("\\x7fELF", dumped)


if __name__ == "__main__":
    unittest.main()
