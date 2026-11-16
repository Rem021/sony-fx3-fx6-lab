#!/usr/bin/env python3
"""Phase 71 Test Suite — Stage 10 Dual-Slot Relay/Simul/Sort Proxy,
`NonRealTimeMeta.xml` Sidecar & `USB-PD -> NP-FZ100` UPS / `.RSV` Salvage Co-Emulator.

Exercises 34 fast unit, protocol, XML/RTMD, power-loss/salvage, Stage 10 suite
integration, CLI, and source-hygiene tests across BOTH Local Donor (`os.O_RDONLY`)
and `FX3_FX6_FORCE_CLEAN_ROOM=1` modes, strictly offline.
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import contextlib
import hashlib
import io
import json
import os
import subprocess
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
FX3_VM_DIR = TESTS_DIR.parent
REPO_ROOT = FX3_VM_DIR.parents[1]
if str(FX3_VM_DIR) not in sys.path:
    sys.path.insert(0, str(FX3_VM_DIR))

import dualslot_proxy_ups_salvage_emulator as p71  # noqa: E402
import fx3_vm_coemulation_suite as suite  # noqa: E402
import tc_genlock_lens_paint_emulator as p67  # noqa: E402


_AUDIT_CACHE: dict = {}


def _get_clean_room_audit() -> dict:
    if "clean_room" not in _AUDIT_CACHE:
        _AUDIT_CACHE["clean_room"] = p71.run_phase71_dualslot_ups_salvage_audit(force_clean_room=True)
    return _AUDIT_CACHE["clean_room"]


class TestPhase71DonorAuditAndRedlines(unittest.TestCase):
    """Verify O_RDONLY donor audit, clean-room fallback, and zero-mutation redlines."""

    def test_01_clean_room_donor_audit_verifies_all_10_artifacts_and_sha256(self) -> None:
        audit = p71.inspect_dualslot_ups_donors(force_clean_room=True)
        self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(audit.access_mode, "O_RDONLY")
        self.assertEqual(audit.donor_files_inspected, 0)
        self.assertTrue(audit.all_contracts_verified)
        self.assertEqual(len(audit.checked_markers), 10)
        self.assertEqual(audit.missing_markers, ())
        for key, (expected_bytes, expected_sha) in p71.PINNED_DONOR_SHA256.items():
            self.assertEqual(audit.bytes_by_artifact[key], expected_bytes)
            self.assertEqual(audit.sha256_by_artifact[key], expected_sha)

    def test_02_force_clean_room_env_disables_local_donor_paths(self) -> None:
        env = {p71.ENV_FORCE_CLEAN_ROOM: "1"}
        self.assertTrue(p71.is_forced_clean_room(env))
        paths = p71.resolve_phase71_donor_paths(env=env)
        self.assertEqual(len(paths), 10)
        for path in paths.values():
            self.assertIn(p71.CLEAN_ROOM_SENTINEL_DIRNAME, str(path))
        audit = p71.inspect_dualslot_ups_donors(env=env)
        self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_03_local_donor_o_rdonly_audit_when_present_or_clean_room(self) -> None:
        if p71.is_forced_clean_room():
            audit = p71.inspect_dualslot_ups_donors()
            self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")
            return
        paths = p71.resolve_phase71_donor_paths()
        audit = p71.inspect_dualslot_ups_donors()
        self.assertTrue(audit.all_contracts_verified)
        if all(p.is_file() for p in paths.values()):
            self.assertEqual(audit.source_mode, "LOCAL_DONOR_RDONLY")
            self.assertEqual(audit.donor_files_inspected, 10)
            for key, (expected_bytes, expected_sha) in p71.PINNED_DONOR_SHA256.items():
                self.assertEqual(audit.bytes_by_artifact[key], expected_bytes)
                self.assertEqual(audit.sha256_by_artifact[key], expected_sha)
        else:
            self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_04_missing_donor_root_falls_back_to_clean_room(self) -> None:
        env = {
            p71.ENV_MAC_WORK_ROOT: "/nonexistent_phase71_mac_work_root",
            p71.ENV_MAIN_LAB_WORK_ROOT: "/nonexistent_phase71_main_work_root",
        }
        audit = p71.inspect_dualslot_ups_donors(force_clean_room=True, env=env)
        self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(audit.all_contracts_verified)

    def test_05_redlines_zero_mutations_zero_emmc_and_c2pa_untouched(self) -> None:
        rep = _get_clean_room_audit()
        red = rep["redlines"]
        self.assertTrue(red["p8_cp_mutation_forbidden"])
        self.assertEqual(red["nop_count"], 0)
        self.assertEqual(red["guest_code_modification_bytes"], 0)
        self.assertEqual(red["cp_mutation_bytes"], 0)
        self.assertEqual(red["wbi_mutation_bytes"], 0)
        self.assertEqual(red["calibration_mutation_bytes"], 0)
        self.assertEqual(red["nvram_persistent_writes"], 0)
        self.assertEqual(red["physical_device_writes"], 0)
        self.assertEqual(red["p1_emmc_mutations"], 0)
        self.assertEqual(red["internal_emmc_writes"], 0)
        self.assertTrue(red["c2pa_license_untouched"])
        self.assertFalse(red["persistent_emmc_writes_authorized"])
        self.assertEqual(red["donor_access_mode"], "O_RDONLY")


class TestDualSlotRelaySimulSortFifo(unittest.TestCase):
    """Verify 256 MiB DRAM Elastic FIFO Relay rollover, Simultaneous yank, and Sort S&Q suspend."""

    def test_06_relay_auto_switch_85ms_zero_dropped_frames_and_moov_finalized(self) -> None:
        res = p71.simulate_dual_slot_ring_recording(
            mode=p71.SLOT_MODE_RELAY,
            total_frames=120,
            slot_a_capacity_frames=60,
            slot_b_capacity_frames=240,
            relay_switch_latency_ms=85.0,
        )
        self.assertTrue(res.passed)
        self.assertEqual(res.fifo_capacity_bytes, 256 * 1024 * 1024)
        self.assertEqual(res.dropped_frames, 0)
        self.assertEqual(res.main_written_frames, 120)
        self.assertEqual(res.slot_a_frames, 60)
        self.assertEqual(res.slot_b_frames, 60)
        self.assertEqual(res.slot_a_volume_dirty, 0)
        self.assertEqual(res.slot_b_volume_dirty, 0)
        self.assertEqual(res.fifo_peak_bytes, 6_545_000)
        self.assertLess(res.fifo_peak_pct, 3.0)
        self.assertEqual(len(res.clips), 2)
        self.assertEqual(res.clips[0].clip_filename, "A001C001_261114_FX3V.MP4")
        self.assertEqual(res.clips[1].clip_filename, "A001C002_261114_FX3V.MP4")
        self.assertTrue(all(c.moov_finalized for c in res.clips))

    def test_07_relay_frame_contiguity_across_slot_a_and_slot_b(self) -> None:
        res = p71.simulate_dual_slot_ring_recording(
            mode=p71.SLOT_MODE_RELAY,
            total_frames=180,
            slot_a_capacity_frames=73,
            slot_b_capacity_frames=200,
            relay_switch_latency_ms=65.0,
        )
        clip_a, clip_b = res.clips
        self.assertEqual(clip_a.start_frame, 0)
        self.assertEqual(clip_a.end_frame, 72)
        self.assertEqual(clip_b.start_frame, 73)
        self.assertEqual(clip_b.end_frame, 179)
        self.assertEqual(clip_a.frame_count + clip_b.frame_count, 180)
        self.assertEqual(clip_a.xml_sidecar, "A001C001_261114_FX3VM01.XML")
        self.assertEqual(clip_b.xml_sidecar, "A001C002_261114_FX3VM01.XML")

    def test_08_relay_fifo_headroom_and_overflow_rejection(self) -> None:
        ok_3400ms = p71.simulate_dual_slot_ring_recording(
            mode=p71.SLOT_MODE_RELAY,
            total_frames=100,
            slot_a_capacity_frames=50,
            relay_switch_latency_ms=3400.0,
        )
        self.assertTrue(ok_3400ms.passed)
        self.assertEqual(ok_3400ms.dropped_frames, 0)

        with self.assertRaises(p71.DualSlotEmulatorError):
            p71.simulate_dual_slot_ring_recording(
                mode=p71.SLOT_MODE_RELAY,
                total_frames=100,
                slot_a_capacity_frames=50,
                relay_switch_latency_ms=3600.0,
            )

    def test_09_relay_invalid_capacity_bounds_rejected(self) -> None:
        with self.assertRaises(p71.DualSlotEmulatorError):
            p71.simulate_dual_slot_ring_recording(
                mode=p71.SLOT_MODE_RELAY,
                total_frames=100,
                slot_a_capacity_frames=100,
            )
        with self.assertRaises(p71.DualSlotEmulatorError):
            p71.simulate_dual_slot_ring_recording(
                mode=p71.SLOT_MODE_RELAY,
                total_frames=120,
                slot_a_capacity_frames=60,
                slot_b_capacity_frames=40,
            )

    def test_10_simultaneous_dual_write_slot_a_equals_slot_b_crc_and_sha256_parity(self) -> None:
        res = p71.simulate_dual_slot_ring_recording(
            mode=p71.SLOT_MODE_SIMULTANEOUS,
            total_frames=150,
        )
        self.assertTrue(res.passed)
        self.assertTrue(res.parity_verified)
        self.assertFalse(res.slot_b_yanked)
        self.assertEqual(res.slot_a_frames, 150)
        self.assertEqual(res.slot_b_frames, 150)
        self.assertEqual(res.slot_a_crc32, res.slot_b_crc32)
        self.assertEqual(len(res.clips), 2)
        self.assertEqual(res.clips[0].stream_sha256, res.clips[1].stream_sha256)
        self.assertEqual(res.slot_a_volume_dirty, 0)
        self.assertEqual(res.slot_b_volume_dirty, 0)

    def test_11_simultaneous_slot_b_yank_mid_take_zero_drops_on_slot_a(self) -> None:
        res = p71.simulate_dual_slot_ring_recording(
            mode=p71.SLOT_MODE_SIMULTANEOUS,
            total_frames=120,
            yank_slot_b_at_frame=45,
        )
        self.assertTrue(res.passed)
        self.assertTrue(res.slot_b_yanked)
        self.assertEqual(res.slot_b_yank_frame, 45)
        self.assertEqual(res.dropped_frames, 0)
        self.assertEqual(res.slot_a_frames, 120)
        self.assertEqual(res.slot_b_frames, 45)
        self.assertEqual(res.slot_b_rsv_salvageable_frames, 45)
        self.assertEqual(res.slot_a_volume_dirty, 0)
        self.assertEqual(res.slot_b_volume_dirty, 1)
        self.assertTrue(res.clips[0].moov_finalized)
        self.assertEqual(res.app_crashes, 0)
        self.assertEqual(res.wdt_resets, 0)

    def test_12_simultaneous_slot_b_yank_at_frame_zero_and_invalid_frame_rejected(self) -> None:
        yank0 = p71.simulate_dual_slot_ring_recording(
            mode=p71.SLOT_MODE_SIMULTANEOUS,
            total_frames=60,
            yank_slot_b_at_frame=0,
        )
        self.assertTrue(yank0.passed)
        self.assertEqual(yank0.dropped_frames, 0)
        self.assertEqual(yank0.slot_a_frames, 60)
        self.assertEqual(yank0.slot_b_frames, 0)

        with self.assertRaises(p71.DualSlotEmulatorError):
            p71.simulate_dual_slot_ring_recording(
                mode=p71.SLOT_MODE_SIMULTANEOUS,
                total_frames=60,
                yank_slot_b_at_frame=60,
            )

    def test_13_sort_mode_cfexpress_main_and_sdxc_v60_proxy_s03_active(self) -> None:
        res = p71.simulate_dual_slot_ring_recording(
            mode=p71.SLOT_MODE_SORT,
            total_frames=120,
            sq_enabled=False,
        )
        self.assertTrue(res.passed)
        self.assertEqual(res.slot_a_media, p71.MEDIA_CFEXPRESS_VPG400)
        self.assertEqual(res.slot_b_media, p71.MEDIA_SDXC_UHS2_V60)
        self.assertTrue(res.proxy_enabled)
        self.assertFalse(res.proxy_suspended)
        self.assertEqual(res.proxy_frames_written, 120)
        self.assertEqual(res.dropped_frames, 0)
        self.assertFalse(res.main_stalled)
        self.assertEqual(len(res.clips), 2)
        self.assertEqual(res.clips[1].clip_filename, "A001C001_261114_FX3VS03.MP4")

    def test_14_sort_mode_sq_120fps_and_240fps_auto_suspend_proxy_without_stalling_main(self) -> None:
        for sq_fps in (120, 240):
            res = p71.simulate_dual_slot_ring_recording(
                mode=p71.SLOT_MODE_SORT,
                total_frames=120,
                sq_enabled=True,
                sq_fps=sq_fps,
            )
            self.assertTrue(res.passed, msg=f"S&Q {sq_fps}fps failed")
            self.assertFalse(res.proxy_enabled)
            self.assertTrue(res.proxy_suspended)
            self.assertEqual(res.proxy_suspended_reason, "SQ_OFF_SPEED_AUTO_SUSPEND")
            self.assertEqual(res.proxy_frames_written, 0)
            self.assertFalse(res.main_stalled)
            self.assertEqual(res.dropped_frames, 0)
            self.assertEqual(res.main_written_frames, 120)
            self.assertEqual(len(res.clips), 1)

    def test_15_dualslot_invalid_inputs_raise_error(self) -> None:
        with self.assertRaises(p71.DualSlotEmulatorError):
            p71.simulate_dual_slot_ring_recording(mode="INVALID_MODE")
        with self.assertRaises(p71.DualSlotEmulatorError):
            p71.simulate_dual_slot_ring_recording(mode=p71.SLOT_MODE_SORT, total_frames=0)
        with self.assertRaises(p71.DualSlotEmulatorError):
            p71.simulate_dual_slot_ring_recording(mode=p71.SLOT_MODE_SORT, sq_enabled=True, sq_fps=96)
        with self.assertRaises(p71.DualSlotEmulatorError):
            p71.simulate_dual_slot_ring_recording(mode=p71.SLOT_MODE_RELAY, relay_switch_latency_ms=-1.0)


class TestNonRealTimeMetaAndRtmdSynchronizer(unittest.TestCase):
    """Verify in-memory Sony NonRealTimeMeta (*M01.XML) <-> RTMD 0xE304 100% provenance parity."""

    def test_16_nonrealtimemeta_cine_ei_800_selp1635g_ibis_active_100pct_match(self) -> None:
        state = p71.ClipProvenanceState(
            cine_ei_base_iso=800,
            exposure_index=800,
            gamut_gamma="S-Gamut3.Cine / S-Log3",
            user_lut_slot="Slot1:Sony_LC709TypeA.cube",
            lut_applied=True,
            start_timecode="01:00:00:00",
            lens_id="SELP1635G",
            focal_length_mm=35.0,
            focus_distance_m=0.28,
            ibis_mode="Active",
        )
        sync = p71.verify_nonrealtimemeta_vs_rtmd(state)
        self.assertTrue(sync.passed)
        self.assertEqual(sync.consistency_pct, 100.0)
        self.assertEqual(sync.mismatched_fields, ())
        self.assertEqual(sync.xml_filename, "A001C001_261114_FX3VM01.XML")
        self.assertEqual(sync.parsed_fields["CaptureGammaEquation"], "S-Gamut3.Cine / S-Log3")
        self.assertEqual(sync.parsed_fields["SteadyShotMode"], "Active")
        self.assertEqual(sync.parsed_fields["LensModelName"], "SELP1635G")
        self.assertEqual(sync.parsed_fields["FocusBreathingScale"], "1.075000")
        self.assertTrue(sync.c2pa_license_untouched)
        self.assertEqual(sync.internal_emmc_writes, 0)
        self.assertFalse(sync.persistent_emmc_writes_authorized)

    def test_17_nonrealtimemeta_cine_ei_12800_dropframe_lut_off_parity(self) -> None:
        state = p71.ClipProvenanceState(
            clip_name="A001C003_261114_FX3V",
            duration_frames=240,
            cine_ei_base_iso=12800,
            exposure_index=12800,
            user_lut_slot="Slot2:Custom_ShowLUT.cube",
            lut_applied=False,
            start_timecode="02:10:00;00",
            lens_id="SELP28135G",
            focal_length_mm=85.0,
            focus_distance_m=1.5,
            ibis_mode="Standard",
        )
        sync = p71.verify_nonrealtimemeta_vs_rtmd(state)
        self.assertTrue(sync.passed)
        self.assertEqual(sync.consistency_pct, 100.0)
        self.assertEqual(sync.parsed_fields["CineEIBaseISO"], "12800")
        self.assertEqual(sync.parsed_fields["UserLUTApplied"], "false")
        self.assertEqual(sync.parsed_fields["StartTimecode"], "02:10:00;00")
        self.assertEqual(sync.parsed_fields["SteadyShotMode"], "Standard")

    def test_18_rtmd_0xe304_hex_inside_xml_matches_stage9_encoder(self) -> None:
        state = p71.ClipProvenanceState(
            lens_id="SELP1635G",
            focal_length_mm=24.0,
            focus_distance_m=0.50,
        )
        expected_rtmd = p67.encode_rtmd_breathing_metadata(
            lens_id="SELP1635G",
            focal_length_mm=24.0,
            focus_distance_m=0.50,
            enabled=True,
        )
        sync = p71.verify_nonrealtimemeta_vs_rtmd(state)
        self.assertEqual(sync.rtmd_e304_hex, expected_rtmd.rtmd_e304_hex)
        self.assertEqual(sync.parsed_fields["RtmdE304Hex"], expected_rtmd.rtmd_e304_hex)

    def test_19_tampered_nonrealtimemeta_xml_detected_with_exact_mismatch(self) -> None:
        state = p71.ClipProvenanceState()
        xml_txt = p71.build_nonrealtimemeta_xml(state)
        tampered = xml_txt.replace('value="Active"', 'value="Off"').replace('value="35.00"', 'value="16.00"')
        sync = p71.verify_nonrealtimemeta_vs_rtmd(state, xml_override=tampered)
        self.assertFalse(sync.passed)
        self.assertLess(sync.consistency_pct, 100.0)
        self.assertEqual(set(sync.mismatched_fields), {"SteadyShotMode", "FocalLengthMm"})

    def test_20_nonrealtimemeta_xml_is_valid_et_document_and_in_memory_only(self) -> None:
        xml_txt = p71.build_nonrealtimemeta_xml(p71.ClipProvenanceState())
        root = ET.fromstring(xml_txt)
        self.assertTrue(root.tag.endswith("NonRealTimeMeta"))
        self.assertFalse((FX3_VM_DIR / "A001C001_261114_FX3VM01.XML").exists())

    def test_21_nonrealtimemeta_preserves_c2pa_and_emmc_isolation_under_mismatch(self) -> None:
        state = p71.ClipProvenanceState()
        tampered = p71.build_nonrealtimemeta_xml(state).replace('value="800"', 'value="12800"')
        sync = p71.verify_nonrealtimemeta_vs_rtmd(state, xml_override=tampered)
        self.assertFalse(sync.passed)
        self.assertTrue(sync.c2pa_license_untouched)
        self.assertEqual(sync.internal_emmc_writes, 0)
        self.assertFalse(sync.persistent_emmc_writes_authorized)


class TestPowerLossUpsBrownoutAndRsvSalvage(unittest.TestCase):
    """Verify USB-PD yank -> NP-FZ100 UPS, 2% PMIC flush, and battery-less .RSV salvage."""

    def test_22_usbpd_yank_at_65pct_npfz100_04ms_switchover_zero_drop(self) -> None:
        res = p71.simulate_power_loss_and_rsv_salvage(
            scenario_id=p71.PWR_USBPD_YANK_NPFZ100_UPS,
            total_captured_frames=120,
            battery_soc_pct=65.0,
        )
        self.assertTrue(res.passed)
        self.assertTrue(res.usbpd_yanked)
        self.assertTrue(res.battery_present)
        self.assertEqual(res.battery_soc_pct, 65.0)
        self.assertEqual(res.switchover_ms, 0.4)
        self.assertLess(res.switchover_ms, p71.HOLDOVER_CAP_MARGIN_MS)
        self.assertTrue(res.recording_continued)
        self.assertEqual(res.dropped_frames, 0)
        self.assertEqual(res.corrupt_clips, 0)
        self.assertFalse(res.rsv_container_created)
        self.assertEqual(res.exfat_volume_dirty_after, 0)

    def test_23_usbpd_yank_ups_supports_range_of_socs_and_rejects_critical_soc(self) -> None:
        for soc in (25.0, 65.0, 95.0):
            res = p71.simulate_power_loss_and_rsv_salvage(
                scenario_id=p71.PWR_USBPD_YANK_NPFZ100_UPS,
                battery_soc_pct=soc,
            )
            self.assertTrue(res.passed)
            self.assertGreater(res.battery_mv, p71.NPFZ100_BROWNOUT_THRESHOLD_MV)

        with self.assertRaises(p71.DualSlotEmulatorError):
            p71.simulate_power_loss_and_rsv_salvage(
                scenario_id=p71.PWR_USBPD_YANK_NPFZ100_UPS,
                battery_soc_pct=2.0,
            )

    def test_24_npfz100_critical_2pct_6200mv_pmic_controlled_libmpr_flush(self) -> None:
        res = p71.simulate_power_loss_and_rsv_salvage(
            scenario_id=p71.PWR_NPFZ100_CRITICAL_2PCT_FLUSH,
            total_captured_frames=120,
        )
        self.assertTrue(res.passed)
        self.assertEqual(res.battery_soc_pct, 2.0)
        self.assertEqual(res.battery_mv, 6200)
        self.assertTrue(res.pmic_brownout_warning)
        self.assertTrue(res.controlled_flush_executed)
        self.assertFalse(res.recording_continued)
        self.assertEqual(res.dropped_frames, 0)
        self.assertEqual(res.corrupt_clips, 0)
        self.assertTrue(res.moov_finalized)
        self.assertTrue(res.xml_finalized)
        self.assertEqual(res.exfat_volume_dirty_after, 0)
        self.assertFalse(res.rsv_container_created)

    def test_25_batteryless_instant_brownout_rsv_salvage_recovers_all_committed_frames(self) -> None:
        res = p71.simulate_power_loss_and_rsv_salvage(
            scenario_id=p71.PWR_BATTERYLESS_BROWNOUT_RSV,
            total_captured_frames=120,
            uncommitted_volatile_tail_frames=6,
        )
        self.assertTrue(res.passed)
        self.assertFalse(res.battery_present)
        self.assertEqual(res.battery_mv, 0)
        self.assertTrue(res.rsv_container_created)
        self.assertEqual(res.rsv_filename, "A001C001_261114_FX3V.RSV")
        self.assertEqual(res.salvaged_filename, "A001C001_261114_FX3V.MP4")
        self.assertEqual(res.committed_ring_frames, 114)
        self.assertEqual(res.salvageable_frames, res.committed_ring_frames)
        self.assertEqual(res.uncommitted_volatile_frames, 6)
        self.assertTrue(res.salvaged_crc32_verified)
        self.assertEqual(res.exfat_volume_dirty_before, 1)
        self.assertEqual(res.exfat_volume_dirty_after, 0)
        self.assertEqual(res.corrupt_clips, 0)
        self.assertEqual(res.p1_emmc_mutations, 0)
        self.assertFalse(res.persistent_emmc_writes_authorized)

    def test_26_batteryless_rsv_salvage_scales_across_ring_sizes(self) -> None:
        res = p71.simulate_power_loss_and_rsv_salvage(
            scenario_id=p71.PWR_BATTERYLESS_BROWNOUT_RSV,
            total_captured_frames=240,
            uncommitted_volatile_tail_frames=12,
        )
        self.assertTrue(res.passed)
        self.assertEqual(res.committed_ring_frames, 228)
        self.assertEqual(res.salvageable_frames, 228)
        self.assertTrue(res.salvaged_crc32_verified)

    def test_27_all_power_scenarios_enforce_zero_emmc_and_c2pa_protection(self) -> None:
        for sc in p71.ALL_POWER_SCENARIOS:
            res = p71.simulate_power_loss_and_rsv_salvage(scenario_id=sc)
            self.assertTrue(res.passed, msg=f"Power scenario {sc} failed")
            self.assertEqual(res.p1_emmc_mutations, 0)
            self.assertEqual(res.internal_emmc_writes, 0)
            self.assertTrue(res.c2pa_license_untouched)
            self.assertFalse(res.persistent_emmc_writes_authorized)

    def test_28_invalid_power_scenario_or_frame_bounds_rejected(self) -> None:
        with self.assertRaises(p71.DualSlotEmulatorError):
            p71.simulate_power_loss_and_rsv_salvage(scenario_id="INVALID_PWR")
        with self.assertRaises(p71.DualSlotEmulatorError):
            p71.simulate_power_loss_and_rsv_salvage(
                scenario_id=p71.PWR_BATTERYLESS_BROWNOUT_RSV,
                total_captured_frames=6,
                uncommitted_volatile_tail_frames=6,
            )


class TestStage10SuiteIntegrationAndCli(unittest.TestCase):
    """Verify Stage 10 wiring in fx3_vm_coemulation_suite.py, CLI flags, and source hygiene."""

    def test_29_coemulation_suite_includes_stage10_and_skip_phase71_backward_compat(self) -> None:
        rep_full = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig(force_clean_room=True))
        self.assertTrue(rep_full["all_checks_passed"])
        self.assertIn("stage10_phase71_dualslot_ups_salvage", rep_full)
        s10 = rep_full["stage10_phase71_dualslot_ups_salvage"]
        self.assertTrue(s10["all_checks_passed"])
        self.assertEqual(s10["cp_mutation_bytes"], 0)
        self.assertEqual(s10["p1_emmc_mutations"], 0)
        self.assertEqual(s10["internal_emmc_writes"], 0)
        self.assertTrue(s10["c2pa_license_untouched"])
        self.assertFalse(s10["persistent_emmc_writes_authorized"])
        self.assertEqual(s10["rsv_salvageable_frames"], s10["rsv_committed_frames"])

        rep_skip = suite.run_fx3_vm_coemulation_suite(
            suite.CoEmulationConfig(force_clean_room=True, include_phase71_dualslot_ups_salvage=False)
        )
        self.assertTrue(rep_skip["all_checks_passed"])
        self.assertNotIn("stage10_phase71_dualslot_ups_salvage", rep_skip)

    def test_30_clean_room_audit_digest_reproducible_and_valid_json(self) -> None:
        rep1 = p71.run_phase71_dualslot_ups_salvage_audit(force_clean_room=True)
        rep2 = p71.run_phase71_dualslot_ups_salvage_audit(force_clean_room=True)
        self.assertEqual(rep1["audit_digest_sha256"], rep2["audit_digest_sha256"])

        rendered = json.dumps(rep1, allow_nan=False)
        self.assertNotRegex(rendered, r'(?<![0-9A-Za-z_/.-])b[\'"]')

        copy = dict(rep1)
        recorded = copy.pop("audit_digest_sha256")
        expected = hashlib.sha256(
            json.dumps(copy, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        self.assertEqual(recorded, expected)

    def test_31_standalone_cli_flags_emit_valid_outputs(self) -> None:
        for argv in (
            ["--clean-room", "--summary"],
            ["--clean-room", "--slot-matrix"],
            ["--clean-room", "--xml-sample"],
            ["--clean-room", "--power-matrix"],
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = p71.main(argv)
            self.assertEqual(rc, 0, msg=f"CLI argv={argv} failed")
            self.assertTrue(buf.getvalue().strip())

    def test_32_suite_cli_summary_and_skip_phase71_flag(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                str(FX3_VM_DIR / "fx3_vm_coemulation_suite.py"),
                "--clean-room",
                "--summary",
            ],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        self.assertIn("dualslot_ups=CLEAN_ROOM_SYNTHETIC", proc.stdout)

        proc_skip = subprocess.run(
            [
                sys.executable,
                "-B",
                str(FX3_VM_DIR / "fx3_vm_coemulation_suite.py"),
                "--clean-room",
                "--skip-phase71",
                "--summary",
            ],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc_skip.returncode, 0, msg=proc_skip.stderr)
        self.assertNotIn("dualslot_ups=", proc_skip.stdout)

    def test_33_json_output_determinism_without_bytes_repr_leakage(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = p71.main(["--clean-room", "--json"])
        self.assertEqual(rc, 0)
        rendered = buf.getvalue()
        self.assertNotRegex(rendered, r'(?<![0-9A-Za-z_/.-])b[\'"]')
        parsed = json.loads(rendered)
        self.assertEqual(parsed["schema"], p71.PHASE_71_SCHEMA)
        self.assertTrue(parsed["all_checks_passed"])

    def test_34_source_hygiene_o_rdonly_and_no_forbidden_writes_or_port(self) -> None:
        forbidden_port = "87" + "68"
        emu_src = (FX3_VM_DIR / "dualslot_proxy_ups_salvage_emulator.py").read_text(encoding="utf-8")
        test_src = Path(__file__).read_text(encoding="utf-8")

        self.assertIn("os.O_RDONLY", emu_src)
        self.assertNotIn("os.O_WRONLY", emu_src)
        self.assertNotIn("os.O_RDWR", emu_src)
        self.assertNotIn(forbidden_port, emu_src)
        self.assertNotIn(forbidden_port, test_src)
        self.assertIn("CP_MUTATION_BYTES = 0", emu_src)
        self.assertIn("P1_EMMC_MUTATIONS = 0", emu_src)
        self.assertIn("INTERNAL_EMMC_WRITES = 0", emu_src)
        self.assertIn("C2PA_LICENSE_UNTOUCHED = True", emu_src)
        self.assertIn("PERSISTENT_EMMC_WRITES_AUTHORIZED = False", emu_src)


if __name__ == "__main__":
    unittest.main()
