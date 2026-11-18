"""Dual-mode unit tests (84 cases) for Phase 302 (`preflight-lens-comp-af-illuminator-copy-slot-and-evf-absence`):
11th Real-Hardware Physical Bench Readiness Verifier across Waves 53-55 check groups (`A..D`).

Runs deterministically across `LOCAL_DONOR_O_RDONLY`, `FX3_CLEAN_ROOM_TEST=1`, and
`FX3_FX6_FORCE_CLEAN_ROOM=1` modes with zero `.pyc` emission, zero persistent writes,
and cross-platform CI (`sys.executable` + `15.0s` timing headroom).
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

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
from fx6_closure.realhw_card_insert_readiness_verifier import (  # noqa: E402
    GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT,
    GO_NO_GO_DRY_RUN_SIMULATED_READY,
)
from fx6_closure.realhw_sd_stageb_bundle_and_uninstaller import (  # noqa: E402
    DEFAULT_TARGET_BODY_SERIAL,
    DEFAULT_TARGET_EMMC_CID,
)
from fx6_closure.realhw_lens_comp_af_illuminator_copy_slot_and_evf_absence_verifier import (  # noqa: E402
    P302_AEL_WITH_SHUTTER_THREE_MODES,
    P302_AF_ASSIST_RESID16_HEX,
    P302_AF_ILLUMINATOR_BKID,
    P302_AF_ILLUMINATOR_RANGE_MAX_M,
    P302_AF_ILLUMINATOR_RANGE_MIN_M,
    P302_AF_ILLUMINATOR_RESID16_HEX,
    P302_AF_ILLUMINATOR_UXC_RESID16_HEX,
    P302_AF_SUBJ_SHIFT_SENS_MAX,
    P302_AF_SUBJ_SHIFT_SENS_MIN,
    P302_AF_SUBJ_SHIFT_SENS_RESID16_HEX,
    P302_AF_TRANSITION_SPEED_MAX,
    P302_AF_TRANSITION_SPEED_MIN,
    P302_AF_TRANSITION_SPEED_RESID16_HEX,
    P302_AF_WITH_SHUTTER_RESID16_HEX,
    P302_APERTURE_DRIVE_IN_AF_RESID16_HEX,
    P302_APERTURE_DRIVE_THREE_MODES,
    P302_BRACKET_ORDER_MODES,
    P302_BRACKET_SELFTIMER_MODES,
    P302_BREATHING_COMP_RESID16_HEX,
    P302_CHECK_GROUP_A_ID,
    P302_CHECK_GROUP_B_ID,
    P302_CHECK_GROUP_C_ID,
    P302_CHECK_GROUP_D_ID,
    P302_CHROMA_ABERRATION_RESID16_HEX,
    P302_CIRC_FOCUS_POINT_RESID16_HEX,
    P302_DISP_MONITOR_PLAYBACK_THREE_MODES,
    P302_DISP_MONITOR_SHOOT_FOUR_MODES,
    P302_DISTORTION_COMP_RESID16_HEX,
    P302_DORMANT_EVF_FINDER_TRAPS,
    P302_DORMANT_FOCUS_AREAS,
    P302_DORMANT_PLAYBACK_EDIT_TRAPS,
    P302_DORMANT_SHADING_AUTO_LOW_RESID16_HEX,
    P302_DORMANT_SHADING_AUTO_LOW_SYMBOL,
    P302_DORMANT_TOUCH_TRAPS,
    P302_ERRNO_EBUSY,
    P302_ERRNO_EOPNOTSUPP,
    P302_ERRNO_EROFS,
    P302_EXPOSURE_STD_ADJUST_5_METERING_MODES,
    P302_EXPOSURE_STD_ADJUST_EV_MAX,
    P302_EXPOSURE_STD_ADJUST_EV_MIN,
    P302_EXPOSURE_STD_ADJUST_RESID16_HEX,
    P302_FOCUS_AREA_COLOR_RESID16_HEX,
    P302_FOCUS_AREA_LIMIT_14_ITEMS,
    P302_FOCUS_AREA_LIMIT_MIN_SELECTED,
    P302_FOCUS_AREA_LIMIT_MIN_SELECTED_RESID16_HEX,
    P302_FOCUS_AREA_LIMIT_RESID16_HEX,
    P302_FOLDER_NAME_MAX_IMAGES,
    P302_GA_ERR_AF_FIVE_PARAMS_PERSISTENCE_OR_CIRC,
    P302_GA_ERR_AF_ILLUMINATOR_OR_FX6_ABSENCE,
    P302_GA_ERR_FOLDER_OR_RATING_SLOT1_VAULT_EROFS,
    P302_GA_ERR_LENS_COMP_LOCK_OR_RESET_BOUNDARY,
    P302_GA_ERR_MODEL_OR_FW_FLOOR,
    P302_GA_ERR_SHADING_AUTO_LOW_EOPNOTSUPP,
    P302_GB_ERR_EXPOSURE_STD_ADJUST_5MODE_OR_BRACKET,
    P302_GB_ERR_FOCUS_AREA_LIMIT_14_OR_MIN2,
    P302_GB_ERR_PLAYBACK_COPY_REVERSE_SLOT1_VAULT_TRAP,
    P302_GB_ERR_SLIDESHOW_BOUNDARY,
    P302_GB_ERR_SWITCH_VH_AF_AREA_GATE,
    P302_GB_ERR_TC_FORMAT_NDF_PAL_OR_BNC_ABSENCE,
    P302_GC_ERR_AEL_SHUTTER_OR_FLASH_STILL_GATE,
    P302_GC_ERR_DISP_4MODE_SHOOT_3MODE_PLAYBACK,
    P302_GC_ERR_INTERVAL_SPEED_1TO9_OR_EDIT_VAULT_GUARD,
    P302_GC_ERR_TOUCH_SHOOTING_3MODE_OR_DORMANT_TRAP,
    P302_GC_ERR_ZERO_EVF_BLACK_SCREEN_LOCKOUT_TRAP,
    P302_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION,
    P302_GD_ERR_H0_H3_IMMUTABILITY_DRIFT,
    P302_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID,
    P302_GO_NO_GO_BLOCKED_LENS_COMP_AF_ILLUMINATOR_COPY_SLOT_EVF_ABSENCE_FAILURE,
    P302_GO_NO_GO_LENS_COMP_AF_ILLUMINATOR_COPY_SLOT_EVF_ABSENCE_VERIFIED,
    P302_INTERVAL_PLAY_SPEED_DEFAULT,
    P302_INTERVAL_PLAY_SPEED_MAX,
    P302_INTERVAL_PLAY_SPEED_MIN,
    P302_LENS_COMP_RESID16_HEX,
    P302_OVERALL_READY_OFFLINE_AWAITING_BENCH_RECEIPTS,
    P302_PLAYBACK_COPY_FUNC,
    P302_PLAYBACK_COPY_RESID16_HEX,
    P302_PLAYBACK_EDIT_ACTIVE_ITEMS,
    P302_PRE_AF_RESID16_HEX,
    P302_SCHEMA,
    P302_SHADING_COMP_BKID,
    P302_SHADING_COMP_RESID16_HEX,
    P302_SHADING_TWO_MODES,
    P302_SLIDE_SHOW_INTERVALS_SEC,
    P302_SLIDE_SHOW_VIEW_MODES,
    P302_SONY_HELP_GUIDE_ID,
    P302_STILL_RATING_MAX_STARS,
    P302_STILL_RATING_MIN_STARS,
    P302_SWITCH_VH_AF_AREA_RESID16_HEX,
    P302_TC_NDF_LOCKED_FRAME_RATES,
    P302_TOUCH_FUNC_SHOOTING_THREE_MODES,
    P302_TOUCH_SENSITIVITY_TWO_MODES,
    PHASE302_PASSIVE_TX_BYTES_EMITTED,
    PHASE302_RAW_FIRMWARE_BYTES_LEAKED,
    PHASE302_USB_PACKETS_TRANSMITTED,
    PHASE_302_CHECK_GROUP_IDS,
    PHASE_302_SCHEMA,
    PHASE_302_VERSION,
    build_simulated_phase302_tier0_receipts,
    evaluate_p302_check_group_a_lens_comp_af_illum_folder_rating,
    evaluate_p302_check_group_b_switch_vh_limit14_stdadj_tc_and_copy_slot1,
    evaluate_p302_check_group_c_touch_disp_evf_absence_ael_flash_and_interval,
    evaluate_p302_check_group_d_physical_bench_and_tier0,
    evaluate_realhw_lens_comp_af_illuminator_copy_slot_and_evf_absence_readiness,
    inspect_phase302_donors_bounded,
    render_phase302_markdown,
    run_lens_comp_af_illuminator_copy_slot_and_evf_absence_preflight,
    verify_phase302_report,
)


def _ci_subprocess_timeout() -> float:
    return 25.0 if os.environ.get("GITHUB_ACTIONS") == "true" else 12.0


def _ci_timing_budget(local_seconds: float) -> float:
    return local_seconds + (15.0 if os.environ.get("GITHUB_ACTIONS") == "true" else 0.0)


def _subprocess_env(*, clean_room: bool = False, force_clean_room_var: bool = False) -> dict[str, str]:
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPATH"] = os.pathsep.join(
        str(REPO_ROOT / rel)
        for rel in (
            "outputs/fx6-on-fx3-closure",
            "outputs/fx3-safety",
            "outputs/fx3-recovery-adapter",
            "outputs/fx3-firmware-lab",
            "outputs/fx3-vm",
        )
    )
    if clean_room:
        env["FX3_CLEAN_ROOM_TEST"] = "1"
    else:
        env.pop("FX3_CLEAN_ROOM_TEST", None)
    if force_clean_room_var:
        env["FX3_FX6_FORCE_CLEAN_ROOM"] = "1"
    else:
        env.pop("FX3_FX6_FORCE_CLEAN_ROOM", None)
    return env


class Phase302RealHwLensCompAfIlluminatorCopySlotEvfAbsenceTests(unittest.TestCase):
    """84 dual-mode tests covering Phase 302 Wave 53-55 contracts & CLI gates."""

    # --- Section 1: Exports, Constants & Bounded O_RDONLY Donor Inspection (8 tests) ---

    def test_01_exports_and_non_shadowing_alongside_ph291_and_ph284(self) -> None:
        self.assertGreaterEqual(len(fx6_closure.__all__), 300)
        for sym in (
            "PHASE_302_SCHEMA",
            "P302_SCHEMA",
            "P302_CHECK_GROUP_A_ID",
            "P302_CHECK_GROUP_B_ID",
            "P302_CHECK_GROUP_C_ID",
            "P302_CHECK_GROUP_D_ID",
            "P302CheckGroupALensCompAfIllumFolderRatingResult",
            "P302CheckGroupBSwitchVhLimit14StdAdjTcCopyResult",
            "P302CheckGroupCTouchDispEvfAbsenceAelIntervalResult",
            "P302CheckGroupDPhysicalBenchAndTier0Result",
            "inspect_phase302_donors_bounded",
            "evaluate_realhw_lens_comp_af_illuminator_copy_slot_and_evf_absence_readiness",
            "run_lens_comp_af_illuminator_copy_slot_and_evf_absence_preflight",
            "verify_phase302_report",
            "render_phase302_markdown",
            # Ph291 & Ph284 & Ph295 exports must remain unshadowed
            "evaluate_realhw_focus_area_zoom_dci4k_and_sensor_cleaning_readiness",
            "evaluate_realhw_pp_scinetone_wb_metering_and_shutter_type_readiness",
            "evaluate_realhw_milestone295_master_gate",
        ):
            self.assertIn(sym, fx6_closure.__all__)
            self.assertTrue(hasattr(fx6_closure, sym), msg=f"Missing export {sym}")

    def test_02_constants_and_uxc_resid16_pinning(self) -> None:
        self.assertEqual(P302_SCHEMA, PHASE_302_SCHEMA)
        self.assertEqual(PHASE_302_VERSION, "302.0.0")
        self.assertEqual(P302_SONY_HELP_GUIDE_ID, "ilc/2210")
        self.assertEqual(len(PHASE_302_CHECK_GROUP_IDS), 4)
        self.assertEqual(P302_ERRNO_EBUSY, 16)
        self.assertEqual(P302_ERRNO_EROFS, 30)
        self.assertEqual(P302_ERRNO_EOPNOTSUPP, 95)
        self.assertEqual(P302_LENS_COMP_RESID16_HEX, "0x75c8")
        self.assertEqual(P302_SHADING_COMP_RESID16_HEX, "0x64e1")
        self.assertEqual(P302_SHADING_COMP_BKID, "BKID_APP_setting_lens_comp_shading")
        self.assertEqual(P302_DORMANT_SHADING_AUTO_LOW_RESID16_HEX, "0x6c9c")
        self.assertEqual(P302_DORMANT_SHADING_AUTO_LOW_SYMBOL, "LENS_COMP_SHADING_AUTO_LOW")
        self.assertEqual(P302_SHADING_TWO_MODES, ("AUTO", "OFF"))
        self.assertEqual(P302_CHROMA_ABERRATION_RESID16_HEX, "0x68cd")
        self.assertEqual(P302_DISTORTION_COMP_RESID16_HEX, "0x6200")
        self.assertEqual(P302_BREATHING_COMP_RESID16_HEX, "0x73ea")
        self.assertEqual(P302_AF_ILLUMINATOR_RESID16_HEX, "0x69c0")
        self.assertEqual(P302_AF_ILLUMINATOR_UXC_RESID16_HEX, "0xe07f")
        self.assertEqual(P302_AF_ILLUMINATOR_BKID, "BKID_APP_setting_still_image_af_illuminator")
        self.assertAlmostEqual(P302_AF_ILLUMINATOR_RANGE_MIN_M, 0.3)
        self.assertAlmostEqual(P302_AF_ILLUMINATOR_RANGE_MAX_M, 3.0)
        self.assertEqual((P302_AF_TRANSITION_SPEED_MIN, P302_AF_TRANSITION_SPEED_MAX), (1, 7))
        self.assertEqual((P302_AF_SUBJ_SHIFT_SENS_MIN, P302_AF_SUBJ_SHIFT_SENS_MAX), (1, 5))
        self.assertEqual(P302_AF_TRANSITION_SPEED_RESID16_HEX, "0x6e9d")
        self.assertEqual(P302_AF_SUBJ_SHIFT_SENS_RESID16_HEX, "0x79d6")
        self.assertEqual(P302_AF_ASSIST_RESID16_HEX, "0x64a9")
        self.assertEqual(P302_APERTURE_DRIVE_IN_AF_RESID16_HEX, "0x7879")
        self.assertEqual(P302_AF_WITH_SHUTTER_RESID16_HEX, "0x771d")
        self.assertEqual(P302_PRE_AF_RESID16_HEX, "0x76d8")
        self.assertEqual(P302_CIRC_FOCUS_POINT_RESID16_HEX, "0x74f6")
        self.assertEqual(P302_FOCUS_AREA_COLOR_RESID16_HEX, "0x74ad")
        self.assertEqual(P302_SWITCH_VH_AF_AREA_RESID16_HEX, "0x73ae")
        self.assertEqual(P302_FOCUS_AREA_LIMIT_RESID16_HEX, "0x6de2")
        self.assertEqual(P302_FOCUS_AREA_LIMIT_MIN_SELECTED_RESID16_HEX, "0xea28")
        self.assertEqual(P302_FOCUS_AREA_LIMIT_MIN_SELECTED, 2)
        self.assertEqual(len(P302_FOCUS_AREA_LIMIT_14_ITEMS), 14)
        self.assertEqual(len(P302_EXPOSURE_STD_ADJUST_5_METERING_MODES), 5)
        self.assertEqual(P302_EXPOSURE_STD_ADJUST_RESID16_HEX, "0x6114")
        self.assertEqual(P302_PLAYBACK_COPY_RESID16_HEX, "0x79fc")
        self.assertEqual(P302_PLAYBACK_COPY_FUNC, "FUNC_copy_content")
        self.assertEqual(len(P302_TOUCH_FUNC_SHOOTING_THREE_MODES), 3)
        self.assertEqual(len(P302_DISP_MONITOR_SHOOT_FOUR_MODES), 4)
        self.assertEqual(len(P302_DISP_MONITOR_PLAYBACK_THREE_MODES), 3)
        self.assertEqual((P302_INTERVAL_PLAY_SPEED_MIN, P302_INTERVAL_PLAY_SPEED_DEFAULT, P302_INTERVAL_PLAY_SPEED_MAX), (1, 5, 9))

    def test_03_donor_inspection_local_o_rdonly_and_150ms_budget(self) -> None:
        from fx6_closure.donor_paths import resolve_work_subpath
        from fx6_closure.realhw_sd_stageb_bundle_and_uninstaller import FX3_IM_ELF_RELPATH

        env_clean = (
            os.environ.get("FX3_CLEAN_ROOM_TEST", "").strip().lower() in ("1", "true", "yes")
            or os.environ.get("FX3_FX6_FORCE_CLEAN_ROOM", "").strip().lower() in ("1", "true", "yes")
        )
        donors_available = resolve_work_subpath(FX3_IM_ELF_RELPATH, require_file=False).is_file()
        t0 = time.perf_counter()
        res = inspect_phase302_donors_bounded()
        dt = time.perf_counter() - t0
        self.assertTrue(res.passed, msg=res.errors)
        self.assertEqual(res.raw_firmware_bytes_leaked, 0)
        self.assertLess(dt, _ci_timing_budget(1.0))
        if not env_clean and donors_available:
            self.assertEqual(res.verification_mode, "LOCAL_DONOR_O_RDONLY")
            self.assertTrue(res.appfw_is_aarch64_elf)
            self.assertTrue(res.upm_ko_is_aarch64_elf)
            self.assertTrue(res.within_150ms_budget)
        else:
            self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_04_donor_inspection_clean_room_env_fx3_clean_room_test_1(self) -> None:
        with mock.patch.dict(os.environ, {"FX3_CLEAN_ROOM_TEST": "1"}, clear=False):
            res = inspect_phase302_donors_bounded()
        self.assertTrue(res.passed)
        self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(res.raw_firmware_bytes_leaked, 0)

    def test_05_donor_inspection_force_clean_room_env_and_explicit_flag(self) -> None:
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}, clear=False):
            res_env = inspect_phase302_donors_bounded()
        self.assertTrue(res_env.passed)
        self.assertEqual(res_env.verification_mode, "CLEAN_ROOM_SYNTHETIC")

        res_arg = inspect_phase302_donors_bounded(force_clean_room=True)
        self.assertTrue(res_arg.passed)
        self.assertEqual(res_arg.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_06_donor_inspection_missing_donors_fail_closed_when_force_clean_room_false(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            res = inspect_phase302_donors_bounded(
                fx6_lib_dir=Path(td) / "missing_lib",
                fx3_modules_dir=Path(td) / "missing_mod",
                force_clean_room=False,
            )
        self.assertFalse(res.passed)
        self.assertEqual(res.verification_mode, "LOCAL_DONOR_O_RDONLY")
        self.assertGreaterEqual(len(res.errors), 1)

    def test_07_donor_inspection_corrupted_donor_file_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            lib_dir = Path(td) / "lib"
            mod_dir = Path(td) / "mod"
            lib_dir.mkdir(parents=True)
            mod_dir.mkdir(parents=True)
            (lib_dir / "libWlanResource.so").write_bytes(b"NOT_AN_ELF_FILE")
            (lib_dir / "appFw.so").write_bytes(b"BAD")
            (mod_dir / "upm.ko").write_bytes(b"BAD")
            res = inspect_phase302_donors_bounded(
                fx6_lib_dir=lib_dir,
                fx3_modules_dir=mod_dir,
                force_clean_room=False,
            )
        self.assertFalse(res.passed)
        self.assertEqual(res.verification_mode, "LOCAL_DONOR_O_RDONLY")
        self.assertGreaterEqual(len(res.errors), 1)

    def test_08_zero_raw_bytes_leaked_and_zero_usb_packets_contract(self) -> None:
        self.assertEqual(PHASE302_RAW_FIRMWARE_BYTES_LEAKED, 0)
        self.assertEqual(PHASE302_PASSIVE_TX_BYTES_EMITTED, 0)
        self.assertEqual(PHASE302_USB_PACKETS_TRANSMITTED, 0)

    # --- Section 2: Check Group A — Wave 53 Lens Comp, Built-in AF Illuminator LED & Folder/Rating Vault (18 tests) ---

    def test_09_ga_nominal_defaults_pass(self) -> None:
        ga = evaluate_p302_check_group_a_lens_comp_af_illum_folder_rating()
        self.assertTrue(ga.passed, msg=ga.errors)
        self.assertEqual(ga.check_group_id, P302_CHECK_GROUP_A_ID)
        self.assertTrue(ga.dormant_auto_low_rejected)
        self.assertTrue(ga.fx3_builtin_af_illuminator_present)
        self.assertFalse(ga.fx6_builtin_af_illuminator_present)
        self.assertTrue(ga.five_af_params_survive_camera_reset)
        self.assertTrue(ga.slot1_folder_rating_firewall_enforced)
        self.assertEqual(ga.slot1_metadata_sector_writes, 0)
        self.assertFalse(ga.slot1_avf_info_mutated)

    def test_10_ga_model_id_and_firmware_floor_fail_closed(self) -> None:
        ga_model = evaluate_p302_check_group_a_lens_comp_af_illum_folder_rating(body_model_id=0x91030099)
        self.assertFalse(ga_model.passed)
        self.assertTrue(any(P302_GA_ERR_MODEL_OR_FW_FLOOR in e for e in ga_model.errors))

        ga_fw = evaluate_p302_check_group_a_lens_comp_af_illum_folder_rating(body_fw="2.00")
        self.assertFalse(ga_fw.passed)
        self.assertTrue(any(P302_GA_ERR_MODEL_OR_FW_FLOOR in e for e in ga_fw.errors))

        ga_hg = evaluate_p302_check_group_a_lens_comp_af_illum_folder_rating(sony_help_guide_id="ilc/9999")
        self.assertFalse(ga_hg.passed)
        self.assertTrue(any(P302_GA_ERR_MODEL_OR_FW_FLOOR in e for e in ga_hg.errors))

    def test_11_ga_shading_comp_two_modes_only_dormant_auto_low_0x6c9c_eopnotsupp_95(self) -> None:
        ga_ok = evaluate_p302_check_group_a_lens_comp_af_illum_folder_rating(shading_comp="OFF")
        self.assertTrue(ga_ok.passed, msg=ga_ok.errors)

        ga_req = evaluate_p302_check_group_a_lens_comp_af_illum_folder_rating(
            dormant_shading_auto_low_requested=True
        )
        self.assertFalse(ga_req.passed)
        self.assertFalse(ga_req.dormant_auto_low_rejected)
        self.assertTrue(any(P302_GA_ERR_SHADING_AUTO_LOW_EOPNOTSUPP in e and "95" in e for e in ga_req.errors))

        ga_val = evaluate_p302_check_group_a_lens_comp_af_illum_folder_rating(shading_comp="AUTO_LOW")
        self.assertFalse(ga_val.passed)
        self.assertTrue(any(P302_GA_ERR_SHADING_AUTO_LOW_EOPNOTSUPP in e for e in ga_val.errors))

        ga_exp = evaluate_p302_check_group_a_lens_comp_af_illum_folder_rating(
            exposed_shading_modes=("AUTO", "AUTO_LOW", "OFF")
        )
        self.assertFalse(ga_exp.passed)
        self.assertTrue(any(P302_GA_ERR_SHADING_AUTO_LOW_EOPNOTSUPP in e for e in ga_exp.errors))

    def test_12_ga_steadyshot_active_locks_distortion_comp_auto_and_rejects_off(self) -> None:
        ga_ok = evaluate_p302_check_group_a_lens_comp_af_illum_folder_rating(
            steadyshot_mode="ACTIVE",
            distortion_comp="AUTO",
        )
        self.assertTrue(ga_ok.passed, msg=ga_ok.errors)

        ga_bad = evaluate_p302_check_group_a_lens_comp_af_illum_folder_rating(
            steadyshot_mode="ACTIVE",
            distortion_comp="OFF",
        )
        self.assertFalse(ga_bad.passed)
        self.assertTrue(any(P302_GA_ERR_LENS_COMP_LOCK_OR_RESET_BOUNDARY in e for e in ga_bad.errors))

    def test_13_ga_lens_locked_distortion_comp_auto_rejects_off(self) -> None:
        ga_ok = evaluate_p302_check_group_a_lens_comp_af_illum_folder_rating(
            lens_distortion_comp_locked_auto=True,
            distortion_comp="AUTO",
        )
        self.assertTrue(ga_ok.passed, msg=ga_ok.errors)

        ga_bad = evaluate_p302_check_group_a_lens_comp_af_illum_folder_rating(
            lens_distortion_comp_locked_auto=True,
            distortion_comp="OFF",
        )
        self.assertFalse(ga_bad.passed)
        self.assertTrue(any(P302_GA_ERR_LENS_COMP_LOCK_OR_RESET_BOUNDARY in e for e in ga_bad.errors))

    def test_14_ga_unchipped_manual_lens_disables_lens_comp(self) -> None:
        ga_ok = evaluate_p302_check_group_a_lens_comp_af_illum_folder_rating(
            unchipped_manual_lens_attached=True,
            expect_lens_comp_active_on_manual_lens=False,
        )
        self.assertTrue(ga_ok.passed, msg=ga_ok.errors)

        ga_bad = evaluate_p302_check_group_a_lens_comp_af_illum_folder_rating(
            unchipped_manual_lens_attached=True,
            expect_lens_comp_active_on_manual_lens=True,
        )
        self.assertFalse(ga_bad.passed)
        self.assertTrue(any(P302_GA_ERR_LENS_COMP_LOCK_OR_RESET_BOUNDARY in e for e in ga_bad.errors))

    def test_15_ga_breathing_comp_movie_only_and_hdmi_raw_and_compliant_lens_locks(self) -> None:
        ga_ok = evaluate_p302_check_group_a_lens_comp_af_illum_folder_rating(
            shoot_mode="MOVIE",
            breathing_comp="ON",
            breathing_comp_compliant_lens=True,
            hdmi_raw_output=False,
        )
        self.assertTrue(ga_ok.passed, msg=ga_ok.errors)

        for bad_kw in (
            {"shoot_mode": "PHOTO", "breathing_comp": "ON"},
            {"shoot_mode": "MOVIE", "breathing_comp": "ON", "hdmi_raw_output": True},
            {"shoot_mode": "MOVIE", "breathing_comp": "ON", "breathing_comp_compliant_lens": False},
        ):
            ga_bad = evaluate_p302_check_group_a_lens_comp_af_illum_folder_rating(**bad_kw)
            self.assertFalse(ga_bad.passed, msg=f"Expected failure for {bad_kw}")
            self.assertTrue(any(P302_GA_ERR_LENS_COMP_LOCK_OR_RESET_BOUNDARY in e for e in ga_bad.errors))

    def test_16_ga_static_lens_comp_3items_survive_camera_settings_reset(self) -> None:
        ga_ok = evaluate_p302_check_group_a_lens_comp_af_illum_folder_rating(
            reset_action="CAMERA_SETTINGS_RESET",
            claimed_static_lens_comp_wiped_by_camera_reset=False,
        )
        self.assertTrue(ga_ok.passed, msg=ga_ok.errors)

        ga_bad = evaluate_p302_check_group_a_lens_comp_af_illum_folder_rating(
            reset_action="CAMERA_SETTINGS_RESET",
            claimed_static_lens_comp_wiped_by_camera_reset=True,
        )
        self.assertFalse(ga_bad.passed)
        self.assertTrue(any(P302_GA_ERR_LENS_COMP_LOCK_OR_RESET_BOUNDARY in e for e in ga_bad.errors))

    def test_17_ga_fx6_lens_comp_in_scene_file_myth_rejected(self) -> None:
        ga = evaluate_p302_check_group_a_lens_comp_af_illum_folder_rating(
            fx6_lens_comp_in_scene_file_claimed=True
        )
        self.assertFalse(ga.passed)
        self.assertTrue(any(P302_GA_ERR_LENS_COMP_LOCK_OR_RESET_BOUNDARY in e for e in ga.errors))

    def test_18_ga_fx3_builtin_af_illuminator_led8_still_afs_and_range_0_3_to_3_0m(self) -> None:
        ga_ok = evaluate_p302_check_group_a_lens_comp_af_illum_folder_rating(
            shoot_mode="PHOTO",
            focus_mode="AF_S",
            af_illuminator="AUTO",
            af_illuminator_firing_requested=True,
            af_illuminator_distance_m=0.3,
        )
        self.assertTrue(ga_ok.passed, msg=ga_ok.errors)

        ga_max = evaluate_p302_check_group_a_lens_comp_af_illum_folder_rating(
            shoot_mode="PHOTO",
            focus_mode="AF_A",
            af_illuminator="AUTO",
            af_illuminator_firing_requested=True,
            af_illuminator_distance_m=3.0,
        )
        self.assertTrue(ga_max.passed, msg=ga_max.errors)

        for dist in (0.29, 3.01):
            ga_bad = evaluate_p302_check_group_a_lens_comp_af_illum_folder_rating(
                shoot_mode="PHOTO",
                focus_mode="AF_S",
                af_illuminator="AUTO",
                af_illuminator_firing_requested=True,
                af_illuminator_distance_m=dist,
            )
            self.assertFalse(ga_bad.passed, msg=f"Expected out-of-range failure for dist={dist}")
            self.assertTrue(any(P302_GA_ERR_AF_ILLUMINATOR_OR_FX6_ABSENCE in e for e in ga_bad.errors))

    def test_19_ga_af_illuminator_locked_out_in_movie_sq_afc_mf_magnifier_and_mount_adaptor(self) -> None:
        for bad_kw in (
            {"shoot_mode": "MOVIE", "focus_mode": "AF_C", "af_illuminator_firing_requested": True},
            {"shoot_mode": "S_AND_Q", "focus_mode": "AF_C", "af_illuminator_firing_requested": True},
            {"shoot_mode": "PHOTO", "focus_mode": "AF_C", "af_illuminator_firing_requested": True},
            {"shoot_mode": "PHOTO", "focus_mode": "MF", "af_illuminator_firing_requested": True},
            {"shoot_mode": "PHOTO", "focus_mode": "AF_S", "af_illuminator_firing_requested": True, "focus_magnifier_active": True},
            {"shoot_mode": "PHOTO", "focus_mode": "AF_S", "af_illuminator_firing_requested": True, "mount_adaptor_attached": True},
            {"shoot_mode": "PHOTO", "focus_mode": "AF_S", "af_illuminator": "OFF", "af_illuminator_firing_requested": True},
        ):
            ga = evaluate_p302_check_group_a_lens_comp_af_illum_folder_rating(**bad_kw)
            self.assertFalse(ga.passed, msg=f"Expected AF illuminator lockout for {bad_kw}")
            self.assertFalse(ga.af_illuminator_still_afs_gate_verified)

    def test_20_ga_fx6_zero_builtin_af_illuminator_and_fx3_absence_myth_rejected(self) -> None:
        ga_fx6 = evaluate_p302_check_group_a_lens_comp_af_illum_folder_rating(
            fx6_builtin_af_illuminator_present=True
        )
        self.assertFalse(ga_fx6.passed)
        self.assertTrue(any(P302_GA_ERR_AF_ILLUMINATOR_OR_FX6_ABSENCE in e for e in ga_fx6.errors))

        ga_fx3 = evaluate_p302_check_group_a_lens_comp_af_illum_folder_rating(
            fx3_builtin_af_illuminator_present=False
        )
        self.assertFalse(ga_fx3.passed)
        self.assertTrue(any(P302_GA_ERR_AF_ILLUMINATOR_OR_FX6_ABSENCE in e for e in ga_fx3.errors))

    def test_21_ga_af_transition_speed_1_7_af_subj_shift_1_5_and_af_assist_movie_afc(self) -> None:
        ga_ok = evaluate_p302_check_group_a_lens_comp_af_illum_folder_rating(
            shoot_mode="MOVIE",
            focus_mode="AF_C",
            af_transition_speed=7,
            af_subj_shift_sensitivity=1,
            af_assist="ON",
            af_assist_compatible_lens=True,
        )
        self.assertTrue(ga_ok.passed, msg=ga_ok.errors)

        for bad_kw in (
            {"af_transition_speed": 0},
            {"af_transition_speed": 8},
            {"af_subj_shift_sensitivity": 0},
            {"af_subj_shift_sensitivity": 6},
            {"shoot_mode": "PHOTO", "focus_mode": "AF_C", "af_assist": "ON"},
            {"shoot_mode": "MOVIE", "focus_mode": "MF", "af_assist": "ON"},
            {"shoot_mode": "MOVIE", "focus_mode": "AF_C", "af_assist": "ON", "af_assist_compatible_lens": False},
        ):
            ga = evaluate_p302_check_group_a_lens_comp_af_illum_folder_rating(**bad_kw)
            self.assertFalse(ga.passed, msg=f"Expected failure for {bad_kw}")

    def test_22_ga_five_initialize_only_af_params_survive_camera_reset_and_fx6_absence(self) -> None:
        for ap_drv in P302_APERTURE_DRIVE_THREE_MODES:
            ga = evaluate_p302_check_group_a_lens_comp_af_illum_folder_rating(
                reset_action="CAMERA_SETTINGS_RESET",
                aperture_drive_in_af=ap_drv,
                af_with_shutter="OFF",
                circ_of_focus_point="CIRCULATE",
                focus_area_color="RED",
                claimed_af_five_params_wiped_by_camera_reset=False,
            )
            self.assertTrue(ga.passed, msg=ga.errors)

        ga_wipe = evaluate_p302_check_group_a_lens_comp_af_illum_folder_rating(
            reset_action="CAMERA_SETTINGS_RESET",
            claimed_af_five_params_wiped_by_camera_reset=True,
        )
        self.assertFalse(ga_wipe.passed)
        self.assertFalse(ga_wipe.five_af_params_survive_camera_reset)
        self.assertTrue(any(P302_GA_ERR_AF_FIVE_PARAMS_PERSISTENCE_OR_CIRC in e for e in ga_wipe.errors))

        ga_fx6 = evaluate_p302_check_group_a_lens_comp_af_illum_folder_rating(
            fx6_aperture_drive_in_af_claimed=True
        )
        self.assertFalse(ga_fx6.passed)

    def test_23_ga_circ_of_focus_point_orthogonal_only_rejects_diagonal_and_pre_af_lens_gate(self) -> None:
        ga_diag = evaluate_p302_check_group_a_lens_comp_af_illum_folder_rating(
            circ_of_focus_point="CIRCULATE",
            expect_diagonal_focus_wrap=True,
        )
        self.assertFalse(ga_diag.passed)
        self.assertTrue(any(P302_GA_ERR_AF_FIVE_PARAMS_PERSISTENCE_OR_CIRC in e for e in ga_diag.errors))

        ga_pre_ok = evaluate_p302_check_group_a_lens_comp_af_illum_folder_rating(
            shoot_mode="PHOTO",
            pre_af="ON",
            lens_pre_af_supported=True,
        )
        self.assertTrue(ga_pre_ok.passed, msg=ga_pre_ok.errors)

        for bad_pre in (
            {"shoot_mode": "MOVIE", "pre_af": "ON", "lens_pre_af_supported": True},
            {"shoot_mode": "PHOTO", "pre_af": "ON", "lens_pre_af_supported": False},
        ):
            ga_pre_bad = evaluate_p302_check_group_a_lens_comp_af_illum_folder_rating(**bad_pre)
            self.assertFalse(ga_pre_bad.passed)

    def test_24_ga_still_folder_name_date_form_disables_select_rec_folder_and_4000_limit(self) -> None:
        ga_ok = evaluate_p302_check_group_a_lens_comp_af_illum_folder_rating(
            still_folder_name_mode="DATE_FORM",
            still_folder_image_count=P302_FOLDER_NAME_MAX_IMAGES,
        )
        self.assertTrue(ga_ok.passed, msg=ga_ok.errors)

        ga_sel = evaluate_p302_check_group_a_lens_comp_af_illum_folder_rating(
            still_folder_name_mode="DATE_FORM",
            select_rec_folder_enabled_claimed=True,
        )
        self.assertFalse(ga_sel.passed)
        self.assertTrue(any(P302_GA_ERR_FOLDER_OR_RATING_SLOT1_VAULT_EROFS in e for e in ga_sel.errors))

        ga_4001 = evaluate_p302_check_group_a_lens_comp_af_illum_folder_rating(
            still_folder_image_count=4001
        )
        self.assertFalse(ga_4001.passed)

    def test_25_ga_still_file_prefix_no_leading_underscore_and_slot1_create_folder_reset_erofs(self) -> None:
        ga_prefix = evaluate_p302_check_group_a_lens_comp_af_illum_folder_rating(
            still_file_prefix="_FX"
        )
        self.assertFalse(ga_prefix.passed)
        self.assertTrue(any(P302_GA_ERR_FOLDER_OR_RATING_SLOT1_VAULT_EROFS in e for e in ga_prefix.errors))

        ga_cf1 = evaluate_p302_check_group_a_lens_comp_af_illum_folder_rating(
            slot1_contains_tier0_dump=True,
            create_new_folder_requested=True,
            create_new_folder_slot=1,
        )
        self.assertFalse(ga_cf1.passed)
        self.assertFalse(ga_cf1.slot1_folder_rating_firewall_enforced)
        self.assertTrue(any("EROFS=30" in e for e in ga_cf1.errors))

        ga_rst1 = evaluate_p302_check_group_a_lens_comp_af_illum_folder_rating(
            slot1_contains_tier0_dump=True,
            forced_file_number_reset_requested=True,
            forced_file_number_reset_slot=1,
        )
        self.assertFalse(ga_rst1.passed)
        self.assertTrue(any("EROFS=30" in e for e in ga_rst1.errors))

        ga_slot2 = evaluate_p302_check_group_a_lens_comp_af_illum_folder_rating(
            create_new_folder_requested=True,
            create_new_folder_slot=2,
            forced_file_number_reset_requested=True,
            forced_file_number_reset_slot=2,
        )
        self.assertTrue(ga_slot2.passed, msg=ga_slot2.errors)

    def test_26_ga_playback_rating_1_to_5_and_slot1_vault_erofs_and_add_rating_unrated(self) -> None:
        ga_s2 = evaluate_p302_check_group_a_lens_comp_af_illum_folder_rating(
            shoot_mode="PHOTO",
            playback_media_slot=2,
            playback_rating_requested=True,
            rating_stars=P302_STILL_RATING_MAX_STARS,
            add_rating_requested=True,
            target_image_already_rated=False,
        )
        self.assertTrue(ga_s2.passed, msg=ga_s2.errors)

        ga_s1 = evaluate_p302_check_group_a_lens_comp_af_illum_folder_rating(
            playback_media_slot=1,
            slot1_contains_tier0_dump=True,
            playback_rating_requested=True,
            rating_stars=P302_STILL_RATING_MIN_STARS,
        )
        self.assertFalse(ga_s1.passed)
        self.assertFalse(ga_s1.slot1_folder_rating_firewall_enforced)
        self.assertTrue(any("EROFS=30" in e for e in ga_s1.errors))

        ga_stars = evaluate_p302_check_group_a_lens_comp_af_illum_folder_rating(
            playback_media_slot=2,
            playback_rating_requested=True,
            rating_stars=6,
        )
        self.assertFalse(ga_stars.passed)

        ga_rated = evaluate_p302_check_group_a_lens_comp_af_illum_folder_rating(
            shoot_mode="PHOTO",
            playback_media_slot=2,
            add_rating_requested=True,
            target_image_already_rated=True,
        )
        self.assertFalse(ga_rated.passed)

    # --- Section 3: Check Group B — Wave 54 Switch V/H AF, 14-Limit, 5-Mode Std. Adj, TC & Copy Slot-1 Trap (20 tests) ---

    def test_27_gb_nominal_defaults_pass(self) -> None:
        gb = evaluate_p302_check_group_b_switch_vh_limit14_stdadj_tc_and_copy_slot1()
        self.assertTrue(gb.passed, msg=gb.errors)
        self.assertEqual(gb.check_group_id, P302_CHECK_GROUP_B_ID)
        self.assertEqual(gb.focus_area_limit_item_count, 14)
        self.assertEqual(gb.exposure_std_metering_mode_count, 5)
        self.assertTrue(gb.dormant_focus_areas_rejected)
        self.assertTrue(gb.copy_reverse_slot1_firewall_enforced)
        self.assertEqual(gb.slot1_data_sector_writes, 0)

    def test_28_gb_switch_vh_af_area_still_afc_0_90_270_degrees_passes(self) -> None:
        for vh in ("AF_POINT_ONLY", "AF_POINT_AND_AF_AREA"):
            for roll in ("0_DEGREES", "90_DEGREES", "270_DEGREES"):
                gb = evaluate_p302_check_group_b_switch_vh_limit14_stdadj_tc_and_copy_slot1(
                    shoot_mode="PHOTO",
                    focus_mode="AF_C",
                    exposure_mode="MANUAL_EXPOSURE",
                    switch_vh_af_area=vh,
                    body_roll_orientation=roll,
                )
                self.assertTrue(gb.passed, msg=f"Failed for {vh} @ {roll}: {gb.errors}")

    def test_29_gb_switch_vh_af_area_rejects_vertical_pitch_and_movie_sq_digital_zoom_magnifier(self) -> None:
        for bad_kw in (
            {"shoot_mode": "MOVIE", "focus_mode": "AF_C", "switch_vh_af_area": "AF_POINT_ONLY"},
            {"shoot_mode": "S_AND_Q", "focus_mode": "AF_C", "switch_vh_af_area": "AF_POINT_ONLY"},
            {"shoot_mode": "PHOTO", "focus_mode": "AF_S", "switch_vh_af_area": "AF_POINT_ONLY"},
            {"shoot_mode": "PHOTO", "focus_mode": "AF_C", "exposure_mode": "INTELLIGENT_AUTO", "switch_vh_af_area": "AF_POINT_ONLY"},
            {"shoot_mode": "PHOTO", "focus_mode": "AF_C", "digital_zoom_active": True, "switch_vh_af_area": "AF_POINT_ONLY"},
            {"shoot_mode": "PHOTO", "focus_mode": "AF_C", "focus_magnifier_active": True, "switch_vh_af_area": "AF_POINT_ONLY"},
            {"shoot_mode": "PHOTO", "focus_mode": "AF_C", "switch_vh_af_area": "AF_POINT_AND_AF_AREA", "body_roll_orientation": "INVALID_VERTICAL_PITCH"},
        ):
            gb = evaluate_p302_check_group_b_switch_vh_limit14_stdadj_tc_and_copy_slot1(**bad_kw)
            self.assertFalse(gb.passed, msg=f"Expected failure for {bad_kw}")
            self.assertTrue(any(P302_GB_ERR_SWITCH_VH_AF_AREA_GATE in e for e in gb.errors))

    def test_30_gb_switch_vh_af_area_rejects_invalid_mode_and_fx6_claim(self) -> None:
        gb_inv = evaluate_p302_check_group_b_switch_vh_limit14_stdadj_tc_and_copy_slot1(
            switch_vh_af_area="BAD_MODE"
        )
        self.assertFalse(gb_inv.passed)

        gb_fx6 = evaluate_p302_check_group_b_switch_vh_limit14_stdadj_tc_and_copy_slot1(
            fx6_switch_vh_af_area_claimed=True
        )
        self.assertFalse(gb_fx6.passed)
        self.assertTrue(any(P302_GB_ERR_SWITCH_VH_AF_AREA_GATE in e for e in gb_fx6.errors))

    def test_31_gb_focus_area_limit_exact_14_items_and_min_2_selected_enforced(self) -> None:
        gb_min2 = evaluate_p302_check_group_b_switch_vh_limit14_stdadj_tc_and_copy_slot1(
            focus_area_limit_selected_count=2
        )
        self.assertTrue(gb_min2.passed, msg=gb_min2.errors)

        for bad_cnt in (0, 1, 15):
            gb_bad = evaluate_p302_check_group_b_switch_vh_limit14_stdadj_tc_and_copy_slot1(
                focus_area_limit_selected_count=bad_cnt
            )
            self.assertFalse(gb_bad.passed)
            self.assertTrue(any(P302_GB_ERR_FOCUS_AREA_LIMIT_14_OR_MIN2 in e for e in gb_bad.errors))

        gb_subset = evaluate_p302_check_group_b_switch_vh_limit14_stdadj_tc_and_copy_slot1(
            exposed_focus_area_limit_items=P302_FOCUS_AREA_LIMIT_14_ITEMS[:13]
        )
        self.assertFalse(gb_subset.passed)

    def test_32_gb_focus_area_limit_rejects_dormant_spot_xl_xs_custom123_and_fx6_claim(self) -> None:
        for dormant in P302_DORMANT_FOCUS_AREAS:
            gb = evaluate_p302_check_group_b_switch_vh_limit14_stdadj_tc_and_copy_slot1(
                dormant_focus_area_requested=dormant
            )
            self.assertFalse(gb.passed, msg=f"Expected rejection for {dormant}")
            self.assertFalse(gb.dormant_focus_areas_rejected)
            self.assertTrue(any("95" in e and P302_GB_ERR_FOCUS_AREA_LIMIT_14_OR_MIN2 in e for e in gb.errors))

        gb_fx6 = evaluate_p302_check_group_b_switch_vh_limit14_stdadj_tc_and_copy_slot1(
            fx6_focus_area_limit_claimed=True
        )
        self.assertFalse(gb_fx6.passed)

    def test_33_gb_exposure_std_adjust_exact_5_metering_modes_passes_rejects_4_mode(self) -> None:
        for mode in P302_EXPOSURE_STD_ADJUST_5_METERING_MODES:
            gb = evaluate_p302_check_group_b_switch_vh_limit14_stdadj_tc_and_copy_slot1(
                exposure_std_adjust_metering_mode=mode
            )
            self.assertTrue(gb.passed, msg=gb.errors)

        gb_4 = evaluate_p302_check_group_b_switch_vh_limit14_stdadj_tc_and_copy_slot1(
            exposed_exposure_std_metering_modes=P302_EXPOSURE_STD_ADJUST_5_METERING_MODES[:4]
        )
        self.assertFalse(gb_4.passed)
        self.assertTrue(any(P302_GB_ERR_EXPOSURE_STD_ADJUST_5MODE_OR_BRACKET in e for e in gb_4.errors))

    def test_34_gb_exposure_std_adjust_ev_range_minus1_to_plus1_in_sixth_ev_steps(self) -> None:
        for step_idx in range(-6, 7):
            ev = round(step_idx / 6.0, 6)
            gb = evaluate_p302_check_group_b_switch_vh_limit14_stdadj_tc_and_copy_slot1(
                exposure_std_adjust_ev=ev
            )
            self.assertTrue(gb.passed, msg=f"Failed for 1/6 EV step {ev}: {gb.errors}")

        for bad_ev in (P302_EXPOSURE_STD_ADJUST_EV_MIN - 1.0 / 6.0, P302_EXPOSURE_STD_ADJUST_EV_MAX + 1.0 / 6.0, 0.25):
            gb_bad = evaluate_p302_check_group_b_switch_vh_limit14_stdadj_tc_and_copy_slot1(
                exposure_std_adjust_ev=bad_ev
            )
            self.assertFalse(gb_bad.passed, msg=f"Expected EV failure for {bad_ev}")
            self.assertTrue(any(P302_GB_ERR_EXPOSURE_STD_ADJUST_5MODE_OR_BRACKET in e for e in gb_bad.errors))

    def test_35_gb_exposure_std_adjust_exif_independence_initialize_only_and_fx6_absence(self) -> None:
        gb_ok = evaluate_p302_check_group_b_switch_vh_limit14_stdadj_tc_and_copy_slot1(
            reset_action="CAMERA_SETTINGS_RESET",
            claimed_exposure_std_adjust_wiped_by_camera_reset=False,
        )
        self.assertTrue(gb_ok.passed, msg=gb_ok.errors)

        for bad_kw in (
            {"expect_std_adjust_changes_exif_exposure_comp": True},
            {"reset_action": "CAMERA_SETTINGS_RESET", "claimed_exposure_std_adjust_wiped_by_camera_reset": True},
            {"fx6_exposure_std_adjust_claimed": True},
        ):
            gb = evaluate_p302_check_group_b_switch_vh_limit14_stdadj_tc_and_copy_slot1(**bad_kw)
            self.assertFalse(gb.passed)
            self.assertTrue(any(P302_GB_ERR_EXPOSURE_STD_ADJUST_5MODE_OR_BRACKET in e for e in gb.errors))

    def test_36_gb_bracket_settings_still_only_valid_selftimer_order_rejects_movie(self) -> None:
        for t in P302_BRACKET_SELFTIMER_MODES:
            for o in P302_BRACKET_ORDER_MODES:
                gb = evaluate_p302_check_group_b_switch_vh_limit14_stdadj_tc_and_copy_slot1(
                    shoot_mode="PHOTO",
                    bracket_selftimer=t,
                    bracket_order=o,
                )
                self.assertTrue(gb.passed, msg=gb.errors)

        gb_bad = evaluate_p302_check_group_b_switch_vh_limit14_stdadj_tc_and_copy_slot1(
            bracket_settings_active_in_movie_claimed=True
        )
        self.assertFalse(gb_bad.passed)

    def test_37_gb_tc_format_ndf_lock_in_23_98p_and_24_00p_allows_df_in_29_97p_59_94p(self) -> None:
        for fps in P302_TC_NDF_LOCKED_FRAME_RATES:
            gb_ok = evaluate_p302_check_group_b_switch_vh_limit14_stdadj_tc_and_copy_slot1(
                video_system="NTSC", rec_frame_rate=fps, tc_format="NDF"
            )
            self.assertTrue(gb_ok.passed, msg=gb_ok.errors)

            gb_df = evaluate_p302_check_group_b_switch_vh_limit14_stdadj_tc_and_copy_slot1(
                video_system="NTSC", rec_frame_rate=fps, tc_format="DF"
            )
            self.assertFalse(gb_df.passed)
            self.assertTrue(any(P302_GB_ERR_TC_FORMAT_NDF_PAL_OR_BNC_ABSENCE in e for e in gb_df.errors))

        gb_29 = evaluate_p302_check_group_b_switch_vh_limit14_stdadj_tc_and_copy_slot1(
            video_system="NTSC", rec_frame_rate="29.97P", tc_format="DF"
        )
        self.assertTrue(gb_29.passed, msg=gb_29.errors)

    def test_38_gb_tc_format_hidden_in_pal_25p_50p(self) -> None:
        gb_pal_ndf = evaluate_p302_check_group_b_switch_vh_limit14_stdadj_tc_and_copy_slot1(
            video_system="PAL", rec_frame_rate="25P", tc_format="NDF"
        )
        self.assertTrue(gb_pal_ndf.passed, msg=gb_pal_ndf.errors)

        gb_pal_df = evaluate_p302_check_group_b_switch_vh_limit14_stdadj_tc_and_copy_slot1(
            video_system="PAL", rec_frame_rate="25P", tc_format="DF"
        )
        self.assertFalse(gb_pal_df.passed)
        self.assertTrue(any(P302_GB_ERR_TC_FORMAT_NDF_PAL_OR_BNC_ABSENCE in e for e in gb_pal_df.errors))

    def test_39_gb_tcub_6items_initialize_only_and_fx3_zero_physical_bnc_switch(self) -> None:
        gb_bnc = evaluate_p302_check_group_b_switch_vh_limit14_stdadj_tc_and_copy_slot1(
            fx3_builtin_bnc_tc_in_out_switch_claimed=True
        )
        self.assertFalse(gb_bnc.passed)

        gb_wipe = evaluate_p302_check_group_b_switch_vh_limit14_stdadj_tc_and_copy_slot1(
            reset_action="CAMERA_SETTINGS_RESET",
            claimed_tcub_6items_wiped_by_camera_reset=True,
        )
        self.assertFalse(gb_wipe.passed)

    def test_40_gb_critical_playback_copy_reverse_direction_slot2_to_slot1_tier0_vault_erofs(self) -> None:
        gb = evaluate_p302_check_group_b_switch_vh_limit14_stdadj_tc_and_copy_slot1(
            playback_media_slot=2,
            slot1_contains_tier0_dump=True,
            slot1_wp_locked=True,
            playback_copy_requested=True,
        )
        self.assertFalse(gb.passed)
        self.assertEqual(gb.copy_destination_slot, 1)
        self.assertFalse(gb.copy_reverse_slot1_firewall_enforced)
        self.assertEqual(gb.slot1_data_sector_writes, 0)
        self.assertFalse(gb.slot1_avf_info_mutated)
        self.assertTrue(
            any(
                P302_GB_ERR_PLAYBACK_COPY_REVERSE_SLOT1_VAULT_TRAP in e and "EROFS=30" in e
                for e in gb.errors
            )
        )

    def test_41_gb_playback_copy_from_slot1_to_slot2_passes_with_slot1_tier0_unmutated(self) -> None:
        gb = evaluate_p302_check_group_b_switch_vh_limit14_stdadj_tc_and_copy_slot1(
            playback_media_slot=1,
            slot1_contains_tier0_dump=True,
            slot1_wp_locked=True,
            playback_copy_requested=True,
        )
        self.assertTrue(gb.passed, msg=gb.errors)
        self.assertEqual(gb.copy_destination_slot, 2)
        self.assertTrue(gb.copy_reverse_slot1_firewall_enforced)

    def test_42_gb_playback_copy_slot2_to_slot1_allowed_only_when_slot1_no_tier0_and_unlocked(self) -> None:
        gb = evaluate_p302_check_group_b_switch_vh_limit14_stdadj_tc_and_copy_slot1(
            playback_media_slot=2,
            slot1_contains_tier0_dump=False,
            slot1_wp_locked=False,
            playback_copy_requested=True,
        )
        self.assertTrue(gb.passed, msg=gb.errors)
        self.assertEqual(gb.copy_destination_slot, 1)

    def test_43_gb_playback_copy_preconditions_battery_speed_dest_and_group_protect_reset(self) -> None:
        for bad_kw in (
            {"playback_media_slot": 1, "playback_copy_requested": True, "copy_battery_ok": False},
            {"playback_media_slot": 1, "playback_copy_requested": True, "copy_target_media_speed_ok": False},
            {"playback_media_slot": 1, "playback_copy_requested": True, "copy_dest_slot_present": False},
            {"expect_copy_preserves_group_or_protect": True},
        ):
            gb = evaluate_p302_check_group_b_switch_vh_limit14_stdadj_tc_and_copy_slot1(**bad_kw)
            self.assertFalse(gb.passed, msg=f"Expected failure for {bad_kw}")
            self.assertTrue(any(P302_GB_ERR_PLAYBACK_COPY_REVERSE_SLOT1_VAULT_TRAP in e for e in gb.errors))

    def test_44_gb_playback_copy_rejects_fx6_copy_clip_myth(self) -> None:
        gb = evaluate_p302_check_group_b_switch_vh_limit14_stdadj_tc_and_copy_slot1(
            fx6_in_camera_copy_clip_claimed=True
        )
        self.assertFalse(gb.passed)
        self.assertTrue(any(P302_GB_ERR_PLAYBACK_COPY_REVERSE_SLOT1_VAULT_TRAP in e for e in gb.errors))

    def test_45_gb_slide_show_1_3_5_10_30s_date_or_folder_still_only_passes(self) -> None:
        for sec in P302_SLIDE_SHOW_INTERVALS_SEC:
            for vm in P302_SLIDE_SHOW_VIEW_MODES:
                gb = evaluate_p302_check_group_b_switch_vh_limit14_stdadj_tc_and_copy_slot1(
                    slide_show_requested=True,
                    slide_show_repeat="ON",
                    slide_show_interval_sec=sec,
                    slide_show_view_mode=vm,
                )
                self.assertTrue(gb.passed, msg=gb.errors)

    def test_46_gb_slide_show_rejects_invalid_interval_and_movie_view(self) -> None:
        gb_sec = evaluate_p302_check_group_b_switch_vh_limit14_stdadj_tc_and_copy_slot1(
            slide_show_requested=True, slide_show_interval_sec=15
        )
        self.assertFalse(gb_sec.passed)
        self.assertTrue(any(P302_GB_ERR_SLIDESHOW_BOUNDARY in e for e in gb_sec.errors))

        gb_mv = evaluate_p302_check_group_b_switch_vh_limit14_stdadj_tc_and_copy_slot1(
            slide_show_requested=True, slide_show_view_mode="MOVIE_VIEW"
        )
        self.assertFalse(gb_mv.passed)
        self.assertTrue(any(P302_GB_ERR_SLIDESHOW_BOUNDARY in e for e in gb_mv.errors))

    # --- Section 4: Check Group C — Wave 55 Touch, 4-Mode DISP / Zero-EVF Blackout, AEL/Flash & Interval Play (20 tests) ---

    def test_47_gc_nominal_defaults_pass(self) -> None:
        gc = evaluate_p302_check_group_c_touch_disp_evf_absence_ael_flash_and_interval()
        self.assertTrue(gc.passed, msg=gc.errors)
        self.assertEqual(gc.check_group_id, P302_CHECK_GROUP_C_ID)
        self.assertTrue(gc.dormant_touch_traps_rejected)
        self.assertFalse(gc.fx3_builtin_evf_present)
        self.assertFalse(gc.fx3_eye_sensor_present)
        self.assertFalse(gc.fx3_select_finder_monitor_present)
        self.assertFalse(gc.fx3_graphic_display_present)
        self.assertTrue(gc.zero_evf_blackout_firewall_enforced)
        self.assertTrue(gc.dormant_edit_traps_rejected)
        self.assertEqual(gc.interval_play_speed, 5)

    def test_48_gc_touch_func_in_shooting_3_modes_across_still_movie_sq(self) -> None:
        for sm in ("PHOTO", "MOVIE", "S_AND_Q"):
            for tf in P302_TOUCH_FUNC_SHOOTING_THREE_MODES:
                gc = evaluate_p302_check_group_c_touch_disp_evf_absence_ael_flash_and_interval(
                    shoot_mode=sm,
                    touch_operation="ON",
                    touch_func_in_shooting=tf,
                )
                self.assertTrue(gc.passed, msg=f"Failed {sm}/{tf}: {gc.errors}")

    def test_49_gc_touch_sensitivity_2_modes_standard_sensitive_rejects_responsive(self) -> None:
        for ts in P302_TOUCH_SENSITIVITY_TWO_MODES:
            gc = evaluate_p302_check_group_c_touch_disp_evf_absence_ael_flash_and_interval(
                touch_sensitivity=ts
            )
            self.assertTrue(gc.passed, msg=gc.errors)

        gc_bad = evaluate_p302_check_group_c_touch_disp_evf_absence_ael_flash_and_interval(
            touch_sensitivity="RESPONSIVE"
        )
        self.assertFalse(gc_bad.passed)
        self.assertTrue(any(P302_GC_ERR_TOUCH_SHOOTING_3MODE_OR_DORMANT_TRAP in e for e in gc_bad.errors))

    def test_50_gc_dormant_touch_traps_touch_shutter_ae_panel_pad_footer_swipe_lr_eopnotsupp(self) -> None:
        for trap in (t for t in P302_DORMANT_TOUCH_TRAPS if t != "NONE"):
            gc = evaluate_p302_check_group_c_touch_disp_evf_absence_ael_flash_and_interval(
                dormant_touch_trap_requested=trap
            )
            self.assertFalse(gc.passed, msg=f"Expected rejection for {trap}")
            self.assertFalse(gc.dormant_touch_traps_rejected)
            self.assertTrue(any("95" in e and P302_GC_ERR_TOUCH_SHOOTING_3MODE_OR_DORMANT_TRAP in e for e in gc.errors))

        for bad_kw in (
            {"touch_panel_pad_present_claimed": True},
            {"footer_icon_touch_enabled_claimed": True},
            {"exposed_touch_func_modes": ("TOUCH_SHUTTER", "TOUCH_FOCUS", "TOUCH_TRACKING", "OFF")},
        ):
            gc = evaluate_p302_check_group_c_touch_disp_evf_absence_ael_flash_and_interval(**bad_kw)
            self.assertFalse(gc.passed)

    def test_51_gc_touch_4items_initialize_only_persistence_survives_camera_reset(self) -> None:
        gc_ok = evaluate_p302_check_group_c_touch_disp_evf_absence_ael_flash_and_interval(
            reset_action="CAMERA_SETTINGS_RESET",
            claimed_touch_4items_wiped_by_camera_reset=False,
        )
        self.assertTrue(gc_ok.passed, msg=gc_ok.errors)

        gc_bad = evaluate_p302_check_group_c_touch_disp_evf_absence_ael_flash_and_interval(
            reset_action="CAMERA_SETTINGS_RESET",
            claimed_touch_4items_wiped_by_camera_reset=True,
        )
        self.assertFalse(gc_bad.passed)

    def test_52_gc_disp_set_exact_4_shoot_and_3_playback_monitor_modes_and_reset_survival(self) -> None:
        gc_ok = evaluate_p302_check_group_c_touch_disp_evf_absence_ael_flash_and_interval(
            reset_action="CAMERA_SETTINGS_RESET",
            claimed_disp_modes_wiped_by_camera_reset=False,
        )
        self.assertTrue(gc_ok.passed, msg=gc_ok.errors)
        self.assertEqual(gc_ok.exposed_disp_shoot_mode_count, 4)
        self.assertEqual(gc_ok.exposed_disp_playback_mode_count, 3)

        for bad_kw in (
            {"exposed_disp_shoot_modes": P302_DISP_MONITOR_SHOOT_FOUR_MODES[:3]},
            {"exposed_disp_playback_modes": P302_DISP_MONITOR_PLAYBACK_THREE_MODES[:2]},
            {"reset_action": "CAMERA_SETTINGS_RESET", "claimed_disp_modes_wiped_by_camera_reset": True},
        ):
            gc = evaluate_p302_check_group_c_touch_disp_evf_absence_ael_flash_and_interval(**bad_kw)
            self.assertFalse(gc.passed)
            self.assertTrue(any(P302_GC_ERR_DISP_4MODE_SHOOT_3MODE_PLAYBACK in e for e in gc.errors))

    def test_53_gc_critical_zero_evf_eye_sensor_select_finder_monitor_graphic_display_absent(self) -> None:
        for flag in (
            "fx3_builtin_evf_present",
            "fx3_eye_sensor_present",
            "fx3_select_finder_monitor_present",
            "fx3_graphic_display_present",
        ):
            gc = evaluate_p302_check_group_c_touch_disp_evf_absence_ael_flash_and_interval(**{flag: True})
            self.assertFalse(gc.passed, msg=f"Expected Zero-EVF failure for {flag}")
            self.assertFalse(gc.zero_evf_blackout_firewall_enforced)
            self.assertTrue(any(P302_GC_ERR_ZERO_EVF_BLACK_SCREEN_LOCKOUT_TRAP in e for e in gc.errors))

    def test_54_gc_critical_activate_dormant_evf_finder_mode_triggers_blackout_firewall(self) -> None:
        gc = evaluate_p302_check_group_c_touch_disp_evf_absence_ael_flash_and_interval(
            activate_dormant_evf_finder_mode=True
        )
        self.assertFalse(gc.passed)
        self.assertFalse(gc.zero_evf_blackout_firewall_enforced)
        self.assertTrue(
            any(
                P302_GC_ERR_ZERO_EVF_BLACK_SCREEN_LOCKOUT_TRAP in e and "95" in e
                for e in gc.errors
            )
        )

    def test_55_gc_dormant_finder_monitor_key_monitor_off_for_viewfinder_and_fx6_loupe_blocked(self) -> None:
        for flag in (
            "finder_monitor_key_claimed",
            "graphic_display_claimed",
            "monitor_off_evf_trap_claimed",
            "for_viewfinder_disp_claimed",
            "fx6_detachable_evf_loupe_claimed",
        ):
            gc = evaluate_p302_check_group_c_touch_disp_evf_absence_ael_flash_and_interval(**{flag: True})
            self.assertFalse(gc.passed, msg=f"Expected failure for {flag}")
            self.assertTrue(any(P302_GC_ERR_ZERO_EVF_BLACK_SCREEN_LOCKOUT_TRAP in e for e in gc.errors))
        self.assertGreaterEqual(len(P302_DORMANT_EVF_FINDER_TRAPS), 4)

    def test_56_gc_ael_with_shutter_still_only_and_initialize_only_survives_camera_reset(self) -> None:
        for mode in P302_AEL_WITH_SHUTTER_THREE_MODES:
            gc = evaluate_p302_check_group_c_touch_disp_evf_absence_ael_flash_and_interval(
                shoot_mode="PHOTO",
                reset_action="CAMERA_SETTINGS_RESET",
                ael_with_shutter=mode,
                claimed_ael_with_shutter_wiped_by_camera_reset=False,
            )
            self.assertTrue(gc.passed, msg=gc.errors)

        gc_wipe = evaluate_p302_check_group_c_touch_disp_evf_absence_ael_flash_and_interval(
            reset_action="CAMERA_SETTINGS_RESET",
            claimed_ael_with_shutter_wiped_by_camera_reset=True,
        )
        self.assertFalse(gc_wipe.passed)
        self.assertTrue(any(P302_GC_ERR_AEL_SHUTTER_OR_FLASH_STILL_GATE in e for e in gc_wipe.errors))

    def test_57_gc_ael_with_shutter_and_external_flash_rejected_in_movie_sq_and_on_fx6(self) -> None:
        for bad_kw in (
            {"ael_with_shutter_in_movie_claimed": True},
            {"fx6_still_ael_or_wireless_flash_claimed": True},
            {"ael_with_shutter": "INVALID"},
        ):
            gc = evaluate_p302_check_group_c_touch_disp_evf_absence_ael_flash_and_interval(**bad_kw)
            self.assertFalse(gc.passed)
            self.assertTrue(any(P302_GC_ERR_AEL_SHUTTER_OR_FLASH_STILL_GATE in e for e in gc.errors))

    def test_58_gc_wireless_flash_resettable_and_external_flash_set_requires_mi_shoe_flash(self) -> None:
        gc_ok = evaluate_p302_check_group_c_touch_disp_evf_absence_ael_flash_and_interval(
            shoot_mode="PHOTO",
            wireless_flash="ON",
            external_flash_set_requested=True,
            mi_shoe_external_flash_attached=True,
        )
        self.assertTrue(gc_ok.passed, msg=gc_ok.errors)

        for bad_kw in (
            {"shoot_mode": "MOVIE", "external_flash_set_requested": True, "mi_shoe_external_flash_attached": True},
            {"shoot_mode": "PHOTO", "external_flash_set_requested": True, "mi_shoe_external_flash_attached": False},
            {"wireless_flash": "BAD"},
        ):
            gc = evaluate_p302_check_group_c_touch_disp_evf_absence_ael_flash_and_interval(**bad_kw)
            self.assertFalse(gc.passed)

    def test_59_gc_exp_comp_set_valid_modes_and_invalid_rejected(self) -> None:
        for m in ("AMBIENT_AND_FLASH", "AMBIENT_ONLY"):
            gc = evaluate_p302_check_group_c_touch_disp_evf_absence_ael_flash_and_interval(exp_comp_set=m)
            self.assertTrue(gc.passed, msg=gc.errors)

        gc_bad = evaluate_p302_check_group_c_touch_disp_evf_absence_ael_flash_and_interval(exp_comp_set="INVALID")
        self.assertFalse(gc_bad.passed)

    def test_60_gc_interval_play_speed_1_to_9_default_5_passes_rejects_cap_at_5_myth(self) -> None:
        for spd in range(1, 10):
            gc = evaluate_p302_check_group_c_touch_disp_evf_absence_ael_flash_and_interval(
                interval_play_speed=spd
            )
            self.assertTrue(gc.passed, msg=gc.errors)

        gc_cap = evaluate_p302_check_group_c_touch_disp_evf_absence_ael_flash_and_interval(
            interval_play_speed_capped_at_5_claimed=True
        )
        self.assertFalse(gc_cap.passed)
        self.assertTrue(any(P302_GC_ERR_INTERVAL_SPEED_1TO9_OR_EDIT_VAULT_GUARD in e for e in gc_cap.errors))

    def test_61_gc_interval_play_speed_rejects_out_of_range_and_in_camera_video_render_myth(self) -> None:
        for bad_spd in (0, 10):
            gc = evaluate_p302_check_group_c_touch_disp_evf_absence_ael_flash_and_interval(
                interval_play_speed=bad_spd
            )
            self.assertFalse(gc.passed)

        gc_rnd = evaluate_p302_check_group_c_touch_disp_evf_absence_ael_flash_and_interval(
            in_camera_interval_to_video_render_claimed=True
        )
        self.assertFalse(gc_rnd.passed)

    def test_62_gc_dormant_beauty_effect_and_trimming_edit_traps_rejected_eopnotsupp_95(self) -> None:
        for bad_kw in (
            {"dormant_beauty_effect_requested": True},
            {"dormant_trimming_requested": True},
            {"exposed_playback_edit_items": (*P302_PLAYBACK_EDIT_ACTIVE_ITEMS, "BEAUTY_EFFECT")},
            {"exposed_playback_edit_items": (*P302_PLAYBACK_EDIT_ACTIVE_ITEMS, "TRIMMING")},
        ):
            gc = evaluate_p302_check_group_c_touch_disp_evf_absence_ael_flash_and_interval(**bad_kw)
            self.assertFalse(gc.passed)
            self.assertFalse(gc.dormant_edit_traps_rejected)
            self.assertTrue(any("95" in e and P302_GC_ERR_INTERVAL_SPEED_1TO9_OR_EDIT_VAULT_GUARD in e for e in gc.errors))
        self.assertEqual(P302_DORMANT_PLAYBACK_EDIT_TRAPS, ("BEAUTY_EFFECT", "TRIMMING"))

    def test_63_gc_playback_photo_capture_and_rotate_blocked_on_slot1_tier0_vault_erofs_30(self) -> None:
        for flag in ("playback_photo_capture_requested", "playback_rotate_requested"):
            gc = evaluate_p302_check_group_c_touch_disp_evf_absence_ael_flash_and_interval(
                playback_media_slot=1,
                slot1_contains_tier0_dump=True,
                **{flag: True},
            )
            self.assertFalse(gc.passed)
            self.assertTrue(any("EROFS=30" in e for e in gc.errors))

    def test_64_gc_playback_photo_capture_and_rotate_allowed_on_slot2_only(self) -> None:
        gc = evaluate_p302_check_group_c_touch_disp_evf_absence_ael_flash_and_interval(
            playback_media_slot=2,
            slot1_contains_tier0_dump=True,
            playback_photo_capture_requested=True,
            playback_rotate_requested=True,
        )
        self.assertTrue(gc.passed, msg=gc.errors)

    def test_65_gc_disp_blackout_trap_mode_in_exposed_disp_list_rejected(self) -> None:
        gc = evaluate_p302_check_group_c_touch_disp_evf_absence_ael_flash_and_interval(
            exposed_disp_shoot_modes=(
                "DISPLAY_ALL_INFO",
                "NO_DISP_INFO",
                "HISTOGRAM",
                "FOR_VIEWFINDER",
            )
        )
        self.assertFalse(gc.passed)
        self.assertFalse(gc.zero_evf_blackout_firewall_enforced)

    def test_66_gc_touch_operation_invalid_mode_and_swipe_up_rejected(self) -> None:
        gc_op = evaluate_p302_check_group_c_touch_disp_evf_absence_ael_flash_and_interval(
            touch_operation="INVALID"
        )
        self.assertFalse(gc_op.passed)

        gc_sw = evaluate_p302_check_group_c_touch_disp_evf_absence_ael_flash_and_interval(
            swipe_up="SWIPE_LEFT_RIGHT"
        )
        self.assertFalse(gc_sw.passed)

    # --- Section 5: Check Group D — Tier-0 Dual Receipts, 16/16 H0==H3 & Redlines (6 tests) ---

    def test_67_gd_offline_awaiting_receipts_and_dry_run_simulated_ready(self) -> None:
        gd_off, t_off = evaluate_p302_check_group_d_physical_bench_and_tier0(simulate_bench_dry_run=False)
        self.assertTrue(gd_off.passed)
        self.assertFalse(gd_off.tier0_receipt_present)
        self.assertFalse(gd_off.tier0_receipt_verified)
        self.assertGreaterEqual(len(t_off), 1)
        self.assertEqual(gd_off.h0_equals_h3_count, 16)
        self.assertEqual(gd_off.h0_h3_surface_count, 16)

        gd_sim, t_sim = evaluate_p302_check_group_d_physical_bench_and_tier0(simulate_bench_dry_run=True)
        self.assertTrue(gd_sim.passed)
        self.assertEqual(len(t_sim), 0)
        self.assertTrue(gd_sim.tier0_receipt_verified)
        self.assertTrue(gd_sim.distinct_physical_media_verified)
        self.assertFalse(gd_sim.overall_ready_for_hardware_attach)

    def test_68_gd_valid_dual_device_file_receipts_reach_verified_verdict_still_no_attach(self) -> None:
        ra, rb, baselines = build_simulated_phase302_tier0_receipts()
        with tempfile.TemporaryDirectory() as td:
            pa = Path(td) / "copy_a.bin"
            pb = Path(td) / "copy_b.bin"
            pa.write_bytes(ra)
            pb.write_bytes(rb)
            rep = evaluate_realhw_lens_comp_af_illuminator_copy_slot_and_evf_absence_readiness(
                receipt_a_path=pa,
                receipt_b_path=pb,
                st_dev_a_override=1001,
                st_dev_b_override=2002,
                body_serial=DEFAULT_TARGET_BODY_SERIAL,
                emmc_cid=DEFAULT_TARGET_EMMC_CID,
                h0_baselines_a=baselines,
                h0_baselines_b=dict(baselines),
            )
        self.assertEqual(
            rep.go_no_go,
            P302_GO_NO_GO_LENS_COMP_AF_ILLUMINATOR_COPY_SLOT_EVF_ABSENCE_VERIFIED,
        )
        self.assertTrue(rep.tier0_receipt_verified)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertTrue(verify_phase302_report(rep.to_dict()).valid)

    def test_69_gd_same_st_dev_or_single_copy_or_byte_mismatch_rejected(self) -> None:
        ra, rb, baselines = build_simulated_phase302_tier0_receipts()
        gd1, err1 = evaluate_p302_check_group_d_physical_bench_and_tier0(
            receipt_a_bytes=ra,
            receipt_b_bytes=rb,
            st_dev_a_override=555,
            st_dev_b_override=555,
            body_serial=DEFAULT_TARGET_BODY_SERIAL,
            emmc_cid=DEFAULT_TARGET_EMMC_CID,
            h0_baselines_a=baselines,
            h0_baselines_b=baselines,
        )
        self.assertFalse(gd1.tier0_receipt_verified)
        self.assertTrue(any("st_dev_a == st_dev_b" in e for e in err1))

        gd2, err2 = evaluate_p302_check_group_d_physical_bench_and_tier0(
            receipt_a_bytes=ra,
            receipt_b_bytes=rb[:-1] + bytes([rb[-1] ^ 0xFF]),
            st_dev_a_override=101,
            st_dev_b_override=202,
            body_serial=DEFAULT_TARGET_BODY_SERIAL,
            emmc_cid=DEFAULT_TARGET_EMMC_CID,
            h0_baselines_a=baselines,
            h0_baselines_b=baselines,
        )
        self.assertFalse(gd2.tier0_receipt_verified)
        self.assertTrue(any("mismatch" in e for e in err2))

        gd3, _ = evaluate_p302_check_group_d_physical_bench_and_tier0(receipt_a_bytes=ra)
        self.assertFalse(gd3.tier0_receipt_verified)

    def test_70_gd_bad_serial_bad_cid_or_missing_h0_baselines_rejected(self) -> None:
        ra, rb, baselines = build_simulated_phase302_tier0_receipts()
        for kw in (
            {
                "body_serial": "0000000",
                "emmc_cid": DEFAULT_TARGET_EMMC_CID,
                "h0_baselines_a": baselines,
                "h0_baselines_b": baselines,
            },
            {
                "body_serial": DEFAULT_TARGET_BODY_SERIAL,
                "emmc_cid": "0" * 32,
                "h0_baselines_a": baselines,
                "h0_baselines_b": baselines,
            },
            {
                "body_serial": DEFAULT_TARGET_BODY_SERIAL,
                "emmc_cid": DEFAULT_TARGET_EMMC_CID,
                "h0_baselines_a": None,
                "h0_baselines_b": baselines,
            },
        ):
            gd, _ = evaluate_p302_check_group_d_physical_bench_and_tier0(
                receipt_a_bytes=ra,
                receipt_b_bytes=rb,
                st_dev_a_override=11,
                st_dev_b_override=22,
                **kw,
            )
            self.assertFalse(gd.tier0_receipt_verified)

    def test_71_gd_corrupted_crc_or_target_fw_mismatch_rejected(self) -> None:
        ra, _, baselines = build_simulated_phase302_tier0_receipts()
        corrupted = bytearray(ra)
        corrupted[-1] ^= 0x5A
        gd_crc, _ = evaluate_p302_check_group_d_physical_bench_and_tier0(
            receipt_a_bytes=bytes(corrupted),
            receipt_b_bytes=bytes(corrupted),
            st_dev_a_override=11,
            st_dev_b_override=22,
            body_serial=DEFAULT_TARGET_BODY_SERIAL,
            emmc_cid=DEFAULT_TARGET_EMMC_CID,
            h0_baselines_a=baselines,
            h0_baselines_b=baselines,
        )
        self.assertFalse(gd_crc.tier0_receipt_verified)

        gd_fw, _ = evaluate_p302_check_group_d_physical_bench_and_tier0(
            receipt_a_bytes=ra,
            receipt_b_bytes=ra,
            st_dev_a_override=11,
            st_dev_b_override=22,
            body_fw="6.00",
            body_serial=DEFAULT_TARGET_BODY_SERIAL,
            emmc_cid=DEFAULT_TARGET_EMMC_CID,
            h0_baselines_a=baselines,
            h0_baselines_b=baselines,
        )
        self.assertFalse(gd_fw.tier0_receipt_verified)

    def test_72_gd_h0_h3_drift_and_redline_unlock_attempts_rejected(self) -> None:
        gd_drift, _ = evaluate_p302_check_group_d_physical_bench_and_tier0(
            simulate_bench_dry_run=True, simulated_h0_h3_drifted_surfaces=1
        )
        self.assertFalse(gd_drift.passed)
        self.assertEqual(gd_drift.h0_equals_h3_count, 15)
        self.assertTrue(any(P302_GD_ERR_H0_H3_IMMUTABILITY_DRIFT in e for e in gd_drift.errors))

        for bad_kw in (
            {"simulated_passive_tx_bytes": 1},
            {"claim_hardware_live_attach_authorized": True},
            {"claim_persistent_emmc_writes_authorized": True},
            {"claim_cross_model_flash_authorized": True},
        ):
            gd, _ = evaluate_p302_check_group_d_physical_bench_and_tier0(
                simulate_bench_dry_run=True, **bad_kw
            )
            self.assertFalse(gd.passed)
            self.assertTrue(any(P302_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION in e for e in gd.errors))

    # --- Section 6: Top-Level Orchestrator, Report Verifier & Markdown (5 tests) ---

    def test_73_orchestrator_offline_and_dry_run_deterministic_sha256(self) -> None:
        rep_off = evaluate_realhw_lens_comp_af_illuminator_copy_slot_and_evf_absence_readiness(
            force_clean_room=True, simulate_bench_dry_run=False
        )
        self.assertEqual(
            rep_off.overall_status,
            P302_OVERALL_READY_OFFLINE_AWAITING_BENCH_RECEIPTS,
        )
        self.assertEqual(
            rep_off.go_no_go,
            GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT,
        )
        self.assertTrue(rep_off.all_4_check_groups_passed)
        self.assertFalse(rep_off.tier0_receipt_verified)

        rep_a = run_lens_comp_af_illuminator_copy_slot_and_evf_absence_preflight(
            force_clean_room=True, simulate_bench_dry_run=True
        )
        rep_b = run_lens_comp_af_illuminator_copy_slot_and_evf_absence_preflight(
            force_clean_room=True, simulate_bench_dry_run=True
        )
        self.assertEqual(rep_a.go_no_go, GO_NO_GO_DRY_RUN_SIMULATED_READY)
        self.assertEqual(rep_a.report_sha256, rep_b.report_sha256)
        self.assertEqual(rep_a.check_groups_passed, 4)
        self.assertTrue(verify_phase302_report(rep_a.to_dict()).valid)
        self.assertTrue(verify_phase302_report(rep_off.to_dict()).valid)

    def test_74_orchestrator_group_failures_propagate_to_blocked_verdict(self) -> None:
        rep = evaluate_realhw_lens_comp_af_illuminator_copy_slot_and_evf_absence_readiness(
            force_clean_room=True,
            simulate_bench_dry_run=True,
            playback_media_slot=2,
            slot1_contains_tier0_dump=True,
            playback_copy_requested=True,
        )
        self.assertEqual(
            rep.go_no_go,
            P302_GO_NO_GO_BLOCKED_LENS_COMP_AF_ILLUMINATOR_COPY_SLOT_EVF_ABSENCE_FAILURE,
        )
        self.assertEqual(rep.check_groups_passed, 3)
        self.assertFalse(rep.all_4_check_groups_passed)
        self.assertTrue(verify_phase302_report(rep.to_dict()).valid)

    def test_75_verify_phase302_report_tamper_detection_locks_zeroes_and_sha(self) -> None:
        rep = evaluate_realhw_lens_comp_af_illuminator_copy_slot_and_evf_absence_readiness(
            force_clean_room=True, simulate_bench_dry_run=True
        )
        base = rep.to_dict()
        self.assertTrue(verify_phase302_report(base).valid)

        for lock_key in (
            "overall_ready_for_hardware_attach",
            "hardware_live_attachment_authorized",
            "persistent_emmc_writes_authorized",
            "persistent_write_release",
            "spi_nor_write_authorized",
            "el3_payload_transmit_authorized",
            "sd_physical_media_written",
            "cross_model_flash_authorized",
            "builtin_evf_present",
            "fx6_builtin_af_illuminator_present",
            "slot1_tier0_vault_mutated",
        ):
            tampered = dict(base)
            tampered[lock_key] = True
            self.assertFalse(verify_phase302_report(tampered).valid)

        for zero_key in (
            "usb_packets_transmitted",
            "physical_usb_packets_emitted",
            "raw_firmware_bytes_leaked",
            "passive_tx_bytes_emitted",
        ):
            tampered = dict(base)
            tampered[zero_key] = 1
            self.assertFalse(verify_phase302_report(tampered).valid)

        tampered_sha = dict(base)
        tampered_sha["report_sha256"] = "a" * 64
        self.assertFalse(verify_phase302_report(tampered_sha).valid)

    def test_76_verify_phase302_report_rejects_simulated_dry_run_claiming_physical_verified(self) -> None:
        rep = evaluate_realhw_lens_comp_af_illuminator_copy_slot_and_evf_absence_readiness(
            force_clean_room=True, simulate_bench_dry_run=True
        )
        bad = rep.to_dict()
        bad["go_no_go"] = P302_GO_NO_GO_LENS_COMP_AF_ILLUMINATOR_COPY_SLOT_EVF_ABSENCE_VERIFIED
        self.assertFalse(verify_phase302_report(bad).valid)

    def test_77_render_phase302_markdown_contains_all_4_groups_and_redlines(self) -> None:
        rep = evaluate_realhw_lens_comp_af_illuminator_copy_slot_and_evf_absence_readiness(
            force_clean_room=True, simulate_bench_dry_run=True
        )
        md = render_phase302_markdown(rep)
        for token in (
            P302_SCHEMA,
            P302_CHECK_GROUP_A_ID,
            P302_CHECK_GROUP_B_ID,
            P302_CHECK_GROUP_C_ID,
            P302_CHECK_GROUP_D_ID,
            "ready_attach=False",
            "emmc_writes=False",
            "builtin_evf=False",
            "fx6_af_illum=False",
            "slot1_mutated=False",
            "leaked_bytes=0",
            rep.report_sha256,
        ):
            self.assertIn(token, md)

    # --- Section 7: CLI Integration Tests via sys.executable (7 tests) ---

    def test_78_cli_help_cleanly_escapes_percent_in_python3(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "fx6_closure",
                "preflight-lens-comp-af-illuminator-copy-slot-and-evf-absence",
                "--help",
            ],
            cwd=REPO_ROOT,
            env=_subprocess_env(clean_room=True),
            capture_output=True,
            text=True,
            timeout=_ci_subprocess_timeout(),
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        self.assertIn("preflight-lens-comp-af-illuminator-copy-slot-and-evf-absence", proc.stdout)
        self.assertIn("--playback-copy-requested", proc.stdout)
        self.assertIn("--activate-dormant-evf-finder-mode", proc.stdout)

    def test_79_cli_offline_exits_2_with_ready_offline_awaiting_bench_receipts(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "fx6_closure",
                "preflight-lens-comp-af-illuminator-copy-slot-and-evf-absence",
                "--clean-room",
                "--json",
            ],
            cwd=REPO_ROOT,
            env=_subprocess_env(clean_room=True),
            capture_output=True,
            text=True,
            timeout=_ci_subprocess_timeout(),
        )
        self.assertEqual(proc.returncode, 2, msg=proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(
            payload["overall_status"],
            P302_OVERALL_READY_OFFLINE_AWAITING_BENCH_RECEIPTS,
        )
        self.assertEqual(
            payload["go_no_go"],
            GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT,
        )
        self.assertTrue(verify_phase302_report(payload).valid)

    def test_80_cli_simulate_bench_dry_run_json_and_summary_exit_0_local_mode(self) -> None:
        t0 = time.perf_counter()
        proc_json = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "fx6_closure",
                "preflight-lens-comp-af-illuminator-copy-slot-and-evf-absence",
                "--simulate-bench-dry-run",
                "--json",
            ],
            cwd=REPO_ROOT,
            env=_subprocess_env(clean_room=False),
            capture_output=True,
            text=True,
            timeout=_ci_subprocess_timeout(),
        )
        dt = time.perf_counter() - t0
        self.assertLess(dt, _ci_subprocess_timeout())
        self.assertEqual(proc_json.returncode, 0, msg=proc_json.stderr)
        payload = json.loads(proc_json.stdout)
        self.assertEqual(payload["go_no_go"], GO_NO_GO_DRY_RUN_SIMULATED_READY)
        self.assertEqual(payload["check_groups_passed"], 4)
        self.assertTrue(verify_phase302_report(payload).valid)

        proc_sum = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "fx6_closure",
                "preflight-lens-comp-af-illuminator-copy-slot-and-evf-absence",
                "--simulate-bench-dry-run",
                "--summary",
            ],
            cwd=REPO_ROOT,
            env=_subprocess_env(clean_room=False),
            capture_output=True,
            text=True,
            timeout=_ci_subprocess_timeout(),
        )
        self.assertEqual(proc_sum.returncode, 0, msg=proc_sum.stderr)
        self.assertIn("OVERALL=DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH", proc_sum.stdout)
        self.assertIn("check_groups=4/4", proc_sum.stdout)

    def test_81_cli_force_clean_room_simulate_bench_dry_run_json_and_markdown_files(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            out_json = Path(td) / "p302.json"
            out_md = Path(td) / "p302.md"
            proc = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    "-m",
                    "fx6_closure",
                    "preflight-lens-comp-af-illuminator-copy-slot-and-evf-absence",
                    "--force-clean-room",
                    "--simulate-bench-dry-run",
                    "--json",
                    "--output",
                    str(out_json),
                    "--markdown-out",
                    str(out_md),
                ],
                cwd=REPO_ROOT,
                env=_subprocess_env(clean_room=True),
                capture_output=True,
                text=True,
                timeout=_ci_subprocess_timeout(),
            )
            self.assertEqual(proc.returncode, 0, msg=proc.stderr)
            self.assertTrue(out_json.is_file())
            self.assertTrue(out_md.is_file())
            payload = json.loads(out_json.read_text(encoding="utf-8"))
            self.assertEqual(payload["verification_mode"], "CLEAN_ROOM_SYNTHETIC")
            self.assertTrue(verify_phase302_report(payload).valid)
            self.assertIn(P302_CHECK_GROUP_B_ID, out_md.read_text(encoding="utf-8"))

    def test_82_cli_fx3_fx6_force_clean_room_env_var_simulate_dry_run_exit_0(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "fx6_closure",
                "preflight-lens-comp-af-illuminator-copy-slot-and-evf-absence",
                "--simulate-bench-dry-run",
                "--json",
            ],
            cwd=REPO_ROOT,
            env=_subprocess_env(clean_room=False, force_clean_room_var=True),
            capture_output=True,
            text=True,
            timeout=_ci_subprocess_timeout(),
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["verification_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(payload["go_no_go"], GO_NO_GO_DRY_RUN_SIMULATED_READY)
        self.assertTrue(verify_phase302_report(payload).valid)

    def test_83_cli_negative_copy_slot2_to_slot1_reverse_vault_firewall_exits_2(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "fx6_closure",
                "preflight-lens-comp-af-illuminator-copy-slot-and-evf-absence",
                "--clean-room",
                "--simulate-bench-dry-run",
                "--playback-media-slot",
                "2",
                "--playback-copy-requested",
                "--json",
            ],
            cwd=REPO_ROOT,
            env=_subprocess_env(clean_room=True),
            capture_output=True,
            text=True,
            timeout=_ci_subprocess_timeout(),
        )
        self.assertEqual(proc.returncode, 2, msg=proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(
            payload["go_no_go"],
            P302_GO_NO_GO_BLOCKED_LENS_COMP_AF_ILLUMINATOR_COPY_SLOT_EVF_ABSENCE_FAILURE,
        )
        self.assertFalse(payload["slot1_tier0_vault_mutated"])
        self.assertTrue(
            any(P302_GB_ERR_PLAYBACK_COPY_REVERSE_SLOT1_VAULT_TRAP in e for e in payload["errors"])
        )

    def test_84_cli_negative_zero_evf_blackout_and_shading_auto_low_exit_2(self) -> None:
        for extra_flag, expected_err in (
            ("--activate-dormant-evf-finder-mode", P302_GC_ERR_ZERO_EVF_BLACK_SCREEN_LOCKOUT_TRAP),
            ("--dormant-shading-auto-low-requested", P302_GA_ERR_SHADING_AUTO_LOW_EOPNOTSUPP),
        ):
            proc = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    "-m",
                    "fx6_closure",
                    "preflight-lens-comp-af-illuminator-copy-slot-and-evf-absence",
                    "--clean-room",
                    "--simulate-bench-dry-run",
                    extra_flag,
                    "--json",
                ],
                cwd=REPO_ROOT,
                env=_subprocess_env(clean_room=True),
                capture_output=True,
                text=True,
                timeout=_ci_subprocess_timeout(),
            )
            self.assertEqual(proc.returncode, 2, msg=f"{extra_flag}: {proc.stderr}")
            payload = json.loads(proc.stdout)
            self.assertTrue(any(expected_err in e for e in payload["errors"]))


if __name__ == "__main__":
    unittest.main()
