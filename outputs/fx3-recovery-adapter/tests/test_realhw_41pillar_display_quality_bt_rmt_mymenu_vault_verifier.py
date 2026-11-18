"""Phase 247 — Dual-mode unit tests for Pillar 41 (`[Display Quality]` `Standard`/`High` survival across
both `[Camera Settings Reset]` and `[Reset Network Set.]` & `NP-FZ100` Tier-0 bench clamp; `[Bluetooth Rmt Ctrl]`
radio prerequisites, zero-RF bench `Airplane Mode=On` suppression, Infrared Remote Commander `SIRCS` lockout &
3-way reset split; `[My Menu Setting]` 6-operation persistence, `[Display From My Menu]` tab behavior & lossless
`O_RDONLY` Slot-1 `CAMSET01.DAT` vault round-trip) and unified `41/41` recovery master
(`verify-41pillar-recovery` / `verify-display-quality-bt-rmt-mymenu-vault`)."""

from __future__ import annotations

from contextlib import redirect_stdout
from dataclasses import replace
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest import mock

import fx3_recovery
from fx3_recovery import __main__ as cli_main
from fx3_recovery import (
    realhw_41pillar_display_quality_bt_rmt_mymenu_vault_verifier as p247,
)
from fx3_recovery.realhw_40pillar_lock_op_parts_audio_timing_exp_step_vault_verifier import (
    MASTER_40_PILLAR_SPECS,
    Master40PillarRecoveryReport,
    evaluate_realhw_40pillar_recovery_master,
)
from fx3_recovery.realhw_41pillar_display_quality_bt_rmt_mymenu_vault_verifier import (
    ALLOW_BOOT_PARTITION_TARGETING,
    ALLOW_DESTRUCTIVE_FASTBOOT,
    ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS,
    ALLOW_PERSISTENT_JIRITSU_WRITES,
    CNFLASHA_USERSPACE_WRITE_BLOCKED,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    ISP_WRITE_AUTHORIZED,
    LIVE_USB_IOKIT_TRANSMIT_ENABLED,
    MASTER_41_PILLAR_COUNT,
    MASTER_41_PILLAR_IDS,
    MASTER_41_PILLAR_SPECS,
    OTP_FUSE_TOUCHES,
    OTP_FUSE_WRITES,
    P247_AIRPLANE_MODE_DEFAULT,
    P247_AIRPLANE_MODE_MENU_PATH,
    P247_BLOCKED_BT_RMT_3WAY_RESET_SPLIT_DRIFT,
    P247_BLOCKED_BT_RMT_PREREQUISITE_OR_ZERO_RF_BENCH_VIOLATION,
    P247_BLOCKED_CAMSET_DISPLAY_QUALITY_OR_BT_RMT_RESTORE_DRIFT,
    P247_BLOCKED_CAMSET_MY_MENU_ROUNDTRIP_DRIFT,
    P247_BLOCKED_DISPLAY_QUALITY_RESET_SURVIVAL_DRIFT,
    P247_BLOCKED_INVALID_DISPLAY_QUALITY_OR_BT_RMT_SPEC,
    P247_BLOCKED_INVALID_MY_MENU_SPEC,
    P247_BLOCKED_IR_REMOTE_USED_WHILE_BT_RMT_CTRL_ON,
    P247_BLOCKED_MY_MENU_OPERATION_OR_TAB_BEHAVIOR_MISMATCH,
    P247_BLOCKED_MY_MENU_RESET_PERSISTENCE_DRIFT,
    P247_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
    P247_BLOCKED_SAFETY_POLICY_VIOLATION,
    P247_BLOCKED_SLOT1_MY_MENU_VAULT_MUTATION_ATTEMPT,
    P247_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
    P247_BLOCKED_TIER0_BATTERY_BENCH_HIGH_DISPLAY_OR_BRIGHTNESS,
    P247_BLUETOOTH_FUNCTION_DEFAULT,
    P247_BLUETOOTH_FUNCTION_MENU_PATH,
    P247_BLUETOOTH_RMT_CTRL_DEFAULT,
    P247_BLUETOOTH_RMT_CTRL_MENU_PATH,
    P247_BT_RMT_IR_LOCKOUT_VIOLATIONS,
    P247_CAMSET_FILENAMES,
    P247_DEFAULT_REGISTERED_MY_MENU_ITEMS,
    P247_DISPLAY_FROM_MY_MENU_DEFAULT,
    P247_DISPLAY_FROM_MY_MENU_MODES,
    P247_DISPLAY_QUALITY_DEFAULT,
    P247_DISPLAY_QUALITY_MENU_PATH,
    P247_DISPLAY_QUALITY_MODES,
    P247_FX3_FW_VERSION,
    P247_FX3_HELPGUIDE_ID,
    P247_FX3_MODEL_ID,
    P247_FX3_MODEL_NAME,
    P247_FX3_SUPPORTED_FW_VERSIONS,
    P247_FX6_DONOR_FW_VERSION,
    P247_FX6_DONOR_MODEL_NAME,
    P247_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    P247_IR_REMOTE_CTRL_MENU_PATH,
    P247_MENU_OPEN_TAB_BEHAVIORS,
    P247_MONITOR_BRIGHTNESS_BENCH_LEVEL,
    P247_MONITOR_BRIGHTNESS_BENCH_MODE,
    P247_MONITOR_BRIGHTNESS_MENU_PATH,
    P247_MY_MENU_6_OPERATIONS,
    P247_MY_MENU_MAX_ITEMS_PER_PAGE,
    P247_MY_MENU_MAX_PAGES,
    P247_MY_MENU_MAX_TOTAL_ITEMS,
    P247_MY_MENU_SETTING_MENU_PATH,
    P247_PILLAR_41A_SCENARIO_IDS,
    P247_PILLAR_41B_SCENARIO_IDS,
    P247_PINNED_FX3_BACKUP_BIN_SHA256,
    P247_PINNED_FX3_LIBGPE_SO_BYTES,
    P247_PINNED_FX3_LIBGPE_SO_SHA256,
    P247_PINNED_FX3_LIBINFRAAIRPLANEMODE_SO_BYTES,
    P247_PINNED_FX3_LIBINFRAAIRPLANEMODE_SO_SHA256,
    P247_PINNED_FX3_LIBINFRABLUETOOTH_SO_BYTES,
    P247_PINNED_FX3_LIBINFRABLUETOOTH_SO_SHA256,
    P247_PINNED_FX6_LIBINFRASIRCS_SO_BYTES,
    P247_PINNED_FX6_LIBINFRASIRCS_SO_SHA256,
    P247_POWER_SOURCES,
    P247_RESET_ACTIONS,
    P247_SLOT1_MYMENU_VAULT_MUTATION_BYTES,
    P247_SLOT1_VAULT_SLOT,
    P247_STATUS_FAIL_41OF41_AGGREGATOR,
    P247_STATUS_FAIL_PILLAR41_SUITE,
    P247_STATUS_VERIFIED_41OF41_AGGREGATOR,
    P247_STATUS_VERIFIED_PILLAR41_SUITE,
    P247_STATUS_VERIFIED_PILLAR_41A,
    P247_STATUS_VERIFIED_PILLAR_41B,
    P247_TIER0_BATTERY_HIGH_DISPLAY_VIOLATIONS,
    PASSIVE_TX_BYTES_EMITTED,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHASE247_SCHEMA,
    PHASE247_VERSION,
    PHYSICAL_DEVICE_WRITES,
    PHYSICAL_USB_PACKETS_EMITTED,
    RAW_FIRMWARE_BYTES_LEAKED,
    READ_ONLY_DONOR_ACCESS,
    RPMB_COUNTER_INCREMENTS,
    SPI_NOR_WRITE_AUTHORIZED,
    DisplayQualityAndBtRmtCtrlVaultSpec,
    Master41PillarRecoveryReport,
    MyMenuPersistenceAndCamsetVaultSpec,
    build_default_safe_display_quality_bt_rmt_vault_spec,
    build_default_safe_my_menu_camset_vault_spec,
    evaluate_41pillar_recovery_master,
    evaluate_display_quality_and_bt_rmt_ctrl_vault,
    evaluate_my_menu_persistence_and_camset_vault,
    evaluate_realhw_41pillar_recovery_master,
    inspect_phase247_donors_readonly,
    run_pillar41_standalone_suite,
    run_pillar41a_display_quality_bt_rmt_vault_6_scenario_suite,
    run_pillar41b_my_menu_camset_vault_6_scenario_suite,
    verify_41pillar_recovery_suite,
    verify_display_quality_bt_rmt_and_mymenu_vault,
)

ADAPTER_ROOT = Path(__file__).resolve().parents[1]

_CACHED_MASTER41_DEFAULT: Master41PillarRecoveryReport | None = None
_CACHED_MASTER41_CLEAN_ROOM: Master41PillarRecoveryReport | None = None
_CACHED_MASTER40_CLEAN_ROOM: Master40PillarRecoveryReport | None = None


def _get_cached_master41_default() -> Master41PillarRecoveryReport:
    global _CACHED_MASTER41_DEFAULT
    if _CACHED_MASTER41_DEFAULT is None:
        _CACHED_MASTER41_DEFAULT = evaluate_realhw_41pillar_recovery_master()
    return _CACHED_MASTER41_DEFAULT


def _get_cached_master41_clean_room() -> Master41PillarRecoveryReport:
    global _CACHED_MASTER41_CLEAN_ROOM
    if _CACHED_MASTER41_CLEAN_ROOM is None:
        _CACHED_MASTER41_CLEAN_ROOM = evaluate_realhw_41pillar_recovery_master(force_clean_room=True)
    return _CACHED_MASTER41_CLEAN_ROOM


def _get_cached_master40_clean_room() -> Master40PillarRecoveryReport:
    global _CACHED_MASTER40_CLEAN_ROOM
    if _CACHED_MASTER40_CLEAN_ROOM is None:
        _CACHED_MASTER40_CLEAN_ROOM = evaluate_realhw_40pillar_recovery_master(force_clean_room=True)
    return _CACHED_MASTER40_CLEAN_ROOM


