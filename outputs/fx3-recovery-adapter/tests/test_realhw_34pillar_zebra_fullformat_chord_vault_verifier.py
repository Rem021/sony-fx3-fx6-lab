"""Phase 229 — Dual-mode unit tests for Pillar 34 (`Slot-1` Tier-0 vault firewall against
`Quick Format`, `(Delete)`-toggled `Full Format`, mid-cancel erasure hazard & `MENU + (Delete)`
~2s chord; `[Zebra Display]`/`[Zebra Level]` survival across `[Camera Settings Reset]`, local-LCD
HDMI assist isolation & Ver. 7.02 `[Mode Settings]` `Fixed/Variable` vs `S&Q` recovery) and unified
`34/34` recovery master (`verify-34pillar-recovery`)."""

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
from fx3_recovery import realhw_34pillar_zebra_fullformat_chord_vault_verifier as p229
from fx3_recovery.realhw_34pillar_zebra_fullformat_chord_vault_verifier import (
    ALLOW_BOOT_PARTITION_TARGETING,
    ALLOW_DESTRUCTIVE_FASTBOOT,
    ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS,
    ALLOW_PERSISTENT_JIRITSU_WRITES,
    CNFLASHA_USERSPACE_WRITE_BLOCKED,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    ISP_WRITE_AUTHORIZED,
    LIVE_USB_IOKIT_TRANSMIT_ENABLED,
    MASTER_34_PILLAR_COUNT,
    MASTER_34_PILLAR_IDS,
    MASTER_34_PILLAR_SPECS,
    OTP_FUSE_TOUCHES,
    OTP_FUSE_WRITES,
    P229_AUDIO_OUT_TIMING_MODES,
    P229_BLOCKED_DELETE_TOGGLE_FULL_FORMAT_SLOT1_VAULT_WIPE,
    P229_BLOCKED_FIXED_VARIABLE_LEGACY_SQ_MENU_CONFLICT,
    P229_BLOCKED_FULL_FORMAT_MID_CANCEL_DATA_ERASED_HAZARD,
    P229_BLOCKED_HDMI_ZEBRA_OR_PEAKING_ASSIST_LEAKAGE,
    P229_BLOCKED_INVALID_FORMAT_SPEC,
    P229_BLOCKED_MENU_DELETE_2S_CHORD_SLOT1_VAULT_WIPE,
    P229_BLOCKED_MISSING_OFFCAMERA_SHA256_OR_WP_VAULT_REMOVAL,
    P229_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
    P229_BLOCKED_QUICK_FORMAT_SLOT1_VAULT_WIPE,
    P229_BLOCKED_SAFETY_POLICY_VIOLATION,
    P229_BLOCKED_SDXC_WP_SWITCH_ENGAGED_FORMAT_DENIED,
    P229_BLOCKED_SLOT1_VAULT_MISSING_WP_OR_CHORD_FIREWALL,
    P229_BLOCKED_SQ_RECORDING_LOCKOUT_VIOLATION,
    P229_BLOCKED_SQ_TRANSITION_STATE_RECOVERY_DRIFT,
    P229_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
    P229_BLOCKED_ZEBRA_CAMERA_SETTINGS_RESET_DRIFT,
    P229_CAMSET_FILENAMES,
    P229_MENU_DELETE_CHORD_MIN_SECONDS,
    P229_PEAKING_COLORS,
    P229_PEAKING_LEVELS,
    P229_STATUS_FAIL_34OF34_AGGREGATOR,
    P229_STATUS_VERIFIED_34OF34_AGGREGATOR,
    P229_STATUS_VERIFIED_PILLAR34_SUITE,
    P229_STATUS_VERIFIED_PILLAR_34A,
    P229_STATUS_VERIFIED_PILLAR_34B,
    P229_TIER0_VAULT_ARTIFACTS,
    P229_ZEBRA_LEVEL_PRESETS,
    PASSIVE_TX_BYTES_EMITTED,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHASE229_SCHEMA,
    PHASE229_VERSION,
    PHYSICAL_DEVICE_WRITES,
    PHYSICAL_USB_PACKETS_EMITTED,
    RAW_FIRMWARE_BYTES_LEAKED,
    READ_ONLY_DONOR_ACCESS,
    RPMB_COUNTER_INCREMENTS,
    SPI_NOR_WRITE_AUTHORIZED,
    Slot1FormatAndChordVaultFirewallSpec,
    ZebraPersistenceAndSqTransitionVaultSpec,
    build_default_safe_slot1_format_chord_spec,
    build_default_safe_zebra_sq_recovery_spec,
    evaluate_34pillar_recovery_master,
    evaluate_realhw_34pillar_recovery_master,
    evaluate_slot1_fullformat_and_chord_vault_firewall,
    evaluate_zebra_persistence_and_sq_transition_vault,
    inspect_phase229_donors_readonly,
    run_pillar34_standalone_suite,
    run_pillar34a_fullformat_chord_slot1_vault_6_scenario_suite,
    run_pillar34b_zebra_persistence_sq_recovery_6_scenario_suite,
    verify_34pillar_recovery_suite,
    verify_zebra_persistence_and_fullformat_chord_slot1_vault,
)

ADAPTER_ROOT = Path(__file__).resolve().parents[1]


