"""Phase 228 Dual-Mode Unit Tests (62 tests, >=56 required):
Gates G83 (`G83_SQ_FIXED_VARIABLE_6LOCK_MATRIX_AND_ZEBRA_PEAKING_HDMI_CLEANFEED_GUARD`),
G84 (`G84_ZEBRA_CAMERA_SETTINGS_RESET_SURVIVAL_AND_FULL_FORMAT_CHORD_VAULT_GUARD`),
and Unified 84-Gate Master Safety Preflight (`verify-84-gates`).
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
from fx3_safety.realhw_sq_fixedvar_zebra_peaking_fullformat_and_84gate_guard import (
    ALLOWED_AUDIO_OUT_TIMING_MODES,
    ALLOWED_FORMAT_MODES,
    ALLOWED_FORMAT_TARGET_SLOTS,
    ALLOWED_FORMAT_TRIGGERS,
    ALLOWED_MOVIE_FILE_FORMATS_G83,
    ALLOWED_PEAKING_COLORS,
    ALLOWED_PEAKING_DISPLAY_MODES,
    ALLOWED_PEAKING_LEVELS,
    ALLOWED_RESET_ACTIONS_G84,
    ALLOWED_SHOOT_MODES_G83,
    ALLOWED_SQ_MODE_SETTINGS,
    ALLOWED_ZEBRA_CUSTOM_MODES,
    ALLOWED_ZEBRA_DISPLAY_MODES,
    ALLOWED_ZEBRA_LEVELS,
    ALLOWED_ZEBRA_PRESET_LEVELS,
    AUDIO_OUT_TIMING_FACTORY_DEFAULT,
    AUDIO_OUT_TIMING_LIP_SYNC,
    AUDIO_OUT_TIMING_LIVE,
    CONTROL_WHEEL_LEFT_DEFAULT_ZEBRA_SELECT,
    CONTROL_WHEEL_RIGHT_DEFAULT_PEAKING_SELECT,
    DONOR_CHECK_MAX_SECONDS,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    FILE_FORMAT_XAVC_HS_4K,
    FILE_FORMAT_XAVC_S_4K,
    FILE_FORMAT_XAVC_S_HD,
    FILE_FORMAT_XAVC_SI_4K,
    FILE_FORMAT_XAVC_SI_DCI_4K,
    FILE_FORMAT_XAVC_SI_HD,
    FORMAT_MODE_FULL,
    FORMAT_MODE_NONE,
    FORMAT_MODE_QUICK,
    FORMAT_SLOT_1,
    FORMAT_SLOT_2,
    FORMAT_SLOT_NONE,
    FORMAT_TRIGGER_CONFIRM_DELETE_TOGGLE,
    FORMAT_TRIGGER_MENU_DELETE_2S_CHORD,
    FORMAT_TRIGGER_MENU_ENTER,
    FORMAT_TRIGGER_NONE,
    FX3_DEFAULT_FW_VERSION_G83,
    FX3_SQ_FIXEDVAR_MIN_FW_TUPLE,
    G83,
    G83_GATE_CODE,
    G83_GATE_ID,
    G84,
    G84_GATE_CODE,
    G84_GATE_ID,
    HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    MENU_DELETE_CHORD_MIN_HOLD_SECONDS,
    MODE_SETTINGS_FIXED_VARIABLE,
    MODE_SETTINGS_VARIABLE,
    NTSC_SQ_ALLOWED_REC_RATES,
    NTSC_SQ_MAX_CAPTURE_FPS,
    PAL_SQ_ALLOWED_REC_RATES,
    PAL_SQ_MAX_CAPTURE_FPS,
    PEAKING_COLOR_BLUE,
    PEAKING_COLOR_RED,
    PEAKING_COLOR_WHITE,
    PEAKING_COLOR_YELLOW,
    PEAKING_DISPLAY_OFF,
    PEAKING_DISPLAY_ON,
    PEAKING_FACTORY_DEFAULT_COLOR,
    PEAKING_FACTORY_DEFAULT_DISPLAY,
    PEAKING_FACTORY_DEFAULT_LEVEL,
    PEAKING_LEVEL_HIGH,
    PEAKING_LEVEL_LOW,
    PEAKING_LEVEL_MID,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PINNED_PHASE228_DONOR_SPECS,
    RAW_FIRMWARE_BYTES_LEAKED,
    REALHW_SQ_FIXEDVAR_ZEBRA_PEAKING_FULLFORMAT_84GATE_SCHEMA,
    RESET_ACTION_CAMERA_SETTINGS_RESET,
    RESET_ACTION_INITIALIZE,
    RESET_ACTION_NONE,
    SHOOT_MODE_MOVIE,
    SHOOT_MODE_SQ,
    SHOOT_MODE_STILL,
    SPI_NOR_WRITE_AUTHORIZED,
    SQ_120_100FPS_BLOCKED_DCI4K_FORMATS,
    SQ_240_200FPS_BLOCKED_4K_FORMATS,
    SQ_6_DISQUALIFICATIONS,
    SQ_PROXY_BLOCKED_CAPTURE_FPS_FLOOR,
    SQ_PROXY_BLOCKED_REC_RATES,
    STATUS_BLOCKED_G83_HDMI_ZEBRA_OR_PEAKING_ASSIST_OVERLAY_LEAK,
    STATUS_BLOCKED_G83_MODE_SETTINGS_FIXED_VARIABLE_OR_SQ_SETTINGS_LOCK_VIOLATION,
    STATUS_BLOCKED_G83_SQ_6LOCK_AUDIO_TC_CODEC_OR_PROXY_VIOLATION,
    STATUS_BLOCKED_G83_TELEMETRY_INVALID,
    STATUS_BLOCKED_G84_FULL_FORMAT_CANCEL_SEMANTICS_MISMATCH,
    STATUS_BLOCKED_G84_SLOT1_TIER0_VAULT_FORMAT_OR_CHORD_LOCKOUT,
    STATUS_BLOCKED_G84_TELEMETRY_INVALID,
    STATUS_BLOCKED_G84_ZEBRA_CAMERA_SETTINGS_RESET_PERSISTENCE_VIOLATION,
    STATUS_BLOCKED_G84_ZEBRA_LEVEL_OR_CUSTOM_THRESHOLD_INVALID,
    STATUS_BLOCKED_PERSISTENT_EMMC_WRITE,
    STATUS_BLOCKED_PHASE228_DONOR_INTEGRITY,
    STATUS_VERIFIED_G83,
    STATUS_VERIFIED_G84,
    TIER0_VAULT_REQUIRED_ARTIFACTS,
    USB_PACKETS_TRANSMITTED,
    VIDEO_SYSTEM_NTSC,
    VIDEO_SYSTEM_PAL,
    ZEBRA_CUSTOM1_RANGE_MAX,
    ZEBRA_CUSTOM1_RANGE_MIN,
    ZEBRA_CUSTOM_IRE_MAX,
    ZEBRA_CUSTOM_IRE_MIN,
    ZEBRA_DISPLAY_OFF,
    ZEBRA_DISPLAY_ON,
    ZEBRA_FACTORY_DEFAULT_DISPLAY,
    ZEBRA_FACTORY_DEFAULT_LEVEL,
    ZEBRA_LEVEL_CUSTOM_1,
    ZEBRA_LEVEL_CUSTOM_2,
    audit_phase228_donor_contracts,
    evaluate_84_master_safety_gates,
    evaluate_84gate_preflight,
    evaluate_g83_sq_fixedvar_zebra_peaking_hdmi_guard,
    evaluate_g84_zebra_reset_and_fullformat_chord_vault_guard,
    main as module_main,
    resolve_fx3_mode_settings_and_sq_6locks,
    resolve_fx3_slot1_format_and_chord_vault_lock,
    resolve_fx3_zebra_peaking_hdmi_cleanfeed,
    resolve_fx3_zebra_reset_survival,
    run_84_gate_preflight,
    verify_sq_fixedvar_6lock_and_zebra_peaking_hdmi_guard,
    verify_zebra_reset_survival_and_fullformat_chord_vault_guard,
)


class TestPhase228SqFixedVarZebraPeakingFullFormat84GateGuard(unittest.TestCase):
    """Comprehensive dual-mode tests for Phase 228 Gates G83, G84 & 84-Gate Preflight."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.offline_82 = fx3_safety.evaluate_82gate_preflight()
        cls.dryrun_82 = fx3_safety.evaluate_82gate_preflight(dry_run_simulated=True)
        cls.offline_84 = evaluate_84gate_preflight(master_82_override=cls.offline_82)
        cls.dryrun_84 = evaluate_84gate_preflight(
            simulate_bench_dry_run=True, master_82_override=cls.dryrun_82
        )
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            cls.clean_offline_82 = fx3_safety.evaluate_82gate_preflight(
                force_clean_room=True
            )
            cls.clean_dryrun_82 = fx3_safety.evaluate_82gate_preflight(
                force_clean_room=True, dry_run_simulated=True
            )
            cls.clean_offline_84 = evaluate_84gate_preflight(
                force_clean_room=True, master_82_override=cls.clean_offline_82
            )
            cls.clean_dryrun_84 = evaluate_84gate_preflight(
                force_clean_room=True,
                simulate_bench_dry_run=True,
                master_82_override=cls.clean_dryrun_82,
            )

    # ------------------------------------------------------------------
    # Section A: Package Exports & Bounded Donor Contract Audit (8 tests)
    # ------------------------------------------------------------------

    def test_01_public_package_exports_and_hard_redline_constants(self) -> None:
        self.assertEqual(G83, G83_GATE_CODE)
        self.assertEqual(G84, G84_GATE_CODE)
        self.assertEqual(
            G83_GATE_CODE,
            "G83_SQ_FIXED_VARIABLE_6LOCK_MATRIX_AND_ZEBRA_PEAKING_HDMI_CLEANFEED_GUARD",
        )
        self.assertEqual(
            G84_GATE_CODE,
            "G84_ZEBRA_CAMERA_SETTINGS_RESET_SURVIVAL_AND_FULL_FORMAT_CHORD_VAULT_GUARD",
        )
        self.assertFalse(EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        self.assertFalse(SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        self.assertEqual(USB_PACKETS_TRANSMITTED, 0)
        self.assertEqual(RAW_FIRMWARE_BYTES_LEAKED, 0)
        self.assertIs(fx3_safety.evaluate_84gate_preflight, evaluate_84gate_preflight)
        self.assertIs(fx3_safety.run_84_gate_preflight, run_84_gate_preflight)
        self.assertIs(
            fx3_safety.evaluate_84_master_safety_gates, evaluate_84_master_safety_gates
        )
        self.assertIn("evaluate_84gate_preflight", fx3_safety.__all__)
        self.assertIn(
            "realhw_sq_fixedvar_zebra_peaking_fullformat_and_84gate_guard",
            fx3_safety.__all__,
        )

    def test_02_wave32_spec_constants_and_enums(self) -> None:
        self.assertEqual(FX3_DEFAULT_FW_VERSION_G83, "7.02")
        self.assertEqual(FX3_SQ_FIXEDVAR_MIN_FW_TUPLE, (7, 0))
        self.assertEqual(
            ALLOWED_SQ_MODE_SETTINGS, (MODE_SETTINGS_FIXED_VARIABLE, MODE_SETTINGS_VARIABLE)
        )
        self.assertEqual(len(SQ_6_DISQUALIFICATIONS), 6)
        self.assertEqual(len(SQ_240_200FPS_BLOCKED_4K_FORMATS), 4)
        self.assertEqual(SQ_120_100FPS_BLOCKED_DCI4K_FORMATS, (FILE_FORMAT_XAVC_SI_DCI_4K,))
        self.assertEqual(SQ_PROXY_BLOCKED_REC_RATES, ("119.88p", "100p"))
        self.assertEqual(SQ_PROXY_BLOCKED_CAPTURE_FPS_FLOOR, 100.0)
        self.assertEqual(AUDIO_OUT_TIMING_FACTORY_DEFAULT, AUDIO_OUT_TIMING_LIVE)
        self.assertEqual(
            ALLOWED_AUDIO_OUT_TIMING_MODES,
            (AUDIO_OUT_TIMING_LIVE, AUDIO_OUT_TIMING_LIP_SYNC),
        )
        self.assertEqual(PEAKING_FACTORY_DEFAULT_DISPLAY, PEAKING_DISPLAY_OFF)
        self.assertEqual(PEAKING_FACTORY_DEFAULT_LEVEL, PEAKING_LEVEL_MID)
        self.assertEqual(PEAKING_FACTORY_DEFAULT_COLOR, PEAKING_COLOR_WHITE)
        self.assertEqual(
            ALLOWED_PEAKING_COLORS,
            (PEAKING_COLOR_RED, PEAKING_COLOR_YELLOW, PEAKING_COLOR_BLUE, PEAKING_COLOR_WHITE),
        )
        self.assertEqual(
            ALLOWED_PEAKING_LEVELS,
            (PEAKING_LEVEL_HIGH, PEAKING_LEVEL_MID, PEAKING_LEVEL_LOW),
        )
        self.assertEqual(ZEBRA_FACTORY_DEFAULT_DISPLAY, ZEBRA_DISPLAY_OFF)
        self.assertEqual(ZEBRA_FACTORY_DEFAULT_LEVEL, "70")
        self.assertEqual(len(ALLOWED_ZEBRA_PRESET_LEVELS), 8)
        self.assertEqual(ALLOWED_ZEBRA_CUSTOM_MODES, (ZEBRA_LEVEL_CUSTOM_1, ZEBRA_LEVEL_CUSTOM_2))
        self.assertEqual(len(ALLOWED_ZEBRA_LEVELS), 10)
        self.assertEqual((ZEBRA_CUSTOM_IRE_MIN, ZEBRA_CUSTOM_IRE_MAX), (0, 109))
        self.assertEqual((ZEBRA_CUSTOM1_RANGE_MIN, ZEBRA_CUSTOM1_RANGE_MAX), (1, 30))
        self.assertEqual(MENU_DELETE_CHORD_MIN_HOLD_SECONDS, 2.0)
        self.assertEqual(TIER0_VAULT_REQUIRED_ARTIFACTS, ("pnflasha", "cnflasha", "CAMSET01.DAT"))

    def test_03_donor_audit_clean_room_forced_via_flag(self) -> None:
        res = audit_phase228_donor_contracts(force_clean_room=True)
        self.assertTrue(res.valid)
        self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(res.access_mode, "O_RDONLY")
        self.assertEqual(res.files_inspected, 0)
        self.assertTrue(res.within_budget_150ms)
        self.assertLess(res.elapsed_seconds, DONOR_CHECK_MAX_SECONDS)
        self.assertEqual(res.raw_firmware_bytes_leaked, 0)
        self.assertEqual(len(res.checked_markers), len(PINNED_PHASE228_DONOR_SPECS))

    def test_04_donor_audit_clean_room_forced_via_env(self) -> None:
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            res = audit_phase228_donor_contracts()
        self.assertTrue(res.valid)
        self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(res.raw_firmware_bytes_leaked, 0)

    def test_05_donor_audit_default_mode_fast_and_zero_leak(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("FX3_FX6_FORCE_CLEAN_ROOM", None)
            res = audit_phase228_donor_contracts()
        self.assertTrue(res.valid)
        self.assertIn(res.verification_mode, ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"))
        self.assertEqual(res.access_mode, "O_RDONLY")
        self.assertTrue(res.within_budget_150ms)
        self.assertEqual(res.raw_firmware_bytes_leaked, 0)
        dumped = json.dumps(res.to_dict())
        self.assertNotIn("\\x7fELF", dumped)

    def test_06_donor_audit_nonexistent_work_root_falls_back_clean_room(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            res = audit_phase228_donor_contracts(
                work_root=Path(tmp) / "missing_donor_tree", force_clean_room=False
            )
        self.assertTrue(res.valid)
        self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(res.files_inspected, 0)

    def test_07_donor_audit_corrupted_donor_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for _key, (_body, rel, *_rest) in PINNED_PHASE228_DONOR_SPECS.items():
                p = root / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(b"CORRUPTED_STUB_DATA")
            res = audit_phase228_donor_contracts(work_root=root, force_clean_room=False)
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_PHASE228_DONOR_INTEGRITY)
        self.assertEqual(res.verification_mode, "LOCAL_DONOR_O_RDONLY")
        self.assertGreaterEqual(len(res.errors), 2)

    def test_08_donor_audit_budget_exceeded_fails_closed(self) -> None:
        res = audit_phase228_donor_contracts(
            force_clean_room=True, max_budget_seconds=-1.0
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_PHASE228_DONOR_INTEGRITY)
        self.assertFalse(res.within_budget_150ms)

    # ------------------------------------------------------------------
    # Section B: Gate G83 — Ver. 7.02 [Mode Settings] Fixed/Variable,
    #            S&Q 6-Lock Matrix & Zebra/Peaking HDMI Clean-Feed (22 tests)
    # ------------------------------------------------------------------

    def test_09_g83_default_fixed_variable_sq_60fps_4k_and_hdmi_cleanfeed_pass(self) -> None:
        res = verify_sq_fixedvar_6lock_and_zebra_peaking_hdmi_guard()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_VERIFIED_G83)
        self.assertEqual(res.sq_mode_settings, MODE_SETTINGS_FIXED_VARIABLE)
        self.assertTrue(res.legacy_sq_settings_menu_locked)
        self.assertTrue(res.direct_fps_control_active)
        self.assertEqual(res.sq_audio_channels_recorded, 0)
        self.assertFalse(res.sound_recorded_in_sq)
        self.assertFalse(res.audio_out_timing_available)
        self.assertFalse(res.time_code_run_available)
        self.assertFalse(res.hdmi_time_code_output_available)
        self.assertTrue(res.all_6_sq_locks_enforced)
        self.assertTrue(res.local_lcd_zebra_rendered)
        self.assertTrue(res.local_lcd_peaking_rendered)
        self.assertFalse(res.hdmi_zebra_overlay_rendered)
        self.assertFalse(res.hdmi_peaking_overlay_rendered)
        self.assertTrue(res.hdmi_assist_clean_feed_enforced)

    def test_10_g83_fixed_variable_requires_ver_7_00_or_newer(self) -> None:
        res = verify_sq_fixedvar_6lock_and_zebra_peaking_hdmi_guard(
            firmware_version="6.01",
            sq_mode_settings=MODE_SETTINGS_FIXED_VARIABLE,
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            res.status,
            STATUS_BLOCKED_G83_MODE_SETTINGS_FIXED_VARIABLE_OR_SQ_SETTINGS_LOCK_VIOLATION,
        )

    def test_11_g83_fixed_variable_blocks_legacy_sq_settings_unlocked_or_mutated(self) -> None:
        r_unlocked = verify_sq_fixedvar_6lock_and_zebra_peaking_hdmi_guard(
            sq_mode_settings=MODE_SETTINGS_FIXED_VARIABLE,
            legacy_sq_settings_menu_locked=False,
        )
        self.assertFalse(r_unlocked.valid)
        self.assertIn(
            STATUS_BLOCKED_G83_MODE_SETTINGS_FIXED_VARIABLE_OR_SQ_SETTINGS_LOCK_VIOLATION,
            r_unlocked.violation_codes,
        )

        r_mut = verify_sq_fixedvar_6lock_and_zebra_peaking_hdmi_guard(
            sq_mode_settings=MODE_SETTINGS_FIXED_VARIABLE,
            legacy_sq_settings_mutation_attempted=True,
        )
        self.assertFalse(r_mut.valid)
        self.assertIn(
            STATUS_BLOCKED_G83_MODE_SETTINGS_FIXED_VARIABLE_OR_SQ_SETTINGS_LOCK_VIOLATION,
            r_mut.violation_codes,
        )

        r_no_fps = verify_sq_fixedvar_6lock_and_zebra_peaking_hdmi_guard(
            sq_mode_settings=MODE_SETTINGS_FIXED_VARIABLE,
            direct_fps_control_active=False,
        )
        self.assertFalse(r_no_fps.valid)
        self.assertIn(
            STATUS_BLOCKED_G83_MODE_SETTINGS_FIXED_VARIABLE_OR_SQ_SETTINGS_LOCK_VIOLATION,
            r_no_fps.violation_codes,
        )

    def test_12_g83_legacy_variable_mode_allows_unlocked_sq_settings_and_rejects_locked_claim(
        self,
    ) -> None:
        ok = verify_sq_fixedvar_6lock_and_zebra_peaking_hdmi_guard(
            firmware_version="6.01",
            sq_mode_settings=MODE_SETTINGS_VARIABLE,
        )
        self.assertTrue(ok.valid)
        self.assertFalse(ok.legacy_sq_settings_menu_locked)
        self.assertFalse(ok.direct_fps_control_active)

        bad = verify_sq_fixedvar_6lock_and_zebra_peaking_hdmi_guard(
            sq_mode_settings=MODE_SETTINGS_VARIABLE,
            legacy_sq_settings_menu_locked=True,
        )
        self.assertFalse(bad.valid)
        self.assertEqual(
            bad.status,
            STATUS_BLOCKED_G83_MODE_SETTINGS_FIXED_VARIABLE_OR_SQ_SETTINGS_LOCK_VIOLATION,
        )

    def test_13_g83_sq_lock1_zero_audio_channels_and_no_sound_recorded(self) -> None:
        bad_ch = verify_sq_fixedvar_6lock_and_zebra_peaking_hdmi_guard(
            shoot_mode=SHOOT_MODE_SQ, sq_audio_channels_recorded=2
        )
        self.assertFalse(bad_ch.valid)
        self.assertEqual(
            bad_ch.status, STATUS_BLOCKED_G83_SQ_6LOCK_AUDIO_TC_CODEC_OR_PROXY_VIOLATION
        )

        bad_snd = verify_sq_fixedvar_6lock_and_zebra_peaking_hdmi_guard(
            shoot_mode=SHOOT_MODE_SQ, sound_recorded_in_sq=True
        )
        self.assertFalse(bad_snd.valid)
        self.assertEqual(
            bad_snd.status, STATUS_BLOCKED_G83_SQ_6LOCK_AUDIO_TC_CODEC_OR_PROXY_VIOLATION
        )

    def test_14_g83_sq_lock2_audio_out_timing_disabled_in_sq_vs_enabled_in_movie(self) -> None:
        for mode in (AUDIO_OUT_TIMING_LIVE, AUDIO_OUT_TIMING_LIP_SYNC):
            bad_sq = verify_sq_fixedvar_6lock_and_zebra_peaking_hdmi_guard(
                shoot_mode=SHOOT_MODE_SQ,
                audio_out_timing_mode=mode,
                audio_out_timing_available=True,
            )
            self.assertFalse(bad_sq.valid)
            self.assertEqual(
                bad_sq.status,
                STATUS_BLOCKED_G83_SQ_6LOCK_AUDIO_TC_CODEC_OR_PROXY_VIOLATION,
            )

            ok_movie = verify_sq_fixedvar_6lock_and_zebra_peaking_hdmi_guard(
                shoot_mode=SHOOT_MODE_MOVIE,
                audio_out_timing_mode=mode,
                audio_out_timing_available=True,
            )
            self.assertTrue(ok_movie.valid)
            self.assertTrue(ok_movie.audio_out_timing_available)
            self.assertEqual(ok_movie.sq_audio_channels_recorded, 2)

    def test_15_g83_sq_lock3_timecode_run_and_hdmi_tc_output_unavailable_in_sq(self) -> None:
        bad_tc_run = verify_sq_fixedvar_6lock_and_zebra_peaking_hdmi_guard(
            shoot_mode=SHOOT_MODE_SQ, time_code_run_available=True
        )
        self.assertFalse(bad_tc_run.valid)
        self.assertEqual(
            bad_tc_run.status,
            STATUS_BLOCKED_G83_SQ_6LOCK_AUDIO_TC_CODEC_OR_PROXY_VIOLATION,
        )

        bad_tc_out = verify_sq_fixedvar_6lock_and_zebra_peaking_hdmi_guard(
            shoot_mode=SHOOT_MODE_SQ, hdmi_time_code_output_available=True
        )
        self.assertFalse(bad_tc_out.valid)
        self.assertEqual(
            bad_tc_out.status,
            STATUS_BLOCKED_G83_SQ_6LOCK_AUDIO_TC_CODEC_OR_PROXY_VIOLATION,
        )

    def test_16_g83_sq_lock4_240fps_ntsc_blocked_across_all_four_4k_formats(self) -> None:
        for fmt in SQ_240_200FPS_BLOCKED_4K_FORMATS:
            res = verify_sq_fixedvar_6lock_and_zebra_peaking_hdmi_guard(
                video_system=VIDEO_SYSTEM_NTSC,
                shoot_mode=SHOOT_MODE_SQ,
                movie_file_format=fmt,
                rec_frame_rate="23.98p",
                sq_capture_fps=240,
            )
            self.assertFalse(res.valid, msg=f"Expected 240fps blocked on {fmt}")
            self.assertEqual(
                res.status,
                STATUS_BLOCKED_G83_SQ_6LOCK_AUDIO_TC_CODEC_OR_PROXY_VIOLATION,
            )

    def test_17_g83_sq_lock4_200fps_pal_blocked_across_all_four_4k_formats(self) -> None:
        for fmt in SQ_240_200FPS_BLOCKED_4K_FORMATS:
            res = verify_sq_fixedvar_6lock_and_zebra_peaking_hdmi_guard(
                video_system=VIDEO_SYSTEM_PAL,
                shoot_mode=SHOOT_MODE_SQ,
                movie_file_format=fmt,
                rec_frame_rate="25p",
                sq_capture_fps=200,
            )
            self.assertFalse(res.valid, msg=f"Expected 200fps PAL blocked on {fmt}")
            self.assertEqual(
                res.status,
                STATUS_BLOCKED_G83_SQ_6LOCK_AUDIO_TC_CODEC_OR_PROXY_VIOLATION,
            )

    def test_18_g83_sq_240fps_ntsc_and_200fps_pal_allowed_on_hd_formats(self) -> None:
        for fmt in (FILE_FORMAT_XAVC_S_HD, FILE_FORMAT_XAVC_SI_HD):
            ok_ntsc = verify_sq_fixedvar_6lock_and_zebra_peaking_hdmi_guard(
                video_system=VIDEO_SYSTEM_NTSC,
                shoot_mode=SHOOT_MODE_SQ,
                movie_file_format=fmt,
                rec_frame_rate="23.98p",
                sq_capture_fps=240,
                proxy_recording_on=False,
            )
            self.assertTrue(ok_ntsc.valid)
            self.assertAlmostEqual(ok_ntsc.sq_playback_speed_ratio, 23.98 / 240.0, places=3)

            ok_pal = verify_sq_fixedvar_6lock_and_zebra_peaking_hdmi_guard(
                video_system=VIDEO_SYSTEM_PAL,
                shoot_mode=SHOOT_MODE_SQ,
                movie_file_format=fmt,
                rec_frame_rate="25p",
                sq_capture_fps=200,
                proxy_recording_on=False,
            )
            self.assertTrue(ok_pal.valid)
            self.assertAlmostEqual(ok_pal.sq_playback_speed_ratio, 0.125, places=3)

    def test_19_g83_sq_lock5_120fps_and_100fps_blocked_on_xavc_si_dci_4k(self) -> None:
        bad_ntsc = verify_sq_fixedvar_6lock_and_zebra_peaking_hdmi_guard(
            video_system=VIDEO_SYSTEM_NTSC,
            shoot_mode=SHOOT_MODE_SQ,
            movie_file_format=FILE_FORMAT_XAVC_SI_DCI_4K,
            rec_frame_rate="24.00p",
            sq_capture_fps=120,
        )
        self.assertFalse(bad_ntsc.valid)
        self.assertEqual(
            bad_ntsc.status,
            STATUS_BLOCKED_G83_SQ_6LOCK_AUDIO_TC_CODEC_OR_PROXY_VIOLATION,
        )

        bad_pal = verify_sq_fixedvar_6lock_and_zebra_peaking_hdmi_guard(
            video_system=VIDEO_SYSTEM_PAL,
            shoot_mode=SHOOT_MODE_SQ,
            movie_file_format=FILE_FORMAT_XAVC_SI_DCI_4K,
            rec_frame_rate="25p",
            sq_capture_fps=100,
        )
        self.assertFalse(bad_pal.valid)
        self.assertEqual(
            bad_pal.status,
            STATUS_BLOCKED_G83_SQ_6LOCK_AUDIO_TC_CODEC_OR_PROXY_VIOLATION,
        )

    def test_20_g83_sq_120fps_allowed_on_uhd_4k_and_60fps_allowed_on_dci_4k(self) -> None:
        for fmt in (FILE_FORMAT_XAVC_HS_4K, FILE_FORMAT_XAVC_S_4K, FILE_FORMAT_XAVC_SI_4K):
            ok_120 = verify_sq_fixedvar_6lock_and_zebra_peaking_hdmi_guard(
                video_system=VIDEO_SYSTEM_NTSC,
                shoot_mode=SHOOT_MODE_SQ,
                movie_file_format=fmt,
                rec_frame_rate="23.98p",
                sq_capture_fps=120,
                proxy_recording_on=False,
            )
            self.assertTrue(ok_120.valid, msg=f"120fps should pass on {fmt}")

        ok_dci_60 = verify_sq_fixedvar_6lock_and_zebra_peaking_hdmi_guard(
            video_system=VIDEO_SYSTEM_NTSC,
            shoot_mode=SHOOT_MODE_SQ,
            movie_file_format=FILE_FORMAT_XAVC_SI_DCI_4K,
            rec_frame_rate="24.00p",
            sq_capture_fps=60,
            proxy_recording_on=True,
        )
        self.assertTrue(ok_dci_60.valid)

    def test_21_g83_sq_lock6_proxy_blocked_at_rec_119_88p_or_100p(self) -> None:
        bad_ntsc = verify_sq_fixedvar_6lock_and_zebra_peaking_hdmi_guard(
            video_system=VIDEO_SYSTEM_NTSC,
            shoot_mode=SHOOT_MODE_SQ,
            movie_file_format=FILE_FORMAT_XAVC_S_4K,
            rec_frame_rate="119.88p",
            sq_capture_fps=60,
            proxy_recording_on=True,
        )
        self.assertFalse(bad_ntsc.valid)
        self.assertEqual(
            bad_ntsc.status,
            STATUS_BLOCKED_G83_SQ_6LOCK_AUDIO_TC_CODEC_OR_PROXY_VIOLATION,
        )

        bad_pal = verify_sq_fixedvar_6lock_and_zebra_peaking_hdmi_guard(
            video_system=VIDEO_SYSTEM_PAL,
            shoot_mode=SHOOT_MODE_SQ,
            movie_file_format=FILE_FORMAT_XAVC_S_4K,
            rec_frame_rate="100p",
            sq_capture_fps=50,
            proxy_recording_on=True,
        )
        self.assertFalse(bad_pal.valid)
        self.assertEqual(
            bad_pal.status,
            STATUS_BLOCKED_G83_SQ_6LOCK_AUDIO_TC_CODEC_OR_PROXY_VIOLATION,
        )

    def test_22_g83_sq_lock6_proxy_blocked_when_capture_fps_ge_120_or_100_but_allowed_at_60(
        self,
    ) -> None:
        bad_120 = verify_sq_fixedvar_6lock_and_zebra_peaking_hdmi_guard(
            video_system=VIDEO_SYSTEM_NTSC,
            shoot_mode=SHOOT_MODE_SQ,
            movie_file_format=FILE_FORMAT_XAVC_S_4K,
            rec_frame_rate="23.98p",
            sq_capture_fps=120,
            proxy_recording_on=True,
        )
        self.assertFalse(bad_120.valid)
        self.assertEqual(
            bad_120.status,
            STATUS_BLOCKED_G83_SQ_6LOCK_AUDIO_TC_CODEC_OR_PROXY_VIOLATION,
        )

        bad_100 = verify_sq_fixedvar_6lock_and_zebra_peaking_hdmi_guard(
            video_system=VIDEO_SYSTEM_PAL,
            shoot_mode=SHOOT_MODE_SQ,
            movie_file_format=FILE_FORMAT_XAVC_S_4K,
            rec_frame_rate="25p",
            sq_capture_fps=100,
            proxy_recording_on=True,
        )
        self.assertFalse(bad_100.valid)

        ok_60 = verify_sq_fixedvar_6lock_and_zebra_peaking_hdmi_guard(
            video_system=VIDEO_SYSTEM_NTSC,
            shoot_mode=SHOOT_MODE_SQ,
            movie_file_format=FILE_FORMAT_XAVC_S_4K,
            rec_frame_rate="59.94p",
            sq_capture_fps=60,
            proxy_recording_on=True,
        )
        self.assertTrue(ok_60.valid)

    def test_23_g83_zebra_and_peaking_all_levels_and_colors_local_lcd_only(self) -> None:
        for lvl in ALLOWED_PEAKING_LEVELS:
            for col in ALLOWED_PEAKING_COLORS:
                res = verify_sq_fixedvar_6lock_and_zebra_peaking_hdmi_guard(
                    zebra_display_mode=ZEBRA_DISPLAY_ON,
                    peaking_display_mode=PEAKING_DISPLAY_ON,
                    peaking_level=lvl,
                    peaking_color=col,
                    hdmi_info_display_on=False,
                )
                self.assertTrue(res.valid)
                self.assertTrue(res.local_lcd_zebra_rendered)
                self.assertTrue(res.local_lcd_peaking_rendered)
                self.assertFalse(res.hdmi_zebra_overlay_rendered)
                self.assertFalse(res.hdmi_peaking_overlay_rendered)

    def test_24_g83_hdmi_info_display_on_blanks_local_lcd_and_still_suppresses_hdmi_overlays(
        self,
    ) -> None:
        cf = resolve_fx3_zebra_peaking_hdmi_cleanfeed(
            zebra_display_mode=ZEBRA_DISPLAY_ON,
            peaking_display_mode=PEAKING_DISPLAY_ON,
            hdmi_info_display_on=True,
        )
        self.assertTrue(cf["camera_lcd_blanked_by_hdmi_info"])
        self.assertFalse(cf["expected_local_lcd_zebra_rendered"])
        self.assertFalse(cf["expected_local_lcd_peaking_rendered"])
        self.assertFalse(cf["expected_hdmi_zebra_overlay_rendered"])
        self.assertFalse(cf["expected_hdmi_peaking_overlay_rendered"])

        res = verify_sq_fixedvar_6lock_and_zebra_peaking_hdmi_guard(
            zebra_display_mode=ZEBRA_DISPLAY_ON,
            peaking_display_mode=PEAKING_DISPLAY_ON,
            hdmi_info_display_on=True,
        )
        self.assertTrue(res.valid)
        self.assertTrue(res.camera_lcd_blanked_by_hdmi_info)
        self.assertFalse(res.local_lcd_zebra_rendered)
        self.assertFalse(res.local_lcd_peaking_rendered)
        self.assertFalse(res.hdmi_zebra_overlay_rendered)
        self.assertFalse(res.hdmi_peaking_overlay_rendered)

    def test_25_g83_hdmi_zebra_or_peaking_leak_blocks_fail_closed(self) -> None:
        leak_z = verify_sq_fixedvar_6lock_and_zebra_peaking_hdmi_guard(
            hdmi_info_display_on=True,
            hdmi_zebra_overlay_rendered=True,
        )
        self.assertFalse(leak_z.valid)
        self.assertEqual(
            leak_z.status, STATUS_BLOCKED_G83_HDMI_ZEBRA_OR_PEAKING_ASSIST_OVERLAY_LEAK
        )

        leak_p = verify_sq_fixedvar_6lock_and_zebra_peaking_hdmi_guard(
            hdmi_info_display_on=False,
            hdmi_peaking_overlay_rendered=True,
        )
        self.assertFalse(leak_p.valid)
        self.assertEqual(
            leak_p.status, STATUS_BLOCKED_G83_HDMI_ZEBRA_OR_PEAKING_ASSIST_OVERLAY_LEAK
        )

    def test_26_g83_lcd_zebra_or_peaking_mismatch_when_hdmi_info_on_blocks(self) -> None:
        bad_lcd = verify_sq_fixedvar_6lock_and_zebra_peaking_hdmi_guard(
            zebra_display_mode=ZEBRA_DISPLAY_ON,
            hdmi_info_display_on=True,
            local_lcd_zebra_rendered=True,
        )
        self.assertFalse(bad_lcd.valid)
        self.assertEqual(
            bad_lcd.status, STATUS_BLOCKED_G83_HDMI_ZEBRA_OR_PEAKING_ASSIST_OVERLAY_LEAK
        )

    def test_27_g83_invalid_telemetry_enums_and_fps_bounds_fail_closed(self) -> None:
        bad_body = verify_sq_fixedvar_6lock_and_zebra_peaking_hdmi_guard(
            body_model_name="ILME-FX6"
        )
        self.assertFalse(bad_body.valid)
        self.assertEqual(bad_body.status, STATUS_BLOCKED_G83_TELEMETRY_INVALID)

        bad_pal_fps = verify_sq_fixedvar_6lock_and_zebra_peaking_hdmi_guard(
            video_system=VIDEO_SYSTEM_PAL,
            rec_frame_rate="25p",
            sq_capture_fps=240,
            movie_file_format=FILE_FORMAT_XAVC_S_HD,
        )
        self.assertFalse(bad_pal_fps.valid)
        self.assertEqual(bad_pal_fps.status, STATUS_BLOCKED_G83_TELEMETRY_INVALID)

        bad_wheel = verify_sq_fixedvar_6lock_and_zebra_peaking_hdmi_guard(
            wheel_right_default_function="Wrong Function"
        )
        self.assertFalse(bad_wheel.valid)
        self.assertEqual(bad_wheel.status, STATUS_BLOCKED_G83_TELEMETRY_INVALID)

    def test_28_g83_ntsc_vs_pal_rec_frame_rate_cross_system_rejected(self) -> None:
        bad_ntsc_25 = verify_sq_fixedvar_6lock_and_zebra_peaking_hdmi_guard(
            video_system=VIDEO_SYSTEM_NTSC, rec_frame_rate="25p"
        )
        self.assertFalse(bad_ntsc_25.valid)
        self.assertEqual(bad_ntsc_25.status, STATUS_BLOCKED_G83_TELEMETRY_INVALID)

        bad_pal_24 = verify_sq_fixedvar_6lock_and_zebra_peaking_hdmi_guard(
            video_system=VIDEO_SYSTEM_PAL, rec_frame_rate="23.98p"
        )
        self.assertFalse(bad_pal_24.valid)
        self.assertEqual(bad_pal_24.status, STATUS_BLOCKED_G83_TELEMETRY_INVALID)

    def test_29_g83_evaluate_dual_mode_and_persistent_write_block(self) -> None:
        v_donor, r_donor = evaluate_g83_sq_fixedvar_zebra_peaking_hdmi_guard(
            force_clean_room=False
        )
        self.assertTrue(v_donor.passed)
        self.assertTrue(r_donor.valid)
        self.assertEqual(v_donor.gate_id, G83_GATE_ID)
        self.assertFalse(r_donor.persistent_emmc_writes_authorized)

        v_clean, r_clean = evaluate_g83_sq_fixedvar_zebra_peaking_hdmi_guard(
            force_clean_room=True
        )
        self.assertTrue(v_clean.passed)
        self.assertEqual(r_clean.verification_mode, "CLEAN_ROOM_SYNTHETIC")

        v_wr, r_wr = evaluate_g83_sq_fixedvar_zebra_peaking_hdmi_guard(
            force_clean_room=True, request_persistent_emmc_writes=True
        )
        self.assertFalse(v_wr.passed)
        self.assertEqual(r_wr.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)

    def test_30_g83_resolve_fx3_mode_settings_and_sq_6locks_speed_ratio_quick_motion(
        self,
    ) -> None:
        st = resolve_fx3_mode_settings_and_sq_6locks(
            firmware_version="7.02",
            video_system=VIDEO_SYSTEM_NTSC,
            shoot_mode=SHOOT_MODE_SQ,
            sq_mode_settings=MODE_SETTINGS_FIXED_VARIABLE,
            movie_file_format=FILE_FORMAT_XAVC_HS_4K,
            rec_frame_rate="59.94p",
            sq_capture_fps=1,
            proxy_recording_on=True,
        )
        self.assertTrue(st["firmware_supports_fixed_variable"])
        self.assertAlmostEqual(st["sq_playback_speed_ratio"], 59.94, places=2)
        self.assertFalse(st["lock4_240_200fps_4k_blocked"])
        self.assertFalse(st["lock5_120_100fps_dci4k_blocked"])
        self.assertFalse(st["lock6_proxy_hfr_blocked"])

    # ------------------------------------------------------------------
    # Section C: Gate G84 — [Zebra Display] Camera Settings Reset Survival
    #            & Format Quick/Full + MENU+Delete 2s Chord Vault Guard (20 tests)
    # ------------------------------------------------------------------

    def test_31_g84_default_zebra_survival_and_slot1_vault_idle_hard_lock_pass(self) -> None:
        res = verify_zebra_reset_survival_and_fullformat_chord_vault_guard()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_VERIFIED_G84)
        self.assertEqual(
            res.wheel_left_default_function, CONTROL_WHEEL_LEFT_DEFAULT_ZEBRA_SELECT
        )
        self.assertEqual(res.effective_post_reset_zebra_display, ZEBRA_DISPLAY_ON)
        self.assertEqual(res.effective_post_reset_zebra_level, ZEBRA_LEVEL_CUSTOM_1)
        self.assertTrue(res.zebra_survived_camera_settings_reset)
        self.assertEqual((res.custom1_band_min_ire, res.custom1_band_max_ire), (65, 75))
        self.assertEqual(res.custom2_lower_limit_ire, 100)
        self.assertTrue(res.slot1_format_hard_locked)

    def test_32_g84_all_9_zebra_levels_survive_camera_settings_reset(self) -> None:
        for lvl in ALLOWED_ZEBRA_LEVELS:
            res = verify_zebra_reset_survival_and_fullformat_chord_vault_guard(
                pre_reset_zebra_display=ZEBRA_DISPLAY_ON,
                pre_reset_zebra_level=lvl,
                reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
            )
            self.assertTrue(res.valid, msg=f"Zebra level {lvl} failed survival")
            self.assertEqual(res.effective_post_reset_zebra_display, ZEBRA_DISPLAY_ON)
            self.assertEqual(res.effective_post_reset_zebra_level, lvl)
            self.assertTrue(res.zebra_survived_camera_settings_reset)

    def test_33_g84_camera_settings_reset_wiping_zebra_blocks_fail_closed(self) -> None:
        bad_disp = verify_zebra_reset_survival_and_fullformat_chord_vault_guard(
            pre_reset_zebra_display=ZEBRA_DISPLAY_ON,
            pre_reset_zebra_level="100+",
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
            post_reset_zebra_display=ZEBRA_DISPLAY_OFF,
        )
        self.assertFalse(bad_disp.valid)
        self.assertEqual(
            bad_disp.status,
            STATUS_BLOCKED_G84_ZEBRA_CAMERA_SETTINGS_RESET_PERSISTENCE_VIOLATION,
        )

        bad_lvl = verify_zebra_reset_survival_and_fullformat_chord_vault_guard(
            pre_reset_zebra_display=ZEBRA_DISPLAY_ON,
            pre_reset_zebra_level=ZEBRA_LEVEL_CUSTOM_2,
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
            post_reset_zebra_level="70",
        )
        self.assertFalse(bad_lvl.valid)
        self.assertEqual(
            bad_lvl.status,
            STATUS_BLOCKED_G84_ZEBRA_CAMERA_SETTINGS_RESET_PERSISTENCE_VIOLATION,
        )

    def test_34_g84_initialize_resets_zebra_to_factory_off_and_70(self) -> None:
        ok_init = verify_zebra_reset_survival_and_fullformat_chord_vault_guard(
            pre_reset_zebra_display=ZEBRA_DISPLAY_ON,
            pre_reset_zebra_level=ZEBRA_LEVEL_CUSTOM_2,
            reset_action=RESET_ACTION_INITIALIZE,
        )
        self.assertTrue(ok_init.valid)
        self.assertEqual(
            ok_init.effective_post_reset_zebra_display, ZEBRA_FACTORY_DEFAULT_DISPLAY
        )
        self.assertEqual(
            ok_init.effective_post_reset_zebra_level, ZEBRA_FACTORY_DEFAULT_LEVEL
        )
        self.assertFalse(ok_init.zebra_survived_camera_settings_reset)

        bad_init = verify_zebra_reset_survival_and_fullformat_chord_vault_guard(
            pre_reset_zebra_display=ZEBRA_DISPLAY_ON,
            pre_reset_zebra_level=ZEBRA_LEVEL_CUSTOM_2,
            reset_action=RESET_ACTION_INITIALIZE,
            post_reset_zebra_display=ZEBRA_DISPLAY_ON,
        )
        self.assertFalse(bad_init.valid)
        self.assertEqual(
            bad_init.status,
            STATUS_BLOCKED_G84_ZEBRA_CAMERA_SETTINGS_RESET_PERSISTENCE_VIOLATION,
        )

    def test_35_g84_custom1_band_clamping_and_custom2_ire_bounds(self) -> None:
        clamped = verify_zebra_reset_survival_and_fullformat_chord_vault_guard(
            pre_reset_zebra_level=ZEBRA_LEVEL_CUSTOM_1,
            custom1_std_level=105,
            custom1_exposure_range=10,
            custom2_lower_limit_ire=109,
        )
        self.assertTrue(clamped.valid)
        self.assertEqual((clamped.custom1_band_min_ire, clamped.custom1_band_max_ire), (95, 109))
        self.assertEqual(clamped.custom2_lower_limit_ire, 109)

        bad_c1_std = verify_zebra_reset_survival_and_fullformat_chord_vault_guard(
            custom1_std_level=110
        )
        self.assertFalse(bad_c1_std.valid)
        self.assertEqual(
            bad_c1_std.status, STATUS_BLOCKED_G84_ZEBRA_LEVEL_OR_CUSTOM_THRESHOLD_INVALID
        )

        bad_c1_rng = verify_zebra_reset_survival_and_fullformat_chord_vault_guard(
            custom1_exposure_range=ZEBRA_CUSTOM1_RANGE_MAX + 1
        )
        self.assertFalse(bad_c1_rng.valid)
        self.assertEqual(
            bad_c1_rng.status, STATUS_BLOCKED_G84_ZEBRA_LEVEL_OR_CUSTOM_THRESHOLD_INVALID
        )

        bad_c2 = verify_zebra_reset_survival_and_fullformat_chord_vault_guard(
            custom2_lower_limit_ire=-1
        )
        self.assertFalse(bad_c2.valid)
        self.assertEqual(
            bad_c2.status, STATUS_BLOCKED_G84_ZEBRA_LEVEL_OR_CUSTOM_THRESHOLD_INVALID
        )

    def test_36_g84_slot1_quick_format_menu_enter_blocked_on_active_tier0_vault(self) -> None:
        res = verify_zebra_reset_survival_and_fullformat_chord_vault_guard(
            slot1_tier0_vault_present=True,
            slot1_tier0_vault_active=True,
            target_slot=FORMAT_SLOT_1,
            format_trigger=FORMAT_TRIGGER_MENU_ENTER,
            format_mode=FORMAT_MODE_QUICK,
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            res.status, STATUS_BLOCKED_G84_SLOT1_TIER0_VAULT_FORMAT_OR_CHORD_LOCKOUT
        )

    def test_37_g84_slot1_full_format_delete_toggle_blocked_on_active_tier0_vault(
        self,
    ) -> None:
        res = verify_zebra_reset_survival_and_fullformat_chord_vault_guard(
            slot1_tier0_vault_present=True,
            slot1_tier0_vault_active=True,
            target_slot=FORMAT_SLOT_1,
            format_trigger=FORMAT_TRIGGER_CONFIRM_DELETE_TOGGLE,
            format_mode=FORMAT_MODE_FULL,
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            res.status, STATUS_BLOCKED_G84_SLOT1_TIER0_VAULT_FORMAT_OR_CHORD_LOCKOUT
        )

    def test_38_g84_slot1_menu_plus_delete_2s_chord_blocked_on_tier0_vault(self) -> None:
        for mode in (FORMAT_MODE_QUICK, FORMAT_MODE_FULL):
            res = verify_zebra_reset_survival_and_fullformat_chord_vault_guard(
                slot1_tier0_vault_present=True,
                slot1_tier0_vault_active=False,
                off_camera_sha256_verified=False,
                target_slot=FORMAT_SLOT_1,
                format_trigger=FORMAT_TRIGGER_MENU_DELETE_2S_CHORD,
                format_mode=mode,
                menu_delete_chord_hold_seconds=2.2,
            )
            self.assertFalse(res.valid)
            self.assertEqual(
                res.status,
                STATUS_BLOCKED_G84_SLOT1_TIER0_VAULT_FORMAT_OR_CHORD_LOCKOUT,
            )

    def test_39_g84_slot1_hard_lock_bypass_rejected_even_when_idle(self) -> None:
        res = verify_zebra_reset_survival_and_fullformat_chord_vault_guard(
            slot1_tier0_vault_present=True,
            slot1_tier0_vault_active=True,
            slot1_format_hard_locked_enforced=False,
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            res.status, STATUS_BLOCKED_G84_SLOT1_TIER0_VAULT_FORMAT_OR_CHORD_LOCKOUT
        )

    def test_40_g84_slot2_scratch_quick_full_and_chord_format_permitted(self) -> None:
        ok_quick = verify_zebra_reset_survival_and_fullformat_chord_vault_guard(
            slot1_tier0_vault_present=True,
            slot1_tier0_vault_active=True,
            target_slot=FORMAT_SLOT_2,
            format_trigger=FORMAT_TRIGGER_MENU_ENTER,
            format_mode=FORMAT_MODE_QUICK,
        )
        self.assertTrue(ok_quick.valid)
        self.assertFalse(ok_quick.full_format_wipes_all_data_blocks)

        ok_full = verify_zebra_reset_survival_and_fullformat_chord_vault_guard(
            slot1_tier0_vault_present=True,
            slot1_tier0_vault_active=True,
            target_slot=FORMAT_SLOT_2,
            format_trigger=FORMAT_TRIGGER_CONFIRM_DELETE_TOGGLE,
            format_mode=FORMAT_MODE_FULL,
        )
        self.assertTrue(ok_full.valid)
        self.assertTrue(ok_full.full_format_wipes_all_data_blocks)

        ok_chord = verify_zebra_reset_survival_and_fullformat_chord_vault_guard(
            slot1_tier0_vault_present=True,
            slot1_tier0_vault_active=True,
            target_slot=FORMAT_SLOT_2,
            format_trigger=FORMAT_TRIGGER_MENU_DELETE_2S_CHORD,
            format_mode=FORMAT_MODE_QUICK,
            menu_delete_chord_hold_seconds=2.5,
        )
        self.assertTrue(ok_chord.valid)
        self.assertTrue(ok_chord.menu_delete_chord_dialog_invoked)

    def test_41_g84_slot1_format_permitted_only_after_sha256_verified_and_card_swapped(
        self,
    ) -> None:
        still_unswapped = verify_zebra_reset_survival_and_fullformat_chord_vault_guard(
            slot1_tier0_vault_present=True,
            slot1_tier0_vault_active=False,
            off_camera_sha256_verified=True,
            slot1_vault_card_removed_or_wp_locked=False,
            target_slot=FORMAT_SLOT_1,
            format_trigger=FORMAT_TRIGGER_MENU_ENTER,
            format_mode=FORMAT_MODE_QUICK,
        )
        self.assertFalse(still_unswapped.valid)

        swapped_ok = verify_zebra_reset_survival_and_fullformat_chord_vault_guard(
            slot1_tier0_vault_present=True,
            slot1_tier0_vault_active=False,
            off_camera_sha256_verified=True,
            slot1_vault_card_removed_or_wp_locked=True,
            target_slot=FORMAT_SLOT_1,
            format_trigger=FORMAT_TRIGGER_CONFIRM_DELETE_TOGGLE,
            format_mode=FORMAT_MODE_FULL,
        )
        self.assertTrue(swapped_ok.valid)
        self.assertFalse(swapped_ok.slot1_format_hard_locked)
        self.assertTrue(swapped_ok.full_format_wipes_all_data_blocks)

    def test_42_g84_menu_delete_chord_under_2s_hold_rejected(self) -> None:
        bad_hold = verify_zebra_reset_survival_and_fullformat_chord_vault_guard(
            target_slot=FORMAT_SLOT_2,
            format_trigger=FORMAT_TRIGGER_MENU_DELETE_2S_CHORD,
            format_mode=FORMAT_MODE_QUICK,
            menu_delete_chord_hold_seconds=1.4,
        )
        self.assertFalse(bad_hold.valid)
        self.assertEqual(bad_hold.status, STATUS_BLOCKED_G84_TELEMETRY_INVALID)

    def test_43_g84_enter_vs_delete_toggle_trigger_mode_consistency_enforced(self) -> None:
        bad_enter_full = verify_zebra_reset_survival_and_fullformat_chord_vault_guard(
            target_slot=FORMAT_SLOT_2,
            format_trigger=FORMAT_TRIGGER_MENU_ENTER,
            format_mode=FORMAT_MODE_FULL,
        )
        self.assertFalse(bad_enter_full.valid)
        self.assertEqual(bad_enter_full.status, STATUS_BLOCKED_G84_TELEMETRY_INVALID)

        bad_del_quick = verify_zebra_reset_survival_and_fullformat_chord_vault_guard(
            target_slot=FORMAT_SLOT_2,
            format_trigger=FORMAT_TRIGGER_CONFIRM_DELETE_TOGGLE,
            format_mode=FORMAT_MODE_QUICK,
        )
        self.assertFalse(bad_del_quick.valid)
        self.assertEqual(bad_del_quick.status, STATUS_BLOCKED_G84_TELEMETRY_INVALID)

    def test_44_g84_full_format_mid_cancel_semantics_data_already_erased_and_usable(
        self,
    ) -> None:
        ok_cancel = verify_zebra_reset_survival_and_fullformat_chord_vault_guard(
            target_slot=FORMAT_SLOT_2,
            format_trigger=FORMAT_TRIGGER_CONFIRM_DELETE_TOGGLE,
            format_mode=FORMAT_MODE_FULL,
            full_format_canceled_midway=True,
        )
        self.assertTrue(ok_cancel.valid)
        self.assertTrue(ok_cancel.mid_cancel_prior_data_erased)
        self.assertTrue(ok_cancel.mid_cancel_card_usable)

        bad_not_erased = verify_zebra_reset_survival_and_fullformat_chord_vault_guard(
            target_slot=FORMAT_SLOT_2,
            format_trigger=FORMAT_TRIGGER_CONFIRM_DELETE_TOGGLE,
            format_mode=FORMAT_MODE_FULL,
            full_format_canceled_midway=True,
            mid_cancel_prior_data_erased=False,
        )
        self.assertFalse(bad_not_erased.valid)
        self.assertEqual(
            bad_not_erased.status,
            STATUS_BLOCKED_G84_FULL_FORMAT_CANCEL_SEMANTICS_MISMATCH,
        )

        bad_unusable = verify_zebra_reset_survival_and_fullformat_chord_vault_guard(
            target_slot=FORMAT_SLOT_2,
            format_trigger=FORMAT_TRIGGER_CONFIRM_DELETE_TOGGLE,
            format_mode=FORMAT_MODE_FULL,
            full_format_canceled_midway=True,
            mid_cancel_card_usable=False,
        )
        self.assertFalse(bad_unusable.valid)
        self.assertEqual(
            bad_unusable.status,
            STATUS_BLOCKED_G84_FULL_FORMAT_CANCEL_SEMANTICS_MISMATCH,
        )

    def test_45_g84_mid_cancel_invalid_on_quick_or_none_format(self) -> None:
        bad = verify_zebra_reset_survival_and_fullformat_chord_vault_guard(
            target_slot=FORMAT_SLOT_2,
            format_trigger=FORMAT_TRIGGER_MENU_ENTER,
            format_mode=FORMAT_MODE_QUICK,
            full_format_canceled_midway=True,
        )
        self.assertFalse(bad.valid)
        self.assertEqual(
            bad.status, STATUS_BLOCKED_G84_FULL_FORMAT_CANCEL_SEMANTICS_MISMATCH
        )

    def test_46_g84_invalid_zebra_enums_and_wheel_left_fail_closed(self) -> None:
        bad_lvl = verify_zebra_reset_survival_and_fullformat_chord_vault_guard(
            pre_reset_zebra_level="65"
        )
        self.assertFalse(bad_lvl.valid)
        self.assertEqual(
            bad_lvl.status, STATUS_BLOCKED_G84_ZEBRA_LEVEL_OR_CUSTOM_THRESHOLD_INVALID
        )

        bad_disp = verify_zebra_reset_survival_and_fullformat_chord_vault_guard(
            pre_reset_zebra_display="Auto"
        )
        self.assertFalse(bad_disp.valid)
        self.assertEqual(
            bad_disp.status, STATUS_BLOCKED_G84_ZEBRA_LEVEL_OR_CUSTOM_THRESHOLD_INVALID
        )

        bad_wheel = verify_zebra_reset_survival_and_fullformat_chord_vault_guard(
            wheel_left_default_function="ISO"
        )
        self.assertFalse(bad_wheel.valid)
        self.assertEqual(bad_wheel.status, STATUS_BLOCKED_G84_TELEMETRY_INVALID)

    def test_47_g84_invalid_reset_action_and_format_slot_fail_closed(self) -> None:
        bad_rst = verify_zebra_reset_survival_and_fullformat_chord_vault_guard(
            reset_action="HARD_BRICK"
        )
        self.assertFalse(bad_rst.valid)
        self.assertEqual(bad_rst.status, STATUS_BLOCKED_G84_TELEMETRY_INVALID)

        bad_slot = verify_zebra_reset_survival_and_fullformat_chord_vault_guard(
            target_slot="SLOT_9"
        )
        self.assertFalse(bad_slot.valid)
        self.assertEqual(bad_slot.status, STATUS_BLOCKED_G84_TELEMETRY_INVALID)

    def test_48_g84_chord_dialog_telemetry_contradiction_rejected(self) -> None:
        bad = verify_zebra_reset_survival_and_fullformat_chord_vault_guard(
            target_slot=FORMAT_SLOT_2,
            format_trigger=FORMAT_TRIGGER_NONE,
            format_mode=FORMAT_MODE_NONE,
            menu_delete_chord_dialog_invoked=True,
        )
        self.assertFalse(bad.valid)
        self.assertEqual(bad.status, STATUS_BLOCKED_G84_TELEMETRY_INVALID)

    def test_49_g84_resolve_helpers_direct_contracts(self) -> None:
        c_d, c_l, c_r, exp_d, exp_l = resolve_fx3_zebra_reset_survival(
            pre_reset_zebra_display="on",
            pre_reset_zebra_level="100_plus",
            reset_action=RESET_ACTION_NONE,
        )
        self.assertEqual((c_d, c_l, c_r, exp_d, exp_l), ("On", "100+", "NONE", "On", "100+"))

        v = resolve_fx3_slot1_format_and_chord_vault_lock(
            slot1_tier0_vault_present=False,
            target_slot="slot1",
            format_trigger="menu_enter",
            format_mode="quick",
        )
        self.assertFalse(v["slot1_format_hard_locked"])
        self.assertFalse(v["slot1_vault_violation"])

    def test_50_g84_evaluate_dual_mode_and_persistent_write_block(self) -> None:
        v_donor, r_donor = evaluate_g84_zebra_reset_and_fullformat_chord_vault_guard(
            force_clean_room=False
        )
        self.assertTrue(v_donor.passed)
        self.assertTrue(r_donor.valid)
        self.assertEqual(v_donor.gate_id, G84_GATE_ID)
        self.assertFalse(r_donor.persistent_emmc_writes_authorized)

        v_clean, r_clean = evaluate_g84_zebra_reset_and_fullformat_chord_vault_guard(
            force_clean_room=True
        )
        self.assertTrue(v_clean.passed)
        self.assertEqual(r_clean.verification_mode, "CLEAN_ROOM_SYNTHETIC")

        v_wr, r_wr = evaluate_g84_zebra_reset_and_fullformat_chord_vault_guard(
            force_clean_room=True, request_persistent_emmc_writes=True
        )
        self.assertFalse(v_wr.passed)
        self.assertEqual(r_wr.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)

    # ------------------------------------------------------------------
    # Section D: Unified 84-Gate Master Preflight (`verify-84-gates`)
    #            Dual-Mode, Fault Propagation & CLI Tests (12 tests)
    # ------------------------------------------------------------------

    def test_51_preflight_84_offline_donor_mode_81_of_84_verified(self) -> None:
        r = self.offline_84
        self.assertEqual(r.schema, REALHW_SQ_FIXEDVAR_ZEBRA_PEAKING_FULLFORMAT_84GATE_SCHEMA)
        self.assertEqual(r.summary["total_gates"], 84)
        self.assertEqual(r.summary["verified_gates"], 81)
        self.assertEqual(r.summary["blocked_or_pending_gates"], 3)
        self.assertEqual(r.summary["g01_to_g12_verified"], 9)
        self.assertEqual(r.summary["g13_to_g82_verified"], 70)
        self.assertEqual(r.summary["g83_to_g84_verified"], 2)
        self.assertTrue(r.offline_81_gates_verified)
        self.assertFalse(r.all_84_gates_verified)
        self.assertTrue(r.g13_to_g84_all_passed)
        self.assertTrue(r.g83_to_g84_all_passed)
        self.assertEqual(r.status, "VERIFIED_81_OF_84_AWAITING_PHYSICAL_TIER0")
        self.assertEqual(len(r.gates), 84)
        self.assertEqual(r.gates[-2]["gate_code"], G83_GATE_CODE)
        self.assertEqual(r.gates[-1]["gate_code"], G84_GATE_CODE)

    def test_52_preflight_84_dry_run_donor_mode_84_of_84_verified(self) -> None:
        r = self.dryrun_84
        self.assertEqual(r.summary["verified_gates"], 84)
        self.assertTrue(r.all_84_gates_verified)
        self.assertTrue(r.offline_81_gates_verified)
        self.assertTrue(r.dry_run_rehearsal_only)
        self.assertEqual(r.status, "VERIFIED_ALL_84_GATES_DRY_RUN_SIMULATED_BACKUP")
        self.assertFalse(r.overall_ready_for_hardware_attach)
        self.assertFalse(r.hardware_live_attachment_authorized)
        self.assertFalse(r.el3_payload_transmit_authorized)
        self.assertFalse(r.spi_nor_write_authorized)
        self.assertFalse(r.persistent_emmc_writes_authorized)
        self.assertEqual(r.usb_packets_transmitted, 0)
        self.assertEqual(r.raw_firmware_bytes_leaked, 0)

    def test_53_preflight_84_clean_room_offline_and_dry_run_parity(self) -> None:
        self.assertEqual(self.clean_offline_84.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(self.clean_offline_84.clean_room_forced)
        self.assertEqual(self.clean_offline_84.summary["verified_gates"], 81)
        self.assertTrue(self.clean_offline_84.offline_81_gates_verified)

        self.assertEqual(self.clean_dryrun_84.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(self.clean_dryrun_84.summary["verified_gates"], 84)
        self.assertTrue(self.clean_dryrun_84.all_84_gates_verified)
        self.assertFalse(self.clean_dryrun_84.overall_ready_for_hardware_attach)

    def test_54_preflight_84_propagates_g83_sq_or_hdmi_cleanfeed_violation(self) -> None:
        r = evaluate_84gate_preflight(
            force_clean_room=True,
            master_82_override=self.clean_offline_82,
            sq_fixedvar_zebra_peaking_kwargs={
                "movie_file_format": FILE_FORMAT_XAVC_HS_4K,
                "sq_capture_fps": 240,
            },
        )
        self.assertFalse(r.g83_to_g84_all_passed)
        self.assertFalse(r.offline_81_gates_verified)
        self.assertEqual(
            r.status, STATUS_BLOCKED_G83_SQ_6LOCK_AUDIO_TC_CODEC_OR_PROXY_VIOLATION
        )
        self.assertEqual(r.summary["verified_gates"], 80)

    def test_55_preflight_84_propagates_g84_slot1_vault_chord_violation(self) -> None:
        r = evaluate_84gate_preflight(
            force_clean_room=True,
            master_82_override=self.clean_offline_82,
            zebra_reset_fullformat_kwargs={
                "target_slot": FORMAT_SLOT_1,
                "format_trigger": FORMAT_TRIGGER_MENU_DELETE_2S_CHORD,
                "format_mode": FORMAT_MODE_FULL,
                "menu_delete_chord_hold_seconds": 2.1,
            },
        )
        self.assertFalse(r.g83_to_g84_all_passed)
        self.assertFalse(r.offline_81_gates_verified)
        self.assertEqual(
            r.status, STATUS_BLOCKED_G84_SLOT1_TIER0_VAULT_FORMAT_OR_CHORD_LOCKOUT
        )
        self.assertEqual(r.summary["verified_gates"], 80)

    def test_56_preflight_84_persistent_emmc_write_request_blocks_all(self) -> None:
        r = evaluate_84gate_preflight(
            force_clean_room=True,
            master_82_override=self.clean_dryrun_82,
            simulate_bench_dry_run=True,
            request_persistent_emmc_writes=True,
        )
        self.assertEqual(r.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        self.assertFalse(r.offline_81_gates_verified)
        self.assertFalse(r.all_84_gates_verified)
        self.assertFalse(r.h0_h1_trial_entry_allowed)
        self.assertFalse(r.persistent_emmc_writes_authorized)

    def test_57_cli_verify_g83_text_and_json_modes(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cli_main(["verify-g83-sq-fixedvar-zebra-peaking", "--force-clean-room"])
        self.assertEqual(rc, 0)
        self.assertIn("status=VERIFIED_SQ_FIXED_VARIABLE_6LOCK_MATRIX", buf.getvalue())

        buf_json = io.StringIO()
        with contextlib.redirect_stdout(buf_json):
            rc_j = cli_main(
                ["verify-g83-sq-fixedvar-zebra-peaking", "--force-clean-room", "--json"]
            )
        self.assertEqual(rc_j, 0)
        payload = json.loads(buf_json.getvalue())
        self.assertTrue(payload["valid"])
        self.assertEqual(payload["verification_mode"], "CLEAN_ROOM_SYNTHETIC")

    def test_58_cli_verify_g84_text_and_json_modes(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cli_main(["verify-g84-zebra-reset-fullformat-chord", "--force-clean-room"])
        self.assertEqual(rc, 0)
        self.assertIn("status=VERIFIED_ZEBRA_CAMERA_SETTINGS_RESET_SURVIVAL", buf.getvalue())

        buf_json = io.StringIO()
        with contextlib.redirect_stdout(buf_json):
            rc_j = cli_main(
                ["verify-g84-zebra-reset-fullformat-chord", "--force-clean-room", "--json"]
            )
        self.assertEqual(rc_j, 0)
        payload = json.loads(buf_json.getvalue())
        self.assertTrue(payload["valid"])
        self.assertTrue(payload["zebra_reset_fullformat_guard"]["slot1_format_hard_locked"])

    def test_59_cli_verify_84_gates_offline_text_and_json(self) -> None:
        with mock.patch(
            "fx3_safety.__main__.evaluate_84gate_preflight",
            return_value=self.clean_offline_84,
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = cli_main(["verify-84-gates", "--force-clean-room"])
            self.assertEqual(rc, 0)
            self.assertIn("verified=81/84", buf.getvalue())

            buf_j = io.StringIO()
            with contextlib.redirect_stdout(buf_j):
                rc_j = cli_main(["verify-84-gates", "--force-clean-room", "--json"])
            self.assertEqual(rc_j, 0)
            parsed = json.loads(buf_j.getvalue())
            self.assertEqual(parsed["summary"]["verified_gates"], 81)
            self.assertFalse(parsed["overall_ready_for_hardware_attach"])

    def test_60_cli_verify_84_gates_simulate_bench_dry_run_84_of_84(self) -> None:
        with mock.patch(
            "fx3_safety.__main__.evaluate_84gate_preflight",
            return_value=self.clean_dryrun_84,
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = cli_main(
                    ["verify-84-gates", "--force-clean-room", "--simulate-bench-dry-run"]
                )
            self.assertEqual(rc, 0)
            self.assertIn("verified=84/84", buf.getvalue())
            self.assertIn("overall_ready_for_hardware_attach=False", buf.getvalue())

    def test_61_module_main_entrypoint_text_and_json(self) -> None:
        with mock.patch(
            "fx3_safety.realhw_sq_fixedvar_zebra_peaking_fullformat_and_84gate_guard.evaluate_84gate_preflight",
            return_value=self.clean_dryrun_84,
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = module_main(["--force-clean-room", "--simulate-bench-dry-run"])
            self.assertEqual(rc, 0)
            self.assertIn("verified=84/84", buf.getvalue())

            buf_j = io.StringIO()
            with contextlib.redirect_stdout(buf_j):
                rc_j = module_main(
                    ["--force-clean-room", "--simulate-bench-dry-run", "--json"]
                )
            self.assertEqual(rc_j, 0)
            data = json.loads(buf_j.getvalue())
            self.assertEqual(data["summary"]["verified_gates"], 84)

    def test_62_zero_raw_firmware_bytes_leaked_in_serialized_84gate_reports(self) -> None:
        for rep in (
            self.offline_84,
            self.dryrun_84,
            self.clean_offline_84,
            self.clean_dryrun_84,
        ):
            dumped = json.dumps(rep.to_dict(), ensure_ascii=False)
            self.assertEqual(rep.raw_firmware_bytes_leaked, 0)
            self.assertEqual(rep.usb_packets_transmitted, 0)
            self.assertNotIn("\\x7fELF", dumped)


if __name__ == "__main__":
    unittest.main()
