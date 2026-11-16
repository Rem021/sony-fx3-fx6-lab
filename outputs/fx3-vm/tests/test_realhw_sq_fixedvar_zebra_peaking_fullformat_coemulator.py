#!/usr/bin/env python3
"""Unit tests for Phase 232 Stage 42 (`42/42` Milestone):
Real-Hardware `ILME-FX3` (`0x91030080`, `Ver. 7.02`) Wave-32 `[Mode Settings]` =
`[Fixed/Variable]` Locking Legacy `[S&Q Settings]` & All 6 Hard S&Q Disqualifications,
`[Zebra Display]` / `[Zebra Level]` (`70..100+`, `Custom 1`, `Custom 2`) Survival Across
`[Camera Settings Reset]` (Cleared Only by `[Initialize]`) & Strict Local-LCD-Only HDMI
Clean-Feed Isolation (`0` External HDMI Overlay Pixels for `[Zebra]` and `[Peaking]` Even
When `[HDMI Info. Display]=On`), and Slot 1 `[Format]` (`[Enter]` Quick Format vs `(Delete)`
Full Format + Mid-Cancel Hazard) & Shooting-Screen `MENU + (Delete)` (~2s) Chord Tier-0
Recovery Vault (`pnflasha`/`cnflasha`/`CAMSET01.DAT`) Firewall HIL Co-Emulator.
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
import realhw_sq_fixedvar_zebra_peaking_fullformat_coemulator as p232  # noqa: E402


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
            p232.run_phase232_realhw_sq_fixedvar_zebra_peaking_fullformat_hil(
                force_clean_room=True
            )
        )
    return _CLEAN_ROOM_AUDIT_CACHE


def _get_default_audit():
    global _DEFAULT_AUDIT_CACHE
    if _DEFAULT_AUDIT_CACHE is None:
        _DEFAULT_AUDIT_CACHE = (
            p232.run_phase232_realhw_sq_fixedvar_zebra_peaking_fullformat_hil()
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


class TestPhase232SqFixedVarZebraPeakingFullFormatCoEmulator(unittest.TestCase):
    # ------------------------------------------------------------------
    # Group 1: Schema, Milestone 42/42, Read-Only Donor Inspection (8)
    # ------------------------------------------------------------------
    def test_01_schema_version_stage_42_milestone_and_redline_constants(self) -> None:
        self.assertEqual(
            p232.SCHEMA_ID,
            "realhw_sq_fixedvar_zebra_peaking_fullformat_coemulator_v1",
        )
        self.assertEqual(p232.PHASE_232_SCHEMA, p232.SCHEMA_ID)
        self.assertEqual(p232.PHASE_232_VERSION, "232.0.0")
        self.assertEqual(p232.STAGE_INDEX, 42)
        self.assertEqual(p232.STAGE_TOTAL, 42)
        self.assertEqual(p232.MILESTONE_LABEL, "42/42")
        self.assertEqual(
            p232.STAGE_NAME,
            "stage42_realhw_sq_fixedvar_zebra_peaking_fullformat_hil",
        )
        self.assertEqual(p232.FX3_MODEL_ID, 0x91030080)
        self.assertTrue(p232.P8_CP_MUTATION_FORBIDDEN)
        self.assertTrue(p232.CNFLASHA_USERSPACE_WRITE_BLOCKED)
        self.assertEqual(p232.CNFLASHA_MUTATION_BYTES, 0)
        self.assertFalse(p232.PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(p232.HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        self.assertFalse(p232.OVERALL_READY_FOR_HARDWARE_ATTACH)
        self.assertFalse(p232.ISP_WRITE_AUTHORIZED)
        self.assertFalse(p232.SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(p232.EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        self.assertEqual(p232.PHYSICAL_USB_PACKETS_EMITTED, 0)
        self.assertEqual(p232.OTP_FUSE_TOUCHES, 0)
        self.assertEqual(p232.RPMB_COUNTER_INCREMENTS, 0)
        self.assertEqual(p232.SQ_FIXEDVAR_6LOCK_BYPASS_EVENTS, 0)
        self.assertEqual(p232.HDMI_ZEBRA_OR_PEAKING_LEAKED_OVERLAY_PIXELS, 0)
        self.assertEqual(p232.TIER0_SLOT1_FORMAT_OR_CHORD_WIPE_EVENTS, 0)
        self.assertEqual(p232.RAW_FIRMWARE_BYTES_LEAKED, 0)
        self.assertEqual(p232.DONOR_ACCESS_MODE, "O_RDONLY")

    def test_02_donor_inspection_fast_bounded_and_cached(self) -> None:
        p232._DONOR_AUDIT_CACHE.clear()
        t0 = time.monotonic()
        da1 = p232.inspect_phase232_donors(force_clean_room=False)
        dt1 = time.monotonic() - t0
        t1 = time.monotonic()
        da2 = p232.inspect_phase232_donors(force_clean_room=False)
        dt2 = time.monotonic() - t1

        self.assertTrue(da1.all_contracts_verified)
        self.assertEqual(da1.errors, ())
        self.assertEqual(da1.donor_files_inspected, 12)
        self.assertEqual(da1.raw_firmware_bytes_leaked, 0)
        self.assertEqual(da1.access_mode, "O_RDONLY")
        self.assertIn(da1.source_mode, ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"))
        self.assertEqual(da1, da2)
        self.assertLess(dt1, 1.25 if __import__("os").environ.get("GITHUB_ACTIONS") == "true" else 0.25)
        self.assertLess(dt2, 0.50 if __import__("os").environ.get("GITHUB_ACTIONS") == "true" else 0.05)

    def test_03_clean_room_donor_inspection_synthetic_parity(self) -> None:
        da = p232.inspect_phase232_donors(force_clean_room=True)
        self.assertEqual(da.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(da.all_contracts_verified)
        self.assertTrue(da.sq_fixedvar_and_6locks_proven)
        self.assertTrue(da.zebra_persistence_and_hdmi_cleanfeed_proven)
        self.assertTrue(da.fullformat_and_menu_delete_chord_proven)
        self.assertEqual(da.donor_files_inspected, 12)
        self.assertEqual(da.raw_firmware_bytes_leaked, 0)

    def test_04_env_force_clean_room_flag_variants(self) -> None:
        for truthy in ("1", "true", "TRUE", "yes", "on"):
            self.assertTrue(p232.is_forced_clean_room({p232.ENV_FORCE_CLEAN_ROOM: truthy}))
        for falsy in ("", "0", "false", "no", "off"):
            self.assertFalse(p232.is_forced_clean_room({p232.ENV_FORCE_CLEAN_ROOM: falsy}))

        paths = p232.resolve_phase232_donor_paths(env={p232.ENV_FORCE_CLEAN_ROOM: "1"})
        self.assertEqual(len(paths), 12)
        for p in paths.values():
            self.assertIn(p232.CLEAN_ROOM_SENTINEL_DIRNAME, str(p))

    def test_05_missing_donor_directory_falls_back_cleanly_to_synthetic(self) -> None:
        env = {
            p232.ENV_FORCE_CLEAN_ROOM: "0",
            p232.ENV_MAC_WORK_ROOT: "/nonexistent/fx3_wave32_work_root",
        }
        da = p232.inspect_phase232_donors(env=env)
        self.assertTrue(da.all_contracts_verified)
        self.assertEqual(da.raw_firmware_bytes_leaked, 0)

    def test_06_large_donors_strictly_bounded_window_reads(self) -> None:
        da = p232.inspect_phase232_donors()
        for key in ("fx3_appfw", "fx6_appfw", "fx3_cpapp", "fx6_cpapp", "fx3_libmpr", "fx6_libmpr"):
            summary = getattr(da, key)
            self.assertTrue(summary.bounded_windows_only, msg=key)
            self.assertLessEqual(summary.bytes_read_total, 16 * p232.BOUNDED_WINDOW_MAX_BYTES)
            self.assertEqual(summary.file_bytes, p232.EXPECTED_DONOR_BYTES[key])
            self.assertTrue(all(v == 1 for v in summary.window_hits.values()), msg=key)

    def test_07_compact_uxc_wave32_menu_tokens_verified(self) -> None:
        da = p232.inspect_phase232_donors()
        hits = da.fx3_string_en_f.marker_hits
        for tok in (
            "Mode Settings",
            "Fixed/Variable",
            "S&Q Settings",
            "FPS",
            "Home",
            "Audio Out Timing",
            "Live",
            "Lip Sync",
            "Time Code Run",
            "Time Code Output",
            "XAVC HS 4K",
            "XAVC S 4K",
            "XAVC S-I 4K",
            "XAVC S-I DCI 4K",
            "240fps",
            "200fps",
            "120fps",
            "100fps",
            "Proxy Recording",
            "Zebra Display",
            "Zebra Display Select",
            "Zebra Level",
            "100+",
            "Peaking Display",
            "Peaking Display Select",
            "Peaking Level",
            "Peaking Color",
            "HDMI Info. Display",
            "Camera Settings Reset",
            "Initialize",
            "Format",
            "Quick Format",
            "Full Format",
            "Switch Full Format",
            "Slot 1",
            "Slot 2",
            "Enter",
            "Delete",
        ):
            self.assertEqual(hits.get(tok), 1, msg=f"Missing token {tok!r}")

    def test_08_local_donor_mode_when_present_uses_exact_local_donor_o_rdonly_label(self) -> None:
        if p232.is_forced_clean_room():
            da = p232.inspect_phase232_donors()
            self.assertEqual(da.source_mode, "CLEAN_ROOM_SYNTHETIC")
            return
        paths = p232.resolve_phase232_donor_paths()
        if all(p.is_file() for p in paths.values()):
            da = p232.inspect_phase232_donors(force_clean_room=False)
            self.assertEqual(da.source_mode, "LOCAL_DONOR_O_RDONLY")

    # ------------------------------------------------------------------
    # Group 2: Sub-model A — [Mode Settings]=[Fixed/Variable] & 6 S&Q Locks (14)
    # ------------------------------------------------------------------
    def test_09_submodel_a_fixed_variable_locks_legacy_sq_settings_menu_and_uses_home_fps(
        self,
    ) -> None:
        blk = p232.probe_sq_mode_settings_fixedvar_and_6locks_hil(
            mode_settings="Fixed/Variable",
            attempt_open_legacy_sq_settings_menu=True,
        )
        self.assertFalse(blk.admitted)
        self.assertTrue(blk.legacy_sq_settings_menu_locked)
        self.assertTrue(blk.direct_home_fps_control_active)
        self.assertEqual(blk.fps_control_path, p232.FPS_HOME_CONTROL_PATH)
        self.assertEqual(blk.errno_code, p232.EOPNOTSUPP_ERRNO)

        legacy_ok = p232.probe_sq_mode_settings_fixedvar_and_6locks_hil(
            mode_settings=p232.MODE_SETTINGS_LEGACY_SQ_SEPARATE,
            attempt_open_legacy_sq_settings_menu=True,
            shooting_fps=60,
        )
        self.assertTrue(legacy_ok.admitted)
        self.assertFalse(legacy_ok.legacy_sq_settings_menu_locked)

    def test_10_submodel_a_fixed_fps_movie_enables_2ch_audio_live_lipsync_and_tc(self) -> None:
        for timing in ("Live", "Lip Sync"):
            res = p232.probe_sq_mode_settings_fixedvar_and_6locks_hil(
                mode_settings="Fixed/Variable",
                fps_switch_state="Fixed",
                file_format="XAVC S-I 4K",
                rec_frame_rate="29.97p",
                requested_audio_out_timing=timing,
                proxy_recording_requested="On",
            )
            self.assertTrue(res.admitted, msg=timing)
            self.assertFalse(res.sq_motion_active)
            self.assertEqual(res.audio_channels_recorded, 2)
            self.assertTrue(res.audio_out_timing_available)
            self.assertEqual(res.effective_audio_out_timing, timing)
            self.assertTrue(res.time_code_run_available)
            self.assertTrue(res.time_code_output_available)
            self.assertEqual(res.effective_proxy_recording, "On")
            self.assertEqual(res.active_sq_disqualifications, ())

    def test_11_submodel_a_sq_lock_1_zero_audio_0ch_and_capture_attempt_blocked(self) -> None:
        sq = p232.probe_sq_mode_settings_fixedvar_and_6locks_hil(
            fps_switch_state="Variable",
            shooting_fps=60,
        )
        self.assertTrue(sq.admitted)
        self.assertEqual(sq.audio_channels_recorded, 0)
        self.assertIn(p232.SQ_LOCK_1_ZERO_AUDIO_0CH, sq.active_sq_disqualifications)

        blk = p232.probe_sq_mode_settings_fixedvar_and_6locks_hil(
            fps_switch_state="Variable",
            shooting_fps=60,
            attempt_sq_audio_capture=True,
        )
        self.assertFalse(blk.admitted)
        self.assertIn(p232.SQ_LOCK_1_ZERO_AUDIO_0CH, blk.blocked_disqualifications)
        self.assertEqual(blk.errno_code, p232.EOPNOTSUPP_ERRNO)

    def test_12_submodel_a_sq_lock_2_audio_out_timing_live_and_lipsync_disabled(self) -> None:
        for timing in ("Live", "Lip Sync"):
            blk = p232.probe_sq_mode_settings_fixedvar_and_6locks_hil(
                fps_switch_state="Variable",
                shooting_fps=30,
                requested_audio_out_timing=timing,
                attempt_select_audio_out_timing_in_sq=True,
            )
            self.assertFalse(blk.admitted, msg=timing)
            self.assertFalse(blk.audio_out_timing_available)
            self.assertEqual(blk.effective_audio_out_timing, "Disabled")
            self.assertIn(p232.SQ_LOCK_2_AUDIO_OUT_TIMING_DISABLED, blk.blocked_disqualifications)
            self.assertEqual(blk.errno_code, p232.EOPNOTSUPP_ERRNO)

    def test_13_submodel_a_sq_lock_3_timecode_run_and_output_unavailable(self) -> None:
        blk = p232.probe_sq_mode_settings_fixedvar_and_6locks_hil(
            fps_switch_state="Variable",
            shooting_fps=15,
            requested_tc_run="Rec Run",
            requested_tc_output="On",
            attempt_enable_tc_run_or_output_in_sq=True,
        )
        self.assertFalse(blk.admitted)
        self.assertFalse(blk.time_code_run_available)
        self.assertFalse(blk.time_code_output_available)
        self.assertIn(p232.SQ_LOCK_3_TIMECODE_RUN_OUTPUT_UNAVAILABLE, blk.blocked_disqualifications)
        self.assertEqual(blk.errno_code, p232.EOPNOTSUPP_ERRNO)

    def test_14_submodel_a_sq_lock_4_240fps_ntsc_and_200fps_pal_blocked_across_all_4k_formats(
        self,
    ) -> None:
        for fmt in p232.FOUR_K_FILE_FORMATS_BLOCKING_240_200FPS:
            ntsc_blk = p232.probe_sq_mode_settings_fixedvar_and_6locks_hil(
                tv_region="NTSC",
                file_format=fmt,
                rec_frame_rate="24.00p" if fmt == "XAVC S-I DCI 4K" else "23.98p",
                shooting_fps=240,
            )
            self.assertFalse(ntsc_blk.admitted, msg=f"NTSC {fmt}")
            self.assertIn(p232.SQ_LOCK_4_240_200FPS_4K_BLOCKED, ntsc_blk.blocked_disqualifications)
            self.assertEqual(ntsc_blk.errno_code, p232.EOPNOTSUPP_ERRNO)

            pal_blk = p232.probe_sq_mode_settings_fixedvar_and_6locks_hil(
                tv_region="PAL",
                file_format=fmt,
                rec_frame_rate="25p",
                shooting_fps=200,
            )
            self.assertFalse(pal_blk.admitted, msg=f"PAL {fmt}")
            self.assertIn(p232.SQ_LOCK_4_240_200FPS_4K_BLOCKED, pal_blk.blocked_disqualifications)

    def test_15_submodel_a_hd_formats_admit_240fps_ntsc_and_200fps_pal(self) -> None:
        for hd_fmt in ("XAVC S HD", "XAVC S-I HD"):
            ntsc_ok = p232.probe_sq_mode_settings_fixedvar_and_6locks_hil(
                tv_region="NTSC",
                file_format=hd_fmt,
                rec_frame_rate="23.98p",
                shooting_fps=240,
            )
            self.assertTrue(ntsc_ok.admitted, msg=hd_fmt)
            self.assertAlmostEqual(ntsc_ok.speed_multiplier_vs_playback, 0.0999, places=3)

            pal_ok = p232.probe_sq_mode_settings_fixedvar_and_6locks_hil(
                tv_region="PAL",
                file_format=hd_fmt,
                rec_frame_rate="25p",
                shooting_fps=200,
            )
            self.assertTrue(pal_ok.admitted, msg=hd_fmt)
            self.assertEqual(pal_ok.speed_multiplier_vs_playback, 0.125)

    def test_16_submodel_a_sq_lock_5_120fps_and_100fps_blocked_on_xavc_si_dci_4k_only(
        self,
    ) -> None:
        dci_120 = p232.probe_sq_mode_settings_fixedvar_and_6locks_hil(
            tv_region="NTSC",
            file_format="XAVC S-I DCI 4K",
            rec_frame_rate="24.00p",
            shooting_fps=120,
        )
        self.assertFalse(dci_120.admitted)
        self.assertIn(p232.SQ_LOCK_5_120_100FPS_DCI_4K_BLOCKED, dci_120.blocked_disqualifications)

        dci_100 = p232.probe_sq_mode_settings_fixedvar_and_6locks_hil(
            tv_region="PAL",
            file_format="XAVC S-I DCI 4K",
            rec_frame_rate="25p",
            shooting_fps=100,
        )
        self.assertFalse(dci_100.admitted)
        self.assertIn(p232.SQ_LOCK_5_120_100FPS_DCI_4K_BLOCKED, dci_100.blocked_disqualifications)

        # DCI 4K allows <= 60/50fps; QFHD 4K allows 120/100fps (with Proxy Off)
        dci_60 = p232.probe_sq_mode_settings_fixedvar_and_6locks_hil(
            tv_region="NTSC",
            file_format="XAVC S-I DCI 4K",
            rec_frame_rate="24.00p",
            shooting_fps=60,
        )
        self.assertTrue(dci_60.admitted)

        for qfhd_fmt in ("XAVC HS 4K", "XAVC S 4K", "XAVC S-I 4K"):
            qfhd_120 = p232.probe_sq_mode_settings_fixedvar_and_6locks_hil(
                tv_region="NTSC",
                file_format=qfhd_fmt,
                rec_frame_rate="23.98p",
                shooting_fps=120,
                proxy_recording_requested="Off",
            )
            self.assertTrue(qfhd_120.admitted, msg=qfhd_fmt)

    def test_17_submodel_a_sq_lock_6_proxy_recording_blocked_at_rec_11988p_100p_or_fps_ge_120_100(
        self,
    ) -> None:
        # Allowed at <= 60fps NTSC / <= 50fps PAL when Rec Frame Rate <= 59.94p / 50p
        for px_codec in p232.VALID_PROXY_CODECS:
            ok_60 = p232.probe_sq_mode_settings_fixedvar_and_6locks_hil(
                tv_region="NTSC",
                file_format="XAVC HS 4K",
                rec_frame_rate="59.94p",
                shooting_fps=60,
                proxy_recording_requested="On",
                proxy_codec=px_codec,
            )
            self.assertTrue(ok_60.admitted, msg=px_codec)
            self.assertTrue(ok_60.proxy_recording_available)
            self.assertEqual(ok_60.effective_proxy_recording, "On")

        ok_50_pal = p232.probe_sq_mode_settings_fixedvar_and_6locks_hil(
            tv_region="PAL",
            file_format="XAVC S 4K",
            rec_frame_rate="50p",
            shooting_fps=50,
            proxy_recording_requested="On",
        )
        self.assertTrue(ok_50_pal.admitted)

        # Blocked when Rec Frame Rate == 119.88p or 100p (even at 60/50fps shooting_fps)
        blk_rec_120p = p232.probe_sq_mode_settings_fixedvar_and_6locks_hil(
            tv_region="NTSC",
            file_format="XAVC S 4K",
            rec_frame_rate="119.88p",
            shooting_fps=60,
            proxy_recording_requested="On",
        )
        self.assertFalse(blk_rec_120p.admitted)
        self.assertIn(p232.SQ_LOCK_6_PROXY_REC_BLOCKED_HFR, blk_rec_120p.blocked_disqualifications)

        blk_rec_100p = p232.probe_sq_mode_settings_fixedvar_and_6locks_hil(
            tv_region="PAL",
            file_format="XAVC S 4K",
            rec_frame_rate="100p",
            shooting_fps=50,
            proxy_recording_requested="On",
        )
        self.assertFalse(blk_rec_100p.admitted)
        self.assertIn(p232.SQ_LOCK_6_PROXY_REC_BLOCKED_HFR, blk_rec_100p.blocked_disqualifications)

        # Blocked when shooting_fps >= 120 (NTSC) or >= 100 (PAL)
        for fps_ntsc in (120, 240):
            blk_fps = p232.probe_sq_mode_settings_fixedvar_and_6locks_hil(
                tv_region="NTSC",
                file_format="XAVC S HD",
                rec_frame_rate="23.98p",
                shooting_fps=fps_ntsc,
                proxy_recording_requested="On",
            )
            self.assertFalse(blk_fps.admitted, msg=str(fps_ntsc))
            self.assertIn(p232.SQ_LOCK_6_PROXY_REC_BLOCKED_HFR, blk_fps.blocked_disqualifications)

        for fps_pal in (100, 200):
            blk_fps_pal = p232.probe_sq_mode_settings_fixedvar_and_6locks_hil(
                tv_region="PAL",
                file_format="XAVC S HD",
                rec_frame_rate="25p",
                shooting_fps=fps_pal,
                proxy_recording_requested="On",
            )
            self.assertFalse(blk_fps_pal.admitted, msg=str(fps_pal))
            self.assertIn(
                p232.SQ_LOCK_6_PROXY_REC_BLOCKED_HFR, blk_fps_pal.blocked_disqualifications
            )

    def test_18_submodel_a_quick_motion_1fps_speed_multiplier_verified(self) -> None:
        qm = p232.probe_sq_mode_settings_fixedvar_and_6locks_hil(
            tv_region="NTSC",
            file_format="XAVC HS 4K",
            rec_frame_rate="59.94p",
            shooting_fps=1,
        )
        self.assertTrue(qm.admitted)
        self.assertEqual(qm.speed_multiplier_vs_playback, 59.94)
        self.assertEqual(qm.audio_channels_recorded, 0)

    def test_19_submodel_a_fixed_movie_11988p_and_dci_4k_2400p_rules(self) -> None:
        fixed_hfr_px_blk = p232.probe_sq_mode_settings_fixedvar_and_6locks_hil(
            fps_switch_state="Fixed",
            file_format="XAVC S 4K",
            rec_frame_rate="119.88p",
            proxy_recording_requested="On",
        )
        self.assertFalse(fixed_hfr_px_blk.admitted)
        self.assertEqual(fixed_hfr_px_blk.errno_code, p232.EOPNOTSUPP_ERRNO)

        non_dci_2400p = p232.probe_sq_mode_settings_fixedvar_and_6locks_hil(
            file_format="XAVC S 4K",
            rec_frame_rate="24.00p",
            shooting_fps=60,
        )
        self.assertFalse(non_dci_2400p.admitted)
        self.assertEqual(non_dci_2400p.errno_code, p232.EOPNOTSUPP_ERRNO)

        dci_120p = p232.probe_sq_mode_settings_fixedvar_and_6locks_hil(
            file_format="XAVC S-I DCI 4K",
            rec_frame_rate="119.88p",
            shooting_fps=60,
        )
        self.assertFalse(dci_120p.admitted)

    def test_20_submodel_a_region_mismatch_and_invalid_arguments_rejected(self) -> None:
        ntsc_with_pal_rec = p232.probe_sq_mode_settings_fixedvar_and_6locks_hil(
            tv_region="NTSC", rec_frame_rate="25p"
        )
        self.assertFalse(ntsc_with_pal_rec.admitted)
        self.assertEqual(ntsc_with_pal_rec.errno_code, p232.EINVAL_ERRNO)

        pal_with_ntsc_sq_fps = p232.probe_sq_mode_settings_fixedvar_and_6locks_hil(
            tv_region="PAL", rec_frame_rate="25p", shooting_fps=60
        )
        self.assertFalse(pal_with_ntsc_sq_fps.admitted)
        self.assertEqual(pal_with_ntsc_sq_fps.errno_code, p232.EINVAL_ERRNO)

        for kw in (
            {"mode_settings": "BogusMode"},
            {"fps_switch_state": "Auto"},
            {"file_format": "ProRes 4444"},
            {"rec_frame_rate": "48p"},
            {"shooting_fps": 75},
            {"requested_audio_out_timing": "ZeroLag"},
        ):
            bad = p232.probe_sq_mode_settings_fixedvar_and_6locks_hil(**kw)
            self.assertFalse(bad.admitted, msg=str(kw))
            self.assertEqual(bad.errno_code, p232.EINVAL_ERRNO)

        with self.assertRaises(p232.RealHwSqFixedVarZebraPeakingFullFormatError):
            p232.probe_sq_mode_settings_fixedvar_and_6locks_hil(tv_region="SECAM")

    def test_21_submodel_a_combined_multi_disqualification_probe(self) -> None:
        combo = p232.probe_sq_mode_settings_fixedvar_and_6locks_hil(
            file_format="XAVC S-I DCI 4K",
            rec_frame_rate="24.00p",
            shooting_fps=240,
            attempt_sq_audio_capture=True,
            attempt_select_audio_out_timing_in_sq=True,
            attempt_enable_tc_run_or_output_in_sq=True,
            proxy_recording_requested="On",
        )
        self.assertFalse(combo.admitted)
        self.assertEqual(combo.sq_fixedvar_6lock_bypass_events, 0)
        self.assertGreaterEqual(len(combo.blocked_disqualifications), 5)

    def test_22_pillar_a_evaluator_matrix_passes_100pct(self) -> None:
        pa = p232.evaluate_pillar_a_sq_fixedvar_and_6locks_hil()
        self.assertTrue(pa["passed"])
        self.assertEqual(len(pa["all_6_sq_disqualification_ids"]), 6)

    # ------------------------------------------------------------------
    # Group 3: Sub-model B — Zebra Persistence & HDMI Clean-Feed Isolation (13)
    # ------------------------------------------------------------------
    def test_23_submodel_b_all_10_zebra_levels_presets_and_custom_1_2_admitted(self) -> None:
        for lvl in p232.VALID_ZEBRA_LEVELS:
            res = p232.probe_zebra_persistence_and_hdmi_cleanfeed_isolation_hil(
                configured_zebra_display="On",
                configured_zebra_level=lvl,
                custom1_std_level=60,
                custom1_range_band=5,
                custom2_lower_limit=98,
            )
            self.assertTrue(res.admitted, msg=lvl)
            self.assertEqual(res.effective_zebra_display, "On")
            self.assertEqual(res.effective_zebra_level, lvl)
            self.assertEqual(res.wheel_left_default_assignment, "Zebra Display Select")
            self.assertEqual(res.wheel_right_default_assignment, "Peaking Display Select")
            self.assertEqual(res.effective_custom1_band_ire, (55, 65))
            self.assertEqual(res.effective_custom2_min_ire, 98)

    def test_24_submodel_b_zebra_survives_camera_settings_reset_while_peaking_resets(self) -> None:
        csr = p232.probe_zebra_persistence_and_hdmi_cleanfeed_isolation_hil(
            configured_zebra_display="On",
            configured_zebra_level="Custom 1",
            custom1_std_level=50,
            custom1_range_band=4,
            configured_peaking_display="On",
            configured_peaking_level="High",
            configured_peaking_color="Yellow",
            reset_action_applied="Camera Settings Reset",
        )
        self.assertTrue(csr.admitted)
        self.assertTrue(csr.zebra_survived_camera_settings_reset)
        self.assertFalse(csr.zebra_cleared_by_initialize)
        self.assertEqual(csr.effective_zebra_display, "On")
        self.assertEqual(csr.effective_zebra_level, "Custom 1")
        self.assertEqual(csr.effective_custom1_band_ire, (46, 54))
        # Peaking resets to default Off / Mid / White on Camera Settings Reset
        self.assertEqual(csr.effective_peaking_display, "Off")
        self.assertEqual(csr.effective_peaking_level, "Mid")
        self.assertEqual(csr.effective_peaking_color, "White")

    def test_25_submodel_b_initialize_clears_zebra_back_to_off_and_70(self) -> None:
        init = p232.probe_zebra_persistence_and_hdmi_cleanfeed_isolation_hil(
            configured_zebra_display="On",
            configured_zebra_level="Custom 2",
            custom2_lower_limit=105,
            configured_peaking_display="On",
            configured_peaking_level="Low",
            configured_peaking_color="Blue",
            reset_action_applied="Initialize",
        )
        self.assertTrue(init.admitted)
        self.assertFalse(init.zebra_survived_camera_settings_reset)
        self.assertTrue(init.zebra_cleared_by_initialize)
        self.assertEqual(init.effective_zebra_display, "Off")
        self.assertEqual(init.effective_zebra_level, "70")
        self.assertEqual(init.effective_peaking_display, "Off")
        self.assertEqual(init.local_lcd_assist_overlay_pixels, 0)

    def test_26_submodel_b_hdmi_zero_overlay_pixels_across_all_peaking_levels_colors_even_with_hdmi_info_on(
        self,
    ) -> None:
        for p_lvl in ("High", "Mid", "Low"):
            for p_col in ("Red", "Yellow", "Blue", "White"):
                for hdmi_info in ("On", "Off"):
                    res = p232.probe_zebra_persistence_and_hdmi_cleanfeed_isolation_hil(
                        configured_zebra_display="On",
                        configured_zebra_level="95",
                        configured_peaking_display="On",
                        configured_peaking_level=p_lvl,
                        configured_peaking_color=p_col,
                        hdmi_connected=True,
                        hdmi_info_display=hdmi_info,
                    )
                    self.assertTrue(res.admitted, msg=f"{p_lvl}/{p_col}/{hdmi_info}")
                    self.assertTrue(res.local_lcd_zebra_overlay_active)
                    self.assertTrue(res.local_lcd_peaking_overlay_active)
                    self.assertGreater(res.local_lcd_assist_overlay_pixels, 0)
                    self.assertEqual(res.hdmi_info_telemetry_osd_active, hdmi_info == "On")
                    self.assertFalse(res.hdmi_zebra_overlay_rendered)
                    self.assertFalse(res.hdmi_peaking_overlay_rendered)
                    self.assertEqual(res.hdmi_zebra_overlay_pixels, 0)
                    self.assertEqual(res.hdmi_peaking_overlay_pixels, 0)
                    self.assertEqual(res.hdmi_zebra_or_peaking_leaked_overlay_pixels, 0)

    def test_27_submodel_b_local_lcd_overlay_toggle_combinations(self) -> None:
        z_only = p232.probe_zebra_persistence_and_hdmi_cleanfeed_isolation_hil(
            configured_zebra_display="On",
            configured_peaking_display="Off",
        )
        self.assertTrue(z_only.local_lcd_zebra_overlay_active)
        self.assertFalse(z_only.local_lcd_peaking_overlay_active)
        self.assertEqual(z_only.local_lcd_assist_overlay_pixels, p232.LOCAL_LCD_ZEBRA_SAMPLE_PIXELS)

        p_only = p232.probe_zebra_persistence_and_hdmi_cleanfeed_isolation_hil(
            configured_zebra_display="Off",
            configured_peaking_display="On",
        )
        self.assertFalse(p_only.local_lcd_zebra_overlay_active)
        self.assertTrue(p_only.local_lcd_peaking_overlay_active)
        self.assertEqual(
            p_only.local_lcd_assist_overlay_pixels, p232.LOCAL_LCD_PEAKING_SAMPLE_PIXELS
        )

    def test_28_submodel_b_attempt_force_assist_overlay_on_hdmi_blocked_fail_closed(self) -> None:
        blk = p232.probe_zebra_persistence_and_hdmi_cleanfeed_isolation_hil(
            attempt_force_assist_overlay_on_hdmi=True,
        )
        self.assertFalse(blk.admitted)
        self.assertEqual(blk.errno_code, p232.EOPNOTSUPP_ERRNO)
        self.assertEqual(blk.hdmi_zebra_overlay_pixels, 0)
        self.assertEqual(blk.hdmi_peaking_overlay_pixels, 0)
        self.assertEqual(blk.hdmi_zebra_or_peaking_leaked_overlay_pixels, 0)

    def test_29_submodel_b_zebra_lifecycle_simulator_verified(self) -> None:
        sim = p232.simulate_zebra_reset_vs_initialize_lifecycle(
            configured_zebra_level="Custom 2",
            custom2_lower_limit=102,
        )
        self.assertTrue(sim["lifecycle_verified"])
        self.assertEqual(sim["hdmi_zebra_or_peaking_leaked_overlay_pixels"], 0)
        self.assertEqual(sim["step2_survived_camera_settings_reset"]["effective_zebra_level"], "Custom 2")
        self.assertEqual(sim["step3_cleared_by_initialize"]["effective_zebra_level"], "70")

    def test_30_submodel_b_custom1_and_custom2_boundary_clamping_and_range_validation(self) -> None:
        edge = p232.probe_zebra_persistence_and_hdmi_cleanfeed_isolation_hil(
            configured_zebra_level="Custom 1",
            custom1_std_level=2,
            custom1_range_band=10,
            custom2_lower_limit=109,
        )
        self.assertTrue(edge.admitted)
        self.assertEqual(edge.effective_custom1_band_ire, (0, 12))
        self.assertEqual(edge.effective_custom2_min_ire, 109)

        for bad_kw in (
            {"custom1_std_level": -1},
            {"custom1_std_level": 110},
            {"custom1_range_band": 0},
            {"custom1_range_band": 31},
            {"custom2_lower_limit": -5},
            {"custom2_lower_limit": 115},
        ):
            bad = p232.probe_zebra_persistence_and_hdmi_cleanfeed_isolation_hil(**bad_kw)
            self.assertFalse(bad.admitted, msg=str(bad_kw))
            self.assertEqual(bad.errno_code, p232.EINVAL_ERRNO)

    def test_31_submodel_b_invalid_zebra_peaking_reset_and_hdmi_options_rejected(self) -> None:
        for bad_kw in (
            {"configured_zebra_display": "Auto"},
            {"configured_zebra_level": "65"},
            {"configured_peaking_display": "Blink"},
            {"configured_peaking_level": "Ultra"},
            {"configured_peaking_color": "Green"},
            {"reset_action_applied": "SoftReboot"},
        ):
            bad = p232.probe_zebra_persistence_and_hdmi_cleanfeed_isolation_hil(**bad_kw)
            self.assertFalse(bad.admitted, msg=str(bad_kw))
            self.assertEqual(bad.errno_code, p232.EINVAL_ERRNO)

        with self.assertRaises(p232.RealHwSqFixedVarZebraPeakingFullFormatError):
            p232.probe_zebra_persistence_and_hdmi_cleanfeed_isolation_hil(hdmi_info_display="Maybe")

    def test_32_pillar_b_evaluator_matrix_passes_100pct(self) -> None:
        pb = p232.evaluate_pillar_b_zebra_persistence_and_hdmi_isolation_hil()
        self.assertTrue(pb["passed"])
        self.assertEqual(
            pb["zebra_and_peaking_on_with_hdmi_info_on_0px"]["hdmi_zebra_overlay_pixels"], 0
        )

    # ------------------------------------------------------------------
    # Group 4: Sub-model C & Redlines — Quick/Full Format & MENU+Delete 2s Vault Firewall (17)
    # ------------------------------------------------------------------
    def test_33_submodel_c_slot1_unverified_tier0_vault_blocks_quick_format_across_all_payloads(
        self,
    ) -> None:
        for vault in ("pnflasha", "cnflasha", "CAMSET01.DAT", "pnflasha+cnflasha+CAMSET01.DAT"):
            blk = p232.probe_slot_format_and_menu_delete_chord_vault_firewall_hil(
                entry_path=p232.ENTRY_VIA_MENU_FORMAT,
                target_slot="Slot 1",
                slot1_tier0_vault_payload=vault,
                off_camera_sha256_verified=False,
                sdxc_wp_switch_locked=False,
                delete_key_toggle_presses=0,
            )
            self.assertFalse(blk.admitted, msg=vault)
            self.assertTrue(blk.tier0_vault_firewall_engaged)
            self.assertFalse(blk.format_executed)
            self.assertEqual(blk.errno_code, p232.EBUSY_ERRNO)
            self.assertEqual(blk.tier0_slot1_format_or_chord_wipe_events, 0)

    def test_34_submodel_c_slot1_tier0_vault_blocks_delete_toggled_full_format(self) -> None:
        blk = p232.probe_slot_format_and_menu_delete_chord_vault_firewall_hil(
            entry_path=p232.ENTRY_VIA_MENU_FORMAT,
            target_slot="Slot 1",
            slot1_tier0_vault_payload="pnflasha+cnflasha+CAMSET01.DAT",
            off_camera_sha256_verified=False,
            sdxc_wp_switch_locked=False,
            delete_key_toggle_presses=1,
        )
        self.assertFalse(blk.admitted)
        self.assertEqual(blk.selected_format_mode, "Full Format")
        self.assertTrue(blk.tier0_vault_firewall_engaged)
        self.assertFalse(blk.all_data_blocks_initialized)
        self.assertEqual(blk.errno_code, p232.EBUSY_ERRNO)

    def test_35_submodel_c_slot1_tier0_vault_blocks_menu_plus_delete_2s_shooting_chord(self) -> None:
        for hold_s in (2.0, 2.5, 4.0):
            blk = p232.probe_slot_format_and_menu_delete_chord_vault_firewall_hil(
                entry_path=p232.ENTRY_VIA_MENU_DELETE_CHORD,
                ui_screen="Shooting",
                chord_hold_sec=hold_s,
                target_slot="Slot 1",
                slot1_tier0_vault_payload="pnflasha",
                off_camera_sha256_verified=False,
                sdxc_wp_switch_locked=False,
            )
            self.assertFalse(blk.admitted, msg=str(hold_s))
            self.assertTrue(blk.chord_threshold_reached)
            self.assertTrue(blk.tier0_vault_firewall_engaged)
            self.assertFalse(blk.format_dialog_opened)
            self.assertEqual(blk.errno_code, p232.EBUSY_ERRNO)

    def test_36_submodel_c_slot1_sdxc_wp_switch_locked_returns_erofs_30(self) -> None:
        erofs = p232.probe_slot_format_and_menu_delete_chord_vault_firewall_hil(
            entry_path=p232.ENTRY_VIA_MENU_FORMAT,
            target_slot="Slot 1",
            slot1_tier0_vault_payload="cnflasha",
            off_camera_sha256_verified=True,
            sdxc_wp_switch_locked=True,
        )
        self.assertFalse(erofs.admitted)
        self.assertTrue(erofs.tier0_vault_firewall_engaged)
        self.assertEqual(erofs.errno_code, p232.EROFS_ERRNO)

    def test_37_submodel_c_slot1_verified_vault_still_in_slot_without_card_swap_remains_blocked(
        self,
    ) -> None:
        blk = p232.probe_slot_format_and_menu_delete_chord_vault_firewall_hil(
            entry_path=p232.ENTRY_VIA_MENU_FORMAT,
            target_slot="Slot 1",
            slot1_tier0_vault_payload="CAMSET01.DAT",
            off_camera_sha256_verified=True,
            sdxc_wp_switch_locked=False,
            vault_card_swapped_for_scratch_media=False,
        )
        self.assertFalse(blk.admitted)
        self.assertTrue(blk.slot1_tier0_vault_present)
        self.assertTrue(blk.tier0_vault_firewall_engaged)
        self.assertEqual(blk.errno_code, p232.EBUSY_ERRNO)

    def test_38_submodel_c_unverified_vault_cannot_bypass_firewall_by_claiming_card_swap(
        self,
    ) -> None:
        blk = p232.probe_slot_format_and_menu_delete_chord_vault_firewall_hil(
            target_slot="Slot 1",
            slot1_tier0_vault_payload="pnflasha",
            off_camera_sha256_verified=False,
            sdxc_wp_switch_locked=False,
            vault_card_swapped_for_scratch_media=True,
        )
        self.assertFalse(blk.admitted)
        self.assertTrue(blk.tier0_vault_firewall_engaged)
        self.assertEqual(blk.errno_code, p232.EBUSY_ERRNO)

    def test_39_submodel_c_verified_and_swapped_scratch_card_admits_quick_and_full_format(
        self,
    ) -> None:
        quick = p232.probe_slot_format_and_menu_delete_chord_vault_firewall_hil(
            target_slot="Slot 1",
            slot1_tier0_vault_payload="pnflasha+cnflasha+CAMSET01.DAT",
            off_camera_sha256_verified=True,
            sdxc_wp_switch_locked=False,
            vault_card_swapped_for_scratch_media=True,
            delete_key_toggle_presses=0,
        )
        self.assertTrue(quick.admitted)
        self.assertEqual(quick.selected_format_mode, "Quick Format")
        self.assertTrue(quick.format_executed)
        self.assertTrue(quick.metadata_reinitialized)
        self.assertFalse(quick.all_data_blocks_initialized)
        self.assertFalse(quick.persistent_emmc_writes_authorized)

        full = p232.probe_slot_format_and_menu_delete_chord_vault_firewall_hil(
            entry_path=p232.ENTRY_VIA_MENU_DELETE_CHORD,
            ui_screen="Shooting",
            chord_hold_sec=2.0,
            target_slot="Slot 1",
            slot1_tier0_vault_payload="pnflasha+cnflasha+CAMSET01.DAT",
            off_camera_sha256_verified=True,
            sdxc_wp_switch_locked=False,
            vault_card_swapped_for_scratch_media=True,
            delete_key_toggle_presses=1,
        )
        self.assertTrue(full.admitted)
        self.assertEqual(full.selected_format_mode, "Full Format")
        self.assertTrue(full.format_executed)
        self.assertTrue(full.metadata_reinitialized)
        self.assertTrue(full.all_data_blocks_initialized)
        self.assertTrue(full.card_write_speed_restored)
        self.assertFalse(full.persistent_emmc_writes_authorized)

    def test_40_submodel_c_delete_key_toggle_parity_between_quick_and_full_format(self) -> None:
        for presses, expected_mode in ((0, "Quick Format"), (1, "Full Format"), (2, "Quick Format"), (3, "Full Format")):
            res = p232.probe_slot_format_and_menu_delete_chord_vault_firewall_hil(
                target_slot="Slot 2",
                delete_key_toggle_presses=presses,
            )
            self.assertTrue(res.admitted)
            self.assertEqual(res.selected_format_mode, expected_mode)
            self.assertEqual(res.all_data_blocks_initialized, expected_mode == "Full Format")

    def test_41_submodel_c_full_format_mid_cancel_leaves_data_erased_and_card_usable(self) -> None:
        for pct in (1, 35, 99):
            mc = p232.probe_slot_format_and_menu_delete_chord_vault_firewall_hil(
                target_slot="Slot 2",
                delete_key_toggle_presses=1,
                dialog_confirm_key="Enter",
                cancel_mid_full_format=True,
                cancel_progress_pct=pct,
            )
            self.assertTrue(mc.admitted, msg=str(pct))
            self.assertEqual(mc.selected_format_mode, "Full Format")
            self.assertTrue(mc.format_executed)
            self.assertTrue(mc.metadata_reinitialized)
            self.assertFalse(mc.all_data_blocks_initialized)
            self.assertFalse(mc.card_write_speed_restored)
            self.assertTrue(mc.prior_data_permanently_erased)
            self.assertTrue(mc.card_formatted_and_immediately_usable)

    def test_42_submodel_c_dialog_cancel_before_enter_preserves_data_intact(self) -> None:
        canceled = p232.probe_slot_format_and_menu_delete_chord_vault_firewall_hil(
            target_slot="Slot 2",
            delete_key_toggle_presses=1,
            dialog_confirm_key="Cancel",
        )
        self.assertTrue(canceled.admitted)
        self.assertTrue(canceled.format_dialog_opened)
        self.assertFalse(canceled.format_executed)
        self.assertFalse(canceled.prior_data_permanently_erased)
        self.assertTrue(canceled.card_formatted_and_immediately_usable)

    def test_43_submodel_c_menu_delete_chord_under_2s_and_non_shooting_screens(self) -> None:
        for short_s in (0.0, 0.5, 1.5, 1.99):
            short_res = p232.probe_slot_format_and_menu_delete_chord_vault_firewall_hil(
                entry_path=p232.ENTRY_VIA_MENU_DELETE_CHORD,
                ui_screen="Shooting",
                chord_hold_sec=short_s,
                target_slot="Slot 1",
                slot1_tier0_vault_payload="pnflasha",
            )
            self.assertTrue(short_res.admitted, msg=str(short_s))
            self.assertFalse(short_res.chord_threshold_reached)
            self.assertFalse(short_res.format_dialog_opened)
            self.assertFalse(short_res.format_executed)

        for screen in ("Playback", "Menu"):
            bad_scr = p232.probe_slot_format_and_menu_delete_chord_vault_firewall_hil(
                entry_path=p232.ENTRY_VIA_MENU_DELETE_CHORD,
                ui_screen=screen,
                chord_hold_sec=2.5,
                target_slot="Slot 2",
            )
            self.assertFalse(bad_scr.admitted, msg=screen)
            self.assertEqual(bad_scr.errno_code, p232.EOPNOTSUPP_ERRNO)

    def test_44_submodel_c_invalid_mid_cancel_and_bad_parameters_rejected(self) -> None:
        # Mid-cancel on Quick Format rejected
        mc_quick = p232.probe_slot_format_and_menu_delete_chord_vault_firewall_hil(
            target_slot="Slot 2",
            delete_key_toggle_presses=0,
            cancel_mid_full_format=True,
            cancel_progress_pct=50,
        )
        self.assertFalse(mc_quick.admitted)
        self.assertEqual(mc_quick.errno_code, p232.EINVAL_ERRNO)

        # Mid-cancel at 0% or 100% rejected
        for bad_pct in (0, 100):
            mc_pct = p232.probe_slot_format_and_menu_delete_chord_vault_firewall_hil(
                target_slot="Slot 2",
                delete_key_toggle_presses=1,
                cancel_mid_full_format=True,
                cancel_progress_pct=bad_pct,
            )
            self.assertFalse(mc_pct.admitted)
            self.assertEqual(mc_pct.errno_code, p232.EINVAL_ERRNO)

        for bad_kw in (
            {"entry_path": "USB_HOST_WIPE"},
            {"ui_screen": "Bootloader"},
            {"target_slot": "Slot 3"},
            {"slot1_tier0_vault_payload": "unknown.bin"},
            {"dialog_confirm_key": "Trash"},
        ):
            bad = p232.probe_slot_format_and_menu_delete_chord_vault_firewall_hil(**bad_kw)
            self.assertFalse(bad.admitted, msg=str(bad_kw))
            self.assertEqual(bad.errno_code, p232.EINVAL_ERRNO)

        with self.assertRaises(p232.RealHwSqFixedVarZebraPeakingFullFormatError):
            p232.probe_slot_format_and_menu_delete_chord_vault_firewall_hil(
                delete_key_toggle_presses=-1
            )
        with self.assertRaises(p232.RealHwSqFixedVarZebraPeakingFullFormatError):
            p232.probe_slot_format_and_menu_delete_chord_vault_firewall_hil(chord_hold_sec=-0.1)
        with self.assertRaises(p232.RealHwSqFixedVarZebraPeakingFullFormatError):
            p232.probe_slot_format_and_menu_delete_chord_vault_firewall_hil(cancel_progress_pct=120)

    def test_45_hard_safety_redline_baseline_and_all_9_forbidden_actions(self) -> None:
        base = p232.probe_hard_safety_redline()
        self.assertTrue(base.valid)
        self.assertFalse(base.persistent_emmc_writes_authorized)
        self.assertFalse(base.hardware_live_attachment_authorized)
        self.assertFalse(base.overall_ready_for_hardware_attach)
        self.assertFalse(base.spi_nor_write_authorized)
        self.assertFalse(base.el3_payload_transmit_authorized)
        self.assertFalse(base.isp_write_authorized)
        self.assertTrue(base.cnflasha_userspace_write_blocked)
        self.assertEqual(base.physical_usb_packets_emitted, 0)
        self.assertEqual(base.otp_fuse_touches, 0)
        self.assertEqual(base.rpmb_counter_increments, 0)

        for flag_name in (
            "authorize_persistent_emmc_writes",
            "authorize_hardware_live_attachment",
            "authorize_spi_nor_write",
            "authorize_el3_payload_transmit",
            "authorize_isp_write",
            "emit_physical_usb_packet",
            "touch_otp_fuse",
            "increment_rpmb_counter",
            "bypass_sq_6locks_or_hdmi_isolation_or_tier0_format_firewall",
        ):
            bad = p232.probe_hard_safety_redline(**{flag_name: True})
            self.assertFalse(bad.valid, msg=flag_name)
            self.assertFalse(bad.persistent_emmc_writes_authorized)
            self.assertFalse(bad.hardware_live_attachment_authorized)
            self.assertFalse(bad.overall_ready_for_hardware_attach)
            self.assertFalse(bad.spi_nor_write_authorized)
            self.assertFalse(bad.el3_payload_transmit_authorized)
            self.assertFalse(bad.isp_write_authorized)
            self.assertTrue(bad.status_code.startswith("FAIL_CLOSED_REDLINE_BLOCKED:"))

    def test_46_combined_multi_redline_violation_blocked(self) -> None:
        combo = p232.probe_hard_safety_redline(
            authorize_persistent_emmc_writes=True,
            authorize_hardware_live_attachment=True,
            authorize_isp_write=True,
            bypass_sq_6locks_or_hdmi_isolation_or_tier0_format_firewall=True,
        )
        self.assertFalse(combo.valid)
        self.assertIn("PERSISTENT_EMMC_WRITE", combo.blocked_action)
        self.assertIn("HARDWARE_LIVE_ATTACHMENT", combo.blocked_action)
        self.assertIn("ISP_WRITE", combo.blocked_action)

    def test_47_pillar_c_d_evaluator_matrix_passes_100pct(self) -> None:
        pcd = p232.evaluate_pillar_c_d_fullformat_chord_vault_firewall_and_redlines()
        self.assertTrue(pcd["passed"])
        self.assertEqual(len(pcd["slot1_vault_quick_format_blocked_by_payload"]), 3)
        self.assertEqual(len(pcd["blocked_redline_probes"]), 9)

    # ------------------------------------------------------------------
    # Group 5: End-to-End Orchestrator, CLI, Suite >=42 & Hygiene (9)
    # ------------------------------------------------------------------
    def test_48_clean_room_audit_deterministic_digest_and_zero_leaks(self) -> None:
        r1 = _get_clean_room_audit()
        r2 = p232.run_phase232_realhw_sq_fixedvar_zebra_peaking_fullformat_hil(
            force_clean_room=True
        )
        self.assertTrue(r1["all_checks_passed"])
        self.assertEqual(r1["schema"], p232.SCHEMA_ID)
        self.assertEqual(r1["source_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(r1["stage_index"], 42)
        self.assertEqual(r1["stage_total"], 42)
        self.assertEqual(r1["milestone"], "42/42")
        self.assertEqual(r1["audit_digest_sha256"], r2["audit_digest_sha256"])
        self.assertEqual(r1["redlines"]["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(r1["donor_audit"]["raw_firmware_bytes_leaked"], 0)

    def test_49_default_mode_audit_passes_all_pillars_and_redlines(self) -> None:
        rep = _get_default_audit()
        self.assertTrue(rep["all_checks_passed"])
        self.assertIn(rep["source_mode"], ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"))
        self.assertTrue(rep["pillar_a_sq_fixedvar_and_6locks_hil"]["passed"])
        self.assertTrue(rep["pillar_b_zebra_persistence_and_hdmi_isolation_hil"]["passed"])
        self.assertTrue(rep["pillar_c_d_fullformat_chord_vault_firewall_and_redlines"]["passed"])
        self.assertFalse(rep["redlines"]["persistent_emmc_writes_authorized"])
        self.assertFalse(rep["redlines"]["hardware_live_attachment_authorized"])
        self.assertFalse(rep["redlines"]["overall_ready_for_hardware_attach"])
        self.assertFalse(rep["redlines"]["isp_write_authorized"])

    def test_50_standalone_cli_self_test_summary_and_clean_room_json(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        script_path = str(
            FX3_VM_DIR / "realhw_sq_fixedvar_zebra_peaking_fullformat_coemulator.py"
        )
        p_sum = subprocess.run(
            [sys.executable, "-B", script_path, "--self-test", "--summary"],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(p_sum.returncode, 0, msg=p_sum.stderr)
        self.assertIn("[PASS] Phase 232 Stage 42 (42/42)", p_sum.stdout)

        p_json = subprocess.run(
            [sys.executable, "-B", script_path, "--self-test", "--clean-room", "--json"],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(p_json.returncode, 0, msg=p_json.stderr)
        parsed = json.loads(p_json.stdout)
        self.assertTrue(parsed["all_checks_passed"])
        self.assertEqual(parsed["schema"], p232.SCHEMA_ID)
        self.assertEqual(parsed["stage_index"], 42)
        self.assertEqual(parsed["milestone"], "42/42")

    def test_51_inprocess_main_summary_and_json_exit_zero(self) -> None:
        buf_sum = io.StringIO()
        with contextlib.redirect_stdout(buf_sum):
            rc_sum = p232.main(["--self-test", "--clean-room", "--summary"])
        self.assertEqual(rc_sum, 0)
        self.assertIn("[PASS] Phase 232 Stage 42 (42/42)", buf_sum.getvalue())

        buf_json = io.StringIO()
        with contextlib.redirect_stdout(buf_json):
            rc_json = p232.main(["--self-test", "--clean-room", "--json"])
        self.assertEqual(rc_json, 0)
        data = json.loads(buf_json.getvalue())
        self.assertEqual(data["source_mode"], "CLEAN_ROOM_SYNTHETIC")

    def test_52_fx3_vm_coemulation_suite_includes_stage42_and_forward_compat_count(self) -> None:
        rep_on, dt_clean = _get_clean_room_suite()
        self.assertTrue(rep_on["all_checks_passed"])
        self.assertLess(dt_clean, 4.0)
        self.assertIn(
            "stage42_realhw_sq_fixedvar_zebra_peaking_fullformat_hil",
            rep_on,
        )
        s42 = rep_on["stage42_realhw_sq_fixedvar_zebra_peaking_fullformat_hil"]
        self.assertTrue(s42["all_checks_passed"])
        self.assertEqual(s42["schema"], p232.SCHEMA_ID)
        self.assertEqual(s42["milestone"], "42/42")
        self.assertFalse(s42["persistent_emmc_writes_authorized"])
        self.assertFalse(s42["hardware_live_attachment_authorized"])
        self.assertFalse(s42["overall_ready_for_hardware_attach"])
        self.assertFalse(s42["isp_write_authorized"])
        self.assertFalse(s42["spi_nor_write_authorized"])
        self.assertFalse(s42["el3_payload_transmit_authorized"])
        self.assertEqual(s42["sq_fixedvar_6lock_bypass_events"], 0)
        self.assertEqual(s42["hdmi_zebra_or_peaking_leaked_overlay_pixels"], 0)
        self.assertEqual(s42["tier0_slot1_format_or_chord_wipe_events"], 0)
        self.assertEqual(s42["raw_firmware_bytes_leaked"], 0)

        stage_keys = [k for k in rep_on if re.match(r"^stage\d+_", k)]
        self.assertGreaterEqual(len(stage_keys), 42)

    def test_53_fx3_vm_coemulation_suite_skip_phase232_option(self) -> None:
        rep_skip = suite.run_fx3_vm_coemulation_suite(
            suite.CoEmulationConfig(
                force_clean_room=True,
                include_phase232_realhw_sq_fixedvar_zebra_peaking_fullformat_hil=False,
            )
        )
        self.assertTrue(rep_skip["all_checks_passed"])
        self.assertNotIn(
            "stage42_realhw_sq_fixedvar_zebra_peaking_fullformat_hil",
            rep_skip,
        )

    def test_54_fx3_vm_coemulation_suite_default_mode_and_cli_summary_stage42(self) -> None:
        rep_def, dt_def = _get_default_suite()
        self.assertTrue(rep_def["all_checks_passed"])
        self.assertLess(dt_def, 8.0)
        s42 = rep_def["stage42_realhw_sq_fixedvar_zebra_peaking_fullformat_hil"]
        self.assertTrue(s42["all_checks_passed"])
        stage_keys = [k for k in rep_def if re.match(r"^stage\d+_", k)]
        self.assertGreaterEqual(len(stage_keys), 42)

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = suite.main(["--clean-room", "--summary"])
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("[PASS] Phase 33 FX3-VM Co-Emulation", out)
        self.assertIn(
            "realhw_sq_fixedvar_zebra_peaking_fullformat_hil=CLEAN_ROOM_SYNTHETIC("
            "sq_locks=6,zebra_csr=1,hdmi_px=0,chord_blk=1,emmc_wr=0)",
            out,
        )

    def test_55_fx3_vm_coemulation_suite_cli_skip_phase232_flag(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = suite.main(["--clean-room", "--skip-phase232", "--summary"])
        self.assertEqual(rc, 0)
        self.assertNotIn(
            "realhw_sq_fixedvar_zebra_peaking_fullformat_hil=",
            buf.getvalue(),
        )

    def test_56_source_hygiene_no_write_flags_no_port_8768_and_readme_documented(self) -> None:
        src = (
            FX3_VM_DIR / "realhw_sq_fixedvar_zebra_peaking_fullformat_coemulator.py"
        ).read_text(encoding="utf-8")
        forbidden_wronly = "O_" + "WRONLY"
        forbidden_rdwr = "O_" + "RDWR"
        forbidden_port = "87" + "68"
        self.assertNotIn(forbidden_wronly, src)
        self.assertNotIn(forbidden_rdwr, src)
        self.assertNotIn(forbidden_port, src)
        self.assertIn("os.O_RDONLY", src)

        readme = (FX3_VM_DIR / "README.md").read_text(encoding="utf-8")
        self.assertIn(
            "realhw_sq_fixedvar_zebra_peaking_fullformat_coemulator.py",
            readme,
        )
        self.assertIn("42/42", readme)
        self.assertIn("--skip-phase232", readme)

    def test_57_slot2_media_formatting_independent_while_slot1_holds_tier0_vault(self) -> None:
        s2_quick = p232.probe_slot_format_and_menu_delete_chord_vault_firewall_hil(
            entry_path=p232.ENTRY_VIA_MENU_FORMAT,
            target_slot="Slot 2",
            slot1_tier0_vault_payload="pnflasha+cnflasha+CAMSET01.DAT",
            off_camera_sha256_verified=False,
            sdxc_wp_switch_locked=True,
            delete_key_toggle_presses=0,
        )
        self.assertTrue(s2_quick.admitted)
        self.assertFalse(s2_quick.tier0_vault_firewall_engaged)
        self.assertTrue(s2_quick.format_executed)
        self.assertEqual(s2_quick.selected_format_mode, "Quick Format")

        s2_full = p232.probe_slot_format_and_menu_delete_chord_vault_firewall_hil(
            entry_path=p232.ENTRY_VIA_MENU_DELETE_CHORD,
            ui_screen="Shooting",
            chord_hold_sec=2.3,
            target_slot="Slot 2",
            slot1_tier0_vault_payload="pnflasha+cnflasha+CAMSET01.DAT",
            off_camera_sha256_verified=False,
            sdxc_wp_switch_locked=True,
            delete_key_toggle_presses=1,
        )
        self.assertTrue(s2_full.admitted)
        self.assertFalse(s2_full.tier0_vault_firewall_engaged)
        self.assertTrue(s2_full.all_data_blocks_initialized)
        self.assertEqual(s2_full.selected_format_mode, "Full Format")

    def test_58_complete_ntsc_and_pal_hd_sq_fps_sweep_admitted_with_zero_bypass(self) -> None:
        for fps_n in p232.NTSC_SQ_SHOOTING_FPS:
            res_n = p232.probe_sq_mode_settings_fixedvar_and_6locks_hil(
                tv_region="NTSC",
                file_format="XAVC S-I HD",
                rec_frame_rate="29.97p",
                shooting_fps=fps_n,
                proxy_recording_requested="Off",
            )
            self.assertTrue(res_n.admitted, msg=f"NTSC {fps_n}")
            self.assertEqual(res_n.audio_channels_recorded, 0)
            self.assertEqual(res_n.sq_fixedvar_6lock_bypass_events, 0)

        for fps_p in p232.PAL_SQ_SHOOTING_FPS:
            res_p = p232.probe_sq_mode_settings_fixedvar_and_6locks_hil(
                tv_region="PAL",
                file_format="XAVC S-I HD",
                rec_frame_rate="25p",
                shooting_fps=fps_p,
                proxy_recording_requested="Off",
            )
            self.assertTrue(res_p.admitted, msg=f"PAL {fps_p}")
            self.assertEqual(res_p.audio_channels_recorded, 0)
            self.assertEqual(res_p.sq_fixedvar_6lock_bypass_events, 0)


if __name__ == "__main__":
    unittest.main()
