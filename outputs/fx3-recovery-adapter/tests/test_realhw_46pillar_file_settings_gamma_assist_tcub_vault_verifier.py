"""Phase 269 — Dual-mode unit tests for Pillar 46 (`Movie [File Settings]` `Cam ID + Reel#` &
`<= 37`-char `Title Name Settings` `"C"` default with fixed `PRIVATE/M4ROOT/CLIP` folder vs Still
`[File/Folder Settings]` `3`-char `DSC` prefix with `_` forbidden at index 0, `100MSDCF` vs `Date Form`,
`[Camera Settings Reset]` survival vs `[Initialize]` reset, and `Slot-1` recovery vault DCIM firewall;
plus `[Gamma Display Assist]` hard-locked `Off` under `[Log Shooting] != Off` & camera-LCD-only scope
for clean external HDMI vs `[Display LUT]` / `[Select LUT]` `3` presets + `User1..User16`, `[Auto Review]`
`Off` cinema default, and all 6 `[TC/UB]` non-resettable timecode parameters surviving
`[Camera Settings Reset]`) and unified `46/46` recovery master
(`verify-46pillar-recovery` / `verify-file-settings-gamma-assist-tcub-vault`)."""

from __future__ import annotations

from contextlib import redirect_stdout
from dataclasses import replace
import io
import json
import os
from pathlib import Path
import struct
import tempfile
import unittest
from unittest import mock

import fx3_recovery
from fx3_recovery import __main__ as cli_main
from fx3_recovery import (
    realhw_46pillar_file_settings_gamma_assist_tcub_vault_verifier as p269,
)
from fx3_recovery.realhw_45pillar_release_wo_card_lens_audio_meter_copyright_vault_verifier import (
    MASTER_45_PILLAR_SPECS,
    Master45PillarRecoveryReport,
)
from fx3_recovery.realhw_46pillar_file_settings_gamma_assist_tcub_vault_verifier import (
    ALLOW_BOOT_PARTITION_TARGETING,
    ALLOW_DESTRUCTIVE_FASTBOOT,
    ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS,
    ALLOW_PERSISTENT_JIRITSU_WRITES,
    CNFLASHA_USERSPACE_WRITE_BLOCKED,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    ISP_WRITE_AUTHORIZED,
    LIVE_USB_IOKIT_TRANSMIT_ENABLED,
    MASTER_46_PILLAR_COUNT,
    MASTER_46_PILLAR_IDS,
    MASTER_46_PILLAR_SPECS,
    OTP_FUSE_TOUCHES,
    OTP_FUSE_WRITES,
    P269_AUTO_REVIEW_DEFAULT,
    P269_AUTO_REVIEW_MENU_PATH,
    P269_AUTO_REVIEW_MODES,
    P269_BLOCKED_FILE_FOLDER_RESET_VS_INITIALIZE_SCOPE_DRIFT,
    P269_BLOCKED_GAMMA_ASSIST_EXTERNAL_HDMI_LEAK_OR_AUTO_REVIEW_VIOLATION,
    P269_BLOCKED_GAMMA_ASSIST_LOG_SHOOTING_LOCKOUT_BYPASS,
    P269_BLOCKED_INVALID_FILE_OR_FOLDER_SETTINGS_SPEC,
    P269_BLOCKED_INVALID_GAMMA_ASSIST_LUT_TCUB_SPEC,
    P269_BLOCKED_MOVIE_FILE_SETTINGS_OR_37CHAR_TITLE_VIOLATION,
    P269_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
    P269_BLOCKED_SAFETY_POLICY_VIOLATION,
    P269_BLOCKED_SLOT1_VAULT_DCIM_FOLDER_MUTATION,
    P269_BLOCKED_STILL_PREFIX_UNDERSCORE_OR_FOLDER_FORM_VIOLATION,
    P269_BLOCKED_TCUB_OR_SETUP_RESET_PERSISTENCE_OR_NDF_DRIFT,
    P269_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
    P269_CAMERA_POSITIONS,
    P269_CAMERA_POSITION_DEFAULT,
    P269_CAMSET_FILENAMES,
    P269_CAM_ID_DEFAULT,
    P269_CAM_ID_LETTERS,
    P269_DISPLAY_LUT_DEFAULT,
    P269_DISPLAY_LUT_MENU_PATH,
    P269_DISPLAY_LUT_MODES,
    P269_ENV_CLEAN_ROOM_TEST,
    P269_FIXED_MOVIE_CLIP_FOLDER,
    P269_FORCED_NDF_FRAME_RATES,
    P269_FX3_FW_VERSION,
    P269_FX3_HELPGUIDE_ID,
    P269_FX3_MODEL_ID,
    P269_FX3_MODEL_NAME,
    P269_FX3_SUPPORTED_FW_VERSIONS,
    P269_FX6_DONOR_FW_VERSION,
    P269_FX6_DONOR_MODEL_NAME,
    P269_GAMMA_ASSIST_EXTERNAL_HDMI_LEAK_EVENTS,
    P269_GAMMA_ASSIST_LOG_LOCKOUT_BYPASS_EVENTS,
    P269_GAMMA_DISPLAY_ASSIST_DEFAULT,
    P269_GAMMA_DISPLAY_ASSIST_MENU_PATH,
    P269_GAMMA_DISPLAY_ASSIST_MODES,
    P269_GAMMA_DISP_ASSIST_TYPES,
    P269_GAMMA_DISP_ASSIST_TYPE_DEFAULT,
    P269_GAMMA_DISP_ASSIST_TYP_MENU_PATH,
    P269_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    P269_LOG_SHOOTING_MODES,
    P269_MOVIE_CUSTOM_FOLDER_OR_TITLE_OVERFLOW_EVENTS,
    P269_MOVIE_FILE_NAME_FORMATS,
    P269_MOVIE_FILE_NAME_FORMAT_DEFAULT,
    P269_MOVIE_FILE_NUMBER_DEFAULT,
    P269_MOVIE_FILE_NUMBER_MODES,
    P269_MOVIE_FILE_SETTINGS_ITEMS,
    P269_MOVIE_FILE_SETTINGS_MENU_PATH,
    P269_MOVIE_FRAME_RATES,
    P269_PILLAR_46A_SCENARIO_IDS,
    P269_PILLAR_46B_SCENARIO_IDS,
    P269_PINNED_FX3_APPFW_702_BYTES,
    P269_PINNED_FX3_APPFW_702_HDR4K_SHA256,
    P269_PINNED_FX3_BACKUP_BIN_BYTES,
    P269_PINNED_FX3_BACKUP_BIN_SHA256,
    P269_PINNED_FX3_BODYDATA_BYTES,
    P269_PINNED_FX3_BODYDATA_HDR4K_SHA256,
    P269_PINNED_FX3_LIBINFRAFSYS_SO_BYTES,
    P269_PINNED_FX3_LIBINFRAFSYS_SO_SHA256,
    P269_PINNED_FX3_LIBINFRAMEDIACOMMON_SO_BYTES,
    P269_PINNED_FX3_LIBINFRAMEDIACOMMON_SO_SHA256,
    P269_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_BYTES,
    P269_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_SHA256,
    P269_PINNED_FX3_LIBINFRAMEDIADETECT_SO_BYTES,
    P269_PINNED_FX3_LIBINFRAMEDIADETECT_SO_SHA256,
    P269_PINNED_FX3_LIBINFRAMEDIAMOUNT_SO_BYTES,
    P269_PINNED_FX3_LIBINFRAMEDIAMOUNT_SO_SHA256,
    P269_PINNED_FX3_LIBINFRAMETASUPPLIER_SO_BYTES,
    P269_PINNED_FX3_LIBINFRAMETASUPPLIER_SO_SHA256,
    P269_PINNED_FX6_APPFW_601_BYTES,
    P269_PINNED_FX6_APPFW_601_HDR4K_SHA256,
    P269_PINNED_FX6_LIBINFRASETUPFILE_SO_BYTES,
    P269_PINNED_FX6_LIBINFRASETUPFILE_SO_SHA256,
    P269_REEL_NUMBER_DEFAULT,
    P269_REEL_NUMBER_MAX,
    P269_REEL_NUMBER_MIN,
    P269_RESET_ACTIONS,
    P269_SELECT_LUT_DEFAULT,
    P269_SELECT_LUT_MENU_PATH,
    P269_SELECT_LUT_MODES,
    P269_SELECT_LUT_PRESETS,
    P269_SELECT_LUT_USER_SLOTS,
    P269_SHOOTING_DOMAINS,
    P269_SLOT1_VAULT_FOLDER_MUTATION_BYTES,
    P269_SLOT1_VAULT_FOLDER_MUTATION_EVENTS,
    P269_SLOT1_VAULT_SLOT,
    P269_STAGE_B_VOLATILE_OVERLAY_DIR,
    P269_STATUS_FAIL_46OF46_AGGREGATOR,
    P269_STATUS_FAIL_PILLAR46_SUITE,
    P269_STATUS_REJECTED_PILLAR_46A,
    P269_STATUS_REJECTED_PILLAR_46B,
    P269_STATUS_VERIFIED_46OF46_AGGREGATOR,
    P269_STATUS_VERIFIED_PILLAR46_SUITE,
    P269_STATUS_VERIFIED_PILLAR_46A,
    P269_STATUS_VERIFIED_PILLAR_46B,
    P269_STILL_FILE_FOLDER_ITEMS,
    P269_STILL_FILE_FOLDER_MENU_PATH,
    P269_STILL_FILE_NUMBER_DEFAULT,
    P269_STILL_FILE_NUMBER_MODES,
    P269_STILL_FOLDER_NAME_DEFAULT,
    P269_STILL_FOLDER_NAME_MODES,
    P269_STILL_PREFIX_UNDERSCORE_LEAD_OR_LEN_VIOLATIONS,
    P269_STILL_SET_FILE_NAME_DEFAULT,
    P269_STILL_SET_FILE_NAME_LEN,
    P269_TCUB_CAMERA_RESET_WIPE_OR_FORMAT_VIOLATIONS,
    P269_TCUB_DISP_SETTING_DEFAULT,
    P269_TCUB_DISP_SETTING_MENU_PATH,
    P269_TCUB_DISP_SETTING_MODES,
    P269_TCUB_EXACT_6_ITEMS,
    P269_TCUB_MENU_PATH,
    P269_TC_FORMAT_DEFAULT,
    P269_TC_FORMAT_MODES,
    P269_TC_MAKE_DEFAULT,
    P269_TC_MAKE_MODES,
    P269_TC_PRESET_DEFAULT,
    P269_TC_RUN_DEFAULT,
    P269_TC_RUN_MODES,
    P269_TIER0_SURFACE_COUNT,
    P269_TITLE_NAME_DEFAULT,
    P269_TITLE_NAME_MAX_CHARS,
    P269_UB_PRESET_DEFAULT,
    P269_UB_TIME_REC_DEFAULT,
    P269_UB_TIME_REC_MODES,
    PASSIVE_TX_BYTES_EMITTED,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHASE269_PHASE_NUMBER,
    PHASE269_SCHEMA,
    PHASE269_VERSION,
    PHYSICAL_DEVICE_WRITES,
    PHYSICAL_USB_PACKETS_EMITTED,
    RAW_FIRMWARE_BYTES_LEAKED,
    READ_ONLY_DONOR_ACCESS,
    RPMB_COUNTER_INCREMENTS,
    SPI_NOR_WRITE_AUTHORIZED,
    FileSettingsAndStillFolderVaultSpec,
    GammaAssistLutAutoReviewTcubVaultSpec,
    Master46PillarRecoveryReport,
    build_default_safe_file_settings_and_still_folder_vault_spec,
    build_default_safe_gamma_assist_lut_auto_review_tcub_vault_spec,
    compute_expected_auto_review_and_tcub_state_after_reset,
    compute_expected_gamma_assist_and_lut_monitoring_state,
    compute_expected_movie_and_still_file_settings_after_reset,
    compute_expected_movie_clip_stem_and_still_path,
    evaluate_46pillar_recovery_master,
    evaluate_file_settings_and_still_folder_vault,
    evaluate_gamma_assist_lut_auto_review_tcub_vault,
    evaluate_realhw_46pillar_recovery_master,
    inspect_phase269_donors_readonly,
    run_pillar46_standalone_suite,
    run_pillar46a_file_settings_and_still_folder_vault_6_scenario_suite,
    run_pillar46b_gamma_assist_lut_auto_review_tcub_vault_6_scenario_suite,
    verify_46pillar_recovery_suite,
    verify_file_settings_gamma_assist_and_tcub_vault,
    verify_file_settings_gamma_assist_tcub_vault,
)


