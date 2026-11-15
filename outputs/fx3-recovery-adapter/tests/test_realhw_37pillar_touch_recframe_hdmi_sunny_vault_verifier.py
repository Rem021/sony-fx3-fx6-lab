"""Phase 238 — Dual-mode unit tests for Pillar 37 (`[Touch Operation]` 4-item `[Camera Settings Reset]`
survival & unattended Tier-0 `75 MiB` `p3` bench vault accidental-tap firewall; `[Monitor Brightness]`
`[Manual]` (`0`) vs `[Sunny Weather]` indoor `NP-FZ100` battery/thermal guard; `[Emphasized REC Display]`
vs `[Grid Line Display]` reset split, HDMI info routing vs forced `[Off(HDMI Only)]` / `RAW` clean-feed
clamp & Slot-1 `CAMSET01.DAT` recovery) and unified `37/37` recovery master (`verify-37pillar-recovery`)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

import fx3_recovery
from fx3_recovery import realhw_37pillar_touch_recframe_hdmi_sunny_vault_verifier as p238
from fx3_recovery.realhw_37pillar_touch_recframe_hdmi_sunny_vault_verifier import (
    ALLOW_BOOT_PARTITION_TARGETING,
    ALLOW_DESTRUCTIVE_FASTBOOT,
    ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS,
    ALLOW_PERSISTENT_JIRITSU_WRITES,
    CNFLASHA_USERSPACE_WRITE_BLOCKED,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    ISP_WRITE_AUTHORIZED,
    LIVE_USB_IOKIT_TRANSMIT_ENABLED,
    MASTER_37_PILLAR_COUNT,
    MASTER_37_PILLAR_IDS,
    MASTER_37_PILLAR_SPECS,
    OTP_FUSE_TOUCHES,
    OTP_FUSE_WRITES,
    P238_BENCH_SAFE_TOUCH_OPERATION_MODES,
    P238_BLOCKED_ACCIDENTAL_CAPACITIVE_TAP_FN_OR_TRACKING_LEAK,
    P238_BLOCKED_BENCH_NP_FZ100_BELOW_TIER0_FLOOR,
    P238_BLOCKED_CAMSET_SLOT1_RECFRAME_GRID_RESTORE_DRIFT,
    P238_BLOCKED_EMPHASIZED_REC_OR_GRID_RESET_SPLIT_DRIFT,
    P238_BLOCKED_HDMI_INFO_ROUTING_OR_LCD_BLANK_MISMATCH,
    P238_BLOCKED_HDMI_ONLY_OR_RAW_CLEAN_FEED_CLAMP_VIOLATION,
    P238_BLOCKED_INDOOR_BENCH_SUNNY_WEATHER_OR_BRIGHTNESS_DRIFT,
    P238_BLOCKED_INVALID_RECFRAME_GRID_OR_HDMI_SPEC,
    P238_BLOCKED_INVALID_TOUCH_OR_BRIGHTNESS_SPEC,
    P238_BLOCKED_LOCAL_ONLY_ASSIST_HDMI_LEAKAGE,
    P238_BLOCKED_MONITOR_BRIGHTNESS_RESET_PERSISTENCE_DRIFT,
    P238_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
    P238_BLOCKED_SAFETY_POLICY_VIOLATION,
    P238_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
    P238_BLOCKED_TOUCH_SETUP_CAMERA_SETTINGS_RESET_DRIFT,
    P238_BLOCKED_UNATTENDED_BENCH_TOUCH_OPERATION_ACTIVE,
    P238_CAMSET_FILENAMES,
    P238_EMPHASIZED_REC_DEFAULT,
    P238_EMPHASIZED_REC_MENU_PATH,
    P238_EMPHASIZED_REC_MODES,
    P238_EMPHASIZED_REC_SCOPES,
    P238_FX3_SUPPORTED_FW_VERSIONS,
    P238_GRID_LINE_DISPLAY_DEFAULT,
    P238_GRID_LINE_MENU_PATH,
    P238_GRID_LINE_TYPES,
    P238_GRID_LINE_TYPE_DEFAULT,
    P238_HDMI_INFO_DISPLAY_MODES,
    P238_HDMI_OUTPUT_SETTINGS_MENU_PATH,
    P238_HDMI_RAW_OUTPUT_MODES,
    P238_MONITOR_BRIGHTNESS_DEFAULT_LEVEL,
    P238_MONITOR_BRIGHTNESS_DEFAULT_MODE,
    P238_MONITOR_BRIGHTNESS_MANUAL_LEVELS,
    P238_MONITOR_BRIGHTNESS_MENU_PATH,
    P238_MONITOR_BRIGHTNESS_MODES,
    P238_PILLAR_37A_SCENARIO_IDS,
    P238_PILLAR_37B_SCENARIO_IDS,
    P238_PINNED_FX3_LIBGPE_SO_BYTES,
    P238_PINNED_FX3_LIBGPE_SO_SHA256,
    P238_PINNED_FX3_LIBSAVELOADSETTINGS_SO_BYTES,
    P238_PINNED_FX3_LIBSAVELOADSETTINGS_SO_SHA256,
    P238_REC_MEDIA_DUR_HDMI_MODES,
    P238_STATUS_FAIL_37OF37_AGGREGATOR,
    P238_STATUS_VERIFIED_37OF37_AGGREGATOR,
    P238_STATUS_VERIFIED_PILLAR37_SUITE,
    P238_STATUS_VERIFIED_PILLAR_37A,
    P238_STATUS_VERIFIED_PILLAR_37B,
    P238_SWIPE_UP_DEFAULT,
    P238_SWIPE_UP_MODES,
    P238_TIER0_BENCH_MIN_NP_FZ100_PCT,
    P238_TIER0_P3_VAULT_DUMP_MIB,
    P238_TOUCH_FUNC_IN_SHOOTING_DEFAULT,
    P238_TOUCH_FUNC_IN_SHOOTING_MODES,
    P238_TOUCH_OPERATION_DEFAULT,
    P238_TOUCH_OPERATION_MODES,
    P238_TOUCH_SENSITIVITY_DEFAULT,
    P238_TOUCH_SENSITIVITY_MODES,
    P238_TOUCH_SETUP_4_ITEMS,
    P238_TOUCH_SETUP_MENU_PATH,
    PASSIVE_TX_BYTES_EMITTED,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHASE238_SCHEMA,
    PHASE238_VERSION,
    PHYSICAL_DEVICE_WRITES,
    PHYSICAL_USB_PACKETS_EMITTED,
    RAW_FIRMWARE_BYTES_LEAKED,
    READ_ONLY_DONOR_ACCESS,
    RPMB_COUNTER_INCREMENTS,
    SPI_NOR_WRITE_AUTHORIZED,
    EmphasizedRecGridHdmiCleanFeedVaultSpec,
    TouchBenchVaultAndSunnyWeatherSpec,
    build_default_safe_recframe_grid_hdmi_vault_spec,
    build_default_safe_touch_sunny_weather_vault_spec,
    evaluate_37pillar_recovery_master,
    evaluate_emphasized_rec_grid_hdmi_clean_feed_vault,
    evaluate_realhw_37pillar_recovery_master,
    evaluate_touch_bench_vault_and_sunny_weather_guard,
    inspect_phase238_donors_readonly,
    run_pillar37_standalone_suite,
    run_pillar37a_touch_bench_sunny_weather_6_scenario_suite,
    run_pillar37b_recframe_grid_hdmi_vault_6_scenario_suite,
    verify_37pillar_recovery_suite,
    verify_touch_recframe_hdmi_and_sunny_weather_vault,
)

ADAPTER_ROOT = Path(__file__).resolve().parents[1]


def _cleanup_exclusive_out_dir(out_dir: Path, expected_filenames: tuple[str, ...]) -> None:
    if not out_dir.exists():
        return
    for name in expected_filenames:
        candidate = out_dir / name
        if candidate.is_file():
            candidate.unlink()
    for child in list(out_dir.iterdir()):
        if child.is_file():
            child.unlink()
    out_dir.rmdir()


class TestPhase238SafetyAndExports(unittest.TestCase):
    def test_01_hard_locked_safety_constants(self) -> None:
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
        self.assertTrue(READ_ONLY_DONOR_ACCESS)
        self.assertTrue(CNFLASHA_USERSPACE_WRITE_BLOCKED)
        self.assertEqual(OTP_FUSE_TOUCHES, 0)
        self.assertEqual(OTP_FUSE_WRITES, 0)
        self.assertEqual(RPMB_COUNTER_INCREMENTS, 0)
        self.assertEqual(PASSIVE_TX_BYTES_EMITTED, 0)
        self.assertEqual(PHYSICAL_USB_PACKETS_EMITTED, 0)
        self.assertEqual(PHYSICAL_DEVICE_WRITES, 0)
        self.assertEqual(RAW_FIRMWARE_BYTES_LEAKED, 0)

    def test_02_package_exports_and_non_shadowing(self) -> None:
        for sym in (
            "realhw_37pillar_touch_recframe_hdmi_sunny_vault_verifier",
            "MASTER_37_PILLAR_COUNT",
            "MASTER_37_PILLAR_IDS",
            "MASTER_37_PILLAR_SPECS",
            "PHASE238_SCHEMA",
            "PHASE238_VERSION",
            "verify_touch_recframe_hdmi_and_sunny_weather_vault",
            "evaluate_realhw_37pillar_recovery_master",
            "evaluate_37pillar_recovery_master",
            "verify_37pillar_recovery_suite",
            "run_pillar37_standalone_suite",
        ):
            self.assertIn(sym, fx3_recovery.__all__)
            self.assertTrue(hasattr(fx3_recovery, sym))
        self.assertEqual(fx3_recovery.MASTER_36_PILLAR_COUNT, 36)
        self.assertEqual(fx3_recovery.MASTER_37_PILLAR_COUNT, 37)

    def test_03_master_37_pillar_registry_extends_36(self) -> None:
        self.assertEqual(MASTER_37_PILLAR_COUNT, 37)
        self.assertEqual(len(MASTER_37_PILLAR_SPECS), 37)
        self.assertEqual(len(MASTER_37_PILLAR_IDS), 37)
        self.assertEqual(len(set(MASTER_37_PILLAR_IDS)), 37)
        self.assertEqual([s[0] for s in MASTER_37_PILLAR_SPECS], list(range(1, 38)))
        self.assertEqual(MASTER_37_PILLAR_SPECS[:36], fx3_recovery.MASTER_36_PILLAR_SPECS)
        self.assertEqual(
            MASTER_37_PILLAR_SPECS[36],
            (
                37,
                "pillar_37_touch_recframe_hdmi_sunny_vault",
                "Phase 238",
                "fx3_recovery.realhw_37pillar_touch_recframe_hdmi_sunny_vault_verifier",
            ),
        )

    def test_04_wave35_menu_paths_and_enums(self) -> None:
        self.assertEqual(P238_TOUCH_SETUP_MENU_PATH, ("MENU", "Setup", "Touch Operation"))
        self.assertEqual(
            P238_TOUCH_SETUP_4_ITEMS,
            ("Touch Operation", "Touch Sensitivity", "Swipe Up", "Touch Func. in Shooting"),
        )
        self.assertEqual(P238_TOUCH_OPERATION_MODES, ("On", "On: Playback Only", "Off"))
        self.assertEqual(P238_BENCH_SAFE_TOUCH_OPERATION_MODES, ("Off", "On: Playback Only"))
        self.assertEqual(P238_TOUCH_SENSITIVITY_MODES, ("Standard", "Sensitive"))
        self.assertEqual(P238_SWIPE_UP_MODES, ("Open the Fn Menu", "Off"))
        self.assertEqual(P238_TOUCH_FUNC_IN_SHOOTING_MODES, ("Touch Tracking", "Touch Focus", "Off"))
        self.assertEqual(P238_MONITOR_BRIGHTNESS_MENU_PATH, ("MENU", "Setup", "Monitor", "Monitor Brightness"))
        self.assertEqual(P238_MONITOR_BRIGHTNESS_MODES, ("Manual", "Sunny Weather"))
        self.assertEqual(P238_MONITOR_BRIGHTNESS_MANUAL_LEVELS, (-2, -1, 0, 1, 2))
        self.assertEqual(P238_EMPHASIZED_REC_MENU_PATH, ("MENU", "Shooting", "Shooting Display", "Emphasized REC Display"))
        self.assertEqual(P238_EMPHASIZED_REC_MODES, ("On", "Off"))
        self.assertEqual(P238_EMPHASIZED_REC_SCOPES, ("Movie", "S&Q"))
        self.assertEqual(P238_GRID_LINE_MENU_PATH, ("MENU", "Shooting", "Shooting Display", "Grid Line Display"))
        self.assertEqual(P238_GRID_LINE_TYPES, ("Rule of 3rds Grid", "Square Grid", "Diag. + Square Grid"))
        self.assertEqual(P238_HDMI_OUTPUT_SETTINGS_MENU_PATH, ("MENU", "Setup", "External Output", "HDMI Output Settings"))
        self.assertEqual(P238_REC_MEDIA_DUR_HDMI_MODES, ("On", "Off(HDMI Only)"))
        self.assertEqual(P238_HDMI_RAW_OUTPUT_MODES, ("Off", "On"))
        self.assertEqual(P238_HDMI_INFO_DISPLAY_MODES, ("Off", "On"))
        self.assertEqual(P238_TIER0_P3_VAULT_DUMP_MIB, 75)
        self.assertEqual(P238_TIER0_BENCH_MIN_NP_FZ100_PCT, 51)
        self.assertIn("7.02", P238_FX3_SUPPORTED_FW_VERSIONS)


class TestPhase238DonorInspection(unittest.TestCase):
    def test_05_donor_inspection_default_mode_under_0_15s(self) -> None:
        snap = inspect_phase238_donors_readonly()
        self.assertTrue(snap.all_donors_present)
        self.assertEqual(snap.donor_files_inspected, 7)
        self.assertTrue(snap.under_0_15s_budget)
        self.assertEqual(snap.raw_firmware_bytes_leaked, 0)
        self.assertIn(snap.verification_mode, ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"))
        for art in snap.artifacts:
            self.assertTrue(art.present)
            self.assertTrue(art.matches_pinned)
            self.assertEqual(len(art.digest_sha256), 64)

    def test_06_donor_inspection_force_clean_room_mode(self) -> None:
        snap = inspect_phase238_donors_readonly(force_clean_room=True)
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(snap.all_donors_present)
        self.assertEqual(snap.donor_files_inspected, 7)
        self.assertTrue(snap.under_0_15s_budget)
        self.assertTrue(all(a.read_mode == "CLEAN_ROOM_SYNTHETIC" for a in snap.artifacts))

    def test_07_donor_inspection_env_force_clean_room(self) -> None:
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            snap = inspect_phase238_donors_readonly()
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(snap.all_donors_present)

    def test_08_donor_inspection_missing_donor_auto_clean_room_fallback(self) -> None:
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "0"}):
            with mock.patch.object(p238, "resolve_donor_path", return_value=None):
                snap = inspect_phase238_donors_readonly(force_clean_room=None)
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(snap.all_donors_present)
        self.assertEqual(snap.donor_files_inspected, 7)

    def test_09_donor_libsaveloadsettings_and_libgpe_elf64_aarch64_tokens(self) -> None:
        snap = inspect_phase238_donors_readonly()
        by_id = {a.artifact_id: a for a in snap.artifacts}
        sls = by_id["fx3_libsaveloadsettings_so"]
        self.assertEqual(sls.total_bytes, P238_PINNED_FX3_LIBSAVELOADSETTINGS_SO_BYTES)
        self.assertEqual(sls.digest_sha256, P238_PINNED_FX3_LIBSAVELOADSETTINGS_SO_SHA256)
        self.assertIn("SaveLoadSettingsIf", sls.marker_summary)
        self.assertIn("Backup_read", sls.marker_summary)
        self.assertIn("Backup_write", sls.marker_summary)

        gpe = by_id["fx3_libgpe_so"]
        self.assertEqual(gpe.total_bytes, P238_PINNED_FX3_LIBGPE_SO_BYTES)
        self.assertEqual(gpe.digest_sha256, P238_PINNED_FX3_LIBGPE_SO_SHA256)
        self.assertIn("gpe_blog_error", gpe.marker_summary)
        self.assertIn("_ZNK5mpgpe5Gperm4InitEv", gpe.marker_summary)

    def test_10_elf64_aarch64_token_checker_rejects_invalid_headers_and_missing_tokens(self) -> None:
        ok, msg = p238._check_elf64_aarch64_tokens(b"not-an-elf", ())
        self.assertFalse(ok)
        self.assertEqual(msg, "NOT_ELF")

        bad_arch = bytearray(64)
        bad_arch[:4] = b"\x7fELF"
        bad_arch[4] = 2
        bad_arch[5] = 1
        bad_arch[18:20] = (62).to_bytes(2, "little")  # x86_64 instead of 183
        ok2, msg2 = p238._check_elf64_aarch64_tokens(bytes(bad_arch), ())
        self.assertFalse(ok2)
        self.assertIn("BAD_ELF64_AARCH64", msg2)

        good_arch = bytearray(64)
        good_arch[:4] = b"\x7fELF"
        good_arch[4] = 2
        good_arch[5] = 1
        good_arch[18:20] = (183).to_bytes(2, "little")
        ok3, msg3 = p238._check_elf64_aarch64_tokens(bytes(good_arch), (b"SaveLoadSettingsIf",))
        self.assertFalse(ok3)
        self.assertIn("MISSING_TOKENS:SaveLoadSettingsIf", msg3)


class TestPillar37ATouchBenchVaultAndSunnyWeatherGuard(unittest.TestCase):
    def test_11_default_safe_touch_off_and_manual_zero_brightness_survive_camera_settings_reset(self) -> None:
        spec = build_default_safe_touch_sunny_weather_vault_spec()
        rep = evaluate_touch_bench_vault_and_sunny_weather_guard(spec)
        self.assertTrue(rep.passed)
        self.assertEqual(rep.status, P238_STATUS_VERIFIED_PILLAR_37A)
        self.assertIsNone(rep.block_code)
        self.assertTrue(rep.touch_4item_reset_survival_verified)
        self.assertTrue(rep.unattended_p3_vault_tap_firewall_verified)
        self.assertTrue(rep.monitor_brightness_reset_survival_verified)
        self.assertTrue(rep.indoor_sunny_weather_battery_guard_verified)
        self.assertTrue(rep.h0_equals_h3_verified)
        self.assertEqual(rep.physical_device_writes, 0)
        self.assertFalse(rep.persistent_emmc_writes_authorized)

    def test_12_playback_only_touch_sensitive_focus_survives_reset_and_blocks_shooting_tap(self) -> None:
        rep = evaluate_touch_bench_vault_and_sunny_weather_guard(
            TouchBenchVaultAndSunnyWeatherSpec(
                pre_reset_touch_operation="On: Playback Only",
                pre_reset_touch_sensitivity="Sensitive",
                pre_reset_swipe_up="Off",
                pre_reset_touch_func_in_shooting="Touch Focus",
                reset_action="Camera Settings Reset",
                post_reset_touch_operation="On: Playback Only",
                post_reset_touch_sensitivity="Sensitive",
                post_reset_swipe_up="Off",
                post_reset_touch_func_in_shooting="Touch Focus",
                capacitive_shooting_touch_blocked=True,
                capacitive_playback_touch_blocked=False,
                unattended_tier0_p3_vault_dump_active=True,
            )
        )
        self.assertTrue(rep.passed)
        self.assertTrue(rep.unattended_p3_vault_tap_firewall_verified)

    def test_13_touch_4_items_survive_none_reset_unchanged(self) -> None:
        rep = evaluate_touch_bench_vault_and_sunny_weather_guard(
            TouchBenchVaultAndSunnyWeatherSpec(
                pre_reset_touch_operation="Off",
                pre_reset_touch_sensitivity="Sensitive",
                pre_reset_swipe_up="Off",
                pre_reset_touch_func_in_shooting="Off",
                reset_action="NONE",
                post_reset_touch_operation="Off",
                post_reset_touch_sensitivity="Sensitive",
                post_reset_swipe_up="Off",
                post_reset_touch_func_in_shooting="Off",
            )
        )
        self.assertTrue(rep.passed)

    def test_14_initialize_resets_all_4_touch_items_and_monitor_brightness_to_factory_defaults(self) -> None:
        rep = evaluate_touch_bench_vault_and_sunny_weather_guard(
            TouchBenchVaultAndSunnyWeatherSpec(
                pre_reset_touch_operation="Off",
                pre_reset_touch_sensitivity="Sensitive",
                pre_reset_swipe_up="Off",
                pre_reset_touch_func_in_shooting="Touch Focus",
                pre_reset_monitor_brightness_mode="Sunny Weather",
                pre_reset_monitor_brightness_manual_level=2,
                reset_action="Initialize",
                post_reset_touch_operation=P238_TOUCH_OPERATION_DEFAULT,
                post_reset_touch_sensitivity=P238_TOUCH_SENSITIVITY_DEFAULT,
                post_reset_swipe_up=P238_SWIPE_UP_DEFAULT,
                post_reset_touch_func_in_shooting=P238_TOUCH_FUNC_IN_SHOOTING_DEFAULT,
                post_reset_monitor_brightness_mode=P238_MONITOR_BRIGHTNESS_DEFAULT_MODE,
                post_reset_monitor_brightness_manual_level=P238_MONITOR_BRIGHTNESS_DEFAULT_LEVEL,
                unattended_tier0_p3_vault_dump_active=False,
                capacitive_shooting_touch_blocked=False,
                capacitive_playback_touch_blocked=False,
            )
        )
        self.assertTrue(rep.passed)

    def test_15_reject_touch_operation_wiped_by_camera_settings_reset(self) -> None:
        rep = evaluate_touch_bench_vault_and_sunny_weather_guard(
            TouchBenchVaultAndSunnyWeatherSpec(
                pre_reset_touch_operation="Off",
                reset_action="Camera Settings Reset",
                post_reset_touch_operation="On",
                unattended_tier0_p3_vault_dump_active=False,
                capacitive_shooting_touch_blocked=False,
                capacitive_playback_touch_blocked=False,
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P238_BLOCKED_TOUCH_SETUP_CAMERA_SETTINGS_RESET_DRIFT)

    def test_16_reject_touch_sensitivity_swipe_up_or_touch_func_wiped_by_camera_settings_reset(self) -> None:
        for field_kwargs in (
            {"pre_reset_touch_sensitivity": "Sensitive", "post_reset_touch_sensitivity": "Standard"},
            {"pre_reset_swipe_up": "Off", "post_reset_swipe_up": "Open the Fn Menu"},
            {"pre_reset_touch_func_in_shooting": "Touch Focus", "post_reset_touch_func_in_shooting": "Touch Tracking"},
        ):
            with self.subTest(field_kwargs=field_kwargs):
                rep = evaluate_touch_bench_vault_and_sunny_weather_guard(
                    TouchBenchVaultAndSunnyWeatherSpec(
                        reset_action="Camera Settings Reset",
                        **field_kwargs,
                    )
                )
                self.assertFalse(rep.passed)
                self.assertEqual(rep.block_code, P238_BLOCKED_TOUCH_SETUP_CAMERA_SETTINGS_RESET_DRIFT)

    def test_17_reject_touch_4_items_failing_to_reset_under_initialize(self) -> None:
        rep = evaluate_touch_bench_vault_and_sunny_weather_guard(
            TouchBenchVaultAndSunnyWeatherSpec(
                pre_reset_touch_operation="Off",
                reset_action="Initialize",
                post_reset_touch_operation="Off",
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P238_BLOCKED_TOUCH_SETUP_CAMERA_SETTINGS_RESET_DRIFT)

    def test_18_reject_unattended_75mib_p3_vault_dump_with_touch_operation_on(self) -> None:
        rep = evaluate_touch_bench_vault_and_sunny_weather_guard(
            TouchBenchVaultAndSunnyWeatherSpec(
                pre_reset_touch_operation="On",
                post_reset_touch_operation="On",
                capacitive_shooting_touch_blocked=False,
                capacitive_playback_touch_blocked=False,
                unattended_tier0_p3_vault_dump_active=True,
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P238_BLOCKED_UNATTENDED_BENCH_TOUCH_OPERATION_ACTIVE)

    def test_19_allow_touch_operation_on_only_when_unattended_p3_vault_dump_inactive(self) -> None:
        rep = evaluate_touch_bench_vault_and_sunny_weather_guard(
            TouchBenchVaultAndSunnyWeatherSpec(
                pre_reset_touch_operation="On",
                post_reset_touch_operation="On",
                capacitive_shooting_touch_blocked=False,
                capacitive_playback_touch_blocked=False,
                unattended_tier0_p3_vault_dump_active=False,
            )
        )
        self.assertTrue(rep.passed)

    def test_20_reject_accidental_fn_menu_swipe_or_shooting_touch_trigger_leak(self) -> None:
        for fn_cnt, shoot_cnt in ((1, 0), (0, 2)):
            with self.subTest(fn_cnt=fn_cnt, shoot_cnt=shoot_cnt):
                rep = evaluate_touch_bench_vault_and_sunny_weather_guard(
                    TouchBenchVaultAndSunnyWeatherSpec(
                        accidental_fn_menu_opened_count=fn_cnt,
                        accidental_shooting_touch_triggers=shoot_cnt,
                    )
                )
                self.assertFalse(rep.passed)
                self.assertEqual(rep.block_code, P238_BLOCKED_ACCIDENTAL_CAPACITIVE_TAP_FN_OR_TRACKING_LEAK)

    def test_21_reject_touch_off_or_playback_only_handler_mask_mismatch(self) -> None:
        rep_off = evaluate_touch_bench_vault_and_sunny_weather_guard(
            TouchBenchVaultAndSunnyWeatherSpec(
                pre_reset_touch_operation="Off",
                post_reset_touch_operation="Off",
                capacitive_shooting_touch_blocked=True,
                capacitive_playback_touch_blocked=False,
            )
        )
        self.assertFalse(rep_off.passed)
        self.assertEqual(rep_off.block_code, P238_BLOCKED_ACCIDENTAL_CAPACITIVE_TAP_FN_OR_TRACKING_LEAK)

        rep_pb = evaluate_touch_bench_vault_and_sunny_weather_guard(
            TouchBenchVaultAndSunnyWeatherSpec(
                pre_reset_touch_operation="On: Playback Only",
                post_reset_touch_operation="On: Playback Only",
                capacitive_shooting_touch_blocked=True,
                capacitive_playback_touch_blocked=True,
            )
        )
        self.assertFalse(rep_pb.passed)
        self.assertEqual(rep_pb.block_code, P238_BLOCKED_ACCIDENTAL_CAPACITIVE_TAP_FN_OR_TRACKING_LEAK)

        rep_on_false_claim = evaluate_touch_bench_vault_and_sunny_weather_guard(
            TouchBenchVaultAndSunnyWeatherSpec(
                pre_reset_touch_operation="On",
                post_reset_touch_operation="On",
                capacitive_shooting_touch_blocked=True,
                capacitive_playback_touch_blocked=False,
                unattended_tier0_p3_vault_dump_active=False,
            )
        )
        self.assertFalse(rep_on_false_claim.passed)
        self.assertEqual(rep_on_false_claim.block_code, P238_BLOCKED_ACCIDENTAL_CAPACITIVE_TAP_FN_OR_TRACKING_LEAK)

    def test_22_reject_unattended_75mib_p3_vault_dump_below_51pct_np_fz100_floor(self) -> None:
        rep = evaluate_touch_bench_vault_and_sunny_weather_guard(
            TouchBenchVaultAndSunnyWeatherSpec(
                np_fz100_charge_pct=50,
                unattended_tier0_p3_vault_dump_active=True,
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P238_BLOCKED_BENCH_NP_FZ100_BELOW_TIER0_FLOOR)

    def test_23_monitor_brightness_sunny_weather_and_manual_levels_survive_camera_settings_reset_outdoors(self) -> None:
        rep_sunny = evaluate_touch_bench_vault_and_sunny_weather_guard(
            TouchBenchVaultAndSunnyWeatherSpec(
                pre_reset_monitor_brightness_mode="Sunny Weather",
                post_reset_monitor_brightness_mode="Sunny Weather",
                indoor_np_fz100_bench_rehearsal=False,
            )
        )
        self.assertTrue(rep_sunny.passed)

        for lvl in (-2, -1, 0, 1, 2):
            rep_lvl = evaluate_touch_bench_vault_and_sunny_weather_guard(
                TouchBenchVaultAndSunnyWeatherSpec(
                    pre_reset_monitor_brightness_mode="Manual",
                    pre_reset_monitor_brightness_manual_level=lvl,
                    post_reset_monitor_brightness_mode="Manual",
                    post_reset_monitor_brightness_manual_level=lvl,
                    indoor_np_fz100_bench_rehearsal=False,
                )
            )
            self.assertTrue(rep_lvl.passed)

    def test_24_reject_monitor_brightness_wiped_by_camera_settings_reset_or_surviving_initialize(self) -> None:
        rep_csr = evaluate_touch_bench_vault_and_sunny_weather_guard(
            TouchBenchVaultAndSunnyWeatherSpec(
                pre_reset_monitor_brightness_mode="Sunny Weather",
                reset_action="Camera Settings Reset",
                post_reset_monitor_brightness_mode="Manual",
                indoor_np_fz100_bench_rehearsal=False,
            )
        )
        self.assertFalse(rep_csr.passed)
        self.assertEqual(rep_csr.block_code, P238_BLOCKED_MONITOR_BRIGHTNESS_RESET_PERSISTENCE_DRIFT)

        rep_init = evaluate_touch_bench_vault_and_sunny_weather_guard(
            TouchBenchVaultAndSunnyWeatherSpec(
                pre_reset_touch_operation="On",
                post_reset_touch_operation="On",
                capacitive_shooting_touch_blocked=False,
                capacitive_playback_touch_blocked=False,
                unattended_tier0_p3_vault_dump_active=False,
                pre_reset_monitor_brightness_mode="Sunny Weather",
                reset_action="Initialize",
                post_reset_monitor_brightness_mode="Sunny Weather",
                indoor_np_fz100_bench_rehearsal=False,
            )
        )
        self.assertFalse(rep_init.passed)
        self.assertEqual(rep_init.block_code, P238_BLOCKED_MONITOR_BRIGHTNESS_RESET_PERSISTENCE_DRIFT)

    def test_25_reject_indoor_np_fz100_bench_with_sunny_weather_or_nonzero_manual_boost(self) -> None:
        rep_sunny = evaluate_touch_bench_vault_and_sunny_weather_guard(
            TouchBenchVaultAndSunnyWeatherSpec(
                pre_reset_monitor_brightness_mode="Sunny Weather",
                post_reset_monitor_brightness_mode="Sunny Weather",
                indoor_np_fz100_bench_rehearsal=True,
                sunny_weather_indoor_exposure_skew_risk=True,
                sunny_weather_extra_np_fz100_drain_active=True,
            )
        )
        self.assertFalse(rep_sunny.passed)
        self.assertEqual(rep_sunny.block_code, P238_BLOCKED_INDOOR_BENCH_SUNNY_WEATHER_OR_BRIGHTNESS_DRIFT)

        rep_plus2 = evaluate_touch_bench_vault_and_sunny_weather_guard(
            TouchBenchVaultAndSunnyWeatherSpec(
                pre_reset_monitor_brightness_mode="Manual",
                pre_reset_monitor_brightness_manual_level=2,
                post_reset_monitor_brightness_mode="Manual",
                post_reset_monitor_brightness_manual_level=2,
                indoor_np_fz100_bench_rehearsal=True,
            )
        )
        self.assertFalse(rep_plus2.passed)
        self.assertEqual(rep_plus2.block_code, P238_BLOCKED_INDOOR_BENCH_SUNNY_WEATHER_OR_BRIGHTNESS_DRIFT)

    def test_26_reject_invalid_touch_or_brightness_tokens_and_wrong_p3_dump_size(self) -> None:
        for bad_kwargs in (
            {"camera_model": "ILME-FX6"},
            {"fw_version": "1.00"},
            {"pre_reset_touch_operation": "Auto"},
            {"pre_reset_monitor_brightness_manual_level": 3},
            {"tier0_p3_vault_dump_mib": 64, "unattended_tier0_p3_vault_dump_active": True},
        ):
            with self.subTest(bad_kwargs=bad_kwargs):
                rep = evaluate_touch_bench_vault_and_sunny_weather_guard(
                    TouchBenchVaultAndSunnyWeatherSpec(**bad_kwargs)
                )
                self.assertFalse(rep.passed)
                self.assertEqual(rep.block_code, P238_BLOCKED_INVALID_TOUCH_OR_BRIGHTNESS_SPEC)

    def test_27_reject_persistent_overlay_escape_h0_h3_drift_and_write_unlock_37a(self) -> None:
        rep_ov = evaluate_touch_bench_vault_and_sunny_weather_guard(
            TouchBenchVaultAndSunnyWeatherSpec(overlay_dir="/setting/touch_escape")
        )
        self.assertFalse(rep_ov.passed)
        self.assertEqual(rep_ov.block_code, P238_BLOCKED_PERSISTENT_OVERLAY_ESCAPE)

        rep_h = evaluate_touch_bench_vault_and_sunny_weather_guard(
            TouchBenchVaultAndSunnyWeatherSpec(tier0_surfaces_h0_h3_matched=15)
        )
        self.assertFalse(rep_h.passed)
        self.assertEqual(rep_h.block_code, P238_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT)

        rep_unlock = evaluate_touch_bench_vault_and_sunny_weather_guard(
            TouchBenchVaultAndSunnyWeatherSpec(persistent_write_unlock_requested=True)
        )
        self.assertFalse(rep_unlock.passed)
        self.assertEqual(rep_unlock.block_code, P238_BLOCKED_SAFETY_POLICY_VIOLATION)

    def test_28_pillar37a_6_scenario_suite_passes_all_6(self) -> None:
        res = run_pillar37a_touch_bench_sunny_weather_6_scenario_suite()
        self.assertTrue(res.passed)
        self.assertEqual(res.status, P238_STATUS_VERIFIED_PILLAR_37A)
        self.assertEqual(res.scenarios_passed, 6)
        self.assertEqual(res.scenarios_total, 6)
        self.assertEqual(tuple(s.scenario_id for s in res.scenarios), P238_PILLAR_37A_SCENARIO_IDS)


class TestPillar37BEmphasizedRecGridHdmiCleanFeedVault(unittest.TestCase):
    def test_29_default_safe_hdmi_only_clamps_hdmi_info_off_zero_baked_overlays_and_reset_split(self) -> None:
        spec = build_default_safe_recframe_grid_hdmi_vault_spec()
        rep = evaluate_emphasized_rec_grid_hdmi_clean_feed_vault(spec)
        self.assertTrue(rep.passed)
        self.assertEqual(rep.status, P238_STATUS_VERIFIED_PILLAR_37B)
        self.assertIsNone(rep.block_code)
        self.assertTrue(rep.recframe_vs_grid_reset_split_verified)
        self.assertTrue(rep.hdmi_clean_feed_auto_clamp_verified)
        self.assertTrue(rep.hdmi_info_routing_and_lcd_blank_verified)
        self.assertTrue(rep.local_only_assist_isolation_verified)
        self.assertTrue(rep.camset_slot1_restore_verified)
        self.assertTrue(rep.h0_equals_h3_verified)
        self.assertEqual(rep.tier0_surfaces_intact, 16)
        self.assertEqual(rep.physical_device_writes, 0)
        self.assertFalse(rep.persistent_emmc_writes_authorized)

    def test_30_hdmi_info_on_blanks_lcd_routes_emphasized_rec_and_grid_with_slot1_camset01_restore(self) -> None:
        rep = evaluate_emphasized_rec_grid_hdmi_clean_feed_vault(
            EmphasizedRecGridHdmiCleanFeedVaultSpec(
                shooting_mode="S&Q",
                recording_active=True,
                hdmi_connected=True,
                reset_action="Camera Settings Reset",
                camset_restore_after_reset=True,
                camset_slot=1,
                camset_filename="CAMSET01.DAT",
                saved_emphasized_rec_display="On",
                saved_grid_line_display="On",
                saved_grid_line_type="Diag. + Square Grid",
                saved_rec_media_dur_hdmi_output="On",
                saved_hdmi_raw_output="Off",
                saved_hdmi_info_display="On",
                post_reset_emphasized_rec_display="On",
                post_reset_grid_line_display="On",
                post_reset_grid_line_type="Diag. + Square Grid",
                post_reset_rec_media_dur_hdmi_output="On",
                post_reset_hdmi_raw_output="Off",
                post_reset_configured_hdmi_info_display="On",
                effective_hdmi_info_display="On",
                built_in_lcd_blanked=True,
                hdmi_red_rec_frame_routed=True,
                hdmi_grid_line_routed=True,
                hdmi_marker_zebra_peaking_leaked_layers=0,
                external_hdmi_master_baked_overlays=0,
            )
        )
        self.assertTrue(rep.passed)

    def test_31_hdmi_raw_movie_output_forces_hdmi_info_off_clean_feed_clamp(self) -> None:
        rep = evaluate_emphasized_rec_grid_hdmi_clean_feed_vault(
            EmphasizedRecGridHdmiCleanFeedVaultSpec(
                post_reset_rec_media_dur_hdmi_output="On",
                post_reset_hdmi_raw_output="On",
                post_reset_configured_hdmi_info_display="On",
                effective_hdmi_info_display="Off",
                built_in_lcd_blanked=False,
                hdmi_red_rec_frame_routed=False,
                hdmi_grid_line_routed=False,
                external_hdmi_master_baked_overlays=0,
            )
        )
        self.assertTrue(rep.passed)
        self.assertTrue(rep.hdmi_clean_feed_auto_clamp_verified)

    def test_32_emphasized_rec_reset_to_on_while_all_3_grid_types_survive_camera_settings_reset(self) -> None:
        for grid_type in P238_GRID_LINE_TYPES:
            with self.subTest(grid_type=grid_type):
                rep = evaluate_emphasized_rec_grid_hdmi_clean_feed_vault(
                    EmphasizedRecGridHdmiCleanFeedVaultSpec(
                        pre_reset_emphasized_rec_display="Off",
                        pre_reset_grid_line_display="On",
                        pre_reset_grid_line_type=grid_type,
                        reset_action="Camera Settings Reset",
                        post_reset_emphasized_rec_display="On",
                        post_reset_grid_line_display="On",
                        post_reset_grid_line_type=grid_type,
                    )
                )
                self.assertTrue(rep.passed)

    def test_33_initialize_resets_emphasized_rec_on_grid_off_and_rule_of_3rds(self) -> None:
        rep = evaluate_emphasized_rec_grid_hdmi_clean_feed_vault(
            EmphasizedRecGridHdmiCleanFeedVaultSpec(
                pre_reset_emphasized_rec_display="Off",
                pre_reset_grid_line_display="On",
                pre_reset_grid_line_type="Diag. + Square Grid",
                reset_action="Initialize",
                post_reset_emphasized_rec_display=P238_EMPHASIZED_REC_DEFAULT,
                post_reset_grid_line_display=P238_GRID_LINE_DISPLAY_DEFAULT,
                post_reset_grid_line_type=P238_GRID_LINE_TYPE_DEFAULT,
            )
        )
        self.assertTrue(rep.passed)

    def test_34_reject_emphasized_rec_not_reset_or_grid_line_wiped_by_camera_settings_reset(self) -> None:
        rep_rec = evaluate_emphasized_rec_grid_hdmi_clean_feed_vault(
            EmphasizedRecGridHdmiCleanFeedVaultSpec(
                pre_reset_emphasized_rec_display="Off",
                reset_action="Camera Settings Reset",
                post_reset_emphasized_rec_display="Off",
            )
        )
        self.assertFalse(rep_rec.passed)
        self.assertEqual(rep_rec.block_code, P238_BLOCKED_EMPHASIZED_REC_OR_GRID_RESET_SPLIT_DRIFT)

        rep_grid = evaluate_emphasized_rec_grid_hdmi_clean_feed_vault(
            EmphasizedRecGridHdmiCleanFeedVaultSpec(
                pre_reset_grid_line_display="On",
                pre_reset_grid_line_type="Square Grid",
                reset_action="Camera Settings Reset",
                post_reset_grid_line_display="Off",
                post_reset_grid_line_type="Rule of 3rds Grid",
            )
        )
        self.assertFalse(rep_grid.passed)
        self.assertEqual(rep_grid.block_code, P238_BLOCKED_EMPHASIZED_REC_OR_GRID_RESET_SPLIT_DRIFT)

    def test_35_reject_initialize_drift_or_none_action_drift_in_pillar37b(self) -> None:
        rep_init = evaluate_emphasized_rec_grid_hdmi_clean_feed_vault(
            EmphasizedRecGridHdmiCleanFeedVaultSpec(
                pre_reset_grid_line_display="On",
                reset_action="Initialize",
                post_reset_emphasized_rec_display="On",
                post_reset_grid_line_display="On",
            )
        )
        self.assertFalse(rep_init.passed)
        self.assertEqual(rep_init.block_code, P238_BLOCKED_EMPHASIZED_REC_OR_GRID_RESET_SPLIT_DRIFT)

        rep_none = evaluate_emphasized_rec_grid_hdmi_clean_feed_vault(
            EmphasizedRecGridHdmiCleanFeedVaultSpec(
                pre_reset_emphasized_rec_display="Off",
                reset_action="NONE",
                post_reset_emphasized_rec_display="On",
            )
        )
        self.assertFalse(rep_none.passed)
        self.assertEqual(rep_none.block_code, P238_BLOCKED_EMPHASIZED_REC_OR_GRID_RESET_SPLIT_DRIFT)

    def test_36_reject_hdmi_only_or_raw_output_failing_hdmi_info_off_clamp_or_baking_overlays(self) -> None:
        for clamp_kwargs in (
            {
                "post_reset_rec_media_dur_hdmi_output": "Off(HDMI Only)",
                "effective_hdmi_info_display": "On",
                "built_in_lcd_blanked": True,
                "hdmi_red_rec_frame_routed": True,
                "external_hdmi_master_baked_overlays": 1,
            },
            {
                "post_reset_rec_media_dur_hdmi_output": "On",
                "post_reset_hdmi_raw_output": "On",
                "effective_hdmi_info_display": "Off",
                "hdmi_grid_line_routed": True,
                "external_hdmi_master_baked_overlays": 1,
            },
        ):
            with self.subTest(clamp_kwargs=clamp_kwargs):
                rep = evaluate_emphasized_rec_grid_hdmi_clean_feed_vault(
                    EmphasizedRecGridHdmiCleanFeedVaultSpec(**clamp_kwargs)
                )
                self.assertFalse(rep.passed)
                self.assertEqual(rep.block_code, P238_BLOCKED_HDMI_ONLY_OR_RAW_CLEAN_FEED_CLAMP_VIOLATION)

    def test_37_reject_hdmi_info_on_without_lcd_blanking_or_mismatched_rec_grid_routing(self) -> None:
        rep_no_blank = evaluate_emphasized_rec_grid_hdmi_clean_feed_vault(
            EmphasizedRecGridHdmiCleanFeedVaultSpec(
                post_reset_rec_media_dur_hdmi_output="On",
                post_reset_hdmi_raw_output="Off",
                post_reset_configured_hdmi_info_display="On",
                effective_hdmi_info_display="On",
                built_in_lcd_blanked=False,
                hdmi_red_rec_frame_routed=True,
                hdmi_grid_line_routed=True,
            )
        )
        self.assertFalse(rep_no_blank.passed)
        self.assertEqual(rep_no_blank.block_code, P238_BLOCKED_HDMI_INFO_ROUTING_OR_LCD_BLANK_MISMATCH)

        rep_bad_route = evaluate_emphasized_rec_grid_hdmi_clean_feed_vault(
            EmphasizedRecGridHdmiCleanFeedVaultSpec(
                post_reset_rec_media_dur_hdmi_output="On",
                post_reset_hdmi_raw_output="Off",
                post_reset_configured_hdmi_info_display="On",
                effective_hdmi_info_display="On",
                built_in_lcd_blanked=True,
                hdmi_red_rec_frame_routed=False,
                hdmi_grid_line_routed=True,
            )
        )
        self.assertFalse(rep_bad_route.passed)
        self.assertEqual(rep_bad_route.block_code, P238_BLOCKED_HDMI_INFO_ROUTING_OR_LCD_BLANK_MISMATCH)

    def test_38_hdmi_info_off_keeps_lcd_active_and_routes_zero_rec_or_grid_to_hdmi(self) -> None:
        rep_ok = evaluate_emphasized_rec_grid_hdmi_clean_feed_vault(
            EmphasizedRecGridHdmiCleanFeedVaultSpec(
                post_reset_rec_media_dur_hdmi_output="On",
                post_reset_hdmi_raw_output="Off",
                post_reset_configured_hdmi_info_display="Off",
                effective_hdmi_info_display="Off",
                built_in_lcd_blanked=False,
                hdmi_red_rec_frame_routed=False,
                hdmi_grid_line_routed=False,
            )
        )
        self.assertTrue(rep_ok.passed)

        rep_bad = evaluate_emphasized_rec_grid_hdmi_clean_feed_vault(
            EmphasizedRecGridHdmiCleanFeedVaultSpec(
                post_reset_rec_media_dur_hdmi_output="On",
                post_reset_hdmi_raw_output="Off",
                post_reset_configured_hdmi_info_display="Off",
                effective_hdmi_info_display="Off",
                built_in_lcd_blanked=False,
                hdmi_red_rec_frame_routed=True,
                hdmi_grid_line_routed=False,
            )
        )
        self.assertFalse(rep_bad.passed)
        self.assertEqual(rep_bad.block_code, P238_BLOCKED_HDMI_INFO_ROUTING_OR_LCD_BLANK_MISMATCH)

    def test_39_reject_local_only_marker_zebra_peaking_leaking_onto_hdmi(self) -> None:
        rep = evaluate_emphasized_rec_grid_hdmi_clean_feed_vault(
            EmphasizedRecGridHdmiCleanFeedVaultSpec(hdmi_marker_zebra_peaking_leaked_layers=1)
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P238_BLOCKED_LOCAL_ONLY_ASSIST_HDMI_LEAKAGE)

    def test_40_camset01_to_camset10_slot1_restore_all_valid_and_reject_slot2_or_drift(self) -> None:
        for fname in P238_CAMSET_FILENAMES:
            rep = evaluate_emphasized_rec_grid_hdmi_clean_feed_vault(
                EmphasizedRecGridHdmiCleanFeedVaultSpec(
                    camset_restore_after_reset=True,
                    camset_slot=1,
                    camset_filename=fname,
                    saved_emphasized_rec_display="Off",
                    saved_grid_line_display="On",
                    saved_grid_line_type="Square Grid",
                    saved_rec_media_dur_hdmi_output="Off(HDMI Only)",
                    saved_hdmi_raw_output="Off",
                    saved_hdmi_info_display="On",
                    post_reset_emphasized_rec_display="Off",
                    post_reset_grid_line_display="On",
                    post_reset_grid_line_type="Square Grid",
                    post_reset_rec_media_dur_hdmi_output="Off(HDMI Only)",
                    post_reset_hdmi_raw_output="Off",
                    post_reset_configured_hdmi_info_display="On",
                    effective_hdmi_info_display="Off",
                )
            )
            self.assertTrue(rep.passed)

        rep_slot2 = evaluate_emphasized_rec_grid_hdmi_clean_feed_vault(
            EmphasizedRecGridHdmiCleanFeedVaultSpec(
                camset_restore_after_reset=True,
                camset_slot=2,
                camset_filename="CAMSET01.DAT",
            )
        )
        self.assertFalse(rep_slot2.passed)
        self.assertEqual(rep_slot2.block_code, P238_BLOCKED_CAMSET_SLOT1_RECFRAME_GRID_RESTORE_DRIFT)

        rep_drift = evaluate_emphasized_rec_grid_hdmi_clean_feed_vault(
            EmphasizedRecGridHdmiCleanFeedVaultSpec(
                camset_restore_after_reset=True,
                camset_slot=1,
                camset_filename="CAMSET01.DAT",
                saved_grid_line_type="Diag. + Square Grid",
                post_reset_grid_line_type="Square Grid",
            )
        )
        self.assertFalse(rep_drift.passed)
        self.assertEqual(rep_drift.block_code, P238_BLOCKED_CAMSET_SLOT1_RECFRAME_GRID_RESTORE_DRIFT)

    def test_41_reject_invalid_recframe_grid_hdmi_spec_overlay_escape_h0_h3_or_write_unlock_37b(self) -> None:
        rep_bad = evaluate_emphasized_rec_grid_hdmi_clean_feed_vault(
            EmphasizedRecGridHdmiCleanFeedVaultSpec(shooting_mode="Photo")
        )
        self.assertFalse(rep_bad.passed)
        self.assertEqual(rep_bad.block_code, P238_BLOCKED_INVALID_RECFRAME_GRID_OR_HDMI_SPEC)

        rep_ov = evaluate_emphasized_rec_grid_hdmi_clean_feed_vault(
            EmphasizedRecGridHdmiCleanFeedVaultSpec(stage_b_overlay_dir="/dev/cnflasha1")
        )
        self.assertFalse(rep_ov.passed)
        self.assertEqual(rep_ov.block_code, P238_BLOCKED_PERSISTENT_OVERLAY_ESCAPE)

        rep_h = evaluate_emphasized_rec_grid_hdmi_clean_feed_vault(
            EmphasizedRecGridHdmiCleanFeedVaultSpec(stage_b_backup_bin_writes=1)
        )
        self.assertFalse(rep_h.passed)
        self.assertEqual(rep_h.block_code, P238_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT)

        rep_unlock = evaluate_emphasized_rec_grid_hdmi_clean_feed_vault(
            EmphasizedRecGridHdmiCleanFeedVaultSpec(persistent_write_unlock_requested=True)
        )
        self.assertFalse(rep_unlock.passed)
        self.assertEqual(rep_unlock.block_code, P238_BLOCKED_SAFETY_POLICY_VIOLATION)

    def test_42_pillar37b_6_scenario_suite_passes_all_6(self) -> None:
        res = run_pillar37b_recframe_grid_hdmi_vault_6_scenario_suite()
        self.assertTrue(res.passed)
        self.assertEqual(res.status, P238_STATUS_VERIFIED_PILLAR_37B)
        self.assertEqual(res.scenarios_passed, 6)
        self.assertEqual(res.scenarios_total, 6)
        self.assertEqual(tuple(s.scenario_id for s in res.scenarios), P238_PILLAR_37B_SCENARIO_IDS)


class TestCombinedVerifierAndMaster37Aggregator(unittest.TestCase):
    def test_43_combined_verifier_default_and_clean_room_modes(self) -> None:
        rep_def = verify_touch_recframe_hdmi_and_sunny_weather_vault()
        rep_cr = verify_touch_recframe_hdmi_and_sunny_weather_vault(force_clean_room=True)
        for rep in (rep_def, rep_cr):
            self.assertTrue(rep.all_passed)
            self.assertTrue(rep.passed)
            self.assertEqual(rep.status, P238_STATUS_VERIFIED_PILLAR37_SUITE)
            self.assertTrue(rep.cnflasha_userspace_write_blocked)
            self.assertEqual(rep.otp_fuse_touches, 0)
            self.assertEqual(rep.rpmb_counter_increments, 0)
            self.assertEqual(rep.physical_device_writes, 0)
            self.assertFalse(rep.persistent_emmc_writes_authorized)
            self.assertEqual(rep.raw_firmware_bytes_leaked, 0)
        self.assertEqual(rep_cr.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_44_combined_verifier_propagates_37a_and_37b_failures(self) -> None:
        rep_a = verify_touch_recframe_hdmi_and_sunny_weather_vault(
            touch_sunny_spec=TouchBenchVaultAndSunnyWeatherSpec(accidental_fn_menu_opened_count=1),
            force_clean_room=True,
        )
        self.assertFalse(rep_a.all_passed)
        self.assertTrue(len(rep_a.errors) >= 1)

        rep_b = verify_touch_recframe_hdmi_and_sunny_weather_vault(
            recframe_grid_hdmi_spec=EmphasizedRecGridHdmiCleanFeedVaultSpec(
                hdmi_marker_zebra_peaking_leaked_layers=1
            ),
            force_clean_room=True,
        )
        self.assertFalse(rep_b.all_passed)
        self.assertTrue(len(rep_b.errors) >= 1)

    def test_45_standalone_pillar37_suite_default_and_clean_room(self) -> None:
        rep_def = run_pillar37_standalone_suite()
        rep_cr = run_pillar37_standalone_suite(force_clean_room=True)
        for rep in (rep_def, rep_cr):
            self.assertTrue(rep.all_passed)
            self.assertEqual(rep.schema, PHASE238_SCHEMA)
            self.assertEqual(rep.version, PHASE238_VERSION)
            self.assertEqual(rep.pillar_37a_touch_bench_sunny_weather_guard.scenarios_passed, 6)
            self.assertEqual(rep.pillar_37b_recframe_grid_hdmi_clean_feed_vault.scenarios_passed, 6)
            self.assertEqual(len(rep.suite_sha256), 64)
        self.assertEqual(rep_cr.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_46_master_37pillar_default_mode_37_of_37_under_6s(self) -> None:
        rep = evaluate_realhw_37pillar_recovery_master()
        self.assertTrue(rep.all_passed)
        self.assertEqual(rep.status, P238_STATUS_VERIFIED_37OF37_AGGREGATOR)
        self.assertEqual(rep.pillar_count, 37)
        self.assertEqual(rep.pillars_passed, 37)
        self.assertEqual(rep.failed_pillars, ())
        self.assertTrue(rep.under_6s_budget)
        self.assertTrue(rep.cnflasha_userspace_write_blocked)
        self.assertEqual(rep.otp_fuse_touches, 0)
        self.assertEqual(rep.rpmb_counter_increments, 0)
        self.assertEqual(rep.physical_device_writes, 0)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_47_master_37pillar_clean_room_deterministic_sha256(self) -> None:
        r1 = evaluate_realhw_37pillar_recovery_master(force_clean_room=True)
        r2 = evaluate_realhw_37pillar_recovery_master(force_clean_room=True)
        self.assertTrue(r1.all_passed)
        self.assertEqual(r1.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(r1.master_37pillar_sha256, r2.master_37pillar_sha256)
        self.assertEqual(len(r1.master_37pillar_sha256), 64)

    def test_48_master_37pillar_env_force_clean_room_invariants(self) -> None:
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            rep = evaluate_realhw_37pillar_recovery_master()
        self.assertTrue(rep.all_passed)
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(rep.pillar_count, 37)
        self.assertEqual(rep.pillars_passed, 37)
        self.assertTrue(rep.cnflasha_userspace_write_blocked)
        self.assertEqual(rep.otp_fuse_touches, 0)
        self.assertEqual(rep.rpmb_counter_increments, 0)
        self.assertEqual(rep.physical_device_writes, 0)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_49_master_37pillar_symmetry_aliases(self) -> None:
        r_alias = evaluate_37pillar_recovery_master(force_clean_room=True)
        r_cli = verify_37pillar_recovery_suite(force_clean_room=True)
        self.assertEqual(r_alias.master_37pillar_sha256, r_cli.master_37pillar_sha256)
        self.assertEqual(r_alias.pillars_passed, 37)

    def test_50_master_37pillar_fault_injection_pillar_37(self) -> None:
        rep = evaluate_realhw_37pillar_recovery_master(
            force_clean_room=True,
            fault_inject_pillar="pillar_37_touch_recframe_hdmi_sunny_vault",
        )
        self.assertFalse(rep.all_passed)
        self.assertEqual(rep.status, P238_STATUS_FAIL_37OF37_AGGREGATOR)
        self.assertEqual(rep.pillars_passed, 36)
        self.assertEqual(rep.failed_pillars, ("pillar_37_touch_recframe_hdmi_sunny_vault",))

    def test_51_master_37pillar_fault_injection_pillar_36(self) -> None:
        rep = evaluate_realhw_37pillar_recovery_master(
            force_clean_room=True,
            fault_inject_pillar="pillar_36_recover_imagedb_monitor_flip_af_vault",
        )
        self.assertFalse(rep.all_passed)
        self.assertEqual(rep.pillars_passed, 36)
        self.assertEqual(rep.failed_pillars, ("pillar_36_recover_imagedb_monitor_flip_af_vault",))

    def test_52_master_37pillar_fault_injection_pillar_1(self) -> None:
        first_id = MASTER_37_PILLAR_IDS[0]
        rep = evaluate_realhw_37pillar_recovery_master(
            force_clean_room=True,
            fault_inject_pillar=first_id,
        )
        self.assertFalse(rep.all_passed)
        self.assertEqual(rep.pillars_passed, 36)
        self.assertEqual(rep.failed_pillars, (first_id,))

    def test_53_master_37pillar_unknown_fault_inject_raises(self) -> None:
        with self.assertRaises(ValueError):
            evaluate_realhw_37pillar_recovery_master(
                force_clean_room=True,
                fault_inject_pillar="nonexistent_pillar_99",
            )

    def test_54_json_serialization_roundtrip_master_and_reports(self) -> None:
        rep = evaluate_realhw_37pillar_recovery_master(force_clean_room=True)
        encoded = json.dumps(rep.to_dict(), sort_keys=True, allow_nan=False)
        decoded = json.loads(encoded)
        self.assertEqual(decoded["status"], P238_STATUS_VERIFIED_37OF37_AGGREGATOR)
        self.assertEqual(decoded["pillar_count"], 37)
        self.assertEqual(decoded["pillars_passed"], 37)
        p37_comb = verify_touch_recframe_hdmi_and_sunny_weather_vault(force_clean_room=True)
        self.assertTrue(json.loads(json.dumps(p37_comb.to_dict(), sort_keys=True))["all_passed"])


class TestBackwardCompatibilityAndCli(unittest.TestCase):
    def test_55_backward_compatibility_with_36pillar_master(self) -> None:
        rep36 = fx3_recovery.evaluate_realhw_36pillar_recovery_master(force_clean_room=True)
        self.assertTrue(rep36.all_passed)
        self.assertEqual(rep36.pillar_count, 36)
        self.assertEqual(rep36.pillars_passed, 36)

    def test_56_backward_compatibility_with_35pillar_master(self) -> None:
        rep35 = fx3_recovery.evaluate_realhw_35pillar_recovery_master(force_clean_room=True)
        self.assertTrue(rep35.all_passed)
        self.assertEqual(rep35.pillar_count, 35)
        self.assertEqual(rep35.pillars_passed, 35)

    def test_57_backward_compatibility_across_22_to_34_pillar_masters(self) -> None:
        for count, fn in (
            (22, fx3_recovery.evaluate_22pillar_recovery_master),
            (24, fx3_recovery.evaluate_24pillar_recovery_master),
            (26, fx3_recovery.evaluate_26pillar_recovery_master),
            (27, fx3_recovery.evaluate_27pillar_recovery_master),
            (28, fx3_recovery.evaluate_28pillar_recovery_master),
            (29, fx3_recovery.evaluate_29pillar_recovery_master),
            (30, fx3_recovery.evaluate_realhw_30pillar_recovery_master),
            (31, fx3_recovery.evaluate_realhw_31pillar_recovery_master),
            (32, fx3_recovery.evaluate_realhw_32pillar_recovery_master),
            (33, fx3_recovery.evaluate_realhw_33pillar_recovery_master),
            (34, fx3_recovery.evaluate_realhw_34pillar_recovery_master),
        ):
            with self.subTest(pillars=count):
                rep = fn(force_clean_room=True)
                self.assertTrue(rep.all_passed)
                self.assertEqual(rep.pillar_count, count)

    def _run_cli(self, *cli_args: str, extra_env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ADAPTER_ROOT)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        if extra_env:
            env.update(extra_env)
        return subprocess.run(
            [sys.executable, "-B", "-m", "fx3_recovery", *cli_args],
            cwd=str(ADAPTER_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_58_cli_verify_touch_recframe_hdmi_sunny_vault_json(self) -> None:
        proc = self._run_cli("verify-touch-recframe-hdmi-sunny-vault", "--json")
        self.assertEqual(proc.returncode, 0, msg=proc.stderr or proc.stdout)
        data = json.loads(proc.stdout)
        self.assertTrue(data["all_passed"])
        self.assertEqual(data["status"], P238_STATUS_VERIFIED_PILLAR37_SUITE)
        self.assertTrue(data["cnflasha_userspace_write_blocked"])
        self.assertEqual(data["raw_firmware_bytes_leaked"], 0)

    def test_59_cli_verify_touch_recframe_hdmi_sunny_vault_clean_room_summary(self) -> None:
        proc = self._run_cli("verify-touch-recframe-hdmi-sunny-vault", "--clean-room")
        self.assertEqual(proc.returncode, 0, msg=proc.stderr or proc.stdout)
        self.assertIn("status=VERIFIED_PILLAR37_TOUCH_RECFRAME_HDMI_SUNNY_VAULT", proc.stdout)
        self.assertIn("mode=CLEAN_ROOM_SYNTHETIC", proc.stdout)
        self.assertIn("pillar_37a=6/6", proc.stdout)
        self.assertIn("pillar_37b=6/6", proc.stdout)

    def test_60_cli_verify_37pillar_recovery_normal_json(self) -> None:
        proc = self._run_cli("verify-37pillar-recovery", "--json")
        self.assertEqual(proc.returncode, 0, msg=proc.stderr or proc.stdout)
        data = json.loads(proc.stdout)
        self.assertTrue(data["all_passed"])
        self.assertEqual(data["status"], P238_STATUS_VERIFIED_37OF37_AGGREGATOR)
        self.assertEqual(data["pillar_count"], 37)
        self.assertEqual(data["pillars_passed"], 37)
        self.assertTrue(data["under_6s_budget"])

    def test_61_cli_verify_37pillar_recovery_normal_summary_line(self) -> None:
        proc = self._run_cli("verify-37pillar-recovery")
        self.assertEqual(proc.returncode, 0, msg=proc.stderr or proc.stdout)
        self.assertIn("status=VERIFIED_37OF37_PILLAR_RECOVERY_MASTER", proc.stdout)
        self.assertIn("pillars=37/37", proc.stdout)
        self.assertIn("pillar37_a=6/6", proc.stdout)
        self.assertIn("pillar37_b=6/6", proc.stdout)

    def test_62_cli_verify_37pillar_recovery_clean_room_env_and_flag(self) -> None:
        proc = self._run_cli(
            "verify-37pillar-recovery",
            "--force-clean-room",
            "--json",
            extra_env={"FX3_FX6_FORCE_CLEAN_ROOM": "1"},
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr or proc.stdout)
        data = json.loads(proc.stdout)
        self.assertEqual(data["verification_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(data["pillars_passed"], 37)

    def test_63_cli_verify_37pillar_recovery_out_directory_and_overwrite_guard(self) -> None:
        here = Path(__file__).resolve().parent
        out_dir = here / f"_tmp_p238_m37_{os.getpid()}"
        p37_dir = here / f"_tmp_p238_p37_{os.getpid()}"
        _cleanup_exclusive_out_dir(out_dir, ("37pillar-recovery-master-report.json",))
        _cleanup_exclusive_out_dir(p37_dir, ("pillar37-touch-recframe-hdmi-sunny-vault-report.json",))
        try:
            proc = self._run_cli("verify-37pillar-recovery", "--clean-room", "--out", str(out_dir))
            self.assertEqual(proc.returncode, 0, msg=proc.stderr or proc.stdout)
            report_file = out_dir / "37pillar-recovery-master-report.json"
            self.assertTrue(report_file.is_file())
            saved = json.loads(report_file.read_text(encoding="utf-8"))
            self.assertEqual(saved["status"], P238_STATUS_VERIFIED_37OF37_AGGREGATOR)
            self.assertEqual(saved["pillars_passed"], 37)

            proc_dup = self._run_cli("verify-37pillar-recovery", "--clean-room", "--out", str(out_dir))
            self.assertEqual(proc_dup.returncode, 2)

            proc_p37 = self._run_cli(
                "verify-touch-recframe-hdmi-sunny-vault",
                "--clean-room",
                "--out",
                str(p37_dir),
            )
            self.assertEqual(proc_p37.returncode, 0, msg=proc_p37.stderr or proc_p37.stdout)
            self.assertTrue((p37_dir / "pillar37-touch-recframe-hdmi-sunny-vault-report.json").is_file())
        finally:
            _cleanup_exclusive_out_dir(out_dir, ("37pillar-recovery-master-report.json",))
            _cleanup_exclusive_out_dir(p37_dir, ("pillar37-touch-recframe-hdmi-sunny-vault-report.json",))

    def test_64_safety_invariant_tamper_detected_and_subreports_to_dict(self) -> None:
        with mock.patch.object(p238, "PERSISTENT_EMMC_WRITES_AUTHORIZED", True):
            errs = p238._safety_invariant_errors()
            self.assertTrue(any("PERSISTENT_EMMC_WRITES_AUTHORIZED" in e for e in errs))
            rep37a = evaluate_touch_bench_vault_and_sunny_weather_guard(TouchBenchVaultAndSunnyWeatherSpec())
            self.assertFalse(rep37a.passed)
            self.assertEqual(rep37a.block_code, P238_BLOCKED_SAFETY_POLICY_VIOLATION)

        rep_a = evaluate_touch_bench_vault_and_sunny_weather_guard(TouchBenchVaultAndSunnyWeatherSpec())
        rep_b = evaluate_emphasized_rec_grid_hdmi_clean_feed_vault(EmphasizedRecGridHdmiCleanFeedVaultSpec())
        self.assertTrue(json.loads(json.dumps(rep_a.to_dict()))["passed"])
        self.assertTrue(json.loads(json.dumps(rep_b.to_dict()))["passed"])


if __name__ == "__main__":
    unittest.main()
