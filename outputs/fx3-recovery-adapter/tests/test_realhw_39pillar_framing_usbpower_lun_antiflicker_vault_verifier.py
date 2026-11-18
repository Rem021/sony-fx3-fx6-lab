"""Phase 243 — Dual-mode unit tests for Pillar 39 (`[Framing Settings]` asymmetric `Full`/`Crop`
recovery, HDMI `RAW` crop incompatibility, `ILME-FX3` `ilc/2210` vs `ZV-E1` naming lock &
`[Anti-flicker Shoot.]` mechanical-still-only / no-`[Var. Shutter]` invariant; `[USB Power Supply]`
mandatory `NP-FZ100` insertion + `USB Type-C` exclusivity & `[USB LUN Setting]` `Multi`/`Single`
`Setup -> [USB]` reset persistence + offline `WP` card-reader Tier-0 vault) and unified `39/39`
recovery master (`verify-39pillar-recovery` / `verify-framing-usbpower-lun-antiflicker-vault`)."""

from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import fx3_recovery
from fx3_recovery import __main__ as cli_main
from fx3_recovery import realhw_39pillar_framing_usbpower_lun_antiflicker_vault_verifier as p243
from fx3_recovery.realhw_38pillar_shoe_audio_wind_saveload_vault_verifier import (
    MASTER_38_PILLAR_SPECS,
    Master38PillarRecoveryReport,
    evaluate_realhw_38pillar_recovery_master,
)
from fx3_recovery.realhw_39pillar_framing_usbpower_lun_antiflicker_vault_verifier import (
    ALLOW_BOOT_PARTITION_TARGETING,
    ALLOW_DESTRUCTIVE_FASTBOOT,
    ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS,
    ALLOW_PERSISTENT_JIRITSU_WRITES,
    CNFLASHA_USERSPACE_WRITE_BLOCKED,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    ISP_WRITE_AUTHORIZED,
    LIVE_USB_IOKIT_TRANSMIT_ENABLED,
    MASTER_39_PILLAR_COUNT,
    MASTER_39_PILLAR_IDS,
    MASTER_39_PILLAR_SPECS,
    OTP_FUSE_TOUCHES,
    OTP_FUSE_WRITES,
    P243_ANTIFLICKER_SHOOT_DEFAULT,
    P243_ANTIFLICKER_SHOOT_MENU_PATH,
    P243_BATTERY_BAY_SOURCES,
    P243_BLOCKED_ANTIFLICKER_MOVIE_OR_ELECTRONIC_SHUTTER_VIOLATION,
    P243_BLOCKED_CAMSET_FRAMING_OR_ANTIFLICKER_RESTORE_DRIFT,
    P243_BLOCKED_FRAMING_ASYMMETRIC_ROUTING_MISMATCH,
    P243_BLOCKED_FRAMING_OR_ANTIFLICKER_RESET_DRIFT,
    P243_BLOCKED_FX3_NONEXISTENT_VAR_SHUTTER_OR_ECS_NODE,
    P243_BLOCKED_HDMI_RAW_FRAMING_CROP_INCOMPATIBLE,
    P243_BLOCKED_INVALID_FRAMING_OR_ANTIFLICKER_SPEC,
    P243_BLOCKED_INVALID_USB_POWER_OR_LUN_SPEC,
    P243_BLOCKED_LIVE_USB_HOST_ATTACHMENT_FORBIDDEN,
    P243_BLOCKED_MID_USB_PD_BATTERY_REMOVAL_POWEROFF,
    P243_BLOCKED_MULTI_MICRO_USB_POWER_OR_CHARGE_FORBIDDEN,
    P243_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
    P243_BLOCKED_SAFETY_POLICY_VIOLATION,
    P243_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
    P243_BLOCKED_USB_LUN_MULTI_SINGLE_ENUMERATION_MISMATCH,
    P243_BLOCKED_USB_POWER_SUPPLY_OFF_OR_PORT_MISMATCH,
    P243_BLOCKED_USB_POWER_WITHOUT_NP_FZ100_UNAVAILABLE,
    P243_BLOCKED_USB_SETUP_CAMERA_SETTINGS_RESET_DRIFT,
    P243_BLOCKED_ZVE1_AUTOFRAMING_NAMING_MISMATCH,
    P243_CAMSET_FILENAMES,
    P243_CAPTURE_MODES,
    P243_FORBIDDEN_VAR_SHUTTER_AND_ECS_NODES,
    P243_FORBIDDEN_ZVE1_AUTOFRAMING_MENU_NAME,
    P243_FRAMING_DEFAULT,
    P243_FRAMING_FRAME_MODES,
    P243_FRAMING_HDMI_DEFAULT,
    P243_FRAMING_REC_STREAMING_DEFAULT,
    P243_FRAMING_SETTINGS_3_ITEMS,
    P243_FRAMING_SETTINGS_MENU_PATH,
    P243_FX3_FW_VERSION,
    P243_FX3_HAS_VAR_SHUTTER,
    P243_FX3_HELPGUIDE_ID,
    P243_FX3_MODEL_ID,
    P243_FX3_MODEL_NAME,
    P243_FX3_SUPPORTED_FW_VERSIONS,
    P243_FX6_DONOR_FW_VERSION,
    P243_FX6_DONOR_MODEL_NAME,
    P243_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    P243_LUN_MULTI_EXPOSED_SLOTS,
    P243_LUN_SINGLE_EXPOSED_SLOTS,
    P243_PILLAR_39A_SCENARIO_IDS,
    P243_PILLAR_39B_SCENARIO_IDS,
    P243_PINNED_FX3_BACKUP_BIN_SHA256,
    P243_PINNED_FX3_LIBUSBBUSPOWER_SO_BYTES,
    P243_PINNED_FX3_LIBUSBBUSPOWER_SO_SHA256,
    P243_PINNED_FX3_LIBUSBCONTROL_SO_BYTES,
    P243_PINNED_FX3_LIBUSBCONTROL_SO_SHA256,
    P243_PINNED_FX6_APPFW_601_BYTES,
    P243_PINNED_FX6_APPFW_601_HDR4K_SHA256,
    P243_SHUTTER_TYPES,
    P243_SLOT1_VAULT_SLOT,
    P243_STATUS_FAIL_39OF39_AGGREGATOR,
    P243_STATUS_FAIL_PILLAR39_SUITE,
    P243_STATUS_VERIFIED_39OF39_AGGREGATOR,
    P243_STATUS_VERIFIED_PILLAR39_SUITE,
    P243_STATUS_VERIFIED_PILLAR_39A,
    P243_STATUS_VERIFIED_PILLAR_39B,
    P243_SUPPORTED_FLICKER_HZ,
    P243_UNBUFFERED_BATTERY_PULL_EVENTS,
    P243_USB_BENCH_MIN_NP_FZ100_PCT,
    P243_USB_CONNECTION_MODES,
    P243_USB_CONNECTION_MODE_DEFAULT,
    P243_USB_LUN_MODES,
    P243_USB_LUN_SETTING_DEFAULT,
    P243_USB_POWER_PORTS,
    P243_USB_POWER_SUPPLY_DEFAULT,
    P243_USB_SETUP_3_ITEMS,
    P243_USB_SETUP_MENU_PATH,
    PASSIVE_TX_BYTES_EMITTED,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHASE243_SCHEMA,
    PHASE243_VERSION,
    PHYSICAL_DEVICE_WRITES,
    PHYSICAL_USB_PACKETS_EMITTED,
    RAW_FIRMWARE_BYTES_LEAKED,
    READ_ONLY_DONOR_ACCESS,
    RPMB_COUNTER_INCREMENTS,
    SPI_NOR_WRITE_AUTHORIZED,
    FramingCropFullAndAntiFlickerVaultSpec,
    Master39PillarRecoveryReport,
    UsbPowerBatteryInterlockAndLunVaultSpec,
    build_default_safe_framing_antiflicker_vault_spec,
    build_default_safe_usb_power_lun_vault_spec,
    evaluate_39pillar_recovery_master,
    evaluate_framing_settings_and_antiflicker_vault,
    evaluate_realhw_39pillar_recovery_master,
    evaluate_usb_power_battery_and_lun_persistence_vault,
    inspect_phase243_donors_readonly,
    run_pillar39_standalone_suite,
    run_pillar39a_framing_antiflicker_vault_6_scenario_suite,
    run_pillar39b_usb_power_lun_vault_6_scenario_suite,
    verify_39pillar_recovery_suite,
    verify_framing_usbpower_lun_and_antiflicker_vault,
)

