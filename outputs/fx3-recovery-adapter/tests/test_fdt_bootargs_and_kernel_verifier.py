"""Phase 106 Dual-Mode Fast Unit Tests (>=36 tests, <0.5s clean-room):

- Pillar 1A: Pure-Python IEEE 1275 / Devicetree v17 (`0xd00dfeed`) binary parser & in-memory synthesizer
- Pillar 1B: `/chosen/bootargs` & `/chosen/linux,initrd-start..end` fail-closed Stage-B firewall
- Pillar 2:  ARM64 Linux `Image` (`0x644d5241` 'ARM\\x64' @ `0x38`) header & cross-SKU FX6 firewall
- Pillar 3:  10-Pillar `verify-all-recovery --with-phase94 --with-phase101 --with-phase106` & CLI
"""

from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import shutil
import struct
import sys
import tempfile
import time
import unittest
from unittest import mock

import fx3_recovery
from fx3_recovery import __main__ as fx3_cli
from fx3_recovery.fdt_bootargs_and_kernel_verifier import (
    ALLOW_BOOT_PARTITION_TARGETING,
    ALLOW_DESTRUCTIVE_FASTBOOT,
    ALLOWED_VERIFIED_INIT_PATHS,
    ARM64_IMAGE_HEADER_SIZE,
    ARM64_IMAGE_MAGIC,
    ARM64_IMAGE_MAGIC_U32,
    CXD90057_COMPATIBLE,
    CXD90057_DRAM_BASE,
    CXD90057_DRAM_SIZE,
    CXD90057_INITRD_BASE,
    CXD90057_SOC_MODEL,
    DEFAULT_SAFE_STAGE_B_BOOTARGS,
    DONOR_FX3_BOOT_DTB_RELPATH,
    DONOR_FX3_KEMCO_RELPATH,
    DONOR_FX3_SETTING_DTB_RELPATH,
    DONOR_FX3_VMLINUX_RELPATH,
    DONOR_FX6_KEMCO_RELPATH,
    DONOR_FX6_SETTING_DTB_RELPATH,
    DONOR_FX6_VMLINUX_RELPATH,
    ERR_BOOTARGS_FORBIDDEN_REPARTITIONING,
    ERR_BOOTARGS_MALFORMED,
    ERR_BOOTARGS_MISSING_OR_EMPTY,
    ERR_BOOTARGS_MISSING_RO,
    ERR_BOOTARGS_MISSING_ROOTWAIT,
    ERR_BOOTARGS_RW_EMMC_ROOTFS,
    ERR_BOOTARGS_UNVERIFIED_INIT_PATH,
    ERR_BOOTARGS_WDT_DISABLED,
    ERR_FDT_BAD_BOUNDS,
    ERR_FDT_BAD_MAGIC,
    ERR_FDT_BAD_MEM_RSVMAP,
    ERR_FDT_BAD_STRING_OFFSET,
    ERR_FDT_BAD_TOTALSIZE,
    ERR_FDT_EMPTY_OR_TRUNCATED_HEADER,
    ERR_FDT_MALFORMED_TOKENS,
    ERR_FDT_MISSING_CHOSEN,
    ERR_FDT_MISSING_END_TOKEN,
    ERR_FDT_NONZERO_PADDING,
    ERR_FDT_OVERLAPPING_REGIONS,
    ERR_FDT_SOC_MISMATCH,
    ERR_FDT_UNCLOSED_NODE,
    ERR_FDT_UNKNOWN_TOKEN,
    ERR_FDT_UNSUPPORTED_VERSION,
    ERR_INITRD_ASYMMETRIC_BOUNDS,
    ERR_INITRD_INVALID_CELL_SIZE,
    ERR_INITRD_INVALID_RANGE,
    ERR_INITRD_MISSING,
    ERR_INITRD_SIZE_OUT_OF_BOUNDS,
    ERR_KERNEL_BAD_ARM64_MAGIC,
    ERR_KERNEL_BIG_ENDIAN_FORBIDDEN,
    ERR_KERNEL_CROSS_SKU_FX6_TRANSPLANT,
    ERR_KERNEL_INVALID_CODE0,
    ERR_KERNEL_INVALID_TEXT_OFFSET,
    ERR_KERNEL_NONZERO_RESERVED_FLAGS,
    ERR_KERNEL_RELEASE_MISMATCH,
    ERR_KERNEL_SHA256_MISMATCH,
    ERR_KERNEL_SOC_MISMATCH,
    ERR_KERNEL_TRUNCATED_HEADER,
    ERR_KERNEL_TRUNCATED_IMAGE,
    ERR_KERNEL_UNSUPPORTED_PAGE_SIZE,
    ERR_KERNEL_ZERO_IMAGE_SIZE,
    EXPECTED_ARM64_IMAGE_SIZE,
    EXPECTED_ARM64_TEXT_OFFSET,
    EXPECTED_FX3_KERNEL_RELEASE,
    FDT_BEGIN_NODE,
    FDT_BOOTARGS_KERNEL_SCHEMA,
    FDT_END,
    FDT_END_NODE,
    FDT_HEADER_SIZE,
    FDT_MAGIC,
    FDT_MAGIC_U32,
    FDT_NOP,
    FDT_PROP,
    FX3_KEMCO_INITRD_SIZE,
    FX3_KERNEL_MIN_FILE_BYTES,
    MAX_INITRD_WINDOW_BYTES,
    OTP_FUSE_TOUCHES,
    PASSIVE_TX_BYTES_EMITTED,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHYSICAL_DEVICE_WRITES,
    PINNED_CXD90057_BOOT_DTB_SHA256,
    PINNED_CXD90057_SETTING_DTB_SHA256,
    PINNED_FX3_VMLINUX_SHA256,
    PINNED_FX6_VMLINUX_SHA256,
    READ_ONLY_DONOR_ACCESS,
    STATUS_FAIL_FDT_KERNEL_GATE,
    STATUS_REJECTED_ARM64_KERNEL,
    STATUS_REJECTED_BOOTARGS_FIREWALL,
    STATUS_REJECTED_FDT_BLOB,
    STATUS_VERIFIED_ARM64_KERNEL,
    STATUS_VERIFIED_BOOTARGS_FIREWALL,
    STATUS_VERIFIED_FDT_BLOB,
    STATUS_VERIFIED_FDT_KERNEL_GATE,
    FdtBootargsAndKernelSuiteReport,
    audit_arm64_kernel_image,
    audit_fdt_chosen_bootargs,
    build_synthetic_arm64_kernel_image,
    build_synthetic_fdt_blob,
    inspect_fdt_and_kernel_donors_readonly,
    parse_fdt_blob,
    run_fdt_bootargs_and_kernel_suite,
)
from fx3_recovery.files import is_forced_clean_room, read_file, resolve_donor_path

