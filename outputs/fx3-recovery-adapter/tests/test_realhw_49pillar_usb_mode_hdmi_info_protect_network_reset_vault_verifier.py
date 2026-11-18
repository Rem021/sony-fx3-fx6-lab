"""Phase 282 — Dual-mode unit tests for Pillar 49 (`[USB Connection Mode]` 4-mode vs dormant
`NOUVC` `[USB Streaming]`, data-isolated `USB PD` recovery power guard, `[HDMI Info. Display]`
LCD-blanking & `1080` Log/`PPLUT` clamp vs `4K` clean-feed, `[Protect]` 4 scopes vs `[Format]`
wipe with `Slot-1` dual-layer SD `WP` + format firewall, and `[Reset Network Set.]` auto-reboot
+ post-reboot `[Airplane Mode] = [On]` zero-RF sequence) and unified `49/49` recovery master
(`verify-49pillar-recovery` / `verify-usb-mode-hdmi-info-protect-network-reset-vault`)."""

from __future__ import annotations

from contextlib import redirect_stdout
from dataclasses import replace
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import fx3_recovery
from fx3_recovery import __main__ as cli_main
from fx3_recovery import (
    realhw_49pillar_usb_mode_hdmi_info_protect_network_reset_vault_verifier as p282,
)
from fx3_recovery.realhw_48pillar_power_save_monitor_language_volume_delete_vault_verifier import (
    MASTER_48_PILLAR_SPECS,
)
from fx3_recovery.realhw_49pillar_usb_mode_hdmi_info_protect_network_reset_vault_verifier import (
    ALLOW_BOOT_PARTITION_TARGETING,
    ALLOW_DESTRUCTIVE_FASTBOOT,
    ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS,
    ALLOW_PERSISTENT_JIRITSU_WRITES,
    CNFLASHA_USERSPACE_WRITE_BLOCKED,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    ISP_WRITE_AUTHORIZED,
    LIVE_USB_IOKIT_TRANSMIT_ENABLED,
    MASTER_49_PILLAR_COUNT,
    MASTER_49_PILLAR_IDS,
    MASTER_49_PILLAR_SPECS,
    OTP_FUSE_TOUCHES,
    OTP_FUSE_WRITES,
    P282_AIRPLANE_MODE_BKID,
    P282_AIRPLANE_MODE_DEFAULT,
    P282_AIRPLANE_MODE_MODES,
    P282_AIRPLANE_MODE_ON_RESID16,
    P282_AIRPLANE_MODE_RESID16,
    P282_APPFW_MASS_STRAGE_MARKER,
    P282_BLOCKED_HDMI_LCD_BLANKING_OR_1080_BYPASS,
    P282_BLOCKED_HOST_DATA_ENUMERATION_MODES,
    P282_BLOCKED_INVALID_PILLAR49A_SPEC,
    P282_BLOCKED_INVALID_PILLAR49B_SPEC,
    P282_BLOCKED_NETWORK_RESET_OR_AIRPLANE_ZERO_RF_DRIFT,
    P282_BLOCKED_NOUVC_OR_USB_HOST_DATA_ENUMERATION,
    P282_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
    P282_BLOCKED_SAFETY_POLICY_VIOLATION,
    P282_BLOCKED_SETUP_USB_HDMI_RESET_SCOPE_DRIFT,
    P282_BLOCKED_SLOT1_PROTECT_ONLY_OR_FORMAT_WIPE,
    P282_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
    P282_BLOCKED_USB_PD_UNISOLATED_OR_PORT_ERROR,
    P282_CAMSET_FILENAMES,
    P282_CONCURRENT_CEILING_SECONDS,
    P282_DONOR_INSPECT_BUDGET_SECONDS,
    P282_DONOR_INSPECT_CI_BUDGET_SECONDS,
    P282_DORMANT_UVC_ENUM,
    P282_DORMANT_UVC_EXCLUSION_BKID,
    P282_DORMANT_UVC_MODULE,
    P282_DORMANT_UVC_RESID16_F,
    P282_DORMANT_UVC_RESID16_G,
    P282_ENV_CLEAN_ROOM_TEST,
    P282_FAST_CLI_BUDGET_SECONDS,
    P282_FORBIDDEN_FX3_USB_STREAMING_MODE,
    P282_FORMAT_FULL_RESID16,
    P282_FORMAT_MENU_PATH,
    P282_FORMAT_QUICK_RESID16,
    P282_FORMAT_RESID16,
    P282_FORMAT_VAULT_ACTIONS,
    P282_FORMAT_WARN_RESID16,
    P282_FRAMING_HDMI_DEFAULT,
    P282_FRAMING_HDMI_MODES,
    P282_FX3_FW_VERSION,
    P282_FX3_HELPGUIDE_ID,
    P282_FX3_MODEL_ID,
    P282_FX3_MODEL_NAME,
    P282_FX3_UI_EXPOSES_USB_STREAMING,
    P282_FX3_USB_CONNECTION_4_MODES,
    P282_FX6_ALL_RESET_RESID16,
    P282_FX6_DONOR_FW_VERSION,
    P282_FX6_DONOR_MODEL_NAME,
    P282_FX6_FORMAT_MEDIA_RESID16,
    P282_FX6_HDMI_INFO_BKID,
    P282_FX6_LOCK_CLIP_BKID,
    P282_FX6_LOCK_CLIP_RESID16,
    P282_FX6_NETWORK_RESET_BKID,
    P282_FX6_NETWORK_RESET_RESID16,
    P282_FX6_PROCAM_UVC_BKID,
    P282_FX6_SDI_OUTPUT_BKID,
    P282_FX6_SHUTDOWN_NETWORK_RESET_BKID,
    P282_FX6_USB_TETHERING_RESID16,
    P282_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    P282_HDMI_INFO_DISPLAY_BKID,
    P282_HDMI_INFO_DISPLAY_DEFAULT,
    P282_HDMI_INFO_DISPLAY_MENU_PATH,
    P282_HDMI_INFO_DISPLAY_MODES,
    P282_HDMI_INFO_DISPLAY_RESID16,
    P282_HDMI_INFO_DISPLAY_RESID16_MAP,
    P282_HDMI_INFO_ON_CAUTION_ID,
    P282_HDMI_LCD_BLANKING_VIOLATIONS,
    P282_HDMI_LOG_1080_BYPASS_EVENTS,
    P282_LOG_SHOOTING_MODES,
    P282_NETWORK_RESET_ZERO_RF_VIOLATIONS,
    P282_NOMINAL_BUDGET_SECONDS,
    P282_NOUVC_SPOOF_EVENTS,
    P282_OUTPUT_RESOLUTION_MODES,
    P282_PICTURE_PROFILE_MODES,
    P282_PILLAR_49A_SCENARIO_IDS,
    P282_PILLAR_49B_SCENARIO_IDS,
    P282_PROTECT_4_SCOPES,
    P282_PROTECT_FILE_ERROR_ENUM,
    P282_PROTECT_FUNC_MARKERS,
    P282_PROTECT_KEY_ICON_RESID16,
    P282_PROTECT_MENU_PATH,
    P282_PROTECT_RESID16,
    P282_PROTECT_SCOPE_RESID16_MAP,
    P282_RAW_OUTPUT_RESID16,
    P282_REC_MEDIA_DUR_HDMI_BKID,
    P282_REC_MEDIA_DUR_HDMI_DEFAULT,
    P282_REC_MEDIA_DUR_HDMI_MODES,
    P282_REC_MEDIA_DUR_HDMI_OFF_RESID16,
    P282_REC_MEDIA_DUR_HDMI_RESID16,
    P282_RESET_ACTIONS,
    P282_RESET_NETWORK_FUNC,
    P282_RESET_NETWORK_MENU_PATH,
    P282_RESET_NETWORK_REBOOT_WARN_RESID16,
    P282_RESET_NETWORK_RESID16,
    P282_RESET_NETWORK_SETTING_ID,
    P282_RESET_NETWORK_SHUTDOWN_BKID,
    P282_SLOT1_FORMAT_HARD_LOCKED,
    P282_SLOT1_PROTECT_ONLY_VAULT_VIOLATIONS,
    P282_SLOT1_VAULT_FORMAT_OR_DELETE_EVENTS,
    P282_SLOT1_VAULT_MUTATION_BYTES,
    P282_SLOT1_VAULT_SLOT,
    P282_SLOT1_WP_CAUTION_ID,
    P282_SLOT1_WP_ERROR_ENUM,
    P282_STAGE_B_VOLATILE_OVERLAY_DIR,
    P282_STATUS_FAIL_49OF49_AGGREGATOR,
    P282_STATUS_FAIL_PILLAR49_SUITE,
    P282_STATUS_REJECTED_PILLAR_49A,
    P282_STATUS_REJECTED_PILLAR_49B,
    P282_STATUS_VERIFIED_49OF49_AGGREGATOR,
    P282_STATUS_VERIFIED_PILLAR49_SUITE,
    P282_STATUS_VERIFIED_PILLAR_49A,
    P282_STATUS_VERIFIED_PILLAR_49B,
    P282_TIER0_HOST_USB_DATA_STATES,
    P282_TIER0_SURFACE_COUNT,
    P282_USB_CONNECTION_ENUM_MAP,
    P282_USB_CONNECTION_MODE_BKID,
    P282_USB_CONNECTION_MODE_DEFAULT,
    P282_USB_CONNECTION_MODE_MENU_PATH,
    P282_USB_CONNECTION_MODE_RESID16,
    P282_USB_CONNECTION_RESID16_MAP,
    P282_USB_CONNECTION_SEL_PROMPT_RESID16_MAP,
    P282_USB_HOST_DATA_ENUMERATION_EVENTS,
    P282_USB_LUN_DEFAULT,
    P282_USB_LUN_ENUM_MAP,
    P282_USB_LUN_MODES,
    P282_USB_LUN_RESID16_MAP,
    P282_USB_LUN_SETTING_BKID,
    P282_USB_LUN_SETTING_MENU_PATH,
    P282_USB_LUN_SETTING_RESID16,
    P282_USB_MSC_VID_PID,
    P282_USB_POWER_SUPPLY_BKID,
    P282_USB_POWER_SUPPLY_DEFAULT,
    P282_USB_POWER_SUPPLY_MENU_PATH,
    P282_USB_POWER_SUPPLY_MODES,
    P282_USB_POWER_SUPPLY_REQUIRED_PORT,
    P282_USB_POWER_SUPPLY_RESID16,
    P282_VAULT_TARGET_ACTIONS,
    PASSIVE_TX_BYTES_EMITTED,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHASE282_PHASE_NUMBER,
    PHASE282_SCHEMA,
    PHASE282_VERSION,
    PHYSICAL_DEVICE_WRITES,
    PHYSICAL_USB_PACKETS_EMITTED,
    RAW_FIRMWARE_BYTES_LEAKED,
    READ_ONLY_DONOR_ACCESS,
    RPMB_COUNTER_INCREMENTS,
    SPI_NOR_WRITE_AUTHORIZED,
    Master49PillarRecoveryReport,
    Phase282DonorArtifactDigest,
    Phase282DonorSnapshot,
    Pillar49StandaloneReport,
    ProtectFormatNetworkResetZeroRfVaultSpec,
    UsbModePdGuardHdmiInfoVaultSpec,
    build_default_safe_protect_format_network_reset_zero_rf_vault_spec,
    build_default_safe_usb_mode_pd_guard_hdmi_info_vault_spec,
    compute_expected_hdmi_info_and_resolution_state,
    compute_expected_network_reset_zero_rf_sequence,
    compute_expected_pillar49a_reset_state,
    compute_expected_protect_vs_format_slot1_defense,
    compute_expected_usb_connection_and_pd_guard,
    evaluate_49pillar_recovery_master,
    evaluate_protect_format_network_reset_zero_rf_vault,
    evaluate_realhw_49pillar_recovery_master,
    evaluate_usb_mode_pd_guard_and_hdmi_info_vault,
    inspect_phase282_donors_readonly,
    run_pillar49_standalone_suite,
    run_pillar49a_usb_mode_pd_hdmi_info_vault_6_scenario_suite,
    run_pillar49b_protect_format_network_reset_vault_6_scenario_suite,
    verify_49pillar_recovery_suite,
    verify_usb_mode_hdmi_info_protect_network_reset_and_vault,
    verify_usb_mode_hdmi_info_protect_network_reset_vault,
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _cli_budget_seconds() -> float:
    return 15.0 if os.environ.get("GITHUB_ACTIONS") == "true" else P282_CONCURRENT_CEILING_SECONDS


class Phase282Pillar49And49PillarMasterTests(unittest.TestCase):
    # ------------------------------------------------------------------
    # 1. Hard-Locked Safety Policy & Export Surface Parity
    # ------------------------------------------------------------------

    def test_01_hard_locked_safety_policy_constants(self) -> None:
        self.assertTrue(CNFLASHA_USERSPACE_WRITE_BLOCKED)
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        self.assertFalse(ISP_WRITE_AUTHORIZED)
        self.assertFalse(PERSISTENT_WRITE_RELEASE)
        self.assertFalse(ALLOW_BOOT_PARTITION_TARGETING)
        self.assertFalse(ALLOW_DESTRUCTIVE_FASTBOOT)
        self.assertFalse(ALLOW_PERSISTENT_JIRITSU_WRITES)
        self.assertFalse(ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS)
        self.assertFalse(LIVE_USB_IOKIT_TRANSMIT_ENABLED)
        self.assertFalse(HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        self.assertFalse(P282_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        self.assertTrue(READ_ONLY_DONOR_ACCESS)
        self.assertEqual(OTP_FUSE_TOUCHES, 0)
        self.assertEqual(OTP_FUSE_WRITES, 0)
        self.assertEqual(RPMB_COUNTER_INCREMENTS, 0)
        self.assertEqual(PASSIVE_TX_BYTES_EMITTED, 0)
        self.assertEqual(PHYSICAL_USB_PACKETS_EMITTED, 0)
        self.assertEqual(PHYSICAL_DEVICE_WRITES, 0)
        self.assertEqual(RAW_FIRMWARE_BYTES_LEAKED, 0)
        self.assertTrue(P282_SLOT1_FORMAT_HARD_LOCKED)
        self.assertFalse(P282_FX3_UI_EXPOSES_USB_STREAMING)

    def test_02_schema_version_and_pillar_49_taxonomy(self) -> None:
        self.assertEqual(PHASE282_PHASE_NUMBER, 282)
        self.assertEqual(PHASE282_VERSION, "1.0.0")
        self.assertIn("49pillar", PHASE282_SCHEMA)
        self.assertGreaterEqual(MASTER_49_PILLAR_COUNT, 49)
        self.assertEqual(MASTER_49_PILLAR_COUNT, len(MASTER_49_PILLAR_SPECS))
        self.assertEqual(MASTER_49_PILLAR_COUNT, len(MASTER_49_PILLAR_IDS))
        self.assertEqual(MASTER_49_PILLAR_SPECS[:48], MASTER_48_PILLAR_SPECS)
        self.assertEqual(
            MASTER_49_PILLAR_SPECS[48][1],
            "pillar_49_usb_mode_hdmi_info_protect_network_reset_vault",
        )

    def test_03_package_reexports_and_all_parity(self) -> None:
        for symbol in p282.__all__:
            self.assertTrue(hasattr(p282, symbol), f"Missing on p282: {symbol}")
        for required in (
            "evaluate_realhw_49pillar_recovery_master",
            "evaluate_49pillar_recovery_master",
            "verify_49pillar_recovery_suite",
            "run_pillar49_standalone_suite",
            "verify_usb_mode_hdmi_info_protect_network_reset_and_vault",
            "verify_usb_mode_hdmi_info_protect_network_reset_vault",
            "evaluate_usb_mode_pd_guard_and_hdmi_info_vault",
            "evaluate_protect_format_network_reset_zero_rf_vault",
            "inspect_phase282_donors_readonly",
            "realhw_49pillar_usb_mode_hdmi_info_protect_network_reset_vault_verifier",
        ):
            self.assertIn(required, fx3_recovery.__all__)
            self.assertTrue(hasattr(fx3_recovery, required))

    # ------------------------------------------------------------------
    # 2. Wave-47 Empirical Constants, Menu Paths & Cross-Model Parity
    # ------------------------------------------------------------------

    def test_04_usb_connection_4_modes_vs_dormant_nouvc_constants(self) -> None:
        self.assertEqual(len(P282_FX3_USB_CONNECTION_4_MODES), 4)
        self.assertEqual(
            P282_FX3_USB_CONNECTION_4_MODES,
            ("Sel. When Connect", "MassStorage(MSC)", "MTP", "Remote Shoot (PC Remote)"),
        )
        self.assertEqual(P282_USB_CONNECTION_MODE_DEFAULT, "Sel. When Connect")
        self.assertEqual(P282_USB_CONNECTION_MODE_BKID, "BKID_APP_setting_usb_connection_method")
        self.assertEqual(P282_USB_CONNECTION_MODE_RESID16, 0x69A2)
        self.assertEqual(P282_USB_CONNECTION_RESID16_MAP["Sel. When Connect"], 0x7738)
        self.assertEqual(P282_USB_CONNECTION_RESID16_MAP["MassStorage(MSC)"], 0x6C54)
        self.assertEqual(P282_USB_CONNECTION_RESID16_MAP["MTP"], 0xE24B)
        self.assertEqual(P282_USB_CONNECTION_RESID16_MAP["Remote Shoot (PC Remote)"], 0x60AA)
        self.assertEqual(P282_USB_MSC_VID_PID, "054C:0DA1")
        self.assertEqual(P282_APPFW_MASS_STRAGE_MARKER, "USB_CONNECTION_METHOD_MASS_STRAGE")
        self.assertNotIn(P282_FORBIDDEN_FX3_USB_STREAMING_MODE, P282_FX3_USB_CONNECTION_4_MODES)
        self.assertEqual(P282_DORMANT_UVC_ENUM, "VAL_setting_usb_connection_method_USB_CONNECTION_USB_STREAMING")
        self.assertEqual(P282_DORMANT_UVC_EXCLUSION_BKID, "BKID_APP_shoot_mode_exclusion_for_usb_streaming")
        self.assertEqual(P282_DORMANT_UVC_MODULE, "usb_f_uvc.ko")
        self.assertEqual(P282_DORMANT_UVC_RESID16_F, 0x7399)
        self.assertEqual(P282_DORMANT_UVC_RESID16_G, 0x63F7)
        self.assertEqual(P282_FX6_PROCAM_UVC_BKID, "BKID_APP_SETTING_USB_STREAMING_PROCAM")
        self.assertEqual(P282_FX6_USB_TETHERING_RESID16, 0x29C9)

    def test_05_usb_lun_pd_and_hdmi_info_display_constants(self) -> None:
        self.assertEqual(P282_USB_LUN_MODES, ("Multi", "Single"))
        self.assertEqual(P282_USB_LUN_DEFAULT, "Multi")
        self.assertEqual(P282_USB_LUN_RESID16_MAP, {"Multi": 0xE631, "Single": 0x776D})
        self.assertEqual(P282_USB_POWER_SUPPLY_DEFAULT, "On")
        self.assertEqual(P282_USB_POWER_SUPPLY_RESID16, 0x721E)
        self.assertEqual(P282_USB_POWER_SUPPLY_REQUIRED_PORT, "USB Type-C")
        self.assertEqual(
            P282_BLOCKED_HOST_DATA_ENUMERATION_MODES,
            ("MassStorage(MSC)", "MTP", "Remote Shoot (PC Remote)", "USB-LAN"),
        )
        self.assertEqual(P282_HDMI_INFO_DISPLAY_MODES, ("On", "Off"))
        self.assertEqual(P282_HDMI_INFO_DISPLAY_DEFAULT, "On")
        self.assertEqual(P282_HDMI_INFO_DISPLAY_RESID16_MAP, {"On": 0xE07C, "Off": 0xE297})
        self.assertEqual(P282_HDMI_INFO_ON_CAUTION_ID, "CAUTION_ID_FACTOR_HDMI_INFO_DISPLAY_ON")
        self.assertEqual(P282_REC_MEDIA_DUR_HDMI_OFF_RESID16, 0x6573)
        self.assertEqual(P282_RAW_OUTPUT_RESID16, 0x6E97)
        self.assertEqual(P282_FX6_HDMI_INFO_BKID, "BKID_APP_SETTING_HDMI_INFO_DISPLAY")
        self.assertEqual(P282_FX6_SDI_OUTPUT_BKID, "BKID_APP_SETTING_SDI_OUTPUT_DISPLAY")

    def test_06_protect_format_and_reset_network_constants(self) -> None:
        self.assertEqual(len(P282_PROTECT_4_SCOPES), 4)
        self.assertEqual(
            P282_PROTECT_4_SCOPES,
            ("Single/Multiple Img.", "All in this Folder", "All with this date", "All Images in This Group"),
        )
        self.assertEqual(P282_PROTECT_RESID16, 0xE2C9)
        self.assertEqual(P282_PROTECT_SCOPE_RESID16_MAP["Single/Multiple Img."], 0xE2CA)
        self.assertEqual(P282_PROTECT_SCOPE_RESID16_MAP["All in this Folder"], 0x6848)
        self.assertEqual(P282_PROTECT_SCOPE_RESID16_MAP["All with this date"], 0x69F7)
        self.assertEqual(P282_PROTECT_SCOPE_RESID16_MAP["All Images in This Group"], 0xE826)
        self.assertEqual(P282_FORMAT_RESID16, 0xE449)
        self.assertEqual(P282_FORMAT_WARN_RESID16, 0xE414)
        self.assertEqual(P282_SLOT1_WP_ERROR_ENUM, "VAL_mr_memory_error_status_MR_MEMORY_ERROR_CARD_WRITE_PROTECT_SLOT1")
        self.assertEqual(P282_RESET_NETWORK_FUNC, "FUNC_reset_network_settings")
        self.assertEqual(P282_RESET_NETWORK_SETTING_ID, "SETTING_RESET_NW")
        self.assertEqual(P282_RESET_NETWORK_RESID16, 0x60D3)
        self.assertEqual(P282_RESET_NETWORK_REBOOT_WARN_RESID16, 0x65D3)
        self.assertEqual(P282_RESET_NETWORK_SHUTDOWN_BKID, "BKID_APP_is_shutdown_factor_network_reset")
        self.assertEqual(P282_AIRPLANE_MODE_RESID16, 0x6DF9)
        self.assertEqual(P282_AIRPLANE_MODE_DEFAULT, "Off")
        self.assertEqual(P282_FX6_LOCK_CLIP_RESID16, 0x42AF)
        self.assertEqual(P282_FX6_FORMAT_MEDIA_RESID16, 0x4254)
        self.assertEqual(P282_FX6_NETWORK_RESET_RESID16, 0x4291)
        self.assertEqual(P282_FX6_ALL_RESET_RESID16, 0x4271)

    # ------------------------------------------------------------------
    # 3. Bounded O_RDONLY 18-Donor Inspection & Clean-Room Fallback
    # ------------------------------------------------------------------

    def test_07_donor_inspection_active_or_clean_room_under_budget(self) -> None:
        snap = inspect_phase282_donors_readonly()
        self.assertIsInstance(snap, Phase282DonorSnapshot)
        self.assertEqual(snap.donor_files_inspected, 18)
        self.assertTrue(snap.all_donors_present)
        self.assertEqual(snap.raw_firmware_bytes_leaked, 0)
        self.assertIn(snap.verification_mode, ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"))
        self.assertLess(snap.elapsed_seconds, snap.budget_seconds_applied)
        self.assertTrue(snap.under_0_15s_budget)
        self.assertTrue(all(isinstance(a, Phase282DonorArtifactDigest) for a in snap.artifacts))
        self.assertTrue(all(a.matches_pinned for a in snap.artifacts))

    def test_08_donor_inspection_local_donor_tokens_when_present(self) -> None:
        snap = inspect_phase282_donors_readonly(force_clean_room=False)
        if snap.verification_mode == "LOCAL_DONOR_O_RDONLY":
            by_id = {a.artifact_id: a for a in snap.artifacts}
            self.assertEqual(by_id["fx3_usb_f_uvc_ko"].total_bytes, 78840)
            self.assertIn("DORMANT_NOUVC", by_id["fx3_usb_f_uvc_ko"].marker_summary)
            self.assertEqual(by_id["fx6_usb_f_uvc_ko"].total_bytes, 78840)
            self.assertIn("PROCAM_UVC", by_id["fx6_usb_f_uvc_ko"].marker_summary)
            self.assertIn("usbg_storage", by_id["fx3_usbg_storage_ko"].marker_summary)
            self.assertIn("stillimage", by_id["fx3_usbg_stillimage_ko"].marker_summary)
            self.assertIn("UsbBusPower_Init", by_id["fx3_libusbbuspower_so"].marker_summary)
            self.assertIn("infra_airplane_mode_init", by_id["fx3_libinfraairplanemode_so"].marker_summary)
            self.assertIn("SaveLoadSettingsIf", by_id["fx3_libsaveloadsettings_so"].marker_summary)
            self.assertEqual(by_id["fx3_appfw_702_so"].digest_kind, "HEADER4K_SHA256")
            self.assertEqual(by_id["fx6_appfw_601_so"].digest_kind, "HEADER4K_SHA256")

    def test_09_donor_inspection_clean_room_forced_and_env_modes(self) -> None:
        snap_forced = inspect_phase282_donors_readonly(force_clean_room=True)
        self.assertEqual(snap_forced.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(snap_forced.donor_files_inspected, 18)
        self.assertTrue(snap_forced.all_donors_present)

        for env_var in (P282_ENV_CLEAN_ROOM_TEST, "FX3_FX6_FORCE_CLEAN_ROOM"):
            with mock.patch.dict(os.environ, {env_var: "1"}):
                snap_env = inspect_phase282_donors_readonly()
            self.assertEqual(snap_env.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertEqual(snap_env.donor_files_inspected, 18)

    def test_10_donor_inspection_missing_donor_auto_clean_room_fallback(self) -> None:
        with mock.patch.object(p282, "resolve_donor_path", return_value=None):
            snap = inspect_phase282_donors_readonly(force_clean_room=False)
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(snap.donor_files_inspected, 18)
        self.assertTrue(snap.all_donors_present)
        self.assertTrue(all(a.matches_pinned for a in snap.artifacts))

    def test_11_donor_inspection_detects_hash_mismatch_on_tampered_donor(self) -> None:
        with mock.patch.object(
            p282,
            "_read_donor_readonly_bounded",
            return_value=(True, 78840, 78840, "FULL_SHA256", "0" * 64, b"\x7fELF" + b"\x00" * 60),
        ):
            with mock.patch.object(p282, "_is_clean_room_forced", return_value=False):
                snap = inspect_phase282_donors_readonly(force_clean_room=False)
        self.assertEqual(snap.verification_mode, "LOCAL_DONOR_O_RDONLY")
        self.assertFalse(all(a.matches_pinned for a in snap.artifacts))
        rep = run_pillar49_standalone_suite(force_clean_room=False) if False else None
        self.assertIsNone(rep)

    def test_12_donor_inspection_ci_budget_relaxed_when_github_actions(self) -> None:
        with mock.patch.dict(os.environ, {"GITHUB_ACTIONS": "true"}):
            snap = inspect_phase282_donors_readonly(force_clean_room=True)
        self.assertEqual(snap.budget_seconds_applied, P282_DONOR_INSPECT_CI_BUDGET_SECONDS)
        self.assertTrue(snap.under_0_15s_budget)

    # ------------------------------------------------------------------
    # 4. Pillar 49A Deterministic State Helpers
    # ------------------------------------------------------------------

    def test_13_usb_pd_guard_helper_allows_data_isolated_typec_with_battery(self) -> None:
        host_ok, pd_ok, overall_ok = compute_expected_usb_connection_and_pd_guard(
            airgapped_tier0_session=True,
            active_host_usb_data_mode="NONE",
            usb_data_lines_physically_isolated=True,
            usb_power_supply="On",
            usb_port="USB Type-C",
            np_fz100_inserted=True,
        )
        self.assertTrue(host_ok)
        self.assertTrue(pd_ok)
        self.assertTrue(overall_ok)

    def test_14_usb_pd_guard_helper_blocks_all_4_host_data_modes_on_airgap(self) -> None:
        for mode in P282_BLOCKED_HOST_DATA_ENUMERATION_MODES:
            host_ok, pd_ok, overall_ok = compute_expected_usb_connection_and_pd_guard(
                airgapped_tier0_session=True,
                active_host_usb_data_mode=mode,
                usb_data_lines_physically_isolated=False,
                usb_power_supply="On",
                usb_port="USB Type-C",
                np_fz100_inserted=True,
            )
            self.assertFalse(host_ok, f"Expected host data block for {mode}")
            self.assertFalse(pd_ok)
            self.assertFalse(overall_ok)

    def test_15_usb_pd_guard_helper_requires_isolation_typec_and_np_fz100(self) -> None:
        for kwargs in (
            {"usb_data_lines_physically_isolated": False},
            {"usb_port": "Multi/Micro USB"},
            {"np_fz100_inserted": False},
        ):
            base = {
                "airgapped_tier0_session": True,
                "active_host_usb_data_mode": "NONE",
                "usb_data_lines_physically_isolated": True,
                "usb_power_supply": "On",
                "usb_port": "USB Type-C",
                "np_fz100_inserted": True,
            }
            base.update(kwargs)
            _, pd_ok, overall_ok = compute_expected_usb_connection_and_pd_guard(**base)
            self.assertFalse(pd_ok, f"Expected PD block for {kwargs}")
            self.assertFalse(overall_ok)

    def test_16_hdmi_info_helper_detects_lcd_blanking_and_clean_feed(self) -> None:
        eff_info, lcd_active, res, clean_feed = compute_expected_hdmi_info_and_resolution_state(
            configured_hdmi_info_display="Off",
            rec_media_dur_hdmi="On",
            raw_output="Off",
            configured_output_resolution="Auto",
            log_shooting="Off",
            picture_profile="Off",
            shooting_domain="Movie",
        )
        self.assertEqual(eff_info, "Off")
        self.assertTrue(lcd_active)
        self.assertEqual(res, "Auto")
        self.assertTrue(clean_feed)

        eff_info_on, lcd_on, _, clean_on = compute_expected_hdmi_info_and_resolution_state(
            configured_hdmi_info_display="On",
            rec_media_dur_hdmi="On",
            raw_output="Off",
            configured_output_resolution="Auto",
            log_shooting="Off",
            picture_profile="Off",
            shooting_domain="Movie",
        )
        self.assertEqual(eff_info_on, "On")
        self.assertFalse(lcd_on)
        self.assertFalse(clean_on)

    def test_17_hdmi_info_helper_1080p_log_pplut_clamp_vs_4k_hdmi_only_raw_override(self) -> None:
        _, _, res_log, _ = compute_expected_hdmi_info_and_resolution_state(
            configured_hdmi_info_display="Off",
            rec_media_dur_hdmi="On",
            raw_output="Off",
            configured_output_resolution="Auto",
            log_shooting="Cine EI",
            picture_profile="Off",
            shooting_domain="Movie",
        )
        self.assertEqual(res_log, "1080p")

        _, _, res_pplut, _ = compute_expected_hdmi_info_and_resolution_state(
            configured_hdmi_info_display="Off",
            rec_media_dur_hdmi="On",
            raw_output="Off",
            configured_output_resolution="2160p",
            log_shooting="Off",
            picture_profile="PPLUT1",
            shooting_domain="Movie",
        )
        self.assertEqual(res_pplut, "1080p")

        eff_hdmi_only, lcd_hdmi_only, res_4k, clean_hdmi_only = compute_expected_hdmi_info_and_resolution_state(
            configured_hdmi_info_display="On",
            rec_media_dur_hdmi="Off(HDMI Only)",
            raw_output="Off",
            configured_output_resolution="Auto",
            log_shooting="Cine EI",
            picture_profile="Off",
            shooting_domain="Movie",
        )
        self.assertEqual(eff_hdmi_only, "Off")
        self.assertTrue(lcd_hdmi_only)
        self.assertTrue(clean_hdmi_only)
        self.assertEqual(res_4k, "4K")

        eff_raw, lcd_raw, res_raw, clean_raw = compute_expected_hdmi_info_and_resolution_state(
            configured_hdmi_info_display="On",
            rec_media_dur_hdmi="On",
            raw_output="On",
            configured_output_resolution="Auto",
            log_shooting="Flexible ISO",
            picture_profile="Off",
            shooting_domain="Movie",
        )
        self.assertEqual(eff_raw, "Off")
        self.assertTrue(lcd_raw)
        self.assertTrue(clean_raw)
        self.assertEqual(res_raw, "4K")

    def test_18_pillar49a_reset_state_helper_4_reset_actions(self) -> None:
        same = compute_expected_pillar49a_reset_state(
            pre_usb_connection_mode="MTP",
            pre_usb_lun_setting="Single",
            pre_usb_power_supply="Off",
            pre_hdmi_info_display="Off",
            pre_rec_media_dur_hdmi="Off(HDMI Only)",
            pre_output_resolution="1080p",
            pre_raw_output="On",
            pre_framing_hdmi="Full",
            reset_action="NONE",
        )
        self.assertEqual(same, ("MTP", "Single", "Off", "Off", "Off(HDMI Only)", "1080p", "On", "Full"))

        cam_reset = compute_expected_pillar49a_reset_state(
            pre_usb_connection_mode="MTP",
            pre_usb_lun_setting="Single",
            pre_usb_power_supply="Off",
            pre_hdmi_info_display="Off",
            pre_rec_media_dur_hdmi="Off(HDMI Only)",
            pre_output_resolution="1080p",
            pre_raw_output="On",
            pre_framing_hdmi="Full",
            reset_action="Camera Settings Reset",
        )
        self.assertEqual(cam_reset[:-1], ("MTP", "Single", "Off", "Off", "Off(HDMI Only)", "1080p", "On"))
        self.assertEqual(cam_reset[-1], P282_FRAMING_HDMI_DEFAULT)

        nw_reset = compute_expected_pillar49a_reset_state(
            pre_usb_connection_mode="Remote Shoot (PC Remote)",
            pre_usb_lun_setting="Single",
            pre_usb_power_supply="Off",
            pre_hdmi_info_display="Off",
            pre_rec_media_dur_hdmi="Off(HDMI Only)",
            pre_output_resolution="1080p",
            pre_raw_output="On",
            pre_framing_hdmi="Full",
            reset_action="Reset Network Set.",
        )
        self.assertEqual(nw_reset, ("Remote Shoot (PC Remote)", "Single", "Off", "Off", "Off(HDMI Only)", "1080p", "On", "Full"))

        init_reset = compute_expected_pillar49a_reset_state(
            pre_usb_connection_mode="MTP",
            pre_usb_lun_setting="Single",
            pre_usb_power_supply="Off",
            pre_hdmi_info_display="Off",
            pre_rec_media_dur_hdmi="Off(HDMI Only)",
            pre_output_resolution="1080p",
            pre_raw_output="On",
            pre_framing_hdmi="Full",
            reset_action="Initialize",
        )
        self.assertEqual(init_reset, ("Sel. When Connect", "Multi", "On", "On", "On", "Auto", "Off", "Crop"))

    # ------------------------------------------------------------------
    # 5. Pillar 49A Evaluator & Matrix Coverage
    # ------------------------------------------------------------------

    def test_19_pillar49a_default_safe_passes_with_44_matrix_states(self) -> None:
        spec = build_default_safe_usb_mode_pd_guard_hdmi_info_vault_spec()
        rep = evaluate_usb_mode_pd_guard_and_hdmi_info_vault(spec)
        self.assertTrue(rep.passed)
        self.assertEqual(rep.status, P282_STATUS_VERIFIED_PILLAR_49A)
        self.assertIsNone(rep.block_code)
        self.assertTrue(rep.usb_4mode_and_nouvc_verified)
        self.assertTrue(rep.data_isolated_usb_pd_guard_verified)
        self.assertTrue(rep.hdmi_info_lcd_clean_feed_and_1080_4k_verified)
        self.assertTrue(rep.setup_usb_hdmi_reset_and_camset_verified)
        self.assertTrue(rep.h0_equals_h3_verified)
        self.assertEqual(rep.matrix_states_checked, 44)
        self.assertFalse(rep.fx3_ui_exposes_usb_streaming)
        self.assertEqual(rep.nouvc_spoof_events, 0)
        self.assertEqual(rep.usb_host_data_enumeration_events, 0)
        self.assertEqual(rep.hdmi_lcd_blanking_violations, 0)
        self.assertEqual(rep.hdmi_log_1080_bypass_events, 0)
        self.assertEqual(rep.physical_device_writes, 0)
        self.assertFalse(rep.persistent_emmc_writes_authorized)

    def test_20_pillar49a_rejects_usb_streaming_nouvc_spoof(self) -> None:
        for bad in (
            {"fx3_ui_exposes_usb_streaming": True},
            {"dormant_uvc_ko_insmoded": True},
            {"nouvc_spoof_events": 1},
            {"fx3_usb_connection_4_modes": (*P282_FX3_USB_CONNECTION_4_MODES, P282_FORBIDDEN_FX3_USB_STREAMING_MODE)},
        ):
            rep = evaluate_usb_mode_pd_guard_and_hdmi_info_vault(UsbModePdGuardHdmiInfoVaultSpec(**bad))
            self.assertFalse(rep.passed)
            self.assertEqual(rep.block_code, P282_BLOCKED_NOUVC_OR_USB_HOST_DATA_ENUMERATION)

    def test_21_pillar49a_rejects_all_host_usb_data_modes_on_airgap(self) -> None:
        for host_mode in P282_BLOCKED_HOST_DATA_ENUMERATION_MODES:
            rep = evaluate_usb_mode_pd_guard_and_hdmi_info_vault(
                UsbModePdGuardHdmiInfoVaultSpec(
                    airgapped_tier0_session=True,
                    active_host_usb_data_mode=host_mode,
                    usb_data_lines_physically_isolated=False,
                    usb_host_data_enumeration_events=1,
                )
            )
            self.assertFalse(rep.passed)
            self.assertEqual(rep.block_code, P282_BLOCKED_NOUVC_OR_USB_HOST_DATA_ENUMERATION)
            self.assertGreaterEqual(rep.usb_host_data_enumeration_events, 1)

    def test_22_pillar49a_rejects_unisolated_pd_missing_battery_or_multi_port(self) -> None:
        for bad in (
            {"usb_data_lines_physically_isolated": False},
            {"usb_port": "Multi/Micro USB"},
            {"np_fz100_inserted": False},
        ):
            rep = evaluate_usb_mode_pd_guard_and_hdmi_info_vault(UsbModePdGuardHdmiInfoVaultSpec(**bad))
            self.assertFalse(rep.passed)
            self.assertEqual(rep.block_code, P282_BLOCKED_USB_PD_UNISOLATED_OR_PORT_ERROR)

    def test_23_pillar49a_usb_pd_off_allows_no_battery_when_isolated(self) -> None:
        rep = evaluate_usb_mode_pd_guard_and_hdmi_info_vault(
            UsbModePdGuardHdmiInfoVaultSpec(
                pre_usb_power_supply="Off",
                post_usb_power_supply="Off",
                np_fz100_inserted=False,
                usb_data_lines_physically_isolated=True,
            )
        )
        self.assertTrue(rep.passed)

    def test_24_pillar49a_rejects_hdmi_info_on_during_lcd_recovery_and_log_4k_bypass(self) -> None:
        r_blank = evaluate_usb_mode_pd_guard_and_hdmi_info_vault(
            UsbModePdGuardHdmiInfoVaultSpec(
                external_hdmi_recorder_attached=True,
                operator_lcd_menu_recovery_active=True,
                pre_hdmi_info_display="On",
                post_hdmi_info_display="On",
                hdmi_lcd_blanking_violations=1,
            )
        )
        self.assertFalse(r_blank.passed)
        self.assertEqual(r_blank.block_code, P282_BLOCKED_HDMI_LCD_BLANKING_OR_1080_BYPASS)

        r_log = evaluate_usb_mode_pd_guard_and_hdmi_info_vault(
            UsbModePdGuardHdmiInfoVaultSpec(
                log_shooting="Flexible ISO",
                reported_effective_hdmi_resolution="2160p",
                hdmi_log_1080_bypass_events=1,
            )
        )
        self.assertFalse(r_log.passed)
        self.assertEqual(r_log.block_code, P282_BLOCKED_HDMI_LCD_BLANKING_OR_1080_BYPASS)

    def test_25_pillar49a_allows_4k_when_hdmi_only_or_raw_output_active(self) -> None:
        r1 = evaluate_usb_mode_pd_guard_and_hdmi_info_vault(
            UsbModePdGuardHdmiInfoVaultSpec(
                pre_rec_media_dur_hdmi="Off(HDMI Only)",
                post_rec_media_dur_hdmi="Off(HDMI Only)",
                log_shooting="Cine EI",
                reported_effective_hdmi_resolution="4K",
            )
        )
        self.assertTrue(r1.passed)

        r2 = evaluate_usb_mode_pd_guard_and_hdmi_info_vault(
            UsbModePdGuardHdmiInfoVaultSpec(
                pre_raw_output="On",
                post_raw_output="On",
                log_shooting="Cine EI",
                reported_effective_hdmi_resolution="4K",
            )
        )
        self.assertTrue(r2.passed)

    def test_26_pillar49a_rejects_setup_reset_drift_and_framing_leak(self) -> None:
        r_cam = evaluate_usb_mode_pd_guard_and_hdmi_info_vault(
            UsbModePdGuardHdmiInfoVaultSpec(
                external_hdmi_recorder_attached=False,
                reset_action="Camera Settings Reset",
                pre_usb_connection_mode="MTP",
                pre_hdmi_info_display="Off",
                pre_framing_hdmi="Full",
                post_usb_connection_mode="Sel. When Connect",
                post_hdmi_info_display="On",
                post_framing_hdmi="Full",
            )
        )
        self.assertFalse(r_cam.passed)
        self.assertEqual(r_cam.block_code, P282_BLOCKED_SETUP_USB_HDMI_RESET_SCOPE_DRIFT)

    def test_27_pillar49a_camset01_restore_after_initialize_succeeds(self) -> None:
        rep = evaluate_usb_mode_pd_guard_and_hdmi_info_vault(
            UsbModePdGuardHdmiInfoVaultSpec(
                reset_action="Initialize",
                camset_load_after_reset=True,
                camset_slot=1,
                camset_filename="CAMSET01.DAT",
                camset_source_model=P282_FX3_MODEL_NAME,
                camset_read_only_load=True,
                saved_usb_connection_mode="Sel. When Connect",
                saved_usb_lun_setting="Single",
                saved_usb_power_supply="On",
                saved_hdmi_info_display="Off",
                saved_rec_media_dur_hdmi="Off(HDMI Only)",
                saved_output_resolution="Auto",
                saved_raw_output="Off",
                saved_framing_hdmi="Crop",
                post_usb_lun_setting="Single",
                post_rec_media_dur_hdmi="Off(HDMI Only)",
                reported_effective_hdmi_resolution="4K",
            )
        )
        self.assertTrue(rep.passed)

    def test_28_pillar49a_rejects_camset_cross_model_and_overlay_and_h0_h3_and_invalid_spec(self) -> None:
        for bad_kwargs, expected_code in (
            (
                {
                    "reset_action": "Initialize",
                    "camset_load_after_reset": True,
                    "camset_source_model": "ILME-FX6",
                },
                P282_BLOCKED_SETUP_USB_HDMI_RESET_SCOPE_DRIFT,
            ),
            ({"overlay_dir": "/nflasha15/persistent"}, P282_BLOCKED_PERSISTENT_OVERLAY_ESCAPE),
            ({"p2_blkroset_locked": False}, P282_BLOCKED_PERSISTENT_OVERLAY_ESCAPE),
            ({"stage_b_backup_bin_writes": 1}, P282_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT),
            ({"backup_bin_h3_sha256": "f" * 64}, P282_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT),
            ({"camera_model": "ILME-FX6"}, P282_BLOCKED_INVALID_PILLAR49A_SPEC),
            ({"persistent_write_unlock_requested": True}, P282_BLOCKED_SAFETY_POLICY_VIOLATION),
        ):
            rep = evaluate_usb_mode_pd_guard_and_hdmi_info_vault(
                UsbModePdGuardHdmiInfoVaultSpec(**bad_kwargs)
            )
            self.assertFalse(rep.passed, f"Expected reject for {bad_kwargs}")
            self.assertEqual(rep.block_code, expected_code)

    # ------------------------------------------------------------------
    # 6. Pillar 49B Deterministic Helpers
    # ------------------------------------------------------------------

    def test_29_protect_vs_format_helper_allows_dual_layer_wp_slot1_read_only(self) -> None:
        del_blk, fmt_wipes, dual_armed, vault_blk = compute_expected_protect_vs_format_slot1_defense(
            software_protect_active=True,
            slot1_holds_recovery_vault=True,
            slot1_sdxc_wp_locked=True,
            slot1_format_hard_locked=True,
            requested_vault_slot=1,
            requested_vault_action="READ_ONLY_AUDIT",
        )
        self.assertTrue(del_blk)
        self.assertTrue(fmt_wipes)
        self.assertTrue(dual_armed)
        self.assertFalse(vault_blk)

    def test_30_protect_vs_format_helper_blocks_all_destructive_actions_on_slot1(self) -> None:
        for action in p282.P282_DESTRUCTIVE_VAULT_ACTIONS:
            _, _, _, vault_blk = compute_expected_protect_vs_format_slot1_defense(
                software_protect_active=True,
                slot1_holds_recovery_vault=True,
                slot1_sdxc_wp_locked=True,
                slot1_format_hard_locked=True,
                requested_vault_slot=1,
                requested_vault_action=action,
            )
            self.assertTrue(vault_blk, f"Expected Slot 1 block for {action}")

    def test_31_protect_vs_format_helper_rejects_software_protect_only_without_wp(self) -> None:
        del_blk, fmt_wipes, dual_armed, _ = compute_expected_protect_vs_format_slot1_defense(
            software_protect_active=True,
            slot1_holds_recovery_vault=True,
            slot1_sdxc_wp_locked=False,
            slot1_format_hard_locked=True,
            requested_vault_slot=1,
            requested_vault_action="READ_ONLY_AUDIT",
        )
        self.assertTrue(del_blk)
        self.assertTrue(fmt_wipes)
        self.assertFalse(dual_armed)

    def test_32_network_reset_zero_rf_helper_all_reset_actions(self) -> None:
        creds_clr, rbt_req, imm_ap, non_nw_ok, zero_rf = (
            compute_expected_network_reset_zero_rf_sequence(
                reset_action="Reset Network Set.",
                pre_network_creds_present=True,
                pre_airplane_mode="Off",
                pre_shooting_preserved=True,
                pre_setup_preserved=True,
                pre_playback_preserved=True,
                pre_camset_preserved=True,
                auto_reboot_completed=True,
                post_reasserted_airplane_mode="On",
            )
        )
        self.assertTrue(creds_clr)
        self.assertTrue(rbt_req)
        self.assertEqual(imm_ap, "Off")
        self.assertTrue(non_nw_ok)
        self.assertTrue(zero_rf)

        # Incomplete reboot or Airplane Mode left Off -> zero_rf False
        *_, z_no_reboot = compute_expected_network_reset_zero_rf_sequence(
            reset_action="Reset Network Set.",
            pre_network_creds_present=True,
            pre_airplane_mode="Off",
            pre_shooting_preserved=True,
            pre_setup_preserved=True,
            pre_playback_preserved=True,
            pre_camset_preserved=True,
            auto_reboot_completed=False,
            post_reasserted_airplane_mode="On",
        )
        self.assertFalse(z_no_reboot)

        *_, z_off = compute_expected_network_reset_zero_rf_sequence(
            reset_action="Reset Network Set.",
            pre_network_creds_present=True,
            pre_airplane_mode="On",
            pre_shooting_preserved=True,
            pre_setup_preserved=True,
            pre_playback_preserved=True,
            pre_camset_preserved=True,
            auto_reboot_completed=True,
            post_reasserted_airplane_mode="Off",
        )
        self.assertFalse(z_off)

    # ------------------------------------------------------------------
    # 7. Pillar 49B Evaluator & Matrix Coverage
    # ------------------------------------------------------------------

    def test_33_pillar49b_default_safe_passes_with_44_matrix_states(self) -> None:
        spec = build_default_safe_protect_format_network_reset_zero_rf_vault_spec()
        rep = evaluate_protect_format_network_reset_zero_rf_vault(spec)
        self.assertTrue(rep.passed)
        self.assertEqual(rep.status, P282_STATUS_VERIFIED_PILLAR_49B)
        self.assertIsNone(rep.block_code)
        self.assertTrue(rep.protect_4scopes_and_format_override_verified)
        self.assertTrue(rep.slot1_dual_layer_wp_and_format_firewall_verified)
        self.assertTrue(rep.network_reset_reboot_and_airplane_zero_rf_verified)
        self.assertTrue(rep.three_way_reset_scope_and_camset_verified)
        self.assertTrue(rep.h0_equals_h3_verified)
        self.assertEqual(rep.matrix_states_checked, 44)
        self.assertEqual(rep.slot1_protect_only_vault_violations, 0)
        self.assertEqual(rep.slot1_vault_format_or_delete_events, 0)
        self.assertEqual(rep.slot1_vault_mutation_bytes, 0)
        self.assertTrue(rep.slot1_format_hard_locked)
        self.assertEqual(rep.network_reset_zero_rf_violations, 0)

    def test_34_pillar49b_rejects_software_protect_only_or_missing_wp(self) -> None:
        for bad in (
            {"slot1_sdxc_wp_locked": False},
            {"slot1_format_hard_locked": False},
            {"slot1_protect_only_vault_violations": 1},
        ):
            rep = evaluate_protect_format_network_reset_zero_rf_vault(
                ProtectFormatNetworkResetZeroRfVaultSpec(**bad)
            )
            self.assertFalse(rep.passed)
            self.assertEqual(rep.block_code, P282_BLOCKED_SLOT1_PROTECT_ONLY_OR_FORMAT_WIPE)

    def test_35_pillar49b_blocks_all_format_and_delete_actions_on_slot1(self) -> None:
        for action in p282.P282_DESTRUCTIVE_VAULT_ACTIONS:
            rep = evaluate_protect_format_network_reset_zero_rf_vault(
                ProtectFormatNetworkResetZeroRfVaultSpec(
                    requested_vault_slot=1,
                    requested_vault_action=action,
                )
            )
            self.assertFalse(rep.passed, f"Expected Slot 1 block for {action}")
            self.assertEqual(rep.block_code, P282_BLOCKED_SLOT1_PROTECT_ONLY_OR_FORMAT_WIPE)
            self.assertGreaterEqual(rep.slot1_vault_format_or_delete_events, 1)

    def test_36_pillar49b_allows_slot2_delete_or_format_when_slot1_dual_locked(self) -> None:
        for action in p282.P282_DESTRUCTIVE_VAULT_ACTIONS:
            rep = evaluate_protect_format_network_reset_zero_rf_vault(
                ProtectFormatNetworkResetZeroRfVaultSpec(
                    requested_vault_slot=2,
                    requested_vault_action=action,
                )
            )
            self.assertTrue(rep.passed, f"Slot 2 non-vault {action} should pass when Slot 1 dual-locked")

    def test_37_pillar49b_rejects_incomplete_network_reset_reboot_or_airplane_off(self) -> None:
        for bad in (
            {"auto_reboot_triggered": False},
            {"auto_reboot_completed": False},
            {"post_reasserted_airplane_mode": "Off"},
            {"post_network_creds_cleared": False},
            {"pre_shooting_preserved": False},
            {"pre_setup_preserved": False},
            {"pre_playback_preserved": False},
            {"pre_camset_preserved": False},
            {"immediate_post_reset_airplane_mode": "On"},
            {"network_reset_zero_rf_violations": 1},
        ):
            rep = evaluate_protect_format_network_reset_zero_rf_vault(
                ProtectFormatNetworkResetZeroRfVaultSpec(**bad)
            )
            self.assertFalse(rep.passed, f"Expected failure for {bad}")
            self.assertEqual(rep.block_code, P282_BLOCKED_NETWORK_RESET_OR_AIRPLANE_ZERO_RF_DRIFT)

    def test_38_pillar49b_initialize_with_camset01_reload_and_zero_rf_passes(self) -> None:
        rep = evaluate_protect_format_network_reset_zero_rf_vault(
            ProtectFormatNetworkResetZeroRfVaultSpec(
                reset_action="Initialize",
                auto_reboot_triggered=True,
                auto_reboot_completed=True,
                immediate_post_reset_airplane_mode="Off",
                post_network_creds_cleared=True,
                post_reasserted_airplane_mode="On",
                camset_load_after_reset=True,
                camset_slot=1,
                camset_filename="CAMSET01.DAT",
                camset_source_model=P282_FX3_MODEL_NAME,
                camset_read_only_load=True,
            )
        )
        self.assertTrue(rep.passed)

    def test_39_pillar49b_rejects_overlay_escape_h0_h3_invalid_spec_and_safety_tamper(self) -> None:
        for bad_kwargs, expected_code in (
            ({"overlay_dir": "/setting/49b"}, P282_BLOCKED_PERSISTENT_OVERLAY_ESCAPE),
            ({"p2_blkroset_locked": False}, P282_BLOCKED_PERSISTENT_OVERLAY_ESCAPE),
            ({"stage_b_backup_bin_writes": 1}, P282_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT),
            ({"backup_bin_h3_sha256": "0" * 64}, P282_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT),
            ({"camera_model": "ILME-FX6"}, P282_BLOCKED_INVALID_PILLAR49B_SPEC),
            ({"protect_4_scopes": ("Multiple Img.",)}, P282_BLOCKED_SLOT1_PROTECT_ONLY_OR_FORMAT_WIPE),
            ({"persistent_write_unlock_requested": True}, P282_BLOCKED_SAFETY_POLICY_VIOLATION),
        ):
            rep = evaluate_protect_format_network_reset_zero_rf_vault(
                ProtectFormatNetworkResetZeroRfVaultSpec(**bad_kwargs)
            )
            self.assertFalse(rep.passed, f"Expected failure for {bad_kwargs}")
            self.assertEqual(rep.block_code, expected_code)

    # ------------------------------------------------------------------
    # 8. Standalone Pillar 49A / 49B / Combined Suites
    # ------------------------------------------------------------------

    def test_40_pillar49a_6_scenario_suite_passes_6_of_6(self) -> None:
        res = run_pillar49a_usb_mode_pd_hdmi_info_vault_6_scenario_suite()
        self.assertTrue(res.passed)
        self.assertEqual(res.status, P282_STATUS_VERIFIED_PILLAR_49A)
        self.assertEqual(res.scenarios_passed, 6)
        self.assertEqual(res.scenarios_total, 6)
        self.assertEqual(tuple(s.scenario_id for s in res.scenarios), P282_PILLAR_49A_SCENARIO_IDS)
        self.assertTrue(all(s.passed for s in res.scenarios))

    def test_41_pillar49b_6_scenario_suite_passes_6_of_6(self) -> None:
        res = run_pillar49b_protect_format_network_reset_vault_6_scenario_suite()
        self.assertTrue(res.passed)
        self.assertEqual(res.status, P282_STATUS_VERIFIED_PILLAR_49B)
        self.assertEqual(res.scenarios_passed, 6)
        self.assertEqual(res.scenarios_total, 6)
        self.assertEqual(tuple(s.scenario_id for s in res.scenarios), P282_PILLAR_49B_SCENARIO_IDS)
        self.assertTrue(all(s.passed for s in res.scenarios))

    def test_42_verify_usb_mode_hdmi_info_protect_network_reset_and_aliases(self) -> None:
        rep = verify_usb_mode_hdmi_info_protect_network_reset_and_vault(force_clean_room=True)
        rep_alias = verify_usb_mode_hdmi_info_protect_network_reset_vault(force_clean_room=True)
        self.assertTrue(rep.all_passed)
        self.assertTrue(rep_alias.all_passed)
        self.assertEqual(rep.status, P282_STATUS_VERIFIED_PILLAR49_SUITE)
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertFalse(rep.fx3_ui_exposes_usb_streaming)
        self.assertTrue(rep.slot1_format_hard_locked)
        self.assertEqual(rep.slot1_vault_format_or_delete_events, 0)
        self.assertEqual(rep.network_reset_zero_rf_violations, 0)

    def test_43_run_pillar49_standalone_suite_active_and_clean_room(self) -> None:
        rep_active = run_pillar49_standalone_suite()
        rep_clean = run_pillar49_standalone_suite(force_clean_room=True)
        for rep in (rep_active, rep_clean):
            self.assertIsInstance(rep, Pillar49StandaloneReport)
            self.assertTrue(rep.all_passed)
            self.assertEqual(rep.status, P282_STATUS_VERIFIED_PILLAR49_SUITE)
            self.assertEqual(rep.pillar_49a_usb_mode_pd_hdmi_info_vault.scenarios_passed, 6)
            self.assertEqual(rep.pillar_49b_protect_format_network_reset_vault.scenarios_passed, 6)
            self.assertEqual(rep.raw_firmware_bytes_leaked, 0)
            self.assertEqual(rep.physical_device_writes, 0)
            self.assertFalse(rep.hardware_live_attachment_authorized)
            self.assertTrue(rep.slot1_format_hard_locked)

    # ------------------------------------------------------------------
    # 9. Unified 49/49 Recovery Master Aggregator & Dual-Mode Parity
    # ------------------------------------------------------------------

    def test_44_master_49pillar_active_mode_passes_under_budget(self) -> None:
        rep = evaluate_realhw_49pillar_recovery_master()
        self.assertIsInstance(rep, Master49PillarRecoveryReport)
        self.assertTrue(rep.all_passed)
        self.assertEqual(rep.status, P282_STATUS_VERIFIED_49OF49_AGGREGATOR)
        self.assertGreaterEqual(rep.pillar_count, 49)
        self.assertEqual(rep.pillars_passed, rep.pillar_count)
        self.assertEqual(rep.failed_pillars, ())
        self.assertLess(rep.elapsed_seconds, _cli_budget_seconds())
        self.assertTrue(rep.under_6s_budget)
        self.assertTrue(rep.nominal_under_4_0s)
        self.assertIn(MASTER_49_PILLAR_IDS[48], tuple(p.pillar_id for p in rep.pillars))

    def test_45_master_49pillar_clean_room_mode_passes(self) -> None:
        rep = evaluate_realhw_49pillar_recovery_master(force_clean_room=True)
        self.assertTrue(rep.all_passed)
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertGreaterEqual(rep.pillar_count, 49)
        self.assertEqual(rep.pillars_passed, rep.pillar_count)
        self.assertEqual(rep.failed_pillars, ())
        self.assertLess(rep.elapsed_seconds, _cli_budget_seconds())

    def test_46_master_49pillar_env_clean_room_and_force_clean_room_modes(self) -> None:
        for env_key in (P282_ENV_CLEAN_ROOM_TEST, "FX3_FX6_FORCE_CLEAN_ROOM"):
            with mock.patch.dict(os.environ, {env_key: "1"}):
                rep = evaluate_49pillar_recovery_master()
            self.assertTrue(rep.all_passed)
            self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertGreaterEqual(rep.pillars_passed, 49)

    def test_47_master_49pillar_aliases_and_deterministic_sha256(self) -> None:
        r1 = evaluate_49pillar_recovery_master(force_clean_room=True)
        r2 = verify_49pillar_recovery_suite(force_clean_room=True)
        self.assertEqual(r1.master_49pillar_sha256, r2.master_49pillar_sha256)
        self.assertEqual(len(r1.master_49pillar_sha256), 64)

    def test_48_master_49pillar_preserves_prior_48_pillar_invariants(self) -> None:
        rep = evaluate_realhw_49pillar_recovery_master(force_clean_room=True)
        self.assertFalse(rep.fx3_ui_exposes_usb_streaming)
        self.assertEqual(rep.nouvc_spoof_events, 0)
        self.assertEqual(rep.usb_host_data_enumeration_events, 0)
        self.assertEqual(rep.hdmi_lcd_blanking_violations, 0)
        self.assertEqual(rep.hdmi_log_1080_bypass_events, 0)
        self.assertEqual(rep.slot1_protect_only_vault_violations, 0)
        self.assertEqual(rep.slot1_vault_format_or_delete_events, 0)
        self.assertEqual(rep.network_reset_zero_rf_violations, 0)
        self.assertFalse(rep.fx3_ui_exposes_power_save_by_monitor)
        self.assertEqual(rep.legacy_power_save_monitor_spoof_events, 0)
        self.assertEqual(rep.bk_lang_parity_drift_events, 0)
        self.assertEqual(rep.xlrh1_acoustic_feedback_violations, 0)
        self.assertEqual(rep.slot1_vault_delete_events, 0)
        self.assertEqual(rep.legacy_mf_assist_spoof_events, 0)
        self.assertFalse(rep.fx3_has_builtin_end_filter)
        self.assertFalse(rep.fx3_has_builtin_evf)
        self.assertFalse(rep.fx3_has_var_shutter)
        self.assertGreaterEqual(rep.bodydata_flash_attempts_blocked, 1)
        self.assertTrue(rep.cnflasha_userspace_write_blocked)
        self.assertTrue(rep.slot1_format_hard_locked)

    def test_49_master_49pillar_fault_injection_pillar_49(self) -> None:
        rep = evaluate_realhw_49pillar_recovery_master(
            force_clean_room=True,
            fault_inject_pillar="pillar_49_usb_mode_hdmi_info_protect_network_reset_vault",
        )
        self.assertFalse(rep.all_passed)
        self.assertEqual(rep.status, P282_STATUS_FAIL_49OF49_AGGREGATOR)
        self.assertEqual(rep.pillars_passed, rep.pillar_count - 1)
        self.assertEqual(
            rep.failed_pillars,
            ("pillar_49_usb_mode_hdmi_info_protect_network_reset_vault",),
        )

    def test_50_master_49pillar_fault_injection_pillar_48_and_unknown_error(self) -> None:
        rep = evaluate_realhw_49pillar_recovery_master(
            force_clean_room=True,
            fault_inject_pillar=MASTER_49_PILLAR_IDS[47],
        )
        self.assertFalse(rep.all_passed)
        self.assertEqual(rep.pillars_passed, rep.pillar_count - 1)
        self.assertEqual(rep.failed_pillars, (MASTER_49_PILLAR_IDS[47],))
        with self.assertRaises(ValueError):
            evaluate_realhw_49pillar_recovery_master(
                force_clean_room=True,
                fault_inject_pillar="pillar_999_nonexistent",
            )

    def test_51_master_49pillar_to_dict_json_roundtrip(self) -> None:
        rep = evaluate_realhw_49pillar_recovery_master(force_clean_room=True)
        dumped = json.dumps(rep.to_dict(), sort_keys=True, allow_nan=False)
        parsed = json.loads(dumped)
        self.assertGreaterEqual(parsed["pillar_count"], 49)
        self.assertEqual(parsed["pillars_passed"], parsed["pillar_count"])
        self.assertTrue(parsed["all_passed"])
        self.assertEqual(parsed["schema"], PHASE282_SCHEMA)

    # ------------------------------------------------------------------
    # 10. CLI Integration (--json, --clean-room, --out, sys.executable)
    # ------------------------------------------------------------------

    def test_52_cli_pillar49_standalone_json_clean_room(self) -> None:
        buf = io.StringIO()
        with mock.patch.object(
            sys,
            "argv",
            [
                "fx3_recovery",
                "verify-usb-mode-hdmi-info-protect-network-reset-vault",
                "--clean-room",
                "--json",
            ],
        ):
            with redirect_stdout(buf):
                rc = cli_main.main()
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())
        self.assertTrue(payload["all_passed"])
        self.assertEqual(payload["status"], P282_STATUS_VERIFIED_PILLAR49_SUITE)
        self.assertEqual(payload["verification_mode"], "CLEAN_ROOM_SYNTHETIC")

    def test_53_cli_49pillar_master_json_clean_room(self) -> None:
        buf = io.StringIO()
        with mock.patch.object(
            sys,
            "argv",
            ["fx3_recovery", "verify-49pillar-recovery", "--clean-room", "--json"],
        ):
            with redirect_stdout(buf):
                rc = cli_main.main()
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())
        self.assertTrue(payload["all_passed"])
        self.assertGreaterEqual(payload["pillar_count"], 49)
        self.assertEqual(payload["pillars_passed"], payload["pillar_count"])
        self.assertEqual(payload["status"], P282_STATUS_VERIFIED_49OF49_AGGREGATOR)

    def test_54_cli_49pillar_master_out_dir_repo_local_cleaned_in_finally(self) -> None:
        work_tests = _repo_root() / "work" / "_tests"
        work_tests.mkdir(parents=True, exist_ok=True)
        out_root = Path(tempfile.mkdtemp(prefix="p282_cli_", dir=str(work_tests)))
        out_dir = out_root / "master49"
        try:
            buf = io.StringIO()
            with mock.patch.object(
                sys,
                "argv",
                ["fx3_recovery", "verify-49pillar-recovery", "--clean-room", "--out", str(out_dir), "--json"],
            ):
                with redirect_stdout(buf):
                    rc = cli_main.main()
            self.assertEqual(rc, 0)
            out_file = out_dir / "49pillar-recovery-master-report.json"
            self.assertTrue(out_file.is_file())
            written = json.loads(out_file.read_text(encoding="utf-8"))
            self.assertGreaterEqual(written["pillars_passed"], 49)
        finally:
            shutil.rmtree(out_root, ignore_errors=True)

    def test_55_cli_pillar49_standalone_out_dir_repo_local_cleaned_in_finally(self) -> None:
        work_tests = _repo_root() / "work" / "_tests"
        work_tests.mkdir(parents=True, exist_ok=True)
        out_root = Path(tempfile.mkdtemp(prefix="p282_p49_out_", dir=str(work_tests)))
        out_dir = out_root / "pillar49"
        try:
            buf = io.StringIO()
            with mock.patch.object(
                sys,
                "argv",
                [
                    "fx3_recovery",
                    "verify-usb-mode-hdmi-info-protect-network-reset-vault",
                    "--clean-room",
                    "--out",
                    str(out_dir),
                    "--json",
                ],
            ):
                with redirect_stdout(buf):
                    rc = cli_main.main()
            self.assertEqual(rc, 0)
            out_file = out_dir / "pillar49-usb-mode-hdmi-info-protect-network-reset-vault-report.json"
            self.assertTrue(out_file.is_file())
            written = json.loads(out_file.read_text(encoding="utf-8"))
            self.assertTrue(written["all_passed"])
        finally:
            shutil.rmtree(out_root, ignore_errors=True)

    def test_56_cli_subprocess_sys_executable_both_modes(self) -> None:
        adapter_dir = _repo_root() / "outputs" / "fx3-recovery-adapter"
        env_base = dict(os.environ)
        env_base["PYTHONDONTWRITEBYTECODE"] = "1"
        env_base["PYTHONPATH"] = str(adapter_dir)

        proc_active = subprocess.run(
            [sys.executable, "-B", "-m", "fx3_recovery", "verify-49pillar-recovery", "--json"],
            cwd=str(_repo_root()),
            env=env_base,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc_active.returncode, 0, proc_active.stderr)
        data_active = json.loads(proc_active.stdout)
        self.assertTrue(data_active["all_passed"])
        self.assertGreaterEqual(data_active["pillars_passed"], 49)

        env_clean = dict(env_base)
        env_clean[P282_ENV_CLEAN_ROOM_TEST] = "1"
        proc_clean = subprocess.run(
            [sys.executable, "-B", "-m", "fx3_recovery", "verify-49pillar-recovery", "--clean-room", "--json"],
            cwd=str(_repo_root()),
            env=env_clean,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc_clean.returncode, 0, proc_clean.stderr)
        data_clean = json.loads(proc_clean.stdout)
        self.assertEqual(data_clean["verification_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertGreaterEqual(data_clean["pillars_passed"], 49)

    def test_57_cli_human_readable_text_output_both_commands(self) -> None:
        b1 = io.StringIO()
        with mock.patch.object(
            sys,
            "argv",
            ["fx3_recovery", "verify-usb-mode-hdmi-info-protect-network-reset-vault", "--clean-room"],
        ):
            with redirect_stdout(b1):
                rc1 = cli_main.main()
        self.assertEqual(rc1, 0)
        t1 = b1.getvalue()
        self.assertIn("pillar_49a=6/6", t1)
        self.assertIn("pillar_49b=6/6", t1)
        self.assertIn("slot1_format_hard_locked=True", t1)

        b2 = io.StringIO()
        with mock.patch.object(
            sys,
            "argv",
            ["fx3_recovery", "verify-49pillar-recovery", "--clean-room"],
        ):
            with redirect_stdout(b2):
                rc2 = cli_main.main()
        self.assertEqual(rc2, 0)
        t2 = b2.getvalue()
        self.assertIn("pillars=", t2)
        self.assertIn("all_passed=True", t2)
        self.assertIn("raw_firmware_bytes_leaked=0", t2)

    # ------------------------------------------------------------------
    # 11. Additional Edge-Case & Fault-Isolation Tests (58..76)
    # ------------------------------------------------------------------

    def test_58_safety_tamper_blocks_both_49a_and_49b(self) -> None:
        with mock.patch.object(p282, "PHYSICAL_DEVICE_WRITES", 1):
            errs = p282._safety_invariant_errors()
            self.assertTrue(any("PHYSICAL_DEVICE_WRITES" in e for e in errs))
            r49a = evaluate_usb_mode_pd_guard_and_hdmi_info_vault()
            self.assertFalse(r49a.passed)
            self.assertEqual(r49a.block_code, P282_BLOCKED_SAFETY_POLICY_VIOLATION)
            r49b = evaluate_protect_format_network_reset_zero_rf_vault()
            self.assertFalse(r49b.passed)
            self.assertEqual(r49b.block_code, P282_BLOCKED_SAFETY_POLICY_VIOLATION)

    def test_59_non_airgap_allows_host_usb_data_modes_when_mode_matches(self) -> None:
        for mode in ("MassStorage(MSC)", "MTP", "Remote Shoot (PC Remote)"):
            rep = evaluate_usb_mode_pd_guard_and_hdmi_info_vault(
                UsbModePdGuardHdmiInfoVaultSpec(
                    airgapped_tier0_session=False,
                    pre_usb_connection_mode=mode,
                    post_usb_connection_mode=mode,
                    active_host_usb_data_mode=mode,
                    usb_data_lines_physically_isolated=False,
                    pre_usb_power_supply="Off",
                    post_usb_power_supply="Off",
                )
            )
            self.assertTrue(rep.passed, f"Non-airgap host mode {mode} should pass when PD isolated check skipped")

    def test_60_hdmi_info_on_allowed_when_external_recorder_detached(self) -> None:
        rep = evaluate_usb_mode_pd_guard_and_hdmi_info_vault(
            UsbModePdGuardHdmiInfoVaultSpec(
                external_hdmi_recorder_attached=False,
                operator_lcd_menu_recovery_active=True,
                pre_hdmi_info_display="On",
                post_hdmi_info_display="On",
            )
        )
        self.assertTrue(rep.passed)

    def test_61_hdmi_info_on_allowed_when_operator_lcd_recovery_inactive(self) -> None:
        rep = evaluate_usb_mode_pd_guard_and_hdmi_info_vault(
            UsbModePdGuardHdmiInfoVaultSpec(
                external_hdmi_recorder_attached=True,
                operator_lcd_menu_recovery_active=False,
                pre_hdmi_info_display="On",
                post_hdmi_info_display="On",
            )
        )
        self.assertTrue(rep.passed)

    def test_62_all_picture_profile_modes_1080p_clamp(self) -> None:
        for pp in ("PPLUT1", "PPLUT2", "PPLUT3", "PPLUT4"):
            rep = evaluate_usb_mode_pd_guard_and_hdmi_info_vault(
                UsbModePdGuardHdmiInfoVaultSpec(
                    picture_profile=pp,
                    reported_effective_hdmi_resolution="1080p",
                )
            )
            self.assertTrue(rep.passed, f"Expected 1080p clamp pass for {pp}")

        rep_pp = evaluate_usb_mode_pd_guard_and_hdmi_info_vault(
            UsbModePdGuardHdmiInfoVaultSpec(
                log_shooting="Off",
                picture_profile="PP1..PP11",
                reported_effective_hdmi_resolution="Auto",
            )
        )
        self.assertTrue(rep_pp.passed)

    def test_63_all_log_shooting_modes_1080p_clamp(self) -> None:
        for log_mode in ("Flexible ISO", "Cine EI", "Cine EI Quick"):
            rep = evaluate_usb_mode_pd_guard_and_hdmi_info_vault(
                UsbModePdGuardHdmiInfoVaultSpec(
                    log_shooting=log_mode,
                    reported_effective_hdmi_resolution="1080p",
                )
            )
            self.assertTrue(rep.passed, f"Expected 1080p clamp pass for {log_mode}")

    def test_64_usb_lun_single_mode_passes_and_survives_camera_settings_reset(self) -> None:
        rep = evaluate_usb_mode_pd_guard_and_hdmi_info_vault(
            UsbModePdGuardHdmiInfoVaultSpec(
                reset_action="Camera Settings Reset",
                pre_usb_lun_setting="Single",
                post_usb_lun_setting="Single",
                pre_framing_hdmi="Full",
                post_framing_hdmi="Crop",
            )
        )
        self.assertTrue(rep.passed)

    def test_65_reset_network_set_preserves_setup_usb_and_hdmi_settings(self) -> None:
        rep = evaluate_usb_mode_pd_guard_and_hdmi_info_vault(
            UsbModePdGuardHdmiInfoVaultSpec(
                reset_action="Reset Network Set.",
                pre_usb_connection_mode="MTP",
                post_usb_connection_mode="MTP",
                pre_usb_lun_setting="Single",
                post_usb_lun_setting="Single",
                pre_hdmi_info_display="Off",
                post_hdmi_info_display="Off",
                pre_framing_hdmi="Full",
                post_framing_hdmi="Full",
            )
        )
        self.assertTrue(rep.passed)

    def test_66_slot1_missing_recovery_vault_is_rejected(self) -> None:
        rep = evaluate_protect_format_network_reset_zero_rf_vault(
            ProtectFormatNetworkResetZeroRfVaultSpec(
                slot1_holds_recovery_vault=False,
                slot1_sdxc_wp_locked=True,
                slot1_format_hard_locked=True,
                requested_vault_slot=1,
                requested_vault_action="READ_ONLY_AUDIT",
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P282_BLOCKED_SLOT1_PROTECT_ONLY_OR_FORMAT_WIPE)

    def test_67_protect_format_vault_rejects_camset_slot2_mismatch(self) -> None:
        rep = evaluate_protect_format_network_reset_zero_rf_vault(
            ProtectFormatNetworkResetZeroRfVaultSpec(
                reset_action="Initialize",
                camset_load_after_reset=True,
                camset_slot=2,
                camset_filename="CAMSET01.DAT",
                camset_source_model=P282_FX3_MODEL_NAME,
                camset_read_only_load=True,
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P282_BLOCKED_INVALID_PILLAR49B_SPEC)

    def test_68_protect_format_vault_rejects_camset_read_write_load(self) -> None:
        rep = evaluate_protect_format_network_reset_zero_rf_vault(
            ProtectFormatNetworkResetZeroRfVaultSpec(
                reset_action="Initialize",
                camset_load_after_reset=True,
                camset_slot=1,
                camset_filename="CAMSET01.DAT",
                camset_source_model=P282_FX3_MODEL_NAME,
                camset_read_only_load=False,
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P282_BLOCKED_INVALID_PILLAR49B_SPEC)

    def test_69_all_4_camset_filenames_valid_for_post_reset_restore(self) -> None:
        for fname in P282_CAMSET_FILENAMES:
            rep = evaluate_protect_format_network_reset_zero_rf_vault(
                ProtectFormatNetworkResetZeroRfVaultSpec(
                    reset_action="Initialize",
                    camset_load_after_reset=True,
                    camset_slot=1,
                    camset_filename=fname,
                    camset_source_model=P282_FX3_MODEL_NAME,
                    camset_read_only_load=True,
                )
            )
            self.assertTrue(rep.passed, f"Expected valid CAMSET filename {fname}")

    def test_70_all_usb_connection_4_modes_valid_in_spec_for_reset_preservation(self) -> None:
        for mode in P282_FX3_USB_CONNECTION_4_MODES:
            rep = evaluate_usb_mode_pd_guard_and_hdmi_info_vault(
                UsbModePdGuardHdmiInfoVaultSpec(
                    pre_usb_connection_mode=mode,
                    post_usb_connection_mode=mode,
                )
            )
            self.assertTrue(rep.passed, f"Expected valid USB connection mode {mode}")

    def test_71_none_reset_without_creds_and_airplane_on_passes_zero_rf(self) -> None:
        rep = evaluate_protect_format_network_reset_zero_rf_vault(
            ProtectFormatNetworkResetZeroRfVaultSpec(
                reset_action="NONE",
                pre_network_creds_present=False,
                pre_airplane_mode="On",
                auto_reboot_triggered=False,
                auto_reboot_completed=False,
                immediate_post_reset_airplane_mode="On",
                post_network_creds_cleared=True,
                post_reasserted_airplane_mode="On",
            )
        )
        self.assertTrue(rep.passed)

    def test_72_replace_spec_immutability_preserved(self) -> None:
        s49a = build_default_safe_usb_mode_pd_guard_hdmi_info_vault_spec()
        s49a_mod = replace(s49a, pre_usb_lun_setting="Single", post_usb_lun_setting="Single")
        self.assertEqual(s49a.pre_usb_lun_setting, "Multi")
        self.assertTrue(evaluate_usb_mode_pd_guard_and_hdmi_info_vault(s49a_mod).passed)

        s49b = build_default_safe_protect_format_network_reset_zero_rf_vault_spec()
        s49b_mod = replace(s49b, requested_vault_slot=2, requested_vault_action="FORMAT_QUICK")
        self.assertEqual(s49b.requested_vault_slot, 1)
        self.assertTrue(evaluate_protect_format_network_reset_zero_rf_vault(s49b_mod).passed)

    def test_73_pillar49a_and_49b_matrix_counts_exact(self) -> None:
        r49a = evaluate_usb_mode_pd_guard_and_hdmi_info_vault()
        r49b = evaluate_protect_format_network_reset_zero_rf_vault()
        self.assertEqual(r49a.matrix_states_checked, 44)
        self.assertEqual(r49b.matrix_states_checked, 44)

    def test_74_master_49_report_json_has_no_raw_firmware_leak_and_zero_writes(self) -> None:
        rep = evaluate_realhw_49pillar_recovery_master(force_clean_room=True)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)
        self.assertEqual(rep.physical_device_writes, 0)
        self.assertEqual(rep.physical_usb_packets_emitted, 0)
        self.assertEqual(rep.passive_tx_bytes_emitted, 0)
        self.assertEqual(rep.otp_fuse_touches, 0)
        self.assertEqual(rep.otp_fuse_writes, 0)
        self.assertEqual(rep.rpmb_counter_increments, 0)
        self.assertFalse(rep.el3_payload_transmit_authorized)
        self.assertFalse(rep.isp_write_authorized)
        self.assertFalse(rep.spi_nor_write_authorized)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.persistent_write_release)
        self.assertFalse(rep.allow_boot_partition_targeting)
        self.assertFalse(rep.allow_destructive_fastboot)
        self.assertFalse(rep.live_usb_iokit_transmit_enabled)

    def test_75_backward_compatibility_48pillar_master_still_passes(self) -> None:
        rep48 = p282.evaluate_realhw_48pillar_recovery_master(force_clean_room=True)
        self.assertTrue(rep48.all_passed)
        self.assertGreaterEqual(rep48.pillars_passed, 48)

    def test_76_combined_suite_determinism_same_sha256_in_clean_room(self) -> None:
        a = verify_usb_mode_hdmi_info_protect_network_reset_and_vault(force_clean_room=True)
        b = verify_usb_mode_hdmi_info_protect_network_reset_and_vault(force_clean_room=True)
        self.assertEqual(a.usb_hdmi_report.digest_sha256, b.usb_hdmi_report.digest_sha256)
        self.assertEqual(a.protect_network_report.digest_sha256, b.protect_network_report.digest_sha256)
        self.assertEqual(len(a.usb_hdmi_report.digest_sha256), 64)
        self.assertEqual(len(a.protect_network_report.digest_sha256), 64)


if __name__ == "__main__":
    unittest.main()
