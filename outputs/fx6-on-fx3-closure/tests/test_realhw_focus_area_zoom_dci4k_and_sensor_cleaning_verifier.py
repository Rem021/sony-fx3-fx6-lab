"""Dual-mode unit tests (76 cases) for Phase 291 (`preflight-focus-area-zoom-dci4k-and-sensor-cleaning`):
10th Real-Hardware Physical Bench & Pre-Shoot Readiness Verifier across Waves 50-52 check groups (`A..D`).

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
    build_default_h0_baselines,
)
from fx6_closure.realhw_sd_stageb_bundle_and_uninstaller import (  # noqa: E402
    DEFAULT_TARGET_BODY_SERIAL,
    DEFAULT_TARGET_EMMC_CID,
)
from fx6_closure.realhw_focus_area_zoom_dci4k_and_sensor_cleaning_verifier import (  # noqa: E402
    P291_AF_AREA_REGISTRATION_BKID,
    P291_AF_AREA_REGISTRATION_LABEL,
    P291_AF_AREA_REGISTRATION_RESID16_HEX,
    P291_ASPECT_RATIO_RESID16_HEX,
    P291_CHECK_GROUP_A_ID,
    P291_CHECK_GROUP_B_ID,
    P291_CHECK_GROUP_C_ID,
    P291_CHECK_GROUP_D_ID,
    P291_CINE_EI_BASE_ISOS,
    P291_CIRC_FOCUS_POINT_RESID16_HEX,
    P291_CRCOMMANDID_SENSOR_CLEANING,
    P291_DCI_4K_FRAME_RATES,
    P291_DCI_4K_REBOOT_24P_RESID16_HEX,
    P291_DCI_4K_SQ_MAX_FPS,
    P291_DCI_4K_WIDTH_HEIGHT,
    P291_DEFAULT_FX3_SETTING_CARD_PATH,
    P291_DORMANT_IMAGE_INDEX_MODES,
    P291_DORMANT_VIEW_MODES,
    P291_ENLARGE_IMAGE_RESID16_HEX,
    P291_EV_COMP_MOVIE_ABS_MAX,
    P291_EV_COMP_STILL_ABS_MAX,
    P291_EXPOSURE_COMP_RESID16_HEX,
    P291_FLASH_MODE_RESID16_HEX,
    P291_FOCUS_AREA_BKID,
    P291_FOCUS_AREA_COLOR_RESID16_HEX,
    P291_FOCUS_AREA_FOURTEEN_MODES,
    P291_FOCUS_AREA_LIMIT_RESID16_HEX,
    P291_FOCUS_AREA_NON_TRACKING_SEVEN,
    P291_FOCUS_AREA_RESID16_HEX,
    P291_FOCUS_AREA_TRACKING_SEVEN,
    P291_FOCUS_MODE_MOVIE_RESID16_HEX,
    P291_FX3_SETTING_CARD_PATH_RE,
    P291_GA_ERR_FLASH_MECH_STILL_GATE_OR_VIDEO_LIGHT,
    P291_GA_ERR_FOCUS_AREA_STILL_TRACKING_OR_AF_REG,
    P291_GA_ERR_ISO_LIMIT_MIN_SS_OR_CINE_EI_LOCK,
    P291_GA_ERR_MODEL_OR_FW_FLOOR,
    P291_GA_ERR_XLR_H1_ZOOM_HANDLE_MYTH_OR_SPEED,
    P291_GB_ERR_CAMSET_CARD_PATH_VS_FX6_PRO_CAMERA,
    P291_GB_ERR_DCI4K_24P_REBOOT_OR_CODEC_GEOMETRY,
    P291_GB_ERR_PHOTO_CAPTURE_DCI4K_OR_SLOT1_FIREWALL,
    P291_GB_ERR_RECALL_CUSTOM_11_OR_HLG_LOCK,
    P291_GB_ERR_STILL_ASPECT_RATIO_4MODE_OR_APSC,
    P291_GC_ERR_EXPOSURE_COMP_RANGE_OR_CINE_EI_LOCK,
    P291_GC_ERR_FOCUS_MODE_5VS2_SPLIT_OR_SUBMENU,
    P291_GC_ERR_PLAYBACK_INDEX_OR_SLOT1_ROTATE_FIREWALL,
    P291_GC_ERR_SENSOR_CLEANING_51PCT_OFF_OR_FX6_END,
    P291_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION,
    P291_GD_ERR_H0_H3_IMMUTABILITY_DRIFT,
    P291_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID,
    P291_GO_NO_GO_BLOCKED_FOCUS_AREA_ZOOM_DCI4K_SENSOR_CLEANING_FAILURE,
    P291_GO_NO_GO_FOCUS_AREA_ZOOM_DCI4K_SENSOR_CLEANING_VERIFIED,
    P291_HDMI_RAW_WIDTH_HEIGHT,
    P291_HD_WIDTH_HEIGHT,
    P291_IMAGE_INDEX_TWO_MODES,
    P291_ISO_AUTO_MIN_SS_RESID16_HEX,
    P291_ISO_CEILING,
    P291_ISO_FLOOR,
    P291_ISO_RANGE_LIMIT_RESID16_HEX,
    P291_LEGACY_CLEANING_MODE_RESID16_HEX,
    P291_MI_SHOE_5V_MAX_MA,
    P291_MOVIE_FOCUS_TWO_MODES,
    P291_OVERALL_READY_OFFLINE_AWAITING_BENCH_RECEIPTS,
    P291_PHOTO_CAPTURE_DCI4K_BLOCK_RESID16_HEX,
    P291_PHOTO_CAPTURE_RESID16_HEX,
    P291_RECALL_CUSTOM_HOLD_11_KEYS,
    P291_RECALL_CUSTOM_SHOOT_SET_RESID16_HEX,
    P291_REMOTE_ZOOM_SPEED_RESID16_HEX,
    P291_SCHEMA,
    P291_SENSOR_CLEANING_MIN_SOC_PCT,
    P291_SENSOR_CLEANING_RESID16_HEX,
    P291_SONY_HELP_GUIDE_ID,
    P291_STILL_ASPECT_FOUR_MODES,
    P291_STILL_FOCUS_FIVE_MODES,
    P291_SWITCH_VH_AF_AREA_RESID16_HEX,
    P291_UHD_4K_WIDTH_HEIGHT,
    P291_VERSION,
    P291_VIDEO_LIGHT_BKID,
    P291_VIDEO_LIGHT_RESID16_HEX,
    P291_VIEW_MODE_THREE_MODES,
    P291_XAVC_SI_DCI_4K_RESID16_HEX,
    P291_ZOOM_LEVER_RESID16_HEX,
    PHASE291_PASSIVE_TX_BYTES_EMITTED,
    PHASE291_RAW_FIRMWARE_BYTES_LEAKED,
    PHASE291_USB_PACKETS_TRANSMITTED,
    PHASE_291_CHECK_GROUP_IDS,
    PHASE_291_SCHEMA,
    PHASE_291_VALID_GO_NO_GO_VALUES,
    PHASE_291_VERSION,
    REALHW_FOCUS_AREA_ZOOM_DCI4K_SENSOR_CLEANING_SCHEMA,
    build_simulated_phase291_tier0_receipts,
    evaluate_p291_check_group_a_focus_zoom_iso_flash,
    evaluate_p291_check_group_b_dci4k_aspect_hold_camset_photo,
    evaluate_p291_check_group_c_sensor_clean_ev_focus_playback,
    evaluate_p291_check_group_d_physical_bench_and_tier0,
    evaluate_realhw_focus_area_zoom_dci4k_and_sensor_cleaning_readiness,
    inspect_phase291_donors_bounded,
    render_phase291_markdown,
    run_focus_area_zoom_dci4k_and_sensor_cleaning_preflight,
    verify_phase291_report,
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
    return 15.0


class TestPhase291FocusAreaZoomDci4kAndSensorCleaningVerifier(unittest.TestCase):
    """76 dual-mode tests for Phase 291 10th physical bench readiness verifier."""

    # --- Section 1: Exports, Non-Shadowing, Constants & Bounded Donors (9 tests) ---

    def test_01_top_level_exports_and_non_shadowing_with_ph284(self) -> None:
        self.assertTrue(
            hasattr(
                fx6_closure,
                "evaluate_realhw_focus_area_zoom_dci4k_and_sensor_cleaning_readiness",
            )
        )
        self.assertTrue(
            hasattr(
                fx6_closure,
                "run_focus_area_zoom_dci4k_and_sensor_cleaning_preflight",
            )
        )
        self.assertIs(
            fx6_closure.run_focus_area_zoom_dci4k_and_sensor_cleaning_preflight,
            evaluate_realhw_focus_area_zoom_dci4k_and_sensor_cleaning_readiness,
        )
        self.assertTrue(hasattr(fx6_closure, "verify_phase291_report"))
        self.assertTrue(hasattr(fx6_closure, "render_phase291_markdown"))
        # Phase 284 exports remain intact and unshadowed.
        self.assertTrue(
            hasattr(
                fx6_closure,
                "evaluate_realhw_pp_scinetone_wb_metering_and_shutter_type_readiness",
            )
        )
        self.assertTrue(hasattr(fx6_closure, "verify_phase284_report"))
        self.assertIn("P291_SCHEMA", fx6_closure.__all__)
        self.assertIn(
            "evaluate_realhw_focus_area_zoom_dci4k_and_sensor_cleaning_readiness",
            fx6_closure.__all__,
        )

    def test_02_schema_version_check_group_ids_and_zero_locks(self) -> None:
        self.assertEqual(
            PHASE_291_SCHEMA,
            "realhw_focus_area_zoom_dci4k_and_sensor_cleaning_verifier_v1",
        )
        self.assertEqual(P291_SCHEMA, PHASE_291_SCHEMA)
        self.assertEqual(
            REALHW_FOCUS_AREA_ZOOM_DCI4K_SENSOR_CLEANING_SCHEMA, PHASE_291_SCHEMA
        )
        self.assertEqual(PHASE_291_VERSION, "291.0.0")
        self.assertEqual(P291_VERSION, "291.0.0")
        self.assertEqual(P291_SONY_HELP_GUIDE_ID, "ilc/2210")
        self.assertEqual(len(PHASE_291_CHECK_GROUP_IDS), 4)
        self.assertEqual(
            PHASE_291_CHECK_GROUP_IDS,
            (
                P291_CHECK_GROUP_A_ID,
                P291_CHECK_GROUP_B_ID,
                P291_CHECK_GROUP_C_ID,
                P291_CHECK_GROUP_D_ID,
            ),
        )
        self.assertEqual(PHASE291_RAW_FIRMWARE_BYTES_LEAKED, 0)
        self.assertEqual(PHASE291_PASSIVE_TX_BYTES_EMITTED, 0)
        self.assertEqual(PHASE291_USB_PACKETS_TRANSMITTED, 0)
        self.assertIn(
            P291_GO_NO_GO_FOCUS_AREA_ZOOM_DCI4K_SENSOR_CLEANING_VERIFIED,
            PHASE_291_VALID_GO_NO_GO_VALUES,
        )

    def test_03_waves50_to_52_constants_resid16_and_bkids(self) -> None:
        self.assertEqual(len(P291_FOCUS_AREA_NON_TRACKING_SEVEN), 7)
        self.assertEqual(len(P291_FOCUS_AREA_TRACKING_SEVEN), 7)
        self.assertEqual(len(P291_FOCUS_AREA_FOURTEEN_MODES), 14)
        self.assertEqual(P291_FOCUS_AREA_BKID, "BKID_APP_setting_autofocus_area_contrast_detect_af")
        self.assertEqual(P291_AF_AREA_REGISTRATION_BKID, "BKID_APP_setting_register_the_af_frame")
        self.assertEqual(P291_AF_AREA_REGISTRATION_LABEL, "AF Area Registration")
        self.assertEqual(P291_FOCUS_AREA_RESID16_HEX, "0x70ac")
        self.assertEqual(P291_FOCUS_AREA_LIMIT_RESID16_HEX, "0x6de2")
        self.assertEqual(P291_SWITCH_VH_AF_AREA_RESID16_HEX, "0x73ae")
        self.assertEqual(P291_FOCUS_AREA_COLOR_RESID16_HEX, "0x6af1")
        self.assertEqual(P291_CIRC_FOCUS_POINT_RESID16_HEX, "0x74f6")
        self.assertEqual(P291_AF_AREA_REGISTRATION_RESID16_HEX, "0x6b64")
        self.assertEqual(P291_ZOOM_LEVER_RESID16_HEX, "0x64c3")
        self.assertEqual(P291_REMOTE_ZOOM_SPEED_RESID16_HEX, "0x7128")
        self.assertEqual(P291_ISO_RANGE_LIMIT_RESID16_HEX, "0x72f8")
        self.assertEqual(P291_ISO_AUTO_MIN_SS_RESID16_HEX, "0x778b")
        self.assertEqual(P291_FLASH_MODE_RESID16_HEX, "0xe5ce")
        self.assertEqual(P291_VIDEO_LIGHT_BKID, "BKID_APP_setting_video_light_set")
        self.assertEqual(P291_VIDEO_LIGHT_RESID16_HEX, "0x6211")
        self.assertEqual(P291_MI_SHOE_5V_MAX_MA, 900)
        self.assertEqual(P291_XAVC_SI_DCI_4K_RESID16_HEX, "0x7336")
        self.assertEqual(P291_DCI_4K_REBOOT_24P_RESID16_HEX, "0x75ce")
        self.assertEqual(P291_DCI_4K_WIDTH_HEIGHT, "4096x2160")
        self.assertEqual(P291_UHD_4K_WIDTH_HEIGHT, "3840x2160")
        self.assertEqual(P291_HDMI_RAW_WIDTH_HEIGHT, "4264x2408")
        self.assertEqual(P291_HD_WIDTH_HEIGHT, "1920x1080")
        self.assertEqual(P291_ASPECT_RATIO_RESID16_HEX, "0x757c")
        self.assertEqual(P291_RECALL_CUSTOM_SHOOT_SET_RESID16_HEX, "0x7631")
        self.assertEqual(len(P291_RECALL_CUSTOM_HOLD_11_KEYS), 11)
        self.assertEqual(P291_PHOTO_CAPTURE_RESID16_HEX, "0x6856")
        self.assertEqual(P291_PHOTO_CAPTURE_DCI4K_BLOCK_RESID16_HEX, "0x60ce")
        self.assertEqual(P291_ENLARGE_IMAGE_RESID16_HEX, "0xe8cb")
        self.assertEqual(P291_SENSOR_CLEANING_RESID16_HEX, "0x67d6")
        self.assertEqual(P291_LEGACY_CLEANING_MODE_RESID16_HEX, "0xe7d7")
        self.assertEqual(P291_SENSOR_CLEANING_MIN_SOC_PCT, 51.0)
        self.assertEqual(P291_CRCOMMANDID_SENSOR_CLEANING, 320)
        self.assertEqual(P291_EXPOSURE_COMP_RESID16_HEX, "0x76de")
        self.assertEqual(P291_EV_COMP_STILL_ABS_MAX, 5.0)
        self.assertEqual(P291_EV_COMP_MOVIE_ABS_MAX, 2.0)
        self.assertEqual(P291_FOCUS_MODE_MOVIE_RESID16_HEX, "0x625e")
        self.assertEqual(len(P291_STILL_FOCUS_FIVE_MODES), 5)
        self.assertEqual(len(P291_MOVIE_FOCUS_TWO_MODES), 2)
        self.assertEqual(P291_VIEW_MODE_THREE_MODES, ("DATE_VIEW", "FOLDER_VIEW_STILL", "MOVIE_VIEW"))
        self.assertEqual(P291_IMAGE_INDEX_TWO_MODES, ("9_IMAGES", "25_IMAGES"))

    def test_04_bounded_donor_inspection_dual_mode_under_150ms(self) -> None:
        d_default = inspect_phase291_donors_bounded()
        self.assertTrue(d_default.passed)
        self.assertTrue(d_default.read_only_o_rdonly_enforced)
        self.assertTrue(d_default.within_150ms_budget)
        self.assertLess(d_default.elapsed_seconds, 0.15)
        self.assertEqual(d_default.raw_firmware_bytes_leaked, 0)
        self.assertIn(
            d_default.verification_mode,
            ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"),
        )

        d_clean = inspect_phase291_donors_bounded(force_clean_room=True)
        self.assertTrue(d_clean.passed)
        self.assertEqual(d_clean.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(d_clean.within_150ms_budget)
        self.assertEqual(d_clean.raw_firmware_bytes_leaked, 0)

    def test_05_forced_clean_room_env_flag_selects_clean_room_synthetic(self) -> None:
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            res = inspect_phase291_donors_bounded()
        self.assertTrue(res.passed)
        self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_06_fx3_clean_room_test_env_flag_selects_clean_room_synthetic(self) -> None:
        with mock.patch.dict(os.environ, {"FX3_CLEAN_ROOM_TEST": "1"}):
            res = inspect_phase291_donors_bounded()
        self.assertTrue(res.passed)
        self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_07_missing_donors_fail_closed_when_clean_room_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            res = inspect_phase291_donors_bounded(
                fx6_lib_dir=Path(td) / "missing_lib",
                fx3_modules_dir=Path(td) / "missing_mod",
                force_clean_room=False,
            )
        self.assertFalse(res.passed)
        self.assertEqual(res.verification_mode, "LOCAL_DONOR_O_RDONLY")
        self.assertEqual(res.raw_firmware_bytes_leaked, 0)
        self.assertTrue(any("missing" in err for err in res.errors))

    def test_08_wrong_model_or_fw_below_floor_rejected_group_a(self) -> None:
        bad_model = evaluate_p291_check_group_a_focus_zoom_iso_flash(body_model_id=0x12345678)
        self.assertFalse(bad_model.passed)
        self.assertTrue(any(P291_GA_ERR_MODEL_OR_FW_FLOOR in e for e in bad_model.errors))

        bad_fw = evaluate_p291_check_group_a_focus_zoom_iso_flash(body_fw="1.01")
        self.assertFalse(bad_fw.passed)
        self.assertTrue(any(P291_GA_ERR_MODEL_OR_FW_FLOOR in e for e in bad_fw.errors))

    def test_09_wrong_help_guide_id_or_invalid_reset_shoot_mode_rejected(self) -> None:
        bad_hg = evaluate_p291_check_group_a_focus_zoom_iso_flash(sony_help_guide_id="ilc/2035")
        self.assertFalse(bad_hg.passed)
        self.assertTrue(any(P291_GA_ERR_MODEL_OR_FW_FLOOR in e for e in bad_hg.errors))

        bad_mode = evaluate_p291_check_group_a_focus_zoom_iso_flash(
            reset_action="BAD_RESET", shoot_mode="BAD_SHOOT"
        )
        self.assertFalse(bad_mode.passed)
        self.assertTrue(
            any(P291_GA_ERR_FOCUS_AREA_STILL_TRACKING_OR_AF_REG in e for e in bad_mode.errors)
        )

    # --- Section 2: Check Group A (Wave 50, 17 tests) ---

    def test_10_ga_7_plus_7_focus_areas_still_tracking_allowed_in_photo(self) -> None:
        ga = evaluate_p291_check_group_a_focus_zoom_iso_flash(
            shoot_mode="PHOTO",
            focus_area="TRACKING_SPOT_M",
        )
        self.assertTrue(ga.passed)
        self.assertEqual(ga.non_tracking_focus_area_count, 7)
        self.assertEqual(ga.tracking_focus_area_count, 7)
        self.assertTrue(ga.tracking_still_only_enforced)

    def test_11_ga_tracking_focus_area_blocked_in_movie_and_sq(self) -> None:
        for mode in ("MOVIE", "S_AND_Q"):
            for fa in P291_FOCUS_AREA_TRACKING_SEVEN:
                ga = evaluate_p291_check_group_a_focus_zoom_iso_flash(
                    shoot_mode=mode, focus_area=fa
                )
                self.assertFalse(ga.passed)
                self.assertFalse(ga.tracking_still_only_enforced)
                self.assertTrue(
                    any(P291_GA_ERR_FOCUS_AREA_STILL_TRACKING_OR_AF_REG in e for e in ga.errors)
                )

    def test_12_ga_expect_tracking_in_movie_or_missing_touch_tracking_rejected(self) -> None:
        ga1 = evaluate_p291_check_group_a_focus_zoom_iso_flash(
            expect_tracking_focus_area_in_movie=True
        )
        self.assertFalse(ga1.passed)
        ga2 = evaluate_p291_check_group_a_focus_zoom_iso_flash(
            touch_tracking_used_for_movie_sq=False
        )
        self.assertFalse(ga2.passed)

    def test_13_ga_fx6_reference_tracking_focus_areas_rejected(self) -> None:
        ga = evaluate_p291_check_group_a_focus_zoom_iso_flash(
            fx6_reference_tracking_focus_areas_present=True
        )
        self.assertFalse(ga.passed)
        self.assertTrue(
            any(P291_GA_ERR_FOCUS_AREA_STILL_TRACKING_OR_AF_REG in e for e in ga.errors)
        )

    def test_14_ga_focus_area_limit_enforces_2_to_14_items(self) -> None:
        self.assertTrue(
            evaluate_p291_check_group_a_focus_zoom_iso_flash(
                focus_area_limit_selected_count=2
            ).passed
        )
        self.assertFalse(
            evaluate_p291_check_group_a_focus_zoom_iso_flash(
                focus_area_limit_selected_count=1
            ).passed
        )
        self.assertFalse(
            evaluate_p291_check_group_a_focus_zoom_iso_flash(
                focus_area_limit_selected_count=15
            ).passed
        )

    def test_15_ga_switch_vh_af_area_still_only_and_focus_area_color_non_resettable(self) -> None:
        ok_still = evaluate_p291_check_group_a_focus_zoom_iso_flash(
            shoot_mode="PHOTO",
            switch_vh_af_area="AF_POINT_AND_AF_AREA",
            focus_area_color="RED",
            circ_of_focus_point="CIRCULATE",
        )
        self.assertTrue(ok_still.passed)

        bad_movie = evaluate_p291_check_group_a_focus_zoom_iso_flash(
            shoot_mode="MOVIE",
            switch_vh_af_area="AF_POINT_ONLY",
        )
        self.assertFalse(bad_movie.passed)

        bad_wipe = evaluate_p291_check_group_a_focus_zoom_iso_flash(
            reset_action="CAMERA_SETTINGS_RESET",
            claimed_non_resettable_af_prefs_wiped=True,
        )
        self.assertFalse(bad_wipe.passed)

    def test_16_ga_af_area_registration_exact_ilc2210_label_vs_legacy_and_reset_survival(self) -> None:
        bad_legacy = evaluate_p291_check_group_a_focus_zoom_iso_flash(
            af_area_registration_label="AF Area Regist."
        )
        self.assertFalse(bad_legacy.passed)
        self.assertTrue(
            any(P291_GA_ERR_FOCUS_AREA_STILL_TRACKING_OR_AF_REG in e for e in bad_legacy.errors)
        )

    def test_17_ga_xlr_h1_has_no_zoom_lever_rec_button_or_zoom_hold_switch(self) -> None:
        for kw in (
            {"xlr_h1_zoom_lever_present": True},
            {"xlr_h1_rec_button_present": True},
            {"xlr_h1_zoom_hold_switch_present": True},
        ):
            ga = evaluate_p291_check_group_a_focus_zoom_iso_flash(**kw)
            self.assertFalse(ga.passed)
            self.assertTrue(
                any(P291_GA_ERR_XLR_H1_ZOOM_HANDLE_MYTH_OR_SPEED in e for e in ga.errors)
            )

    def test_18_ga_fx6_zero_to_99_is_zoom_position_display_not_speed_scale(self) -> None:
        ga_ok = evaluate_p291_check_group_a_focus_zoom_iso_flash()
        self.assertTrue(ga_ok.fx6_smart_handle_zero_to_99_is_position_display)
        ga_bad = evaluate_p291_check_group_a_focus_zoom_iso_flash(
            fx6_smart_handle_zero_to_99_is_speed_scale=True
        )
        self.assertFalse(ga_bad.passed)
        self.assertFalse(ga_bad.fx6_smart_handle_zero_to_99_is_position_display)
        self.assertTrue(
            any(P291_GA_ERR_XLR_H1_ZOOM_HANDLE_MYTH_OR_SPEED in e for e in ga_bad.errors)
        )

    def test_19_ga_body_wt_zoom_lever_custom_key_and_remote_speeds_1_to_8(self) -> None:
        ok = evaluate_p291_check_group_a_focus_zoom_iso_flash(
            zoom_lever_stby_speed=1,
            zoom_lever_rec_speed=8,
            custom_key_zoom_stby_speed=5,
            custom_key_zoom_rec_speed=7,
            remote_zoom_speed_type="FIXED",
            remote_zoom_fixed_stby_speed=2,
            remote_zoom_fixed_rec_speed=6,
        )
        self.assertTrue(ok.passed)

        for kw in (
            {"zoom_lever_stby_speed": 0},
            {"zoom_lever_rec_speed": 9},
            {"custom_key_zoom_rec_speed": 99},
            {"remote_zoom_fixed_stby_speed": 9},
            {"remote_zoom_speed_type": "STEP99"},
        ):
            self.assertFalse(
                evaluate_p291_check_group_a_focus_zoom_iso_flash(**kw).passed
            )

    def test_20_ga_zoom_range_clearimage_digital_lockout_in_raw_120p_and_reset_survival(self) -> None:
        self.assertTrue(
            evaluate_p291_check_group_a_focus_zoom_iso_flash(
                zoom_range="CLEAR_IMAGE_ZOOM"
            ).passed
        )
        self.assertFalse(
            evaluate_p291_check_group_a_focus_zoom_iso_flash(
                zoom_range="CLEAR_IMAGE_ZOOM", still_raw_active=True
            ).passed
        )
        self.assertFalse(
            evaluate_p291_check_group_a_focus_zoom_iso_flash(
                zoom_range="DIGITAL_ZOOM", high_fps_120_100=True
            ).passed
        )
        self.assertFalse(
            evaluate_p291_check_group_a_focus_zoom_iso_flash(
                reset_action="CAMERA_SETTINGS_RESET", claimed_zoom_range_wiped=True
            ).passed
        )

    def test_21_ga_iso_range_limit_50_to_409600_and_reset_survival(self) -> None:
        self.assertTrue(
            evaluate_p291_check_group_a_focus_zoom_iso_flash(
                iso_range_limit_min=P291_ISO_FLOOR,
                iso_range_limit_max=P291_ISO_CEILING,
            ).passed
        )
        self.assertFalse(
            evaluate_p291_check_group_a_focus_zoom_iso_flash(
                iso_range_limit_min=25
            ).passed
        )
        self.assertFalse(
            evaluate_p291_check_group_a_focus_zoom_iso_flash(
                iso_range_limit_max=819200
            ).passed
        )
        self.assertFalse(
            evaluate_p291_check_group_a_focus_zoom_iso_flash(
                reset_action="CAMERA_SETTINGS_RESET",
                claimed_iso_range_limit_wiped=True,
            ).passed
        )

    def test_22_ga_iso_auto_min_ss_allowed_in_still_pa_iso_auto_with_thresholds(self) -> None:
        for exp in ("PROGRAM_AUTO", "APERTURE_PRIORITY"):
            for min_ss in ("STANDARD", "FAST_1EV", "1/250"):
                ga = evaluate_p291_check_group_a_focus_zoom_iso_flash(
                    shoot_mode="PHOTO",
                    exposure_mode=exp,
                    iso_mode="ISO_AUTO",
                    log_shooting_mode="OFF",
                    iso_auto_min_ss=min_ss,
                    iso_auto_min_ss_active=True,
                )
                self.assertTrue(ga.passed, msg=f"Failed for {exp} {min_ss}: {ga.errors}")
                self.assertTrue(ga.iso_auto_min_ss_still_pa_only_enforced)

    def test_23_ga_iso_auto_min_ss_locked_out_in_movie_manual_iso_or_cine_ei(self) -> None:
        for kw in (
            {
                "shoot_mode": "MOVIE",
                "exposure_mode": "PROGRAM_AUTO",
                "iso_mode": "ISO_AUTO",
                "log_shooting_mode": "OFF",
                "iso_auto_min_ss_active": True,
            },
            {
                "shoot_mode": "PHOTO",
                "exposure_mode": "MANUAL_EXPOSURE",
                "iso_mode": "ISO_AUTO",
                "log_shooting_mode": "OFF",
                "iso_auto_min_ss_active": True,
            },
            {
                "shoot_mode": "PHOTO",
                "exposure_mode": "PROGRAM_AUTO",
                "iso_mode": "MANUAL_ISO",
                "log_shooting_mode": "OFF",
                "iso_auto_min_ss_active": True,
            },
            {"expect_iso_auto_min_ss_in_movie_or_manual_iso": True},
        ):
            ga = evaluate_p291_check_group_a_focus_zoom_iso_flash(**kw)
            self.assertFalse(ga.passed)
            self.assertFalse(ga.iso_auto_min_ss_still_pa_only_enforced)
            self.assertTrue(
                any(P291_GA_ERR_ISO_LIMIT_MIN_SS_OR_CINE_EI_LOCK in e for e in ga.errors)
            )

    def test_24_ga_cine_ei_locks_base_iso_800_12800_and_rejects_variable_iso(self) -> None:
        for base in P291_CINE_EI_BASE_ISOS:
            self.assertTrue(
                evaluate_p291_check_group_a_focus_zoom_iso_flash(
                    log_shooting_mode="CINE_EI", cine_ei_base_iso=base
                ).passed
            )
        self.assertFalse(
            evaluate_p291_check_group_a_focus_zoom_iso_flash(
                log_shooting_mode="CINE_EI", cine_ei_base_iso=3200
            ).passed
        )
        self.assertFalse(
            evaluate_p291_check_group_a_focus_zoom_iso_flash(
                log_shooting_mode="CINE_EI_QUICK", expect_iso_variable_in_cine_ei=True
            ).passed
        )

    def test_25_ga_flash_mode_gated_to_mechanical_shutter_still_only(self) -> None:
        ok = evaluate_p291_check_group_a_focus_zoom_iso_flash(
            shoot_mode="PHOTO",
            shutter_type="MECHANICAL_SHUTTER",
            silent_mode="OFF",
            flash_mode="FILL_FLASH",
            flash_firing_enabled=True,
        )
        self.assertTrue(ok.passed)
        self.assertTrue(ok.flash_mechanical_still_gate_verified)

        for kw in (
            {"shoot_mode": "MOVIE", "flash_firing_enabled": True},
            {"shoot_mode": "S_AND_Q", "flash_firing_enabled": True},
            {"shoot_mode": "PHOTO", "shutter_type": "ELECTRONIC_SHUTTER", "flash_firing_enabled": True},
            {"shoot_mode": "PHOTO", "silent_mode": "ON", "flash_firing_enabled": True},
        ):
            ga = evaluate_p291_check_group_a_focus_zoom_iso_flash(**kw)
            self.assertFalse(ga.passed)
            self.assertFalse(ga.flash_mechanical_still_gate_verified)
            self.assertTrue(
                any(P291_GA_ERR_FLASH_MECH_STILL_GATE_OR_VIDEO_LIGHT in e for e in ga.errors)
            )

    def test_26_ga_flash_comp_range_exp_comp_set_and_video_light_5v_900ma_gate(self) -> None:
        self.assertFalse(
            evaluate_p291_check_group_a_focus_zoom_iso_flash(flash_comp_ev=3.3).passed
        )
        self.assertFalse(
            evaluate_p291_check_group_a_focus_zoom_iso_flash(
                reset_action="CAMERA_SETTINGS_RESET", claimed_exp_comp_set_wiped=True
            ).passed
        )
        for mode in ("POWER_LINK", "REC_LINK", "REC_LINK_AND_STBY", "AUTO"):
            self.assertTrue(
                evaluate_p291_check_group_a_focus_zoom_iso_flash(
                    video_light_mode=mode, mi_shoe_5v_current_ma=900
                ).passed
            )
        self.assertFalse(
            evaluate_p291_check_group_a_focus_zoom_iso_flash(
                video_light_mode="POWER_LINK", mi_shoe_5v_current_ma=901
            ).passed
        )

    # --- Section 3: Check Group B (Wave 51, 15 tests) ---

    def test_27_gb_xavc_si_dci_4k_4096x2160_17_9_allowed_23_98p_to_59_94p(self) -> None:
        for fps in P291_DCI_4K_FRAME_RATES:
            gb = evaluate_p291_check_group_b_dci4k_aspect_hold_camset_photo(
                movie_file_format="XAVC_S_I_DCI_4K",
                movie_resolution_wh="4096x2160",
                rec_frame_rate=fps,
                ack_24p_reboot_wipes_tmp_overlay=(fps == "24.00P"),
            )
            self.assertTrue(gb.passed, msg=f"DCI 4K {fps} failed: {gb.errors}")

    def test_28_gb_xavc_si_dci_4k_rejects_100p_120p_and_sq_above_48fps(self) -> None:
        for bad_fps in ("100P", "119.88P"):
            gb = evaluate_p291_check_group_b_dci4k_aspect_hold_camset_photo(
                movie_file_format="XAVC_S_I_DCI_4K",
                movie_resolution_wh="4096x2160",
                rec_frame_rate=bad_fps,
            )
            self.assertFalse(gb.passed)
            self.assertTrue(
                any(P291_GB_ERR_DCI4K_24P_REBOOT_OR_CODEC_GEOMETRY in e for e in gb.errors)
            )

        bad_sq = evaluate_p291_check_group_b_dci4k_aspect_hold_camset_photo(
            sq_dci4k_fps=P291_DCI_4K_SQ_MAX_FPS + 12
        )
        self.assertFalse(bad_sq.passed)

    def test_29_gb_xavc_si_dci_4k_600m_requires_vpg200_or_v90_media(self) -> None:
        self.assertTrue(
            evaluate_p291_check_group_b_dci4k_aspect_hold_camset_photo(
                rec_frame_rate="59.94P",
                bitrate_mbps=600,
                media_speed_grade="SDXC_V90",
            ).passed
        )
        self.assertFalse(
            evaluate_p291_check_group_b_dci4k_aspect_hold_camset_photo(
                rec_frame_rate="59.94P",
                bitrate_mbps=600,
                media_speed_grade="SDXC_V60",
            ).passed
        )

    def test_30_gb_long_gop_4k_codecs_stay_uhd_3840x2160_no_24p(self) -> None:
        for fmt in ("XAVC_HS_4K", "XAVC_S_4K", "XAVC_S_I_4K"):
            self.assertTrue(
                evaluate_p291_check_group_b_dci4k_aspect_hold_camset_photo(
                    movie_file_format=fmt,
                    movie_resolution_wh=P291_UHD_4K_WIDTH_HEIGHT,
                    rec_frame_rate="23.98P",
                ).passed
            )
            self.assertFalse(
                evaluate_p291_check_group_b_dci4k_aspect_hold_camset_photo(
                    movie_file_format=fmt,
                    movie_resolution_wh=P291_DCI_4K_WIDTH_HEIGHT,
                    rec_frame_rate="23.98P",
                ).passed
            )
            self.assertFalse(
                evaluate_p291_check_group_b_dci4k_aspect_hold_camset_photo(
                    movie_file_format=fmt,
                    movie_resolution_wh=P291_UHD_4K_WIDTH_HEIGHT,
                    rec_frame_rate="24.00P",
                    ack_24p_reboot_wipes_tmp_overlay=True,
                ).passed
            )

    def test_31_gb_24_00p_reboot_quarantine_requires_clear_tmp_and_explicit_ack(self) -> None:
        ok = evaluate_p291_check_group_b_dci4k_aspect_hold_camset_photo(
            movie_file_format="XAVC_S_I_DCI_4K",
            movie_resolution_wh="4096x2160",
            rec_frame_rate="24.00P",
            stage_b_volatile_tmp_overlay_active=False,
            ack_24p_reboot_wipes_tmp_overlay=True,
        )
        self.assertTrue(ok.passed)
        self.assertTrue(ok.dci4k_24p_reboot_required)
        self.assertTrue(ok.dci4k_24p_reboot_wipes_volatile_tmp_acknowledged)

        for kw in (
            {"rec_frame_rate": "24.00P", "ack_24p_reboot_wipes_tmp_overlay": False},
            {
                "rec_frame_rate": "24.00P",
                "stage_b_volatile_tmp_overlay_active": True,
                "ack_24p_reboot_wipes_tmp_overlay": True,
            },
            {"expect_24p_no_reboot": True},
        ):
            self.assertFalse(
                evaluate_p291_check_group_b_dci4k_aspect_hold_camset_photo(**kw).passed
            )

    def test_32_gb_hdmi_raw_output_4264x2408_validated(self) -> None:
        self.assertTrue(
            evaluate_p291_check_group_b_dci4k_aspect_hold_camset_photo(
                hdmi_raw_output=True, hdmi_raw_resolution_wh="4264x2408"
            ).passed
        )
        self.assertFalse(
            evaluate_p291_check_group_b_dci4k_aspect_hold_camset_photo(
                hdmi_raw_output=True, hdmi_raw_resolution_wh="4096x2160"
            ).passed
        )

    def test_33_gb_still_aspect_ratio_4modes_and_apsc_s35_l_to_m_stepdown(self) -> None:
        for ar in P291_STILL_ASPECT_FOUR_MODES:
            self.assertTrue(
                evaluate_p291_check_group_b_dci4k_aspect_hold_camset_photo(
                    still_aspect_ratio=ar
                ).passed
            )
        self.assertTrue(
            evaluate_p291_check_group_b_dci4k_aspect_hold_camset_photo(
                apsc_s35_on=True, still_jpeg_heif_size="M"
            ).passed
        )
        bad_apsc = evaluate_p291_check_group_b_dci4k_aspect_hold_camset_photo(
            apsc_s35_on=True, still_jpeg_heif_size="L"
        )
        self.assertFalse(bad_apsc.passed)
        self.assertTrue(
            any(P291_GB_ERR_STILL_ASPECT_RATIO_4MODE_OR_APSC in e for e in bad_apsc.errors)
        )

    def test_34_gb_fx6_still_aspect_ratio_claim_rejected(self) -> None:
        gb = evaluate_p291_check_group_b_dci4k_aspect_hold_camset_photo(
            fx6_reference_still_aspect_ratio_present=True
        )
        self.assertFalse(gb.passed)
        self.assertTrue(
            any(P291_GB_ERR_STILL_ASPECT_RATIO_4MODE_OR_APSC in e for e in gb.errors)
        )

    def test_35_gb_reg_custom_shoot_set_exact_11_hold_checkboxes_and_still_pasm_only(self) -> None:
        ok = evaluate_p291_check_group_b_dci4k_aspect_hold_camset_photo(
            exposure_mode="APERTURE_PRIORITY",
            recall_custom_recalled_items=("SHOOTING_MODE", "ISO", "FOCUS_AREA"),
        )
        self.assertTrue(ok.passed)
        self.assertEqual(ok.recall_custom_hold_checkbox_count, 11)

        bad_10 = evaluate_p291_check_group_b_dci4k_aspect_hold_camset_photo(
            recall_custom_hold_keys=P291_RECALL_CUSTOM_HOLD_11_KEYS[:10]
        )
        self.assertFalse(bad_10.passed)
        self.assertTrue(
            any(P291_GB_ERR_RECALL_CUSTOM_11_OR_HLG_LOCK in e for e in bad_10.errors)
        )

        bad_iauto = evaluate_p291_check_group_b_dci4k_aspect_hold_camset_photo(
            exposure_mode="INTELLIGENT_AUTO",
            recall_custom_recalled_items=("APERTURE",),
        )
        self.assertFalse(bad_iauto.passed)

    def test_36_gb_reg_custom_shoot_set_hlg_still_iso_dro_lockout_and_reset_survival(self) -> None:
        self.assertFalse(
            evaluate_p291_check_group_b_dci4k_aspect_hold_camset_photo(
                hlg_still_image="ON", recall_custom_recalled_items=("ISO",)
            ).passed
        )
        self.assertFalse(
            evaluate_p291_check_group_b_dci4k_aspect_hold_camset_photo(
                hlg_still_image="ON", recall_custom_recalled_items=("DRO_BRACKET",)
            ).passed
        )
        self.assertFalse(
            evaluate_p291_check_group_b_dci4k_aspect_hold_camset_photo(
                reset_action="CAMERA_SETTINGS_RESET",
                claimed_recall_custom_wiped_by_camera_reset=True,
            ).passed
        )

    def test_37_gb_fx3_camset_and_m1_m4_card_paths_vs_forbidden_fx6_pro_camera(self) -> None:
        for path in (
            P291_DEFAULT_FX3_SETTING_CARD_PATH,
            "E:/SONY/SETTING/FX3/CAMSET03.DAT",
            "/PRIVATE/SONY/SETTING/FX3/CAMPR01M.DAT",
            "D:/SONY/SETTING/FX3/CAMPR04A.DAT",
        ):
            self.assertRegex(path, P291_FX3_SETTING_CARD_PATH_RE)
            self.assertTrue(
                evaluate_p291_check_group_b_dci4k_aspect_hold_camset_photo(
                    camset_card_path=path
                ).passed
            )

        for bad_path in (
            "/PRIVATE/SONY/PRO/CAMERA/USER01.DAT",
            "/SONY/PRO/SCENE/SCN01.DAT",
        ):
            gb = evaluate_p291_check_group_b_dci4k_aspect_hold_camset_photo(
                camset_card_path=bad_path
            )
            self.assertFalse(gb.passed)
            self.assertTrue(
                any(P291_GB_ERR_CAMSET_CARD_PATH_VS_FX6_PRO_CAMERA in e for e in gb.errors)
            )

        self.assertFalse(
            evaluate_p291_check_group_b_dci4k_aspect_hold_camset_photo(
                fx3_uses_private_sony_pro_camera=True
            ).passed
        )

    def test_38_gb_memory_recall_media_resets_to_slot1_and_format_erases_m1_m4(self) -> None:
        self.assertFalse(
            evaluate_p291_check_group_b_dci4k_aspect_hold_camset_photo(
                reset_action="CAMERA_SETTINGS_RESET",
                claimed_memory_recall_media_survives_reset_as_slot2=True,
            ).passed
        )
        self.assertFalse(
            evaluate_p291_check_group_b_dci4k_aspect_hold_camset_photo(
                expect_format_preserves_camset_or_m1_m4=True
            ).passed
        )

    def test_39_gb_photo_capture_blocked_on_xavc_si_dci4k_0x60ce(self) -> None:
        gb = evaluate_p291_check_group_b_dci4k_aspect_hold_camset_photo(
            movie_file_format="XAVC_S_I_DCI_4K",
            movie_resolution_wh="4096x2160",
            photo_capture_requested=True,
            photo_capture_slot=2,
        )
        self.assertFalse(gb.passed)
        self.assertFalse(gb.photo_capture_dci4k_blocked_and_slot1_firewalled)
        self.assertTrue(
            any(P291_GB_ERR_PHOTO_CAPTURE_DCI4K_OR_SLOT1_FIREWALL in e for e in gb.errors)
        )

    def test_40_gb_photo_capture_blocked_on_slot1_tier0_vault_allowed_on_slot2_uhd(self) -> None:
        bad_slot1 = evaluate_p291_check_group_b_dci4k_aspect_hold_camset_photo(
            movie_file_format="XAVC_S_I_4K",
            movie_resolution_wh="3840x2160",
            photo_capture_requested=True,
            photo_capture_slot=1,
            slot1_contains_tier0_dump=True,
        )
        self.assertFalse(bad_slot1.passed)
        self.assertFalse(bad_slot1.photo_capture_dci4k_blocked_and_slot1_firewalled)

        ok_slot2 = evaluate_p291_check_group_b_dci4k_aspect_hold_camset_photo(
            movie_file_format="XAVC_S_I_4K",
            movie_resolution_wh="3840x2160",
            photo_capture_requested=True,
            photo_capture_slot=2,
            slot1_contains_tier0_dump=True,
        )
        self.assertTrue(ok_slot2.passed)
        self.assertTrue(ok_slot2.photo_capture_dci4k_blocked_and_slot1_firewalled)

    def test_41_gb_enlarge_image_still_only_and_initial_mag_pos_survive_reset(self) -> None:
        self.assertFalse(
            evaluate_p291_check_group_b_dci4k_aspect_hold_camset_photo(
                enlarge_image_in_movie_claimed=True
            ).passed
        )
        self.assertFalse(
            evaluate_p291_check_group_b_dci4k_aspect_hold_camset_photo(
                reset_action="CAMERA_SETTINGS_RESET",
                claimed_enlarge_prefs_wiped_by_camera_reset=True,
            ).passed
        )

    # --- Section 4: Check Group C (Wave 52, 16 tests) ---

    def test_42_gc_sensor_cleaning_requires_51pct_soc_and_mandatory_off(self) -> None:
        gc = evaluate_p291_check_group_c_sensor_clean_ev_focus_playback(
            sensor_cleaning_requested=True,
            battery_soc_pct=51.0,
            mandatory_power_off_after_cleaning=True,
        )
        self.assertTrue(gc.passed)
        self.assertTrue(gc.mandatory_power_off_after_cleaning)

    def test_43_gc_sensor_cleaning_blocked_below_51pct_or_missing_off_or_active_dump(self) -> None:
        for kw in (
            {
                "sensor_cleaning_requested": True,
                "battery_soc_pct": 50.9,
                "mandatory_power_off_after_cleaning": True,
            },
            {
                "sensor_cleaning_requested": True,
                "battery_soc_pct": 90.0,
                "mandatory_power_off_after_cleaning": False,
            },
            {
                "sensor_cleaning_requested": True,
                "battery_soc_pct": 90.0,
                "mandatory_power_off_after_cleaning": True,
                "unattended_tier0_dump_active": True,
            },
        ):
            gc = evaluate_p291_check_group_c_sensor_clean_ev_focus_playback(**kw)
            self.assertFalse(gc.passed)
            self.assertTrue(
                any(P291_GC_ERR_SENSOR_CLEANING_51PCT_OFF_OR_FX6_END in e for e in gc.errors)
            )

    def test_44_gc_fx6_sensor_cleaning_and_fx3_builtin_end_filter_claims_rejected(self) -> None:
        self.assertFalse(
            evaluate_p291_check_group_c_sensor_clean_ev_focus_playback(
                fx6_sensor_cleaning_supported_claimed=True
            ).passed
        )
        self.assertFalse(
            evaluate_p291_check_group_c_sensor_clean_ev_focus_playback(
                fx3_has_built_in_end_filter=True
            ).passed
        )

    def test_45_gc_exposure_comp_plus_minus_5ev_still_and_2ev_movie(self) -> None:
        self.assertTrue(
            evaluate_p291_check_group_c_sensor_clean_ev_focus_playback(
                shoot_mode="PHOTO",
                exposure_mode="APERTURE_PRIORITY",
                iso_mode="ISO_AUTO",
                log_shooting_mode="OFF",
                exposure_comp_ev=5.0,
            ).passed
        )
        self.assertFalse(
            evaluate_p291_check_group_c_sensor_clean_ev_focus_playback(
                shoot_mode="PHOTO",
                exposure_mode="APERTURE_PRIORITY",
                iso_mode="ISO_AUTO",
                log_shooting_mode="OFF",
                exposure_comp_ev=5.3,
            ).passed
        )
        self.assertTrue(
            evaluate_p291_check_group_c_sensor_clean_ev_focus_playback(
                shoot_mode="MOVIE",
                exposure_mode="MANUAL_EXPOSURE",
                iso_mode="ISO_AUTO",
                log_shooting_mode="OFF",
                exposure_comp_ev=-2.0,
            ).passed
        )
        self.assertFalse(
            evaluate_p291_check_group_c_sensor_clean_ev_focus_playback(
                shoot_mode="MOVIE",
                exposure_mode="MANUAL_EXPOSURE",
                iso_mode="ISO_AUTO",
                log_shooting_mode="OFF",
                exposure_comp_ev=2.3,
            ).passed
        )

    def test_46_gc_exposure_comp_locked_out_under_cine_ei_and_fixed_manual_iso(self) -> None:
        for log_mode in ("CINE_EI", "CINE_EI_QUICK"):
            gc = evaluate_p291_check_group_c_sensor_clean_ev_focus_playback(
                shoot_mode="MOVIE",
                exposure_mode="MANUAL_EXPOSURE",
                iso_mode="CINE_EI_BASE",
                log_shooting_mode=log_mode,
                exposure_comp_ev=1.0,
            )
            self.assertFalse(gc.passed)
            self.assertFalse(gc.ev_comp_cine_ei_lockout_verified)
            self.assertTrue(
                any(P291_GC_ERR_EXPOSURE_COMP_RANGE_OR_CINE_EI_LOCK in e for e in gc.errors)
            )

        fixed_m = evaluate_p291_check_group_c_sensor_clean_ev_focus_playback(
            shoot_mode="MOVIE",
            exposure_mode="MANUAL_EXPOSURE",
            iso_mode="MANUAL_ISO",
            log_shooting_mode="OFF",
            exposure_comp_ev=-1.0,
        )
        self.assertFalse(fixed_m.passed)

    def test_47_gc_exposure_comp_locked_out_in_iauto_and_allowed_under_flexible_iso(self) -> None:
        self.assertFalse(
            evaluate_p291_check_group_c_sensor_clean_ev_focus_playback(
                shoot_mode="PHOTO",
                exposure_mode="INTELLIGENT_AUTO",
                iso_mode="ISO_AUTO",
                log_shooting_mode="OFF",
                exposure_comp_ev=1.0,
            ).passed
        )
        self.assertTrue(
            evaluate_p291_check_group_c_sensor_clean_ev_focus_playback(
                shoot_mode="MOVIE",
                exposure_mode="MANUAL_EXPOSURE",
                iso_mode="ISO_AUTO",
                log_shooting_mode="FLEXIBLE_ISO",
                exposure_comp_ev=1.7,
            ).passed
        )

    def test_48_gc_omitted_legacy_reset_ev_comp_and_exposure_step_reset_survival(self) -> None:
        self.assertFalse(
            evaluate_p291_check_group_c_sensor_clean_ev_focus_playback(
                legacy_reset_ev_comp_claimed=True
            ).passed
        )
        self.assertFalse(
            evaluate_p291_check_group_c_sensor_clean_ev_focus_playback(
                reset_action="CAMERA_SETTINGS_RESET",
                claimed_exposure_step_wiped_by_camera_reset=True,
            ).passed
        )
        self.assertTrue(
            evaluate_p291_check_group_c_sensor_clean_ev_focus_playback(
                exposure_step="0.5EV"
            ).passed
        )

    def test_49_gc_focus_mode_5vs2_split_still_5_vs_movie_sq_2(self) -> None:
        for fm in P291_STILL_FOCUS_FIVE_MODES:
            gc = evaluate_p291_check_group_c_sensor_clean_ev_focus_playback(
                shoot_mode="PHOTO", focus_mode=fm
            )
            self.assertTrue(gc.passed, msg=f"Still focus {fm} failed: {gc.errors}")
            self.assertEqual(gc.exposed_still_focus_mode_count, 5)
            self.assertEqual(gc.exposed_movie_focus_mode_count, 2)
            self.assertTrue(gc.focus_mode_5vs2_split_verified)

        for sm in ("MOVIE", "S_AND_Q"):
            for fm in P291_MOVIE_FOCUS_TWO_MODES:
                self.assertTrue(
                    evaluate_p291_check_group_c_sensor_clean_ev_focus_playback(
                        shoot_mode=sm, focus_mode=fm
                    ).passed
                )

    def test_50_gc_focus_mode_af_s_af_a_dmf_blocked_in_movie_and_sq(self) -> None:
        for sm in ("MOVIE", "S_AND_Q"):
            for fm in ("AF_S", "AF_A", "DMF"):
                gc = evaluate_p291_check_group_c_sensor_clean_ev_focus_playback(
                    shoot_mode=sm, focus_mode=fm
                )
                self.assertFalse(gc.passed)
                self.assertFalse(gc.focus_mode_5vs2_split_verified)
                self.assertTrue(
                    any(P291_GC_ERR_FOCUS_MODE_5VS2_SPLIT_OR_SUBMENU in e for e in gc.errors)
                )

    def test_51_gc_af_assist_gated_to_movie_af_c_only_and_priority_set_survives_reset(self) -> None:
        self.assertTrue(
            evaluate_p291_check_group_c_sensor_clean_ev_focus_playback(
                shoot_mode="MOVIE", focus_mode="AF_C", af_assist_active=True
            ).passed
        )
        self.assertFalse(
            evaluate_p291_check_group_c_sensor_clean_ev_focus_playback(
                shoot_mode="MOVIE", focus_mode="MF", af_assist_active=True
            ).passed
        )
        self.assertFalse(
            evaluate_p291_check_group_c_sensor_clean_ev_focus_playback(
                shoot_mode="PHOTO", focus_mode="AF_C", af_assist_active=True
            ).passed
        )
        self.assertFalse(
            evaluate_p291_check_group_c_sensor_clean_ev_focus_playback(
                reset_action="CAMERA_SETTINGS_RESET",
                claimed_priority_set_wiped_by_camera_reset=True,
            ).passed
        )

    def test_52_gc_playback_view_mode_3modes_rejects_dormant_mp4_avchd(self) -> None:
        for vm in P291_VIEW_MODE_THREE_MODES:
            self.assertTrue(
                evaluate_p291_check_group_c_sensor_clean_ev_focus_playback(
                    view_mode=vm
                ).passed
            )
        for bad_vm in P291_DORMANT_VIEW_MODES:
            gc = evaluate_p291_check_group_c_sensor_clean_ev_focus_playback(
                exposed_view_modes=P291_VIEW_MODE_THREE_MODES + (bad_vm,)
            )
            self.assertFalse(gc.passed)
            self.assertTrue(
                any(P291_GC_ERR_PLAYBACK_INDEX_OR_SLOT1_ROTATE_FIREWALL in e for e in gc.errors)
            )

    def test_53_gc_playback_image_index_9_25_only_rejects_dormant_12_30(self) -> None:
        for idx in P291_IMAGE_INDEX_TWO_MODES:
            self.assertTrue(
                evaluate_p291_check_group_c_sensor_clean_ev_focus_playback(
                    image_index_mode=idx
                ).passed
            )
        for bad_idx in P291_DORMANT_IMAGE_INDEX_MODES:
            self.assertFalse(
                evaluate_p291_check_group_c_sensor_clean_ev_focus_playback(
                    image_index_mode=bad_idx
                ).passed
            )
            self.assertFalse(
                evaluate_p291_check_group_c_sensor_clean_ev_focus_playback(
                    exposed_image_index_modes=P291_IMAGE_INDEX_TWO_MODES + (bad_idx,)
                ).passed
            )

    def test_54_gc_display_as_group_display_rotation_and_reset_survival(self) -> None:
        self.assertTrue(
            evaluate_p291_check_group_c_sensor_clean_ev_focus_playback(
                display_as_group="ON", display_rotation="MANUAL"
            ).passed
        )
        self.assertFalse(
            evaluate_p291_check_group_c_sensor_clean_ev_focus_playback(
                reset_action="CAMERA_SETTINGS_RESET",
                claimed_playback_view_prefs_wiped_by_camera_reset=True,
            ).passed
        )

    def test_55_gc_playback_rotate_blocked_on_slot1_tier0_vault(self) -> None:
        gc = evaluate_p291_check_group_c_sensor_clean_ev_focus_playback(
            playback_media_slot=1,
            slot1_contains_tier0_dump=True,
            playback_rotate_requested=True,
        )
        self.assertFalse(gc.passed)
        self.assertFalse(gc.playback_rotate_slot1_firewall_enforced)
        self.assertTrue(
            any(P291_GC_ERR_PLAYBACK_INDEX_OR_SLOT1_ROTATE_FIREWALL in e for e in gc.errors)
        )

    def test_56_gc_playback_rotate_blocked_on_movie_or_transfer_allowed_idle_still_slot2(self) -> None:
        self.assertTrue(
            evaluate_p291_check_group_c_sensor_clean_ev_focus_playback(
                playback_media_slot=2,
                slot1_contains_tier0_dump=True,
                playback_rotate_requested=True,
            ).passed
        )
        self.assertFalse(
            evaluate_p291_check_group_c_sensor_clean_ev_focus_playback(
                playback_media_slot=2,
                playback_rotate_requested=True,
                playback_rotate_on_movie=True,
            ).passed
        )
        self.assertFalse(
            evaluate_p291_check_group_c_sensor_clean_ev_focus_playback(
                playback_media_slot=2,
                playback_rotate_requested=True,
                playback_rotate_during_transfer=True,
            ).passed
        )

    def test_57_gc_sensor_cleaning_resid16_0x67d6_verified(self) -> None:
        self.assertFalse(
            evaluate_p291_check_group_c_sensor_clean_ev_focus_playback(
                sensor_cleaning_resid16_hex="0xdead"
            ).passed
        )

    # --- Section 5: Check Group D & Tier-0 Dual-Media Receipts (8 tests) ---

    def test_58_gd_16_of_16_h0_h3_zero_drift_passes_and_any_drift_fails(self) -> None:
        gd_ok, _ = evaluate_p291_check_group_d_physical_bench_and_tier0(
            simulate_bench_dry_run=True
        )
        self.assertTrue(gd_ok.passed)
        self.assertEqual(gd_ok.h0_h3_surface_count, 16)
        self.assertEqual(gd_ok.h0_equals_h3_count, 16)

        gd_bad, _ = evaluate_p291_check_group_d_physical_bench_and_tier0(
            simulate_bench_dry_run=True, simulated_h0_h3_drifted_surfaces=2
        )
        self.assertFalse(gd_bad.passed)
        self.assertEqual(gd_bad.h0_equals_h3_count, 14)
        self.assertTrue(any(P291_GD_ERR_H0_H3_IMMUTABILITY_DRIFT in e for e in gd_bad.errors))

    def test_59_gd_passive_tx_nonzero_or_redline_claims_fail_closed(self) -> None:
        for kw in (
            {"simulated_passive_tx_bytes": 1},
            {"claim_hardware_live_attach_authorized": True},
            {"claim_persistent_emmc_writes_authorized": True},
            {"claim_cross_model_flash_authorized": True},
        ):
            gd, _ = evaluate_p291_check_group_d_physical_bench_and_tier0(**kw)
            self.assertFalse(gd.passed)
            self.assertFalse(gd.overall_ready_for_hardware_attach)
            self.assertFalse(gd.persistent_emmc_writes_authorized)
            self.assertFalse(gd.cross_model_flash_authorized)
            self.assertTrue(
                any(P291_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION in e for e in gd.errors)
            )

    def test_60_gd_offline_no_receipts_fails_closed_awaiting_receipts(self) -> None:
        gd, t_errs = evaluate_p291_check_group_d_physical_bench_and_tier0(
            simulate_bench_dry_run=False
        )
        self.assertTrue(gd.passed)
        self.assertFalse(gd.tier0_receipt_present)
        self.assertFalse(gd.tier0_receipt_verified)
        self.assertFalse(gd.overall_ready_for_hardware_attach)
        self.assertTrue(
            any(P291_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID in e for e in t_errs)
        )

    def test_61_gd_simulated_bench_dry_run_verifies_528b_receipts_and_keeps_attach_false(self) -> None:
        gd, t_errs = evaluate_p291_check_group_d_physical_bench_and_tier0(
            simulate_bench_dry_run=True
        )
        self.assertTrue(gd.passed)
        self.assertEqual(len(t_errs), 0)
        self.assertTrue(gd.tier0_receipt_present)
        self.assertTrue(gd.tier0_receipt_verified)
        self.assertTrue(gd.distinct_physical_media_verified)
        self.assertFalse(gd.overall_ready_for_hardware_attach)

    def test_62_gd_valid_dual_device_file_receipts_reach_verified_verdict_still_no_attach(self) -> None:
        ra, rb, baselines = build_simulated_phase291_tier0_receipts()
        with tempfile.TemporaryDirectory() as td:
            pa = Path(td) / "copy_a.bin"
            pb = Path(td) / "copy_b.bin"
            pa.write_bytes(ra)
            pb.write_bytes(rb)
            rep = evaluate_realhw_focus_area_zoom_dci4k_and_sensor_cleaning_readiness(
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
            P291_GO_NO_GO_FOCUS_AREA_ZOOM_DCI4K_SENSOR_CLEANING_VERIFIED,
        )
        self.assertTrue(rep.tier0_receipt_verified)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertTrue(verify_phase291_report(rep.to_dict()).valid)

    def test_63_gd_same_st_dev_or_single_copy_or_byte_mismatch_rejected(self) -> None:
        ra, rb, baselines = build_simulated_phase291_tier0_receipts()
        # Same st_dev rejected
        gd1, err1 = evaluate_p291_check_group_d_physical_bench_and_tier0(
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

        # Byte mismatch rejected
        gd2, err2 = evaluate_p291_check_group_d_physical_bench_and_tier0(
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

        # Single copy rejected
        gd3, _ = evaluate_p291_check_group_d_physical_bench_and_tier0(
            receipt_a_bytes=ra
        )
        self.assertFalse(gd3.tier0_receipt_verified)

    def test_64_gd_bad_serial_bad_cid_or_missing_h0_baselines_rejected(self) -> None:
        ra, rb, baselines = build_simulated_phase291_tier0_receipts()
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
            gd, _ = evaluate_p291_check_group_d_physical_bench_and_tier0(
                receipt_a_bytes=ra,
                receipt_b_bytes=rb,
                st_dev_a_override=11,
                st_dev_b_override=22,
                **kw,
            )
            self.assertFalse(gd.tier0_receipt_verified)

    def test_65_gd_corrupted_fx3rcpt1_crc_or_target_fw_mismatch_rejected(self) -> None:
        ra, _, baselines = build_simulated_phase291_tier0_receipts()
        corrupted = bytearray(ra)
        corrupted[-1] ^= 0x5A
        gd_crc, _ = evaluate_p291_check_group_d_physical_bench_and_tier0(
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

        gd_fw, _ = evaluate_p291_check_group_d_physical_bench_and_tier0(
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

    # --- Section 6: Top-Level Orchestrator, Report Verifier & Markdown (5 tests) ---

    def test_66_orchestrator_offline_and_dry_run_deterministic_json_and_sha256(self) -> None:
        rep_off = evaluate_realhw_focus_area_zoom_dci4k_and_sensor_cleaning_readiness(
            force_clean_room=True, simulate_bench_dry_run=False
        )
        self.assertEqual(
            rep_off.overall_status,
            P291_OVERALL_READY_OFFLINE_AWAITING_BENCH_RECEIPTS,
        )
        self.assertEqual(
            rep_off.go_no_go,
            GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT,
        )
        self.assertTrue(rep_off.all_4_check_groups_passed)
        self.assertFalse(rep_off.tier0_receipt_verified)

        rep_a = run_focus_area_zoom_dci4k_and_sensor_cleaning_preflight(
            force_clean_room=True, simulate_bench_dry_run=True
        )
        rep_b = run_focus_area_zoom_dci4k_and_sensor_cleaning_preflight(
            force_clean_room=True, simulate_bench_dry_run=True
        )
        self.assertEqual(rep_a.go_no_go, GO_NO_GO_DRY_RUN_SIMULATED_READY)
        self.assertEqual(rep_a.report_sha256, rep_b.report_sha256)
        self.assertEqual(rep_a.check_groups_passed, 4)
        self.assertTrue(verify_phase291_report(rep_a.to_dict()).valid)
        self.assertTrue(verify_phase291_report(rep_off.to_dict()).valid)

    def test_67_orchestrator_group_failures_propagate_to_blocked_verdict(self) -> None:
        rep = evaluate_realhw_focus_area_zoom_dci4k_and_sensor_cleaning_readiness(
            force_clean_room=True,
            simulate_bench_dry_run=True,
            xlr_h1_zoom_lever_present=True,
        )
        self.assertEqual(
            rep.go_no_go,
            P291_GO_NO_GO_BLOCKED_FOCUS_AREA_ZOOM_DCI4K_SENSOR_CLEANING_FAILURE,
        )
        self.assertEqual(rep.check_groups_passed, 3)
        self.assertFalse(rep.all_4_check_groups_passed)
        self.assertTrue(verify_phase291_report(rep.to_dict()).valid)

    def test_68_verify_phase291_report_tamper_detection_locks_zeroes_and_sha(self) -> None:
        rep = evaluate_realhw_focus_area_zoom_dci4k_and_sensor_cleaning_readiness(
            force_clean_room=True, simulate_bench_dry_run=True
        )
        base = rep.to_dict()
        self.assertTrue(verify_phase291_report(base).valid)

        for lock_key in (
            "overall_ready_for_hardware_attach",
            "hardware_live_attachment_authorized",
            "persistent_emmc_writes_authorized",
            "cross_model_flash_authorized",
            "xlr_h1_zoom_lever_present",
            "fx3_private_sony_pro_camera_used",
        ):
            tampered = dict(base)
            tampered[lock_key] = True
            self.assertFalse(verify_phase291_report(tampered).valid)

        for zero_key in (
            "usb_packets_transmitted",
            "raw_firmware_bytes_leaked",
            "passive_tx_bytes_emitted",
        ):
            tampered = dict(base)
            tampered[zero_key] = 1
            self.assertFalse(verify_phase291_report(tampered).valid)

        tampered_sha = dict(base)
        tampered_sha["report_sha256"] = "a" * 64
        self.assertFalse(verify_phase291_report(tampered_sha).valid)

    def test_69_verify_phase291_report_rejects_simulated_dry_run_claiming_physical_verified(self) -> None:
        rep = evaluate_realhw_focus_area_zoom_dci4k_and_sensor_cleaning_readiness(
            force_clean_room=True, simulate_bench_dry_run=True
        )
        bad = rep.to_dict()
        bad["go_no_go"] = P291_GO_NO_GO_FOCUS_AREA_ZOOM_DCI4K_SENSOR_CLEANING_VERIFIED
        self.assertFalse(verify_phase291_report(bad).valid)

    def test_70_render_phase291_markdown_contains_all_4_groups_and_locks(self) -> None:
        rep = evaluate_realhw_focus_area_zoom_dci4k_and_sensor_cleaning_readiness(
            force_clean_room=True, simulate_bench_dry_run=True
        )
        md = render_phase291_markdown(rep)
        for token in (
            P291_SCHEMA,
            P291_CHECK_GROUP_A_ID,
            P291_CHECK_GROUP_B_ID,
            P291_CHECK_GROUP_C_ID,
            P291_CHECK_GROUP_D_ID,
            "ready_attach=False",
            "emmc_writes=False",
            "leaked_bytes=0",
            rep.report_sha256,
        ):
            self.assertIn(token, md)

    # --- Section 7: CLI Integration Tests via sys.executable (6 tests) ---

    def test_71_cli_help_cleanly_escapes_percent_in_python3(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "fx6_closure",
                "preflight-focus-area-zoom-dci4k-and-sensor-cleaning",
                "--help",
            ],
            cwd=REPO_ROOT,
            env=_subprocess_env(clean_room=True),
            capture_output=True,
            text=True,
            timeout=_ci_subprocess_timeout(),
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        self.assertIn("51%", proc.stdout)
        self.assertIn("%c:%s/SONY/SETTING/%s/", proc.stdout)

    def test_72_cli_offline_exits_2_with_ready_offline_awaiting_bench_receipts(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "fx6_closure",
                "preflight-focus-area-zoom-dci4k-and-sensor-cleaning",
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
            P291_OVERALL_READY_OFFLINE_AWAITING_BENCH_RECEIPTS,
        )
        self.assertEqual(
            payload["go_no_go"],
            GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT,
        )
        self.assertTrue(verify_phase291_report(payload).valid)

    def test_73_cli_simulate_bench_dry_run_json_and_summary_exit_0(self) -> None:
        t0 = time.perf_counter()
        proc_json = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "fx6_closure",
                "preflight-focus-area-zoom-dci4k-and-sensor-cleaning",
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
        self.assertTrue(verify_phase291_report(payload).valid)

        proc_sum = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "fx6_closure",
                "preflight-focus-area-zoom-dci4k-and-sensor-cleaning",
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

    def test_74_cli_clean_room_simulate_bench_dry_run_markdown_and_output_files(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            out_json = Path(td) / "p291.json"
            out_md = Path(td) / "p291.md"
            proc = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    "-m",
                    "fx6_closure",
                    "preflight-focus-area-zoom-dci4k-and-sensor-cleaning",
                    "--clean-room",
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
            data = json.loads(out_json.read_text(encoding="utf-8"))
            self.assertEqual(data["verification_mode"], "CLEAN_ROOM_SYNTHETIC")
            self.assertTrue(verify_phase291_report(data).valid)
            self.assertIn(data["report_sha256"], out_md.read_text(encoding="utf-8"))

    def test_75_cli_dual_device_physical_receipt_files_via_main_fails_same_st_dev_in_tmp(self) -> None:
        # In a single TemporaryDirectory both files share st_dev; verify fail-closed st_dev check via CLI.
        ra, rb, _ = build_simulated_phase291_tier0_receipts()
        with tempfile.TemporaryDirectory() as td:
            pa = Path(td) / "rcpt_a.bin"
            pb = Path(td) / "rcpt_b.bin"
            pa.write_bytes(ra)
            pb.write_bytes(rb)
            proc = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    "-m",
                    "fx6_closure",
                    "preflight-focus-area-zoom-dci4k-and-sensor-cleaning",
                    "--clean-room",
                    "--receipt-a",
                    str(pa),
                    "--receipt-b",
                    str(pb),
                    "--body-serial",
                    DEFAULT_TARGET_BODY_SERIAL,
                    "--emmc-cid",
                    DEFAULT_TARGET_EMMC_CID,
                    "--json",
                ],
                cwd=REPO_ROOT,
                env=_subprocess_env(clean_room=True),
                capture_output=True,
                text=True,
                timeout=_ci_subprocess_timeout(),
            )
        self.assertEqual(proc.returncode, 2)
        payload = json.loads(proc.stdout)
        self.assertEqual(
            payload["go_no_go"],
            P291_GO_NO_GO_BLOCKED_FOCUS_AREA_ZOOM_DCI4K_SENSOR_CLEANING_FAILURE,
        )
        self.assertTrue(any("st_dev_a == st_dev_b" in e for e in payload["errors"]))

    def test_76_cli_negative_controls_xlr_h1_zoom_dci4k_24p_cleaning_low_soc_exit_2(self) -> None:
        for bad_flags in (
            ["--xlr-h1-zoom-lever-present"],
            ["--rec-frame-rate", "24.00P"],
            ["--sensor-cleaning-requested", "--battery-soc-pct", "49.0"],
            ["--playback-rotate-requested", "--playback-media-slot", "1"],
        ):
            proc = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    "-m",
                    "fx6_closure",
                    "preflight-focus-area-zoom-dci4k-and-sensor-cleaning",
                    "--clean-room",
                    "--simulate-bench-dry-run",
                    "--json",
                    *bad_flags,
                ],
                cwd=REPO_ROOT,
                env=_subprocess_env(clean_room=True),
                capture_output=True,
                text=True,
                timeout=_ci_subprocess_timeout(),
            )
            self.assertEqual(proc.returncode, 2, msg=f"Expected exit 2 for {bad_flags}")
            payload = json.loads(proc.stdout)
            self.assertEqual(
                payload["go_no_go"],
                P291_GO_NO_GO_BLOCKED_FOCUS_AREA_ZOOM_DCI4K_SENSOR_CLEANING_FAILURE,
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
