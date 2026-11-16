"""Phase 119 Dual-Mode Fast Unit Tests (>=36 tests, <0.5s clean-room):

- Pillar 0: Hard-locked safety redlines, package exports, O_RDONLY donor inspection & clean-room fallback
- Pillar A: SquashFS 4.0 (`hsqs` 0x73717368) 96B superblock, compression IDs {1..6}, block_size/block_log & monotonic table-bounds verifier
- Pillar B: Sony Warp-Boot `hibdrv` (`WBI2`) stale-resume poisoning triage, ephemeral `noresume`/`hibdrv.resume=0` RAM-boot bypass & WBI write firewall
- Pillar C: CLI `verify-squashfs-wbi-triage` & `verify-all-recovery --with-phase94 --with-phase101 --with-phase106 --with-phase113 --with-phase119` (>=12 pillars)
"""

from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import shutil
import sys
import time
import unittest
from unittest import mock
import zlib

import fx3_recovery
from fx3_recovery import __main__ as fx3_cli
from fx3_recovery.files import is_forced_clean_room, resolve_donor_path
from fx3_recovery.squashfs_and_hibdrv_wbi_verifier import (
    ALLOWED_NORESUME_INIT_PATHS,
    ALLOW_BOOT_PARTITION_TARGETING,
    ALLOW_DESTRUCTIVE_FASTBOOT,
    DEFAULT_SAFE_STAGE_B_NORESUME_BOOTARGS,
    DONOR_FX3_NFLASH5_WBI2_RELPATH,
    DONOR_FX3_P1_205_SQUASHFS_HOST_RELPATH,
    DONOR_FX3_UDTRBODY_SQUASHFS_RELPATH,
    DONOR_FX3_VMLINUX_KERNEL_RELPATH,
    DONOR_FX6_NFLASH5_WBI2_RELPATH,
    DONOR_FX6_UPDATER_SQUASHFS_RELPATH,
    DONOR_FX6_VMLINUX_KERNEL_RELPATH,
    ERR_NORESUME_MISSING_BYPASS_TOKEN,
    ERR_NORESUME_RW_EMMC_OR_REPARTITION_FORBIDDEN,
    ERR_NORESUME_UNVERIFIED_INIT,
    ERR_NORESUME_WDT_DISABLED,
    ERR_SQUASHFS_BAD_MAGIC,
    ERR_SQUASHFS_BLANK_OR_ERASED_FLASH,
    ERR_SQUASHFS_BYTES_USED_EXCEEDS_PARTITION,
    ERR_SQUASHFS_EMPTY_OR_TRUNCATED_HEADER,
    ERR_SQUASHFS_INVALID_BLOCK_SIZE_OR_LOG,
    ERR_SQUASHFS_INVALID_BYTES_USED,
    ERR_SQUASHFS_INVALID_ID_COUNT,
    ERR_SQUASHFS_INVALID_INODE_COUNT,
    ERR_SQUASHFS_NON_MONOTONIC_TABLE_BOUNDS,
    ERR_SQUASHFS_ROOT_INODE_OUT_OF_BOUNDS,
    ERR_SQUASHFS_TABLE_OUT_OF_BOUNDS,
    ERR_SQUASHFS_TRUNCATED_IMAGE_PAYLOAD,
    ERR_SQUASHFS_UNSUPPORTED_COMPRESSION_ID,
    ERR_SQUASHFS_UNSUPPORTED_VERSION,
    ERR_SQUASHFS_WRONG_ENDIAN_BIG_SQSH,
    ERR_WBI_BAD_MAGIC,
    ERR_WBI_HEADER_OR_TABLE_INVALID,
    ERR_WBI_PAGE_TABLE_RESTORE_PANIC_RISK,
    ERR_WBI_PERSISTENT_PARTITION_WRITE_FORBIDDEN,
    FX3_EXPECTED_KERNEL_UTS,
    FX3_SKU_NAME,
    FX6_EXPECTED_KERNEL_UTS,
    FX6_SKU_NAME,
    OTP_FUSE_TOUCHES,
    PASSIVE_TX_BYTES_EMITTED,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHYSICAL_DEVICE_WRITES,
    PINNED_FX3_NFLASH5_WBI2_HDR_SHA256,
    PINNED_FX3_NFLASH5_WBI2_SECTIONS,
    PINNED_FX3_NFLASH5_WBI2_TABLE_SHA256,
    PINNED_FX3_P1_INITRD_SQUASHFS_SHA256,
    PINNED_FX3_UDTRBODY_SQUASHFS_SHA256,
    PINNED_FX3_VMLINUX_KERNEL_SHA256,
    PINNED_FX6_NFLASH5_WBI2_HDR_SHA256,
    PINNED_FX6_NFLASH5_WBI2_SECTIONS,
    PINNED_FX6_UPDATER_SQUASHFS_SHA256,
    PINNED_FX6_VMLINUX_KERNEL_SHA256,
    READ_ONLY_DONOR_ACCESS,
    SQUASHFS_COMPRESSION_NAMES,
    SQUASHFS_INVALID_BLK,
    SQUASHFS_MAGIC,
    SQUASHFS_MAGIC_BE,
    SQUASHFS_WBI_HIBDRV_SCHEMA,
    SQUASHFS_WBI_HIBDRV_VERSION,
    STATUS_FAIL_SQUASHFS_WBI_GATE,
    STATUS_REJECTED_SQUASHFS_SUPERBLOCK,
    STATUS_VERIFIED_SQUASHFS_SUPERBLOCK,
    STATUS_VERIFIED_SQUASHFS_WBI_GATE,
    STATUS_WBI_COLD_BOOT_INVALIDATED,
    STATUS_WBI_HEALTHY_RESUME_MATCH,
    STATUS_WBI_PERSISTENT_WRITE_BLOCKED,
    STATUS_WBI_POISONING_NORESUME_BYPASS,
    WBI_EPHEMERAL_NORESUME_REQUIRED,
    WBI_KERNEL_ABI_FINGERPRINT_MISMATCH,
    WBI_PARTITION_WRITES,
    WBI_SCENARIO_IDS,
    WBI_SECTOR_SIZE,
    WBI_SNAPSHOT_TRUNCATED_OR_CRC_MISMATCH,
    SquashfsAndHibdrvWbiSuiteReport,
    WbiActiveBootContext,
    WbiSnapshotEnvelope,
    audit_wbi_partition_write_attempt,
    build_synthetic_squashfs_superblock,
    build_synthetic_wbi2_snapshot_bytes,
    inspect_squashfs_and_wbi_donors_readonly,
    parse_wbi2_header_and_table,
    run_squashfs_and_hibdrv_wbi_suite,
    run_wbi_hibdrv_6_scenario_triage,
    triage_wbi_hibdrv_snapshot,
    verify_ephemeral_noresume_bootargs_bypass,
    verify_squashfs_partition_bytes,
)

