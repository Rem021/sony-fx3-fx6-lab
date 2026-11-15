"""Phase 211 Dual-Mode Unit Tests (54 tests) — 44th Firmware Auditor (44/44):
Real-Hardware `ILME-FX3` (`Ver. 7.02`) HDMI Log `1080p` vs `Off(HDMI Only)` `4K 10-bit`,
`Px` Proxy Coupled Vault & `Focus Magnifier` / `Bright Monitoring` Auditor.
"""

from __future__ import annotations

import ast
import io
import json
import os
import sys
import tempfile
import time
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.dont_write_bytecode = True

import fx3_firmware_lab as pkg  # noqa: E402
from fx3_firmware_lab import (  # noqa: E402
    APPFW_FX3_702_EXCLUSIVE_MARKERS_P211,
    APPFW_FX6_601_EXCLUSIVE_MARKERS_P211,
    APPFW_SHARED_WAVE28_MARKERS_P211,
    AUDITOR_INDEX_P211,
    BRIDGE_CLASS_HARD_WRITE_PROTECTED,
    BRIDGE_CLASS_MASKED_ABSENT_HW,
    BRIDGE_CLASS_NATIVE_PASSTHROUGH,
    BRIDGE_CLASS_SHIM_TRANSLATED,
    CPAPP_BOUNDED_HEAD_BYTES_P211,
    CPAPP_BOUNDED_TAIL_BYTES_P211,
    CPAPP_SHARED_MARKERS_P211,
    DEFAULT_PROXY_FILE_FORMAT_P211,
    DONOR_COLD_SCAN_BUDGET_SEC_P211,
    EXPECTED_FX3_APPFW_BYTES_P211,
    EXPECTED_FX3_CPAPP_BYTES_P211,
    EXPECTED_FX3_UXC_EN_F_BYTES_P211,
    EXPECTED_FX6_APPFW_BYTES_P211,
    EXPECTED_FX6_CPAPP_BYTES_P211,
    EXPECTED_FX6_UXC_EN_BYTES_P211,
    FORBIDDEN_NON_FX3_PROXY_FORMATS_P211,
    FX3_HDMI_INFO_DISPLAY_MENU_PATH_P211,
    FX3_HDMI_OUTPUT_SETTINGS_MENU_PATH_P211,
    FX3_HDMI_RESOLUTION_MENU_PATH_P211,
    FX3_INITIAL_FOCUS_MAG_MENU_PATH_P211,
    FX3_PROXY_FORMAT_SPECS_P211,
    FX3_PROXY_SETTINGS_MENU_PATH_P211,
    HDMI_4K_DCI_RESOLUTION_P211,
    HDMI_4K_UHD_RESOLUTION_P211,
    HDMI_FHD_1080P_RESOLUTION_P211,
    HDMI_RAW_SENSOR_RESOLUTION_P211,
    PASM_EXPOSURE_MODES_P211,
    PHASE_211_SCHEMA,
    PHASE_211_VERSION,
    PPLUT_PICTURE_PROFILES_P211,
    PROXY_CUTOFF_REC_FRAME_RATES_P211,
    PROXY_CUTOFF_SQ_MIN_NTSC_FPS_P211,
    PROXY_CUTOFF_SQ_MIN_PAL_FPS_P211,
    PROXY_MAIN_CLIP_DIR_P211,
    PROXY_SUB_DIR_P211,
    PROXY_SUB_SUFFIX_P211,
    UXC_FX3_EN_F_REQUIRED_TOKENS_P211,
    UXC_FX6_EN_REQUIRED_TOKENS_P211,
    VALID_4K_OUTPUT_HDMI_ONLY_SETTINGS_P211,
    VALID_BRIDGE_CLASSES,
    VALID_FOCUS_MAGNIF_TIMES_P211,
    VALID_LOG_SHOOTING_MODES_P211,
    VALID_MOVIE_INITIAL_FOCUS_MAG_P211,
    VALID_STILL_APSC_INITIAL_FOCUS_MAG_P211,
    VALID_STILL_FF_INITIAL_FOCUS_MAG_P211,
    VOLATILE_WAVE28_OVERLAY_DIR_P211,
    analyze_realhw_hdmi_log1080_proxy_vault_and_focusmag_brightmon,
    build_clean_room_realhw_hdmi_log1080_proxy_focusmag_brightmon_fixtures,
    build_phase211_compat_matrix,
    evaluate_coupled_clip_sub_vault_integrity,
    evaluate_focus_magnifier_and_bright_monitoring_interlocks,
    evaluate_hdmi_log_1080p_vs_hdmionly_4k_and_lcd_blanking,
    evaluate_phase211_write_guard,
    evaluate_proxy_codec_matrix_and_hfr_cutoffs,
    realhw_hdmi_log1080_proxy_vault_and_focusmag_brightmon_report_to_dict,
)
from fx3_firmware_lab import (  # noqa: E402
    realhw_hdmi_log1080_proxy_vault_and_focusmag_brightmon_auditor as mod_p211,
)
from fx3_firmware_lab.__main__ import main as cli_main  # noqa: E402
from fx3_firmware_lab.__main__ import run_audit_all  # noqa: E402


