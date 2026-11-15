"""Phase 134 Dual-Mode Fast Unit Tests (42 tests, <0.5s clean-room):

- Pillar 0: Hard-locked safety redlines, package exports, O_RDONLY donor inspection & clean-room fallback
- Pillar A: CXD90057 IPL -> BLoader -> ARM Trusted Firmware (BL31) -> Kernel
  secure-boot chain-of-trust envelope & cross-SKU signature mismatch firewall
- Pillar B: nflasha1..nflasha20 eMMC 512B LBA / 4 KiB page / 512 KiB erase-group
  interval tree, neighbor-partition bleed & protected-partition write firewall
- Pillar C: Master determinism, JSON hygiene, CLI `verify-secureboot-partalign` &
  `verify-all-recovery --with-phase94 ... --with-phase134` (`>= 15` pillars)
"""

from __future__ import annotations

from contextlib import redirect_stdout
from dataclasses import replace
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
from fx3_recovery.secureboot_chain_and_partition_align_verifier import (
    ALLOW_BOOT_PARTITION_TARGETING,
    ALLOW_DESTRUCTIVE_FASTBOOT,
    BLOCKED_CROSS_SKU_FX6_BOOTLOADER_ON_FX3_SOC,
    BLOCKED_OTP_EFUSE_OR_SPACC_KEYSLOT_ACCESS,
    BLOCKED_UNSIGNED_OR_PATCHED_BOOT_STAGE_ON_LOCKED_SOC,
    CXD90057_SECUREBOOT_STAGES,
    EMMC_ERASE_GROUP_BYTES,
    EMMC_ERASE_GROUP_LBA_MULTIPLE,
    EMMC_PAGE_BYTES,
    EMMC_PAGE_LBA_MULTIPLE,
    EMMC_SECTOR_BYTES,
    ERR_PARTALIGN_INVALID_GEOMETRY,
    ERR_PARTALIGN_MISALIGNED_4K_PAGE,
    ERR_PARTALIGN_UNKNOWN_TARGET_PARTITION,
    ERR_SECUREBOOT_CAPACITY_OVERFLOW,
    ERR_SECUREBOOT_EPOCH_ROLLBACK,
    ERR_SECUREBOOT_STAGE_B_MODIFIED_BOOTSTAGE,
    ERR_SECUREBOOT_STAGE_ORDER_OR_MISSING,
    FX3_SOC_MODEL_ID,
    FX3_SOC_SKU_CODE,
    FX6_SOC_MODEL_ID,
    FX6_SOC_SKU_CODE,
    OTP_FUSE_TOUCHES,
    OTP_FUSE_WRITES,
    PARTALIGN_FIREWALL_SCENARIO_IDS,
    PARTITION_LBA_OVERLAP_DETECTED,
    PASSIVE_TX_BYTES_EMITTED,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHYSICAL_DEVICE_WRITES,
    PROTECTED_EMMC_PARTITIONS,
    PROTECTED_PARTITION_WRITE_ATTEMPT_BLOCKED,
    READ_ONLY_DONOR_ACCESS,
    SBPA_DONOR_FX3_LOADER_NOR_BIN_RELPATH,
    SBPA_DONOR_FX3_PARTINF_CONF_RELPATH,
    SBPA_DONOR_FX3_VMLINUX_RELPATH,
    SBPA_DONOR_FX6_LOADER_NOR_TAR_RELPATH,
    SBPA_DONOR_FX6_PARTINF_CONF_RELPATH,
    SBPA_DONOR_FX6_VMLINUX_RELPATH,
    SBPA_PINNED_FX3_LOADER_NOR_BIN_BYTES,
    SBPA_PINNED_FX3_LOADER_NOR_BIN_SHA256,
    SBPA_PINNED_FX3_PARTINF_CONF_BYTES,
    SBPA_PINNED_FX3_PARTINF_CONF_SHA256,
    SBPA_PINNED_FX3_VMLINUX_BYTES,
    SBPA_PINNED_FX3_VMLINUX_SHA256,
    SBPA_PINNED_FX6_LOADER_NOR_BIN_BYTES,
    SBPA_PINNED_FX6_LOADER_NOR_BIN_SHA256,
    SBPA_PINNED_FX6_PARTINF_CONF_BYTES,
    SBPA_PINNED_FX6_PARTINF_CONF_SHA256,
    SBPA_PINNED_FX6_VMLINUX_BYTES,
    SBPA_PINNED_FX6_VMLINUX_SHA256,
    SECUREBOOT_FIREWALL_SCENARIO_IDS,
    SECUREBOOT_PARTALIGN_SCHEMA,
    SECUREBOOT_PARTALIGN_VERSION,
    SECUREBOOT_TARGET_EMMC_LOCKED_SOC,
    SECUREBOOT_TARGET_STAGE_B_BIND_MOUNT,
    SECUREBOOT_TARGET_STAGE_B_QEMU_OVERLAY,
    SPACC_KEY_READS,
    STATUS_FAIL_SECUREBOOT_PARTALIGN_GATE,
    STATUS_REJECTED_PARTITION_ALIGN_FIREWALL,
    STATUS_REJECTED_SECUREBOOT_FIREWALL,
    STATUS_VERIFIED_PARTITION_ALIGN_FIREWALL,
    STATUS_VERIFIED_SECUREBOOT_ENVELOPE,
    STATUS_VERIFIED_SECUREBOOT_PARTALIGN_GATE,
    STATUS_VERIFIED_STAGE_B_UNTOUCHED_BOOTCHAIN,
    UNALIGNED_ERASE_GROUP_BLEED_HAZARD,
    EmmcFlashOrEraseOp,
    EmmcPartitionEntry,
    LbaIntervalTree,
    SecurebootChainAndPartitionAlignSuiteReport,
    audit_otp_efuse_and_spacc_operation,
    build_synthetic_fx3_nflasha_partition_map,
    build_synthetic_secureboot_chain_manifest,
    find_partition_lba_overlaps,
    inspect_secureboot_and_partalign_donors_readonly,
    run_partition_align_6_scenario_firewall,
    run_secureboot_chain_and_partition_align_suite,
    run_secureboot_envelope_6_scenario_firewall,
    verify_cxd90057_secureboot_envelope,
    verify_partition_map_and_flash_ops,
)

