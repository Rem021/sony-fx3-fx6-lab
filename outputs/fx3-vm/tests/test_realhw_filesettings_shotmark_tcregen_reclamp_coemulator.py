#!/usr/bin/env python3
"""Unit tests for Phase 217 Stage 39 (`39/39` Milestone):
Real-Hardware `ILME-FX3` (`0x91030080`, `Ver. 7.02`) `[File Settings]` (`5` Naming Modes,
`37`-Char ASCII `[Title Name]`, `SDHC <=32GB` Forced `[Standard]` Lock & `Shot Mark1/2`
`*M01.XML` Sidecars + `[Image Jump Setting]` / FTP Filter), `[TC/UB]` (`[Regenerate]`
Exclusive Slot-1 Master Read, Forced `Rec Run`, `VMC-BNCM1` `EXT-LK` Release & `S&Q`
`Time Code Output` Block), and `[REC Lamp]` (`3`-State Coupled Rear + Top `REC` Button Tally,
`[Emphasized REC Display]` & `[Silent Mode]` -> `[Audio signals]` Hard Lock) HIL.
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import contextlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import time
import unittest

FX3_VM_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = FX3_VM_DIR.parents[1]
if str(FX3_VM_DIR) not in sys.path:
    sys.path.insert(0, str(FX3_VM_DIR))

import fx3_vm_coemulation_suite as suite  # noqa: E402
import realhw_filesettings_shotmark_tcregen_reclamp_coemulator as p217  # noqa: E402


_CLEAN_ROOM_AUDIT_CACHE = None
_DEFAULT_AUDIT_CACHE = None
_CLEAN_SUITE_CACHE = None
_CLEAN_SUITE_ELAPSED = None
_DEFAULT_SUITE_CACHE = None
_DEFAULT_SUITE_ELAPSED = None


def _get_clean_room_audit():
    global _CLEAN_ROOM_AUDIT_CACHE
    if _CLEAN_ROOM_AUDIT_CACHE is None:
        _CLEAN_ROOM_AUDIT_CACHE = (
            p217.run_phase217_realhw_filesettings_shotmark_tcregen_reclamp_hil(
                force_clean_room=True
            )
        )
    return _CLEAN_ROOM_AUDIT_CACHE


def _get_default_audit():
    global _DEFAULT_AUDIT_CACHE
    if _DEFAULT_AUDIT_CACHE is None:
        _DEFAULT_AUDIT_CACHE = (
            p217.run_phase217_realhw_filesettings_shotmark_tcregen_reclamp_hil()
        )
    return _DEFAULT_AUDIT_CACHE


def _get_clean_room_suite():
    global _CLEAN_SUITE_CACHE, _CLEAN_SUITE_ELAPSED
    if _CLEAN_SUITE_CACHE is None:
        t0 = time.monotonic()
        _CLEAN_SUITE_CACHE = suite.run_fx3_vm_coemulation_suite(
            suite.CoEmulationConfig(force_clean_room=True)
        )
        _CLEAN_SUITE_ELAPSED = time.monotonic() - t0
    return _CLEAN_SUITE_CACHE, float(_CLEAN_SUITE_ELAPSED)


def _get_default_suite():
    global _DEFAULT_SUITE_CACHE, _DEFAULT_SUITE_ELAPSED
    if _DEFAULT_SUITE_CACHE is None:
        t0 = time.monotonic()
        _DEFAULT_SUITE_CACHE = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig())
        _DEFAULT_SUITE_ELAPSED = time.monotonic() - t0
    return _DEFAULT_SUITE_CACHE, float(_DEFAULT_SUITE_ELAPSED)


class TestPhase217FileSettingsShotMarkTcRegenRecLampCoEmulator(unittest.TestCase):
    def test_01_schema_version_stage_39_milestone_and_redline_constants(self) -> None:
        self.assertEqual(
            p217.PHASE_217_SCHEMA,
            "phase217_realhw_filesettings_shotmark_tcregen_reclamp_coemulator_v1",
        )
        self.assertEqual(p217.PHASE_217_VERSION, "217.0.0")
        self.assertEqual(p217.STAGE_INDEX, 39)
        self.assertEqual(p217.STAGE_TOTAL, 39)
        self.assertEqual(p217.MILESTONE_LABEL, "39/39")
        self.assertEqual(
            p217.STAGE_NAME,
            "stage39_realhw_filesettings_shotmark_tcregen_reclamp_hil",
        )
        self.assertEqual(p217.FX3_MODEL_ID, 0x91030080)
        self.assertTrue(p217.P8_CP_MUTATION_FORBIDDEN)
        self.assertFalse(p217.PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(p217.SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(p217.EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        self.assertEqual(p217.PHYSICAL_USB_PACKETS_EMITTED, 0)
        self.assertEqual(p217.OTP_FUSE_TOUCHES, 0)
        self.assertEqual(p217.RPMB_COUNTER_INCREMENTS, 0)
        self.assertEqual(p217.SDHC_NON_STANDARD_FILENAME_OR_CUSTOM_FOLDER_BYPASSES, 0)
        self.assertEqual(p217.SLOT2_SIMULT_TC_REGENERATE_CONTAMINATION_EVENTS, 0)
        self.assertEqual(p217.DECOUPLED_TOP_REC_BUTTON_VS_REAR_TALLY_MISMATCHES, 0)
        self.assertEqual(p217.RAW_FIRMWARE_BYTES_LEAKED, 0)
        self.assertEqual(p217.DONOR_ACCESS_MODE, "O_RDONLY")

    def test_02_donor_inspection_fast_bounded_and_cached(self) -> None:
        p217._DONOR_AUDIT_CACHE.clear()
        t0 = time.monotonic()
        da1 = p217.inspect_phase217_donors(force_clean_room=False)
        dt1 = time.monotonic() - t0
        t1 = time.monotonic()
        da2 = p217.inspect_phase217_donors(force_clean_room=False)
        dt2 = time.monotonic() - t1
        self.assertLess(dt1, 0.05)
        self.assertLess(dt2, 0.01)
        self.assertEqual(da1.donor_files_inspected, 12)
        self.assertEqual(da1.raw_firmware_bytes_leaked, 0)
        self.assertTrue(da1.all_contracts_verified)
        self.assertEqual(da1.errors, ())
        if da1.source_mode == "LOCAL_DONOR_RDONLY":
            self.assertIs(da1, da2)

    def test_03_clean_room_donor_fallback_via_flag_and_env(self) -> None:
        da_flag = p217.inspect_phase217_donors(force_clean_room=True)
        self.assertEqual(da_flag.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(da_flag.access_mode, "O_RDONLY")
        self.assertEqual(da_flag.donor_files_inspected, 12)
        self.assertEqual(da_flag.raw_firmware_bytes_leaked, 0)
        self.assertTrue(da_flag.all_contracts_verified)

        da_env = p217.inspect_phase217_donors(env={"FX3_FX6_FORCE_CLEAN_ROOM": "1"})
        self.assertEqual(da_env.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertIs(da_env, da_flag)

    def test_04_clean_room_sentinel_paths_do_not_touch_local_donors(self) -> None:
        paths_clean = p217.resolve_phase217_donor_paths(env={"FX3_FX6_FORCE_CLEAN_ROOM": "1"})
        self.assertEqual(len(paths_clean), 12)
        for p in paths_clean.values():
            self.assertIn(p217.CLEAN_ROOM_SENTINEL_DIRNAME, str(p))
            self.assertFalse(p.exists())
        da = p217.inspect_phase217_donors(env={"FX3_FX6_FORCE_CLEAN_ROOM": "1"})
        self.assertEqual(da.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(da.all_contracts_verified)
        self.assertEqual(da.raw_firmware_bytes_leaked, 0)

    def test_05_twelve_donors_expected_sizes_and_bounded_windows(self) -> None:
        da = p217.inspect_phase217_donors()
        self.assertEqual(da.fx3_lens_comm.file_bytes, 14_544)
        self.assertEqual(da.fx6_lens_comm.file_bytes, 14_544)
        self.assertEqual(da.fx3_media_cfg.file_bytes, 52_312)
        self.assertEqual(da.fx3_adj_media.file_bytes, 318_152)
        self.assertEqual(da.fx3_string_en_f.file_bytes, 373_820)
        self.assertEqual(da.fx6_string_en.file_bytes, 118_208)
        self.assertEqual(da.fx3_appfw.file_bytes, 79_015_712)
        self.assertEqual(da.fx6_appfw.file_bytes, 50_520_424)
        self.assertEqual(da.fx3_cpapp.file_bytes, 15_980_568)
        self.assertEqual(da.fx6_cpapp.file_bytes, 17_952_816)
        self.assertEqual(da.fx3_libmpr.file_bytes, 3_517_008)
        self.assertEqual(da.fx6_libmpr.file_bytes, 28_921_824)
        for key, large in (
            ("fx3_appfw", da.fx3_appfw),
            ("fx6_appfw", da.fx6_appfw),
            ("fx3_cpapp", da.fx3_cpapp),
            ("fx6_cpapp", da.fx6_cpapp),
            ("fx3_libmpr", da.fx3_libmpr),
            ("fx6_libmpr", da.fx6_libmpr),
        ):
            self.assertTrue(large.bounded_windows_only, msg=key)
            self.assertLessEqual(
                large.bytes_read_total,
                (len(p217.LARGE_DONOR_WINDOWS[key]) + 1) * p217.BOUNDED_WINDOW_MAX_BYTES,
                msg=key,
            )

    def test_06_donor_wave29_menu_and_symbol_proofs(self) -> None:
        da = p217.inspect_phase217_donors()
        self.assertTrue(da.file_settings_sdhc_and_shotmark_proven)
        self.assertTrue(da.tc_regenerate_slot1_and_extlk_proven)
        self.assertTrue(da.rec_lamp_coupled_tally_and_silent_audio_proven)
        hits = da.fx3_string_en_f.marker_hits
        for token in (
            "File Settings",
            "File Name Format",
            "Title Name Settings",
            "Cam ID + Reel#",
            "Shot Mark",
            "Add Shot Mark1",
            "Add Shot Mark2",
            "Image Jump Setting",
            "Only Shot Mark Mov.",
            "Time Code Make",
            "Regenerate",
            "Time Code Output",
            "REC Lamp",
            "Only Front Off",
            "Silent Mode",
        ):
            self.assertEqual(hits.get(token), 1, msg=token)
        self.assertEqual(da.fx3_appfw.window_hits.get("REGENERATE"), 1)
        self.assertEqual(da.fx3_appfw.window_hits.get("REC_LAMP"), 1)
        self.assertEqual(da.fx3_appfw.window_hits.get("SILENT_MODE"), 1)
        self.assertEqual(da.fx3_libmpr.window_hits.get("NON_REAL_TIME_META"), 1)
        self.assertEqual(da.fx3_libmpr.window_hits.get("LTC_CHANGE_TABLE"), 1)

    def test_07_submodel_a_all_five_file_name_formats_across_simult_slots(self) -> None:
        std = p217.probe_file_settings_sdhc_lock_and_shotmark_hil(
            recording_media="Simult. Recording",
            requested_file_name_format=p217.FMT_STANDARD,
            prior_series_counter=4,
        )
        self.assertTrue(std.admitted)
        self.assertEqual(std.clip_filename, "C0005.MP4")
        self.assertEqual(
            std.active_slot_clip_paths,
            (
                "/mnt/slot1/PRIVATE/M4ROOT/CLIP/C0005.MP4",
                "/mnt/slot2/PRIVATE/M4ROOT/CLIP/C0005.MP4",
            ),
        )
        self.assertEqual(std.sidecar_xml_path, "/PRIVATE/M4ROOT/CLIP/C0005M01.XML")

        cam_reel = p217.probe_file_settings_sdhc_lock_and_shotmark_hil(
            requested_file_name_format=p217.FMT_CAM_ID_REEL,
            camera_id="B",
            reel_number=7,
            date_yyyymmdd="20261115",
            camera_uid4="FX3B",
            prior_series_counter=0,
        )
        self.assertTrue(cam_reel.admitted)
        self.assertEqual(cam_reel.clip_filename, "B007C0001_261115_FX3B.MP4")

        title_only = p217.probe_file_settings_sdhc_lock_and_shotmark_hil(
            requested_file_name_format=p217.FMT_TITLE,
            title_name="DOC_UNIT1",
            prior_series_counter=9,
        )
        self.assertTrue(title_only.admitted)
        self.assertEqual(title_only.clip_filename, "DOC_UNIT10010.MP4")

        date_title = p217.probe_file_settings_sdhc_lock_and_shotmark_hil(
            requested_file_name_format=p217.FMT_DATE_PLUS_TITLE,
            title_name="SCENE2",
            date_yyyymmdd="20261115",
            prior_series_counter=1,
        )
        self.assertTrue(date_title.admitted)
        self.assertEqual(date_title.clip_filename, "20261115_SCENE20002.MP4")

        title_date = p217.probe_file_settings_sdhc_lock_and_shotmark_hil(
            requested_file_name_format=p217.FMT_TITLE_PLUS_DATE,
            title_name="SCENE2",
            date_yyyymmdd="20261115",
            prior_series_counter=1,
        )
        self.assertTrue(title_date.admitted)
        self.assertEqual(title_date.clip_filename, "SCENE2_20261115_0002.MP4")

    def test_08_submodel_a_file_number_series_vs_reset_and_series_counter_reset(self) -> None:
        # Series carries across formatted empty card
        series_carry = p217.probe_file_settings_sdhc_lock_and_shotmark_hil(
            file_number_mode="Series",
            prior_series_counter=42,
            max_existing_clip_num_on_card=0,
        )
        self.assertEqual(series_carry.assigned_clip_number, 43)
        self.assertEqual(series_carry.next_series_counter, 43)

        # Series jumps above higher existing clip on swapped card
        series_jump = p217.probe_file_settings_sdhc_lock_and_shotmark_hil(
            file_number_mode="Series",
            prior_series_counter=12,
            max_existing_clip_num_on_card=80,
        )
        self.assertEqual(series_jump.assigned_clip_number, 81)
        self.assertEqual(series_jump.next_series_counter, 81)

        # Reset restarts at 0001 on empty card
        reset_empty = p217.probe_file_settings_sdhc_lock_and_shotmark_hil(
            file_number_mode="Reset",
            prior_series_counter=42,
            max_existing_clip_num_on_card=0,
        )
        self.assertEqual(reset_empty.assigned_clip_number, 1)
        self.assertEqual(reset_empty.clip_filename, "C0001.MP4")

        # Series Counter Reset restarts at 0001 on empty card and updates series counter
        series_rst = p217.probe_file_settings_sdhc_lock_and_shotmark_hil(
            file_number_mode="Series",
            series_counter_reset=True,
            prior_series_counter=99,
            max_existing_clip_num_on_card=0,
        )
        self.assertEqual(series_rst.assigned_clip_number, 1)
        self.assertEqual(series_rst.next_series_counter, 1)

        # Rollover past 9999 wraps to 0001
        wrap_9999 = p217.probe_file_settings_sdhc_lock_and_shotmark_hil(
            file_number_mode="Series",
            prior_series_counter=9999,
        )
        self.assertEqual(wrap_9999.assigned_clip_number, 1)

    def test_09_submodel_a_title_name_37_char_allowed_ascii_set_exact_boundary(self) -> None:
        self.assertEqual(len(p217.TITLE_NAME_ALLOWED_ASCII), 26 + 26 + 10 + 18)
        title_37 = "Az09.-_@!#$%+=^~(),;[]BCDEFGHIJKLMNOP"
        self.assertEqual(len(title_37), 37)
        ok, reason = p217.validate_title_name_ascii(title_37)
        self.assertTrue(ok, msg=reason)
        res = p217.probe_file_settings_sdhc_lock_and_shotmark_hil(
            requested_file_name_format=p217.FMT_TITLE,
            title_name=title_37,
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.title_char_length, 37)
        self.assertEqual(res.clip_filename, f"{title_37}0001.MP4")

    def test_10_submodel_a_title_name_rejects_empty_38char_and_disallowed_symbols(self) -> None:
        empty_res = p217.probe_file_settings_sdhc_lock_and_shotmark_hil(
            requested_file_name_format=p217.FMT_TITLE,
            title_name="",
        )
        self.assertFalse(empty_res.admitted)
        self.assertEqual(empty_res.errno_code, p217.EINVAL_ERRNO)

        over_38 = p217.probe_file_settings_sdhc_lock_and_shotmark_hil(
            requested_file_name_format=p217.FMT_TITLE,
            title_name=("X" * 38),
        )
        self.assertFalse(over_38.admitted)
        self.assertEqual(over_38.errno_code, p217.EINVAL_ERRNO)

        for bad_ch in (" ", "/", "\\", ":", "*", "?", '"', "<", ">", "|", "&", "{", "}", "\u65e5"):
            bad = p217.probe_file_settings_sdhc_lock_and_shotmark_hil(
                requested_file_name_format=p217.FMT_TITLE,
                title_name=f"CLIP{bad_ch}A",
            )
            self.assertFalse(bad.admitted, msg=repr(bad_ch))
            self.assertEqual(bad.errno_code, p217.EINVAL_ERRNO)

    def test_11_submodel_a_sdhc_le_32gb_forces_standard_format_and_blocks_unlock_bypass(self) -> None:
        # Slot 2 SDHC 32GB forces [Standard] even if [Cam ID + Reel#] requested
        sdhc_s2 = p217.probe_file_settings_sdhc_lock_and_shotmark_hil(
            recording_media="Slot 2",
            slot2_card_type="SDHC",
            slot2_capacity_gb=32,
            requested_file_name_format=p217.FMT_CAM_ID_REEL,
        )
        self.assertTrue(sdhc_s2.admitted)
        self.assertTrue(sdhc_s2.sdhc_forced_standard_lock)
        self.assertEqual(sdhc_s2.effective_file_name_format, p217.FMT_STANDARD)
        self.assertEqual(sdhc_s2.clip_filename, "C0001.MP4")

        # Simult. Recording with Slot 1 CFexpress + Slot 2 SDHC also locks to [Standard]
        sdhc_sim = p217.probe_file_settings_sdhc_lock_and_shotmark_hil(
            recording_media="Simult. Recording",
            slot1_card_type="CFexpress Type A",
            slot1_capacity_gb=160,
            slot2_card_type="SDHC",
            slot2_capacity_gb=16,
            requested_file_name_format=p217.FMT_TITLE_PLUS_DATE,
            title_name="REEL_A",
        )
        self.assertTrue(sdhc_sim.admitted)
        self.assertTrue(sdhc_sim.sdhc_forced_standard_lock)
        self.assertEqual(sdhc_sim.effective_file_name_format, p217.FMT_STANDARD)

        # Inactive SDHC in Slot 2 while recording to Slot 1 CFexpress does NOT lock Slot 1
        s1_only = p217.probe_file_settings_sdhc_lock_and_shotmark_hil(
            recording_media="Slot 1",
            slot1_card_type="CFexpress Type A",
            slot1_capacity_gb=160,
            slot2_card_type="SDHC",
            slot2_capacity_gb=32,
            requested_file_name_format=p217.FMT_TITLE,
            title_name="S1_CFE",
        )
        self.assertTrue(s1_only.admitted)
        self.assertFalse(s1_only.sdhc_forced_standard_lock)
        self.assertEqual(s1_only.effective_file_name_format, p217.FMT_TITLE)
        self.assertEqual(s1_only.clip_filename, "S1_CFE0001.MP4")

        # Explicit attempt to bypass SDHC [Standard] lock fails closed (EOPNOTSUPP)
        bypass = p217.probe_file_settings_sdhc_lock_and_shotmark_hil(
            recording_media="Slot 1",
            slot1_card_type="SDHC",
            slot1_capacity_gb=16,
            requested_file_name_format=p217.FMT_TITLE,
            title_name="BYPASS",
            attempt_unlock_non_standard_on_sdhc=True,
        )
        self.assertFalse(bypass.admitted)
        self.assertTrue(bypass.sdhc_forced_standard_lock)
        self.assertEqual(bypass.sdhc_non_standard_filename_or_custom_folder_bypasses, 0)
        self.assertEqual(bypass.errno_code, p217.EOPNOTSUPP_ERRNO)

    def test_12_submodel_a_custom_movie_folder_prohibited_and_prior_clips_unrenamed(self) -> None:
        bad_dir = p217.probe_file_settings_sdhc_lock_and_shotmark_hil(
            custom_movie_folder_name="DAY1_MOVIES"
        )
        self.assertFalse(bad_dir.admitted)
        self.assertEqual(bad_dir.movie_folder_path, "/PRIVATE/M4ROOT/CLIP")
        self.assertEqual(bad_dir.sdhc_non_standard_filename_or_custom_folder_bypasses, 0)
        self.assertEqual(bad_dir.errno_code, p217.EOPNOTSUPP_ERRNO)

        prior = ("C0001.MP4", "C0002.MP4")
        after_title_change = p217.probe_file_settings_sdhc_lock_and_shotmark_hil(
            requested_file_name_format=p217.FMT_TITLE,
            title_name="NEW_NAME",
            prior_series_counter=2,
            prior_recorded_clips=prior,
        )
        self.assertTrue(after_title_change.admitted)
        self.assertEqual(after_title_change.prior_recorded_clips, prior)
        self.assertFalse(after_title_change.prior_clips_retroactively_renamed)
        self.assertEqual(after_title_change.clip_filename, "NEW_NAME0003.MP4")

    def test_13_submodel_a_shot_mark1_and_shot_mark2_rec_and_playback_toggle_sidecar_xml(self) -> None:
        # Punch Shot Mark1 @ 24, 96 and Shot Mark2 @ 48 during recording;
        # then toggle-delete 24, toggle-add 144 on Mark1 and toggle-add 200 on Mark2 in playback.
        sm = p217.probe_file_settings_sdhc_lock_and_shotmark_hil(
            rec_shot_mark1_frames=(24, 96),
            rec_shot_mark2_frames=(48,),
            playback_toggle_shot_mark1_frames=(24, 144),
            playback_toggle_shot_mark2_frames=(200,),
            image_jump_setting=p217.JUMP_SHOT_MARK1_ONLY,
            ftp_target_movie_filter=p217.FTP_FILTER_ONLY_SHOT_MARK_MOV,
        )
        self.assertTrue(sm.admitted)
        self.assertEqual(sm.shot_mark1_frames, (96, 144))
        self.assertEqual(sm.shot_mark2_frames, (48, 200))
        self.assertTrue(sm.has_shot_mark1)
        self.assertTrue(sm.has_shot_mark2)
        self.assertTrue(sm.has_any_shot_mark)
        self.assertIn('type="ShotMark1" frame="96"', sm.sidecar_xml_excerpt)
        self.assertIn('type="ShotMark2" frame="200"', sm.sidecar_xml_excerpt)
        self.assertNotIn('frame="24"', sm.sidecar_xml_excerpt)
        self.assertTrue(sm.clip_matched_by_image_jump)
        self.assertTrue(sm.clip_selected_for_ftp_transfer)

    def test_14_submodel_a_image_jump_setting_four_modes_and_ftp_shot_mark_filters(self) -> None:
        clips = (
            ("C0001.MP4", False, False),
            ("C0002.MP4", True, False),
            ("C0003.MP4", False, True),
            ("C0004.MP4", True, True),
        )
        r_any = p217.evaluate_shot_mark_jump_and_ftp_filter(
            clips,
            image_jump_setting=p217.JUMP_SHOT_MARK_ONLY,
            ftp_target_movie_filter=p217.FTP_FILTER_ONLY_SHOT_MARK_MOV,
        )
        self.assertEqual(r_any["image_jump_matched_clips"], ("C0002.MP4", "C0003.MP4", "C0004.MP4"))
        self.assertEqual(
            r_any["ftp_transfer_selected_clips"], ("C0002.MP4", "C0003.MP4", "C0004.MP4")
        )

        r_m1 = p217.evaluate_shot_mark_jump_and_ftp_filter(
            clips,
            image_jump_setting=p217.JUMP_SHOT_MARK1_ONLY,
            ftp_target_movie_filter=p217.FTP_FILTER_ONLY_SHOT_MARK,
        )
        self.assertEqual(r_m1["image_jump_matched_clips"], ("C0002.MP4", "C0004.MP4"))
        self.assertEqual(
            r_m1["ftp_transfer_selected_clips"], ("C0002.MP4", "C0003.MP4", "C0004.MP4")
        )

        r_m2 = p217.evaluate_shot_mark_jump_and_ftp_filter(
            clips,
            image_jump_setting=p217.JUMP_SHOT_MARK2_ONLY,
            ftp_target_movie_filter=p217.FTP_FILTER_ALL,
        )
        self.assertEqual(r_m2["image_jump_matched_clips"], ("C0003.MP4", "C0004.MP4"))
        self.assertEqual(
            r_m2["ftp_transfer_selected_clips"],
            ("C0001.MP4", "C0002.MP4", "C0003.MP4", "C0004.MP4"),
        )

        r_none = p217.evaluate_shot_mark_jump_and_ftp_filter(
            clips,
            image_jump_setting=p217.JUMP_NO_SHOT_MARK,
        )
        self.assertEqual(r_none["image_jump_matched_clips"], ("C0001.MP4",))

    def test_15_submodel_a_validation_errors_for_invalid_capacity_format_camid_reel(self) -> None:
        bad_fmt = p217.probe_file_settings_sdhc_lock_and_shotmark_hil(
            requested_file_name_format="MXF_UMID"
        )
        self.assertFalse(bad_fmt.admitted)
        self.assertEqual(bad_fmt.errno_code, p217.EINVAL_ERRNO)

        bad_sdhc_cap = p217.probe_file_settings_sdhc_lock_and_shotmark_hil(
            slot1_card_type="SDHC",
            slot1_capacity_gb=64,
        )
        self.assertFalse(bad_sdhc_cap.admitted)
        self.assertEqual(bad_sdhc_cap.errno_code, p217.EINVAL_ERRNO)

        bad_sdxc_cap = p217.probe_file_settings_sdhc_lock_and_shotmark_hil(
            slot2_card_type="SDXC",
            slot2_capacity_gb=32,
        )
        self.assertFalse(bad_sdxc_cap.admitted)
        self.assertEqual(bad_sdxc_cap.errno_code, p217.EINVAL_ERRNO)

        bad_camid = p217.probe_file_settings_sdhc_lock_and_shotmark_hil(camera_id="a1")
        self.assertFalse(bad_camid.admitted)
        self.assertEqual(bad_camid.errno_code, p217.EINVAL_ERRNO)

        bad_reel = p217.probe_file_settings_sdhc_lock_and_shotmark_hil(reel_number=1000)
        self.assertFalse(bad_reel.admitted)
        self.assertEqual(bad_reel.errno_code, p217.EINVAL_ERRNO)

        with self.assertRaises(p217.RealHwFileSettingsShotMarkTcRegenRecLampError):
            p217.probe_file_settings_sdhc_lock_and_shotmark_hil(recording_media="Slot 3")
        with self.assertRaises(p217.RealHwFileSettingsShotMarkTcRegenRecLampError):
            p217.probe_file_settings_sdhc_lock_and_shotmark_hil(
                playback_toggle_shot_mark1_frames=(-1,)
            )

    def test_16_pillar_a_evaluator_matrix_passes_100pct(self) -> None:
        pa = p217.evaluate_pillar_a_file_settings_sdhc_and_shotmark_hil()
        self.assertTrue(pa["passed"])
        self.assertEqual(len(pa["five_mode_filename_matrix"]), 5)
        self.assertEqual(
            pa["sdhc_32gb_forced_standard_lock"]["effective_file_name_format"],
            p217.FMT_STANDARD,
        )

    def test_17_submodel_b_smpte_tc_parse_format_roundtrip_and_24h_wrap(self) -> None:
        f24 = p217.parse_smpte_tc("01:02:03:04", 24)
        self.assertEqual(p217.format_smpte_tc(f24, 24), "01:02:03:04")
        # 23:59:59:23 + 1 frame wraps to 00:00:00:00
        end_day = p217.parse_smpte_tc("23:59:59:23", 24)
        self.assertEqual(p217.format_smpte_tc(end_day + 1, 24), "00:00:00:00")
        with self.assertRaises(ValueError):
            p217.parse_smpte_tc("01:00:00:24", 24)
        with self.assertRaises(ValueError):
            p217.parse_smpte_tc("25:00:00:00", 24)

    def test_18_submodel_b_regenerate_single_slot1_vs_slot2_active_read(self) -> None:
        s1 = p217.probe_tc_regenerate_slot1_extlk_and_sq_hil(
            recording_media="Slot 1",
            time_code_make=p217.TC_MAKE_REGENERATE,
            requested_time_code_run=p217.TC_RUN_FREE_RUN,
            nominal_fps=24,
            slot1_last_end_tc="03:10:00:06",
            slot2_last_end_tc="11:22:33:12",
            standby_frames=500,
            record_frames=18,
        )
        self.assertTrue(s1.admitted)
        self.assertEqual(s1.regenerate_reference_slot, "Slot 1")
        self.assertFalse(s1.slot2_simult_tc_ignored)
        self.assertEqual(s1.effective_time_code_run, p217.TC_RUN_REC_RUN)
        self.assertTrue(s1.forced_rec_run_under_regenerate)
        self.assertEqual(s1.clip_start_tc, "03:10:00:06")
        self.assertEqual(s1.clip_end_tc, "03:10:01:00")

        s2 = p217.probe_tc_regenerate_slot1_extlk_and_sq_hil(
            recording_media="Slot 2",
            time_code_make=p217.TC_MAKE_REGENERATE,
            requested_time_code_run=p217.TC_RUN_FREE_RUN,
            nominal_fps=24,
            slot1_last_end_tc="03:10:00:06",
            slot2_last_end_tc="11:22:33:12",
            standby_frames=500,
            record_frames=12,
        )
        self.assertTrue(s2.admitted)
        self.assertEqual(s2.regenerate_reference_slot, "Slot 2")
        self.assertEqual(s2.clip_start_tc, "11:22:33:12")
        self.assertEqual(s2.clip_end_tc, "11:22:34:00")

    def test_19_submodel_b_simult_recording_regenerate_reads_exclusively_slot1(self) -> None:
        sim = p217.probe_tc_regenerate_slot1_extlk_and_sq_hil(
            recording_media="Simult. Recording",
            time_code_make=p217.TC_MAKE_REGENERATE,
            requested_time_code_run=p217.TC_RUN_FREE_RUN,
            nominal_fps=30,
            slot1_last_end_tc="04:00:10:15",
            slot2_last_end_tc="19:59:59:29",
            standby_frames=900,
            record_frames=45,
        )
        self.assertTrue(sim.admitted)
        self.assertEqual(sim.regenerate_reference_slot, "Slot 1")
        self.assertTrue(sim.slot2_simult_tc_ignored)
        self.assertEqual(sim.effective_time_code_run, p217.TC_RUN_REC_RUN)
        self.assertEqual(sim.clip_start_tc, "04:00:10:15")
        self.assertEqual(sim.clip_end_tc, "04:00:12:00")
        self.assertEqual(sim.slot2_simult_tc_regenerate_contamination_events, 0)

        blk = p217.probe_tc_regenerate_slot1_extlk_and_sq_hil(
            recording_media="Simult. Recording",
            attempt_slot2_simult_regenerate_override=True,
        )
        self.assertFalse(blk.admitted)
        self.assertEqual(blk.slot2_simult_tc_regenerate_contamination_events, 0)
        self.assertEqual(blk.errno_code, p217.EOPNOTSUPP_ERRNO)

    def test_20_submodel_b_preset_rec_run_vs_free_run_advances_standby_frames(self) -> None:
        rec_run = p217.probe_tc_regenerate_slot1_extlk_and_sq_hil(
            time_code_make=p217.TC_MAKE_PRESET,
            requested_time_code_run=p217.TC_RUN_REC_RUN,
            nominal_fps=25,
            preset_tc="01:00:00:00",
            standby_frames=250,
            record_frames=50,
        )
        self.assertEqual(rec_run.clip_start_tc, "01:00:00:00")
        self.assertEqual(rec_run.clip_end_tc, "01:00:02:00")

        free_run = p217.probe_tc_regenerate_slot1_extlk_and_sq_hil(
            time_code_make=p217.TC_MAKE_PRESET,
            requested_time_code_run=p217.TC_RUN_FREE_RUN,
            nominal_fps=25,
            preset_tc="01:00:00:00",
            standby_frames=250,
            record_frames=50,
        )
        self.assertEqual(free_run.clip_start_tc, "01:00:10:00")
        self.assertEqual(free_run.clip_end_tc, "01:00:12:00")

    def test_21_submodel_b_vmc_bncm1_ext_lk_requires_movie_preset_freerun_and_10s_hold(self) -> None:
        locked = p217.probe_tc_regenerate_slot1_extlk_and_sq_hil(
            capture_mode="Movie",
            time_code_make=p217.TC_MAKE_PRESET,
            requested_time_code_run=p217.TC_RUN_FREE_RUN,
            nominal_fps=24,
            vmc_bncm1_attached=True,
            sync_hold_seconds=10.0,
            external_ltc_tc="12:30:00:00",
            standby_frames=24,
            record_frames=24,
            requested_hdmi_time_code_output="On",
        )
        self.assertTrue(locked.admitted)
        self.assertTrue(locked.ext_lk_active)
        self.assertFalse(locked.ext_lk_released)
        self.assertEqual(locked.tc_status_badge, "EXT-LK")
        self.assertEqual(locked.clip_start_tc, "12:30:01:00")
        self.assertTrue(locked.hdmi_tc_packet_stream_active)

        under_10s = p217.probe_tc_regenerate_slot1_extlk_and_sq_hil(
            capture_mode="Movie",
            time_code_make=p217.TC_MAKE_PRESET,
            requested_time_code_run=p217.TC_RUN_FREE_RUN,
            vmc_bncm1_attached=True,
            sync_hold_seconds=9.5,
        )
        self.assertFalse(under_10s.ext_lk_active)
        self.assertEqual(under_10s.tc_status_badge, "INT")

    def test_22_submodel_b_ext_lk_immediately_releases_on_tc_make_tc_run_mode_or_unplug(self) -> None:
        drop_make = p217.probe_tc_regenerate_slot1_extlk_and_sq_hil(
            capture_mode="Movie",
            time_code_make=p217.TC_MAKE_REGENERATE,
            requested_time_code_run=p217.TC_RUN_FREE_RUN,
            vmc_bncm1_attached=True,
            sync_hold_seconds=15.0,
            prior_ext_lk_locked=True,
        )
        self.assertFalse(drop_make.ext_lk_active)
        self.assertTrue(drop_make.ext_lk_released)
        self.assertIn("TIME_CODE_MAKE_CHANGED_FROM_PRESET", drop_make.ext_lk_release_reasons)

        drop_run = p217.probe_tc_regenerate_slot1_extlk_and_sq_hil(
            capture_mode="Movie",
            time_code_make=p217.TC_MAKE_PRESET,
            requested_time_code_run=p217.TC_RUN_REC_RUN,
            vmc_bncm1_attached=True,
            sync_hold_seconds=15.0,
            prior_ext_lk_locked=True,
        )
        self.assertFalse(drop_run.ext_lk_active)
        self.assertTrue(drop_run.ext_lk_released)
        self.assertIn("TIME_CODE_RUN_CHANGED_FROM_FREE_RUN", drop_run.ext_lk_release_reasons)

        drop_unplug = p217.probe_tc_regenerate_slot1_extlk_and_sq_hil(
            capture_mode="Movie",
            time_code_make=p217.TC_MAKE_PRESET,
            requested_time_code_run=p217.TC_RUN_FREE_RUN,
            vmc_bncm1_attached=False,
            prior_ext_lk_locked=True,
        )
        self.assertTrue(drop_unplug.ext_lk_released)
        self.assertIn("VMC_BNCM1_DISCONNECTED", drop_unplug.ext_lk_release_reasons)

    def test_23_submodel_b_sq_mode_blocks_tc_run_and_hdmi_time_code_output(self) -> None:
        sq_state = p217.probe_tc_regenerate_slot1_extlk_and_sq_hil(
            capture_mode="S&Q",
            time_code_make=p217.TC_MAKE_PRESET,
            requested_time_code_run=p217.TC_RUN_FREE_RUN,
            requested_hdmi_time_code_output="On",
            vmc_bncm1_attached=True,
            sync_hold_seconds=15.0,
            prior_ext_lk_locked=True,
            standby_frames=300,
            record_frames=24,
        )
        self.assertTrue(sq_state.admitted)
        self.assertFalse(sq_state.time_code_run_menu_available)
        self.assertEqual(sq_state.effective_time_code_run, p217.TC_RUN_REC_RUN)
        self.assertFalse(sq_state.hdmi_time_code_output_available)
        self.assertEqual(sq_state.effective_hdmi_time_code_output, "Off")
        self.assertFalse(sq_state.hdmi_tc_packet_stream_active)
        self.assertTrue(sq_state.ext_lk_released)
        self.assertIn("CAPTURE_MODE_NOT_MOVIE", sq_state.ext_lk_release_reasons)

        blk_run = p217.probe_tc_regenerate_slot1_extlk_and_sq_hil(
            capture_mode="S&Q",
            attempt_change_tc_run_in_sq=True,
        )
        self.assertFalse(blk_run.admitted)
        self.assertEqual(blk_run.errno_code, p217.EOPNOTSUPP_ERRNO)

        blk_hdmi = p217.probe_tc_regenerate_slot1_extlk_and_sq_hil(
            capture_mode="S&Q",
            attempt_enable_hdmi_tc_out_in_sq=True,
        )
        self.assertFalse(blk_hdmi.admitted)
        self.assertEqual(blk_hdmi.errno_code, p217.EOPNOTSUPP_ERRNO)

    def test_24_submodel_b_invalid_tc_make_tc_run_malformed_tc_and_arg_errors(self) -> None:
        bad_make = p217.probe_tc_regenerate_slot1_extlk_and_sq_hil(time_code_make="JamSync")
        self.assertFalse(bad_make.admitted)
        self.assertEqual(bad_make.errno_code, p217.EINVAL_ERRNO)

        bad_run = p217.probe_tc_regenerate_slot1_extlk_and_sq_hil(
            requested_time_code_run="TimeOfDay"
        )
        self.assertFalse(bad_run.admitted)
        self.assertEqual(bad_run.errno_code, p217.EINVAL_ERRNO)

        bad_tc = p217.probe_tc_regenerate_slot1_extlk_and_sq_hil(slot1_last_end_tc="99:99:99:99")
        self.assertFalse(bad_tc.admitted)
        self.assertEqual(bad_tc.errno_code, p217.EINVAL_ERRNO)

        with self.assertRaises(p217.RealHwFileSettingsShotMarkTcRegenRecLampError):
            p217.probe_tc_regenerate_slot1_extlk_and_sq_hil(nominal_fps=48)
        with self.assertRaises(p217.RealHwFileSettingsShotMarkTcRegenRecLampError):
            p217.probe_tc_regenerate_slot1_extlk_and_sq_hil(standby_frames=-5)

    def test_25_pillar_b_evaluator_matrix_passes_100pct(self) -> None:
        pb = p217.evaluate_pillar_b_tc_regenerate_slot1_extlk_and_sq_hil()
        self.assertTrue(pb["passed"])
        self.assertEqual(
            pb["simult_slot1_exclusive_regenerate"]["regenerate_reference_slot"],
            "Slot 1",
        )

    def test_26_submodel_c_rec_lamp_all_on_lights_front_rear_and_top_rec_button(self) -> None:
        all_on = p217.probe_rec_lamp_coupled_tally_and_silent_audio_hil(
            rec_lamp_mode=p217.REC_LAMP_ALL_ON,
            is_recording=True,
        )
        self.assertTrue(all_on.admitted)
        self.assertTrue(all_on.front_tally_led_on)
        self.assertTrue(all_on.rear_tally_led_on)
        self.assertTrue(all_on.top_rec_button_led_on)
        self.assertTrue(all_on.rear_and_top_rec_button_coupled)

        standby = p217.probe_rec_lamp_coupled_tally_and_silent_audio_hil(
            rec_lamp_mode=p217.REC_LAMP_ALL_ON,
            is_recording=False,
        )
        self.assertFalse(standby.front_tally_led_on)
        self.assertFalse(standby.rear_tally_led_on)
        self.assertFalse(standby.top_rec_button_led_on)

    def test_27_submodel_c_only_front_off_keeps_both_rear_and_top_rec_button_lit(self) -> None:
        front_off = p217.probe_rec_lamp_coupled_tally_and_silent_audio_hil(
            rec_lamp_mode=p217.REC_LAMP_ONLY_FRONT_OFF,
            is_recording=True,
        )
        self.assertTrue(front_off.admitted)
        self.assertFalse(front_off.front_tally_led_on)
        self.assertTrue(front_off.rear_tally_led_on)
        self.assertTrue(front_off.top_rec_button_led_on)
        self.assertTrue(front_off.rear_and_top_rec_button_coupled)
        self.assertEqual(front_off.decoupled_top_rec_button_vs_rear_tally_mismatches, 0)

    def test_28_submodel_c_all_off_extinguishes_leds_while_emphasized_rec_display_independent(self) -> None:
        # HDMI Info. Display = Off -> red frame on LCD, clean HDMI
        all_off_lcd = p217.probe_rec_lamp_coupled_tally_and_silent_audio_hil(
            rec_lamp_mode=p217.REC_LAMP_ALL_OFF,
            is_recording=True,
            emphasized_rec_display="On",
            hdmi_info_display="Off",
        )
        self.assertTrue(all_off_lcd.admitted)
        self.assertFalse(all_off_lcd.front_tally_led_on)
        self.assertFalse(all_off_lcd.rear_tally_led_on)
        self.assertFalse(all_off_lcd.top_rec_button_led_on)
        self.assertTrue(all_off_lcd.lcd_red_rec_frame_active)
        self.assertFalse(all_off_lcd.hdmi_red_rec_frame_active)

        # HDMI Info. Display = On -> red frame exported over HDMI
        all_off_hdmi = p217.probe_rec_lamp_coupled_tally_and_silent_audio_hil(
            rec_lamp_mode=p217.REC_LAMP_ALL_OFF,
            is_recording=True,
            emphasized_rec_display="On",
            hdmi_info_display="On",
        )
        self.assertFalse(all_off_hdmi.lcd_red_rec_frame_active)
        self.assertTrue(all_off_hdmi.hdmi_red_rec_frame_active)

        # Emphasized REC Display = Off -> neither LCD nor HDMI red frame
        no_red = p217.probe_rec_lamp_coupled_tally_and_silent_audio_hil(
            rec_lamp_mode=p217.REC_LAMP_ALL_OFF,
            is_recording=True,
            emphasized_rec_display="Off",
            hdmi_info_display="On",
        )
        self.assertFalse(no_red.lcd_red_rec_frame_active)
        self.assertFalse(no_red.hdmi_red_rec_frame_active)

    def test_29_submodel_c_decouple_top_rec_button_and_fx6_only_rear_modes_rejected(self) -> None:
        decouple = p217.probe_rec_lamp_coupled_tally_and_silent_audio_hil(
            rec_lamp_mode=p217.REC_LAMP_ONLY_FRONT_OFF,
            attempt_decouple_top_rec_button_from_rear=True,
        )
        self.assertFalse(decouple.admitted)
        self.assertEqual(decouple.decoupled_top_rec_button_vs_rear_tally_mismatches, 0)
        self.assertEqual(decouple.errno_code, p217.EOPNOTSUPP_ERRNO)

        for invalid_mode in ("Only Rear Off", "Front Only", "Green Preview"):
            bad = p217.probe_rec_lamp_coupled_tally_and_silent_audio_hil(
                rec_lamp_mode=invalid_mode
            )
            self.assertFalse(bad.admitted, msg=invalid_mode)
            self.assertEqual(bad.errno_code, p217.EINVAL_ERRNO)

    def test_30_submodel_c_silent_mode_locks_audio_signals_off_and_blocks_override(self) -> None:
        normal_beep = p217.probe_rec_lamp_coupled_tally_and_silent_audio_hil(
            silent_mode="Off",
            requested_audio_signals="On",
        )
        self.assertTrue(normal_beep.admitted)
        self.assertEqual(normal_beep.effective_audio_signals, "On")
        self.assertFalse(normal_beep.audio_signals_locked_by_silent_mode)
        self.assertTrue(normal_beep.af_lock_beep_emitted)
        self.assertTrue(normal_beep.self_timer_beep_emitted)

        silent_locked = p217.probe_rec_lamp_coupled_tally_and_silent_audio_hil(
            silent_mode="On",
            requested_audio_signals="On",
        )
        self.assertTrue(silent_locked.admitted)
        self.assertEqual(silent_locked.effective_audio_signals, "Off")
        self.assertTrue(silent_locked.audio_signals_locked_by_silent_mode)
        self.assertFalse(silent_locked.af_lock_beep_emitted)
        self.assertFalse(silent_locked.self_timer_beep_emitted)

        override_blk = p217.probe_rec_lamp_coupled_tally_and_silent_audio_hil(
            silent_mode="On",
            attempt_enable_audio_signals_under_silent_mode=True,
        )
        self.assertFalse(override_blk.admitted)
        self.assertTrue(override_blk.audio_signals_locked_by_silent_mode)
        self.assertEqual(override_blk.errno_code, p217.EOPNOTSUPP_ERRNO)

        with self.assertRaises(p217.RealHwFileSettingsShotMarkTcRegenRecLampError):
            p217.probe_rec_lamp_coupled_tally_and_silent_audio_hil(silent_mode="Auto")

    def test_31_hard_safety_redline_baseline_and_all_9_forbidden_actions(self) -> None:
        base = p217.probe_hard_safety_redline()
        self.assertTrue(base.valid)
        self.assertFalse(base.persistent_emmc_writes_authorized)
        self.assertFalse(base.spi_nor_write_authorized)
        self.assertFalse(base.el3_payload_transmit_authorized)
        self.assertEqual(base.physical_usb_packets_emitted, 0)
        self.assertEqual(base.otp_fuse_touches, 0)
        self.assertEqual(base.rpmb_counter_increments, 0)
        self.assertEqual(base.sdhc_non_standard_filename_or_custom_folder_bypasses, 0)
        self.assertEqual(base.slot2_simult_tc_regenerate_contamination_events, 0)
        self.assertEqual(base.decoupled_top_rec_button_vs_rear_tally_mismatches, 0)

        for flag_name in (
            "authorize_persistent_emmc_writes",
            "authorize_spi_nor_write",
            "authorize_el3_payload_transmit",
            "emit_physical_usb_packet",
            "touch_otp_fuse",
            "increment_rpmb_counter",
            "bypass_sdhc_standard_filename_lock",
            "contaminate_simult_tc_regenerate_from_slot2",
            "decouple_top_rec_button_from_rear_tally",
        ):
            bad = p217.probe_hard_safety_redline(**{flag_name: True})
            self.assertFalse(bad.valid, msg=flag_name)
            self.assertFalse(bad.persistent_emmc_writes_authorized)
            self.assertFalse(bad.spi_nor_write_authorized)
            self.assertFalse(bad.el3_payload_transmit_authorized)
            self.assertEqual(bad.physical_usb_packets_emitted, 0)
            self.assertEqual(bad.otp_fuse_touches, 0)
            self.assertEqual(bad.rpmb_counter_increments, 0)
            self.assertEqual(bad.sdhc_non_standard_filename_or_custom_folder_bypasses, 0)
            self.assertEqual(bad.slot2_simult_tc_regenerate_contamination_events, 0)
            self.assertEqual(bad.decoupled_top_rec_button_vs_rear_tally_mismatches, 0)
            self.assertTrue(bad.status_code.startswith("FAIL_CLOSED_REDLINE_BLOCKED:"))

    def test_32_combined_multi_redline_violation_blocked(self) -> None:
        combo = p217.probe_hard_safety_redline(
            authorize_persistent_emmc_writes=True,
            bypass_sdhc_standard_filename_lock=True,
            contaminate_simult_tc_regenerate_from_slot2=True,
            decouple_top_rec_button_from_rear_tally=True,
        )
        self.assertFalse(combo.valid)
        self.assertIn("PERSISTENT_EMMC_WRITE", combo.blocked_action)
        self.assertIn("SDHC_NON_STANDARD_FILENAME_BYPASS", combo.blocked_action)
        self.assertIn("SLOT2_SIMULT_TC_REGENERATE_CONTAMINATION", combo.blocked_action)
        self.assertIn("DECOUPLED_TOP_REC_BUTTON_TALLY", combo.blocked_action)

    def test_33_pillar_c_d_evaluator_matrix_passes_100pct(self) -> None:
        pcd = p217.evaluate_pillar_c_d_rec_lamp_silent_audio_and_redlines()
        self.assertTrue(pcd["passed"])
        self.assertEqual(len(pcd["blocked_redline_probes"]), 9)

    def test_34_clean_room_audit_deterministic_digest_and_zero_leaks(self) -> None:
        r1 = _get_clean_room_audit()
        r2 = p217.run_phase217_realhw_filesettings_shotmark_tcregen_reclamp_hil(
            force_clean_room=True
        )
        self.assertTrue(r1["all_checks_passed"])
        self.assertEqual(r1["source_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(r1["stage_index"], 39)
        self.assertEqual(r1["stage_total"], 39)
        self.assertEqual(r1["milestone"], "39/39")
        self.assertEqual(r1["audit_digest_sha256"], r2["audit_digest_sha256"])
        self.assertEqual(r1["redlines"]["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(r1["donor_audit"]["raw_firmware_bytes_leaked"], 0)

    def test_35_default_mode_audit_passes_all_pillars_and_redlines(self) -> None:
        rep = _get_default_audit()
        self.assertTrue(rep["all_checks_passed"])
        self.assertIn(rep["source_mode"], ("LOCAL_DONOR_RDONLY", "CLEAN_ROOM_SYNTHETIC"))
        self.assertTrue(rep["pillar_a_file_settings_sdhc_and_shotmark_hil"]["passed"])
        self.assertTrue(rep["pillar_b_tc_regenerate_slot1_extlk_and_sq_hil"]["passed"])
        self.assertTrue(rep["pillar_c_d_rec_lamp_silent_audio_and_redlines"]["passed"])
        self.assertFalse(rep["redlines"]["persistent_emmc_writes_authorized"])
        self.assertFalse(rep["redlines"]["spi_nor_write_authorized"])
        self.assertFalse(rep["redlines"]["el3_payload_transmit_authorized"])
        self.assertEqual(rep["redlines"]["physical_usb_packets_emitted"], 0)
        self.assertEqual(rep["redlines"]["otp_fuse_touches"], 0)
        self.assertEqual(rep["redlines"]["rpmb_counter_increments"], 0)
        self.assertEqual(rep["redlines"]["sdhc_non_standard_filename_or_custom_folder_bypasses"], 0)
        self.assertEqual(rep["redlines"]["slot2_simult_tc_regenerate_contamination_events"], 0)
        self.assertEqual(rep["redlines"]["decoupled_top_rec_button_vs_rear_tally_mismatches"], 0)

    def test_36_standalone_cli_self_test_summary_and_clean_room_json(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        p_sum = subprocess.run(
            [
                "/usr/bin/python3",
                "-B",
                str(
                    FX3_VM_DIR
                    / "realhw_filesettings_shotmark_tcregen_reclamp_coemulator.py"
                ),
                "--self-test",
                "--summary",
            ],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(p_sum.returncode, 0, msg=p_sum.stderr)
        self.assertIn("[PASS] Phase 217 Stage 39 (39/39)", p_sum.stdout)

        p_json = subprocess.run(
            [
                "/usr/bin/python3",
                "-B",
                str(
                    FX3_VM_DIR
                    / "realhw_filesettings_shotmark_tcregen_reclamp_coemulator.py"
                ),
                "--self-test",
                "--clean-room",
                "--json",
            ],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(p_json.returncode, 0, msg=p_json.stderr)
        parsed = json.loads(p_json.stdout)
        self.assertTrue(parsed["all_checks_passed"])
        self.assertEqual(parsed["stage_index"], 39)
        self.assertEqual(parsed["milestone"], "39/39")

    def test_37_inprocess_main_summary_and_clean_room_exit_zero(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = p217.main(["--self-test", "--clean-room", "--summary"])
        self.assertEqual(rc, 0)
        self.assertIn("[PASS] Phase 217 Stage 39 (39/39)", buf.getvalue())

    def test_38_fx3_vm_coemulation_suite_includes_stage39_and_skip_phase217(self) -> None:
        rep_on, _dt = _get_clean_room_suite()
        self.assertTrue(rep_on["all_checks_passed"])
        self.assertIn(
            "stage39_realhw_filesettings_shotmark_tcregen_reclamp_hil",
            rep_on,
        )
        s39 = rep_on["stage39_realhw_filesettings_shotmark_tcregen_reclamp_hil"]
        self.assertTrue(s39["all_checks_passed"])
        self.assertFalse(s39["persistent_emmc_writes_authorized"])
        self.assertFalse(s39["spi_nor_write_authorized"])
        self.assertFalse(s39["el3_payload_transmit_authorized"])
        self.assertEqual(s39["physical_usb_packets_emitted"], 0)
        self.assertEqual(s39["otp_fuse_touches"], 0)
        self.assertEqual(s39["rpmb_counter_increments"], 0)
        self.assertEqual(s39["sdhc_non_standard_filename_or_custom_folder_bypasses"], 0)
        self.assertEqual(s39["slot2_simult_tc_regenerate_contamination_events"], 0)
        self.assertEqual(s39["decoupled_top_rec_button_vs_rear_tally_mismatches"], 0)
        self.assertEqual(s39["raw_firmware_bytes_leaked"], 0)

        stage_keys = [k for k in rep_on if re.match(r"^stage\d+_", k)]
        self.assertGreaterEqual(len(stage_keys), 39)

        rep_skip = suite.run_fx3_vm_coemulation_suite(
            suite.CoEmulationConfig(
                force_clean_room=True,
                include_phase217_realhw_filesettings_shotmark_tcregen_reclamp_hil=False,
            )
        )
        self.assertTrue(rep_skip["all_checks_passed"])
        self.assertNotIn(
            "stage39_realhw_filesettings_shotmark_tcregen_reclamp_hil",
            rep_skip,
        )
        self.assertGreaterEqual(len([k for k in rep_skip if re.match(r"^stage\d+_", k)]), 38)

    def test_39_all_39_of_39_stages_present_and_passing_in_suite(self) -> None:
        rep, _dt = _get_clean_room_suite()
        self.assertTrue(rep["stage1_coldboot_and_bt"]["all_checks_passed"])
        self.assertTrue(rep["stage2_dual_isa_cp_shooting"]["all_checks_passed"])
        self.assertTrue(rep["stage3_soft_gpe_hud_ramfb"]["all_checks_passed"])
        for idx in range(4, 40):
            matches = [k for k in rep if k.startswith(f"stage{idx}_")]
            self.assertEqual(len(matches), 1, msg=f"Missing or duplicate stage{idx}_* key")
            self.assertTrue(rep[matches[0]]["all_checks_passed"], msg=matches[0])

    def test_40_suite_subprocess_summary_and_skip_phase217_flag(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        proc = subprocess.run(
            [
                "/usr/bin/python3",
                "-B",
                str(FX3_VM_DIR / "fx3_vm_coemulation_suite.py"),
                "--clean-room",
                "--summary",
            ],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        self.assertIn(
            "realhw_filesettings_shotmark_tcregen_reclamp_hil=CLEAN_ROOM_SYNTHETIC",
            proc.stdout,
        )

        proc_skip = subprocess.run(
            [
                "/usr/bin/python3",
                "-B",
                str(FX3_VM_DIR / "fx3_vm_coemulation_suite.py"),
                "--clean-room",
                "--skip-phase217",
                "--summary",
            ],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc_skip.returncode, 0, msg=proc_skip.stderr)
        self.assertNotIn(
            "realhw_filesettings_shotmark_tcregen_reclamp_hil=",
            proc_skip.stdout,
        )

    def test_41_suite_39_stages_under_6s_wall_clock_ceiling_and_json_cli(self) -> None:
        rep_clean, dt_clean = _get_clean_room_suite()
        self.assertTrue(rep_clean["all_checks_passed"])
        self.assertGreaterEqual(len([k for k in rep_clean if re.match(r"^stage\d+_", k)]), 39)
        self.assertLess(dt_clean, 6.0)

        rep_def, dt_def = _get_default_suite()
        self.assertTrue(rep_def["all_checks_passed"])
        self.assertGreaterEqual(len([k for k in rep_def if re.match(r"^stage\d+_", k)]), 39)
        self.assertLess(dt_def, 6.0)

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc_json = suite.main(["--clean-room", "--json"])
        self.assertEqual(rc_json, 0)
        parsed = json.loads(buf.getvalue())
        self.assertTrue(parsed["all_checks_passed"])
        self.assertIn(
            "stage39_realhw_filesettings_shotmark_tcregen_reclamp_hil",
            parsed,
        )

    def test_42_source_hygiene_rdonly_only_and_no_forbidden_write_flags_or_ports(self) -> None:
        src = (
            FX3_VM_DIR / "realhw_filesettings_shotmark_tcregen_reclamp_coemulator.py"
        ).read_text(encoding="utf-8")
        self.assertIn("os.O_RDONLY", src)
        self.assertNotIn("O_WR" + "ONLY", src)
        self.assertNotIn("O_RD" + "WR", src)
        self.assertNotIn("87" + "68", src)

    def test_43_is_forced_clean_room_truthy_and_falsy_values(self) -> None:
        for truthy in ("1", "true", "TRUE", "yes", "on", " 1 "):
            self.assertTrue(
                p217.is_forced_clean_room({"FX3_FX6_FORCE_CLEAN_ROOM": truthy}),
                msg=truthy,
            )
        for falsy in ("", "0", "false", "no", "off"):
            self.assertFalse(
                p217.is_forced_clean_room({"FX3_FX6_FORCE_CLEAN_ROOM": falsy}),
                msg=falsy,
            )

    def test_44_missing_work_root_gracefully_falls_back_to_clean_room_synthetic(self) -> None:
        non_existent = str(REPO_ROOT / "work" / "__nonexistent_phase217_donor_root__")
        env_missing = {
            "FX3_FX6_FORCE_CLEAN_ROOM": "0",
            "FX3_FX6_MAC_WORK_ROOT": non_existent,
            "FX3_FX6_MAC_ROOT": non_existent,
            "FX3_FX6_MAIN_LAB_WORK_ROOT": non_existent,
        }
        paths = p217.resolve_phase217_donor_paths(env=env_missing)
        self.assertEqual(len(paths), 12)
        da = p217.inspect_phase217_donors(force_clean_room=True, env=env_missing)
        self.assertEqual(da.source_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_45_shot_mark_jump_and_ftp_filter_rejects_unsupported_modes(self) -> None:
        with self.assertRaises(p217.RealHwFileSettingsShotMarkTcRegenRecLampError):
            p217.evaluate_shot_mark_jump_and_ftp_filter(
                (("C0001.MP4", True, False),),
                image_jump_setting="Protected Only",
            )
        with self.assertRaises(p217.RealHwFileSettingsShotMarkTcRegenRecLampError):
            p217.evaluate_shot_mark_jump_and_ftp_filter(
                (("C0001.MP4", True, False),),
                ftp_target_movie_filter="Proxy Only",
            )

    def test_46_photo_capture_mode_blocks_hdmi_tc_out_and_releases_prior_ext_lk(self) -> None:
        photo_tc = p217.probe_tc_regenerate_slot1_extlk_and_sq_hil(
            capture_mode="Photo",
            time_code_make=p217.TC_MAKE_PRESET,
            requested_time_code_run=p217.TC_RUN_FREE_RUN,
            requested_hdmi_time_code_output="On",
            vmc_bncm1_attached=True,
            sync_hold_seconds=20.0,
            prior_ext_lk_locked=True,
        )
        self.assertTrue(photo_tc.admitted)
        self.assertTrue(photo_tc.time_code_run_menu_available)
        self.assertFalse(photo_tc.hdmi_time_code_output_available)
        self.assertEqual(photo_tc.effective_hdmi_time_code_output, "Off")
        self.assertFalse(photo_tc.hdmi_tc_packet_stream_active)
        self.assertTrue(photo_tc.ext_lk_released)
        self.assertIn("CAPTURE_MODE_NOT_MOVIE", photo_tc.ext_lk_release_reasons)

    def test_47_all_five_tc_nominal_fps_rates_supported_in_regenerate(self) -> None:
        for fps in (24, 25, 30, 50, 60):
            last_ff = fps - 1
            start_tc = f"00:10:00:{last_ff:02d}"
            res = p217.probe_tc_regenerate_slot1_extlk_and_sq_hil(
                recording_media="Slot 1",
                time_code_make=p217.TC_MAKE_REGENERATE,
                nominal_fps=fps,
                slot1_last_end_tc=start_tc,
                record_frames=1,
            )
            self.assertTrue(res.admitted, msg=str(fps))
            self.assertEqual(res.clip_start_tc, start_tc)
            self.assertEqual(res.clip_end_tc, "00:10:01:00")

    def test_48_run_stage39_runner_directly_matches_phase217_digest(self) -> None:
        cfg = suite.CoEmulationConfig(force_clean_room=True)
        s39 = suite.run_stage39_realhw_filesettings_shotmark_tcregen_reclamp_hil(cfg)
        rep = _get_clean_room_audit()
        self.assertEqual(
            s39["stage"], "stage39_realhw_filesettings_shotmark_tcregen_reclamp_hil"
        )
        self.assertTrue(s39["all_checks_passed"])
        self.assertEqual(s39["phase217_audit_digest_sha256"], rep["audit_digest_sha256"])


if __name__ == "__main__":
    unittest.main()
