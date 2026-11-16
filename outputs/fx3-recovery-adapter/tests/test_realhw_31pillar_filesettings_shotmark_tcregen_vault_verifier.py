"""Phase 215 dual-mode tests: Pillar 31 (`[File Settings]` SDHC/37-Char & `Shot Mark1/2` `*M01.XML`
Sidecar + `[TC/UB]` `Regenerate` Slot-1 Continuity Vault) and Unified `31/31` Recovery Master.
"""

from __future__ import annotations

from dataclasses import replace
import io
import json
import os
from pathlib import Path
import shutil
import sys
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent

import fx3_recovery
from fx3_recovery import (
    MASTER_30_PILLAR_COUNT,
    MASTER_31_PILLAR_COUNT,
    MASTER_31_PILLAR_IDS,
    MASTER_31_PILLAR_SPECS,
    P215_BLOCKED_EXT_LK_DROP_HAZARD_ON_RESTORE,
    P215_BLOCKED_IMAGE_JUMP_OR_FTP_SHOTMARK_RESCUE_BROKEN,
    P215_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
    P215_BLOCKED_RECLAMP_COUPLED_TALLY_OR_SILENT_LOCK_DRIFT,
    P215_BLOCKED_REEL_OR_SERIES_COUNTER_COLLISION,
    P215_BLOCKED_SAFETY_POLICY_VIOLATION,
    P215_BLOCKED_SDHC_FORCED_STANDARD_LOCK_VIOLATION,
    P215_BLOCKED_SHOTMARK_XML_SIDECAR_ORPHAN_OR_CORRUPT,
    P215_BLOCKED_SQ_TIMECODE_RUN_OR_HDMI_TCOUT_LOCKOUT,
    P215_BLOCKED_TCREGEN_SLOT1_OR_FORCED_RECRUN_VIOLATION,
    P215_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
    P215_BLOCKED_TITLE_NAME_37CHAR_OR_ASCII_INVALID,
    P215_CONCURRENT_CEILING_SECONDS,
    P215_DONOR_INSPECT_BUDGET_SECONDS,
    P215_FILE_NAME_FORMATS,
    P215_FX3_FW_VERSION,
    P215_FX3_MODEL_NAME,
    P215_IMAGE_JUMP_MODES,
    P215_PILLAR_31A_SCENARIO_IDS,
    P215_PILLAR_31B_SCENARIO_IDS,
    P215_REC_LAMP_MODES,
    P215_STATUS_FAIL_31OF31_AGGREGATOR,
    P215_STATUS_FAIL_PILLAR31_SUITE,
    P215_STATUS_VERIFIED_31OF31_AGGREGATOR,
    P215_STATUS_VERIFIED_PILLAR31_SUITE,
    P215_STATUS_VERIFIED_PILLAR_31A,
    P215_STATUS_VERIFIED_PILLAR_31B,
    P215_TITLE_ALLOWED_SYMBOLS,
    P215_TITLE_NAME_MAX_CHARS,
    FileSettingsAndShotMarkVaultSpec,
    ShotMarkSidecarPairSpec,
    SlotMediaFileSettingsSpec,
    TcRegenSlot1AndExtLkVaultSpec,
    build_default_safe_filesettings_shotmark_spec,
    build_default_safe_tcregen_extlk_spec,
    evaluate_22pillar_recovery_master,
    evaluate_24pillar_recovery_master,
    evaluate_26pillar_recovery_master,
    evaluate_27pillar_recovery_master,
    evaluate_28pillar_recovery_master,
    evaluate_29pillar_recovery_master,
    evaluate_30pillar_recovery_master,
    evaluate_31pillar_recovery_master,
    evaluate_filesettings_and_shotmark_xml_vault,
    evaluate_realhw_31pillar_recovery_master,
    evaluate_tcregen_slot1_and_extlk_vault,
    inspect_phase215_donors_readonly,
    realhw_31pillar_filesettings_shotmark_tcregen_vault_verifier as p215,
    run_pillar31_standalone_suite,
    run_pillar31a_filesettings_shotmark_6_scenario_suite,
    run_pillar31b_tcregen_slot1_extlk_6_scenario_suite,
    verify_31pillar_recovery_suite,
    verify_filesettings_shotmark_and_tcregen_slot1_vault,
)
from fx3_recovery.__main__ import main as cli_main


def _assert_zero_raw_firmware_leaks(testcase: unittest.TestCase, payload_dict: dict) -> None:
    dumped = json.dumps(payload_dict, sort_keys=True)
    testcase.assertNotIn("\\x7fELF", dumped)
    testcase.assertNotIn("89554655", dumped)
    testcase.assertNotIn("424b3400", dumped)
    testcase.assertEqual(payload_dict.get("raw_firmware_bytes_leaked", 0), 0)
    testcase.assertEqual(payload_dict.get("physical_device_writes", 0), 0)
    testcase.assertFalse(payload_dict.get("persistent_emmc_writes_authorized", False))


