"""Dual-mode unit tests for Phase 176 Pillar 23: p5:/wbi (WBI2/hibdrv.ko)
contamination firewall, NP-FZ100 battery-pull/6.3V brownout recovery &
100-cycle H0 -> H1 -> H2 -> H3 invariance verifier.
"""

from __future__ import annotations

import errno
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import unittest
from unittest import mock


ADAPTER_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ADAPTER_ROOT.parents[1]
if str(ADAPTER_ROOT) not in sys.path:
    sys.path.insert(0, str(ADAPTER_ROOT))

import fx3_recovery  # noqa: E402
from fx3_recovery import (  # noqa: E402
    BLOCKED_EH3_LIBJIT_CRC32_TAMPER,
    BLOCKED_EMMC_BIT_DRIFT_DETECTED,
    BLOCKED_HIBDRV_WRITE_EROFS,
    BLOCKED_MISSING_WBI_RECEIPT_HASH,
    BLOCKED_SUSPEND_DISK_MASKED,
    BLOCKED_WBI_BLKROSET_UNLOCKED,
    BLOCKED_WBI_RESUME_NOT_BYPASSED,
    EVENT_BATTERY_PULL_BIG6_MENU,
    EVENT_BOOT_STOCK_H0,
    EVENT_BROWNOUT_6V3_REC_RSV,
    EVENT_CLEAN_UNINSTALL_H2_H3,
    EVENT_EH1_SD_EJECT_47US,
    EVENT_EH2_DISP_MENU_SHUTTER,
    EVENT_EH3_LIBJIT_1BYTE_CRC32_TAMPER,
    EVENT_STAGE_A_TO_STAGE_B,
    EVENT_UFU_BODYDATA_COLDBOOT,
    P166_FX3RCPT1_FLAGS_DUAL_MEDIA_READY,
    P176_100CYCLE_COUNT,
    P176_CRITICAL_16_SURFACE_IDS,
    P176_CRITICAL_CAL_CERT_PARTITIONS,
    P176_EH1_MAX_BYPASS_US,
    P176_EH3_MAX_FALLBACK_US,
    P176_FX3_MODEL_ID,
    P176_FX3_MODEL_NAME,
    P176_FX3_STOCK_VERSION,
    P176_KERNEL_RELEASE,
    P176_PILLAR_23A_SCENARIO_IDS,
    P176_PILLAR_23B_SCENARIO_IDS,
    P176_PINNED_FX3_WBI2_HDR_SHA256,
    P176_PINNED_FX3_WBI2_SECTIONS,
    P176_PINNED_FX3_WBI2_TABLE_SHA256,
    P176_PINNED_FX3_WBI2_TOTAL_BYTES,
    P176_SOC_NAME,
    P176_STATUS_VERIFIED_PILLAR_23A,
    P176_STATUS_VERIFIED_PILLAR_23B,
    P176_STATUS_VERIFIED_SUITE,
    P176_UFU_MAX_BYPASS_US,
    P176_WBI_DEVICE_NODES,
    P176_WBI_INVALID_MAGICS,
    P176_WBI_MAGIC_ASCII,
    P176_WBI_PARTITION_BYTES,
    PHASE176_SCHEMA,
    PHASE176_VERSION,
    STATE_H0_STOCK_FX3,
    STATE_H2_STAGE_B_LIVE,
    STATE_H3_STOCK_UNINSTALLED,
    WBI_PERSISTENT_WRITES,
    build_fx3rcpt1_receipt,
    build_synthetic_16_surface_chunks,
    evaluate_stage_a_wbi_coldboot_entry,
    evaluate_tier0_fx3rcpt1_wbi_prerequisite,
    inspect_phase176_wbi_donors_readonly,
    intercept_sys_power_state_write,
    run_100cycle_transition_simulation,
    run_pillar23a_wbi_contamination_firewall_suite,
    run_pillar23b_powerloss_and_100cycle_suite,
    run_wbi_powerloss_and_100cycle_suite,
    simulate_hibdrv_write_under_blkroset,
)
from fx3_recovery import realhw_wbi_powerloss_and_100cycle_transition_verifier as p176  # noqa: E402


def _contains_raw_bytes(obj: object) -> bool:
    if isinstance(obj, (bytes, bytearray, memoryview)):
        return True
    if isinstance(obj, dict):
        return any(_contains_raw_bytes(k) or _contains_raw_bytes(v) for k, v in obj.items())
    if isinstance(obj, (list, tuple)):
        return any(_contains_raw_bytes(v) for v in obj)
    return False


