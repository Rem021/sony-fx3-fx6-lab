"""Phase 252 Dual-Mode Unit Tests (68 tests, < 4s runtime) for
`fx3_safety.realhw_display_quality_bt_rmt_mymenu_and_98gate_guard`:

- Gate `G97`: `ILME-FX3` (`Ver. 7.02`) `[Display Quality]` (`Standard`/`High`)
  `NP-FZ100` Tier-0 Bench Battery Conservation & `[Setup]` Survival Across
  `Camera Settings Reset` + `Reset Network Set.` + `[Bluetooth Rmt Ctrl]`
  (`Off`/`On`) Radio Prerequisites, Infrared Remote (`SIRCS`) Mutual Exclusion &
  3-Way `Reset Network Set.` Split Guard.
- Gate `G98`: `ILME-FX3` (`Ver. 7.02`) `[My Menu Setting]` 6-Operation
  (`Add Item`, `Sort Item`, `Delete Item`, `Delete Page`, `Delete All`,
  `[Display From My Menu]` `Off`/`On`, up to `6x6 = 36` items) Persistence Across
  `Camera Settings Reset` + `Reset Network Set.` & Slot-1 Tier-0 `CAMSET01.DAT`
  `O_RDONLY` Load-Only Firewall Guard.
- Unified `98`-Gate Master Safety Preflight (`evaluate_98gate_preflight` /
  `verify-98-gates`): `95/98` offline awaiting physical Tier-0 receipt and
  `98/98` in `--simulate-bench-dry-run` with all hardware write/live-attach
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
from fx3_safety.realhw_display_quality_bt_rmt_mymenu_and_98gate_guard import (
    ALLOWED_BLUETOOTH_RMT_CTRL_MODES_G97,
    ALLOWED_CAMSET_OPERATIONS_G98,
    ALLOWED_DISPLAY_FROM_MY_MENU_MODES_G98,
    ALLOWED_DISPLAY_QUALITY_MODES_G97,
    ALLOWED_MONITOR_BRIGHTNESS_LEVELS_G97,
    ALLOWED_MONITOR_BRIGHTNESS_MODES_G97,
    ALLOWED_MY_MENU_ACTIVE_OPS_G98,
    ALLOWED_POWER_SOURCES_G97,
    ALLOWED_RESET_ACTIONS_PHASE252,
    BT_RMT_CTRL_FACTORY_DEFAULT_G97,
    BT_RMT_CTRL_MENU_PATH_G97,
    BT_RMT_CTRL_OFF_G97,
    BT_RMT_CTRL_ON_G97,
    CAMSET_DEFAULT_SLOT1_FILENAME_G98,
    CAMSET_OP_LOAD_O_RDONLY_G98,
    CAMSET_OP_NONE_G98,
    CAMSET_OP_SAVE_OVERWRITE_G98,
    DISPLAY_FROM_MY_MENU_FACTORY_DEFAULT_G98,
    DISPLAY_FROM_MY_MENU_MENU_PATH_G98,
    DISPLAY_FROM_MY_MENU_OFF_G98,
    DISPLAY_FROM_MY_MENU_ON_G98,
    DISPLAY_QUALITY_FACTORY_DEFAULT_G97,
    DISPLAY_QUALITY_HIGH_G97,
    DISPLAY_QUALITY_MENU_PATH_G97,
    DISPLAY_QUALITY_STANDARD_G97,
    DONOR_CHECK_MAX_SECONDS_PHASE252,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    FX3_DEFAULT_FW_VERSION_PHASE252,
    FX3_HELP_GUIDE_CODE_PHASE252,
    FX3_MIN_SUPPORTED_FW_TUPLE_PHASE252,
    FX3_MODEL_ID,
    FX3_MODEL_NAME,
    FX6_MODEL_NAME,
    G97,
    G97_GATE_CODE,
    G97_GATE_ID,
    G98,
    G98_GATE_CODE,
    G98_GATE_ID,
    GATE_G97_DISPLAY_QUALITY_BATTERY_CONSERVATION_AND_BT_RMT_CTRL_IR_LOCKOUT_GUARD,
    GATE_G98_MYMENU_6OP_PERSISTENCE_AND_SLOT1_CAMSET01_FIREWALL_GUARD,
    HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    HUMAN_HARDWARE_ATTACH_TOKEN,
    MONITOR_BRIGHTNESS_MANUAL_G97,
    MONITOR_BRIGHTNESS_SUNNY_WEATHER_G97,
    MY_MENU_MAX_ITEMS_PER_PAGE_G98,
    MY_MENU_MAX_PAGES_G98,
    MY_MENU_MAX_TOTAL_ITEMS_G98,
    MY_MENU_OPEN_TARGET_MOST_RECENT_TAB_G98,
    MY_MENU_OPEN_TARGET_MY_MENU_FIRST_G98,
    MY_MENU_SETTING_MENU_PATH_G98,
    MY_MENU_SIX_SUB_OPERATIONS_G98,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED,
    PHYSICAL_USB_PACKETS_EMITTED,
    PINNED_PHASE252_DONOR_SPECS,
    POWER_SOURCE_DC_C1_G97,
    POWER_SOURCE_NP_FZ100_G97,
    POWER_SOURCE_USB_PD_G97,
    RAW_FIRMWARE_BYTES_LEAKED,
    REALHW_DISPLAY_QUALITY_BT_RMT_MYMENU_98GATE_SCHEMA,
    REALHW_DISPLAY_QUALITY_BT_RMT_MYMENU_98GATE_VERSION,
    RESET_ACTION_CAMERA_SETTINGS_RESET,
    RESET_ACTION_INITIALIZE,
    RESET_ACTION_NONE,
    RESET_ACTION_RESET_NETWORK_SET_PHASE252,
    SPI_NOR_WRITE_AUTHORIZED,
    STATUS_BLOCKED_G97_BT_RMT_CTRL_ENUM_OR_NETWORK_RESET_SPLIT_VIOLATION,
    STATUS_BLOCKED_G97_BT_RMT_IR_SIRCS_MUTUAL_EXCLUSION_VIOLATION,
    STATUS_BLOCKED_G97_BT_RMT_PREREQUISITE_OR_ZERO_RF_BENCH_VIOLATION,
    STATUS_BLOCKED_G97_DISPLAY_QUALITY_ENUM_OR_RESET_PERSISTENCE_VIOLATION,
    STATUS_BLOCKED_G97_TELEMETRY_INVALID,
    STATUS_BLOCKED_G97_TIER0_BATTERY_HIGH_DISPLAY_OR_BRIGHTNESS_DRAIN,
    STATUS_BLOCKED_G98_DISPLAY_FROM_MY_MENU_ENUM_OR_OPEN_TARGET_VIOLATION,
    STATUS_BLOCKED_G98_MY_MENU_RESET_PERSISTENCE_VIOLATION,
    STATUS_BLOCKED_G98_MY_MENU_SUB_OP_OR_CAPACITY_VIOLATION,
    STATUS_BLOCKED_G98_SLOT1_CAMSET01_FIREWALL_MUTATION_VIOLATION,
    STATUS_BLOCKED_G98_TELEMETRY_INVALID,
    STATUS_BLOCKED_PERSISTENT_EMMC_WRITE,
    STATUS_BLOCKED_PHASE252_DONOR_INTEGRITY,
    STATUS_VERIFIED_G97,
    STATUS_VERIFIED_G98,
    TIER0_BATTERY_MONITOR_BRIGHTNESS_LEVEL_G97,
    USB_PACKETS_TRANSMITTED,
    _read_file_o_rdonly,
    audit_phase252_donor_contracts,
    evaluate_98_master_safety_gates,
    evaluate_98gate_preflight,
    evaluate_g97_display_quality_and_bt_rmt_guard,
    evaluate_g98_mymenu_and_camset_firewall_guard,
    main as module_main,
    resolve_fx3_display_quality_and_bt_rmt_state,
    resolve_fx3_mymenu_and_camset_firewall_state,
    run_98_gate_preflight,
    verify_display_quality_battery_and_bt_rmt_ir_lockout_guard,
    verify_mymenu_6op_persistence_and_slot1_camset_firewall_guard,
)


class TestPhase252DisplayQualityBtRmtMyMenuAnd98GateGuard(unittest.TestCase):
    """68 fast dual-mode tests covering Gates G97, G98, and unified 98-Gate preflight (< 4s)."""

    @classmethod
    def setUpClass(cls) -> None:
        # Cache upstream 96-gate and 98-gate preflight evaluations once so all 68
        # tests execute well under < 4s in both LOCAL_DONOR_O_RDONLY and
        # FX3_FX6_FORCE_CLEAN_ROOM=1 modes.
        cls.active_offline_96 = fx3_safety.evaluate_96gate_preflight()
        cls.active_offline_98 = evaluate_98gate_preflight(
            master_96_override=cls.active_offline_96
        )
        if cls.active_offline_96.clean_room_forced:
            cls.clean_offline_96 = cls.active_offline_96
        else:
            with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
                cls.clean_offline_96 = fx3_safety.evaluate_96gate_preflight(
                    force_clean_room=True
                )
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            cls.clean_dryrun_96 = fx3_safety.evaluate_96gate_preflight(
                force_clean_room=True, dry_run_simulated=True
            )
            cls.clean_offline_98 = evaluate_98gate_preflight(
                force_clean_room=True, master_96_override=cls.clean_offline_96
            )
            cls.clean_dryrun_98 = evaluate_98gate_preflight(
                force_clean_room=True,
                simulate_bench_dry_run=True,
                master_96_override=cls.clean_dryrun_96,
            )

    # ------------------------------------------------------------------
    # Section A: Schema, Exports & O_RDONLY / Clean-Room Donor Audit (01..12)
    # ------------------------------------------------------------------

    def test_01_schema_version_gate_ids_and_redline_constants(self) -> None:
        self.assertEqual(
            REALHW_DISPLAY_QUALITY_BT_RMT_MYMENU_98GATE_SCHEMA,
            "realhw_display_quality_bt_rmt_mymenu_and_98gate_guard_v1",
        )
        self.assertEqual(REALHW_DISPLAY_QUALITY_BT_RMT_MYMENU_98GATE_VERSION, "1.0.0")
        self.assertEqual(G97, G97_GATE_ID)
        self.assertEqual(G98, G98_GATE_ID)
        self.assertEqual(
            GATE_G97_DISPLAY_QUALITY_BATTERY_CONSERVATION_AND_BT_RMT_CTRL_IR_LOCKOUT_GUARD,
            G97_GATE_CODE,
        )
        self.assertEqual(
            GATE_G98_MYMENU_6OP_PERSISTENCE_AND_SLOT1_CAMSET01_FIREWALL_GUARD,
            G98_GATE_CODE,
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
        phase252_syms = (
            "REALHW_DISPLAY_QUALITY_BT_RMT_MYMENU_98GATE_SCHEMA",
            "REALHW_DISPLAY_QUALITY_BT_RMT_MYMENU_98GATE_VERSION",
            "G97_GATE_ID",
            "G97_GATE_CODE",
            "G98_GATE_ID",
            "G98_GATE_CODE",
            "Master98GateReport",
            "Phase252DonorAuditResult",
            "DisplayQualityAndBtRmtGuardResult",
            "MyMenuAndCamsetFirewallGuardResult",
            "G97DisplayQualityAndBtRmtGuardResult",
            "G98MyMenuAndCamsetFirewallGuardResult",
            "audit_phase252_donor_contracts",
            "evaluate_98gate_preflight",
            "evaluate_98_master_safety_gates",
            "run_98_gate_preflight",
            "evaluate_g97_display_quality_and_bt_rmt_guard",
            "evaluate_g98_mymenu_and_camset_firewall_guard",
            "verify_display_quality_battery_and_bt_rmt_ir_lockout_guard",
            "verify_mymenu_6op_persistence_and_slot1_camset_firewall_guard",
            "realhw_display_quality_bt_rmt_mymenu_and_98gate_guard",
        )
        for sym in phase252_syms:
            self.assertEqual(fx3_safety.__all__.count(sym), 1, msg=sym)
            self.assertTrue(hasattr(fx3_safety, sym), msg=sym)
        for prior_sym in ("evaluate_96gate_preflight", "evaluate_94gate_preflight"):
            self.assertIn(prior_sym, fx3_safety.__all__)
            self.assertTrue(hasattr(fx3_safety, prior_sym))

    def test_03_pinned_donor_specs_cover_bluetooth_airplanemode_saveload_and_sircs(
        self,
    ) -> None:
        self.assertEqual(len(PINNED_PHASE252_DONOR_SPECS), 6)
        rels = {k: v[1] for k, v in PINNED_PHASE252_DONOR_SPECS.items()}
        self.assertTrue(rels["fx3_cpapp_bin"].endswith("cpapp-b.bin"))
        self.assertTrue(rels["fx3_libinfrabluetooth_so"].endswith("libInfraBluetooth.so"))
        self.assertTrue(rels["fx3_libinfraairplanemode_so"].endswith("libInfraAirplaneMode.so"))
        self.assertTrue(rels["fx3_libsaveloadsettings_so"].endswith("libSaveLoadSettings.so"))
        self.assertTrue(rels["fx6_libinfrabluetooth_so"].endswith("libInfraBluetooth.so"))
        self.assertTrue(rels["fx6_libinfrasircs_so"].endswith("libInfraSircs.so"))

    def test_04_active_donor_audit_within_100ms_and_zero_leaked_bytes(self) -> None:
        res = audit_phase252_donor_contracts()
        self.assertTrue(res.valid)
        self.assertTrue(res.within_budget_100ms)
        self.assertLess(res.elapsed_seconds, DONOR_CHECK_MAX_SECONDS_PHASE252)
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

    def test_05_forced_clean_room_flag_and_env_var_fallback(self) -> None:
        r_flag = audit_phase252_donor_contracts(force_clean_room=True)
        self.assertTrue(r_flag.valid)
        self.assertEqual(r_flag.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(r_flag.access_mode, "SYNTHETIC_CLEAN_ROOM")
        self.assertEqual(r_flag.files_inspected, 0)
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            r_env = audit_phase252_donor_contracts()
            self.assertTrue(r_env.valid)
            self.assertEqual(r_env.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_06_missing_donor_directory_falls_back_to_clean_room_synthetic(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            res = audit_phase252_donor_contracts(
                work_root=Path(tmp) / "nonexistent_donor_dir",
                force_clean_room=False,
            )
            self.assertTrue(res.valid)
            self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertEqual(res.files_inspected, 0)

    def test_07_partial_donor_directory_falls_back_to_clean_room_synthetic(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first_rel = next(iter(PINNED_PHASE252_DONOR_SPECS.values()))[1]
            fp = root / first_rel
            fp.parent.mkdir(parents=True, exist_ok=True)
            fp.write_bytes(b"PARTIAL")
            res = audit_phase252_donor_contracts(work_root=root, force_clean_room=False)
            self.assertTrue(res.valid)
            self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_08_corrupted_donor_marker_and_sha_blocks_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for _k, (_body, rel, *_rest) in PINNED_PHASE252_DONOR_SPECS.items():
                fp = root / rel
                fp.parent.mkdir(parents=True, exist_ok=True)
                fp.write_bytes(b"CORRUPTED_DONOR_STUB")
            res = audit_phase252_donor_contracts(work_root=root, force_clean_room=False)
            self.assertFalse(res.valid)
            self.assertEqual(res.status, STATUS_BLOCKED_PHASE252_DONOR_INTEGRITY)
            self.assertEqual(res.verification_mode, "LOCAL_DONOR_O_RDONLY")
            self.assertGreater(len(res.errors), 0)

    def test_09_donor_budget_exceeded_blocks_fail_closed_in_clean_room(self) -> None:
        r_clean = audit_phase252_donor_contracts(
            force_clean_room=True, max_budget_seconds=-1.0
        )
        self.assertFalse(r_clean.valid)
        self.assertEqual(r_clean.status, STATUS_BLOCKED_PHASE252_DONOR_INTEGRITY)

    def test_10_o_rdonly_strict_open_flags_never_request_write_bits(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sample = Path(tmp) / "sample.bin"
            sample.write_bytes(b"RDONLY_TEST")
            seen_flags: list[int] = []
            real_open = os.open

            def _spy_open(path: str, flags: int, *args: object) -> int:
                seen_flags.append(flags)
                return real_open(path, flags, *args)

            with mock.patch("os.open", side_effect=_spy_open):
                blob = _read_file_o_rdonly(sample)
            self.assertEqual(blob, b"RDONLY_TEST")
            self.assertEqual(len(seen_flags), 1)
            write_bits = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND
            self.assertEqual(seen_flags[0] & write_bits, 0)

    def test_11_donor_audit_to_dict_serializes_cleanly_without_raw_bytes(self) -> None:
        d = audit_phase252_donor_contracts(force_clean_room=True).to_dict()
        text = json.dumps(d)
        self.assertIn("checked_markers", text)
        self.assertEqual(d["raw_firmware_bytes_leaked"], 0)

    def test_12_allowed_reset_actions_and_enums_match_wave39_help_guide(self) -> None:
        self.assertEqual(
            ALLOWED_RESET_ACTIONS_PHASE252,
            ("NONE", "Camera Settings Reset", "Reset Network Set.", "Initialize"),
        )
        self.assertEqual(ALLOWED_DISPLAY_QUALITY_MODES_G97, ("Standard", "High"))
        self.assertEqual(ALLOWED_BLUETOOTH_RMT_CTRL_MODES_G97, ("Off", "On"))
        self.assertEqual(ALLOWED_DISPLAY_FROM_MY_MENU_MODES_G98, ("Off", "On"))
        self.assertEqual(ALLOWED_MONITOR_BRIGHTNESS_MODES_G97, ("Manual", "Sunny Weather"))
        self.assertEqual(ALLOWED_MONITOR_BRIGHTNESS_LEVELS_G97, (-2, -1, 0, 1, 2))
        self.assertEqual(ALLOWED_POWER_SOURCES_G97, ("NP-FZ100", "USB_PD", "DC-C1"))
        self.assertEqual(
            ALLOWED_CAMSET_OPERATIONS_G98, ("NONE", "LOAD_O_RDONLY", "SAVE_OVERWRITE")
        )
        self.assertEqual(len(ALLOWED_MY_MENU_ACTIVE_OPS_G98), 7)


    # ------------------------------------------------------------------
    # Section B: Gate G97 — [Display Quality] Battery Conservation &
    # [Bluetooth Rmt Ctrl] IR Lockout + 3-Way Network Reset Split (13..32)
    # ------------------------------------------------------------------

    def test_13_g97_default_bench_posture_passes_cleanly(self) -> None:
        verdict, res = evaluate_g97_display_quality_and_bt_rmt_guard(
            force_clean_room=True
        )
        self.assertTrue(verdict.passed)
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_VERIFIED_G97)
        guard = res.display_quality_bt_rmt_guard
        self.assertEqual(guard["display_quality_menu_path"], DISPLAY_QUALITY_MENU_PATH_G97)
        self.assertEqual(
            guard["display_quality_factory_default"], DISPLAY_QUALITY_FACTORY_DEFAULT_G97
        )
        self.assertEqual(
            guard["effective_post_reset_display_quality"], DISPLAY_QUALITY_STANDARD_G97
        )
        self.assertTrue(guard["tier0_battery_clamped_to_standard_and_manual0"])
        self.assertEqual(guard["tier0_battery_high_display_violations"], 0)
        self.assertEqual(guard["bt_rmt_ctrl_menu_path"], BT_RMT_CTRL_MENU_PATH_G97)
        self.assertEqual(
            guard["bt_rmt_ctrl_factory_default"], BT_RMT_CTRL_FACTORY_DEFAULT_G97
        )
        self.assertEqual(guard["airplane_mode"], "On")
        self.assertEqual(guard["passive_tx_bytes_emitted"], 0)
        self.assertEqual(guard["bt_rmt_ir_lockout_violations"], 0)

    def test_14_g97_display_quality_high_survives_camera_settings_reset_on_external_pd(
        self,
    ) -> None:
        r = verify_display_quality_battery_and_bt_rmt_ir_lockout_guard(
            pre_reset_display_quality="[High]",
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
            power_source=POWER_SOURCE_USB_PD_G97,
        )
        self.assertTrue(r.valid)
        self.assertEqual(r.effective_post_reset_display_quality, DISPLAY_QUALITY_HIGH_G97)

    def test_15_g97_display_quality_high_survives_reset_network_set_on_dc_c1(
        self,
    ) -> None:
        r = verify_display_quality_battery_and_bt_rmt_ir_lockout_guard(
            pre_reset_display_quality="High",
            reset_action=RESET_ACTION_RESET_NETWORK_SET_PHASE252,
            power_source=POWER_SOURCE_DC_C1_G97,
        )
        self.assertTrue(r.valid)
        self.assertEqual(r.effective_post_reset_display_quality, DISPLAY_QUALITY_HIGH_G97)

    def test_16_g97_display_quality_high_resets_to_standard_only_on_initialize(
        self,
    ) -> None:
        r = verify_display_quality_battery_and_bt_rmt_ir_lockout_guard(
            pre_reset_display_quality="High",
            reset_action=RESET_ACTION_INITIALIZE,
            power_source=POWER_SOURCE_NP_FZ100_G97,
            tier0_bench_dump_active=True,
        )
        self.assertTrue(r.valid)
        self.assertEqual(
            r.effective_post_reset_display_quality, DISPLAY_QUALITY_STANDARD_G97
        )

    def test_17_g97_display_quality_wrong_post_reset_observation_blocks(self) -> None:
        r = verify_display_quality_battery_and_bt_rmt_ir_lockout_guard(
            pre_reset_display_quality="High",
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
            observed_post_reset_display_quality="Standard",
            power_source=POWER_SOURCE_USB_PD_G97,
        )
        self.assertFalse(r.valid)
        self.assertEqual(
            r.status,
            STATUS_BLOCKED_G97_DISPLAY_QUALITY_ENUM_OR_RESET_PERSISTENCE_VIOLATION,
        )

    def test_18_g97_display_quality_invalid_enum_or_reset_flag_blocks(self) -> None:
        r = verify_display_quality_battery_and_bt_rmt_ir_lockout_guard(
            pre_reset_display_quality="Ultra4K",
        )
        self.assertFalse(r.valid)
        self.assertEqual(
            r.status,
            STATUS_BLOCKED_G97_DISPLAY_QUALITY_ENUM_OR_RESET_PERSISTENCE_VIOLATION,
        )

        r_flag = verify_display_quality_battery_and_bt_rmt_ir_lockout_guard(
            display_quality_survives_reset_network_set=False
        )
        self.assertFalse(r_flag.valid)
        self.assertEqual(
            r_flag.status,
            STATUS_BLOCKED_G97_DISPLAY_QUALITY_ENUM_OR_RESET_PERSISTENCE_VIOLATION,
        )

    def test_19_g97_tier0_internal_np_fz100_high_display_quality_blocks_drain(
        self,
    ) -> None:
        r = verify_display_quality_battery_and_bt_rmt_ir_lockout_guard(
            pre_reset_display_quality=DISPLAY_QUALITY_HIGH_G97,
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
            power_source=POWER_SOURCE_NP_FZ100_G97,
            tier0_bench_dump_active=True,
        )
        self.assertFalse(r.valid)
        self.assertEqual(
            r.status, STATUS_BLOCKED_G97_TIER0_BATTERY_HIGH_DISPLAY_OR_BRIGHTNESS_DRAIN
        )
        self.assertGreater(r.tier0_battery_high_display_violations, 0)

    def test_20_g97_tier0_internal_np_fz100_sunny_weather_or_nonzero_brightness_blocks(
        self,
    ) -> None:
        r_sunny = verify_display_quality_battery_and_bt_rmt_ir_lockout_guard(
            power_source=POWER_SOURCE_NP_FZ100_G97,
            tier0_bench_dump_active=True,
            monitor_brightness_mode=MONITOR_BRIGHTNESS_SUNNY_WEATHER_G97,
            monitor_brightness_level=0,
        )
        self.assertFalse(r_sunny.valid)
        self.assertEqual(
            r_sunny.status,
            STATUS_BLOCKED_G97_TIER0_BATTERY_HIGH_DISPLAY_OR_BRIGHTNESS_DRAIN,
        )

        r_lvl = verify_display_quality_battery_and_bt_rmt_ir_lockout_guard(
            power_source=POWER_SOURCE_NP_FZ100_G97,
            tier0_bench_dump_active=True,
            monitor_brightness_mode=MONITOR_BRIGHTNESS_MANUAL_G97,
            monitor_brightness_level=2,
        )
        self.assertFalse(r_lvl.valid)
        self.assertEqual(
            r_lvl.status,
            STATUS_BLOCKED_G97_TIER0_BATTERY_HIGH_DISPLAY_OR_BRIGHTNESS_DRAIN,
        )

    def test_21_g97_bt_rmt_ctrl_exact_3way_reset_split_resolver(self) -> None:
        s_cam = resolve_fx3_display_quality_and_bt_rmt_state(
            pre_reset_display_quality="High",
            pre_reset_bt_rmt_ctrl="On",
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
        )
        self.assertEqual(s_cam["expected_post_reset_display_quality"], "High")
        self.assertEqual(s_cam["expected_post_reset_bt_rmt_ctrl"], "On")

        s_net = resolve_fx3_display_quality_and_bt_rmt_state(
            pre_reset_display_quality="High",
            pre_reset_bt_rmt_ctrl="On",
            reset_action=RESET_ACTION_RESET_NETWORK_SET_PHASE252,
        )
        self.assertEqual(s_net["expected_post_reset_display_quality"], "High")
        self.assertEqual(s_net["expected_post_reset_bt_rmt_ctrl"], "Off")

        s_init = resolve_fx3_display_quality_and_bt_rmt_state(
            pre_reset_display_quality="High",
            pre_reset_bt_rmt_ctrl="On",
            reset_action=RESET_ACTION_INITIALIZE,
        )
        self.assertEqual(s_init["expected_post_reset_display_quality"], "Standard")
        self.assertEqual(s_init["expected_post_reset_bt_rmt_ctrl"], "Off")

    def test_22_g97_bt_rmt_ctrl_survives_camera_reset_and_suppressed_by_zero_rf_airplane_on(
        self,
    ) -> None:
        r = verify_display_quality_battery_and_bt_rmt_ir_lockout_guard(
            pre_reset_bt_rmt_ctrl="On",
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
            bluetooth_function="On",
            airplane_mode="On",
            zero_rf_bench_enforced=True,
            passive_tx_bytes_emitted=0,
        )
        self.assertTrue(r.valid)
        self.assertEqual(r.effective_post_reset_bt_rmt_ctrl, "On")
        self.assertFalse(r.effective_bt_rmt_ctrl_active)
        self.assertTrue(r.bt_rmt_ctrl_suppressed_by_radio_prereq)
        self.assertFalse(r.ir_remote_sircs_usable)

    def test_23_g97_bt_rmt_ctrl_resets_to_off_on_reset_network_set_restoring_ir_sircs(
        self,
    ) -> None:
        r = verify_display_quality_battery_and_bt_rmt_ir_lockout_guard(
            pre_reset_bt_rmt_ctrl="On",
            reset_action="Reset Network Set.",
            airplane_mode="On",
            zero_rf_bench_enforced=True,
        )
        self.assertTrue(r.valid)
        self.assertEqual(r.effective_post_reset_bt_rmt_ctrl, "Off")
        self.assertTrue(r.ir_remote_sircs_usable)

    def test_24_g97_bt_rmt_ctrl_wrong_post_network_reset_observation_blocks(
        self,
    ) -> None:
        r = verify_display_quality_battery_and_bt_rmt_ir_lockout_guard(
            pre_reset_bt_rmt_ctrl="On",
            reset_action=RESET_ACTION_RESET_NETWORK_SET_PHASE252,
            observed_post_reset_bt_rmt_ctrl="On",
        )
        self.assertFalse(r.valid)
        self.assertEqual(
            r.status,
            STATUS_BLOCKED_G97_BT_RMT_CTRL_ENUM_OR_NETWORK_RESET_SPLIT_VIOLATION,
        )

    def test_25_g97_bt_rmt_ctrl_invalid_enum_or_split_flag_blocks(self) -> None:
        r = verify_display_quality_battery_and_bt_rmt_ir_lockout_guard(
            pre_reset_bt_rmt_ctrl="PairingOnly"
        )
        self.assertFalse(r.valid)
        self.assertEqual(
            r.status,
            STATUS_BLOCKED_G97_BT_RMT_CTRL_ENUM_OR_NETWORK_RESET_SPLIT_VIOLATION,
        )

        r2 = verify_display_quality_battery_and_bt_rmt_ir_lockout_guard(
            bt_rmt_reset_by_reset_network_set=False
        )
        self.assertFalse(r2.valid)
        self.assertEqual(
            r2.status,
            STATUS_BLOCKED_G97_BT_RMT_CTRL_ENUM_OR_NETWORK_RESET_SPLIT_VIOLATION,
        )

    def test_26_g97_non_bench_bt_rmt_on_requires_bt_function_on_and_airplane_off(
        self,
    ) -> None:
        r_ok = verify_display_quality_battery_and_bt_rmt_ir_lockout_guard(
            pre_reset_bt_rmt_ctrl="On",
            bluetooth_function="On",
            airplane_mode="Off",
            zero_rf_bench_enforced=False,
            tier0_bench_dump_active=False,
        )
        self.assertTrue(r_ok.valid)
        self.assertTrue(r_ok.effective_bt_rmt_ctrl_active)
        self.assertFalse(r_ok.ir_remote_sircs_usable)

    def test_27_g97_claiming_bt_rmt_active_when_bt_function_off_blocks(self) -> None:
        r = verify_display_quality_battery_and_bt_rmt_ir_lockout_guard(
            pre_reset_bt_rmt_ctrl="On",
            bluetooth_function="Off",
            airplane_mode="Off",
            zero_rf_bench_enforced=False,
            observed_effective_bt_rmt_ctrl_active=True,
        )
        self.assertFalse(r.valid)
        self.assertEqual(
            r.status, STATUS_BLOCKED_G97_BT_RMT_PREREQUISITE_OR_ZERO_RF_BENCH_VIOLATION
        )

    def test_28_g97_zero_rf_bench_blocks_airplane_off_or_nonzero_passive_tx_bytes(
        self,
    ) -> None:
        r_air = verify_display_quality_battery_and_bt_rmt_ir_lockout_guard(
            airplane_mode="Off",
            zero_rf_bench_enforced=True,
        )
        self.assertFalse(r_air.valid)
        self.assertEqual(
            r_air.status,
            STATUS_BLOCKED_G97_BT_RMT_PREREQUISITE_OR_ZERO_RF_BENCH_VIOLATION,
        )

        r_tx = verify_display_quality_battery_and_bt_rmt_ir_lockout_guard(
            airplane_mode="On",
            zero_rf_bench_enforced=True,
            passive_tx_bytes_emitted=16,
        )
        self.assertFalse(r_tx.valid)
        self.assertEqual(
            r_tx.status,
            STATUS_BLOCKED_G97_BT_RMT_PREREQUISITE_OR_ZERO_RF_BENCH_VIOLATION,
        )

    def test_29_g97_ir_sircs_mutual_exclusion_blocks_when_bt_rmt_on(self) -> None:
        r_usable = verify_display_quality_battery_and_bt_rmt_ir_lockout_guard(
            pre_reset_bt_rmt_ctrl="On",
            observed_ir_remote_sircs_usable=True,
        )
        self.assertFalse(r_usable.valid)
        self.assertEqual(
            r_usable.status, STATUS_BLOCKED_G97_BT_RMT_IR_SIRCS_MUTUAL_EXCLUSION_VIOLATION
        )

        r_cmd = verify_display_quality_battery_and_bt_rmt_ir_lockout_guard(
            pre_reset_bt_rmt_ctrl="On",
            ir_remote_command_attempted=True,
        )
        self.assertFalse(r_cmd.valid)
        self.assertEqual(
            r_cmd.status, STATUS_BLOCKED_G97_BT_RMT_IR_SIRCS_MUTUAL_EXCLUSION_VIOLATION
        )
        self.assertGreater(r_cmd.bt_rmt_ir_lockout_violations, 0)

    def test_30_g97_ir_sircs_allowed_when_bt_rmt_off(self) -> None:
        r = verify_display_quality_battery_and_bt_rmt_ir_lockout_guard(
            pre_reset_bt_rmt_ctrl="Off",
            ir_remote_command_attempted=True,
        )
        self.assertTrue(r.valid)
        self.assertTrue(r.ir_remote_sircs_usable)
        self.assertEqual(r.bt_rmt_ir_lockout_violations, 0)

    def test_31_g97_invalid_model_firmware_or_brightness_telemetry_blocks(self) -> None:
        self.assertEqual(FX3_MIN_SUPPORTED_FW_TUPLE_PHASE252, (1, 0))
        self.assertEqual(TIER0_BATTERY_MONITOR_BRIGHTNESS_LEVEL_G97, 0)
        r = verify_display_quality_battery_and_bt_rmt_ir_lockout_guard(
            body_model_name=FX6_MODEL_NAME
        )
        self.assertFalse(r.valid)
        self.assertEqual(r.status, STATUS_BLOCKED_G97_TELEMETRY_INVALID)

        r_fw = verify_display_quality_battery_and_bt_rmt_ir_lockout_guard(
            firmware_version="bad_fw"
        )
        self.assertFalse(r_fw.valid)
        self.assertEqual(r_fw.status, STATUS_BLOCKED_G97_TELEMETRY_INVALID)

    def test_32_g97_persistent_emmc_write_request_blocks_fail_closed(self) -> None:
        verdict, res = evaluate_g97_display_quality_and_bt_rmt_guard(
            force_clean_room=True, request_persistent_emmc_writes=True
        )
        self.assertFalse(verdict.passed)
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)


    # ------------------------------------------------------------------
    # Section C: Gate G98 — [My Menu Setting] 6-Op Persistence & Slot-1
    # CAMSET01.DAT O_RDONLY Load-Only Firewall Guard (33..52)
    # ------------------------------------------------------------------

    def test_33_g98_default_bench_posture_passes_cleanly(self) -> None:
        verdict, res = evaluate_g98_mymenu_and_camset_firewall_guard(
            force_clean_room=True
        )
        self.assertTrue(verdict.passed)
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_VERIFIED_G98)
        guard = res.mymenu_camset_firewall_guard
        self.assertEqual(guard["my_menu_setting_menu_path"], MY_MENU_SETTING_MENU_PATH_G98)
        self.assertEqual(
            guard["display_from_my_menu_menu_path"], DISPLAY_FROM_MY_MENU_MENU_PATH_G98
        )
        self.assertEqual(
            tuple(guard["supported_sub_operations"]), MY_MENU_SIX_SUB_OPERATIONS_G98
        )
        self.assertEqual(guard["max_pages"], MY_MENU_MAX_PAGES_G98)
        self.assertEqual(guard["max_items_per_page"], MY_MENU_MAX_ITEMS_PER_PAGE_G98)
        self.assertEqual(guard["max_total_items"], MY_MENU_MAX_TOTAL_ITEMS_G98)
        self.assertEqual(guard["slot1_camset_filename"], CAMSET_DEFAULT_SLOT1_FILENAME_G98)
        self.assertEqual(guard["slot1_camset_operation"], CAMSET_OP_LOAD_O_RDONLY_G98)
        self.assertEqual(guard["slot1_mymenu_vault_mutation_bytes"], 0)

    def test_34_g98_my_menu_survives_camera_settings_reset_and_reset_network_set(
        self,
    ) -> None:
        r_cam = verify_mymenu_6op_persistence_and_slot1_camset_firewall_guard(
            pre_op_pages_item_counts=(6, 6, 3),
            pre_reset_display_from_my_menu=DISPLAY_FROM_MY_MENU_ON_G98,
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
        )
        self.assertTrue(r_cam.valid)
        self.assertEqual(r_cam.effective_post_reset_pages_item_counts, (6, 6, 3))
        self.assertEqual(r_cam.effective_post_reset_total_items, 15)
        self.assertEqual(
            r_cam.effective_post_reset_display_from_my_menu, DISPLAY_FROM_MY_MENU_ON_G98
        )
        self.assertEqual(
            r_cam.menu_button_open_target, MY_MENU_OPEN_TARGET_MY_MENU_FIRST_G98
        )

        r_net = verify_mymenu_6op_persistence_and_slot1_camset_firewall_guard(
            pre_op_pages_item_counts=(6, 6, 3),
            pre_reset_display_from_my_menu=DISPLAY_FROM_MY_MENU_ON_G98,
            reset_action=RESET_ACTION_RESET_NETWORK_SET_PHASE252,
        )
        self.assertTrue(r_net.valid)
        self.assertEqual(r_net.effective_post_reset_pages_item_counts, (6, 6, 3))
        self.assertEqual(
            r_net.effective_post_reset_display_from_my_menu, DISPLAY_FROM_MY_MENU_ON_G98
        )

    def test_35_g98_my_menu_clears_and_resets_display_from_my_menu_on_initialize(
        self,
    ) -> None:
        r_init = verify_mymenu_6op_persistence_and_slot1_camset_firewall_guard(
            pre_op_pages_item_counts=(6, 6, 6, 6, 6, 6),
            pre_reset_display_from_my_menu=DISPLAY_FROM_MY_MENU_ON_G98,
            reset_action=RESET_ACTION_INITIALIZE,
        )
        self.assertTrue(r_init.valid)
        self.assertEqual(r_init.effective_post_reset_pages_item_counts, ())
        self.assertEqual(r_init.effective_post_reset_total_items, 0)
        self.assertEqual(
            r_init.effective_post_reset_display_from_my_menu,
            DISPLAY_FROM_MY_MENU_FACTORY_DEFAULT_G98,
        )
        self.assertEqual(
            r_init.menu_button_open_target, MY_MENU_OPEN_TARGET_MOST_RECENT_TAB_G98
        )

    def test_36_g98_sub_op_add_item_within_page_and_new_page_allocation(self) -> None:
        r_same = verify_mymenu_6op_persistence_and_slot1_camset_firewall_guard(
            pre_op_pages_item_counts=(5,),
            active_sub_operation="Add Item",
            target_page_index=0,
        )
        self.assertTrue(r_same.valid)
        self.assertEqual(r_same.effective_post_reset_pages_item_counts, (6,))

        r_new_page = verify_mymenu_6op_persistence_and_slot1_camset_firewall_guard(
            pre_op_pages_item_counts=(6,),
            active_sub_operation="Add Item",
            target_page_index=0,
        )
        self.assertTrue(r_new_page.valid)
        self.assertEqual(r_new_page.effective_post_reset_pages_item_counts, (6, 1))

    def test_37_g98_sub_op_sort_delete_item_delete_page_and_delete_all(self) -> None:
        r_sort = verify_mymenu_6op_persistence_and_slot1_camset_firewall_guard(
            pre_op_pages_item_counts=(4, 2),
            active_sub_operation="Sort Item",
        )
        self.assertTrue(r_sort.valid)
        self.assertEqual(r_sort.effective_post_reset_pages_item_counts, (4, 2))

        r_del_item = verify_mymenu_6op_persistence_and_slot1_camset_firewall_guard(
            pre_op_pages_item_counts=(4, 1),
            active_sub_operation="Delete Item",
            target_page_index=1,
        )
        self.assertTrue(r_del_item.valid)
        self.assertEqual(r_del_item.effective_post_reset_pages_item_counts, (4,))

        r_del_page = verify_mymenu_6op_persistence_and_slot1_camset_firewall_guard(
            pre_op_pages_item_counts=(6, 3, 2),
            active_sub_operation="Delete Page",
            target_page_index=1,
        )
        self.assertTrue(r_del_page.valid)
        self.assertEqual(r_del_page.effective_post_reset_pages_item_counts, (6, 2))

        r_del_all = verify_mymenu_6op_persistence_and_slot1_camset_firewall_guard(
            pre_op_pages_item_counts=(6, 6, 6),
            active_sub_operation="Delete All",
            pre_reset_display_from_my_menu="On",
            reset_action=RESET_ACTION_NONE,
        )
        self.assertTrue(r_del_all.valid)
        self.assertEqual(r_del_all.effective_post_reset_pages_item_counts, ())
        self.assertEqual(r_del_all.effective_post_reset_display_from_my_menu, "On")

    def test_38_g98_max_capacity_6x6_36_items_passes_and_37th_add_item_blocks(
        self,
    ) -> None:
        r_max = verify_mymenu_6op_persistence_and_slot1_camset_firewall_guard(
            pre_op_pages_item_counts=(6, 6, 6, 6, 6, 6),
            active_sub_operation="NONE",
        )
        self.assertTrue(r_max.valid)
        self.assertEqual(r_max.effective_post_reset_total_items, 36)

        r_overflow = verify_mymenu_6op_persistence_and_slot1_camset_firewall_guard(
            pre_op_pages_item_counts=(6, 6, 6, 6, 6, 6),
            active_sub_operation="Add Item",
        )
        self.assertFalse(r_overflow.valid)
        self.assertEqual(
            r_overflow.status, STATUS_BLOCKED_G98_MY_MENU_SUB_OP_OR_CAPACITY_VIOLATION
        )

    def test_39_g98_over_6_pages_or_over_6_items_per_page_blocks(self) -> None:
        r_pages = verify_mymenu_6op_persistence_and_slot1_camset_firewall_guard(
            pre_op_pages_item_counts=(1, 1, 1, 1, 1, 1, 1)
        )
        self.assertFalse(r_pages.valid)
        self.assertEqual(
            r_pages.status, STATUS_BLOCKED_G98_MY_MENU_SUB_OP_OR_CAPACITY_VIOLATION
        )

        r_items = verify_mymenu_6op_persistence_and_slot1_camset_firewall_guard(
            pre_op_pages_item_counts=(7, 2)
        )
        self.assertFalse(r_items.valid)
        self.assertEqual(
            r_items.status, STATUS_BLOCKED_G98_MY_MENU_SUB_OP_OR_CAPACITY_VIOLATION
        )

    def test_40_g98_missing_or_invalid_sub_operation_blocks(self) -> None:
        r_missing = verify_mymenu_6op_persistence_and_slot1_camset_firewall_guard(
            supported_sub_operations=("Add Item", "Delete All")
        )
        self.assertFalse(r_missing.valid)
        self.assertEqual(
            r_missing.status, STATUS_BLOCKED_G98_MY_MENU_SUB_OP_OR_CAPACITY_VIOLATION
        )

        r_bad_op = verify_mymenu_6op_persistence_and_slot1_camset_firewall_guard(
            active_sub_operation="Format All"
        )
        self.assertFalse(r_bad_op.valid)
        self.assertEqual(
            r_bad_op.status, STATUS_BLOCKED_G98_MY_MENU_SUB_OP_OR_CAPACITY_VIOLATION
        )

    def test_41_g98_display_from_my_menu_off_opens_most_recent_tab(self) -> None:
        r = verify_mymenu_6op_persistence_and_slot1_camset_firewall_guard(
            pre_reset_display_from_my_menu=DISPLAY_FROM_MY_MENU_OFF_G98
        )
        self.assertTrue(r.valid)
        self.assertEqual(
            r.menu_button_open_target, MY_MENU_OPEN_TARGET_MOST_RECENT_TAB_G98
        )

    def test_42_g98_display_from_my_menu_invalid_enum_or_wrong_open_target_blocks(
        self,
    ) -> None:
        r_enum = verify_mymenu_6op_persistence_and_slot1_camset_firewall_guard(
            pre_reset_display_from_my_menu="Auto"
        )
        self.assertFalse(r_enum.valid)
        self.assertEqual(
            r_enum.status,
            STATUS_BLOCKED_G98_DISPLAY_FROM_MY_MENU_ENUM_OR_OPEN_TARGET_VIOLATION,
        )

        r_target = verify_mymenu_6op_persistence_and_slot1_camset_firewall_guard(
            pre_reset_display_from_my_menu="On",
            observed_menu_button_open_target=MY_MENU_OPEN_TARGET_MOST_RECENT_TAB_G98,
        )
        self.assertFalse(r_target.valid)
        self.assertEqual(
            r_target.status,
            STATUS_BLOCKED_G98_DISPLAY_FROM_MY_MENU_ENUM_OR_OPEN_TARGET_VIOLATION,
        )

    def test_43_g98_post_reset_pages_or_dfmm_drift_blocks_persistence_contract(
        self,
    ) -> None:
        r_pages = verify_mymenu_6op_persistence_and_slot1_camset_firewall_guard(
            pre_op_pages_item_counts=(6, 4),
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
            observed_post_reset_pages_item_counts=(),
        )
        self.assertFalse(r_pages.valid)
        self.assertEqual(
            r_pages.status, STATUS_BLOCKED_G98_MY_MENU_RESET_PERSISTENCE_VIOLATION
        )

        r_dfmm = verify_mymenu_6op_persistence_and_slot1_camset_firewall_guard(
            pre_reset_display_from_my_menu="On",
            reset_action=RESET_ACTION_RESET_NETWORK_SET_PHASE252,
            observed_post_reset_display_from_my_menu="Off",
        )
        self.assertFalse(r_dfmm.valid)
        self.assertEqual(
            r_dfmm.status, STATUS_BLOCKED_G98_MY_MENU_RESET_PERSISTENCE_VIOLATION
        )

    def test_44_g98_reset_persistence_flag_override_blocks(self) -> None:
        r = verify_mymenu_6op_persistence_and_slot1_camset_firewall_guard(
            my_menu_survives_reset_network_set=False
        )
        self.assertFalse(r.valid)
        self.assertEqual(
            r.status, STATUS_BLOCKED_G98_MY_MENU_RESET_PERSISTENCE_VIOLATION
        )

    def test_45_g98_slot1_camset01_through_camset10_o_rdonly_load_passes(self) -> None:
        for fn in ("CAMSET01.DAT", "CAMSET05.DAT", "CAMSET10.DAT"):
            r = verify_mymenu_6op_persistence_and_slot1_camset_firewall_guard(
                slot1_camset_filename=fn,
                slot1_camset_operation=CAMSET_OP_LOAD_O_RDONLY_G98,
                slot1_camset_open_flags=os.O_RDONLY,
            )
            self.assertTrue(r.valid, msg=fn)
            self.assertTrue(r.slot1_camset_load_only_o_rdonly_enforced)

    def test_46_g98_slot1_camset_save_overwrite_blocks_firewall(self) -> None:
        r = verify_mymenu_6op_persistence_and_slot1_camset_firewall_guard(
            slot1_tier0_vault_protected=True,
            slot1_camset_operation=CAMSET_OP_SAVE_OVERWRITE_G98,
        )
        self.assertFalse(r.valid)
        self.assertEqual(
            r.status, STATUS_BLOCKED_G98_SLOT1_CAMSET01_FIREWALL_MUTATION_VIOLATION
        )

    def test_47_g98_slot1_camset_write_open_flags_block_firewall(self) -> None:
        for bad_flag in (os.O_WRONLY, os.O_RDWR, os.O_CREAT, os.O_TRUNC):
            r = verify_mymenu_6op_persistence_and_slot1_camset_firewall_guard(
                slot1_camset_open_flags=bad_flag
            )
            self.assertFalse(r.valid)
            self.assertEqual(
                r.status, STATUS_BLOCKED_G98_SLOT1_CAMSET01_FIREWALL_MUTATION_VIOLATION
            )

    def test_48_g98_slot1_nonzero_mymenu_vault_mutation_bytes_blocks(self) -> None:
        r = verify_mymenu_6op_persistence_and_slot1_camset_firewall_guard(
            slot1_mymenu_vault_mutation_bytes=64
        )
        self.assertFalse(r.valid)
        self.assertEqual(
            r.status, STATUS_BLOCKED_G98_SLOT1_CAMSET01_FIREWALL_MUTATION_VIOLATION
        )

    def test_49_g98_cross_model_fx6_camset_or_invalid_filename_blocks(self) -> None:
        r_fx6 = verify_mymenu_6op_persistence_and_slot1_camset_firewall_guard(
            camset_source_body_model=FX6_MODEL_NAME
        )
        self.assertFalse(r_fx6.valid)
        self.assertEqual(
            r_fx6.status, STATUS_BLOCKED_G98_SLOT1_CAMSET01_FIREWALL_MUTATION_VIOLATION
        )

        r_fn = verify_mymenu_6op_persistence_and_slot1_camset_firewall_guard(
            slot1_camset_filename="CAMSET99.DAT"
        )
        self.assertFalse(r_fn.valid)
        self.assertEqual(
            r_fn.status, STATUS_BLOCKED_G98_SLOT1_CAMSET01_FIREWALL_MUTATION_VIOLATION
        )

    def test_50_g98_mymenu_state_resolver_empty_add_and_single_delete(self) -> None:
        s_add = resolve_fx3_mymenu_and_camset_firewall_state(
            pre_op_pages_item_counts=(),
            active_sub_operation="Add Item",
        )
        self.assertEqual(s_add["expected_post_reset_pages_item_counts"], (1,))
        self.assertEqual(s_add["expected_post_reset_total_items"], 1)

        s_del = resolve_fx3_mymenu_and_camset_firewall_state(
            pre_op_pages_item_counts=(1,),
            active_sub_operation="Delete Item",
        )
        self.assertEqual(s_del["expected_post_reset_pages_item_counts"], ())
        self.assertEqual(s_del["expected_post_reset_total_items"], 0)

    def test_51_g98_invalid_body_telemetry_or_negative_mutation_bytes_blocks(
        self,
    ) -> None:
        self.assertEqual(FX3_MODEL_NAME, "ILME-FX3")
        self.assertEqual(FX3_MODEL_ID, 0x91030080)
        self.assertEqual(FX3_DEFAULT_FW_VERSION_PHASE252, "7.02")
        self.assertEqual(FX3_HELP_GUIDE_CODE_PHASE252, "ilc/2210")
        r = verify_mymenu_6op_persistence_and_slot1_camset_firewall_guard(
            body_model_id=0xDEADBEEF
        )
        self.assertFalse(r.valid)
        self.assertEqual(r.status, STATUS_BLOCKED_G98_TELEMETRY_INVALID)

        r_neg = verify_mymenu_6op_persistence_and_slot1_camset_firewall_guard(
            slot1_mymenu_vault_mutation_bytes=-1
        )
        self.assertFalse(r_neg.valid)
        self.assertEqual(r_neg.status, STATUS_BLOCKED_G98_TELEMETRY_INVALID)

    def test_52_g98_persistent_emmc_write_request_blocks_fail_closed(self) -> None:
        verdict, res = evaluate_g98_mymenu_and_camset_firewall_guard(
            force_clean_room=True, request_persistent_emmc_writes=True
        )
        self.assertFalse(verdict.passed)
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)


    # ------------------------------------------------------------------
    # Section D: Unified 98-Gate Master Preflight & CLI Contracts (53..68)
    # ------------------------------------------------------------------

    def test_53_active_offline_98gate_preflight_passes_95_of_98_redlines_locked(
        self,
    ) -> None:
        rep = self.active_offline_98
        self.assertEqual(rep.summary["total_gates"], 98)
        self.assertEqual(rep.summary["verified_gates"], 95)
        self.assertEqual(rep.summary["blocked_or_pending_gates"], 3)
        self.assertTrue(rep.offline_95_gates_verified)
        self.assertFalse(rep.all_98_gates_verified)
        self.assertTrue(rep.g97_to_g98_all_passed)
        self.assertTrue(rep.g13_to_g98_all_passed)
        self.assertEqual(rep.status, "VERIFIED_95_OF_98_AWAITING_PHYSICAL_TIER0")
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.hardware_live_attachment_authorized)
        self.assertFalse(rep.el3_payload_transmit_authorized)
        self.assertFalse(rep.spi_nor_write_authorized)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertEqual(rep.usb_packets_transmitted, 0)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_54_clean_room_offline_98gate_preflight_passes_95_of_98(self) -> None:
        rep = self.clean_offline_98
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(rep.clean_room_forced)
        self.assertEqual(rep.summary["verified_gates"], 95)
        self.assertTrue(rep.offline_95_gates_verified)
        self.assertFalse(rep.all_98_gates_verified)

    def test_55_simulated_dry_run_98gate_preflight_passes_all_98_gates(self) -> None:
        rep = self.clean_dryrun_98
        self.assertEqual(rep.summary["total_gates"], 98)
        self.assertEqual(rep.summary["verified_gates"], 98)
        self.assertTrue(rep.all_98_gates_verified)
        self.assertTrue(rep.dry_run_rehearsal_only)
        self.assertEqual(
            rep.status, "VERIFIED_ALL_98_GATES_DRY_RUN_SIMULATED_BACKUP"
        )
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertEqual(rep.usb_packets_transmitted, 0)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_56_preflight_aliases_run_98_gate_preflight_and_master_safety_gates(
        self,
    ) -> None:
        self.assertIs(run_98_gate_preflight, evaluate_98gate_preflight)
        self.assertIs(evaluate_98_master_safety_gates, evaluate_98gate_preflight)

    def test_57_preflight_gates_tuple_ends_with_g97_and_g98(self) -> None:
        self.assertEqual(len(self.clean_offline_98.gates), 98)
        self.assertEqual(self.clean_offline_98.gates[96]["gate_id"], G97_GATE_ID)
        self.assertEqual(self.clean_offline_98.gates[97]["gate_id"], G98_GATE_ID)
        self.assertTrue(self.clean_offline_98.gates[96]["passed"])
        self.assertTrue(self.clean_offline_98.gates[97]["passed"])

    def test_58_preflight_propagates_g97_battery_drain_violation_to_overall_status(
        self,
    ) -> None:
        rep = evaluate_98gate_preflight(
            force_clean_room=True,
            master_96_override=self.clean_offline_96,
            display_quality_bt_rmt_kwargs={"pre_reset_display_quality": "High"},
        )
        self.assertFalse(rep.g97_to_g98_all_passed)
        self.assertFalse(rep.offline_95_gates_verified)
        self.assertFalse(rep.h0_h1_trial_entry_allowed)
        self.assertEqual(
            rep.status, STATUS_BLOCKED_G97_TIER0_BATTERY_HIGH_DISPLAY_OR_BRIGHTNESS_DRAIN
        )

    def test_59_preflight_propagates_g97_ir_sircs_lockout_violation_to_overall_status(
        self,
    ) -> None:
        rep = evaluate_98gate_preflight(
            force_clean_room=True,
            master_96_override=self.clean_offline_96,
            display_quality_bt_rmt_kwargs={
                "pre_reset_bt_rmt_ctrl": "On",
                "ir_remote_command_attempted": True,
            },
        )
        self.assertFalse(rep.g97_to_g98_all_passed)
        self.assertEqual(
            rep.status, STATUS_BLOCKED_G97_BT_RMT_IR_SIRCS_MUTUAL_EXCLUSION_VIOLATION
        )

    def test_60_preflight_propagates_g98_slot1_camset_mutation_to_overall_status(
        self,
    ) -> None:
        rep = evaluate_98gate_preflight(
            force_clean_room=True,
            master_96_override=self.clean_offline_96,
            mymenu_camset_kwargs={"slot1_camset_operation": "SAVE_OVERWRITE"},
        )
        self.assertFalse(rep.g97_to_g98_all_passed)
        self.assertFalse(rep.offline_95_gates_verified)
        self.assertFalse(rep.h0_h1_trial_entry_allowed)
        self.assertEqual(
            rep.status, STATUS_BLOCKED_G98_SLOT1_CAMSET01_FIREWALL_MUTATION_VIOLATION
        )

    def test_61_preflight_blocks_persistent_emmc_write_request(self) -> None:
        rep = evaluate_98gate_preflight(
            force_clean_room=True,
            master_96_override=self.clean_offline_96,
            request_persistent_emmc_writes=True,
        )
        self.assertEqual(rep.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        self.assertFalse(rep.offline_95_gates_verified)
        self.assertFalse(rep.h0_h1_trial_entry_allowed)

    def test_62_preflight_json_serialization_contains_zero_raw_firmware_bytes(
        self,
    ) -> None:
        payload = json.dumps(self.clean_dryrun_98.to_dict())
        parsed = json.loads(payload)
        self.assertEqual(parsed["summary"]["total_gates"], 98)
        self.assertEqual(parsed["summary"]["verified_gates"], 98)
        self.assertEqual(parsed["raw_firmware_bytes_leaked"], 0)

    def test_63_cli_verify_display_quality_bt_rmt_guard_text_json_and_alias(
        self,
    ) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cli_main(
                ["verify-display-quality-bt-rmt-guard", "--force-clean-room"]
            )
        self.assertEqual(rc, 0)
        self.assertIn(G97_GATE_ID, buf.getvalue())

        buf_json = io.StringIO()
        with contextlib.redirect_stdout(buf_json):
            rc_j = cli_main(
                ["verify-g97-display-quality-bt-rmt", "--force-clean-room", "--json"]
            )
        self.assertEqual(rc_j, 0)
        data = json.loads(buf_json.getvalue())
        self.assertTrue(data["valid"])
        self.assertEqual(data["status"], STATUS_VERIFIED_G97)

    def test_64_cli_verify_mymenu_camset_firewall_guard_text_json_and_alias(
        self,
    ) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cli_main(
                ["verify-mymenu-camset-firewall-guard", "--force-clean-room"]
            )
        self.assertEqual(rc, 0)
        self.assertIn(G98_GATE_ID, buf.getvalue())

        buf_json = io.StringIO()
        with contextlib.redirect_stdout(buf_json):
            rc_j = cli_main(
                ["verify-g98-mymenu-camset", "--force-clean-room", "--json"]
            )
        self.assertEqual(rc_j, 0)
        data = json.loads(buf_json.getvalue())
        self.assertTrue(data["valid"])
        self.assertEqual(data["status"], STATUS_VERIFIED_G98)

    def test_65_cli_verify_98_gates_offline_and_dry_run_text_and_json(self) -> None:
        with mock.patch(
            "fx3_safety.realhw_display_quality_bt_rmt_mymenu_and_98gate_guard.evaluate_96gate_preflight",
            return_value=self.clean_offline_96,
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = cli_main(["verify-98-gates", "--force-clean-room"])
            self.assertEqual(rc, 0)
            self.assertIn("verified=95/98", buf.getvalue())

        with mock.patch(
            "fx3_safety.realhw_display_quality_bt_rmt_mymenu_and_98gate_guard.evaluate_96gate_preflight",
            return_value=self.clean_dryrun_96,
        ):
            buf_j = io.StringIO()
            with contextlib.redirect_stdout(buf_j):
                rc_j = cli_main(
                    [
                        "verify-98-gates",
                        "--force-clean-room",
                        "--simulate-bench-dry-run",
                        "--json",
                    ]
                )
            self.assertEqual(rc_j, 0)
            parsed = json.loads(buf_j.getvalue())
            self.assertEqual(parsed["summary"]["verified_gates"], 98)
            self.assertFalse(parsed["overall_ready_for_hardware_attach"])

    def test_66_module_standalone_main_offline_and_dry_run_text_and_json(self) -> None:
        with mock.patch(
            "fx3_safety.realhw_display_quality_bt_rmt_mymenu_and_98gate_guard.evaluate_96gate_preflight",
            return_value=self.clean_offline_96,
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = module_main(["--force-clean-room"])
            self.assertEqual(rc, 0)
            self.assertIn("verified=95/98", buf.getvalue())

        with mock.patch(
            "fx3_safety.realhw_display_quality_bt_rmt_mymenu_and_98gate_guard.evaluate_96gate_preflight",
            return_value=self.clean_dryrun_96,
        ):
            buf_j = io.StringIO()
            with contextlib.redirect_stdout(buf_j):
                rc_j = module_main(
                    ["--force-clean-room", "--simulate-bench-dry-run", "--json"]
                )
            self.assertEqual(rc_j, 0)
            parsed = json.loads(buf_j.getvalue())
            self.assertEqual(parsed["summary"]["verified_gates"], 98)

    def test_67_backward_compatibility_with_96gate_preflight_preserved(self) -> None:
        self.assertEqual(self.active_offline_96.summary["total_gates"], 96)
        self.assertEqual(self.active_offline_96.summary["verified_gates"], 93)
        self.assertEqual(self.clean_dryrun_96.summary["verified_gates"], 96)

    def test_68_env_force_clean_room_truthy_values_recognized(self) -> None:
        for val in ("1", "true", "TRUE", "yes", "YES"):
            with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": val}):
                res = audit_phase252_donor_contracts()
                self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")


if __name__ == "__main__":
    unittest.main()
