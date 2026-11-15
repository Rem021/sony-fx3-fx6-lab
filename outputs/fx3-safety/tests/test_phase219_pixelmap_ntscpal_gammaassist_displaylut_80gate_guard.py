"""Phase 219 (`80/80` Milestone) Dual-Mode Unit Tests (60 tests, >=50 required):
Gates G79 (`G79_PIXEL_MAPPING_REBOOT_LOWBATT_LOCK_AND_CNFLASHA_READONLY_GUARD`),
G80 (`G80_NTSCPAL_RESET_PERSISTENCE_AND_GAMMA_ASSIST_DISPLAY_LUT_SPLIT_GUARD`),
and Unified 80-Gate Master Safety Preflight (`verify-80-gates`).
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
from fx3_safety.realhw_pixelmap_ntscpal_gammaassist_displaylut_and_80gate_guard import (
    ALLOWED_FX3_702_GAMMA_ASSIST_TYPES,
    ALLOWED_LOG_SHOOTING_MODES_G80,
    ALLOWED_RESET_ACTIONS,
    ALLOWED_VIDEO_SYSTEMS,
    AUTO_PIXEL_MAPPING_DEFAULT_ON,
    CNFLASHA_CALIBRATION_PARTITION,
    DEFAULT_SYNTHETIC_H0_SURFACE_SHA256,
    DONOR_CHECK_MAX_SECONDS,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    G79,
    G79_GATE_CODE,
    G79_GATE_ID,
    G80,
    G80_GATE_CODE,
    G80_GATE_ID,
    GAMMA_ASSIST_TYPE_AUTO,
    GAMMA_ASSIST_TYPE_HLG_709,
    GAMMA_ASSIST_TYPE_HLG_BT2020,
    GAMMA_ASSIST_TYPE_SLOG3_709,
    HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    LOG_SHOOTING_CINE_EI,
    LOG_SHOOTING_CINE_EI_QUICK,
    LOG_SHOOTING_FLEXIBLE_ISO,
    LOG_SHOOTING_OFF,
    MANUAL_PIXEL_MAPPING_RECOMMENDED_MAX_DAYS,
    NTSC_ALLOWED_FRAME_RATES,
    NTSC_ALLOWED_TC_FORMATS,
    PAL_ALLOWED_FRAME_RATES,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PINNED_PHASE219_DONOR_SPECS,
    PIXEL_MAPPING_MIN_BATTERY_SOC_PCT,
    RAW_FIRMWARE_BYTES_LEAKED,
    REALHW_PIXELMAP_NTSCPAL_GAMMAASSIST_DISPLAYLUT_80GATE_SCHEMA,
    RESET_ACTION_CAMERA_SETTINGS_RESET,
    RESET_ACTION_INITIALIZE,
    RESET_ACTION_NONE,
    SPI_NOR_WRITE_AUTHORIZED,
    STARTUP_BANNER_NONE,
    STARTUP_BANNER_RUNNING_ON_NTSC,
    STARTUP_BANNER_RUNNING_ON_PAL,
    STATUS_BLOCKED_G79_AUTO_PIXEL_MAPPING_SHUTTER_OR_CADENCE_VIOLATION,
    STATUS_BLOCKED_G79_CNFLASHA_FACTORY_CALIBRATION_WRITE_FIREWALL,
    STATUS_BLOCKED_G79_MANUAL_PIXEL_MAPPING_LOW_BATTERY_LOCKOUT,
    STATUS_BLOCKED_G79_PIXEL_MAPPING_MANDATORY_REBOOT_OR_H0_H2_MISMATCH,
    STATUS_BLOCKED_G79_PIXEL_MAPPING_OPERATOR_CONTROL_LOCKOUT_VIOLATION,
    STATUS_BLOCKED_G79_TELEMETRY_INVALID,
    STATUS_BLOCKED_G80_EXTERNAL_HDMI_GAMMA_ASSIST_SCOPE_VIOLATION,
    STATUS_BLOCKED_G80_GAMMA_ASSIST_TYPE_OR_SLOG2_FORBIDDEN,
    STATUS_BLOCKED_G80_LOG_SHOOTING_GAMMA_ASSIST_OR_DISPLAY_LUT_SPLIT_VIOLATION,
    STATUS_BLOCKED_G80_NTSCPAL_FRAMERATE_OR_TC_FORMAT_MATRIX_VIOLATION,
    STATUS_BLOCKED_G80_NTSCPAL_RESET_PERSISTENCE_ASYMMETRY_VIOLATION,
    STATUS_BLOCKED_G80_NTSCPAL_STARTUP_BANNER_OR_MEDIA_DB_VIOLATION,
    STATUS_BLOCKED_G80_TELEMETRY_INVALID,
    STATUS_BLOCKED_PERSISTENT_EMMC_WRITE,
    STATUS_BLOCKED_PHASE219_DONOR_INTEGRITY,
    STATUS_VERIFIED_G79,
    STATUS_VERIFIED_G80,
    TC_FORMAT_DF,
    TC_FORMAT_NDF,
    TC_FORMAT_PAL_LOCKED,
    USB_PACKETS_TRANSMITTED,
    VIDEO_SYSTEM_NTSC,
    VIDEO_SYSTEM_PAL,
    audit_phase219_donor_contracts,
    evaluate_80_master_safety_gates,
    evaluate_80gate_preflight,
    evaluate_g79_pixelmap_reboot_cnflasha_guard,
    evaluate_g80_ntscpal_gammaassist_displaylut_guard,
    main as module_main,
    resolve_fx3_gamma_assist_and_display_lut_split,
    resolve_fx3_ntscpal_state,
    resolve_fx3_pixel_mapping_lifecycle,
    run_80_gate_preflight,
    verify_ntscpal_persistence_and_gamma_assist_displaylut_guard,
    verify_pixel_mapping_reboot_lowbatt_and_cnflasha_guard,
)


class TestPhase219PixelMapNtscPalGammaAssistDisplayLut80GateGuard(unittest.TestCase):
    """Comprehensive dual-mode tests for Phase 219 Gates G79, G80 & 80-Gate Preflight."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.offline_78 = fx3_safety.evaluate_78gate_preflight()
        cls.dryrun_78 = fx3_safety.evaluate_78gate_preflight(dry_run_simulated=True)
        cls.offline_80 = evaluate_80gate_preflight(master_78_override=cls.offline_78)
        cls.dryrun_80 = evaluate_80gate_preflight(
            simulate_bench_dry_run=True, master_78_override=cls.dryrun_78
        )
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            cls.clean_offline_78 = fx3_safety.evaluate_78gate_preflight(
                force_clean_room=True
            )
            cls.clean_dryrun_78 = fx3_safety.evaluate_78gate_preflight(
                force_clean_room=True, dry_run_simulated=True
            )
            cls.clean_offline_80 = evaluate_80gate_preflight(
                force_clean_room=True, master_78_override=cls.clean_offline_78
            )
            cls.clean_dryrun_80 = evaluate_80gate_preflight(
                force_clean_room=True,
                simulate_bench_dry_run=True,
                master_78_override=cls.clean_dryrun_78,
            )

    # ------------------------------------------------------------------
    # Section A: Package Exports & Bounded Donor Contract Audit (8 tests)
    # ------------------------------------------------------------------

    def test_01_public_package_exports_and_hard_redline_constants(self) -> None:
        self.assertEqual(G79, G79_GATE_CODE)
        self.assertEqual(G80, G80_GATE_CODE)
        self.assertEqual(
            G79_GATE_CODE,
            "G79_PIXEL_MAPPING_REBOOT_LOWBATT_LOCK_AND_CNFLASHA_READONLY_GUARD",
        )
        self.assertEqual(
            G80_GATE_CODE,
            "G80_NTSCPAL_RESET_PERSISTENCE_AND_GAMMA_ASSIST_DISPLAY_LUT_SPLIT_GUARD",
        )
        self.assertFalse(EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        self.assertFalse(SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        self.assertEqual(USB_PACKETS_TRANSMITTED, 0)
        self.assertEqual(RAW_FIRMWARE_BYTES_LEAKED, 0)
        self.assertIs(fx3_safety.evaluate_80gate_preflight, evaluate_80gate_preflight)
        self.assertIs(fx3_safety.run_80_gate_preflight, run_80_gate_preflight)
        self.assertIs(
            fx3_safety.evaluate_80_master_safety_gates, evaluate_80_master_safety_gates
        )
        self.assertIs(
            fx3_safety.evaluate_g79_pixelmap_reboot_cnflasha_guard,
            evaluate_g79_pixelmap_reboot_cnflasha_guard,
        )
        self.assertIs(
            fx3_safety.evaluate_g80_ntscpal_gammaassist_displaylut_guard,
            evaluate_g80_ntscpal_gammaassist_displaylut_guard,
        )

    def test_02_all_phase219_symbols_present_in_dunder_all(self) -> None:
        for sym in (
            "G79",
            "G80",
            "Master80GateReport",
            "evaluate_80gate_preflight",
            "evaluate_80_master_safety_gates",
            "run_80_gate_preflight",
            "evaluate_g79_pixelmap_reboot_cnflasha_guard",
            "evaluate_g80_ntscpal_gammaassist_displaylut_guard",
            "verify_pixel_mapping_reboot_lowbatt_and_cnflasha_guard",
            "verify_ntscpal_persistence_and_gamma_assist_displaylut_guard",
            "audit_phase219_donor_contracts",
            "realhw_pixelmap_ntscpal_gammaassist_displaylut_and_80gate_guard",
        ):
            self.assertIn(sym, fx3_safety.__all__)
            self.assertTrue(hasattr(fx3_safety, sym))

    def test_03_pinned_phase219_donor_specs_structure(self) -> None:
        self.assertEqual(len(PINNED_PHASE219_DONOR_SPECS), 4)
        self.assertEqual(DONOR_CHECK_MAX_SECONDS, 0.15)
        for key, (role, rel, exp_size, exp_sha, markers, label) in PINNED_PHASE219_DONOR_SPECS.items():
            self.assertIn(role, ("fx3", "fx6"), key)
            self.assertTrue(rel)
            self.assertGreater(exp_size, 0)
            self.assertEqual(len(exp_sha), 64)
            self.assertGreater(len(markers), 0)
            self.assertIn("::", label)

    def test_04_donor_audit_default_mode_under_150ms_and_zero_leak(self) -> None:
        res = audit_phase219_donor_contracts()
        self.assertTrue(res.valid)
        self.assertEqual(res.access_mode, "O_RDONLY")
        self.assertTrue(res.within_budget_150ms)
        self.assertLess(res.elapsed_seconds, DONOR_CHECK_MAX_SECONDS)
        self.assertEqual(res.raw_firmware_bytes_leaked, 0)
        self.assertTrue(res.fx3_contracts_verified)
        self.assertTrue(res.fx6_contracts_verified)
        self.assertEqual(res.missing_markers, ())

    def test_05_donor_audit_env_force_clean_room_synthetic_fallback(self) -> None:
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            res = audit_phase219_donor_contracts()
        self.assertTrue(res.valid)
        self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(res.files_inspected, 0)
        self.assertEqual(res.raw_firmware_bytes_leaked, 0)
        self.assertEqual(len(res.checked_markers), 4)

    def test_06_donor_audit_missing_work_root_falls_back_cleanly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            res = audit_phase219_donor_contracts(work_root=Path(tmp))
        self.assertTrue(res.valid)
        self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(res.files_inspected, 0)

    def test_07_donor_audit_detects_corrupted_local_donor_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for _key, (_role, rel, _sz, _sha, _m, _lbl) in PINNED_PHASE219_DONOR_SPECS.items():
                p = root / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(b"corrupted-donor-bytes")
            with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "0"}):
                res = audit_phase219_donor_contracts(
                    work_root=root, force_clean_room=False
                )
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_PHASE219_DONOR_INTEGRITY)
        self.assertEqual(res.verification_mode, "LOCAL_DONOR_O_RDONLY")
        self.assertGreater(len(res.errors), 0)

    def test_08_donor_audit_enforces_strict_time_budget(self) -> None:
        res = audit_phase219_donor_contracts(
            force_clean_room=True, max_budget_seconds=0.0
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_PHASE219_DONOR_INTEGRITY)
        self.assertFalse(res.within_budget_150ms)

    # ------------------------------------------------------------------
    # Section B: Gate G79 — Pixel Mapping Reboot, Low-Batt & cnflasha RO (17 tests)
    # ------------------------------------------------------------------

    def test_09_g79_default_auto_and_manual_pixel_mapping_passes(self) -> None:
        res = verify_pixel_mapping_reboot_lowbatt_and_cnflasha_guard()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_VERIFIED_G79)
        self.assertEqual(res.violation_codes, ())
        self.assertTrue(res.auto_pixel_mapping_on)
        self.assertTrue(res.power_off_shutter_sound_expected)
        self.assertFalse(res.manual_3day_cadence_recommended)
        self.assertTrue(res.operator_controls_locked_during_exec)
        self.assertTrue(res.auto_camera_restart_on_completion)
        self.assertTrue(res.stageb_tmp_overlay_unmounted_post_reboot)
        self.assertTrue(res.h0_equals_h2_post_reboot)
        self.assertEqual(res.cnflasha_partition, CNFLASHA_CALIBRATION_PARTITION)
        self.assertTrue(res.cnflasha_userspace_write_blocked)
        self.assertFalse(res.persistent_emmc_writes_authorized)

    def test_10_g79_auto_pixel_mapping_poweroff_shutter_sound_even_in_silent_mode(self) -> None:
        shutter_snd, rec_3day, low_batt = resolve_fx3_pixel_mapping_lifecycle(
            auto_pixel_mapping_on=True, silent_mode_on=True, battery_soc_pct=90.0
        )
        self.assertTrue(shutter_snd)
        self.assertFalse(rec_3day)
        self.assertFalse(low_batt)

        res = verify_pixel_mapping_reboot_lowbatt_and_cnflasha_guard(
            auto_pixel_mapping_on=True,
            silent_mode_on=True,
            claimed_silent_mode_suppresses_poweroff_shutter=False,
        )
        self.assertTrue(res.valid)
        self.assertTrue(res.power_off_shutter_sound_expected)

    def test_11_g79_blocks_false_claim_that_silent_mode_suppresses_poweroff_shutter(self) -> None:
        res = verify_pixel_mapping_reboot_lowbatt_and_cnflasha_guard(
            auto_pixel_mapping_on=True,
            silent_mode_on=True,
            claimed_silent_mode_suppresses_poweroff_shutter=True,
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            res.status, STATUS_BLOCKED_G79_AUTO_PIXEL_MAPPING_SHUTTER_OR_CADENCE_VIOLATION
        )

    def test_12_g79_auto_pixel_mapping_off_within_3_days_passes(self) -> None:
        self.assertTrue(AUTO_PIXEL_MAPPING_DEFAULT_ON)
        self.assertEqual(MANUAL_PIXEL_MAPPING_RECOMMENDED_MAX_DAYS, 3.0)
        res = verify_pixel_mapping_reboot_lowbatt_and_cnflasha_guard(
            auto_pixel_mapping_on=False,
            days_since_last_pixel_mapping=2.5,
            manual_pixel_mapping_requested=False,
        )
        self.assertTrue(res.valid)
        self.assertFalse(res.power_off_shutter_sound_expected)
        self.assertTrue(res.manual_3day_cadence_recommended)

    def test_13_g79_auto_pixel_mapping_off_overdue_without_manual_mapping_blocks(self) -> None:
        res = verify_pixel_mapping_reboot_lowbatt_and_cnflasha_guard(
            auto_pixel_mapping_on=False,
            days_since_last_pixel_mapping=3.5,
            manual_pixel_mapping_requested=False,
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            res.status, STATUS_BLOCKED_G79_AUTO_PIXEL_MAPPING_SHUTTER_OR_CADENCE_VIOLATION
        )

    def test_14_g79_auto_pixel_mapping_off_overdue_with_manual_mapping_executes(self) -> None:
        res = verify_pixel_mapping_reboot_lowbatt_and_cnflasha_guard(
            auto_pixel_mapping_on=False,
            days_since_last_pixel_mapping=5.0,
            manual_pixel_mapping_requested=True,
            battery_soc_pct=75.0,
        )
        self.assertTrue(res.valid)

    def test_15_g79_manual_pixel_mapping_low_battery_soc_lockout(self) -> None:
        self.assertEqual(PIXEL_MAPPING_MIN_BATTERY_SOC_PCT, 20.0)
        res_19 = verify_pixel_mapping_reboot_lowbatt_and_cnflasha_guard(
            manual_pixel_mapping_requested=True, battery_soc_pct=19.9
        )
        self.assertFalse(res_19.valid)
        self.assertEqual(
            res_19.status, STATUS_BLOCKED_G79_MANUAL_PIXEL_MAPPING_LOW_BATTERY_LOCKOUT
        )
        self.assertTrue(res_19.low_battery_lockout_triggered)

        res_20 = verify_pixel_mapping_reboot_lowbatt_and_cnflasha_guard(
            manual_pixel_mapping_requested=True, battery_soc_pct=20.0
        )
        self.assertTrue(res_20.valid)

    def test_16_g79_manual_pixel_mapping_low_battery_warning_flag_lockout(self) -> None:
        res = verify_pixel_mapping_reboot_lowbatt_and_cnflasha_guard(
            manual_pixel_mapping_requested=True,
            battery_soc_pct=35.0,
            battery_low_warning_active=True,
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            res.status, STATUS_BLOCKED_G79_MANUAL_PIXEL_MAPPING_LOW_BATTERY_LOCKOUT
        )

    def test_17_g79_operator_controls_unlocked_during_exec_blocks(self) -> None:
        res = verify_pixel_mapping_reboot_lowbatt_and_cnflasha_guard(
            manual_pixel_mapping_requested=True,
            operator_controls_locked_during_exec=False,
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            res.status, STATUS_BLOCKED_G79_PIXEL_MAPPING_OPERATOR_CONTROL_LOCKOUT_VIOLATION
        )

    def test_18_g79_concurrent_operator_input_accepted_during_exec_blocks(self) -> None:
        res = verify_pixel_mapping_reboot_lowbatt_and_cnflasha_guard(
            manual_pixel_mapping_requested=True,
            concurrent_operator_input_accepted=True,
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            res.status, STATUS_BLOCKED_G79_PIXEL_MAPPING_OPERATOR_CONTROL_LOCKOUT_VIOLATION
        )

    def test_19_g79_missing_automatic_camera_restart_on_completion_blocks(self) -> None:
        res = verify_pixel_mapping_reboot_lowbatt_and_cnflasha_guard(
            manual_pixel_mapping_requested=True,
            auto_camera_restart_on_completion=False,
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            res.status, STATUS_BLOCKED_G79_PIXEL_MAPPING_MANDATORY_REBOOT_OR_H0_H2_MISMATCH
        )

    def test_20_g79_stageb_tmp_overlay_residual_or_h0_h2_mismatch_blocks(self) -> None:
        res_overlay = verify_pixel_mapping_reboot_lowbatt_and_cnflasha_guard(
            manual_pixel_mapping_requested=True,
            stageb_tmp_overlay_unmounted_post_reboot=False,
        )
        self.assertFalse(res_overlay.valid)
        self.assertEqual(
            res_overlay.status,
            STATUS_BLOCKED_G79_PIXEL_MAPPING_MANDATORY_REBOOT_OR_H0_H2_MISMATCH,
        )

        res_hash = verify_pixel_mapping_reboot_lowbatt_and_cnflasha_guard(
            manual_pixel_mapping_requested=True,
            h0_surface_sha256=DEFAULT_SYNTHETIC_H0_SURFACE_SHA256,
            h2_post_reboot_surface_sha256="a" * 64,
        )
        self.assertFalse(res_hash.valid)
        self.assertFalse(res_hash.h0_equals_h2_post_reboot)
        self.assertEqual(
            res_hash.status,
            STATUS_BLOCKED_G79_PIXEL_MAPPING_MANDATORY_REBOOT_OR_H0_H2_MISMATCH,
        )

    def test_21_g79_cnflasha_userspace_write_unblocked_blocks(self) -> None:
        res = verify_pixel_mapping_reboot_lowbatt_and_cnflasha_guard(
            cnflasha_userspace_write_blocked=False
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            res.status, STATUS_BLOCKED_G79_CNFLASHA_FACTORY_CALIBRATION_WRITE_FIREWALL
        )

    def test_22_g79_cnflasha_write_attempt_or_mutation_bytes_blocks(self) -> None:
        res_attempt = verify_pixel_mapping_reboot_lowbatt_and_cnflasha_guard(
            cnflasha_write_attempted=True
        )
        self.assertFalse(res_attempt.valid)
        self.assertEqual(
            res_attempt.status,
            STATUS_BLOCKED_G79_CNFLASHA_FACTORY_CALIBRATION_WRITE_FIREWALL,
        )

        res_mut = verify_pixel_mapping_reboot_lowbatt_and_cnflasha_guard(
            cnflasha_calibration_mutation_bytes=16
        )
        self.assertFalse(res_mut.valid)
        self.assertEqual(
            res_mut.status,
            STATUS_BLOCKED_G79_CNFLASHA_FACTORY_CALIBRATION_WRITE_FIREWALL,
        )

    def test_23_g79_rejects_wrong_model_old_firmware_and_bad_telemetry(self) -> None:
        res_model = verify_pixel_mapping_reboot_lowbatt_and_cnflasha_guard(
            body_model_name="ILME-FX6"
        )
        self.assertFalse(res_model.valid)
        self.assertEqual(res_model.status, STATUS_BLOCKED_G79_TELEMETRY_INVALID)

        res_fw = verify_pixel_mapping_reboot_lowbatt_and_cnflasha_guard(
            firmware_version="6.00"
        )
        self.assertFalse(res_fw.valid)
        self.assertEqual(res_fw.status, STATUS_BLOCKED_G79_TELEMETRY_INVALID)

        res_sha = verify_pixel_mapping_reboot_lowbatt_and_cnflasha_guard(
            h0_surface_sha256="not-a-sha256"
        )
        self.assertFalse(res_sha.valid)
        self.assertEqual(res_sha.status, STATUS_BLOCKED_G79_TELEMETRY_INVALID)

    def test_24_evaluate_g79_dual_mode_normal_and_clean_room(self) -> None:
        v_norm, r_norm = evaluate_g79_pixelmap_reboot_cnflasha_guard()
        self.assertTrue(v_norm.passed)
        self.assertEqual(v_norm.gate_id, G79_GATE_ID)
        self.assertEqual(r_norm.status, STATUS_VERIFIED_G79)
        self.assertEqual(r_norm.raw_firmware_bytes_leaked, 0)

        v_clean, r_clean = evaluate_g79_pixelmap_reboot_cnflasha_guard(
            force_clean_room=True
        )
        self.assertTrue(v_clean.passed)
        self.assertEqual(r_clean.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_25_evaluate_g79_blocks_persistent_emmc_write_request(self) -> None:
        verdict, res = evaluate_g79_pixelmap_reboot_cnflasha_guard(
            force_clean_room=True, request_persistent_emmc_writes=True
        )
        self.assertFalse(verdict.passed)
        self.assertFalse(res.valid)
        self.assertIn(STATUS_BLOCKED_PERSISTENT_EMMC_WRITE, res.violation_codes)

    # ------------------------------------------------------------------
    # Section C: Gate G80 — NTSC/PAL Persistence & Gamma Assist / Display LUT (20 tests)
    # ------------------------------------------------------------------

    def test_26_g80_default_ntsc_2398p_cine_ei_display_lut_passes(self) -> None:
        res = verify_ntscpal_persistence_and_gamma_assist_displaylut_guard()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_VERIFIED_G80)
        self.assertEqual(res.effective_post_reset_system, VIDEO_SYSTEM_NTSC)
        self.assertTrue(res.ntsc_exclusive_2398p_active)
        self.assertTrue(res.tc_format_df_ndf_available)
        self.assertEqual(res.startup_notification_banner, STARTUP_BANNER_NONE)
        self.assertTrue(res.camera_settings_reset_preserved_system)
        self.assertTrue(res.initialize_restores_regional_default)
        self.assertTrue(res.log_shooting_active)
        self.assertTrue(res.gamma_display_assist_locked_off_by_log)
        self.assertFalse(res.effective_gamma_display_assist_on)
        self.assertTrue(res.effective_display_lut_preview_on)
        self.assertEqual(res.active_preview_governor, "DISPLAY_LUT")
        self.assertTrue(res.builtin_lcd_only_scope)
        self.assertFalse(res.external_hdmi_gamma_assist_applied)

    def test_27_g80_ntsc_accepts_all_ntsc_rates_and_df_ndf_tc_formats(self) -> None:
        for fps in NTSC_ALLOWED_FRAME_RATES:
            for tc_fmt in NTSC_ALLOWED_TC_FORMATS:
                res = verify_ntscpal_persistence_and_gamma_assist_displaylut_guard(
                    regional_default_system="NTSC",
                    configured_ntsc_pal_system="NTSC",
                    selected_frame_rate=fps,
                    selected_tc_format=tc_fmt,
                )
                self.assertTrue(res.valid, f"Expected valid for {fps}/{tc_fmt}")

    def test_28_g80_ntsc_rejects_pal_frame_rates_and_pal_locked_tc(self) -> None:
        for pal_fps in PAL_ALLOWED_FRAME_RATES:
            res = verify_ntscpal_persistence_and_gamma_assist_displaylut_guard(
                configured_ntsc_pal_system="NTSC", selected_frame_rate=pal_fps
            )
            self.assertFalse(res.valid)
            self.assertEqual(
                res.status,
                STATUS_BLOCKED_G80_NTSCPAL_FRAMERATE_OR_TC_FORMAT_MATRIX_VIOLATION,
            )

        res_tc = verify_ntscpal_persistence_and_gamma_assist_displaylut_guard(
            configured_ntsc_pal_system="NTSC",
            selected_frame_rate="29.97p",
            selected_tc_format="PAL_LOCKED",
        )
        self.assertFalse(res_tc.valid)
        self.assertEqual(
            res_tc.status,
            STATUS_BLOCKED_G80_NTSCPAL_FRAMERATE_OR_TC_FORMAT_MATRIX_VIOLATION,
        )

    def test_29_g80_pal_accepts_25p_50p_100p_with_locked_tc_and_banner(self) -> None:
        for fps in PAL_ALLOWED_FRAME_RATES:
            res = verify_ntscpal_persistence_and_gamma_assist_displaylut_guard(
                regional_default_system="NTSC",
                configured_ntsc_pal_system="PAL",
                reset_action=RESET_ACTION_NONE,
                selected_frame_rate=fps,
                selected_tc_format=TC_FORMAT_PAL_LOCKED,
            )
            self.assertTrue(res.valid, fps)
            self.assertEqual(
                res.startup_notification_banner, STARTUP_BANNER_RUNNING_ON_PAL
            )
            self.assertFalse(res.tc_format_df_ndf_available)
            self.assertFalse(res.ntsc_exclusive_2398p_active)

    def test_30_g80_pal_blocks_ntsc_exclusive_2398p_and_other_ntsc_rates(self) -> None:
        for ntsc_fps in ("23.98p", "29.97p", "59.94p", "119.88p"):
            res = verify_ntscpal_persistence_and_gamma_assist_displaylut_guard(
                regional_default_system="PAL",
                configured_ntsc_pal_system="PAL",
                selected_frame_rate=ntsc_fps,
                selected_tc_format=TC_FORMAT_PAL_LOCKED,
            )
            self.assertFalse(res.valid, ntsc_fps)
            self.assertEqual(
                res.status,
                STATUS_BLOCKED_G80_NTSCPAL_FRAMERATE_OR_TC_FORMAT_MATRIX_VIOLATION,
            )

    def test_31_g80_pal_blocks_df_and_ndf_tc_format_selection(self) -> None:
        for tc_fmt in (TC_FORMAT_DF, TC_FORMAT_NDF):
            res = verify_ntscpal_persistence_and_gamma_assist_displaylut_guard(
                regional_default_system="PAL",
                configured_ntsc_pal_system="PAL",
                selected_frame_rate="25p",
                selected_tc_format=tc_fmt,
            )
            self.assertFalse(res.valid, tc_fmt)
            self.assertEqual(
                res.status,
                STATUS_BLOCKED_G80_NTSCPAL_FRAMERATE_OR_TC_FORMAT_MATRIX_VIOLATION,
            )

    def test_32_g80_startup_banner_running_on_ntsc_for_pal_default_body(self) -> None:
        eff, banner, rates, tc_avail = resolve_fx3_ntscpal_state(
            regional_default_system="PAL",
            configured_ntsc_pal_system="NTSC",
            reset_action=RESET_ACTION_NONE,
        )
        self.assertEqual(eff, VIDEO_SYSTEM_NTSC)
        self.assertEqual(banner, STARTUP_BANNER_RUNNING_ON_NTSC)
        self.assertEqual(rates, NTSC_ALLOWED_FRAME_RATES)
        self.assertTrue(tc_avail)

    def test_33_g80_startup_banner_mismatch_or_untracked_media_db_blocks(self) -> None:
        res_banner = verify_ntscpal_persistence_and_gamma_assist_displaylut_guard(
            regional_default_system="NTSC",
            configured_ntsc_pal_system="PAL",
            selected_frame_rate="25p",
            selected_tc_format=TC_FORMAT_PAL_LOCKED,
            observed_startup_banner="NONE",
        )
        self.assertFalse(res_banner.valid)
        self.assertEqual(
            res_banner.status, STATUS_BLOCKED_G80_NTSCPAL_STARTUP_BANNER_OR_MEDIA_DB_VIOLATION
        )

        res_db = verify_ntscpal_persistence_and_gamma_assist_displaylut_guard(
            media_db_system_tracked=False
        )
        self.assertFalse(res_db.valid)
        self.assertEqual(
            res_db.status, STATUS_BLOCKED_G80_NTSCPAL_STARTUP_BANNER_OR_MEDIA_DB_VIOLATION
        )

    def test_34_g80_camera_settings_reset_preserves_non_default_ntscpal(self) -> None:
        res = verify_ntscpal_persistence_and_gamma_assist_displaylut_guard(
            regional_default_system="NTSC",
            configured_ntsc_pal_system="PAL",
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
            observed_post_reset_system="PAL",
            selected_frame_rate="50p",
            selected_tc_format=TC_FORMAT_PAL_LOCKED,
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.effective_post_reset_system, VIDEO_SYSTEM_PAL)
        self.assertEqual(res.startup_notification_banner, STARTUP_BANNER_RUNNING_ON_PAL)

    def test_35_g80_initialize_resets_ntscpal_back_to_regional_default(self) -> None:
        res = verify_ntscpal_persistence_and_gamma_assist_displaylut_guard(
            regional_default_system="NTSC",
            configured_ntsc_pal_system="PAL",
            reset_action=RESET_ACTION_INITIALIZE,
            observed_post_reset_system="NTSC",
            selected_frame_rate="23.98p",
            selected_tc_format=TC_FORMAT_NDF,
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.effective_post_reset_system, VIDEO_SYSTEM_NTSC)
        self.assertEqual(res.startup_notification_banner, STARTUP_BANNER_NONE)

    def test_36_g80_reset_persistence_asymmetry_violation_blocks(self) -> None:
        res_csr = verify_ntscpal_persistence_and_gamma_assist_displaylut_guard(
            regional_default_system="NTSC",
            configured_ntsc_pal_system="PAL",
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
            observed_post_reset_system="NTSC",
            selected_frame_rate="25p",
            selected_tc_format=TC_FORMAT_PAL_LOCKED,
        )
        self.assertFalse(res_csr.valid)
        self.assertEqual(
            res_csr.status,
            STATUS_BLOCKED_G80_NTSCPAL_RESET_PERSISTENCE_ASYMMETRY_VIOLATION,
        )

        res_init = verify_ntscpal_persistence_and_gamma_assist_displaylut_guard(
            regional_default_system="NTSC",
            configured_ntsc_pal_system="PAL",
            reset_action=RESET_ACTION_INITIALIZE,
            observed_post_reset_system="PAL",
            selected_frame_rate="23.98p",
            selected_tc_format=TC_FORMAT_NDF,
        )
        self.assertFalse(res_init.valid)
        self.assertEqual(
            res_init.status,
            STATUS_BLOCKED_G80_NTSCPAL_RESET_PERSISTENCE_ASYMMETRY_VIOLATION,
        )

    def test_37_g80_accepts_all_4_official_ver702_gamma_assist_types(self) -> None:
        self.assertEqual(
            ALLOWED_FX3_702_GAMMA_ASSIST_TYPES,
            (
                GAMMA_ASSIST_TYPE_AUTO,
                GAMMA_ASSIST_TYPE_SLOG3_709,
                GAMMA_ASSIST_TYPE_HLG_BT2020,
                GAMMA_ASSIST_TYPE_HLG_709,
            ),
        )
        for gtype in (
            "Auto",
            "S-Log3->709(800%)",
            "HLG(BT.2020)",
            "HLG(709)",
            "S_LOG3_TO_709_800",
        ):
            res = verify_ntscpal_persistence_and_gamma_assist_displaylut_guard(
                log_shooting_mode=LOG_SHOOTING_OFF,
                gamma_assist_type=gtype,
                gamma_display_assist_menu_on=True,
                display_lut_on=False,
            )
            self.assertTrue(res.valid, gtype)
            self.assertTrue(res.effective_gamma_display_assist_on)
            self.assertEqual(res.active_preview_governor, "GAMMA_DISPLAY_ASSIST")

    def test_38_g80_strictly_blocks_slog2_gamma_assist_in_ver702(self) -> None:
        for forbidden in ("S-Log2->709(800%)", "S_LOG2", "S-Log2", "CINEMA_GAMMA"):
            res = verify_ntscpal_persistence_and_gamma_assist_displaylut_guard(
                gamma_assist_type=forbidden
            )
            self.assertFalse(res.valid, forbidden)
            self.assertEqual(
                res.status, STATUS_BLOCKED_G80_GAMMA_ASSIST_TYPE_OR_SLOG2_FORBIDDEN
            )

    def test_39_g80_log_shooting_modes_hard_lock_gamma_assist_off_and_use_display_lut(self) -> None:
        for log_mode in (
            LOG_SHOOTING_CINE_EI,
            LOG_SHOOTING_CINE_EI_QUICK,
            LOG_SHOOTING_FLEXIBLE_ISO,
        ):
            log_act, locked, eff_ga, eff_lut, gov = (
                resolve_fx3_gamma_assist_and_display_lut_split(
                    log_shooting_mode=log_mode,
                    gamma_display_assist_menu_on=True,
                    display_lut_on=False,
                )
            )
            self.assertTrue(log_act)
            self.assertTrue(locked)
            self.assertFalse(eff_ga)
            self.assertFalse(eff_lut)
            self.assertEqual(gov, "DISPLAY_LUT")

    def test_40_g80_blocks_claiming_gamma_assist_active_during_log_shooting(self) -> None:
        res = verify_ntscpal_persistence_and_gamma_assist_displaylut_guard(
            log_shooting_mode=LOG_SHOOTING_FLEXIBLE_ISO,
            claimed_gamma_assist_active_in_log_shooting=True,
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            res.status,
            STATUS_BLOCKED_G80_LOG_SHOOTING_GAMMA_ASSIST_OR_DISPLAY_LUT_SPLIT_VIOLATION,
        )

    def test_41_g80_blocks_claiming_display_lut_active_when_log_shooting_off(self) -> None:
        res = verify_ntscpal_persistence_and_gamma_assist_displaylut_guard(
            log_shooting_mode=LOG_SHOOTING_OFF,
            claimed_display_lut_active_outside_log=True,
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            res.status,
            STATUS_BLOCKED_G80_LOG_SHOOTING_GAMMA_ASSIST_OR_DISPLAY_LUT_SPLIT_VIOLATION,
        )

    def test_42_g80_blocks_external_hdmi_or_tv_gamma_assist_application(self) -> None:
        res = verify_ntscpal_persistence_and_gamma_assist_displaylut_guard(
            log_shooting_mode=LOG_SHOOTING_OFF,
            gamma_display_assist_menu_on=True,
            external_hdmi_gamma_assist_applied=True,
        )
        self.assertFalse(res.valid)
        self.assertFalse(res.builtin_lcd_only_scope)
        self.assertEqual(
            res.status, STATUS_BLOCKED_G80_EXTERNAL_HDMI_GAMMA_ASSIST_SCOPE_VIOLATION
        )

    def test_43_g80_rejects_malformed_enums_and_non_boolean_telemetry(self) -> None:
        self.assertEqual(ALLOWED_VIDEO_SYSTEMS, ("NTSC", "PAL"))
        self.assertEqual(
            ALLOWED_RESET_ACTIONS, ("NONE", "CAMERA_SETTINGS_RESET", "INITIALIZE")
        )
        self.assertEqual(
            ALLOWED_LOG_SHOOTING_MODES_G80,
            ("OFF", "CINE_EI", "CINE_EI_QUICK", "FLEXIBLE_ISO"),
        )
        res_sys = verify_ntscpal_persistence_and_gamma_assist_displaylut_guard(
            configured_ntsc_pal_system="SECAM"
        )
        self.assertFalse(res_sys.valid)
        self.assertEqual(res_sys.status, STATUS_BLOCKED_G80_TELEMETRY_INVALID)

        res_log = verify_ntscpal_persistence_and_gamma_assist_displaylut_guard(
            log_shooting_mode="RAW_LOG_UNKNOWN"
        )
        self.assertFalse(res_log.valid)
        self.assertEqual(res_log.status, STATUS_BLOCKED_G80_TELEMETRY_INVALID)

    def test_44_evaluate_g80_dual_mode_normal_and_clean_room(self) -> None:
        v_norm, r_norm = evaluate_g80_ntscpal_gammaassist_displaylut_guard()
        self.assertTrue(v_norm.passed)
        self.assertEqual(v_norm.gate_id, G80_GATE_ID)
        self.assertEqual(r_norm.status, STATUS_VERIFIED_G80)
        self.assertEqual(r_norm.raw_firmware_bytes_leaked, 0)

        v_clean, r_clean = evaluate_g80_ntscpal_gammaassist_displaylut_guard(
            force_clean_room=True
        )
        self.assertTrue(v_clean.passed)
        self.assertEqual(r_clean.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_45_evaluate_g80_blocks_persistent_emmc_write_request(self) -> None:
        verdict, res = evaluate_g80_ntscpal_gammaassist_displaylut_guard(
            force_clean_room=True, request_persistent_emmc_writes=True
        )
        self.assertFalse(verdict.passed)
        self.assertFalse(res.valid)
        self.assertIn(STATUS_BLOCKED_PERSISTENT_EMMC_WRITE, res.violation_codes)

    # ------------------------------------------------------------------
    # Section D: Unified 80/80 Milestone Master Safety Preflight (10 tests)
    # ------------------------------------------------------------------

    def test_46_master_80gate_offline_default_verifies_77_of_80(self) -> None:
        r = self.offline_80
        self.assertEqual(
            r.schema, REALHW_PIXELMAP_NTSCPAL_GAMMAASSIST_DISPLAYLUT_80GATE_SCHEMA
        )
        self.assertEqual(r.status, "VERIFIED_77_OF_80_AWAITING_PHYSICAL_TIER0")
        self.assertEqual(len(r.gates), 80)
        self.assertEqual(r.summary["total_gates"], 80)
        self.assertEqual(r.summary["verified_gates"], 77)
        self.assertEqual(r.summary["blocked_or_pending_gates"], 3)
        self.assertEqual(r.summary["g01_to_g12_verified"], 9)
        self.assertEqual(r.summary["g13_to_g78_verified"], 66)
        self.assertEqual(r.summary["g79_to_g80_verified"], 2)
        self.assertTrue(r.offline_77_gates_verified)
        self.assertFalse(r.all_80_gates_verified)
        self.assertTrue(r.g13_to_g80_all_passed)
        self.assertTrue(r.g79_to_g80_all_passed)
        self.assertFalse(r.overall_ready_for_hardware_attach)

    def test_47_master_80gate_simulate_bench_dry_run_verifies_80_of_80(self) -> None:
        r = self.dryrun_80
        self.assertEqual(
            r.status, "VERIFIED_ALL_80_GATES_DRY_RUN_SIMULATED_BACKUP"
        )
        self.assertEqual(r.summary["verified_gates"], 80)
        self.assertEqual(r.summary["blocked_or_pending_gates"], 0)
        self.assertTrue(r.all_80_gates_verified)
        self.assertTrue(r.offline_77_gates_verified)
        self.assertTrue(r.dry_run_rehearsal_only)
        self.assertFalse(r.overall_ready_for_hardware_attach)

    def test_48_master_80gate_clean_room_offline_and_dry_run_parity(self) -> None:
        self.assertEqual(self.clean_offline_80.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(self.clean_offline_80.summary["verified_gates"], 77)
        self.assertTrue(self.clean_offline_80.offline_77_gates_verified)

        self.assertEqual(self.clean_dryrun_80.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(self.clean_dryrun_80.summary["verified_gates"], 80)
        self.assertTrue(self.clean_dryrun_80.all_80_gates_verified)

    def test_49_master_80gate_hard_safety_redlines_locked_in_all_modes(self) -> None:
        for r in (
            self.offline_80,
            self.dryrun_80,
            self.clean_offline_80,
            self.clean_dryrun_80,
        ):
            self.assertFalse(r.overall_ready_for_hardware_attach)
            self.assertFalse(r.hardware_live_attachment_authorized)
            self.assertFalse(r.el3_payload_transmit_authorized)
            self.assertFalse(r.spi_nor_write_authorized)
            self.assertFalse(r.persistent_emmc_writes_authorized)
            self.assertFalse(r.persistent_write_release)
            self.assertFalse(r.physical_flash_auto_exec_authorized)
            self.assertTrue(r.agent_auto_flash_blocked)
            self.assertEqual(r.usb_packets_transmitted, 0)
            self.assertEqual(r.physical_usb_packets_emitted, 0)
            self.assertEqual(r.raw_firmware_bytes_leaked, 0)

    def test_50_master_80gate_propagates_g79_failure(self) -> None:
        r = evaluate_80gate_preflight(
            force_clean_room=True,
            simulate_bench_dry_run=True,
            master_78_override=self.clean_dryrun_78,
            pixelmap_cnflasha_kwargs={"battery_soc_pct": 10.0},
        )
        self.assertFalse(r.all_80_gates_verified)
        self.assertFalse(r.g79_to_g80_all_passed)
        self.assertEqual(r.summary["verified_gates"], 79)
        self.assertEqual(
            r.status, STATUS_BLOCKED_G79_MANUAL_PIXEL_MAPPING_LOW_BATTERY_LOCKOUT
        )

    def test_51_master_80gate_propagates_g80_failure(self) -> None:
        r = evaluate_80gate_preflight(
            force_clean_room=True,
            simulate_bench_dry_run=True,
            master_78_override=self.clean_dryrun_78,
            ntscpal_gammaassist_kwargs={"external_hdmi_gamma_assist_applied": True},
        )
        self.assertFalse(r.all_80_gates_verified)
        self.assertFalse(r.g79_to_g80_all_passed)
        self.assertEqual(r.summary["verified_gates"], 79)
        self.assertEqual(
            r.status, STATUS_BLOCKED_G80_EXTERNAL_HDMI_GAMMA_ASSIST_SCOPE_VIOLATION
        )

    def test_52_master_80gate_blocks_persistent_emmc_write_request(self) -> None:
        r = evaluate_80gate_preflight(
            force_clean_room=True,
            simulate_bench_dry_run=True,
            master_78_override=self.clean_dryrun_78,
            request_persistent_emmc_writes=True,
        )
        self.assertEqual(r.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        self.assertFalse(r.all_80_gates_verified)
        self.assertFalse(r.offline_77_gates_verified)
        self.assertFalse(r.h0_h1_trial_entry_allowed)

    def test_53_master_80gate_gate_ordering_g01_through_g80(self) -> None:
        ids = [g["gate_id"] for g in self.offline_80.gates]
        self.assertEqual(len(ids), 80)
        self.assertEqual(ids[-2], G79_GATE_ID)
        self.assertEqual(ids[-1], G80_GATE_ID)

    def test_54_backward_compatibility_across_58_to_78_gate_evaluators(self) -> None:
        self.assertEqual(self.clean_dryrun_78.summary["verified_gates"], 78)
        self.assertEqual(self.clean_offline_78.summary["verified_gates"], 75)
        for fn_name, expected_total in (
            ("evaluate_58gate_preflight", 58),
            ("evaluate_68gate_preflight", 68),
            ("evaluate_76gate_preflight", 76),
            ("evaluate_78gate_preflight", 78),
        ):
            fn = getattr(fx3_safety, fn_name)
            self.assertTrue(callable(fn), fn_name)
        m76 = self.clean_dryrun_78.master_76_report
        self.assertEqual(m76["summary"]["total_gates"], 76)
        self.assertEqual(m76["summary"]["verified_gates"], 76)

    def test_55_serialized_80gate_report_json_has_zero_raw_bytes(self) -> None:
        payload = json.dumps(self.dryrun_80.to_dict())
        parsed = json.loads(payload)
        self.assertEqual(parsed["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(parsed["summary"]["verified_gates"], 80)

    # ------------------------------------------------------------------
    # Section E: CLI Subcommands & Module Entrypoint (5 tests)
    # ------------------------------------------------------------------

    def test_56_cli_verify_g79_pixelmap_cnflasha_text_and_json(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cli_main(["verify-g79-pixelmap-cnflasha", "--force-clean-room"])
        self.assertEqual(rc, 0)
        self.assertIn("status=VERIFIED_PIXEL_MAPPING_REBOOT_LOWBATT_LOCK", buf.getvalue())

        jbuf = io.StringIO()
        with contextlib.redirect_stdout(jbuf):
            rc_j = cli_main(
                ["verify-g79-pixelmap-cnflasha", "--force-clean-room", "--json"]
            )
        self.assertEqual(rc_j, 0)
        data = json.loads(jbuf.getvalue())
        self.assertTrue(data["valid"])
        self.assertFalse(data["persistent_emmc_writes_authorized"])

    def test_57_cli_verify_g80_ntscpal_gammaassist_displaylut_text_and_json(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cli_main(
                ["verify-g80-ntscpal-gammaassist-displaylut", "--force-clean-room"]
            )
        self.assertEqual(rc, 0)
        self.assertIn("status=VERIFIED_NTSCPAL_RESET_PERSISTENCE", buf.getvalue())

        jbuf = io.StringIO()
        with contextlib.redirect_stdout(jbuf):
            rc_j = cli_main(
                [
                    "verify-g80-ntscpal-gammaassist-displaylut",
                    "--force-clean-room",
                    "--json",
                ]
            )
        self.assertEqual(rc_j, 0)
        data = json.loads(jbuf.getvalue())
        self.assertTrue(data["valid"])
        self.assertEqual(
            data["ntscpal_gammaassist_displaylut_guard"]["active_preview_governor"],
            "DISPLAY_LUT",
        )

    def test_58_cli_verify_80_gates_offline_text_mode(self) -> None:
        buf = io.StringIO()
        with mock.patch(
            "fx3_safety.__main__.evaluate_80gate_preflight",
            return_value=self.clean_offline_80,
        ):
            with contextlib.redirect_stdout(buf):
                rc = cli_main(["verify-80-gates", "--force-clean-room"])
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("verified=77/80", out)
        self.assertIn("overall_ready_for_hardware_attach=False", out)

    def test_59_cli_verify_80_gates_dry_run_json_mode(self) -> None:
        buf = io.StringIO()
        with mock.patch(
            "fx3_safety.__main__.evaluate_80gate_preflight",
            return_value=self.clean_dryrun_80,
        ):
            with contextlib.redirect_stdout(buf):
                rc = cli_main(
                    [
                        "verify-80-gates",
                        "--force-clean-room",
                        "--simulate-bench-dry-run",
                        "--json",
                    ]
                )
        self.assertEqual(rc, 0)
        parsed = json.loads(buf.getvalue())
        self.assertEqual(parsed["summary"]["verified_gates"], 80)
        self.assertTrue(parsed["all_80_gates_verified"])

    def test_60_module_main_entrypoint_offline_and_dry_run(self) -> None:
        buf_off = io.StringIO()
        with mock.patch(
            "fx3_safety.realhw_pixelmap_ntscpal_gammaassist_displaylut_and_80gate_guard.evaluate_80gate_preflight",
            return_value=self.clean_offline_80,
        ):
            with contextlib.redirect_stdout(buf_off):
                rc_off = module_main(["--force-clean-room"])
        self.assertEqual(rc_off, 0)
        self.assertIn("verified=77/80", buf_off.getvalue())

        buf_dry = io.StringIO()
        with mock.patch(
            "fx3_safety.realhw_pixelmap_ntscpal_gammaassist_displaylut_and_80gate_guard.evaluate_80gate_preflight",
            return_value=self.clean_dryrun_80,
        ):
            with contextlib.redirect_stdout(buf_dry):
                rc_dry = module_main(
                    ["--force-clean-room", "--simulate-bench-dry-run", "--json"]
                )
        self.assertEqual(rc_dry, 0)
        self.assertTrue(json.loads(buf_dry.getvalue())["all_80_gates_verified"])


if __name__ == "__main__":
    unittest.main()