class TestPhase176SafetyAndExports(unittest.TestCase):
    def test_01_hard_locked_safety_constants(self) -> None:
        self.assertFalse(p176.PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(p176.SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(p176.EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        self.assertFalse(p176.ISP_WRITE_AUTHORIZED)
        self.assertFalse(p176.PERSISTENT_WRITE_RELEASE)
        self.assertFalse(p176.ALLOW_BOOT_PARTITION_TARGETING)
        self.assertFalse(p176.ALLOW_DESTRUCTIVE_FASTBOOT)
        self.assertTrue(p176.READ_ONLY_DONOR_ACCESS)

    def test_02_zero_counter_invariants(self) -> None:
        self.assertEqual(p176.OTP_FUSE_TOUCHES, 0)
        self.assertEqual(p176.OTP_FUSE_WRITES, 0)
        self.assertEqual(p176.RPMB_COUNTER_INCREMENTS, 0)
        self.assertEqual(p176.PASSIVE_TX_BYTES_EMITTED, 0)
        self.assertEqual(p176.PHYSICAL_USB_PACKETS_EMITTED, 0)
        self.assertEqual(p176.PHYSICAL_DEVICE_WRITES, 0)
        self.assertEqual(p176.WBI_PERSISTENT_WRITES, 0)
        self.assertEqual(p176.RAW_FIRMWARE_BYTES_LEAKED, 0)

    def test_03_package_exports_and_non_shadowing(self) -> None:
        self.assertIn("run_wbi_powerloss_and_100cycle_suite", fx3_recovery.__all__)
        self.assertIn("realhw_wbi_powerloss_and_100cycle_transition_verifier", fx3_recovery.__all__)
        self.assertNotIn("annotations", fx3_recovery.__all__)
        self.assertIs(fx3_recovery.run_wbi_powerloss_and_100cycle_suite, run_wbi_powerloss_and_100cycle_suite)
        self.assertFalse(fx3_recovery.PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(fx3_recovery.SPI_NOR_WRITE_AUTHORIZED)
        self.assertEqual(fx3_recovery.MASTER_22_PILLAR_COUNT, 22)

    def test_04_pinned_fx3_hardware_constants(self) -> None:
        self.assertEqual(P176_FX3_MODEL_ID, 0x91030080)
        self.assertEqual(P176_FX3_MODEL_NAME, "ILME-FX3")
        self.assertEqual(P176_FX3_STOCK_VERSION, "7.02")
        self.assertEqual(P176_KERNEL_RELEASE, "4.9.337-scel+")
        self.assertEqual(P176_SOC_NAME, "CXD90057")
        self.assertEqual(P176_WBI_DEVICE_NODES, ("/dev/nflasha5", "/dev/pnflasha5"))
        self.assertEqual(P176_WBI_PARTITION_BYTES, 314_572_800)
        self.assertEqual(P176_100CYCLE_COUNT, 100)
        self.assertEqual(len(P176_CRITICAL_16_SURFACE_IDS), 16)
        self.assertEqual(P176_CRITICAL_CAL_CERT_PARTITIONS, ("p2", "p5", "p12", "p18"))

    def test_05_scenario_id_counts(self) -> None:
        self.assertEqual(len(P176_PILLAR_23A_SCENARIO_IDS), 8)
        self.assertEqual(len(P176_PILLAR_23B_SCENARIO_IDS), 8)
        self.assertEqual(len(set(P176_PILLAR_23A_SCENARIO_IDS)), 8)
        self.assertEqual(len(set(P176_PILLAR_23B_SCENARIO_IDS)), 8)


class TestPhase176DonorInspection(unittest.TestCase):
    def test_06_clean_room_donor_snapshot_exact(self) -> None:
        snap = inspect_phase176_wbi_donors_readonly(force_clean_room=True)
        self.assertTrue(snap.all_passed)
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(snap.access_mode, "SYNTHETIC_METADATA_ONLY")
        self.assertEqual(snap.donor_files_inspected, 0)
        self.assertEqual(snap.raw_firmware_bytes_leaked, 0)
        self.assertEqual(snap.wbi2_magic_ascii, P176_WBI_MAGIC_ASCII)
        self.assertEqual(snap.wbi2_sections, P176_PINNED_FX3_WBI2_SECTIONS)
        self.assertEqual(snap.wbi2_hdr_sha256, P176_PINNED_FX3_WBI2_HDR_SHA256)
        self.assertEqual(snap.wbi2_table_sha256, P176_PINNED_FX3_WBI2_TABLE_SHA256)
        self.assertTrue(snap.partinf_p5_wbi_verified)
        self.assertTrue(snap.mount_conf_wbi_verified)
        self.assertTrue(snap.kemco_wbi_mem_verified)
        self.assertTrue(snap.init_setup_nflash_verified)
        self.assertTrue(snap.vmlinux_pm_suspend_verified)
        self.assertTrue(snap.bodydata_ufu_header_verified)
        self.assertEqual(len(snap.artifacts), 9)
        self.assertLess(snap.elapsed_seconds, 0.25)

    def test_07_default_mode_donor_inspection_and_parity(self) -> None:
        snap = inspect_phase176_wbi_donors_readonly()
        self.assertTrue(snap.all_passed)
        self.assertIn(snap.verification_mode, ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"))
        self.assertEqual(snap.raw_firmware_bytes_leaked, 0)
        self.assertEqual(snap.wbi2_sections, P176_PINNED_FX3_WBI2_SECTIONS)
        self.assertEqual(snap.wbi2_hdr_sha256, P176_PINNED_FX3_WBI2_HDR_SHA256)
        self.assertEqual(snap.wbi2_table_sha256, P176_PINNED_FX3_WBI2_TABLE_SHA256)
        self.assertEqual(len(snap.artifacts), 9)
        self.assertLess(snap.elapsed_seconds, 1.0)
        if os.environ.get("FX3_FX6_FORCE_CLEAN_ROOM") != "1":
            self.assertEqual(snap.verification_mode, "LOCAL_DONOR_O_RDONLY")
            self.assertEqual(snap.donor_files_inspected, 9)
            self.assertEqual(snap.artifacts[0].byte_length, P176_PINNED_FX3_WBI2_TOTAL_BYTES)

    def test_08_donor_snapshot_json_safe_and_zero_raw_bytes(self) -> None:
        for mode_flag in (None, True):
            snap = inspect_phase176_wbi_donors_readonly(force_clean_room=mode_flag)
            d = snap.to_dict()
            self.assertFalse(_contains_raw_bytes(d))
            encoded = json.dumps(d, sort_keys=True, allow_nan=False)
            self.assertNotIn("0x7fELF", encoded)
            self.assertIn("wbi2_table_sha256", encoded)

    def test_09_donor_snapshot_deterministic_digest(self) -> None:
        s1 = inspect_phase176_wbi_donors_readonly(force_clean_room=True)
        s2 = inspect_phase176_wbi_donors_readonly(force_clean_room=True)
        self.assertEqual(s1.snapshot_sha256, s2.snapshot_sha256)


class TestPhase176Pillar23AWbiFirewall(unittest.TestCase):
    def test_10_wbi_s1_stage_a_coldboot_forced_bypass(self) -> None:
        dec = evaluate_stage_a_wbi_coldboot_entry(sd_inserted=True, wbi_resume_bypass_env="1")
        self.assertTrue(dec.passed)
        self.assertFalse(dec.wbi_resume_attempted)
        self.assertTrue(dec.cold_boot_enforced)
        self.assertTrue(dec.wbi_resume_bypassed)
        self.assertEqual(dec.wbi_persistent_writes, 0)

    def test_11_wbi_s1_rejects_missing_wbi_resume_bypass_env(self) -> None:
        dec = evaluate_stage_a_wbi_coldboot_entry(sd_inserted=True, wbi_resume_bypass_env="0")
        self.assertFalse(dec.passed)
        self.assertIn(BLOCKED_WBI_RESUME_NOT_BYPASSED, dec.blocked_codes)

    def test_12_wbi_s1_rejects_missing_noresume_kernel_arg(self) -> None:
        dec = evaluate_stage_a_wbi_coldboot_entry(
            sd_inserted=True,
            wbi_resume_bypass_env="1",
            bootargs="console=ttyAMA0,460800n8 rootwait ro",
        )
        self.assertFalse(dec.passed)
        self.assertIn(BLOCKED_WBI_RESUME_NOT_BYPASSED, dec.blocked_codes)

    def test_13_wbi_s1_allows_wbi_resume_zero_alias_with_noresume(self) -> None:
        dec = evaluate_stage_a_wbi_coldboot_entry(
            sd_inserted=True,
            wbi_resume_bypass_env="1",
            bootargs="noresume wbi.resume=0",
        )
        self.assertTrue(dec.passed)
        self.assertTrue(dec.cold_boot_enforced)

    def test_14_wbi_s2_blkroset_lock_enforced_for_both_nodes(self) -> None:
        for node in ("/dev/nflasha5", "/dev/pnflasha5"):
            res = simulate_hibdrv_write_under_blkroset(
                device_node=node,
                blkroset_nflasha5=1,
                blkroset_pnflasha5=1,
            )
            self.assertTrue(res.passed)
            self.assertTrue(res.blkroset_locked)
            self.assertTrue(res.write_rejected)
            self.assertEqual(res.returned_errno, errno.EROFS)
            self.assertEqual(res.errno_name, "EROFS")
            self.assertEqual(res.wbi_persistent_writes, 0)
            self.assertIn(BLOCKED_HIBDRV_WRITE_EROFS, res.blocked_codes)

    def test_15_wbi_s2_rejects_unlocked_nflasha5_or_pnflasha5(self) -> None:
        r1 = simulate_hibdrv_write_under_blkroset(device_node="/dev/nflasha5", blkroset_nflasha5=0, blkroset_pnflasha5=1)
        r2 = simulate_hibdrv_write_under_blkroset(device_node="/dev/pnflasha5", blkroset_nflasha5=1, blkroset_pnflasha5=0)
        self.assertFalse(r1.passed)
        self.assertFalse(r2.passed)
        self.assertIn(BLOCKED_WBI_BLKROSET_UNLOCKED, r1.blocked_codes)
        self.assertIn(BLOCKED_WBI_BLKROSET_UNLOCKED, r2.blocked_codes)
        d_entry = evaluate_stage_a_wbi_coldboot_entry(sd_inserted=True, blkroset_nflasha5=1, blkroset_pnflasha5=0)
        self.assertFalse(d_entry.passed)
        self.assertIn(BLOCKED_WBI_BLKROSET_UNLOCKED, d_entry.blocked_codes)

    def test_16_wbi_s2_rejects_unknown_device_node(self) -> None:
        res = simulate_hibdrv_write_under_blkroset(
            device_node="/dev/nflasha1",
            blkroset_nflasha5=1,
            blkroset_pnflasha5=1,
        )
        self.assertFalse(res.passed)
        self.assertTrue(any("Unexpected WBI target node" in e for e in res.errors))

    def test_17_wbi_s3_eh1_sd_eject_under_50us(self) -> None:
        dec = evaluate_stage_a_wbi_coldboot_entry(sd_inserted=False)
        self.assertTrue(dec.passed)
        self.assertTrue(dec.stage_b_bypassed)
        self.assertLessEqual(dec.bypass_latency_us, P176_EH1_MAX_BYPASS_US)
        self.assertEqual(dec.wbi_persistent_writes, 0)

    def test_18_wbi_s4_stale_and_corrupt_wbi_magic_fallback(self) -> None:
        for bad_magic in P176_WBI_INVALID_MAGICS:
            dec = evaluate_stage_a_wbi_coldboot_entry(
                sd_inserted=False,
                p5_wbi_magic=bad_magic,
                p5_wbi_corrupted=True,
            )
            self.assertTrue(dec.passed, bad_magic)
            self.assertFalse(dec.wbi_resume_attempted, bad_magic)
            self.assertTrue(dec.cold_boot_enforced, bad_magic)
            self.assertTrue(dec.cold_ram_state, bad_magic)

    def test_19_wbi_s5_bodydata_ufu_coldboot_coexistence(self) -> None:
        dec = evaluate_stage_a_wbi_coldboot_entry(
            sd_inserted=True,
            bodydata_ufu_present=True,
            bodydata_ufu_magic_valid=True,
        )
        self.assertTrue(dec.passed)
        self.assertTrue(dec.stage_b_bypassed)
        self.assertTrue(dec.wbi_resume_bypassed)
        self.assertFalse(dec.wbi_resume_attempted)
        self.assertTrue(dec.cold_ram_state)
        self.assertLess(dec.bypass_latency_us, P176_UFU_MAX_BYPASS_US)

    def test_20_wbi_s5_rejects_invalid_bodydata_magic_or_missing_noresume(self) -> None:
        bad_magic = evaluate_stage_a_wbi_coldboot_entry(
            sd_inserted=True,
            bodydata_ufu_present=True,
            bodydata_ufu_magic_valid=False,
        )
        self.assertFalse(bad_magic.passed)
        bad_args = evaluate_stage_a_wbi_coldboot_entry(
            sd_inserted=True,
            bodydata_ufu_present=True,
            bodydata_ufu_magic_valid=True,
            bootargs="console=ttyAMA0",
        )
        self.assertFalse(bad_args.passed)
        self.assertIn(BLOCKED_WBI_RESUME_NOT_BYPASSED, bad_args.blocked_codes)

    def test_21_wbi_s6_pm_suspend_disk_masked_in_stage_b(self) -> None:
        for state in ("disk", "PM_SUSPEND_DISK", "hibernate", "wbi2"):
            res = intercept_sys_power_state_write(stage_b_active=True, requested_state=state)
            self.assertTrue(res.passed)
            self.assertTrue(res.intercepted_to_noop)
            self.assertFalse(res.hibdrv_triggered)
            self.assertEqual(res.wbi_persistent_writes, 0)
            self.assertIn(BLOCKED_SUSPEND_DISK_MASKED, res.blocked_codes)

    def test_22_wbi_s6_mem_suspend_and_inactive_stage_b_passthrough(self) -> None:
        mem_res = intercept_sys_power_state_write(stage_b_active=True, requested_state="mem")
        self.assertTrue(mem_res.passed)
        self.assertFalse(mem_res.intercepted_to_noop)
        self.assertFalse(mem_res.hibdrv_triggered)
        stock_res = intercept_sys_power_state_write(stage_b_active=False, requested_state="disk")
        self.assertTrue(stock_res.passed)
        self.assertFalse(stock_res.intercepted_to_noop)
        self.assertEqual(stock_res.blocked_codes, ())

    def test_23_wbi_s8_fx3rcpt1_prerequisite_accepts_valid_dual_media(self) -> None:
        _, p2_files, p18_files = build_synthetic_16_surface_chunks(body_tag="fx3-p176-rcpt")
        rcpt = build_fx3rcpt1_receipt(
            body_serial_sha256=sha256(b"SER1").hexdigest(),
            emmc_cid_sha256=sha256(b"CID1").hexdigest(),
            manifest_sha256=sha256(b"MAN1").hexdigest(),
            p2_cal_bundle_sha256=sha256(json.dumps(p2_files, sort_keys=True).encode()).hexdigest(),
            p18_lensfile_sha256=sha256(json.dumps(p18_files, sort_keys=True).encode()).hexdigest(),
            flags=P166_FX3RCPT1_FLAGS_DUAL_MEDIA_READY,
        )
        wbi_sha = P176_PINNED_FX3_WBI2_TABLE_SHA256
        gate = evaluate_tier0_fx3rcpt1_wbi_prerequisite(
            receipt_bytes=rcpt,
            p5_wbi_sha256_media_a=wbi_sha,
            p5_wbi_sha256_media_b=wbi_sha,
            media_a_device_id="nvme0n1",
            media_b_device_id="disk4s1",
        )
        self.assertTrue(gate.passed)
        self.assertTrue(gate.stage_b_activation_permitted)
        self.assertTrue(gate.dual_media_distinct)
        self.assertTrue(gate.p5_wbi_baseline_present)
        self.assertTrue(gate.p5_wbi_baseline_match)

    def test_24_wbi_s8_rejects_missing_or_mismatched_p5_wbi_hash(self) -> None:
        rcpt = build_fx3rcpt1_receipt(
            body_serial_sha256=sha256(b"SER1").hexdigest(),
            emmc_cid_sha256=sha256(b"CID1").hexdigest(),
            manifest_sha256=sha256(b"MAN1").hexdigest(),
            p2_cal_bundle_sha256=sha256(b"P2").hexdigest(),
            p18_lensfile_sha256=sha256(b"P18").hexdigest(),
            flags=P166_FX3RCPT1_FLAGS_DUAL_MEDIA_READY,
        )
        g_missing = evaluate_tier0_fx3rcpt1_wbi_prerequisite(
            receipt_bytes=rcpt,
            p5_wbi_sha256_media_a=P176_PINNED_FX3_WBI2_TABLE_SHA256,
            p5_wbi_sha256_media_b="",
            media_a_device_id="nvme0n1",
            media_b_device_id="disk4s1",
        )
        self.assertFalse(g_missing.passed)
        self.assertFalse(g_missing.stage_b_activation_permitted)
        self.assertIn(BLOCKED_MISSING_WBI_RECEIPT_HASH, g_missing.blocked_codes)

        g_mismatch = evaluate_tier0_fx3rcpt1_wbi_prerequisite(
            receipt_bytes=rcpt,
            p5_wbi_sha256_media_a=P176_PINNED_FX3_WBI2_TABLE_SHA256,
            p5_wbi_sha256_media_b="0" * 64,
            media_a_device_id="nvme0n1",
            media_b_device_id="disk4s1",
        )
        self.assertFalse(g_mismatch.passed)
        self.assertFalse(g_mismatch.p5_wbi_baseline_match)

    def test_25_wbi_s8_rejects_same_physical_device_or_bad_receipt(self) -> None:
        rcpt = build_fx3rcpt1_receipt(
            body_serial_sha256=sha256(b"SER1").hexdigest(),
            emmc_cid_sha256=sha256(b"CID1").hexdigest(),
            manifest_sha256=sha256(b"MAN1").hexdigest(),
            p2_cal_bundle_sha256=sha256(b"P2").hexdigest(),
            p18_lensfile_sha256=sha256(b"P18").hexdigest(),
            flags=P166_FX3RCPT1_FLAGS_DUAL_MEDIA_READY,
        )
        g_same = evaluate_tier0_fx3rcpt1_wbi_prerequisite(
            receipt_bytes=rcpt,
            p5_wbi_sha256_media_a=P176_PINNED_FX3_WBI2_TABLE_SHA256,
            p5_wbi_sha256_media_b=P176_PINNED_FX3_WBI2_TABLE_SHA256,
            media_a_device_id="nvme0n1",
            media_b_device_id="nvme0n1",
        )
        self.assertFalse(g_same.passed)
        self.assertFalse(g_same.dual_media_distinct)

        g_bad_rcpt = evaluate_tier0_fx3rcpt1_wbi_prerequisite(
            receipt_bytes=b"\x00" * 528,
            p5_wbi_sha256_media_a=P176_PINNED_FX3_WBI2_TABLE_SHA256,
            p5_wbi_sha256_media_b=P176_PINNED_FX3_WBI2_TABLE_SHA256,
            media_a_device_id="nvme0n1",
            media_b_device_id="disk4s1",
        )
        self.assertFalse(g_bad_rcpt.passed)
        self.assertFalse(g_bad_rcpt.receipt_valid)

    def test_26_pillar_23a_full_8_scenario_suite(self) -> None:
        snap = inspect_phase176_wbi_donors_readonly(force_clean_room=True)
        res = run_pillar23a_wbi_contamination_firewall_suite(snap)
        self.assertTrue(res.passed)
        self.assertEqual(res.status, P176_STATUS_VERIFIED_PILLAR_23A)
        self.assertEqual(res.scenarios_passed, 8)
        self.assertEqual(res.scenarios_total, 8)
        self.assertEqual(res.wbi_persistent_writes, 0)
        self.assertFalse(res.persistent_emmc_writes_authorized)
        self.assertEqual(tuple(s.scenario_id for s in res.scenarios), P176_PILLAR_23A_SCENARIO_IDS)
        self.assertTrue(all(s.passed for s in res.scenarios))


class TestPhase176Pillar23BPowerlossAnd100Cycle(unittest.TestCase):
    def test_27_hundred_cycle_simulation_clean_room_exact(self) -> None:
        snap = inspect_phase176_wbi_donors_readonly(force_clean_room=True)
        sim = run_100cycle_transition_simulation(snap, cycles=100)
        self.assertTrue(sim.passed)
        self.assertEqual(sim.cycles_executed, 100)
        self.assertEqual(sim.cycles_passed, 100)
        self.assertEqual(sim.emmc_bit_drift_count, 0)
        self.assertEqual(sim.wbi_persistent_writes, 0)
        self.assertEqual(sim.persistent_emmc_writes, 0)
        self.assertEqual(sim.surfaces_total, 16)
        self.assertEqual(sim.surfaces_h0_eq_h3_exact, 16)
        self.assertTrue(sim.h0_equals_h3)
        self.assertEqual(sim.h0_16_surfaces_digest, sim.h3_16_surfaces_digest)
        self.assertEqual(sim.errors, ())
        self.assertEqual(sim.blocked_codes, ())

    def test_28_hundred_cycle_covers_all_9_event_types(self) -> None:
        sim = run_100cycle_transition_simulation(inspect_phase176_wbi_donors_readonly(force_clean_room=True))
        for ev in (
            EVENT_BOOT_STOCK_H0,
            EVENT_STAGE_A_TO_STAGE_B,
            EVENT_BATTERY_PULL_BIG6_MENU,
            EVENT_BROWNOUT_6V3_REC_RSV,
            EVENT_EH1_SD_EJECT_47US,
            EVENT_EH2_DISP_MENU_SHUTTER,
            EVENT_EH3_LIBJIT_1BYTE_CRC32_TAMPER,
            EVENT_UFU_BODYDATA_COLDBOOT,
            EVENT_CLEAN_UNINSTALL_H2_H3,
        ):
            self.assertGreater(sim.event_counts.get(ev, 0), 0, f"missing event coverage: {ev}")
        self.assertEqual(sum(sim.event_counts.values()), 100)

    def test_29_hundred_cycle_terminal_state_is_h3_and_samples_bounded(self) -> None:
        sim = run_100cycle_transition_simulation(inspect_phase176_wbi_donors_readonly(force_clean_room=True))
        self.assertGreater(len(sim.sample_records), 0)
        self.assertEqual(sim.sample_records[0].cycle_index, 1)
        self.assertEqual(sim.sample_records[0].start_state, STATE_H0_STOCK_FX3)
        self.assertEqual(sim.sample_records[0].end_state, STATE_H2_STAGE_B_LIVE)
        self.assertEqual(sim.sample_records[-1].cycle_index, 100)
        self.assertEqual(sim.sample_records[-1].end_state, STATE_H3_STOCK_UNINSTALLED)
        self.assertTrue(sim.sample_records[-1].h0_baseline_16_surfaces_match)

    def test_30_1bit_emmc_drift_injection_fails_closed(self) -> None:
        snap = inspect_phase176_wbi_donors_readonly(force_clean_room=True)
        sim = run_100cycle_transition_simulation(snap, cycles=100, inject_1bit_emmc_drift_at_cycle=57)
        self.assertFalse(sim.passed)
        self.assertGreaterEqual(sim.emmc_bit_drift_count, 1)
        self.assertLess(sim.surfaces_h0_eq_h3_exact, 16)
        self.assertFalse(sim.h0_equals_h3)
        self.assertNotEqual(sim.h0_16_surfaces_digest, sim.h3_16_surfaces_digest)
        self.assertIn(BLOCKED_EMMC_BIT_DRIFT_DETECTED, sim.blocked_codes)
        self.assertLess(sim.cycles_passed, 100)

    def test_31_invalid_cycle_count_rejected(self) -> None:
        snap = inspect_phase176_wbi_donors_readonly(force_clean_room=True)
        with self.assertRaises(ValueError):
            run_100cycle_transition_simulation(snap, cycles=0)

    def test_32_pillar_23b_full_8_scenario_suite(self) -> None:
        snap = inspect_phase176_wbi_donors_readonly(force_clean_room=True)
        res = run_pillar23b_powerloss_and_100cycle_suite(snap)
        self.assertTrue(res.passed)
        self.assertEqual(res.status, P176_STATUS_VERIFIED_PILLAR_23B)
        self.assertEqual(res.scenarios_passed, 8)
        self.assertEqual(res.scenarios_total, 8)
        self.assertEqual(res.cycles_executed, 100)
        self.assertEqual(res.cycles_passed, 100)
        self.assertEqual(res.emmc_bit_drift_count, 0)
        self.assertEqual(res.wbi_persistent_writes, 0)
        self.assertTrue(res.h0_equals_h3)
        self.assertEqual(res.surfaces_h0_eq_h3_exact, 16)
        self.assertEqual(tuple(s.scenario_id for s in res.scenarios), P176_PILLAR_23B_SCENARIO_IDS)
        self.assertTrue(all(s.passed for s in res.scenarios))

    def test_33_eh3_scenario_records_tamper_code_and_sub_ms_latency(self) -> None:
        res = run_pillar23b_powerloss_and_100cycle_suite(inspect_phase176_wbi_donors_readonly(force_clean_room=True))
        eh3 = [s for s in res.scenarios if s.scenario_id == "PWR_S6_EH3_LIBJIT_1BYTE_CRC32_TAMPER"][0]
        self.assertTrue(eh3.passed)
        self.assertIn(BLOCKED_EH3_LIBJIT_CRC32_TAMPER, eh3.blocked_codes)
        self.assertLess(p176.P176_EH3_NOMINAL_FALLBACK_US, P176_EH3_MAX_FALLBACK_US)


class TestPhase176TopLevelSuiteAndCli(unittest.TestCase):
    def test_34_top_level_suite_default_mode_passes(self) -> None:
        t0 = time.monotonic()
        rep = run_wbi_powerloss_and_100cycle_suite()
        dt = time.monotonic() - t0
        self.assertTrue(rep.all_passed)
        self.assertEqual(rep.schema, PHASE176_SCHEMA)
        self.assertEqual(rep.version, PHASE176_VERSION)
        self.assertEqual(rep.status, P176_STATUS_VERIFIED_SUITE)
        self.assertLess(dt, 5.0)
        self.assertTrue(rep.under_1s_budget)
        self.assertEqual(rep.pillar_23a_wbi_firewall.scenarios_passed, 8)
        self.assertEqual(rep.pillar_23b_powerloss_100cycle.scenarios_passed, 8)
        self.assertEqual(rep.pillar_23b_powerloss_100cycle.cycles_passed, 100)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.spi_nor_write_authorized)
        self.assertFalse(rep.el3_payload_transmit_authorized)
        self.assertFalse(rep.isp_write_authorized)
        self.assertEqual(rep.otp_fuse_touches, 0)
        self.assertEqual(rep.rpmb_counter_increments, 0)
        self.assertEqual(rep.physical_usb_packets_emitted, 0)
        self.assertEqual(rep.wbi_persistent_writes, 0)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_35_top_level_suite_clean_room_passes(self) -> None:
        rep = run_wbi_powerloss_and_100cycle_suite(force_clean_room=True)
        self.assertTrue(rep.all_passed)
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(rep.under_1s_budget)
        self.assertEqual(rep.errors, ())

    def test_36_top_level_suite_deterministic_sha_in_clean_room(self) -> None:
        r1 = run_wbi_powerloss_and_100cycle_suite(force_clean_room=True)
        r2 = run_wbi_powerloss_and_100cycle_suite(force_clean_room=True)
        self.assertEqual(r1.suite_sha256, r2.suite_sha256)
        self.assertEqual(r1.pillar_23b_powerloss_100cycle.hundred_cycle_report.h0_16_surfaces_digest,
                         r2.pillar_23b_powerloss_100cycle.hundred_cycle_report.h0_16_surfaces_digest)

    def test_37_top_level_report_to_dict_zero_raw_bytes(self) -> None:
        rep = run_wbi_powerloss_and_100cycle_suite(force_clean_room=True)
        d = rep.to_dict()
        self.assertFalse(_contains_raw_bytes(d))
        raw = json.dumps(d, sort_keys=True, allow_nan=False)
        parsed = json.loads(raw)
        self.assertEqual(parsed["schema"], PHASE176_SCHEMA)
        self.assertTrue(parsed["all_passed"])

    def test_38_cli_json_and_force_clean_room(self) -> None:
        env = dict(os.environ)
        env["PYTHONPATH"] = str(ADAPTER_ROOT)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        proc = subprocess.run(
            [sys.executable, "-B", "-m", "fx3_recovery", "verify-wbi-powerloss-recovery", "--force-clean-room", "--json"],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["verification_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(payload["all_passed"])
        self.assertEqual(payload["wbi_persistent_writes"], 0)
        self.assertEqual(payload["raw_firmware_bytes_leaked"], 0)

    def test_39_cli_default_mode_and_out_directory(self) -> None:
        env = dict(os.environ)
        env["PYTHONPATH"] = str(ADAPTER_ROOT)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        out_dir = REPO_ROOT / "work" / "_tests" / f"test_p176_cli_out_{os.getpid()}"
        if out_dir.exists():
            shutil.rmtree(out_dir)
        out_dir.parent.mkdir(parents=True, exist_ok=True)
        try:
            proc = subprocess.run(
                [sys.executable, "-B", "-m", "fx3_recovery", "verify-wbi-powerloss-recovery", "--out", str(out_dir)],
                cwd=str(REPO_ROOT),
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
            self.assertIn("status=VERIFIED_PILLAR23_WBI_POWERLOSS_AND_100CYCLE_RECOVERY", proc.stdout)
            self.assertIn("cycles=100/100", proc.stdout)
            self.assertIn("h0_equals_h3=True", proc.stdout)
            out_json = out_dir / "wbi-powerloss-100cycle-report.json"
            self.assertTrue(out_json.is_file())
            loaded = json.loads(out_json.read_text(encoding="utf-8"))
            self.assertTrue(loaded["all_passed"])
        finally:
            if out_dir.exists():
                shutil.rmtree(out_dir)

    def test_40_master_22pillar_verifier_not_modified_and_intact(self) -> None:
        from fx3_recovery import verify_22pillar_recovery_suite
        rep22 = verify_22pillar_recovery_suite(force_clean_room=True)
        self.assertTrue(rep22.all_passed)
        self.assertEqual(rep22.pillar_count, 22)

    def test_41_wbi_invalid_magics_distinct_from_valid_wbi2(self) -> None:
        self.assertNotIn(P176_WBI_MAGIC_ASCII, P176_WBI_INVALID_MAGICS)
        self.assertIn("invl", P176_WBI_INVALID_MAGICS)
        self.assertIn("wbi2", P176_WBI_INVALID_MAGICS)
        self.assertIn("WBI3", P176_WBI_INVALID_MAGICS)

    def test_42_scenario_wbi_s7_cal_and_cert_co_invariance(self) -> None:
        res = run_pillar23a_wbi_contamination_firewall_suite(inspect_phase176_wbi_donors_readonly(force_clean_room=True))
        s7 = [s for s in res.scenarios if s.scenario_id == "WBI_S7_FACTORY_CAL_AND_CERT_RO_COINVARIANCE"][0]
        self.assertTrue(s7.passed)
        self.assertEqual(s7.wbi_persistent_writes, 0)
        self.assertEqual(s7.persistent_writes, 0)

    def test_43_deterministic_schedule_pattern_coverage(self) -> None:
        sched = p176._build_deterministic_100_cycle_schedule()
        self.assertEqual(len(sched), 100)
        self.assertEqual(sched[-1], EVENT_CLEAN_UNINSTALL_H2_H3)
        self.assertIn(EVENT_BATTERY_PULL_BIG6_MENU, sched)
        self.assertIn(EVENT_BROWNOUT_6V3_REC_RSV, sched)

    def test_44_missing_donor_root_triggers_clean_room_fallback(self) -> None:
        prev = os.environ.pop("FX3_FX6_FORCE_CLEAN_ROOM", None)
        missing_path = REPO_ROOT / "__fx3_fx6_clean_room_donor_disabled__" / "missing"
        try:
            with mock.patch.object(p176, "resolve_donor_path", return_value=missing_path):
                snap = inspect_phase176_wbi_donors_readonly(force_clean_room=None)
            self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertEqual(snap.donor_files_inspected, 0)
            self.assertTrue(snap.all_passed)
        finally:
            if prev is not None:
                os.environ["FX3_FX6_FORCE_CLEAN_ROOM"] = prev

    def test_45_env_force_clean_room_respected(self) -> None:
        prev = os.environ.get("FX3_FX6_FORCE_CLEAN_ROOM")
        os.environ["FX3_FX6_FORCE_CLEAN_ROOM"] = "1"
        try:
            rep = run_wbi_powerloss_and_100cycle_suite()
            self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertTrue(rep.all_passed)
        finally:
            if prev is None:
                os.environ.pop("FX3_FX6_FORCE_CLEAN_ROOM", None)
            else:
                os.environ["FX3_FX6_FORCE_CLEAN_ROOM"] = prev

    def test_46_single_cycle_simulation_edge_case(self) -> None:
        sim = run_100cycle_transition_simulation(
            inspect_phase176_wbi_donors_readonly(force_clean_room=True),
            cycles=1,
        )
        self.assertTrue(sim.passed)
        self.assertEqual(sim.cycles_executed, 1)
        self.assertEqual(sim.cycles_passed, 1)
        self.assertTrue(sim.h0_equals_h3)

    def test_47_negative_unknown_event_impossible_in_default_schedule(self) -> None:
        sched = p176._build_deterministic_100_cycle_schedule()
        self.assertTrue(all(ev in p176.P176_TRANSITION_EVENT_TYPES for ev in sched))

    def test_48_read_bounded_helpers_enforce_rdonly_and_reject_missing(self) -> None:
        with self.assertRaises(ValueError):
            p176._read_bounded_wbi2_rdonly("does-not-exist/nflasha5.img")
        with self.assertRaises(ValueError):
            p176._read_small_or_bounded_rdonly("does-not-exist/partinf.conf")

    def test_49_open_rdonly_regular_rejects_symlink(self) -> None:
        td = REPO_ROOT / "work" / "_tests" / f"test_p176_symlink_{os.getpid()}"
        if td.exists():
            shutil.rmtree(td)
        td.mkdir(parents=True, exist_ok=True)
        try:
            target = td / "real.bin"
            target.write_bytes(b"hello")
            link = td / "sym.bin"
            link.symlink_to(target)
            with self.assertRaises(ValueError) as ctx:
                p176._open_rdonly_regular(link)
            self.assertIn("symlink", str(ctx.exception).lower())
        finally:
            if td.exists():
                shutil.rmtree(td)

    def test_50_pillar23_status_strings_distinct_and_informative(self) -> None:
        statuses = {
            p176.P176_STATUS_VERIFIED_SUITE,
            p176.P176_STATUS_FAIL_SUITE,
            p176.P176_STATUS_VERIFIED_PILLAR_23A,
            p176.P176_STATUS_REJECTED_PILLAR_23A,
            p176.P176_STATUS_VERIFIED_PILLAR_23B,
            p176.P176_STATUS_REJECTED_PILLAR_23B,
        }
        self.assertEqual(len(statuses), 6)

    def test_51_cli_help_lists_verify_wbi_powerloss_recovery(self) -> None:
        env = dict(os.environ)
        env["PYTHONPATH"] = str(ADAPTER_ROOT)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        proc = subprocess.run(
            [sys.executable, "-B", "-m", "fx3_recovery", "--help"],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0)
        self.assertIn("verify-wbi-powerloss-recovery", proc.stdout)

    def test_52_wbi2_total_and_section_constants_positive(self) -> None:
        self.assertGreater(P176_PINNED_FX3_WBI2_TOTAL_BYTES, 0)
        self.assertEqual(P176_PINNED_FX3_WBI2_SECTIONS, 1399)
        self.assertEqual(len(P176_PINNED_FX3_WBI2_HDR_SHA256), 64)
        self.assertEqual(len(P176_PINNED_FX3_WBI2_TABLE_SHA256), 64)


if __name__ == "__main__":
    unittest.main()