ADAPTER_ROOT = Path(__file__).resolve().parents[1]

_CACHED_MASTER39_DEFAULT: Master39PillarRecoveryReport | None = None
_CACHED_MASTER39_CLEAN_ROOM: Master39PillarRecoveryReport | None = None
_CACHED_MASTER38_CLEAN_ROOM: Master38PillarRecoveryReport | None = None


def _get_cached_master39_default() -> Master39PillarRecoveryReport:
    global _CACHED_MASTER39_DEFAULT
    if _CACHED_MASTER39_DEFAULT is None:
        _CACHED_MASTER39_DEFAULT = evaluate_realhw_39pillar_recovery_master()
    return _CACHED_MASTER39_DEFAULT


def _get_cached_master39_clean_room() -> Master39PillarRecoveryReport:
    global _CACHED_MASTER39_CLEAN_ROOM
    if _CACHED_MASTER39_CLEAN_ROOM is None:
        _CACHED_MASTER39_CLEAN_ROOM = evaluate_realhw_39pillar_recovery_master(force_clean_room=True)
    return _CACHED_MASTER39_CLEAN_ROOM


def _get_cached_master38_clean_room() -> Master38PillarRecoveryReport:
    global _CACHED_MASTER38_CLEAN_ROOM
    if _CACHED_MASTER38_CLEAN_ROOM is None:
        _CACHED_MASTER38_CLEAN_ROOM = evaluate_realhw_38pillar_recovery_master(force_clean_room=True)
    return _CACHED_MASTER38_CLEAN_ROOM


def _run_inprocess_cli(*cli_args: str) -> tuple[int, str]:
    buf = io.StringIO()
    with mock.patch.object(sys, "argv", ["fx3_recovery", *cli_args]):
        with redirect_stdout(buf):
            rc = cli_main.main()
    return rc, buf.getvalue()


