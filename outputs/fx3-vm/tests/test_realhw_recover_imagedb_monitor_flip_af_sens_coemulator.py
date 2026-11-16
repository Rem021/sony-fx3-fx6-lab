#!/usr/bin/env python3
"""Unit tests for Phase 239 Stage 44 (`44/44` Milestone):
Real-Hardware `ILME-FX3` (`0x91030080`, `Ver. 2.00..7.02`) Wave-34 `[Recover Image DB]`
Depleted-Battery Refusal Before FAT/exFAT Write, Non-Deleting `AVF_INFO` Repair, Action-Item
Reset Immunity & Slot-1 Tier-0 Vault Read-Only Firewall, `[Monitor Flip Direction]` Survival
Across `[Camera Settings Reset]` & `[Horizontal Flip]` Playback Non-Inversion, and Movie/S&Q
AF Kinematics (`[AF Transition Speed]` `1..7` & `[AF Subj. Shift Sensitivity]` `1..5` Exact
Full Spelling) vs Still-Only `[Interval Shoot Func.]` HIL Co-Emulator.
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import contextlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import time
import unittest

FX3_VM_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = FX3_VM_DIR.parents[1]
if str(FX3_VM_DIR) not in sys.path:
    sys.path.insert(0, str(FX3_VM_DIR))

import fx3_vm_coemulation_suite as suite  # noqa: E402
import realhw_recover_imagedb_monitor_flip_af_sens_coemulator as p239  # noqa: E402


_CLEAN_ROOM_AUDIT_CACHE = None
_DEFAULT_AUDIT_CACHE = None
_CLEAN_SUITE_CACHE = None
_CLEAN_SUITE_ELAPSED = None
_DEFAULT_SUITE_CACHE = None
_DEFAULT_SUITE_ELAPSED = None


def _get_clean_room_audit():
    global _CLEAN_ROOM_AUDIT_CACHE
    if _CLEAN_ROOM_AUDIT_CACHE is None:
        _CLEAN_ROOM_AUDIT_CACHE = (
            p239.run_phase239_realhw_recover_imagedb_monitor_flip_af_sens_hil(
                force_clean_room=True
            )
        )
    return _CLEAN_ROOM_AUDIT_CACHE


def _get_default_audit():
    global _DEFAULT_AUDIT_CACHE
    if _DEFAULT_AUDIT_CACHE is None:
        _DEFAULT_AUDIT_CACHE = (
            p239.run_phase239_realhw_recover_imagedb_monitor_flip_af_sens_hil()
        )
    return _DEFAULT_AUDIT_CACHE


def _get_clean_room_suite():
    global _CLEAN_SUITE_CACHE, _CLEAN_SUITE_ELAPSED
    if _CLEAN_SUITE_CACHE is None:
        t0 = time.monotonic()
        _CLEAN_SUITE_CACHE = suite.run_fx3_vm_coemulation_suite(
            suite.CoEmulationConfig(force_clean_room=True)
        )
        _CLEAN_SUITE_ELAPSED = time.monotonic() - t0
    return _CLEAN_SUITE_CACHE, float(_CLEAN_SUITE_ELAPSED)


def _get_default_suite():
    global _DEFAULT_SUITE_CACHE, _DEFAULT_SUITE_ELAPSED
    if _DEFAULT_SUITE_CACHE is None:
        t0 = time.monotonic()
        _DEFAULT_SUITE_CACHE = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig())
        _DEFAULT_SUITE_ELAPSED = time.monotonic() - t0
    return _DEFAULT_SUITE_CACHE, float(_DEFAULT_SUITE_ELAPSED)


class TestPhase239RecoverImageDbMonitorFlipAfSensCoEmulator(unittest.TestCase):
    # ------------------------------------------------------------------
    # Group 1: Schema, Milestone 44/44 & O_RDONLY Donor Inspection (9)
    # ------------------------------------------------------------------
    def test_01_schema_version_stage_44_milestone_and_redline_constants(self) -> None:
        self.assertEqual(
            p239.SCHEMA_ID,
            "realhw_recover_imagedb_monitor_flip_af_sens_coemulator_v1",
        )
        self.assertEqual(p239.PHASE_239_SCHEMA, p239.SCHEMA_ID)
        self.assertEqual(p239.PHASE_239_VERSION, "239.0.0")
        self.assertEqual(p239.STAGE_INDEX, 44)
        self.assertEqual(p239.STAGE_TOTAL, 44)
        self.assertEqual(p239.MILESTONE_LABEL, "44/44")
        self.assertEqual(
            p239.STAGE_NAME,
            "stage44_realhw_recover_imagedb_monitor_flip_af_sens_hil",
        )
        self.assertEqual(p239.FX3_MODEL_ID, 0x91030080)
        self.assertTrue(p239.P8_CP_MUTATION_FORBIDDEN)
        self.assertTrue(p239.CNFLASHA_USERSPACE_WRITE_BLOCKED)
        self.assertEqual(p239.CNFLASHA_MUTATION_BYTES, 0)
        self.assertEqual(p239.PHYSICAL_DEVICE_WRITES, 0)
        self.assertFalse(p239.PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(p239.HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        self.assertFalse(p239.OVERALL_READY_FOR_HARDWARE_ATTACH)
        self.assertFalse(p239.ISP_WRITE_AUTHORIZED)
        self.assertFalse(p239.SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(p239.EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        self.assertEqual(p239.PHYSICAL_USB_PACKETS_EMITTED, 0)
        self.assertEqual(p239.OTP_FUSE_TOUCHES, 0)
        self.assertEqual(p239.RPMB_COUNTER_INCREMENTS, 0)
        self.assertEqual(p239.TIER0_SLOT1_UNVERIFIED_IMAGEDB_MUTATION_EVENTS, 0)
        self.assertEqual(p239.PLAYBACK_HORIZONTAL_FLIP_INVERSION_EVENTS, 0)
        self.assertEqual(p239.MONITOR_FLIP_OR_AF_KINEMATICS_DRIFT_EVENTS, 0)
        self.assertEqual(p239.RAW_FIRMWARE_BYTES_LEAKED, 0)
        self.assertEqual(p239.DONOR_ACCESS_MODE, "O_RDONLY")

    def test_02_donor_inspection_fast_sub_100ms_bounded_and_cached(self) -> None:
        p239._DONOR_AUDIT_CACHE.clear()
        t0 = time.monotonic()
        da1 = p239.inspect_phase239_donors(force_clean_room=False)
        dt1 = time.monotonic() - t0
        t1 = time.monotonic()
        da2 = p239.inspect_phase239_donors(force_clean_room=False)
        dt2 = time.monotonic() - t1

        self.assertTrue(da1.all_contracts_verified)
        self.assertEqual(da1.errors, ())
        self.assertEqual(da1.donor_files_inspected, 14)
        self.assertEqual(da1.raw_firmware_bytes_leaked, 0)
        self.assertEqual(da1.access_mode, "O_RDONLY")
        self.assertIn(da1.source_mode, ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"))
        self.assertEqual(da1, da2)
        self.assertLess(dt1, 0.50 if __import__("os").environ.get("GITHUB_ACTIONS") == "true" else 0.1)
        self.assertLess(dt2, 0.50 if __import__("os").environ.get("GITHUB_ACTIONS") == "true" else 0.02)

    def test_03_clean_room_donor_inspection_synthetic_parity(self) -> None:
        da = p239.inspect_phase239_donors(force_clean_room=True)
        self.assertEqual(da.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(da.all_contracts_verified)
        self.assertTrue(da.recover_imagedb_battery_and_vault_proven)
        self.assertTrue(da.monitor_flip_reset_and_playback_non_inversion_proven)
        self.assertTrue(da.af_kinematics_full_spelling_and_still_interval_proven)
        self.assertEqual(da.donor_files_inspected, 14)
        self.assertEqual(da.raw_firmware_bytes_leaked, 0)

    def test_04_env_force_clean_room_flag_variants(self) -> None:
        for truthy in ("1", "true", "TRUE", "yes", "on"):
            self.assertTrue(p239.is_forced_clean_room({p239.ENV_FORCE_CLEAN_ROOM: truthy}))
        for falsy in ("", "0", "false", "no", "off"):
            self.assertFalse(p239.is_forced_clean_room({p239.ENV_FORCE_CLEAN_ROOM: falsy}))

    def test_05_env_clean_room_sentinel_paths_never_touch_local_donors(self) -> None:
        paths = p239.resolve_phase239_donor_paths(env={p239.ENV_FORCE_CLEAN_ROOM: "1"})
        self.assertEqual(len(paths), 14)
        for p in paths.values():
            self.assertIn(p239.CLEAN_ROOM_SENTINEL_DIRNAME, str(p))
            self.assertFalse(p.exists())

    def test_06_missing_donor_directory_falls_back_to_clean_room_synthetic(self) -> None:
        env = {
            p239.ENV_MAC_WORK_ROOT: "/nonexistent_phase239_work_root_a",
            p239.ENV_MAIN_LAB_WORK_ROOT: "/nonexistent_phase239_work_root_b",
            p239.ENV_MAC_ROOT: "/nonexistent_phase239_mac_root",
        }
        da = p239.inspect_phase239_donors(force_clean_room=True, env=env)
        self.assertEqual(da.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(da.all_contracts_verified)

    def test_07_local_or_clean_donor_compact_and_window_markers_verified(self) -> None:
        da = p239.inspect_phase239_donors()
        self.assertTrue(da.fx3_imdb.elf64_le_ok)
        self.assertTrue(da.fx3_saveload.elf64_le_ok)
        self.assertTrue(da.fx3_media_cfg.elf64_le_ok)
        self.assertTrue(da.fx3_string_en_f.uxd_container_ok)
        self.assertTrue(da.fx6_string_en.uxd_container_ok)
        self.assertEqual(da.fx3_string_en_f.marker_hits["Recover Image DB"], 1)
        self.assertEqual(da.fx3_string_en_f.marker_hits["Monitor Flip Direction"], 1)
        self.assertEqual(da.fx3_string_en_f.marker_hits["Horizontal Flip"], 1)
        self.assertEqual(da.fx3_string_en_f.marker_hits["AF Transition Speed"], 1)
        self.assertEqual(da.fx3_string_en_f.marker_hits["AF Subj. Shift Sensitivity"], 1)
        self.assertEqual(da.fx3_string_en_f.marker_hits["1(Locked on)"], 1)
        self.assertEqual(da.fx3_string_en_f.marker_hits["5(Responsive)"], 1)
        self.assertEqual(da.fx3_string_en_f.marker_hits["Interval Shoot Func."], 1)
        self.assertEqual(da.fx6_string_en.marker_hits["AF Subj. Shift Sens."], 1)

    def test_08_large_donors_strictly_bounded_window_reads(self) -> None:
        da = p239.inspect_phase239_donors()
        for large in (
            da.fx3_appfw,
            da.fx6_appfw,
            da.fx3_cpapp,
            da.fx6_cpapp,
            da.fx3_libmpr,
            da.fx6_libmpr,
        ):
            self.assertTrue(large.bounded_windows_only)
            self.assertLessEqual(large.bytes_read_total, 10 * p239.BOUNDED_WINDOW_MAX_BYTES)
            self.assertTrue(all(v == 1 for v in large.window_hits.values()))

    def test_09_active_environment_mode_matches_clean_room_env_var(self) -> None:
        rep = _get_default_audit()
        self.assertTrue(rep["all_checks_passed"])
        if p239.is_forced_clean_room():
            self.assertEqual(rep["source_mode"], "CLEAN_ROOM_SYNTHETIC")
        else:
            self.assertIn(rep["source_mode"], ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"))

    # ------------------------------------------------------------------
    # Group 2: Sub-Model 44A — [Recover Image DB] Battery, Non-Deleting
    #          AVF_INFO Repair & Slot-1 Tier-0 Vault Firewall (14)
    # ------------------------------------------------------------------
    def test_10_extremely_depleted_battery_refused_before_any_fat_exfat_write(self) -> None:
        res = p239.probe_recover_imagedb_battery_and_vault_hil(
            target_slot="Slot 2",
            battery_state="extremely_depleted",
            battery_soc_pct=3,
            battery_mv=6100,
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p239.EAGAIN_ERRNO)
        self.assertTrue(res.hardware_refused_before_fat_exfat_write)
        self.assertEqual(res.card_metadata_sector_writes, 0)
        self.assertEqual(res.deleted_clip_or_still_count, 0)

    def test_11_low_soc_or_low_millivolts_refused_before_any_write(self) -> None:
        r_soc = p239.probe_recover_imagedb_battery_and_vault_hil(
            target_slot="Slot 2",
            battery_state="sufficient_charge",
            battery_soc_pct=8,
            battery_mv=7200,
        )
        r_mv = p239.probe_recover_imagedb_battery_and_vault_hil(
            target_slot="Slot 2",
            battery_state="sufficient_charge",
            battery_soc_pct=45,
            battery_mv=6300,
        )
        for r in (r_soc, r_mv):
            self.assertFalse(r.admitted)
            self.assertEqual(r.errno_code, p239.EAGAIN_ERRNO)
            self.assertTrue(r.hardware_refused_before_fat_exfat_write)
            self.assertEqual(r.card_metadata_sector_writes, 0)

    def test_12_slot2_scratch_repair_non_deleting_avf_info_and_mediapro_ok(self) -> None:
        res = p239.probe_recover_imagedb_battery_and_vault_hil(
            target_slot="Slot 2",
            battery_state="sufficient_charge",
            battery_soc_pct=85,
            battery_mv=7700,
            slot1_tier0_vault_present=True,
            imagedb_anomaly=p239.IMAGEDB_ANOMALY_DATABASE_ERROR,
            clips_before=42,
            stills_before=108,
            recordable_images_before_repair=0,
            recordable_images_after_repair_capacity=2400,
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.errno_code, 0)
        self.assertEqual(res.deleted_clip_or_still_count, 0)
        self.assertEqual(res.clips_after, 42)
        self.assertEqual(res.stills_after, 108)
        self.assertEqual(res.recordable_images_after_repair, 2400)
        self.assertEqual(res.repaired_avf_info_files, p239.REPAIRED_AVF_INFO_FILES)
        self.assertEqual(res.slot1_metadata_sector_writes, 0)
        self.assertEqual(res.tier0_slot1_unverified_imagedb_mutation_events, 0)

    def test_13_false_zero_recordable_images_anomaly_repaired_without_deletion(self) -> None:
        res = p239.probe_recover_imagedb_battery_and_vault_hil(
            target_slot="Slot 2",
            imagedb_anomaly=p239.IMAGEDB_ANOMALY_FALSE_ZERO_REMAINING,
            clips_before=19,
            stills_before=77,
            recordable_images_before_repair=0,
            recordable_images_after_repair_capacity=1650,
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.deleted_clip_or_still_count, 0)
        self.assertEqual(res.clips_after, 19)
        self.assertEqual(res.stills_after, 77)
        self.assertEqual(res.recordable_images_after_repair, 1650)

    def test_14_healthy_avf_info_index_verification_single_sector_sync(self) -> None:
        res = p239.probe_recover_imagedb_battery_and_vault_hil(
            target_slot="Slot 2",
            imagedb_anomaly=p239.IMAGEDB_ANOMALY_NONE,
            clips_before=5,
            stills_before=10,
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.card_metadata_sector_writes, 1)
        self.assertEqual(res.deleted_clip_or_still_count, 0)

    def test_15_attempt_to_delete_media_during_recover_imagedb_blocked_eopnotsupp(self) -> None:
        res = p239.probe_recover_imagedb_battery_and_vault_hil(
            target_slot="Slot 2",
            attempt_delete_media_during_recover=True,
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p239.EOPNOTSUPP_ERRNO)
        self.assertEqual(res.deleted_clip_or_still_count, 0)
        self.assertEqual(res.card_metadata_sector_writes, 0)

    def test_16_recover_imagedb_action_item_immunity_across_reset_and_initialize(self) -> None:
        for rst in (
            p239.RESET_ACTION_NONE,
            p239.RESET_ACTION_CAMERA_SETTINGS_RESET,
            p239.RESET_ACTION_INITIALIZE,
        ):
            res = p239.probe_recover_imagedb_battery_and_vault_hil(
                target_slot="Slot 2",
                reset_action=rst,
            )
            self.assertTrue(res.admitted)
            self.assertTrue(res.is_immediate_execution_action)
            self.assertFalse(res.reset_by_camera_settings_reset)
            self.assertFalse(res.reset_by_initialize)
            self.assertTrue(res.action_item_immune_to_reset_and_initialize)

    def test_17_slot1_tier0_vault_unverified_sha256_blocked_ebusy(self) -> None:
        res = p239.probe_recover_imagedb_battery_and_vault_hil(
            target_slot="Slot 1",
            battery_state="sufficient_charge",
            slot1_tier0_vault_present=True,
            off_camera_sha256_verified=False,
            sdxc_wp_switch_locked=False,
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p239.EBUSY_ERRNO)
        self.assertTrue(res.tier0_vault_firewall_engaged)
        self.assertEqual(res.slot1_metadata_sector_writes, 0)
        self.assertEqual(res.tier0_slot1_unverified_imagedb_mutation_events, 0)

    def test_18_slot1_tier0_vault_wp_locked_blocked_erofs(self) -> None:
        res = p239.probe_recover_imagedb_battery_and_vault_hil(
            target_slot="Slot 1",
            battery_state="sufficient_charge",
            slot1_tier0_vault_present=True,
            off_camera_sha256_verified=True,
            sdxc_wp_switch_locked=True,
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p239.EROFS_ERRNO)
        self.assertTrue(res.tier0_vault_firewall_engaged)
        self.assertEqual(res.slot1_metadata_sector_writes, 0)

    def test_19_slot1_active_tier0_vault_card_not_retired_blocked_ebusy(self) -> None:
        res = p239.probe_recover_imagedb_battery_and_vault_hil(
            target_slot="Slot 1",
            battery_state="sufficient_charge",
            slot1_tier0_vault_present=True,
            off_camera_sha256_verified=True,
            tier0_vault_card_retired_for_scratch=False,
            sdxc_wp_switch_locked=False,
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p239.EBUSY_ERRNO)
        self.assertTrue(res.tier0_vault_firewall_engaged)
        self.assertEqual(res.slot1_metadata_sector_writes, 0)

    def test_20_slot1_scratch_admitted_after_sha256_and_vault_card_retirement(self) -> None:
        res = p239.probe_recover_imagedb_battery_and_vault_hil(
            target_slot="Slot 1",
            battery_state="sufficient_charge",
            slot1_tier0_vault_present=True,
            off_camera_sha256_verified=True,
            tier0_vault_card_retired_for_scratch=True,
            sdxc_wp_switch_locked=False,
            clips_before=14,
            stills_before=22,
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.errno_code, 0)
        self.assertEqual(res.deleted_clip_or_still_count, 0)
        self.assertEqual(res.tier0_slot1_unverified_imagedb_mutation_events, 0)

    def test_21_slot2_wp_locked_sdxc_refused_erofs(self) -> None:
        res = p239.probe_recover_imagedb_battery_and_vault_hil(
            target_slot="Slot 2",
            sdxc_wp_switch_locked=True,
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p239.EROFS_ERRNO)
        self.assertEqual(res.card_metadata_sector_writes, 0)

    def test_22_recover_imagedb_invalid_parameters_rejected_einval(self) -> None:
        cases = (
            {"firmware_version": "1.00"},
            {"target_slot": "Slot 3"},
            {"battery_state": "unknown_charge"},
            {"imagedb_anomaly": "Bogus error"},
            {"reset_action": "Hard Wipe"},
            {"clips_before": -1},
            {"recordable_images_after_repair_capacity": 0},
        )
        for kwargs in cases:
            res = p239.probe_recover_imagedb_battery_and_vault_hil(**kwargs)
            self.assertFalse(res.admitted, msg=str(kwargs))
            self.assertEqual(res.errno_code, p239.EINVAL_ERRNO)

    def test_23_evaluate_pillar_a_summary_passes_all_invariants(self) -> None:
        pa = p239.evaluate_pillar_a_recover_imagedb_battery_and_vault_hil()
        self.assertTrue(pa["passed"])
        self.assertEqual(len(pa["repaired_avf_info_files"]), 4)
        self.assertIn("pnflasha", pa["tier0_vault_protected_artifacts"])
        self.assertIn("CAMSET01.DAT", pa["tier0_vault_protected_artifacts"])

    # ------------------------------------------------------------------
    # Group 3: Sub-Model 44B — [Monitor Flip Direction] Reset Survival &
    #          [Horizontal Flip] Playback Non-Inversion (12)
    # ------------------------------------------------------------------
    def test_24_all_4_monitor_flip_directions_survive_camera_settings_reset(self) -> None:
        for mode in ("Auto", "Horizontal Flip", "Vertical Flip", "Off"):
            res = p239.probe_monitor_flip_reset_and_playback_hil(
                configured_monitor_flip=mode,
                reset_action="Camera Settings Reset",
                screen_context="live_shooting",
            )
            self.assertTrue(res.admitted)
            self.assertEqual(res.effective_monitor_flip, mode)
            self.assertTrue(res.survived_camera_settings_reset)
            self.assertTrue(res.reset_only_by_initialize)
            self.assertFalse(res.cleared_to_auto_by_initialize)

    def test_25_initialize_restores_monitor_flip_direction_to_auto(self) -> None:
        for mode in ("Horizontal Flip", "Vertical Flip", "Off"):
            res = p239.probe_monitor_flip_reset_and_playback_hil(
                configured_monitor_flip=mode,
                reset_action="Initialize",
                screen_context="live_shooting",
            )
            self.assertTrue(res.admitted)
            self.assertEqual(res.effective_monitor_flip, "Auto")
            self.assertTrue(res.cleared_to_auto_by_initialize)
            self.assertFalse(res.survived_camera_settings_reset)

    def test_26_horizontal_flip_mirrors_live_shooting_local_lcd_only(self) -> None:
        res = p239.probe_monitor_flip_reset_and_playback_hil(
            configured_monitor_flip="Horizontal Flip",
            screen_context="live_shooting",
            hdmi_connected=True,
            hdmi_info_display="On",
        )
        self.assertTrue(res.admitted)
        self.assertTrue(res.live_shooting_lcd_horizontally_mirrored)
        self.assertFalse(res.live_shooting_lcd_vertically_flipped)
        self.assertFalse(res.external_hdmi_clean_feed_flipped)

    def test_27_vertical_flip_flips_live_shooting_local_lcd_vertically_only(self) -> None:
        res = p239.probe_monitor_flip_reset_and_playback_hil(
            configured_monitor_flip="Vertical Flip",
            screen_context="live_shooting",
            hdmi_connected=True,
            hdmi_info_display="On",
        )
        self.assertTrue(res.admitted)
        self.assertFalse(res.live_shooting_lcd_horizontally_mirrored)
        self.assertTrue(res.live_shooting_lcd_vertically_flipped)
        self.assertFalse(res.external_hdmi_clean_feed_flipped)

    def test_28_auto_flip_tracks_articulated_selfie_hinge_in_live_shooting(self) -> None:
        stowed = p239.probe_monitor_flip_reset_and_playback_hil(
            configured_monitor_flip="Auto",
            screen_context="live_shooting",
            panel_hinge_selfie_flipped=False,
        )
        articulated = p239.probe_monitor_flip_reset_and_playback_hil(
            configured_monitor_flip="Auto",
            screen_context="live_shooting",
            panel_hinge_selfie_flipped=True,
        )
        self.assertFalse(stowed.live_shooting_lcd_horizontally_mirrored)
        self.assertTrue(articulated.live_shooting_lcd_horizontally_mirrored)

    def test_29_off_disables_lcd_flip_even_when_panel_hinge_articulated(self) -> None:
        res = p239.probe_monitor_flip_reset_and_playback_hil(
            configured_monitor_flip="Off",
            screen_context="live_shooting",
            panel_hinge_selfie_flipped=True,
        )
        self.assertTrue(res.admitted)
        self.assertFalse(res.live_shooting_lcd_horizontally_mirrored)
        self.assertFalse(res.live_shooting_lcd_vertically_flipped)

    def test_30_horizontal_flip_playback_display_is_never_inverted(self) -> None:
        for rst in ("NONE", "Camera Settings Reset"):
            res = p239.probe_monitor_flip_reset_and_playback_hil(
                configured_monitor_flip="Horizontal Flip",
                reset_action=rst,
                screen_context="playback",
                hdmi_connected=True,
                hdmi_info_display="On",
            )
            self.assertTrue(res.admitted)
            self.assertEqual(res.effective_monitor_flip, "Horizontal Flip")
            self.assertFalse(res.playback_display_horizontally_inverted)
            self.assertTrue(res.playback_timecode_and_text_legible)
            self.assertEqual(res.playback_horizontal_flip_inversion_events, 0)
            self.assertFalse(res.external_hdmi_clean_feed_flipped)

    def test_31_forcing_playback_inversion_under_horizontal_flip_blocked_eopnotsupp(self) -> None:
        res = p239.probe_monitor_flip_reset_and_playback_hil(
            configured_monitor_flip="Horizontal Flip",
            screen_context="playback",
            attempt_invert_playback_under_horizontal_flip=True,
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p239.EOPNOTSUPP_ERRNO)
        self.assertEqual(res.playback_horizontal_flip_inversion_events, 0)

    def test_32_forcing_external_hdmi_clean_feed_flip_blocked_eopnotsupp(self) -> None:
        res = p239.probe_monitor_flip_reset_and_playback_hil(
            configured_monitor_flip="Horizontal Flip",
            attempt_flip_external_hdmi_feed=True,
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p239.EOPNOTSUPP_ERRNO)
        self.assertFalse(res.external_hdmi_clean_feed_flipped)

    def test_33_monitor_flip_supported_across_all_fx3_firmware_versions(self) -> None:
        for ver in p239.VALID_FX3_FIRMWARE_VERSIONS:
            res = p239.probe_monitor_flip_reset_and_playback_hil(
                firmware_version=ver,
                configured_monitor_flip="Horizontal Flip",
                screen_context="playback",
            )
            self.assertTrue(res.admitted)
            self.assertFalse(res.playback_display_horizontally_inverted)

    def test_34_monitor_flip_invalid_inputs_rejected_einval(self) -> None:
        cases = (
            {"firmware_version": "0.99"},
            {"configured_monitor_flip": "Mirror Both"},
            {"reset_action": "Factory Wipe"},
            {"screen_context": "menu_boot"},
            {"hdmi_info_display": "Auto"},
        )
        for kwargs in cases:
            res = p239.probe_monitor_flip_reset_and_playback_hil(**kwargs)
            self.assertFalse(res.admitted, msg=str(kwargs))
            self.assertEqual(res.errno_code, p239.EINVAL_ERRNO)

    def test_35_evaluate_pillar_b_summary_passes_all_invariants(self) -> None:
        pb = p239.evaluate_pillar_b_monitor_flip_reset_and_playback_hil()
        self.assertTrue(pb["passed"])
        self.assertEqual(pb["default_monitor_flip_direction"], "Auto")
        self.assertEqual(len(pb["four_mode_csr_survival_matrix"]), 4)

    # ------------------------------------------------------------------
    # Group 4: Sub-Model 44C — Movie/S&Q AF Kinematics (Exact Full Spelling)
    #          vs Still-Only [Interval Shoot Func.] (14)
    # ------------------------------------------------------------------
    def test_36_af_transition_speed_1_to_7_and_labels_verified(self) -> None:
        expected = {1: "1(Slow)", 5: "5", 7: "7(Fast)"}
        for step in range(1, 8):
            res = p239.probe_af_kinematics_and_interval_shoot_hil(
                capture_mode="movie",
                configured_af_transition_speed=step,
                configured_af_subj_shift_sensitivity=5,
            )
            self.assertTrue(res.admitted)
            self.assertEqual(res.effective_af_transition_speed, step)
            self.assertTrue(res.movie_or_sq_af_kinematics_active)
            if step in expected:
                self.assertEqual(res.effective_af_transition_speed_label, expected[step])

    def test_37_af_subj_shift_sensitivity_1_to_5_exact_full_spelling_verified(self) -> None:
        expected = {1: "1(Locked on)", 3: "3", 5: "5(Responsive)"}
        for step in range(1, 6):
            res = p239.probe_af_kinematics_and_interval_shoot_hil(
                capture_mode="s_and_q",
                af_subj_shift_menu_label="AF Subj. Shift Sensitivity",
                configured_af_transition_speed=5,
                configured_af_subj_shift_sensitivity=step,
            )
            self.assertTrue(res.admitted)
            self.assertEqual(res.af_subj_shift_menu_label, "AF Subj. Shift Sensitivity")
            self.assertEqual(res.effective_af_subj_shift_sensitivity, step)
            self.assertTrue(res.movie_or_sq_af_kinematics_active)
            if step in expected:
                self.assertEqual(res.effective_af_subj_shift_sensitivity_label, expected[step])

    def test_38_abbreviated_af_subj_shift_sens_labels_rejected_einval(self) -> None:
        for bad in (
            "AF Subj. Shift Sens.",
            "AF Subj. Shift Sens",
            "AF Subject Shift Sens.",
            "AF Subj Shift Sens.",
            "AF Subj. Sensitivity",
        ):
            res = p239.probe_af_kinematics_and_interval_shoot_hil(
                af_subj_shift_menu_label=bad,
            )
            self.assertFalse(res.admitted, msg=bad)
            self.assertEqual(res.errno_code, p239.EINVAL_ERRNO)

    def test_39_af_transition_speed_and_sensitivity_out_of_range_rejected_einval(self) -> None:
        for bad_speed in (0, 8, -1, True):
            res = p239.probe_af_kinematics_and_interval_shoot_hil(
                configured_af_transition_speed=bad_speed,  # type: ignore[arg-type]
            )
            self.assertFalse(res.admitted)
            self.assertEqual(res.errno_code, p239.EINVAL_ERRNO)

        for bad_sens in (0, 6, -2, False):
            res = p239.probe_af_kinematics_and_interval_shoot_hil(
                configured_af_subj_shift_sensitivity=bad_sens,  # type: ignore[arg-type]
            )
            self.assertFalse(res.admitted)
            self.assertEqual(res.errno_code, p239.EINVAL_ERRNO)

    def test_40_asymmetric_camera_settings_reset_resets_af_while_monitor_flip_survives(self) -> None:
        res = p239.probe_af_kinematics_and_interval_shoot_hil(
            capture_mode="movie",
            configured_af_transition_speed=1,
            configured_af_subj_shift_sensitivity=1,
            configured_monitor_flip="Horizontal Flip",
            reset_action="Camera Settings Reset",
        )
        self.assertTrue(res.admitted)
        self.assertTrue(res.af_kinematics_reset_by_camera_settings_reset)
        self.assertTrue(res.monitor_flip_survived_while_af_kinematics_reset_verified)
        self.assertEqual(res.effective_af_transition_speed, 5)
        self.assertEqual(res.effective_af_subj_shift_sensitivity, 5)
        self.assertEqual(res.effective_af_subj_shift_sensitivity_label, "5(Responsive)")
        self.assertEqual(res.effective_monitor_flip, "Horizontal Flip")
        self.assertEqual(res.monitor_flip_or_af_kinematics_drift_events, 0)

    def test_41_three_step_monitor_flip_vs_af_kinematics_reset_lifecycle(self) -> None:
        lc = p239.simulate_monitor_flip_vs_af_kinematics_reset_lifecycle(
            configured_monitor_flip="Vertical Flip",
            configured_af_transition_speed=2,
            configured_af_subj_shift_sensitivity=1,
        )
        self.assertTrue(lc["lifecycle_verified"])
        self.assertEqual(lc["step2_camera_settings_reset_split"]["effective_monitor_flip"], "Vertical Flip")
        self.assertEqual(lc["step2_camera_settings_reset_split"]["effective_af_transition_speed"], 5)
        self.assertEqual(lc["step3_initialize_full_clear"]["effective_monitor_flip"], "Auto")

    def test_42_slot1_camset01_to_camset10_restore_af_kinematics_zero_nvram_writes(self) -> None:
        for slot_file in ("CAMSET01.DAT", "CAMSET05.DAT", "CAMSET10.DAT"):
            res = p239.probe_af_kinematics_and_interval_shoot_hil(
                capture_mode="movie",
                configured_monitor_flip="Horizontal Flip",
                reset_action="Camera Settings Reset",
                restore_from_slot1_camset=slot_file,
                saved_camset_af_transition_speed=3,
                saved_camset_af_subj_shift_sensitivity=2,
            )
            self.assertTrue(res.admitted)
            self.assertEqual(res.slot1_camset_restored, slot_file)
            self.assertEqual(res.effective_af_transition_speed, 3)
            self.assertEqual(res.effective_af_subj_shift_sensitivity, 2)
            self.assertEqual(res.bk4_persistent_nvram_writes, 0)

    def test_43_invalid_slot1_camset_filename_rejected_einval(self) -> None:
        for bad_camset in ("CAMSET00.DAT", "CAMSET11.DAT", "../CAMSET01.DAT", "FX6_ALL.DAT"):
            res = p239.probe_af_kinematics_and_interval_shoot_hil(
                restore_from_slot1_camset=bad_camset,
            )
            self.assertFalse(res.admitted)
            self.assertEqual(res.errno_code, p239.EINVAL_ERRNO)

    def test_44_forcing_movie_af_kinematics_in_still_mode_blocked_eopnotsupp(self) -> None:
        res = p239.probe_af_kinematics_and_interval_shoot_hil(
            capture_mode="still",
            attempt_movie_af_kinematics_in_still_mode=True,
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p239.EOPNOTSUPP_ERRNO)

    def test_45_still_only_interval_shoot_func_boundary_1s_to_99m59s_and_60s_ok(self) -> None:
        for start_s, period_s, shots, fmt in (
            (1, 1, 1, "JPEG"),
            (5999, 60, 9999, "RAW & HEIF"),
            (10, 5, 300, "RAW"),
        ):
            res = p239.probe_af_kinematics_and_interval_shoot_hil(
                capture_mode="still",
                interval_shoot_enabled="On",
                interval_target_domain="still_image_sequence",
                still_image_format=fmt,
                shooting_start_time_s=start_s,
                shooting_interval_s=period_s,
                number_of_shots=shots,
            )
            self.assertTrue(res.admitted)
            self.assertFalse(res.movie_or_sq_af_kinematics_active)
            self.assertFalse(res.in_camera_timelapse_movie_generated)
            self.assertEqual(res.post_capture_assembler, "Imaging Edge Desktop (Viewer)")

    def test_46_fx6_video_interval_rec_mxf_mp4_conflation_blocked_eopnotsupp(self) -> None:
        r1 = p239.probe_af_kinematics_and_interval_shoot_hil(
            capture_mode="movie",
            interval_shoot_enabled="On",
            attempt_in_camera_video_interval_rec_mxf_mp4=True,
        )
        r2 = p239.probe_af_kinematics_and_interval_shoot_hil(
            capture_mode="still",
            interval_shoot_enabled="On",
            interval_target_domain="in_camera_mxf_mp4_video_interval_rec",
        )
        r3 = p239.probe_af_kinematics_and_interval_shoot_hil(
            capture_mode="movie",
            interval_shoot_enabled="On",
        )
        for r in (r1, r2, r3):
            self.assertFalse(r.admitted)
            self.assertEqual(r.errno_code, p239.EOPNOTSUPP_ERRNO)
            self.assertFalse(r.in_camera_timelapse_movie_generated)

    def test_47_interval_shoot_out_of_range_timings_rejected_einval(self) -> None:
        cases = (
            {"shooting_start_time_s": 0},
            {"shooting_start_time_s": 6000},
            {"shooting_interval_s": 0},
            {"shooting_interval_s": 61},
            {"number_of_shots": 0},
            {"number_of_shots": 10000},
        )
        for kw in cases:
            res = p239.probe_af_kinematics_and_interval_shoot_hil(
                capture_mode="still",
                interval_shoot_enabled="On",
                **kw,
            )
            self.assertFalse(res.admitted, msg=str(kw))
            self.assertEqual(res.errno_code, p239.EINVAL_ERRNO)

    def test_48_af_and_interval_invalid_modes_rejected_einval(self) -> None:
        for kw in (
            {"firmware_version": "9.99"},
            {"capture_mode": "panoramic"},
            {"configured_monitor_flip": "Diagonal"},
            {"interval_shoot_enabled": "Auto"},
            {"still_image_format": "MXF"},
        ):
            res = p239.probe_af_kinematics_and_interval_shoot_hil(**kw)
            self.assertFalse(res.admitted, msg=str(kw))
            self.assertEqual(res.errno_code, p239.EINVAL_ERRNO)

    def test_49_evaluate_pillar_c_d_summary_passes_all_invariants(self) -> None:
        pcd = p239.evaluate_pillar_c_d_af_kinematics_interval_and_redlines()
        self.assertTrue(pcd["passed"])
        self.assertEqual(pcd["exact_fx3_af_subj_shift_menu_label"], "AF Subj. Shift Sensitivity")
        self.assertEqual(len(pcd["af_transition_7step_matrix"]), 7)
        self.assertEqual(len(pcd["af_subj_shift_5step_matrix"]), 5)

    # ------------------------------------------------------------------
    # Group 5: Hard Safety Redlines, Digest, CLI, Suite Stage 44 & Hygiene (11)
    # ------------------------------------------------------------------
    def test_50_hard_safety_redline_guard_baseline_and_all_10_violations_blocked(self) -> None:
        ok = p239.probe_hard_safety_redline()
        self.assertTrue(ok.valid)
        self.assertFalse(ok.persistent_emmc_writes_authorized)
        self.assertFalse(ok.hardware_live_attachment_authorized)
        self.assertFalse(ok.overall_ready_for_hardware_attach)
        self.assertFalse(ok.isp_write_authorized)
        self.assertTrue(ok.cnflasha_userspace_write_blocked)

        flags = (
            "persistent_emmc_writes_authorized",
            "hardware_live_attachment_authorized",
            "overall_ready_for_hardware_attach",
            "spi_nor_write_authorized",
            "el3_payload_transmit_authorized",
            "isp_write_authorized",
            "cnflasha_userspace_write_attempt",
            "bypass_slot1_tier0_imagedb_firewall",
            "force_playback_horizontal_flip_inversion",
            "force_monitor_flip_or_af_kinematics_drift",
        )
        for flg in flags:
            blk = p239.probe_hard_safety_redline(**{flg: True})
            self.assertFalse(blk.valid, msg=flg)
            self.assertIn(flg, blk.blocked_action)
            self.assertFalse(blk.persistent_emmc_writes_authorized)
            self.assertFalse(blk.hardware_live_attachment_authorized)
            self.assertFalse(blk.overall_ready_for_hardware_attach)
            self.assertFalse(blk.isp_write_authorized)
            self.assertEqual(blk.cnflasha_mutation_bytes, 0)
            self.assertEqual(blk.physical_device_writes, 0)

    def test_51_multi_redline_violations_joined_deterministically(self) -> None:
        blk = p239.probe_hard_safety_redline(
            persistent_emmc_writes_authorized=True,
            bypass_slot1_tier0_imagedb_firewall=True,
            force_playback_horizontal_flip_inversion=True,
        )
        self.assertFalse(blk.valid)
        self.assertEqual(
            blk.blocked_action,
            "persistent_emmc_writes_authorized+bypass_slot1_tier0_imagedb_firewall+"
            "force_playback_horizontal_flip_inversion",
        )

    def test_52_deterministic_audit_digest_in_both_donor_and_clean_room_modes(self) -> None:
        c1 = _get_clean_room_audit()
        c2 = p239.run_phase239_realhw_recover_imagedb_monitor_flip_af_sens_hil(
            force_clean_room=True
        )
        self.assertEqual(c1["audit_digest_sha256"], c2["audit_digest_sha256"])
        self.assertEqual(c1["milestone"], "44/44")

        d1 = _get_default_audit()
        d2 = p239.run_phase239_realhw_recover_imagedb_monitor_flip_af_sens_hil()
        self.assertEqual(d1["audit_digest_sha256"], d2["audit_digest_sha256"])
        self.assertEqual(d1["redlines"]["raw_firmware_bytes_leaked"], 0)

    def test_53_standalone_cli_self_test_summary_and_clean_room_json(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        script_path = str(
            FX3_VM_DIR / "realhw_recover_imagedb_monitor_flip_af_sens_coemulator.py"
        )
        p_sum = subprocess.run(
            [sys.executable, "-B", script_path, "--self-test", "--summary"],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(p_sum.returncode, 0, msg=p_sum.stderr)
        self.assertIn("[PASS] Phase 239 Stage 44 (44/44)", p_sum.stdout)

        p_json = subprocess.run(
            [sys.executable, "-B", script_path, "--self-test", "--clean-room", "--json"],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(p_json.returncode, 0, msg=p_json.stderr)
        parsed = json.loads(p_json.stdout)
        self.assertTrue(parsed["all_checks_passed"])
        self.assertEqual(parsed["schema"], p239.SCHEMA_ID)
        self.assertEqual(parsed["stage_index"], 44)
        self.assertEqual(parsed["milestone"], "44/44")

    def test_54_inprocess_main_summary_and_json_exit_zero(self) -> None:
        buf_sum = io.StringIO()
        with contextlib.redirect_stdout(buf_sum):
            rc_sum = p239.main(["--self-test", "--clean-room", "--summary"])
        self.assertEqual(rc_sum, 0)
        self.assertIn("[PASS] Phase 239 Stage 44 (44/44)", buf_sum.getvalue())

        buf_json = io.StringIO()
        with contextlib.redirect_stdout(buf_json):
            rc_json = p239.main(["--self-test", "--clean-room", "--json"])
        self.assertEqual(rc_json, 0)
        data = json.loads(buf_json.getvalue())
        self.assertEqual(data["source_mode"], "CLEAN_ROOM_SYNTHETIC")

    def test_55_fx3_vm_coemulation_suite_includes_stage44_and_44_stage_count(self) -> None:
        rep_on, dt_clean = _get_clean_room_suite()
        self.assertTrue(rep_on["all_checks_passed"])
        self.assertLess(dt_clean, 4.0)
        self.assertIn(
            "stage44_realhw_recover_imagedb_monitor_flip_af_sens_hil",
            rep_on,
        )
        s44 = rep_on["stage44_realhw_recover_imagedb_monitor_flip_af_sens_hil"]
        self.assertTrue(s44["all_checks_passed"])
        self.assertEqual(s44["schema"], p239.SCHEMA_ID)
        self.assertEqual(s44["milestone"], "44/44")
        self.assertFalse(s44["persistent_emmc_writes_authorized"])
        self.assertFalse(s44["hardware_live_attachment_authorized"])
        self.assertFalse(s44["overall_ready_for_hardware_attach"])
        self.assertFalse(s44["isp_write_authorized"])
        self.assertFalse(s44["spi_nor_write_authorized"])
        self.assertFalse(s44["el3_payload_transmit_authorized"])
        self.assertTrue(s44["cnflasha_userspace_write_blocked"])
        self.assertEqual(s44["cnflasha_mutation_bytes"], 0)
        self.assertEqual(s44["physical_device_writes"], 0)
        self.assertEqual(s44["tier0_slot1_unverified_imagedb_mutation_events"], 0)
        self.assertEqual(s44["playback_horizontal_flip_inversion_events"], 0)
        self.assertEqual(s44["monitor_flip_or_af_kinematics_drift_events"], 0)
        self.assertEqual(s44["raw_firmware_bytes_leaked"], 0)

        stage_keys = [k for k in rep_on if re.match(r"^stage\d+_", k)]
        self.assertGreaterEqual(len(stage_keys), 44)

    def test_56_fx3_vm_coemulation_suite_skip_stage44_and_skip_phase239_config(self) -> None:
        rep_skip_p239 = suite.run_fx3_vm_coemulation_suite(
            suite.CoEmulationConfig(
                force_clean_room=True,
                include_phase239_realhw_recover_imagedb_monitor_flip_af_sens_hil=False,
            )
        )
        self.assertTrue(rep_skip_p239["all_checks_passed"])
        self.assertNotIn(
            "stage44_realhw_recover_imagedb_monitor_flip_af_sens_hil",
            rep_skip_p239,
        )

        rep_skip_s44 = suite.run_fx3_vm_coemulation_suite(
            suite.CoEmulationConfig(
                force_clean_room=True,
                include_stage44=False,
            )
        )
        self.assertTrue(rep_skip_s44["all_checks_passed"])
        self.assertNotIn(
            "stage44_realhw_recover_imagedb_monitor_flip_af_sens_hil",
            rep_skip_s44,
        )

    def test_57_fx3_vm_coemulation_suite_default_mode_and_include_stage44_cli(self) -> None:
        rep_def, dt_def = _get_default_suite()
        self.assertTrue(rep_def["all_checks_passed"])
        self.assertLess(dt_def, 8.0)
        s44 = rep_def["stage44_realhw_recover_imagedb_monitor_flip_af_sens_hil"]
        self.assertTrue(s44["all_checks_passed"])
        stage_keys = [k for k in rep_def if re.match(r"^stage\d+_", k)]
        self.assertGreaterEqual(len(stage_keys), 44)

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = suite.main(["--clean-room", "--include-stage44", "--summary"])
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("[PASS] Phase 33 FX3-VM Co-Emulation", out)
        self.assertIn(
            "realhw_recover_imagedb_monitor_flip_af_sens_hil=CLEAN_ROOM_SYNTHETIC("
            "imagedb_del=0,t0_mut=0,flip=4m,pb_inv=0,csr_split=1,emmc_wr=0)",
            out,
        )

    def test_58_fx3_vm_coemulation_suite_cli_skip_phase239_and_skip_stage44(self) -> None:
        for flag in ("--skip-phase239", "--skip-stage44", "--no-include-stage44"):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = suite.main(["--clean-room", flag, "--summary"])
            self.assertEqual(rc, 0, msg=flag)
            self.assertNotIn(
                "realhw_recover_imagedb_monitor_flip_af_sens_hil=",
                buf.getvalue(),
                msg=flag,
            )

    def test_59_source_hygiene_no_write_flags_no_port_8768_and_readme_documented(self) -> None:
        src = (
            FX3_VM_DIR / "realhw_recover_imagedb_monitor_flip_af_sens_coemulator.py"
        ).read_text(encoding="utf-8")
        forbidden_wronly = "O_" + "WRONLY"
        forbidden_rdwr = "O_" + "RDWR"
        forbidden_port = "87" + "68"
        self.assertNotIn(forbidden_wronly, src)
        self.assertNotIn(forbidden_rdwr, src)
        self.assertNotIn(forbidden_port, src)
        self.assertIn("os.O_RDONLY", src)

        readme = (FX3_VM_DIR / "README.md").read_text(encoding="utf-8")
        self.assertIn(
            "realhw_recover_imagedb_monitor_flip_af_sens_coemulator.py",
            readme,
        )
        self.assertIn("44/44", readme)
        self.assertIn("--include-stage44", readme)
        self.assertIn("--skip-phase239", readme)

    def test_60_zero_pyc_bytecode_artifacts_in_fx3_vm(self) -> None:
        pyc_files = list(FX3_VM_DIR.rglob("*.pyc"))
        self.assertEqual(pyc_files, [])


if __name__ == "__main__":
    unittest.main()
