"""Dual-mode unit tests (58 cases) for Phase 227 (`preflight-pixelmap-ntscpal-powersave-and-autotemp`):
Physical Bench & Pre-Shoot Media Readiness Verifier across Waves 29–31 check groups (`A..C`).

Runs deterministically in both `LOCAL_DONOR_O_RDONLY` and `FX3_FX6_FORCE_CLEAN_ROOM=1`
modes with zero `.pyc` emission, zero persistent writes, and `< 2.0s` runtime.
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
from fx6_closure.realhw_pixelmap_ntscpal_powersave_and_autotemp_verifier import (  # noqa: E402
    CHECK_GROUP_A_ID,
    CHECK_GROUP_B_ID,
    CHECK_GROUP_C_ID,
    CIZ_FOUR_AF_METERING_LOCKS,
    GA_ERR_AUTO_PIXEL_MAPPING_CADENCE_OR_SHUTTER,
    GA_ERR_CNFLASHA_USERSPACE_RO_FIREWALL_VIOLATION,
    GA_ERR_GAMMA_ASSIST_EXTERNAL_HDMI_FORBIDDEN,
    GA_ERR_GAMMA_ASSIST_VS_DISPLAY_LUT_SPLIT,
    GA_ERR_MODEL_OR_FW_FLOOR,
    GA_ERR_NTSCPAL_FRAMERATE_OR_TC_FORMAT_CONFLICT,
    GA_ERR_NTSCPAL_RESET_PERSISTENCE_OR_MEDIA_DB,
    GA_ERR_PIXEL_MAPPING_DURING_ACTIVE_TIER0_DUMP,
    GA_ERR_PIXEL_MAPPING_LOW_BATTERY_BLOCKED,
    GA_ERR_PIXEL_MAPPING_MANDATORY_RESTART_OR_CONTROL_LOCK,
    GB_ERR_EXT_LK_RELEASE_OR_SQ_TC_VIOLATION,
    GB_ERR_FILE_SETTINGS_TITLE_OR_NUMBER_INVALID,
    GB_ERR_REC_LAMP_COUPLED_BODY_AND_XLR_H1_VIOLATION,
    GB_ERR_SDHC_FILE_SETTINGS_UNAVAILABLE,
    GB_ERR_SHOT_MARK_MP4_XAVC_ONLY_VIOLATION,
    GB_ERR_SILENT_MODE_AUDIO_SIGNALS_LOCK,
    GB_ERR_TC_REGENERATE_SLOT1_OR_RECRUN_VIOLATION,
    GC_ERR_AUTO_POWER_OFF_TEMP_HIGH_REQUIRES_TRIPOD,
    GC_ERR_CIZ_FOUR_AF_METERING_LOCK_VIOLATION,
    GC_ERR_CIZ_RAW_HFR_OR_SCALE_FORBIDDEN,
    GC_ERR_FAN_OR_THERMAL_SAFETY_INTERLOCK,
    GC_ERR_H0_H3_IMMUTABILITY_DRIFT,
    GC_ERR_NPFZ100_P3_75MIB_DUMP_SLEEP_HAZARD,
    GC_ERR_POWER_SAVE_MENU_OR_BYPASS_INVALID,
    GC_ERR_STEADYSHOT_ACTIVE_CUTOFF_VIOLATION,
    GC_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID,
    GO_NO_GO_BLOCKED_PIXELMAP_NTSCPAL_POWERSAVE_AUTOTEMP_FAILURE,
    GO_NO_GO_PIXELMAP_NTSCPAL_POWERSAVE_AUTOTEMP_VERIFIED,
    PHASE_227_CHECK_GROUP_IDS,
    PHASE_227_SCHEMA,
    PHASE_227_VERSION,
    POWER_SAVE_MENU_EXACT_LABEL,
    POWER_SAVE_NINE_BYPASS_CONDITIONS,
    REC_LAMP_ALL_OFF,
    REC_LAMP_ALL_ON,
    REC_LAMP_ONLY_FRONT_OFF,
    WARN_EXT_LK_RELEASED_BY_TC_CHANGE,
    build_simulated_phase227_tier0_receipts,
    evaluate_check_group_a_pixelmap_ntscpal_and_gamma_split,
    evaluate_check_group_b_filesettings_tcregen_and_reclamp,
    evaluate_check_group_c_powersave_autotemp_steadyshot_ciz_and_tier0,
    evaluate_realhw_pixelmap_ntscpal_powersave_and_autotemp_readiness,
    inspect_phase227_donors_bounded,
    render_phase227_markdown,
    run_pixelmap_ntscpal_powersave_and_autotemp_preflight,
    verify_phase227_report,
)
from fx6_closure.realhw_sd_stageb_bundle_and_uninstaller import (  # noqa: E402
    DEFAULT_TARGET_BODY_SERIAL,
    DEFAULT_TARGET_EMMC_CID,
)


class TestPhase227PixelMapNtscPalPowerSaveAutoTempVerifier(unittest.TestCase):
    """58 deterministic dual-mode unit tests for Phase 227 pre-shoot bench verifier."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._suite_t0 = time.perf_counter()

    @classmethod
    def tearDownClass(cls) -> None:
        elapsed = time.perf_counter() - cls._suite_t0
        assert elapsed < 2.0, f"Phase 227 test suite exceeded <2.0s budget: {elapsed:.3f}s"

    # --- Group 0: Exports, Bounded Donor O_RDONLY & Clean-Room Parity (7 tests) ---

    def test_01_public_symbols_exported_in_fx6_closure(self) -> None:
        self.assertEqual(
            PHASE_227_SCHEMA,
            "realhw_pixelmap_ntscpal_powersave_and_autotemp_verifier_v1",
        )
        self.assertEqual(PHASE_227_VERSION, "227.0.0")
        self.assertTrue(hasattr(fx6_closure, "PHASE_227_SCHEMA"))
        self.assertTrue(
            hasattr(
                fx6_closure,
                "evaluate_realhw_pixelmap_ntscpal_powersave_and_autotemp_readiness",
            )
        )
        self.assertIs(
            run_pixelmap_ntscpal_powersave_and_autotemp_preflight,
            evaluate_realhw_pixelmap_ntscpal_powersave_and_autotemp_readiness,
        )
        self.assertEqual(
            PHASE_227_CHECK_GROUP_IDS,
            (CHECK_GROUP_A_ID, CHECK_GROUP_B_ID, CHECK_GROUP_C_ID),
        )

    def test_02_donor_inspection_respects_150ms_budget_default_mode(self) -> None:
        res = inspect_phase227_donors_bounded()
        self.assertTrue(res.passed)
        self.assertTrue(res.read_only_o_rdonly_enforced)
        self.assertTrue(res.within_150ms_budget)
        self.assertLess(res.elapsed_seconds, DONOR_INSPECTION_MAX_SECONDS)
        self.assertEqual(res.raw_firmware_bytes_leaked, 0)

    def test_03_donor_inspection_clean_room_synthetic_mode(self) -> None:
        res = inspect_phase227_donors_bounded(force_clean_room=True)
        self.assertTrue(res.passed)
        self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(res.raw_firmware_bytes_leaked, 0)

    def test_04_donor_inspection_env_var_force_clean_room(self) -> None:
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            res = inspect_phase227_donors_bounded()
        self.assertTrue(res.passed)
        self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_05_donor_inspection_missing_donors_fails_closed_when_forced_local(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            res = inspect_phase227_donors_bounded(fx6_lib_dir=Path(tmp), force_clean_room=False)
        self.assertFalse(res.passed)
        self.assertEqual(res.verification_mode, "LOCAL_DONOR_O_RDONLY")
        self.assertTrue(res.errors)

    def test_06_deterministic_report_sha256_across_repeated_evaluations(self) -> None:
        r1 = evaluate_realhw_pixelmap_ntscpal_powersave_and_autotemp_readiness(
            force_clean_room=True, simulate_bench_dry_run=True
        )
        r2 = evaluate_realhw_pixelmap_ntscpal_powersave_and_autotemp_readiness(
            force_clean_room=True, simulate_bench_dry_run=True
        )
        self.assertEqual(r1.report_sha256, r2.report_sha256)
        self.assertEqual(r1.go_no_go, GO_NO_GO_DRY_RUN_SIMULATED_READY)
        self.assertTrue(verify_phase227_report(r1.to_dict()).valid)

    def test_07_offline_default_blocks_awaiting_physical_tier0_receipt_with_hard_locks(self) -> None:
        rep = evaluate_realhw_pixelmap_ntscpal_powersave_and_autotemp_readiness()
        self.assertEqual(rep.go_no_go, GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT)
        self.assertTrue(rep.all_3_check_groups_passed)
        self.assertEqual(rep.check_groups_passed, 3)
        self.assertFalse(rep.tier0_receipt_verified)
        self.assertFalse(rep.hardware_live_attachment_authorized)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.persistent_write_release)
        self.assertFalse(rep.spi_nor_write_authorized)
        self.assertFalse(rep.el3_payload_transmit_authorized)
        self.assertFalse(rep.sd_physical_media_written)
        self.assertEqual(rep.usb_packets_transmitted, 0)
        self.assertEqual(rep.physical_usb_packets_emitted, 0)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)
        self.assertTrue(verify_phase227_report(rep.to_dict()).valid)

    # --- Group A: Pixel Mapping / cnflasha RO / NTSC-PAL Reset / Gamma vs LUT (15 tests) ---

    def test_08_group_a_nominal_ntsc_cine_ei_display_lut_passes(self) -> None:
        ga = evaluate_check_group_a_pixelmap_ntscpal_and_gamma_split()
        self.assertTrue(ga.passed)
        self.assertTrue(ga.pixel_mapping_allowed)
        self.assertTrue(ga.cnflasha_userspace_o_rdonly_enforced)
        self.assertEqual(ga.cnflasha_calibration_mutation_bytes, 0)
        self.assertEqual(ga.startup_notification_banner, "")
        self.assertEqual(ga.effective_gamma_display_assist, "OFF")
        self.assertEqual(ga.display_lut, "ON")
        self.assertFalse(ga.gamma_assist_applied_to_hdmi)

        ga_pal_region = evaluate_check_group_a_pixelmap_ntscpal_and_gamma_split(
            ntsc_pal_selector="NTSC", regional_default_system="PAL"
        )
        self.assertTrue(ga_pal_region.passed)
        self.assertEqual(ga_pal_region.startup_notification_banner, "Running on NTSC.")

    def test_09_group_a_rejects_foreign_model_or_sub_204_firmware(self) -> None:
        ga_model = evaluate_check_group_a_pixelmap_ntscpal_and_gamma_split(
            body_model_id=0x91030099
        )
        self.assertFalse(ga_model.passed)
        self.assertTrue(any(GA_ERR_MODEL_OR_FW_FLOOR in e for e in ga_model.errors))

        ga_fw = evaluate_check_group_a_pixelmap_ntscpal_and_gamma_split(body_fw="2.00")
        self.assertFalse(ga_fw.passed)
        self.assertTrue(any(GA_ERR_MODEL_OR_FW_FLOOR in e for e in ga_fw.errors))

    def test_10_group_a_blocks_manual_pixel_mapping_on_low_battery_soc_or_warning(self) -> None:
        ga_low = evaluate_check_group_a_pixelmap_ntscpal_and_gamma_split(
            manual_pixel_mapping_requested=True, battery_soc_pct=19.5
        )
        self.assertFalse(ga_low.passed)
        self.assertFalse(ga_low.pixel_mapping_allowed)
        self.assertTrue(any(GA_ERR_PIXEL_MAPPING_LOW_BATTERY_BLOCKED in e for e in ga_low.errors))

        ga_warn = evaluate_check_group_a_pixelmap_ntscpal_and_gamma_split(
            manual_pixel_mapping_requested=True,
            battery_soc_pct=25.0,
            low_battery_warning_active=True,
        )
        self.assertFalse(ga_warn.passed)
        self.assertTrue(any(GA_ERR_PIXEL_MAPPING_LOW_BATTERY_BLOCKED in e for e in ga_warn.errors))

    def test_11_group_a_blocks_pixel_mapping_during_active_tier0_dump(self) -> None:
        ga = evaluate_check_group_a_pixelmap_ntscpal_and_gamma_split(
            manual_pixel_mapping_requested=True, tier0_dump_active=True
        )
        self.assertFalse(ga.passed)
        self.assertFalse(ga.pixel_mapping_allowed)
        self.assertTrue(
            any(GA_ERR_PIXEL_MAPPING_DURING_ACTIVE_TIER0_DUMP in e for e in ga.errors)
        )

    def test_12_group_a_blocks_unguarded_cnflasha_calibration_mutation(self) -> None:
        for kwargs in (
            {"unguarded_calibration_attempt": True},
            {"cnflasha_userspace_o_rdonly_enforced": False},
            {"cnflasha_calibration_mutation_bytes": 4},
        ):
            ga = evaluate_check_group_a_pixelmap_ntscpal_and_gamma_split(**kwargs)
            self.assertFalse(ga.passed)
            self.assertTrue(
                any(GA_ERR_CNFLASHA_USERSPACE_RO_FIREWALL_VIOLATION in e for e in ga.errors)
            )

    def test_13_group_a_enforces_mandatory_auto_restart_and_stageb_ram_unmount(self) -> None:
        ga_ok = evaluate_check_group_a_pixelmap_ntscpal_and_gamma_split(
            manual_pixel_mapping_requested=True,
            battery_soc_pct=85.0,
            auto_restart_after_pixel_mapping=True,
            stageb_volatile_ram_unmounted_on_reboot=True,
        )
        self.assertTrue(ga_ok.passed)

        for bad_kw in (
            {"auto_restart_after_pixel_mapping": False},
            {"operator_controls_locked_during_calibration": False},
            {"stageb_volatile_ram_unmounted_on_reboot": False},
        ):
            ga_bad = evaluate_check_group_a_pixelmap_ntscpal_and_gamma_split(
                manual_pixel_mapping_requested=True, **bad_kw
            )
            self.assertFalse(ga_bad.passed)
            self.assertTrue(
                any(
                    GA_ERR_PIXEL_MAPPING_MANDATORY_RESTART_OR_CONTROL_LOCK in e
                    for e in ga_bad.errors
                )
            )

    def test_14_group_a_models_auto_pixel_mapping_shutter_sound_and_3day_cadence(self) -> None:
        ga_shutter = evaluate_check_group_a_pixelmap_ntscpal_and_gamma_split(
            expect_silent_mode_suppresses_auto_pixelmap_shutter=True
        )
        self.assertFalse(ga_shutter.passed)
        self.assertTrue(
            any(GA_ERR_AUTO_PIXEL_MAPPING_CADENCE_OR_SHUTTER in e for e in ga_shutter.errors)
        )

        ga_overdue = evaluate_check_group_a_pixelmap_ntscpal_and_gamma_split(
            auto_pixel_mapping="OFF", days_since_manual_pixel_mapping=4
        )
        self.assertFalse(ga_overdue.passed)
        self.assertTrue(
            any(GA_ERR_AUTO_PIXEL_MAPPING_CADENCE_OR_SHUTTER in e for e in ga_overdue.errors)
        )

        ga_timely = evaluate_check_group_a_pixelmap_ntscpal_and_gamma_split(
            auto_pixel_mapping="OFF", days_since_manual_pixel_mapping=3
        )
        self.assertTrue(ga_timely.passed)

    def test_15_group_a_ntsc_pal_survives_camera_settings_reset(self) -> None:
        ga = evaluate_check_group_a_pixelmap_ntscpal_and_gamma_split(
            ntsc_pal_selector="PAL",
            regional_default_system="NTSC",
            rec_frame_rate_fps=25.0,
            tc_format="UNAVAILABLE",
            reset_action="CAMERA_SETTINGS_RESET",
            claimed_ntsc_pal_after_reset="PAL",
        )
        self.assertTrue(ga.passed)
        self.assertTrue(ga.survives_camera_settings_reset)
        self.assertEqual(ga.effective_ntsc_pal_after_reset, "PAL")
        self.assertEqual(ga.startup_notification_banner, "Running on PAL.")

        ga_wrong = evaluate_check_group_a_pixelmap_ntscpal_and_gamma_split(
            ntsc_pal_selector="PAL",
            regional_default_system="NTSC",
            rec_frame_rate_fps=25.0,
            tc_format="UNAVAILABLE",
            reset_action="CAMERA_SETTINGS_RESET",
            claimed_ntsc_pal_after_reset="NTSC",
        )
        self.assertFalse(ga_wrong.passed)
        self.assertTrue(
            any(GA_ERR_NTSCPAL_RESET_PERSISTENCE_OR_MEDIA_DB in e for e in ga_wrong.errors)
        )

    def test_16_group_a_ntsc_pal_cleared_only_by_initialize(self) -> None:
        ga = evaluate_check_group_a_pixelmap_ntscpal_and_gamma_split(
            ntsc_pal_selector="PAL",
            regional_default_system="NTSC",
            rec_frame_rate_fps=25.0,
            tc_format="UNAVAILABLE",
            reset_action="INITIALIZE",
            claimed_ntsc_pal_after_reset="NTSC",
        )
        self.assertTrue(ga.passed)
        self.assertTrue(ga.cleared_only_by_initialize)
        self.assertEqual(ga.effective_ntsc_pal_after_reset, "NTSC")

        ga_wrong = evaluate_check_group_a_pixelmap_ntscpal_and_gamma_split(
            ntsc_pal_selector="PAL",
            regional_default_system="NTSC",
            rec_frame_rate_fps=25.0,
            tc_format="UNAVAILABLE",
            reset_action="INITIALIZE",
            claimed_ntsc_pal_after_reset="PAL",
        )
        self.assertFalse(ga_wrong.passed)
        self.assertTrue(
            any(GA_ERR_NTSCPAL_RESET_PERSISTENCE_OR_MEDIA_DB in e for e in ga_wrong.errors)
        )

    def test_17_group_a_pal_rejects_2398p_and_df_ndf_tc_format(self) -> None:
        ga_2398 = evaluate_check_group_a_pixelmap_ntscpal_and_gamma_split(
            ntsc_pal_selector="PAL", rec_frame_rate_fps=23.98, tc_format="UNAVAILABLE"
        )
        self.assertFalse(ga_2398.passed)
        self.assertTrue(
            any(GA_ERR_NTSCPAL_FRAMERATE_OR_TC_FORMAT_CONFLICT in e for e in ga_2398.errors)
        )

        ga_df = evaluate_check_group_a_pixelmap_ntscpal_and_gamma_split(
            ntsc_pal_selector="PAL", rec_frame_rate_fps=25.0, tc_format="DF"
        )
        self.assertFalse(ga_df.passed)
        self.assertTrue(
            any(GA_ERR_NTSCPAL_FRAMERATE_OR_TC_FORMAT_CONFLICT in e for e in ga_df.errors)
        )

    def test_18_group_a_ntsc_rejects_pal_25p_50p_100p(self) -> None:
        ga = evaluate_check_group_a_pixelmap_ntscpal_and_gamma_split(
            ntsc_pal_selector="NTSC", rec_frame_rate_fps=50.0, tc_format="NDF"
        )
        self.assertFalse(ga.passed)
        self.assertTrue(
            any(GA_ERR_NTSCPAL_FRAMERATE_OR_TC_FORMAT_CONFLICT in e for e in ga.errors)
        )

    def test_19_group_a_rejects_media_db_system_mismatch_requiring_reformat(self) -> None:
        ga = evaluate_check_group_a_pixelmap_ntscpal_and_gamma_split(
            ntsc_pal_selector="PAL",
            media_db_system="NTSC",
            rec_frame_rate_fps=25.0,
            tc_format="UNAVAILABLE",
        )
        self.assertFalse(ga.passed)
        self.assertTrue(
            any(GA_ERR_NTSCPAL_RESET_PERSISTENCE_OR_MEDIA_DB in e for e in ga.errors)
        )

    def test_20_group_a_locks_gamma_display_assist_off_when_log_shooting_on(self) -> None:
        for log_mode in ("ON", "CINE_EI", "CINE_EI_QUICK", "FLEXIBLE_ISO"):
            ga_bad = evaluate_check_group_a_pixelmap_ntscpal_and_gamma_split(
                log_shooting_mode=log_mode, gamma_display_assist="ON", display_lut="ON"
            )
            self.assertFalse(ga_bad.passed)
            self.assertEqual(ga_bad.effective_gamma_display_assist, "OFF")
            self.assertTrue(
                any(GA_ERR_GAMMA_ASSIST_VS_DISPLAY_LUT_SPLIT in e for e in ga_bad.errors)
            )

        ga_pp = evaluate_check_group_a_pixelmap_ntscpal_and_gamma_split(
            log_shooting_mode="OFF",
            gamma_display_assist="ON",
            gamma_disp_assist_type="S_LOG3_TO_709_800PCT",
            display_lut="OFF",
        )
        self.assertTrue(ga_pp.passed)
        self.assertEqual(ga_pp.effective_gamma_display_assist, "ON")

    def test_21_group_a_rejects_legacy_slog2_gamma_assist_type(self) -> None:
        ga = evaluate_check_group_a_pixelmap_ntscpal_and_gamma_split(
            log_shooting_mode="OFF",
            gamma_display_assist="ON",
            gamma_disp_assist_type="S_LOG2_TO_709",
        )
        self.assertFalse(ga.passed)
        self.assertTrue(any(GA_ERR_GAMMA_ASSIST_VS_DISPLAY_LUT_SPLIT in e for e in ga.errors))

    def test_22_group_a_blocks_gamma_display_assist_on_external_hdmi(self) -> None:
        ga = evaluate_check_group_a_pixelmap_ntscpal_and_gamma_split(
            expect_gamma_assist_on_external_hdmi=True
        )
        self.assertFalse(ga.passed)
        self.assertTrue(
            any(GA_ERR_GAMMA_ASSIST_EXTERNAL_HDMI_FORBIDDEN in e for e in ga.errors)
        )

    # --- Group B: File Settings 37-Char/SDHC + ShotMark MP4/XAVC + TC Regen Slot-1/EXT-LK + REC Lamp (15 tests) ---

    def test_23_group_b_nominal_37char_series_mp4_shotmark_and_coupled_reclamp_passes(
        self,
    ) -> None:
        exact_37 = "FX3_P227_BENCH_0123456789_ABCDEFGHIJK"
        self.assertEqual(len(exact_37), 37)
        gb = evaluate_check_group_b_filesettings_tcregen_and_reclamp(
            title_name=exact_37,
            clip_container_format="XAVC_HS_4K",
            shot_mark1_count=2,
            shot_mark2_count=1,
            rec_lamp_mode=REC_LAMP_ONLY_FRONT_OFF,
            xlr_h1_attached=True,
        )
        self.assertTrue(gb.passed)
        self.assertEqual(gb.title_ascii_length, 37)
        self.assertTrue(gb.shot_mark_mp4_xavc_only_verified)
        self.assertFalse(gb.front_tally_lit)
        self.assertTrue(gb.rear_tally_lit)
        self.assertTrue(gb.top_rec_button_lit)
        self.assertTrue(gb.xlr_h1_rec_lamp_lit)

    def test_24_group_b_rejects_38char_or_non_ascii_or_retroactive_title(self) -> None:
        for bad_kw in (
            {"title_name": "A" * 38},
            {"title_name": "FX3_镜头_01"},
            {"expect_retroactive_clip_rename": True},
        ):
            gb = evaluate_check_group_b_filesettings_tcregen_and_reclamp(**bad_kw)
            self.assertFalse(gb.passed)
            self.assertTrue(
                any(GB_ERR_FILE_SETTINGS_TITLE_OR_NUMBER_INVALID in e for e in gb.errors)
            )

    def test_25_group_b_file_number_reset_allowed_only_when_series_not_required(self) -> None:
        gb_blocked = evaluate_check_group_b_filesettings_tcregen_and_reclamp(
            file_number_mode="RESET", require_series_counter=True
        )
        self.assertFalse(gb_blocked.passed)
        self.assertTrue(
            any(GB_ERR_FILE_SETTINGS_TITLE_OR_NUMBER_INVALID in e for e in gb_blocked.errors)
        )

        gb_allowed = evaluate_check_group_b_filesettings_tcregen_and_reclamp(
            file_number_mode="RESET", require_series_counter=False
        )
        self.assertTrue(gb_allowed.passed)

    def test_26_group_b_rejects_invalid_cam_id_reel_or_slot_format_mismatch(self) -> None:
        for bad_kw in (
            {"cam_id": "AB"},
            {"reel_number": 0},
            {"reel_number": 1000},
            {"slot2_file_name_format": "TITLE"},
        ):
            gb = evaluate_check_group_b_filesettings_tcregen_and_reclamp(**bad_kw)
            self.assertFalse(gb.passed)
            self.assertTrue(
                any(GB_ERR_FILE_SETTINGS_TITLE_OR_NUMBER_INVALID in e for e in gb.errors)
            )

    def test_27_group_b_sdhc_locks_standard_file_format_and_blocks_custom_folder(self) -> None:
        gb_custom_fmt = evaluate_check_group_b_filesettings_tcregen_and_reclamp(
            slot2_media_type="SDHC", file_name_format="CAM_ID_PLUS_REEL"
        )
        self.assertFalse(gb_custom_fmt.passed)
        self.assertTrue(
            any(GB_ERR_SDHC_FILE_SETTINGS_UNAVAILABLE in e for e in gb_custom_fmt.errors)
        )

        gb_custom_folder = evaluate_check_group_b_filesettings_tcregen_and_reclamp(
            slot1_media_type="SDHC",
            file_name_format="STANDARD",
            custom_folder_name_requested=True,
        )
        self.assertFalse(gb_custom_folder.passed)
        self.assertTrue(
            any(GB_ERR_SDHC_FILE_SETTINGS_UNAVAILABLE in e for e in gb_custom_folder.errors)
        )

        gb_std_ok = evaluate_check_group_b_filesettings_tcregen_and_reclamp(
            slot1_media_type="SDHC",
            slot2_media_type="SDHC",
            file_name_format="STANDARD",
            custom_folder_name_requested=False,
        )
        self.assertTrue(gb_std_ok.passed)

    def test_28_group_b_shot_mark_mp4_xavc_only_rejects_jpeg_heif_raw_and_photo(self) -> None:
        for fmt in ("JPEG", "HEIF", "RAW", "ARW"):
            gb = evaluate_check_group_b_filesettings_tcregen_and_reclamp(
                clip_container_format=fmt, shot_mark1_count=1
            )
            self.assertFalse(gb.passed)
            self.assertTrue(
                any(GB_ERR_SHOT_MARK_MP4_XAVC_ONLY_VIOLATION in e for e in gb.errors)
            )

        gb_photo = evaluate_check_group_b_filesettings_tcregen_and_reclamp(
            shoot_mode="PHOTO", clip_container_format="XAVC_S_4K", shot_mark2_count=1
        )
        self.assertFalse(gb_photo.passed)
        self.assertTrue(
            any(GB_ERR_SHOT_MARK_MP4_XAVC_ONLY_VIOLATION in e for e in gb_photo.errors)
        )

    def test_29_group_b_shot_mark_requires_m01_xml_sidecar_and_valid_image_jump(self) -> None:
        gb_no_xml = evaluate_check_group_b_filesettings_tcregen_and_reclamp(
            shot_mark1_count=1, shot_mark_xml_sidecar_enabled=False
        )
        self.assertFalse(gb_no_xml.passed)
        self.assertTrue(
            any(GB_ERR_SHOT_MARK_MP4_XAVC_ONLY_VIOLATION in e for e in gb_no_xml.errors)
        )

        gb_bad_jump = evaluate_check_group_b_filesettings_tcregen_and_reclamp(
            image_jump_setting="SHOT_MARK3_ONLY"
        )
        self.assertFalse(gb_bad_jump.passed)
        self.assertTrue(
            any(GB_ERR_SHOT_MARK_MP4_XAVC_ONLY_VIOLATION in e for e in gb_bad_jump.errors)
        )

    def test_30_group_b_tc_regenerate_tracks_slot1_and_forces_rec_run(self) -> None:
        gb_ok = evaluate_check_group_b_filesettings_tcregen_and_reclamp(
            tc_make="REGENERATE", tc_run="REC_RUN", tc_regenerate_reference_slot=1
        )
        self.assertTrue(gb_ok.passed)
        self.assertEqual(gb_ok.effective_tc_run, "REC_RUN")
        self.assertTrue(gb_ok.tc_regenerate_slot1_tracked)

        gb_slot2 = evaluate_check_group_b_filesettings_tcregen_and_reclamp(
            tc_make="REGENERATE", tc_regenerate_reference_slot=2
        )
        self.assertFalse(gb_slot2.passed)
        self.assertTrue(
            any(GB_ERR_TC_REGENERATE_SLOT1_OR_RECRUN_VIOLATION in e for e in gb_slot2.errors)
        )

        gb_freerun = evaluate_check_group_b_filesettings_tcregen_and_reclamp(
            tc_make="REGENERATE", expect_free_run_under_regenerate=True
        )
        self.assertFalse(gb_freerun.passed)
        self.assertTrue(
            any(GB_ERR_TC_REGENERATE_SLOT1_OR_RECRUN_VIOLATION in e for e in gb_freerun.errors)
        )

    def test_31_group_b_emits_ext_lk_release_warning_when_switching_to_regenerate_or_rec_run(
        self,
    ) -> None:
        gb_warn = evaluate_check_group_b_filesettings_tcregen_and_reclamp(
            external_tc_jam_was_active=True,
            vmc_bncm1_ext_lk_required=False,
            tc_make="REGENERATE",
            tc_run="REC_RUN",
        )
        self.assertTrue(gb_warn.passed)
        self.assertTrue(gb_warn.ext_lk_released)
        self.assertIn(WARN_EXT_LK_RELEASED_BY_TC_CHANGE, gb_warn.warnings)

        gb_req_err = evaluate_check_group_b_filesettings_tcregen_and_reclamp(
            external_tc_jam_was_active=True,
            vmc_bncm1_ext_lk_required=True,
            tc_make="REGENERATE",
        )
        self.assertFalse(gb_req_err.passed)
        self.assertTrue(
            any(GB_ERR_EXT_LK_RELEASE_OR_SQ_TC_VIOLATION in e for e in gb_req_err.errors)
        )

    def test_32_group_b_blocks_hdmi_tc_output_in_sq_mode(self) -> None:
        gb = evaluate_check_group_b_filesettings_tcregen_and_reclamp(
            shoot_mode="S_AND_Q", hdmi_tc_output_enabled_in_sq=True
        )
        self.assertFalse(gb.passed)
        self.assertTrue(any(GB_ERR_EXT_LK_RELEASE_OR_SQ_TC_VIOLATION in e for e in gb.errors))

    def test_33_group_b_rec_lamp_off_silences_both_body_tally_and_xlr_h1_handle_lamp(
        self,
    ) -> None:
        for mode_tok in ("OFF", REC_LAMP_ALL_OFF):
            gb = evaluate_check_group_b_filesettings_tcregen_and_reclamp(
                rec_lamp_mode=mode_tok, xlr_h1_attached=True
            )
            self.assertTrue(gb.passed)
            self.assertEqual(gb.rec_lamp_mode, REC_LAMP_ALL_OFF)
            self.assertFalse(gb.front_tally_lit)
            self.assertFalse(gb.rear_tally_lit)
            self.assertFalse(gb.top_rec_button_lit)
            self.assertFalse(gb.xlr_h1_rec_lamp_lit)
            self.assertTrue(gb.body_and_xlr_h1_reclamp_coupled_ok)

    def test_34_group_b_rec_lamp_all_on_and_only_front_off_keep_rear_top_and_xlr_h1_coupled(
        self,
    ) -> None:
        gb_all_on = evaluate_check_group_b_filesettings_tcregen_and_reclamp(
            rec_lamp_mode=REC_LAMP_ALL_ON, xlr_h1_attached=True
        )
        self.assertTrue(gb_all_on.passed)
        self.assertEqual(
            (
                gb_all_on.front_tally_lit,
                gb_all_on.rear_tally_lit,
                gb_all_on.top_rec_button_lit,
                gb_all_on.xlr_h1_rec_lamp_lit,
            ),
            (True, True, True, True),
        )

        gb_no_handle = evaluate_check_group_b_filesettings_tcregen_and_reclamp(
            rec_lamp_mode=REC_LAMP_ONLY_FRONT_OFF, xlr_h1_attached=False
        )
        self.assertTrue(gb_no_handle.passed)
        self.assertEqual(
            (
                gb_no_handle.front_tally_lit,
                gb_no_handle.rear_tally_lit,
                gb_no_handle.top_rec_button_lit,
                gb_no_handle.xlr_h1_rec_lamp_lit,
            ),
            (False, True, True, False),
        )

    def test_35_group_b_rejects_uncoupled_rear_top_or_lit_xlr_h1_when_reclamp_off(self) -> None:
        gb_handle_lit = evaluate_check_group_b_filesettings_tcregen_and_reclamp(
            rec_lamp_mode="OFF", xlr_h1_attached=True, claimed_xlr_h1_rec_lamp_lit=True
        )
        self.assertFalse(gb_handle_lit.passed)
        self.assertTrue(
            any(GB_ERR_REC_LAMP_COUPLED_BODY_AND_XLR_H1_VIOLATION in e for e in gb_handle_lit.errors)
        )

        gb_uncoupled = evaluate_check_group_b_filesettings_tcregen_and_reclamp(
            rec_lamp_mode=REC_LAMP_ONLY_FRONT_OFF, expect_uncoupled_rear_vs_top_tally=True
        )
        self.assertFalse(gb_uncoupled.passed)
        self.assertTrue(
            any(GB_ERR_REC_LAMP_COUPLED_BODY_AND_XLR_H1_VIOLATION in e for e in gb_uncoupled.errors)
        )

    def test_36_group_b_rejects_invalid_rec_lamp_enum(self) -> None:
        gb = evaluate_check_group_b_filesettings_tcregen_and_reclamp(
            rec_lamp_mode="REAR_ONLY_OFF"
        )
        self.assertFalse(gb.passed)
        self.assertTrue(
            any(GB_ERR_REC_LAMP_COUPLED_BODY_AND_XLR_H1_VIOLATION in e for e in gb.errors)
        )

    def test_37_group_b_enforces_silent_mode_audio_signals_off_lock(self) -> None:
        gb_bad = evaluate_check_group_b_filesettings_tcregen_and_reclamp(
            silent_mode_enabled=True, audio_signals_mode="ON"
        )
        self.assertFalse(gb_bad.passed)
        self.assertTrue(any(GB_ERR_SILENT_MODE_AUDIO_SIGNALS_LOCK in e for e in gb_bad.errors))

        gb_ok = evaluate_check_group_b_filesettings_tcregen_and_reclamp(
            silent_mode_enabled=True, audio_signals_mode="OFF"
        )
        self.assertTrue(gb_ok.passed)

    # --- Group C: Power Save 9-Condition + AutoTemp Tripod + SteadyShot + CIZ + Tier-0 (15 tests) ---

    def test_38_group_c_enforces_power_save_off_or_30min_on_np_fz100_during_75mib_p3_dump(
        self,
    ) -> None:
        for safe_val in ("OFF", "30 Min"):
            gc_ok, _ = evaluate_check_group_c_powersave_autotemp_steadyshot_ciz_and_tier0(
                power_save_start_time=safe_val,
                power_source="INTERNAL_NP_FZ100",
                p3_75mib_cold_dump_active=True,
                simulate_bench_dry_run=True,
            )
            self.assertTrue(gc_ok.passed)
            self.assertTrue(gc_ok.np_fz100_p3_dump_sleep_safe)

        for unsafe_val in ("5_MIN", "2_MIN", "1_MIN", "10_SEC"):
            gc_bad, _ = evaluate_check_group_c_powersave_autotemp_steadyshot_ciz_and_tier0(
                power_save_start_time=unsafe_val,
                power_source="INTERNAL_NP_FZ100",
                p3_75mib_cold_dump_active=True,
                simulate_bench_dry_run=True,
            )
            self.assertFalse(gc_bad.passed)
            self.assertFalse(gc_bad.np_fz100_p3_dump_sleep_safe)
            self.assertTrue(
                any(GC_ERR_NPFZ100_P3_75MIB_DUMP_SLEEP_HAZARD in e for e in gc_bad.errors)
            )

    def test_39_group_c_verifies_all_9_individual_power_save_bypass_conditions(self) -> None:
        kw_to_cond = (
            ("usb_power_supply_active", "USB_POWER_SUPPLY"),
            ("slideshow_playback_active", "SLIDESHOW_PLAYBACK"),
            ("ftp_transfer_active", "FTP_TRANSFER"),
            ("movie_recording_active", "MOVIE_RECORDING"),
            ("computer_connection_active", "COMPUTER_CONNECTION"),
            ("hdmi_tv_connection_active", "TV_HDMI_CONNECTION"),
            ("ir_remote_ctrl_on", "IR_REMOTE_CTRL_ON"),
            ("bluetooth_rmt_ctrl_on", "BLUETOOTH_RMT_CTRL_ON"),
            ("streaming_or_cloud_active", "STREAMING_OR_CLOUD_UPLOAD"),
        )
        self.assertEqual(len(kw_to_cond), 9)
        self.assertEqual(
            tuple(cond for _, cond in kw_to_cond), POWER_SAVE_NINE_BYPASS_CONDITIONS
        )
        for kw_name, expected_cond in kw_to_cond:
            gc, _ = evaluate_check_group_c_powersave_autotemp_steadyshot_ciz_and_tier0(
                power_save_start_time="1_MIN",
                power_source="INTERNAL_NP_FZ100",
                p3_75mib_cold_dump_active=True,
                simulate_bench_dry_run=True,
                **{kw_name: True},
            )
            self.assertTrue(gc.passed, msg=f"Failed for bypass {kw_name}")
            self.assertTrue(gc.power_save_bypassed)
            self.assertEqual(gc.active_bypass_conditions, (expected_cond,))

    def test_40_group_c_rejects_wrong_power_save_menu_label_or_bypass_claim_mismatch(
        self,
    ) -> None:
        gc_label, _ = evaluate_check_group_c_powersave_autotemp_steadyshot_ciz_and_tier0(
            power_save_menu_label="Auto Power Off", simulate_bench_dry_run=True
        )
        self.assertFalse(gc_label.passed)
        self.assertEqual(POWER_SAVE_MENU_EXACT_LABEL, "Power Save Start Time")
        self.assertTrue(
            any(GC_ERR_POWER_SAVE_MENU_OR_BYPASS_INVALID in e for e in gc_label.errors)
        )

        gc_claim, _ = evaluate_check_group_c_powersave_autotemp_steadyshot_ciz_and_tier0(
            claimed_power_save_bypassed=True, simulate_bench_dry_run=True
        )
        self.assertFalse(gc_claim.passed)
        self.assertTrue(
            any(GC_ERR_POWER_SAVE_MENU_OR_BYPASS_INVALID in e for e in gc_claim.errors)
        )

    def test_41_group_c_enforces_tripod_mounting_when_auto_power_off_temp_high(self) -> None:
        for bad_kw in (
            {"tripod_mounted": False},
            {"handheld_operation_active": True},
        ):
            gc, _ = evaluate_check_group_c_powersave_autotemp_steadyshot_ciz_and_tier0(
                auto_power_off_temp="HIGH", simulate_bench_dry_run=True, **bad_kw
            )
            self.assertFalse(gc.passed)
            self.assertTrue(
                any(GC_ERR_AUTO_POWER_OFF_TEMP_HIGH_REQUIRES_TRIPOD in e for e in gc.errors)
            )

        gc_std, _ = evaluate_check_group_c_powersave_autotemp_steadyshot_ciz_and_tier0(
            auto_power_off_temp="STANDARD",
            tripod_mounted=False,
            handheld_operation_active=True,
            simulate_bench_dry_run=True,
        )
        self.assertTrue(gc_std.passed)

    def test_42_group_c_blocks_fan_always_off_or_overtemp_body_start(self) -> None:
        gc_fan, _ = evaluate_check_group_c_powersave_autotemp_steadyshot_ciz_and_tier0(
            fan_control_mode="ALWAYS_OFF", simulate_bench_dry_run=True
        )
        self.assertFalse(gc_fan.passed)
        self.assertTrue(
            any(GC_ERR_FAN_OR_THERMAL_SAFETY_INTERLOCK in e for e in gc_fan.errors)
        )

        gc_hot, _ = evaluate_check_group_c_powersave_autotemp_steadyshot_ciz_and_tier0(
            body_temp_c=45.0, simulate_bench_dry_run=True
        )
        self.assertFalse(gc_hot.passed)
        self.assertTrue(
            any(GC_ERR_FAN_OR_THERMAL_SAFETY_INTERLOCK in e for e in gc_hot.errors)
        )

    def test_43_group_c_steadyshot_active_passes_at_2398p_with_1_1x_crop_and_8_to_1000mm_focal(
        self,
    ) -> None:
        gc, _ = evaluate_check_group_c_powersave_autotemp_steadyshot_ciz_and_tier0(
            steadyshot_mode="ACTIVE",
            rec_frame_rate_fps=23.98,
            steadyshot_manual_focal_mm=50,
            simulate_bench_dry_run=True,
        )
        self.assertTrue(gc.passed)
        self.assertAlmostEqual(gc.steadyshot_crop_factor, 1.1)

        for bad_focal in (7, 1001):
            gc_bad, _ = evaluate_check_group_c_powersave_autotemp_steadyshot_ciz_and_tier0(
                steadyshot_mode="ACTIVE",
                steadyshot_manual_focal_mm=bad_focal,
                simulate_bench_dry_run=True,
            )
            self.assertFalse(gc_bad.passed)
            self.assertTrue(
                any(GC_ERR_STEADYSHOT_ACTIVE_CUTOFF_VIOLATION in e for e in gc_bad.errors)
            )

    def test_44_group_c_steadyshot_active_cutoff_1_blocks_119_88p_and_100p(self) -> None:
        for hfr_fps in (119.88, 100.0):
            gc, _ = evaluate_check_group_c_powersave_autotemp_steadyshot_ciz_and_tier0(
                steadyshot_mode="ACTIVE",
                rec_frame_rate_fps=hfr_fps,
                simulate_bench_dry_run=True,
            )
            self.assertFalse(gc.passed)
            self.assertIn("NORMAL_MOVIE_100P_119_88P_OR_HIGHER", gc.steadyshot_active_cutoff_reasons)
            self.assertTrue(
                any(GC_ERR_STEADYSHOT_ACTIVE_CUTOFF_VIOLATION in e for e in gc.errors)
            )

    def test_45_group_c_steadyshot_active_cutoff_2_blocks_sq_120fps_and_100fps(self) -> None:
        for sq_fps in (120.0, 100.0):
            gc, _ = evaluate_check_group_c_powersave_autotemp_steadyshot_ciz_and_tier0(
                steadyshot_mode="ACTIVE",
                sq_mode_enabled=True,
                sq_frame_rate_fps=sq_fps,
                simulate_bench_dry_run=True,
            )
            self.assertFalse(gc.passed)
            self.assertIn("S_AND_Q_100FPS_120FPS_OR_HIGHER", gc.steadyshot_active_cutoff_reasons)
            self.assertTrue(
                any(GC_ERR_STEADYSHOT_ACTIVE_CUTOFF_VIOLATION in e for e in gc.errors)
            )

    def test_46_group_c_steadyshot_active_cutoff_3_blocks_hdmi_raw_output(self) -> None:
        gc, _ = evaluate_check_group_c_powersave_autotemp_steadyshot_ciz_and_tier0(
            steadyshot_mode="ACTIVE",
            hdmi_raw_output=True,
            simulate_bench_dry_run=True,
        )
        self.assertFalse(gc.passed)
        self.assertIn("HDMI_RAW_OUTPUT_ACTIVE", gc.steadyshot_active_cutoff_reasons)
        self.assertTrue(any(GC_ERR_STEADYSHOT_ACTIVE_CUTOFF_VIOLATION in e for e in gc.errors))

    def test_47_group_c_ciz_scale_limits_1_5x_4k_2_0x_hd_and_4_0x_digital(self) -> None:
        gc_4k_ok, _ = evaluate_check_group_c_powersave_autotemp_steadyshot_ciz_and_tier0(
            zoom_mode="CLEAR_IMAGE_ZOOM",
            zoom_scale=1.5,
            video_resolution_class="4K",
            simulate_bench_dry_run=True,
        )
        self.assertTrue(gc_4k_ok.passed)

        gc_4k_over, _ = evaluate_check_group_c_powersave_autotemp_steadyshot_ciz_and_tier0(
            zoom_mode="CLEAR_IMAGE_ZOOM",
            zoom_scale=1.6,
            video_resolution_class="4K",
            simulate_bench_dry_run=True,
        )
        self.assertFalse(gc_4k_over.passed)
        self.assertTrue(
            any(GC_ERR_CIZ_RAW_HFR_OR_SCALE_FORBIDDEN in e for e in gc_4k_over.errors)
        )

        gc_hd_ok, _ = evaluate_check_group_c_powersave_autotemp_steadyshot_ciz_and_tier0(
            zoom_mode="CLEAR_IMAGE_ZOOM",
            zoom_scale=2.0,
            video_resolution_class="HD",
            simulate_bench_dry_run=True,
        )
        self.assertTrue(gc_hd_ok.passed)

        gc_dz_ok, _ = evaluate_check_group_c_powersave_autotemp_steadyshot_ciz_and_tier0(
            zoom_mode="DIGITAL_ZOOM",
            zoom_scale=4.0,
            video_resolution_class="4K",
            simulate_bench_dry_run=True,
        )
        self.assertTrue(gc_dz_ok.passed)

    def test_48_group_c_ciz_blocks_raw_stills_and_100p_120fps_hfr(self) -> None:
        for bad_kw in (
            {"still_file_format": "RAW"},
            {"rec_frame_rate_fps": 119.88},
            {"sq_mode_enabled": True, "sq_frame_rate_fps": 100.0},
        ):
            gc, _ = evaluate_check_group_c_powersave_autotemp_steadyshot_ciz_and_tier0(
                zoom_mode="CLEAR_IMAGE_ZOOM",
                zoom_scale=1.3,
                simulate_bench_dry_run=True,
                **bad_kw,
            )
            self.assertFalse(gc.passed)
            self.assertTrue(any(GC_ERR_CIZ_RAW_HFR_OR_SCALE_FORBIDDEN in e for e in gc.errors))

    def test_49_group_c_ciz_enforces_all_4_af_and_metering_locks(self) -> None:
        self.assertEqual(len(CIZ_FOUR_AF_METERING_LOCKS), 4)
        for bad_lock_kw in (
            {"ciz_focus_area_center_locked": False},
            {"ciz_metering_mode": "SPOT"},
            {"ciz_face_eye_priority_disabled": False},
            {"ciz_realtime_tracking_disabled": False},
        ):
            gc, _ = evaluate_check_group_c_powersave_autotemp_steadyshot_ciz_and_tier0(
                zoom_mode="CLEAR_IMAGE_ZOOM",
                zoom_scale=1.4,
                simulate_bench_dry_run=True,
                **bad_lock_kw,
            )
            self.assertFalse(gc.passed)
            self.assertFalse(gc.ciz_four_locks_satisfied)
            self.assertTrue(
                any(GC_ERR_CIZ_FOUR_AF_METERING_LOCK_VIOLATION in e for e in gc.errors)
            )

    def test_50_group_c_detects_h0_h3_immutability_drift(self) -> None:
        gc, _ = evaluate_check_group_c_powersave_autotemp_steadyshot_ciz_and_tier0(
            simulated_h0_h3_drifted_surfaces=1, simulate_bench_dry_run=True
        )
        self.assertFalse(gc.passed)
        self.assertEqual(gc.h0_equals_h3_count, 15)
        self.assertTrue(any(GC_ERR_H0_H3_IMMUTABILITY_DRIFT in e for e in gc.errors))

    def test_51_group_c_verifies_physical_dual_media_fx3rcpt1_and_rejects_same_st_dev(
        self,
    ) -> None:
        raw_a, raw_b, baselines = build_simulated_phase227_tier0_receipts()
        rep_ok = evaluate_realhw_pixelmap_ntscpal_powersave_and_autotemp_readiness(
            force_clean_room=True,
            simulate_bench_dry_run=False,
            receipt_a_bytes=raw_a,
            receipt_b_bytes=raw_b,
            st_dev_a_override=11,
            st_dev_b_override=22,
            body_serial=DEFAULT_TARGET_BODY_SERIAL,
            emmc_cid=DEFAULT_TARGET_EMMC_CID,
            h0_baselines_a=baselines,
            h0_baselines_b=dict(baselines),
        )
        self.assertEqual(rep_ok.go_no_go, GO_NO_GO_PIXELMAP_NTSCPAL_POWERSAVE_AUTOTEMP_VERIFIED)
        self.assertTrue(rep_ok.tier0_receipt_verified)
        self.assertFalse(rep_ok.hardware_live_attachment_authorized)
        self.assertTrue(verify_phase227_report(rep_ok.to_dict()).valid)

        rep_same_dev = evaluate_realhw_pixelmap_ntscpal_powersave_and_autotemp_readiness(
            force_clean_room=True,
            simulate_bench_dry_run=False,
            receipt_a_bytes=raw_a,
            receipt_b_bytes=raw_b,
            st_dev_a_override=11,
            st_dev_b_override=11,
            body_serial=DEFAULT_TARGET_BODY_SERIAL,
            emmc_cid=DEFAULT_TARGET_EMMC_CID,
            h0_baselines_a=baselines,
            h0_baselines_b=dict(baselines),
        )
        self.assertEqual(
            rep_same_dev.go_no_go, GO_NO_GO_BLOCKED_PIXELMAP_NTSCPAL_POWERSAVE_AUTOTEMP_FAILURE
        )
        self.assertTrue(
            any(
                GC_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID in e
                for e in rep_same_dev.errors
            )
        )

    def test_52_group_c_rejects_corrupted_fx3rcpt1_or_trivial_serial_cid(self) -> None:
        raw_a, raw_b, baselines = build_simulated_phase227_tier0_receipts()
        corrupted = bytearray(raw_b)
        corrupted[16] ^= 0xFF
        rep_corrupt = evaluate_realhw_pixelmap_ntscpal_powersave_and_autotemp_readiness(
            force_clean_room=True,
            receipt_a_bytes=raw_a,
            receipt_b_bytes=bytes(corrupted),
            st_dev_a_override=11,
            st_dev_b_override=22,
            body_serial=DEFAULT_TARGET_BODY_SERIAL,
            emmc_cid=DEFAULT_TARGET_EMMC_CID,
            h0_baselines_a=baselines,
            h0_baselines_b=dict(baselines),
        )
        self.assertEqual(
            rep_corrupt.go_no_go, GO_NO_GO_BLOCKED_PIXELMAP_NTSCPAL_POWERSAVE_AUTOTEMP_FAILURE
        )

        rep_triv = evaluate_realhw_pixelmap_ntscpal_powersave_and_autotemp_readiness(
            force_clean_room=True,
            receipt_a_bytes=raw_a,
            receipt_b_bytes=raw_b,
            st_dev_a_override=11,
            st_dev_b_override=22,
            body_serial="0000000",
            emmc_cid="0" * 32,
            h0_baselines_a=baselines,
            h0_baselines_b=dict(baselines),
        )
        self.assertEqual(
            rep_triv.go_no_go, GO_NO_GO_BLOCKED_PIXELMAP_NTSCPAL_POWERSAVE_AUTOTEMP_FAILURE
        )

    # --- Group D: Tamper Verifier, Markdown Renderer & CLI Subcommand (6 tests) ---

    def test_53_verify_phase227_report_detects_safety_lock_or_counter_tampering(self) -> None:
        base = evaluate_realhw_pixelmap_ntscpal_powersave_and_autotemp_readiness(
            force_clean_room=True, simulate_bench_dry_run=True
        ).to_dict()
        for field, bad_val in (
            ("hardware_live_attachment_authorized", True),
            ("persistent_emmc_writes_authorized", True),
            ("spi_nor_write_authorized", True),
            ("usb_packets_transmitted", 1),
            ("raw_firmware_bytes_leaked", 8),
        ):
            tampered = dict(base)
            tampered[field] = bad_val
            v_res = verify_phase227_report(tampered)
            self.assertFalse(v_res.valid, msg=f"Expected failure for {field}")

    def test_54_verify_phase227_report_detects_sha256_or_simulated_verdict_escalation(
        self,
    ) -> None:
        base = evaluate_realhw_pixelmap_ntscpal_powersave_and_autotemp_readiness(
            force_clean_room=True, simulate_bench_dry_run=True
        ).to_dict()
        escalated = dict(base)
        escalated["go_no_go"] = GO_NO_GO_PIXELMAP_NTSCPAL_POWERSAVE_AUTOTEMP_VERIFIED
        self.assertFalse(verify_phase227_report(escalated).valid)

        bad_sha = dict(base)
        bad_sha["report_sha256"] = "a" * 64
        self.assertFalse(verify_phase227_report(bad_sha).valid)

    def test_55_cli_offline_default_fails_closed_rc1_awaiting_physical_tier0_receipt(
        self,
    ) -> None:
        buf = io.StringIO()
        with mock.patch("sys.stdout", buf):
            rc = cli_main(
                [
                    "preflight-pixelmap-ntscpal-powersave-and-autotemp",
                    "--force-clean-room",
                    "--json",
                ]
            )
        self.assertEqual(rc, 1)
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["schema"], PHASE_227_SCHEMA)
        self.assertEqual(payload["go_no_go"], GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT)
        self.assertFalse(payload["hardware_live_attachment_authorized"])

    def test_56_cli_simulate_bench_dry_run_emits_deterministic_json_and_markdown_rc0(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            json_path = Path(tmp) / "p227.json"
            md_path = Path(tmp) / "p227.md"
            buf = io.StringIO()
            with mock.patch("sys.stdout", buf):
                rc = cli_main(
                    [
                        "preflight-pixelmap-ntscpal-powersave-and-autotemp",
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
            self.assertTrue(verify_phase227_report(loaded).valid)
            md_text = md_path.read_text(encoding="utf-8")
            self.assertIn(PHASE_227_SCHEMA, md_text)
            self.assertIn(CHECK_GROUP_A_ID, md_text)
            self.assertIn(CHECK_GROUP_B_ID, md_text)
            self.assertIn(CHECK_GROUP_C_ID, md_text)

    def test_57_cli_blocks_np_fz100_p3_sleep_hazard_and_handheld_autotemp_high_rc1(
        self,
    ) -> None:
        for extra_flags in (
            ["--power-save-start-time", "1_MIN"],
            ["--handheld-active"],
        ):
            buf = io.StringIO()
            with mock.patch("sys.stdout", buf):
                rc = cli_main(
                    [
                        "preflight-pixelmap-ntscpal-powersave-and-autotemp",
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
                GO_NO_GO_BLOCKED_PIXELMAP_NTSCPAL_POWERSAVE_AUTOTEMP_FAILURE,
            )

    def test_58_cli_verifies_dual_receipt_files_and_markdown_renderer(self) -> None:
        raw_a, raw_b, _ = build_simulated_phase227_tier0_receipts()
        with tempfile.TemporaryDirectory() as tmp:
            pa = Path(tmp) / "rcpt_a.bin"
            pb = Path(tmp) / "rcpt_b.bin"
            pa.write_bytes(raw_a)
            pb.write_bytes(raw_b)
            # Same tmpfs directory has st_dev_a == st_dev_b, so fail-closed rc == 1
            buf = io.StringIO()
            with mock.patch("sys.stdout", buf):
                rc = cli_main(
                    [
                        "preflight-pixelmap-ntscpal-powersave-and-autotemp",
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
            self.assertTrue(
                any("st_dev_a == st_dev_b" in err for err in payload["errors"])
            )
            rep = evaluate_realhw_pixelmap_ntscpal_powersave_and_autotemp_readiness(
                force_clean_room=True, simulate_bench_dry_run=True
            )
            self.assertIn(rep.report_sha256, render_phase227_markdown(rep))


if __name__ == "__main__":
    unittest.main()