ROOT = Path(__file__).resolve().parents[3]
RAW_BYTES_RE = r'(?<![0-9A-Za-z_/.-])b[\'\"]'


class TestSecurebootChainAndPartitionAlignVerifier(unittest.TestCase):
    """42 dual-mode tests covering Phase 134 CXD90057 secure-boot envelope, partition-align firewall & >=15-pillar gate."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.suite_report = run_secureboot_chain_and_partition_align_suite()
        cls.clean_report = run_secureboot_chain_and_partition_align_suite(force_clean_room=True)

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
        self.assertEqual(SPACC_KEY_READS, 0)
        self.assertEqual(PASSIVE_TX_BYTES_EMITTED, 0)
        self.assertEqual(PHYSICAL_DEVICE_WRITES, 0)
        self.assertEqual(SECUREBOOT_PARTALIGN_SCHEMA, "fx3-secureboot-chain-and-partition-align-verifier-v1")
        self.assertEqual(SECUREBOOT_PARTALIGN_VERSION, "1.0.0")

    def test_02_package_exports_preserve_prior_symbols_and_expose_phase134(self) -> None:
        expected_symbols = (
            "secureboot_chain_and_partition_align_verifier",
            "run_secureboot_chain_and_partition_align_suite",
            "run_secureboot_envelope_6_scenario_firewall",
            "run_partition_align_6_scenario_firewall",
            "inspect_secureboot_and_partalign_donors_readonly",
            "audit_otp_efuse_and_spacc_operation",
            "verify_cxd90057_secureboot_envelope",
            "verify_partition_map_and_flash_ops",
            "find_partition_lba_overlaps",
            "LbaIntervalTree",
            "BLOCKED_UNSIGNED_OR_PATCHED_BOOT_STAGE_ON_LOCKED_SOC",
            "BLOCKED_CROSS_SKU_FX6_BOOTLOADER_ON_FX3_SOC",
            "BLOCKED_OTP_EFUSE_OR_SPACC_KEYSLOT_ACCESS",
            "PARTITION_LBA_OVERLAP_DETECTED",
            "UNALIGNED_ERASE_GROUP_BLEED_HAZARD",
            "PROTECTED_PARTITION_WRITE_ATTEMPT_BLOCKED",
            "OTP_FUSE_WRITES",
            "SPACC_KEY_READS",
            "SecurebootChainAndPartitionAlignSuiteReport",
            "run_recovery_master_suite",
            "run_factory_cal_ibis_defectpixel_and_nvs_suite",
        )
        for sym in expected_symbols:
            self.assertIn(sym, fx3_recovery.__all__)
            self.assertTrue(hasattr(fx3_recovery, sym), f"Missing export: {sym}")

    def test_03_clean_room_donor_snapshot_uses_pinned_anchors(self) -> None:
        snap = inspect_secureboot_and_partalign_donors_readonly(force_clean_room=True)
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(snap.read_only_access)
        self.assertTrue(snap.cross_sku_distinct)
        self.assertEqual(snap.fx3_loader_nor_sha256, SBPA_PINNED_FX3_LOADER_NOR_BIN_SHA256)
        self.assertEqual(snap.fx6_loader_nor_sha256, SBPA_PINNED_FX6_LOADER_NOR_BIN_SHA256)
        self.assertEqual(snap.fx3_partinf_sha256, SBPA_PINNED_FX3_PARTINF_CONF_SHA256)
        self.assertEqual(snap.fx6_partinf_sha256, SBPA_PINNED_FX6_PARTINF_CONF_SHA256)
        self.assertEqual(snap.fx3_vmlinux_sha256, SBPA_PINNED_FX3_VMLINUX_SHA256)
        self.assertEqual(snap.fx6_vmlinux_sha256, SBPA_PINNED_FX6_VMLINUX_SHA256)
        self.assertEqual(snap.fx3_lensdata_start_lba, 0x0031C000)
        self.assertEqual(snap.fx6_lensdata_start_lba, 0x00312000)
        self.assertEqual(len(snap.artifacts), 6)
        by_label = {a.label: a for a in snap.artifacts}
        self.assertEqual(by_label["fx3_v702_loader_nor_bin"].byte_length, SBPA_PINNED_FX3_LOADER_NOR_BIN_BYTES)
        self.assertEqual(by_label["fx6_v601_loader_nor_bin"].byte_length, SBPA_PINNED_FX6_LOADER_NOR_BIN_BYTES)
        self.assertEqual(by_label["fx3_v702_partinf_conf"].byte_length, SBPA_PINNED_FX3_PARTINF_CONF_BYTES)
        self.assertEqual(by_label["fx6_v601_partinf_conf"].byte_length, SBPA_PINNED_FX6_PARTINF_CONF_BYTES)
        self.assertEqual(by_label["fx3_v702_vmlinux_bin"].byte_length, SBPA_PINNED_FX3_VMLINUX_BYTES)
        self.assertEqual(by_label["fx6_v601_vmlinux_bin"].byte_length, SBPA_PINNED_FX6_VMLINUX_BYTES)

    def test_04_active_donor_mode_o_rdonly_matches_pinned_or_falls_back(self) -> None:
        donor_paths = [
            resolve_donor_path(rel, require_file=True)
            for rel in (
                SBPA_DONOR_FX3_LOADER_NOR_BIN_RELPATH,
                SBPA_DONOR_FX6_LOADER_NOR_TAR_RELPATH,
                SBPA_DONOR_FX3_PARTINF_CONF_RELPATH,
                SBPA_DONOR_FX6_PARTINF_CONF_RELPATH,
                SBPA_DONOR_FX3_VMLINUX_RELPATH,
                SBPA_DONOR_FX6_VMLINUX_RELPATH,
            )
        ]
        if (not is_forced_clean_room()) and all(p.is_file() for p in donor_paths):
            self.assertEqual(self.suite_report.verification_mode, "LOCAL_DONOR_O_RDONLY")
            self.assertEqual(
                self.suite_report.donor_snapshot.fx3_loader_nor_sha256,
                self.clean_report.donor_snapshot.fx3_loader_nor_sha256,
            )
            self.assertEqual(
                self.suite_report.donor_snapshot.fx6_loader_nor_sha256,
                self.clean_report.donor_snapshot.fx6_loader_nor_sha256,
            )
            self.assertEqual(
                self.suite_report.donor_snapshot.fx3_partinf_sha256,
                self.clean_report.donor_snapshot.fx3_partinf_sha256,
            )
            self.assertEqual(
                self.suite_report.donor_snapshot.fx6_vmlinux_sha256,
                self.clean_report.donor_snapshot.fx6_vmlinux_sha256,
            )
            self.assertTrue(all(a.inspected for a in self.suite_report.donor_snapshot.artifacts))
        else:
            self.assertEqual(self.suite_report.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(self.suite_report.all_passed)
        self.assertTrue(self.clean_report.all_passed)

    def test_05_clean_room_fallback_does_not_open_donor_files(self) -> None:
        with mock.patch("fx3_recovery.files.os.open") as m_open:
            m_open.side_effect = OSError("sentinel stop")
            snap = inspect_secureboot_and_partalign_donors_readonly(force_clean_room=True)
            self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            m_open.assert_not_called()

    def test_06_clean_room_suite_completes_under_half_second(self) -> None:
        t0 = time.monotonic()
        rep = run_secureboot_chain_and_partition_align_suite(force_clean_room=True)
        elapsed = time.monotonic() - t0
        self.assertTrue(rep.all_passed)
        self.assertLess(elapsed, 0.5)

    def test_07_absent_donor_files_automatically_fall_back_to_clean_room(self) -> None:
        missing = Path("/nonexistent/fx3-missing-donor-dir/file.bin")
        with mock.patch(
            "fx3_recovery.secureboot_chain_and_partition_align_verifier.resolve_donor_path",
            return_value=missing,
        ):
            snap = inspect_secureboot_and_partalign_donors_readonly(force_clean_room=False)
            self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertTrue(all(not a.inspected for a in snap.artifacts))
            self.assertTrue(snap.cross_sku_distinct)

    # ------------------------------------------------------------------
    # Pillar A — CXD90057 IPL -> BLoader -> BL31 -> Kernel Secure-Boot Firewall
    # ------------------------------------------------------------------

    def test_08_healthy_emmc_secureboot_chain_passes(self) -> None:
        manifest = build_synthetic_secureboot_chain_manifest(
            boot_target=SECUREBOOT_TARGET_EMMC_LOCKED_SOC,
        )
        rep = verify_cxd90057_secureboot_envelope(manifest, scenario_id="TEST_SB_HEALTHY")
        self.assertTrue(rep.passed, f"Unexpected errors: {rep.errors}")
        self.assertEqual(rep.status, STATUS_VERIFIED_SECUREBOOT_ENVELOPE)
        self.assertEqual(rep.stages_verified, CXD90057_SECUREBOOT_STAGES)
        self.assertTrue(rep.boot_stages_untouched)
        self.assertFalse(rep.stage_b_volatile_overlay_only)
        self.assertEqual(rep.otp_fuse_writes, 0)
        self.assertEqual(rep.spacc_key_reads, 0)
        self.assertEqual(rep.physical_device_writes, 0)

    def test_09_stage_b_qemu_overlay_and_bind_mount_pass_with_untouched_bootchain(self) -> None:
        for target in (SECUREBOOT_TARGET_STAGE_B_QEMU_OVERLAY, SECUREBOOT_TARGET_STAGE_B_BIND_MOUNT):
            manifest = build_synthetic_secureboot_chain_manifest(
                boot_target=target,
                requested_operations=("mount_userland_bind_overlay", "verify_boot_stages_untouched"),
            )
            rep = verify_cxd90057_secureboot_envelope(manifest)
            self.assertTrue(rep.passed, f"Stage-B target {target} failed: {rep.errors}")
            self.assertEqual(rep.status, STATUS_VERIFIED_STAGE_B_UNTOUCHED_BOOTCHAIN)
            self.assertTrue(rep.stage_b_volatile_overlay_only)
            self.assertTrue(rep.boot_stages_untouched)

    def test_10_stage_b_attempting_to_modify_boot_stages_is_blocked(self) -> None:
        manifest = build_synthetic_secureboot_chain_manifest(
            boot_target=SECUREBOOT_TARGET_STAGE_B_QEMU_OVERLAY,
            stage_b_modifies_boot_stages=True,
        )
        rep = verify_cxd90057_secureboot_envelope(manifest)
        self.assertFalse(rep.passed)
        self.assertEqual(rep.status, STATUS_REJECTED_SECUREBOOT_FIREWALL)
        self.assertIn(ERR_SECUREBOOT_STAGE_B_MODIFIED_BOOTSTAGE, rep.error_codes)
        self.assertFalse(rep.stage_b_volatile_overlay_only)

    def test_11_patched_payload_digest_on_any_stage_blocked_on_locked_soc(self) -> None:
        for stage in CXD90057_SECUREBOOT_STAGES:
            manifest = build_synthetic_secureboot_chain_manifest(
                boot_target=SECUREBOOT_TARGET_EMMC_LOCKED_SOC,
                patched_stage=stage,
            )
            rep = verify_cxd90057_secureboot_envelope(manifest)
            self.assertFalse(rep.passed)
            self.assertEqual(rep.status, STATUS_REJECTED_SECUREBOOT_FIREWALL)
            self.assertTrue(rep.unsigned_or_patched_blocked)
            self.assertIn(BLOCKED_UNSIGNED_OR_PATCHED_BOOT_STAGE_ON_LOCKED_SOC, rep.error_codes)

    def test_12_unsigned_or_touched_signature_envelope_blocked(self) -> None:
        for stage in CXD90057_SECUREBOOT_STAGES:
            manifest = build_synthetic_secureboot_chain_manifest(unsigned_stage=stage)
            rep = verify_cxd90057_secureboot_envelope(manifest)
            self.assertFalse(rep.passed)
            self.assertTrue(rep.unsigned_or_patched_blocked)
            self.assertIn(BLOCKED_UNSIGNED_OR_PATCHED_BOOT_STAGE_ON_LOCKED_SOC, rep.error_codes)

        # Also catch unsupported signature algorithm even if digest matches
        base = build_synthetic_secureboot_chain_manifest()
        bad_stages = tuple(
            replace(st, signature_algorithm="MD5-NONE") if st.stage_name == "BL31" else st
            for st in base.stages
        )
        rep_alg = verify_cxd90057_secureboot_envelope(replace(base, stages=bad_stages))
        self.assertFalse(rep_alg.passed)
        self.assertTrue(rep_alg.unsigned_or_patched_blocked)

    def test_13_payload_capacity_overflow_blocked(self) -> None:
        manifest = build_synthetic_secureboot_chain_manifest(overflow_stage="Kernel")
        rep = verify_cxd90057_secureboot_envelope(manifest)
        self.assertFalse(rep.passed)
        self.assertIn(ERR_SECUREBOOT_CAPACITY_OVERFLOW, rep.error_codes)
        self.assertIn(BLOCKED_UNSIGNED_OR_PATCHED_BOOT_STAGE_ON_LOCKED_SOC, rep.error_codes)

    def test_14_monotonic_epoch_rollback_blocked(self) -> None:
        manifest = build_synthetic_secureboot_chain_manifest(downgrade_stage="IPL")
        rep = verify_cxd90057_secureboot_envelope(manifest)
        self.assertFalse(rep.passed)
        self.assertIn(ERR_SECUREBOOT_EPOCH_ROLLBACK, rep.error_codes)
        self.assertIn(BLOCKED_UNSIGNED_OR_PATCHED_BOOT_STAGE_ON_LOCKED_SOC, rep.error_codes)

    def test_15_incomplete_or_reordered_boot_chain_blocked(self) -> None:
        base = build_synthetic_secureboot_chain_manifest()
        missing_bl31 = tuple(st for st in base.stages if st.stage_name != "BL31")
        rep = verify_cxd90057_secureboot_envelope(replace(base, stages=missing_bl31))
        self.assertFalse(rep.passed)
        self.assertIn(ERR_SECUREBOOT_STAGE_ORDER_OR_MISSING, rep.error_codes)

        swapped = (base.stages[0], base.stages[2], base.stages[1], base.stages[3])
        rep_order = verify_cxd90057_secureboot_envelope(replace(base, stages=swapped))
        self.assertFalse(rep_order.passed)
        self.assertIn(ERR_SECUREBOOT_STAGE_ORDER_OR_MISSING, rep_order.error_codes)

    def test_16_cross_sku_fx6_bootloader_and_pmic_init_blocked_on_fx3(self) -> None:
        for stage in ("IPL", "BLoader", "BL31", "Kernel"):
            manifest = build_synthetic_secureboot_chain_manifest(cross_sku_fx6_stage=stage)
            rep = verify_cxd90057_secureboot_envelope(manifest)
            self.assertFalse(rep.passed)
            self.assertTrue(rep.cross_sku_fx6_blocked)
            self.assertIn(BLOCKED_CROSS_SKU_FX6_BOOTLOADER_ON_FX3_SOC, rep.error_codes)

        # Target manifest SKU mismatch also blocked
        base = build_synthetic_secureboot_chain_manifest()
        fx6_target = replace(base, target_sku_code=FX6_SOC_SKU_CODE, target_model_id=FX6_SOC_MODEL_ID)
        rep_target = verify_cxd90057_secureboot_envelope(fx6_target)
        self.assertFalse(rep_target.passed)
        self.assertTrue(rep_target.cross_sku_fx6_blocked)
        self.assertNotEqual(FX3_SOC_MODEL_ID, FX6_SOC_MODEL_ID)
        self.assertNotEqual(FX3_SOC_SKU_CODE, FX6_SOC_SKU_CODE)

    def test_17_otp_efuse_blow_and_spacc_keyslot_dump_blocked(self) -> None:
        for op in (
            "blow_efuse",
            "burn_otp_antirollback",
            "program_efuse_bank",
            "dump_spacc_keyslot",
            "read_spacc_key_slot_0",
            "extract_spacc_keys",
        ):
            dec = audit_otp_efuse_and_spacc_operation(op)
            self.assertFalse(dec.allowed, f"Op should be blocked: {op}")
            self.assertEqual(dec.status, BLOCKED_OTP_EFUSE_OR_SPACC_KEYSLOT_ACCESS)
            self.assertIn(BLOCKED_OTP_EFUSE_OR_SPACC_KEYSLOT_ACCESS, dec.error_codes)
            self.assertEqual(dec.otp_fuse_writes, 0)
            self.assertEqual(dec.spacc_key_reads, 0)
            self.assertEqual(dec.physical_device_writes, 0)

        safe_dec = audit_otp_efuse_and_spacc_operation("verify_boot_chain_envelope")
        self.assertTrue(safe_dec.allowed)
        self.assertEqual(safe_dec.error_codes, ())

        # Manifest-level flags must also block even with benign operation string
        manifest = build_synthetic_secureboot_chain_manifest(
            efuse_otp_write_requested=True,
            spacc_keyslot_read_requested=True,
        )
        rep = verify_cxd90057_secureboot_envelope(manifest)
        self.assertFalse(rep.passed)
        self.assertTrue(rep.otp_efuse_spacc_blocked)
        self.assertIn(BLOCKED_OTP_EFUSE_OR_SPACC_KEYSLOT_ACCESS, rep.error_codes)
        self.assertEqual(rep.otp_fuse_writes, 0)
        self.assertEqual(rep.spacc_key_reads, 0)

    def test_18_secureboot_6_scenario_firewall_all_green(self) -> None:
        res = run_secureboot_envelope_6_scenario_firewall()
        self.assertTrue(res.passed, f"Pillar A errors: {res.errors}")
        self.assertEqual(res.scenarios_passed, 6)
        self.assertEqual(res.scenarios_total, 6)
        self.assertEqual([r.scenario_id for r in res.scenario_results], list(SECUREBOOT_FIREWALL_SCENARIO_IDS))
        self.assertEqual(res.otp_fuse_writes, 0)
        self.assertEqual(res.spacc_key_reads, 0)
        self.assertEqual(res.physical_device_writes, 0)

    # ------------------------------------------------------------------
    # Pillar B — nflasha1..nflasha20 4 KiB / 512 KiB Erase-Group Interval Tree Firewall
    # ------------------------------------------------------------------

    def test_19_emmc_geometry_constants_and_canonical_20_partition_map(self) -> None:
        self.assertEqual(EMMC_SECTOR_BYTES, 512)
        self.assertEqual(EMMC_PAGE_BYTES, 4096)
        self.assertEqual(EMMC_PAGE_LBA_MULTIPLE, 8)
        self.assertEqual(EMMC_ERASE_GROUP_BYTES, 524288)
        self.assertEqual(EMMC_ERASE_GROUP_LBA_MULTIPLE, 1024)
        self.assertEqual(PROTECTED_EMMC_PARTITIONS, ("BOOT0", "BOOT1", "RPMB", "nvs", "adj", "cnflasha"))

        pmap = build_synthetic_fx3_nflasha_partition_map()
        names = [p.partition_name for p in pmap]
        for idx in range(1, 21):
            self.assertIn(f"nflasha{idx}", names)
        for hw in ("BOOT0", "BOOT1", "RPMB"):
            self.assertIn(hw, names)
        self.assertEqual(len(pmap), 23)
        self.assertEqual(find_partition_lba_overlaps(pmap), ())

    def test_20_lba_interval_tree_exact_boundary_and_overlap_queries(self) -> None:
        tree = LbaIntervalTree()
        p1 = EmmcPartitionEntry("pA", 1024, 2047, 1024)
        p2 = EmmcPartitionEntry("pB", 2048, 4095, 2048)
        p3 = EmmcPartitionEntry("pC", 8192, 9215, 1024)
        for p in (p2, p1, p3):
            tree.insert(p)

        # Exact boundary touch at 2047 vs 2048 must not overlap across partitions
        self.assertEqual([h.partition_name for h in tree.query_overlaps(1024, 2047)], ["pA"])
        self.assertEqual([h.partition_name for h in tree.query_overlaps(2048, 4095)], ["pB"])
        # Cross-boundary span [2047, 2048] hits both pA and pB
        hits = sorted(h.partition_name for h in tree.query_overlaps(2047, 2048))
        self.assertEqual(hits, ["pA", "pB"])
        self.assertEqual(tree.query_overlaps(4096, 8191), [])

    def test_21_healthy_fx3_partition_map_and_512k_aligned_op_passes(self) -> None:
        pmap = build_synthetic_fx3_nflasha_partition_map()
        op = EmmcFlashOrEraseOp(
            op_id="aligned-work-erase",
            operation="dryrun_aligned_erase",
            target_partition="nflasha10",
            seek_lba=0,
            sector_count=1024,
            is_erase_or_trim=True,
        )
        rep = verify_partition_map_and_flash_ops(pmap, ops=(op,))
        self.assertTrue(rep.passed, f"Healthy op failed: {rep.errors}")
        self.assertEqual(rep.status, STATUS_VERIFIED_PARTITION_ALIGN_FIREWALL)
        self.assertEqual(rep.overlap_pairs, ())
        self.assertEqual(rep.neighbor_bleed_partitions, ())
        self.assertEqual(rep.erase_group_lba_multiple, 1024)

    def test_22_partition_lba_overlap_detected_across_fx6_shifted_lensdata(self) -> None:
        overlap_map = build_synthetic_fx3_nflasha_partition_map(
            overlap_pair=("nflasha18", 0x00312000),
        )
        rep = verify_partition_map_and_flash_ops(overlap_map)
        self.assertFalse(rep.passed)
        self.assertEqual(rep.status, STATUS_REJECTED_PARTITION_ALIGN_FIREWALL)
        self.assertTrue(rep.overlap_detected)
        self.assertIn(PARTITION_LBA_OVERLAP_DETECTED, rep.error_codes)
        pairs = {(ov.partition_a, ov.partition_b) for ov in rep.overlap_pairs}
        self.assertIn(("nflasha15", "nflasha18"), pairs)

    def test_23_off_by_one_dd_seek_and_unaligned_erase_group_blocked(self) -> None:
        pmap = build_synthetic_fx3_nflasha_partition_map()
        for bad_op in (
            EmmcFlashOrEraseOp("dd-seek-1", "dd_write", "nflasha7", seek_lba=1, sector_count=1024, is_write=True),
            EmmcFlashOrEraseOp("trim-512", "trim", "nflasha7", seek_lba=0, sector_count=512, is_erase_or_trim=True),
            EmmcFlashOrEraseOp("abs-misaligned", "erase", "nflasha1", seek_lba=0x80, sector_count=1024, use_absolute_lba=True, is_erase_or_trim=True),
        ):
            rep = verify_partition_map_and_flash_ops(pmap, ops=(bad_op,))
            self.assertFalse(rep.passed, f"Unaligned op should fail: {bad_op.op_id}")
            self.assertTrue(rep.unaligned_erase_bleed_detected)
            self.assertIn(UNALIGNED_ERASE_GROUP_BLEED_HAZARD, rep.error_codes)

    def test_24_block_size_non_512b_and_zero_sector_op_blocked(self) -> None:
        pmap = build_synthetic_fx3_nflasha_partition_map()
        bad_bs = EmmcFlashOrEraseOp(
            op_id="bad-bs",
            operation="dd_write",
            target_partition="nflasha7",
            seek_lba=0,
            sector_count=1,
            block_size_bytes=333,
            is_write=True,
        )
        rep_bs = verify_partition_map_and_flash_ops(pmap, ops=(bad_bs,))
        self.assertFalse(rep_bs.passed)
        self.assertIn(UNALIGNED_ERASE_GROUP_BLEED_HAZARD, rep_bs.error_codes)

        # 4 KiB bs=4096 scaling: seek_lba=128 -> 128*8 = 1024 sectors (512 KiB aligned)
        ok_4k = EmmcFlashOrEraseOp(
            op_id="aligned-4k-bs",
            operation="dryrun_aligned_check",
            target_partition="nflasha10",
            seek_lba=128,
            sector_count=128,
            block_size_bytes=4096,
            is_erase_or_trim=True,
        )
        rep_4k = verify_partition_map_and_flash_ops(pmap, ops=(ok_4k,))
        self.assertTrue(rep_4k.passed, f"4KiB scaled 512KiB op should pass: {rep_4k.errors}")

    def test_25_neighbor_partition_bleed_into_cnflasha_and_nvs_blocked(self) -> None:
        pmap = build_synthetic_fx3_nflasha_partition_map()
        # Bleed from end of nflasha15 into nflasha18 (cnflasha LensData)
        bleed_18 = EmmcFlashOrEraseOp(
            op_id="bleed-cnflasha",
            operation="erase_trim",
            target_partition="nflasha15",
            seek_lba=0x000F9C00,
            sector_count=2048,
            is_erase_or_trim=True,
        )
        rep_18 = verify_partition_map_and_flash_ops(pmap, ops=(bleed_18,))
        self.assertFalse(rep_18.passed)
        self.assertTrue(rep_18.unaligned_erase_bleed_detected)
        self.assertIn("nflasha18", rep_18.neighbor_bleed_partitions)
        self.assertIn(UNALIGNED_ERASE_GROUP_BLEED_HAZARD, rep_18.error_codes)

        # Bleed from end of nflasha1 (0x80..0xBFFF) into nflasha2 (nvs @ 0xC000)
        bleed_2 = EmmcFlashOrEraseOp(
            op_id="bleed-nvs",
            operation="dd_write",
            target_partition="nflasha1",
            seek_lba=0x0000B800,
            sector_count=2048,
            is_write=True,
        )
        rep_2 = verify_partition_map_and_flash_ops(pmap, ops=(bleed_2,))
        self.assertFalse(rep_2.passed)
        self.assertIn("nflasha2", rep_2.neighbor_bleed_partitions)
        self.assertIn(UNALIGNED_ERASE_GROUP_BLEED_HAZARD, rep_2.error_codes)

    def test_26_protected_hardware_partitions_boot0_boot1_rpmb_write_blocked(self) -> None:
        pmap = build_synthetic_fx3_nflasha_partition_map()
        for target in ("BOOT0", "BOOT1", "RPMB", "/dev/mmcblk0boot0", "/dev/mmcblk0boot1", "/dev/mmcblk0rpmb", "nflashaB0", "nflashaB1"):
            op = EmmcFlashOrEraseOp(
                op_id=f"write-{target}",
                operation="dd_write",
                target_partition=target,
                seek_lba=0,
                sector_count=1024,
                is_write=True,
            )
            rep = verify_partition_map_and_flash_ops(pmap, ops=(op,))
            self.assertFalse(rep.passed, f"Protected target should be blocked: {target}")
            self.assertTrue(rep.protected_partition_write_blocked)
            self.assertIn(PROTECTED_PARTITION_WRITE_ATTEMPT_BLOCKED, rep.error_codes)

    def test_27_protected_calibration_partitions_nvs_adj_cnflasha_write_blocked(self) -> None:
        pmap = build_synthetic_fx3_nflasha_partition_map()
        for target in ("nvs", "adj", "cnflasha", "nflasha2", "nflasha4", "nflasha18"):
            op = EmmcFlashOrEraseOp(
                op_id=f"erase-{target}",
                operation="erase",
                target_partition=target,
                seek_lba=0,
                sector_count=1024,
                is_erase_or_trim=True,
            )
            rep = verify_partition_map_and_flash_ops(pmap, ops=(op,))
            self.assertFalse(rep.passed, f"Protected cal partition should be blocked: {target}")
            self.assertTrue(rep.protected_partition_write_blocked)
            self.assertIn(PROTECTED_PARTITION_WRITE_ATTEMPT_BLOCKED, rep.error_codes)

    def test_28_invalid_4k_page_alignment_and_invalid_geometry_rejected(self) -> None:
        base = list(build_synthetic_fx3_nflasha_partition_map())
        bad_4k = replace(base[6], start_lba=base[6].start_lba + 1, end_lba=base[6].end_lba + 1)
        rep_4k = verify_partition_map_and_flash_ops(tuple([bad_4k] + base[7:]))
        self.assertFalse(rep_4k.passed)
        self.assertIn(ERR_PARTALIGN_MISALIGNED_4K_PAGE, rep_4k.error_codes)

        bad_geom = replace(base[6], partition_sector_count=base[6].partition_sector_count + 8)
        rep_geom = verify_partition_map_and_flash_ops(tuple([bad_geom] + base[7:]))
        self.assertFalse(rep_geom.passed)
        self.assertIn(ERR_PARTALIGN_INVALID_GEOMETRY, rep_geom.error_codes)

    def test_29_unknown_target_partition_and_reserved_empty_write_rejected(self) -> None:
        pmap = build_synthetic_fx3_nflasha_partition_map()
        unknown_op = EmmcFlashOrEraseOp(
            op_id="unknown-part",
            operation="dd_write",
            target_partition="nflasha99",
            seek_lba=0,
            sector_count=1024,
            is_write=True,
        )
        rep_unk = verify_partition_map_and_flash_ops(pmap, ops=(unknown_op,))
        self.assertFalse(rep_unk.passed)
        self.assertIn(ERR_PARTALIGN_UNKNOWN_TARGET_PARTITION, rep_unk.error_codes)

        reserved_op = EmmcFlashOrEraseOp(
            op_id="reserved-part",
            operation="erase",
            target_partition="nflasha9",
            seek_lba=0,
            sector_count=1024,
            is_erase_or_trim=True,
        )
        rep_res = verify_partition_map_and_flash_ops(pmap, ops=(reserved_op,))
        self.assertFalse(rep_res.passed)
        self.assertIn(UNALIGNED_ERASE_GROUP_BLEED_HAZARD, rep_res.error_codes)

    def test_30_readonly_inspect_op_on_non_protected_partition_allowed(self) -> None:
        pmap = build_synthetic_fx3_nflasha_partition_map()
        ro_op = EmmcFlashOrEraseOp(
            op_id="readonly-sha-audit",
            operation="readonly_sha256_verify",
            target_partition="nflasha7",
            seek_lba=0,
            sector_count=1024,
            is_write=False,
            is_erase_or_trim=False,
        )
        rep = verify_partition_map_and_flash_ops(pmap, ops=(ro_op,))
        self.assertTrue(rep.passed, f"Read-only audit op should pass: {rep.errors}")

    def test_31_partition_align_6_scenario_firewall_all_green(self) -> None:
        res = run_partition_align_6_scenario_firewall()
        self.assertTrue(res.passed, f"Pillar B errors: {res.errors}")
        self.assertEqual(res.scenarios_passed, 6)
        self.assertEqual(res.scenarios_total, 6)
        self.assertEqual([r.scenario_id for r in res.scenario_results], list(PARTALIGN_FIREWALL_SCENARIO_IDS))
        self.assertEqual(res.physical_device_writes, 0)
        self.assertEqual(res.otp_fuse_writes, 0)
        self.assertEqual(res.spacc_key_reads, 0)

    # ------------------------------------------------------------------
    # Pillar C — Master Determinism, JSON Hygiene, CLI & >=15-Pillar Integration
    # ------------------------------------------------------------------

    def test_32_clean_room_suite_sha256_is_deterministic(self) -> None:
        r2 = run_secureboot_chain_and_partition_align_suite(force_clean_room=True)
        self.assertEqual(self.clean_report.suite_sha256, r2.suite_sha256)
        self.assertEqual(
            self.clean_report.secureboot_6_scenario_firewall.suite_sha256,
            r2.secureboot_6_scenario_firewall.suite_sha256,
        )
        self.assertEqual(
            self.clean_report.partition_align_6_scenario_firewall.suite_sha256,
            r2.partition_align_6_scenario_firewall.suite_sha256,
        )

    def test_33_json_serialization_no_raw_bytes_and_no_nan(self) -> None:
        rendered = json.dumps(self.suite_report.to_dict(), ensure_ascii=False, sort_keys=True, allow_nan=False)
        self.assertNotRegex(rendered, RAW_BYTES_RE)
        decoded = json.loads(rendered)
        self.assertEqual(decoded["suite_sha256"], self.suite_report.suite_sha256)
        self.assertEqual(decoded["physical_device_writes"], 0)
        self.assertEqual(decoded["otp_fuse_touches"], 0)
        self.assertEqual(decoded["otp_fuse_writes"], 0)
        self.assertEqual(decoded["spacc_key_reads"], 0)
        self.assertEqual(decoded["passive_tx_bytes_emitted"], 0)
        self.assertFalse(decoded["persistent_emmc_writes_authorized"])
        self.assertFalse(decoded["persistent_write_release"])

    def test_34_cli_verify_secureboot_partalign_clean_room_json_and_text(self) -> None:
        buf_json = io.StringIO()
        with (
            mock.patch.object(sys, "argv", ["fx3_recovery", "verify-secureboot-partalign", "--clean-room", "--json"]),
            redirect_stdout(buf_json),
        ):
            rc_json = fx3_cli.main()
        self.assertEqual(rc_json, 0)
        rendered = buf_json.getvalue()
        self.assertNotRegex(rendered, RAW_BYTES_RE)
        parsed = json.loads(rendered)
        self.assertEqual(parsed["status"], STATUS_VERIFIED_SECUREBOOT_PARTALIGN_GATE)
        self.assertEqual(parsed["verification_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(parsed["otp_fuse_writes"], 0)
        self.assertEqual(parsed["spacc_key_reads"], 0)
        self.assertEqual(parsed["physical_device_writes"], 0)

        buf_txt = io.StringIO()
        with (
            mock.patch.object(sys, "argv", ["fx3_recovery", "verify-secureboot-partalign", "--clean-room"]),
            redirect_stdout(buf_txt),
        ):
            rc_txt = fx3_cli.main()
        self.assertEqual(rc_txt, 0)
        txt = buf_txt.getvalue()
        self.assertIn(f"status={STATUS_VERIFIED_SECUREBOOT_PARTALIGN_GATE}", txt)
        self.assertIn("secureboot_scenarios=6/6", txt)
        self.assertIn("partalign_scenarios=6/6", txt)
        self.assertIn("otp_fuse_writes=0", txt)
        self.assertIn("spacc_key_reads=0", txt)

    def test_35_cli_verify_secureboot_partalign_active_mode(self) -> None:
        buf = io.StringIO()
        with (
            mock.patch.object(sys, "argv", ["fx3_recovery", "verify-secureboot-partalign", "--json"]),
            redirect_stdout(buf),
        ):
            rc = fx3_cli.main()
        self.assertEqual(rc, 0)
        rendered = buf.getvalue()
        self.assertNotRegex(rendered, RAW_BYTES_RE)
        parsed = json.loads(rendered)
        self.assertTrue(parsed["all_passed"])
        self.assertIn(parsed["verification_mode"], ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"))

    def test_36_cli_verify_secureboot_partalign_out_writes_artifact(self) -> None:
        scratch_root = ROOT / "work" / "_tests" / "phase134_cli_out"
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
                        "verify-secureboot-partalign",
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
            out_file = scratch_root / "secureboot-partalign-report.json"
            self.assertTrue(out_file.is_file())
            written = json.loads(out_file.read_text(encoding="utf-8"))
            self.assertEqual(written["status"], STATUS_VERIFIED_SECUREBOOT_PARTALIGN_GATE)
            self.assertEqual(written["spacc_key_reads"], 0)
        finally:
            if scratch_root.exists():
                shutil.rmtree(scratch_root)

    def test_37_cli_verify_secureboot_partalign_failure_returns_exit_2(self) -> None:
        failing = SecurebootChainAndPartitionAlignSuiteReport(
            **{**self.clean_report.__dict__, "all_passed": False, "status": STATUS_FAIL_SECUREBOOT_PARTALIGN_GATE}
        )
        with mock.patch(
            "fx3_recovery.__main__.run_secureboot_chain_and_partition_align_suite",
            return_value=failing,
        ):
            buf = io.StringIO()
            with (
                mock.patch.object(sys, "argv", ["fx3_recovery", "verify-secureboot-partalign", "--clean-room", "--json"]),
                redirect_stdout(buf),
            ):
                rc = fx3_cli.main()
            self.assertEqual(rc, 2)
            parsed = json.loads(buf.getvalue())
            self.assertFalse(parsed["all_passed"])
            self.assertEqual(parsed["status"], STATUS_FAIL_SECUREBOOT_PARTALIGN_GATE)

    def test_38_cli_verify_all_recovery_15_pillars_clean_room_and_failure_propagation(self) -> None:
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
                    "--with-phase124",
                    "--with-phase126",
                    "--with-phase134",
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
        self.assertGreaterEqual(parsed["pillar_count"], 15)
        self.assertEqual(parsed["pillars_passed"], parsed["pillar_count"])
        self.assertIn("phase134_pillar15_secureboot_chain_partalign", parsed)
        self.assertEqual(
            parsed["phase134_pillar15_secureboot_chain_partalign"]["status"],
            STATUS_VERIFIED_SECUREBOOT_PARTALIGN_GATE,
        )

        failing = SecurebootChainAndPartitionAlignSuiteReport(
            **{**self.clean_report.__dict__, "all_passed": False, "status": STATUS_FAIL_SECUREBOOT_PARTALIGN_GATE}
        )
        with mock.patch(
            "fx3_recovery.__main__.run_secureboot_chain_and_partition_align_suite",
            return_value=failing,
        ):
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
                        "--with-phase124",
                        "--with-phase126",
                        "--with-phase134",
                        "--json",
                    ],
                ),
                redirect_stdout(buf_fail),
            ):
                rc_fail = fx3_cli.main()
            self.assertEqual(rc_fail, 2)
            parsed_fail = json.loads(buf_fail.getvalue())
            self.assertFalse(parsed_fail["all_passed"])
            self.assertGreaterEqual(parsed_fail["pillar_count"], 15)
            self.assertEqual(parsed_fail["pillars_passed"], parsed_fail["pillar_count"] - 1)

    def test_39_cli_verify_all_recovery_15_pillars_active_mode(self) -> None:
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
        self.assertGreaterEqual(parsed["pillar_count"], 15)
        self.assertEqual(parsed["pillars_passed"], parsed["pillar_count"])
        self.assertIn("phase134_pillar15_secureboot_chain_partalign", parsed)

    def test_40_cli_verify_all_recovery_default_compat_and_text_15_pillars(self) -> None:
        buf_def = io.StringIO()
        with (
            mock.patch.object(
                sys,
                "argv",
                ["fx3_recovery", "verify-all-recovery", "--clean-room", "--json"],
            ),
            redirect_stdout(buf_def),
        ):
            rc_def = fx3_cli.main()
        self.assertEqual(rc_def, 0)
        parsed_def = json.loads(buf_def.getvalue())
        self.assertGreaterEqual(parsed_def["pillar_count"], 7)
        self.assertEqual(parsed_def["pillars_passed"], parsed_def["pillar_count"])
        self.assertNotIn("phase134_pillar15_secureboot_chain_partalign", parsed_def)

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
                ],
            ),
            redirect_stdout(buf_txt),
        ):
            rc_txt = fx3_cli.main()
        self.assertEqual(rc_txt, 0)
        txt = buf_txt.getvalue()
        self.assertIn("status=VERIFIED_RECOVERY_MASTER_SUITE", txt)
        self.assertIn("pillars=15/15", txt)

    def test_41_donor_snapshot_and_pillar_reports_to_dict_serializable(self) -> None:
        sb_dict = self.clean_report.secureboot_6_scenario_firewall.to_dict()
        pa_dict = self.clean_report.partition_align_6_scenario_firewall.to_dict()
        self.assertEqual(sb_dict["scenarios_passed"], 6)
        self.assertEqual(pa_dict["scenarios_passed"], 6)
        self.assertEqual(sb_dict["otp_fuse_writes"], 0)
        self.assertEqual(sb_dict["spacc_key_reads"], 0)
        self.assertEqual(pa_dict["physical_device_writes"], 0)

    def test_42_cross_sku_failure_propagates_to_master_suite(self) -> None:
        bad_snap = replace(self.clean_report.donor_snapshot, cross_sku_distinct=False)
        with mock.patch(
            "fx3_recovery.secureboot_chain_and_partition_align_verifier.inspect_secureboot_and_partalign_donors_readonly",
            return_value=bad_snap,
        ):
            rep = run_secureboot_chain_and_partition_align_suite(force_clean_room=True)
            self.assertFalse(rep.all_passed)
            self.assertEqual(rep.status, STATUS_FAIL_SECUREBOOT_PARTALIGN_GATE)
            self.assertGreaterEqual(len(rep.errors), 1)


if __name__ == "__main__":
    unittest.main()
