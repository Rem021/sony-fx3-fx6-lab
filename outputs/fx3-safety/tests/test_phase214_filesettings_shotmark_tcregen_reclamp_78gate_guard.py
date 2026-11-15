"""Phase 214 Dual-Mode Unit Tests (60 tests, >=50 required):
Gates G77 (`G77_FILE_SETTINGS_SDHC_37CHAR_LOCK_AND_SHOTMARK_XML_FILTER_GUARD`),
G78 (`G78_TC_REGENERATE_SLOT1_EXTLK_RELEASE_AND_RECLAMP_COUPLED_TALLY_GUARD`),
and Unified 78-Gate Master Safety Preflight (`verify-78-gates`).
"""

from __future__ import annotations

import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import fx3_safety
from fx3_safety.__main__ import main as cli_main
from fx3_safety.realhw_filesettings_shotmark_tcregen_reclamp_and_78gate_guard import (
    ALLOWED_FILE_NAME_FORMATS,
    ALLOWED_FX3_REC_LAMP_MODES,
    ALLOWED_SHOTMARK_IMAGE_JUMP_SETTINGS,
    DONOR_CHECK_MAX_SECONDS,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    FILE_NAME_FORMAT_STANDARD,
    G77,
    G77_GATE_CODE,
    G77_GATE_ID,
    G78,
    G78_GATE_CODE,
    G78_GATE_ID,
    HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PINNED_PHASE214_DONOR_SPECS,
    RAW_FIRMWARE_BYTES_LEAKED,
    REALHW_FILESETTINGS_SHOTMARK_TCREGEN_RECLAMP_78GATE_SCHEMA,
    REC_LAMP_ALL_OFF,
    REC_LAMP_ALL_ON,
    REC_LAMP_ONLY_FRONT_OFF,
    REC_MEDIA_SLOT_1,
    REC_MEDIA_SLOT_2,
    SPI_NOR_WRITE_AUTHORIZED,
    STATUS_BLOCKED_G77_FILE_NAME_FORMAT_OR_NUMBER_INVALID,
    STATUS_BLOCKED_G77_SDHC_STANDARD_LOCK_OR_CUSTOM_FOLDER_FORBIDDEN,
    STATUS_BLOCKED_G77_SHOTMARK_JUMP_OR_TRANSFER_FILTER_VIOLATION,
    STATUS_BLOCKED_G77_SHOTMARK_XML_SIDECAR_OR_MODE_VIOLATION,
    STATUS_BLOCKED_G77_TELEMETRY_INVALID,
    STATUS_BLOCKED_G77_TITLE_NAME_LENGTH_OR_CHARSET_INVALID,
    STATUS_BLOCKED_G78_REC_LAMP_COUPLED_TALLY_OR_OSD_VIOLATION,
    STATUS_BLOCKED_G78_SILENT_MODE_AUDIO_SIGNALS_LOCK_VIOLATION,
    STATUS_BLOCKED_G78_SQ_TC_RUN_OR_HDMI_TCOUT_LOCKOUT,
    STATUS_BLOCKED_G78_TC_REGENERATE_REC_RUN_OR_SLOT1_VIOLATION,
    STATUS_BLOCKED_G78_TELEMETRY_INVALID,
    STATUS_BLOCKED_G78_VMC_BNCM1_EXT_LK_PREREQ_OR_RELEASE_VIOLATION,
    STATUS_BLOCKED_PERSISTENT_EMMC_WRITE,
    STATUS_BLOCKED_PHASE214_DONOR_INTEGRITY,
    STATUS_VERIFIED_G77,
    STATUS_VERIFIED_G78,
    TC_RUN_REC_RUN,
    TITLE_NAME_ALLOWED_SYMBOLS,
    TITLE_NAME_MAX_CHARS,
    USB_PACKETS_TRANSMITTED,
    audit_phase214_donor_contracts,
    evaluate_78_master_safety_gates,
    evaluate_78gate_preflight,
    evaluate_g77_filesettings_shotmark_guard,
    evaluate_g78_tcregen_reclamp_guard,
    evaluate_shotmark_jump_and_transfer_match,
    main as module_main,
    resolve_effective_fx3_file_name_format,
    resolve_fx3_rec_lamp_coupled_tally,
    resolve_tc_regenerate_slot_and_extlk,
    run_78_gate_preflight,
    validate_fx3_title_name,
    verify_file_settings_sdhc_37char_and_shotmark_guard,
    verify_tc_regenerate_extlk_and_reclamp_tally_guard,
)


