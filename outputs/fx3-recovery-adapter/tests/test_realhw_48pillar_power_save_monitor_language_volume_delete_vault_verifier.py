"""Phase 277 — Dual-mode unit tests for Pillar 48 (`[Power Save by Monitor]` reality split vs
`ILME-FX3` `ilc/2210` 2-item `[Power Setting Option]`, `[Power Save Start Time]` 9-deactivation
Tier-0 recovery guard, `[Language]` `BK_LANG` `0x02cf019c` 4-language Stage-B parity,
`[Volume Settings]` `0..15` default `7` + `XLR-H1` speaker feedback guard, `[4ch Audio Monitoring]`
5 routes vs HDMI `[4ch Audio Output]`, `[Delete confirm.]` `"Cancel" first` + hard `Slot-1`
recovery vault delete/format firewall) and unified `48/48` recovery master
(`verify-48pillar-recovery` / `verify-power-save-monitor-language-volume-delete-vault`)."""

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
    realhw_48pillar_power_save_monitor_language_volume_delete_vault_verifier as p277,
)
from fx3_recovery.realhw_47pillar_focus_mag_datetime_videolight_hdmires_vault_verifier import (
    MASTER_47_PILLAR_SPECS,
)
from fx3_recovery.realhw_48pillar_power_save_monitor_language_volume_delete_vault_verifier import (
    ALLOW_BOOT_PARTITION_TARGETING,
    ALLOW_DESTRUCTIVE_FASTBOOT,
    ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS,
    ALLOW_PERSISTENT_JIRITSU_WRITES,
    CNFLASHA_USERSPACE_WRITE_BLOCKED,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    ISP_WRITE_AUTHORIZED,
    LIVE_USB_IOKIT_TRANSMIT_ENABLED,
    MASTER_48_PILLAR_COUNT,
    MASTER_48_PILLAR_IDS,
    MASTER_48_PILLAR_SPECS,
    OTP_FUSE_TOUCHES,
    OTP_FUSE_WRITES,
    P277_AUDIO_MONITORING_5_ROUTES,
    P277_AUDIO_MONITORING_BKID,
    P277_AUDIO_MONITORING_DEFAULT,
    P277_AUDIO_MONITORING_ENUM_MAP,
    P277_AUDIO_MONITORING_MENU_PATH,
    P277_AUDIO_MONITORING_RESID16_MAP,
    P277_AUDIO_MON_4CH_HDMI_CONFUSION_EVENTS,
    P277_AUDIO_SIGNALS_RESID16,
    P277_AUTO_POWER_OFF_TEMP_DEFAULT,
    P277_AUTO_POWER_OFF_TEMP_MODES,
    P277_BK_LANG_PARITY_DRIFT_EVENTS,
    P277_BLOCKED_AUDIO_MON_4CH_OR_HDMI_CONFUSION,
    P277_BLOCKED_BK_LANG_OR_STAGE_B_4LANG_PARITY_DRIFT,
    P277_BLOCKED_DESTRUCTIVE_DELETE_CONFIRM_DRIFT,
    P277_BLOCKED_INVALID_PILLAR48A_SPEC,
    P277_BLOCKED_INVALID_PILLAR48B_SPEC,
    P277_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
    P277_BLOCKED_POWER_SAVE_MONITOR_REALITY_SPLIT_OR_SPOOF,
    P277_BLOCKED_POWER_SAVE_START_TIME_RECOVERY_SLEEP,
    P277_BLOCKED_SAFETY_POLICY_VIOLATION,
    P277_BLOCKED_SETUP_LANGUAGE_POWER_RESET_SCOPE_DRIFT,
    P277_BLOCKED_SLOT1_VAULT_DELETE_OR_FORMAT,
    P277_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
    P277_BLOCKED_VOLUME_RANGE_OR_XLRH1_FEEDBACK,
    P277_CAMSET_FILENAMES,
    P277_CONCURRENT_CEILING_SECONDS,
    P277_DELETE_CONFIRM_BKID,
    P277_DELETE_CONFIRM_DEFAULT,
    P277_DELETE_CONFIRM_MENU_PATH,
    P277_DELETE_CONFIRM_MODES,
    P277_DELETE_CONFIRM_RESID16_PAIRS,
    P277_DELETE_TWICE_BKID,
    P277_DELETE_TWICE_DEFAULT,
    P277_DELETE_TWICE_MENU_PATH,
    P277_DELETE_TWICE_RESID16,
    P277_DESTRUCTIVE_DELETE_CONFIRM_DRIFT_EVENTS,
    P277_DESTRUCTIVE_VAULT_ACTIONS,
    P277_DONOR_INSPECT_BUDGET_SECONDS,
    P277_DONOR_INSPECT_CI_BUDGET_SECONDS,
    P277_ENV_CLEAN_ROOM_TEST,
    P277_FAST_CLI_BUDGET_SECONDS,
    P277_FORBIDDEN_POWER_SAVE_MONITOR_SPOOF_LABEL,
    P277_FX3_BACKUP_BK_LANG_DEFAULT_VALUE,
    P277_FX3_BACKUP_BK_LANG_OFFSET,
    P277_FX3_FW_VERSION,
    P277_FX3_HELPGUIDE_ID,
    P277_FX3_LANGUAGE_COUNT,
    P277_FX3_MODEL_ID,
    P277_FX3_MODEL_NAME,
    P277_FX3_POWER_SETTING_EXACT_2_SUBITEMS,
    P277_FX3_UI_EXPOSES_POWER_SAVE_BY_MONITOR,
    P277_FX6_BACKUP_BK_LANG_OFFSET,
    P277_FX6_BACKUP_CN1_BK_LANG_VALUE,
    P277_FX6_BACKUP_NTSC_BK_LANG_VALUE,
    P277_FX6_DONOR_FW_VERSION,
    P277_FX6_DONOR_MODEL_NAME,
    P277_FX6_LANGUAGE_COUNT,
    P277_FX6_LANGUAGE_RESID16,
    P277_FX6_UI_EXPOSES_POWER_SAVE_BY_MONITOR,
    P277_FX6_VOLUME_SETTINGS_BKID,
    P277_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    P277_HDMI_4CH_OUTPUT_BKID,
    P277_HDMI_4CH_OUTPUT_MODES,
    P277_HDMI_4CH_OUTPUT_RESID16,
    P277_HEADPHONE_35MM_MAX_CHANNELS,
    P277_LANGUAGE_BKID_FX3,
    P277_LANGUAGE_BKID_FX6,
    P277_LANGUAGE_BK_KEY,
    P277_LANGUAGE_DEFAULT,
    P277_LANGUAGE_MENU_PATH,
    P277_LANGUAGE_RESID16,
    P277_LEGACY_POWER_SAVE_MONITOR_SPOOF_EVENTS,
    P277_NOMINAL_BUDGET_SECONDS,
    P277_PILLAR_48A_SCENARIO_IDS,
    P277_PILLAR_48B_SCENARIO_IDS,
    P277_PINNED_FX3_APPFW_702_BYTES,
    P277_PINNED_FX3_BACKUP_BIN_BYTES,
    P277_PINNED_FX3_BACKUP_BIN_SHA256,
    P277_PINNED_FX3_LIBSAVELOADSETTINGS_SO_BYTES,
    P277_PINNED_FX6_APPFW_601_BYTES,
    P277_PINNED_FX6_BACKUP_CN1_BIN_BYTES,
    P277_PINNED_FX6_BACKUP_NTSC_BIN_BYTES,
    P277_POWER_SAVE_9_DEACTIVATION_CONDITIONS,
    P277_POWER_SAVE_MONITOR_4_MODES,
    P277_POWER_SAVE_MONITOR_BKID,
    P277_POWER_SAVE_MONITOR_ENUM_MAP,
    P277_POWER_SAVE_MONITOR_RESID16,
    P277_POWER_SAVE_MONITOR_RESID16_MAP,
    P277_POWER_SAVE_START_TIME_DEFAULT,
    P277_POWER_SAVE_START_TIME_MODES,
    P277_POWER_SETTING_OPTION_MENU_PATH,
    P277_RECOVERY_SAFE_POWER_SAVE_START_TIMES,
    P277_RESET_ACTIONS,
    P277_SIBLING_POWER_SAVE_MONITOR_DEFAULT,
    P277_SIBLING_POWER_SAVE_MONITOR_MODELS,
    P277_SLOT1_FORMAT_HARD_LOCKED,
    P277_SLOT1_VAULT_DELETE_EVENTS,
    P277_SLOT1_VAULT_MUTATION_BYTES,
    P277_STAGE_B_4LANG_ORDER,
    P277_STAGE_B_4LANG_UXC_LTT_DRIFT_EVENTS,
    P277_STAGE_B_4LANG_UXC_LTT_TABLE,
    P277_STATUS_FAIL_48OF48_AGGREGATOR,
    P277_STATUS_FAIL_PILLAR48_SUITE,
    P277_STATUS_REJECTED_PILLAR_48A,
    P277_STATUS_REJECTED_PILLAR_48B,
    P277_STATUS_VERIFIED_48OF48_AGGREGATOR,
    P277_STATUS_VERIFIED_PILLAR48_SUITE,
    P277_STATUS_VERIFIED_PILLAR_48A,
    P277_STATUS_VERIFIED_PILLAR_48B,
    P277_TIER0_SURFACE_COUNT,
    P277_UNSAFE_POWER_SAVE_SLEEP_INTERFERENCE_EVENTS,
    P277_VOLUME_SETTINGS_BKID,
    P277_VOLUME_SETTINGS_DEFAULT,
    P277_VOLUME_SETTINGS_MAX,
    P277_VOLUME_SETTINGS_MENU_PATH,
    P277_VOLUME_SETTINGS_MIN,
    P277_VOLUME_SETTINGS_RESID16,
    P277_XLRH1_ACOUSTIC_FEEDBACK_VIOLATIONS,
    P277_XLRH1_SAFE_INTERNAL_SPEAKER_MAX_VOLUME,
    PASSIVE_TX_BYTES_EMITTED,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHASE277_PHASE_NUMBER,
    PHASE277_SCHEMA,
    PHASE277_VERSION,
    PHYSICAL_DEVICE_WRITES,
    PHYSICAL_USB_PACKETS_EMITTED,
    RAW_FIRMWARE_BYTES_LEAKED,
    READ_ONLY_DONOR_ACCESS,
    RPMB_COUNTER_INCREMENTS,
    SPI_NOR_WRITE_AUTHORIZED,
    Master48PillarRecoveryReport,
    Pillar48StandaloneReport,
    PowerSaveMonitorLanguageVaultSpec,
    Volume4chMonDeleteConfirmVaultSpec,
    build_default_safe_power_save_monitor_language_vault_spec,
    build_default_safe_volume_4ch_mon_delete_confirm_vault_spec,
    compute_expected_pillar48a_reset_state,
    compute_expected_pillar48b_reset_and_slot1_vault_guard,
    compute_expected_power_save_by_monitor_effective_state,
    compute_expected_power_save_start_time_recovery_guard,
    compute_expected_xlrh1_speaker_feedback_guard,
    evaluate_48pillar_recovery_master,
    evaluate_power_save_monitor_language_vault,
    evaluate_realhw_48pillar_recovery_master,
    evaluate_volume_4ch_mon_delete_confirm_vault,
    inspect_phase277_donors_readonly,
    run_pillar48_standalone_suite,
    run_pillar48a_power_save_monitor_start_time_language_vault_6_scenario_suite,
    run_pillar48b_volume_4ch_mon_delete_confirm_slot1_vault_6_scenario_suite,
    verify_48pillar_recovery_suite,
    verify_power_save_monitor_language_volume_delete_and_vault,
    verify_power_save_monitor_language_volume_delete_vault,
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _cli_budget_seconds() -> float:
    if os.environ.get("GITHUB_ACTIONS", "").strip().lower() == "true":
        return 15.0
    return 2.5


class TestPhase277Realhw48PillarVerifier(unittest.TestCase):
    """76 comprehensive dual-mode unit tests for Phase 277 Pillar 48 & 48/48 Master."""

    # ------------------------------------------------------------------
    # 1. Safety Invariants, Module Exports & 48-Pillar Spec Integrity
    # ------------------------------------------------------------------

    def test_01_hard_locked_zero_write_safety_constants(self) -> None:
        self.assertEqual(PHASE277_PHASE_NUMBER, 277)
        self.assertEqual(
            PHASE277_SCHEMA,
            "realhw_48pillar_power_save_monitor_language_volume_delete_vault_verifier_v1",
        )
        self.assertEqual(PHASE277_VERSION, "1.0.0")
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
        self.assertTrue(READ_ONLY_DONOR_ACCESS)
        self.assertTrue(CNFLASHA_USERSPACE_WRITE_BLOCKED)
        self.assertTrue(P277_SLOT1_FORMAT_HARD_LOCKED)
        self.assertEqual(OTP_FUSE_TOUCHES, 0)
        self.assertEqual(OTP_FUSE_WRITES, 0)
        self.assertEqual(RPMB_COUNTER_INCREMENTS, 0)
        self.assertEqual(PASSIVE_TX_BYTES_EMITTED, 0)
        self.assertEqual(PHYSICAL_USB_PACKETS_EMITTED, 0)
        self.assertEqual(PHYSICAL_DEVICE_WRITES, 0)
        self.assertEqual(RAW_FIRMWARE_BYTES_LEAKED, 0)

    def test_02_wave46_zero_violation_constants(self) -> None:
        self.assertFalse(P277_FX3_UI_EXPOSES_POWER_SAVE_BY_MONITOR)
        self.assertFalse(P277_FX6_UI_EXPOSES_POWER_SAVE_BY_MONITOR)
        self.assertEqual(P277_LEGACY_POWER_SAVE_MONITOR_SPOOF_EVENTS, 0)
        self.assertEqual(P277_UNSAFE_POWER_SAVE_SLEEP_INTERFERENCE_EVENTS, 0)
        self.assertEqual(P277_BK_LANG_PARITY_DRIFT_EVENTS, 0)
        self.assertEqual(P277_STAGE_B_4LANG_UXC_LTT_DRIFT_EVENTS, 0)
        self.assertEqual(P277_XLRH1_ACOUSTIC_FEEDBACK_VIOLATIONS, 0)
        self.assertEqual(P277_AUDIO_MON_4CH_HDMI_CONFUSION_EVENTS, 0)
        self.assertEqual(P277_DESTRUCTIVE_DELETE_CONFIRM_DRIFT_EVENTS, 0)
        self.assertEqual(P277_SLOT1_VAULT_DELETE_EVENTS, 0)
        self.assertEqual(P277_SLOT1_VAULT_MUTATION_BYTES, 0)

    def test_03_package_exports_and_all_include_phase277_symbols(self) -> None:
        for sym in (
            "MASTER_48_PILLAR_COUNT",
            "MASTER_48_PILLAR_IDS",
            "MASTER_48_PILLAR_SPECS",
            "PHASE277_SCHEMA",
            "Master48PillarRecoveryReport",
            "evaluate_realhw_48pillar_recovery_master",
            "evaluate_48pillar_recovery_master",
            "verify_48pillar_recovery_suite",
            "verify_power_save_monitor_language_volume_delete_vault",
            "run_pillar48_standalone_suite",
        ):
            self.assertTrue(hasattr(fx3_recovery, sym), f"Missing package export: {sym}")
            self.assertIn(sym, fx3_recovery.__all__)

    def test_04_master_48_pillar_specs_extend_47_cleanly(self) -> None:
        self.assertEqual(MASTER_48_PILLAR_COUNT, 48)
        self.assertEqual(len(MASTER_48_PILLAR_SPECS), 48)
        self.assertGreaterEqual(len(MASTER_48_PILLAR_SPECS), 48)
        self.assertEqual(MASTER_48_PILLAR_SPECS[:47], MASTER_47_PILLAR_SPECS)
        self.assertEqual(
            MASTER_48_PILLAR_SPECS[47],
            (
                48,
                "pillar_48_power_save_monitor_language_volume_delete_vault",
                "Phase 277 (48/48)",
                "fx3_recovery.realhw_48pillar_power_save_monitor_language_volume_delete_vault_verifier",
            ),
        )
        self.assertEqual(len(set(MASTER_48_PILLAR_IDS)), 48)

    def test_05_default_safe_builders_return_expected_dataclasses(self) -> None:
        s48a = build_default_safe_power_save_monitor_language_vault_spec()
        s48b = build_default_safe_volume_4ch_mon_delete_confirm_vault_spec()
        self.assertIsInstance(s48a, PowerSaveMonitorLanguageVaultSpec)
        self.assertIsInstance(s48b, Volume4chMonDeleteConfirmVaultSpec)
        self.assertEqual(s48a.camera_model, P277_FX3_MODEL_NAME)
        self.assertEqual(s48a.camera_model_id, 0x91030080)
        self.assertEqual(s48b.pre_volume_settings, 7)

    # ------------------------------------------------------------------
    # 2. Bounded O_RDONLY Donor Inspection & Clean-Room Fallback
    # ------------------------------------------------------------------

    def test_06_inspect_phase277_donors_readonly_active_mode(self) -> None:
        snap = inspect_phase277_donors_readonly()
        self.assertTrue(snap.all_donors_present)
        self.assertEqual(snap.donor_files_inspected, 18)
        self.assertEqual(snap.raw_firmware_bytes_leaked, 0)
        self.assertIn(snap.verification_mode, ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"))
        self.assertTrue(snap.under_0_15s_budget)
        self.assertEqual(len(snap.artifacts), 18)
        self.assertTrue(all(a.present and a.matches_pinned for a in snap.artifacts))

    def test_07_inspect_phase277_donors_explicit_clean_room(self) -> None:
        snap = inspect_phase277_donors_readonly(force_clean_room=True)
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(snap.all_donors_present)
        self.assertEqual(snap.donor_files_inspected, 18)
        self.assertEqual(snap.raw_firmware_bytes_leaked, 0)
        self.assertTrue(all(a.read_mode == "CLEAN_ROOM_SYNTHETIC" for a in snap.artifacts))

    def test_08_inspect_phase277_donors_env_fx3_clean_room_test(self) -> None:
        with mock.patch.dict(os.environ, {P277_ENV_CLEAN_ROOM_TEST: "1"}):
            snap = inspect_phase277_donors_readonly()
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(snap.all_donors_present)

    def test_09_inspect_phase277_donors_env_fx3_fx6_force_clean_room(self) -> None:
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            snap = inspect_phase277_donors_readonly()
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(snap.all_donors_present)

    def test_10_inspect_phase277_donors_missing_local_falls_back_to_clean_room(self) -> None:
        with mock.patch.object(p277, "resolve_donor_path", return_value=None):
            with mock.patch.dict(os.environ, {}, clear=False):
                os.environ.pop(P277_ENV_CLEAN_ROOM_TEST, None)
                os.environ.pop("FX3_FX6_FORCE_CLEAN_ROOM", None)
                snap = inspect_phase277_donors_readonly(force_clean_room=False)
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(snap.all_donors_present)
        self.assertEqual(snap.donor_files_inspected, 18)

    def test_11_ci_donor_budget_relaxes_to_0_50s(self) -> None:
        with mock.patch.dict(os.environ, {"GITHUB_ACTIONS": "true"}):
            self.assertEqual(p277._donor_inspect_budget_seconds(), P277_DONOR_INSPECT_CI_BUDGET_SECONDS)
            snap = inspect_phase277_donors_readonly(force_clean_room=True)
            self.assertEqual(snap.budget_seconds_applied, 0.50)

    def test_12_pinned_donor_byte_sizes_and_bk_lang_markers(self) -> None:
        self.assertEqual(P277_PINNED_FX3_APPFW_702_BYTES, 79015712)
        self.assertEqual(P277_PINNED_FX6_APPFW_601_BYTES, 50520424)
        self.assertEqual(P277_PINNED_FX3_LIBSAVELOADSETTINGS_SO_BYTES, 18760)
        self.assertEqual(P277_PINNED_FX3_BACKUP_BIN_BYTES, 2229740)
        self.assertEqual(P277_PINNED_FX6_BACKUP_NTSC_BIN_BYTES, 2253333)
        self.assertEqual(P277_PINNED_FX6_BACKUP_CN1_BIN_BYTES, 2253333)
        snap = inspect_phase277_donors_readonly()
        by_id = {a.artifact_id: a for a in snap.artifacts}
        self.assertIn("BK_LANG=0x00@0x90ff0", by_id["fx3_backup_bin"].marker_summary)
        self.assertIn("BK_LANG=0x00@0x89242", by_id["fx6_backup_ntsc_bin"].marker_summary)
        self.assertIn("BK_LANG=0x19@0x89242", by_id["fx6_backup_cn1_bin"].marker_summary)

    # ------------------------------------------------------------------
    # 3. Pillar 48A — [Power Save by Monitor] Reality Split & 4-Mode UXC
    # ------------------------------------------------------------------

    def test_13_fx3_power_setting_option_exposes_exact_2_items_only(self) -> None:
        self.assertEqual(P277_POWER_SETTING_OPTION_MENU_PATH, ("MENU", "Setup", "Power Setting Option"))
        self.assertEqual(
            P277_FX3_POWER_SETTING_EXACT_2_SUBITEMS,
            ("Power Save Start Time", "Auto Power OFF Temp."),
        )
        self.assertFalse(P277_FX3_UI_EXPOSES_POWER_SAVE_BY_MONITOR)
        self.assertFalse(P277_FX6_UI_EXPOSES_POWER_SAVE_BY_MONITOR)
        self.assertEqual(P277_FX3_HELPGUIDE_ID, "ilc/2210")
        self.assertEqual(P277_FX3_FW_VERSION, "7.02")
        self.assertEqual(P277_FX6_DONOR_MODEL_NAME, "ILME-FX6")
        self.assertEqual(P277_FX6_DONOR_FW_VERSION, "6.01")

    def test_14_appfw_monitor_power_linkage_4_modes_and_resid16(self) -> None:
        self.assertEqual(P277_POWER_SAVE_MONITOR_BKID, "BKID_APP_setting_monitor_power_linkage")
        self.assertEqual(P277_POWER_SAVE_MONITOR_RESID16, 0x60B9)
        self.assertEqual(
            P277_POWER_SAVE_MONITOR_4_MODES,
            ("Both Linked", "Open: Return", "Close: Power Save", "Does Not Link"),
        )
        self.assertEqual(P277_POWER_SAVE_MONITOR_RESID16_MAP["Both Linked"], 0x6DB5)
        self.assertEqual(P277_POWER_SAVE_MONITOR_RESID16_MAP["Open: Return"], 0x6DB6)
        self.assertEqual(P277_POWER_SAVE_MONITOR_RESID16_MAP["Close: Power Save"], 0x60A8)
        self.assertEqual(P277_POWER_SAVE_MONITOR_RESID16_MAP["Does Not Link"], 0x6B2E)
        self.assertEqual(
            P277_POWER_SAVE_MONITOR_ENUM_MAP["Both Linked"],
            "EXTERN_VAL_MONITOR_POWER_LINKAGE_ON_ALL",
        )
        self.assertEqual(
            P277_POWER_SAVE_MONITOR_ENUM_MAP["Does Not Link"],
            "EXTERN_VAL_MONITOR_POWER_LINKAGE_OFF",
        )
        self.assertEqual(P277_SIBLING_POWER_SAVE_MONITOR_DEFAULT, "Both Linked")

    def test_15_helper_fx3_does_not_sleep_when_lcd_folded_inward(self) -> None:
        for mode in P277_POWER_SAVE_MONITOR_4_MODES:
            ui_exp, sleeps, h_safe = compute_expected_power_save_by_monitor_effective_state(
                camera_model="ILME-FX3",
                monitor_power_linkage_mode=mode,
                lcd_folded_inward=True,
                headless_hdmi_capture_active=True,
            )
            self.assertFalse(ui_exp)
            self.assertFalse(sleeps)
            self.assertTrue(h_safe)

    def test_16_helper_sibling_bodies_headless_hdmi_rule(self) -> None:
        for body in P277_SIBLING_POWER_SAVE_MONITOR_MODELS:
            ui_exp, sleeps_bl, safe_bl = compute_expected_power_save_by_monitor_effective_state(
                camera_model=body,
                monitor_power_linkage_mode="Both Linked",
                lcd_folded_inward=True,
                headless_hdmi_capture_active=True,
            )
            self.assertTrue(ui_exp)
            self.assertTrue(sleeps_bl)
            self.assertFalse(safe_bl)

            _, sleeps_dnl, safe_dnl = compute_expected_power_save_by_monitor_effective_state(
                camera_model=body,
                monitor_power_save_mode="Does Not Link" if False else "Does Not Link",
                monitor_power_linkage_mode="Does Not Link",
                lcd_folded_inward=True,
                headless_hdmi_capture_active=True,
            ) if False else compute_expected_power_save_by_monitor_effective_state(
                camera_model=body,
                monitor_power_linkage_mode="Does Not Link",
                lcd_folded_inward=True,
                headless_hdmi_capture_active=True,
            )
            self.assertFalse(sleeps_dnl)
            self.assertTrue(safe_dnl)

            _, sleeps_or, safe_or = compute_expected_power_save_by_monitor_effective_state(
                camera_model=body,
                monitor_power_linkage_mode="Open: Return",
                lcd_folded_inward=True,
                headless_hdmi_capture_active=True,
            )
            self.assertFalse(sleeps_or)
            self.assertTrue(safe_or)

    def test_17_reject_fx3_exposing_power_save_by_monitor_in_ui(self) -> None:
        rep = evaluate_power_save_monitor_language_vault(
            PowerSaveMonitorLanguageVaultSpec(fx3_ui_exposes_power_save_by_monitor=True)
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P277_BLOCKED_POWER_SAVE_MONITOR_REALITY_SPLIT_OR_SPOOF)
        self.assertGreaterEqual(rep.legacy_power_save_monitor_spoof_events, 1)

    def test_18_reject_fx6_exposing_power_save_by_monitor_in_ui(self) -> None:
        rep = evaluate_power_save_monitor_language_vault(
            PowerSaveMonitorLanguageVaultSpec(fx6_ui_exposes_power_save_by_monitor=True)
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P277_BLOCKED_POWER_SAVE_MONITOR_REALITY_SPLIT_OR_SPOOF)

    def test_19_reject_spoofed_open_on_close_off_label(self) -> None:
        rep = evaluate_power_save_monitor_language_vault(
            PowerSaveMonitorLanguageVaultSpec(
                sibling_power_save_by_monitor_mode=P277_FORBIDDEN_POWER_SAVE_MONITOR_SPOOF_LABEL,
                legacy_power_save_monitor_spoof_events=1,
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P277_BLOCKED_POWER_SAVE_MONITOR_REALITY_SPLIT_OR_SPOOF)

    def test_20_reject_sibling_both_linked_or_close_power_save_during_headless_hdmi(self) -> None:
        for bad_mode in ("Both Linked", "Close: Power Save"):
            rep = evaluate_power_save_monitor_language_vault(
                PowerSaveMonitorLanguageVaultSpec(
                    sibling_power_save_by_monitor_mode=bad_mode,
                    sibling_lcd_folded_inward=True,
                    headless_hdmi_capture_active=True,
                )
            )
            self.assertFalse(rep.passed)
            self.assertEqual(rep.block_code, P277_BLOCKED_POWER_SAVE_MONITOR_REALITY_SPLIT_OR_SPOOF)

    # ------------------------------------------------------------------
    # 4. Pillar 48A — [Power Save Start Time] 9-Deactivation Recovery Guard
    # ------------------------------------------------------------------

    def test_21_power_save_start_time_and_9_deactivation_conditions_exact(self) -> None:
        self.assertEqual(
            P277_POWER_SAVE_START_TIME_MODES,
            ("Off", "30 Min", "5 Min", "2 Min", "1 Min", "10 Sec"),
        )
        self.assertEqual(P277_POWER_SAVE_START_TIME_DEFAULT, "5 Min")
        self.assertEqual(P277_RECOVERY_SAFE_POWER_SAVE_START_TIMES, ("Off", "30 Min"))
        self.assertEqual(P277_AUTO_POWER_OFF_TEMP_MODES, ("Standard", "High"))
        self.assertEqual(P277_AUTO_POWER_OFF_TEMP_DEFAULT, "Standard")
        self.assertEqual(len(P277_POWER_SAVE_9_DEACTIVATION_CONDITIONS), 9)

    def test_22_airgapped_battery_tier0_allows_off_and_30min(self) -> None:
        for safe_time in ("Off", "30 Min"):
            rep = evaluate_power_save_monitor_language_vault(
                PowerSaveMonitorLanguageVaultSpec(
                    airgapped_battery_tier0_session=True,
                    active_deactivation_conditions=(),
                    pre_power_save_start_time=safe_time,
                    post_power_save_start_time=safe_time,
                )
            )
            self.assertTrue(rep.passed, f"Expected pass for {safe_time}: {rep.errors}")

    def test_23_airgapped_battery_tier0_rejects_short_sleep_timers_without_9cond(self) -> None:
        for bad_time in ("5 Min", "2 Min", "1 Min", "10 Sec"):
            rep = evaluate_power_save_monitor_language_vault(
                PowerSaveMonitorLanguageVaultSpec(
                    airgapped_battery_tier0_session=True,
                    active_deactivation_conditions=(),
                    pre_power_save_start_time=bad_time,
                    post_power_save_start_time=bad_time,
                )
            )
            self.assertFalse(rep.passed)
            self.assertEqual(rep.block_code, P277_BLOCKED_POWER_SAVE_START_TIME_RECOVERY_SLEEP)
            self.assertGreaterEqual(rep.unsafe_power_save_sleep_interference_events, 1)

    def test_24_every_one_of_9_deactivation_conditions_bypasses_idle_sleep(self) -> None:
        for cond in P277_POWER_SAVE_9_DEACTIVATION_CONDITIONS:
            bypassed, safe = compute_expected_power_save_start_time_recovery_guard(
                configured_power_save_start_time="5 Min",
                active_deactivation_conditions=(cond,),
                airgapped_battery_tier0_session=True,
            )
            self.assertTrue(bypassed)
            self.assertTrue(safe)
            rep = evaluate_power_save_monitor_language_vault(
                PowerSaveMonitorLanguageVaultSpec(
                    airgapped_battery_tier0_session=True,
                    active_deactivation_conditions=(cond,),
                    pre_power_save_start_time="5 Min",
                    post_power_save_start_time="5 Min",
                )
            )
            self.assertTrue(rep.passed, f"Expected bypass for condition {cond}: {rep.errors}")

    def test_25_reject_unknown_deactivation_condition(self) -> None:
        rep = evaluate_power_save_monitor_language_vault(
            PowerSaveMonitorLanguageVaultSpec(
                active_deactivation_conditions=("Nonexistent Mock Condition",),
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P277_BLOCKED_POWER_SAVE_START_TIME_RECOVERY_SLEEP)

    # ------------------------------------------------------------------
    # 5. Pillar 48A — [Language] BK_LANG 0x02cf019c & Stage-B 4-Lang Parity
    # ------------------------------------------------------------------

    def test_26_bk_lang_constants_fx3_34_vs_fx6_29(self) -> None:
        self.assertEqual(P277_LANGUAGE_MENU_PATH, ("MENU", "Setup", "Area/Date", "Language"))
        self.assertEqual(P277_LANGUAGE_BK_KEY, 0x02CF019C)
        self.assertEqual(P277_LANGUAGE_RESID16, 0xE397)
        self.assertEqual(P277_FX6_LANGUAGE_RESID16, 0x2F4D)
        self.assertEqual(P277_LANGUAGE_BKID_FX3, "BKID_APP_setting_language")
        self.assertEqual(P277_LANGUAGE_BKID_FX6, "BKID_APP_SETTING_LANGUAGE")
        self.assertEqual(P277_LANGUAGE_DEFAULT, "—")
        self.assertEqual(P277_FX3_LANGUAGE_COUNT, 34)
        self.assertEqual(P277_FX6_LANGUAGE_COUNT, 29)
        self.assertEqual(P277_FX3_BACKUP_BK_LANG_OFFSET, 0x90FF0)
        self.assertEqual(P277_FX3_BACKUP_BK_LANG_DEFAULT_VALUE, 0x00)
        self.assertEqual(P277_FX6_BACKUP_BK_LANG_OFFSET, 0x89242)
        self.assertEqual(P277_FX6_BACKUP_NTSC_BK_LANG_VALUE, 0x00)
        self.assertEqual(P277_FX6_BACKUP_CN1_BK_LANG_VALUE, 0x19)

    def test_27_all_4_stage_b_languages_uxc_and_ltt_table_pass(self) -> None:
        for lang_key in P277_STAGE_B_4LANG_ORDER:
            row = P277_STAGE_B_4LANG_UXC_LTT_TABLE[lang_key]
            rep = evaluate_power_save_monitor_language_vault(
                PowerSaveMonitorLanguageVaultSpec(
                    stage_b_selected_lang=lang_key,
                    stage_b_bank_id=row["bank_id"],
                    stage_b_font_str_pair=row["font_str_pair"],
                    stage_b_ltt_font=row["ltt_font"],
                )
            )
            self.assertTrue(rep.passed, f"Expected pass for Stage-B lang {lang_key}: {rep.errors}")

    def test_28_reject_bk_lang_seed_or_language_count_drift(self) -> None:
        for bad_kwargs in (
            {"fx3_language_count": 29},
            {"fx6_language_count": 34},
            {"fx3_backup_bk_lang_val": 0x19},
            {"fx6_ntsc_bk_lang_val": 0x01},
            {"fx6_cn1_bk_lang_val": 0x00},
            {"bk_lang_key": 0xDEADBEEF},
        ):
            rep = evaluate_power_save_monitor_language_vault(
                PowerSaveMonitorLanguageVaultSpec(**bad_kwargs)
            )
            self.assertFalse(rep.passed)
            self.assertEqual(rep.block_code, P277_BLOCKED_BK_LANG_OR_STAGE_B_4LANG_PARITY_DRIFT)

    def test_29_reject_stage_b_uxc_or_ltt_bank_mismatch(self) -> None:
        for bad_kwargs in (
            {"stage_b_selected_lang": "french"},
            {"stage_b_bank_id": 0},
            {"stage_b_font_str_pair": (4, 4)},
            {"stage_b_ltt_font": "UniversOTS-SJ_wIcon.ltt"},
        ):
            rep = evaluate_power_save_monitor_language_vault(
                PowerSaveMonitorLanguageVaultSpec(**bad_kwargs)
            )
            self.assertFalse(rep.passed)
            self.assertEqual(rep.block_code, P277_BLOCKED_BK_LANG_OR_STAGE_B_4LANG_PARITY_DRIFT)

    # ------------------------------------------------------------------
    # 6. Pillar 48A — Setup Reset Persistence, CAMSET Restore & H0 == H3
    # ------------------------------------------------------------------

    def test_30_setup_survives_camera_and_network_reset_but_clears_on_initialize(self) -> None:
        for act in ("NONE", "Camera Settings Reset", "Reset Network Set."):
            out = compute_expected_pillar48a_reset_state(
                pre_power_save_start_time="30 Min",
                pre_auto_power_off_temp="High",
                pre_sibling_power_save_by_monitor="Open: Return",
                pre_language="Japanese",
                reset_action=act,
            )
            self.assertEqual(out, ("30 Min", "High", "Open: Return", "Japanese"))
        out_init = compute_expected_pillar48a_reset_state(
            pre_power_save_start_time="30 Min",
            pre_auto_power_off_temp="High",
            pre_sibling_power_save_by_monitor="Open: Return",
            pre_language="Japanese",
            reset_action="Initialize",
        )
        self.assertEqual(out_init, ("5 Min", "Standard", "Both Linked", "—"))

    def test_31_reject_camera_settings_reset_wiping_setup_power_or_language(self) -> None:
        rep = evaluate_power_save_monitor_language_vault(
            PowerSaveMonitorLanguageVaultSpec(
                active_deactivation_conditions=("USB power supply",),
                reset_action="Camera Settings Reset",
                pre_power_save_start_time="30 Min",
                pre_language="Japanese",
                post_power_save_start_time="5 Min",
                post_language="—",
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P277_BLOCKED_SETUP_LANGUAGE_POWER_RESET_SCOPE_DRIFT)

    def test_32_reject_invalid_camset_load_source_or_slot(self) -> None:
        for bad_kwargs in (
            {"camset_load_after_reset": True, "camset_slot": 2},
            {"camset_load_after_reset": True, "camset_filename": "BAD.DAT"},
            {"camset_load_after_reset": True, "camset_source_model": "ILME-FX6"},
            {"camset_load_after_reset": True, "camset_read_only_load": False},
        ):
            rep = evaluate_power_save_monitor_language_vault(
                PowerSaveMonitorLanguageVaultSpec(**bad_kwargs)
            )
            self.assertFalse(rep.passed)
            self.assertEqual(rep.block_code, P277_BLOCKED_SETUP_LANGUAGE_POWER_RESET_SCOPE_DRIFT)

    def test_33_reject_persistent_overlay_escape_and_tier0_h0_h3_drift_48a(self) -> None:
        rep_ovl = evaluate_power_save_monitor_language_vault(
            PowerSaveMonitorLanguageVaultSpec(overlay_dir="/setting/overlay")
        )
        self.assertFalse(rep_ovl.passed)
        self.assertEqual(rep_ovl.block_code, P277_BLOCKED_PERSISTENT_OVERLAY_ESCAPE)

        rep_h03 = evaluate_power_save_monitor_language_vault(
            PowerSaveMonitorLanguageVaultSpec(
                backup_bin_h3_sha256="0" * 64,
                tier0_surfaces_h0_h3_matched=15,
            )
        )
        self.assertFalse(rep_h03.passed)
        self.assertEqual(rep_h03.block_code, P277_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT)

    def test_34_reject_invalid_pillar48a_camera_and_unlock_request(self) -> None:
        rep_bad = evaluate_power_save_monitor_language_vault(
            PowerSaveMonitorLanguageVaultSpec(camera_model="ILCE-7M4")
        )
        self.assertFalse(rep_bad.passed)
        self.assertEqual(rep_bad.block_code, P277_BLOCKED_INVALID_PILLAR48A_SPEC)

        rep_unlock = evaluate_power_save_monitor_language_vault(
            PowerSaveMonitorLanguageVaultSpec(persistent_write_unlock_requested=True)
        )
        self.assertFalse(rep_unlock.passed)
        self.assertEqual(rep_unlock.block_code, P277_BLOCKED_SAFETY_POLICY_VIOLATION)

    # ------------------------------------------------------------------
    # 7. Pillar 48B — [Volume Settings] (0..15, Default 7) & XLR-H1 Guard
    # ------------------------------------------------------------------

    def test_35_volume_settings_constants_and_distinct_audio_signals(self) -> None:
        self.assertEqual(
            P277_VOLUME_SETTINGS_MENU_PATH,
            ("MENU", "Setup", "Sound Option", "Volume Settings"),
        )
        self.assertEqual(P277_VOLUME_SETTINGS_BKID, "BKID_APP_setting_volume_settings")
        self.assertEqual(P277_FX6_VOLUME_SETTINGS_BKID, "BKID_APP_SETTING_MONITOR_VOLUME")
        self.assertEqual(P277_VOLUME_SETTINGS_RESID16, 0xE8C9)
        self.assertEqual(P277_AUDIO_SIGNALS_RESID16, 0x7AF6)
        self.assertEqual(P277_VOLUME_SETTINGS_MIN, 0)
        self.assertEqual(P277_VOLUME_SETTINGS_MAX, 15)
        self.assertEqual(P277_VOLUME_SETTINGS_DEFAULT, 7)

    def test_36_all_discrete_volumes_0_to_15_pass_on_headphone(self) -> None:
        for vol in range(0, 16):
            rep = evaluate_volume_4ch_mon_delete_confirm_vault(
                Volume4chMonDeleteConfirmVaultSpec(
                    pre_volume_settings=vol,
                    post_volume_settings=vol,
                    playback_output_target="Headphone 3.5mm",
                )
            )
            self.assertTrue(rep.passed, f"Expected pass for volume={vol}: {rep.errors}")

    def test_37_reject_out_of_range_volume_below_0_or_above_15(self) -> None:
        for bad_vol in (-1, 16, 31):
            rep = evaluate_volume_4ch_mon_delete_confirm_vault(
                Volume4chMonDeleteConfirmVaultSpec(
                    pre_volume_settings=bad_vol,
                    post_volume_settings=bad_vol,
                )
            )
            self.assertFalse(rep.passed)
            self.assertEqual(rep.block_code, P277_BLOCKED_VOLUME_RANGE_OR_XLRH1_FEEDBACK)

    def test_38_xlrh1_acoustic_feedback_guard_allows_low_speaker_or_separated(self) -> None:
        for vol in range(0, P277_XLRH1_SAFE_INTERNAL_SPEAKER_MAX_VOLUME + 1):
            safe, clamped = compute_expected_xlrh1_speaker_feedback_guard(
                volume_level=vol,
                xlrh1_mic_attached=True,
                playback_output_target="Internal Speaker",
                xlrh1_acoustic_separation_active=False,
            )
            self.assertTrue(safe)
            self.assertEqual(clamped, vol)
        rep_sep = evaluate_volume_4ch_mon_delete_confirm_vault(
            Volume4chMonDeleteConfirmVaultSpec(
                xlrh1_mic_attached=True,
                playback_output_target="Internal Speaker",
                xlrh1_acoustic_separation_active=True,
                pre_volume_settings=12,
                post_volume_settings=12,
            )
        )
        self.assertTrue(rep_sep.passed)

    def test_39_xlrh1_acoustic_feedback_blocks_high_speaker_without_separation(self) -> None:
        for vol in range(P277_XLRH1_SAFE_INTERNAL_SPEAKER_MAX_VOLUME + 1, 16):
            safe, clamped = compute_expected_xlrh1_speaker_feedback_guard(
                volume_level=vol,
                xlrh1_mic_attached=True,
                playback_output_target="Internal Speaker",
                xlrh1_acoustic_separation_active=False,
            )
            self.assertFalse(safe)
            self.assertEqual(clamped, P277_XLRH1_SAFE_INTERNAL_SPEAKER_MAX_VOLUME)
        rep = evaluate_volume_4ch_mon_delete_confirm_vault(
            Volume4chMonDeleteConfirmVaultSpec(
                xlrh1_mic_attached=True,
                playback_output_target="Internal Speaker",
                xlrh1_acoustic_separation_active=False,
                pre_volume_settings=10,
                post_volume_settings=10,
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P277_BLOCKED_VOLUME_RANGE_OR_XLRH1_FEEDBACK)
        self.assertGreaterEqual(rep.xlrh1_acoustic_feedback_violations, 1)

    # ------------------------------------------------------------------
    # 8. Pillar 48B — [4ch Audio Monitoring] (5 Routes) vs HDMI Output
    # ------------------------------------------------------------------

    def test_40_audio_monitoring_5_routes_resid16_and_enums(self) -> None:
        self.assertEqual(
            P277_AUDIO_MONITORING_MENU_PATH,
            ("MENU", "Setup", "Sound Option", "4ch Audio Monitoring"),
        )
        self.assertEqual(P277_AUDIO_MONITORING_BKID, "BKID_APP_setting_audio_monitoring_ch")
        self.assertEqual(P277_HDMI_4CH_OUTPUT_BKID, "BKID_APP_setting_4ch_output_ch")
        self.assertEqual(P277_HDMI_4CH_OUTPUT_RESID16, 0x6AA0)
        self.assertEqual(P277_HDMI_4CH_OUTPUT_MODES, ("CH1/CH2", "CH3/CH4"))
        self.assertEqual(
            P277_AUDIO_MONITORING_5_ROUTES,
            ("CH1/CH2", "CH3/CH4", "CH1+3/CH2+4", "CH1/CH1", "CH2/CH2"),
        )
        self.assertEqual(P277_AUDIO_MONITORING_DEFAULT, "CH1/CH2")
        self.assertEqual(P277_AUDIO_MONITORING_RESID16_MAP["CH1/CH2"], 0x713B)
        self.assertEqual(P277_AUDIO_MONITORING_RESID16_MAP["CH3/CH4"], 0x6BF6)
        self.assertEqual(P277_AUDIO_MONITORING_RESID16_MAP["CH1+3/CH2+4"], 0x6C2E)
        self.assertEqual(P277_AUDIO_MONITORING_RESID16_MAP["CH1/CH1"], 0x6F9C)
        self.assertEqual(P277_AUDIO_MONITORING_RESID16_MAP["CH2/CH2"], 0x7A26)
        self.assertEqual(P277_AUDIO_MONITORING_ENUM_MAP["CH1+3/CH2+4"], "AUDIO_MONITORING_CH_MIX_ALL")
        self.assertEqual(P277_HEADPHONE_35MM_MAX_CHANNELS, 2)

    def test_41_all_5_audio_monitoring_routes_pass_independent_of_hdmi_4ch_output(self) -> None:
        for route in P277_AUDIO_MONITORING_5_ROUTES:
            for hdmi_out in P277_HDMI_4CH_OUTPUT_MODES:
                rep = evaluate_volume_4ch_mon_delete_confirm_vault(
                    Volume4chMonDeleteConfirmVaultSpec(
                        pre_audio_monitoring_ch=route,
                        post_audio_monitoring_ch=route,
                        hdmi_4ch_output_ch=hdmi_out,
                    )
                )
                self.assertTrue(rep.passed, f"Expected pass for route={route}, hdmi={hdmi_out}")

    def test_42_reject_invalid_4ch_route_headphone_4ch_or_hdmi_confusion(self) -> None:
        for bad_kwargs in (
            {"pre_audio_monitoring_ch": "CH3/CH3", "post_audio_monitoring_ch": "CH3/CH3"},
            {"headphone_35mm_channels": 4},
            {"hdmi_4ch_output_ch": "CH1+3/CH2+4"},
            {"audio_mon_4ch_hdmi_confusion_events": 1},
        ):
            rep = evaluate_volume_4ch_mon_delete_confirm_vault(
                Volume4chMonDeleteConfirmVaultSpec(**bad_kwargs)
            )
            self.assertFalse(rep.passed)
            self.assertEqual(rep.block_code, P277_BLOCKED_AUDIO_MON_4CH_OR_HDMI_CONFUSION)

    # ------------------------------------------------------------------
    # 9. Pillar 48B — [Delete confirm.] & Slot-1 Delete/Format Firewall
    # ------------------------------------------------------------------

    def test_43_delete_confirm_and_delete_twice_constants(self) -> None:
        self.assertEqual(
            P277_DELETE_CONFIRM_MENU_PATH,
            ("MENU", "Playback", "Delete", "Delete confirm."),
        )
        self.assertEqual(
            P277_DELETE_TWICE_MENU_PATH,
            ("MENU", "Playback", "Delete", "Delete pressing twice"),
        )
        self.assertEqual(P277_DELETE_CONFIRM_BKID, "BKID_APP_setting_delete_confirm")
        self.assertEqual(P277_DELETE_TWICE_BKID, "BKID_APP_setting_delete_by_delete_twice")
        self.assertEqual(P277_DELETE_CONFIRM_MODES, ('"Cancel" first', '"Delete" first'))
        self.assertEqual(P277_DELETE_CONFIRM_DEFAULT, '"Cancel" first')
        self.assertEqual(P277_DELETE_CONFIRM_RESID16_PAIRS['"Cancel" first'], (0xE724, 0x6A5E))
        self.assertEqual(P277_DELETE_CONFIRM_RESID16_PAIRS['"Delete" first'], (0xE725, 0x6E0A))
        self.assertEqual(P277_DELETE_TWICE_RESID16, 0x74DB)
        self.assertEqual(P277_DELETE_TWICE_DEFAULT, "Off")

    def test_44_reject_delete_first_or_delete_twice_on_recovery_bench(self) -> None:
        rep_del = evaluate_volume_4ch_mon_delete_confirm_vault(
            Volume4chMonDeleteConfirmVaultSpec(
                pre_delete_confirm='"Delete" first',
                post_delete_confirm='"Delete" first',
            )
        )
        self.assertFalse(rep_del.passed)
        self.assertEqual(rep_del.block_code, P277_BLOCKED_DESTRUCTIVE_DELETE_CONFIRM_DRIFT)

        rep_2x = evaluate_volume_4ch_mon_delete_confirm_vault(
            Volume4chMonDeleteConfirmVaultSpec(
                pre_delete_pressing_twice="On",
                post_delete_pressing_twice="On",
            )
        )
        self.assertFalse(rep_2x.passed)
        self.assertEqual(rep_2x.block_code, P277_BLOCKED_DESTRUCTIVE_DELETE_CONFIRM_DRIFT)

    def test_45_setup_and_playback_items_survive_camera_and_network_reset_helper(self) -> None:
        for act in ("NONE", "Camera Settings Reset", "Reset Network Set."):
            v, m, dc, d2x, blk = compute_expected_pillar48b_reset_and_slot1_vault_guard(
                pre_volume_settings=11,
                pre_audio_monitoring_ch="CH3/CH4",
                pre_delete_confirm='"Delete" first',
                pre_delete_pressing_twice="On",
                reset_action=act,
                slot1_holds_recovery_vault=True,
                slot1_sdxc_wp_locked=True,
                requested_vault_slot=1,
                requested_vault_action="READ_ONLY_AUDIT",
            )
            self.assertEqual((v, m, dc, d2x, blk), (11, "CH3/CH4", '"Delete" first', "On", False))

        v_i, m_i, dc_i, d2x_i, blk_i = compute_expected_pillar48b_reset_and_slot1_vault_guard(
            pre_volume_settings=11,
            pre_audio_monitoring_ch="CH3/CH4",
            pre_delete_confirm='"Delete" first',
            pre_delete_pressing_twice="On",
            reset_action="Initialize",
            slot1_holds_recovery_vault=True,
            slot1_sdxc_wp_locked=True,
            requested_vault_slot=1,
            requested_vault_action="READ_ONLY_AUDIT",
        )
        self.assertEqual((v_i, m_i, dc_i, d2x_i, blk_i), (7, "CH1/CH2", '"Cancel" first', "Off", False))

    def test_46_hard_slot1_firewall_blocks_all_6_delete_and_format_actions(self) -> None:
        for action in P277_DESTRUCTIVE_VAULT_ACTIONS:
            rep = evaluate_volume_4ch_mon_delete_confirm_vault(
                Volume4chMonDeleteConfirmVaultSpec(
                    requested_vault_slot=1,
                    requested_vault_action=action,
                )
            )
            self.assertFalse(rep.passed, f"Expected hard block for {action}")
            self.assertEqual(rep.block_code, P277_BLOCKED_SLOT1_VAULT_DELETE_OR_FORMAT)
            self.assertGreaterEqual(rep.slot1_vault_delete_events, 1)

    def test_47_slot2_delete_does_not_trip_slot1_vault_firewall_helper(self) -> None:
        for action in P277_DESTRUCTIVE_VAULT_ACTIONS:
            _, _, _, _, blk = compute_expected_pillar48b_reset_and_slot1_vault_guard(
                pre_volume_settings=7,
                pre_audio_monitoring_ch="CH1/CH2",
                pre_delete_confirm='"Cancel" first',
                pre_delete_pressing_twice="Off",
                reset_action="NONE",
                slot1_holds_recovery_vault=True,
                slot1_sdxc_wp_locked=True,
                requested_vault_slot=2,
                requested_vault_action=action,
            )
            self.assertFalse(blk)

    def test_48_reject_slot1_unlock_mutation_overlay_or_h0_h3_drift_48b(self) -> None:
        for bad_kwargs, expected_code in (
            ({"slot1_sdxc_wp_locked": False}, P277_BLOCKED_SLOT1_VAULT_DELETE_OR_FORMAT),
            ({"slot1_format_hard_locked": False}, P277_BLOCKED_SLOT1_VAULT_DELETE_OR_FORMAT),
            ({"slot1_vault_mutation_bytes": 512}, P277_BLOCKED_SLOT1_VAULT_DELETE_OR_FORMAT),
            ({"overlay_dir": "/setting/48b"}, P277_BLOCKED_PERSISTENT_OVERLAY_ESCAPE),
            ({"p2_blkroset_locked": False}, P277_BLOCKED_PERSISTENT_OVERLAY_ESCAPE),
            ({"stage_b_backup_bin_writes": 1}, P277_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT),
            ({"camera_model": "ILME-FX6"}, P277_BLOCKED_INVALID_PILLAR48B_SPEC),
            ({"persistent_write_unlock_requested": True}, P277_BLOCKED_SAFETY_POLICY_VIOLATION),
        ):
            rep = evaluate_volume_4ch_mon_delete_confirm_vault(
                Volume4chMonDeleteConfirmVaultSpec(**bad_kwargs)
            )
            self.assertFalse(rep.passed)
            self.assertEqual(rep.block_code, expected_code)

    def test_49_camset_restore_after_initialize_passes_when_valid(self) -> None:
        rep = evaluate_volume_4ch_mon_delete_confirm_vault(
            Volume4chMonDeleteConfirmVaultSpec(
                reset_action="Initialize",
                camset_load_after_reset=True,
                camset_slot=1,
                camset_filename=P277_CAMSET_FILENAMES[0],
                camset_source_model=P277_FX3_MODEL_NAME,
                camset_read_only_load=True,
                saved_volume_settings=5,
                saved_audio_monitoring_ch="CH1/CH1",
                saved_delete_confirm='"Cancel" first',
                saved_delete_pressing_twice="Off",
                post_volume_settings=5,
                post_audio_monitoring_ch="CH1/CH1",
                post_delete_confirm='"Cancel" first',
                post_delete_pressing_twice="Off",
            )
        )
        self.assertTrue(rep.passed)

    # ------------------------------------------------------------------
    # 10. Standalone Pillar 48 Suites & Direct Verifier Entry Points
    # ------------------------------------------------------------------

    def test_50_pillar48a_6_scenario_suite_passes_6_of_6(self) -> None:
        res = run_pillar48a_power_save_monitor_start_time_language_vault_6_scenario_suite()
        self.assertTrue(res.passed)
        self.assertEqual(res.status, P277_STATUS_VERIFIED_PILLAR_48A)
        self.assertEqual(res.scenarios_passed, 6)
        self.assertEqual(res.scenarios_total, 6)
        self.assertEqual(tuple(s.scenario_id for s in res.scenarios), P277_PILLAR_48A_SCENARIO_IDS)
        self.assertTrue(all(s.passed for s in res.scenarios))

    def test_51_pillar48b_6_scenario_suite_passes_6_of_6(self) -> None:
        res = run_pillar48b_volume_4ch_mon_delete_confirm_slot1_vault_6_scenario_suite()
        self.assertTrue(res.passed)
        self.assertEqual(res.status, P277_STATUS_VERIFIED_PILLAR_48B)
        self.assertEqual(res.scenarios_passed, 6)
        self.assertEqual(res.scenarios_total, 6)
        self.assertEqual(tuple(s.scenario_id for s in res.scenarios), P277_PILLAR_48B_SCENARIO_IDS)
        self.assertTrue(all(s.passed for s in res.scenarios))

    def test_52_verify_power_save_monitor_language_volume_delete_and_aliases(self) -> None:
        rep = verify_power_save_monitor_language_volume_delete_and_vault(force_clean_room=True)
        rep_alias = verify_power_save_monitor_language_volume_delete_vault(force_clean_room=True)
        self.assertTrue(rep.all_passed)
        self.assertTrue(rep_alias.all_passed)
        self.assertEqual(rep.status, P277_STATUS_VERIFIED_PILLAR48_SUITE)
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertFalse(rep.fx3_ui_exposes_power_save_by_monitor)
        self.assertTrue(rep.slot1_format_hard_locked)
        self.assertEqual(rep.slot1_vault_delete_events, 0)

    def test_53_run_pillar48_standalone_suite_active_and_clean_room(self) -> None:
        rep_active = run_pillar48_standalone_suite()
        rep_clean = run_pillar48_standalone_suite(force_clean_room=True)
        for rep in (rep_active, rep_clean):
            self.assertIsInstance(rep, Pillar48StandaloneReport)
            self.assertTrue(rep.all_passed)
            self.assertEqual(rep.status, P277_STATUS_VERIFIED_PILLAR48_SUITE)
            self.assertEqual(rep.pillar_48a_power_save_monitor_language_vault.scenarios_passed, 6)
            self.assertEqual(rep.pillar_48b_volume_4ch_mon_delete_confirm_slot1_vault.scenarios_passed, 6)
            self.assertEqual(rep.raw_firmware_bytes_leaked, 0)
            self.assertEqual(rep.physical_device_writes, 0)
            self.assertFalse(rep.hardware_live_attachment_authorized)
            self.assertTrue(rep.slot1_format_hard_locked)

    # ------------------------------------------------------------------
    # 11. Unified 48/48 Recovery Master Aggregator & Dual-Mode Parity
    # ------------------------------------------------------------------

    def test_54_master_48pillar_active_mode_passes_48_of_48_under_budget(self) -> None:
        rep = evaluate_realhw_48pillar_recovery_master()
        self.assertIsInstance(rep, Master48PillarRecoveryReport)
        self.assertTrue(rep.all_passed)
        self.assertEqual(rep.status, P277_STATUS_VERIFIED_48OF48_AGGREGATOR)
        self.assertEqual(rep.pillar_count, 48)
        self.assertEqual(rep.pillars_passed, 48)
        self.assertEqual(rep.failed_pillars, ())
        self.assertLess(rep.elapsed_seconds, _cli_budget_seconds())
        self.assertTrue(rep.under_6s_budget)
        self.assertTrue(rep.nominal_under_4_0s)
        self.assertEqual(tuple(p.pillar_id for p in rep.pillars), MASTER_48_PILLAR_IDS)

    def test_55_master_48pillar_clean_room_mode_passes_48_of_48(self) -> None:
        rep = evaluate_realhw_48pillar_recovery_master(force_clean_room=True)
        self.assertTrue(rep.all_passed)
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(rep.pillar_count, 48)
        self.assertEqual(rep.pillars_passed, 48)
        self.assertEqual(rep.failed_pillars, ())
        self.assertLess(rep.elapsed_seconds, _cli_budget_seconds())

    def test_56_master_48pillar_env_clean_room_and_force_clean_room_modes(self) -> None:
        for env_key in (P277_ENV_CLEAN_ROOM_TEST, "FX3_FX6_FORCE_CLEAN_ROOM"):
            with mock.patch.dict(os.environ, {env_key: "1"}):
                rep = evaluate_48pillar_recovery_master()
            self.assertTrue(rep.all_passed)
            self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertEqual(rep.pillars_passed, 48)

    def test_57_master_48pillar_aliases_and_deterministic_sha256(self) -> None:
        r1 = evaluate_48pillar_recovery_master(force_clean_room=True)
        r2 = verify_48pillar_recovery_suite(force_clean_room=True)
        self.assertEqual(r1.master_48pillar_sha256, r2.master_48pillar_sha256)
        self.assertEqual(len(r1.master_48pillar_sha256), 64)

    def test_58_master_48pillar_preserves_prior_47_pillar_invariants(self) -> None:
        rep = evaluate_realhw_48pillar_recovery_master(force_clean_room=True)
        self.assertEqual(rep.legacy_mf_assist_spoof_events, 0)
        self.assertEqual(rep.still_movie_initial_mag_couplings, 0)
        self.assertEqual(rep.hdmi_clean_feed_focus_mag_or_peaking_leak_pixels, 0)
        self.assertEqual(rep.mishoe_5v_overcurrent_events, 0)
        self.assertEqual(rep.hdmi_res_log_internal_rec_2160p_bypass_events, 0)
        self.assertFalse(rep.fx3_has_builtin_end_filter)
        self.assertFalse(rep.fx3_has_builtin_evf)
        self.assertFalse(rep.fx3_has_var_shutter)
        self.assertGreaterEqual(rep.bodydata_flash_attempts_blocked, 1)
        self.assertTrue(rep.cnflasha_userspace_write_blocked)
        self.assertFalse(rep.fx3_ui_exposes_power_save_by_monitor)
        self.assertTrue(rep.slot1_format_hard_locked)
        self.assertEqual(rep.slot1_vault_delete_events, 0)

    def test_59_master_48pillar_fault_injection_pillar_48(self) -> None:
        rep = evaluate_realhw_48pillar_recovery_master(
            force_clean_room=True,
            fault_inject_pillar="pillar_48_power_save_monitor_language_volume_delete_vault",
        )
        self.assertFalse(rep.all_passed)
        self.assertEqual(rep.status, P277_STATUS_FAIL_48OF48_AGGREGATOR)
        self.assertEqual(rep.pillars_passed, 47)
        self.assertEqual(
            rep.failed_pillars,
            ("pillar_48_power_save_monitor_language_volume_delete_vault",),
        )

    def test_60_master_48pillar_fault_injection_pillar_47_and_unknown_error(self) -> None:
        rep = evaluate_realhw_48pillar_recovery_master(
            force_clean_room=True,
            fault_inject_pillar=MASTER_48_PILLAR_IDS[46],
        )
        self.assertFalse(rep.all_passed)
        self.assertEqual(rep.pillars_passed, 47)
        self.assertEqual(rep.failed_pillars, (MASTER_48_PILLAR_IDS[46],))
        with self.assertRaises(ValueError):
            evaluate_realhw_48pillar_recovery_master(
                force_clean_room=True,
                fault_inject_pillar="pillar_999_nonexistent",
            )

    def test_61_master_48pillar_to_dict_json_roundtrip(self) -> None:
        rep = evaluate_realhw_48pillar_recovery_master(force_clean_room=True)
        dumped = json.dumps(rep.to_dict(), sort_keys=True, allow_nan=False)
        parsed = json.loads(dumped)
        self.assertEqual(parsed["pillar_count"], 48)
        self.assertEqual(parsed["pillars_passed"], 48)
        self.assertTrue(parsed["all_passed"])
        self.assertEqual(parsed["schema"], PHASE277_SCHEMA)

    # ------------------------------------------------------------------
    # 12. CLI Integration (--json, --clean-room, --out, sys.executable)
    # ------------------------------------------------------------------

    def test_62_cli_pillar48_standalone_json_clean_room(self) -> None:
        buf = io.StringIO()
        with mock.patch.object(
            sys,
            "argv",
            ["fx3_recovery", "verify-power-save-monitor-language-volume-delete-vault", "--clean-room", "--json"],
        ):
            with redirect_stdout(buf):
                rc = cli_main.main()
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())
        self.assertTrue(payload["all_passed"])
        self.assertEqual(payload["status"], P277_STATUS_VERIFIED_PILLAR48_SUITE)
        self.assertEqual(payload["verification_mode"], "CLEAN_ROOM_SYNTHETIC")

    def test_63_cli_48pillar_master_json_clean_room(self) -> None:
        buf = io.StringIO()
        with mock.patch.object(
            sys,
            "argv",
            ["fx3_recovery", "verify-48pillar-recovery", "--clean-room", "--json"],
        ):
            with redirect_stdout(buf):
                rc = cli_main.main()
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())
        self.assertTrue(payload["all_passed"])
        self.assertEqual(payload["pillar_count"], 48)
        self.assertEqual(payload["pillars_passed"], 48)
        self.assertEqual(payload["status"], P277_STATUS_VERIFIED_48OF48_AGGREGATOR)

    def test_64_cli_48pillar_master_out_dir_repo_local_cleaned_in_finally(self) -> None:
        work_tests = _repo_root() / "work" / "_tests"
        work_tests.mkdir(parents=True, exist_ok=True)
        out_root = Path(tempfile.mkdtemp(prefix="p277_cli_", dir=str(work_tests)))
        out_dir = out_root / "master48"
        try:
            buf = io.StringIO()
            with mock.patch.object(
                sys,
                "argv",
                ["fx3_recovery", "verify-48pillar-recovery", "--clean-room", "--out", str(out_dir), "--json"],
            ):
                with redirect_stdout(buf):
                    rc = cli_main.main()
            self.assertEqual(rc, 0)
            out_file = out_dir / "48pillar-recovery-master-report.json"
            self.assertTrue(out_file.is_file())
            written = json.loads(out_file.read_text(encoding="utf-8"))
            self.assertEqual(written["pillars_passed"], 48)
        finally:
            shutil.rmtree(out_root, ignore_errors=True)

    def test_65_cli_subprocess_sys_executable_both_modes(self) -> None:
        adapter_dir = _repo_root() / "outputs" / "fx3-recovery-adapter"
        env_base = dict(os.environ)
        env_base["PYTHONDONTWRITEBYTECODE"] = "1"
        env_base["PYTHONPATH"] = str(adapter_dir)

        proc_active = subprocess.run(
            [sys.executable, "-B", "-m", "fx3_recovery", "verify-48pillar-recovery", "--json"],
            cwd=str(_repo_root()),
            env=env_base,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc_active.returncode, 0, proc_active.stderr)
        data_active = json.loads(proc_active.stdout)
        self.assertTrue(data_active["all_passed"])
        self.assertEqual(data_active["pillars_passed"], 48)

        env_clean = dict(env_base)
        env_clean[P277_ENV_CLEAN_ROOM_TEST] = "1"
        proc_clean = subprocess.run(
            [sys.executable, "-B", "-m", "fx3_recovery", "verify-48pillar-recovery", "--clean-room", "--json"],
            cwd=str(_repo_root()),
            env=env_clean,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc_clean.returncode, 0, proc_clean.stderr)
        data_clean = json.loads(proc_clean.stdout)
        self.assertEqual(data_clean["verification_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(data_clean["pillars_passed"], 48)

    # ------------------------------------------------------------------
    # 13. Additional Edge-Case & Invariant Coverage (66..76)
    # ------------------------------------------------------------------

    def test_66_power_save_start_time_non_airgap_allows_default_5min(self) -> None:
        rep = evaluate_power_save_monitor_language_vault(
            PowerSaveMonitorLanguageVaultSpec(
                airgapped_battery_tier0_session=False,
                active_deactivation_conditions=(),
                pre_power_save_start_time="5 Min",
                post_power_save_start_time="5 Min",
            )
        )
        self.assertTrue(rep.passed)

    def test_67_reject_nonzero_spoof_or_drift_counters_even_with_safe_fields(self) -> None:
        for field_name in (
            "legacy_power_save_monitor_spoof_events",
            "unsafe_power_save_sleep_interference_events",
            "bk_lang_parity_drift_events",
            "stage_b_4lang_uxc_ltt_drift_events",
        ):
            rep = evaluate_power_save_monitor_language_vault(
                PowerSaveMonitorLanguageVaultSpec(**{field_name: 1})
            )
            self.assertFalse(rep.passed, f"Expected failure when {field_name}=1")

    def test_68_reject_nonzero_pillar48b_violation_counters(self) -> None:
        for field_name in (
            "xlrh1_acoustic_feedback_violations",
            "audio_mon_4ch_hdmi_confusion_events",
            "destructive_delete_confirm_drift_events",
            "slot1_vault_delete_events",
        ):
            rep = evaluate_volume_4ch_mon_delete_confirm_vault(
                Volume4chMonDeleteConfirmVaultSpec(**{field_name: 1})
            )
            self.assertFalse(rep.passed, f"Expected failure when {field_name}=1")

    def test_69_internal_speaker_low_volume_4_passes_with_xlrh1_unseparated(self) -> None:
        rep = evaluate_volume_4ch_mon_delete_confirm_vault(
            Volume4chMonDeleteConfirmVaultSpec(
                xlrh1_mic_attached=True,
                playback_output_target="Internal Speaker",
                xlrh1_acoustic_separation_active=False,
                pre_volume_settings=4,
                post_volume_settings=4,
            )
        )
        self.assertTrue(rep.passed)

    def test_70_muted_output_allows_volume_15_with_xlrh1_attached(self) -> None:
        rep = evaluate_volume_4ch_mon_delete_confirm_vault(
            Volume4chMonDeleteConfirmVaultSpec(
                xlrh1_mic_attached=True,
                playback_output_target="Muted",
                xlrh1_acoustic_separation_active=False,
                pre_volume_settings=15,
                post_volume_settings=15,
            )
        )
        self.assertTrue(rep.passed)

    def test_71_verify_48pillar_recovery_passes_when_safety_tampered_blocks(self) -> None:
        with mock.patch.object(p277, "PHYSICAL_DEVICE_WRITES", 1):
            errs = p277._safety_invariant_errors()
            self.assertTrue(any("PHYSICAL_DEVICE_WRITES" in e for e in errs))
            rep48a = evaluate_power_save_monitor_language_vault()
            self.assertFalse(rep48a.passed)
            self.assertEqual(rep48a.block_code, P277_BLOCKED_SAFETY_POLICY_VIOLATION)
            rep48b = evaluate_volume_4ch_mon_delete_confirm_vault()
            self.assertFalse(rep48b.passed)
            self.assertEqual(rep48b.block_code, P277_BLOCKED_SAFETY_POLICY_VIOLATION)

    def test_72_pillar48a_and_48b_matrix_counts_are_exhaustive(self) -> None:
        rep48a = evaluate_power_save_monitor_language_vault()
        rep48b = evaluate_volume_4ch_mon_delete_confirm_vault()
        # 48A: 32 (body x mode x fold x hdmi) + 24 (6 start times x 2 conds x 2 airgap) + 4 langs + 4 reset = 64
        self.assertEqual(rep48a.matrix_states_checked, 64)
        # 48B: 96 (16 vols x 3 targets x 2 sep) + 10 (5 routes x 2 hdmi) + 32 (4 resets x 8 vault actions) = 138
        self.assertEqual(rep48b.matrix_states_checked, 138)

    def test_73_pillar48_human_readable_cli_text_output_passes(self) -> None:
        buf = io.StringIO()
        with mock.patch.object(
            sys,
            "argv",
            ["fx3_recovery", "verify-power-save-monitor-language-volume-delete-vault", "--clean-room"],
        ):
            with redirect_stdout(buf):
                rc = cli_main.main()
        self.assertEqual(rc, 0)
        text = buf.getvalue()
        self.assertIn("pillar_48a=6/6", text)
        self.assertIn("pillar_48b=6/6", text)
        self.assertIn("slot1_format_hard_locked=True", text)

    def test_74_master48_human_readable_cli_text_output_passes(self) -> None:
        buf = io.StringIO()
        with mock.patch.object(
            sys,
            "argv",
            ["fx3_recovery", "verify-48pillar-recovery", "--clean-room"],
        ):
            with redirect_stdout(buf):
                rc = cli_main.main()
        self.assertEqual(rc, 0)
        text = buf.getvalue()
        self.assertIn("pillars=48/48", text)
        self.assertIn("all_passed=True", text)
        self.assertIn("raw_firmware_bytes_leaked=0", text)

    def test_75_replace_spec_immutability_preserved(self) -> None:
        s = build_default_safe_power_save_monitor_language_vault_spec()
        s2 = replace(s, stage_b_selected_lang="en", stage_b_bank_id=0, stage_b_font_str_pair=(4, 4), stage_b_ltt_font="UniversOTS-SJ_wIcon.ltt")
        self.assertEqual(s.stage_b_selected_lang, "schinese")
        self.assertTrue(evaluate_power_save_monitor_language_vault(s2).passed)

    def test_76_backward_compatibility_47pillar_master_still_passes(self) -> None:
        rep47 = p277.evaluate_realhw_47pillar_recovery_master(force_clean_room=True)
        self.assertTrue(rep47.all_passed)
        self.assertEqual(rep47.pillars_passed, 47)


if __name__ == "__main__":
    unittest.main()