class TestPhase215Pillar31FileSettingsShotMarkTcRegenAnd31Of31Master(unittest.TestCase):
    # -----------------------------------------------------------------------
    # Group 0: Safety invariants, exports, donor check & clean-room fallback
    # -----------------------------------------------------------------------

    def test_01_hardlocked_safety_policy_constants(self) -> None:
        self.assertFalse(p215.PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(p215.SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(p215.EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        self.assertFalse(p215.ISP_WRITE_AUTHORIZED)
        self.assertFalse(p215.PERSISTENT_WRITE_RELEASE)
        self.assertFalse(p215.ALLOW_BOOT_PARTITION_TARGETING)
        self.assertFalse(p215.ALLOW_DESTRUCTIVE_FASTBOOT)
        self.assertFalse(p215.ALLOW_PERSISTENT_JIRITSU_WRITES)
        self.assertFalse(p215.ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS)
        self.assertFalse(p215.LIVE_USB_IOKIT_TRANSMIT_ENABLED)
        self.assertTrue(p215.READ_ONLY_DONOR_ACCESS)
        self.assertEqual(p215.OTP_FUSE_TOUCHES, 0)
        self.assertEqual(p215.OTP_FUSE_WRITES, 0)
        self.assertEqual(p215.RPMB_COUNTER_INCREMENTS, 0)
        self.assertEqual(p215.PASSIVE_TX_BYTES_EMITTED, 0)
        self.assertEqual(p215.PHYSICAL_USB_PACKETS_EMITTED, 0)
        self.assertEqual(p215.PHYSICAL_DEVICE_WRITES, 0)
        self.assertEqual(p215.RAW_FIRMWARE_BYTES_LEAKED, 0)

    def test_02_package_exports_and_zero_symbol_shadowing(self) -> None:
        for sym in (
            "MASTER_31_PILLAR_COUNT",
            "MASTER_31_PILLAR_IDS",
            "MASTER_31_PILLAR_SPECS",
            "verify_filesettings_shotmark_and_tcregen_slot1_vault",
            "evaluate_realhw_31pillar_recovery_master",
            "evaluate_31pillar_recovery_master",
            "verify_31pillar_recovery_suite",
            "run_pillar31_standalone_suite",
            "P215_BLOCKED_SDHC_FORCED_STANDARD_LOCK_VIOLATION",
            "P215_BLOCKED_TCREGEN_SLOT1_OR_FORCED_RECRUN_VIOLATION",
        ):
            self.assertIn(sym, fx3_recovery.__all__)
            self.assertTrue(hasattr(fx3_recovery, sym))
        self.assertFalse(fx3_recovery.PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertTrue(fx3_recovery.READ_ONLY_DONOR_ACCESS)
        self.assertEqual(MASTER_30_PILLAR_COUNT, 30)
        self.assertEqual(MASTER_31_PILLAR_COUNT, 31)

    def test_03_master_31_pillar_registry_completeness(self) -> None:
        self.assertEqual(len(MASTER_31_PILLAR_SPECS), 31)
        self.assertEqual(len(MASTER_31_PILLAR_IDS), 31)
        self.assertEqual(len(set(MASTER_31_PILLAR_IDS)), 31)
        self.assertEqual([spec[0] for spec in MASTER_31_PILLAR_SPECS], list(range(1, 32)))
        self.assertEqual(MASTER_31_PILLAR_SPECS[30][1], "pillar_31_filesettings_shotmark_tcregen_vault")
        self.assertEqual(MASTER_31_PILLAR_SPECS[30][2], "Phase 215")

    def test_04_bounded_readonly_donor_inspection_under_0_15s(self) -> None:
        snap = inspect_phase215_donors_readonly()
        self.assertIn(snap.verification_mode, ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"))
        self.assertTrue(snap.all_donors_present)
        self.assertEqual(snap.donor_files_inspected, 6)
        self.assertTrue(snap.under_0_15s_budget)
        self.assertLess(snap.elapsed_seconds, P215_DONOR_INSPECT_BUDGET_SECONDS)
        self.assertEqual(snap.raw_firmware_bytes_leaked, 0)
        for art in snap.artifacts:
            self.assertTrue(art.matches_pinned)
            if art.digest_kind == "HEADER4K_SHA256":
                self.assertEqual(art.header_bytes_read, 4096)

    def test_05_donor_open_uses_strict_o_rdonly_nofollow_nonblock(self) -> None:
        seen_flags: list[int] = []
        real_open = os.open

        def _spy_open(path_arg: str, flags: int, *args: object) -> int:
            seen_flags.append(flags)
            return real_open(path_arg, flags, *args)

        with patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "0"}, clear=False):
            with patch("fx3_recovery.realhw_31pillar_filesettings_shotmark_tcregen_vault_verifier.os.open", side_effect=_spy_open):
                snap = inspect_phase215_donors_readonly(force_clean_room=False)
        if snap.verification_mode == "LOCAL_DONOR_O_RDONLY":
            self.assertEqual(len(seen_flags), 6)
            for fl in seen_flags:
                self.assertEqual(fl & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC), 0)
                if hasattr(os, "O_NOFOLLOW"):
                    self.assertNotEqual(fl & os.O_NOFOLLOW, 0)
                if hasattr(os, "O_NONBLOCK"):
                    self.assertNotEqual(fl & os.O_NONBLOCK, 0)

    def test_06_env_force_clean_room_synthetic_fallback(self) -> None:
        with patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}, clear=False):
            snap = inspect_phase215_donors_readonly()
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(snap.all_donors_present)
        self.assertEqual(snap.donor_files_inspected, 6)
        self.assertTrue(all(a.read_mode == "CLEAN_ROOM_SYNTHETIC" for a in snap.artifacts))

    def test_07_missing_local_donor_falls_back_cleanly_to_synthetic(self) -> None:
        with patch(
            "fx3_recovery.realhw_31pillar_filesettings_shotmark_tcregen_vault_verifier.resolve_donor_path",
            return_value=None,
        ):
            snap = inspect_phase215_donors_readonly(force_clean_room=False)
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(snap.all_donors_present)
        self.assertEqual(snap.donor_files_inspected, 6)

    def test_08_standalone_suite_deterministic_digest(self) -> None:
        r1 = run_pillar31_standalone_suite(force_clean_room=True)
        r2 = run_pillar31_standalone_suite(force_clean_room=True)
        self.assertTrue(r1.all_passed)
        self.assertEqual(r1.status, P215_STATUS_VERIFIED_PILLAR31_SUITE)
        self.assertEqual(r1.suite_sha256, r2.suite_sha256)

    def test_09_json_serialization_zero_raw_firmware_bytes_leaked(self) -> None:
        rep = run_pillar31_standalone_suite()
        _assert_zero_raw_firmware_leaks(self, rep.to_dict())

    def test_10_default_safe_filesettings_and_tcregen_specs_pass(self) -> None:
        fs_rep = evaluate_filesettings_and_shotmark_xml_vault(build_default_safe_filesettings_shotmark_spec())
        tc_rep = evaluate_tcregen_slot1_and_extlk_vault(build_default_safe_tcregen_extlk_spec())
        self.assertTrue(fs_rep.passed)
        self.assertEqual(fs_rep.status, P215_STATUS_VERIFIED_PILLAR_31A)
        self.assertTrue(tc_rep.passed)
        self.assertEqual(tc_rep.status, P215_STATUS_VERIFIED_PILLAR_31B)

    # -----------------------------------------------------------------------
    # Group A: Pillar 31A — [File Settings], SDHC Lock & Shot Mark1/2 *M01.XML
    # -----------------------------------------------------------------------

    def test_11_all_five_file_name_formats_accepted_across_dual_exfat_slots(self) -> None:
        base = build_default_safe_filesettings_shotmark_spec()
        self.assertEqual(
            P215_FILE_NAME_FORMATS,
            ("Standard", "Cam ID + Reel#", "Title", "Date + Title", "Title + Date"),
        )
        for fmt in P215_FILE_NAME_FORMATS:
            cards = tuple(replace(c, effective_file_name_format=fmt) for c in base.slot_cards)
            rep = evaluate_filesettings_and_shotmark_xml_vault(
                replace(base, file_name_format=fmt, slot_cards=cards)
            )
            self.assertTrue(rep.passed, msg=f"Failed format {fmt}: {rep.errors}")
            self.assertEqual(rep.slots_audited, (1, 2))

    def test_12_title_name_37char_boundary_and_allowed_symbol_charset(self) -> None:
        base = build_default_safe_filesettings_shotmark_spec()
        max_37 = ("FX3" + P215_TITLE_ALLOWED_SYMBOLS + "0123456789ABCDEFGH")[:P215_TITLE_NAME_MAX_CHARS]
        self.assertEqual(len(max_37), 37)
        rep_ok = evaluate_filesettings_and_shotmark_xml_vault(replace(base, title_name=max_37))
        self.assertTrue(rep_ok.passed)
        self.assertEqual(rep_ok.title_name_length, 37)

        for bad_title in ("", "A" * 38, "FX3 BAD SPACE", "FX3/SLASH", "FX3相机"):
            rep_bad = evaluate_filesettings_and_shotmark_xml_vault(replace(base, title_name=bad_title))
            self.assertFalse(rep_bad.passed)
            self.assertEqual(rep_bad.block_code, P215_BLOCKED_TITLE_NAME_37CHAR_OR_ASCII_INVALID)

    def test_13_retroactive_title_rename_on_existing_clips_rejected(self) -> None:
        base = build_default_safe_filesettings_shotmark_spec()
        rep = evaluate_filesettings_and_shotmark_xml_vault(
            replace(base, retroactive_rename_existing_clips_assumed=True)
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P215_BLOCKED_TITLE_NAME_37CHAR_OR_ASCII_INVALID)

    def test_14_sdhc_32gb_fat32_forced_standard_lock_accepted(self) -> None:
        base = build_default_safe_filesettings_shotmark_spec()
        sdhc_slot2 = SlotMediaFileSettingsSpec(
            slot=2,
            card_type="SDHC",
            capacity_gb=32,
            filesystem="FAT32",
            effective_file_name_format="Standard",
            custom_movie_folder_requested=False,
            existing_clip_numbers=(1, 2),
            existing_clip_stems=("C0001", "C0002"),
        )
        rep = evaluate_filesettings_and_shotmark_xml_vault(
            replace(base, slot_cards=(base.slot_cards[0], sdhc_slot2))
        )
        self.assertTrue(rep.passed)
        self.assertEqual(rep.sdhc_slots_locked_to_standard, 1)

    def test_15_sdhc_non_standard_format_or_custom_folder_or_topology_mismatch_rejected(self) -> None:
        base = build_default_safe_filesettings_shotmark_spec()
        bad_fmt = SlotMediaFileSettingsSpec(
            slot=2, card_type="SDHC", capacity_gb=32, filesystem="FAT32", effective_file_name_format="Title"
        )
        bad_folder = SlotMediaFileSettingsSpec(
            slot=2,
            card_type="SDHC",
            capacity_gb=32,
            filesystem="FAT32",
            effective_file_name_format="Standard",
            custom_movie_folder_requested=True,
        )
        bad_topo = SlotMediaFileSettingsSpec(
            slot=2, card_type="SDHC", capacity_gb=64, filesystem="exFAT", effective_file_name_format="Standard"
        )
        for card in (bad_fmt, bad_folder, bad_topo):
            rep = evaluate_filesettings_and_shotmark_xml_vault(
                replace(base, slot_cards=(base.slot_cards[0], card))
            )
            self.assertFalse(rep.passed)
            self.assertEqual(rep.block_code, P215_BLOCKED_SDHC_FORCED_STANDARD_LOCK_VIOLATION)

    def test_16_series_and_reset_counter_collision_against_m4root_clip_rejected(self) -> None:
        base = build_default_safe_filesettings_shotmark_spec()
        # Existing clips on Slot 1 & 2 are (1, 2); restoring Series next=2 or executing Reset (next=1) collides
        rep_series = evaluate_filesettings_and_shotmark_xml_vault(
            replace(base, restored_series_counter_next=2)
        )
        self.assertFalse(rep_series.passed)
        self.assertEqual(rep_series.block_code, P215_BLOCKED_REEL_OR_SERIES_COUNTER_COLLISION)
        self.assertGreaterEqual(rep_series.counter_collision_count, 1)

        rep_reset = evaluate_filesettings_and_shotmark_xml_vault(
            replace(base, series_counter_reset_executed=True)
        )
        self.assertFalse(rep_reset.passed)
        self.assertEqual(rep_reset.block_code, P215_BLOCKED_REEL_OR_SERIES_COUNTER_COLLISION)

        # Empty card accepts Reset cleanly
        empty_cards = tuple(replace(c, existing_clip_numbers=(), existing_clip_stems=()) for c in base.slot_cards)
        rep_clean_reset = evaluate_filesettings_and_shotmark_xml_vault(
            replace(base, file_number_mode="Reset", series_counter_reset_executed=True, slot_cards=empty_cards)
        )
        self.assertTrue(rep_clean_reset.passed)

    def test_17_cam_id_reel_number_stem_collision_and_bounds_rejected(self) -> None:
        base = build_default_safe_filesettings_shotmark_spec()
        reel_card = SlotMediaFileSettingsSpec(
            slot=1,
            card_type="CFexpress_Type_A",
            capacity_gb=160,
            filesystem="exFAT",
            effective_file_name_format="Cam ID + Reel#",
            existing_clip_numbers=(),
            existing_clip_stems=("B007C0005",),
        )
        rep_col = evaluate_filesettings_and_shotmark_xml_vault(
            replace(
                base,
                file_name_format="Cam ID + Reel#",
                cam_id="B",
                reel_number=7,
                restored_series_counter_next=5,
                slot_cards=(reel_card,),
            )
        )
        self.assertFalse(rep_col.passed)
        self.assertEqual(rep_col.block_code, P215_BLOCKED_REEL_OR_SERIES_COUNTER_COLLISION)

        for kw in ({"cam_id": "1"}, {"reel_number": 0}, {"reel_number": 1000}, {"restored_series_counter_next": 10000}):
            rep_bounds = evaluate_filesettings_and_shotmark_xml_vault(replace(base, **kw))
            self.assertFalse(rep_bounds.passed)
            self.assertEqual(rep_bounds.block_code, P215_BLOCKED_REEL_OR_SERIES_COUNTER_COLLISION)

    def test_18_shotmark_m01_xml_orphan_missing_corrupt_unsynced_negative_rejected(self) -> None:
        base = build_default_safe_filesettings_shotmark_spec()
        p0 = base.sidecar_pairs[0]
        bad_variants = (
            replace(p0, mp4_present=False, xml_present=True),
            replace(p0, mp4_present=True, xml_present=False),
            replace(p0, xml_well_formed=False),
            replace(p0, nrt_metadata_intact=False),
            replace(p0, xml_shot_mark1_synced=False),
            replace(p0, xml_shot_mark2_synced=False),
            replace(p0, shot_mark1_frames=(-1, 24)),
            replace(p0, xml_relpath="/M4ROOT/CLIP/WRONG_NAME.XML"),
        )
        for bad_pair in bad_variants:
            rep = evaluate_filesettings_and_shotmark_xml_vault(
                replace(base, sidecar_pairs=(bad_pair, base.sidecar_pairs[1]))
            )
            self.assertFalse(rep.passed)
            self.assertEqual(rep.block_code, P215_BLOCKED_SHOTMARK_XML_SIDECAR_ORPHAN_OR_CORRUPT)
            self.assertGreaterEqual(rep.orphaned_or_corrupt_xml_count, 1)

    def test_19_image_jump_modes_verified_when_sidecars_intact(self) -> None:
        base = build_default_safe_filesettings_shotmark_spec()
        for mode in P215_IMAGE_JUMP_MODES:
            rep = evaluate_filesettings_and_shotmark_xml_vault(replace(base, image_jump_setting=mode))
            self.assertTrue(rep.passed, msg=f"Image Jump {mode} failed: {rep.errors}")

    def test_20_ftp_only_shot_mark_mov_rescue_blocked_when_zero_marked_clips(self) -> None:
        base = build_default_safe_filesettings_shotmark_spec()
        unmarked = tuple(replace(p, shot_mark1_frames=(), shot_mark2_frames=()) for p in base.sidecar_pairs)
        for ftp_mode in ("Only Shot Mark Mov.", "Only Shot Mark"):
            rep = evaluate_filesettings_and_shotmark_xml_vault(
                replace(base, sidecar_pairs=unmarked, ftp_target_movie=ftp_mode, ftp_batch_rescue_active=True)
            )
            self.assertFalse(rep.passed)
            self.assertEqual(rep.block_code, P215_BLOCKED_IMAGE_JUMP_OR_FTP_SHOTMARK_RESCUE_BROKEN)
            self.assertEqual(rep.marked_clips_ready_for_ftp, 0)

        rep_all = evaluate_filesettings_and_shotmark_xml_vault(
            replace(base, sidecar_pairs=unmarked, ftp_target_movie="All", ftp_batch_rescue_active=True)
        )
        self.assertTrue(rep_all.passed)

    def test_21_pillar31a_persistent_overlay_escape_rejected(self) -> None:
        base = build_default_safe_filesettings_shotmark_spec()
        for bad_dir in ("/setting/filesettings", "p2:/setting/Backup.bin", "/dev/nflasha2", "/var/tmp/escape"):
            rep = evaluate_filesettings_and_shotmark_xml_vault(replace(base, overlay_dir=bad_dir))
            self.assertFalse(rep.passed)
            self.assertEqual(rep.block_code, P215_BLOCKED_PERSISTENT_OVERLAY_ESCAPE)
        rep_unwiped = evaluate_filesettings_and_shotmark_xml_vault(replace(base, overlay_wiped_on_reset=False))
        self.assertFalse(rep_unwiped.passed)
        self.assertEqual(rep_unwiped.block_code, P215_BLOCKED_PERSISTENT_OVERLAY_ESCAPE)

    def test_22_pillar31a_tier0_h0_h3_drift_rejected(self) -> None:
        base = build_default_safe_filesettings_shotmark_spec()
        for kw in (
            {"p2_blkroset_locked": False},
            {"stage_b_backup_bin_writes": 1},
            {"backup_bin_h3_sha256": "0" * 64},
            {"tier0_surfaces_h0_h3_matched": 15},
        ):
            rep = evaluate_filesettings_and_shotmark_xml_vault(replace(base, **kw))
            self.assertFalse(rep.passed)
            self.assertEqual(rep.block_code, P215_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT)

    def test_23_pillar31a_write_unlock_or_wrong_camera_rejected(self) -> None:
        base = build_default_safe_filesettings_shotmark_spec()
        for kw in (
            {"persistent_write_unlock_requested": True},
            {"camera_model": "ILME-FX6"},
            {"fw_version": "6.00"},
        ):
            rep = evaluate_filesettings_and_shotmark_xml_vault(replace(base, **kw))
            self.assertFalse(rep.passed)
            self.assertEqual(rep.block_code, P215_BLOCKED_SAFETY_POLICY_VIOLATION)

    def test_24_pillar31a_6_scenario_suite_passes_all_6(self) -> None:
        suite = run_pillar31a_filesettings_shotmark_6_scenario_suite()
        self.assertTrue(suite.passed)
        self.assertEqual(suite.status, P215_STATUS_VERIFIED_PILLAR_31A)
        self.assertEqual(suite.scenarios_passed, 6)
        self.assertEqual(suite.scenarios_total, 6)
        self.assertEqual(tuple(s.scenario_id for s in suite.scenarios), P215_PILLAR_31A_SCENARIO_IDS)

    # -----------------------------------------------------------------------
    # Group B: Pillar 31B — [TC/UB] Regenerate Slot-1, EXT-LK & Coupled Tally
    # -----------------------------------------------------------------------

    def test_25_simult_recording_regenerate_reads_slot1_master_and_forces_recrun(self) -> None:
        base = build_default_safe_tcregen_extlk_spec()
        rep = evaluate_tcregen_slot1_and_extlk_vault(base)
        self.assertTrue(rep.passed)
        self.assertTrue(rep.slot1_master_tc_verified)
        self.assertEqual(rep.effective_time_code_run, "Rec Run")

    def test_26_slot2_active_media_regenerate_reads_slot2_and_midnight_wraparound(self) -> None:
        base = build_default_safe_tcregen_extlk_spec()
        rep_s2 = evaluate_tcregen_slot1_and_extlk_vault(
            replace(
                base,
                recording_media="Slot 2",
                slot1_last_end_tc="01:12:30:10",
                slot2_last_end_tc="02:00:00:05",
                regenerated_next_start_tc="02:00:00:06",
                regenerate_source_slot_used=2,
            )
        )
        self.assertTrue(rep_s2.passed)

        # Midnight wraparound 23:59:59:23 -> 00:00:00:00 at 24fps, plus drop-frame ';' separator at 30fps
        rep_wrap = evaluate_tcregen_slot1_and_extlk_vault(
            replace(
                base,
                fps_timebase_ceil=24,
                slot1_last_end_tc="23:59:59:23",
                regenerated_next_start_tc="00:00:00:00",
                regenerate_source_slot_used=1,
            )
        )
        self.assertTrue(rep_wrap.passed)

        rep_df = evaluate_tcregen_slot1_and_extlk_vault(
            replace(
                base,
                fps_timebase_ceil=30,
                slot1_last_end_tc="01:05:10;29",
                slot2_last_end_tc="00:10:00;00",
                regenerated_next_start_tc="01:05:11;00",
                regenerate_source_slot_used=1,
            )
        )
        self.assertTrue(rep_df.passed)

    def test_27_simult_regenerate_reading_slot2_or_non_sequential_tc_rejected(self) -> None:
        base = build_default_safe_tcregen_extlk_spec()
        rep_wrong_slot = evaluate_tcregen_slot1_and_extlk_vault(
            replace(base, regenerate_source_slot_used=2, regenerated_next_start_tc="00:45:10:03")
        )
        self.assertFalse(rep_wrong_slot.passed)
        self.assertEqual(rep_wrong_slot.block_code, P215_BLOCKED_TCREGEN_SLOT1_OR_FORCED_RECRUN_VIOLATION)

        rep_gap = evaluate_tcregen_slot1_and_extlk_vault(
            replace(base, regenerated_next_start_tc="01:12:30:15")
        )
        self.assertFalse(rep_gap.passed)
        self.assertEqual(rep_gap.block_code, P215_BLOCKED_TCREGEN_SLOT1_OR_FORCED_RECRUN_VIOLATION)

    def test_28_regenerate_unforced_free_run_or_malformed_tc_rejected(self) -> None:
        base = build_default_safe_tcregen_extlk_spec()
        rep_fr = evaluate_tcregen_slot1_and_extlk_vault(replace(base, effective_time_code_run="Free Run"))
        self.assertFalse(rep_fr.passed)
        self.assertEqual(rep_fr.block_code, P215_BLOCKED_TCREGEN_SLOT1_OR_FORCED_RECRUN_VIOLATION)

        rep_bad_tc = evaluate_tcregen_slot1_and_extlk_vault(replace(base, slot1_last_end_tc="01:12:30:29"))
        self.assertFalse(rep_bad_tc.passed)
        self.assertEqual(rep_bad_tc.block_code, P215_BLOCKED_TCREGEN_SLOT1_OR_FORCED_RECRUN_VIOLATION)

    def test_29_vmc_bncm1_ext_lk_preserved_when_preset_freerun_restored_in_movie_mode(self) -> None:
        base = build_default_safe_tcregen_extlk_spec()
        rep = evaluate_tcregen_slot1_and_extlk_vault(
            replace(
                base,
                shooting_mode="Movie",
                sq_mode_active=False,
                time_code_make="Preset",
                configured_time_code_run="Free Run",
                effective_time_code_run="Free Run",
                vmc_bncm1_ext_lk_active_before_restore=True,
                restored_backup_time_code_make="Preset",
                restored_backup_time_code_run="Free Run",
                ext_lk_retained_after_mode_change_assumed=False,
                ext_lk_rejam_acknowledged=False,
            )
        )
        self.assertTrue(rep.passed)
        self.assertFalse(rep.ext_lk_drop_hazard_detected)

    def test_30_ext_lk_drop_hazard_flagged_on_unacknowledged_backup_restore_or_sq(self) -> None:
        base = build_default_safe_tcregen_extlk_spec()
        # Restoring Regenerate/Rec Run while EXT-LK active without re-jam acknowledgement -> blocked
        rep_drop = evaluate_tcregen_slot1_and_extlk_vault(
            replace(
                base,
                vmc_bncm1_ext_lk_active_before_restore=True,
                restored_backup_time_code_make="Regenerate",
                restored_backup_time_code_run="Rec Run",
                ext_lk_rejam_acknowledged=False,
            )
        )
        self.assertFalse(rep_drop.passed)
        self.assertTrue(rep_drop.ext_lk_drop_hazard_detected)
        self.assertEqual(rep_drop.block_code, P215_BLOCKED_EXT_LK_DROP_HAZARD_ON_RESTORE)

        # Assuming EXT-LK remains locked after switching away from Preset+Free Run -> blocked
        rep_assumed = evaluate_tcregen_slot1_and_extlk_vault(
            replace(
                base,
                vmc_bncm1_ext_lk_active_before_restore=True,
                restored_backup_time_code_make="Preset",
                restored_backup_time_code_run="Rec Run",
                ext_lk_retained_after_mode_change_assumed=True,
                ext_lk_rejam_acknowledged=True,
            )
        )
        self.assertFalse(rep_assumed.passed)
        self.assertEqual(rep_assumed.block_code, P215_BLOCKED_EXT_LK_DROP_HAZARD_ON_RESTORE)

        # EXT-LK claimed in S&Q mode -> blocked
        rep_sq = evaluate_tcregen_slot1_and_extlk_vault(
            replace(
                base,
                shooting_mode="S&Q",
                sq_mode_active=True,
                hdmi_time_code_output="Off",
                vmc_bncm1_ext_lk_active_before_restore=True,
                restored_backup_time_code_make="Preset",
                restored_backup_time_code_run="Free Run",
            )
        )
        self.assertFalse(rep_sq.passed)
        self.assertEqual(rep_sq.block_code, P215_BLOCKED_EXT_LK_DROP_HAZARD_ON_RESTORE)

    def test_31_sq_mode_blocks_tc_run_override_and_hdmi_timecode_output_on(self) -> None:
        base = build_default_safe_tcregen_extlk_spec()
        rep_clean_sq = evaluate_tcregen_slot1_and_extlk_vault(
            replace(base, shooting_mode="S&Q", sq_mode_active=True, hdmi_time_code_output="Off")
        )
        self.assertTrue(rep_clean_sq.passed)

        rep_tc_ovr = evaluate_tcregen_slot1_and_extlk_vault(
            replace(
                base,
                shooting_mode="S&Q",
                sq_mode_active=True,
                hdmi_time_code_output="Off",
                sq_tc_run_override_attempted=True,
            )
        )
        self.assertFalse(rep_tc_ovr.passed)
        self.assertEqual(rep_tc_ovr.block_code, P215_BLOCKED_SQ_TIMECODE_RUN_OR_HDMI_TCOUT_LOCKOUT)

        rep_hdmi_on = evaluate_tcregen_slot1_and_extlk_vault(
            replace(base, shooting_mode="S&Q", sq_mode_active=True, hdmi_time_code_output="On")
        )
        self.assertFalse(rep_hdmi_on.passed)
        self.assertEqual(rep_hdmi_on.block_code, P215_BLOCKED_SQ_TIMECODE_RUN_OR_HDMI_TCOUT_LOCKOUT)

    def test_32_coupled_reclamp_tally_modes_verified_and_decouple_rejected(self) -> None:
        base = build_default_safe_tcregen_extlk_spec()
        self.assertEqual(P215_REC_LAMP_MODES, ("All On", "Only Front Off", "All Off"))
        valid_table = (
            ("All On", True, True, True),
            ("Only Front Off", False, True, True),
            ("All Off", False, False, False),
        )
        for mode, f_on, r_on, t_on in valid_table:
            rep = evaluate_tcregen_slot1_and_extlk_vault(
                replace(base, rec_lamp_mode=mode, front_tally_led_on=f_on, rear_tally_led_on=r_on, top_rec_button_led_on=t_on)
            )
            self.assertTrue(rep.passed)
            self.assertTrue(rep.coupled_reclamp_tally_verified)

        # Attempting to decouple rear tally from top REC button LED -> rejected
        rep_decoupled = evaluate_tcregen_slot1_and_extlk_vault(
            replace(
                base,
                rec_lamp_mode="Only Front Off",
                front_tally_led_on=False,
                rear_tally_led_on=False,
                top_rec_button_led_on=True,
            )
        )
        self.assertFalse(rep_decoupled.passed)
        self.assertEqual(rep_decoupled.block_code, P215_BLOCKED_RECLAMP_COUPLED_TALLY_OR_SILENT_LOCK_DRIFT)

    def test_33_silent_mode_audio_signals_off_hard_lock_enforced(self) -> None:
        base = build_default_safe_tcregen_extlk_spec()
        for bad_audio in ("On: All", "On: Shutter Only"):
            rep = evaluate_tcregen_slot1_and_extlk_vault(
                replace(base, silent_mode_enabled=True, audio_signals_mode=bad_audio)
            )
            self.assertFalse(rep.passed)
            self.assertEqual(rep.block_code, P215_BLOCKED_RECLAMP_COUPLED_TALLY_OR_SILENT_LOCK_DRIFT)

        rep_unlocked = evaluate_tcregen_slot1_and_extlk_vault(
            replace(base, silent_mode_enabled=False, audio_signals_mode="On: Shutter Only")
        )
        self.assertTrue(rep_unlocked.passed)

    def test_34_pillar31b_persistent_overlay_escape_rejected(self) -> None:
        base = build_default_safe_tcregen_extlk_spec()
        for bad_dir in ("/setting/tc", "p2:/setting", "/dev/mmcblk0p2", "/opt/overlay"):
            rep = evaluate_tcregen_slot1_and_extlk_vault(replace(base, stage_b_overlay_dir=bad_dir))
            self.assertFalse(rep.passed)
            self.assertEqual(rep.block_code, P215_BLOCKED_PERSISTENT_OVERLAY_ESCAPE)

    def test_35_pillar31b_tier0_h0_h3_drift_rejected(self) -> None:
        base = build_default_safe_tcregen_extlk_spec()
        for kw in (
            {"p2_blkroset_locked": False},
            {"stage_b_backup_bin_writes": 2},
            {"backup_bin_h3_sha256": "f" * 64},
            {"tier0_surfaces_h0_h3_matched": 14},
        ):
            rep = evaluate_tcregen_slot1_and_extlk_vault(replace(base, **kw))
            self.assertFalse(rep.passed)
            self.assertEqual(rep.block_code, P215_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT)

    def test_36_pillar31b_write_unlock_or_wrong_camera_rejected(self) -> None:
        base = build_default_safe_tcregen_extlk_spec()
        for kw in (
            {"persistent_write_unlock_requested": True},
            {"camera_model": "ILCE-7SM3"},
            {"fw_version": "7.00"},
        ):
            rep = evaluate_tcregen_slot1_and_extlk_vault(replace(base, **kw))
            self.assertFalse(rep.passed)
            self.assertEqual(rep.block_code, P215_BLOCKED_SAFETY_POLICY_VIOLATION)

    def test_37_monkeypatched_safety_constant_immediately_caught(self) -> None:
        with patch.object(p215, "PERSISTENT_EMMC_WRITES_AUTHORIZED", True):
            rep_a = evaluate_filesettings_and_shotmark_xml_vault(build_default_safe_filesettings_shotmark_spec())
            rep_b = evaluate_tcregen_slot1_and_extlk_vault(build_default_safe_tcregen_extlk_spec())
            self.assertFalse(rep_a.passed)
            self.assertFalse(rep_b.passed)
            with self.assertRaises(ValueError):
                evaluate_realhw_31pillar_recovery_master(force_clean_room=True)

    def test_38_camera_target_constants_pinned_to_fx3_7_02(self) -> None:
        self.assertEqual(P215_FX3_MODEL_NAME, "ILME-FX3")
        self.assertEqual(P215_FX3_FW_VERSION, "7.02")
        self.assertEqual(p215.P215_FX3_MODEL_ID, 0x91030080)

    def test_39_pillar31b_6_scenario_suite_passes_all_6(self) -> None:
        suite = run_pillar31b_tcregen_slot1_extlk_6_scenario_suite()
        self.assertTrue(suite.passed)
        self.assertEqual(suite.status, P215_STATUS_VERIFIED_PILLAR_31B)
        self.assertEqual(suite.scenarios_passed, 6)
        self.assertEqual(suite.scenarios_total, 6)
        self.assertEqual(tuple(s.scenario_id for s in suite.scenarios), P215_PILLAR_31B_SCENARIO_IDS)

    # -----------------------------------------------------------------------
    # Group C: Combined Verifier, 31/31 Master, Fault Injection & Compat
    # -----------------------------------------------------------------------

    def test_40_verify_filesettings_shotmark_and_tcregen_slot1_vault_passes_and_fails_cleanly(self) -> None:
        ok_rep = verify_filesettings_shotmark_and_tcregen_slot1_vault(force_clean_room=True)
        self.assertTrue(ok_rep.all_passed)
        self.assertTrue(ok_rep.passed)
        self.assertEqual(ok_rep.status, P215_STATUS_VERIFIED_PILLAR31_SUITE)
        _assert_zero_raw_firmware_leaks(self, ok_rep.to_dict())

        bad_fs = replace(build_default_safe_filesettings_shotmark_spec(), title_name="X" * 40)
        fail_rep = verify_filesettings_shotmark_and_tcregen_slot1_vault(
            filesettings_spec=bad_fs, force_clean_room=True
        )
        self.assertFalse(fail_rep.all_passed)
        self.assertEqual(fail_rep.status, P215_STATUS_FAIL_PILLAR31_SUITE)

    def test_41_evaluate_realhw_31pillar_recovery_master_default_mode(self) -> None:
        rep = evaluate_realhw_31pillar_recovery_master()
        self.assertTrue(rep.all_passed)
        self.assertEqual(rep.status, P215_STATUS_VERIFIED_31OF31_AGGREGATOR)
        self.assertEqual(rep.pillar_count, 31)
        self.assertEqual(rep.pillars_passed, 31)
        self.assertEqual(rep.failed_pillars, ())
        self.assertTrue(rep.under_6s_budget)
        self.assertLess(rep.elapsed_seconds, P215_CONCURRENT_CEILING_SECONDS)
        _assert_zero_raw_firmware_leaks(self, rep.to_dict())

    def test_42_evaluate_realhw_31pillar_recovery_master_clean_room_mode(self) -> None:
        with patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}, clear=False):
            rep = evaluate_realhw_31pillar_recovery_master()
        self.assertTrue(rep.all_passed)
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(rep.pillar_count, 31)
        self.assertEqual(rep.pillars_passed, 31)
        self.assertTrue(all(p.verification_mode == "CLEAN_ROOM_SYNTHETIC" for p in rep.pillars))

    def test_43_master_31pillar_deterministic_sha256_and_aliases(self) -> None:
        r1 = evaluate_realhw_31pillar_recovery_master(force_clean_room=True)
        r2 = evaluate_31pillar_recovery_master(force_clean_room=True)
        r3 = verify_31pillar_recovery_suite(force_clean_room=True)
        self.assertEqual(r1.master_31pillar_sha256, r2.master_31pillar_sha256)
        self.assertEqual(r1.master_31pillar_sha256, r3.master_31pillar_sha256)

    def test_44_fault_injection_on_pillar_31_drops_to_30_of_31(self) -> None:
        rep = evaluate_realhw_31pillar_recovery_master(
            force_clean_room=True,
            fault_inject_pillar="pillar_31_filesettings_shotmark_tcregen_vault",
        )
        self.assertFalse(rep.all_passed)
        self.assertEqual(rep.status, P215_STATUS_FAIL_31OF31_AGGREGATOR)
        self.assertEqual(rep.pillar_count, 31)
        self.assertEqual(rep.pillars_passed, 30)
        self.assertEqual(rep.failed_pillars, ("pillar_31_filesettings_shotmark_tcregen_vault",))

    def test_45_fault_injection_on_earlier_pillar_and_unknown_pillar_error(self) -> None:
        earlier_id = MASTER_31_PILLAR_IDS[14]
        rep = evaluate_realhw_31pillar_recovery_master(
            force_clean_room=True,
            fault_inject_pillar=earlier_id,
        )
        self.assertFalse(rep.all_passed)
        self.assertEqual(rep.pillars_passed, 30)
        self.assertEqual(rep.failed_pillars, (earlier_id,))
        with self.assertRaises(ValueError):
            evaluate_realhw_31pillar_recovery_master(
                force_clean_room=True,
                fault_inject_pillar="pillar_99_nonexistent",
            )

    def test_46_backward_compatibility_22_24_26_27_28_29_30_pillar_masters(self) -> None:
        expected_suites = (
            (evaluate_22pillar_recovery_master, 22),
            (evaluate_24pillar_recovery_master, 24),
            (evaluate_26pillar_recovery_master, 26),
            (evaluate_27pillar_recovery_master, 27),
            (evaluate_28pillar_recovery_master, 28),
            (evaluate_29pillar_recovery_master, 29),
            (evaluate_30pillar_recovery_master, 30),
        )
        for fn, count in expected_suites:
            rep = fn(force_clean_room=True)
            self.assertTrue(rep.all_passed, msg=f"{count}-pillar suite regressed")
            self.assertEqual(rep.pillar_count, count)
            self.assertEqual(rep.pillars_passed, count)

    def test_47_master_31pillar_statuses_numbered_1_through_31_in_order(self) -> None:
        rep = evaluate_realhw_31pillar_recovery_master(force_clean_room=True)
        self.assertEqual([p.pillar_number for p in rep.pillars], list(range(1, 32)))
        self.assertEqual(tuple(p.pillar_id for p in rep.pillars), MASTER_31_PILLAR_IDS)
        p31 = rep.pillars[-1]
        self.assertEqual(p31.key_metrics["pillar_31a_filesettings_shotmark_vault"], "6/6")
        self.assertEqual(p31.key_metrics["pillar_31b_tcregen_slot1_extlk_vault"], "6/6")

    def test_48_master_31pillar_json_roundtrip_integrity(self) -> None:
        rep = evaluate_realhw_31pillar_recovery_master(force_clean_room=True)
        parsed = json.loads(json.dumps(rep.to_dict()))
        self.assertEqual(parsed["schema"], "fx3-realhw-31pillar-recovery-master-verifier-v1")
        self.assertEqual(parsed["pillar_count"], 31)
        self.assertEqual(parsed["pillars_passed"], 31)
        self.assertEqual(len(parsed["pillars"]), 31)

    # -----------------------------------------------------------------------
    # Group D: CLI Subcommands (`verify-filesettings-shotmark-tcregen-vault`, `verify-31pillar-recovery`)
    # -----------------------------------------------------------------------

    def _run_cli(self, argv: list[str]) -> tuple[int, str]:
        buf = io.StringIO()
        with patch.object(sys, "argv", ["fx3_recovery", *argv]), patch.object(sys, "stdout", buf):
            rc = cli_main()
        return rc, buf.getvalue()

    def test_49_cli_verify_filesettings_shotmark_tcregen_vault_json(self) -> None:
        rc, out = self._run_cli(["verify-filesettings-shotmark-tcregen-vault", "--json"])
        self.assertEqual(rc, 0)
        payload = json.loads(out)
        self.assertTrue(payload["all_passed"])
        self.assertEqual(payload["status"], P215_STATUS_VERIFIED_PILLAR31_SUITE)
        _assert_zero_raw_firmware_leaks(self, payload)

    def test_50_cli_verify_filesettings_shotmark_tcregen_vault_clean_room_summary(self) -> None:
        rc, out = self._run_cli(["verify-filesettings-shotmark-tcregen-vault", "--force-clean-room"])
        self.assertEqual(rc, 0)
        self.assertIn("VERIFIED_PILLAR31_FILESETTINGS_SHOTMARK_TCREGEN_VAULT", out)
        self.assertIn("CLEAN_ROOM_SYNTHETIC", out)
        self.assertIn("6/6", out)

    def test_51_cli_verify_31pillar_recovery_json_normal_mode(self) -> None:
        rc, out = self._run_cli(["verify-31pillar-recovery", "--json"])
        self.assertEqual(rc, 0)
        payload = json.loads(out)
        self.assertTrue(payload["all_passed"])
        self.assertEqual(payload["pillar_count"], 31)
        self.assertEqual(payload["pillars_passed"], 31)
        self.assertEqual(payload["status"], P215_STATUS_VERIFIED_31OF31_AGGREGATOR)
        _assert_zero_raw_firmware_leaks(self, payload)

    def test_52_cli_verify_31pillar_recovery_clean_room_summary(self) -> None:
        rc, out = self._run_cli(["verify-31pillar-recovery", "--force-clean-room"])
        self.assertEqual(rc, 0)
        self.assertIn("VERIFIED_31OF31_PILLAR_RECOVERY_MASTER", out)
        self.assertIn("31/31", out)
        self.assertIn("CLEAN_ROOM_SYNTHETIC", out)

    def test_53_cli_verify_31pillar_recovery_exclusive_out_directory(self) -> None:
        out_dir = HERE / f"_tmp_p215_m31_{os.getpid()}"
        out_dir_p31 = HERE / f"_tmp_p215_p31_{os.getpid()}"
        for d in (out_dir, out_dir_p31):
            if d.exists():
                shutil.rmtree(d)
        try:
            rc, _ = self._run_cli(["verify-31pillar-recovery", "--clean-room", "--out", str(out_dir), "--json"])
            self.assertEqual(rc, 0)
            report_file = out_dir / "31pillar-recovery-master-report.json"
            self.assertTrue(report_file.is_file())
            saved = json.loads(report_file.read_text(encoding="utf-8"))
            self.assertEqual(saved["pillars_passed"], 31)

            rc2, _ = self._run_cli(
                ["verify-filesettings-shotmark-tcregen-vault", "--clean-room", "--out", str(out_dir_p31), "--json"]
            )
            self.assertEqual(rc2, 0)
            self.assertTrue((out_dir_p31 / "pillar31-filesettings-shotmark-tcregen-vault-report.json").is_file())
        finally:
            for d in (out_dir, out_dir_p31):
                if d.exists():
                    shutil.rmtree(d)

    def test_54_cli_backward_compat_verify_30pillar_recovery_still_passes(self) -> None:
        rc, out = self._run_cli(["verify-30pillar-recovery", "--force-clean-room", "--json"])
        self.assertEqual(rc, 0)
        payload = json.loads(out)
        self.assertTrue(payload["all_passed"])
        self.assertEqual(payload["pillar_count"], 30)
        self.assertEqual(payload["pillars_passed"], 30)


if __name__ == "__main__":
    unittest.main()
