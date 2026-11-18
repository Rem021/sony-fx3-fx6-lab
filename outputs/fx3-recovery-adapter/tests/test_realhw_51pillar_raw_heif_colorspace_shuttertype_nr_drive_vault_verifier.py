"""Phase 292 — Dual-mode unit tests for Pillar 51
(Still `[Image Quality Settings]` `Compressed`/`Uncompressed` `.ARW` vs dormant `Lossless Comp`,
`JPEG/HEIF Switch` `4:2:0/4:2:2` `.HIF`, `[HLG Still Image]` `BT.2100` & 4 lockouts vs
still-less `ILME-FX6`, `[Color Space]` `AdobeRGB` `_DSC` prefix, `[Set File Name]` leading-`_`
ban, `[Shutter Type]` 2-option split without `Auto`, `1/250 s` flash sync, Electronic/Silent
5-Lock Matrix, `[e-Front Curtain Shut.]`, `[Long Exposure NR]` / `[High ISO NR]`, `[Drive Mode]`
`10 fps` burst / `F > F11` AF lock, and `Slot-1` `EROFS`/`EBUSY` Vault Firewall)
and unified `51/51` recovery master (`verify-51pillar-recovery` /
`verify-pillar51-raw-heif-colorspace-shuttertype-vault`).
"""

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
    realhw_51pillar_raw_heif_colorspace_shuttertype_nr_drive_vault_verifier as p292,
)
from fx3_recovery.realhw_50pillar_pp_scinetone_creativelook_dro_wb_metering_vault_verifier import (
    evaluate_realhw_50pillar_recovery_master,
)
from fx3_recovery.realhw_51pillar_raw_heif_colorspace_shuttertype_nr_drive_vault_verifier import (
    ALLOW_BOOT_PARTITION_TARGETING,
    ALLOW_DESTRUCTIVE_FASTBOOT,
    ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS,
    ALLOW_PERSISTENT_JIRITSU_WRITES,
    CNFLASHA_USERSPACE_WRITE_BLOCKED,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    ISP_WRITE_AUTHORIZED,
    LIVE_USB_IOKIT_TRANSMIT_ENABLED,
    MASTER_51_PILLAR_COUNT,
    MASTER_51_PILLAR_IDS,
    MASTER_51_PILLAR_SPECS,
    OTP_FUSE_TOUCHES,
    OTP_FUSE_WRITES,
    OVERALL_READY_FOR_HARDWARE_ATTACH,
    P292_AF_LOCK_APERTURE_THRESHOLD_F,
    P292_BLOCKED_COLORSPACE_ADOBERGB_OR_PREFIX_VIOLATION,
    P292_BLOCKED_DORMANT_LOSSLESS_RAW_EXPOSURE,
    P292_BLOCKED_ELECTRONIC_SILENT_5LOCK_BYPASS,
    P292_BLOCKED_FX6_STILL_PIPELINE_CONFLATION,
    P292_BLOCKED_HLG_STILL_PREREQ_OR_LOCKOUT_DRIFT,
    P292_BLOCKED_INVALID_PILLAR51A_SPEC,
    P292_BLOCKED_INVALID_PILLAR51B_SPEC,
    P292_BLOCKED_NR_OR_DRIVE_BURST_WALL_VIOLATION,
    P292_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
    P292_BLOCKED_SAFETY_POLICY_VIOLATION,
    P292_BLOCKED_SHUTTER_TYPE_AUTO_OR_FX6_CONFLATION,
    P292_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL,
    P292_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
    P292_COLOR_SPACE_BKID,
    P292_COLOR_SPACE_DEFAULT,
    P292_COLOR_SPACE_MODES,
    P292_CONT_SHOOTING_4_SPEEDS,
    P292_CONT_SHOOTING_FPS_MAP,
    P292_DONOR_INSPECT_BUDGET_SECONDS,
    P292_DORMANT_LOSSLESS_RAW_MODES,
    P292_DORMANT_SHUTTER_TYPES,
    P292_DRIVE_8_MODES,
    P292_DRIVE_MODE_BKID,
    P292_DRIVE_MODE_DEFAULT,
    P292_EFRONT_CURTAIN_BKID,
    P292_EFRONT_CURTAIN_DEFAULT,
    P292_ELECTRONIC_SILENT_5LOCK_FUNCTIONS,
    P292_ENV_CLEAN_ROOM_TEST,
    P292_FAST_CLI_BUDGET_SECONDS,
    P292_FX3_EXPOSED_RAW_FILE_TYPES,
    P292_FX3_EXPOSED_SHUTTER_TYPES,
    P292_FX3_FW_VERSION,
    P292_FX3_HELPGUIDE_ID,
    P292_FX3_MAX_FLASH_SYNC_DENOM,
    P292_FX3_MODEL_ID,
    P292_FX3_MODEL_NAME,
    P292_FX3_SENSOR_FAMILY,
    P292_FX3_UI_EXPOSES_LOSSLESS_RAW,
    P292_FX3_UI_EXPOSES_SHUTTER_TYPE_AUTO,
    P292_FX6_MECHANICAL_SHUTTER_PRESENT,
    P292_FX6_STILL_PIPELINE_PRESENT,
    P292_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    P292_HIGH_ISO_NR_BKID,
    P292_HIGH_ISO_NR_DEFAULT,
    P292_HIGH_ISO_NR_MODES,
    P292_HLG_STILL_BKID,
    P292_HLG_STILL_DEFAULT,
    P292_JPEG_HEIF_SWITCH_BKID,
    P292_JPEG_HEIF_SWITCH_DEFAULT,
    P292_JPEG_HEIF_SWITCH_MODES,
    P292_LONG_EXPOSURE_NR_BKID,
    P292_LONG_EXPOSURE_NR_DEFAULT,
    P292_LONG_EXPOSURE_NR_THRESHOLD_SEC,
    P292_OVERALL_READY_FOR_HARDWARE_ATTACH,
    P292_PINNED_FX3_APPFW_702_BYTES,
    P292_PINNED_FX3_APPFW_702_HDR4K_SHA256,
    P292_PINNED_FX3_BACKUP_BIN_BYTES,
    P292_PINNED_FX3_BACKUP_BIN_SHA256,
    P292_PINNED_FX3_UXC_EN_F_BYTES,
    P292_PINNED_FX3_UXC_EN_F_SHA256,
    P292_PINNED_FX6_APPFW_601_BYTES,
    P292_PINNED_FX6_APPFW_601_HDR4K_SHA256,
    P292_SET_FILE_NAME_BKID,
    P292_SET_FILE_NAME_DEFAULT,
    P292_SHUTTER_TYPE_BKID,
    P292_SHUTTER_TYPE_DEFAULT,
    P292_SILENT_MODE_BKID,
    P292_SILENT_MODE_DEFAULT,
    P292_SLOT1_FORMAT_HARD_LOCKED,
    P292_SLOT1_VAULT_EROFS_EBUSY_ENFORCED,
    P292_STATUS_FAIL_51OF51_AGGREGATOR,
    P292_STATUS_FAIL_PILLAR51_SUITE,
    P292_STATUS_VERIFIED_51OF51_AGGREGATOR,
    P292_STATUS_VERIFIED_PILLAR51_SUITE,
    P292_STATUS_VERIFIED_PILLAR_51A,
    P292_STATUS_VERIFIED_PILLAR_51B,
    P292_STILL_FILE_FORMATS,
    P292_STILL_FILE_FORMAT_BKID,
    P292_STILL_FILE_FORMAT_DEFAULT,
    P292_STILL_RAW_BIT_DEPTH,
    P292_STILL_RAW_FILE_TYPE_BKID,
    P292_STILL_RAW_FILE_TYPE_DEFAULT,
    PASSIVE_TX_BYTES_EMITTED,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHASE292_PHASE_NUMBER,
    PHASE292_SCHEMA,
    PHASE292_VERSION,
    PHYSICAL_DEVICE_WRITES,
    PHYSICAL_USB_PACKETS_EMITTED,
    RAW_FIRMWARE_BYTES_LEAKED,
    READ_ONLY_DONOR_ACCESS,
    RPMB_COUNTER_INCREMENTS,
    SPI_NOR_WRITE_AUTHORIZED,
    ShutterTypeNrDriveVaultSpec,
    StillImageQualityHlgColorspaceFilenameVaultSpec,
    build_default_safe_shutter_type_nr_drive_vault_spec,
    build_default_safe_still_image_quality_hlg_colorspace_filename_vault_spec,
    compute_expected_colorspace_and_filename_prefix,
    compute_expected_nr_and_drive_mode_boundaries,
    compute_expected_shutter_type_and_5lock_matrix,
    compute_expected_still_image_quality_and_hlg_state,
    evaluate_51pillar_recovery_master,
    evaluate_realhw_51pillar_recovery_master,
    evaluate_shutter_type_nr_drive_vault,
    evaluate_still_image_quality_hlg_colorspace_filename_vault,
    inspect_phase292_donors_readonly,
    is_valid_fx3_still_filename_prefix,
    run_pillar51_standalone_suite,
    run_pillar51a_raw_heif_hlg_colorspace_6_scenario_suite,
    run_pillar51b_shuttertype_nr_drive_6_scenario_suite,
    verify_51pillar_recovery_suite,
    verify_raw_heif_colorspace_shuttertype_nr_drive_and_vault,
    verify_raw_heif_colorspace_shuttertype_nr_drive_vault,
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _is_ci() -> bool:
    return os.environ.get("GITHUB_ACTIONS") == "true"


def _clean_room_forced_by_env() -> bool:
    return (
        os.environ.get(P292_ENV_CLEAN_ROOM_TEST) == "1"
        or os.environ.get("FX3_FX6_FORCE_CLEAN_ROOM") == "1"
    )


class TestPhase292Pillar51And51PillarRecoveryMaster(unittest.TestCase):
    # ------------------------------------------------------------------
    # 1. Safety Invariants & Firmware Reality Constants (1..6)
    # ------------------------------------------------------------------

    def test_01_safety_constants_hard_locked(self) -> None:
        self.assertTrue(CNFLASHA_USERSPACE_WRITE_BLOCKED)
        self.assertTrue(READ_ONLY_DONOR_ACCESS)
        self.assertTrue(P292_SLOT1_FORMAT_HARD_LOCKED)
        self.assertTrue(P292_SLOT1_VAULT_EROFS_EBUSY_ENFORCED)
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(PERSISTENT_WRITE_RELEASE)
        self.assertFalse(SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        self.assertFalse(ISP_WRITE_AUTHORIZED)
        self.assertFalse(LIVE_USB_IOKIT_TRANSMIT_ENABLED)
        self.assertFalse(HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        self.assertFalse(OVERALL_READY_FOR_HARDWARE_ATTACH)
        self.assertFalse(P292_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        self.assertFalse(P292_OVERALL_READY_FOR_HARDWARE_ATTACH)
        self.assertFalse(ALLOW_BOOT_PARTITION_TARGETING)
        self.assertFalse(ALLOW_DESTRUCTIVE_FASTBOOT)
        self.assertFalse(ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS)
        self.assertFalse(ALLOW_PERSISTENT_JIRITSU_WRITES)
        self.assertEqual(OTP_FUSE_TOUCHES, 0)
        self.assertEqual(OTP_FUSE_WRITES, 0)
        self.assertEqual(RPMB_COUNTER_INCREMENTS, 0)
        self.assertEqual(PASSIVE_TX_BYTES_EMITTED, 0)
        self.assertEqual(PHYSICAL_USB_PACKETS_EMITTED, 0)
        self.assertEqual(PHYSICAL_DEVICE_WRITES, 0)
        self.assertEqual(RAW_FIRMWARE_BYTES_LEAKED, 0)

    def test_02_camera_baseline_and_phase_metadata(self) -> None:
        self.assertEqual(PHASE292_PHASE_NUMBER, 292)
        self.assertEqual(PHASE292_VERSION, "1.0.0")
        self.assertIn("51pillar", PHASE292_SCHEMA)
        self.assertEqual(P292_FX3_MODEL_NAME, "ILME-FX3")
        self.assertEqual(P292_FX3_MODEL_ID, 0x91030080)
        self.assertEqual(P292_FX3_HELPGUIDE_ID, "ilc/2210")
        self.assertEqual(P292_FX3_FW_VERSION, "7.02")
        self.assertEqual(P292_FX3_SENSOR_FAMILY, "12 MP IMX510")

    def test_03_fx3_raw_heif_hlg_colorspace_filename_constants(self) -> None:
        self.assertEqual(P292_FX3_EXPOSED_RAW_FILE_TYPES, ("Compressed", "Uncompressed"))
        self.assertEqual(P292_STILL_RAW_FILE_TYPE_DEFAULT, "Compressed")
        self.assertEqual(P292_STILL_RAW_BIT_DEPTH, 14)
        self.assertFalse(P292_FX3_UI_EXPOSES_LOSSLESS_RAW)
        self.assertIn("Lossless Comp", P292_DORMANT_LOSSLESS_RAW_MODES)
        self.assertFalse(P292_FX6_STILL_PIPELINE_PRESENT)
        self.assertEqual(P292_JPEG_HEIF_SWITCH_MODES, ("JPEG", "HEIF(4:2:0)", "HEIF(4:2:2)"))
        self.assertEqual(P292_JPEG_HEIF_SWITCH_DEFAULT, "JPEG")
        self.assertEqual(P292_STILL_FILE_FORMATS, ("RAW", "RAW & JPEG", "RAW & HEIF", "JPEG", "HEIF"))
        self.assertEqual(P292_STILL_FILE_FORMAT_DEFAULT, "JPEG")
        self.assertEqual(P292_HLG_STILL_DEFAULT, "Off")
        self.assertEqual(P292_COLOR_SPACE_MODES, ("sRGB", "AdobeRGB"))
        self.assertEqual(P292_COLOR_SPACE_DEFAULT, "sRGB")
        self.assertEqual(P292_SET_FILE_NAME_DEFAULT, "DSC")

    def test_04_fx3_shutter_type_5lock_nr_drive_constants(self) -> None:
        self.assertEqual(P292_FX3_EXPOSED_SHUTTER_TYPES, ("Mechanical Shutter", "Electronic Shutter"))
        self.assertEqual(P292_DORMANT_SHUTTER_TYPES, ("Auto",))
        self.assertFalse(P292_FX3_UI_EXPOSES_SHUTTER_TYPE_AUTO)
        self.assertFalse(P292_FX6_MECHANICAL_SHUTTER_PRESENT)
        self.assertEqual(P292_SHUTTER_TYPE_DEFAULT, "Mechanical Shutter")
        self.assertEqual(P292_EFRONT_CURTAIN_DEFAULT, "On")
        self.assertEqual(P292_SILENT_MODE_DEFAULT, "Off")
        self.assertEqual(P292_FX3_MAX_FLASH_SYNC_DENOM, 250)
        self.assertEqual(len(P292_ELECTRONIC_SILENT_5LOCK_FUNCTIONS), 5)
        self.assertEqual(P292_LONG_EXPOSURE_NR_DEFAULT, "On")
        self.assertEqual(P292_LONG_EXPOSURE_NR_THRESHOLD_SEC, 1.0)
        self.assertEqual(P292_HIGH_ISO_NR_MODES, ("Normal", "Low", "Off"))
        self.assertEqual(P292_HIGH_ISO_NR_DEFAULT, "Normal")
        self.assertEqual(len(P292_DRIVE_8_MODES), 8)
        self.assertEqual(P292_DRIVE_MODE_DEFAULT, "Single Shooting")
        self.assertEqual(P292_CONT_SHOOTING_4_SPEEDS, ("Hi+", "Hi", "Mid", "Lo"))
        self.assertEqual(P292_CONT_SHOOTING_FPS_MAP["Hi+"], 10)
        self.assertEqual(P292_AF_LOCK_APERTURE_THRESHOLD_F, 11.0)

    def test_05_bkid_and_master_51_pillar_catalog(self) -> None:
        self.assertEqual(P292_JPEG_HEIF_SWITCH_BKID, "BKID_APP_setting_jh_file_type")
        self.assertEqual(P292_STILL_FILE_FORMAT_BKID, "BKID_APP_setting_still_file_format")
        self.assertEqual(P292_STILL_RAW_FILE_TYPE_BKID, "BKID_APP_setting_still_raw_file_type")
        self.assertEqual(P292_HLG_STILL_BKID, "BKID_APP_setting_still_hlg_photo")
        self.assertEqual(P292_COLOR_SPACE_BKID, "BKID_APP_setting_still_color_space")
        self.assertEqual(P292_SET_FILE_NAME_BKID, "BKID_APP_set_file_name_prefix_still")
        self.assertEqual(P292_SHUTTER_TYPE_BKID, "BKID_APP_setting_still_shutter_type")
        self.assertEqual(P292_EFRONT_CURTAIN_BKID, "BKID_APP_setting_front_curtaion_shutter")
        self.assertEqual(P292_SILENT_MODE_BKID, "BKID_APP_setting_silent_mode")
        self.assertEqual(P292_LONG_EXPOSURE_NR_BKID, "BKID_APP_setting_still_long_exposure_nr")
        self.assertEqual(P292_HIGH_ISO_NR_BKID, "BKID_APP_setting_still_high_iso_nr")
        self.assertEqual(P292_DRIVE_MODE_BKID, "BKID_APP_setting_menu_drive_mode")

        self.assertEqual(MASTER_51_PILLAR_COUNT, 51)
        self.assertEqual(len(MASTER_51_PILLAR_SPECS), 51)
        self.assertEqual(len(MASTER_51_PILLAR_IDS), 51)
        self.assertEqual(len(set(MASTER_51_PILLAR_IDS)), 51)
        self.assertEqual(MASTER_51_PILLAR_SPECS[50][0], 51)
        self.assertEqual(
            MASTER_51_PILLAR_IDS[50],
            "pillar_51_raw_heif_colorspace_shuttertype_nr_drive_vault",
        )

    def test_06_default_spec_builders_produce_safe_specs(self) -> None:
        s51a = build_default_safe_still_image_quality_hlg_colorspace_filename_vault_spec()
        s51b = build_default_safe_shutter_type_nr_drive_vault_spec()
        self.assertIsInstance(s51a, StillImageQualityHlgColorspaceFilenameVaultSpec)
        self.assertIsInstance(s51b, ShutterTypeNrDriveVaultSpec)
        self.assertTrue(evaluate_still_image_quality_hlg_colorspace_filename_vault(s51a).passed)
        self.assertTrue(evaluate_shutter_type_nr_drive_vault(s51b).passed)

    # ------------------------------------------------------------------
    # 2. Bounded O_RDONLY Donor Inspection & Clean-Room Fallback (7..12)
    # ------------------------------------------------------------------

    def test_07_donor_inspection_clean_room_returns_17_pinned_artifacts(self) -> None:
        snap = inspect_phase292_donors_readonly(force_clean_room=True)
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(snap.all_donors_present)
        self.assertEqual(snap.donor_files_inspected, 17)
        self.assertEqual(len(snap.artifacts), 17)
        self.assertEqual(snap.raw_firmware_bytes_leaked, 0)
        self.assertTrue(all(a.matches_pinned and a.present for a in snap.artifacts))

    def test_08_donor_inspection_active_or_env_forced_clean_room(self) -> None:
        snap = inspect_phase292_donors_readonly()
        self.assertTrue(snap.all_donors_present)
        self.assertEqual(snap.donor_files_inspected, 17)
        self.assertEqual(snap.raw_firmware_bytes_leaked, 0)
        if _clean_room_forced_by_env():
            self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        elif snap.verification_mode == "LOCAL_DONOR_O_RDONLY":
            by_id = {a.artifact_id: a for a in snap.artifacts}
            self.assertEqual(by_id["fx3_appfw_702_so"].total_bytes, P292_PINNED_FX3_APPFW_702_BYTES)
            self.assertEqual(by_id["fx3_appfw_702_so"].header_bytes_read, 4096)
            self.assertEqual(
                by_id["fx3_appfw_702_so"].digest_sha256,
                P292_PINNED_FX3_APPFW_702_HDR4K_SHA256,
            )
            self.assertEqual(by_id["fx6_appfw_601_so"].total_bytes, P292_PINNED_FX6_APPFW_601_BYTES)
            self.assertEqual(
                by_id["fx6_appfw_601_so"].digest_sha256,
                P292_PINNED_FX6_APPFW_601_HDR4K_SHA256,
            )
            self.assertEqual(by_id["fx3_backup_bin"].total_bytes, P292_PINNED_FX3_BACKUP_BIN_BYTES)
            self.assertEqual(by_id["fx3_backup_bin"].digest_sha256, P292_PINNED_FX3_BACKUP_BIN_SHA256)
            self.assertEqual(by_id["fx3_uxc_en_f"].total_bytes, P292_PINNED_FX3_UXC_EN_F_BYTES)
            self.assertEqual(by_id["fx3_uxc_en_f"].digest_sha256, P292_PINNED_FX3_UXC_EN_F_SHA256)

    def test_09_donor_inspection_missing_donor_falls_back_to_clean_room(self) -> None:
        with mock.patch.object(p292, "_is_clean_room_forced", return_value=False):
            with mock.patch.object(
                p292,
                "_read_donor_readonly_bounded",
                return_value=(False, 0, 0, "MISSING", "", b""),
            ):
                snap = inspect_phase292_donors_readonly()
                self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
                self.assertTrue(snap.all_donors_present)
                self.assertEqual(snap.donor_files_inspected, 17)

    def test_10_env_clean_room_test_and_fx6_force_flags(self) -> None:
        with mock.patch.dict(os.environ, {P292_ENV_CLEAN_ROOM_TEST: "1"}):
            snap = inspect_phase292_donors_readonly()
            self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            snap2 = inspect_phase292_donors_readonly()
            self.assertEqual(snap2.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_11_donor_read_latency_with_ci_headroom(self) -> None:
        snap = inspect_phase292_donors_readonly()
        ceiling = 15.0 if _is_ci() else P292_DONOR_INSPECT_BUDGET_SECONDS
        self.assertLess(snap.elapsed_seconds, ceiling)
        if not _is_ci():
            self.assertTrue(snap.under_0_20s_budget)

    def test_12_donor_bounded_read_never_reads_full_appfw_so(self) -> None:
        snap = inspect_phase292_donors_readonly(force_clean_room=True)
        for art in snap.artifacts:
            if art.artifact_id in ("fx3_appfw_702_so", "fx6_appfw_601_so"):
                self.assertEqual(art.digest_kind, "HEADER4K_SHA256")
                self.assertEqual(art.header_bytes_read, 4096)

    # ------------------------------------------------------------------
    # 3. Pillar 51A — Still RAW/HEIF, HLG Still, Color Space & Vault (13..32)
    # ------------------------------------------------------------------

    def test_13_pillar51a_default_safe_passes(self) -> None:
        rep = evaluate_still_image_quality_hlg_colorspace_filename_vault()
        self.assertTrue(rep.passed, rep.errors)
        self.assertEqual(rep.status, P292_STATUS_VERIFIED_PILLAR_51A)
        self.assertIsNone(rep.block_code)
        self.assertGreaterEqual(rep.matrix_states_checked, 60)
        self.assertEqual(rep.dormant_lossless_raw_exposure_events, 0)
        self.assertEqual(rep.slot1_still_capture_or_sort_write_bytes, 0)

    def test_14_pillar51a_compressed_and_uncompressed_14bit_raw_pass(self) -> None:
        for rft in ("Compressed", "Uncompressed"):
            rep = evaluate_still_image_quality_hlg_colorspace_filename_vault(
                StillImageQualityHlgColorspaceFilenameVaultSpec(
                    file_format="RAW",
                    raw_file_type=rft,
                )
            )
            self.assertTrue(rep.passed, f"{rft} failed: {rep.errors}")

    def test_15_pillar51a_dormant_lossless_comp_raw_rejected_fail_closed(self) -> None:
        for dormant in P292_DORMANT_LOSSLESS_RAW_MODES:
            rep = evaluate_still_image_quality_hlg_colorspace_filename_vault(
                StillImageQualityHlgColorspaceFilenameVaultSpec(
                    file_format="RAW",
                    raw_file_type=dormant,
                )
            )
            self.assertFalse(rep.passed)
            self.assertEqual(rep.block_code, P292_BLOCKED_DORMANT_LOSSLESS_RAW_EXPOSURE)
            self.assertGreaterEqual(rep.dormant_lossless_raw_exposure_events, 1)

    def test_16_pillar51a_fx3_ui_exposes_lossless_raw_flag_rejected(self) -> None:
        rep = evaluate_still_image_quality_hlg_colorspace_filename_vault(
            StillImageQualityHlgColorspaceFilenameVaultSpec(fx3_ui_exposes_lossless_raw=True)
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P292_BLOCKED_DORMANT_LOSSLESS_RAW_EXPOSURE)

    def test_17_pillar51a_fx6_still_pipeline_conflation_rejected(self) -> None:
        rep = evaluate_still_image_quality_hlg_colorspace_filename_vault(
            StillImageQualityHlgColorspaceFilenameVaultSpec(
                still_surface_model="FX6_STILL_LESS_MOVIE_RAW_HLG_PIPELINE",
                fx6_still_pipeline_present=True,
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P292_BLOCKED_FX6_STILL_PIPELINE_CONFLATION)
        self.assertGreaterEqual(rep.fx6_still_pipeline_conflation_events, 1)

    def test_18_pillar51a_heif_420_and_422_hif_and_hlg_still_on_valid(self) -> None:
        for sw in ("HEIF(4:2:0)", "HEIF(4:2:2)"):
            for mode in ("P", "A", "S", "M"):
                rep = evaluate_still_image_quality_hlg_colorspace_filename_vault(
                    StillImageQualityHlgColorspaceFilenameVaultSpec(
                        jpeg_heif_switch=sw,
                        file_format="HEIF",
                        shooting_mode=mode,
                        configured_hlg_still="On",
                        reported_hlg_still="On",
                        reported_picture_profile_locked=True,
                        reported_creative_look_locked=True,
                        reported_dro_locked=True,
                        reported_dro_bracket_locked=True,
                        reported_hlg_iso_bounds_shifted=True,
                        configured_color_space="AdobeRGB",
                        reported_effective_color_space="BT.2100",
                        reported_filename_stem="DSC00001",
                    )
                )
                self.assertTrue(rep.passed, f"{sw} + {mode} failed: {rep.errors}")

    def test_19_pillar51a_hlg_still_requires_heif_switch_heif_only_pasm_and_no_reg_custom(self) -> None:
        # 1) JPEG switch blocks HLG Still
        r1 = compute_expected_still_image_quality_and_hlg_state(
            jpeg_heif_switch="JPEG",
            file_format="HEIF",
            raw_file_type="Compressed",
            shooting_mode="M",
            configured_hlg_still="On",
            reg_custom_iso_or_dro_bracket_active=False,
        )
        self.assertEqual(r1[1], "Off")
        self.assertEqual(r1[2], ".JPG")

        # 2) RAW & HEIF blocks HLG Still
        r2 = compute_expected_still_image_quality_and_hlg_state(
            jpeg_heif_switch="HEIF(4:2:2)",
            file_format="RAW & HEIF",
            raw_file_type="Compressed",
            shooting_mode="M",
            configured_hlg_still="On",
            reg_custom_iso_or_dro_bracket_active=False,
        )
        self.assertEqual(r2[1], "Off")
        self.assertEqual(r2[2], ".HIF")

        # 3) Intelligent Auto blocks HLG Still
        r3 = compute_expected_still_image_quality_and_hlg_state(
            jpeg_heif_switch="HEIF(4:2:0)",
            file_format="HEIF",
            raw_file_type="Compressed",
            shooting_mode="Intelligent Auto",
            configured_hlg_still="On",
            reg_custom_iso_or_dro_bracket_active=False,
        )
        self.assertEqual(r3[1], "Off")

        # 4) Reg. Custom Shoot Set ISO/DRO Bracket active blocks HLG Still
        r4 = compute_expected_still_image_quality_and_hlg_state(
            jpeg_heif_switch="HEIF(4:2:0)",
            file_format="HEIF",
            raw_file_type="Compressed",
            shooting_mode="M",
            configured_hlg_still="On",
            reg_custom_iso_or_dro_bracket_active=True,
        )
        self.assertEqual(r4[1], "Off")

    def test_20_pillar51a_hlg_still_missing_lockout_or_prereq_bypass_rejected(self) -> None:
        # Missing Picture Profile / Creative Look / DRO / DRO Bracket lockout
        rep_lock = evaluate_still_image_quality_hlg_colorspace_filename_vault(
            StillImageQualityHlgColorspaceFilenameVaultSpec(
                jpeg_heif_switch="HEIF(4:2:2)",
                file_format="HEIF",
                shooting_mode="M",
                configured_hlg_still="On",
                reported_hlg_still="On",
                reported_picture_profile_locked=True,
                reported_creative_look_locked=False,
                reported_dro_locked=True,
                reported_dro_bracket_locked=True,
                reported_hlg_iso_bounds_shifted=True,
                reported_effective_color_space="BT.2100",
            )
        )
        self.assertFalse(rep_lock.passed)
        self.assertEqual(rep_lock.block_code, P292_BLOCKED_HLG_STILL_PREREQ_OR_LOCKOUT_DRIFT)

        # Bypass under RAW & HEIF
        rep_prereq = evaluate_still_image_quality_hlg_colorspace_filename_vault(
            StillImageQualityHlgColorspaceFilenameVaultSpec(
                jpeg_heif_switch="HEIF(4:2:0)",
                file_format="RAW & HEIF",
                shooting_mode="M",
                configured_hlg_still="On",
                reported_hlg_still="On",
                reported_picture_profile_locked=True,
                reported_creative_look_locked=True,
                reported_dro_locked=True,
                reported_dro_bracket_locked=True,
                reported_hlg_iso_bounds_shifted=True,
                reported_effective_color_space="BT.2100",
            )
        )
        self.assertFalse(rep_prereq.passed)
        self.assertEqual(rep_prereq.block_code, P292_BLOCKED_HLG_STILL_PREREQ_OR_LOCKOUT_DRIFT)

    def test_21_pillar51a_adobergb_prepends_leading_underscore_stem(self) -> None:
        rep = evaluate_still_image_quality_hlg_colorspace_filename_vault(
            StillImageQualityHlgColorspaceFilenameVaultSpec(
                jpeg_heif_switch="JPEG",
                file_format="RAW & JPEG",
                configured_color_space="AdobeRGB",
                reported_effective_color_space="AdobeRGB",
                pre_file_name_prefix="DSC",
                post_file_name_prefix="DSC",
                reported_filename_stem="_DSC0001",
            )
        )
        self.assertTrue(rep.passed, rep.errors)

        # Custom 3-char prefix + AdobeRGB -> _FX30001
        rep_fx3 = evaluate_still_image_quality_hlg_colorspace_filename_vault(
            StillImageQualityHlgColorspaceFilenameVaultSpec(
                jpeg_heif_switch="JPEG",
                configured_color_space="AdobeRGB",
                reported_effective_color_space="AdobeRGB",
                pre_file_name_prefix="FX3",
                post_file_name_prefix="FX3",
                reported_filename_stem="_FX30001",
            )
        )
        self.assertTrue(rep_fx3.passed, rep_fx3.errors)

    def test_22_pillar51a_adobergb_stem_without_underscore_rejected(self) -> None:
        rep = evaluate_still_image_quality_hlg_colorspace_filename_vault(
            StillImageQualityHlgColorspaceFilenameVaultSpec(
                jpeg_heif_switch="JPEG",
                configured_color_space="AdobeRGB",
                reported_effective_color_space="AdobeRGB",
                reported_filename_stem="DSC00001",
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P292_BLOCKED_COLORSPACE_ADOBERGB_OR_PREFIX_VIOLATION)

    def test_23_pillar51a_heif_ignores_adobergb_and_uses_srgb_or_bt2100(self) -> None:
        # HEIF + HLG Off -> sRGB + DSC00001 even if configured_color_space=AdobeRGB
        rep_off = evaluate_still_image_quality_hlg_colorspace_filename_vault(
            StillImageQualityHlgColorspaceFilenameVaultSpec(
                jpeg_heif_switch="HEIF(4:2:0)",
                file_format="HEIF",
                configured_hlg_still="Off",
                reported_hlg_still="Off",
                configured_color_space="AdobeRGB",
                reported_effective_color_space="sRGB",
                reported_filename_stem="DSC00001",
            )
        )
        self.assertTrue(rep_off.passed, rep_off.errors)

    def test_24_pillar51a_set_file_name_prefix_validation_forbids_leading_underscore(self) -> None:
        for good in ("DSC", "FX3", "A_1", "Z9_", "001"):
            self.assertTrue(is_valid_fx3_still_filename_prefix(good), good)
        for bad in ("_DS", "_A1", "___", "DS", "ABCD", "ab1", "A-1", "A 1", ""):
            self.assertFalse(is_valid_fx3_still_filename_prefix(bad), bad)

        rep_bad = evaluate_still_image_quality_hlg_colorspace_filename_vault(
            StillImageQualityHlgColorspaceFilenameVaultSpec(
                manual_prefix_edit="_FX",
                post_file_name_prefix="_FX",
            )
        )
        self.assertFalse(rep_bad.passed)
        self.assertEqual(rep_bad.block_code, P292_BLOCKED_COLORSPACE_ADOBERGB_OR_PREFIX_VIOLATION)

    def test_25_pillar51a_set_file_name_survives_camera_settings_reset_only_initialize_resets(self) -> None:
        # Survives Camera Settings Reset & Reset Network Set.
        for ra in ("Camera Settings Reset", "Reset Network Set."):
            rep = evaluate_still_image_quality_hlg_colorspace_filename_vault(
                StillImageQualityHlgColorspaceFilenameVaultSpec(
                    pre_file_name_prefix="CAM",
                    reset_action=ra,
                    post_file_name_prefix="CAM",
                    reported_filename_stem="CAM00001",
                )
            )
            self.assertTrue(rep.passed, f"{ra} failed: {rep.errors}")

        # Initialize resets back to DSC
        rep_init = evaluate_still_image_quality_hlg_colorspace_filename_vault(
            StillImageQualityHlgColorspaceFilenameVaultSpec(
                pre_file_name_prefix="CAM",
                reset_action="Initialize",
                post_file_name_prefix="DSC",
                reported_filename_stem="DSC00001",
            )
        )
        self.assertTrue(rep_init.passed, rep_init.errors)

        # Claiming Camera Settings Reset wiped prefix back to DSC must fail
        rep_wipe = evaluate_still_image_quality_hlg_colorspace_filename_vault(
            StillImageQualityHlgColorspaceFilenameVaultSpec(
                pre_file_name_prefix="CAM",
                reset_action="Camera Settings Reset",
                post_file_name_prefix="DSC",
                reported_filename_stem="DSC00001",
            )
        )
        self.assertFalse(rep_wipe.passed)
        self.assertEqual(rep_wipe.block_code, P292_BLOCKED_COLORSPACE_ADOBERGB_OR_PREFIX_VIOLATION)

    def test_26_pillar51a_slot1_firewall_blocks_still_capture_and_sort_recording(self) -> None:
        for spec_bad in (
            StillImageQualityHlgColorspaceFilenameVaultSpec(target_still_write_slot=1),
            StillImageQualityHlgColorspaceFilenameVaultSpec(sort_recording_targets_slot1=True),
            StillImageQualityHlgColorspaceFilenameVaultSpec(
                requested_vault_slot=1,
                requested_vault_action="STILL_CAPTURE_WRITE",
            ),
            StillImageQualityHlgColorspaceFilenameVaultSpec(
                requested_vault_slot=1,
                requested_vault_action="SORT_RECORDING_WRITE",
            ),
            StillImageQualityHlgColorspaceFilenameVaultSpec(
                requested_vault_slot=1,
                requested_vault_action="FORMAT_QUICK",
            ),
        ):
            rep = evaluate_still_image_quality_hlg_colorspace_filename_vault(spec_bad)
            self.assertFalse(rep.passed)
            self.assertEqual(rep.block_code, P292_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL)
            self.assertEqual(rep.slot1_still_capture_or_sort_write_bytes, 4096)
            self.assertEqual(rep.physical_device_writes, 0)

    def test_27_pillar51a_persistent_overlay_escape_rejected(self) -> None:
        rep = evaluate_still_image_quality_hlg_colorspace_filename_vault(
            StillImageQualityHlgColorspaceFilenameVaultSpec(overlay_dir="/setting/51a")
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P292_BLOCKED_PERSISTENT_OVERLAY_ESCAPE)

        rep_blk = evaluate_still_image_quality_hlg_colorspace_filename_vault(
            StillImageQualityHlgColorspaceFilenameVaultSpec(p2_blkroset_locked=False)
        )
        self.assertFalse(rep_blk.passed)
        self.assertEqual(rep_blk.block_code, P292_BLOCKED_PERSISTENT_OVERLAY_ESCAPE)

    def test_28_pillar51a_tier0_backup_bin_h0_h3_drift_rejected(self) -> None:
        rep = evaluate_still_image_quality_hlg_colorspace_filename_vault(
            StillImageQualityHlgColorspaceFilenameVaultSpec(
                backup_bin_h3_sha256="f" * 64,
                tier0_surfaces_h0_h3_matched=15,
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P292_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT)

    def test_29_pillar51a_persistent_write_unlock_requested_blocked(self) -> None:
        rep = evaluate_still_image_quality_hlg_colorspace_filename_vault(
            StillImageQualityHlgColorspaceFilenameVaultSpec(persistent_write_unlock_requested=True)
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P292_BLOCKED_SAFETY_POLICY_VIOLATION)

    def test_30_pillar51a_invalid_enum_or_menu_path_rejected(self) -> None:
        rep = evaluate_still_image_quality_hlg_colorspace_filename_vault(
            StillImageQualityHlgColorspaceFilenameVaultSpec(jpeg_heif_switch="HEIF(4:4:4)")
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P292_BLOCKED_INVALID_PILLAR51A_SPEC)

    def test_31_pillar51a_6_scenario_suite_passes_6_of_6(self) -> None:
        suite = run_pillar51a_raw_heif_hlg_colorspace_6_scenario_suite()
        self.assertTrue(suite.passed)
        self.assertEqual(suite.status, P292_STATUS_VERIFIED_PILLAR_51A)
        self.assertEqual(suite.scenarios_passed, 6)
        self.assertEqual(suite.scenarios_total, 6)
        self.assertTrue(all(o.passed for o in suite.scenarios))
        self.assertEqual(sum(1 for o in suite.scenarios if o.expected_allowed), 2)
        self.assertEqual(sum(1 for o in suite.scenarios if not o.expected_allowed), 4)

    def test_32_pillar51a_none_spec_defaults_to_safe(self) -> None:
        rep = evaluate_still_image_quality_hlg_colorspace_filename_vault(None)
        self.assertTrue(rep.passed)
        self.assertGreaterEqual(rep.matrix_states_checked, 60)

    # ------------------------------------------------------------------
    # 4. Pillar 51B — Shutter Type 2-Opt, 5-Lock, NR, 10fps Drive & Vault (33..55)
    # ------------------------------------------------------------------

    def test_33_pillar51b_default_safe_passes(self) -> None:
        rep = evaluate_shutter_type_nr_drive_vault()
        self.assertTrue(rep.passed, rep.errors)
        self.assertEqual(rep.status, P292_STATUS_VERIFIED_PILLAR_51B)
        self.assertIsNone(rep.block_code)
        self.assertGreaterEqual(rep.matrix_states_checked, 48)
        self.assertEqual(rep.shutter_type_auto_spoof_events, 0)
        self.assertEqual(rep.slot1_imagedb_or_burst_mutation_bytes, 0)

    def test_34_pillar51b_shutter_type_auto_spoof_rejected_fail_closed(self) -> None:
        rep_auto = evaluate_shutter_type_nr_drive_vault(
            ShutterTypeNrDriveVaultSpec(configured_shutter_type="Auto")
        )
        self.assertFalse(rep_auto.passed)
        self.assertEqual(rep_auto.block_code, P292_BLOCKED_SHUTTER_TYPE_AUTO_OR_FX6_CONFLATION)
        self.assertGreaterEqual(rep_auto.shutter_type_auto_spoof_events, 1)

        rep_flag = evaluate_shutter_type_nr_drive_vault(
            ShutterTypeNrDriveVaultSpec(fx3_ui_exposes_shutter_type_auto=True)
        )
        self.assertFalse(rep_flag.passed)
        self.assertEqual(rep_flag.block_code, P292_BLOCKED_SHUTTER_TYPE_AUTO_OR_FX6_CONFLATION)

    def test_35_pillar51b_fx6_mechanical_shutter_conflation_rejected(self) -> None:
        rep = evaluate_shutter_type_nr_drive_vault(
            ShutterTypeNrDriveVaultSpec(
                shutter_surface_model="FX6_NO_MECHANICAL_SHUTTER_PIPELINE",
                fx6_mechanical_shutter_present=True,
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P292_BLOCKED_SHUTTER_TYPE_AUTO_OR_FX6_CONFLATION)
        self.assertGreaterEqual(rep.fx6_mechanical_shutter_conflation_events, 1)

    def test_36_pillar51b_electronic_shutter_forces_all_5_locks_in_pasm(self) -> None:
        for mode in ("P", "A", "S", "M"):
            rep = evaluate_shutter_type_nr_drive_vault(
                ShutterTypeNrDriveVaultSpec(
                    shooting_mode=mode,
                    configured_shutter_type="Electronic Shutter",
                    reported_shutter_type="Electronic Shutter",
                    reported_flash_allowed=False,
                    reported_long_exposure_nr_allowed=False,
                    reported_e_front_curtain_allowed=False,
                    reported_bulb_allowed=False,
                    reported_anti_flicker_allowed=False,
                    reported_long_exposure_nr="Off",
                )
            )
            self.assertTrue(rep.passed, f"Electronic Shutter in {mode} failed: {rep.errors}")

    def test_37_pillar51b_electronic_shutter_not_selectable_in_intelligent_auto(self) -> None:
        sh_valid, eff, locks, fl_ok, _ = compute_expected_shutter_type_and_5lock_matrix(
            configured_shutter_type="Electronic Shutter",
            shooting_mode="Intelligent Auto",
            silent_mode="Off",
            silent_mode_target_override_shutter=False,
            pre_e_front_curtain="On",
            reset_action="None",
        )
        self.assertTrue(sh_valid)
        self.assertEqual(eff, "Mechanical Shutter")
        self.assertEqual(locks, ())
        self.assertTrue(fl_ok)

    def test_38_pillar51b_silent_mode_forces_electronic_unless_target_override(self) -> None:
        # Silent Mode = On without override -> Electronic Shutter + 5 locks
        rep_sil = evaluate_shutter_type_nr_drive_vault(
            ShutterTypeNrDriveVaultSpec(
                configured_shutter_type="Mechanical Shutter",
                silent_mode="On",
                silent_mode_target_override_shutter=False,
                reported_shutter_type="Electronic Shutter",
                reported_flash_allowed=False,
                reported_long_exposure_nr_allowed=False,
                reported_e_front_curtain_allowed=False,
                reported_bulb_allowed=False,
                reported_anti_flicker_allowed=False,
                reported_long_exposure_nr="Off",
            )
        )
        self.assertTrue(rep_sil.passed, rep_sil.errors)

        # Silent Mode = On WITH Target Function override -> Mechanical Shutter allowed
        rep_ovr = evaluate_shutter_type_nr_drive_vault(
            ShutterTypeNrDriveVaultSpec(
                configured_shutter_type="Mechanical Shutter",
                silent_mode="On",
                silent_mode_target_override_shutter=True,
                reported_shutter_type="Mechanical Shutter",
                reported_flash_allowed=True,
                reported_long_exposure_nr_allowed=True,
                reported_e_front_curtain_allowed=True,
                reported_bulb_allowed=True,
                reported_anti_flicker_allowed=True,
                reported_long_exposure_nr="On",
            )
        )
        self.assertTrue(rep_ovr.passed, rep_ovr.errors)

    def test_39_pillar51b_bypassing_any_of_5_electronic_silent_locks_rejected(self) -> None:
        for field in (
            "reported_flash_allowed",
            "reported_long_exposure_nr_allowed",
            "reported_e_front_curtain_allowed",
            "reported_bulb_allowed",
            "reported_anti_flicker_allowed",
        ):
            kw = {
                "configured_shutter_type": "Electronic Shutter",
                "reported_shutter_type": "Electronic Shutter",
                "reported_flash_allowed": False,
                "reported_long_exposure_nr_allowed": False,
                "reported_e_front_curtain_allowed": False,
                "reported_bulb_allowed": False,
                "reported_anti_flicker_allowed": False,
                "reported_long_exposure_nr": "Off",
                field: True,
            }
            rep = evaluate_shutter_type_nr_drive_vault(ShutterTypeNrDriveVaultSpec(**kw))
            self.assertFalse(rep.passed, f"{field}=True should fail")
            self.assertEqual(rep.block_code, P292_BLOCKED_ELECTRONIC_SILENT_5LOCK_BYPASS)

    def test_40_pillar51b_flash_sync_1_250s_only_enforced(self) -> None:
        for bad_denom in (200, 320, 500):
            rep = evaluate_shutter_type_nr_drive_vault(
                ShutterTypeNrDriveVaultSpec(flash_sync_speed_denom=bad_denom)
            )
            self.assertFalse(rep.passed)
            self.assertEqual(rep.block_code, P292_BLOCKED_ELECTRONIC_SILENT_5LOCK_BYPASS)

    def test_41_pillar51b_e_front_curtain_survives_camera_reset_only_initialize_resets(self) -> None:
        for ra in ("Camera Settings Reset", "Reset Network Set."):
            rep = evaluate_shutter_type_nr_drive_vault(
                ShutterTypeNrDriveVaultSpec(
                    pre_e_front_curtain="Off",
                    reset_action=ra,
                    post_e_front_curtain="Off",
                )
            )
            self.assertTrue(rep.passed, f"{ra} failed: {rep.errors}")

        rep_init = evaluate_shutter_type_nr_drive_vault(
            ShutterTypeNrDriveVaultSpec(
                pre_e_front_curtain="Off",
                reset_action="Initialize",
                post_e_front_curtain="On",
            )
        )
        self.assertTrue(rep_init.passed, rep_init.errors)

        rep_drift = evaluate_shutter_type_nr_drive_vault(
            ShutterTypeNrDriveVaultSpec(
                pre_e_front_curtain="Off",
                reset_action="Camera Settings Reset",
                post_e_front_curtain="On",
            )
        )
        self.assertFalse(rep_drift.passed)
        self.assertEqual(rep_drift.block_code, P292_BLOCKED_ELECTRONIC_SILENT_5LOCK_BYPASS)

    def test_42_pillar51b_long_exposure_nr_1s_threshold_and_lockouts(self) -> None:
        # >= 1.0 s or BULB blocks next shot with equal-duration dark frame
        for ss, bulb in ((1.0, False), (30.0, False), (0.01, True)):
            rep = evaluate_shutter_type_nr_drive_vault(
                ShutterTypeNrDriveVaultSpec(
                    shutter_speed_sec=ss,
                    is_bulb=bulb,
                    reported_long_nr_blocks_next=True,
                )
            )
            self.assertTrue(rep.passed, f"ss={ss}, bulb={bulb} failed: {rep.errors}")

        # Cont. Shooting & Cont. Bracket force Long Exposure NR Off
        for dm in ("Cont. Shooting", "Cont. Bracket"):
            rep_dm = evaluate_shutter_type_nr_drive_vault(
                ShutterTypeNrDriveVaultSpec(
                    drive_mode=dm,
                    cont_shooting_speed="Mid",
                    configured_long_exposure_nr="On",
                    reported_long_exposure_nr="Off",
                    reported_eff_burst_fps=6 if dm == "Cont. Shooting" else 1,
                    reported_long_nr_blocks_next=False,
                )
            )
            self.assertTrue(rep_dm.passed, f"{dm} failed: {rep_dm.errors}")

        # Intelligent Auto forces Long Exposure NR On even if configured Off
        rep_ia = evaluate_shutter_type_nr_drive_vault(
            ShutterTypeNrDriveVaultSpec(
                shooting_mode="Intelligent Auto",
                configured_long_exposure_nr="Off",
                reported_long_exposure_nr="On",
                configured_high_iso_nr="Off",
                reported_high_iso_nr="Normal",
            )
        )
        self.assertTrue(rep_ia.passed, rep_ia.errors)

    def test_43_pillar51b_high_iso_nr_unavailable_in_raw_only_and_allowed_in_hybrid(self) -> None:
        # RAW only -> Unavailable
        rep_raw_ok = evaluate_shutter_type_nr_drive_vault(
            ShutterTypeNrDriveVaultSpec(
                file_format="RAW",
                configured_high_iso_nr="Normal",
                reported_high_iso_nr="Unavailable",
            )
        )
        self.assertTrue(rep_raw_ok.passed, rep_raw_ok.errors)

        rep_raw_bad = evaluate_shutter_type_nr_drive_vault(
            ShutterTypeNrDriveVaultSpec(
                file_format="RAW",
                configured_high_iso_nr="Low",
                reported_high_iso_nr="Low",
            )
        )
        self.assertFalse(rep_raw_bad.passed)
        self.assertEqual(rep_raw_bad.block_code, P292_BLOCKED_NR_OR_DRIVE_BURST_WALL_VIOLATION)

        # RAW & JPEG / RAW & HEIF / JPEG / HEIF allow Normal/Low/Off (applies to JPEG/HEIF only)
        for ff in ("JPEG", "HEIF", "RAW & JPEG", "RAW & HEIF"):
            for nr in P292_HIGH_ISO_NR_MODES:
                rep_hyb = evaluate_shutter_type_nr_drive_vault(
                    ShutterTypeNrDriveVaultSpec(
                        file_format=ff,
                        configured_high_iso_nr=nr,
                        reported_high_iso_nr=nr,
                    )
                )
                self.assertTrue(rep_hyb.passed, f"{ff}/{nr} failed: {rep_hyb.errors}")

    def test_44_pillar51b_drive_mode_all_8_modes_and_speeds(self) -> None:
        for dm in P292_DRIVE_8_MODES:
            is_cont = dm == "Cont. Shooting"
            is_cb = dm == "Cont. Bracket"
            rep = evaluate_shutter_type_nr_drive_vault(
                ShutterTypeNrDriveVaultSpec(
                    drive_mode=dm,
                    cont_shooting_speed="Hi",
                    reported_eff_burst_fps=8 if is_cont else 1,
                    reported_long_exposure_nr="Off" if (is_cont or is_cb) else "On",
                )
            )
            self.assertTrue(rep.passed, f"Drive mode {dm} failed: {rep.errors}")

        for spd, fps in P292_CONT_SHOOTING_FPS_MAP.items():
            rep_s = evaluate_shutter_type_nr_drive_vault(
                ShutterTypeNrDriveVaultSpec(
                    file_format="RAW",
                    raw_file_type="Compressed",
                    configured_high_iso_nr="Normal",
                    reported_high_iso_nr="Unavailable",
                    drive_mode="Cont. Shooting",
                    cont_shooting_speed=spd,
                    reported_long_exposure_nr="Off",
                    reported_eff_burst_fps=fps,
                    reported_hi_plus_live_monitor=(spd != "Hi+"),
                )
            )
            self.assertTrue(rep_s.passed, f"Speed {spd} failed: {rep_s.errors}")

    def test_45_pillar51b_hi_plus_10fps_drops_on_uncompressed_raw_or_flash(self) -> None:
        # Uncompressed RAW drops below 10 fps
        res_uncomp = compute_expected_nr_and_drive_mode_boundaries(
            shooting_mode="M",
            file_format="RAW",
            raw_file_type="Uncompressed",
            eff_hlg_still="Off",
            electronic_or_silent_locks_active=False,
            configured_long_exposure_nr="On",
            configured_high_iso_nr="Normal",
            drive_mode="Cont. Shooting",
            cont_shooting_speed="Hi+",
            flash_fired=False,
            aperture_f_number=2.8,
            shutter_speed_sec=0.01,
            is_bulb=False,
        )
        self.assertLess(res_uncomp[5], 10)

        # Flash fired drops below 10 fps
        res_flash = compute_expected_nr_and_drive_mode_boundaries(
            shooting_mode="M",
            file_format="JPEG",
            raw_file_type="Compressed",
            eff_hlg_still="Off",
            electronic_or_silent_locks_active=False,
            configured_long_exposure_nr="On",
            configured_high_iso_nr="Normal",
            drive_mode="Cont. Shooting",
            cont_shooting_speed="Hi+",
            flash_fired=True,
            aperture_f_number=2.8,
            shutter_speed_sec=0.01,
            is_bulb=False,
        )
        self.assertLess(res_flash[5], 10)

        # Claiming 10 fps on Uncompressed RAW rejected
        rep_bad = evaluate_shutter_type_nr_drive_vault(
            ShutterTypeNrDriveVaultSpec(
                file_format="RAW",
                raw_file_type="Uncompressed",
                reported_high_iso_nr="Unavailable",
                drive_mode="Cont. Shooting",
                cont_shooting_speed="Hi+",
                reported_long_exposure_nr="Off",
                reported_eff_burst_fps=10,
                reported_hi_plus_live_monitor=False,
            )
        )
        self.assertFalse(rep_bad.passed)
        self.assertEqual(rep_bad.block_code, P292_BLOCKED_NR_OR_DRIVE_BURST_WALL_VIOLATION)

    def test_46_pillar51b_f_gt_f11_af_lock_and_hi_plus_non_live_monitor(self) -> None:
        # At F11 -> NOT AF locked
        rep_f11 = evaluate_shutter_type_nr_drive_vault(
            ShutterTypeNrDriveVaultSpec(
                drive_mode="Cont. Shooting",
                cont_shooting_speed="Hi",
                aperture_f_number=11.0,
                reported_long_exposure_nr="Off",
                reported_eff_burst_fps=8,
                reported_af_locked_first_frame=False,
            )
        )
        self.assertTrue(rep_f11.passed, rep_f11.errors)

        # At F14 in Hi+/Hi/Mid -> AF locked to 1st shot; Lo -> NOT locked
        for spd in ("Hi+", "Hi", "Mid"):
            rep_lock = evaluate_shutter_type_nr_drive_vault(
                ShutterTypeNrDriveVaultSpec(
                    drive_mode="Cont. Shooting",
                    cont_shooting_speed=spd,
                    aperture_f_number=14.0,
                    reported_long_exposure_nr="Off",
                    reported_eff_burst_fps=P292_CONT_SHOOTING_FPS_MAP[spd],
                    reported_hi_plus_live_monitor=(spd != "Hi+"),
                    reported_af_locked_first_frame=True,
                )
            )
            self.assertTrue(rep_lock.passed, f"{spd} @ F14 failed: {rep_lock.errors}")

        rep_lo = evaluate_shutter_type_nr_drive_vault(
            ShutterTypeNrDriveVaultSpec(
                drive_mode="Cont. Shooting",
                cont_shooting_speed="Lo",
                aperture_f_number=16.0,
                reported_long_exposure_nr="Off",
                reported_eff_burst_fps=3,
                reported_af_locked_first_frame=False,
            )
        )
        self.assertTrue(rep_lo.passed, rep_lo.errors)

    def test_47_pillar51b_dro_bracket_blocked_when_hlg_still_on(self) -> None:
        rep_ok = evaluate_shutter_type_nr_drive_vault(
            ShutterTypeNrDriveVaultSpec(
                eff_hlg_still="On",
                reported_dro_bracket_allowed=False,
            )
        )
        self.assertTrue(rep_ok.passed, rep_ok.errors)

        rep_bad = evaluate_shutter_type_nr_drive_vault(
            ShutterTypeNrDriveVaultSpec(
                eff_hlg_still="On",
                reported_dro_bracket_allowed=True,
            )
        )
        self.assertFalse(rep_bad.passed)
        self.assertEqual(rep_bad.block_code, P292_BLOCKED_NR_OR_DRIVE_BURST_WALL_VIOLATION)

    def test_48_pillar51b_slot1_burst_bracket_imagedb_firewall(self) -> None:
        for spec_bad in (
            ShutterTypeNrDriveVaultSpec(target_burst_bracket_slot=1),
            ShutterTypeNrDriveVaultSpec(avf_info_imagedb_targets_slot1=True),
            ShutterTypeNrDriveVaultSpec(
                requested_vault_slot=1,
                requested_vault_action="BURST_BRACKET_DCIM_WRITE",
            ),
            ShutterTypeNrDriveVaultSpec(
                requested_vault_slot=1,
                requested_vault_action="AVF_INFO_IMAGEDB_MUTATION",
            ),
            ShutterTypeNrDriveVaultSpec(
                requested_vault_slot=1,
                requested_vault_action="FORMAT_FULL",
            ),
            ShutterTypeNrDriveVaultSpec(
                requested_vault_slot=1,
                requested_vault_action="DELETE_SINGLE",
            ),
        ):
            rep = evaluate_shutter_type_nr_drive_vault(spec_bad)
            self.assertFalse(rep.passed)
            self.assertEqual(rep.block_code, P292_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL)
            self.assertEqual(rep.slot1_imagedb_or_burst_mutation_bytes, 4096)
            self.assertEqual(rep.physical_device_writes, 0)

    def test_49_pillar51b_slot1_unprotected_wp_or_format_lock_rejected(self) -> None:
        rep = evaluate_shutter_type_nr_drive_vault(
            ShutterTypeNrDriveVaultSpec(
                slot1_sdxc_wp_locked=False,
                slot1_format_hard_locked=False,
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P292_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL)

    def test_50_pillar51b_overlay_escape_and_h0_h3_drift_rejected(self) -> None:
        rep_ov = evaluate_shutter_type_nr_drive_vault(
            ShutterTypeNrDriveVaultSpec(overlay_dir="/dev/mmcblk0")
        )
        self.assertFalse(rep_ov.passed)
        self.assertEqual(rep_ov.block_code, P292_BLOCKED_PERSISTENT_OVERLAY_ESCAPE)

        rep_h3 = evaluate_shutter_type_nr_drive_vault(
            ShutterTypeNrDriveVaultSpec(
                backup_bin_h3_sha256="a" * 64,
                tier0_surfaces_h0_h3_matched=14,
            )
        )
        self.assertFalse(rep_h3.passed)
        self.assertEqual(rep_h3.block_code, P292_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT)

    def test_51_pillar51b_invalid_enum_spec_rejected(self) -> None:
        rep = evaluate_shutter_type_nr_drive_vault(
            ShutterTypeNrDriveVaultSpec(drive_mode="Pixel Shift Multi Shoot")
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P292_BLOCKED_INVALID_PILLAR51B_SPEC)

    def test_52_pillar51b_persistent_write_unlock_requested_blocked(self) -> None:
        rep = evaluate_shutter_type_nr_drive_vault(
            ShutterTypeNrDriveVaultSpec(persistent_write_unlock_requested=True)
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P292_BLOCKED_SAFETY_POLICY_VIOLATION)

    def test_53_pillar51b_6_scenario_suite_passes_6_of_6(self) -> None:
        suite = run_pillar51b_shuttertype_nr_drive_6_scenario_suite()
        self.assertTrue(suite.passed)
        self.assertEqual(suite.status, P292_STATUS_VERIFIED_PILLAR_51B)
        self.assertEqual(suite.scenarios_passed, 6)
        self.assertEqual(suite.scenarios_total, 6)
        self.assertTrue(all(o.passed for o in suite.scenarios))
        self.assertEqual(sum(1 for o in suite.scenarios if o.expected_allowed), 2)
        self.assertEqual(sum(1 for o in suite.scenarios if not o.expected_allowed), 4)

    def test_54_pillar51b_none_spec_defaults_to_safe(self) -> None:
        rep = evaluate_shutter_type_nr_drive_vault(None)
        self.assertTrue(rep.passed)
        self.assertGreaterEqual(rep.matrix_states_checked, 48)

    def test_55_pillar51_supported_fw_versions_include_200_through_702(self) -> None:
        for fw in ("2.00", "3.00", "4.00", "5.00", "6.00", "6.02", "7.00", "7.01", "7.02"):
            ra = evaluate_still_image_quality_hlg_colorspace_filename_vault(
                StillImageQualityHlgColorspaceFilenameVaultSpec(fw_version=fw)
            )
            rb = evaluate_shutter_type_nr_drive_vault(ShutterTypeNrDriveVaultSpec(fw_version=fw))
            self.assertTrue(ra.passed, f"51A fw {fw} failed")
            self.assertTrue(rb.passed, f"51B fw {fw} failed")

    # ------------------------------------------------------------------
    # 5. Pillar 51 Combined & Standalone Suite + Tamper Propagation (56..63)
    # ------------------------------------------------------------------

    def test_56_combined_verify_function_and_symmetry_alias_clean_room(self) -> None:
        r1 = verify_raw_heif_colorspace_shuttertype_nr_drive_and_vault(force_clean_room=True)
        r2 = verify_raw_heif_colorspace_shuttertype_nr_drive_vault(force_clean_room=True)
        self.assertTrue(r1.all_passed)
        self.assertTrue(r2.all_passed)
        self.assertEqual(r1.status, P292_STATUS_VERIFIED_PILLAR51_SUITE)
        self.assertEqual(r1.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(
            r1.still_quality_hlg_colorspace_report.digest_sha256,
            r2.still_quality_hlg_colorspace_report.digest_sha256,
        )
        self.assertEqual(
            r1.shutter_type_nr_drive_report.digest_sha256,
            r2.shutter_type_nr_drive_report.digest_sha256,
        )
        self.assertEqual(r1.raw_firmware_bytes_leaked, 0)

    def test_57_standalone_suite_clean_room_and_active_modes(self) -> None:
        st_cr = run_pillar51_standalone_suite(force_clean_room=True)
        self.assertTrue(st_cr.all_passed)
        self.assertEqual(st_cr.status, P292_STATUS_VERIFIED_PILLAR51_SUITE)
        self.assertEqual(st_cr.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(st_cr.pillar_51a_raw_heif_hlg_colorspace_vault.scenarios_passed, 6)
        self.assertEqual(st_cr.pillar_51b_shuttertype_nr_drive_vault.scenarios_passed, 6)
        self.assertTrue(st_cr.slot1_format_hard_locked)
        self.assertTrue(st_cr.slot1_vault_erofs_ebusy_enforced)
        self.assertEqual(st_cr.slot1_vault_mutation_bytes, 0)
        self.assertEqual(st_cr.raw_firmware_bytes_leaked, 0)

        st_act = run_pillar51_standalone_suite()
        self.assertTrue(st_act.all_passed)
        self.assertEqual(st_act.status, P292_STATUS_VERIFIED_PILLAR51_SUITE)

    def test_58_donor_failure_propagates_to_pillar51_standalone_and_combined(self) -> None:
        bad_snap = inspect_phase292_donors_readonly(force_clean_room=True)
        bad_snap = replace(bad_snap, all_donors_present=False, under_0_20s_budget=False)
        with mock.patch.object(p292, "inspect_phase292_donors_readonly", return_value=bad_snap):
            st = run_pillar51_standalone_suite(force_clean_room=True)
            self.assertFalse(st.all_passed)
            self.assertEqual(st.status, P292_STATUS_FAIL_PILLAR51_SUITE)
            self.assertTrue(any("donor" in e.lower() for e in st.errors))

            comb = verify_raw_heif_colorspace_shuttertype_nr_drive_and_vault(force_clean_room=True)
            self.assertFalse(comb.all_passed)
            self.assertEqual(comb.status, P292_STATUS_FAIL_PILLAR51_SUITE)

    def test_59_safety_tamper_blocks_both_51a_and_51b(self) -> None:
        with mock.patch.object(p292, "PHYSICAL_DEVICE_WRITES", 1):
            errs = p292._safety_invariant_errors()
            self.assertTrue(any("PHYSICAL_DEVICE_WRITES" in e for e in errs))
            r51a = evaluate_still_image_quality_hlg_colorspace_filename_vault()
            self.assertFalse(r51a.passed)
            self.assertEqual(r51a.block_code, P292_BLOCKED_SAFETY_POLICY_VIOLATION)
            r51b = evaluate_shutter_type_nr_drive_vault()
            self.assertFalse(r51b.passed)
            self.assertEqual(r51b.block_code, P292_BLOCKED_SAFETY_POLICY_VIOLATION)

    def test_60_p292_standalone_json_roundtrip_strict_allow_nan_false(self) -> None:
        st = run_pillar51_standalone_suite(force_clean_room=True)
        dumped = json.dumps(st.to_dict(), ensure_ascii=False, sort_keys=True, allow_nan=False)
        parsed = json.loads(dumped)
        self.assertEqual(parsed["schema"], PHASE292_SCHEMA)
        self.assertTrue(parsed["all_passed"])
        self.assertEqual(parsed["raw_firmware_bytes_leaked"], 0)

    # ------------------------------------------------------------------
    # 6. Unified 51/51 Recovery Master Aggregator (61..72)
    # ------------------------------------------------------------------

    def test_61_master_51pillar_clean_room_passes_51_of_51(self) -> None:
        rep = evaluate_realhw_51pillar_recovery_master(force_clean_room=True)
        self.assertTrue(rep.all_passed, rep.errors)
        self.assertEqual(rep.status, P292_STATUS_VERIFIED_51OF51_AGGREGATOR)
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertGreaterEqual(rep.pillar_count, 51)
        self.assertEqual(rep.pillars_passed, rep.pillar_count)
        self.assertEqual(rep.failed_pillars, ())
        self.assertEqual(len(rep.pillars), rep.pillar_count)
        self.assertTrue(rep.under_6s_budget)
        self.assertTrue(rep.nominal_under_4_0s)
        ceiling = 15.0 if _is_ci() else P292_FAST_CLI_BUDGET_SECONDS
        self.assertLess(rep.elapsed_seconds, ceiling)
        if not _is_ci():
            self.assertTrue(rep.under_1_2s_fast_cli_budget)
            self.assertTrue(rep.under_2_5s_fast_cli_budget)

    def test_62_master_51pillar_active_mode_passes_and_under_budget(self) -> None:
        rep = evaluate_realhw_51pillar_recovery_master()
        self.assertTrue(rep.all_passed, rep.errors)
        self.assertEqual(rep.status, P292_STATUS_VERIFIED_51OF51_AGGREGATOR)
        self.assertGreaterEqual(rep.pillar_count, 51)
        self.assertEqual(rep.pillars_passed, rep.pillar_count)
        self.assertEqual(rep.failed_pillars, ())
        ceiling = 15.0 if _is_ci() else 2.5
        self.assertLess(rep.elapsed_seconds, ceiling)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)
        self.assertEqual(rep.physical_device_writes, 0)
        self.assertFalse(rep.hardware_live_attachment_authorized)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.persistent_emmc_writes_authorized)

    def test_63_master_51pillar_aliases_consistent(self) -> None:
        r1 = evaluate_realhw_51pillar_recovery_master(force_clean_room=True)
        r2 = evaluate_51pillar_recovery_master(force_clean_room=True)
        r3 = verify_51pillar_recovery_suite(force_clean_room=True)
        self.assertEqual(r1.master_51pillar_sha256, r2.master_51pillar_sha256)
        self.assertEqual(r2.master_51pillar_sha256, r3.master_51pillar_sha256)
        self.assertGreaterEqual(r1.pillars_passed, 51)

    def test_64_master_51pillar_preserves_all_upstream_safety_and_reality_metrics(self) -> None:
        rep = evaluate_realhw_51pillar_recovery_master(force_clean_room=True)
        # Pillar 51 counters
        self.assertEqual(rep.dormant_lossless_raw_exposure_events, 0)
        self.assertEqual(rep.fx6_still_pipeline_conflation_events, 0)
        self.assertEqual(rep.hlg_still_prereq_or_lockout_drift_events, 0)
        self.assertEqual(rep.colorspace_adobergb_prefix_violations, 0)
        self.assertEqual(rep.shutter_type_auto_spoof_events, 0)
        self.assertEqual(rep.fx6_mechanical_shutter_conflation_events, 0)
        self.assertEqual(rep.electronic_silent_5lock_bypass_events, 0)
        self.assertEqual(rep.nr_or_drive_burst_wall_violations, 0)
        self.assertEqual(rep.slot1_still_capture_or_sort_write_bytes, 0)
        self.assertEqual(rep.slot1_imagedb_or_burst_mutation_bytes, 0)
        self.assertEqual(rep.slot1_vault_mutation_bytes, 0)
        self.assertTrue(rep.slot1_format_hard_locked)
        self.assertTrue(rep.slot1_vault_erofs_ebusy_enforced)
        self.assertFalse(rep.fx3_ui_exposes_lossless_raw)
        self.assertFalse(rep.fx3_ui_exposes_shutter_type_auto)
        self.assertFalse(rep.fx6_still_pipeline_present)
        self.assertFalse(rep.fx6_mechanical_shutter_present)
        # Pillars 1..50 preserved invariants
        self.assertEqual(rep.double_log_or_lockout_bypass_events, 0)
        self.assertEqual(rep.wb_custom_camset_exclusion_drift_events, 0)
        self.assertFalse(rep.fx3_ui_exposes_usb_streaming)
        self.assertFalse(rep.fx3_ui_exposes_power_save_by_monitor)
        self.assertFalse(rep.fx3_has_builtin_end_filter)
        self.assertFalse(rep.fx3_has_builtin_evf)
        self.assertFalse(rep.fx3_has_var_shutter)
        self.assertGreaterEqual(rep.bodydata_flash_attempts_blocked, 1)
        self.assertTrue(rep.cnflasha_userspace_write_blocked)
        self.assertEqual(rep.otp_fuse_touches, 0)
        self.assertEqual(rep.rpmb_counter_increments, 0)
        self.assertEqual(rep.passive_tx_bytes_emitted, 0)
        self.assertEqual(rep.physical_usb_packets_emitted, 0)
        self.assertEqual(rep.physical_device_writes, 0)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)
        self.assertFalse(rep.el3_payload_transmit_authorized)
        self.assertFalse(rep.isp_write_authorized)
        self.assertFalse(rep.spi_nor_write_authorized)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.overall_ready_for_hardware_attach)

    def test_65_master_51pillar_fault_injection_pillar_51(self) -> None:
        rep = evaluate_realhw_51pillar_recovery_master(
            force_clean_room=True,
            fault_inject_pillar="pillar_51_raw_heif_colorspace_shuttertype_nr_drive_vault",
        )
        self.assertFalse(rep.all_passed)
        self.assertEqual(rep.pillars_passed, rep.pillar_count - 1)
        self.assertEqual(
            rep.failed_pillars,
            ("pillar_51_raw_heif_colorspace_shuttertype_nr_drive_vault",),
        )
        self.assertEqual(rep.status, P292_STATUS_FAIL_51OF51_AGGREGATOR)

    def test_66_master_51pillar_fault_injection_pillar_50_and_pillar_01(self) -> None:
        for pid in (
            MASTER_51_PILLAR_IDS[0],
            "pillar_50_pp_scinetone_creativelook_dro_wb_metering_vault",
        ):
            rep = evaluate_realhw_51pillar_recovery_master(
                force_clean_room=True,
                fault_inject_pillar=pid,
            )
            self.assertFalse(rep.all_passed)
            self.assertEqual(rep.pillars_passed, rep.pillar_count - 1)
            self.assertEqual(rep.failed_pillars, (pid,))

    def test_67_master_51pillar_unknown_fault_inject_pillar_raises(self) -> None:
        with self.assertRaises(ValueError):
            evaluate_realhw_51pillar_recovery_master(
                force_clean_room=True,
                fault_inject_pillar="pillar_999_nonexistent",
            )

    def test_68_master_51pillar_upstream_violation_detected(self) -> None:
        m50 = evaluate_realhw_50pillar_recovery_master(force_clean_room=True)
        bad_m50 = replace(m50, slot1_format_hard_locked=False)
        with mock.patch.object(
            p292,
            "evaluate_realhw_50pillar_recovery_master",
            return_value=bad_m50,
        ):
            rep = evaluate_realhw_51pillar_recovery_master(force_clean_room=True)
            self.assertFalse(rep.all_passed)
            self.assertTrue(any("slot1_format_hard_locked" in e for e in rep.errors))

    def test_69_master_51pillar_p51_violation_detected(self) -> None:
        p51 = run_pillar51_standalone_suite(force_clean_room=True)
        bad_p51 = replace(p51, dormant_lossless_raw_exposure_events=1)
        with mock.patch.object(p292, "run_pillar51_standalone_suite", return_value=bad_p51):
            rep = evaluate_realhw_51pillar_recovery_master(force_clean_room=True)
            self.assertFalse(rep.all_passed)
            self.assertTrue(any("dormant_lossless_raw_exposure_events" in e for e in rep.errors))

    def test_70_master_51pillar_safety_tamper_raises(self) -> None:
        with mock.patch.object(p292, "RAW_FIRMWARE_BYTES_LEAKED", 1):
            with self.assertRaises(ValueError):
                evaluate_realhw_51pillar_recovery_master(force_clean_room=True)

    def test_71_pillar_50_backward_compatibility_still_passes(self) -> None:
        rep50 = evaluate_realhw_50pillar_recovery_master(force_clean_room=True)
        self.assertTrue(rep50.all_passed)
        self.assertGreaterEqual(rep50.pillar_count, 50)
        self.assertEqual(rep50.pillars_passed, rep50.pillar_count)

    def test_72_fx3_recovery_package_exports_all_pillar51_symbols(self) -> None:
        for sym in p292.__all__:
            self.assertTrue(hasattr(fx3_recovery, sym), f"fx3_recovery missing export {sym}")
            self.assertIn(sym, fx3_recovery.__all__, f"fx3_recovery.__all__ missing {sym}")
        self.assertIn(
            "realhw_51pillar_raw_heif_colorspace_shuttertype_nr_drive_vault_verifier",
            fx3_recovery.__all__,
        )

    def test_73_master_51pillar_json_serialization_no_nan(self) -> None:
        rep = evaluate_realhw_51pillar_recovery_master(force_clean_room=True)
        text = json.dumps(rep.to_dict(), ensure_ascii=False, sort_keys=True, allow_nan=False)
        data = json.loads(text)
        self.assertEqual(data["schema"], PHASE292_SCHEMA)
        self.assertGreaterEqual(data["pillar_count"], 51)
        self.assertEqual(data["pillars_passed"], data["pillar_count"])
        self.assertTrue(data["all_passed"])

    # ------------------------------------------------------------------
    # 7. CLI Subcommands & Cross-Platform CI Subprocess Portability (74..80)
    # ------------------------------------------------------------------

    def test_74_cli_standalone_json_clean_room(self) -> None:
        buf = io.StringIO()
        with mock.patch.object(
            sys,
            "argv",
            [
                "fx3_recovery",
                "verify-pillar51-raw-heif-colorspace-shuttertype-vault",
                "--clean-room",
                "--json",
            ],
        ):
            with redirect_stdout(buf):
                rc = cli_main.main()
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())
        self.assertTrue(payload["all_passed"])
        self.assertEqual(payload["status"], P292_STATUS_VERIFIED_PILLAR51_SUITE)
        self.assertEqual(payload["verification_mode"], "CLEAN_ROOM_SYNTHETIC")

    def test_75_cli_51pillar_master_json_clean_room(self) -> None:
        buf = io.StringIO()
        with mock.patch.object(
            sys,
            "argv",
            ["fx3_recovery", "verify-51pillar-recovery", "--clean-room", "--json"],
        ):
            with redirect_stdout(buf):
                rc = cli_main.main()
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())
        self.assertTrue(payload["all_passed"])
        self.assertGreaterEqual(payload["pillar_count"], 51)
        self.assertEqual(payload["pillars_passed"], payload["pillar_count"])
        self.assertEqual(payload["status"], P292_STATUS_VERIFIED_51OF51_AGGREGATOR)

    def test_76_cli_out_dirs_repo_local_cleaned_in_finally(self) -> None:
        work_tests = _repo_root() / "work" / "_tests"
        work_tests.mkdir(parents=True, exist_ok=True)
        out_root = Path(tempfile.mkdtemp(prefix="p292_cli_", dir=str(work_tests)))
        out_master = out_root / "master51"
        out_p51 = out_root / "pillar51"
        try:
            b1 = io.StringIO()
            with mock.patch.object(
                sys,
                "argv",
                ["fx3_recovery", "verify-51pillar-recovery", "--clean-room", "--out", str(out_master), "--json"],
            ):
                with redirect_stdout(b1):
                    rc1 = cli_main.main()
            self.assertEqual(rc1, 0)
            master_file = out_master / "51pillar-recovery-master-report.json"
            self.assertTrue(master_file.is_file())
            written_m = json.loads(master_file.read_text(encoding="utf-8"))
            self.assertGreaterEqual(written_m["pillars_passed"], 51)

            b2 = io.StringIO()
            with mock.patch.object(
                sys,
                "argv",
                [
                    "fx3_recovery",
                    "verify-pillar51-raw-heif-colorspace-shuttertype-vault",
                    "--clean-room",
                    "--out",
                    str(out_p51),
                    "--json",
                ],
            ):
                with redirect_stdout(b2):
                    rc2 = cli_main.main()
            self.assertEqual(rc2, 0)
            p51_file = out_p51 / "pillar51-raw-heif-colorspace-shuttertype-vault-report.json"
            self.assertTrue(p51_file.is_file())
            written_p51 = json.loads(p51_file.read_text(encoding="utf-8"))
            self.assertTrue(written_p51["all_passed"])
        finally:
            shutil.rmtree(out_root, ignore_errors=True)

    def test_77_cli_subprocess_sys_executable_all_modes(self) -> None:
        adapter_dir = _repo_root() / "outputs" / "fx3-recovery-adapter"
        env_base = dict(os.environ)
        env_base["PYTHONDONTWRITEBYTECODE"] = "1"
        env_base["PYTHONPATH"] = str(adapter_dir)

        proc_active = subprocess.run(
            [sys.executable, "-B", "-m", "fx3_recovery", "verify-51pillar-recovery", "--json"],
            cwd=str(_repo_root()),
            env=env_base,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc_active.returncode, 0, proc_active.stderr)
        data_active = json.loads(proc_active.stdout)
        self.assertTrue(data_active["all_passed"])
        self.assertGreaterEqual(data_active["pillars_passed"], 51)

        for env_key in (P292_ENV_CLEAN_ROOM_TEST, "FX3_FX6_FORCE_CLEAN_ROOM"):
            env_clean = dict(env_base)
            env_clean[env_key] = "1"
            proc_clean = subprocess.run(
                [sys.executable, "-B", "-m", "fx3_recovery", "verify-51pillar-recovery", "--json"],
                cwd=str(_repo_root()),
                env=env_clean,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc_clean.returncode, 0, proc_clean.stderr)
            data_clean = json.loads(proc_clean.stdout)
            self.assertEqual(data_clean["verification_mode"], "CLEAN_ROOM_SYNTHETIC")
            self.assertGreaterEqual(data_clean["pillars_passed"], 51)

    def test_78_cli_human_readable_text_output_and_help_portability(self) -> None:
        b1 = io.StringIO()
        with mock.patch.object(
            sys,
            "argv",
            ["fx3_recovery", "verify-pillar51-raw-heif-colorspace-shuttertype-vault", "--clean-room"],
        ):
            with redirect_stdout(b1):
                rc1 = cli_main.main()
        self.assertEqual(rc1, 0)
        t1 = b1.getvalue()
        self.assertIn("pillar_51a=6/6", t1)
        self.assertIn("pillar_51b=6/6", t1)
        self.assertIn("slot1_format_hard_locked=True", t1)

        b2 = io.StringIO()
        with mock.patch.object(
            sys,
            "argv",
            ["fx3_recovery", "verify-51pillar-recovery", "--clean-room"],
        ):
            with redirect_stdout(b2):
                rc2 = cli_main.main()
        self.assertEqual(rc2, 0)
        t2 = b2.getvalue()
        self.assertIn("pillars=", t2)
        self.assertIn("all_passed=True", t2)
        self.assertIn("raw_firmware_bytes_leaked=0", t2)

        adapter_dir = _repo_root() / "outputs" / "fx3-recovery-adapter"
        env_base = dict(os.environ)
        env_base["PYTHONDONTWRITEBYTECODE"] = "1"
        env_base["PYTHONPATH"] = str(adapter_dir)
        for subcmd in (
            "--help",
            "verify-pillar51-raw-heif-colorspace-shuttertype-vault --help",
            "verify-51pillar-recovery --help",
        ):
            proc = subprocess.run(
                [sys.executable, "-B", "-m", "fx3_recovery", *subcmd.split()],
                cwd=str(_repo_root()),
                env=env_base,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_79_cli_returns_nonzero_on_pillar51_and_master_failures(self) -> None:
        failed_st = replace(
            run_pillar51_standalone_suite(force_clean_room=True),
            all_passed=False,
            status=P292_STATUS_FAIL_PILLAR51_SUITE,
        )
        with mock.patch.object(cli_main, "run_pillar51_standalone_suite", return_value=failed_st):
            buf = io.StringIO()
            with mock.patch.object(
                sys,
                "argv",
                [
                    "fx3_recovery",
                    "verify-pillar51-raw-heif-colorspace-shuttertype-vault",
                    "--clean-room",
                    "--json",
                ],
            ):
                with redirect_stdout(buf):
                    rc = cli_main.main()
            self.assertEqual(rc, 2)

        failed_m = replace(
            evaluate_realhw_51pillar_recovery_master(force_clean_room=True),
            all_passed=False,
            status=P292_STATUS_FAIL_51OF51_AGGREGATOR,
        )
        with mock.patch.object(cli_main, "verify_51pillar_recovery_suite", return_value=failed_m):
            buf = io.StringIO()
            with mock.patch.object(
                sys,
                "argv",
                ["fx3_recovery", "verify-51pillar-recovery", "--clean-room", "--json"],
            ):
                with redirect_stdout(buf):
                    rc = cli_main.main()
            self.assertEqual(rc, 2)

    def test_80_no_raw_firmware_bytes_or_usb_tx_anywhere_in_module(self) -> None:
        snap = inspect_phase292_donors_readonly()
        st = run_pillar51_standalone_suite(force_clean_room=True)
        m51 = evaluate_realhw_51pillar_recovery_master(force_clean_room=True)
        self.assertEqual(snap.raw_firmware_bytes_leaked, 0)
        self.assertEqual(st.raw_firmware_bytes_leaked, 0)
        self.assertEqual(m51.raw_firmware_bytes_leaked, 0)
        self.assertEqual(st.passive_tx_bytes_emitted, 0)
        self.assertEqual(m51.passive_tx_bytes_emitted, 0)
        self.assertFalse(m51.overall_ready_for_hardware_attach)
        self.assertFalse(m51.persistent_emmc_writes_authorized)


if __name__ == "__main__":
    unittest.main()