ROOT = Path(__file__).resolve().parents[3]


class TestFdtBootargsAndKernelVerifier(unittest.TestCase):
    suite_report: FdtBootargsAndKernelSuiteReport

    @classmethod
    def setUpClass(cls) -> None:
        cls.suite_report = run_fdt_bootargs_and_kernel_suite()

    def setUp(self) -> None:
        self._sandbox = (
            ROOT / "outputs" / "fx3-recovery-adapter" / f".tmp-phase106-test-{os.getpid()}-{time.time_ns()}"
        )

    def tearDown(self) -> None:
        shutil.rmtree(self._sandbox, ignore_errors=True)

    # ------------------------------------------------------------------
    # Safety Redlines & Package Exports
    # ------------------------------------------------------------------

    def test_01_safety_redlines_and_package_exports(self) -> None:
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(PERSISTENT_WRITE_RELEASE)
        self.assertFalse(ALLOW_BOOT_PARTITION_TARGETING)
        self.assertFalse(ALLOW_DESTRUCTIVE_FASTBOOT)
        self.assertTrue(READ_ONLY_DONOR_ACCESS)
        self.assertEqual(OTP_FUSE_TOUCHES, 0)
        self.assertEqual(PASSIVE_TX_BYTES_EMITTED, 0)
        self.assertEqual(PHYSICAL_DEVICE_WRITES, 0)
        self.assertEqual(FDT_MAGIC, 0xD00DFEED)
        self.assertEqual(FDT_MAGIC_U32, 0xD00DFEED)
        self.assertEqual(ARM64_IMAGE_MAGIC, 0x644D5241)
        self.assertEqual(ARM64_IMAGE_MAGIC_U32, 0x644D5241)
        # Ensure tier0 bytes-typed magic exports were NOT overwritten in fx3_recovery
        self.assertIsInstance(fx3_recovery.FDT_MAGIC, bytes)
        self.assertIsInstance(fx3_recovery.ARM64_IMAGE_MAGIC, bytes)
        for name in (
            "fdt_bootargs_and_kernel_verifier",
            "FDT_MAGIC_U32",
            "ARM64_IMAGE_MAGIC_U32",
            "parse_fdt_blob",
            "audit_fdt_chosen_bootargs",
            "audit_arm64_kernel_image",
            "build_synthetic_fdt_blob",
            "build_synthetic_arm64_kernel_image",
            "inspect_fdt_and_kernel_donors_readonly",
            "run_fdt_bootargs_and_kernel_suite",
        ):
            self.assertTrue(hasattr(fx3_recovery, name), f"missing export {name}")
            self.assertIn(name, fx3_recovery.__all__)

    # ------------------------------------------------------------------
    # Dual-Mode Donor Inspection (O_RDONLY & Clean-Room Fallback)
    # ------------------------------------------------------------------

    def test_02_dual_mode_donor_inspection_and_forced_clean_room(self) -> None:
        clean_snap = inspect_fdt_and_kernel_donors_readonly(force_clean_room=True)
        self.assertEqual(clean_snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(clean_snap.read_only_access)
        self.assertTrue(clean_snap.fx3_setting_dtb_ok)
        self.assertTrue(clean_snap.fx3_boot_dtb_ok)
        self.assertTrue(clean_snap.fx6_setting_dtb_ok)
        self.assertTrue(clean_snap.fx3_kernel_ok)
        self.assertTrue(clean_snap.fx6_kernel_detected_as_fx6)
        self.assertTrue(clean_snap.fx3_kemco_ok)
        self.assertTrue(clean_snap.fx6_kemco_ok)
        self.assertEqual(len(clean_snap.snapshot_sha256), 64)

        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            env_snap = inspect_fdt_and_kernel_donors_readonly()
            self.assertEqual(env_snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertEqual(env_snap.snapshot_sha256, clean_snap.snapshot_sha256)

    def test_03_local_donor_o_rdonly_real_dtbs_and_kernels_when_present(self) -> None:
        if is_forced_clean_room():
            self.skipTest("Clean-room forced via FX3_FX6_FORCE_CLEAN_ROOM=1")
        paths = [
            resolve_donor_path(DONOR_FX3_SETTING_DTB_RELPATH),
            resolve_donor_path(DONOR_FX3_BOOT_DTB_RELPATH),
            resolve_donor_path(DONOR_FX6_SETTING_DTB_RELPATH),
            resolve_donor_path(DONOR_FX3_VMLINUX_RELPATH),
            resolve_donor_path(DONOR_FX6_VMLINUX_RELPATH),
            resolve_donor_path(DONOR_FX3_KEMCO_RELPATH),
            resolve_donor_path(DONOR_FX6_KEMCO_RELPATH),
        ]
        if not all(p is not None and p.is_file() for p in paths):
            self.skipTest("Local FX3/FX6 donor files not present")

        snap = inspect_fdt_and_kernel_donors_readonly(force_clean_room=False)
        self.assertEqual(snap.verification_mode, "LOCAL_DONOR_O_RDONLY")
        self.assertTrue(snap.fx3_setting_dtb_ok)
        self.assertTrue(snap.fx3_boot_dtb_ok)
        self.assertTrue(snap.fx6_setting_dtb_ok)
        self.assertTrue(snap.fx3_kernel_ok)
        self.assertTrue(snap.fx6_kernel_detected_as_fx6)

        by_lbl = {a.label: a for a in snap.artifacts}
        self.assertEqual(by_lbl["fx3_setting_cxd90057_dtb"].sha256, PINNED_CXD90057_SETTING_DTB_SHA256)
        self.assertEqual(by_lbl["fx3_boot_cxd90057_dtb"].sha256, PINNED_CXD90057_BOOT_DTB_SHA256)
        self.assertEqual(by_lbl["fx3_vmlinux_arm64_image"].sha256, PINNED_FX3_VMLINUX_SHA256)
        self.assertEqual(by_lbl["fx6_vmlinux_arm64_image"].sha256, PINNED_FX6_VMLINUX_SHA256)
        self.assertGreaterEqual(by_lbl["fx3_vmlinux_arm64_image"].byte_length, FX3_KERNEL_MIN_FILE_BYTES)

        # Direct read_file + audit on real FX6 kernel confirms cross-SKU firewall rejects it
        assert paths[4] is not None
        fx6_bytes = read_file(paths[4], 32 * 1024 * 1024)
        fx6_rep = audit_arm64_kernel_image(fx6_bytes, label="real_fx6_vmlinux.bin", min_file_bytes=FX3_KERNEL_MIN_FILE_BYTES)
        self.assertFalse(fx6_rep.passed)
        self.assertEqual(fx6_rep.detected_sku, "ILME-FX6")
        self.assertIn(ERR_KERNEL_CROSS_SKU_FX6_TRANSPLANT, fx6_rep.error_codes)

    # ------------------------------------------------------------------
    # Pillar 1A: Pure-Python FDT (0xd00dfeed v17) Parser & Synthesizer
    # ------------------------------------------------------------------

    def test_04_fdt_synthesizer_and_parser_roundtrip_with_mem_rsvmap_and_nop(self) -> None:
        blob = build_synthetic_fdt_blob(
            mem_rsvmap=[(0x400000000, 0x10000), (0x408000000, 0x2000000)],
            boot_cpuid_phys=0,
            include_nop_token=True,
        )
        rep = parse_fdt_blob(blob)
        self.assertTrue(rep.valid, rep.errors)
        self.assertEqual(rep.status, STATUS_VERIFIED_FDT_BLOB)
        self.assertIsNotNone(rep.header)
        assert rep.header is not None
        self.assertEqual(rep.header.magic, FDT_MAGIC)
        self.assertEqual(rep.header.magic_hex, "0xd00dfeed")
        self.assertEqual(rep.header.version, 17)
        self.assertEqual(rep.header.totalsize, len(blob))
        self.assertEqual(len(rep.mem_rsvmap), 2)
        self.assertEqual(rep.mem_rsvmap[0].address, CXD90057_DRAM_BASE)
        self.assertEqual(rep.mem_rsvmap[1].size, FX3_KEMCO_INITRD_SIZE)
        self.assertEqual(rep.root_model, CXD90057_SOC_MODEL)
        self.assertEqual(rep.root_compatible, (CXD90057_COMPATIBLE,))
        self.assertTrue(rep.has_chosen)
        self.assertEqual(rep.chosen_stdout_path, "serial0:460800n8")
        self.assertEqual(rep.chosen_bootargs, DEFAULT_SAFE_STAGE_B_BOOTARGS)
        self.assertEqual(rep.chosen_initrd_start, CXD90057_INITRD_BASE)
        self.assertEqual(rep.chosen_initrd_end, CXD90057_INITRD_BASE + FX3_KEMCO_INITRD_SIZE)
        self.assertEqual(rep.node_count, 3)

    def test_05_fdt_rejects_empty_and_truncated_header(self) -> None:
        for size in (0, 12, FDT_HEADER_SIZE - 1):
            rep = parse_fdt_blob(b"\x00" * size)
            self.assertFalse(rep.valid)
            self.assertEqual(rep.status, STATUS_REJECTED_FDT_BLOB)
            self.assertIn(ERR_FDT_EMPTY_OR_TRUNCATED_HEADER, rep.error_codes)

    def test_06_fdt_rejects_bad_magic_and_truncated_totalsize(self) -> None:
        valid = build_synthetic_fdt_blob()
        bad_magic = b"\xca\xfe\xba\xbe" + valid[4:]
        rep_m = parse_fdt_blob(bad_magic)
        self.assertFalse(rep_m.valid)
        self.assertIn(ERR_FDT_BAD_MAGIC, rep_m.error_codes)

        rep_t = parse_fdt_blob(valid[:-4])
        self.assertFalse(rep_t.valid)
        self.assertIn(ERR_FDT_BAD_TOTALSIZE, rep_t.error_codes)

        # Declared totalsize < header size
        tiny_hdr = bytearray(valid)
        struct.pack_into(">I", tiny_hdr, 4, 20)
        rep_tiny = parse_fdt_blob(bytes(tiny_hdr))
        self.assertFalse(rep_tiny.valid)
        self.assertIn(ERR_FDT_BAD_TOTALSIZE, rep_tiny.error_codes)

    def test_07_fdt_rejects_unsupported_version(self) -> None:
        blob = build_synthetic_fdt_blob(version=16, last_comp_version=16)
        rep = parse_fdt_blob(blob)
        self.assertFalse(rep.valid)
        self.assertIn(ERR_FDT_UNSUPPORTED_VERSION, rep.error_codes)

    def test_08_fdt_rejects_out_of_bounds_and_overlapping_regions(self) -> None:
        valid = bytearray(build_synthetic_fdt_blob())
        # Misaligned off_dt_struct
        bad_align = bytearray(valid)
        struct.pack_into(">I", bad_align, 8, FDT_HEADER_SIZE + 2)
        rep_a = parse_fdt_blob(bytes(bad_align))
        self.assertFalse(rep_a.valid)
        self.assertIn(ERR_FDT_BAD_BOUNDS, rep_a.error_codes)

        # Overlapping dt_struct and dt_strings
        overlap = bytearray(valid)
        off_struct = struct.unpack_from(">I", overlap, 8)[0]
        struct.pack_into(">I", overlap, 12, off_struct)
        rep_o = parse_fdt_blob(bytes(overlap))
        self.assertFalse(rep_o.valid)
        self.assertIn(ERR_FDT_OVERLAPPING_REGIONS, rep_o.error_codes)

    def test_09_fdt_rejects_unterminated_mem_rsvmap(self) -> None:
        valid = bytearray(build_synthetic_fdt_blob())
        off_rsv = struct.unpack_from(">I", valid, 16)[0]
        # Replace (0, 0) terminator with non-zero entry so table hits off_dt_struct without terminating
        struct.pack_into(">QQ", valid, off_rsv, 0x400000000, 0x1000)
        rep = parse_fdt_blob(bytes(valid))
        self.assertFalse(rep.valid)
        self.assertIn(ERR_FDT_BAD_MEM_RSVMAP, rep.error_codes)

    def test_10_fdt_rejects_bad_string_offset_and_nonzero_padding(self) -> None:
        valid = build_synthetic_fdt_blob()
        rep_ok = parse_fdt_blob(valid)
        assert rep_ok.header is not None
        off_struct = rep_ok.header.off_dt_struct

        # Corrupt first FDT_PROP nameoff (root node has FDT_BEGIN_NODE=4, ""+nul+pad=4, FDT_PROP=4, len=4, nameoff at +16)
        bad_str = bytearray(valid)
        struct.pack_into(">I", bad_str, off_struct + 16, 0xFFFFFF)
        rep_s = parse_fdt_blob(bytes(bad_str))
        self.assertFalse(rep_s.valid)
        self.assertIn(ERR_FDT_BAD_STRING_OFFSET, rep_s.error_codes)

        # Corrupt alignment padding after root "" node name (offset off_struct + 5..7)
        bad_pad = bytearray(valid)
        bad_pad[off_struct + 5] = 0xAA
        rep_p = parse_fdt_blob(bytes(bad_pad))
        self.assertFalse(rep_p.valid)
        self.assertIn(ERR_FDT_NONZERO_PADDING, rep_p.error_codes)

    def test_11_fdt_rejects_unknown_token_unclosed_node_and_missing_end(self) -> None:
        valid = build_synthetic_fdt_blob()
        rep_ok = parse_fdt_blob(valid)
        assert rep_ok.header is not None
        off_struct = rep_ok.header.off_dt_struct
        end_struct = off_struct + rep_ok.header.size_dt_struct

        # Replace final FDT_END with unknown token
        bad_tok = bytearray(valid)
        struct.pack_into(">I", bad_tok, end_struct - 4, 0x12345678)
        rep_u = parse_fdt_blob(bytes(bad_tok))
        self.assertFalse(rep_u.valid)
        self.assertIn(ERR_FDT_UNKNOWN_TOKEN, rep_u.error_codes)

        # Replace final FDT_END with FDT_NOP -> missing FDT_END
        no_end = bytearray(valid)
        struct.pack_into(">I", no_end, end_struct - 4, FDT_NOP)
        rep_ne = parse_fdt_blob(bytes(no_end))
        self.assertFalse(rep_ne.valid)
        self.assertIn(ERR_FDT_MISSING_END_TOKEN, rep_ne.error_codes)

        # Overwrite root FDT_END_NODE (just before FDT_END) with FDT_NOP -> unclosed node at FDT_END
        unclosed = bytearray(valid)
        struct.pack_into(">I", unclosed, end_struct - 8, FDT_NOP)
        rep_uc = parse_fdt_blob(bytes(unclosed))
        self.assertFalse(rep_uc.valid)
        self.assertIn(ERR_FDT_UNCLOSED_NODE, rep_uc.error_codes)

    def test_12_fdt_rejects_prop_outside_node_and_end_node_underflow(self) -> None:
        valid = build_synthetic_fdt_blob()
        rep_ok = parse_fdt_blob(valid)
        assert rep_ok.header is not None
        off_struct = rep_ok.header.off_dt_struct

        # Replace root FDT_BEGIN_NODE with FDT_END_NODE -> underflow
        under = bytearray(valid)
        struct.pack_into(">I", under, off_struct, FDT_END_NODE)
        rep_under = parse_fdt_blob(bytes(under))
        self.assertFalse(rep_under.valid)
        self.assertIn(ERR_FDT_MALFORMED_TOKENS, rep_under.error_codes)

        # Replace root FDT_BEGIN_NODE with FDT_PROP -> property outside node
        prop_out = bytearray(valid)
        struct.pack_into(">I", prop_out, off_struct, FDT_PROP)
        rep_po = parse_fdt_blob(bytes(prop_out))
        self.assertFalse(rep_po.valid)
        self.assertIn(ERR_FDT_MALFORMED_TOKENS, rep_po.error_codes)

    # ------------------------------------------------------------------
    # Pillar 1B: /chosen/bootargs & initrd Firewall
    # ------------------------------------------------------------------

    def test_13_bootargs_firewall_passes_compliant_stage_b_32bit_and_64bit_initrd(self) -> None:
        for cell_sz, start_addr, size_val in (
            (8, CXD90057_INITRD_BASE, FX3_KEMCO_INITRD_SIZE),
            (4, 0x80000000, 0x1000000),
        ):
            blob = build_synthetic_fdt_blob(
                bootargs=DEFAULT_SAFE_STAGE_B_BOOTARGS,
                initrd_start=start_addr,
                initrd_end=start_addr + size_val,
                initrd_cell_bytes=cell_sz,
            )
            rep = audit_fdt_chosen_bootargs(blob)
            self.assertTrue(rep.passed, rep.errors)
            self.assertEqual(rep.status, STATUS_VERIFIED_BOOTARGS_FIREWALL)
            self.assertTrue(rep.rootfs_is_emmc_block)
            self.assertTrue(rep.has_ro)
            self.assertFalse(rep.has_rw)
            self.assertTrue(rep.has_rootwait)
            self.assertTrue(rep.init_path_verified)
            self.assertFalse(rep.has_forbidden_repartitioning)
            self.assertTrue(rep.watchdog_enabled)
            self.assertTrue(rep.initrd_present)
            self.assertTrue(rep.initrd_valid)
            self.assertEqual(rep.initrd_size_bytes, size_val)
            self.assertFalse(rep.persistent_emmc_writes_authorized)
            self.assertFalse(rep.persistent_write_release)
            self.assertEqual(rep.physical_device_writes, 0)

    def test_14_bootargs_firewall_rejects_rw_emmc_rootfs_and_missing_ro_rootwait(self) -> None:
        for root_dev in ("/dev/mmcblk0p7", "/dev/nflasha2", "/dev/cnflasha1"):
            rw_blob = build_synthetic_fdt_blob(
                bootargs=f"console=ttyAMA0,115200 root={root_dev} rw rootwait init=/sbin/init"
            )
            rep_rw = audit_fdt_chosen_bootargs(rw_blob)
            self.assertFalse(rep_rw.passed)
            self.assertEqual(rep_rw.status, STATUS_REJECTED_BOOTARGS_FIREWALL)
            self.assertIn(ERR_BOOTARGS_RW_EMMC_ROOTFS, rep_rw.error_codes)
            self.assertIn(ERR_BOOTARGS_MISSING_RO, rep_rw.error_codes)

        no_wait_blob = build_synthetic_fdt_blob(
            bootargs="console=ttyAMA0,115200 root=/dev/mmcblk0p7 ro init=/sbin/init"
        )
        rep_nw = audit_fdt_chosen_bootargs(no_wait_blob)
        self.assertFalse(rep_nw.passed)
        self.assertIn(ERR_BOOTARGS_MISSING_ROOTWAIT, rep_nw.error_codes)

    def test_15_bootargs_firewall_allows_all_verified_inits_and_rejects_unverified_init_rdinit(self) -> None:
        for good_init in ALLOWED_VERIFIED_INIT_PATHS:
            blob = build_synthetic_fdt_blob(
                bootargs=f"console=ttyAMA0,115200 root=/dev/mmcblk0p7 ro rootwait init={good_init}"
            )
            rep = audit_fdt_chosen_bootargs(blob)
            self.assertTrue(rep.passed, f"{good_init} failed: {rep.errors}")

        for bad_arg in ("init=/bin/sh", "init=/tmp/evil_backdoor.sh", "rdinit=/bin/ash", "init=../sbin/init"):
            blob = build_synthetic_fdt_blob(
                bootargs=f"console=ttyAMA0,115200 root=/dev/mmcblk0p7 ro rootwait {bad_arg}"
            )
            rep = audit_fdt_chosen_bootargs(blob)
            self.assertFalse(rep.passed)
            self.assertFalse(rep.init_path_verified)
            self.assertIn(ERR_BOOTARGS_UNVERIFIED_INIT_PATH, rep.error_codes)

    def test_16_bootargs_firewall_rejects_mtdparts_blkdevparts_and_mmcparts(self) -> None:
        for bad_part in (
            "mtdparts=emmc0:1m(nbl)ro,-(user)",
            "blkdevparts=mmcblk0:16M(p1),32M(p2)",
            "mmcparts=mmcblk0:4M(boot0)",
        ):
            blob = build_synthetic_fdt_blob(
                bootargs=f"console=ttyAMA0,115200 root=/dev/mmcblk0p7 ro rootwait init=/sbin/init {bad_part}"
            )
            rep = audit_fdt_chosen_bootargs(blob)
            self.assertFalse(rep.passed)
            self.assertTrue(rep.has_forbidden_repartitioning)
            self.assertIn(ERR_BOOTARGS_FORBIDDEN_REPARTITIONING, rep.error_codes)

    def test_17_bootargs_firewall_rejects_nowatchdog_and_wdt_disable_flags(self) -> None:
        for bad_wdt in ("nowatchdog", "wdt=0", "watchdog=0", "cxd90057_wdt.disable=1", "wdt.disable=1"):
            blob = build_synthetic_fdt_blob(
                bootargs=f"console=ttyAMA0,115200 root=/dev/mmcblk0p7 ro rootwait init=/sbin/init {bad_wdt}"
            )
            rep = audit_fdt_chosen_bootargs(blob)
            self.assertFalse(rep.passed)
            self.assertFalse(rep.watchdog_enabled)
            self.assertIn(ERR_BOOTARGS_WDT_DISABLED, rep.error_codes)

    def test_18_bootargs_firewall_rejects_missing_empty_malformed_and_wrong_soc(self) -> None:
        rep_no_chosen = audit_fdt_chosen_bootargs(build_synthetic_fdt_blob(include_chosen=False))
        self.assertFalse(rep_no_chosen.passed)
        self.assertIn(ERR_FDT_MISSING_CHOSEN, rep_no_chosen.error_codes)
        self.assertIn(ERR_BOOTARGS_MISSING_OR_EMPTY, rep_no_chosen.error_codes)

        rep_empty = audit_fdt_chosen_bootargs(build_synthetic_fdt_blob(bootargs="   "))
        self.assertFalse(rep_empty.passed)
        self.assertIn(ERR_BOOTARGS_MISSING_OR_EMPTY, rep_empty.error_codes)

        rep_quote = audit_fdt_chosen_bootargs(build_synthetic_fdt_blob(bootargs='root=/dev/mmcblk0p7 ro "unclosed'))
        self.assertFalse(rep_quote.passed)
        self.assertIn(ERR_BOOTARGS_MALFORMED, rep_quote.error_codes)

        rep_soc = audit_fdt_chosen_bootargs(build_synthetic_fdt_blob(model="CXD99999", compatible=("sony,other",)))
        self.assertFalse(rep_soc.passed)
        self.assertIn(ERR_FDT_SOC_MISMATCH, rep_soc.error_codes)

    def test_19_bootargs_firewall_rejects_invalid_initrd_bounds_and_cell_sizes(self) -> None:
        rep_missing = audit_fdt_chosen_bootargs(build_synthetic_fdt_blob(initrd_start=None, initrd_end=None))
        self.assertFalse(rep_missing.passed)
        self.assertIn(ERR_INITRD_MISSING, rep_missing.error_codes)

        rep_asym = audit_fdt_chosen_bootargs(build_synthetic_fdt_blob(initrd_start=CXD90057_INITRD_BASE, initrd_end=None))
        self.assertFalse(rep_asym.passed)
        self.assertIn(ERR_INITRD_ASYMMETRIC_BOUNDS, rep_asym.error_codes)

        rep_inv = audit_fdt_chosen_bootargs(
            build_synthetic_fdt_blob(initrd_start=CXD90057_INITRD_BASE + 0x1000, initrd_end=CXD90057_INITRD_BASE)
        )
        self.assertFalse(rep_inv.passed)
        self.assertIn(ERR_INITRD_INVALID_RANGE, rep_inv.error_codes)

        rep_big = audit_fdt_chosen_bootargs(
            build_synthetic_fdt_blob(
                initrd_start=CXD90057_INITRD_BASE,
                initrd_end=CXD90057_INITRD_BASE + MAX_INITRD_WINDOW_BYTES + 4096,
            )
        )
        self.assertFalse(rep_big.passed)
        self.assertIn(ERR_INITRD_SIZE_OUT_OF_BOUNDS, rep_big.error_codes)

        # Optional initrd passes when require_initrd=False
        rep_opt = audit_fdt_chosen_bootargs(
            build_synthetic_fdt_blob(initrd_start=None, initrd_end=None),
            require_initrd=False,
        )
        self.assertTrue(rep_opt.passed, rep_opt.errors)

    def test_20_bootargs_firewall_rejects_invalid_initrd_cell_byte_length(self) -> None:
        # Synthesize a 6-byte linux,initrd-start manually by mutating an 8-byte blob's FDT_PROP len (8 -> 6)
        # Keep struct aligned by replacing a valid FDT with custom 3-byte string? Simpler: test ValueError on builder
        with self.assertRaises(ValueError):
            build_synthetic_fdt_blob(initrd_cell_bytes=6)

        # Build a valid FDT where linux,initrd-start has 12 bytes by patching prop len in dt_struct from 8 to 12?
        # Instead build a small FDT with 0-byte linux,initrd-start via manual struct assembly:
        valid = bytearray(build_synthetic_fdt_blob())
        # Locate b"linux,initrd-start" offset in dt_strings -> find FDT_PROP with plen=8
        rep = parse_fdt_blob(bytes(valid))
        assert rep.header is not None
        # Verify an 0-len initrd property triggers ERR_INITRD_INVALID_CELL_SIZE
        # Find the first FDT_PROP with len==8 in dt_struct (which is linux,initrd-start):
        pos = rep.header.off_dt_struct
        end = pos + rep.header.size_dt_struct
        patched = False
        while pos + 12 <= end:
            tok = struct.unpack_from(">I", valid, pos)[0]
            if tok == FDT_PROP:
                plen, nameoff = struct.unpack_from(">II", valid, pos + 4)
                if plen == 8 and valid[rep.header.off_dt_strings + nameoff :].startswith(b"linux,initrd-start\x00"):
                    # Replace plen=8 with plen=0 AND turn the 8 value bytes into 2 FDT_NOP tokens so stream stays valid!
                    struct.pack_into(">I", valid, pos + 4, 0)
                    struct.pack_into(">II", valid, pos + 12, FDT_NOP, FDT_NOP)
                    patched = True
                    break
                pos += 12 + ((plen + 3) & ~3)
            elif tok == FDT_BEGIN_NODE:
                nul = valid.find(b"\x00", pos + 4, end)
                pos = ((nul + 1) + 3) & ~3
            else:
                pos += 4
        self.assertTrue(patched)
        rep_cell = audit_fdt_chosen_bootargs(bytes(valid))
        self.assertFalse(rep_cell.passed)
        self.assertIn(ERR_INITRD_INVALID_CELL_SIZE, rep_cell.error_codes)

    # ------------------------------------------------------------------
    # Pillar 2: ARM64 Linux Kernel Image Header & Cross-SKU Firewall
    # ------------------------------------------------------------------

    def test_21_arm64_kernel_valid_fx3_header_geometry_and_banner(self) -> None:
        img = build_synthetic_arm64_kernel_image(sku="ILME-FX3")
        rep = audit_arm64_kernel_image(img, label="fx3_stage_b_vmlinux.bin")
        self.assertTrue(rep.passed, rep.errors)
        self.assertEqual(rep.status, STATUS_VERIFIED_ARM64_KERNEL)
        self.assertEqual(rep.magic, ARM64_IMAGE_MAGIC)
        self.assertEqual(rep.magic_hex, "0x644d5241")
        self.assertEqual(rep.text_offset, EXPECTED_ARM64_TEXT_OFFSET)
        self.assertEqual(rep.image_size, EXPECTED_ARM64_IMAGE_SIZE)
        self.assertTrue(rep.is_little_endian)
        self.assertEqual(rep.page_size_code, 1)
        self.assertEqual(rep.page_size_label, "4K")
        self.assertTrue(rep.phys_placement_2mb_aligned)
        self.assertTrue(rep.reserved_flags_zero)
        self.assertEqual(rep.kernel_release, EXPECTED_FX3_KERNEL_RELEASE)
        self.assertTrue(rep.cxd90057_marker_present)
        self.assertEqual(rep.detected_sku, "ILME-FX3")
        self.assertFalse(rep.cross_sku_transplant_detected)
        self.assertFalse(rep.truncated_image)

    def test_22_arm64_kernel_rejects_cross_sku_fx6_transplant(self) -> None:
        fx6_img = build_synthetic_arm64_kernel_image(sku="ILME-FX6")
        rep = audit_arm64_kernel_image(fx6_img, label="fx6_vmlinux.bin", expected_sku="ILME-FX3")
        self.assertFalse(rep.passed)
        self.assertEqual(rep.status, STATUS_REJECTED_ARM64_KERNEL)
        self.assertEqual(rep.detected_sku, "ILME-FX6")
        self.assertTrue(rep.cross_sku_transplant_detected)
        self.assertIn(ERR_KERNEL_CROSS_SKU_FX6_TRANSPLANT, rep.error_codes)

    def test_23_arm64_kernel_rejects_bad_magic_and_zero_code0(self) -> None:
        rep_m = audit_arm64_kernel_image(build_synthetic_arm64_kernel_image(magic=0x11223344))
        self.assertFalse(rep_m.passed)
        self.assertIn(ERR_KERNEL_BAD_ARM64_MAGIC, rep_m.error_codes)

        rep_c0 = audit_arm64_kernel_image(build_synthetic_arm64_kernel_image(code0=0))
        self.assertFalse(rep_c0.passed)
        self.assertIn(ERR_KERNEL_INVALID_CODE0, rep_c0.error_codes)

    def test_24_arm64_kernel_rejects_big_endian_bad_page_size_and_reserved_flags(self) -> None:
        rep_be = audit_arm64_kernel_image(build_synthetic_arm64_kernel_image(flags=0xB))  # bit 0 = 1 (BE)
        self.assertFalse(rep_be.passed)
        self.assertFalse(rep_be.is_little_endian)
        self.assertIn(ERR_KERNEL_BIG_ENDIAN_FORBIDDEN, rep_be.error_codes)

        for bad_flags, page_lbl in ((0x8, "UNSPECIFIED"), (0xC, "16K"), (0xE, "64K")):
            rep_pg = audit_arm64_kernel_image(build_synthetic_arm64_kernel_image(flags=bad_flags))
            self.assertFalse(rep_pg.passed)
            self.assertEqual(rep_pg.page_size_label, page_lbl)
            self.assertIn(ERR_KERNEL_UNSUPPORTED_PAGE_SIZE, rep_pg.error_codes)

        rep_res = audit_arm64_kernel_image(build_synthetic_arm64_kernel_image(flags=0x10A))
        self.assertFalse(rep_res.passed)
        self.assertFalse(rep_res.reserved_flags_zero)
        self.assertIn(ERR_KERNEL_NONZERO_RESERVED_FLAGS, rep_res.error_codes)

    def test_25_arm64_kernel_rejects_bad_text_offset_and_zero_image_size(self) -> None:
        rep_off = audit_arm64_kernel_image(build_synthetic_arm64_kernel_image(text_offset=0x0))
        self.assertFalse(rep_off.passed)
        self.assertIn(ERR_KERNEL_INVALID_TEXT_OFFSET, rep_off.error_codes)

        rep_sz = audit_arm64_kernel_image(build_synthetic_arm64_kernel_image(image_size=0))
        self.assertFalse(rep_sz.passed)
        self.assertIn(ERR_KERNEL_ZERO_IMAGE_SIZE, rep_sz.error_codes)

    def test_26_arm64_kernel_rejects_truncated_header_and_truncated_payload(self) -> None:
        rep_hdr = audit_arm64_kernel_image(b"\x00" * (ARM64_IMAGE_HEADER_SIZE - 1))
        self.assertFalse(rep_hdr.passed)
        self.assertTrue(rep_hdr.truncated_image)
        self.assertIn(ERR_KERNEL_TRUNCATED_HEADER, rep_hdr.error_codes)

        small_img = build_synthetic_arm64_kernel_image(total_size_bytes=512)
        rep_pay = audit_arm64_kernel_image(small_img, min_file_bytes=4096)
        self.assertFalse(rep_pay.passed)
        self.assertTrue(rep_pay.truncated_image)
        self.assertIn(ERR_KERNEL_TRUNCATED_IMAGE, rep_pay.error_codes)

    def test_27_arm64_kernel_rejects_wrong_release_missing_soc_and_sha256_mismatch(self) -> None:
        rep_rel = audit_arm64_kernel_image(build_synthetic_arm64_kernel_image(kernel_release="5.10.0-other"))
        self.assertFalse(rep_rel.passed)
        self.assertIn(ERR_KERNEL_RELEASE_MISMATCH, rep_rel.error_codes)

        rep_soc = audit_arm64_kernel_image(build_synthetic_arm64_kernel_image(include_cxd90057_marker=False))
        self.assertFalse(rep_soc.passed)
        self.assertFalse(rep_soc.cxd90057_marker_present)
        self.assertIn(ERR_KERNEL_SOC_MISMATCH, rep_soc.error_codes)

        rep_sha = audit_arm64_kernel_image(
            build_synthetic_arm64_kernel_image(sku="ILME-FX3"),
            expected_fx3_sha256="0" * 64,
        )
        self.assertFalse(rep_sha.passed)
        self.assertIn(ERR_KERNEL_SHA256_MISMATCH, rep_sha.error_codes)

    # ------------------------------------------------------------------
    # Pillar 3: Suite Determinism, Timing, CLI & 10-Pillar Integration
    # ------------------------------------------------------------------

    def test_28_unified_suite_all_passed_flags_and_safety_invariants(self) -> None:
        rep = self.suite_report
        self.assertTrue(rep.all_passed, rep.errors)
        self.assertEqual(rep.schema, FDT_BOOTARGS_KERNEL_SCHEMA)
        self.assertEqual(rep.status, STATUS_VERIFIED_FDT_KERNEL_GATE)
        self.assertTrue(rep.stage_b_boot_gate_ready)
        self.assertEqual(len(rep.suite_sha256), 64)
        self.assertEqual(rep.otp_fuse_touches, 0)
        self.assertEqual(rep.passive_tx_bytes_emitted, 0)
        self.assertEqual(rep.physical_device_writes, 0)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.persistent_write_release)
        self.assertTrue(rep.bootargs_reject_rw_emmc_passed)
        self.assertTrue(rep.bootargs_reject_bad_init_passed)
        self.assertTrue(rep.bootargs_reject_mtdparts_passed)
        self.assertTrue(rep.bootargs_reject_blkdevparts_passed)
        self.assertTrue(rep.bootargs_reject_nowatchdog_passed)
        self.assertTrue(rep.fdt_reject_bad_magic_passed)
        self.assertTrue(rep.fdt_reject_truncated_passed)
        self.assertTrue(rep.kernel_reject_fx6_transplant_passed)
        self.assertTrue(rep.kernel_reject_bad_magic_passed)
        self.assertTrue(rep.kernel_reject_truncated_passed)
        self.assertTrue(rep.kernel_reject_wrong_release_passed)

    def test_29_clean_room_suite_runtime_and_sha256_determinism(self) -> None:
        t0 = time.monotonic()
        r1 = run_fdt_bootargs_and_kernel_suite(force_clean_room=True)
        elapsed = time.monotonic() - t0
        self.assertTrue(r1.all_passed, r1.errors)
        self.assertEqual(r1.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertLessEqual(elapsed, 1.0)
        r2 = run_fdt_bootargs_and_kernel_suite(force_clean_room=True)
        self.assertEqual(r1.suite_sha256, r2.suite_sha256)
        self.assertEqual(r1.donor_snapshot.snapshot_sha256, r2.donor_snapshot.snapshot_sha256)

    def test_30_cli_verify_fdt_bootargs_json_out_text_and_fail_rc(self) -> None:
        self._sandbox.mkdir(parents=True, exist_ok=True)
        out_dir = self._sandbox / "cli_p106_out"

        buf_json = io.StringIO()
        with (
            mock.patch.object(
                sys,
                "argv",
                ["fx3_recovery", "verify-fdt-bootargs", "--clean-room", "--json", "--out", str(out_dir)],
            ),
            redirect_stdout(buf_json),
        ):
            rc = fx3_cli.main()
        self.assertEqual(rc, 0)
        rendered = buf_json.getvalue()
        self.assertNotRegex(rendered, r'(?<![0-9A-Za-z_/.-])b[\'"]')
        parsed = json.loads(rendered)
        self.assertEqual(parsed["schema"], FDT_BOOTARGS_KERNEL_SCHEMA)
        self.assertTrue(parsed["all_passed"])
        self.assertTrue(parsed["stage_b_boot_gate_ready"])
        self.assertTrue((out_dir / "fdt-bootargs-kernel-report.json").is_file())

        buf_txt = io.StringIO()
        with mock.patch.object(sys, "argv", ["fx3_recovery", "verify-fdt-bootargs", "--clean-room"]), redirect_stdout(
            buf_txt
        ):
            rc_txt = fx3_cli.main()
        self.assertEqual(rc_txt, 0)
        self.assertIn("status=VERIFIED_FDT_BOOTARGS_AND_KERNEL_GATE", buf_txt.getvalue())
        self.assertIn("stage_b_boot_gate_ready=True", buf_txt.getvalue())
        self.assertIn("kernel_magic=0x644d5241", buf_txt.getvalue())

        failing = FdtBootargsAndKernelSuiteReport(
            **{**self.suite_report.__dict__, "all_passed": False, "status": STATUS_FAIL_FDT_KERNEL_GATE}
        )
        with mock.patch("fx3_recovery.__main__.run_fdt_bootargs_and_kernel_suite", return_value=failing):
            buf_fail = io.StringIO()
            with mock.patch.object(sys, "argv", ["fx3_recovery", "verify-fdt-bootargs", "--json"]), redirect_stdout(
                buf_fail
            ):
                rc_fail = fx3_cli.main()
            self.assertEqual(rc_fail, 2)

    def test_31_cli_verify_all_recovery_10_pillar_clean_room_json_and_text(self) -> None:
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
                    "--json",
                ],
            ),
            redirect_stdout(buf),
        ):
            rc = fx3_cli.main()
        self.assertEqual(rc, 0)
        rendered = buf.getvalue()
        self.assertNotRegex(rendered, r'(?<![0-9A-Za-z_/.-])b[\'"]')
        parsed = json.loads(rendered)
        self.assertTrue(parsed["all_passed"])
        self.assertEqual(parsed["pillar_count"], 10)
        self.assertEqual(parsed["pillars_passed"], 10)
        self.assertIn("phase94_pillar8_gpt_rpmb_rescue", parsed)
        self.assertIn("phase101_pillar9_ramdisk_emmc_health", parsed)
        self.assertIn("phase106_pillar10_fdt_bootargs_kernel", parsed)
        self.assertTrue(parsed["phase106_pillar10_fdt_bootargs_kernel"]["all_passed"])

        buf_txt = io.StringIO()
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
                ],
            ),
            redirect_stdout(buf_txt),
        ):
            rc_txt = fx3_cli.main()
        self.assertEqual(rc_txt, 0)
        self.assertIn("pillars=10/10", buf_txt.getvalue())

    def test_32_cli_verify_all_recovery_10_pillar_active_mode_and_fail_propagation(self) -> None:
        # Active mode (local donor if available, clean-room fallback if not)
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
                    "--json",
                ],
            ),
            redirect_stdout(buf),
        ):
            rc = fx3_cli.main()
        self.assertEqual(rc, 0)
        parsed = json.loads(buf.getvalue())
        self.assertTrue(parsed["all_passed"])
        self.assertEqual(parsed["pillar_count"], 10)
        self.assertEqual(parsed["pillars_passed"], 10)

        # Fail propagation when Phase 106 fails
        failing = FdtBootargsAndKernelSuiteReport(
            **{**self.suite_report.__dict__, "all_passed": False, "status": STATUS_FAIL_FDT_KERNEL_GATE}
        )
        with mock.patch("fx3_recovery.__main__.run_fdt_bootargs_and_kernel_suite", return_value=failing):
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
                        "--json",
                    ],
                ),
                redirect_stdout(buf_fail),
            ):
                rc_fail = fx3_cli.main()
            self.assertEqual(rc_fail, 2)
            parsed_fail = json.loads(buf_fail.getvalue())
            self.assertFalse(parsed_fail["all_passed"])
            self.assertEqual(parsed_fail["pillar_count"], 10)
            self.assertEqual(parsed_fail["pillars_passed"], 9)

    def test_33_cli_verify_all_recovery_default_7_pillar_compatibility_preserved(self) -> None:
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
        self.assertNotIn("phase106_pillar10_fdt_bootargs_kernel", parsed)

    def test_34_json_serialization_no_raw_bytes_and_no_nan(self) -> None:
        rendered = json.dumps(self.suite_report.to_dict(), ensure_ascii=False, sort_keys=True, allow_nan=False)
        self.assertNotRegex(rendered, r'(?<![0-9A-Za-z_/.-])b[\'"]')
        decoded = json.loads(rendered)
        self.assertEqual(decoded["suite_sha256"], self.suite_report.suite_sha256)
        self.assertEqual(decoded["otp_fuse_touches"], 0)
        self.assertEqual(decoded["passive_tx_bytes_emitted"], 0)
        self.assertEqual(decoded["physical_device_writes"], 0)
        self.assertFalse(decoded["persistent_emmc_writes_authorized"])
        self.assertFalse(decoded["persistent_write_release"])

    def test_35_fdt_rejects_trailing_garbage_and_duplicate_node_paths(self) -> None:
        valid = build_synthetic_fdt_blob()
        rep_ok = parse_fdt_blob(valid)
        assert rep_ok.header is not None
        # Add 4 bytes of non-NOP trailing garbage after FDT_END by extending dt_struct and totalsize
        end_struct = rep_ok.header.off_dt_struct + rep_ok.header.size_dt_struct
        # Build a slightly mutated blob where we insert 4 bytes at end_struct? Even simpler:
        # Append 4 bytes to end of blob and set size_dt_struct += 4 if dt_strings was before dt_struct,
        # OR swap FDT_END and trailing FDT_NOP: place FDT_END earlier and a non-NOP after it!
        # Let's build a blob with include_nop_token=True and test trailing token after FDT_END by patching:
        blob_n = bytearray(build_synthetic_fdt_blob(include_nop_token=True))
        rep_n = parse_fdt_blob(bytes(blob_n))
        assert rep_n.header is not None
        end_s = rep_n.header.off_dt_struct + rep_n.header.size_dt_struct
        # Replace final FDT_END_NODE + FDT_END (last 8 bytes of dt_struct) with FDT_END + 0x00000002?
        # Wait: stack would be non-empty. Instead put FDT_END at end_s-8 where root already ended? Root ends at end_s-8.
        # Put FDT_END at end_s-4 only; what if size_dt_struct is extended by 0? No, wait:
        # Look at where include_nop_token emits FDT_NOP: inside root node before children!
        # Let's craft minimal valid dt_struct with FDT_BEGIN_NODE "", FDT_END_NODE, FDT_END, 0x00000001:
        dt_struct = struct.pack(">IIIIII", FDT_BEGIN_NODE, 0, FDT_END_NODE, FDT_END, FDT_BEGIN_NODE, 0)
        rsv = struct.pack(">QQ", 0, 0)
        off_rsv = 40
        off_struct = off_rsv + len(rsv)
        off_str = off_struct + len(dt_struct)
        hdr = struct.pack(">10I", FDT_MAGIC, off_str, off_struct, off_str, off_rsv, 17, 16, 0, 0, len(dt_struct))
        rep_garb = parse_fdt_blob(hdr + rsv + dt_struct)
        self.assertFalse(rep_garb.valid)
        self.assertIn(ERR_FDT_MALFORMED_TOKENS, rep_garb.error_codes)

        # Duplicate /chosen node inside root
        dup_struct = struct.pack(
            ">IIIIIIIIII",
            FDT_BEGIN_NODE,
            0,
            FDT_BEGIN_NODE,
            int.from_bytes(b"dup\x00", "big"),
            FDT_END_NODE,
            FDT_BEGIN_NODE,
            int.from_bytes(b"dup\x00", "big"),
            FDT_END_NODE,
            FDT_END_NODE,
            FDT_END,
        )
        off_str2 = off_struct + len(dup_struct)
        hdr2 = struct.pack(">10I", FDT_MAGIC, off_str2, off_struct, off_str2, off_rsv, 17, 16, 0, 0, len(dup_struct))
        rep_dup = parse_fdt_blob(hdr2 + rsv + dup_struct)
        self.assertFalse(rep_dup.valid)
        self.assertIn(ERR_FDT_MALFORMED_TOKENS, rep_dup.error_codes)

    def test_36_bootargs_firewall_allows_ramdisk_rw_only_for_dev_ram0_and_rejects_untyped_rw(self) -> None:
        ram0_blob = build_synthetic_fdt_blob(
            bootargs="console=ttyAMA0,115200 root=/dev/ram0 rootfstype=squashfs rw init=/sbin/init wdt.timeout=500"
        )
        rep_ram0 = audit_fdt_chosen_bootargs(ram0_blob)
        self.assertTrue(rep_ram0.passed, rep_ram0.errors)
        self.assertFalse(rep_ram0.rootfs_is_emmc_block)

        untyped_rw = build_synthetic_fdt_blob(
            bootargs="console=ttyAMA0,115200 rw init=/sbin/init wdt.timeout=500"
        )
        rep_untyped = audit_fdt_chosen_bootargs(untyped_rw)
        self.assertFalse(rep_untyped.passed)
        self.assertIn(ERR_BOOTARGS_RW_EMMC_ROOTFS, rep_untyped.error_codes)


if __name__ == "__main__":
    unittest.main()
