"""Phase 231 — Dual-mode unit tests for Milestone Pillar 35 (`[Silent Mode]` `[Auto Pixel Mapping]`
bench shutdown firewall, 5-function lockout & `ILME-FX3` `[Shutter When Pwr OFF]` absence;
`[Marker Display]` 15-ratio `[Camera Settings Reset]` survival, local-LCD HDMI marker suppression &
`[Flexible Exp. Mode]` `Av/Tv/ISO` + `[Auto Slow Shutter]` reset-split / Slot-1 `CAMSET01.DAT` vault)
and unified `35/35` recovery master (`verify-35pillar-recovery`)."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

import fx3_recovery
from fx3_recovery import realhw_35pillar_silent_autopixelmap_marker_vault_verifier as p231
from fx3_recovery.realhw_35pillar_silent_autopixelmap_marker_vault_verifier import (
    ALLOW_BOOT_PARTITION_TARGETING,
    ALLOW_DESTRUCTIVE_FASTBOOT,
    ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS,
    ALLOW_PERSISTENT_JIRITSU_WRITES,
    CNFLASHA_USERSPACE_WRITE_BLOCKED,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    ISP_WRITE_AUTHORIZED,
    LIVE_USB_IOKIT_TRANSMIT_ENABLED,
    MASTER_35_PILLAR_COUNT,
    MASTER_35_PILLAR_IDS,
    MASTER_35_PILLAR_SPECS,
    OTP_FUSE_TOUCHES,
    OTP_FUSE_WRITES,
    P231_APERTURE_DRIVE_IN_AF_MODES,
    P231_ASPECT_MARKER_15_RATIOS,
    P231_ASPECT_MARKER_MODES,
    P231_BLOCKED_BENCH_SHUTDOWN_UNSUPPRESSED_AUTO_PIXELMAP,
    P231_BLOCKED_CAMSET_SLOT1_FLEXEXP_RESTORE_DRIFT,
    P231_BLOCKED_CNFLASHA_DEFECT_TABLE_TOUCH_ON_SHUTDOWN,
    P231_BLOCKED_FABRICATED_SHUTTER_WHEN_PWR_OFF_ON_FX3,
    P231_BLOCKED_FLEXEXP_OR_AUTOSLOWSHUTTER_RESET_SPLIT_DRIFT,
    P231_BLOCKED_HDMI_MARKER_OVERLAY_LEAKAGE,
    P231_BLOCKED_INVALID_MARKER_OR_FLEXEXP_SPEC,
    P231_BLOCKED_INVALID_SILENT_OR_PIXELMAP_SPEC,
    P231_BLOCKED_MARKER_CAMERA_SETTINGS_RESET_DRIFT,
    P231_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
    P231_BLOCKED_SAFETY_POLICY_VIOLATION,
    P231_BLOCKED_SILENT_MODE_SHUTTER_AUDIO_OR_5FUNC_LOCKOUT_VIOLATION,
    P231_BLOCKED_TARGET_FUNCTION_SETTINGS_SEMANTIC_DRIFT,
    P231_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
    P231_CAMSET_FILENAMES,
    P231_EXPOSURE_CTRL_TYPES,
    P231_FX3_PRE_300_FW_VERSIONS,
    P231_FX3_SETUP_SENSOR_MENU_ITEMS,
    P231_FX3_SUPPORTED_FW_VERSIONS,
    P231_PASM_SUBMODES,
    P231_SAFETY_ZONE_MODES,
    P231_SILENT_5_DISQUALIFIED_FUNCTIONS,
    P231_STATUS_FAIL_35OF35_AGGREGATOR,
    P231_STATUS_VERIFIED_35OF35_AGGREGATOR,
    P231_STATUS_VERIFIED_PILLAR35_SUITE,
    P231_STATUS_VERIFIED_PILLAR_35A,
    P231_STATUS_VERIFIED_PILLAR_35B,
    P231_TARGET_FUNCTION_ITEMS,
    PASSIVE_TX_BYTES_EMITTED,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHASE231_SCHEMA,
    PHASE231_VERSION,
    PHYSICAL_DEVICE_WRITES,
    PHYSICAL_USB_PACKETS_EMITTED,
    RAW_FIRMWARE_BYTES_LEAKED,
    READ_ONLY_DONOR_ACCESS,
    RPMB_COUNTER_INCREMENTS,
    SPI_NOR_WRITE_AUTHORIZED,
    MarkerPersistenceAndFlexExpVaultSpec,
    SilentModeAutoPixelMapBenchFirewallSpec,
    build_default_safe_marker_flexexp_vault_spec,
    build_default_safe_silent_autopixelmap_spec,
    evaluate_35pillar_recovery_master,
    evaluate_marker_persistence_hdmi_and_flexexp_vault,
    evaluate_realhw_35pillar_recovery_master,
    evaluate_silent_mode_autopixelmap_bench_firewall,
    inspect_phase231_donors_readonly,
    run_pillar35_standalone_suite,
    run_pillar35a_silent_autopixelmap_bench_6_scenario_suite,
    run_pillar35b_marker_hdmi_flexexp_vault_6_scenario_suite,
    verify_35pillar_recovery_suite,
    verify_silent_autopixelmap_and_marker_flexexp_vault,
)

ADAPTER_ROOT = Path(__file__).resolve().parents[1]


class TestPhase231SafetyAndExports(unittest.TestCase):
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
            "realhw_35pillar_silent_autopixelmap_marker_vault_verifier",
            "MASTER_35_PILLAR_COUNT",
            "MASTER_35_PILLAR_IDS",
            "MASTER_35_PILLAR_SPECS",
            "PHASE231_SCHEMA",
            "PHASE231_VERSION",
            "verify_silent_autopixelmap_and_marker_flexexp_vault",
            "evaluate_realhw_35pillar_recovery_master",
            "evaluate_35pillar_recovery_master",
            "verify_35pillar_recovery_suite",
            "run_pillar35_standalone_suite",
        ):
            self.assertIn(sym, fx3_recovery.__all__)
            self.assertTrue(hasattr(fx3_recovery, sym))
        self.assertEqual(fx3_recovery.MASTER_34_PILLAR_COUNT, 34)
        self.assertEqual(fx3_recovery.MASTER_35_PILLAR_COUNT, 35)

    def test_03_master_35_pillar_registry_extends_34(self) -> None:
        self.assertEqual(MASTER_35_PILLAR_COUNT, 35)
        self.assertEqual(len(MASTER_35_PILLAR_SPECS), 35)
        self.assertEqual(len(MASTER_35_PILLAR_IDS), 35)
        self.assertEqual(len(set(MASTER_35_PILLAR_IDS)), 35)
        self.assertEqual([s[0] for s in MASTER_35_PILLAR_SPECS], list(range(1, 36)))
        self.assertEqual(MASTER_35_PILLAR_SPECS[:34], fx3_recovery.MASTER_34_PILLAR_SPECS)
        self.assertEqual(
            MASTER_35_PILLAR_SPECS[34],
            (
                35,
                "pillar_35_silent_autopixelmap_marker_flexexp_vault",
                "Phase 231",
                "fx3_recovery.realhw_35pillar_silent_autopixelmap_marker_vault_verifier",
            ),
        )

    def test_04_wave33_silent_marker_15ratios_and_flexexp_constants(self) -> None:
        self.assertEqual(P231_FX3_SETUP_SENSOR_MENU_ITEMS, ("Sensor Cleaning", "Auto Pixel Mapping", "Pixel Mapping"))
        self.assertNotIn("Shutter When Pwr OFF", P231_FX3_SETUP_SENSOR_MENU_ITEMS)
        self.assertEqual(P231_TARGET_FUNCTION_ITEMS, ("Aperture Drive in AF", "Auto Pixel Mapping"))
        self.assertEqual(len(P231_SILENT_5_DISQUALIFIED_FUNCTIONS), 5)
        self.assertEqual(len(P231_ASPECT_MARKER_15_RATIOS), 15)
        self.assertEqual(len(P231_ASPECT_MARKER_MODES), 16)
        self.assertIn("16:9", P231_ASPECT_MARKER_15_RATIOS)
        self.assertIn("2.39:1", P231_ASPECT_MARKER_15_RATIOS)
        self.assertEqual(P231_SAFETY_ZONE_MODES, ("Off", "80%", "90%"))
        self.assertEqual(P231_EXPOSURE_CTRL_TYPES, ("P/A/S/M Mode", "Flexible Exp. Mode"))
        self.assertEqual(len(P231_PASM_SUBMODES), 4)
        self.assertEqual(len(P231_CAMSET_FILENAMES), 10)


class TestPhase231ReadOnlyDonorInspection(unittest.TestCase):
    def test_05_donor_inspect_default_mode_under_budget(self) -> None:
        snap = inspect_phase231_donors_readonly()
        self.assertIn(snap.verification_mode, ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"))
        self.assertTrue(snap.all_donors_present)
        self.assertEqual(snap.donor_files_inspected, 7)
        self.assertTrue(snap.under_0_15s_budget)
        self.assertEqual(snap.raw_firmware_bytes_leaked, 0)
        for art in snap.artifacts:
            self.assertTrue(art.present)
            self.assertTrue(art.matches_pinned)
            self.assertEqual(len(art.digest_sha256), 64)

    def test_06_donor_inspect_force_clean_room_true(self) -> None:
        snap = inspect_phase231_donors_readonly(force_clean_room=True)
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(snap.all_donors_present)
        self.assertEqual(snap.donor_files_inspected, 7)
        for art in snap.artifacts:
            self.assertEqual(art.read_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertTrue(art.matches_pinned)

    def test_07_donor_inspect_env_force_clean_room(self) -> None:
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            snap = inspect_phase231_donors_readonly()
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(snap.all_donors_present)

    def test_08_donor_inspect_uses_strictly_o_rdonly_flags_and_ondemand_saver_symbols(self) -> None:
        seen_flags: list[int] = []
        real_open = os.open

        def spy_open(path: str, flags: int, *args: object) -> int:
            seen_flags.append(flags)
            return real_open(path, flags, *args)  # type: ignore[arg-type]

        with mock.patch("os.open", side_effect=spy_open):
            snap = inspect_phase231_donors_readonly()
        for fl in seen_flags:
            self.assertEqual(fl & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC), 0)
        if snap.verification_mode == "LOCAL_DONOR_O_RDONLY":
            self.assertEqual(len(seen_flags), 7)
            saver_art = [a for a in snap.artifacts if a.artifact_id == "fx3_camera_ondemand_saver_so"][0]
            self.assertIn("cam_ondemand_saver_init", saver_art.marker_summary)
            self.assertIn("cam_ondemand_saver_thread", saver_art.marker_summary)
            self.assertIn("cam_ondemand_saver_exit", saver_art.marker_summary)

    def test_09_donor_inspect_missing_donor_falls_back_to_clean_room(self) -> None:
        with mock.patch.object(p231, "resolve_donor_path", return_value=None):
            snap = inspect_phase231_donors_readonly(force_clean_room=False)
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(snap.all_donors_present)


class TestPillar35ASilentModeAutoPixelMapBenchFirewall(unittest.TestCase):
    def test_10_default_safe_silent_autopixelmap_bench_shutdown_firewall_passes(self) -> None:
        spec = build_default_safe_silent_autopixelmap_spec()
        rep = evaluate_silent_mode_autopixelmap_bench_firewall(spec)
        self.assertTrue(rep.passed)
        self.assertEqual(rep.status, P231_STATUS_VERIFIED_PILLAR_35A)
        self.assertIsNone(rep.block_code)
        self.assertTrue(rep.bench_shutdown_firewall_verified)
        self.assertTrue(rep.silent_5_function_lockout_verified)
        self.assertTrue(rep.shutter_when_pwr_off_absent_verified)
        self.assertTrue(rep.cnflasha_zero_touch_verified)
        self.assertTrue(rep.h0_equals_h3_verified)
        self.assertEqual(rep.physical_device_writes, 0)
        self.assertFalse(rep.persistent_emmc_writes_authorized)

    def test_11_silent_on_not_target_retains_normal_autopixelmap_and_aperture_outside_bench(self) -> None:
        for ap_mode in P231_APERTURE_DRIVE_IN_AF_MODES:
            with self.subTest(aperture_drive=ap_mode):
                rep = evaluate_silent_mode_autopixelmap_bench_firewall(
                    SilentModeAutoPixelMapBenchFirewallSpec(
                        silent_mode="On",
                        aperture_drive_in_af_target="Not Target",
                        auto_pixel_mapping_target="Not Target",
                        aperture_drive_in_af_setting=ap_mode,
                        auto_pixel_mapping_setting="On",
                        effective_auto_pixel_mapping_retained=True,
                        effective_aperture_drive_retained=True,
                        tier0_bench_shutdown_cycle_active=False,
                        poweroff_mechanical_pixelmap_suppressed=False,
                    )
                )
                self.assertTrue(rep.passed)
                self.assertTrue(rep.bench_shutdown_firewall_verified)

    def test_12_silent_off_outside_bench_allows_normal_shutter_audio_and_5_functions(self) -> None:
        rep = evaluate_silent_mode_autopixelmap_bench_firewall(
            SilentModeAutoPixelMapBenchFirewallSpec(
                silent_mode="Off",
                aperture_drive_in_af_target="Target",
                auto_pixel_mapping_target="Target",
                auto_pixel_mapping_setting="On",
                effective_auto_pixel_mapping_retained=True,
                effective_aperture_drive_retained=True,
                shutter_type="Mechanical Shutter",
                shutter_type_in_interval="Auto",
                audio_signals="On: all",
                flash_shooting_enabled=True,
                long_exposure_nr_enabled=True,
                e_front_curtain_shutter_enabled=True,
                bulb_shooting_enabled=True,
                anti_flicker_shoot_enabled=True,
                tier0_bench_shutdown_cycle_active=False,
                poweroff_mechanical_pixelmap_suppressed=False,
            )
        )
        self.assertTrue(rep.passed)

    def test_13_bench_shutdown_with_autopixelmap_off_and_silent_off_passes_zero_actuation(self) -> None:
        rep = evaluate_silent_mode_autopixelmap_bench_firewall(
            SilentModeAutoPixelMapBenchFirewallSpec(
                silent_mode="Off",
                auto_pixel_mapping_setting="Off",
                effective_auto_pixel_mapping_retained=True,
                effective_aperture_drive_retained=True,
                shutter_type="Auto",
                shutter_type_in_interval="Auto",
                audio_signals="On: all",
                tier0_bench_shutdown_cycle_active=True,
                poweroff_mechanical_pixelmap_suppressed=True,
                poweroff_mechanical_shutter_actuated=False,
            )
        )
        self.assertTrue(rep.passed)

    def test_14_bench_shutdown_with_autopixelmap_on_and_not_target_blocked(self) -> None:
        rep = evaluate_silent_mode_autopixelmap_bench_firewall(
            SilentModeAutoPixelMapBenchFirewallSpec(
                silent_mode="On",
                auto_pixel_mapping_target="Not Target",
                auto_pixel_mapping_setting="On",
                effective_auto_pixel_mapping_retained=True,
                tier0_bench_shutdown_cycle_active=True,
                poweroff_mechanical_pixelmap_suppressed=False,
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P231_BLOCKED_BENCH_SHUTDOWN_UNSUPPRESSED_AUTO_PIXELMAP)

    def test_15_bench_shutdown_with_silent_off_and_autopixelmap_on_blocked(self) -> None:
        rep = evaluate_silent_mode_autopixelmap_bench_firewall(
            SilentModeAutoPixelMapBenchFirewallSpec(
                silent_mode="Off",
                auto_pixel_mapping_target="Target",
                auto_pixel_mapping_setting="On",
                effective_auto_pixel_mapping_retained=True,
                effective_aperture_drive_retained=True,
                tier0_bench_shutdown_cycle_active=True,
                poweroff_mechanical_pixelmap_suppressed=False,
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P231_BLOCKED_BENCH_SHUTDOWN_UNSUPPRESSED_AUTO_PIXELMAP)

    def test_16_bench_shutdown_mechanical_shutter_actuated_blocked(self) -> None:
        rep = evaluate_silent_mode_autopixelmap_bench_firewall(
            SilentModeAutoPixelMapBenchFirewallSpec(poweroff_mechanical_shutter_actuated=True)
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P231_BLOCKED_BENCH_SHUTDOWN_UNSUPPRESSED_AUTO_PIXELMAP)

    def test_17_silent_mode_on_shutter_type_and_interval_lockout_enforced(self) -> None:
        for bad_kw in (
            {"shutter_type": "Mechanical Shutter"},
            {"shutter_type": "Auto"},
            {"shutter_type_in_interval": "Mechanical Shutter"},
            {"shutter_type_in_interval": "Auto"},
        ):
            with self.subTest(bad_kw=bad_kw):
                rep = evaluate_silent_mode_autopixelmap_bench_firewall(
                    SilentModeAutoPixelMapBenchFirewallSpec(**bad_kw)
                )
                self.assertFalse(rep.passed)
                self.assertEqual(
                    rep.block_code,
                    P231_BLOCKED_SILENT_MODE_SHUTTER_AUDIO_OR_5FUNC_LOCKOUT_VIOLATION,
                )

    def test_18_silent_mode_on_audio_signals_lockout_enforced(self) -> None:
        for sig in ("On: all", "On: shutter only", "On: other than shutter"):
            with self.subTest(audio_signals=sig):
                rep = evaluate_silent_mode_autopixelmap_bench_firewall(
                    SilentModeAutoPixelMapBenchFirewallSpec(audio_signals=sig)
                )
                self.assertFalse(rep.passed)
                self.assertEqual(
                    rep.block_code,
                    P231_BLOCKED_SILENT_MODE_SHUTTER_AUDIO_OR_5FUNC_LOCKOUT_VIOLATION,
                )

    def test_19_silent_mode_on_each_of_5_disqualified_functions_blocked(self) -> None:
        for field_name in (
            "flash_shooting_enabled",
            "long_exposure_nr_enabled",
            "e_front_curtain_shutter_enabled",
            "bulb_shooting_enabled",
            "anti_flicker_shoot_enabled",
        ):
            with self.subTest(disqualified_function=field_name):
                rep = evaluate_silent_mode_autopixelmap_bench_firewall(
                    SilentModeAutoPixelMapBenchFirewallSpec(**{field_name: True})
                )
                self.assertFalse(rep.passed)
                self.assertEqual(
                    rep.block_code,
                    P231_BLOCKED_SILENT_MODE_SHUTTER_AUDIO_OR_5FUNC_LOCKOUT_VIOLATION,
                )

    def test_20_shutter_when_pwr_off_rejected_across_all_fx3_fw_versions_200_to_702(self) -> None:
        for fw in P231_FX3_SUPPORTED_FW_VERSIONS:
            with self.subTest(fw_version=fw):
                ok_rep = evaluate_silent_mode_autopixelmap_bench_firewall(
                    SilentModeAutoPixelMapBenchFirewallSpec(fw_version=fw)
                )
                self.assertTrue(ok_rep.passed)

                bad_rep = evaluate_silent_mode_autopixelmap_bench_firewall(
                    SilentModeAutoPixelMapBenchFirewallSpec(
                        fw_version=fw,
                        shutter_when_pwr_off_menu_present=True,
                        shutter_when_pwr_off_setting="On",
                    )
                )
                self.assertFalse(bad_rep.passed)
                self.assertEqual(bad_rep.block_code, P231_BLOCKED_FABRICATED_SHUTTER_WHEN_PWR_OFF_ON_FX3)

    def test_21_shutter_when_pwr_off_injected_into_setup_or_target_menus_blocked(self) -> None:
        for kw in (
            {"setup_sensor_menu_items": ("Sensor Cleaning", "Shutter When Pwr OFF")},
            {"target_function_menu_items": ("Aperture Drive in AF", "Auto Pixel Mapping", "Shutter When Pwr OFF")},
            {"shutter_when_pwr_off_setting": "Off"},
        ):
            with self.subTest(kw=kw):
                rep = evaluate_silent_mode_autopixelmap_bench_firewall(
                    SilentModeAutoPixelMapBenchFirewallSpec(**kw)
                )
                self.assertFalse(rep.passed)
                self.assertEqual(rep.block_code, P231_BLOCKED_FABRICATED_SHUTTER_WHEN_PWR_OFF_ON_FX3)

    def test_22_target_function_settings_semantic_drift_blocked(self) -> None:
        for kw in (
            {"effective_auto_pixel_mapping_retained": True},
            {"effective_aperture_drive_retained": True},
            {
                "tier0_bench_shutdown_cycle_active": False,
                "auto_pixel_mapping_target": "Not Target",
                "effective_auto_pixel_mapping_retained": False,
                "poweroff_mechanical_pixelmap_suppressed": False,
            },
            {
                "tier0_bench_shutdown_cycle_active": False,
                "poweroff_mechanical_shutter_actuated": True,
            },
        ):
            with self.subTest(kw=kw):
                rep = evaluate_silent_mode_autopixelmap_bench_firewall(
                    SilentModeAutoPixelMapBenchFirewallSpec(**kw)
                )
                self.assertFalse(rep.passed)
                self.assertEqual(rep.block_code, P231_BLOCKED_TARGET_FUNCTION_SETTINGS_SEMANTIC_DRIFT)

    def test_23_uncommanded_cnflasha_calibration_touch_or_write_attempt_blocked(self) -> None:
        for kw in (
            {"poweroff_cnflasha_calibration_touches": 1},
            {"cnflasha_defect_table_write_attempted": True},
        ):
            with self.subTest(kw=kw):
                rep = evaluate_silent_mode_autopixelmap_bench_firewall(
                    SilentModeAutoPixelMapBenchFirewallSpec(**kw)
                )
                self.assertFalse(rep.passed)
                self.assertEqual(rep.block_code, P231_BLOCKED_CNFLASHA_DEFECT_TABLE_TOUCH_ON_SHUTDOWN)
                self.assertFalse(rep.cnflasha_zero_touch_verified)

    def test_24_pillar35a_invalid_model_fw_menu_overlay_h0h3_or_unlock_blocked(self) -> None:
        self.assertEqual(
            evaluate_silent_mode_autopixelmap_bench_firewall(
                SilentModeAutoPixelMapBenchFirewallSpec(camera_model="ILCE-7SM3")
            ).block_code,
            P231_BLOCKED_INVALID_SILENT_OR_PIXELMAP_SPEC,
        )
        self.assertEqual(
            evaluate_silent_mode_autopixelmap_bench_firewall(
                SilentModeAutoPixelMapBenchFirewallSpec(fw_version="1.00")
            ).block_code,
            P231_BLOCKED_INVALID_SILENT_OR_PIXELMAP_SPEC,
        )
        self.assertEqual(
            evaluate_silent_mode_autopixelmap_bench_firewall(
                SilentModeAutoPixelMapBenchFirewallSpec(setup_sensor_menu_items=("Unknown Item",))
            ).block_code,
            P231_BLOCKED_INVALID_SILENT_OR_PIXELMAP_SPEC,
        )
        self.assertEqual(
            evaluate_silent_mode_autopixelmap_bench_firewall(
                SilentModeAutoPixelMapBenchFirewallSpec(overlay_dir="/setting/silent_overlay")
            ).block_code,
            P231_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
        )
        self.assertEqual(
            evaluate_silent_mode_autopixelmap_bench_firewall(
                SilentModeAutoPixelMapBenchFirewallSpec(stage_b_backup_bin_writes=1)
            ).block_code,
            P231_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
        )
        self.assertEqual(
            evaluate_silent_mode_autopixelmap_bench_firewall(
                SilentModeAutoPixelMapBenchFirewallSpec(persistent_write_unlock_requested=True)
            ).block_code,
            P231_BLOCKED_SAFETY_POLICY_VIOLATION,
        )

    def test_25_pillar35a_6_scenario_suite_all_pass(self) -> None:
        res = run_pillar35a_silent_autopixelmap_bench_6_scenario_suite()
        self.assertTrue(res.passed)
        self.assertEqual(res.status, P231_STATUS_VERIFIED_PILLAR_35A)
        self.assertEqual(res.scenarios_passed, 6)
        self.assertEqual(res.scenarios_total, 6)


class TestPillar35BMarker15RatioHdmiIsolationAndFlexExpResetSplit(unittest.TestCase):
    def test_26_default_safe_marker_survival_hdmi_isolation_and_flexexp_reset_split_passes(self) -> None:
        spec = build_default_safe_marker_flexexp_vault_spec()
        rep = evaluate_marker_persistence_hdmi_and_flexexp_vault(spec)
        self.assertTrue(rep.passed)
        self.assertEqual(rep.status, P231_STATUS_VERIFIED_PILLAR_35B)
        self.assertIsNone(rep.block_code)
        self.assertTrue(rep.marker_reset_persistence_verified)
        self.assertTrue(rep.hdmi_marker_zero_leak_verified)
        self.assertTrue(rep.flexexp_reset_split_verified)
        self.assertTrue(rep.camset_slot1_restore_verified)
        self.assertTrue(rep.h0_equals_h3_verified)
        self.assertEqual(rep.tier0_surfaces_intact, 16)

    def test_27_all_15_aspect_marker_ratios_and_off_survive_camera_settings_reset_on_ver702(self) -> None:
        for aspect in P231_ASPECT_MARKER_MODES:
            for sz in P231_SAFETY_ZONE_MODES:
                with self.subTest(aspect_marker=aspect, safety_zone=sz):
                    sub_on = aspect != "Off" or sz != "Off"
                    rep = evaluate_marker_persistence_hdmi_and_flexexp_vault(
                        MarkerPersistenceAndFlexExpVaultSpec(
                            pre_reset_marker_display="On",
                            pre_reset_center_marker="Off",
                            pre_reset_aspect_marker=aspect,
                            pre_reset_safety_zone=sz,
                            pre_reset_guideframe="Off",
                            reset_action="Camera Settings Reset",
                            post_reset_marker_display="On",
                            post_reset_center_marker="Off",
                            post_reset_aspect_marker=aspect,
                            post_reset_safety_zone=sz,
                            post_reset_guideframe="Off",
                            lcd_markers_rendered=sub_on,
                        )
                    )
                    self.assertTrue(rep.passed)

    def test_28_aspect_marker_16_9_requires_ver_300_or_newer(self) -> None:
        for pre300_fw in P231_FX3_PRE_300_FW_VERSIONS:
            with self.subTest(fw_version=pre300_fw):
                rep = evaluate_marker_persistence_hdmi_and_flexexp_vault(
                    MarkerPersistenceAndFlexExpVaultSpec(
                        fw_version=pre300_fw,
                        pre_reset_aspect_marker="16:9",
                        post_reset_aspect_marker="16:9",
                    )
                )
                self.assertFalse(rep.passed)
                self.assertEqual(rep.block_code, P231_BLOCKED_INVALID_MARKER_OR_FLEXEXP_SPEC)
        rep_300 = evaluate_marker_persistence_hdmi_and_flexexp_vault(
            MarkerPersistenceAndFlexExpVaultSpec(
                fw_version="3.00",
                pre_reset_aspect_marker="16:9",
                post_reset_aspect_marker="16:9",
            )
        )
        self.assertTrue(rep_300.passed)

    def test_29_marker_wiped_or_drifted_across_camera_settings_reset_blocked(self) -> None:
        for kw in (
            {"post_reset_marker_display": "Off", "lcd_markers_rendered": False},
            {"post_reset_center_marker": "Off"},
            {"post_reset_aspect_marker": "4:3"},
            {"post_reset_safety_zone": "80%"},
            {"post_reset_guideframe": "Off"},
        ):
            with self.subTest(kw=kw):
                rep = evaluate_marker_persistence_hdmi_and_flexexp_vault(
                    MarkerPersistenceAndFlexExpVaultSpec(**kw)
                )
                self.assertFalse(rep.passed)
                self.assertEqual(rep.block_code, P231_BLOCKED_MARKER_CAMERA_SETTINGS_RESET_DRIFT)

    def test_30_initialize_clears_all_markers_to_off_passes_and_retaining_any_marker_blocked(self) -> None:
        ok_rep = evaluate_marker_persistence_hdmi_and_flexexp_vault(
            MarkerPersistenceAndFlexExpVaultSpec(
                reset_action="Initialize",
                post_reset_marker_display="Off",
                post_reset_center_marker="Off",
                post_reset_aspect_marker="Off",
                post_reset_safety_zone="Off",
                post_reset_guideframe="Off",
                lcd_markers_rendered=False,
            )
        )
        self.assertTrue(ok_rep.passed)

        for retained in (
            {"post_reset_marker_display": "On"},
            {"post_reset_center_marker": "On"},
            {"post_reset_aspect_marker": "2.39:1"},
            {"post_reset_safety_zone": "90%"},
            {"post_reset_guideframe": "On"},
        ):
            base = {
                "reset_action": "Initialize",
                "post_reset_marker_display": "Off",
                "post_reset_center_marker": "Off",
                "post_reset_aspect_marker": "Off",
                "post_reset_safety_zone": "Off",
                "post_reset_guideframe": "Off",
                "lcd_markers_rendered": False,
            }
            base.update(retained)
            with self.subTest(retained=retained):
                bad_rep = evaluate_marker_persistence_hdmi_and_flexexp_vault(
                    MarkerPersistenceAndFlexExpVaultSpec(**base)
                )
                self.assertFalse(bad_rep.passed)
                self.assertEqual(bad_rep.block_code, P231_BLOCKED_MARKER_CAMERA_SETTINGS_RESET_DRIFT)

    def test_31_hdmi_marker_suppression_zero_leak_even_with_hdmi_info_display_on_and_off(self) -> None:
        for hdmi_info in ("Off", "On"):
            with self.subTest(hdmi_info_display=hdmi_info):
                rep = evaluate_marker_persistence_hdmi_and_flexexp_vault(
                    MarkerPersistenceAndFlexExpVaultSpec(hdmi_info_display=hdmi_info)
                )
                self.assertTrue(rep.passed)
                self.assertTrue(rep.hdmi_marker_zero_leak_verified)

    def test_32_any_hdmi_marker_overlay_leak_or_lcd_mismatch_blocked(self) -> None:
        for kw in (
            {"hdmi_center_marker_rendered": True},
            {"hdmi_aspect_marker_rendered": True},
            {"hdmi_safety_zone_rendered": True},
            {"hdmi_guideframe_rendered": True},
            {"hdmi_marker_overlay_leak_count": 1},
            {"lcd_markers_rendered": False},
        ):
            with self.subTest(kw=kw):
                rep = evaluate_marker_persistence_hdmi_and_flexexp_vault(
                    MarkerPersistenceAndFlexExpVaultSpec(**kw)
                )
                self.assertFalse(rep.passed)
                self.assertEqual(rep.block_code, P231_BLOCKED_HDMI_MARKER_OVERLAY_LEAKAGE)

    def test_33_flexexp_av_tv_iso_and_auto_slow_shutter_reset_split_enforced(self) -> None:
        for bad_kw in (
            {"post_reset_av_switch": "Auto"},
            {"post_reset_tv_switch": "Auto"},
            {"post_reset_iso_switch": "Auto"},
            {"post_reset_auto_slow_shutter": "Off"},
        ):
            with self.subTest(bad_kw=bad_kw):
                rep = evaluate_marker_persistence_hdmi_and_flexexp_vault(
                    MarkerPersistenceAndFlexExpVaultSpec(
                        reset_action="Camera Settings Reset",
                        camset_restore_after_reset=False,
                        **bad_kw,
                    )
                )
                self.assertFalse(rep.passed)
                self.assertEqual(
                    rep.block_code,
                    P231_BLOCKED_FLEXEXP_OR_AUTOSLOWSHUTTER_RESET_SPLIT_DRIFT,
                )

    def test_34_no_reset_action_preserves_flexexp_and_pasm_submodes(self) -> None:
        for pasm in P231_PASM_SUBMODES:
            with self.subTest(pasm_submode=pasm):
                rep = evaluate_marker_persistence_hdmi_and_flexexp_vault(
                    MarkerPersistenceAndFlexExpVaultSpec(
                        reset_action="NONE",
                        exposure_ctrl_type="P/A/S/M Mode",
                        post_reset_exposure_ctrl_type="P/A/S/M Mode",
                        pasm_submode=pasm,
                        pre_reset_av_switch="Auto",
                        pre_reset_tv_switch="Manual",
                        pre_reset_iso_switch="Auto",
                        pre_reset_auto_slow_shutter="Off",
                        post_reset_av_switch="Auto",
                        post_reset_tv_switch="Manual",
                        post_reset_iso_switch="Auto",
                        post_reset_auto_slow_shutter="Off",
                    )
                )
                self.assertTrue(rep.passed)

    def test_35_no_reset_action_unexpected_flexexp_drift_blocked(self) -> None:
        rep = evaluate_marker_persistence_hdmi_and_flexexp_vault(
            MarkerPersistenceAndFlexExpVaultSpec(
                reset_action="NONE",
                pre_reset_av_switch="Auto",
                post_reset_av_switch="Manual",
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P231_BLOCKED_FLEXEXP_OR_AUTOSLOWSHUTTER_RESET_SPLIT_DRIFT)

    def test_36_camset01_to_10_slot1_vault_restores_flexexp_av_tv_iso_and_auto_slow_shutter(self) -> None:
        for fn in P231_CAMSET_FILENAMES:
            with self.subTest(camset_filename=fn):
                rep = evaluate_marker_persistence_hdmi_and_flexexp_vault(
                    MarkerPersistenceAndFlexExpVaultSpec(
                        reset_action="Camera Settings Reset",
                        camset_restore_after_reset=True,
                        camset_slot=1,
                        camset_filename=fn,
                        saved_exposure_ctrl_type="Flexible Exp. Mode",
                        saved_av_switch="Auto",
                        saved_tv_switch="Auto",
                        saved_iso_switch="Auto",
                        saved_auto_slow_shutter="Off",
                        post_reset_exposure_ctrl_type="Flexible Exp. Mode",
                        post_reset_av_switch="Auto",
                        post_reset_tv_switch="Auto",
                        post_reset_iso_switch="Auto",
                        post_reset_auto_slow_shutter="Off",
                    )
                )
                self.assertTrue(rep.passed)
                self.assertTrue(rep.camset_slot1_restore_verified)

    def test_37_camset_slot2_or_camset11_or_restored_switch_mismatch_blocked(self) -> None:
        for bad_kw in (
            {"camset_slot": 2},
            {"camset_filename": "CAMSET11.DAT"},
            {
                "camset_restore_after_reset": True,
                "saved_av_switch": "Auto",
                "post_reset_av_switch": "Manual",
            },
            {
                "camset_restore_after_reset": True,
                "saved_auto_slow_shutter": "Off",
                "post_reset_auto_slow_shutter": "On",
            },
        ):
            with self.subTest(bad_kw=bad_kw):
                rep = evaluate_marker_persistence_hdmi_and_flexexp_vault(
                    MarkerPersistenceAndFlexExpVaultSpec(**bad_kw)
                )
                self.assertFalse(rep.passed)
                self.assertEqual(rep.block_code, P231_BLOCKED_CAMSET_SLOT1_FLEXEXP_RESTORE_DRIFT)

    def test_38_pillar35b_invalid_aspect_ratio_or_flexexp_token_blocked(self) -> None:
        self.assertEqual(
            evaluate_marker_persistence_hdmi_and_flexexp_vault(
                MarkerPersistenceAndFlexExpVaultSpec(
                    pre_reset_aspect_marker="2.40:1",
                    post_reset_aspect_marker="2.40:1",
                )
            ).block_code,
            P231_BLOCKED_INVALID_MARKER_OR_FLEXEXP_SPEC,
        )
        self.assertEqual(
            evaluate_marker_persistence_hdmi_and_flexexp_vault(
                MarkerPersistenceAndFlexExpVaultSpec(hdmi_info_display="Auto")
            ).block_code,
            P231_BLOCKED_INVALID_MARKER_OR_FLEXEXP_SPEC,
        )
        self.assertEqual(
            evaluate_marker_persistence_hdmi_and_flexexp_vault(
                MarkerPersistenceAndFlexExpVaultSpec(exposure_ctrl_type="Cine Auto")
            ).block_code,
            P231_BLOCKED_INVALID_MARKER_OR_FLEXEXP_SPEC,
        )

    def test_39_pillar35b_overlay_escape_and_backup_h0_h3_drift_and_unlock_blocked(self) -> None:
        self.assertEqual(
            evaluate_marker_persistence_hdmi_and_flexexp_vault(
                MarkerPersistenceAndFlexExpVaultSpec(stage_b_overlay_dir="/dev/cnflasha/marker_overlay")
            ).block_code,
            P231_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
        )
        self.assertEqual(
            evaluate_marker_persistence_hdmi_and_flexexp_vault(
                MarkerPersistenceAndFlexExpVaultSpec(tier0_surfaces_h0_h3_matched=15)
            ).block_code,
            P231_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
        )
        self.assertEqual(
            evaluate_marker_persistence_hdmi_and_flexexp_vault(
                MarkerPersistenceAndFlexExpVaultSpec(persistent_write_unlock_requested=True)
            ).block_code,
            P231_BLOCKED_SAFETY_POLICY_VIOLATION,
        )

    def test_40_pillar35b_6_scenario_suite_all_pass(self) -> None:
        res = run_pillar35b_marker_hdmi_flexexp_vault_6_scenario_suite()
        self.assertTrue(res.passed)
        self.assertEqual(res.status, P231_STATUS_VERIFIED_PILLAR_35B)
        self.assertEqual(res.scenarios_passed, 6)
        self.assertEqual(res.scenarios_total, 6)


class TestCombinedPillar35AndMaster35Aggregator(unittest.TestCase):
    def test_41_combined_verify_silent_autopixelmap_and_marker_flexexp_vault_both_modes(self) -> None:
        for clean in (False, True):
            with self.subTest(force_clean_room=clean):
                rep = verify_silent_autopixelmap_and_marker_flexexp_vault(force_clean_room=clean)
                self.assertTrue(rep.all_passed)
                self.assertTrue(rep.passed)
                self.assertEqual(rep.status, P231_STATUS_VERIFIED_PILLAR35_SUITE)
                self.assertTrue(rep.cnflasha_userspace_write_blocked)
                self.assertEqual(rep.otp_fuse_touches, 0)
                self.assertEqual(rep.rpmb_counter_increments, 0)
                self.assertEqual(rep.physical_device_writes, 0)
                self.assertFalse(rep.persistent_emmc_writes_authorized)
                self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_42_combined_verifier_env_force_clean_room(self) -> None:
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            rep = verify_silent_autopixelmap_and_marker_flexexp_vault()
        self.assertTrue(rep.all_passed)
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(rep.cnflasha_userspace_write_blocked)
        self.assertEqual(rep.otp_fuse_touches, 0)
        self.assertEqual(rep.rpmb_counter_increments, 0)
        self.assertEqual(rep.physical_device_writes, 0)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_43_combined_verifier_propagates_35a_and_35b_failures(self) -> None:
        rep_a = verify_silent_autopixelmap_and_marker_flexexp_vault(
            silent_autopixelmap_spec=SilentModeAutoPixelMapBenchFirewallSpec(
                shutter_when_pwr_off_menu_present=True,
                shutter_when_pwr_off_setting="On",
            ),
            force_clean_room=True,
        )
        self.assertFalse(rep_a.all_passed)
        self.assertTrue(len(rep_a.errors) >= 1)

        rep_b = verify_silent_autopixelmap_and_marker_flexexp_vault(
            marker_flexexp_spec=MarkerPersistenceAndFlexExpVaultSpec(hdmi_aspect_marker_rendered=True),
            force_clean_room=True,
        )
        self.assertFalse(rep_b.all_passed)
        self.assertTrue(len(rep_b.errors) >= 1)

    def test_44_standalone_pillar35_suite_default_and_clean_room(self) -> None:
        rep_def = run_pillar35_standalone_suite()
        rep_cr = run_pillar35_standalone_suite(force_clean_room=True)
        for rep in (rep_def, rep_cr):
            self.assertTrue(rep.all_passed)
            self.assertEqual(rep.schema, PHASE231_SCHEMA)
            self.assertEqual(rep.version, PHASE231_VERSION)
            self.assertEqual(rep.pillar_35a_silent_autopixelmap_firewall.scenarios_passed, 6)
            self.assertEqual(rep.pillar_35b_marker_hdmi_flexexp_vault.scenarios_passed, 6)
            self.assertEqual(len(rep.suite_sha256), 64)
        self.assertEqual(rep_cr.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_45_master_35pillar_default_mode_35_of_35_under_6s(self) -> None:
        rep = evaluate_realhw_35pillar_recovery_master()
        self.assertTrue(rep.all_passed)
        self.assertEqual(rep.status, P231_STATUS_VERIFIED_35OF35_AGGREGATOR)
        self.assertEqual(rep.pillar_count, 35)
        self.assertEqual(rep.pillars_passed, 35)
        self.assertEqual(rep.failed_pillars, ())
        self.assertTrue(rep.under_6s_budget)
        self.assertTrue(rep.cnflasha_userspace_write_blocked)
        self.assertEqual(rep.otp_fuse_touches, 0)
        self.assertEqual(rep.rpmb_counter_increments, 0)
        self.assertEqual(rep.physical_device_writes, 0)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_46_master_35pillar_clean_room_deterministic_sha256(self) -> None:
        r1 = evaluate_realhw_35pillar_recovery_master(force_clean_room=True)
        r2 = evaluate_realhw_35pillar_recovery_master(force_clean_room=True)
        self.assertTrue(r1.all_passed)
        self.assertEqual(r1.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(r1.master_35pillar_sha256, r2.master_35pillar_sha256)
        self.assertEqual(len(r1.master_35pillar_sha256), 64)

    def test_47_master_35pillar_env_force_clean_room_invariants(self) -> None:
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            rep = evaluate_realhw_35pillar_recovery_master()
        self.assertTrue(rep.all_passed)
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(rep.pillar_count, 35)
        self.assertEqual(rep.pillars_passed, 35)
        self.assertTrue(rep.cnflasha_userspace_write_blocked)
        self.assertEqual(rep.otp_fuse_touches, 0)
        self.assertEqual(rep.rpmb_counter_increments, 0)
        self.assertEqual(rep.physical_device_writes, 0)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_48_master_35pillar_symmetry_aliases(self) -> None:
        r_alias = evaluate_35pillar_recovery_master(force_clean_room=True)
        r_cli = verify_35pillar_recovery_suite(force_clean_room=True)
        self.assertEqual(r_alias.master_35pillar_sha256, r_cli.master_35pillar_sha256)
        self.assertEqual(r_alias.pillars_passed, 35)

    def test_49_master_35pillar_fault_injection_pillar_35(self) -> None:
        rep = evaluate_realhw_35pillar_recovery_master(
            force_clean_room=True,
            fault_inject_pillar="pillar_35_silent_autopixelmap_marker_flexexp_vault",
        )
        self.assertFalse(rep.all_passed)
        self.assertEqual(rep.status, P231_STATUS_FAIL_35OF35_AGGREGATOR)
        self.assertEqual(rep.pillars_passed, 34)
        self.assertEqual(rep.failed_pillars, ("pillar_35_silent_autopixelmap_marker_flexexp_vault",))

    def test_50_master_35pillar_fault_injection_pillar_34(self) -> None:
        rep = evaluate_realhw_35pillar_recovery_master(
            force_clean_room=True,
            fault_inject_pillar="pillar_34_zebra_fullformat_chord_slot1_vault",
        )
        self.assertFalse(rep.all_passed)
        self.assertEqual(rep.pillars_passed, 34)
        self.assertEqual(rep.failed_pillars, ("pillar_34_zebra_fullformat_chord_slot1_vault",))

    def test_51_master_35pillar_fault_injection_pillar_1(self) -> None:
        first_id = MASTER_35_PILLAR_IDS[0]
        rep = evaluate_realhw_35pillar_recovery_master(
            force_clean_room=True,
            fault_inject_pillar=first_id,
        )
        self.assertFalse(rep.all_passed)
        self.assertEqual(rep.pillars_passed, 34)
        self.assertEqual(rep.failed_pillars, (first_id,))

    def test_52_master_35pillar_unknown_fault_inject_raises(self) -> None:
        with self.assertRaises(ValueError):
            evaluate_realhw_35pillar_recovery_master(
                force_clean_room=True,
                fault_inject_pillar="nonexistent_pillar_99",
            )

    def test_53_json_serialization_roundtrip_master_and_reports(self) -> None:
        rep = evaluate_realhw_35pillar_recovery_master(force_clean_room=True)
        encoded = json.dumps(rep.to_dict(), sort_keys=True, allow_nan=False)
        decoded = json.loads(encoded)
        self.assertEqual(decoded["status"], P231_STATUS_VERIFIED_35OF35_AGGREGATOR)
        self.assertEqual(decoded["pillar_count"], 35)
        self.assertEqual(decoded["pillars_passed"], 35)
        p35_comb = verify_silent_autopixelmap_and_marker_flexexp_vault(force_clean_room=True)
        self.assertTrue(json.loads(json.dumps(p35_comb.to_dict(), sort_keys=True))["all_passed"])


class TestBackwardCompatibilityAndCli(unittest.TestCase):
    def test_54_backward_compatibility_with_34pillar_master(self) -> None:
        rep34 = fx3_recovery.evaluate_realhw_34pillar_recovery_master(force_clean_room=True)
        self.assertTrue(rep34.all_passed)
        self.assertEqual(rep34.pillar_count, 34)
        self.assertEqual(rep34.pillars_passed, 34)

    def test_55_backward_compatibility_with_33pillar_master(self) -> None:
        rep33 = fx3_recovery.evaluate_realhw_33pillar_recovery_master(force_clean_room=True)
        self.assertTrue(rep33.all_passed)
        self.assertEqual(rep33.pillar_count, 33)
        self.assertEqual(rep33.pillars_passed, 33)

    def test_56_backward_compatibility_across_22_to_32_pillar_masters(self) -> None:
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

    def test_57_cli_verify_silent_autopixelmap_marker_vault_json(self) -> None:
        proc = self._run_cli("verify-silent-autopixelmap-marker-vault", "--json")
        self.assertEqual(proc.returncode, 0, msg=proc.stderr or proc.stdout)
        data = json.loads(proc.stdout)
        self.assertTrue(data["all_passed"])
        self.assertEqual(data["status"], P231_STATUS_VERIFIED_PILLAR35_SUITE)
        self.assertTrue(data["cnflasha_userspace_write_blocked"])
        self.assertEqual(data["raw_firmware_bytes_leaked"], 0)

    def test_58_cli_verify_silent_autopixelmap_marker_vault_clean_room_summary(self) -> None:
        proc = self._run_cli("verify-silent-autopixelmap-marker-vault", "--clean-room")
        self.assertEqual(proc.returncode, 0, msg=proc.stderr or proc.stdout)
        self.assertIn("status=VERIFIED_PILLAR35_SILENT_AUTOPIXELMAP_MARKER_FLEXEXP_VAULT", proc.stdout)
        self.assertIn("mode=CLEAN_ROOM_SYNTHETIC", proc.stdout)
        self.assertIn("pillar_35a=6/6", proc.stdout)
        self.assertIn("pillar_35b=6/6", proc.stdout)

    def test_59_cli_verify_35pillar_recovery_normal_json(self) -> None:
        proc = self._run_cli("verify-35pillar-recovery", "--json")
        self.assertEqual(proc.returncode, 0, msg=proc.stderr or proc.stdout)
        data = json.loads(proc.stdout)
        self.assertTrue(data["all_passed"])
        self.assertEqual(data["status"], P231_STATUS_VERIFIED_35OF35_AGGREGATOR)
        self.assertEqual(data["pillar_count"], 35)
        self.assertEqual(data["pillars_passed"], 35)
        self.assertTrue(data["under_6s_budget"])

    def test_60_cli_verify_35pillar_recovery_normal_summary_line(self) -> None:
        proc = self._run_cli("verify-35pillar-recovery")
        self.assertEqual(proc.returncode, 0, msg=proc.stderr or proc.stdout)
        self.assertIn("status=VERIFIED_35OF35_PILLAR_RECOVERY_MASTER", proc.stdout)
        self.assertIn("pillars=35/35", proc.stdout)
        self.assertIn("pillar35_a=6/6", proc.stdout)
        self.assertIn("pillar35_b=6/6", proc.stdout)

    def test_61_cli_verify_35pillar_recovery_clean_room_env_and_flag(self) -> None:
        proc = self._run_cli(
            "verify-35pillar-recovery",
            "--force-clean-room",
            "--json",
            extra_env={"FX3_FX6_FORCE_CLEAN_ROOM": "1"},
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr or proc.stdout)
        data = json.loads(proc.stdout)
        self.assertEqual(data["verification_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(data["pillars_passed"], 35)

    def test_62_cli_verify_35pillar_recovery_out_directory_and_overwrite_guard(self) -> None:
        here = Path(__file__).resolve().parent
        out_dir = here / f"_tmp_p231_m35_{os.getpid()}"
        p35_dir = here / f"_tmp_p231_p35_{os.getpid()}"
        for d in (out_dir, p35_dir):
            if d.exists():
                shutil.rmtree(d)
        try:
            proc = self._run_cli("verify-35pillar-recovery", "--clean-room", "--out", str(out_dir))
            self.assertEqual(proc.returncode, 0, msg=proc.stderr or proc.stdout)
            report_file = out_dir / "35pillar-recovery-master-report.json"
            self.assertTrue(report_file.is_file())
            saved = json.loads(report_file.read_text(encoding="utf-8"))
            self.assertEqual(saved["status"], P231_STATUS_VERIFIED_35OF35_AGGREGATOR)
            self.assertEqual(saved["pillars_passed"], 35)

            proc_dup = self._run_cli("verify-35pillar-recovery", "--clean-room", "--out", str(out_dir))
            self.assertEqual(proc_dup.returncode, 2)

            proc_p35 = self._run_cli(
                "verify-silent-autopixelmap-marker-vault",
                "--clean-room",
                "--out",
                str(p35_dir),
            )
            self.assertEqual(proc_p35.returncode, 0, msg=proc_p35.stderr or proc_p35.stdout)
            self.assertTrue((p35_dir / "pillar35-silent-autopixelmap-marker-vault-report.json").is_file())
        finally:
            for d in (out_dir, p35_dir):
                if d.exists():
                    shutil.rmtree(d)

    def test_63_safety_invariant_tamper_detected_by_helper(self) -> None:
        with mock.patch.object(p231, "PERSISTENT_EMMC_WRITES_AUTHORIZED", True):
            errs = p231._safety_invariant_errors()
            self.assertTrue(any("PERSISTENT_EMMC_WRITES_AUTHORIZED" in e for e in errs))
            rep35a = evaluate_silent_mode_autopixelmap_bench_firewall(SilentModeAutoPixelMapBenchFirewallSpec())
            self.assertFalse(rep35a.passed)
            self.assertEqual(rep35a.block_code, P231_BLOCKED_SAFETY_POLICY_VIOLATION)

    def test_64_subreports_to_dict_serializable(self) -> None:
        rep_a = evaluate_silent_mode_autopixelmap_bench_firewall(SilentModeAutoPixelMapBenchFirewallSpec())
        rep_b = evaluate_marker_persistence_hdmi_and_flexexp_vault(MarkerPersistenceAndFlexExpVaultSpec())
        self.assertTrue(json.loads(json.dumps(rep_a.to_dict()))["passed"])
        self.assertTrue(json.loads(json.dumps(rep_b.to_dict()))["passed"])


if __name__ == "__main__":
    unittest.main()
