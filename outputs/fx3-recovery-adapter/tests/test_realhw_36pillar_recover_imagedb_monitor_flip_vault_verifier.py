"""Phase 234 — Dual-mode unit tests for Pillar 36 (`[Recover Image DB]` depleted-battery refusal,
non-deleting `AVF_INFO` repair & Slot-1 Tier-0 dump vault mutation firewall; `[Monitor Flip Direction]`
`[Camera Settings Reset]` survival + playback non-inversion, exact `[AF Subj. Shift Sensitivity]` /
`[AF Transition Speed]` reset + `CAMSET01.DAT` restore & still-only `[Interval Shoot Func.]` scope)
and unified `36/36` recovery master (`verify-36pillar-recovery`)."""

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
from fx3_recovery import realhw_36pillar_recover_imagedb_monitor_flip_vault_verifier as p234
from fx3_recovery.realhw_36pillar_recover_imagedb_monitor_flip_vault_verifier import (
    ALLOW_BOOT_PARTITION_TARGETING,
    ALLOW_DESTRUCTIVE_FASTBOOT,
    ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS,
    ALLOW_PERSISTENT_JIRITSU_WRITES,
    CNFLASHA_USERSPACE_WRITE_BLOCKED,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    ISP_WRITE_AUTHORIZED,
    LIVE_USB_IOKIT_TRANSMIT_ENABLED,
    MASTER_36_PILLAR_COUNT,
    MASTER_36_PILLAR_IDS,
    MASTER_36_PILLAR_SPECS,
    OTP_FUSE_TOUCHES,
    OTP_FUSE_WRITES,
    P234_AF_KINEMATICS_SCOPES,
    P234_AF_SUBJ_SHIFT_SENSITIVITY_DEFAULT,
    P234_AF_SUBJ_SHIFT_SENSITIVITY_MENU_NAME,
    P234_AF_SUBJ_SHIFT_SENSITIVITY_VALUES,
    P234_AF_TRANSITION_SPEED_DEFAULT,
    P234_AF_TRANSITION_SPEED_MENU_NAME,
    P234_AF_TRANSITION_SPEED_VALUES,
    P234_AVF_INFO_DB_FILES,
    P234_BLOCKED_ABBREVIATED_OR_INVALID_AF_MENU_NAME,
    P234_BLOCKED_AF_KINEMATICS_RESET_OR_CAMSET_RESTORE_DRIFT,
    P234_BLOCKED_CAMSET_SLOT1_AF_RESTORE_DRIFT,
    P234_BLOCKED_INTERVAL_SHOOT_STILL_ONLY_SCOPE_OR_RANGE_VIOLATION,
    P234_BLOCKED_INVALID_MONITOR_FLIP_OR_AF_INTERVAL_SPEC,
    P234_BLOCKED_INVALID_RECOVER_IMAGEDB_SPEC,
    P234_BLOCKED_MONITOR_FLIP_CAMERA_SETTINGS_RESET_DRIFT,
    P234_BLOCKED_MONITOR_FLIP_PLAYBACK_INVERSION_VIOLATION,
    P234_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
    P234_BLOCKED_RECOVER_IMAGEDB_ACTION_RESET_IMMUNITY_DRIFT,
    P234_BLOCKED_RECOVER_IMAGEDB_CLIP_OR_STILL_DELETION,
    P234_BLOCKED_RECOVER_IMAGEDB_DEPLETED_BATTERY,
    P234_BLOCKED_SAFETY_POLICY_VIOLATION,
    P234_BLOCKED_SLOT1_UNVERIFIED_TIER0_VAULT_IMAGEDB_MUTATION,
    P234_BLOCKED_SLOT1_WP_OR_ACTIVE_VAULT_IMAGEDB_WRITE_DENIED,
    P234_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
    P234_CAMSET_FILENAMES,
    P234_FORBIDDEN_ABBREVIATED_AF_MENU_NAMES,
    P234_FX3_SUPPORTED_FW_VERSIONS,
    P234_IMAGEDB_SYMPTOMS,
    P234_INTERVAL_OUTPUT_STILL_SEQUENCE,
    P234_INTERVAL_SHOOTING_MAX_SEC,
    P234_INTERVAL_SHOOTING_MIN_SEC,
    P234_INTERVAL_SHOOT_MENU_PATH,
    P234_INTERVAL_START_TIME_MAX_SEC,
    P234_INTERVAL_START_TIME_MIN_SEC,
    P234_MONITOR_FLIP_DEFAULT,
    P234_MONITOR_FLIP_DIRECTIONS,
    P234_MONITOR_FLIP_MENU_PATH,
    P234_PINNED_FX3_LIBIMDB_SO_BYTES,
    P234_PINNED_FX3_LIBIMDB_SO_SHA256,
    P234_RECOVER_IMAGEDB_MENU_PATH,
    P234_RECOVER_IMAGEDB_MIN_BATTERY_PCT,
    P234_RECOVER_IMAGEDB_MIN_VOLTAGE_V,
    P234_STATUS_FAIL_36OF36_AGGREGATOR,
    P234_STATUS_VERIFIED_36OF36_AGGREGATOR,
    P234_STATUS_VERIFIED_PILLAR36_SUITE,
    P234_STATUS_VERIFIED_PILLAR_36A,
    P234_STATUS_VERIFIED_PILLAR_36B,
    P234_TIER0_VAULT_ARTIFACTS,
    PASSIVE_TX_BYTES_EMITTED,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHASE234_SCHEMA,
    PHASE234_VERSION,
    PHYSICAL_DEVICE_WRITES,
    PHYSICAL_USB_PACKETS_EMITTED,
    RAW_FIRMWARE_BYTES_LEAKED,
    READ_ONLY_DONOR_ACCESS,
    RPMB_COUNTER_INCREMENTS,
    SPI_NOR_WRITE_AUTHORIZED,
    MonitorFlipPlaybackAndAfIntervalVaultSpec,
    RecoverImageDbBatteryAndVaultFirewallSpec,
    build_default_safe_monitor_flip_af_interval_spec,
    build_default_safe_recover_imagedb_spec,
    evaluate_36pillar_recovery_master,
    evaluate_monitor_flip_playback_and_af_interval_vault,
    evaluate_realhw_36pillar_recovery_master,
    evaluate_recover_imagedb_battery_and_vault_firewall,
    inspect_phase234_donors_readonly,
    run_pillar36_standalone_suite,
    run_pillar36a_recover_imagedb_vault_firewall_6_scenario_suite,
    run_pillar36b_monitor_flip_af_interval_6_scenario_suite,
    verify_36pillar_recovery_suite,
    verify_recover_imagedb_and_monitor_flip_af_vault,
)

ADAPTER_ROOT = Path(__file__).resolve().parents[1]


