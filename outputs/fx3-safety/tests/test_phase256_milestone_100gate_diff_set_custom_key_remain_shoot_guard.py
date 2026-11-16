"""Phase 256 Grand Milestone Dual-Mode Unit Tests (70 tests, < 4s runtime) for
`fx3_safety.realhw_diff_set_still_mv_custom_key_remain_shoot_and_100gate_guard`:

- Gate `G99`: `ILME-FX3` (`Ver. 7.02`) `[Different Set for Still/Mv]` exact 8-item
  catalog (`Aperture`, `Shutter Speed`, `ISO`, `Exposure Comp.`, `Metering Mode`,
  `White Balance`, `Picture Profile`, `Focus Mode`), survival across
  `Camera Settings Reset` + `Reset Network Set.`, asymmetric `Common -> Separate`
  (`Custom White Balance` Still-only) & `Separate -> Common` (`Aperture`,
  `Shutter Speed`, and `Custom White Balance` retain Still values), and `Ver. 7.02`
  `[Shutter Mode] = [Angle]` independence override guard.
- Gate `G100` (`100th` Safety Gate): `ILME-FX3` (`Ver. 7.02`) `[Custom Key/Dial Set.]`
  3-domain keymaps (`Still`/`Movie`/`Playback`), Cinema-Line factory dial defaults
  (`Front dial=Aperture`, `Rear dial=ISO/EI`, `Control Wheel=Shutter Speed`),
  `[Follow Custom]`, `[My Dial 1..3]`, Slot-1 Tier-0 `CAMSET01.DAT` `O_RDONLY`
  load-only firewall, AND `[Remain Shoot Display]` still-buffer-only scope +
  EVF-less `ILME-FX3` (`ilc/2210`) monitor topology guard.
- Unified `100`-Gate Grand Milestone Master Safety Preflight
  (`evaluate_100gate_preflight` / `verify-100-gates`): `97/100` offline awaiting
  physical Tier-0 receipt and `100/100` in `--simulate-bench-dry-run` with all
  hardware write/live-attach redlines hard-locked `False`.
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
from fx3_safety.realhw_diff_set_still_mv_custom_key_remain_shoot_and_100gate_guard import (
    ALLOWED_CAMSET_OPERATIONS_G100,
    ALLOWED_CUSTOM_KEY_CONTROLS_G100,
    ALLOWED_CUSTOM_KEY_DOMAINS_G100,
    ALLOWED_DIFF_SET_TRANSITIONS_G99,
    ALLOWED_LOG_SHOOTING_MODES_G100,
    ALLOWED_MOVIE_SHUTTER_MODES_G99,
    ALLOWED_MY_DIAL_SLOTS_G100,
    ALLOWED_RECALL_CUSTOM_HOLD_SLOTS_G100,
    ALLOWED_REMAIN_SHOOT_DISPLAY_MODES_G100,
    ALLOWED_RESET_ACTIONS_PHASE256,
    CAMSET_DEFAULT_SLOT1_FILENAME_G100,
    CAMSET_OP_LOAD_O_RDONLY_G100,
    CAMSET_OP_NONE_G100,
    CAMSET_OP_SAVE_OVERWRITE_G100,
    CINEMA_LINE_FACTORY_DIAL_DEFAULTS_G100,
    CUSTOM_KEY_DIAL_MENU_PATH_G100,
    CUSTOM_KEY_FOLLOW_CUSTOM_TOKEN_G100,
    CUSTOM_WHITE_BALANCE_VALUES_G99,
    DIFF_SET_FACTORY_CHECKED_ITEMS_G99,
    DIFF_SET_INITIAL_FACTORY_PARAM_DEFAULTS_G99,
    DIFF_SET_ITEM_APERTURE_G99,
    DIFF_SET_ITEM_EXPOSURE_COMP_G99,
    DIFF_SET_ITEM_FOCUS_MODE_G99,
    DIFF_SET_ITEM_ISO_G99,
    DIFF_SET_ITEM_METERING_MODE_G99,
    DIFF_SET_ITEM_PICTURE_PROFILE_G99,
    DIFF_SET_ITEM_SHUTTER_SPEED_G99,
    DIFF_SET_ITEM_WHITE_BALANCE_G99,
    DIFF_SET_SEPARATE_TO_COMMON_STILL_RETAINED_ITEMS_G99,
    DIFF_SET_STILL_MV_EIGHT_ITEMS_G99,
    DIFF_SET_STILL_MV_MENU_PATH_G99,
    DIFF_SET_TRANSITION_COMMON_TO_SEPARATE_G99,
    DIFF_SET_TRANSITION_NONE_G99,
    DIFF_SET_TRANSITION_SEPARATE_TO_COMMON_G99,
    DONOR_CHECK_MAX_SECONDS_PHASE256,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    FX3_ACTIVE_DISPLAY_SURFACE_LCD_G100,
    FX3_DEFAULT_FW_VERSION_PHASE256,
    FX3_HAS_BUILTIN_EVF_G100,
    FX3_HELP_GUIDE_CODE_PHASE256,
    FX3_MIN_SUPPORTED_FW_TUPLE_PHASE256,
    FX3_MODEL_ID,
    FX3_MODEL_NAME,
    FX3_SHUTTER_ANGLE_MIN_FW_TUPLE_G99,
    FX6_MODEL_NAME,
    G99,
    G99_GATE_CODE,
    G99_GATE_ID,
    G100,
    G100_GATE_CODE,
    G100_GATE_ID,
    GATE_G99_DIFF_SET_STILL_MV_8ITEM_TRANSITIONS_AND_SHUTTER_ANGLE_OVERRIDE_GUARD,
    GATE_G100_CUSTOM_KEY_DIAL_ISO_EI_FIREWALL_AND_REMAIN_SHOOT_EVF_LESS_GUARD,
    HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    HUMAN_HARDWARE_ATTACH_TOKEN,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED,
    PHYSICAL_USB_PACKETS_EMITTED,
    PINNED_PHASE256_DONOR_SPECS,
    RAW_FIRMWARE_BYTES_LEAKED,
    REALHW_DIFF_SET_STILL_MV_CUSTOM_KEY_REMAIN_SHOOT_100GATE_SCHEMA,
    REALHW_DIFF_SET_STILL_MV_CUSTOM_KEY_REMAIN_SHOOT_100GATE_VERSION,
    REMAIN_SHOOT_ALWAYS_DISPLAY_G100,
    REMAIN_SHOOT_DISPLAY_MENU_PATH_G100,
    REMAIN_SHOOT_FACTORY_DEFAULT_G100,
    REMAIN_SHOOT_NOT_DISPLAYED_G100,
    REMAIN_SHOOT_SCOPE_STILL_BUFFER_ONLY_G100,
    REMAIN_SHOOT_SHOOT_ONLY_DISPLAY_G100,
    RESET_ACTION_CAMERA_SETTINGS_RESET,
    RESET_ACTION_INITIALIZE,
    RESET_ACTION_NONE,
    RESET_ACTION_RESET_NETWORK_SET_PHASE256,
    SHUTTER_MODE_ANGLE_G99,
    SHUTTER_MODE_MENU_PATH_G99,
    SHUTTER_MODE_SPEED_G99,
    SPI_NOR_WRITE_AUTHORIZED,
    STATUS_BLOCKED_G99_COMMON_TO_SEPARATE_CUSTOM_WB_STILL_ONLY_VIOLATION,
    STATUS_BLOCKED_G99_DIFF_SET_ITEM_CATALOG_OR_RESET_PERSISTENCE_VIOLATION,
    STATUS_BLOCKED_G99_SEPARATE_TO_COMMON_ASYMMETRIC_RETENTION_VIOLATION,
    STATUS_BLOCKED_G99_SHUTTER_ANGLE_COMMON_BLEED_VIOLATION,
    STATUS_BLOCKED_G99_TELEMETRY_INVALID,
    STATUS_BLOCKED_G100_CUSTOM_KEY_DIAL_DOMAIN_OR_ISO_EI_MISMATCH,
    STATUS_BLOCKED_G100_CUSTOM_KEY_RESET_PERSISTENCE_VIOLATION,
    STATUS_BLOCKED_G100_EVF_FINDER_MONITOR_TOPOLOGY_SPOOF_VIOLATION,
    STATUS_BLOCKED_G100_REMAIN_SHOOT_SCOPE_OR_RESET_PERSISTENCE_VIOLATION,
    STATUS_BLOCKED_G100_SLOT1_CUSTOM_KEY_CAMSET01_FIREWALL_VIOLATION,
    STATUS_BLOCKED_G100_TELEMETRY_INVALID,
    STATUS_BLOCKED_PERSISTENT_EMMC_WRITE,
    STATUS_BLOCKED_PHASE256_DONOR_INTEGRITY,
    STATUS_VERIFIED_G99,
    STATUS_VERIFIED_G100,
    USB_PACKETS_TRANSMITTED,
    _norm_camset_filename_g100,
    _norm_camset_op_g100,
    _norm_diff_set_item_g99,
    _norm_diff_set_transition_g99,
    _norm_log_shooting_mode_g100,
    _norm_movie_shutter_mode_g99,
    _norm_my_dial_slot_g100,
    _norm_recall_custom_hold_slot_g100,
    _norm_remain_shoot_display_g100,
    _norm_reset_action_phase256,
    _read_file_o_rdonly,
    audit_phase256_donor_contracts,
    evaluate_100_master_safety_gates,
    evaluate_100gate_preflight,
    evaluate_g99_diff_set_still_mv_and_shutter_angle_guard,
    evaluate_g100_custom_key_dial_and_remain_shoot_guard,
    main as module_main,
    resolve_fx3_custom_key_dial_and_remain_shoot_state,
    resolve_fx3_diff_set_still_mv_and_shutter_angle_state,
    run_100_gate_preflight,
    verify_custom_key_dial_iso_ei_and_remain_shoot_guard,
    verify_diff_set_still_mv_and_shutter_angle_guard,
)


class TestPhase256Milestone100GateDiffSetCustomKeyRemainShootGuard(unittest.TestCase):
    """70 fast dual-mode tests covering Gates G99, G100, and unified 100-Gate preflight (< 4s)."""

    @classmethod
    def setUpClass(cls) -> None:
        # Cache upstream 98-gate and 100-gate preflight evaluations once so all 70
        # tests execute well under < 4s in both LOCAL_DONOR_O_RDONLY and
        # FX3_FX6_FORCE_CLEAN_ROOM=1 modes.
        cls.active_offline_98 = fx3_safety.evaluate_98gate_preflight()
        cls.active_offline_100 = evaluate_100gate_preflight(
            master_98_override=cls.active_offline_98
        )
        if cls.active_offline_98.clean_room_forced:
            cls.clean_offline_98 = cls.active_offline_98
        else:
            with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
                cls.clean_offline_98 = fx3_safety.evaluate_98gate_preflight(
                    force_clean_room=True
                )
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            cls.clean_dryrun_98 = fx3_safety.evaluate_98gate_preflight(
                force_clean_room=True, dry_run_simulated=True
            )
            cls.clean_offline_100 = evaluate_100gate_preflight(
                force_clean_room=True, master_98_override=cls.clean_offline_98
            )
            cls.clean_dryrun_100 = evaluate_100gate_preflight(
                force_clean_room=True,
                simulate_bench_dry_run=True,
                master_98_override=cls.clean_dryrun_98,
            )

    # ------------------------------------------------------------------
    # Section A: Schema, Exports & O_RDONLY / Clean-Room Donor Audit (01..14)
    # ------------------------------------------------------------------

    def test_01_schema_version_gate_ids_and_redline_constants(self) -> None:
        self.assertEqual(
            REALHW_DIFF_SET_STILL_MV_CUSTOM_KEY_REMAIN_SHOOT_100GATE_SCHEMA,
            "realhw_diff_set_still_mv_custom_key_remain_shoot_and_100gate_guard_v1",
        )
        self.assertEqual(
            REALHW_DIFF_SET_STILL_MV_CUSTOM_KEY_REMAIN_SHOOT_100GATE_VERSION, "1.0.0"
        )
        self.assertEqual(G99, G99_GATE_ID)
        self.assertEqual(G100, G100_GATE_ID)
        self.assertEqual(
            GATE_G99_DIFF_SET_STILL_MV_8ITEM_TRANSITIONS_AND_SHUTTER_ANGLE_OVERRIDE_GUARD,
            G99_GATE_CODE,
        )
        self.assertEqual(
            GATE_G100_CUSTOM_KEY_DIAL_ISO_EI_FIREWALL_AND_REMAIN_SHOOT_EVF_LESS_GUARD,
            G100_GATE_CODE,
        )
        self.assertFalse(HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        self.assertFalse(HUMAN_HARDWARE_ATTACH_TOKEN)
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(PERSISTENT_WRITE_RELEASE)
        self.assertFalse(SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        self.assertFalse(PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED)
        self.assertFalse(FX3_HAS_BUILTIN_EVF_G100)
        self.assertEqual(USB_PACKETS_TRANSMITTED, 0)
        self.assertEqual(PHYSICAL_USB_PACKETS_EMITTED, 0)
        self.assertEqual(RAW_FIRMWARE_BYTES_LEAKED, 0)

    def test_02_top_level_package_exports_all_phase256_symbols_unshadowed(self) -> None:
        mod = fx3_safety.realhw_diff_set_still_mv_custom_key_remain_shoot_and_100gate_guard
        self.assertEqual(fx3_safety.__all__.count(mod.__name__.split(".")[-1]), 1)
        for sym in (
            "G99",
            "G100",
            "G99_GATE_ID",
            "G100_GATE_ID",
            "Master100GateReport",
            "evaluate_100gate_preflight",
            "run_100_gate_preflight",
            "evaluate_100_master_safety_gates",
            "verify_diff_set_still_mv_and_shutter_angle_guard",
            "verify_custom_key_dial_iso_ei_and_remain_shoot_guard",
        ):
            self.assertEqual(fx3_safety.__all__.count(sym), 1)
            self.assertIs(getattr(fx3_safety, sym), getattr(mod, sym))

    def test_03_pinned_phase256_donor_specs_cover_fx3_and_fx6_contracts(self) -> None:
        self.assertEqual(len(PINNED_PHASE256_DONOR_SPECS), 6)
        bodies = {spec[0] for spec in PINNED_PHASE256_DONOR_SPECS.values()}
        self.assertEqual(bodies, {"FX3", "FX6"})
        self.assertLessEqual(DONOR_CHECK_MAX_SECONDS_PHASE256, 0.10)

    def test_04_donor_audit_active_mode_within_100ms_and_zero_leaked_bytes(
        self,
    ) -> None:
        audit = audit_phase256_donor_contracts()
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
        audit = audit_phase256_donor_contracts(force_clean_room=True)
        self.assertTrue(audit.valid)
        self.assertEqual(audit.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(audit.access_mode, "SYNTHETIC_CLEAN_ROOM")
        self.assertEqual(audit.files_inspected, 0)
        self.assertEqual(len(audit.checked_markers), 6)
        self.assertEqual(audit.missing_markers, ())

    def test_06_donor_audit_missing_work_root_falls_back_to_clean_room(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            audit = audit_phase256_donor_contracts(
                work_root=Path(tmp) / "nonexistent", force_clean_room=False
            )
            self.assertTrue(audit.valid)
            self.assertEqual(audit.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_07_donor_audit_corrupted_sha256_blocks_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for _k, (_body, rel, _sz, _sha, markers, _lbl) in (
                PINNED_PHASE256_DONOR_SPECS.items()
            ):
                fp = root / rel
                fp.parent.mkdir(parents=True, exist_ok=True)
                fp.write_bytes(b"".join(markers) + b"corrupt")
            audit = audit_phase256_donor_contracts(
                work_root=root, force_clean_room=False
            )
            self.assertFalse(audit.valid)
            self.assertEqual(audit.status, STATUS_BLOCKED_PHASE256_DONOR_INTEGRITY)

    def test_08_donor_audit_missing_marker_bytes_blocks_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for _k, (_body, rel, _sz, _sha, _markers, _lbl) in (
                PINNED_PHASE256_DONOR_SPECS.items()
            ):
                fp = root / rel
                fp.parent.mkdir(parents=True, exist_ok=True)
                fp.write_bytes(b"empty_without_markers")
            audit = audit_phase256_donor_contracts(
                work_root=root, force_clean_room=False
            )
            self.assertFalse(audit.valid)
            self.assertEqual(len(audit.missing_markers), 6)
            self.assertEqual(audit.status, STATUS_BLOCKED_PHASE256_DONOR_INTEGRITY)

    def test_09_donor_audit_budget_exceeded_blocks_fail_closed(self) -> None:
        audit = audit_phase256_donor_contracts(
            force_clean_room=True, max_budget_seconds=0.0
        )
        self.assertFalse(audit.valid)
        self.assertEqual(audit.status, STATUS_BLOCKED_PHASE256_DONOR_INTEGRITY)

    def test_10_read_file_o_rdonly_strictly_uses_os_o_rdonly_flags(self) -> None:
        with tempfile.NamedTemporaryFile(delete=False) as tf:
            tf.write(b"fx3_phase256_rdonly_probe")
            probe_path = Path(tf.name)
        try:
            real_open = os.open
            captured_flags = []

            def spy_open(p: str, flags: int, *args: object) -> int:
                captured_flags.append(flags)
                return real_open(p, flags, *args)

            with mock.patch("os.open", side_effect=spy_open):
                blob = _read_file_o_rdonly(probe_path)
            self.assertEqual(blob, b"fx3_phase256_rdonly_probe")
            self.assertEqual(captured_flags, [os.O_RDONLY | getattr(os, "O_BINARY", 0)])
        finally:
            probe_path.unlink(missing_ok=True)

    def test_11_env_force_clean_room_truthy_values_recognized(self) -> None:
        for val in ("1", "true", "TRUE", "yes", "YES"):
            with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": val}):
                res = audit_phase256_donor_contracts()
                self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_12_reset_action_normalizer_handles_all_four_canonical_modes(self) -> None:
        self.assertEqual(ALLOWED_RESET_ACTIONS_PHASE256[0], RESET_ACTION_NONE)
        self.assertEqual(_norm_reset_action_phase256(""), RESET_ACTION_NONE)
        self.assertEqual(
            _norm_reset_action_phase256("[Camera Settings Reset]"),
            RESET_ACTION_CAMERA_SETTINGS_RESET,
        )
        self.assertEqual(
            _norm_reset_action_phase256("Reset Network Set"),
            RESET_ACTION_RESET_NETWORK_SET_PHASE256,
        )
        self.assertEqual(
            _norm_reset_action_phase256("[Initialize]"), RESET_ACTION_INITIALIZE
        )
        self.assertIsNone(_norm_reset_action_phase256("Factory Wipe Unknown"))

    def test_13_diff_set_item_and_transition_normalizers_handle_variants(self) -> None:
        self.assertEqual(
            _norm_diff_set_item_g99("[Exposure Comp]"), DIFF_SET_ITEM_EXPOSURE_COMP_G99
        )
        self.assertEqual(
            _norm_diff_set_item_g99("shutter_speed"), DIFF_SET_ITEM_SHUTTER_SPEED_G99
        )
        self.assertIsNone(_norm_diff_set_item_g99("Drive Mode"))
        self.assertEqual(
            _norm_diff_set_transition_g99("Common -> Separate"),
            DIFF_SET_TRANSITION_COMMON_TO_SEPARATE_G99,
        )
        self.assertEqual(
            _norm_diff_set_transition_g99("Separate -> Common"),
            DIFF_SET_TRANSITION_SEPARATE_TO_COMMON_G99,
        )
        self.assertEqual(
            _norm_movie_shutter_mode_g99("[Shutter Angle]"), SHUTTER_MODE_ANGLE_G99
        )
        self.assertEqual(
            _norm_movie_shutter_mode_g99("Shutter Speed"), SHUTTER_MODE_SPEED_G99
        )

    def test_14_custom_key_and_remain_shoot_normalizers_handle_variants(self) -> None:
        self.assertEqual(_norm_log_shooting_mode_g100("[Cine EI Quick]"), "Cine EI Quick")
        self.assertEqual(_norm_my_dial_slot_g100("[My Dial 2]"), "My Dial 2")
        self.assertEqual(
            _norm_recall_custom_hold_slot_g100("Recall Custom hold 3"),
            "Recall Custom hold 3",
        )
        self.assertEqual(_norm_camset_op_g100("LOAD"), CAMSET_OP_LOAD_O_RDONLY_G100)
        self.assertEqual(_norm_camset_filename_g100("camset10.dat"), "CAMSET10.DAT")
        self.assertIsNone(_norm_camset_filename_g100("CAMSET11.DAT"))
        self.assertEqual(
            _norm_remain_shoot_display_g100("[Shoot-Only Display]"),
            REMAIN_SHOOT_SHOOT_ONLY_DISPLAY_G100,
        )


    # ------------------------------------------------------------------
    # Section B: Gate G99 — [Different Set for Still/Mv] & Shutter Angle (15..34)
    # ------------------------------------------------------------------

    def test_15_g99_default_pass_and_verdict_contract(self) -> None:
        verdict, res = evaluate_g99_diff_set_still_mv_and_shutter_angle_guard(
            force_clean_room=True
        )
        self.assertTrue(verdict.passed)
        self.assertTrue(res.valid)
        self.assertEqual(verdict.gate_id, G99_GATE_ID)
        self.assertEqual(verdict.gate_code, G99_GATE_CODE)
        self.assertEqual(res.status, STATUS_VERIFIED_G99)
        self.assertFalse(res.persistent_emmc_writes_authorized)
        self.assertEqual(res.raw_firmware_bytes_leaked, 0)
        self.assertEqual(
            res.diff_set_still_mv_guard["diff_set_transition_corruption_events"], 0
        )
        self.assertEqual(
            res.diff_set_still_mv_guard["shutter_angle_common_bleed_events"], 0
        )

    def test_16_g99_exact_eight_items_catalog_order_and_factory_defaults(self) -> None:
        self.assertEqual(
            DIFF_SET_STILL_MV_MENU_PATH_G99,
            "MENU -> Setup -> [Operation Customize] -> [Different Set for Still/Mv]",
        )
        self.assertEqual(
            DIFF_SET_STILL_MV_EIGHT_ITEMS_G99,
            (
                DIFF_SET_ITEM_APERTURE_G99,
                DIFF_SET_ITEM_SHUTTER_SPEED_G99,
                DIFF_SET_ITEM_ISO_G99,
                DIFF_SET_ITEM_EXPOSURE_COMP_G99,
                DIFF_SET_ITEM_METERING_MODE_G99,
                DIFF_SET_ITEM_WHITE_BALANCE_G99,
                DIFF_SET_ITEM_PICTURE_PROFILE_G99,
                DIFF_SET_ITEM_FOCUS_MODE_G99,
            ),
        )
        self.assertEqual(DIFF_SET_FACTORY_CHECKED_ITEMS_G99, ())
        self.assertEqual(len(DIFF_SET_INITIAL_FACTORY_PARAM_DEFAULTS_G99), 8)
        self.assertEqual(
            DIFF_SET_SEPARATE_TO_COMMON_STILL_RETAINED_ITEMS_G99,
            ("Aperture", "Shutter Speed"),
        )
        self.assertIn("Custom White Balance", CUSTOM_WHITE_BALANCE_VALUES_G99)
        self.assertEqual(len(ALLOWED_DIFF_SET_TRANSITIONS_G99), 3)
        self.assertEqual(len(ALLOWED_MOVIE_SHUTTER_MODES_G99), 2)

    def test_17_g99_unknown_ninth_item_rejected_fail_closed(self) -> None:
        r = verify_diff_set_still_mv_and_shutter_angle_guard(
            pre_reset_checked_items=("Aperture", "Audio Rec Level")
        )
        self.assertFalse(r.valid)
        self.assertEqual(
            r.status,
            STATUS_BLOCKED_G99_DIFF_SET_ITEM_CATALOG_OR_RESET_PERSISTENCE_VIOLATION,
        )

    def test_18_g99_survives_camera_settings_reset(self) -> None:
        checked = DIFF_SET_STILL_MV_EIGHT_ITEMS_G99
        r = verify_diff_set_still_mv_and_shutter_angle_guard(
            pre_reset_checked_items=checked,
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
            observed_post_reset_checked_items=checked,
        )
        self.assertTrue(r.valid)
        self.assertEqual(r.effective_post_reset_checked_items, checked)
        self.assertTrue(r.diff_set_survives_camera_settings_reset)

    def test_19_g99_survives_reset_network_set(self) -> None:
        checked = ("Aperture", "ISO", "Focus Mode")
        r = verify_diff_set_still_mv_and_shutter_angle_guard(
            pre_reset_checked_items=checked,
            reset_action=RESET_ACTION_RESET_NETWORK_SET_PHASE256,
            observed_post_reset_checked_items=checked,
        )
        self.assertTrue(r.valid)
        self.assertEqual(r.effective_post_reset_checked_items, checked)
        self.assertTrue(r.diff_set_survives_reset_network_set)

    def test_20_g99_reset_to_unchecked_factory_default_by_initialize(self) -> None:
        r = verify_diff_set_still_mv_and_shutter_angle_guard(
            pre_reset_checked_items=DIFF_SET_STILL_MV_EIGHT_ITEMS_G99,
            reset_action=RESET_ACTION_INITIALIZE,
            observed_post_reset_checked_items=(),
        )
        self.assertTrue(r.valid)
        self.assertEqual(r.effective_post_reset_checked_items, ())
        self.assertTrue(r.diff_set_reset_only_by_initialize)

    def test_21_g99_post_reset_drift_under_camera_settings_reset_blocks(self) -> None:
        r = verify_diff_set_still_mv_and_shutter_angle_guard(
            pre_reset_checked_items=("Aperture", "ISO"),
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
            observed_post_reset_checked_items=(),
        )
        self.assertFalse(r.valid)
        self.assertEqual(
            r.status,
            STATUS_BLOCKED_G99_DIFF_SET_ITEM_CATALOG_OR_RESET_PERSISTENCE_VIOLATION,
        )

    def test_22_g99_post_reset_drift_under_initialize_blocks(self) -> None:
        r = verify_diff_set_still_mv_and_shutter_angle_guard(
            pre_reset_checked_items=("Aperture", "ISO"),
            reset_action=RESET_ACTION_INITIALIZE,
            observed_post_reset_checked_items=("Aperture",),
        )
        self.assertFalse(r.valid)
        self.assertEqual(
            r.status,
            STATUS_BLOCKED_G99_DIFF_SET_ITEM_CATALOG_OR_RESET_PERSISTENCE_VIOLATION,
        )

    def test_23_g99_common_to_separate_copies_standard_items_to_still_and_movie(
        self,
    ) -> None:
        common = {
            "Aperture": "F2.8",
            "Shutter Speed": "1/60",
            "ISO": "ISO 1600",
            "Exposure Comp.": "+0.3EV",
            "Metering Mode": "Center",
            "White Balance": "5600K",
            "Picture Profile": "PP11",
            "Focus Mode": "AF-S",
        }
        r = verify_diff_set_still_mv_and_shutter_angle_guard(
            transition_mode=DIFF_SET_TRANSITION_COMMON_TO_SEPARATE_G99,
            common_values=common,
            observed_post_transition_still_values=common,
            observed_post_transition_movie_values=common,
        )
        self.assertTrue(r.valid)
        self.assertEqual(r.expected_post_transition_still_values, common)
        self.assertEqual(r.expected_post_transition_movie_values, common)
        self.assertEqual(r.diff_set_transition_corruption_events, 0)

    def test_24_g99_common_to_separate_keeps_custom_wb_still_only(self) -> None:
        common = {
            "Aperture": "F2.8",
            "Shutter Speed": "1/100",
            "ISO": "ISO 800",
            "Exposure Comp.": "0.0EV",
            "Metering Mode": "Multi",
            "White Balance": "Custom White Balance",
            "Picture Profile": "PP11",
            "Focus Mode": "AF-C",
        }
        r = verify_diff_set_still_mv_and_shutter_angle_guard(
            transition_mode=DIFF_SET_TRANSITION_COMMON_TO_SEPARATE_G99,
            common_values=common,
            movie_fallback_white_balance="Auto",
        )
        self.assertTrue(r.valid)
        self.assertEqual(
            r.expected_post_transition_still_values["White Balance"],
            "Custom White Balance",
        )
        self.assertEqual(
            r.expected_post_transition_movie_values["White Balance"], "Auto"
        )
        self.assertTrue(r.custom_wb_still_only_enforced)

    def test_25_g99_common_to_separate_custom_wb_leaked_to_movie_blocks(self) -> None:
        common = {"White Balance": "Custom 1"}
        r = verify_diff_set_still_mv_and_shutter_angle_guard(
            transition_mode=DIFF_SET_TRANSITION_COMMON_TO_SEPARATE_G99,
            common_values=common,
            observed_post_transition_movie_values={"White Balance": "Custom 1"},
        )
        self.assertFalse(r.valid)
        self.assertEqual(
            r.status, STATUS_BLOCKED_G99_COMMON_TO_SEPARATE_CUSTOM_WB_STILL_ONLY_VIOLATION
        )
        self.assertGreater(r.diff_set_transition_corruption_events, 0)

    def test_26_g99_common_to_separate_still_register_mismatch_blocks(self) -> None:
        r = verify_diff_set_still_mv_and_shutter_angle_guard(
            transition_mode=DIFF_SET_TRANSITION_COMMON_TO_SEPARATE_G99,
            common_values={"ISO": "ISO 3200"},
            observed_post_transition_still_values={"ISO": "ISO 100"},
        )
        self.assertFalse(r.valid)
        self.assertEqual(
            r.status, STATUS_BLOCKED_G99_COMMON_TO_SEPARATE_CUSTOM_WB_STILL_ONLY_VIOLATION
        )

    def test_27_g99_separate_to_common_retains_still_aperture_shutter_and_custom_wb(
        self,
    ) -> None:
        sep_still = {
            "Aperture": "F1.4",
            "Shutter Speed": "1/500",
            "ISO": "ISO 640",
            "Exposure Comp.": "+1.0EV",
            "Metering Mode": "Highlight",
            "White Balance": "Custom White Balance",
            "Picture Profile": "PP8",
            "Focus Mode": "DMF",
        }
        r = verify_diff_set_still_mv_and_shutter_angle_guard(
            transition_mode=DIFF_SET_TRANSITION_SEPARATE_TO_COMMON_G99,
            separate_still_values=sep_still,
        )
        self.assertTrue(r.valid)
        exp = r.expected_post_transition_common_values
        self.assertEqual(exp["Aperture"], "F1.4")
        self.assertEqual(exp["Shutter Speed"], "1/500")
        self.assertEqual(exp["White Balance"], "Custom White Balance")
        self.assertEqual(exp["ISO"], "ISO AUTO")
        self.assertEqual(exp["Exposure Comp."], "0.0EV")
        self.assertEqual(exp["Metering Mode"], "Multi")
        self.assertEqual(exp["Picture Profile"], "Off")
        self.assertEqual(exp["Focus Mode"], "AF-C")

    def test_28_g99_separate_to_common_resets_non_custom_wb_and_other_five_items(
        self,
    ) -> None:
        state = resolve_fx3_diff_set_still_mv_and_shutter_angle_state(
            transition_mode=DIFF_SET_TRANSITION_SEPARATE_TO_COMMON_G99,
            separate_still_values={
                "Aperture": "F2.0",
                "Shutter Speed": "1/1000",
                "White Balance": "Daylight",
                "ISO": "ISO 3200",
            },
        )
        common = state["expected_post_transition_common_values"]
        self.assertEqual(common["Aperture"], "F2.0")
        self.assertEqual(common["Shutter Speed"], "1/1000")
        self.assertEqual(common["White Balance"], "Auto")
        self.assertEqual(common["ISO"], "ISO AUTO")

    def test_29_g99_separate_to_common_retaining_movie_iso_or_pp_blocks(self) -> None:
        r = verify_diff_set_still_mv_and_shutter_angle_guard(
            transition_mode=DIFF_SET_TRANSITION_SEPARATE_TO_COMMON_G99,
            observed_post_transition_common_values={"ISO": "ISO 12800"},
        )
        self.assertFalse(r.valid)
        self.assertEqual(
            r.status,
            STATUS_BLOCKED_G99_SEPARATE_TO_COMMON_ASYMMETRIC_RETENTION_VIOLATION,
        )
        self.assertGreater(r.diff_set_transition_corruption_events, 0)

    def test_30_g99_separate_to_common_losing_still_aperture_or_custom_wb_blocks(
        self,
    ) -> None:
        r = verify_diff_set_still_mv_and_shutter_angle_guard(
            transition_mode=DIFF_SET_TRANSITION_SEPARATE_TO_COMMON_G99,
            separate_still_values={
                "Aperture": "F2.8",
                "White Balance": "Custom White Balance",
            },
            observed_post_transition_common_values={
                "Aperture": "F4.0",
                "White Balance": "Auto",
            },
        )
        self.assertFalse(r.valid)
        self.assertEqual(
            r.status,
            STATUS_BLOCKED_G99_SEPARATE_TO_COMMON_ASYMMETRIC_RETENTION_VIOLATION,
        )

    def test_31_g99_shutter_mode_angle_overrides_unchecked_common_shutter_speed(
        self,
    ) -> None:
        self.assertEqual(SHUTTER_MODE_MENU_PATH_G99, "MENU -> Exposure/Color -> [Shutter/Silent] -> [Shutter Mode]")
        r = verify_diff_set_still_mv_and_shutter_angle_guard(
            pre_reset_checked_items=("ISO",),  # Shutter Speed unchecked (Common)
            movie_shutter_mode=SHUTTER_MODE_ANGLE_G99,
            still_shutter_speed="1/500",
            movie_shutter_angle_deg=172.8,
            observed_still_shutter_speed="1/500",
            observed_movie_shutter_angle_deg=172.8,
            observed_shutter_still_movie_independent=True,
        )
        self.assertTrue(r.valid)
        self.assertFalse(r.shutter_speed_checked_separate)
        self.assertTrue(r.shutter_angle_override_active)
        self.assertTrue(r.effective_shutter_still_movie_independent)
        self.assertEqual(r.shutter_angle_common_bleed_events, 0)

    def test_32_g99_shutter_mode_angle_bleed_or_coupling_blocks_fail_closed(
        self,
    ) -> None:
        r_coupled = verify_diff_set_still_mv_and_shutter_angle_guard(
            pre_reset_checked_items=(),
            movie_shutter_mode=SHUTTER_MODE_ANGLE_G99,
            observed_shutter_still_movie_independent=False,
        )
        self.assertFalse(r_coupled.valid)
        self.assertEqual(
            r_coupled.status, STATUS_BLOCKED_G99_SHUTTER_ANGLE_COMMON_BLEED_VIOLATION
        )

        r_bleed = verify_diff_set_still_mv_and_shutter_angle_guard(
            movie_shutter_mode=SHUTTER_MODE_ANGLE_G99,
            still_shutter_speed="1/250",
            observed_still_shutter_speed="1/48",
        )
        self.assertFalse(r_bleed.valid)
        self.assertEqual(
            r_bleed.status, STATUS_BLOCKED_G99_SHUTTER_ANGLE_COMMON_BLEED_VIOLATION
        )

    def test_33_g99_shutter_mode_angle_pre_v600_firmware_or_invalid_angle_blocks(
        self,
    ) -> None:
        self.assertEqual(FX3_SHUTTER_ANGLE_MIN_FW_TUPLE_G99, (6, 0))
        r_fw = verify_diff_set_still_mv_and_shutter_angle_guard(
            firmware_version="5.00", movie_shutter_mode=SHUTTER_MODE_ANGLE_G99
        )
        self.assertFalse(r_fw.valid)
        self.assertEqual(
            r_fw.status, STATUS_BLOCKED_G99_SHUTTER_ANGLE_COMMON_BLEED_VIOLATION
        )

        r_ang = verify_diff_set_still_mv_and_shutter_angle_guard(
            movie_shutter_mode=SHUTTER_MODE_ANGLE_G99, movie_shutter_angle_deg=720.0
        )
        self.assertFalse(r_ang.valid)
        self.assertEqual(
            r_ang.status, STATUS_BLOCKED_G99_SHUTTER_ANGLE_COMMON_BLEED_VIOLATION
        )

    def test_34_g99_shutter_mode_speed_follows_checked_vs_unchecked_and_emmc_block(
        self,
    ) -> None:
        r_common = verify_diff_set_still_mv_and_shutter_angle_guard(
            pre_reset_checked_items=("ISO",),
            movie_shutter_mode=SHUTTER_MODE_SPEED_G99,
            observed_shutter_still_movie_independent=False,
        )
        self.assertTrue(r_common.valid)
        self.assertFalse(r_common.effective_shutter_still_movie_independent)

        r_bad_tel = verify_diff_set_still_mv_and_shutter_angle_guard(
            body_model_id=0xCAFEBABE
        )
        self.assertFalse(r_bad_tel.valid)
        self.assertEqual(r_bad_tel.status, STATUS_BLOCKED_G99_TELEMETRY_INVALID)

        verdict, res = evaluate_g99_diff_set_still_mv_and_shutter_angle_guard(
            force_clean_room=True, request_persistent_emmc_writes=True
        )
        self.assertFalse(verdict.passed)
        self.assertEqual(res.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)


    # ------------------------------------------------------------------
    # Section C: Gate G100 (100th Milestone) — Custom Key/Dial & Remain Shoot (35..54)
    # ------------------------------------------------------------------

    def test_35_g100_default_pass_and_100th_milestone_verdict_contract(self) -> None:
        verdict, res = evaluate_g100_custom_key_dial_and_remain_shoot_guard(
            force_clean_room=True
        )
        self.assertTrue(verdict.passed)
        self.assertTrue(res.valid)
        self.assertEqual(verdict.gate_id, G100_GATE_ID)
        self.assertEqual(verdict.gate_code, G100_GATE_CODE)
        self.assertEqual(res.status, STATUS_VERIFIED_G100)
        self.assertFalse(res.persistent_emmc_writes_authorized)
        self.assertEqual(res.raw_firmware_bytes_leaked, 0)
        guard = res.custom_key_remain_shoot_guard
        self.assertEqual(guard["slot1_custom_key_vault_mutation_bytes"], 0)
        self.assertFalse(guard["fx3_has_builtin_evf"])
        self.assertEqual(guard["evf_finder_monitor_spoof_events"], 0)

    def test_36_g100_cinema_line_factory_dial_defaults_aperture_iso_ei_shutter(
        self,
    ) -> None:
        self.assertEqual(
            CUSTOM_KEY_DIAL_MENU_PATH_G100,
            "MENU -> Setup -> [Operation Customize] -> [Custom Key/Dial Set.]",
        )
        self.assertEqual(ALLOWED_CUSTOM_KEY_DOMAINS_G100, ("Still", "Movie", "Playback"))
        self.assertEqual(len(ALLOWED_CUSTOM_KEY_CONTROLS_G100), 11)
        self.assertEqual(
            CINEMA_LINE_FACTORY_DIAL_DEFAULTS_G100,
            {
                "Front dial": "Aperture",
                "Rear dial": "ISO/EI",
                "Control Wheel": "Shutter Speed",
            },
        )

    def test_37_g100_rear_dial_iso_ei_auto_adapts_between_iso_and_cine_ei(self) -> None:
        self.assertEqual(len(ALLOWED_LOG_SHOOTING_MODES_G100), 4)
        for mode, exp_target in (
            ("Off", "ISO"),
            ("Flexible ISO", "ISO"),
            ("Cine EI Quick", "Exposure Index (EI)"),
            ("Cine EI", "Exposure Index (EI)"),
        ):
            r = verify_custom_key_dial_iso_ei_and_remain_shoot_guard(
                log_shooting_mode=mode, observed_rear_dial_target=exp_target
            )
            self.assertTrue(r.valid)
            self.assertEqual(r.effective_rear_dial_target, exp_target)

    def test_38_g100_rear_dial_iso_ei_mismatch_blocks_fail_closed(self) -> None:
        r = verify_custom_key_dial_iso_ei_and_remain_shoot_guard(
            log_shooting_mode="Cine EI", observed_rear_dial_target="ISO"
        )
        self.assertFalse(r.valid)
        self.assertEqual(
            r.status, STATUS_BLOCKED_G100_CUSTOM_KEY_DIAL_DOMAIN_OR_ISO_EI_MISMATCH
        )

    def test_39_g100_follow_custom_movie_inherits_still_assignments(self) -> None:
        state = resolve_fx3_custom_key_dial_and_remain_shoot_state(
            still_custom_keymap={"Custom Button 1": "Focus Magnifier"},
            movie_custom_keymap={
                "Custom Button 1": CUSTOM_KEY_FOLLOW_CUSTOM_TOKEN_G100
            },
        )
        self.assertEqual(
            state["resolved_movie_custom_keymap"]["Custom Button 1"],
            "Focus Magnifier",
        )
        self.assertIn("Custom Button 1", state["follow_custom_inherited_controls"])

    def test_40_g100_follow_custom_in_still_or_playback_or_wrong_inheritance_blocks(
        self,
    ) -> None:
        r_still = verify_custom_key_dial_iso_ei_and_remain_shoot_guard(
            still_custom_keymap={
                "Custom Button 1": CUSTOM_KEY_FOLLOW_CUSTOM_TOKEN_G100
            }
        )
        self.assertFalse(r_still.valid)
        self.assertEqual(
            r_still.status,
            STATUS_BLOCKED_G100_CUSTOM_KEY_DIAL_DOMAIN_OR_ISO_EI_MISMATCH,
        )

        r_inh = verify_custom_key_dial_iso_ei_and_remain_shoot_guard(
            still_custom_keymap={"Custom Button 1": "White Balance"},
            movie_custom_keymap={
                "Custom Button 1": CUSTOM_KEY_FOLLOW_CUSTOM_TOKEN_G100
            },
            observed_resolved_movie_keymap={"Custom Button 1": "Zebra Display Select"},
        )
        self.assertFalse(r_inh.valid)
        self.assertEqual(
            r_inh.status, STATUS_BLOCKED_G100_CUSTOM_KEY_DIAL_DOMAIN_OR_ISO_EI_MISMATCH
        )

    def test_41_g100_my_dial_1_to_3_and_recall_custom_hold_1_to_3_supported(
        self,
    ) -> None:
        self.assertEqual(len(ALLOWED_MY_DIAL_SLOTS_G100), 4)
        self.assertEqual(len(ALLOWED_RECALL_CUSTOM_HOLD_SLOTS_G100), 4)
        for slot, hold in zip(
            ("My Dial 1", "My Dial 2", "My Dial 3"),
            ("Recall Custom hold 1", "Recall Custom hold 2", "Recall Custom hold 3"),
        ):
            r = verify_custom_key_dial_iso_ei_and_remain_shoot_guard(
                active_my_dial_slot=slot, active_recall_custom_hold_slot=hold
            )
            self.assertTrue(r.valid)
            self.assertEqual(r.active_my_dial_slot, slot)
            self.assertEqual(r.active_recall_custom_hold_slot, hold)

    def test_42_g100_invalid_my_dial_or_domain_catalog_blocks(self) -> None:
        r_slot = verify_custom_key_dial_iso_ei_and_remain_shoot_guard(
            active_my_dial_slot="My Dial 4"
        )
        self.assertFalse(r_slot.valid)
        self.assertEqual(
            r_slot.status, STATUS_BLOCKED_G100_CUSTOM_KEY_DIAL_DOMAIN_OR_ISO_EI_MISMATCH
        )

        r_dom = verify_custom_key_dial_iso_ei_and_remain_shoot_guard(
            supported_domains=("Still", "Movie")
        )
        self.assertFalse(r_dom.valid)
        self.assertEqual(
            r_dom.status, STATUS_BLOCKED_G100_CUSTOM_KEY_DIAL_DOMAIN_OR_ISO_EI_MISMATCH
        )

    def test_43_g100_custom_key_survives_camera_settings_reset_and_network_reset(
        self,
    ) -> None:
        custom_dials = {
            "Front dial": "Exposure Comp.",
            "Rear dial": "ISO/EI",
            "Control Wheel": "Aperture",
        }
        for rst in (
            RESET_ACTION_CAMERA_SETTINGS_RESET,
            RESET_ACTION_RESET_NETWORK_SET_PHASE256,
        ):
            r = verify_custom_key_dial_iso_ei_and_remain_shoot_guard(
                pre_reset_dial_assignments=custom_dials,
                reset_action=rst,
                observed_post_reset_dial_assignments=custom_dials,
                observed_post_reset_custom_keys_preserved=True,
            )
            self.assertTrue(r.valid)
            self.assertEqual(r.effective_post_reset_dial_assignments, custom_dials)

    def test_44_g100_custom_key_restored_to_factory_by_initialize_and_drift_blocks(
        self,
    ) -> None:
        custom_dials = {
            "Front dial": "Exposure Comp.",
            "Rear dial": "Aperture",
            "Control Wheel": "ISO",
        }
        r_init = verify_custom_key_dial_iso_ei_and_remain_shoot_guard(
            pre_reset_dial_assignments=custom_dials,
            reset_action=RESET_ACTION_INITIALIZE,
            observed_post_reset_dial_assignments=CINEMA_LINE_FACTORY_DIAL_DEFAULTS_G100,
            observed_post_reset_custom_keys_preserved=False,
        )
        self.assertTrue(r_init.valid)

        r_drift = verify_custom_key_dial_iso_ei_and_remain_shoot_guard(
            pre_reset_dial_assignments=custom_dials,
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
            observed_post_reset_dial_assignments=CINEMA_LINE_FACTORY_DIAL_DEFAULTS_G100,
        )
        self.assertFalse(r_drift.valid)
        self.assertEqual(
            r_drift.status, STATUS_BLOCKED_G100_CUSTOM_KEY_RESET_PERSISTENCE_VIOLATION
        )

    def test_45_g100_slot1_camset01_o_rdonly_load_allowed_camset01_through_10(
        self,
    ) -> None:
        self.assertEqual(CAMSET_DEFAULT_SLOT1_FILENAME_G100, "CAMSET01.DAT")
        self.assertEqual(
            ALLOWED_CAMSET_OPERATIONS_G100,
            (CAMSET_OP_NONE_G100, CAMSET_OP_LOAD_O_RDONLY_G100, CAMSET_OP_SAVE_OVERWRITE_G100),
        )
        for idx in range(1, 11):
            fn = f"CAMSET{idx:02d}.DAT"
            r = verify_custom_key_dial_iso_ei_and_remain_shoot_guard(
                slot1_camset_filename=fn,
                slot1_camset_operation=CAMSET_OP_LOAD_O_RDONLY_G100,
                slot1_open_flags=os.O_RDONLY,
            )
            self.assertTrue(r.valid)
            self.assertEqual(r.slot1_camset_filename, fn)
            self.assertEqual(r.slot1_custom_key_vault_mutation_bytes, 0)

    def test_46_g100_slot1_camset_save_overwrite_or_write_flags_blocked(self) -> None:
        r_save = verify_custom_key_dial_iso_ei_and_remain_shoot_guard(
            slot1_camset_operation=CAMSET_OP_SAVE_OVERWRITE_G100
        )
        self.assertFalse(r_save.valid)
        self.assertEqual(
            r_save.status, STATUS_BLOCKED_G100_SLOT1_CUSTOM_KEY_CAMSET01_FIREWALL_VIOLATION
        )

        r_wr = verify_custom_key_dial_iso_ei_and_remain_shoot_guard(
            slot1_open_flags=os.O_RDWR
        )
        self.assertFalse(r_wr.valid)
        self.assertEqual(
            r_wr.status, STATUS_BLOCKED_G100_SLOT1_CUSTOM_KEY_CAMSET01_FIREWALL_VIOLATION
        )

    def test_47_g100_slot1_camset_cross_model_fx6_or_mutation_bytes_blocked(
        self,
    ) -> None:
        r_fx6 = verify_custom_key_dial_iso_ei_and_remain_shoot_guard(
            camset_source_body_model=FX6_MODEL_NAME
        )
        self.assertFalse(r_fx6.valid)
        self.assertEqual(
            r_fx6.status, STATUS_BLOCKED_G100_SLOT1_CUSTOM_KEY_CAMSET01_FIREWALL_VIOLATION
        )

        r_mut = verify_custom_key_dial_iso_ei_and_remain_shoot_guard(
            slot1_custom_key_vault_mutation_bytes=64
        )
        self.assertFalse(r_mut.valid)
        self.assertEqual(
            r_mut.status, STATUS_BLOCKED_G100_SLOT1_CUSTOM_KEY_CAMSET01_FIREWALL_VIOLATION
        )

    def test_48_g100_remain_shoot_display_three_modes_and_still_buffer_only_scope(
        self,
    ) -> None:
        self.assertEqual(
            REMAIN_SHOOT_DISPLAY_MENU_PATH_G100,
            "MENU -> Setup -> [Display Option] -> [Remain Shoot Display]",
        )
        self.assertEqual(REMAIN_SHOOT_FACTORY_DEFAULT_G100, REMAIN_SHOOT_NOT_DISPLAYED_G100)
        self.assertEqual(
            ALLOWED_REMAIN_SHOOT_DISPLAY_MODES_G100,
            (
                REMAIN_SHOOT_NOT_DISPLAYED_G100,
                REMAIN_SHOOT_ALWAYS_DISPLAY_G100,
                REMAIN_SHOOT_SHOOT_ONLY_DISPLAY_G100,
            ),
        )
        for opt in ALLOWED_REMAIN_SHOOT_DISPLAY_MODES_G100:
            r = verify_custom_key_dial_iso_ei_and_remain_shoot_guard(
                pre_reset_remain_shoot_display=opt
            )
            self.assertTrue(r.valid)
            self.assertEqual(r.effective_post_reset_remain_shoot_display, opt)
            self.assertEqual(r.remain_shoot_scope, REMAIN_SHOOT_SCOPE_STILL_BUFFER_ONLY_G100)
            self.assertFalse(r.displays_movie_card_remaining_time)

    def test_49_g100_remain_shoot_movie_card_time_claim_or_invalid_mode_blocks(
        self,
    ) -> None:
        r_mv = verify_custom_key_dial_iso_ei_and_remain_shoot_guard(
            displays_movie_card_remaining_time=True
        )
        self.assertFalse(r_mv.valid)
        self.assertEqual(
            r_mv.status,
            STATUS_BLOCKED_G100_REMAIN_SHOOT_SCOPE_OR_RESET_PERSISTENCE_VIOLATION,
        )

        r_opt = verify_custom_key_dial_iso_ei_and_remain_shoot_guard(
            pre_reset_remain_shoot_display="Movie Remaining Time"
        )
        self.assertFalse(r_opt.valid)
        self.assertEqual(
            r_opt.status,
            STATUS_BLOCKED_G100_REMAIN_SHOOT_SCOPE_OR_RESET_PERSISTENCE_VIOLATION,
        )

    def test_50_g100_remain_shoot_survives_camera_and_network_reset_cleared_by_init(
        self,
    ) -> None:
        for rst in (
            RESET_ACTION_CAMERA_SETTINGS_RESET,
            RESET_ACTION_RESET_NETWORK_SET_PHASE256,
        ):
            r = verify_custom_key_dial_iso_ei_and_remain_shoot_guard(
                pre_reset_remain_shoot_display=REMAIN_SHOOT_ALWAYS_DISPLAY_G100,
                reset_action=rst,
                observed_post_reset_remain_shoot_display=REMAIN_SHOOT_ALWAYS_DISPLAY_G100,
            )
            self.assertTrue(r.valid)

        r_init = verify_custom_key_dial_iso_ei_and_remain_shoot_guard(
            pre_reset_remain_shoot_display=REMAIN_SHOOT_ALWAYS_DISPLAY_G100,
            reset_action=RESET_ACTION_INITIALIZE,
            observed_post_reset_remain_shoot_display=REMAIN_SHOOT_NOT_DISPLAYED_G100,
        )
        self.assertTrue(r_init.valid)

    def test_51_g100_remain_shoot_post_reset_drift_blocks_fail_closed(self) -> None:
        r = verify_custom_key_dial_iso_ei_and_remain_shoot_guard(
            pre_reset_remain_shoot_display=REMAIN_SHOOT_SHOOT_ONLY_DISPLAY_G100,
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
            observed_post_reset_remain_shoot_display=REMAIN_SHOOT_NOT_DISPLAYED_G100,
        )
        self.assertFalse(r.valid)
        self.assertEqual(
            r.status,
            STATUS_BLOCKED_G100_REMAIN_SHOOT_SCOPE_OR_RESET_PERSISTENCE_VIOLATION,
        )

    def test_52_g100_evf_less_fx3_topology_blocks_builtin_evf_or_finder_monitor_spoof(
        self,
    ) -> None:
        self.assertEqual(
            FX3_ACTIVE_DISPLAY_SURFACE_LCD_G100, "VARI_ANGLE_LCD_MONITOR"
        )
        for kw in (
            {"claimed_builtin_evf": True},
            {"finder_monitor_switch_present": True},
            {"evf_eye_sensor_present": True},
            {"active_display_surface": "OLED_EVF_FINDER"},
            {"evf_finder_monitor_spoof_events": 1},
        ):
            r = verify_custom_key_dial_iso_ei_and_remain_shoot_guard(**kw)
            self.assertFalse(r.valid)
            self.assertEqual(
                r.status,
                STATUS_BLOCKED_G100_EVF_FINDER_MONITOR_TOPOLOGY_SPOOF_VIOLATION,
            )

    def test_53_g100_invalid_body_telemetry_or_negative_counters_block(self) -> None:
        self.assertEqual(FX3_MODEL_NAME, "ILME-FX3")
        self.assertEqual(FX3_MODEL_ID, 0x91030080)
        self.assertEqual(FX3_DEFAULT_FW_VERSION_PHASE256, "7.02")
        self.assertEqual(FX3_HELP_GUIDE_CODE_PHASE256, "ilc/2210")
        self.assertEqual(FX3_MIN_SUPPORTED_FW_TUPLE_PHASE256, (1, 0))
        r = verify_custom_key_dial_iso_ei_and_remain_shoot_guard(
            body_model_name="ILCE-7SM3"
        )
        self.assertFalse(r.valid)
        self.assertEqual(r.status, STATUS_BLOCKED_G100_TELEMETRY_INVALID)

        r_neg = verify_custom_key_dial_iso_ei_and_remain_shoot_guard(
            evf_finder_monitor_spoof_events=-1
        )
        self.assertFalse(r_neg.valid)
        self.assertEqual(r_neg.status, STATUS_BLOCKED_G100_TELEMETRY_INVALID)

    def test_54_g100_persistent_emmc_write_request_blocks_fail_closed(self) -> None:
        verdict, res = evaluate_g100_custom_key_dial_and_remain_shoot_guard(
            force_clean_room=True, request_persistent_emmc_writes=True
        )
        self.assertFalse(verdict.passed)
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)


    # ------------------------------------------------------------------
    # Section D: Unified 100-Gate Milestone Preflight & CLI Contracts (55..70)
    # ------------------------------------------------------------------

    def test_55_active_offline_100gate_preflight_passes_97_of_100_redlines_locked(
        self,
    ) -> None:
        rep = self.active_offline_100
        self.assertEqual(rep.summary["total_gates"], 100)
        self.assertEqual(rep.summary["verified_gates"], 97)
        self.assertEqual(rep.summary["blocked_or_pending_gates"], 3)
        self.assertTrue(rep.offline_97_gates_verified)
        self.assertFalse(rep.all_100_gates_verified)
        self.assertTrue(rep.g99_to_g100_all_passed)
        self.assertTrue(rep.g13_to_g100_all_passed)
        self.assertEqual(rep.status, "VERIFIED_97_OF_100_AWAITING_PHYSICAL_TIER0")
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.hardware_live_attachment_authorized)
        self.assertFalse(rep.el3_payload_transmit_authorized)
        self.assertFalse(rep.spi_nor_write_authorized)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertEqual(rep.usb_packets_transmitted, 0)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_56_clean_room_offline_100gate_preflight_passes_97_of_100(self) -> None:
        rep = self.clean_offline_100
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(rep.clean_room_forced)
        self.assertEqual(rep.summary["verified_gates"], 97)
        self.assertTrue(rep.offline_97_gates_verified)
        self.assertFalse(rep.all_100_gates_verified)

    def test_57_simulated_dry_run_100gate_preflight_passes_all_100_gates(self) -> None:
        rep = self.clean_dryrun_100
        self.assertEqual(rep.summary["total_gates"], 100)
        self.assertEqual(rep.summary["verified_gates"], 100)
        self.assertTrue(rep.all_100_gates_verified)
        self.assertTrue(rep.dry_run_rehearsal_only)
        self.assertEqual(
            rep.status, "VERIFIED_ALL_100_GATES_DRY_RUN_SIMULATED_BACKUP"
        )
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertEqual(rep.usb_packets_transmitted, 0)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_58_preflight_aliases_run_100_gate_preflight_and_master_safety_gates(
        self,
    ) -> None:
        self.assertIs(run_100_gate_preflight, evaluate_100gate_preflight)
        self.assertIs(evaluate_100_master_safety_gates, evaluate_100gate_preflight)

    def test_59_preflight_gates_tuple_ends_with_g99_and_g100_at_index_98_and_99(
        self,
    ) -> None:
        self.assertEqual(len(self.clean_offline_100.gates), 100)
        self.assertEqual(self.clean_offline_100.gates[98]["gate_id"], G99_GATE_ID)
        self.assertEqual(self.clean_offline_100.gates[99]["gate_id"], G100_GATE_ID)
        self.assertTrue(self.clean_offline_100.gates[98]["passed"])
        self.assertTrue(self.clean_offline_100.gates[99]["passed"])

    def test_60_preflight_propagates_g99_custom_wb_transition_violation_to_status(
        self,
    ) -> None:
        rep = evaluate_100gate_preflight(
            force_clean_room=True,
            master_98_override=self.clean_offline_98,
            diff_set_still_mv_kwargs={
                "transition_mode": DIFF_SET_TRANSITION_COMMON_TO_SEPARATE_G99,
                "common_values": {"White Balance": "Custom White Balance"},
                "observed_post_transition_movie_values": {
                    "White Balance": "Custom White Balance"
                },
            },
        )
        self.assertFalse(rep.g99_to_g100_all_passed)
        self.assertFalse(rep.offline_97_gates_verified)
        self.assertFalse(rep.h0_h1_trial_entry_allowed)
        self.assertEqual(
            rep.status,
            STATUS_BLOCKED_G99_COMMON_TO_SEPARATE_CUSTOM_WB_STILL_ONLY_VIOLATION,
        )

    def test_61_preflight_propagates_g99_shutter_angle_bleed_violation_to_status(
        self,
    ) -> None:
        rep = evaluate_100gate_preflight(
            force_clean_room=True,
            master_98_override=self.clean_offline_98,
            diff_set_still_mv_kwargs={
                "movie_shutter_mode": SHUTTER_MODE_ANGLE_G99,
                "shutter_angle_common_bleed_events": 1,
            },
        )
        self.assertFalse(rep.g99_to_g100_all_passed)
        self.assertEqual(
            rep.status, STATUS_BLOCKED_G99_SHUTTER_ANGLE_COMMON_BLEED_VIOLATION
        )

    def test_62_preflight_propagates_g100_slot1_camset_mutation_to_status(
        self,
    ) -> None:
        rep = evaluate_100gate_preflight(
            force_clean_room=True,
            master_98_override=self.clean_offline_98,
            custom_key_remain_shoot_kwargs={
                "slot1_camset_operation": CAMSET_OP_SAVE_OVERWRITE_G100
            },
        )
        self.assertFalse(rep.g99_to_g100_all_passed)
        self.assertFalse(rep.offline_97_gates_verified)
        self.assertFalse(rep.h0_h1_trial_entry_allowed)
        self.assertEqual(
            rep.status, STATUS_BLOCKED_G100_SLOT1_CUSTOM_KEY_CAMSET01_FIREWALL_VIOLATION
        )

    def test_63_preflight_propagates_g100_evf_spoof_violation_to_status(self) -> None:
        rep = evaluate_100gate_preflight(
            force_clean_room=True,
            master_98_override=self.clean_offline_98,
            custom_key_remain_shoot_kwargs={"claimed_builtin_evf": True},
        )
        self.assertFalse(rep.g99_to_g100_all_passed)
        self.assertEqual(
            rep.status,
            STATUS_BLOCKED_G100_EVF_FINDER_MONITOR_TOPOLOGY_SPOOF_VIOLATION,
        )

    def test_64_preflight_blocks_persistent_emmc_write_request(self) -> None:
        rep = evaluate_100gate_preflight(
            force_clean_room=True,
            master_98_override=self.clean_offline_98,
            request_persistent_emmc_writes=True,
        )
        self.assertEqual(rep.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        self.assertFalse(rep.offline_97_gates_verified)
        self.assertFalse(rep.h0_h1_trial_entry_allowed)

    def test_65_preflight_json_serialization_contains_zero_raw_firmware_bytes(
        self,
    ) -> None:
        payload = json.dumps(self.clean_dryrun_100.to_dict())
        parsed = json.loads(payload)
        self.assertEqual(parsed["summary"]["total_gates"], 100)
        self.assertEqual(parsed["summary"]["verified_gates"], 100)
        self.assertEqual(parsed["raw_firmware_bytes_leaked"], 0)

    def test_66_cli_verify_diff_set_still_mv_guard_text_json_and_alias(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cli_main(
                ["verify-diff-set-still-mv-shutter-angle-guard", "--force-clean-room"]
            )
        self.assertEqual(rc, 0)
        self.assertIn(G99_GATE_ID, buf.getvalue())

        buf_json = io.StringIO()
        with contextlib.redirect_stdout(buf_json):
            rc_j = cli_main(
                ["verify-g99-diff-set-still-mv", "--force-clean-room", "--json"]
            )
        self.assertEqual(rc_j, 0)
        data = json.loads(buf_json.getvalue())
        self.assertTrue(data["valid"])
        self.assertEqual(data["status"], STATUS_VERIFIED_G99)

    def test_67_cli_verify_custom_key_dial_remain_shoot_guard_text_json_and_alias(
        self,
    ) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cli_main(
                ["verify-custom-key-dial-remain-shoot-guard", "--force-clean-room"]
            )
        self.assertEqual(rc, 0)
        self.assertIn(G100_GATE_ID, buf.getvalue())

        buf_json = io.StringIO()
        with contextlib.redirect_stdout(buf_json):
            rc_j = cli_main(
                ["verify-g100-custom-key-remain-shoot", "--force-clean-room", "--json"]
            )
        self.assertEqual(rc_j, 0)
        data = json.loads(buf_json.getvalue())
        self.assertTrue(data["valid"])
        self.assertEqual(data["status"], STATUS_VERIFIED_G100)

    def test_68_cli_verify_100_gates_offline_and_dry_run_text_and_json(self) -> None:
        with mock.patch(
            "fx3_safety.realhw_diff_set_still_mv_custom_key_remain_shoot_and_100gate_guard.evaluate_98gate_preflight",
            return_value=self.clean_offline_98,
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = cli_main(["verify-100-gates", "--force-clean-room"])
            self.assertEqual(rc, 0)
            self.assertIn("verified=97/100", buf.getvalue())

        with mock.patch(
            "fx3_safety.realhw_diff_set_still_mv_custom_key_remain_shoot_and_100gate_guard.evaluate_98gate_preflight",
            return_value=self.clean_dryrun_98,
        ):
            buf_j = io.StringIO()
            with contextlib.redirect_stdout(buf_j):
                rc_j = cli_main(
                    [
                        "verify-100-gates",
                        "--force-clean-room",
                        "--simulate-bench-dry-run",
                        "--json",
                    ]
                )
            self.assertEqual(rc_j, 0)
            parsed = json.loads(buf_j.getvalue())
            self.assertEqual(parsed["summary"]["verified_gates"], 100)
            self.assertFalse(parsed["overall_ready_for_hardware_attach"])

    def test_69_module_standalone_main_offline_and_dry_run_text_and_json(self) -> None:
        with mock.patch(
            "fx3_safety.realhw_diff_set_still_mv_custom_key_remain_shoot_and_100gate_guard.evaluate_98gate_preflight",
            return_value=self.clean_offline_98,
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = module_main(["--force-clean-room"])
            self.assertEqual(rc, 0)
            self.assertIn("verified=97/100", buf.getvalue())

        with mock.patch(
            "fx3_safety.realhw_diff_set_still_mv_custom_key_remain_shoot_and_100gate_guard.evaluate_98gate_preflight",
            return_value=self.clean_dryrun_98,
        ):
            buf_j = io.StringIO()
            with contextlib.redirect_stdout(buf_j):
                rc_j = module_main(
                    ["--force-clean-room", "--simulate-bench-dry-run", "--json"]
                )
            self.assertEqual(rc_j, 0)
            parsed = json.loads(buf_j.getvalue())
            self.assertEqual(parsed["summary"]["verified_gates"], 100)

    def test_70_backward_compatibility_with_98gate_preflight_preserved(self) -> None:
        self.assertEqual(self.active_offline_98.summary["total_gates"], 98)
        self.assertEqual(self.active_offline_98.summary["verified_gates"], 95)
        self.assertEqual(self.clean_dryrun_98.summary["verified_gates"], 98)


if __name__ == "__main__":
    unittest.main()