class TestRealhwHdmiLog1080ProxyVaultAndFocusmagBrightmon(unittest.TestCase):
    """54 dual-mode unit tests for Phase 211 (44th Auditor `44/44`)."""

    # ------------------------------------------------------------------
    # Group A (Tests 01-10): O_RDONLY Proof, <0.15s SLA, Clean-Room & Safety
    # ------------------------------------------------------------------

    def test_01_ast_strictly_o_rdonly_and_zero_write_calls(self) -> None:
        src_path = Path(mod_p211.__file__)
        src_text = src_path.read_text(encoding="utf-8")
        tree = ast.parse(src_text)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                self.assertNotEqual(node.func.id, "open", "builtin open() is forbidden")
            if isinstance(node, ast.Attribute):
                self.assertFalse(
                    node.attr.startswith(
                        ("write", "unlink", "rmdir", "mkdir", "chmod", "chown")
                    ),
                    f"forbidden mutating attribute: {node.attr}",
                )
        self.assertIn("os.O_RDONLY", src_text)
        self.assertIn("os.pread", src_text)

    def test_02_clean_room_report_passes_and_meets_015s_sla(self) -> None:
        t0 = time.perf_counter()
        rep = analyze_realhw_hdmi_log1080_proxy_vault_and_focusmag_brightmon(
            clean_room=True
        )
        dt = time.perf_counter() - t0
        self.assertLess(dt, DONOR_COLD_SCAN_BUDGET_SEC_P211)
        self.assertEqual(rep.schema, PHASE_211_SCHEMA)
        self.assertEqual(rep.version, PHASE_211_VERSION)
        self.assertEqual(rep.auditor_index, AUDITOR_INDEX_P211)
        self.assertEqual(rep.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(rep.donor_cold_scan_within_sla)
        self.assertTrue(rep.all_checks_passed)

    def test_03_hard_safety_invariants_enforced_in_both_modes(self) -> None:
        for cr in (True, False):
            rep = analyze_realhw_hdmi_log1080_proxy_vault_and_focusmag_brightmon(
                clean_room=cr
            )
            self.assertTrue(rep.all_checks_passed)
            p4 = rep.pillar_4_write_guard_and_matrix
            self.assertFalse(p4.persistent_emmc_writes_authorized)
            self.assertFalse(p4.spi_nor_write_authorized)
            self.assertFalse(p4.el3_payload_transmit_authorized)
            self.assertEqual(p4.physical_usb_packets_emitted, 0)
            self.assertEqual(p4.raw_firmware_bytes_leaked, 0)
            self.assertEqual(p4.volatile_overlay_dir, VOLATILE_WAVE28_OVERLAY_DIR_P211)

    def test_04_auto_mode_donor_or_clean_room_cold_scan_within_015s_budget(self) -> None:
        rep = analyze_realhw_hdmi_log1080_proxy_vault_and_focusmag_brightmon(
            clean_room=False
        )
        self.assertTrue(rep.all_checks_passed)
        self.assertTrue(rep.donor_cold_scan_within_sla)
        self.assertLessEqual(
            rep.donor_cold_scan_duration_sec, DONOR_COLD_SCAN_BUDGET_SEC_P211
        )
        if os.environ.get("FX3_FX6_FORCE_CLEAN_ROOM") == "1":
            self.assertEqual(rep.source_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertTrue(rep.clean_room_forced)
        elif rep.source_mode == "LOCAL_DONOR_RDONLY":
            self.assertFalse(rep.clean_room_forced)
            p1 = rep.pillar_1_hdmi_log_1080p_and_hdmionly_4k
            p2 = rep.pillar_2_proxy_matrix_and_coupled_vault
            self.assertEqual(p1.fx3_appfw.file_bytes, EXPECTED_FX3_APPFW_BYTES_P211)
            self.assertEqual(p1.fx6_appfw.file_bytes, EXPECTED_FX6_APPFW_BYTES_P211)
            self.assertEqual(
                p1.fx3_uxc_en_f.file_bytes, EXPECTED_FX3_UXC_EN_F_BYTES_P211
            )
            self.assertEqual(
                p1.fx6_uxc_en.file_bytes, EXPECTED_FX6_UXC_EN_BYTES_P211
            )
            self.assertEqual(p2.fx3_cpapp.file_bytes, EXPECTED_FX3_CPAPP_BYTES_P211)
            self.assertEqual(p2.fx6_cpapp.file_bytes, EXPECTED_FX6_CPAPP_BYTES_P211)

    def test_05_uncached_cold_donor_scan_stays_under_015s_when_donors_present(self) -> None:
        if os.environ.get("FX3_FX6_FORCE_CLEAN_ROOM") == "1":
            rep = analyze_realhw_hdmi_log1080_proxy_vault_and_focusmag_brightmon()
            self.assertEqual(rep.source_mode, "CLEAN_ROOM_SYNTHETIC")
            return
        saved = dict(mod_p211._DONOR_SCAN_CACHE_P211)
        try:
            mod_p211._DONOR_SCAN_CACHE_P211.clear()
            rep = analyze_realhw_hdmi_log1080_proxy_vault_and_focusmag_brightmon(
                clean_room=False
            )
            self.assertLessEqual(
                rep.donor_cold_scan_duration_sec, DONOR_COLD_SCAN_BUDGET_SEC_P211
            )
            self.assertTrue(rep.donor_cold_scan_within_sla)
            t_warm = time.perf_counter()
            rep_warm = analyze_realhw_hdmi_log1080_proxy_vault_and_focusmag_brightmon(
                clean_room=False
            )
            self.assertLess(time.perf_counter() - t_warm, 0.02)
            self.assertEqual(rep.report_digest_sha256, rep_warm.report_digest_sha256)
        finally:
            mod_p211._DONOR_SCAN_CACHE_P211.update(saved)

    def test_06_missing_donor_directory_falls_back_cleanly_to_synthetic(self) -> None:
        from unittest import mock

        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(mod_p211, "resolve_donor_file", return_value=None):
                rep = analyze_realhw_hdmi_log1080_proxy_vault_and_focusmag_brightmon(
                    repo_root=Path(tmp), clean_room=False
                )
            self.assertEqual(rep.source_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertTrue(rep.all_checks_passed)

    def test_07_deterministic_sha256_digest_across_repeated_runs(self) -> None:
        r1 = analyze_realhw_hdmi_log1080_proxy_vault_and_focusmag_brightmon(
            clean_room=True
        )
        r2 = analyze_realhw_hdmi_log1080_proxy_vault_and_focusmag_brightmon(
            clean_room=True
        )
        self.assertEqual(len(r1.report_digest_sha256), 64)
        self.assertEqual(r1.report_digest_sha256, r2.report_digest_sha256)

    def test_08_synthetic_fixtures_preserve_exact_expected_sizes_and_markers(self) -> None:
        fx3_app, fx6_app, fx3_uxc, fx6_uxc, fx3_cp, fx6_cp = (
            build_clean_room_realhw_hdmi_log1080_proxy_focusmag_brightmon_fixtures()
        )
        self.assertEqual(fx3_app.file_bytes, EXPECTED_FX3_APPFW_BYTES_P211)
        self.assertEqual(fx6_app.file_bytes, EXPECTED_FX6_APPFW_BYTES_P211)
        self.assertEqual(fx3_uxc.file_bytes, EXPECTED_FX3_UXC_EN_F_BYTES_P211)
        self.assertEqual(fx6_uxc.file_bytes, EXPECTED_FX6_UXC_EN_BYTES_P211)
        self.assertEqual(
            fx3_cp.bounded_bytes_scanned,
            CPAPP_BOUNDED_HEAD_BYTES_P211 + CPAPP_BOUNDED_TAIL_BYTES_P211,
        )
        self.assertEqual(
            fx6_cp.bounded_bytes_scanned,
            CPAPP_BOUNDED_HEAD_BYTES_P211 + CPAPP_BOUNDED_TAIL_BYTES_P211,
        )
        for m in APPFW_SHARED_WAVE28_MARKERS_P211 + APPFW_FX3_702_EXCLUSIVE_MARKERS_P211:
            self.assertGreaterEqual(fx3_app.marker_hits[m], 1)
        for m in APPFW_SHARED_WAVE28_MARKERS_P211 + APPFW_FX6_601_EXCLUSIVE_MARKERS_P211:
            self.assertGreaterEqual(fx6_app.marker_hits[m], 1)

    def test_09_donor_and_synthetic_uxc_cpapp_tokens_verified(self) -> None:
        rep = analyze_realhw_hdmi_log1080_proxy_vault_and_focusmag_brightmon()
        p1 = rep.pillar_1_hdmi_log_1080p_and_hdmionly_4k
        p2 = rep.pillar_2_proxy_matrix_and_coupled_vault
        for tok in UXC_FX3_EN_F_REQUIRED_TOKENS_P211:
            self.assertGreaterEqual(p1.fx3_uxc_en_f.token_hits[tok], 1, tok)
        for tok in UXC_FX6_EN_REQUIRED_TOKENS_P211:
            self.assertGreaterEqual(p1.fx6_uxc_en.token_hits[tok], 1, tok)
        for m in CPAPP_SHARED_MARKERS_P211:
            self.assertGreaterEqual(p2.fx3_cpapp.marker_hits[m], 1, m)
            self.assertGreaterEqual(p2.fx6_cpapp.marker_hits[m], 1, m)

    def test_10_report_to_dict_json_roundtrip_contains_zero_raw_bytes(self) -> None:
        rep = analyze_realhw_hdmi_log1080_proxy_vault_and_focusmag_brightmon(
            clean_room=True
        )
        d = realhw_hdmi_log1080_proxy_vault_and_focusmag_brightmon_report_to_dict(rep)
        blob = json.dumps(d, sort_keys=True)
        parsed = json.loads(blob)
        self.assertEqual(parsed["auditor_index"], "44/44")
        self.assertTrue(parsed["all_checks_passed"])
        self.assertEqual(
            parsed["pillar_4_write_guard_and_matrix"]["raw_firmware_bytes_leaked"], 0
        )

    # ------------------------------------------------------------------
    # Group B (Tests 11-22): Pillar A — HDMI Log/PPLUT 1080p vs Off(HDMI Only) 4K & LCD Blanking
    # ------------------------------------------------------------------

    def test_11_menu_paths_match_sony_fx3_ver_702_help_guide(self) -> None:
        self.assertEqual(
            FX3_HDMI_OUTPUT_SETTINGS_MENU_PATH_P211,
            "MENU -> Setup -> [External Output] -> [HDMI Output Settings]",
        )
        self.assertEqual(
            FX3_HDMI_INFO_DISPLAY_MENU_PATH_P211,
            "MENU -> Setup -> [External Output] -> [HDMI Info. Display]",
        )
        self.assertEqual(
            FX3_HDMI_RESOLUTION_MENU_PATH_P211,
            "MENU -> Setup -> [External Output] -> [HDMI Resolution]",
        )

    def test_12_all_three_log_shooting_modes_force_1080p_when_rec_media_on_and_raw_off(self) -> None:
        for log_mode in ("Cine EI", "Cine EI Quick", "Flexible ISO"):
            for hdmi_res in ("Auto", "2160p"):
                res = evaluate_hdmi_log_1080p_vs_hdmionly_4k_and_lcd_blanking(
                    rec_media_dur_hdmi="On",
                    raw_output="Off",
                    hdmi_resolution_menu=hdmi_res,
                    log_shooting=log_mode,
                    internal_rec_resolution="4K",
                )
                self.assertTrue(res.log_or_pplut_active)
                self.assertTrue(res.forced_1080p_downshift_by_log_or_pplut)
                self.assertEqual(res.effective_hdmi_resolution, HDMI_FHD_1080P_RESOLUTION_P211)
                self.assertEqual(
                    res.effective_hdmi_signal_class,
                    "YCBCR_1080P_CLAMPED_BY_LOG_OR_PPLUT",
                )

    def test_13_pplut1_to_pplut4_force_1080p_when_rec_media_on_and_raw_off(self) -> None:
        for pp in PPLUT_PICTURE_PROFILES_P211:
            res = evaluate_hdmi_log_1080p_vs_hdmionly_4k_and_lcd_blanking(
                rec_media_dur_hdmi="On",
                raw_output="Off",
                hdmi_resolution_menu="2160p",
                log_shooting="Off",
                picture_profile=pp,
                internal_rec_resolution="4K",
            )
            self.assertTrue(res.forced_1080p_downshift_by_log_or_pplut, pp)
            self.assertEqual(res.effective_hdmi_resolution, HDMI_FHD_1080P_RESOLUTION_P211)

    def test_14_standard_pp_off_and_pp1_to_pp11_allow_4k_hdmi_with_card_rec(self) -> None:
        for pp in ("Off", "PP1", "PP8", "PP10", "PP11"):
            res = evaluate_hdmi_log_1080p_vs_hdmionly_4k_and_lcd_blanking(
                rec_media_dur_hdmi="On",
                raw_output="Off",
                hdmi_resolution_menu="Auto",
                log_shooting="Off",
                picture_profile=pp,
                internal_rec_resolution="4K",
            )
            self.assertFalse(res.forced_1080p_downshift_by_log_or_pplut, pp)
            self.assertEqual(res.effective_hdmi_resolution, HDMI_4K_UHD_RESOLUTION_P211)
            self.assertTrue(res.internal_card_recording_permitted)

        dci = evaluate_hdmi_log_1080p_vs_hdmionly_4k_and_lcd_blanking(
            rec_media_dur_hdmi="On",
            raw_output="Off",
            hdmi_resolution_menu="2160p",
            log_shooting="Off",
            picture_profile="Off",
            internal_rec_resolution="4K_DCI",
            rec_frame_rate="24.00p",
        )
        self.assertEqual(dci.effective_hdmi_resolution, HDMI_4K_DCI_RESOLUTION_P211)

    def test_15_off_hdmi_only_unlocks_all_six_4k_10bit_rates_even_in_cine_ei_and_pplut(self) -> None:
        self.assertEqual(len(VALID_4K_OUTPUT_HDMI_ONLY_SETTINGS_P211), 6)
        for setting in VALID_4K_OUTPUT_HDMI_ONLY_SETTINGS_P211:
            res = evaluate_hdmi_log_1080p_vs_hdmionly_4k_and_lcd_blanking(
                rec_media_dur_hdmi="Off(HDMI Only)",
                raw_output="Off",
                hdmi_4k_output_set=setting,
                log_shooting="Cine EI",
                hdmi_info_display_requested="On",
                desqueeze_display="2.0x",
            )
            self.assertFalse(res.internal_card_recording_permitted)
            self.assertFalse(res.proxy_recording_permitted_by_hdmi)
            self.assertFalse(res.forced_1080p_downshift_by_log_or_pplut)
            self.assertEqual(res.effective_hdmi_resolution, HDMI_4K_UHD_RESOLUTION_P211)
            self.assertEqual(res.effective_hdmi_bit_depth, 10)
            self.assertEqual(res.effective_hdmi_info_display, "Off")
            self.assertTrue(res.hdmi_info_display_forced_off)
            self.assertFalse(res.hdmi_desqueeze_applied)

    def test_16_off_hdmi_only_24_00p_supports_4096x2160_dci_when_enabled(self) -> None:
        res = evaluate_hdmi_log_1080p_vs_hdmionly_4k_and_lcd_blanking(
            rec_media_dur_hdmi="Off(HDMI Only)",
            hdmi_4k_output_set="24.00p 10bit",
            dci_4k_24_00p_enabled=True,
        )
        self.assertEqual(res.effective_hdmi_resolution, HDMI_4K_DCI_RESOLUTION_P211)

    def test_17_raw_output_emits_4264x2408_16bit_and_forces_hdmi_info_off(self) -> None:
        for rec_mode, expect_card in (("On", True), ("Off(HDMI Only)", False)):
            res = evaluate_hdmi_log_1080p_vs_hdmionly_4k_and_lcd_blanking(
                rec_media_dur_hdmi=rec_mode,
                raw_output="On",
                log_shooting="Cine EI",
                hdmi_info_display_requested="On",
                desqueeze_display="1.6x",
            )
            self.assertEqual(res.effective_hdmi_resolution, HDMI_RAW_SENSOR_RESOLUTION_P211)
            self.assertEqual(res.effective_hdmi_bit_depth, 16)
            self.assertEqual(res.internal_card_recording_permitted, expect_card)
            self.assertEqual(res.effective_hdmi_info_display, "Off")
            self.assertTrue(res.hdmi_info_display_forced_off)
            self.assertFalse(res.camera_lcd_live_view_blanked)
            self.assertFalse(res.hdmi_desqueeze_applied)

    def test_18_hdmi_info_display_on_blanks_builtin_lcd_and_shows_red_rec_border_on_hdmi(self) -> None:
        res = evaluate_hdmi_log_1080p_vs_hdmionly_4k_and_lcd_blanking(
            rec_media_dur_hdmi="On",
            raw_output="Off",
            log_shooting="Cine EI",
            hdmi_info_display_requested="On",
            emphasized_rec_display="On",
            desqueeze_display="1.6x",
            hdmi_cable_connected=True,
        )
        self.assertEqual(res.effective_hdmi_info_display, "On")
        self.assertTrue(res.camera_lcd_live_view_blanked)
        self.assertTrue(res.hdmi_emphasized_rec_border_visible)
        self.assertFalse(res.hdmi_desqueeze_applied)

    def test_19_hdmi_cable_disconnected_keeps_builtin_lcd_active(self) -> None:
        res = evaluate_hdmi_log_1080p_vs_hdmionly_4k_and_lcd_blanking(
            rec_media_dur_hdmi="On",
            hdmi_info_display_requested="On",
            emphasized_rec_display="On",
            hdmi_cable_connected=False,
        )
        self.assertEqual(res.effective_hdmi_info_display, "Off")
        self.assertFalse(res.camera_lcd_live_view_blanked)
        self.assertFalse(res.hdmi_emphasized_rec_border_visible)

    def test_20_clean_hdmi_with_log_and_info_off_allows_desqueeze_on_hdmi_1080p(self) -> None:
        res = evaluate_hdmi_log_1080p_vs_hdmionly_4k_and_lcd_blanking(
            rec_media_dur_hdmi="On",
            raw_output="Off",
            log_shooting="Cine EI",
            hdmi_info_display_requested="Off",
            desqueeze_display="1.6x",
            hdmi_cable_connected=True,
        )
        self.assertEqual(res.effective_hdmi_resolution, HDMI_FHD_1080P_RESOLUTION_P211)
        self.assertFalse(res.camera_lcd_live_view_blanked)
        self.assertTrue(res.hdmi_desqueeze_applied)

    def test_21_hfr_120p_100p_with_rec_media_on_outputs_1080_standard(self) -> None:
        for fps in PROXY_CUTOFF_REC_FRAME_RATES_P211:
            res = evaluate_hdmi_log_1080p_vs_hdmionly_4k_and_lcd_blanking(
                rec_media_dur_hdmi="On",
                raw_output="Off",
                log_shooting="Off",
                hdmi_resolution_menu="Auto",
                internal_rec_resolution="4K",
                rec_frame_rate=fps,
            )
            self.assertEqual(res.effective_hdmi_resolution, HDMI_FHD_1080P_RESOLUTION_P211)

    def test_22_hdmi_evaluator_rejects_invalid_parameters(self) -> None:
        with self.assertRaises(ValueError):
            evaluate_hdmi_log_1080p_vs_hdmionly_4k_and_lcd_blanking(
                rec_media_dur_hdmi="Invalid"
            )
        with self.assertRaises(ValueError):
            evaluate_hdmi_log_1080p_vs_hdmionly_4k_and_lcd_blanking(
                hdmi_4k_output_set="120p 10bit"
            )
        with self.assertRaises(ValueError):
            evaluate_hdmi_log_1080p_vs_hdmionly_4k_and_lcd_blanking(
                log_shooting="S-Gamut3Only"
            )
        with self.assertRaises(ValueError):
            evaluate_hdmi_log_1080p_vs_hdmionly_4k_and_lcd_blanking(
                picture_profile="PPLUT5"
            )

    # ------------------------------------------------------------------
    # Group C (Tests 23-36): Pillar B — Proxy 2-Format/3-Bitrate, Cutoffs & Coupled Vault
    # ------------------------------------------------------------------

    def test_23_proxy_settings_exact_two_formats_and_three_bitrates(self) -> None:
        self.assertEqual(
            FX3_PROXY_SETTINGS_MENU_PATH_P211,
            "MENU -> Shooting -> [Image Quality/Rec] -> [Proxy Settings]",
        )
        self.assertEqual(DEFAULT_PROXY_FILE_FORMAT_P211, "XAVC S HD")
        self.assertEqual(set(FX3_PROXY_FORMAT_SPECS_P211.keys()), {"XAVC HS HD", "XAVC S HD"})
        self.assertEqual(FX3_PROXY_FORMAT_SPECS_P211["XAVC HS HD"]["bitrates"], ("16M", "9M"))
        self.assertEqual(FX3_PROXY_FORMAT_SPECS_P211["XAVC HS HD"]["default_bitrate"], "9M")
        self.assertEqual(FX3_PROXY_FORMAT_SPECS_P211["XAVC S HD"]["bitrates"], ("6M",))

    def test_24_xavc_hs_hd_16m_and_9m_1080p_10bit_hevc_evaluation(self) -> None:
        r_def = evaluate_proxy_codec_matrix_and_hfr_cutoffs(
            proxy_file_format="XAVC HS HD"
        )
        self.assertTrue(r_def.proxy_active)
        self.assertEqual(r_def.proxy_bitrate, "9M")
        self.assertEqual(r_def.proxy_resolution, (1920, 1080))
        self.assertEqual(r_def.proxy_chroma_bit_depth, "4:2:0 10-bit")
        self.assertEqual(
            r_def.appfw_record_setting_enum,
            "PROXY_RECORD_SETTING_9M_420_10BIT_XAVC_HS_HD",
        )

        r_16 = evaluate_proxy_codec_matrix_and_hfr_cutoffs(
            proxy_file_format="XAVC HS HD", proxy_bitrate="16M", rec_frame_rate="59.94p"
        )
        self.assertTrue(r_16.proxy_active)
        self.assertEqual(
            r_16.appfw_record_setting_enum,
            "PROXY_RECORD_SETTING_16M_420_10BIT_XAVC_HS_HD",
        )

    def test_25_xavc_s_hd_overall_default_720p_8bit_avc_6m_evaluation(self) -> None:
        r_def = evaluate_proxy_codec_matrix_and_hfr_cutoffs()
        self.assertTrue(r_def.proxy_active)
        self.assertEqual(r_def.proxy_file_format, "XAVC S HD")
        self.assertEqual(r_def.proxy_bitrate, "6M")
        self.assertEqual(r_def.proxy_resolution, (1280, 720))
        self.assertEqual(r_def.proxy_chroma_bit_depth, "4:2:0 8-bit")
        self.assertEqual(
            r_def.appfw_record_setting_enum,
            "PROXY_RECORD_SETTING_6M_420_8BIT_XAVC_S_HD",
        )
        self.assertEqual(r_def.main_clip_dir, PROXY_MAIN_CLIP_DIR_P211)
        self.assertEqual(r_def.proxy_sub_dir, PROXY_SUB_DIR_P211)

    def test_26_forbidden_proxy_formats_and_mismatched_bitrates_rejected(self) -> None:
        for bad_fmt in FORBIDDEN_NON_FX3_PROXY_FORMATS_P211:
            with self.assertRaises(ValueError):
                evaluate_proxy_codec_matrix_and_hfr_cutoffs(proxy_file_format=bad_fmt)
        with self.assertRaises(ValueError):
            evaluate_proxy_codec_matrix_and_hfr_cutoffs(
                proxy_file_format="XAVC S HD", proxy_bitrate="16M"
            )
        with self.assertRaises(ValueError):
            evaluate_proxy_codec_matrix_and_hfr_cutoffs(
                proxy_file_format="XAVC HS HD", proxy_bitrate="6M"
            )

    def test_27_proxy_cutoff_at_119_88p_and_100p_movie_frame_rates(self) -> None:
        for hfr in ("119.88p", "100p"):
            res = evaluate_proxy_codec_matrix_and_hfr_cutoffs(
                proxy_file_format="XAVC HS HD", proxy_bitrate="16M", rec_frame_rate=hfr
            )
            self.assertFalse(res.proxy_active)
            self.assertEqual(res.cutoff_reason, "REC_FRAME_RATE_119_88P_OR_100P")
            self.assertIsNone(res.proxy_resolution)
            self.assertFalse(res.playback_thumbnail_px_badge_shown)

    def test_28_proxy_cutoff_in_sq_ge_120fps_ntsc_and_ge_100fps_pal(self) -> None:
        self.assertEqual(PROXY_CUTOFF_SQ_MIN_NTSC_FPS_P211, 120)
        self.assertEqual(PROXY_CUTOFF_SQ_MIN_PAL_FPS_P211, 100)
        for fps in (120, 240):
            r_ntsc = evaluate_proxy_codec_matrix_and_hfr_cutoffs(
                capture_mode="S&Q", sq_sensor_fps=fps, ntsc_pal_region="NTSC"
            )
            self.assertFalse(r_ntsc.proxy_active)
            self.assertEqual(r_ntsc.cutoff_reason, "SQ_SENSOR_FPS_GE_120")
        r_ntsc_60 = evaluate_proxy_codec_matrix_and_hfr_cutoffs(
            capture_mode="S&Q", sq_sensor_fps=60, ntsc_pal_region="NTSC"
        )
        self.assertTrue(r_ntsc_60.proxy_active)

        for fps in (100, 200):
            r_pal = evaluate_proxy_codec_matrix_and_hfr_cutoffs(
                capture_mode="S&Q",
                rec_frame_rate="25p",
                sq_sensor_fps=fps,
                ntsc_pal_region="PAL",
            )
            self.assertFalse(r_pal.proxy_active)
            self.assertEqual(r_pal.cutoff_reason, "SQ_SENSOR_FPS_GE_100")
        r_pal_50 = evaluate_proxy_codec_matrix_and_hfr_cutoffs(
            capture_mode="S&Q",
            rec_frame_rate="25p",
            sq_sensor_fps=50,
            ntsc_pal_region="PAL",
        )
        self.assertTrue(r_pal_50.proxy_active)

    def test_29_proxy_cutoff_under_off_hdmi_only_and_when_switched_off(self) -> None:
        r_hdmi = evaluate_proxy_codec_matrix_and_hfr_cutoffs(
            rec_media_dur_hdmi="Off(HDMI Only)"
        )
        self.assertFalse(r_hdmi.proxy_active)
        self.assertEqual(r_hdmi.cutoff_reason, "REC_MEDIA_OFF_HDMI_ONLY")

        r_off = evaluate_proxy_codec_matrix_and_hfr_cutoffs(
            proxy_recording_setting="Off"
        )
        self.assertFalse(r_off.proxy_active)
        self.assertEqual(r_off.cutoff_reason, "PROXY_RECORDING_SWITCHED_OFF")

    def test_30_zero_oncamera_proxy_playback_and_px_thumbnail_badge_invariant(self) -> None:
        for fmt in ("XAVC HS HD", "XAVC S HD"):
            res = evaluate_proxy_codec_matrix_and_hfr_cutoffs(proxy_file_format=fmt)
            self.assertFalse(res.on_camera_proxy_playback_supported)
            self.assertTrue(res.playback_thumbnail_px_badge_shown)

    def test_31_atomic_coupled_incamera_delete_removes_both_clip_and_sub(self) -> None:
        res = evaluate_coupled_clip_sub_vault_integrity(
            clip_stem="C0042",
            clip_present=True,
            sub_present=True,
            action="DELETE",
            scope="COUPLED_PAIR",
            in_camera=True,
        )
        self.assertTrue(res.allowed)
        self.assertFalse(res.resulting_clip_present)
        self.assertFalse(res.resulting_sub_present)
        self.assertEqual(res.integrity_status, "ATOMIC_COUPLED_DELETED")
        self.assertIn(PROXY_SUB_SUFFIX_P211, res.reason)

    def test_32_incamera_single_sided_delete_or_protect_rejected(self) -> None:
        for action in ("DELETE", "PROTECT", "UNPROTECT"):
            for scope in ("CLIP_ONLY", "SUB_ONLY"):
                res = evaluate_coupled_clip_sub_vault_integrity(
                    clip_stem="C0043",
                    action=action,
                    scope=scope,
                    in_camera=True,
                )
                self.assertFalse(res.allowed)
                self.assertTrue(res.single_sided_incamera_op_rejected)
                self.assertEqual(
                    res.integrity_status, "REJECTED_SINGLE_SIDED_INCAMERA_OP"
                )

    def test_33_atomic_coupled_protect_blocks_delete_until_unprotected(self) -> None:
        prot = evaluate_coupled_clip_sub_vault_integrity(
            clip_stem="C0044", action="PROTECT", scope="COUPLED_PAIR", in_camera=True
        )
        self.assertTrue(prot.allowed)
        self.assertTrue(prot.resulting_protected)
        self.assertEqual(prot.integrity_status, "ATOMIC_COUPLED_PROTECT_UPDATED")

        blocked = evaluate_coupled_clip_sub_vault_integrity(
            clip_stem="C0044",
            clip_protected=True,
            sub_protected=True,
            action="DELETE",
            scope="COUPLED_PAIR",
            in_camera=True,
        )
        self.assertFalse(blocked.allowed)
        self.assertEqual(blocked.integrity_status, "BLOCKED_BY_PROTECT_LOCK")
        self.assertTrue(blocked.resulting_clip_present)
        self.assertTrue(blocked.resulting_sub_present)

        unprot = evaluate_coupled_clip_sub_vault_integrity(
            clip_stem="C0044",
            clip_protected=True,
            sub_protected=True,
            action="UNPROTECT",
            scope="COUPLED_PAIR",
            in_camera=True,
        )
        self.assertTrue(unprot.allowed)
        self.assertFalse(unprot.resulting_protected)

    def test_34_vault_verify_detects_orphan_sub_missing_sub_and_desynced_protect(self) -> None:
        r_orphan = evaluate_coupled_clip_sub_vault_integrity(
            clip_stem="C0050", clip_present=False, sub_present=True, action="VERIFY_ONLY"
        )
        self.assertFalse(r_orphan.allowed)
        self.assertEqual(r_orphan.orphan_anomaly, "ORPHAN_SUB_WITHOUT_CLIP")

        r_miss = evaluate_coupled_clip_sub_vault_integrity(
            clip_stem="C0051",
            clip_present=True,
            sub_present=False,
            expect_proxy_pair=True,
            action="VERIFY_ONLY",
        )
        self.assertFalse(r_miss.allowed)
        self.assertEqual(r_miss.orphan_anomaly, "MISSING_SUB_FOR_PX_CLIP")

        r_desync = evaluate_coupled_clip_sub_vault_integrity(
            clip_stem="C0052",
            clip_present=True,
            sub_present=True,
            clip_protected=True,
            sub_protected=False,
            action="VERIFY_ONLY",
        )
        self.assertFalse(r_desync.allowed)
        self.assertEqual(r_desync.orphan_anomaly, "DESYNCED_CLIP_SUB_PROTECT_FLAGS")

    def test_35_external_host_single_sided_delete_flagged_as_vault_anomaly(self) -> None:
        r_ext = evaluate_coupled_clip_sub_vault_integrity(
            clip_stem="C0053",
            clip_present=True,
            sub_present=True,
            action="DELETE",
            scope="CLIP_ONLY",
            in_camera=False,
        )
        self.assertFalse(r_ext.allowed)
        self.assertEqual(r_ext.orphan_anomaly, "ORPHAN_SUB_WITHOUT_CLIP")
        self.assertEqual(r_ext.integrity_status, "VAULT_ANOMALY_DETECTED")

    def test_36_vault_evaluator_rejects_path_traversal_clip_stems(self) -> None:
        for bad_stem in ("", "../C0001", "CLIP/C0001", "C0001.."):
            with self.assertRaises(ValueError):
                evaluate_coupled_clip_sub_vault_integrity(clip_stem=bad_stem)

    # ------------------------------------------------------------------
    # Group D (Tests 37-47): Pillar C — Focus Magnifier Scales & Bright Monitoring Interlocks
    # ------------------------------------------------------------------

    def test_37_movie_and_sq_initial_focus_mag_allows_only_x10_and_x40(self) -> None:
        self.assertEqual(
            FX3_INITIAL_FOCUS_MAG_MENU_PATH_P211,
            "MENU -> Focus -> [Focus Assistant] -> [Initial Focus Mag.]",
        )
        self.assertEqual(VALID_MOVIE_INITIAL_FOCUS_MAG_P211, ("x1.0", "x4.0"))
        for mode in ("Movie", "S&Q"):
            for crop in ("Full-Frame", "APS-C_S35"):
                for scale in ("x1.0", "x4.0"):
                    res = evaluate_focus_magnifier_and_bright_monitoring_interlocks(
                        capture_mode=mode, sensor_crop_mode=crop, initial_focus_mag=scale
                    )
                    self.assertEqual(res.initial_focus_mag, scale)
                for bad_scale in ("x2.1", "x1.5", "x3.0", "x6.0"):
                    with self.assertRaises(ValueError):
                        evaluate_focus_magnifier_and_bright_monitoring_interlocks(
                            capture_mode=mode,
                            sensor_crop_mode=crop,
                            initial_focus_mag=bad_scale,
                        )

    def test_38_still_ff_x10_x21_and_still_apsc_x10_x15_scales_enforced(self) -> None:
        self.assertEqual(VALID_STILL_FF_INITIAL_FOCUS_MAG_P211, ("x1.0", "x2.1"))
        self.assertEqual(VALID_STILL_APSC_INITIAL_FOCUS_MAG_P211, ("x1.0", "x1.5"))
        for scale in ("x1.0", "x2.1"):
            r_ff = evaluate_focus_magnifier_and_bright_monitoring_interlocks(
                capture_mode="Still", sensor_crop_mode="Full-Frame", initial_focus_mag=scale
            )
            self.assertEqual(r_ff.initial_focus_mag, scale)
        with self.assertRaises(ValueError):
            evaluate_focus_magnifier_and_bright_monitoring_interlocks(
                capture_mode="Still", sensor_crop_mode="Full-Frame", initial_focus_mag="x4.0"
            )
        with self.assertRaises(ValueError):
            evaluate_focus_magnifier_and_bright_monitoring_interlocks(
                capture_mode="Still", sensor_crop_mode="Full-Frame", initial_focus_mag="x1.5"
            )

        for scale in ("x1.0", "x1.5"):
            r_s35 = evaluate_focus_magnifier_and_bright_monitoring_interlocks(
                capture_mode="Still", sensor_crop_mode="APS-C_S35", initial_focus_mag=scale
            )
            self.assertEqual(r_s35.initial_focus_mag, scale)
        with self.assertRaises(ValueError):
            evaluate_focus_magnifier_and_bright_monitoring_interlocks(
                capture_mode="Still", sensor_crop_mode="APS-C_S35", initial_focus_mag="x2.1"
            )

    def test_39_focus_magnif_time_options_verified(self) -> None:
        self.assertEqual(VALID_FOCUS_MAGNIF_TIMES_P211, ("2 Sec", "5 Sec", "No Limit"))
        for dur in VALID_FOCUS_MAGNIF_TIMES_P211:
            res = evaluate_focus_magnifier_and_bright_monitoring_interlocks(
                focus_magnif_time=dur
            )
            self.assertEqual(res.focus_magnif_time, dur)
        with self.assertRaises(ValueError):
            evaluate_focus_magnifier_and_bright_monitoring_interlocks(
                focus_magnif_time="4 Sec"
            )

    def test_40_auto_magnifier_in_mf_blocked_in_movie_and_sq_even_when_ring_rotated(self) -> None:
        for mode in ("Movie", "S&Q"):
            res = evaluate_focus_magnifier_and_bright_monitoring_interlocks(
                capture_mode=mode,
                focus_mode="MF",
                auto_magnifier_in_mf_setting="On",
                focus_ring_rotated=True,
                marker_display_setting="On",
            )
            self.assertTrue(res.auto_magnifier_blocked_in_movie)
            self.assertFalse(res.auto_magnifier_in_mf_effective)
            self.assertFalse(res.auto_magnifier_triggered_active)
            self.assertTrue(res.marker_display_visible)

    def test_41_auto_magnifier_in_mf_triggers_in_still_mf_and_suppresses_markers(self) -> None:
        res = evaluate_focus_magnifier_and_bright_monitoring_interlocks(
            capture_mode="Still",
            sensor_crop_mode="Full-Frame",
            focus_mode="MF",
            initial_focus_mag="x2.1",
            auto_magnifier_in_mf_setting="On",
            focus_ring_rotated=True,
            marker_display_setting="On",
        )
        self.assertFalse(res.auto_magnifier_blocked_in_movie)
        self.assertTrue(res.auto_magnifier_in_mf_effective)
        self.assertTrue(res.auto_magnifier_triggered_active)
        self.assertFalse(res.marker_display_visible)
        self.assertTrue(res.marker_display_suppressed_by_magnifier)

    def test_42_marker_display_suppressed_during_movie_focus_magnifier_and_restored_after(self) -> None:
        active = evaluate_focus_magnifier_and_bright_monitoring_interlocks(
            capture_mode="Movie",
            initial_focus_mag="x4.0",
            focus_magnifier_custom_active=True,
            marker_display_setting="On",
        )
        self.assertFalse(active.marker_display_visible)
        self.assertTrue(active.marker_display_suppressed_by_magnifier)

        restored = evaluate_focus_magnifier_and_bright_monitoring_interlocks(
            capture_mode="Movie",
            initial_focus_mag="x4.0",
            focus_magnifier_custom_active=False,
            marker_display_setting="On",
        )
        self.assertTrue(restored.marker_display_visible)
        self.assertFalse(restored.marker_display_suppressed_by_magnifier)

    def test_43_bright_monitoring_custom_key_locked_out_during_focus_magnifier(self) -> None:
        locked_on = evaluate_focus_magnifier_and_bright_monitoring_interlocks(
            capture_mode="Movie",
            exposure_mode="M",
            focus_mode="MF",
            focus_magnifier_custom_active=True,
            bright_monitoring_prior_active=False,
            bright_monitoring_key_pressed=True,
        )
        self.assertTrue(locked_on.bright_monitoring_key_locked_out)
        self.assertFalse(locked_on.bright_monitoring_active_after)

        locked_still_auto = evaluate_focus_magnifier_and_bright_monitoring_interlocks(
            capture_mode="Still",
            exposure_mode="M",
            focus_mode="MF",
            auto_magnifier_in_mf_setting="On",
            focus_ring_rotated=True,
            bright_monitoring_prior_active=False,
            bright_monitoring_key_pressed=True,
        )
        self.assertTrue(locked_still_auto.bright_monitoring_key_locked_out)
        self.assertFalse(locked_still_auto.bright_monitoring_active_after)

    def test_44_bright_monitoring_toggles_in_pasm_mf_and_forces_setting_effect_off(self) -> None:
        self.assertEqual(PASM_EXPOSURE_MODES_P211, ("P", "A", "S", "M"))
        for exp in PASM_EXPOSURE_MODES_P211:
            res = evaluate_focus_magnifier_and_bright_monitoring_interlocks(
                capture_mode="Movie",
                exposure_mode=exp,
                focus_mode="MF",
                live_view_display_setting="Setting Effect ON",
                bright_monitoring_prior_active=False,
                bright_monitoring_key_pressed=True,
            )
            self.assertFalse(res.bright_monitoring_key_locked_out)
            self.assertTrue(res.bright_monitoring_active_after)
            self.assertEqual(res.effective_live_view_display, "Setting Effect OFF")

    def test_45_bright_monitoring_auto_cancels_when_leaving_pasm(self) -> None:
        for non_pasm in ("Flexible Exp.", "Auto", "Scene"):
            res = evaluate_focus_magnifier_and_bright_monitoring_interlocks(
                capture_mode="Movie",
                exposure_mode=non_pasm,
                focus_mode="MF",
                bright_monitoring_prior_active=True,
            )
            self.assertTrue(res.bright_monitoring_auto_canceled)
            self.assertFalse(res.bright_monitoring_active_after)
            self.assertEqual(res.effective_live_view_display, "Setting Effect ON")

    def test_46_bright_monitoring_auto_cancels_when_leaving_mf(self) -> None:
        for af_mode in ("AF-C", "AF-S", "DMF"):
            res = evaluate_focus_magnifier_and_bright_monitoring_interlocks(
                capture_mode="Movie",
                exposure_mode="M",
                focus_mode=af_mode,
                bright_monitoring_prior_active=True,
            )
            self.assertTrue(res.bright_monitoring_auto_canceled)
            self.assertFalse(res.bright_monitoring_active_after)

    def test_47_bright_monitoring_auto_cancels_on_camera_power_off(self) -> None:
        res = evaluate_focus_magnifier_and_bright_monitoring_interlocks(
            capture_mode="Movie",
            exposure_mode="M",
            focus_mode="MF",
            bright_monitoring_prior_active=True,
            power_off_event=True,
        )
        self.assertTrue(res.bright_monitoring_auto_canceled)
        self.assertFalse(res.bright_monitoring_active_after)
        self.assertEqual(res.effective_live_view_display, "Setting Effect ON")

    # ------------------------------------------------------------------
    # Group E (Tests 48-54): Pillar D — Zero-Write Firewall, Matrix, Exports & CLI (44/44)
    # ------------------------------------------------------------------

    def test_48_write_guard_blocks_all_persistent_emmc_spinor_and_cp_partitions(self) -> None:
        forbidden_targets = (
            "p2:/setting/Backup.bin",
            "p2:/setting/BODYDATA.DAT",
            "p5:/wbi/hibdrv_snapshot.img",
            "p8:/cpapp-b.bin",
            "p12:/cert/device_c2pa.der",
            "p18:/lens/mount_calib.bin",
            "/dev/cnflasha2",
            "/dev/nflasha8",
            "spi_nor:0x000000",
        )
        for target in forbidden_targets:
            res = evaluate_phase211_write_guard(target, operation="WRITE")
            self.assertFalse(res.allowed, target)
            self.assertFalse(res.persistent_emmc_writes_authorized)
            self.assertFalse(res.spi_nor_write_authorized)
            self.assertFalse(res.el3_payload_transmit_authorized)
            self.assertEqual(res.physical_usb_packets_emitted, 0)

    def test_49_write_guard_allows_volatile_overlay_and_fails_closed_on_unknown_paths(self) -> None:
        ok_tmp = evaluate_phase211_write_guard(
            f"{VOLATILE_WAVE28_OVERLAY_DIR_P211}/state.json", operation="WRITE"
        )
        self.assertTrue(ok_tmp.allowed)
        ok_ram = evaluate_phase211_write_guard("ram://wave28_state", operation="WRITE")
        self.assertTrue(ok_ram.allowed)
        ok_read = evaluate_phase211_write_guard("p2:/setting/Backup.bin", operation="READ")
        self.assertTrue(ok_read.allowed)
        denied_var = evaluate_phase211_write_guard("/var/lib/persist.db", operation="WRITE")
        self.assertFalse(denied_var.allowed)

    def test_50_compat_matrix_has_12_touchpoints_and_all_four_bridge_classes(self) -> None:
        mat = build_phase211_compat_matrix()
        self.assertEqual(mat.total_touchpoints, 12)
        self.assertTrue(mat.all_classes_valid)
        ids = [e.touchpoint_id for e in mat.entries]
        self.assertEqual(ids, [f"P211-{i:02d}" for i in range(1, 13)])
        for cls in (
            BRIDGE_CLASS_NATIVE_PASSTHROUGH,
            BRIDGE_CLASS_SHIM_TRANSLATED,
            BRIDGE_CLASS_MASKED_ABSENT_HW,
            BRIDGE_CLASS_HARD_WRITE_PROTECTED,
        ):
            self.assertIn(cls, VALID_BRIDGE_CLASSES)
            self.assertGreaterEqual(mat.class_counts[cls], 1)

    def test_51_package_init_exports_all_phase211_symbols(self) -> None:
        expected_exports = (
            "PHASE_211_SCHEMA",
            "PHASE_211_VERSION",
            "AUDITOR_INDEX_P211",
            "FX3_PROXY_FORMAT_SPECS_P211",
            "analyze_realhw_hdmi_log1080_proxy_vault_and_focusmag_brightmon",
            "realhw_hdmi_log1080_proxy_vault_and_focusmag_brightmon_report_to_dict",
            "evaluate_hdmi_log_1080p_vs_hdmionly_4k_and_lcd_blanking",
            "evaluate_proxy_codec_matrix_and_hfr_cutoffs",
            "evaluate_coupled_clip_sub_vault_integrity",
            "evaluate_focus_magnifier_and_bright_monitoring_interlocks",
            "evaluate_phase211_write_guard",
            "build_phase211_compat_matrix",
        )
        for sym in expected_exports:
            self.assertIn(sym, pkg.__all__)
            self.assertTrue(hasattr(pkg, sym), sym)

    def test_52_cli_subcommand_json_succeeds_in_clean_room_and_default_modes(self) -> None:
        for argv in (
            ["audit-realhw-hdmi-log1080-proxy-focusmag-brightmon", "--clean-room", "--json"],
            ["audit-realhw-hdmi-log1080-proxy-focusmag-brightmon", "--json"],
        ):
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = cli_main(argv)
            self.assertEqual(rc, 0)
            payload = json.loads(buf.getvalue())
            self.assertEqual(payload["schema"], PHASE_211_SCHEMA)
            self.assertEqual(payload["auditor_index"], "44/44")
            self.assertTrue(payload["all_checks_passed"])

    def test_53_run_audit_all_registers_44_of_44_auditors_and_passes(self) -> None:
        summary = run_audit_all(clean_room=True)
        self.assertTrue(summary["all_checks_passed"])
        audit_keys = [k for k in summary.keys() if k != "all_checks_passed"]
        self.assertGreaterEqual(len(audit_keys), 44)
        self.assertIn(
            "realhw_hdmi_log1080_proxy_vault_and_focusmag_brightmon_audit", summary
        )
        p211_entry = summary[
            "realhw_hdmi_log1080_proxy_vault_and_focusmag_brightmon_audit"
        ]
        self.assertEqual(p211_entry["auditor_index"], "44/44")
        self.assertTrue(p211_entry["all_checks_passed"])

    def test_54_fx3_702_vs_fx6_601_exclusive_appfw_markers_stay_disjoint(self) -> None:
        fx3_app, fx6_app, *_ = (
            build_clean_room_realhw_hdmi_log1080_proxy_focusmag_brightmon_fixtures()
        )
        for tok in APPFW_FX3_702_EXCLUSIVE_MARKERS_P211:
            self.assertGreaterEqual(fx3_app.marker_hits[tok], 1)
            self.assertEqual(fx6_app.marker_hits[tok], 0)
        for tok in APPFW_FX6_601_EXCLUSIVE_MARKERS_P211:
            self.assertGreaterEqual(fx6_app.marker_hits[tok], 1)
            self.assertEqual(fx3_app.marker_hits[tok], 0)


if __name__ == "__main__":
    unittest.main()
