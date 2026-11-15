"""Phase 138 Dual-Mode Fast Unit Tests (44 tests, <0.5s clean-room):

- Pillar 0: Hard-locked safety redlines, package exports, O_RDONLY donor inspection & clean-room fallback
- Pillar A: Reversible A7C-II-style `/dev/nflasha15` (`ext2` `/usr`) atomic Stage-B installer dry-run,
  hash-rollback engine, SD escape-hatch wrapper & `/dev/pnflasha3/8/15/23` raw-plaintext firewall
- Pillar B: `p1`/`p3` mutual-exclusion invariant, `p1:/dat2`/`dat3` preservation, `cfg.uart=1` vs FX6
  `cfg.uart=9` blackout guard & `/sbin/init` line-1 `rm -f /setting/updater/mode* && sync` verifier
- Pillar C: Tier-0 backup receipt precondition + hard-locked `persistent_emmc_writes_authorized = False`
- Master & CLI: Determinism, JSON hygiene, `verify-realhw-ext2-installer` & 16-pillar `verify-all-recovery`
"""

from __future__ import annotations

from contextlib import redirect_stdout
from dataclasses import replace
from hashlib import sha256
import io
import json
from pathlib import Path
import shutil
import sys
import time
import unittest
from unittest import mock

import fx3_recovery
from fx3_recovery import __main__ as fx3_cli
from fx3_recovery.files import is_forced_clean_room, resolve_donor_path
from fx3_recovery.realhw_ext2_installer_and_p1_rescue_verifier import (
    ALLOW_BOOT_PARTITION_TARGETING,
    ALLOW_DESTRUCTIVE_FASTBOOT,
    BLOCKED_DUAL_BOOT_PARTITION_SIMULTANEOUS_WRITE,
    BLOCKED_FX6_UART9_BLIND_BLACKOUT,
    BLOCKED_HARDWARE_EMMC_WRITE_LOCKED,
    BLOCKED_MISSING_FIRST_LINE_MODE_CLEAR_SYNC,
    BLOCKED_MISSING_SD_ESCAPE_HATCH_WRAPPER,
    BLOCKED_MISSING_TIER0_BACKUP_PRECONDITION,
    BLOCKED_P1_DAT2_MODEL_ID_CORRUPTED,
    BLOCKED_P1_DAT3_REGION_CORRUPTED,
    BLOCKED_P1_LOADADDR_INVALID,
    BLOCKED_P1_MISSING_SERIAL_CONSOLE,
    BLOCKED_RAW_PNFLASHA_PLAINTEXT_HAZARD,
    BLOCKED_READBACK_SHA256_MISMATCH_ROLLED_BACK,
    BLOCKED_SHORT_WRITE_ROLLED_BACK,
    BLOCKED_STOCK_SHA256_MISMATCH,
    BLOCKED_TIER0_READBACK_UNVERIFIED,
    DEFAULT_P1_LOADADDR_TEXT,
    ERR_EXT2_BAD_MAGIC,
    ERR_EXT2_INSUFFICIENT_HEADROOM,
    ERR_EXT2_INSUFFICIENT_INODES,
    ERR_EXT2_SLOT_OVERFLOW,
    EXT2_INSTALLER_SCENARIO_IDS,
    EXT2_MIN_HEADROOM_BYTES,
    EXT2_SUPER_MAGIC,
    FX3_EXPECTED_REGION_TAG,
    FX3_MODEL_ID_STR,
    FX3_P15_IMAGE_BYTES,
    FX6_MODEL_ID_STR,
    OTP_FUSE_TOUCHES,
    OTP_FUSE_WRITES,
    P1_RESCUE_SCENARIO_IDS,
    P1_VFAT_CAPACITY_BYTES,
    P15_EXT2_SLOT_BYTES,
    P138_DONOR_FX3_IM_ELF_RELPATH,
    P138_DONOR_FX3_MOUNT_RELPATH,
    P138_DONOR_FX3_NFLASHA15_RELPATH,
    P138_DONOR_FX3_P2_KEMCO_RELPATH,
    P138_DONOR_FX3_PARTINF_RELPATH,
    P138_DONOR_FX6_IM_ELF_RELPATH,
    P138_DONOR_FX6_MOUNT_RELPATH,
    P138_DONOR_FX6_NFLASHA15_RELPATH,
    P138_DONOR_FX6_P1_KEMCO_RELPATH,
    P138_DONOR_FX6_P1_LOADADDR_RELPATH,
    P138_DONOR_FX6_P2_KEMCO_RELPATH,
    P138_DONOR_FX6_PARTINF_RELPATH,
    P138_PINNED_FX3_IM_ELF_BYTES,
    P138_PINNED_FX3_IM_ELF_SHA256,
    P138_PINNED_FX3_MOUNT_BYTES,
    P138_PINNED_FX3_MOUNT_SHA256,
    P138_PINNED_FX3_NFLASHA15_BYTES,
    P138_PINNED_FX3_NFLASHA15_HDR4K_SHA256,
    P138_PINNED_FX3_P2_KEMCO_BYTES,
    P138_PINNED_FX3_P2_KEMCO_SHA256,
    P138_PINNED_FX3_PARTINF_BYTES,
    P138_PINNED_FX3_PARTINF_SHA256,
    P138_PINNED_FX6_IM_ELF_BYTES,
    P138_PINNED_FX6_IM_ELF_SHA256,
    P138_PINNED_FX6_MOUNT_BYTES,
    P138_PINNED_FX6_MOUNT_SHA256,
    P138_PINNED_FX6_NFLASHA15_BYTES,
    P138_PINNED_FX6_NFLASHA15_HDR4K_SHA256,
    P138_PINNED_FX6_P1_KEMCO_BYTES,
    P138_PINNED_FX6_P1_KEMCO_SHA256,
    P138_PINNED_FX6_P1_LOADADDR_BYTES,
    P138_PINNED_FX6_P1_LOADADDR_SHA256,
    P138_PINNED_FX6_P2_KEMCO_BYTES,
    P138_PINNED_FX6_P2_KEMCO_SHA256,
    P138_PINNED_FX6_PARTINF_BYTES,
    P138_PINNED_FX6_PARTINF_SHA256,
    PASSIVE_TX_BYTES_EMITTED,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHYSICAL_DEVICE_WRITES,
    READ_ONLY_DONOR_ACCESS,
    REALHW_EXT2_P1_RESCUE_SCHEMA,
    REALHW_EXT2_P1_RESCUE_VERSION,
    REQUIRED_TIER0_ARTIFACT_NAMES,
    STATUS_FAIL_REALHW_EXT2_P1_GATE,
    STATUS_REJECTED_EXT2_INSTALLER_PILLAR,
    STATUS_REJECTED_P1_RESCUE_PILLAR,
    STATUS_REJECTED_TIER0_LOCK_PILLAR,
    STATUS_ROLLED_BACK_TO_STOCK_EXACT,
    STATUS_VERIFIED_EXT2_INSTALLER_PILLAR,
    STATUS_VERIFIED_P1_RESCUE_PILLAR,
    STATUS_VERIFIED_REALHW_EXT2_P1_GATE,
    STATUS_VERIFIED_TIER0_LOCK_PILLAR,
    TIER0_LOCK_SCENARIO_IDS,
    InMemoryExt2Filesystem,
    P1OneshotRescueProposal,
    RealHwExt2InstallerAndP1RescueSuiteReport,
    Tier0BackupArtifactEntry,
    Tier0BackupReceipt,
    audit_crypto_block_device_path,
    audit_p1_oneshot_rescue_proposal,
    audit_p1_p3_mutual_exclusion,
    build_default_oneshot_p1_sbin_init,
    build_default_safe_p1_kemco_text,
    build_default_sd_escape_wrapper_script,
    build_synthetic_ext2_superblock_header,
    build_synthetic_tier0_receipt,
    inspect_realhw_ext2_and_p1_donors_readonly,
    parse_ext2_superblock_bytes,
    run_ext2_atomic_installer_6_scenario_suite,
    run_p1_rescue_and_mutual_exclusion_6_scenario_suite,
    run_realhw_ext2_installer_and_p1_rescue_suite,
    run_tier0_precondition_and_lock_4_scenario_suite,
    simulate_atomic_ext2_install_and_rollback,
    validate_sd_escape_hatch_wrapper,
    verify_tier0_backup_precondition,
)

