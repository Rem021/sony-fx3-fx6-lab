"""Phase 249 Dual-Mode Unit Tests (`>=64` tests; 68 tests implemented) for
`fx3_safety.realhw_lock_op_parts_audio_timing_exp_step_and_96gate_guard`:

- Gate `G95`: `ILME-FX3` (`Ver. 7.02`) `[Lock Operation Parts]` (`Fn` Hold,
  `MENU + Fn` 5s Full-Body Lock Chord vs Destructive `MENU + Delete` 2s Slot
  Full Format Firewall & `My Dial` Temporary Override) Bench Guard.
- Gate `G96`: `ILME-FX3` (`Ver. 7.02`) `[Audio Out Timing]` (`Live`/`Lip Sync`)
  vs `[Audio signals]` Setup Persistence + `[Silent Mode]` Hard-Lock &
  `[Exposure step]` (`0.3EV`/`0.5EV`) vs `[Shutter Angle]` Constant-Table Guard.
- Unified `96`-Gate Master Safety Preflight (`evaluate_96gate_preflight` /
  `verify-96-gates`): `93/96` offline awaiting physical Tier-0 receipt and
  `96/96` in `--simulate-bench-dry-run` with all hardware write/live-attach
  redlines hard-locked `False`.
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
from fx3_safety.realhw_lock_op_parts_audio_timing_exp_step_and_96gate_guard import (
    ALLOWED_AUDIO_OUT_TIMING_MODES_G96,
    ALLOWED_AUDIO_SIGNALS_MODES_G96,
    ALLOWED_DIAL_CONTROLS_G95,
    ALLOWED_EXPOSURE_STEPS_G96,
    ALLOWED_LOCK_OPERATION_PARTS_MODES_G95,
    ALLOWED_RESET_ACTIONS_PHASE249,
    ALLOWED_SHOOT_MODES_G96,
    ALLOWED_SHUTTER_MODES_G96,
    AUDIO_OUT_TIMING_FACTORY_DEFAULT_G96,
    AUDIO_OUT_TIMING_LIP_SYNC_G96,
    AUDIO_OUT_TIMING_LIVE_G96,
    AUDIO_OUT_TIMING_MENU_PATH_G96,
    AUDIO_SIGNALS_FACTORY_DEFAULT_G96,
    AUDIO_SIGNALS_MENU_PATH_G96,
    AUDIO_SIGNALS_OFF_G96,
    AUDIO_SIGNALS_ON_G96,
    CINE_SHUTTER_ANGLE_CONSTANT_TABLE_DEG_G96,
    DESTRUCTIVE_MENU_DELETE_2S_CHORD_KEYS_G95,
    DESTRUCTIVE_MENU_DELETE_HOLD_SECONDS_G95,
    DONOR_CHECK_MAX_SECONDS_PHASE249,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    EXPOSURE_STEP_0_3EV_G96,
    EXPOSURE_STEP_0_5EV_G96,
    EXPOSURE_STEP_FACTORY_DEFAULT_G96,
    EXPOSURE_STEP_GOVERNED_TARGETS_G96,
    EXPOSURE_STEP_MENU_PATH_G96,
    FX3_DEFAULT_FW_VERSION_PHASE249,
    FX3_HELP_GUIDE_CODE_PHASE249,
    FX3_MIN_SUPPORTED_FW_TUPLE_PHASE249,
    FX3_MODEL_ID,
    FX3_MODEL_NAME,
    FX3_SHUTTER_ANGLE_MIN_FW_TUPLE_G96,
    G95,
    G95_GATE_CODE,
    G95_GATE_ID,
    G96,
    G96_GATE_CODE,
    G96_GATE_ID,
    GATE_G95_LOCK_OPERATION_PARTS_MENU_FN_5S_CHORD_AND_MYDIAL_OVERRIDE_GUARD,
    GATE_G96_AUDIO_OUT_TIMING_SIGNALS_PERSISTENCE_AND_EXP_STEP_SHUTTER_ANGLE_GUARD,
    HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    HUMAN_HARDWARE_ATTACH_TOKEN,
    LOCK_OPERATION_PARTS_FACTORY_DEFAULT_G95,
    LOCK_OPERATION_PARTS_MENU_PATH_G95,
    LOCK_OP_PARTS_ALL_G95,
    LOCK_OP_PARTS_DIAL_PLUS_WHEEL_G95,
    LOCK_OP_PARTS_LOCKED_OSD_BANNER_G95,
    LOCK_OP_PARTS_MULTI_SELECTOR_ONLY_G95,
    LOCK_OP_PARTS_OFF_G95,
    LOCK_OP_PARTS_SCOPE_MAP_G95,
    MENU_FN_5S_CHORD_KEYS_G95,
    MENU_FN_5S_LOCKED_CONTROLS_G95,
    MENU_FN_FULL_BODY_LOCK_HOLD_SECONDS_G95,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED,
    PHYSICAL_USB_PACKETS_EMITTED,
    PINNED_PHASE249_DONOR_SPECS,
    RAW_FIRMWARE_BYTES_LEAKED,
    REALHW_LOCK_OP_PARTS_AUDIO_TIMING_EXP_STEP_96GATE_SCHEMA,
    REALHW_LOCK_OP_PARTS_AUDIO_TIMING_EXP_STEP_96GATE_VERSION,
    RESET_ACTION_CAMERA_SETTINGS_RESET,
    RESET_ACTION_INITIALIZE,
    RESET_ACTION_NONE,
    SHOOT_MODE_MOVIE_G96,
    SHOOT_MODE_SQ_MOTION_G96,
    SHOOT_MODE_STILL_G96,
    SHUTTER_MODE_ANGLE_G96,
    SHUTTER_MODE_SPEED_G96,
    SPI_NOR_WRITE_AUTHORIZED,
    STATUS_BLOCKED_G95_DESTRUCTIVE_MENU_DELETE_2S_FORMAT_CHORD_CONFUSION,
    STATUS_BLOCKED_G95_FN_HOLD_TOGGLE_SCOPE_OR_OSD_VIOLATION,
    STATUS_BLOCKED_G95_LOCK_OP_PARTS_ENUM_OR_RESET_PERSISTENCE_VIOLATION,
    STATUS_BLOCKED_G95_MENU_FN_5S_CHORD_TIMING_OR_SHUTTER_SCOPE_VIOLATION,
    STATUS_BLOCKED_G95_MY_DIAL_TEMPORARY_OVERRIDE_VIOLATION,
    STATUS_BLOCKED_G95_TELEMETRY_INVALID,
    STATUS_BLOCKED_G95_UNATTENDED_TIER0_BENCH_CONTROLS_UNLOCKED,
    STATUS_BLOCKED_G96_AUDIO_OUT_TIMING_ENUM_OR_RESET_VIOLATION,
    STATUS_BLOCKED_G96_AUDIO_OUT_TIMING_SQ_OR_AUDIO_OFF_LOCKOUT_VIOLATION,
    STATUS_BLOCKED_G96_AUDIO_SIGNALS_SETUP_PERSISTENCE_VIOLATION,
    STATUS_BLOCKED_G96_AUDIO_SIGNALS_SILENT_MODE_HARD_LOCK_VIOLATION,
    STATUS_BLOCKED_G96_EXPOSURE_STEP_ENUM_RESET_OR_TARGETS_VIOLATION,
    STATUS_BLOCKED_G96_SHUTTER_ANGLE_CONSTANT_TABLE_COUPLED_DRIFT,
    STATUS_BLOCKED_G96_TELEMETRY_INVALID,
    STATUS_BLOCKED_PERSISTENT_EMMC_WRITE,
    STATUS_BLOCKED_PHASE249_DONOR_INTEGRITY,
    STATUS_VERIFIED_G95,
    STATUS_VERIFIED_G96,
    USB_PACKETS_TRANSMITTED,
    audit_phase249_donor_contracts,
    evaluate_96_master_safety_gates,
    evaluate_96gate_preflight,
    evaluate_g95_lock_operation_parts_and_chord_guard,
    evaluate_g96_audio_timing_signals_and_exp_step_guard,
    main as module_main,
    resolve_fx3_audio_timing_signals_and_exp_step_state,
    resolve_fx3_lock_operation_parts_and_chord_state,
    run_96_gate_preflight,
    verify_audio_timing_signals_and_exp_step_shutter_angle_guard,
    verify_lock_operation_parts_chord_and_mydial_guard,
)


class TestPhase249LockOpPartsAudioTimingExpStepAnd96GateGuard(unittest.TestCase):
    """68 fast dual-mode tests covering Gates G95, G96, and unified 96-Gate preflight."""

    @classmethod
    def setUpClass(cls) -> None:
        # Run unmocked evaluate_94gate_preflight() + evaluate_96gate_preflight() once
        # in the active environment mode and cache upstream 94-gate reports so all
        # 68 tests finish well under < 5s in both LOCAL_DONOR_O_RDONLY and
        # FX3_FX6_FORCE_CLEAN_ROOM=1 modes.
        cls.active_offline_94 = fx3_safety.evaluate_94gate_preflight()
        cls.active_offline_96 = evaluate_96gate_preflight(
            master_94_override=cls.active_offline_94
        )
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            cls.clean_offline_94 = fx3_safety.evaluate_94gate_preflight(
                force_clean_room=True
            )
            cls.clean_dryrun_94 = fx3_safety.evaluate_94gate_preflight(
                force_clean_room=True, dry_run_simulated=True
            )
            cls.clean_offline_96 = evaluate_96gate_preflight(
                force_clean_room=True, master_94_override=cls.clean_offline_94
            )
            cls.clean_dryrun_96 = evaluate_96gate_preflight(
                force_clean_room=True,
                simulate_bench_dry_run=True,
                master_94_override=cls.clean_dryrun_94,
            )

    # ------------------------------------------------------------------
    # Section A: Schema, Exports & O_RDONLY / Clean-Room Donor Audit (01..12)
    # ------------------------------------------------------------------

    def test_01_schema_version_gate_ids_and_redline_constants(self) -> None:
        self.assertEqual(
            REALHW_LOCK_OP_PARTS_AUDIO_TIMING_EXP_STEP_96GATE_SCHEMA,
            "realhw_lock_op_parts_audio_timing_exp_step_and_96gate_guard_v1",
        )
        self.assertEqual(
            REALHW_LOCK_OP_PARTS_AUDIO_TIMING_EXP_STEP_96GATE_VERSION, "1.0.0"
        )
        self.assertEqual(G95, G95_GATE_ID)
        self.assertEqual(G96, G96_GATE_ID)
        self.assertEqual(
            GATE_G95_LOCK_OPERATION_PARTS_MENU_FN_5S_CHORD_AND_MYDIAL_OVERRIDE_GUARD,
            G95_GATE_CODE,
        )
        self.assertEqual(
            GATE_G96_AUDIO_OUT_TIMING_SIGNALS_PERSISTENCE_AND_EXP_STEP_SHUTTER_ANGLE_GUARD,
            G96_GATE_CODE,
        )
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

    def test_02_top_level_package_exports_and_unique_dunder_all_no_shadowing(
        self,
    ) -> None:
        phase249_syms = (
            "REALHW_LOCK_OP_PARTS_AUDIO_TIMING_EXP_STEP_96GATE_SCHEMA",
            "REALHW_LOCK_OP_PARTS_AUDIO_TIMING_EXP_STEP_96GATE_VERSION",
            "G95_GATE_ID",
            "G95_GATE_CODE",
            "G96_GATE_ID",
            "G96_GATE_CODE",
            "Master96GateReport",
            "Phase249DonorAuditResult",
            "LockOperationPartsAndChordGuardResult",
            "AudioTimingSignalsAndExpStepGuardResult",
            "G95LockOperationPartsAndChordGuardResult",
            "G96AudioTimingSignalsAndExpStepGuardResult",
            "audit_phase249_donor_contracts",
            "evaluate_96gate_preflight",
            "evaluate_96_master_safety_gates",
            "run_96_gate_preflight",
            "evaluate_g95_lock_operation_parts_and_chord_guard",
            "evaluate_g96_audio_timing_signals_and_exp_step_guard",
            "verify_lock_operation_parts_chord_and_mydial_guard",
            "verify_audio_timing_signals_and_exp_step_shutter_angle_guard",
            "realhw_lock_op_parts_audio_timing_exp_step_and_96gate_guard",
        )
        for sym in phase249_syms:
            self.assertEqual(fx3_safety.__all__.count(sym), 1, msg=sym)
            self.assertTrue(hasattr(fx3_safety, sym), msg=sym)
        for prior_sym in ("evaluate_94gate_preflight", "evaluate_92gate_preflight"):
            self.assertIn(prior_sym, fx3_safety.__all__)
            self.assertTrue(hasattr(fx3_safety, prior_sym))

    def test_03_active_donor_audit_within_100ms_and_zero_leaked_bytes(self) -> None:
        res = audit_phase249_donor_contracts()
        self.assertTrue(res.valid)
        self.assertTrue(res.within_budget_100ms)
        self.assertLess(res.elapsed_seconds, DONOR_CHECK_MAX_SECONDS_PHASE249)
        self.assertEqual(res.raw_firmware_bytes_leaked, 0)
        self.assertTrue(res.fx3_contracts_verified)
        self.assertTrue(res.fx6_contracts_verified)
        env_clean = os.environ.get("FX3_FX6_FORCE_CLEAN_ROOM", "").strip() in (
            "1",
            "true",
            "TRUE",
            "yes",
            "YES",
        )
        if env_clean:
            self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        else:
            self.assertIn(
                res.verification_mode, ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC")
            )

    def test_04_forced_clean_room_flag_and_env_var_fallback(self) -> None:
        r_flag = audit_phase249_donor_contracts(force_clean_room=True)
        self.assertTrue(r_flag.valid)
        self.assertEqual(r_flag.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(r_flag.access_mode, "SYNTHETIC_CLEAN_ROOM")
        self.assertEqual(r_flag.files_inspected, 0)
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            r_env = audit_phase249_donor_contracts()
            self.assertTrue(r_env.valid)
            self.assertEqual(r_env.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_05_missing_donor_directory_falls_back_to_clean_room_synthetic(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            res = audit_phase249_donor_contracts(
                work_root=Path(tmp) / "nonexistent_donor_dir",
                force_clean_room=False,
            )
            self.assertTrue(res.valid)
            self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertEqual(res.files_inspected, 0)

    def test_06_corrupted_donor_marker_and_sha_blocks_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for _k, (_body, rel, *_rest) in PINNED_PHASE249_DONOR_SPECS.items():
                fp = root / rel
                fp.parent.mkdir(parents=True, exist_ok=True)
                fp.write_bytes(b"CORRUPTED_DONOR_STUB")
            res = audit_phase249_donor_contracts(
                work_root=root, force_clean_room=False
            )
            self.assertFalse(res.valid)
            self.assertEqual(res.status, STATUS_BLOCKED_PHASE249_DONOR_INTEGRITY)
            self.assertEqual(res.verification_mode, "LOCAL_DONOR_O_RDONLY")
            self.assertGreater(len(res.errors), 0)

    def test_07_donor_budget_exceeded_blocks_fail_closed_in_both_modes(self) -> None:
        r_clean = audit_phase249_donor_contracts(
            force_clean_room=True, max_budget_seconds=-1.0
        )
        self.assertFalse(r_clean.valid)
        self.assertEqual(r_clean.status, STATUS_BLOCKED_PHASE249_DONOR_INTEGRITY)

    def test_08_o_rdonly_strict_open_flags_never_request_write_bits(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sample = Path(tmp) / "sample.bin"
            sample.write_bytes(b"RDONLY_TEST")
            seen_flags = []
            real_open = os.open

            def _spy_open(path: str, flags: int, *args: object) -> int:
                seen_flags.append(flags)
                return real_open(path, flags, *args)

            from fx3_safety.realhw_lock_op_parts_audio_timing_exp_step_and_96gate_guard import (
                _read_file_o_rdonly,
            )

            with mock.patch("os.open", side_effect=_spy_open):
                data = _read_file_o_rdonly(sample)
            self.assertEqual(data, b"RDONLY_TEST")
            self.assertEqual(len(seen_flags), 1)
            self.assertEqual(seen_flags[0] & (os.O_WRONLY | os.O_RDWR), 0)

    def test_09_g95_canonical_menu_modes_scopes_and_chords(self) -> None:
        self.assertEqual(
            LOCK_OPERATION_PARTS_MENU_PATH_G95,
            "MENU -> Setup -> [Dial Customize] -> [Lock Operation Parts]",
        )
        self.assertEqual(
            ALLOWED_LOCK_OPERATION_PARTS_MODES_G95,
            ("Off", "Multi-Selector Only", "Dial + Wheel", "All"),
        )
        self.assertEqual(LOCK_OPERATION_PARTS_FACTORY_DEFAULT_G95, "Off")
        self.assertEqual(LOCK_OP_PARTS_LOCKED_OSD_BANNER_G95, "Locked.")
        self.assertEqual(MENU_FN_5S_CHORD_KEYS_G95, ("MENU", "Fn"))
        self.assertEqual(MENU_FN_FULL_BODY_LOCK_HOLD_SECONDS_G95, 5.0)
        self.assertEqual(DESTRUCTIVE_MENU_DELETE_2S_CHORD_KEYS_G95, ("MENU", "Delete"))
        self.assertEqual(DESTRUCTIVE_MENU_DELETE_HOLD_SECONDS_G95, 2.0)
        self.assertEqual(
            ALLOWED_DIAL_CONTROLS_G95,
            ("FRONT_DIAL", "REAR_DIAL", "CONTROL_WHEEL"),
        )
        self.assertEqual(
            ALLOWED_RESET_ACTIONS_PHASE249,
            ("NONE", "Camera Settings Reset", "Initialize"),
        )

    def test_10_g96_canonical_menu_modes_targets_and_constant_cine_angle_table(
        self,
    ) -> None:
        self.assertEqual(
            AUDIO_OUT_TIMING_MENU_PATH_G96,
            "MENU -> Shooting -> [Audio Recording] -> [Audio Out Timing]",
        )
        self.assertEqual(ALLOWED_AUDIO_OUT_TIMING_MODES_G96, ("Live", "Lip Sync"))
        self.assertEqual(AUDIO_OUT_TIMING_FACTORY_DEFAULT_G96, "Live")
        self.assertEqual(
            AUDIO_SIGNALS_MENU_PATH_G96,
            "MENU -> Setup -> [Sound Option] -> [Audio signals]",
        )
        self.assertEqual(ALLOWED_AUDIO_SIGNALS_MODES_G96, ("On", "Off"))
        self.assertEqual(AUDIO_SIGNALS_FACTORY_DEFAULT_G96, "On")
        self.assertEqual(ALLOWED_SHOOT_MODES_G96, ("Still", "Movie", "S&Q Motion"))
        self.assertEqual(
            EXPOSURE_STEP_MENU_PATH_G96,
            "MENU -> Exposure/Color -> [Exposure Comp.] -> [Exposure step]",
        )
        self.assertEqual(ALLOWED_EXPOSURE_STEPS_G96, ("0.3EV", "0.5EV"))
        self.assertEqual(EXPOSURE_STEP_FACTORY_DEFAULT_G96, "0.3EV")
        self.assertEqual(
            EXPOSURE_STEP_GOVERNED_TARGETS_G96,
            ("Shutter Speed", "Aperture", "Exposure Comp."),
        )
        self.assertEqual(ALLOWED_SHUTTER_MODES_G96, ("Shutter Speed", "Shutter Angle"))
        self.assertEqual(
            CINE_SHUTTER_ANGLE_CONSTANT_TABLE_DEG_G96,
            (5.6, 11.2, 22.5, 45.0, 72.0, 90.0, 144.0, 172.8, 180.0, 270.0, 360.0),
        )
        self.assertEqual(FX3_SHUTTER_ANGLE_MIN_FW_TUPLE_G96, (6, 0))

    def test_11_donor_audit_to_dict_json_roundtrip_zero_raw_bytes(self) -> None:
        d = audit_phase249_donor_contracts(force_clean_room=True).to_dict()
        blob = json.dumps(d)
        parsed = json.loads(blob)
        self.assertEqual(parsed["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(len(parsed["checked_markers"]), 6)

    def test_12_pinned_phase249_fx3_and_fx6_donor_spec_structure(self) -> None:
        bodies = {spec[0] for spec in PINNED_PHASE249_DONOR_SPECS.values()}
        self.assertEqual(bodies, {"FX3", "FX6"})
        self.assertEqual(len(PINNED_PHASE249_DONOR_SPECS), 6)


    # ------------------------------------------------------------------
    # Section B: Gate G95 — [Lock Operation Parts], Fn Hold, MENU + Fn 5s
    # Chord vs Destructive MENU + Delete 2s Firewall & My Dial Override (13..34)
    # ------------------------------------------------------------------

    def test_13_g95_default_bench_posture_passes_in_active_and_clean_room_modes(
        self,
    ) -> None:
        v_act, r_act = evaluate_g95_lock_operation_parts_and_chord_guard()
        self.assertTrue(v_act.passed)
        self.assertTrue(r_act.valid)
        self.assertEqual(r_act.status, STATUS_VERIFIED_G95)

        v_cln, r_cln = evaluate_g95_lock_operation_parts_and_chord_guard(
            force_clean_room=True
        )
        self.assertTrue(v_cln.passed)
        self.assertEqual(r_cln.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(r_cln.raw_firmware_bytes_leaked, 0)

    def test_14_g95_lock_op_parts_survives_camera_settings_reset_across_all_4_modes(
        self,
    ) -> None:
        for mode in ALLOWED_LOCK_OPERATION_PARTS_MODES_G95:
            res = verify_lock_operation_parts_chord_and_mydial_guard(
                pre_reset_lock_operation_parts=mode,
                reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
            )
            self.assertTrue(res.valid, msg=mode)
            self.assertEqual(res.effective_post_reset_lock_operation_parts, mode)
            self.assertTrue(res.lock_op_parts_survives_camera_settings_reset)

    def test_15_g95_lock_op_parts_resets_to_off_exclusively_on_initialize(self) -> None:
        for mode in ALLOWED_LOCK_OPERATION_PARTS_MODES_G95:
            res = verify_lock_operation_parts_chord_and_mydial_guard(
                pre_reset_lock_operation_parts=mode,
                reset_action=RESET_ACTION_INITIALIZE,
            )
            self.assertTrue(res.valid, msg=mode)
            self.assertEqual(
                res.effective_post_reset_lock_operation_parts, LOCK_OP_PARTS_OFF_G95
            )
            self.assertFalse(res.fn_hold_lock_engaged)
            self.assertEqual(res.effective_fn_hold_locked_controls, ())

    def test_16_g95_lock_op_parts_multi_slct_only_alias_normalized(self) -> None:
        res = verify_lock_operation_parts_chord_and_mydial_guard(
            pre_reset_lock_operation_parts="[Multi-Slct Only]",
            reset_action=RESET_ACTION_NONE,
            fn_hold_toggle_count=1,
        )
        self.assertTrue(res.valid)
        self.assertEqual(
            res.effective_post_reset_lock_operation_parts,
            LOCK_OP_PARTS_MULTI_SELECTOR_ONLY_G95,
        )
        self.assertEqual(res.effective_fn_hold_locked_controls, ("MULTI_SELECTOR",))

    def test_17_g95_blocks_false_camera_settings_reset_wipe_or_initialize_drift(
        self,
    ) -> None:
        r_wipe = verify_lock_operation_parts_chord_and_mydial_guard(
            pre_reset_lock_operation_parts=LOCK_OP_PARTS_ALL_G95,
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
            effective_post_reset_lock_operation_parts=LOCK_OP_PARTS_OFF_G95,
        )
        self.assertFalse(r_wipe.valid)
        self.assertIn(
            STATUS_BLOCKED_G95_LOCK_OP_PARTS_ENUM_OR_RESET_PERSISTENCE_VIOLATION,
            r_wipe.violation_codes,
        )

        r_init_drift = verify_lock_operation_parts_chord_and_mydial_guard(
            pre_reset_lock_operation_parts=LOCK_OP_PARTS_DIAL_PLUS_WHEEL_G95,
            reset_action=RESET_ACTION_INITIALIZE,
            effective_post_reset_lock_operation_parts=LOCK_OP_PARTS_DIAL_PLUS_WHEEL_G95,
        )
        self.assertFalse(r_init_drift.valid)
        self.assertIn(
            STATUS_BLOCKED_G95_LOCK_OP_PARTS_ENUM_OR_RESET_PERSISTENCE_VIOLATION,
            r_init_drift.violation_codes,
        )

    def test_18_g95_blocks_unsupported_lock_operation_parts_enum(self) -> None:
        res = verify_lock_operation_parts_chord_and_mydial_guard(
            pre_reset_lock_operation_parts="Touch + Shutter"
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            res.status,
            STATUS_BLOCKED_G95_LOCK_OP_PARTS_ENUM_OR_RESET_PERSISTENCE_VIOLATION,
        )

    def test_19_g95_fn_hold_off_mode_never_locks_controls(self) -> None:
        res = verify_lock_operation_parts_chord_and_mydial_guard(
            pre_reset_lock_operation_parts=LOCK_OP_PARTS_OFF_G95,
            reset_action=RESET_ACTION_NONE,
            fn_hold_toggle_count=3,
        )
        self.assertTrue(res.valid)
        self.assertFalse(res.fn_hold_lock_engaged)
        self.assertEqual(res.effective_fn_hold_locked_controls, ())

    def test_20_g95_fn_hold_multi_selector_only_scope_and_second_hold_release(
        self,
    ) -> None:
        r_lock = verify_lock_operation_parts_chord_and_mydial_guard(
            pre_reset_lock_operation_parts=LOCK_OP_PARTS_MULTI_SELECTOR_ONLY_G95,
            fn_hold_toggle_count=1,
            chord_keys_pressed=(),
            chord_hold_seconds=0.0,
            unattended_tier0_dump_active=False,
        )
        self.assertTrue(r_lock.valid)
        self.assertTrue(r_lock.fn_hold_lock_engaged)
        self.assertEqual(r_lock.effective_fn_hold_locked_controls, ("MULTI_SELECTOR",))
        self.assertEqual(r_lock.locked_osd_banner, "Locked.")

        r_unlock = verify_lock_operation_parts_chord_and_mydial_guard(
            pre_reset_lock_operation_parts=LOCK_OP_PARTS_MULTI_SELECTOR_ONLY_G95,
            fn_hold_toggle_count=2,
            chord_keys_pressed=(),
            chord_hold_seconds=0.0,
            unattended_tier0_dump_active=False,
        )
        self.assertTrue(r_unlock.valid)
        self.assertFalse(r_unlock.fn_hold_lock_engaged)
        self.assertEqual(r_unlock.effective_fn_hold_locked_controls, ())
        self.assertEqual(r_unlock.locked_osd_banner, "")

    def test_21_g95_fn_hold_dial_plus_wheel_and_all_scopes_with_locked_osd_banner(
        self,
    ) -> None:
        r_dw = verify_lock_operation_parts_chord_and_mydial_guard(
            pre_reset_lock_operation_parts=LOCK_OP_PARTS_DIAL_PLUS_WHEEL_G95,
            fn_hold_toggle_count=1,
        )
        self.assertTrue(r_dw.valid)
        self.assertEqual(
            r_dw.effective_fn_hold_locked_controls,
            LOCK_OP_PARTS_SCOPE_MAP_G95[LOCK_OP_PARTS_DIAL_PLUS_WHEEL_G95],
        )

        r_all = verify_lock_operation_parts_chord_and_mydial_guard(
            pre_reset_lock_operation_parts=LOCK_OP_PARTS_ALL_G95,
            fn_hold_toggle_count=1,
        )
        self.assertTrue(r_all.valid)
        self.assertEqual(
            r_all.effective_fn_hold_locked_controls,
            LOCK_OP_PARTS_SCOPE_MAP_G95[LOCK_OP_PARTS_ALL_G95],
        )
        self.assertEqual(r_all.locked_osd_banner, "Locked.")

    def test_22_g95_blocks_fn_hold_scope_mismatch_or_missing_locked_osd_banner(
        self,
    ) -> None:
        r_scope = verify_lock_operation_parts_chord_and_mydial_guard(
            pre_reset_lock_operation_parts=LOCK_OP_PARTS_MULTI_SELECTOR_ONLY_G95,
            fn_hold_toggle_count=1,
            effective_fn_hold_locked_controls=("FRONT_DIAL",),
        )
        self.assertFalse(r_scope.valid)
        self.assertIn(
            STATUS_BLOCKED_G95_FN_HOLD_TOGGLE_SCOPE_OR_OSD_VIOLATION,
            r_scope.violation_codes,
        )

        r_osd = verify_lock_operation_parts_chord_and_mydial_guard(
            pre_reset_lock_operation_parts=LOCK_OP_PARTS_ALL_G95,
            fn_hold_toggle_count=1,
            locked_osd_banner="",
        )
        self.assertFalse(r_osd.valid)
        self.assertIn(
            STATUS_BLOCKED_G95_FN_HOLD_TOGGLE_SCOPE_OR_OSD_VIOLATION,
            r_osd.violation_codes,
        )

    def test_23_g95_menu_fn_5s_chord_locks_all_controls_except_shutter_button(
        self,
    ) -> None:
        res = verify_lock_operation_parts_chord_and_mydial_guard(
            pre_reset_lock_operation_parts=LOCK_OP_PARTS_OFF_G95,
            chord_keys_pressed="MENU + Fn",
            chord_hold_seconds=5.2,
            unattended_tier0_dump_active=True,
        )
        self.assertTrue(res.valid)
        self.assertTrue(res.menu_fn_5s_full_body_lock_engaged)
        self.assertEqual(
            res.effective_full_body_locked_controls, MENU_FN_5S_LOCKED_CONTROLS_G95
        )
        self.assertTrue(res.shutter_button_remains_unlocked)
        self.assertTrue(res.unattended_bench_physical_lock_enforced)

    def test_24_g95_blocks_menu_fn_hold_under_5_seconds(self) -> None:
        res = verify_lock_operation_parts_chord_and_mydial_guard(
            chord_keys_pressed=("MENU", "Fn"),
            chord_hold_seconds=4.9,
            unattended_tier0_dump_active=False,
        )
        self.assertFalse(res.valid)
        self.assertIn(
            STATUS_BLOCKED_G95_MENU_FN_5S_CHORD_TIMING_OR_SHUTTER_SCOPE_VIOLATION,
            res.violation_codes,
        )

    def test_25_g95_blocks_false_claim_that_shutter_button_is_locked(self) -> None:
        res = verify_lock_operation_parts_chord_and_mydial_guard(
            chord_keys_pressed=("MENU", "Fn"),
            chord_hold_seconds=5.0,
            shutter_button_remains_unlocked=False,
        )
        self.assertFalse(res.valid)
        self.assertIn(
            STATUS_BLOCKED_G95_MENU_FN_5S_CHORD_TIMING_OR_SHUTTER_SCOPE_VIOLATION,
            res.violation_codes,
        )

    def test_26_g95_blocks_unknown_key_chord_combination(self) -> None:
        res = verify_lock_operation_parts_chord_and_mydial_guard(
            chord_keys_pressed=("MENU", "ISO"),
            chord_hold_seconds=5.0,
            unattended_tier0_dump_active=False,
        )
        self.assertFalse(res.valid)
        self.assertIn(
            STATUS_BLOCKED_G95_MENU_FN_5S_CHORD_TIMING_OR_SHUTTER_SCOPE_VIOLATION,
            res.violation_codes,
        )

    def test_27_g95_blocks_unattended_tier0_dump_when_physical_controls_unlocked(
        self,
    ) -> None:
        res = verify_lock_operation_parts_chord_and_mydial_guard(
            chord_keys_pressed=(),
            chord_hold_seconds=0.0,
            unattended_tier0_dump_active=True,
        )
        self.assertFalse(res.valid)
        self.assertIn(
            STATUS_BLOCKED_G95_UNATTENDED_TIER0_BENCH_CONTROLS_UNLOCKED,
            res.violation_codes,
        )

    def test_28_g95_allows_unlocked_bench_when_unattended_tier0_dump_inactive(
        self,
    ) -> None:
        res = verify_lock_operation_parts_chord_and_mydial_guard(
            pre_reset_lock_operation_parts=LOCK_OP_PARTS_OFF_G95,
            fn_hold_toggle_count=0,
            chord_keys_pressed=(),
            chord_hold_seconds=0.0,
            unattended_tier0_dump_active=False,
        )
        self.assertTrue(res.valid)
        self.assertFalse(res.menu_fn_5s_full_body_lock_engaged)
        self.assertEqual(res.locked_osd_banner, "")

    def test_29_g95_hard_firewall_blocks_destructive_menu_delete_2s_format_chord(
        self,
    ) -> None:
        res = verify_lock_operation_parts_chord_and_mydial_guard(
            chord_keys_pressed="MENU + Delete",
            chord_hold_seconds=2.0,
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            res.status,
            STATUS_BLOCKED_G95_DESTRUCTIVE_MENU_DELETE_2S_FORMAT_CHORD_CONFUSION,
        )
        self.assertFalse(res.destructive_menu_delete_chord_blocked)
        self.assertEqual(res.destructive_menu_delete_confusions, 1)

    def test_30_g95_hard_firewall_blocks_slot_full_format_chord_flag_or_trash_alias(
        self,
    ) -> None:
        r_flag = verify_lock_operation_parts_chord_and_mydial_guard(
            slot_full_format_chord_invoked=True
        )
        self.assertFalse(r_flag.valid)
        self.assertIn(
            STATUS_BLOCKED_G95_DESTRUCTIVE_MENU_DELETE_2S_FORMAT_CHORD_CONFUSION,
            r_flag.violation_codes,
        )

        r_trash = verify_lock_operation_parts_chord_and_mydial_guard(
            chord_keys_pressed=("MENU", "Trash"),
            chord_hold_seconds=2.0,
        )
        self.assertFalse(r_trash.valid)
        self.assertIn(
            STATUS_BLOCKED_G95_DESTRUCTIVE_MENU_DELETE_2S_FORMAT_CHORD_CONFUSION,
            r_trash.violation_codes,
        )

    def test_31_g95_my_dial_recall_temporarily_unlocks_assigned_dials_and_relocks(
        self,
    ) -> None:
        res = verify_lock_operation_parts_chord_and_mydial_guard(
            pre_reset_lock_operation_parts=LOCK_OP_PARTS_DIAL_PLUS_WHEEL_G95,
            fn_hold_toggle_count=1,
            my_dial_recall_active=True,
            my_dial_assigned_controls=("FRONT_DIAL", "REAR_DIAL"),
            my_dial_relocked_on_release=True,
        )
        self.assertTrue(res.valid)
        self.assertTrue(res.my_dial_recall_active)
        self.assertEqual(
            res.effective_temporarily_unlocked_controls, ("FRONT_DIAL", "REAR_DIAL")
        )
        self.assertTrue(res.my_dial_relocked_on_release)

    def test_32_g95_blocks_my_dial_non_dial_target_mismatch_or_failure_to_relock(
        self,
    ) -> None:
        r_bad_target = verify_lock_operation_parts_chord_and_mydial_guard(
            my_dial_recall_active=True,
            my_dial_assigned_controls=("MULTI_SELECTOR",),
        )
        self.assertFalse(r_bad_target.valid)
        self.assertIn(
            STATUS_BLOCKED_G95_MY_DIAL_TEMPORARY_OVERRIDE_VIOLATION,
            r_bad_target.violation_codes,
        )

        r_no_relock = verify_lock_operation_parts_chord_and_mydial_guard(
            my_dial_recall_active=True,
            my_dial_assigned_controls=("FRONT_DIAL",),
            my_dial_relocked_on_release=False,
        )
        self.assertFalse(r_no_relock.valid)
        self.assertIn(
            STATUS_BLOCKED_G95_MY_DIAL_TEMPORARY_OVERRIDE_VIOLATION,
            r_no_relock.violation_codes,
        )

    def test_33_g95_blocks_invalid_model_firmware_or_boolean_telemetry(self) -> None:
        r_model = verify_lock_operation_parts_chord_and_mydial_guard(
            body_model_name="ILME-FX6"
        )
        self.assertFalse(r_model.valid)
        self.assertIn(STATUS_BLOCKED_G95_TELEMETRY_INVALID, r_model.violation_codes)

        r_reset = verify_lock_operation_parts_chord_and_mydial_guard(
            reset_action="HardWipe"
        )
        self.assertFalse(r_reset.valid)
        self.assertIn(STATUS_BLOCKED_G95_TELEMETRY_INVALID, r_reset.violation_codes)

    def test_34_g95_blocks_persistent_emmc_write_and_corrupted_donor_audit(
        self,
    ) -> None:
        v_emmc, r_emmc = evaluate_g95_lock_operation_parts_and_chord_guard(
            force_clean_room=True, request_persistent_emmc_writes=True
        )
        self.assertFalse(v_emmc.passed)
        self.assertIn(STATUS_BLOCKED_PERSISTENT_EMMC_WRITE, r_emmc.violation_codes)

        bad_audit = audit_phase249_donor_contracts(
            force_clean_room=True, max_budget_seconds=-1.0
        )
        v_bad, r_bad = evaluate_g95_lock_operation_parts_and_chord_guard(
            donor_audit=bad_audit
        )
        self.assertFalse(v_bad.passed)
        self.assertIn(STATUS_BLOCKED_PHASE249_DONOR_INTEGRITY, r_bad.violation_codes)

    # ------------------------------------------------------------------
    # Section C: Gate G96 — [Audio Out Timing], [Audio signals],
    # [Exposure step] & [Shutter Angle] Constant-Table Guard (35..54)
    # ------------------------------------------------------------------

    def test_35_g96_default_bench_posture_passes_in_active_and_clean_room_modes(
        self,
    ) -> None:
        v_act, r_act = evaluate_g96_audio_timing_signals_and_exp_step_guard()
        self.assertTrue(v_act.passed)
        self.assertTrue(r_act.valid)
        self.assertEqual(r_act.status, STATUS_VERIFIED_G96)

        v_cln, r_cln = evaluate_g96_audio_timing_signals_and_exp_step_guard(
            force_clean_room=True
        )
        self.assertTrue(v_cln.passed)
        self.assertEqual(r_cln.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(r_cln.raw_firmware_bytes_leaked, 0)

    def test_36_g96_audio_out_timing_live_and_lip_sync_reset_by_camera_settings_reset(
        self,
    ) -> None:
        r_none = verify_audio_timing_signals_and_exp_step_shutter_angle_guard(
            pre_reset_audio_out_timing=AUDIO_OUT_TIMING_LIP_SYNC_G96,
            reset_action=RESET_ACTION_NONE,
        )
        self.assertTrue(r_none.valid)
        self.assertEqual(
            r_none.effective_post_reset_audio_out_timing, AUDIO_OUT_TIMING_LIP_SYNC_G96
        )

        r_reset = verify_audio_timing_signals_and_exp_step_shutter_angle_guard(
            pre_reset_audio_out_timing=AUDIO_OUT_TIMING_LIP_SYNC_G96,
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
        )
        self.assertTrue(r_reset.valid)
        self.assertEqual(
            r_reset.effective_post_reset_audio_out_timing, AUDIO_OUT_TIMING_LIVE_G96
        )
        self.assertTrue(r_reset.audio_out_timing_reset_by_camera_settings_reset)

    def test_37_g96_blocks_audio_out_timing_invalid_enum_or_reset_survival_drift(
        self,
    ) -> None:
        r_enum = verify_audio_timing_signals_and_exp_step_shutter_angle_guard(
            pre_reset_audio_out_timing="Delayed 2f"
        )
        self.assertFalse(r_enum.valid)
        self.assertIn(
            STATUS_BLOCKED_G96_AUDIO_OUT_TIMING_ENUM_OR_RESET_VIOLATION,
            r_enum.violation_codes,
        )

        r_drift = verify_audio_timing_signals_and_exp_step_shutter_angle_guard(
            pre_reset_audio_out_timing=AUDIO_OUT_TIMING_LIP_SYNC_G96,
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
            effective_post_reset_audio_out_timing=AUDIO_OUT_TIMING_LIP_SYNC_G96,
        )
        self.assertFalse(r_drift.valid)
        self.assertIn(
            STATUS_BLOCKED_G96_AUDIO_OUT_TIMING_ENUM_OR_RESET_VIOLATION,
            r_drift.violation_codes,
        )

    def test_38_g96_audio_out_timing_locked_out_in_sq_motion(self) -> None:
        res = verify_audio_timing_signals_and_exp_step_shutter_angle_guard(
            shoot_mode=SHOOT_MODE_SQ_MOTION_G96,
            audio_recording="On",
        )
        self.assertTrue(res.valid)
        self.assertFalse(res.audio_out_timing_available)
        self.assertTrue(res.audio_out_timing_sq_or_audio_off_locked_out)

    def test_39_g96_audio_out_timing_locked_out_when_audio_recording_off(self) -> None:
        res = verify_audio_timing_signals_and_exp_step_shutter_angle_guard(
            shoot_mode=SHOOT_MODE_MOVIE_G96,
            audio_recording="Off",
        )
        self.assertTrue(res.valid)
        self.assertFalse(res.audio_out_timing_available)
        self.assertTrue(res.audio_out_timing_sq_or_audio_off_locked_out)

    def test_40_g96_blocks_audio_out_timing_false_availability_or_override_while_locked(
        self,
    ) -> None:
        r_avail = verify_audio_timing_signals_and_exp_step_shutter_angle_guard(
            shoot_mode=SHOOT_MODE_SQ_MOTION_G96,
            audio_out_timing_available=True,
        )
        self.assertFalse(r_avail.valid)
        self.assertIn(
            STATUS_BLOCKED_G96_AUDIO_OUT_TIMING_SQ_OR_AUDIO_OFF_LOCKOUT_VIOLATION,
            r_avail.violation_codes,
        )

        r_ovr = verify_audio_timing_signals_and_exp_step_shutter_angle_guard(
            shoot_mode=SHOOT_MODE_MOVIE_G96,
            audio_recording="Off",
            audio_out_timing_override_while_locked=True,
        )
        self.assertFalse(r_ovr.valid)
        self.assertIn(
            STATUS_BLOCKED_G96_AUDIO_OUT_TIMING_SQ_OR_AUDIO_OFF_LOCKOUT_VIOLATION,
            r_ovr.violation_codes,
        )

    def test_41_g96_audio_signals_survives_camera_settings_reset_and_resets_on_initialize(
        self,
    ) -> None:
        r_cam = verify_audio_timing_signals_and_exp_step_shutter_angle_guard(
            pre_reset_audio_signals=AUDIO_SIGNALS_OFF_G96,
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
            silent_mode="Off",
        )
        self.assertTrue(r_cam.valid)
        self.assertEqual(
            r_cam.configured_post_reset_audio_signals, AUDIO_SIGNALS_OFF_G96
        )
        self.assertEqual(r_cam.effective_audio_signals, AUDIO_SIGNALS_OFF_G96)
        self.assertTrue(r_cam.audio_signals_survives_camera_settings_reset)

        r_init = verify_audio_timing_signals_and_exp_step_shutter_angle_guard(
            pre_reset_audio_signals=AUDIO_SIGNALS_OFF_G96,
            reset_action=RESET_ACTION_INITIALIZE,
            silent_mode="Off",
        )
        self.assertTrue(r_init.valid)
        self.assertEqual(
            r_init.configured_post_reset_audio_signals, AUDIO_SIGNALS_ON_G96
        )
        self.assertEqual(r_init.effective_audio_signals, AUDIO_SIGNALS_ON_G96)

    def test_42_g96_blocks_audio_signals_camera_settings_reset_wipe_or_invalid_enum(
        self,
    ) -> None:
        r_wipe = verify_audio_timing_signals_and_exp_step_shutter_angle_guard(
            pre_reset_audio_signals=AUDIO_SIGNALS_OFF_G96,
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
            configured_post_reset_audio_signals=AUDIO_SIGNALS_ON_G96,
        )
        self.assertFalse(r_wipe.valid)
        self.assertIn(
            STATUS_BLOCKED_G96_AUDIO_SIGNALS_SETUP_PERSISTENCE_VIOLATION,
            r_wipe.violation_codes,
        )

        r_enum = verify_audio_timing_signals_and_exp_step_shutter_angle_guard(
            pre_reset_audio_signals="ShutterOnly"
        )
        self.assertFalse(r_enum.valid)
        self.assertIn(
            STATUS_BLOCKED_G96_AUDIO_SIGNALS_SETUP_PERSISTENCE_VIOLATION,
            r_enum.violation_codes,
        )

    def test_43_g96_silent_mode_on_hard_locks_audio_signals_to_off_and_restores_when_off(
        self,
    ) -> None:
        r_silent = verify_audio_timing_signals_and_exp_step_shutter_angle_guard(
            pre_reset_audio_signals=AUDIO_SIGNALS_ON_G96,
            reset_action=RESET_ACTION_NONE,
            silent_mode="On",
        )
        self.assertTrue(r_silent.valid)
        self.assertEqual(
            r_silent.configured_post_reset_audio_signals, AUDIO_SIGNALS_ON_G96
        )
        self.assertEqual(r_silent.effective_audio_signals, AUDIO_SIGNALS_OFF_G96)
        self.assertTrue(r_silent.audio_signals_locked_off_by_silent_mode)

    def test_44_g96_blocks_audio_signals_on_or_override_while_silent_mode_on(
        self,
    ) -> None:
        r_on = verify_audio_timing_signals_and_exp_step_shutter_angle_guard(
            pre_reset_audio_signals=AUDIO_SIGNALS_ON_G96,
            silent_mode="On",
            effective_audio_signals=AUDIO_SIGNALS_ON_G96,
        )
        self.assertFalse(r_on.valid)
        self.assertIn(
            STATUS_BLOCKED_G96_AUDIO_SIGNALS_SILENT_MODE_HARD_LOCK_VIOLATION,
            r_on.violation_codes,
        )

        r_ovr = verify_audio_timing_signals_and_exp_step_shutter_angle_guard(
            pre_reset_audio_signals=AUDIO_SIGNALS_ON_G96,
            silent_mode="On",
            audio_signals_override_while_silent=True,
        )
        self.assertFalse(r_ovr.valid)
        self.assertIn(
            STATUS_BLOCKED_G96_AUDIO_SIGNALS_SILENT_MODE_HARD_LOCK_VIOLATION,
            r_ovr.violation_codes,
        )


    def test_45_g96_exposure_step_0_3ev_and_0_5ev_reset_by_camera_settings_reset(
        self,
    ) -> None:
        r_none = verify_audio_timing_signals_and_exp_step_shutter_angle_guard(
            pre_reset_exposure_step=EXPOSURE_STEP_0_5EV_G96,
            reset_action=RESET_ACTION_NONE,
        )
        self.assertTrue(r_none.valid)
        self.assertEqual(r_none.effective_post_reset_exposure_step, EXPOSURE_STEP_0_5EV_G96)

        r_reset = verify_audio_timing_signals_and_exp_step_shutter_angle_guard(
            pre_reset_exposure_step=EXPOSURE_STEP_0_5EV_G96,
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
        )
        self.assertTrue(r_reset.valid)
        self.assertEqual(
            r_reset.effective_post_reset_exposure_step, EXPOSURE_STEP_0_3EV_G96
        )
        self.assertTrue(r_reset.exposure_step_reset_by_camera_settings_reset)

    def test_46_g96_blocks_exposure_step_invalid_enum_reset_drift_or_corrupted_targets(
        self,
    ) -> None:
        r_enum = verify_audio_timing_signals_and_exp_step_shutter_angle_guard(
            pre_reset_exposure_step="1.0EV"
        )
        self.assertFalse(r_enum.valid)
        self.assertIn(
            STATUS_BLOCKED_G96_EXPOSURE_STEP_ENUM_RESET_OR_TARGETS_VIOLATION,
            r_enum.violation_codes,
        )

        r_drift = verify_audio_timing_signals_and_exp_step_shutter_angle_guard(
            pre_reset_exposure_step=EXPOSURE_STEP_0_5EV_G96,
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
            effective_post_reset_exposure_step=EXPOSURE_STEP_0_5EV_G96,
        )
        self.assertFalse(r_drift.valid)
        self.assertIn(
            STATUS_BLOCKED_G96_EXPOSURE_STEP_ENUM_RESET_OR_TARGETS_VIOLATION,
            r_drift.violation_codes,
        )

        r_targets = verify_audio_timing_signals_and_exp_step_shutter_angle_guard(
            governed_exposure_targets=("Shutter Speed", "Aperture")
        )
        self.assertFalse(r_targets.valid)
        self.assertIn(
            STATUS_BLOCKED_G96_EXPOSURE_STEP_ENUM_RESET_OR_TARGETS_VIOLATION,
            r_targets.violation_codes,
        )

    def test_47_g96_shutter_angle_constant_table_identical_across_0_3ev_and_0_5ev(
        self,
    ) -> None:
        for deg in CINE_SHUTTER_ANGLE_CONSTANT_TABLE_DEG_G96:
            r03 = verify_audio_timing_signals_and_exp_step_shutter_angle_guard(
                pre_reset_exposure_step=EXPOSURE_STEP_0_3EV_G96,
                reset_action=RESET_ACTION_NONE,
                shutter_mode=SHUTTER_MODE_ANGLE_G96,
                active_shutter_angle_deg=deg,
            )
            r05 = verify_audio_timing_signals_and_exp_step_shutter_angle_guard(
                pre_reset_exposure_step=EXPOSURE_STEP_0_5EV_G96,
                reset_action=RESET_ACTION_NONE,
                shutter_mode=SHUTTER_MODE_ANGLE_G96,
                active_shutter_angle_deg=deg,
            )
            self.assertTrue(r03.valid)
            self.assertTrue(r05.valid)
            self.assertEqual(
                r03.shutter_angle_table_at_0_3ev, r05.shutter_angle_table_at_0_5ev
            )
            self.assertTrue(r05.shutter_angle_unaffected_by_exposure_step)
            self.assertEqual(r05.shutter_angle_exposure_step_drift_events, 0)

    def test_48_g96_shutter_speed_mode_with_valid_exposure_step_passes(self) -> None:
        res = verify_audio_timing_signals_and_exp_step_shutter_angle_guard(
            shutter_mode=SHUTTER_MODE_SPEED_G96,
            shoot_mode=SHOOT_MODE_STILL_G96,
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.shutter_mode, SHUTTER_MODE_SPEED_G96)

    def test_49_g96_blocks_shutter_angle_claimed_in_exposure_step_governed_targets(
        self,
    ) -> None:
        res = verify_audio_timing_signals_and_exp_step_shutter_angle_guard(
            governed_exposure_targets=(
                "Shutter Speed",
                "Shutter Angle",
                "Aperture",
                "Exposure Comp.",
            )
        )
        self.assertFalse(res.valid)
        self.assertIn(
            STATUS_BLOCKED_G96_SHUTTER_ANGLE_CONSTANT_TABLE_COUPLED_DRIFT,
            res.violation_codes,
        )
        self.assertFalse(res.shutter_angle_unaffected_by_exposure_step)
        self.assertEqual(res.shutter_angle_exposure_step_drift_events, 1)

    def test_50_g96_blocks_shutter_angle_table_drift_or_scaling_between_0_3ev_and_0_5ev(
        self,
    ) -> None:
        r_tbl = verify_audio_timing_signals_and_exp_step_shutter_angle_guard(
            shutter_angle_table_at_0_5ev=(6.0, 12.0, 24.0, 45.0, 90.0, 180.0, 360.0)
        )
        self.assertFalse(r_tbl.valid)
        self.assertIn(
            STATUS_BLOCKED_G96_SHUTTER_ANGLE_CONSTANT_TABLE_COUPLED_DRIFT,
            r_tbl.violation_codes,
        )

        r_scaled = verify_audio_timing_signals_and_exp_step_shutter_angle_guard(
            shutter_angle_scaled_by_exposure_step=True
        )
        self.assertFalse(r_scaled.valid)
        self.assertIn(
            STATUS_BLOCKED_G96_SHUTTER_ANGLE_CONSTANT_TABLE_COUPLED_DRIFT,
            r_scaled.violation_codes,
        )

    def test_51_g96_blocks_shutter_angle_out_of_constant_table_or_pre_600_firmware(
        self,
    ) -> None:
        r_deg = verify_audio_timing_signals_and_exp_step_shutter_angle_guard(
            shutter_mode=SHUTTER_MODE_ANGLE_G96,
            active_shutter_angle_deg=137.5,
        )
        self.assertFalse(r_deg.valid)
        self.assertIn(
            STATUS_BLOCKED_G96_SHUTTER_ANGLE_CONSTANT_TABLE_COUPLED_DRIFT,
            r_deg.violation_codes,
        )

        r_fw = verify_audio_timing_signals_and_exp_step_shutter_angle_guard(
            firmware_version="5.00",
            shutter_mode=SHUTTER_MODE_ANGLE_G96,
        )
        self.assertFalse(r_fw.valid)
        self.assertIn(
            STATUS_BLOCKED_G96_SHUTTER_ANGLE_CONSTANT_TABLE_COUPLED_DRIFT,
            r_fw.violation_codes,
        )

    def test_52_g96_blocks_invalid_model_firmware_or_boolean_telemetry(self) -> None:
        r_model = verify_audio_timing_signals_and_exp_step_shutter_angle_guard(
            body_model_id=0xDEADBEEF
        )
        self.assertFalse(r_model.valid)
        self.assertIn(STATUS_BLOCKED_G96_TELEMETRY_INVALID, r_model.violation_codes)

        r_shoot = verify_audio_timing_signals_and_exp_step_shutter_angle_guard(
            shoot_mode="TimelapseVideo"
        )
        self.assertFalse(r_shoot.valid)
        self.assertIn(STATUS_BLOCKED_G96_TELEMETRY_INVALID, r_shoot.violation_codes)

    def test_53_g96_blocks_persistent_emmc_write_and_corrupted_donor_audit(
        self,
    ) -> None:
        v_emmc, r_emmc = evaluate_g96_audio_timing_signals_and_exp_step_guard(
            force_clean_room=True, request_persistent_emmc_writes=True
        )
        self.assertFalse(v_emmc.passed)
        self.assertIn(STATUS_BLOCKED_PERSISTENT_EMMC_WRITE, r_emmc.violation_codes)

        bad_audit = audit_phase249_donor_contracts(
            force_clean_room=True, max_budget_seconds=-1.0
        )
        v_bad, r_bad = evaluate_g96_audio_timing_signals_and_exp_step_guard(
            donor_audit=bad_audit
        )
        self.assertFalse(v_bad.passed)
        self.assertIn(STATUS_BLOCKED_PHASE249_DONOR_INTEGRITY, r_bad.violation_codes)

    def test_54_g96_state_resolver_none_reset_and_initialize_matrix(self) -> None:
        s_none = resolve_fx3_audio_timing_signals_and_exp_step_state(
            pre_reset_audio_out_timing="Lip Sync",
            pre_reset_audio_signals="Off",
            pre_reset_exposure_step="0.5EV",
            reset_action="NONE",
            silent_mode="Off",
        )
        self.assertEqual(s_none["expected_post_reset_audio_out_timing"], "Lip Sync")
        self.assertEqual(s_none["expected_post_reset_audio_signals"], "Off")
        self.assertEqual(s_none["expected_post_reset_exposure_step"], "0.5EV")

        s_cam = resolve_fx3_audio_timing_signals_and_exp_step_state(
            pre_reset_audio_out_timing="Lip Sync",
            pre_reset_audio_signals="Off",
            pre_reset_exposure_step="0.5EV",
            reset_action="Camera Settings Reset",
            silent_mode="Off",
        )
        self.assertEqual(s_cam["expected_post_reset_audio_out_timing"], "Live")
        self.assertEqual(s_cam["expected_post_reset_audio_signals"], "Off")
        self.assertEqual(s_cam["expected_post_reset_exposure_step"], "0.3EV")

        s_init = resolve_fx3_audio_timing_signals_and_exp_step_state(
            pre_reset_audio_out_timing="Lip Sync",
            pre_reset_audio_signals="Off",
            pre_reset_exposure_step="0.5EV",
            reset_action="Initialize",
            silent_mode="On",
        )
        self.assertEqual(s_init["expected_post_reset_audio_out_timing"], "Live")
        self.assertEqual(s_init["expected_post_reset_audio_signals"], "On")
        self.assertEqual(s_init["expected_effective_audio_signals"], "Off")
        self.assertEqual(s_init["expected_post_reset_exposure_step"], "0.3EV")

    # ------------------------------------------------------------------
    # Section D: Unified 96-Gate Master Preflight & CLI Wiring (55..68)
    # ------------------------------------------------------------------

    def test_55_offline_96gate_preflight_verifies_93_of_96_in_active_mode(
        self,
    ) -> None:
        rep = self.active_offline_96
        self.assertEqual(
            rep.schema, REALHW_LOCK_OP_PARTS_AUDIO_TIMING_EXP_STEP_96GATE_SCHEMA
        )
        self.assertEqual(rep.summary["total_gates"], 96)
        self.assertEqual(rep.summary["verified_gates"], 93)
        self.assertEqual(rep.summary["blocked_or_pending_gates"], 3)
        self.assertTrue(rep.offline_93_gates_verified)
        self.assertFalse(rep.all_96_gates_verified)
        self.assertTrue(rep.g95_to_g96_all_passed)
        self.assertTrue(rep.g13_to_g96_all_passed)
        self.assertEqual(rep.status, "VERIFIED_93_OF_96_AWAITING_PHYSICAL_TIER0")
        self.assertEqual(len(rep.gates), 96)
        self.assertEqual(rep.gates[-2]["gate_id"], G95_GATE_ID)
        self.assertEqual(rep.gates[-1]["gate_id"], G96_GATE_ID)

    def test_56_clean_room_offline_and_dryrun_96gate_preflight_93_and_96(self) -> None:
        off = self.clean_offline_96
        self.assertEqual(off.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(off.summary["verified_gates"], 93)
        self.assertTrue(off.offline_93_gates_verified)
        self.assertFalse(off.all_96_gates_verified)

        dry = self.clean_dryrun_96
        self.assertEqual(dry.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(dry.summary["verified_gates"], 96)
        self.assertEqual(dry.summary["blocked_or_pending_gates"], 0)
        self.assertTrue(dry.offline_93_gates_verified)
        self.assertTrue(dry.all_96_gates_verified)
        self.assertTrue(dry.dry_run_rehearsal_only)
        self.assertEqual(
            dry.status, "VERIFIED_ALL_96_GATES_DRY_RUN_SIMULATED_BACKUP"
        )

    def test_57_all_hardware_redlines_remain_false_even_in_96_of_96_dry_run(
        self,
    ) -> None:
        for rep in (self.active_offline_96, self.clean_offline_96, self.clean_dryrun_96):
            self.assertFalse(rep.overall_ready_for_hardware_attach)
            self.assertFalse(rep.hardware_live_attachment_authorized)
            self.assertFalse(rep.persistent_emmc_writes_authorized)
            self.assertFalse(rep.persistent_write_release)
            self.assertFalse(rep.spi_nor_write_authorized)
            self.assertFalse(rep.el3_payload_transmit_authorized)
            self.assertFalse(rep.physical_flash_auto_exec_authorized)
            self.assertFalse(rep.human_hardware_attach_token)
            self.assertTrue(rep.agent_auto_flash_blocked)
            self.assertEqual(rep.usb_packets_transmitted, 0)
            self.assertEqual(rep.physical_usb_packets_emitted, 0)
            self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_58_preflight_aliases_and_dry_run_flag_variants_consistent(self) -> None:
        self.assertIs(evaluate_96_master_safety_gates, evaluate_96gate_preflight)
        self.assertIs(run_96_gate_preflight, evaluate_96gate_preflight)
        r_backup_flag = evaluate_96gate_preflight(
            force_clean_room=True,
            dry_run_simulated_backup=True,
            master_94_override=self.clean_dryrun_94,
        )
        self.assertTrue(r_backup_flag.all_96_gates_verified)
        self.assertTrue(r_backup_flag.dry_run_rehearsal_only)

    def test_59_preflight_propagates_g95_failure_status_and_blocks_h0_h1(self) -> None:
        rep = evaluate_96gate_preflight(
            force_clean_room=True,
            master_94_override=self.clean_offline_94,
            lock_op_parts_kwargs={"chord_keys_pressed": "MENU + Delete", "chord_hold_seconds": 2.0},
        )
        self.assertFalse(rep.g95_to_g96_all_passed)
        self.assertFalse(rep.offline_93_gates_verified)
        self.assertFalse(rep.h0_h1_trial_entry_allowed)
        self.assertEqual(
            rep.status,
            STATUS_BLOCKED_G95_DESTRUCTIVE_MENU_DELETE_2S_FORMAT_CHORD_CONFUSION,
        )

    def test_60_preflight_propagates_g96_failure_status_and_blocks_h0_h1(self) -> None:
        rep = evaluate_96gate_preflight(
            force_clean_room=True,
            master_94_override=self.clean_offline_94,
            audio_timing_exp_step_kwargs={"shutter_angle_scaled_by_exposure_step": True},
        )
        self.assertFalse(rep.g95_to_g96_all_passed)
        self.assertFalse(rep.offline_93_gates_verified)
        self.assertFalse(rep.h0_h1_trial_entry_allowed)
        self.assertEqual(
            rep.status,
            STATUS_BLOCKED_G96_SHUTTER_ANGLE_CONSTANT_TABLE_COUPLED_DRIFT,
        )

    def test_61_preflight_blocks_persistent_emmc_write_request(self) -> None:
        rep = evaluate_96gate_preflight(
            force_clean_room=True,
            master_94_override=self.clean_offline_94,
            request_persistent_emmc_writes=True,
        )
        self.assertEqual(rep.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        self.assertFalse(rep.offline_93_gates_verified)
        self.assertFalse(rep.h0_h1_trial_entry_allowed)

    def test_62_preflight_json_serialization_contains_zero_raw_firmware_bytes(
        self,
    ) -> None:
        payload = json.dumps(self.clean_dryrun_96.to_dict())
        parsed = json.loads(payload)
        self.assertEqual(parsed["summary"]["total_gates"], 96)
        self.assertEqual(parsed["summary"]["verified_gates"], 96)
        self.assertEqual(parsed["raw_firmware_bytes_leaked"], 0)

    def test_63_cli_verify_lock_op_parts_chord_guard_text_json_and_alias(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cli_main(["verify-lock-op-parts-chord-guard", "--force-clean-room"])
        self.assertEqual(rc, 0)
        self.assertIn(G95_GATE_ID, buf.getvalue())

        buf_json = io.StringIO()
        with contextlib.redirect_stdout(buf_json):
            rc_j = cli_main(
                ["verify-g95-lock-op-parts-chord", "--force-clean-room", "--json"]
            )
        self.assertEqual(rc_j, 0)
        data = json.loads(buf_json.getvalue())
        self.assertTrue(data["valid"])
        self.assertEqual(data["status"], STATUS_VERIFIED_G95)

    def test_64_cli_verify_audio_timing_exp_step_guard_text_json_and_alias(
        self,
    ) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cli_main(["verify-audio-timing-exp-step-guard", "--force-clean-room"])
        self.assertEqual(rc, 0)
        self.assertIn(G96_GATE_ID, buf.getvalue())

        buf_json = io.StringIO()
        with contextlib.redirect_stdout(buf_json):
            rc_j = cli_main(
                ["verify-g96-audio-timing-exp-step", "--force-clean-room", "--json"]
            )
        self.assertEqual(rc_j, 0)
        data = json.loads(buf_json.getvalue())
        self.assertTrue(data["valid"])
        self.assertEqual(data["status"], STATUS_VERIFIED_G96)

    def test_65_cli_verify_96_gates_offline_and_dry_run_text_and_json(self) -> None:
        with mock.patch(
            "fx3_safety.realhw_lock_op_parts_audio_timing_exp_step_and_96gate_guard.evaluate_94gate_preflight",
            return_value=self.clean_offline_94,
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = cli_main(["verify-96-gates", "--force-clean-room"])
            self.assertEqual(rc, 0)
            self.assertIn("verified=93/96", buf.getvalue())

        with mock.patch(
            "fx3_safety.realhw_lock_op_parts_audio_timing_exp_step_and_96gate_guard.evaluate_94gate_preflight",
            return_value=self.clean_dryrun_94,
        ):
            buf_j = io.StringIO()
            with contextlib.redirect_stdout(buf_j):
                rc_j = cli_main(
                    [
                        "verify-96-gates",
                        "--force-clean-room",
                        "--simulate-bench-dry-run",
                        "--json",
                    ]
                )
            self.assertEqual(rc_j, 0)
            parsed = json.loads(buf_j.getvalue())
            self.assertEqual(parsed["summary"]["verified_gates"], 96)
            self.assertFalse(parsed["overall_ready_for_hardware_attach"])

    def test_66_module_standalone_main_offline_and_dry_run_text_and_json(self) -> None:
        with mock.patch(
            "fx3_safety.realhw_lock_op_parts_audio_timing_exp_step_and_96gate_guard.evaluate_94gate_preflight",
            return_value=self.clean_offline_94,
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = module_main(["--force-clean-room"])
            self.assertEqual(rc, 0)
            self.assertIn("verified=93/96", buf.getvalue())

        with mock.patch(
            "fx3_safety.realhw_lock_op_parts_audio_timing_exp_step_and_96gate_guard.evaluate_94gate_preflight",
            return_value=self.clean_dryrun_94,
        ):
            buf_j = io.StringIO()
            with contextlib.redirect_stdout(buf_j):
                rc_j = module_main(
                    ["--force-clean-room", "--simulate-bench-dry-run", "--json"]
                )
            self.assertEqual(rc_j, 0)
            parsed = json.loads(buf_j.getvalue())
            self.assertEqual(parsed["summary"]["verified_gates"], 96)

    def test_67_backward_compatibility_with_94gate_preflight_preserved(self) -> None:
        self.assertEqual(self.active_offline_94.summary["total_gates"], 94)
        self.assertEqual(self.active_offline_94.summary["verified_gates"], 91)
        self.assertEqual(self.clean_dryrun_94.summary["verified_gates"], 94)

    def test_68_env_force_clean_room_truthy_values_recognized(self) -> None:
        for val in ("1", "true", "TRUE", "yes", "YES"):
            with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": val}):
                res = audit_phase249_donor_contracts()
                self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")


if __name__ == "__main__":
    unittest.main()