ROOT = Path(__file__).resolve().parents[3]
RAW_BYTES_RE = r'(?<![0-9A-Za-z_/.-])b[\'"]'


class TestSquashfsAndHibdrvWbiVerifier(unittest.TestCase):
    """40 dual-mode tests covering Phase 119 SquashFS 4.0, Sony hibdrv WBI2, & 12-pillar master suite."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.suite_report = run_squashfs_and_hibdrv_wbi_suite()
        cls.clean_report = run_squashfs_and_hibdrv_wbi_suite(force_clean_room=True)

    # ------------------------------------------------------------------
    # Pillar 0 — Safety Redlines, Exports & Dual-Mode Donor Inspection
    # ------------------------------------------------------------------

    def test_01_safety_redlines_hard_locked_and_exported(self) -> None:
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(PERSISTENT_WRITE_RELEASE)
        self.assertFalse(ALLOW_BOOT_PARTITION_TARGETING)
        self.assertFalse(ALLOW_DESTRUCTIVE_FASTBOOT)
        self.assertTrue(READ_ONLY_DONOR_ACCESS)
        self.assertEqual(OTP_FUSE_TOUCHES, 0)
        self.assertEqual(PASSIVE_TX_BYTES_EMITTED, 0)
        self.assertEqual(PHYSICAL_DEVICE_WRITES, 0)
        self.assertEqual(WBI_PARTITION_WRITES, 0)
        self.assertEqual(SQUASHFS_WBI_HIBDRV_SCHEMA, "fx3-squashfs-and-hibdrv-wbi-verifier-v1")
        self.assertEqual(SQUASHFS_WBI_HIBDRV_VERSION, "1.0.0")

    def test_02_package_exports_preserve_prior_symbols_and_expose_phase119(self) -> None:
        expected_symbols = (
            "run_squashfs_and_hibdrv_wbi_suite",
            "verify_squashfs_partition_bytes",
            "build_synthetic_squashfs_superblock",
            "build_synthetic_wbi2_snapshot_bytes",
            "parse_wbi2_header_and_table",
            "triage_wbi_hibdrv_snapshot",
            "run_wbi_hibdrv_6_scenario_triage",
            "verify_ephemeral_noresume_bootargs_bypass",
            "audit_wbi_partition_write_attempt",
            "inspect_squashfs_and_wbi_donors_readonly",
            "WBI_SNAPSHOT_TRUNCATED_OR_CRC_MISMATCH",
            "WBI_KERNEL_ABI_FINGERPRINT_MISMATCH",
            "WBI_EPHEMERAL_NORESUME_REQUIRED",
            "DonorArtifactDigest",
            "AbBankDonorArtifactDigest",
            "SquashfsWbiDonorArtifactDigest",
            "run_recovery_master_suite",
        )
        for sym in expected_symbols:
            self.assertIn(sym, fx3_recovery.__all__)
            self.assertTrue(hasattr(fx3_recovery, sym), f"Missing export: {sym}")

    def test_03_clean_room_donor_snapshot_uses_pinned_anchors(self) -> None:
        snap = inspect_squashfs_and_wbi_donors_readonly(force_clean_room=True)
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(snap.read_only_access)
        self.assertEqual(snap.fx3_p1_initrd_squashfs_sha256, PINNED_FX3_P1_INITRD_SQUASHFS_SHA256)
        self.assertEqual(snap.fx3_udtrbody_squashfs_sha256, PINNED_FX3_UDTRBODY_SQUASHFS_SHA256)
        self.assertEqual(snap.fx6_updater_squashfs_sha256, PINNED_FX6_UPDATER_SQUASHFS_SHA256)
        self.assertEqual(snap.fx3_wbi2_hdr_sha256, PINNED_FX3_NFLASH5_WBI2_HDR_SHA256)
        self.assertEqual(snap.fx3_wbi2_table_sha256, PINNED_FX3_NFLASH5_WBI2_TABLE_SHA256)
        self.assertEqual(snap.fx3_wbi2_sections, PINNED_FX3_NFLASH5_WBI2_SECTIONS)
        self.assertEqual(snap.fx6_wbi2_hdr_sha256, PINNED_FX6_NFLASH5_WBI2_HDR_SHA256)
        self.assertEqual(snap.fx6_wbi2_sections, PINNED_FX6_NFLASH5_WBI2_SECTIONS)
        self.assertEqual(snap.fx3_vmlinux_sha256, PINNED_FX3_VMLINUX_KERNEL_SHA256)
        self.assertEqual(snap.fx6_vmlinux_sha256, PINNED_FX6_VMLINUX_KERNEL_SHA256)
        self.assertEqual(len(snap.artifacts), 7)

    def test_04_active_donor_mode_o_rdonly_matches_pinned_or_falls_back(self) -> None:
        donor_paths = [
            resolve_donor_path(rel, require_file=True)
            for rel in (
                DONOR_FX3_P1_205_SQUASHFS_HOST_RELPATH,
                DONOR_FX3_UDTRBODY_SQUASHFS_RELPATH,
                DONOR_FX6_UPDATER_SQUASHFS_RELPATH,
                DONOR_FX3_NFLASH5_WBI2_RELPATH,
                DONOR_FX6_NFLASH5_WBI2_RELPATH,
                DONOR_FX3_VMLINUX_KERNEL_RELPATH,
                DONOR_FX6_VMLINUX_KERNEL_RELPATH,
            )
        ]
        if (not is_forced_clean_room()) and all(p.is_file() for p in donor_paths):
            self.assertEqual(self.suite_report.verification_mode, "LOCAL_DONOR_O_RDONLY")
            self.assertEqual(
                self.suite_report.donor_snapshot.fx3_p1_initrd_squashfs_sha256,
                self.clean_report.donor_snapshot.fx3_p1_initrd_squashfs_sha256,
            )
            self.assertEqual(
                self.suite_report.donor_snapshot.fx3_wbi2_table_sha256,
                self.clean_report.donor_snapshot.fx3_wbi2_table_sha256,
            )
        else:
            self.assertEqual(self.suite_report.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(self.suite_report.all_passed)
        self.assertTrue(self.clean_report.all_passed)

    def test_05_clean_room_suite_completes_under_half_second(self) -> None:
        t0 = time.monotonic()
        rep = run_squashfs_and_hibdrv_wbi_suite(force_clean_room=True)
        elapsed = time.monotonic() - t0
        self.assertTrue(rep.all_passed)
        self.assertLess(elapsed, 0.5)

    def test_06_wbi2_donor_open_strictly_o_rdonly_and_bounded(self) -> None:
        with mock.patch("fx3_recovery.squashfs_and_hibdrv_wbi_verifier.os.open") as m_open:
            m_open.side_effect = OSError("sentinel stop")
            snap = inspect_squashfs_and_wbi_donors_readonly(force_clean_room=True)
            self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            m_open.assert_not_called()

    # ------------------------------------------------------------------
    # Pillar A — SquashFS 4.0 Superblock, Compression & Table-Bounds
    # ------------------------------------------------------------------

    def test_07_squashfs_validates_all_6_supported_compression_ids(self) -> None:
        self.assertEqual(len(SQUASHFS_COMPRESSION_NAMES), 6)
        self.assertEqual(len(self.clean_report.squashfs_compression_reports), 6)
        for cid, cname in SQUASHFS_COMPRESSION_NAMES.items():
            buf = build_synthetic_squashfs_superblock(compression_id=cid, block_size=131072, block_log=17)
            rep = verify_squashfs_partition_bytes(buf, partition_size=4096, label=f"test_{cname}")
            self.assertTrue(rep.passed, f"{cname} failed: {rep.errors}")
            self.assertEqual(rep.status, STATUS_VERIFIED_SQUASHFS_SUPERBLOCK)
            self.assertIsNotNone(rep.superblock)
            assert rep.superblock is not None
            self.assertEqual(rep.superblock.s_magic, SQUASHFS_MAGIC)
            self.assertEqual(rep.superblock.s_magic_ascii, "hsqs")
            self.assertEqual(rep.superblock.compression_id, cid)
            self.assertEqual(rep.superblock.compression_name, cname)
            self.assertEqual(rep.physical_device_writes, 0)

    def test_08_squashfs_validates_power_of_two_block_sizes_4kib_to_1mib(self) -> None:
        for log in range(12, 21):
            bsize = 1 << log
            buf = build_synthetic_squashfs_superblock(block_size=bsize, block_log=log)
            rep = verify_squashfs_partition_bytes(buf, partition_size=4096, label=f"bsize_{bsize}")
            self.assertTrue(rep.passed, f"block_size={bsize} log={log} failed: {rep.errors}")

    def test_09_squashfs_rejects_out_of_range_or_non_pow2_block_size(self) -> None:
        for bsize, blog in ((2048, 11), (2097152, 21), (100000, 17), (131072, 16)):
            buf = build_synthetic_squashfs_superblock(block_size=bsize, block_log=blog)
            rep = verify_squashfs_partition_bytes(buf, partition_size=4096)
            self.assertFalse(rep.passed)
            self.assertIn(ERR_SQUASHFS_INVALID_BLOCK_SIZE_OR_LOG, rep.error_codes)

    def test_10_squashfs_rejects_big_endian_sqsh_magic(self) -> None:
        buf = build_synthetic_squashfs_superblock(s_magic=SQUASHFS_MAGIC_BE)
        rep = verify_squashfs_partition_bytes(buf, partition_size=4096)
        self.assertFalse(rep.passed)
        self.assertEqual(rep.status, STATUS_REJECTED_SQUASHFS_SUPERBLOCK)
        self.assertIn(ERR_SQUASHFS_WRONG_ENDIAN_BIG_SQSH, rep.error_codes)
        self.assertTrue(rep.sigbus_or_vfs_mount_loop_risk)

    def test_11_squashfs_rejects_bad_magic_and_empty_or_short_buffer(self) -> None:
        rep_empty = verify_squashfs_partition_bytes(b"")
        self.assertFalse(rep_empty.passed)
        self.assertIn(ERR_SQUASHFS_EMPTY_OR_TRUNCATED_HEADER, rep_empty.error_codes)

        rep_short = verify_squashfs_partition_bytes(b"hsqs" + bytes(40))
        self.assertFalse(rep_short.passed)
        self.assertIn(ERR_SQUASHFS_EMPTY_OR_TRUNCATED_HEADER, rep_short.error_codes)

        rep_bad = verify_squashfs_partition_bytes(build_synthetic_squashfs_superblock(s_magic=0xDEADBEEF))
        self.assertFalse(rep_bad.passed)
        self.assertIn(ERR_SQUASHFS_BAD_MAGIC, rep_bad.error_codes)

    def test_12_squashfs_rejects_all_zero_and_all_ff_erased_flash(self) -> None:
        for fill in (0x00, 0xFF):
            rep = verify_squashfs_partition_bytes(bytes([fill]) * 4096)
            self.assertFalse(rep.passed)
            self.assertIn(ERR_SQUASHFS_BLANK_OR_ERASED_FLASH, rep.error_codes)
            self.assertTrue(rep.truncated_flash_detected)

    def test_13_squashfs_rejects_unsupported_version_and_compression_id(self) -> None:
        rep_ver = verify_squashfs_partition_bytes(build_synthetic_squashfs_superblock(s_major=3, s_minor=1))
        self.assertFalse(rep_ver.passed)
        self.assertIn(ERR_SQUASHFS_UNSUPPORTED_VERSION, rep_ver.error_codes)

        rep_comp = verify_squashfs_partition_bytes(build_synthetic_squashfs_superblock(compression_id=7))
        self.assertFalse(rep_comp.passed)
        self.assertIn(ERR_SQUASHFS_UNSUPPORTED_COMPRESSION_ID, rep_comp.error_codes)

        # Kernel allow-list check (e.g., kernel without ZSTD support)
        rep_policy = verify_squashfs_partition_bytes(
            build_synthetic_squashfs_superblock(compression_id=6),
            allowed_compression_ids=(1, 4),
        )
        self.assertFalse(rep_policy.passed)
        self.assertIn(ERR_SQUASHFS_UNSUPPORTED_COMPRESSION_ID, rep_policy.error_codes)

    def test_14_squashfs_rejects_truncated_flash_and_partition_overrun(self) -> None:
        # Payload truncated compared to bytes_used -> causes SIGBUS / VFS panic
        trunc_buf = build_synthetic_squashfs_superblock(bytes_used=8192, payload_size=4096)
        rep_trunc = verify_squashfs_partition_bytes(trunc_buf, partition_size=8192, label="app_truncated")
        self.assertFalse(rep_trunc.passed)
        self.assertTrue(rep_trunc.truncated_flash_detected)
        self.assertTrue(rep_trunc.sigbus_or_vfs_mount_loop_risk)
        self.assertIn(ERR_SQUASHFS_TRUNCATED_IMAGE_PAYLOAD, rep_trunc.error_codes)

        # bytes_used larger than hardware GPT partition size
        over_buf = build_synthetic_squashfs_superblock(bytes_used=4096, payload_size=4096)
        rep_over = verify_squashfs_partition_bytes(over_buf, partition_size=2048, label="rootfs_overrun")
        self.assertFalse(rep_over.passed)
        self.assertTrue(rep_over.truncated_flash_detected)
        self.assertIn(ERR_SQUASHFS_BYTES_USED_EXCEEDS_PARTITION, rep_over.error_codes)

    def test_15_squashfs_rejects_non_monotonic_and_out_of_bounds_tables(self) -> None:
        # inode_table_start >= directory_table_start
        rep_nm1 = verify_squashfs_partition_bytes(
            build_synthetic_squashfs_superblock(inode_table_start=3800, directory_table_start=3500)
        )
        self.assertFalse(rep_nm1.passed)
        self.assertIn(ERR_SQUASHFS_NON_MONOTONIC_TABLE_BOUNDS, rep_nm1.error_codes)

        # fragment_table_start < directory_table_start
        rep_nm2 = verify_squashfs_partition_bytes(
            build_synthetic_squashfs_superblock(directory_table_start=3584, fragment_table_start=3400)
        )
        self.assertFalse(rep_nm2.passed)
        self.assertIn(ERR_SQUASHFS_NON_MONOTONIC_TABLE_BOUNDS, rep_nm2.error_codes)

        # id_table_start == SQUASHFS_INVALID_BLK
        rep_oob = verify_squashfs_partition_bytes(
            build_synthetic_squashfs_superblock(id_table_start=SQUASHFS_INVALID_BLK)
        )
        self.assertFalse(rep_oob.passed)
        self.assertIn(ERR_SQUASHFS_TABLE_OUT_OF_BOUNDS, rep_oob.error_codes)

    def test_16_squashfs_rejects_zero_inodes_zero_ids_bad_bytes_used_and_oob_root_inode(self) -> None:
        rep_inodes = verify_squashfs_partition_bytes(build_synthetic_squashfs_superblock(inodes=0))
        self.assertIn(ERR_SQUASHFS_INVALID_INODE_COUNT, rep_inodes.error_codes)

        rep_ids = verify_squashfs_partition_bytes(build_synthetic_squashfs_superblock(no_ids=0))
        self.assertIn(ERR_SQUASHFS_INVALID_ID_COUNT, rep_ids.error_codes)

        rep_bu = verify_squashfs_partition_bytes(build_synthetic_squashfs_superblock(bytes_used=64, payload_size=256))
        self.assertIn(ERR_SQUASHFS_INVALID_BYTES_USED, rep_bu.error_codes)

        rep_root = verify_squashfs_partition_bytes(
            build_synthetic_squashfs_superblock(
                inode_table_start=3072,
                directory_table_start=3200,
                root_inode=(1024 << 16),
            )
        )
        self.assertFalse(rep_root.passed)
        self.assertIn(ERR_SQUASHFS_ROOT_INODE_OUT_OF_BOUNDS, rep_root.error_codes)

    # ------------------------------------------------------------------
    # Pillar B — Sony Warp-Boot / hibdrv (WBI2) Stale-Resume & noresume
    # ------------------------------------------------------------------

    def test_17_wbi2_synthetic_header_and_section_table_parse_cleanly(self) -> None:
        full_bytes, tbl_bytes, full_crc = build_synthetic_wbi2_snapshot_bytes(sections=4)
        info, codes, errs = parse_wbi2_header_and_table(
            full_bytes[:WBI_SECTOR_SIZE],
            section_table_bytes=tbl_bytes,
            available_bytes=len(full_bytes),
        )
        self.assertEqual(codes, [])
        self.assertEqual(errs, [])
        self.assertIsNotNone(info)
        assert info is not None
        self.assertEqual(info.magic_ascii, "WBI2")
        self.assertEqual(info.sections, 4)
        self.assertEqual(info.r_data_size, 3 * 4096)
        self.assertEqual(info.o_data_size, 4 * 4096)
        self.assertGreater(full_crc, 0)

    def test_18_wbi2_detects_truncated_snapshot_and_crc_mismatch(self) -> None:
        full_bytes, tbl_bytes, valid_crc = build_synthetic_wbi2_snapshot_bytes(sections=4)
        trunc_bytes, _, _ = build_synthetic_wbi2_snapshot_bytes(sections=4, truncate_after_bytes=2048)
        env = WbiSnapshotEnvelope(
            header_bytes=trunc_bytes[:WBI_SECTOR_SIZE],
            section_table_bytes=tbl_bytes,
            available_bytes=len(trunc_bytes),
            expected_total_bytes=len(full_bytes),
            declared_crc32=valid_crc,
            computed_crc32=zlib.crc32(trunc_bytes) & 0xFFFFFFFF,
        )
        ctx = WbiActiveBootContext(stage_b_ram_boot=True, bootargs=DEFAULT_SAFE_STAGE_B_NORESUME_BOOTARGS)
        rep = triage_wbi_hibdrv_snapshot(env, ctx, scenario_id="TRUNC_TEST")
        self.assertTrue(rep.snapshot_truncated_or_crc_mismatch)
        self.assertTrue(rep.ephemeral_noresume_required)
        self.assertIn(WBI_SNAPSHOT_TRUNCATED_OR_CRC_MISMATCH, rep.error_codes)
        self.assertIn(WBI_EPHEMERAL_NORESUME_REQUIRED, rep.error_codes)
        self.assertTrue(rep.passed)  # Safe because ephemeral noresume bypass is active!
        self.assertEqual(rep.wbi_partition_writes, 0)

    def test_19_wbi2_detects_section_table_xor_metadata_corruption(self) -> None:
        bad_bytes, bad_tbl, _ = build_synthetic_wbi2_snapshot_bytes(sections=4, corrupt_meta_xor_index=2)
        info, codes, errs = parse_wbi2_header_and_table(
            bad_bytes[:WBI_SECTOR_SIZE],
            section_table_bytes=bad_tbl,
            available_bytes=len(bad_bytes),
        )
        self.assertIsNotNone(info)
        self.assertIn(WBI_SNAPSHOT_TRUNCATED_OR_CRC_MISMATCH, codes)
        self.assertTrue(any("XOR metadata checksum mismatch" in e for e in errs))

    def test_20_wbi2_detects_bad_magic_and_short_header(self) -> None:
        info_short, codes_short, _ = parse_wbi2_header_and_table(b"WBI2" + bytes(20))
        self.assertIsNone(info_short)
        self.assertIn(WBI_SNAPSHOT_TRUNCATED_OR_CRC_MISMATCH, codes_short)

        bad_hdr = b"BAD!" + bytes(WBI_SECTOR_SIZE - 4)
        _, codes_bad, _ = parse_wbi2_header_and_table(bad_hdr)
        self.assertIn(ERR_WBI_BAD_MAGIC, codes_bad)

    def test_21_wbi2_detects_kernel_abi_fingerprint_and_cross_sku_mismatch(self) -> None:
        full_bytes, tbl_bytes, valid_crc = build_synthetic_wbi2_snapshot_bytes(sections=4)
        env_stale = WbiSnapshotEnvelope(
            header_bytes=full_bytes[:WBI_SECTOR_SIZE],
            section_table_bytes=tbl_bytes,
            available_bytes=len(full_bytes),
            expected_total_bytes=len(full_bytes),
            declared_crc32=valid_crc,
            computed_crc32=valid_crc,
            kernel_uts_version=FX6_EXPECTED_KERNEL_UTS,
            kernel_build_fingerprint=PINNED_FX6_VMLINUX_KERNEL_SHA256,
            initramfs_layout_hash="a" * 64,
            firmware_slot_version="6.01",
            sku_code=FX6_SKU_NAME,
        )
        ctx_fx3 = WbiActiveBootContext(
            kernel_uts_version=FX3_EXPECTED_KERNEL_UTS,
            kernel_build_fingerprint=PINNED_FX3_VMLINUX_KERNEL_SHA256,
            sku_code=FX3_SKU_NAME,
            stage_b_ram_boot=True,
            bootargs=DEFAULT_SAFE_STAGE_B_NORESUME_BOOTARGS,
        )
        rep = triage_wbi_hibdrv_snapshot(env_stale, ctx_fx3, scenario_id="ABI_MISMATCH_TEST")
        self.assertTrue(rep.kernel_abi_fingerprint_mismatch)
        self.assertTrue(rep.ephemeral_noresume_required)
        self.assertFalse(rep.page_table_restore_panic_risk)
        self.assertIn(WBI_KERNEL_ABI_FINGERPRINT_MISMATCH, rep.error_codes)
        self.assertIn(WBI_EPHEMERAL_NORESUME_REQUIRED, rep.error_codes)
        self.assertEqual(rep.status, STATUS_WBI_POISONING_NORESUME_BYPASS)
        self.assertTrue(rep.passed)

    def test_22_wbi2_stage_b_ram_boot_without_noresume_fails_closed_with_panic_risk(self) -> None:
        full_bytes, tbl_bytes, valid_crc = build_synthetic_wbi2_snapshot_bytes(sections=4)
        env = WbiSnapshotEnvelope(
            header_bytes=full_bytes[:WBI_SECTOR_SIZE],
            section_table_bytes=tbl_bytes,
            available_bytes=len(full_bytes),
            expected_total_bytes=len(full_bytes),
            declared_crc32=valid_crc,
            computed_crc32=valid_crc,
        )
        ctx_unsafe = WbiActiveBootContext(
            stage_b_ram_boot=True,
            bootargs="console=ttyAMA0,115200 root=/dev/mmcblk0p7 ro rootwait init=/tmp/stage_b/sbin/init2_stage_b",
        )
        rep = triage_wbi_hibdrv_snapshot(env, ctx_unsafe, scenario_id="MISSING_NORESUME")
        self.assertFalse(rep.passed)
        self.assertTrue(rep.ephemeral_noresume_required)
        self.assertTrue(rep.page_table_restore_panic_risk)
        self.assertFalse(rep.noresume_bypass_active)
        self.assertIn(WBI_EPHEMERAL_NORESUME_REQUIRED, rep.error_codes)
        self.assertIn(ERR_WBI_PAGE_TABLE_RESTORE_PANIC_RISK, rep.error_codes)
        self.assertIn(ERR_NORESUME_MISSING_BYPASS_TOKEN, rep.error_codes)
        self.assertEqual(rep.wbi_partition_writes, 0)

    def test_23_wbi2_healthy_stock_fingerprint_match_passes_without_noresume(self) -> None:
        full_bytes, tbl_bytes, valid_crc = build_synthetic_wbi2_snapshot_bytes(sections=4)
        env = WbiSnapshotEnvelope(
            header_bytes=full_bytes[:WBI_SECTOR_SIZE],
            section_table_bytes=tbl_bytes,
            available_bytes=len(full_bytes),
            expected_total_bytes=len(full_bytes),
            declared_crc32=valid_crc,
            computed_crc32=valid_crc,
        )
        ctx_stock = WbiActiveBootContext(
            stage_b_ram_boot=False,
            bootargs="console=ttyAMA0,115200 root=/dev/mmcblk0p7 ro rootwait init=/sbin/init",
        )
        rep = triage_wbi_hibdrv_snapshot(env, ctx_stock, scenario_id="HEALTHY_STOCK")
        self.assertTrue(rep.passed)
        self.assertEqual(rep.status, STATUS_WBI_HEALTHY_RESUME_MATCH)
        self.assertFalse(rep.ephemeral_noresume_required)
        self.assertFalse(rep.page_table_restore_panic_risk)
        self.assertEqual(rep.wbi_partition_writes, 0)

    def test_24_wbi2_explicit_invalidated_magic_invl_cold_boots_safely(self) -> None:
        full_bytes, _, _ = build_synthetic_wbi2_snapshot_bytes(sections=4)
        for inv_magic in (b"invl", b"wbi2", b"WBI3", b"prof"):
            env = WbiSnapshotEnvelope(
                header_bytes=inv_magic + full_bytes[4:WBI_SECTOR_SIZE],
                available_bytes=len(full_bytes),
            )
            ctx = WbiActiveBootContext(
                stage_b_ram_boot=False,
                bootargs="console=ttyAMA0,115200 root=/dev/mmcblk0p7 ro rootwait init=/sbin/init",
            )
            rep = triage_wbi_hibdrv_snapshot(env, ctx, scenario_id=f"INVL_{inv_magic.decode()}")
            self.assertTrue(rep.passed)
            self.assertEqual(rep.status, STATUS_WBI_COLD_BOOT_INVALIDATED)
            self.assertEqual(rep.wbi_partition_writes, 0)

    def test_25_wbi2_header_rejects_unaligned_and_uncovered_resume_vector(self) -> None:
        full_bytes, tbl_bytes, _ = build_synthetic_wbi2_snapshot_bytes(sections=4)
        # Corrupt padding field (offset 4..8) to non-zero
        bad_pad = full_bytes[:4] + b"\x01\x00\x00\x00" + full_bytes[8:WBI_SECTOR_SIZE]
        _, codes, _ = parse_wbi2_header_and_table(bad_pad, section_table_bytes=tbl_bytes, available_bytes=len(full_bytes))
        self.assertIn(ERR_WBI_HEADER_OR_TABLE_INVALID, codes)

    def test_26_ephemeral_noresume_bootargs_accepts_noresume_or_hibdrv_resume_zero(self) -> None:
        rep_both = verify_ephemeral_noresume_bootargs_bypass(DEFAULT_SAFE_STAGE_B_NORESUME_BOOTARGS, require_noresume=True)
        self.assertTrue(rep_both.passed)
        self.assertTrue(rep_both.has_noresume)
        self.assertTrue(rep_both.has_hibdrv_resume_zero)
        self.assertTrue(rep_both.has_ro)
        self.assertFalse(rep_both.has_rw_emmc)
        self.assertEqual(rep_both.wbi_partition_writes, 0)

        rep_hib_only = verify_ephemeral_noresume_bootargs_bypass(
            "console=ttyAMA0,115200 root=/dev/mmcblk0p7 ro rootwait hibdrv.resume=0 init=/sbin/init",
            require_noresume=True,
        )
        self.assertTrue(rep_hib_only.passed)
        self.assertTrue(rep_hib_only.has_hibdrv_resume_zero)

    def test_27_ephemeral_noresume_bootargs_rejects_rw_emmc_repartition_wdt_bad_init(self) -> None:
        rep_rw = verify_ephemeral_noresume_bootargs_bypass(
            "console=ttyAMA0,115200 root=/dev/mmcblk0p7 rw rootwait noresume init=/sbin/init",
            require_noresume=True,
        )
        self.assertFalse(rep_rw.passed)
        self.assertTrue(rep_rw.has_rw_emmc)
        self.assertIn(ERR_NORESUME_RW_EMMC_OR_REPARTITION_FORBIDDEN, rep_rw.error_codes)

        rep_part = verify_ephemeral_noresume_bootargs_bypass(
            "console=ttyAMA0,115200 root=/dev/mmcblk0p7 ro rootwait noresume mtdparts=cxd:1M(wbi) init=/sbin/init",
            require_noresume=True,
        )
        self.assertFalse(rep_part.passed)
        self.assertTrue(rep_part.has_repartitioning)
        self.assertIn(ERR_NORESUME_RW_EMMC_OR_REPARTITION_FORBIDDEN, rep_part.error_codes)

        rep_wdt = verify_ephemeral_noresume_bootargs_bypass(
            "console=ttyAMA0,115200 root=/dev/mmcblk0p7 ro rootwait noresume nowatchdog init=/sbin/init",
            require_noresume=True,
        )
        self.assertFalse(rep_wdt.passed)
        self.assertTrue(rep_wdt.has_wdt_disable)
        self.assertIn(ERR_NORESUME_WDT_DISABLED, rep_wdt.error_codes)

        rep_init = verify_ephemeral_noresume_bootargs_bypass(
            "console=ttyAMA0,115200 root=/dev/mmcblk0p7 ro rootwait noresume init=/mnt/sd/evil.sh",
            require_noresume=True,
        )
        self.assertFalse(rep_init.passed)
        self.assertFalse(rep_init.init_verified)
        self.assertIn(ERR_NORESUME_UNVERIFIED_INIT, rep_init.error_codes)

    def test_28_allowed_noresume_init_paths_frozen(self) -> None:
        self.assertIn("/sbin/init", ALLOWED_NORESUME_INIT_PATHS)
        self.assertIn("/tmp/stage_b/sbin/init2_stage_b", ALLOWED_NORESUME_INIT_PATHS)

    def test_29_wbi_partition_write_firewall_blocks_all_emmc_wbi_writes(self) -> None:
        for target, op in (
            ("/dev/nflasha5", "dd_zero_erase"),
            ("/dev/mmcblk0p5", "blkdiscard"),
            ("wbi2", "invl_patch"),
            ("/dev/nflasha5", "inspect_readonly"),
        ):
            dec = audit_wbi_partition_write_attempt(target, op)
            self.assertFalse(dec.allowed)
            self.assertEqual(dec.status, STATUS_WBI_PERSISTENT_WRITE_BLOCKED)
            self.assertEqual(dec.wbi_partition_writes, 0)
            self.assertEqual(dec.physical_device_writes, 0)
            self.assertFalse(dec.persistent_emmc_writes_authorized)
            self.assertFalse(dec.persistent_write_release)
            self.assertIn(ERR_WBI_PERSISTENT_PARTITION_WRITE_FORBIDDEN, dec.error_codes)

    def test_30_wbi_6_scenario_suite_passes_all_scenarios_with_zero_writes(self) -> None:
        res = run_wbi_hibdrv_6_scenario_triage()
        self.assertTrue(res.passed, f"WBI 6-scenario errors: {res.errors}")
        self.assertEqual(res.scenarios_passed, 6)
        self.assertEqual(res.scenarios_total, 6)
        self.assertEqual([r.scenario_id for r in res.scenario_results], list(WBI_SCENARIO_IDS))
        self.assertFalse(res.write_firewall_decision.allowed)
        self.assertEqual(res.write_firewall_decision.wbi_partition_writes, 0)

        by_id = {r.scenario_id: r for r in res.scenario_results}
        self.assertTrue(by_id["W2_POWER_DROP_MID_SNAPSHOT_TRUNCATED_CRC"].snapshot_truncated_or_crc_mismatch)
        self.assertTrue(by_id["W3_STALE_SLOT_KERNEL_UTS_OR_INITRAMFS_MISMATCH"].kernel_abi_fingerprint_mismatch)
        self.assertTrue(by_id["W4_STAGE_B_RAM_BOOT_NORESUME_BYPASS_ACTIVE"].ephemeral_noresume_required)
        self.assertFalse(by_id["W5_STAGE_B_RAM_BOOT_MISSING_NORESUME_REJECTED"].passed)
        self.assertTrue(by_id["W5_STAGE_B_RAM_BOOT_MISSING_NORESUME_REJECTED"].page_table_restore_panic_risk)
        self.assertEqual(by_id["W6_PERSISTENT_WBI_ERASE_ATTEMPT_BLOCKED"].status, STATUS_WBI_COLD_BOOT_INVALIDATED)

    # ------------------------------------------------------------------
    # Pillar C — Master Suite Determinism, CLI & 12-Pillar Integration
    # ------------------------------------------------------------------

    def test_31_clean_room_suite_sha256_is_deterministic(self) -> None:
        r2 = run_squashfs_and_hibdrv_wbi_suite(force_clean_room=True)
        self.assertEqual(self.clean_report.suite_sha256, r2.suite_sha256)
        self.assertEqual(self.clean_report.wbi_6_scenario_suite.suite_sha256, r2.wbi_6_scenario_suite.suite_sha256)

    def test_32_json_serialization_no_raw_bytes_and_no_nan(self) -> None:
        rendered = json.dumps(self.suite_report.to_dict(), ensure_ascii=False, sort_keys=True, allow_nan=False)
        self.assertNotRegex(rendered, RAW_BYTES_RE)
        decoded = json.loads(rendered)
        self.assertEqual(decoded["suite_sha256"], self.suite_report.suite_sha256)
        self.assertEqual(decoded["wbi_partition_writes"], 0)
        self.assertEqual(decoded["physical_device_writes"], 0)
        self.assertEqual(decoded["otp_fuse_touches"], 0)
        self.assertEqual(decoded["passive_tx_bytes_emitted"], 0)
        self.assertFalse(decoded["persistent_emmc_writes_authorized"])
        self.assertFalse(decoded["persistent_write_release"])

    def test_33_cli_verify_squashfs_wbi_triage_clean_room_json_and_text(self) -> None:
        buf_json = io.StringIO()
        with (
            mock.patch.object(sys, "argv", ["fx3_recovery", "verify-squashfs-wbi-triage", "--clean-room", "--json"]),
            redirect_stdout(buf_json),
        ):
            rc_json = fx3_cli.main()
        self.assertEqual(rc_json, 0)
        rendered = buf_json.getvalue()
        self.assertNotRegex(rendered, RAW_BYTES_RE)
        parsed = json.loads(rendered)
        self.assertEqual(parsed["status"], STATUS_VERIFIED_SQUASHFS_WBI_GATE)
        self.assertEqual(parsed["verification_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(parsed["wbi_partition_writes"], 0)

        buf_txt = io.StringIO()
        with (
            mock.patch.object(sys, "argv", ["fx3_recovery", "verify-squashfs-wbi-triage", "--clean-room"]),
            redirect_stdout(buf_txt),
        ):
            rc_txt = fx3_cli.main()
        self.assertEqual(rc_txt, 0)
        txt = buf_txt.getvalue()
        self.assertIn("status=VERIFIED_SQUASHFS_AND_HIBDRV_WBI_GATE", txt)
        self.assertIn("wbi_partition_writes=0", txt)

    def test_34_cli_verify_squashfs_wbi_triage_active_mode(self) -> None:
        buf = io.StringIO()
        with (
            mock.patch.object(sys, "argv", ["fx3_recovery", "verify-squashfs-wbi-triage", "--json"]),
            redirect_stdout(buf),
        ):
            rc = fx3_cli.main()
        self.assertEqual(rc, 0)
        rendered = buf.getvalue()
        self.assertNotRegex(rendered, RAW_BYTES_RE)
        parsed = json.loads(rendered)
        self.assertTrue(parsed["all_passed"])
        self.assertIn(parsed["verification_mode"], ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"))

    def test_35_cli_verify_squashfs_wbi_triage_out_writes_artifact(self) -> None:
        scratch_root = ROOT / "work" / "_tests" / "phase119_cli_out"
        if scratch_root.exists():
            shutil.rmtree(scratch_root)
        scratch_root.parent.mkdir(parents=True, exist_ok=True)
        try:
            buf = io.StringIO()
            with (
                mock.patch.object(
                    sys,
                    "argv",
                    [
                        "fx3_recovery",
                        "verify-squashfs-wbi-triage",
                        "--clean-room",
                        "--json",
                        "--out",
                        str(scratch_root),
                    ],
                ),
                redirect_stdout(buf),
            ):
                rc = fx3_cli.main()
            self.assertEqual(rc, 0)
            out_file = scratch_root / "squashfs-wbi-triage-report.json"
            self.assertTrue(out_file.is_file())
            written = json.loads(out_file.read_text(encoding="utf-8"))
            self.assertEqual(written["status"], STATUS_VERIFIED_SQUASHFS_WBI_GATE)
            self.assertEqual(written["wbi_partition_writes"], 0)
        finally:
            if scratch_root.exists():
                shutil.rmtree(scratch_root)

    def test_36_cli_verify_squashfs_wbi_triage_failure_returns_exit_2(self) -> None:
        failing = SquashfsAndHibdrvWbiSuiteReport(
            **{**self.clean_report.__dict__, "all_passed": False, "status": STATUS_FAIL_SQUASHFS_WBI_GATE}
        )
        with mock.patch("fx3_recovery.__main__.run_squashfs_and_hibdrv_wbi_suite", return_value=failing):
            buf = io.StringIO()
            with (
                mock.patch.object(sys, "argv", ["fx3_recovery", "verify-squashfs-wbi-triage", "--clean-room", "--json"]),
                redirect_stdout(buf),
            ):
                rc = fx3_cli.main()
            self.assertEqual(rc, 2)
            parsed = json.loads(buf.getvalue())
            self.assertFalse(parsed["all_passed"])
            self.assertEqual(parsed["status"], STATUS_FAIL_SQUASHFS_WBI_GATE)

    def test_37_cli_verify_all_recovery_12_pillars_clean_room_and_failure_propagation(self) -> None:
        buf = io.StringIO()
        with (
            mock.patch.object(
                sys,
                "argv",
                [
                    "fx3_recovery",
                    "verify-all-recovery",
                    "--clean-room",
                    "--with-phase94",
                    "--with-phase101",
                    "--with-phase106",
                    "--with-phase113",
                    "--with-phase119",
                    "--json",
                ],
            ),
            redirect_stdout(buf),
        ):
            rc = fx3_cli.main()
        self.assertEqual(rc, 0)
        rendered = buf.getvalue()
        self.assertNotRegex(rendered, RAW_BYTES_RE)
        parsed = json.loads(rendered)
        self.assertTrue(parsed["all_passed"])
        self.assertGreaterEqual(parsed["pillar_count"], 12)
        self.assertEqual(parsed["pillars_passed"], parsed["pillar_count"])
        self.assertIn("phase119_pillar12_squashfs_wbi_hibdrv", parsed)
        self.assertEqual(parsed["phase119_pillar12_squashfs_wbi_hibdrv"]["status"], STATUS_VERIFIED_SQUASHFS_WBI_GATE)

        failing = SquashfsAndHibdrvWbiSuiteReport(
            **{**self.clean_report.__dict__, "all_passed": False, "status": STATUS_FAIL_SQUASHFS_WBI_GATE}
        )
        with mock.patch("fx3_recovery.__main__.run_squashfs_and_hibdrv_wbi_suite", return_value=failing):
            buf_fail = io.StringIO()
            with (
                mock.patch.object(
                    sys,
                    "argv",
                    [
                        "fx3_recovery",
                        "verify-all-recovery",
                        "--clean-room",
                        "--with-phase94",
                        "--with-phase101",
                        "--with-phase106",
                        "--with-phase113",
                        "--with-phase119",
                        "--json",
                    ],
                ),
                redirect_stdout(buf_fail),
            ):
                rc_fail = fx3_cli.main()
            self.assertEqual(rc_fail, 2)
            parsed_fail = json.loads(buf_fail.getvalue())
            self.assertFalse(parsed_fail["all_passed"])
            self.assertGreaterEqual(parsed_fail["pillar_count"], 12)
            self.assertEqual(parsed_fail["pillars_passed"], parsed_fail["pillar_count"] - 1)

    def test_38_cli_verify_all_recovery_12_pillars_active_mode(self) -> None:
        buf = io.StringIO()
        with (
            mock.patch.object(
                sys,
                "argv",
                [
                    "fx3_recovery",
                    "verify-all-recovery",
                    "--with-phase94",
                    "--with-phase101",
                    "--with-phase106",
                    "--with-phase113",
                    "--with-phase119",
                    "--json",
                ],
            ),
            redirect_stdout(buf),
        ):
            rc = fx3_cli.main()
        self.assertEqual(rc, 0)
        rendered = buf.getvalue()
        self.assertNotRegex(rendered, RAW_BYTES_RE)
        parsed = json.loads(rendered)
        self.assertTrue(parsed["all_passed"])
        self.assertGreaterEqual(parsed["pillar_count"], 12)
        self.assertEqual(parsed["pillars_passed"], parsed["pillar_count"])
        self.assertIn("phase119_pillar12_squashfs_wbi_hibdrv", parsed)

    def test_39_cli_verify_all_recovery_default_7_pillar_compatibility_preserved(self) -> None:
        buf = io.StringIO()
        with (
            mock.patch.object(
                sys,
                "argv",
                ["fx3_recovery", "verify-all-recovery", "--clean-room", "--json"],
            ),
            redirect_stdout(buf),
        ):
            rc = fx3_cli.main()
        self.assertEqual(rc, 0)
        parsed = json.loads(buf.getvalue())
        self.assertEqual(parsed["pillar_count"], 7)
        self.assertEqual(parsed["pillars_passed"], 7)
        self.assertNotIn("phase119_pillar12_squashfs_wbi_hibdrv", parsed)

    def test_40_cli_verify_all_recovery_text_output_shows_12_pillars(self) -> None:
        buf = io.StringIO()
        with (
            mock.patch.object(
                sys,
                "argv",
                [
                    "fx3_recovery",
                    "verify-all-recovery",
                    "--clean-room",
                    "--with-phase94",
                    "--with-phase101",
                    "--with-phase106",
                    "--with-phase113",
                    "--with-phase119",
                ],
            ),
            redirect_stdout(buf),
        ):
            rc = fx3_cli.main()
        self.assertEqual(rc, 0)
        txt = buf.getvalue()
        self.assertIn("pillars=12/12", txt)
        self.assertIn("physical_device_writes=0", txt)
        self.assertIn("persistent_emmc_writes_authorized=False", txt)


if __name__ == "__main__":
    unittest.main()