ROOT = Path(__file__).resolve().parents[3]
RAW_BYTES_RE = r'(?<![0-9A-Za-z_/.-])b[\'\"]'


def _make_stock_bytes() -> bytes:
    return (b"\x7fELF" + b"FX3_STOCK_IM_ELF_40920B" * 1779)[:P138_PINNED_FX3_IM_ELF_BYTES]


def _make_p1_proposal(**overrides: object) -> P1OneshotRescueProposal:
    base = {
        "scenario_id": "UNIT_P1_PROPOSAL",
        "touches_p1": True,
        "touches_p3": False,
        "p1_device_path": "/dev/nflasha1",
        "p3_device_path": "/dev/cnflasha3",
        "p1_dat2_value": FX3_MODEL_ID_STR,
        "p1_dat3_value": FX3_EXPECTED_REGION_TAG,
        "p1_dat3_expected": FX3_EXPECTED_REGION_TAG,
        "p1_kemco_text": build_default_safe_p1_kemco_text(),
        "p1_loadaddr_text": DEFAULT_P1_LOADADDR_TEXT,
        "p1_payload_bytes": 16684032,
        "initrd_sbin_init_text": build_default_oneshot_p1_sbin_init(),
    }
    base.update(overrides)
    return P1OneshotRescueProposal(**base)  # type: ignore[arg-type]


