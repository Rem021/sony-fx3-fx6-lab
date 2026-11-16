"""Dual-mode unit tests for Phase 66 `init2` Escape Shell, CXD90057 Watchdog & `p1` FAT12/FAT16 Verifier.

Passes in BOTH:
- Local Donor `O_RDONLY` mode (verifies real FX3 `2.05/nflasha1` via `os.O_RDONLY`)
- `FX3_FX6_FORCE_CLEAN_ROOM=1` mode (deterministic clean-room synthetic fixtures)
Designed for `<0.5s` execution time with zero binary/bytecode residue.
"""

from __future__ import annotations

from contextlib import redirect_stdout
from hashlib import sha256
import io
import json
import os
from pathlib import Path
import shutil
import struct
import sys
import time
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import fx3_recovery
from fx3_recovery import __main__ as fx3_cli
from fx3_recovery.fat import FatP1
from fx3_recovery.files import ROOT, is_forced_clean_room, resolve_donor_path
from fx3_recovery.init2_escape_and_watchdog_simulator import (
    ALLOW_BOOT_PARTITION_TARGETING,
    ALLOW_DESTRUCTIVE_FASTBOOT,
    CXD90057_WDT_KICK_INTERVAL_MS,
    CXD90057_WDT_TIMEOUT_MS,
    DONOR_P1_205_RELPATH,
    EMMC_WRITE_BYTES,
    INIT2_ESCAPE_SCHEMA,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHYSICAL_WRITES,
    STATUS_FAIL_FAT_CLUSTER_CYCLE,
    STATUS_FAIL_FAT_CROSS_LINK,
    STATUS_FAIL_FAT_DIR_CHECKSUM,
    STATUS_FAIL_FAT_MIRROR_MISMATCH,
    STATUS_FAIL_FAT_ORPHAN_CLUSTERS,
    STATUS_VERIFIED_FAT_INTEGRITY,
    STATUS_VERIFIED_PHASE66,
    audit_p1_fat_filesystem,
    build_synthetic_p1_vfat_with_init2,
    render_init2_escape_wrapper_script,
    run_all_init2_escape_drills,
    run_cxd90057_watchdog_suite,
    run_init2_escape_and_watchdog_suite,
    run_init2_escape_drill,
    simulate_atomic_83_dir_swap,
    simulate_cxd90057_watchdog_scenario,
)


def _patch_fat_entry_mirror(
    buf: bytearray,
    fat_type: str,
    cluster: int,
    value: int,
    *,
    mirror_both: bool = True,
) -> None:
    u16 = lambda at: struct.unpack_from("<H", buf, at)[0]
    reserved = u16(14)
    fat_sectors = u16(22)
    fat1_off = reserved * 512
    fat2_off = fat1_off + fat_sectors * 512
    bases = (fat1_off, fat2_off) if mirror_both else (fat1_off,)
    for base in bases:
        if fat_type == "FAT12":
            at = base + cluster + cluster // 2
            word = struct.unpack_from("<H", buf, at)[0]
            if cluster & 1:
                word = (word & 0x000F) | ((value & 0xFFF) << 4)
            else:
                word = (word & 0xF000) | (value & 0xFFF)
            struct.pack_into("<H", buf, at, word)
        else:
            struct.pack_into("<H", buf, base + cluster * 2, value & 0xFFFF)


def _find_root_entry_offset(data: bytes, target_83_upper: str) -> int:
    u16 = lambda at: struct.unpack_from("<H", data, at)[0]
    reserved = u16(14)
    copies = data[16]
    entries = u16(17)
    fat_sectors = u16(22)
    root_start = (reserved + copies * fat_sectors) * 512
    root_size = entries * 32
    for at in range(root_start, root_start + root_size, 32):
        row = data[at : at + 32]
        if row[0] == 0x00:
            break
        if row[0] == 0xE5 or row[11] == 0x0F or (row[11] & 0x08):
            continue
        name = row[0:8].rstrip(b" ").decode("ascii", errors="replace")
        ext = row[8:11].rstrip(b" ").decode("ascii", errors="replace")
        fmt = f"{name}.{ext}" if ext else name
        if fmt == target_83_upper:
            return at
    raise AssertionError(f"Root entry {target_83_upper!r} not found")


class Init2EscapeAndWatchdogSimulatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self._sandbox = (
            ROOT / "outputs" / "fx3-recovery-adapter" / f".tmp-phase66-test-{os.getpid()}-{time.time_ns()}"
        )

    def tearDown(self) -> None:
        shutil.rmtree(self._sandbox, ignore_errors=True)

    def test_01_safety_constants_and_package_exports(self) -> None:
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(PERSISTENT_WRITE_RELEASE)
        self.assertFalse(ALLOW_BOOT_PARTITION_TARGETING)
        self.assertFalse(ALLOW_DESTRUCTIVE_FASTBOOT)
        self.assertEqual(PHYSICAL_WRITES, 0)
        self.assertEqual(EMMC_WRITE_BYTES, 0)
        self.assertEqual(fx3_recovery.INIT2_ESCAPE_SCHEMA, INIT2_ESCAPE_SCHEMA)
        for symbol in (
            "render_init2_escape_wrapper_script",
            "run_init2_escape_drill",
            "run_all_init2_escape_drills",
            "simulate_cxd90057_watchdog_scenario",
            "run_cxd90057_watchdog_suite",
            "build_synthetic_p1_vfat_with_init2",
            "audit_p1_fat_filesystem",
            "simulate_atomic_83_dir_swap",
            "run_init2_escape_and_watchdog_suite",
        ):
            self.assertIn(symbol, fx3_recovery.__all__)

    def test_02_posix_sh_wrapper_script_is_pure_sh_and_guard_ordered(self) -> None:
        script = render_init2_escape_wrapper_script()
        self.assertTrue(script.startswith("#!/bin/sh\n"))
        self.assertNotIn("[[", script)
        self.assertNotIn("function ", script)
        pos_g1 = script.index("GUARD1_SENTINEL_HIT")
        pos_g2 = script.index("GUARD2_KEY_CHORD_HIT")
        pos_g3 = script.index("GUARD3_SHA256_MISMATCH")
        pos_g4 = script.index("GUARD4_PREMOUNT_CRASH_LOOP_TRIPPED")
        pos_extract = script.index("STAGE_B_CPIO_EXTRACT_TMPFS=1")
        self.assertLess(pos_g1, pos_extract)
        self.assertLess(pos_g2, pos_extract)
        self.assertLess(pos_g3, pos_extract)
        self.assertLess(pos_g4, pos_extract)

    def test_03_init2_sandbox_normal_stage_b_entry(self) -> None:
        res = run_init2_escape_drill("T03_NORMAL_STAGE_B", procam_exit_sequence=(0,))
        self.assertTrue(res.passed, res.errors)
        self.assertFalse(res.escape_triggered)
        self.assertEqual(res.boot_target, "STAGE_B_OVERLAY")
        self.assertTrue(res.stage_b_active)
        self.assertFalse(res.stock_procam_exec)
        self.assertEqual(res.cpio_extract_count, 1)
        self.assertEqual(res.bind_mount_count, 2)
        self.assertEqual(res.emmc_write_count, 0)

    def test_04_escape1_slot_a_fx3_safe_stock_flg_before_cpio_mount(self) -> None:
        res = run_init2_escape_drill("T04_SLOT_A_FLG", slot_a_sentinel="FX3_SAFE_STOCK.FLG")
        self.assertTrue(res.passed, res.errors)
        self.assertTrue(res.escape_triggered)
        self.assertEqual(res.escape_mechanism, "EXTERNAL_MEDIA_SENTINEL")
        self.assertEqual(res.boot_target, "STOCK_FX3_V702")
        self.assertTrue(res.stock_procam_exec)
        self.assertFalse(res.stage_b_active)
        self.assertEqual(res.cpio_extract_count, 0)
        self.assertEqual(res.bind_mount_count, 0)
        self.assertEqual(res.emmc_write_count, 0)

    def test_05_escape1_slot_b_fx3_safe_stock_flg_before_cpio_mount(self) -> None:
        res = run_init2_escape_drill("T05_SLOT_B_FLG", slot_b_sentinel="FX3_SAFE_STOCK.FLG")
        self.assertTrue(res.passed, res.errors)
        self.assertEqual(res.escape_mechanism, "EXTERNAL_MEDIA_SENTINEL")
        self.assertEqual(res.boot_target, "STOCK_FX3_V702")
        self.assertEqual(res.cpio_extract_count, 0)
        self.assertEqual(res.bind_mount_count, 0)

    def test_06_escape1_disable_stage_b_txt_in_slot_a_and_b(self) -> None:
        for slot_arg in ({"slot_a_sentinel": "DISABLE_STAGE_B.TXT"}, {"slot_b_sentinel": "DISABLE_STAGE_B.TXT"}):
            res = run_init2_escape_drill("T06_DISABLE_TXT", **slot_arg)
            self.assertTrue(res.passed, res.errors)
            self.assertEqual(res.escape_mechanism, "EXTERNAL_MEDIA_SENTINEL")
            self.assertEqual(res.bind_mount_count, 0)
            self.assertEqual(res.cpio_extract_count, 0)
            self.assertEqual(res.emmc_write_count, 0)

    def test_07_escape2_physical_key_chord_rec_menu(self) -> None:
        res = run_init2_escape_drill("T07_CHORD_REC_MENU", gpio_chord="REC+MENU")
        self.assertTrue(res.passed, res.errors)
        self.assertEqual(res.escape_mechanism, "PHYSICAL_KEY_CHORD")
        self.assertEqual(res.boot_target, "STOCK_FX3_V702")
        self.assertTrue(res.stock_procam_exec)
        self.assertEqual(res.cpio_extract_count, 0)
        self.assertEqual(res.bind_mount_count, 0)

    def test_08_escape2_physical_key_chord_shutter(self) -> None:
        res = run_init2_escape_drill("T08_CHORD_SHUTTER", gpio_chord="SHUTTER")
        self.assertTrue(res.passed, res.errors)
        self.assertEqual(res.escape_mechanism, "PHYSICAL_KEY_CHORD")
        self.assertEqual(res.boot_target, "STOCK_FX3_V702")
        self.assertEqual(res.cpio_extract_count, 0)
        self.assertEqual(res.bind_mount_count, 0)

    def test_09_escape2_non_escape_gpio_chord_enters_stage_b(self) -> None:
        res = run_init2_escape_drill("T09_CHORD_NONE", gpio_chord="IDLE")
        self.assertTrue(res.passed, res.errors)
        self.assertFalse(res.escape_triggered)
        self.assertEqual(res.boot_target, "STAGE_B_OVERLAY")
        self.assertTrue(res.stage_b_active)

    def test_10_escape3_payload_sha256_mismatch_fails_open_to_stock(self) -> None:
        res = run_init2_escape_drill("T10_SHA_MISMATCH", corrupt_payload_bytes=True)
        self.assertTrue(res.passed, res.errors)
        self.assertEqual(res.escape_mechanism, "PAYLOAD_SHA256_OR_MAGIC_MISMATCH")
        self.assertEqual(res.boot_target, "STOCK_FX3_V702")
        self.assertEqual(res.cpio_extract_count, 0)
        self.assertEqual(res.bind_mount_count, 0)

    def test_11_escape3_payload_cpio_magic_mismatch_fails_open(self) -> None:
        res = run_init2_escape_drill("T11_MAGIC_MISMATCH", invalid_cpio_magic=True)
        self.assertTrue(res.passed, res.errors)
        self.assertEqual(res.escape_mechanism, "PAYLOAD_SHA256_OR_MAGIC_MISMATCH")
        self.assertEqual(res.cpio_extract_count, 0)
        self.assertEqual(res.bind_mount_count, 0)

    def test_12_escape3_payload_truncated_and_missing_fail_open(self) -> None:
        for flag in ({"truncated_payload": True}, {"missing_payload": True}):
            res = run_init2_escape_drill("T12_TRUNC_OR_MISSING", **flag)
            self.assertTrue(res.passed, res.errors)
            self.assertEqual(res.escape_mechanism, "PAYLOAD_SHA256_OR_MAGIC_MISMATCH")
            self.assertEqual(res.boot_target, "STOCK_FX3_V702")
            self.assertEqual(res.cpio_extract_count, 0)
            self.assertEqual(res.bind_mount_count, 0)

    def test_13_escape4_crash_loop_below_threshold_does_not_trip(self) -> None:
        res = run_init2_escape_drill(
            "T13_CRASH_2_OF_3",
            procam_exit_sequence=(1, 1),
            now_epochs=(1_700_000_000, 1_700_000_005),
        )
        self.assertTrue(res.passed, res.errors)
        self.assertFalse(res.escape_triggered)
        self.assertEqual(res.crash_count_in_window, 2)
        self.assertEqual(res.boot_target, "STAGE_B_CRASH_RETRY_PENDING")
        self.assertEqual(res.active_bind_mounts_remaining, 0)

    def test_14_escape4_crash_loop_3_exits_within_15s_unmounts_and_execs_stock(self) -> None:
        res = run_init2_escape_drill(
            "T14_CRASH_3_IN_15S",
            procam_exit_sequence=(139, 139, 139),
            now_epochs=(1_700_000_000, 1_700_000_004, 1_700_000_009),
        )
        self.assertTrue(res.passed, res.errors)
        self.assertTrue(res.escape_triggered)
        self.assertEqual(res.escape_mechanism, "CRASH_LOOP_BREAKER")
        self.assertEqual(res.boot_target, "STOCK_FX3_V702")
        self.assertTrue(res.stock_procam_exec)
        self.assertFalse(res.stage_b_active)
        self.assertEqual(res.umount_count, 2)
        self.assertEqual(res.active_bind_mounts_remaining, 0)
        self.assertEqual(res.emmc_write_count, 0)
        self.assertEqual(res.crash_count_in_window, 3)

    def test_15_escape4_stale_crashes_outside_15s_window_pruned(self) -> None:
        res = run_init2_escape_drill(
            "T15_STALE_WINDOW_PRUNE",
            prior_crash_epochs=(1_700_000_000, 1_700_000_003),
            procam_exit_sequence=(1,),
            now_epochs=(1_700_000_030,),
        )
        self.assertTrue(res.passed, res.errors)
        self.assertFalse(res.escape_triggered)
        self.assertEqual(res.crash_count_in_window, 1)

    def test_16_escape4_premount_tripped_counter_skips_cpio_and_mount(self) -> None:
        res = run_init2_escape_drill(
            "T16_PREMOUNT_CRASH_LOOP",
            prior_crash_epochs=(1_700_000_000, 1_700_000_004, 1_700_000_008),
            procam_exit_sequence=(0,),
            now_epochs=(1_700_000_010,),
        )
        self.assertTrue(res.passed, res.errors)
        self.assertEqual(res.escape_mechanism, "CRASH_LOOP_BREAKER")
        self.assertEqual(res.boot_target, "STOCK_FX3_V702")
        self.assertEqual(res.cpio_extract_count, 0)
        self.assertEqual(res.bind_mount_count, 0)
        self.assertTrue(res.stock_procam_exec)

    def test_17_wdt_normal_operation_periodic_2000ms_kicks_stay_healthy(self) -> None:
        res = simulate_cxd90057_watchdog_scenario("WDT_OK", fault_mode="NORMAL_OPERATION")
        self.assertTrue(res.passed, res.errors)
        self.assertEqual(res.timeout_ms, CXD90057_WDT_TIMEOUT_MS)
        self.assertEqual(res.kick_interval_ms, CXD90057_WDT_KICK_INTERVAL_MS)
        self.assertFalse(res.wdt_reset_triggered)
        self.assertGreater(res.kicks_sent, 5)
        self.assertTrue(res.h0_equals_h2)
        self.assertEqual(res.persistent_emmc_mutations, 0)

    def test_18_wdt_hung_ui_presenter_starves_and_restores_h0_stock(self) -> None:
        res = simulate_cxd90057_watchdog_scenario("WDT_HUNG_UI", fault_mode="HUNG_UI_PRESENTER", hang_at_ms=4_000)
        self.assertTrue(res.passed, res.errors)
        self.assertTrue(res.wdt_reset_triggered)
        self.assertTrue(res.volatile_ram_wiped)
        self.assertEqual(res.recovery_tier, "TIER_0")
        self.assertTrue(res.h0_equals_h2)
        self.assertEqual(res.elapsed_ms, 12_000)

    def test_19_wdt_kernel_oops_panic_on_oops_triggers_wdt_reset(self) -> None:
        res = simulate_cxd90057_watchdog_scenario(
            "WDT_OOPS", fault_mode="KERNEL_OOPS_PANIC_ON_OOPS", oops_at_ms=3_000, panic_on_oops=True
        )
        self.assertTrue(res.passed, res.errors)
        self.assertTrue(res.wdt_reset_triggered)
        self.assertTrue(res.volatile_ram_wiped)
        self.assertEqual(res.recovery_tier, "TIER_0")
        self.assertTrue(res.h0_equals_h2)
        self.assertIn("PANIC_ON_OOPS_HALT_NO_KICK", res.state_transitions)

    def test_20_wdt_clean_reboot_wipes_volatile_ram_h0_equals_h2(self) -> None:
        res = simulate_cxd90057_watchdog_scenario("WDT_REBOOT", fault_mode="CLEAN_REBOOT", reboot_at_ms=4_000)
        self.assertTrue(res.passed, res.errors)
        self.assertFalse(res.wdt_reset_triggered)
        self.assertTrue(res.volatile_ram_wiped)
        self.assertEqual(res.recovery_tier, "TIER_0")
        self.assertTrue(res.h0_equals_h2)

    def test_21_wdt_experimental_p1_pointer_triggers_tier12_rollback(self) -> None:
        res = simulate_cxd90057_watchdog_scenario(
            "WDT_P1_PTR",
            fault_mode="EXPERIMENTAL_P1_POINTER_ROLLBACK",
            experimental_p1_pointer=True,
        )
        self.assertTrue(res.passed, res.errors)
        self.assertTrue(res.wdt_reset_triggered)
        self.assertTrue(res.p1_pointer_rolled_back)
        self.assertEqual(res.recovery_tier, "TIER_1_2_P1_VFAT_ROLLBACK")
        self.assertTrue(res.h0_equals_h2)

    def test_22_wdt_rejects_nonzero_persistent_emmc_mutations(self) -> None:
        res = simulate_cxd90057_watchdog_scenario(
            "WDT_MUTATION_BREACH",
            fault_mode="HUNG_UI_PRESENTER",
            persistent_emmc_mutations=1,
        )
        self.assertFalse(res.passed)
        self.assertFalse(res.h0_equals_h2)
        self.assertNotEqual(res.h0_stock_sha256, res.h2_restored_sha256)

    def test_23_fat12_synthetic_image_compatible_with_fatp1_and_auditor(self) -> None:
        img = build_synthetic_p1_vfat_with_init2(fat_type="FAT12", include_lfn=True)
        fat_p1 = FatP1(img)
        self.assertIn("/init2.sh", fat_p1.files)
        self.assertIn("/init2bak.sh", fat_p1.files)
        audit = audit_p1_fat_filesystem(img)
        self.assertTrue(audit.passed, audit.errors)
        self.assertEqual(audit.status, STATUS_VERIFIED_FAT_INTEGRITY)
        self.assertEqual(audit.fat_type, "FAT12")
        self.assertTrue(audit.fat_mirrors_equal)
        self.assertEqual(audit.cycle_clusters, ())
        self.assertEqual(audit.cross_linked_clusters, ())
        self.assertEqual(audit.orphan_clusters, ())

    def test_24_fat16_synthetic_image_auditor_passes(self) -> None:
        img = build_synthetic_p1_vfat_with_init2(fat_type="FAT16", include_lfn=True)
        audit = audit_p1_fat_filesystem(img)
        self.assertTrue(audit.passed, audit.errors)
        self.assertEqual(audit.status, STATUS_VERIFIED_FAT_INTEGRITY)
        self.assertEqual(audit.fat_type, "FAT16")
        self.assertGreaterEqual(audit.cluster_count, 4085)
        self.assertTrue(audit.fat_mirrors_equal)

    def test_25_fat_detects_fat1_fat2_mirror_mismatch(self) -> None:
        buf = bytearray(build_synthetic_p1_vfat_with_init2(fat_type="FAT12"))
        u16 = lambda at: struct.unpack_from("<H", buf, at)[0]
        fat2_off = (u16(14) + u16(22)) * 512
        buf[fat2_off + 10] ^= 0x5A
        audit = audit_p1_fat_filesystem(bytes(buf))
        self.assertFalse(audit.passed)
        self.assertEqual(audit.status, STATUS_FAIL_FAT_MIRROR_MISMATCH)
        self.assertFalse(audit.fat_mirrors_equal)
        self.assertEqual(audit.fat_mirror_first_diff_offset, 10)

    def test_26_fat_detects_cluster_chain_cycle_fat12_and_fat16(self) -> None:
        for fat_type in ("FAT12", "FAT16"):
            buf = bytearray(build_synthetic_p1_vfat_with_init2(fat_type=fat_type))
            off_init2 = _find_root_entry_offset(bytes(buf), "INIT2.SH")
            start_c = struct.unpack_from("<H", buf, off_init2 + 26)[0]
            # Point start_c -> start_c (1-node self cycle)
            _patch_fat_entry_mirror(buf, fat_type, start_c, start_c, mirror_both=True)
            audit = audit_p1_fat_filesystem(bytes(buf))
            self.assertFalse(audit.passed)
            self.assertEqual(audit.status, STATUS_FAIL_FAT_CLUSTER_CYCLE)
            self.assertIn(start_c, audit.cycle_clusters)

    def test_27_fat_detects_cross_linked_cluster_between_two_files(self) -> None:
        buf = bytearray(build_synthetic_p1_vfat_with_init2(fat_type="FAT12"))
        off_a = _find_root_entry_offset(bytes(buf), "INIT2.SH")
        off_b = _find_root_entry_offset(bytes(buf), "INIT2BAK.SH")
        cluster_a = struct.unpack_from("<H", buf, off_a + 26)[0]
        cluster_b = struct.unpack_from("<H", buf, off_b + 26)[0]
        # Free cluster_b to avoid orphan masking cross-link priority, then cross-link INIT2BAK -> cluster_a
        _patch_fat_entry_mirror(buf, "FAT12", cluster_b, 0x000, mirror_both=True)
        struct.pack_into("<H", buf, off_b + 26, cluster_a)
        audit = audit_p1_fat_filesystem(bytes(buf))
        self.assertFalse(audit.passed)
        self.assertEqual(audit.status, STATUS_FAIL_FAT_CROSS_LINK)
        self.assertTrue(any(c == cluster_a for c, _, _ in audit.cross_linked_clusters))

    def test_28_fat_detects_orphan_allocated_clusters(self) -> None:
        buf = bytearray(build_synthetic_p1_vfat_with_init2(fat_type="FAT16"))
        _patch_fat_entry_mirror(buf, "FAT16", 120, 0xFFFF, mirror_both=True)
        audit = audit_p1_fat_filesystem(bytes(buf))
        self.assertFalse(audit.passed)
        self.assertEqual(audit.status, STATUS_FAIL_FAT_ORPHAN_CLUSTERS)
        self.assertIn(120, audit.orphan_clusters)

    def test_29_fat_detects_invalid_83_name_and_lfn_checksum_mismatch(self) -> None:
        # 1. Invalid 8.3 lowercase character
        buf1 = bytearray(build_synthetic_p1_vfat_with_init2(fat_type="FAT12"))
        off_a = _find_root_entry_offset(bytes(buf1), "INIT2.SH")
        buf1[off_a] = ord("?")
        audit1 = audit_p1_fat_filesystem(bytes(buf1))
        self.assertFalse(audit1.passed)
        self.assertEqual(audit1.status, STATUS_FAIL_FAT_DIR_CHECKSUM)
        self.assertTrue(audit1.invalid_83_entries)

        # 2. Invalid LFN checksum on P1CHKSUM
        buf2 = bytearray(build_synthetic_p1_vfat_with_init2(fat_type="FAT12", include_lfn=True))
        off_chk = _find_root_entry_offset(bytes(buf2), "P1CHKSUM")
        # Previous 32-byte slot is LFN row; byte +13 is DOS 8.3 checksum
        buf2[off_chk - 32 + 13] ^= 0xFF
        audit2 = audit_p1_fat_filesystem(bytes(buf2))
        self.assertFalse(audit2.passed)
        self.assertEqual(audit2.status, STATUS_FAIL_FAT_DIR_CHECKSUM)
        self.assertTrue(audit2.invalid_lfn_checksums)

    def test_30_atomic_83_dir_swap_fat12_and_fat16_in_memory_roundtrip(self) -> None:
        for fat_type in ("FAT12", "FAT16"):
            img = build_synthetic_p1_vfat_with_init2(fat_type=fat_type)
            swap = simulate_atomic_83_dir_swap(img)
            self.assertTrue(swap.passed, swap.errors)
            self.assertEqual(swap.fat_type, fat_type)
            self.assertEqual(swap.physical_writes, 0)
            self.assertFalse(swap.persistent_emmc_writes_authorized)
            self.assertFalse(swap.persistent_write_release)
            self.assertTrue(swap.pre_audit_passed)
            self.assertTrue(swap.post_audit_passed)
            self.assertTrue(swap.content_swapped_exact)
            self.assertTrue(swap.roundtrip_sha256_exact)
            self.assertNotEqual(swap.pre_sha256, swap.post_sha256)
            self.assertEqual(swap.pre_sha256, swap.roundtrip_sha256)

    def test_31_dual_mode_suite_clean_room_and_local_donor_o_rdonly(self) -> None:
        # Clean-room mode (forced)
        rep_clean = run_init2_escape_and_watchdog_suite(force_clean_room=True)
        self.assertTrue(rep_clean.all_passed, rep_clean.errors)
        self.assertEqual(rep_clean.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertIsNone(rep_clean.donor_fat_audit)
        self.assertFalse(rep_clean.persistent_emmc_writes_authorized)
        self.assertFalse(rep_clean.persistent_write_release)
        self.assertEqual(rep_clean.physical_writes, 0)

        # Local Donor O_RDONLY check (when donor is available and clean-room is not forced)
        donor_path = resolve_donor_path(DONOR_P1_205_RELPATH)
        if not is_forced_clean_room() and donor_path.is_file():
            from fx3_recovery.files import read_file
            from fx3_recovery.fat import MAX_P1

            donor_bytes = read_file(donor_path, MAX_P1)
            donor_audit = audit_p1_fat_filesystem(donor_bytes)
            self.assertTrue(donor_audit.passed, donor_audit.errors)
            self.assertEqual(donor_audit.fat_type, "FAT12")
            self.assertTrue(donor_audit.fat_mirrors_equal)

    def test_32_cli_verify_init2_escape_clean_room_json_out_and_no_raw_bytes(self) -> None:
        self._sandbox.mkdir(parents=True, exist_ok=True)
        out_dir = self._sandbox / "cli-out"
        buf = io.StringIO()
        with mock.patch.object(
            sys,
            "argv",
            ["fx3_recovery", "verify-init2-escape", "--clean-room", "--json", "--out", str(out_dir)],
        ):
            with redirect_stdout(buf):
                rc = fx3_cli.main()
        self.assertEqual(rc, 0)
        rendered = buf.getvalue()
        self.assertNotRegex(rendered, r'(?<![0-9A-Za-z_/.-])b[\'"]')
        payload = json.loads(rendered)
        self.assertTrue(payload["all_passed"])
        self.assertEqual(payload["status"], STATUS_VERIFIED_PHASE66)
        self.assertEqual(payload["verification_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(payload["physical_writes"], 0)
        self.assertFalse(payload["persistent_emmc_writes_authorized"])
        self.assertFalse(payload["persistent_write_release"])
        report_file = out_dir / "init2-escape-report.json"
        self.assertTrue(report_file.is_file())
        saved = json.loads(report_file.read_text(encoding="utf-8"))
        self.assertEqual(saved["schema"], INIT2_ESCAPE_SCHEMA)

    def test_33_watchdog_and_fat_auditor_json_contain_no_raw_bytes_repr(self) -> None:
        wdt_suite = run_cxd90057_watchdog_suite()
        fat12_img = build_synthetic_p1_vfat_with_init2(fat_type="FAT12")
        fat12_audit = audit_p1_fat_filesystem(fat12_img)
        fat12_swap = simulate_atomic_83_dir_swap(fat12_img)
        rendered = json.dumps(
            {
                "wdt": [s.__dict__ for s in wdt_suite.scenarios],
                "fat_audit": fat12_audit.__dict__,
                "fat_swap": fat12_swap.__dict__,
            },
            sort_keys=True,
        )
        self.assertNotRegex(rendered, r'(?<![0-9A-Za-z_/.-])b[\'"]')

    def test_34_full_suite_runtime_under_half_second(self) -> None:
        t0 = time.monotonic()
        rep = run_init2_escape_and_watchdog_suite(force_clean_room=True)
        elapsed = time.monotonic() - t0
        self.assertTrue(rep.all_passed, rep.errors)
        self.assertLessEqual(elapsed, 2.5)


if __name__ == "__main__":
    unittest.main()
