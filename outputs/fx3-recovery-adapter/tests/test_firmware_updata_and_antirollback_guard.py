"""Dual-mode unit tests for Phase 79 CXD90057 OTP/RPMB Anti-Rollback & BYOF Guard.

Passes in BOTH:
- Local Donor `O_RDONLY` mode (inspects real FX3 `v7.02` & FX6 `v6.01` `WBI2`,
  `vmlinux.bin`, `libc-2.25.so`, `libstdc++.so.6.0.22`, `libInfraSetupFile.so`,
  `appFw.so`, and `cxd90057.dtb` via bounded `os.O_RDONLY` reads)
- `FX3_FX6_FORCE_CLEAN_ROOM=1` mode (deterministic clean-room synthetic fixtures)
Designed for `< 0.3s` execution time with zero binary/bytecode residue.
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

HERE = Path(__file__).resolve().parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import fx3_recovery
from fx3_recovery import __main__ as fx3_cli
from fx3_recovery.files import ROOT, is_forced_clean_room, resolve_donor_path
from fx3_recovery.firmware_updata_and_antirollback_guard import (
    ALLOWED_STAGE_B_VOLATILE_RAM_OVERLAY,
    ALLOW_BOOT_PARTITION_TARGETING,
    ALLOW_DESTRUCTIVE_FASTBOOT,
    ANTIROLLBACK_GUARD_SCHEMA,
    BLOCKED_ANTIROLLBACK_EPOCH_DOWNGRADE,
    BLOCKED_CROSS_SKU_BOOTCHAIN_BRICK,
    BLOCKED_PERMANENT_EMMC_WP_FUSE_TRAP,
    BLOCKED_PERSISTENT_EMMC_WRITES_LOCKED,
    BOOT_CHAIN_STAGES,
    DONOR_FX3_WBI2_RELPATH,
    DONOR_FX6_WBI2_RELPATH,
    ELFCLASS32,
    ELFDATA2MSB,
    EM_ARM,
    EM_X86_64,
    ERR_KERNEL_VERSION_MISMATCH,
    ERR_MISSING_REQUIRED_DONOR_MEMBER,
    ERR_TRUNCATED_ELF_LOAD_SEGMENT,
    ERR_WBI2_SECTION_COUNT_MISMATCH,
    ERR_WRONG_ISA_OR_ENDIANNESS,
    EXPECTED_GLIBC_EPOCH,
    EXPECTED_KERNEL_RELEASE_PREFIX,
    EXT_CSD_BOOT_WP_IDX,
    EXT_CSD_B_PERM_WP_EN,
    EXT_CSD_B_PWR_WP_EN,
    EXT_CSD_USER_WP_IDX,
    EXT_CSD_US_PERM_WP_EN,
    EXT_CSD_US_PWR_WP_EN,
    FX3_SKU_CODE,
    FX3_WBI2_EXPECTED_SECTIONS,
    FX6_SKU_CODE,
    FX6_WBI2_EXPECTED_SECTIONS,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHYSICAL_DEVICE_WRITES,
    READ_ONLY_DONOR_ACCESS,
    REJECTED_GLIBC_CXXABI_MISMATCH,
    REJECTED_HOST_FX3_PRE_V700,
    REJECTED_INCOMPATIBLE_PRE_V600_NO_BIG6,
    REJECTED_KERNEL_ABI_MISMATCH,
    STATUS_FAIL_ANTIROLLBACK_GUARD,
    STATUS_VERIFIED_ANTIROLLBACK_GUARD,
    TIER_A_GOLD_VERIFIED,
    TIER_B_CONDITIONALLY_COMPATIBLE,
    ZERO_USERSPACE_RAM_ONLY,
    audit_ext_csd_write_protect,
    audit_mmc_wp_command_or_write,
    build_byof_compatibility_matrix,
    build_synthetic_byof_donor_tree,
    build_synthetic_elf64_aarch64,
    build_synthetic_ext_csd_with_wp,
    build_synthetic_vmlinux_banner_bytes,
    build_synthetic_wbi2_header_bytes,
    classify_byof_version_pair,
    evaluate_bootchain_transition,
    evaluate_stage_b_volatile_ram_overlay,
    inspect_donor_artifacts_readonly,
    inspect_elf64_aarch64_bytes,
    resolve_firmware_epoch,
    run_antirollback_and_byof_guard_suite,
    validate_byof_donor_tree,
)


class FirmwareUpdataAndAntiRollbackGuardTests(unittest.TestCase):
    def setUp(self) -> None:
        self._sandbox = (
            ROOT / "outputs" / "fx3-recovery-adapter" / f".tmp-phase79-test-{os.getpid()}-{time.time_ns()}"
        )

    def tearDown(self) -> None:
        shutil.rmtree(self._sandbox, ignore_errors=True)

    def test_01_safety_constants_and_package_exports(self) -> None:
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(PERSISTENT_WRITE_RELEASE)
        self.assertFalse(ALLOW_BOOT_PARTITION_TARGETING)
        self.assertFalse(ALLOW_DESTRUCTIVE_FASTBOOT)
        self.assertTrue(READ_ONLY_DONOR_ACCESS)
        self.assertEqual(PHYSICAL_DEVICE_WRITES, 0)
        self.assertEqual(len(BOOT_CHAIN_STAGES), 8)
        self.assertEqual(fx3_recovery.ANTIROLLBACK_GUARD_SCHEMA, ANTIROLLBACK_GUARD_SCHEMA)
        for symbol in (
            "evaluate_bootchain_transition",
            "evaluate_stage_b_volatile_ram_overlay",
            "classify_byof_version_pair",
            "build_byof_compatibility_matrix",
            "inspect_elf64_aarch64_bytes",
            "validate_byof_donor_tree",
            "audit_ext_csd_write_protect",
            "audit_mmc_wp_command_or_write",
            "run_antirollback_and_byof_guard_suite",
        ):
            self.assertIn(symbol, fx3_recovery.__all__)

    def test_02_monotonic_firmware_epoch_resolution(self) -> None:
        self.assertLess(resolve_firmware_epoch("FX3", "v2.05"), resolve_firmware_epoch("FX3", "v6.00"))
        self.assertLess(resolve_firmware_epoch("FX3", "v6.00"), resolve_firmware_epoch("FX3", "v7.00"))
        self.assertLess(resolve_firmware_epoch("FX3", "v7.00"), resolve_firmware_epoch("FX3", "v7.02"))
        self.assertEqual(resolve_firmware_epoch("ILME-FX3", "7.02"), 5)
        self.assertEqual(resolve_firmware_epoch("ILME-FX6", "6.01"), 5)
        with self.assertRaises(ValueError):
            resolve_firmware_epoch("FX3", "not-a-version")
        with self.assertRaises(ValueError):
            resolve_firmware_epoch("A7SIII", "v3.00")

    def test_03_blocks_nbl_and_tz_downgrade_from_v702_to_pre_v700(self) -> None:
        for old_ver in ("v1.01", "v2.05", "v5.00", "v6.00"):
            for comp in ("nbl_a", "nbl_b", "tz_optee", "uboot_a", "boot_a", "firmware.updata"):
                dec = evaluate_bootchain_transition(
                    host_sku=FX3_SKU_CODE,
                    host_version="v7.02",
                    target_component=comp,
                    candidate_sku=FX3_SKU_CODE,
                    candidate_version=old_ver,
                )
                self.assertFalse(dec.allowed)
                self.assertEqual(dec.decision_code, BLOCKED_ANTIROLLBACK_EPOCH_DOWNGRADE)
                self.assertFalse(dec.epoch_check_passed)
                self.assertTrue(dec.sku_check_passed)
                self.assertEqual(dec.antirollback_brick_risk, "IRREVERSIBLE_SECURE_BOOT_BRICK")
                self.assertFalse(dec.persistent_emmc_writes_authorized)
                self.assertFalse(dec.persistent_write_release)
                self.assertEqual(dec.physical_device_writes, 0)

    def test_04_blocks_v700_ratcheted_body_downgrade_to_v600(self) -> None:
        dec = evaluate_bootchain_transition(
            host_sku=FX3_SKU_CODE,
            host_version="v7.00",
            target_component="uboot_b",
            candidate_sku=FX3_SKU_CODE,
            candidate_version="v6.00",
        )
        self.assertFalse(dec.allowed)
        self.assertEqual(dec.decision_code, BLOCKED_ANTIROLLBACK_EPOCH_DOWNGRADE)
        self.assertEqual(dec.host_epoch, 4)
        self.assertEqual(dec.candidate_epoch, 3)

    def test_05_blocks_cross_sku_fx6_bootchain_and_wbi2_on_fx3(self) -> None:
        for comp in ("nbl_a", "tz_optee", "uboot_a", "WBI2", "cpapp-b.bin", "boot_a"):
            dec = evaluate_bootchain_transition(
                host_sku=FX3_SKU_CODE,
                host_version="v7.02",
                target_component=comp,
                candidate_sku=FX6_SKU_CODE,
                candidate_version="v6.01",
            )
            self.assertFalse(dec.allowed)
            self.assertEqual(dec.decision_code, BLOCKED_CROSS_SKU_BOOTCHAIN_BRICK)
            self.assertFalse(dec.sku_check_passed)
            self.assertEqual(dec.otp_fuse_touches, 0)
            self.assertEqual(dec.rpmb_counter_increments, 0)

    def test_06_blocks_persistent_same_epoch_flash_while_writes_locked(self) -> None:
        dec = evaluate_bootchain_transition(
            host_sku=FX3_SKU_CODE,
            host_version="v7.02",
            target_component="nbl_a",
            candidate_sku=FX3_SKU_CODE,
            candidate_version="v7.02",
            mode="PERSISTENT_FLASH",
        )
        self.assertFalse(dec.allowed)
        self.assertTrue(dec.epoch_check_passed)
        self.assertTrue(dec.sku_check_passed)
        self.assertEqual(dec.decision_code, BLOCKED_PERSISTENT_EMMC_WRITES_LOCKED)
        self.assertFalse(dec.persistent_emmc_writes_authorized)

    def test_07_allows_stage_b_volatile_ram_overlay_transition(self) -> None:
        dec = evaluate_bootchain_transition(
            host_sku=FX3_SKU_CODE,
            host_version="v7.02",
            target_component="stage_b_volatile_ram_overlay",
            candidate_sku=FX6_SKU_CODE,
            candidate_version="v6.01",
            mode="VOLATILE_RAM_OVERLAY",
        )
        self.assertTrue(dec.allowed)
        self.assertEqual(dec.decision_code, ALLOWED_STAGE_B_VOLATILE_RAM_OVERLAY)
        self.assertEqual(dec.otp_fuse_touches, 0)
        self.assertEqual(dec.rpmb_counter_increments, 0)
        self.assertEqual(dec.antirollback_brick_risk, ZERO_USERSPACE_RAM_ONLY)
        self.assertFalse(dec.persistent_emmc_writes_authorized)
        self.assertFalse(dec.persistent_write_release)

    def test_08_stage_b_volatile_ram_overlay_structural_proof(self) -> None:
        proof = evaluate_stage_b_volatile_ram_overlay(
            host_fx3_version="v7.02",
            host_kernel_release="4.9.337-scel+",
            donor_fx6_version="v6.01",
            userspace_mount_base="/tmp",
        )
        self.assertTrue(proof.passed)
        self.assertEqual(proof.decision_code, ALLOWED_STAGE_B_VOLATILE_RAM_OVERLAY)
        self.assertEqual(proof.otp_fuse_touches, 0)
        self.assertEqual(proof.rpmb_counter_increments, 0)
        self.assertEqual(proof.bootchain_mutations, 0)
        self.assertEqual(proof.kernel_mutations, 0)
        self.assertEqual(proof.cp_rtos_mutations, 0)
        self.assertEqual(proof.antirollback_brick_risk, ZERO_USERSPACE_RAM_ONLY)
        self.assertEqual(len(proof.stages), 7)
        self.assertTrue(all(not s.mutated and s.otp_touches == 0 and s.rpmb_increments == 0 for s in proof.stages))

    def test_09_stage_b_rejects_non_tmp_mount_or_wrong_kernel(self) -> None:
        bad_mount = evaluate_stage_b_volatile_ram_overlay(userspace_mount_base="/usr")
        self.assertFalse(bad_mount.passed)
        self.assertNotEqual(bad_mount.antirollback_brick_risk, ZERO_USERSPACE_RAM_ONLY)

        bad_kern = evaluate_stage_b_volatile_ram_overlay(host_kernel_release="5.10.0-custom")
        self.assertFalse(bad_kern.passed)

        bad_host = evaluate_stage_b_volatile_ram_overlay(host_fx3_version="v2.05")
        self.assertFalse(bad_host.passed)

    def test_10_byof_matrix_gold_verified_fx3_v702_fx6_v601(self) -> None:
        dec = classify_byof_version_pair("v7.02", "v6.01")
        self.assertTrue(dec.compatible)
        self.assertEqual(dec.tier, TIER_A_GOLD_VERIFIED)
        self.assertTrue(dec.big6_available)
        self.assertFalse(dec.requires_autolocator)

    def test_11_byof_matrix_conditionally_compatible_pairs(self) -> None:
        for host_v, donor_v in (
            ("v7.01", "v6.01"),
            ("v7.00", "v6.01"),
            ("v7.02", "v6.00"),
            ("v7.01", "v6.00"),
            ("v7.00", "v6.00"),
        ):
            dec = classify_byof_version_pair(host_v, donor_v)
            self.assertTrue(dec.compatible)
            self.assertEqual(dec.tier, TIER_B_CONDITIONALLY_COMPATIBLE)
            self.assertTrue(dec.big6_available)
            self.assertTrue(dec.requires_autolocator)

    def test_12_byof_matrix_rejects_pre_v600_fx6_v502_missing_big6(self) -> None:
        for host_v in ("v7.00", "v7.01", "v7.02"):
            dec = classify_byof_version_pair(host_v, "v5.02")
            self.assertFalse(dec.compatible)
            self.assertEqual(dec.tier, REJECTED_INCOMPATIBLE_PRE_V600_NO_BIG6)
            self.assertFalse(dec.big6_available)
            self.assertIn("v6.01", dec.actionable_guidance)

    def test_13_byof_matrix_full_3x3_shape(self) -> None:
        matrix = build_byof_compatibility_matrix()
        self.assertEqual(len(matrix), 9)
        gold = [r for r in matrix if r.tier == TIER_A_GOLD_VERIFIED]
        cond = [r for r in matrix if r.tier == TIER_B_CONDITIONALLY_COMPATIBLE]
        rej = [r for r in matrix if not r.compatible]
        self.assertEqual(len(gold), 1)
        self.assertEqual(len(cond), 5)
        self.assertEqual(len(rej), 3)

    def test_14_byof_rejects_pre_v700_host_and_abi_or_kernel_mismatch(self) -> None:
        pre_host = classify_byof_version_pair("v2.05", "v6.01")
        self.assertFalse(pre_host.compatible)
        self.assertEqual(pre_host.tier, REJECTED_HOST_FX3_PRE_V700)

        bad_glibc = classify_byof_version_pair("v7.02", "v6.01", glibc_epoch="GLIBC_2.34")
        self.assertFalse(bad_glibc.compatible)
        self.assertEqual(bad_glibc.tier, REJECTED_GLIBC_CXXABI_MISMATCH)

        bad_cxx = classify_byof_version_pair("v7.02", "v6.01", cxxabi_versions=("CXXABI_1.3.15",))
        self.assertFalse(bad_cxx.compatible)
        self.assertEqual(bad_cxx.tier, REJECTED_GLIBC_CXXABI_MISMATCH)

        bad_kern = classify_byof_version_pair("v7.02", "v6.01", kernel_release="5.10.12")
        self.assertFalse(bad_kern.compatible)
        self.assertEqual(bad_kern.tier, REJECTED_KERNEL_ABI_MISMATCH)

    def test_15_elf64_inspector_valid_aarch64_image(self) -> None:
        raw = build_synthetic_elf64_aarch64("libInfraTest.so")
        rep = inspect_elf64_aarch64_bytes(
            raw, label="libInfraTest.so", require_glibc_217=True, require_cxxabi_13=True
        )
        self.assertTrue(rep.valid)
        self.assertEqual(rep.e_machine, 183)
        self.assertEqual(rep.pt_load_count, 1)
        self.assertTrue(rep.has_glibc_217)
        self.assertTrue(rep.has_cxxabi_13)

    def test_16_elf64_inspector_rejects_wrong_isa_and_endianness(self) -> None:
        x86 = build_synthetic_elf64_aarch64("x86", e_machine=EM_X86_64)
        rep_x86 = inspect_elf64_aarch64_bytes(x86, label="x86")
        self.assertFalse(rep_x86.valid)
        self.assertIn(ERR_WRONG_ISA_OR_ENDIANNESS, rep_x86.error_codes)

        arm32 = build_synthetic_elf64_aarch64("arm32", ei_class=ELFCLASS32, e_machine=EM_ARM)
        rep_arm = inspect_elf64_aarch64_bytes(arm32, label="arm32")
        self.assertFalse(rep_arm.valid)
        self.assertIn(ERR_WRONG_ISA_OR_ENDIANNESS, rep_arm.error_codes)

        msb = build_synthetic_elf64_aarch64("msb", ei_data=ELFDATA2MSB)
        rep_msb = inspect_elf64_aarch64_bytes(msb, label="msb")
        self.assertFalse(rep_msb.valid)
        self.assertIn(ERR_WRONG_ISA_OR_ENDIANNESS, rep_msb.error_codes)

        not_elf = b"NOT_AN_ELF_FILE" + b"\x00" * 128
        rep_bad = inspect_elf64_aarch64_bytes(not_elf, label="not_elf")
        self.assertFalse(rep_bad.valid)
        self.assertIn(ERR_WRONG_ISA_OR_ENDIANNESS, rep_bad.error_codes)

    def test_17_elf64_inspector_rejects_truncated_pt_load_segment(self) -> None:
        trunc = build_synthetic_elf64_aarch64("trunc", truncate_to=512)
        rep = inspect_elf64_aarch64_bytes(trunc, label="trunc")
        self.assertFalse(rep.valid)
        self.assertIn(ERR_TRUNCATED_ELF_LOAD_SEGMENT, rep.error_codes)

        tiny = b"\x7fELF" + b"\x00" * 20
        rep_tiny = inspect_elf64_aarch64_bytes(tiny, label="tiny")
        self.assertFalse(rep_tiny.valid)
        self.assertIn(ERR_TRUNCATED_ELF_LOAD_SEGMENT, rep_tiny.error_codes)

    def test_18_donor_tree_valid_in_memory_and_on_disk_readonly(self) -> None:
        tree = build_synthetic_byof_donor_tree(donor_sku=FX6_SKU_CODE)
        rep_mem = validate_byof_donor_tree(tree, expected_donor_sku=FX6_SKU_CODE)
        self.assertTrue(rep_mem.passed)
        self.assertEqual(rep_mem.wbi2_section_count, FX6_WBI2_EXPECTED_SECTIONS)
        self.assertEqual(rep_mem.kernel_release_observed, EXPECTED_KERNEL_RELEASE_PREFIX)

        self._sandbox.mkdir(parents=True, exist_ok=True)
        for rel, content in tree.items():
            dest = self._sandbox / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(content)
        rep_disk = validate_byof_donor_tree(self._sandbox, expected_donor_sku=FX6_SKU_CODE)
        self.assertTrue(rep_disk.passed)
        self.assertEqual(rep_disk.source_mode, "DIRECTORY_O_RDONLY")
        self.assertEqual(rep_disk.wbi2_section_count, FX6_WBI2_EXPECTED_SECTIONS)

    def test_19_donor_tree_rejects_missing_member_before_cpio(self) -> None:
        tree: dict[str, bytes | None] = dict(build_synthetic_byof_donor_tree(donor_sku=FX6_SKU_CODE))
        tree.pop("lib/libc-2.25.so")
        rep = validate_byof_donor_tree(tree, expected_donor_sku=FX6_SKU_CODE)
        self.assertFalse(rep.passed)
        self.assertIn("lib/libc-2.25.so", rep.missing_members)
        self.assertIn(ERR_MISSING_REQUIRED_DONOR_MEMBER, rep.error_codes)

    def test_20_donor_tree_rejects_wrong_isa_and_truncated_elf(self) -> None:
        bad_isa = dict(build_synthetic_byof_donor_tree(donor_sku=FX6_SKU_CODE))
        bad_isa["lib/libInfraSetupFile.so"] = build_synthetic_elf64_aarch64("x86", e_machine=EM_X86_64)
        rep_isa = validate_byof_donor_tree(bad_isa, expected_donor_sku=FX6_SKU_CODE)
        self.assertFalse(rep_isa.passed)
        self.assertIn(ERR_WRONG_ISA_OR_ENDIANNESS, rep_isa.error_codes)

        bad_trunc = dict(build_synthetic_byof_donor_tree(donor_sku=FX6_SKU_CODE))
        bad_trunc["lib/appFw.so"] = build_synthetic_elf64_aarch64("appFw", truncate_to=1024)
        rep_trunc = validate_byof_donor_tree(bad_trunc, expected_donor_sku=FX6_SKU_CODE)
        self.assertFalse(rep_trunc.passed)
        self.assertIn(ERR_TRUNCATED_ELF_LOAD_SEGMENT, rep_trunc.error_codes)

    def test_21_donor_tree_rejects_wrong_kernel_and_cross_sku_wbi2_sections(self) -> None:
        bad_kern = dict(build_synthetic_byof_donor_tree(donor_sku=FX6_SKU_CODE))
        bad_kern["vmlinux.bin"] = build_synthetic_vmlinux_banner_bytes(kernel_release="5.4.0-wrong")
        rep_kern = validate_byof_donor_tree(bad_kern, expected_donor_sku=FX6_SKU_CODE)
        self.assertFalse(rep_kern.passed)
        self.assertIn(ERR_KERNEL_VERSION_MISMATCH, rep_kern.error_codes)

        wrong_wbi2 = dict(build_synthetic_byof_donor_tree(donor_sku=FX6_SKU_CODE))
        wrong_wbi2["nflasha5"] = build_synthetic_wbi2_header_bytes(sections=FX3_WBI2_EXPECTED_SECTIONS)
        rep_wbi = validate_byof_donor_tree(wrong_wbi2, expected_donor_sku=FX6_SKU_CODE)
        self.assertFalse(rep_wbi.passed)
        self.assertIn(ERR_WBI2_SECTION_COUNT_MISMATCH, rep_wbi.error_codes)
        self.assertEqual(rep_wbi.wbi2_section_count, FX3_WBI2_EXPECTED_SECTIONS)

    def test_22_donor_tree_rejects_symlink_on_disk(self) -> None:
        tree = build_synthetic_byof_donor_tree(donor_sku=FX6_SKU_CODE)
        self._sandbox.mkdir(parents=True, exist_ok=True)
        for rel, content in tree.items():
            dest = self._sandbox / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            if rel == "vmlinux.bin":
                real_f = self._sandbox / "real_vmlinux.bin"
                real_f.write_bytes(content)
                dest.symlink_to(real_f)
            else:
                dest.write_bytes(content)
        with self.assertRaises(ValueError):
            validate_byof_donor_tree(self._sandbox, expected_donor_sku=FX6_SKU_CODE)

    def test_23_ext_csd_clean_passes_wp_guard(self) -> None:
        ext = build_synthetic_ext_csd_with_wp(boot_wp=0x00, user_wp=0x00)
        rep = audit_ext_csd_write_protect(ext)
        self.assertTrue(rep.safe)
        self.assertEqual(rep.status, STATUS_VERIFIED_ANTIROLLBACK_GUARD)
        self.assertFalse(rep.b_perm_wp_en)
        self.assertFalse(rep.us_perm_wp_en)
        self.assertEqual(rep.blocked_fuse_traps, ())

    def test_24_ext_csd_blocks_boot_perm_wp_en_173(self) -> None:
        ext = build_synthetic_ext_csd_with_wp(boot_wp=EXT_CSD_B_PERM_WP_EN)
        rep = audit_ext_csd_write_protect(ext)
        self.assertFalse(rep.safe)
        self.assertEqual(rep.status, BLOCKED_PERMANENT_EMMC_WP_FUSE_TRAP)
        self.assertTrue(rep.b_perm_wp_en)
        self.assertIn("EXT_CSD[173]:B_PERM_WP_EN", rep.blocked_fuse_traps)

    def test_25_ext_csd_blocks_user_perm_wp_en_171(self) -> None:
        ext = build_synthetic_ext_csd_with_wp(user_wp=EXT_CSD_US_PERM_WP_EN)
        rep = audit_ext_csd_write_protect(ext)
        self.assertFalse(rep.safe)
        self.assertEqual(rep.status, BLOCKED_PERMANENT_EMMC_WP_FUSE_TRAP)
        self.assertTrue(rep.us_perm_wp_en)
        self.assertIn("EXT_CSD[171]:US_PERM_WP_EN", rep.blocked_fuse_traps)

    def test_26_ext_csd_handles_power_on_wp_warning_and_bad_size(self) -> None:
        pwr = audit_ext_csd_write_protect(
            build_synthetic_ext_csd_with_wp(boot_wp=EXT_CSD_B_PWR_WP_EN, user_wp=EXT_CSD_US_PWR_WP_EN)
        )
        self.assertTrue(pwr.safe)
        self.assertTrue(pwr.b_pwr_wp_en)
        self.assertTrue(pwr.us_pwr_wp_en)
        self.assertEqual(len(pwr.warnings), 2)

        bad_sz = audit_ext_csd_write_protect(b"\x00" * 128)
        self.assertFalse(bad_sz.safe)
        self.assertEqual(bad_sz.status, STATUS_FAIL_ANTIROLLBACK_GUARD)

    def test_27_mmc_utils_commands_and_manifests_blocked(self) -> None:
        for cmd in (
            "mmc boot_wp enable_perm /dev/mmcblk0boot0",
            "mmc writeprotect boot set /dev/mmcblk0 -p",
            "mmc writeprotect user set perm 0 1 /dev/mmcblk0",
            "mmc extcsd write EXT_CSD[173] 0x04",
            "mmc extcsd write EXT_CSD[171] US_PERM_WP_EN",
        ):
            rep = audit_mmc_wp_command_or_write(cmd)
            self.assertFalse(rep.safe)
            self.assertEqual(rep.status, BLOCKED_PERMANENT_EMMC_WP_FUSE_TRAP)

        non_perm_mut = audit_mmc_wp_command_or_write("mmc writeprotect boot set /dev/mmcblk0")
        self.assertFalse(non_perm_mut.safe)
        self.assertEqual(non_perm_mut.status, BLOCKED_PERSISTENT_EMMC_WRITES_LOCKED)

        m_boot = audit_mmc_wp_command_or_write({"ext_csd_index": EXT_CSD_BOOT_WP_IDX, "value": EXT_CSD_B_PERM_WP_EN})
        self.assertFalse(m_boot.safe)
        self.assertEqual(m_boot.status, BLOCKED_PERMANENT_EMMC_WP_FUSE_TRAP)

        m_user = audit_mmc_wp_command_or_write({"ext_csd_index": EXT_CSD_USER_WP_IDX, "value": EXT_CSD_US_PERM_WP_EN})
        self.assertFalse(m_user.safe)
        self.assertEqual(m_user.status, BLOCKED_PERMANENT_EMMC_WP_FUSE_TRAP)

        m_read = audit_mmc_wp_command_or_write({"operation": "read_verify"})
        self.assertTrue(m_read.safe)

    def test_28_clean_room_suite_execution_and_zero_otp_rpmb_invariants(self) -> None:
        rep = run_antirollback_and_byof_guard_suite(force_clean_room=True)
        self.assertTrue(rep.all_passed)
        self.assertEqual(rep.status, STATUS_VERIFIED_ANTIROLLBACK_GUARD)
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(rep.otp_fuse_touches, 0)
        self.assertEqual(rep.rpmb_counter_increments, 0)
        self.assertEqual(rep.antirollback_brick_risk, ZERO_USERSPACE_RAM_ONLY)
        self.assertEqual(rep.donor_snapshot.fx3_wbi2_sections, FX3_WBI2_EXPECTED_SECTIONS)
        self.assertEqual(rep.donor_snapshot.fx6_wbi2_sections, FX6_WBI2_EXPECTED_SECTIONS)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.persistent_write_release)
        self.assertEqual(rep.physical_device_writes, 0)

    def test_29_forced_clean_room_env_disables_local_donors(self) -> None:
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            snap = inspect_donor_artifacts_readonly()
            self.assertEqual(snap.source_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertEqual(snap.inspected_files_count, 0)
            self.assertEqual(snap.fx3_wbi2_sections, FX3_WBI2_EXPECTED_SECTIONS)
            self.assertEqual(snap.fx6_wbi2_sections, FX6_WBI2_EXPECTED_SECTIONS)

    def test_30_local_donor_or_clean_room_dual_mode_parity(self) -> None:
        rep = run_antirollback_and_byof_guard_suite()
        self.assertTrue(rep.all_passed, msg=f"errors={rep.errors}")
        donor_fx3 = resolve_donor_path(DONOR_FX3_WBI2_RELPATH, require_file=True)
        donor_fx6 = resolve_donor_path(DONOR_FX6_WBI2_RELPATH, require_file=True)
        if not is_forced_clean_room() and donor_fx3.is_file() and donor_fx6.is_file():
            self.assertEqual(rep.verification_mode, "LOCAL_DONOR_O_RDONLY")
            self.assertGreaterEqual(rep.donor_snapshot.inspected_files_count, 8)
            self.assertIn(EXPECTED_GLIBC_EPOCH, rep.donor_snapshot.fx6_libc_glibc_versions)
            self.assertTrue(rep.donor_snapshot.fx6_libinfra_glibc_217)
            self.assertTrue(rep.donor_snapshot.fx6_appfw_elf_valid)
            self.assertTrue(rep.donor_snapshot.cxd90057_dtb_present)
        else:
            self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")

        clean = run_antirollback_and_byof_guard_suite(force_clean_room=True)
        self.assertEqual(rep.donor_snapshot.fx3_wbi2_sections, clean.donor_snapshot.fx3_wbi2_sections)
        self.assertEqual(rep.donor_snapshot.fx6_wbi2_sections, clean.donor_snapshot.fx6_wbi2_sections)
        self.assertEqual(rep.stage_b_overlay_proof.otp_fuse_touches, clean.stage_b_overlay_proof.otp_fuse_touches)
        self.assertEqual(
            rep.stage_b_overlay_proof.rpmb_counter_increments,
            clean.stage_b_overlay_proof.rpmb_counter_increments,
        )

    def test_31_cli_verify_antirollback_guard_json_and_out(self) -> None:
        self._sandbox.mkdir(parents=True, exist_ok=True)
        out_dir = self._sandbox / "antirollback-out"
        buf = io.StringIO()
        with mock.patch.object(
            sys,
            "argv",
            ["fx3_recovery", "verify-antirollback-guard", "--clean-room", "--json", "--out", str(out_dir)],
        ):
            with redirect_stdout(buf):
                rc = fx3_cli.main()
        self.assertEqual(rc, 0)
        rendered = buf.getvalue()
        self.assertNotRegex(rendered, r'(?<![0-9A-Za-z_/.-])b[\'"]')
        payload = json.loads(rendered)
        self.assertTrue(payload["all_passed"])
        self.assertEqual(payload["status"], STATUS_VERIFIED_ANTIROLLBACK_GUARD)
        self.assertEqual(payload["otp_fuse_touches"], 0)
        self.assertEqual(payload["rpmb_counter_increments"], 0)
        self.assertEqual(payload["antirollback_brick_risk"], ZERO_USERSPACE_RAM_ONLY)
        self.assertFalse(payload["persistent_emmc_writes_authorized"])
        self.assertFalse(payload["persistent_write_release"])
        self.assertEqual(payload["physical_device_writes"], 0)
        report_file = out_dir / "antirollback-guard-report.json"
        self.assertTrue(report_file.is_file())

    def test_32_cli_verify_antirollback_guard_summary_text(self) -> None:
        buf = io.StringIO()
        with mock.patch.object(sys, "argv", ["fx3_recovery", "verify-antirollback-guard", "--clean-room"]):
            with redirect_stdout(buf):
                rc = fx3_cli.main()
        self.assertEqual(rc, 0)
        out = buf.getvalue().strip()
        self.assertIn("status=VERIFIED_ANTIROLLBACK_GUARD", out)
        self.assertIn("otp_fuse_touches=0", out)
        self.assertIn("rpmb_counter_increments=0", out)
        self.assertIn("antirollback_brick_risk=ZERO_USERSPACE_RAM_ONLY", out)
        self.assertIn("persistent_emmc_writes_authorized=False", out)
        self.assertIn("persistent_write_release=False", out)

    def test_33_json_serialization_zero_raw_bytes_repr(self) -> None:
        rep = run_antirollback_and_byof_guard_suite(force_clean_room=True)
        rendered = json.dumps(rep.to_dict(), sort_keys=True, allow_nan=False)
        self.assertNotRegex(rendered, r'(?<![0-9A-Za-z_/.-])b[\'"]')

    def test_34_suite_runtime_under_300ms(self) -> None:
        t0 = time.monotonic()
        rep = run_antirollback_and_byof_guard_suite()
        elapsed = time.monotonic() - t0
        self.assertTrue(rep.all_passed)
        self.assertLess(elapsed, 0.30)


if __name__ == "__main__":
    unittest.main()