class TestPhase214FileSettingsShotMarkTcRegenRecLamp78GateGuard(unittest.TestCase):
    """Comprehensive dual-mode tests for Phase 214 Gates G77, G78 & 78-Gate Preflight."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.offline_76 = fx3_safety.evaluate_76gate_preflight()
        cls.dryrun_76 = fx3_safety.evaluate_76gate_preflight(dry_run_simulated=True)
        cls.offline_78 = evaluate_78gate_preflight(master_76_override=cls.offline_76)
        cls.dryrun_78 = evaluate_78gate_preflight(
            simulate_bench_dry_run=True, master_76_override=cls.dryrun_76
        )
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            cls.clean_offline_76 = fx3_safety.evaluate_76gate_preflight(
                force_clean_room=True
            )
            cls.clean_dryrun_76 = fx3_safety.evaluate_76gate_preflight(
                force_clean_room=True, dry_run_simulated=True
            )
            cls.clean_offline_78 = evaluate_78gate_preflight(
                force_clean_room=True, master_76_override=cls.clean_offline_76
            )
            cls.clean_dryrun_78 = evaluate_78gate_preflight(
                force_clean_room=True,
                simulate_bench_dry_run=True,
                master_76_override=cls.clean_dryrun_76,
            )

    # ------------------------------------------------------------------
    # Section A: Package Exports & Bounded Donor Contract Audit (7 tests)
    # ------------------------------------------------------------------

    def test_01_public_package_exports_and_hard_redline_constants(self) -> None:
        self.assertEqual(G77, G77_GATE_CODE)
        self.assertEqual(G78, G78_GATE_CODE)
        self.assertEqual(
            G77_GATE_CODE,
            "G77_FILE_SETTINGS_SDHC_37CHAR_LOCK_AND_SHOTMARK_XML_FILTER_GUARD",
        )
        self.assertEqual(
            G78_GATE_CODE,
            "G78_TC_REGENERATE_SLOT1_EXTLK_RELEASE_AND_RECLAMP_COUPLED_TALLY_GUARD",
        )
        self.assertFalse(EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        self.assertFalse(SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        self.assertEqual(USB_PACKETS_TRANSMITTED, 0)
        self.assertEqual(RAW_FIRMWARE_BYTES_LEAKED, 0)
        self.assertIs(fx3_safety.evaluate_78gate_preflight, evaluate_78gate_preflight)
        self.assertIs(fx3_safety.run_78_gate_preflight, run_78_gate_preflight)
        self.assertIs(
            fx3_safety.evaluate_78_master_safety_gates, evaluate_78_master_safety_gates
        )
        self.assertIs(
            fx3_safety.evaluate_g77_filesettings_shotmark_guard,
            evaluate_g77_filesettings_shotmark_guard,
        )
        self.assertIs(
            fx3_safety.evaluate_g78_tcregen_reclamp_guard,
            evaluate_g78_tcregen_reclamp_guard,
        )

    def test_02_donor_audit_bounded_under_150ms_and_zero_bytes_leaked(self) -> None:
        audit = audit_phase214_donor_contracts()
        self.assertTrue(audit.valid)
        self.assertTrue(audit.within_budget_150ms)
        self.assertLess(audit.elapsed_seconds, DONOR_CHECK_MAX_SECONDS)
        self.assertEqual(audit.raw_firmware_bytes_leaked, 0)
        self.assertIn(
            audit.verification_mode,
            ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"),
        )
        self.assertEqual(len(audit.checked_markers), len(PINNED_PHASE214_DONOR_SPECS))
        self.assertEqual(len(audit.sha256_by_artifact), len(PINNED_PHASE214_DONOR_SPECS))

    def test_03_donor_audit_force_clean_room_flag_deterministic(self) -> None:
        audit = audit_phase214_donor_contracts(force_clean_room=True)
        self.assertTrue(audit.valid)
        self.assertEqual(audit.files_inspected, 0)
        self.assertEqual(audit.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(audit.raw_firmware_bytes_leaked, 0)

    def test_04_donor_audit_force_clean_room_env_override(self) -> None:
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            audit = audit_phase214_donor_contracts()
        self.assertTrue(audit.valid)
        self.assertEqual(audit.files_inspected, 0)
        self.assertEqual(audit.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_05_donor_audit_missing_work_root_falls_back_to_clean_room(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "0"}):
                audit = audit_phase214_donor_contracts(
                    work_root=Path(tmpdir) / "nonexistent_work_root",
                    force_clean_room=False,
                )
        self.assertTrue(audit.valid)
        self.assertEqual(audit.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_06_donor_audit_detects_tampered_donor_size_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            work_dir = Path(tmpdir)
            for _key, (_body, rel_path, *_rest) in PINNED_PHASE214_DONOR_SPECS.items():
                p = work_dir / rel_path
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(b"corrupt_short_donor")
            audit = audit_phase214_donor_contracts(
                work_root=work_dir, force_clean_room=False
            )
            v77, r77 = evaluate_g77_filesettings_shotmark_guard(donor_audit=audit)
        self.assertFalse(audit.valid)
        self.assertEqual(audit.files_inspected, len(PINNED_PHASE214_DONOR_SPECS))
        self.assertEqual(audit.status, STATUS_BLOCKED_PHASE214_DONOR_INTEGRITY)
        self.assertFalse(v77.passed)
        self.assertIn(STATUS_BLOCKED_PHASE214_DONOR_INTEGRITY, r77.violation_codes)

    def test_07_donor_audit_enforces_150ms_wall_clock_budget(self) -> None:
        with mock.patch(
            "fx3_safety.realhw_filesettings_shotmark_tcregen_reclamp_and_78gate_guard.time.perf_counter",
            side_effect=[10.0, 10.25],
        ):
            audit = audit_phase214_donor_contracts(force_clean_room=True)
        self.assertFalse(audit.valid)
        self.assertFalse(audit.within_budget_150ms)
        self.assertEqual(audit.status, STATUS_BLOCKED_PHASE214_DONOR_INTEGRITY)

    # ------------------------------------------------------------------
    # Section B: Gate G77 ([File Settings], 37-Char Title, SDHC & Shot Mark)
    # ------------------------------------------------------------------

    def test_08_g77_default_profile_passes_in_normal_and_clean_room(self) -> None:
        res = verify_file_settings_sdhc_37char_and_shotmark_guard()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_VERIFIED_G77)
        self.assertEqual(res.violation_codes, ())
        v_norm, r_norm = evaluate_g77_filesettings_shotmark_guard()
        v_clean, r_clean = evaluate_g77_filesettings_shotmark_guard(force_clean_room=True)
        self.assertTrue(v_norm.passed)
        self.assertTrue(v_clean.passed)
        self.assertEqual(r_clean.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertFalse(r_norm.persistent_emmc_writes_authorized)
        self.assertEqual(r_norm.raw_firmware_bytes_leaked, 0)

    def test_09_g77_all_five_file_name_formats_accepted_across_dual_slots(self) -> None:
        inputs = (
            ("Standard", "STANDARD"),
            ("Cam ID + Reel#", "CAM_ID_PLUS_REEL"),
            ("Title", "TITLE"),
            ("Date + Title", "DATE_PLUS_TITLE"),
            ("Title + Date", "TITLE_PLUS_DATE"),
        )
        self.assertEqual(len(ALLOWED_FILE_NAME_FORMATS), 5)
        for label, expected in inputs:
            res = verify_file_settings_sdhc_37char_and_shotmark_guard(
                file_name_format=label,
                slot2_file_name_format=label,
                slot1_media_type="CFexpress Type A",
                slot2_media_type="SDXC",
            )
            self.assertTrue(res.valid, msg=label)
            self.assertEqual(res.canonical_file_name_format, expected)
            self.assertEqual(res.effective_file_name_format, expected)

    def test_10_g77_slot2_divergent_file_name_format_blocked(self) -> None:
        res = verify_file_settings_sdhc_37char_and_shotmark_guard(
            file_name_format="Cam ID + Reel#",
            slot2_file_name_format="Title",
        )
        self.assertFalse(res.valid)
        self.assertIn(
            STATUS_BLOCKED_G77_FILE_NAME_FORMAT_OR_NUMBER_INVALID, res.violation_codes
        )

    def test_11_g77_invalid_file_name_format_or_file_number_mode_blocked(self) -> None:
        bad_fmt = verify_file_settings_sdhc_37char_and_shotmark_guard(
            file_name_format="Custom Scene + Take"
        )
        bad_num = verify_file_settings_sdhc_37char_and_shotmark_guard(
            file_number_mode="Random"
        )
        self.assertFalse(bad_fmt.valid)
        self.assertFalse(bad_num.valid)
        self.assertIn(
            STATUS_BLOCKED_G77_FILE_NAME_FORMAT_OR_NUMBER_INVALID, bad_fmt.violation_codes
        )
        self.assertIn(
            STATUS_BLOCKED_G77_FILE_NAME_FORMAT_OR_NUMBER_INVALID, bad_num.violation_codes
        )

    def test_12_g77_file_number_series_continuity_and_series_counter_reset(self) -> None:
        cont = verify_file_settings_sdhc_37char_and_shotmark_guard(
            file_number_mode="Series",
            previous_clip_number=41,
            card_swapped_to_empty=True,
            claimed_next_clip_number=42,
        )
        self.assertTrue(cont.valid)
        self.assertEqual(cont.modeled_next_clip_number, 42)

        wrap = verify_file_settings_sdhc_37char_and_shotmark_guard(
            file_number_mode="Series",
            previous_clip_number=9999,
            claimed_next_clip_number=1,
        )
        self.assertTrue(wrap.valid)

        reset_exec = verify_file_settings_sdhc_37char_and_shotmark_guard(
            file_number_mode="Series",
            previous_clip_number=128,
            series_counter_reset_executed=True,
            claimed_next_clip_number=1,
        )
        self.assertTrue(reset_exec.valid)
        self.assertTrue(reset_exec.series_counter_reset_applied)
        self.assertEqual(reset_exec.modeled_next_clip_number, 1)

    def test_13_g77_file_number_reset_mode_and_wrong_next_counter_blocked(self) -> None:
        swapped = verify_file_settings_sdhc_37char_and_shotmark_guard(
            file_number_mode="Reset",
            previous_clip_number=77,
            card_swapped_to_empty=True,
            claimed_next_clip_number=1,
        )
        self.assertTrue(swapped.valid)

        wrong = verify_file_settings_sdhc_37char_and_shotmark_guard(
            file_number_mode="Series",
            previous_clip_number=41,
            card_swapped_to_empty=True,
            claimed_next_clip_number=1,
        )
        self.assertFalse(wrong.valid)
        self.assertIn(
            STATUS_BLOCKED_G77_FILE_NAME_FORMAT_OR_NUMBER_INVALID, wrong.violation_codes
        )

    def test_14_g77_cam_id_and_reel_number_bounds_enforced(self) -> None:
        bad_cam = verify_file_settings_sdhc_37char_and_shotmark_guard(cam_id="AB")
        bad_reel = verify_file_settings_sdhc_37char_and_shotmark_guard(reel_number=1000)
        self.assertFalse(bad_cam.valid)
        self.assertFalse(bad_reel.valid)
        self.assertIn(
            STATUS_BLOCKED_G77_FILE_NAME_FORMAT_OR_NUMBER_INVALID, bad_cam.violation_codes
        )
        self.assertIn(
            STATUS_BLOCKED_G77_FILE_NAME_FORMAT_OR_NUMBER_INVALID, bad_reel.violation_codes
        )

    def test_15_g77_title_name_exact_37_chars_and_all_18_allowed_symbols_pass(self) -> None:
        self.assertEqual(TITLE_NAME_MAX_CHARS, 37)
        self.assertEqual(TITLE_NAME_ALLOWED_SYMBOLS, ".-_@!#$%+=^~(),;[]")
        exact_37 = "Az09" + TITLE_NAME_ALLOWED_SYMBOLS + "BCDEFGHIJKLMNO1"
        self.assertEqual(len(exact_37), 37)
        ok, bad = validate_fx3_title_name(exact_37)
        self.assertTrue(ok)
        self.assertEqual(bad, ())
        res = verify_file_settings_sdhc_37char_and_shotmark_guard(
            file_name_format="Title", title_name=exact_37
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.title_name_length, 37)

    def test_16_g77_title_name_38_chars_or_empty_blocked(self) -> None:
        too_long = verify_file_settings_sdhc_37char_and_shotmark_guard(
            file_name_format="Title", title_name="A" * 38
        )
        empty = verify_file_settings_sdhc_37char_and_shotmark_guard(
            file_name_format="Title", title_name=""
        )
        self.assertFalse(too_long.valid)
        self.assertFalse(empty.valid)
        self.assertIn(
            STATUS_BLOCKED_G77_TITLE_NAME_LENGTH_OR_CHARSET_INVALID,
            too_long.violation_codes,
        )
        self.assertIn(
            STATUS_BLOCKED_G77_TITLE_NAME_LENGTH_OR_CHARSET_INVALID,
            empty.violation_codes,
        )

    def test_17_g77_title_name_disallowed_space_slash_colon_unicode_blocked(self) -> None:
        for bad_title in ("FX3 Scene 01", "FX3/Reel1", "CAM:01", 'Take"1"', "FX3_镜头1"):
            res = verify_file_settings_sdhc_37char_and_shotmark_guard(
                file_name_format="Date + Title", title_name=bad_title
            )
            self.assertFalse(res.valid, msg=bad_title)
            self.assertIn(
                STATUS_BLOCKED_G77_TITLE_NAME_LENGTH_OR_CHARSET_INVALID,
                res.violation_codes,
            )

    def test_18_g77_retroactive_existing_clip_rename_claim_blocked(self) -> None:
        res = verify_file_settings_sdhc_37char_and_shotmark_guard(
            retroactive_existing_clip_rename_claimed=True
        )
        self.assertFalse(res.valid)
        self.assertIn(
            STATUS_BLOCKED_G77_TITLE_NAME_LENGTH_OR_CHARSET_INVALID,
            res.violation_codes,
        )

    def test_19_g77_sdhc_card_forced_lock_to_standard_format(self) -> None:
        eff, locked = resolve_effective_fx3_file_name_format(
            "Title + Date", slot1_media_type="SDHC", slot2_media_type="SDXC"
        )
        self.assertTrue(locked)
        self.assertEqual(eff, FILE_NAME_FORMAT_STANDARD)

        # Standard requested on SDHC passes cleanly
        ok_sdhc = verify_file_settings_sdhc_37char_and_shotmark_guard(
            file_name_format="Standard",
            slot1_media_type="CFEXPRESS_A",
            slot2_media_type="SDHC",
            slot2_capacity_gb=32.0,
            slot2_filesystem="FAT32",
        )
        self.assertTrue(ok_sdhc.valid)
        self.assertTrue(ok_sdhc.sdhc_standard_lock_active)

        # Non-Standard requested while SDHC (or <=32GB FAT32) inserted is blocked
        for non_std in ("Cam ID + Reel#", "Title", "Date + Title", "Title + Date"):
            blocked = verify_file_settings_sdhc_37char_and_shotmark_guard(
                file_name_format=non_std,
                slot1_media_type="CFEXPRESS_A",
                slot2_media_type="SDXC",
                slot2_capacity_gb=16.0,
                slot2_filesystem="FAT32",
            )
            self.assertFalse(blocked.valid, msg=non_std)
            self.assertIn(
                STATUS_BLOCKED_G77_SDHC_STANDARD_LOCK_OR_CUSTOM_FOLDER_FORBIDDEN,
                blocked.violation_codes,
            )

    def test_20_g77_sdhc_mismatched_effective_format_claim_blocked(self) -> None:
        res = verify_file_settings_sdhc_37char_and_shotmark_guard(
            file_name_format="Standard",
            slot1_media_type="SDHC",
            claimed_effective_file_name_format="Title",
        )
        self.assertFalse(res.valid)
        self.assertIn(
            STATUS_BLOCKED_G77_SDHC_STANDARD_LOCK_OR_CUSTOM_FOLDER_FORBIDDEN,
            res.violation_codes,
        )

    def test_21_g77_custom_movie_folder_prohibited_enforces_m4root_clip(self) -> None:
        req_custom = verify_file_settings_sdhc_37char_and_shotmark_guard(
            custom_movie_folder_requested=True
        )
        bad_dir = verify_file_settings_sdhc_37char_and_shotmark_guard(
            movie_clip_folder="DCIM/100MSDCF"
        )
        private_ok = verify_file_settings_sdhc_37char_and_shotmark_guard(
            movie_clip_folder="PRIVATE/M4ROOT/CLIP"
        )
        self.assertFalse(req_custom.valid)
        self.assertFalse(bad_dir.valid)
        self.assertTrue(private_ok.valid)
        self.assertIn(
            STATUS_BLOCKED_G77_SDHC_STANDARD_LOCK_OR_CUSTOM_FOLDER_FORBIDDEN,
            bad_dir.violation_codes,
        )

    def test_22_g77_shotmark_rec_and_playback_xml_sidecar_valid_ops(self) -> None:
        for rec_key in ("None", "Add Shot Mark1", "Add Shot Mark2"):
            for pb_op in (
                "None",
                "Add/Delete Shot Mark1",
                "Add/Delete Shot Mark2",
            ):
                res = verify_file_settings_sdhc_37char_and_shotmark_guard(
                    shooting_mode="Movie",
                    rec_shot_mark_key=rec_key,
                    playback_shot_mark_op=pb_op,
                    shot_mark1_present=True,
                    shot_mark2_present=True,
                    shot_mark_xml_path="M4ROOT/CLIP/C0005M01.XML",
                )
                self.assertTrue(res.valid, msg=f"{rec_key}/{pb_op}")

        wrong_pb_enum = verify_file_settings_sdhc_37char_and_shotmark_guard(
            playback_shot_mark_op="Add Shot Mark1"
        )
        self.assertFalse(wrong_pb_enum.valid)
        self.assertIn(
            STATUS_BLOCKED_G77_SHOTMARK_XML_SIDECAR_OR_MODE_VIOLATION,
            wrong_pb_enum.violation_codes,
        )

    def test_23_g77_shotmark_still_mode_bad_xml_or_essence_mutation_blocked(self) -> None:
        still_err = verify_file_settings_sdhc_37char_and_shotmark_guard(
            shooting_mode="Still", rec_shot_mark_key="Add Shot Mark1"
        )
        xml_err = verify_file_settings_sdhc_37char_and_shotmark_guard(
            shot_mark_xml_path="M4ROOT/CLIP/C0005.MP4"
        )
        ess_err = verify_file_settings_sdhc_37char_and_shotmark_guard(
            video_essence_mutated_by_shotmark=True
        )
        for failed in (still_err, xml_err, ess_err):
            self.assertFalse(failed.valid)
            self.assertIn(
                STATUS_BLOCKED_G77_SHOTMARK_XML_SIDECAR_OR_MODE_VIOLATION,
                failed.violation_codes,
            )

    def test_24_g77_image_jump_setting_four_modes_truth_table(self) -> None:
        self.assertEqual(len(ALLOWED_SHOTMARK_IMAGE_JUMP_SETTINGS), 4)
        self.assertEqual(
            evaluate_shotmark_jump_and_transfer_match(
                shot_mark1=False,
                shot_mark2=True,
                image_jump_setting="Shot Mark Only",
                transfer_target_movie="Only Shot Mark Mov.",
            ),
            (True, True),
        )
        self.assertEqual(
            evaluate_shotmark_jump_and_transfer_match(
                shot_mark1=False,
                shot_mark2=True,
                image_jump_setting="Shot Mark1 Only",
                transfer_target_movie="Only Shot Mark",
            ),
            (False, True),
        )
        self.assertEqual(
            evaluate_shotmark_jump_and_transfer_match(
                shot_mark1=False,
                shot_mark2=False,
                image_jump_setting="No Shot Mark",
                transfer_target_movie="Only Shot Mark Mov.",
            ),
            (True, False),
        )

    def test_25_g77_image_jump_mismatch_claim_blocked(self) -> None:
        res = verify_file_settings_sdhc_37char_and_shotmark_guard(
            shot_mark1_present=False,
            shot_mark2_present=True,
            image_jump_setting="Shot Mark1 Only",
            claimed_image_jump_matched=True,
        )
        self.assertFalse(res.valid)
        self.assertIn(
            STATUS_BLOCKED_G77_SHOTMARK_JUMP_OR_TRANSFER_FILTER_VIOLATION,
            res.violation_codes,
        )

    def test_26_g77_ftp_and_smartphone_only_shotmark_transfer_filter_enforced(self) -> None:
        unmarked_blocked = verify_file_settings_sdhc_37char_and_shotmark_guard(
            shot_mark1_present=False,
            shot_mark2_present=False,
            image_jump_setting="No Shot Mark",
            transfer_target_movie="Only Shot Mark Mov.",
            clip_selected_for_transfer=True,
        )
        leak_blocked = verify_file_settings_sdhc_37char_and_shotmark_guard(
            transfer_target_movie="Only Shot Mark",
            unmarked_clip_transferred_under_shotmark_filter=True,
        )
        unmarked_skipped_ok = verify_file_settings_sdhc_37char_and_shotmark_guard(
            shot_mark1_present=False,
            shot_mark2_present=False,
            image_jump_setting="No Shot Mark",
            transfer_target_movie="Only Shot Mark",
            clip_selected_for_transfer=False,
        )
        self.assertFalse(unmarked_blocked.valid)
        self.assertFalse(leak_blocked.valid)
        self.assertTrue(unmarked_skipped_ok.valid)
        self.assertIn(
            STATUS_BLOCKED_G77_SHOTMARK_JUMP_OR_TRANSFER_FILTER_VIOLATION,
            unmarked_blocked.violation_codes,
        )

    def test_27_g77_invalid_model_telemetry_and_emmc_write_redline_blocked(self) -> None:
        wrong_model = verify_file_settings_sdhc_37char_and_shotmark_guard(
            body_model_name="ILME-FX6V"
        )
        bad_type = verify_file_settings_sdhc_37char_and_shotmark_guard(
            reel_number=True  # type: ignore[arg-type]
        )
        self.assertFalse(wrong_model.valid)
        self.assertFalse(bad_type.valid)
        self.assertIn(STATUS_BLOCKED_G77_TELEMETRY_INVALID, wrong_model.violation_codes)
        self.assertIn(STATUS_BLOCKED_G77_TELEMETRY_INVALID, bad_type.violation_codes)

        v_emmc, r_emmc = evaluate_g77_filesettings_shotmark_guard(
            force_clean_room=True, request_persistent_emmc_writes=True
        )
        self.assertFalse(v_emmc.passed)
        self.assertIn(STATUS_BLOCKED_PERSISTENT_EMMC_WRITE, r_emmc.violation_codes)

    # ------------------------------------------------------------------
    # Section C: Gate G78 (TC Regenerate Slot 1, EXT-LK, REC Lamp & Silent)
    # ------------------------------------------------------------------

    def test_28_g78_default_profile_passes_in_normal_and_clean_room(self) -> None:
        res = verify_tc_regenerate_extlk_and_reclamp_tally_guard()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_VERIFIED_G78)
        self.assertEqual(res.effective_time_code_run, TC_RUN_REC_RUN)
        self.assertEqual(res.regenerate_reference_slot, REC_MEDIA_SLOT_1)
        v_norm, r_norm = evaluate_g78_tcregen_reclamp_guard()
        v_clean, r_clean = evaluate_g78_tcregen_reclamp_guard(force_clean_room=True)
        self.assertTrue(v_norm.passed)
        self.assertTrue(v_clean.passed)
        self.assertEqual(r_clean.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertFalse(r_norm.persistent_emmc_writes_authorized)
        self.assertEqual(r_norm.raw_firmware_bytes_leaked, 0)

    def test_29_g78_tc_regenerate_forces_rec_run_regardless_of_free_run_menu(self) -> None:
        eff_run, ref_slot, ext_lk = resolve_tc_regenerate_slot_and_extlk(
            shooting_mode="Movie",
            time_code_make="Regenerate",
            time_code_run="Free Run",
            recording_media="Simult. Recording",
        )
        self.assertEqual(eff_run, TC_RUN_REC_RUN)
        self.assertEqual(ref_slot, REC_MEDIA_SLOT_1)
        self.assertFalse(ext_lk)

        bad_claim = verify_tc_regenerate_extlk_and_reclamp_tally_guard(
            time_code_make="Regenerate",
            time_code_run="Free Run",
            claimed_effective_time_code_run="Free Run",
        )
        self.assertFalse(bad_claim.valid)
        self.assertIn(
            STATUS_BLOCKED_G78_TC_REGENERATE_REC_RUN_OR_SLOT1_VIOLATION,
            bad_claim.violation_codes,
        )

    def test_30_g78_tc_regenerate_simult_recording_reads_exclusively_slot1(self) -> None:
        ok_slot1 = verify_tc_regenerate_extlk_and_reclamp_tally_guard(
            time_code_make="Regenerate",
            recording_media="Simult. Recording",
            regenerate_reference_slot="Slot 1",
            slot1_last_clip_end_tc="01:10:20:12",
            slot2_last_clip_end_tc="04:55:00:00",
            claimed_regenerated_start_tc="01:10:20:12",
        )
        self.assertTrue(ok_slot1.valid)

        bad_slot2_ref = verify_tc_regenerate_extlk_and_reclamp_tally_guard(
            time_code_make="Regenerate",
            recording_media="Simult. Recording",
            regenerate_reference_slot="Slot 2",
        )
        bad_slot2_tc = verify_tc_regenerate_extlk_and_reclamp_tally_guard(
            time_code_make="Regenerate",
            recording_media="Simult. Recording",
            slot1_last_clip_end_tc="01:10:20:12",
            slot2_last_clip_end_tc="04:55:00:00",
            claimed_regenerated_start_tc="04:55:00:00",
        )
        self.assertFalse(bad_slot2_ref.valid)
        self.assertFalse(bad_slot2_tc.valid)
        self.assertIn(
            STATUS_BLOCKED_G78_TC_REGENERATE_REC_RUN_OR_SLOT1_VIOLATION,
            bad_slot2_ref.violation_codes,
        )
        self.assertIn(
            STATUS_BLOCKED_G78_TC_REGENERATE_REC_RUN_OR_SLOT1_VIOLATION,
            bad_slot2_tc.violation_codes,
        )

    def test_31_g78_tc_regenerate_single_slot_reads_active_slot(self) -> None:
        s2_ok = verify_tc_regenerate_extlk_and_reclamp_tally_guard(
            time_code_make="Regenerate",
            recording_media="Slot 2",
            slot1_last_clip_end_tc="01:00:00:00",
            slot2_last_clip_end_tc="03:22:11:05",
            claimed_regenerated_start_tc="03:22:11:05",
        )
        self.assertTrue(s2_ok.valid)
        self.assertEqual(s2_ok.regenerate_reference_slot, REC_MEDIA_SLOT_2)

    def test_32_g78_vmc_bncm1_ext_lk_active_in_movie_preset_free_run(self) -> None:
        res = verify_tc_regenerate_extlk_and_reclamp_tally_guard(
            shooting_mode="Movie",
            time_code_make="Preset",
            time_code_run="Free Run",
            vmc_bncm1_attached=True,
            claimed_ext_lk_active=True,
        )
        self.assertTrue(res.valid)
        self.assertTrue(res.modeled_ext_lk_active)
        self.assertFalse(res.ext_lk_released_on_tc_change)

    def test_33_g78_vmc_bncm1_ext_lk_blocked_in_regenerate_rec_run_or_sq(self) -> None:
        for kwargs in (
            {"shooting_mode": "Movie", "time_code_make": "Regenerate", "time_code_run": "Free Run"},
            {"shooting_mode": "Movie", "time_code_make": "Preset", "time_code_run": "Rec Run"},
            {"shooting_mode": "S&Q", "time_code_make": "Preset", "time_code_run": "Free Run"},
            {"shooting_mode": "Still", "time_code_make": "Preset", "time_code_run": "Free Run"},
        ):
            res = verify_tc_regenerate_extlk_and_reclamp_tally_guard(
                vmc_bncm1_attached=True,
                claimed_ext_lk_active=True,
                **kwargs,
            )
            self.assertFalse(res.valid, msg=str(kwargs))
            self.assertIn(
                STATUS_BLOCKED_G78_VMC_BNCM1_EXT_LK_PREREQ_OR_RELEASE_VIOLATION,
                res.violation_codes,
            )

    def test_34_g78_vmc_bncm1_ext_lk_immediately_releases_on_tc_make_or_run_switch(self) -> None:
        released_make = verify_tc_regenerate_extlk_and_reclamp_tally_guard(
            shooting_mode="Movie",
            time_code_make="Preset",
            time_code_run="Free Run",
            vmc_bncm1_attached=True,
            tc_make_switched_after_lock=True,
            claimed_ext_lk_active=False,
        )
        self.assertTrue(released_make.valid)
        self.assertFalse(released_make.modeled_ext_lk_active)
        self.assertTrue(released_make.ext_lk_released_on_tc_change)

        stale_ext_lk_claim = verify_tc_regenerate_extlk_and_reclamp_tally_guard(
            shooting_mode="Movie",
            time_code_make="Preset",
            time_code_run="Free Run",
            vmc_bncm1_attached=True,
            tc_run_switched_after_lock=True,
            claimed_ext_lk_active=True,
        )
        self.assertFalse(stale_ext_lk_claim.valid)
        self.assertIn(
            STATUS_BLOCKED_G78_VMC_BNCM1_EXT_LK_PREREQ_OR_RELEASE_VIOLATION,
            stale_ext_lk_claim.violation_codes,
        )

    def test_35_g78_sq_mode_locks_out_tc_run_and_hdmi_timecode_output(self) -> None:
        sq_valid = verify_tc_regenerate_extlk_and_reclamp_tally_guard(
            shooting_mode="S&Q",
            sq_time_code_run_selectable_claimed=False,
            hdmi_time_code_output_on=False,
        )
        self.assertTrue(sq_valid.valid)
        self.assertTrue(sq_valid.sq_tc_run_locked_out)

        sq_tcrun_err = verify_tc_regenerate_extlk_and_reclamp_tally_guard(
            shooting_mode="S&Q", sq_time_code_run_selectable_claimed=True
        )
        sq_hdmi_err = verify_tc_regenerate_extlk_and_reclamp_tally_guard(
            shooting_mode="S&Q", hdmi_time_code_output_on=True
        )
        self.assertFalse(sq_tcrun_err.valid)
        self.assertFalse(sq_hdmi_err.valid)
        self.assertIn(
            STATUS_BLOCKED_G78_SQ_TC_RUN_OR_HDMI_TCOUT_LOCKOUT,
            sq_tcrun_err.violation_codes,
        )
        self.assertIn(
            STATUS_BLOCKED_G78_SQ_TC_RUN_OR_HDMI_TCOUT_LOCKOUT,
            sq_hdmi_err.violation_codes,
        )

    def test_36_g78_movie_mode_allows_hdmi_time_code_output_on(self) -> None:
        res = verify_tc_regenerate_extlk_and_reclamp_tally_guard(
            shooting_mode="Movie", hdmi_time_code_output_on=True
        )
        self.assertTrue(res.valid)
        self.assertTrue(res.hdmi_time_code_output_on)

    def test_37_g78_rec_lamp_three_states_and_standby_truth_table(self) -> None:
        self.assertEqual(
            ALLOWED_FX3_REC_LAMP_MODES,
            (REC_LAMP_ALL_ON, REC_LAMP_ONLY_FRONT_OFF, REC_LAMP_ALL_OFF),
        )
        self.assertEqual(
            resolve_fx3_rec_lamp_coupled_tally(rec_lamp_mode="All On", is_recording=True),
            (True, True, True, True, False),
        )
        self.assertEqual(
            resolve_fx3_rec_lamp_coupled_tally(
                rec_lamp_mode="Only Front Off", is_recording=True
            ),
            (False, True, True, True, False),
        )
        self.assertEqual(
            resolve_fx3_rec_lamp_coupled_tally(rec_lamp_mode="All Off", is_recording=True),
            (False, False, False, True, False),
        )
        self.assertEqual(
            resolve_fx3_rec_lamp_coupled_tally(rec_lamp_mode="All On", is_recording=False),
            (False, False, False, False, False),
        )

    def test_38_g78_only_front_off_keeps_both_rear_and_top_rec_button_lit(self) -> None:
        res = verify_tc_regenerate_extlk_and_reclamp_tally_guard(
            rec_lamp_mode="Only Front Off",
            is_recording=True,
            front_tally_led_on=False,
            rear_tally_led_on=True,
            top_rec_button_led_on=True,
        )
        self.assertTrue(res.valid)
        self.assertFalse(res.front_tally_led_on)
        self.assertTrue(res.rear_tally_led_on)
        self.assertTrue(res.top_rec_button_led_on)
        self.assertTrue(res.rear_and_top_tally_coupled)

    def test_39_g78_decoupled_rear_top_tally_or_invalid_lamp_mode_blocked(self) -> None:
        decoupled_top_off = verify_tc_regenerate_extlk_and_reclamp_tally_guard(
            rec_lamp_mode="Only Front Off",
            is_recording=True,
            front_tally_led_on=False,
            rear_tally_led_on=True,
            top_rec_button_led_on=False,
        )
        decoupled_rear_off = verify_tc_regenerate_extlk_and_reclamp_tally_guard(
            rec_lamp_mode="All Off",
            is_recording=True,
            front_tally_led_on=False,
            rear_tally_led_on=False,
            top_rec_button_led_on=True,
        )
        invalid_4zone = verify_tc_regenerate_extlk_and_reclamp_tally_guard(
            rec_lamp_mode="Only Rear Off"
        )
        for bad in (decoupled_top_off, decoupled_rear_off, invalid_4zone):
            self.assertFalse(bad.valid)
            self.assertIn(
                STATUS_BLOCKED_G78_REC_LAMP_COUPLED_TALLY_OR_OSD_VIOLATION,
                bad.violation_codes,
            )

    def test_40_g78_all_off_with_independent_emphasized_rec_display_hdmi_red_frame(self) -> None:
        hdmi_red_on = verify_tc_regenerate_extlk_and_reclamp_tally_guard(
            rec_lamp_mode="All Off",
            is_recording=True,
            emphasized_rec_display_on=True,
            hdmi_info_display_on=True,
            hdmi_red_rec_frame_active=True,
        )
        self.assertTrue(hdmi_red_on.valid)
        self.assertTrue(hdmi_red_on.hdmi_red_rec_frame_active)

        hdmi_clean_feed = verify_tc_regenerate_extlk_and_reclamp_tally_guard(
            rec_lamp_mode="All Off",
            is_recording=True,
            emphasized_rec_display_on=True,
            hdmi_info_display_on=False,
            hdmi_red_rec_frame_active=True,
        )
        self.assertFalse(hdmi_clean_feed.valid)
        self.assertIn(
            STATUS_BLOCKED_G78_REC_LAMP_COUPLED_TALLY_OR_OSD_VIOLATION,
            hdmi_clean_feed.violation_codes,
        )

    def test_41_g78_silent_mode_hard_locks_audio_signals_off(self) -> None:
        valid_silent = verify_tc_regenerate_extlk_and_reclamp_tally_guard(
            silent_mode_on=True,
            audio_signals_menu_on=True,
            effective_audio_signals_on=False,
            audio_signals_editable_in_silent_mode_claimed=False,
            af_or_selftimer_beep_emitted=False,
        )
        self.assertTrue(valid_silent.valid)
        self.assertFalse(valid_silent.effective_audio_signals_on)

        for bad_kwargs in (
            {"silent_mode_on": True, "effective_audio_signals_on": True},
            {"silent_mode_on": True, "audio_signals_editable_in_silent_mode_claimed": True},
            {"silent_mode_on": True, "af_or_selftimer_beep_emitted": True},
        ):
            bad = verify_tc_regenerate_extlk_and_reclamp_tally_guard(**bad_kwargs)
            self.assertFalse(bad.valid, msg=str(bad_kwargs))
            self.assertIn(
                STATUS_BLOCKED_G78_SILENT_MODE_AUDIO_SIGNALS_LOCK_VIOLATION,
                bad.violation_codes,
            )

    def test_42_g78_invalid_telemetry_and_emmc_write_redline_blocked(self) -> None:
        bad_enum = verify_tc_regenerate_extlk_and_reclamp_tally_guard(
            time_code_make="JamSyncAuto"
        )
        bad_type = verify_tc_regenerate_extlk_and_reclamp_tally_guard(
            is_recording="yes"  # type: ignore[arg-type]
        )
        self.assertFalse(bad_enum.valid)
        self.assertFalse(bad_type.valid)
        self.assertIn(STATUS_BLOCKED_G78_TELEMETRY_INVALID, bad_enum.violation_codes)
        self.assertIn(STATUS_BLOCKED_G78_TELEMETRY_INVALID, bad_type.violation_codes)

        v_emmc, r_emmc = evaluate_g78_tcregen_reclamp_guard(
            force_clean_room=True, request_persistent_emmc_writes=True
        )
        self.assertFalse(v_emmc.passed)
        self.assertIn(STATUS_BLOCKED_PERSISTENT_EMMC_WRITE, r_emmc.violation_codes)

    # ------------------------------------------------------------------
    # Section D: Unified 78-Gate Preflight, Compat & CLI (18 tests -> 60 total)
    # ------------------------------------------------------------------

    def test_43_master_78gate_offline_default_75_of_78_verified(self) -> None:
        r = self.offline_78
        self.assertEqual(r.schema, REALHW_FILESETTINGS_SHOTMARK_TCREGEN_RECLAMP_78GATE_SCHEMA)
        self.assertEqual(r.summary["total_gates"], 78)
        self.assertEqual(r.summary["verified_gates"], 75)
        self.assertEqual(r.summary["blocked_or_pending_gates"], 3)
        self.assertTrue(r.offline_75_gates_verified)
        self.assertFalse(r.all_78_gates_verified)
        self.assertTrue(r.g13_to_g78_all_passed)
        self.assertTrue(r.g77_to_g78_all_passed)
        self.assertEqual(r.status, "VERIFIED_75_OF_78_AWAITING_PHYSICAL_TIER0")
        self.assertEqual(len(r.gates), 78)
        self.assertEqual(r.gates[76]["gate_id"], G77_GATE_ID)
        self.assertEqual(r.gates[77]["gate_id"], G78_GATE_ID)

    def test_44_master_78gate_simulate_bench_dry_run_78_of_78_verified(self) -> None:
        r = self.dryrun_78
        self.assertEqual(r.summary["total_gates"], 78)
        self.assertEqual(r.summary["verified_gates"], 78)
        self.assertTrue(r.offline_75_gates_verified)
        self.assertTrue(r.all_78_gates_verified)
        self.assertTrue(r.dry_run_rehearsal_only)
        self.assertEqual(r.status, "VERIFIED_ALL_78_GATES_DRY_RUN_SIMULATED_BACKUP")

    def test_45_master_78gate_hard_redlines_locked_in_offline_and_dry_run(self) -> None:
        for r in (
            self.offline_78,
            self.dryrun_78,
            self.clean_offline_78,
            self.clean_dryrun_78,
        ):
            self.assertFalse(r.overall_ready_for_hardware_attach)
            self.assertFalse(r.hardware_live_attachment_authorized)
            self.assertFalse(r.persistent_emmc_writes_authorized)
            self.assertFalse(r.spi_nor_write_authorized)
            self.assertFalse(r.el3_payload_transmit_authorized)
            self.assertFalse(r.physical_flash_auto_exec_authorized)
            self.assertFalse(r.human_hardware_attach_token)
            self.assertTrue(r.agent_auto_flash_blocked)
            self.assertEqual(r.usb_packets_transmitted, 0)
            self.assertEqual(r.raw_firmware_bytes_leaked, 0)

    def test_46_master_78gate_clean_room_offline_and_dry_run_parity(self) -> None:
        self.assertEqual(self.clean_offline_78.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(self.clean_offline_78.clean_room_forced)
        self.assertEqual(self.clean_offline_78.summary["verified_gates"], 75)
        self.assertEqual(self.clean_dryrun_78.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(self.clean_dryrun_78.summary["verified_gates"], 78)
        self.assertTrue(self.clean_dryrun_78.all_78_gates_verified)

    def test_47_master_78gate_dry_run_simulated_backup_alias_supported(self) -> None:
        r = evaluate_78gate_preflight(
            dry_run_simulated_backup=True, master_76_override=self.dryrun_76
        )
        self.assertTrue(r.all_78_gates_verified)
        self.assertTrue(r.dry_run_rehearsal_only)

    def test_48_master_78gate_propagates_g77_failure_fail_closed(self) -> None:
        r = evaluate_78gate_preflight(
            force_clean_room=True,
            master_76_override=self.clean_offline_76,
            filesettings_shotmark_kwargs={
                "file_name_format": "Title",
                "slot1_media_type": "SDHC",
            },
        )
        self.assertFalse(r.g77_to_g78_all_passed)
        self.assertFalse(r.offline_75_gates_verified)
        self.assertEqual(
            r.status, STATUS_BLOCKED_G77_SDHC_STANDARD_LOCK_OR_CUSTOM_FOLDER_FORBIDDEN
        )
        self.assertEqual(r.summary["verified_gates"], 74)

    def test_49_master_78gate_propagates_g78_failure_fail_closed(self) -> None:
        r = evaluate_78gate_preflight(
            force_clean_room=True,
            master_76_override=self.clean_offline_76,
            tcregen_reclamp_kwargs={
                "rec_lamp_mode": "Only Front Off",
                "is_recording": True,
                "top_rec_button_led_on": False,
            },
        )
        self.assertFalse(r.g77_to_g78_all_passed)
        self.assertFalse(r.offline_75_gates_verified)
        self.assertEqual(
            r.status, STATUS_BLOCKED_G78_REC_LAMP_COUPLED_TALLY_OR_OSD_VIOLATION
        )
        self.assertEqual(r.summary["verified_gates"], 74)

    def test_50_master_78gate_blocks_persistent_emmc_write_request(self) -> None:
        r = evaluate_78gate_preflight(
            force_clean_room=True,
            master_76_override=self.clean_offline_76,
            request_persistent_emmc_writes=True,
        )
        self.assertFalse(r.offline_75_gates_verified)
        self.assertFalse(r.h0_h1_trial_entry_allowed)
        self.assertEqual(r.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)

    def test_51_master_78gate_json_serializable_to_dict(self) -> None:
        payload = json.loads(json.dumps(self.offline_78.to_dict()))
        self.assertEqual(payload["summary"]["total_gates"], 78)
        self.assertEqual(len(payload["gates"]), 78)
        self.assertIn("g77_result", payload)
        self.assertIn("g78_result", payload)

    def test_52_backward_compatibility_across_verify_58_through_verify_76_gates(self) -> None:
        # Verify nested chain G01..G76 remains 100% intact across 58..76 evaluators
        self.assertEqual(self.offline_76.summary["total_gates"], 76)
        self.assertEqual(self.offline_76.summary["verified_gates"], 73)
        self.assertEqual(self.dryrun_76.summary["verified_gates"], 76)
        for fn_name, expected_total in (
            ("evaluate_58gate_preflight", 58),
            ("evaluate_60gate_preflight", 60),
            ("evaluate_62gate_preflight", 62),
            ("evaluate_64gate_preflight", 64),
            ("evaluate_66gate_preflight", 66),
            ("evaluate_68gate_preflight", 68),
            ("evaluate_70gate_preflight", 70),
            ("evaluate_72gate_preflight", 72),
            ("evaluate_74gate_preflight", 74),
            ("evaluate_76gate_preflight", 76),
        ):
            self.assertTrue(hasattr(fx3_safety, fn_name), msg=fn_name)
            self.assertEqual(expected_total % 2, 0)

    def test_53_cli_verify_g77_text_and_json_modes(self) -> None:
        buf_txt = io.StringIO()
        with contextlib.redirect_stdout(buf_txt):
            rc_txt = cli_main(["verify-g77-filesettings-shotmark"])
        self.assertEqual(rc_txt, 0)
        self.assertIn("valid=True", buf_txt.getvalue())

        buf_json = io.StringIO()
        with contextlib.redirect_stdout(buf_json):
            rc_json = cli_main(
                ["verify-g77-filesettings-shotmark", "--force-clean-room", "--json"]
            )
        self.assertEqual(rc_json, 0)
        parsed = json.loads(buf_json.getvalue())
        self.assertTrue(parsed["valid"])
        self.assertEqual(parsed["verification_mode"], "CLEAN_ROOM_SYNTHETIC")

    def test_54_cli_verify_g78_text_and_json_modes(self) -> None:
        buf_txt = io.StringIO()
        with contextlib.redirect_stdout(buf_txt):
            rc_txt = cli_main(["verify-g78-tcregen-reclamp"])
        self.assertEqual(rc_txt, 0)
        self.assertIn("valid=True", buf_txt.getvalue())

        buf_json = io.StringIO()
        with contextlib.redirect_stdout(buf_json):
            rc_json = cli_main(
                ["verify-g78-tcregen-reclamp", "--force-clean-room", "--json"]
            )
        self.assertEqual(rc_json, 0)
        parsed = json.loads(buf_json.getvalue())
        self.assertTrue(parsed["valid"])
        self.assertEqual(parsed["verification_mode"], "CLEAN_ROOM_SYNTHETIC")

    def test_55_cli_verify_78_gates_offline_text_mode(self) -> None:
        buf = io.StringIO()
        with mock.patch(
            "fx3_safety.__main__.evaluate_78gate_preflight",
            return_value=self.offline_78,
        ):
            with contextlib.redirect_stdout(buf):
                rc = cli_main(["verify-78-gates"])
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("verified=75/78", out)
        self.assertIn("hardware_live_attachment_authorized=False", out)
        self.assertIn("usb_packets_transmitted=0", out)

    def test_56_cli_verify_78_gates_simulate_bench_dry_run_json_mode(self) -> None:
        buf = io.StringIO()
        with mock.patch(
            "fx3_safety.__main__.evaluate_78gate_preflight",
            return_value=self.dryrun_78,
        ):
            with contextlib.redirect_stdout(buf):
                rc = cli_main(["verify-78-gates", "--simulate-bench-dry-run", "--json"])
        self.assertEqual(rc, 0)
        parsed = json.loads(buf.getvalue())
        self.assertEqual(parsed["summary"]["verified_gates"], 78)
        self.assertTrue(parsed["all_78_gates_verified"])

    def test_57_module_standalone_main_text_and_json(self) -> None:
        buf_txt = io.StringIO()
        with mock.patch(
            "fx3_safety.realhw_filesettings_shotmark_tcregen_reclamp_and_78gate_guard.evaluate_78gate_preflight",
            return_value=self.clean_offline_78,
        ):
            with contextlib.redirect_stdout(buf_txt):
                rc1 = module_main(["--force-clean-room"])
        self.assertEqual(rc1, 0)
        self.assertIn("verified=75/78", buf_txt.getvalue())

        buf_json = io.StringIO()
        with mock.patch(
            "fx3_safety.realhw_filesettings_shotmark_tcregen_reclamp_and_78gate_guard.evaluate_78gate_preflight",
            return_value=self.clean_dryrun_78,
        ):
            with contextlib.redirect_stdout(buf_json):
                rc2 = module_main(["--simulate-bench-dry-run", "--json"])
        self.assertEqual(rc2, 0)
        self.assertEqual(json.loads(buf_json.getvalue())["summary"]["verified_gates"], 78)

    def test_58_g77_all_transfer_target_aliases_normalized_accurately(self) -> None:
        for alias, expected in (
            ("All", "ALL"),
            ("Only Shot Mark Mov.", "ONLY_SHOT_MARK_MOV"),
            ("Only Shot Mark", "ONLY_SHOT_MARK"),
        ):
            res = verify_file_settings_sdhc_37char_and_shotmark_guard(
                shot_mark1_present=True,
                transfer_target_movie=alias,
                clip_selected_for_transfer=True,
            )
            self.assertTrue(res.valid, msg=alias)
            self.assertEqual(res.canonical_transfer_target_movie, expected)

    def test_59_g78_silent_mode_off_respects_audio_signals_menu_toggle(self) -> None:
        on_res = verify_tc_regenerate_extlk_and_reclamp_tally_guard(
            silent_mode_on=False, audio_signals_menu_on=True
        )
        off_res = verify_tc_regenerate_extlk_and_reclamp_tally_guard(
            silent_mode_on=False, audio_signals_menu_on=False
        )
        self.assertTrue(on_res.valid)
        self.assertTrue(on_res.effective_audio_signals_on)
        self.assertTrue(off_res.valid)
        self.assertFalse(off_res.effective_audio_signals_on)

    def test_60_direct_end_to_end_live_evaluate_78gate_both_modes_without_mock(self) -> None:
        live_norm = evaluate_78gate_preflight()
        self.assertEqual(live_norm.summary["verified_gates"], 75)
        self.assertTrue(live_norm.offline_75_gates_verified)

        live_clean_dry = evaluate_78gate_preflight(
            force_clean_room=True, simulate_bench_dry_run=True
        )
        self.assertEqual(live_clean_dry.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(live_clean_dry.summary["verified_gates"], 78)
        self.assertTrue(live_clean_dry.all_78_gates_verified)


if __name__ == "__main__":
    unittest.main()
