"""Comprehensive 4-mode test suite for Phase 356 (`154/154` Hardware Safety Gates):
Gate G153 (`[Pixel Mapping]`/`[Auto Pixel Mapping]` Dual Reset Split & Sony Typos
vs FX6 `APR` + Dormant `ABB`, `Setup -> [Monitor]` 3 Init-Only Items vs Zero
`[Finder/Monitor]` & 4 Dormant EVF Symbols vs FX6 `VF Setting`/`VF Adjust`),
Gate G154 (Still-Only `P/A/S/M` `[Recall Custom hold 1..3]` Exact 11 Params with
Zero Standalone `White Balance` vs FX6 `Push AF/AGC/Iris` + `[External Output]`
HDMI `Rec. Media = On` `Slot 1` `EROFS=30` Vault + `[REC Control]` `TC Output=On`
Prerequisite + `ctrl_for_hmdi` Typo vs FX6 `SDI/HDMI` Matrix), and Unified
154-Gate Master Safety Preflight (`G01..G154`).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.dont_write_bytecode = True

SAFETY_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SAFETY_ROOT.parents[1]
if str(SAFETY_ROOT) not in sys.path:
    sys.path.insert(0, str(SAFETY_ROOT))

import fx3_safety  # noqa: E402
from fx3_safety import __main__ as safety_cli  # noqa: E402
from fx3_safety.realhw_pixelmap_apr_monitor_vfadjust_customhold_hdmi_reccontrol_and_154gate_guard import (  # noqa: E402
    ABSENT_FINDER_MONITOR_GROUP_NAME_G153,
    AUTO_PIXEL_MAPPING_SETUP_DEFAULT_G153,
    AUTO_PIXEL_MAPPING_SETUP_RESETTABLE_BY_CAMSET_RESET_G153,
    AUTO_PIXEL_MAPPING_SILENT_DEFAULT_G153,
    AUTO_PIXEL_MAPPING_SILENT_RESETTABLE_BY_CAMSET_RESET_G153,
    CTRL_FOR_HDMI_ELF_TYPO_G154,
    DISPLAY_QUALITY_DEFAULT_G153,
    DISPLAY_QUALITY_HIGH_G153,
    DISPLAY_QUALITY_STANDARD_G153,
    DONOR_CHECK_MAX_SECONDS_PHASE356,
    DORMANT_EVF_EXPOSED_ITEMS_FX3_G153,
    DORMANT_EXTERNAL_OUTPUT_HITS_G154,
    DORMANT_EXTERNAL_OUTPUT_MENUS_G154,
    DORMANT_PIXEL_MAP_FX3_TOKENS_G153,
    EINVAL_ERRNO_PHASE356,
    ENV_CLEAN_ROOM_TEST_PHASE356,
    EOPNOTSUPP_ERRNO_PHASE356,
    EROFS_ERRNO_PHASE356,
    EXACT_11_RECALL_CUSTOM_HOLD_PARAMS_G154,
    EXACT_3_MONITOR_ITEMS_G153,
    EXACT_4_DORMANT_EVF_SYMBOLS_FX3_G153,
    EXACT_4_MONITOR_FLIP_DIRECTIONS_G153,
    EXTERNAL_OUTPUT_RESETTABLE_BY_CAMSET_RESET_G154,
    FX3_DEFAULT_FW_VERSION_PHASE356,
    FX3_HELP_GUIDE_CODE_PHASE356,
    FX3_MODEL_ID_PHASE356,
    FX3_MODEL_NAME_PHASE356,
    FX6_APR_RESULT_TOKENS_G153,
    FX6_DORMANT_ABB_EXPOSED_G153,
    FX6_DORMANT_HIGH_LOW_KEY_EXPOSED_G154,
    FX6_DORMANT_VF_ADJUST_SUBMENU_ITEMS_G153,
    FX6_PIXEL_MAPPING_ELF_TYPO_EXCUTED_G153,
    FX6_PUSH_AF_MODES_G154,
    FX6_PUSH_ASSIGNABLE_BUTTONS_G154,
    FX6_SDI_HDMI_REC_CONTROL_MODES_G154,
    FX6_VF_ADJUST_SUBMENU_EXPOSED_G153,
    FX6_VF_MIRROR_SWITCH_MODES_G153,
    FX6_VF_SETTING_BRIGHTNESS_DEFAULT_G153,
    FX6_VF_SETTING_BRIGHTNESS_MAX_G153,
    FX6_VF_SETTING_BRIGHTNESS_MIN_G153,
    G153,
    G154,
    HDMI_4CH_AUDIO_CH1_CH2_G154,
    HDMI_4CH_AUDIO_CH3_CH4_G154,
    HDMI_4K_OUTPUT_ELF_TYPO_G154,
    HDMI_4K_OUTPUT_SET_OPTIONS_G154,
    HDMI_RESOLUTION_AUTO_G154,
    MEDIA_SLOT_1_PHASE356,
    MEDIA_SLOT_2_PHASE356,
    MEDIA_SLOT_NONE_PHASE356,
    MONITOR_ALL_3_ITEMS_RESETTABLE_BY_CAMSET_RESET_G153,
    MONITOR_BRIGHTNESS_DEFAULT_G153,
    MONITOR_FLIP_180_G153,
    MONITOR_FLIP_AUTO_G153,
    MONITOR_FLIP_HORIZONTAL_G153,
    MONITOR_FLIP_NO_FLIP_G153,
    MONITOR_MENU_PATH_G153,
    PINNED_FX3_APPFW_SLICES_PHASE356,
    PINNED_FX6_APPFW_SLICES_PHASE356,
    PINNED_PHASE356_DONOR_SPECS,
    PIXEL_MAPPING_ELF_TYPO_EXCUTED_G153,
    PIXEL_MAPPING_ELF_TYPO_MAPPINNG_G153,
    PIXEL_MAPPING_PRM_HAITA_USB_STREAM_TEMP_HITS_G153,
    REALHW_154GATE_PREFLIGHT_SCHEMA,
    RECALL_CUSTOM_HOLD_PARAM_COUNT_G154,
    RECALL_CUSTOM_HOLD_PERSISTENCE_FILE_G154,
    RECALL_CUSTOM_HOLD_RESETTABLE_BY_CAMSET_RESET_G154,
    RECALL_CUSTOM_HOLD_SLOTS_G154,
    RECALL_CUSTOM_HOLD_STILL_PASM_MODES_G154,
    REC_MEDIA_HDMI_OFF_ONLY_G154,
    REC_MEDIA_HDMI_ON_G154,
    RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE356,
    RESET_ACTION_INITIALIZE_PHASE356,
    RESET_ACTION_NONE_PHASE356,
    RESET_ACTION_RESET_NETWORK_SET_PHASE356,
    SHOOT_MODE_MOVIE_PHASE356,
    SHOOT_MODE_SQ_PHASE356,
    SHOOT_MODE_STILL_PHASE356,
    SHOOT_SET_REGISTRATION_WHITE_BALANCE_HITS_G154,
    STATUS_BLOCKED_G153_DORMANT_EVF_FINDER_MONITOR_OR_FX6_ABB_EOPNOTSUPP,
    STATUS_BLOCKED_G153_MONITOR_THERMAL_LOCK_OR_RESET_VIOLATION,
    STATUS_BLOCKED_G153_PIXELMAP_SHIELD_BATTERY_OR_RESET_VIOLATION,
    STATUS_BLOCKED_G153_TELEMETRY_INVALID,
    STATUS_BLOCKED_G154_CUSTOM_HOLD_OR_HDMI_REC_CTRL_PREREQ_VIOLATION,
    STATUS_BLOCKED_G154_DORMANT_WB_4K2K_24P60P_OR_MOVIE_HOLD_EOPNOTSUPP,
    STATUS_BLOCKED_G154_SLOT1_HDMI_REC_MEDIA_VAULT_EROFS,
    STATUS_BLOCKED_G154_TELEMETRY_INVALID,
    STATUS_BLOCKED_PHASE356_DONOR_INTEGRITY,
    STATUS_VERIFIED_G153,
    STATUS_VERIFIED_G154,
    Master154GateReport,
    audit_phase356_donor_contracts,
    compute_customhold_hdmi_external_output_matrix,
    compute_pixelmap_apr_monitor_vfadjust_matrix,
    evaluate_154_master_safety_gates,
    evaluate_154gate_preflight,
    evaluate_g153_pixelmap_apr_monitor_vfadjust_guard,
    evaluate_g154_recall_custom_hold_hdmi_reccontrol_vault_guard,
    main as module_main,
    resolve_fx3_custom_hold_and_external_output_state,
    resolve_fx3_pixelmap_and_monitor_state,
    run_154_gate_preflight,
    strip_elapsed_seconds_recursive_phase356,
    verify_pixelmap_apr_monitor_vfadjust_guard,
    verify_pixelmap_apr_monitor_vfadjust_guard_with_audit,
    verify_real_hardware_154gate_readiness,
    verify_recall_custom_hold_hdmi_reccontrol_vault_guard,
    verify_recall_custom_hold_hdmi_reccontrol_vault_guard_with_audit,
)


def _mock_paths_work_root_none(**_kwargs):
    return mock.MagicMock(work_root=None)


class TestPhase356PixelMapAprMonitorVfAdjustCustomHoldHdmi154GateGuard(
    unittest.TestCase
):
    """4-mode & comprehensive unit coverage for Phase 356 G153, G154, and 154-gate preflight."""

    # -----------------------------------------------------------------------
    # 1..12: Donor Integrity Audit & 4-Mode Clean-Room Fallback Contracts
    # -----------------------------------------------------------------------

    def test_01_donor_audit_runs_under_200ms_and_zero_leak(self) -> None:
        audit = audit_phase356_donor_contracts(repo_root=REPO_ROOT)
        self.assertTrue(audit.valid)
        self.assertTrue(audit.within_budget_200ms)
        self.assertLessEqual(audit.elapsed_seconds, DONOR_CHECK_MAX_SECONDS_PHASE356)
        self.assertEqual(audit.raw_firmware_bytes_leaked, 0)
        self.assertTrue(audit.fx3_contracts_verified)
        self.assertTrue(audit.fx6_contracts_verified)
        self.assertTrue(audit.four_lang_resid16_parity_verified)
        self.assertTrue(audit.zero_forbidden_myths_verified)

    def test_02_donor_audit_pinned_11_artifacts_and_slice_counts(self) -> None:
        self.assertEqual(len(PINNED_PHASE356_DONOR_SPECS), 11)
        self.assertEqual(len(PINNED_FX3_APPFW_SLICES_PHASE356), 31)
        self.assertEqual(len(PINNED_FX6_APPFW_SLICES_PHASE356), 10)
        audit = audit_phase356_donor_contracts(repo_root=REPO_ROOT)
        self.assertEqual(len(audit.file_digests), 11)

    def test_03_donor_audit_forced_clean_room_argument(self) -> None:
        audit = audit_phase356_donor_contracts(
            repo_root=REPO_ROOT, force_clean_room=True
        )
        self.assertTrue(audit.valid)
        self.assertEqual(audit.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(audit.access_mode, "SYNTHETIC_NO_DONOR_DISK_IO")
        self.assertEqual(audit.files_inspected, 0)
        self.assertEqual(audit.raw_firmware_bytes_leaked, 0)

    def test_04_donor_audit_env_fx3_clean_room_test_1(self) -> None:
        with mock.patch.dict(os.environ, {ENV_CLEAN_ROOM_TEST_PHASE356: "1"}):
            audit = audit_phase356_donor_contracts(repo_root=REPO_ROOT)
            self.assertTrue(audit.valid)
            self.assertEqual(audit.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_05_donor_audit_env_force_clean_room_1(self) -> None:
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            audit = audit_phase356_donor_contracts(repo_root=REPO_ROOT)
            self.assertTrue(audit.valid)
            self.assertEqual(audit.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_06_donor_audit_absent_donor_work_root_none_fallback(self) -> None:
        env_clean = {
            k: v
            for k, v in os.environ.items()
            if k not in ("FX3_FX6_FORCE_CLEAN_ROOM", ENV_CLEAN_ROOM_TEST_PHASE356)
        }
        with mock.patch.dict(os.environ, env_clean, clear=True), mock.patch(
            "fx3_safety.realhw_pixelmap_apr_monitor_vfadjust_customhold_hdmi_reccontrol_and_154gate_guard.resolve_donor_thermal_power_paths",
            side_effect=_mock_paths_work_root_none,
        ):
            audit = audit_phase356_donor_contracts(repo_root=REPO_ROOT)
            self.assertTrue(audit.valid)
            self.assertEqual(audit.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertEqual(audit.access_mode, "SYNTHETIC_ABSENT_DONOR_FALLBACK")
            self.assertTrue(len(audit.warnings) >= 1)

    def test_07_donor_audit_missing_file_with_override_fails_closed(self) -> None:
        env_clean = {
            k: v
            for k, v in os.environ.items()
            if k not in ("FX3_FX6_FORCE_CLEAN_ROOM", ENV_CLEAN_ROOM_TEST_PHASE356)
        }
        with tempfile.TemporaryDirectory() as tmpdir, mock.patch.dict(
            os.environ, env_clean, clear=True
        ):
            audit = audit_phase356_donor_contracts(
                work_root=Path(tmpdir),
                donor_specs_override={
                    "fake": (
                        "FX3",
                        "nonexistent.bin",
                        10,
                        "0" * 64,
                        (b"x",),
                        "Missing file",
                    )
                },
            )
            self.assertFalse(audit.valid)
            self.assertEqual(audit.status, STATUS_BLOCKED_PHASE356_DONOR_INTEGRITY)
            self.assertIn("fake:file_missing", audit.missing_markers)

    def test_08_donor_audit_work_root_none_with_override_fails_closed(self) -> None:
        env_clean = {
            k: v
            for k, v in os.environ.items()
            if k not in ("FX3_FX6_FORCE_CLEAN_ROOM", ENV_CLEAN_ROOM_TEST_PHASE356)
        }
        with mock.patch.dict(os.environ, env_clean, clear=True), mock.patch(
            "fx3_safety.realhw_pixelmap_apr_monitor_vfadjust_customhold_hdmi_reccontrol_and_154gate_guard.resolve_donor_thermal_power_paths",
            side_effect=_mock_paths_work_root_none,
        ):
            audit = audit_phase356_donor_contracts(
                donor_specs_override={
                    "fake": (
                        "FX3",
                        "nonexistent.bin",
                        10,
                        "0" * 64,
                        (b"x",),
                        "Missing work_root",
                    )
                },
            )
            self.assertFalse(audit.valid)
            self.assertIn("fake:work_root_none", audit.missing_markers)

    def test_09_donor_audit_sha_size_token_mismatch_fails_closed(self) -> None:
        env_clean = {
            k: v
            for k, v in os.environ.items()
            if k not in ("FX3_FX6_FORCE_CLEAN_ROOM", ENV_CLEAN_ROOM_TEST_PHASE356)
        }
        with tempfile.TemporaryDirectory() as tmpdir, mock.patch.dict(
            os.environ, env_clean, clear=True
        ):
            p = Path(tmpdir) / "bad.bin"
            p.write_bytes(b"hello")
            audit = audit_phase356_donor_contracts(
                work_root=Path(tmpdir),
                donor_specs_override={
                    "bad": ("FX3", "bad.bin", 99, "f" * 64, (b"missing",), "Bad spec")
                },
            )
            self.assertFalse(audit.valid)
            self.assertIn("bad:size_mismatch:5!=99", audit.missing_markers)
            self.assertIn("bad:sha256_mismatch", audit.missing_markers)
            self.assertIn("bad:token_missing_idx_0", audit.missing_markers)

    def test_10_strip_elapsed_seconds_recursive_helper(self) -> None:
        sample = {
            "elapsed_seconds": 0.123,
            "nested": [{"elapsed_seconds": 0.456, "keep": 1}],
            "tuple_val": ({"elapsed_seconds": 0.789, "ok": True},),
        }
        cleaned = strip_elapsed_seconds_recursive_phase356(sample)
        self.assertNotIn("elapsed_seconds", cleaned)
        self.assertEqual(cleaned["nested"], [{"keep": 1}])
        self.assertEqual(cleaned["tuple_val"], [{"ok": True}])

    def test_11_sony_elf_typos_pinned_constants(self) -> None:
        self.assertEqual(
            PIXEL_MAPPING_ELF_TYPO_MAPPINNG_G153,
            "BKID_APP_setting_notification_for_pixel_mappinng",
        )
        self.assertEqual(
            PIXEL_MAPPING_ELF_TYPO_EXCUTED_G153,
            "BKID_APP_pixel_mapping_excuted_status",
        )
        self.assertEqual(
            FX6_PIXEL_MAPPING_ELF_TYPO_EXCUTED_G153,
            "BKID_APP_PIXEL_MAPPING_EXCUTED_STATUS",
        )
        self.assertEqual(
            HDMI_4K_OUTPUT_ELF_TYPO_G154,
            "PRM_HAITA_hdmi_4k_outpute_apsc_restriction",
        )
        self.assertEqual(
            CTRL_FOR_HDMI_ELF_TYPO_G154,
            "BKID_APP_setting_ctrl_for_hmdi",
        )

    def test_12_g153_g154_with_audit_wrapper_aliases(self) -> None:
        v153, r153 = verify_pixelmap_apr_monitor_vfadjust_guard_with_audit(
            repo_root=REPO_ROOT, force_clean_room=True
        )
        v154, r154 = verify_recall_custom_hold_hdmi_reccontrol_vault_guard_with_audit(
            repo_root=REPO_ROOT, force_clean_room=True
        )
        self.assertTrue(v153.passed)
        self.assertTrue(r153.valid)
        self.assertEqual(v153.gate_id, G153)
        self.assertTrue(v154.passed)
        self.assertTrue(r154.valid)
        self.assertEqual(v154.gate_id, G154)

    # -----------------------------------------------------------------------
    # 13..39: Gate G153 ([Pixel Mapping] / [Auto Pixel Mapping] Dual Reset
    #         Split vs FX6 APR + Dormant ABB & Setup -> [Monitor] vs Zero EVF)
    # -----------------------------------------------------------------------

    def test_13_g153_default_state_valid_and_zero_evf(self) -> None:
        res = verify_pixelmap_apr_monitor_vfadjust_guard()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_VERIFIED_G153)
        self.assertEqual(res.block_errno, 0)
        self.assertEqual(res.monitor_menu_path, MONITOR_MENU_PATH_G153)
        self.assertFalse(res.fx3_finder_monitor_group_present)
        self.assertEqual(res.dormant_evf_exposed_items_fx3, 0)
        self.assertFalse(res.fx6_abb_menu_present)
        self.assertFalse(res.fx6_vf_adjust_backlight_submenu_present)
        self.assertEqual(res.effective_auto_pixel_mapping_setup, "On")
        self.assertEqual(res.effective_auto_pixel_mapping_silent, "Off")
        self.assertFalse(res.power_off_pixel_mapping_shutter_muted)

    def test_14_g153_dual_auto_pixel_mapping_reset_split_matrix(self) -> None:
        self.assertFalse(AUTO_PIXEL_MAPPING_SETUP_RESETTABLE_BY_CAMSET_RESET_G153)
        self.assertTrue(AUTO_PIXEL_MAPPING_SILENT_RESETTABLE_BY_CAMSET_RESET_G153)
        # Camera Settings Reset preserves Setup -> Auto Pixel Mapping = Off,
        # while resetting Silent -> Target -> Auto Pixel Mapping back to Off!
        st = resolve_fx3_pixelmap_and_monitor_state(
            auto_pixel_mapping_setup="Off",
            auto_pixel_mapping_silent="On",
            silent_mode="On",
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE356,
        )
        self.assertEqual(st["effective_auto_pixel_mapping_setup"], "Off")
        self.assertEqual(st["effective_auto_pixel_mapping_silent"], "Off")
        self.assertFalse(st["power_off_pixel_mapping_shutter_muted"])

    def test_15_g153_initialize_restores_setup_apm_and_3_monitor_items(self) -> None:
        st = resolve_fx3_pixelmap_and_monitor_state(
            auto_pixel_mapping_setup="Off",
            auto_pixel_mapping_silent="On",
            monitor_brightness_mode="Sunny Weather",
            monitor_brightness_manual_level=2,
            display_quality=DISPLAY_QUALITY_HIGH_G153,
            monitor_flip_direction=MONITOR_FLIP_180_G153,
            reset_action=RESET_ACTION_INITIALIZE_PHASE356,
        )
        self.assertEqual(st["effective_auto_pixel_mapping_setup"], AUTO_PIXEL_MAPPING_SETUP_DEFAULT_G153)
        self.assertEqual(st["effective_auto_pixel_mapping_silent"], AUTO_PIXEL_MAPPING_SILENT_DEFAULT_G153)
        self.assertEqual(st["effective_monitor_brightness_mode"], MONITOR_BRIGHTNESS_DEFAULT_G153)
        self.assertEqual(st["effective_monitor_brightness_manual_level"], 0)
        self.assertEqual(st["effective_display_quality"], DISPLAY_QUALITY_DEFAULT_G153)
        self.assertEqual(st["effective_monitor_flip_direction"], MONITOR_FLIP_AUTO_G153)

    def test_16_g153_silent_mode_alone_does_not_mute_poweroff_pixel_mapping(self) -> None:
        res = verify_pixelmap_apr_monitor_vfadjust_guard(
            silent_mode="On",
            auto_pixel_mapping_silent="Off",
            claimed_silent_mode_alone_mutes_pixel_mapping=True,
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.block_errno, EINVAL_ERRNO_PHASE356)
        self.assertEqual(
            res.status, STATUS_BLOCKED_G153_PIXELMAP_SHIELD_BATTERY_OR_RESET_VIOLATION
        )

    def test_17_g153_silent_mode_plus_silent_apm_on_mutes_shutter(self) -> None:
        res = verify_pixelmap_apr_monitor_vfadjust_guard(
            silent_mode="On",
            auto_pixel_mapping_silent="On",
            claimed_silent_mode_alone_mutes_pixel_mapping=True,
        )
        self.assertTrue(res.valid)
        self.assertTrue(res.power_off_pixel_mapping_shutter_muted)

    def test_18_g153_camset_reset_cannot_clear_setup_auto_pixel_mapping(self) -> None:
        res = verify_pixelmap_apr_monitor_vfadjust_guard(
            claimed_camset_reset_clears_setup_auto_pixel_mapping=True
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.block_errno, EINVAL_ERRNO_PHASE356)
        self.assertIn("PIXELMAP_SETUP_RESET_IMMUNITY_VIOLATION", res.violation_codes)

    def test_19_g153_manual_pixel_mapping_requires_lens_cap_and_battery(self) -> None:
        r_cap = verify_pixelmap_apr_monitor_vfadjust_guard(
            manual_pixel_mapping_requested=True,
            lens_cap_attached=False,
        )
        self.assertFalse(r_cap.valid)
        self.assertEqual(r_cap.block_errno, EINVAL_ERRNO_PHASE356)

        r_bat = verify_pixelmap_apr_monitor_vfadjust_guard(
            manual_pixel_mapping_requested=True,
            battery_level_sufficient=False,
        )
        self.assertFalse(r_bat.valid)
        self.assertEqual(r_bat.block_errno, EINVAL_ERRNO_PHASE356)

        r_ok = verify_pixelmap_apr_monitor_vfadjust_guard(
            manual_pixel_mapping_requested=True,
            lens_cap_attached=True,
            battery_level_sufficient=True,
        )
        self.assertTrue(r_ok.valid)
        self.assertTrue(r_ok.manual_pixel_mapping_requires_lens_cap_battery_and_reboot)

    def test_20_g153_prm_haita_usb_stream_temp_claim_rejected(self) -> None:
        self.assertEqual(PIXEL_MAPPING_PRM_HAITA_USB_STREAM_TEMP_HITS_G153, 0)
        res = verify_pixelmap_apr_monitor_vfadjust_guard(
            claimed_prm_haita_usb_stream_temp_blocks_pixelmap=True
        )
        self.assertFalse(res.valid)
        self.assertIn("PIXELMAP_PRM_HAITA_SPECULATION_VIOLATION", res.violation_codes)

    def test_21_g153_dormant_pixel_map_notify_and_shutter_pwr_off_rejected_eopnotsupp(self) -> None:
        self.assertEqual(len(DORMANT_PIXEL_MAP_FX3_TOKENS_G153), 2)
        res = verify_pixelmap_apr_monitor_vfadjust_guard(
            requested_dormant_pixel_map_notify_or_shutter_pwr_off_fx3=True
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.block_errno, EOPNOTSUPP_ERRNO_PHASE356)
        self.assertTrue(res.dormant_pixel_map_notify_fx3_rejected)
        self.assertEqual(
            res.status,
            STATUS_BLOCKED_G153_DORMANT_EVF_FINDER_MONITOR_OR_FX6_ABB_EOPNOTSUPP,
        )

    def test_22_g153_fx6_apr_light_detected_and_invalid_temp_rejected(self) -> None:
        self.assertEqual(len(FX6_APR_RESULT_TOKENS_G153), 2)
        r1 = verify_pixelmap_apr_monitor_vfadjust_guard(fx6_apr_light_detected=True)
        r2 = verify_pixelmap_apr_monitor_vfadjust_guard(fx6_apr_invalid_temperature=True)
        self.assertFalse(r1.valid)
        self.assertFalse(r2.valid)
        self.assertIn("FX6_APR_LIGHT_DETECTED_VIOLATION", r1.violation_codes)
        self.assertIn("FX6_APR_INVALID_TEMPERATURE_VIOLATION", r2.violation_codes)

    def test_23_g153_fx6_dormant_abb_rejected_eopnotsupp(self) -> None:
        self.assertEqual(FX6_DORMANT_ABB_EXPOSED_G153, 0)
        res = verify_pixelmap_apr_monitor_vfadjust_guard(
            requested_fx6_dormant_abb_menu=True
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.block_errno, EOPNOTSUPP_ERRNO_PHASE356)
        self.assertTrue(res.fx6_abb_or_vf_submenu_spoof_rejected)

    def test_24_g153_finder_monitor_group_spoof_rejected_eopnotsupp(self) -> None:
        self.assertEqual(ABSENT_FINDER_MONITOR_GROUP_NAME_G153, "Setup -> [Finder/Monitor]")
        res = verify_pixelmap_apr_monitor_vfadjust_guard(
            claimed_finder_monitor_group_exists_on_fx3=True
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.block_errno, EOPNOTSUPP_ERRNO_PHASE356)
        self.assertTrue(res.dormant_evf_or_finder_monitor_spoof_rejected)

    def test_25_g153_all_4_dormant_evf_symbols_rejected_eopnotsupp(self) -> None:
        self.assertEqual(DORMANT_EVF_EXPOSED_ITEMS_FX3_G153, 0)
        self.assertEqual(len(EXACT_4_DORMANT_EVF_SYMBOLS_FX3_G153), 4)
        for evf_item in EXACT_4_DORMANT_EVF_SYMBOLS_FX3_G153:
            res = verify_pixelmap_apr_monitor_vfadjust_guard(
                requested_dormant_evf_item_fx3=evf_item
            )
            self.assertFalse(res.valid)
            self.assertEqual(res.block_errno, EOPNOTSUPP_ERRNO_PHASE356)
            self.assertEqual(res.dormant_evf_exposed_items_fx3, 0)

    def test_26_g153_setup_monitor_exact_3_items_and_reset_immunity(self) -> None:
        self.assertEqual(len(EXACT_3_MONITOR_ITEMS_G153), 3)
        self.assertFalse(MONITOR_ALL_3_ITEMS_RESETTABLE_BY_CAMSET_RESET_G153)
        st = resolve_fx3_pixelmap_and_monitor_state(
            monitor_brightness_mode="Sunny Weather",
            monitor_brightness_manual_level=2,
            display_quality=DISPLAY_QUALITY_HIGH_G153,
            monitor_flip_direction=MONITOR_FLIP_HORIZONTAL_G153,
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE356,
        )
        self.assertEqual(st["effective_monitor_brightness_mode"], "Sunny Weather")
        self.assertEqual(st["effective_display_quality"], DISPLAY_QUALITY_HIGH_G153)
        self.assertEqual(st["effective_monitor_flip_direction"], MONITOR_FLIP_HORIZONTAL_G153)

        bad = verify_pixelmap_apr_monitor_vfadjust_guard(
            claimed_camset_reset_clears_monitor_3items=True
        )
        self.assertFalse(bad.valid)
        self.assertEqual(bad.status, STATUS_BLOCKED_G153_MONITOR_THERMAL_LOCK_OR_RESET_VIOLATION)

    def test_27_g153_display_quality_thermal_locks_to_standard_when_hot(self) -> None:
        st = resolve_fx3_pixelmap_and_monitor_state(
            display_quality=DISPLAY_QUALITY_HIGH_G153,
            body_temperature_high=True,
        )
        self.assertTrue(st["display_quality_thermal_locked_to_standard"])
        self.assertEqual(st["effective_display_quality"], DISPLAY_QUALITY_STANDARD_G153)

        bad = verify_pixelmap_apr_monitor_vfadjust_guard(
            display_quality=DISPLAY_QUALITY_HIGH_G153,
            body_temperature_high=True,
            claimed_display_quality_high_unlocked_when_hot=True,
        )
        self.assertFalse(bad.valid)
        self.assertEqual(bad.status, STATUS_BLOCKED_G153_MONITOR_THERMAL_LOCK_OR_RESET_VIOLATION)

    def test_28_g153_fx6_vf_adjust_backlight_submenu_rejected_eopnotsupp(self) -> None:
        self.assertEqual(FX6_VF_ADJUST_SUBMENU_EXPOSED_G153, 0)
        self.assertEqual(len(FX6_DORMANT_VF_ADJUST_SUBMENU_ITEMS_G153), 4)
        res = verify_pixelmap_apr_monitor_vfadjust_guard(
            requested_fx6_vf_adjust_backlight_submenu=True
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.block_errno, EOPNOTSUPP_ERRNO_PHASE356)
        self.assertFalse(res.fx6_vf_adjust_backlight_submenu_present)

    def test_29_g153_fx6_vf_setting_bounds_and_mirror_switch(self) -> None:
        for b in (FX6_VF_SETTING_BRIGHTNESS_MIN_G153, FX6_VF_SETTING_BRIGHTNESS_DEFAULT_G153, FX6_VF_SETTING_BRIGHTNESS_MAX_G153):
            for mirror in FX6_VF_MIRROR_SWITCH_MODES_G153:
                self.assertTrue(
                    verify_pixelmap_apr_monitor_vfadjust_guard(
                        fx6_vf_brightness=b, fx6_vf_mirror_switch=mirror
                    ).valid
                )
        for bad_b in (0, 16, True):
            r = verify_pixelmap_apr_monitor_vfadjust_guard(fx6_vf_brightness=bad_b)
            self.assertFalse(r.valid)
            self.assertEqual(r.status, STATUS_BLOCKED_G153_TELEMETRY_INVALID)

    def test_30_g153_monitor_brightness_manual_bounds_and_modes(self) -> None:
        for lvl in (-2, -1, 0, 1, 2):
            self.assertTrue(
                verify_pixelmap_apr_monitor_vfadjust_guard(
                    monitor_brightness_manual_level=lvl
                ).valid
            )
        for bad_lvl in (-3, 3, False):
            r = verify_pixelmap_apr_monitor_vfadjust_guard(
                monitor_brightness_manual_level=bad_lvl
            )
            self.assertFalse(r.valid)
            self.assertEqual(r.status, STATUS_BLOCKED_G153_TELEMETRY_INVALID)

    def test_31_g153_all_4_monitor_flip_directions_supported(self) -> None:
        self.assertEqual(len(EXACT_4_MONITOR_FLIP_DIRECTIONS_G153), 4)
        for d in EXACT_4_MONITOR_FLIP_DIRECTIONS_G153:
            self.assertTrue(
                verify_pixelmap_apr_monitor_vfadjust_guard(
                    monitor_flip_direction=d
                ).valid
            )
        self.assertEqual(
            verify_pixelmap_apr_monitor_vfadjust_guard(
                monitor_flip_direction="90 Degree"
            ).status,
            STATUS_BLOCKED_G153_TELEMETRY_INVALID,
        )

    def test_32_g153_combinatoric_matrix_384_states(self) -> None:
        m = compute_pixelmap_apr_monitor_vfadjust_matrix()
        self.assertEqual(m["total_matrix_states"], 384)
        self.assertGreater(m["setup_apm_reset_preserved_count"], 0)
        self.assertGreater(m["silent_apm_reset_to_off_count"], 0)
        self.assertGreater(m["silent_on_shutter_not_muted_count"], 0)
        self.assertGreater(m["dq_thermal_locked_standard_count"], 0)
        self.assertGreater(m["monitor_flip_reset_preserved_count"], 0)

    def test_33_g153_reset_network_set_preserves_pixelmap_and_monitor(self) -> None:
        st = resolve_fx3_pixelmap_and_monitor_state(
            auto_pixel_mapping_setup="Off",
            auto_pixel_mapping_silent="On",
            monitor_brightness_mode="Sunny Weather",
            display_quality=DISPLAY_QUALITY_HIGH_G153,
            monitor_flip_direction=MONITOR_FLIP_NO_FLIP_G153,
            reset_action=RESET_ACTION_RESET_NETWORK_SET_PHASE356,
        )
        self.assertEqual(st["effective_auto_pixel_mapping_setup"], "Off")
        self.assertEqual(st["effective_auto_pixel_mapping_silent"], "On")
        self.assertEqual(st["effective_monitor_brightness_mode"], "Sunny Weather")
        self.assertEqual(st["effective_display_quality"], DISPLAY_QUALITY_HIGH_G153)
        self.assertEqual(st["effective_monitor_flip_direction"], MONITOR_FLIP_NO_FLIP_G153)

    def test_34_g153_invalid_identity_telemetry_rejected(self) -> None:
        for bad_kw in (
            {"body_model_name": "ILME-FX6"},
            {"body_model_id": 0x1234},
            {"help_guide_code": "5-024-458-18"},
            {"firmware_version": ""},
        ):
            r = verify_pixelmap_apr_monitor_vfadjust_guard(**bad_kw)
            self.assertFalse(r.valid)
            self.assertEqual(r.status, STATUS_BLOCKED_G153_TELEMETRY_INVALID)

    def test_35_g153_invalid_enum_telemetry_rejected(self) -> None:
        for bad_kw in (
            {"auto_pixel_mapping_setup": "Auto"},
            {"auto_pixel_mapping_silent": "Target"},
            {"silent_mode": "Yes"},
            {"monitor_brightness_mode": "Auto"},
            {"display_quality": "Ultra"},
            {"fx6_vf_color_mode": "Sepia"},
            {"fx6_vf_mirror_switch": "Diagonal"},
            {"reset_action": "Wipe"},
        ):
            r = verify_pixelmap_apr_monitor_vfadjust_guard(**bad_kw)
            self.assertFalse(r.valid)
            self.assertEqual(r.status, STATUS_BLOCKED_G153_TELEMETRY_INVALID)

    def test_36_g153_unknown_evf_symbol_rejected_eopnotsupp(self) -> None:
        r = verify_pixelmap_apr_monitor_vfadjust_guard(
            requested_dormant_evf_item_fx3="EVF Diopter Motorized"
        )
        self.assertFalse(r.valid)
        self.assertEqual(r.block_errno, EOPNOTSUPP_ERRNO_PHASE356)

    def test_37_g153_evaluate_with_local_donor_o_rdonly(self) -> None:
        verdict, wrapped = evaluate_g153_pixelmap_apr_monitor_vfadjust_guard(
            repo_root=REPO_ROOT
        )
        self.assertTrue(verdict.passed)
        self.assertTrue(wrapped.valid)
        self.assertFalse(wrapped.persistent_emmc_writes_authorized)
        self.assertFalse(wrapped.cross_model_flash_authorized)
        self.assertEqual(wrapped.raw_firmware_bytes_leaked, 0)

    def test_38_g153_evaluate_fault_propagates_to_verdict(self) -> None:
        verdict, wrapped = evaluate_g153_pixelmap_apr_monitor_vfadjust_guard(
            repo_root=REPO_ROOT,
            force_clean_room=True,
            requested_dormant_evf_item_fx3="Finder Frame Rate",
        )
        self.assertFalse(verdict.passed)
        self.assertFalse(wrapped.valid)
        self.assertEqual(
            verdict.status,
            STATUS_BLOCKED_G153_DORMANT_EVF_FINDER_MONITOR_OR_FX6_ABB_EOPNOTSUPP,
        )

    def test_39_g153_redlines_always_locked_false_and_zero(self) -> None:
        res = verify_pixelmap_apr_monitor_vfadjust_guard()
        self.assertFalse(res.emmc_writes_authorized)
        self.assertFalse(res.cross_model_flash_authorized)
        self.assertEqual(res.usb_packets_transmitted, 0)
        self.assertEqual(res.raw_firmware_bytes_leaked, 0)

    # -----------------------------------------------------------------------
    # 40..69: Gate G154 (Still-Only [Recall Custom hold 1..3] 11 Params / Zero
    #         WB vs FX6 Push & HDMI Slot-1 EROFS=30 Vault / REC Control)
    # -----------------------------------------------------------------------

    def test_40_g154_default_state_valid_and_exact_11_params(self) -> None:
        res = verify_recall_custom_hold_hdmi_reccontrol_vault_guard()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_VERIFIED_G154)
        self.assertEqual(res.block_errno, 0)
        self.assertTrue(res.recall_custom_hold_available)
        self.assertEqual(len(res.recall_custom_hold_exact_11_params), RECALL_CUSTOM_HOLD_PARAM_COUNT_G154)
        self.assertEqual(res.recall_custom_hold_exact_11_params, EXACT_11_RECALL_CUSTOM_HOLD_PARAMS_G154)
        self.assertFalse(res.recall_custom_hold_standalone_wb_present)
        self.assertEqual(res.shoot_set_registration_white_balance_hits, 0)
        self.assertFalse(res.recall_custom_hold_resettable_by_camset_reset)
        self.assertEqual(res.recall_custom_hold_persistence_file, RECALL_CUSTOM_HOLD_PERSISTENCE_FILE_G154)
        self.assertFalse(res.external_output_resettable_by_camset_reset)
        self.assertEqual(res.ctrl_for_hdmi_elf_typo, CTRL_FOR_HDMI_ELF_TYPO_G154)
        self.assertEqual(res.slot1_data_sector_writes, 0)
        self.assertEqual(res.emmc_nflasha_write_count, 0)

    def test_41_g154_recall_custom_hold_allowed_only_still_pasm(self) -> None:
        for slot in RECALL_CUSTOM_HOLD_SLOTS_G154:
            for exp_m in RECALL_CUSTOM_HOLD_STILL_PASM_MODES_G154:
                r = verify_recall_custom_hold_hdmi_reccontrol_vault_guard(
                    shoot_mode=SHOOT_MODE_STILL_PHASE356,
                    exposure_mode=exp_m,
                    recall_custom_hold_slot=slot,
                )
                self.assertTrue(r.valid)
                self.assertTrue(r.recall_custom_hold_available)

    def test_42_g154_recall_custom_hold_rejected_in_movie_sq_and_iauto_eopnotsupp(self) -> None:
        for slot in RECALL_CUSTOM_HOLD_SLOTS_G154:
            for bad_sm, bad_exp in (
                (SHOOT_MODE_MOVIE_PHASE356, "P"),
                (SHOOT_MODE_SQ_PHASE356, "M"),
                (SHOOT_MODE_STILL_PHASE356, "iAuto"),
            ):
                r = verify_recall_custom_hold_hdmi_reccontrol_vault_guard(
                    shoot_mode=bad_sm,
                    exposure_mode=bad_exp,
                    recall_custom_hold_slot=slot,
                )
                self.assertFalse(r.valid)
                self.assertFalse(r.recall_custom_hold_available)
                self.assertEqual(r.block_errno, EOPNOTSUPP_ERRNO_PHASE356)
                self.assertEqual(
                    r.status,
                    STATUS_BLOCKED_G154_DORMANT_WB_4K2K_24P60P_OR_MOVIE_HOLD_EOPNOTSUPP,
                )

    def test_43_g154_standalone_wb_checkbox_rejected_eopnotsupp(self) -> None:
        self.assertEqual(SHOOT_SET_REGISTRATION_WHITE_BALANCE_HITS_G154, 0)
        r = verify_recall_custom_hold_hdmi_reccontrol_vault_guard(
            claimed_standalone_wb_checkbox_in_recall_custom_hold=True
        )
        self.assertFalse(r.valid)
        self.assertEqual(r.block_errno, EOPNOTSUPP_ERRNO_PHASE356)
        self.assertIn("RECALL_CUSTOM_HOLD_ZERO_STANDALONE_WB_EOPNOTSUPP", r.violation_codes)

    def test_44_g154_self_timer_in_recall_drive_mode_rejected(self) -> None:
        r = verify_recall_custom_hold_hdmi_reccontrol_vault_guard(
            claimed_self_timer_in_recall_drive_mode=True
        )
        self.assertFalse(r.valid)
        self.assertEqual(r.block_errno, EINVAL_ERRNO_PHASE356)
        self.assertIn("RECALL_CUSTOM_HOLD_NO_SELF_TIMER_VIOLATION", r.violation_codes)

    def test_45_g154_tracking_on_in_movie_or_sq_rejected(self) -> None:
        r = verify_recall_custom_hold_hdmi_reccontrol_vault_guard(
            claimed_tracking_on_available_in_movie_or_sq=True
        )
        self.assertFalse(r.valid)
        self.assertEqual(r.block_errno, EINVAL_ERRNO_PHASE356)

    def test_46_g154_fx6_push_buttons_and_dormant_high_low_key(self) -> None:
        self.assertEqual(len(FX6_PUSH_ASSIGNABLE_BUTTONS_G154), 6)
        self.assertEqual(FX6_PUSH_AF_MODES_G154, ("AF", "Single-shot AF(AF-S)"))
        self.assertEqual(FX6_DORMANT_HIGH_LOW_KEY_EXPOSED_G154, 0)

        r_hlk = verify_recall_custom_hold_hdmi_reccontrol_vault_guard(
            requested_fx6_dormant_high_low_key=True
        )
        self.assertFalse(r_hlk.valid)
        self.assertEqual(r_hlk.block_errno, EOPNOTSUPP_ERRNO_PHASE356)

        r_agc = verify_recall_custom_hold_hdmi_reccontrol_vault_guard(
            claimed_fx6_push_agc_active_in_cine_ei_or_bokeh=True
        )
        self.assertFalse(r_agc.valid)
        self.assertEqual(r_agc.block_errno, EINVAL_ERRNO_PHASE356)

        r_iris = verify_recall_custom_hold_hdmi_reccontrol_vault_guard(
            claimed_fx6_push_auto_iris_active_on_manual_lens_or_bokeh=True
        )
        self.assertFalse(r_iris.valid)
        self.assertEqual(r_iris.block_errno, EINVAL_ERRNO_PHASE356)

    def test_47_g154_slot1_erofs30_vault_blocks_hdmi_rec_media_on_write(self) -> None:
        r = verify_recall_custom_hold_hdmi_reccontrol_vault_guard(
            shoot_mode=SHOOT_MODE_MOVIE_PHASE356,
            rec_media_dur_hdmi_output=REC_MEDIA_HDMI_ON_G154,
            target_media_slot=MEDIA_SLOT_1_PHASE356,
            hdmi_recording_write_requested=True,
        )
        self.assertFalse(r.valid)
        self.assertEqual(r.block_errno, EROFS_ERRNO_PHASE356)
        self.assertEqual(r.status, STATUS_BLOCKED_G154_SLOT1_HDMI_REC_MEDIA_VAULT_EROFS)
        self.assertTrue(r.slot1_tier0_vault_firewall_blocked)
        self.assertEqual(r.slot1_data_sector_writes, 0)
        self.assertEqual(r.emmc_nflasha_write_count, 0)

    def test_48_g154_off_hdmi_only_bypasses_slot1_write_in_movie_mode(self) -> None:
        r = verify_recall_custom_hold_hdmi_reccontrol_vault_guard(
            shoot_mode=SHOOT_MODE_MOVIE_PHASE356,
            rec_media_dur_hdmi_output=REC_MEDIA_HDMI_OFF_ONLY_G154,
            target_media_slot=MEDIA_SLOT_1_PHASE356,
            hdmi_recording_write_requested=True,
            requested_write_operation=False,
        )
        self.assertTrue(r.valid)
        self.assertFalse(r.slot1_tier0_vault_firewall_blocked)
        self.assertEqual(r.effective_rec_media_dur_hdmi_output, REC_MEDIA_HDMI_OFF_ONLY_G154)
        self.assertEqual(r.effective_hdmi_info_display, "Off")
        self.assertEqual(r.slot1_data_sector_writes, 0)

    def test_49_g154_sq_forces_rec_media_on_and_still_hits_slot1_erofs30(self) -> None:
        r = verify_recall_custom_hold_hdmi_reccontrol_vault_guard(
            shoot_mode=SHOOT_MODE_SQ_PHASE356,
            rec_media_dur_hdmi_output=REC_MEDIA_HDMI_OFF_ONLY_G154,
            target_media_slot=MEDIA_SLOT_1_PHASE356,
            hdmi_recording_write_requested=True,
        )
        self.assertFalse(r.valid)
        self.assertTrue(r.rec_media_locked_on_in_sq)
        self.assertEqual(r.effective_rec_media_dur_hdmi_output, REC_MEDIA_HDMI_ON_G154)
        self.assertEqual(r.block_errno, EROFS_ERRNO_PHASE356)
        self.assertEqual(r.status, STATUS_BLOCKED_G154_SLOT1_HDMI_REC_MEDIA_VAULT_EROFS)

    def test_50_g154_slot2_allows_rec_media_on_write_cleanly(self) -> None:
        r = verify_recall_custom_hold_hdmi_reccontrol_vault_guard(
            shoot_mode=SHOOT_MODE_MOVIE_PHASE356,
            rec_media_dur_hdmi_output=REC_MEDIA_HDMI_ON_G154,
            target_media_slot=MEDIA_SLOT_2_PHASE356,
            hdmi_recording_write_requested=True,
        )
        self.assertTrue(r.valid)
        self.assertFalse(r.slot1_tier0_vault_firewall_blocked)

    def test_51_g154_rec_control_requires_tc_output_on_and_compatible_recorder(self) -> None:
        r_no_tc = verify_recall_custom_hold_hdmi_reccontrol_vault_guard(
            shoot_mode=SHOOT_MODE_MOVIE_PHASE356,
            time_code_output="Off",
            rec_control="On",
        )
        self.assertFalse(r_no_tc.valid)
        self.assertFalse(r_no_tc.rec_control_tc_prerequisite_satisfied)
        self.assertEqual(
            r_no_tc.status,
            STATUS_BLOCKED_G154_CUSTOM_HOLD_OR_HDMI_REC_CTRL_PREREQ_VIOLATION,
        )

        r_incompat = verify_recall_custom_hold_hdmi_reccontrol_vault_guard(
            shoot_mode=SHOOT_MODE_MOVIE_PHASE356,
            time_code_output="On",
            rec_control="On",
            rec_control_external_recorder_compatible=False,
        )
        self.assertFalse(r_incompat.valid)

        r_ok = verify_recall_custom_hold_hdmi_reccontrol_vault_guard(
            shoot_mode=SHOOT_MODE_MOVIE_PHASE356,
            time_code_output="On",
            rec_control="On",
            rec_control_external_recorder_compatible=True,
        )
        self.assertTrue(r_ok.valid)
        self.assertTrue(r_ok.rec_control_tc_prerequisite_satisfied)

    def test_52_g154_sq_disables_tc_output_blocking_rec_control(self) -> None:
        r = verify_recall_custom_hold_hdmi_reccontrol_vault_guard(
            shoot_mode=SHOOT_MODE_SQ_PHASE356,
            time_code_output="On",
            rec_control="On",
        )
        self.assertFalse(r.valid)
        self.assertEqual(r.effective_time_code_output, "Off")
        self.assertFalse(r.rec_control_tc_prerequisite_satisfied)

    def test_53_g154_log_or_pplut_forces_1080_when_rec_media_on_and_non_raw(self) -> None:
        st_log = resolve_fx3_custom_hold_and_external_output_state(
            shoot_mode=SHOOT_MODE_MOVIE_PHASE356,
            rec_media_dur_hdmi_output=REC_MEDIA_HDMI_ON_G154,
            raw_output="Off",
            output_resolution="2160p",
            log_shooting_mode="Flexible ISO",
        )
        self.assertTrue(st_log["output_resolution_forced_1080_by_log_or_pplut"])
        self.assertEqual(st_log["effective_output_resolution"], "1080p")

        st_pplut = resolve_fx3_custom_hold_and_external_output_state(
            shoot_mode=SHOOT_MODE_MOVIE_PHASE356,
            rec_media_dur_hdmi_output=REC_MEDIA_HDMI_ON_G154,
            raw_output="Off",
            output_resolution="2160p",
            picture_profile="PPLUT1",
        )
        self.assertTrue(st_pplut["output_resolution_forced_1080_by_log_or_pplut"])
        self.assertEqual(st_pplut["effective_output_resolution"], "1080p")

        bad = verify_recall_custom_hold_hdmi_reccontrol_vault_guard(
            shoot_mode=SHOOT_MODE_MOVIE_PHASE356,
            log_shooting_mode="Cine EI",
            claimed_log_or_pplut_outputs_4k_when_rec_media_on_and_non_raw=True,
        )
        self.assertFalse(bad.valid)
        self.assertEqual(bad.block_errno, EINVAL_ERRNO_PHASE356)

    def test_54_g154_hdmi_info_display_blacks_out_lcd_and_auto_forces_off(self) -> None:
        st_black = resolve_fx3_custom_hold_and_external_output_state(
            hdmi_connected=True,
            hdmi_info_display="On",
            rec_media_dur_hdmi_output=REC_MEDIA_HDMI_ON_G154,
            raw_output="Off",
        )
        self.assertTrue(st_black["builtin_lcd_blacked_out"])
        self.assertEqual(st_black["effective_hdmi_info_display"], "On")

        st_raw = resolve_fx3_custom_hold_and_external_output_state(
            hdmi_connected=True,
            hdmi_info_display="On",
            raw_output="On",
        )
        self.assertFalse(st_raw["builtin_lcd_blacked_out"])
        self.assertEqual(st_raw["effective_hdmi_info_display"], "Off")

    def test_55_g154_24_00p_reboot_and_playback_isolation(self) -> None:
        for opt in HDMI_4K_OUTPUT_SET_OPTIONS_G154:
            r = verify_recall_custom_hold_hdmi_reccontrol_vault_guard(
                hdmi_4k_output_setting=opt
            )
            self.assertTrue(r.valid)
            self.assertEqual(
                r.hdmi_24_00p_requires_reboot_and_playback_isolation,
                opt == "24.00p 10bit",
            )
        bad = verify_recall_custom_hold_hdmi_reccontrol_vault_guard(
            hdmi_4k_output_setting="24.00p 10bit",
            claimed_24_00p_requires_zero_reboot_or_cross_plays=True,
        )
        self.assertFalse(bad.valid)
        self.assertEqual(bad.block_errno, EINVAL_ERRNO_PHASE356)

    def test_56_g154_dormant_4k2k_and_24p60p_output_rejected_eopnotsupp(self) -> None:
        self.assertEqual(DORMANT_EXTERNAL_OUTPUT_HITS_G154, 0)
        self.assertEqual(DORMANT_EXTERNAL_OUTPUT_MENUS_G154, ("4K/2K Output", "24p/60p Output"))
        r = verify_recall_custom_hold_hdmi_reccontrol_vault_guard(
            requested_dormant_4k2k_or_24p60p_output_fx3=True
        )
        self.assertFalse(r.valid)
        self.assertEqual(r.block_errno, EOPNOTSUPP_ERRNO_PHASE356)

    def test_57_g154_camset_reset_preserves_external_output_while_initialize_restores(self) -> None:
        st_rst = resolve_fx3_custom_hold_and_external_output_state(
            hdmi_resolution="1080p",
            rec_media_dur_hdmi_output=REC_MEDIA_HDMI_OFF_ONLY_G154,
            ctrl_for_hdmi="Off",
            hdmi_4ch_audio_output=HDMI_4CH_AUDIO_CH3_CH4_G154,
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE356,
        )
        self.assertEqual(st_rst["effective_hdmi_resolution"], "1080p")
        self.assertEqual(st_rst["effective_rec_media_dur_hdmi_output"], REC_MEDIA_HDMI_OFF_ONLY_G154)
        self.assertEqual(st_rst["effective_ctrl_for_hdmi"], "Off")
        self.assertEqual(st_rst["effective_4ch_audio_output"], HDMI_4CH_AUDIO_CH3_CH4_G154)

        st_init = resolve_fx3_custom_hold_and_external_output_state(
            hdmi_resolution="1080p",
            rec_media_dur_hdmi_output=REC_MEDIA_HDMI_OFF_ONLY_G154,
            ctrl_for_hdmi="Off",
            hdmi_4ch_audio_output=HDMI_4CH_AUDIO_CH3_CH4_G154,
            reset_action=RESET_ACTION_INITIALIZE_PHASE356,
        )
        self.assertEqual(st_init["effective_hdmi_resolution"], HDMI_RESOLUTION_AUTO_G154)
        self.assertEqual(st_init["effective_rec_media_dur_hdmi_output"], REC_MEDIA_HDMI_ON_G154)
        self.assertEqual(st_init["effective_ctrl_for_hdmi"], "On")
        self.assertEqual(st_init["effective_4ch_audio_output"], HDMI_4CH_AUDIO_CH1_CH2_G154)

    def test_58_g154_camset_reset_immunity_violation_rejected(self) -> None:
        r = verify_recall_custom_hold_hdmi_reccontrol_vault_guard(
            claimed_camset_reset_clears_reg_custom_or_external_output=True
        )
        self.assertFalse(r.valid)
        self.assertEqual(r.block_errno, EINVAL_ERRNO_PHASE356)

    def test_59_g154_sq_lock_claim_rejected(self) -> None:
        r = verify_recall_custom_hold_hdmi_reccontrol_vault_guard(
            claimed_sq_allows_off_hdmi_only_or_tc_output_on=True
        )
        self.assertFalse(r.valid)
        self.assertEqual(r.block_errno, EINVAL_ERRNO_PHASE356)

    def test_60_g154_combinatoric_matrix_384_states(self) -> None:
        m = compute_customhold_hdmi_external_output_matrix()
        self.assertEqual(m["total_matrix_states"], 384)
        self.assertGreater(m["recall_available_count"], 0)
        self.assertGreater(m["sq_rec_media_locked_on_count"], 0)
        self.assertGreater(m["log_forced_1080_count"], 0)
        self.assertGreater(m["info_forced_off_count"], 0)
        self.assertGreater(m["ext_out_reset_preserved_count"], 0)
        self.assertGreater(m["slot1_erofs_risk_count"], 0)

    def test_61_g154_fx6_sdi_hdmi_rec_control_modes_constant(self) -> None:
        self.assertEqual(
            FX6_SDI_HDMI_REC_CONTROL_MODES_G154,
            ("Off", "SDI/HDMI Remote I/F", "Parallel Rec"),
        )

    def test_62_g154_slot0_none_allows_no_slot1_block(self) -> None:
        r = verify_recall_custom_hold_hdmi_reccontrol_vault_guard(
            target_media_slot=MEDIA_SLOT_NONE_PHASE356,
            hdmi_recording_write_requested=False,
        )
        self.assertTrue(r.valid)
        self.assertFalse(r.slot1_tier0_vault_firewall_blocked)

    def test_63_g154_explicit_write_op_on_slot1_blocked_even_if_hdmi_only(self) -> None:
        r = verify_recall_custom_hold_hdmi_reccontrol_vault_guard(
            rec_media_dur_hdmi_output=REC_MEDIA_HDMI_OFF_ONLY_G154,
            target_media_slot=MEDIA_SLOT_1_PHASE356,
            requested_write_operation=True,
        )
        self.assertFalse(r.valid)
        self.assertEqual(r.block_errno, EROFS_ERRNO_PHASE356)
        self.assertEqual(r.status, STATUS_BLOCKED_G154_SLOT1_HDMI_REC_MEDIA_VAULT_EROFS)

    def test_64_g154_invalid_identity_rejected(self) -> None:
        for bad_kw in (
            {"body_model_name": "ILCE-7SM3"},
            {"body_model_id": 0x0001},
            {"help_guide_code": "ilc/2000"},
            {"firmware_version": "abc"},
        ):
            r = verify_recall_custom_hold_hdmi_reccontrol_vault_guard(**bad_kw)
            self.assertFalse(r.valid)
            self.assertEqual(r.status, STATUS_BLOCKED_G154_TELEMETRY_INVALID)

    def test_65_g154_invalid_enum_telemetry_rejected(self) -> None:
        for bad_kw in (
            {"shoot_mode": "Panorama"},
            {"exposure_mode": "SCN"},
            {"recall_custom_hold_slot": "Recall Custom hold 4"},
            {"hdmi_resolution": "4320p"},
            {"rec_media_dur_hdmi_output": "Disabled"},
            {"output_resolution": "480p"},
            {"hdmi_4k_output_setting": "120p 10bit"},
            {"raw_output": "Auto"},
            {"time_code_output": "Yes"},
            {"rec_control": "Auto"},
            {"hdmi_info_display": "1"},
            {"ctrl_for_hdmi": "Enabled"},
            {"hdmi_4ch_audio_output": "CH1/CH2/CH3/CH4"},
            {"target_media_slot": 3},
            {"target_media_slot": True},
            {"reset_action": "Factory"},
        ):
            r = verify_recall_custom_hold_hdmi_reccontrol_vault_guard(**bad_kw)
            self.assertFalse(r.valid)
            self.assertEqual(r.status, STATUS_BLOCKED_G154_TELEMETRY_INVALID)

    def test_66_g154_evaluate_with_local_donor_o_rdonly(self) -> None:
        verdict, wrapped = evaluate_g154_recall_custom_hold_hdmi_reccontrol_vault_guard(
            repo_root=REPO_ROOT
        )
        self.assertTrue(verdict.passed)
        self.assertTrue(wrapped.valid)
        self.assertFalse(wrapped.persistent_emmc_writes_authorized)
        self.assertFalse(wrapped.cross_model_flash_authorized)
        self.assertEqual(wrapped.raw_firmware_bytes_leaked, 0)

    def test_67_g154_evaluate_fault_propagates_to_verdict(self) -> None:
        verdict, wrapped = evaluate_g154_recall_custom_hold_hdmi_reccontrol_vault_guard(
            repo_root=REPO_ROOT,
            force_clean_room=True,
            target_media_slot=MEDIA_SLOT_1_PHASE356,
            hdmi_recording_write_requested=True,
        )
        self.assertFalse(verdict.passed)
        self.assertFalse(wrapped.valid)
        self.assertEqual(
            verdict.status, STATUS_BLOCKED_G154_SLOT1_HDMI_REC_MEDIA_VAULT_EROFS
        )

    def test_68_g154_redlines_always_locked_false_and_zero(self) -> None:
        res = verify_recall_custom_hold_hdmi_reccontrol_vault_guard()
        self.assertFalse(res.emmc_writes_authorized)
        self.assertFalse(res.cross_model_flash_authorized)
        self.assertEqual(res.usb_packets_transmitted, 0)
        self.assertEqual(res.raw_firmware_bytes_leaked, 0)

    def test_69_g154_reset_network_set_preserves_external_output(self) -> None:
        st = resolve_fx3_custom_hold_and_external_output_state(
            hdmi_resolution="2160p",
            ctrl_for_hdmi="Off",
            reset_action=RESET_ACTION_RESET_NETWORK_SET_PHASE356,
        )
        self.assertEqual(st["effective_hdmi_resolution"], "2160p")
        self.assertEqual(st["effective_ctrl_for_hdmi"], "Off")

    # -----------------------------------------------------------------------
    # 70..104: Unified 154-Gate Master Preflight, 4-Mode Matrix, Forward-Compat
    #          Discovery, CLI Subprocesses & Exports
    # -----------------------------------------------------------------------

    def test_70_preflight_154_offline_default_verifies_151_of_154(self) -> None:
        rep = evaluate_154gate_preflight(REPO_ROOT)
        self.assertIsInstance(rep, Master154GateReport)
        self.assertEqual(rep.schema_version, REALHW_154GATE_PREFLIGHT_SCHEMA)
        self.assertEqual(rep.summary["total_gates"], 154)
        self.assertEqual(rep.summary["verified_gates"], 151)
        self.assertEqual(rep.summary["blocked_or_pending_gates"], 3)
        self.assertTrue(rep.offline_151_gates_verified)
        self.assertFalse(rep.all_154_gates_verified)
        self.assertTrue(rep.g153_to_g154_all_passed)
        self.assertTrue(rep.g13_to_g154_all_passed)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.hardware_live_attachment_authorized)
        self.assertFalse(rep.cross_model_flash_authorized)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertEqual(rep.usb_packets_transmitted, 0)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)
        self.assertEqual(rep.status, "VERIFIED_151_OF_154_AWAITING_PHYSICAL_TIER0")

    def test_71_preflight_154_dry_run_verifies_154_of_154(self) -> None:
        rep = evaluate_154gate_preflight(
            REPO_ROOT, dry_run_simulated=True
        )
        self.assertEqual(rep.summary["verified_gates"], 154)
        self.assertEqual(rep.summary["blocked_or_pending_gates"], 0)
        self.assertTrue(rep.all_154_gates_verified)
        self.assertTrue(rep.dry_run_rehearsal_only)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.hardware_live_attachment_authorized)
        self.assertFalse(rep.cross_model_flash_authorized)
        self.assertEqual(rep.usb_packets_transmitted, 0)
        self.assertEqual(rep.status, "VERIFIED_ALL_154_GATES_DRY_RUN_SIMULATED_BACKUP")

    def test_72_preflight_154_clean_room_test_1_mode(self) -> None:
        with mock.patch.dict(os.environ, {ENV_CLEAN_ROOM_TEST_PHASE356: "1"}):
            rep = evaluate_154gate_preflight(REPO_ROOT, dry_run_simulated=True)
            self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertEqual(rep.summary["verified_gates"], 154)

    def test_73_preflight_154_force_clean_room_env_1_mode(self) -> None:
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            rep = evaluate_154gate_preflight(REPO_ROOT)
            self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertEqual(rep.summary["verified_gates"], 151)

    def test_74_preflight_154_mocked_work_root_none_mode(self) -> None:
        env_clean = {
            k: v
            for k, v in os.environ.items()
            if k not in ("FX3_FX6_FORCE_CLEAN_ROOM", ENV_CLEAN_ROOM_TEST_PHASE356)
        }
        with mock.patch.dict(os.environ, env_clean, clear=True), mock.patch(
            "fx3_safety.realhw_pixelmap_apr_monitor_vfadjust_customhold_hdmi_reccontrol_and_154gate_guard.resolve_donor_thermal_power_paths",
            side_effect=_mock_paths_work_root_none,
        ):
            rep = evaluate_154gate_preflight(REPO_ROOT, dry_run_simulated=True)
            self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertEqual(rep.summary["verified_gates"], 154)

    def test_75_preflight_154_persistent_emmc_write_request_blocks(self) -> None:
        rep = evaluate_154gate_preflight(
            REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            request_persistent_emmc_writes=True,
        )
        self.assertFalse(rep.offline_151_gates_verified)
        self.assertFalse(rep.all_154_gates_verified)
        self.assertFalse(rep.h0_h1_trial_entry_allowed)
        self.assertIn("BLOCKED_PERSISTENT_EMMC_WRITE", rep.status)

    def test_76_preflight_154_g153_fault_blocks_master(self) -> None:
        rep = evaluate_154gate_preflight(
            REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            pixelmap_apr_monitor_vfadjust_kwargs={
                "claimed_finder_monitor_group_exists_on_fx3": True
            },
        )
        self.assertFalse(rep.all_154_gates_verified)
        self.assertFalse(rep.g153_to_g154_all_passed)
        self.assertEqual(rep.summary["g153_to_g154_verified"], 1)

    def test_77_preflight_154_g154_fault_blocks_master(self) -> None:
        rep = evaluate_154gate_preflight(
            REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            recall_custom_hold_hdmi_reccontrol_kwargs={
                "target_media_slot": MEDIA_SLOT_1_PHASE356,
                "hdmi_recording_write_requested": True,
            },
        )
        self.assertFalse(rep.all_154_gates_verified)
        self.assertFalse(rep.g153_to_g154_all_passed)
        self.assertEqual(rep.status, STATUS_BLOCKED_G154_SLOT1_HDMI_REC_MEDIA_VAULT_EROFS)

    def test_78_preflight_154_propagates_upstream_g151_g152_fault(self) -> None:
        rep = evaluate_154gate_preflight(
            REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            drive_focusbracket_shutter_efcs_nr_kwargs={
                "requested_dormant_focus_bracket": "Focus Bracket"
            },
        )
        self.assertFalse(rep.all_154_gates_verified)
        self.assertFalse(rep.g13_to_g154_all_passed)

    def test_79_preflight_154_gate_ids_g01_through_g154_ordered(self) -> None:
        rep = evaluate_154gate_preflight(
            REPO_ROOT, force_clean_room=True, dry_run_simulated=True
        )
        gate_ids = [g["gate_id"] for g in rep.gates]
        self.assertTrue(gate_ids[0].startswith("G01"))
        self.assertEqual(gate_ids[-2], G153)
        self.assertEqual(gate_ids[-1], G154)
        self.assertEqual(len(set(gate_ids)), 154)

    def test_80_preflight_154_no_raw_bytes_repr_in_report_dict(self) -> None:
        rep = evaluate_154gate_preflight(
            REPO_ROOT, force_clean_room=True, dry_run_simulated=True
        )
        dumped = json.dumps(rep.to_dict(), ensure_ascii=False)
        self.assertNotIn("b'\\x7fELF", dumped)
        self.assertNotIn('b"\\x7fELF', dumped)

    def test_81_preflight_154_report_has_master_152_and_g153_g154_dicts(self) -> None:
        rep = evaluate_154gate_preflight(REPO_ROOT, force_clean_room=True)
        d = rep.to_dict()
        self.assertIn("master_152_report", d)
        self.assertIn("g153_result", d)
        self.assertIn("g154_result", d)
        self.assertEqual(d["g153_result"]["gate_id"], G153)
        self.assertEqual(d["g154_result"]["gate_id"], G154)

    def test_82_backward_compatibility_152_150_148_146_gates(self) -> None:
        r152 = fx3_safety.evaluate_152gate_preflight(REPO_ROOT, force_clean_room=True)
        r150 = fx3_safety.evaluate_150gate_preflight(REPO_ROOT, force_clean_room=True)
        r148 = fx3_safety.evaluate_148gate_preflight(REPO_ROOT, force_clean_room=True)
        r146 = fx3_safety.evaluate_146gate_preflight(REPO_ROOT, force_clean_room=True)
        self.assertEqual(r152.summary["verified_gates"], 149)
        self.assertEqual(r150.summary["verified_gates"], 147)
        self.assertEqual(r148.summary["verified_gates"], 145)
        self.assertEqual(r146.summary["verified_gates"], 143)

    def test_83_simulate_bench_dry_run_alias_kwargs_and_wrapper_fns(self) -> None:
        r1 = evaluate_154_master_safety_gates(
            REPO_ROOT, force_clean_room=True, simulate_bench_dry_run=True
        )
        r2 = run_154_gate_preflight(
            REPO_ROOT, force_clean_room=True, dry_run_simulated_backup=True
        )
        r3 = verify_real_hardware_154gate_readiness(
            REPO_ROOT, force_clean_room=True, dry_run_simulated=True
        )
        self.assertEqual(r1.summary["verified_gates"], 154)
        self.assertEqual(r2.summary["verified_gates"], 154)
        self.assertEqual(r3.summary["verified_gates"], 154)

    def test_84_forward_compatible_dynamic_discovery_export(self) -> None:
        nums = sorted(
            int(name[9:-14])
            for name in dir(fx3_safety)
            if name.startswith("evaluate_")
            and name.endswith("gate_preflight")
            and name[9:-14].isdigit()
        )
        self.assertIn(154, nums)
        self.assertGreaterEqual(max(nums), 154)

    def test_85_fx3_safety_package_exports_and_all(self) -> None:
        for sym in (
            "evaluate_154gate_preflight",
            "evaluate_154_master_safety_gates",
            "run_154_gate_preflight",
            "verify_real_hardware_154gate_readiness",
            "evaluate_g153_pixelmap_apr_monitor_vfadjust_guard",
            "evaluate_g154_recall_custom_hold_hdmi_reccontrol_vault_guard",
            "Master154GateReport",
        ):
            self.assertTrue(hasattr(fx3_safety, sym), f"Missing export {sym}")
            self.assertIn(sym, fx3_safety.__all__)

    def test_86_master_152_override_injection_works(self) -> None:
        m152 = fx3_safety.evaluate_152gate_preflight(
            REPO_ROOT, force_clean_room=True, dry_run_simulated=True
        )
        rep = evaluate_154gate_preflight(
            REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            master_152_override=m152,
        )
        self.assertEqual(rep.summary["verified_gates"], 154)

    def test_87_cli_verify_154_gates_text_offline_and_dry_run(self) -> None:
        rc1 = safety_cli.main(["verify-154-gates", "--clean-room"])
        rc2 = safety_cli.main(["verify-154-gates", "--clean-room", "--simulate-bench-dry-run"])
        self.assertEqual(rc1, 0)
        self.assertEqual(rc2, 0)

    def test_88_cli_verify_154_gates_json_and_summary(self) -> None:
        from io import StringIO
        from contextlib import redirect_stdout

        buf = StringIO()
        with redirect_stdout(buf):
            rc = safety_cli.main(
                ["verify-154-gates", "--clean-room", "--simulate-bench-dry-run", "--json", "--summary"]
            )
        self.assertEqual(rc, 0)
        parsed = json.loads(buf.getvalue())
        self.assertEqual(parsed["summary"]["verified_gates"], 154)
        self.assertEqual(parsed["g153_status"], STATUS_VERIFIED_G153)
        self.assertEqual(parsed["g154_status"], STATUS_VERIFIED_G154)

    def test_89_cli_g153_and_g154_aliases_json_summary(self) -> None:
        from io import StringIO
        from contextlib import redirect_stdout

        for cmd in (
            ["verify-pixelmap-apr-monitor-vfadjust-guard", "--clean-room", "--json", "--summary"],
            ["verify-g153-pixelmap-apr-monitor", "--clean-room", "--json", "--summary"],
            ["verify-g153", "--clean-room"],
            ["verify-recall-custom-hold-hdmi-reccontrol-guard", "--clean-room", "--json", "--summary"],
            ["verify-g154-customhold-hdmi-reccontrol", "--clean-room", "--json", "--summary"],
            ["verify-g154", "--clean-room"],
        ):
            buf = StringIO()
            with redirect_stdout(buf):
                rc = safety_cli.main(cmd)
            self.assertEqual(rc, 0)

    def test_90_module_main_entrypoint_g153_g154_and_154(self) -> None:
        from io import StringIO
        from contextlib import redirect_stdout

        for argv in (
            ["--clean-room", "--gate", "g153", "--json", "--summary"],
            ["--clean-room", "--gate", "g154", "--json", "--summary"],
            ["--clean-room", "--gate", "154", "--simulate-bench-dry-run", "--json", "--summary"],
            ["--clean-room", "--gate", "154"],
        ):
            buf = StringIO()
            with redirect_stdout(buf):
                rc = module_main(argv)
            self.assertEqual(rc, 0)

    # -----------------------------------------------------------------------
    # 91..104: Extra Wave-67 Edge Cases & Cross-Model Negative Invariants
    # -----------------------------------------------------------------------

    def test_91_g153_silent_mode_off_plus_silent_apm_on_still_does_not_mute(self) -> None:
        st = resolve_fx3_pixelmap_and_monitor_state(
            silent_mode="Off",
            auto_pixel_mapping_silent="On",
        )
        self.assertFalse(st["power_off_pixel_mapping_shutter_muted"])

    def test_92_g153_silent_mode_on_plus_silent_apm_on_mutes_poweroff_shutter(self) -> None:
        st = resolve_fx3_pixelmap_and_monitor_state(
            silent_mode="On",
            auto_pixel_mapping_silent="On",
        )
        self.assertTrue(st["power_off_pixel_mapping_shutter_muted"])

    def test_93_g153_display_quality_defaults_standard_even_cool(self) -> None:
        st = resolve_fx3_pixelmap_and_monitor_state(body_temperature_high=False)
        self.assertEqual(st["effective_display_quality"], DISPLAY_QUALITY_STANDARD_G153)
        self.assertFalse(st["display_quality_thermal_locked_to_standard"])

    def test_94_g154_hdmi_info_display_off_manually_preserves_lcd(self) -> None:
        st = resolve_fx3_custom_hold_and_external_output_state(
            hdmi_connected=True,
            hdmi_info_display="Off",
        )
        self.assertFalse(st["builtin_lcd_blacked_out"])
        self.assertEqual(st["effective_hdmi_info_display"], "Off")

    def test_95_g154_hdmi_not_connected_does_not_black_out_lcd(self) -> None:
        st = resolve_fx3_custom_hold_and_external_output_state(
            hdmi_connected=False,
            hdmi_info_display="On",
        )
        self.assertFalse(st["builtin_lcd_blacked_out"])

    def test_96_g154_log_shooting_with_hdmi_only_allows_4k_output_resolution(self) -> None:
        st = resolve_fx3_custom_hold_and_external_output_state(
            shoot_mode=SHOOT_MODE_MOVIE_PHASE356,
            rec_media_dur_hdmi_output=REC_MEDIA_HDMI_OFF_ONLY_G154,
            output_resolution="2160p",
            log_shooting_mode="Flexible ISO",
        )
        self.assertFalse(st["output_resolution_forced_1080_by_log_or_pplut"])
        self.assertEqual(st["effective_output_resolution"], "2160p")

    def test_97_g154_raw_output_on_with_rec_media_on_does_not_force_1080(self) -> None:
        st = resolve_fx3_custom_hold_and_external_output_state(
            shoot_mode=SHOOT_MODE_MOVIE_PHASE356,
            rec_media_dur_hdmi_output=REC_MEDIA_HDMI_ON_G154,
            raw_output="On",
            output_resolution="2160p",
            log_shooting_mode="Flexible ISO",
        )
        self.assertFalse(st["output_resolution_forced_1080_by_log_or_pplut"])
        self.assertEqual(st["effective_output_resolution"], "2160p")
        self.assertEqual(st["effective_hdmi_info_display"], "Off")

    def test_98_g154_sq_forces_raw_output_off_and_tc_output_off(self) -> None:
        st = resolve_fx3_custom_hold_and_external_output_state(
            shoot_mode=SHOOT_MODE_SQ_PHASE356,
            raw_output="On",
            time_code_output="On",
        )
        self.assertEqual(st["effective_raw_output"], "Off")
        self.assertEqual(st["effective_time_code_output"], "Off")

    def test_99_g154_all_4_pplut_slots_force_1080_when_rec_media_on_and_non_raw(self) -> None:
        for pplut in ("PPLUT1", "PPLUT2", "PPLUT3", "PPLUT4"):
            st = resolve_fx3_custom_hold_and_external_output_state(
                shoot_mode=SHOOT_MODE_MOVIE_PHASE356,
                rec_media_dur_hdmi_output=REC_MEDIA_HDMI_ON_G154,
                raw_output="Off",
                picture_profile=pplut,
            )
            self.assertTrue(st["output_resolution_forced_1080_by_log_or_pplut"])
            self.assertEqual(st["effective_output_resolution"], "1080p")

    def test_100_g154_rec_control_off_passes_without_tc_output_on(self) -> None:
        r = verify_recall_custom_hold_hdmi_reccontrol_vault_guard(
            shoot_mode=SHOOT_MODE_MOVIE_PHASE356,
            time_code_output="Off",
            rec_control="Off",
            rec_control_external_recorder_compatible=False,
        )
        self.assertTrue(r.valid)
        self.assertTrue(r.rec_control_tc_prerequisite_satisfied)

    def test_101_g154_exact_11_params_have_zero_wb_or_self_timer(self) -> None:
        self.assertEqual(len(EXACT_11_RECALL_CUSTOM_HOLD_PARAMS_G154), 11)
        self.assertNotIn("white_balance", EXACT_11_RECALL_CUSTOM_HOLD_PARAMS_G154)
        self.assertNotIn("self_timer", EXACT_11_RECALL_CUSTOM_HOLD_PARAMS_G154)
        self.assertEqual(
            EXACT_11_RECALL_CUSTOM_HOLD_PARAMS_G154,
            (
                "shooting_mode",
                "aperture",
                "shutter_speed",
                "exposure_comp",
                "iso_sensitivity",
                "metering_mode",
                "drive_mode",
                "focus_mode",
                "focus_area",
                "af_on",
                "still_af_track_sens",
            ),
        )

    def test_102_cli_help_percent_escaping_clean(self) -> None:
        from io import StringIO
        from contextlib import redirect_stdout

        buf = StringIO()
        with redirect_stdout(buf):
            try:
                safety_cli.main(["--help"])
            except SystemExit as exc:
                self.assertEqual(exc.code, 0)
        help_out = buf.getvalue()
        self.assertIn("verify-154-gates", help_out)
        self.assertIn("verify-g153", help_out)
        self.assertIn("verify-g154", help_out)

    def test_103_g153_g154_no_raw_bytes_repr_in_guard_dicts(self) -> None:
        _, g153_res = evaluate_g153_pixelmap_apr_monitor_vfadjust_guard(
            repo_root=REPO_ROOT, force_clean_room=True
        )
        _, g154_res = evaluate_g154_recall_custom_hold_hdmi_reccontrol_vault_guard(
            repo_root=REPO_ROOT, force_clean_room=True
        )
        for obj in (g153_res.to_dict(), g154_res.to_dict()):
            s = json.dumps(obj, ensure_ascii=False)
            self.assertNotIn("b'\\x7fELF", s)
            self.assertNotIn('b"\\x7fELF', s)

    def test_104_g154_g153_negative_bool_invariants_remain_false(self) -> None:
        _, g153_res = evaluate_g153_pixelmap_apr_monitor_vfadjust_guard(
            repo_root=REPO_ROOT, force_clean_room=True
        )
        _, g154_res = evaluate_g154_recall_custom_hold_hdmi_reccontrol_vault_guard(
            repo_root=REPO_ROOT, force_clean_room=True
        )
        g153_d = g153_res.pixelmap_apr_monitor_vfadjust_guard
        g154_d = g154_res.recall_custom_hold_hdmi_reccontrol_guard
        self.assertFalse(g153_d["fx3_finder_monitor_group_present"])
        self.assertFalse(g153_d["fx6_abb_menu_present"])
        self.assertFalse(g153_d["fx6_vf_adjust_backlight_submenu_present"])
        self.assertFalse(g154_d["recall_custom_hold_standalone_wb_present"])
        self.assertFalse(g154_d["slot1_tier0_vault_firewall_blocked"])


if __name__ == "__main__":
    unittest.main()
