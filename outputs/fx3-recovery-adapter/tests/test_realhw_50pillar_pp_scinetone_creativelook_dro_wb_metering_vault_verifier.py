"""Phase 287 (50/50 Recovery Pillars Milestone!) — Dual-mode unit tests for Pillar 50
(`[Picture Profile]` `PP11` `S-Cinetone` default vs `[Creative Look]` 10 presets + `CREATIVE_BOX_1..6`,
`[D-Range Optimizer]`, `[Log Shooting]` triple lockout, `PPLUT1..4` Movie-only & `1080p` HDMI clamp,
`PP1..11` / `[Different Set for Still/Mv]` non-resettable recovery trap vs `[PPx]->[Reset]` & `FX6` `Base Look`,
`[White Balance]` `2500K..9900K`, `Custom 1..3` `CAMSET` Slot-1 exclusion, `Cine EI` AWB/`[Custom Setup]` trap,
`[Metering Mode]` 6 modes, `De-Squeeze` Face-Priority lockout, `Cine EI` Base ISO `800`/`12800` `M.M.` invariance)
and unified `50/50` recovery master (`verify-50pillar-recovery` / `verify-pp-scinetone-wb-metering-vault`).
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
    realhw_50pillar_pp_scinetone_creativelook_dro_wb_metering_vault_verifier as p287,
)
from fx3_recovery.realhw_49pillar_usb_mode_hdmi_info_protect_network_reset_vault_verifier import (
    MASTER_49_PILLAR_SPECS,
    evaluate_realhw_49pillar_recovery_master,
)
from fx3_recovery.realhw_50pillar_pp_scinetone_creativelook_dro_wb_metering_vault_verifier import (
    ALLOW_BOOT_PARTITION_TARGETING,
    ALLOW_DESTRUCTIVE_FASTBOOT,
    ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS,
    ALLOW_PERSISTENT_JIRITSU_WRITES,
    CNFLASHA_USERSPACE_WRITE_BLOCKED,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    ISP_WRITE_AUTHORIZED,
    LIVE_USB_IOKIT_TRANSMIT_ENABLED,
    MASTER_50_PILLAR_COUNT,
    MASTER_50_PILLAR_IDS,
    MASTER_50_PILLAR_SPECS,
    OTP_FUSE_TOUCHES,
    OTP_FUSE_WRITES,
    P287_AEL_W_SHUTTER_BKID,
    P287_AEL_W_SHUTTER_DEFAULT,
    P287_AEL_W_SHUTTER_MODES,
    P287_BLOCKED_DOUBLE_LOG_OR_LOCKOUT_BYPASS,
    P287_BLOCKED_FX6_BASELOOK_CONFUSION,
    P287_BLOCKED_INVALID_PILLAR50A_SPEC,
    P287_BLOCKED_INVALID_PILLAR50B_SPEC,
    P287_BLOCKED_METERING_DESQUEEZE_OR_CINE_EI_BASE_ISO_DRIFT,
    P287_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
    P287_BLOCKED_PP_INTERNAL_OR_DIFF_SET_RESET_TRAP,
    P287_BLOCKED_SAFETY_POLICY_VIOLATION,
    P287_BLOCKED_SLOT1_VAULT_FORMAT_OR_MUTATION,
    P287_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
    P287_BLOCKED_WB_CINE_EI_AWB_OR_CUSTOM_SETUP_TRAP,
    P287_BLOCKED_WB_CUSTOM_CAMSET_EXCLUSION_DRIFT,
    P287_CAMSET_FILENAMES,
    P287_CINE_EI_BASE_ISOS,
    P287_CREATIVE_LOOK_10_PRESETS,
    P287_CREATIVE_LOOK_8_PARAMS,
    P287_CREATIVE_LOOK_BKID,
    P287_CREATIVE_LOOK_CUSTOM_SLOTS,
    P287_CREATIVE_LOOK_DEFAULT,
    P287_CREATIVE_LOOK_LOCKED,
    P287_CREATIVE_LOOK_RESID16,
    P287_DESQUEEZE_MODES,
    P287_DIFF_SET_BKID,
    P287_DIFF_SET_RESID16,
    P287_DONOR_INSPECT_BUDGET_SECONDS,
    P287_DONOR_INSPECT_CI_BUDGET_SECONDS,
    P287_DRO_BKID,
    P287_DRO_DEFAULT,
    P287_DRO_MODES,
    P287_DRO_RESID16,
    P287_ENV_CLEAN_ROOM_TEST,
    P287_FACE_PRIORITY_MULTI_BKID,
    P287_FACE_PRIORITY_MULTI_DEFAULT,
    P287_FACE_PRIORITY_MULTI_RESID16,
    P287_FAST_CLI_BUDGET_SECONDS,
    P287_FX3_FW_VERSION,
    P287_FX3_HELPGUIDE_ID,
    P287_FX3_MODEL_ID,
    P287_FX3_MODEL_NAME,
    P287_FX6_BASE_LOOK_CINE_EI_LOCKED,
    P287_FX6_BASE_LOOK_CUSTOM_DEFAULT,
    P287_FX6_DONOR_FW_VERSION,
    P287_FX6_DONOR_MODEL_NAME,
    P287_FX6_WB_MODES,
    P287_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    P287_LOG_SHOOTING_BKID,
    P287_LOG_SHOOTING_DEFAULT,
    P287_LOG_SHOOTING_MODES,
    P287_LOG_SHOOTING_RESID16,
    P287_METERING_6_MODES,
    P287_METERING_MODE_BKID,
    P287_METERING_MODE_DEFAULT,
    P287_METERING_MODE_RESID16,
    P287_PICTURE_PROFILE_ALL_MODES,
    P287_PICTURE_PROFILE_BKID,
    P287_PICTURE_PROFILE_FACTORY_DEFAULT,
    P287_PICTURE_PROFILE_RESID16,
    P287_PILLAR_50A_SCENARIO_IDS,
    P287_PILLAR_50B_SCENARIO_IDS,
    P287_PINNED_FX3_APPFW_702_BYTES,
    P287_PINNED_FX3_APPFW_702_HDR4K_SHA256,
    P287_PINNED_FX3_BACKUP_BIN_BYTES,
    P287_PINNED_FX3_BACKUP_BIN_SHA256,
    P287_PINNED_FX3_UXC_EN_F_BYTES,
    P287_PINNED_FX3_UXC_EN_F_SHA256,
    P287_PINNED_FX6_APPFW_601_BYTES,
    P287_PINNED_FX6_APPFW_601_HDR4K_SHA256,
    P287_PP11_RESID16,
    P287_PPLUT_MODES,
    P287_PP_1_TO_11,
    P287_PRIORITY_IN_AWB_BKID,
    P287_PRIORITY_IN_AWB_DEFAULT,
    P287_SCINETONE_CAUTION_ID,
    P287_SCINETONE_RESID16,
    P287_SHOCKLESS_WB_BKID,
    P287_SHOCKLESS_WB_DEFAULT,
    P287_SHOCKLESS_WB_MODES,
    P287_SHUTTER_AWB_LOCK_BKID,
    P287_SHUTTER_AWB_LOCK_DEFAULT,
    P287_SHUTTER_AWB_LOCK_MODES,
    P287_SLOT1_FORMAT_HARD_LOCKED,
    P287_SPOT_METERING_POINT_BKID,
    P287_SPOT_METERING_POINT_DEFAULT,
    P287_SPOT_METERING_POINT_MODES,
    P287_STATUS_VERIFIED_50OF50_AGGREGATOR,
    P287_STATUS_VERIFIED_PILLAR50_SUITE,
    P287_STATUS_VERIFIED_PILLAR_50A,
    P287_STATUS_VERIFIED_PILLAR_50B,
    P287_WB_AB_RANGE,
    P287_WB_ALL_MODES,
    P287_WB_CTEMP_MAX_K,
    P287_WB_CTEMP_MIN_K,
    P287_WB_CTEMP_STEP_COUNT,
    P287_WB_CTEMP_STEP_K,
    P287_WB_CUSTOM_SLOTS,
    P287_WB_DEFAULT,
    P287_WB_GM_RANGE,
    P287_WHITE_BALANCE_BKID,
    P287_WHITE_BALANCE_RESID16,
    PASSIVE_TX_BYTES_EMITTED,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHASE287_PHASE_NUMBER,
    PHASE287_SCHEMA,
    PHASE287_VERSION,
    PHYSICAL_DEVICE_WRITES,
    PHYSICAL_USB_PACKETS_EMITTED,
    PictureProfileScinetoneDroLogVaultSpec,
    RAW_FIRMWARE_BYTES_LEAKED,
    READ_ONLY_DONOR_ACCESS,
    RPMB_COUNTER_INCREMENTS,
    SPI_NOR_WRITE_AUTHORIZED,
    WhiteBalanceCamsetExclusionAndMeteringVaultSpec,
    build_default_safe_pp_scinetone_dro_log_vault_spec,
    build_default_safe_wb_camset_exclusion_metering_vault_spec,
    compute_expected_metering_and_cine_ei_invariance,
    compute_expected_pillar50a_reset_state,
    compute_expected_pp_creativelook_dro_log_pipeline,
    compute_expected_wb_cine_ei_custom_guard,
    evaluate_50pillar_recovery_master,
    evaluate_pp_scinetone_creativelook_dro_log_vault,
    evaluate_realhw_50pillar_recovery_master,
    evaluate_wb_camset_exclusion_and_metering_vault,
    inspect_phase287_donors_readonly,
    run_pillar50_standalone_suite,
    run_pillar50a_pp_scinetone_creativelook_dro_6_scenario_suite,
    run_pillar50b_wb_camset_exclusion_metering_6_scenario_suite,
    verify_50pillar_recovery_suite,
    verify_pp_scinetone_creativelook_dro_wb_metering_and_vault,
    verify_pp_scinetone_creativelook_dro_wb_metering_vault,
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _is_ci() -> bool:
    return os.environ.get("GITHUB_ACTIONS") == "true"


def _clean_room_forced_by_env() -> bool:
    return (
        os.environ.get(P287_ENV_CLEAN_ROOM_TEST) == "1"
        or os.environ.get("FX3_FX6_FORCE_CLEAN_ROOM") == "1"
    )


class TestPhase287Pillar50And50PillarRecoveryMaster(unittest.TestCase):
    # ------------------------------------------------------------------
    # 1. Safety Invariants & Firmware Reality Constants (1..5)
    # ------------------------------------------------------------------

    def test_01_safety_constants_hard_locked(self) -> None:
        self.assertTrue(CNFLASHA_USERSPACE_WRITE_BLOCKED)
        self.assertTrue(READ_ONLY_DONOR_ACCESS)
        self.assertTrue(P287_SLOT1_FORMAT_HARD_LOCKED)
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(PERSISTENT_WRITE_RELEASE)
        self.assertFalse(SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        self.assertFalse(ISP_WRITE_AUTHORIZED)
        self.assertFalse(LIVE_USB_IOKIT_TRANSMIT_ENABLED)
        self.assertFalse(HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        self.assertFalse(P287_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
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
        self.assertEqual(p287._safety_invariant_errors(), [])

    def test_02_wave48_schema_and_camera_anchor_constants(self) -> None:
        self.assertEqual(PHASE287_PHASE_NUMBER, 287)
        self.assertEqual(
            PHASE287_SCHEMA,
            "realhw_50pillar_pp_scinetone_creativelook_dro_wb_metering_vault_verifier_v1",
        )
        self.assertEqual(PHASE287_VERSION, "1.0.0")
        self.assertEqual(P287_FX3_MODEL_NAME, "ILME-FX3")
        self.assertEqual(P287_FX3_FW_VERSION, "7.02")
        self.assertEqual(P287_FX3_MODEL_ID, 0x91030080)
        self.assertEqual(P287_FX3_HELPGUIDE_ID, "ilc/2210")
        self.assertEqual(P287_FX6_DONOR_MODEL_NAME, "ILME-FX6")
        self.assertEqual(P287_FX6_DONOR_FW_VERSION, "6.01")
        self.assertEqual(len(P287_CAMSET_FILENAMES), 10)
        self.assertEqual(P287_CAMSET_FILENAMES[0], "CAMSET01.DAT")

    def test_03_picture_profile_creative_look_dro_log_anchors(self) -> None:
        self.assertEqual(P287_PICTURE_PROFILE_FACTORY_DEFAULT, "PP11")
        self.assertEqual(P287_PICTURE_PROFILE_BKID, "BKID_APP_setting_picture_profile")
        self.assertEqual(P287_DIFF_SET_BKID, "BKID_APP_setting_different_set")
        self.assertEqual(P287_PICTURE_PROFILE_RESID16, 0x6830)
        self.assertEqual(P287_PP11_RESID16, 0x67AB)
        self.assertEqual(P287_SCINETONE_RESID16, 0x6E61)
        self.assertEqual(P287_SCINETONE_CAUTION_ID, "CAUTION_ID_FACTOR_GAMMA_SCINETONE_MSG")
        self.assertEqual(P287_DIFF_SET_RESID16, 0x62EE)
        self.assertEqual(P287_CREATIVE_LOOK_BKID, "BKID_APP_setting_creative_style_plus")
        self.assertEqual(P287_CREATIVE_LOOK_RESID16, 0x6823)
        self.assertEqual(P287_CREATIVE_LOOK_DEFAULT, "ST")
        self.assertEqual(P287_CREATIVE_LOOK_LOCKED, "-")
        self.assertEqual(len(P287_CREATIVE_LOOK_10_PRESETS), 10)
        self.assertEqual(len(P287_CREATIVE_LOOK_CUSTOM_SLOTS), 6)
        self.assertEqual(len(P287_CREATIVE_LOOK_8_PARAMS), 8)
        self.assertEqual(P287_DRO_BKID, "BKID_APP_setting_dro")
        self.assertEqual(P287_DRO_RESID16, 0xE89C)
        self.assertEqual(P287_DRO_DEFAULT, "Auto")
        self.assertEqual(len(P287_DRO_MODES), 7)
        self.assertEqual(P287_LOG_SHOOTING_BKID, "BKID_APP_setting_log_shooting")
        self.assertEqual(P287_LOG_SHOOTING_RESID16, 0x6020)
        self.assertEqual(P287_LOG_SHOOTING_DEFAULT, "Off")
        self.assertEqual(
            P287_LOG_SHOOTING_MODES,
            ("Off", "Flexible ISO", "Cine EI Quick", "Cine EI"),
        )
        self.assertEqual(len(P287_PP_1_TO_11), 11)
        self.assertEqual(len(P287_PPLUT_MODES), 4)
        self.assertEqual(len(P287_PICTURE_PROFILE_ALL_MODES), 16)
        self.assertEqual(P287_FX6_BASE_LOOK_CUSTOM_DEFAULT, "S-Cinetone")
        self.assertEqual(P287_FX6_BASE_LOOK_CINE_EI_LOCKED, "S-Log3")

    def test_04_white_balance_and_metering_anchors(self) -> None:
        self.assertEqual(P287_WHITE_BALANCE_BKID, "BKID_APP_setting_white_balance")
        self.assertEqual(P287_WHITE_BALANCE_RESID16, 0xE5D4)
        self.assertEqual(P287_WB_DEFAULT, "Auto")
        self.assertEqual(P287_PRIORITY_IN_AWB_BKID, "BKID_APP_setting_priority_set_in_awb")
        self.assertEqual(P287_PRIORITY_IN_AWB_DEFAULT, "Standard")
        self.assertEqual(P287_SHUTTER_AWB_LOCK_BKID, "BKID_APP_setting_stl_awb_lock_with_shutter")
        self.assertEqual(P287_SHUTTER_AWB_LOCK_DEFAULT, "Off")
        self.assertEqual(len(P287_SHUTTER_AWB_LOCK_MODES), 3)
        self.assertEqual(P287_SHOCKLESS_WB_BKID, "BKID_APP_setting_movie_shockless_wb")
        self.assertEqual(P287_SHOCKLESS_WB_DEFAULT, "1 (Fast)")
        self.assertEqual(len(P287_SHOCKLESS_WB_MODES), 4)
        self.assertEqual(P287_WB_CTEMP_MIN_K, 2500)
        self.assertEqual(P287_WB_CTEMP_MAX_K, 9900)
        self.assertEqual(P287_WB_CTEMP_STEP_K, 100)
        self.assertEqual(P287_WB_CTEMP_STEP_COUNT, 75)
        self.assertEqual(P287_WB_AB_RANGE, (-7, 7))
        self.assertEqual(P287_WB_GM_RANGE, (-7, 7))
        self.assertEqual(P287_WB_CUSTOM_SLOTS, ("Custom 1", "Custom 2", "Custom 3"))
        self.assertEqual(P287_METERING_MODE_BKID, "BKID_APP_setting_metering_mode")
        self.assertEqual(P287_METERING_MODE_RESID16, 0xE5CF)
        self.assertEqual(P287_METERING_MODE_DEFAULT, "Multi")
        self.assertEqual(len(P287_METERING_6_MODES), 6)
        self.assertEqual(P287_FACE_PRIORITY_MULTI_BKID, "BKID_APP_setting_face_detection_in_multi")
        self.assertEqual(P287_FACE_PRIORITY_MULTI_RESID16, 0x69C7)
        self.assertEqual(P287_FACE_PRIORITY_MULTI_DEFAULT, "On")
        self.assertEqual(
            P287_SPOT_METERING_POINT_BKID,
            "BKID_APP_setting_spot_metering_link_to_focus_point",
        )
        self.assertEqual(P287_SPOT_METERING_POINT_DEFAULT, "Center")
        self.assertEqual(P287_SPOT_METERING_POINT_MODES, ("Center", "Focus Point Link"))
        self.assertEqual(P287_AEL_W_SHUTTER_BKID, "BKID_APP_setting_still_image_ael_w_shutter")
        self.assertEqual(P287_AEL_W_SHUTTER_DEFAULT, "Auto")
        self.assertEqual(P287_AEL_W_SHUTTER_MODES, ("Auto", "On", "Off"))
        self.assertEqual(P287_CINE_EI_BASE_ISOS, (800, 12800))
        self.assertEqual(P287_DESQUEEZE_MODES, ("Off", "1.3x", "1.6x", "2.0x"))

    def test_05_master_50_pillar_catalog_structure(self) -> None:
        self.assertEqual(MASTER_50_PILLAR_COUNT, 50)
        self.assertEqual(len(MASTER_50_PILLAR_SPECS), 50)
        self.assertEqual(len(MASTER_50_PILLAR_IDS), 50)
        self.assertEqual(MASTER_50_PILLAR_SPECS[:49], MASTER_49_PILLAR_SPECS)
        nums = [spec[0] for spec in MASTER_50_PILLAR_SPECS]
        self.assertEqual(nums, list(range(1, 51)))
        self.assertEqual(
            MASTER_50_PILLAR_SPECS[49][1],
            "pillar_50_pp_scinetone_creativelook_dro_wb_metering_vault",
        )
        self.assertEqual(MASTER_50_PILLAR_SPECS[49][2], "Phase 287 (50/50 Milestone)")
        self.assertEqual(len(P287_PILLAR_50A_SCENARIO_IDS), 6)
        self.assertEqual(len(P287_PILLAR_50B_SCENARIO_IDS), 6)

    # ------------------------------------------------------------------
    # 2. Bounded O_RDONLY Donor Inspection & Clean-Room Fallback (6..12)
    # ------------------------------------------------------------------

    def test_06_clean_room_donor_inspection_synthetic_mode(self) -> None:
        snap = inspect_phase287_donors_readonly(force_clean_room=True)
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(snap.all_donors_present)
        self.assertEqual(snap.donor_files_inspected, 11)
        self.assertEqual(len(snap.artifacts), 11)
        self.assertEqual(snap.raw_firmware_bytes_leaked, 0)
        self.assertTrue(snap.under_0_20s_budget)
        self.assertTrue(all(a.matches_pinned and a.present for a in snap.artifacts))
        self.assertTrue(all(a.read_mode == "CLEAN_ROOM_SYNTHETIC" for a in snap.artifacts))

    def test_07_active_donor_inspection_respects_environment(self) -> None:
        snap = inspect_phase287_donors_readonly()
        self.assertTrue(snap.all_donors_present)
        self.assertEqual(snap.donor_files_inspected, 11)
        self.assertEqual(snap.raw_firmware_bytes_leaked, 0)
        self.assertTrue(snap.under_0_20s_budget)
        if _clean_room_forced_by_env():
            self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        else:
            self.assertIn(snap.verification_mode, ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"))
        if snap.verification_mode == "LOCAL_DONOR_O_RDONLY":
            by_id = {a.artifact_id: a for a in snap.artifacts}
            self.assertEqual(by_id["fx3_appfw_702_so"].total_bytes, P287_PINNED_FX3_APPFW_702_BYTES)
            self.assertEqual(
                by_id["fx3_appfw_702_so"].digest_sha256,
                P287_PINNED_FX3_APPFW_702_HDR4K_SHA256,
            )
            self.assertEqual(by_id["fx6_appfw_601_so"].total_bytes, P287_PINNED_FX6_APPFW_601_BYTES)
            self.assertEqual(
                by_id["fx6_appfw_601_so"].digest_sha256,
                P287_PINNED_FX6_APPFW_601_HDR4K_SHA256,
            )
            self.assertEqual(by_id["fx3_backup_bin"].total_bytes, P287_PINNED_FX3_BACKUP_BIN_BYTES)
            self.assertEqual(by_id["fx3_backup_bin"].digest_sha256, P287_PINNED_FX3_BACKUP_BIN_SHA256)
            self.assertEqual(by_id["fx3_uxc_en_f"].total_bytes, P287_PINNED_FX3_UXC_EN_F_BYTES)
            self.assertEqual(by_id["fx3_uxc_en_f"].digest_sha256, P287_PINNED_FX3_UXC_EN_F_SHA256)
            budget = (
                P287_DONOR_INSPECT_CI_BUDGET_SECONDS
                if _is_ci()
                else P287_DONOR_INSPECT_BUDGET_SECONDS
            )
            self.assertLess(snap.elapsed_seconds, budget)

    def test_08_env_clean_room_var_forces_clean_room(self) -> None:
        with mock.patch.dict(os.environ, {P287_ENV_CLEAN_ROOM_TEST: "1"}, clear=False):
            snap = inspect_phase287_donors_readonly(force_clean_room=None)
            self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertTrue(snap.all_donors_present)

    def test_09_fx3_fx6_force_clean_room_env_var_forces_clean_room(self) -> None:
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}, clear=False):
            snap = inspect_phase287_donors_readonly(force_clean_room=None)
            self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertTrue(snap.all_donors_present)

    def test_10_missing_donors_fallback_clean_room(self) -> None:
        with mock.patch.dict(
            os.environ,
            {P287_ENV_CLEAN_ROOM_TEST: "", "FX3_FX6_FORCE_CLEAN_ROOM": ""},
            clear=False,
        ):
            with mock.patch.object(p287, "resolve_donor_path", return_value=None):
                snap = inspect_phase287_donors_readonly(force_clean_room=False)
                self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
                self.assertTrue(snap.all_donors_present)
                self.assertEqual(snap.raw_firmware_bytes_leaked, 0)

    def test_11_corrupted_donor_digest_detected_fail_closed(self) -> None:
        good_ret = (
            True,
            P287_PINNED_FX3_UXC_EN_F_BYTES,
            P287_PINNED_FX3_UXC_EN_F_BYTES,
            "FULL_SHA256",
            "bad0" * 16,
            b"uxc\x07" + b"\x00" * 32,
        )
        with mock.patch.dict(
            os.environ,
            {P287_ENV_CLEAN_ROOM_TEST: "", "FX3_FX6_FORCE_CLEAN_ROOM": ""},
            clear=False,
        ):
            with mock.patch.object(p287, "_read_donor_readonly_bounded", return_value=good_ret):
                snap = inspect_phase287_donors_readonly(force_clean_room=False)
                self.assertFalse(snap.all_donors_present)
                self.assertEqual(snap.verification_mode, "LOCAL_DONOR_O_RDONLY")
                self.assertTrue(any(not a.matches_pinned for a in snap.artifacts))

    def test_12_donor_snapshot_bounded_read_limits(self) -> None:
        snap = inspect_phase287_donors_readonly()
        for art in snap.artifacts:
            if art.digest_kind == "HEADER4K_SHA256":
                self.assertEqual(art.header_bytes_read, 4096)
                self.assertGreater(art.total_bytes, 4096)
            else:
                self.assertEqual(art.digest_kind, "FULL_SHA256")
                self.assertEqual(art.header_bytes_read, art.total_bytes)

    # ------------------------------------------------------------------
    # 3. Pillar 50A — PP11 S-Cinetone, Creative Look, DRO, Log & Reset Trap (13..27)
    # ------------------------------------------------------------------

    def test_13_pillar50a_default_safe_spec_passes(self) -> None:
        spec = build_default_safe_pp_scinetone_dro_log_vault_spec()
        rep = evaluate_pp_scinetone_creativelook_dro_log_vault(spec)
        self.assertTrue(rep.passed, rep.errors)
        self.assertEqual(rep.status, P287_STATUS_VERIFIED_PILLAR_50A)
        self.assertIsNone(rep.block_code)
        self.assertTrue(rep.pp11_scinetone_default_and_diff_set_verified)
        self.assertTrue(rep.mutual_exclusivity_and_log_lockout_verified)
        self.assertTrue(rep.pplut_movie_only_and_1080p_clamp_verified)
        self.assertTrue(rep.pp_internal_reset_trap_verified)
        self.assertTrue(rep.fx6_baselook_distinction_verified)
        self.assertTrue(rep.h0_equals_h3_verified)
        self.assertGreaterEqual(rep.matrix_states_checked, 40)
        self.assertEqual(rep.double_log_or_lockout_bypass_events, 0)
        self.assertEqual(rep.pplut_1080p_clamp_bypass_events, 0)
        self.assertEqual(rep.pp_internal_reset_trap_violations, 0)
        self.assertEqual(rep.fx6_baselook_confusion_events, 0)
        self.assertEqual(rep.slot1_vault_mutation_bytes, 0)

    def test_14_pp11_default_locks_creative_look_and_dro(self) -> None:
        exp_pp, exp_cl, exp_dro, exp_gda, pplut_ok, exp_hdmi = (
            compute_expected_pp_creativelook_dro_log_pipeline(
                shooting_domain="Movie",
                intelligent_auto=False,
                log_shooting="Off",
                configured_picture_profile="PP11",
                configured_creative_look="IN",
                configured_dro="Lv5",
                configured_gamma_disp_assist="On",
                hlg_still_image=False,
                hdmi_internal_recording=True,
                configured_hdmi_resolution="Auto",
            )
        )
        self.assertEqual(exp_pp, "PP11")
        self.assertEqual(exp_cl, "-")
        self.assertEqual(exp_dro, "Off")
        self.assertEqual(exp_gda, "On")
        self.assertTrue(pplut_ok)
        self.assertEqual(exp_hdmi, "Auto")

    def test_15_pp_off_and_log_off_unlocks_creative_look_and_dro(self) -> None:
        for cl in P287_CREATIVE_LOOK_10_PRESETS + P287_CREATIVE_LOOK_CUSTOM_SLOTS:
            for dro in P287_DRO_MODES:
                exp_pp, exp_cl, exp_dro, exp_gda, pplut_ok, _ = (
                    compute_expected_pp_creativelook_dro_log_pipeline(
                        shooting_domain="Still",
                        intelligent_auto=False,
                        log_shooting="Off",
                        configured_picture_profile="Off",
                        configured_creative_look=cl,
                        configured_dro=dro,
                        configured_gamma_disp_assist="Off",
                        hlg_still_image=False,
                        hdmi_internal_recording=False,
                        configured_hdmi_resolution="2160p",
                    )
                )
                self.assertEqual(exp_pp, "Off")
                self.assertEqual(exp_cl, cl)
                self.assertEqual(exp_dro, dro)
                self.assertEqual(exp_gda, "Off")
                self.assertFalse(pplut_ok)

    def test_16_log_shooting_all_modes_lock_pp_cl_dro_and_clamp_hdmi_1080p(self) -> None:
        for log_mode in ("Flexible ISO", "Cine EI Quick", "Cine EI"):
            exp_pp, exp_cl, exp_dro, exp_gda, _, exp_hdmi = (
                compute_expected_pp_creativelook_dro_log_pipeline(
                    shooting_domain="Movie",
                    intelligent_auto=False,
                    log_shooting=log_mode,
                    configured_picture_profile="PP11",
                    configured_creative_look="FL",
                    configured_dro="Lv3",
                    configured_gamma_disp_assist="On",
                    hlg_still_image=False,
                    hdmi_internal_recording=True,
                    configured_hdmi_resolution="2160p",
                )
            )
            self.assertEqual(exp_pp, "Off")
            self.assertEqual(exp_cl, "-")
            self.assertEqual(exp_dro, "Off")
            self.assertEqual(exp_gda, "Off")
            self.assertEqual(exp_hdmi, "1080p")

            rep = evaluate_pp_scinetone_creativelook_dro_log_vault(
                PictureProfileScinetoneDroLogVaultSpec(
                    log_shooting=log_mode,
                    configured_picture_profile="PP11",
                    configured_creative_look="FL",
                    configured_dro="Lv3",
                    configured_gamma_disp_assist="On",
                    reported_picture_profile="Off",
                    reported_creative_look="-",
                    reported_dro="Off",
                    reported_gamma_disp_assist="Off",
                    hdmi_internal_recording=True,
                    configured_hdmi_resolution="2160p",
                    reported_hdmi_resolution="1080p",
                )
            )
            self.assertTrue(rep.passed, f"Log mode {log_mode} failed: {rep.errors}")

    def test_17_reject_double_log_bypass_when_pp_or_cl_or_dro_unlocked_in_log(self) -> None:
        rep = evaluate_pp_scinetone_creativelook_dro_log_vault(
            PictureProfileScinetoneDroLogVaultSpec(
                log_shooting="Cine EI",
                reported_picture_profile="PP8",
                reported_creative_look="-",
                reported_dro="Off",
                reported_gamma_disp_assist="Off",
                hdmi_internal_recording=True,
                reported_hdmi_resolution="1080p",
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P287_BLOCKED_DOUBLE_LOG_OR_LOCKOUT_BYPASS)
        self.assertGreaterEqual(rep.double_log_or_lockout_bypass_events, 1)

    def test_18_reject_creative_look_or_dro_unlocked_when_pp11_active(self) -> None:
        rep_cl = evaluate_pp_scinetone_creativelook_dro_log_vault(
            PictureProfileScinetoneDroLogVaultSpec(
                configured_picture_profile="PP11",
                reported_picture_profile="PP11",
                reported_creative_look="ST",
                reported_dro="Off",
            )
        )
        self.assertFalse(rep_cl.passed)
        self.assertEqual(rep_cl.block_code, P287_BLOCKED_DOUBLE_LOG_OR_LOCKOUT_BYPASS)

        rep_dro = evaluate_pp_scinetone_creativelook_dro_log_vault(
            PictureProfileScinetoneDroLogVaultSpec(
                configured_picture_profile="PP11",
                reported_picture_profile="PP11",
                reported_creative_look="-",
                reported_dro="Auto",
            )
        )
        self.assertFalse(rep_dro.passed)
        self.assertEqual(rep_dro.block_code, P287_BLOCKED_DOUBLE_LOG_OR_LOCKOUT_BYPASS)

    def test_19_pplut1_to_4_movie_only_and_1080p_clamp_during_internal_rec(self) -> None:
        for lut in P287_PPLUT_MODES:
            rep_ok = evaluate_pp_scinetone_creativelook_dro_log_vault(
                PictureProfileScinetoneDroLogVaultSpec(
                    shooting_domain="Movie",
                    log_shooting="Off",
                    configured_picture_profile=lut,
                    reported_picture_profile=lut,
                    reported_creative_look="-",
                    reported_dro="Off",
                    hdmi_internal_recording=True,
                    configured_hdmi_resolution="2160p",
                    reported_hdmi_resolution="1080p",
                )
            )
            self.assertTrue(rep_ok.passed, f"{lut} Movie pass failed: {rep_ok.errors}")

            rep_still = evaluate_pp_scinetone_creativelook_dro_log_vault(
                PictureProfileScinetoneDroLogVaultSpec(
                    shooting_domain="Still",
                    log_shooting="Off",
                    configured_picture_profile=lut,
                    reported_picture_profile=lut,
                    reported_creative_look="-",
                    reported_dro="Off",
                    hdmi_internal_recording=False,
                    configured_hdmi_resolution="Auto",
                    reported_hdmi_resolution="Auto",
                )
            )
            self.assertFalse(rep_still.passed)
            self.assertEqual(rep_still.block_code, P287_BLOCKED_DOUBLE_LOG_OR_LOCKOUT_BYPASS)

            rep_2160 = evaluate_pp_scinetone_creativelook_dro_log_vault(
                PictureProfileScinetoneDroLogVaultSpec(
                    shooting_domain="Movie",
                    log_shooting="Off",
                    configured_picture_profile=lut,
                    reported_picture_profile=lut,
                    reported_creative_look="-",
                    reported_dro="Off",
                    hdmi_internal_recording=True,
                    configured_hdmi_resolution="2160p",
                    reported_hdmi_resolution="2160p",
                )
            )
            self.assertFalse(rep_2160.passed)
            self.assertEqual(rep_2160.block_code, P287_BLOCKED_DOUBLE_LOG_OR_LOCKOUT_BYPASS)
            self.assertGreaterEqual(rep_2160.pplut_1080p_clamp_bypass_events, 1)

    def test_20_different_set_for_still_mv_coupling_and_decoupling(self) -> None:
        rep_coupled = evaluate_pp_scinetone_creativelook_dro_log_vault(
            PictureProfileScinetoneDroLogVaultSpec(
                diff_set_pp_checked=False,
                movie_picture_profile="PP11",
                still_picture_profile="PP11",
            )
        )
        self.assertTrue(rep_coupled.passed)

        rep_bad_couple = evaluate_pp_scinetone_creativelook_dro_log_vault(
            PictureProfileScinetoneDroLogVaultSpec(
                diff_set_pp_checked=False,
                movie_picture_profile="PP11",
                still_picture_profile="Off",
            )
        )
        self.assertFalse(rep_bad_couple.passed)
        self.assertEqual(rep_bad_couple.block_code, P287_BLOCKED_DOUBLE_LOG_OR_LOCKOUT_BYPASS)
        self.assertTrue(any("Different Set" in e for e in rep_bad_couple.errors))

        rep_decoupled = evaluate_pp_scinetone_creativelook_dro_log_vault(
            PictureProfileScinetoneDroLogVaultSpec(
                diff_set_pp_checked=True,
                movie_picture_profile="PP8",
                still_picture_profile="Off",
            )
        )
        self.assertTrue(rep_decoupled.passed)

    def test_21_critical_reset_trap_pp_internal_and_diff_set_survive_both_resets(self) -> None:
        for action in ("Camera Settings Reset", "Initialize"):
            _, _, _, _, post_diff, post_int, post_lut = compute_expected_pillar50a_reset_state(
                pre_diff_set_pp_checked=True,
                pre_pp_internal_customized=True,
                pre_pplut_customized=True,
                reset_action=action,
                explicit_per_profile_pp_reset=False,
                explicit_diff_set_uncheck=False,
            )
            self.assertTrue(post_diff, f"{action} must NOT clear diff_set checkmark")
            self.assertTrue(post_int, f"{action} must NOT clear PP1..11 internal params")
            if action == "Initialize":
                self.assertFalse(post_lut, "Initialize resets PPLUT1..4")
            else:
                self.assertTrue(post_lut, "Camera Settings Reset preserves PPLUT1..4")

        # Hallucinating that Initialize cleared PP internal params or diff_set MUST fail!
        rep_halluc = evaluate_pp_scinetone_creativelook_dro_log_vault(
            PictureProfileScinetoneDroLogVaultSpec(
                reset_action="Initialize",
                pre_diff_set_pp_checked=True,
                pre_pp_internal_customized=True,
                pre_pplut_customized=True,
                explicit_per_profile_pp_reset=False,
                explicit_diff_set_uncheck=False,
                post_diff_set_pp_checked=False,
                post_pp_internal_customized=False,
                post_pplut_customized=False,
            )
        )
        self.assertFalse(rep_halluc.passed)
        self.assertEqual(rep_halluc.block_code, P287_BLOCKED_PP_INTERNAL_OR_DIFF_SET_RESET_TRAP)
        self.assertGreaterEqual(rep_halluc.pp_internal_reset_trap_violations, 1)

    def test_22_explicit_per_profile_pp_reset_and_diff_set_uncheck_restores_baseline(self) -> None:
        rep_ok = evaluate_pp_scinetone_creativelook_dro_log_vault(
            PictureProfileScinetoneDroLogVaultSpec(
                reset_action="Initialize",
                pre_diff_set_pp_checked=True,
                pre_pp_internal_customized=True,
                pre_pplut_customized=True,
                explicit_per_profile_pp_reset=True,
                explicit_diff_set_uncheck=True,
                post_diff_set_pp_checked=False,
                post_pp_internal_customized=False,
                post_pplut_customized=False,
            )
        )
        self.assertTrue(rep_ok.passed, rep_ok.errors)

    def test_23_fx6_baselook_pipeline_confusion_blocked(self) -> None:
        rep = evaluate_pp_scinetone_creativelook_dro_log_vault(
            PictureProfileScinetoneDroLogVaultSpec(
                pipeline_surface_model="FX6_BASE_LOOK_SCENE_FILE_PIPELINE",
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P287_BLOCKED_FX6_BASELOOK_CONFUSION)
        self.assertGreaterEqual(rep.fx6_baselook_confusion_events, 1)

    def test_24_pillar50a_slot1_vault_wp_and_tmp_overlay_and_h0_h3_guards(self) -> None:
        rep_slot1 = evaluate_pp_scinetone_creativelook_dro_log_vault(
            PictureProfileScinetoneDroLogVaultSpec(
                slot1_sdxc_wp_locked=False,
                slot1_vault_mutation_bytes=4096,
            )
        )
        self.assertFalse(rep_slot1.passed)
        self.assertEqual(rep_slot1.block_code, P287_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT)
        self.assertEqual(rep_slot1.slot1_vault_mutation_bytes, 4096)

        rep_overlay = evaluate_pp_scinetone_creativelook_dro_log_vault(
            PictureProfileScinetoneDroLogVaultSpec(overlay_dir="/setting/pp_override")
        )
        self.assertFalse(rep_overlay.passed)
        self.assertEqual(rep_overlay.block_code, P287_BLOCKED_PERSISTENT_OVERLAY_ESCAPE)

        rep_h3 = evaluate_pp_scinetone_creativelook_dro_log_vault(
            PictureProfileScinetoneDroLogVaultSpec(
                backup_bin_h3_sha256="f" * 64,
                tier0_surfaces_h0_h3_matched=15,
            )
        )
        self.assertFalse(rep_h3.passed)
        self.assertEqual(rep_h3.block_code, P287_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT)

    def test_25_pillar50a_invalid_enum_spec_rejected(self) -> None:
        rep = evaluate_pp_scinetone_creativelook_dro_log_vault(
            PictureProfileScinetoneDroLogVaultSpec(configured_picture_profile="PP99")
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P287_BLOCKED_INVALID_PILLAR50A_SPEC)

    def test_26_pillar50a_6_scenario_suite_passes_6_of_6(self) -> None:
        suite = run_pillar50a_pp_scinetone_creativelook_dro_6_scenario_suite()
        self.assertTrue(suite.passed)
        self.assertEqual(suite.status, P287_STATUS_VERIFIED_PILLAR_50A)
        self.assertEqual(suite.scenarios_passed, 6)
        self.assertEqual(suite.scenarios_total, 6)
        self.assertTrue(all(o.passed for o in suite.scenarios))
        self.assertEqual(sum(1 for o in suite.scenarios if o.expected_allowed), 2)
        self.assertEqual(sum(1 for o in suite.scenarios if not o.expected_allowed), 4)

    def test_27_pillar50a_factory_defaults_check_none_uses_safe_spec(self) -> None:
        rep = evaluate_pp_scinetone_creativelook_dro_log_vault(None)
        self.assertTrue(rep.passed)
        self.assertGreaterEqual(rep.matrix_states_checked, 40)

    # ------------------------------------------------------------------
    # 4. Pillar 50B — WB 2500K..9900K, Custom 1..3 CAMSET Exclusion & Metering Mode (28..44)
    # ------------------------------------------------------------------

    def test_28_pillar50b_default_safe_spec_passes(self) -> None:
        spec = build_default_safe_wb_camset_exclusion_metering_vault_spec()
        rep = evaluate_wb_camset_exclusion_and_metering_vault(spec)
        self.assertTrue(rep.passed, rep.errors)
        self.assertEqual(rep.status, P287_STATUS_VERIFIED_PILLAR_50B)
        self.assertIsNone(rep.block_code)
        self.assertTrue(rep.wb_modes_ctemp_and_shockless_verified)
        self.assertTrue(rep.cine_ei_awb_and_custom_setup_trap_verified)
        self.assertTrue(rep.custom_wb_camset_exclusion_and_reset_verified)
        self.assertTrue(rep.metering_6modes_desqueeze_face_spot_verified)
        self.assertTrue(rep.cine_ei_base_iso_mm_invariance_verified)
        self.assertTrue(rep.h0_equals_h3_verified)
        self.assertGreaterEqual(rep.matrix_states_checked, 40)
        self.assertEqual(rep.wb_cine_ei_awb_or_custom_setup_trap_events, 0)
        self.assertEqual(rep.wb_custom_camset_exclusion_drift_events, 0)
        self.assertEqual(rep.metering_desqueeze_or_cine_ei_base_iso_drift_events, 0)
        self.assertEqual(rep.slot1_vault_mutation_bytes, 0)

    def test_29_ctemp_range_2500k_to_9900k_in_100k_steps_plus_ab_gm_filters(self) -> None:
        valid_temps = list(range(2500, 10000, 100))
        self.assertEqual(len(valid_temps), 75)
        for k in (2500, 3200, 4300, 5600, 9900):
            for ab, gm in ((-7, -7), (0, 0), (7, 7)):
                rep = evaluate_wb_camset_exclusion_and_metering_vault(
                    WhiteBalanceCamsetExclusionAndMeteringVaultSpec(
                        wb_mode="C.Temp./Filter",
                        ctemp_kelvin=k,
                        ab_filter=ab,
                        gm_filter=gm,
                    )
                )
                self.assertTrue(rep.passed, f"CTemp {k}K ab={ab} gm={gm} failed: {rep.errors}")

        for bad_k, bad_ab, bad_gm in ((2400, 0, 0), (10000, 0, 0), (5550, 0, 0), (5500, 8, 0), (5500, 0, -8)):
            rep_bad = evaluate_wb_camset_exclusion_and_metering_vault(
                WhiteBalanceCamsetExclusionAndMeteringVaultSpec(
                    wb_mode="C.Temp./Filter",
                    ctemp_kelvin=bad_k,
                    ab_filter=bad_ab,
                    gm_filter=bad_gm,
                )
            )
            self.assertFalse(rep_bad.passed)
            self.assertEqual(rep_bad.block_code, P287_BLOCKED_WB_CUSTOM_CAMSET_EXCLUSION_DRIFT)

    def test_30_cine_ei_and_cine_ei_quick_block_awb_and_underwater_auto(self) -> None:
        for log_m in ("Cine EI", "Cine EI Quick"):
            for awb_m in ("Auto", "Underwater Auto"):
                _, wb_allowed, custom_trap, _, _, _, _, _ = compute_expected_wb_cine_ei_custom_guard(
                    log_shooting=log_m,
                    picture_profile="Off",
                    picture_profile_gamma="S-Log3",
                    requested_wb_mode=awb_m,
                    ctemp_kelvin=5600,
                    ab_filter=0,
                    gm_filter=0,
                    shockless_wb_setting="1 (Fast)",
                    custom_setup_attempted=False,
                    reset_action="NONE",
                    camset_load_attempted=False,
                    pre_custom_wb_memorized_dirty=False,
                    manual_custom_wb_reregistered=False,
                    pre_shutter_awb_lock="Off",
                )
                self.assertFalse(wb_allowed)
                self.assertFalse(custom_trap)

                rep = evaluate_wb_camset_exclusion_and_metering_vault(
                    WhiteBalanceCamsetExclusionAndMeteringVaultSpec(
                        log_shooting=log_m,
                        wb_mode=awb_m,
                    )
                )
                self.assertFalse(rep.passed)
                self.assertEqual(rep.block_code, P287_BLOCKED_WB_CINE_EI_AWB_OR_CUSTOM_SETUP_TRAP)
                self.assertGreaterEqual(rep.wb_cine_ei_awb_or_custom_setup_trap_events, 1)

    def test_31_flexible_iso_allows_awb_while_custom_setup_still_traps(self) -> None:
        _, wb_allowed, custom_trap, _, _, _, _, _ = compute_expected_wb_cine_ei_custom_guard(
            log_shooting="Flexible ISO",
            picture_profile="Off",
            picture_profile_gamma="S-Log3",
            requested_wb_mode="Auto",
            ctemp_kelvin=5600,
            ab_filter=0,
            gm_filter=0,
            shockless_wb_setting="1 (Fast)",
            custom_setup_attempted=True,
            reset_action="NONE",
            camset_load_attempted=False,
            pre_custom_wb_memorized_dirty=False,
            manual_custom_wb_reregistered=False,
            pre_shutter_awb_lock="Off",
        )
        self.assertTrue(wb_allowed)
        self.assertTrue(custom_trap)

        rep = evaluate_wb_camset_exclusion_and_metering_vault(
            WhiteBalanceCamsetExclusionAndMeteringVaultSpec(
                log_shooting="Flexible ISO",
                wb_mode="Auto",
                custom_setup_attempted=True,
                reported_custom_setup_error=True,
            )
        )
        self.assertTrue(rep.passed, rep.errors)

    def test_32_custom_setup_error_trap_under_log_or_slog3_or_pplut(self) -> None:
        trap_cases = (
            ("Cine EI", "Off", "S-Log3"),
            ("Cine EI Quick", "Off", "S-Log3"),
            ("Off", "PP8", "S-Log3"),
            ("Off", "PPLUT1", "PPLUT"),
            ("Off", "PPLUT4", "PPLUT"),
        )
        for log_m, pp_m, gamma_m in trap_cases:
            rep_fail = evaluate_wb_camset_exclusion_and_metering_vault(
                WhiteBalanceCamsetExclusionAndMeteringVaultSpec(
                    log_shooting=log_m,
                    picture_profile=pp_m,
                    picture_profile_gamma=gamma_m,
                    wb_mode="Custom 1",
                    custom_setup_attempted=True,
                    reported_custom_setup_error=False,
                )
            )
            self.assertFalse(rep_fail.passed)
            self.assertEqual(rep_fail.block_code, P287_BLOCKED_WB_CINE_EI_AWB_OR_CUSTOM_SETUP_TRAP)

            rep_ok = evaluate_wb_camset_exclusion_and_metering_vault(
                WhiteBalanceCamsetExclusionAndMeteringVaultSpec(
                    log_shooting=log_m,
                    picture_profile=pp_m,
                    picture_profile_gamma=gamma_m,
                    wb_mode="Custom 1",
                    custom_setup_attempted=True,
                    reported_custom_setup_error=True,
                )
            )
            self.assertTrue(rep_ok.passed, rep_ok.errors)

    def test_33_custom_1_to_3_survive_camera_reset_and_excluded_from_camset_slot1(self) -> None:
        # Custom 1..3 memorized WB survives Camera Settings Reset unless manually re-registered
        _, _, _, _, custom_preserved, camset_excludes, post_lock, _ = (
            compute_expected_wb_cine_ei_custom_guard(
                log_shooting="Off",
                picture_profile="PP11",
                picture_profile_gamma="S-Cinetone",
                requested_wb_mode="Custom 1",
                ctemp_kelvin=5600,
                ab_filter=0,
                gm_filter=0,
                shockless_wb_setting="1 (Fast)",
                custom_setup_attempted=False,
                reset_action="Camera Settings Reset",
                camset_load_attempted=True,
                pre_custom_wb_memorized_dirty=True,
                manual_custom_wb_reregistered=False,
                pre_shutter_awb_lock="Shutter Half Press",
            )
        )
        self.assertEqual(post_lock, "Shutter Half Press")
        self.assertTrue(custom_preserved)
        self.assertTrue(camset_excludes)

        # Initialize DOES clear Custom 1..3 memorized WB and Shutter AWB Lock
        _, _, _, _, custom_init, _, post_lock_init, _ = compute_expected_wb_cine_ei_custom_guard(
            log_shooting="Off",
            picture_profile="PP11",
            picture_profile_gamma="S-Cinetone",
            requested_wb_mode="Custom 1",
            ctemp_kelvin=5600,
            ab_filter=0,
            gm_filter=0,
            shockless_wb_setting="1 (Fast)",
            custom_setup_attempted=False,
            reset_action="Initialize",
            camset_load_attempted=True,
            pre_custom_wb_memorized_dirty=True,
            manual_custom_wb_reregistered=False,
            pre_shutter_awb_lock="Shutter Half Press",
        )
        self.assertEqual(post_lock_init, "Off")
        self.assertFalse(custom_init)

        # Expecting Save/Load Settings (CAMSET) on Slot 1 to save/restore Custom 1..3 MUST be blocked!
        rep_camset = evaluate_wb_camset_exclusion_and_metering_vault(
            WhiteBalanceCamsetExclusionAndMeteringVaultSpec(
                expect_camset_restores_custom_wb=True,
            )
        )
        self.assertFalse(rep_camset.passed)
        self.assertEqual(rep_camset.block_code, P287_BLOCKED_WB_CUSTOM_CAMSET_EXCLUSION_DRIFT)
        self.assertGreaterEqual(rep_camset.wb_custom_camset_exclusion_drift_events, 1)

    def test_34_manual_custom_wb_reregistration_after_camera_reset_restores_clean(self) -> None:
        rep = evaluate_wb_camset_exclusion_and_metering_vault(
            WhiteBalanceCamsetExclusionAndMeteringVaultSpec(
                wb_mode="Custom 2",
                reset_action="Camera Settings Reset",
                pre_custom_wb_memorized_dirty=True,
                manual_custom_wb_reregistered=True,
                post_custom_wb_memorized_dirty=False,
            )
        )
        self.assertTrue(rep.passed, rep.errors)

    def test_35_shutter_awb_lock_and_ael_w_shutter_non_resettable_on_camera_reset(self) -> None:
        rep_drift = evaluate_wb_camset_exclusion_and_metering_vault(
            WhiteBalanceCamsetExclusionAndMeteringVaultSpec(
                reset_action="Camera Settings Reset",
                pre_shutter_awb_lock="Shutter Half Press",
                post_shutter_awb_lock="Off",
            )
        )
        self.assertFalse(rep_drift.passed)
        self.assertEqual(rep_drift.block_code, P287_BLOCKED_WB_CUSTOM_CAMSET_EXCLUSION_DRIFT)

        rep_ael_drift = evaluate_wb_camset_exclusion_and_metering_vault(
            WhiteBalanceCamsetExclusionAndMeteringVaultSpec(
                reset_action="Camera Settings Reset",
                pre_ael_w_shutter="Off",
                post_ael_w_shutter="Auto",
            )
        )
        self.assertFalse(rep_ael_drift.passed)
        self.assertEqual(
            rep_ael_drift.block_code,
            P287_BLOCKED_METERING_DESQUEEZE_OR_CINE_EI_BASE_ISO_DRIFT,
        )

    def test_36_metering_all_6_modes_and_iauto_multi_lock(self) -> None:
        for mode in P287_METERING_6_MODES:
            rep = evaluate_wb_camset_exclusion_and_metering_vault(
                WhiteBalanceCamsetExclusionAndMeteringVaultSpec(
                    configured_metering_mode=mode,
                    reported_metering_mode=mode,
                )
            )
            self.assertTrue(rep.passed, f"Metering mode {mode} failed: {rep.errors}")

        eff_met, _, _, _, _, _ = compute_expected_metering_and_cine_ei_invariance(
            intelligent_auto=True,
            configured_metering_mode="Spot: Large",
            desqueeze_mode="Off",
            configured_face_priority="On",
            focus_area="Spot",
            active_tracking_running=False,
            configured_spot_point="Focus Point Link",
            log_shooting="Off",
            cine_ei_base_iso=800,
            pre_ael_w_shutter="Auto",
            reset_action="NONE",
        )
        self.assertEqual(eff_met, "Multi")

    def test_37_desqueeze_forces_face_priority_off(self) -> None:
        for dsq in ("1.3x", "1.6x", "2.0x"):
            rep_ok = evaluate_wb_camset_exclusion_and_metering_vault(
                WhiteBalanceCamsetExclusionAndMeteringVaultSpec(
                    desqueeze_mode=dsq,
                    configured_face_priority="On",
                    reported_face_priority="Off",
                )
            )
            self.assertTrue(rep_ok.passed, f"De-Squeeze {dsq} safe lockout failed: {rep_ok.errors}")

            rep_fail = evaluate_wb_camset_exclusion_and_metering_vault(
                WhiteBalanceCamsetExclusionAndMeteringVaultSpec(
                    desqueeze_mode=dsq,
                    configured_face_priority="On",
                    reported_face_priority="On",
                )
            )
            self.assertFalse(rep_fail.passed)
            self.assertEqual(
                rep_fail.block_code,
                P287_BLOCKED_METERING_DESQUEEZE_OR_CINE_EI_BASE_ISO_DRIFT,
            )

    def test_38_spot_metering_point_focus_link_only_under_spot_or_tracking_start(self) -> None:
        # Wide -> forces Center
        rep_wide_bad = evaluate_wb_camset_exclusion_and_metering_vault(
            WhiteBalanceCamsetExclusionAndMeteringVaultSpec(
                focus_area="Wide",
                configured_spot_point="Focus Point Link",
                reported_spot_point="Focus Point Link",
            )
        )
        self.assertFalse(rep_wide_bad.passed)
        self.assertEqual(
            rep_wide_bad.block_code,
            P287_BLOCKED_METERING_DESQUEEZE_OR_CINE_EI_BASE_ISO_DRIFT,
        )

        # Spot & Tracking start focus areas (prior to active tracking motion) allow Focus Point Link
        for link_area in ("Spot", "Expand Spot", "Tracking: Spot", "Tracking: Expand Spot"):
            rep_spot_ok = evaluate_wb_camset_exclusion_and_metering_vault(
                WhiteBalanceCamsetExclusionAndMeteringVaultSpec(
                    focus_area=link_area,
                    active_tracking_running=False,
                    configured_spot_point="Focus Point Link",
                    reported_spot_point="Focus Point Link",
                )
            )
            self.assertTrue(rep_spot_ok.passed, f"{link_area} failed: {rep_spot_ok.errors}")

        # Once active tracking is running, Spot Metering Point stays Center and does NOT follow tracker
        rep_trk_active = evaluate_wb_camset_exclusion_and_metering_vault(
            WhiteBalanceCamsetExclusionAndMeteringVaultSpec(
                focus_area="Tracking: Spot",
                active_tracking_running=True,
                configured_spot_point="Focus Point Link",
                reported_spot_point="Center",
            )
        )
        self.assertTrue(rep_trk_active.passed, rep_trk_active.errors)

    def test_39_cine_ei_base_iso_800_12800_invariant_passive_mm_only(self) -> None:
        for base_iso in (800, 12800):
            rep_ok = evaluate_wb_camset_exclusion_and_metering_vault(
                WhiteBalanceCamsetExclusionAndMeteringVaultSpec(
                    log_shooting="Cine EI",
                    wb_mode="Custom 1",
                    cine_ei_base_iso=base_iso,
                    configured_metering_mode="Highlight",
                    reported_metering_mode="Highlight",
                    metering_altered_cine_ei_gain=False,
                )
            )
            self.assertTrue(rep_ok.passed, f"Cine EI Base ISO {base_iso} failed: {rep_ok.errors}")

        rep_bad_iso = evaluate_wb_camset_exclusion_and_metering_vault(
            WhiteBalanceCamsetExclusionAndMeteringVaultSpec(
                log_shooting="Cine EI",
                wb_mode="Custom 1",
                cine_ei_base_iso=3200,
                metering_altered_cine_ei_gain=True,
            )
        )
        self.assertFalse(rep_bad_iso.passed)
        self.assertEqual(
            rep_bad_iso.block_code,
            P287_BLOCKED_METERING_DESQUEEZE_OR_CINE_EI_BASE_ISO_DRIFT,
        )
        self.assertGreaterEqual(rep_bad_iso.metering_desqueeze_or_cine_ei_base_iso_drift_events, 1)

    def test_40_shockless_wb_all_modes_supported(self) -> None:
        for swb in P287_SHOCKLESS_WB_MODES:
            rep = evaluate_wb_camset_exclusion_and_metering_vault(
                WhiteBalanceCamsetExclusionAndMeteringVaultSpec(
                    reset_action="NONE",
                    shockless_wb_setting=swb,
                    post_shockless_wb_setting=swb,
                )
            )
            self.assertTrue(rep.passed, f"Shockless WB {swb} failed: {rep.errors}")

    def test_41_pillar50b_slot1_firewall_and_overlay_and_h0_h3_guards(self) -> None:
        rep_slot1 = evaluate_wb_camset_exclusion_and_metering_vault(
            WhiteBalanceCamsetExclusionAndMeteringVaultSpec(
                requested_vault_slot=1,
                requested_vault_action="DELETE_SINGLE",
            )
        )
        self.assertFalse(rep_slot1.passed)
        self.assertEqual(rep_slot1.block_code, P287_BLOCKED_SLOT1_VAULT_FORMAT_OR_MUTATION)
        self.assertEqual(rep_slot1.slot1_vault_mutation_bytes, 4096)

        rep_ov = evaluate_wb_camset_exclusion_and_metering_vault(
            WhiteBalanceCamsetExclusionAndMeteringVaultSpec(overlay_dir="/lib/overlay_wb")
        )
        self.assertFalse(rep_ov.passed)
        self.assertEqual(rep_ov.block_code, P287_BLOCKED_PERSISTENT_OVERLAY_ESCAPE)

        rep_h3 = evaluate_wb_camset_exclusion_and_metering_vault(
            WhiteBalanceCamsetExclusionAndMeteringVaultSpec(
                backup_bin_h3_sha256="a" * 64,
                tier0_surfaces_h0_h3_matched=14,
            )
        )
        self.assertFalse(rep_h3.passed)
        self.assertEqual(rep_h3.block_code, P287_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT)

    def test_42_pillar50b_invalid_enum_spec_rejected(self) -> None:
        rep = evaluate_wb_camset_exclusion_and_metering_vault(
            WhiteBalanceCamsetExclusionAndMeteringVaultSpec(configured_metering_mode="MatrixBogus")
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P287_BLOCKED_INVALID_PILLAR50B_SPEC)

    def test_43_pillar50b_6_scenario_suite_passes_6_of_6(self) -> None:
        suite = run_pillar50b_wb_camset_exclusion_metering_6_scenario_suite()
        self.assertTrue(suite.passed)
        self.assertEqual(suite.status, P287_STATUS_VERIFIED_PILLAR_50B)
        self.assertEqual(suite.scenarios_passed, 6)
        self.assertEqual(suite.scenarios_total, 6)
        self.assertTrue(all(o.passed for o in suite.scenarios))
        self.assertEqual(sum(1 for o in suite.scenarios if o.expected_allowed), 2)
        self.assertEqual(sum(1 for o in suite.scenarios if not o.expected_allowed), 4)

    def test_44_pillar50b_none_spec_defaults_to_safe(self) -> None:
        rep = evaluate_wb_camset_exclusion_and_metering_vault(None)
        self.assertTrue(rep.passed)
        self.assertGreaterEqual(rep.matrix_states_checked, 40)

    # ------------------------------------------------------------------
    # 5. Pillar 50 Combined & Standalone Suite + Tamper Propagation (45..52)
    # ------------------------------------------------------------------

    def test_45_combined_verify_function_and_symmetry_alias_clean_room(self) -> None:
        r1 = verify_pp_scinetone_creativelook_dro_wb_metering_and_vault(force_clean_room=True)
        r2 = verify_pp_scinetone_creativelook_dro_wb_metering_vault(force_clean_room=True)
        self.assertTrue(r1.all_passed)
        self.assertTrue(r2.all_passed)
        self.assertEqual(r1.status, P287_STATUS_VERIFIED_PILLAR50_SUITE)
        self.assertEqual(r1.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(r1.pp_scinetone_dro_report.digest_sha256, r2.pp_scinetone_dro_report.digest_sha256)
        self.assertEqual(r1.wb_metering_report.digest_sha256, r2.wb_metering_report.digest_sha256)
        self.assertEqual(r1.raw_firmware_bytes_leaked, 0)

    def test_46_standalone_suite_clean_room_and_active_modes(self) -> None:
        st_cr = run_pillar50_standalone_suite(force_clean_room=True)
        self.assertTrue(st_cr.all_passed)
        self.assertEqual(st_cr.status, P287_STATUS_VERIFIED_PILLAR50_SUITE)
        self.assertEqual(st_cr.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(st_cr.pillar_50a_pp_scinetone_creativelook_dro_vault.scenarios_passed, 6)
        self.assertEqual(st_cr.pillar_50b_wb_camset_exclusion_metering_vault.scenarios_passed, 6)
        self.assertTrue(st_cr.slot1_format_hard_locked)
        self.assertEqual(st_cr.slot1_vault_mutation_bytes, 0)
        self.assertEqual(st_cr.raw_firmware_bytes_leaked, 0)

        st_act = run_pillar50_standalone_suite()
        self.assertTrue(st_act.all_passed)
        self.assertEqual(st_act.status, P287_STATUS_VERIFIED_PILLAR50_SUITE)

    def test_47_donor_failure_propagates_to_pillar50_standalone(self) -> None:
        bad_snap = inspect_phase287_donors_readonly(force_clean_room=True)
        bad_snap = replace(bad_snap, all_donors_present=False, under_0_20s_budget=False)
        with mock.patch.object(p287, "inspect_phase287_donors_readonly", return_value=bad_snap):
            st = run_pillar50_standalone_suite(force_clean_room=True)
            self.assertFalse(st.all_passed)
            self.assertTrue(any("donor" in e.lower() for e in st.errors))

    def test_48_safety_tamper_blocks_both_50a_and_50b(self) -> None:
        with mock.patch.object(p287, "PHYSICAL_DEVICE_WRITES", 1):
            errs = p287._safety_invariant_errors()
            self.assertTrue(any("PHYSICAL_DEVICE_WRITES" in e for e in errs))
            r50a = evaluate_pp_scinetone_creativelook_dro_log_vault()
            self.assertFalse(r50a.passed)
            self.assertEqual(r50a.block_code, P287_BLOCKED_SAFETY_POLICY_VIOLATION)
            r50b = evaluate_wb_camset_exclusion_and_metering_vault()
            self.assertFalse(r50b.passed)
            self.assertEqual(r50b.block_code, P287_BLOCKED_SAFETY_POLICY_VIOLATION)

    def test_49_non_slot1_write_protection_cannot_save_if_slot1_unprotected(self) -> None:
        rep = evaluate_wb_camset_exclusion_and_metering_vault(
            WhiteBalanceCamsetExclusionAndMeteringVaultSpec(
                slot1_sdxc_wp_locked=False,
                slot1_format_hard_locked=False,
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P287_BLOCKED_SLOT1_VAULT_FORMAT_OR_MUTATION)

    def test_50_fx6_wb_presets_and_shooting_modes_catalog_pinned(self) -> None:
        self.assertEqual(p287.P287_FX6_SHOOTING_MODES, ("Custom", "Cine EI", "Cine EI Quick"))
        self.assertEqual(p287.P287_FX6_WB_CINE_EI_PRESETS_K, (3200, 4300, 5500))
        self.assertEqual(P287_FX6_WB_MODES, ("Memory A", "Memory B", "Preset", "ATW"))

    def test_51_p287_p50_json_roundtrip_strict_allow_nan_false(self) -> None:
        st = run_pillar50_standalone_suite(force_clean_room=True)
        dumped = json.dumps(st.to_dict(), ensure_ascii=False, sort_keys=True, allow_nan=False)
        parsed = json.loads(dumped)
        self.assertEqual(parsed["schema"], PHASE287_SCHEMA)
        self.assertTrue(parsed["all_passed"])
        self.assertEqual(parsed["raw_firmware_bytes_leaked"], 0)

    def test_52_p287_donor_read_latency_with_ci_headroom(self) -> None:
        snap = inspect_phase287_donors_readonly()
        ceiling = 15.0 if _is_ci() else P287_DONOR_INSPECT_BUDGET_SECONDS
        self.assertLess(snap.elapsed_seconds, ceiling)

    # ------------------------------------------------------------------
    # 6. Unified 50/50 Recovery Master Aggregator (53..65)
    # ------------------------------------------------------------------

    def test_53_master_50pillar_clean_room_passes_50_of_50(self) -> None:
        rep = evaluate_realhw_50pillar_recovery_master(force_clean_room=True)
        self.assertTrue(rep.all_passed, rep.errors)
        self.assertEqual(rep.status, P287_STATUS_VERIFIED_50OF50_AGGREGATOR)
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertGreaterEqual(rep.pillar_count, 50)
        self.assertEqual(rep.pillars_passed, rep.pillar_count)
        self.assertEqual(rep.failed_pillars, ())
        self.assertEqual(len(rep.pillars), rep.pillar_count)
        self.assertTrue(rep.under_6s_budget)
        self.assertTrue(rep.nominal_under_4_0s)
        ceiling = 15.0 if _is_ci() else P287_FAST_CLI_BUDGET_SECONDS
        self.assertLess(rep.elapsed_seconds, ceiling)
        if not _is_ci():
            self.assertTrue(rep.under_2_2s_fast_cli_budget)
            self.assertTrue(rep.under_2_5s_fast_cli_budget)

    def test_54_master_50pillar_active_mode_passes_and_under_budget(self) -> None:
        rep = evaluate_realhw_50pillar_recovery_master()
        self.assertTrue(rep.all_passed, rep.errors)
        self.assertEqual(rep.status, P287_STATUS_VERIFIED_50OF50_AGGREGATOR)
        self.assertGreaterEqual(rep.pillar_count, 50)
        self.assertEqual(rep.pillars_passed, rep.pillar_count)
        self.assertEqual(rep.failed_pillars, ())
        ceiling = 15.0 if _is_ci() else P287_FAST_CLI_BUDGET_SECONDS
        self.assertLess(rep.elapsed_seconds, ceiling)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)
        self.assertEqual(rep.physical_device_writes, 0)
        self.assertFalse(rep.hardware_live_attachment_authorized)

    def test_55_master_50pillar_aliases_consistent(self) -> None:
        r1 = evaluate_realhw_50pillar_recovery_master(force_clean_room=True)
        r2 = evaluate_50pillar_recovery_master(force_clean_room=True)
        r3 = verify_50pillar_recovery_suite(force_clean_room=True)
        self.assertEqual(r1.master_50pillar_sha256, r2.master_50pillar_sha256)
        self.assertEqual(r2.master_50pillar_sha256, r3.master_50pillar_sha256)
        self.assertGreaterEqual(r1.pillars_passed, 50)

    def test_56_master_50pillar_preserves_all_upstream_safety_and_reality_metrics(self) -> None:
        rep = evaluate_realhw_50pillar_recovery_master(force_clean_room=True)
        # Pillar 50 counters
        self.assertEqual(rep.double_log_or_lockout_bypass_events, 0)
        self.assertEqual(rep.pplut_1080p_clamp_bypass_events, 0)
        self.assertEqual(rep.pp_internal_reset_trap_violations, 0)
        self.assertEqual(rep.fx6_baselook_confusion_events, 0)
        self.assertEqual(rep.wb_cine_ei_awb_or_custom_setup_trap_events, 0)
        self.assertEqual(rep.wb_custom_camset_exclusion_drift_events, 0)
        self.assertEqual(rep.metering_desqueeze_or_cine_ei_base_iso_drift_events, 0)
        self.assertEqual(rep.slot1_vault_mutation_bytes, 0)
        self.assertTrue(rep.slot1_format_hard_locked)
        # Pillars 1..49 preserved invariants
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

    def test_57_master_50pillar_fault_injection_pillar_50(self) -> None:
        rep = evaluate_realhw_50pillar_recovery_master(
            force_clean_room=True,
            fault_inject_pillar="pillar_50_pp_scinetone_creativelook_dro_wb_metering_vault",
        )
        self.assertFalse(rep.all_passed)
        self.assertEqual(rep.pillars_passed, rep.pillar_count - 1)
        self.assertEqual(
            rep.failed_pillars,
            ("pillar_50_pp_scinetone_creativelook_dro_wb_metering_vault",),
        )
        self.assertEqual(rep.status, p287.P287_STATUS_FAIL_50OF50_AGGREGATOR)

    def test_58_master_50pillar_fault_injection_pillar_49_and_pillar_01(self) -> None:
        for pid in (
            MASTER_50_PILLAR_IDS[0],
            "pillar_49_usb_mode_hdmi_info_protect_network_reset_vault",
        ):
            rep = evaluate_realhw_50pillar_recovery_master(
                force_clean_room=True,
                fault_inject_pillar=pid,
            )
            self.assertFalse(rep.all_passed)
            self.assertEqual(rep.pillars_passed, rep.pillar_count - 1)
            self.assertEqual(rep.failed_pillars, (pid,))

    def test_59_master_50pillar_unknown_fault_inject_pillar_raises(self) -> None:
        with self.assertRaises(ValueError):
            evaluate_realhw_50pillar_recovery_master(
                force_clean_room=True,
                fault_inject_pillar="pillar_99_nonexistent",
            )

    def test_60_master_50pillar_upstream_violation_detected(self) -> None:
        m49 = evaluate_realhw_49pillar_recovery_master(force_clean_room=True)
        bad_m49 = replace(m49, slot1_format_hard_locked=False)
        with mock.patch.object(
            p287,
            "evaluate_realhw_49pillar_recovery_master",
            return_value=bad_m49,
        ):
            rep = evaluate_realhw_50pillar_recovery_master(force_clean_room=True)
            self.assertFalse(rep.all_passed)
            self.assertTrue(any("slot1_format_hard_locked" in e for e in rep.errors))

    def test_61_master_50pillar_p50_violation_detected(self) -> None:
        p50 = run_pillar50_standalone_suite(force_clean_room=True)
        bad_p50 = replace(p50, double_log_or_lockout_bypass_events=1)
        with mock.patch.object(p287, "run_pillar50_standalone_suite", return_value=bad_p50):
            rep = evaluate_realhw_50pillar_recovery_master(force_clean_room=True)
            self.assertFalse(rep.all_passed)
            self.assertTrue(any("double_log_or_lockout_bypass_events" in e for e in rep.errors))

    def test_62_master_50pillar_safety_tamper_raises(self) -> None:
        with mock.patch.object(p287, "RAW_FIRMWARE_BYTES_LEAKED", 1):
            with self.assertRaises(ValueError):
                evaluate_realhw_50pillar_recovery_master(force_clean_room=True)

    def test_63_pillar_49_backward_compatibility_still_49_of_49(self) -> None:
        rep49 = evaluate_realhw_49pillar_recovery_master(force_clean_room=True)
        self.assertTrue(rep49.all_passed)
        self.assertGreaterEqual(rep49.pillar_count, 49)
        self.assertEqual(rep49.pillars_passed, rep49.pillar_count)

    def test_64_fx3_recovery_package_exports_all_pillar50_symbols(self) -> None:
        for sym in p287.__all__:
            self.assertTrue(hasattr(fx3_recovery, sym), f"fx3_recovery missing export {sym}")
            self.assertIn(sym, fx3_recovery.__all__, f"fx3_recovery.__all__ missing {sym}")
        self.assertIn(
            "realhw_50pillar_pp_scinetone_creativelook_dro_wb_metering_vault_verifier",
            fx3_recovery.__all__,
        )

    def test_65_master_50pillar_json_serialization_no_nan(self) -> None:
        rep = evaluate_realhw_50pillar_recovery_master(force_clean_room=True)
        text = json.dumps(rep.to_dict(), ensure_ascii=False, sort_keys=True, allow_nan=False)
        data = json.loads(text)
        self.assertEqual(data["schema"], PHASE287_SCHEMA)
        self.assertGreaterEqual(data["pillar_count"], 50)
        self.assertEqual(data["pillars_passed"], data["pillar_count"])
        self.assertTrue(data["all_passed"])

    # ------------------------------------------------------------------
    # 7. CLI Subcommands & Cross-Platform CI Subprocess Portability (66..78)
    # ------------------------------------------------------------------

    def test_66_cli_standalone_json_clean_room(self) -> None:
        buf = io.StringIO()
        with mock.patch.object(
            sys,
            "argv",
            [
                "fx3_recovery",
                "verify-pp-scinetone-wb-metering-vault",
                "--clean-room",
                "--json",
            ],
        ):
            with redirect_stdout(buf):
                rc = cli_main.main()
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())
        self.assertTrue(payload["all_passed"])
        self.assertEqual(payload["status"], P287_STATUS_VERIFIED_PILLAR50_SUITE)
        self.assertEqual(payload["verification_mode"], "CLEAN_ROOM_SYNTHETIC")

    def test_67_cli_50pillar_master_json_clean_room(self) -> None:
        buf = io.StringIO()
        with mock.patch.object(
            sys,
            "argv",
            ["fx3_recovery", "verify-50pillar-recovery", "--clean-room", "--json"],
        ):
            with redirect_stdout(buf):
                rc = cli_main.main()
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())
        self.assertTrue(payload["all_passed"])
        self.assertGreaterEqual(payload["pillar_count"], 50)
        self.assertEqual(payload["pillars_passed"], payload["pillar_count"])
        self.assertEqual(payload["status"], P287_STATUS_VERIFIED_50OF50_AGGREGATOR)

    def test_68_cli_50pillar_master_out_dir_repo_local_cleaned_in_finally(self) -> None:
        work_tests = _repo_root() / "work" / "_tests"
        work_tests.mkdir(parents=True, exist_ok=True)
        out_root = Path(tempfile.mkdtemp(prefix="p287_cli_", dir=str(work_tests)))
        out_dir = out_root / "master50"
        try:
            buf = io.StringIO()
            with mock.patch.object(
                sys,
                "argv",
                ["fx3_recovery", "verify-50pillar-recovery", "--clean-room", "--out", str(out_dir), "--json"],
            ):
                with redirect_stdout(buf):
                    rc = cli_main.main()
            self.assertEqual(rc, 0)
            out_file = out_dir / "50pillar-recovery-master-report.json"
            self.assertTrue(out_file.is_file())
            written = json.loads(out_file.read_text(encoding="utf-8"))
            self.assertGreaterEqual(written["pillars_passed"], 50)
        finally:
            shutil.rmtree(out_root, ignore_errors=True)

    def test_69_cli_standalone_out_dir_repo_local_cleaned_in_finally(self) -> None:
        work_tests = _repo_root() / "work" / "_tests"
        work_tests.mkdir(parents=True, exist_ok=True)
        out_root = Path(tempfile.mkdtemp(prefix="p287_p50_out_", dir=str(work_tests)))
        out_dir = out_root / "pillar50"
        try:
            buf = io.StringIO()
            with mock.patch.object(
                sys,
                "argv",
                [
                    "fx3_recovery",
                    "verify-pp-scinetone-wb-metering-vault",
                    "--clean-room",
                    "--out",
                    str(out_dir),
                    "--json",
                ],
            ):
                with redirect_stdout(buf):
                    rc = cli_main.main()
            self.assertEqual(rc, 0)
            out_file = out_dir / "pillar50-pp-scinetone-wb-metering-vault-report.json"
            self.assertTrue(out_file.is_file())
            written = json.loads(out_file.read_text(encoding="utf-8"))
            self.assertTrue(written["all_passed"])
        finally:
            shutil.rmtree(out_root, ignore_errors=True)

    def test_70_cli_subprocess_sys_executable_both_modes(self) -> None:
        adapter_dir = _repo_root() / "outputs" / "fx3-recovery-adapter"
        env_base = dict(os.environ)
        env_base["PYTHONDONTWRITEBYTECODE"] = "1"
        env_base["PYTHONPATH"] = str(adapter_dir)

        proc_active = subprocess.run(
            [sys.executable, "-B", "-m", "fx3_recovery", "verify-50pillar-recovery", "--json"],
            cwd=str(_repo_root()),
            env=env_base,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc_active.returncode, 0, proc_active.stderr)
        data_active = json.loads(proc_active.stdout)
        self.assertTrue(data_active["all_passed"])
        self.assertGreaterEqual(data_active["pillars_passed"], 50)

        env_clean = dict(env_base)
        env_clean[P287_ENV_CLEAN_ROOM_TEST] = "1"
        proc_clean = subprocess.run(
            [sys.executable, "-B", "-m", "fx3_recovery", "verify-50pillar-recovery", "--clean-room", "--json"],
            cwd=str(_repo_root()),
            env=env_clean,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc_clean.returncode, 0, proc_clean.stderr)
        data_clean = json.loads(proc_clean.stdout)
        self.assertEqual(data_clean["verification_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertGreaterEqual(data_clean["pillars_passed"], 50)

    def test_71_cli_human_readable_text_output_both_commands(self) -> None:
        b1 = io.StringIO()
        with mock.patch.object(
            sys,
            "argv",
            ["fx3_recovery", "verify-pp-scinetone-wb-metering-vault", "--clean-room"],
        ):
            with redirect_stdout(b1):
                rc1 = cli_main.main()
        self.assertEqual(rc1, 0)
        t1 = b1.getvalue()
        self.assertIn("pillar_50a=6/6", t1)
        self.assertIn("pillar_50b=6/6", t1)
        self.assertIn("slot1_format_hard_locked=True", t1)

        b2 = io.StringIO()
        with mock.patch.object(
            sys,
            "argv",
            ["fx3_recovery", "verify-50pillar-recovery", "--clean-room"],
        ):
            with redirect_stdout(b2):
                rc2 = cli_main.main()
        self.assertEqual(rc2, 0)
        t2 = b2.getvalue()
        self.assertIn("pillars=", t2)
        self.assertIn("all_passed=True", t2)
        self.assertIn("raw_firmware_bytes_leaked=0", t2)

    def test_72_cli_help_parses_without_python314_argparse_percent_errors(self) -> None:
        adapter_dir = _repo_root() / "outputs" / "fx3-recovery-adapter"
        env_base = dict(os.environ)
        env_base["PYTHONDONTWRITEBYTECODE"] = "1"
        env_base["PYTHONPATH"] = str(adapter_dir)
        for subcmd in ("--help", "verify-pp-scinetone-wb-metering-vault --help", "verify-50pillar-recovery --help"):
            proc = subprocess.run(
                [sys.executable, "-B", "-m", "fx3_recovery", *subcmd.split()],
                cwd=str(_repo_root()),
                env=env_base,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_73_cli_returns_nonzero_on_pillar50_failure(self) -> None:
        failed_st = replace(
            run_pillar50_standalone_suite(force_clean_room=True),
            all_passed=False,
            status=p287.P287_STATUS_FAIL_PILLAR50_SUITE,
        )
        with mock.patch.object(cli_main, "run_pillar50_standalone_suite", return_value=failed_st):
            buf = io.StringIO()
            with mock.patch.object(
                sys,
                "argv",
                ["fx3_recovery", "verify-pp-scinetone-wb-metering-vault", "--clean-room", "--json"],
            ):
                with redirect_stdout(buf):
                    rc = cli_main.main()
            self.assertEqual(rc, 2)

    def test_74_cli_returns_nonzero_on_50pillar_master_failure(self) -> None:
        failed_m = replace(
            evaluate_realhw_50pillar_recovery_master(force_clean_room=True),
            all_passed=False,
            status=p287.P287_STATUS_FAIL_50OF50_AGGREGATOR,
        )
        with mock.patch.object(cli_main, "verify_50pillar_recovery_suite", return_value=failed_m):
            buf = io.StringIO()
            with mock.patch.object(
                sys,
                "argv",
                ["fx3_recovery", "verify-50pillar-recovery", "--clean-room", "--json"],
            ):
                with redirect_stdout(buf):
                    rc = cli_main.main()
            self.assertEqual(rc, 2)

    def test_75_still_and_movie_pp_all_modes_covered_by_validator(self) -> None:
        for pp in P287_PP_1_TO_11:
            rep = evaluate_pp_scinetone_creativelook_dro_log_vault(
                PictureProfileScinetoneDroLogVaultSpec(
                    shooting_domain="Still",
                    log_shooting="Off",
                    configured_picture_profile=pp,
                    movie_picture_profile=pp,
                    still_picture_profile=pp,
                    reported_picture_profile=pp,
                    reported_creative_look="-",
                    reported_dro="Off",
                )
            )
            self.assertTrue(rep.passed, f"{pp} failed: {rep.errors}")

    def test_76_creative_look_all_10_presets_and_custom_boxes_pass_when_pp_off(self) -> None:
        for cl in P287_CREATIVE_LOOK_10_PRESETS + P287_CREATIVE_LOOK_CUSTOM_SLOTS:
            rep = evaluate_pp_scinetone_creativelook_dro_log_vault(
                PictureProfileScinetoneDroLogVaultSpec(
                    shooting_domain="Movie",
                    log_shooting="Off",
                    configured_picture_profile="Off",
                    movie_picture_profile="Off",
                    still_picture_profile="Off",
                    configured_creative_look=cl,
                    reported_picture_profile="Off",
                    reported_creative_look=cl,
                    reported_dro="Auto",
                )
            )
            self.assertTrue(rep.passed, f"Creative Look {cl} failed when PP=Off: {rep.errors}")

    def test_77_wb_all_fixed_and_custom_modes_supported_in_cine_ei(self) -> None:
        cine_ei_valid_wb = [m for m in P287_WB_ALL_MODES if m not in ("Auto", "Underwater Auto")]
        for wb in cine_ei_valid_wb:
            rep = evaluate_wb_camset_exclusion_and_metering_vault(
                WhiteBalanceCamsetExclusionAndMeteringVaultSpec(
                    log_shooting="Cine EI",
                    wb_mode=wb,
                )
            )
            self.assertTrue(rep.passed, f"WB {wb} failed in Cine EI: {rep.errors}")

    def test_78_no_raw_firmware_bytes_or_usb_tx_anywhere_in_module(self) -> None:
        snap = inspect_phase287_donors_readonly()
        st = run_pillar50_standalone_suite(force_clean_room=True)
        m50 = evaluate_realhw_50pillar_recovery_master(force_clean_room=True)
        self.assertEqual(snap.raw_firmware_bytes_leaked, 0)
        self.assertEqual(st.raw_firmware_bytes_leaked, 0)
        self.assertEqual(m50.raw_firmware_bytes_leaked, 0)
        self.assertEqual(st.passive_tx_bytes_emitted, 0)
        self.assertEqual(m50.passive_tx_bytes_emitted, 0)


if __name__ == "__main__":
    unittest.main()