class TestPhase234SafetyAndExports(unittest.TestCase):
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
            "realhw_36pillar_recover_imagedb_monitor_flip_vault_verifier",
            "MASTER_36_PILLAR_COUNT",
            "MASTER_36_PILLAR_IDS",
            "MASTER_36_PILLAR_SPECS",
            "PHASE234_SCHEMA",
            "PHASE234_VERSION",
            "verify_recover_imagedb_and_monitor_flip_af_vault",
            "evaluate_realhw_36pillar_recovery_master",
            "evaluate_36pillar_recovery_master",
            "verify_36pillar_recovery_suite",
            "run_pillar36_standalone_suite",
        ):
            self.assertIn(sym, fx3_recovery.__all__)
            self.assertTrue(hasattr(fx3_recovery, sym))
        self.assertEqual(fx3_recovery.MASTER_35_PILLAR_COUNT, 35)
        self.assertEqual(fx3_recovery.MASTER_36_PILLAR_COUNT, 36)

    def test_03_master_36_pillar_registry_extends_35(self) -> None:
        self.assertEqual(MASTER_36_PILLAR_COUNT, 36)
        self.assertEqual(len(MASTER_36_PILLAR_SPECS), 36)
        self.assertEqual(len(MASTER_36_PILLAR_IDS), 36)
        self.assertEqual(len(set(MASTER_36_PILLAR_IDS)), 36)
        self.assertEqual([s[0] for s in MASTER_36_PILLAR_SPECS], list(range(1, 37)))
        self.assertEqual(MASTER_36_PILLAR_SPECS[:35], fx3_recovery.MASTER_35_PILLAR_SPECS)
        self.assertEqual(
            MASTER_36_PILLAR_SPECS[35],
            (
                36,
                "pillar_36_recover_imagedb_monitor_flip_af_vault",
                "Phase 234",
                "fx3_recovery.realhw_36pillar_recover_imagedb_monitor_flip_vault_verifier",
            ),
        )

    def test_04_wave34_recover_imagedb_monitor_flip_af_interval_constants(self) -> None:
        self.assertEqual(P234_RECOVER_IMAGEDB_MENU_PATH, ("MENU", "Shooting", "Media", "Recover Image DB"))
        self.assertIn("Image DataBase File error", P234_IMAGEDB_SYMPTOMS)
        self.assertIn("FALSE_ZERO_RECORDABLE_IMAGES", P234_IMAGEDB_SYMPTOMS)
        self.assertIn("AVF_INFO/AVIN0001.INP", P234_AVF_INFO_DB_FILES)
        self.assertEqual(P234_MONITOR_FLIP_MENU_PATH, ("MENU", "Setup", "Monitor", "Monitor Flip Direction"))
        self.assertEqual(
            P234_MONITOR_FLIP_DIRECTIONS,
            ("Auto", "Horizontal Flip", "Vertical Flip", "Off"),
        )
        self.assertEqual(P234_MONITOR_FLIP_DEFAULT, "Auto")
        self.assertEqual(P234_AF_SUBJ_SHIFT_SENSITIVITY_MENU_NAME, "AF Subj. Shift Sensitivity")
        self.assertEqual(P234_AF_TRANSITION_SPEED_MENU_NAME, "AF Transition Speed")
        self.assertEqual(P234_AF_SUBJ_SHIFT_SENSITIVITY_DEFAULT, "5(Responsive)")
        self.assertEqual(P234_AF_TRANSITION_SPEED_DEFAULT, "5")
        self.assertEqual(len(P234_AF_SUBJ_SHIFT_SENSITIVITY_VALUES), 5)
        self.assertEqual(len(P234_AF_TRANSITION_SPEED_VALUES), 7)
        self.assertEqual(P234_INTERVAL_SHOOT_MENU_PATH, ("MENU", "Shooting", "Drive Mode", "Interval Shoot Func."))
        self.assertEqual((P234_INTERVAL_START_TIME_MIN_SEC, P234_INTERVAL_START_TIME_MAX_SEC), (1, 5999))
        self.assertEqual((P234_INTERVAL_SHOOTING_MIN_SEC, P234_INTERVAL_SHOOTING_MAX_SEC), (1, 60))
        self.assertEqual(len(P234_CAMSET_FILENAMES), 10)


