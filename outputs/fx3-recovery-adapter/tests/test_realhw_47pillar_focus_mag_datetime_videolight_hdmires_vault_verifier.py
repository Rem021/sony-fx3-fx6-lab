"""Phase 272 — Dual-mode unit tests for Pillar 47 (`[Focus Assistant]` `[Auto Magnifier in MF] = [On]`
vs legacy `"MF Assist"` spoofing, `Custom Button 5`, `[Focus Magnif. Time] = [No Limit]`,
independent Still & Movie `[Initial Focus Mag.] = [x1.0]`, Still-only `[AF in Focus Mag.] = [On]`,
`[Peaking Display]` camera-LCD-only clean-HDMI isolation & Still-only `[AF Illuminator]`; plus
`[Area/Date/Time Setting]` exact 4 sub-items & Zero-RF Creators' App suppression preserving
`H0..H3` forensic timestamps, `[Video Light Mode] = [Power Link]` MI-Shoe `5V <= 900 mA` rail guard,
`[HDMI Resolution] = [Auto]` Log internal-recording `1080p` downshift override & Slot-1 recovery vault
read-only lock) and unified `47/47` recovery master (`verify-47pillar-recovery` /
`verify-focus-mag-datetime-videolight-hdmires-vault`)."""

from __future__ import annotations