class TestPhase229SafetyAndExports(unittest.TestCase):
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
            "realhw_34pillar_zebra_fullformat_chord_vault_verifier",
            "MASTER_34_PILLAR_COUNT",
            "MASTER_34_PILLAR_IDS",
            "MASTER_34_PILLAR_SPECS",
            "PHASE229_SCHEMA",
            "PHASE229_VERSION",
            "verify_zebra_persistence_and_fullformat_chord_slot1_vault",
            "evaluate_realhw_34pillar_recovery_master",
            "evaluate_34pillar_recovery_master",
            "verify_34pillar_recovery_suite",
            "run_pillar34_standalone_suite",
        ):
            self.assertIn(sym, fx3_recovery.__all__)
            self.assertTrue(hasattr(fx3_recovery, sym))
        self.assertEqual(fx3_recovery.MASTER_33_PILLAR_COUNT, 33)
        self.assertEqual(fx3_recovery.MASTER_34_PILLAR_COUNT, 34)

    def test_03_master_34_pillar_registry_extends_33(self) -> None:
        self.assertEqual(MASTER_34_PILLAR_COUNT, 34)
        self.assertEqual(len(MASTER_34_PILLAR_SPECS), 34)
        self.assertEqual(len(MASTER_34_PILLAR_IDS), 34)
        self.assertEqual(len(set(MASTER_34_PILLAR_IDS)), 34)
        self.assertEqual([s[0] for s in MASTER_34_PILLAR_SPECS], list(range(1, 35)))
        self.assertEqual(MASTER_34_PILLAR_SPECS[:33], fx3_recovery.MASTER_33_PILLAR_SPECS)
        self.assertEqual(
            MASTER_34_PILLAR_SPECS[33],
            (
                34,
                "pillar_34_zebra_fullformat_chord_slot1_vault",
                "Phase 229",
                "fx3_recovery.realhw_34pillar_zebra_fullformat_chord_vault_verifier",
            ),
        )

    def test_04_zebra_peaking_format_chord_and_camset_constants(self) -> None:
        self.assertEqual(P229_TIER0_VAULT_ARTIFACTS, ("pnflasha", "cnflasha", "CAMSET01.DAT"))
        self.assertEqual(P229_MENU_DELETE_CHORD_MIN_SECONDS, 2.0)
        self.assertEqual(len(P229_ZEBRA_LEVEL_PRESETS), 10)
        self.assertIn("100+", P229_ZEBRA_LEVEL_PRESETS)
        self.assertIn("Custom 1", P229_ZEBRA_LEVEL_PRESETS)
        self.assertIn("Custom 2", P229_ZEBRA_LEVEL_PRESETS)
        self.assertEqual(P229_PEAKING_LEVELS, ("High", "Mid", "Low"))
        self.assertEqual(P229_PEAKING_COLORS, ("Red", "Yellow", "Blue", "White"))
        self.assertEqual(P229_AUDIO_OUT_TIMING_MODES, ("Live", "Lip Sync"))
        self.assertEqual(len(P229_CAMSET_FILENAMES), 10)


class TestPhase229ReadOnlyDonorInspection(unittest.TestCase):
    def test_05_donor_inspect_default_mode_under_budget(self) -> None:
        snap = inspect_phase229_donors_readonly()
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
        snap = inspect_phase229_donors_readonly(force_clean_room=True)
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(snap.all_donors_present)
        self.assertEqual(snap.donor_files_inspected, 7)
        for art in snap.artifacts:
            self.assertEqual(art.read_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertTrue(art.matches_pinned)

    def test_07_donor_inspect_env_force_clean_room(self) -> None:
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            snap = inspect_phase229_donors_readonly()
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(snap.all_donors_present)

    def test_08_donor_inspect_uses_strictly_o_rdonly_flags_and_format_symbols(self) -> None:
        seen_flags: list[int] = []
        real_open = os.open

        def spy_open(path: str, flags: int, *args: object) -> int:
            seen_flags.append(flags)
            return real_open(path, flags, *args)  # type: ignore[arg-type]

        with mock.patch("os.open", side_effect=spy_open):
            snap = inspect_phase229_donors_readonly()
        for fl in seen_flags:
            self.assertEqual(fl & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC), 0)
        if snap.verification_mode == "LOCAL_DONOR_O_RDONLY":
            self.assertEqual(len(seen_flags), 7)
            common_art = [a for a in snap.artifacts if a.artifact_id == "fx3_libinframediacommon_so"][0]
            self.assertIn("GetFormatProgress", common_art.marker_summary)
            self.assertIn("mmcdIoctlFormat", common_art.marker_summary)
            self.assertIn("msdFormat", common_art.marker_summary)

    def test_09_donor_inspect_missing_donor_falls_back_to_clean_room(self) -> None:
        with mock.patch.object(p229, "resolve_donor_path", return_value=None):
            snap = inspect_phase229_donors_readonly(force_clean_room=False)
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(snap.all_donors_present)


