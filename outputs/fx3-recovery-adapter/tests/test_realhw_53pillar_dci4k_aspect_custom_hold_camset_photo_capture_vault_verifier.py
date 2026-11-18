"""Phase 300 (300th Phase Grand Milestone!!) — Dual-mode unit tests for Pillar 53
(`[XAVC S-I DCI 4K]` `4096x2160` `17:9` All-Intra vs Long-GOP `3840x2160` UHD split,
dormant `8K` lockout, `24.00p` mandatory reboot & volatile `/tmp` Stage-B clean wipe +
playback quarantine, `4264x2408` Type-A HDMI RAW, Still `[Aspect Ratio]` `3:2..1:1` +
`APS-C S35` `L -> M` step-down vs still-less `FX6`; `[Reg. Custom Shoot Set]` Still `P/A/S/M`
`Recall Custom hold 1..3` 11 checkboxes & `HLG Still = Off` lockout, `[Camera Set. Memory]`
`1..3 + M1..M4` `%c:%s/SONY/SETTING/%s/CAMPR%02d%c.DAT` & `CAMSET` isolation vs `FX6`
`PRO/CAMERA` cross-model block, `[Playback] -> [Edit] -> [Photo Capture]` `8.3M/2.1M` DCI 4K
lockout & `Slot-1` Tier-0 Vault `EROFS`/`EBUSY` firewall, read-only `[Enlarge Image]`)
and unified `53/53` recovery master (`verify-53pillar-recovery` /
`verify-pillar53-dci4k-aspect-custom-hold-camset-vault`).
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
    realhw_53pillar_dci4k_aspect_custom_hold_camset_photo_capture_vault_verifier as p300,
)
from fx3_recovery.realhw_52pillar_focus_area_zoom_lever_iso_minss_flash_vault_verifier import (
    evaluate_realhw_52pillar_recovery_master,
)
from fx3_recovery.realhw_53pillar_dci4k_aspect_custom_hold_camset_photo_capture_vault_verifier import (
    ALLOW_BOOT_PARTITION_TARGETING,
    ALLOW_DESTRUCTIVE_FASTBOOT,
    ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS,
    ALLOW_PERSISTENT_JIRITSU_WRITES,
    CNFLASHA_USERSPACE_WRITE_BLOCKED,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    ISP_WRITE_AUTHORIZED,
    LIVE_USB_IOKIT_TRANSMIT_ENABLED,
    MASTER_53_PILLAR_COUNT,
    MASTER_53_PILLAR_IDS,
    MASTER_53_PILLAR_SPECS,
    OTP_FUSE_TOUCHES,
    OTP_FUSE_WRITES,
    OVERALL_READY_FOR_HARDWARE_ATTACH,
    P300_2400P_PLAYBACK_QUARANTINE_G_RESID16,
    P300_2400P_REBOOT_ALT_G_RESID16,
    P300_2400P_REBOOT_G_RESID16,
    P300_2400P_RESID16,
    P300_BLOCKED_2400P_REBOOT_STAGE_B_WIPE_OR_QUARANTINE_DRIFT,
    P300_BLOCKED_CAMSET_CROSS_MODEL_OR_PATH_VIOLATION,
    P300_BLOCKED_DCI4K_LONG_GOP_OR_DORMANT_8K_VIOLATION,
    P300_BLOCKED_HDMI_RAW_OR_STILL_ASPECT_VIOLATION,
    P300_BLOCKED_INVALID_PILLAR53A_SPEC,
    P300_BLOCKED_INVALID_PILLAR53B_SPEC,
    P300_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
    P300_BLOCKED_PHOTO_CAPTURE_DCI4K_LOCKOUT_OR_ENLARGE_DRIFT,
    P300_BLOCKED_REG_CUSTOM_HOLD_OR_HLG_LOCKOUT_DRIFT,
    P300_BLOCKED_SAFETY_POLICY_VIOLATION,
    P300_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL,
    P300_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
    P300_CAMSET_ALL_BANKS,
    P300_CAMSET_BODY_BANKS,
    P300_CAMSET_CARD_BANKS,
    P300_DCI4K_600M_MIN_GRADES,
    P300_DCI4K_ASPECT,
    P300_DCI4K_BITRATE_BY_FPS_MBPS,
    P300_DCI4K_DIMENSIONS,
    P300_DCI4K_REC_FRAME_RATES,
    P300_DCI4K_RESID16,
    P300_DCI4K_SQ_ALLOWED_FPS,
    P300_DCI4K_SQ_LOCKED_OUT_FPS,
    P300_DONOR_INSPECT_BUDGET_SECONDS,
    P300_DONOR_INSPECT_CI_BUDGET_SECONDS,
    P300_DORMANT_8K_FORMAT,
    P300_ENLARGE_INITIAL_MAG_BKID,
    P300_ENLARGE_INITIAL_MAG_DEFAULT,
    P300_ENLARGE_INITIAL_POS_BKID,
    P300_ENLARGE_INITIAL_POS_DEFAULT,
    P300_ENV_CLEAN_ROOM_TEST,
    P300_FAST_CLI_BUDGET_SECONDS,
    P300_FX3_APPFW_HAS_DCI4K_INTERNAL,
    P300_FX3_APPFW_HAS_PRO_CAMERA_PATH,
    P300_FX3_CAMPR_PATH_TEMPLATE,
    P300_FX3_CAMSET_PATH_TEMPLATE,
    P300_FX3_FW_VERSION,
    P300_FX3_HDMI_RAW_DIMENSIONS,
    P300_FX3_HELPGUIDE_ID,
    P300_FX3_MODEL_ID,
    P300_FX3_MODEL_NAME,
    P300_FX3_SENSOR_FAMILY,
    P300_FX3_STILL_RAW_NATIVE_DIMS,
    P300_FX6_DCI4K_SQ_MAX_FPS,
    P300_FX6_HAS_CAMERA_SET_MEMORY,
    P300_FX6_HAS_PHOTO_CAPTURE,
    P300_FX6_HAS_PLAYBACK_ENLARGE_IMAGE,
    P300_FX6_HAS_REG_CUSTOM_SHOOT_SET,
    P300_FX6_HAS_STILL_ASPECT_RATIO,
    P300_FX6_PRO_CAMERA_PATH_PREFIX,
    P300_FX6_RAW_DIMENSIONS,
    P300_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    P300_HD_DIMENSIONS,
    P300_OVERALL_READY_FOR_HARDWARE_ATTACH,
    P300_PHOTO_CAPTURE_4K_UHD_DIMS,
    P300_PHOTO_CAPTURE_4K_UHD_MP,
    P300_PHOTO_CAPTURE_BKID,
    P300_PHOTO_CAPTURE_DCI4K_LOCKOUT_G_RESID16,
    P300_PHOTO_CAPTURE_FILE_TYPES,
    P300_PHOTO_CAPTURE_HD_DIMS,
    P300_PHOTO_CAPTURE_HD_MP,
    P300_PINNED_FX3_APPFW_702_BYTES,
    P300_PINNED_FX3_APPFW_702_HDR4K_SHA256,
    P300_PINNED_FX3_BACKUP_BIN_BYTES,
    P300_PINNED_FX3_BACKUP_BIN_SHA256,
    P300_PINNED_FX3_UXC_EN_F_BYTES,
    P300_PINNED_FX3_UXC_EN_F_SHA256,
    P300_PINNED_FX6_APPFW_601_BYTES,
    P300_PINNED_FX6_APPFW_601_HDR4K_SHA256,
    P300_REG_CUSTOM_HOLD_CHECKBOX_COUNT,
    P300_REG_CUSTOM_HOLD_DEFAULT,
    P300_REG_CUSTOM_SHOOT_SET_11_CHECKBOXES,
    P300_REG_CUSTOM_SHOOT_SET_SLOTS,
    P300_SLOT1_FORMAT_HARD_LOCKED,
    P300_SLOT1_VAULT_EROFS_EBUSY_ENFORCED,
    P300_STATUS_FAIL_53OF53_AGGREGATOR,
    P300_STATUS_FAIL_PILLAR53_SUITE,
    P300_STATUS_VERIFIED_53OF53_AGGREGATOR,
    P300_STATUS_VERIFIED_PILLAR53_SUITE,
    P300_STATUS_VERIFIED_PILLAR_53A,
    P300_STATUS_VERIFIED_PILLAR_53B,
    P300_STILL_ASPECT_BKID,
    P300_STILL_ASPECT_DEFAULT,
    P300_STILL_ASPECT_RATIOS,
    P300_STILL_ASPECT_SIZE_MATRIX,
    P300_UHD_4K_DIMENSIONS,
    P300_UHD_ASPECT,
    PASSIVE_TX_BYTES_EMITTED,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHASE300_PHASE_NUMBER,
    PHASE300_SCHEMA,
    PHASE300_VERSION,
    PHYSICAL_DEVICE_WRITES,
    PHYSICAL_USB_PACKETS_EMITTED,
    RAW_FIRMWARE_BYTES_LEAKED,
    READ_ONLY_DONOR_ACCESS,
    RPMB_COUNTER_INCREMENTS,
    SPI_NOR_WRITE_AUTHORIZED,
    build_default_safe_dci4k_2400p_hdmi_raw_still_aspect_vault_spec,
    build_default_safe_reg_custom_hold_camset_photo_capture_vault_spec,
    build_fx3_campr_card_path,
    build_fx3_camset_card_path,
    compute_expected_dci4k_2400p_hdmi_raw_and_still_aspect_state,
    compute_expected_photo_capture_and_enlarge_image_state,
    compute_expected_reg_custom_hold_and_camset_memory_state,
    evaluate_53pillar_recovery_master,
    evaluate_dci4k_2400p_hdmi_raw_still_aspect_vault,
    evaluate_realhw_53pillar_recovery_master,
    evaluate_reg_custom_hold_camset_photo_capture_vault,
    inspect_phase300_donors_readonly,
    run_pillar53_standalone_suite,
    run_pillar53a_dci4k_2400p_hdmi_raw_still_aspect_6_scenario_suite,
    run_pillar53b_custom_hold_camset_photo_capture_6_scenario_suite,
    verify_53pillar_recovery_suite,
    verify_dci4k_aspect_custom_hold_camset_photo_capture_and_vault,
    verify_dci4k_aspect_custom_hold_camset_photo_capture_vault,
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _is_ci() -> bool:
    return os.environ.get("GITHUB_ACTIONS") == "true"


def _clean_room_forced_by_env() -> bool:
    return (
        os.environ.get(P300_ENV_CLEAN_ROOM_TEST) == "1"
        or os.environ.get("FX3_FX6_FORCE_CLEAN_ROOM") == "1"
    )


class TestPhase300Pillar53And53PillarRecoveryMaster(unittest.TestCase):
    # ------------------------------------------------------------------
    # 1. Safety Invariants, Metadata & Wave-51 Constants (1..7)
    # ------------------------------------------------------------------

    def test_01_safety_constants_hard_locked(self) -> None:
        self.assertTrue(CNFLASHA_USERSPACE_WRITE_BLOCKED)
        self.assertTrue(READ_ONLY_DONOR_ACCESS)
        self.assertTrue(P300_SLOT1_FORMAT_HARD_LOCKED)
        self.assertTrue(P300_SLOT1_VAULT_EROFS_EBUSY_ENFORCED)
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(PERSISTENT_WRITE_RELEASE)
        self.assertFalse(SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        self.assertFalse(ISP_WRITE_AUTHORIZED)
        self.assertFalse(LIVE_USB_IOKIT_TRANSMIT_ENABLED)
        self.assertFalse(HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        self.assertFalse(OVERALL_READY_FOR_HARDWARE_ATTACH)
        self.assertFalse(P300_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        self.assertFalse(P300_OVERALL_READY_FOR_HARDWARE_ATTACH)
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

    def test_02_camera_baseline_and_phase300_metadata(self) -> None:
        self.assertEqual(PHASE300_PHASE_NUMBER, 300)
        self.assertEqual(PHASE300_VERSION, "1.0.0")
        self.assertIn("53pillar", PHASE300_SCHEMA)
        self.assertEqual(P300_FX3_MODEL_NAME, "ILME-FX3")
        self.assertEqual(P300_FX3_MODEL_ID, 0x91030080)
        self.assertEqual(P300_FX3_HELPGUIDE_ID, "ilc/2210")
        self.assertEqual(P300_FX3_FW_VERSION, "7.02")
        self.assertEqual(P300_FX3_SENSOR_FAMILY, "12 MP IMX510")

    def test_03_pillar53a_dci4k_2400p_hdmi_raw_still_aspect_constants(self) -> None:
        self.assertTrue(P300_FX3_APPFW_HAS_DCI4K_INTERNAL)
        self.assertEqual(P300_DCI4K_RESID16, 0x7336)
        self.assertEqual(P300_2400P_RESID16, 0x75CE)
        self.assertEqual(P300_2400P_REBOOT_G_RESID16, 0x639B)
        self.assertEqual(P300_2400P_REBOOT_ALT_G_RESID16, 0x63B6)
        self.assertEqual(P300_2400P_PLAYBACK_QUARANTINE_G_RESID16, 0x63D7)
        self.assertEqual(P300_DCI4K_DIMENSIONS, (4096, 2160))
        self.assertEqual(P300_DCI4K_ASPECT, "17:9")
        self.assertEqual(P300_UHD_4K_DIMENSIONS, (3840, 2160))
        self.assertEqual(P300_UHD_ASPECT, "16:9")
        self.assertEqual(P300_FX3_HDMI_RAW_DIMENSIONS, (4264, 2408))
        self.assertEqual(P300_FX3_STILL_RAW_NATIVE_DIMS, (4240, 2832))
        self.assertEqual(P300_DCI4K_SQ_ALLOWED_FPS, (1, 2, 3, 6, 12, 24, 48))
        self.assertEqual(P300_DCI4K_SQ_LOCKED_OUT_FPS, (100, 120))
        self.assertEqual(P300_STILL_ASPECT_RATIOS, ("3:2", "4:3", "16:9", "1:1"))
        self.assertEqual(P300_STILL_ASPECT_DEFAULT, "3:2")
        self.assertEqual(P300_STILL_ASPECT_BKID, "BKID_APP_setting_aspect_ratio")
        self.assertFalse(P300_FX6_HAS_STILL_ASPECT_RATIO)
        self.assertEqual(P300_FX6_DCI4K_SQ_MAX_FPS, 60)

    def test_04_pillar53b_reg_custom_hold_camset_photo_capture_enlarge_constants(self) -> None:
        self.assertEqual(len(P300_REG_CUSTOM_SHOOT_SET_11_CHECKBOXES), 11)
        self.assertEqual(P300_REG_CUSTOM_HOLD_CHECKBOX_COUNT, 11)
        self.assertEqual(
            P300_REG_CUSTOM_SHOOT_SET_SLOTS,
            ("Recall Custom hold 1", "Recall Custom hold 2", "Recall Custom hold 3"),
        )
        self.assertEqual(P300_REG_CUSTOM_HOLD_DEFAULT, "Recall Custom hold 1")
        self.assertEqual(P300_CAMSET_BODY_BANKS, ("1", "2", "3"))
        self.assertEqual(P300_CAMSET_CARD_BANKS, ("M1", "M2", "M3", "M4"))
        self.assertEqual(len(P300_CAMSET_ALL_BANKS), 7)
        self.assertEqual(P300_FX3_CAMPR_PATH_TEMPLATE, "%c:%s/SONY/SETTING/%s/CAMPR%02d%c.DAT")
        self.assertEqual(P300_FX3_CAMSET_PATH_TEMPLATE, "%c:%s/SONY/SETTING/%s/CAMSET/%s.DAT")
        self.assertEqual(P300_FX6_PRO_CAMERA_PATH_PREFIX, "s/SONY/PRO/CAMERA/")
        self.assertFalse(P300_FX3_APPFW_HAS_PRO_CAMERA_PATH)
        self.assertEqual(P300_PHOTO_CAPTURE_BKID, "BKID_APP_is_edit_photo_capture")
        self.assertEqual(P300_PHOTO_CAPTURE_DCI4K_LOCKOUT_G_RESID16, 0x60CE)
        self.assertEqual(P300_PHOTO_CAPTURE_FILE_TYPES, ("JPEG", "HEIF(4:2:0)", "HEIF(4:2:2)"))
        self.assertEqual(P300_PHOTO_CAPTURE_4K_UHD_MP, "8.3M")
        self.assertEqual(P300_PHOTO_CAPTURE_HD_MP, "2.1M")
        self.assertEqual(P300_ENLARGE_INITIAL_MAG_BKID, "BKID_APP_setting_magnif_set_in_large")
        self.assertEqual(P300_ENLARGE_INITIAL_POS_BKID, "BKID_APP_setting_position_set_in_large")
        self.assertFalse(P300_FX6_HAS_PHOTO_CAPTURE)
        self.assertFalse(P300_FX6_HAS_PLAYBACK_ENLARGE_IMAGE)
        self.assertFalse(P300_FX6_HAS_REG_CUSTOM_SHOOT_SET)
        self.assertFalse(P300_FX6_HAS_CAMERA_SET_MEMORY)

    def test_05_master_53_pillar_specs_lineage_and_uniqueness(self) -> None:
        self.assertEqual(MASTER_53_PILLAR_COUNT, 53)
        self.assertEqual(len(MASTER_53_PILLAR_SPECS), 53)
        self.assertEqual(len(MASTER_53_PILLAR_IDS), 53)
        self.assertEqual(len(set(MASTER_53_PILLAR_IDS)), 53)
        self.assertEqual(
            MASTER_53_PILLAR_SPECS[52],
            (
                53,
                "pillar_53_dci4k_aspect_custom_hold_camset_photo_capture_vault",
                "Phase 300 (300th Phase Milestone, Wave-51)",
                "fx3_recovery.realhw_53pillar_dci4k_aspect_custom_hold_camset_photo_capture_vault_verifier",
            ),
        )

    def test_06_public_package_exports_and_no_shadowing(self) -> None:
        for sym in p300.__all__:
            self.assertTrue(hasattr(fx3_recovery, sym), f"Missing export {sym}")
        self.assertIs(fx3_recovery.evaluate_realhw_53pillar_recovery_master, evaluate_realhw_53pillar_recovery_master)
        self.assertIs(fx3_recovery.evaluate_53pillar_recovery_master, evaluate_53pillar_recovery_master)
        self.assertIs(fx3_recovery.verify_53pillar_recovery_suite, verify_53pillar_recovery_suite)
        self.assertIs(fx3_recovery.run_pillar53_standalone_suite, run_pillar53_standalone_suite)

    def test_07_slot1_vault_constants_and_error_codes(self) -> None:
        codes = {
            P300_BLOCKED_SAFETY_POLICY_VIOLATION,
            P300_BLOCKED_INVALID_PILLAR53A_SPEC,
            P300_BLOCKED_DCI4K_LONG_GOP_OR_DORMANT_8K_VIOLATION,
            P300_BLOCKED_2400P_REBOOT_STAGE_B_WIPE_OR_QUARANTINE_DRIFT,
            P300_BLOCKED_HDMI_RAW_OR_STILL_ASPECT_VIOLATION,
            P300_BLOCKED_INVALID_PILLAR53B_SPEC,
            P300_BLOCKED_REG_CUSTOM_HOLD_OR_HLG_LOCKOUT_DRIFT,
            P300_BLOCKED_CAMSET_CROSS_MODEL_OR_PATH_VIOLATION,
            P300_BLOCKED_PHOTO_CAPTURE_DCI4K_LOCKOUT_OR_ENLARGE_DRIFT,
            P300_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL,
            P300_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
            P300_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
        }
        self.assertEqual(len(codes), 12)

    # ------------------------------------------------------------------
    # 2. Bounded O_RDONLY Donor Inspection & Helpers (8..18)
    # ------------------------------------------------------------------

    def test_08_donor_inspect_mode_aware_local_or_clean_room(self) -> None:
        snap = inspect_phase300_donors_readonly()
        self.assertTrue(snap.all_donors_present)
        self.assertEqual(snap.donor_files_inspected, 17)
        self.assertEqual(snap.raw_firmware_bytes_leaked, 0)
        self.assertTrue(snap.under_0_20s_budget)
        if _clean_room_forced_by_env():
            self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        else:
            self.assertIn(
                snap.verification_mode, ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC")
            )
            for art in snap.artifacts:
                self.assertTrue(art.matches_pinned, art)

    def test_09_donor_inspect_forced_clean_room_synthetic_all_17(self) -> None:
        snap = inspect_phase300_donors_readonly(force_clean_room=True)
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(snap.all_donors_present)
        self.assertEqual(snap.donor_files_inspected, 17)
        self.assertEqual(snap.raw_firmware_bytes_leaked, 0)
        self.assertTrue(all(a.read_mode == "CLEAN_ROOM_SYNTHETIC" for a in snap.artifacts))

    def test_10_donor_inspect_honors_env_clean_room_test_and_force_clean_room(self) -> None:
        with mock.patch.dict(os.environ, {P300_ENV_CLEAN_ROOM_TEST: "1"}):
            snap = inspect_phase300_donors_readonly()
            self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            snap2 = inspect_phase300_donors_readonly()
            self.assertEqual(snap2.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_11_donor_inspect_falls_back_cleanly_when_donor_missing(self) -> None:
        with mock.patch.dict(os.environ, {P300_ENV_CLEAN_ROOM_TEST: "", "FX3_FX6_FORCE_CLEAN_ROOM": ""}):
            with mock.patch.object(p300, "resolve_donor_path", return_value=None):
                snap = inspect_phase300_donors_readonly(force_clean_room=False)
                self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
                self.assertTrue(snap.all_donors_present)
                self.assertEqual(snap.donor_files_inspected, 17)

    def test_12_donor_inspect_detects_corrupted_elf64_uxc7_and_bk4(self) -> None:
        ok_elf, _ = p300._check_elf64_aarch64(b"\x00" * 64, "bad")
        self.assertFalse(ok_elf)
        ok_uxc, _ = p300._check_uxc7_pack(b"bad!" * 4, "bad")
        self.assertFalse(ok_uxc)
        ok_bk4, _ = p300._check_bk4_backup(b"\x00" * 32, "bad")
        self.assertFalse(ok_bk4)

    def test_13_read_donor_readonly_bounded_rejects_open_error_and_non_regular(self) -> None:
        with mock.patch.object(p300, "resolve_donor_path", return_value=Path("/nonexistent/fx3_fake")):
            present, _, _, status, _, _ = p300._read_donor_readonly_bounded("fake")
            self.assertFalse(present)
            self.assertEqual(status, "OPEN_ERROR")
        with mock.patch.object(p300, "resolve_donor_path", return_value=_repo_root() / "outputs"):
            present, _, _, status, _, _ = p300._read_donor_readonly_bounded("outputs")
            self.assertFalse(present)
            self.assertEqual(status, "NOT_REGULAR")

    def test_14_donor_inspect_respects_github_actions_ci_budget(self) -> None:
        with mock.patch.dict(os.environ, {"GITHUB_ACTIONS": "true"}):
            self.assertEqual(p300._donor_inspect_budget_seconds(), P300_DONOR_INSPECT_CI_BUDGET_SECONDS)
            snap = inspect_phase300_donors_readonly(force_clean_room=True)
            self.assertTrue(snap.under_0_20s_budget)
        with mock.patch.dict(os.environ, {"GITHUB_ACTIONS": "false"}):
            self.assertEqual(p300._donor_inspect_budget_seconds(), P300_DONOR_INSPECT_BUDGET_SECONDS)

    def test_15_donor_artifact_pinned_sha256_and_sizes_match(self) -> None:
        snap = inspect_phase300_donors_readonly(force_clean_room=True)
        by_id = {a.artifact_id: a for a in snap.artifacts}
        self.assertEqual(by_id["fx3_appfw_702_so"].total_bytes, P300_PINNED_FX3_APPFW_702_BYTES)
        self.assertEqual(by_id["fx3_appfw_702_so"].digest_sha256, P300_PINNED_FX3_APPFW_702_HDR4K_SHA256)
        self.assertEqual(by_id["fx6_appfw_601_so"].total_bytes, P300_PINNED_FX6_APPFW_601_BYTES)
        self.assertEqual(by_id["fx6_appfw_601_so"].digest_sha256, P300_PINNED_FX6_APPFW_601_HDR4K_SHA256)
        self.assertEqual(by_id["fx3_backup_bin"].total_bytes, P300_PINNED_FX3_BACKUP_BIN_BYTES)
        self.assertEqual(by_id["fx3_backup_bin"].digest_sha256, P300_PINNED_FX3_BACKUP_BIN_SHA256)
        self.assertEqual(by_id["fx3_uxc_en_f"].total_bytes, P300_PINNED_FX3_UXC_EN_F_BYTES)
        self.assertEqual(by_id["fx3_uxc_en_f"].digest_sha256, P300_PINNED_FX3_UXC_EN_F_SHA256)

    def test_16_build_fx3_campr_card_path_sdxc_and_cfexpress_formatting(self) -> None:
        self.assertEqual(
            build_fx3_campr_card_path(drive_letter="E", media_kind="SDXC", bank_index=1, slot_suffix="B"),
            "E:/PRIVATE/SONY/SETTING/FX3/CAMPR01B.DAT",
        )
        self.assertEqual(
            build_fx3_campr_card_path(
                drive_letter="E", media_kind="CFexpress Type A", bank_index=4, slot_suffix="A"
            ),
            "E:/SONY/SETTING/FX3/CAMPR04A.DAT",
        )

    def test_17_build_fx3_camset_card_path_and_invalid_inputs_raise(self) -> None:
        self.assertEqual(
            build_fx3_camset_card_path(drive_letter="E", media_kind="SDXC", filename_stem="CAMSET01"),
            "E:/PRIVATE/SONY/SETTING/FX3/CAMSET/CAMSET01.DAT",
        )
        self.assertEqual(
            build_fx3_camset_card_path(
                drive_letter="E", media_kind="CFexpress Type A", filename_stem="CAMSET10"
            ),
            "E:/SONY/SETTING/FX3/CAMSET/CAMSET10.DAT",
        )
        with self.assertRaises(ValueError):
            build_fx3_campr_card_path(media_kind="NVMe", bank_index=1)
        with self.assertRaises(ValueError):
            build_fx3_campr_card_path(media_kind="SDXC", bank_index=5)

    def test_18_path_helpers_tmpfs_and_persistent_emmc_detection(self) -> None:
        self.assertTrue(p300._is_tmpfs_path("/tmp/fx3_overlay"))
        self.assertTrue(p300._is_tmpfs_path("/run/fx3_overlay"))
        self.assertFalse(p300._is_tmpfs_path("/setting/fx3"))
        self.assertTrue(p300._targets_persistent_emmc("p2:/setting"))
        self.assertTrue(p300._targets_persistent_emmc("/dev/cnflasha"))
        self.assertFalse(p300._targets_persistent_emmc("/tmp/fx3_overlay"))

    # ------------------------------------------------------------------
    # 3. Pillar 53A — DCI 4K vs Long-GOP UHD, 24.00p Reboot Wipe,
    #    4264x2408 HDMI RAW & Still Aspect Ratio (19..40)
    # ------------------------------------------------------------------

    def test_19_p53a_default_safe_spec_passes(self) -> None:
        rep = evaluate_dci4k_2400p_hdmi_raw_still_aspect_vault(
            build_default_safe_dci4k_2400p_hdmi_raw_still_aspect_vault_spec()
        )
        self.assertTrue(rep.passed, rep.errors)
        self.assertEqual(rep.status, P300_STATUS_VERIFIED_PILLAR_53A)
        self.assertIsNone(rep.block_code)
        self.assertTrue(rep.dci4k_vs_long_gop_and_no_8k_verified)
        self.assertTrue(rep.reboot_2400p_stage_b_wipe_and_quarantine_verified)
        self.assertTrue(rep.hdmi_raw_4264_and_still_aspect_verified)
        self.assertTrue(rep.fx6_cinema_raw_and_still_less_contrast_verified)
        self.assertTrue(rep.slot1_erofs_ebusy_firewall_and_h0_h3_verified)

    def test_20_p53a_xavc_si_dci4k_all_valid_framerates_and_bitrates(self) -> None:
        for fps in P300_DCI4K_REC_FRAME_RATES:
            is_2400 = fps == "24.00p"
            grade = "CFexpress VPG200+" if P300_DCI4K_BITRATE_BY_FPS_MBPS[fps] >= 500 else "SDXC V90+"
            spec = build_default_safe_dci4k_2400p_hdmi_raw_still_aspect_vault_spec(
                file_format="XAVC S-I DCI 4K",
                target_rec_frame_rate=fps,
                media_card_grade=grade,
                reported_mandatory_reboot=is_2400,
                reported_volatile_stage_b_wiped=is_2400,
                reported_2400p_playback_quarantined=is_2400,
            )
            rep = evaluate_dci4k_2400p_hdmi_raw_still_aspect_vault(spec)
            self.assertTrue(rep.passed, f"{fps}: {rep.errors}")

    def test_21_p53a_xavc_si_dci4k_600m_requires_vpg200_or_v90(self) -> None:
        for grade in P300_DCI4K_600M_MIN_GRADES:
            rep = evaluate_dci4k_2400p_hdmi_raw_still_aspect_vault(
                build_default_safe_dci4k_2400p_hdmi_raw_still_aspect_vault_spec(
                    file_format="XAVC S-I DCI 4K",
                    target_rec_frame_rate="59.94p",
                    media_card_grade=grade,
                )
            )
            self.assertTrue(rep.passed, grade)

    def test_22_p53a_xavc_si_dci4k_rejects_v60_and_v30_at_5994p(self) -> None:
        for slow_grade in ("SDXC V60", "SDXC V30"):
            rep = evaluate_dci4k_2400p_hdmi_raw_still_aspect_vault(
                build_default_safe_dci4k_2400p_hdmi_raw_still_aspect_vault_spec(
                    file_format="XAVC S-I DCI 4K",
                    target_rec_frame_rate="59.94p",
                    media_card_grade=slow_grade,
                )
            )
            self.assertFalse(rep.passed)
            self.assertEqual(rep.block_code, P300_BLOCKED_DCI4K_LONG_GOP_OR_DORMANT_8K_VIOLATION)

    def test_23_p53a_xavc_si_dci4k_sq_1_to_48fps_passes_and_100_120fps_rejected(self) -> None:
        for sq_ok in P300_DCI4K_SQ_ALLOWED_FPS:
            rep = evaluate_dci4k_2400p_hdmi_raw_still_aspect_vault(
                build_default_safe_dci4k_2400p_hdmi_raw_still_aspect_vault_spec(sq_frame_rate_fps=sq_ok)
            )
            self.assertTrue(rep.passed, sq_ok)
        for sq_bad in P300_DCI4K_SQ_LOCKED_OUT_FPS:
            rep = evaluate_dci4k_2400p_hdmi_raw_still_aspect_vault(
                build_default_safe_dci4k_2400p_hdmi_raw_still_aspect_vault_spec(sq_frame_rate_fps=sq_bad)
            )
            self.assertFalse(rep.passed)
            self.assertEqual(rep.block_code, P300_BLOCKED_DCI4K_LONG_GOP_OR_DORMANT_8K_VIOLATION)

    def test_24_p53a_long_gop_xavc_hs_and_xavc_s_stay_strictly_3840x2160_uhd(self) -> None:
        for fmt in ("XAVC HS 4K", "XAVC S 4K", "XAVC S-I 4K"):
            rep = evaluate_dci4k_2400p_hdmi_raw_still_aspect_vault(
                build_default_safe_dci4k_2400p_hdmi_raw_still_aspect_vault_spec(
                    file_format=fmt,
                    reported_movie_dimensions=P300_UHD_4K_DIMENSIONS,
                    reported_movie_aspect=P300_UHD_ASPECT,
                    target_rec_frame_rate="119.88p" if fmt != "XAVC S-I 4K" else "59.94p",
                    sq_frame_rate_fps=120,
                )
            )
            self.assertTrue(rep.passed, f"{fmt}: {rep.errors}")

    def test_25_p53a_long_gop_or_xavc_si_4k_dci4096_or_2400p_spoof_rejected(self) -> None:
        rep_dims = evaluate_dci4k_2400p_hdmi_raw_still_aspect_vault(
            build_default_safe_dci4k_2400p_hdmi_raw_still_aspect_vault_spec(
                file_format="XAVC S 4K",
                reported_movie_dimensions=P300_DCI4K_DIMENSIONS,
                reported_movie_aspect=P300_DCI4K_ASPECT,
            )
        )
        self.assertFalse(rep_dims.passed)
        self.assertEqual(rep_dims.block_code, P300_BLOCKED_DCI4K_LONG_GOP_OR_DORMANT_8K_VIOLATION)

        rep_2400 = evaluate_dci4k_2400p_hdmi_raw_still_aspect_vault(
            build_default_safe_dci4k_2400p_hdmi_raw_still_aspect_vault_spec(
                file_format="XAVC HS 4K",
                reported_movie_dimensions=P300_UHD_4K_DIMENSIONS,
                reported_movie_aspect=P300_UHD_ASPECT,
                target_rec_frame_rate="24.00p",
                reported_mandatory_reboot=True,
                reported_volatile_stage_b_wiped=True,
                reported_2400p_playback_quarantined=True,
            )
        )
        self.assertFalse(rep_2400.passed)
        self.assertEqual(rep_2400.block_code, P300_BLOCKED_DCI4K_LONG_GOP_OR_DORMANT_8K_VIOLATION)

    def test_26_p53a_dormant_xavc_hs_8k_24p_rejected_fail_closed(self) -> None:
        rep = evaluate_dci4k_2400p_hdmi_raw_still_aspect_vault(
            build_default_safe_dci4k_2400p_hdmi_raw_still_aspect_vault_spec(
                file_format=P300_DORMANT_8K_FORMAT,
                reported_movie_dimensions=(7680, 4320),
                reported_movie_aspect="16:9",
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P300_BLOCKED_DCI4K_LONG_GOP_OR_DORMANT_8K_VIOLATION)

    def test_27_p53a_2400p_entry_triggers_mandatory_reboot_stage_b_wipe_h0_eq_h2_and_quarantine(
        self,
    ) -> None:
        rep = evaluate_dci4k_2400p_hdmi_raw_still_aspect_vault(
            build_default_safe_dci4k_2400p_hdmi_raw_still_aspect_vault_spec(
                prev_rec_frame_rate="23.98p",
                target_rec_frame_rate="24.00p",
                reported_mandatory_reboot=True,
                reported_volatile_stage_b_wiped=True,
                reported_2400p_playback_quarantined=True,
                stage_b_post_2400p_h0_eq_h2=True,
            )
        )
        self.assertTrue(rep.passed, rep.errors)
        self.assertTrue(rep.reboot_2400p_stage_b_wipe_and_quarantine_verified)

    def test_28_p53a_2400p_exit_triggers_mandatory_reboot_and_stage_b_wipe(self) -> None:
        rep = evaluate_dci4k_2400p_hdmi_raw_still_aspect_vault(
            build_default_safe_dci4k_2400p_hdmi_raw_still_aspect_vault_spec(
                prev_rec_frame_rate="24.00p",
                target_rec_frame_rate="23.98p",
                reported_mandatory_reboot=True,
                reported_volatile_stage_b_wiped=True,
                reported_2400p_playback_quarantined=False,
                stage_b_post_2400p_h0_eq_h2=True,
            )
        )
        self.assertTrue(rep.passed, rep.errors)

    def test_29_p53a_2400p_silent_no_reboot_or_stage_b_persist_or_unquarantined_rejected(
        self,
    ) -> None:
        for bad_kw in (
            {
                "prev_rec_frame_rate": "23.98p",
                "target_rec_frame_rate": "24.00p",
                "reported_mandatory_reboot": False,
                "reported_volatile_stage_b_wiped": True,
                "reported_2400p_playback_quarantined": True,
            },
            {
                "prev_rec_frame_rate": "23.98p",
                "target_rec_frame_rate": "24.00p",
                "reported_mandatory_reboot": True,
                "reported_volatile_stage_b_wiped": False,
                "reported_2400p_playback_quarantined": True,
            },
            {
                "prev_rec_frame_rate": "23.98p",
                "target_rec_frame_rate": "24.00p",
                "reported_mandatory_reboot": True,
                "reported_volatile_stage_b_wiped": True,
                "reported_2400p_playback_quarantined": False,
            },
            {
                "prev_rec_frame_rate": "23.98p",
                "target_rec_frame_rate": "24.00p",
                "reported_mandatory_reboot": True,
                "reported_volatile_stage_b_wiped": True,
                "reported_2400p_playback_quarantined": True,
                "stage_b_post_2400p_h0_eq_h2": False,
            },
        ):
            rep = evaluate_dci4k_2400p_hdmi_raw_still_aspect_vault(
                build_default_safe_dci4k_2400p_hdmi_raw_still_aspect_vault_spec(**bad_kw)
            )
            self.assertFalse(rep.passed)
            self.assertEqual(
                rep.block_code, P300_BLOCKED_2400P_REBOOT_STAGE_B_WIPE_OR_QUARANTINE_DRIFT
            )

    def test_30_p53a_shutter_mode_angle_5_6_to_360_validated_and_out_of_range_rejected(self) -> None:
        rep_ok = evaluate_dci4k_2400p_hdmi_raw_still_aspect_vault(
            build_default_safe_dci4k_2400p_hdmi_raw_still_aspect_vault_spec(
                shutter_mode="Angle", shutter_angle_deg=5.6
            )
        )
        self.assertTrue(rep_ok.passed)
        rep_bad = evaluate_dci4k_2400p_hdmi_raw_still_aspect_vault(
            build_default_safe_dci4k_2400p_hdmi_raw_still_aspect_vault_spec(
                shutter_mode="Angle", shutter_angle_deg=400.0
            )
        )
        self.assertFalse(rep_bad.passed)
        self.assertEqual(rep_bad.block_code, P300_BLOCKED_INVALID_PILLAR53A_SPEC)

    def test_31_p53a_4264x2408_hdmi_raw_requires_log_locks_slog3_blocks_ss_desqueeze(self) -> None:
        rep_off = evaluate_dci4k_2400p_hdmi_raw_still_aspect_vault(
            build_default_safe_dci4k_2400p_hdmi_raw_still_aspect_vault_spec(
                hdmi_raw_enabled=True, log_shooting_mode="Off"
            )
        )
        self.assertFalse(rep_off.passed)
        self.assertEqual(rep_off.block_code, P300_BLOCKED_DCI4K_LONG_GOP_OR_DORMANT_8K_VIOLATION)

        for bad_raw in (
            {"hdmi_raw_dimensions": (4096, 2160)},
            {"hdmi_raw_gamma_locked": "S-Cinetone"},
            {"hdmi_raw_steadyshot_active_allowed": True},
            {"hdmi_raw_desqueeze_allowed": True},
        ):
            rep = evaluate_dci4k_2400p_hdmi_raw_still_aspect_vault(
                build_default_safe_dci4k_2400p_hdmi_raw_still_aspect_vault_spec(**bad_raw)
            )
            self.assertFalse(rep.passed, bad_raw)
            self.assertEqual(rep.block_code, P300_BLOCKED_HDMI_RAW_OR_STILL_ASPECT_VIOLATION)

    def test_32_p53a_still_aspect_ratio_3_2_4_3_16_9_1_1_and_raw_native_invariant(self) -> None:
        self.assertEqual(len(P300_STILL_ASPECT_SIZE_MATRIX), 4)
        for ratio in P300_STILL_ASPECT_RATIOS:
            rep = evaluate_dci4k_2400p_hdmi_raw_still_aspect_vault(
                build_default_safe_dci4k_2400p_hdmi_raw_still_aspect_vault_spec(
                    still_aspect_ratio=ratio,
                    post_still_aspect_ratio=ratio,
                    still_raw_native_dims=(4240, 2832),
                )
            )
            self.assertTrue(rep.passed, ratio)
        rep_cropped_raw = evaluate_dci4k_2400p_hdmi_raw_still_aspect_vault(
            build_default_safe_dci4k_2400p_hdmi_raw_still_aspect_vault_spec(
                still_aspect_ratio="1:1",
                post_still_aspect_ratio="1:1",
                still_raw_native_dims=(2832, 2832),
            )
        )
        self.assertFalse(rep_cropped_raw.passed)
        self.assertEqual(rep_cropped_raw.block_code, P300_BLOCKED_HDMI_RAW_OR_STILL_ASPECT_VIOLATION)

    def test_33_p53a_still_aspect_reset_and_apsc_s35_l_to_m_step_down(self) -> None:
        rep_reset = evaluate_dci4k_2400p_hdmi_raw_still_aspect_vault(
            build_default_safe_dci4k_2400p_hdmi_raw_still_aspect_vault_spec(
                still_aspect_ratio="1:1",
                still_size_tier="S",
                reset_action="Camera Settings Reset",
                post_still_aspect_ratio="3:2",
                post_still_size_tier="L",
            )
        )
        self.assertTrue(rep_reset.passed, rep_reset.errors)

        rep_apsc = evaluate_dci4k_2400p_hdmi_raw_still_aspect_vault(
            build_default_safe_dci4k_2400p_hdmi_raw_still_aspect_vault_spec(
                apsc_s35_enabled=True,
                still_size_tier="L",
                post_still_size_tier="M",
            )
        )
        self.assertTrue(rep_apsc.passed, rep_apsc.errors)

        rep_bad_apsc = evaluate_dci4k_2400p_hdmi_raw_still_aspect_vault(
            build_default_safe_dci4k_2400p_hdmi_raw_still_aspect_vault_spec(
                apsc_s35_enabled=True,
                still_size_tier="L",
                post_still_size_tier="L",
            )
        )
        self.assertFalse(rep_bad_apsc.passed)
        self.assertEqual(rep_bad_apsc.block_code, P300_BLOCKED_HDMI_RAW_OR_STILL_ASPECT_VIOLATION)

    def test_34_p53a_fx6_still_aspect_or_raw_dimensions_conflation_rejected(self) -> None:
        for bad_fx6 in (
            {"fx6_has_still_aspect_ratio": True},
            {"fx6_raw_dimensions": ((4264, 2408),)},
            {"fx6_dci4k_sq_max_fps": 48},
            {"fx6_still_or_raw_conflation_events": 1},
        ):
            rep = evaluate_dci4k_2400p_hdmi_raw_still_aspect_vault(
                build_default_safe_dci4k_2400p_hdmi_raw_still_aspect_vault_spec(**bad_fx6)
            )
            self.assertFalse(rep.passed, bad_fx6)
            self.assertEqual(rep.block_code, P300_BLOCKED_HDMI_RAW_OR_STILL_ASPECT_VIOLATION)

    def test_35_p53a_slot1_vault_format_delete_and_camset_mutation_blocked(self) -> None:
        for action in ("FORMAT_QUICK", "FORMAT_FULL", "DELETE_SINGLE", "SAVE_CAMSET_DAT_CARD"):
            rep = evaluate_dci4k_2400p_hdmi_raw_still_aspect_vault(
                build_default_safe_dci4k_2400p_hdmi_raw_still_aspect_vault_spec(
                    requested_vault_action=action
                )
            )
            self.assertFalse(rep.passed, action)
            self.assertEqual(rep.block_code, P300_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL)

        rep_bytes = evaluate_dci4k_2400p_hdmi_raw_still_aspect_vault(
            build_default_safe_dci4k_2400p_hdmi_raw_still_aspect_vault_spec(
                target_capture_slot=1,
                slot1_vault_mutation_bytes=4096,
                slot1_vault_erofs_ebusy_enforced=False,
            )
        )
        self.assertFalse(rep_bytes.passed)
        self.assertEqual(rep_bytes.block_code, P300_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL)

    def test_36_p53a_persistent_overlay_escape_and_h0_h3_drift_rejected(self) -> None:
        rep_ov = evaluate_dci4k_2400p_hdmi_raw_still_aspect_vault(
            build_default_safe_dci4k_2400p_hdmi_raw_still_aspect_vault_spec(
                overlay_dir="/setting/53a",
                p2_blkroset_locked=False,
            )
        )
        self.assertFalse(rep_ov.passed)
        self.assertEqual(rep_ov.block_code, P300_BLOCKED_PERSISTENT_OVERLAY_ESCAPE)

        rep_h3 = evaluate_dci4k_2400p_hdmi_raw_still_aspect_vault(
            build_default_safe_dci4k_2400p_hdmi_raw_still_aspect_vault_spec(
                backup_bin_h3_sha256="0" * 64,
                tier0_surfaces_h0_h3_matched=15,
            )
        )
        self.assertFalse(rep_h3.passed)
        self.assertEqual(rep_h3.block_code, P300_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT)

    def test_37_p53a_persistent_write_unlock_and_safety_invariant_tamper_rejected(self) -> None:
        rep_unlock = evaluate_dci4k_2400p_hdmi_raw_still_aspect_vault(
            build_default_safe_dci4k_2400p_hdmi_raw_still_aspect_vault_spec(
                persistent_write_unlock_requested=True
            )
        )
        self.assertFalse(rep_unlock.passed)
        self.assertEqual(rep_unlock.block_code, P300_BLOCKED_SAFETY_POLICY_VIOLATION)

        with mock.patch.object(p300, "RAW_FIRMWARE_BYTES_LEAKED", 64):
            rep_tamper = evaluate_dci4k_2400p_hdmi_raw_still_aspect_vault(
                build_default_safe_dci4k_2400p_hdmi_raw_still_aspect_vault_spec()
            )
            self.assertFalse(rep_tamper.passed)
            self.assertEqual(rep_tamper.block_code, P300_BLOCKED_SAFETY_POLICY_VIOLATION)

    def test_38_p53a_invalid_camera_identity_fw_version_or_enum_rejected(self) -> None:
        for bad_id in (
            {"camera_model": "ILME-FX6"},
            {"camera_model_id": 0x12345678},
            {"fw_version": "2.00"},
            {"helpguide_id": "ilc/9999"},
            {"dci4k_aspect_surface_model": "FX6_RAW"},
            {"shutter_mode": "Auto"},
            {"reset_action": "FactoryWipe"},
        ):
            rep = evaluate_dci4k_2400p_hdmi_raw_still_aspect_vault(
                build_default_safe_dci4k_2400p_hdmi_raw_still_aspect_vault_spec(**bad_id)
            )
            self.assertFalse(rep.passed, bad_id)
            self.assertEqual(rep.block_code, P300_BLOCKED_INVALID_PILLAR53A_SPEC)

    def test_39_p53a_6_scenario_suite_passes_2_allow_4_reject(self) -> None:
        suite = run_pillar53a_dci4k_2400p_hdmi_raw_still_aspect_6_scenario_suite()
        self.assertTrue(suite.passed)
        self.assertEqual(suite.scenarios_passed, 6)
        self.assertEqual(suite.scenarios_total, 6)
        self.assertTrue(suite.scenarios[0].actual_allowed)
        self.assertTrue(suite.scenarios[1].actual_allowed)
        for s in suite.scenarios[2:]:
            self.assertFalse(s.actual_allowed)

    def test_40_p53a_report_json_serializable_and_deterministic_digest(self) -> None:
        s = build_default_safe_dci4k_2400p_hdmi_raw_still_aspect_vault_spec()
        r1 = evaluate_dci4k_2400p_hdmi_raw_still_aspect_vault(s)
        r2 = evaluate_dci4k_2400p_hdmi_raw_still_aspect_vault(s)
        self.assertEqual(r1.digest_sha256, r2.digest_sha256)
        parsed = json.loads(json.dumps(r1.to_dict(), sort_keys=True, allow_nan=False))
        self.assertTrue(parsed["passed"])

    # ------------------------------------------------------------------
    # 4. Pillar 53B — Reg. Custom Shoot Set (11 Checkboxes & HLG Off),
    #    Camera Set. Memory (CAMPR/CAMSET vs FX6 PRO/CAMERA), Photo
    #    Capture (DCI 4K Lockout & Slot-1 Firewall) & Enlarge Image (41..62)
    # ------------------------------------------------------------------

    def test_41_p53b_default_safe_spec_passes(self) -> None:
        rep = evaluate_reg_custom_hold_camset_photo_capture_vault(
            build_default_safe_reg_custom_hold_camset_photo_capture_vault_spec()
        )
        self.assertTrue(rep.passed, rep.errors)
        self.assertEqual(rep.status, P300_STATUS_VERIFIED_PILLAR_53B)
        self.assertIsNone(rep.block_code)
        self.assertTrue(rep.reg_custom_hold11_and_hlg_lockout_verified)
        self.assertTrue(rep.camset_path_isolation_and_fx6_firewall_verified)
        self.assertTrue(rep.photo_capture_dci4k_lockout_and_enlarge_verified)
        self.assertTrue(rep.slot1_erofs_ebusy_firewall_and_h0_h3_verified)

    def test_42_p53b_reg_custom_hold_1_2_3_still_pasm_only_with_exact_11_checkboxes(self) -> None:
        for slot in P300_REG_CUSTOM_SHOOT_SET_SLOTS:
            for mode in ("P", "A", "S", "M"):
                rep = evaluate_reg_custom_hold_camset_photo_capture_vault(
                    build_default_safe_reg_custom_hold_camset_photo_capture_vault_spec(
                        shooting_domain="Still",
                        shooting_mode=mode,
                        reg_custom_hold_slot=slot,
                        reported_reg_custom_hold_allowed=True,
                    )
                )
                self.assertTrue(rep.passed, f"{slot}/{mode}: {rep.errors}")

    def test_43_p53b_reg_custom_hold_blocked_in_movie_sq_intelligent_auto_and_mr(self) -> None:
        for dom, mode in (
            ("Movie", "M"),
            ("S&Q", "M"),
            ("Still", "Intelligent Auto"),
            ("Still", "MR"),
        ):
            rep_spoof = evaluate_reg_custom_hold_camset_photo_capture_vault(
                build_default_safe_reg_custom_hold_camset_photo_capture_vault_spec(
                    shooting_domain=dom,
                    shooting_mode=mode,
                    reported_reg_custom_hold_allowed=True,
                )
            )
            self.assertFalse(rep_spoof.passed, f"{dom}/{mode}")
            self.assertEqual(rep_spoof.block_code, P300_BLOCKED_REG_CUSTOM_HOLD_OR_HLG_LOCKOUT_DRIFT)

    def test_44_p53b_reg_custom_hold_wrong_checkbox_count_or_order_rejected(self) -> None:
        rep_short = evaluate_reg_custom_hold_camset_photo_capture_vault(
            build_default_safe_reg_custom_hold_camset_photo_capture_vault_spec(
                reg_custom_hold_checkboxes=P300_REG_CUSTOM_SHOOT_SET_11_CHECKBOXES[:10]
            )
        )
        self.assertFalse(rep_short.passed)
        self.assertEqual(rep_short.block_code, P300_BLOCKED_REG_CUSTOM_HOLD_OR_HLG_LOCKOUT_DRIFT)

    def test_45_p53b_reg_custom_hold_iso_or_dro_bracket_forces_hlg_still_off(self) -> None:
        for item in ("iso_sensitivity", "dro_bracket"):
            rep_ok = evaluate_reg_custom_hold_camset_photo_capture_vault(
                build_default_safe_reg_custom_hold_camset_photo_capture_vault_spec(
                    hold_recalled_items=(item,),
                    initial_hlg_still_image="On",
                    reported_hlg_still_image="Off",
                )
            )
            self.assertTrue(rep_ok.passed, item)
            rep_bad = evaluate_reg_custom_hold_camset_photo_capture_vault(
                build_default_safe_reg_custom_hold_camset_photo_capture_vault_spec(
                    hold_recalled_items=(item,),
                    initial_hlg_still_image="On",
                    reported_hlg_still_image="On",
                )
            )
            self.assertFalse(rep_bad.passed, item)
            self.assertEqual(rep_bad.block_code, P300_BLOCKED_REG_CUSTOM_HOLD_OR_HLG_LOCKOUT_DRIFT)

    def test_46_p53b_reg_custom_hold_survives_camera_settings_reset_wiped_only_by_initialize(
        self,
    ) -> None:
        rep_cam_reset = evaluate_reg_custom_hold_camset_photo_capture_vault(
            build_default_safe_reg_custom_hold_camset_photo_capture_vault_spec(
                reset_action="Camera Settings Reset",
                post_memory_recall_media="Slot 1",
                reported_reg_custom_hold_survived=True,
                reported_body_banks_survived=True,
            )
        )
        self.assertTrue(rep_cam_reset.passed, rep_cam_reset.errors)

        rep_init_ok = evaluate_reg_custom_hold_camset_photo_capture_vault(
            build_default_safe_reg_custom_hold_camset_photo_capture_vault_spec(
                reset_action="Initialize",
                post_memory_recall_media="Slot 1",
                reported_reg_custom_hold_survived=False,
                reported_body_banks_survived=False,
                post_photo_capture_type="JPEG",
                post_enlarge_init_mag=P300_ENLARGE_INITIAL_MAG_DEFAULT,
                post_enlarge_init_pos=P300_ENLARGE_INITIAL_POS_DEFAULT,
            )
        )
        self.assertTrue(rep_init_ok.passed, rep_init_ok.errors)

    def test_47_p53b_camset_body_1_3_and_card_m1_m4_sdxc_vs_cfexpress_paths(self) -> None:
        for bank in ("1", "2", "3", "M1", "M2", "M3", "M4"):
            for mkind in ("SDXC", "CFexpress Type A"):
                idx = 1 if bank in ("1", "2", "3") else int(bank[1])
                rep = evaluate_reg_custom_hold_camset_photo_capture_vault(
                    build_default_safe_reg_custom_hold_camset_photo_capture_vault_spec(
                        camset_bank=bank,
                        camset_media_kind=mkind,
                        camset_card_path=build_fx3_campr_card_path(
                            media_kind=mkind, bank_index=idx, slot_suffix="B"
                        ),
                        camset_all_path=build_fx3_camset_card_path(
                            media_kind=mkind, filename_stem="CAMSET05"
                        ),
                    )
                )
                self.assertTrue(rep.passed, f"{bank}/{mkind}: {rep.errors}")

    def test_48_p53b_camset_fx6_pro_camera_or_pro_scene_cross_model_import_rejected(self) -> None:
        for bad_camset in (
            {"camset_card_path": "E:/PRIVATE/SONY/PRO/CAMERA/C0001.DAT"},
            {"camset_all_path": "E:/PRIVATE/SONY/PRO/SCENE/SC001.DAT"},
            {"fx3_appfw_has_pro_camera_path": True},
            {"cross_model_fx6_import_attempted": True},
            {"camset_cross_model_path_drift_events": 1},
        ):
            rep = evaluate_reg_custom_hold_camset_photo_capture_vault(
                build_default_safe_reg_custom_hold_camset_photo_capture_vault_spec(**bad_camset)
            )
            self.assertFalse(rep.passed, bad_camset)
            self.assertEqual(rep.block_code, P300_BLOCKED_CAMSET_CROSS_MODEL_OR_PATH_VIOLATION)

    def test_49_p53b_camset_mr_mode_save_blocked_and_camera_reset_reverts_media_to_slot1(
        self,
    ) -> None:
        rep_mr = evaluate_reg_custom_hold_camset_photo_capture_vault(
            build_default_safe_reg_custom_hold_camset_photo_capture_vault_spec(
                shooting_mode="MR",
                reported_reg_custom_hold_allowed=False,
                reported_camset_save_allowed=True,
            )
        )
        self.assertFalse(rep_mr.passed)
        self.assertEqual(rep_mr.block_code, P300_BLOCKED_CAMSET_CROSS_MODEL_OR_PATH_VIOLATION)

        rep_drift = evaluate_reg_custom_hold_camset_photo_capture_vault(
            build_default_safe_reg_custom_hold_camset_photo_capture_vault_spec(
                memory_recall_media="Slot 2",
                reset_action="Camera Settings Reset",
                post_memory_recall_media="Slot 2",
            )
        )
        self.assertFalse(rep_drift.passed)
        self.assertEqual(rep_drift.block_code, P300_BLOCKED_CAMSET_CROSS_MODEL_OR_PATH_VIOLATION)

    def test_50_p53b_photo_capture_uhd_8_3m_and_hd_2_1m_to_slot2_jpeg_heif_passes(self) -> None:
        for ftype in P300_PHOTO_CAPTURE_FILE_TYPES:
            for dims, mp in ((P300_UHD_4K_DIMENSIONS, "8.3M"), (P300_HD_DIMENSIONS, "2.1M")):
                rep = evaluate_reg_custom_hold_camset_photo_capture_vault(
                    build_default_safe_reg_custom_hold_camset_photo_capture_vault_spec(
                        playback_media_kind="Movie",
                        select_playback_media="Slot 2",
                        clip_file_format="XAVC S 4K" if dims == P300_UHD_4K_DIMENSIONS else "XAVC S HD",
                        clip_resolution=dims,
                        configured_photo_capture_type=ftype,
                        post_photo_capture_type=ftype,
                        photo_capture_attempted=True,
                        reported_photo_capture_allowed=True,
                        reported_photo_capture_dims=dims,
                        reported_photo_capture_mp=mp,
                    )
                )
                self.assertTrue(rep.passed, f"{ftype}/{mp}: {rep.errors}")

    def test_51_p53b_photo_capture_locked_out_on_xavc_si_dci4k_clips(self) -> None:
        rep_dci = evaluate_reg_custom_hold_camset_photo_capture_vault(
            build_default_safe_reg_custom_hold_camset_photo_capture_vault_spec(
                playback_media_kind="Movie",
                select_playback_media="Slot 2",
                clip_file_format="XAVC S-I DCI 4K",
                clip_resolution=P300_DCI4K_DIMENSIONS,
                photo_capture_attempted=True,
                reported_photo_capture_allowed=True,
                reported_photo_capture_dims=P300_DCI4K_DIMENSIONS,
                reported_photo_capture_mp="8.8M",
            )
        )
        self.assertFalse(rep_dci.passed)
        self.assertEqual(rep_dci.block_code, P300_BLOCKED_PHOTO_CAPTURE_DCI4K_LOCKOUT_OR_ENLARGE_DRIFT)

    def test_52_p53b_photo_capture_blocked_fail_closed_when_select_playback_media_is_slot1_vault(
        self,
    ) -> None:
        rep_slot1_pc = evaluate_reg_custom_hold_camset_photo_capture_vault(
            build_default_safe_reg_custom_hold_camset_photo_capture_vault_spec(
                playback_media_kind="Movie",
                select_playback_media="Slot 1",
                clip_file_format="XAVC S 4K",
                clip_resolution=P300_UHD_4K_DIMENSIONS,
                photo_capture_attempted=True,
                reported_photo_capture_allowed=False,
                reported_photo_capture_dims=None,
                reported_photo_capture_mp=None,
                slot1_photo_capture_write_bytes=4096,
            )
        )
        self.assertFalse(rep_slot1_pc.passed)
        self.assertEqual(rep_slot1_pc.block_code, P300_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL)

    def test_53_p53b_slot1_campr_camset_save_and_format_blocked_erofs_ebusy(self) -> None:
        for action in ("SAVE_CAMPR_M1_M4_CARD", "SAVE_CAMSET_DAT_CARD", "FORMAT_QUICK", "DELETE_SINGLE"):
            rep = evaluate_reg_custom_hold_camset_photo_capture_vault(
                build_default_safe_reg_custom_hold_camset_photo_capture_vault_spec(
                    requested_vault_action=action,
                    target_camset_or_capture_slot=1,
                    slot1_camset_write_bytes=4096,
                )
            )
            self.assertFalse(rep.passed, action)
            self.assertEqual(rep.block_code, P300_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL)

    def test_54_p53b_enlarge_image_readonly_safe_even_with_camera_reset_survival(self) -> None:
        rep = evaluate_reg_custom_hold_camset_photo_capture_vault(
            build_default_safe_reg_custom_hold_camset_photo_capture_vault_spec(
                playback_media_kind="Still",
                select_playback_media="Slot 1",
                photo_capture_attempted=False,
                reported_photo_capture_allowed=False,
                reported_photo_capture_dims=None,
                reported_photo_capture_mp=None,
                enlarge_image_attempted=True,
                reported_enlarge_image_allowed=True,
                configured_enlarge_init_mag="Previous Mag.",
                post_enlarge_init_mag="Previous Mag.",
                configured_enlarge_init_pos="Center",
                post_enlarge_init_pos="Center",
                reset_action="Camera Settings Reset",
                post_memory_recall_media="Slot 1",
            )
        )
        self.assertTrue(rep.passed, rep.errors)

    def test_55_p53b_enlarge_image_initialize_resets_mag_and_pos(self) -> None:
        rep_ok = evaluate_reg_custom_hold_camset_photo_capture_vault(
            build_default_safe_reg_custom_hold_camset_photo_capture_vault_spec(
                playback_media_kind="Still",
                photo_capture_attempted=False,
                reported_photo_capture_allowed=False,
                reported_photo_capture_dims=None,
                reported_photo_capture_mp=None,
                enlarge_image_attempted=True,
                reported_enlarge_image_allowed=True,
                configured_enlarge_init_mag="Previous Mag.",
                post_enlarge_init_mag=P300_ENLARGE_INITIAL_MAG_DEFAULT,
                configured_enlarge_init_pos="Center",
                post_enlarge_init_pos=P300_ENLARGE_INITIAL_POS_DEFAULT,
                reset_action="Initialize",
                reported_reg_custom_hold_survived=False,
                reported_body_banks_survived=False,
                post_memory_recall_media="Slot 1",
            )
        )
        self.assertTrue(rep_ok.passed, rep_ok.errors)

    def test_56_p53b_fx6_has_zero_reg_hold_camset_photo_capture_or_enlarge(self) -> None:
        for flag, expected_code in (
            ("fx6_has_reg_custom_shoot_set", P300_BLOCKED_REG_CUSTOM_HOLD_OR_HLG_LOCKOUT_DRIFT),
            ("fx6_has_camera_set_memory", P300_BLOCKED_CAMSET_CROSS_MODEL_OR_PATH_VIOLATION),
            (
                "fx6_has_photo_capture",
                P300_BLOCKED_PHOTO_CAPTURE_DCI4K_LOCKOUT_OR_ENLARGE_DRIFT,
            ),
            (
                "fx6_has_playback_enlarge_image",
                P300_BLOCKED_PHOTO_CAPTURE_DCI4K_LOCKOUT_OR_ENLARGE_DRIFT,
            ),
        ):
            rep = evaluate_reg_custom_hold_camset_photo_capture_vault(
                build_default_safe_reg_custom_hold_camset_photo_capture_vault_spec(**{flag: True})
            )
            self.assertFalse(rep.passed, flag)
            self.assertEqual(rep.block_code, expected_code, flag)

    def test_57_p53b_persistent_overlay_escape_and_h0_h3_drift_rejected(self) -> None:
        rep_ov = evaluate_reg_custom_hold_camset_photo_capture_vault(
            build_default_safe_reg_custom_hold_camset_photo_capture_vault_spec(
                overlay_dir="/dev/cnflasha",
                p2_blkroset_locked=False,
            )
        )
        self.assertFalse(rep_ov.passed)
        self.assertEqual(rep_ov.block_code, P300_BLOCKED_PERSISTENT_OVERLAY_ESCAPE)

        rep_h3 = evaluate_reg_custom_hold_camset_photo_capture_vault(
            build_default_safe_reg_custom_hold_camset_photo_capture_vault_spec(
                backup_bin_h3_sha256="b" * 64,
                tier0_surfaces_h0_h3_matched=15,
            )
        )
        self.assertFalse(rep_h3.passed)
        self.assertEqual(rep_h3.block_code, P300_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT)

    def test_58_p53b_safety_policy_tamper_and_invalid_enum_rejected(self) -> None:
        rep_unlock = evaluate_reg_custom_hold_camset_photo_capture_vault(
            build_default_safe_reg_custom_hold_camset_photo_capture_vault_spec(
                persistent_write_unlock_requested=True
            )
        )
        self.assertFalse(rep_unlock.passed)
        self.assertEqual(rep_unlock.block_code, P300_BLOCKED_SAFETY_POLICY_VIOLATION)

        for bad_kw in (
            {"camera_model": "ILME-FX6"},
            {"camset_bank": "M9"},
            {"camset_media_kind": "XQD"},
            {"configured_photo_capture_type": "TIFF"},
            {"configured_enlarge_init_mag": "20x"},
            {"configured_enlarge_init_pos": "TopLeft"},
        ):
            rep_inv = evaluate_reg_custom_hold_camset_photo_capture_vault(
                build_default_safe_reg_custom_hold_camset_photo_capture_vault_spec(**bad_kw)
            )
            self.assertFalse(rep_inv.passed, bad_kw)
            self.assertEqual(rep_inv.block_code, P300_BLOCKED_INVALID_PILLAR53B_SPEC)

    def test_59_p53b_6_scenario_suite_passes_2_allow_4_reject(self) -> None:
        suite = run_pillar53b_custom_hold_camset_photo_capture_6_scenario_suite()
        self.assertTrue(suite.passed)
        self.assertEqual(suite.scenarios_passed, 6)
        self.assertEqual(suite.scenarios_total, 6)
        self.assertTrue(suite.scenarios[0].actual_allowed)
        self.assertTrue(suite.scenarios[1].actual_allowed)
        for s in suite.scenarios[2:]:
            self.assertFalse(s.actual_allowed)

    def test_60_p53b_report_json_serializable_and_deterministic_digest(self) -> None:
        s = build_default_safe_reg_custom_hold_camset_photo_capture_vault_spec()
        r1 = evaluate_reg_custom_hold_camset_photo_capture_vault(s)
        r2 = evaluate_reg_custom_hold_camset_photo_capture_vault(s)
        self.assertEqual(r1.digest_sha256, r2.digest_sha256)
        parsed = json.loads(json.dumps(r1.to_dict(), sort_keys=True, allow_nan=False))
        self.assertTrue(parsed["passed"])
        self.assertEqual(parsed["slot1_vault_mutation_bytes"], 0)

    def test_61_compute_helpers_path_builders_and_reg_hold_camset_state(self) -> None:
        p_sdxc = build_fx3_campr_card_path(
            drive_letter="E", media_kind="SDXC", bank_index=3, slot_suffix="A"
        )
        p_cfex = build_fx3_camset_card_path(
            drive_letter="F", media_kind="CFexpress Type A", filename_stem="CAMSET07"
        )
        self.assertEqual(p_sdxc, "E:/PRIVATE/SONY/SETTING/FX3/CAMPR03A.DAT")
        self.assertEqual(p_cfex, "F:/SONY/SETTING/FX3/CAMSET/CAMSET07.DAT")
        with self.assertRaises(ValueError):
            build_fx3_campr_card_path(media_kind="SDXC", bank_index=5)

        st_reg = compute_expected_reg_custom_hold_and_camset_memory_state(
            shooting_domain="Still",
            shooting_mode="A",
            hold_recalled_items=("iso_sensitivity",),
            initial_hlg_still_image="On",
            camset_bank="2",
            memory_recall_media="Slot 2",
            reset_action="Camera Settings Reset",
        )
        self.assertEqual(st_reg, (True, "Off", True, True, "Slot 1", True))

        st_pc = compute_expected_photo_capture_and_enlarge_image_state(
            clip_file_format="XAVC S-I DCI 4K",
            clip_resolution=P300_DCI4K_DIMENSIONS,
            select_playback_media="Slot 2",
            slot1_holds_recovery_vault=True,
            playback_media_kind="Movie",
            configured_photo_capture_type="HEIF",
            configured_enlarge_init_mag="Previous Mag.",
            configured_enlarge_init_pos="Center",
            reset_action="Initialize",
        )
        self.assertFalse(st_pc[0])  # DCI 4K locks out Photo Capture
        self.assertIsNone(st_pc[1])
        self.assertEqual(st_pc[4], "JPEG")
        self.assertEqual(st_pc[5], P300_ENLARGE_INITIAL_MAG_DEFAULT)
        self.assertEqual(st_pc[6], P300_ENLARGE_INITIAL_POS_DEFAULT)

    # ------------------------------------------------------------------
    # 5. Combined Verifier & Standalone Pillar 53 Suite (62..68)
    # ------------------------------------------------------------------

    def test_62_combined_verifier_passes_and_alias_matches(self) -> None:
        r1 = verify_dci4k_aspect_custom_hold_camset_photo_capture_and_vault(force_clean_room=True)
        r2 = verify_dci4k_aspect_custom_hold_camset_photo_capture_vault(force_clean_room=True)
        self.assertTrue(r1.all_passed)
        self.assertTrue(r2.passed)
        self.assertEqual(r1.status, P300_STATUS_VERIFIED_PILLAR53_SUITE)
        self.assertEqual(r1.slot1_vault_mutation_bytes, 0)
        self.assertEqual(r1.raw_firmware_bytes_leaked, 0)
        self.assertFalse(r1.overall_ready_for_hardware_attach)

    def test_63_combined_verifier_fails_when_53a_fails(self) -> None:
        bad_53a = build_default_safe_dci4k_2400p_hdmi_raw_still_aspect_vault_spec(
            file_format=P300_DORMANT_8K_FORMAT
        )
        r = verify_dci4k_aspect_custom_hold_camset_photo_capture_and_vault(
            force_clean_room=True, spec_53a=bad_53a
        )
        self.assertFalse(r.all_passed)
        self.assertEqual(r.status, P300_STATUS_FAIL_PILLAR53_SUITE)

    def test_64_combined_verifier_fails_when_53b_fails(self) -> None:
        bad_53b = build_default_safe_reg_custom_hold_camset_photo_capture_vault_spec(
            cross_model_fx6_import_attempted=True
        )
        r = verify_dci4k_aspect_custom_hold_camset_photo_capture_and_vault(
            force_clean_room=True, spec_53b=bad_53b
        )
        self.assertFalse(r.all_passed)
        self.assertEqual(r.status, P300_STATUS_FAIL_PILLAR53_SUITE)

    def test_65_standalone_suite_passes_default_and_clean_room(self) -> None:
        st_def = run_pillar53_standalone_suite()
        self.assertTrue(st_def.all_passed, st_def.errors)
        self.assertEqual(st_def.pillar_53a_dci4k_2400p_hdmi_raw_aspect_vault.scenarios_passed, 6)
        self.assertEqual(st_def.pillar_53b_custom_hold_camset_photo_capture_vault.scenarios_passed, 6)
        self.assertEqual(st_def.raw_firmware_bytes_leaked, 0)

        st_cr = run_pillar53_standalone_suite(force_clean_room=True)
        self.assertTrue(st_cr.all_passed)
        self.assertEqual(st_cr.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_66_standalone_suite_propagates_53a_and_53b_failures(self) -> None:
        bad_a = replace(run_pillar53a_dci4k_2400p_hdmi_raw_still_aspect_6_scenario_suite(), passed=False)
        with mock.patch.object(
            p300,
            "run_pillar53a_dci4k_2400p_hdmi_raw_still_aspect_6_scenario_suite",
            return_value=bad_a,
        ):
            st = run_pillar53_standalone_suite(force_clean_room=True)
            self.assertFalse(st.all_passed)
            self.assertEqual(st.status, P300_STATUS_FAIL_PILLAR53_SUITE)
            self.assertEqual(st.dci4k_long_gop_or_8k_violations, 1)
            self.assertEqual(st.slot1_vault_mutation_bytes, 4096)

        bad_b = replace(run_pillar53b_custom_hold_camset_photo_capture_6_scenario_suite(), passed=False)
        with mock.patch.object(
            p300,
            "run_pillar53b_custom_hold_camset_photo_capture_6_scenario_suite",
            return_value=bad_b,
        ):
            st2 = run_pillar53_standalone_suite(force_clean_room=True)
            self.assertFalse(st2.all_passed)
            self.assertEqual(st2.slot1_camset_write_bytes, 4096)
            self.assertEqual(st2.slot1_photo_capture_write_bytes, 4096)

    def test_67_standalone_suite_json_serializable_and_deterministic_sha(self) -> None:
        s1 = run_pillar53_standalone_suite(force_clean_room=True)
        s2 = run_pillar53_standalone_suite(force_clean_room=True)
        self.assertEqual(s1.suite_sha256, s2.suite_sha256)
        payload = json.dumps(s1.to_dict(), sort_keys=True, allow_nan=False)
        parsed = json.loads(payload)
        self.assertEqual(parsed["status"], P300_STATUS_VERIFIED_PILLAR53_SUITE)
        self.assertEqual(parsed["raw_firmware_bytes_leaked"], 0)

    def test_68_standalone_suite_donor_error_and_budget_guard(self) -> None:
        bad_snap = replace(
            inspect_phase300_donors_readonly(force_clean_room=True),
            all_donors_present=False,
            under_0_20s_budget=False,
        )
        with mock.patch.object(p300, "inspect_phase300_donors_readonly", return_value=bad_snap):
            st = run_pillar53_standalone_suite(force_clean_room=True)
            self.assertFalse(st.all_passed)
            self.assertTrue(any("donor" in e.lower() for e in st.errors))

    # ------------------------------------------------------------------
    # 6. Unified 53-Pillar Recovery Master Aggregator — Phase 300 (69..76)
    # ------------------------------------------------------------------

    def test_69_master_53of53_passes_in_default_mode_under_budget(self) -> None:
        m53 = evaluate_realhw_53pillar_recovery_master()
        self.assertTrue(m53.all_passed, m53.errors)
        self.assertEqual(m53.status, P300_STATUS_VERIFIED_53OF53_AGGREGATOR)
        self.assertGreaterEqual(m53.pillar_count, 53)
        self.assertGreaterEqual(m53.pillars_passed, 53)
        self.assertEqual(m53.failed_pillars, ())
        budget = 15.0 if _is_ci() else P300_FAST_CLI_BUDGET_SECONDS * 2.5
        self.assertLess(m53.elapsed_seconds, budget)
        self.assertEqual(m53.raw_firmware_bytes_leaked, 0)
        self.assertFalse(m53.persistent_emmc_writes_authorized)
        self.assertFalse(m53.overall_ready_for_hardware_attach)
        self.assertFalse(m53.hardware_live_attachment_authorized)

    def test_70_master_53of53_passes_in_clean_room_and_env_forced_modes(self) -> None:
        m_cr = evaluate_realhw_53pillar_recovery_master(force_clean_room=True)
        self.assertTrue(m_cr.all_passed)
        self.assertEqual(m_cr.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertGreaterEqual(m_cr.pillars_passed, 53)

        with mock.patch.dict(os.environ, {P300_ENV_CLEAN_ROOM_TEST: "1"}):
            m_env = evaluate_53pillar_recovery_master()
            self.assertTrue(m_env.all_passed)
            self.assertEqual(m_env.verification_mode, "CLEAN_ROOM_SYNTHETIC")

        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            m_env2 = verify_53pillar_recovery_suite()
            self.assertTrue(m_env2.all_passed)
            self.assertEqual(m_env2.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_71_master_53of53_preserves_52_plus_1_lineage_and_wave51_fields(self) -> None:
        m52 = evaluate_realhw_52pillar_recovery_master(force_clean_room=True)
        m53 = evaluate_realhw_53pillar_recovery_master(force_clean_room=True)
        self.assertEqual(m53.pillar_count, m52.pillar_count + 1)
        self.assertEqual(m53.pillars[-1].pillar_number, 53)
        self.assertEqual(
            m53.pillars[-1].pillar_id,
            "pillar_53_dci4k_aspect_custom_hold_camset_photo_capture_vault",
        )
        self.assertTrue(m53.fx3_appfw_has_dci4k_internal)
        self.assertFalse(m53.fx3_appfw_has_pro_camera_path)
        self.assertFalse(m53.fx6_has_still_aspect_ratio)
        self.assertFalse(m53.fx6_has_photo_capture)
        self.assertFalse(m53.fx6_has_playback_enlarge_image)
        self.assertFalse(m53.fx6_has_reg_custom_shoot_set)
        self.assertFalse(m53.fx6_has_camera_set_memory)
        self.assertEqual(m53.slot1_camset_write_bytes, 0)
        self.assertEqual(m53.slot1_photo_capture_write_bytes, 0)
        self.assertEqual(m53.slot1_vault_mutation_bytes, 0)
        self.assertTrue(m53.slot1_format_hard_locked)
        self.assertTrue(m53.slot1_vault_erofs_ebusy_enforced)

    def test_72_master_53of53_fault_injection_pillar53(self) -> None:
        m53 = evaluate_realhw_53pillar_recovery_master(
            force_clean_room=True,
            fault_inject_pillar="pillar_53_dci4k_aspect_custom_hold_camset_photo_capture_vault",
        )
        self.assertFalse(m53.all_passed)
        self.assertEqual(m53.status, P300_STATUS_FAIL_53OF53_AGGREGATOR)
        self.assertEqual(m53.pillars_passed, 52)
        self.assertEqual(
            m53.failed_pillars,
            ("pillar_53_dci4k_aspect_custom_hold_camset_photo_capture_vault",),
        )

    def test_73_master_53of53_fault_injection_unknown_pillar_raises(self) -> None:
        with self.assertRaises(ValueError):
            evaluate_realhw_53pillar_recovery_master(
                force_clean_room=True,
                fault_inject_pillar="nonexistent_pillar_53",
            )

    def test_74_master_53of53_rejects_m52_or_p53_safety_and_vault_drift(self) -> None:
        m52_bad = replace(
            evaluate_realhw_52pillar_recovery_master(force_clean_room=True),
            raw_firmware_bytes_leaked=32,
        )
        with mock.patch.object(p300, "evaluate_realhw_52pillar_recovery_master", return_value=m52_bad):
            m53 = evaluate_realhw_53pillar_recovery_master(force_clean_room=True)
            self.assertFalse(m53.all_passed)
            self.assertTrue(any("raw_firmware_bytes_leaked" in e for e in m53.errors))

        p53_bad = replace(
            run_pillar53_standalone_suite(force_clean_room=True),
            slot1_camset_write_bytes=4096,
        )
        with mock.patch.object(p300, "run_pillar53_standalone_suite", return_value=p53_bad):
            m53_b = evaluate_realhw_53pillar_recovery_master(force_clean_room=True)
            self.assertFalse(m53_b.all_passed)
            self.assertTrue(any("slot1_camset_write_bytes" in e for e in m53_b.errors))

    def test_75_master_53of53_digest_deterministic_and_json_roundtrip(self) -> None:
        r1 = evaluate_realhw_53pillar_recovery_master(force_clean_room=True)
        r2 = evaluate_realhw_53pillar_recovery_master(force_clean_room=True)
        self.assertEqual(r1.master_53pillar_sha256, r2.master_53pillar_sha256)
        payload = json.dumps(r1.to_dict(), sort_keys=True, allow_nan=False)
        parsed = json.loads(payload)
        self.assertGreaterEqual(parsed["pillar_count"], 53)
        self.assertGreaterEqual(parsed["pillars_passed"], 53)
        self.assertEqual(parsed["status"], P300_STATUS_VERIFIED_53OF53_AGGREGATOR)

    def test_76_backward_compatibility_52pillar_master_still_passes(self) -> None:
        m52 = evaluate_realhw_52pillar_recovery_master(force_clean_room=True)
        self.assertTrue(m52.all_passed)
        self.assertGreaterEqual(m52.pillar_count, 52)
        self.assertGreaterEqual(m52.pillars_passed, 52)

    # ------------------------------------------------------------------
    # 7. CLI Subcommands, --out Output & Subprocess Portability (77..82)
    # ------------------------------------------------------------------

    def test_77_cli_pillar53_json_and_out_in_repo_work_tests(self) -> None:
        work_tests = _repo_root() / "work" / "_tests"
        work_tests.mkdir(parents=True, exist_ok=True)
        out_dir = Path(tempfile.mkdtemp(prefix="p300_p53_", dir=str(work_tests)))
        shutil.rmtree(out_dir)
        try:
            buf = io.StringIO()
            with mock.patch.object(
                sys,
                "argv",
                [
                    "fx3_recovery",
                    "verify-pillar53-dci4k-aspect-custom-hold-camset-vault",
                    "--clean-room",
                    "--json",
                    "--out",
                    str(out_dir),
                ],
            ):
                with redirect_stdout(buf):
                    rc = cli_main.main()
            self.assertEqual(rc, 0)
            payload = json.loads(buf.getvalue())
            self.assertTrue(payload["all_passed"])
            self.assertEqual(payload["status"], P300_STATUS_VERIFIED_PILLAR53_SUITE)
            report_file = out_dir / "pillar53-dci4k-aspect-custom-hold-camset-vault-report.json"
            self.assertTrue(report_file.is_file())
        finally:
            shutil.rmtree(out_dir, ignore_errors=True)

    def test_78_cli_53pillar_recovery_json_and_out_in_repo_work_tests(self) -> None:
        work_tests = _repo_root() / "work" / "_tests"
        work_tests.mkdir(parents=True, exist_ok=True)
        out_dir = Path(tempfile.mkdtemp(prefix="p300_m53_", dir=str(work_tests)))
        shutil.rmtree(out_dir)
        try:
            buf = io.StringIO()
            with mock.patch.object(
                sys,
                "argv",
                [
                    "fx3_recovery",
                    "verify-53pillar-recovery",
                    "--clean-room",
                    "--json",
                    "--out",
                    str(out_dir),
                ],
            ):
                with redirect_stdout(buf):
                    rc = cli_main.main()
            self.assertEqual(rc, 0)
            payload = json.loads(buf.getvalue())
            self.assertTrue(payload["all_passed"])
            self.assertGreaterEqual(payload["pillars_passed"], 53)
            self.assertEqual(payload["status"], P300_STATUS_VERIFIED_53OF53_AGGREGATOR)
            report_file = out_dir / "53pillar-recovery-master-report.json"
            self.assertTrue(report_file.is_file())
        finally:
            shutil.rmtree(out_dir, ignore_errors=True)

    def test_79_cli_human_readable_output_and_subprocess_sys_executable(self) -> None:
        b1 = io.StringIO()
        with mock.patch.object(
            sys,
            "argv",
            ["fx3_recovery", "verify-pillar53-dci4k-aspect-custom-hold-camset-vault", "--clean-room"],
        ):
            with redirect_stdout(b1):
                rc1 = cli_main.main()
        self.assertEqual(rc1, 0)
        self.assertIn("pillar_53a=6/6", b1.getvalue())
        self.assertIn("pillar_53b=6/6", b1.getvalue())

        b2 = io.StringIO()
        with mock.patch.object(
            sys,
            "argv",
            ["fx3_recovery", "verify-53pillar-recovery", "--clean-room"],
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
            "verify-pillar53-dci4k-aspect-custom-hold-camset-vault --clean-room --json",
            "verify-53pillar-recovery --clean-room --json",
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
            parsed = json.loads(proc.stdout)
            self.assertTrue(parsed["all_passed"])

    def test_80_cli_help_portability_and_python314_percent_escaping(self) -> None:
        adapter_dir = _repo_root() / "outputs" / "fx3-recovery-adapter"
        env_base = dict(os.environ)
        env_base["PYTHONDONTWRITEBYTECODE"] = "1"
        env_base["PYTHONPATH"] = str(adapter_dir)
        for subcmd in (
            "--help",
            "verify-pillar53-dci4k-aspect-custom-hold-camset-vault --help",
            "verify-53pillar-recovery --help",
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
            self.assertNotIn("ValueError", proc.stderr)

    def test_81_cli_returns_nonzero_on_pillar53_and_master_failures(self) -> None:
        failed_st = replace(
            run_pillar53_standalone_suite(force_clean_room=True),
            all_passed=False,
            status=P300_STATUS_FAIL_PILLAR53_SUITE,
        )
        with mock.patch.object(cli_main, "run_pillar53_standalone_suite", return_value=failed_st):
            buf = io.StringIO()
            with mock.patch.object(
                sys,
                "argv",
                [
                    "fx3_recovery",
                    "verify-pillar53-dci4k-aspect-custom-hold-camset-vault",
                    "--clean-room",
                    "--json",
                ],
            ):
                with redirect_stdout(buf):
                    rc = cli_main.main()
            self.assertEqual(rc, 2)

        failed_m = replace(
            evaluate_realhw_53pillar_recovery_master(force_clean_room=True),
            all_passed=False,
            status=P300_STATUS_FAIL_53OF53_AGGREGATOR,
        )
        with mock.patch.object(cli_main, "verify_53pillar_recovery_suite", return_value=failed_m):
            buf = io.StringIO()
            with mock.patch.object(
                sys,
                "argv",
                ["fx3_recovery", "verify-53pillar-recovery", "--clean-room", "--json"],
            ):
                with redirect_stdout(buf):
                    rc = cli_main.main()
            self.assertEqual(rc, 2)

    def test_82_no_raw_firmware_bytes_or_usb_tx_anywhere_in_module(self) -> None:
        snap = inspect_phase300_donors_readonly()
        st = run_pillar53_standalone_suite(force_clean_room=True)
        m53 = evaluate_realhw_53pillar_recovery_master(force_clean_room=True)
        self.assertEqual(snap.raw_firmware_bytes_leaked, 0)
        self.assertEqual(st.raw_firmware_bytes_leaked, 0)
        self.assertEqual(m53.raw_firmware_bytes_leaked, 0)
        self.assertEqual(st.passive_tx_bytes_emitted, 0)
        self.assertEqual(m53.passive_tx_bytes_emitted, 0)
        self.assertFalse(m53.overall_ready_for_hardware_attach)
        self.assertFalse(m53.persistent_emmc_writes_authorized)


if __name__ == "__main__":
    unittest.main()