class TestPhase243SafetyLocksAndExports(unittest.TestCase):
    def test_01_hard_locked_safety_flags_and_counters_zero(self) -> None:
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
        self.assertFalse(P243_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        self.assertTrue(READ_ONLY_DONOR_ACCESS)
        self.assertTrue(CNFLASHA_USERSPACE_WRITE_BLOCKED)
        self.assertFalse(P243_FX3_HAS_VAR_SHUTTER)
        self.assertEqual(P243_UNBUFFERED_BATTERY_PULL_EVENTS, 0)
        self.assertEqual(OTP_FUSE_TOUCHES, 0)
        self.assertEqual(OTP_FUSE_WRITES, 0)
        self.assertEqual(RPMB_COUNTER_INCREMENTS, 0)
        self.assertEqual(PASSIVE_TX_BYTES_EMITTED, 0)
        self.assertEqual(PHYSICAL_USB_PACKETS_EMITTED, 0)
        self.assertEqual(PHYSICAL_DEVICE_WRITES, 0)
        self.assertEqual(RAW_FIRMWARE_BYTES_LEAKED, 0)

    def test_02_schema_version_and_fx3_fx6_identity_pins(self) -> None:
        self.assertEqual(
            PHASE243_SCHEMA,
            "realhw_39pillar_framing_usbpower_lun_antiflicker_vault_verifier_v1",
        )
        self.assertEqual(PHASE243_VERSION, "1.0.0")
        self.assertEqual(P243_FX3_MODEL_NAME, "ILME-FX3")
        self.assertEqual(P243_FX3_MODEL_ID, 0x91030080)
        self.assertEqual(P243_FX3_HELPGUIDE_ID, "ilc/2210")
        self.assertEqual(P243_FX3_FW_VERSION, "7.02")
        self.assertIn("7.02", P243_FX3_SUPPORTED_FW_VERSIONS)
        self.assertEqual(P243_FX6_DONOR_MODEL_NAME, "ILME-FX6")
        self.assertEqual(P243_FX6_DONOR_FW_VERSION, "6.01")

    def test_03_master_39_pillar_specs_extend_38_cleanly(self) -> None:
        self.assertEqual(MASTER_39_PILLAR_COUNT, 39)
        self.assertEqual(len(MASTER_39_PILLAR_SPECS), 39)
        self.assertEqual(len(MASTER_39_PILLAR_IDS), 39)
        self.assertEqual(len(set(MASTER_39_PILLAR_IDS)), 39)
        self.assertEqual(MASTER_39_PILLAR_SPECS[:38], MASTER_38_PILLAR_SPECS)
        self.assertEqual([s[0] for s in MASTER_39_PILLAR_SPECS], list(range(1, 40)))
        self.assertEqual(
            MASTER_39_PILLAR_SPECS[38],
            (
                39,
                "pillar_39_framing_usbpower_lun_antiflicker_vault",
                "Phase 243",
                "fx3_recovery.realhw_39pillar_framing_usbpower_lun_antiflicker_vault_verifier",
            ),
        )

    def test_04_wave37_menu_paths_asymmetric_defaults_and_usb_setup_constants(self) -> None:
        self.assertEqual(P243_FRAMING_SETTINGS_MENU_PATH, ("MENU", "Shooting", "Framing Settings"))
        self.assertEqual(P243_FRAMING_SETTINGS_3_ITEMS, ("Framing", "Recording/Streaming", "HDMI"))
        self.assertEqual(P243_FRAMING_DEFAULT, "Off")
        self.assertEqual(P243_FRAMING_REC_STREAMING_DEFAULT, "Full")
        self.assertEqual(P243_FRAMING_HDMI_DEFAULT, "Crop")
        self.assertEqual(P243_FRAMING_FRAME_MODES, ("Full", "Crop"))
        self.assertEqual(P243_FORBIDDEN_ZVE1_AUTOFRAMING_MENU_NAME, "Autoframing Settings")
        self.assertEqual(
            P243_ANTIFLICKER_SHOOT_MENU_PATH,
            ("MENU", "Shooting", "Shutter/Silent", "Anti-flicker Shoot."),
        )
        self.assertEqual(P243_ANTIFLICKER_SHOOT_DEFAULT, "Off")
        self.assertEqual(P243_SUPPORTED_FLICKER_HZ, (0, 100, 120))
        self.assertIn("Var. Shutter", P243_FORBIDDEN_VAR_SHUTTER_AND_ECS_NODES)
        self.assertIn("ECS", P243_FORBIDDEN_VAR_SHUTTER_AND_ECS_NODES)
        self.assertEqual(P243_USB_SETUP_MENU_PATH, ("MENU", "Setup", "USB"))
        self.assertEqual(
            P243_USB_SETUP_3_ITEMS,
            ("USB Connection Mode", "USB LUN Setting", "USB Power Supply"),
        )
        self.assertEqual(P243_USB_CONNECTION_MODE_DEFAULT, "Sel. When Connect")
        self.assertEqual(P243_USB_LUN_SETTING_DEFAULT, "Multi")
        self.assertEqual(P243_USB_POWER_SUPPLY_DEFAULT, "On")
        self.assertEqual(P243_LUN_MULTI_EXPOSED_SLOTS, (1, 2))
        self.assertEqual(P243_LUN_SINGLE_EXPOSED_SLOTS, (1,))
        self.assertEqual(len(P243_CAMSET_FILENAMES), 10)
        self.assertEqual(len(P243_PILLAR_39A_SCENARIO_IDS), 6)
        self.assertEqual(len(P243_PILLAR_39B_SCENARIO_IDS), 6)

    def test_05_package_init_exports_all_phase243_symbols_without_shadowing(self) -> None:
        self.assertIs(
            fx3_recovery.realhw_39pillar_framing_usbpower_lun_antiflicker_vault_verifier,
            p243,
        )
        self.assertEqual(
            fx3_recovery.__all__.count("realhw_39pillar_framing_usbpower_lun_antiflicker_vault_verifier"),
            1,
        )
        for sym in p243.__all__:
            with self.subTest(symbol=sym):
                self.assertIn(sym, fx3_recovery.__all__)
                self.assertEqual(fx3_recovery.__all__.count(sym), 1)
                self.assertTrue(hasattr(fx3_recovery, sym))

    def test_06_safety_invariant_tamper_triggers_fail_closed_errors(self) -> None:
        with mock.patch.object(p243, "PERSISTENT_EMMC_WRITES_AUTHORIZED", True):
            errs = p243._safety_invariant_errors()
            self.assertTrue(any("PERSISTENT_EMMC_WRITES_AUTHORIZED" in e for e in errs))
        with mock.patch.object(p243, "P243_FX3_HAS_VAR_SHUTTER", True):
            errs2 = p243._safety_invariant_errors()
            self.assertTrue(any("P243_FX3_HAS_VAR_SHUTTER" in e for e in errs2))
        with mock.patch.object(p243, "HARDWARE_LIVE_ATTACHMENT_AUTHORIZED", True):
            errs3 = p243._safety_invariant_errors()
            self.assertTrue(any("HARDWARE_LIVE_ATTACHMENT_AUTHORIZED" in e for e in errs3))


class TestPhase243DonorReadOnlyAndCleanRoomFallback(unittest.TestCase):
    def test_07_donor_inspection_force_clean_room_synthetic_parity(self) -> None:
        snap = inspect_phase243_donors_readonly(force_clean_room=True)
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(snap.all_donors_present)
        self.assertEqual(snap.donor_files_inspected, 9)
        self.assertTrue(snap.under_0_15s_budget)
        self.assertEqual(snap.raw_firmware_bytes_leaked, 0)
        for art in snap.artifacts:
            self.assertTrue(art.present)
            self.assertTrue(art.matches_pinned)
            self.assertEqual(art.read_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertEqual(len(art.digest_sha256), 64)

    def test_08_donor_inspection_env_force_clean_room_override(self) -> None:
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            snap = inspect_phase243_donors_readonly()
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(snap.all_donors_present)
        self.assertEqual(snap.donor_files_inspected, 9)

    def test_09_donor_inspection_default_mode_local_or_clean_room(self) -> None:
        snap = inspect_phase243_donors_readonly()
        self.assertTrue(snap.all_donors_present)
        self.assertEqual(snap.donor_files_inspected, 9)
        self.assertTrue(snap.under_0_15s_budget)
        self.assertLess(snap.elapsed_seconds, 2.0)
        self.assertEqual(snap.raw_firmware_bytes_leaked, 0)
        if os.environ.get("FX3_FX6_FORCE_CLEAN_ROOM") == "1":
            self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        else:
            self.assertIn(snap.verification_mode, ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"))
            if snap.verification_mode == "LOCAL_DONOR_O_RDONLY":
                for art in snap.artifacts:
                    self.assertEqual(art.read_mode, "O_RDONLY_NOFOLLOW_NONBLOCK")
                    self.assertTrue(art.matches_pinned, msg=art.artifact_id)

    def test_10_donor_snapshot_pins_usb_bus_power_and_usb_control_elf64_anchors(self) -> None:
        snap = inspect_phase243_donors_readonly()
        by_id = {a.artifact_id: a for a in snap.artifacts}
        self.assertIn("fx3_libusbbuspower_so", by_id)
        self.assertIn("fx3_libusbcontrol_so", by_id)
        self.assertIn("fx6_appfw_601_so", by_id)
        ubp = by_id["fx3_libusbbuspower_so"]
        self.assertEqual(ubp.total_bytes, P243_PINNED_FX3_LIBUSBBUSPOWER_SO_BYTES)
        self.assertEqual(ubp.digest_sha256, P243_PINNED_FX3_LIBUSBBUSPOWER_SO_SHA256)
        if snap.verification_mode == "LOCAL_DONOR_O_RDONLY":
            self.assertIn("UsbBusPower_Init", ubp.marker_summary)
            self.assertIn("SetWatchSWForceOFF", ubp.marker_summary)
        uctrl = by_id["fx3_libusbcontrol_so"]
        self.assertEqual(uctrl.total_bytes, P243_PINNED_FX3_LIBUSBCONTROL_SO_BYTES)
        self.assertEqual(uctrl.digest_sha256, P243_PINNED_FX3_LIBUSBCONTROL_SO_SHA256)
        if snap.verification_mode == "LOCAL_DONOR_O_RDONLY":
            self.assertIn("UsbControlDebug", uctrl.marker_summary)
        fx6 = by_id["fx6_appfw_601_so"]
        self.assertEqual(fx6.total_bytes, P243_PINNED_FX6_APPFW_601_BYTES)
        self.assertEqual(fx6.digest_sha256, P243_PINNED_FX6_APPFW_601_HDR4K_SHA256)

    def test_11_donor_missing_path_falls_back_cleanly_to_synthetic(self) -> None:
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "0"}):
            with mock.patch.object(p243, "resolve_donor_path", return_value=None):
                snap = inspect_phase243_donors_readonly(force_clean_room=False)
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(snap.all_donors_present)
        self.assertEqual(snap.donor_files_inspected, 9)

    def test_12_readonly_bounded_reader_rejects_missing_or_symlink_target(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            real_f = td_path / "donor.bin"
            real_f.write_bytes(b"ABCD" * 32)
            link_f = td_path / "donor_link.bin"
            link_f.symlink_to(real_f)
            with mock.patch.object(p243, "resolve_donor_path", return_value=link_f):
                ok, total_b, _, _, sha_hex, raw = p243._read_donor_readonly_bounded("fake/rel")
            self.assertFalse(ok)
            self.assertEqual(total_b, 0)
            self.assertEqual(sha_hex, "")
            self.assertEqual(raw, b"")


class TestPillar39AFramingSettingsAndAntiFlickerVault(unittest.TestCase):
    def test_13_pillar39a_6_scenario_suite_passes_all_6(self) -> None:
        res = run_pillar39a_framing_antiflicker_vault_6_scenario_suite()
        self.assertTrue(res.passed)
        self.assertEqual(res.status, P243_STATUS_VERIFIED_PILLAR_39A)
        self.assertEqual(res.scenarios_passed, 6)
        self.assertEqual(res.scenarios_total, 6)
        self.assertEqual(tuple(s.scenario_id for s in res.scenarios), P243_PILLAR_39A_SCENARIO_IDS)
        for s in res.scenarios:
            self.assertTrue(s.passed, msg=s.scenario_id)

    def test_14_default_safe_framing_and_antiflicker_spec_passes_camera_settings_reset(self) -> None:
        spec = build_default_safe_framing_antiflicker_vault_spec()
        rep = evaluate_framing_settings_and_antiflicker_vault(spec)
        self.assertTrue(rep.passed)
        self.assertEqual(rep.status, P243_STATUS_VERIFIED_PILLAR_39A)
        self.assertIsNone(rep.block_code)
        self.assertTrue(rep.fx3_framing_naming_lock_verified)
        self.assertTrue(rep.framing_and_antiflicker_reset_verified)
        self.assertTrue(rep.camset_slot1_restore_verified)
        self.assertTrue(rep.framing_asymmetric_and_hdmi_raw_guard_verified)
        self.assertTrue(rep.antiflicker_mech_still_only_verified)
        self.assertTrue(rep.no_var_shutter_invariant_verified)
        self.assertTrue(rep.h0_equals_h3_verified)
        self.assertFalse(rep.fx3_has_var_shutter)
        self.assertEqual(rep.physical_device_writes, 0)

    def test_15_full_initialize_resets_framing_3items_and_antiflicker_cleanly(self) -> None:
        spec = FramingCropFullAndAntiFlickerVaultSpec(
            reset_action="Initialize",
            pre_reset_framing="On",
            pre_reset_framing_rec_streaming="Crop",
            pre_reset_framing_hdmi="Full",
            pre_reset_antiflicker_shoot="On",
            post_reset_framing="Off",
            post_reset_framing_rec_streaming="Full",
            post_reset_framing_hdmi="Crop",
            post_reset_antiflicker_shoot="Off",
            effective_rec_streaming_frame="Full",
            effective_hdmi_frame="Full",
        )
        rep = evaluate_framing_settings_and_antiflicker_vault(spec)
        self.assertTrue(rep.passed)
        self.assertEqual(rep.errors, ())

    def test_16_camset01_dat_slot1_load_restores_asymmetric_full_crop_and_antiflicker_on(self) -> None:
        for hz in (100, 120):
            with self.subTest(flicker_hz=hz):
                spec = FramingCropFullAndAntiFlickerVaultSpec(
                    reset_action="Camera Settings Reset",
                    camset_load_after_reset=True,
                    camset_slot=1,
                    camset_filename="CAMSET01.DAT",
                    saved_framing="On",
                    saved_framing_rec_streaming="Full",
                    saved_framing_hdmi="Crop",
                    saved_antiflicker_shoot="On",
                    post_reset_framing="On",
                    post_reset_framing_rec_streaming="Full",
                    post_reset_framing_hdmi="Crop",
                    post_reset_antiflicker_shoot="On",
                    hdmi_raw_output="Off",
                    effective_rec_streaming_frame="Full",
                    effective_hdmi_frame="Crop",
                    capture_mode="Still",
                    silent_mode="Off",
                    shutter_type="Mechanical Shutter",
                    flicker_lighting_hz=hz,
                    antiflicker_available_in_current_mode=True,
                    antiflicker_effective_active=True,
                )
                rep = evaluate_framing_settings_and_antiflicker_vault(spec)
                self.assertTrue(rep.passed, msg=rep.errors)

    def test_17_inverted_asymmetric_crop_rec_full_hdmi_routing_passes_when_hdmi_raw_off(self) -> None:
        spec = FramingCropFullAndAntiFlickerVaultSpec(
            reset_action="NONE",
            pre_reset_framing="On",
            pre_reset_framing_rec_streaming="Crop",
            pre_reset_framing_hdmi="Full",
            pre_reset_antiflicker_shoot="Off",
            post_reset_framing="On",
            post_reset_framing_rec_streaming="Crop",
            post_reset_framing_hdmi="Full",
            post_reset_antiflicker_shoot="Off",
            hdmi_raw_output="Off",
            effective_rec_streaming_frame="Crop",
            effective_hdmi_frame="Full",
        )
        rep = evaluate_framing_settings_and_antiflicker_vault(spec)
        self.assertTrue(rep.passed, msg=rep.errors)

    def test_18_framing_off_requires_un_cropped_full_routing_and_allows_hdmi_raw_on(self) -> None:
        ok_spec = FramingCropFullAndAntiFlickerVaultSpec(
            reset_action="NONE",
            pre_reset_framing="Off",
            pre_reset_framing_rec_streaming="Full",
            pre_reset_framing_hdmi="Crop",
            pre_reset_antiflicker_shoot="Off",
            post_reset_framing="Off",
            post_reset_framing_rec_streaming="Full",
            post_reset_framing_hdmi="Crop",
            post_reset_antiflicker_shoot="Off",
            hdmi_raw_output="On",
            effective_rec_streaming_frame="Full",
            effective_hdmi_frame="Full",
        )
        self.assertTrue(evaluate_framing_settings_and_antiflicker_vault(ok_spec).passed)

        bad_spec = FramingCropFullAndAntiFlickerVaultSpec(
            effective_rec_streaming_frame="Full",
            effective_hdmi_frame="Crop",
        )
        bad_rep = evaluate_framing_settings_and_antiflicker_vault(bad_spec)
        self.assertFalse(bad_rep.passed)
        self.assertEqual(bad_rep.block_code, P243_BLOCKED_FRAMING_ASYMMETRIC_ROUTING_MISMATCH)

    def test_19_hdmi_raw_output_on_with_cropped_framing_on_is_rejected(self) -> None:
        for rec_f, hdmi_f in (("Full", "Crop"), ("Crop", "Full"), ("Crop", "Crop")):
            with self.subTest(rec=rec_f, hdmi=hdmi_f):
                spec = FramingCropFullAndAntiFlickerVaultSpec(
                    reset_action="NONE",
                    pre_reset_framing="On",
                    pre_reset_framing_rec_streaming=rec_f,
                    pre_reset_framing_hdmi=hdmi_f,
                    pre_reset_antiflicker_shoot="Off",
                    post_reset_framing="On",
                    post_reset_framing_rec_streaming=rec_f,
                    post_reset_framing_hdmi=hdmi_f,
                    post_reset_antiflicker_shoot="Off",
                    hdmi_raw_output="On",
                    effective_rec_streaming_frame=rec_f,
                    effective_hdmi_frame=hdmi_f,
                )
                rep = evaluate_framing_settings_and_antiflicker_vault(spec)
                self.assertFalse(rep.passed)
                self.assertEqual(rep.block_code, P243_BLOCKED_HDMI_RAW_FRAMING_CROP_INCOMPATIBLE)

    def test_20_zve1_autoframing_settings_naming_and_ilc2310_rejected(self) -> None:
        rep_menu = evaluate_framing_settings_and_antiflicker_vault(
            FramingCropFullAndAntiFlickerVaultSpec(
                framing_menu_path=("MENU", "Shooting", "Autoframing Settings"),
            )
        )
        self.assertFalse(rep_menu.passed)
        self.assertEqual(rep_menu.block_code, P243_BLOCKED_ZVE1_AUTOFRAMING_NAMING_MISMATCH)

        rep_model = evaluate_framing_settings_and_antiflicker_vault(
            FramingCropFullAndAntiFlickerVaultSpec(camera_model="ZV-E1", helpguide_id="ilc/2310")
        )
        self.assertFalse(rep_model.passed)
        self.assertEqual(rep_model.block_code, P243_BLOCKED_ZVE1_AUTOFRAMING_NAMING_MISMATCH)

    def test_21_camera_settings_reset_drift_on_framing_or_antiflicker_rejected(self) -> None:
        rep = evaluate_framing_settings_and_antiflicker_vault(
            FramingCropFullAndAntiFlickerVaultSpec(
                reset_action="Camera Settings Reset",
                camset_load_after_reset=False,
                post_reset_framing="On",
                effective_rec_streaming_frame="Full",
                effective_hdmi_frame="Crop",
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P243_BLOCKED_FRAMING_OR_ANTIFLICKER_RESET_DRIFT)

    def test_22_camset_restore_drift_or_non_slot1_vault_rejected(self) -> None:
        rep_slot2 = evaluate_framing_settings_and_antiflicker_vault(
            FramingCropFullAndAntiFlickerVaultSpec(
                camset_load_after_reset=True,
                camset_slot=2,
                camset_filename="CAMSET01.DAT",
            )
        )
        self.assertFalse(rep_slot2.passed)
        self.assertEqual(rep_slot2.block_code, P243_BLOCKED_CAMSET_FRAMING_OR_ANTIFLICKER_RESTORE_DRIFT)

        rep_drift = evaluate_framing_settings_and_antiflicker_vault(
            FramingCropFullAndAntiFlickerVaultSpec(
                camset_load_after_reset=True,
                camset_slot=1,
                camset_filename="CAMSET01.DAT",
                saved_framing="On",
                saved_framing_rec_streaming="Full",
                saved_framing_hdmi="Crop",
                saved_antiflicker_shoot="On",
                post_reset_framing="Off",
            )
        )
        self.assertFalse(rep_drift.passed)
        self.assertEqual(rep_drift.block_code, P243_BLOCKED_CAMSET_FRAMING_OR_ANTIFLICKER_RESTORE_DRIFT)

    def test_23_antiflicker_shoot_rejected_in_movie_and_sq_motion_modes(self) -> None:
        for mode in ("Movie", "S&Q Motion"):
            with self.subTest(capture_mode=mode):
                rep = evaluate_framing_settings_and_antiflicker_vault(
                    FramingCropFullAndAntiFlickerVaultSpec(
                        reset_action="NONE",
                        pre_reset_framing="Off",
                        pre_reset_framing_rec_streaming="Full",
                        pre_reset_framing_hdmi="Crop",
                        pre_reset_antiflicker_shoot="On",
                        post_reset_framing="Off",
                        post_reset_framing_rec_streaming="Full",
                        post_reset_framing_hdmi="Crop",
                        post_reset_antiflicker_shoot="On",
                        capture_mode=mode,
                        silent_mode="Off",
                        shutter_type="Electronic Shutter",
                        antiflicker_available_in_current_mode=False,
                        antiflicker_effective_active=True,
                    )
                )
                self.assertFalse(rep.passed)
                self.assertEqual(
                    rep.block_code,
                    P243_BLOCKED_ANTIFLICKER_MOVIE_OR_ELECTRONIC_SHUTTER_VIOLATION,
                )

    def test_24_movie_mode_passes_when_antiflicker_marked_unavailable_and_inactive(self) -> None:
        spec = FramingCropFullAndAntiFlickerVaultSpec(
            reset_action="NONE",
            pre_reset_framing="Off",
            pre_reset_framing_rec_streaming="Full",
            pre_reset_framing_hdmi="Crop",
            pre_reset_antiflicker_shoot="On",
            post_reset_framing="Off",
            post_reset_framing_rec_streaming="Full",
            post_reset_framing_hdmi="Crop",
            post_reset_antiflicker_shoot="On",
            capture_mode="Movie",
            silent_mode="Off",
            shutter_type="Electronic Shutter",
            antiflicker_available_in_current_mode=False,
            antiflicker_effective_active=False,
        )
        rep = evaluate_framing_settings_and_antiflicker_vault(spec)
        self.assertTrue(rep.passed, msg=rep.errors)

    def test_25_antiflicker_shoot_rejected_under_silent_mode_or_electronic_shutter_still(self) -> None:
        rep_silent = evaluate_framing_settings_and_antiflicker_vault(
            FramingCropFullAndAntiFlickerVaultSpec(
                capture_mode="Still",
                silent_mode="On",
                shutter_type="Electronic Shutter",
                antiflicker_available_in_current_mode=True,
                antiflicker_effective_active=False,
            )
        )
        self.assertFalse(rep_silent.passed)
        self.assertEqual(
            rep_silent.block_code,
            P243_BLOCKED_ANTIFLICKER_MOVIE_OR_ELECTRONIC_SHUTTER_VIOLATION,
        )

        rep_eshutter = evaluate_framing_settings_and_antiflicker_vault(
            FramingCropFullAndAntiFlickerVaultSpec(
                capture_mode="Still",
                silent_mode="Off",
                shutter_type="Electronic Shutter",
                antiflicker_available_in_current_mode=False,
                antiflicker_effective_active=True,
            )
        )
        self.assertFalse(rep_eshutter.passed)
        self.assertEqual(
            rep_eshutter.block_code,
            P243_BLOCKED_ANTIFLICKER_MOVIE_OR_ELECTRONIC_SHUTTER_VIOLATION,
        )

    def test_26_fx3_var_shutter_or_fx6_ecs_claims_hard_rejected(self) -> None:
        for claimed in ("Var. Shutter", "Var. Shutter Set.", "ECS", "Extended Clear Scan"):
            with self.subTest(claimed_node=claimed):
                rep = evaluate_framing_settings_and_antiflicker_vault(
                    FramingCropFullAndAntiFlickerVaultSpec(
                        fx3_has_var_shutter=False,
                        claimed_var_shutter_or_ecs_menu_node=claimed,
                    )
                )
                self.assertFalse(rep.passed)
                self.assertEqual(
                    rep.block_code,
                    P243_BLOCKED_FX3_NONEXISTENT_VAR_SHUTTER_OR_ECS_NODE,
                )

    def test_27_foreign_fx30_model_or_helpguide_id_rejected_in_pillar39a(self) -> None:
        rep = evaluate_framing_settings_and_antiflicker_vault(
            FramingCropFullAndAntiFlickerVaultSpec(
                camera_model="ILME-FX30",
                helpguide_id="ilc/2220",
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P243_BLOCKED_INVALID_FRAMING_OR_ANTIFLICKER_SPEC)

    def test_28_pillar39a_overlay_escape_rejected(self) -> None:
        rep = evaluate_framing_settings_and_antiflicker_vault(
            FramingCropFullAndAntiFlickerVaultSpec(overlay_dir="/setting/framing_escape")
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P243_BLOCKED_PERSISTENT_OVERLAY_ESCAPE)

    def test_29_pillar39a_tier0_backup_bin_h0_h3_drift_rejected(self) -> None:
        rep = evaluate_framing_settings_and_antiflicker_vault(
            FramingCropFullAndAntiFlickerVaultSpec(backup_bin_h3_sha256="0" * 64)
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P243_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT)

    def test_30_pillar39a_persistent_write_unlock_request_rejected(self) -> None:
        rep = evaluate_framing_settings_and_antiflicker_vault(
            FramingCropFullAndAntiFlickerVaultSpec(persistent_write_unlock_requested=True)
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P243_BLOCKED_SAFETY_POLICY_VIOLATION)


class TestPillar39BUsbPowerBatteryAndLunPersistenceVault(unittest.TestCase):
    def test_31_pillar39b_6_scenario_suite_passes_all_6(self) -> None:
        res = run_pillar39b_usb_power_lun_vault_6_scenario_suite()
        self.assertTrue(res.passed)
        self.assertEqual(res.status, P243_STATUS_VERIFIED_PILLAR_39B)
        self.assertEqual(res.scenarios_passed, 6)
        self.assertEqual(res.scenarios_total, 6)
        self.assertEqual(tuple(s.scenario_id for s in res.scenarios), P243_PILLAR_39B_SCENARIO_IDS)
        for s in res.scenarios:
            self.assertTrue(s.passed, msg=s.scenario_id)

    def test_32_default_safe_usb_power_lun_spec_survives_camera_settings_reset(self) -> None:
        spec = build_default_safe_usb_power_lun_vault_spec()
        rep = evaluate_usb_power_battery_and_lun_persistence_vault(spec)
        self.assertTrue(rep.passed)
        self.assertEqual(rep.status, P243_STATUS_VERIFIED_PILLAR_39B)
        self.assertIsNone(rep.block_code)
        self.assertTrue(rep.usb_setup_reset_persistence_verified)
        self.assertTrue(rep.mandatory_npfz100_battery_interlock_verified)
        self.assertTrue(rep.usb_typec_power_exclusivity_verified)
        self.assertTrue(rep.usb_lun_multi_single_visibility_verified)
        self.assertTrue(rep.offline_wp_card_reader_tier0_verified)
        self.assertTrue(rep.h0_equals_h3_verified)
        self.assertEqual(rep.unbuffered_battery_pull_events, 0)
        self.assertFalse(rep.hardware_live_attachment_authorized)
        self.assertEqual(rep.physical_usb_packets_emitted, 0)
        self.assertEqual(rep.physical_device_writes, 0)

    def test_33_non_default_usb_setup_3items_survive_camera_settings_reset(self) -> None:
        spec = UsbPowerBatteryInterlockAndLunVaultSpec(
            pre_reset_usb_connection_mode="MassStorage(MSC)",
            pre_reset_usb_lun_setting="Single",
            pre_reset_usb_power_supply="Off",
            reset_action="Camera Settings Reset",
            post_reset_usb_connection_mode="MassStorage(MSC)",
            post_reset_usb_lun_setting="Single",
            post_reset_usb_power_supply="Off",
            battery_bay_source="NP-FZ100",
            np_fz100_charge_pct=75,
            usb_power_port="NONE",
            usb_power_delivery_active=False,
            internal_battery_charging_active=False,
            msc_modeled_lun_count=1,
            msc_modeled_exposed_slots=P243_LUN_SINGLE_EXPOSED_SLOTS,
        )
        rep = evaluate_usb_power_battery_and_lun_persistence_vault(spec)
        self.assertTrue(rep.passed, msg=rep.errors)

    def test_34_camera_settings_reset_falsely_wiping_usb_setup_items_is_rejected(self) -> None:
        rep = evaluate_usb_power_battery_and_lun_persistence_vault(
            UsbPowerBatteryInterlockAndLunVaultSpec(
                pre_reset_usb_connection_mode="MTP",
                pre_reset_usb_lun_setting="Single",
                pre_reset_usb_power_supply="Off",
                reset_action="Camera Settings Reset",
                post_reset_usb_connection_mode="Sel. When Connect",
                post_reset_usb_lun_setting="Multi",
                post_reset_usb_power_supply="On",
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P243_BLOCKED_USB_SETUP_CAMERA_SETTINGS_RESET_DRIFT)

    def test_35_initialize_resets_usb_setup_3items_and_rejects_stale_post_init_state(self) -> None:
        ok_rep = evaluate_usb_power_battery_and_lun_persistence_vault(
            UsbPowerBatteryInterlockAndLunVaultSpec(
                pre_reset_usb_connection_mode="MTP",
                pre_reset_usb_lun_setting="Single",
                pre_reset_usb_power_supply="Off",
                reset_action="Initialize",
                post_reset_usb_connection_mode="Sel. When Connect",
                post_reset_usb_lun_setting="Multi",
                post_reset_usb_power_supply="On",
                msc_modeled_lun_count=2,
                msc_modeled_exposed_slots=P243_LUN_MULTI_EXPOSED_SLOTS,
            )
        )
        self.assertTrue(ok_rep.passed, msg=ok_rep.errors)

        bad_rep = evaluate_usb_power_battery_and_lun_persistence_vault(
            UsbPowerBatteryInterlockAndLunVaultSpec(
                pre_reset_usb_connection_mode="MTP",
                pre_reset_usb_lun_setting="Single",
                pre_reset_usb_power_supply="Off",
                reset_action="Initialize",
                post_reset_usb_connection_mode="MTP",
                post_reset_usb_lun_setting="Single",
                post_reset_usb_power_supply="Off",
                usb_power_port="NONE",
                usb_power_delivery_active=False,
                msc_modeled_lun_count=1,
                msc_modeled_exposed_slots=P243_LUN_SINGLE_EXPOSED_SLOTS,
            )
        )
        self.assertFalse(bad_rep.passed)
        self.assertEqual(bad_rep.block_code, P243_BLOCKED_USB_SETUP_CAMERA_SETTINGS_RESET_DRIFT)

    def test_36_dcc1_dc_coupler_in_battery_bay_with_usb_typec_pd_passes(self) -> None:
        rep = evaluate_usb_power_battery_and_lun_persistence_vault(
            UsbPowerBatteryInterlockAndLunVaultSpec(
                battery_bay_source="DC-C1",
                np_fz100_charge_pct=0,
                usb_power_port="USB_TYPE_C",
                usb_power_delivery_active=True,
            )
        )
        self.assertTrue(rep.passed, msg=rep.errors)

    def test_37_empty_battery_bay_power_on_or_usb_pd_rejected(self) -> None:
        rep = evaluate_usb_power_battery_and_lun_persistence_vault(
            UsbPowerBatteryInterlockAndLunVaultSpec(
                battery_bay_source="EMPTY",
                camera_power_on_requested=True,
                usb_power_port="USB_TYPE_C",
                usb_power_delivery_active=True,
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P243_BLOCKED_USB_POWER_WITHOUT_NP_FZ100_UNAVAILABLE)

    def test_38_severely_depleted_np_fz100_below_10pct_rejected(self) -> None:
        rep = evaluate_usb_power_battery_and_lun_persistence_vault(
            UsbPowerBatteryInterlockAndLunVaultSpec(
                battery_bay_source="NP-FZ100",
                np_fz100_charge_pct=P243_USB_BENCH_MIN_NP_FZ100_PCT - 1,
                usb_power_port="USB_TYPE_C",
                usb_power_delivery_active=True,
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P243_BLOCKED_USB_POWER_WITHOUT_NP_FZ100_UNAVAILABLE)

    def test_39_mid_usb_pd_battery_removal_triggers_immediate_unbuffered_poweroff_rejection(self) -> None:
        rep = evaluate_usb_power_battery_and_lun_persistence_vault(
            UsbPowerBatteryInterlockAndLunVaultSpec(
                battery_bay_source="NP-FZ100",
                np_fz100_charge_pct=85,
                usb_power_port="USB_TYPE_C",
                usb_power_delivery_active=True,
                battery_removed_during_usb_power=True,
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P243_BLOCKED_MID_USB_PD_BATTERY_REMOVAL_POWEROFF)
        self.assertGreaterEqual(rep.unbuffered_battery_pull_events, 1)

    def test_40_multi_micro_usb_power_supply_or_battery_charging_rejected(self) -> None:
        rep_pd = evaluate_usb_power_battery_and_lun_persistence_vault(
            UsbPowerBatteryInterlockAndLunVaultSpec(
                usb_power_port="MULTI_MICRO_USB",
                usb_power_delivery_active=True,
                internal_battery_charging_active=False,
            )
        )
        self.assertFalse(rep_pd.passed)
        self.assertEqual(rep_pd.block_code, P243_BLOCKED_MULTI_MICRO_USB_POWER_OR_CHARGE_FORBIDDEN)

        rep_chg = evaluate_usb_power_battery_and_lun_persistence_vault(
            UsbPowerBatteryInterlockAndLunVaultSpec(
                usb_power_port="MULTI_MICRO_USB",
                usb_power_delivery_active=False,
                internal_battery_charging_active=True,
            )
        )
        self.assertFalse(rep_chg.passed)
        self.assertEqual(rep_chg.block_code, P243_BLOCKED_MULTI_MICRO_USB_POWER_OR_CHARGE_FORBIDDEN)

    def test_41_multi_micro_usb_non_power_passive_bench_with_internal_np_fz100_passes(self) -> None:
        rep = evaluate_usb_power_battery_and_lun_persistence_vault(
            UsbPowerBatteryInterlockAndLunVaultSpec(
                usb_power_port="MULTI_MICRO_USB",
                usb_power_delivery_active=False,
                internal_battery_charging_active=False,
                multi_micro_usb_power_or_charge_attempted=False,
                battery_bay_source="NP-FZ100",
                np_fz100_charge_pct=80,
            )
        )
        self.assertTrue(rep.passed, msg=rep.errors)

    def test_42_usb_power_supply_off_claiming_active_usb_pd_is_rejected(self) -> None:
        rep = evaluate_usb_power_battery_and_lun_persistence_vault(
            UsbPowerBatteryInterlockAndLunVaultSpec(
                pre_reset_usb_power_supply="Off",
                post_reset_usb_power_supply="Off",
                usb_power_port="USB_TYPE_C",
                usb_power_delivery_active=True,
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P243_BLOCKED_USB_POWER_SUPPLY_OFF_OR_PORT_MISMATCH)

    def test_43_usb_lun_multi_vs_single_slot_visibility_mismatch_rejected(self) -> None:
        rep_single_claiming_slot2 = evaluate_usb_power_battery_and_lun_persistence_vault(
            UsbPowerBatteryInterlockAndLunVaultSpec(
                pre_reset_usb_lun_setting="Single",
                post_reset_usb_lun_setting="Single",
                msc_modeled_lun_count=2,
                msc_modeled_exposed_slots=(1, 2),
            )
        )
        self.assertFalse(rep_single_claiming_slot2.passed)
        self.assertEqual(
            rep_single_claiming_slot2.block_code,
            P243_BLOCKED_USB_LUN_MULTI_SINGLE_ENUMERATION_MISMATCH,
        )

        rep_multi_claiming_1lun = evaluate_usb_power_battery_and_lun_persistence_vault(
            UsbPowerBatteryInterlockAndLunVaultSpec(
                pre_reset_usb_lun_setting="Multi",
                post_reset_usb_lun_setting="Multi",
                msc_modeled_lun_count=1,
                msc_modeled_exposed_slots=(1,),
            )
        )
        self.assertFalse(rep_multi_claiming_1lun.passed)
        self.assertEqual(
            rep_multi_claiming_1lun.block_code,
            P243_BLOCKED_USB_LUN_MULTI_SINGLE_ENUMERATION_MISMATCH,
        )

    def test_44_live_usb_host_attachment_or_unlocked_wp_card_reader_rejected(self) -> None:
        rep_live = evaluate_usb_power_battery_and_lun_persistence_vault(
            UsbPowerBatteryInterlockAndLunVaultSpec(
                live_host_usb_data_attached=True,
            )
        )
        self.assertFalse(rep_live.passed)
        self.assertEqual(rep_live.block_code, P243_BLOCKED_LIVE_USB_HOST_ATTACHMENT_FORBIDDEN)

        rep_unlocked_wp = evaluate_usb_power_battery_and_lun_persistence_vault(
            UsbPowerBatteryInterlockAndLunVaultSpec(
                slot1_sdxc_wp_switch_locked=False,
            )
        )
        self.assertFalse(rep_unlocked_wp.passed)
        self.assertEqual(rep_unlocked_wp.block_code, P243_BLOCKED_LIVE_USB_HOST_ATTACHMENT_FORBIDDEN)

    def test_45_invalid_usb_connection_mode_or_model_rejected(self) -> None:
        rep = evaluate_usb_power_battery_and_lun_persistence_vault(
            UsbPowerBatteryInterlockAndLunVaultSpec(
                pre_reset_usb_connection_mode="InvalidMode",
                post_reset_usb_connection_mode="InvalidMode",
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P243_BLOCKED_INVALID_USB_POWER_OR_LUN_SPEC)

    def test_46_pillar39b_stageb_overlay_escape_rejected(self) -> None:
        rep = evaluate_usb_power_battery_and_lun_persistence_vault(
            UsbPowerBatteryInterlockAndLunVaultSpec(stage_b_overlay_dir="/dev/cnflasha2/usb_escape")
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P243_BLOCKED_PERSISTENT_OVERLAY_ESCAPE)

    def test_47_pillar39b_tier0_backup_bin_h0_h3_drift_rejected(self) -> None:
        rep = evaluate_usb_power_battery_and_lun_persistence_vault(
            UsbPowerBatteryInterlockAndLunVaultSpec(stage_b_backup_bin_writes=1)
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P243_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT)

    def test_48_pillar39b_persistent_write_unlock_request_rejected(self) -> None:
        rep = evaluate_usb_power_battery_and_lun_persistence_vault(
            UsbPowerBatteryInterlockAndLunVaultSpec(persistent_write_unlock_requested=True)
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P243_BLOCKED_SAFETY_POLICY_VIOLATION)


class TestCombinedPillar39AndMaster39PillarAggregator(unittest.TestCase):
    def test_49_combined_verifier_default_and_clean_room_pass(self) -> None:
        r_def = verify_framing_usbpower_lun_and_antiflicker_vault()
        self.assertTrue(r_def.all_passed)
        self.assertTrue(r_def.passed)
        self.assertEqual(r_def.status, P243_STATUS_VERIFIED_PILLAR39_SUITE)
        self.assertFalse(r_def.fx3_has_var_shutter)
        self.assertEqual(r_def.unbuffered_battery_pull_events, 0)
        self.assertFalse(r_def.hardware_live_attachment_authorized)
        self.assertEqual(r_def.physical_usb_packets_emitted, 0)
        self.assertEqual(r_def.physical_device_writes, 0)
        self.assertEqual(r_def.raw_firmware_bytes_leaked, 0)

        r_cr = verify_framing_usbpower_lun_and_antiflicker_vault(force_clean_room=True)
        self.assertTrue(r_cr.all_passed)
        self.assertEqual(r_cr.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_50_combined_verifier_propagates_39a_and_39b_failures(self) -> None:
        bad_39a = verify_framing_usbpower_lun_and_antiflicker_vault(
            framing_antiflicker_spec=FramingCropFullAndAntiFlickerVaultSpec(fx3_has_var_shutter=True),
            force_clean_room=True,
        )
        self.assertFalse(bad_39a.all_passed)
        self.assertEqual(bad_39a.status, P243_STATUS_FAIL_PILLAR39_SUITE)
        self.assertTrue(bad_39a.fx3_has_var_shutter)

        bad_39b = verify_framing_usbpower_lun_and_antiflicker_vault(
            usb_power_lun_spec=UsbPowerBatteryInterlockAndLunVaultSpec(
                battery_removed_during_usb_power=True
            ),
            force_clean_room=True,
        )
        self.assertFalse(bad_39b.all_passed)
        self.assertEqual(bad_39b.status, P243_STATUS_FAIL_PILLAR39_SUITE)
        self.assertEqual(bad_39b.unbuffered_battery_pull_events, 1)

    def test_51_standalone_pillar39_suite_dual_mode_determinism(self) -> None:
        s_def = run_pillar39_standalone_suite()
        s_cr1 = run_pillar39_standalone_suite(force_clean_room=True)
        s_cr2 = run_pillar39_standalone_suite(force_clean_room=True)
        self.assertTrue(s_def.all_passed)
        self.assertTrue(s_cr1.all_passed)
        self.assertEqual(s_cr1.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(s_cr1.suite_sha256, s_cr2.suite_sha256)
        self.assertEqual(s_cr1.pillar_39a_framing_antiflicker_vault.scenarios_passed, 6)
        self.assertEqual(s_cr1.pillar_39b_usb_power_lun_vault.scenarios_passed, 6)
        self.assertFalse(s_cr1.fx3_has_var_shutter)
        self.assertEqual(s_cr1.unbuffered_battery_pull_events, 0)
        self.assertFalse(s_cr1.hardware_live_attachment_authorized)

    def test_52_master_39pillar_default_mode_passes_39_of_39_under_budget(self) -> None:
        rep = _get_cached_master39_default()
        self.assertTrue(rep.all_passed)
        self.assertEqual(rep.status, P243_STATUS_VERIFIED_39OF39_AGGREGATOR)
        self.assertEqual(rep.pillar_count, 39)
        self.assertEqual(rep.pillars_passed, 39)
        self.assertEqual(rep.failed_pillars, ())
        self.assertTrue(rep.under_6s_budget)
        self.assertTrue(rep.nominal_under_4_0s)
        self.assertFalse(rep.fx3_has_var_shutter)
        self.assertEqual(rep.unbuffered_battery_pull_events, 0)
        self.assertFalse(rep.hardware_live_attachment_authorized)
        self.assertTrue(rep.cnflasha_userspace_write_blocked)
        self.assertEqual(rep.otp_fuse_touches, 0)
        self.assertEqual(rep.rpmb_counter_increments, 0)
        self.assertEqual(rep.passive_tx_bytes_emitted, 0)
        self.assertEqual(rep.physical_usb_packets_emitted, 0)
        self.assertEqual(rep.physical_device_writes, 0)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)
        self.assertFalse(rep.persistent_emmc_writes_authorized)

    def test_53_master_39pillar_clean_room_determinism(self) -> None:
        r1 = _get_cached_master39_clean_room()
        m38 = _get_cached_master38_clean_room()
        with mock.patch.object(p243, "evaluate_realhw_38pillar_recovery_master", return_value=m38):
            r2 = evaluate_realhw_39pillar_recovery_master(force_clean_room=True)
        self.assertTrue(r1.all_passed)
        self.assertEqual(r1.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(r1.master_39pillar_sha256, r2.master_39pillar_sha256)
        self.assertEqual(len(r1.master_39pillar_sha256), 64)

    def test_54_master_39pillar_env_force_clean_room_invariants(self) -> None:
        m38 = _get_cached_master38_clean_room()
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            with mock.patch.object(p243, "evaluate_realhw_38pillar_recovery_master", return_value=m38):
                rep = evaluate_realhw_39pillar_recovery_master()
        self.assertTrue(rep.all_passed)
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(rep.pillar_count, 39)
        self.assertEqual(rep.pillars_passed, 39)
        self.assertFalse(rep.fx3_has_var_shutter)
        self.assertEqual(rep.unbuffered_battery_pull_events, 0)
        self.assertFalse(rep.hardware_live_attachment_authorized)

    def test_55_master_39pillar_symmetry_aliases(self) -> None:
        m38 = _get_cached_master38_clean_room()
        with mock.patch.object(p243, "evaluate_realhw_38pillar_recovery_master", return_value=m38):
            r_alias = evaluate_39pillar_recovery_master(force_clean_room=True)
            r_cli = verify_39pillar_recovery_suite(force_clean_room=True)
        self.assertEqual(r_alias.master_39pillar_sha256, r_cli.master_39pillar_sha256)
        self.assertEqual(r_alias.pillars_passed, 39)

    def test_56_master_39pillar_fault_injection_pillar_39(self) -> None:
        m38 = _get_cached_master38_clean_room()
        with mock.patch.object(p243, "evaluate_realhw_38pillar_recovery_master", return_value=m38):
            rep = evaluate_realhw_39pillar_recovery_master(
                force_clean_room=True,
                fault_inject_pillar="pillar_39_framing_usbpower_lun_antiflicker_vault",
            )
        self.assertFalse(rep.all_passed)
        self.assertEqual(rep.status, P243_STATUS_FAIL_39OF39_AGGREGATOR)
        self.assertEqual(rep.pillars_passed, 38)
        self.assertEqual(rep.failed_pillars, ("pillar_39_framing_usbpower_lun_antiflicker_vault",))

    def test_57_master_39pillar_fault_injection_pillar_38_and_pillar_1(self) -> None:
        m38 = _get_cached_master38_clean_room()
        first_id = MASTER_39_PILLAR_IDS[0]
        for target_id in ("pillar_38_shoe_audio_wind_saveload_vault", first_id):
            with self.subTest(fault_pillar=target_id):
                with mock.patch.object(p243, "evaluate_realhw_38pillar_recovery_master", return_value=m38):
                    rep = evaluate_realhw_39pillar_recovery_master(
                        force_clean_room=True,
                        fault_inject_pillar=target_id,
                    )
                self.assertFalse(rep.all_passed)
                self.assertEqual(rep.pillars_passed, 38)
                self.assertEqual(rep.failed_pillars, (target_id,))

    def test_58_master_39pillar_unknown_fault_inject_raises(self) -> None:
        with self.assertRaises(ValueError):
            evaluate_realhw_39pillar_recovery_master(
                force_clean_room=True,
                fault_inject_pillar="nonexistent_pillar_99",
            )

    def test_59_master_39pillar_pillar39_entry_key_metrics_verified(self) -> None:
        rep = _get_cached_master39_clean_room()
        p39_entry = rep.pillars[38]
        self.assertEqual(p39_entry.pillar_number, 39)
        self.assertEqual(p39_entry.pillar_id, "pillar_39_framing_usbpower_lun_antiflicker_vault")
        self.assertTrue(p39_entry.passed)
        self.assertEqual(p39_entry.key_metrics["pillar_39a_framing_antiflicker_vault"], "6/6")
        self.assertEqual(p39_entry.key_metrics["pillar_39b_usb_power_lun_vault"], "6/6")
        self.assertIs(p39_entry.key_metrics["fx3_has_var_shutter"], False)
        self.assertEqual(p39_entry.key_metrics["unbuffered_battery_pull_events"], 0)
        self.assertIs(p39_entry.key_metrics["hardware_live_attachment_authorized"], False)
        self.assertEqual(p39_entry.key_metrics["donor_files_inspected"], 9)

    def test_60_json_serialization_roundtrip_master_and_reports(self) -> None:
        rep = _get_cached_master39_clean_room()
        encoded = json.dumps(rep.to_dict(), sort_keys=True, allow_nan=False)
        decoded = json.loads(encoded)
        self.assertEqual(decoded["status"], P243_STATUS_VERIFIED_39OF39_AGGREGATOR)
        self.assertEqual(decoded["pillar_count"], 39)
        self.assertEqual(decoded["pillars_passed"], 39)
        p39_comb = verify_framing_usbpower_lun_and_antiflicker_vault(force_clean_room=True)
        self.assertTrue(json.loads(json.dumps(p39_comb.to_dict(), sort_keys=True))["all_passed"])


class TestBackwardCompatibilityAndCli(unittest.TestCase):
    def test_61_backward_compatibility_with_38pillar_master(self) -> None:
        rep38 = _get_cached_master38_clean_room()
        self.assertTrue(rep38.all_passed)
        self.assertEqual(rep38.pillar_count, 38)
        self.assertEqual(rep38.pillars_passed, 38)

    def test_62_backward_compatibility_callable_exports_22_to_38(self) -> None:
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
        ):
            with self.subTest(pillars=count):
                self.assertTrue(callable(getattr(fx3_recovery, attr_name)))
        rep_m = _get_cached_master39_clean_room()
        self.assertEqual([p.pillar_number for p in rep_m.pillars], list(range(1, 40)))

    def test_63_cli_verify_framing_usbpower_lun_antiflicker_vault_summary_and_json(self) -> None:
        rc_txt, out_txt = _run_inprocess_cli("verify-framing-usbpower-lun-antiflicker-vault")
        self.assertEqual(rc_txt, 0)
        self.assertIn("status=VERIFIED_PILLAR39_FRAMING_USBPOWER_LUN_ANTIFLICKER_VAULT", out_txt)
        self.assertIn("pillar_39a=6/6", out_txt)
        self.assertIn("pillar_39b=6/6", out_txt)
        self.assertIn("fx3_has_var_shutter=False", out_txt)
        self.assertIn("unbuffered_battery_pull_events=0", out_txt)
        self.assertIn("hardware_live_attachment_authorized=False", out_txt)

        rc_js, out_js = _run_inprocess_cli("verify-framing-usbpower-lun-antiflicker-vault", "--json")
        self.assertEqual(rc_js, 0)
        payload = json.loads(out_js)
        self.assertTrue(payload["all_passed"])
        self.assertEqual(payload["schema"], PHASE243_SCHEMA)

    def test_64_cli_verify_framing_usbpower_lun_antiflicker_vault_force_clean_room(self) -> None:
        rc, out = _run_inprocess_cli(
            "verify-framing-usbpower-lun-antiflicker-vault", "--force-clean-room", "--json"
        )
        self.assertEqual(rc, 0)
        payload = json.loads(out)
        self.assertTrue(payload["all_passed"])
        self.assertEqual(payload["verification_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertFalse(payload["fx3_has_var_shutter"])
        self.assertEqual(payload["unbuffered_battery_pull_events"], 0)
        self.assertFalse(payload["hardware_live_attachment_authorized"])

    def test_65_cli_verify_framing_usbpower_lun_antiflicker_vault_subprocess_smoke(self) -> None:
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ADAPTER_ROOT)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "fx3_recovery",
                "verify-framing-usbpower-lun-antiflicker-vault",
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

    def test_66_cli_verify_39pillar_recovery_summary_json_and_clean_room_forwarding(self) -> None:
        cached = _get_cached_master39_default()
        with mock.patch.object(cli_main, "verify_39pillar_recovery_suite", return_value=cached):
            rc_txt, out_txt = _run_inprocess_cli("verify-39pillar-recovery")
            self.assertEqual(rc_txt, 0)
            self.assertIn("status=VERIFIED_39OF39_PILLAR_RECOVERY_MASTER", out_txt)
            self.assertIn("pillars=39/39", out_txt)
            self.assertIn("pillar39_a=6/6", out_txt)
            self.assertIn("pillar39_b=6/6", out_txt)

            rc_js, out_js = _run_inprocess_cli("verify-39pillar-recovery", "--json")
            self.assertEqual(rc_js, 0)
            payload = json.loads(out_js)
            self.assertEqual(payload["pillar_count"], 39)
            self.assertEqual(payload["pillars_passed"], 39)

        cached_cr = _get_cached_master39_clean_room()
        with mock.patch.object(
            cli_main, "verify_39pillar_recovery_suite", return_value=cached_cr
        ) as mocked_suite:
            rc_cr, out_cr = _run_inprocess_cli("verify-39pillar-recovery", "--clean-room", "--json")
        self.assertEqual(rc_cr, 0)
        mocked_suite.assert_called_once_with(force_clean_room=True)
        self.assertEqual(json.loads(out_cr)["verification_mode"], "CLEAN_ROOM_SYNTHETIC")

    def test_67_cli_out_creates_exclusive_directories_for_pillar39_and_39pillar_master(self) -> None:
        here = Path(__file__).resolve().parent
        out_p39 = here / f"_tmp_p243_p39_{os.getpid()}"
        rep_p39 = out_p39 / "pillar39-framing-usbpower-lun-antiflicker-vault-report.json"
        out_m39 = here / f"_tmp_p243_m39_{os.getpid()}"
        rep_m39 = out_m39 / "39pillar-recovery-master-report.json"
        for f, d in ((rep_p39, out_p39), (rep_m39, out_m39)):
            if f.is_file():
                f.unlink()
            if d.is_dir():
                d.rmdir()
        try:
            rc1, _ = _run_inprocess_cli(
                "verify-framing-usbpower-lun-antiflicker-vault",
                "--force-clean-room",
                "--out",
                str(out_p39),
            )
            self.assertEqual(rc1, 0)
            self.assertTrue(rep_p39.is_file())
            self.assertEqual(
                json.loads(rep_p39.read_text(encoding="utf-8"))["schema"],
                PHASE243_SCHEMA,
            )

            cached_cr = _get_cached_master39_clean_room()
            with mock.patch.object(cli_main, "verify_39pillar_recovery_suite", return_value=cached_cr):
                rc2, _ = _run_inprocess_cli(
                    "verify-39pillar-recovery",
                    "--force-clean-room",
                    "--out",
                    str(out_m39),
                )
            self.assertEqual(rc2, 0)
            self.assertTrue(rep_m39.is_file())
            self.assertEqual(
                json.loads(rep_m39.read_text(encoding="utf-8"))["pillar_count"],
                39,
            )
        finally:
            for f, d in ((rep_p39, out_p39), (rep_m39, out_m39)):
                if f.is_file():
                    f.unlink()
                if d.is_dir():
                    d.rmdir()

    def test_68_cli_out_refuses_preexisting_directory_overwrite_guard(self) -> None:
        here = Path(__file__).resolve().parent
        existing_dir = here / f"_tmp_p243_exist_{os.getpid()}"
        existing_dir.mkdir(exist_ok=True)
        try:
            rc, out = _run_inprocess_cli(
                "verify-framing-usbpower-lun-antiflicker-vault",
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
