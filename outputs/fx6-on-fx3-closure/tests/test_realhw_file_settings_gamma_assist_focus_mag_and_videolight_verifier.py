"""Dual-mode unit tests (68 cases) for Phase 275 (`preflight-file-settings-gamma-assist-focus-mag-and-videolight`):
7th Physical Bench & Pre-Shoot Readiness Verifier across Waves 44–46 check groups (`A..D`).

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
from fx6_closure.realhw_file_settings_gamma_assist_focus_mag_and_videolight_verifier import (  # noqa: E402
    P275_4CH_AUDIO_MONITORING_FIVE_ROUTES,
    P275_ACTIVE_LOG_SHOOTING_MODES,
    P275_APPFW_MONITOR_POWER_LINKAGE_FOUR_MODES,
    P275_APPFW_MONITOR_POWER_LINKAGE_RESIDS,
    P275_AREA_DATE_TIME_EXACT_LABEL,
    P275_AREA_DATE_TIME_FOUR_SUBITEMS,
    P275_AUTO_MAG_IN_MF_EXACT_LABEL,
    P275_BKLANG_FOUR_LANG_CODES,
    P275_BKLANG_REGISTER_HEX,
    P275_CHECK_GROUP_A_ID,
    P275_CHECK_GROUP_B_ID,
    P275_CHECK_GROUP_C_ID,
    P275_CHECK_GROUP_D_ID,
    P275_DEFAULT_STILL_FILE_PREFIX,
    P275_DEFAULT_TITLE_NAME,
    P275_FOCUS_MAG_DEFAULT_CUSTOM_BUTTON,
    P275_FX3_ILC2210_POWER_SETTING_TWO_ITEMS,
    P275_FX3_LANGUAGE_COUNT,
    P275_FX6_LANGUAGE_COUNT,
    P275_GA_ERR_AUTO_REVIEW_OR_TCUB_6ITEM_RESET_PERSISTENCE,
    P275_GA_ERR_MODEL_OR_FW_FLOOR,
    P275_GA_ERR_MOVIE_FILE_SETTINGS_CAMID_REEL_OR_37CHAR,
    P275_GA_ERR_STILL_PREFIX_DSC_UNDERSCORE_OR_SLOT1_VAULT_MUTATION,
    P275_GB_ERR_DISPLAY_LUT_OR_SELECT_LUT_USER16_INVALID,
    P275_GB_ERR_GAMMA_ASSIST_EXTERNAL_HDMI_BOUNDARY,
    P275_GB_ERR_GAMMA_ASSIST_LOG_LOCKOUT_VIOLATED,
    P275_GC_ERR_AREA_DATE_TIME_OR_ZERO_RF_CREATORS_APP_SYNC,
    P275_GC_ERR_FOCUS_MAG_4X_CLEAN_HDMI_OR_RAW_LOCKOUT,
    P275_GC_ERR_HDMI_RESOLUTION_LOG_1080P_OR_4K_DOWNSHIFT,
    P275_GC_ERR_PEAKING_OR_AF_ILLUMINATOR_MOVIE_AFC_LOCKOUT,
    P275_GC_ERR_VIDEO_LIGHT_MODE_OR_MI_SHOE_5V_900MA_OVERCURRENT,
    P275_GD_ERR_BKLANG_34_VS_29_OR_SETUP_RESET_PERSISTENCE,
    P275_GD_ERR_DELETE_CONFIRM_OR_SLOT1_VAULT_DELETE_FORMAT_BLOCKED,
    P275_GD_ERR_H0_H3_IMMUTABILITY_DRIFT,
    P275_GD_ERR_POWER_SETTING_OPTION_REALITY_SPLIT_OR_9COND,
    P275_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID,
    P275_GD_ERR_VOLUME_OR_4CH_MONITORING_5ROUTE_OR_FEEDBACK,
    P275_GO_NO_GO_BLOCKED_FILE_SETTINGS_GAMMA_ASSIST_FOCUS_MAG_VIDEOLIGHT_FAILURE,
    P275_GO_NO_GO_FILE_SETTINGS_GAMMA_ASSIST_FOCUS_MAG_VIDEOLIGHT_VERIFIED,
    P275_HEADLESS_SAFE_MONITOR_POWER_LINK_MODES,
    P275_MI_SHOE_5V_MAX_CURRENT_MA,
    P275_MOVIE_FIXED_CLIP_DIR,
    P275_OVERALL_READY_OFFLINE_AWAITING_BENCH_RECEIPTS,
    P275_POWER_SAVE_NINE_DEACTIVATION_CONDITIONS,
    P275_SAFE_AIRGAPPED_BATTERY_POWER_SAVE_TIMES,
    P275_SELECT_LUT_THREE_PRESETS,
    P275_SELECT_LUT_USER_SLOTS,
    P275_SONY_HELP_GUIDE_ID,
    P275_TCUB_SIX_ITEMS,
    P275_TITLE_NAME_MAX_CHARS,
    P275_USER_LUT_MAX_SLOTS,
    P275_VALID_GAMMA_ASSIST_TYPES,
    P275_VALID_SELECT_LUTS,
    P275_VALID_VIDEO_LIGHT_MODES,
    P275_VOLUME_SETTINGS_DEFAULT,
    P275_VOLUME_SETTINGS_MAX,
    P275_VOLUME_SETTINGS_MIN,
    PHASE_275_CHECK_GROUP_IDS,
    PHASE_275_SCHEMA,
    PHASE_275_VERSION,
    build_simulated_phase275_tier0_receipts,
    evaluate_p275_check_group_a_cinema_slate_and_timecode,
    evaluate_p275_check_group_b_gamma_assist_and_display_lut,
    evaluate_p275_check_group_c_focus_mag_videolight_and_hdmi_res,
    evaluate_p275_check_group_d_power_bklang_volume_delete_and_tier0,
    evaluate_realhw_file_settings_gamma_assist_focus_mag_and_videolight_readiness,
    inspect_phase275_donors_bounded,
    render_phase275_markdown,
    run_file_settings_gamma_assist_focus_mag_and_videolight_preflight,
    verify_phase275_report,
)
from fx6_closure.realhw_sd_stageb_bundle_and_uninstaller import (  # noqa: E402
    DEFAULT_TARGET_BODY_SERIAL,
    DEFAULT_TARGET_EMMC_CID,
)


def _timing_budget(local_seconds: float, ci_seconds: float) -> float:
    return ci_seconds if os.environ.get("GITHUB_ACTIONS") == "true" else local_seconds


class TestPhase275FileSettingsGammaAssistFocusMagVideoLightVerifier(unittest.TestCase):
    """68 deterministic dual-mode unit tests for Phase 275 7th physical bench verifier."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._suite_t0 = time.perf_counter()

    @classmethod
    def tearDownClass(cls) -> None:
        elapsed = time.perf_counter() - cls._suite_t0
        limit = _timing_budget(6.0, 15.0)
        assert elapsed < limit, f"Phase 275 test suite exceeded <{limit:.1f}s budget: {elapsed:.3f}s"

    # --- Group 0: Exports, Non-Shadowing & Bounded O_RDONLY / Clean-Room Parity (6 tests) ---

    def test_01_public_p275_symbols_exported_without_shadowing_prior_phases(self) -> None:
        self.assertEqual(
            PHASE_275_SCHEMA,
            "realhw_file_settings_gamma_assist_focus_mag_and_videolight_verifier_v1",
        )
        self.assertEqual(PHASE_275_VERSION, "275.0.0")
        for sym in (
            "PHASE_275_SCHEMA",
            "PHASE_275_VERSION",
            "P275_CHECK_GROUP_A_ID",
            "P275_CHECK_GROUP_B_ID",
            "P275_CHECK_GROUP_C_ID",
            "P275_CHECK_GROUP_D_ID",
            "evaluate_realhw_file_settings_gamma_assist_focus_mag_and_videolight_readiness",
            "run_file_settings_gamma_assist_focus_mag_and_videolight_preflight",
            "verify_phase275_report",
            "render_phase275_markdown",
        ):
            self.assertIn(sym, fx6_closure.__all__)
            self.assertTrue(hasattr(fx6_closure, sym))
        # Verify prior phase exports remain non-shadowed
        self.assertEqual(
            fx6_closure.CHECK_GROUP_A_ID,
            "GROUP_A_PIXEL_MAPPING_CNFLASHA_RO_AND_NTSCPAL_GAMMA_SPLIT",
        )
        self.assertEqual(
            fx6_closure.P248_CHECK_GROUP_A_ID,
            "GROUP_A_RECOVER_IMAGEDB_BATTERY_SLOT1_VAULT_AND_MONITOR_FLIP",
        )
        self.assertEqual(
            fx6_closure.P261_CHECK_GROUP_A_ID,
            "GROUP_A_DIFF_SET_8ITEMS_SHUTTER_ANGLE_CUSTOM_KEY_AND_EVFLESS",
        )
        self.assertIs(
            run_file_settings_gamma_assist_focus_mag_and_videolight_preflight,
            evaluate_realhw_file_settings_gamma_assist_focus_mag_and_videolight_readiness,
        )
        self.assertEqual(
            PHASE_275_CHECK_GROUP_IDS,
            (
                P275_CHECK_GROUP_A_ID,
                P275_CHECK_GROUP_B_ID,
                P275_CHECK_GROUP_C_ID,
                P275_CHECK_GROUP_D_ID,
            ),
        )

    def test_02_donor_inspection_bounded_and_zero_leaked_bytes(self) -> None:
        max_sec = _timing_budget(0.15, 1.0)
        res = inspect_phase275_donors_bounded(max_seconds=max_sec)
        self.assertTrue(res.passed, res.errors)
        self.assertTrue(res.read_only_o_rdonly_enforced)
        self.assertTrue(res.within_150ms_budget)
        self.assertEqual(res.raw_firmware_bytes_leaked, 0)
        self.assertIn(res.verification_mode, ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"))

    def test_03_force_clean_room_synthetic_and_env_overrides(self) -> None:
        res_direct = inspect_phase275_donors_bounded(force_clean_room=True)
        self.assertTrue(res_direct.passed)
        self.assertEqual(res_direct.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(res_direct.fx3_im_elf_verified)
        self.assertTrue(res_direct.fx6_appfw_verified)
        for env_key in ("FX3_CLEAN_ROOM_TEST", "FX3_FX6_FORCE_CLEAN_ROOM"):
            with mock.patch.dict(os.environ, {env_key: "1"}):
                res_env = inspect_phase275_donors_bounded()
                self.assertTrue(res_env.passed)
                self.assertEqual(res_env.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_04_missing_local_donors_fail_closed_when_not_clean_room(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            res = inspect_phase275_donors_bounded(
                fx6_lib_dir=Path(tmp) / "missing_fx6",
                fx3_modules_dir=Path(tmp) / "missing_mods",
                force_clean_room=False,
            )
            self.assertFalse(res.passed)
            self.assertEqual(res.verification_mode, "LOCAL_DONOR_O_RDONLY")
            self.assertEqual(res.raw_firmware_bytes_leaked, 0)
            self.assertTrue(res.errors)

    def test_05_group_a_model_fw_floor_and_help_guide_enforced(self) -> None:
        ok = evaluate_p275_check_group_a_cinema_slate_and_timecode()
        self.assertTrue(ok.passed)
        self.assertEqual(ok.sony_help_guide_id, P275_SONY_HELP_GUIDE_ID)

        bad_model = evaluate_p275_check_group_a_cinema_slate_and_timecode(body_model_id=0x91030099)
        self.assertFalse(bad_model.passed)
        self.assertTrue(any(P275_GA_ERR_MODEL_OR_FW_FLOOR in e for e in bad_model.errors))

        bad_fw = evaluate_p275_check_group_a_cinema_slate_and_timecode(body_fw="2.03")
        self.assertFalse(bad_fw.passed)
        self.assertTrue(any(P275_GA_ERR_MODEL_OR_FW_FLOOR in e for e in bad_fw.errors))

        bad_guide = evaluate_p275_check_group_a_cinema_slate_and_timecode(
            sony_help_guide_id="ilc/9999"
        )
        self.assertFalse(bad_guide.passed)
        self.assertTrue(any(P275_GA_ERR_MODEL_OR_FW_FLOOR in e for e in bad_guide.errors))

    def test_06_clean_room_and_local_reports_share_check_group_parity(self) -> None:
        rep_clean = evaluate_realhw_file_settings_gamma_assist_focus_mag_and_videolight_readiness(
            force_clean_room=True,
            simulate_bench_dry_run=True,
        )
        rep_default = evaluate_realhw_file_settings_gamma_assist_focus_mag_and_videolight_readiness(
            simulate_bench_dry_run=True,
        )
        self.assertEqual(rep_clean.check_groups_passed, 4)
        self.assertEqual(rep_default.check_groups_passed, 4)
        self.assertEqual(rep_clean.go_no_go, rep_default.go_no_go)

    # --- Group A: Wave 44 Cinema Slate File Settings, Still Prefix, Auto Review & TC/UB (11 tests) ---

    def test_07_group_a_nominal_movie_camid_reel_and_default_title(self) -> None:
        res = evaluate_p275_check_group_a_cinema_slate_and_timecode()
        self.assertTrue(res.passed, res.errors)
        self.assertEqual(res.camera_id, "A")
        self.assertEqual(res.reel_number, 1)
        self.assertEqual(res.camera_position, "C")
        self.assertEqual(res.title_name_len, len(P275_DEFAULT_TITLE_NAME))
        self.assertEqual(res.movie_clip_fixed_dir, P275_MOVIE_FIXED_CLIP_DIR)

    def test_08_group_a_37_char_title_boundary_passes_38_char_rejected(self) -> None:
        title_37 = "F" * P275_TITLE_NAME_MAX_CHARS
        res_ok = evaluate_p275_check_group_a_cinema_slate_and_timecode(title_name=title_37)
        self.assertTrue(res_ok.passed, res_ok.errors)
        self.assertEqual(res_ok.title_name_len, 37)

        res_bad = evaluate_p275_check_group_a_cinema_slate_and_timecode(
            title_name=("F" * (P275_TITLE_NAME_MAX_CHARS + 1))
        )
        self.assertFalse(res_bad.passed)
        self.assertTrue(
            any(P275_GA_ERR_MOVIE_FILE_SETTINGS_CAMID_REEL_OR_37CHAR in e for e in res_bad.errors)
        )

    def test_09_group_a_cam_id_reel_range_and_camera_position_validated(self) -> None:
        for kwargs in (
            {"camera_id": "AB"},
            {"camera_id": "1"},
            {"reel_number": 0},
            {"reel_number": 1000},
            {"camera_position": "X"},
            {"custom_movie_folder_requested": True},
            {"movie_clip_dir": "PRIVATE/CUSTOM/CLIP"},
        ):
            res = evaluate_p275_check_group_a_cinema_slate_and_timecode(**kwargs)
            self.assertFalse(res.passed, f"Expected failure for {kwargs}")
            self.assertTrue(
                any(P275_GA_ERR_MOVIE_FILE_SETTINGS_CAMID_REEL_OR_37CHAR in e for e in res.errors)
            )
        # Valid edge L/R position and Reel 999 Z
        res_edge = evaluate_p275_check_group_a_cinema_slate_and_timecode(
            camera_id="Z", reel_number=999, camera_position="R"
        )
        self.assertTrue(res_edge.passed, res_edge.errors)

    def test_10_group_a_still_dsc_prefix_and_leading_underscore_rejected(self) -> None:
        res_ok = evaluate_p275_check_group_a_cinema_slate_and_timecode(
            still_file_prefix=P275_DEFAULT_STILL_FILE_PREFIX
        )
        self.assertTrue(res_ok.passed)

        res_alt = evaluate_p275_check_group_a_cinema_slate_and_timecode(still_file_prefix="FX3")
        self.assertTrue(res_alt.passed)

        for bad_prefix in ("_SC", "_01", "AB", "ABCD", "fx3"):
            res_bad = evaluate_p275_check_group_a_cinema_slate_and_timecode(
                still_file_prefix=bad_prefix
            )
            self.assertFalse(res_bad.passed, f"Expected rejection for prefix={bad_prefix!r}")
            self.assertTrue(
                any(
                    P275_GA_ERR_STILL_PREFIX_DSC_UNDERSCORE_OR_SLOT1_VAULT_MUTATION in e
                    for e in res_bad.errors
                )
            )

    def test_11_group_a_slot1_dcim_forced_reset_and_new_folder_blocked_on_vault(self) -> None:
        for bad_kwargs in (
            {"still_forced_file_number_reset_slot": 1},
            {"still_create_new_folder_slot": 1},
            {"expect_slot1_dcim_mutation_allowed": True},
        ):
            res = evaluate_p275_check_group_a_cinema_slate_and_timecode(
                slot1_contains_tier0_dump=True, **bad_kwargs
            )
            self.assertFalse(res.passed)
            self.assertGreater(res.slot1_vault_folder_mutation_events, 0)
            self.assertTrue(
                any(
                    P275_GA_ERR_STILL_PREFIX_DSC_UNDERSCORE_OR_SLOT1_VAULT_MUTATION in e
                    for e in res.errors
                )
            )

        # Slot 2 DCIM folder operations remain permitted
        res_slot2 = evaluate_p275_check_group_a_cinema_slate_and_timecode(
            slot1_contains_tier0_dump=True,
            still_forced_file_number_reset_slot=2,
            still_create_new_folder_slot=2,
        )
        self.assertTrue(res_slot2.passed, res_slot2.errors)
        self.assertEqual(res_slot2.slot1_vault_folder_mutation_events, 0)

    def test_12_group_a_auto_review_off_cinema_default_and_movie_scope_rejected(self) -> None:
        res_off = evaluate_p275_check_group_a_cinema_slate_and_timecode(auto_review="OFF")
        self.assertTrue(res_off.passed)

        res_2s = evaluate_p275_check_group_a_cinema_slate_and_timecode(auto_review="2_SEC")
        self.assertFalse(res_2s.passed)
        self.assertTrue(
            any(P275_GA_ERR_AUTO_REVIEW_OR_TCUB_6ITEM_RESET_PERSISTENCE in e for e in res_2s.errors)
        )

        res_mv = evaluate_p275_check_group_a_cinema_slate_and_timecode(expect_auto_review_in_movie=True)
        self.assertFalse(res_mv.passed)
        self.assertFalse(res_mv.auto_review_still_only_verified)

    def test_13_group_a_six_tcub_items_exact_and_24p_pal_ndf_rule(self) -> None:
        res_ok = evaluate_p275_check_group_a_cinema_slate_and_timecode()
        self.assertTrue(res_ok.passed)
        self.assertEqual(len(res_ok.tcub_six_items), 6)
        self.assertEqual(res_ok.tcub_six_items, P275_TCUB_SIX_ITEMS)

        # DF rejected at 24.00p and on PAL (25p/50p)
        res_24p_df = evaluate_p275_check_group_a_cinema_slate_and_timecode(
            tc_format="DF", rec_frame_rate_fps=24.0
        )
        self.assertFalse(res_24p_df.passed)

        res_pal_df = evaluate_p275_check_group_a_cinema_slate_and_timecode(
            tc_format="DF", rec_frame_rate_fps=25.0, video_system="PAL"
        )
        self.assertFalse(res_pal_df.passed)

        # Missing one TC/UB item rejected
        res_5item = evaluate_p275_check_group_a_cinema_slate_and_timecode(
            tcub_items=P275_TCUB_SIX_ITEMS[:-1]
        )
        self.assertFalse(res_5item.passed)

    def test_14_group_a_tcub_and_file_settings_survive_camera_settings_reset(self) -> None:
        res_reset = evaluate_p275_check_group_a_cinema_slate_and_timecode(
            reset_action="CAMERA_SETTINGS_RESET",
            title_name="SCENE_01A",
            still_file_prefix="FX3",
            tc_format="NDF",
        )
        self.assertTrue(res_reset.passed, res_reset.errors)
        self.assertTrue(res_reset.movie_file_settings_survive_camera_reset)
        self.assertTrue(res_reset.still_file_folder_survive_camera_reset)
        self.assertTrue(res_reset.all_6_tcub_survive_camera_reset)
        self.assertEqual(res_reset.effective_tc_format_after_reset, "NDF")

        # Claiming TC/UB reset during Camera Settings Reset fails
        res_bad = evaluate_p275_check_group_a_cinema_slate_and_timecode(
            reset_action="CAMERA_SETTINGS_RESET",
            claimed_tcub_reset_on_camera_reset=True,
        )
        self.assertFalse(res_bad.passed)
        self.assertFalse(res_bad.all_6_tcub_survive_camera_reset)

    def test_15_group_a_initialize_restores_defaults_for_title_prefix_and_tc(self) -> None:
        res_init = evaluate_p275_check_group_a_cinema_slate_and_timecode(
            reset_action="INITIALIZE",
            title_name="CUSTOM_SLATE",
            still_file_prefix="FX3",
            tc_format="NDF",
            claimed_title_name_after_reset="C",
            claimed_still_prefix_after_reset="DSC",
            claimed_tc_format_after_reset="DF",
        )
        self.assertTrue(res_init.passed, res_init.errors)
        self.assertEqual(res_init.effective_tc_format_after_reset, "DF")

    def test_16_group_a_file_settings_reset_drift_caught_on_camera_reset(self) -> None:
        res_bad_mv = evaluate_p275_check_group_a_cinema_slate_and_timecode(
            reset_action="CAMERA_SETTINGS_RESET",
            title_name="SLATE_A",
            claimed_title_name_after_reset="C",
        )
        self.assertFalse(res_bad_mv.passed)
        res_bad_st = evaluate_p275_check_group_a_cinema_slate_and_timecode(
            reset_action="CAMERA_SETTINGS_RESET",
            still_file_prefix="FX3",
            claimed_still_prefix_after_reset="DSC",
        )
        self.assertFalse(res_bad_st.passed)

    def test_17_group_a_tcub_disp_setting_and_tc_make_options(self) -> None:
        res_ub = evaluate_p275_check_group_a_cinema_slate_and_timecode(
            tcub_disp_setting="UB", tc_make="REGENERATE", tc_run="REC_RUN"
        )
        self.assertTrue(res_ub.passed, res_ub.errors)
        self.assertEqual(res_ub.tcub_disp_setting, "UB")

        res_bad = evaluate_p275_check_group_a_cinema_slate_and_timecode(
            tcub_disp_setting="SMPTE_INVALID"
        )
        self.assertFalse(res_bad.passed)

    # --- Group B: Wave 44 [Gamma Display Assist] vs [Display LUT] / [Select LUT] Clean HDMI (9 tests) ---

    def test_18_group_b_gamma_assist_hard_locked_off_for_all_log_modes(self) -> None:
        for log_mode in P275_ACTIVE_LOG_SHOOTING_MODES:
            res_ok = evaluate_p275_check_group_b_gamma_assist_and_display_lut(
                log_shooting_mode=log_mode,
                gamma_display_assist="OFF",
            )
            self.assertTrue(res_ok.passed, f"Failed for {log_mode}: {res_ok.errors}")
            self.assertTrue(res_ok.gamma_assist_locked_off_by_log)

            res_bad = evaluate_p275_check_group_b_gamma_assist_and_display_lut(
                log_shooting_mode=log_mode,
                gamma_display_assist="ON",
            )
            self.assertFalse(res_bad.passed, f"Should fail when Assist=ON under {log_mode}")
            self.assertTrue(
                any(P275_GB_ERR_GAMMA_ASSIST_LOG_LOCKOUT_VIOLATED in e for e in res_bad.errors)
            )

    def test_19_group_b_gamma_assist_expect_active_under_log_rejected(self) -> None:
        res = evaluate_p275_check_group_b_gamma_assist_and_display_lut(
            log_shooting_mode="FLEXIBLE_ISO",
            gamma_display_assist="OFF",
            expect_gamma_assist_active_under_log=True,
        )
        self.assertFalse(res.passed)
        self.assertTrue(
            any(P275_GB_ERR_GAMMA_ASSIST_LOG_LOCKOUT_VIOLATED in e for e in res.errors)
        )

    def test_20_group_b_log_off_allows_gamma_assist_all_4_types(self) -> None:
        self.assertEqual(len(P275_VALID_GAMMA_ASSIST_TYPES), 4)
        for assist_type in P275_VALID_GAMMA_ASSIST_TYPES:
            res = evaluate_p275_check_group_b_gamma_assist_and_display_lut(
                log_shooting_mode="OFF",
                gamma_display_assist="ON",
                gamma_disp_assist_type=assist_type,
            )
            self.assertTrue(res.passed, f"Failed for {assist_type}: {res.errors}")
            self.assertFalse(res.gamma_assist_locked_off_by_log)

    def test_21_group_b_gamma_assist_external_hdmi_clean_boundary_enforced(self) -> None:
        res_flag = evaluate_p275_check_group_b_gamma_assist_and_display_lut(
            log_shooting_mode="OFF",
            gamma_display_assist="ON",
            expect_gamma_assist_on_external_hdmi=True,
        )
        self.assertFalse(res_flag.passed)
        self.assertFalse(res_flag.gamma_assist_lcd_only_clean_hdmi)
        self.assertGreater(res_flag.external_hdmi_gamma_assist_pixels, 0)
        self.assertTrue(
            any(P275_GB_ERR_GAMMA_ASSIST_EXTERNAL_HDMI_BOUNDARY in e for e in res_flag.errors)
        )

        res_px = evaluate_p275_check_group_b_gamma_assist_and_display_lut(
            log_shooting_mode="OFF",
            gamma_display_assist="ON",
            simulated_external_hdmi_gamma_assist_pixels=128,
        )
        self.assertFalse(res_px.passed)

    def test_22_group_b_select_lut_all_3_presets_and_16_user_slots(self) -> None:
        self.assertEqual(len(P275_SELECT_LUT_THREE_PRESETS), 3)
        self.assertEqual(len(P275_SELECT_LUT_USER_SLOTS), 16)
        self.assertEqual(len(P275_VALID_SELECT_LUTS), 19)
        for lut_name in P275_VALID_SELECT_LUTS:
            res = evaluate_p275_check_group_b_gamma_assist_and_display_lut(
                log_shooting_mode="CINE_EI",
                display_lut="ON",
                select_lut=lut_name,
            )
            self.assertTrue(res.passed, f"Failed for Select LUT {lut_name!r}: {res.errors}")

    def test_23_group_b_invalid_select_lut_or_user17_rejected(self) -> None:
        for bad_lut in ("User17", "User0", "Rec2020_Bad"):
            res = evaluate_p275_check_group_b_gamma_assist_and_display_lut(select_lut=bad_lut)
            self.assertFalse(res.passed)
            self.assertTrue(
                any(
                    P275_GB_ERR_DISPLAY_LUT_OR_SELECT_LUT_USER16_INVALID in e
                    for e in res.errors
                )
            )

    def test_24_group_b_user_lut_slot_count_mismatch_rejected(self) -> None:
        res = evaluate_p275_check_group_b_gamma_assist_and_display_lut(user_lut_slot_count=8)
        self.assertFalse(res.passed)
        self.assertTrue(
            any(P275_GB_ERR_DISPLAY_LUT_OR_SELECT_LUT_USER16_INVALID in e for e in res.errors)
        )

    def test_25_group_b_setup_lut_assist_survive_camera_settings_reset(self) -> None:
        res_ok = evaluate_p275_check_group_b_gamma_assist_and_display_lut(
            reset_action="CAMERA_SETTINGS_RESET",
            display_lut="OFF",
            claimed_display_lut_after_reset="OFF",
        )
        self.assertTrue(res_ok.passed, res_ok.errors)
        self.assertTrue(res_ok.setup_lut_assist_survive_camera_reset)

        res_bad = evaluate_p275_check_group_b_gamma_assist_and_display_lut(
            reset_action="CAMERA_SETTINGS_RESET",
            claimed_setup_lut_reset_on_camera_reset=True,
        )
        self.assertFalse(res_bad.passed)

    def test_26_group_b_display_lut_normalization_aliases(self) -> None:
        res_slog3 = evaluate_p275_check_group_b_gamma_assist_and_display_lut(select_lut="s_log3")
        self.assertTrue(res_slog3.passed)
        self.assertEqual(res_slog3.select_lut, "S-Log3")

        res_709 = evaluate_p275_check_group_b_gamma_assist_and_display_lut(select_lut="709_800pct")
        self.assertTrue(res_709.passed)
        self.assertEqual(res_709.select_lut, "709(800%)")

    # --- Group C: Wave 45 Focus Magnifier 4x, Peaking, Zero-RF Time, Video Light & HDMI Res (14 tests) ---

    def test_27_group_c_auto_magnifier_in_mf_exact_label_and_4x_magnifier(self) -> None:
        res_ok = evaluate_p275_check_group_c_focus_mag_videolight_and_hdmi_res(
            initial_focus_mag_movie="4.0x",
            initial_focus_mag_still="4x",
            focus_magnif_time="NO_LIMIT",
        )
        self.assertTrue(res_ok.passed, res_ok.errors)
        self.assertEqual(res_ok.auto_mag_label_verified, P275_AUTO_MAG_IN_MF_EXACT_LABEL)
        self.assertEqual(res_ok.focus_magnifier_custom_button, P275_FOCUS_MAG_DEFAULT_CUSTOM_BUTTON)
        self.assertEqual(res_ok.initial_focus_mag_movie, "X4_0")
        self.assertEqual(res_ok.initial_focus_mag_still, "X4_0")

        res_bad_label = evaluate_p275_check_group_c_focus_mag_videolight_and_hdmi_res(
            auto_mag_label="MF Assist"
        )
        self.assertFalse(res_bad_label.passed)
        self.assertTrue(
            any(P275_GC_ERR_FOCUS_MAG_4X_CLEAN_HDMI_OR_RAW_LOCKOUT in e for e in res_bad_label.errors)
        )

    def test_28_group_c_focus_magnifier_clean_hdmi_exit_isolation(self) -> None:
        res_bad = evaluate_p275_check_group_c_focus_mag_videolight_and_hdmi_res(
            expect_magnifier_baked_on_clean_hdmi=True
        )
        self.assertFalse(res_bad.passed)
        self.assertFalse(res_bad.focus_mag_clean_hdmi_isolated)
        self.assertGreater(res_bad.hdmi_magnifier_baked_pixels, 0)
        self.assertTrue(
            any(P275_GC_ERR_FOCUS_MAG_4X_CLEAN_HDMI_OR_RAW_LOCKOUT in e for e in res_bad.errors)
        )

    def test_29_group_c_focus_magnifier_locked_out_during_hdmi_raw(self) -> None:
        res_raw_idle = evaluate_p275_check_group_c_focus_mag_videolight_and_hdmi_res(
            hdmi_raw_output=True, focus_magnifier_active=False
        )
        self.assertTrue(res_raw_idle.passed, res_raw_idle.errors)

        res_raw_active = evaluate_p275_check_group_c_focus_mag_videolight_and_hdmi_res(
            hdmi_raw_output=True, focus_magnifier_active=True
        )
        self.assertFalse(res_raw_active.passed)
        self.assertTrue(
            any(P275_GC_ERR_FOCUS_MAG_4X_CLEAN_HDMI_OR_RAW_LOCKOUT in e for e in res_raw_active.errors)
        )

    def test_30_group_c_peaking_display_levels_and_colors(self) -> None:
        for lvl, col in (("HIGH", "RED"), ("MID", "YELLOW"), ("LOW", "BLUE"), ("HIGH", "WHITE")):
            res = evaluate_p275_check_group_c_focus_mag_videolight_and_hdmi_res(
                peaking_display="ON", peaking_level=lvl, peaking_color=col
            )
            self.assertTrue(res.passed, res.errors)

        res_bad = evaluate_p275_check_group_c_focus_mag_videolight_and_hdmi_res(
            peaking_display="ON", peaking_color="GREEN"
        )
        self.assertFalse(res_bad.passed)
        self.assertTrue(
            any(P275_GC_ERR_PEAKING_OR_AF_ILLUMINATOR_MOVIE_AFC_LOCKOUT in e for e in res_bad.errors)
        )

    def test_31_group_c_af_illuminator_still_only_movie_and_afc_lockout(self) -> None:
        res_still_afs = evaluate_p275_check_group_c_focus_mag_videolight_and_hdmi_res(
            shoot_mode="PHOTO", focus_mode="AF_S", af_illuminator="AUTO"
        )
        self.assertTrue(res_still_afs.passed)

        for sh, fc in (("MOVIE", "MF"), ("S_AND_Q", "AF_S"), ("PHOTO", "AF_C")):
            res_bad = evaluate_p275_check_group_c_focus_mag_videolight_and_hdmi_res(
                shoot_mode=sh, focus_mode=fc, expect_af_illuminator_fires_in_movie_or_afc=True
            )
            self.assertFalse(res_bad.passed)
            self.assertFalse(res_bad.af_illuminator_still_only_verified)
            self.assertTrue(
                any(
                    P275_GC_ERR_PEAKING_OR_AF_ILLUMINATOR_MOVIE_AFC_LOCKOUT in e
                    for e in res_bad.errors
                )
            )

    def test_32_group_c_area_date_time_4_subitems_and_zero_rf_creators_app_block(self) -> None:
        res_ok = evaluate_p275_check_group_c_focus_mag_videolight_and_hdmi_res()
        self.assertTrue(res_ok.passed)
        self.assertEqual(res_ok.area_date_time_label_verified, P275_AREA_DATE_TIME_EXACT_LABEL)
        self.assertEqual(res_ok.area_date_time_four_subitems, P275_AREA_DATE_TIME_FOUR_SUBITEMS)
        self.assertTrue(res_ok.zero_rf_time_isolated)
        self.assertEqual(res_ok.passive_tx_bytes_emitted, 0)

        for bad_kwargs in (
            {"creators_app_location_linkage": "ON"},
            {"airplane_mode": "OFF"},
            {"bluetooth_function": "ON"},
            {"expect_creators_app_auto_time_sync": True},
            {"simulated_passive_tx_bytes": 16},
            {"area_date_time_subitems": P275_AREA_DATE_TIME_FOUR_SUBITEMS[:-1]},
        ):
            res_bad = evaluate_p275_check_group_c_focus_mag_videolight_and_hdmi_res(**bad_kwargs)
            self.assertFalse(res_bad.passed, f"Expected failure for {bad_kwargs}")
            self.assertTrue(
                any(
                    P275_GC_ERR_AREA_DATE_TIME_OR_ZERO_RF_CREATORS_APP_SYNC in e
                    for e in res_bad.errors
                )
            )

    def test_33_group_c_video_light_mode_four_options_validated(self) -> None:
        self.assertEqual(len(P275_VALID_VIDEO_LIGHT_MODES), 4)
        for mode in P275_VALID_VIDEO_LIGHT_MODES:
            res = evaluate_p275_check_group_c_focus_mag_videolight_and_hdmi_res(
                video_light_mode=mode, mi_shoe_5v_current_ma=450
            )
            self.assertTrue(res.passed, f"Failed for {mode}: {res.errors}")

        res_bad = evaluate_p275_check_group_c_focus_mag_videolight_and_hdmi_res(
            video_light_mode="STROBE_ONLY"
        )
        self.assertFalse(res_bad.passed)

    def test_34_group_c_mi_shoe_5v_900ma_overcurrent_guard(self) -> None:
        res_900 = evaluate_p275_check_group_c_focus_mag_videolight_and_hdmi_res(
            mi_shoe_5v_current_ma=P275_MI_SHOE_5V_MAX_CURRENT_MA
        )
        self.assertTrue(res_900.passed)
        self.assertTrue(res_900.mi_shoe_5v_budget_ok)

        res_901 = evaluate_p275_check_group_c_focus_mag_videolight_and_hdmi_res(
            mi_shoe_5v_current_ma=P275_MI_SHOE_5V_MAX_CURRENT_MA + 1
        )
        self.assertFalse(res_901.passed)
        self.assertFalse(res_901.mi_shoe_5v_budget_ok)
        self.assertTrue(
            any(
                P275_GC_ERR_VIDEO_LIGHT_MODE_OR_MI_SHOE_5V_900MA_OVERCURRENT in e
                for e in res_901.errors
            )
        )

    def test_35_group_c_hdmi_resolution_log_1080p_downshift_enforced(self) -> None:
        # Log + internal rec: Auto / 1080p / 1080i pass, 2160p fails
        for ok_res in ("AUTO", "1080P", "1080I"):
            res = evaluate_p275_check_group_c_focus_mag_videolight_and_hdmi_res(
                log_shooting_mode="CINE_EI",
                rec_media_dur_hdmi_output="ON",
                hdmi_resolution=ok_res,
            )
            self.assertTrue(res.passed, res.errors)
            self.assertEqual(res.effective_hdmi_output_class, "1080P_LOG_DOWNSHIFT")

        res_2160 = evaluate_p275_check_group_c_focus_mag_videolight_and_hdmi_res(
            log_shooting_mode="CINE_EI",
            rec_media_dur_hdmi_output="ON",
            hdmi_resolution="2160P",
        )
        self.assertFalse(res_2160.passed)
        self.assertTrue(
            any(P275_GC_ERR_HDMI_RESOLUTION_LOG_1080P_OR_4K_DOWNSHIFT in e for e in res_2160.errors)
        )

    def test_36_group_c_hdmi_resolution_2160p_allowed_with_off_hdmi_only_non_raw(self) -> None:
        res = evaluate_p275_check_group_c_focus_mag_videolight_and_hdmi_res(
            log_shooting_mode="CINE_EI",
            rec_media_dur_hdmi_output="Off(HDMI Only)",
            hdmi_resolution="2160P",
            hdmi_raw_output=False,
        )
        self.assertTrue(res.passed, res.errors)
        self.assertEqual(res.effective_hdmi_output_class, "4K_2160P_COMPATIBLE")

    def test_37_group_c_hdmi_raw_rejects_2160p_forcing(self) -> None:
        res = evaluate_p275_check_group_c_focus_mag_videolight_and_hdmi_res(
            hdmi_raw_output=True,
            hdmi_resolution="2160P",
        )
        self.assertFalse(res.passed)
        self.assertEqual(res.effective_hdmi_output_class, "RAW_4264X2408_16BIT")

    def test_38_group_c_expect_4k_hdmi_log_with_internal_rec_blocked(self) -> None:
        res = evaluate_p275_check_group_c_focus_mag_videolight_and_hdmi_res(
            log_shooting_mode="FLEXIBLE_ISO",
            rec_media_dur_hdmi_output="ON",
            expect_4k_hdmi_log_with_internal_rec=True,
        )
        self.assertFalse(res.passed)

    def test_39_group_c_focus_mag_time_options_and_setup_reset_survival(self) -> None:
        for t in ("NO_LIMIT", "2_SEC", "5_SEC"):
            res = evaluate_p275_check_group_c_focus_mag_videolight_and_hdmi_res(
                focus_magnif_time=t, reset_action="CAMERA_SETTINGS_RESET"
            )
            self.assertTrue(res.passed, res.errors)
            self.assertTrue(res.setup_items_survive_camera_reset)

        res_bad = evaluate_p275_check_group_c_focus_mag_videolight_and_hdmi_res(
            claimed_setup_c_items_reset_on_camera_reset=True
        )
        self.assertFalse(res_bad.passed)

    def test_40_group_c_mi_shoe_negative_current_or_overcurrent_flag_blocked(self) -> None:
        res_neg = evaluate_p275_check_group_c_focus_mag_videolight_and_hdmi_res(
            mi_shoe_5v_current_ma=-1
        )
        self.assertFalse(res_neg.passed)
        res_flag = evaluate_p275_check_group_c_focus_mag_videolight_and_hdmi_res(
            expect_mi_shoe_5v_overcurrent_allowed=True
        )
        self.assertFalse(res_flag.passed)

    # --- Group D: Wave 46 Power Save Monitor Split, BK_LANG, Volume/4ch, Delete Guard & Tier-0 (17 tests) ---

    def test_41_group_d_power_setting_option_2item_vs_appfw_4mode_reality_split(self) -> None:
        gd, tier0_err = evaluate_p275_check_group_d_power_bklang_volume_delete_and_tier0(
            simulate_bench_dry_run=True
        )
        self.assertTrue(gd.passed, gd.errors)
        self.assertEqual(tier0_err, ())
        self.assertEqual(gd.power_setting_exposed_two_items, P275_FX3_ILC2210_POWER_SETTING_TWO_ITEMS)
        self.assertFalse(gd.power_save_by_monitor_exposed_in_fx3_ui)
        self.assertEqual(
            gd.appfw_monitor_power_linkage_four_modes, P275_APPFW_MONITOR_POWER_LINKAGE_FOUR_MODES
        )
        self.assertEqual(len(P275_APPFW_MONITOR_POWER_LINKAGE_RESIDS), 4)

        # Reject claiming [Power Save by Monitor] is exposed in stock FX3 UI
        gd_ui, _ = evaluate_p275_check_group_d_power_bklang_volume_delete_and_tier0(
            power_save_by_monitor_exposed_in_fx3_ui=True, simulate_bench_dry_run=True
        )
        self.assertFalse(gd_ui.passed)
        self.assertTrue(
            any(P275_GD_ERR_POWER_SETTING_OPTION_REALITY_SPLIT_OR_9COND in e for e in gd_ui.errors)
        )

        # Reject headless unsafe close-sleep linkage modes
        for unsafe_mode in ("CLOSE_POWER_SAVE", "BOTH_LINKED"):
            gd_close, _ = evaluate_p275_check_group_d_power_bklang_volume_delete_and_tier0(
                headless_monitor_power_linkage_mode=unsafe_mode, simulate_bench_dry_run=True
            )
            self.assertFalse(gd_close.passed)

    def test_42_group_d_headless_safe_monitor_power_linkage_modes_accepted(self) -> None:
        for safe_mode in P275_HEADLESS_SAFE_MONITOR_POWER_LINK_MODES:
            gd, _ = evaluate_p275_check_group_d_power_bklang_volume_delete_and_tier0(
                headless_monitor_power_linkage_mode=safe_mode, simulate_bench_dry_run=True
            )
            self.assertTrue(gd.passed, f"Failed for {safe_mode}: {gd.errors}")

    def test_43_group_d_airgapped_battery_power_save_time_vs_9_deactivations(self) -> None:
        for safe_t in P275_SAFE_AIRGAPPED_BATTERY_POWER_SAVE_TIMES:
            gd, _ = evaluate_p275_check_group_d_power_bklang_volume_delete_and_tier0(
                power_save_start_time=safe_t, simulate_bench_dry_run=True
            )
            self.assertTrue(gd.passed, gd.errors)

        # Short timer on air-gapped battery with 0 deactivation conditions fails
        gd_short, _ = evaluate_p275_check_group_d_power_bklang_volume_delete_and_tier0(
            power_save_start_time="10_SEC",
            power_save_deactivation_conditions=(),
            simulate_bench_dry_run=True,
        )
        self.assertFalse(gd_short.passed)

        # Deactivated when one of the 9 conditions is active (e.g., MOVIE_RECORDING)
        self.assertEqual(len(P275_POWER_SAVE_NINE_DEACTIVATION_CONDITIONS), 9)
        gd_deact, _ = evaluate_p275_check_group_d_power_bklang_volume_delete_and_tier0(
            power_save_start_time="10_SEC",
            power_save_deactivation_conditions=("MOVIE_RECORDING",),
            simulate_bench_dry_run=True,
        )
        self.assertTrue(gd_deact.passed, gd_deact.errors)

        # Invalid deactivation condition fails
        gd_bogus, _ = evaluate_p275_check_group_d_power_bklang_volume_delete_and_tier0(
            power_save_deactivation_conditions=("BOGUS_CONDITION",),
            simulate_bench_dry_run=True,
        )
        self.assertFalse(gd_bogus.passed)

    def test_44_group_d_bklang_0x02cf019c_34_vs_29_and_4_lang_codes(self) -> None:
        self.assertEqual(P275_FX3_LANGUAGE_COUNT, 34)
        self.assertEqual(P275_FX6_LANGUAGE_COUNT, 29)
        self.assertEqual(
            P275_BKLANG_FOUR_LANG_CODES,
            {"en": 0x00, "japanese": 0x01, "tchinese": 0x18, "schinese": 0x19},
        )
        for lang, code in P275_BKLANG_FOUR_LANG_CODES.items():
            gd, _ = evaluate_p275_check_group_d_power_bklang_volume_delete_and_tier0(
                selected_lang=lang, simulate_bench_dry_run=True
            )
            self.assertTrue(gd.passed, gd.errors)
            self.assertEqual(gd.selected_bklang_code_hex, f"0x{code:02x}")

        for bad_kwargs in (
            {"bklang_register_hex": "0x00000000"},
            {"fx3_language_count": 29},
            {"fx6_language_count": 34},
            {"selected_lang": "klingon"},
        ):
            gd_bad, _ = evaluate_p275_check_group_d_power_bklang_volume_delete_and_tier0(
                simulate_bench_dry_run=True, **bad_kwargs
            )
            self.assertFalse(gd_bad.passed)
            self.assertTrue(
                any(P275_GD_ERR_BKLANG_34_VS_29_OR_SETUP_RESET_PERSISTENCE in e for e in gd_bad.errors)
            )

    def test_45_group_d_bklang_survives_camera_settings_and_network_resets(self) -> None:
        for rst in ("CAMERA_SETTINGS_RESET", "RESET_NETWORK_SET"):
            gd, _ = evaluate_p275_check_group_d_power_bklang_volume_delete_and_tier0(
                reset_action=rst, selected_lang="schinese", simulate_bench_dry_run=True
            )
            self.assertTrue(gd.passed, gd.errors)
            self.assertTrue(gd.bklang_survives_camera_and_network_reset)

        gd_bad, _ = evaluate_p275_check_group_d_power_bklang_volume_delete_and_tier0(
            reset_action="CAMERA_SETTINGS_RESET",
            claimed_bklang_cleared_by_camera_or_network_reset=True,
            simulate_bench_dry_run=True,
        )
        self.assertFalse(gd_bad.passed)

    def test_46_group_d_volume_settings_0_to_15_and_xlr_h1_feedback_guard(self) -> None:
        gd_default, _ = evaluate_p275_check_group_d_power_bklang_volume_delete_and_tier0(
            volume_settings=P275_VOLUME_SETTINGS_DEFAULT,
            xlr_h1_attached=True,
            simulate_bench_dry_run=True,
        )
        self.assertTrue(gd_default.passed)
        self.assertEqual(gd_default.warnings, ())

        # Warning between 8 and 10 when XLR-H1 is attached
        gd_warn, _ = evaluate_p275_check_group_d_power_bklang_volume_delete_and_tier0(
            volume_settings=9, xlr_h1_attached=True, simulate_bench_dry_run=True
        )
        self.assertTrue(gd_warn.passed)
        self.assertTrue(gd_warn.warnings)

        # > 10 with XLR-H1 attached fails feedback guard
        gd_fb, _ = evaluate_p275_check_group_d_power_bklang_volume_delete_and_tier0(
            volume_settings=12, xlr_h1_attached=True, simulate_bench_dry_run=True
        )
        self.assertFalse(gd_fb.passed)
        self.assertTrue(
            any(P275_GD_ERR_VOLUME_OR_4CH_MONITORING_5ROUTE_OR_FEEDBACK in e for e in gd_fb.errors)
        )

        # Out-of-range volume rejected
        for out_v in (P275_VOLUME_SETTINGS_MIN - 1, P275_VOLUME_SETTINGS_MAX + 1):
            gd_oob, _ = evaluate_p275_check_group_d_power_bklang_volume_delete_and_tier0(
                volume_settings=out_v, simulate_bench_dry_run=True
            )
            self.assertFalse(gd_oob.passed)

    def test_47_group_d_4ch_audio_monitoring_five_routes_and_35mm_2ch_limit(self) -> None:
        self.assertEqual(len(P275_4CH_AUDIO_MONITORING_FIVE_ROUTES), 5)
        for route in ("CH1/CH2", "CH3/CH4", "CH1+3/CH2+4", "CH1/CH1", "CH2/CH2"):
            gd, _ = evaluate_p275_check_group_d_power_bklang_volume_delete_and_tier0(
                four_ch_audio_monitoring=route, simulate_bench_dry_run=True
            )
            self.assertTrue(gd.passed, gd.errors)

        gd_bad_hp, _ = evaluate_p275_check_group_d_power_bklang_volume_delete_and_tier0(
            expect_4ch_discrete_over_35mm_headphone=True, simulate_bench_dry_run=True
        )
        self.assertFalse(gd_bad_hp.passed)
        self.assertFalse(gd_bad_hp.headphone_35mm_2ch_only_verified)

        gd_bad_route, _ = evaluate_p275_check_group_d_power_bklang_volume_delete_and_tier0(
            four_ch_audio_monitoring="CH1_CH2_CH3_CH4_DISCRETE", simulate_bench_dry_run=True
        )
        self.assertFalse(gd_bad_route.passed)

    def test_48_group_d_delete_confirm_cancel_first_and_slot1_vault_delete_format_blocked(self) -> None:
        gd_ok, _ = evaluate_p275_check_group_d_power_bklang_volume_delete_and_tier0(
            delete_confirm='"Cancel" first', simulate_bench_dry_run=True
        )
        self.assertTrue(gd_ok.passed, gd_ok.errors)
        self.assertEqual(gd_ok.delete_confirm, "CANCEL_FIRST")
        self.assertTrue(gd_ok.slot1_format_hard_locked)

        for bad_kwargs in (
            {"delete_confirm": "DELETE_FIRST"},
            {"slot1_delete_requested": True},
            {"slot1_format_requested": True},
            {"expect_slot1_vault_delete_or_format_allowed": True},
        ):
            gd_bad, _ = evaluate_p275_check_group_d_power_bklang_volume_delete_and_tier0(
                simulate_bench_dry_run=True, **bad_kwargs
            )
            self.assertFalse(gd_bad.passed, f"Expected block for {bad_kwargs}")
            self.assertTrue(
                any(
                    P275_GD_ERR_DELETE_CONFIRM_OR_SLOT1_VAULT_DELETE_FORMAT_BLOCKED in e
                    for e in gd_bad.errors
                )
            )

    def test_49_group_d_h0_h3_16_surface_drift_blocked(self) -> None:
        gd, _ = evaluate_p275_check_group_d_power_bklang_volume_delete_and_tier0(
            simulated_h0_h3_drifted_surfaces=1, simulate_bench_dry_run=True
        )
        self.assertFalse(gd.passed)
        self.assertEqual(gd.h0_h3_surface_count, 16)
        self.assertEqual(gd.h0_equals_h3_count, 15)
        self.assertTrue(any(P275_GD_ERR_H0_H3_IMMUTABILITY_DRIFT in e for e in gd.errors))

    def test_50_group_d_offline_no_receipts_fails_closed_cleanly(self) -> None:
        gd, tier0_err = evaluate_p275_check_group_d_power_bklang_volume_delete_and_tier0(
            simulate_bench_dry_run=False
        )
        self.assertTrue(gd.passed)
        self.assertFalse(gd.tier0_receipt_present)
        self.assertFalse(gd.tier0_receipt_verified)
        self.assertTrue(
            any(P275_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID in e for e in tier0_err)
        )

    def test_51_group_d_valid_dual_media_receipts_verified_distinct_st_dev(self) -> None:
        raw_a, raw_b, h0 = build_simulated_phase275_tier0_receipts()
        gd, tier0_err = evaluate_p275_check_group_d_power_bklang_volume_delete_and_tier0(
            receipt_a_bytes=raw_a,
            receipt_b_bytes=raw_b,
            st_dev_a_override=1001,
            st_dev_b_override=2002,
            body_serial=DEFAULT_TARGET_BODY_SERIAL,
            emmc_cid=DEFAULT_TARGET_EMMC_CID,
            h0_baselines_a=h0,
            h0_baselines_b=h0,
        )
        self.assertTrue(gd.passed)
        self.assertEqual(tier0_err, ())
        self.assertTrue(gd.tier0_receipt_verified)
        self.assertTrue(gd.distinct_physical_media_verified)

    def test_52_group_d_same_st_dev_rejected(self) -> None:
        raw_a, raw_b, h0 = build_simulated_phase275_tier0_receipts()
        gd, tier0_err = evaluate_p275_check_group_d_power_bklang_volume_delete_and_tier0(
            receipt_a_bytes=raw_a,
            receipt_b_bytes=raw_b,
            st_dev_a_override=42,
            st_dev_b_override=42,
            body_serial=DEFAULT_TARGET_BODY_SERIAL,
            emmc_cid=DEFAULT_TARGET_EMMC_CID,
            h0_baselines_a=h0,
            h0_baselines_b=h0,
        )
        self.assertFalse(gd.tier0_receipt_verified)
        self.assertFalse(gd.distinct_physical_media_verified)
        self.assertTrue(any("st_dev_a == st_dev_b" in e for e in tier0_err))

    def test_53_group_d_corrupt_crc_or_mismatched_receipt_bytes_rejected(self) -> None:
        raw_a, raw_b, h0 = build_simulated_phase275_tier0_receipts()
        corrupt = bytearray(raw_b)
        corrupt[-1] ^= 0xFF
        gd_mismatch, tier0_err = evaluate_p275_check_group_d_power_bklang_volume_delete_and_tier0(
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
        self.assertTrue(tier0_err)

        # Identical but bad CRC32 also fails
        gd_crc, tier0_crc = evaluate_p275_check_group_d_power_bklang_volume_delete_and_tier0(
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
        self.assertTrue(any("CRC32" in e for e in tier0_crc))

    def test_54_group_d_trivial_serial_cid_or_missing_h0_rejected(self) -> None:
        raw_a, raw_b, h0 = build_simulated_phase275_tier0_receipts()
        gd_ser, _ = evaluate_p275_check_group_d_power_bklang_volume_delete_and_tier0(
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

        gd_h0, _ = evaluate_p275_check_group_d_power_bklang_volume_delete_and_tier0(
            receipt_a_bytes=raw_a,
            receipt_b_bytes=raw_b,
            st_dev_a_override=1,
            st_dev_b_override=2,
            body_serial=DEFAULT_TARGET_BODY_SERIAL,
            emmc_cid=DEFAULT_TARGET_EMMC_CID,
            h0_baselines_a=None,
            h0_baselines_b=None,
        )
        self.assertFalse(gd_h0.tier0_receipt_verified)

    def test_55_group_d_h0_key_mismatch_or_trivial_digest_rejected(self) -> None:
        raw_a, raw_b, h0 = build_simulated_phase275_tier0_receipts()
        bad_h0 = dict(h0)
        first_key = next(iter(bad_h0))
        bad_h0[first_key] = "0" * 64
        gd, tier0_err = evaluate_p275_check_group_d_power_bklang_volume_delete_and_tier0(
            receipt_a_bytes=raw_a,
            receipt_b_bytes=raw_b,
            st_dev_a_override=1,
            st_dev_b_override=2,
            body_serial=DEFAULT_TARGET_BODY_SERIAL,
            emmc_cid=DEFAULT_TARGET_EMMC_CID,
            h0_baselines_a=h0,
            h0_baselines_b=bad_h0,
        )
        self.assertFalse(gd.tier0_receipt_verified)
        self.assertTrue(any("invalid/mismatched H0" in e for e in tier0_err))

    def test_56_group_d_missing_receipt_path_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            gd, tier0_err = evaluate_p275_check_group_d_power_bklang_volume_delete_and_tier0(
                receipt_a_path=Path(tmp) / "missing_a.bin",
                receipt_b_path=Path(tmp) / "missing_b.bin",
            )
            self.assertFalse(gd.tier0_receipt_verified)
            self.assertTrue(any("read failed" in e for e in tier0_err))

    def test_57_group_d_audio_delete_and_power_camera_reset_persistence_failures(self) -> None:
        for bad_kwargs in (
            {"claimed_power_setting_reset_on_camera_reset": True},
            {"claimed_audio_setup_reset_on_camera_reset": True},
            {"claimed_delete_confirm_reset_on_camera_reset": True},
        ):
            gd, _ = evaluate_p275_check_group_d_power_bklang_volume_delete_and_tier0(
                simulate_bench_dry_run=True, **bad_kwargs
            )
            self.assertFalse(gd.passed, f"Expected failure for {bad_kwargs}")

    # --- Orchestrator, Tamper Verification, Markdown & CLI / Subprocess (11 tests) ---

    def test_58_orchestrator_offline_default_fail_closed_both_modes(self) -> None:
        for clean in (None, True):
            rep = evaluate_realhw_file_settings_gamma_assist_focus_mag_and_videolight_readiness(
                force_clean_room=clean,
                simulate_bench_dry_run=False,
            )
            self.assertEqual(rep.overall_status, P275_OVERALL_READY_OFFLINE_AWAITING_BENCH_RECEIPTS)
            self.assertEqual(rep.go_no_go, GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT)
            self.assertTrue(rep.all_4_check_groups_passed)
            self.assertFalse(rep.tier0_receipt_verified)
            self.assertFalse(rep.overall_ready_for_hardware_attach)
            self.assertFalse(rep.hardware_live_attachment_authorized)
            self.assertFalse(rep.persistent_emmc_writes_authorized)
            self.assertEqual(rep.usb_packets_transmitted, 0)
            self.assertEqual(rep.raw_firmware_bytes_leaked, 0)
            self.assertEqual(rep.passive_tx_bytes_emitted, 0)
            self.assertEqual(rep.h0_equals_h3_count, 16)
            self.assertTrue(verify_phase275_report(rep.to_dict()).valid)

    def test_59_orchestrator_simulate_bench_dry_run_passes_4of4_16of16_both_modes(self) -> None:
        for clean in (None, True):
            rep = evaluate_realhw_file_settings_gamma_assist_focus_mag_and_videolight_readiness(
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
            self.assertTrue(verify_phase275_report(rep.to_dict()).valid)

    def test_60_orchestrator_distinct_device_receipts_verify_readonly_preflight(self) -> None:
        raw_a, raw_b, h0 = build_simulated_phase275_tier0_receipts()
        rep = evaluate_realhw_file_settings_gamma_assist_focus_mag_and_videolight_readiness(
            force_clean_room=True,
            simulate_bench_dry_run=False,
            receipt_a_bytes=raw_a,
            receipt_b_bytes=raw_b,
            st_dev_a_override=101,
            st_dev_b_override=202,
            body_serial=DEFAULT_TARGET_BODY_SERIAL,
            emmc_cid=DEFAULT_TARGET_EMMC_CID,
            h0_baselines_a=h0,
            h0_baselines_b=h0,
        )
        self.assertEqual(
            rep.go_no_go, P275_GO_NO_GO_FILE_SETTINGS_GAMMA_ASSIST_FOCUS_MAG_VIDEOLIGHT_VERIFIED
        )
        self.assertEqual(
            rep.overall_status,
            P275_GO_NO_GO_FILE_SETTINGS_GAMMA_ASSIST_FOCUS_MAG_VIDEOLIGHT_VERIFIED,
        )
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.hardware_live_attachment_authorized)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertTrue(verify_phase275_report(rep.to_dict()).valid)

    def test_61_orchestrator_check_failure_populates_remediations_and_blocks(self) -> None:
        rep = evaluate_realhw_file_settings_gamma_assist_focus_mag_and_videolight_readiness(
            force_clean_room=True,
            simulate_bench_dry_run=True,
            log_shooting_mode="CINE_EI",
            gamma_display_assist="ON",
        )
        self.assertEqual(
            rep.go_no_go,
            P275_GO_NO_GO_BLOCKED_FILE_SETTINGS_GAMMA_ASSIST_FOCUS_MAG_VIDEOLIGHT_FAILURE,
        )
        self.assertFalse(rep.all_4_check_groups_passed)
        self.assertEqual(rep.check_groups_passed, 3)
        self.assertTrue(rep.remediation_actions)
        self.assertTrue(verify_phase275_report(rep.to_dict()).valid)

    def test_62_verify_phase275_report_catches_locks_passive_tx_spoof_and_sha_tampering(self) -> None:
        base = evaluate_realhw_file_settings_gamma_assist_focus_mag_and_videolight_readiness(
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
            "power_save_by_monitor_exposed_in_fx3_ui",
        ):
            mutated = dict(base)
            mutated[lock_key] = True
            self.assertFalse(verify_phase275_report(mutated).valid, f"Failed to catch {lock_key}")

        for zero_key in (
            "usb_packets_transmitted",
            "physical_usb_packets_emitted",
            "raw_firmware_bytes_leaked",
            "passive_tx_bytes_emitted",
        ):
            mutated = dict(base)
            mutated[zero_key] = 1
            self.assertFalse(verify_phase275_report(mutated).valid, f"Failed to catch {zero_key}")

        # Simulated dry-run spoofing verified verdict must fail
        escalated = dict(base)
        escalated["go_no_go"] = (
            P275_GO_NO_GO_FILE_SETTINGS_GAMMA_ASSIST_FOCUS_MAG_VIDEOLIGHT_VERIFIED
        )
        self.assertFalse(verify_phase275_report(escalated).valid)

        # Tampered canonical SHA-256 must fail
        bad_sha = dict(base)
        bad_sha["report_sha256"] = "a" * 64
        self.assertFalse(verify_phase275_report(bad_sha).valid)

    def test_63_deterministic_sha256_and_markdown_rendering(self) -> None:
        r1 = evaluate_realhw_file_settings_gamma_assist_focus_mag_and_videolight_readiness(
            force_clean_room=True, simulate_bench_dry_run=True
        )
        r2 = evaluate_realhw_file_settings_gamma_assist_focus_mag_and_videolight_readiness(
            force_clean_room=True, simulate_bench_dry_run=True
        )
        self.assertEqual(r1.report_sha256, r2.report_sha256)
        md = render_phase275_markdown(r1)
        for token in (
            PHASE_275_SCHEMA,
            P275_CHECK_GROUP_A_ID,
            P275_CHECK_GROUP_B_ID,
            P275_CHECK_GROUP_C_ID,
            P275_CHECK_GROUP_D_ID,
            r1.report_sha256,
        ):
            self.assertIn(token, md)

    def test_64_cli_offline_default_fails_closed_exit_2_ready_offline_awaiting_receipts(self) -> None:
        buf = io.StringIO()
        with mock.patch("sys.stdout", buf):
            rc = cli_main(
                [
                    "preflight-file-settings-gamma-assist-focus-mag-and-videolight",
                    "--force-clean-room",
                    "--json",
                ]
            )
        self.assertEqual(rc, 2)
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["schema"], PHASE_275_SCHEMA)
        self.assertEqual(
            payload["overall_status"], P275_OVERALL_READY_OFFLINE_AWAITING_BENCH_RECEIPTS
        )
        self.assertEqual(payload["go_no_go"], GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT)
        self.assertFalse(payload["overall_ready_for_hardware_attach"])
        self.assertFalse(payload["hardware_live_attachment_authorized"])
        self.assertFalse(payload["persistent_emmc_writes_authorized"])

    def test_65_cli_simulate_bench_dry_run_emits_deterministic_json_and_markdown_exit_0(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            json_path = Path(tmp) / "p275.json"
            md_path = Path(tmp) / "p275.md"
            buf = io.StringIO()
            with mock.patch("sys.stdout", buf):
                rc = cli_main(
                    [
                        "preflight-file-settings-gamma-assist-focus-mag-and-videolight",
                        "--simulate-bench-dry-run",
                        "--output",
                        str(json_path),
                        "--markdown-out",
                        str(md_path),
                    ]
                )
            self.assertEqual(rc, 0)
            out_line = buf.getvalue()
            self.assertIn("OVERALL=DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH", out_line)
            self.assertIn("go_no_go=DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH", out_line)
            loaded = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertTrue(verify_phase275_report(loaded).valid)
            md_text = md_path.read_text(encoding="utf-8")
            self.assertIn(PHASE_275_SCHEMA, md_text)

    def test_66_cli_blocks_violations_across_all_4_groups_exit_2(self) -> None:
        for extra_flags in (
            ["--still-file-prefix", "_SC"],
            ["--log-shooting-mode", "CINE_EI", "--gamma-display-assist", "ON"],
            ["--mi-shoe-5v-current-ma", "950"],
            ["--slot1-format-requested"],
        ):
            buf = io.StringIO()
            with mock.patch("sys.stdout", buf):
                rc = cli_main(
                    [
                        "preflight-file-settings-gamma-assist-focus-mag-and-videolight",
                        "--force-clean-room",
                        "--simulate-bench-dry-run",
                        "--json",
                        *extra_flags,
                    ]
                )
            self.assertEqual(rc, 2)
            payload = json.loads(buf.getvalue())
            self.assertEqual(
                payload["go_no_go"],
                P275_GO_NO_GO_BLOCKED_FILE_SETTINGS_GAMMA_ASSIST_FOCUS_MAG_VIDEOLIGHT_FAILURE,
            )

    def test_67_cli_blocks_same_filesystem_st_dev_receipt_files_exit_2(self) -> None:
        raw_a, raw_b, _ = build_simulated_phase275_tier0_receipts()
        with tempfile.TemporaryDirectory() as tmp:
            pa = Path(tmp) / "rcpt_a.bin"
            pb = Path(tmp) / "rcpt_b.bin"
            pa.write_bytes(raw_a)
            pb.write_bytes(raw_b)
            buf = io.StringIO()
            with mock.patch("sys.stdout", buf):
                rc = cli_main(
                    [
                        "preflight-file-settings-gamma-assist-focus-mag-and-videolight",
                        "--force-clean-room",
                        "--receipt-a",
                        str(pa),
                        "--receipt-b",
                        str(pb),
                        "--body-serial",
                        DEFAULT_TARGET_BODY_SERIAL,
                        "--emmc-cid",
                        DEFAULT_TARGET_EMMC_CID,
                        "--json",
                    ]
                )
            self.assertEqual(rc, 2)
            payload = json.loads(buf.getvalue())
            self.assertEqual(
                payload["go_no_go"],
                P275_GO_NO_GO_BLOCKED_FILE_SETTINGS_GAMMA_ASSIST_FOCUS_MAG_VIDEOLIGHT_FAILURE,
            )
            self.assertTrue(
                any(
                    P275_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID in e
                    for e in payload["errors"]
                )
            )

    def test_68_subprocess_cli_clean_room_dry_run_via_sys_executable(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONPATH"] = os.pathsep.join(
            [
                str(REPO_ROOT / "outputs" / "fx6-on-fx3-closure"),
                str(REPO_ROOT / "outputs" / "fx3-safety"),
                str(REPO_ROOT / "outputs" / "fx3-recovery-adapter"),
                str(REPO_ROOT / "outputs" / "fx3-firmware-lab"),
                str(REPO_ROOT / "outputs" / "fx3-vm"),
            ]
        )
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "fx6_closure",
                "preflight-file-settings-gamma-assist-focus-mag-and-videolight",
                "--force-clean-room",
                "--simulate-bench-dry-run",
                "--json",
            ],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["schema"], PHASE_275_SCHEMA)
        self.assertEqual(payload["verification_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(verify_phase275_report(payload).valid)


if __name__ == "__main__":
    unittest.main()