class TestPillar34ASlot1FormatAndChordVaultFirewall(unittest.TestCase):
    def test_10_default_safe_slot1_active_vault_passes(self) -> None:
        spec = build_default_safe_slot1_format_chord_spec()
        rep = evaluate_slot1_fullformat_and_chord_vault_firewall(spec)
        self.assertTrue(rep.passed)
        self.assertEqual(rep.status, P229_STATUS_VERIFIED_PILLAR_34A)
        self.assertIsNone(rep.block_code)
        self.assertFalse(rep.format_requested)
        self.assertTrue(rep.slot1_vault_protected)
        self.assertTrue(rep.off_camera_sha256_receipt_verified)
        self.assertTrue(rep.mid_cancel_erasure_hazard_clear)
        self.assertTrue(rep.h0_equals_h3_verified)
        self.assertEqual(rep.physical_device_writes, 0)
        self.assertFalse(rep.persistent_emmc_writes_authorized)

    def test_11_safe_post_receipt_wp_locked_vault_removed_scratch_full_format_passes(self) -> None:
        rep = evaluate_slot1_fullformat_and_chord_vault_firewall(
            Slot1FormatAndChordVaultFirewallSpec(
                slot1_tier0_vault_active=False,
                prior_tier0_vault_session=True,
                off_camera_sha256_receipt_verified=True,
                sdxc_physical_wp_engaged=True,
                vault_card_removed_or_swapped=True,
                inserted_card_sdxc_wp_engaged=False,
                format_trigger="MENU_MEDIA_FORMAT_DIALOG",
                format_mode="Full Format",
                delete_key_toggled_full_format=True,
            )
        )
        self.assertTrue(rep.passed)
        self.assertTrue(rep.format_requested)
        self.assertEqual(rep.effective_format_mode, "Full Format")

    def test_12_safe_slot2_format_while_slot1_vault_locked_passes(self) -> None:
        rep = evaluate_slot1_fullformat_and_chord_vault_firewall(
            Slot1FormatAndChordVaultFirewallSpec(
                target_slot=2,
                slot1_tier0_vault_active=True,
                off_camera_sha256_receipt_verified=True,
                sdxc_physical_wp_engaged=True,
                menu_delete_2s_chord_firewall_armed=True,
                inserted_card_sdxc_wp_engaged=False,
                format_trigger="MENU_MEDIA_FORMAT_DIALOG",
                format_mode="Quick Format",
            )
        )
        self.assertTrue(rep.passed)
        self.assertEqual(rep.target_slot, 2)
        self.assertEqual(rep.effective_format_mode, "Quick Format")

    def test_13_active_slot1_vault_missing_offcamera_receipt_or_wp_blocked(self) -> None:
        for kw in (
            {"off_camera_sha256_receipt_verified": False},
            {"sdxc_physical_wp_engaged": False, "cfexpress_readonly_bench_lock_engaged": False},
        ):
            with self.subTest(kw=kw):
                rep = evaluate_slot1_fullformat_and_chord_vault_firewall(
                    Slot1FormatAndChordVaultFirewallSpec(**kw)
                )
                self.assertFalse(rep.passed)
                self.assertEqual(rep.block_code, P229_BLOCKED_SLOT1_VAULT_MISSING_WP_OR_CHORD_FIREWALL)

    def test_14_active_slot1_vault_bad_sha256_hex_blocked(self) -> None:
        rep = evaluate_slot1_fullformat_and_chord_vault_firewall(
            Slot1FormatAndChordVaultFirewallSpec(off_camera_vault_sha256="not-a-valid-sha256")
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P229_BLOCKED_SLOT1_VAULT_MISSING_WP_OR_CHORD_FIREWALL)
        self.assertFalse(rep.off_camera_sha256_receipt_verified)

    def test_15_active_slot1_vault_chord_firewall_disarmed_blocked(self) -> None:
        rep = evaluate_slot1_fullformat_and_chord_vault_firewall(
            Slot1FormatAndChordVaultFirewallSpec(menu_delete_2s_chord_firewall_armed=False)
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P229_BLOCKED_SLOT1_VAULT_MISSING_WP_OR_CHORD_FIREWALL)

    def test_16_quick_format_on_active_slot1_vault_blocked(self) -> None:
        rep = evaluate_slot1_fullformat_and_chord_vault_firewall(
            Slot1FormatAndChordVaultFirewallSpec(
                slot1_tier0_vault_active=True,
                format_trigger="MENU_MEDIA_FORMAT_DIALOG",
                format_mode="Quick Format",
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P229_BLOCKED_QUICK_FORMAT_SLOT1_VAULT_WIPE)

    def test_17_quick_format_on_unverified_prior_vault_blocked(self) -> None:
        rep = evaluate_slot1_fullformat_and_chord_vault_firewall(
            Slot1FormatAndChordVaultFirewallSpec(
                slot1_tier0_vault_active=False,
                prior_tier0_vault_session=True,
                off_camera_sha256_receipt_verified=False,
                format_trigger="MENU_MEDIA_FORMAT_DIALOG",
                format_mode="Quick Format",
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P229_BLOCKED_QUICK_FORMAT_SLOT1_VAULT_WIPE)

    def test_18_delete_key_toggled_full_format_on_active_slot1_vault_blocked(self) -> None:
        rep = evaluate_slot1_fullformat_and_chord_vault_firewall(
            Slot1FormatAndChordVaultFirewallSpec(
                slot1_tier0_vault_active=True,
                format_trigger="MENU_MEDIA_FORMAT_DIALOG",
                format_mode="Quick Format",
                delete_key_toggled_full_format=True,
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.effective_format_mode, "Full Format")
        self.assertEqual(rep.block_code, P229_BLOCKED_DELETE_TOGGLE_FULL_FORMAT_SLOT1_VAULT_WIPE)

    def test_19_full_format_mid_cancel_on_active_slot1_vault_blocked(self) -> None:
        rep = evaluate_slot1_fullformat_and_chord_vault_firewall(
            Slot1FormatAndChordVaultFirewallSpec(
                slot1_tier0_vault_active=True,
                format_trigger="MENU_MEDIA_FORMAT_DIALOG",
                format_mode="Full Format",
                delete_key_toggled_full_format=True,
                full_format_canceled_mid_process=True,
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P229_BLOCKED_FULL_FORMAT_MID_CANCEL_DATA_ERASED_HAZARD)
        self.assertFalse(rep.mid_cancel_erasure_hazard_clear)

    def test_20_full_format_mid_cancel_assumed_preserved_or_unarchived_data_blocked(self) -> None:
        for extra in (
            {"mid_cancel_assumed_data_preserved": True},
            {"mid_cancel_card_usable_but_erased_acknowledged": False},
            {"target_slot_has_unarchived_data": True},
        ):
            with self.subTest(extra=extra):
                rep = evaluate_slot1_fullformat_and_chord_vault_firewall(
                    Slot1FormatAndChordVaultFirewallSpec(
                        slot1_tier0_vault_active=False,
                        prior_tier0_vault_session=True,
                        off_camera_sha256_receipt_verified=True,
                        sdxc_physical_wp_engaged=True,
                        vault_card_removed_or_swapped=True,
                        inserted_card_sdxc_wp_engaged=False,
                        format_trigger="MENU_MEDIA_FORMAT_DIALOG",
                        format_mode="Full Format",
                        delete_key_toggled_full_format=True,
                        full_format_canceled_mid_process=True,
                        **extra,
                    )
                )
                self.assertFalse(rep.passed)
                self.assertEqual(rep.block_code, P229_BLOCKED_FULL_FORMAT_MID_CANCEL_DATA_ERASED_HAZARD)

    def test_21_menu_plus_delete_2s_chord_on_active_slot1_vault_blocked(self) -> None:
        rep = evaluate_slot1_fullformat_and_chord_vault_firewall(
            Slot1FormatAndChordVaultFirewallSpec(
                slot1_tier0_vault_active=True,
                menu_plus_delete_chord_pressed=True,
                menu_plus_delete_hold_seconds=2.05,
            )
        )
        self.assertFalse(rep.passed)
        self.assertTrue(rep.chord_2s_triggered)
        self.assertEqual(rep.block_code, P229_BLOCKED_MENU_DELETE_2S_CHORD_SLOT1_VAULT_WIPE)

    def test_22_menu_plus_delete_sub_2s_short_press_does_not_trigger_chord(self) -> None:
        rep = evaluate_slot1_fullformat_and_chord_vault_firewall(
            Slot1FormatAndChordVaultFirewallSpec(
                slot1_tier0_vault_active=True,
                menu_plus_delete_chord_pressed=True,
                menu_plus_delete_hold_seconds=1.2,
            )
        )
        self.assertTrue(rep.passed)
        self.assertFalse(rep.chord_2s_triggered)
        self.assertFalse(rep.format_requested)

    def test_23_post_vault_slot1_format_without_vault_card_removal_blocked(self) -> None:
        rep = evaluate_slot1_fullformat_and_chord_vault_firewall(
            Slot1FormatAndChordVaultFirewallSpec(
                slot1_tier0_vault_active=False,
                prior_tier0_vault_session=True,
                off_camera_sha256_receipt_verified=True,
                sdxc_physical_wp_engaged=True,
                vault_card_removed_or_swapped=False,
                inserted_card_sdxc_wp_engaged=False,
                format_trigger="MENU_MEDIA_FORMAT_DIALOG",
                format_mode="Quick Format",
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P229_BLOCKED_MISSING_OFFCAMERA_SHA256_OR_WP_VAULT_REMOVAL)

    def test_24_inserted_sdxc_wp_switch_engaged_hardware_denies_format(self) -> None:
        rep = evaluate_slot1_fullformat_and_chord_vault_firewall(
            Slot1FormatAndChordVaultFirewallSpec(
                slot1_tier0_vault_active=False,
                prior_tier0_vault_session=True,
                off_camera_sha256_receipt_verified=True,
                sdxc_physical_wp_engaged=True,
                vault_card_removed_or_swapped=True,
                inserted_card_sdxc_wp_engaged=True,
                format_trigger="MENU_MEDIA_FORMAT_DIALOG",
                format_mode="Quick Format",
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P229_BLOCKED_SDXC_WP_SWITCH_ENGAGED_FORMAT_DENIED)

    def test_25_slot2_format_with_unguarded_slot1_vault_blocked(self) -> None:
        rep = evaluate_slot1_fullformat_and_chord_vault_firewall(
            Slot1FormatAndChordVaultFirewallSpec(
                target_slot=2,
                slot1_tier0_vault_active=True,
                off_camera_sha256_receipt_verified=False,
                inserted_card_sdxc_wp_engaged=False,
                format_trigger="MENU_MEDIA_FORMAT_DIALOG",
                format_mode="Quick Format",
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P229_BLOCKED_MISSING_OFFCAMERA_SHA256_OR_WP_VAULT_REMOVAL)

    def test_26_pillar34a_invalid_slot_or_overlay_escape_or_h0_h3_drift_or_unlock_blocked(self) -> None:
        self.assertEqual(
            evaluate_slot1_fullformat_and_chord_vault_firewall(
                Slot1FormatAndChordVaultFirewallSpec(target_slot=3)
            ).block_code,
            P229_BLOCKED_INVALID_FORMAT_SPEC,
        )
        self.assertEqual(
            evaluate_slot1_fullformat_and_chord_vault_firewall(
                Slot1FormatAndChordVaultFirewallSpec(slot1_vault_artifacts=("UNKNOWN.BIN",))
            ).block_code,
            P229_BLOCKED_INVALID_FORMAT_SPEC,
        )
        self.assertEqual(
            evaluate_slot1_fullformat_and_chord_vault_firewall(
                Slot1FormatAndChordVaultFirewallSpec(overlay_dir="/setting/format_overlay")
            ).block_code,
            P229_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
        )
        self.assertEqual(
            evaluate_slot1_fullformat_and_chord_vault_firewall(
                Slot1FormatAndChordVaultFirewallSpec(stage_b_backup_bin_writes=1)
            ).block_code,
            P229_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
        )
        self.assertEqual(
            evaluate_slot1_fullformat_and_chord_vault_firewall(
                Slot1FormatAndChordVaultFirewallSpec(persistent_write_unlock_requested=True)
            ).block_code,
            P229_BLOCKED_SAFETY_POLICY_VIOLATION,
        )

    def test_27_pillar34a_6_scenario_suite_all_pass(self) -> None:
        res = run_pillar34a_fullformat_chord_slot1_vault_6_scenario_suite()
        self.assertTrue(res.passed)
        self.assertEqual(res.status, P229_STATUS_VERIFIED_PILLAR_34A)
        self.assertEqual(res.scenarios_passed, 6)
        self.assertEqual(res.scenarios_total, 6)


class TestPillar34BZebraPersistenceHdmiIsolationAndSqRecovery(unittest.TestCase):
    def test_28_default_safe_zebra_custom1_camera_settings_reset_survival_passes(self) -> None:
        spec = build_default_safe_zebra_sq_recovery_spec()
        rep = evaluate_zebra_persistence_and_sq_transition_vault(spec)
        self.assertTrue(rep.passed)
        self.assertEqual(rep.status, P229_STATUS_VERIFIED_PILLAR_34B)
        self.assertIsNone(rep.block_code)
        self.assertTrue(rep.zebra_reset_persistence_verified)
        self.assertTrue(rep.hdmi_assist_zero_leak_verified)
        self.assertTrue(rep.fixed_variable_and_sq_lockouts_verified)
        self.assertTrue(rep.sq_transition_state_recovery_verified)
        self.assertTrue(rep.h0_equals_h3_verified)
        self.assertEqual(rep.tier0_surfaces_intact, 16)

    def test_29_all_10_zebra_level_presets_survive_camera_settings_reset(self) -> None:
        for preset in P229_ZEBRA_LEVEL_PRESETS:
            with self.subTest(preset=preset):
                rep = evaluate_zebra_persistence_and_sq_transition_vault(
                    ZebraPersistenceAndSqTransitionVaultSpec(
                        pre_reset_zebra_display="On",
                        pre_reset_zebra_level=preset,
                        reset_action="Camera Settings Reset",
                        post_reset_zebra_display="On",
                        post_reset_zebra_level=preset,
                        lcd_zebra_rendered=True,
                    )
                )
                self.assertTrue(rep.passed)

    def test_30_zebra_wiped_or_custom_drifted_across_camera_settings_reset_blocked(self) -> None:
        for kw in (
            {"post_reset_zebra_display": "Off", "lcd_zebra_rendered": False},
            {"post_reset_zebra_level": "70"},
            {"post_reset_custom1_std_level": 80},
            {"post_reset_custom1_range": 10},
            {"post_reset_custom2_lower_limit": 95},
        ):
            with self.subTest(kw=kw):
                rep = evaluate_zebra_persistence_and_sq_transition_vault(
                    ZebraPersistenceAndSqTransitionVaultSpec(**kw)
                )
                self.assertFalse(rep.passed)
                self.assertEqual(rep.block_code, P229_BLOCKED_ZEBRA_CAMERA_SETTINGS_RESET_DRIFT)

    def test_31_initialize_clears_zebra_display_off_and_level_70_passes(self) -> None:
        rep = evaluate_zebra_persistence_and_sq_transition_vault(
            ZebraPersistenceAndSqTransitionVaultSpec(
                pre_reset_zebra_display="On",
                pre_reset_zebra_level="100+",
                reset_action="Initialize",
                post_reset_zebra_display="Off",
                post_reset_zebra_level="70",
                lcd_zebra_rendered=False,
            )
        )
        self.assertTrue(rep.passed)
        self.assertTrue(rep.zebra_reset_persistence_verified)

    def test_32_initialize_retaining_custom_zebra_state_blocked(self) -> None:
        rep = evaluate_zebra_persistence_and_sq_transition_vault(
            ZebraPersistenceAndSqTransitionVaultSpec(
                pre_reset_zebra_display="On",
                pre_reset_zebra_level="Custom 2",
                reset_action="Initialize",
                post_reset_zebra_display="On",
                post_reset_zebra_level="Custom 2",
                lcd_zebra_rendered=True,
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P229_BLOCKED_ZEBRA_CAMERA_SETTINGS_RESET_DRIFT)

    def test_33_zebra_and_peaking_all_levels_colors_lcd_only_zero_hdmi_leak_passes(self) -> None:
        for lvl in P229_PEAKING_LEVELS:
            for col in P229_PEAKING_COLORS:
                for hdmi_info in ("Off", "On"):
                    with self.subTest(level=lvl, color=col, hdmi_info=hdmi_info):
                        rep = evaluate_zebra_persistence_and_sq_transition_vault(
                            ZebraPersistenceAndSqTransitionVaultSpec(
                                peaking_display="On",
                                peaking_level=lvl,
                                peaking_color=col,
                                hdmi_info_display=hdmi_info,
                                lcd_peaking_rendered=True,
                                hdmi_zebra_rendered=False,
                                hdmi_peaking_rendered=False,
                                hdmi_assist_leak_pixels=0,
                            )
                        )
                        self.assertTrue(rep.passed)

    def test_34_hdmi_zebra_or_peaking_or_pixel_leak_blocked(self) -> None:
        for kw in (
            {"hdmi_zebra_rendered": True},
            {"hdmi_peaking_rendered": True},
            {"hdmi_assist_leak_pixels": 64},
            {"lcd_zebra_rendered": False},
        ):
            with self.subTest(kw=kw):
                rep = evaluate_zebra_persistence_and_sq_transition_vault(
                    ZebraPersistenceAndSqTransitionVaultSpec(**kw)
                )
                self.assertFalse(rep.passed)
                self.assertEqual(rep.block_code, P229_BLOCKED_HDMI_ZEBRA_OR_PEAKING_ASSIST_LEAKAGE)

    def test_35_ver702_fixed_variable_mode_locks_legacy_sq_settings_menu(self) -> None:
        for kw in (
            {"legacy_sq_settings_menu_unlocked": True},
            {"fps_direct_control_enabled": False},
            {"sq_recording_active": True},
        ):
            with self.subTest(kw=kw):
                rep = evaluate_zebra_persistence_and_sq_transition_vault(
                    ZebraPersistenceAndSqTransitionVaultSpec(mode_settings="Fixed/Variable", **kw)
                )
                self.assertFalse(rep.passed)
                self.assertEqual(rep.block_code, P229_BLOCKED_FIXED_VARIABLE_LEGACY_SQ_MENU_CONFLICT)

    def test_36_sq_6_lockouts_enforced_audio_timing_tc_240fps4k_120fpsdci_proxy100(self) -> None:
        base = {
            "mode_settings": "S&Q",
            "sq_recording_active": True,
            "file_format": "XAVC S 4K",
            "rec_frame_rate": "23.98p",
            "sq_shooting_fps": 60,
        }
        violations = (
            {"sq_audio_channels_recorded": 2},
            {"sq_audio_out_timing_enabled": True},
            {"sq_time_code_run_enabled": True},
            {"sq_time_code_output_enabled": True},
            {"file_format": "XAVC HS 4K", "sq_shooting_fps": 240},
            {"file_format": "XAVC S 4K", "sq_shooting_fps": 200},
            {"file_format": "XAVC S-I DCI 4K", "sq_shooting_fps": 120},
            {"file_format": "XAVC S-I DCI 4K", "sq_shooting_fps": 100},
            {"sq_shooting_fps": 100, "sq_proxy_recording_active": True},
            {"rec_frame_rate": "119.88p", "sq_shooting_fps": 60, "sq_proxy_recording_active": True},
        )
        for bad in violations:
            merged = dict(base)
            merged.update(bad)
            with self.subTest(bad=bad):
                rep = evaluate_zebra_persistence_and_sq_transition_vault(
                    ZebraPersistenceAndSqTransitionVaultSpec(**merged)
                )
                self.assertFalse(rep.passed)
                self.assertEqual(rep.block_code, P229_BLOCKED_SQ_RECORDING_LOCKOUT_VIOLATION)

    def test_37_valid_sq_60fps_4k_with_proxy_on_passes(self) -> None:
        rep = evaluate_zebra_persistence_and_sq_transition_vault(
            ZebraPersistenceAndSqTransitionVaultSpec(
                mode_settings="S&Q",
                sq_recording_active=True,
                file_format="XAVC S 4K",
                rec_frame_rate="23.98p",
                sq_shooting_fps=60,
                sq_audio_channels_recorded=0,
                sq_audio_out_timing_enabled=False,
                sq_time_code_run_enabled=False,
                sq_time_code_output_enabled=False,
                sq_proxy_recording_active=True,
            )
        )
        self.assertTrue(rep.passed)
        self.assertTrue(rep.fixed_variable_and_sq_lockouts_verified)

    def test_38_sq_transition_recovery_live_and_lipsync_audio_tc_proxy_passes(self) -> None:
        for timing in ("Live", "Lip Sync"):
            for tc_run in ("Rec Run", "Free Run"):
                for tc_out in ("Off", "On"):
                    with self.subTest(timing=timing, tc_run=tc_run, tc_out=tc_out):
                        rep = evaluate_zebra_persistence_and_sq_transition_vault(
                            ZebraPersistenceAndSqTransitionVaultSpec(
                                saved_audio_out_timing=timing,
                                restored_audio_out_timing=timing,
                                saved_time_code_run=tc_run,
                                restored_time_code_run=tc_run,
                                saved_time_code_output=tc_out,
                                restored_time_code_output=tc_out,
                                saved_proxy_recording="On",
                                restored_proxy_recording="On",
                            )
                        )
                        self.assertTrue(rep.passed)

    def test_39_sq_transition_recovery_drift_or_119_88p_proxy_conflict_blocked(self) -> None:
        for kw in (
            {"saved_mode_settings": "Fixed/Variable", "restored_mode_settings": "S&Q"},
            {"saved_audio_out_timing": "Lip Sync", "restored_audio_out_timing": "Live"},
            {"saved_time_code_run": "Free Run", "restored_time_code_run": "Rec Run"},
            {"saved_time_code_output": "On", "restored_time_code_output": "Off"},
            {"saved_proxy_recording": "On", "restored_proxy_recording": "Off"},
            {"rec_frame_rate": "119.88p", "saved_proxy_recording": "On", "restored_proxy_recording": "On"},
        ):
            with self.subTest(kw=kw):
                rep = evaluate_zebra_persistence_and_sq_transition_vault(
                    ZebraPersistenceAndSqTransitionVaultSpec(**kw)
                )
                self.assertFalse(rep.passed)
                self.assertEqual(rep.block_code, P229_BLOCKED_SQ_TRANSITION_STATE_RECOVERY_DRIFT)

    def test_40_camset_all_10_slots_on_slot1_accepted_and_slot2_or_camset11_rejected(self) -> None:
        for fn in P229_CAMSET_FILENAMES:
            rep = evaluate_zebra_persistence_and_sq_transition_vault(
                ZebraPersistenceAndSqTransitionVaultSpec(camset_slot=1, camset_filename=fn)
            )
            self.assertTrue(rep.passed)
        self.assertEqual(
            evaluate_zebra_persistence_and_sq_transition_vault(
                ZebraPersistenceAndSqTransitionVaultSpec(camset_slot=2)
            ).block_code,
            P229_BLOCKED_SQ_TRANSITION_STATE_RECOVERY_DRIFT,
        )
        self.assertEqual(
            evaluate_zebra_persistence_and_sq_transition_vault(
                ZebraPersistenceAndSqTransitionVaultSpec(camset_filename="CAMSET11.DAT")
            ).block_code,
            P229_BLOCKED_SQ_TRANSITION_STATE_RECOVERY_DRIFT,
        )

    def test_41_pillar34b_overlay_escape_and_backup_h0_h3_drift_and_unlock_blocked(self) -> None:
        self.assertEqual(
            evaluate_zebra_persistence_and_sq_transition_vault(
                ZebraPersistenceAndSqTransitionVaultSpec(stage_b_overlay_dir="/dev/cnflasha/overlay")
            ).block_code,
            P229_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
        )
        self.assertEqual(
            evaluate_zebra_persistence_and_sq_transition_vault(
                ZebraPersistenceAndSqTransitionVaultSpec(tier0_surfaces_h0_h3_matched=15)
            ).block_code,
            P229_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
        )
        self.assertEqual(
            evaluate_zebra_persistence_and_sq_transition_vault(
                ZebraPersistenceAndSqTransitionVaultSpec(persistent_write_unlock_requested=True)
            ).block_code,
            P229_BLOCKED_SAFETY_POLICY_VIOLATION,
        )

    def test_42_pillar34b_invalid_zebra_custom_bounds_or_peaking_tokens_blocked(self) -> None:
        self.assertEqual(
            evaluate_zebra_persistence_and_sq_transition_vault(
                ZebraPersistenceAndSqTransitionVaultSpec(custom1_std_level=110)
            ).block_code,
            P229_BLOCKED_ZEBRA_CAMERA_SETTINGS_RESET_DRIFT,
        )
        self.assertEqual(
            evaluate_zebra_persistence_and_sq_transition_vault(
                ZebraPersistenceAndSqTransitionVaultSpec(custom1_range=21)
            ).block_code,
            P229_BLOCKED_ZEBRA_CAMERA_SETTINGS_RESET_DRIFT,
        )
        self.assertEqual(
            evaluate_zebra_persistence_and_sq_transition_vault(
                ZebraPersistenceAndSqTransitionVaultSpec(peaking_color="Green")
            ).block_code,
            P229_BLOCKED_HDMI_ZEBRA_OR_PEAKING_ASSIST_LEAKAGE,
        )

    def test_43_pillar34b_6_scenario_suite_all_pass(self) -> None:
        res = run_pillar34b_zebra_persistence_sq_recovery_6_scenario_suite()
        self.assertTrue(res.passed)
        self.assertEqual(res.status, P229_STATUS_VERIFIED_PILLAR_34B)
        self.assertEqual(res.scenarios_passed, 6)
        self.assertEqual(res.scenarios_total, 6)


class TestCombinedPillar34AndMaster34Aggregator(unittest.TestCase):
    def test_44_combined_verify_zebra_persistence_and_fullformat_chord_slot1_vault_both_modes(self) -> None:
        for clean in (False, True):
            with self.subTest(force_clean_room=clean):
                rep = verify_zebra_persistence_and_fullformat_chord_slot1_vault(force_clean_room=clean)
                self.assertTrue(rep.all_passed)
                self.assertTrue(rep.passed)
                self.assertEqual(rep.status, P229_STATUS_VERIFIED_PILLAR34_SUITE)
                self.assertTrue(rep.cnflasha_userspace_write_blocked)
                self.assertEqual(rep.otp_fuse_touches, 0)
                self.assertEqual(rep.rpmb_counter_increments, 0)
                self.assertEqual(rep.physical_device_writes, 0)
                self.assertFalse(rep.persistent_emmc_writes_authorized)
                self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_45_combined_verifier_propagates_34a_and_34b_failures(self) -> None:
        rep_a = verify_zebra_persistence_and_fullformat_chord_slot1_vault(
            format_vault_spec=Slot1FormatAndChordVaultFirewallSpec(
                format_trigger="MENU_PLUS_DELETE_2S_CHORD",
                menu_plus_delete_chord_pressed=True,
                menu_plus_delete_hold_seconds=2.5,
            ),
            force_clean_room=True,
        )
        self.assertFalse(rep_a.all_passed)
        self.assertTrue(len(rep_a.errors) >= 1)

        rep_b = verify_zebra_persistence_and_fullformat_chord_slot1_vault(
            zebra_sq_spec=ZebraPersistenceAndSqTransitionVaultSpec(hdmi_zebra_rendered=True),
            force_clean_room=True,
        )
        self.assertFalse(rep_b.all_passed)
        self.assertTrue(len(rep_b.errors) >= 1)

    def test_46_standalone_pillar34_suite_default_and_clean_room(self) -> None:
        rep_def = run_pillar34_standalone_suite()
        rep_cr = run_pillar34_standalone_suite(force_clean_room=True)
        for rep in (rep_def, rep_cr):
            self.assertTrue(rep.all_passed)
            self.assertEqual(rep.schema, PHASE229_SCHEMA)
            self.assertEqual(rep.version, PHASE229_VERSION)
            self.assertEqual(rep.pillar_34a_fullformat_chord_vault.scenarios_passed, 6)
            self.assertEqual(rep.pillar_34b_zebra_sq_recovery_vault.scenarios_passed, 6)
            self.assertEqual(len(rep.suite_sha256), 64)
        self.assertEqual(rep_cr.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_47_master_34pillar_default_mode_34_of_34_under_6s(self) -> None:
        rep = evaluate_realhw_34pillar_recovery_master()
        self.assertTrue(rep.all_passed)
        self.assertEqual(rep.status, P229_STATUS_VERIFIED_34OF34_AGGREGATOR)
        self.assertEqual(rep.pillar_count, 34)
        self.assertEqual(rep.pillars_passed, 34)
        self.assertEqual(rep.failed_pillars, ())
        self.assertTrue(rep.under_6s_budget)
        self.assertTrue(rep.cnflasha_userspace_write_blocked)
        self.assertEqual(rep.otp_fuse_touches, 0)
        self.assertEqual(rep.rpmb_counter_increments, 0)
        self.assertEqual(rep.physical_device_writes, 0)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_48_master_34pillar_clean_room_deterministic_sha256(self) -> None:
        r1 = evaluate_realhw_34pillar_recovery_master(force_clean_room=True)
        r2 = evaluate_realhw_34pillar_recovery_master(force_clean_room=True)
        self.assertTrue(r1.all_passed)
        self.assertEqual(r1.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(r1.master_34pillar_sha256, r2.master_34pillar_sha256)
        self.assertEqual(len(r1.master_34pillar_sha256), 64)

    def test_49_master_34pillar_symmetry_aliases(self) -> None:
        r_alias = evaluate_34pillar_recovery_master(force_clean_room=True)
        r_cli = verify_34pillar_recovery_suite(force_clean_room=True)
        self.assertEqual(r_alias.master_34pillar_sha256, r_cli.master_34pillar_sha256)
        self.assertEqual(r_alias.pillars_passed, 34)

    def test_50_master_34pillar_fault_injection_pillar_34(self) -> None:
        rep = evaluate_realhw_34pillar_recovery_master(
            force_clean_room=True,
            fault_inject_pillar="pillar_34_zebra_fullformat_chord_slot1_vault",
        )
        self.assertFalse(rep.all_passed)
        self.assertEqual(rep.status, P229_STATUS_FAIL_34OF34_AGGREGATOR)
        self.assertEqual(rep.pillars_passed, 33)
        self.assertEqual(rep.failed_pillars, ("pillar_34_zebra_fullformat_chord_slot1_vault",))

    def test_51_master_34pillar_fault_injection_pillar_1(self) -> None:
        first_id = MASTER_34_PILLAR_IDS[0]
        rep = evaluate_realhw_34pillar_recovery_master(
            force_clean_room=True,
            fault_inject_pillar=first_id,
        )
        self.assertFalse(rep.all_passed)
        self.assertEqual(rep.pillars_passed, 33)
        self.assertEqual(rep.failed_pillars, (first_id,))

    def test_52_master_34pillar_unknown_fault_inject_raises(self) -> None:
        with self.assertRaises(ValueError):
            evaluate_realhw_34pillar_recovery_master(
                force_clean_room=True,
                fault_inject_pillar="nonexistent_pillar_99",
            )

    def test_53_json_serialization_roundtrip(self) -> None:
        rep = evaluate_realhw_34pillar_recovery_master(force_clean_room=True)
        encoded = json.dumps(rep.to_dict(), sort_keys=True, allow_nan=False)
        decoded = json.loads(encoded)
        self.assertEqual(decoded["status"], P229_STATUS_VERIFIED_34OF34_AGGREGATOR)
        self.assertEqual(decoded["pillar_count"], 34)
        self.assertEqual(decoded["pillars_passed"], 34)


class TestBackwardCompatibilityAndCli(unittest.TestCase):
    def test_54_backward_compatibility_with_33pillar_master(self) -> None:
        rep33 = fx3_recovery.evaluate_realhw_33pillar_recovery_master(force_clean_room=True)
        self.assertTrue(rep33.all_passed)
        self.assertEqual(rep33.pillar_count, 33)
        self.assertEqual(rep33.pillars_passed, 33)

    def test_55_backward_compatibility_across_22_to_32_pillar_masters(self) -> None:
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

    def test_56_cli_verify_zebra_fullformat_chord_vault_json(self) -> None:
        proc = self._run_cli("verify-zebra-fullformat-chord-vault", "--json")
        self.assertEqual(proc.returncode, 0, msg=proc.stderr or proc.stdout)
        data = json.loads(proc.stdout)
        self.assertTrue(data["all_passed"])
        self.assertEqual(data["status"], P229_STATUS_VERIFIED_PILLAR34_SUITE)

    def test_57_cli_verify_zebra_fullformat_chord_vault_clean_room_summary(self) -> None:
        proc = self._run_cli("verify-zebra-fullformat-chord-vault", "--clean-room")
        self.assertEqual(proc.returncode, 0, msg=proc.stderr or proc.stdout)
        self.assertIn("status=VERIFIED_PILLAR34_ZEBRA_FULLFORMAT_CHORD_SLOT1_VAULT", proc.stdout)
        self.assertIn("mode=CLEAN_ROOM_SYNTHETIC", proc.stdout)
        self.assertIn("pillar_34a=6/6", proc.stdout)
        self.assertIn("pillar_34b=6/6", proc.stdout)

    def test_58_cli_verify_34pillar_recovery_normal_json(self) -> None:
        proc = self._run_cli("verify-34pillar-recovery", "--json")
        self.assertEqual(proc.returncode, 0, msg=proc.stderr or proc.stdout)
        data = json.loads(proc.stdout)
        self.assertTrue(data["all_passed"])
        self.assertEqual(data["status"], P229_STATUS_VERIFIED_34OF34_AGGREGATOR)
        self.assertEqual(data["pillar_count"], 34)
        self.assertEqual(data["pillars_passed"], 34)

    def test_59_cli_verify_34pillar_recovery_clean_room_env_and_flag(self) -> None:
        proc = self._run_cli(
            "verify-34pillar-recovery",
            "--force-clean-room",
            "--json",
            extra_env={"FX3_FX6_FORCE_CLEAN_ROOM": "1"},
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr or proc.stdout)
        data = json.loads(proc.stdout)
        self.assertEqual(data["verification_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(data["pillars_passed"], 34)

    def test_60_cli_verify_34pillar_recovery_out_directory(self) -> None:
        here = Path(__file__).resolve().parent
        out_dir = here / f"_tmp_p229_m34_{os.getpid()}"
        p34_dir = here / f"_tmp_p229_p34_{os.getpid()}"
        for d in (out_dir, p34_dir):
            if d.exists():
                shutil.rmtree(d)
        try:
            proc = self._run_cli("verify-34pillar-recovery", "--clean-room", "--out", str(out_dir))
            self.assertEqual(proc.returncode, 0, msg=proc.stderr or proc.stdout)
            report_file = out_dir / "34pillar-recovery-master-report.json"
            self.assertTrue(report_file.is_file())
            saved = json.loads(report_file.read_text(encoding="utf-8"))
            self.assertEqual(saved["status"], P229_STATUS_VERIFIED_34OF34_AGGREGATOR)
            self.assertEqual(saved["pillars_passed"], 34)

            proc_dup = self._run_cli("verify-34pillar-recovery", "--clean-room", "--out", str(out_dir))
            self.assertEqual(proc_dup.returncode, 2)

            proc_p34 = self._run_cli("verify-zebra-fullformat-chord-vault", "--clean-room", "--out", str(p34_dir))
            self.assertEqual(proc_p34.returncode, 0, msg=proc_p34.stderr or proc_p34.stdout)
            self.assertTrue((p34_dir / "pillar34-zebra-fullformat-chord-vault-report.json").is_file())
        finally:
            for d in (out_dir, p34_dir):
                if d.exists():
                    shutil.rmtree(d)


if __name__ == "__main__":
    unittest.main()
