#!/usr/bin/env python3
"""Unit tests for Phase 213 Stage 38 (`38/38` Milestone):
Real-Hardware `ILME-FX3` (`0x91030080`, `Ver. 7.02`) `[HDMI Output Settings]` (`[Log Shooting]` /
`PPLUT1..4` Forced `1080p` Downshift vs `[Off(HDMI Only)]` `4K 10-bit` & `[HDMI Info. Display]`
Blank-LCD), `[Proxy Settings]` (`XAVC HS HD` 10-bit HEVC `16M`/`9M` & `XAVC S HD` 8-bit AVC `6M`,
`119.88p/100p` & `>=120fps/100fps` Cutoffs, `(Px)` Zero-Playback & Atomic Coupled `CLIP/`+`SUB/`
Vault), and `[Focus Magnifier]` (`x1.0`/`x4.0` Movie vs `x1.0`/`x2.1`/`x1.5` Still) x
`[Bright Monitoring]` (`P/A/S/M` + `MF` Lock, Custom-Key Lockout & `[Setting Effect OFF]`) HIL.
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
import realhw_hdmi_log1080_proxy_vault_focusmag_brightmon_coemulator as p213  # noqa: E402


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
            p213.run_phase213_realhw_hdmi_log1080_proxy_vault_focusmag_brightmon_hil(
                force_clean_room=True
            )
        )
    return _CLEAN_ROOM_AUDIT_CACHE


def _get_default_audit():
    global _DEFAULT_AUDIT_CACHE
    if _DEFAULT_AUDIT_CACHE is None:
        _DEFAULT_AUDIT_CACHE = (
            p213.run_phase213_realhw_hdmi_log1080_proxy_vault_focusmag_brightmon_hil()
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


class TestPhase213HdmiLog1080ProxyVaultFocusMagBrightMonCoEmulator(unittest.TestCase):
    def test_01_schema_version_stage_38_milestone_and_redline_constants(self) -> None:
        self.assertEqual(
            p213.PHASE_213_SCHEMA,
            "phase213_realhw_hdmi_log1080_proxy_vault_focusmag_brightmon_coemulator_v1",
        )
        self.assertEqual(p213.PHASE_213_VERSION, "213.0.0")
        self.assertEqual(p213.STAGE_INDEX, 38)
        self.assertEqual(p213.STAGE_TOTAL, 38)
        self.assertEqual(p213.MILESTONE_LABEL, "38/38")
        self.assertEqual(
            p213.STAGE_NAME,
            "stage38_realhw_hdmi_log1080_proxy_vault_focusmag_brightmon_hil",
        )
        self.assertEqual(p213.FX3_MODEL_ID, 0x91030080)
        self.assertTrue(p213.P8_CP_MUTATION_FORBIDDEN)
        self.assertFalse(p213.PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(p213.SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(p213.EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        self.assertEqual(p213.PHYSICAL_USB_PACKETS_EMITTED, 0)
        self.assertEqual(p213.OTP_FUSE_TOUCHES, 0)
        self.assertEqual(p213.RPMB_COUNTER_INCREMENTS, 0)
        self.assertEqual(p213.SINGLE_SIDED_PROXY_OR_MAIN_ORPHAN_MUTATIONS, 0)
        self.assertEqual(p213.ON_CAMERA_PROXY_PLAYBACK_FRAMES, 0)
        self.assertEqual(p213.RAW_FIRMWARE_BYTES_LEAKED, 0)
        self.assertEqual(p213.DONOR_ACCESS_MODE, "O_RDONLY")

    def test_02_donor_inspection_fast_bounded_and_cached(self) -> None:
        p213._DONOR_AUDIT_CACHE.clear()
        t0 = time.monotonic()
        da1 = p213.inspect_phase213_donors(force_clean_room=False)
        dt1 = time.monotonic() - t0
        t1 = time.monotonic()
        da2 = p213.inspect_phase213_donors(force_clean_room=False)
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
        da_flag = p213.inspect_phase213_donors(force_clean_room=True)
        self.assertEqual(da_flag.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(da_flag.access_mode, "O_RDONLY")
        self.assertEqual(da_flag.donor_files_inspected, 12)
        self.assertEqual(da_flag.raw_firmware_bytes_leaked, 0)
        self.assertTrue(da_flag.all_contracts_verified)

        da_env = p213.inspect_phase213_donors(env={"FX3_FX6_FORCE_CLEAN_ROOM": "1"})
        self.assertEqual(da_env.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertIs(da_env, da_flag)

    def test_04_clean_room_sentinel_paths_do_not_touch_local_donors(self) -> None:
        paths_clean = p213.resolve_phase213_donor_paths(env={"FX3_FX6_FORCE_CLEAN_ROOM": "1"})
        self.assertEqual(len(paths_clean), 12)
        for p in paths_clean.values():
            self.assertIn(p213.CLEAN_ROOM_SENTINEL_DIRNAME, str(p))
            self.assertFalse(p.exists())
        da = p213.inspect_phase213_donors(env={"FX3_FX6_FORCE_CLEAN_ROOM": "1"})
        self.assertEqual(da.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(da.all_contracts_verified)
        self.assertEqual(da.raw_firmware_bytes_leaked, 0)

    def test_05_twelve_donors_expected_sizes_and_bounded_windows(self) -> None:
        da = p213.inspect_phase213_donors()
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
        for w in (
            da.fx3_appfw,
            da.fx6_appfw,
            da.fx3_cpapp,
            da.fx6_cpapp,
            da.fx3_libmpr,
            da.fx6_libmpr,
        ):
            self.assertTrue(w.bounded_windows_only)
            self.assertLessEqual(w.bytes_read_total, 65_536)

    def test_06_donor_wave28_menu_and_symbol_contracts_proven(self) -> None:
        da = p213.inspect_phase213_donors()
        self.assertTrue(da.hdmi_log_1080p_and_hdmionly_4k_proven)
        self.assertTrue(da.proxy_dual_codec_and_coupled_vault_proven)
        self.assertTrue(da.focus_mag_and_bright_monitoring_proven)
        for tok in (
            "HDMI Output Settings",
            "Rec. Media dur HDMI Output",
            "Off(HDMI Only)",
            "4K Output Set.(HDMI Only)",
            "HDMI Info. Display",
            "Proxy Settings",
            "XAVC HS HD",
            "XAVC S HD",
            "16M 4:2:0 10bit",
            "9M 4:2:0 10bit",
            "6M 4:2:0 8bit",
            "Initial Focus Mag.",
            "Auto Magnifier in MF",
            "Bright Monitoring",
            "Setting Effect OFF",
        ):
            self.assertEqual(da.fx3_string_en_f.marker_hits[tok], 1, msg=tok)

    def test_07_submodel_a_hdmi_forced_1080p_downshift_under_all_log_modes(self) -> None:
        for log_mode in ("Cine EI", "Cine EI Quick", "Flexible ISO"):
            for req_res in ("Auto", "2160p"):
                res = p213.probe_hdmi_log1080_vs_hdmionly_4k_blank_lcd_hil(
                    rec_media_dur_hdmi="On",
                    hdmi_raw_output="Off",
                    requested_output_resolution=req_res,
                    log_shooting=log_mode,
                    picture_profile="Off",
                )
                self.assertTrue(res.admitted, msg=f"{log_mode}/{req_res}")
                self.assertEqual(res.effective_hdmi_width, 1920)
                self.assertEqual(res.effective_hdmi_height, 1080)
                self.assertEqual(res.effective_hdmi_resolution_label, "1080p")
                self.assertTrue(res.hdmi_downshifted_to_1080p)
                self.assertIn(f"LOG_SHOOTING:{log_mode}", res.downshift_trigger_reason)
                self.assertTrue(res.internal_card_recording_active)

    def test_08_submodel_a_hdmi_forced_1080p_downshift_under_pplut1_to_pplut4(self) -> None:
        for pp in ("PPLUT1", "PPLUT2", "PPLUT3", "PPLUT4"):
            res = p213.probe_hdmi_log1080_vs_hdmionly_4k_blank_lcd_hil(
                rec_media_dur_hdmi="On",
                hdmi_raw_output="Off",
                requested_output_resolution="2160p",
                log_shooting="Off",
                picture_profile=pp,
                record_setting_bit_depth=8,
            )
            self.assertTrue(res.admitted, msg=pp)
            self.assertEqual((res.effective_hdmi_width, res.effective_hdmi_height), (1920, 1080))
            self.assertEqual(res.effective_hdmi_bit_depth, 8)
            self.assertTrue(res.hdmi_downshifted_to_1080p)
            self.assertEqual(res.downshift_trigger_reason, f"PICTURE_PROFILE:{pp}")
            self.assertTrue(res.internal_card_recording_active)

    def test_09_submodel_a_standard_4k_output_when_log_off_and_non_pplut(self) -> None:
        for pp in ("Off", "PP1", "PP8", "PP11"):
            res = p213.probe_hdmi_log1080_vs_hdmionly_4k_blank_lcd_hil(
                rec_media_dur_hdmi="On",
                hdmi_raw_output="Off",
                requested_output_resolution="2160p",
                log_shooting="Off",
                picture_profile=pp,
            )
            self.assertTrue(res.admitted, msg=pp)
            self.assertEqual((res.effective_hdmi_width, res.effective_hdmi_height), (3840, 2160))
            self.assertFalse(res.hdmi_downshifted_to_1080p)
            self.assertTrue(res.internal_card_recording_active)

        res_1080i = p213.probe_hdmi_log1080_vs_hdmionly_4k_blank_lcd_hil(
            rec_media_dur_hdmi="On",
            requested_output_resolution="1080i",
            log_shooting="Off",
            picture_profile="Off",
        )
        self.assertEqual((res_1080i.effective_hdmi_width, res_1080i.effective_hdmi_height), (1920, 1080))
        self.assertEqual(res_1080i.effective_hdmi_resolution_label, "1080i")
        self.assertFalse(res_1080i.hdmi_downshifted_to_1080p)

    def test_10_submodel_a_off_hdmi_only_4k_10bit_all_6_frame_rates_and_suppressions(self) -> None:
        expected = (
            "59.94p 10bit",
            "50p 10bit",
            "29.97p 10bit",
            "25p 10bit",
            "23.98p 10bit",
            "24.00p 10bit",
        )
        self.assertEqual(p213.VALID_HDMI_ONLY_4K_SETTINGS, expected)
        for opt in expected:
            res = p213.probe_hdmi_log1080_vs_hdmionly_4k_blank_lcd_hil(
                rec_media_dur_hdmi="Off(HDMI Only)",
                hdmi_raw_output="Off",
                hdmi_only_4k_setting=opt,
                log_shooting="Cine EI",
                requested_hdmi_info_display="On",
                desqueeze_option="1.6x",
            )
            self.assertTrue(res.admitted, msg=opt)
            self.assertEqual((res.effective_hdmi_width, res.effective_hdmi_height), (3840, 2160))
            self.assertEqual(res.effective_hdmi_bit_depth, 10)
            self.assertFalse(res.hdmi_downshifted_to_1080p)
            self.assertFalse(res.internal_card_recording_active)
            self.assertEqual(res.effective_hdmi_info_display, "Off")
            self.assertFalse(res.hdmi_desqueeze_active)
            self.assertFalse(res.camera_lcd_blanked)

    def test_11_submodel_a_off_hdmi_only_blocks_internal_card_recording_eopnotsupp(self) -> None:
        for raw_flag in ("Off", "On"):
            blocked = p213.probe_hdmi_log1080_vs_hdmionly_4k_blank_lcd_hil(
                rec_media_dur_hdmi="Off(HDMI Only)",
                hdmi_raw_output=raw_flag,
                attempt_internal_card_rec=True,
            )
            self.assertFalse(blocked.admitted, msg=raw_flag)
            self.assertFalse(blocked.internal_card_recording_active)
            self.assertEqual(blocked.errno_code, p213.EOPNOTSUPP_ERRNO)

    def test_12_submodel_a_hdmi_info_display_on_blanks_builtin_camera_lcd_and_rec_tally(self) -> None:
        info_on = p213.probe_hdmi_log1080_vs_hdmionly_4k_blank_lcd_hil(
            rec_media_dur_hdmi="On",
            log_shooting="Cine EI",
            requested_hdmi_info_display="On",
            emphasized_rec_display="On",
        )
        self.assertTrue(info_on.admitted)
        self.assertEqual(info_on.effective_hdmi_info_display, "On")
        self.assertTrue(info_on.camera_lcd_blanked)
        self.assertTrue(info_on.hdmi_emphasized_rec_tally_active)

        info_on_tally_off = p213.probe_hdmi_log1080_vs_hdmionly_4k_blank_lcd_hil(
            rec_media_dur_hdmi="On",
            log_shooting="Cine EI",
            requested_hdmi_info_display="On",
            emphasized_rec_display="Off",
        )
        self.assertTrue(info_on_tally_off.camera_lcd_blanked)
        self.assertFalse(info_on_tally_off.hdmi_emphasized_rec_tally_active)

        info_off = p213.probe_hdmi_log1080_vs_hdmionly_4k_blank_lcd_hil(
            rec_media_dur_hdmi="On",
            log_shooting="Cine EI",
            requested_hdmi_info_display="Off",
            emphasized_rec_display="On",
        )
        self.assertFalse(info_off.camera_lcd_blanked)
        self.assertFalse(info_off.hdmi_emphasized_rec_tally_active)

    def test_13_submodel_a_hdmi_raw_4264x2408_bypasses_1080p_downshift_and_hud(self) -> None:
        raw_res = p213.probe_hdmi_log1080_vs_hdmionly_4k_blank_lcd_hil(
            rec_media_dur_hdmi="On",
            hdmi_raw_output="On",
            log_shooting="Cine EI",
            requested_hdmi_info_display="On",
            desqueeze_option="1.6x",
        )
        self.assertTrue(raw_res.admitted)
        self.assertEqual((raw_res.effective_hdmi_width, raw_res.effective_hdmi_height), (4264, 2408))
        self.assertEqual(raw_res.effective_hdmi_bit_depth, 16)
        self.assertFalse(raw_res.hdmi_downshifted_to_1080p)
        self.assertEqual(raw_res.effective_hdmi_info_display, "Off")
        self.assertFalse(raw_res.camera_lcd_blanked)
        self.assertFalse(raw_res.hdmi_desqueeze_active)
        self.assertTrue(raw_res.internal_card_recording_active)

    def test_14_submodel_a_invalid_resolution_einval_and_validation_errors(self) -> None:
        bad_res = p213.probe_hdmi_log1080_vs_hdmionly_4k_blank_lcd_hil(
            requested_output_resolution="720p"
        )
        self.assertFalse(bad_res.admitted)
        self.assertEqual(bad_res.errno_code, p213.EINVAL_ERRNO)

        bad_4k = p213.probe_hdmi_log1080_vs_hdmionly_4k_blank_lcd_hil(
            rec_media_dur_hdmi="Off(HDMI Only)",
            hdmi_only_4k_setting="119.88p 10bit",
        )
        self.assertFalse(bad_4k.admitted)
        self.assertEqual(bad_4k.errno_code, p213.EINVAL_ERRNO)

        with self.assertRaises(p213.RealHwHdmiLog1080ProxyVaultFocusMagBrightMonError):
            p213.probe_hdmi_log1080_vs_hdmionly_4k_blank_lcd_hil(rec_media_dur_hdmi="Invalid")
        with self.assertRaises(p213.RealHwHdmiLog1080ProxyVaultFocusMagBrightMonError):
            p213.probe_hdmi_log1080_vs_hdmionly_4k_blank_lcd_hil(record_setting_bit_depth=12)

    def test_15_pillar_a_evaluator_matrix_passes_100pct(self) -> None:
        pa = p213.evaluate_pillar_a_hdmi_log1080_vs_hdmionly_4k_blank_lcd_hil()
        self.assertTrue(pa["passed"])
        self.assertEqual(len(pa["log_downshift_1080p_matrix"]), 3)
        self.assertEqual(len(pa["pplut_downshift_1080p_matrix"]), 4)
        self.assertEqual(len(pa["hdmi_only_4k_10bit_matrix"]), 6)

    def test_16_submodel_b_proxy_xavc_hs_hd_1080p_10bit_16m_and_9m_default(self) -> None:
        hs_def = p213.probe_proxy_dual_codec_and_coupled_vault_hil(
            proxy_file_format="XAVC HS HD",
            rec_frame_rate="50p",
            clip_id="C0042",
        )
        self.assertTrue(hs_def.admitted)
        self.assertTrue(hs_def.proxy_generated)
        self.assertEqual((hs_def.proxy_width, hs_def.proxy_height), (1920, 1080))
        self.assertEqual(hs_def.proxy_bit_depth, 10)
        self.assertEqual(hs_def.proxy_codec_name, "MPEG-H HEVC/H.265")
        self.assertEqual(hs_def.proxy_record_setting, "9M 4:2:0 10bit")
        self.assertEqual(hs_def.main_clip_path, "/PRIVATE/M4ROOT/CLIP/C0042.MP4")
        self.assertEqual(hs_def.proxy_sub_path, "/PRIVATE/M4ROOT/SUB/C0042S03.MP4")
        self.assertTrue(hs_def.px_badge_displayed)

        hs_16m = p213.probe_proxy_dual_codec_and_coupled_vault_hil(
            proxy_file_format="XAVC HS HD",
            proxy_record_setting="16M 4:2:0 10bit",
            rec_frame_rate="59.94p",
        )
        self.assertTrue(hs_16m.admitted)
        self.assertTrue(hs_16m.proxy_generated)
        self.assertEqual(hs_16m.proxy_record_setting, "16M 4:2:0 10bit")

    def test_17_submodel_b_proxy_xavc_s_hd_720p_8bit_6m_overall_default(self) -> None:
        s_def = p213.probe_proxy_dual_codec_and_coupled_vault_hil(rec_frame_rate="23.98p")
        self.assertTrue(s_def.admitted)
        self.assertTrue(s_def.proxy_generated)
        self.assertEqual(s_def.proxy_file_format, "XAVC S HD")
        self.assertEqual(s_def.proxy_record_setting, "6M 4:2:0 8bit")
        self.assertEqual((s_def.proxy_width, s_def.proxy_height), (1280, 720))
        self.assertEqual(s_def.proxy_bit_depth, 8)
        self.assertEqual(s_def.proxy_codec_name, "MPEG-4 AVC/H.264")
        self.assertTrue(s_def.main_clip_exists)
        self.assertTrue(s_def.proxy_sub_exists)

    def test_18_submodel_b_proxy_blocked_at_normal_119_88p_and_100p(self) -> None:
        for hfr in ("100p", "119.88p"):
            res = p213.probe_proxy_dual_codec_and_coupled_vault_hil(
                capture_mode="Movie",
                rec_frame_rate=hfr,
            )
            self.assertFalse(res.admitted, msg=hfr)
            self.assertTrue(res.main_clip_exists)
            self.assertFalse(res.proxy_sub_exists)
            self.assertFalse(res.proxy_generated)
            self.assertFalse(res.px_badge_displayed)
            self.assertEqual(res.errno_code, p213.EOPNOTSUPP_ERRNO)

    def test_19_submodel_b_proxy_sq_cutoffs_ge_100_120fps_vs_allowed_sub100fps(self) -> None:
        for rec_hfr in ("100p", "119.88p"):
            r_blk = p213.probe_proxy_dual_codec_and_coupled_vault_hil(
                capture_mode="S&Q",
                rec_frame_rate=rec_hfr,
                sq_sensor_fps=60.0,
            )
            self.assertFalse(r_blk.admitted, msg=rec_hfr)
            self.assertEqual(r_blk.errno_code, p213.EOPNOTSUPP_ERRNO)

        for sq_fps in (100.0, 120.0, 200.0, 240.0):
            s_blk = p213.probe_proxy_dual_codec_and_coupled_vault_hil(
                capture_mode="S&Q",
                rec_frame_rate="23.98p",
                sq_sensor_fps=sq_fps,
            )
            self.assertFalse(s_blk.admitted, msg=str(sq_fps))
            self.assertFalse(s_blk.proxy_generated)
            self.assertEqual(s_blk.errno_code, p213.EOPNOTSUPP_ERRNO)

        for sq_ok in (1.0, 24.0, 50.0, 60.0):
            s_ok = p213.probe_proxy_dual_codec_and_coupled_vault_hil(
                capture_mode="S&Q",
                rec_frame_rate="23.98p",
                sq_sensor_fps=sq_ok,
            )
            self.assertTrue(s_ok.admitted, msg=str(sq_ok))
            self.assertTrue(s_ok.proxy_generated)

    def test_20_submodel_b_proxy_blocked_under_off_hdmi_only_and_proxy_off_mode(self) -> None:
        hdmi_only = p213.probe_proxy_dual_codec_and_coupled_vault_hil(
            rec_media_dur_hdmi="Off(HDMI Only)"
        )
        self.assertFalse(hdmi_only.admitted)
        self.assertFalse(hdmi_only.main_clip_exists)
        self.assertFalse(hdmi_only.proxy_sub_exists)
        self.assertFalse(hdmi_only.proxy_generated)
        self.assertEqual(hdmi_only.errno_code, p213.EOPNOTSUPP_ERRNO)

        px_off = p213.probe_proxy_dual_codec_and_coupled_vault_hil(proxy_recording="Off")
        self.assertTrue(px_off.admitted)
        self.assertTrue(px_off.main_clip_exists)
        self.assertFalse(px_off.proxy_sub_exists)
        self.assertFalse(px_off.proxy_generated)
        self.assertFalse(px_off.px_badge_displayed)

    def test_21_submodel_b_zero_on_camera_proxy_playback_and_px_badge_only(self) -> None:
        pb = p213.probe_proxy_dual_codec_and_coupled_vault_hil(
            vault_operation=p213.VAULT_OP_ATTEMPT_PROXY_PLAYBACK
        )
        self.assertFalse(pb.admitted)
        self.assertFalse(pb.on_camera_proxy_playback_supported)
        self.assertFalse(pb.proxy_visible_in_playback_index)
        self.assertEqual(pb.on_camera_proxy_playback_frames, 0)
        self.assertTrue(pb.px_badge_displayed)
        self.assertEqual(pb.errno_code, p213.EOPNOTSUPP_ERRNO)

    def test_22_submodel_b_atomic_coupled_protect_on_off_and_delete_clip_plus_sub(self) -> None:
        prot_on = p213.probe_proxy_dual_codec_and_coupled_vault_hil(
            vault_operation=p213.VAULT_OP_COUPLED_PROTECT_ON
        )
        self.assertTrue(prot_on.admitted)
        self.assertTrue(prot_on.main_protected)
        self.assertTrue(prot_on.proxy_protected)
        self.assertTrue(prot_on.coupled_pair_intact)

        del_blocked = p213.probe_proxy_dual_codec_and_coupled_vault_hil(
            prior_protected=True,
            vault_operation=p213.VAULT_OP_COUPLED_DELETE,
        )
        self.assertFalse(del_blocked.admitted)
        self.assertTrue(del_blocked.main_clip_exists)
        self.assertTrue(del_blocked.proxy_sub_exists)
        self.assertEqual(del_blocked.errno_code, p213.EACCES_ERRNO)

        prot_off = p213.probe_proxy_dual_codec_and_coupled_vault_hil(
            prior_protected=True,
            vault_operation=p213.VAULT_OP_COUPLED_PROTECT_OFF,
        )
        self.assertTrue(prot_off.admitted)
        self.assertFalse(prot_off.main_protected)
        self.assertFalse(prot_off.proxy_protected)

        del_ok = p213.probe_proxy_dual_codec_and_coupled_vault_hil(
            prior_protected=False,
            vault_operation=p213.VAULT_OP_COUPLED_DELETE,
        )
        self.assertTrue(del_ok.admitted)
        self.assertFalse(del_ok.main_clip_exists)
        self.assertFalse(del_ok.proxy_sub_exists)
        self.assertFalse(del_ok.px_badge_displayed)
        self.assertTrue(del_ok.coupled_pair_intact)

    def test_23_submodel_b_single_sided_mutations_rejected_and_orphan_detection(self) -> None:
        for op in (
            p213.VAULT_OP_SINGLE_DELETE_MAIN,
            p213.VAULT_OP_SINGLE_DELETE_PROXY,
            p213.VAULT_OP_SINGLE_PROTECT_MAIN,
            p213.VAULT_OP_SINGLE_PROTECT_PROXY,
        ):
            rej = p213.probe_proxy_dual_codec_and_coupled_vault_hil(vault_operation=op)
            self.assertFalse(rej.admitted, msg=op)
            self.assertTrue(rej.single_sided_mutation_rejected)
            self.assertEqual(rej.single_sided_proxy_or_main_orphan_mutations, 0)
            self.assertTrue(rej.coupled_pair_intact)
            self.assertEqual(rej.errno_code, p213.EOPNOTSUPP_ERRNO)

        for orphan_mode in ("ORPHAN_SUB_WITHOUT_CLIP", "ORPHAN_CLIP_MISSING_EXPECTED_SUB"):
            orph = p213.probe_proxy_dual_codec_and_coupled_vault_hil(
                simulate_external_orphan_state=orphan_mode
            )
            self.assertFalse(orph.admitted, msg=orphan_mode)
            self.assertTrue(orph.orphan_detected)
            self.assertFalse(orph.coupled_pair_intact)
            self.assertEqual(orph.errno_code, p213.EINVAL_ERRNO)

    def test_24_submodel_b_format_bitrate_mismatch_einval_and_validation_errors(self) -> None:
        bad_pair1 = p213.probe_proxy_dual_codec_and_coupled_vault_hil(
            proxy_file_format="XAVC S HD",
            proxy_record_setting="16M 4:2:0 10bit",
        )
        self.assertFalse(bad_pair1.admitted)
        self.assertEqual(bad_pair1.errno_code, p213.EINVAL_ERRNO)

        bad_pair2 = p213.probe_proxy_dual_codec_and_coupled_vault_hil(
            proxy_file_format="XAVC HS HD",
            proxy_record_setting="6M 4:2:0 8bit",
        )
        self.assertFalse(bad_pair2.admitted)
        self.assertEqual(bad_pair2.errno_code, p213.EINVAL_ERRNO)

        bad_fmt = p213.probe_proxy_dual_codec_and_coupled_vault_hil(
            proxy_file_format="ProRes Proxy"
        )
        self.assertFalse(bad_fmt.admitted)
        self.assertEqual(bad_fmt.errno_code, p213.EINVAL_ERRNO)

        with self.assertRaises(p213.RealHwHdmiLog1080ProxyVaultFocusMagBrightMonError):
            p213.probe_proxy_dual_codec_and_coupled_vault_hil(sq_sensor_fps=300.0)
        with self.assertRaises(p213.RealHwHdmiLog1080ProxyVaultFocusMagBrightMonError):
            p213.probe_proxy_dual_codec_and_coupled_vault_hil(vault_operation="FORMAT_CARD")

    def test_25_pillar_b_evaluator_matrix_passes_100pct(self) -> None:
        pb = p213.evaluate_pillar_b_proxy_dual_codec_and_coupled_vault_hil()
        self.assertTrue(pb["passed"])
        self.assertEqual(
            pb["on_camera_proxy_playback_blocked"]["on_camera_proxy_playback_frames"],
            0,
        )

    def test_26_submodel_c_movie_initial_focus_mag_x1_0_and_x4_0_vs_invalid_still_scales(self) -> None:
        for mode in ("Movie", "S&Q"):
            for scale_lbl, expected_val in (("x1.0", 1.0), ("x4.0", 4.0)):
                ok = p213.probe_focus_mag_and_bright_monitoring_hil(
                    capture_mode=mode,
                    initial_focus_mag=scale_lbl,
                    trigger_source=p213.MAG_TRIGGER_CUSTOM_KEY,
                )
                self.assertTrue(ok.admitted, msg=f"{mode}/{scale_lbl}")
                self.assertTrue(ok.focus_magnifier_active)
                self.assertAlmostEqual(ok.applied_mag_scale, expected_val)

            for bad_scale in ("x2.1", "x1.5", "x8.0"):
                bad = p213.probe_focus_mag_and_bright_monitoring_hil(
                    capture_mode=mode,
                    initial_focus_mag=bad_scale,
                )
                self.assertFalse(bad.admitted, msg=f"{mode}/{bad_scale}")
                self.assertEqual(bad.errno_code, p213.EINVAL_ERRNO)

    def test_27_submodel_c_still_photo_initial_focus_mag_ff_x2_1_vs_apsc_s35_x1_5(self) -> None:
        ff_ok = p213.probe_focus_mag_and_bright_monitoring_hil(
            capture_mode="Photo",
            sensor_crop_mode=p213.CROP_FULL_FRAME,
            initial_focus_mag="x2.1",
            trigger_source=p213.MAG_TRIGGER_CUSTOM_KEY,
        )
        self.assertTrue(ff_ok.admitted)
        self.assertAlmostEqual(ff_ok.applied_mag_scale, 2.1)

        ff_reject_apsc = p213.probe_focus_mag_and_bright_monitoring_hil(
            capture_mode="Photo",
            sensor_crop_mode=p213.CROP_FULL_FRAME,
            initial_focus_mag="x1.5",
        )
        self.assertFalse(ff_reject_apsc.admitted)
        self.assertEqual(ff_reject_apsc.errno_code, p213.EINVAL_ERRNO)

        apsc_ok = p213.probe_focus_mag_and_bright_monitoring_hil(
            capture_mode="Photo",
            sensor_crop_mode=p213.CROP_APSC_S35,
            initial_focus_mag="x1.5",
            trigger_source=p213.MAG_TRIGGER_CUSTOM_KEY,
        )
        self.assertTrue(apsc_ok.admitted)
        self.assertAlmostEqual(apsc_ok.applied_mag_scale, 1.5)

        apsc_reject_x4 = p213.probe_focus_mag_and_bright_monitoring_hil(
            capture_mode="Photo",
            sensor_crop_mode=p213.CROP_APSC_S35,
            initial_focus_mag="x4.0",
        )
        self.assertFalse(apsc_reject_x4.admitted)
        self.assertEqual(apsc_reject_x4.errno_code, p213.EINVAL_ERRNO)

    def test_28_submodel_c_auto_magnifier_in_mf_blocked_in_movie_and_active_in_photo_mf(self) -> None:
        for mv_mode in ("Movie", "S&Q"):
            blk = p213.probe_focus_mag_and_bright_monitoring_hil(
                capture_mode=mv_mode,
                initial_focus_mag="x4.0",
                trigger_source=p213.MAG_TRIGGER_FOCUS_RING_AUTO,
            )
            self.assertFalse(blk.admitted, msg=mv_mode)
            self.assertTrue(blk.auto_magnifier_in_mf_blocked_in_movie)
            self.assertFalse(blk.focus_magnifier_active)
            self.assertEqual(blk.errno_code, p213.EOPNOTSUPP_ERRNO)

        photo_ring_on = p213.probe_focus_mag_and_bright_monitoring_hil(
            capture_mode="Photo",
            focus_mode="MF",
            initial_focus_mag="x2.1",
            auto_magnifier_in_mf="On",
            trigger_source=p213.MAG_TRIGGER_FOCUS_RING_AUTO,
        )
        self.assertTrue(photo_ring_on.admitted)
        self.assertTrue(photo_ring_on.focus_magnifier_active)
        self.assertAlmostEqual(photo_ring_on.applied_mag_scale, 2.1)

        photo_ring_off = p213.probe_focus_mag_and_bright_monitoring_hil(
            capture_mode="Photo",
            focus_mode="MF",
            initial_focus_mag="x2.1",
            auto_magnifier_in_mf="Off",
            trigger_source=p213.MAG_TRIGGER_FOCUS_RING_AUTO,
        )
        self.assertTrue(photo_ring_off.admitted)
        self.assertFalse(photo_ring_off.focus_magnifier_active)
        self.assertAlmostEqual(photo_ring_off.applied_mag_scale, 1.0)

    def test_29_submodel_c_marker_display_suppressed_while_focus_magnifier_active(self) -> None:
        mag_on = p213.probe_focus_mag_and_bright_monitoring_hil(
            capture_mode="Movie",
            initial_focus_mag="x4.0",
            trigger_source=p213.MAG_TRIGGER_CUSTOM_KEY,
            requested_marker_display="On",
        )
        self.assertTrue(mag_on.focus_magnifier_active)
        self.assertEqual(mag_on.effective_marker_display, "Off")
        self.assertTrue(mag_on.marker_display_suppressed)

        mag_idle = p213.probe_focus_mag_and_bright_monitoring_hil(
            capture_mode="Movie",
            initial_focus_mag="x4.0",
            trigger_source=p213.MAG_TRIGGER_IDLE,
            requested_marker_display="On",
        )
        self.assertFalse(mag_idle.focus_magnifier_active)
        self.assertEqual(mag_idle.effective_marker_display, "On")
        self.assertFalse(mag_idle.marker_display_suppressed)

    def test_30_submodel_c_bright_monitoring_custom_key_locked_while_magnified(self) -> None:
        locked_key = p213.probe_focus_mag_and_bright_monitoring_hil(
            capture_mode="Movie",
            initial_focus_mag="x4.0",
            trigger_source=p213.MAG_TRIGGER_CUSTOM_KEY,
            press_bright_monitoring_custom_key=True,
        )
        self.assertFalse(locked_key.admitted)
        self.assertTrue(locked_key.focus_magnifier_active)
        self.assertTrue(locked_key.bright_monitoring_key_locked_out)
        self.assertFalse(locked_key.effective_bright_monitoring)
        self.assertEqual(locked_key.errno_code, p213.EOPNOTSUPP_ERRNO)

        locked_auto_mf = p213.probe_focus_mag_and_bright_monitoring_hil(
            capture_mode="Photo",
            initial_focus_mag="x2.1",
            focus_mode="MF",
            auto_magnifier_in_mf="On",
            trigger_source=p213.MAG_TRIGGER_FOCUS_RING_AUTO,
            press_bright_monitoring_custom_key=True,
        )
        self.assertFalse(locked_auto_mf.admitted)
        self.assertTrue(locked_auto_mf.bright_monitoring_key_locked_out)
        self.assertEqual(locked_auto_mf.errno_code, p213.EOPNOTSUPP_ERRNO)

    def test_31_submodel_c_bright_monitoring_pasm_mf_toggle_and_setting_effect_off(self) -> None:
        for exp in ("P", "A", "S", "M"):
            bm_on = p213.probe_focus_mag_and_bright_monitoring_hil(
                capture_mode="Photo",
                exposure_mode=exp,
                focus_mode="MF",
                trigger_source=p213.MAG_TRIGGER_IDLE,
                prior_bright_monitoring_active=False,
                press_bright_monitoring_custom_key=True,
                requested_live_view_display="Setting Effect ON",
            )
            self.assertTrue(bm_on.admitted, msg=exp)
            self.assertTrue(bm_on.effective_bright_monitoring)
            self.assertEqual(bm_on.effective_live_view_display, "Setting Effect OFF")
            self.assertTrue(bm_on.live_view_forced_setting_effect_off)

        bm_toggle_off = p213.probe_focus_mag_and_bright_monitoring_hil(
            capture_mode="Photo",
            exposure_mode="M",
            focus_mode="MF",
            trigger_source=p213.MAG_TRIGGER_IDLE,
            prior_bright_monitoring_active=True,
            press_bright_monitoring_custom_key=True,
            requested_live_view_display="Setting Effect ON",
        )
        self.assertTrue(bm_toggle_off.admitted)
        self.assertFalse(bm_toggle_off.effective_bright_monitoring)
        self.assertEqual(bm_toggle_off.effective_live_view_display, "Setting Effect ON")
        self.assertFalse(bm_toggle_off.live_view_forced_setting_effect_off)

    def test_32_submodel_c_bright_monitoring_auto_cancels_outside_pasm_mf_or_poweroff(self) -> None:
        for non_pasm in ("Auto", "SCN", "Flexible_Auto"):
            canc_exp = p213.probe_focus_mag_and_bright_monitoring_hil(
                capture_mode="Photo",
                exposure_mode=non_pasm,
                focus_mode="MF",
                trigger_source=p213.MAG_TRIGGER_IDLE,
                prior_bright_monitoring_active=True,
            )
            self.assertTrue(canc_exp.admitted, msg=non_pasm)
            self.assertFalse(canc_exp.effective_bright_monitoring)
            self.assertTrue(canc_exp.bright_monitoring_auto_canceled)
            self.assertIn("EXPOSURE_MODE_OUTSIDE_PASM", canc_exp.auto_cancel_reasons)

        for non_mf in ("AF-S", "AF-C", "DMF"):
            canc_af = p213.probe_focus_mag_and_bright_monitoring_hil(
                capture_mode="Photo",
                exposure_mode="M",
                focus_mode=non_mf,
                trigger_source=p213.MAG_TRIGGER_IDLE,
                prior_bright_monitoring_active=True,
            )
            self.assertTrue(canc_af.admitted, msg=non_mf)
            self.assertFalse(canc_af.effective_bright_monitoring)
            self.assertTrue(canc_af.bright_monitoring_auto_canceled)
            self.assertIn("FOCUS_MODE_NOT_MF", canc_af.auto_cancel_reasons)

        canc_pwr = p213.probe_focus_mag_and_bright_monitoring_hil(
            capture_mode="Photo",
            exposure_mode="M",
            focus_mode="MF",
            trigger_source=p213.MAG_TRIGGER_IDLE,
            prior_bright_monitoring_active=True,
            camera_power_off=True,
        )
        self.assertTrue(canc_pwr.bright_monitoring_auto_canceled)
        self.assertIn("CAMERA_POWER_OFF", canc_pwr.auto_cancel_reasons)

    def test_33_submodel_c_bright_monitoring_activation_rejected_outside_pasm_or_mf(self) -> None:
        rej = p213.probe_focus_mag_and_bright_monitoring_hil(
            capture_mode="Photo",
            exposure_mode="Auto",
            focus_mode="AF-C",
            trigger_source=p213.MAG_TRIGGER_IDLE,
            press_bright_monitoring_custom_key=True,
        )
        self.assertFalse(rej.admitted)
        self.assertFalse(rej.effective_bright_monitoring)
        self.assertEqual(rej.errno_code, p213.EOPNOTSUPP_ERRNO)

        bad_time = p213.probe_focus_mag_and_bright_monitoring_hil(
            focus_magnif_time="10 Sec"
        )
        self.assertFalse(bad_time.admitted)
        self.assertEqual(bad_time.errno_code, p213.EINVAL_ERRNO)

        with self.assertRaises(p213.RealHwHdmiLog1080ProxyVaultFocusMagBrightMonError):
            p213.probe_focus_mag_and_bright_monitoring_hil(capture_mode="Interval")

    def test_34_hard_safety_redline_baseline_and_all_8_forbidden_actions(self) -> None:
        base = p213.probe_hard_safety_redline()
        self.assertTrue(base.valid)
        self.assertFalse(base.persistent_emmc_writes_authorized)
        self.assertFalse(base.spi_nor_write_authorized)
        self.assertFalse(base.el3_payload_transmit_authorized)
        self.assertEqual(base.physical_usb_packets_emitted, 0)
        self.assertEqual(base.otp_fuse_touches, 0)
        self.assertEqual(base.rpmb_counter_increments, 0)
        self.assertEqual(base.single_sided_proxy_or_main_orphan_mutations, 0)
        self.assertEqual(base.on_camera_proxy_playback_frames, 0)

        for flag_name in (
            "authorize_persistent_emmc_writes",
            "authorize_spi_nor_write",
            "authorize_el3_payload_transmit",
            "emit_physical_usb_packet",
            "touch_otp_fuse",
            "increment_rpmb_counter",
            "mutate_single_sided_proxy_or_main_clip",
            "force_on_camera_proxy_playback",
        ):
            bad = p213.probe_hard_safety_redline(**{flag_name: True})
            self.assertFalse(bad.valid, msg=flag_name)
            self.assertFalse(bad.persistent_emmc_writes_authorized)
            self.assertFalse(bad.spi_nor_write_authorized)
            self.assertFalse(bad.el3_payload_transmit_authorized)
            self.assertEqual(bad.physical_usb_packets_emitted, 0)
            self.assertEqual(bad.otp_fuse_touches, 0)
            self.assertEqual(bad.rpmb_counter_increments, 0)
            self.assertEqual(bad.single_sided_proxy_or_main_orphan_mutations, 0)
            self.assertEqual(bad.on_camera_proxy_playback_frames, 0)
            self.assertTrue(bad.status_code.startswith("FAIL_CLOSED_REDLINE_BLOCKED:"))

    def test_35_combined_multi_redline_violation_blocked(self) -> None:
        combo = p213.probe_hard_safety_redline(
            authorize_persistent_emmc_writes=True,
            mutate_single_sided_proxy_or_main_clip=True,
            force_on_camera_proxy_playback=True,
        )
        self.assertFalse(combo.valid)
        self.assertIn("PERSISTENT_EMMC_WRITE", combo.blocked_action)
        self.assertIn("SINGLE_SIDED_PROXY_MAIN_ORPHAN_MUTATION", combo.blocked_action)
        self.assertIn("ON_CAMERA_PROXY_SUB_PLAYBACK", combo.blocked_action)

    def test_36_pillar_c_d_evaluator_matrix_passes_100pct(self) -> None:
        pcd = p213.evaluate_pillar_c_d_focus_mag_bright_monitoring_and_redlines()
        self.assertTrue(pcd["passed"])
        self.assertEqual(len(pcd["blocked_redline_probes"]), 8)

    def test_37_clean_room_audit_deterministic_digest_and_zero_leaks(self) -> None:
        r1 = _get_clean_room_audit()
        r2 = p213.run_phase213_realhw_hdmi_log1080_proxy_vault_focusmag_brightmon_hil(
            force_clean_room=True
        )
        self.assertTrue(r1["all_checks_passed"])
        self.assertEqual(r1["source_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(r1["stage_index"], 38)
        self.assertEqual(r1["stage_total"], 38)
        self.assertEqual(r1["milestone"], "38/38")
        self.assertEqual(r1["audit_digest_sha256"], r2["audit_digest_sha256"])
        self.assertEqual(r1["redlines"]["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(r1["donor_audit"]["raw_firmware_bytes_leaked"], 0)

    def test_38_default_mode_audit_passes_all_pillars_and_redlines(self) -> None:
        rep = _get_default_audit()
        self.assertTrue(rep["all_checks_passed"])
        self.assertIn(rep["source_mode"], ("LOCAL_DONOR_RDONLY", "CLEAN_ROOM_SYNTHETIC"))
        self.assertTrue(rep["pillar_a_hdmi_log1080_vs_hdmionly_4k_blank_lcd_hil"]["passed"])
        self.assertTrue(rep["pillar_b_proxy_dual_codec_and_coupled_vault_hil"]["passed"])
        self.assertTrue(rep["pillar_c_d_focus_mag_bright_monitoring_and_redlines"]["passed"])
        self.assertFalse(rep["redlines"]["persistent_emmc_writes_authorized"])
        self.assertFalse(rep["redlines"]["spi_nor_write_authorized"])
        self.assertFalse(rep["redlines"]["el3_payload_transmit_authorized"])
        self.assertEqual(rep["redlines"]["physical_usb_packets_emitted"], 0)
        self.assertEqual(rep["redlines"]["otp_fuse_touches"], 0)
        self.assertEqual(rep["redlines"]["rpmb_counter_increments"], 0)
        self.assertEqual(rep["redlines"]["single_sided_proxy_or_main_orphan_mutations"], 0)
        self.assertEqual(rep["redlines"]["on_camera_proxy_playback_frames"], 0)

    def test_39_standalone_cli_self_test_summary_and_clean_room_json(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        p_sum = subprocess.run(
            [
                "/usr/bin/python3",
                "-B",
                str(
                    FX3_VM_DIR
                    / "realhw_hdmi_log1080_proxy_vault_focusmag_brightmon_coemulator.py"
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
        self.assertIn("[PASS] Phase 213 Stage 38 (38/38)", p_sum.stdout)

        p_json = subprocess.run(
            [
                "/usr/bin/python3",
                "-B",
                str(
                    FX3_VM_DIR
                    / "realhw_hdmi_log1080_proxy_vault_focusmag_brightmon_coemulator.py"
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
        self.assertEqual(parsed["stage_index"], 38)
        self.assertEqual(parsed["milestone"], "38/38")

    def test_40_inprocess_main_summary_and_clean_room_exit_zero(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = p213.main(["--self-test", "--clean-room", "--summary"])
        self.assertEqual(rc, 0)
        self.assertIn("[PASS] Phase 213 Stage 38 (38/38)", buf.getvalue())

    def test_41_fx3_vm_coemulation_suite_includes_stage38_and_skip_phase213(self) -> None:
        rep_on, _dt = _get_clean_room_suite()
        self.assertTrue(rep_on["all_checks_passed"])
        self.assertIn(
            "stage38_realhw_hdmi_log1080_proxy_vault_focusmag_brightmon_hil",
            rep_on,
        )
        s38 = rep_on["stage38_realhw_hdmi_log1080_proxy_vault_focusmag_brightmon_hil"]
        self.assertTrue(s38["all_checks_passed"])
        self.assertFalse(s38["persistent_emmc_writes_authorized"])
        self.assertFalse(s38["spi_nor_write_authorized"])
        self.assertFalse(s38["el3_payload_transmit_authorized"])
        self.assertEqual(s38["physical_usb_packets_emitted"], 0)
        self.assertEqual(s38["otp_fuse_touches"], 0)
        self.assertEqual(s38["rpmb_counter_increments"], 0)
        self.assertEqual(s38["single_sided_proxy_or_main_orphan_mutations"], 0)
        self.assertEqual(s38["on_camera_proxy_playback_frames"], 0)
        self.assertEqual(s38["raw_firmware_bytes_leaked"], 0)

        stage_keys = [k for k in rep_on if re.match(r"^stage\d+_", k)]
        self.assertGreaterEqual(len(stage_keys), 38)

        rep_skip = suite.run_fx3_vm_coemulation_suite(
            suite.CoEmulationConfig(
                force_clean_room=True,
                include_phase213_realhw_hdmi_log1080_proxy_vault_focusmag_brightmon_hil=False,
            )
        )
        self.assertTrue(rep_skip["all_checks_passed"])
        self.assertNotIn(
            "stage38_realhw_hdmi_log1080_proxy_vault_focusmag_brightmon_hil",
            rep_skip,
        )
        self.assertGreaterEqual(len([k for k in rep_skip if re.match(r"^stage\d+_", k)]), 37)

    def test_42_all_38_of_38_stages_present_and_passing_in_suite(self) -> None:
        rep, _dt = _get_clean_room_suite()
        self.assertTrue(rep["stage1_coldboot_and_bt"]["all_checks_passed"])
        self.assertTrue(rep["stage2_dual_isa_cp_shooting"]["all_checks_passed"])
        self.assertTrue(rep["stage3_soft_gpe_hud_ramfb"]["all_checks_passed"])
        for idx in range(4, 39):
            matches = [k for k in rep if k.startswith(f"stage{idx}_")]
            self.assertEqual(len(matches), 1, msg=f"Missing or duplicate stage{idx}_* key")
            self.assertTrue(rep[matches[0]]["all_checks_passed"], msg=matches[0])

    def test_43_suite_subprocess_summary_and_skip_phase213_flag(self) -> None:
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
            "realhw_hdmi_log1080_proxy_vault_focusmag_brightmon_hil=CLEAN_ROOM_SYNTHETIC",
            proc.stdout,
        )

        proc_skip = subprocess.run(
            [
                "/usr/bin/python3",
                "-B",
                str(FX3_VM_DIR / "fx3_vm_coemulation_suite.py"),
                "--clean-room",
                "--skip-phase213",
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
            "realhw_hdmi_log1080_proxy_vault_focusmag_brightmon_hil=",
            proc_skip.stdout,
        )

    def test_44_suite_38_stages_under_6s_wall_clock_ceiling_and_json_cli(self) -> None:
        rep_clean, dt_clean = _get_clean_room_suite()
        self.assertTrue(rep_clean["all_checks_passed"])
        self.assertGreaterEqual(len([k for k in rep_clean if re.match(r"^stage\d+_", k)]), 38)
        self.assertLess(dt_clean, 6.0)

        rep_def, dt_def = _get_default_suite()
        self.assertTrue(rep_def["all_checks_passed"])
        self.assertGreaterEqual(len([k for k in rep_def if re.match(r"^stage\d+_", k)]), 38)
        self.assertLess(dt_def, 6.0)

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc_json = suite.main(["--clean-room", "--json"])
        self.assertEqual(rc_json, 0)
        parsed = json.loads(buf.getvalue())
        self.assertTrue(parsed["all_checks_passed"])
        self.assertIn(
            "stage38_realhw_hdmi_log1080_proxy_vault_focusmag_brightmon_hil",
            parsed,
        )

    def test_45_source_hygiene_rdonly_only_and_no_forbidden_write_flags_or_ports(self) -> None:
        src = (
            FX3_VM_DIR / "realhw_hdmi_log1080_proxy_vault_focusmag_brightmon_coemulator.py"
        ).read_text(encoding="utf-8")
        self.assertIn("os.O_RDONLY", src)
        self.assertNotIn("O_WR" + "ONLY", src)
        self.assertNotIn("O_RD" + "WR", src)
        self.assertNotIn("87" + "68", src)

    def test_46_is_forced_clean_room_truthy_and_falsy_values(self) -> None:
        for truthy in ("1", "true", "TRUE", "yes", "on", " 1 "):
            self.assertTrue(
                p213.is_forced_clean_room({"FX3_FX6_FORCE_CLEAN_ROOM": truthy}),
                msg=truthy,
            )
        for falsy in ("", "0", "false", "no", "off"):
            self.assertFalse(
                p213.is_forced_clean_room({"FX3_FX6_FORCE_CLEAN_ROOM": falsy}),
                msg=falsy,
            )

    def test_47_missing_work_root_gracefully_falls_back_to_clean_room_synthetic(self) -> None:
        non_existent = str(REPO_ROOT / "work" / "__nonexistent_phase213_donor_root__")
        env_missing = {
            "FX3_FX6_FORCE_CLEAN_ROOM": "0",
            "FX3_FX6_MAC_WORK_ROOT": non_existent,
        }
        paths = p213.resolve_phase213_donor_paths(env=env_missing)
        self.assertEqual(len(paths), 12)
        da = p213.inspect_phase213_donors(force_clean_room=True, env=env_missing)
        self.assertEqual(da.source_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_48_combined_log_and_pplut_downshift_and_multi_reason_bright_cancel(self) -> None:
        combo_hdmi = p213.probe_hdmi_log1080_vs_hdmionly_4k_blank_lcd_hil(
            rec_media_dur_hdmi="On",
            requested_output_resolution="Auto",
            log_shooting="Flexible ISO",
            picture_profile="PPLUT2",
            desqueeze_option="1.6x",
        )
        self.assertTrue(combo_hdmi.admitted)
        self.assertTrue(combo_hdmi.hdmi_downshifted_to_1080p)
        self.assertEqual(
            combo_hdmi.downshift_trigger_reason,
            "LOG_SHOOTING:Flexible ISO+PICTURE_PROFILE:PPLUT2",
        )
        self.assertTrue(combo_hdmi.hdmi_desqueeze_active)

        combo_cancel = p213.probe_focus_mag_and_bright_monitoring_hil(
            capture_mode="Photo",
            exposure_mode="Auto",
            focus_mode="AF-C",
            trigger_source=p213.MAG_TRIGGER_IDLE,
            prior_bright_monitoring_active=True,
            camera_power_off=True,
        )
        self.assertTrue(combo_cancel.bright_monitoring_auto_canceled)
        self.assertEqual(
            combo_cancel.auto_cancel_reasons,
            (
                "CAMERA_POWER_OFF",
                "EXPOSURE_MODE_OUTSIDE_PASM",
                "FOCUS_MODE_NOT_MF",
            ),
        )


if __name__ == "__main__":
    unittest.main()
