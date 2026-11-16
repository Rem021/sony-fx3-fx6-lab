"""Dual-mode unit tests (64 cases) for Phase 261 (`preflight-diffset-customkey-autoslow-and-apsc`):
6th Physical Bench & Pre-Shoot Readiness Verifier across Waves 40–43 check groups (`A..D`).

Runs deterministically in both `LOCAL_DONOR_O_RDONLY` and `FX3_FX6_FORCE_CLEAN_ROOM=1`
modes with zero `.pyc` emission, zero persistent writes, and `< 1.0s` runtime.
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import io
import json
import os
from pathlib import Path
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
    DONOR_INSPECTION_MAX_SECONDS,
    GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT,
    GO_NO_GO_DRY_RUN_SIMULATED_READY,
)
from fx6_closure.realhw_diffset_customkey_autoslow_and_apsc_verifier import (  # noqa: E402
    P261_4K_MOVIE_FILE_FORMATS,
    P261_AUTO_SLOW_SHUTTER_SIX_LOCKOUTS,
    P261_CHECK_GROUP_A_ID,
    P261_CHECK_GROUP_B_ID,
    P261_CHECK_GROUP_C_ID,
    P261_CHECK_GROUP_D_ID,
    P261_COMMON_TO_SEPARATE_STILL_ONLY_EXCEPTION,
    P261_COPYRIGHT_INFO_FOUR_SUBITEMS,
    P261_COPYRIGHT_INFO_MAX_CHARS,
    P261_CUSTOM_KEY_THREE_DOMAINS,
    P261_DEFAULT_CONTROL_WHEEL_ASSIGNMENT,
    P261_DEFAULT_FRONT_DIAL_ASSIGNMENT,
    P261_DEFAULT_REAR_DIAL_ASSIGNMENT,
    P261_DIFF_SET_EIGHT_ITEMS,
    P261_FACE_EYE_AF_FOUR_ITEMS,
    P261_GA_ERR_CUSTOM_KEY_3DOMAIN_ISO_EI_OR_SLOT1_VAULT_FIREWALL,
    P261_GA_ERR_DIFF_SET_8ITEMS_TRANSITION_OR_SHUTTER_ANGLE_OVERRIDE,
    P261_GA_ERR_MODEL_OR_FW_FLOOR,
    P261_GA_ERR_REMAIN_SHOOT_STILL_BUFFER_OR_EVFLESS_TOPOLOGY,
    P261_GB_ERR_AUTO_SLOW_SHUTTER_6LOCKS_OR_SHUTTER_ANGLE_OVERLAP,
    P261_GB_ERR_BREATHING_COMP_MOVIE_ONLY_LENS_RAW_OR_240P_LOCKOUT,
    P261_GB_ERR_HDMI_REC_CTRL_TC_PREREQ_4CH_OR_MEDIA_VAULT_GUARD,
    P261_GC_ERR_APSC_S35_12MP_4K_OR_HDMI_RAW_LOCKOUT,
    P261_GC_ERR_FACE_EYE_AF_MENU_OR_CLEAN_HDMI_FRAME_ISOLATION,
    P261_GC_ERR_VERSION_READONLY_OR_HARD_BLOCKED_BODYDATA_FLASH,
    P261_GD_ERR_COPYRIGHT_INFO_46CHAR_STILL_EXIF_OR_PII_HYGIENE,
    P261_GD_ERR_H0_H3_IMMUTABILITY_DRIFT,
    P261_GD_ERR_RELEASE_WO_CARD_STILL_MOVIE_GATE_OR_WO_LENS_END_ZERO,
    P261_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID,
    P261_GD_ERR_V702_AUDIO_5ITEM_MENU_OR_DISP_METER_SPLIT,
    P261_GO_NO_GO_BLOCKED_DIFFSET_CUSTOMKEY_AUTOSLOW_APSC_FAILURE,
    P261_GO_NO_GO_DIFFSET_CUSTOMKEY_AUTOSLOW_APSC_VERIFIED,
    P261_HD_MOVIE_FILE_FORMATS,
    P261_SEPARATE_TO_COMMON_STILL_RETAINED_ITEMS,
    P261_SONY_HELP_GUIDE_ID,
    P261_V702_AUDIO_RECORDING_FIVE_ITEMS,
    PHASE_261_CHECK_GROUP_IDS,
    PHASE_261_SCHEMA,
    PHASE_261_VERSION,
    build_simulated_phase261_tier0_receipts,
    evaluate_p261_check_group_a_diffset_customkey_and_evfless,
    evaluate_p261_check_group_b_autoslow_hdmi_rec_ctrl_and_breathing,
    evaluate_p261_check_group_c_apsc_s35_face_eye_af_and_version,
    evaluate_p261_check_group_d_release_wo_card_audio_copyright_and_tier0,
    evaluate_realhw_diffset_customkey_autoslow_and_apsc_readiness,
    inspect_phase261_donors_bounded,
    render_phase261_markdown,
    run_diffset_customkey_autoslow_and_apsc_preflight,
    verify_phase261_report,
)
from fx6_closure.realhw_sd_stageb_bundle_and_uninstaller import (  # noqa: E402
    DEFAULT_TARGET_BODY_SERIAL,
    DEFAULT_TARGET_EMMC_CID,
)


class TestPhase261DiffSetCustomKeyAutoSlowApscVerifier(unittest.TestCase):
    """64 deterministic dual-mode unit tests for Phase 261 6th physical bench verifier."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._suite_t0 = time.perf_counter()

    @classmethod
    def tearDownClass(cls) -> None:
        elapsed = time.perf_counter() - cls._suite_t0
        assert elapsed < 1.0, f"Phase 261 test suite exceeded <1.0s budget: {elapsed:.3f}s"

    # --- Group 0: Exports, Bounded Donor O_RDONLY & Clean-Room Parity (6 tests) ---

    def test_01_public_p261_symbols_exported_without_shadowing_prior_phases(self) -> None:
        self.assertEqual(
            PHASE_261_SCHEMA,
            "realhw_diffset_customkey_autoslow_and_apsc_verifier_v1",
        )
        self.assertEqual(PHASE_261_VERSION, "261.0.0")
        for sym in (
            "PHASE_261_SCHEMA",
            "PHASE_261_VERSION",
            "P261_CHECK_GROUP_A_ID",
            "P261_CHECK_GROUP_B_ID",
            "P261_CHECK_GROUP_C_ID",
            "P261_CHECK_GROUP_D_ID",
            "evaluate_realhw_diffset_customkey_autoslow_and_apsc_readiness",
            "run_diffset_customkey_autoslow_and_apsc_preflight",
            "verify_phase261_report",
            "render_phase261_markdown",
        ):
            self.assertIn(sym, fx6_closure.__all__)
            self.assertTrue(hasattr(fx6_closure, sym))
        # Verify non-shadowing of Phase 227 and Phase 248 exports
        self.assertEqual(
            fx6_closure.CHECK_GROUP_A_ID,
            "GROUP_A_PIXEL_MAPPING_CNFLASHA_RO_AND_NTSCPAL_GAMMA_SPLIT",
        )
        self.assertEqual(
            fx6_closure.P248_CHECK_GROUP_A_ID,
            "GROUP_A_RECOVER_IMAGEDB_BATTERY_SLOT1_VAULT_AND_MONITOR_FLIP",
        )
        self.assertIs(
            run_diffset_customkey_autoslow_and_apsc_preflight,
            evaluate_realhw_diffset_customkey_autoslow_and_apsc_readiness,
        )
        self.assertEqual(
            PHASE_261_CHECK_GROUP_IDS,
            (
                P261_CHECK_GROUP_A_ID,
                P261_CHECK_GROUP_B_ID,
                P261_CHECK_GROUP_C_ID,
                P261_CHECK_GROUP_D_ID,
            ),
        )

    def test_02_donor_inspection_respects_150ms_budget_default_mode(self) -> None:
        res = inspect_phase261_donors_bounded()
        self.assertTrue(res.passed)
        self.assertTrue(res.read_only_o_rdonly_enforced)
        self.assertTrue(res.within_150ms_budget)
        self.assertLess(res.elapsed_seconds, DONOR_INSPECTION_MAX_SECONDS)
        self.assertIn(res.verification_mode, ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"))

    def test_03_donor_inspection_clean_room_synthetic_mode_and_env_override(self) -> None:
        res = inspect_phase261_donors_bounded(force_clean_room=True)
        self.assertTrue(res.passed)
        self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(len(res.inspected_artifacts), 6)
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            env_res = inspect_phase261_donors_bounded()
            self.assertEqual(env_res.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_04_donor_inspection_fails_closed_when_forced_live_missing_donors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            res = inspect_phase261_donors_bounded(
                fx6_lib_dir=Path(tmp) / "missing_fx6",
                fx3_modules_dir=Path(tmp) / "missing_fx3",
                force_clean_room=False,
            )
        self.assertFalse(res.passed)
        self.assertEqual(res.verification_mode, "LOCAL_DONOR_O_RDONLY")
        self.assertGreaterEqual(len(res.errors), 1)

    def test_05_donor_inspection_zero_raw_firmware_bytes_leaked(self) -> None:
        for clean in (None, True):
            res = inspect_phase261_donors_bounded(force_clean_room=clean)
            self.assertEqual(res.raw_firmware_bytes_leaked, 0)

    def test_06_sony_help_guide_id_ilc_2210_and_model_fw_floor_enforced(self) -> None:
        bad_guide = evaluate_p261_check_group_a_diffset_customkey_and_evfless(
            sony_help_guide_id="ilc/2035"
        )
        self.assertFalse(bad_guide.passed)
        self.assertTrue(any(P261_GA_ERR_MODEL_OR_FW_FLOOR in e for e in bad_guide.errors))

        bad_fw = evaluate_p261_check_group_a_diffset_customkey_and_evfless(body_fw="2.00")
        self.assertFalse(bad_fw.passed)
        self.assertTrue(any(P261_GA_ERR_MODEL_OR_FW_FLOOR in e for e in bad_fw.errors))

        bad_model = evaluate_p261_check_group_a_diffset_customkey_and_evfless(
            body_model_id=0x91030099
        )
        self.assertFalse(bad_model.passed)

    # --- Group A: Wave 40 Different Set / Custom Key / EVF-Less (16 tests) ---

    def test_07_group_a_nominal_diff_set_8items_and_custom_key_passes(self) -> None:
        ga = evaluate_p261_check_group_a_diffset_customkey_and_evfless()
        self.assertTrue(ga.passed)
        self.assertEqual(ga.sony_help_guide_id, P261_SONY_HELP_GUIDE_ID)
        self.assertEqual(len(ga.diff_set_eight_items), 8)
        self.assertEqual(ga.diff_set_eight_items, P261_DIFF_SET_EIGHT_ITEMS)
        self.assertEqual(ga.slot1_custom_key_vault_mutation_bytes, 0)
        self.assertFalse(ga.fx3_has_builtin_evf)
        self.assertFalse(ga.fx3_has_finder_monitor_switch)

    def test_08_group_a_rejects_wrong_diff_set_8item_list(self) -> None:
        ga = evaluate_p261_check_group_a_diffset_customkey_and_evfless(
            diff_set_items=P261_DIFF_SET_EIGHT_ITEMS[:-1]
        )
        self.assertFalse(ga.passed)
        self.assertTrue(
            any(P261_GA_ERR_DIFF_SET_8ITEMS_TRANSITION_OR_SHUTTER_ANGLE_OVERRIDE in e for e in ga.errors)
        )

    def test_09_group_a_blocks_custom_wb_copied_to_movie_on_common_to_separate(self) -> None:
        ga = evaluate_p261_check_group_a_diffset_customkey_and_evfless(
            diff_set_transition="COMMON_TO_SEPARATE",
            expect_custom_wb_copied_to_movie_on_common_to_separate=True,
        )
        self.assertFalse(ga.passed)
        self.assertEqual(
            ga.common_to_separate_still_only_exception,
            P261_COMMON_TO_SEPARATE_STILL_ONLY_EXCEPTION,
        )

    def test_10_group_a_verifies_separate_to_common_retains_aperture_shutter_cwb(self) -> None:
        ga = evaluate_p261_check_group_a_diffset_customkey_and_evfless(
            diff_set_transition="SEPARATE_TO_COMMON",
        )
        self.assertTrue(ga.passed)
        self.assertEqual(
            ga.separate_to_common_still_retained_items,
            ("Aperture", "Shutter Speed", "Custom White Balance"),
        )
        self.assertEqual(
            ga.separate_to_common_still_retained_items,
            P261_SEPARATE_TO_COMMON_STILL_RETAINED_ITEMS,
        )

    def test_11_group_a_blocks_all_items_factory_reset_claim_on_separate_to_common(self) -> None:
        ga = evaluate_p261_check_group_a_diffset_customkey_and_evfless(
            diff_set_transition="SEPARATE_TO_COMMON",
            expect_all_items_factory_reset_on_separate_to_common=True,
        )
        self.assertFalse(ga.passed)
        bad_retained = evaluate_p261_check_group_a_diffset_customkey_and_evfless(
            separate_to_common_retained_items=("Aperture", "ISO")
        )
        self.assertFalse(bad_retained.passed)

    def test_12_group_a_shutter_angle_independent_even_when_shutter_speed_unchecked(self) -> None:
        ga = evaluate_p261_check_group_a_diffset_customkey_and_evfless(
            diff_set_shutter_speed_checked=False,
            movie_shutter_mode="SHUTTER_ANGLE",
        )
        self.assertTrue(ga.passed)
        self.assertTrue(ga.shutter_angle_independent_from_still_shutter)

    def test_13_group_a_blocks_claim_that_common_shutter_merges_movie_shutter_angle(self) -> None:
        ga = evaluate_p261_check_group_a_diffset_customkey_and_evfless(
            diff_set_shutter_speed_checked=False,
            movie_shutter_mode="SHUTTER_ANGLE",
            expect_common_shutter_merges_movie_shutter_angle=True,
        )
        self.assertFalse(ga.passed)
        self.assertTrue(
            any(P261_GA_ERR_DIFF_SET_8ITEMS_TRANSITION_OR_SHUTTER_ANGLE_OVERRIDE in e for e in ga.errors)
        )

    def test_14_group_a_diff_set_survives_camera_settings_reset(self) -> None:
        ok = evaluate_p261_check_group_a_diffset_customkey_and_evfless(
            reset_action="CAMERA_SETTINGS_RESET",
            claimed_diff_set_reset_on_camera_reset=False,
        )
        self.assertTrue(ok.passed)
        bad = evaluate_p261_check_group_a_diffset_customkey_and_evfless(
            reset_action="CAMERA_SETTINGS_RESET",
            claimed_diff_set_reset_on_camera_reset=True,
        )
        self.assertFalse(bad.passed)

    def test_15_group_a_custom_key_3domain_cinema_dial_defaults_iso_ei(self) -> None:
        ga = evaluate_p261_check_group_a_diffset_customkey_and_evfless()
        self.assertEqual(ga.custom_key_domains, P261_CUSTOM_KEY_THREE_DOMAINS)
        self.assertEqual(ga.front_dial_assignment, P261_DEFAULT_FRONT_DIAL_ASSIGNMENT)
        self.assertEqual(ga.rear_dial_assignment, P261_DEFAULT_REAR_DIAL_ASSIGNMENT)
        self.assertEqual(ga.control_wheel_assignment, P261_DEFAULT_CONTROL_WHEEL_ASSIGNMENT)

    def test_16_group_a_blocks_non_iso_ei_rear_dial_or_invalid_domain_tuple(self) -> None:
        bad_dial = evaluate_p261_check_group_a_diffset_customkey_and_evfless(
            rear_dial_assignment="Exposure Comp."
        )
        self.assertFalse(bad_dial.passed)
        self.assertTrue(
            any(P261_GA_ERR_CUSTOM_KEY_3DOMAIN_ISO_EI_OR_SLOT1_VAULT_FIREWALL in e for e in bad_dial.errors)
        )
        bad_dom = evaluate_p261_check_group_a_diffset_customkey_and_evfless(
            custom_key_domains=("STILL", "MOVIE")
        )
        self.assertFalse(bad_dom.passed)

    def test_17_group_a_slot1_camset01_o_rdonly_firewall_blocks_write_or_unlocked_wp(self) -> None:
        wr = evaluate_p261_check_group_a_diffset_customkey_and_evfless(
            slot1_camset_custom_key_access_mode="WRITE"
        )
        self.assertFalse(wr.passed)
        self.assertGreater(wr.slot1_custom_key_vault_mutation_bytes, 0)

        unlocked = evaluate_p261_check_group_a_diffset_customkey_and_evfless(
            slot1_contains_tier0_dump=True,
            slot1_wp_locked=False,
            slot1_camset_custom_key_access_mode="O_RDONLY",
        )
        self.assertFalse(unlocked.passed)

    def test_18_group_a_slot1_custom_key_mutation_bytes_nonzero_fails_closed(self) -> None:
        ga = evaluate_p261_check_group_a_diffset_customkey_and_evfless(
            simulated_slot1_custom_key_mutation_bytes=64
        )
        self.assertFalse(ga.passed)
        self.assertEqual(ga.slot1_custom_key_vault_mutation_bytes, 64)

    def test_19_group_a_remain_shoot_display_modes_and_reset_survival(self) -> None:
        for mode in ("NOT_DISPLAYED", "ALWAYS_DISPLAY", "SHOOT_ONLY_DISPLAY"):
            ga = evaluate_p261_check_group_a_diffset_customkey_and_evfless(
                remain_shoot_display=mode,
                reset_action="CAMERA_SETTINGS_RESET",
                claimed_remain_shoot_after_reset=mode,
            )
            self.assertTrue(ga.passed)
        init_ga = evaluate_p261_check_group_a_diffset_customkey_and_evfless(
            remain_shoot_display="ALWAYS_DISPLAY",
            reset_action="INITIALIZE",
            claimed_remain_shoot_after_reset="NOT_DISPLAYED",
        )
        self.assertTrue(init_ga.passed)
        bad_rst = evaluate_p261_check_group_a_diffset_customkey_and_evfless(
            remain_shoot_display="ALWAYS_DISPLAY",
            reset_action="CAMERA_SETTINGS_RESET",
            claimed_remain_shoot_after_reset="NOT_DISPLAYED",
        )
        self.assertFalse(bad_rst.passed)

    def test_20_group_a_blocks_remain_shoot_display_movie_card_time_claim(self) -> None:
        ga = evaluate_p261_check_group_a_diffset_customkey_and_evfless(
            expect_remain_shoot_displays_movie_card_time=True
        )
        self.assertFalse(ga.passed)
        self.assertTrue(
            any(P261_GA_ERR_REMAIN_SHOOT_STILL_BUFFER_OR_EVFLESS_TOPOLOGY in e for e in ga.errors)
        )

    def test_21_group_a_enforces_evfless_fx3_ilc_2210_topology(self) -> None:
        ga = evaluate_p261_check_group_a_diffset_customkey_and_evfless(
            expect_builtin_evf_or_finder_monitor_switch=True
        )
        self.assertFalse(ga.passed)
        self.assertFalse(ga.fx3_has_builtin_evf)
        self.assertFalse(ga.fx3_has_finder_monitor_switch)

    def test_22_group_a_custom_key_survives_camera_settings_reset(self) -> None:
        ga = evaluate_p261_check_group_a_diffset_customkey_and_evfless(
            claimed_custom_key_reset_on_camera_reset=True
        )
        self.assertFalse(ga.passed)


    # --- Group B: Wave 41 Auto Slow Shutter / HDMI Output / Breathing Comp. (12 tests) ---

    def test_23_group_b_nominal_cine_ei_shutter_angle_bench_passes(self) -> None:
        gb = evaluate_p261_check_group_b_autoslow_hdmi_rec_ctrl_and_breathing()
        self.assertTrue(gb.passed)
        self.assertFalse(gb.auto_slow_shutter_effective_active)
        self.assertEqual(gb.auto_slow_shutter_angle_overlap_events, 0)
        self.assertEqual(gb.hdmi_rec_ctrl_without_tc_violations, 0)
        self.assertTrue(gb.slot1_hdmi_media_vault_protected)

    def test_24_group_b_auto_slow_shutter_active_in_program_auto_iso_auto_non_log(self) -> None:
        gb = evaluate_p261_check_group_b_autoslow_hdmi_rec_ctrl_and_breathing(
            auto_slow_shutter="ON",
            exposure_ctrl_type="P_A_S_M_MODE",
            exposure_mode="PROGRAM_AUTO",
            flexible_shutter_mode="AUTO",
            iso_mode="ISO_AUTO",
            log_shooting_mode="OFF",
            sq_mode_enabled=False,
            movie_shutter_mode="SHUTTER_SPEED",
            expect_auto_slow_shutter_active=True,
        )
        self.assertTrue(gb.passed)
        self.assertEqual(gb.active_auto_slow_shutter_lockouts, ())
        self.assertTrue(gb.auto_slow_shutter_effective_active)

    def test_25_group_b_verifies_all_6_individual_auto_slow_shutter_lockouts(self) -> None:
        base_kwargs = dict(
            auto_slow_shutter="ON",
            exposure_ctrl_type="P_A_S_M_MODE",
            exposure_mode="PROGRAM_AUTO",
            flexible_shutter_mode="AUTO",
            iso_mode="ISO_AUTO",
            log_shooting_mode="OFF",
            sq_mode_enabled=False,
            movie_shutter_mode="SHUTTER_SPEED",
        )
        cases = (
            ({"sq_mode_enabled": True}, "SQ_MOTION_SHOOTING"),
            ({"exposure_mode": "SHUTTER_PRIORITY"}, "SHUTTER_PRIORITY_S_MODE"),
            ({"exposure_mode": "MANUAL_EXPOSURE"}, "MANUAL_EXPOSURE_M_MODE"),
            ({"iso_mode": "ISO_800"}, "MANUAL_FIXED_ISO_NON_AUTO"),
            (
                {"exposure_ctrl_type": "FLEXIBLE_EXP_MODE", "flexible_shutter_mode": "MANUAL"},
                "FLEXIBLE_EXP_MANUAL_SHUTTER",
            ),
            ({"log_shooting_mode": "CINE_EI_QUICK"}, "LOG_SHOOTING_CINE_EI_OR_QUICK"),
        )
        seen = []
        for override, expected_lock in cases:
            cfg = {**base_kwargs, **override}
            gb = evaluate_p261_check_group_b_autoslow_hdmi_rec_ctrl_and_breathing(**cfg)
            self.assertTrue(gb.passed)
            self.assertIn(expected_lock, gb.active_auto_slow_shutter_lockouts)
            self.assertFalse(gb.auto_slow_shutter_effective_active)
            seen.append(expected_lock)
        self.assertEqual(tuple(seen), P261_AUTO_SLOW_SHUTTER_SIX_LOCKOUTS)

    def test_26_group_b_blocks_expect_auto_slow_active_under_any_of_6_lockouts(self) -> None:
        gb = evaluate_p261_check_group_b_autoslow_hdmi_rec_ctrl_and_breathing(
            expect_auto_slow_shutter_active=True
        )
        self.assertFalse(gb.passed)
        self.assertTrue(
            any(P261_GB_ERR_AUTO_SLOW_SHUTTER_6LOCKS_OR_SHUTTER_ANGLE_OVERLAP in e for e in gb.errors)
        )

    def test_27_group_b_enforces_auto_slow_shutter_and_shutter_angle_disjointness(self) -> None:
        overlap_claim = evaluate_p261_check_group_b_autoslow_hdmi_rec_ctrl_and_breathing(
            expect_auto_slow_shutter_with_shutter_angle=True
        )
        self.assertFalse(overlap_claim.passed)
        self.assertEqual(overlap_claim.auto_slow_shutter_angle_overlap_events, 1)

        illegal_angle = evaluate_p261_check_group_b_autoslow_hdmi_rec_ctrl_and_breathing(
            exposure_ctrl_type="P_A_S_M_MODE",
            exposure_mode="PROGRAM_AUTO",
            iso_mode="ISO_AUTO",
            log_shooting_mode="OFF",
            movie_shutter_mode="SHUTTER_ANGLE",
        )
        self.assertFalse(illegal_angle.passed)
        self.assertEqual(illegal_angle.auto_slow_shutter_angle_overlap_events, 1)

    def test_28_group_b_auto_slow_shutter_resets_to_on_under_camera_settings_reset(self) -> None:
        gb = evaluate_p261_check_group_b_autoslow_hdmi_rec_ctrl_and_breathing(
            auto_slow_shutter="OFF",
            reset_action="CAMERA_SETTINGS_RESET",
            claimed_auto_slow_after_reset="ON",
        )
        self.assertTrue(gb.passed)
        bad = evaluate_p261_check_group_b_autoslow_hdmi_rec_ctrl_and_breathing(
            auto_slow_shutter="OFF",
            reset_action="CAMERA_SETTINGS_RESET",
            claimed_auto_slow_after_reset="OFF",
        )
        self.assertFalse(bad.passed)

    def test_29_group_b_hdmi_rec_control_requires_mandatory_time_code_output_on(self) -> None:
        ok = evaluate_p261_check_group_b_autoslow_hdmi_rec_ctrl_and_breathing(
            hdmi_time_code_output="ON",
            hdmi_rec_control="ON",
        )
        self.assertTrue(ok.passed)
        self.assertEqual(ok.hdmi_rec_ctrl_without_tc_violations, 0)

        bad = evaluate_p261_check_group_b_autoslow_hdmi_rec_ctrl_and_breathing(
            hdmi_time_code_output="OFF",
            hdmi_rec_control="ON",
        )
        self.assertFalse(bad.passed)
        self.assertEqual(bad.hdmi_rec_ctrl_without_tc_violations, 1)
        self.assertTrue(
            any(P261_GB_ERR_HDMI_REC_CTRL_TC_PREREQ_4CH_OR_MEDIA_VAULT_GUARD in e for e in bad.errors)
        )

    def test_30_group_b_hdmi_4ch_audio_ch3_ch4_requires_4ch_mi_shoe_active(self) -> None:
        ok = evaluate_p261_check_group_b_autoslow_hdmi_rec_ctrl_and_breathing(
            hdmi_4ch_audio_output="CH3_CH4",
            mi_shoe_4ch_audio_active=True,
        )
        self.assertTrue(ok.passed)
        bad = evaluate_p261_check_group_b_autoslow_hdmi_rec_ctrl_and_breathing(
            hdmi_4ch_audio_output="CH3_CH4",
            mi_shoe_4ch_audio_active=False,
        )
        self.assertFalse(bad.passed)

    def test_31_group_b_rec_media_dur_hdmi_off_inhibits_internal_and_proxy_writes(self) -> None:
        bad = evaluate_p261_check_group_b_autoslow_hdmi_rec_ctrl_and_breathing(
            rec_media_dur_hdmi_output="OFF_HDMI_ONLY",
            expect_internal_or_proxy_rec_when_hdmi_media_off=True,
        )
        self.assertFalse(bad.passed)
        bad_rst = evaluate_p261_check_group_b_autoslow_hdmi_rec_ctrl_and_breathing(
            claimed_hdmi_settings_reset_on_camera_reset=True
        )
        self.assertFalse(bad_rst.passed)

    def test_32_group_b_slot1_tier0_vault_protected_during_hdmi_output(self) -> None:
        bad = evaluate_p261_check_group_b_autoslow_hdmi_rec_ctrl_and_breathing(
            slot1_contains_tier0_dump=True,
            internal_rec_to_slot1_during_hdmi=True,
        )
        self.assertFalse(bad.passed)
        self.assertFalse(bad.slot1_hdmi_media_vault_protected)

    def test_33_group_b_breathing_comp_compliant_lens_allowed_in_non_raw_movie(self) -> None:
        gb = evaluate_p261_check_group_b_autoslow_hdmi_rec_ctrl_and_breathing(
            breathing_comp="ON",
            breathing_comp_compliant_lens=True,
            hdmi_raw_output=False,
            sq_240p_or_200p_active=False,
        )
        self.assertTrue(gb.passed)

    def test_34_group_b_breathing_comp_blocked_on_noncompliant_lens_raw_240p_or_still(self) -> None:
        for bad_kw in (
            {"breathing_comp": "ON", "breathing_comp_compliant_lens": False},
            {"breathing_comp": "ON", "hdmi_raw_output": True},
            {"breathing_comp": "ON", "sq_240p_or_200p_active": True},
            {"expect_breathing_comp_in_still_image": True},
        ):
            gb = evaluate_p261_check_group_b_autoslow_hdmi_rec_ctrl_and_breathing(**bad_kw)
            self.assertFalse(gb.passed)
            self.assertTrue(
                any(
                    P261_GB_ERR_BREATHING_COMP_MOVIE_ONLY_LENS_RAW_OR_240P_LOCKOUT in e
                    for e in gb.errors
                )
            )

    # --- Group C: Wave 42 APS-C S35 4K Lockout / Face/Eye AF / Version RO (10 tests) ---

    def test_35_group_c_nominal_4k_locks_apsc_s35_off_zero_bypass(self) -> None:
        gc = evaluate_p261_check_group_c_apsc_s35_face_eye_af_and_version()
        self.assertTrue(gc.passed)
        self.assertTrue(gc.apsc_s35_4k_or_raw_locked_off)
        self.assertEqual(gc.effective_apsc_s35_movie_state, "OFF_4K_OR_RAW_LOCKOUT")
        self.assertEqual(gc.apsc_s35_4k_or_raw_bypass_events, 0)
        self.assertEqual(gc.hdmi_clean_feed_eye_frame_baked_pixels, 0)
        self.assertFalse(gc.bodydata_auto_flash_authorized)

    def test_36_group_c_blocks_apsc_s35_on_across_all_three_4k_xavc_formats(self) -> None:
        for fmt in P261_4K_MOVIE_FILE_FORMATS:
            gc = evaluate_p261_check_group_c_apsc_s35_face_eye_af_and_version(
                apsc_s35_shooting="ON",
                movie_file_format=fmt,
            )
            self.assertFalse(gc.passed)
            self.assertEqual(gc.apsc_s35_4k_or_raw_bypass_events, 1)
            self.assertTrue(
                any(P261_GC_ERR_APSC_S35_12MP_4K_OR_HDMI_RAW_LOCKOUT in e for e in gc.errors)
            )

    def test_37_group_c_blocks_apsc_s35_on_under_4264x2408_hdmi_raw_output(self) -> None:
        gc = evaluate_p261_check_group_c_apsc_s35_face_eye_af_and_version(
            apsc_s35_shooting="ON",
            movie_file_format="XAVC_S_HD",
            hdmi_raw_output=True,
        )
        self.assertFalse(gc.passed)
        self.assertEqual(gc.apsc_s35_4k_or_raw_bypass_events, 1)

    def test_38_group_c_allows_apsc_s35_on_exclusively_in_hd_movie_formats(self) -> None:
        for fmt in P261_HD_MOVIE_FILE_FORMATS:
            gc = evaluate_p261_check_group_c_apsc_s35_face_eye_af_and_version(
                apsc_s35_shooting="ON",
                movie_file_format=fmt,
                hdmi_raw_output=False,
            )
            self.assertTrue(gc.passed)
            self.assertFalse(gc.apsc_s35_4k_or_raw_locked_off)
            self.assertEqual(gc.effective_apsc_s35_movie_state, "ON_S35_HD_ALLOWED")

    def test_39_group_c_apsc_s35_resets_to_auto_on_camera_settings_reset(self) -> None:
        ok = evaluate_p261_check_group_c_apsc_s35_face_eye_af_and_version(
            apsc_s35_shooting="OFF",
            reset_action="CAMERA_SETTINGS_RESET",
            claimed_apsc_s35_after_reset="AUTO",
        )
        self.assertTrue(ok.passed)
        bad = evaluate_p261_check_group_c_apsc_s35_face_eye_af_and_version(
            apsc_s35_shooting="OFF",
            reset_action="CAMERA_SETTINGS_RESET",
            claimed_apsc_s35_after_reset="OFF",
        )
        self.assertFalse(bad.passed)

    def test_40_group_c_face_eye_af_4item_bionz_xr_hierarchy_and_right_left_eye(self) -> None:
        for subj in ("HUMAN", "ANIMAL", "BIRD"):
            for eye in ("AUTO", "RIGHT_EYE", "LEFT_EYE"):
                gc = evaluate_p261_check_group_c_apsc_s35_face_eye_af_and_version(
                    face_eye_subject=subj,
                    right_left_eye_select=eye,
                )
                self.assertTrue(gc.passed)
                self.assertEqual(gc.face_eye_af_four_items, P261_FACE_EYE_AF_FOUR_ITEMS)

    def test_41_group_c_rejects_dedicated_ai_unit_subject_recog_menu_and_iauto_prior_off(
        self,
    ) -> None:
        ai_claim = evaluate_p261_check_group_c_apsc_s35_face_eye_af_and_version(
            expect_dedicated_ai_subject_recog_menu=True
        )
        self.assertFalse(ai_claim.passed)
        iauto_off = evaluate_p261_check_group_c_apsc_s35_face_eye_af_and_version(
            exposure_mode="INTELLIGENT_AUTO",
            face_eye_prior_in_af="OFF",
        )
        self.assertFalse(iauto_off.passed)

    def test_42_group_c_face_memory_survives_camera_reset_and_clean_hdmi_zero_baked_px(
        self,
    ) -> None:
        bad_mem = evaluate_p261_check_group_c_apsc_s35_face_eye_af_and_version(
            claimed_face_memory_cleared_by_camera_reset=True
        )
        self.assertFalse(bad_mem.passed)
        bad_hdmi = evaluate_p261_check_group_c_apsc_s35_face_eye_af_and_version(
            expect_eye_frame_baked_on_clean_hdmi_or_raw=True
        )
        self.assertFalse(bad_hdmi.passed)
        self.assertGreater(bad_hdmi.hdmi_clean_feed_eye_frame_baked_pixels, 0)
        self.assertTrue(
            any(P261_GC_ERR_FACE_EYE_AF_MENU_OR_CLEAN_HDMI_FRAME_ISOLATION in e for e in bad_hdmi.errors)
        )

    def test_43_group_c_version_dialog_read_only_and_airplane_mode_suppresses_badge(self) -> None:
        gc = evaluate_p261_check_group_c_apsc_s35_face_eye_af_and_version()
        self.assertTrue(gc.version_dialog_read_only)
        self.assertTrue(gc.update_notification_suppressed)
        self.assertEqual(gc.passive_tx_bytes_emitted, 0)

    def test_44_group_c_hard_blocks_slot1_bodydata_dat_flash_and_rf_leakage(self) -> None:
        for bad_kw in (
            {"slot1_bodydata_flash_requested": True},
            {"expect_automated_bodydata_flash_allowed": True},
            {"airplane_mode": "OFF"},
            {"simulated_passive_tx_bytes": 12},
            {"simulated_version_dialog_flash_touches": 1},
        ):
            gc = evaluate_p261_check_group_c_apsc_s35_face_eye_af_and_version(**bad_kw)
            self.assertFalse(gc.passed)
            self.assertFalse(gc.bodydata_auto_flash_authorized)
            self.assertTrue(
                any(
                    P261_GC_ERR_VERSION_READONLY_OR_HARD_BLOCKED_BODYDATA_FLASH in e
                    for e in gc.errors
                )
            )


    # --- Group D, Orchestrator & CLI: Wave 43 + Tier-0 Gate (20 tests) ---

    def test_45_group_d_nominal_cardless_body_only_zero_end_bench_passes(self) -> None:
        gd, t0_err = evaluate_p261_check_group_d_release_wo_card_audio_copyright_and_tier0(
            simulate_bench_dry_run=True
        )
        self.assertTrue(gd.passed)
        self.assertEqual(t0_err, ())
        self.assertEqual(gd.e_nd_uart_bytes_transmitted, 0)
        self.assertEqual(gd.legacy_v1_audio_level_menu_spoof_events, 0)
        self.assertEqual(gd.photographer_copyright_pii_leaked_bytes, 0)
        self.assertEqual(gd.h0_equals_h3_count, 16)
        self.assertTrue(gd.tier0_receipt_verified)

    def test_46_group_d_release_wo_card_still_only_blocks_cardless_internal_movie_rec(
        self,
    ) -> None:
        cardless_still = evaluate_p261_check_group_d_release_wo_card_audio_copyright_and_tier0(
            release_wo_card="ENABLE",
            production_shoot_mode=False,
            movie_internal_rec_requested=False,
            simulate_bench_dry_run=True,
        )[0]
        self.assertTrue(cardless_still.passed)
        self.assertGreaterEqual(len(cardless_still.warnings), 1)

        bad_movie = evaluate_p261_check_group_d_release_wo_card_audio_copyright_and_tier0(
            release_wo_card="ENABLE",
            card_inserted_for_movie_rec=False,
            movie_internal_rec_requested=True,
            simulate_bench_dry_run=True,
        )[0]
        self.assertFalse(bad_movie.passed)
        self.assertTrue(
            any(
                P261_GD_ERR_RELEASE_WO_CARD_STILL_MOVIE_GATE_OR_WO_LENS_END_ZERO in e
                for e in bad_movie.errors
            )
        )

    def test_47_group_d_production_shoot_mode_requires_release_wo_card_disable(self) -> None:
        bad = evaluate_p261_check_group_d_release_wo_card_audio_copyright_and_tier0(
            release_wo_card="ENABLE",
            production_shoot_mode=True,
            simulate_bench_dry_run=True,
        )[0]
        self.assertFalse(bad.passed)
        ok = evaluate_p261_check_group_d_release_wo_card_audio_copyright_and_tier0(
            release_wo_card="DISABLE",
            production_shoot_mode=True,
            simulate_bench_dry_run=True,
        )[0]
        self.assertTrue(ok.passed)

    def test_48_group_d_release_wo_lens_zero_e_nd_uart_bytes_enforced(self) -> None:
        bad_lens_off = evaluate_p261_check_group_d_release_wo_card_audio_copyright_and_tier0(
            body_only_or_pl_adapter_bench=True,
            release_wo_lens="DISABLE",
            simulate_bench_dry_run=True,
        )[0]
        self.assertFalse(bad_lens_off.passed)

        bad_end = evaluate_p261_check_group_d_release_wo_card_audio_copyright_and_tier0(
            simulated_e_nd_uart_bytes=4,
            simulate_bench_dry_run=True,
        )[0]
        self.assertFalse(bad_end.passed)
        self.assertEqual(bad_end.e_nd_uart_bytes_transmitted, 4)

    def test_49_group_d_v702_audio_recording_exact_5_items_and_level_0_to_31(self) -> None:
        for lvl in (0, 16, 31):
            gd = evaluate_p261_check_group_d_release_wo_card_audio_copyright_and_tier0(
                audio_rec_level=lvl, simulate_bench_dry_run=True
            )[0]
            self.assertTrue(gd.passed)
            self.assertEqual(
                gd.v702_audio_recording_five_items, P261_V702_AUDIO_RECORDING_FIVE_ITEMS
            )
        for bad_lvl in (-1, 32):
            bad = evaluate_p261_check_group_d_release_wo_card_audio_copyright_and_tier0(
                audio_rec_level=bad_lvl, simulate_bench_dry_run=True
            )[0]
            self.assertFalse(bad.passed)

    def test_50_group_d_disp_audio_meter_integration_vs_absent_v1_audio_level_display(
        self,
    ) -> None:
        spoof = evaluate_p261_check_group_d_release_wo_card_audio_copyright_and_tier0(
            expect_standalone_v1_audio_level_display_menu=True,
            simulate_bench_dry_run=True,
        )[0]
        self.assertFalse(spoof.passed)
        self.assertEqual(spoof.legacy_v1_audio_level_menu_spoof_events, 1)
        self.assertTrue(
            any(P261_GD_ERR_V702_AUDIO_5ITEM_MENU_OR_DISP_METER_SPLIT in e for e in spoof.errors)
        )

    def test_51_group_d_audio_meter_suppressed_in_sq_mode(self) -> None:
        ok_sq = evaluate_p261_check_group_d_release_wo_card_audio_copyright_and_tier0(
            sq_mode_enabled=True,
            expect_audio_meter_in_sq_mode=False,
            simulate_bench_dry_run=True,
        )[0]
        self.assertTrue(ok_sq.passed)
        self.assertFalse(ok_sq.effective_audio_meter_visible)

        bad_sq = evaluate_p261_check_group_d_release_wo_card_audio_copyright_and_tier0(
            sq_mode_enabled=True,
            expect_audio_meter_in_sq_mode=True,
            simulate_bench_dry_run=True,
        )[0]
        self.assertFalse(bad_sq.passed)

    def test_52_group_d_copyright_info_write_off_and_46char_still_exif_hygiene(self) -> None:
        self.assertEqual(len(P261_COPYRIGHT_INFO_FOUR_SUBITEMS), 4)
        self.assertEqual(P261_COPYRIGHT_INFO_MAX_CHARS, 46)
        gd = evaluate_p261_check_group_d_release_wo_card_audio_copyright_and_tier0(
            write_copyright_info="OFF",
            photographer_text="A" * 46,
            copyright_text="B" * 46,
            clean_room_pii_hygiene_enforced=False,
            simulate_bench_dry_run=True,
        )[0]
        self.assertTrue(gd.passed)
        self.assertEqual(gd.photographer_copyright_pii_leaked_bytes, 0)

    def test_53_group_d_copyright_blocks_over_46chars_movie_exif_or_pii_leakage(self) -> None:
        for bad_kw in (
            {"photographer_text": "X" * 47, "clean_room_pii_hygiene_enforced": False},
            {"copyright_text": "Y" * 47, "clean_room_pii_hygiene_enforced": False},
            {"write_copyright_info": "ON", "photographer_text": "OperatorPII"},
            {"photographer_text": "OperatorPII", "clean_room_pii_hygiene_enforced": True},
            {"expect_copyright_exif_written_to_movies": True},
        ):
            gd = evaluate_p261_check_group_d_release_wo_card_audio_copyright_and_tier0(
                simulate_bench_dry_run=True, **bad_kw
            )[0]
            self.assertFalse(gd.passed)
            self.assertTrue(
                any(
                    P261_GD_ERR_COPYRIGHT_INFO_46CHAR_STILL_EXIF_OR_PII_HYGIENE in e
                    for e in gd.errors
                )
            )

    def test_54_group_d_copyright_strings_survive_camera_settings_reset(self) -> None:
        bad = evaluate_p261_check_group_d_release_wo_card_audio_copyright_and_tier0(
            claimed_copyright_cleared_by_camera_reset=True,
            simulate_bench_dry_run=True,
        )[0]
        self.assertFalse(bad.passed)

    def test_55_group_d_h0_equals_h3_drift_fails_closed(self) -> None:
        gd = evaluate_p261_check_group_d_release_wo_card_audio_copyright_and_tier0(
            simulated_h0_h3_drifted_surfaces=2,
            simulate_bench_dry_run=True,
        )[0]
        self.assertFalse(gd.passed)
        self.assertEqual(gd.h0_equals_h3_count, 14)
        self.assertTrue(any(P261_GD_ERR_H0_H3_IMMUTABILITY_DRIFT in e for e in gd.errors))

    def test_56_orchestrator_offline_default_blocks_awaiting_tier0_receipt_both_modes(
        self,
    ) -> None:
        for clean in (None, True):
            rep = evaluate_realhw_diffset_customkey_autoslow_and_apsc_readiness(
                force_clean_room=clean,
                simulate_bench_dry_run=False,
            )
            self.assertEqual(rep.go_no_go, GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT)
            self.assertEqual(rep.check_groups_passed, 4)
            self.assertTrue(rep.all_4_check_groups_passed)
            self.assertFalse(rep.tier0_receipt_verified)
            self.assertFalse(rep.overall_ready_for_hardware_attach)
            self.assertFalse(rep.hardware_live_attachment_authorized)
            self.assertFalse(rep.persistent_emmc_writes_authorized)
            self.assertFalse(rep.spi_nor_write_authorized)
            self.assertFalse(rep.el3_payload_transmit_authorized)
            self.assertEqual(rep.usb_packets_transmitted, 0)
            self.assertEqual(rep.raw_firmware_bytes_leaked, 0)
            self.assertEqual(rep.e_nd_uart_bytes_transmitted, 0)
            self.assertEqual(rep.h0_equals_h3_count, 16)
            self.assertTrue(verify_phase261_report(rep.to_dict()).valid)

    def test_57_orchestrator_simulate_bench_dry_run_passes_4of4_16of16_both_modes(self) -> None:
        for clean in (None, True):
            rep = evaluate_realhw_diffset_customkey_autoslow_and_apsc_readiness(
                force_clean_room=clean,
                simulate_bench_dry_run=True,
            )
            self.assertEqual(rep.go_no_go, GO_NO_GO_DRY_RUN_SIMULATED_READY)
            self.assertEqual(rep.check_groups_passed, 4)
            self.assertTrue(rep.all_4_check_groups_passed)
            self.assertTrue(rep.tier0_receipt_verified)
            self.assertEqual(rep.h0_equals_h3_count, 16)
            self.assertEqual(rep.h0_h3_surface_count, 16)
            self.assertFalse(rep.overall_ready_for_hardware_attach)
            self.assertFalse(rep.hardware_live_attachment_authorized)
            self.assertTrue(verify_phase261_report(rep.to_dict()).valid)

    def test_58_orchestrator_distinct_device_receipts_verify_readonly_preflight(self) -> None:
        raw_a, raw_b, h0 = build_simulated_phase261_tier0_receipts()
        rep = evaluate_realhw_diffset_customkey_autoslow_and_apsc_readiness(
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
        self.assertEqual(rep.go_no_go, P261_GO_NO_GO_DIFFSET_CUSTOMKEY_AUTOSLOW_APSC_VERIFIED)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.hardware_live_attachment_authorized)
        self.assertTrue(verify_phase261_report(rep.to_dict()).valid)

    def test_59_verify_phase261_report_catches_safety_lock_end_uart_and_digest_tampering(
        self,
    ) -> None:
        base = evaluate_realhw_diffset_customkey_autoslow_and_apsc_readiness(
            force_clean_room=True,
            simulate_bench_dry_run=True,
        ).to_dict()
        for lock_key in (
            "overall_ready_for_hardware_attach",
            "hardware_live_attachment_authorized",
            "persistent_emmc_writes_authorized",
            "spi_nor_write_authorized",
            "el3_payload_transmit_authorized",
            "fx3_has_builtin_evf",
        ):
            mutated = dict(base)
            mutated[lock_key] = True
            self.assertFalse(verify_phase261_report(mutated).valid)

        for zero_key in (
            "usb_packets_transmitted",
            "raw_firmware_bytes_leaked",
            "e_nd_uart_bytes_transmitted",
            "slot1_custom_key_vault_mutation_bytes",
            "photographer_copyright_pii_leaked_bytes",
        ):
            mutated = dict(base)
            mutated[zero_key] = 1
            self.assertFalse(verify_phase261_report(mutated).valid)

        escalated = dict(base)
        escalated["go_no_go"] = P261_GO_NO_GO_DIFFSET_CUSTOMKEY_AUTOSLOW_APSC_VERIFIED
        self.assertFalse(verify_phase261_report(escalated).valid)

        bad_sha = dict(base)
        bad_sha["report_sha256"] = "c" * 64
        self.assertFalse(verify_phase261_report(bad_sha).valid)

    def test_60_deterministic_sha256_and_markdown_rendering(self) -> None:
        r1 = evaluate_realhw_diffset_customkey_autoslow_and_apsc_readiness(
            force_clean_room=True, simulate_bench_dry_run=True
        )
        r2 = evaluate_realhw_diffset_customkey_autoslow_and_apsc_readiness(
            force_clean_room=True, simulate_bench_dry_run=True
        )
        self.assertEqual(r1.report_sha256, r2.report_sha256)
        md = render_phase261_markdown(r1)
        for token in (
            PHASE_261_SCHEMA,
            P261_CHECK_GROUP_A_ID,
            P261_CHECK_GROUP_B_ID,
            P261_CHECK_GROUP_C_ID,
            P261_CHECK_GROUP_D_ID,
            r1.report_sha256,
        ):
            self.assertIn(token, md)

    def test_61_cli_offline_default_fails_closed_exit_2_awaiting_physical_tier0_receipt(
        self,
    ) -> None:
        buf = io.StringIO()
        with mock.patch("sys.stdout", buf):
            rc = cli_main(
                [
                    "preflight-diffset-customkey-autoslow-and-apsc",
                    "--force-clean-room",
                    "--json",
                ]
            )
        self.assertEqual(rc, 2)
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["schema"], PHASE_261_SCHEMA)
        self.assertEqual(payload["go_no_go"], GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT)
        self.assertFalse(payload["overall_ready_for_hardware_attach"])
        self.assertFalse(payload["hardware_live_attachment_authorized"])

    def test_62_cli_simulate_bench_dry_run_emits_deterministic_json_and_markdown_exit_0(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            json_path = Path(tmp) / "p261.json"
            md_path = Path(tmp) / "p261.md"
            buf = io.StringIO()
            with mock.patch("sys.stdout", buf):
                rc = cli_main(
                    [
                        "preflight-diffset-customkey-autoslow-and-apsc",
                        "--simulate-bench-dry-run",
                        "--output",
                        str(json_path),
                        "--markdown-out",
                        str(md_path),
                    ]
                )
            self.assertEqual(rc, 0)
            self.assertIn("go_no_go=DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH", buf.getvalue())
            loaded = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertTrue(verify_phase261_report(loaded).valid)
            md_text = md_path.read_text(encoding="utf-8")
            self.assertIn(PHASE_261_SCHEMA, md_text)

    def test_63_cli_blocks_violations_across_all_4_groups_exit_2(self) -> None:
        for extra_flags in (
            ["--slot1-custom-key-access", "WRITE"],
            ["--hdmi-time-code-output", "OFF", "--hdmi-rec-control", "ON"],
            ["--apsc-s35-shooting", "ON", "--movie-file-format", "XAVC_S_I_4K"],
            ["--write-copyright-info", "ON", "--photographer-text", "Leak"],
        ):
            buf = io.StringIO()
            with mock.patch("sys.stdout", buf):
                rc = cli_main(
                    [
                        "preflight-diffset-customkey-autoslow-and-apsc",
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
                P261_GO_NO_GO_BLOCKED_DIFFSET_CUSTOMKEY_AUTOSLOW_APSC_FAILURE,
            )

    def test_64_cli_blocks_same_filesystem_st_dev_receipt_files_exit_2(self) -> None:
        raw_a, raw_b, _ = build_simulated_phase261_tier0_receipts()
        with tempfile.TemporaryDirectory() as tmp:
            pa = Path(tmp) / "rcpt_a.bin"
            pb = Path(tmp) / "rcpt_b.bin"
            pa.write_bytes(raw_a)
            pb.write_bytes(raw_b)
            buf = io.StringIO()
            with mock.patch("sys.stdout", buf):
                rc = cli_main(
                    [
                        "preflight-diffset-customkey-autoslow-and-apsc",
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
                P261_GO_NO_GO_BLOCKED_DIFFSET_CUSTOMKEY_AUTOSLOW_APSC_FAILURE,
            )
            self.assertTrue(
                any(
                    P261_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID in e
                    for e in payload["errors"]
                )
            )


if __name__ == "__main__":
    unittest.main()
