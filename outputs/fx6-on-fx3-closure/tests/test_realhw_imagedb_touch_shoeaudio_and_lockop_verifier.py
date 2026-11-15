"""Dual-mode unit tests (64 cases) for Phase 248 (`preflight-imagedb-touch-shoeaudio-and-lockop`):
5th Physical Bench & Pre-Shoot Media/Audio/Vault Readiness Verifier across Waves 34–39 check groups (`A..D`).

Runs deterministically in both `LOCAL_DONOR_O_RDONLY` and `FX3_FX6_FORCE_CLEAN_ROOM=1`
modes with zero `.pyc` emission, zero persistent writes, and `< 3.5s` runtime.
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
from fx6_closure.realhw_imagedb_touch_shoeaudio_and_lockop_verifier import (  # noqa: E402
    AF_SUBJ_SHIFT_SENSITIVITY_EXACT_LABEL,
    DESTRUCTIVE_SLOT_FULL_FORMAT_CHORD,
    GO_NO_GO_BLOCKED_IMAGEDB_TOUCH_SHOEAUDIO_LOCKOP_FAILURE,
    GO_NO_GO_IMAGEDB_TOUCH_SHOEAUDIO_LOCKOP_VERIFIED,
    LOCK_OP_FULL_BODY_CHORD,
    P248_CHECK_GROUP_A_ID,
    P248_CHECK_GROUP_B_ID,
    P248_CHECK_GROUP_C_ID,
    P248_CHECK_GROUP_D_ID,
    P248_GA_ERR_AF_KINEMATICS_OR_INTERVAL_STILL_ONLY,
    P248_GA_ERR_MODEL_OR_FW_FLOOR,
    P248_GA_ERR_MONITOR_FLIP_PERSISTENCE_OR_PLAYBACK_INVERSION,
    P248_GA_ERR_RECOVER_IMAGEDB_DEPLETED_BATTERY,
    P248_GA_ERR_RECOVER_IMAGEDB_SEMANTICS_INVALID,
    P248_GA_ERR_RECOVER_IMAGEDB_SLOT1_TIER0_VAULT_GUARD,
    P248_GB_ERR_BT_RMT_CTRL_IR_LOCKOUT_OR_NETWORK_RESET,
    P248_GB_ERR_HDMI_CLEAN_FEED_OR_INFO_DISPLAY_VIOLATION,
    P248_GB_ERR_INDOOR_SUNNY_WEATHER_OR_DISPLAY_QUALITY_HIGH,
    P248_GB_ERR_TOUCH_OP_BENCH_TAP_GUARD_OR_PERSISTENCE,
    P248_GC_ERR_SAVELOAD_EXCLUSIONS_OR_CROSS_MODEL_VIOLATION,
    P248_GC_ERR_SAVELOAD_SLOT1_TIER0_SAVE_BLOCKED,
    P248_GC_ERR_SHOE_AUDIO_LOCKOUT_OR_METER_COUPLING,
    P248_GC_ERR_WIND_NOISE_REDUCT_EXTERNAL_MIC_OR_INDOOR_ON,
    P248_GD_ERR_H0_H3_IMMUTABILITY_DRIFT,
    P248_GD_ERR_LOCK_OP_PARTS_OR_DESTRUCTIVE_CHORD_VIOLATION,
    P248_GD_ERR_SHUTTER_ANGLE_OR_AUDIO_TIMING_VIOLATION,
    P248_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID,
    P248_GD_ERR_USB_POWER_MISSING_NPFZ100_OR_WRONG_PORT,
    PHASE_248_CHECK_GROUP_IDS,
    PHASE_248_SCHEMA,
    PHASE_248_VERSION,
    SAVELOAD_FOUR_EXCLUDED_CATEGORIES,
    SHUTTER_ANGLE_CONSTANT_DEGREE_TABLE,
    TOUCH_OPERATION_FOUR_SETUP_ITEMS,
    build_simulated_phase248_tier0_receipts,
    evaluate_check_group_a_imagedb_vault_and_monitor_flip,
    evaluate_check_group_b_touch_op_hdmi_and_display_power,
    evaluate_check_group_c_shoe_audio_wind_and_saveload,
    evaluate_check_group_d_lock_op_usb_power_shutter_angle_and_tier0,
    evaluate_realhw_imagedb_touch_shoeaudio_and_lockop_readiness,
    inspect_phase248_donors_bounded,
    render_phase248_markdown,
    run_imagedb_touch_shoeaudio_and_lockop_preflight,
    verify_phase248_report,
)
from fx6_closure.realhw_sd_stageb_bundle_and_uninstaller import (  # noqa: E402
    DEFAULT_TARGET_BODY_SERIAL,
    DEFAULT_TARGET_EMMC_CID,
)


class TestPhase248ImageDbTouchShoeAudioLockOpVerifier(unittest.TestCase):
    """64 deterministic dual-mode unit tests for Phase 248 5th physical bench verifier."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._suite_t0 = time.perf_counter()

    @classmethod
    def tearDownClass(cls) -> None:
        elapsed = time.perf_counter() - cls._suite_t0
        assert elapsed < 3.5, f"Phase 248 test suite exceeded <3.5s budget: {elapsed:.3f}s"

    # --- Group 0: Exports, Bounded Donor O_RDONLY & Clean-Room Parity (7 tests) ---

    def test_01_public_symbols_exported_cleanly_without_shadowing_phase227(self) -> None:
        self.assertEqual(
            PHASE_248_SCHEMA,
            "realhw_imagedb_touch_shoeaudio_and_lockop_verifier_v1",
        )
        self.assertEqual(PHASE_248_VERSION, "248.0.0")
        for sym in (
            "PHASE_248_SCHEMA",
            "PHASE_248_VERSION",
            "P248_CHECK_GROUP_A_ID",
            "P248_CHECK_GROUP_B_ID",
            "P248_CHECK_GROUP_C_ID",
            "P248_CHECK_GROUP_D_ID",
            "evaluate_realhw_imagedb_touch_shoeaudio_and_lockop_readiness",
            "run_imagedb_touch_shoeaudio_and_lockop_preflight",
            "verify_phase248_report",
            "render_phase248_markdown",
        ):
            self.assertIn(sym, fx6_closure.__all__)
            self.assertTrue(hasattr(fx6_closure, sym))
        # Verify Phase 227 CHECK_GROUP_A_ID was NOT shadowed
        self.assertEqual(
            fx6_closure.CHECK_GROUP_A_ID,
            "GROUP_A_PIXEL_MAPPING_CNFLASHA_RO_AND_NTSCPAL_GAMMA_SPLIT",
        )
        self.assertIs(
            run_imagedb_touch_shoeaudio_and_lockop_preflight,
            evaluate_realhw_imagedb_touch_shoeaudio_and_lockop_readiness,
        )
        self.assertEqual(
            PHASE_248_CHECK_GROUP_IDS,
            (
                P248_CHECK_GROUP_A_ID,
                P248_CHECK_GROUP_B_ID,
                P248_CHECK_GROUP_C_ID,
                P248_CHECK_GROUP_D_ID,
            ),
        )

    def test_02_donor_inspection_respects_150ms_budget_default_mode(self) -> None:
        res = inspect_phase248_donors_bounded()
        self.assertTrue(res.passed)
        self.assertTrue(res.read_only_o_rdonly_enforced)
        self.assertTrue(res.within_150ms_budget)
        self.assertLess(res.elapsed_seconds, DONOR_INSPECTION_MAX_SECONDS)
        self.assertEqual(res.raw_firmware_bytes_leaked, 0)

    def test_03_donor_inspection_clean_room_synthetic_mode(self) -> None:
        res = inspect_phase248_donors_bounded(force_clean_room=True)
        self.assertTrue(res.passed)
        self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(res.raw_firmware_bytes_leaked, 0)
        self.assertTrue(all(a.startswith("synthetic:") for a in res.inspected_artifacts))

    def test_04_donor_inspection_env_var_force_clean_room(self) -> None:
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            res = inspect_phase248_donors_bounded()
        self.assertTrue(res.passed)
        self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_05_donor_inspection_synthetic_clean_room_alias(self) -> None:
        res = inspect_phase248_donors_bounded(synthetic_clean_room=True)
        self.assertTrue(res.passed)
        self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_06_donor_inspection_missing_donors_fails_closed_when_forced_local(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            res = inspect_phase248_donors_bounded(fx6_lib_dir=Path(tmp), force_clean_room=False)
        self.assertFalse(res.passed)
        self.assertEqual(res.verification_mode, "LOCAL_DONOR_O_RDONLY")
        self.assertEqual(res.raw_firmware_bytes_leaked, 0)

    def test_07_donor_inspection_exceeded_budget_fails_closed(self) -> None:
        res = inspect_phase248_donors_bounded(force_clean_room=True, max_seconds=0.0)
        self.assertFalse(res.passed)
        self.assertFalse(res.within_150ms_budget)

    # --- Group A: [Recover Image DB] Battery & Slot-1 Vault Guard + Monitor Flip (12 tests) ---

    def test_08_group_a_default_bench_posture_passes(self) -> None:
        ga = evaluate_check_group_a_imagedb_vault_and_monitor_flip()
        self.assertTrue(ga.passed)
        self.assertTrue(ga.recover_image_db_allowed)
        self.assertTrue(ga.non_deleting_repair_semantics_verified)
        self.assertFalse(ga.playback_display_horizontally_inverted)
        self.assertEqual(ga.errors, ())

    def test_09_group_a_blocks_wrong_model_id_or_old_firmware(self) -> None:
        ga_model = evaluate_check_group_a_imagedb_vault_and_monitor_flip(body_model_id=0x91030099)
        self.assertFalse(ga_model.passed)
        self.assertTrue(any(P248_GA_ERR_MODEL_OR_FW_FLOOR in e for e in ga_model.errors))

        ga_fw = evaluate_check_group_a_imagedb_vault_and_monitor_flip(body_fw="2.00")
        self.assertFalse(ga_fw.passed)
        self.assertTrue(any(P248_GA_ERR_MODEL_OR_FW_FLOOR in e for e in ga_fw.errors))

    def test_10_group_a_blocks_recover_imagedb_on_depleted_np_fz100_battery(self) -> None:
        ga = evaluate_check_group_a_imagedb_vault_and_monitor_flip(
            recover_image_db_requested=True,
            recover_image_db_target_slot=2,
            battery_soc_pct=19.5,
        )
        self.assertFalse(ga.passed)
        self.assertFalse(ga.recover_image_db_allowed)
        self.assertTrue(
            any(P248_GA_ERR_RECOVER_IMAGEDB_DEPLETED_BATTERY in e for e in ga.errors)
        )

    def test_11_group_a_blocks_recover_imagedb_when_low_battery_warning_active(self) -> None:
        ga = evaluate_check_group_a_imagedb_vault_and_monitor_flip(
            recover_image_db_requested=True,
            recover_image_db_target_slot=2,
            battery_soc_pct=24.0,
            low_battery_warning_active=True,
        )
        self.assertFalse(ga.passed)
        self.assertTrue(
            any(P248_GA_ERR_RECOVER_IMAGEDB_DEPLETED_BATTERY in e for e in ga.errors)
        )

    def test_12_group_a_blocks_recover_imagedb_on_unverified_slot1_tier0_card(self) -> None:
        ga = evaluate_check_group_a_imagedb_vault_and_monitor_flip(
            recover_image_db_requested=True,
            recover_image_db_target_slot=1,
            slot1_contains_tier0_dump=True,
            slot1_tier0_sha256_verified_off_camera=False,
            slot1_wp_locked=True,
        )
        self.assertFalse(ga.passed)
        self.assertTrue(
            any(P248_GA_ERR_RECOVER_IMAGEDB_SLOT1_TIER0_VAULT_GUARD in e for e in ga.errors)
        )

    def test_13_group_a_blocks_recover_imagedb_on_non_wp_locked_slot1_tier0_card(self) -> None:
        ga = evaluate_check_group_a_imagedb_vault_and_monitor_flip(
            recover_image_db_requested=True,
            recover_image_db_target_slot=1,
            slot1_contains_tier0_dump=True,
            slot1_tier0_sha256_verified_off_camera=True,
            slot1_wp_locked=False,
        )
        self.assertFalse(ga.passed)
        self.assertTrue(
            any(P248_GA_ERR_RECOVER_IMAGEDB_SLOT1_TIER0_VAULT_GUARD in e for e in ga.errors)
        )

    def test_14_group_a_allows_recover_imagedb_on_slot2_with_charged_battery(self) -> None:
        ga = evaluate_check_group_a_imagedb_vault_and_monitor_flip(
            recover_image_db_requested=True,
            recover_image_db_target_slot=2,
            battery_soc_pct=75.0,
            slot1_contains_tier0_dump=True,
            slot1_tier0_sha256_verified_off_camera=False,
            slot1_wp_locked=False,
        )
        self.assertTrue(ga.passed)
        self.assertTrue(ga.recover_image_db_allowed)

    def test_15_group_a_rejects_clip_deleting_semantics_or_invalid_slot(self) -> None:
        ga = evaluate_check_group_a_imagedb_vault_and_monitor_flip(
            expect_recover_imagedb_deletes_clips=True
        )
        self.assertFalse(ga.passed)
        self.assertTrue(
            any(P248_GA_ERR_RECOVER_IMAGEDB_SEMANTICS_INVALID in e for e in ga.errors)
        )

        ga_slot = evaluate_check_group_a_imagedb_vault_and_monitor_flip(
            recover_image_db_target_slot=3
        )
        self.assertFalse(ga_slot.passed)

    def test_16_group_a_monitor_flip_survives_camera_reset_and_clears_on_initialize(self) -> None:
        ga_cam = evaluate_check_group_a_imagedb_vault_and_monitor_flip(
            monitor_flip_direction="HORIZONTAL_FLIP",
            reset_action="CAMERA_SETTINGS_RESET",
            claimed_monitor_flip_after_reset="HORIZONTAL_FLIP",
        )
        self.assertTrue(ga_cam.passed)
        self.assertEqual(ga_cam.effective_monitor_flip_after_reset, "HORIZONTAL_FLIP")

        ga_init = evaluate_check_group_a_imagedb_vault_and_monitor_flip(
            monitor_flip_direction="VERTICAL_FLIP",
            reset_action="INITIALIZE",
            claimed_monitor_flip_after_reset="AUTO",
        )
        self.assertTrue(ga_init.passed)
        self.assertEqual(ga_init.effective_monitor_flip_after_reset, "AUTO")

    def test_17_group_a_rejects_wrong_monitor_flip_reset_claim(self) -> None:
        ga = evaluate_check_group_a_imagedb_vault_and_monitor_flip(
            monitor_flip_direction="HORIZONTAL_FLIP",
            reset_action="CAMERA_SETTINGS_RESET",
            claimed_monitor_flip_after_reset="AUTO",
        )
        self.assertFalse(ga.passed)
        self.assertTrue(
            any(
                P248_GA_ERR_MONITOR_FLIP_PERSISTENCE_OR_PLAYBACK_INVERSION in e
                for e in ga.errors
            )
        )

    def test_18_group_a_enforces_horizontal_flip_playback_non_inversion(self) -> None:
        ga_ok = evaluate_check_group_a_imagedb_vault_and_monitor_flip(
            monitor_flip_direction="HORIZONTAL_FLIP"
        )
        self.assertTrue(ga_ok.passed)
        self.assertFalse(ga_ok.playback_display_horizontally_inverted)

        ga_bad = evaluate_check_group_a_imagedb_vault_and_monitor_flip(
            monitor_flip_direction="HORIZONTAL_FLIP",
            expect_playback_inverted_under_horizontal_flip=True,
        )
        self.assertFalse(ga_bad.passed)
        self.assertTrue(
            any(
                P248_GA_ERR_MONITOR_FLIP_PERSISTENCE_OR_PLAYBACK_INVERSION in e
                for e in ga_bad.errors
            )
        )

    def test_19_group_a_enforces_af_kinematics_exact_spelling_and_interval_still_only(self) -> None:
        self.assertEqual(AF_SUBJ_SHIFT_SENSITIVITY_EXACT_LABEL, "AF Subj. Shift Sensitivity")
        ga_abbr = evaluate_check_group_a_imagedb_vault_and_monitor_flip(
            af_subj_shift_sensitivity_label="AF Subj. Shift Sens."
        )
        self.assertFalse(ga_abbr.passed)
        self.assertTrue(
            any(P248_GA_ERR_AF_KINEMATICS_OR_INTERVAL_STILL_ONLY in e for e in ga_abbr.errors)
        )

        ga_intv = evaluate_check_group_a_imagedb_vault_and_monitor_flip(
            interval_shoot_func_enabled=True,
            expect_interval_in_camera_movie_recording=True,
        )
        self.assertFalse(ga_intv.passed)

    # --- Group B: [Touch Operation] 4-Item Guard, HDMI Clean-Feed & Display Power (13 tests) ---

    def test_20_group_b_default_bench_posture_passes(self) -> None:
        self.assertEqual(len(TOUCH_OPERATION_FOUR_SETUP_ITEMS), 4)
        gb = evaluate_check_group_b_touch_op_hdmi_and_display_power()
        self.assertTrue(gb.passed)
        self.assertTrue(gb.touch_bench_tap_guard_satisfied)
        self.assertTrue(gb.indoor_np_fz100_display_conservation_ok)

    def test_21_group_b_allows_on_playback_only_during_unattended_tier0_dump(self) -> None:
        gb = evaluate_check_group_b_touch_op_hdmi_and_display_power(
            touch_operation="On: Playback Only",
            unattended_tier0_dump_active=True,
        )
        self.assertTrue(gb.passed)
        self.assertEqual(gb.touch_operation, "ON_PLAYBACK_ONLY")

    def test_22_group_b_blocks_touch_operation_on_during_unattended_tier0_dump(self) -> None:
        gb = evaluate_check_group_b_touch_op_hdmi_and_display_power(
            touch_operation="ON",
            unattended_tier0_dump_active=True,
        )
        self.assertFalse(gb.passed)
        self.assertFalse(gb.touch_bench_tap_guard_satisfied)
        self.assertTrue(
            any(P248_GB_ERR_TOUCH_OP_BENCH_TAP_GUARD_OR_PERSISTENCE in e for e in gb.errors)
        )

    def test_23_group_b_touch_4_items_survive_camera_settings_reset(self) -> None:
        gb_surv = evaluate_check_group_b_touch_op_hdmi_and_display_power(
            touch_operation="OFF",
            touch_sensitivity="SENSITIVE",
            swipe_up="OPEN_THE_FN_MENU",
            touch_func_in_shooting="TOUCH_FOCUS",
            reset_action="CAMERA_SETTINGS_RESET",
            claimed_touch_operation_after_reset="OFF",
        )
        self.assertTrue(gb_surv.passed)
        self.assertEqual(gb_surv.effective_touch_operation_after_reset, "OFF")

        gb_bad = evaluate_check_group_b_touch_op_hdmi_and_display_power(
            touch_operation="OFF",
            reset_action="CAMERA_SETTINGS_RESET",
            claimed_touch_operation_after_reset="ON",
        )
        self.assertFalse(gb_bad.passed)

    def test_24_group_b_forces_hdmi_info_off_under_off_hdmi_only_clean_feed(self) -> None:
        gb_ok = evaluate_check_group_b_touch_op_hdmi_and_display_power(
            rec_media_dur_hdmi_output="OFF_HDMI_ONLY",
            hdmi_info_display="OFF",
        )
        self.assertTrue(gb_ok.passed)
        self.assertTrue(gb_ok.hdmi_clean_feed_forced_off)
        self.assertEqual(gb_ok.effective_hdmi_info_display, "OFF")

        gb_bad = evaluate_check_group_b_touch_op_hdmi_and_display_power(
            rec_media_dur_hdmi_output="OFF_HDMI_ONLY",
            hdmi_info_display="ON",
        )
        self.assertFalse(gb_bad.passed)
        self.assertTrue(
            any(P248_GB_ERR_HDMI_CLEAN_FEED_OR_INFO_DISPLAY_VIOLATION in e for e in gb_bad.errors)
        )

    def test_25_group_b_forces_hdmi_info_off_under_hdmi_raw_output(self) -> None:
        gb_bad = evaluate_check_group_b_touch_op_hdmi_and_display_power(
            hdmi_raw_output=True,
            expect_hdmi_info_on_during_hdmionly_or_raw=True,
        )
        self.assertFalse(gb_bad.passed)
        self.assertTrue(
            any(P248_GB_ERR_HDMI_CLEAN_FEED_OR_INFO_DISPLAY_VIOLATION in e for e in gb_bad.errors)
        )

    def test_26_group_b_allows_hdmi_info_on_for_emphasized_rec_and_grid_when_not_clean_feed(
        self,
    ) -> None:
        gb = evaluate_check_group_b_touch_op_hdmi_and_display_power(
            rec_media_dur_hdmi_output="ON",
            hdmi_raw_output=False,
            hdmi_info_display="ON",
            emphasized_rec_display="ON",
            grid_line_display="ON",
            grid_line_type="DIAG_PLUS_SQUARE_GRID",
        )
        self.assertTrue(gb.passed)
        self.assertEqual(gb.effective_hdmi_info_display, "ON")
        self.assertTrue(gb.builtin_lcd_blanked_by_hdmi_info)

    def test_27_group_b_blocks_marker_zebra_peaking_over_hdmi_claim(self) -> None:
        gb = evaluate_check_group_b_touch_op_hdmi_and_display_power(
            expect_marker_zebra_peaking_on_hdmi=True
        )
        self.assertFalse(gb.passed)
        self.assertTrue(
            any(P248_GB_ERR_HDMI_CLEAN_FEED_OR_INFO_DISPLAY_VIOLATION in e for e in gb.errors)
        )

    def test_28_group_b_clamps_indoor_monitor_brightness_away_from_sunny_weather(self) -> None:
        gb_in = evaluate_check_group_b_touch_op_hdmi_and_display_power(
            indoor_bench_environment=True,
            monitor_brightness_mode="SUNNY_WEATHER",
        )
        self.assertFalse(gb_in.passed)
        self.assertTrue(
            any(
                P248_GB_ERR_INDOOR_SUNNY_WEATHER_OR_DISPLAY_QUALITY_HIGH in e
                for e in gb_in.errors
            )
        )

        gb_out = evaluate_check_group_b_touch_op_hdmi_and_display_power(
            indoor_bench_environment=False,
            unattended_tier0_dump_active=False,
            monitor_brightness_mode="SUNNY_WEATHER",
        )
        self.assertTrue(gb_out.passed)

    def test_29_group_b_rejects_out_of_range_manual_brightness_level(self) -> None:
        for bad_lvl in (-3, 3):
            gb = evaluate_check_group_b_touch_op_hdmi_and_display_power(
                monitor_brightness_manual_level=bad_lvl
            )
            self.assertFalse(gb.passed)

    def test_30_group_b_clamps_display_quality_to_standard_for_np_fz100_conservation(self) -> None:
        gb = evaluate_check_group_b_touch_op_hdmi_and_display_power(
            indoor_bench_environment=True,
            display_quality="HIGH",
        )
        self.assertFalse(gb.passed)
        self.assertFalse(gb.indoor_np_fz100_display_conservation_ok)
        self.assertTrue(
            any(P248_GB_ERR_INDOOR_SUNNY_WEATHER_OR_DISPLAY_QUALITY_HIGH in e for e in gb.errors)
        )

    def test_31_group_b_enforces_bluetooth_rmt_ctrl_ir_lockout_and_radio_prereqs(self) -> None:
        gb_air = evaluate_check_group_b_touch_op_hdmi_and_display_power(
            bluetooth_rmt_ctrl="ON",
            bluetooth_function="ON",
            airplane_mode="ON",
        )
        self.assertFalse(gb_air.passed)

        gb_ir = evaluate_check_group_b_touch_op_hdmi_and_display_power(
            bluetooth_rmt_ctrl="ON",
            bluetooth_function="ON",
            airplane_mode="OFF",
            expect_ir_remote_usable=True,
        )
        self.assertFalse(gb_ir.passed)
        self.assertTrue(gb_ir.ir_remote_locked_out_by_bt)
        self.assertTrue(
            any(P248_GB_ERR_BT_RMT_CTRL_IR_LOCKOUT_OR_NETWORK_RESET in e for e in gb_ir.errors)
        )

    def test_32_group_b_verifies_3_reset_domain_split_network_vs_mymenu(self) -> None:
        gb = evaluate_check_group_b_touch_op_hdmi_and_display_power(
            bluetooth_rmt_ctrl="ON",
            bluetooth_function="ON",
            airplane_mode="OFF",
            display_from_my_menu="ON",
            reset_action="RESET_NETWORK_SET",
            claimed_bluetooth_rmt_ctrl_after_reset="OFF",
            claimed_display_from_my_menu_after_reset="ON",
        )
        self.assertTrue(gb.passed)
        self.assertEqual(gb.effective_bluetooth_rmt_ctrl_after_reset, "OFF")
        self.assertEqual(gb.effective_display_from_my_menu_after_reset, "ON")

    # --- Group C: [Shoe Audio Set.] 4ch, [Wind Noise Reduct.] & [Save/Load] Firewall (12 tests) ---

    def test_33_group_c_default_xlr_h1_digital_4ch_passes_with_4_meters(self) -> None:
        gc = evaluate_check_group_c_shoe_audio_wind_and_saveload()
        self.assertTrue(gc.passed)
        self.assertTrue(gc.shoe_audio_digital_available)
        self.assertEqual(gc.effective_audio_meter_channels, 4)
        self.assertEqual(gc.active_shoe_audio_lockouts, ())

    def test_34_group_c_lockout1_blocks_shoe_audio_in_sq_or_audio_recording_off(self) -> None:
        gc_sq = evaluate_check_group_c_shoe_audio_wind_and_saveload(sq_mode_enabled=True)
        self.assertFalse(gc_sq.passed)
        self.assertIn("SQ_OR_AUDIO_RECORDING_OFF", gc_sq.active_shoe_audio_lockouts)
        self.assertEqual(gc_sq.effective_audio_meter_channels, 0)
        self.assertTrue(
            any(P248_GC_ERR_SHOE_AUDIO_LOCKOUT_OR_METER_COUPLING in e for e in gc_sq.errors)
        )

        gc_off = evaluate_check_group_c_shoe_audio_wind_and_saveload(audio_recording="OFF")
        self.assertFalse(gc_off.passed)
        self.assertEqual(gc_off.effective_audio_meter_channels, 0)

    def test_35_group_c_lockout2_blocks_digital_shoe_audio_when_body_35mm_mic_plugged(self) -> None:
        gc = evaluate_check_group_c_shoe_audio_wind_and_saveload(body_35mm_mic_plugged=True)
        self.assertFalse(gc.passed)
        self.assertIn("BODY_35MM_MIC_JACK_OVERRIDE", gc.active_shoe_audio_lockouts)
        self.assertEqual(gc.effective_audio_meter_channels, 2)
        self.assertTrue(
            any(P248_GC_ERR_SHOE_AUDIO_LOCKOUT_OR_METER_COUPLING in e for e in gc.errors)
        )

    def test_36_group_c_lockout3_blocks_digital_4ch_when_xlr_h1_analog_or_detached(self) -> None:
        gc_ana = evaluate_check_group_c_shoe_audio_wind_and_saveload(xlr_h1_mode_switch="ANALOG")
        self.assertFalse(gc_ana.passed)
        self.assertIn("XLR_H1_ANALOG_SWITCH_MODE", gc_ana.active_shoe_audio_lockouts)
        self.assertEqual(gc_ana.effective_audio_meter_channels, 2)

        gc_det = evaluate_check_group_c_shoe_audio_wind_and_saveload(xlr_h1_attached=False)
        self.assertFalse(gc_det.passed)

    def test_37_group_c_rejects_mismatched_claimed_audio_meter_channels(self) -> None:
        gc = evaluate_check_group_c_shoe_audio_wind_and_saveload(
            shoe_audio_set="48KHZ_16BIT_2CH",
            claimed_audio_meter_channels=4,
        )
        self.assertFalse(gc.passed)
        self.assertTrue(
            any(P248_GC_ERR_SHOE_AUDIO_LOCKOUT_OR_METER_COUPLING in e for e in gc.errors)
        )

    def test_38_group_c_blocks_wind_noise_reduct_external_mic_expectations(self) -> None:
        gc_claim = evaluate_check_group_c_shoe_audio_wind_and_saveload(
            expect_wind_noise_reduct_on_external_mic=True
        )
        self.assertFalse(gc_claim.passed)
        self.assertTrue(
            any(
                P248_GC_ERR_WIND_NOISE_REDUCT_EXTERNAL_MIC_OR_INDOOR_ON in e
                for e in gc_claim.errors
            )
        )

        gc_xlr_on = evaluate_check_group_c_shoe_audio_wind_and_saveload(
            xlr_h1_attached=True,
            wind_noise_reduct="ON",
            indoor_calm_bench_audio=False,
        )
        self.assertFalse(gc_xlr_on.passed)

    def test_39_group_c_wind_noise_reduct_blocks_indoor_calm_but_allows_builtin_outdoor(
        self,
    ) -> None:
        gc_indoor = evaluate_check_group_c_shoe_audio_wind_and_saveload(
            xlr_h1_attached=False,
            shoe_audio_set="48KHZ_16BIT_2CH",
            wind_noise_reduct="ON",
            indoor_calm_bench_audio=True,
        )
        self.assertFalse(gc_indoor.passed)

        gc_outdoor = evaluate_check_group_c_shoe_audio_wind_and_saveload(
            xlr_h1_attached=False,
            shoe_audio_set="48KHZ_16BIT_2CH",
            wind_noise_reduct="ON",
            indoor_calm_bench_audio=False,
        )
        self.assertTrue(gc_outdoor.passed)

    def test_40_group_c_saveload_enforces_same_model_ilme_fx3_and_slot_1_to_10(self) -> None:
        for bad_kwargs in (
            {"camset_model_code": "ILME-FX6"},
            {"camset_model_code": "ILME-FX3A"},
            {"camset_slot_index": 0},
            {"camset_slot_index": 11},
        ):
            gc = evaluate_check_group_c_shoe_audio_wind_and_saveload(**bad_kwargs)
            self.assertFalse(gc.passed)
            self.assertTrue(
                any(
                    P248_GC_ERR_SAVELOAD_EXCLUSIONS_OR_CROSS_MODEL_VIOLATION in e
                    for e in gc.errors
                )
            )

    def test_41_group_c_saveload_enforces_4_excluded_privacy_and_calibration_categories(
        self,
    ) -> None:
        self.assertEqual(len(SAVELOAD_FOUR_EXCLUDED_CATEGORIES), 4)
        gc = evaluate_check_group_c_shoe_audio_wind_and_saveload(
            camset_payload_contains_excluded_items=True
        )
        self.assertFalse(gc.passed)
        self.assertFalse(gc.saveload_exclusions_verified)
        self.assertTrue(
            any(P248_GC_ERR_SAVELOAD_EXCLUSIONS_OR_CROSS_MODEL_VIOLATION in e for e in gc.errors)
        )

    def test_42_group_c_blocks_camset_save_to_slot1_tier0_vault_card(self) -> None:
        gc = evaluate_check_group_c_shoe_audio_wind_and_saveload(
            saveload_operation="SAVE",
            saveload_target="SLOT_1",
            slot1_contains_tier0_dump=True,
        )
        self.assertFalse(gc.passed)
        self.assertFalse(gc.slot1_camset_save_firewall_ok)
        self.assertTrue(any(P248_GC_ERR_SAVELOAD_SLOT1_TIER0_SAVE_BLOCKED in e for e in gc.errors))

    def test_43_group_c_allows_o_rdonly_load_from_slot1_and_save_to_slot2_or_cloud(self) -> None:
        gc_load = evaluate_check_group_c_shoe_audio_wind_and_saveload(
            saveload_operation="LOAD",
            saveload_target="SLOT_1",
            slot1_contains_tier0_dump=True,
        )
        self.assertTrue(gc_load.passed)

        gc_save2 = evaluate_check_group_c_shoe_audio_wind_and_saveload(
            saveload_operation="SAVE",
            saveload_target="SLOT_2",
            camset_slot_index=10,
        )
        self.assertTrue(gc_save2.passed)

        gc_cloud = evaluate_check_group_c_shoe_audio_wind_and_saveload(
            saveload_operation="SAVE",
            saveload_target="CLOUD_PRIVATE",
        )
        self.assertTrue(gc_cloud.passed)

    def test_44_group_c_accepts_human_readable_shoe_audio_label_and_xlr_low_cut(self) -> None:
        gc = evaluate_check_group_c_shoe_audio_wind_and_saveload(
            shoe_audio_set="48kHz/24bit 4ch",
            xlr_h1_low_cut_switch="100HZ",
        )
        self.assertTrue(gc.passed)
        self.assertEqual(gc.shoe_audio_set, "48KHZ_24BIT_4CH")
        self.assertEqual(gc.xlr_h1_low_cut_switch, "100HZ")

    # --- Group D: [Lock Operation Parts] 5s Chord, USB Power Battery & Shutter Angle (11 tests) ---

    def test_45_group_d_default_bench_posture_passes_with_5s_lock_chord(self) -> None:
        gd, t0_errs = evaluate_check_group_d_lock_op_usb_power_shutter_angle_and_tier0(
            simulate_bench_dry_run=True
        )
        self.assertTrue(gd.passed)
        self.assertEqual(t0_errs, ())
        self.assertTrue(gd.full_body_lock_except_shutter_engaged)
        self.assertTrue(gd.destructive_format_chord_blocked)
        self.assertTrue(gd.my_dial_temporarily_unlocks_dials)
        self.assertTrue(gd.usb_power_battery_interlock_ok)
        self.assertTrue(gd.shutter_angle_unaffected_by_exposure_step)
        self.assertEqual(gd.h0_equals_h3_count, 16)
        self.assertTrue(gd.tier0_receipt_verified)

    def test_46_group_d_lock_operation_parts_survives_camera_reset_and_clears_on_initialize(
        self,
    ) -> None:
        gd_surv, _ = evaluate_check_group_d_lock_op_usb_power_shutter_angle_and_tier0(
            lock_operation_parts="Multi-Slct Only",
            reset_action="CAMERA_SETTINGS_RESET",
            claimed_lock_op_after_reset="MULTI_SELECTOR_ONLY",
        )
        self.assertTrue(gd_surv.passed)
        self.assertEqual(gd_surv.effective_lock_op_after_reset, "MULTI_SELECTOR_ONLY")

        gd_init, _ = evaluate_check_group_d_lock_op_usb_power_shutter_angle_and_tier0(
            lock_operation_parts="Dial + Wheel",
            reset_action="INITIALIZE",
            claimed_lock_op_after_reset="OFF",
        )
        self.assertTrue(gd_init.passed)

    def test_47_group_d_hard_blocks_destructive_menu_plus_delete_2s_format_chord(self) -> None:
        gd1, _ = evaluate_check_group_d_lock_op_usb_power_shutter_angle_and_tier0(
            active_key_chord=DESTRUCTIVE_SLOT_FULL_FORMAT_CHORD
        )
        self.assertFalse(gd1.passed)
        self.assertFalse(gd1.destructive_format_chord_blocked)
        self.assertTrue(
            any(
                P248_GD_ERR_LOCK_OP_PARTS_OR_DESTRUCTIVE_CHORD_VIOLATION in e
                for e in gd1.errors
            )
        )

        gd2, _ = evaluate_check_group_d_lock_op_usb_power_shutter_angle_and_tier0(
            active_key_chord=LOCK_OP_FULL_BODY_CHORD,
            destructive_slot_full_format_chord_invoked=True,
        )
        self.assertFalse(gd2.passed)

    def test_48_group_d_enforces_5s_hold_shutter_exemption_and_my_dial_override(self) -> None:
        gd_short, _ = evaluate_check_group_d_lock_op_usb_power_shutter_angle_and_tier0(
            active_key_chord=LOCK_OP_FULL_BODY_CHORD,
            lock_chord_hold_seconds=4.5,
        )
        self.assertFalse(gd_short.passed)

        gd_shut, _ = evaluate_check_group_d_lock_op_usb_power_shutter_angle_and_tier0(
            expect_shutter_button_locked_by_menu_fn_5s=True
        )
        self.assertFalse(gd_shut.passed)

        gd_mydial, _ = evaluate_check_group_d_lock_op_usb_power_shutter_angle_and_tier0(
            expect_my_dial_blocked_by_lock_op_parts=True
        )
        self.assertFalse(gd_mydial.passed)

    def test_49_group_d_blocks_usb_power_without_inserted_np_fz100_or_on_battery_removal(
        self,
    ) -> None:
        gd_missing, _ = evaluate_check_group_d_lock_op_usb_power_shutter_angle_and_tier0(
            power_source="USB_PD_BODY",
            np_fz100_battery_inserted=False,
        )
        self.assertFalse(gd_missing.passed)
        self.assertFalse(gd_missing.usb_power_battery_interlock_ok)
        self.assertTrue(
            any(P248_GD_ERR_USB_POWER_MISSING_NPFZ100_OR_WRONG_PORT in e for e in gd_missing.errors)
        )

        gd_pulled, _ = evaluate_check_group_d_lock_op_usb_power_shutter_angle_and_tier0(
            power_source="USB_PD_BODY",
            np_fz100_battery_inserted=True,
            battery_removed_under_usb_power=True,
        )
        self.assertFalse(gd_pulled.passed)

    def test_50_group_d_allows_dc_c1_coupler_and_blocks_multi_micro_usb_power(self) -> None:
        gd_dc, _ = evaluate_check_group_d_lock_op_usb_power_shutter_angle_and_tier0(
            power_source="DC_C1_COUPLER",
            np_fz100_battery_inserted=False,
            dc_c1_coupler_inserted=True,
            usb_power_terminal="USB_TYPE_C",
        )
        self.assertTrue(gd_dc.passed)

        gd_micro, _ = evaluate_check_group_d_lock_op_usb_power_shutter_angle_and_tier0(
            power_source="USB_PD_BODY",
            np_fz100_battery_inserted=True,
            usb_power_terminal="MULTI_MICRO_USB",
        )
        self.assertFalse(gd_micro.passed)
        self.assertTrue(
            any(P248_GD_ERR_USB_POWER_MISSING_NPFZ100_OR_WRONG_PORT in e for e in gd_micro.errors)
        )

    def test_51_group_d_verifies_usb_lun_setting_survives_camera_settings_reset(self) -> None:
        gd_ok, _ = evaluate_check_group_d_lock_op_usb_power_shutter_angle_and_tier0(
            usb_lun_setting="SINGLE",
            reset_action="CAMERA_SETTINGS_RESET",
            claimed_usb_lun_after_reset="SINGLE",
        )
        self.assertTrue(gd_ok.passed)

        gd_bad, _ = evaluate_check_group_d_lock_op_usb_power_shutter_angle_and_tier0(
            usb_lun_setting="SINGLE",
            reset_action="CAMERA_SETTINGS_RESET",
            claimed_usb_lun_after_reset="MULTI",
        )
        self.assertFalse(gd_bad.passed)

    def test_52_group_d_enforces_exposure_step_independence_from_shutter_angle_table(self) -> None:
        for step in ("0.3EV", "0.5EV"):
            for deg in SHUTTER_ANGLE_CONSTANT_DEGREE_TABLE:
                gd_ok, _ = evaluate_check_group_d_lock_op_usb_power_shutter_angle_and_tier0(
                    exposure_step=step,
                    shutter_mode="SHUTTER_ANGLE",
                    shutter_angle_deg=deg,
                )
                self.assertTrue(gd_ok.passed)

        gd_alter, _ = evaluate_check_group_d_lock_op_usb_power_shutter_angle_and_tier0(
            exposure_step="0.5EV",
            expect_exposure_step_alters_shutter_angle=True,
        )
        self.assertFalse(gd_alter.passed)
        self.assertTrue(
            any(P248_GD_ERR_SHUTTER_ANGLE_OR_AUDIO_TIMING_VIOLATION in e for e in gd_alter.errors)
        )

        gd_deg, _ = evaluate_check_group_d_lock_op_usb_power_shutter_angle_and_tier0(
            shutter_mode="SHUTTER_ANGLE",
            shutter_angle_deg=179.3,
        )
        self.assertFalse(gd_deg.passed)

    def test_53_group_d_rejects_native_var_shutter_and_movie_antiflicker_assumptions(self) -> None:
        gd1, _ = evaluate_check_group_d_lock_op_usb_power_shutter_angle_and_tier0(
            expect_fx3_native_var_shutter_menu=True
        )
        self.assertFalse(gd1.passed)

        gd2, _ = evaluate_check_group_d_lock_op_usb_power_shutter_angle_and_tier0(
            expect_antiflicker_in_movie_or_silent=True
        )
        self.assertFalse(gd2.passed)

    def test_54_group_d_enforces_audio_out_timing_sq_lockout_and_silent_mode_audio_signals(
        self,
    ) -> None:
        gd_sq, _ = evaluate_check_group_d_lock_op_usb_power_shutter_angle_and_tier0(
            audio_out_timing="LIP_SYNC",
            sq_mode_enabled=True,
            expect_audio_out_timing_in_sq_or_audio_off=True,
        )
        self.assertFalse(gd_sq.passed)

        gd_sil, _ = evaluate_check_group_d_lock_op_usb_power_shutter_angle_and_tier0(
            silent_mode_enabled=True,
            audio_signals_mode="ON",
        )
        self.assertFalse(gd_sil.passed)

    def test_55_group_d_blocks_h0_h3_drift_and_invalid_tier0_receipts(self) -> None:
        gd_drift, _ = evaluate_check_group_d_lock_op_usb_power_shutter_angle_and_tier0(
            simulated_h0_h3_drifted_surfaces=1,
            simulate_bench_dry_run=True,
        )
        self.assertFalse(gd_drift.passed)
        self.assertEqual(gd_drift.h0_equals_h3_count, 15)
        self.assertTrue(any(P248_GD_ERR_H0_H3_IMMUTABILITY_DRIFT in e for e in gd_drift.errors))

        raw_a, raw_b, h0 = build_simulated_phase248_tier0_receipts()
        gd_same_dev, t0_errs = evaluate_check_group_d_lock_op_usb_power_shutter_angle_and_tier0(
            receipt_a_bytes=raw_a,
            receipt_b_bytes=raw_b,
            st_dev_a_override=77,
            st_dev_b_override=77,
            body_serial=DEFAULT_TARGET_BODY_SERIAL,
            emmc_cid=DEFAULT_TARGET_EMMC_CID,
            h0_baselines_a=h0,
            h0_baselines_b=h0,
        )
        self.assertFalse(gd_same_dev.tier0_receipt_verified)
        self.assertTrue(
            any(P248_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID in e for e in t0_errs)
        )

    # --- Group E: End-to-End Orchestrator, Tamper Verifier & CLI (9 tests) ---

    def test_56_orchestrator_offline_blocks_awaiting_physical_tier0_receipt_both_modes(
        self,
    ) -> None:
        for clean in (None, True):
            rep = evaluate_realhw_imagedb_touch_shoeaudio_and_lockop_readiness(
                force_clean_room=clean,
                simulate_bench_dry_run=False,
            )
            self.assertEqual(rep.go_no_go, GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT)
            self.assertEqual(rep.check_group_count, 4)
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
            self.assertEqual(rep.h0_equals_h3_count, 16)
            self.assertTrue(verify_phase248_report(rep.to_dict()).valid)

    def test_57_orchestrator_simulate_bench_dry_run_passes_4of4_both_modes(self) -> None:
        for clean in (None, True):
            rep = evaluate_realhw_imagedb_touch_shoeaudio_and_lockop_readiness(
                force_clean_room=clean,
                simulate_bench_dry_run=True,
            )
            self.assertEqual(rep.go_no_go, GO_NO_GO_DRY_RUN_SIMULATED_READY)
            self.assertEqual(rep.check_groups_passed, 4)
            self.assertTrue(rep.all_4_check_groups_passed)
            self.assertTrue(rep.tier0_receipt_verified)
            self.assertFalse(rep.overall_ready_for_hardware_attach)
            self.assertFalse(rep.hardware_live_attachment_authorized)
            self.assertTrue(verify_phase248_report(rep.to_dict()).valid)

    def test_58_orchestrator_distinct_device_receipts_verify_readonly_preflight(self) -> None:
        raw_a, raw_b, h0 = build_simulated_phase248_tier0_receipts()
        rep = evaluate_realhw_imagedb_touch_shoeaudio_and_lockop_readiness(
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
        self.assertEqual(rep.go_no_go, GO_NO_GO_IMAGEDB_TOUCH_SHOEAUDIO_LOCKOP_VERIFIED)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.hardware_live_attachment_authorized)
        self.assertTrue(verify_phase248_report(rep.to_dict()).valid)

    def test_59_verify_phase248_report_catches_safety_lock_and_digest_tampering(self) -> None:
        base = evaluate_realhw_imagedb_touch_shoeaudio_and_lockop_readiness(
            force_clean_room=True,
            simulate_bench_dry_run=True,
        ).to_dict()
        for lock_key in (
            "overall_ready_for_hardware_attach",
            "hardware_live_attachment_authorized",
            "persistent_emmc_writes_authorized",
            "spi_nor_write_authorized",
            "el3_payload_transmit_authorized",
        ):
            mutated = dict(base)
            mutated[lock_key] = True
            self.assertFalse(verify_phase248_report(mutated).valid)

        for zero_key in ("usb_packets_transmitted", "raw_firmware_bytes_leaked"):
            mutated = dict(base)
            mutated[zero_key] = 1
            self.assertFalse(verify_phase248_report(mutated).valid)

        escalated = dict(base)
        escalated["go_no_go"] = GO_NO_GO_IMAGEDB_TOUCH_SHOEAUDIO_LOCKOP_VERIFIED
        self.assertFalse(verify_phase248_report(escalated).valid)

        bad_sha = dict(base)
        bad_sha["report_sha256"] = "b" * 64
        self.assertFalse(verify_phase248_report(bad_sha).valid)

    def test_60_deterministic_sha256_and_markdown_rendering(self) -> None:
        r1 = evaluate_realhw_imagedb_touch_shoeaudio_and_lockop_readiness(
            force_clean_room=True, simulate_bench_dry_run=True
        )
        r2 = evaluate_realhw_imagedb_touch_shoeaudio_and_lockop_readiness(
            force_clean_room=True, simulate_bench_dry_run=True
        )
        self.assertEqual(r1.report_sha256, r2.report_sha256)
        md = render_phase248_markdown(r1)
        for token in (
            PHASE_248_SCHEMA,
            P248_CHECK_GROUP_A_ID,
            P248_CHECK_GROUP_B_ID,
            P248_CHECK_GROUP_C_ID,
            P248_CHECK_GROUP_D_ID,
            r1.report_sha256,
        ):
            self.assertIn(token, md)

    def test_61_cli_offline_default_fails_closed_rc1_awaiting_physical_tier0_receipt(
        self,
    ) -> None:
        buf = io.StringIO()
        with mock.patch("sys.stdout", buf):
            rc = cli_main(
                [
                    "preflight-imagedb-touch-shoeaudio-and-lockop",
                    "--force-clean-room",
                    "--json",
                ]
            )
        self.assertEqual(rc, 1)
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["schema"], PHASE_248_SCHEMA)
        self.assertEqual(payload["go_no_go"], GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT)
        self.assertFalse(payload["overall_ready_for_hardware_attach"])
        self.assertFalse(payload["hardware_live_attachment_authorized"])

    def test_62_cli_simulate_bench_dry_run_emits_deterministic_json_and_markdown_rc0(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            json_path = Path(tmp) / "p248.json"
            md_path = Path(tmp) / "p248.md"
            buf = io.StringIO()
            with mock.patch("sys.stdout", buf):
                rc = cli_main(
                    [
                        "preflight-imagedb-touch-shoeaudio-and-lockop",
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
            self.assertTrue(verify_phase248_report(loaded).valid)
            md_text = md_path.read_text(encoding="utf-8")
            self.assertIn(PHASE_248_SCHEMA, md_text)

    def test_63_cli_blocks_violations_across_all_4_groups_rc1(self) -> None:
        for extra_flags in (
            ["--recover-image-db", "--battery-soc", "15.0"],
            ["--touch-operation", "ON"],
            ["--saveload-operation", "SAVE", "--saveload-target", "SLOT_1"],
            ["--destructive-format-chord"],
        ):
            buf = io.StringIO()
            with mock.patch("sys.stdout", buf):
                rc = cli_main(
                    [
                        "preflight-imagedb-touch-shoeaudio-and-lockop",
                        "--force-clean-room",
                        "--simulate-bench-dry-run",
                        "--json",
                        *extra_flags,
                    ]
                )
            self.assertEqual(rc, 1)
            payload = json.loads(buf.getvalue())
            self.assertEqual(
                payload["go_no_go"],
                GO_NO_GO_BLOCKED_IMAGEDB_TOUCH_SHOEAUDIO_LOCKOP_FAILURE,
            )

    def test_64_cli_blocks_same_filesystem_st_dev_receipt_files_rc1(self) -> None:
        raw_a, raw_b, _ = build_simulated_phase248_tier0_receipts()
        with tempfile.TemporaryDirectory() as tmp:
            pa = Path(tmp) / "rcpt_a.bin"
            pb = Path(tmp) / "rcpt_b.bin"
            pa.write_bytes(raw_a)
            pb.write_bytes(raw_b)
            buf = io.StringIO()
            with mock.patch("sys.stdout", buf):
                rc = cli_main(
                    [
                        "preflight-imagedb-touch-shoeaudio-and-lockop",
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
            self.assertEqual(rc, 1)
            payload = json.loads(buf.getvalue())
            self.assertTrue(any("st_dev_a == st_dev_b" in err for err in payload["errors"]))


if __name__ == "__main__":
    unittest.main()
