"""Phase 259 Dual-Mode Unit Tests (68 tests, < 4s runtime) for
`fx3_safety.realhw_auto_slow_shutter_hdmi_reccontrol_breathing_and_102gate_guard`:

- Gate `G101`: `ILME-FX3` (`Ver. 7.02`) `[Auto Slow Shutter]` (`On` default / `Off`,
  resettable by `[Camera Settings Reset]`), exact 6 Sony non-function lockouts
  (`S&Q`, `Shutter Priority`, `Manual Exposure`, `[ISO] != [ISO AUTO]`,
  `[Flexible Exp. Mode]` with manual shutter, and `[Log Shooting]` = `Cine EI Quick`
  / `Cine EI`), strict 320-state hardware disjointness with `Ver. 7.02`
  `[Shutter Mode] = [Angle]`, AND `[Lens Compensation] -> [Breathing Comp.]`
  (`Off` default / `On`, movie-only compliant E-mount crop, locked out during
  `4264x2408` `RAW Output` and `S&Q` `239.76p`/`200p`).
- Gate `G102`: `ILME-FX3` (`Ver. 7.02`) `[HDMI Output Settings]` surviving
  `[Camera Settings Reset]` & `[Reset Network Set.]` (cleared only by `[Initialize]`),
  `[REC Control]` mandatory prerequisite `[Time Code Output] = [On]`,
  `[4ch Audio Output]` (`CH1/CH2` -> `CH1=L/CH2=R` vs `CH3/CH4` -> `CH3=L/CH4=R`),
  and `[Rec. Media dur HDMI Output]` Slot-1/Slot-2 + `[Proxy Recording]` inhibition
  protecting Slot-1 Tier-0 recovery vault.
- Unified `102`-Gate Master Safety Preflight (`evaluate_102gate_preflight` /
  `verify-102-gates`): `99/102` offline and `102/102` in `--simulate-bench-dry-run`
  with all hardware write/live-attach redlines hard-locked `False`.
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
from fx3_safety.realhw_auto_slow_shutter_hdmi_reccontrol_breathing_and_102gate_guard import (
    ALLOWED_AUTO_SLOW_SHUTTER_SETTINGS_G101,
    ALLOWED_BREATHING_COMP_SETTINGS_G101,
    ALLOWED_CAPTURE_DOMAINS_G101,
    ALLOWED_EXPOSURE_CTRL_TYPES_G101,
    ALLOWED_FLEX_EXP_SHUTTER_MODES_G101,
    ALLOWED_HDMI_4CH_AUDIO_SETTINGS_G102,
    ALLOWED_HDMI_AUDIO_OUTPUT_PAIRS_G102,
    ALLOWED_HDMI_REC_CONTROL_SETTINGS_G102,
    ALLOWED_HDMI_REC_MEDIA_SETTINGS_G102,
    ALLOWED_HDMI_TC_OUTPUT_SETTINGS_G102,
    ALLOWED_LOG_SHOOTING_MODES_G101,
    ALLOWED_MOVIE_SHOOT_MODES_G101,
    ALLOWED_RESET_ACTIONS_PHASE259,
    ALLOWED_SHUTTER_MODES_G101,
    AUTO_SLOW_SHUTTER_FACTORY_DEFAULT_G101,
    AUTO_SLOW_SHUTTER_MENU_PATH_G101,
    AUTO_SLOW_SHUTTER_OFF_G101,
    AUTO_SLOW_SHUTTER_ON_G101,
    AUTO_SLOW_SHUTTER_SIX_LOCKOUT_CONDITIONS_G101,
    BREATHING_COMP_FACTORY_DEFAULT_G101,
    BREATHING_COMP_LOCKED_SQ_HIGH_FPS_G101,
    BREATHING_COMP_MENU_PATH_G101,
    BREATHING_COMP_OFF_G101,
    BREATHING_COMP_ON_G101,
    BREATHING_COMP_RAW_RESOLUTION_G101,
    CAPTURE_DOMAIN_MOVIE_G101,
    CAPTURE_DOMAIN_STILL_G101,
    DONOR_CHECK_MAX_SECONDS_PHASE259,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    EXPOSURE_CTRL_FLEXIBLE_EXP_MODE_G101,
    EXPOSURE_CTRL_PASM_MODE_G101,
    FLEX_EXP_SHUTTER_AUTO_G101,
    FLEX_EXP_SHUTTER_MANUAL_G101,
    FX3_BREATHING_COMP_MIN_FW_TUPLE_G101,
    FX3_DEFAULT_FW_VERSION_PHASE259,
    FX3_HELP_GUIDE_CODE_PHASE259,
    FX3_MIN_SUPPORTED_FW_TUPLE_PHASE259,
    FX3_MODEL_ID,
    FX3_MODEL_NAME,
    FX3_SHUTTER_ANGLE_MIN_FW_TUPLE_G101,
    FX6_MODEL_NAME,
    G101,
    G101_GATE_CODE,
    G101_GATE_ID,
    G102,
    G102_GATE_CODE,
    G102_GATE_ID,
    GATE_G101_AUTO_SLOW_SHUTTER_6LOCK_ANGLE_DISJOINT_AND_BREATHING_COMP_GUARD,
    GATE_G102_HDMI_REC_CONTROL_TCOUT_4CHAUDIO_AND_SLOT1_REC_MEDIA_VAULT_GUARD,
    HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    HDMI_4CH_AUDIO_CH1_CH2_G102,
    HDMI_4CH_AUDIO_CH3_CH4_G102,
    HDMI_4CH_AUDIO_FACTORY_DEFAULT_G102,
    HDMI_AUDIO_PAIR_CH1_L_CH2_R_G102,
    HDMI_AUDIO_PAIR_CH3_L_CH4_R_G102,
    HDMI_OUTPUT_FACTORY_DEFAULTS_G102,
    HDMI_OUTPUT_SETTINGS_MENU_PATH_G102,
    HDMI_REC_CONTROL_FACTORY_DEFAULT_G102,
    HDMI_REC_CONTROL_OFF_G102,
    HDMI_REC_CONTROL_ON_G102,
    HDMI_REC_MEDIA_FACTORY_DEFAULT_G102,
    HDMI_REC_MEDIA_OFF_G102,
    HDMI_REC_MEDIA_ON_G102,
    HDMI_REC_MEDIA_TIER0_BENCH_SAFE_DEFAULT_G102,
    HDMI_TC_OUTPUT_FACTORY_DEFAULT_G102,
    HDMI_TC_OUTPUT_OFF_G102,
    HDMI_TC_OUTPUT_ON_G102,
    HUMAN_HARDWARE_ATTACH_TOKEN,
    ISO_AUTO_TOKEN_G101,
    LOCKOUT_1_SQ_MODE_G101,
    LOCKOUT_2_SHUTTER_PRIORITY_G101,
    LOCKOUT_3_MANUAL_EXPOSURE_G101,
    LOCKOUT_4_ISO_NOT_AUTO_G101,
    LOCKOUT_5_FLEX_EXP_MANUAL_SHUTTER_G101,
    LOCKOUT_6_LOG_CINE_EI_G101,
    LOG_SHOOTING_CINE_EI_G101,
    LOG_SHOOTING_CINE_EI_QUICK_G101,
    LOG_SHOOTING_FLEXIBLE_ISO_G101,
    LOG_SHOOTING_OFF_G101,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED,
    PHYSICAL_USB_PACKETS_EMITTED,
    PINNED_PHASE259_DONOR_SPECS,
    RAW_FIRMWARE_BYTES_LEAKED,
    REALHW_AUTO_SLOW_SHUTTER_HDMI_RECCONTROL_BREATHING_102GATE_SCHEMA,
    REALHW_AUTO_SLOW_SHUTTER_HDMI_RECCONTROL_BREATHING_102GATE_VERSION,
    RESET_ACTION_CAMERA_SETTINGS_RESET,
    RESET_ACTION_INITIALIZE,
    RESET_ACTION_NONE,
    RESET_ACTION_RESET_NETWORK_SET_PHASE259,
    SHOOT_MODE_APERTURE_PRIORITY_G101,
    SHOOT_MODE_MANUAL_EXPOSURE_G101,
    SHOOT_MODE_PROGRAM_AUTO_G101,
    SHOOT_MODE_SHUTTER_PRIORITY_G101,
    SHOOT_MODE_SQ_G101,
    SHUTTER_MODE_ANGLE_G101,
    SHUTTER_MODE_MENU_PATH_G101,
    SHUTTER_MODE_SPEED_G101,
    SPI_NOR_WRITE_AUTHORIZED,
    STATUS_BLOCKED_G101_AUTO_SLOW_SHUTTER_LOCKOUT_BYPASS_VIOLATION,
    STATUS_BLOCKED_G101_BREATHING_COMP_RAW_OR_240P_BYPASS_VIOLATION,
    STATUS_BLOCKED_G101_BREATHING_COMP_STILL_OR_LENS_VIOLATION,
    STATUS_BLOCKED_G101_RESET_SCOPE_PERSISTENCE_VIOLATION,
    STATUS_BLOCKED_G101_SHUTTER_ANGLE_OVERLAP_VIOLATION,
    STATUS_BLOCKED_G101_TELEMETRY_INVALID,
    STATUS_BLOCKED_G102_HDMI_4CH_AUDIO_ROUTING_MISMATCH,
    STATUS_BLOCKED_G102_HDMI_REC_CTRL_WITHOUT_TCOUT_VIOLATION,
    STATUS_BLOCKED_G102_HDMI_SETUP_RESET_PERSISTENCE_VIOLATION,
    STATUS_BLOCKED_G102_SLOT1_HDMI_REC_MEDIA_VAULT_VIOLATION,
    STATUS_BLOCKED_G102_TELEMETRY_INVALID,
    STATUS_BLOCKED_PERSISTENT_EMMC_WRITE,
    STATUS_BLOCKED_PHASE259_DONOR_INTEGRITY,
    STATUS_VERIFIED_G101,
    STATUS_VERIFIED_G102,
    USB_PACKETS_TRANSMITTED,
    _norm_4ch_audio_setting_g102,
    _norm_capture_domain_g101,
    _norm_exposure_ctrl_type_g101,
    _norm_flex_exp_shutter_mode_g101,
    _norm_hdmi_audio_pair_g102,
    _norm_iso_setting_g101,
    _norm_log_shooting_mode_g101,
    _norm_on_off_phase259,
    _norm_reset_action_phase259,
    _norm_shoot_mode_g101,
    _norm_shutter_mode_g101,
    _read_file_o_rdonly,
    audit_phase259_donor_contracts,
    compute_auto_slow_shutter_angle_disjointness_matrix,
    evaluate_102_master_safety_gates,
    evaluate_102gate_preflight,
    evaluate_g101_auto_slow_shutter_and_breathing_comp_guard,
    evaluate_g102_hdmi_reccontrol_tcout_4chaudio_guard,
    main as module_main,
    resolve_fx3_auto_slow_shutter_and_breathing_comp_state,
    resolve_fx3_hdmi_reccontrol_tcout_4chaudio_state,
    run_102_gate_preflight,
    verify_auto_slow_shutter_and_breathing_comp_guard,
    verify_hdmi_reccontrol_tcout_4chaudio_and_vault_guard,
)


class TestPhase259AutoSlowShutterHdmiRecControlBreathing102GateGuard(unittest.TestCase):
    """68 fast dual-mode tests covering Gates G101, G102, and unified 102-Gate preflight (< 4s)."""

    @classmethod
    def setUpClass(cls) -> None:
        # Cache upstream 100-gate and 102-gate preflight evaluations once so all 68
        # tests execute well under < 4s in both LOCAL_DONOR_O_RDONLY and
        # FX3_FX6_FORCE_CLEAN_ROOM=1 modes.
        cls.active_offline_100 = fx3_safety.evaluate_100gate_preflight()
        cls.active_offline_102 = evaluate_102gate_preflight(
            master_100_override=cls.active_offline_100
        )
        if cls.active_offline_100.clean_room_forced:
            cls.clean_offline_100 = cls.active_offline_100
        else:
            with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
                cls.clean_offline_100 = fx3_safety.evaluate_100gate_preflight(
                    force_clean_room=True
                )
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            cls.clean_dryrun_100 = fx3_safety.evaluate_100gate_preflight(
                force_clean_room=True, dry_run_simulated=True
            )
            cls.clean_offline_102 = evaluate_102gate_preflight(
                force_clean_room=True, master_100_override=cls.clean_offline_100
            )
            cls.clean_dryrun_102 = evaluate_102gate_preflight(
                force_clean_room=True,
                simulate_bench_dry_run=True,
                master_100_override=cls.clean_dryrun_100,
            )
        cls.active_dryrun_102 = evaluate_102gate_preflight(
            simulate_bench_dry_run=True,
            master_100_override=cls.clean_dryrun_100,
        )

    # ------------------------------------------------------------------
    # Section A: Schema, Exports & O_RDONLY / Clean-Room Donor Audit (01..12)
    # ------------------------------------------------------------------

    def test_01_schema_version_gate_ids_and_redline_constants(self) -> None:
        self.assertEqual(
            REALHW_AUTO_SLOW_SHUTTER_HDMI_RECCONTROL_BREATHING_102GATE_SCHEMA,
            "realhw_auto_slow_shutter_hdmi_reccontrol_breathing_and_102gate_guard_v1",
        )
        self.assertEqual(
            REALHW_AUTO_SLOW_SHUTTER_HDMI_RECCONTROL_BREATHING_102GATE_VERSION, "1.0.0"
        )
        self.assertEqual(G101, G101_GATE_ID)
        self.assertEqual(G102, G102_GATE_ID)
        self.assertEqual(
            GATE_G101_AUTO_SLOW_SHUTTER_6LOCK_ANGLE_DISJOINT_AND_BREATHING_COMP_GUARD,
            G101_GATE_CODE,
        )
        self.assertEqual(
            GATE_G102_HDMI_REC_CONTROL_TCOUT_4CHAUDIO_AND_SLOT1_REC_MEDIA_VAULT_GUARD,
            G102_GATE_CODE,
        )
        self.assertEqual(FX3_MODEL_NAME, "ILME-FX3")
        self.assertEqual(FX3_MODEL_ID, 0x91030080)
        self.assertEqual(FX6_MODEL_NAME, "ILME-FX6")
        self.assertEqual(FX3_DEFAULT_FW_VERSION_PHASE259, "7.02")
        self.assertEqual(FX3_HELP_GUIDE_CODE_PHASE259, "ilc/2210")
        self.assertFalse(HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        self.assertFalse(HUMAN_HARDWARE_ATTACH_TOKEN)
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(PERSISTENT_WRITE_RELEASE)
        self.assertFalse(SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        self.assertFalse(PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED)
        self.assertEqual(USB_PACKETS_TRANSMITTED, 0)
        self.assertEqual(PHYSICAL_USB_PACKETS_EMITTED, 0)
        self.assertEqual(RAW_FIRMWARE_BYTES_LEAKED, 0)

    def test_02_top_level_package_exports_all_phase259_symbols_unshadowed(self) -> None:
        mod = fx3_safety.realhw_auto_slow_shutter_hdmi_reccontrol_breathing_and_102gate_guard
        self.assertEqual(fx3_safety.__all__.count(mod.__name__.split(".")[-1]), 1)
        for sym in (
            "G101",
            "G102",
            "G101_GATE_ID",
            "G102_GATE_ID",
            "Master102GateReport",
            "evaluate_102gate_preflight",
            "run_102_gate_preflight",
            "evaluate_102_master_safety_gates",
            "verify_auto_slow_shutter_and_breathing_comp_guard",
            "verify_hdmi_reccontrol_tcout_4chaudio_and_vault_guard",
        ):
            self.assertEqual(fx3_safety.__all__.count(sym), 1)
            self.assertIs(getattr(fx3_safety, sym), getattr(mod, sym))

    def test_03_pinned_phase259_donor_specs_cover_fx3_and_fx6_contracts(self) -> None:
        self.assertEqual(len(PINNED_PHASE259_DONOR_SPECS), 6)
        bodies = {spec[0] for spec in PINNED_PHASE259_DONOR_SPECS.values()}
        self.assertEqual(bodies, {"FX3", "FX6"})
        self.assertLessEqual(DONOR_CHECK_MAX_SECONDS_PHASE259, 0.10)

    def test_04_donor_audit_active_mode_within_100ms_and_zero_leaked_bytes(
        self,
    ) -> None:
        audit = audit_phase259_donor_contracts()
        self.assertTrue(audit.valid)
        self.assertTrue(audit.within_budget_100ms)
        self.assertLess(audit.elapsed_seconds, 0.10)
        self.assertEqual(audit.raw_firmware_bytes_leaked, 0)
        self.assertTrue(audit.fx3_contracts_verified)
        self.assertTrue(audit.fx6_contracts_verified)
        self.assertIn(
            audit.verification_mode, ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC")
        )

    def test_05_donor_audit_force_clean_room_synthetic_parity(self) -> None:
        audit = audit_phase259_donor_contracts(force_clean_room=True)
        self.assertTrue(audit.valid)
        self.assertEqual(audit.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(audit.access_mode, "SYNTHETIC_CLEAN_ROOM")
        self.assertEqual(audit.files_inspected, 0)
        self.assertEqual(len(audit.checked_markers), 6)
        self.assertEqual(audit.missing_markers, ())

    def test_06_donor_audit_env_force_clean_room_toggle(self) -> None:
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            audit = audit_phase259_donor_contracts()
            self.assertTrue(audit.valid)
            self.assertEqual(audit.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_07_donor_audit_missing_work_root_falls_back_to_clean_room(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            audit = audit_phase259_donor_contracts(
                work_root=Path(tmp) / "nonexistent", force_clean_room=False
            )
            self.assertTrue(audit.valid)
            self.assertEqual(audit.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_08_donor_audit_corrupted_sha256_blocks_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for _k, (_body, rel, _sz, _sha, markers, _lbl) in (
                PINNED_PHASE259_DONOR_SPECS.items()
            ):
                fp = root / rel
                fp.parent.mkdir(parents=True, exist_ok=True)
                fp.write_bytes(b"".join(markers) + b"corrupt")
            audit = audit_phase259_donor_contracts(
                work_root=root, force_clean_room=False
            )
            self.assertFalse(audit.valid)
            self.assertEqual(audit.status, STATUS_BLOCKED_PHASE259_DONOR_INTEGRITY)

    def test_09_donor_audit_budget_exceeded_blocks_fail_closed(self) -> None:
        audit = audit_phase259_donor_contracts(
            force_clean_room=True, max_budget_seconds=0.0
        )
        self.assertFalse(audit.valid)
        self.assertEqual(audit.status, STATUS_BLOCKED_PHASE259_DONOR_INTEGRITY)

    def test_10_read_file_o_rdonly_strictly_uses_os_o_rdonly_flag(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fp = Path(tmp) / "probe.bin"
            fp.write_bytes(b"FX3_WAVE41_PROBE")
            orig_open = os.open
            captured_flags = []

            def spy_open(path_arg: str, flags: int, *args: object) -> int:
                captured_flags.append(flags)
                return orig_open(path_arg, flags, *args)  # type: ignore[arg-type]

            with mock.patch("os.open", side_effect=spy_open):
                data = _read_file_o_rdonly(fp)
            self.assertEqual(data, b"FX3_WAVE41_PROBE")
            self.assertEqual(len(captured_flags), 1)
            self.assertEqual(captured_flags[0] & 3, os.O_RDONLY)

    def test_11_normalizers_handle_brackets_case_and_reject_invalid_tokens(self) -> None:
        self.assertEqual(_norm_reset_action_phase259("[Camera Settings Reset]"), RESET_ACTION_CAMERA_SETTINGS_RESET)
        self.assertEqual(_norm_reset_action_phase259("Reset Network Set."), RESET_ACTION_RESET_NETWORK_SET_PHASE259)
        self.assertIsNone(_norm_reset_action_phase259("Factory Format"))
        self.assertEqual(_norm_on_off_phase259("[On]"), "On")
        self.assertEqual(_norm_on_off_phase259("off"), "Off")
        self.assertIsNone(_norm_on_off_phase259("Maybe"))
        self.assertEqual(_norm_shoot_mode_g101("S&Q"), SHOOT_MODE_SQ_G101)
        self.assertEqual(_norm_shoot_mode_g101("S"), SHOOT_MODE_SHUTTER_PRIORITY_G101)
        self.assertEqual(_norm_shoot_mode_g101("M"), SHOOT_MODE_MANUAL_EXPOSURE_G101)
        self.assertEqual(_norm_exposure_ctrl_type_g101("[Flexible Exp. Mode]"), EXPOSURE_CTRL_FLEXIBLE_EXP_MODE_G101)
        self.assertEqual(_norm_flex_exp_shutter_mode_g101("[Manual]"), FLEX_EXP_SHUTTER_MANUAL_G101)
        self.assertEqual(_norm_iso_setting_g101("[ISO AUTO]"), ISO_AUTO_TOKEN_G101)
        self.assertEqual(_norm_iso_setting_g101("800"), "ISO 800")
        self.assertIsNone(_norm_iso_setting_g101("ISO 10"))
        self.assertEqual(_norm_log_shooting_mode_g101("[Cine EI Quick]"), LOG_SHOOTING_CINE_EI_QUICK_G101)
        self.assertEqual(_norm_shutter_mode_g101("[Angle]"), SHUTTER_MODE_ANGLE_G101)
        self.assertEqual(_norm_capture_domain_g101("Still"), CAPTURE_DOMAIN_STILL_G101)
        self.assertEqual(_norm_4ch_audio_setting_g102("[CH3/CH4]"), HDMI_4CH_AUDIO_CH3_CH4_G102)
        self.assertEqual(_norm_hdmi_audio_pair_g102("CH3=L/CH4=R"), HDMI_AUDIO_PAIR_CH3_L_CH4_R_G102)

    def test_12_catalog_tuples_match_sony_ilc2210_help_guide_exact_values(self) -> None:
        self.assertEqual(ALLOWED_AUTO_SLOW_SHUTTER_SETTINGS_G101, ("On", "Off"))
        self.assertEqual(ALLOWED_BREATHING_COMP_SETTINGS_G101, ("Off", "On"))
        self.assertEqual(ALLOWED_CAPTURE_DOMAINS_G101, ("Movie", "Still"))
        self.assertEqual(ALLOWED_EXPOSURE_CTRL_TYPES_G101, ("P/A/S/M Mode", "Flexible Exp. Mode"))
        self.assertEqual(ALLOWED_FLEX_EXP_SHUTTER_MODES_G101, ("Auto", "Manual"))
        self.assertEqual(ALLOWED_SHUTTER_MODES_G101, ("Speed", "Angle"))
        self.assertEqual(
            ALLOWED_LOG_SHOOTING_MODES_G101,
            ("Off", "Flexible ISO", "Cine EI Quick", "Cine EI"),
        )
        self.assertEqual(
            ALLOWED_MOVIE_SHOOT_MODES_G101,
            ("Program Auto", "Aperture Priority", "Shutter Priority", "Manual Exposure", "S&Q"),
        )
        self.assertEqual(
            ALLOWED_RESET_ACTIONS_PHASE259,
            ("NONE", "Camera Settings Reset", "Reset Network Set.", "Initialize"),
        )
        self.assertEqual(ALLOWED_HDMI_TC_OUTPUT_SETTINGS_G102, ("Off", "On"))
        self.assertEqual(ALLOWED_HDMI_REC_CONTROL_SETTINGS_G102, ("Off", "On"))
        self.assertEqual(ALLOWED_HDMI_4CH_AUDIO_SETTINGS_G102, ("CH1/CH2", "CH3/CH4"))
        self.assertEqual(
            ALLOWED_HDMI_AUDIO_OUTPUT_PAIRS_G102, ("CH1=L/CH2=R", "CH3=L/CH4=R")
        )
        self.assertEqual(ALLOWED_HDMI_REC_MEDIA_SETTINGS_G102, ("On", "Off"))
        self.assertEqual(FX3_MIN_SUPPORTED_FW_TUPLE_PHASE259, (1, 0))
        self.assertEqual(FX3_BREATHING_COMP_MIN_FW_TUPLE_G101, (3, 0))
        self.assertEqual(FX3_SHUTTER_ANGLE_MIN_FW_TUPLE_G101, (6, 0))


    # ------------------------------------------------------------------
    # Section B: Gate G101 — Auto Slow Shutter (6 Lockouts + Angle Disjoint)
    #            & Lens Compensation -> Breathing Comp. Guard (13..34)
    # ------------------------------------------------------------------

    def test_13_g101_default_program_auto_iso_auto_passes_cleanly(self) -> None:
        res = verify_auto_slow_shutter_and_breathing_comp_guard()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_VERIFIED_G101)
        self.assertEqual(res.auto_slow_shutter_menu_path, AUTO_SLOW_SHUTTER_MENU_PATH_G101)
        self.assertEqual(res.auto_slow_shutter_factory_default, AUTO_SLOW_SHUTTER_ON_G101)
        self.assertEqual(res.effective_post_reset_auto_slow_shutter, AUTO_SLOW_SHUTTER_ON_G101)
        self.assertEqual(res.active_auto_slow_shutter_lockouts, ())
        self.assertFalse(res.auto_slow_shutter_hardware_locked_out)
        self.assertTrue(res.auto_slow_shutter_effective_active)
        self.assertEqual(res.auto_slow_shutter_lockout_bypass_events, 0)
        self.assertEqual(res.auto_slow_shutter_angle_overlap_events, 0)
        self.assertEqual(res.breathing_comp_raw_or_240p_bypass_events, 0)

    def test_14_g101_auto_slow_shutter_off_disables_function_with_zero_lockouts(self) -> None:
        res = verify_auto_slow_shutter_and_breathing_comp_guard(
            pre_reset_auto_slow_shutter=AUTO_SLOW_SHUTTER_OFF_G101,
            claimed_auto_slow_shutter_active=False,
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.effective_post_reset_auto_slow_shutter, AUTO_SLOW_SHUTTER_OFF_G101)
        self.assertFalse(res.auto_slow_shutter_effective_active)

    def test_15_g101_reset_scope_camera_settings_reset_and_initialize_vs_network_reset(
        self,
    ) -> None:
        # Camera Settings Reset restores Auto Slow Shutter -> On and Breathing Comp. -> Off
        r_cam = verify_auto_slow_shutter_and_breathing_comp_guard(
            pre_reset_auto_slow_shutter=AUTO_SLOW_SHUTTER_OFF_G101,
            pre_reset_breathing_comp=BREATHING_COMP_ON_G101,
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
            claimed_post_reset_auto_slow_shutter=AUTO_SLOW_SHUTTER_ON_G101,
            claimed_post_reset_breathing_comp=BREATHING_COMP_OFF_G101,
        )
        self.assertTrue(r_cam.valid)
        self.assertTrue(r_cam.auto_slow_shutter_effective_active)
        self.assertFalse(r_cam.breathing_comp_effective_active)

        # Reset Network Set. leaves both Exposure and Lens Compensation settings intact
        r_net = verify_auto_slow_shutter_and_breathing_comp_guard(
            pre_reset_auto_slow_shutter=AUTO_SLOW_SHUTTER_OFF_G101,
            pre_reset_breathing_comp=BREATHING_COMP_ON_G101,
            reset_action=RESET_ACTION_RESET_NETWORK_SET_PHASE259,
            claimed_post_reset_auto_slow_shutter=AUTO_SLOW_SHUTTER_OFF_G101,
            claimed_post_reset_breathing_comp=BREATHING_COMP_ON_G101,
        )
        self.assertTrue(r_net.valid)
        self.assertFalse(r_net.auto_slow_shutter_effective_active)
        self.assertTrue(r_net.breathing_comp_effective_active)

        # Initialize restores both to factory defaults (On / Off)
        r_init = verify_auto_slow_shutter_and_breathing_comp_guard(
            pre_reset_auto_slow_shutter=AUTO_SLOW_SHUTTER_OFF_G101,
            pre_reset_breathing_comp=BREATHING_COMP_ON_G101,
            reset_action=RESET_ACTION_INITIALIZE,
            claimed_post_reset_auto_slow_shutter=AUTO_SLOW_SHUTTER_ON_G101,
            claimed_post_reset_breathing_comp=BREATHING_COMP_OFF_G101,
        )
        self.assertTrue(r_init.valid)

    def test_16_g101_post_reset_drift_blocks_fail_closed(self) -> None:
        r_ass_drift = verify_auto_slow_shutter_and_breathing_comp_guard(
            pre_reset_auto_slow_shutter=AUTO_SLOW_SHUTTER_OFF_G101,
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
            claimed_post_reset_auto_slow_shutter=AUTO_SLOW_SHUTTER_OFF_G101,
        )
        self.assertFalse(r_ass_drift.valid)
        self.assertEqual(
            r_ass_drift.status, STATUS_BLOCKED_G101_RESET_SCOPE_PERSISTENCE_VIOLATION
        )

        r_bc_drift = verify_auto_slow_shutter_and_breathing_comp_guard(
            pre_reset_breathing_comp=BREATHING_COMP_ON_G101,
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
            claimed_post_reset_breathing_comp=BREATHING_COMP_ON_G101,
        )
        self.assertFalse(r_bc_drift.valid)
        self.assertEqual(
            r_bc_drift.status, STATUS_BLOCKED_G101_RESET_SCOPE_PERSISTENCE_VIOLATION
        )

    def test_17_g101_lockout_1_sq_mode_inhibits_auto_slow_shutter(self) -> None:
        r_ok = verify_auto_slow_shutter_and_breathing_comp_guard(
            shoot_mode=SHOOT_MODE_SQ_G101,
            claimed_auto_slow_shutter_active=False,
        )
        self.assertTrue(r_ok.valid)
        self.assertEqual(r_ok.active_auto_slow_shutter_lockouts, (LOCKOUT_1_SQ_MODE_G101,))
        self.assertFalse(r_ok.auto_slow_shutter_effective_active)

        r_bad = verify_auto_slow_shutter_and_breathing_comp_guard(
            shoot_mode=SHOOT_MODE_SQ_G101,
            claimed_auto_slow_shutter_active=True,
        )
        self.assertFalse(r_bad.valid)
        self.assertEqual(
            r_bad.status, STATUS_BLOCKED_G101_AUTO_SLOW_SHUTTER_LOCKOUT_BYPASS_VIOLATION
        )

    def test_18_g101_lockout_2_shutter_priority_inhibits_auto_slow_shutter(self) -> None:
        r_ok = verify_auto_slow_shutter_and_breathing_comp_guard(
            shoot_mode=SHOOT_MODE_SHUTTER_PRIORITY_G101,
            claimed_auto_slow_shutter_active=False,
        )
        self.assertTrue(r_ok.valid)
        self.assertEqual(
            r_ok.active_auto_slow_shutter_lockouts, (LOCKOUT_2_SHUTTER_PRIORITY_G101,)
        )

        r_bad = verify_auto_slow_shutter_and_breathing_comp_guard(
            shoot_mode=SHOOT_MODE_SHUTTER_PRIORITY_G101,
            claimed_auto_slow_shutter_active=True,
        )
        self.assertFalse(r_bad.valid)
        self.assertEqual(
            r_bad.status, STATUS_BLOCKED_G101_AUTO_SLOW_SHUTTER_LOCKOUT_BYPASS_VIOLATION
        )

    def test_19_g101_lockout_3_manual_exposure_inhibits_auto_slow_shutter(self) -> None:
        r_ok = verify_auto_slow_shutter_and_breathing_comp_guard(
            shoot_mode=SHOOT_MODE_MANUAL_EXPOSURE_G101,
            claimed_auto_slow_shutter_active=False,
        )
        self.assertTrue(r_ok.valid)
        self.assertEqual(
            r_ok.active_auto_slow_shutter_lockouts, (LOCKOUT_3_MANUAL_EXPOSURE_G101,)
        )

        r_bad = verify_auto_slow_shutter_and_breathing_comp_guard(
            shoot_mode=SHOOT_MODE_MANUAL_EXPOSURE_G101,
            claimed_auto_slow_shutter_active=True,
        )
        self.assertFalse(r_bad.valid)
        self.assertEqual(
            r_bad.status, STATUS_BLOCKED_G101_AUTO_SLOW_SHUTTER_LOCKOUT_BYPASS_VIOLATION
        )

    def test_20_g101_lockout_4_fixed_manual_iso_inhibits_auto_slow_shutter(self) -> None:
        r_ok = verify_auto_slow_shutter_and_breathing_comp_guard(
            iso_setting="ISO 800",
            claimed_auto_slow_shutter_active=False,
        )
        self.assertTrue(r_ok.valid)
        self.assertEqual(
            r_ok.active_auto_slow_shutter_lockouts, (LOCKOUT_4_ISO_NOT_AUTO_G101,)
        )

        r_bad = verify_auto_slow_shutter_and_breathing_comp_guard(
            iso_setting="ISO 12800",
            claimed_auto_slow_shutter_active=True,
        )
        self.assertFalse(r_bad.valid)
        self.assertEqual(
            r_bad.status, STATUS_BLOCKED_G101_AUTO_SLOW_SHUTTER_LOCKOUT_BYPASS_VIOLATION
        )

    def test_21_g101_lockout_5_flexible_exp_manual_shutter_vs_auto_shutter(self) -> None:
        # Flexible Exp. Mode with Auto shutter + ISO AUTO allows Auto Slow Shutter
        r_auto = verify_auto_slow_shutter_and_breathing_comp_guard(
            exposure_ctrl_type=EXPOSURE_CTRL_FLEXIBLE_EXP_MODE_G101,
            flexible_exp_shutter_mode=FLEX_EXP_SHUTTER_AUTO_G101,
            claimed_auto_slow_shutter_active=True,
        )
        self.assertTrue(r_auto.valid)
        self.assertTrue(r_auto.auto_slow_shutter_effective_active)

        # Flexible Exp. Mode with Manual shutter locks out Auto Slow Shutter
        r_man = verify_auto_slow_shutter_and_breathing_comp_guard(
            exposure_ctrl_type=EXPOSURE_CTRL_FLEXIBLE_EXP_MODE_G101,
            flexible_exp_shutter_mode=FLEX_EXP_SHUTTER_MANUAL_G101,
            claimed_auto_slow_shutter_active=False,
        )
        self.assertTrue(r_man.valid)
        self.assertEqual(
            r_man.active_auto_slow_shutter_lockouts,
            (LOCKOUT_5_FLEX_EXP_MANUAL_SHUTTER_G101,),
        )

        r_bad = verify_auto_slow_shutter_and_breathing_comp_guard(
            exposure_ctrl_type=EXPOSURE_CTRL_FLEXIBLE_EXP_MODE_G101,
            flexible_exp_shutter_mode=FLEX_EXP_SHUTTER_MANUAL_G101,
            claimed_auto_slow_shutter_active=True,
        )
        self.assertFalse(r_bad.valid)
        self.assertEqual(
            r_bad.status, STATUS_BLOCKED_G101_AUTO_SLOW_SHUTTER_LOCKOUT_BYPASS_VIOLATION
        )

    def test_22_g101_lockout_6_cine_ei_and_cine_ei_quick_vs_flexible_iso(self) -> None:
        # Flexible ISO + ISO AUTO permits Auto Slow Shutter
        r_flex_iso = verify_auto_slow_shutter_and_breathing_comp_guard(
            shoot_mode=SHOOT_MODE_APERTURE_PRIORITY_G101,
            log_shooting_mode=LOG_SHOOTING_FLEXIBLE_ISO_G101,
            claimed_auto_slow_shutter_active=True,
        )
        self.assertTrue(r_flex_iso.valid)
        self.assertTrue(r_flex_iso.auto_slow_shutter_effective_active)

        for cine_mode in (LOG_SHOOTING_CINE_EI_QUICK_G101, LOG_SHOOTING_CINE_EI_G101):
            r_locked = verify_auto_slow_shutter_and_breathing_comp_guard(
                log_shooting_mode=cine_mode,
                claimed_auto_slow_shutter_active=False,
            )
            self.assertTrue(r_locked.valid)
            self.assertEqual(
                r_locked.active_auto_slow_shutter_lockouts,
                (LOCKOUT_6_LOG_CINE_EI_G101,),
            )

            r_bypass = verify_auto_slow_shutter_and_breathing_comp_guard(
                log_shooting_mode=cine_mode,
                claimed_auto_slow_shutter_active=True,
            )
            self.assertFalse(r_bypass.valid)
            self.assertEqual(
                r_bypass.status,
                STATUS_BLOCKED_G101_AUTO_SLOW_SHUTTER_LOCKOUT_BYPASS_VIOLATION,
            )

    def test_23_g101_simultaneous_six_lockouts_and_nonzero_bypass_counter(self) -> None:
        r_all6 = verify_auto_slow_shutter_and_breathing_comp_guard(
            shoot_mode=SHOOT_MODE_SQ_G101,
            exposure_ctrl_type=EXPOSURE_CTRL_FLEXIBLE_EXP_MODE_G101,
            flexible_exp_shutter_mode=FLEX_EXP_SHUTTER_MANUAL_G101,
            iso_setting="ISO 800",
            log_shooting_mode=LOG_SHOOTING_CINE_EI_G101,
            claimed_auto_slow_shutter_active=False,
        )
        self.assertTrue(r_all6.valid)
        self.assertEqual(len(r_all6.active_auto_slow_shutter_lockouts), 4)
        self.assertEqual(
            AUTO_SLOW_SHUTTER_SIX_LOCKOUT_CONDITIONS_G101,
            (
                LOCKOUT_1_SQ_MODE_G101,
                LOCKOUT_2_SHUTTER_PRIORITY_G101,
                LOCKOUT_3_MANUAL_EXPOSURE_G101,
                LOCKOUT_4_ISO_NOT_AUTO_G101,
                LOCKOUT_5_FLEX_EXP_MANUAL_SHUTTER_G101,
                LOCKOUT_6_LOG_CINE_EI_G101,
            ),
        )

        r_cnt = verify_auto_slow_shutter_and_breathing_comp_guard(
            auto_slow_shutter_lockout_bypass_events=1
        )
        self.assertFalse(r_cnt.valid)
        self.assertEqual(
            r_cnt.status, STATUS_BLOCKED_G101_AUTO_SLOW_SHUTTER_LOCKOUT_BYPASS_VIOLATION
        )

    def test_24_g101_exhaustive_320_state_shutter_angle_disjointness_proof(self) -> None:
        matrix = compute_auto_slow_shutter_angle_disjointness_matrix()
        self.assertEqual(matrix["states_checked"], 320)
        self.assertGreater(matrix["auto_slow_active_states"], 0)
        self.assertGreater(matrix["shutter_angle_active_states"], 0)
        self.assertEqual(matrix["overlap_states"], 0)

    def test_25_g101_shutter_angle_valid_manual_modes_vs_program_auto_disjoint(
        self,
    ) -> None:
        # Valid Shutter Angle in Manual Exposure -> Angle governs, Auto Slow Shutter locked out
        r_man = verify_auto_slow_shutter_and_breathing_comp_guard(
            shoot_mode=SHOOT_MODE_MANUAL_EXPOSURE_G101,
            movie_shutter_mode=SHUTTER_MODE_ANGLE_G101,
            shutter_angle_deg=180.0,
            claimed_shutter_angle_governing_exposure=True,
            claimed_auto_slow_shutter_active=False,
        )
        self.assertTrue(r_man.valid)
        self.assertTrue(r_man.shutter_angle_governing_exposure)
        self.assertFalse(r_man.auto_slow_shutter_effective_active)

        # Valid Shutter Angle in Flexible Exp. Mode (Manual shutter)
        r_flex = verify_auto_slow_shutter_and_breathing_comp_guard(
            exposure_ctrl_type=EXPOSURE_CTRL_FLEXIBLE_EXP_MODE_G101,
            flexible_exp_shutter_mode=FLEX_EXP_SHUTTER_MANUAL_G101,
            movie_shutter_mode=SHUTTER_MODE_ANGLE_G101,
            shutter_angle_deg=90.0,
            claimed_shutter_angle_governing_exposure=True,
            claimed_auto_slow_shutter_active=False,
        )
        self.assertTrue(r_flex.valid)
        self.assertTrue(r_flex.shutter_angle_governing_exposure)

    def test_26_g101_shutter_angle_overlap_or_pre_v600_firmware_blocks(self) -> None:
        # Claiming Shutter Angle governs exposure in Program Auto blocks
        r_prog = verify_auto_slow_shutter_and_breathing_comp_guard(
            shoot_mode=SHOOT_MODE_PROGRAM_AUTO_G101,
            movie_shutter_mode=SHUTTER_MODE_ANGLE_G101,
            claimed_shutter_angle_governing_exposure=True,
        )
        self.assertFalse(r_prog.valid)
        self.assertEqual(
            r_prog.status, STATUS_BLOCKED_G101_SHUTTER_ANGLE_OVERLAP_VIOLATION
        )

        # Pre-6.00 firmware cannot select Shutter Mode = Angle
        r_old_fw = verify_auto_slow_shutter_and_breathing_comp_guard(
            firmware_version="5.00",
            shoot_mode=SHOOT_MODE_MANUAL_EXPOSURE_G101,
            movie_shutter_mode=SHUTTER_MODE_ANGLE_G101,
        )
        self.assertFalse(r_old_fw.valid)
        self.assertEqual(
            r_old_fw.status, STATUS_BLOCKED_G101_SHUTTER_ANGLE_OVERLAP_VIOLATION
        )

        # Non-zero overlap counter blocks
        r_ov = verify_auto_slow_shutter_and_breathing_comp_guard(
            auto_slow_shutter_angle_overlap_events=1
        )
        self.assertFalse(r_ov.valid)
        self.assertEqual(
            r_ov.status, STATUS_BLOCKED_G101_SHUTTER_ANGLE_OVERLAP_VIOLATION
        )

    def test_27_g101_breathing_comp_movie_compliant_lens_enables_fov_crop(self) -> None:
        r = verify_auto_slow_shutter_and_breathing_comp_guard(
            pre_reset_breathing_comp=BREATHING_COMP_ON_G101,
            capture_domain=CAPTURE_DOMAIN_MOVIE_G101,
            lens_breathing_comp_compliant=True,
            claimed_breathing_comp_active=True,
            claimed_breathing_comp_fov_crop_active=True,
        )
        self.assertTrue(r.valid)
        self.assertTrue(r.breathing_comp_effective_active)
        self.assertTrue(r.breathing_comp_fov_crop_active)

    def test_28_g101_breathing_comp_still_image_and_noncompliant_lens_boundaries(
        self,
    ) -> None:
        # Still image domain: Breathing Comp. does not apply
        r_still_ok = verify_auto_slow_shutter_and_breathing_comp_guard(
            pre_reset_breathing_comp=BREATHING_COMP_ON_G101,
            capture_domain=CAPTURE_DOMAIN_STILL_G101,
            claimed_breathing_comp_active=False,
            claimed_breathing_comp_fov_crop_active=False,
        )
        self.assertTrue(r_still_ok.valid)
        self.assertFalse(r_still_ok.breathing_comp_effective_active)

        r_still_bad = verify_auto_slow_shutter_and_breathing_comp_guard(
            pre_reset_breathing_comp=BREATHING_COMP_ON_G101,
            capture_domain=CAPTURE_DOMAIN_STILL_G101,
            claimed_breathing_comp_active=True,
        )
        self.assertFalse(r_still_bad.valid)
        self.assertEqual(
            r_still_bad.status, STATUS_BLOCKED_G101_BREATHING_COMP_STILL_OR_LENS_VIOLATION
        )

        # Non-compliant / PL-adapted lens cannot activate Breathing Comp.
        r_lens_bad = verify_auto_slow_shutter_and_breathing_comp_guard(
            pre_reset_breathing_comp=BREATHING_COMP_ON_G101,
            lens_breathing_comp_compliant=False,
            claimed_breathing_comp_active=True,
        )
        self.assertFalse(r_lens_bad.valid)
        self.assertEqual(
            r_lens_bad.status, STATUS_BLOCKED_G101_BREATHING_COMP_STILL_OR_LENS_VIOLATION
        )

        # Pre-3.00 firmware blocks Breathing Comp. = On
        r_fw2 = verify_auto_slow_shutter_and_breathing_comp_guard(
            firmware_version="2.00",
            pre_reset_breathing_comp=BREATHING_COMP_ON_G101,
        )
        self.assertFalse(r_fw2.valid)
        self.assertEqual(
            r_fw2.status, STATUS_BLOCKED_G101_BREATHING_COMP_STILL_OR_LENS_VIOLATION
        )

    def test_29_g101_breathing_comp_locked_out_during_4264x2408_raw_output(self) -> None:
        r_raw_ok = verify_auto_slow_shutter_and_breathing_comp_guard(
            pre_reset_breathing_comp=BREATHING_COMP_ON_G101,
            hdmi_raw_output_enabled=True,
            claimed_breathing_comp_active=False,
            claimed_breathing_comp_fov_crop_active=False,
        )
        self.assertTrue(r_raw_ok.valid)
        self.assertTrue(r_raw_ok.breathing_comp_hardware_locked_out)
        self.assertFalse(r_raw_ok.breathing_comp_effective_active)

        r_raw_bypass = verify_auto_slow_shutter_and_breathing_comp_guard(
            pre_reset_breathing_comp=BREATHING_COMP_ON_G101,
            hdmi_raw_output_enabled=True,
            claimed_breathing_comp_active=True,
        )
        self.assertFalse(r_raw_bypass.valid)
        self.assertEqual(
            r_raw_bypass.status,
            STATUS_BLOCKED_G101_BREATHING_COMP_RAW_OR_240P_BYPASS_VIOLATION,
        )

    def test_30_g101_breathing_comp_locked_out_during_sq_239_76p_and_200p(self) -> None:
        self.assertEqual(BREATHING_COMP_LOCKED_SQ_HIGH_FPS_G101, (200.0, 239.76, 240.0))
        for fps in (239.76, 200.0):
            r_ok = verify_auto_slow_shutter_and_breathing_comp_guard(
                shoot_mode=SHOOT_MODE_SQ_G101,
                sq_frame_rate_fps=fps,
                pre_reset_breathing_comp=BREATHING_COMP_ON_G101,
                claimed_breathing_comp_active=False,
            )
            self.assertTrue(r_ok.valid)
            self.assertTrue(r_ok.sq_high_fps_240p_200p_lockout_active)
            self.assertFalse(r_ok.breathing_comp_effective_active)

            r_bad = verify_auto_slow_shutter_and_breathing_comp_guard(
                shoot_mode=SHOOT_MODE_SQ_G101,
                sq_frame_rate_fps=fps,
                pre_reset_breathing_comp=BREATHING_COMP_ON_G101,
                claimed_breathing_comp_active=True,
            )
            self.assertFalse(r_bad.valid)
            self.assertEqual(
                r_bad.status,
                STATUS_BLOCKED_G101_BREATHING_COMP_RAW_OR_240P_BYPASS_VIOLATION,
            )

        # S&Q 119.88p permits Breathing Comp.
        r_120 = verify_auto_slow_shutter_and_breathing_comp_guard(
            shoot_mode=SHOOT_MODE_SQ_G101,
            sq_frame_rate_fps=119.88,
            pre_reset_breathing_comp=BREATHING_COMP_ON_G101,
            claimed_breathing_comp_active=True,
        )
        self.assertTrue(r_120.valid)
        self.assertTrue(r_120.breathing_comp_effective_active)

    def test_31_g101_breathing_comp_bypass_counter_blocks(self) -> None:
        r = verify_auto_slow_shutter_and_breathing_comp_guard(
            breathing_comp_raw_or_240p_bypass_events=2
        )
        self.assertFalse(r.valid)
        self.assertEqual(
            r.status, STATUS_BLOCKED_G101_BREATHING_COMP_RAW_OR_240P_BYPASS_VIOLATION
        )

    def test_32_g101_invalid_telemetry_and_wrong_body_model_block(self) -> None:
        r_fx6 = verify_auto_slow_shutter_and_breathing_comp_guard(
            body_model_name=FX6_MODEL_NAME
        )
        self.assertFalse(r_fx6.valid)
        self.assertEqual(r_fx6.status, STATUS_BLOCKED_G101_TELEMETRY_INVALID)

        r_angle = verify_auto_slow_shutter_and_breathing_comp_guard(
            shutter_angle_deg=720.0
        )
        self.assertFalse(r_angle.valid)
        self.assertEqual(r_angle.status, STATUS_BLOCKED_G101_TELEMETRY_INVALID)

        r_raw_res = verify_auto_slow_shutter_and_breathing_comp_guard(
            hdmi_raw_resolution="3840x2160"
        )
        self.assertFalse(r_raw_res.valid)
        self.assertEqual(r_raw_res.status, STATUS_BLOCKED_G101_TELEMETRY_INVALID)

    def test_33_g101_resolver_raises_value_error_on_invalid_inputs(self) -> None:
        with self.assertRaises(ValueError):
            resolve_fx3_auto_slow_shutter_and_breathing_comp_state(
                shoot_mode="InvalidMode"
            )

    def test_34_evaluate_g101_active_clean_room_and_persistent_write_block(self) -> None:
        v_act, res_act = evaluate_g101_auto_slow_shutter_and_breathing_comp_guard()
        self.assertTrue(v_act.passed)
        self.assertTrue(res_act.valid)
        self.assertEqual(v_act.gate_id, G101_GATE_ID)
        self.assertEqual(v_act.gate_code, G101_GATE_CODE)

        v_cr, res_cr = evaluate_g101_auto_slow_shutter_and_breathing_comp_guard(
            force_clean_room=True
        )
        self.assertTrue(v_cr.passed)
        self.assertEqual(res_cr.verification_mode, "CLEAN_ROOM_SYNTHETIC")

        v_wr, res_wr = evaluate_g101_auto_slow_shutter_and_breathing_comp_guard(
            force_clean_room=True, request_persistent_emmc_writes=True
        )
        self.assertFalse(v_wr.passed)
        self.assertFalse(res_wr.valid)
        self.assertEqual(res_wr.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)


    # ------------------------------------------------------------------
    # Section C: Gate G102 — HDMI Output Settings (`REC Control` <- `Time Code
    #            Output`, `4ch Audio Output` & `Rec. Media dur HDMI Output`
    #            Slot-1 Tier-0 Vault Guard) (35..52)
    # ------------------------------------------------------------------

    def test_35_g102_default_tier0_bench_safe_posture_passes_cleanly(self) -> None:
        res = verify_hdmi_reccontrol_tcout_4chaudio_and_vault_guard()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_VERIFIED_G102)
        self.assertEqual(
            res.hdmi_output_settings_menu_path, HDMI_OUTPUT_SETTINGS_MENU_PATH_G102
        )
        self.assertEqual(
            res.hdmi_output_factory_defaults, HDMI_OUTPUT_FACTORY_DEFAULTS_G102
        )
        self.assertEqual(res.effective_post_reset_time_code_output, HDMI_TC_OUTPUT_OFF_G102)
        self.assertEqual(res.effective_post_reset_rec_control, HDMI_REC_CONTROL_OFF_G102)
        self.assertEqual(res.hdmi_rec_ctrl_without_tc_violations, 0)
        self.assertEqual(
            res.effective_hdmi_audio_output_pair, HDMI_AUDIO_PAIR_CH1_L_CH2_R_G102
        )
        self.assertEqual(
            res.effective_post_reset_rec_media_dur_hdmi_output,
            HDMI_REC_MEDIA_TIER0_BENCH_SAFE_DEFAULT_G102,
        )
        self.assertTrue(res.internal_slot1_slot2_recording_inhibited)
        self.assertTrue(res.internal_proxy_recording_inhibited)
        self.assertEqual(res.slot1_hdmi_rec_vault_mutation_bytes, 0)

    def test_36_g102_hdmi_settings_survive_camera_and_network_reset_cleared_by_init(
        self,
    ) -> None:
        for rst in (
            RESET_ACTION_CAMERA_SETTINGS_RESET,
            RESET_ACTION_RESET_NETWORK_SET_PHASE259,
        ):
            r = verify_hdmi_reccontrol_tcout_4chaudio_and_vault_guard(
                reset_action=rst,
                pre_reset_time_code_output=HDMI_TC_OUTPUT_ON_G102,
                pre_reset_rec_control=HDMI_REC_CONTROL_ON_G102,
                pre_reset_audio_4ch_output=HDMI_4CH_AUDIO_CH3_CH4_G102,
                pre_reset_rec_media_dur_hdmi_output=HDMI_REC_MEDIA_OFF_G102,
                mi_shoe_4ch_audio_active=True,
                claimed_post_reset_time_code_output=HDMI_TC_OUTPUT_ON_G102,
                claimed_post_reset_rec_control=HDMI_REC_CONTROL_ON_G102,
                claimed_post_reset_audio_4ch_output=HDMI_4CH_AUDIO_CH3_CH4_G102,
                claimed_post_reset_rec_media_dur_hdmi_output=HDMI_REC_MEDIA_OFF_G102,
            )
            self.assertTrue(r.valid)
            self.assertTrue(r.hdmi_settings_survive_camera_settings_reset)
            self.assertTrue(r.hdmi_settings_survive_reset_network_set)
            self.assertTrue(r.hdmi_settings_cleared_only_by_initialize)

        # Initialize restores Sony factory defaults (TC=Off, REC Control=Off, 4ch=CH1/CH2, Rec. Media=On)
        r_init = verify_hdmi_reccontrol_tcout_4chaudio_and_vault_guard(
            reset_action=RESET_ACTION_INITIALIZE,
            pre_reset_time_code_output=HDMI_TC_OUTPUT_ON_G102,
            pre_reset_rec_control=HDMI_REC_CONTROL_ON_G102,
            pre_reset_audio_4ch_output=HDMI_4CH_AUDIO_CH3_CH4_G102,
            pre_reset_rec_media_dur_hdmi_output=HDMI_REC_MEDIA_OFF_G102,
            rec_trigger_requested=False,
            claimed_post_reset_time_code_output=HDMI_TC_OUTPUT_FACTORY_DEFAULT_G102,
            claimed_post_reset_rec_control=HDMI_REC_CONTROL_FACTORY_DEFAULT_G102,
            claimed_post_reset_audio_4ch_output=HDMI_4CH_AUDIO_FACTORY_DEFAULT_G102,
            claimed_post_reset_rec_media_dur_hdmi_output=HDMI_REC_MEDIA_FACTORY_DEFAULT_G102,
        )
        self.assertTrue(r_init.valid)

    def test_37_g102_post_reset_persistence_drift_blocks_across_all_4_items(
        self,
    ) -> None:
        for kwarg in (
            {"claimed_post_reset_time_code_output": HDMI_TC_OUTPUT_OFF_G102},
            {"claimed_post_reset_rec_control": HDMI_REC_CONTROL_OFF_G102},
            {"claimed_post_reset_audio_4ch_output": HDMI_4CH_AUDIO_CH1_CH2_G102},
            {"claimed_post_reset_rec_media_dur_hdmi_output": HDMI_REC_MEDIA_ON_G102},
        ):
            r = verify_hdmi_reccontrol_tcout_4chaudio_and_vault_guard(
                reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
                pre_reset_time_code_output=HDMI_TC_OUTPUT_ON_G102,
                pre_reset_rec_control=HDMI_REC_CONTROL_ON_G102,
                pre_reset_audio_4ch_output=HDMI_4CH_AUDIO_CH3_CH4_G102,
                pre_reset_rec_media_dur_hdmi_output=HDMI_REC_MEDIA_OFF_G102,
                **kwarg,  # type: ignore[arg-type]
            )
            self.assertFalse(r.valid)
            self.assertEqual(
                r.status, STATUS_BLOCKED_G102_HDMI_SETUP_RESET_PERSISTENCE_VIOLATION
            )

    def test_38_g102_rec_control_on_with_time_code_output_on_activates_cleanly(
        self,
    ) -> None:
        r = verify_hdmi_reccontrol_tcout_4chaudio_and_vault_guard(
            pre_reset_time_code_output=HDMI_TC_OUTPUT_ON_G102,
            pre_reset_rec_control=HDMI_REC_CONTROL_ON_G102,
            hdmi_output_active=True,
            claimed_rec_control_active=True,
        )
        self.assertTrue(r.valid)
        self.assertTrue(r.effective_rec_control_active)
        self.assertEqual(r.hdmi_rec_ctrl_without_tc_violations, 0)

    def test_39_g102_rec_control_on_with_time_code_output_off_blocks_fail_closed(
        self,
    ) -> None:
        r = verify_hdmi_reccontrol_tcout_4chaudio_and_vault_guard(
            pre_reset_time_code_output=HDMI_TC_OUTPUT_OFF_G102,
            pre_reset_rec_control=HDMI_REC_CONTROL_ON_G102,
        )
        self.assertFalse(r.valid)
        self.assertEqual(
            r.status, STATUS_BLOCKED_G102_HDMI_REC_CTRL_WITHOUT_TCOUT_VIOLATION
        )
        self.assertGreater(r.hdmi_rec_ctrl_without_tc_violations, 0)

    def test_40_g102_claimed_rec_control_active_without_tcout_or_hdmi_blocks(
        self,
    ) -> None:
        r_no_tc = verify_hdmi_reccontrol_tcout_4chaudio_and_vault_guard(
            pre_reset_time_code_output=HDMI_TC_OUTPUT_OFF_G102,
            pre_reset_rec_control=HDMI_REC_CONTROL_OFF_G102,
            claimed_rec_control_active=True,
        )
        self.assertFalse(r_no_tc.valid)
        self.assertEqual(
            r_no_tc.status, STATUS_BLOCKED_G102_HDMI_REC_CTRL_WITHOUT_TCOUT_VIOLATION
        )

        r_no_hdmi = verify_hdmi_reccontrol_tcout_4chaudio_and_vault_guard(
            pre_reset_time_code_output=HDMI_TC_OUTPUT_ON_G102,
            pre_reset_rec_control=HDMI_REC_CONTROL_ON_G102,
            hdmi_output_active=False,
            claimed_rec_control_active=True,
        )
        self.assertFalse(r_no_hdmi.valid)
        self.assertEqual(
            r_no_hdmi.status, STATUS_BLOCKED_G102_HDMI_REC_CTRL_WITHOUT_TCOUT_VIOLATION
        )

    def test_41_g102_nonzero_rec_ctrl_without_tc_counter_blocks(self) -> None:
        r = verify_hdmi_reccontrol_tcout_4chaudio_and_vault_guard(
            hdmi_rec_ctrl_without_tc_violations=1
        )
        self.assertFalse(r.valid)
        self.assertEqual(
            r.status, STATUS_BLOCKED_G102_HDMI_REC_CTRL_WITHOUT_TCOUT_VIOLATION
        )

    def test_42_g102_4ch_audio_output_ch1_ch2_routes_ch1_l_ch2_r(self) -> None:
        r = verify_hdmi_reccontrol_tcout_4chaudio_and_vault_guard(
            pre_reset_audio_4ch_output=HDMI_4CH_AUDIO_CH1_CH2_G102,
            mi_shoe_4ch_audio_active=True,
            claimed_hdmi_audio_output_pair=HDMI_AUDIO_PAIR_CH1_L_CH2_R_G102,
            claimed_hdmi_audio_left_channel="CH1",
            claimed_hdmi_audio_right_channel="CH2",
        )
        self.assertTrue(r.valid)
        self.assertEqual(r.hdmi_audio_left_channel, "CH1")
        self.assertEqual(r.hdmi_audio_right_channel, "CH2")
        self.assertEqual(r.effective_hdmi_audio_output_pair, HDMI_AUDIO_PAIR_CH1_L_CH2_R_G102)

    def test_43_g102_4ch_audio_output_ch3_ch4_with_mi_shoe_active_routes_ch3_l_ch4_r(
        self,
    ) -> None:
        r = verify_hdmi_reccontrol_tcout_4chaudio_and_vault_guard(
            pre_reset_audio_4ch_output=HDMI_4CH_AUDIO_CH3_CH4_G102,
            mi_shoe_4ch_audio_active=True,
            claimed_hdmi_audio_output_pair=HDMI_AUDIO_PAIR_CH3_L_CH4_R_G102,
            claimed_hdmi_audio_left_channel="CH3",
            claimed_hdmi_audio_right_channel="CH4",
        )
        self.assertTrue(r.valid)
        self.assertEqual(r.hdmi_audio_left_channel, "CH3")
        self.assertEqual(r.hdmi_audio_right_channel, "CH4")
        self.assertEqual(r.effective_hdmi_audio_output_pair, HDMI_AUDIO_PAIR_CH3_L_CH4_R_G102)

    def test_44_g102_4ch_audio_output_ch3_ch4_without_mi_shoe_falls_back_to_ch1_ch2(
        self,
    ) -> None:
        r_ok = verify_hdmi_reccontrol_tcout_4chaudio_and_vault_guard(
            pre_reset_audio_4ch_output=HDMI_4CH_AUDIO_CH3_CH4_G102,
            mi_shoe_4ch_audio_active=False,
            claimed_hdmi_audio_output_pair=HDMI_AUDIO_PAIR_CH1_L_CH2_R_G102,
        )
        self.assertTrue(r_ok.valid)

        r_bad = verify_hdmi_reccontrol_tcout_4chaudio_and_vault_guard(
            pre_reset_audio_4ch_output=HDMI_4CH_AUDIO_CH3_CH4_G102,
            mi_shoe_4ch_audio_active=False,
            claimed_hdmi_audio_output_pair=HDMI_AUDIO_PAIR_CH3_L_CH4_R_G102,
        )
        self.assertFalse(r_bad.valid)
        self.assertEqual(
            r_bad.status, STATUS_BLOCKED_G102_HDMI_4CH_AUDIO_ROUTING_MISMATCH
        )

    def test_45_g102_4ch_audio_left_or_right_channel_swap_blocks(self) -> None:
        r_swap = verify_hdmi_reccontrol_tcout_4chaudio_and_vault_guard(
            pre_reset_audio_4ch_output=HDMI_4CH_AUDIO_CH3_CH4_G102,
            mi_shoe_4ch_audio_active=True,
            claimed_hdmi_audio_left_channel="CH4",
            claimed_hdmi_audio_right_channel="CH3",
        )
        self.assertFalse(r_swap.valid)
        self.assertEqual(
            r_swap.status, STATUS_BLOCKED_G102_HDMI_4CH_AUDIO_ROUTING_MISMATCH
        )

    def test_46_g102_rec_media_off_inhibits_internal_card_and_proxy_recording(
        self,
    ) -> None:
        r = verify_hdmi_reccontrol_tcout_4chaudio_and_vault_guard(
            pre_reset_rec_media_dur_hdmi_output=HDMI_REC_MEDIA_OFF_G102,
            hdmi_output_active=True,
            proxy_recording_menu_setting="On",
            rec_trigger_requested=True,
            tier0_slot1_vault_protection_active=True,
            claimed_internal_media_recording_active=False,
            claimed_proxy_recording_active=False,
        )
        self.assertTrue(r.valid)
        self.assertTrue(r.internal_slot1_slot2_recording_inhibited)
        self.assertTrue(r.internal_proxy_recording_inhibited)
        self.assertFalse(r.effective_internal_media_recording_active)
        self.assertFalse(r.effective_proxy_recording_active)
        self.assertEqual(r.slot1_hdmi_rec_vault_mutation_bytes, 0)

    def test_47_g102_claimed_internal_or_proxy_write_when_rec_media_off_blocks(
        self,
    ) -> None:
        r_clip = verify_hdmi_reccontrol_tcout_4chaudio_and_vault_guard(
            pre_reset_rec_media_dur_hdmi_output=HDMI_REC_MEDIA_OFF_G102,
            hdmi_output_active=True,
            rec_trigger_requested=True,
            claimed_internal_media_recording_active=True,
        )
        self.assertFalse(r_clip.valid)
        self.assertEqual(
            r_clip.status, STATUS_BLOCKED_G102_SLOT1_HDMI_REC_MEDIA_VAULT_VIOLATION
        )

        r_proxy = verify_hdmi_reccontrol_tcout_4chaudio_and_vault_guard(
            pre_reset_rec_media_dur_hdmi_output=HDMI_REC_MEDIA_OFF_G102,
            hdmi_output_active=True,
            proxy_recording_menu_setting="On",
            rec_trigger_requested=True,
            claimed_proxy_recording_active=True,
        )
        self.assertFalse(r_proxy.valid)
        self.assertEqual(
            r_proxy.status, STATUS_BLOCKED_G102_SLOT1_HDMI_REC_MEDIA_VAULT_VIOLATION
        )

    def test_48_g102_rec_media_on_permitted_only_when_tier0_vault_not_active(
        self,
    ) -> None:
        # Non-vault production shooting: Rec. Media dur HDMI Output = On allows simultaneous card + proxy recording
        r_prod = verify_hdmi_reccontrol_tcout_4chaudio_and_vault_guard(
            pre_reset_rec_media_dur_hdmi_output=HDMI_REC_MEDIA_ON_G102,
            hdmi_output_active=True,
            proxy_recording_menu_setting="On",
            rec_trigger_requested=True,
            tier0_slot1_vault_protection_active=False,
            claimed_internal_media_recording_active=True,
            claimed_proxy_recording_active=True,
        )
        self.assertTrue(r_prod.valid)
        self.assertTrue(r_prod.effective_internal_media_recording_active)
        self.assertTrue(r_prod.effective_proxy_recording_active)

        # Tier-0 Slot-1 vault active: Rec. Media dur HDMI Output = On + rec_trigger blocks!
        r_vault_bad = verify_hdmi_reccontrol_tcout_4chaudio_and_vault_guard(
            pre_reset_rec_media_dur_hdmi_output=HDMI_REC_MEDIA_ON_G102,
            hdmi_output_active=True,
            rec_trigger_requested=True,
            tier0_slot1_vault_protection_active=True,
        )
        self.assertFalse(r_vault_bad.valid)
        self.assertEqual(
            r_vault_bad.status, STATUS_BLOCKED_G102_SLOT1_HDMI_REC_MEDIA_VAULT_VIOLATION
        )

    def test_49_g102_nonzero_slot1_vault_mutation_bytes_blocks_fail_closed(self) -> None:
        r = verify_hdmi_reccontrol_tcout_4chaudio_and_vault_guard(
            slot1_hdmi_rec_vault_mutation_bytes=4096
        )
        self.assertFalse(r.valid)
        self.assertEqual(
            r.status, STATUS_BLOCKED_G102_SLOT1_HDMI_REC_MEDIA_VAULT_VIOLATION
        )

    def test_50_g102_invalid_telemetry_and_wrong_body_model_block(self) -> None:
        r_fx6 = verify_hdmi_reccontrol_tcout_4chaudio_and_vault_guard(
            body_model_name=FX6_MODEL_NAME
        )
        self.assertFalse(r_fx6.valid)
        self.assertEqual(r_fx6.status, STATUS_BLOCKED_G102_TELEMETRY_INVALID)

        r_menu = verify_hdmi_reccontrol_tcout_4chaudio_and_vault_guard(
            hdmi_output_settings_menu_path="MENU -> Shooting -> [HDMI]"
        )
        self.assertFalse(r_menu.valid)
        self.assertEqual(r_menu.status, STATUS_BLOCKED_G102_TELEMETRY_INVALID)

    def test_51_g102_resolver_raises_value_error_on_invalid_inputs(self) -> None:
        with self.assertRaises(ValueError):
            resolve_fx3_hdmi_reccontrol_tcout_4chaudio_state(
                pre_reset_audio_4ch_output="CH5/CH6"
            )

    def test_52_evaluate_g102_active_clean_room_and_persistent_write_block(self) -> None:
        v_act, res_act = evaluate_g102_hdmi_reccontrol_tcout_4chaudio_guard()
        self.assertTrue(v_act.passed)
        self.assertTrue(res_act.valid)
        self.assertEqual(v_act.gate_id, G102_GATE_ID)
        self.assertEqual(v_act.gate_code, G102_GATE_CODE)

        v_cr, res_cr = evaluate_g102_hdmi_reccontrol_tcout_4chaudio_guard(
            force_clean_room=True
        )
        self.assertTrue(v_cr.passed)
        self.assertEqual(res_cr.verification_mode, "CLEAN_ROOM_SYNTHETIC")

        v_wr, res_wr = evaluate_g102_hdmi_reccontrol_tcout_4chaudio_guard(
            force_clean_room=True, request_persistent_emmc_writes=True
        )
        self.assertFalse(v_wr.passed)
        self.assertFalse(res_wr.valid)
        self.assertEqual(res_wr.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)


    # ------------------------------------------------------------------
    # Section D: Unified 102-Gate Master Preflight & CLI Verification (53..68)
    # ------------------------------------------------------------------

    def test_53_preflight_aliases_point_to_evaluate_102gate_preflight(self) -> None:
        self.assertIs(run_102_gate_preflight, evaluate_102gate_preflight)
        self.assertIs(evaluate_102_master_safety_gates, evaluate_102gate_preflight)

    def test_54_active_offline_102gate_preflight_verifies_99_of_102(self) -> None:
        rep = self.active_offline_102
        self.assertEqual(rep.summary["total_gates"], 102)
        self.assertEqual(rep.summary["verified_gates"], 99)
        self.assertEqual(rep.summary["blocked_or_pending_gates"], 3)
        self.assertEqual(rep.summary["g01_to_g12_verified"], 9)
        self.assertEqual(rep.summary["g13_to_g100_verified"], 88)
        self.assertEqual(rep.summary["g101_to_g102_verified"], 2)
        self.assertTrue(rep.offline_99_gates_verified)
        self.assertFalse(rep.all_102_gates_verified)
        self.assertTrue(rep.g13_to_g102_all_passed)
        self.assertTrue(rep.g101_to_g102_all_passed)
        self.assertEqual(rep.status, "VERIFIED_99_OF_102_AWAITING_PHYSICAL_TIER0")
        self.assertEqual(len(rep.gates), 102)
        self.assertEqual(rep.gates[-2]["gate_id"], G101_GATE_ID)
        self.assertEqual(rep.gates[-1]["gate_id"], G102_GATE_ID)

    def test_55_clean_room_offline_102gate_preflight_verifies_99_of_102(self) -> None:
        rep = self.clean_offline_102
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(rep.clean_room_forced)
        self.assertEqual(rep.summary["verified_gates"], 99)
        self.assertTrue(rep.offline_99_gates_verified)
        self.assertFalse(rep.all_102_gates_verified)
        self.assertEqual(rep.status, "VERIFIED_99_OF_102_AWAITING_PHYSICAL_TIER0")

    def test_56_active_dry_run_102gate_preflight_verifies_all_102_of_102(self) -> None:
        rep = self.active_dryrun_102
        self.assertEqual(rep.summary["total_gates"], 102)
        self.assertEqual(rep.summary["verified_gates"], 102)
        self.assertEqual(rep.summary["blocked_or_pending_gates"], 0)
        self.assertTrue(rep.offline_99_gates_verified)
        self.assertTrue(rep.all_102_gates_verified)
        self.assertTrue(rep.dry_run_rehearsal_only)
        self.assertEqual(
            rep.status, "VERIFIED_ALL_102_GATES_DRY_RUN_SIMULATED_BACKUP"
        )

    def test_57_clean_room_dry_run_102gate_preflight_verifies_all_102_of_102(
        self,
    ) -> None:
        rep = self.clean_dryrun_102
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(rep.summary["verified_gates"], 102)
        self.assertTrue(rep.all_102_gates_verified)
        self.assertTrue(rep.dry_run_rehearsal_only)
        self.assertEqual(
            rep.status, "VERIFIED_ALL_102_GATES_DRY_RUN_SIMULATED_BACKUP"
        )

    def test_58_preflight_dry_run_simulated_backup_kwarg_alias(self) -> None:
        rep = evaluate_102gate_preflight(
            force_clean_room=True,
            dry_run_simulated_backup=True,
            master_100_override=self.clean_dryrun_100,
        )
        self.assertTrue(rep.all_102_gates_verified)
        self.assertTrue(rep.dry_run_rehearsal_only)
        self.assertEqual(
            rep.status, "VERIFIED_ALL_102_GATES_DRY_RUN_SIMULATED_BACKUP"
        )

    def test_59_preflight_redlines_remain_hard_locked_across_all_modes(self) -> None:
        for rep in (
            self.active_offline_102,
            self.active_dryrun_102,
            self.clean_offline_102,
            self.clean_dryrun_102,
        ):
            self.assertFalse(rep.overall_ready_for_hardware_attach)
            self.assertFalse(rep.hardware_live_attachment_authorized)
            self.assertTrue(rep.agent_auto_flash_blocked)
            self.assertFalse(rep.human_hardware_attach_token)
            self.assertFalse(rep.el3_payload_transmit_authorized)
            self.assertFalse(rep.spi_nor_write_authorized)
            self.assertFalse(rep.persistent_emmc_writes_authorized)
            self.assertFalse(rep.persistent_write_release)
            self.assertFalse(rep.physical_flash_auto_exec_authorized)
            self.assertEqual(rep.usb_packets_transmitted, 0)
            self.assertEqual(rep.physical_usb_packets_emitted, 0)
            self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_60_preflight_propagates_g101_lockout_and_breathing_violations(
        self,
    ) -> None:
        rep_lock = evaluate_102gate_preflight(
            force_clean_room=True,
            master_100_override=self.clean_offline_100,
            auto_slow_shutter_breathing_kwargs={
                "shoot_mode": SHOOT_MODE_MANUAL_EXPOSURE_G101,
                "claimed_auto_slow_shutter_active": True,
            },
        )
        self.assertFalse(rep_lock.g101_to_g102_all_passed)
        self.assertFalse(rep_lock.offline_99_gates_verified)
        self.assertEqual(
            rep_lock.status,
            STATUS_BLOCKED_G101_AUTO_SLOW_SHUTTER_LOCKOUT_BYPASS_VIOLATION,
        )

        rep_bc = evaluate_102gate_preflight(
            force_clean_room=True,
            master_100_override=self.clean_offline_100,
            auto_slow_shutter_breathing_kwargs={
                "pre_reset_breathing_comp": BREATHING_COMP_ON_G101,
                "hdmi_raw_output_enabled": True,
                "claimed_breathing_comp_active": True,
            },
        )
        self.assertFalse(rep_bc.g101_to_g102_all_passed)
        self.assertEqual(
            rep_bc.status,
            STATUS_BLOCKED_G101_BREATHING_COMP_RAW_OR_240P_BYPASS_VIOLATION,
        )

    def test_61_preflight_propagates_g102_tcout_audio_and_vault_violations(
        self,
    ) -> None:
        rep_tc = evaluate_102gate_preflight(
            force_clean_room=True,
            master_100_override=self.clean_offline_100,
            hdmi_reccontrol_4chaudio_kwargs={
                "pre_reset_time_code_output": HDMI_TC_OUTPUT_OFF_G102,
                "pre_reset_rec_control": HDMI_REC_CONTROL_ON_G102,
            },
        )
        self.assertFalse(rep_tc.g101_to_g102_all_passed)
        self.assertEqual(
            rep_tc.status, STATUS_BLOCKED_G102_HDMI_REC_CTRL_WITHOUT_TCOUT_VIOLATION
        )

        rep_vault = evaluate_102gate_preflight(
            force_clean_room=True,
            master_100_override=self.clean_offline_100,
            hdmi_reccontrol_4chaudio_kwargs={
                "slot1_hdmi_rec_vault_mutation_bytes": 512,
            },
        )
        self.assertFalse(rep_vault.g101_to_g102_all_passed)
        self.assertEqual(
            rep_vault.status, STATUS_BLOCKED_G102_SLOT1_HDMI_REC_MEDIA_VAULT_VIOLATION
        )

    def test_62_preflight_blocks_persistent_emmc_write_request(self) -> None:
        rep = evaluate_102gate_preflight(
            force_clean_room=True,
            master_100_override=self.clean_offline_100,
            request_persistent_emmc_writes=True,
        )
        self.assertEqual(rep.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        self.assertFalse(rep.offline_99_gates_verified)
        self.assertFalse(rep.h0_h1_trial_entry_allowed)

    def test_63_preflight_json_serialization_contains_zero_raw_firmware_bytes(
        self,
    ) -> None:
        payload = json.dumps(self.clean_dryrun_102.to_dict())
        parsed = json.loads(payload)
        self.assertEqual(parsed["summary"]["total_gates"], 102)
        self.assertEqual(parsed["summary"]["verified_gates"], 102)
        self.assertEqual(parsed["raw_firmware_bytes_leaked"], 0)

    def test_64_cli_verify_auto_slow_shutter_breathing_guard_text_json_and_alias(
        self,
    ) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cli_main(
                [
                    "verify-auto-slow-shutter-breathing-comp-guard",
                    "--force-clean-room",
                ]
            )
        self.assertEqual(rc, 0)
        self.assertIn(G101_GATE_ID, buf.getvalue())

        buf_json = io.StringIO()
        with contextlib.redirect_stdout(buf_json):
            rc_j = cli_main(
                [
                    "verify-g101-auto-slow-shutter-breathing",
                    "--force-clean-room",
                    "--json",
                ]
            )
        self.assertEqual(rc_j, 0)
        data = json.loads(buf_json.getvalue())
        self.assertTrue(data["valid"])
        self.assertEqual(data["status"], STATUS_VERIFIED_G101)

    def test_65_cli_verify_hdmi_reccontrol_tcout_4chaudio_guard_text_json_and_alias(
        self,
    ) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cli_main(
                [
                    "verify-hdmi-reccontrol-tcout-4chaudio-guard",
                    "--force-clean-room",
                ]
            )
        self.assertEqual(rc, 0)
        self.assertIn(G102_GATE_ID, buf.getvalue())

        buf_json = io.StringIO()
        with contextlib.redirect_stdout(buf_json):
            rc_j = cli_main(
                [
                    "verify-g102-hdmi-reccontrol-4chaudio",
                    "--force-clean-room",
                    "--json",
                ]
            )
        self.assertEqual(rc_j, 0)
        data = json.loads(buf_json.getvalue())
        self.assertTrue(data["valid"])
        self.assertEqual(data["status"], STATUS_VERIFIED_G102)

    def test_66_cli_verify_102_gates_offline_and_dry_run_text_and_json(self) -> None:
        with mock.patch(
            "fx3_safety.realhw_auto_slow_shutter_hdmi_reccontrol_breathing_and_102gate_guard.evaluate_100gate_preflight",
            return_value=self.clean_offline_100,
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = cli_main(["verify-102-gates", "--force-clean-room"])
            self.assertEqual(rc, 0)
            self.assertIn("verified=99/102", buf.getvalue())

        with mock.patch(
            "fx3_safety.realhw_auto_slow_shutter_hdmi_reccontrol_breathing_and_102gate_guard.evaluate_100gate_preflight",
            return_value=self.clean_dryrun_100,
        ):
            buf_j = io.StringIO()
            with contextlib.redirect_stdout(buf_j):
                rc_j = cli_main(
                    [
                        "verify-102-gates",
                        "--force-clean-room",
                        "--simulate-bench-dry-run",
                        "--json",
                    ]
                )
            self.assertEqual(rc_j, 0)
            parsed = json.loads(buf_j.getvalue())
            self.assertEqual(parsed["summary"]["verified_gates"], 102)
            self.assertFalse(parsed["overall_ready_for_hardware_attach"])

    def test_67_module_standalone_main_offline_and_dry_run_text_and_json(self) -> None:
        with mock.patch(
            "fx3_safety.realhw_auto_slow_shutter_hdmi_reccontrol_breathing_and_102gate_guard.evaluate_100gate_preflight",
            return_value=self.clean_offline_100,
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = module_main(["--force-clean-room"])
            self.assertEqual(rc, 0)
            self.assertIn("verified=99/102", buf.getvalue())

        with mock.patch(
            "fx3_safety.realhw_auto_slow_shutter_hdmi_reccontrol_breathing_and_102gate_guard.evaluate_100gate_preflight",
            return_value=self.clean_dryrun_100,
        ):
            buf_j = io.StringIO()
            with contextlib.redirect_stdout(buf_j):
                rc_j = module_main(
                    ["--force-clean-room", "--simulate-bench-dry-run", "--json"]
                )
            self.assertEqual(rc_j, 0)
            parsed = json.loads(buf_j.getvalue())
            self.assertEqual(parsed["summary"]["verified_gates"], 102)

    def test_68_backward_compatibility_with_100gate_preflight_preserved(self) -> None:
        self.assertEqual(self.active_offline_100.summary["total_gates"], 100)
        self.assertEqual(self.active_offline_100.summary["verified_gates"], 97)
        self.assertEqual(self.clean_offline_100.summary["verified_gates"], 97)
        self.assertEqual(self.clean_dryrun_100.summary["verified_gates"], 100)


if __name__ == "__main__":
    unittest.main()
