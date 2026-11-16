"""Unit tests for Phase 218 (45th Milestone Auditor, `45/45`) Wave-29 FX3/FX6 auditor."""

from __future__ import annotations

import ast
import io
import json
import os
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import fx3_firmware_lab
from fx3_firmware_lab.__main__ import main as cli_main, run_audit_all
from fx3_firmware_lab.realhw_filesettings_shotmark_tcregen_and_reclamp_auditor import (
    VALID_BRIDGE_CLASSES,
    APPFW_FX3_702_EXCLUSIVE_MARKERS_P218,
    APPFW_FX6_601_EXCLUSIVE_MARKERS_P218,
    APPFW_SHARED_WAVE29_MARKERS_P218,
    AUDITOR_INDEX_P218,
    CPAPP_BOUNDED_HEAD_BYTES_P218,
    CPAPP_BOUNDED_TAIL_BYTES_P218,
    CPAPP_SHARED_MARKERS_P218,
    DEFAULT_MOVIE_CLIP_DIR_P218,
    DONOR_COLD_SCAN_BUDGET_SEC_P218,
    EXPECTED_FX3_APPFW_BYTES_P218,
    EXPECTED_FX3_CPAPP_BYTES_P218,
    EXPECTED_FX3_UXC_EN_F_BYTES_P218,
    EXPECTED_FX6_APPFW_BYTES_P218,
    EXPECTED_FX6_CPAPP_BYTES_P218,
    EXPECTED_FX6_UXC_EN_BYTES_P218,
    FORBIDDEN_NON_FX3_REC_LAMP_MODES_P218,
    MAX_TITLE_NAME_ASCII_CHARS_P218,
    PHASE_218_SCHEMA,
    PHASE_218_VERSION,
    SHOTMARK_NRTM_SUFFIX_P218,
    TITLE_ALLOWED_ASCII_SET_P218,
    TITLE_ALLOWED_SYMBOLS_P218,
    UXC_FX3_EN_F_REQUIRED_TOKENS_P218,
    UXC_FX6_EN_REQUIRED_TOKENS_P218,
    VALID_FILE_NAME_FORMATS_P218,
    VALID_FX3_REC_LAMP_MODES_P218,
    VOLATILE_WAVE29_OVERLAY_DIR_P218,
    _DONOR_SCAN_CACHE_P218,
    advance_smpte_tc_one_frame,
    analyze_realhw_filesettings_shotmark_tcregen_and_reclamp,
    build_clean_room_realhw_filesettings_shotmark_tcregen_reclamp_fixtures,
    build_phase218_compat_matrix,
    evaluate_file_settings_and_sdhc_lock,
    evaluate_phase218_write_guard,
    evaluate_rec_lamp_coupled_tally_and_silent_audio_lock,
    evaluate_shotmark_xml_jump_and_ftp_filter,
    evaluate_tc_regenerate_slot1_and_ext_lk_release,
    realhw_filesettings_shotmark_tcregen_and_reclamp_report_to_dict,
    validate_fx3_title_name_settings,
)

AUDITOR_PATH = (
    Path(__file__).resolve().parents[1]
    / "fx3_firmware_lab"
    / "realhw_filesettings_shotmark_tcregen_and_reclamp_auditor.py"
)


