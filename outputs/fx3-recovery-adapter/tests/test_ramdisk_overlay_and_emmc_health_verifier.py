"""Dual-mode unit tests for Phase 101 CXD90057 init2 SVR4 newc cpio Firewall,
JEDEC eMMC 5.1 EXT_CSD [267..269] Health Auditor, & 9-Pillar Master Suite Integration.

Passes in BOTH:
- Local Donor `O_RDONLY` mode (verifies real local donor metadata via `os.O_RDONLY | O_NOFOLLOW | O_NONBLOCK`)
- `FX3_FX6_FORCE_CLEAN_ROOM=1` mode (deterministic clean-room synthetic fixtures)
Designed for `< 0.5s` total execution time with zero binary/bytecode residue.
"""

from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import shutil
import stat
import sys
import time
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import fx3_recovery
from fx3_recovery import __main__ as fx3_cli
from fx3_recovery.emmc_dump_forensic_verifier import build_synthetic_ext_csd
from fx3_recovery.files import ROOT, is_forced_clean_room
from fx3_recovery.ramdisk_overlay_and_emmc_health_verifier import (
    ALLOW_BOOT_PARTITION_TARGETING,
    ALLOW_DESTRUCTIVE_FASTBOOT,
    CPIO_HEADER_SIZE,
    CPIO_NEWC_MAGIC_BYTES,
    ERR_CPIO_ABSOLUTE_PATH,
    ERR_CPIO_BAD_HEX_FIELD,
    ERR_CPIO_BAD_MAGIC,
    ERR_CPIO_BAD_NAMESIZE,
    ERR_CPIO_DUPLICATE_PATH,
    ERR_CPIO_EMBEDDED_NUL_IN_NAME,
    ERR_CPIO_EMPTY_OR_TRUNCATED_HEADER,
    ERR_CPIO_MISSING_TRAILER,
    ERR_CPIO_MMCBLK_SYMLINK_ESCAPE,
    ERR_CPIO_NAME_NOT_NUL_TERMINATED,
    ERR_CPIO_NONZERO_NONREG_FILESIZE,
    ERR_CPIO_NONZERO_TRAILER_SIZE,
    ERR_CPIO_PATH_TRAVERSAL,
    ERR_CPIO_SYMLINK_ESCAPE,
    ERR_CPIO_TRAILING_GARBAGE_AFTER_TRAILER,
    ERR_CPIO_TRUNCATED_PAYLOAD,
    ERR_CPIO_UNAUTHORIZED_BLK_NODE,
    ERR_CPIO_UNAUTHORIZED_CHR_NODE,
    ERR_CPIO_UNAUTHORIZED_SETUID,
    ERR_CPIO_UNSUPPORTED_FILE_TYPE,
    ERR_EMMC_LIFE_TIME_A_CRITICAL,
    ERR_EMMC_LIFE_TIME_B_CRITICAL,
    ERR_EMMC_LIFE_TIME_RESERVED,
    ERR_EMMC_LIFE_TIME_UNDEFINED,
    ERR_EMMC_PRE_EOL_RESERVED,
    ERR_EMMC_PRE_EOL_UNDEFINED,
    ERR_EMMC_PRE_EOL_URGENT,
    ERR_EMMC_PRE_EOL_WARNING,
    ERR_EXT_CSD_BAD_LENGTH,
    ERR_EXT_CSD_BOOT_POINTER_FLIPPED,
    ERR_EXT_CSD_PARTITION_ACCESS_DIRTY,
    ERR_MOUNT_EMPTY_OR_MALFORMED,
    ERR_MOUNT_MISSING_RO_NOATIME,
    ERR_MOUNT_RW_BLOCK_DEVICE,
    ERR_OVERLAY_MISSING_OR_INVALID_OPTIONS,
    ERR_OVERLAY_NO_VOLATILE_OVERLAY_MOUNT,
    ERR_OVERLAY_UPPERDIR_NOT_TMPFS,
    ERR_OVERLAY_UPPERDIR_ON_BLOCK_PATH,
    ERR_OVERLAY_WORKDIR_NOT_TMPFS,
    EXT_CSD_LIFE_TIME_EXCEEDED,
    EXT_CSD_PRE_EOL_NORMAL,
    EXT_CSD_PRE_EOL_URGENT,
    EXT_CSD_PRE_EOL_WARNING,
    FX3_STOCK_PART_CONFIG,
    OTP_FUSE_TOUCHES,
    PASSIVE_TX_BYTES_EMITTED,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHYSICAL_DEVICE_WRITES,
    RAMDISK_EMMC_HEALTH_SCHEMA,
    READ_ONLY_DONOR_ACCESS,
    STATUS_FAIL_RAMDISK_EMMC_HEALTH,
    STATUS_VERIFIED_RAMDISK_EMMC_HEALTH,
    CpioEntrySpec,
    RamdiskOverlayAndEmmcHealthSuiteReport,
    audit_cpio_ramdisk_overlay,
    audit_emmc_ext_csd_health,
    audit_ramdisk_overlay_mount_table,
    build_cpio_newc,
    build_synthetic_safe_stage_b_mount_table,
    build_synthetic_stage_b_cpio_overlay,
    inspect_ramdisk_and_emmc_donors_readonly,
    parse_cpio_newc,
    run_ramdisk_overlay_and_emmc_health_suite,
)


