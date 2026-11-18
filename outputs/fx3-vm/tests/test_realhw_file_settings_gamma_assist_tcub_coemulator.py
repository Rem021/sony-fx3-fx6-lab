#!/usr/bin/env python3
"""Unit tests for Phase 274 (Stage 54, 54/54):
Real-Hardware `ILME-FX3` (`0x91030080`, `ilc/2210`, `Ver. 7.02`) Wave-44
Movie `[File Settings]` (`Cam ID + Reel#` & `37`-Char `Title Name`) vs Still
`[File/Folder Settings]` (`3`-Char `DSC` Prefix & `Slot-1` DCIM Vault Firewall),
`[Gamma Display Assist]` (`[Log Shooting]` Lockout & LCD-Only Clean HDMI) vs
`[Display LUT]` / `[Select LUT]` (`3` Presets + `User1..User16`), and
`[Auto Review]` (`Off` Cinema Default) & `[TC/UB]` (`6` Non-Resettable Parameters
+ `[TC/UB Disp. Setting]`) HIL Co-Emulator (70 dual-mode tests).
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
import unittest.mock

FX3_VM_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = FX3_VM_DIR.parents[1]
if str(FX3_VM_DIR) not in sys.path:
    sys.path.insert(0, str(FX3_VM_DIR))

import fx3_vm_coemulation_suite as suite  # noqa: E402
import realhw_file_settings_gamma_assist_tcub_coemulator as p274  # noqa: E402

IS_CI = os.environ.get("GITHUB_ACTIONS", "").lower() == "true"


def _fast_suite_kwargs(**overrides: object) -> dict:
    """Fast config skipping heavy unrelated stages for <50ms flag/override tests."""
    base = dict(
        force_clean_room=True,
        include_phase41_dtb_mhlx=False,
        include_phase45_imx510_xavc=False,
        include_phase53_hil_fault_harness=False,
        include_phase58_qmp_introspection=False,
        include_phase63_hdmi_raw_uvc=False,
        include_phase67_tc_lens_paint=False,
        include_phase71_dualslot_ups_salvage=False,
        include_phase78_touchaf_ciz_assignable=False,
        include_phase82_camset_lpcm_tcub=False,
        include_phase87_playback_shotmark_dewpoint=False,
        include_phase91_gyroflow_rtmd_anamorphic=False,
        include_phase96_interval_cache_ftp_fan=False,
        include_phase99_lut3d_subzero_sdi=False,
        include_phase103_emi_exfat_endurance=False,
        include_phase107_c2pa_shading_mcfleet_ovp=False,
        include_phase112_hdr_hlg_fiz_gimbal=False,
        include_phase117_proresraw_breathing_mishoe_hil=False,
        include_phase121_uvc_srt_crsdk_usbpd_hil=False,
        include_phase127_mxf_ptpv2_tally_monsoon_hil=False,
        include_phase132_vp_ledwall_freed_artnet_hil=False,
        include_phase141_realhw_preflash_dualboot_hil=False,
        include_phase145_realhw_mpr_dmm_rec=False,
        include_phase150_realhw_body_peripheral_hil=False,
        include_phase157_realhw_imx510_network_usb_hil=False,
        include_phase162_realhw_cfexpress_ufu_5tier_hil=False,
        include_phase167_realhw_cxd90058_sabin_seal_hil=False,
        include_phase172_realhw_c2pa_tc_gyro_prebench_hil=False,
        include_phase178_realhw_ssboot_wbi2_powerloss_slot1_ufu_hil=False,
        include_phase182_realhw_emount_info3d_breathing_hdmi_4264_raw_hil=False,
        include_phase188_realhw_fx3a_firewall_and_xlrh1_4ch_mishoe_hil=False,
        include_phase194_realhw_nouvc_dcc1_lut_path_cineei_hil=False,
        include_phase200_realhw_fan_pwm_shutter_angle_lut_split_hil=False,
        include_phase202_realhw_big6_noend_camset_slot1_vmcbncm1_hil=False,
        include_phase207_realhw_desqueeze_165x_focusmap_simult_shocklesswb_hil=False,
        include_phase213_realhw_hdmi_log1080_proxy_vault_focusmag_brightmon_hil=False,
        include_phase217_realhw_filesettings_shotmark_tcregen_reclamp_hil=False,
        include_phase222_realhw_pixelmap_ntscpal_gammaassist_displaylut_hil=False,
        include_phase226_realhw_steadyshot_active_ciz_4locks_powersave_autotemp_hil=False,
        include_phase232_realhw_sq_fixedvar_zebra_peaking_fullformat_hil=False,
        include_phase236_realhw_silent_autopixelmap_marker_flexexp_hil=False,
        include_stage44=False,
        include_stage45=False,
        include_stage46=False,
        include_stage47=False,
        include_stage48=False,
        include_stage49=False,
        include_stage50=False,
        include_stage51=False,
        include_stage52=False,
        include_stage53=False,
    )
    base.update(overrides)
    return base


_FAST_CLI_FLAGS = [
    "--clean-room",
    "--skip-phase41",
    "--skip-phase45",
    "--skip-phase53",
    "--skip-phase58",
    "--skip-phase63",
    "--skip-phase67",
    "--skip-phase71",
    "--skip-phase78",
    "--skip-phase82",
    "--skip-phase87",
    "--skip-phase91",
    "--skip-phase96",
    "--skip-phase99",
    "--skip-phase103",
    "--skip-phase107",
    "--skip-phase112",
    "--skip-phase117",
    "--skip-phase121",
    "--skip-phase127",
    "--skip-phase132",
    "--skip-phase141",
    "--skip-phase145",
    "--skip-phase150",
    "--skip-phase157",
    "--skip-phase162",
    "--skip-phase167",
    "--skip-phase172",
    "--skip-phase178",
    "--skip-phase182",
    "--skip-phase188",
    "--skip-phase194",
    "--skip-phase200",
    "--skip-phase202",
    "--skip-phase207",
    "--skip-phase213",
    "--skip-phase217",
    "--skip-phase222",
    "--skip-phase226",
    "--skip-phase232",
    "--skip-phase236",
    "--skip-stage44",
    "--skip-stage45",
    "--skip-stage46",
    "--skip-stage47",
    "--skip-stage48",
    "--skip-stage49",
    "--skip-stage50",
    "--skip-stage51",
    "--skip-stage52",
    "--skip-stage53",
]


class TestPhase274FileSettingsGammaAssistTcubCoEmulator(unittest.TestCase):
    clean_audit: dict = {}
    default_audit: dict = {}
    clean_suite: dict = {}
    clean_suite_elapsed: float = 0.0
    default_suite: dict = {}
    default_suite_elapsed: float = 0.0

    @classmethod
    def setUpClass(cls) -> None:
        cls.clean_audit = p274.run_phase274_realhw_file_settings_gamma_assist_tcub_hil(
            force_clean_room=True
        )
        cls.default_audit = p274.run_phase274_realhw_file_settings_gamma_assist_tcub_hil()

        forced = p274.is_forced_clean_room()
        t0 = time.monotonic()
        cls.default_suite = suite.run_fx3_vm_coemulation_suite(
            suite.CoEmulationConfig(force_clean_room=True if forced else None)
        )
        cls.default_suite_elapsed = time.monotonic() - t0

        if forced:
            cls.clean_suite = cls.default_suite
            cls.clean_suite_elapsed = cls.default_suite_elapsed
        else:
            t1 = time.monotonic()
            cls.clean_suite = suite.run_fx3_vm_coemulation_suite(
                suite.CoEmulationConfig(**_fast_suite_kwargs(force_clean_room=True))
            )
            cls.clean_suite_elapsed = time.monotonic() - t1

    # ------------------------------------------------------------------
    # Group 1: Schema, Stage 54 (54/54) & O_RDONLY 18-Donor Verification (14 tests)
    # ------------------------------------------------------------------
    def test_01_schema_version_phase274_stage54_and_redline_constants(self) -> None:
        self.assertEqual(
            p274.SCHEMA_ID,
            "realhw_file_settings_gamma_assist_tcub_coemulator_v1",
        )
        self.assertEqual(p274.PHASE_274_SCHEMA, p274.SCHEMA_ID)
        self.assertEqual(p274.PHASE_274_VERSION, "274.0.0")
        self.assertEqual(p274.PHASE_NUMBER, 274)
        self.assertEqual(p274.STAGE_INDEX, 54)
        self.assertEqual(p274.STAGE_TOTAL, 54)
        self.assertEqual(p274.MILESTONE_LABEL, "54/54")
        self.assertEqual(
            p274.STAGE_NAME,
            "stage54_realhw_file_settings_gamma_assist_tcub_hil",
        )
        self.assertEqual(p274.FX3_MODEL_ID, 0x91030080)
        self.assertEqual(p274.FX6_MODEL_ID, 0x91020080)
        self.assertEqual(p274.FX3_HELP_GUIDE_ID, "ilc/2210")
        self.assertTrue(p274.CNFLASHA_USERSPACE_WRITE_BLOCKED)
        self.assertFalse(p274.PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(p274.HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        self.assertFalse(p274.OVERALL_READY_FOR_HARDWARE_ATTACH)

    def test_02_clean_room_audit_deterministic_sha256_digest(self) -> None:
        self.assertTrue(self.clean_audit["all_checks_passed"])
        self.assertEqual(self.clean_audit["source_mode"], p274.SOURCE_MODE_CLEAN_ROOM)
        again = p274.run_phase274_realhw_file_settings_gamma_assist_tcub_hil(
            force_clean_room=True
        )
        self.assertEqual(
            self.clean_audit["audit_digest_sha256"],
            again["audit_digest_sha256"],
        )

    def test_03_both_clean_room_env_vars_force_clean_room(self) -> None:
        self.assertTrue(p274.is_forced_clean_room({p274.ENV_CLEAN_ROOM_TEST: "1"}))
        self.assertTrue(p274.is_forced_clean_room({p274.ENV_FORCE_CLEAN_ROOM: "1"}))
        self.assertTrue(p274.is_forced_clean_room({p274.ENV_CLEAN_ROOM_TEST: "true"}))
        self.assertFalse(p274.is_forced_clean_room({}))
        rep = p274.run_phase274_realhw_file_settings_gamma_assist_tcub_hil(
            env={p274.ENV_CLEAN_ROOM_TEST: "1"}
        )
        self.assertEqual(rep["source_mode"], p274.SOURCE_MODE_CLEAN_ROOM)
        self.assertTrue(rep["all_checks_passed"])

    def test_04_donor_audit_18_artifacts_and_zero_raw_leakage(self) -> None:
        for rep in (self.clean_audit, self.default_audit):
            da = rep["donor_audit"]
            self.assertEqual(da["access_mode"], "O_RDONLY")
            self.assertEqual(da["donor_files_inspected"], 18)
            self.assertEqual(da["raw_firmware_bytes_leaked"], 0)
            self.assertTrue(da["file_settings_and_vault_proven"])
            self.assertTrue(da["gamma_assist_and_display_lut_proven"])
            self.assertTrue(da["auto_review_and_tcub_proven"])
            self.assertTrue(da["all_contracts_verified"])
            self.assertEqual(list(da["errors"]), [])

    def test_05_compact_donors_exact_sizes_and_sha256(self) -> None:
        da = self.default_audit["donor_audit"]
        compact_keys = tuple(p274.EXPECTED_COMPACT_DONOR_SHA256.keys())
        self.assertEqual(len(compact_keys), 10)
        for key in compact_keys:
            entry = da[key]
            self.assertEqual(entry["file_bytes"], p274.EXPECTED_DONOR_BYTES[key])
            self.assertEqual(len(entry["sha256"]), 64)
            self.assertTrue(entry["sha256_verified"])
            if da["source_mode"] == p274.SOURCE_MODE_LOCAL_DONOR:
                self.assertEqual(entry["sha256"], p274.EXPECTED_COMPACT_DONOR_SHA256[key])

    def test_06_large_donors_bounded_window_only_and_head_sha256(self) -> None:
        da = self.default_audit["donor_audit"]
        large_keys = tuple(p274.EXPECTED_LARGE_HEAD4K_SHA256.keys())
        self.assertEqual(len(large_keys), 8)
        for key in large_keys:
            entry = da[key]
            self.assertTrue(entry["bounded_windows_only"])
            self.assertGreater(entry["bytes_read_total"], 0)
            self.assertLessEqual(
                entry["bytes_read_total"],
                (len(p274.LARGE_DONOR_WINDOWS[key]) + 1) * p274.BOUNDED_WINDOW_MAX_BYTES,
            )
            self.assertLess(entry["bytes_read_total"], entry["file_bytes"])
            self.assertEqual(entry["file_bytes"], p274.EXPECTED_DONOR_BYTES[key])
            self.assertEqual(len(entry["head_sha256"]), 64)
            self.assertTrue(entry["head_sha256_verified"])
            if da["source_mode"] == p274.SOURCE_MODE_LOCAL_DONOR:
                self.assertEqual(entry["head_sha256"], p274.EXPECTED_LARGE_HEAD4K_SHA256[key])

    def test_07_fx3_string_uxc_wave44_tokens_present(self) -> None:
        fx3_str = self.default_audit["donor_audit"]["fx3_string_en_f"]
        self.assertTrue(fx3_str["uxd_container_ok"])
        for tok in (
            "File Settings",
            "File/Folder Settings",
            "Cam ID + Reel#",
            "Title Name Settings",
            "Set File Name",
            "Forced File Number Reset",
            "Gamma Display Assist",
            "Gamma Disp. Assist Typ.",
            "Display LUT",
            "Select LUT",
            "Auto Review",
            "TC/UB",
            "Time Code Preset",
            "User Bit Preset",
            "Time Code Format",
            "Time Code Run",
            "Time Code Make",
            "User Bit Time Rec",
            "TC/UB Disp. Setting",
            "Camera Settings Reset",
            "Initialize",
        ):
            self.assertEqual(fx3_str["marker_hits"][tok], 1)

    def test_08_absent_tokens_confirmed_zero_on_fx3_and_fx6(self) -> None:
        da = self.default_audit["donor_audit"]
        for key, absent_map in (
            ("fx3_string_en_f", da["fx3_string_en_f"]["absent_marker_hits"]),
            ("fx6_string_en", da["fx6_string_en"]["absent_marker_hits"]),
        ):
            self.assertGreater(len(absent_map), 0, msg=key)
            for tok, hits in absent_map.items():
                self.assertEqual(hits, 0, msg=f"{key}:{tok}")

    def test_09_donor_inspection_latency_within_budget(self) -> None:
        max_s = 15.0 if IS_CI else 0.5
        t0 = time.monotonic()
        p274._DONOR_AUDIT_CACHE.clear()
        audit = p274.inspect_phase274_donors()
        elapsed = time.monotonic() - t0
        self.assertTrue(audit.all_contracts_verified)
        self.assertLess(elapsed, max_s)
        self.assertLess(audit.inspection_elapsed_s, 0.2)

    def test_10_missing_donor_directory_falls_back_cleanly_to_clean_room(self) -> None:
        with unittest.mock.patch.object(
            p274,
            "_iter_work_roots",
            return_value=(Path("/nonexistent/fx3/work/root/xyz"),),
        ):
            audit = p274.inspect_phase274_donors(force_clean_room=False, env={})
        self.assertEqual(audit.source_mode, p274.SOURCE_MODE_CLEAN_ROOM)
        self.assertTrue(audit.all_contracts_verified)

    def test_11_dual_mode_functional_pillar_parity(self) -> None:
        self.assertTrue(self.default_audit["all_checks_passed"])
        self.assertTrue(self.clean_audit["all_checks_passed"])
        for pillar_key in (
            "pillar_a_file_settings_and_vault_hil",
            "pillar_b_gamma_assist_vs_display_lut_hil",
            "pillar_c_d_auto_review_tcub_and_redlines",
        ):
            self.assertEqual(
                self.default_audit[pillar_key],
                self.clean_audit[pillar_key],
                msg=pillar_key,
            )

    def test_12_clean_room_sentinel_path_blocks_donor_reads(self) -> None:
        paths = p274.resolve_phase274_donor_paths(
            env={p274.ENV_CLEAN_ROOM_TEST: "1"}
        )
        self.assertEqual(len(paths), 18)
        for p in paths.values():
            self.assertIn(p274.CLEAN_ROOM_SENTINEL_DIRNAME, str(p))

    def test_13_bounded_window_reader_never_exceeds_4096_bytes_per_window(self) -> None:
        for key, windows in p274.LARGE_DONOR_WINDOWS.items():
            for off, label, tok in windows:
                self.assertGreaterEqual(off, 0, msg=f"{key}:{label}")
                self.assertLessEqual(len(tok), p274.BOUNDED_WINDOW_MAX_BYTES)

    def test_14_redlines_identical_between_local_and_clean_room(self) -> None:
        self.assertEqual(self.default_audit["redlines"], self.clean_audit["redlines"])

    # ------------------------------------------------------------------
    # Group 2: Sub-Model 54A Movie [File Settings] vs Still [File/Folder Settings] & Vault (18 tests)
    # ------------------------------------------------------------------
    def test_15_movie_file_settings_defaults_and_menu_path(self) -> None:
        res = p274.simulate_file_settings_and_vault_hil()
        self.assertTrue(res.admitted)
        self.assertEqual(res.errno_code, 0)
        self.assertEqual(res.movie_menu_path, "MENU -> Shooting -> [File] -> [File Settings]")
        self.assertEqual(res.effective_movie_file_number, p274.FILE_NUMBER_SERIES)
        self.assertEqual(res.effective_movie_file_name_format, p274.MOVIE_FORMAT_STANDARD)
        self.assertEqual(res.effective_title_name, "C")
        self.assertEqual(res.rendered_movie_filename, "C0001.MP4")
        self.assertEqual(res.movie_folder_path, "PRIVATE/M4ROOT/CLIP")

    def test_16_movie_cam_id_and_reel_number_formatting(self) -> None:
        res = p274.simulate_file_settings_and_vault_hil(
            configured_movie_file_name_format=p274.MOVIE_FORMAT_CAM_ID_REEL,
            configured_camera_id="B",
            configured_reel_number=7,
            configured_camera_position="L",
            clip_index=42,
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.effective_camera_id, "B")
        self.assertEqual(res.effective_reel_number, "007")
        self.assertEqual(res.effective_camera_position, "L")
        self.assertEqual(res.rendered_movie_filename, "B007L0042.MP4")

    def test_17_movie_cam_id_reel_bounds_and_positions(self) -> None:
        for cam_id in ("A", "Z"):
            for reel in (1, 999):
                for pos in ("C", "L", "R"):
                    res = p274.simulate_file_settings_and_vault_hil(
                        configured_movie_file_name_format=p274.MOVIE_FORMAT_CAM_ID_REEL,
                        configured_camera_id=cam_id,
                        configured_reel_number=reel,
                        configured_camera_position=pos,
                        clip_index=1,
                    )
                    self.assertTrue(res.admitted)
                    self.assertEqual(
                        res.rendered_movie_filename,
                        f"{cam_id}{reel:03d}{pos}0001.MP4",
                    )

    def test_18_movie_invalid_cam_id_reel_or_position_rejected_einval(self) -> None:
        for kwargs in (
            {"configured_camera_id": "a"},
            {"configured_camera_id": "1"},
            {"configured_reel_number": 0},
            {"configured_reel_number": 1000},
            {"configured_reel_number": "12"},
            {"configured_camera_position": "X"},
        ):
            res = p274.simulate_file_settings_and_vault_hil(**kwargs)
            self.assertFalse(res.admitted)
            self.assertEqual(res.errno_code, p274.EINVAL_ERRNO)

    def test_19_movie_all_five_file_name_formats_verified(self) -> None:
        matrix = self.clean_audit["pillar_a_file_settings_and_vault_hil"]["five_format_matrix"]
        self.assertEqual(len(matrix), 5)
        self.assertEqual(matrix["Standard"]["rendered_movie_filename"], "C0012.MP4")
        self.assertEqual(matrix["Cam ID + Reel#"]["rendered_movie_filename"], "A001C0012.MP4")
        self.assertTrue(matrix["Title"]["rendered_movie_filename"].endswith("_0012.MP4"))
        self.assertTrue(matrix["Date + Title"]["rendered_movie_filename"].startswith("20261117_"))
        self.assertTrue(matrix["Title + Date"]["rendered_movie_filename"].endswith("_20261117_0012.MP4"))

    def test_20_movie_title_exact_37_chars_admitted(self) -> None:
        title37 = "A" * 37
        res = p274.simulate_file_settings_and_vault_hil(
            configured_movie_file_name_format=p274.MOVIE_FORMAT_TITLE,
            configured_title_name=title37,
            clip_index=9,
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.title_char_len, 37)
        self.assertEqual(res.rendered_movie_filename, f"{title37}_0009.MP4")

    def test_21_movie_title_38_chars_or_empty_rejected_einval(self) -> None:
        for bad_title in ("", "X" * 38, "BAD/TITLE", "BAD*NAME"):
            res = p274.simulate_file_settings_and_vault_hil(
                configured_movie_file_name_format=p274.MOVIE_FORMAT_TITLE,
                configured_title_name=bad_title,
            )
            self.assertFalse(res.admitted, msg=repr(bad_title))
            self.assertEqual(res.errno_code, p274.EINVAL_ERRNO)
            self.assertEqual(res.title_name_37char_overflow_events, 0)

    def test_22_movie_folder_m4root_clip_immutable_eopnotsupp(self) -> None:
        res = p274.simulate_file_settings_and_vault_hil(force_custom_movie_folder=True)
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p274.EOPNOTSUPP_ERRNO)
        self.assertEqual(res.movie_folder_path, "PRIVATE/M4ROOT/CLIP")

    def test_23_movie_series_counter_reset_action(self) -> None:
        res = p274.simulate_file_settings_and_vault_hil(
            configured_movie_file_number=p274.FILE_NUMBER_RESET,
            media_action=p274.MEDIA_ACTION_SERIES_COUNTER_RESET,
            clip_index=99,
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.rendered_movie_filename, "C0001.MP4")

    def test_24_still_file_folder_defaults_and_menu_path(self) -> None:
        res = p274.simulate_file_settings_and_vault_hil()
        self.assertEqual(
            res.still_menu_path,
            "MENU -> Shooting -> [File] -> [File/Folder Settings]",
        )
        self.assertEqual(res.effective_still_file_number, p274.FILE_NUMBER_SERIES)
        self.assertEqual(res.effective_still_prefix, "DSC")
        self.assertEqual(res.effective_still_folder_form, p274.FOLDER_NAME_STANDARD_FORM)
        self.assertEqual(res.rendered_still_folder, "100MSDCF")
        self.assertEqual(res.rendered_still_filename, "DSC0001.JPG")

    def test_25_still_set_file_name_custom_3char_with_internal_underscore_ok(self) -> None:
        for prefix in ("FX3", "A_1", "9Z_"):
            res = p274.simulate_file_settings_and_vault_hil(
                configured_still_prefix=prefix,
                still_index=123,
            )
            self.assertTrue(res.admitted, msg=prefix)
            self.assertEqual(res.effective_still_prefix, prefix)
            self.assertEqual(res.rendered_still_filename, f"{prefix}0123.JPG")

    def test_26_still_prefix_leading_underscore_hard_rejected_einval(self) -> None:
        for bad_prefix in ("_AB", "_SC", "_01", "___"):
            res = p274.simulate_file_settings_and_vault_hil(
                configured_still_prefix=bad_prefix
            )
            self.assertFalse(res.admitted, msg=bad_prefix)
            self.assertEqual(res.errno_code, p274.EINVAL_ERRNO)
            self.assertEqual(res.reason_code, "STILL_PREFIX_LEADING_UNDERSCORE_FORBIDDEN")
            self.assertEqual(res.still_prefix_leading_underscore_bypass_events, 0)

    def test_27_still_prefix_wrong_length_or_lowercase_rejected_einval(self) -> None:
        for bad_prefix in ("", "DS", "DSCX", "dsc", "D-C"):
            res = p274.simulate_file_settings_and_vault_hil(
                configured_still_prefix=bad_prefix
            )
            self.assertFalse(res.admitted, msg=bad_prefix)
            self.assertEqual(res.errno_code, p274.EINVAL_ERRNO)

    def test_28_still_folder_name_standard_vs_date_form(self) -> None:
        std = p274.simulate_file_settings_and_vault_hil(
            configured_still_folder_form=p274.FOLDER_NAME_STANDARD_FORM,
            folder_index=104,
            date_yyyymmdd="20261117",
        )
        dt = p274.simulate_file_settings_and_vault_hil(
            configured_still_folder_form=p274.FOLDER_NAME_DATE_FORM,
            folder_index=104,
            date_yyyymmdd="20261117",
        )
        self.assertEqual(std.rendered_still_folder, "104MSDCF")
        self.assertEqual(dt.rendered_still_folder, "10461117")

    def test_29_all_file_settings_survive_camera_settings_reset(self) -> None:
        res = p274.simulate_file_settings_and_vault_hil(
            configured_movie_file_number=p274.FILE_NUMBER_RESET,
            configured_movie_file_name_format=p274.MOVIE_FORMAT_CAM_ID_REEL,
            configured_camera_id="K",
            configured_reel_number=88,
            configured_camera_position="R",
            configured_title_name="WAVE44_SCENE_A",
            configured_still_file_number=p274.FILE_NUMBER_RESET,
            configured_still_prefix="K_7",
            configured_still_folder_form=p274.FOLDER_NAME_DATE_FORM,
            reset_action=p274.RESET_ACTION_CAMERA_SETTINGS_RESET,
        )
        self.assertTrue(res.admitted)
        self.assertTrue(res.settings_survived_reset)
        self.assertFalse(res.settings_wiped_by_initialize)
        self.assertEqual(res.effective_movie_file_number, p274.FILE_NUMBER_RESET)
        self.assertEqual(res.effective_movie_file_name_format, p274.MOVIE_FORMAT_CAM_ID_REEL)
        self.assertEqual(res.effective_camera_id, "K")
        self.assertEqual(res.effective_reel_number, "088")
        self.assertEqual(res.effective_camera_position, "R")
        self.assertEqual(res.effective_title_name, "WAVE44_SCENE_A")
        self.assertEqual(res.effective_still_file_number, p274.FILE_NUMBER_RESET)
        self.assertEqual(res.effective_still_prefix, "K_7")
        self.assertEqual(res.effective_still_folder_form, p274.FOLDER_NAME_DATE_FORM)

    def test_30_initialize_restores_all_movie_and_still_file_defaults(self) -> None:
        res = p274.simulate_file_settings_and_vault_hil(
            configured_movie_file_number=p274.FILE_NUMBER_RESET,
            configured_movie_file_name_format=p274.MOVIE_FORMAT_TITLE_DATE,
            configured_camera_id="Z",
            configured_reel_number=999,
            configured_camera_position="L",
            configured_title_name="CUSTOM_TITLE",
            configured_still_file_number=p274.FILE_NUMBER_RESET,
            configured_still_prefix="FX3",
            configured_still_folder_form=p274.FOLDER_NAME_DATE_FORM,
            reset_action=p274.RESET_ACTION_INITIALIZE,
        )
        self.assertTrue(res.admitted)
        self.assertTrue(res.settings_wiped_by_initialize)
        self.assertEqual(res.effective_movie_file_number, p274.FILE_NUMBER_SERIES)
        self.assertEqual(res.effective_movie_file_name_format, p274.MOVIE_FORMAT_STANDARD)
        self.assertEqual(res.effective_camera_id, "A")
        self.assertEqual(res.effective_reel_number, "001")
        self.assertEqual(res.effective_camera_position, "C")
        self.assertEqual(res.effective_title_name, "C")
        self.assertEqual(res.effective_still_file_number, p274.FILE_NUMBER_SERIES)
        self.assertEqual(res.effective_still_prefix, "DSC")
        self.assertEqual(res.effective_still_folder_form, p274.FOLDER_NAME_STANDARD_FORM)

    def test_31_slot1_recovery_vault_blocks_forced_reset_and_create_new_folder_erofs(self) -> None:
        for action in (
            p274.MEDIA_ACTION_FORCED_FILE_NUMBER_RESET,
            p274.MEDIA_ACTION_CREATE_NEW_FOLDER,
        ):
            res = p274.simulate_file_settings_and_vault_hil(
                media_action=action,
                target_slot=1,
                slot1_has_recovery_vault=True,
            )
            self.assertFalse(res.admitted, msg=action)
            self.assertEqual(res.errno_code, p274.EROFS_ERRNO)
            self.assertEqual(res.slot1_vault_folder_mutation_events, 0)
            self.assertEqual(res.physical_device_writes, 0)

    def test_32_slot2_scratch_admits_create_new_folder_and_forced_reset_with_zero_writes(self) -> None:
        for action in (
            p274.MEDIA_ACTION_FORCED_FILE_NUMBER_RESET,
            p274.MEDIA_ACTION_CREATE_NEW_FOLDER,
        ):
            res = p274.simulate_file_settings_and_vault_hil(
                media_action=action,
                target_slot=2,
                slot1_has_recovery_vault=True,
                folder_index=100,
                still_index=55,
            )
            self.assertTrue(res.admitted, msg=action)
            self.assertEqual(res.rendered_still_folder, "101MSDCF")
            self.assertEqual(res.rendered_still_filename, "DSC0001.JPG")
            self.assertEqual(res.physical_device_writes, 0)
            self.assertEqual(res.bk4_persistent_nvram_writes, 0)

    # ------------------------------------------------------------------
    # Group 3: Sub-Model 54B [Gamma Display Assist] Log Lockout & Clean HDMI vs [Display LUT] (14 tests)
    # ------------------------------------------------------------------
    def test_33_gamma_display_assist_defaults_and_menu_paths(self) -> None:
        res = p274.simulate_gamma_assist_vs_display_lut_hil()
        self.assertTrue(res.admitted)
        self.assertEqual(
            res.gamma_assist_menu_path,
            "MENU -> Setup -> [Display Option] -> [Gamma Display Assist]",
        )
        self.assertEqual(
            res.display_lut_menu_path,
            "MENU -> Setup -> [Display Option] -> [Display LUT]",
        )
        self.assertEqual(
            res.select_lut_menu_path,
            "MENU -> Exposure/Color -> [Color/Tone] -> [Select LUT]",
        )
        self.assertEqual(res.effective_gamma_display_assist, p274.TOGGLE_OFF)
        self.assertEqual(res.effective_gamma_assist_type, p274.GAMMA_ASSIST_TYP_AUTO)
        self.assertEqual(res.effective_display_lut, p274.TOGGLE_ON)
        self.assertEqual(res.effective_select_lut, p274.LUT_PRESET_SLOG3)

    def test_34_gamma_display_assist_enabled_when_log_shooting_off(self) -> None:
        for typ in p274.VALID_GAMMA_ASSIST_TYPES:
            res = p274.simulate_gamma_assist_vs_display_lut_hil(
                configured_log_shooting=p274.LOG_SHOOTING_OFF,
                configured_gamma_display_assist=p274.TOGGLE_ON,
                configured_gamma_assist_type=typ,
                monitor_sink=p274.MONITOR_SINK_LCD_LIVE_VIEW,
            )
            self.assertTrue(res.admitted)
            self.assertFalse(res.gamma_display_assist_locked_by_log)
            self.assertEqual(res.effective_gamma_display_assist, p274.TOGGLE_ON)
            self.assertTrue(res.lcd_gamma_assist_applied)
            self.assertEqual(res.active_monitoring_conversion, f"GAMMA_DISPLAY_ASSIST:{typ}")

    def test_35_gamma_display_assist_hard_locked_off_under_all_log_modes(self) -> None:
        for mode in (
            p274.LOG_SHOOTING_CINE_EI,
            p274.LOG_SHOOTING_CINE_EI_QUICK,
            p274.LOG_SHOOTING_FLEXIBLE_ISO,
        ):
            res = p274.simulate_gamma_assist_vs_display_lut_hil(
                configured_log_shooting=mode,
                configured_gamma_display_assist=p274.TOGGLE_ON,
                configured_display_lut=p274.TOGGLE_ON,
                configured_select_lut="s709",
                monitor_sink=p274.MONITOR_SINK_LCD_LIVE_VIEW,
            )
            self.assertTrue(res.admitted, msg=mode)
            self.assertTrue(res.gamma_display_assist_locked_by_log)
            self.assertEqual(res.effective_gamma_display_assist, p274.TOGGLE_OFF)
            self.assertFalse(res.lcd_gamma_assist_applied)
            self.assertEqual(res.active_monitoring_conversion, "DISPLAY_LUT:s709")

    def test_36_forced_gamma_assist_bypass_during_log_shooting_blocked_eopnotsupp(self) -> None:
        for mode in (
            p274.LOG_SHOOTING_CINE_EI,
            p274.LOG_SHOOTING_CINE_EI_QUICK,
            p274.LOG_SHOOTING_FLEXIBLE_ISO,
        ):
            res = p274.simulate_gamma_assist_vs_display_lut_hil(
                configured_log_shooting=mode,
                configured_gamma_display_assist=p274.TOGGLE_ON,
                force_gamma_assist_during_log=True,
            )
            self.assertFalse(res.admitted)
            self.assertEqual(res.errno_code, p274.EOPNOTSUPP_ERRNO)
            self.assertTrue(res.gamma_display_assist_locked_by_log)
            self.assertEqual(res.gamma_assist_log_lockout_bypass_events, 0)

    def test_37_gamma_assist_lcd_live_view_and_internal_playback_only(self) -> None:
        for sink in (
            p274.MONITOR_SINK_LCD_LIVE_VIEW,
            p274.MONITOR_SINK_INTERNAL_PLAYBACK,
        ):
            res = p274.simulate_gamma_assist_vs_display_lut_hil(
                configured_log_shooting=p274.LOG_SHOOTING_OFF,
                configured_gamma_display_assist=p274.TOGGLE_ON,
                monitor_sink=sink,
            )
            self.assertTrue(res.admitted)
            self.assertTrue(res.lcd_gamma_assist_applied)
            self.assertFalse(res.external_hdmi_gamma_assist_applied)
            self.assertEqual(res.hdmi_gamma_assist_baked_frames, 0)

    def test_38_gamma_assist_never_applied_to_external_clean_hdmi(self) -> None:
        for typ in p274.VALID_GAMMA_ASSIST_TYPES:
            res = p274.simulate_gamma_assist_vs_display_lut_hil(
                configured_log_shooting=p274.LOG_SHOOTING_OFF,
                configured_gamma_display_assist=p274.TOGGLE_ON,
                configured_gamma_assist_type=typ,
                monitor_sink=p274.MONITOR_SINK_EXTERNAL_HDMI,
            )
            self.assertTrue(res.admitted)
            self.assertFalse(res.lcd_gamma_assist_applied)
            self.assertFalse(res.external_hdmi_gamma_assist_applied)
            self.assertEqual(res.hdmi_gamma_assist_baked_frames, 0)
            self.assertEqual(
                res.active_monitoring_conversion,
                "CLEAN_EXTERNAL_HDMI_NO_GAMMA_ASSIST",
            )

    def test_39_forced_gamma_assist_bake_to_hdmi_blocked_eopnotsupp(self) -> None:
        res = p274.simulate_gamma_assist_vs_display_lut_hil(
            configured_log_shooting=p274.LOG_SHOOTING_OFF,
            configured_gamma_display_assist=p274.TOGGLE_ON,
            monitor_sink=p274.MONITOR_SINK_EXTERNAL_HDMI,
            force_bake_gamma_assist_to_hdmi=True,
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p274.EOPNOTSUPP_ERRNO)
        self.assertEqual(res.hdmi_gamma_assist_baked_frames, 0)

    def test_40_select_lut_has_exact_3_presets_plus_16_user_slots(self) -> None:
        self.assertEqual(len(p274.SELECT_LUT_PRESETS), 3)
        self.assertEqual(len(p274.SELECT_LUT_USER_SLOTS), 16)
        self.assertEqual(len(p274.VALID_SELECT_LUT_OPTIONS), 19)
        self.assertEqual(p274.SELECT_LUT_PRESETS, ("S-Log3", "s709", "709(800%)"))
        self.assertEqual(p274.SELECT_LUT_USER_SLOTS[0], "User1")
        self.assertEqual(p274.SELECT_LUT_USER_SLOTS[-1], "User16")

    def test_41_select_lut_19_slots_all_admitted_under_log_shooting(self) -> None:
        mat = self.clean_audit["pillar_b_gamma_assist_vs_display_lut_hil"][
            "select_lut_19_matrix"
        ]
        self.assertEqual(len(mat), 19)
        for lut_name, entry in mat.items():
            self.assertTrue(entry["admitted"], msg=lut_name)
            self.assertEqual(entry["effective_select_lut"], lut_name)
            self.assertEqual(entry["active_monitoring_conversion"], f"DISPLAY_LUT:{lut_name}")

    def test_42_display_lut_off_yields_log_raw_passthrough(self) -> None:
        res = p274.simulate_gamma_assist_vs_display_lut_hil(
            configured_log_shooting=p274.LOG_SHOOTING_FLEXIBLE_ISO,
            configured_display_lut=p274.TOGGLE_OFF,
            configured_select_lut="User16",
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.effective_display_lut, p274.TOGGLE_OFF)
        self.assertEqual(res.active_monitoring_conversion, "LOG_RAW_PASSTHROUGH")

    def test_43_invalid_gamma_assist_or_lut_option_rejected_einval(self) -> None:
        for kwargs in (
            {"configured_gamma_assist_type": "S-Log2"},
            {"configured_select_lut": "User17"},
            {"configured_log_shooting": "S-Log2"},
            {"monitor_sink": "BUILTIN_EVF"},
        ):
            res = p274.simulate_gamma_assist_vs_display_lut_hil(**kwargs)
            self.assertFalse(res.admitted, msg=str(kwargs))
            self.assertEqual(res.errno_code, p274.EINVAL_ERRNO)

    def test_44_setup_gamma_assist_and_display_lut_survive_camera_settings_reset(self) -> None:
        res = p274.simulate_gamma_assist_vs_display_lut_hil(
            configured_log_shooting=p274.LOG_SHOOTING_OFF,
            configured_gamma_display_assist=p274.TOGGLE_ON,
            configured_gamma_assist_type=p274.GAMMA_ASSIST_TYP_HLG_709,
            configured_display_lut=p274.TOGGLE_OFF,
            reset_action=p274.RESET_ACTION_CAMERA_SETTINGS_RESET,
        )
        self.assertTrue(res.admitted)
        self.assertTrue(res.setup_items_survived_camera_reset)
        self.assertEqual(res.effective_gamma_display_assist, p274.TOGGLE_ON)
        self.assertEqual(res.effective_gamma_assist_type, p274.GAMMA_ASSIST_TYP_HLG_709)
        self.assertEqual(res.effective_display_lut, p274.TOGGLE_OFF)

    def test_45_initialize_resets_gamma_assist_and_display_lut_to_defaults(self) -> None:
        res = p274.simulate_gamma_assist_vs_display_lut_hil(
            configured_log_shooting=p274.LOG_SHOOTING_OFF,
            configured_gamma_display_assist=p274.TOGGLE_ON,
            configured_gamma_assist_type=p274.GAMMA_ASSIST_TYP_HLG_BT2020,
            configured_display_lut=p274.TOGGLE_OFF,
            configured_select_lut="User8",
            reset_action=p274.RESET_ACTION_INITIALIZE,
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.effective_gamma_display_assist, p274.TOGGLE_OFF)
        self.assertEqual(res.effective_gamma_assist_type, p274.GAMMA_ASSIST_TYP_AUTO)
        self.assertEqual(res.effective_display_lut, p274.TOGGLE_ON)
        self.assertEqual(res.effective_select_lut, p274.LUT_PRESET_SLOG3)

    def test_46_pillar_b_passed_flag_and_zero_writes(self) -> None:
        pb = self.clean_audit["pillar_b_gamma_assist_vs_display_lut_hil"]
        self.assertTrue(pb["passed"])
        self.assertEqual(pb["select_lut_count"], 19)

    # ------------------------------------------------------------------
    # Group 4: Sub-Model 54C [Auto Review] & 6 Non-Resettable [TC/UB] Items (14 tests)
    # ------------------------------------------------------------------
    def test_47_auto_review_cinema_default_is_off_on_fx3(self) -> None:
        res = p274.simulate_auto_review_and_tcub_hil(
            shooting_domain=p274.SHOOTING_DOMAIN_STILL,
        )
        self.assertTrue(res.admitted)
        self.assertEqual(
            res.auto_review_menu_path,
            "MENU -> Setup -> [Display Option] -> [Auto Review]",
        )
        self.assertEqual(res.effective_auto_review, p274.AUTO_REVIEW_OFF)
        self.assertEqual(res.still_post_capture_review_seconds, 0)

    def test_48_auto_review_2s_5s_10s_still_only(self) -> None:
        for opt, expected_s in (("2 Sec", 2), ("5 Sec", 5), ("10 Sec", 10)):
            still_res = p274.simulate_auto_review_and_tcub_hil(
                shooting_domain=p274.SHOOTING_DOMAIN_STILL,
                configured_auto_review=opt,
            )
            self.assertTrue(still_res.admitted)
            self.assertEqual(still_res.still_post_capture_review_seconds, expected_s)
            for movie_dom in (p274.SHOOTING_DOMAIN_MOVIE, p274.SHOOTING_DOMAIN_SQ):
                mv_res = p274.simulate_auto_review_and_tcub_hil(
                    shooting_domain=movie_dom,
                    configured_auto_review=opt,
                )
                self.assertTrue(mv_res.admitted)
                self.assertEqual(mv_res.still_post_capture_review_seconds, 0)

    def test_49_tc_ub_exact_6_items_locked(self) -> None:
        self.assertEqual(
            p274.TC_UB_EXACT_6_ITEMS,
            (
                "Time Code Preset",
                "User Bit Preset",
                "Time Code Format",
                "Time Code Run",
                "Time Code Make",
                "User Bit Time Rec",
            ),
        )
        self.assertEqual(len(p274.TC_UB_EXACT_6_ITEMS), 6)

    def test_50_tc_ub_defaults_and_disp_setting(self) -> None:
        res = p274.simulate_auto_review_and_tcub_hil()
        self.assertTrue(res.admitted)
        self.assertEqual(res.tc_ub_menu_path, "MENU -> Shooting -> [TC/UB]")
        self.assertEqual(
            res.tc_ub_disp_menu_path,
            "MENU -> Setup -> [Display Option] -> [TC/UB Disp. Setting]",
        )
        self.assertEqual(res.effective_tc_preset, "00:00:00.00")
        self.assertEqual(res.effective_ub_preset, "00 00 00 00")
        self.assertEqual(res.effective_tc_format, "DF")
        self.assertEqual(res.effective_tc_run, "Rec Run")
        self.assertEqual(res.effective_tc_make, "Preset")
        self.assertEqual(res.effective_ub_time_rec, "Off")
        self.assertEqual(res.effective_tc_ub_disp_setting, "TC")

    def test_51_tc_format_forced_ndf_on_24p_and_pal_25p_50p(self) -> None:
        for fps in (p274.FRAME_RATE_2400P, p274.FRAME_RATE_25P, p274.FRAME_RATE_50P):
            res = p274.simulate_auto_review_and_tcub_hil(
                frame_rate=fps,
                configured_tc_format=p274.TC_FORMAT_DF,
            )
            self.assertTrue(res.admitted, msg=fps)
            self.assertTrue(res.tc_format_forced_ndf, msg=fps)
            self.assertEqual(res.effective_tc_format, p274.TC_FORMAT_NDF)

    def test_52_tc_format_df_available_on_2997p_5994p_and_2398p(self) -> None:
        for fps in (
            p274.FRAME_RATE_2398P,
            p274.FRAME_RATE_2997P,
            p274.FRAME_RATE_5994P,
        ):
            res = p274.simulate_auto_review_and_tcub_hil(
                frame_rate=fps,
                configured_tc_format=p274.TC_FORMAT_DF,
            )
            self.assertTrue(res.admitted, msg=fps)
            self.assertFalse(res.tc_format_forced_ndf, msg=fps)
            self.assertEqual(res.effective_tc_format, p274.TC_FORMAT_DF)

    def test_53_forced_df_on_24p_or_pal_rejected_einval(self) -> None:
        for fps in (p274.FRAME_RATE_2400P, p274.FRAME_RATE_25P, p274.FRAME_RATE_50P):
            res = p274.simulate_auto_review_and_tcub_hil(
                frame_rate=fps,
                configured_tc_format=p274.TC_FORMAT_DF,
                force_df_on_24p_or_pal=True,
            )
            self.assertFalse(res.admitted)
            self.assertEqual(res.errno_code, p274.EINVAL_ERRNO)
            self.assertEqual(res.tc_24p_or_pal_df_violation_events, 0)

    def test_54_all_6_tc_ub_items_survive_camera_settings_reset(self) -> None:
        res = p274.simulate_auto_review_and_tcub_hil(
            shooting_domain=p274.SHOOTING_DOMAIN_STILL,
            frame_rate=p274.FRAME_RATE_2997P,
            configured_auto_review=p274.AUTO_REVIEW_5S,
            configured_tc_preset="01:23:45.12",
            configured_ub_preset="ab cd ef 01",
            configured_tc_format=p274.TC_FORMAT_NDF,
            configured_tc_run=p274.TC_RUN_FREE_RUN,
            configured_tc_make=p274.TC_MAKE_REGENERATE,
            configured_ub_time_rec=p274.TOGGLE_ON,
            configured_tc_ub_disp_setting=p274.TC_DISP_UBIT,
            reset_action=p274.RESET_ACTION_CAMERA_SETTINGS_RESET,
        )
        self.assertTrue(res.admitted)
        self.assertTrue(res.auto_review_survived_camera_reset)
        self.assertTrue(res.all_6_tcub_survived_camera_reset)
        self.assertTrue(res.tc_ub_disp_survived_camera_reset)
        self.assertEqual(res.effective_auto_review, p274.AUTO_REVIEW_5S)
        self.assertEqual(res.effective_tc_preset, "01:23:45.12")
        self.assertEqual(res.effective_ub_preset, "AB CD EF 01")
        self.assertEqual(res.effective_tc_format, p274.TC_FORMAT_NDF)
        self.assertEqual(res.effective_tc_run, p274.TC_RUN_FREE_RUN)
        self.assertEqual(res.effective_tc_make, p274.TC_MAKE_REGENERATE)
        self.assertEqual(res.effective_ub_time_rec, p274.TOGGLE_ON)
        self.assertEqual(res.effective_tc_ub_disp_setting, p274.TC_DISP_UBIT)

    def test_55_all_6_tc_ub_and_auto_review_survive_reset_network_set(self) -> None:
        res = p274.simulate_auto_review_and_tcub_hil(
            frame_rate=p274.FRAME_RATE_5994P,
            configured_auto_review=p274.AUTO_REVIEW_2S,
            configured_tc_preset="10:11:12.13",
            configured_ub_preset="CA FE BA BE",
            configured_tc_format=p274.TC_FORMAT_NDF,
            configured_tc_run=p274.TC_RUN_FREE_RUN,
            configured_tc_make=p274.TC_MAKE_REGENERATE,
            configured_ub_time_rec=p274.TOGGLE_ON,
            configured_tc_ub_disp_setting=p274.TC_DISP_UBIT,
            reset_action=p274.RESET_ACTION_RESET_NETWORK_SET,
        )
        self.assertTrue(res.admitted)
        self.assertTrue(res.all_6_tcub_survived_camera_reset)
        self.assertEqual(res.effective_tc_preset, "10:11:12.13")
        self.assertEqual(res.effective_ub_preset, "CA FE BA BE")

    def test_56_forced_tcub_wipe_on_camera_settings_reset_blocked_eopnotsupp(self) -> None:
        res = p274.simulate_auto_review_and_tcub_hil(
            configured_tc_preset="01:23:45.12",
            reset_action=p274.RESET_ACTION_CAMERA_SETTINGS_RESET,
            force_wipe_tcub_on_camera_settings_reset=True,
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p274.EOPNOTSUPP_ERRNO)
        self.assertEqual(res.tcub_camera_settings_reset_wipe_events, 0)

    def test_57_initialize_clears_all_6_tcub_and_auto_review_to_defaults(self) -> None:
        res = p274.simulate_auto_review_and_tcub_hil(
            shooting_domain=p274.SHOOTING_DOMAIN_STILL,
            frame_rate=p274.FRAME_RATE_5994P,
            configured_auto_review=p274.AUTO_REVIEW_10S,
            configured_tc_preset="22:33:44.05",
            configured_ub_preset="DE AD BE EF",
            configured_tc_format=p274.TC_FORMAT_NDF,
            configured_tc_run=p274.TC_RUN_FREE_RUN,
            configured_tc_make=p274.TC_MAKE_REGENERATE,
            configured_ub_time_rec=p274.TOGGLE_ON,
            configured_tc_ub_disp_setting=p274.TC_DISP_UBIT,
            reset_action=p274.RESET_ACTION_INITIALIZE,
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.effective_auto_review, p274.AUTO_REVIEW_OFF)
        self.assertEqual(res.still_post_capture_review_seconds, 0)
        self.assertEqual(res.effective_tc_preset, p274.TC_PRESET_DEFAULT)
        self.assertEqual(res.effective_ub_preset, p274.UB_PRESET_DEFAULT)
        self.assertEqual(res.effective_tc_format, p274.TC_FORMAT_DF)
        self.assertEqual(res.effective_tc_run, p274.TC_RUN_REC_RUN)
        self.assertEqual(res.effective_tc_make, p274.TC_MAKE_PRESET)
        self.assertEqual(res.effective_ub_time_rec, p274.TOGGLE_OFF)
        self.assertEqual(res.effective_tc_ub_disp_setting, p274.TC_DISP_TC)

    def test_58_invalid_tc_ub_presets_or_auto_review_rejected_einval(self) -> None:
        for kwargs in (
            {"configured_auto_review": "1 Sec"},
            {"configured_tc_preset": "01:23:45"},
            {"configured_ub_preset": "12345678"},
            {"configured_ub_preset": "GG 00 00 00"},
            {"configured_tc_ub_disp_setting": "Duration"},
        ):
            res = p274.simulate_auto_review_and_tcub_hil(**kwargs)
            self.assertFalse(res.admitted, msg=str(kwargs))
            self.assertEqual(res.errno_code, p274.EINVAL_ERRNO)

    def test_59_tc_ub_disp_setting_modes_tc_and_ubit(self) -> None:
        for disp in (p274.TC_DISP_TC, p274.TC_DISP_UBIT):
            res = p274.simulate_auto_review_and_tcub_hil(
                configured_tc_ub_disp_setting=disp
            )
            self.assertTrue(res.admitted)
            self.assertEqual(res.effective_tc_ub_disp_setting, disp)

    def test_60_pillar_cd_passed_flag_and_zero_writes(self) -> None:
        pcd = self.clean_audit["pillar_c_d_auto_review_tcub_and_redlines"]
        self.assertTrue(pcd["passed"])
        self.assertEqual(len(pcd["tc_ub_exact_6_items"]), 6)

    # ------------------------------------------------------------------
    # Group 5: 16 Redline Probes, Stage 54 (54/54) Suite & Subprocess Hygiene (10 tests)
    # ------------------------------------------------------------------
    def test_61_all_16_redline_probes_fail_closed_and_unknown_probe_einval(self) -> None:
        self.assertEqual(len(p274.ALL_16_REDLINE_PROBE_FIELDS), 16)
        base = p274.probe_phase274_redline_guard()
        self.assertTrue(base.valid)
        self.assertEqual(base.errno_code, 0)
        for field in p274.ALL_16_REDLINE_PROBE_FIELDS:
            blocked = p274.probe_phase274_redline_guard(**{field: True})
            self.assertFalse(blocked.valid, msg=field)
            self.assertGreater(blocked.errno_code, 0, msg=field)
            self.assertEqual(blocked.physical_device_writes, 0)
            self.assertEqual(blocked.emmc_corruptions, 0)
            self.assertEqual(blocked.raw_firmware_bytes_leaked, 0)
        bad = p274.probe_phase274_redline_guard(unknown_probe_xyz=True)
        self.assertFalse(bad.valid)
        self.assertEqual(bad.errno_code, p274.EINVAL_ERRNO)

    def test_62_standalone_cli_self_test_summary_and_json_via_sys_executable(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env[p274.ENV_CLEAN_ROOM_TEST] = "1"
        script = str(FX3_VM_DIR / "realhw_file_settings_gamma_assist_tcub_coemulator.py")

        proc_sum = subprocess.run(
            [sys.executable, "-B", script, "--self-test", "--summary"],
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertIn("[PASS] Phase 274 Stage 54 (54/54)", proc_sum.stdout)
        self.assertIn("mode=CLEAN_ROOM_SYNTHETIC", proc_sum.stdout)

        proc_json = subprocess.run(
            [sys.executable, "-B", script, "--self-test", "--json"],
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        data = json.loads(proc_json.stdout)
        self.assertTrue(data["all_checks_passed"])
        self.assertEqual(data["milestone"], "54/54")
        self.assertEqual(data["phase_number"], 274)

    def test_63_suite_stage54_54_of_54_auto_discovered_and_all_stages_pass(self) -> None:
        for rep in (self.default_suite, self.clean_suite):
            self.assertTrue(rep["all_checks_passed"])
            s54 = rep["stage54_realhw_file_settings_gamma_assist_tcub_hil"]
            self.assertTrue(s54["all_checks_passed"])
            self.assertEqual(s54["phase_number"], 274)
            self.assertEqual(s54["milestone"], "54/54")
            stage_keys = [
                k for k in rep if re.match(r"^stage\d+_", k) and isinstance(rep[k], dict)
            ]
            if rep is self.default_suite:
                self.assertGreaterEqual(len(stage_keys), 54)

    def test_64_suite_default_and_clean_room_runtime_within_budget(self) -> None:
        max_default_s = 15.0 if IS_CI else 5.0
        max_clean_s = 10.0 if IS_CI else 3.0
        self.assertLess(self.default_suite_elapsed, max_default_s)
        self.assertLess(self.clean_suite_elapsed, max_clean_s)

    def test_65_suite_deterministic_digest_in_clean_room_mode(self) -> None:
        rep_a = suite.run_fx3_vm_coemulation_suite(
            suite.CoEmulationConfig(**_fast_suite_kwargs(force_clean_room=True))
        )
        rep_b = suite.run_fx3_vm_coemulation_suite(
            suite.CoEmulationConfig(**_fast_suite_kwargs(force_clean_room=True))
        )
        self.assertEqual(rep_a["audit_digest_sha256"], rep_b["audit_digest_sha256"])

    def test_66_suite_stage54_config_defaults_and_skip_overrides(self) -> None:
        default_cfg = suite.CoEmulationConfig()
        self.assertTrue(default_cfg.stage54_realhw_file_settings_gamma_assist_tcub_hil)
        self.assertTrue(default_cfg.include_stage54)
        self.assertTrue(
            default_cfg.include_phase274_realhw_file_settings_gamma_assist_tcub_hil
        )

        for override in (
            {"stage54_realhw_file_settings_gamma_assist_tcub_hil": False},
            {"include_stage54": False},
            {"include_phase274_realhw_file_settings_gamma_assist_tcub_hil": False},
        ):
            rep = suite.run_fx3_vm_coemulation_suite(
                suite.CoEmulationConfig(**_fast_suite_kwargs(**override))
            )
            self.assertTrue(rep["all_checks_passed"])
            self.assertNotIn(
                "stage54_realhw_file_settings_gamma_assist_tcub_hil", rep
            )
            self.assertFalse(rep["config"]["include_stage54"])
            self.assertFalse(
                rep["config"]["stage54_realhw_file_settings_gamma_assist_tcub_hil"]
            )

    def test_67_fx3_vm_coemulation_suite_include_stage54_cli_summary(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = suite.main(_FAST_CLI_FLAGS + ["--include-stage54", "--summary"])
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("[PASS] Phase 33 FX3-VM Co-Emulation", out)
        self.assertIn(
            "realhw_file_settings_gamma_assist_tcub_hil=CLEAN_ROOM_SYNTHETIC",
            out,
        )

    def test_68_fx3_vm_coemulation_suite_cli_skip_phase274_and_skip_stage54(self) -> None:
        for skip_flag in ("--skip-phase274", "--skip-stage54", "--no-include-stage54"):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = suite.main(_FAST_CLI_FLAGS + [skip_flag, "--json"])
            self.assertEqual(rc, 0)
            parsed = json.loads(buf.getvalue())
            self.assertTrue(parsed["all_checks_passed"])
            self.assertNotIn(
                "stage54_realhw_file_settings_gamma_assist_tcub_hil", parsed
            )

    def test_69_all_safety_and_byof_redlines_locked_across_stage54_and_suite(self) -> None:
        for rep in (self.clean_audit, self.default_audit):
            red = rep["redlines"]
            self.assertFalse(red["persistent_emmc_writes_authorized"])
            self.assertFalse(red["hardware_live_attachment_authorized"])
            self.assertFalse(red["overall_ready_for_hardware_attach"])
            self.assertFalse(red["isp_write_authorized"])
            self.assertFalse(red["spi_nor_write_authorized"])
            self.assertFalse(red["el3_payload_transmit_authorized"])
            self.assertTrue(red["cnflasha_userspace_write_blocked"])
            self.assertEqual(red["slot1_vault_folder_mutation_events"], 0)
            self.assertEqual(red["title_name_37char_overflow_events"], 0)
            self.assertEqual(red["still_prefix_leading_underscore_bypass_events"], 0)
            self.assertEqual(red["gamma_assist_log_lockout_bypass_events"], 0)
            self.assertEqual(red["hdmi_gamma_assist_baked_frames"], 0)
            self.assertEqual(red["tcub_camera_settings_reset_wipe_events"], 0)
            self.assertEqual(red["tc_24p_or_pal_df_violation_events"], 0)
            self.assertEqual(red["physical_device_writes"], 0)
            self.assertEqual(red["emmc_corruptions"], 0)
            self.assertEqual(red["nop_count"], 0)
            self.assertEqual(red["guest_code_modification_bytes"], 0)
            self.assertEqual(red["raw_firmware_bytes_leaked"], 0)

    def test_70_no_pyc_bytecode_files_emitted_under_fx3_vm(self) -> None:
        pyc_files = list(FX3_VM_DIR.rglob("*.pyc"))
        self.assertEqual(pyc_files, [])


if __name__ == "__main__":
    unittest.main()