class TestRealHwExt2InstallerAndP1RescueVerifier(unittest.TestCase):
    """44 dual-mode tests covering Phase 138 Pillar 16 ext2 `/dev/nflasha15` installer, p1/p3 rescue & 16-pillar gate."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.suite_report = run_realhw_ext2_installer_and_p1_rescue_suite()
        cls.clean_report = run_realhw_ext2_installer_and_p1_rescue_suite(force_clean_room=True)

    # ------------------------------------------------------------------
    # Pillar 0 — Safety Redlines, Exports & Dual-Mode Donor Inspection
    # ------------------------------------------------------------------

    def test_01_safety_redlines_hard_locked(self) -> None:
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(PERSISTENT_WRITE_RELEASE)
        self.assertFalse(ALLOW_BOOT_PARTITION_TARGETING)
        self.assertFalse(ALLOW_DESTRUCTIVE_FASTBOOT)
        self.assertTrue(READ_ONLY_DONOR_ACCESS)
        self.assertEqual(OTP_FUSE_TOUCHES, 0)
        self.assertEqual(OTP_FUSE_WRITES, 0)
        self.assertEqual(PASSIVE_TX_BYTES_EMITTED, 0)
        self.assertEqual(PHYSICAL_DEVICE_WRITES, 0)
        self.assertEqual(REALHW_EXT2_P1_RESCUE_SCHEMA, "fx3-realhw-ext2-installer-and-p1-rescue-verifier-v1")
        self.assertEqual(REALHW_EXT2_P1_RESCUE_VERSION, "1.0.0")

    def test_02_package_exports_preserve_prior_symbols_and_expose_phase138(self) -> None:
        expected_symbols = (
            "realhw_ext2_installer_and_p1_rescue_verifier",
            "run_realhw_ext2_installer_and_p1_rescue_suite",
            "inspect_realhw_ext2_and_p1_donors_readonly",
            "parse_ext2_superblock_bytes",
            "audit_crypto_block_device_path",
            "validate_sd_escape_hatch_wrapper",
            "InMemoryExt2Filesystem",
            "simulate_atomic_ext2_install_and_rollback",
            "run_ext2_atomic_installer_6_scenario_suite",
            "audit_p1_p3_mutual_exclusion",
            "audit_p1_oneshot_rescue_proposal",
            "run_p1_rescue_and_mutual_exclusion_6_scenario_suite",
            "verify_tier0_backup_precondition",
            "run_tier0_precondition_and_lock_4_scenario_suite",
            "BLOCKED_RAW_PNFLASHA_PLAINTEXT_HAZARD",
            "BLOCKED_DUAL_BOOT_PARTITION_SIMULTANEOUS_WRITE",
            "BLOCKED_FX6_UART9_BLIND_BLACKOUT",
            "BLOCKED_MISSING_FIRST_LINE_MODE_CLEAR_SYNC",
            "BLOCKED_MISSING_TIER0_BACKUP_PRECONDITION",
            "RealHwExt2InstallerAndP1RescueSuiteReport",
            "run_recovery_master_suite",
            "run_secureboot_chain_and_partition_align_suite",
        )
        for sym in expected_symbols:
            self.assertIn(sym, fx3_recovery.__all__)
            self.assertTrue(hasattr(fx3_recovery, sym), f"Missing export: {sym}")

    def test_03_clean_room_donor_snapshot_uses_pinned_anchors(self) -> None:
        snap = inspect_realhw_ext2_and_p1_donors_readonly(force_clean_room=True)
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(snap.read_only_access)
        self.assertTrue(snap.cross_sku_distinct)
        self.assertEqual(snap.fx3_p15_bytes, FX3_P15_IMAGE_BYTES)
        self.assertEqual(snap.fx6_p15_bytes, P138_PINNED_FX6_NFLASHA15_BYTES)
        self.assertEqual(snap.fx3_p15_ext2_magic_hex, "0xef53")
        self.assertEqual(snap.fx6_p15_ext2_magic_hex, "0xef53")
        self.assertGreaterEqual(snap.fx3_p15_effective_headroom_bytes, EXT2_MIN_HEADROOM_BYTES)
        self.assertEqual(snap.fx3_p2_cfg_uart, 1)
        self.assertEqual(snap.fx6_p2_cfg_uart, 9)
        self.assertEqual(snap.fx6_p1_cfg_uart, 9)
        self.assertEqual(snap.fx6_p1_loadaddr_sha256, P138_PINNED_FX6_P1_LOADADDR_SHA256)
        self.assertEqual(snap.fx3_im_elf_sha256, P138_PINNED_FX3_IM_ELF_SHA256)
        self.assertEqual(snap.fx6_im_elf_sha256, P138_PINNED_FX6_IM_ELF_SHA256)
        self.assertEqual(len(snap.artifacts), 12)
        by_label = {a.label: a for a in snap.artifacts}
        self.assertEqual(by_label["fx3_v702_partinf_conf"].sha256_digest, P138_PINNED_FX3_PARTINF_SHA256)
        self.assertEqual(by_label["fx3_v702_partinf_conf"].byte_length, P138_PINNED_FX3_PARTINF_BYTES)
        self.assertEqual(by_label["fx6_v601_partinf_conf"].sha256_digest, P138_PINNED_FX6_PARTINF_SHA256)
        self.assertEqual(by_label["fx6_v601_partinf_conf"].byte_length, P138_PINNED_FX6_PARTINF_BYTES)
        self.assertEqual(by_label["fx3_v702_mount_conf"].sha256_digest, P138_PINNED_FX3_MOUNT_SHA256)
        self.assertEqual(by_label["fx3_v702_mount_conf"].byte_length, P138_PINNED_FX3_MOUNT_BYTES)
        self.assertEqual(by_label["fx6_v601_mount_conf"].sha256_digest, P138_PINNED_FX6_MOUNT_SHA256)
        self.assertEqual(by_label["fx6_v601_mount_conf"].byte_length, P138_PINNED_FX6_MOUNT_BYTES)
        self.assertEqual(by_label["fx3_v702_p2_kemco_txt"].sha256_digest, P138_PINNED_FX3_P2_KEMCO_SHA256)
        self.assertEqual(by_label["fx3_v702_p2_kemco_txt"].byte_length, P138_PINNED_FX3_P2_KEMCO_BYTES)
        self.assertEqual(by_label["fx6_v601_p2_kemco_txt"].sha256_digest, P138_PINNED_FX6_P2_KEMCO_SHA256)
        self.assertEqual(by_label["fx6_v601_p2_kemco_txt"].byte_length, P138_PINNED_FX6_P2_KEMCO_BYTES)
        self.assertEqual(by_label["fx6_v601_p1_kemco_txt"].sha256_digest, P138_PINNED_FX6_P1_KEMCO_SHA256)
        self.assertEqual(by_label["fx6_v601_p1_kemco_txt"].byte_length, P138_PINNED_FX6_P1_KEMCO_BYTES)
        self.assertEqual(by_label["fx6_v601_p1_loadaddr_txt"].byte_length, P138_PINNED_FX6_P1_LOADADDR_BYTES)
        self.assertEqual(by_label["fx3_v702_nflasha15_ext2_hdr4k"].sha256_digest, P138_PINNED_FX3_NFLASHA15_HDR4K_SHA256)
        self.assertEqual(by_label["fx3_v702_nflasha15_ext2_hdr4k"].byte_length, P138_PINNED_FX3_NFLASHA15_BYTES)
        self.assertEqual(by_label["fx6_v601_nflasha15_ext2_hdr4k"].sha256_digest, P138_PINNED_FX6_NFLASHA15_HDR4K_SHA256)
        self.assertEqual(by_label["fx6_v601_nflasha15_ext2_hdr4k"].byte_length, P138_PINNED_FX6_NFLASHA15_BYTES)
        self.assertEqual(by_label["fx3_v702_im_elf"].byte_length, P138_PINNED_FX3_IM_ELF_BYTES)
        self.assertEqual(by_label["fx6_v601_im_elf"].byte_length, P138_PINNED_FX6_IM_ELF_BYTES)

    def test_04_active_donor_mode_o_rdonly_matches_pinned_or_falls_back(self) -> None:
        donor_paths = [
            resolve_donor_path(rel, require_file=True)
            for rel in (
                P138_DONOR_FX3_PARTINF_RELPATH,
                P138_DONOR_FX6_PARTINF_RELPATH,
                P138_DONOR_FX3_MOUNT_RELPATH,
                P138_DONOR_FX6_MOUNT_RELPATH,
                P138_DONOR_FX3_P2_KEMCO_RELPATH,
                P138_DONOR_FX6_P2_KEMCO_RELPATH,
                P138_DONOR_FX6_P1_KEMCO_RELPATH,
                P138_DONOR_FX6_P1_LOADADDR_RELPATH,
                P138_DONOR_FX3_NFLASHA15_RELPATH,
                P138_DONOR_FX6_NFLASHA15_RELPATH,
                P138_DONOR_FX3_IM_ELF_RELPATH,
                P138_DONOR_FX6_IM_ELF_RELPATH,
            )
        ]
        if (not is_forced_clean_room()) and all(p.is_file() for p in donor_paths):
            self.assertEqual(self.suite_report.verification_mode, "LOCAL_DONOR_O_RDONLY")
            live_by_label = {a.label: a for a in self.suite_report.donor_snapshot.artifacts}
            clean_by_label = {a.label: a for a in self.clean_report.donor_snapshot.artifacts}
            for label, live_art in live_by_label.items():
                self.assertEqual(live_art.source_mode, "LOCAL_DONOR_O_RDONLY")
                self.assertEqual(live_art.sha256_digest, clean_by_label[label].sha256_digest)
                self.assertEqual(live_art.byte_length, clean_by_label[label].byte_length)
        else:
            self.assertEqual(self.suite_report.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(self.suite_report.all_passed)
        self.assertTrue(self.clean_report.all_passed)

    def test_05_clean_room_fallback_does_not_open_donor_files(self) -> None:
        with mock.patch("fx3_recovery.files.os.open") as m_open:
            m_open.side_effect = OSError("sentinel stop")
            snap = inspect_realhw_ext2_and_p1_donors_readonly(force_clean_room=True)
            self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            m_open.assert_not_called()

    def test_06_clean_room_suite_completes_under_half_second(self) -> None:
        t0 = time.monotonic()
        rep = run_realhw_ext2_installer_and_p1_rescue_suite(force_clean_room=True)
        elapsed = time.monotonic() - t0
        self.assertTrue(rep.all_passed)
        self.assertLess(elapsed, 0.5)

    def test_07_absent_donor_files_automatically_fall_back_to_clean_room(self) -> None:
        missing = Path("/nonexistent/fx3-missing-phase138-dir/file.bin")
        with mock.patch(
            "fx3_recovery.realhw_ext2_installer_and_p1_rescue_verifier.resolve_donor_path",
            return_value=missing,
        ):
            snap = inspect_realhw_ext2_and_p1_donors_readonly(force_clean_room=False)
            self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertTrue(all(a.source_mode == "CLEAN_ROOM_SYNTHETIC" for a in snap.artifacts))
            self.assertTrue(snap.cross_sku_distinct)

    # ------------------------------------------------------------------
    # Pillar A — EXT2_NFLASHA15_ATOMIC_INSTALLER_AND_ROLLBACK
    # ------------------------------------------------------------------

    def test_08_parse_ext2_superblock_fx3_headroom_passes(self) -> None:
        hdr = build_synthetic_ext2_superblock_header()
        sb = parse_ext2_superblock_bytes(hdr)
        self.assertEqual(sb.s_magic, EXT2_SUPER_MAGIC)
        self.assertEqual(sb.s_magic_hex, "0xef53")
        self.assertEqual(sb.block_size_bytes, 1024)
        self.assertEqual(sb.image_bytes, FX3_P15_IMAGE_BYTES)
        self.assertEqual(sb.partition_slot_bytes, P15_EXT2_SLOT_BYTES)
        self.assertGreaterEqual(sb.effective_headroom_bytes, EXT2_MIN_HEADROOM_BYTES)
        self.assertGreaterEqual(sb.s_free_inodes_count, 256)

    def test_09_parse_ext2_superblock_rejects_bad_magic_truncated_and_overflow(self) -> None:
        with self.assertRaisesRegex(ValueError, ERR_EXT2_BAD_MAGIC):
            parse_ext2_superblock_bytes(b"\x00" * 512)
        with self.assertRaisesRegex(ValueError, ERR_EXT2_BAD_MAGIC):
            parse_ext2_superblock_bytes(build_synthetic_ext2_superblock_header(s_magic=0xDEAD))
        with self.assertRaisesRegex(ValueError, ERR_EXT2_BAD_MAGIC):
            parse_ext2_superblock_bytes(build_synthetic_ext2_superblock_header(s_log_block_size=9))
        with self.assertRaisesRegex(ValueError, ERR_EXT2_SLOT_OVERFLOW):
            parse_ext2_superblock_bytes(build_synthetic_ext2_superblock_header(s_blocks_count=600000))

    def test_10_crypto_block_device_path_enforces_transparent_crypto_and_blocks_pnflasha(self) -> None:
        for raw_enc in ("/dev/pnflasha3", "/dev/pnflasha8", "/dev/pnflasha15", "/dev/pnflasha23"):
            dec = audit_crypto_block_device_path(raw_enc)
            self.assertFalse(dec.allowed, f"Raw plaintext {raw_enc} must be hard-blocked")
            self.assertTrue(dec.is_encrypted_type5)
            self.assertFalse(dec.uses_transparent_crypto_layer)
            self.assertEqual(dec.error_code, BLOCKED_RAW_PNFLASHA_PLAINTEXT_HAZARD)

        for safe_dev in ("/dev/nflasha15", "/dev/cnflasha15", "/dev/nflasha3", "/dev/cnflasha3", "/dev/cnflasha8", "/dev/cnflasha23"):
            dec = audit_crypto_block_device_path(safe_dev)
            self.assertTrue(dec.allowed, f"Transparent crypto route {safe_dev} must pass")
            self.assertTrue(dec.is_encrypted_type5)
            self.assertTrue(dec.uses_transparent_crypto_layer)

        vfat_p1 = audit_crypto_block_device_path("/dev/pnflasha1")
        self.assertTrue(vfat_p1.allowed)
        self.assertFalse(vfat_p1.is_encrypted_type5)

        unknown = audit_crypto_block_device_path("/dev/mmcblk0p99")
        self.assertFalse(unknown.allowed)
        self.assertEqual(unknown.error_code, BLOCKED_RAW_PNFLASHA_PLAINTEXT_HAZARD)

    def test_11_sd_escape_hatch_wrapper_validation(self) -> None:
        good = build_default_sd_escape_wrapper_script()
        res_good = validate_sd_escape_hatch_wrapper(good)
        self.assertTrue(res_good.passed)
        self.assertTrue(res_good.has_shebang)
        self.assertTrue(res_good.checks_manifest_path)
        self.assertTrue(res_good.execs_orig_binary)

        for bad in (
            "exec /tmp/stageb/im_hook.elf \"$@\"\n",
            "#!/bin/sh\nexec /tmp/stageb/im_hook.elf \"$@\"\n",
            "#!/bin/sh\nif [ ! -f /mnt/sd/OTHER.TXT ]; then exec /usr/bin/im.elf.orig \"$@\"; fi\n",
            "if [ ! -f /mnt/sd/FX6_STAGEB_BOOT.MANIFEST ]; then exec /usr/bin/im.elf.orig \"$@\"; fi\n",
        ):
            res_bad = validate_sd_escape_hatch_wrapper(bad)
            self.assertFalse(res_bad.passed)
            self.assertEqual(res_bad.error_code, BLOCKED_MISSING_SD_ESCAPE_HATCH_WRAPPER)

    def test_12_in_memory_ext2_filesystem_enforces_ro_mount_discipline(self) -> None:
        fs = InMemoryExt2Filesystem(files={"/usr/bin/im.elf": b"STOCK"})
        self.assertEqual(fs.mount_mode, "ro")
        with self.assertRaises(PermissionError):
            fs.write_bytes("/usr/bin/im.elf", b"NEW")
        with self.assertRaises(PermissionError):
            fs.remove("/usr/bin/im.elf")
        fs.remount("rw")
        fs.write_bytes("/usr/bin/im.elf", b"NEW")
        self.assertEqual(fs.read_bytes("/usr/bin/im.elf"), b"NEW")
        fs.remount("ro")
        with self.assertRaises(ValueError):
            fs.remount("rw-unsafe")

    def test_13_atomic_install_succeeds_preserves_orig_and_remounts_ro(self) -> None:
        stock = _make_stock_bytes()
        stock_sha = sha256(stock).hexdigest()
        wrapper = build_default_sd_escape_wrapper_script()
        wrapper_sha = sha256(wrapper.encode("utf-8")).hexdigest()
        fs = InMemoryExt2Filesystem(device_path="/dev/cnflasha15", files={"/usr/bin/im.elf": stock})

        rep = simulate_atomic_ext2_install_and_rollback(
            fs=fs,
            expected_stock_sha256=stock_sha,
            staged_wrapper_text=wrapper,
            fault_injection="none",
            perform_clean_uninstall_rollback=False,
            scenario_id="UNIT_INSTALL_ONLY",
        )
        self.assertTrue(rep.passed, f"Install failed: {rep.errors}")
        self.assertEqual(rep.status, STATUS_VERIFIED_EXT2_INSTALLER_PILLAR)
        self.assertEqual(rep.final_target_sha256, wrapper_sha)
        self.assertEqual(rep.final_backup_sha256, stock_sha)
        self.assertTrue(rep.ro_remount_verified)
        self.assertEqual(rep.final_mount_state, "ro")
        self.assertEqual(rep.physical_device_writes, 0)
        self.assertFalse(rep.persistent_emmc_writes_authorized)

    def test_14_atomic_install_plus_clean_uninstall_restores_exact_stock_sha256(self) -> None:
        stock = _make_stock_bytes()
        stock_sha = sha256(stock).hexdigest()
        fs = InMemoryExt2Filesystem(device_path="/dev/nflasha15", files={"/usr/bin/im.elf": stock})

        rep = simulate_atomic_ext2_install_and_rollback(
            fs=fs,
            expected_stock_sha256=stock_sha,
            staged_wrapper_text=build_default_sd_escape_wrapper_script(),
            fault_injection="none",
            perform_clean_uninstall_rollback=True,
            scenario_id="UNIT_INSTALL_AND_UNINSTALL",
        )
        self.assertTrue(rep.passed)
        self.assertEqual(rep.status, STATUS_VERIFIED_EXT2_INSTALLER_PILLAR)
        self.assertEqual(rep.final_target_sha256, stock_sha)
        self.assertEqual(rep.final_backup_sha256, "")
        self.assertTrue(rep.stock_restored_exact)
        self.assertTrue(rep.ro_remount_verified)
        self.assertIn("CLEAN_UNINSTALL_FROM_ORIG", rep.phases_executed)

    def test_15_injected_bit_flip_triggers_automatic_exact_rollback_and_ro_remount(self) -> None:
        stock = _make_stock_bytes()
        stock_sha = sha256(stock).hexdigest()
        fs = InMemoryExt2Filesystem(device_path="/dev/cnflasha15", files={"/usr/bin/im.elf": stock})

        rep = simulate_atomic_ext2_install_and_rollback(
            fs=fs,
            expected_stock_sha256=stock_sha,
            staged_wrapper_text=build_default_sd_escape_wrapper_script(),
            fault_injection="bit_flip",
            scenario_id="UNIT_BIT_FLIP",
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.status, STATUS_ROLLED_BACK_TO_STOCK_EXACT)
        self.assertIn(BLOCKED_READBACK_SHA256_MISMATCH_ROLLED_BACK, rep.error_codes)
        self.assertTrue(rep.stock_restored_exact)
        self.assertEqual(rep.final_target_sha256, stock_sha)
        self.assertEqual(rep.final_backup_sha256, "")
        self.assertTrue(rep.ro_remount_verified)
        self.assertIn("ROLLBACK_FROM_ORIG", rep.phases_executed)
        self.assertIn("VERIFY_ROLLBACK_SHA256", rep.phases_executed)

    def test_16_injected_short_write_triggers_automatic_exact_rollback_and_ro_remount(self) -> None:
        stock = _make_stock_bytes()
        stock_sha = sha256(stock).hexdigest()
        fs = InMemoryExt2Filesystem(device_path="/dev/cnflasha15", files={"/usr/bin/im.elf": stock})

        rep = simulate_atomic_ext2_install_and_rollback(
            fs=fs,
            expected_stock_sha256=stock_sha,
            staged_wrapper_text=build_default_sd_escape_wrapper_script(),
            fault_injection="short_write",
            scenario_id="UNIT_SHORT_WRITE",
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.status, STATUS_ROLLED_BACK_TO_STOCK_EXACT)
        self.assertIn(BLOCKED_SHORT_WRITE_ROLLED_BACK, rep.error_codes)
        self.assertTrue(rep.stock_restored_exact)
        self.assertEqual(rep.final_target_sha256, stock_sha)
        self.assertTrue(rep.ro_remount_verified)

    def test_17_stock_sha256_mismatch_aborts_before_rw_remount(self) -> None:
        stock = _make_stock_bytes()
        wrong_expected = "f" * 64
        fs = InMemoryExt2Filesystem(device_path="/dev/cnflasha15", files={"/usr/bin/im.elf": stock})

        rep = simulate_atomic_ext2_install_and_rollback(
            fs=fs,
            expected_stock_sha256=wrong_expected,
            staged_wrapper_text=build_default_sd_escape_wrapper_script(),
            scenario_id="UNIT_STOCK_MISMATCH",
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.status, STATUS_REJECTED_EXT2_INSTALLER_PILLAR)
        self.assertIn(BLOCKED_STOCK_SHA256_MISMATCH, rep.error_codes)
        self.assertNotIn("REMOUNT_RW", rep.phases_executed)
        self.assertTrue(rep.ro_remount_verified)

    def test_18_low_ext2_headroom_and_low_free_inodes_aborted_before_rw(self) -> None:
        stock = _make_stock_bytes()
        stock_sha = sha256(stock).hexdigest()
        cramped_sb = parse_ext2_superblock_bytes(
            build_synthetic_ext2_superblock_header(
                s_blocks_count=500000,
                s_free_blocks_count=4096,
                s_free_inodes_count=64,
            )
        )
        fs = InMemoryExt2Filesystem(
            device_path="/dev/cnflasha15",
            superblock=cramped_sb,
            files={"/usr/bin/im.elf": stock},
        )
        rep = simulate_atomic_ext2_install_and_rollback(
            fs=fs,
            expected_stock_sha256=stock_sha,
            staged_wrapper_text=build_default_sd_escape_wrapper_script(),
            scenario_id="UNIT_LOW_HEADROOM",
        )
        self.assertFalse(rep.passed)
        self.assertIn(ERR_EXT2_INSUFFICIENT_HEADROOM, rep.error_codes)
        self.assertIn(ERR_EXT2_INSUFFICIENT_INODES, rep.error_codes)
        self.assertNotIn("REMOUNT_RW", rep.phases_executed)
        self.assertTrue(rep.ro_remount_verified)

    def test_19_raw_pnflasha15_blocked_before_rw_remount(self) -> None:
        stock = _make_stock_bytes()
        stock_sha = sha256(stock).hexdigest()
        fs = InMemoryExt2Filesystem(device_path="/dev/pnflasha15", files={"/usr/bin/im.elf": stock})
        rep = simulate_atomic_ext2_install_and_rollback(
            fs=fs,
            expected_stock_sha256=stock_sha,
            staged_wrapper_text=build_default_sd_escape_wrapper_script(),
            scenario_id="UNIT_RAW_PNFLASHA15",
        )
        self.assertFalse(rep.passed)
        self.assertIn(BLOCKED_RAW_PNFLASHA_PLAINTEXT_HAZARD, rep.error_codes)
        self.assertNotIn("REMOUNT_RW", rep.phases_executed)
        self.assertTrue(rep.ro_remount_verified)

    def test_20_pillar_a_6_scenario_suite_all_green(self) -> None:
        res = run_ext2_atomic_installer_6_scenario_suite()
        self.assertTrue(res.passed, f"Pillar A errors: {res.errors}")
        self.assertEqual(res.status, STATUS_VERIFIED_EXT2_INSTALLER_PILLAR)
        self.assertEqual(res.scenarios_passed, 6)
        self.assertEqual(res.scenarios_total, 6)
        self.assertEqual([r.scenario_id for r in res.scenario_results], list(EXT2_INSTALLER_SCENARIO_IDS))
        self.assertEqual(res.physical_device_writes, 0)

    # ------------------------------------------------------------------
    # Pillar B — P1_P3_MUTUAL_EXCLUSION_AND_ONESHOT_RESCUE_INITRD
    # ------------------------------------------------------------------

    def test_21_p1_p3_mutual_exclusion_matrix(self) -> None:
        d_none = audit_p1_p3_mutual_exclusion(touches_p1=False, touches_p3=False)
        self.assertTrue(d_none.allowed)
        self.assertEqual(d_none.untouched_bootable_banks, ("p1", "p3"))

        d_p1 = audit_p1_p3_mutual_exclusion(touches_p1=True, touches_p3=False)
        self.assertTrue(d_p1.allowed)
        self.assertTrue(d_p1.p3_intact)
        self.assertEqual(d_p1.untouched_bootable_banks, ("p3",))

        d_p3 = audit_p1_p3_mutual_exclusion(touches_p1=False, touches_p3=True)
        self.assertTrue(d_p3.allowed)
        self.assertTrue(d_p3.p1_intact)
        self.assertEqual(d_p3.untouched_bootable_banks, ("p1",))

        d_both = audit_p1_p3_mutual_exclusion(touches_p1=True, touches_p3=True)
        self.assertFalse(d_both.allowed)
        self.assertEqual(d_both.untouched_bootable_banks, ())
        self.assertIn(BLOCKED_DUAL_BOOT_PARTITION_SIMULTANEOUS_WRITE, d_both.error_codes)

    def test_22_healthy_p1_oneshot_rescue_proposal_passes(self) -> None:
        rep = audit_p1_oneshot_rescue_proposal(_make_p1_proposal())
        self.assertTrue(rep.passed, f"Healthy p1 rescue failed: {rep.errors}")
        self.assertEqual(rep.status, STATUS_VERIFIED_P1_RESCUE_PILLAR)
        self.assertTrue(rep.mutual_exclusion_ok)
        self.assertIn("p3", rep.untouched_bootable_banks)
        self.assertTrue(rep.dat2_preserved)
        self.assertTrue(rep.dat3_preserved)
        self.assertEqual(rep.cfg_uart, 1)
        self.assertTrue(rep.console_uart_ok)
        self.assertTrue(rep.first_line_mode_clear_sync_ok)
        self.assertTrue(rep.loadaddr_ok)
        self.assertEqual(rep.physical_device_writes, 0)
        self.assertFalse(rep.persistent_emmc_writes_authorized)

    def test_23_fx6_cfg_uart9_and_ttynull_hard_blocked(self) -> None:
        bad_kemco = build_default_safe_p1_kemco_text().replace("cfg.uart=1", "cfg.uart=9").replace(
            "console=ttyAMA0,460800n8", "console=ttynull"
        )
        rep = audit_p1_oneshot_rescue_proposal(_make_p1_proposal(p1_kemco_text=bad_kemco))
        self.assertFalse(rep.passed)
        self.assertEqual(rep.status, STATUS_REJECTED_P1_RESCUE_PILLAR)
        self.assertIn(BLOCKED_FX6_UART9_BLIND_BLACKOUT, rep.error_codes)
        self.assertIn(BLOCKED_P1_MISSING_SERIAL_CONSOLE, rep.error_codes)
        self.assertEqual(rep.cfg_uart, 9)
        self.assertFalse(rep.console_uart_ok)

    def test_24_missing_or_late_mode_clear_sync_in_sbin_init_blocked(self) -> None:
        for bad_init in (
            "#!/bin/sh\nmount -t proc proc /proc\nrm -f /setting/updater/mode* && sync\n",
            "#!/bin/sh\nrm -f /setting/updater/mode*\nsync\n",
            "#!/bin/sh\necho hi\n",
        ):
            rep = audit_p1_oneshot_rescue_proposal(_make_p1_proposal(initrd_sbin_init_text=bad_init))
            self.assertFalse(rep.passed)
            self.assertFalse(rep.first_line_mode_clear_sync_ok)
            self.assertIn(BLOCKED_MISSING_FIRST_LINE_MODE_CLEAR_SYNC, rep.error_codes)

        # Semicolon and rm -rf variants with leading comments still satisfy line-1 invariant
        alt_init = "#!/bin/sh\n# comment\nrm -rf /setting/updater/mode*; sync\nreboot -f\n"
        rep_alt = audit_p1_oneshot_rescue_proposal(_make_p1_proposal(initrd_sbin_init_text=alt_init))
        self.assertTrue(rep_alt.passed, f"Valid rm -rf; sync variant failed: {rep_alt.errors}")

    def test_25_dat2_model_id_and_dat3_region_tampering_blocked(self) -> None:
        rep = audit_p1_oneshot_rescue_proposal(
            _make_p1_proposal(p1_dat2_value=FX6_MODEL_ID_STR, p1_dat3_value="DIFFERENT_REGION")
        )
        self.assertFalse(rep.passed)
        self.assertFalse(rep.dat2_preserved)
        self.assertFalse(rep.dat3_preserved)
        self.assertIn(BLOCKED_P1_DAT2_MODEL_ID_CORRUPTED, rep.error_codes)
        self.assertIn(BLOCKED_P1_DAT3_REGION_CORRUPTED, rep.error_codes)

    def test_26_p1_loadaddr_and_23_94mib_capacity_enforced(self) -> None:
        rep_bad_addr = audit_p1_oneshot_rescue_proposal(
            _make_p1_proposal(p1_loadaddr_text="0x00000000,0x00000000")
        )
        self.assertFalse(rep_bad_addr.passed)
        self.assertFalse(rep_bad_addr.loadaddr_ok)
        self.assertIn(BLOCKED_P1_LOADADDR_INVALID, rep_bad_addr.error_codes)

        rep_overflow = audit_p1_oneshot_rescue_proposal(
            _make_p1_proposal(p1_payload_bytes=P1_VFAT_CAPACITY_BYTES + 1)
        )
        self.assertFalse(rep_overflow.passed)
        self.assertIn(BLOCKED_P1_LOADADDR_INVALID, rep_overflow.error_codes)

    def test_27_p3_only_transaction_routes_via_cnflasha3_and_blocks_pnflasha3(self) -> None:
        rep_ok = audit_p1_oneshot_rescue_proposal(
            _make_p1_proposal(touches_p1=False, touches_p3=True, p3_device_path="/dev/cnflasha3")
        )
        self.assertTrue(rep_ok.passed, f"Valid p3-only via /dev/cnflasha3 failed: {rep_ok.errors}")
        self.assertIn("p1", rep_ok.untouched_bootable_banks)

        rep_raw = audit_p1_oneshot_rescue_proposal(
            _make_p1_proposal(touches_p1=False, touches_p3=True, p3_device_path="/dev/pnflasha3")
        )
        self.assertFalse(rep_raw.passed)
        self.assertIn(BLOCKED_RAW_PNFLASHA_PLAINTEXT_HAZARD, rep_raw.error_codes)

    def test_28_pillar_b_6_scenario_suite_all_green(self) -> None:
        res = run_p1_rescue_and_mutual_exclusion_6_scenario_suite()
        self.assertTrue(res.passed, f"Pillar B errors: {res.errors}")
        self.assertEqual(res.status, STATUS_VERIFIED_P1_RESCUE_PILLAR)
        self.assertEqual(res.scenarios_passed, 6)
        self.assertEqual(res.scenarios_total, 6)
        self.assertEqual([r.scenario_id for r in res.scenario_results], list(P1_RESCUE_SCENARIO_IDS))
        self.assertEqual(res.physical_device_writes, 0)

    # ------------------------------------------------------------------
    # Pillar C — TIER0_PRECONDITION_AND_HARDWARE_WRITE_LOCK
    # ------------------------------------------------------------------

    def test_29_complete_tier0_receipt_permits_dry_run_while_locking_writes(self) -> None:
        receipt = build_synthetic_tier0_receipt()
        rep = verify_tier0_backup_precondition(receipt, scenario_id="UNIT_TIER0_OK")
        self.assertTrue(rep.passed, f"Complete Tier-0 receipt failed: {rep.errors}")
        self.assertEqual(rep.status, STATUS_VERIFIED_TIER0_LOCK_PILLAR)
        self.assertEqual(rep.present_artifacts, REQUIRED_TIER0_ARTIFACT_NAMES)
        self.assertEqual(rep.missing_artifacts, ())
        self.assertEqual(rep.unverified_artifacts, ())
        self.assertTrue(rep.tier0_complete)
        self.assertTrue(rep.dry_run_readiness_permitted)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.persistent_write_release)
        self.assertEqual(rep.physical_device_writes, 0)

    def test_30_missing_any_tier0_artifact_blocks_dry_run_readiness(self) -> None:
        for omitted in ("sector0", "p1", "p2", "p6", "p12", "p18", "spi_nor_ddrtraining"):
            rep = verify_tier0_backup_precondition(build_synthetic_tier0_receipt(omit=(omitted,)))
            self.assertFalse(rep.passed)
            self.assertEqual(rep.status, STATUS_REJECTED_TIER0_LOCK_PILLAR)
            self.assertFalse(rep.tier0_complete)
            self.assertFalse(rep.dry_run_readiness_permitted)
            self.assertIn(omitted, rep.missing_artifacts)
            self.assertIn(BLOCKED_MISSING_TIER0_BACKUP_PRECONDITION, rep.error_codes)

    def test_31_unverified_readback_or_zero_sha256_or_bad_size_blocks_readiness(self) -> None:
        rep_unver = verify_tier0_backup_precondition(build_synthetic_tier0_receipt(unverified=("p12",)))
        self.assertFalse(rep_unver.passed)
        self.assertFalse(rep_unver.dry_run_readiness_permitted)
        self.assertIn("p12", rep_unver.unverified_artifacts)
        self.assertIn(BLOCKED_TIER0_READBACK_UNVERIFIED, rep_unver.error_codes)

        # Non-O_RDONLY source_mode or truncated size also rejected
        base = build_synthetic_tier0_receipt()
        bad_arts = tuple(
            Tier0BackupArtifactEntry(a.name, 10, a.sha256_digest, True, "O_RDWR") if a.name == "sector0" else a
            for a in base.artifacts
        )
        rep_bad = verify_tier0_backup_precondition(replace(base, artifacts=bad_arts))
        self.assertFalse(rep_bad.passed)
        self.assertIn("sector0", rep_bad.unverified_artifacts)
        self.assertIn(BLOCKED_TIER0_READBACK_UNVERIFIED, rep_bad.error_codes)

    def test_32_wrong_model_id_or_invalid_body_tag_blocked(self) -> None:
        base = build_synthetic_tier0_receipt()
        rep_model = verify_tier0_backup_precondition(replace(base, model_id=FX6_MODEL_ID_STR))
        self.assertFalse(rep_model.passed)
        self.assertIn(BLOCKED_MISSING_TIER0_BACKUP_PRECONDITION, rep_model.error_codes)

        rep_tag = verify_tier0_backup_precondition(replace(base, body_id_tag="not-hex64"))
        self.assertFalse(rep_tag.passed)
        self.assertIn(BLOCKED_MISSING_TIER0_BACKUP_PRECONDITION, rep_tag.error_codes)

    def test_33_persistent_emmc_write_unlock_attempt_hard_blocked(self) -> None:
        rep = verify_tier0_backup_precondition(
            build_synthetic_tier0_receipt(persistent_emmc_writes_requested=True)
        )
        self.assertFalse(rep.passed)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.dry_run_readiness_permitted)
        self.assertIn(BLOCKED_HARDWARE_EMMC_WRITE_LOCKED, rep.error_codes)

    def test_34_pillar_c_4_scenario_suite_all_green(self) -> None:
        res = run_tier0_precondition_and_lock_4_scenario_suite()
        self.assertTrue(res.passed, f"Pillar C errors: {res.errors}")
        self.assertEqual(res.status, STATUS_VERIFIED_TIER0_LOCK_PILLAR)
        self.assertEqual(res.scenarios_passed, 4)
        self.assertEqual(res.scenarios_total, 4)
        self.assertEqual([r.scenario_id for r in res.scenario_results], list(TIER0_LOCK_SCENARIO_IDS))
        self.assertEqual(res.physical_device_writes, 0)

    # ------------------------------------------------------------------
    # Master Gate, Determinism, JSON Hygiene & CLI 16-Pillar Integration
    # ------------------------------------------------------------------

    def test_35_clean_room_suite_sha256_is_deterministic(self) -> None:
        r2 = run_realhw_ext2_installer_and_p1_rescue_suite(force_clean_room=True)
        self.assertEqual(self.clean_report.suite_sha256, r2.suite_sha256)
        self.assertEqual(
            self.clean_report.pillar_a_ext2_installer_6_scenarios.suite_sha256,
            r2.pillar_a_ext2_installer_6_scenarios.suite_sha256,
        )
        self.assertEqual(
            self.clean_report.pillar_b_p1_rescue_6_scenarios.suite_sha256,
            r2.pillar_b_p1_rescue_6_scenarios.suite_sha256,
        )
        self.assertEqual(
            self.clean_report.pillar_c_tier0_lock_4_scenarios.suite_sha256,
            r2.pillar_c_tier0_lock_4_scenarios.suite_sha256,
        )

    def test_36_json_serialization_no_raw_bytes_and_no_nan(self) -> None:
        rendered = json.dumps(self.suite_report.to_dict(), ensure_ascii=False, sort_keys=True, allow_nan=False)
        self.assertNotRegex(rendered, RAW_BYTES_RE)
        decoded = json.loads(rendered)
        self.assertEqual(decoded["suite_sha256"], self.suite_report.suite_sha256)
        self.assertEqual(decoded["physical_device_writes"], 0)
        self.assertEqual(decoded["otp_fuse_touches"], 0)
        self.assertEqual(decoded["otp_fuse_writes"], 0)
        self.assertEqual(decoded["passive_tx_bytes_emitted"], 0)
        self.assertFalse(decoded["persistent_emmc_writes_authorized"])
        self.assertFalse(decoded["persistent_write_release"])

    def test_37_cli_verify_realhw_ext2_installer_clean_room_json_and_text(self) -> None:
        buf_json = io.StringIO()
        with (
            mock.patch.object(sys, "argv", ["fx3_recovery", "verify-realhw-ext2-installer", "--clean-room", "--json"]),
            redirect_stdout(buf_json),
        ):
            rc_json = fx3_cli.main()
        self.assertEqual(rc_json, 0)
        rendered = buf_json.getvalue()
        self.assertNotRegex(rendered, RAW_BYTES_RE)
        parsed = json.loads(rendered)
        self.assertEqual(parsed["status"], STATUS_VERIFIED_REALHW_EXT2_P1_GATE)
        self.assertEqual(parsed["verification_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(parsed["physical_device_writes"], 0)
        self.assertFalse(parsed["persistent_emmc_writes_authorized"])

        buf_txt = io.StringIO()
        with (
            mock.patch.object(sys, "argv", ["fx3_recovery", "verify-realhw-ext2-installer", "--clean-room"]),
            redirect_stdout(buf_txt),
        ):
            rc_txt = fx3_cli.main()
        self.assertEqual(rc_txt, 0)
        txt = buf_txt.getvalue()
        self.assertIn(f"status={STATUS_VERIFIED_REALHW_EXT2_P1_GATE}", txt)
        self.assertIn("ext2_installer_scenarios=6/6", txt)
        self.assertIn("p1_rescue_scenarios=6/6", txt)
        self.assertIn("tier0_lock_scenarios=4/4", txt)
        self.assertIn("persistent_emmc_writes_authorized=False", txt)

    def test_38_cli_verify_realhw_ext2_installer_active_mode(self) -> None:
        buf = io.StringIO()
        with (
            mock.patch.object(sys, "argv", ["fx3_recovery", "verify-realhw-ext2-installer", "--json"]),
            redirect_stdout(buf),
        ):
            rc = fx3_cli.main()
        self.assertEqual(rc, 0)
        rendered = buf.getvalue()
        self.assertNotRegex(rendered, RAW_BYTES_RE)
        parsed = json.loads(rendered)
        self.assertTrue(parsed["all_passed"])
        self.assertIn(parsed["verification_mode"], ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"))

    def test_39_cli_verify_realhw_ext2_installer_out_writes_artifact(self) -> None:
        scratch_root = ROOT / "work" / "_tests" / "phase138_cli_out"
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
                        "verify-realhw-ext2-installer",
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
            out_file = scratch_root / "realhw-ext2-installer-p1-rescue-report.json"
            self.assertTrue(out_file.is_file())
            written = json.loads(out_file.read_text(encoding="utf-8"))
            self.assertEqual(written["status"], STATUS_VERIFIED_REALHW_EXT2_P1_GATE)
            self.assertEqual(written["physical_device_writes"], 0)
        finally:
            if scratch_root.exists():
                shutil.rmtree(scratch_root)

    def test_40_cli_verify_realhw_ext2_installer_failure_returns_exit_2(self) -> None:
        failing = RealHwExt2InstallerAndP1RescueSuiteReport(
            **{**self.clean_report.__dict__, "all_passed": False, "status": STATUS_FAIL_REALHW_EXT2_P1_GATE}
        )
        with mock.patch(
            "fx3_recovery.__main__.run_realhw_ext2_installer_and_p1_rescue_suite",
            return_value=failing,
        ):
            buf = io.StringIO()
            with (
                mock.patch.object(sys, "argv", ["fx3_recovery", "verify-realhw-ext2-installer", "--clean-room", "--json"]),
                redirect_stdout(buf),
            ):
                rc = fx3_cli.main()
            self.assertEqual(rc, 2)
            parsed = json.loads(buf.getvalue())
            self.assertFalse(parsed["all_passed"])
            self.assertEqual(parsed["status"], STATUS_FAIL_REALHW_EXT2_P1_GATE)

    def test_41_cli_verify_all_recovery_16_pillars_clean_room_and_failure_propagation(self) -> None:
        argv_16 = [
            "fx3_recovery",
            "verify-all-recovery",
            "--clean-room",
            "--with-phase94",
            "--with-phase101",
            "--with-phase106",
            "--with-phase113",
            "--with-phase119",
            "--with-phase124",
            "--with-phase126",
            "--with-phase134",
            "--with-phase138",
            "--json",
        ]
        buf = io.StringIO()
        with mock.patch.object(sys, "argv", argv_16), redirect_stdout(buf):
            rc = fx3_cli.main()
        self.assertEqual(rc, 0)
        rendered = buf.getvalue()
        self.assertNotRegex(rendered, RAW_BYTES_RE)
        parsed = json.loads(rendered)
        self.assertTrue(parsed["all_passed"])
        self.assertEqual(parsed["pillar_count"], 16)
        self.assertEqual(parsed["pillars_passed"], 16)
        self.assertIn("phase138_pillar16_realhw_ext2_installer_p1_rescue", parsed)
        self.assertEqual(
            parsed["phase138_pillar16_realhw_ext2_installer_p1_rescue"]["status"],
            STATUS_VERIFIED_REALHW_EXT2_P1_GATE,
        )

        failing = RealHwExt2InstallerAndP1RescueSuiteReport(
            **{**self.clean_report.__dict__, "all_passed": False, "status": STATUS_FAIL_REALHW_EXT2_P1_GATE}
        )
        with mock.patch(
            "fx3_recovery.__main__.run_realhw_ext2_installer_and_p1_rescue_suite",
            return_value=failing,
        ):
            buf_fail = io.StringIO()
            with mock.patch.object(sys, "argv", argv_16), redirect_stdout(buf_fail):
                rc_fail = fx3_cli.main()
            self.assertEqual(rc_fail, 2)
            parsed_fail = json.loads(buf_fail.getvalue())
            self.assertFalse(parsed_fail["all_passed"])
            self.assertEqual(parsed_fail["pillar_count"], 16)
            self.assertEqual(parsed_fail["pillars_passed"], 15)

    def test_42_cli_verify_all_recovery_16_pillars_active_mode(self) -> None:
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
                    "--with-phase124",
                    "--with-phase126",
                    "--with-phase134",
                    "--with-phase138",
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
        self.assertEqual(parsed["pillar_count"], 16)
        self.assertEqual(parsed["pillars_passed"], 16)
        self.assertIn("phase138_pillar16_realhw_ext2_installer_p1_rescue", parsed)

    def test_43_cli_verify_all_recovery_default_and_15_pillar_compat_and_text_16_pillars(self) -> None:
        buf_def = io.StringIO()
        with (
            mock.patch.object(sys, "argv", ["fx3_recovery", "verify-all-recovery", "--clean-room", "--json"]),
            redirect_stdout(buf_def),
        ):
            rc_def = fx3_cli.main()
        self.assertEqual(rc_def, 0)
        parsed_def = json.loads(buf_def.getvalue())
        self.assertEqual(parsed_def["pillar_count"], 7)
        self.assertNotIn("phase138_pillar16_realhw_ext2_installer_p1_rescue", parsed_def)

        buf_15 = io.StringIO()
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
                    "--with-phase124",
                    "--with-phase126",
                    "--with-phase134",
                    "--json",
                ],
            ),
            redirect_stdout(buf_15),
        ):
            rc_15 = fx3_cli.main()
        self.assertEqual(rc_15, 0)
        parsed_15 = json.loads(buf_15.getvalue())
        self.assertEqual(parsed_15["pillar_count"], 15)
        self.assertNotIn("phase138_pillar16_realhw_ext2_installer_p1_rescue", parsed_15)

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
                    "--with-phase113",
                    "--with-phase119",
                    "--with-phase124",
                    "--with-phase126",
                    "--with-phase134",
                    "--with-phase138",
                ],
            ),
            redirect_stdout(buf_txt),
        ):
            rc_txt = fx3_cli.main()
        self.assertEqual(rc_txt, 0)
        txt = buf_txt.getvalue()
        self.assertIn("status=VERIFIED_RECOVERY_MASTER_SUITE", txt)
        self.assertIn("pillars=16/16", txt)

    def test_44_cross_sku_failure_propagates_to_master_suite(self) -> None:
        bad_snap = replace(self.clean_report.donor_snapshot, cross_sku_distinct=False)
        with mock.patch(
            "fx3_recovery.realhw_ext2_installer_and_p1_rescue_verifier.inspect_realhw_ext2_and_p1_donors_readonly",
            return_value=bad_snap,
        ):
            rep = run_realhw_ext2_installer_and_p1_rescue_suite(force_clean_room=True)
            self.assertFalse(rep.all_passed)
            self.assertEqual(rep.status, STATUS_FAIL_REALHW_EXT2_P1_GATE)
            self.assertGreaterEqual(len(rep.errors), 1)


if __name__ == "__main__":
    unittest.main()