class TestRealHw46PillarFileSettingsGammaAssistTcubVaultVerifier(unittest.TestCase):
    """70 fast dual-mode tests for Phase 269 Pillar 46 & `verify-46pillar-recovery`."""

    master46_default: Master46PillarRecoveryReport
    master46_clean_room: Master46PillarRecoveryReport
    master45_clean_room: Master45PillarRecoveryReport

    @classmethod
    def setUpClass(cls) -> None:
        cls.master46_default = evaluate_realhw_46pillar_recovery_master()
        captured_m45 = []
        orig_m45 = p269.evaluate_realhw_45pillar_recovery_master

        def _spy_m45(**kwargs):
            res = orig_m45(**kwargs)
            captured_m45.append(res)
            return res

        with mock.patch.object(p269, "evaluate_realhw_45pillar_recovery_master", side_effect=_spy_m45):
            cls.master46_clean_room = evaluate_realhw_46pillar_recovery_master(force_clean_room=True)
        cls.master45_clean_room = captured_m45[0]

    # ------------------------------------------------------------------
    # 1. Safety Invariants, Schema, Package Exports & Donor Verification
    # ------------------------------------------------------------------

    def test_01_hard_locked_zero_write_and_wave44_safety_constants(self) -> None:
        self.assertTrue(CNFLASHA_USERSPACE_WRITE_BLOCKED)
        self.assertTrue(READ_ONLY_DONOR_ACCESS)
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
        self.assertFalse(P269_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        self.assertEqual(P269_SLOT1_VAULT_FOLDER_MUTATION_EVENTS, 0)
        self.assertEqual(P269_SLOT1_VAULT_FOLDER_MUTATION_BYTES, 0)
        self.assertEqual(P269_MOVIE_CUSTOM_FOLDER_OR_TITLE_OVERFLOW_EVENTS, 0)
        self.assertEqual(P269_STILL_PREFIX_UNDERSCORE_LEAD_OR_LEN_VIOLATIONS, 0)
        self.assertEqual(P269_GAMMA_ASSIST_LOG_LOCKOUT_BYPASS_EVENTS, 0)
        self.assertEqual(P269_GAMMA_ASSIST_EXTERNAL_HDMI_LEAK_EVENTS, 0)
        self.assertEqual(P269_TCUB_CAMERA_RESET_WIPE_OR_FORMAT_VIOLATIONS, 0)
        self.assertEqual(OTP_FUSE_TOUCHES, 0)
        self.assertEqual(OTP_FUSE_WRITES, 0)
        self.assertEqual(RPMB_COUNTER_INCREMENTS, 0)
        self.assertEqual(PASSIVE_TX_BYTES_EMITTED, 0)
        self.assertEqual(PHYSICAL_USB_PACKETS_EMITTED, 0)
        self.assertEqual(PHYSICAL_DEVICE_WRITES, 0)
        self.assertEqual(RAW_FIRMWARE_BYTES_LEAKED, 0)

    def test_02_schema_version_phase_269_and_master_46_pillar_specs(self) -> None:
        self.assertEqual(
            PHASE269_SCHEMA,
            "realhw_46pillar_file_settings_gamma_assist_tcub_vault_verifier_v1",
        )
        self.assertEqual(PHASE269_VERSION, "1.0.0")
        self.assertEqual(PHASE269_PHASE_NUMBER, 269)
        self.assertEqual(MASTER_46_PILLAR_COUNT, 46)
        self.assertEqual(len(MASTER_46_PILLAR_SPECS), 46)
        self.assertEqual(len(MASTER_46_PILLAR_IDS), 46)
        self.assertEqual(MASTER_46_PILLAR_SPECS[:45], MASTER_45_PILLAR_SPECS)
        self.assertEqual([s[0] for s in MASTER_46_PILLAR_SPECS], list(range(1, 47)))
        self.assertEqual(
            MASTER_46_PILLAR_IDS[-1],
            "pillar_46_file_settings_gamma_assist_tcub_vault",
        )
        self.assertIn("46/46", MASTER_46_PILLAR_SPECS[-1][2])

    def test_03_package_top_level_exports_non_shadowing_and_pillars_22_to_45_intact(self) -> None:
        for sym in (
            "PHASE269_SCHEMA",
            "PHASE269_VERSION",
            "PHASE269_PHASE_NUMBER",
            "MASTER_46_PILLAR_COUNT",
            "MASTER_46_PILLAR_SPECS",
            "MASTER_46_PILLAR_IDS",
            "P269_MOVIE_FILE_SETTINGS_MENU_PATH",
            "P269_STILL_FILE_FOLDER_MENU_PATH",
            "P269_GAMMA_DISPLAY_ASSIST_MENU_PATH",
            "P269_SELECT_LUT_MODES",
            "P269_AUTO_REVIEW_DEFAULT",
            "P269_TCUB_EXACT_6_ITEMS",
            "evaluate_file_settings_and_still_folder_vault",
            "evaluate_gamma_assist_lut_auto_review_tcub_vault",
            "evaluate_realhw_46pillar_recovery_master",
            "evaluate_46pillar_recovery_master",
            "verify_46pillar_recovery_suite",
            "verify_file_settings_gamma_assist_and_tcub_vault",
            "verify_file_settings_gamma_assist_tcub_vault",
            # Backward-compatibility across Pillars 22..45
            "evaluate_realhw_45pillar_recovery_master",
            "evaluate_45pillar_recovery_master",
            "verify_45pillar_recovery_suite",
            "evaluate_realhw_44pillar_recovery_master",
            "evaluate_realhw_35pillar_recovery_master",
            "evaluate_22pillar_recovery_master",
            "verify_22pillar_recovery_suite",
        ):
            self.assertTrue(hasattr(fx3_recovery, sym), f"Missing package export: {sym}")
            self.assertIn(sym, fx3_recovery.__all__)
            self.assertEqual(fx3_recovery.__all__.count(sym), 1)

    def test_04_pinned_wave44_fx3_702_and_fx6_601_donor_constants(self) -> None:
        self.assertEqual(P269_FX3_MODEL_NAME, "ILME-FX3")
        self.assertEqual(P269_FX3_MODEL_ID, 0x91030080)
        self.assertEqual(P269_FX3_HELPGUIDE_ID, "ilc/2210")
        self.assertEqual(P269_FX3_FW_VERSION, "7.02")
        self.assertEqual(P269_FX6_DONOR_MODEL_NAME, "ILME-FX6")
        self.assertEqual(P269_FX6_DONOR_FW_VERSION, "6.01")
        self.assertEqual(P269_PINNED_FX3_BODYDATA_BYTES, 811876768)
        self.assertEqual(len(P269_PINNED_FX3_BODYDATA_HDR4K_SHA256), 64)
        self.assertEqual(P269_PINNED_FX3_APPFW_702_BYTES, 79015712)
        self.assertEqual(len(P269_PINNED_FX3_APPFW_702_HDR4K_SHA256), 64)
        self.assertEqual(P269_PINNED_FX6_APPFW_601_BYTES, 50520424)
        self.assertEqual(len(P269_PINNED_FX6_APPFW_601_HDR4K_SHA256), 64)
        self.assertEqual(P269_PINNED_FX3_BACKUP_BIN_BYTES, 2229740)
        self.assertEqual(
            P269_PINNED_FX3_BACKUP_BIN_SHA256,
            "bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2",
        )
        self.assertEqual(P269_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_BYTES, 52312)
        self.assertEqual(len(P269_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_SHA256), 64)
        self.assertEqual(P269_PINNED_FX3_LIBINFRAMEDIADETECT_SO_BYTES, 98224)
        self.assertEqual(len(P269_PINNED_FX3_LIBINFRAMEDIADETECT_SO_SHA256), 64)
        self.assertEqual(P269_PINNED_FX3_LIBINFRAMEDIACOMMON_SO_BYTES, 402624)
        self.assertEqual(len(P269_PINNED_FX3_LIBINFRAMEDIACOMMON_SO_SHA256), 64)
        self.assertEqual(P269_PINNED_FX3_LIBINFRAMEDIAMOUNT_SO_BYTES, 65392)
        self.assertEqual(len(P269_PINNED_FX3_LIBINFRAMEDIAMOUNT_SO_SHA256), 64)
        self.assertEqual(P269_PINNED_FX3_LIBINFRAFSYS_SO_BYTES, 683632)
        self.assertEqual(len(P269_PINNED_FX3_LIBINFRAFSYS_SO_SHA256), 64)
        self.assertEqual(P269_PINNED_FX3_LIBINFRAMETASUPPLIER_SO_BYTES, 23048)
        self.assertEqual(len(P269_PINNED_FX3_LIBINFRAMETASUPPLIER_SO_SHA256), 64)
        self.assertEqual(P269_PINNED_FX6_LIBINFRASETUPFILE_SO_BYTES, 202664)
        self.assertEqual(len(P269_PINNED_FX6_LIBINFRASETUPFILE_SO_SHA256), 64)

    def test_05_donor_snapshot_default_mode_16_artifacts_under_0_15s_zero_raw_leak(self) -> None:
        snap = inspect_phase269_donors_readonly()
        self.assertIn(snap.verification_mode, ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"))
        self.assertTrue(snap.all_donors_present)
        self.assertEqual(snap.donor_files_inspected, 16)
        self.assertTrue(snap.under_0_15s_budget)
        self.assertEqual(snap.raw_firmware_bytes_leaked, 0)
        for art in snap.artifacts:
            self.assertTrue(art.present)
            self.assertTrue(art.matches_pinned)
            self.assertEqual(len(art.digest_sha256), 64)

    def test_06_donor_snapshot_forced_clean_room_and_missing_donor_fallback(self) -> None:
        snap_cr = inspect_phase269_donors_readonly(force_clean_room=True)
        self.assertEqual(snap_cr.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(snap_cr.all_donors_present)
        self.assertEqual(snap_cr.donor_files_inspected, 16)
        self.assertTrue(all(a.read_mode == "CLEAN_ROOM_SYNTHETIC" for a in snap_cr.artifacts))

        with mock.patch.object(p269, "resolve_donor_path", return_value=None):
            snap_fb = inspect_phase269_donors_readonly(force_clean_room=False)
        self.assertEqual(snap_fb.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(snap_fb.all_donors_present)
        self.assertEqual(snap_fb.donor_files_inspected, 16)

    def test_07_clean_room_env_honors_both_fx3_clean_room_test_and_fx3_fx6_force_clean_room(self) -> None:
        self.assertEqual(P269_ENV_CLEAN_ROOM_TEST, "FX3_CLEAN_ROOM_TEST")
        with mock.patch.dict(os.environ, {"FX3_CLEAN_ROOM_TEST": "1", "FX3_FX6_FORCE_CLEAN_ROOM": ""}, clear=False):
            self.assertTrue(p269._is_clean_room_forced(None))
            snap1 = inspect_phase269_donors_readonly()
            self.assertEqual(snap1.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        with mock.patch.dict(os.environ, {"FX3_CLEAN_ROOM_TEST": "", "FX3_FX6_FORCE_CLEAN_ROOM": "1"}, clear=False):
            self.assertTrue(p269._is_clean_room_forced(None))
            snap2 = inspect_phase269_donors_readonly()
            self.assertEqual(snap2.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_08_elf64_aarch64_token_checker_valid_and_negative_branches(self) -> None:
        hdr = bytearray(64)
        hdr[0:4] = b"\x7fELF"
        hdr[4] = 2
        hdr[5] = 1
        struct.pack_into("<H", hdr, 18, 183)
        valid_blob = bytes(hdr) + b"\x00InfraFsys\x00_ZTV9InfraFsys\x00"
        ok, summary = p269._check_elf64_aarch64_tokens(valid_blob, (b"InfraFsys", b"_ZTV9InfraFsys"))
        self.assertTrue(ok)
        self.assertIn("ELF64_AARCH64:InfraFsys+_ZTV9InfraFsys", summary)

        ok_not_elf, msg_not_elf = p269._check_elf64_aarch64_tokens(b"NOT_AN_ELF", ())
        self.assertFalse(ok_not_elf)
        self.assertEqual(msg_not_elf, "NOT_ELF")

        bad_mach = bytearray(hdr)
        struct.pack_into("<H", bad_mach, 18, 62)
        ok_mach, msg_mach = p269._check_elf64_aarch64_tokens(bytes(bad_mach), ())
        self.assertFalse(ok_mach)
        self.assertIn("BAD_ELF64_AARCH64", msg_mach)

        ok_miss, msg_miss = p269._check_elf64_aarch64_tokens(valid_blob, (b"MissingSym",))
        self.assertFalse(ok_miss)
        self.assertIn("MISSING_TOKENS:MissingSym", msg_miss)

    def test_09_bounded_donor_reader_full_vs_header4k_and_error_branches(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            f_small = Path(td) / "small.bin"
            f_small.write_bytes(b"ABCD" * 256)
            with mock.patch.object(p269, "resolve_donor_path", return_value=f_small):
                ok1, tot1, rd1, kind1, sha1, _ = p269._read_donor_readonly_bounded("small.bin", max_full_bytes=2048)
                self.assertTrue(ok1)
                self.assertEqual(tot1, 1024)
                self.assertEqual(rd1, 1024)
                self.assertEqual(kind1, "FULL_SHA256")
                self.assertEqual(len(sha1), 64)

                ok2, tot2, rd2, kind2, _, _ = p269._read_donor_readonly_bounded("small.bin", max_full_bytes=512)
                self.assertTrue(ok2)
                self.assertEqual(tot2, 1024)
                self.assertEqual(rd2, 1024)
                self.assertEqual(kind2, "HEADER4K_SHA256")

            d_dir = Path(td) / "a_dir"
            d_dir.mkdir()
            with mock.patch.object(p269, "resolve_donor_path", return_value=d_dir):
                ok_dir, _, _, kind_dir, _, _ = p269._read_donor_readonly_bounded("a_dir")
                self.assertFalse(ok_dir)
                self.assertEqual(kind_dir, "NOT_REGULAR")

            with (
                mock.patch.object(p269, "resolve_donor_path", return_value=f_small),
                mock.patch.object(os, "open", side_effect=OSError("perm denied")),
            ):
                ok_err, _, _, kind_err, _, _ = p269._read_donor_readonly_bounded("small.bin")
                self.assertFalse(ok_err)
                self.assertEqual(kind_err, "OPEN_ERROR")

    def test_10_donor_corrupt_digest_marks_all_donors_present_false_when_not_missing(self) -> None:
        fake_calls = []

        def _fake_read(relpath, max_full_bytes=p269.P269_MAX_FULL_DONOR_BYTES):
            fake_calls.append(relpath)
            return True, 123, 123, "FULL_SHA256", "0" * 64, b"\x00" * 123

        with mock.patch.object(p269, "_read_donor_readonly_bounded", side_effect=_fake_read):
            snap = inspect_phase269_donors_readonly(force_clean_room=False)
        self.assertEqual(snap.verification_mode, "LOCAL_DONOR_O_RDONLY")
        self.assertFalse(snap.all_donors_present)
        self.assertEqual(len(fake_calls), 16)
        self.assertTrue(all(not a.matches_pinned for a in snap.artifacts))

    def test_11_safety_invariant_helper_catches_mutated_policy_flag(self) -> None:
        self.assertEqual(p269._safety_invariant_errors(), [])
        with mock.patch.object(p269, "PERSISTENT_EMMC_WRITES_AUTHORIZED", True):
            errs = p269._safety_invariant_errors()
            self.assertEqual(len(errs), 1)
            self.assertIn("PERSISTENT_EMMC_WRITES_AUTHORIZED", errs[0])

    def test_12_default_safe_spec_builders_pass_cleanly(self) -> None:
        spec_a = build_default_safe_file_settings_and_still_folder_vault_spec()
        spec_b = build_default_safe_gamma_assist_lut_auto_review_tcub_vault_spec()
        rep_a = evaluate_file_settings_and_still_folder_vault(spec_a)
        rep_b = evaluate_gamma_assist_lut_auto_review_tcub_vault(spec_b)
        self.assertTrue(rep_a.passed)
        self.assertEqual(rep_a.status, P269_STATUS_VERIFIED_PILLAR_46A)
        self.assertIsNone(rep_a.block_code)
        self.assertTrue(rep_b.passed)
        self.assertEqual(rep_b.status, P269_STATUS_VERIFIED_PILLAR_46B)
        self.assertIsNone(rep_b.block_code)

    # ------------------------------------------------------------------
    # 2. Pillar 46A — Movie [File Settings] vs Still [File/Folder Settings] & Slot-1 Firewall
    # ------------------------------------------------------------------

    def test_13_movie_file_settings_constants_camid_reel_37char_and_fixed_clip_folder(self) -> None:
        self.assertEqual(
            P269_MOVIE_FILE_SETTINGS_MENU_PATH,
            ("MENU", "Shooting", "File", "File Settings"),
        )
        self.assertEqual(
            P269_MOVIE_FILE_SETTINGS_ITEMS,
            ("File Number", "Series Counter Reset", "File Name Format", "Title Name Settings"),
        )
        self.assertEqual(P269_MOVIE_FILE_NUMBER_MODES, ("Series", "Reset"))
        self.assertEqual(P269_MOVIE_FILE_NUMBER_DEFAULT, "Series")
        self.assertEqual(
            P269_MOVIE_FILE_NAME_FORMATS,
            ("Standard", "Cam ID + Reel#", "Title", "Date + Title", "Title + Date"),
        )
        self.assertEqual(P269_MOVIE_FILE_NAME_FORMAT_DEFAULT, "Standard")
        self.assertEqual(len(P269_CAM_ID_LETTERS), 26)
        self.assertEqual(P269_CAM_ID_DEFAULT, "A")
        self.assertEqual((P269_REEL_NUMBER_MIN, P269_REEL_NUMBER_MAX, P269_REEL_NUMBER_DEFAULT), (1, 999, "001"))
        self.assertEqual(P269_CAMERA_POSITIONS, ("C", "L", "R"))
        self.assertEqual(P269_CAMERA_POSITION_DEFAULT, "C")
        self.assertEqual(P269_TITLE_NAME_MAX_CHARS, 37)
        self.assertEqual(P269_TITLE_NAME_DEFAULT, "C")
        self.assertEqual(P269_FIXED_MOVIE_CLIP_FOLDER, "PRIVATE/M4ROOT/CLIP")

    def test_14_still_file_folder_settings_constants_3char_dsc_and_standard_vs_date_form(self) -> None:
        self.assertEqual(
            P269_STILL_FILE_FOLDER_MENU_PATH,
            ("MENU", "Shooting", "File", "File/Folder Settings"),
        )
        self.assertEqual(
            P269_STILL_FILE_FOLDER_ITEMS,
            ("File Number", "Forced File Number Reset", "Set File Name", "Folder Name"),
        )
        self.assertEqual(P269_STILL_FILE_NUMBER_MODES, ("Series", "Reset"))
        self.assertEqual(P269_STILL_FILE_NUMBER_DEFAULT, "Series")
        self.assertEqual(P269_STILL_SET_FILE_NAME_LEN, 3)
        self.assertEqual(P269_STILL_SET_FILE_NAME_DEFAULT, "DSC")
        self.assertEqual(P269_STILL_FOLDER_NAME_MODES, ("Standard Form", "Date Form"))
        self.assertEqual(P269_STILL_FOLDER_NAME_DEFAULT, "Standard Form")

    def test_15_movie_clip_stem_and_still_dcim_path_all_5_formats_and_2_folder_forms(self) -> None:
        cases = (
            ("Standard", "PRIVATE/M4ROOT/CLIP/C0007.MP4", "Standard Form", "100MSDCF", "DCIM/100MSDCF/DSC00009.JPG"),
            ("Cam ID + Reel#", "PRIVATE/M4ROOT/CLIP/C999R0007.MP4", "Date Form", "10561115", "DCIM/10561115/A_100009.JPG"),
            ("Title", "PRIVATE/M4ROOT/CLIP/REEL_ALPHA0007.MP4", "Standard Form", "100MSDCF", "DCIM/100MSDCF/DSC00009.JPG"),
            ("Date + Title", "PRIVATE/M4ROOT/CLIP/20261115_REEL_ALPHA0007.MP4", "Standard Form", "100MSDCF", "DCIM/100MSDCF/DSC00009.JPG"),
            ("Title + Date", "PRIVATE/M4ROOT/CLIP/REEL_ALPHA_20261115_0007.MP4", "Date Form", "10561115", "DCIM/10561115/A_100009.JPG"),
        )
        for fmt, exp_mov, sform, exp_dir, exp_still in cases:
            with self.subTest(fmt=fmt, sform=sform):
                mov, dcim_d, still = compute_expected_movie_clip_stem_and_still_path(
                    movie_file_name_format=fmt,
                    camera_id="C",
                    reel_number="999",
                    camera_position="R",
                    title_name="REEL_ALPHA",
                    movie_seq_number=7,
                    date_yyyymmdd="20261115",
                    still_set_file_name="DSC" if sform == "Standard Form" else "A_1",
                    still_folder_name_form=sform,
                    still_folder_number=100 if sform == "Standard Form" else 105,
                    date_ymmdd="61115",
                    still_seq_number=9,
                )
                self.assertEqual(mov, exp_mov)
                self.assertEqual(dcim_d, exp_dir)
                self.assertEqual(still, exp_still)

    def test_16_movie_and_still_file_settings_survive_camera_and_network_reset_reset_only_on_initialize(self) -> None:
        for r_act in P269_RESET_ACTIONS:
            tup = compute_expected_movie_and_still_file_settings_after_reset(
                pre_movie_file_number="Reset",
                pre_movie_file_name_format="Cam ID + Reel#",
                pre_camera_id="Z",
                pre_reel_number="999",
                pre_camera_position="R",
                pre_title_name="SLATE_37CHAR_TEST",
                pre_still_file_number="Reset",
                pre_still_set_file_name="F_3",
                pre_still_folder_name_form="Date Form",
                reset_action=r_act,
            )
            if r_act == "Initialize":
                self.assertEqual(
                    tup,
                    ("Series", "Standard", "A", "001", "C", "C", "Series", "DSC", "Standard Form"),
                )
            else:
                self.assertEqual(
                    tup,
                    ("Reset", "Cam ID + Reel#", "Z", "999", "R", "SLATE_37CHAR_TEST", "Reset", "F_3", "Date Form"),
                )

    def test_17_exact_37char_title_passes_and_38char_or_empty_or_bad_symbol_rejected(self) -> None:
        t37 = "A123456789012345678901234567890123456"
        self.assertEqual(len(t37), 37)
        r_ok = evaluate_file_settings_and_still_folder_vault(
            FileSettingsAndStillFolderVaultSpec(
                pre_title_name=t37,
                saved_title_name=t37,
                post_title_name=t37,
            )
        )
        self.assertTrue(r_ok.passed)
        self.assertEqual(r_ok.title_name_char_length, 37)

        for bad_title in ("X" * 38, "", "BAD SPACE", "BAD/SLASH"):
            with self.subTest(bad_title=bad_title):
                r_bad = evaluate_file_settings_and_still_folder_vault(
                    FileSettingsAndStillFolderVaultSpec(
                        pre_title_name=bad_title,
                        post_title_name=bad_title,
                    )
                )
                self.assertFalse(r_bad.passed)
                self.assertEqual(r_bad.block_code, P269_BLOCKED_MOVIE_FILE_SETTINGS_OR_37CHAR_TITLE_VIOLATION)
                self.assertGreaterEqual(r_bad.movie_custom_folder_or_title_overflow_events, 1)

    def test_18_camid_a_to_z_reel_001_to_999_position_clr_and_fixed_m4root_clip_enforced(self) -> None:
        for kw in (
            {"pre_camera_id": "a", "post_camera_id": "a"},
            {"pre_reel_number": "000", "post_reel_number": "000"},
            {"pre_reel_number": "1000", "post_reel_number": "1000"},
            {"pre_camera_position": "M", "post_camera_position": "M"},
            {"movie_clip_folder_path": "PRIVATE/CUSTOM/CLIP"},
            {"movie_custom_folder_attempted": True},
        ):
            with self.subTest(kw=kw):
                rep = evaluate_file_settings_and_still_folder_vault(FileSettingsAndStillFolderVaultSpec(**kw))
                self.assertFalse(rep.passed)
                self.assertEqual(rep.block_code, P269_BLOCKED_MOVIE_FILE_SETTINGS_OR_37CHAR_TITLE_VIOLATION)

    def test_19_still_set_file_name_allows_underscore_at_index_1_2_but_rejects_leading_underscore_at_index_0(self) -> None:
        for ok_prefix in ("DSC", "A_B", "9__", "Z0_"):
            with self.subTest(ok_prefix=ok_prefix):
                rep = evaluate_file_settings_and_still_folder_vault(
                    FileSettingsAndStillFolderVaultSpec(
                        pre_still_set_file_name=ok_prefix,
                        saved_still_set_file_name=ok_prefix,
                        post_still_set_file_name=ok_prefix,
                        expected_still_file_relpath=f"DCIM/100MSDCF/{ok_prefix}00001.JPG",
                    )
                )
                self.assertTrue(rep.passed)
                self.assertEqual(rep.still_prefix_underscore_lead_or_len_violations, 0)

        for bad_prefix in ("_SC", "___", "DS", "DSCA", "dsc", "D-C"):
            with self.subTest(bad_prefix=bad_prefix):
                rep_bad = evaluate_file_settings_and_still_folder_vault(
                    FileSettingsAndStillFolderVaultSpec(
                        pre_still_set_file_name=bad_prefix,
                        post_still_set_file_name=bad_prefix,
                    )
                )
                self.assertFalse(rep_bad.passed)
                self.assertEqual(rep_bad.block_code, P269_BLOCKED_STILL_PREFIX_UNDERSCORE_OR_FOLDER_FORM_VIOLATION)
                self.assertGreaterEqual(rep_bad.still_prefix_underscore_lead_or_len_violations, 1)

    def test_20_initialize_resets_file_and_folder_settings_and_camset01_ordonly_restores(self) -> None:
        rep_init = evaluate_file_settings_and_still_folder_vault(
            FileSettingsAndStillFolderVaultSpec(
                reset_action="Initialize",
                post_movie_file_number="Series",
                post_movie_file_name_format="Standard",
                post_camera_id="A",
                post_reel_number="001",
                post_camera_position="C",
                post_title_name="C",
                post_still_file_number="Series",
                post_still_set_file_name="DSC",
                post_still_folder_name_form="Standard Form",
                expected_movie_clip_relpath="PRIVATE/M4ROOT/CLIP/C0001.MP4",
                expected_still_dcim_folder="100MSDCF",
                expected_still_file_relpath="DCIM/100MSDCF/DSC00001.JPG",
            )
        )
        self.assertTrue(rep_init.passed)

        rep_drift = evaluate_file_settings_and_still_folder_vault(
            FileSettingsAndStillFolderVaultSpec(
                reset_action="Initialize",
                # post_* stayed non-default without CAMSET load -> must fail!
            )
        )
        self.assertFalse(rep_drift.passed)
        self.assertEqual(rep_drift.block_code, P269_BLOCKED_FILE_FOLDER_RESET_VS_INITIALIZE_SCOPE_DRIFT)

    def test_21_camset_slot1_ordonly_envelope_rejects_wrong_slot_wrong_model_or_rw_load(self) -> None:
        for kw in (
            {"camset_load_after_reset": True, "camset_slot": 2},
            {"camset_load_after_reset": True, "camset_filename": "CAMSET11.DAT"},
            {"camset_load_after_reset": True, "camset_source_model": "ILME-FX6"},
            {"camset_load_after_reset": True, "camset_read_only_load": False},
        ):
            with self.subTest(kw=kw):
                rep = evaluate_file_settings_and_still_folder_vault(FileSettingsAndStillFolderVaultSpec(**kw))
                self.assertFalse(rep.passed)
                self.assertEqual(rep.block_code, P269_BLOCKED_FILE_FOLDER_RESET_VS_INITIALIZE_SCOPE_DRIFT)

    def test_22_slot1_recovery_vault_firewall_blocks_forced_reset_and_create_new_folder_on_slot1(self) -> None:
        # Allowed on Slot 2 while Slot 1 holds read-only vault
        r_slot2_ok = evaluate_file_settings_and_still_folder_vault(
            FileSettingsAndStillFolderVaultSpec(
                slot1_holds_recovery_vault=True,
                slot1_sdxc_wp_locked=True,
                active_still_media_slot=2,
                forced_file_number_reset_requested=True,
                create_new_folder_requested=True,
            )
        )
        self.assertTrue(r_slot2_ok.passed)
        self.assertEqual(r_slot2_ok.slot1_vault_folder_mutation_events, 0)

        # Blocked on Slot 1 whenever Slot 1 holds CAMSET/BODYDATA.DAT vault
        for kw in (
            {"active_still_media_slot": 1, "forced_file_number_reset_requested": True},
            {"active_still_media_slot": 1, "create_new_folder_requested": True},
            {"slot1_sdxc_wp_locked": False},
            {"slot1_vault_folder_mutation_events": 1},
            {"slot1_vault_folder_mutation_bytes": 512},
        ):
            with self.subTest(kw=kw):
                r_bad = evaluate_file_settings_and_still_folder_vault(FileSettingsAndStillFolderVaultSpec(**kw))
                self.assertFalse(r_bad.passed)
                self.assertEqual(r_bad.block_code, P269_BLOCKED_SLOT1_VAULT_DCIM_FOLDER_MUTATION)
                self.assertGreaterEqual(r_bad.slot1_vault_folder_mutation_events, 1)

    def test_23_pillar46a_rejects_persistent_unlock_overlay_escape_tier0_drift_and_bad_spec(self) -> None:
        r_unlock = evaluate_file_settings_and_still_folder_vault(
            FileSettingsAndStillFolderVaultSpec(persistent_write_unlock_requested=True)
        )
        self.assertFalse(r_unlock.passed)
        self.assertEqual(r_unlock.block_code, P269_BLOCKED_SAFETY_POLICY_VIOLATION)

        r_ov = evaluate_file_settings_and_still_folder_vault(
            FileSettingsAndStillFolderVaultSpec(overlay_dir="/dev/cnflasha")
        )
        self.assertFalse(r_ov.passed)
        self.assertEqual(r_ov.block_code, P269_BLOCKED_PERSISTENT_OVERLAY_ESCAPE)

        r_h3 = evaluate_file_settings_and_still_folder_vault(
            FileSettingsAndStillFolderVaultSpec(tier0_surfaces_h0_h3_matched=15)
        )
        self.assertFalse(r_h3.passed)
        self.assertEqual(r_h3.block_code, P269_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT)

        r_inv = evaluate_file_settings_and_still_folder_vault(
            FileSettingsAndStillFolderVaultSpec(camera_model="ILCE-7SM3")
        )
        self.assertFalse(r_inv.passed)
        self.assertEqual(r_inv.block_code, P269_BLOCKED_INVALID_FILE_OR_FOLDER_SETTINGS_SPEC)

    def test_24_pillar46a_rejects_mismatched_expected_clip_or_dcim_relpath(self) -> None:
        r_bad_path = evaluate_file_settings_and_still_folder_vault(
            FileSettingsAndStillFolderVaultSpec(
                expected_movie_clip_relpath="PRIVATE/M4ROOT/CLIP/WRONG0001.MP4"
            )
        )
        self.assertFalse(r_bad_path.passed)
        self.assertEqual(r_bad_path.block_code, P269_BLOCKED_MOVIE_FILE_SETTINGS_OR_37CHAR_TITLE_VIOLATION)

    def test_25_pillar46a_report_to_dict_serializes_clean_json(self) -> None:
        rep = evaluate_file_settings_and_still_folder_vault(FileSettingsAndStillFolderVaultSpec())
        d = rep.to_dict()
        self.assertTrue(d["passed"])
        self.assertEqual(d["slot1_vault_folder_mutation_events"], 0)
        self.assertEqual(len(json.dumps(d)), len(json.dumps(d)))

    def test_26_pillar46a_6_scenario_suite_passes_all_6_scenarios(self) -> None:
        res = run_pillar46a_file_settings_and_still_folder_vault_6_scenario_suite()
        self.assertTrue(res.passed)
        self.assertEqual(res.status, P269_STATUS_VERIFIED_PILLAR_46A)
        self.assertEqual(res.scenarios_passed, 6)
        self.assertEqual(res.scenarios_total, 6)
        self.assertEqual(tuple(s.scenario_id for s in res.scenarios), P269_PILLAR_46A_SCENARIO_IDS)
        self.assertEqual([s.expected_allowed for s in res.scenarios], [True, True, False, False, False, False])

    # ------------------------------------------------------------------
    # 3. Pillar 46B — [Gamma Display Assist] vs [Display LUT]/[Select LUT], [Auto Review] & [TC/UB]
    # ------------------------------------------------------------------

    def test_27_gamma_assist_display_lut_select_lut_auto_review_and_tcub_constants(self) -> None:
        self.assertEqual(
            P269_GAMMA_DISPLAY_ASSIST_MENU_PATH,
            ("MENU", "Setup", "Display Option", "Gamma Display Assist"),
        )
        self.assertEqual(
            P269_GAMMA_DISP_ASSIST_TYP_MENU_PATH,
            ("MENU", "Setup", "Display Option", "Gamma Disp. Assist Typ."),
        )
        self.assertEqual(P269_GAMMA_DISPLAY_ASSIST_MODES, ("Off", "On"))
        self.assertEqual(P269_GAMMA_DISPLAY_ASSIST_DEFAULT, "Off")
        self.assertEqual(
            P269_GAMMA_DISP_ASSIST_TYPES,
            ("Auto", "S-Log3->709(800%)", "HLG(BT.2020)", "HLG(709)"),
        )
        self.assertEqual(P269_GAMMA_DISP_ASSIST_TYPE_DEFAULT, "Auto")
        self.assertEqual(P269_LOG_SHOOTING_MODES, ("Off", "Cine EI", "Cine EI Quick", "Flexible ISO"))
        self.assertEqual(P269_DISPLAY_LUT_MENU_PATH, ("MENU", "Setup", "Display Option", "Display LUT"))
        self.assertEqual(P269_DISPLAY_LUT_MODES, ("On", "Off"))
        self.assertEqual(P269_DISPLAY_LUT_DEFAULT, "On")
        self.assertEqual(P269_SELECT_LUT_MENU_PATH, ("MENU", "Exposure/Color", "Color/Tone", "Select LUT"))
        self.assertEqual(P269_SELECT_LUT_PRESETS, ("S-Log3", "s709", "709(800%)"))
        self.assertEqual(len(P269_SELECT_LUT_USER_SLOTS), 16)
        self.assertEqual(P269_SELECT_LUT_USER_SLOTS[0], "User1")
        self.assertEqual(P269_SELECT_LUT_USER_SLOTS[-1], "User16")
        self.assertEqual(len(P269_SELECT_LUT_MODES), 19)
        self.assertEqual(P269_SELECT_LUT_DEFAULT, "s709")
        self.assertEqual(P269_AUTO_REVIEW_MENU_PATH, ("MENU", "Setup", "Display Option", "Auto Review"))
        self.assertEqual(P269_AUTO_REVIEW_MODES, ("Off", "2 Sec", "5 Sec", "10 Sec"))
        self.assertEqual(P269_AUTO_REVIEW_DEFAULT, "Off")
        self.assertEqual(P269_TCUB_MENU_PATH, ("MENU", "Shooting", "TC/UB"))
        self.assertEqual(
            P269_TCUB_EXACT_6_ITEMS,
            (
                "Time Code Preset",
                "User Bit Preset",
                "Time Code Format",
                "Time Code Run",
                "Time Code Make",
                "User Bit Time Rec",
            ),
        )
        self.assertEqual(P269_TCUB_DISP_SETTING_MENU_PATH, ("MENU", "Setup", "Display Option", "TC/UB Disp. Setting"))
        self.assertEqual(P269_TC_PRESET_DEFAULT, "00:00:00.00")
        self.assertEqual(P269_UB_PRESET_DEFAULT, "00 00 00 00")
        self.assertEqual((P269_TC_FORMAT_MODES, P269_TC_FORMAT_DEFAULT), (("DF", "NDF"), "DF"))
        self.assertEqual((P269_TC_RUN_MODES, P269_TC_RUN_DEFAULT), (("Rec Run", "Free Run"), "Rec Run"))
        self.assertEqual((P269_TC_MAKE_MODES, P269_TC_MAKE_DEFAULT), (("Preset", "Regenerate"), "Preset"))
        self.assertEqual((P269_UB_TIME_REC_MODES, P269_UB_TIME_REC_DEFAULT), (("Off", "On"), "Off"))
        self.assertEqual((P269_TCUB_DISP_SETTING_MODES, P269_TCUB_DISP_SETTING_DEFAULT), (("TC", "U-Bit"), "TC"))

    def test_28_log_shooting_locks_gamma_display_assist_off_across_cine_ei_quick_and_flexible_iso(self) -> None:
        for log_mode in ("Cine EI", "Cine EI Quick", "Flexible ISO"):
            with self.subTest(log_mode=log_mode):
                eff_g, locked, lcd_g, hdmi_g, mon_lut = compute_expected_gamma_assist_and_lut_monitoring_state(
                    log_shooting_mode=log_mode,
                    configured_gamma_display_assist="On",
                    configured_gamma_disp_assist_type="S-Log3->709(800%)",
                    configured_display_lut="On",
                    configured_select_lut="User16",
                )
                self.assertEqual(eff_g, "Off")
                self.assertTrue(locked)
                self.assertFalse(lcd_g)
                self.assertFalse(hdmi_g)
                self.assertEqual(mon_lut, "User16")

                rep_ok = evaluate_gamma_assist_lut_auto_review_tcub_vault(
                    GammaAssistLutAutoReviewTcubVaultSpec(
                        log_shooting_mode=log_mode,
                        pre_select_lut="User16",
                        post_select_lut="User16",
                        active_monitoring_lut="User16",
                    )
                )
                self.assertTrue(rep_ok.passed)

                rep_bypass = evaluate_gamma_assist_lut_auto_review_tcub_vault(
                    GammaAssistLutAutoReviewTcubVaultSpec(
                        log_shooting_mode=log_mode,
                        effective_gamma_display_assist="On",
                        lcd_gamma_assist_applied=True,
                    )
                )
                self.assertFalse(rep_bypass.passed)
                self.assertEqual(rep_bypass.block_code, P269_BLOCKED_GAMMA_ASSIST_LOG_SHOOTING_LOCKOUT_BYPASS)

    def test_29_all_19_select_lut_options_pass_and_user0_or_user17_rejected(self) -> None:
        for lut in P269_SELECT_LUT_MODES:
            with self.subTest(lut=lut):
                rep = evaluate_gamma_assist_lut_auto_review_tcub_vault(
                    GammaAssistLutAutoReviewTcubVaultSpec(
                        pre_select_lut=lut,
                        saved_select_lut=lut,
                        post_select_lut=lut,
                        active_monitoring_lut=lut,
                    )
                )
                self.assertTrue(rep.passed)
                self.assertEqual(rep.active_monitoring_lut, lut)

        for bad_lut in ("User0", "User17", "Custom99"):
            with self.subTest(bad_lut=bad_lut):
                rep_bad = evaluate_gamma_assist_lut_auto_review_tcub_vault(
                    GammaAssistLutAutoReviewTcubVaultSpec(
                        pre_select_lut=bad_lut,
                        post_select_lut=bad_lut,
                        active_monitoring_lut=bad_lut,
                    )
                )
                self.assertFalse(rep_bad.passed)
                self.assertEqual(rep_bad.block_code, P269_BLOCKED_GAMMA_ASSIST_LOG_SHOOTING_LOCKOUT_BYPASS)

    def test_30_display_lut_off_during_log_shooting_sets_none_lut_bypassed(self) -> None:
        eff_g, locked, lcd_g, hdmi_g, mon_lut = compute_expected_gamma_assist_and_lut_monitoring_state(
            log_shooting_mode="Cine EI",
            configured_gamma_display_assist="Off",
            configured_gamma_disp_assist_type="Auto",
            configured_display_lut="Off",
            configured_select_lut="s709",
        )
        self.assertEqual((eff_g, locked, lcd_g, hdmi_g, mon_lut), ("Off", True, False, False, "NONE_LUT_BYPASSED"))

    def test_31_gamma_display_assist_lcd_only_under_log_off_and_external_hdmi_leak_rejected(self) -> None:
        for g_type in P269_GAMMA_DISP_ASSIST_TYPES:
            with self.subTest(g_type=g_type):
                rep = evaluate_gamma_assist_lut_auto_review_tcub_vault(
                    GammaAssistLutAutoReviewTcubVaultSpec(
                        log_shooting_mode="Off",
                        pre_gamma_display_assist="On",
                        pre_gamma_disp_assist_type=g_type,
                        post_gamma_display_assist="On",
                        post_gamma_disp_assist_type=g_type,
                        effective_gamma_display_assist="On",
                        gamma_assist_locked_by_log_shooting=False,
                        lcd_gamma_assist_applied=True,
                        hdmi_external_monitor_connected=True,
                        external_hdmi_gamma_assist_applied=False,
                        active_monitoring_lut=f"GAMMA_ASSIST:{g_type}",
                    )
                )
                self.assertTrue(rep.passed)
                self.assertEqual(rep.gamma_assist_external_hdmi_leak_events, 0)

        rep_leak = evaluate_gamma_assist_lut_auto_review_tcub_vault(
            GammaAssistLutAutoReviewTcubVaultSpec(
                log_shooting_mode="Off",
                effective_gamma_display_assist="On",
                gamma_assist_locked_by_log_shooting=False,
                lcd_gamma_assist_applied=True,
                active_monitoring_lut="GAMMA_ASSIST:S-Log3->709(800%)",
                external_hdmi_gamma_assist_applied=True,
            )
        )
        self.assertFalse(rep_leak.passed)
        self.assertEqual(rep_leak.block_code, P269_BLOCKED_GAMMA_ASSIST_EXTERNAL_HDMI_LEAK_OR_AUTO_REVIEW_VIOLATION)

    def test_32_auto_review_off_cinema_default_and_movie_live_view_non_interruption(self) -> None:
        for ar_val in P269_AUTO_REVIEW_MODES:
            with self.subTest(ar_val=ar_val):
                rep = evaluate_gamma_assist_lut_auto_review_tcub_vault(
                    GammaAssistLutAutoReviewTcubVaultSpec(
                        shooting_domain="Still",
                        pre_auto_review=ar_val,
                        post_auto_review=ar_val,
                    )
                )
                self.assertTrue(rep.passed)

        for bad_kw in (
            {"factory_default_auto_review": "2 Sec"},
            {"pre_auto_review": "30 Sec", "post_auto_review": "30 Sec"},
            {"movie_live_view_interrupted_by_auto_review": True},
        ):
            with self.subTest(bad_kw=bad_kw):
                rep_bad = evaluate_gamma_assist_lut_auto_review_tcub_vault(
                    GammaAssistLutAutoReviewTcubVaultSpec(**bad_kw)
                )
                self.assertFalse(rep_bad.passed)
                self.assertEqual(
                    rep_bad.block_code,
                    P269_BLOCKED_GAMMA_ASSIST_EXTERNAL_HDMI_LEAK_OR_AUTO_REVIEW_VIOLATION,
                )

    def test_33_all_6_tcub_items_and_setup_options_survive_camera_and_network_reset_reset_only_on_initialize(self) -> None:
        for r_act in P269_RESET_ACTIONS:
            tup = compute_expected_auto_review_and_tcub_state_after_reset(
                pre_gamma_display_assist="On",
                pre_gamma_disp_assist_type="HLG(BT.2020)",
                pre_display_lut="Off",
                pre_auto_review="5 Sec",
                pre_tc_preset="12:34:56.18",
                pre_ub_preset="AB CD EF 09",
                pre_tc_format="DF",
                pre_tc_run="Free Run",
                pre_tc_make="Regenerate",
                pre_ub_time_rec="On",
                pre_tcub_disp_setting="U-Bit",
                movie_frame_rate="29.97p",
                reset_action=r_act,
            )
            if r_act == "Initialize":
                self.assertEqual(
                    tup,
                    ("Off", "Auto", "On", "Off", "00:00:00.00", "00 00 00 00", "DF", "Rec Run", "Preset", "Off", "TC"),
                )
            else:
                self.assertEqual(
                    tup,
                    (
                        "On",
                        "HLG(BT.2020)",
                        "Off",
                        "5 Sec",
                        "12:34:56.18",
                        "AB CD EF 09",
                        "DF",
                        "Free Run",
                        "Regenerate",
                        "On",
                        "U-Bit",
                    ),
                )

    def test_34_24p_and_pal_frame_rates_force_ndf_while_ntsc_2997p_5994p_allow_df(self) -> None:
        for fps in P269_FORCED_NDF_FRAME_RATES:
            with self.subTest(fps=fps):
                rep_ok = evaluate_gamma_assist_lut_auto_review_tcub_vault(
                    GammaAssistLutAutoReviewTcubVaultSpec(
                        movie_frame_rate=fps,
                        pre_tc_format="NDF",
                        post_tc_format="NDF",
                    )
                )
                self.assertTrue(rep_ok.passed)

                rep_df_bad = evaluate_gamma_assist_lut_auto_review_tcub_vault(
                    GammaAssistLutAutoReviewTcubVaultSpec(
                        movie_frame_rate=fps,
                        pre_tc_format="DF",
                        post_tc_format="DF",
                    )
                )
                self.assertFalse(rep_df_bad.passed)
                self.assertEqual(rep_df_bad.block_code, P269_BLOCKED_TCUB_OR_SETUP_RESET_PERSISTENCE_OR_NDF_DRIFT)

        for ntsc_fps in ("23.98p", "29.97p", "59.94p", "119.88p"):
            with self.subTest(ntsc_fps=ntsc_fps):
                rep_df_ok = evaluate_gamma_assist_lut_auto_review_tcub_vault(
                    GammaAssistLutAutoReviewTcubVaultSpec(
                        movie_frame_rate=ntsc_fps,
                        pre_tc_format="DF",
                        post_tc_format="DF",
                    )
                )
                self.assertTrue(rep_df_ok.passed)

    def test_35_tc_and_ub_preset_regex_bounds_reject_out_of_range_smpte_or_bad_hex(self) -> None:
        for bad_tc in ("24:00:00.00", "00:60:00.00", "00:00:60.00", "00:00:00.60", "BAD_TC"):
            with self.subTest(bad_tc=bad_tc):
                rep = evaluate_gamma_assist_lut_auto_review_tcub_vault(
                    GammaAssistLutAutoReviewTcubVaultSpec(pre_tc_preset=bad_tc, post_tc_preset=bad_tc)
                )
                self.assertFalse(rep.passed)
                self.assertEqual(rep.block_code, P269_BLOCKED_TCUB_OR_SETUP_RESET_PERSISTENCE_OR_NDF_DRIFT)

        for bad_ub in ("GG 00 00 00", "00:00:00:00", "00 00 00", "aa bb cc dd"):
            with self.subTest(bad_ub=bad_ub):
                rep = evaluate_gamma_assist_lut_auto_review_tcub_vault(
                    GammaAssistLutAutoReviewTcubVaultSpec(pre_ub_preset=bad_ub, post_ub_preset=bad_ub)
                )
                self.assertFalse(rep.passed)
                self.assertEqual(rep.block_code, P269_BLOCKED_TCUB_OR_SETUP_RESET_PERSISTENCE_OR_NDF_DRIFT)

    def test_36_initialize_without_camset_load_resets_gamma_assist_display_lut_auto_review_and_tcub(self) -> None:
        rep = evaluate_gamma_assist_lut_auto_review_tcub_vault(
            GammaAssistLutAutoReviewTcubVaultSpec(
                movie_frame_rate="24.00p",
                reset_action="Initialize",
                post_gamma_display_assist="Off",
                post_gamma_disp_assist_type="Auto",
                post_display_lut="On",
                post_select_lut="s709",
                post_auto_review="Off",
                post_tc_preset="00:00:00.00",
                post_ub_preset="00 00 00 00",
                post_tc_format="NDF",
                post_tc_run="Rec Run",
                post_tc_make="Preset",
                post_ub_time_rec="Off",
                post_tcub_disp_setting="TC",
                effective_gamma_display_assist="Off",
                gamma_assist_locked_by_log_shooting=True,
                lcd_gamma_assist_applied=False,
                active_monitoring_lut="s709",
            )
        )
        self.assertTrue(rep.passed)

    def test_37_pillar46b_rejects_bad_camset_envelope_persistent_unlock_tier0_drift_and_bad_6item_tcub(self) -> None:
        r_cam = evaluate_gamma_assist_lut_auto_review_tcub_vault(
            GammaAssistLutAutoReviewTcubVaultSpec(camset_load_after_reset=True, camset_slot=2)
        )
        self.assertFalse(r_cam.passed)
        self.assertEqual(r_cam.block_code, P269_BLOCKED_TCUB_OR_SETUP_RESET_PERSISTENCE_OR_NDF_DRIFT)

        r_unlock = evaluate_gamma_assist_lut_auto_review_tcub_vault(
            GammaAssistLutAutoReviewTcubVaultSpec(persistent_write_unlock_requested=True)
        )
        self.assertFalse(r_unlock.passed)
        self.assertEqual(r_unlock.block_code, P269_BLOCKED_SAFETY_POLICY_VIOLATION)

        r_h3 = evaluate_gamma_assist_lut_auto_review_tcub_vault(
            GammaAssistLutAutoReviewTcubVaultSpec(tier0_surfaces_h0_h3_matched=14)
        )
        self.assertFalse(r_h3.passed)
        self.assertEqual(r_h3.block_code, P269_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT)

        r_inv = evaluate_gamma_assist_lut_auto_review_tcub_vault(
            GammaAssistLutAutoReviewTcubVaultSpec(tcub_menu_items=("Time Code Preset",))
        )
        self.assertFalse(r_inv.passed)
        self.assertEqual(r_inv.block_code, P269_BLOCKED_INVALID_GAMMA_ASSIST_LUT_TCUB_SPEC)

    def test_38_pillar46b_report_to_dict_serializes_clean_json(self) -> None:
        rep = evaluate_gamma_assist_lut_auto_review_tcub_vault(GammaAssistLutAutoReviewTcubVaultSpec())
        d = rep.to_dict()
        self.assertTrue(d["passed"])
        self.assertEqual(d["effective_gamma_display_assist"], "Off")
        self.assertEqual(d["active_monitoring_lut"], "User1")

    def test_39_pillar46b_6_scenario_suite_passes_all_6_scenarios(self) -> None:
        res = run_pillar46b_gamma_assist_lut_auto_review_tcub_vault_6_scenario_suite()
        self.assertTrue(res.passed)
        self.assertEqual(res.status, P269_STATUS_VERIFIED_PILLAR_46B)
        self.assertEqual(res.scenarios_passed, 6)
        self.assertEqual(res.scenarios_total, 6)
        self.assertEqual(tuple(s.scenario_id for s in res.scenarios), P269_PILLAR_46B_SCENARIO_IDS)
        self.assertEqual([s.expected_allowed for s in res.scenarios], [True, True, False, False, False, False])

    # ------------------------------------------------------------------
    # 4. Combined Verifier & Standalone Pillar 46 Suite
    # ------------------------------------------------------------------

    def test_40_combined_verifier_and_symmetry_alias_pass_dual_mode_and_serialize(self) -> None:
        r_ok = verify_file_settings_gamma_assist_and_tcub_vault()
        r_alias = verify_file_settings_gamma_assist_tcub_vault(force_clean_room=True)
        self.assertTrue(r_ok.all_passed)
        self.assertTrue(r_ok.passed)
        self.assertEqual(r_ok.status, P269_STATUS_VERIFIED_PILLAR46_SUITE)
        self.assertEqual(r_ok.slot1_vault_folder_mutation_events, 0)
        self.assertEqual(r_ok.slot1_vault_folder_mutation_bytes, 0)
        self.assertEqual(r_ok.movie_custom_folder_or_title_overflow_events, 0)
        self.assertEqual(r_ok.still_prefix_underscore_lead_or_len_violations, 0)
        self.assertEqual(r_ok.gamma_assist_log_lockout_bypass_events, 0)
        self.assertEqual(r_ok.gamma_assist_external_hdmi_leak_events, 0)
        self.assertEqual(r_ok.tcub_camera_reset_wipe_or_format_violations, 0)
        self.assertTrue(r_alias.all_passed)
        self.assertEqual(r_alias.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        d = r_alias.to_dict()
        self.assertEqual(d["schema"], PHASE269_SCHEMA)
        self.assertTrue(d["cnflasha_userspace_write_blocked"])

    def test_41_combined_verifier_propagates_pillar46a_pillar46b_and_donor_failures(self) -> None:
        r_bad_a = verify_file_settings_gamma_assist_and_tcub_vault(
            file_settings_spec=FileSettingsAndStillFolderVaultSpec(slot1_vault_folder_mutation_events=2),
            force_clean_room=True,
        )
        self.assertFalse(r_bad_a.all_passed)
        self.assertEqual(r_bad_a.status, P269_STATUS_FAIL_PILLAR46_SUITE)
        self.assertEqual(r_bad_a.slot1_vault_folder_mutation_events, 2)

        r_bad_b = verify_file_settings_gamma_assist_and_tcub_vault(
            gamma_tcub_spec=GammaAssistLutAutoReviewTcubVaultSpec(gamma_assist_log_lockout_bypass_events=3),
            force_clean_room=True,
        )
        self.assertFalse(r_bad_b.all_passed)
        self.assertEqual(r_bad_b.status, P269_STATUS_FAIL_PILLAR46_SUITE)
        self.assertEqual(r_bad_b.gamma_assist_log_lockout_bypass_events, 3)

        bad_snap = replace(
            inspect_phase269_donors_readonly(force_clean_room=True),
            all_donors_present=False,
            under_0_15s_budget=False,
        )
        with mock.patch.object(p269, "inspect_phase269_donors_readonly", return_value=bad_snap):
            r_bad_d = verify_file_settings_gamma_assist_and_tcub_vault(force_clean_room=True)
        self.assertFalse(r_bad_d.all_passed)
        self.assertGreaterEqual(len(r_bad_d.errors), 2)

    def test_42_standalone_pillar46_suite_deterministic_sha256_in_default_and_clean_room(self) -> None:
        rep_d1 = run_pillar46_standalone_suite()
        rep_d2 = run_pillar46_standalone_suite()
        self.assertTrue(rep_d1.all_passed)
        self.assertEqual(rep_d1.status, P269_STATUS_VERIFIED_PILLAR46_SUITE)
        self.assertEqual(rep_d1.suite_sha256, rep_d2.suite_sha256)
        self.assertEqual(len(rep_d1.suite_sha256), 64)

        rep_cr1 = run_pillar46_standalone_suite(force_clean_room=True)
        with mock.patch.dict(os.environ, {"FX3_CLEAN_ROOM_TEST": "1"}, clear=False):
            rep_cr2 = run_pillar46_standalone_suite()
        self.assertTrue(rep_cr1.all_passed)
        self.assertEqual(rep_cr1.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(rep_cr2.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(rep_cr1.suite_sha256, rep_cr2.suite_sha256)

    def test_43_standalone_pillar46_suite_fails_closed_on_subsuite_or_donor_failure(self) -> None:
        bad_a = replace(
            run_pillar46a_file_settings_and_still_folder_vault_6_scenario_suite(),
            passed=False,
            status=P269_STATUS_REJECTED_PILLAR_46A,
        )
        with mock.patch.object(
            p269, "run_pillar46a_file_settings_and_still_folder_vault_6_scenario_suite", return_value=bad_a
        ):
            rep = run_pillar46_standalone_suite(force_clean_room=True)
        self.assertFalse(rep.all_passed)
        self.assertEqual(rep.status, P269_STATUS_FAIL_PILLAR46_SUITE)
        self.assertEqual(rep.slot1_vault_folder_mutation_events, 1)

        bad_b = replace(
            run_pillar46b_gamma_assist_lut_auto_review_tcub_vault_6_scenario_suite(),
            passed=False,
            status=P269_STATUS_REJECTED_PILLAR_46B,
        )
        with mock.patch.object(
            p269, "run_pillar46b_gamma_assist_lut_auto_review_tcub_vault_6_scenario_suite", return_value=bad_b
        ):
            rep_b = run_pillar46_standalone_suite(force_clean_room=True)
        self.assertFalse(rep_b.all_passed)
        self.assertEqual(rep_b.gamma_assist_log_lockout_bypass_events, 1)

    # ------------------------------------------------------------------
    # 5. Unified 46/46 Recovery Master Aggregator & Fault Injection
    # ------------------------------------------------------------------

    def test_44_master46_default_passes_all_46_pillars_within_latency_budgets(self) -> None:
        rep = self.master46_default
        self.assertEqual(rep.schema, PHASE269_SCHEMA)
        self.assertEqual(rep.version, PHASE269_VERSION)
        self.assertTrue(rep.all_passed)
        self.assertEqual(rep.status, P269_STATUS_VERIFIED_46OF46_AGGREGATOR)
        self.assertEqual(rep.pillar_count, 46)
        self.assertEqual(rep.pillars_passed, 46)
        self.assertEqual(rep.failed_pillars, ())
        self.assertTrue(rep.nominal_under_4_0s)
        self.assertTrue(rep.under_6s_budget)
        self.assertEqual([p.pillar_number for p in rep.pillars], list(range(1, 47)))
        self.assertEqual(tuple(p.pillar_id for p in rep.pillars), MASTER_46_PILLAR_IDS)

    def test_45_master46_clean_room_passes_all_46_pillars_with_64hex_digest(self) -> None:
        rep = self.master46_clean_room
        self.assertTrue(rep.all_passed)
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(rep.status, P269_STATUS_VERIFIED_46OF46_AGGREGATOR)
        self.assertEqual(rep.pillar_count, 46)
        self.assertEqual(rep.pillars_passed, 46)
        self.assertEqual(rep.failed_pillars, ())
        self.assertEqual(len(rep.master_46pillar_sha256), 64)
        self.assertTrue(all(p.passed for p in rep.pillars))

    def test_46_fx3_clean_room_test_env_propagates_to_45pillar_and_matches_clean_room_digest(self) -> None:
        seen_kwargs = []

        def _mock_m45(**kwargs):
            seen_kwargs.append(kwargs)
            return self.master45_clean_room

        with (
            mock.patch.dict(os.environ, {"FX3_CLEAN_ROOM_TEST": "1"}, clear=False),
            mock.patch.object(p269, "evaluate_realhw_45pillar_recovery_master", side_effect=_mock_m45),
        ):
            rep_env = evaluate_realhw_46pillar_recovery_master()
        self.assertEqual(seen_kwargs, [{"force_clean_room": True}])
        self.assertEqual(rep_env.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(rep_env.master_46pillar_sha256, self.master46_clean_room.master_46pillar_sha256)

    def test_47_master46_hard_locked_zero_write_safety_telemetry(self) -> None:
        for rep in (self.master46_default, self.master46_clean_room):
            self.assertTrue(rep.cnflasha_userspace_write_blocked)
            self.assertEqual(rep.otp_fuse_touches, 0)
            self.assertEqual(rep.otp_fuse_writes, 0)
            self.assertEqual(rep.rpmb_counter_increments, 0)
            self.assertEqual(rep.passive_tx_bytes_emitted, 0)
            self.assertEqual(rep.physical_usb_packets_emitted, 0)
            self.assertEqual(rep.physical_device_writes, 0)
            self.assertEqual(rep.raw_firmware_bytes_leaked, 0)
            self.assertFalse(rep.el3_payload_transmit_authorized)
            self.assertFalse(rep.isp_write_authorized)
            self.assertFalse(rep.spi_nor_write_authorized)
            self.assertFalse(rep.persistent_emmc_writes_authorized)
            self.assertFalse(rep.persistent_write_release)
            self.assertFalse(rep.allow_boot_partition_targeting)
            self.assertFalse(rep.allow_destructive_fastboot)
            self.assertFalse(rep.live_usb_iokit_transmit_enabled)
            self.assertFalse(rep.hardware_live_attachment_authorized)

    def test_48_master46_wave44_and_preserved_pillars_1_to_45_rollup_metrics(self) -> None:
        rep = self.master46_clean_room
        self.assertEqual(rep.slot1_vault_folder_mutation_events, 0)
        self.assertEqual(rep.slot1_vault_folder_mutation_bytes, 0)
        self.assertEqual(rep.movie_custom_folder_or_title_overflow_events, 0)
        self.assertEqual(rep.still_prefix_underscore_lead_or_len_violations, 0)
        self.assertEqual(rep.gamma_assist_log_lockout_bypass_events, 0)
        self.assertEqual(rep.gamma_assist_external_hdmi_leak_events, 0)
        self.assertEqual(rep.tcub_camera_reset_wipe_or_format_violations, 0)
        self.assertFalse(rep.fx3_has_builtin_end_filter)
        self.assertEqual(rep.e_nd_actuator_tx_count, 0)
        self.assertEqual(rep.cardless_unrecorded_production_violations, 0)
        self.assertEqual(rep.legacy_v1_audio_level_menu_spoof_events, 0)
        self.assertEqual(rep.photographer_copyright_pii_leaked_bytes, 0)
        self.assertEqual(rep.copyright_char_overflow_or_movie_mutation_events, 0)
        self.assertEqual(rep.slot1_copyright_vault_mutation_bytes, 0)
        self.assertEqual(rep.apsc_s35_4k_or_raw_bypass_events, 0)
        self.assertGreaterEqual(rep.bodydata_flash_attempts_blocked, 1)
        self.assertFalse(rep.fx3_has_builtin_evf)
        self.assertFalse(rep.fx3_has_var_shutter)

    def test_49_master46_symmetry_aliases_match_exact_sha256(self) -> None:
        with mock.patch.object(
            p269, "evaluate_realhw_45pillar_recovery_master", return_value=self.master45_clean_room
        ):
            r1 = evaluate_46pillar_recovery_master(force_clean_room=True)
            r2 = verify_46pillar_recovery_suite(force_clean_room=True)
        self.assertEqual(r1.master_46pillar_sha256, self.master46_clean_room.master_46pillar_sha256)
        self.assertEqual(r2.master_46pillar_sha256, self.master46_clean_room.master_46pillar_sha256)

    def test_50_master46_pillar46_status_entry_contains_wave44_metrics(self) -> None:
        p46 = self.master46_clean_room.pillars[45]
        self.assertEqual(p46.pillar_number, 46)
        self.assertEqual(p46.pillar_id, "pillar_46_file_settings_gamma_assist_tcub_vault")
        self.assertTrue(p46.passed)
        self.assertEqual(p46.key_metrics["pillar_46a_file_settings_still_folder_vault"], "6/6")
        self.assertEqual(p46.key_metrics["pillar_46b_gamma_assist_lut_auto_review_tcub_vault"], "6/6")
        self.assertEqual(p46.key_metrics["slot1_vault_folder_mutation_events"], 0)
        self.assertEqual(p46.key_metrics["gamma_assist_log_lockout_bypass_events"], 0)
        self.assertEqual(p46.key_metrics["donor_files_inspected"], 16)

    def test_51_fault_injection_pillar_1_fails_master46_closed(self) -> None:
        pid = MASTER_46_PILLAR_IDS[0]
        with mock.patch.object(
            p269, "evaluate_realhw_45pillar_recovery_master", return_value=self.master45_clean_room
        ):
            rep = evaluate_realhw_46pillar_recovery_master(force_clean_room=True, fault_inject_pillar=pid)
        self.assertFalse(rep.all_passed)
        self.assertEqual(rep.status, P269_STATUS_FAIL_46OF46_AGGREGATOR)
        self.assertEqual(rep.pillars_passed, 45)
        self.assertEqual(rep.failed_pillars, (pid,))

    def test_52_fault_injection_pillar_31_and_pillar_45_fail_master46_closed(self) -> None:
        for idx in (30, 44):
            pid = MASTER_46_PILLAR_IDS[idx]
            with (
                self.subTest(pid=pid),
                mock.patch.object(
                    p269, "evaluate_realhw_45pillar_recovery_master", return_value=self.master45_clean_room
                ),
            ):
                rep = evaluate_realhw_46pillar_recovery_master(force_clean_room=True, fault_inject_pillar=pid)
                self.assertFalse(rep.all_passed)
                self.assertEqual(rep.pillars_passed, 45)
                self.assertEqual(rep.failed_pillars, (pid,))

    def test_53_fault_injection_pillar_46_fails_master46_closed(self) -> None:
        pid = MASTER_46_PILLAR_IDS[45]
        with mock.patch.object(
            p269, "evaluate_realhw_45pillar_recovery_master", return_value=self.master45_clean_room
        ):
            rep = evaluate_realhw_46pillar_recovery_master(force_clean_room=True, fault_inject_pillar=pid)
        self.assertFalse(rep.all_passed)
        self.assertEqual(rep.status, P269_STATUS_FAIL_46OF46_AGGREGATOR)
        self.assertEqual(rep.pillars_passed, 45)
        self.assertEqual(rep.failed_pillars, (pid,))
        self.assertIn(f"FAULT_INJECTED:{pid}", rep.pillars[45].errors)

    def test_54_fault_injection_unknown_pillar_id_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            evaluate_realhw_46pillar_recovery_master(
                force_clean_room=True,
                fault_inject_pillar="pillar_99_nonexistent",
            )

    def test_55_master46_raises_value_error_if_global_safety_constant_tampered(self) -> None:
        with (
            mock.patch.object(p269, "OTP_FUSE_TOUCHES", 1),
            self.assertRaises(ValueError),
        ):
            evaluate_realhw_46pillar_recovery_master(force_clean_room=True)

    def test_56_master46_fails_closed_when_m45_zero_write_telemetry_violated(self) -> None:
        bad_m45 = replace(self.master45_clean_room, otp_fuse_touches=1, cnflasha_userspace_write_blocked=False)
        with mock.patch.object(p269, "evaluate_realhw_45pillar_recovery_master", return_value=bad_m45):
            rep = evaluate_realhw_46pillar_recovery_master(force_clean_room=True)
        self.assertFalse(rep.all_passed)
        self.assertEqual(rep.status, P269_STATUS_FAIL_46OF46_AGGREGATOR)
        self.assertTrue(any("otp_fuse_touches" in e for e in rep.errors))

    def test_57_master46_fails_closed_when_m45_rollup_or_bodydata_block_violated(self) -> None:
        bad_m45 = replace(
            self.master45_clean_room,
            e_nd_actuator_tx_count=2,
            bodydata_flash_attempts_blocked=0,
        )
        with mock.patch.object(p269, "evaluate_realhw_45pillar_recovery_master", return_value=bad_m45):
            rep = evaluate_realhw_46pillar_recovery_master(force_clean_room=True)
        self.assertFalse(rep.all_passed)
        self.assertTrue(any("e_nd_actuator_tx_count" in e for e in rep.errors))
        self.assertTrue(any("bodydata_flash_attempts_blocked" in e for e in rep.errors))

    def test_58_master46_fails_closed_when_p46_wave44_telemetry_violated(self) -> None:
        bad_p46 = replace(
            run_pillar46_standalone_suite(force_clean_room=True),
            slot1_vault_folder_mutation_events=1,
            gamma_assist_log_lockout_bypass_events=1,
            otp_fuse_touches=1,
        )
        with (
            mock.patch.object(p269, "evaluate_realhw_45pillar_recovery_master", return_value=self.master45_clean_room),
            mock.patch.object(p269, "run_pillar46_standalone_suite", return_value=bad_p46),
        ):
            rep = evaluate_realhw_46pillar_recovery_master(force_clean_room=True)
        self.assertFalse(rep.all_passed)
        self.assertEqual(rep.status, P269_STATUS_FAIL_46OF46_AGGREGATOR)
        self.assertTrue(any("slot1_vault_folder_mutation_events" in e for e in rep.errors))
        self.assertTrue(any("gamma_assist_log_lockout_bypass_events" in e for e in rep.errors))

    def test_59_master46_to_dict_json_roundtrip_contains_all_46_pillars(self) -> None:
        d = self.master46_clean_room.to_dict()
        raw = json.dumps(d, sort_keys=True)
        parsed = json.loads(raw)
        self.assertEqual(parsed["pillar_count"], 46)
        self.assertEqual(parsed["pillars_passed"], 46)
        self.assertEqual(len(parsed["pillars"]), 46)
        self.assertEqual(parsed["raw_firmware_bytes_leaked"], 0)

    def test_60_need_helper_raises_value_error_when_false(self) -> None:
        p269._need(True, "ok")
        with self.assertRaises(ValueError):
            p269._need(False, "boom")

    # ------------------------------------------------------------------
    # 6. CLI Subcommands & Firmware Version Matrix
    # ------------------------------------------------------------------

    @staticmethod
    def _run_inprocess_cli(*argv: str):
        import sys as _sys

        buf = io.StringIO()
        with (
            mock.patch.object(_sys, "argv", ["fx3_recovery", *argv]),
            redirect_stdout(buf),
        ):
            rc = cli_main.main()
        return rc, buf.getvalue()

    def test_61_cli_verify_file_settings_gamma_assist_tcub_vault_json(self) -> None:
        rc, out = self._run_inprocess_cli(
            "verify-file-settings-gamma-assist-tcub-vault", "--json"
        )
        self.assertEqual(rc, 0)
        payload = json.loads(out)
        self.assertTrue(payload["all_passed"])
        self.assertEqual(payload["status"], P269_STATUS_VERIFIED_PILLAR46_SUITE)
        self.assertEqual(payload["slot1_vault_folder_mutation_events"], 0)
        self.assertEqual(payload["gamma_assist_log_lockout_bypass_events"], 0)
        self.assertEqual(payload["gamma_assist_external_hdmi_leak_events"], 0)
        self.assertEqual(payload["tcub_camera_reset_wipe_or_format_violations"], 0)

    def test_62_cli_verify_file_settings_gamma_assist_tcub_vault_clean_room_text(self) -> None:
        rc, out = self._run_inprocess_cli(
            "verify-file-settings-gamma-assist-tcub-vault", "--clean-room"
        )
        self.assertEqual(rc, 0)
        self.assertIn(f"status={P269_STATUS_VERIFIED_PILLAR46_SUITE}", out)
        self.assertIn("mode=CLEAN_ROOM_SYNTHETIC", out)
        self.assertIn("pillar_46a=6/6", out)
        self.assertIn("pillar_46b=6/6", out)

    def test_63_cli_verify_file_settings_gamma_assist_tcub_vault_out_file(self) -> None:
        here = Path(__file__).resolve().parent
        out_dir = here / f"_tmp_p269_p46_{os.getpid()}"
        rep_file = out_dir / "pillar46-file-settings-gamma-assist-tcub-vault-report.json"
        if rep_file.is_file():
            rep_file.unlink()
        if out_dir.is_dir():
            out_dir.rmdir()
        try:
            rc, _ = self._run_inprocess_cli(
                "verify-file-settings-gamma-assist-tcub-vault",
                "--force-clean-room",
                "--out",
                str(out_dir),
            )
            self.assertEqual(rc, 0)
            self.assertTrue(rep_file.is_file())
            saved = json.loads(rep_file.read_text(encoding="utf-8"))
            self.assertTrue(saved["all_passed"])
            self.assertEqual(saved["verification_mode"], "CLEAN_ROOM_SYNTHETIC")
        finally:
            if rep_file.is_file():
                rep_file.unlink()
            if out_dir.is_dir():
                out_dir.rmdir()

    def test_64_cli_verify_file_settings_gamma_assist_tcub_vault_exit_2_on_failure(self) -> None:
        bad_suite = replace(
            run_pillar46_standalone_suite(force_clean_room=True),
            all_passed=False,
            status=P269_STATUS_FAIL_PILLAR46_SUITE,
        )
        with mock.patch.object(cli_main, "run_pillar46_standalone_suite", return_value=bad_suite):
            rc, out = self._run_inprocess_cli(
                "verify-file-settings-gamma-assist-tcub-vault", "--clean-room"
            )
        self.assertEqual(rc, 2)
        self.assertIn(f"status={P269_STATUS_FAIL_PILLAR46_SUITE}", out)

    def test_65_cli_verify_46pillar_recovery_clean_room_json_end_to_end(self) -> None:
        with mock.patch.object(
            p269, "evaluate_realhw_45pillar_recovery_master", return_value=self.master45_clean_room
        ):
            rc, out = self._run_inprocess_cli("verify-46pillar-recovery", "--clean-room", "--json")
        self.assertEqual(rc, 0)
        payload = json.loads(out)
        self.assertTrue(payload["all_passed"])
        self.assertEqual(payload["pillar_count"], 46)
        self.assertEqual(payload["pillars_passed"], 46)
        self.assertEqual(payload["status"], P269_STATUS_VERIFIED_46OF46_AGGREGATOR)
        self.assertEqual(payload["verification_mode"], "CLEAN_ROOM_SYNTHETIC")

    def test_66_cli_verify_46pillar_recovery_force_clean_room_human_summary(self) -> None:
        with mock.patch.object(
            cli_main, "verify_46pillar_recovery_suite", return_value=self.master46_clean_room
        ) as mocked_suite:
            rc, out = self._run_inprocess_cli("verify-46pillar-recovery", "--force-clean-room")
        self.assertEqual(rc, 0)
        mocked_suite.assert_called_once_with(force_clean_room=True)
        self.assertIn("status=VERIFIED_46OF46_PILLAR_RECOVERY_MASTER", out)
        self.assertIn("pillars=46/46", out)
        self.assertIn("pillar46_a=6/6", out)
        self.assertIn("pillar46_b=6/6", out)

    def test_67_cli_verify_46pillar_recovery_out_file_serialization(self) -> None:
        here = Path(__file__).resolve().parent
        out_dir = here / f"_tmp_p269_m46_{os.getpid()}"
        rep_file = out_dir / "46pillar-recovery-master-report.json"
        if rep_file.is_file():
            rep_file.unlink()
        if out_dir.is_dir():
            out_dir.rmdir()
        try:
            with mock.patch.object(
                cli_main,
                "verify_46pillar_recovery_suite",
                return_value=self.master46_clean_room,
            ):
                rc, _ = self._run_inprocess_cli(
                    "verify-46pillar-recovery", "--json", "--out", str(out_dir)
                )
            self.assertEqual(rc, 0)
            self.assertTrue(rep_file.is_file())
            saved = json.loads(rep_file.read_text(encoding="utf-8"))
            self.assertEqual(saved["pillar_count"], 46)
            self.assertEqual(saved["master_46pillar_sha256"], self.master46_clean_room.master_46pillar_sha256)
        finally:
            if rep_file.is_file():
                rep_file.unlink()
            if out_dir.is_dir():
                out_dir.rmdir()

    def test_68_cli_verify_46pillar_recovery_returns_2_when_failed(self) -> None:
        bad_master = replace(
            self.master46_clean_room,
            all_passed=False,
            status=P269_STATUS_FAIL_46OF46_AGGREGATOR,
            pillars_passed=45,
            failed_pillars=(MASTER_46_PILLAR_IDS[-1],),
        )
        with mock.patch.object(cli_main, "verify_46pillar_recovery_suite", return_value=bad_master):
            rc, out = self._run_inprocess_cli("verify-46pillar-recovery")
        self.assertEqual(rc, 2)
        self.assertIn("status=FAIL_46OF46_PILLAR_RECOVERY_MASTER", out)
        self.assertIn("pillars=45/46", out)

    def test_69_cli_dispatches_phase269_and_preserves_45pillar_subcommand_routing(self) -> None:
        with mock.patch.object(
            cli_main, "verify_45pillar_recovery_suite", return_value=self.master45_clean_room
        ) as m45_fn:
            rc45, out45 = self._run_inprocess_cli("verify-45pillar-recovery", "--clean-room", "--json")
        self.assertEqual(rc45, 0)
        m45_fn.assert_called_once_with(force_clean_room=True)
        self.assertEqual(json.loads(out45)["pillar_count"], 45)

    def test_70_supported_fx3_fw_versions_300_through_702_pass_and_unknown_fw_rejected(self) -> None:
        for fw in P269_FX3_SUPPORTED_FW_VERSIONS:
            with self.subTest(fw=fw):
                ra = evaluate_file_settings_and_still_folder_vault(
                    FileSettingsAndStillFolderVaultSpec(fw_version=fw)
                )
                rb = evaluate_gamma_assist_lut_auto_review_tcub_vault(
                    GammaAssistLutAutoReviewTcubVaultSpec(fw_version=fw)
                )
                self.assertTrue(ra.passed)
                self.assertTrue(rb.passed)

        ra_bad = evaluate_file_settings_and_still_folder_vault(
            FileSettingsAndStillFolderVaultSpec(fw_version="9.99")
        )
        rb_bad = evaluate_gamma_assist_lut_auto_review_tcub_vault(
            GammaAssistLutAutoReviewTcubVaultSpec(fw_version="9.99")
        )
        self.assertFalse(ra_bad.passed)
        self.assertEqual(ra_bad.block_code, P269_BLOCKED_INVALID_FILE_OR_FOLDER_SETTINGS_SPEC)
        self.assertFalse(rb_bad.passed)
        self.assertEqual(rb_bad.block_code, P269_BLOCKED_INVALID_GAMMA_ASSIST_LUT_TCUB_SPEC)


if __name__ == "__main__":
    unittest.main()