class RamdiskOverlayAndEmmcHealthVerifierTests(unittest.TestCase):
    suite_report: RamdiskOverlayAndEmmcHealthSuiteReport

    @classmethod
    def setUpClass(cls) -> None:
        cls.suite_report = run_ramdisk_overlay_and_emmc_health_suite()

    def setUp(self) -> None:
        self._sandbox = (
            ROOT / "outputs" / "fx3-recovery-adapter" / f".tmp-phase101-test-{os.getpid()}-{time.time_ns()}"
        )

    def tearDown(self) -> None:
        shutil.rmtree(self._sandbox, ignore_errors=True)

    # ------------------------------------------------------------------
    # Safety Redlines, Exports & Dual-Mode Donor Inspection
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
        self.assertEqual(fx3_recovery.RAMDISK_EMMC_HEALTH_SCHEMA, RAMDISK_EMMC_HEALTH_SCHEMA)
        for symbol in (
            "CpioEntrySpec",
            "CpioOverlayAuditReport",
            "EmmcHealthAuditReport",
            "MountTableIsolationReport",
            "RamdiskOverlayAndEmmcHealthSuiteReport",
            "build_cpio_newc",
            "parse_cpio_newc",
            "audit_cpio_ramdisk_overlay",
            "audit_emmc_ext_csd_health",
            "audit_ramdisk_overlay_mount_table",
            "build_synthetic_safe_stage_b_mount_table",
            "build_synthetic_stage_b_cpio_overlay",
            "inspect_ramdisk_and_emmc_donors_readonly",
            "run_ramdisk_overlay_and_emmc_health_suite",
        ):
            self.assertIn(symbol, fx3_recovery.__all__)

    def test_02_donor_inspection_dual_mode_and_readonly_sha256(self) -> None:
        snap_default = inspect_ramdisk_and_emmc_donors_readonly()
        snap_clean = inspect_ramdisk_and_emmc_donors_readonly(force_clean_room=True)

        if is_forced_clean_room():
            self.assertEqual(snap_default.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertEqual(snap_default.snapshot_sha256, snap_clean.snapshot_sha256)
        else:
            self.assertIn(snap_default.verification_mode, ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"))
        self.assertEqual(snap_clean.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(snap_default.read_only_access)
        self.assertTrue(snap_default.fx3_initrd_squashfs_ok)
        self.assertTrue(snap_default.fx3_init2_tmpfs_observed)
        self.assertTrue(snap_default.fx6_dtb_fdt_ok)
        self.assertGreaterEqual(snap_default.fx3_stock_fstab_rw_count, 1)
        self.assertEqual(len(snap_default.artifacts), 4)
        for art in snap_default.artifacts:
            self.assertTrue(art.magic_ok, f"magic check failed for {art.label}")
            self.assertEqual(len(art.sha256), 64)

    # ------------------------------------------------------------------
    # Pillar 1: SVR4 '070701' newc cpio Parser & Firewall
    # ------------------------------------------------------------------

    def test_03_valid_stage_b_cpio_overlay_and_4byte_alignment(self) -> None:
        archive = build_synthetic_stage_b_cpio_overlay()
        self.assertEqual(archive[:6], CPIO_NEWC_MAGIC_BYTES)
        parsed = parse_cpio_newc(archive)
        self.assertTrue(parsed.valid_structure)
        self.assertTrue(parsed.trailer_present)
        self.assertEqual(len(parsed.entries), 9)

        rep = audit_cpio_ramdisk_overlay(archive)
        self.assertTrue(rep.passed)
        self.assertTrue(rep.trailer_present)
        self.assertEqual(rep.block_node_count, 0)
        self.assertEqual(rep.char_node_count, 0)
        self.assertEqual(rep.setuid_count, 0)
        self.assertEqual(rep.symlink_count, 1)
        self.assertEqual(rep.regular_file_count, 3)
        self.assertEqual(rep.directory_count, 5)
        self.assertEqual(rep.physical_device_writes, 0)
        self.assertFalse(rep.persistent_emmc_writes_authorized)

    def test_04_cpio_4byte_alignment_boundary_lengths_1_to_5(self) -> None:
        # Exercise every 4-byte remainder (0, 1, 2, 3) on both name and payload
        specs = [
            CpioEntrySpec(path=name, mode=stat.S_IFREG | 0o644, payload=b"X" * plen, ino=idx)
            for idx, (name, plen) in enumerate(
                [("a", 0), ("ab", 1), ("abc", 2), ("abcd", 3), ("abcde", 4), ("abcdef", 5)],
                start=1,
            )
        ]
        blob = build_cpio_newc(specs)
        rep = audit_cpio_ramdisk_overlay(blob)
        self.assertTrue(rep.passed)
        self.assertEqual(rep.regular_file_count, 6)
        self.assertEqual([e.filesize for e in rep.entries], [0, 1, 2, 3, 4, 5])

    def test_05_cpio_rejects_dotdot_path_traversal_and_backslash(self) -> None:
        for bad_path in ("../etc/passwd", "tmp/../../etc/shadow", "tmp/stage_b/..", "tmp\\evil"):
            blob = build_cpio_newc([CpioEntrySpec(path=bad_path, mode=stat.S_IFREG | 0o644, payload=b"pwn")])
            rep = audit_cpio_ramdisk_overlay(blob)
            self.assertFalse(rep.passed, f"failed to reject traversal path: {bad_path}")
            self.assertIn(ERR_CPIO_PATH_TRAVERSAL, rep.error_codes)

    def test_06_cpio_rejects_absolute_paths_and_duplicate_normalized_paths(self) -> None:
        abs_blob = build_cpio_newc([CpioEntrySpec(path="/etc/passwd", mode=stat.S_IFREG | 0o644, payload=b"x")])
        rep_abs = audit_cpio_ramdisk_overlay(abs_blob)
        self.assertFalse(rep_abs.passed)
        self.assertIn(ERR_CPIO_ABSOLUTE_PATH, rep_abs.error_codes)

        dup_blob = build_cpio_newc(
            [
                CpioEntrySpec(path="./tmp/stage_b/cfg", mode=stat.S_IFREG | 0o644, payload=b"a", ino=1),
                CpioEntrySpec(path="tmp/stage_b/cfg", mode=stat.S_IFREG | 0o644, payload=b"b", ino=2),
            ]
        )
        rep_dup = audit_cpio_ramdisk_overlay(dup_blob)
        self.assertFalse(rep_dup.passed)
        self.assertIn(ERR_CPIO_DUPLICATE_PATH, rep_dup.error_codes)

    def test_07_cpio_rejects_mmcblk_and_nflasha_symlink_escapes(self) -> None:
        for target in (
            "/dev/mmcblk0",
            "/dev/mmcblk0p1",
            "/dev/mmcblk0boot0",
            "/dev/mmcblk0rpmb",
            "../../../dev/mmcblk0p5",
            "/dev/nflasha1",
        ):
            blob = build_cpio_newc(
                [CpioEntrySpec(path="tmp/stage_b/alias", mode=stat.S_IFLNK | 0o777, payload=target.encode("utf-8"))]
            )
            rep = audit_cpio_ramdisk_overlay(blob)
            self.assertFalse(rep.passed, f"failed to reject symlink to {target}")
            self.assertIn(ERR_CPIO_MMCBLK_SYMLINK_ESCAPE, rep.error_codes)

    def test_08_cpio_rejects_relative_root_escape_and_disallowed_abs_symlinks(self) -> None:
        rel_esc = build_cpio_newc(
            [CpioEntrySpec(path="tmp/stage_b/esc", mode=stat.S_IFLNK | 0o777, payload=b"../../../etc/shadow")]
        )
        rep_rel = audit_cpio_ramdisk_overlay(rel_esc)
        self.assertFalse(rep_rel.passed)
        self.assertIn(ERR_CPIO_SYMLINK_ESCAPE, rep_rel.error_codes)

        abs_esc = build_cpio_newc(
            [CpioEntrySpec(path="tmp/stage_b/preload", mode=stat.S_IFLNK | 0o777, payload=b"/etc/ld.so.preload")]
        )
        rep_abs = audit_cpio_ramdisk_overlay(abs_esc)
        self.assertFalse(rep_abs.passed)
        self.assertIn(ERR_CPIO_SYMLINK_ESCAPE, rep_abs.error_codes)

        # Safe allowlisted absolute symlink succeeds
        abs_ok = build_cpio_newc(
            [CpioEntrySpec(path="tmp/stage_b/bin/ash", mode=stat.S_IFLNK | 0o777, payload=b"/bin/busybox")]
        )
        rep_ok = audit_cpio_ramdisk_overlay(abs_ok)
        self.assertTrue(rep_ok.passed)

    def test_09_cpio_rejects_s_ifblk_raw_flash_and_unauthorized_s_ifchr(self) -> None:
        blk_blob = build_cpio_newc(
            [CpioEntrySpec(path="tmp/stage_b/raw_mmc", mode=stat.S_IFBLK | 0o600, rdevmajor=179, rdevminor=0)]
        )
        rep_blk = audit_cpio_ramdisk_overlay(blk_blob)
        self.assertFalse(rep_blk.passed)
        self.assertEqual(rep_blk.block_node_count, 1)
        self.assertIn(ERR_CPIO_UNAUTHORIZED_BLK_NODE, rep_blk.error_codes)

        chr_mem = build_cpio_newc(
            [CpioEntrySpec(path="tmp/stage_b/kmem", mode=stat.S_IFCHR | 0o600, rdevmajor=1, rdevminor=1)]
        )
        rep_chr = audit_cpio_ramdisk_overlay(chr_mem)
        self.assertFalse(rep_chr.passed)
        self.assertIn(ERR_CPIO_UNAUTHORIZED_CHR_NODE, rep_chr.error_codes)

        # Explicitly allowlisted dev/null (1,3) succeeds, while dev/mem (1,1) stays blocked even if named in allowlist
        chr_null = build_cpio_newc(
            [CpioEntrySpec(path="dev/null", mode=stat.S_IFCHR | 0o666, rdevmajor=1, rdevminor=3)]
        )
        rep_null = audit_cpio_ramdisk_overlay(chr_null, allowed_char_nodes=(("dev/null", 1, 3),))
        self.assertTrue(rep_null.passed)

        chr_mem_forbidden = build_cpio_newc(
            [CpioEntrySpec(path="dev/mem", mode=stat.S_IFCHR | 0o600, rdevmajor=1, rdevminor=1)]
        )
        rep_mem_blocked = audit_cpio_ramdisk_overlay(
            chr_mem_forbidden, allowed_char_nodes=(("dev/mem", 1, 1),)
        )
        self.assertFalse(rep_mem_blocked.passed)
        self.assertIn(ERR_CPIO_UNAUTHORIZED_CHR_NODE, rep_mem_blocked.error_codes)

    def test_10_cpio_rejects_unauthorized_setuid_and_setgid_root(self) -> None:
        suid_blob = build_cpio_newc(
            [CpioEntrySpec(path="tmp/stage_b/bin/escalate", mode=stat.S_IFREG | stat.S_ISUID | 0o755, payload=b"bin")]
        )
        rep_suid = audit_cpio_ramdisk_overlay(suid_blob)
        self.assertFalse(rep_suid.passed)
        self.assertEqual(rep_suid.setuid_count, 1)
        self.assertIn(ERR_CPIO_UNAUTHORIZED_SETUID, rep_suid.error_codes)

        sgid_blob = build_cpio_newc(
            [CpioEntrySpec(path="tmp/stage_b/bin/sgid0", mode=stat.S_IFREG | stat.S_ISGID | 0o755, gid=0, payload=b"bin")]
        )
        rep_sgid = audit_cpio_ramdisk_overlay(sgid_blob)
        self.assertFalse(rep_sgid.passed)
        self.assertIn(ERR_CPIO_UNAUTHORIZED_SETUID, rep_sgid.error_codes)

        # Explicit allowlist permits specific binary
        rep_allowed = audit_cpio_ramdisk_overlay(suid_blob, allowed_setuid_paths=("tmp/stage_b/bin/escalate",))
        self.assertTrue(rep_allowed.passed)

    def test_11_cpio_rejects_fifo_socket_and_nonzero_dir_filesize(self) -> None:
        fifo_blob = build_cpio_newc([CpioEntrySpec(path="tmp/stage_b/pipe", mode=stat.S_IFIFO | 0o600)])
        rep_fifo = audit_cpio_ramdisk_overlay(fifo_blob)
        self.assertFalse(rep_fifo.passed)
        self.assertIn(ERR_CPIO_UNSUPPORTED_FILE_TYPE, rep_fifo.error_codes)

        dir_payload_blob = build_cpio_newc(
            [CpioEntrySpec(path="tmp/stage_b/dir", mode=stat.S_IFDIR | 0o755, payload=b"junk")]
        )
        rep_dir = audit_cpio_ramdisk_overlay(dir_payload_blob)
        self.assertFalse(rep_dir.passed)
        self.assertIn(ERR_CPIO_NONZERO_NONREG_FILESIZE, rep_dir.error_codes)

    def test_12_cpio_rejects_missing_trailer_nonzero_trailer_and_trailing_garbage(self) -> None:
        no_tr = build_cpio_newc(
            [CpioEntrySpec(path="tmp/stage_b/file", mode=stat.S_IFREG | 0o644, payload=b"ok")],
            include_trailer=False,
        )
        rep_no_tr = audit_cpio_ramdisk_overlay(no_tr)
        self.assertFalse(rep_no_tr.passed)
        self.assertFalse(rep_no_tr.trailer_present)
        self.assertIn(ERR_CPIO_MISSING_TRAILER, rep_no_tr.error_codes)

        valid_with_garbage = build_cpio_newc(
            [CpioEntrySpec(path="tmp/stage_b/file", mode=stat.S_IFREG | 0o644, payload=b"ok")]
        ) + b"\xde\xad\xbe\xef"
        rep_garbage = audit_cpio_ramdisk_overlay(valid_with_garbage)
        self.assertFalse(rep_garbage.passed)
        self.assertIn(ERR_CPIO_TRAILING_GARBAGE_AFTER_TRAILER, rep_garbage.error_codes)

        # Construct TRAILER!!! with non-zero filesize (4 bytes)
        bad_trailer = build_cpio_newc(
            [CpioEntrySpec(path="TRAILER!!!", mode=0, payload=b"abcd")],
            include_trailer=False,
        )
        rep_nz = audit_cpio_ramdisk_overlay(bad_trailer)
        self.assertFalse(rep_nz.passed)
        self.assertIn(ERR_CPIO_NONZERO_TRAILER_SIZE, rep_nz.error_codes)

    def test_13_cpio_rejects_bad_magic_hex_namesize_nul_and_truncation(self) -> None:
        valid = build_synthetic_stage_b_cpio_overlay()
        unpadded = build_cpio_newc(
            [CpioEntrySpec(path="tmp/stage_b/ok", mode=stat.S_IFREG | 0o644, payload=b"hello_stage_b")],
            include_trailer=True,
            trailer_block_pad=0,
        )

        # Bad magic ('070702')
        bad_magic = b"070702" + valid[6:]
        rep_magic = audit_cpio_ramdisk_overlay(bad_magic)
        self.assertFalse(rep_magic.passed)
        self.assertIn(ERR_CPIO_BAD_MAGIC, rep_magic.error_codes)

        # Bad hex field
        bad_hex = valid[:6] + b"ZZZZZZZZ" + valid[14:]
        rep_hex = audit_cpio_ramdisk_overlay(bad_hex)
        self.assertFalse(rep_hex.passed)
        self.assertIn(ERR_CPIO_BAD_HEX_FIELD, rep_hex.error_codes)

        # Truncated at every stage (header, name, payload, trailer)
        for cut in (0, 50, CPIO_HEADER_SIZE + 1, len(unpadded) - 4):
            rep_cut = audit_cpio_ramdisk_overlay(unpadded[:cut])
            self.assertFalse(rep_cut.passed, f"failed to reject truncated archive at {cut}")

        # Empty/too short
        rep_short = audit_cpio_ramdisk_overlay(b"070701")
        self.assertFalse(rep_short.passed)
        self.assertIn(ERR_CPIO_EMPTY_OR_TRUNCATED_HEADER, rep_short.error_codes)

        # Bad namesize = 0
        ns0 = valid[:94] + b"00000000" + valid[102:]
        rep_ns0 = audit_cpio_ramdisk_overlay(ns0)
        self.assertFalse(rep_ns0.passed)
        self.assertIn(ERR_CPIO_BAD_NAMESIZE, rep_ns0.error_codes)

        # Missing NUL terminator & embedded NUL in name
        one = build_cpio_newc([CpioEntrySpec(path="abcd", mode=stat.S_IFREG | 0o644, payload=b"")])
        no_nul = bytearray(one)
        no_nul[CPIO_HEADER_SIZE + 4] = ord("X")
        rep_no_nul = audit_cpio_ramdisk_overlay(bytes(no_nul))
        self.assertFalse(rep_no_nul.passed)
        self.assertIn(ERR_CPIO_NAME_NOT_NUL_TERMINATED, rep_no_nul.error_codes)

        emb_nul = bytearray(one)
        emb_nul[CPIO_HEADER_SIZE + 2] = 0
        rep_emb = audit_cpio_ramdisk_overlay(bytes(emb_nul))
        self.assertFalse(rep_emb.passed)
        self.assertIn(ERR_CPIO_EMBEDDED_NUL_IN_NAME, rep_emb.error_codes)

        # Truncated payload
        one_file = build_cpio_newc([CpioEntrySpec(path="ab", mode=stat.S_IFREG | 0o644, payload=b"0123456789abcdef")])
        rep_tp = audit_cpio_ramdisk_overlay(one_file[: CPIO_HEADER_SIZE + 8])
        self.assertFalse(rep_tp.passed)
        self.assertIn(ERR_CPIO_TRUNCATED_PAYLOAD, rep_tp.error_codes)

    # ------------------------------------------------------------------
    # Pillar 2: JEDEC eMMC 5.1 EXT_CSD [267..269] & [179] Health Auditor
    # ------------------------------------------------------------------

    def test_14_ext_csd_healthy_normal_and_80pct_boundary_pass(self) -> None:
        rep1 = audit_emmc_ext_csd_health(build_synthetic_ext_csd())
        self.assertTrue(rep1.passed)
        self.assertTrue(rep1.stage_b_rehearsal_permitted)
        self.assertFalse(rep1.tier0_backup_preservation_required)
        self.assertTrue(rep1.boot_pointer_stock_intact)
        self.assertEqual(rep1.pre_eol_info_raw, EXT_CSD_PRE_EOL_NORMAL)
        self.assertEqual(rep1.part_config_raw, FX3_STOCK_PART_CONFIG)
        self.assertEqual(rep1.boot_partition_name, "BOOT0")

        # 0x08 (70%..80% wear) is the maximum safe threshold before >80% (0x09)
        rep8 = audit_emmc_ext_csd_health(build_synthetic_ext_csd(life_time_a=0x08, life_time_b=0x08))
        self.assertTrue(rep8.passed)
        self.assertTrue(rep8.stage_b_rehearsal_permitted)
        self.assertEqual(rep8.life_time_typ_a_pct_range, (70, 80))

    def test_15_ext_csd_fails_closed_on_pre_eol_warning_and_urgent(self) -> None:
        rep_warn = audit_emmc_ext_csd_health(build_synthetic_ext_csd(pre_eol_info=EXT_CSD_PRE_EOL_WARNING))
        self.assertFalse(rep_warn.passed)
        self.assertFalse(rep_warn.stage_b_rehearsal_permitted)
        self.assertTrue(rep_warn.tier0_backup_preservation_required)
        self.assertIn(ERR_EMMC_PRE_EOL_WARNING, rep_warn.error_codes)
        self.assertIn("TIER0_BACKUP", rep_warn.recommended_action)

        rep_urg = audit_emmc_ext_csd_health(build_synthetic_ext_csd(pre_eol_info=EXT_CSD_PRE_EOL_URGENT))
        self.assertFalse(rep_urg.passed)
        self.assertFalse(rep_urg.stage_b_rehearsal_permitted)
        self.assertTrue(rep_urg.tier0_backup_preservation_required)
        self.assertIn(ERR_EMMC_PRE_EOL_URGENT, rep_urg.error_codes)

    def test_16_ext_csd_fails_closed_on_lifetime_gt80_slc_mlc_and_exceeded(self) -> None:
        for val_a, val_b, expected_err in (
            (0x09, 0x03, ERR_EMMC_LIFE_TIME_A_CRITICAL),
            (0x03, 0x09, ERR_EMMC_LIFE_TIME_B_CRITICAL),
            (0x0A, 0x0A, ERR_EMMC_LIFE_TIME_A_CRITICAL),
            (EXT_CSD_LIFE_TIME_EXCEEDED, 0x05, ERR_EMMC_LIFE_TIME_A_CRITICAL),
            (0x05, EXT_CSD_LIFE_TIME_EXCEEDED, ERR_EMMC_LIFE_TIME_B_CRITICAL),
        ):
            rep = audit_emmc_ext_csd_health(build_synthetic_ext_csd(life_time_a=val_a, life_time_b=val_b))
            self.assertFalse(rep.passed)
            self.assertFalse(rep.stage_b_rehearsal_permitted)
            self.assertTrue(rep.tier0_backup_preservation_required)
            self.assertIn(expected_err, rep.error_codes)

    def test_17_ext_csd_fails_closed_on_undefined_reserved_and_bad_length(self) -> None:
        rep_short = audit_emmc_ext_csd_health(b"\x00" * 511)
        self.assertFalse(rep_short.passed)
        self.assertIn(ERR_EXT_CSD_BAD_LENGTH, rep_short.error_codes)

        rep_undef = audit_emmc_ext_csd_health(build_synthetic_ext_csd(pre_eol_info=0x00, life_time_a=0x00, life_time_b=0x00))
        self.assertFalse(rep_undef.passed)
        self.assertIn(ERR_EMMC_PRE_EOL_UNDEFINED, rep_undef.error_codes)
        self.assertIn(ERR_EMMC_LIFE_TIME_UNDEFINED, rep_undef.error_codes)

        rep_res = audit_emmc_ext_csd_health(build_synthetic_ext_csd(pre_eol_info=0x04, life_time_a=0x0C, life_time_b=0xFF))
        self.assertFalse(rep_res.passed)
        self.assertIn(ERR_EMMC_PRE_EOL_RESERVED, rep_res.error_codes)
        self.assertIn(ERR_EMMC_LIFE_TIME_RESERVED, rep_res.error_codes)

    def test_18_ext_csd_fails_closed_on_boot_partition_pointer_flip(self) -> None:
        # Flipped to BOOT1 (0x50), disabled (0x40), USER_AREA (0x78), or BOOT_ACK=0 (0x08)
        for bad_cfg in (0x50, 0x40, 0x78, 0x08, 0xC8):
            rep = audit_emmc_ext_csd_health(build_synthetic_ext_csd(part_config=bad_cfg))
            self.assertFalse(rep.passed, f"failed to reject flipped part_config=0x{bad_cfg:02x}")
            self.assertFalse(rep.boot_pointer_stock_intact)
            self.assertFalse(rep.stage_b_rehearsal_permitted)
            self.assertIn(ERR_EXT_CSD_BOOT_POINTER_FLIPPED, rep.error_codes)

        # Dirty PARTITION_ACCESS left pointed at BOOT0 (0x49) or RPMB (0x4B)
        for dirty_cfg in (0x49, 0x4A, 0x4B):
            rep_acc = audit_emmc_ext_csd_health(build_synthetic_ext_csd(part_config=dirty_cfg))
            self.assertFalse(rep_acc.passed)
            self.assertFalse(rep_acc.boot_pointer_stock_intact)
            self.assertIn(ERR_EXT_CSD_PARTITION_ACCESS_DIRTY, rep_acc.error_codes)

    # ------------------------------------------------------------------
    # Pillar 3: RAM-Only tmpfs / overlayfs Isolation Proof
    # ------------------------------------------------------------------

    def test_19_mount_table_safe_tmpfs_overlay_with_ro_noatime_and_unmounted_emmc(self) -> None:
        safe_with_ro = build_synthetic_safe_stage_b_mount_table(include_ro_emmc_mounts=True)
        rep1 = audit_ramdisk_overlay_mount_table(safe_with_ro)
        self.assertTrue(rep1.passed)
        self.assertTrue(rep1.all_upperdir_on_tmpfs)
        self.assertTrue(rep1.all_workdir_on_tmpfs)
        self.assertTrue(rep1.zero_rw_block_mounts)
        self.assertEqual(rep1.emmc_block_mounts_checked, 3)
        self.assertEqual(rep1.rw_block_mounts_found, ())

        safe_unmounted = build_synthetic_safe_stage_b_mount_table(include_ro_emmc_mounts=False)
        rep2 = audit_ramdisk_overlay_mount_table(safe_unmounted)
        self.assertTrue(rep2.passed)
        self.assertEqual(rep2.emmc_block_mounts_checked, 0)
        self.assertTrue(rep2.zero_rw_block_mounts)

    def test_20_mount_table_rejects_rw_mmcblk_and_missing_noatime(self) -> None:
        base = build_synthetic_safe_stage_b_mount_table(include_ro_emmc_mounts=True)

        rw_case = base.replace("/dev/mmcblk0p1 /mnt/p1_ro vfat ro,noatime", "/dev/mmcblk0p1 /mnt/p1_rw vfat rw,noatime")
        rep_rw = audit_ramdisk_overlay_mount_table(rw_case)
        self.assertFalse(rep_rw.passed)
        self.assertFalse(rep_rw.zero_rw_block_mounts)
        self.assertIn(ERR_MOUNT_RW_BLOCK_DEVICE, rep_rw.error_codes)

        # Sony /dev/nflasha2 rw mount (like stock fstab) must also fail Stage-B isolation
        nflasha_rw = base + "/dev/nflasha2 /setting vfat rw,noatime,sync 0 0\n"
        rep_nf = audit_ramdisk_overlay_mount_table(nflasha_rw)
        self.assertFalse(rep_nf.passed)
        self.assertIn(ERR_MOUNT_RW_BLOCK_DEVICE, rep_nf.error_codes)

        no_noatime = base.replace("/dev/mmcblk0p7 /rootfs ext2 ro,noatime,sync", "/dev/mmcblk0p7 /rootfs ext2 ro,sync")
        rep_na = audit_ramdisk_overlay_mount_table(no_noatime)
        self.assertFalse(rep_na.passed)
        self.assertIn(ERR_MOUNT_MISSING_RO_NOATIME, rep_na.error_codes)

    def test_21_mount_table_rejects_non_tmpfs_upperdir_workdir_and_malformed_specs(self) -> None:
        non_tmpfs_upper = "\n".join(
            [
                "tmpfs /tmp tmpfs rw,nosuid,nodev 0 0",
                "/dev/mmcblk0p14 /usr ext2 ro,noatime 0 0",
                "overlay /tmp/merged overlay rw,lowerdir=/usr,upperdir=/usr/upper,workdir=/tmp/work 0 0",
            ]
        )
        rep_u = audit_ramdisk_overlay_mount_table(non_tmpfs_upper)
        self.assertFalse(rep_u.passed)
        self.assertFalse(rep_u.all_upperdir_on_tmpfs)
        self.assertIn(ERR_OVERLAY_UPPERDIR_NOT_TMPFS, rep_u.error_codes)

        non_tmpfs_work = "\n".join(
            [
                "tmpfs /tmp tmpfs rw,nosuid,nodev 0 0",
                "/dev/mmcblk0p14 /usr ext2 ro,noatime 0 0",
                "overlay /tmp/merged overlay rw,lowerdir=/usr,upperdir=/tmp/upper,workdir=/usr/work 0 0",
            ]
        )
        rep_w = audit_ramdisk_overlay_mount_table(non_tmpfs_work)
        self.assertFalse(rep_w.passed)
        self.assertFalse(rep_w.all_workdir_on_tmpfs)
        self.assertIn(ERR_OVERLAY_WORKDIR_NOT_TMPFS, rep_w.error_codes)

        same_dir = "\n".join(
            [
                "tmpfs /tmp tmpfs rw,nosuid,nodev 0 0",
                "overlay /tmp/merged overlay rw,lowerdir=/usr,upperdir=/tmp/same,workdir=/tmp/same 0 0",
            ]
        )
        rep_same = audit_ramdisk_overlay_mount_table(same_dir)
        self.assertFalse(rep_same.passed)
        self.assertIn(ERR_OVERLAY_UPPERDIR_ON_BLOCK_PATH, rep_same.error_codes)

        missing_opts = "tmpfs /tmp tmpfs rw 0 0\noverlay /tmp/merged overlay rw,lowerdir=/usr 0 0\n"
        rep_opts = audit_ramdisk_overlay_mount_table(missing_opts)
        self.assertFalse(rep_opts.passed)
        self.assertIn(ERR_OVERLAY_MISSING_OR_INVALID_OPTIONS, rep_opts.error_codes)

        no_overlay = "tmpfs /tmp tmpfs rw 0 0\n/dev/mmcblk0p1 /mnt/p1 ro vfat ro,noatime 0 0\n"
        rep_no_ov = audit_ramdisk_overlay_mount_table("tmpfs /tmp tmpfs rw 0 0\n")
        self.assertFalse(rep_no_ov.passed)
        self.assertIn(ERR_OVERLAY_NO_VOLATILE_OVERLAY_MOUNT, rep_no_ov.error_codes)

        rep_empty = audit_ramdisk_overlay_mount_table("# comment only\n\n")
        self.assertFalse(rep_empty.passed)
        self.assertIn(ERR_MOUNT_EMPTY_OR_MALFORMED, rep_empty.error_codes)

        rep_malformed = audit_ramdisk_overlay_mount_table("broken_line_only_2_fields /tmp\n")
        self.assertFalse(rep_malformed.passed)
        self.assertIn(ERR_MOUNT_EMPTY_OR_MALFORMED, rep_malformed.error_codes)

    # ------------------------------------------------------------------
    # Additional Targeted Coverage & Suite / CLI / 9-Pillar Integration
    # ------------------------------------------------------------------

    def test_22_cpio_parse_entry_metadata_fields_preserved(self) -> None:
        spec = CpioEntrySpec(
            path="tmp/stage_b/script.sh",
            mode=stat.S_IFREG | 0o750,
            payload=b"echo hello\n",
            uid=0,
            gid=0,
            nlink=1,
            mtime=1700000000,
            ino=4242,
        )
        blob = build_cpio_newc([spec])
        rep = audit_cpio_ramdisk_overlay(blob)
        self.assertTrue(rep.passed)
        e = rep.entries[0]
        self.assertEqual(e.ino, 4242)
        self.assertEqual(e.mtime, 1700000000)
        self.assertEqual(e.permissions_octal, "0o0750")
        self.assertEqual(e.file_type, "REG")
        self.assertEqual(e.filesize, 11)

    def test_23_cpio_rejects_empty_symlink_target_and_forbidden_path_token(self) -> None:
        empty_lnk = build_cpio_newc([CpioEntrySpec(path="tmp/stage_b/badlnk", mode=stat.S_IFLNK | 0o777, payload=b"")])
        rep_el = audit_cpio_ramdisk_overlay(empty_lnk)
        self.assertFalse(rep_el.passed)
        self.assertIn(ERR_CPIO_SYMLINK_ESCAPE, rep_el.error_codes)

        dev_path = build_cpio_newc([CpioEntrySpec(path="dev/mmcblk0p1", mode=stat.S_IFREG | 0o644, payload=b"fake")])
        rep_dp = audit_cpio_ramdisk_overlay(dev_path)
        self.assertFalse(rep_dp.passed)
        self.assertIn(ERR_CPIO_PATH_TRAVERSAL, rep_dp.error_codes)

    def test_24_cpio_rejects_oversized_namesize_and_excessive_archive_bounds(self) -> None:
        valid = build_synthetic_stage_b_cpio_overlay()
        huge_ns = valid[:94] + b"00002000" + valid[102:]  # 0x2000 = 8192 > 4096
        rep = audit_cpio_ramdisk_overlay(huge_ns)
        self.assertFalse(rep.passed)
        self.assertIn(ERR_CPIO_BAD_NAMESIZE, rep.error_codes)

    def test_25_cpio_allows_clean_trailing_512b_nul_block_padding(self) -> None:
        blob = build_cpio_newc(
            [CpioEntrySpec(path="tmp/stage_b/x", mode=stat.S_IFREG | 0o644, payload=b"hi")],
            trailer_block_pad=512,
        )
        self.assertEqual(len(blob) % 512, 0)
        rep = audit_cpio_ramdisk_overlay(blob)
        self.assertTrue(rep.passed)
        self.assertTrue(rep.trailer_present)

    def test_26_ext_csd_custom_expected_boot_partition_and_boot_ack_check(self) -> None:
        # Stock with BOOT_ACK=0, BOOT0=1 (0x08) passes when expected_boot_ack=0
        ext = build_synthetic_ext_csd(part_config=0x08)
        rep_strict = audit_emmc_ext_csd_health(ext)
        self.assertFalse(rep_strict.passed)
        rep_custom = audit_emmc_ext_csd_health(ext, expected_boot_ack=0)
        self.assertTrue(rep_custom.passed)

    def test_27_ext_csd_lifetime_step_ranges_0x01_to_0x0b(self) -> None:
        for step in range(1, 9):
            rep = audit_emmc_ext_csd_health(build_synthetic_ext_csd(life_time_a=step, life_time_b=step))
            self.assertTrue(rep.passed, f"step {step} should pass")
            self.assertEqual(rep.life_time_typ_a_pct_range, ((step - 1) * 10, step * 10))
        for step in (0x09, 0x0A, 0x0B):
            rep = audit_emmc_ext_csd_health(build_synthetic_ext_csd(life_time_a=step, life_time_b=1))
            self.assertFalse(rep.passed, f"step 0x{step:02x} must fail closed")

    def test_28_mount_table_nested_tmpfs_longest_prefix_resolution(self) -> None:
        # /tmp is ext2 ro,noatime (bad), but /tmp/ram is tmpfs (good) -> longest prefix wins!
        mt = "\n".join(
            [
                "/dev/mmcblk0p10 /mnt/ext ext2 ro,noatime 0 0",
                "tmpfs /mnt/ext/ram tmpfs rw,nosuid,nodev 0 0",
                "overlay /mnt/ext/ram/merged overlay rw,lowerdir=/mnt/ext,upperdir=/mnt/ext/ram/up,workdir=/mnt/ext/ram/wk 0 0",
            ]
        )
        rep = audit_ramdisk_overlay_mount_table(mt)
        self.assertTrue(rep.passed)
        self.assertEqual(rep.overlay_checks[0].upperdir_backing_fstype, "tmpfs")
        self.assertEqual(rep.overlay_checks[0].workdir_backing_fstype, "tmpfs")

    def test_29_mount_table_optional_no_overlay_when_not_required(self) -> None:
        mt = "tmpfs /tmp tmpfs rw 0 0\n/dev/mmcblk0p1 /mnt/p1 vfat ro,noatime 0 0\n"
        rep = audit_ramdisk_overlay_mount_table(mt, require_overlay_entry=False)
        self.assertTrue(rep.passed)
        self.assertTrue(rep.zero_rw_block_mounts)

    def test_30_donor_fallback_when_env_forces_clean_room(self) -> None:
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            snap = inspect_ramdisk_and_emmc_donors_readonly()
            self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            rep = run_ramdisk_overlay_and_emmc_health_suite()
            self.assertTrue(rep.all_passed)
            self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_31_unified_suite_all_passed_timing_and_determinism(self) -> None:
        rep = self.suite_report
        self.assertTrue(rep.all_passed)
        self.assertEqual(rep.status, STATUS_VERIFIED_RAMDISK_EMMC_HEALTH)
        self.assertTrue(rep.stage_b_containment_ready)
        self.assertEqual(len(rep.suite_sha256), 64)
        self.assertEqual(rep.otp_fuse_touches, 0)
        self.assertEqual(rep.passive_tx_bytes_emitted, 0)
        self.assertEqual(rep.physical_device_writes, 0)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.persistent_write_release)
        self.assertTrue(rep.cpio_reject_traversal_passed)
        self.assertTrue(rep.cpio_reject_mmcblk_symlink_passed)
        self.assertTrue(rep.cpio_reject_blk_node_passed)
        self.assertTrue(rep.cpio_reject_setuid_passed)
        self.assertTrue(rep.cpio_reject_missing_trailer_passed)
        self.assertTrue(rep.cpio_reject_truncated_passed)
        self.assertTrue(rep.emmc_reject_pre_eol_warning_passed)
        self.assertTrue(rep.emmc_reject_pre_eol_urgent_passed)
        self.assertTrue(rep.emmc_reject_lifetime_gt80_passed)
        self.assertTrue(rep.emmc_reject_boot_pointer_flip_passed)
        self.assertTrue(rep.mount_reject_rw_mmcblk_passed)
        self.assertTrue(rep.mount_reject_non_tmpfs_upperdir_passed)

        t0 = time.monotonic()
        clean1 = run_ramdisk_overlay_and_emmc_health_suite(force_clean_room=True)
        elapsed = time.monotonic() - t0
        self.assertLess(elapsed, 0.5)
        clean2 = run_ramdisk_overlay_and_emmc_health_suite(force_clean_room=True)
        self.assertEqual(clean1.suite_sha256, clean2.suite_sha256)

    def test_32_cli_verify_ramdisk_emmc_health_json_text_out_and_fail_rc(self) -> None:
        self._sandbox.mkdir(parents=True, exist_ok=True)
        out_dir = self._sandbox / "cli_p101_out"

        buf_json = io.StringIO()
        with (
            mock.patch.object(
                sys,
                "argv",
                ["fx3_recovery", "verify-ramdisk-emmc-health", "--clean-room", "--json", "--out", str(out_dir)],
            ),
            redirect_stdout(buf_json),
        ):
            rc = fx3_cli.main()
        self.assertEqual(rc, 0)
        rendered = buf_json.getvalue()
        self.assertNotRegex(rendered, r'(?<![0-9A-Za-z_/.-])b[\'"]')
        parsed = json.loads(rendered)
        self.assertEqual(parsed["schema"], RAMDISK_EMMC_HEALTH_SCHEMA)
        self.assertTrue(parsed["all_passed"])
        self.assertTrue(parsed["stage_b_containment_ready"])
        self.assertTrue((out_dir / "ramdisk-emmc-health-report.json").is_file())

        buf_text = io.StringIO()
        with mock.patch.object(sys, "argv", ["fx3_recovery", "verify-ramdisk-emmc-health"]), redirect_stdout(buf_text):
            rc_txt = fx3_cli.main()
        self.assertEqual(rc_txt, 0)
        self.assertIn("status=VERIFIED_RAMDISK_OVERLAY_AND_EMMC_HEALTH", buf_text.getvalue())
        self.assertIn("stage_b_containment_ready=True", buf_text.getvalue())

        failing = RamdiskOverlayAndEmmcHealthSuiteReport(
            **{**self.suite_report.__dict__, "all_passed": False, "status": STATUS_FAIL_RAMDISK_EMMC_HEALTH}
        )
        with mock.patch("fx3_recovery.__main__.run_ramdisk_overlay_and_emmc_health_suite", return_value=failing):
            buf_fail = io.StringIO()
            with mock.patch.object(sys, "argv", ["fx3_recovery", "verify-ramdisk-emmc-health", "--json"]), redirect_stdout(buf_fail):
                rc_fail = fx3_cli.main()
            self.assertEqual(rc_fail, 2)

    def test_33_cli_verify_all_recovery_9_pillar_with_phase94_and_phase101(self) -> None:
        buf = io.StringIO()
        with (
            mock.patch.object(
                sys,
                "argv",
                ["fx3_recovery", "verify-all-recovery", "--clean-room", "--with-phase94", "--with-phase101", "--json"],
            ),
            redirect_stdout(buf),
        ):
            rc = fx3_cli.main()
        self.assertEqual(rc, 0)
        rendered = buf.getvalue()
        self.assertNotRegex(rendered, r'(?<![0-9A-Za-z_/.-])b[\'"]')
        parsed = json.loads(rendered)
        self.assertTrue(parsed["all_passed"])
        self.assertEqual(parsed["pillar_count"], 9)
        self.assertEqual(parsed["pillars_passed"], 9)
        self.assertIn("phase94_pillar8_gpt_rpmb_rescue", parsed)
        self.assertIn("phase101_pillar9_ramdisk_emmc_health", parsed)
        self.assertTrue(parsed["phase101_pillar9_ramdisk_emmc_health"]["all_passed"])

        # Also verify text mode prints pillars=9/9
        buf_txt = io.StringIO()
        with (
            mock.patch.object(
                sys,
                "argv",
                ["fx3_recovery", "verify-all-recovery", "--clean-room", "--with-phase94", "--with-phase101"],
            ),
            redirect_stdout(buf_txt),
        ):
            rc_txt = fx3_cli.main()
        self.assertEqual(rc_txt, 0)
        self.assertIn("pillars=9/9", buf_txt.getvalue())

    def test_34_cli_verify_all_recovery_with_phase101_alone_and_fail_propagation(self) -> None:
        buf = io.StringIO()
        with (
            mock.patch.object(
                sys,
                "argv",
                ["fx3_recovery", "verify-all-recovery", "--clean-room", "--with-phase101", "--json"],
            ),
            redirect_stdout(buf),
        ):
            rc = fx3_cli.main()
        self.assertEqual(rc, 0)
        parsed = json.loads(buf.getvalue())
        self.assertEqual(parsed["pillar_count"], 8)
        self.assertEqual(parsed["pillars_passed"], 8)

        failing = RamdiskOverlayAndEmmcHealthSuiteReport(
            **{**self.suite_report.__dict__, "all_passed": False, "status": STATUS_FAIL_RAMDISK_EMMC_HEALTH}
        )
        with mock.patch("fx3_recovery.__main__.run_ramdisk_overlay_and_emmc_health_suite", return_value=failing):
            buf_fail = io.StringIO()
            with (
                mock.patch.object(
                    sys,
                    "argv",
                    ["fx3_recovery", "verify-all-recovery", "--clean-room", "--with-phase94", "--with-phase101", "--json"],
                ),
                redirect_stdout(buf_fail),
            ):
                rc_fail = fx3_cli.main()
            self.assertEqual(rc_fail, 2)
            parsed_fail = json.loads(buf_fail.getvalue())
            self.assertFalse(parsed_fail["all_passed"])
            self.assertEqual(parsed_fail["pillar_count"], 9)
            self.assertEqual(parsed_fail["pillars_passed"], 8)

    def test_35_json_serialization_no_raw_bytes_and_no_nan(self) -> None:
        rendered = json.dumps(self.suite_report.to_dict(), ensure_ascii=False, sort_keys=True, allow_nan=False)
        self.assertNotRegex(rendered, r'(?<![0-9A-Za-z_/.-])b[\'"]')
        decoded = json.loads(rendered)
        self.assertEqual(decoded["suite_sha256"], self.suite_report.suite_sha256)
        self.assertEqual(decoded["otp_fuse_touches"], 0)
        self.assertEqual(decoded["passive_tx_bytes_emitted"], 0)
        self.assertEqual(decoded["physical_device_writes"], 0)
        self.assertFalse(decoded["persistent_emmc_writes_authorized"])
        self.assertFalse(decoded["persistent_write_release"])

    def test_36_cpio_symlink_intra_subdir_relative_navigation_allowed(self) -> None:
        blob = build_cpio_newc(
            [
                CpioEntrySpec(path="tmp/stage_b/bin/busybox", mode=stat.S_IFREG | 0o755, payload=b"bb", ino=1),
                CpioEntrySpec(
                    path="tmp/stage_b/usr/bin/env",
                    mode=stat.S_IFLNK | 0o777,
                    payload=b"../../bin/busybox",
                    ino=2,
                ),
            ]
        )
        rep = audit_cpio_ramdisk_overlay(blob)
        self.assertTrue(rep.passed)
        self.assertEqual(rep.symlink_count, 1)


if __name__ == "__main__":
    unittest.main()