class TestPhase234ReadOnlyDonorInspection(unittest.TestCase):
    def test_05_donor_inspect_default_mode_under_budget(self) -> None:
        snap = inspect_phase234_donors_readonly()
        self.assertIn(snap.verification_mode, ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"))
        self.assertTrue(snap.all_donors_present)
        self.assertEqual(snap.donor_files_inspected, 7)
        self.assertTrue(snap.under_0_15s_budget)
        self.assertEqual(snap.raw_firmware_bytes_leaked, 0)
        by_id = {a.artifact_id: a for a in snap.artifacts}
        self.assertIn("fx3_libimdb_so", by_id)
        self.assertEqual(by_id["fx3_libimdb_so"].total_bytes, P234_PINNED_FX3_LIBIMDB_SO_BYTES)
        self.assertEqual(by_id["fx3_libimdb_so"].digest_sha256, P234_PINNED_FX3_LIBIMDB_SO_SHA256)
        self.assertIn("IMDB_find_entry", by_id["fx3_libimdb_so"].marker_summary)
        self.assertIn("IMDB_get_entries", by_id["fx3_libimdb_so"].marker_summary)
        self.assertIn("InfraDatabase_Init", by_id["fx3_libimdb_so"].marker_summary)

    def test_06_donor_inspect_force_clean_room_true(self) -> None:
        snap = inspect_phase234_donors_readonly(force_clean_room=True)
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(snap.all_donors_present)
        self.assertEqual(snap.donor_files_inspected, 7)
        self.assertTrue(snap.under_0_15s_budget)
        self.assertEqual(snap.raw_firmware_bytes_leaked, 0)
        self.assertTrue(all(a.read_mode == "CLEAN_ROOM_SYNTHETIC" and a.matches_pinned for a in snap.artifacts))

    def test_07_donor_inspect_env_force_clean_room(self) -> None:
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            snap = inspect_phase234_donors_readonly()
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(snap.all_donors_present)

    def test_08_donor_inspect_missing_local_file_falls_back_to_clean_room(self) -> None:
        with mock.patch.object(p234, "resolve_donor_path", return_value=None):
            snap = inspect_phase234_donors_readonly(force_clean_room=False)
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(snap.all_donors_present)
        self.assertEqual(snap.donor_files_inspected, 7)


class TestPillar36ARecoverImageDbBatteryAndVaultFirewall(unittest.TestCase):
    def test_09_default_slot2_recover_imagedb_with_slot1_wp_vault_untouched_passes(self) -> None:
        spec = build_default_safe_recover_imagedb_spec()
        rep = evaluate_recover_imagedb_battery_and_vault_firewall(spec)
        self.assertTrue(rep.passed)
        self.assertEqual(rep.status, P234_STATUS_VERIFIED_PILLAR_36A)
        self.assertIsNone(rep.block_code)
        self.assertEqual(rep.target_slot, 2)
        self.assertTrue(rep.non_deleting_repair_verified)
        self.assertTrue(rep.depleted_battery_guard_verified)
        self.assertTrue(rep.action_reset_immunity_verified)
        self.assertTrue(rep.slot1_tier0_vault_firewall_verified)
        self.assertTrue(rep.h0_equals_h3_verified)
        self.assertEqual(rep.physical_device_writes, 0)
        self.assertFalse(rep.persistent_emmc_writes_authorized)

    def test_10_slot1_recover_imagedb_permitted_after_offcamera_sha256_and_vault_card_removal(self) -> None:
        rep = evaluate_recover_imagedb_battery_and_vault_firewall(
            RecoverImageDbBatteryAndVaultFirewallSpec(
                target_slot=1,
                imagedb_symptom="FALSE_ZERO_RECORDABLE_IMAGES",
                recordable_images_display_before=0,
                recordable_images_display_after=940,
                slot1_tier0_vault_present=False,
                slot1_vault_artifacts=(),
                slot1_offcamera_sha256_verified=True,
                slot1_sdxc_wp_locked=False,
                target_card_wp_locked=False,
                slot1_filesystem_metadata_writes=0,
            )
        )
        self.assertTrue(rep.passed)
        self.assertTrue(rep.slot1_tier0_vault_firewall_verified)
        self.assertTrue(rep.non_deleting_repair_verified)

    def test_11_all_supported_fx3_fw_versions_accepted_in_pillar36a(self) -> None:
        for fw in P234_FX3_SUPPORTED_FW_VERSIONS:
            with self.subTest(fw_version=fw):
                rep = evaluate_recover_imagedb_battery_and_vault_firewall(
                    RecoverImageDbBatteryAndVaultFirewallSpec(fw_version=fw)
                )
                self.assertTrue(rep.passed)

    def test_12_extremely_depleted_np_fz100_battery_refused_by_flag_pct_or_voltage(self) -> None:
        for bad_kw in (
            {"battery_extremely_depleted": True, "np_fz100_charge_pct": 60, "np_fz100_voltage_v": 7.40},
            {"battery_extremely_depleted": False, "np_fz100_charge_pct": P234_RECOVER_IMAGEDB_MIN_BATTERY_PCT - 1},
            {"battery_extremely_depleted": False, "np_fz100_voltage_v": P234_RECOVER_IMAGEDB_MIN_VOLTAGE_V - 0.05},
        ):
            with self.subTest(bad_kw=bad_kw):
                rep = evaluate_recover_imagedb_battery_and_vault_firewall(
                    RecoverImageDbBatteryAndVaultFirewallSpec(**bad_kw)
                )
                self.assertFalse(rep.passed)
                self.assertEqual(rep.block_code, P234_BLOCKED_RECOVER_IMAGEDB_DEPLETED_BATTERY)
                self.assertFalse(rep.depleted_battery_guard_verified)

    def test_13_depleted_battery_with_recover_imagedb_not_requested_is_safe_idle(self) -> None:
        rep = evaluate_recover_imagedb_battery_and_vault_firewall(
            RecoverImageDbBatteryAndVaultFirewallSpec(
                recover_imagedb_requested=False,
                imagedb_symptom="HEALTHY_NO_REPAIR_NEEDED",
                battery_extremely_depleted=True,
                np_fz100_charge_pct=4,
                np_fz100_voltage_v=6.42,
            )
        )
        self.assertTrue(rep.passed)

    def test_14_slot1_unverified_tier0_vault_blocks_recover_imagedb_across_vault_artifacts(self) -> None:
        for artifact in ("pnflasha", "cnflasha", "CAMSET01.DAT"):
            with self.subTest(vault_artifact=artifact):
                rep = evaluate_recover_imagedb_battery_and_vault_firewall(
                    RecoverImageDbBatteryAndVaultFirewallSpec(
                        target_slot=1,
                        slot1_tier0_vault_present=True,
                        slot1_vault_artifacts=(artifact,),
                        slot1_offcamera_sha256_verified=False,
                        slot1_offcamera_receipt_sha256="",
                        slot1_sdxc_wp_locked=False,
                    )
                )
                self.assertFalse(rep.passed)
                self.assertEqual(rep.block_code, P234_BLOCKED_SLOT1_UNVERIFIED_TIER0_VAULT_IMAGEDB_MUTATION)
                self.assertFalse(rep.slot1_tier0_vault_firewall_verified)

    def test_15_slot1_bad_hex_or_short_receipt_sha256_treated_as_unverified_vault(self) -> None:
        for bad_receipt in ("abc123", "z" * 64):
            with self.subTest(bad_receipt=bad_receipt):
                rep = evaluate_recover_imagedb_battery_and_vault_firewall(
                    RecoverImageDbBatteryAndVaultFirewallSpec(
                        target_slot=1,
                        slot1_tier0_vault_present=True,
                        slot1_offcamera_sha256_verified=True,
                        slot1_offcamera_receipt_sha256=bad_receipt,
                        slot1_sdxc_wp_locked=False,
                    )
                )
                self.assertFalse(rep.passed)
                self.assertEqual(rep.block_code, P234_BLOCKED_SLOT1_UNVERIFIED_TIER0_VAULT_IMAGEDB_MUTATION)

    def test_16_slot1_verified_but_wp_locked_or_still_inserted_vault_card_blocks_writes(self) -> None:
        for bad_kw in (
            {
                "target_slot": 1,
                "slot1_tier0_vault_present": True,
                "slot1_offcamera_sha256_verified": True,
                "slot1_sdxc_wp_locked": False,
            },
            {
                "target_slot": 1,
                "slot1_tier0_vault_present": False,
                "slot1_vault_artifacts": (),
                "slot1_offcamera_sha256_verified": True,
                "slot1_sdxc_wp_locked": True,
            },
            {
                "target_slot": 2,
                "target_card_wp_locked": True,
            },
        ):
            with self.subTest(bad_kw=bad_kw):
                rep = evaluate_recover_imagedb_battery_and_vault_firewall(
                    RecoverImageDbBatteryAndVaultFirewallSpec(**bad_kw)
                )
                self.assertFalse(rep.passed)
                self.assertEqual(rep.block_code, P234_BLOCKED_SLOT1_WP_OR_ACTIVE_VAULT_IMAGEDB_WRITE_DENIED)

    def test_17_slot1_filesystem_metadata_writes_while_vault_present_or_wp_locked_blocked(self) -> None:
        rep_unver = evaluate_recover_imagedb_battery_and_vault_firewall(
            RecoverImageDbBatteryAndVaultFirewallSpec(
                target_slot=2,
                slot1_tier0_vault_present=True,
                slot1_offcamera_sha256_verified=False,
                slot1_filesystem_metadata_writes=1,
            )
        )
        self.assertFalse(rep_unver.passed)
        self.assertEqual(rep_unver.block_code, P234_BLOCKED_SLOT1_UNVERIFIED_TIER0_VAULT_IMAGEDB_MUTATION)

        rep_wp = evaluate_recover_imagedb_battery_and_vault_firewall(
            RecoverImageDbBatteryAndVaultFirewallSpec(
                target_slot=2,
                slot1_tier0_vault_present=True,
                slot1_offcamera_sha256_verified=True,
                slot1_sdxc_wp_locked=True,
                slot1_filesystem_metadata_writes=2,
            )
        )
        self.assertFalse(rep_wp.passed)
        self.assertEqual(rep_wp.block_code, P234_BLOCKED_SLOT1_WP_OR_ACTIVE_VAULT_IMAGEDB_WRITE_DENIED)

    def test_18_recover_imagedb_clip_or_still_deletion_blocked(self) -> None:
        for bad_kw in (
            {"recorded_clips_deleted": 1, "recorded_clips_after": 17},
            {"recorded_stills_deleted": 1, "recorded_stills_after": 41},
            {"recorded_clips_after": 19},
            {"recorded_stills_after": 40},
        ):
            with self.subTest(bad_kw=bad_kw):
                rep = evaluate_recover_imagedb_battery_and_vault_firewall(
                    RecoverImageDbBatteryAndVaultFirewallSpec(**bad_kw)
                )
                self.assertFalse(rep.passed)
                self.assertEqual(rep.block_code, P234_BLOCKED_RECOVER_IMAGEDB_CLIP_OR_STILL_DELETION)
                self.assertFalse(rep.non_deleting_repair_verified)

    def test_19_recover_imagedb_action_item_reset_immunity_enforced(self) -> None:
        for bad_kw in (
            {"action_item_reset_by_camera_settings_reset": True},
            {"action_item_reset_by_initialize": True},
        ):
            with self.subTest(bad_kw=bad_kw):
                rep = evaluate_recover_imagedb_battery_and_vault_firewall(
                    RecoverImageDbBatteryAndVaultFirewallSpec(**bad_kw)
                )
                self.assertFalse(rep.passed)
                self.assertEqual(rep.block_code, P234_BLOCKED_RECOVER_IMAGEDB_ACTION_RESET_IMMUNITY_DRIFT)
                self.assertFalse(rep.action_reset_immunity_verified)

    def test_20_false_zero_recordable_images_requires_nonzero_recovery_and_repaired_flag(self) -> None:
        rep_unrepaired = evaluate_recover_imagedb_battery_and_vault_firewall(
            RecoverImageDbBatteryAndVaultFirewallSpec(avf_info_repaired=False)
        )
        self.assertFalse(rep_unrepaired.passed)
        self.assertEqual(rep_unrepaired.block_code, P234_BLOCKED_INVALID_RECOVER_IMAGEDB_SPEC)

        rep_still_zero = evaluate_recover_imagedb_battery_and_vault_firewall(
            RecoverImageDbBatteryAndVaultFirewallSpec(
                imagedb_symptom="FALSE_ZERO_RECORDABLE_IMAGES",
                recordable_images_display_before=0,
                recordable_images_display_after=0,
            )
        )
        self.assertFalse(rep_still_zero.passed)
        self.assertEqual(rep_still_zero.block_code, P234_BLOCKED_INVALID_RECOVER_IMAGEDB_SPEC)

    def test_21_invalid_model_menu_slot_symptom_or_vault_artifact_blocked(self) -> None:
        for bad_kw in (
            {"camera_model": "ILME-FX6"},
            {"fw_version": "1.01"},
            {"menu_path": ("MENU", "Setup", "Media", "Recover Image DB")},
            {"target_slot": 3},
            {"imagedb_symptom": "UNKNOWN_ERROR"},
            {"slot1_vault_artifacts": ("UNKNOWN.BIN",)},
            {"slot1_tier0_vault_present": True, "slot1_vault_artifacts": ()},
        ):
            with self.subTest(bad_kw=bad_kw):
                rep = evaluate_recover_imagedb_battery_and_vault_firewall(
                    RecoverImageDbBatteryAndVaultFirewallSpec(**bad_kw)
                )
                self.assertFalse(rep.passed)
                self.assertEqual(rep.block_code, P234_BLOCKED_INVALID_RECOVER_IMAGEDB_SPEC)

    def test_22_pillar36a_overlay_escape_h0_h3_drift_and_persistent_unlock_blocked(self) -> None:
        self.assertEqual(
            evaluate_recover_imagedb_battery_and_vault_firewall(
                RecoverImageDbBatteryAndVaultFirewallSpec(overlay_dir="/setting/imagedb_overlay")
            ).block_code,
            P234_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
        )
        self.assertEqual(
            evaluate_recover_imagedb_battery_and_vault_firewall(
                RecoverImageDbBatteryAndVaultFirewallSpec(p2_blkroset_locked=False)
            ).block_code,
            P234_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
        )
        self.assertEqual(
            evaluate_recover_imagedb_battery_and_vault_firewall(
                RecoverImageDbBatteryAndVaultFirewallSpec(persistent_write_unlock_requested=True)
            ).block_code,
            P234_BLOCKED_SAFETY_POLICY_VIOLATION,
        )

    def test_23_pillar36a_6_scenario_suite_all_pass(self) -> None:
        res = run_pillar36a_recover_imagedb_vault_firewall_6_scenario_suite()
        self.assertTrue(res.passed)
        self.assertEqual(res.status, P234_STATUS_VERIFIED_PILLAR_36A)
        self.assertEqual(res.scenarios_passed, 6)
        self.assertEqual(res.scenarios_total, 6)


class TestPillar36BMonitorFlipPlaybackAfAndIntervalVault(unittest.TestCase):
    def test_24_default_horizontal_flip_survives_camera_settings_reset_without_playback_inversion(self) -> None:
        spec = build_default_safe_monitor_flip_af_interval_spec()
        rep = evaluate_monitor_flip_playback_and_af_interval_vault(spec)
        self.assertTrue(rep.passed)
        self.assertEqual(rep.status, P234_STATUS_VERIFIED_PILLAR_36B)
        self.assertIsNone(rep.block_code)
        self.assertTrue(rep.monitor_flip_reset_persistence_verified)
        self.assertTrue(rep.playback_non_inversion_verified)
        self.assertTrue(rep.af_kinematics_reset_and_menu_verified)
        self.assertTrue(rep.camset_slot1_af_restore_verified)
        self.assertTrue(rep.interval_still_only_scope_verified)
        self.assertTrue(rep.h0_equals_h3_verified)
        self.assertEqual(rep.tier0_surfaces_intact, 16)
        self.assertEqual(rep.physical_device_writes, 0)
        self.assertFalse(rep.persistent_emmc_writes_authorized)

    def test_25_all_4_monitor_flip_directions_survive_camera_settings_reset(self) -> None:
        for direction in P234_MONITOR_FLIP_DIRECTIONS:
            with self.subTest(direction=direction):
                rep = evaluate_monitor_flip_playback_and_af_interval_vault(
                    MonitorFlipPlaybackAndAfIntervalVaultSpec(
                        pre_reset_monitor_flip_direction=direction,
                        reset_action="Camera Settings Reset",
                        post_reset_monitor_flip_direction=direction,
                        shooting_liveview_horizontally_flipped=(direction == "Horizontal Flip"),
                        playback_monitor_display_inverted=False,
                    )
                )
                self.assertTrue(rep.passed)
                self.assertTrue(rep.monitor_flip_reset_persistence_verified)

    def test_26_monitor_flip_wiped_by_camera_settings_reset_rejected(self) -> None:
        for direction in ("Horizontal Flip", "Vertical Flip", "Off"):
            with self.subTest(pre_direction=direction):
                rep = evaluate_monitor_flip_playback_and_af_interval_vault(
                    MonitorFlipPlaybackAndAfIntervalVaultSpec(
                        pre_reset_monitor_flip_direction=direction,
                        reset_action="Camera Settings Reset",
                        post_reset_monitor_flip_direction="Auto",
                        shooting_liveview_horizontally_flipped=False,
                    )
                )
                self.assertFalse(rep.passed)
                self.assertEqual(rep.block_code, P234_BLOCKED_MONITOR_FLIP_CAMERA_SETTINGS_RESET_DRIFT)

    def test_27_initialize_restores_monitor_flip_to_auto_and_rejects_non_auto_survival(self) -> None:
        ok_rep = evaluate_monitor_flip_playback_and_af_interval_vault(
            MonitorFlipPlaybackAndAfIntervalVaultSpec(
                pre_reset_monitor_flip_direction="Vertical Flip",
                reset_action="Initialize",
                post_reset_monitor_flip_direction="Auto",
                shooting_liveview_horizontally_flipped=False,
            )
        )
        self.assertTrue(ok_rep.passed)

        for non_default in ("Horizontal Flip", "Vertical Flip", "Off"):
            with self.subTest(post_direction=non_default):
                bad_rep = evaluate_monitor_flip_playback_and_af_interval_vault(
                    MonitorFlipPlaybackAndAfIntervalVaultSpec(
                        pre_reset_monitor_flip_direction=non_default,
                        reset_action="Initialize",
                        post_reset_monitor_flip_direction=non_default,
                        shooting_liveview_horizontally_flipped=(non_default == "Horizontal Flip"),
                    )
                )
                self.assertFalse(bad_rep.passed)
                self.assertEqual(bad_rep.block_code, P234_BLOCKED_MONITOR_FLIP_CAMERA_SETTINGS_RESET_DRIFT)

    def test_28_playback_display_and_timecode_never_inverted_even_under_horizontal_flip(self) -> None:
        for bad_kw in (
            {"playback_monitor_display_inverted": True},
            {"playback_timecode_clipname_mirrored": True},
            {"shooting_liveview_horizontally_flipped": False},
            {
                "pre_reset_monitor_flip_direction": "Auto",
                "post_reset_monitor_flip_direction": "Auto",
                "shooting_liveview_horizontally_flipped": True,
            },
        ):
            with self.subTest(bad_kw=bad_kw):
                rep = evaluate_monitor_flip_playback_and_af_interval_vault(
                    MonitorFlipPlaybackAndAfIntervalVaultSpec(**bad_kw)
                )
                self.assertFalse(rep.passed)
                self.assertEqual(rep.block_code, P234_BLOCKED_MONITOR_FLIP_PLAYBACK_INVERSION_VIOLATION)
                self.assertFalse(rep.playback_non_inversion_verified)

    def test_29_abbreviated_af_subj_shift_sens_or_wrong_af_menu_strings_rejected(self) -> None:
        for bad_name in P234_FORBIDDEN_ABBREVIATED_AF_MENU_NAMES:
            with self.subTest(af_menu_name=bad_name):
                rep = evaluate_monitor_flip_playback_and_af_interval_vault(
                    MonitorFlipPlaybackAndAfIntervalVaultSpec(
                        af_subj_shift_sensitivity_menu_name=bad_name,
                    )
                )
                self.assertFalse(rep.passed)
                self.assertEqual(rep.block_code, P234_BLOCKED_ABBREVIATED_OR_INVALID_AF_MENU_NAME)

        rep_speed = evaluate_monitor_flip_playback_and_af_interval_vault(
            MonitorFlipPlaybackAndAfIntervalVaultSpec(af_transition_speed_menu_name="AF Trans. Speed")
        )
        self.assertFalse(rep_speed.passed)
        self.assertEqual(rep_speed.block_code, P234_BLOCKED_ABBREVIATED_OR_INVALID_AF_MENU_NAME)

    def test_30_all_af_sensitivity_1_to_5_and_transition_speed_1_to_7_reset_across_movie_and_sq(self) -> None:
        for scope in P234_AF_KINEMATICS_SCOPES:
            for sens in P234_AF_SUBJ_SHIFT_SENSITIVITY_VALUES:
                for spd in P234_AF_TRANSITION_SPEED_VALUES:
                    with self.subTest(scope=scope, sens=sens, spd=spd):
                        rep = evaluate_monitor_flip_playback_and_af_interval_vault(
                            MonitorFlipPlaybackAndAfIntervalVaultSpec(
                                af_kinematics_scope=scope,
                                pre_reset_af_subj_shift_sensitivity=sens,
                                pre_reset_af_transition_speed=spd,
                                reset_action="Camera Settings Reset",
                                post_reset_af_subj_shift_sensitivity=P234_AF_SUBJ_SHIFT_SENSITIVITY_DEFAULT,
                                post_reset_af_transition_speed=P234_AF_TRANSITION_SPEED_DEFAULT,
                            )
                        )
                        self.assertTrue(rep.passed)

    def test_31_af_kinematics_failing_to_reset_under_camera_settings_reset_blocked(self) -> None:
        for bad_kw in (
            {"post_reset_af_subj_shift_sensitivity": "1(Locked on)"},
            {"post_reset_af_transition_speed": "1(Slow)"},
            {"post_reset_af_transition_speed": "7(Fast)"},
        ):
            with self.subTest(bad_kw=bad_kw):
                rep = evaluate_monitor_flip_playback_and_af_interval_vault(
                    MonitorFlipPlaybackAndAfIntervalVaultSpec(
                        reset_action="Camera Settings Reset",
                        camset_restore_after_reset=False,
                        **bad_kw,
                    )
                )
                self.assertFalse(rep.passed)
                self.assertEqual(rep.block_code, P234_BLOCKED_AF_KINEMATICS_RESET_OR_CAMSET_RESTORE_DRIFT)

    def test_32_no_reset_action_preserves_af_kinematics_and_blocks_drift(self) -> None:
        ok_rep = evaluate_monitor_flip_playback_and_af_interval_vault(
            MonitorFlipPlaybackAndAfIntervalVaultSpec(
                reset_action="NONE",
                pre_reset_af_subj_shift_sensitivity="2",
                post_reset_af_subj_shift_sensitivity="2",
                pre_reset_af_transition_speed="6",
                post_reset_af_transition_speed="6",
            )
        )
        self.assertTrue(ok_rep.passed)

        bad_rep = evaluate_monitor_flip_playback_and_af_interval_vault(
            MonitorFlipPlaybackAndAfIntervalVaultSpec(
                reset_action="NONE",
                pre_reset_af_subj_shift_sensitivity="2",
                post_reset_af_subj_shift_sensitivity="5(Responsive)",
            )
        )
        self.assertFalse(bad_rep.passed)
        self.assertEqual(bad_rep.block_code, P234_BLOCKED_AF_KINEMATICS_RESET_OR_CAMSET_RESTORE_DRIFT)

    def test_33_camset01_to_10_slot1_restores_af_kinematics_after_reset(self) -> None:
        for fn in P234_CAMSET_FILENAMES:
            with self.subTest(camset_filename=fn):
                rep = evaluate_monitor_flip_playback_and_af_interval_vault(
                    MonitorFlipPlaybackAndAfIntervalVaultSpec(
                        reset_action="Camera Settings Reset",
                        camset_restore_after_reset=True,
                        camset_slot=1,
                        camset_filename=fn,
                        saved_af_subj_shift_sensitivity="1(Locked on)",
                        saved_af_transition_speed="2",
                        post_reset_af_subj_shift_sensitivity="1(Locked on)",
                        post_reset_af_transition_speed="2",
                    )
                )
                self.assertTrue(rep.passed)
                self.assertTrue(rep.camset_slot1_af_restore_verified)

    def test_34_camset_slot2_or_camset11_or_af_restore_mismatch_blocked(self) -> None:
        for bad_kw in (
            {"camset_slot": 2},
            {"camset_filename": "CAMSET11.DAT"},
            {
                "camset_restore_after_reset": True,
                "saved_af_subj_shift_sensitivity": "1(Locked on)",
                "post_reset_af_subj_shift_sensitivity": "5(Responsive)",
            },
            {
                "camset_restore_after_reset": True,
                "saved_af_transition_speed": "7(Fast)",
                "post_reset_af_transition_speed": "5",
            },
        ):
            with self.subTest(bad_kw=bad_kw):
                rep = evaluate_monitor_flip_playback_and_af_interval_vault(
                    MonitorFlipPlaybackAndAfIntervalVaultSpec(**bad_kw)
                )
                self.assertFalse(rep.passed)
                self.assertEqual(rep.block_code, P234_BLOCKED_CAMSET_SLOT1_AF_RESTORE_DRIFT)

    def test_35_interval_shoot_func_boundary_timings_1s_to_99m59s_and_1s_to_60s_pass(self) -> None:
        for start_s, intv_s, shots in ((1, 1, 1), (5999, 60, 9999), (30, 15, 300)):
            with self.subTest(start_s=start_s, intv_s=intv_s, shots=shots):
                rep = evaluate_monitor_flip_playback_and_af_interval_vault(
                    MonitorFlipPlaybackAndAfIntervalVaultSpec(
                        interval_shoot_func="On",
                        interval_start_time_seconds=start_s,
                        interval_shooting_seconds=intv_s,
                        interval_number_of_shots=shots,
                        interval_output_kind=P234_INTERVAL_OUTPUT_STILL_SEQUENCE,
                        requires_external_timelapse_assembly=True,
                        in_camera_video_interval_rec_supported=False,
                        fx6_interval_rec_mxf_mp4_assumed_on_fx3=False,
                    )
                )
                self.assertTrue(rep.passed)
                self.assertTrue(rep.interval_still_only_scope_verified)

    def test_36_interval_shoot_video_assumption_or_out_of_range_timing_blocked(self) -> None:
        for bad_kw in (
            {"interval_start_time_seconds": 0},
            {"interval_start_time_seconds": 6000},
            {"interval_shooting_seconds": 0},
            {"interval_shooting_seconds": 61},
            {"interval_number_of_shots": 0},
            {"interval_number_of_shots": 10000},
            {"interval_output_kind": "VIDEO_MP4_TIMELAPSE"},
            {"requires_external_timelapse_assembly": False},
            {"in_camera_video_interval_rec_supported": True},
            {"fx6_interval_rec_mxf_mp4_assumed_on_fx3": True},
        ):
            with self.subTest(bad_kw=bad_kw):
                rep = evaluate_monitor_flip_playback_and_af_interval_vault(
                    MonitorFlipPlaybackAndAfIntervalVaultSpec(**bad_kw)
                )
                self.assertFalse(rep.passed)
                self.assertEqual(
                    rep.block_code,
                    P234_BLOCKED_INTERVAL_SHOOT_STILL_ONLY_SCOPE_OR_RANGE_VIOLATION,
                )

    def test_37_pillar36b_invalid_monitor_flip_or_af_value_or_interval_state_blocked(self) -> None:
        for bad_kw in (
            {"pre_reset_monitor_flip_direction": "180 Rotate"},
            {"reset_action": "Soft Reset"},
            {"af_kinematics_scope": "Photo"},
            {"pre_reset_af_subj_shift_sensitivity": "6"},
            {"pre_reset_af_transition_speed": "8"},
            {"interval_shoot_func": "Auto"},
        ):
            with self.subTest(bad_kw=bad_kw):
                rep = evaluate_monitor_flip_playback_and_af_interval_vault(
                    MonitorFlipPlaybackAndAfIntervalVaultSpec(**bad_kw)
                )
                self.assertFalse(rep.passed)
                self.assertEqual(rep.block_code, P234_BLOCKED_INVALID_MONITOR_FLIP_OR_AF_INTERVAL_SPEC)

    def test_38_pillar36b_overlay_escape_h0_h3_drift_and_persistent_unlock_blocked(self) -> None:
        self.assertEqual(
            evaluate_monitor_flip_playback_and_af_interval_vault(
                MonitorFlipPlaybackAndAfIntervalVaultSpec(stage_b_overlay_dir="/dev/cnflasha/flip_overlay")
            ).block_code,
            P234_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
        )
        self.assertEqual(
            evaluate_monitor_flip_playback_and_af_interval_vault(
                MonitorFlipPlaybackAndAfIntervalVaultSpec(tier0_surfaces_h0_h3_matched=15)
            ).block_code,
            P234_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
        )
        self.assertEqual(
            evaluate_monitor_flip_playback_and_af_interval_vault(
                MonitorFlipPlaybackAndAfIntervalVaultSpec(persistent_write_unlock_requested=True)
            ).block_code,
            P234_BLOCKED_SAFETY_POLICY_VIOLATION,
        )

    def test_39_pillar36b_6_scenario_suite_all_pass(self) -> None:
        res = run_pillar36b_monitor_flip_af_interval_6_scenario_suite()
        self.assertTrue(res.passed)
        self.assertEqual(res.status, P234_STATUS_VERIFIED_PILLAR_36B)
        self.assertEqual(res.scenarios_passed, 6)
        self.assertEqual(res.scenarios_total, 6)


class TestCombinedPillar36AndMaster36Aggregator(unittest.TestCase):
    def test_40_combined_verify_recover_imagedb_and_monitor_flip_af_vault_both_modes(self) -> None:
        for clean in (False, True):
            with self.subTest(force_clean_room=clean):
                rep = verify_recover_imagedb_and_monitor_flip_af_vault(force_clean_room=clean)
                self.assertTrue(rep.all_passed)
                self.assertTrue(rep.passed)
                self.assertEqual(rep.status, P234_STATUS_VERIFIED_PILLAR36_SUITE)
                self.assertTrue(rep.cnflasha_userspace_write_blocked)
                self.assertEqual(rep.otp_fuse_touches, 0)
                self.assertEqual(rep.rpmb_counter_increments, 0)
                self.assertEqual(rep.physical_device_writes, 0)
                self.assertFalse(rep.persistent_emmc_writes_authorized)
                self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_41_combined_verifier_env_force_clean_room(self) -> None:
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            rep = verify_recover_imagedb_and_monitor_flip_af_vault()
        self.assertTrue(rep.all_passed)
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(rep.cnflasha_userspace_write_blocked)
        self.assertEqual(rep.otp_fuse_touches, 0)
        self.assertEqual(rep.rpmb_counter_increments, 0)
        self.assertEqual(rep.physical_device_writes, 0)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_42_combined_verifier_propagates_36a_and_36b_failures(self) -> None:
        rep_a = verify_recover_imagedb_and_monitor_flip_af_vault(
            recover_imagedb_spec=RecoverImageDbBatteryAndVaultFirewallSpec(battery_extremely_depleted=True),
            force_clean_room=True,
        )
        self.assertFalse(rep_a.all_passed)
        self.assertTrue(len(rep_a.errors) >= 1)

        rep_b = verify_recover_imagedb_and_monitor_flip_af_vault(
            monitor_flip_af_interval_spec=MonitorFlipPlaybackAndAfIntervalVaultSpec(
                playback_monitor_display_inverted=True
            ),
            force_clean_room=True,
        )
        self.assertFalse(rep_b.all_passed)
        self.assertTrue(len(rep_b.errors) >= 1)

    def test_43_standalone_pillar36_suite_default_and_clean_room(self) -> None:
        rep_def = run_pillar36_standalone_suite()
        rep_cr = run_pillar36_standalone_suite(force_clean_room=True)
        for rep in (rep_def, rep_cr):
            self.assertTrue(rep.all_passed)
            self.assertEqual(rep.schema, PHASE234_SCHEMA)
            self.assertEqual(rep.version, PHASE234_VERSION)
            self.assertEqual(rep.pillar_36a_recover_imagedb_vault_firewall.scenarios_passed, 6)
            self.assertEqual(rep.pillar_36b_monitor_flip_af_interval_vault.scenarios_passed, 6)
            self.assertEqual(len(rep.suite_sha256), 64)
        self.assertEqual(rep_cr.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_44_master_36pillar_default_mode_36_of_36_under_6s(self) -> None:
        rep = evaluate_realhw_36pillar_recovery_master()
        self.assertTrue(rep.all_passed)
        self.assertEqual(rep.status, P234_STATUS_VERIFIED_36OF36_AGGREGATOR)
        self.assertEqual(rep.pillar_count, 36)
        self.assertEqual(rep.pillars_passed, 36)
        self.assertEqual(rep.failed_pillars, ())
        self.assertTrue(rep.under_6s_budget)
        self.assertTrue(rep.cnflasha_userspace_write_blocked)
        self.assertEqual(rep.otp_fuse_touches, 0)
        self.assertEqual(rep.rpmb_counter_increments, 0)
        self.assertEqual(rep.physical_device_writes, 0)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_45_master_36pillar_clean_room_deterministic_sha256(self) -> None:
        r1 = evaluate_realhw_36pillar_recovery_master(force_clean_room=True)
        r2 = evaluate_realhw_36pillar_recovery_master(force_clean_room=True)
        self.assertTrue(r1.all_passed)
        self.assertEqual(r1.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(r1.master_36pillar_sha256, r2.master_36pillar_sha256)
        self.assertEqual(len(r1.master_36pillar_sha256), 64)

    def test_46_master_36pillar_env_force_clean_room_invariants(self) -> None:
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            rep = evaluate_realhw_36pillar_recovery_master()
        self.assertTrue(rep.all_passed)
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(rep.pillar_count, 36)
        self.assertEqual(rep.pillars_passed, 36)
        self.assertTrue(rep.cnflasha_userspace_write_blocked)
        self.assertEqual(rep.otp_fuse_touches, 0)
        self.assertEqual(rep.rpmb_counter_increments, 0)
        self.assertEqual(rep.physical_device_writes, 0)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_47_master_36pillar_symmetry_aliases(self) -> None:
        r_alias = evaluate_36pillar_recovery_master(force_clean_room=True)
        r_cli = verify_36pillar_recovery_suite(force_clean_room=True)
        self.assertEqual(r_alias.master_36pillar_sha256, r_cli.master_36pillar_sha256)
        self.assertEqual(r_alias.pillars_passed, 36)

    def test_48_master_36pillar_fault_injection_pillar_36(self) -> None:
        rep = evaluate_realhw_36pillar_recovery_master(
            force_clean_room=True,
            fault_inject_pillar="pillar_36_recover_imagedb_monitor_flip_af_vault",
        )
        self.assertFalse(rep.all_passed)
        self.assertEqual(rep.status, P234_STATUS_FAIL_36OF36_AGGREGATOR)
        self.assertEqual(rep.pillars_passed, 35)
        self.assertEqual(rep.failed_pillars, ("pillar_36_recover_imagedb_monitor_flip_af_vault",))

    def test_49_master_36pillar_fault_injection_pillar_35(self) -> None:
        rep = evaluate_realhw_36pillar_recovery_master(
            force_clean_room=True,
            fault_inject_pillar="pillar_35_silent_autopixelmap_marker_flexexp_vault",
        )
        self.assertFalse(rep.all_passed)
        self.assertEqual(rep.pillars_passed, 35)
        self.assertEqual(rep.failed_pillars, ("pillar_35_silent_autopixelmap_marker_flexexp_vault",))

    def test_50_master_36pillar_fault_injection_pillar_1(self) -> None:
        first_id = MASTER_36_PILLAR_IDS[0]
        rep = evaluate_realhw_36pillar_recovery_master(
            force_clean_room=True,
            fault_inject_pillar=first_id,
        )
        self.assertFalse(rep.all_passed)
        self.assertEqual(rep.pillars_passed, 35)
        self.assertEqual(rep.failed_pillars, (first_id,))

    def test_51_master_36pillar_unknown_fault_inject_raises(self) -> None:
        with self.assertRaises(ValueError):
            evaluate_realhw_36pillar_recovery_master(
                force_clean_room=True,
                fault_inject_pillar="nonexistent_pillar_99",
            )

    def test_52_json_serialization_roundtrip_master_and_reports(self) -> None:
        rep = evaluate_realhw_36pillar_recovery_master(force_clean_room=True)
        encoded = json.dumps(rep.to_dict(), sort_keys=True, allow_nan=False)
        decoded = json.loads(encoded)
        self.assertEqual(decoded["status"], P234_STATUS_VERIFIED_36OF36_AGGREGATOR)
        self.assertEqual(decoded["pillar_count"], 36)
        self.assertEqual(decoded["pillars_passed"], 36)
        p36_comb = verify_recover_imagedb_and_monitor_flip_af_vault(force_clean_room=True)
        self.assertTrue(json.loads(json.dumps(p36_comb.to_dict(), sort_keys=True))["all_passed"])


class TestBackwardCompatibilityAndCli(unittest.TestCase):
    def test_53_backward_compatibility_with_35pillar_master(self) -> None:
        rep35 = fx3_recovery.evaluate_realhw_35pillar_recovery_master(force_clean_room=True)
        self.assertTrue(rep35.all_passed)
        self.assertEqual(rep35.pillar_count, 35)
        self.assertEqual(rep35.pillars_passed, 35)

    def test_54_backward_compatibility_with_34pillar_master(self) -> None:
        rep34 = fx3_recovery.evaluate_realhw_34pillar_recovery_master(force_clean_room=True)
        self.assertTrue(rep34.all_passed)
        self.assertEqual(rep34.pillar_count, 34)
        self.assertEqual(rep34.pillars_passed, 34)

    def test_55_backward_compatibility_across_22_to_33_pillar_masters(self) -> None:
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

    def test_56_cli_verify_recover_imagedb_monitor_flip_vault_json(self) -> None:
        proc = self._run_cli("verify-recover-imagedb-monitor-flip-vault", "--json")
        self.assertEqual(proc.returncode, 0, msg=proc.stderr or proc.stdout)
        data = json.loads(proc.stdout)
        self.assertTrue(data["all_passed"])
        self.assertEqual(data["status"], P234_STATUS_VERIFIED_PILLAR36_SUITE)
        self.assertTrue(data["cnflasha_userspace_write_blocked"])
        self.assertEqual(data["raw_firmware_bytes_leaked"], 0)

    def test_57_cli_verify_recover_imagedb_monitor_flip_vault_clean_room_summary(self) -> None:
        proc = self._run_cli("verify-recover-imagedb-monitor-flip-vault", "--clean-room")
        self.assertEqual(proc.returncode, 0, msg=proc.stderr or proc.stdout)
        self.assertIn("status=VERIFIED_PILLAR36_RECOVER_IMAGEDB_MONITOR_FLIP_AF_VAULT", proc.stdout)
        self.assertIn("mode=CLEAN_ROOM_SYNTHETIC", proc.stdout)
        self.assertIn("pillar_36a=6/6", proc.stdout)
        self.assertIn("pillar_36b=6/6", proc.stdout)

    def test_58_cli_verify_36pillar_recovery_normal_json(self) -> None:
        proc = self._run_cli("verify-36pillar-recovery", "--json")
        self.assertEqual(proc.returncode, 0, msg=proc.stderr or proc.stdout)
        data = json.loads(proc.stdout)
        self.assertTrue(data["all_passed"])
        self.assertEqual(data["status"], P234_STATUS_VERIFIED_36OF36_AGGREGATOR)
        self.assertEqual(data["pillar_count"], 36)
        self.assertEqual(data["pillars_passed"], 36)
        self.assertTrue(data["under_6s_budget"])

    def test_59_cli_verify_36pillar_recovery_normal_summary_line(self) -> None:
        proc = self._run_cli("verify-36pillar-recovery")
        self.assertEqual(proc.returncode, 0, msg=proc.stderr or proc.stdout)
        self.assertIn("status=VERIFIED_36OF36_PILLAR_RECOVERY_MASTER", proc.stdout)
        self.assertIn("pillars=36/36", proc.stdout)
        self.assertIn("pillar36_a=6/6", proc.stdout)
        self.assertIn("pillar36_b=6/6", proc.stdout)

    def test_60_cli_verify_36pillar_recovery_clean_room_env_and_flag(self) -> None:
        proc = self._run_cli(
            "verify-36pillar-recovery",
            "--force-clean-room",
            "--json",
            extra_env={"FX3_FX6_FORCE_CLEAN_ROOM": "1"},
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr or proc.stdout)
        data = json.loads(proc.stdout)
        self.assertEqual(data["verification_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(data["pillars_passed"], 36)

    def test_61_cli_verify_36pillar_recovery_out_directory_and_overwrite_guard(self) -> None:
        here = Path(__file__).resolve().parent
        out_dir = here / f"_tmp_p234_m36_{os.getpid()}"
        p36_dir = here / f"_tmp_p234_p36_{os.getpid()}"
        for d in (out_dir, p36_dir):
            if d.exists():
                shutil.rmtree(d)
        try:
            proc = self._run_cli("verify-36pillar-recovery", "--clean-room", "--out", str(out_dir))
            self.assertEqual(proc.returncode, 0, msg=proc.stderr or proc.stdout)
            report_file = out_dir / "36pillar-recovery-master-report.json"
            self.assertTrue(report_file.is_file())
            saved = json.loads(report_file.read_text(encoding="utf-8"))
            self.assertEqual(saved["status"], P234_STATUS_VERIFIED_36OF36_AGGREGATOR)
            self.assertEqual(saved["pillars_passed"], 36)

            proc_dup = self._run_cli("verify-36pillar-recovery", "--clean-room", "--out", str(out_dir))
            self.assertEqual(proc_dup.returncode, 2)

            proc_p36 = self._run_cli(
                "verify-recover-imagedb-monitor-flip-vault",
                "--clean-room",
                "--out",
                str(p36_dir),
            )
            self.assertEqual(proc_p36.returncode, 0, msg=proc_p36.stderr or proc_p36.stdout)
            self.assertTrue((p36_dir / "pillar36-recover-imagedb-monitor-flip-vault-report.json").is_file())
        finally:
            for d in (out_dir, p36_dir):
                if d.exists():
                    shutil.rmtree(d)

    def test_62_safety_invariant_tamper_detected_by_helper(self) -> None:
        with mock.patch.object(p234, "PERSISTENT_EMMC_WRITES_AUTHORIZED", True):
            errs = p234._safety_invariant_errors()
            self.assertTrue(any("PERSISTENT_EMMC_WRITES_AUTHORIZED" in e for e in errs))
            rep36a = evaluate_recover_imagedb_battery_and_vault_firewall(RecoverImageDbBatteryAndVaultFirewallSpec())
            self.assertFalse(rep36a.passed)
            self.assertEqual(rep36a.block_code, P234_BLOCKED_SAFETY_POLICY_VIOLATION)

    def test_63_subreports_to_dict_serializable(self) -> None:
        rep_a = evaluate_recover_imagedb_battery_and_vault_firewall(RecoverImageDbBatteryAndVaultFirewallSpec())
        rep_b = evaluate_monitor_flip_playback_and_af_interval_vault(MonitorFlipPlaybackAndAfIntervalVaultSpec())
        self.assertTrue(json.loads(json.dumps(rep_a.to_dict()))["passed"])
        self.assertTrue(json.loads(json.dumps(rep_b.to_dict()))["passed"])

    def test_64_tier0_vault_artifacts_tuple_contains_core_surfaces(self) -> None:
        for expected in ("pnflasha", "cnflasha", "CAMSET01.DAT"):
            self.assertIn(expected, P234_TIER0_VAULT_ARTIFACTS)


if __name__ == "__main__":
    unittest.main()
