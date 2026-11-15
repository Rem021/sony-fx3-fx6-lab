"""Dual-mode unit tests (56 cases) for Phase 216 (`preflight-hdmi-proxy-desqueeze-and-simult`):
Physical Shoot & Monitoring Readiness Preflight across Waves 27–29 checklists (`S1..S5`).

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
    GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT,
    GO_NO_GO_DRY_RUN_SIMULATED_READY,
)
from fx6_closure.realhw_hdmi_proxy_desqueeze_and_simult_verifier import (  # noqa: E402
    CHECKLIST_S1_ID,
    CHECKLIST_S2_ID,
    CHECKLIST_S3_ID,
    CHECKLIST_S4_ID,
    CHECKLIST_S5_ID,
    DONOR_INSPECTION_MAX_SECONDS,
    GO_NO_GO_BLOCKED_HDMI_PROXY_DESQUEEZE_SIMULT_FAILURE,
    GO_NO_GO_HDMI_PROXY_DESQUEEZE_SIMULT_VERIFIED,
    HDMI_REC_MEDIA_OFF_HDMI_ONLY,
    HDMI_REC_MEDIA_ON,
    PHASE_216_CHECKLIST_IDS,
    PHASE_216_SCHEMA,
    PHASE_216_VERSION,
    REC_LAMP_ALL_OFF,
    REC_LAMP_ALL_ON,
    REC_LAMP_ONLY_FRONT_OFF,
    S1_ERR_DESQUEEZE_FOUR_SETTING_LOCK_VIOLATION,
    S1_ERR_DESQUEEZE_SUPPRESSED_STATE_CONFLICT,
    S1_ERR_FOCUS_MAG_OR_BRIGHT_MON_CONFLICT,
    S1_ERR_IN_BODY_FOCUS_MAP_FORBIDDEN,
    S1_ERR_MC_FOCUS_MAP_150FPS_OR_LENS_LIMIT,
    S1_ERR_MODEL_OR_FW_FLOOR,
    S1_ERR_UNSUPPORTED_DESQUEEZE_RATIO,
    S2_ERR_BUILT_IN_LCD_BLANKED_UNACKNOWLEDGED,
    S2_ERR_HDMI_INFO_DISPLAY_FORCED_OFF_CONFLICT,
    S2_ERR_HDMI_LOG_OR_PPLUT_FORCES_1080P_DOWNSHIFT,
    S2_ERR_HDMI_ONLY_24P_REQUIRES_DCI_GATE,
    S2_ERR_HDMI_ONLY_DISABLES_INTERNAL_CARD_REC,
    S3_ERR_AUTO_SWITCH_BREAKS_STRICT_VAULT_PARITY,
    S3_ERR_CLIP_SUB_COUPLED_DELETE_PROTECT_BROKEN,
    S3_ERR_PROXY_IN_CAMERA_PLAYBACK_UNSUPPORTED,
    S3_ERR_PROXY_UNSUPPORTED_FORMAT_OR_CUTOFF_100FPS,
    S3_ERR_SIMULT_DUAL_SLOT_EXFAT_OR_PARITY,
    S4_ERR_FILE_SETTINGS_TITLE_OR_SERIES_COUNTER,
    S4_ERR_SDHC_FORCES_STANDARD_FILE_FORMAT,
    S4_ERR_SHOT_MARK_XML_SIDECAR_MISMATCH,
    S4_ERR_TC_REGENERATE_SLOT1_OR_RECRUN_VIOLATION,
    S4_ERR_VMC_BNCM1_EXT_LK_OR_SQ_TC_VIOLATION,
    S5_ERR_H0_H3_IMMUTABILITY_DRIFT,
    S5_ERR_REC_LAMP_COUPLED_REAR_TOP_VIOLATION,
    S5_ERR_SHOCKLESS_WB_ZERO_FRAME_KELVIN_GRID,
    S5_ERR_SILENT_MODE_AUDIO_SIGNALS_LOCK,
    S5_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID,
    WARN_HDMI_INFO_DISPLAY_ON_BLANKS_LCD,
    build_simulated_phase216_tier0_receipts,
    evaluate_checklist_1_desqueeze_and_mc_focus_map,
    evaluate_checklist_2_hdmi_log_and_blank_lcd,
    evaluate_checklist_3_simult_autoswitch_and_proxy_vault,
    evaluate_checklist_4_file_settings_shotmark_and_tc_slot1,
    evaluate_checklist_5_reclamp_shockless_wb_and_tier0_gate,
    evaluate_realhw_hdmi_proxy_desqueeze_and_simult_readiness,
    inspect_phase216_donors_bounded,
    render_phase216_markdown,
    verify_phase216_report,
)
from fx6_closure.realhw_sd_stageb_bundle_and_uninstaller import (  # noqa: E402
    DEFAULT_TARGET_BODY_SERIAL,
    DEFAULT_TARGET_EMMC_CID,
)


class TestPhase216HdmiProxyDesqueezeAndSimultVerifier(unittest.TestCase):
    """56 deterministic dual-mode unit tests for Phase 216 pre-shoot bench verifier."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._suite_t0 = time.perf_counter()

    @classmethod
    def tearDownClass(cls) -> None:
        elapsed = time.perf_counter() - cls._suite_t0
        assert elapsed < 2.0, f"Phase 216 test suite exceeded <2.0s budget: {elapsed:.3f}s"

    # --- Group 0: Exports, Donor O_RDONLY & Clean-Room Parity (6 tests) ---

    def test_01_public_symbols_exported_in_fx6_closure(self) -> None:
        self.assertTrue(hasattr(fx6_closure, "PHASE_216_SCHEMA"))
        self.assertTrue(hasattr(fx6_closure, "evaluate_realhw_hdmi_proxy_desqueeze_and_simult_readiness"))
        self.assertEqual(
            PHASE_216_CHECKLIST_IDS,
            (CHECKLIST_S1_ID, CHECKLIST_S2_ID, CHECKLIST_S3_ID, CHECKLIST_S4_ID, CHECKLIST_S5_ID),
        )

    def test_02_donor_inspection_respects_150ms_budget_default_mode(self) -> None:
        res = inspect_phase216_donors_bounded()
        self.assertTrue(res.passed)
        self.assertTrue(res.read_only_o_rdonly_enforced)
        self.assertTrue(res.within_150ms_budget)
        self.assertLess(res.elapsed_seconds, DONOR_INSPECTION_MAX_SECONDS)
        self.assertEqual(res.raw_firmware_bytes_leaked, 0)

    def test_03_donor_inspection_clean_room_synthetic_mode(self) -> None:
        res = inspect_phase216_donors_bounded(force_clean_room=True)
        self.assertTrue(res.passed)
        self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(res.raw_firmware_bytes_leaked, 0)

    def test_04_donor_inspection_env_var_force_clean_room(self) -> None:
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            res = inspect_phase216_donors_bounded()
        self.assertTrue(res.passed)
        self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_05_donor_inspection_missing_donors_fails_closed_when_forced_local(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            res = inspect_phase216_donors_bounded(fx6_lib_dir=Path(tmp), force_clean_room=False)
        self.assertFalse(res.passed)
        self.assertEqual(res.verification_mode, "LOCAL_DONOR_O_RDONLY")
        self.assertTrue(res.errors)

    def test_06_deterministic_report_sha256_across_repeated_evaluations(self) -> None:
        r1 = evaluate_realhw_hdmi_proxy_desqueeze_and_simult_readiness(
            force_clean_room=True, simulate_bench_dry_run=True
        )
        r2 = evaluate_realhw_hdmi_proxy_desqueeze_and_simult_readiness(
            force_clean_room=True, simulate_bench_dry_run=True
        )
        self.assertEqual(r1.report_sha256, r2.report_sha256)
        self.assertTrue(verify_phase216_report(r1.to_dict()).valid)
        self.assertTrue(verify_phase216_report(r2.to_dict()).valid)

    # --- Checklist 1: De-Squeeze (1.6x=1.65x), 4 Locks & External M&C Focus Map (11 tests) ---

    def test_07_s1_desqueeze_16x_maps_to_actual_165x_stretch(self) -> None:
        c1 = evaluate_checklist_1_desqueeze_and_mc_focus_map(desqueeze_ratio="1.6x")
        self.assertTrue(c1.passed)
        self.assertEqual(c1.desqueeze_ratio, "1.6X")
        self.assertAlmostEqual(c1.actual_desqueeze_factor, 1.65)
        self.assertAlmostEqual(c1.effective_desqueeze_factor, 1.65)
        self.assertFalse(c1.desqueeze_suppressed)

    def test_08_s1_desqueeze_all_supported_ratios_pass(self) -> None:
        expected = {"OFF": 1.0, "1.3x": 1.3, "1.5x": 1.5, "1.6x(1.65x)": 1.65, "1.8x": 1.8, "2.0x": 2.0}
        for label, factor in expected.items():
            c1 = evaluate_checklist_1_desqueeze_and_mc_focus_map(desqueeze_ratio=label)
            self.assertTrue(c1.passed, label)
            self.assertAlmostEqual(c1.actual_desqueeze_factor, factor)

    def test_09_s1_unsupported_desqueeze_ratio_rejected(self) -> None:
        c1 = evaluate_checklist_1_desqueeze_and_mc_focus_map(desqueeze_ratio="1.75x")
        self.assertFalse(c1.passed)
        self.assertTrue(any(S1_ERR_UNSUPPORTED_DESQUEEZE_RATIO in e for e in c1.errors))

    def test_10_s1_wrong_camera_model_or_firmware_rejected(self) -> None:
        c1 = evaluate_checklist_1_desqueeze_and_mc_focus_map(body_model_id=0x91030099, body_fw="6.01")
        self.assertFalse(c1.passed)
        self.assertTrue(any(S1_ERR_MODEL_OR_FW_FLOOR in e for e in c1.errors))

    def test_11_s1_active_desqueeze_enforces_all_four_setting_locks(self) -> None:
        for kw in (
            {"marker_display_locked_off": False},
            {"focus_magnifier_locked_off": False},
            {"auto_mag_mf_locked_off": False},
            {"face_eye_af_locked_off": False},
        ):
            c1 = evaluate_checklist_1_desqueeze_and_mc_focus_map(desqueeze_ratio="2.0x", **kw)
            self.assertFalse(c1.passed, str(kw))
            self.assertFalse(c1.four_setting_locks_satisfied)
            self.assertTrue(any(S1_ERR_DESQUEEZE_FOUR_SETTING_LOCK_VIOLATION in e for e in c1.errors))

    def test_12_s1_desqueeze_suppressions_hdmi_raw_hdmionly_logoff_remote(self) -> None:
        cases = (
            {"hdmi_raw_output": True},
            {"rec_media_dur_hdmi_output": HDMI_REC_MEDIA_OFF_HDMI_ONLY},
            {"log_shooting_mode": "OFF"},
            {"remote_shooting_active": True},
        )
        for kw in cases:
            c1_ok = evaluate_checklist_1_desqueeze_and_mc_focus_map(desqueeze_ratio="1.6x", **kw)
            self.assertTrue(c1_ok.passed)
            self.assertTrue(c1_ok.desqueeze_suppressed)
            self.assertEqual(c1_ok.effective_desqueeze_factor, 1.0)

            c1_conflict = evaluate_checklist_1_desqueeze_and_mc_focus_map(
                desqueeze_ratio="1.6x", expect_active_desqueeze_under_suppression=True, **kw
            )
            self.assertFalse(c1_conflict.passed)
            self.assertTrue(any(S1_ERR_DESQUEEZE_SUPPRESSED_STATE_CONFLICT in e for e in c1_conflict.errors))

    def test_13_s1_movie_initial_focus_mag_rejects_photo_only_x15_or_x20(self) -> None:
        c1 = evaluate_checklist_1_desqueeze_and_mc_focus_map(initial_focus_mag_scale="x2.0")
        self.assertFalse(c1.passed)
        self.assertTrue(any(S1_ERR_FOCUS_MAG_OR_BRIGHT_MON_CONFLICT in e for e in c1.errors))

    def test_14_s1_focus_magnifier_and_bright_monitoring_mutually_exclusive(self) -> None:
        c1 = evaluate_checklist_1_desqueeze_and_mc_focus_map(
            focus_magnifier_active=True, bright_monitoring_active=True
        )
        self.assertFalse(c1.passed)
        self.assertTrue(any(S1_ERR_FOCUS_MAG_OR_BRIGHT_MON_CONFLICT in e for e in c1.errors))

    def test_15_s1_in_body_focus_map_strictly_forbidden_on_fx3(self) -> None:
        c1 = evaluate_checklist_1_desqueeze_and_mc_focus_map(in_body_focus_map_menu_present=True)
        self.assertFalse(c1.passed)
        self.assertTrue(any(S1_ERR_IN_BODY_FOCUS_MAP_FORBIDDEN in e for e in c1.errors))

    def test_16_s1_external_mc_focus_map_passes_under_150fps_including_1fps_to_120fps(self) -> None:
        for fps in (1.0, 6.0, 23.98, 59.94, 119.88, 149.9):
            c1 = evaluate_checklist_1_desqueeze_and_mc_focus_map(
                mc_external_focus_map_enabled=True, mc_sensor_fps=fps
            )
            self.assertTrue(c1.passed, f"fps={fps}")
            self.assertTrue(c1.mc_focus_map_under_150fps)

    def test_17_s1_external_mc_focus_map_blocks_150fps_240fps_non_pdaf_or_playback(self) -> None:
        for kw in (
            {"mc_sensor_fps": 150.0},
            {"mc_sensor_fps": 240.0},
            {"mc_pdaf_compatible_lens": False},
            {"camera_in_playback": True},
        ):
            c1 = evaluate_checklist_1_desqueeze_and_mc_focus_map(
                mc_external_focus_map_enabled=True, **kw
            )
            self.assertFalse(c1.passed, str(kw))
            self.assertTrue(any(S1_ERR_MC_FOCUS_MAP_150FPS_OR_LENS_LIMIT in e for e in c1.errors))

    # --- Checklist 2: HDMI Log 1080p vs [Off(HDMI Only)] 4K & Blank LCD (9 tests) ---

    def test_18_s2_hdmi_only_blocks_unacknowledged_loss_of_internal_card_recording(self) -> None:
        c2 = evaluate_checklist_2_hdmi_log_and_blank_lcd(
            rec_media_dur_hdmi_output=HDMI_REC_MEDIA_OFF_HDMI_ONLY
        )
        self.assertFalse(c2.passed)
        self.assertFalse(c2.internal_card_recording_active)
        self.assertTrue(any(S2_ERR_HDMI_ONLY_DISABLES_INTERNAL_CARD_REC in e for e in c2.errors))

    def test_19_s2_hdmi_only_4k_10bit_passes_when_external_only_acknowledged(self) -> None:
        c2 = evaluate_checklist_2_hdmi_log_and_blank_lcd(
            rec_media_dur_hdmi_output=HDMI_REC_MEDIA_OFF_HDMI_ONLY,
            require_internal_card_recording=False,
            ack_hdmi_only_no_internal_card_rec=True,
            hdmi_only_4k_setting="59.94p 10bit",
        )
        self.assertTrue(c2.passed)
        self.assertEqual(c2.effective_hdmi_resolution, "2160P_10BIT_HDMI_ONLY")
        self.assertEqual(c2.effective_hdmi_info_display, "OFF")

    def test_20_s2_hdmi_only_2400p_10bit_requires_dci_4k_24p_gate(self) -> None:
        c2_fail = evaluate_checklist_2_hdmi_log_and_blank_lcd(
            rec_media_dur_hdmi_output=HDMI_REC_MEDIA_OFF_HDMI_ONLY,
            require_internal_card_recording=False,
            ack_hdmi_only_no_internal_card_rec=True,
            hdmi_only_4k_setting="24.00p 10bit",
            dci_4k_24p_mode=False,
        )
        self.assertFalse(c2_fail.passed)
        self.assertTrue(any(S2_ERR_HDMI_ONLY_24P_REQUIRES_DCI_GATE in e for e in c2_fail.errors))

    def test_21_s2_log_shooting_with_internal_card_rec_downshifts_hdmi_to_1080p(self) -> None:
        c2 = evaluate_checklist_2_hdmi_log_and_blank_lcd(
            rec_media_dur_hdmi_output=HDMI_REC_MEDIA_ON,
            log_shooting_mode="CINE_EI",
            hdmi_output_resolution="2160p",
        )
        self.assertTrue(c2.passed)
        self.assertTrue(c2.log_or_pplut_1080p_downshift_active)
        self.assertEqual(c2.effective_hdmi_resolution, "1080P")

    def test_22_s2_pplut1_to_4_also_triggers_1080p_hdmi_downshift_and_blocks_false_4k_claim(self) -> None:
        c2 = evaluate_checklist_2_hdmi_log_and_blank_lcd(
            rec_media_dur_hdmi_output=HDMI_REC_MEDIA_ON,
            log_shooting_mode="OFF",
            picture_profile="PPLUT2",
            expected_hdmi_4k_with_internal_rec_and_log=True,
        )
        self.assertFalse(c2.passed)
        self.assertTrue(c2.log_or_pplut_1080p_downshift_active)
        self.assertTrue(any(S2_ERR_HDMI_LOG_OR_PPLUT_FORCES_1080P_DOWNSHIFT in e for e in c2.errors))

    def test_23_s2_hdmi_raw_output_bypasses_1080p_downshift_at_4264x2408(self) -> None:
        c2 = evaluate_checklist_2_hdmi_log_and_blank_lcd(
            rec_media_dur_hdmi_output=HDMI_REC_MEDIA_ON,
            log_shooting_mode="CINE_EI",
            hdmi_raw_output=True,
            hdmi_info_display="OFF",
        )
        self.assertTrue(c2.passed)
        self.assertEqual(c2.effective_hdmi_resolution, "4264X2408_RAW16")

    def test_24_s2_hdmi_info_display_on_rejected_under_hdmi_only_or_raw(self) -> None:
        c2 = evaluate_checklist_2_hdmi_log_and_blank_lcd(
            hdmi_raw_output=True, hdmi_info_display="ON"
        )
        self.assertFalse(c2.passed)
        self.assertTrue(any(S2_ERR_HDMI_INFO_DISPLAY_FORCED_OFF_CONFLICT in e for e in c2.errors))

    def test_25_s2_hdmi_info_display_on_blanks_built_in_lcd_and_blocks_by_default(self) -> None:
        c2 = evaluate_checklist_2_hdmi_log_and_blank_lcd(
            hdmi_info_display="ON", require_unblanked_camera_lcd=True
        )
        self.assertFalse(c2.passed)
        self.assertTrue(c2.camera_lcd_blanked)
        self.assertIn(WARN_HDMI_INFO_DISPLAY_ON_BLANKS_LCD, c2.warnings)
        self.assertTrue(any(S2_ERR_BUILT_IN_LCD_BLANKED_UNACKNOWLEDGED in e for e in c2.errors))

    def test_26_s2_hdmi_info_display_on_allowed_with_warning_when_blank_lcd_permitted(self) -> None:
        c2 = evaluate_checklist_2_hdmi_log_and_blank_lcd(
            hdmi_info_display="ON", require_unblanked_camera_lcd=False
        )
        self.assertTrue(c2.passed)
        self.assertTrue(c2.camera_lcd_blanked)
        self.assertIn(WARN_HDMI_INFO_DISPLAY_ON_BLANKS_LCD, c2.warnings)

    # --- Checklist 3: Dual-Slot Simult + Auto Switch Media & Px Proxy Vault (10 tests) ---

    def test_27_s3_nominal_dual_cfexpress_a_simult_and_xavc_hs_hd_proxy_pass(self) -> None:
        c3 = evaluate_checklist_3_simult_autoswitch_and_proxy_vault()
        self.assertTrue(c3.passed)
        self.assertTrue(c3.dual_slot_exfat_and_speed_parity_ok)
        self.assertTrue(c3.strict_dual_vault_parity_preserved)
        self.assertTrue(c3.proxy_under_100fps_cutoff)
        self.assertFalse(c3.in_camera_proxy_playback_supported)

    def test_28_s3_simult_rejects_missing_slot2_or_sdhc_fat32(self) -> None:
        for s2_type in ("NONE", "SDHC"):
            c3 = evaluate_checklist_3_simult_autoswitch_and_proxy_vault(slot2_media_type=s2_type)
            self.assertFalse(c3.passed, s2_type)
            self.assertTrue(any(S3_ERR_SIMULT_DUAL_SLOT_EXFAT_OR_PARITY in e for e in c3.errors))

    def test_29_s3_simult_rejects_mismatched_capacity_or_slow_v30_card(self) -> None:
        c3_cap = evaluate_checklist_3_simult_autoswitch_and_proxy_vault(
            slot1_capacity_gb=160, slot2_capacity_gb=80, auto_switch_media="OFF"
        )
        self.assertFalse(c3_cap.passed)
        c3_spd = evaluate_checklist_3_simult_autoswitch_and_proxy_vault(
            slot2_media_type="SDXC", slot2_speed_tier="V30", required_min_speed_tier="V90"
        )
        self.assertFalse(c3_spd.passed)

    def test_30_s3_auto_switch_media_on_blocked_when_strict_1to1_dual_vault_required(self) -> None:
        c3 = evaluate_checklist_3_simult_autoswitch_and_proxy_vault(
            auto_switch_media="ON", require_strict_dual_vault_parity=True
        )
        self.assertFalse(c3.passed)
        self.assertTrue(any(S3_ERR_AUTO_SWITCH_BREAKS_STRICT_VAULT_PARITY in e for e in c3.errors))

    def test_31_s3_auto_switch_media_on_allowed_for_extended_rollover_mode(self) -> None:
        c3 = evaluate_checklist_3_simult_autoswitch_and_proxy_vault(
            auto_switch_media="ON",
            require_strict_dual_vault_parity=False,
            slot1_capacity_gb=160,
            slot2_capacity_gb=320,
        )
        self.assertTrue(c3.passed)

    def test_32_s3_px_proxy_supports_xavc_hs_hd_and_xavc_s_hd_under_100p(self) -> None:
        for fmt, fps in (("XAVC_HS_HD", 59.94), ("XAVC_S_HD", 50.0)):
            c3 = evaluate_checklist_3_simult_autoswitch_and_proxy_vault(
                proxy_file_format=fmt, rec_frame_rate_fps=fps
            )
            self.assertTrue(c3.passed)

    def test_33_s3_px_proxy_blocked_at_100p_or_11988p(self) -> None:
        for fps in (100.0, 119.88):
            c3 = evaluate_checklist_3_simult_autoswitch_and_proxy_vault(
                proxy_recording_enabled=True, rec_frame_rate_fps=fps
            )
            self.assertFalse(c3.passed)
            self.assertTrue(any(S3_ERR_PROXY_UNSUPPORTED_FORMAT_OR_CUTOFF_100FPS in e for e in c3.errors))

    def test_34_s3_px_proxy_blocked_in_sq_100_120_200_240fps_and_hdmi_only(self) -> None:
        c3_sq = evaluate_checklist_3_simult_autoswitch_and_proxy_vault(
            proxy_recording_enabled=True, sq_mode_enabled=True, sq_frame_rate_fps=120.0
        )
        self.assertFalse(c3_sq.passed)
        c3_hdmi = evaluate_checklist_3_simult_autoswitch_and_proxy_vault(
            proxy_recording_enabled=True, rec_media_dur_hdmi_output=HDMI_REC_MEDIA_OFF_HDMI_ONLY
        )
        self.assertFalse(c3_hdmi.passed)

    def test_35_s3_in_camera_proxy_playback_expectation_rejected(self) -> None:
        c3 = evaluate_checklist_3_simult_autoswitch_and_proxy_vault(
            expect_in_camera_proxy_playback=True
        )
        self.assertFalse(c3.passed)
        self.assertTrue(any(S3_ERR_PROXY_IN_CAMERA_PLAYBACK_UNSUPPORTED in e for e in c3.errors))

    def test_36_s3_uncoupled_clip_sub_delete_protect_or_orphans_rejected(self) -> None:
        for kw in (
            {"clip_sub_delete_coupled": False},
            {"clip_sub_protect_coupled": False},
            {"orphan_clip_or_sub_count": 2},
        ):
            c3 = evaluate_checklist_3_simult_autoswitch_and_proxy_vault(**kw)
            self.assertFalse(c3.passed, str(kw))
            self.assertTrue(any(S3_ERR_CLIP_SUB_COUPLED_DELETE_PROTECT_BROKEN in e for e in c3.errors))

    # --- Checklist 4: File Settings, SDHC Lock, Shot Mark XML & TC Slot-1 (9 tests) ---

    def test_37_s4_title_37_ascii_chars_boundary_pass_and_38_or_non_ascii_fail(self) -> None:
        exact_37 = "A" * 37
        c4_ok = evaluate_checklist_4_file_settings_shotmark_and_tc_slot1(
            file_name_format="TITLE", title_name=exact_37
        )
        self.assertTrue(c4_ok.passed)
        self.assertEqual(c4_ok.title_ascii_length, 37)

        for bad_title in ("B" * 38, "FX3/ILLEGAL", "索尼FX3"):
            c4_bad = evaluate_checklist_4_file_settings_shotmark_and_tc_slot1(title_name=bad_title)
            self.assertFalse(c4_bad.passed, bad_title)
            self.assertTrue(any(S4_ERR_FILE_SETTINGS_TITLE_OR_SERIES_COUNTER in e for e in c4_bad.errors))

    def test_38_s4_file_number_reset_rejected_when_non_colliding_series_required(self) -> None:
        c4 = evaluate_checklist_4_file_settings_shotmark_and_tc_slot1(
            file_number_mode="RESET", require_series_counter=True
        )
        self.assertFalse(c4.passed)
        self.assertTrue(any(S4_ERR_FILE_SETTINGS_TITLE_OR_SERIES_COUNTER in e for e in c4.errors))

    def test_39_s4_sdhc_locks_file_name_format_to_standard_and_blocks_custom_folder(self) -> None:
        c4_fmt = evaluate_checklist_4_file_settings_shotmark_and_tc_slot1(
            slot1_media_type="SDHC", file_name_format="CAM_ID_PLUS_REEL"
        )
        self.assertFalse(c4_fmt.passed)
        self.assertTrue(any(S4_ERR_SDHC_FORCES_STANDARD_FILE_FORMAT in e for e in c4_fmt.errors))

        c4_std = evaluate_checklist_4_file_settings_shotmark_and_tc_slot1(
            slot1_media_type="SDHC", file_name_format="STANDARD", custom_folder_name_requested=False
        )
        self.assertTrue(c4_std.passed)

    def test_40_s4_shot_mark1_2_requires_m01_xml_sidecar_and_valid_jump_mode(self) -> None:
        c4_fail = evaluate_checklist_4_file_settings_shotmark_and_tc_slot1(
            shot_mark1_count=2, shot_mark_xml_sidecar_enabled=False
        )
        self.assertFalse(c4_fail.passed)
        self.assertTrue(any(S4_ERR_SHOT_MARK_XML_SIDECAR_MISMATCH in e for e in c4_fail.errors))

    def test_41_s4_tc_regenerate_reads_slot1_and_forces_rec_run(self) -> None:
        c4_ok = evaluate_checklist_4_file_settings_shotmark_and_tc_slot1(
            tc_make="REGENERATE", tc_run="FREE_RUN", tc_regenerate_reference_slot=1
        )
        self.assertTrue(c4_ok.passed)
        self.assertEqual(c4_ok.effective_tc_run, "REC_RUN")

    def test_42_s4_tc_regenerate_rejects_slot2_reference_or_free_run_expectation(self) -> None:
        for kw in (
            {"tc_regenerate_reference_slot": 2},
            {"expect_free_run_under_regenerate": True},
        ):
            c4 = evaluate_checklist_4_file_settings_shotmark_and_tc_slot1(tc_make="REGENERATE", **kw)
            self.assertFalse(c4.passed)
            self.assertTrue(any(S4_ERR_TC_REGENERATE_SLOT1_OR_RECRUN_VIOLATION in e for e in c4.errors))

    def test_43_s4_vmc_bncm1_ext_lk_preserved_only_under_movie_preset_free_run(self) -> None:
        c4_ok = evaluate_checklist_4_file_settings_shotmark_and_tc_slot1(
            shoot_mode="MOVIE", tc_make="PRESET", tc_run="FREE_RUN", vmc_bncm1_ext_lk_required=True
        )
        self.assertTrue(c4_ok.passed)
        self.assertTrue(c4_ok.vmc_bncm1_ext_lk_preserved)

    def test_44_s4_vmc_bncm1_ext_lk_drops_on_regenerate_rec_run_or_sq(self) -> None:
        for kw in (
            {"tc_make": "REGENERATE"},
            {"tc_run": "REC_RUN"},
            {"shoot_mode": "S&Q"},
        ):
            c4 = evaluate_checklist_4_file_settings_shotmark_and_tc_slot1(
                vmc_bncm1_ext_lk_required=True, **kw
            )
            self.assertFalse(c4.passed, str(kw))
            self.assertFalse(c4.vmc_bncm1_ext_lk_preserved)
            self.assertTrue(any(S4_ERR_VMC_BNCM1_EXT_LK_OR_SQ_TC_VIOLATION in e for e in c4.errors))

    def test_45_s4_sq_mode_blocks_hdmi_tc_output_expectation(self) -> None:
        c4 = evaluate_checklist_4_file_settings_shotmark_and_tc_slot1(
            shoot_mode="S&Q", hdmi_tc_output_expected_in_sq=True
        )
        self.assertFalse(c4.passed)
        self.assertTrue(any(S4_ERR_VMC_BNCM1_EXT_LK_OR_SQ_TC_VIOLATION in e for e in c4.errors))

    # --- Checklist 5, Tier-0 Gate, Tamper Verifier & CLI (11 tests) ---

    def test_46_s5_rec_lamp_three_states_and_coupled_rear_plus_top_tally(self) -> None:
        states = {
            REC_LAMP_ALL_ON: (True, True, True),
            REC_LAMP_ONLY_FRONT_OFF: (False, True, True),
            REC_LAMP_ALL_OFF: (False, False, False),
        }
        for mode, expected_leds in states.items():
            c5, _ = evaluate_checklist_5_reclamp_shockless_wb_and_tier0_gate(
                rec_lamp_mode=mode, simulate_bench_dry_run=True
            )
            self.assertTrue(c5.passed)
            self.assertEqual((c5.front_tally_lit, c5.rear_tally_lit, c5.top_rec_button_lit), expected_leds)
            self.assertTrue(c5.rear_and_top_coupled)

    def test_47_s5_rec_lamp_rejects_bogus_rear_off_or_uncoupled_rear_top_claim(self) -> None:
        c5_bad, _ = evaluate_checklist_5_reclamp_shockless_wb_and_tier0_gate(rec_lamp_mode="REAR_OFF")
        self.assertFalse(c5_bad.passed)
        self.assertTrue(any(S5_ERR_REC_LAMP_COUPLED_REAR_TOP_VIOLATION in e for e in c5_bad.errors))

        c5_uncoupled, _ = evaluate_checklist_5_reclamp_shockless_wb_and_tier0_gate(
            rec_lamp_mode=REC_LAMP_ONLY_FRONT_OFF, expect_uncoupled_rear_vs_top_tally=True
        )
        self.assertFalse(c5_uncoupled.passed)

    def test_48_s5_silent_mode_requires_audio_signals_off(self) -> None:
        c5_fail, _ = evaluate_checklist_5_reclamp_shockless_wb_and_tier0_gate(
            silent_mode_enabled=True, audio_signals_mode="ON"
        )
        self.assertFalse(c5_fail.passed)
        self.assertTrue(any(S5_ERR_SILENT_MODE_AUDIO_SIGNALS_LOCK in e for e in c5_fail.errors))

        c5_ok, _ = evaluate_checklist_5_reclamp_shockless_wb_and_tier0_gate(
            silent_mode_enabled=True, audio_signals_mode="OFF"
        )
        self.assertTrue(c5_ok.passed)

    def test_49_s5_shockless_wb_enforces_zero_frame_kelvin_and_grid_jumps(self) -> None:
        c5_fail, _ = evaluate_checklist_5_reclamp_shockless_wb_and_tier0_gate(
            shockless_wb_mode="3 (Slow)", kelvin_or_grid_transition_frames=12
        )
        self.assertFalse(c5_fail.passed)
        self.assertTrue(any(S5_ERR_SHOCKLESS_WB_ZERO_FRAME_KELVIN_GRID in e for e in c5_fail.errors))

    def test_50_s5_h0_h3_surface_drift_fails_closed(self) -> None:
        c5_fail, _ = evaluate_checklist_5_reclamp_shockless_wb_and_tier0_gate(
            simulated_h0_h3_drifted_surfaces=1
        )
        self.assertFalse(c5_fail.passed)
        self.assertEqual(c5_fail.h0_equals_h3_count, 15)
        self.assertTrue(any(S5_ERR_H0_H3_IMMUTABILITY_DRIFT in e for e in c5_fail.errors))

    def test_51_offline_default_verdict_is_blocked_awaiting_physical_tier0_receipt(self) -> None:
        rep = evaluate_realhw_hdmi_proxy_desqueeze_and_simult_readiness()
        self.assertEqual(rep.schema, PHASE_216_SCHEMA)
        self.assertEqual(rep.phase_version, PHASE_216_VERSION)
        self.assertEqual(rep.go_no_go, GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT)
        self.assertTrue(rep.all_5_operator_checklists_passed)
        self.assertFalse(rep.tier0_receipt_verified)
        self.assertFalse(rep.hardware_live_attachment_authorized)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.spi_nor_write_authorized)
        self.assertFalse(rep.el3_payload_transmit_authorized)
        self.assertEqual(rep.usb_packets_transmitted, 0)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)
        self.assertTrue(verify_phase216_report(rep.to_dict()).valid)

    def test_52_simulate_bench_dry_run_verdict_and_hard_locks(self) -> None:
        rep = evaluate_realhw_hdmi_proxy_desqueeze_and_simult_readiness(simulate_bench_dry_run=True)
        self.assertEqual(rep.go_no_go, GO_NO_GO_DRY_RUN_SIMULATED_READY)
        self.assertTrue(rep.tier0_receipt_verified)
        self.assertEqual(rep.h0_equals_h3_count, 16)
        self.assertFalse(rep.hardware_live_attachment_authorized)
        self.assertEqual(rep.usb_packets_transmitted, 0)
        self.assertTrue(verify_phase216_report(rep.to_dict()).valid)

    def test_53_valid_dual_device_tier0_receipts_yield_readonly_verified_and_same_stdev_blocks(self) -> None:
        raw_a, raw_b, h0 = build_simulated_phase216_tier0_receipts()
        rep_ok = evaluate_realhw_hdmi_proxy_desqueeze_and_simult_readiness(
            receipt_a_bytes=raw_a,
            receipt_b_bytes=raw_b,
            st_dev_a_override=11,
            st_dev_b_override=22,
            body_serial=DEFAULT_TARGET_BODY_SERIAL,
            emmc_cid=DEFAULT_TARGET_EMMC_CID,
            h0_baselines_a=h0,
            h0_baselines_b=h0,
        )
        self.assertEqual(rep_ok.go_no_go, GO_NO_GO_HDMI_PROXY_DESQUEEZE_SIMULT_VERIFIED)
        self.assertFalse(rep_ok.hardware_live_attachment_authorized)
        self.assertTrue(verify_phase216_report(rep_ok.to_dict()).valid)

        rep_same_dev = evaluate_realhw_hdmi_proxy_desqueeze_and_simult_readiness(
            receipt_a_bytes=raw_a,
            receipt_b_bytes=raw_b,
            st_dev_a_override=11,
            st_dev_b_override=11,
            body_serial=DEFAULT_TARGET_BODY_SERIAL,
            emmc_cid=DEFAULT_TARGET_EMMC_CID,
            h0_baselines_a=h0,
            h0_baselines_b=h0,
        )
        self.assertEqual(rep_same_dev.go_no_go, GO_NO_GO_BLOCKED_HDMI_PROXY_DESQUEEZE_SIMULT_FAILURE)
        self.assertTrue(
            any(S5_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID in e for e in rep_same_dev.errors)
        )

    def test_54_verify_phase216_report_catches_tampering_and_safety_lock_violations(self) -> None:
        rep = evaluate_realhw_hdmi_proxy_desqueeze_and_simult_readiness(simulate_bench_dry_run=True)
        base = rep.to_dict()
        self.assertTrue(verify_phase216_report(base).valid)

        for field, bad_val in (
            ("hardware_live_attachment_authorized", True),
            ("persistent_emmc_writes_authorized", True),
            ("spi_nor_write_authorized", True),
            ("el3_payload_transmit_authorized", True),
            ("usb_packets_transmitted", 1),
            ("raw_firmware_bytes_leaked", 4),
        ):
            mutated = dict(base)
            mutated[field] = bad_val
            self.assertFalse(verify_phase216_report(mutated).valid, field)

    def test_55_cli_offline_default_returns_nonzero_fail_closed(self) -> None:
        buf = io.StringIO()
        with mock.patch("sys.stdout", buf):
            rc = cli_main(["preflight-hdmi-proxy-desqueeze-and-simult", "--force-clean-room"])
        self.assertEqual(rc, 1)
        self.assertIn("go_no_go=BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT", buf.getvalue())

    def test_56_cli_simulate_bench_dry_run_json_and_markdown_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            json_path = Path(tmp) / "p216.json"
            md_path = Path(tmp) / "p216.md"
            buf = io.StringIO()
            with mock.patch("sys.stdout", buf):
                rc = cli_main(
                    [
                        "preflight-hdmi-proxy-desqueeze-and-simult",
                        "--simulate-bench-dry-run",
                        "--desqueeze-ratio",
                        "1.6x",
                        "--mc-focus-map-enabled",
                        "--mc-sensor-fps",
                        "23.98",
                        "--json",
                        "--output",
                        str(json_path),
                        "--markdown-out",
                        str(md_path),
                    ]
                )
            self.assertEqual(rc, 0)
            parsed = json.loads(buf.getvalue())
            self.assertEqual(parsed["go_no_go"], GO_NO_GO_DRY_RUN_SIMULATED_READY)
            self.assertTrue(verify_phase216_report(parsed).valid)
            self.assertTrue(json_path.is_file())
            md_text = md_path.read_text(encoding="utf-8")
            self.assertIn(PHASE_216_SCHEMA, md_text)
            self.assertIn(CHECKLIST_S1_ID, render_phase216_markdown(
                evaluate_realhw_hdmi_proxy_desqueeze_and_simult_readiness(simulate_bench_dry_run=True)
            ))


if __name__ == "__main__":
    unittest.main()