class TestPhase218FilesettingsShotmarkTcregenReclampAuditor(unittest.TestCase):
    """55 dual-mode tests covering Wave-29 FX3 Ver. 7.02 hardware rules & 45/45 milestone."""

    def test_01_ast_strictly_rdonly_and_zero_mutating_calls(self) -> None:
        src = AUDITOR_PATH.read_text(encoding="utf-8")
        tree = ast.parse(src, filename=str(AUDITOR_PATH))
        os_open_calls = 0
        forbidden_attrs = {
            "write",
            "writelines",
            "write_bytes",
            "write_text",
            "unlink",
            "remove",
            "rmdir",
            "mkdir",
            "makedirs",
            "popen",
            "system",
        }
        forbidden_flags = {"O_WRONLY", "O_RDWR", "O_CREAT", "O_TRUNC", "O_APPEND"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertNotIn(alias.name, {"subprocess", "socket", "shutil", "tempfile"})
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    self.assertNotEqual(node.func.id, "open")
                elif isinstance(node.func, ast.Attribute):
                    self.assertNotIn(node.func.attr, forbidden_attrs)
                    if (
                        isinstance(node.func.value, ast.Name)
                        and node.func.value.id == "os"
                        and node.func.attr == "open"
                    ):
                        os_open_calls += 1
                        self.assertGreaterEqual(len(node.args), 2)
                        flag_dump = ast.dump(node.args[1])
                        self.assertIn("O_RDONLY", flag_dump)
                        for bad in forbidden_flags:
                            self.assertNotIn(bad, flag_dump)
        self.assertGreaterEqual(os_open_calls, 3)

    def test_02_default_and_clean_room_audits_pass_and_index_45_of_45(self) -> None:
        for cr in (False, True):
            rep = analyze_realhw_filesettings_shotmark_tcregen_and_reclamp(clean_room=cr)
            self.assertEqual(rep.schema, PHASE_218_SCHEMA)
            self.assertEqual(rep.version, PHASE_218_VERSION)
            self.assertEqual(rep.auditor_index, "45/45")
            self.assertEqual(AUDITOR_INDEX_P218, "45/45")
            self.assertTrue(rep.all_checks_passed)
            self.assertTrue(rep.donor_cold_scan_within_sla)
            self.assertLessEqual(rep.donor_cold_scan_duration_sec, DONOR_COLD_SCAN_BUDGET_SEC_P218)
            self.assertTrue(rep.pillar_1_file_settings_and_shotmark.passed)
            self.assertTrue(rep.pillar_2_tc_regenerate_slot1_and_ext_lk.passed)
            self.assertTrue(rep.pillar_3_rec_lamp_coupled_tally_and_silent_audio.passed)
            self.assertTrue(rep.pillar_4_write_guard_and_matrix.passed)
            if cr or os.environ.get("FX3_FX6_FORCE_CLEAN_ROOM") == "1":
                self.assertEqual(rep.source_mode, "CLEAN_ROOM_SYNTHETIC")
                self.assertTrue(rep.clean_room_forced)
            else:
                self.assertIn(rep.source_mode, {"LOCAL_DONOR_RDONLY", "CLEAN_ROOM_SYNTHETIC"})

    def test_03_donor_scan_cache_and_env_force_clean_room(self) -> None:
        _DONOR_SCAN_CACHE_P218.clear()
        r1 = analyze_realhw_filesettings_shotmark_tcregen_and_reclamp(clean_room=False)
        r2 = analyze_realhw_filesettings_shotmark_tcregen_and_reclamp(clean_room=False)
        self.assertEqual(r1.report_digest_sha256, r2.report_digest_sha256)
        with patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            r_env = analyze_realhw_filesettings_shotmark_tcregen_and_reclamp(clean_room=False)
            self.assertEqual(r_env.source_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertTrue(r_env.clean_room_forced)
            self.assertTrue(r_env.all_checks_passed)

    def test_04_missing_repo_root_graceful_clean_room_fallback(self) -> None:
        with patch(
            "fx3_firmware_lab.realhw_filesettings_shotmark_tcregen_and_reclamp_auditor.resolve_donor_file",
            return_value=None,
        ):
            rep = analyze_realhw_filesettings_shotmark_tcregen_and_reclamp(
                repo_root=Path("/nonexistent/fx3_p218_missing_root"),
                clean_room=False,
            )
            self.assertEqual(rep.source_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertTrue(rep.all_checks_passed)

    def test_05_report_digest_sha256_deterministic_and_excludes_scan_jitter(self) -> None:
        c1 = analyze_realhw_filesettings_shotmark_tcregen_and_reclamp(clean_room=True)
        c2 = analyze_realhw_filesettings_shotmark_tcregen_and_reclamp(clean_room=True)
        self.assertEqual(len(c1.report_digest_sha256), 64)
        self.assertEqual(c1.report_digest_sha256, c2.report_digest_sha256)

    def test_06_zero_raw_firmware_bytes_leaked_in_json_payload(self) -> None:
        payload = realhw_filesettings_shotmark_tcregen_and_reclamp_report_to_dict(
            analyze_realhw_filesettings_shotmark_tcregen_and_reclamp(clean_room=False)
        )
        self.assertEqual(
            payload["pillar_4_write_guard_and_matrix"]["raw_firmware_bytes_leaked"], 0
        )

        def _walk(v: object) -> None:
            self.assertNotIsInstance(v, (bytes, bytearray, memoryview))
            if isinstance(v, dict):
                for k, sub in v.items():
                    self.assertIsInstance(k, str)
                    _walk(sub)
            elif isinstance(v, (list, tuple)):
                for item in v:
                    _walk(item)

        _walk(payload)
        encoded = json.dumps(payload, sort_keys=True)
        self.assertNotIn("\\x7fELF", encoded)

    def test_07_donor_and_clean_room_binary_byte_sizes_and_markers(self) -> None:
        fx3_app, fx6_app, fx3_uxc, fx6_uxc, fx3_cp, fx6_cp = (
            build_clean_room_realhw_filesettings_shotmark_tcregen_reclamp_fixtures()
        )
        self.assertEqual(fx3_app.file_bytes, EXPECTED_FX3_APPFW_BYTES_P218)
        self.assertEqual(fx6_app.file_bytes, EXPECTED_FX6_APPFW_BYTES_P218)
        self.assertEqual(fx3_uxc.file_bytes, EXPECTED_FX3_UXC_EN_F_BYTES_P218)
        self.assertEqual(fx6_uxc.file_bytes, EXPECTED_FX6_UXC_EN_BYTES_P218)
        self.assertEqual(fx3_uxc.header_magic_hex, "75786407")
        self.assertEqual(fx6_uxc.header_magic_hex, "75786407")
        self.assertEqual(fx3_cp.file_bytes, EXPECTED_FX3_CPAPP_BYTES_P218)
        self.assertEqual(fx6_cp.file_bytes, EXPECTED_FX6_CPAPP_BYTES_P218)
        self.assertEqual(
            fx3_cp.bounded_bytes_scanned,
            CPAPP_BOUNDED_HEAD_BYTES_P218 + CPAPP_BOUNDED_TAIL_BYTES_P218,
        )
        for m in APPFW_SHARED_WAVE29_MARKERS_P218:
            self.assertGreaterEqual(fx3_app.marker_hits[m], 1)
            self.assertGreaterEqual(fx6_app.marker_hits[m], 1)
        for m in APPFW_FX3_702_EXCLUSIVE_MARKERS_P218:
            self.assertGreaterEqual(fx3_app.marker_hits[m], 1)
            self.assertEqual(fx6_app.marker_hits[m], 0)
        for m in APPFW_FX6_601_EXCLUSIVE_MARKERS_P218:
            self.assertGreaterEqual(fx6_app.marker_hits[m], 1)
            self.assertEqual(fx3_app.marker_hits[m], 0)
        for t in UXC_FX3_EN_F_REQUIRED_TOKENS_P218:
            self.assertGreaterEqual(fx3_uxc.token_hits[t], 1)
        for t in UXC_FX6_EN_REQUIRED_TOKENS_P218:
            self.assertGreaterEqual(fx6_uxc.token_hits[t], 1)
        for cm in CPAPP_SHARED_MARKERS_P218:
            self.assertGreaterEqual(fx3_cp.marker_hits[cm], 1)
            self.assertGreaterEqual(fx6_cp.marker_hits[cm], 1)

    # --- Pillar A: [File Settings], <=37-char Title, SDHC FAT32 Lock & Shot Mark1/2 ---

    def test_08_file_name_format_standard_slot1_and_slot2(self) -> None:
        self.assertEqual(
            VALID_FILE_NAME_FORMATS_P218,
            ("Standard", "Cam ID + Reel#", "Title", "Date + Title", "Title + Date"),
        )
        r1 = evaluate_file_settings_and_sdhc_lock(
            active_slot="Slot 1", requested_file_name_format="Standard", prior_series_counter=0
        )
        r2 = evaluate_file_settings_and_sdhc_lock(
            active_slot="Slot 2", requested_file_name_format="Standard", prior_series_counter=41
        )
        self.assertEqual(r1.generated_clip_filename, "C0001.MP4")
        self.assertEqual(r1.generated_nrtm_xml_filename, "C0001M01.XML")
        self.assertEqual(r2.generated_clip_filename, "C0042.MP4")
        self.assertEqual(r2.generated_nrtm_xml_filename, "C0042M01.XML")

    def test_09_file_name_format_cam_id_plus_reel_positions_c_l_r(self) -> None:
        for pos, cam, reel in (("C", "A", 1), ("L", "B", 12), ("R", "Z", 999)):
            r = evaluate_file_settings_and_sdhc_lock(
                requested_file_name_format="Cam ID + Reel#",
                cam_id=cam,
                reel_number=reel,
                camera_position=pos,
                prior_series_counter=6,
            )
            self.assertEqual(r.generated_clip_filename, f"{cam}{reel:03d}{pos}0007.MP4")

    def test_10_file_name_format_title_date_plus_title_and_title_plus_date(self) -> None:
        r_title = evaluate_file_settings_and_sdhc_lock(
            requested_file_name_format="Title",
            title_name="FX3_CAM-A",
            prior_series_counter=2,
        )
        r_dt = evaluate_file_settings_and_sdhc_lock(
            requested_file_name_format="Date + Title",
            title_name="DOC",
            date_yymmdd="261115",
            prior_series_counter=2,
        )
        r_td = evaluate_file_settings_and_sdhc_lock(
            requested_file_name_format="Title + Date",
            title_name="DOC",
            date_yymmdd="261115",
            prior_series_counter=2,
        )
        self.assertEqual(r_title.generated_clip_filename, "FX3_CAM-A0003.MP4")
        self.assertEqual(r_dt.generated_clip_filename, "261115DOC0003.MP4")
        self.assertEqual(r_td.generated_clip_filename, "DOC2611150003.MP4")

    def test_11_simult_recording_produces_identical_clip_and_m01_xml_names(self) -> None:
        r_sim = evaluate_file_settings_and_sdhc_lock(
            active_slot="Simult. Recording",
            slot1_card_type="CFEXPRESS_A_EXFAT",
            slot2_card_type="SDXC_EXFAT",
            requested_file_name_format="Cam ID + Reel#",
            cam_id="C",
            reel_number=5,
            prior_series_counter=99,
        )
        self.assertEqual(r_sim.generated_clip_filename, "C005C0100.MP4")
        self.assertEqual(r_sim.generated_nrtm_xml_filename, f"C005C0100{SHOTMARK_NRTM_SUFFIX_P218}")
        self.assertFalse(r_sim.sdhc_card_detected)

    def test_12_title_name_settings_exact_37_char_allowed_ascii_set(self) -> None:
        self.assertEqual(MAX_TITLE_NAME_ASCII_CHARS_P218, 37)
        self.assertEqual(TITLE_ALLOWED_SYMBOLS_P218, ".-_@!#$%+=^~(),;[]")
        self.assertEqual(len(TITLE_ALLOWED_ASCII_SET_P218), 26 + 26 + 10 + 18)
        valid_37 = "Az09.-_@!#$%+=^~(),;[]FX3_Wave29_Test"
        self.assertEqual(len(valid_37), 37)
        self.assertTrue(validate_fx3_title_name_settings(valid_37))
        self.assertTrue(validate_fx3_title_name_settings("A"))
        r = evaluate_file_settings_and_sdhc_lock(
            requested_file_name_format="Title", title_name=valid_37
        )
        self.assertEqual(r.title_char_len, 37)
        self.assertEqual(r.generated_clip_filename, f"{valid_37}0001.MP4")

    def test_13_title_name_settings_rejects_empty_38_chars_spaces_slashes_and_unicode(self) -> None:
        bad_titles = (
            "",
            "A" * 38,
            "HAS SPACE",
            "BAD/SLASH",
            "BAD\\SLASH",
            "BAD:COLON",
            "BAD*STAR",
            "BAD?Q",
            "BAD<GT>",
            "BAD|PIPE",
            "日本語タイトル",
        )
        for bad in bad_titles:
            self.assertFalse(validate_fx3_title_name_settings(bad), msg=f"Should reject {bad!r}")
            with self.assertRaises(ValueError):
                evaluate_file_settings_and_sdhc_lock(
                    requested_file_name_format="Title", title_name=bad
                )

    def test_14_title_change_non_retroactive_on_existing_clips(self) -> None:
        r = evaluate_file_settings_and_sdhc_lock(
            requested_file_name_format="Title", title_name="NEW_SCENE"
        )
        self.assertFalse(r.retroactive_rename_existing_clips)
        self.assertIn("strictly to subsequent clip", r.reason)

    def test_15_file_number_series_persists_across_empty_card_swap(self) -> None:
        r = evaluate_file_settings_and_sdhc_lock(
            file_number_mode="Series",
            prior_series_counter=54,
            card_max_existing_counter=0,
            card_swapped_empty=True,
        )
        self.assertEqual(r.next_clip_counter, 55)
        self.assertEqual(r.generated_clip_filename, "C0055.MP4")

    def test_16_file_number_series_adopts_higher_existing_card_counter(self) -> None:
        r = evaluate_file_settings_and_sdhc_lock(
            file_number_mode="Series",
            prior_series_counter=12,
            card_max_existing_counter=240,
            card_swapped_empty=False,
        )
        self.assertEqual(r.next_clip_counter, 241)

    def test_17_file_number_series_counter_reset_returns_to_0001(self) -> None:
        r = evaluate_file_settings_and_sdhc_lock(
            file_number_mode="Series",
            prior_series_counter=512,
            card_swapped_empty=True,
            series_counter_reset_triggered=True,
        )
        self.assertEqual(r.next_clip_counter, 1)
        self.assertEqual(r.generated_clip_filename, "C0001.MP4")

    def test_18_file_number_reset_restarts_0001_on_empty_card_and_increments_non_empty(self) -> None:
        r_empty = evaluate_file_settings_and_sdhc_lock(
            file_number_mode="Reset",
            prior_series_counter=300,
            card_max_existing_counter=18,
            card_swapped_empty=True,
        )
        r_non_empty = evaluate_file_settings_and_sdhc_lock(
            file_number_mode="Reset",
            prior_series_counter=300,
            card_max_existing_counter=18,
            card_swapped_empty=False,
        )
        self.assertEqual(r_empty.next_clip_counter, 1)
        self.assertEqual(r_non_empty.next_clip_counter, 19)

    def test_19_file_number_9999_wraps_to_0001(self) -> None:
        r = evaluate_file_settings_and_sdhc_lock(
            file_number_mode="Series",
            prior_series_counter=9999,
            card_max_existing_counter=9999,
        )
        self.assertEqual(r.next_clip_counter, 1)
        self.assertEqual(r.generated_clip_filename, "C0001.MP4")

    def test_20_sdhc_fat32_forces_standard_format_and_blocks_custom_folder(self) -> None:
        r = evaluate_file_settings_and_sdhc_lock(
            active_slot="Slot 1",
            slot1_card_type="SDHC_FAT32",
            requested_file_name_format="Cam ID + Reel#",
            custom_movie_folder_name="SCENE_02",
            prior_series_counter=7,
        )
        self.assertTrue(r.sdhc_card_detected)
        self.assertTrue(r.sdhc_forced_standard_lock)
        self.assertEqual(r.effective_file_name_format, "Standard")
        self.assertTrue(r.custom_movie_folder_requested)
        self.assertFalse(r.custom_movie_folder_allowed)
        self.assertEqual(r.effective_movie_clip_dir, DEFAULT_MOVIE_CLIP_DIR_P218)
        self.assertEqual(r.generated_clip_filename, "C0008.MP4")

    def test_21_sdhc_in_either_slot_during_simult_recording_enforces_lock(self) -> None:
        r = evaluate_file_settings_and_sdhc_lock(
            active_slot="Simult. Recording",
            slot1_card_type="CFEXPRESS_A_EXFAT",
            slot2_card_type="SDHC_FAT32",
            requested_file_name_format="Title",
            title_name="CAM_A",
            custom_movie_folder_name="DAY1",
        )
        self.assertTrue(r.sdhc_card_detected)
        self.assertTrue(r.sdhc_forced_standard_lock)
        self.assertEqual(r.effective_file_name_format, "Standard")
        self.assertFalse(r.custom_movie_folder_allowed)

    def test_22_exfat_cfexpress_and_sdxc_allow_custom_movie_folder_and_reject_traversal(self) -> None:
        r = evaluate_file_settings_and_sdhc_lock(
            active_slot="Slot 1",
            slot1_card_type="CFEXPRESS_A_EXFAT",
            custom_movie_folder_name="CLIP_REEL02",
        )
        self.assertTrue(r.custom_movie_folder_allowed)
        self.assertEqual(r.effective_movie_clip_dir, "/PRIVATE/M4ROOT/CLIP_REEL02")
        with self.assertRaises(ValueError):
            evaluate_file_settings_and_sdhc_lock(custom_movie_folder_name="../ESCAPE")

    def test_23_file_settings_rejects_invalid_parameters_and_empty_active_slot(self) -> None:
        with self.assertRaises(ValueError):
            evaluate_file_settings_and_sdhc_lock(active_slot="Slot 3")
        with self.assertRaises(ValueError):
            evaluate_file_settings_and_sdhc_lock(active_slot="Slot 1", slot1_card_type="NONE")
        with self.assertRaises(ValueError):
            evaluate_file_settings_and_sdhc_lock(cam_id="a")
        with self.assertRaises(ValueError):
            evaluate_file_settings_and_sdhc_lock(reel_number=0)
        with self.assertRaises(ValueError):
            evaluate_file_settings_and_sdhc_lock(camera_position="X")
        with self.assertRaises(ValueError):
            evaluate_file_settings_and_sdhc_lock(date_yymmdd="20261115")

    def test_24_shotmark_live_and_playback_edits_update_m01_xml_sidecar(self) -> None:
        clips = (("C0001", False, False), ("C0002", True, False))
        r_m1 = evaluate_shotmark_xml_jump_and_ftp_filter(
            clips=clips, edited_clip_stem="C0001", edit_operation="LIVE_ADD_MARK1"
        )
        self.assertTrue(r_m1.nrtm_xml_sidecar_updated)
        self.assertTrue(r_m1.clips_after_edit[0].shot_mark1)
        self.assertFalse(r_m1.clips_after_edit[0].shot_mark2)
        self.assertTrue(r_m1.clips_after_edit[0].nrtm_xml_relpath.endswith("/C0001M01.XML"))

        r_both = evaluate_shotmark_xml_jump_and_ftp_filter(
            clips=clips, edited_clip_stem="C0001", edit_operation="LIVE_ADD_BOTH"
        )
        self.assertTrue(r_both.clips_after_edit[0].shot_mark1)
        self.assertTrue(r_both.clips_after_edit[0].shot_mark2)

        r_toggle = evaluate_shotmark_xml_jump_and_ftp_filter(
            clips=clips, edited_clip_stem="C0002", edit_operation="TOGGLE_MARK1"
        )
        self.assertFalse(r_toggle.clips_after_edit[1].shot_mark1)

    def test_25_shotmark_all_four_image_jump_modes(self) -> None:
        clips = (
            ("C0001", True, False),
            ("C0002", False, True),
            ("C0003", True, True),
            ("C0004", False, False),
        )
        j_any = evaluate_shotmark_xml_jump_and_ftp_filter(
            clips=clips, image_jump_mode="Shot Mark Only"
        )
        j_m1 = evaluate_shotmark_xml_jump_and_ftp_filter(
            clips=clips, image_jump_mode="Shot Mark1 Only"
        )
        j_m2 = evaluate_shotmark_xml_jump_and_ftp_filter(
            clips=clips, image_jump_mode="Shot Mark2 Only"
        )
        j_none = evaluate_shotmark_xml_jump_and_ftp_filter(
            clips=clips, image_jump_mode="No Shot Mark"
        )
        self.assertEqual(j_any.image_jump_matched_stems, ("C0001", "C0002", "C0003"))
        self.assertEqual(j_m1.image_jump_matched_stems, ("C0001", "C0003"))
        self.assertEqual(j_m2.image_jump_matched_stems, ("C0002", "C0003"))
        self.assertEqual(j_none.image_jump_matched_stems, ("C0004",))

    def test_26_shotmark_ftp_filters_only_shot_mark_mov_and_all(self) -> None:
        clips = (("C0001", True, False), ("C0002", False, False), ("C0003", False, True))
        f_sm_mov = evaluate_shotmark_xml_jump_and_ftp_filter(
            clips=clips, ftp_target_movie_filter="Only Shot Mark Mov."
        )
        f_sm = evaluate_shotmark_xml_jump_and_ftp_filter(
            clips=clips, ftp_target_movie_filter="Only Shot Mark"
        )
        f_all = evaluate_shotmark_xml_jump_and_ftp_filter(
            clips=clips, ftp_target_movie_filter="All"
        )
        self.assertEqual(f_sm_mov.ftp_selected_stems, ("C0001", "C0003"))
        self.assertEqual(f_sm.ftp_selected_stems, ("C0001", "C0003"))
        self.assertEqual(f_all.ftp_selected_stems, ("C0001", "C0002", "C0003"))

    def test_27_shotmark_rejects_invalid_ops_modes_empty_clips_and_missing_stem(self) -> None:
        with self.assertRaises(ValueError):
            evaluate_shotmark_xml_jump_and_ftp_filter(clips=())
        with self.assertRaises(ValueError):
            evaluate_shotmark_xml_jump_and_ftp_filter(
                clips=(("C0001", False, False),), edit_operation="BAD_OP"
            )
        with self.assertRaises(ValueError):
            evaluate_shotmark_xml_jump_and_ftp_filter(
                clips=(("C0001", False, False),),
                edited_clip_stem="C9999",
                edit_operation="TOGGLE_MARK2",
            )

    # --- Pillar B: [TC/UB] Regenerate Slot-1 Master Read, Forced Rec Run & EXT-LK Release ---

    def test_28_smpte_tc_advance_one_frame_ndf_across_all_six_frame_rates(self) -> None:
        cases = (
            ("23.98p", "01:00:00:23", "01:00:01:00"),
            ("24.00p", "01:00:00:23", "01:00:01:00"),
            ("25p", "01:00:00:24", "01:00:01:00"),
            ("29.97p", "01:00:00:29", "01:00:01:00"),
            ("50p", "01:00:00:49", "01:00:01:00"),
            ("59.94p", "01:00:00:59", "01:00:01:00"),
        )
        for fps, tc_in, tc_out in cases:
            self.assertEqual(
                advance_smpte_tc_one_frame(tc_in, rec_frame_rate=fps, drop_frame=False), tc_out
            )

    def test_29_smpte_tc_advance_one_frame_drop_frame_2997p_and_5994p_minute_rollover(self) -> None:
        # Non-10th minute skips :00 and :01 (29.97 DF) or :00..:03 (59.94 DF); 10th minute keeps :00
        self.assertEqual(
            advance_smpte_tc_one_frame("00:00:59;29", rec_frame_rate="29.97p", drop_frame=True),
            "00:01:00;02",
        )
        self.assertEqual(
            advance_smpte_tc_one_frame("00:09:59;29", rec_frame_rate="29.97p", drop_frame=True),
            "00:10:00;00",
        )
        self.assertEqual(
            advance_smpte_tc_one_frame("00:00:59;59", rec_frame_rate="59.94p", drop_frame=True),
            "00:01:00;04",
        )
        self.assertEqual(
            advance_smpte_tc_one_frame("00:09:59;59", rec_frame_rate="59.94p", drop_frame=True),
            "00:10:00;00",
        )

    def test_30_smpte_tc_advance_24h_wrap_and_invalid_tc_rejection(self) -> None:
        self.assertEqual(
            advance_smpte_tc_one_frame("23:59:59:23", rec_frame_rate="24.00p"), "00:00:00:00"
        )
        with self.assertRaises(ValueError):
            advance_smpte_tc_one_frame("01:00:00:24", rec_frame_rate="24.00p")
        with self.assertRaises(ValueError):
            advance_smpte_tc_one_frame("bad_tc", rec_frame_rate="24.00p")

    def test_31_regenerate_reads_active_slot1_or_slot2_and_empty_card_starts_zero(self) -> None:
        r_s1 = evaluate_tc_regenerate_slot1_and_ext_lk_release(
            recording_media="Slot 1",
            tc_make="Regenerate",
            slot1_last_end_tc="03:12:10:15",
            slot2_last_end_tc="08:00:00:00",
        )
        r_s2 = evaluate_tc_regenerate_slot1_and_ext_lk_release(
            recording_media="Slot 2",
            tc_make="Regenerate",
            slot1_last_end_tc="03:12:10:15",
            slot2_last_end_tc="08:00:00:00",
        )
        r_empty = evaluate_tc_regenerate_slot1_and_ext_lk_release(
            recording_media="Slot 1",
            tc_make="Regenerate",
            rec_frame_rate="29.97p",
            drop_frame=True,
            slot1_last_end_tc=None,
        )
        self.assertEqual(r_s1.regenerate_reference_slot, "Slot 1")
        self.assertEqual(r_s1.next_clip_start_tc, "03:12:10:16")
        self.assertEqual(r_s2.regenerate_reference_slot, "Slot 2")
        self.assertEqual(r_s2.next_clip_start_tc, "08:00:00:01")
        self.assertEqual(r_empty.next_clip_start_tc, "00:00:00;00")

    def test_32_regenerate_simult_recording_reads_exclusively_from_slot1_ignoring_slot2(self) -> None:
        r_sim = evaluate_tc_regenerate_slot1_and_ext_lk_release(
            recording_media="Simult. Recording",
            tc_make="Regenerate",
            requested_tc_run="Free Run",
            rec_frame_rate="25p",
            slot1_last_end_tc="01:20:30:24",
            slot2_last_end_tc="11:45:00:12",
        )
        self.assertEqual(r_sim.regenerate_reference_slot, "Slot 1")
        self.assertTrue(r_sim.slot2_tc_ignored_in_simult)
        self.assertEqual(r_sim.next_clip_start_tc, "01:20:31:00")
        self.assertTrue(r_sim.forced_rec_run_by_regenerate)
        self.assertEqual(r_sim.effective_tc_run, "Rec Run")

    def test_33_regenerate_auto_switch_media_reads_slot1_and_forces_rec_run_over_free_run(self) -> None:
        r_auto = evaluate_tc_regenerate_slot1_and_ext_lk_release(
            recording_media="Auto Switch Media",
            tc_make="Regenerate",
            requested_tc_run="Free Run",
            slot1_last_end_tc="00:05:00:00",
        )
        self.assertEqual(r_auto.regenerate_reference_slot, "Slot 1")
        self.assertTrue(r_auto.forced_rec_run_by_regenerate)
        self.assertEqual(r_auto.effective_tc_run, "Rec Run")

    def test_34_preset_mode_honors_free_run_and_rec_run_in_movie_mode(self) -> None:
        r_free = evaluate_tc_regenerate_slot1_and_ext_lk_release(
            tc_make="Preset", requested_tc_run="Free Run", preset_tc="10:00:00:00"
        )
        r_rec = evaluate_tc_regenerate_slot1_and_ext_lk_release(
            tc_make="Preset", requested_tc_run="Rec Run", preset_tc="10:00:00:00"
        )
        self.assertFalse(r_free.forced_rec_run_by_regenerate)
        self.assertEqual(r_free.effective_tc_run, "Free Run")
        self.assertEqual(r_rec.effective_tc_run, "Rec Run")
        self.assertEqual(r_free.next_clip_start_tc, "10:00:00:00")

    def test_35_vmc_bncm1_ext_lk_engages_under_movie_preset_free_run(self) -> None:
        r = evaluate_tc_regenerate_slot1_and_ext_lk_release(
            capture_mode="Movie",
            tc_make="Preset",
            requested_tc_run="Free Run",
            vmc_bncm1_ltc_present=True,
            prior_ext_lk_locked=False,
        )
        self.assertTrue(r.ext_lk_active_after)
        self.assertFalse(r.ext_lk_released)

    def test_36_ext_lk_immediately_releases_when_switching_tc_make_to_regenerate(self) -> None:
        r = evaluate_tc_regenerate_slot1_and_ext_lk_release(
            capture_mode="Movie",
            tc_make="Regenerate",
            requested_tc_run="Free Run",
            vmc_bncm1_ltc_present=True,
            prior_ext_lk_locked=True,
            tc_make_changed=True,
        )
        self.assertTrue(r.ext_lk_released)
        self.assertFalse(r.ext_lk_active_after)

    def test_37_ext_lk_immediately_releases_when_switching_tc_run_to_rec_run(self) -> None:
        r = evaluate_tc_regenerate_slot1_and_ext_lk_release(
            capture_mode="Movie",
            tc_make="Preset",
            requested_tc_run="Rec Run",
            vmc_bncm1_ltc_present=True,
            prior_ext_lk_locked=True,
            tc_run_changed=True,
        )
        self.assertTrue(r.ext_lk_released)
        self.assertFalse(r.ext_lk_active_after)

    def test_38_sq_locks_out_tc_run_and_hdmi_tc_output_and_releases_ext_lk(self) -> None:
        r = evaluate_tc_regenerate_slot1_and_ext_lk_release(
            capture_mode="S&Q",
            tc_make="Preset",
            requested_tc_run="Free Run",
            vmc_bncm1_ltc_present=True,
            prior_ext_lk_locked=True,
            hdmi_tc_output_requested="On",
        )
        self.assertFalse(r.tc_run_menu_available)
        self.assertFalse(r.hdmi_tc_output_available)
        self.assertEqual(r.effective_hdmi_tc_output, "Off")
        self.assertEqual(r.effective_tc_run, "Rec Run")
        self.assertTrue(r.ext_lk_released)
        self.assertFalse(r.ext_lk_active_after)

    def test_39_hdmi_tc_output_permitted_in_movie_mode_and_invalid_tc_args_rejected(self) -> None:
        r = evaluate_tc_regenerate_slot1_and_ext_lk_release(
            capture_mode="Movie", hdmi_tc_output_requested="On"
        )
        self.assertTrue(r.hdmi_tc_output_available)
        self.assertEqual(r.effective_hdmi_tc_output, "On")
        with self.assertRaises(ValueError):
            evaluate_tc_regenerate_slot1_and_ext_lk_release(capture_mode="Photo")
        with self.assertRaises(ValueError):
            evaluate_tc_regenerate_slot1_and_ext_lk_release(tc_make="External")

    # --- Pillar C: [REC Lamp] Coupled Rear+Top Tally & [Silent Mode] -> [Audio signals] ---

    def test_40_rec_lamp_all_on_lights_front_rear_and_top_in_recording_and_dark_in_standby(self) -> None:
        self.assertEqual(VALID_FX3_REC_LAMP_MODES_P218, ("All On", "Only Front Off", "All Off"))
        r_rec = evaluate_rec_lamp_coupled_tally_and_silent_audio_lock(
            rec_lamp_setting="All On", is_recording=True
        )
        r_stby = evaluate_rec_lamp_coupled_tally_and_silent_audio_lock(
            rec_lamp_setting="All On", is_recording=False
        )
        self.assertEqual(r_rec.appfw_rec_lamp_enum, "REC_LAMP_ALL_LIGHTS_UP")
        self.assertTrue(r_rec.front_tally_led_lit)
        self.assertTrue(r_rec.rear_tally_led_lit)
        self.assertTrue(r_rec.top_rec_button_led_lit)
        self.assertTrue(r_rec.rear_and_top_coupled_equal)
        self.assertFalse(r_stby.front_tally_led_lit)
        self.assertFalse(r_stby.rear_tally_led_lit)
        self.assertFalse(r_stby.top_rec_button_led_lit)

    def test_41_rec_lamp_only_front_off_extinguishes_front_and_keeps_both_rear_and_top_lit(self) -> None:
        r = evaluate_rec_lamp_coupled_tally_and_silent_audio_lock(
            rec_lamp_setting="Only Front Off", is_recording=True
        )
        self.assertEqual(r.appfw_rec_lamp_enum, "REC_LAMP_ONLY_FRONT_OFF")
        self.assertFalse(r.front_tally_led_lit)
        self.assertTrue(r.rear_tally_led_lit)
        self.assertTrue(r.top_rec_button_led_lit)
        self.assertTrue(r.rear_and_top_coupled_equal)

    def test_42_rec_lamp_all_off_extinguishes_all_three_leds_with_lcd_emphasized_rec_frame(self) -> None:
        r = evaluate_rec_lamp_coupled_tally_and_silent_audio_lock(
            rec_lamp_setting="All Off",
            is_recording=True,
            emphasized_rec_display="On",
            hdmi_connected=False,
            hdmi_info_display="Off",
        )
        self.assertEqual(r.appfw_rec_lamp_enum, "REC_LAMP_ALL_LIGHTS_OUT")
        self.assertFalse(r.front_tally_led_lit)
        self.assertFalse(r.rear_tally_led_lit)
        self.assertFalse(r.top_rec_button_led_lit)
        self.assertTrue(r.emphasized_rec_on_lcd)
        self.assertFalse(r.emphasized_rec_on_hdmi)

    def test_43_rec_lamp_all_off_routes_emphasized_rec_red_frame_to_hdmi_when_info_display_on(self) -> None:
        r = evaluate_rec_lamp_coupled_tally_and_silent_audio_lock(
            rec_lamp_setting="All Off",
            is_recording=True,
            emphasized_rec_display="On",
            hdmi_connected=True,
            hdmi_info_display="On",
        )
        self.assertFalse(r.front_tally_led_lit)
        self.assertFalse(r.rear_tally_led_lit)
        self.assertFalse(r.top_rec_button_led_lit)
        self.assertTrue(r.emphasized_rec_on_hdmi)
        self.assertFalse(r.emphasized_rec_on_lcd)

    def test_44_emphasized_rec_display_suppressed_when_not_recording_or_setting_off(self) -> None:
        r_stby = evaluate_rec_lamp_coupled_tally_and_silent_audio_lock(
            rec_lamp_setting="All Off",
            is_recording=False,
            emphasized_rec_display="On",
            hdmi_connected=True,
            hdmi_info_display="On",
        )
        self.assertFalse(r_stby.emphasized_rec_on_hdmi)
        self.assertFalse(r_stby.emphasized_rec_on_lcd)

    def test_45_forbidden_non_fx3_independent_tally_modes_rejected(self) -> None:
        self.assertGreaterEqual(len(FORBIDDEN_NON_FX3_REC_LAMP_MODES_P218), 4)
        for bad_mode in FORBIDDEN_NON_FX3_REC_LAMP_MODES_P218:
            with self.assertRaises(ValueError):
                evaluate_rec_lamp_coupled_tally_and_silent_audio_lock(rec_lamp_setting=bad_mode)

    def test_46_silent_mode_on_hard_locks_audio_signals_to_off_and_silences_beeps(self) -> None:
        for req_audio in ("On", "Shutter Only", "Off"):
            r = evaluate_rec_lamp_coupled_tally_and_silent_audio_lock(
                silent_mode="On", requested_audio_signals=req_audio
            )
            self.assertTrue(r.audio_signals_locked_by_silent_mode)
            self.assertEqual(r.effective_audio_signals, "Off")
            self.assertFalse(r.af_and_selftimer_beeps_emitted)

    def test_47_silent_mode_off_honors_audio_signals_on_off_and_on_shutter_only(self) -> None:
        r_on = evaluate_rec_lamp_coupled_tally_and_silent_audio_lock(
            silent_mode="Off", requested_audio_signals="On"
        )
        r_sh = evaluate_rec_lamp_coupled_tally_and_silent_audio_lock(
            silent_mode="Off", requested_audio_signals="Shutter Only"
        )
        self.assertFalse(r_on.audio_signals_locked_by_silent_mode)
        self.assertEqual(r_on.effective_audio_signals, "On")
        self.assertTrue(r_on.af_and_selftimer_beeps_emitted)
        self.assertEqual(r_sh.effective_audio_signals, "Shutter Only")
        self.assertFalse(r_sh.af_and_selftimer_beeps_emitted)

    def test_48_rec_lamp_evaluator_rejects_invalid_enum_inputs(self) -> None:
        with self.assertRaises(ValueError):
            evaluate_rec_lamp_coupled_tally_and_silent_audio_lock(silent_mode="Auto")
        with self.assertRaises(ValueError):
            evaluate_rec_lamp_coupled_tally_and_silent_audio_lock(requested_audio_signals="Loud")

    # --- Pillar D: Zero-Write Firewall, 12-TP Matrix, Exports & CLI `45/45` ---

    def test_49_write_guard_blocks_persistent_emmc_spinor_backup_ufu_and_cpapp(self) -> None:
        protected_targets = (
            "p2:/setting/Backup.bin",
            "p5:/wbi/hibdrv.img",
            "p8:/cpapp-b.bin",
            "p12:/cert/RQ_LIC.DAT",
            "p18:/lens/LENSFILE.BIN",
            "/dev/cnflasha2",
            "/dev/nflasha30",
            "spi_nor:0x000000",
            "/mnt/sd/BODYDATA.DAT",
        )
        for tgt in protected_targets:
            res = evaluate_phase218_write_guard(tgt, operation="WRITE")
            self.assertFalse(res.allowed, msg=f"Must block {tgt}")
            self.assertFalse(res.persistent_emmc_writes_authorized)
            self.assertFalse(res.spi_nor_write_authorized)
            self.assertFalse(res.el3_payload_transmit_authorized)
            self.assertEqual(res.physical_usb_packets_emitted, 0)

    def test_50_write_guard_allows_rdonly_reads_and_volatile_tmp_overlays_with_zero_auth(self) -> None:
        r_read = evaluate_phase218_write_guard("p2:/setting/Backup.bin", operation="READ")
        r_tmp = evaluate_phase218_write_guard(
            f"{VOLATILE_WAVE29_OVERLAY_DIR_P218}/wave29_state.json", operation="WRITE"
        )
        r_ram = evaluate_phase218_write_guard("ram://wave29_shadow", operation="WRITE")
        for g in (r_read, r_tmp, r_ram):
            self.assertTrue(g.allowed)
            self.assertFalse(g.persistent_emmc_writes_authorized)
            self.assertFalse(g.spi_nor_write_authorized)
            self.assertFalse(g.el3_payload_transmit_authorized)

    def test_51_write_guard_fail_closed_on_unknown_non_volatile_paths(self) -> None:
        g = evaluate_phase218_write_guard("/etc/persistent_override.conf", operation="WRITE")
        self.assertFalse(g.allowed)

    def test_52_compat_matrix_12_touchpoints_p218_01_to_12_cover_all_four_bridge_classes(self) -> None:
        mat = build_phase218_compat_matrix()
        self.assertEqual(mat.total_touchpoints, 12)
        self.assertTrue(mat.all_classes_valid)
        ids = tuple(e.touchpoint_id for e in mat.entries)
        self.assertEqual(ids, tuple(f"P218-{i:02d}" for i in range(1, 13)))
        self.assertEqual(set(mat.class_counts.keys()), set(VALID_BRIDGE_CLASSES))
        for cls in VALID_BRIDGE_CLASSES:
            self.assertGreaterEqual(mat.class_counts[cls], 1)

    def test_53_package_init_exports_all_phase218_public_symbols(self) -> None:
        expected_symbols = (
            "PHASE_218_SCHEMA",
            "AUDITOR_INDEX_P218",
            "analyze_realhw_filesettings_shotmark_tcregen_and_reclamp",
            "realhw_filesettings_shotmark_tcregen_and_reclamp_report_to_dict",
            "validate_fx3_title_name_settings",
            "evaluate_file_settings_and_sdhc_lock",
            "evaluate_shotmark_xml_jump_and_ftp_filter",
            "advance_smpte_tc_one_frame",
            "evaluate_tc_regenerate_slot1_and_ext_lk_release",
            "evaluate_rec_lamp_coupled_tally_and_silent_audio_lock",
            "evaluate_phase218_write_guard",
            "build_phase218_compat_matrix",
        )
        for sym in expected_symbols:
            self.assertIn(sym, fx3_firmware_lab.__all__)
            self.assertTrue(hasattr(fx3_firmware_lab, sym))

    def test_54_cli_subcommand_donor_and_clean_room_exit_zero_and_emit_valid_json(self) -> None:
        for argv in (
            ["audit-realhw-filesettings-shotmark-tcregen-reclamp", "--json"],
            ["audit-realhw-filesettings-shotmark-tcregen-reclamp", "--clean-room", "--json"],
        ):
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = cli_main(argv)
            self.assertEqual(rc, 0)
            parsed = json.loads(buf.getvalue())
            self.assertTrue(parsed["all_checks_passed"])
            self.assertEqual(parsed["auditor_index"], "45/45")

    def test_55_run_audit_all_integrates_45th_milestone_auditor_45_of_45(self) -> None:
        summary = run_audit_all(clean_room=True)
        self.assertTrue(summary["all_checks_passed"])
        audit_keys = [k for k in summary.keys() if k.endswith("_audit")]
        self.assertEqual(len(audit_keys), 45)
        self.assertIn("realhw_filesettings_shotmark_tcregen_and_reclamp_audit", summary)
        p218_entry = summary["realhw_filesettings_shotmark_tcregen_and_reclamp_audit"]
        self.assertIsInstance(p218_entry, dict)
        self.assertEqual(p218_entry["auditor_index"], "45/45")
        self.assertTrue(p218_entry["all_checks_passed"])


if __name__ == "__main__":
    unittest.main()
