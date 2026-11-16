#!/usr/bin/env python3
"""Phase 162 Test Suite — Stage 28 (`28/28`) Real-Hardware Main Track Part 11:
Dual-Slot `CFexpress Type A / SDXC V90` Hot-Swap, `.RSV` Clip Salvage,
Official `BODYDATA.DAT` (`\\x89UFU`) `<100 us` Auto-Bypass & 5-Tier Unbrickable Recovery HIL.

Exercises 46 fast dual-mode unit, integration, bounded 4 KiB header, Pillar A-D HIL,
Stage 28 suite orchestration (`28/28` stages), CLI, runtime-budget, and clean-room hygiene checks.
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import contextlib
import io
import json
import os
import re
import subprocess
import time
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
FX3_VM_DIR = TESTS_DIR.parent
REPO_ROOT = FX3_VM_DIR.parents[1]
if str(FX3_VM_DIR) not in sys.path:
    sys.path.insert(0, str(FX3_VM_DIR))

import fx3_vm_coemulation_suite as suite  # noqa: E402
import realhw_cfexpress_ufu_and_5tier_recovery_coemulator as p162  # noqa: E402


_AUDIT_CACHE: dict = {}


def _get_default_audit() -> dict:
    key = ("default", p162.is_forced_clean_room())
    if key not in _AUDIT_CACHE:
        _AUDIT_CACHE[key] = p162.run_phase162_realhw_cfexpress_ufu_5tier_hil(env=os.environ)
    return _AUDIT_CACHE[key]


def _get_clean_room_audit() -> dict:
    key = ("clean_room", True)
    if key not in _AUDIT_CACHE:
        _AUDIT_CACHE[key] = p162.run_phase162_realhw_cfexpress_ufu_5tier_hil(
            force_clean_room=True,
            env=os.environ,
        )
    return _AUDIT_CACHE[key]


class TestStage28DualModeDonorsAndRedlines(unittest.TestCase):
    """Dual-mode O_RDONLY donor inspection, bounded <=4 KiB BODYDATA.DAT check & redlines."""

    def test_01_donor_path_resolution_honors_clean_room_toggle(self) -> None:
        paths_clean = p162.resolve_phase162_donor_paths(env={"FX3_FX6_FORCE_CLEAN_ROOM": "1"})
        self.assertEqual(len(paths_clean), 12)
        for p in paths_clean.values():
            self.assertIn(p162.CLEAN_ROOM_SENTINEL_DIRNAME, str(p))
            self.assertFalse(p.exists())
        bd_clean = p162.resolve_optional_bodydata_paths(env={"FX3_FX6_FORCE_CLEAN_ROOM": "1"})
        self.assertEqual(len(bd_clean), 2)
        for p in bd_clean.values():
            self.assertIn(p162.CLEAN_ROOM_SENTINEL_DIRNAME, str(p))
            self.assertFalse(p.exists())

    def test_02_clean_room_synthetic_fixtures_valid_elf_bk4_and_ufu(self) -> None:
        fx = p162.build_clean_room_phase162_fixtures()
        self.assertEqual(len(fx), 14)
        for k in ("fx3_libmpr", "fx6_libmpr", "fx3_sencore", "fx6_sencore", "fx3_im_elf", "fx6_im_elf"):
            self.assertEqual(fx[k][:4], b"\x7fELF")
        self.assertEqual(fx["fx3_backup"][12:16], b"BK4\x00")
        self.assertEqual(fx["fx6_backup"][12:16], b"BK4\x00")
        self.assertEqual(fx["fx3_bodydata_4k"][:8], p162.UFU_MAGIC)
        self.assertEqual(fx["fx6_bodydata_4k"][:8], p162.UFU_MAGIC)
        self.assertLessEqual(len(fx["fx3_bodydata_4k"]), p162.BODYDATA_BOUNDED_READ_MAX_BYTES)
        self.assertLessEqual(len(fx["fx6_bodydata_4k"]), p162.BODYDATA_BOUNDED_READ_MAX_BYTES)

    def test_03_clean_room_donor_audit_verifies_all_12_core_plus_2_ufu_contracts(self) -> None:
        da = p162.inspect_phase162_donors(force_clean_room=True)
        self.assertEqual(da.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(da.access_mode, "O_RDONLY")
        self.assertEqual(da.donor_files_inspected, 12)
        self.assertTrue(da.im_elf_abi_zero_diff)
        self.assertTrue(da.sencore_symbol_parity)
        self.assertTrue(da.fx3_bodydata_header.bounded_header_only)
        self.assertLessEqual(da.fx3_bodydata_header.bytes_read, p162.BODYDATA_BOUNDED_READ_MAX_BYTES)
        self.assertTrue(da.fx3_bodydata_header.fx3_0da1_pid_present)
        self.assertFalse(da.fx6_bodydata_header.fx3_0da1_pid_present)
        self.assertTrue(da.all_contracts_verified, msg=str(da.errors))

    def test_04_missing_donor_directory_falls_back_deterministically(self) -> None:
        from unittest import mock

        with mock.patch.object(p162, "_iter_work_roots", return_value=(Path("/nonexistent/fx3/work"),)):
            da = p162.inspect_phase162_donors(force_clean_room=False, env={})
        self.assertEqual(da.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(da.all_contracts_verified)

    def test_05_stage28_clean_room_execution_fast_and_redlines_locked(self) -> None:
        t0 = time.monotonic()
        rep = _get_clean_room_audit()
        dt = time.monotonic() - t0
        self.assertLess(dt, 0.25)
        self.assertEqual(rep["schema"], p162.PHASE_162_SCHEMA)
        self.assertEqual(rep["version"], p162.PHASE_162_VERSION)
        self.assertEqual(rep["stage_index"], 28)
        self.assertTrue(rep["all_checks_passed"])
        self.assertEqual(rep["source_mode"], "CLEAN_ROOM_SYNTHETIC")

        red = rep["redlines"]
        self.assertTrue(red["p8_cp_mutation_forbidden"])
        self.assertEqual(red["nop_count"], 0)
        self.assertEqual(red["cp_mutation_bytes"], 0)
        self.assertEqual(red["wbi_mutation_bytes"], 0)
        self.assertEqual(red["calibration_mutation_bytes"], 0)
        self.assertFalse(red["persistent_emmc_writes_authorized"])
        self.assertEqual(red["emmc_nflasha_write_count"], 0)
        self.assertEqual(red["emmc_mutation_bytes"], 0)
        self.assertFalse(red["spi_nor_write_authorized"])
        self.assertEqual(red["spi_nor_mutation_bytes"], 0)
        self.assertFalse(red["el3_payload_transmit_authorized"])
        self.assertTrue(red["user_media_clips_intact"])
        self.assertEqual(red["rsv_orphan_count"], 0)
        self.assertEqual(red["donor_access_mode"], "O_RDONLY")

    def test_06_local_or_clean_default_mode_passes_all_checks(self) -> None:
        rep = _get_default_audit()
        self.assertTrue(rep["all_checks_passed"])
        self.assertIn(rep["source_mode"], ("LOCAL_DONOR_RDONLY", "CLEAN_ROOM_SYNTHETIC"))
        self.assertGreaterEqual(rep["donor_audit"]["donor_files_inspected"], 12)
        self.assertLessEqual(rep["donor_audit"]["donor_files_inspected"], 14)
        self.assertTrue(rep["donor_audit"]["all_contracts_verified"])

    @unittest.skipUnless(
        (not p162.is_forced_clean_room())
        and all(p.is_file() for p in p162.resolve_phase162_donor_paths().values()),
        "Local FX3/FX6 donor images absent or FX3_FX6_FORCE_CLEAN_ROOM=1",
    )
    def test_07_local_rdonly_donors_exact_bytes_and_bounded_4k_bodydata(self) -> None:
        rep = _get_default_audit()
        self.assertEqual(rep["source_mode"], "LOCAL_DONOR_RDONLY")
        da = rep["donor_audit"]
        self.assertEqual(da["fx3_libmpr"]["file_bytes"], 3_517_008)
        self.assertEqual(da["fx6_libmpr"]["file_bytes"], 28_921_824)
        self.assertEqual(da["fx3_sencore"]["file_bytes"], 377_328)
        self.assertEqual(da["fx6_sencore"]["file_bytes"], 401_952)
        self.assertEqual(da["fx3_im_elf"]["file_bytes"], 40_920)
        self.assertEqual(da["fx6_im_elf"]["file_bytes"], 40_920)
        self.assertEqual(da["fx3_loader_nor"]["file_bytes"], 101_888)
        self.assertEqual(da["fx6_loader_nor"]["file_bytes"], 92_448)
        self.assertEqual(da["fx3_cpapp"]["file_bytes"], 15_980_568)
        self.assertEqual(da["fx6_cpapp"]["file_bytes"], 17_952_816)
        self.assertEqual(da["fx3_backup"]["subsystem_count"], 819)
        self.assertEqual(da["fx6_backup"]["subsystem_count"], 840)

        for bd_key in ("fx3_bodydata_header", "fx6_bodydata_header"):
            bd = da[bd_key]
            self.assertTrue(bd["bounded_header_only"])
            self.assertLessEqual(bd["bytes_read"], 4096)
            self.assertTrue(bd["ufu_magic_ok"])
        if da["fx3_bodydata_header"]["present_locally"]:
            self.assertEqual(da["fx3_bodydata_header"]["file_bytes"], 811_876_768)
            self.assertEqual(da["fx3_bodydata_header"]["bytes_read"], 4096)
            self.assertTrue(da["fx3_bodydata_header"]["fx3_0da1_pid_present"])

    def test_08_im_elf_and_sencore_abi_parity_both_bodies(self) -> None:
        da = _get_default_audit()["donor_audit"]
        self.assertEqual(da["fx3_im_elf"]["export_count"], 11)
        self.assertEqual(da["fx6_im_elf"]["export_count"], 11)
        self.assertEqual(da["fx3_im_elf"]["import_count"], 85)
        self.assertEqual(da["fx6_im_elf"]["import_count"], 85)
        self.assertEqual(da["fx3_sencore"]["export_count"], 355)
        self.assertEqual(da["fx6_sencore"]["export_count"], 355)
        self.assertEqual(da["fx3_sencore"]["import_count"], 130)
        self.assertEqual(da["fx6_sencore"]["import_count"], 130)

    def test_09_parse_ufu_header_4k_rejects_oversized_or_bad_magic(self) -> None:
        bad = p162.parse_ufu_header_4k(
            b"BADMAGIC" + b"\x00" * 32,
            artifact_key="bad",
            body_label="FX3_7.02",
            source_mode="CLEAN_ROOM_SYNTHETIC",
            present_locally=False,
            total_file_bytes=40,
        )
        self.assertFalse(bad.ufu_magic_ok)
        self.assertFalse(bad.fx3_0da1_pid_present)
        self.assertEqual(bad.fdat_offset, -1)

        with self.assertRaises(p162.RealHwCfexpressUfu5TierError):
            p162.parse_ufu_header_4k(
                p162.UFU_MAGIC + b"\x00" * 5000,
                artifact_key="oversized",
                body_label="FX3_7.02",
                source_mode="CLEAN_ROOM_SYNTHETIC",
                present_locally=False,
                total_file_bytes=5008,
            )


class TestPillarACfexpressRelayAndCardDoorGpio(unittest.TestCase):
    """Pillar A: CFexpress Type A / SDXC V90 bitrate gate, relay & card-door GPIO flush."""

    def test_10_cfexpress_to_sdxc_v90_600mbps_relay_admitted_zero_drop(self) -> None:
        r = p162.evaluate_cfexpress_sdxc_admission_and_relay(
            slot_a_media=p162.MEDIA_CFEXPRESS_TYPE_A,
            slot_b_media=p162.MEDIA_SDXC_V90,
            recording_profile="XAVC_SI_4K_120P_600M",
            relay_switch=True,
        )
        self.assertTrue(r.valid)
        self.assertTrue(r.admitted)
        self.assertTrue(r.relay_switched)
        self.assertEqual(r.dropped_frames, 0)
        self.assertEqual(r.mpr_fifo_residual_bytes, 0)
        self.assertEqual(r.emmc_nflasha_write_count, 0)
        self.assertEqual(r.status_code, "RELAY_ADMITTED_ZERO_DROP")

    def test_11_sdxc_v90_single_slot_600mbps_admitted(self) -> None:
        r = p162.evaluate_cfexpress_sdxc_admission_and_relay(
            slot_a_media=p162.MEDIA_SDXC_V90,
            slot_b_media=p162.MEDIA_SDXC_V90,
            recording_profile="XAVC_SI_4K_120P_600M",
            relay_switch=False,
        )
        self.assertTrue(r.valid)
        self.assertTrue(r.admitted)
        self.assertEqual(r.slot_a_sustained_mbps, 720)
        self.assertEqual(r.dropped_frames, 0)

    def test_12_sdxc_v30_600mbps_rejected_safely_zero_crash(self) -> None:
        r = p162.evaluate_cfexpress_sdxc_admission_and_relay(
            slot_a_media=p162.MEDIA_SDXC_V30,
            slot_b_media=p162.MEDIA_SDXC_V90,
            recording_profile="XAVC_SI_4K_120P_600M",
            relay_switch=True,
        )
        self.assertFalse(r.valid)
        self.assertFalse(r.admitted)
        self.assertEqual(r.appfw_crashes, 0)
        self.assertEqual(r.emmc_nflasha_write_count, 0)
        self.assertIn("SPEED_CLASS_REJECTED", r.status_code)

    def test_13_sdxc_v60_relay_target_rejected_for_600mbps_but_admitted_for_200mbps(self) -> None:
        rej = p162.evaluate_cfexpress_sdxc_admission_and_relay(
            slot_a_media=p162.MEDIA_CFEXPRESS_TYPE_A,
            slot_b_media=p162.MEDIA_SDXC_V60,
            recording_profile="XAVC_SI_4K_120P_600M",
            relay_switch=True,
        )
        self.assertFalse(rej.admitted)
        self.assertIn("RELAY_SLOT_B_SPEED_REJECTED", rej.status_code)

        ok = p162.evaluate_cfexpress_sdxc_admission_and_relay(
            slot_a_media=p162.MEDIA_CFEXPRESS_TYPE_A,
            slot_b_media=p162.MEDIA_SDXC_V60,
            recording_profile="XAVC_S_4K_60P_200M",
            relay_switch=True,
        )
        self.assertTrue(ok.admitted)
        self.assertTrue(ok.relay_switched)

    def test_14_card_door_gpio_mid_write_flushes_fifo_zero_residual_and_preserves_clips(self) -> None:
        r = p162.evaluate_cfexpress_sdxc_admission_and_relay(
            slot_a_media=p162.MEDIA_CFEXPRESS_TYPE_A,
            slot_b_media=p162.MEDIA_SDXC_V90,
            recording_profile="XAVC_SI_4K_120P_600M",
            relay_switch=False,
            card_door_opened_mid_write=True,
            dual_boot_switch_count=5,
            m4root_clips_count=18,
            xdroot_clips_count=9,
        )
        self.assertTrue(r.valid)
        self.assertTrue(r.card_door_gpio_triggered)
        self.assertEqual(r.mpr_fifo_residual_bytes, 0)
        self.assertEqual(r.exfat_volume_dirty, 0)
        self.assertTrue(r.user_media_clips_intact)
        self.assertEqual(r.m4root_clips_count, 18)
        self.assertEqual(r.xdroot_clips_count, 9)
        self.assertEqual(r.status_code, "CARD_DOOR_GPIO_SAFE_FLUSH_ZERO_RESIDUAL")

    def test_15_invalid_media_or_profile_raises(self) -> None:
        with self.assertRaises(p162.RealHwCfexpressUfu5TierError):
            p162.evaluate_cfexpress_sdxc_admission_and_relay(slot_a_media="BAD_MEDIA")
        with self.assertRaises(p162.RealHwCfexpressUfu5TierError):
            p162.evaluate_cfexpress_sdxc_admission_and_relay(recording_profile="RAW_12G")

    def test_16_pillar_a_aggregate_passes(self) -> None:
        pa = _get_clean_room_audit()["pillar_a_cfexpress_sdxc_relay_and_card_door"]
        self.assertTrue(pa["passed"])


class TestPillarBRsvBatteryPullSalvage(unittest.TestCase):
    """Pillar B: Sudden battery pull .RSV clip salvage (`Recover Image DB`)."""

    def test_17_battery_pull_mp4_rsv_salvaged_with_zero_emmc_writes(self) -> None:
        r = p162.evaluate_rsv_clip_salvage(
            container_kind=p162.RSV_CONTAINER_MP4,
            committed_gop_frames=720,
            index_entry_pending=True,
        )
        self.assertTrue(r.valid)
        self.assertTrue(r.salvage_succeeded)
        self.assertEqual(r.target_filename, "C0001.MP4")
        self.assertEqual(r.salvaged_frames, 720)
        self.assertEqual(r.rsv_orphan_count, 0)
        self.assertTrue(r.mediapro_xml_rebuilt)
        self.assertTrue(r.existing_clips_preserved)
        self.assertEqual(r.emmc_nflasha_write_count, 0)
        self.assertFalse(r.persistent_emmc_writes_authorized)

    def test_18_battery_pull_mxf_rsv_salvaged_to_mxf(self) -> None:
        r = p162.evaluate_rsv_clip_salvage(
            container_kind=p162.RSV_CONTAINER_MXF,
            committed_gop_frames=1440,
            index_entry_pending=True,
        )
        self.assertTrue(r.valid)
        self.assertTrue(r.salvage_succeeded)
        self.assertEqual(r.target_filename, "C0001.MXF")
        self.assertEqual(r.salvaged_frames, 1440)
        self.assertEqual(r.rsv_orphan_count, 0)

    def test_19_corrupt_or_zero_frame_rsv_rejected_preserving_existing_clips(self) -> None:
        r = p162.evaluate_rsv_clip_salvage(
            container_kind=p162.RSV_CONTAINER_CORRUPT,
            committed_gop_frames=0,
            corrupt_header=True,
        )
        self.assertFalse(r.valid)
        self.assertFalse(r.salvage_succeeded)
        self.assertEqual(r.salvaged_frames, 0)
        self.assertEqual(r.rsv_orphan_count, 1)
        self.assertTrue(r.existing_clips_preserved)
        self.assertEqual(r.emmc_nflasha_write_count, 0)
        self.assertEqual(r.status_code, "SALVAGE_REJECTED_CORRUPT_RSV")

    def test_20_invalid_container_kind_or_negative_frames_raises(self) -> None:
        with self.assertRaises(p162.RealHwCfexpressUfu5TierError):
            p162.evaluate_rsv_clip_salvage(container_kind="AVI_BAD")
        with self.assertRaises(p162.RealHwCfexpressUfu5TierError):
            p162.evaluate_rsv_clip_salvage(committed_gop_frames=-1)

    def test_21_pillar_b_aggregate_passes(self) -> None:
        pb = _get_clean_room_audit()["pillar_b_rsv_clip_salvage_and_recover_db"]
        self.assertTrue(pb["passed"])


class TestPillarCBodydataUfuBypassAndModelGate(unittest.TestCase):
    """Pillar C: Official BODYDATA.DAT (\\x89UFU), <100 us auto-bypass & cross-model gate."""

    def test_22_bodydata_present_triggers_stage_a_bypass_under_100us(self) -> None:
        r = p162.evaluate_bodydata_ufu_coexistence_and_bypass(
            bodydata_present=True,
            target_model_id=p162.FX3_MODEL_ID,
            p15_orig_uninstall_complete=False,
            launch_p1_updater=False,
        )
        self.assertTrue(r.valid)
        self.assertTrue(r.ufu_magic_ok)
        self.assertTrue(r.stage_a_auto_bypass_triggered)
        self.assertLess(r.bypass_latency_us, 100.0)
        self.assertEqual(r.active_userland, "STOCK_FX3_702")
        self.assertEqual(r.emmc_nflasha_write_count, 0)

    def test_23_p1_updater_blocked_when_h0_neq_h3_until_p15_orig_uninstall(self) -> None:
        r = p162.evaluate_bodydata_ufu_coexistence_and_bypass(
            bodydata_present=True,
            target_model_id=p162.FX3_MODEL_ID,
            p15_orig_uninstall_complete=False,
            launch_p1_updater=True,
        )
        self.assertFalse(r.valid)
        self.assertFalse(r.h0_equals_h3)
        self.assertTrue(r.p1_update_blocked)
        self.assertFalse(r.p1_update_launch_permitted)
        self.assertEqual(r.status_code, "BLOCKED_P15_ORIG_UNINSTALL_REQUIRED_H0_NEQ_H3")

    def test_24_p1_updater_permitted_after_h0_eq_h3_clean_uninstall(self) -> None:
        r = p162.evaluate_bodydata_ufu_coexistence_and_bypass(
            bodydata_present=True,
            target_model_id=p162.FX3_MODEL_ID,
            p15_orig_uninstall_complete=True,
            launch_p1_updater=True,
        )
        self.assertTrue(r.valid)
        self.assertTrue(r.h0_equals_h3)
        self.assertTrue(r.p1_update_launch_permitted)
        self.assertFalse(r.p1_update_blocked)
        self.assertFalse(r.persistent_emmc_writes_authorized)

    def test_25_cross_model_fx30_and_a7s3_and_fx6_rejected_fail_closed(self) -> None:
        for mid in (p162.FX30_MODEL_ID, p162.A7S3_MODEL_ID, p162.FX6_MODEL_ID):
            r = p162.evaluate_bodydata_ufu_coexistence_and_bypass(
                bodydata_present=True,
                target_model_id=mid,
                p15_orig_uninstall_complete=True,
                launch_p1_updater=True,
            )
            self.assertFalse(r.valid)
            self.assertFalse(r.model_id_matched_fx3)
            self.assertTrue(r.p1_update_blocked)
            self.assertFalse(r.p1_update_launch_permitted)
            self.assertIn("BLOCKED_CROSS_MODEL_UFU_", r.status_code)

    def test_26_invalid_ufu_magic_blocked_and_reverts_to_stock_fx3(self) -> None:
        r = p162.evaluate_bodydata_ufu_coexistence_and_bypass(
            bodydata_present=True,
            ufu_magic=b"NOTUFU!!",
            target_model_id=p162.FX3_MODEL_ID,
            p15_orig_uninstall_complete=True,
            launch_p1_updater=True,
        )
        self.assertFalse(r.valid)
        self.assertFalse(r.ufu_magic_ok)
        self.assertTrue(r.p1_update_blocked)
        self.assertEqual(r.active_userland, "STOCK_FX3_702")

    def test_27_no_bodydata_keeps_stage_b_active(self) -> None:
        r = p162.evaluate_bodydata_ufu_coexistence_and_bypass(
            bodydata_present=False,
            launch_p1_updater=False,
        )
        self.assertTrue(r.valid)
        self.assertFalse(r.stage_a_auto_bypass_triggered)
        self.assertEqual(r.active_userland, "FX6_STAGE_B_DUALBOOT")

    def test_28_pillar_c_aggregate_passes(self) -> None:
        pc = _get_clean_room_audit()["pillar_c_bodydata_ufu_bypass_and_model_gate"]
        self.assertTrue(pc["passed"])


class TestPillarDFiveTierUnbrickableRecovery(unittest.TestCase):
    """Pillar D: 5-Tier Unbrickable Recovery Escalation Drill & hardware safety redlines."""

    def test_29_all_five_tiers_recover_with_zero_unsafe_writes_or_el3_tx(self) -> None:
        for tier in p162.ALL_RECOVERY_TIERS:
            r = p162.evaluate_5tier_recovery_escalation(
                tier=tier,
                fault_injected=f"FAULT_FOR_{tier}",
            )
            self.assertTrue(r.valid, msg=tier)
            self.assertTrue(r.recovered, msg=tier)
            self.assertFalse(r.el3_payload_transmit_authorized, msg=tier)
            self.assertFalse(r.spi_nor_write_authorized, msg=tier)
            self.assertFalse(r.persistent_emmc_writes_authorized, msg=tier)
            self.assertEqual(r.emmc_nflasha_write_count, 0, msg=tier)
            self.assertEqual(r.passive_tx_bytes_emitted, 0, msg=tier)
            self.assertTrue(r.ddrtraining_0x3e210fc_preserved, msg=tier)

    def test_30_tier1_sd_47us_escape_latency_exact(self) -> None:
        r = p162.evaluate_5tier_recovery_escalation(
            tier=p162.TIER_1_SD_ESCAPE_47US,
            fault_injected="STAGE_B_HANG",
        )
        self.assertAlmostEqual(r.recovery_latency_ms, 0.047, places=6)
        self.assertEqual(r.active_boot_target, "STOCK_FX3_702_SD_EJECT_47US")

    def test_31_tier3_cross_model_ufu_rejected(self) -> None:
        r = p162.evaluate_5tier_recovery_escalation(
            tier=p162.TIER_3_SAME_MODEL_UFU,
            fault_injected="CROSS_MODEL_UFU_INJECTION",
            same_model_fx3_ufu=False,
        )
        self.assertFalse(r.valid)
        self.assertFalse(r.recovered)
        self.assertEqual(r.status_code, "TIER3_CROSS_MODEL_UFU_REJECTED")

    def test_32_tier5_isp_cid_mismatch_rejected(self) -> None:
        r = p162.evaluate_5tier_recovery_escalation(
            tier=p162.TIER_5_CID_MATCHED_ISP,
            fault_injected="WRONG_DONOR_EMMC_CID",
            cid_and_serial_matched=False,
        )
        self.assertFalse(r.valid)
        self.assertFalse(r.recovered)
        self.assertEqual(r.status_code, "TIER5_ISP_CID_SERIAL_MISMATCH_BLOCKED")

    def test_33_unsafe_el3_tx_spi_nor_or_emmc_write_requests_hard_blocked(self) -> None:
        for kwargs in (
            {"authorize_el3_payload_tx": True},
            {"authorize_spi_nor_write": True},
            {"authorize_emmc_write": True},
        ):
            r = p162.evaluate_5tier_recovery_escalation(
                tier=p162.TIER_4_MULTI_USB_1V8_UART_EL3_RO,
                fault_injected="UNSAFE_AUTH_REQUEST",
                **kwargs,
            )
            self.assertFalse(r.valid)
            self.assertFalse(r.recovered)
            self.assertFalse(r.el3_payload_transmit_authorized)
            self.assertFalse(r.spi_nor_write_authorized)
            self.assertFalse(r.persistent_emmc_writes_authorized)
            self.assertEqual(r.status_code, "BLOCKED_UNSAFE_HARDWARE_WRITE_OR_EL3_TX_REQUEST")

    def test_34_invalid_tier_raises(self) -> None:
        with self.assertRaises(p162.RealHwCfexpressUfu5TierError):
            p162.evaluate_5tier_recovery_escalation(tier="TIER_99", fault_injected="NONE")

    def test_35_pillar_d_aggregate_verifies_all_5_tiers(self) -> None:
        pd = _get_clean_room_audit()["pillar_d_five_tier_unbrickable_recovery_drill"]
        self.assertTrue(pd["passed"])
        self.assertEqual(pd["tiers_verified_count"], 5)


class TestStage28SuiteOrchestrationCliAndHygiene(unittest.TestCase):
    """CLI, 28/28 suite orchestration, runtime budget, JSON safety & O_RDONLY hygiene."""

    def test_36_cli_in_process_clean_room_summary_and_json(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = p162.main(["--clean-room", "--self-test", "--summary"])
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("[PASS] Phase 162 Stage 28", out)
        self.assertIn("mode=CLEAN_ROOM_SYNTHETIC", out)
        self.assertIn("tiers=5/5", out)
        self.assertIn("el3_tx=False", out)
        self.assertIn("spi_wr=False", out)
        self.assertIn("emmc_wr=0", out)

        buf_json = io.StringIO()
        with contextlib.redirect_stdout(buf_json):
            rc_j = p162.main(["--clean-room", "--json"])
        self.assertEqual(rc_j, 0)
        parsed = json.loads(buf_json.getvalue())
        self.assertEqual(parsed["stage_index"], 28)
        self.assertTrue(parsed["all_checks_passed"])

    def test_37_cli_unknown_flag_exits_nonzero(self) -> None:
        buf_err = io.StringIO()
        with contextlib.redirect_stderr(buf_err):
            with self.assertRaises(SystemExit) as ctx:
                p162.main(["--no-such-flag"])
            self.assertNotEqual(ctx.exception.code, 0)

    def test_38_suite_in_process_28_stages_and_skip_phase162_config(self) -> None:
        rep_on = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig(force_clean_room=True))
        self.assertTrue(rep_on["all_checks_passed"])
        self.assertIn("stage28_realhw_cfexpress_ufu_5tier_hil", rep_on)
        s28 = rep_on["stage28_realhw_cfexpress_ufu_5tier_hil"]
        self.assertTrue(s28["all_checks_passed"])
        self.assertFalse(s28["persistent_emmc_writes_authorized"])
        self.assertFalse(s28["spi_nor_write_authorized"])
        self.assertFalse(s28["el3_payload_transmit_authorized"])
        self.assertEqual(s28["emmc_nflasha_write_count"], 0)
        self.assertEqual(s28["rsv_orphan_count"], 0)
        self.assertTrue(s28["user_media_clips_intact"])

        stage_keys = [k for k in rep_on if re.match(r"^stage\d+_", k)]
        self.assertGreaterEqual(len(stage_keys), 28)

        rep_skip = suite.run_fx3_vm_coemulation_suite(
            suite.CoEmulationConfig(
                force_clean_room=True,
                include_phase162_realhw_cfexpress_ufu_5tier_hil=False,
            )
        )
        self.assertTrue(rep_skip["all_checks_passed"])
        self.assertNotIn("stage28_realhw_cfexpress_ufu_5tier_hil", rep_skip)
        self.assertEqual(
            len([k for k in rep_skip if re.match(r"^stage\d+_", k)]),
            len(stage_keys) - 1,
        )

    def test_39_suite_subprocess_summary_and_skip_phase162_flag(self) -> None:
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
        self.assertIn("realhw_cfexpress_ufu_5tier_hil=CLEAN_ROOM_SYNTHETIC", proc.stdout)

        proc_skip = subprocess.run(
            [
                sys.executable,
                "-B",
                str(FX3_VM_DIR / "fx3_vm_coemulation_suite.py"),
                "--clean-room",
                "--skip-phase162",
                "--summary",
            ],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc_skip.returncode, 0, msg=proc_skip.stderr)
        self.assertNotIn("realhw_cfexpress_ufu_5tier_hil=", proc_skip.stdout)

    def test_40_suite_28_stages_clean_room_lt_1p1s_and_local_lt_2p5s_and_json_cli(self) -> None:
        t0 = time.monotonic()
        rep_clean = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig(force_clean_room=True))
        dt_clean = time.monotonic() - t0
        self.assertTrue(rep_clean["all_checks_passed"])
        self.assertGreaterEqual(len([k for k in rep_clean if re.match(r"^stage\d+_", k)]), 28)
        self.assertLess(dt_clean, 1.10)

        t1 = time.monotonic()
        rep_mode = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig())
        dt_mode = time.monotonic() - t1
        self.assertTrue(rep_mode["all_checks_passed"])
        self.assertGreaterEqual(len([k for k in rep_mode if re.match(r"^stage\d+_", k)]), 28)
        self.assertLess(dt_mode, 2.50)

        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        p_clean = subprocess.run(
            [
                sys.executable,
                "-B",
                str(FX3_VM_DIR / "fx3_vm_coemulation_suite.py"),
                "--clean-room",
                "--json",
            ],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(p_clean.returncode, 0, msg=p_clean.stderr)
        d_clean = json.loads(p_clean.stdout)
        self.assertTrue(d_clean["all_checks_passed"])
        self.assertGreaterEqual(len([k for k in d_clean if re.match(r"^stage\d+_", k)]), 28)

    def test_41_all_28_stages_present_and_passing_in_suite_report(self) -> None:
        rep = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig(force_clean_room=True))
        self.assertTrue(rep["stage1_coldboot_and_bt"]["all_checks_passed"])
        self.assertTrue(rep["stage2_dual_isa_cp_shooting"]["all_checks_passed"])
        self.assertTrue(rep["stage3_soft_gpe_hud_ramfb"]["all_checks_passed"])
        for idx in range(4, 29):
            matches = [k for k in rep if k.startswith(f"stage{idx}_")]
            self.assertEqual(len(matches), 1, msg=f"Missing or duplicate stage{idx}_* key")
            self.assertTrue(rep[matches[0]]["all_checks_passed"])

    def test_42_stage28_no_raw_bytes_repr_or_nan_in_json(self) -> None:
        rep = _get_clean_room_audit()
        rendered = json.dumps(rep, allow_nan=False)
        self.assertNotRegex(rendered, r"(?<![0-9A-Za-z_/.-])b[\'\"]")
        self.assertIsNone(re.search(r"NaN|Infinity", rendered))

        rep_suite = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig(force_clean_room=True))
        rendered_suite = json.dumps(rep_suite, allow_nan=False)
        self.assertNotRegex(rendered_suite, r"(?<![0-9A-Za-z_/.-])b[\'\"]")
        self.assertIsNone(re.search(r"NaN|Infinity", rendered_suite))

    def test_43_source_hygiene_o_rdonly_and_no_write_flags_or_forbidden_port(self) -> None:
        src = (FX3_VM_DIR / "realhw_cfexpress_ufu_and_5tier_recovery_coemulator.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("os.O_RDONLY", src)
        self.assertNotIn("os.O_WRONLY", src)
        self.assertNotIn("os.O_RDWR", src)
        self.assertNotIn("87" + "68", src)
        self.assertIn("sys.dont_write_bytecode = True", src)

    def test_44_audit_digest_sha256_deterministic_across_repeated_runs(self) -> None:
        r1 = p162.run_phase162_realhw_cfexpress_ufu_5tier_hil(force_clean_room=True)
        r2 = p162.run_phase162_realhw_cfexpress_ufu_5tier_hil(force_clean_room=True)
        self.assertEqual(len(r1["audit_digest_sha256"]), 64)
        self.assertEqual(r1["audit_digest_sha256"], r2["audit_digest_sha256"])

    def test_45_read_bounded_rdonly_never_reads_more_than_4k(self) -> None:
        da = p162.inspect_phase162_donors(force_clean_room=True)
        self.assertEqual(da.fx3_bodydata_header.file_bytes, p162.EXPECTED_FX3_BODYDATA_BYTES)
        self.assertLessEqual(da.fx3_bodydata_header.bytes_read, 4096)
        self.assertTrue(da.fx3_bodydata_header.bounded_header_only)
        self.assertEqual(da.fx6_bodydata_header.file_bytes, p162.EXPECTED_FX6_BODYDATA_BYTES)
        self.assertLessEqual(da.fx6_bodydata_header.bytes_read, 4096)
        self.assertTrue(da.fx6_bodydata_header.bounded_header_only)

    def test_46_suite_phase162_digest_propagated_and_nonzero_stage_count(self) -> None:
        rep = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig(force_clean_room=True))
        s28 = rep["stage28_realhw_cfexpress_ufu_5tier_hil"]
        self.assertEqual(
            s28["phase162_audit_digest_sha256"],
            _get_clean_room_audit()["audit_digest_sha256"],
        )
        self.assertEqual(len(rep["audit_digest_sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