def _run_inprocess_cli(*argv: str) -> tuple[int, str]:
    buf = io.StringIO()
    with mock.patch.object(sys, "argv", ["fx3_recovery", *argv]), redirect_stdout(buf):
        rc = cli_main.main()
    return rc, buf.getvalue()


class TestPhase247Pillar41And41PillarRecoveryMaster(unittest.TestCase):
    """68 fast dual-mode tests covering Pillar 41A, Pillar 41B, O_RDONLY donors, CLI & 41/41 master."""

    def test_01_hard_locked_zero_write_safety_constants(self) -> None:
        self.assertEqual(PHASE247_SCHEMA, "realhw_41pillar_display_quality_bt_rmt_mymenu_vault_verifier_v1")
        self.assertEqual(PHASE247_VERSION, "1.0.0")
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        self.assertFalse(ISP_WRITE_AUTHORIZED)
        self.assertFalse(PERSISTENT_WRITE_RELEASE)
        self.assertFalse(ALLOW_BOOT_PARTITION_TARGETING)
        self.assertFalse(ALLOW_DESTRUCTIVE_FASTBOOT)
        self.assertFalse(ALLOW_PERSISTENT_JIRITSU_WRITES)
        self.assertFalse(ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS)
        self.assertFalse(LIVE_USB_IOKIT_TRANSMIT_ENABLED)
        self.assertFalse(HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        self.assertFalse(P247_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        self.assertTrue(READ_ONLY_DONOR_ACCESS)
        self.assertTrue(CNFLASHA_USERSPACE_WRITE_BLOCKED)
        self.assertEqual(OTP_FUSE_TOUCHES, 0)
        self.assertEqual(OTP_FUSE_WRITES, 0)
        self.assertEqual(RPMB_COUNTER_INCREMENTS, 0)
        self.assertEqual(PASSIVE_TX_BYTES_EMITTED, 0)
        self.assertEqual(PHYSICAL_USB_PACKETS_EMITTED, 0)
        self.assertEqual(PHYSICAL_DEVICE_WRITES, 0)
        self.assertEqual(RAW_FIRMWARE_BYTES_LEAKED, 0)
        self.assertEqual(P247_TIER0_BATTERY_HIGH_DISPLAY_VIOLATIONS, 0)
        self.assertEqual(P247_BT_RMT_IR_LOCKOUT_VIOLATIONS, 0)
        self.assertEqual(P247_SLOT1_MYMENU_VAULT_MUTATION_BYTES, 0)

    def test_02_wave39_menu_paths_modes_and_model_constants(self) -> None:
        self.assertEqual(P247_FX3_MODEL_NAME, "ILME-FX3")
        self.assertEqual(P247_FX3_MODEL_ID, 0x91030080)
        self.assertEqual(P247_FX3_HELPGUIDE_ID, "ilc/2210")
        self.assertEqual(P247_FX3_FW_VERSION, "7.02")
        self.assertEqual(P247_FX6_DONOR_MODEL_NAME, "ILME-FX6")
        self.assertEqual(P247_FX6_DONOR_FW_VERSION, "6.01")
        self.assertEqual(P247_DISPLAY_QUALITY_MENU_PATH, ("MENU", "Setup", "Monitor", "Display Quality"))
        self.assertEqual(P247_DISPLAY_QUALITY_DEFAULT, "Standard")
        self.assertEqual(P247_DISPLAY_QUALITY_MODES, ("Standard", "High"))
        self.assertEqual(P247_BLUETOOTH_RMT_CTRL_MENU_PATH, ("MENU", "Network", "Bluetooth", "Bluetooth Rmt Ctrl"))
        self.assertEqual(P247_BLUETOOTH_RMT_CTRL_DEFAULT, "Off")
        self.assertEqual(P247_BLUETOOTH_FUNCTION_DEFAULT, "Off")
        self.assertEqual(P247_AIRPLANE_MODE_DEFAULT, "Off")
        self.assertEqual(P247_MY_MENU_SETTING_MENU_PATH, ("MENU", "My Menu", "My Menu Setting"))
        self.assertEqual(
            P247_MY_MENU_6_OPERATIONS,
            ("Add Item", "Sort Item", "Delete Item", "Delete Page", "Delete All", "Display From My Menu"),
        )
        self.assertEqual(P247_DISPLAY_FROM_MY_MENU_DEFAULT, "Off")
        self.assertEqual(P247_DISPLAY_FROM_MY_MENU_MODES, ("Off", "On"))
        self.assertEqual(P247_MENU_OPEN_TAB_BEHAVIORS, ("MOST_RECENT_TAB", "MY_MENU_FIRST"))
        self.assertEqual(P247_RESET_ACTIONS, ("NONE", "Camera Settings Reset", "Reset Network Set.", "Initialize"))

    def test_03_package_exports_complete_and_free_of_duplicates_or_shadowing(self) -> None:
        all_exports = fx3_recovery.__all__
        self.assertEqual(len(p247.__all__), len(set(p247.__all__)))
        self.assertEqual(all_exports.count("realhw_41pillar_display_quality_bt_rmt_mymenu_vault_verifier"), 1)
        shared_safety_syms = {
            "ALLOW_BOOT_PARTITION_TARGETING",
            "ALLOW_DESTRUCTIVE_FASTBOOT",
            "ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS",
            "ALLOW_PERSISTENT_JIRITSU_WRITES",
            "CNFLASHA_USERSPACE_WRITE_BLOCKED",
            "EL3_PAYLOAD_TRANSMIT_AUTHORIZED",
            "HARDWARE_LIVE_ATTACHMENT_AUTHORIZED",
            "ISP_WRITE_AUTHORIZED",
            "LIVE_USB_IOKIT_TRANSMIT_ENABLED",
            "OTP_FUSE_TOUCHES",
            "OTP_FUSE_WRITES",
            "PASSIVE_TX_BYTES_EMITTED",
            "PERSISTENT_EMMC_WRITES_AUTHORIZED",
            "PERSISTENT_WRITE_RELEASE",
            "PHYSICAL_DEVICE_WRITES",
            "PHYSICAL_USB_PACKETS_EMITTED",
            "RAW_FIRMWARE_BYTES_LEAKED",
            "READ_ONLY_DONOR_ACCESS",
            "RPMB_COUNTER_INCREMENTS",
            "SPI_NOR_WRITE_AUTHORIZED",
        }
        for sym in p247.__all__:
            self.assertIn(sym, all_exports)
            self.assertTrue(hasattr(fx3_recovery, sym), f"Missing {sym} on fx3_recovery")
            if sym not in shared_safety_syms:
                self.assertEqual(all_exports.count(sym), 1, f"Duplicate Phase 247 export {sym}")
                self.assertIs(getattr(fx3_recovery, sym), getattr(p247, sym))

    def test_04_donor_inspection_default_mode_under_0_15s_zero_leak(self) -> None:
        snap = inspect_phase247_donors_readonly()
        self.assertIn(snap.verification_mode, ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"))
        self.assertTrue(snap.all_donors_present)
        self.assertEqual(snap.donor_files_inspected, 11)
        self.assertTrue(snap.under_0_15s_budget)
        self.assertLess(snap.elapsed_seconds, 2.0)
        self.assertEqual(snap.raw_firmware_bytes_leaked, 0)
        if os.environ.get("FX3_FX6_FORCE_CLEAN_ROOM") == "1":
            self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_05_donor_inspection_force_clean_room_synthetic_11_artifacts(self) -> None:
        snap = inspect_phase247_donors_readonly(force_clean_room=True)
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(snap.all_donors_present)
        self.assertEqual(snap.donor_files_inspected, 11)
        self.assertEqual(snap.raw_firmware_bytes_leaked, 0)
        by_id = {a.artifact_id: a for a in snap.artifacts}
        self.assertEqual(
            by_id["fx3_libinfrabluetooth_so"].total_bytes, P247_PINNED_FX3_LIBINFRABLUETOOTH_SO_BYTES
        )
        self.assertEqual(
            by_id["fx3_libinfrabluetooth_so"].digest_sha256, P247_PINNED_FX3_LIBINFRABLUETOOTH_SO_SHA256
        )
        self.assertEqual(
            by_id["fx3_libinfraairplanemode_so"].total_bytes, P247_PINNED_FX3_LIBINFRAAIRPLANEMODE_SO_BYTES
        )
        self.assertEqual(
            by_id["fx3_libinfraairplanemode_so"].digest_sha256, P247_PINNED_FX3_LIBINFRAAIRPLANEMODE_SO_SHA256
        )
        self.assertEqual(by_id["fx6_libinfrasircs_so"].total_bytes, P247_PINNED_FX6_LIBINFRASIRCS_SO_BYTES)
        self.assertEqual(by_id["fx6_libinfrasircs_so"].digest_sha256, P247_PINNED_FX6_LIBINFRASIRCS_SO_SHA256)
        self.assertEqual(by_id["fx3_libgpe_so"].total_bytes, P247_PINNED_FX3_LIBGPE_SO_BYTES)
        self.assertEqual(by_id["fx3_libgpe_so"].digest_sha256, P247_PINNED_FX3_LIBGPE_SO_SHA256)

    def test_06_donor_inspection_automatic_clean_room_fallback_when_donors_missing(self) -> None:
        with mock.patch.object(p247, "resolve_donor_path", return_value=None):
            snap = inspect_phase247_donors_readonly(force_clean_room=False)
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(snap.all_donors_present)
        self.assertEqual(snap.donor_files_inspected, 11)

    def test_07_elf64_aarch64_token_helper_validates_headers_and_symbols(self) -> None:
        ok_bad, msg_bad = p247._check_elf64_aarch64_tokens(b"NOT_ELF_DATA", ())
        self.assertFalse(ok_bad)
        self.assertEqual(msg_bad, "NOT_ELF")
        hdr = bytearray(64)
        hdr[:4] = b"\x7fELF"
        hdr[4] = 2
        hdr[5] = 1
        hdr[18:20] = (183).to_bytes(2, "little")
        blob = bytes(hdr) + b"\x00_ZN14InfraBluetoothC1Ev\x00_ZN10InfraSircs4InitEv\x00"
        ok_good, msg_good = p247._check_elf64_aarch64_tokens(
            blob, (b"_ZN14InfraBluetoothC1Ev", b"_ZN10InfraSircs4InitEv")
        )
        self.assertTrue(ok_good)
        self.assertIn("InfraBluetooth", msg_good)
        ok_miss, msg_miss = p247._check_elf64_aarch64_tokens(blob, (b"MissingSym",))
        self.assertFalse(ok_miss)
        self.assertIn("MISSING_TOKENS:MissingSym", msg_miss)

    def test_08_default_safe_display_quality_bt_rmt_spec_passes(self) -> None:
        spec = build_default_safe_display_quality_bt_rmt_vault_spec()
        rep = evaluate_display_quality_and_bt_rmt_ctrl_vault(spec)
        self.assertTrue(rep.passed)
        self.assertEqual(rep.status, P247_STATUS_VERIFIED_PILLAR_41A)
        self.assertIsNone(rep.block_code)
        self.assertTrue(rep.display_quality_reset_survival_verified)
        self.assertTrue(rep.tier0_battery_bench_clamp_verified)
        self.assertTrue(rep.bt_rmt_prerequisite_and_zero_rf_verified)
        self.assertTrue(rep.bt_rmt_ir_remote_lockout_verified)
        self.assertTrue(rep.bt_rmt_3way_reset_split_verified)
        self.assertTrue(rep.h0_equals_h3_verified)
        self.assertEqual(rep.tier0_battery_high_display_violations, 0)
        self.assertEqual(rep.bt_rmt_ir_lockout_violations, 0)
        self.assertEqual(rep.passive_tx_bytes_emitted, 0)
        self.assertEqual(rep.physical_device_writes, 0)
        self.assertFalse(rep.persistent_emmc_writes_authorized)

    def test_09_display_quality_high_survives_both_camera_and_network_resets_on_external_dc(self) -> None:
        for action, expected_bt in (("Camera Settings Reset", "On"), ("Reset Network Set.", "Off")):
            with self.subTest(reset_action=action):
                spec = DisplayQualityAndBtRmtCtrlVaultSpec(
                    pre_reset_display_quality="High",
                    pre_reset_bt_rmt_ctrl="On",
                    reset_action=action,
                    post_reset_display_quality="High",
                    post_reset_bt_rmt_ctrl=expected_bt,
                    power_source="DC-C1",
                    tier0_internal_battery_bench_active=False,
                    ir_remote_ctrl_setting="Off",
                    ir_remote_commander_usable=False,
                )
                rep = evaluate_display_quality_and_bt_rmt_ctrl_vault(spec)
                self.assertTrue(rep.passed, rep.errors)

    def test_10_display_quality_resets_to_standard_only_on_initialize(self) -> None:
        spec_ok = DisplayQualityAndBtRmtCtrlVaultSpec(
            pre_reset_display_quality="High",
            pre_reset_bt_rmt_ctrl="On",
            reset_action="Initialize",
            post_reset_display_quality="Standard",
            post_reset_bt_rmt_ctrl="Off",
        )
        self.assertTrue(evaluate_display_quality_and_bt_rmt_ctrl_vault(spec_ok).passed)

        spec_bad = replace(
            spec_ok,
            post_reset_display_quality="High",
            power_source="DC-C1",
            tier0_internal_battery_bench_active=False,
        )
        rep_bad = evaluate_display_quality_and_bt_rmt_ctrl_vault(spec_bad)
        self.assertFalse(rep_bad.passed)
        self.assertEqual(rep_bad.block_code, P247_BLOCKED_DISPLAY_QUALITY_RESET_SURVIVAL_DRIFT)

    def test_11_display_quality_rejects_false_wipe_by_camera_or_network_reset(self) -> None:
        for action, expected_bt in (("Camera Settings Reset", "On"), ("Reset Network Set.", "Off")):
            with self.subTest(reset_action=action):
                spec = DisplayQualityAndBtRmtCtrlVaultSpec(
                    pre_reset_display_quality="High",
                    pre_reset_bt_rmt_ctrl="On",
                    reset_action=action,
                    post_reset_display_quality="Standard",
                    post_reset_bt_rmt_ctrl=expected_bt,
                    power_source="DC-C1",
                    tier0_internal_battery_bench_active=False,
                )
                rep = evaluate_display_quality_and_bt_rmt_ctrl_vault(spec)
                self.assertFalse(rep.passed)
                self.assertEqual(rep.block_code, P247_BLOCKED_DISPLAY_QUALITY_RESET_SURVIVAL_DRIFT)

    def test_12_tier0_np_fz100_bench_rejects_high_display_quality_or_sunny_weather_brightness(self) -> None:
        spec_high = DisplayQualityAndBtRmtCtrlVaultSpec(
            pre_reset_display_quality="High",
            post_reset_display_quality="High",
            power_source="NP-FZ100",
            tier0_internal_battery_bench_active=True,
        )
        rep_high = evaluate_display_quality_and_bt_rmt_ctrl_vault(spec_high)
        self.assertFalse(rep_high.passed)
        self.assertEqual(rep_high.block_code, P247_BLOCKED_TIER0_BATTERY_BENCH_HIGH_DISPLAY_OR_BRIGHTNESS)
        self.assertGreaterEqual(rep_high.tier0_battery_high_display_violations, 1)

        spec_sunny = DisplayQualityAndBtRmtCtrlVaultSpec(
            monitor_brightness_mode="Sunny Weather",
            power_source="NP-FZ100",
            tier0_internal_battery_bench_active=True,
        )
        rep_sunny = evaluate_display_quality_and_bt_rmt_ctrl_vault(spec_sunny)
        self.assertFalse(rep_sunny.passed)
        self.assertEqual(rep_sunny.block_code, P247_BLOCKED_TIER0_BATTERY_BENCH_HIGH_DISPLAY_OR_BRIGHTNESS)

        spec_lvl = DisplayQualityAndBtRmtCtrlVaultSpec(
            monitor_brightness_mode="Manual",
            monitor_brightness_manual_level=2,
            power_source="NP-FZ100",
            tier0_internal_battery_bench_active=True,
        )
        rep_lvl = evaluate_display_quality_and_bt_rmt_ctrl_vault(spec_lvl)
        self.assertFalse(rep_lvl.passed)
        self.assertEqual(rep_lvl.block_code, P247_BLOCKED_TIER0_BATTERY_BENCH_HIGH_DISPLAY_OR_BRIGHTNESS)

    def test_13_bt_rmt_ctrl_3way_reset_split_exact_matrix(self) -> None:
        matrix = (
            ("NONE", "On", "On", True),
            ("Camera Settings Reset", "On", "On", True),
            ("Camera Settings Reset", "On", "Off", False),
            ("Reset Network Set.", "On", "Off", True),
            ("Reset Network Set.", "On", "On", False),
            ("Initialize", "On", "Off", True),
            ("Initialize", "On", "On", False),
        )
        for action, pre_bt, post_bt, expected_ok in matrix:
            with self.subTest(action=action, post_bt=post_bt):
                spec = DisplayQualityAndBtRmtCtrlVaultSpec(
                    pre_reset_bt_rmt_ctrl=pre_bt,
                    reset_action=action,
                    post_reset_bt_rmt_ctrl=post_bt,
                    ir_remote_ctrl_setting="Off",
                    ir_remote_commander_usable=False,
                )
                rep = evaluate_display_quality_and_bt_rmt_ctrl_vault(spec)
                self.assertEqual(rep.passed, expected_ok)
                if not expected_ok:
                    self.assertEqual(rep.block_code, P247_BLOCKED_BT_RMT_3WAY_RESET_SPLIT_DRIFT)

    def test_14_bt_rmt_ctrl_ir_remote_commander_mutual_exclusion(self) -> None:
        spec_locked = DisplayQualityAndBtRmtCtrlVaultSpec(
            pre_reset_bt_rmt_ctrl="On",
            reset_action="Camera Settings Reset",
            post_reset_bt_rmt_ctrl="On",
            ir_remote_ctrl_setting="On",
            ir_remote_commander_usable=False,
        )
        self.assertTrue(evaluate_display_quality_and_bt_rmt_ctrl_vault(spec_locked).passed)

        spec_violated = replace(spec_locked, ir_remote_commander_usable=True)
        rep_v = evaluate_display_quality_and_bt_rmt_ctrl_vault(spec_violated)
        self.assertFalse(rep_v.passed)
        self.assertEqual(rep_v.block_code, P247_BLOCKED_IR_REMOTE_USED_WHILE_BT_RMT_CTRL_ON)
        self.assertGreaterEqual(rep_v.bt_rmt_ir_lockout_violations, 1)

        spec_unlocked_after_net_reset = DisplayQualityAndBtRmtCtrlVaultSpec(
            pre_reset_bt_rmt_ctrl="On",
            reset_action="Reset Network Set.",
            post_reset_bt_rmt_ctrl="Off",
            ir_remote_ctrl_setting="On",
            ir_remote_commander_usable=True,
        )
        self.assertTrue(evaluate_display_quality_and_bt_rmt_ctrl_vault(spec_unlocked_after_net_reset).passed)

    def test_15_bt_rmt_ctrl_prerequisites_and_zero_rf_bench_suppression(self) -> None:
        # Non-bench scenario: active only when Bluetooth Rmt Ctrl=On AND Bluetooth Function=On AND Airplane Mode=Off
        spec_field_active = DisplayQualityAndBtRmtCtrlVaultSpec(
            pre_reset_bt_rmt_ctrl="On",
            reset_action="NONE",
            post_reset_bt_rmt_ctrl="On",
            bluetooth_function="On",
            airplane_mode="Off",
            zero_rf_bench_enforced=False,
            effective_bt_rmt_ctrl_active=True,
            passive_rf_tx_bytes=0,
            ir_remote_ctrl_setting="On",
            ir_remote_commander_usable=False,
        )
        self.assertTrue(evaluate_display_quality_and_bt_rmt_ctrl_vault(spec_field_active).passed)

        # Zero-RF bench rejects Airplane Mode=Off or passive RF TX > 0
        spec_zero_rf_breach = replace(spec_field_active, zero_rf_bench_enforced=True)
        rep_breach = evaluate_display_quality_and_bt_rmt_ctrl_vault(spec_zero_rf_breach)
        self.assertFalse(rep_breach.passed)
        self.assertEqual(rep_breach.block_code, P247_BLOCKED_BT_RMT_PREREQUISITE_OR_ZERO_RF_BENCH_VIOLATION)

        spec_tx_leak = DisplayQualityAndBtRmtCtrlVaultSpec(passive_rf_tx_bytes=64)
        rep_tx = evaluate_display_quality_and_bt_rmt_ctrl_vault(spec_tx_leak)
        self.assertFalse(rep_tx.passed)
        self.assertEqual(rep_tx.block_code, P247_BLOCKED_BT_RMT_PREREQUISITE_OR_ZERO_RF_BENCH_VIOLATION)

    def test_16_camset01_restore_for_display_quality_and_bt_rmt_ctrl(self) -> None:
        spec_ok = DisplayQualityAndBtRmtCtrlVaultSpec(
            pre_reset_display_quality="High",
            pre_reset_bt_rmt_ctrl="On",
            reset_action="Initialize",
            camset_load_after_reset=True,
            camset_slot=1,
            camset_filename="CAMSET01.DAT",
            saved_display_quality="Standard",
            saved_bt_rmt_ctrl="On",
            post_reset_display_quality="Standard",
            post_reset_bt_rmt_ctrl="On",
        )
        rep_ok = evaluate_display_quality_and_bt_rmt_ctrl_vault(spec_ok)
        self.assertTrue(rep_ok.passed)
        self.assertTrue(rep_ok.camset_slot1_restore_verified)

        spec_drift_dq = replace(
            spec_ok,
            saved_display_quality="High",
            post_reset_display_quality="Standard",
        )
        rep_dq = evaluate_display_quality_and_bt_rmt_ctrl_vault(spec_drift_dq)
        self.assertFalse(rep_dq.passed)
        self.assertEqual(rep_dq.block_code, P247_BLOCKED_CAMSET_DISPLAY_QUALITY_OR_BT_RMT_RESTORE_DRIFT)

        spec_drift_bt = replace(spec_ok, saved_bt_rmt_ctrl="Off", post_reset_bt_rmt_ctrl="On")
        rep_bt = evaluate_display_quality_and_bt_rmt_ctrl_vault(spec_drift_bt)
        self.assertFalse(rep_bt.passed)
        self.assertEqual(rep_bt.block_code, P247_BLOCKED_CAMSET_DISPLAY_QUALITY_OR_BT_RMT_RESTORE_DRIFT)

    def test_17_pillar41a_rejects_invalid_model_menu_paths_or_false_drain_claim(self) -> None:
        for kw in (
            {"camera_model": "ILME-FX6"},
            {"helpguide_id": "ilc/2310"},
            {"fw_version": "1.00"},
            {"display_quality_menu_path": ("MENU", "Shooting", "Display Quality")},
            {"bt_rmt_ctrl_menu_path": ("MENU", "Setup", "Bluetooth Rmt Ctrl")},
            {"high_mode_increases_np_fz100_drain": False},
            {"camset_slot": 2, "camset_filename": "CAMSET01.DAT"},
        ):
            with self.subTest(kw=kw):
                rep = evaluate_display_quality_and_bt_rmt_ctrl_vault(DisplayQualityAndBtRmtCtrlVaultSpec(**kw))
                self.assertFalse(rep.passed)
                self.assertEqual(rep.block_code, P247_BLOCKED_INVALID_DISPLAY_QUALITY_OR_BT_RMT_SPEC)

    def test_18_pillar41a_rejects_persistent_overlay_escape_and_h0_h3_drift(self) -> None:
        rep_esc = evaluate_display_quality_and_bt_rmt_ctrl_vault(
            DisplayQualityAndBtRmtCtrlVaultSpec(overlay_dir="/setting/escaped")
        )
        self.assertFalse(rep_esc.passed)
        self.assertEqual(rep_esc.block_code, P247_BLOCKED_PERSISTENT_OVERLAY_ESCAPE)

        rep_ro = evaluate_display_quality_and_bt_rmt_ctrl_vault(
            DisplayQualityAndBtRmtCtrlVaultSpec(p2_blkroset_locked=False)
        )
        self.assertFalse(rep_ro.passed)
        self.assertEqual(rep_ro.block_code, P247_BLOCKED_PERSISTENT_OVERLAY_ESCAPE)

        rep_h = evaluate_display_quality_and_bt_rmt_ctrl_vault(
            DisplayQualityAndBtRmtCtrlVaultSpec(backup_bin_h3_sha256="0" * 64)
        )
        self.assertFalse(rep_h.passed)
        self.assertEqual(rep_h.block_code, P247_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT)

    def test_19_pillar41a_rejects_persistent_write_unlock_request(self) -> None:
        rep = evaluate_display_quality_and_bt_rmt_ctrl_vault(
            DisplayQualityAndBtRmtCtrlVaultSpec(persistent_write_unlock_requested=True)
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P247_BLOCKED_SAFETY_POLICY_VIOLATION)

    def test_20_pillar41a_6_scenario_suite_passes_all_6(self) -> None:
        res = run_pillar41a_display_quality_bt_rmt_vault_6_scenario_suite()
        self.assertTrue(res.passed)
        self.assertEqual(res.status, P247_STATUS_VERIFIED_PILLAR_41A)
        self.assertEqual(res.scenarios_total, 6)
        self.assertEqual(res.scenarios_passed, 6)
        self.assertEqual(tuple(s.scenario_id for s in res.scenarios), P247_PILLAR_41A_SCENARIO_IDS)
        self.assertEqual([s.expected_allowed for s in res.scenarios], [True, True, False, False, False, False])

    def test_21_default_safe_my_menu_camset_spec_passes(self) -> None:
        spec = build_default_safe_my_menu_camset_vault_spec()
        rep = evaluate_my_menu_persistence_and_camset_vault(spec)
        self.assertTrue(rep.passed)
        self.assertEqual(rep.status, P247_STATUS_VERIFIED_PILLAR_41B)
        self.assertIsNone(rep.block_code)
        self.assertTrue(rep.my_menu_6_operations_and_tab_verified)
        self.assertTrue(rep.my_menu_non_resettable_survival_verified)
        self.assertTrue(rep.initialize_full_clear_verified)
        self.assertTrue(rep.camset_slot1_roundtrip_verified)
        self.assertTrue(rep.slot1_vault_zero_mutation_verified)
        self.assertTrue(rep.h0_equals_h3_verified)
        self.assertEqual(rep.slot1_mymenu_vault_mutation_bytes, 0)
        self.assertEqual(rep.physical_device_writes, 0)
        self.assertFalse(rep.persistent_emmc_writes_authorized)

    def test_22_my_menu_add_item_operation_valid_and_invalid_transitions(self) -> None:
        items_after = P247_DEFAULT_REGISTERED_MY_MENU_ITEMS + ("Bluetooth Rmt Ctrl",)
        spec_ok = MyMenuPersistenceAndCamsetVaultSpec(
            pre_op_registered_items=P247_DEFAULT_REGISTERED_MY_MENU_ITEMS,
            pre_op_page_item_counts=(4,),
            my_menu_operation="Add Item",
            operation_target_item="Bluetooth Rmt Ctrl",
            post_op_registered_items=items_after,
            post_op_page_item_counts=(5,),
            post_reset_registered_items=items_after,
            post_reset_page_item_counts=(5,),
        )
        self.assertTrue(evaluate_my_menu_persistence_and_camset_vault(spec_ok).passed)

        # Reject Add Item when target was already registered
        spec_dup_target = MyMenuPersistenceAndCamsetVaultSpec(
            pre_op_registered_items=P247_DEFAULT_REGISTERED_MY_MENU_ITEMS,
            pre_op_page_item_counts=(4,),
            my_menu_operation="Add Item",
            operation_target_item="Display Quality",
            post_op_registered_items=P247_DEFAULT_REGISTERED_MY_MENU_ITEMS,
            post_op_page_item_counts=(4,),
            post_reset_registered_items=P247_DEFAULT_REGISTERED_MY_MENU_ITEMS,
            post_reset_page_item_counts=(4,),
        )
        rep_bad = evaluate_my_menu_persistence_and_camset_vault(spec_dup_target)
        self.assertFalse(rep_bad.passed)
        self.assertEqual(rep_bad.block_code, P247_BLOCKED_MY_MENU_OPERATION_OR_TAB_BEHAVIOR_MISMATCH)

    def test_23_my_menu_sort_item_operation_permutation_invariant(self) -> None:
        reordered = tuple(reversed(P247_DEFAULT_REGISTERED_MY_MENU_ITEMS))
        spec_ok = MyMenuPersistenceAndCamsetVaultSpec(
            pre_op_registered_items=P247_DEFAULT_REGISTERED_MY_MENU_ITEMS,
            pre_op_page_item_counts=(4,),
            my_menu_operation="Sort Item",
            post_op_registered_items=reordered,
            post_op_page_item_counts=(4,),
            post_reset_registered_items=reordered,
            post_reset_page_item_counts=(4,),
        )
        self.assertTrue(evaluate_my_menu_persistence_and_camset_vault(spec_ok).passed)

        substituted = ("Zebra Display",) + P247_DEFAULT_REGISTERED_MY_MENU_ITEMS[1:]
        spec_bad = replace(
            spec_ok,
            post_op_registered_items=substituted,
            post_reset_registered_items=substituted,
        )
        rep_bad = evaluate_my_menu_persistence_and_camset_vault(spec_bad)
        self.assertFalse(rep_bad.passed)
        self.assertEqual(rep_bad.block_code, P247_BLOCKED_MY_MENU_OPERATION_OR_TAB_BEHAVIOR_MISMATCH)

    def test_24_my_menu_delete_item_operation(self) -> None:
        rem = tuple(x for x in P247_DEFAULT_REGISTERED_MY_MENU_ITEMS if x != "Monitor Brightness")
        spec_ok = MyMenuPersistenceAndCamsetVaultSpec(
            pre_op_registered_items=P247_DEFAULT_REGISTERED_MY_MENU_ITEMS,
            pre_op_page_item_counts=(4,),
            my_menu_operation="Delete Item",
            operation_target_item="Monitor Brightness",
            post_op_registered_items=rem,
            post_op_page_item_counts=(3,),
            post_reset_registered_items=rem,
            post_reset_page_item_counts=(3,),
        )
        self.assertTrue(evaluate_my_menu_persistence_and_camset_vault(spec_ok).passed)

        spec_bad = replace(spec_ok, operation_target_item="NonExistentItem")
        rep_bad = evaluate_my_menu_persistence_and_camset_vault(spec_bad)
        self.assertFalse(rep_bad.passed)
        self.assertEqual(rep_bad.block_code, P247_BLOCKED_MY_MENU_OPERATION_OR_TAB_BEHAVIOR_MISMATCH)

    def test_25_my_menu_delete_page_operation_across_multi_page_layout(self) -> None:
        two_page_items = (
            "Display Quality",
            "Monitor Brightness",
            "Lock Operation Parts",
            "Save/Load Settings",
            "Zebra Display",
            "Audio Out Timing",
        )
        # Page 0 has 4 items, Page 1 has 2 items; deleting Page 0 leaves Page 1's 2 items
        rem_items = ("Zebra Display", "Audio Out Timing")
        spec_ok = MyMenuPersistenceAndCamsetVaultSpec(
            pre_op_registered_items=two_page_items,
            pre_op_page_item_counts=(4, 2),
            my_menu_operation="Delete Page",
            operation_target_page_index=0,
            post_op_registered_items=rem_items,
            post_op_page_item_counts=(2,),
            post_reset_registered_items=rem_items,
            post_reset_page_item_counts=(2,),
        )
        self.assertTrue(evaluate_my_menu_persistence_and_camset_vault(spec_ok).passed)

        spec_oob = replace(spec_ok, operation_target_page_index=3)
        rep_oob = evaluate_my_menu_persistence_and_camset_vault(spec_oob)
        self.assertFalse(rep_oob.passed)
        self.assertEqual(rep_oob.block_code, P247_BLOCKED_MY_MENU_OPERATION_OR_TAB_BEHAVIOR_MISMATCH)

    def test_26_my_menu_delete_all_clears_all_pages_and_rejects_residual_items(self) -> None:
        spec_ok = MyMenuPersistenceAndCamsetVaultSpec(
            pre_op_registered_items=P247_DEFAULT_REGISTERED_MY_MENU_ITEMS,
            pre_op_page_item_counts=(4,),
            my_menu_operation="Delete All",
            post_op_registered_items=(),
            post_op_page_item_counts=(),
            reset_action="NONE",
            post_reset_registered_items=(),
            post_reset_page_item_counts=(),
        )
        self.assertTrue(evaluate_my_menu_persistence_and_camset_vault(spec_ok).passed)

        spec_residual = replace(
            spec_ok,
            post_op_registered_items=("Display Quality",),
            post_op_page_item_counts=(1,),
            post_reset_registered_items=("Display Quality",),
            post_reset_page_item_counts=(1,),
        )
        rep_res = evaluate_my_menu_persistence_and_camset_vault(spec_residual)
        self.assertFalse(rep_res.passed)
        self.assertEqual(rep_res.block_code, P247_BLOCKED_MY_MENU_OPERATION_OR_TAB_BEHAVIOR_MISMATCH)

    def test_27_display_from_my_menu_tab_behavior_off_vs_on(self) -> None:
        spec_off = MyMenuPersistenceAndCamsetVaultSpec(
            pre_reset_display_from_my_menu="Off",
            post_reset_display_from_my_menu="Off",
            menu_button_opens_tab="MOST_RECENT_TAB",
        )
        self.assertTrue(evaluate_my_menu_persistence_and_camset_vault(spec_off).passed)

        spec_on = MyMenuPersistenceAndCamsetVaultSpec(
            pre_reset_display_from_my_menu="On",
            post_reset_display_from_my_menu="On",
            menu_button_opens_tab="MY_MENU_FIRST",
        )
        self.assertTrue(evaluate_my_menu_persistence_and_camset_vault(spec_on).passed)

        spec_inverted = replace(spec_off, menu_button_opens_tab="MY_MENU_FIRST")
        rep_inv = evaluate_my_menu_persistence_and_camset_vault(spec_inverted)
        self.assertFalse(rep_inv.passed)
        self.assertEqual(rep_inv.block_code, P247_BLOCKED_MY_MENU_OPERATION_OR_TAB_BEHAVIOR_MISMATCH)

    def test_28_my_menu_survives_both_camera_settings_reset_and_reset_network_set(self) -> None:
        for action in ("NONE", "Camera Settings Reset", "Reset Network Set."):
            with self.subTest(reset_action=action):
                spec = MyMenuPersistenceAndCamsetVaultSpec(
                    reset_action=action,
                    pre_reset_display_from_my_menu="On",
                    post_reset_display_from_my_menu="On",
                    menu_button_opens_tab="MY_MENU_FIRST",
                )
                self.assertTrue(evaluate_my_menu_persistence_and_camset_vault(spec).passed)

                spec_wiped = replace(
                    spec,
                    post_reset_registered_items=(),
                    post_reset_page_item_counts=(),
                    post_reset_display_from_my_menu="Off",
                    menu_button_opens_tab="MOST_RECENT_TAB",
                )
                rep_w = evaluate_my_menu_persistence_and_camset_vault(spec_wiped)
                self.assertFalse(rep_w.passed)
                self.assertEqual(rep_w.block_code, P247_BLOCKED_MY_MENU_RESET_PERSISTENCE_DRIFT)

    def test_29_initialize_wipes_my_menu_pages_and_resets_display_from_my_menu_to_off(self) -> None:
        spec_init = MyMenuPersistenceAndCamsetVaultSpec(
            reset_action="Initialize",
            pre_reset_display_from_my_menu="On",
            post_reset_registered_items=(),
            post_reset_page_item_counts=(),
            post_reset_display_from_my_menu="Off",
            menu_button_opens_tab="MOST_RECENT_TAB",
        )
        rep_ok = evaluate_my_menu_persistence_and_camset_vault(spec_init)
        self.assertTrue(rep_ok.passed)
        self.assertTrue(rep_ok.initialize_full_clear_verified)

        spec_not_cleared = replace(
            spec_init,
            post_reset_registered_items=P247_DEFAULT_REGISTERED_MY_MENU_ITEMS,
            post_reset_page_item_counts=(4,),
        )
        rep_bad = evaluate_my_menu_persistence_and_camset_vault(spec_not_cleared)
        self.assertFalse(rep_bad.passed)
        self.assertEqual(rep_bad.block_code, P247_BLOCKED_MY_MENU_RESET_PERSISTENCE_DRIFT)

    def test_30_camset01_ordonly_load_roundtrip_restores_my_menu_after_initialize(self) -> None:
        spec_restore = MyMenuPersistenceAndCamsetVaultSpec(
            reset_action="Initialize",
            camset_load_after_reset=True,
            camset_slot=P247_SLOT1_VAULT_SLOT,
            camset_filename="CAMSET01.DAT",
            camset_source_model="ILME-FX3",
            camset_read_only_load=True,
            saved_registered_items=P247_DEFAULT_REGISTERED_MY_MENU_ITEMS,
            saved_page_item_counts=(4,),
            saved_display_from_my_menu="On",
            post_reset_registered_items=P247_DEFAULT_REGISTERED_MY_MENU_ITEMS,
            post_reset_page_item_counts=(4,),
            post_reset_display_from_my_menu="On",
            menu_button_opens_tab="MY_MENU_FIRST",
        )
        rep = evaluate_my_menu_persistence_and_camset_vault(spec_restore)
        self.assertTrue(rep.passed)
        self.assertTrue(rep.camset_slot1_roundtrip_verified)
        self.assertEqual(rep.slot1_mymenu_vault_mutation_bytes, 0)

        spec_drift = replace(spec_restore, post_reset_display_from_my_menu="Off", menu_button_opens_tab="MOST_RECENT_TAB")
        rep_d = evaluate_my_menu_persistence_and_camset_vault(spec_drift)
        self.assertFalse(rep_d.passed)
        self.assertEqual(rep_d.block_code, P247_BLOCKED_CAMSET_MY_MENU_ROUNDTRIP_DRIFT)

    def test_31_slot1_tier0_vault_blocks_save_overwrite_unlocked_wp_or_rw_load(self) -> None:
        for kw in (
            {"camset_save_to_slot1_attempted": True},
            {"slot1_sdxc_wp_locked": False},
            {"camset_load_after_reset": True, "camset_read_only_load": False},
            {"slot1_mymenu_vault_mutation_bytes": 512},
        ):
            with self.subTest(kw=kw):
                rep = evaluate_my_menu_persistence_and_camset_vault(MyMenuPersistenceAndCamsetVaultSpec(**kw))
                self.assertFalse(rep.passed)
                self.assertEqual(rep.block_code, P247_BLOCKED_SLOT1_MY_MENU_VAULT_MUTATION_ATTEMPT)
                self.assertGreaterEqual(rep.slot1_mymenu_vault_mutation_bytes, 1)

    def test_32_pillar41b_rejects_invalid_capacity_or_duplicate_items(self) -> None:
        self.assertEqual(P247_MY_MENU_MAX_PAGES, 5)
        self.assertEqual(P247_MY_MENU_MAX_ITEMS_PER_PAGE, 6)
        self.assertEqual(P247_MY_MENU_MAX_TOTAL_ITEMS, 30)

        # > 6 items on a single page
        seven_items = tuple(f"Item_{i}" for i in range(7))
        rep_7 = evaluate_my_menu_persistence_and_camset_vault(
            MyMenuPersistenceAndCamsetVaultSpec(
                pre_op_registered_items=seven_items,
                pre_op_page_item_counts=(7,),
                post_op_registered_items=seven_items,
                post_op_page_item_counts=(7,),
                post_reset_registered_items=seven_items,
                post_reset_page_item_counts=(7,),
            )
        )
        self.assertFalse(rep_7.passed)
        self.assertEqual(rep_7.block_code, P247_BLOCKED_INVALID_MY_MENU_SPEC)

        # > 5 pages
        six_pages_items = tuple(f"Item_{i}" for i in range(6))
        rep_6p = evaluate_my_menu_persistence_and_camset_vault(
            MyMenuPersistenceAndCamsetVaultSpec(
                pre_op_registered_items=six_pages_items,
                pre_op_page_item_counts=(1, 1, 1, 1, 1, 1),
                post_op_registered_items=six_pages_items,
                post_op_page_item_counts=(1, 1, 1, 1, 1, 1),
                post_reset_registered_items=six_pages_items,
                post_reset_page_item_counts=(1, 1, 1, 1, 1, 1),
            )
        )
        self.assertFalse(rep_6p.passed)
        self.assertEqual(rep_6p.block_code, P247_BLOCKED_INVALID_MY_MENU_SPEC)

        # Duplicate item in My Menu
        dup_items = ("Display Quality", "Display Quality")
        rep_dup = evaluate_my_menu_persistence_and_camset_vault(
            MyMenuPersistenceAndCamsetVaultSpec(
                pre_op_registered_items=dup_items,
                pre_op_page_item_counts=(2,),
                post_op_registered_items=dup_items,
                post_op_page_item_counts=(2,),
                post_reset_registered_items=dup_items,
                post_reset_page_item_counts=(2,),
            )
        )
        self.assertFalse(rep_dup.passed)
        self.assertEqual(rep_dup.block_code, P247_BLOCKED_INVALID_MY_MENU_SPEC)

    def test_33_pillar41b_rejects_overlay_escape_h0_h3_drift_and_unlock_request(self) -> None:
        rep_esc = evaluate_my_menu_persistence_and_camset_vault(
            MyMenuPersistenceAndCamsetVaultSpec(overlay_dir="/dev/cnflasha")
        )
        self.assertFalse(rep_esc.passed)
        self.assertEqual(rep_esc.block_code, P247_BLOCKED_PERSISTENT_OVERLAY_ESCAPE)

        rep_h = evaluate_my_menu_persistence_and_camset_vault(
            MyMenuPersistenceAndCamsetVaultSpec(tier0_surfaces_h0_h3_matched=15)
        )
        self.assertFalse(rep_h.passed)
        self.assertEqual(rep_h.block_code, P247_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT)

        rep_unlock = evaluate_my_menu_persistence_and_camset_vault(
            MyMenuPersistenceAndCamsetVaultSpec(persistent_write_unlock_requested=True)
        )
        self.assertFalse(rep_unlock.passed)
        self.assertEqual(rep_unlock.block_code, P247_BLOCKED_SAFETY_POLICY_VIOLATION)

    def test_34_pillar41b_6_scenario_suite_passes_all_6(self) -> None:
        res = run_pillar41b_my_menu_camset_vault_6_scenario_suite()
        self.assertTrue(res.passed)
        self.assertEqual(res.status, P247_STATUS_VERIFIED_PILLAR_41B)
        self.assertEqual(res.scenarios_total, 6)
        self.assertEqual(res.scenarios_passed, 6)
        self.assertEqual(tuple(s.scenario_id for s in res.scenarios), P247_PILLAR_41B_SCENARIO_IDS)
        self.assertEqual([s.expected_allowed for s in res.scenarios], [True, True, False, False, False, False])

    def test_35_combined_verify_display_quality_bt_rmt_and_mymenu_vault_dual_mode(self) -> None:
        for force_cr in (None, True):
            with self.subTest(force_clean_room=force_cr):
                rep = verify_display_quality_bt_rmt_and_mymenu_vault(force_clean_room=force_cr)
                self.assertTrue(rep.all_passed)
                self.assertTrue(rep.passed)
                self.assertEqual(rep.status, P247_STATUS_VERIFIED_PILLAR41_SUITE)
                self.assertEqual(rep.tier0_battery_high_display_violations, 0)
                self.assertEqual(rep.bt_rmt_ir_lockout_violations, 0)
                self.assertEqual(rep.slot1_mymenu_vault_mutation_bytes, 0)
                self.assertFalse(rep.hardware_live_attachment_authorized)
                self.assertTrue(rep.cnflasha_userspace_write_blocked)
                self.assertFalse(rep.persistent_emmc_writes_authorized)
                self.assertEqual(rep.passive_tx_bytes_emitted, 0)
                self.assertEqual(rep.physical_usb_packets_emitted, 0)
                self.assertEqual(rep.physical_device_writes, 0)
                self.assertEqual(rep.raw_firmware_bytes_leaked, 0)
                d = rep.to_dict()
                self.assertEqual(d["schema"], PHASE247_SCHEMA)

    def test_36_combined_verify_propagates_pillar41a_and_pillar41b_failures(self) -> None:
        rep_fail_a = verify_display_quality_bt_rmt_and_mymenu_vault(
            display_bt_spec=DisplayQualityAndBtRmtCtrlVaultSpec(
                post_reset_display_quality="High",
                power_source="NP-FZ100",
                tier0_internal_battery_bench_active=True,
            ),
            force_clean_room=True,
        )
        self.assertFalse(rep_fail_a.all_passed)
        self.assertEqual(rep_fail_a.status, P247_STATUS_FAIL_PILLAR41_SUITE)

        rep_fail_b = verify_display_quality_bt_rmt_and_mymenu_vault(
            my_menu_spec=MyMenuPersistenceAndCamsetVaultSpec(camset_save_to_slot1_attempted=True),
            force_clean_room=True,
        )
        self.assertFalse(rep_fail_b.all_passed)
        self.assertEqual(rep_fail_b.status, P247_STATUS_FAIL_PILLAR41_SUITE)

    def test_37_standalone_pillar41_suite_dual_mode_deterministic_digest(self) -> None:
        rep_default = run_pillar41_standalone_suite()
        self.assertTrue(rep_default.all_passed)
        self.assertEqual(rep_default.status, P247_STATUS_VERIFIED_PILLAR41_SUITE)
        self.assertEqual(rep_default.pillar_41a_display_quality_bt_rmt_vault.scenarios_passed, 6)
        self.assertEqual(rep_default.pillar_41b_my_menu_camset_vault.scenarios_passed, 6)

        rep_cr1 = run_pillar41_standalone_suite(force_clean_room=True)
        rep_cr2 = run_pillar41_standalone_suite(force_clean_room=True)
        self.assertTrue(rep_cr1.all_passed)
        self.assertEqual(rep_cr1.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(rep_cr1.suite_sha256, rep_cr2.suite_sha256)
        self.assertEqual(len(rep_cr1.suite_sha256), 64)

    def test_38_master_41_pillar_specs_extend_master_40_cleanly(self) -> None:
        self.assertEqual(MASTER_41_PILLAR_COUNT, 41)
        self.assertEqual(len(MASTER_41_PILLAR_SPECS), 41)
        self.assertEqual(len(MASTER_41_PILLAR_IDS), 41)
        self.assertEqual(len(set(MASTER_41_PILLAR_IDS)), 41)
        self.assertEqual(MASTER_41_PILLAR_SPECS[:40], MASTER_40_PILLAR_SPECS)
        self.assertEqual(
            MASTER_41_PILLAR_SPECS[40],
            (
                41,
                "pillar_41_display_quality_bt_rmt_mymenu_vault",
                "Phase 247",
                "fx3_recovery.realhw_41pillar_display_quality_bt_rmt_mymenu_vault_verifier",
            ),
        )

    def test_39_master_41pillar_default_mode_41_of_41_verified_under_budget(self) -> None:
        rep = _get_cached_master41_default()
        self.assertTrue(rep.all_passed)
        self.assertEqual(rep.status, P247_STATUS_VERIFIED_41OF41_AGGREGATOR)
        self.assertEqual(rep.pillar_count, 41)
        self.assertEqual(rep.pillars_passed, 41)
        self.assertEqual(rep.failed_pillars, ())
        self.assertTrue(rep.under_6s_budget)
        self.assertTrue(rep.nominal_under_4_0s)
        self.assertLess(rep.elapsed_seconds, 4.0)

    def test_40_master_41pillar_clean_room_mode_41_of_41_verified(self) -> None:
        rep = _get_cached_master41_clean_room()
        self.assertTrue(rep.all_passed)
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(rep.status, P247_STATUS_VERIFIED_41OF41_AGGREGATOR)
        self.assertEqual(rep.pillar_count, 41)
        self.assertEqual(rep.pillars_passed, 41)
        self.assertEqual(rep.failed_pillars, ())
        self.assertTrue(rep.under_6s_budget)

    def test_41_master_41pillar_zero_write_and_domain_invariants_preserved(self) -> None:
        rep = _get_cached_master41_default()
        self.assertEqual(rep.tier0_battery_high_display_violations, 0)
        self.assertEqual(rep.bt_rmt_ir_lockout_violations, 0)
        self.assertEqual(rep.slot1_mymenu_vault_mutation_bytes, 0)
        self.assertEqual(rep.destructive_menu_delete_confusions, 0)
        self.assertEqual(rep.shutter_angle_exposure_step_drift_events, 0)
        self.assertFalse(rep.fx3_has_var_shutter)
        self.assertEqual(rep.unbuffered_battery_pull_events, 0)
        self.assertFalse(rep.hardware_live_attachment_authorized)
        self.assertTrue(rep.cnflasha_userspace_write_blocked)
        self.assertEqual(rep.otp_fuse_touches, 0)
        self.assertEqual(rep.otp_fuse_writes, 0)
        self.assertEqual(rep.rpmb_counter_increments, 0)
        self.assertEqual(rep.passive_tx_bytes_emitted, 0)
        self.assertEqual(rep.physical_usb_packets_emitted, 0)
        self.assertEqual(rep.physical_device_writes, 0)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)
        self.assertFalse(rep.el3_payload_transmit_authorized)
        self.assertFalse(rep.isp_write_authorized)
        self.assertFalse(rep.spi_nor_write_authorized)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.persistent_write_release)
        self.assertFalse(rep.allow_boot_partition_targeting)
        self.assertFalse(rep.allow_destructive_fastboot)
        self.assertFalse(rep.live_usb_iokit_transmit_enabled)
        self.assertEqual(rep.errors, ())

    def test_42_master_41pillar_individual_pillar_numbering_and_status(self) -> None:
        rep = _get_cached_master41_clean_room()
        self.assertEqual([p.pillar_number for p in rep.pillars], list(range(1, 42)))
        self.assertTrue(all(p.passed for p in rep.pillars))
        p41 = rep.pillars[40]
        self.assertEqual(p41.pillar_number, 41)
        self.assertEqual(p41.pillar_id, "pillar_41_display_quality_bt_rmt_mymenu_vault")
        self.assertEqual(p41.phase_label, "Phase 247")
        self.assertEqual(p41.key_metrics["pillar_41a_display_quality_bt_rmt_vault"], "6/6")
        self.assertEqual(p41.key_metrics["pillar_41b_my_menu_camset_vault"], "6/6")
        self.assertEqual(p41.key_metrics["tier0_battery_high_display_violations"], 0)
        self.assertEqual(p41.key_metrics["bt_rmt_ir_lockout_violations"], 0)
        self.assertEqual(p41.key_metrics["slot1_mymenu_vault_mutation_bytes"], 0)
        self.assertEqual(p41.key_metrics["donor_files_inspected"], 11)

    def test_43_master_41pillar_json_serializable_without_nan(self) -> None:
        rep = _get_cached_master41_clean_room()
        encoded = json.dumps(rep.to_dict(), sort_keys=True, allow_nan=False)
        parsed = json.loads(encoded)
        self.assertEqual(parsed["schema"], PHASE247_SCHEMA)
        self.assertEqual(parsed["pillar_count"], 41)
        self.assertEqual(parsed["pillars_passed"], 41)
        self.assertEqual(len(parsed["master_41pillar_sha256"]), 64)

    def test_44_master_41pillar_fault_injection_on_pillar_41_marks_40_of_41(self) -> None:
        m40 = _get_cached_master40_clean_room()
        with mock.patch.object(p247, "evaluate_realhw_40pillar_recovery_master", return_value=m40):
            rep = evaluate_realhw_41pillar_recovery_master(
                force_clean_room=True,
                fault_inject_pillar="pillar_41_display_quality_bt_rmt_mymenu_vault",
            )
        self.assertFalse(rep.all_passed)
        self.assertEqual(rep.status, P247_STATUS_FAIL_41OF41_AGGREGATOR)
        self.assertEqual(rep.pillar_count, 41)
        self.assertEqual(rep.pillars_passed, 40)
        self.assertEqual(rep.failed_pillars, ("pillar_41_display_quality_bt_rmt_mymenu_vault",))

    def test_45_master_41pillar_fault_injection_on_upstream_pillar_1_marks_40_of_41(self) -> None:
        m40 = _get_cached_master40_clean_room()
        first_id = MASTER_41_PILLAR_IDS[0]
        with mock.patch.object(p247, "evaluate_realhw_40pillar_recovery_master", return_value=m40):
            rep = evaluate_realhw_41pillar_recovery_master(
                force_clean_room=True,
                fault_inject_pillar=first_id,
            )
        self.assertFalse(rep.all_passed)
        self.assertEqual(rep.pillars_passed, 40)
        self.assertEqual(rep.failed_pillars, (first_id,))

    def test_46_master_41pillar_rejects_unknown_fault_inject_pillar(self) -> None:
        with self.assertRaises(ValueError):
            evaluate_realhw_41pillar_recovery_master(
                force_clean_room=True,
                fault_inject_pillar="nonexistent_pillar_999",
            )

    def test_47_master_41pillar_aliases_forward_cleanly(self) -> None:
        cached = _get_cached_master41_clean_room()
        with mock.patch.object(
            p247, "evaluate_realhw_41pillar_recovery_master", return_value=cached
        ) as mocked_eval:
            r1 = evaluate_41pillar_recovery_master(force_clean_room=True)
            r2 = verify_41pillar_recovery_suite(force_clean_room=True)
        self.assertIs(r1, cached)
        self.assertIs(r2, cached)
        self.assertEqual(mocked_eval.call_count, 2)

    def test_48_safety_invariant_tamper_detection_blocks_master(self) -> None:
        with mock.patch.object(p247, "PERSISTENT_EMMC_WRITES_AUTHORIZED", True):
            with self.assertRaises(ValueError):
                evaluate_realhw_41pillar_recovery_master(force_clean_room=True)

    def test_49_safety_invariant_tamper_detection_blocks_standalone_suite(self) -> None:
        with mock.patch.object(p247, "PASSIVE_TX_BYTES_EMITTED", 1):
            rep = run_pillar41_standalone_suite(force_clean_room=True)
        self.assertFalse(rep.all_passed)
        self.assertEqual(rep.status, P247_STATUS_FAIL_PILLAR41_SUITE)
        self.assertTrue(any("PASSIVE_TX_BYTES_EMITTED" in e for e in rep.errors))

    def test_50_master_41pillar_detects_upstream_m40_safety_violation(self) -> None:
        m40_bad = replace(_get_cached_master40_clean_room(), destructive_menu_delete_confusions=1)
        with mock.patch.object(p247, "evaluate_realhw_40pillar_recovery_master", return_value=m40_bad):
            rep = evaluate_realhw_41pillar_recovery_master(force_clean_room=True)
        self.assertFalse(rep.all_passed)
        self.assertTrue(any("destructive_menu_delete_confusions" in e for e in rep.errors))

    def test_51_master_41pillar_detects_p41_domain_counter_violation(self) -> None:
        p41_bad = replace(
            run_pillar41_standalone_suite(force_clean_room=True),
            slot1_mymenu_vault_mutation_bytes=64,
        )
        m40 = _get_cached_master40_clean_room()
        with (
            mock.patch.object(p247, "evaluate_realhw_40pillar_recovery_master", return_value=m40),
            mock.patch.object(p247, "run_pillar41_standalone_suite", return_value=p41_bad),
        ):
            rep = evaluate_realhw_41pillar_recovery_master(force_clean_room=True)
        self.assertFalse(rep.all_passed)
        self.assertTrue(any("slot1_mymenu_vault_mutation_bytes" in e for e in rep.errors))

    def test_52_all_supported_fx3_firmware_versions_accepted_in_pillar41a_and_41b(self) -> None:
        self.assertIn("7.02", P247_FX3_SUPPORTED_FW_VERSIONS)
        for ver in P247_FX3_SUPPORTED_FW_VERSIONS:
            with self.subTest(fw_version=ver):
                self.assertTrue(
                    evaluate_display_quality_and_bt_rmt_ctrl_vault(
                        DisplayQualityAndBtRmtCtrlVaultSpec(fw_version=ver)
                    ).passed
                )
                self.assertTrue(
                    evaluate_my_menu_persistence_and_camset_vault(
                        MyMenuPersistenceAndCamsetVaultSpec(fw_version=ver)
                    ).passed
                )

    def test_53_all_10_camset_slots_accepted_for_non_slot1_and_slot1_ordonly_loads(self) -> None:
        self.assertEqual(len(P247_CAMSET_FILENAMES), 10)
        for slot in range(1, 11):
            fname = f"CAMSET{slot:02d}.DAT"
            with self.subTest(slot=slot):
                rep_a = evaluate_display_quality_and_bt_rmt_ctrl_vault(
                    DisplayQualityAndBtRmtCtrlVaultSpec(
                        camset_load_after_reset=True,
                        camset_slot=slot,
                        camset_filename=fname,
                        saved_display_quality="Standard",
                        saved_bt_rmt_ctrl="On",
                    )
                )
                self.assertTrue(rep_a.passed)
                rep_b = evaluate_my_menu_persistence_and_camset_vault(
                    MyMenuPersistenceAndCamsetVaultSpec(
                        camset_load_after_reset=True,
                        camset_slot=slot,
                        camset_filename=fname,
                        camset_read_only_load=True,
                    )
                )
                self.assertTrue(rep_b.passed)

    def test_54_my_menu_max_5_pages_30_items_full_capacity_accepted(self) -> None:
        thirty_items = tuple(f"MenuItem_{i:02d}" for i in range(30))
        counts = (6, 6, 6, 6, 6)
        spec = MyMenuPersistenceAndCamsetVaultSpec(
            pre_op_registered_items=thirty_items,
            pre_op_page_item_counts=counts,
            post_op_registered_items=thirty_items,
            post_op_page_item_counts=counts,
            post_reset_registered_items=thirty_items,
            post_reset_page_item_counts=counts,
        )
        self.assertTrue(evaluate_my_menu_persistence_and_camset_vault(spec).passed)

    def test_55_usb_pd_external_power_allows_high_display_quality_when_not_tier0_battery_bench(self) -> None:
        self.assertEqual(P247_POWER_SOURCES, ("NP-FZ100", "DC-C1", "USB-PD"))
        spec = DisplayQualityAndBtRmtCtrlVaultSpec(
            pre_reset_display_quality="High",
            post_reset_display_quality="High",
            power_source="USB-PD",
            tier0_internal_battery_bench_active=False,
        )
        self.assertTrue(evaluate_display_quality_and_bt_rmt_ctrl_vault(spec).passed)

    def test_56_monitor_brightness_bench_constants_locked_to_manual_zero(self) -> None:
        self.assertEqual(P247_MONITOR_BRIGHTNESS_MENU_PATH, ("MENU", "Setup", "Monitor", "Monitor Brightness"))
        self.assertEqual(P247_MONITOR_BRIGHTNESS_BENCH_MODE, "Manual")
        self.assertEqual(P247_MONITOR_BRIGHTNESS_BENCH_LEVEL, 0)

    def test_57_ir_remote_ctrl_menu_path_and_bt_function_airplane_paths_verified(self) -> None:
        self.assertEqual(P247_IR_REMOTE_CTRL_MENU_PATH, ("MENU", "Setup", "Setup Option", "IR Remote Ctrl"))
        self.assertEqual(P247_BLUETOOTH_FUNCTION_MENU_PATH, ("MENU", "Network", "Bluetooth", "Bluetooth Function"))
        self.assertEqual(P247_AIRPLANE_MODE_MENU_PATH, ("MENU", "Network", "Network Option", "Airplane Mode"))

    def test_58_bt_rmt_ctrl_suppressed_when_bt_function_on_but_airplane_mode_on(self) -> None:
        spec = DisplayQualityAndBtRmtCtrlVaultSpec(
            pre_reset_bt_rmt_ctrl="On",
            reset_action="NONE",
            post_reset_bt_rmt_ctrl="On",
            bluetooth_function="On",
            airplane_mode="On",
            zero_rf_bench_enforced=True,
            effective_bt_rmt_ctrl_active=False,
            ir_remote_ctrl_setting="Off",
            ir_remote_commander_usable=False,
        )
        self.assertTrue(evaluate_display_quality_and_bt_rmt_ctrl_vault(spec).passed)

    def test_59_ir_remote_commander_false_positive_rejected_when_ir_setting_off(self) -> None:
        spec = DisplayQualityAndBtRmtCtrlVaultSpec(
            pre_reset_bt_rmt_ctrl="Off",
            reset_action="NONE",
            post_reset_bt_rmt_ctrl="Off",
            ir_remote_ctrl_setting="Off",
            ir_remote_commander_usable=True,
        )
        rep = evaluate_display_quality_and_bt_rmt_ctrl_vault(spec)
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P247_BLOCKED_IR_REMOTE_USED_WHILE_BT_RMT_CTRL_ON)

    def test_60_my_menu_none_operation_rejects_spurious_item_mutation(self) -> None:
        spec = MyMenuPersistenceAndCamsetVaultSpec(
            pre_op_registered_items=P247_DEFAULT_REGISTERED_MY_MENU_ITEMS,
            pre_op_page_item_counts=(4,),
            my_menu_operation="NONE",
            post_op_registered_items=P247_DEFAULT_REGISTERED_MY_MENU_ITEMS[:3],
            post_op_page_item_counts=(3,),
            post_reset_registered_items=P247_DEFAULT_REGISTERED_MY_MENU_ITEMS[:3],
            post_reset_page_item_counts=(3,),
        )
        rep = evaluate_my_menu_persistence_and_camset_vault(spec)
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P247_BLOCKED_MY_MENU_OPERATION_OR_TAB_BEHAVIOR_MISMATCH)

    def test_61_pinned_backup_bin_digest_consistent_across_phase247(self) -> None:
        self.assertEqual(
            P247_PINNED_FX3_BACKUP_BIN_SHA256,
            "bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2",
        )

    def test_62_backward_compatibility_callable_exports_22_to_40(self) -> None:
        for count, attr_name in (
            (22, "evaluate_22pillar_recovery_master"),
            (24, "evaluate_24pillar_recovery_master"),
            (26, "evaluate_26pillar_recovery_master"),
            (27, "evaluate_27pillar_recovery_master"),
            (28, "evaluate_28pillar_recovery_master"),
            (29, "evaluate_29pillar_recovery_master"),
            (30, "evaluate_realhw_30pillar_recovery_master"),
            (31, "evaluate_realhw_31pillar_recovery_master"),
            (32, "evaluate_realhw_32pillar_recovery_master"),
            (33, "evaluate_realhw_33pillar_recovery_master"),
            (34, "evaluate_realhw_34pillar_recovery_master"),
            (35, "evaluate_realhw_35pillar_recovery_master"),
            (36, "evaluate_realhw_36pillar_recovery_master"),
            (37, "evaluate_realhw_37pillar_recovery_master"),
            (38, "evaluate_realhw_38pillar_recovery_master"),
            (39, "evaluate_realhw_39pillar_recovery_master"),
            (40, "evaluate_realhw_40pillar_recovery_master"),
        ):
            with self.subTest(pillars=count):
                self.assertTrue(callable(getattr(fx3_recovery, attr_name)))
        rep_m = _get_cached_master41_clean_room()
        self.assertEqual([p.pillar_number for p in rep_m.pillars], list(range(1, 42)))

    def test_63_cli_verify_display_quality_bt_rmt_mymenu_vault_summary_and_json(self) -> None:
        rc_txt, out_txt = _run_inprocess_cli("verify-display-quality-bt-rmt-mymenu-vault")
        self.assertEqual(rc_txt, 0)
        self.assertIn("status=VERIFIED_PILLAR41_DISPLAY_QUALITY_BT_RMT_MYMENU_VAULT", out_txt)
        self.assertIn("pillar_41a=6/6", out_txt)
        self.assertIn("pillar_41b=6/6", out_txt)
        self.assertIn("tier0_battery_high_display_violations=0", out_txt)
        self.assertIn("bt_rmt_ir_lockout_violations=0", out_txt)
        self.assertIn("slot1_mymenu_vault_mutation_bytes=0", out_txt)
        self.assertIn("hardware_live_attachment_authorized=False", out_txt)

        rc_js, out_js = _run_inprocess_cli("verify-display-quality-bt-rmt-mymenu-vault", "--json")
        self.assertEqual(rc_js, 0)
        payload = json.loads(out_js)
        self.assertTrue(payload["all_passed"])
        self.assertEqual(payload["schema"], PHASE247_SCHEMA)

    def test_64_cli_verify_display_quality_bt_rmt_mymenu_vault_force_clean_room(self) -> None:
        rc, out = _run_inprocess_cli(
            "verify-display-quality-bt-rmt-mymenu-vault", "--force-clean-room", "--json"
        )
        self.assertEqual(rc, 0)
        payload = json.loads(out)
        self.assertTrue(payload["all_passed"])
        self.assertEqual(payload["verification_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(payload["tier0_battery_high_display_violations"], 0)
        self.assertEqual(payload["bt_rmt_ir_lockout_violations"], 0)
        self.assertEqual(payload["slot1_mymenu_vault_mutation_bytes"], 0)
        self.assertFalse(payload["hardware_live_attachment_authorized"])

    def test_65_cli_verify_display_quality_bt_rmt_mymenu_vault_subprocess_smoke(self) -> None:
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ADAPTER_ROOT)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "fx3_recovery",
                "verify-display-quality-bt-rmt-mymenu-vault",
                "--json",
            ],
            cwd=str(ADAPTER_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertTrue(payload["all_passed"])
        self.assertEqual(payload["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(payload["physical_device_writes"], 0)
        self.assertEqual(payload["physical_usb_packets_emitted"], 0)
        self.assertEqual(payload["passive_tx_bytes_emitted"], 0)

    def test_66_cli_verify_41pillar_recovery_summary_json_and_clean_room_forwarding(self) -> None:
        cached = _get_cached_master41_default()
        with mock.patch.object(cli_main, "verify_41pillar_recovery_suite", return_value=cached):
            rc_txt, out_txt = _run_inprocess_cli("verify-41pillar-recovery")
            self.assertEqual(rc_txt, 0)
            self.assertIn("status=VERIFIED_41OF41_PILLAR_RECOVERY_MASTER", out_txt)
            self.assertIn("pillars=41/41", out_txt)
            self.assertIn("pillar41_a=6/6", out_txt)
            self.assertIn("pillar41_b=6/6", out_txt)

            rc_js, out_js = _run_inprocess_cli("verify-41pillar-recovery", "--json")
            self.assertEqual(rc_js, 0)
            payload = json.loads(out_js)
            self.assertEqual(payload["pillar_count"], 41)
            self.assertEqual(payload["pillars_passed"], 41)

        cached_cr = _get_cached_master41_clean_room()
        with mock.patch.object(
            cli_main, "verify_41pillar_recovery_suite", return_value=cached_cr
        ) as mocked_suite:
            rc_cr, out_cr = _run_inprocess_cli("verify-41pillar-recovery", "--clean-room", "--json")
        self.assertEqual(rc_cr, 0)
        mocked_suite.assert_called_once_with(force_clean_room=True)
        self.assertEqual(json.loads(out_cr)["verification_mode"], "CLEAN_ROOM_SYNTHETIC")

    def test_67_cli_out_creates_exclusive_directories_for_pillar41_and_41pillar_master(self) -> None:
        here = Path(__file__).resolve().parent
        out_p41 = here / f"_tmp_p247_p41_{os.getpid()}"
        rep_p41 = out_p41 / "pillar41-display-quality-bt-rmt-mymenu-vault-report.json"
        out_m41 = here / f"_tmp_p247_m41_{os.getpid()}"
        rep_m41 = out_m41 / "41pillar-recovery-master-report.json"
        for f, d in ((rep_p41, out_p41), (rep_m41, out_m41)):
            if f.is_file():
                f.unlink()
            if d.is_dir():
                d.rmdir()
        try:
            rc1, _ = _run_inprocess_cli(
                "verify-display-quality-bt-rmt-mymenu-vault",
                "--force-clean-room",
                "--out",
                str(out_p41),
            )
            self.assertEqual(rc1, 0)
            self.assertTrue(rep_p41.is_file())
            self.assertEqual(
                json.loads(rep_p41.read_text(encoding="utf-8"))["schema"],
                PHASE247_SCHEMA,
            )

            cached_cr = _get_cached_master41_clean_room()
            with mock.patch.object(cli_main, "verify_41pillar_recovery_suite", return_value=cached_cr):
                rc2, _ = _run_inprocess_cli(
                    "verify-41pillar-recovery",
                    "--force-clean-room",
                    "--out",
                    str(out_m41),
                )
            self.assertEqual(rc2, 0)
            self.assertTrue(rep_m41.is_file())
            self.assertEqual(
                json.loads(rep_m41.read_text(encoding="utf-8"))["pillar_count"],
                41,
            )
        finally:
            for f, d in ((rep_p41, out_p41), (rep_m41, out_m41)):
                if f.is_file():
                    f.unlink()
                if d.is_dir():
                    d.rmdir()

    def test_68_cli_out_refuses_preexisting_directory_overwrite_guard(self) -> None:
        here = Path(__file__).resolve().parent
        existing_dir = here / f"_tmp_p247_exist_{os.getpid()}"
        existing_dir.mkdir(exist_ok=True)
        try:
            rc, out = _run_inprocess_cli(
                "verify-display-quality-bt-rmt-mymenu-vault",
                "--force-clean-room",
                "--out",
                str(existing_dir),
            )
            self.assertEqual(rc, 2)
            err_payload = json.loads(out)
            self.assertEqual(err_payload["status"], "REJECTED")
        finally:
            if existing_dir.is_dir():
                existing_dir.rmdir()


if __name__ == "__main__":
    unittest.main()
