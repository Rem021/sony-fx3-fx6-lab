"""Dual-mode unit tests (72 cases) for Phase 284 (`preflight-pp-scinetone-wb-metering-and-shutter-type`):
9th Physical Bench & Pre-Shoot Readiness Verifier across Waves 48-49 check groups (`A..D`).

Runs deterministically across `LOCAL_DONOR_O_RDONLY`, `FX3_CLEAN_ROOM_TEST=1`, and
`FX3_FX6_FORCE_CLEAN_ROOM=1` modes with zero `.pyc` emission, zero persistent writes,
and cross-platform CI (`sys.executable` + `GITHUB_ACTIONS` timing headroom).
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import unittest
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[3]
for _rel in (
    "outputs/fx6-on-fx3-closure",
    "outputs/fx3-safety",
    "outputs/fx3-recovery-adapter",
    "outputs/fx3-firmware-lab",
    "outputs/fx3-vm",
):
    _cand = str(REPO_ROOT / _rel)
    if _cand not in sys.path:
        sys.path.insert(0, _cand)

import fx6_closure  # noqa: E402
from fx6_closure.__main__ import main as cli_main  # noqa: E402
from fx6_closure.realhw_card_insert_readiness_verifier import (  # noqa: E402
    GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT,
    GO_NO_GO_DRY_RUN_SIMULATED_READY,
)
from fx6_closure.realhw_sd_stageb_bundle_and_uninstaller import (  # noqa: E402
    DEFAULT_TARGET_BODY_SERIAL,
    DEFAULT_TARGET_EMMC_CID,
)
from fx6_closure.realhw_pp_scinetone_wb_metering_and_shutter_type_verifier import (  # noqa: E402
    P284_ACTIVE_LOG_SHOOTING_MODES,
    P284_AEL_WITH_SHUTTER_RESID16_HEX,
    P284_AF_LOCK_APERTURE_THRESHOLD_F,
    P284_CHECK_GROUP_A_ID,
    P284_CHECK_GROUP_B_ID,
    P284_CHECK_GROUP_C_ID,
    P284_CHECK_GROUP_D_ID,
    P284_CINE_EI_BASE_ISOS,
    P284_COLOR_SPACE_BKID,
    P284_COLOR_SPACE_RESID16_HEX,
    P284_COLOR_SPACE_RESIDS,
    P284_CONT_HIP_MAX_FPS,
    P284_CONT_HIP_RESID16_HEX,
    P284_CREATIVE_LOOK_BKID,
    P284_CREATIVE_LOOK_DEFAULT,
    P284_CREATIVE_LOOK_LOCKED_DASH,
    P284_CREATIVE_LOOK_RESID16_HEX,
    P284_CREATIVE_LOOK_TEN_PRESETS,
    P284_DEFAULT_STILL_PREFIX,
    P284_DIFF_SET_BKID,
    P284_DIFF_SET_RESID16_HEX,
    P284_DISPLAY_LUT_RESID16_HEX,
    P284_DORMANT_LOSSLESS_COMP_RESID16_HEX,
    P284_DORMANT_LOSSLESS_RAW_OPTIONS,
    P284_DRIVE_EIGHT_MODES,
    P284_DRIVE_MODE_BKID,
    P284_DRIVE_MODE_RESID16_HEX,
    P284_DRO_BKID,
    P284_DRO_RESID16_HEX,
    P284_DRO_VALID_MODES,
    P284_E_FRONT_CURTAIN_BKID,
    P284_E_FRONT_CURTAIN_RESID16_HEX,
    P284_ELECTRONIC_SHUTTER_FIVE_LOCKOUTS,
    P284_FACE_PRIORITY_MULTI_METERING_RESID16_HEX,
    P284_FLASH_SYNC_RESID16_HEX,
    P284_FORBIDDEN_SHUTTER_TYPE_AUTO,
    P284_FX3_RAW_OPTION_RESIDS,
    P284_FX3_RAW_TWO_OPTIONS,
    P284_FX3_SHUTTER_TWO_TYPES,
    P284_FX3_SHUTTER_TYPE_RESIDS,
    P284_GA_ERR_CREATIVE_LOOK_DRO_OR_LOG_LOCKOUT,
    P284_GA_ERR_MODEL_OR_FW_FLOOR,
    P284_GA_ERR_PP11_SCINETONE_OR_DIFF_SET_COUPLING,
    P284_GA_ERR_PP_INTERNAL_RESET_TRAP_OR_DIFF_SET_PERSISTENCE,
    P284_GA_ERR_PPLUT_STILL_OR_1080P_HDMI_CLAMP,
    P284_GB_ERR_CUSTOM_WB_RESET_OR_CAMSET_EXCLUSION,
    P284_GB_ERR_METERING_6MODE_FACE_DESQUEEZE_OR_MM_BASE_ISO,
    P284_GB_ERR_WB_CINE_EI_OR_CUSTOM_SETUP_TRAP,
    P284_GB_ERR_WB_RANGE_OR_NON_RESETTABLE_LOCK_PERSISTENCE,
    P284_GC_ERR_COLOR_SPACE_OR_DCF20_ADOBERGB_UNDERSCORE_PREFIX,
    P284_GC_ERR_HLG_STILL_PREREQ_OR_LOCKOUT_VIOLATED,
    P284_GC_ERR_RAW_2OPTION_OR_DORMANT_LOSSLESS_COMP_SPOOF,
    P284_GD_ERR_DRIVE_HIP_10FPS_OR_F11_AF_LOCK_OR_NR_RULE,
    P284_GD_ERR_FLASH_SYNC_1_250_OR_ELECTRONIC_5LOCKOUT,
    P284_GD_ERR_H0_H3_IMMUTABILITY_DRIFT,
    P284_GD_ERR_SHUTTER_TYPE_2OPTION_NO_AUTO_OR_SILENT_LOCK,
    P284_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID,
    P284_GO_NO_GO_BLOCKED_PP_SCINETONE_WB_METERING_SHUTTER_TYPE_FAILURE,
    P284_GO_NO_GO_PP_SCINETONE_WB_METERING_SHUTTER_TYPE_VERIFIED,
    P284_HIGH_ISO_NR_BKID,
    P284_HIGH_ISO_NR_RESID16_HEX,
    P284_HLG_BT2020_RESID16_HEX,
    P284_HLG_STILL_BKID,
    P284_HLG_STILL_RESID16_HEX,
    P284_JH_FILE_TYPE_BKID,
    P284_JH_FILE_TYPE_RESID16_HEX,
    P284_LOG_SHOOTING_BKID,
    P284_LOG_SHOOTING_RESID16_HEX,
    P284_LONG_EXPOSURE_NR_BKID,
    P284_LONG_EXPOSURE_NR_RESID16_HEX,
    P284_MECHANICAL_FLASH_SYNC_DENOM_CEILING,
    P284_METERING_MODE_BKID,
    P284_METERING_MODE_RESID16_HEX,
    P284_METERING_MODE_RESIDS,
    P284_METERING_SIX_MODES,
    P284_OVERALL_READY_OFFLINE_AWAITING_BENCH_RECEIPTS,
    P284_PASM_EXPOSURE_MODES,
    P284_PP11_CAUTION_ID,
    P284_PP11_GAMMA_NAME,
    P284_PP11_RESIDS,
    P284_PP1_TO_PP11_PROFILES,
    P284_PP_BKID,
    P284_PP_DEFAULT_PROFILE,
    P284_PP_RESID16_HEX,
    P284_PPLUT_PROFILES,
    P284_PRIORITY_AWB_RESID16_HEX,
    P284_SCHEMA,
    P284_SELECT_LUT_RESID16_HEX,
    P284_SET_FILE_NAME_RESID16_HEX,
    P284_SHOCKLESS_WB_RESID16_HEX,
    P284_SHUTTER_AWB_LOCK_RESID16_HEX,
    P284_SHUTTER_TYPE_BKID,
    P284_SHUTTER_TYPE_RESID16_HEX,
    P284_SILENT_MODE_RESID16_HEX,
    P284_SLOG3_PROFILES,
    P284_SONY_HELP_GUIDE_ID,
    P284_SPOT_METERING_POINT_RESID16_HEX,
    P284_STILL_PREFIX_NO_LEADING_UNDERSCORE_RE,
    P284_STILL_RAW_FILE_TYPE_BKID,
    P284_STILL_RAW_FILE_TYPE_RESID16_HEX,
    P284_VALID_AEL_WITH_SHUTTER_MODES,
    P284_VALID_COLOR_SPACES,
    P284_VALID_EXPOSURE_MODES,
    P284_VALID_HIGH_ISO_NR_MODES,
    P284_VALID_JH_FILE_TYPES,
    P284_VALID_LOG_SHOOTING_MODES,
    P284_VALID_PICTURE_PROFILES,
    P284_VALID_PRIORITY_AWB_MODES,
    P284_VALID_RESET_ACTIONS,
    P284_VALID_SHOCKLESS_WB_MODES,
    P284_VALID_SHOOT_MODES,
    P284_VALID_SHUTTER_AWB_LOCK_MODES,
    P284_VALID_SPOT_METERING_POINTS,
    P284_VALID_STILL_FILE_FORMATS,
    P284_VERSION,
    P284_WB_AB_MAX,
    P284_WB_AB_MIN,
    P284_WB_BKID,
    P284_WB_CINE_EI_BLOCKED_MODES,
    P284_WB_CTEMP_RESID16_HEX,
    P284_WB_CUSTOM_SLOTS,
    P284_WB_FILTER_RESID16_HEX,
    P284_WB_GM_MAX,
    P284_WB_GM_MIN,
    P284_WB_KELVIN_MAX_K,
    P284_WB_KELVIN_MIN_K,
    P284_WB_KELVIN_STEP_K,
    P284_WB_RESID16_HEX,
    P284_WB_VALID_MODES,
    PHASE284_PASSIVE_TX_BYTES_EMITTED,
    PHASE284_RAW_FIRMWARE_BYTES_LEAKED,
    PHASE284_USB_PACKETS_TRANSMITTED,
    PHASE_284_CHECK_GROUP_IDS,
    PHASE_284_SCHEMA,
    PHASE_284_VALID_GO_NO_GO_VALUES,
    PHASE_284_VERSION,
    REALHW_PP_SCINETONE_WB_METERING_SHUTTER_TYPE_SCHEMA,
    build_simulated_phase284_tier0_receipts,
    evaluate_p284_check_group_a_pp_scinetone_look_dro_log,
    evaluate_p284_check_group_b_wb_and_metering,
    evaluate_p284_check_group_c_raw_hlg_and_colorspace,
    evaluate_p284_check_group_d_shutter_type_drive_and_tier0,
    evaluate_realhw_pp_scinetone_wb_metering_and_shutter_type_readiness,
    inspect_phase284_donors_bounded,
    render_phase284_markdown,
    run_pp_scinetone_wb_metering_and_shutter_type_preflight,
    verify_phase284_report,
)


def _subprocess_env(*, clean_room: bool = False) -> dict[str, str]:
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    python_paths = [
        str(REPO_ROOT / "outputs/fx6-on-fx3-closure"),
        str(REPO_ROOT / "outputs/fx3-safety"),
        str(REPO_ROOT / "outputs/fx3-recovery-adapter"),
        str(REPO_ROOT / "outputs/fx3-firmware-lab"),
        str(REPO_ROOT / "outputs/fx3-vm"),
    ]
    existing = env.get("PYTHONPATH", "")
    if existing:
        python_paths.append(existing)
    env["PYTHONPATH"] = os.pathsep.join(python_paths)
    if clean_room:
        env["FX3_CLEAN_ROOM_TEST"] = "1"
    return env


def _ci_subprocess_timeout() -> float:
    return 15.0 if os.environ.get("GITHUB_ACTIONS") == "true" else 8.0


class TestPhase284PpScinetoneWbMeteringAndShutterTypeVerifier(unittest.TestCase):
    """72 dual-mode tests for Phase 284 9th real-hardware physical bench verifier."""

    # --- Exports, Constants & Non-Shadowing Integrity (4 tests) ---

    def test_01_top_level_exports_and_non_shadowing_with_ph279(self) -> None:
        self.assertTrue(
            hasattr(fx6_closure, "evaluate_realhw_pp_scinetone_wb_metering_and_shutter_type_readiness")
        )
        self.assertTrue(
            hasattr(fx6_closure, "run_pp_scinetone_wb_metering_and_shutter_type_preflight")
        )
        self.assertIs(
            fx6_closure.run_pp_scinetone_wb_metering_and_shutter_type_preflight,
            evaluate_realhw_pp_scinetone_wb_metering_and_shutter_type_readiness,
        )
        self.assertTrue(hasattr(fx6_closure, "verify_phase284_report"))
        self.assertTrue(hasattr(fx6_closure, "render_phase284_markdown"))
        # Phase 279 exports remain intact and unshadowed.
        self.assertTrue(
            hasattr(fx6_closure, "evaluate_realhw_usb_mode_hdmi_info_protect_and_network_reset_readiness")
        )
        self.assertTrue(hasattr(fx6_closure, "verify_phase279_report"))
        self.assertIn("evaluate_realhw_pp_scinetone_wb_metering_and_shutter_type_readiness", fx6_closure.__all__)
        self.assertIn("P284_SCHEMA", fx6_closure.__all__)

    def test_02_schema_version_check_group_ids_and_zero_locks(self) -> None:
        self.assertEqual(
            PHASE_284_SCHEMA,
            "realhw_pp_scinetone_wb_metering_and_shutter_type_verifier_v1",
        )
        self.assertEqual(P284_SCHEMA, PHASE_284_SCHEMA)
        self.assertEqual(REALHW_PP_SCINETONE_WB_METERING_SHUTTER_TYPE_SCHEMA, PHASE_284_SCHEMA)
        self.assertEqual(PHASE_284_VERSION, "284.0.0")
        self.assertEqual(P284_VERSION, "284.0.0")
        self.assertEqual(P284_SONY_HELP_GUIDE_ID, "ilc/2210")
        self.assertEqual(len(PHASE_284_CHECK_GROUP_IDS), 4)
        self.assertEqual(
            PHASE_284_CHECK_GROUP_IDS,
            (
                P284_CHECK_GROUP_A_ID,
                P284_CHECK_GROUP_B_ID,
                P284_CHECK_GROUP_C_ID,
                P284_CHECK_GROUP_D_ID,
            ),
        )
        self.assertEqual(PHASE284_USB_PACKETS_TRANSMITTED, 0)
        self.assertEqual(PHASE284_RAW_FIRMWARE_BYTES_LEAKED, 0)
        self.assertEqual(PHASE284_PASSIVE_TX_BYTES_EMITTED, 0)
        self.assertIn(GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT, PHASE_284_VALID_GO_NO_GO_VALUES)
        self.assertIn(GO_NO_GO_DRY_RUN_SIMULATED_READY, PHASE_284_VALID_GO_NO_GO_VALUES)
        self.assertIn(
            P284_GO_NO_GO_PP_SCINETONE_WB_METERING_SHUTTER_TYPE_VERIFIED,
            PHASE_284_VALID_GO_NO_GO_VALUES,
        )
        self.assertIn(
            P284_GO_NO_GO_BLOCKED_PP_SCINETONE_WB_METERING_SHUTTER_TYPE_FAILURE,
            PHASE_284_VALID_GO_NO_GO_VALUES,
        )

    def test_03_wave48_constants_and_resid16_tokens(self) -> None:
        self.assertEqual(P284_PP_DEFAULT_PROFILE, "PP11")
        self.assertEqual(P284_PP11_GAMMA_NAME, "S-Cinetone")
        self.assertEqual(P284_PP_BKID, "BKID_APP_setting_picture_profile")
        self.assertEqual(P284_PP_RESID16_HEX, "0x6830")
        self.assertEqual(P284_DIFF_SET_BKID, "BKID_APP_setting_different_set")
        self.assertEqual(P284_DIFF_SET_RESID16_HEX, "0x62ee")
        self.assertEqual(P284_CREATIVE_LOOK_BKID, "BKID_APP_setting_creative_style_plus")
        self.assertEqual(P284_CREATIVE_LOOK_RESID16_HEX, "0x6823")
        self.assertEqual(P284_CREATIVE_LOOK_DEFAULT, "ST")
        self.assertEqual(P284_CREATIVE_LOOK_LOCKED_DASH, "-")
        self.assertEqual(len(P284_CREATIVE_LOOK_TEN_PRESETS), 10)
        self.assertEqual(P284_DRO_BKID, "BKID_APP_setting_dro")
        self.assertEqual(P284_DRO_RESID16_HEX, "0xe89c")
        self.assertEqual(P284_LOG_SHOOTING_BKID, "BKID_APP_setting_log_shooting")
        self.assertEqual(P284_LOG_SHOOTING_RESID16_HEX, "0x6020")
        self.assertEqual(len(P284_PP1_TO_PP11_PROFILES), 11)
        self.assertEqual(len(P284_PPLUT_PROFILES), 4)
        self.assertEqual(P284_SLOG3_PROFILES, ("PP8", "PP9"))
        self.assertEqual(P284_PP11_RESIDS, ("0x67ab", "0x6e61"))
        self.assertEqual(P284_PP11_CAUTION_ID, "CAUTION_ID_FACTOR_GAMMA_SCINETONE_MSG")
        self.assertEqual(P284_WB_BKID, "BKID_APP_setting_white_balance")
        self.assertEqual(P284_WB_RESID16_HEX, "0xe5d4")
        self.assertEqual(P284_WB_KELVIN_MIN_K, 2500)
        self.assertEqual(P284_WB_KELVIN_MAX_K, 9900)
        self.assertEqual(P284_WB_KELVIN_STEP_K, 100)
        self.assertEqual((P284_WB_AB_MIN, P284_WB_AB_MAX), (-7, 7))
        self.assertEqual((P284_WB_GM_MIN, P284_WB_GM_MAX), (-7, 7))
        self.assertEqual(P284_WB_CUSTOM_SLOTS, ("CUSTOM_1", "CUSTOM_2", "CUSTOM_3"))
        self.assertEqual(P284_WB_CINE_EI_BLOCKED_MODES, ("AUTO", "UNDERWATER_AUTO"))
        self.assertEqual(len(P284_METERING_SIX_MODES), 6)
        self.assertEqual(P284_CINE_EI_BASE_ISOS, (800, 12800))
        self.assertEqual(P284_SHUTTER_AWB_LOCK_RESID16_HEX, "0x66db")
        self.assertEqual(P284_AEL_WITH_SHUTTER_RESID16_HEX, "0x669d")
        self.assertEqual(P284_SHOCKLESS_WB_RESID16_HEX, "0x62fe")
        self.assertEqual(P284_FACE_PRIORITY_MULTI_METERING_RESID16_HEX, "0x69c7")
        self.assertEqual(P284_SPOT_METERING_POINT_RESID16_HEX, "0x71b5")
        self.assertEqual(P284_PRIORITY_AWB_RESID16_HEX, "0x67a7")
        self.assertEqual(P284_WB_CTEMP_RESID16_HEX, "0xe2ac")
        self.assertEqual(P284_WB_FILTER_RESID16_HEX, "0xe992")
        self.assertEqual(P284_METERING_MODE_BKID, "BKID_APP_setting_metering_mode")
        self.assertEqual(P284_METERING_MODE_RESID16_HEX, "0xe5cf")
        self.assertEqual(len(P284_METERING_MODE_RESIDS), 6)
        self.assertEqual(P284_DISPLAY_LUT_RESID16_HEX, "0x729a")
        self.assertEqual(P284_SELECT_LUT_RESID16_HEX, "0x643e")

    def test_04_wave49_constants_and_resid16_tokens(self) -> None:
        self.assertEqual(P284_STILL_RAW_FILE_TYPE_BKID, "BKID_APP_setting_still_raw_file_type")
        self.assertEqual(P284_STILL_RAW_FILE_TYPE_RESID16_HEX, "0x6ff2")
        self.assertEqual(P284_FX3_RAW_TWO_OPTIONS, ("COMPRESSED", "UNCOMPRESSED"))
        self.assertEqual(len(P284_FX3_RAW_OPTION_RESIDS), 2)
        self.assertEqual(P284_DORMANT_LOSSLESS_RAW_OPTIONS, ("LOSSLESS_COMP", "LOSSLESS_COMPRESSED", "LOSSLESS_COMP_L", "LOSSLESS_COMP_M", "LOSSLESS_COMP_S"))
        self.assertEqual(P284_DORMANT_LOSSLESS_COMP_RESID16_HEX, "0x6b56")
        self.assertEqual(P284_HLG_STILL_BKID, "BKID_APP_setting_still_hlg_photo")
        self.assertEqual(P284_HLG_STILL_RESID16_HEX, "0x76c8")
        self.assertEqual(P284_HLG_BT2020_RESID16_HEX, "0x79e1")
        self.assertEqual(P284_JH_FILE_TYPE_BKID, "BKID_APP_setting_jh_file_type")
        self.assertEqual(P284_JH_FILE_TYPE_RESID16_HEX, "0x742a")
        self.assertEqual(P284_PASM_EXPOSURE_MODES, ("PROGRAM_AUTO", "APERTURE_PRIORITY", "SHUTTER_PRIORITY", "MANUAL_EXPOSURE"))
        self.assertEqual(P284_COLOR_SPACE_BKID, "BKID_APP_setting_still_color_space")
        self.assertEqual(P284_COLOR_SPACE_RESID16_HEX, "0x68b7")
        self.assertEqual(len(P284_COLOR_SPACE_RESIDS), 2)
        self.assertEqual(P284_SET_FILE_NAME_RESID16_HEX, "0x6993")
        self.assertEqual(P284_DEFAULT_STILL_PREFIX, "DSC")
        self.assertIsNotNone(P284_STILL_PREFIX_NO_LEADING_UNDERSCORE_RE.match("DSC"))
        self.assertIsNone(P284_STILL_PREFIX_NO_LEADING_UNDERSCORE_RE.match("_DS"))
        self.assertEqual(P284_SHUTTER_TYPE_BKID, "BKID_APP_setting_still_shutter_type")
        self.assertEqual(P284_SHUTTER_TYPE_RESID16_HEX, "0x7aa9")
        self.assertEqual(P284_FX3_SHUTTER_TWO_TYPES, ("MECHANICAL_SHUTTER", "ELECTRONIC_SHUTTER"))
        self.assertEqual(len(P284_FX3_SHUTTER_TYPE_RESIDS), 2)
        self.assertEqual(P284_FORBIDDEN_SHUTTER_TYPE_AUTO, "AUTO")
        self.assertEqual(P284_SILENT_MODE_RESID16_HEX, "0x7a53")
        self.assertEqual(P284_E_FRONT_CURTAIN_BKID, "BKID_APP_setting_front_curtaion_shutter")
        self.assertEqual(P284_E_FRONT_CURTAIN_RESID16_HEX, "0x64c6")
        self.assertEqual(P284_MECHANICAL_FLASH_SYNC_DENOM_CEILING, 250)
        self.assertEqual(P284_FLASH_SYNC_RESID16_HEX, "0x759b")
        self.assertEqual(len(P284_ELECTRONIC_SHUTTER_FIVE_LOCKOUTS), 5)
        self.assertEqual(P284_LONG_EXPOSURE_NR_BKID, "BKID_APP_setting_long_exposure_nr")
        self.assertEqual(P284_LONG_EXPOSURE_NR_RESID16_HEX, "0x6cd7")
        self.assertEqual(P284_HIGH_ISO_NR_BKID, "BKID_APP_setting_high_iso_nr")
        self.assertEqual(P284_HIGH_ISO_NR_RESID16_HEX, "0x650b")
        self.assertEqual(P284_DRIVE_MODE_BKID, "BKID_APP_setting_drive_mode")
        self.assertEqual(P284_DRIVE_MODE_RESID16_HEX, "0x7228")
        self.assertEqual(len(P284_DRIVE_EIGHT_MODES), 8)
        self.assertEqual(P284_CONT_HIP_MAX_FPS, 10)
        self.assertEqual(P284_CONT_HIP_RESID16_HEX, "0x68d1")
        self.assertEqual(P284_AF_LOCK_APERTURE_THRESHOLD_F, 11.0)

    # --- Bounded O_RDONLY Donor Inspection & Clean-Room Fallback (4 tests) ---

    def test_05_donor_inspection_force_clean_room_and_env_vars(self) -> None:
        res_cr = inspect_phase284_donors_bounded(force_clean_room=True)
        self.assertTrue(res_cr.passed)
        self.assertEqual(res_cr.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(res_cr.read_only_o_rdonly_enforced)
        self.assertTrue(res_cr.within_150ms_budget)
        self.assertEqual(res_cr.raw_firmware_bytes_leaked, 0)
        self.assertEqual(len(res_cr.errors), 0)

        for env_key in ("FX3_CLEAN_ROOM_TEST", "FX3_FX6_FORCE_CLEAN_ROOM"):
            with mock.patch.dict(os.environ, {env_key: "1"}):
                res_env = inspect_phase284_donors_bounded()
                self.assertTrue(res_env.passed)
                self.assertEqual(res_env.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_06_donor_inspection_default_mode_respects_budget(self) -> None:
        res = inspect_phase284_donors_bounded()
        self.assertTrue(res.passed)
        self.assertIn(res.verification_mode, ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"))
        self.assertTrue(res.read_only_o_rdonly_enforced)
        self.assertTrue(res.within_150ms_budget)
        self.assertLessEqual(res.elapsed_seconds, 0.15)
        self.assertEqual(res.raw_firmware_bytes_leaked, 0)
        if res.verification_mode == "LOCAL_DONOR_O_RDONLY":
            self.assertTrue(res.fx3_im_elf_verified)
            self.assertTrue(res.fx3_libjiritsu_verified)
            self.assertTrue(res.fx3_libusbbuspower_verified)
            self.assertTrue(res.fx6_appfw_verified)
            self.assertTrue(res.fx6_wlan_rsrc_verified)
            self.assertTrue(res.fx3_upm_ko_verified)

    def test_07_donor_inspection_synthetic_clean_room_alias(self) -> None:
        res = inspect_phase284_donors_bounded(synthetic_clean_room=True)
        self.assertTrue(res.passed)
        self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(res.raw_firmware_bytes_leaked, 0)

    def test_08_donor_inspection_missing_donors_without_clean_room_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            missing_dir = Path(tmp) / "nonexistent_donor"
            clean_env = {
                k: v
                for k, v in os.environ.items()
                if k not in ("FX3_CLEAN_ROOM_TEST", "FX3_FX6_FORCE_CLEAN_ROOM")
            }
            with mock.patch.dict(os.environ, clean_env, clear=True):
                res = inspect_phase284_donors_bounded(
                    fx6_lib_dir=missing_dir,
                    fx3_modules_dir=missing_dir,
                    force_clean_room=False,
                )
                self.assertFalse(res.passed)
                self.assertEqual(res.verification_mode, "LOCAL_DONOR_O_RDONLY")
                self.assertGreater(len(res.errors), 0)

    # --- Check Group A: Wave 48 PP11 S-Cinetone, Creative Look, DRO, Log & Reset Trap (14 tests) ---

    def test_09_group_a_default_cine_ei_passes(self) -> None:
        ga = evaluate_p284_check_group_a_pp_scinetone_look_dro_log()
        self.assertTrue(ga.passed)
        self.assertEqual(ga.check_group_id, P284_CHECK_GROUP_A_ID)
        self.assertEqual(ga.factory_default_pp, "PP11")
        self.assertEqual(ga.log_shooting_mode, "CINE_EI")
        self.assertEqual(ga.effective_picture_profile, "OFF")
        self.assertEqual(ga.creative_look, "-")
        self.assertEqual(ga.dro_mode, "OFF")
        self.assertEqual(ga.exposed_creative_look_count, 10)
        self.assertTrue(ga.pp1_11_internal_params_survive_resets)
        self.assertTrue(ga.different_set_checkmarks_survive_resets)
        self.assertEqual(len(ga.errors), 0)

    def test_10_group_a_stock_pp11_scinetone_coupled_movie_and_still(self) -> None:
        for shoot in ("MOVIE", "PHOTO"):
            ga = evaluate_p284_check_group_a_pp_scinetone_look_dro_log(
                shoot_mode=shoot,
                log_shooting_mode="OFF",
                picture_profile="PP11",
                different_set_pp_checked=False,
                creative_look="-",
                dro_mode="OFF",
            )
            self.assertTrue(ga.passed, ga.errors)
            self.assertEqual(ga.effective_picture_profile, "PP11")
            self.assertTrue(ga.creative_look_and_dro_locked_out)

    def test_11_group_a_different_set_decouples_still_and_movie_pp(self) -> None:
        ga_still = evaluate_p284_check_group_a_pp_scinetone_look_dro_log(
            shoot_mode="PHOTO",
            log_shooting_mode="OFF",
            different_set_pp_checked=True,
            movie_picture_profile="PP11",
            still_picture_profile="OFF",
            creative_look="ST",
            dro_mode="AUTO",
        )
        self.assertTrue(ga_still.passed, ga_still.errors)
        self.assertEqual(ga_still.effective_picture_profile, "OFF")
        self.assertFalse(ga_still.creative_look_and_dro_locked_out)

        ga_movie = evaluate_p284_check_group_a_pp_scinetone_look_dro_log(
            shoot_mode="MOVIE",
            log_shooting_mode="OFF",
            different_set_pp_checked=True,
            movie_picture_profile="PP11",
            still_picture_profile="OFF",
            creative_look="-",
            dro_mode="OFF",
        )
        self.assertTrue(ga_movie.passed, ga_movie.errors)
        self.assertEqual(ga_movie.effective_picture_profile, "PP11")

    def test_12_group_a_rejects_wrong_factory_default_pp(self) -> None:
        ga = evaluate_p284_check_group_a_pp_scinetone_look_dro_log(
            factory_default_pp="OFF",
        )
        self.assertFalse(ga.passed)
        self.assertTrue(any(P284_GA_ERR_PP11_SCINETONE_OR_DIFF_SET_COUPLING in e for e in ga.errors))

    def test_13_group_a_pp_active_locks_creative_look_and_dro(self) -> None:
        ga_look = evaluate_p284_check_group_a_pp_scinetone_look_dro_log(
            log_shooting_mode="OFF",
            picture_profile="PP11",
            creative_look="ST",
            dro_mode="OFF",
        )
        self.assertFalse(ga_look.passed)
        self.assertTrue(any(P284_GA_ERR_CREATIVE_LOOK_DRO_OR_LOG_LOCKOUT in e for e in ga_look.errors))

        ga_dro = evaluate_p284_check_group_a_pp_scinetone_look_dro_log(
            log_shooting_mode="OFF",
            picture_profile="PP11",
            creative_look="-",
            dro_mode="AUTO",
        )
        self.assertFalse(ga_dro.passed)
        self.assertTrue(any(P284_GA_ERR_CREATIVE_LOOK_DRO_OR_LOG_LOCKOUT in e for e in ga_dro.errors))

    def test_14_group_a_log_shooting_locks_pp_look_dro_and_gamma_assist(self) -> None:
        for log_mode in P284_ACTIVE_LOG_SHOOTING_MODES:
            ga_ok = evaluate_p284_check_group_a_pp_scinetone_look_dro_log(
                log_shooting_mode=log_mode,
                picture_profile="OFF",
                creative_look="-",
                dro_mode="OFF",
                movie_gamma_display_assist="OFF",
            )
            self.assertTrue(ga_ok.passed, ga_ok.errors)

        ga_bad_pp = evaluate_p284_check_group_a_pp_scinetone_look_dro_log(
            log_shooting_mode="CINE_EI",
            picture_profile="PP8",
            creative_look="-",
            dro_mode="OFF",
        )
        self.assertFalse(ga_bad_pp.passed)
        self.assertTrue(any(P284_GA_ERR_CREATIVE_LOOK_DRO_OR_LOG_LOCKOUT in e for e in ga_bad_pp.errors))

        ga_bad_gamma = evaluate_p284_check_group_a_pp_scinetone_look_dro_log(
            log_shooting_mode="FLEXIBLE_ISO",
            picture_profile="OFF",
            creative_look="-",
            dro_mode="OFF",
            movie_gamma_display_assist="ON",
        )
        self.assertFalse(ga_bad_gamma.passed)
        self.assertTrue(any(P284_GA_ERR_CREATIVE_LOOK_DRO_OR_LOG_LOCKOUT in e for e in ga_bad_gamma.errors))

    def test_15_group_a_all_10_creative_looks_valid_when_log_off_and_pp_off(self) -> None:
        for look in P284_CREATIVE_LOOK_TEN_PRESETS:
            ga = evaluate_p284_check_group_a_pp_scinetone_look_dro_log(
                log_shooting_mode="OFF",
                picture_profile="OFF",
                creative_look=look,
                dro_mode="AUTO",
            )
            self.assertTrue(ga.passed, f"{look}: {ga.errors}")

    def test_16_group_a_rejects_missing_or_extra_creative_looks(self) -> None:
        ga = evaluate_p284_check_group_a_pp_scinetone_look_dro_log(
            exposed_creative_looks=("ST", "PT", "NT"),
        )
        self.assertFalse(ga.passed)
        self.assertTrue(any(P284_GA_ERR_CREATIVE_LOOK_DRO_OR_LOG_LOCKOUT in e for e in ga.errors))

    def test_17_group_a_expect_creative_look_active_with_pp_or_log_rejected(self) -> None:
        ga = evaluate_p284_check_group_a_pp_scinetone_look_dro_log(
            expect_creative_look_or_dro_active_with_pp_or_log=True,
        )
        self.assertFalse(ga.passed)
        self.assertTrue(any(P284_GA_ERR_CREATIVE_LOOK_DRO_OR_LOG_LOCKOUT in e for e in ga.errors))

    def test_18_group_a_pplut_movie_only_and_1080p_internal_rec_hdmi_clamp(self) -> None:
        ga_ok = evaluate_p284_check_group_a_pp_scinetone_look_dro_log(
            shoot_mode="MOVIE",
            log_shooting_mode="OFF",
            picture_profile="PPLUT1",
            creative_look="-",
            dro_mode="OFF",
            internal_recording_active=True,
            hdmi_output_resolution="1080P",
        )
        self.assertTrue(ga_ok.passed, ga_ok.errors)
        self.assertTrue(ga_ok.pplut_movie_only_enforced)
        self.assertTrue(ga_ok.pplut_1080p_hdmi_clamp_verified)

        ga_still = evaluate_p284_check_group_a_pp_scinetone_look_dro_log(
            shoot_mode="PHOTO",
            log_shooting_mode="OFF",
            picture_profile="PPLUT1",
            creative_look="-",
            dro_mode="OFF",
        )
        self.assertFalse(ga_still.passed)
        self.assertTrue(any(P284_GA_ERR_PPLUT_STILL_OR_1080P_HDMI_CLAMP in e for e in ga_still.errors))

        ga_4k = evaluate_p284_check_group_a_pp_scinetone_look_dro_log(
            shoot_mode="MOVIE",
            log_shooting_mode="OFF",
            picture_profile="PPLUT2",
            creative_look="-",
            dro_mode="OFF",
            internal_recording_active=True,
            hdmi_output_resolution="2160P",
        )
        self.assertFalse(ga_4k.passed)
        self.assertTrue(any(P284_GA_ERR_PPLUT_STILL_OR_1080P_HDMI_CLAMP in e for e in ga_4k.errors))

    def test_19_group_a_expect_pplut_in_still_rejected(self) -> None:
        ga = evaluate_p284_check_group_a_pp_scinetone_look_dro_log(
            expect_pplut_in_still=True,
        )
        self.assertFalse(ga.passed)
        self.assertTrue(any(P284_GA_ERR_PPLUT_STILL_OR_1080P_HDMI_CLAMP in e for e in ga.errors))

    def test_20_group_a_pp1_11_internal_params_survive_camera_reset_and_initialize(self) -> None:
        for reset_action in ("CAMERA_SETTINGS_RESET", "INITIALIZE"):
            ga_ok = evaluate_p284_check_group_a_pp_scinetone_look_dro_log(
                reset_action=reset_action,
                pp1_11_custom_params_modified=True,
                pp_individual_reset_executed=False,
                claimed_pp1_11_internal_params_wiped=False,
                claimed_diff_set_checkmarks_wiped=False,
            )
            self.assertTrue(ga_ok.passed, ga_ok.errors)

            ga_wiped_pp = evaluate_p284_check_group_a_pp_scinetone_look_dro_log(
                reset_action=reset_action,
                pp1_11_custom_params_modified=True,
                pp_individual_reset_executed=False,
                claimed_pp1_11_internal_params_wiped=True,
            )
            self.assertFalse(ga_wiped_pp.passed)
            self.assertTrue(any(P284_GA_ERR_PP_INTERNAL_RESET_TRAP_OR_DIFF_SET_PERSISTENCE in e for e in ga_wiped_pp.errors))

    def test_21_group_a_diff_set_survives_initialize_and_active_selector_resets_to_pp11(self) -> None:
        ga_diff_wiped = evaluate_p284_check_group_a_pp_scinetone_look_dro_log(
            reset_action="INITIALIZE",
            claimed_diff_set_checkmarks_wiped=True,
        )
        self.assertFalse(ga_diff_wiped.passed)
        self.assertTrue(any(P284_GA_ERR_PP_INTERNAL_RESET_TRAP_OR_DIFF_SET_PERSISTENCE in e for e in ga_diff_wiped.errors))

        ga_selector_stuck = evaluate_p284_check_group_a_pp_scinetone_look_dro_log(
            reset_action="CAMERA_SETTINGS_RESET",
            claimed_pp_active_selector_remains_non_pp11_after_camera_reset=True,
        )
        self.assertFalse(ga_selector_stuck.passed)
        self.assertTrue(any(P284_GA_ERR_PP_INTERNAL_RESET_TRAP_OR_DIFF_SET_PERSISTENCE in e for e in ga_selector_stuck.errors))

    def test_22_group_a_model_id_fw_floor_and_help_guide_enforced(self) -> None:
        ga_model = evaluate_p284_check_group_a_pp_scinetone_look_dro_log(
            body_model_id=0xDEADBEEF,
        )
        self.assertFalse(ga_model.passed)
        self.assertTrue(any(P284_GA_ERR_MODEL_OR_FW_FLOOR in e for e in ga_model.errors))

        ga_fw = evaluate_p284_check_group_a_pp_scinetone_look_dro_log(
            body_fw="1.00",
        )
        self.assertFalse(ga_fw.passed)
        self.assertTrue(any(P284_GA_ERR_MODEL_OR_FW_FLOOR in e for e in ga_fw.errors))

        ga_guide = evaluate_p284_check_group_a_pp_scinetone_look_dro_log(
            sony_help_guide_id="ilc/9999",
        )
        self.assertFalse(ga_guide.passed)
        self.assertTrue(any(P284_GA_ERR_MODEL_OR_FW_FLOOR in e for e in ga_guide.errors))

    # --- Check Group B: Wave 48 White Balance, Custom 1..3 & Metering Mode (14 tests) ---

    def test_23_group_b_default_cine_ei_passes(self) -> None:
        gb = evaluate_p284_check_group_b_wb_and_metering()
        self.assertTrue(gb.passed, gb.errors)
        self.assertEqual(gb.check_group_id, P284_CHECK_GROUP_B_ID)
        self.assertEqual(gb.wb_mode, "C_TEMP_FILTER")
        self.assertEqual(gb.wb_kelvin_k, 5600)
        self.assertEqual(gb.metering_mode, "MULTI")
        self.assertEqual(len(gb.exposed_metering_modes), 6)
        self.assertEqual(gb.cine_ei_base_iso, 800)
        self.assertTrue(gb.custom_wb_survives_camera_reset)
        self.assertTrue(gb.custom_wb_excluded_from_camset)
        self.assertEqual(len(gb.errors), 0)

    def test_24_group_b_wb_kelvin_2500_to_9900_100k_step_boundaries(self) -> None:
        for kelvin in (2500, 5600, 9900):
            gb_ok = evaluate_p284_check_group_b_wb_and_metering(wb_kelvin_k=kelvin)
            self.assertTrue(gb_ok.passed, gb_ok.errors)

        for bad_kelvin in (2400, 5650, 10000):
            gb_bad = evaluate_p284_check_group_b_wb_and_metering(wb_kelvin_k=bad_kelvin)
            self.assertFalse(gb_bad.passed)
            self.assertTrue(any(P284_GB_ERR_WB_RANGE_OR_NON_RESETTABLE_LOCK_PERSISTENCE in e for e in gb_bad.errors))

    def test_25_group_b_wb_ab_and_gm_7step_boundaries(self) -> None:
        gb_edge = evaluate_p284_check_group_b_wb_and_metering(wb_ab_shift=-7, wb_gm_shift=7)
        self.assertTrue(gb_edge.passed, gb_edge.errors)

        gb_ab_oob = evaluate_p284_check_group_b_wb_and_metering(wb_ab_shift=8)
        self.assertFalse(gb_ab_oob.passed)
        self.assertTrue(any(P284_GB_ERR_WB_RANGE_OR_NON_RESETTABLE_LOCK_PERSISTENCE in e for e in gb_ab_oob.errors))

        gb_gm_oob = evaluate_p284_check_group_b_wb_and_metering(wb_gm_shift=-8)
        self.assertFalse(gb_gm_oob.passed)
        self.assertTrue(any(P284_GB_ERR_WB_RANGE_OR_NON_RESETTABLE_LOCK_PERSISTENCE in e for e in gb_gm_oob.errors))

    def test_26_group_b_flash_wb_blocked_in_movie_allowed_in_photo(self) -> None:
        gb_movie = evaluate_p284_check_group_b_wb_and_metering(
            shoot_mode="MOVIE",
            log_shooting_mode="OFF",
            wb_mode="FLASH",
        )
        self.assertFalse(gb_movie.passed)
        self.assertTrue(any(P284_GB_ERR_WB_RANGE_OR_NON_RESETTABLE_LOCK_PERSISTENCE in e for e in gb_movie.errors))

        gb_photo = evaluate_p284_check_group_b_wb_and_metering(
            shoot_mode="PHOTO",
            log_shooting_mode="OFF",
            wb_mode="FLASH",
        )
        self.assertTrue(gb_photo.passed, gb_photo.errors)

    def test_27_group_b_cine_ei_and_quick_block_auto_and_underwater_auto(self) -> None:
        for log_mode in ("CINE_EI", "CINE_EI_QUICK"):
            for wb in P284_WB_CINE_EI_BLOCKED_MODES:
                gb = evaluate_p284_check_group_b_wb_and_metering(
                    log_shooting_mode=log_mode,
                    wb_mode=wb,
                )
                self.assertFalse(gb.passed)
                self.assertTrue(any(P284_GB_ERR_WB_CINE_EI_OR_CUSTOM_SETUP_TRAP in e for e in gb.errors))

        # Flexible ISO allows Auto WB.
        gb_flex = evaluate_p284_check_group_b_wb_and_metering(
            log_shooting_mode="FLEXIBLE_ISO",
            wb_mode="AUTO",
        )
        self.assertTrue(gb_flex.passed, gb_flex.errors)

    def test_28_group_b_custom_setup_trapped_under_log_slog3_or_pplut(self) -> None:
        for log_mode in P284_ACTIVE_LOG_SHOOTING_MODES:
            gb_log = evaluate_p284_check_group_b_wb_and_metering(
                log_shooting_mode=log_mode,
                wb_mode="CUSTOM_1",
                custom_wb_setup_requested=True,
            )
            self.assertFalse(gb_log.passed)
            self.assertTrue(any(P284_GB_ERR_WB_CINE_EI_OR_CUSTOM_SETUP_TRAP in e for e in gb_log.errors))

        for pp in (*P284_SLOG3_PROFILES, *P284_PPLUT_PROFILES):
            gb_pp = evaluate_p284_check_group_b_wb_and_metering(
                log_shooting_mode="OFF",
                picture_profile=pp,
                wb_mode="CUSTOM_2",
                custom_wb_setup_requested=True,
            )
            self.assertFalse(gb_pp.passed)
            self.assertTrue(any(P284_GB_ERR_WB_CINE_EI_OR_CUSTOM_SETUP_TRAP in e for e in gb_pp.errors))

        # Permitted when Log=Off and PP=PP11.
        gb_ok = evaluate_p284_check_group_b_wb_and_metering(
            log_shooting_mode="OFF",
            picture_profile="PP11",
            wb_mode="CUSTOM_1",
            custom_wb_setup_requested=True,
        )
        self.assertTrue(gb_ok.passed, gb_ok.errors)

    def test_29_group_b_custom_1_3_survives_camera_reset_and_excluded_from_camset(self) -> None:
        gb_ok = evaluate_p284_check_group_b_wb_and_metering(
            reset_action="CAMERA_SETTINGS_RESET",
            wb_mode="CUSTOM_3",
            custom_wb_survives_camera_reset=True,
            custom_wb_excluded_from_camset=True,
        )
        self.assertTrue(gb_ok.passed, gb_ok.errors)

        gb_saved = evaluate_p284_check_group_b_wb_and_metering(
            claimed_custom_wb_saved_in_camset=True,
        )
        self.assertFalse(gb_saved.passed)
        self.assertTrue(any(P284_GB_ERR_CUSTOM_WB_RESET_OR_CAMSET_EXCLUSION in e for e in gb_saved.errors))

        gb_wiped = evaluate_p284_check_group_b_wb_and_metering(
            reset_action="CAMERA_SETTINGS_RESET",
            claimed_custom_wb_wiped_by_camera_reset=True,
        )
        self.assertFalse(gb_wiped.passed)
        self.assertTrue(any(P284_GB_ERR_CUSTOM_WB_RESET_OR_CAMSET_EXCLUSION in e for e in gb_wiped.errors))

    def test_30_group_b_non_resettable_shutter_awb_lock_and_ael_w_shutter(self) -> None:
        gb_awb = evaluate_p284_check_group_b_wb_and_metering(
            reset_action="CAMERA_SETTINGS_RESET",
            shutter_awb_lock_survives_camera_reset=False,
        )
        self.assertFalse(gb_awb.passed)
        self.assertTrue(any(P284_GB_ERR_WB_RANGE_OR_NON_RESETTABLE_LOCK_PERSISTENCE in e for e in gb_awb.errors))

        gb_ael = evaluate_p284_check_group_b_wb_and_metering(
            reset_action="CAMERA_SETTINGS_RESET",
            ael_with_shutter_survives_camera_reset=False,
        )
        self.assertFalse(gb_ael.passed)
        self.assertTrue(any(P284_GB_ERR_METERING_6MODE_FACE_DESQUEEZE_OR_MM_BASE_ISO in e for e in gb_ael.errors))

    def test_31_group_b_priority_set_in_awb_and_shockless_wb_validation(self) -> None:
        for prio in P284_VALID_PRIORITY_AWB_MODES:
            for shock in P284_VALID_SHOCKLESS_WB_MODES:
                gb = evaluate_p284_check_group_b_wb_and_metering(
                    priority_set_in_awb=prio,
                    shockless_wb=shock,
                )
                self.assertTrue(gb.passed, gb.errors)

        gb_bad = evaluate_p284_check_group_b_wb_and_metering(
            priority_set_in_awb="INVALID",
            shockless_wb="99",
        )
        self.assertFalse(gb_bad.passed)
        self.assertTrue(any(P284_GB_ERR_WB_RANGE_OR_NON_RESETTABLE_LOCK_PERSISTENCE in e for e in gb_bad.errors))

    def test_32_group_b_metering_6modes_and_missing_mode_rejected(self) -> None:
        for mode in P284_METERING_SIX_MODES:
            gb = evaluate_p284_check_group_b_wb_and_metering(metering_mode=mode)
            self.assertTrue(gb.passed, f"{mode}: {gb.errors}")

        gb_missing = evaluate_p284_check_group_b_wb_and_metering(
            exposed_metering_modes=("MULTI", "CENTER", "SPOT_STANDARD"),
        )
        self.assertFalse(gb_missing.passed)
        self.assertTrue(any(P284_GB_ERR_METERING_6MODE_FACE_DESQUEEZE_OR_MM_BASE_ISO in e for e in gb_missing.errors))

    def test_33_group_b_desqueeze_forces_face_priority_in_multi_metering_off(self) -> None:
        gb_ok = evaluate_p284_check_group_b_wb_and_metering(
            desqueeze_display="2.0X",
            face_priority_in_multi_metering="OFF",
        )
        self.assertTrue(gb_ok.passed, gb_ok.errors)

        gb_bad = evaluate_p284_check_group_b_wb_and_metering(
            desqueeze_display="1.3X",
            face_priority_in_multi_metering="ON",
        )
        self.assertFalse(gb_bad.passed)
        self.assertTrue(any(P284_GB_ERR_METERING_6MODE_FACE_DESQUEEZE_OR_MM_BASE_ISO in e for e in gb_bad.errors))

    def test_34_group_b_spot_metering_point_and_ael_modes(self) -> None:
        for pt in P284_VALID_SPOT_METERING_POINTS:
            for ael in P284_VALID_AEL_WITH_SHUTTER_MODES:
                gb = evaluate_p284_check_group_b_wb_and_metering(
                    spot_metering_point=pt,
                    ael_with_shutter=ael,
                )
                self.assertTrue(gb.passed, gb.errors)

    def test_35_group_b_cine_ei_base_iso_800_and_12800_invariance(self) -> None:
        for base_iso in P284_CINE_EI_BASE_ISOS:
            gb = evaluate_p284_check_group_b_wb_and_metering(
                log_shooting_mode="CINE_EI",
                cine_ei_base_iso=base_iso,
                expect_metering_changes_cine_ei_iso=False,
            )
            self.assertTrue(gb.passed, gb.errors)

        gb_bad_iso = evaluate_p284_check_group_b_wb_and_metering(
            log_shooting_mode="CINE_EI",
            cine_ei_base_iso=1600,
        )
        self.assertFalse(gb_bad_iso.passed)
        self.assertTrue(any(P284_GB_ERR_METERING_6MODE_FACE_DESQUEEZE_OR_MM_BASE_ISO in e for e in gb_bad_iso.errors))

    def test_36_group_b_expect_metering_changes_cine_ei_iso_rejected(self) -> None:
        gb = evaluate_p284_check_group_b_wb_and_metering(
            log_shooting_mode="CINE_EI",
            expect_metering_changes_cine_ei_iso=True,
        )
        self.assertFalse(gb.passed)
        self.assertTrue(any(P284_GB_ERR_METERING_6MODE_FACE_DESQUEEZE_OR_MM_BASE_ISO in e for e in gb.errors))

    # --- Check Group C: Wave 49 Still RAW 2-Option, HLG Still & AdobeRGB DCF 2.0 (12 tests) ---

    def test_37_group_c_default_2option_raw_passes(self) -> None:
        for raw_type in P284_FX3_RAW_TWO_OPTIONS:
            gc = evaluate_p284_check_group_c_raw_hlg_and_colorspace(
                raw_file_type=raw_type,
            )
            self.assertTrue(gc.passed, gc.errors)
            self.assertEqual(gc.check_group_id, P284_CHECK_GROUP_C_ID)
            self.assertFalse(gc.lossless_comp_exposed_in_fx3_ui)
            self.assertTrue(gc.fx3_mechanical_shutter_present)
            self.assertFalse(gc.fx6_reference_mechanical_shutter)

    def test_38_group_c_rejects_dormant_lossless_comp_spoofing(self) -> None:
        gc_flag = evaluate_p284_check_group_c_raw_hlg_and_colorspace(
            lossless_comp_exposed_in_fx3_ui=True,
        )
        self.assertFalse(gc_flag.passed)
        self.assertTrue(any(P284_GC_ERR_RAW_2OPTION_OR_DORMANT_LOSSLESS_COMP_SPOOF in e for e in gc_flag.errors))

        gc_req = evaluate_p284_check_group_c_raw_hlg_and_colorspace(
            expect_lossless_comp_raw=True,
        )
        self.assertFalse(gc_req.passed)
        self.assertTrue(any(P284_GC_ERR_RAW_2OPTION_OR_DORMANT_LOSSLESS_COMP_SPOOF in e for e in gc_req.errors))

        gc_val = evaluate_p284_check_group_c_raw_hlg_and_colorspace(
            raw_file_type="LOSSLESS_COMP",
        )
        self.assertFalse(gc_val.passed)
        self.assertTrue(any(P284_GC_ERR_RAW_2OPTION_OR_DORMANT_LOSSLESS_COMP_SPOOF in e for e in gc_val.errors))

    def test_39_group_c_rejects_still_less_fx6_mechanical_shutter_spoof(self) -> None:
        gc = evaluate_p284_check_group_c_raw_hlg_and_colorspace(
            fx6_reference_mechanical_shutter=True,
        )
        self.assertFalse(gc.passed)
        self.assertTrue(any(P284_GC_ERR_RAW_2OPTION_OR_DORMANT_LOSSLESS_COMP_SPOOF in e for e in gc.errors))

    def test_40_group_c_rejects_wrong_exposed_raw_option_count(self) -> None:
        gc = evaluate_p284_check_group_c_raw_hlg_and_colorspace(
            exposed_raw_file_types=("COMPRESSED", "LOSSLESS_COMP", "UNCOMPRESSED"),
        )
        self.assertFalse(gc.passed)
        self.assertTrue(any(P284_GC_ERR_RAW_2OPTION_OR_DORMANT_LOSSLESS_COMP_SPOOF in e for e in gc.errors))

    def test_41_group_c_hlg_still_on_passes_with_heif_pasm_and_4lockouts(self) -> None:
        for exp_mode in P284_PASM_EXPOSURE_MODES:
            for jh in ("HEIF_420", "HEIF_422"):
                gc = evaluate_p284_check_group_c_raw_hlg_and_colorspace(
                    hlg_still_image="ON",
                    jh_file_type=jh,
                    still_file_format="HEIF",
                    exposure_mode=exp_mode,
                    picture_profile="OFF",
                    creative_look="-",
                    dro_mode="OFF",
                    dro_bracket_active=False,
                )
                self.assertTrue(gc.passed, f"{exp_mode}/{jh}: {gc.errors}")
                self.assertTrue(gc.hlg_still_prerequisites_met)
                self.assertTrue(gc.hlg_still_lockouts_enforced)

    def test_42_group_c_hlg_still_on_rejects_jpeg_or_raw_only(self) -> None:
        gc_jpeg = evaluate_p284_check_group_c_raw_hlg_and_colorspace(
            hlg_still_image="ON",
            jh_file_type="JPEG",
            still_file_format="HEIF",
            exposure_mode="MANUAL_EXPOSURE",
        )
        self.assertFalse(gc_jpeg.passed)
        self.assertTrue(any(P284_GC_ERR_HLG_STILL_PREREQ_OR_LOCKOUT_VIOLATED in e for e in gc_jpeg.errors))

        gc_raw_only = evaluate_p284_check_group_c_raw_hlg_and_colorspace(
            hlg_still_image="ON",
            jh_file_type="HEIF_420",
            still_file_format="RAW",
            exposure_mode="MANUAL_EXPOSURE",
        )
        self.assertFalse(gc_raw_only.passed)
        self.assertTrue(any(P284_GC_ERR_HLG_STILL_PREREQ_OR_LOCKOUT_VIOLATED in e for e in gc_raw_only.errors))

    def test_43_group_c_hlg_still_on_rejects_non_pasm_exposure_mode(self) -> None:
        for bad_exp in ("INTELLIGENT_AUTO", "FLEXIBLE_EXP"):
            gc = evaluate_p284_check_group_c_raw_hlg_and_colorspace(
                hlg_still_image="ON",
                jh_file_type="HEIF_420",
                still_file_format="HEIF",
                exposure_mode=bad_exp,
            )
            self.assertFalse(gc.passed)
            self.assertTrue(any(P284_GC_ERR_HLG_STILL_PREREQ_OR_LOCKOUT_VIOLATED in e for e in gc.errors))

    def test_44_group_c_hlg_still_on_enforces_all_4_lockouts(self) -> None:
        bad_kwargs_list = [
            {"picture_profile": "PP11"},
            {"creative_look": "ST"},
            {"dro_mode": "AUTO"},
            {"dro_bracket_active": True},
        ]
        for kw in bad_kwargs_list:
            gc = evaluate_p284_check_group_c_raw_hlg_and_colorspace(
                hlg_still_image="ON",
                jh_file_type="HEIF_420",
                still_file_format="HEIF",
                exposure_mode="MANUAL_EXPOSURE",
                **kw,
            )
            self.assertFalse(gc.passed, f"Expected fail for {kw}")
            self.assertTrue(any(P284_GC_ERR_HLG_STILL_PREREQ_OR_LOCKOUT_VIOLATED in e for e in gc.errors))

    def test_45_group_c_dcf20_srgb_vs_adobergb_prefix_rule(self) -> None:
        gc_srgb = evaluate_p284_check_group_c_raw_hlg_and_colorspace(
            color_space="SRGB",
            still_file_prefix="DSC",
            expected_dcf_sample_filename="DSC00001.ARW",
        )
        self.assertTrue(gc_srgb.passed, gc_srgb.errors)
        self.assertEqual(gc_srgb.effective_dcf_sample_filename, "DSC00001.ARW")

        gc_adobe = evaluate_p284_check_group_c_raw_hlg_and_colorspace(
            color_space="ADOBERGB",
            still_file_prefix="DSC",
            expected_dcf_sample_filename="_DSC0001.ARW",
        )
        self.assertTrue(gc_adobe.passed, gc_adobe.errors)
        self.assertEqual(gc_adobe.effective_dcf_sample_filename, "_DSC0001.ARW")

        gc_adobe_custom = evaluate_p284_check_group_c_raw_hlg_and_colorspace(
            color_space="ADOBERGB",
            still_file_prefix="FX3",
            expected_dcf_sample_filename="_FX30001.ARW",
        )
        self.assertTrue(gc_adobe_custom.passed, gc_adobe_custom.errors)

    def test_46_group_c_rejects_mismatched_dcf_filename_for_color_space(self) -> None:
        gc_bad_adobe = evaluate_p284_check_group_c_raw_hlg_and_colorspace(
            color_space="ADOBERGB",
            still_file_prefix="DSC",
            expected_dcf_sample_filename="DSC00001.ARW",
        )
        self.assertFalse(gc_bad_adobe.passed)
        self.assertTrue(any(P284_GC_ERR_COLOR_SPACE_OR_DCF20_ADOBERGB_UNDERSCORE_PREFIX in e for e in gc_bad_adobe.errors))

        gc_bad_srgb = evaluate_p284_check_group_c_raw_hlg_and_colorspace(
            color_space="SRGB",
            still_file_prefix="DSC",
            expected_dcf_sample_filename="_DSC0001.ARW",
        )
        self.assertFalse(gc_bad_srgb.passed)
        self.assertTrue(any(P284_GC_ERR_COLOR_SPACE_OR_DCF20_ADOBERGB_UNDERSCORE_PREFIX in e for e in gc_bad_srgb.errors))

    def test_47_group_c_forbids_manual_leading_underscore_in_set_file_name(self) -> None:
        gc = evaluate_p284_check_group_c_raw_hlg_and_colorspace(
            still_file_prefix="_FX",
            expected_dcf_sample_filename="_FX00001.ARW",
        )
        self.assertFalse(gc.passed)
        self.assertTrue(any(P284_GC_ERR_COLOR_SPACE_OR_DCF20_ADOBERGB_UNDERSCORE_PREFIX in e for e in gc.errors))

    def test_48_group_c_set_file_name_must_survive_camera_reset(self) -> None:
        gc = evaluate_p284_check_group_c_raw_hlg_and_colorspace(
            set_file_name_survives_camera_reset=False,
        )
        self.assertFalse(gc.passed)
        self.assertTrue(any(P284_GC_ERR_COLOR_SPACE_OR_DCF20_ADOBERGB_UNDERSCORE_PREFIX in e for e in gc.errors))

    # --- Check Group D & Tier-0 Dual-Media Receipt Validation (14 tests) ---

    def test_49_group_d_default_mechanical_offline_awaiting_receipts(self) -> None:
        gd, tier0_err = evaluate_p284_check_group_d_shutter_type_drive_and_tier0(
            simulate_bench_dry_run=False,
        )
        self.assertTrue(gd.passed, gd.errors)
        self.assertFalse(gd.tier0_receipt_verified)
        self.assertGreater(len(tier0_err), 0)
        self.assertEqual(gd.effective_shutter_type, "MECHANICAL_SHUTTER")
        self.assertFalse(gd.shutter_type_auto_exposed_in_fx3_ui)
        self.assertEqual(gd.h0_equals_h3_count, 16)
        self.assertEqual(gd.h0_h3_surface_count, 16)

    def test_50_group_d_rejects_2option_shutter_auto_spoof_or_wrong_list(self) -> None:
        gd_spoof, _ = evaluate_p284_check_group_d_shutter_type_drive_and_tier0(
            shutter_type_auto_exposed_in_fx3_ui=True,
            simulate_bench_dry_run=True,
        )
        self.assertFalse(gd_spoof.passed)
        self.assertTrue(any(P284_GD_ERR_SHUTTER_TYPE_2OPTION_NO_AUTO_OR_SILENT_LOCK in e for e in gd_spoof.errors))

        gd_req, _ = evaluate_p284_check_group_d_shutter_type_drive_and_tier0(
            expect_shutter_type_auto=True,
            simulate_bench_dry_run=True,
        )
        self.assertFalse(gd_req.passed)
        self.assertTrue(any(P284_GD_ERR_SHUTTER_TYPE_2OPTION_NO_AUTO_OR_SILENT_LOCK in e for e in gd_req.errors))

        gd_list, _ = evaluate_p284_check_group_d_shutter_type_drive_and_tier0(
            exposed_shutter_types=("AUTO", "MECHANICAL_SHUTTER", "ELECTRONIC_SHUTTER"),
            simulate_bench_dry_run=True,
        )
        self.assertFalse(gd_list.passed)
        self.assertTrue(any(P284_GD_ERR_SHUTTER_TYPE_2OPTION_NO_AUTO_OR_SILENT_LOCK in e for e in gd_list.errors))

    def test_51_group_d_silent_mode_forces_electronic_and_audio_off_plus_5lockouts(self) -> None:
        gd_ok, _ = evaluate_p284_check_group_d_shutter_type_drive_and_tier0(
            shutter_type="ELECTRONIC_SHUTTER",
            silent_mode="ON",
            audio_signals="OFF",
            flash_enabled=False,
            long_exposure_nr="OFF",
            e_front_curtain_shutter="OFF",
            bulb_enabled=False,
            anti_flicker_shoot="OFF",
            simulate_bench_dry_run=True,
        )
        self.assertTrue(gd_ok.passed, gd_ok.errors)
        self.assertEqual(gd_ok.silent_mode, "ON")
        self.assertEqual(gd_ok.effective_shutter_type, "ELECTRONIC_SHUTTER")
        self.assertTrue(gd_ok.electronic_5function_lockout_verified)

        gd_audio, _ = evaluate_p284_check_group_d_shutter_type_drive_and_tier0(
            shutter_type="ELECTRONIC_SHUTTER",
            silent_mode="ON",
            audio_signals="ON",
            long_exposure_nr="OFF",
            e_front_curtain_shutter="OFF",
            simulate_bench_dry_run=True,
        )
        self.assertFalse(gd_audio.passed)
        self.assertTrue(any(P284_GD_ERR_SHUTTER_TYPE_2OPTION_NO_AUTO_OR_SILENT_LOCK in e for e in gd_audio.errors))

    def test_52_group_d_electronic_shutter_5_function_lockout_matrix(self) -> None:
        base_kw = dict(
            shutter_type="ELECTRONIC_SHUTTER",
            long_exposure_nr="OFF",
            e_front_curtain_shutter="OFF",
            flash_enabled=False,
            bulb_enabled=False,
            anti_flicker_shoot="OFF",
            simulate_bench_dry_run=True,
        )
        violations = [
            {"flash_enabled": True},
            {"long_exposure_nr": "ON"},
            {"e_front_curtain_shutter": "ON"},
            {"bulb_enabled": True},
            {"anti_flicker_shoot": "ON"},
        ]
        for v in violations:
            kw = dict(base_kw)
            kw.update(v)
            gd, _ = evaluate_p284_check_group_d_shutter_type_drive_and_tier0(**kw)
            self.assertFalse(gd.passed, f"Expected electronic 5-lockout failure for {v}")
            self.assertTrue(any(P284_GD_ERR_FLASH_SYNC_1_250_OR_ELECTRONIC_5LOCKOUT in e for e in gd.errors))

    def test_53_group_d_electronic_shutter_restricted_to_pasm_and_efront_survives_reset(self) -> None:
        gd_exp, _ = evaluate_p284_check_group_d_shutter_type_drive_and_tier0(
            shutter_type="ELECTRONIC_SHUTTER",
            exposure_mode="INTELLIGENT_AUTO",
            long_exposure_nr="OFF",
            e_front_curtain_shutter="OFF",
            simulate_bench_dry_run=True,
        )
        self.assertFalse(gd_exp.passed)
        self.assertTrue(any(P284_GD_ERR_SHUTTER_TYPE_2OPTION_NO_AUTO_OR_SILENT_LOCK in e for e in gd_exp.errors))

        gd_efront, _ = evaluate_p284_check_group_d_shutter_type_drive_and_tier0(
            e_front_curtain_survives_camera_reset=False,
            simulate_bench_dry_run=True,
        )
        self.assertFalse(gd_efront.passed)
        self.assertTrue(any(P284_GD_ERR_SHUTTER_TYPE_2OPTION_NO_AUTO_OR_SILENT_LOCK in e for e in gd_efront.errors))

    def test_54_group_d_flash_sync_1_250_ceiling_enforced(self) -> None:
        gd_ok, _ = evaluate_p284_check_group_d_shutter_type_drive_and_tier0(
            shutter_type="MECHANICAL_SHUTTER",
            flash_enabled=True,
            flash_sync_denominator=250,
            simulate_bench_dry_run=True,
        )
        self.assertTrue(gd_ok.passed, gd_ok.errors)

        gd_fast, _ = evaluate_p284_check_group_d_shutter_type_drive_and_tier0(
            shutter_type="MECHANICAL_SHUTTER",
            flash_enabled=True,
            flash_sync_denominator=500,
            simulate_bench_dry_run=True,
        )
        self.assertFalse(gd_fast.passed)
        self.assertTrue(any(P284_GD_ERR_FLASH_SYNC_1_250_OR_ELECTRONIC_5LOCKOUT in e for e in gd_fast.errors))

    def test_55_group_d_hi_plus_10fps_uncompressed_raw_and_f11_af_lock(self) -> None:
        gd_hip_ok, _ = evaluate_p284_check_group_d_shutter_type_drive_and_tier0(
            drive_mode="CONT_HI_PLUS",
            cont_fps=10,
            raw_file_type="COMPRESSED",
            aperture_f_number=2.8,
            long_exposure_nr="OFF",
            simulate_bench_dry_run=True,
        )
        self.assertTrue(gd_hip_ok.passed, gd_hip_ok.errors)

        gd_over_10, _ = evaluate_p284_check_group_d_shutter_type_drive_and_tier0(
            drive_mode="CONT_HI_PLUS",
            cont_fps=12,
            long_exposure_nr="OFF",
            simulate_bench_dry_run=True,
        )
        self.assertFalse(gd_over_10.passed)
        self.assertTrue(any(P284_GD_ERR_DRIVE_HIP_10FPS_OR_F11_AF_LOCK_OR_NR_RULE in e for e in gd_over_10.errors))

        gd_uncomp_drop, _ = evaluate_p284_check_group_d_shutter_type_drive_and_tier0(
            drive_mode="CONT_HI_PLUS",
            cont_fps=10,
            raw_file_type="UNCOMPRESSED",
            long_exposure_nr="OFF",
            simulate_bench_dry_run=True,
        )
        self.assertFalse(gd_uncomp_drop.passed)
        self.assertTrue(any(P284_GD_ERR_DRIVE_HIP_10FPS_OR_F11_AF_LOCK_OR_NR_RULE in e for e in gd_uncomp_drop.errors))

        gd_f16_claim, _ = evaluate_p284_check_group_d_shutter_type_drive_and_tier0(
            drive_mode="CONT_HI_PLUS",
            cont_fps=10,
            aperture_f_number=16.0,
            expect_af_tracks_all_frames_above_f11=True,
            long_exposure_nr="OFF",
            simulate_bench_dry_run=True,
        )
        self.assertFalse(gd_f16_claim.passed)
        self.assertTrue(any(P284_GD_ERR_DRIVE_HIP_10FPS_OR_F11_AF_LOCK_OR_NR_RULE in e for e in gd_f16_claim.errors))

    def test_56_group_d_high_iso_nr_raw_invariance_and_cont_lenr_lockout(self) -> None:
        gd_raw_nr, _ = evaluate_p284_check_group_d_shutter_type_drive_and_tier0(
            still_file_format="RAW",
            expect_high_iso_nr_applies_to_raw=True,
            simulate_bench_dry_run=True,
        )
        self.assertFalse(gd_raw_nr.passed)
        self.assertTrue(any(P284_GD_ERR_DRIVE_HIP_10FPS_OR_F11_AF_LOCK_OR_NR_RULE in e for e in gd_raw_nr.errors))

        gd_cont_lenr, _ = evaluate_p284_check_group_d_shutter_type_drive_and_tier0(
            drive_mode="CONT_HI",
            cont_fps=8,
            long_exposure_nr="ON",
            simulate_bench_dry_run=True,
        )
        self.assertFalse(gd_cont_lenr.passed)
        self.assertTrue(any(P284_GD_ERR_DRIVE_HIP_10FPS_OR_F11_AF_LOCK_OR_NR_RULE in e for e in gd_cont_lenr.errors))

    def test_57_group_d_h0_h3_drift_and_passive_tx_violations_block(self) -> None:
        gd_drift, _ = evaluate_p284_check_group_d_shutter_type_drive_and_tier0(
            simulated_h0_h3_drifted_surfaces=1,
            simulate_bench_dry_run=True,
        )
        self.assertFalse(gd_drift.passed)
        self.assertTrue(any(P284_GD_ERR_H0_H3_IMMUTABILITY_DRIFT in e for e in gd_drift.errors))

        gd_tx, _ = evaluate_p284_check_group_d_shutter_type_drive_and_tier0(
            simulated_passive_tx_bytes=32,
            simulate_bench_dry_run=True,
        )
        self.assertFalse(gd_tx.passed)
        self.assertEqual(gd_tx.passive_tx_bytes_emitted, 32)

    def test_58_group_d_tier0_valid_dual_media_receipts_distinct_st_dev_pass(self) -> None:
        raw_a, raw_b, h0 = build_simulated_phase284_tier0_receipts()
        self.assertEqual(len(raw_a), 528)
        self.assertEqual(raw_a, raw_b)
        gd, tier0_err = evaluate_p284_check_group_d_shutter_type_drive_and_tier0(
            receipt_a_bytes=raw_a,
            receipt_b_bytes=raw_b,
            st_dev_a_override=1001,
            st_dev_b_override=2002,
            body_serial=DEFAULT_TARGET_BODY_SERIAL,
            emmc_cid=DEFAULT_TARGET_EMMC_CID,
            h0_baselines_a=h0,
            h0_baselines_b=h0,
            simulate_bench_dry_run=False,
        )
        self.assertTrue(gd.passed, gd.errors)
        self.assertTrue(gd.tier0_receipt_verified, tier0_err)
        self.assertEqual(len(tier0_err), 0)

    def test_59_group_d_tier0_same_st_dev_rejected(self) -> None:
        raw_a, raw_b, h0 = build_simulated_phase284_tier0_receipts()
        gd, tier0_err = evaluate_p284_check_group_d_shutter_type_drive_and_tier0(
            receipt_a_bytes=raw_a,
            receipt_b_bytes=raw_b,
            st_dev_a_override=777,
            st_dev_b_override=777,
            body_serial=DEFAULT_TARGET_BODY_SERIAL,
            emmc_cid=DEFAULT_TARGET_EMMC_CID,
            h0_baselines_a=h0,
            h0_baselines_b=h0,
        )
        self.assertFalse(gd.tier0_receipt_verified)
        self.assertFalse(gd.distinct_physical_media_verified)
        self.assertTrue(any("st_dev_a == st_dev_b" in e for e in tier0_err))

    def test_60_group_d_tier0_corrupt_crc_or_copy_mismatch_rejected(self) -> None:
        raw_a, raw_b, h0 = build_simulated_phase284_tier0_receipts()
        corrupt = bytearray(raw_b)
        corrupt[-1] ^= 0xFF
        gd_mismatch, tier0_mismatch = evaluate_p284_check_group_d_shutter_type_drive_and_tier0(
            receipt_a_bytes=raw_a,
            receipt_b_bytes=bytes(corrupt),
            st_dev_a_override=1,
            st_dev_b_override=2,
            body_serial=DEFAULT_TARGET_BODY_SERIAL,
            emmc_cid=DEFAULT_TARGET_EMMC_CID,
            h0_baselines_a=h0,
            h0_baselines_b=h0,
        )
        self.assertFalse(gd_mismatch.tier0_receipt_verified)
        self.assertTrue(tier0_mismatch)

        gd_crc, tier0_crc = evaluate_p284_check_group_d_shutter_type_drive_and_tier0(
            receipt_a_bytes=bytes(corrupt),
            receipt_b_bytes=bytes(corrupt),
            st_dev_a_override=1,
            st_dev_b_override=2,
            body_serial=DEFAULT_TARGET_BODY_SERIAL,
            emmc_cid=DEFAULT_TARGET_EMMC_CID,
            h0_baselines_a=h0,
            h0_baselines_b=h0,
        )
        self.assertFalse(gd_crc.tier0_receipt_verified)
        self.assertTrue(any("CRC32" in e or "corrupt" in e for e in tier0_crc))

    def test_61_group_d_tier0_trivial_serial_or_bad_h0_rejected(self) -> None:
        raw_a, raw_b, h0 = build_simulated_phase284_tier0_receipts()
        gd_ser, _ = evaluate_p284_check_group_d_shutter_type_drive_and_tier0(
            receipt_a_bytes=raw_a,
            receipt_b_bytes=raw_b,
            st_dev_a_override=1,
            st_dev_b_override=2,
            body_serial="0000000",
            emmc_cid=DEFAULT_TARGET_EMMC_CID,
            h0_baselines_a=h0,
            h0_baselines_b=h0,
        )
        self.assertFalse(gd_ser.tier0_receipt_verified)

        bad_h0 = dict(h0)
        first_k = next(iter(bad_h0))
        bad_h0[first_k] = "0" * 64
        gd_h0, err_h0 = evaluate_p284_check_group_d_shutter_type_drive_and_tier0(
            receipt_a_bytes=raw_a,
            receipt_b_bytes=raw_b,
            st_dev_a_override=1,
            st_dev_b_override=2,
            body_serial=DEFAULT_TARGET_BODY_SERIAL,
            emmc_cid=DEFAULT_TARGET_EMMC_CID,
            h0_baselines_a=h0,
            h0_baselines_b=bad_h0,
        )
        self.assertFalse(gd_h0.tier0_receipt_verified)
        self.assertTrue(any("H0" in e for e in err_h0))

    def test_62_group_d_tier0_missing_receipt_file_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            gd, tier0_err = evaluate_p284_check_group_d_shutter_type_drive_and_tier0(
                receipt_a_path=Path(tmp) / "missing_a.bin",
                receipt_b_path=Path(tmp) / "missing_b.bin",
            )
            self.assertFalse(gd.tier0_receipt_verified)
            self.assertTrue(any("read failed" in e for e in tier0_err))

    # --- Orchestrator, Tamper Resistance, Markdown & CLI Subprocess (10 tests) ---

    def test_63_orchestrator_offline_fail_closed_both_modes(self) -> None:
        for clean in (None, True):
            rep = evaluate_realhw_pp_scinetone_wb_metering_and_shutter_type_readiness(
                force_clean_room=clean,
                simulate_bench_dry_run=False,
            )
            self.assertEqual(rep.overall_status, P284_OVERALL_READY_OFFLINE_AWAITING_BENCH_RECEIPTS)
            self.assertEqual(rep.go_no_go, GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT)
            self.assertTrue(rep.all_4_check_groups_passed)
            self.assertFalse(rep.tier0_receipt_verified)
            self.assertFalse(rep.overall_ready_for_hardware_attach)
            self.assertFalse(rep.hardware_live_attachment_authorized)
            self.assertFalse(rep.persistent_emmc_writes_authorized)
            self.assertFalse(rep.lossless_comp_exposed_in_fx3_ui)
            self.assertFalse(rep.shutter_type_auto_exposed_in_fx3_ui)
            self.assertEqual(rep.usb_packets_transmitted, 0)
            self.assertEqual(rep.raw_firmware_bytes_leaked, 0)
            self.assertEqual(rep.passive_tx_bytes_emitted, 0)
            self.assertEqual(rep.h0_equals_h3_count, 16)
            self.assertTrue(verify_phase284_report(rep.to_dict()).valid)

    def test_64_orchestrator_simulate_bench_dry_run_both_modes(self) -> None:
        for clean in (None, True):
            rep = evaluate_realhw_pp_scinetone_wb_metering_and_shutter_type_readiness(
                force_clean_room=clean,
                simulate_bench_dry_run=True,
            )
            self.assertEqual(rep.overall_status, GO_NO_GO_DRY_RUN_SIMULATED_READY)
            self.assertEqual(rep.go_no_go, GO_NO_GO_DRY_RUN_SIMULATED_READY)
            self.assertEqual(rep.check_groups_passed, 4)
            self.assertTrue(rep.all_4_check_groups_passed)
            self.assertTrue(rep.tier0_receipt_verified)
            self.assertEqual(rep.h0_equals_h3_count, 16)
            self.assertEqual(rep.h0_h3_surface_count, 16)
            self.assertFalse(rep.overall_ready_for_hardware_attach)
            self.assertFalse(rep.hardware_live_attachment_authorized)
            self.assertFalse(rep.persistent_emmc_writes_authorized)
            self.assertTrue(verify_phase284_report(rep.to_dict()).valid)

    def test_65_orchestrator_deterministic_sha256_and_receipt_verified_verdict(self) -> None:
        rep_a = evaluate_realhw_pp_scinetone_wb_metering_and_shutter_type_readiness(
            force_clean_room=True,
            simulate_bench_dry_run=True,
        )
        rep_b = evaluate_realhw_pp_scinetone_wb_metering_and_shutter_type_readiness(
            force_clean_room=True,
            simulate_bench_dry_run=True,
        )
        self.assertEqual(rep_a.report_sha256, rep_b.report_sha256)

        raw_a, raw_b, h0 = build_simulated_phase284_tier0_receipts()
        rep_phys = evaluate_realhw_pp_scinetone_wb_metering_and_shutter_type_readiness(
            force_clean_room=True,
            simulate_bench_dry_run=False,
            receipt_a_bytes=raw_a,
            receipt_b_bytes=raw_b,
            st_dev_a_override=11,
            st_dev_b_override=22,
            body_serial=DEFAULT_TARGET_BODY_SERIAL,
            emmc_cid=DEFAULT_TARGET_EMMC_CID,
            h0_baselines_a=h0,
            h0_baselines_b=h0,
        )
        self.assertEqual(rep_phys.go_no_go, P284_GO_NO_GO_PP_SCINETONE_WB_METERING_SHUTTER_TYPE_VERIFIED)
        self.assertTrue(verify_phase284_report(rep_phys.to_dict()).valid)

    def test_66_orchestrator_failure_sets_blocked_failure_verdict(self) -> None:
        rep = evaluate_realhw_pp_scinetone_wb_metering_and_shutter_type_readiness(
            force_clean_room=True,
            simulate_bench_dry_run=True,
            expect_lossless_comp_raw=True,
        )
        self.assertFalse(rep.all_4_check_groups_passed)
        self.assertEqual(
            rep.go_no_go,
            P284_GO_NO_GO_BLOCKED_PP_SCINETONE_WB_METERING_SHUTTER_TYPE_FAILURE,
        )
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertTrue(verify_phase284_report(rep.to_dict()).valid)

    def test_67_verify_report_rejects_safety_lock_and_zero_counter_tampering(self) -> None:
        base = evaluate_realhw_pp_scinetone_wb_metering_and_shutter_type_readiness(
            force_clean_room=True,
            simulate_bench_dry_run=True,
        ).to_dict()

        for lock_key in (
            "overall_ready_for_hardware_attach",
            "hardware_live_attachment_authorized",
            "persistent_emmc_writes_authorized",
            "persistent_write_release",
            "spi_nor_write_authorized",
            "el3_payload_transmit_authorized",
            "sd_physical_media_written",
            "lossless_comp_exposed_in_fx3_ui",
            "shutter_type_auto_exposed_in_fx3_ui",
        ):
            tampered = dict(base)
            tampered[lock_key] = True
            res = verify_phase284_report(tampered)
            self.assertFalse(res.valid, f"Expected tamper rejection on {lock_key}")

        for zero_key in (
            "usb_packets_transmitted",
            "physical_usb_packets_emitted",
            "raw_firmware_bytes_leaked",
            "passive_tx_bytes_emitted",
        ):
            tampered = dict(base)
            tampered[zero_key] = 1
            res = verify_phase284_report(tampered)
            self.assertFalse(res.valid, f"Expected tamper rejection on {zero_key}")

    def test_68_verify_report_rejects_dry_run_claiming_verified_and_digest_tamper(self) -> None:
        base = evaluate_realhw_pp_scinetone_wb_metering_and_shutter_type_readiness(
            force_clean_room=True,
            simulate_bench_dry_run=True,
        ).to_dict()

        spoof_verified = dict(base)
        spoof_verified["go_no_go"] = P284_GO_NO_GO_PP_SCINETONE_WB_METERING_SHUTTER_TYPE_VERIFIED
        self.assertFalse(verify_phase284_report(spoof_verified).valid)

        spoof_sha = dict(base)
        spoof_sha["report_sha256"] = "a" * 64
        res = verify_phase284_report(spoof_sha)
        self.assertFalse(res.valid)
        self.assertTrue(any("digest" in e for e in res.errors))

    def test_69_render_phase284_markdown_contains_all_groups_and_locks(self) -> None:
        rep = evaluate_realhw_pp_scinetone_wb_metering_and_shutter_type_readiness(
            force_clean_room=True,
            simulate_bench_dry_run=True,
        )
        md = render_phase284_markdown(rep)
        self.assertIn("Phase 284", md)
        self.assertIn(P284_CHECK_GROUP_A_ID, md)
        self.assertIn(P284_CHECK_GROUP_B_ID, md)
        self.assertIn(P284_CHECK_GROUP_C_ID, md)
        self.assertIn(P284_CHECK_GROUP_D_ID, md)
        self.assertIn("lossless_comp=False", md)
        self.assertIn("shutter_auto=False", md)
        self.assertIn(rep.report_sha256, md)

    def test_70_cli_inprocess_dry_run_and_offline_exit_codes(self) -> None:
        buf_dry = io.StringIO()
        with mock.patch("sys.stdout", buf_dry):
            rc_dry = cli_main(
                [
                    "preflight-pp-scinetone-wb-metering-and-shutter-type",
                    "--force-clean-room",
                    "--simulate-bench-dry-run",
                    "--json",
                ]
            )
        self.assertEqual(rc_dry, 0)
        payload_dry = json.loads(buf_dry.getvalue())
        self.assertEqual(payload_dry["go_no_go"], GO_NO_GO_DRY_RUN_SIMULATED_READY)
        self.assertTrue(verify_phase284_report(payload_dry).valid)

        buf_off = io.StringIO()
        with mock.patch("sys.stdout", buf_off):
            rc_off = cli_main(
                [
                    "preflight-pp-scinetone-wb-metering-and-shutter-type",
                    "--force-clean-room",
                    "--json",
                ]
            )
        self.assertEqual(rc_off, 2)
        payload_off = json.loads(buf_off.getvalue())
        self.assertEqual(payload_off["go_no_go"], GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT)

    def test_71_cli_inprocess_writes_json_and_markdown_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            json_out = Path(tmp) / "ph284.json"
            md_out = Path(tmp) / "ph284.md"
            buf = io.StringIO()
            with mock.patch("sys.stdout", buf):
                rc = cli_main(
                    [
                        "preflight-pp-scinetone-wb-metering-and-shutter-type",
                        "--force-clean-room",
                        "--simulate-bench-dry-run",
                        "--output",
                        str(json_out),
                        "--markdown-out",
                        str(md_out),
                        "--json",
                    ]
                )
            self.assertEqual(rc, 0)
            self.assertTrue(json_out.is_file())
            self.assertTrue(md_out.is_file())
            loaded = json.loads(json_out.read_text(encoding="utf-8"))
            self.assertTrue(verify_phase284_report(loaded).valid)
            self.assertIn(loaded["report_sha256"], md_out.read_text(encoding="utf-8"))

    def test_72_cli_subprocess_sys_executable_both_modes_within_budget(self) -> None:
        timeout_sec = _subprocess_subprocess_budget = _ci_subprocess_timeout()
        t0 = time.monotonic()
        proc_dry = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "fx6_closure",
                "preflight-pp-scinetone-wb-metering-and-shutter-type",
                "--simulate-bench-dry-run",
                "--json",
            ],
            cwd=str(REPO_ROOT),
            env=_subprocess_env(clean_room=False),
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            check=False,
        )
        elapsed_dry = time.monotonic() - t0
        self.assertEqual(proc_dry.returncode, 0, proc_dry.stderr)
        self.assertLessEqual(elapsed_dry, _subprocess_subprocess_budget)
        payload_dry = json.loads(proc_dry.stdout)
        self.assertEqual(payload_dry["go_no_go"], GO_NO_GO_DRY_RUN_SIMULATED_READY)
        self.assertTrue(verify_phase284_report(payload_dry).valid)

        proc_cr_off = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "fx6_closure",
                "preflight-pp-scinetone-wb-metering-and-shutter-type",
                "--force-clean-room",
                "--json",
            ],
            cwd=str(REPO_ROOT),
            env=_subprocess_env(clean_room=True),
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            check=False,
        )
        self.assertEqual(proc_cr_off.returncode, 2, proc_cr_off.stderr)
        payload_cr_off = json.loads(proc_cr_off.stdout)
        self.assertEqual(payload_cr_off["verification_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(
            payload_cr_off["go_no_go"],
            GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT,
        )


if __name__ == "__main__":
    unittest.main()