from contextlib import redirect_stdout
from dataclasses import replace
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import fx3_recovery
from fx3_recovery import __main__ as cli_main
from fx3_recovery import (
    realhw_47pillar_focus_mag_datetime_videolight_hdmires_vault_verifier as p272,
)
from fx3_recovery.realhw_46pillar_file_settings_gamma_assist_tcub_vault_verifier import (
    MASTER_46_PILLAR_SPECS,
    Master46PillarRecoveryReport,
)
from fx3_recovery.realhw_47pillar_focus_mag_datetime_videolight_hdmires_vault_verifier import (
    ALLOW_BOOT_PARTITION_TARGETING,
    ALLOW_DESTRUCTIVE_FASTBOOT,
    ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS,
    ALLOW_PERSISTENT_JIRITSU_WRITES,
    CNFLASHA_USERSPACE_WRITE_BLOCKED,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    ISP_WRITE_AUTHORIZED,
    LIVE_USB_IOKIT_TRANSMIT_ENABLED,
    MASTER_47_PILLAR_COUNT,
    MASTER_47_PILLAR_IDS,
    MASTER_47_PILLAR_SPECS,
    OTP_FUSE_TOUCHES,
    OTP_FUSE_WRITES,
    P272_AF_ILLUMINATOR_DEFAULT,
    P272_AF_ILLUMINATOR_MENU_PATH,
    P272_AF_ILLUMINATOR_MODES,
    P272_AF_IN_FOCUS_MAG_DEFAULT,
    P272_AIRPLANE_MODES,
    P272_AIRPLANE_MODE_MENU_PATH,
    P272_ALLOWED_FOCUS_MAG_CUSTOM_BTNS,
    P272_ALLOWED_PEAKING_SELECT_BTNS,
    P272_AREA_DATETIME_EXACT_4_SUBITEMS,
    P272_AREA_DATETIME_LABEL,
    P272_AREA_DATETIME_MENU_PATH,
    P272_AREA_SETTING_DEFAULT,
    P272_AUTO_MAG_IN_MF_DEFAULT,
    P272_AUTO_MAG_IN_MF_LABEL,
    P272_BLOCKED_FOCUS_ASSISTANT_RESET_SCOPE_DRIFT,
    P272_BLOCKED_FOCUS_MAG_DEFAULTS_OR_REGISTER_COUPLING,
    P272_BLOCKED_HDMI_CLEAN_FEED_OVERLAY_LEAK,
    P272_BLOCKED_HDMI_RES_LOG_1080P_OVERRIDE,
    P272_BLOCKED_INVALID_DATETIME_VIDEOLIGHT_HDMIRES_SPEC,
    P272_BLOCKED_INVALID_FOCUS_MAG_PEAKING_SPEC,
    P272_BLOCKED_LEGACY_DATETIME_SETUP_SPOOF,
    P272_BLOCKED_LEGACY_MF_ASSIST_NOMENCLATURE_SPOOF,
    P272_BLOCKED_MISHOE_5V_OVERCURRENT,
    P272_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
    P272_BLOCKED_SAFETY_POLICY_VIOLATION,
    P272_BLOCKED_SETUP_RESET_PERSISTENCE_OR_SLOT1_VAULT_DRIFT,
    P272_BLOCKED_STILL_ONLY_AF_ILLUMINATOR_OR_AF_IN_MAG,
    P272_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
    P272_BLOCKED_ZERO_RF_CREATORS_APP_SYNC_OR_RTC_JUMP,
    P272_BOUNDED_HEADER_BYTES,
    P272_CAMSET_FILENAMES,
    P272_CONCURRENT_CEILING_SECONDS,
    P272_DATE_FORMATS,
    P272_DATE_FORMAT_DEFAULT,
    P272_DAYLIGHT_SAVINGS_DEFAULT,
    P272_DAYLIGHT_SAVINGS_MODES,
    P272_DONOR_INSPECT_BUDGET_SECONDS,
    P272_DONOR_INSPECT_CI_BUDGET_SECONDS,
    P272_ENV_CLEAN_ROOM_TEST,
    P272_FAST_CLI_BUDGET_SECONDS,
    P272_FOCUS_ASSISTANT_MENU_PATH,
    P272_FOCUS_MAGNIFIER_CUSTOM_BTN_DEFAULT,
    P272_FOCUS_MAGNIF_TIME_DEFAULT,
    P272_FOCUS_MAGNIF_TIME_MODES,
    P272_FORBIDDEN_LEGACY_DATETIME_LABEL,
    P272_FORBIDDEN_LEGACY_MF_ASSIST_LABEL,
    P272_FX3_FW_VERSION,
    P272_FX3_HELPGUIDE_ID,
    P272_FX3_MODEL_ID,
    P272_FX3_MODEL_NAME,
    P272_FX3_SUPPORTED_FW_VERSIONS,
    P272_FX6_DONOR_FW_VERSION,
    P272_FX6_DONOR_MODEL_NAME,
    P272_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    P272_HDMI_CLEAN_FEED_FOCUS_MAG_OR_PEAKING_LEAK_PIXELS,
    P272_HDMI_FEED_MODES,
    P272_HDMI_INFO_DISPLAY_MENU_PATH,
    P272_HDMI_RESOLUTIONS,
    P272_HDMI_RESOLUTION_DEFAULT,
    P272_HDMI_RESOLUTION_MENU_PATH,
    P272_HDMI_RES_LOG_INTERNAL_REC_2160P_BYPASS_EVENTS,
    P272_INITIAL_FOCUS_MAG_MODES,
    P272_INITIAL_FOCUS_MAG_MOVIE_DEFAULT,
    P272_INITIAL_FOCUS_MAG_STILL_DEFAULT,
    P272_LEGACY_DATETIME_SETUP_SPOOF_EVENTS,
    P272_LEGACY_MF_ASSIST_SPOOF_EVENTS,
    P272_LOG_SHOOTING_MODES,
    P272_MISHOE_5V_MAX_BUDGET_MA,
    P272_MISHOE_5V_OVERCURRENT_EVENTS,
    P272_MOVIE_AF_IN_FOCUS_MAG_EVENTS,
    P272_MOVIE_SQ_AF_ILLUMINATOR_FIRE_EVENTS,
    P272_NOMINAL_BUDGET_SECONDS,
    P272_ON_OFF_MODES,
    P272_PEAKING_COLORS,
    P272_PEAKING_COLOR_DEFAULT,
    P272_PEAKING_DISPLAY_DEFAULT,
    P272_PEAKING_DISPLAY_MENU_PATH,
    P272_PEAKING_DISPLAY_SELECT_DEFAULT,
    P272_PEAKING_LEVELS,
    P272_PEAKING_LEVEL_DEFAULT,
    P272_PILLAR_47A_SCENARIO_IDS,
    P272_PILLAR_47B_SCENARIO_IDS,
    P272_PINNED_FX3_APPFW_702_BYTES,
    P272_PINNED_FX3_APPFW_702_HDR4K_SHA256,
    P272_PINNED_FX3_BACKUP_BIN_BYTES,
    P272_PINNED_FX3_BACKUP_BIN_SHA256,
    P272_PINNED_FX3_BODYDATA_BYTES,
    P272_PINNED_FX3_BODYDATA_HDR4K_SHA256,
    P272_PINNED_FX3_CAMERAONDEMANDSAVER_SO_BYTES,
    P272_PINNED_FX3_CAMERAONDEMANDSAVER_SO_SHA256,
    P272_PINNED_FX3_CPAPP_B_BIN_BYTES,
    P272_PINNED_FX3_CPAPP_B_BIN_HDR4K_SHA256,
    P272_PINNED_FX3_LIBBACKUPMANAGER_SO_BYTES,
    P272_PINNED_FX3_LIBBACKUPMANAGER_SO_SHA256,
    P272_PINNED_FX3_LIBBACKUP_SO_BYTES,
    P272_PINNED_FX3_LIBBACKUP_SO_SHA256,
    P272_PINNED_FX3_LIBGPE_SO_BYTES,
    P272_PINNED_FX3_LIBGPE_SO_SHA256,
    P272_PINNED_FX3_LIBINFRAAIRPLANEMODE_SO_BYTES,
    P272_PINNED_FX3_LIBINFRAAIRPLANEMODE_SO_SHA256,
    P272_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_BYTES,
    P272_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_SHA256,
    P272_PINNED_FX3_LIBINFRAMEDIADETECT_SO_BYTES,
    P272_PINNED_FX3_LIBINFRAMEDIADETECT_SO_SHA256,
    P272_PINNED_FX3_LIBSAVELOADSETTINGS_SO_BYTES,
    P272_PINNED_FX3_LIBSAVELOADSETTINGS_SO_SHA256,
    P272_PINNED_FX6_APPFW_601_BYTES,
    P272_PINNED_FX6_APPFW_601_HDR4K_SHA256,
    P272_PINNED_FX6_BACKUP_NTSC_BIN_BYTES,
    P272_PINNED_FX6_BACKUP_NTSC_BIN_SHA256,
    P272_PINNED_FX6_LIBINFRADIAL_SO_BYTES,
    P272_PINNED_FX6_LIBINFRADIAL_SO_SHA256,
    P272_PINNED_FX6_LIBINFRAHOTSHOE_SO_BYTES,
    P272_PINNED_FX6_LIBINFRAHOTSHOE_SO_SHA256,
    P272_REC_MEDIA_DUR_HDMI_MODES,
    P272_RESET_ACTIONS,
    P272_SHOOTING_DOMAINS,
    P272_SLOT1_VAULT_MUTATION_BYTES,
    P272_SLOT1_VAULT_MUTATION_EVENTS,
    P272_SLOT1_VAULT_SLOT,
    P272_STAGE_B_VOLATILE_OVERLAY_DIR,
    P272_STATUS_FAIL_47OF47_AGGREGATOR,
    P272_STATUS_FAIL_PILLAR47_SUITE,
    P272_STATUS_REJECTED_PILLAR_47A,
    P272_STATUS_REJECTED_PILLAR_47B,
    P272_STATUS_VERIFIED_47OF47_AGGREGATOR,
    P272_STATUS_VERIFIED_PILLAR47_SUITE,
    P272_STATUS_VERIFIED_PILLAR_47A,
    P272_STATUS_VERIFIED_PILLAR_47B,
    P272_STILL_MOVIE_INITIAL_MAG_COUPLINGS,
    P272_TIER0_SURFACE_COUNT,
    P272_UNSOLICITED_RTC_TIMEZONE_JUMP_EVENTS,
    P272_VIDEO_LIGHT_MODES,
    P272_VIDEO_LIGHT_MODE_DEFAULT,
    P272_VIDEO_LIGHT_MODE_MENU_PATH,
    PASSIVE_TX_BYTES_EMITTED,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHASE272_PHASE_NUMBER,
    PHASE272_SCHEMA,
    PHASE272_VERSION,
    PHYSICAL_DEVICE_WRITES,
    PHYSICAL_USB_PACKETS_EMITTED,
    RAW_FIRMWARE_BYTES_LEAKED,
    READ_ONLY_DONOR_ACCESS,
    RPMB_COUNTER_INCREMENTS,
    SPI_NOR_WRITE_AUTHORIZED,
    AreaDatetimeVideolightHdmiresVaultReport,
    AreaDatetimeVideolightHdmiresVaultSpec,
    FocusMagDatetimeVideolightHdmiresVaultReport,
    FocusMagPeakingStillAfIlluminatorVaultReport,
    FocusMagPeakingStillAfIlluminatorVaultSpec,
    Master47PillarRecoveryReport,
    Phase272DonorSnapshot,
    Pillar47ASuiteResult,
    Pillar47BSuiteResult,
    Pillar47StandaloneReport,
    build_default_safe_area_datetime_videolight_hdmires_vault_spec,
    build_default_safe_focus_mag_peaking_still_af_illuminator_vault_spec,
    compute_expected_effective_hdmi_resolution,
    compute_expected_focus_mag_peaking_runtime_gates,
    compute_expected_pillar47a_focus_assistant_state_after_reset,
    compute_expected_pillar47b_setup_state_after_reset,
    evaluate_47pillar_recovery_master,
    evaluate_area_datetime_videolight_hdmires_vault,
    evaluate_focus_mag_peaking_still_af_illuminator_vault,
    evaluate_realhw_47pillar_recovery_master,
    inspect_phase272_donors_readonly,
    run_pillar47_standalone_suite,
    run_pillar47a_focus_mag_peaking_still_af_illuminator_vault_6_scenario_suite,
    run_pillar47b_area_datetime_videolight_hdmires_vault_6_scenario_suite,
    verify_47pillar_recovery_suite,
    verify_focus_mag_datetime_videolight_hdmires_and_vault,
    verify_focus_mag_datetime_videolight_hdmires_vault,
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


class TestPhase272Realhw47PillarVerifier(unittest.TestCase):
    """75 comprehensive dual-mode unit tests for Phase 272 Pillar 47 & 47/47 Master."""

    # ------------------------------------------------------------------
    # 1. Safety Invariants, Module Exports & 47-Pillar Spec Integrity
    # ------------------------------------------------------------------

    def test_01_hard_locked_zero_write_safety_constants(self) -> None:
        self.assertEqual(PHASE272_PHASE_NUMBER, 272)
        self.assertEqual(PHASE272_SCHEMA, "realhw_47pillar_focus_mag_datetime_videolight_hdmires_vault_verifier_v1")
        self.assertEqual(PHASE272_VERSION, "1.0.0")
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
        self.assertFalse(P272_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        self.assertTrue(READ_ONLY_DONOR_ACCESS)
        self.assertTrue(CNFLASHA_USERSPACE_WRITE_BLOCKED)
        self.assertEqual(OTP_FUSE_TOUCHES, 0)
        self.assertEqual(OTP_FUSE_WRITES, 0)
        self.assertEqual(RPMB_COUNTER_INCREMENTS, 0)
        self.assertEqual(PASSIVE_TX_BYTES_EMITTED, 0)
        self.assertEqual(PHYSICAL_USB_PACKETS_EMITTED, 0)
        self.assertEqual(PHYSICAL_DEVICE_WRITES, 0)
        self.assertEqual(RAW_FIRMWARE_BYTES_LEAKED, 0)

    def test_02_wave45_baseline_and_zero_event_constants(self) -> None:
        self.assertEqual(P272_FX3_MODEL_NAME, "ILME-FX3")
        self.assertEqual(P272_FX3_MODEL_ID, 0x91030080)
        self.assertEqual(P272_FX3_HELPGUIDE_ID, "ilc/2210")
        self.assertEqual(P272_FX3_FW_VERSION, "7.02")
        self.assertEqual(P272_FX6_DONOR_MODEL_NAME, "ILME-FX6")
        self.assertEqual(P272_FX6_DONOR_FW_VERSION, "6.01")
        self.assertIn("7.02", P272_FX3_SUPPORTED_FW_VERSIONS)
        self.assertEqual(P272_LEGACY_MF_ASSIST_SPOOF_EVENTS, 0)
        self.assertEqual(P272_STILL_MOVIE_INITIAL_MAG_COUPLINGS, 0)
        self.assertEqual(P272_MOVIE_AF_IN_FOCUS_MAG_EVENTS, 0)
        self.assertEqual(P272_HDMI_CLEAN_FEED_FOCUS_MAG_OR_PEAKING_LEAK_PIXELS, 0)
        self.assertEqual(P272_MOVIE_SQ_AF_ILLUMINATOR_FIRE_EVENTS, 0)
        self.assertEqual(P272_LEGACY_DATETIME_SETUP_SPOOF_EVENTS, 0)
        self.assertEqual(P272_UNSOLICITED_RTC_TIMEZONE_JUMP_EVENTS, 0)
        self.assertEqual(P272_MISHOE_5V_OVERCURRENT_EVENTS, 0)
        self.assertEqual(P272_HDMI_RES_LOG_INTERNAL_REC_2160P_BYPASS_EVENTS, 0)
        self.assertEqual(P272_SLOT1_VAULT_MUTATION_EVENTS, 0)
        self.assertEqual(P272_SLOT1_VAULT_MUTATION_BYTES, 0)

    def test_03_package_reexports_and_non_shadowing_of_pillars_1_to_46(self) -> None:
        self.assertEqual(fx3_recovery.PHASE272_PHASE_NUMBER, 272)
        self.assertEqual(fx3_recovery.MASTER_47_PILLAR_COUNT, 47)
        self.assertIs(
            fx3_recovery.evaluate_realhw_47pillar_recovery_master,
            evaluate_realhw_47pillar_recovery_master,
        )
        self.assertIs(
            fx3_recovery.verify_focus_mag_datetime_videolight_hdmires_vault,
            verify_focus_mag_datetime_videolight_hdmires_vault,
        )
        # Ensure Pillars 1..46 exports are NOT shadowed
        self.assertEqual(fx3_recovery.PHASE269_PHASE_NUMBER, 269)
        self.assertEqual(fx3_recovery.MASTER_46_PILLAR_COUNT, 46)
        self.assertTrue(callable(fx3_recovery.evaluate_realhw_46pillar_recovery_master))
        self.assertTrue(callable(fx3_recovery.evaluate_realhw_45pillar_recovery_master))
        self.assertTrue(callable(fx3_recovery.evaluate_22pillar_recovery_master))

    def test_04_master_47_pillar_specs_unique_and_contiguous(self) -> None:
        self.assertEqual(MASTER_47_PILLAR_COUNT, 47)
        self.assertEqual(len(MASTER_47_PILLAR_SPECS), 47)
        self.assertEqual(MASTER_47_PILLAR_SPECS[:46], MASTER_46_PILLAR_SPECS)
        nums = [spec[0] for spec in MASTER_47_PILLAR_SPECS]
        self.assertEqual(nums, list(range(1, 48)))
        self.assertEqual(len(set(MASTER_47_PILLAR_IDS)), 47)
        self.assertEqual(
            MASTER_47_PILLAR_SPECS[46][1],
            "pillar_47_focus_mag_datetime_videolight_hdmires_vault",
        )
        self.assertEqual(MASTER_47_PILLAR_SPECS[46][2], "Phase 272 (47/47)")

    def test_05_safety_invariant_tamper_detection(self) -> None:
        with mock.patch.object(p272, "PERSISTENT_EMMC_WRITES_AUTHORIZED", True):
            errs = p272._safety_invariant_errors()
            self.assertTrue(any("PERSISTENT_EMMC_WRITES_AUTHORIZED" in e for e in errs))
            rep_a = evaluate_focus_mag_peaking_still_af_illuminator_vault(
                build_default_safe_focus_mag_peaking_still_af_illuminator_vault_spec()
            )
            self.assertFalse(rep_a.passed)
            self.assertEqual(rep_a.block_code, P272_BLOCKED_SAFETY_POLICY_VIOLATION)
            rep_b = evaluate_area_datetime_videolight_hdmires_vault(
                build_default_safe_area_datetime_videolight_hdmires_vault_spec()
            )
            self.assertFalse(rep_b.passed)
            self.assertEqual(rep_b.block_code, P272_BLOCKED_SAFETY_POLICY_VIOLATION)

    def test_06_persistent_write_unlock_request_rejected_on_both_pillars(self) -> None:
        rep_a = evaluate_focus_mag_peaking_still_af_illuminator_vault(
            replace(
                build_default_safe_focus_mag_peaking_still_af_illuminator_vault_spec(),
                persistent_write_unlock_requested=True,
            )
        )
        self.assertFalse(rep_a.passed)
        self.assertEqual(rep_a.block_code, P272_BLOCKED_SAFETY_POLICY_VIOLATION)

        rep_b = evaluate_area_datetime_videolight_hdmires_vault(
            replace(
                build_default_safe_area_datetime_videolight_hdmires_vault_spec(),
                persistent_write_unlock_requested=True,
            )
        )
        self.assertFalse(rep_b.passed)
        self.assertEqual(rep_b.block_code, P272_BLOCKED_SAFETY_POLICY_VIOLATION)

    # ------------------------------------------------------------------
    # 2. Bounded O_RDONLY Donor Inspection & Clean-Room Fallback
    # ------------------------------------------------------------------

    def test_07_donor_snapshot_bounded_o_rdonly_and_budget(self) -> None:
        snap = inspect_phase272_donors_readonly()
        self.assertIsInstance(snap, Phase272DonorSnapshot)
        self.assertIn(snap.verification_mode, ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"))
        self.assertTrue(snap.all_donors_present)
        self.assertEqual(snap.donor_files_inspected, 16)
        self.assertEqual(snap.raw_firmware_bytes_leaked, 0)
        self.assertTrue(snap.under_0_15s_budget)
        expected_budget = (
            P272_DONOR_INSPECT_CI_BUDGET_SECONDS
            if os.environ.get("GITHUB_ACTIONS", "").strip().lower() == "true"
            else P272_DONOR_INSPECT_BUDGET_SECONDS
        )
        self.assertEqual(snap.budget_seconds_applied, expected_budget)
        self.assertLess(snap.elapsed_seconds, expected_budget)

    def test_08_donor_pinned_hashes_and_sizes_match_wave45_baseline(self) -> None:
        snap = inspect_phase272_donors_readonly()
        by_id = {a.artifact_id: a for a in snap.artifacts}
        expected = {
            "fx3_bodydata_702": (
                P272_PINNED_FX3_BODYDATA_BYTES,
                P272_BOUNDED_HEADER_BYTES,
                "HEADER4K_SHA256",
                P272_PINNED_FX3_BODYDATA_HDR4K_SHA256,
            ),
            "fx3_appfw_702_so": (
                P272_PINNED_FX3_APPFW_702_BYTES,
                P272_BOUNDED_HEADER_BYTES,
                "HEADER4K_SHA256",
                P272_PINNED_FX3_APPFW_702_HDR4K_SHA256,
            ),
            "fx3_cpapp_b_bin": (
                P272_PINNED_FX3_CPAPP_B_BIN_BYTES,
                P272_BOUNDED_HEADER_BYTES,
                "HEADER4K_SHA256",
                P272_PINNED_FX3_CPAPP_B_BIN_HDR4K_SHA256,
            ),
            "fx6_appfw_601_so": (
                P272_PINNED_FX6_APPFW_601_BYTES,
                P272_BOUNDED_HEADER_BYTES,
                "HEADER4K_SHA256",
                P272_PINNED_FX6_APPFW_601_HDR4K_SHA256,
            ),
            "fx3_backup_bin": (
                P272_PINNED_FX3_BACKUP_BIN_BYTES,
                P272_PINNED_FX3_BACKUP_BIN_BYTES,
                "FULL_SHA256",
                P272_PINNED_FX3_BACKUP_BIN_SHA256,
            ),
            "fx6_backup_ntsc_bin": (
                P272_PINNED_FX6_BACKUP_NTSC_BIN_BYTES,
                P272_PINNED_FX6_BACKUP_NTSC_BIN_BYTES,
                "FULL_SHA256",
                P272_PINNED_FX6_BACKUP_NTSC_BIN_SHA256,
            ),
            "fx3_libbackup_so": (
                P272_PINNED_FX3_LIBBACKUP_SO_BYTES,
                P272_PINNED_FX3_LIBBACKUP_SO_BYTES,
                "FULL_SHA256",
                P272_PINNED_FX3_LIBBACKUP_SO_SHA256,
            ),
            "fx3_libbackupmanager_so": (
                P272_PINNED_FX3_LIBBACKUPMANAGER_SO_BYTES,
                P272_PINNED_FX3_LIBBACKUPMANAGER_SO_BYTES,
                "FULL_SHA256",
                P272_PINNED_FX3_LIBBACKUPMANAGER_SO_SHA256,
            ),
            "fx3_libsaveloadsettings_so": (
                P272_PINNED_FX3_LIBSAVELOADSETTINGS_SO_BYTES,
                P272_PINNED_FX3_LIBSAVELOADSETTINGS_SO_BYTES,
                "FULL_SHA256",
                P272_PINNED_FX3_LIBSAVELOADSETTINGS_SO_SHA256,
            ),
            "fx3_libgpe_so": (
                P272_PINNED_FX3_LIBGPE_SO_BYTES,
                P272_PINNED_FX3_LIBGPE_SO_BYTES,
                "FULL_SHA256",
                P272_PINNED_FX3_LIBGPE_SO_SHA256,
            ),
            "fx3_cameraondemandsaver_so": (
                P272_PINNED_FX3_CAMERAONDEMANDSAVER_SO_BYTES,
                P272_PINNED_FX3_CAMERAONDEMANDSAVER_SO_BYTES,
                "FULL_SHA256",
                P272_PINNED_FX3_CAMERAONDEMANDSAVER_SO_SHA256,
            ),
            "fx3_libinfraairplanemode_so": (
                P272_PINNED_FX3_LIBINFRAAIRPLANEMODE_SO_BYTES,
                P272_PINNED_FX3_LIBINFRAAIRPLANEMODE_SO_BYTES,
                "FULL_SHA256",
                P272_PINNED_FX3_LIBINFRAAIRPLANEMODE_SO_SHA256,
            ),
            "fx3_libinframediaconfig_so": (
                P272_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_BYTES,
                P272_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_BYTES,
                "FULL_SHA256",
                P272_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_SHA256,
            ),
            "fx3_libinframediadetect_so": (
                P272_PINNED_FX3_LIBINFRAMEDIADETECT_SO_BYTES,
                P272_PINNED_FX3_LIBINFRAMEDIADETECT_SO_BYTES,
                "FULL_SHA256",
                P272_PINNED_FX3_LIBINFRAMEDIADETECT_SO_SHA256,
            ),
            "fx6_libinfradial_so": (
                P272_PINNED_FX6_LIBINFRADIAL_SO_BYTES,
                P272_PINNED_FX6_LIBINFRADIAL_SO_BYTES,
                "FULL_SHA256",
                P272_PINNED_FX6_LIBINFRADIAL_SO_SHA256,
            ),
            "fx6_libinfrahotshoe_so": (
                P272_PINNED_FX6_LIBINFRAHOTSHOE_SO_BYTES,
                P272_PINNED_FX6_LIBINFRAHOTSHOE_SO_BYTES,
                "FULL_SHA256",
                P272_PINNED_FX6_LIBINFRAHOTSHOE_SO_SHA256,
            ),
        }
        self.assertEqual(set(by_id.keys()), set(expected.keys()))
        for aid, (exp_bytes, exp_hdr, exp_kind, exp_sha) in expected.items():
            art = by_id[aid]
            self.assertTrue(art.present, aid)
            self.assertTrue(art.matches_pinned, aid)
            self.assertEqual(art.total_bytes, exp_bytes, aid)
            self.assertEqual(art.header_bytes_read, exp_hdr, aid)
            self.assertEqual(art.digest_kind, exp_kind, aid)
            self.assertEqual(art.digest_sha256, exp_sha, aid)

    def test_09_clean_room_forced_by_flag_and_both_env_vars(self) -> None:
        snap_flag = inspect_phase272_donors_readonly(force_clean_room=True)
        self.assertEqual(snap_flag.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(snap_flag.all_donors_present)
        self.assertEqual(snap_flag.donor_files_inspected, 16)

        with mock.patch.dict(os.environ, {P272_ENV_CLEAN_ROOM_TEST: "1"}):
            snap_env1 = inspect_phase272_donors_readonly()
            self.assertEqual(snap_env1.verification_mode, "CLEAN_ROOM_SYNTHETIC")

        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            snap_env2 = inspect_phase272_donors_readonly()
            self.assertEqual(snap_env2.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_10_missing_donor_triggers_clean_room_fallback_parity(self) -> None:
        with mock.patch.dict(
            os.environ,
            {P272_ENV_CLEAN_ROOM_TEST: "", "FX3_FX6_FORCE_CLEAN_ROOM": ""},
        ):
            with mock.patch.object(p272, "resolve_donor_path", return_value=None):
                snap = inspect_phase272_donors_readonly()
                self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
                self.assertTrue(snap.all_donors_present)
                self.assertEqual(snap.donor_files_inspected, 16)

    def test_11_donor_ci_headroom_budget_applied_under_github_actions(self) -> None:
        with mock.patch.dict(os.environ, {"GITHUB_ACTIONS": "true"}):
            snap = inspect_phase272_donors_readonly(force_clean_room=True)
            self.assertEqual(snap.budget_seconds_applied, P272_DONOR_INSPECT_CI_BUDGET_SECONDS)
            self.assertTrue(snap.under_0_15s_budget)

    # ------------------------------------------------------------------
    # 3. Pillar 47A — Focus Assistant, Dual Initial Mag, Peaking, AF Illuminator
    # ------------------------------------------------------------------

    def test_12_default_pillar47a_safe_spec_passes_with_144_matrix(self) -> None:
        spec = build_default_safe_focus_mag_peaking_still_af_illuminator_vault_spec()
        rep = evaluate_focus_mag_peaking_still_af_illuminator_vault(spec)
        self.assertIsInstance(rep, FocusMagPeakingStillAfIlluminatorVaultReport)
        self.assertTrue(rep.passed)
        self.assertEqual(rep.status, P272_STATUS_VERIFIED_PILLAR_47A)
        self.assertIsNone(rep.block_code)
        self.assertTrue(rep.auto_mag_nomenclature_and_c5_verified)
        self.assertTrue(rep.independent_still_movie_x10_verified)
        self.assertTrue(rep.peaking_lcd_only_clean_hdmi_verified)
        self.assertTrue(rep.still_only_af_in_mag_and_af_illuminator_verified)
        self.assertTrue(rep.reset_scope_and_camset_restore_verified)
        self.assertTrue(rep.h0_equals_h3_verified)
        self.assertEqual(rep.matrix_states_checked, 144)
        self.assertEqual(rep.physical_device_writes, 0)
        self.assertFalse(rep.persistent_emmc_writes_authorized)

    def test_13_pillar47a_factory_default_constants_match_wave45(self) -> None:
        self.assertEqual(P272_FOCUS_ASSISTANT_MENU_PATH, ("MENU", "Focus", "Focus Assistant"))
        self.assertEqual(P272_PEAKING_DISPLAY_MENU_PATH, ("MENU", "Focus", "Peaking Display"))
        self.assertEqual(P272_AF_ILLUMINATOR_MENU_PATH, ("MENU", "Focus", "AF/MF", "AF Illuminator"))
        self.assertEqual(P272_HDMI_INFO_DISPLAY_MENU_PATH, ("MENU", "Setup", "External Output", "HDMI Info. Display"))
        self.assertEqual(P272_AUTO_MAG_IN_MF_LABEL, "Auto Magnifier in MF")
        self.assertEqual(P272_FORBIDDEN_LEGACY_MF_ASSIST_LABEL, "MF Assist")
        self.assertEqual(P272_AUTO_MAG_IN_MF_DEFAULT, "On")
        self.assertEqual(P272_FOCUS_MAGNIFIER_CUSTOM_BTN_DEFAULT, "Custom Button 5")
        self.assertEqual(P272_FOCUS_MAGNIF_TIME_DEFAULT, "No Limit")
        self.assertEqual(P272_INITIAL_FOCUS_MAG_STILL_DEFAULT, "x1.0")
        self.assertEqual(P272_INITIAL_FOCUS_MAG_MOVIE_DEFAULT, "x1.0")
        self.assertEqual(P272_AF_IN_FOCUS_MAG_DEFAULT, "On")
        self.assertEqual(P272_PEAKING_DISPLAY_DEFAULT, "Off")
        self.assertEqual(P272_PEAKING_DISPLAY_SELECT_DEFAULT, "Control Wheel Right")
        self.assertEqual(P272_PEAKING_LEVEL_DEFAULT, "Mid")
        self.assertEqual(P272_PEAKING_COLOR_DEFAULT, "White")
        self.assertEqual(P272_AF_ILLUMINATOR_DEFAULT, "Auto")

    def test_14_reject_legacy_mf_assist_label_spoof(self) -> None:
        spec = replace(
            build_default_safe_focus_mag_peaking_still_af_illuminator_vault_spec(),
            auto_mag_menu_label=P272_FORBIDDEN_LEGACY_MF_ASSIST_LABEL,
        )
        rep = evaluate_focus_mag_peaking_still_af_illuminator_vault(spec)
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P272_BLOCKED_LEGACY_MF_ASSIST_NOMENCLATURE_SPOOF)
        self.assertEqual(rep.legacy_mf_assist_spoof_events, 1)
        self.assertFalse(rep.auto_mag_nomenclature_and_c5_verified)

    def test_15_reject_nonzero_legacy_mf_assist_spoof_events(self) -> None:
        spec = replace(
            build_default_safe_focus_mag_peaking_still_af_illuminator_vault_spec(),
            legacy_mf_assist_spoof_events=2,
        )
        rep = evaluate_focus_mag_peaking_still_af_illuminator_vault(spec)
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P272_BLOCKED_LEGACY_MF_ASSIST_NOMENCLATURE_SPOOF)
        self.assertEqual(rep.legacy_mf_assist_spoof_events, 2)

    def test_16_reject_coupled_still_movie_initial_focus_mag_register(self) -> None:
        spec = replace(
            build_default_safe_focus_mag_peaking_still_af_illuminator_vault_spec(),
            still_movie_initial_mag_couplings=1,
        )
        rep = evaluate_focus_mag_peaking_still_af_illuminator_vault(spec)
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P272_BLOCKED_FOCUS_MAG_DEFAULTS_OR_REGISTER_COUPLING)
        self.assertEqual(rep.still_movie_initial_mag_couplings, 1)
        self.assertFalse(rep.independent_still_movie_x10_verified)

    def test_17_independent_still_and_movie_initial_focus_mag_registers(self) -> None:
        # Still=x4.0, Movie=x1.0 preserves independence across Still, Movie, S&Q
        still_gate = compute_expected_focus_mag_peaking_runtime_gates(
            shooting_domain="Still",
            focus_mode="MF",
            hdmi_feed_mode="Info On",
            still_initial_focus_mag="x4.0",
            movie_initial_focus_mag="x1.0",
            af_in_focus_mag="On",
            peaking_display="On",
            af_illuminator="Auto",
        )
        movie_gate = compute_expected_focus_mag_peaking_runtime_gates(
            shooting_domain="Movie",
            focus_mode="MF",
            hdmi_feed_mode="Info Off",
            still_initial_focus_mag="x4.0",
            movie_initial_focus_mag="x1.0",
            af_in_focus_mag="On",
            peaking_display="On",
            af_illuminator="Auto",
        )
        sq_gate = compute_expected_focus_mag_peaking_runtime_gates(
            shooting_domain="S&Q",
            focus_mode="DMF",
            hdmi_feed_mode="HDMI RAW",
            still_initial_focus_mag="x4.0",
            movie_initial_focus_mag="x1.0",
            af_in_focus_mag="On",
            peaking_display="On",
            af_illuminator="Auto",
        )
        self.assertEqual(still_gate[0], "x4.0")
        self.assertEqual(movie_gate[0], "x1.0")
        self.assertEqual(sq_gate[0], "x1.0")

    def test_18_still_only_af_in_focus_mag_and_af_illuminator_runtime_gates(self) -> None:
        # Still MF/DMF arms AF in Focus Mag; AF-S/AF-C/DMF arms AF Illuminator
        still_mf = compute_expected_focus_mag_peaking_runtime_gates(
            shooting_domain="Still",
            focus_mode="MF",
            hdmi_feed_mode="Info Off",
            still_initial_focus_mag="x1.0",
            movie_initial_focus_mag="x1.0",
            af_in_focus_mag="On",
            peaking_display="Off",
            af_illuminator="Auto",
        )
        self.assertTrue(still_mf[1])   # af_in_focus_mag_armed
        self.assertFalse(still_mf[2])  # af_illuminator_armed (MF -> False)

        still_dmf = compute_expected_focus_mag_peaking_runtime_gates(
            shooting_domain="Still",
            focus_mode="DMF",
            hdmi_feed_mode="Info Off",
            still_initial_focus_mag="x1.0",
            movie_initial_focus_mag="x1.0",
            af_in_focus_mag="On",
            peaking_display="On",
            af_illuminator="Auto",
        )
        self.assertTrue(still_dmf[1])
        self.assertTrue(still_dmf[2])
        self.assertTrue(still_dmf[3])  # lcd_peaking_visible

        for domain in ("Movie", "S&Q"):
            for fmode in ("MF", "DMF", "AF-S", "AF-C"):
                g = compute_expected_focus_mag_peaking_runtime_gates(
                    shooting_domain=domain,
                    focus_mode=fmode,
                    hdmi_feed_mode="HDMI RAW",
                    still_initial_focus_mag="x1.0",
                    movie_initial_focus_mag="x1.0",
                    af_in_focus_mag="On",
                    peaking_display="On",
                    af_illuminator="Auto",
                )
                self.assertFalse(g[1], f"{domain}/{fmode} must disarm AF in Focus Mag.")
                self.assertFalse(g[2], f"{domain}/{fmode} must disarm AF Illuminator")
                self.assertTrue(g[4] and g[5])

    def test_19_reject_movie_af_in_focus_mag_event(self) -> None:
        spec = replace(
            build_default_safe_focus_mag_peaking_still_af_illuminator_vault_spec(),
            shooting_domain="Movie",
            movie_af_in_focus_mag_events=1,
        )
        rep = evaluate_focus_mag_peaking_still_af_illuminator_vault(spec)
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P272_BLOCKED_STILL_ONLY_AF_ILLUMINATOR_OR_AF_IN_MAG)
        self.assertEqual(rep.movie_af_in_focus_mag_events, 1)
        self.assertFalse(rep.still_only_af_in_mag_and_af_illuminator_verified)

    def test_20_reject_movie_sq_af_illuminator_fire_event(self) -> None:
        spec = replace(
            build_default_safe_focus_mag_peaking_still_af_illuminator_vault_spec(),
            shooting_domain="S&Q",
            movie_sq_af_illuminator_fire_events=1,
        )
        rep = evaluate_focus_mag_peaking_still_af_illuminator_vault(spec)
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P272_BLOCKED_STILL_ONLY_AF_ILLUMINATOR_OR_AF_IN_MAG)
        self.assertEqual(rep.movie_sq_af_illuminator_fire_events, 1)

    def test_21_reject_hdmi_clean_feed_focus_mag_or_peaking_leak_pixels(self) -> None:
        for hfeed in ("Info Off", "HDMI RAW"):
            spec = replace(
                build_default_safe_focus_mag_peaking_still_af_illuminator_vault_spec(),
                hdmi_feed_mode=hfeed,
                hdmi_clean_feed_focus_mag_or_peaking_leak_pixels=128,
            )
            rep = evaluate_focus_mag_peaking_still_af_illuminator_vault(spec)
            self.assertFalse(rep.passed, hfeed)
            self.assertEqual(rep.block_code, P272_BLOCKED_HDMI_CLEAN_FEED_OVERLAY_LEAK, hfeed)
            self.assertEqual(rep.hdmi_clean_feed_focus_mag_or_peaking_leak_pixels, 128)
            self.assertFalse(rep.peaking_lcd_only_clean_hdmi_verified)

    def test_22_reject_wrong_factory_defaults_in_pillar47a(self) -> None:
        bad_cases = (
            {"factory_default_auto_mag_in_mf": "Off"},
            {"factory_default_focus_mag_custom_btn": "Custom Button 1"},
            {"factory_default_focus_mag_time": "2 Sec"},
            {"factory_default_still_initial_focus_mag": "x4.0"},
            {"factory_default_movie_initial_focus_mag": "x4.0"},
            {"factory_default_af_in_focus_mag": "Off"},
            {"factory_default_peaking_display": "On"},
            {"factory_default_peaking_select_btn": "Custom Button 1"},
            {"factory_default_peaking_level": "High"},
            {"factory_default_peaking_color": "Red"},
            {"factory_default_af_illuminator": "Off"},
        )
        base = build_default_safe_focus_mag_peaking_still_af_illuminator_vault_spec()
        for patch_kw in bad_cases:
            rep = evaluate_focus_mag_peaking_still_af_illuminator_vault(replace(base, **patch_kw))
            self.assertFalse(rep.passed, str(patch_kw))
            self.assertEqual(rep.block_code, P272_BLOCKED_FOCUS_MAG_DEFAULTS_OR_REGISTER_COUPLING, str(patch_kw))

    def test_23_pillar47a_camera_settings_reset_vs_network_reset_vs_initialize(self) -> None:
        base_args = dict(
            pre_auto_mag_in_mf="Off",
            pre_focus_mag_custom_btn="Custom Button 2",
            pre_focus_mag_time="2 Sec",
            pre_still_initial_focus_mag="x4.0",
            pre_movie_initial_focus_mag="x4.0",
            pre_af_in_focus_mag="Off",
            pre_peaking_display="On",
            pre_peaking_select_btn="Custom Button 1",
            pre_peaking_level="High",
            pre_peaking_color="Red",
            pre_af_illuminator="Off",
        )
        # Camera Settings Reset: Focus items reset to defaults, Custom Keys SURVIVE
        cam_rst = compute_expected_pillar47a_focus_assistant_state_after_reset(
            reset_action="Camera Settings Reset", **base_args
        )
        self.assertEqual(
            cam_rst,
            (
                "On",
                "Custom Button 2",
                "No Limit",
                "x1.0",
                "x1.0",
                "On",
                "Off",
                "Custom Button 1",
                "Mid",
                "White",
                "Auto",
            ),
        )
        # Reset Network Set.: ALL Focus items & Custom Keys SURVIVE
        net_rst = compute_expected_pillar47a_focus_assistant_state_after_reset(
            reset_action="Reset Network Set.", **base_args
        )
        self.assertEqual(
            net_rst,
            (
                "Off",
                "Custom Button 2",
                "2 Sec",
                "x4.0",
                "x4.0",
                "Off",
                "On",
                "Custom Button 1",
                "High",
                "Red",
                "Off",
            ),
        )
        # Initialize: BOTH Focus items AND Custom Keys reset to C5 & Control Wheel Right
        init_rst = compute_expected_pillar47a_focus_assistant_state_after_reset(
            reset_action="Initialize", **base_args
        )
        self.assertEqual(
            init_rst,
            (
                "On",
                "Custom Button 5",
                "No Limit",
                "x1.0",
                "x1.0",
                "On",
                "Off",
                "Control Wheel Right",
                "Mid",
                "White",
                "Auto",
            ),
        )

    def test_24_pillar47a_camera_settings_reset_custom_btn_preservation_accepted(self) -> None:
        spec = replace(
            build_default_safe_focus_mag_peaking_still_af_illuminator_vault_spec(),
            reset_action="Camera Settings Reset",
            pre_focus_mag_custom_btn="Custom Button 3",
            pre_peaking_select_btn="Custom Button 2",
            post_focus_mag_custom_btn="Custom Button 3",
            post_peaking_select_btn="Custom Button 2",
        )
        rep = evaluate_focus_mag_peaking_still_af_illuminator_vault(spec)
        self.assertTrue(rep.passed)
        self.assertTrue(rep.reset_scope_and_camset_restore_verified)

    def test_25_reject_pillar47a_reset_scope_drift_and_invalid_camset_load(self) -> None:
        # Camera Settings Reset illegally wiping custom key or preserving Off
        bad_reset = replace(
            build_default_safe_focus_mag_peaking_still_af_illuminator_vault_spec(),
            reset_action="Camera Settings Reset",
            pre_focus_mag_custom_btn="Custom Button 2",
            post_focus_mag_custom_btn="Custom Button 5",
        )
        rep1 = evaluate_focus_mag_peaking_still_af_illuminator_vault(bad_reset)
        self.assertFalse(rep1.passed)
        self.assertEqual(rep1.block_code, P272_BLOCKED_FOCUS_ASSISTANT_RESET_SCOPE_DRIFT)

        # Cross-model or writable CAMSET Load rejected
        bad_camset = replace(
            build_default_safe_focus_mag_peaking_still_af_illuminator_vault_spec(),
            reset_action="Initialize",
            camset_load_after_reset=True,
            camset_source_model="ILME-FX6",
        )
        rep2 = evaluate_focus_mag_peaking_still_af_illuminator_vault(bad_camset)
        self.assertFalse(rep2.passed)
        self.assertEqual(rep2.block_code, P272_BLOCKED_FOCUS_ASSISTANT_RESET_SCOPE_DRIFT)

        # Slot-2 CAMSET load rejected (recovery vault pinned to Slot-1)
        bad_slot = replace(
            build_default_safe_focus_mag_peaking_still_af_illuminator_vault_spec(),
            reset_action="Initialize",
            camset_load_after_reset=True,
            camset_slot=2,
        )
        rep3 = evaluate_focus_mag_peaking_still_af_illuminator_vault(bad_slot)
        self.assertFalse(rep3.passed)
        self.assertEqual(rep3.block_code, P272_BLOCKED_FOCUS_ASSISTANT_RESET_SCOPE_DRIFT)

    def test_26_reject_pillar47a_slot1_vault_mutation_or_invalid_camset_rw(self) -> None:
        bad_mut = replace(
            build_default_safe_focus_mag_peaking_still_af_illuminator_vault_spec(),
            slot1_vault_mutation_events=1,
            slot1_vault_mutation_bytes=64,
        )
        rep = evaluate_focus_mag_peaking_still_af_illuminator_vault(bad_mut)
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P272_BLOCKED_FOCUS_ASSISTANT_RESET_SCOPE_DRIFT)

        bad_rw = replace(
            build_default_safe_focus_mag_peaking_still_af_illuminator_vault_spec(),
            reset_action="Initialize",
            camset_load_after_reset=True,
            camset_read_only_load=False,
        )
        rep_rw = evaluate_focus_mag_peaking_still_af_illuminator_vault(bad_rw)
        self.assertFalse(rep_rw.passed)
        self.assertEqual(rep_rw.block_code, P272_BLOCKED_FOCUS_ASSISTANT_RESET_SCOPE_DRIFT)

    def test_27_reject_pillar47a_persistent_overlay_escape_and_p2_unlock(self) -> None:
        for bad_dir, lock in (("/setting/overlay", True), ("/tmp/fx3_overlay", False)):
            spec = replace(
                build_default_safe_focus_mag_peaking_still_af_illuminator_vault_spec(),
                overlay_dir=bad_dir,
                p2_blkroset_locked=lock,
            )
            rep = evaluate_focus_mag_peaking_still_af_illuminator_vault(spec)
            self.assertFalse(rep.passed)
            self.assertEqual(rep.block_code, P272_BLOCKED_PERSISTENT_OVERLAY_ESCAPE)

    def test_28_reject_pillar47a_tier0_backup_bin_h0_h3_drift(self) -> None:
        spec = replace(
            build_default_safe_focus_mag_peaking_still_af_illuminator_vault_spec(),
            backup_bin_h3_sha256="0" * 64,
        )
        rep = evaluate_focus_mag_peaking_still_af_illuminator_vault(spec)
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P272_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT)
        self.assertFalse(rep.h0_equals_h3_verified)

    def test_29_reject_pillar47a_invalid_model_menu_domain_or_enum(self) -> None:
        bad_model = replace(
            build_default_safe_focus_mag_peaking_still_af_illuminator_vault_spec(),
            camera_model="ILME-FX6",
        )
        rep1 = evaluate_focus_mag_peaking_still_af_illuminator_vault(bad_model)
        self.assertFalse(rep1.passed)
        self.assertEqual(rep1.block_code, P272_BLOCKED_INVALID_FOCUS_MAG_PEAKING_SPEC)

        bad_enum = replace(
            build_default_safe_focus_mag_peaking_still_af_illuminator_vault_spec(),
            pre_still_initial_focus_mag="x8.0",
        )
        rep2 = evaluate_focus_mag_peaking_still_af_illuminator_vault(bad_enum)
        self.assertFalse(rep2.passed)
        self.assertEqual(rep2.block_code, P272_BLOCKED_FOCUS_MAG_DEFAULTS_OR_REGISTER_COUPLING)

    def test_30_pillar47a_6_scenario_suite_passes_all_6_scenarios(self) -> None:
        res = run_pillar47a_focus_mag_peaking_still_af_illuminator_vault_6_scenario_suite()
        self.assertIsInstance(res, Pillar47ASuiteResult)
        self.assertTrue(res.passed)
        self.assertEqual(res.status, P272_STATUS_VERIFIED_PILLAR_47A)
        self.assertEqual(res.scenarios_passed, 6)
        self.assertEqual(res.scenarios_total, 6)
        self.assertEqual([s.scenario_id for s in res.scenarios], list(P272_PILLAR_47A_SCENARIO_IDS))
        self.assertEqual([s.expected_allowed for s in res.scenarios], [True, True, False, False, False, False])
        for sc in res.scenarios:
            self.assertTrue(sc.passed, sc.scenario_id)

    # ------------------------------------------------------------------
    # 4. Pillar 47B — Area/Date/Time Zero-RF, Video Light 5V, HDMI Res Log
    # ------------------------------------------------------------------

    def test_31_default_pillar47b_safe_spec_passes_with_256_matrix(self) -> None:
        spec = build_default_safe_area_datetime_videolight_hdmires_vault_spec()
        rep = evaluate_area_datetime_videolight_hdmires_vault(spec)
        self.assertIsInstance(rep, AreaDatetimeVideolightHdmiresVaultReport)
        self.assertTrue(rep.passed)
        self.assertEqual(rep.status, P272_STATUS_VERIFIED_PILLAR_47B)
        self.assertIsNone(rep.block_code)
        self.assertTrue(rep.area_datetime_nomenclature_and_4subitems_verified)
        self.assertTrue(rep.zero_rf_creators_app_suppression_verified)
        self.assertTrue(rep.video_light_power_link_5v_900ma_verified)
        self.assertTrue(rep.hdmi_res_auto_and_log_1080p_override_verified)
        self.assertTrue(rep.setup_reset_persistence_and_slot1_vault_verified)
        self.assertTrue(rep.h0_equals_h3_verified)
        self.assertEqual(rep.matrix_states_checked, 256)
        self.assertEqual(rep.effective_hdmi_resolution, "1080p")
        self.assertEqual(rep.slot1_vault_mutation_bytes, 0)

    def test_32_pillar47b_constants_match_wave45(self) -> None:
        self.assertEqual(P272_AREA_DATETIME_MENU_PATH, ("MENU", "Setup", "Area/Date", "Area/Date/Time Setting"))
        self.assertEqual(P272_AREA_DATETIME_LABEL, "Area/Date/Time Setting")
        self.assertEqual(P272_FORBIDDEN_LEGACY_DATETIME_LABEL, "Date/Time Setup")
        self.assertEqual(
            P272_AREA_DATETIME_EXACT_4_SUBITEMS,
            ("Area Setting", "Daylight Savings", "Date/Time", "Date Format"),
        )
        self.assertEqual(P272_AREA_SETTING_DEFAULT, "—")
        self.assertEqual(P272_DAYLIGHT_SAVINGS_DEFAULT, "Off")
        self.assertEqual(P272_DATE_FORMAT_DEFAULT, "YYYY-MM-DD")
        self.assertEqual(P272_AIRPLANE_MODE_MENU_PATH, ("MENU", "Network", "Network Option", "Airplane Mode"))
        self.assertEqual(P272_VIDEO_LIGHT_MODE_MENU_PATH, ("MENU", "Setup", "Setup Option", "Video Light Mode"))
        self.assertEqual(P272_VIDEO_LIGHT_MODE_DEFAULT, "Power Link")
        self.assertEqual(P272_MISHOE_5V_MAX_BUDGET_MA, 900)
        self.assertEqual(P272_HDMI_RESOLUTION_MENU_PATH, ("MENU", "Setup", "External Output", "HDMI Resolution"))
        self.assertEqual(P272_HDMI_RESOLUTION_DEFAULT, "Auto")

    def test_33_reject_legacy_datetime_setup_label_spoof_or_wrong_subitems(self) -> None:
        bad_label = replace(
            build_default_safe_area_datetime_videolight_hdmires_vault_spec(),
            area_datetime_menu_label=P272_FORBIDDEN_LEGACY_DATETIME_LABEL,
        )
        rep1 = evaluate_area_datetime_videolight_hdmires_vault(bad_label)
        self.assertFalse(rep1.passed)
        self.assertEqual(rep1.block_code, P272_BLOCKED_LEGACY_DATETIME_SETUP_SPOOF)
        self.assertEqual(rep1.legacy_datetime_setup_spoof_events, 1)

        bad_subitems = replace(
            build_default_safe_area_datetime_videolight_hdmires_vault_spec(),
            area_datetime_subitems=("Area Setting", "Date/Time", "Date Format"),
        )
        rep2 = evaluate_area_datetime_videolight_hdmires_vault(bad_subitems)
        self.assertFalse(rep2.passed)
        self.assertEqual(rep2.block_code, P272_BLOCKED_LEGACY_DATETIME_SETUP_SPOOF)

    def test_34_reject_zero_rf_creators_app_auto_sync_or_rtc_jump(self) -> None:
        base = build_default_safe_area_datetime_videolight_hdmires_vault_spec()
        for bad_kw in (
            {"airplane_mode": "Off"},
            {"creators_app_auto_time_correction": "On"},
            {"creators_app_auto_area_adjustment": "On"},
            {"passive_tx_bytes_emitted": 16},
            {"unsolicited_rtc_timezone_jump_events": 1},
            {"h0_h3_forensic_timestamps_preserved": False},
        ):
            rep = evaluate_area_datetime_videolight_hdmires_vault(replace(base, **bad_kw))
            self.assertFalse(rep.passed, str(bad_kw))
            self.assertEqual(rep.block_code, P272_BLOCKED_ZERO_RF_CREATORS_APP_SYNC_OR_RTC_JUMP, str(bad_kw))
            self.assertFalse(rep.zero_rf_creators_app_suppression_verified)

    def test_35_video_light_5v_900ma_boundary_accepts_900_and_rejects_901(self) -> None:
        base = build_default_safe_area_datetime_videolight_hdmires_vault_spec()
        for valid_ma in (0, 680, 900):
            rep_ok = evaluate_area_datetime_videolight_hdmires_vault(
                replace(base, mishoe_5v_measured_ma=valid_ma)
            )
            self.assertTrue(rep_ok.passed, f"{valid_ma}mA should pass")
            self.assertTrue(rep_ok.video_light_power_link_5v_900ma_verified)

        for bad_kw in (
            {"mishoe_5v_measured_ma": 901},
            {"mishoe_5v_measured_ma": -1},
            {"mishoe_5v_rail_budget_ma": 950},
            {"mishoe_5v_overcurrent_events": 1},
        ):
            rep_bad = evaluate_area_datetime_videolight_hdmires_vault(replace(base, **bad_kw))
            self.assertFalse(rep_bad.passed, str(bad_kw))
            self.assertEqual(rep_bad.block_code, P272_BLOCKED_MISHOE_5V_OVERCURRENT, str(bad_kw))
            self.assertGreaterEqual(rep_bad.mishoe_5v_overcurrent_events, 1)

    def test_36_hdmi_resolution_log_internal_recording_1080p_downshift_matrix(self) -> None:
        for log_mode in P272_LOG_SHOOTING_MODES:
            for cfg in P272_HDMI_RESOLUTIONS:
                for int_rec in (False, True):
                    for rec_hdmi in P272_REC_MEDIA_DUR_HDMI_MODES:
                        eff, down = compute_expected_effective_hdmi_resolution(
                            configured_hdmi_resolution=cfg,
                            log_shooting_mode=log_mode,
                            internal_recording_active=int_rec,
                            rec_media_dur_hdmi_output=rec_hdmi,
                        )
                        if log_mode != "Off" and int_rec and rec_hdmi == "On":
                            self.assertEqual(eff, "1080p")
                            self.assertTrue(down)
                        else:
                            self.assertEqual(eff, cfg)
                            self.assertFalse(down)

    def test_37_reject_hdmi_resolution_2160p_bypass_under_log_internal_recording(self) -> None:
        for log_mode in ("Cine EI", "Cine EI Quick", "Flexible ISO"):
            spec = replace(
                build_default_safe_area_datetime_videolight_hdmires_vault_spec(),
                pre_hdmi_resolution="2160p",
                post_hdmi_resolution="2160p",
                log_shooting_mode=log_mode,
                internal_recording_active=True,
                rec_media_dur_hdmi_output="On",
                effective_hdmi_resolution="2160p",
            )
            rep = evaluate_area_datetime_videolight_hdmires_vault(spec)
            self.assertFalse(rep.passed, log_mode)
            self.assertEqual(rep.block_code, P272_BLOCKED_HDMI_RES_LOG_1080P_OVERRIDE)
            self.assertFalse(rep.hdmi_res_auto_and_log_1080p_override_verified)

    def test_38_accept_hdmi_2160p_when_off_hdmi_only_or_log_off(self) -> None:
        spec_hdmi_only = replace(
            build_default_safe_area_datetime_videolight_hdmires_vault_spec(),
            pre_hdmi_resolution="2160p",
            post_hdmi_resolution="2160p",
            log_shooting_mode="Cine EI",
            internal_recording_active=True,
            rec_media_dur_hdmi_output="Off(HDMI Only)",
            effective_hdmi_resolution="2160p",
        )
        rep1 = evaluate_area_datetime_videolight_hdmires_vault(spec_hdmi_only)
        self.assertTrue(rep1.passed)
        self.assertEqual(rep1.effective_hdmi_resolution, "2160p")

        spec_log_off = replace(
            build_default_safe_area_datetime_videolight_hdmires_vault_spec(),
            pre_hdmi_resolution="2160p",
            post_hdmi_resolution="2160p",
            log_shooting_mode="Off",
            internal_recording_active=True,
            rec_media_dur_hdmi_output="On",
            effective_hdmi_resolution="2160p",
        )
        rep2 = evaluate_area_datetime_videolight_hdmires_vault(spec_log_off)
        self.assertTrue(rep2.passed)
        self.assertEqual(rep2.effective_hdmi_resolution, "2160p")

    def test_39_pillar47b_setup_reset_survival_vs_initialize_and_rtc_loss(self) -> None:
        base_args = dict(
            pre_area_setting="Tokyo / UTC+9",
            pre_daylight_savings="On",
            pre_date_format="DD-MM-YYYY",
            pre_video_light_mode="REC Link",
            pre_hdmi_resolution="2160p",
            rtc_backup_battery_lost=False,
        )
        # Camera Settings Reset & Reset Network Set. preserve all Setup items
        for act in ("NONE", "Camera Settings Reset", "Reset Network Set."):
            out = compute_expected_pillar47b_setup_state_after_reset(reset_action=act, **base_args)
            self.assertEqual(
                out,
                ("Tokyo / UTC+9", "On", "DD-MM-YYYY", "REC Link", "2160p"),
                act,
            )
        # Initialize resets ALL Setup items
        out_init = compute_expected_pillar47b_setup_state_after_reset(
            reset_action="Initialize", **base_args
        )
        self.assertEqual(out_init, ("—", "Off", "YYYY-MM-DD", "Power Link", "Auto"))

        # RTC backup battery loss clears Area/Date/Time while keeping Video Light & HDMI Res
        rtc_args = dict(base_args)
        rtc_args["rtc_backup_battery_lost"] = True
        out_rtc = compute_expected_pillar47b_setup_state_after_reset(
            reset_action="NONE", **rtc_args
        )
        self.assertEqual(out_rtc, ("—", "Off", "YYYY-MM-DD", "REC Link", "2160p"))

    def test_40_reject_slot1_vault_unlocked_or_mutation_or_setup_reset_drift(self) -> None:
        base = build_default_safe_area_datetime_videolight_hdmires_vault_spec()
        for bad_kw in (
            {"slot1_sdxc_wp_locked": False},
            {"slot1_vault_mutation_events": 1},
            {"slot1_vault_mutation_bytes": 128},
            {"reset_action": "Camera Settings Reset", "post_video_light_mode": "REC Link"},
            {"reset_action": "Initialize", "camset_load_after_reset": True, "camset_source_model": "ILME-FX6"},
            {"reset_action": "Initialize", "camset_load_after_reset": True, "camset_slot": 2},
            {"reset_action": "Initialize", "camset_load_after_reset": True, "camset_read_only_load": False},
        ):
            rep = evaluate_area_datetime_videolight_hdmires_vault(replace(base, **bad_kw))
            self.assertFalse(rep.passed, str(bad_kw))
            self.assertEqual(
                rep.block_code,
                P272_BLOCKED_SETUP_RESET_PERSISTENCE_OR_SLOT1_VAULT_DRIFT,
                str(bad_kw),
            )

    def test_41_reject_pillar47b_persistent_overlay_escape_and_h0_h3_drift(self) -> None:
        base = build_default_safe_area_datetime_videolight_hdmires_vault_spec()
        rep_ov = evaluate_area_datetime_videolight_hdmires_vault(
            replace(base, overlay_dir="/dev/cnflasha/overlay")
        )
        self.assertFalse(rep_ov.passed)
        self.assertEqual(rep_ov.block_code, P272_BLOCKED_PERSISTENT_OVERLAY_ESCAPE)

        rep_h3 = evaluate_area_datetime_videolight_hdmires_vault(
            replace(base, tier0_surfaces_h0_h3_matched=15)
        )
        self.assertFalse(rep_h3.passed)
        self.assertEqual(rep_h3.block_code, P272_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT)
        self.assertFalse(rep_h3.h0_equals_h3_verified)

    def test_42_reject_pillar47b_invalid_factory_defaults_or_spec(self) -> None:
        base = build_default_safe_area_datetime_videolight_hdmires_vault_spec()
        rep1 = evaluate_area_datetime_videolight_hdmires_vault(replace(base, helpguide_id="ilc/9999"))
        self.assertFalse(rep1.passed)
        self.assertEqual(rep1.block_code, P272_BLOCKED_INVALID_DATETIME_VIDEOLIGHT_HDMIRES_SPEC)

        rep2 = evaluate_area_datetime_videolight_hdmires_vault(
            replace(base, factory_default_video_light_mode="Auto")
        )
        self.assertFalse(rep2.passed)
        self.assertEqual(rep2.block_code, P272_BLOCKED_INVALID_DATETIME_VIDEOLIGHT_HDMIRES_SPEC)

        rep3 = evaluate_area_datetime_videolight_hdmires_vault(
            replace(base, pre_date_format="YY-MM-DD")
        )
        self.assertFalse(rep3.passed)
        self.assertEqual(rep3.block_code, P272_BLOCKED_INVALID_DATETIME_VIDEOLIGHT_HDMIRES_SPEC)

    def test_43_pillar47b_6_scenario_suite_passes_all_6_scenarios(self) -> None:
        res = run_pillar47b_area_datetime_videolight_hdmires_vault_6_scenario_suite()
        self.assertIsInstance(res, Pillar47BSuiteResult)
        self.assertTrue(res.passed)
        self.assertEqual(res.status, P272_STATUS_VERIFIED_PILLAR_47B)
        self.assertEqual(res.scenarios_passed, 6)
        self.assertEqual(res.scenarios_total, 6)
        self.assertEqual([s.scenario_id for s in res.scenarios], list(P272_PILLAR_47B_SCENARIO_IDS))
        self.assertEqual([s.expected_allowed for s in res.scenarios], [True, True, False, False, False, False])
        for sc in res.scenarios:
            self.assertTrue(sc.passed, sc.scenario_id)

    # ------------------------------------------------------------------
    # 5. Combined Verifier, Standalone Runner & Unified 47/47 Master
    # ------------------------------------------------------------------

    def test_44_combined_verifier_and_symmetry_alias_pass(self) -> None:
        rep1 = verify_focus_mag_datetime_videolight_hdmires_and_vault()
        rep2 = verify_focus_mag_datetime_videolight_hdmires_vault()
        for rep in (rep1, rep2):
            self.assertIsInstance(rep, FocusMagDatetimeVideolightHdmiresVaultReport)
            self.assertTrue(rep.all_passed)
            self.assertTrue(rep.passed)
            self.assertEqual(rep.status, P272_STATUS_VERIFIED_PILLAR47_SUITE)
            self.assertEqual(rep.donor_snapshot.donor_files_inspected, 16)
            self.assertEqual(rep.raw_firmware_bytes_leaked, 0)
            self.assertEqual(rep.physical_device_writes, 0)
            self.assertEqual(rep.slot1_vault_mutation_bytes, 0)
            d = rep.to_dict()
            self.assertEqual(d["status"], P272_STATUS_VERIFIED_PILLAR47_SUITE)

    def test_45_combined_verifier_propagates_negative_subreport(self) -> None:
        bad_a = replace(
            build_default_safe_focus_mag_peaking_still_af_illuminator_vault_spec(),
            auto_mag_menu_label=P272_FORBIDDEN_LEGACY_MF_ASSIST_LABEL,
        )
        rep = verify_focus_mag_datetime_videolight_hdmires_vault(
            focus_mag_spec=bad_a,
            force_clean_room=True,
        )
        self.assertFalse(rep.passed)
        self.assertFalse(rep.all_passed)
        self.assertEqual(rep.status, P272_STATUS_FAIL_PILLAR47_SUITE)
        self.assertEqual(rep.legacy_mf_assist_spoof_events, 1)

    def test_46_standalone_pillar47_suite_passes_12_of_12_scenarios(self) -> None:
        rep = run_pillar47_standalone_suite()
        self.assertIsInstance(rep, Pillar47StandaloneReport)
        self.assertTrue(rep.all_passed)
        self.assertEqual(rep.status, P272_STATUS_VERIFIED_PILLAR47_SUITE)
        self.assertEqual(rep.pillar_47a_focus_mag_peaking_still_af_illuminator_vault.scenarios_passed, 6)
        self.assertEqual(rep.pillar_47b_area_datetime_videolight_hdmires_vault.scenarios_passed, 6)
        self.assertEqual(len(rep.suite_sha256), 64)
        self.assertEqual(rep.physical_device_writes, 0)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertTrue(rep.cnflasha_userspace_write_blocked)

    def test_47_standalone_suite_clean_room_mode_parity(self) -> None:
        rep = run_pillar47_standalone_suite(force_clean_room=True)
        self.assertTrue(rep.all_passed)
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(rep.donor_snapshot.donor_files_inspected, 16)
        self.assertTrue(rep.to_dict()["all_passed"])

    def test_48_master_47pillar_recovery_passes_47_of_47_and_timing(self) -> None:
        rep = evaluate_realhw_47pillar_recovery_master()
        self.assertIsInstance(rep, Master47PillarRecoveryReport)
        self.assertTrue(rep.all_passed)
        self.assertEqual(rep.status, P272_STATUS_VERIFIED_47OF47_AGGREGATOR)
        self.assertEqual(rep.pillar_count, 47)
        self.assertEqual(rep.pillars_passed, 47)
        self.assertEqual(rep.failed_pillars, ())
        self.assertEqual(len(rep.pillars), 47)
        self.assertTrue(rep.under_6s_budget)
        self.assertTrue(rep.nominal_under_4_0s)
        if os.environ.get("GITHUB_ACTIONS", "").strip().lower() != "true":
            self.assertLess(rep.elapsed_seconds, P272_FAST_CLI_BUDGET_SECONDS)
            self.assertTrue(rep.under_2s_fast_cli_budget)
        self.assertEqual(len(rep.master_47pillar_sha256), 64)

    def test_49_master_47pillar_preserves_all_46_pillars_and_rollup_metrics(self) -> None:
        rep = evaluate_realhw_47pillar_recovery_master(force_clean_room=True)
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(rep.all_passed)
        self.assertEqual([p.pillar_id for p in rep.pillars], list(MASTER_47_PILLAR_IDS))
        self.assertEqual(rep.slot1_vault_folder_mutation_events, 0)
        self.assertEqual(rep.slot1_vault_folder_mutation_bytes, 0)
        self.assertEqual(rep.gamma_assist_log_lockout_bypass_events, 0)
        self.assertEqual(rep.gamma_assist_external_hdmi_leak_events, 0)
        self.assertEqual(rep.tcub_camera_reset_wipe_or_format_violations, 0)
        self.assertFalse(rep.fx3_has_builtin_end_filter)
        self.assertEqual(rep.e_nd_actuator_tx_count, 0)
        self.assertEqual(rep.legacy_v1_audio_level_menu_spoof_events, 0)
        self.assertEqual(rep.photographer_copyright_pii_leaked_bytes, 0)
        self.assertEqual(rep.version_dialog_flash_writes, 0)
        self.assertGreaterEqual(rep.bodydata_flash_attempts_blocked, 1)
        self.assertFalse(rep.fx3_has_builtin_evf)
        self.assertFalse(rep.fx3_has_var_shutter)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)
        self.assertEqual(rep.physical_device_writes, 0)

    def test_50_master_47pillar_aliases_match_primary(self) -> None:
        r1 = evaluate_47pillar_recovery_master(force_clean_room=True)
        r2 = verify_47pillar_recovery_suite(force_clean_room=True)
        self.assertEqual(r1.status, P272_STATUS_VERIFIED_47OF47_AGGREGATOR)
        self.assertEqual(r2.status, P272_STATUS_VERIFIED_47OF47_AGGREGATOR)
        self.assertEqual(r1.master_47pillar_sha256, r2.master_47pillar_sha256)

    def test_51_master_47pillar_fault_injection_pillar_47(self) -> None:
        pid47 = MASTER_47_PILLAR_IDS[46]
        rep = evaluate_realhw_47pillar_recovery_master(
            force_clean_room=True,
            fault_inject_pillar=pid47,
        )
        self.assertFalse(rep.all_passed)
        self.assertEqual(rep.status, P272_STATUS_FAIL_47OF47_AGGREGATOR)
        self.assertEqual(rep.pillars_passed, 46)
        self.assertEqual(rep.failed_pillars, (pid47,))

    def test_52_master_47pillar_fault_injection_pillar_1_and_46(self) -> None:
        for idx in (0, 45):
            pid = MASTER_47_PILLAR_IDS[idx]
            rep = evaluate_realhw_47pillar_recovery_master(
                force_clean_room=True,
                fault_inject_pillar=pid,
            )
            self.assertFalse(rep.all_passed)
            self.assertEqual(rep.pillars_passed, 46)
            self.assertEqual(rep.failed_pillars, (pid,))

    def test_53_master_47pillar_rejects_unknown_fault_inject_pillar(self) -> None:
        with self.assertRaises(ValueError):
            evaluate_realhw_47pillar_recovery_master(
                force_clean_room=True,
                fault_inject_pillar="nonexistent_pillar_99",
            )

    def test_54_master_47pillar_delegates_to_evaluate_realhw_46pillar_recovery_master(self) -> None:
        with mock.patch.object(
            p272,
            "evaluate_realhw_46pillar_recovery_master",
            wraps=p272.evaluate_realhw_46pillar_recovery_master,
        ) as spy_46:
            rep = evaluate_realhw_47pillar_recovery_master(force_clean_room=True)
            self.assertTrue(rep.all_passed)
            spy_46.assert_called_once()
            self.assertIsInstance(spy_46.call_args.kwargs.get("force_clean_room"), bool)

    def test_55_master_47pillar_catches_46pillar_rollup_tampering(self) -> None:
        real_46 = p272.evaluate_realhw_46pillar_recovery_master(force_clean_room=True)
        self.assertIsInstance(real_46, Master46PillarRecoveryReport)
        tampered_46 = replace(real_46, tcub_camera_reset_wipe_or_format_violations=1)
        with mock.patch.object(p272, "evaluate_realhw_46pillar_recovery_master", return_value=tampered_46):
            rep = evaluate_realhw_47pillar_recovery_master(force_clean_room=True)
            self.assertFalse(rep.all_passed)
            self.assertTrue(any("tcub_camera_reset_wipe_or_format_violations" in e for e in rep.errors))

    # ------------------------------------------------------------------
    # 6. CLI Integration (`cli_main.main` & Subprocess Execution)
    # ------------------------------------------------------------------

    def test_56_cli_verify_focus_mag_datetime_videolight_hdmires_vault_text(self) -> None:
        buf = io.StringIO()
        with mock.patch.object(sys, "argv", ["fx3_recovery", "verify-focus-mag-datetime-videolight-hdmires-vault"]):
            with redirect_stdout(buf):
                rc = cli_main.main()
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("VERIFIED_PILLAR47_FOCUS_MAG_DATETIME_VIDEOLIGHT_HDMIRES_VAULT", out)
        self.assertIn("legacy_mf_assist_spoof_events=0", out)
        self.assertIn("mishoe_5v_overcurrent_events=0", out)

    def test_57_cli_verify_focus_mag_datetime_videolight_hdmires_vault_json_and_out(self) -> None:
        work_tests = _repo_root() / "work" / "_tests"
        work_tests.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="p272_p47_", dir=work_tests) as td:
            out_dir = Path(td) / "p47_out"
            rep_file = out_dir / "pillar47-focus-mag-datetime-videolight-hdmires-vault-report.json"
            buf = io.StringIO()
            with mock.patch.object(
                sys,
                "argv",
                [
                    "fx3_recovery",
                    "verify-focus-mag-datetime-videolight-hdmires-vault",
                    "--force-clean-room",
                    "--json",
                    "--out",
                    str(out_dir),
                ],
            ):
                with redirect_stdout(buf):
                    rc = cli_main.main()
            self.assertEqual(rc, 0)
            payload = json.loads(buf.getvalue())
            self.assertEqual(payload["verification_mode"], "CLEAN_ROOM_SYNTHETIC")
            self.assertTrue(payload["all_passed"])
            self.assertEqual(
                payload["pillar_47a_focus_mag_peaking_still_af_illuminator_vault"]["scenarios_passed"],
                6,
            )
            self.assertEqual(
                payload["pillar_47b_area_datetime_videolight_hdmires_vault"]["scenarios_passed"],
                6,
            )
            self.assertTrue(rep_file.is_file())
            self.assertEqual(json.loads(rep_file.read_text(encoding="utf-8"))["status"], payload["status"])

    def test_58_cli_verify_47pillar_recovery_text_and_clean_room(self) -> None:
        buf = io.StringIO()
        with mock.patch.object(sys, "argv", ["fx3_recovery", "verify-47pillar-recovery", "--clean-room"]):
            with redirect_stdout(buf):
                rc = cli_main.main()
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("status=VERIFIED_47OF47_PILLAR_RECOVERY_MASTER", out)
        self.assertIn("mode=CLEAN_ROOM_SYNTHETIC", out)
        self.assertIn("pillars=47/47", out)
        self.assertIn("raw_firmware_bytes_leaked=0", out)

    def test_59_cli_verify_47pillar_recovery_json_and_out(self) -> None:
        work_tests = _repo_root() / "work" / "_tests"
        work_tests.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="p272_m47_", dir=work_tests) as td:
            out_dir = Path(td) / "master47_out"
            rep_file = out_dir / "47pillar-recovery-master-report.json"
            buf = io.StringIO()
            with mock.patch.object(
                sys,
                "argv",
                [
                    "fx3_recovery",
                    "verify-47pillar-recovery",
                    "--force-clean-room",
                    "--json",
                    "--out",
                    str(out_dir),
                ],
            ):
                with redirect_stdout(buf):
                    rc = cli_main.main()
            self.assertEqual(rc, 0)
            payload = json.loads(buf.getvalue())
            self.assertEqual(payload["pillar_count"], 47)
            self.assertEqual(payload["pillars_passed"], 47)
            self.assertEqual(payload["status"], P272_STATUS_VERIFIED_47OF47_AGGREGATOR)
            self.assertEqual(len(payload["pillars"]), 47)
            self.assertTrue(rep_file.is_file())
            self.assertEqual(
                json.loads(rep_file.read_text(encoding="utf-8"))["master_47pillar_sha256"],
                payload["master_47pillar_sha256"],
            )

    def test_60_cli_help_does_not_crash_on_percent_formatting(self) -> None:
        for subcmd in ("verify-focus-mag-datetime-videolight-hdmires-vault", "verify-47pillar-recovery"):
            buf = io.StringIO()
            with mock.patch.object(sys, "argv", ["fx3_recovery", subcmd, "--help"]):
                with redirect_stdout(buf):
                    with self.assertRaises(SystemExit) as ctx:
                        cli_main.main()
            self.assertEqual(ctx.exception.code, 0)
            self.assertIn(subcmd, buf.getvalue())

    def test_61_subprocess_cli_verify_47pillar_recovery_fast_budget(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONPATH"] = str(_repo_root() / "outputs" / "fx3-recovery-adapter")
        proc = subprocess.run(
            [sys.executable, "-B", "-m", "fx3_recovery", "verify-47pillar-recovery", "--force-clean-room", "--json"],
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertTrue(payload["all_passed"])
        self.assertEqual(payload["pillars_passed"], 47)
        self.assertTrue(payload["under_6s_budget"])

    # ------------------------------------------------------------------
    # 7. Extended Edge Cases & Enum Coverage
    # ------------------------------------------------------------------

    def test_62_all_focus_mag_custom_buttons_and_peaking_options_accepted(self) -> None:
        base = build_default_safe_focus_mag_peaking_still_af_illuminator_vault_spec()
        for btn in P272_ALLOWED_FOCUS_MAG_CUSTOM_BTNS:
            spec = replace(
                base,
                reset_action="NONE",
                pre_focus_mag_custom_btn=btn,
                post_focus_mag_custom_btn=btn,
                pre_auto_mag_in_mf="On",
                pre_focus_mag_time="No Limit",
                pre_still_initial_focus_mag="x1.0",
                pre_movie_initial_focus_mag="x1.0",
                pre_af_in_focus_mag="On",
                pre_peaking_display="Off",
                pre_peaking_select_btn=P272_PEAKING_DISPLAY_SELECT_DEFAULT,
                pre_peaking_level="Mid",
                pre_peaking_color="White",
                pre_af_illuminator="Auto",
            )
            self.assertTrue(evaluate_focus_mag_peaking_still_af_illuminator_vault(spec).passed, btn)

        for lvl in P272_PEAKING_LEVELS:
            for col in P272_PEAKING_COLORS:
                spec2 = replace(
                    base,
                    reset_action="NONE",
                    pre_auto_mag_in_mf="On",
                    pre_focus_mag_custom_btn=P272_FOCUS_MAGNIFIER_CUSTOM_BTN_DEFAULT,
                    pre_focus_mag_time="No Limit",
                    pre_still_initial_focus_mag="x1.0",
                    pre_movie_initial_focus_mag="x1.0",
                    pre_af_in_focus_mag="On",
                    pre_peaking_display="On",
                    pre_peaking_select_btn=P272_PEAKING_DISPLAY_SELECT_DEFAULT,
                    pre_peaking_level=lvl,
                    pre_peaking_color=col,
                    pre_af_illuminator="Auto",
                    post_peaking_display="On",
                    post_peaking_level=lvl,
                    post_peaking_color=col,
                )
                self.assertTrue(evaluate_focus_mag_peaking_still_af_illuminator_vault(spec2).passed)

    def test_63_all_camset_01_to_10_filenames_accepted_in_pillar47a_and_47b(self) -> None:
        base_a = build_default_safe_focus_mag_peaking_still_af_illuminator_vault_spec()
        base_b = build_default_safe_area_datetime_videolight_hdmires_vault_spec()
        for fname in P272_CAMSET_FILENAMES:
            spec_a = replace(base_a, reset_action="Initialize", camset_load_after_reset=True, camset_filename=fname)
            self.assertTrue(evaluate_focus_mag_peaking_still_af_illuminator_vault(spec_a).passed, fname)
            spec_b = replace(
                base_b,
                reset_action="Initialize",
                camset_load_after_reset=True,
                camset_filename=fname,
                post_area_setting="Los Angeles / UTC-8",
                effective_hdmi_resolution="1080p",
            )
            self.assertTrue(evaluate_area_datetime_videolight_hdmires_vault(spec_b).passed, fname)

    def test_64_all_video_light_modes_and_date_formats_accepted(self) -> None:
        base = build_default_safe_area_datetime_videolight_hdmires_vault_spec()
        for vlm in P272_VIDEO_LIGHT_MODES:
            for dfmt in P272_DATE_FORMATS:
                spec = replace(
                    base,
                    pre_video_light_mode=vlm,
                    post_video_light_mode=vlm,
                    pre_date_format=dfmt,
                    post_date_format=dfmt,
                )
                self.assertTrue(evaluate_area_datetime_videolight_hdmires_vault(spec).passed, f"{vlm}/{dfmt}")

    def test_65_all_fx3_supported_fw_versions_accepted(self) -> None:
        base_a = build_default_safe_focus_mag_peaking_still_af_illuminator_vault_spec()
        base_b = build_default_safe_area_datetime_videolight_hdmires_vault_spec()
        for fw in P272_FX3_SUPPORTED_FW_VERSIONS:
            self.assertTrue(evaluate_focus_mag_peaking_still_af_illuminator_vault(replace(base_a, fw_version=fw)).passed)
            self.assertTrue(evaluate_area_datetime_videolight_hdmires_vault(replace(base_b, fw_version=fw)).passed)

    def test_66_reject_stage_b_nonzero_backup_bin_writes(self) -> None:
        rep_a = evaluate_focus_mag_peaking_still_af_illuminator_vault(
            replace(build_default_safe_focus_mag_peaking_still_af_illuminator_vault_spec(), stage_b_backup_bin_writes=1)
        )
        self.assertFalse(rep_a.passed)
        self.assertEqual(rep_a.block_code, P272_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT)

        rep_b = evaluate_area_datetime_videolight_hdmires_vault(
            replace(build_default_safe_area_datetime_videolight_hdmires_vault_spec(), stage_b_backup_bin_writes=1)
        )
        self.assertFalse(rep_b.passed)
        self.assertEqual(rep_b.block_code, P272_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT)

    def test_67_reject_all_forbidden_persistent_targets_on_overlay(self) -> None:
        base_a = build_default_safe_focus_mag_peaking_still_af_illuminator_vault_spec()
        base_b = build_default_safe_area_datetime_videolight_hdmires_vault_spec()
        for target in ("/setting/x", "p2:/setting/x", "/dev/nflasha", "/dev/pnflasha", "/dev/cnflasha", "/dev/mmcblk0"):
            rep_a = evaluate_focus_mag_peaking_still_af_illuminator_vault(replace(base_a, overlay_dir=target))
            self.assertEqual(rep_a.block_code, P272_BLOCKED_PERSISTENT_OVERLAY_ESCAPE, target)
            rep_b = evaluate_area_datetime_videolight_hdmires_vault(replace(base_b, overlay_dir=target))
            self.assertEqual(rep_b.block_code, P272_BLOCKED_PERSISTENT_OVERLAY_ESCAPE, target)

    def test_68_reject_non_on_off_focus_mag_and_peaking_enums(self) -> None:
        base_a = build_default_safe_focus_mag_peaking_still_af_illuminator_vault_spec()
        for bad_kw in (
            {"saved_auto_mag_in_mf": "Yes"},
            {"post_focus_mag_time": "10 Sec"},
            {"post_peaking_select_btn": "Dial 1"},
            {"post_af_illuminator": "Always"},
        ):
            rep = evaluate_focus_mag_peaking_still_af_illuminator_vault(replace(base_a, **bad_kw))
            self.assertFalse(rep.passed, str(bad_kw))
            self.assertEqual(rep.block_code, P272_BLOCKED_FOCUS_MAG_DEFAULTS_OR_REGISTER_COUPLING)

    def test_69_pillar47a_and_47b_report_digests_are_deterministic_sha256(self) -> None:
        a1 = evaluate_focus_mag_peaking_still_af_illuminator_vault(
            build_default_safe_focus_mag_peaking_still_af_illuminator_vault_spec()
        )
        a2 = evaluate_focus_mag_peaking_still_af_illuminator_vault(
            build_default_safe_focus_mag_peaking_still_af_illuminator_vault_spec()
        )
        self.assertEqual(len(a1.digest_sha256), 64)
        self.assertEqual(a1.digest_sha256, a2.digest_sha256)

        b1 = evaluate_area_datetime_videolight_hdmires_vault(
            build_default_safe_area_datetime_videolight_hdmires_vault_spec()
        )
        b2 = evaluate_area_datetime_videolight_hdmires_vault(
            build_default_safe_area_datetime_videolight_hdmires_vault_spec()
        )
        self.assertEqual(len(b1.digest_sha256), 64)
        self.assertEqual(b1.digest_sha256, b2.digest_sha256)

    def test_70_all_16_donor_relpaths_are_non_empty_and_distinct(self) -> None:
        snap = inspect_phase272_donors_readonly(force_clean_room=True)
        relpaths = [a.relpath for a in snap.artifacts]
        self.assertEqual(len(relpaths), 16)
        self.assertEqual(len(set(relpaths)), 16)
        self.assertTrue(all(bool(r) for r in relpaths))

    def test_71_verify_47_cli_subcommand_and_46_backward_compatibility(self) -> None:
        buf46 = io.StringIO()
        with mock.patch.object(sys, "argv", ["fx3_recovery", "verify-46pillar-recovery", "--force-clean-room"]):
            with redirect_stdout(buf46):
                rc46 = cli_main.main()
        self.assertEqual(rc46, 0)
        self.assertIn("VERIFIED_46OF46_PILLAR_RECOVERY_MASTER", buf46.getvalue())

        buf47 = io.StringIO()
        with mock.patch.object(sys, "argv", ["fx3_recovery", "verify-47pillar-recovery", "--force-clean-room"]):
            with redirect_stdout(buf47):
                rc47 = cli_main.main()
        self.assertEqual(rc47, 0)
        self.assertIn("VERIFIED_47OF47_PILLAR_RECOVERY_MASTER", buf47.getvalue())

    def test_72_pillar47a_still_vs_movie_initial_mag_in_standalone_scenario_2(self) -> None:
        res = run_pillar47a_focus_mag_peaking_still_af_illuminator_vault_6_scenario_suite()
        sc2 = res.scenarios[1]
        self.assertTrue(sc2.passed)
        self.assertTrue(sc2.actual_allowed)

    def test_73_pillar47b_hdmi_off_only_2160p_in_standalone_scenario_2(self) -> None:
        res = run_pillar47b_area_datetime_videolight_hdmires_vault_6_scenario_suite()
        sc2 = res.scenarios[1]
        self.assertTrue(sc2.passed)
        self.assertTrue(sc2.actual_allowed)

    def test_74_standalone_suite_fails_gracefully_if_donor_budget_missed(self) -> None:
        fake_snap = replace(
            inspect_phase272_donors_readonly(force_clean_room=True),
            under_0_15s_budget=False,
            elapsed_seconds=0.99,
        )
        with mock.patch.object(p272, "inspect_phase272_donors_readonly", return_value=fake_snap):
            rep = run_pillar47_standalone_suite(force_clean_room=True)
            self.assertFalse(rep.all_passed)
            self.assertEqual(rep.status, P272_STATUS_FAIL_PILLAR47_SUITE)
            self.assertTrue(any("budget" in e for e in rep.errors))

    def test_75_donor_elf_token_helper_rejects_bad_magic_and_missing_tokens(self) -> None:
        ok_bad, msg_bad = p272._check_elf64_aarch64_tokens(b"NOT_ELF" * 16, ())
        self.assertFalse(ok_bad)
        self.assertEqual(msg_bad, "NOT_ELF")

        # Valid ELF64 AArch64 header (little-endian, EM_AARCH64=183) missing expected token
        hdr = bytearray(64)
        hdr[0:4] = b"\x7fELF"
        hdr[4] = 2  # ELFCLASS64
        hdr[5] = 1  # ELFDATA2LSB
        hdr[18] = 183  # EM_AARCH64
        ok_miss, msg_miss = p272._check_elf64_aarch64_tokens(bytes(hdr), (b"Backup_read",))
        self.assertFalse(ok_miss)
        self.assertIn("MISSING_TOKENS", msg_miss)

        # Valid ELF64 AArch64 header with token present
        ok_hit, msg_hit = p272._check_elf64_aarch64_tokens(bytes(hdr) + b"\x00Backup_read\x00", (b"Backup_read",))
        self.assertTrue(ok_hit)
        self.assertIn("Backup_read", msg_hit)


if __name__ == "__main__":
    unittest.main()
