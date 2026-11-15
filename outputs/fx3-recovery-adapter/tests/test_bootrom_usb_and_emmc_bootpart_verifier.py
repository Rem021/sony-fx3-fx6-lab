"""Phase 124 Dual-Mode Fast Unit Tests (>=36 tests, <0.5s clean-room):

- Pillar 0: Hard-locked safety redlines, package exports, O_RDONLY donor inspection & clean-room fallback
- Pillar A: JEDEC eMMC 5.1 BOOT0/BOOT1 hardware boot-partition & EXT_CSD[179]/[177]/[173]/[226] triage
- Pillar B: CXD90057 Mask-BootROM USB 0x054C cold-plug enumeration & RAM_LOAD_ONLY XIP sandbox
- Pillar C: CLI `verify-bootrom-bootpart` & `verify-all-recovery --with-phase94 ... --with-phase124` (>=13 pillars)
"""

from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import re
import shutil
import sys
import time
import unittest
from unittest import mock

import fx3_recovery
from fx3_recovery import __main__ as fx3_cli
from fx3_recovery.bootrom_usb_and_emmc_bootpart_verifier import (
    ALLOW_BOOT_PARTITION_TARGETING,
    ALLOW_DESTRUCTIVE_FASTBOOT,
    BLOCKED_PERMANENT_BOOT_WP_FUSE_HAZARD,
    BOOT0_CORRUPTED_FAILOVER_TO_BOOT1_AVAILABLE,
    BOOTPART_SCENARIO_IDS,
    BOOTROM_SCENARIO_IDS,
    BOOTROM_USB_EMMC_BOOTPART_SCHEMA,
    BOOTROM_USB_EMMC_BOOTPART_VERSION,
    BOOTROM_VALID_TRIGGERS,
    BOOT_PART_DISABLED_DEAD_BOOT_TRAP,
    CXD90057_BOOTROM_USB_PIDS,
    CXD90057_DRAM_STAGE_B_BASE,
    CXD90057_SRAM_AWAKE_MEMADDR,
    CXD90057_SRAM_LOADER_ENTRY,
    DONOR_FX3_LOADER_NOR_BIN_RELPATH,
    DONOR_FX3_LOADER_NOR_TAR_RELPATH,
    DONOR_FX3_PARTINF_CONF_RELPATH,
    DONOR_FX3_PFORMAT_CONFIG_RELPATH,
    DONOR_FX6_LOADER_NOR_TAR_RELPATH,
    DONOR_FX6_PARTINF_CONF_RELPATH,
    EMMC_BOOT_PARTITION_BYTES,
    EMMC_EXT_CSD_BYTES,
    EMMC_PERSISTENT_PROGRAM_COMMANDS,
    ERR_BOOTPART_BOOT_SIZE_MULT_MISMATCH,
    ERR_BOOTPART_BOTH_CORRUPTED_MASK_BOOTROM_REQUIRED,
    ERR_BOOTPART_CROSS_SKU_TRANSPLANT,
    ERR_BOOTPART_EXT_CSD_BAD_LENGTH,
    ERR_BOOTPART_INVALID_BOOT_BUS_CONDITIONS,
    ERR_BOOTPART_RESERVED_PART_CONFIG_BITS,
    ERR_BOOTROM_CROSS_SKU_PAYLOAD_REJECTED,
    ERR_BOOTROM_INVALID_BULK_ENDPOINTS,
    ERR_BOOTROM_INVALID_RAM_XIP_WINDOW,
    ERR_BOOTROM_NON_RAM_LOAD_MODE_FORBIDDEN,
    ERR_BOOTROM_NON_SONY_USB_VID,
    ERR_BOOTROM_PERSISTENT_PROGRAM_COMMAND_FORBIDDEN,
    ERR_BOOTROM_UNRECOGNIZED_TRIGGER,
    ERR_BOOTROM_UNSUPPORTED_PID,
    EXT_CSD_BOOT_WP_PERM_EN_BIT2,
    EXT_CSD_BOOT_WP_PERM_EN_BIT6,
    FORBIDDEN_BOOTROM_PROGRAM_VERBS,
    FX3_DEFAULT_BOOT_BUS_CONDITIONS,
    FX3_DEFAULT_PART_CONFIG,
    OTP_FUSE_TOUCHES,
    PARTITION_ACCESS_NONZERO_LEAK,
    PASSIVE_TX_BYTES_EMITTED,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHYSICAL_DEVICE_WRITES,
    PINNED_FX3_LOADER_NOR_BIN_BYTES,
    PINNED_FX3_LOADER_NOR_BIN_SHA256,
    PINNED_FX3_LOADER_NOR_TAR_SHA256,
    PINNED_FX3_PARTINF_CONF_SHA256,
    PINNED_FX3_PFORMAT_CONFIG_SHA256,
    PINNED_FX6_INTERNAL_LOADER_NOR_BIN_BYTES,
    PINNED_FX6_INTERNAL_LOADER_NOR_BIN_SHA256,
    PINNED_FX6_LOADER_NOR_TAR_SHA256,
    PINNED_FX6_PARTINF_CONF_SHA256,
    RAM_LOAD_ONLY,
    READ_ONLY_DONOR_ACCESS,
    SONY_USB_VENDOR_ID,
    STATUS_BLOCKED_BOOT_WP_FUSE_HAZARD,
    STATUS_EMMC_BOOT0_FAILOVER_TO_BOOT1,
    STATUS_EMMC_BOOTPART_REJECTED,
    STATUS_FAIL_BOOTROM_BOOTPART_GATE,
    STATUS_REJECTED_BOOTROM_SANDBOX,
    STATUS_VERIFIED_BOOTROM_BOOTPART_GATE,
    STATUS_VERIFIED_BOOTROM_RAM_LOAD_ONLY,
    STATUS_VERIFIED_EMMC_BOOTPART_HEALTHY,
    BootromPayloadStageRequest,
    BootromUsbAndEmmcBootpartSuiteReport,
    UsbDeviceDescriptorSpec,
    audit_boot_wp_script_or_profile,
    build_synthetic_boot_partition_image,
    build_synthetic_ext_csd_boot_config,
    inspect_bootrom_and_bootpart_donors_readonly,
    parse_ext_csd_boot_config,
    run_bootrom_usb_5_scenario_sandbox,
    run_bootrom_usb_and_emmc_bootpart_suite,
    run_emmc_bootpart_6_scenario_triage,
    triage_emmc_boot_partitions_and_ext_csd,
    verify_bootrom_usb_coldplug_and_ram_sandbox,
)
from fx3_recovery.files import is_forced_clean_room, resolve_donor_path

ROOT = Path(__file__).resolve().parents[3]
RAW_BYTES_RE = r'(?<![0-9A-Za-z_/.-])b[\'"]'


class TestBootromUsbAndEmmcBootpartVerifier(unittest.TestCase):
    """40 dual-mode tests covering Phase 124 Mask-BootROM USB, eMMC BOOT0/BOOT1, & 13-pillar master suite."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.suite_report = run_bootrom_usb_and_emmc_bootpart_suite()
        cls.clean_report = run_bootrom_usb_and_emmc_bootpart_suite(force_clean_room=True)

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
        self.assertEqual(PASSIVE_TX_BYTES_EMITTED, 0)
        self.assertEqual(PHYSICAL_DEVICE_WRITES, 0)
        self.assertEqual(EMMC_PERSISTENT_PROGRAM_COMMANDS, 0)
        self.assertEqual(BOOTROM_USB_EMMC_BOOTPART_SCHEMA, "fx3-bootrom-usb-and-emmc-bootpart-verifier-v1")
        self.assertEqual(BOOTROM_USB_EMMC_BOOTPART_VERSION, "1.0.0")

    def test_02_package_exports_preserve_prior_symbols_and_expose_phase124(self) -> None:
        expected_symbols = (
            "run_bootrom_usb_and_emmc_bootpart_suite",
            "run_emmc_bootpart_6_scenario_triage",
            "run_bootrom_usb_5_scenario_sandbox",
            "inspect_bootrom_and_bootpart_donors_readonly",
            "parse_ext_csd_boot_config",
            "audit_boot_wp_script_or_profile",
            "triage_emmc_boot_partitions_and_ext_csd",
            "verify_bootrom_usb_coldplug_and_ram_sandbox",
            "BOOT_PART_DISABLED_DEAD_BOOT_TRAP",
            "BOOT0_CORRUPTED_FAILOVER_TO_BOOT1_AVAILABLE",
            "BLOCKED_PERMANENT_BOOT_WP_FUSE_HAZARD",
            "PARTITION_ACCESS_NONZERO_LEAK",
            "RAM_LOAD_ONLY",
            "DonorArtifactDigest",
            "SquashfsWbiDonorArtifactDigest",
            "BootromBootpartDonorArtifactDigest",
            "run_recovery_master_suite",
            "run_squashfs_and_hibdrv_wbi_suite",
        )
        for sym in expected_symbols:
            self.assertIn(sym, fx3_recovery.__all__)
            self.assertTrue(hasattr(fx3_recovery, sym), f"Missing export: {sym}")

    def test_03_clean_room_donor_snapshot_uses_pinned_anchors(self) -> None:
        snap = inspect_bootrom_and_bootpart_donors_readonly(force_clean_room=True)
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(snap.read_only_access)
        self.assertTrue(snap.cross_sku_loader_distinct)
        self.assertEqual(snap.fx3_loader_nor_bin_bytes, PINNED_FX3_LOADER_NOR_BIN_BYTES)
        self.assertEqual(snap.fx3_loader_nor_bin_sha256, PINNED_FX3_LOADER_NOR_BIN_SHA256)
        self.assertEqual(snap.fx3_pformat_config_sha256, PINNED_FX3_PFORMAT_CONFIG_SHA256)
        self.assertEqual(snap.fx3_loader_nor_tar_sha256, PINNED_FX3_LOADER_NOR_TAR_SHA256)
        self.assertEqual(snap.fx6_loader_nor_tar_sha256, PINNED_FX6_LOADER_NOR_TAR_SHA256)
        self.assertEqual(snap.fx6_internal_loader_nor_bin_bytes, PINNED_FX6_INTERNAL_LOADER_NOR_BIN_BYTES)
        self.assertEqual(snap.fx6_internal_loader_nor_bin_sha256, PINNED_FX6_INTERNAL_LOADER_NOR_BIN_SHA256)
        self.assertEqual(snap.fx3_partinf_conf_sha256, PINNED_FX3_PARTINF_CONF_SHA256)
        self.assertEqual(snap.fx6_partinf_conf_sha256, PINNED_FX6_PARTINF_CONF_SHA256)
        self.assertEqual(len(snap.artifacts), 6)

    def test_04_active_donor_mode_o_rdonly_matches_pinned_or_falls_back(self) -> None:
        donor_paths = [
            resolve_donor_path(rel, require_file=True)
            for rel in (
                DONOR_FX3_LOADER_NOR_BIN_RELPATH,
                DONOR_FX3_PFORMAT_CONFIG_RELPATH,
                DONOR_FX3_LOADER_NOR_TAR_RELPATH,
                DONOR_FX6_LOADER_NOR_TAR_RELPATH,
                DONOR_FX3_PARTINF_CONF_RELPATH,
                DONOR_FX6_PARTINF_CONF_RELPATH,
            )
        ]
        if (not is_forced_clean_room()) and all(p.is_file() for p in donor_paths):
            self.assertEqual(self.suite_report.verification_mode, "LOCAL_DONOR_O_RDONLY")
            self.assertEqual(
                self.suite_report.donor_snapshot.fx3_loader_nor_bin_sha256,
                self.clean_report.donor_snapshot.fx3_loader_nor_bin_sha256,
            )
            self.assertEqual(
                self.suite_report.donor_snapshot.fx6_internal_loader_nor_bin_sha256,
                self.clean_report.donor_snapshot.fx6_internal_loader_nor_bin_sha256,
            )
        else:
            self.assertEqual(self.suite_report.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(self.suite_report.all_passed)
        self.assertTrue(self.clean_report.all_passed)

    def test_05_clean_room_suite_completes_under_half_second(self) -> None:
        t0 = time.monotonic()
        rep = run_bootrom_usb_and_emmc_bootpart_suite(force_clean_room=True)
        elapsed = time.monotonic() - t0
        self.assertTrue(rep.all_passed)
        self.assertLess(elapsed, 0.5)

    def test_06_clean_room_fallback_does_not_open_donor_files(self) -> None:
        with mock.patch("fx3_recovery.files.os.open") as m_open:
            m_open.side_effect = OSError("sentinel stop")
            snap = inspect_bootrom_and_bootpart_donors_readonly(force_clean_room=True)
            self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            m_open.assert_not_called()

    # ------------------------------------------------------------------
    # Pillar A — JEDEC eMMC 5.1 BOOT0/BOOT1 & EXT_CSD Anti-Corruption Triage
    # ------------------------------------------------------------------

    def test_07_ext_csd_valid_boot0_and_boot1_configs_parse_cleanly(self) -> None:
        for part_cfg, target in ((FX3_DEFAULT_PART_CONFIG, "BOOT0"), (0x50, "BOOT1")):
            buf = build_synthetic_ext_csd_boot_config(
                part_config=part_cfg,
                boot_bus_conditions=FX3_DEFAULT_BOOT_BUS_CONDITIONS,
                boot_wp=0x00,
            )
            self.assertEqual(len(buf), EMMC_EXT_CSD_BYTES)
            view, codes, errs = parse_ext_csd_boot_config(buf)
            self.assertEqual(codes, [])
            self.assertEqual(errs, [])
            self.assertIsNotNone(view)
            assert view is not None
            self.assertEqual(view.boot_partition_target, target)
            self.assertEqual(view.partition_access, 0)
            self.assertEqual(view.boot_ack, 1)
            self.assertEqual(view.boot_partition_capacity_bytes, EMMC_BOOT_PARTITION_BYTES)
            self.assertFalse(view.boot_perm_wp_asserted)

    def test_08_ext_csd_rejects_bad_length(self) -> None:
        view, codes, _ = parse_ext_csd_boot_config(bytes(256))
        self.assertIsNone(view)
        self.assertIn(ERR_BOOTPART_EXT_CSD_BAD_LENGTH, codes)

    def test_09_ext_csd_detects_boot_part_disabled_dead_boot_trap(self) -> None:
        for boot_en in (0x0, 0x3, 0x4, 0x5, 0x6, 0x7):
            part_cfg = 0x40 | (boot_en << 3)
            buf = build_synthetic_ext_csd_boot_config(part_config=part_cfg)
            view, codes, _ = parse_ext_csd_boot_config(buf)
            self.assertIsNotNone(view)
            self.assertIn(BOOT_PART_DISABLED_DEAD_BOOT_TRAP, codes)

    def test_10_ext_csd_detects_partition_access_nonzero_leak(self) -> None:
        for access in (0x1, 0x2, 0x3, 0x7):
            part_cfg = 0x48 | access
            buf = build_synthetic_ext_csd_boot_config(part_config=part_cfg)
            view, codes, _ = parse_ext_csd_boot_config(buf)
            self.assertIsNotNone(view)
            self.assertIn(PARTITION_ACCESS_NONZERO_LEAK, codes)
            assert view is not None
            self.assertEqual(view.partition_access, access)

    def test_11_ext_csd_detects_invalid_boot_bus_conditions_and_reserved_bit7(self) -> None:
        # Invalid boot_bus_conditions width=3, mode=3, reserved bits
        for bad_bus in (0x03, 0x18, 0x20):
            _, codes, _ = parse_ext_csd_boot_config(build_synthetic_ext_csd_boot_config(boot_bus_conditions=bad_bus))
            self.assertIn(ERR_BOOTPART_INVALID_BOOT_BUS_CONDITIONS, codes)

        # Reserved bit 7 in PART_CONFIG
        _, codes_rsv, _ = parse_ext_csd_boot_config(build_synthetic_ext_csd_boot_config(part_config=0xC8))
        self.assertIn(ERR_BOOTPART_RESERVED_PART_CONFIG_BITS, codes_rsv)

    def test_12_ext_csd_rejects_boot_size_mult_mismatch(self) -> None:
        _, codes, _ = parse_ext_csd_boot_config(build_synthetic_ext_csd_boot_config(boot_size_mult=16))
        self.assertIn(ERR_BOOTPART_BOOT_SIZE_MULT_MISMATCH, codes)

    def test_13_ext_csd_blocks_permanent_boot_wp_bit2_and_bit6_fuse_hazard(self) -> None:
        for wp_byte in (EXT_CSD_BOOT_WP_PERM_EN_BIT2, EXT_CSD_BOOT_WP_PERM_EN_BIT6, 0x44):
            buf = build_synthetic_ext_csd_boot_config(part_config=0x48, boot_wp=wp_byte)
            view, codes, _ = parse_ext_csd_boot_config(buf)
            self.assertIsNotNone(view)
            assert view is not None
            self.assertTrue(view.boot_perm_wp_asserted)
            self.assertIn(BLOCKED_PERMANENT_BOOT_WP_FUSE_HAZARD, codes)

    def test_14_boot_wp_firewall_blocks_perm_scripts_and_mutations(self) -> None:
        for cmd, wp in (
            ("mmc writeprotect boot set /dev/mmcblk0boot0 -p", 0x00),
            ("ext_csd[173] B_PERM_WP_EN", 0x00),
            ("mmc switch 173 0x04", 0x04),
            ("profile_ext_csd_173", EXT_CSD_BOOT_WP_PERM_EN_BIT6),
        ):
            dec = audit_boot_wp_script_or_profile(cmd, ext_csd_boot_wp=wp)
            self.assertFalse(dec.allowed)
            self.assertEqual(dec.status, STATUS_BLOCKED_BOOT_WP_FUSE_HAZARD)
            self.assertIn(BLOCKED_PERMANENT_BOOT_WP_FUSE_HAZARD, dec.error_codes)
            self.assertEqual(dec.physical_device_writes, 0)

        # Read-only mutation verb without -p still blocked by read-only safety lock
        mut = audit_boot_wp_script_or_profile("mmc bootpart enable 1 1 /dev/mmcblk0")
        self.assertFalse(mut.allowed)
        self.assertEqual(mut.physical_device_writes, 0)

        # Pure read-only audit allowed with zero writes
        ro = audit_boot_wp_script_or_profile("readonly_ext_csd_inspect")
        self.assertTrue(ro.allowed)
        self.assertEqual(ro.physical_device_writes, 0)

    def test_15_triage_healthy_boot0_and_boot1_passes_with_zero_writes(self) -> None:
        _, b0 = build_synthetic_boot_partition_image(partition_name="BOOT0")
        _, b1 = build_synthetic_boot_partition_image(partition_name="BOOT1")
        rep = triage_emmc_boot_partitions_and_ext_csd(
            build_synthetic_ext_csd_boot_config(),
            b0,
            b1,
            scenario_id="TEST_HEALTHY",
        )
        self.assertTrue(rep.passed)
        self.assertEqual(rep.status, STATUS_VERIFIED_EMMC_BOOTPART_HEALTHY)
        self.assertTrue(rep.boot0_intact)
        self.assertTrue(rep.boot1_intact)
        self.assertFalse(rep.dead_boot_trap_detected)
        self.assertFalse(rep.failover_to_boot1_available)
        self.assertFalse(rep.permanent_boot_wp_hazard_detected)
        self.assertFalse(rep.partition_access_nonzero_leak)
        self.assertFalse(rep.mask_bootrom_fallback_required)
        self.assertEqual(rep.physical_device_writes, 0)

    def test_16_triage_detects_boot0_corrupted_failover_to_boot1_available(self) -> None:
        _, corrupt_b0 = build_synthetic_boot_partition_image(partition_name="BOOT0", corrupt_payload=True)
        _, erased_b0 = build_synthetic_boot_partition_image(partition_name="BOOT0", blank_fill=0xFF)
        _, healthy_b1 = build_synthetic_boot_partition_image(partition_name="BOOT1")

        for bad_slot in (corrupt_b0, erased_b0):
            rep = triage_emmc_boot_partitions_and_ext_csd(
                build_synthetic_ext_csd_boot_config(part_config=0x48),
                bad_slot,
                healthy_b1,
                scenario_id="TEST_FAILOVER",
            )
            self.assertFalse(rep.passed)
            self.assertEqual(rep.status, STATUS_EMMC_BOOT0_FAILOVER_TO_BOOT1)
            self.assertTrue(rep.failover_to_boot1_available)
            self.assertFalse(rep.mask_bootrom_fallback_required)
            self.assertIn(BOOT0_CORRUPTED_FAILOVER_TO_BOOT1_AVAILABLE, rep.error_codes)
            self.assertEqual(rep.physical_device_writes, 0)

    def test_17_triage_detects_dual_corruption_requiring_mask_bootrom_fallback(self) -> None:
        _, corrupt_b0 = build_synthetic_boot_partition_image(partition_name="BOOT0", corrupt_payload=True)
        _, corrupt_b1 = build_synthetic_boot_partition_image(partition_name="BOOT1", corrupt_payload=True)
        rep = triage_emmc_boot_partitions_and_ext_csd(
            build_synthetic_ext_csd_boot_config(part_config=0x48),
            corrupt_b0,
            corrupt_b1,
            scenario_id="TEST_DUAL_CORRUPT",
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.status, STATUS_EMMC_BOOTPART_REJECTED)
        self.assertTrue(rep.mask_bootrom_fallback_required)
        self.assertIn(ERR_BOOTPART_BOTH_CORRUPTED_MASK_BOOTROM_REQUIRED, rep.error_codes)
        self.assertEqual(rep.recommended_action, "ENTER_CXD90057_MASK_BOOTROM_USB_054C_RAM_LOAD_ONLY_SANDBOX")

    def test_18_triage_rejects_cross_sku_fx6_boot_partition_slot(self) -> None:
        _, fx6_b0 = build_synthetic_boot_partition_image(partition_name="BOOT0", sku_code="ILME-FX6")
        _, fx3_b1 = build_synthetic_boot_partition_image(partition_name="BOOT1", sku_code="ILME-FX3")
        rep = triage_emmc_boot_partitions_and_ext_csd(
            build_synthetic_ext_csd_boot_config(part_config=0x48),
            fx6_b0,
            fx3_b1,
        )
        self.assertFalse(rep.passed)
        self.assertIn(ERR_BOOTPART_CROSS_SKU_TRANSPLANT, rep.error_codes)

    def test_19_triage_perm_wp_hazard_overrides_status_and_blocks_immediately(self) -> None:
        _, b0 = build_synthetic_boot_partition_image(partition_name="BOOT0")
        _, b1 = build_synthetic_boot_partition_image(partition_name="BOOT1")
        rep = triage_emmc_boot_partitions_and_ext_csd(
            build_synthetic_ext_csd_boot_config(part_config=0x48, boot_wp=EXT_CSD_BOOT_WP_PERM_EN_BIT6),
            b0,
            b1,
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.status, STATUS_BLOCKED_BOOT_WP_FUSE_HAZARD)
        self.assertTrue(rep.permanent_boot_wp_hazard_detected)
        self.assertIn(BLOCKED_PERMANENT_BOOT_WP_FUSE_HAZARD, rep.error_codes)

    def test_20_emmc_bootpart_6_scenario_suite_all_green(self) -> None:
        res = run_emmc_bootpart_6_scenario_triage()
        self.assertTrue(res.passed, f"Bootpart 6-scenario errors: {res.errors}")
        self.assertEqual(res.scenarios_passed, 6)
        self.assertEqual(res.scenarios_total, 6)
        self.assertEqual([r.scenario_id for r in res.scenario_results], list(BOOTPART_SCENARIO_IDS))
        self.assertFalse(res.wp_bit2_firewall.allowed)
        self.assertFalse(res.wp_bit6_firewall.allowed)
        self.assertFalse(res.wp_script_firewall.allowed)

    # ------------------------------------------------------------------
    # Pillar B — CXD90057 Mask-BootROM USB 0x054C & RAM_LOAD_ONLY Sandbox
    # ------------------------------------------------------------------

    def test_21_bootrom_usb_accepts_valid_sram_and_dram_ram_load_only(self) -> None:
        for pid in CXD90057_BOOTROM_USB_PIDS:
            for trig in BOOTROM_VALID_TRIGGERS:
                rep_sram = verify_bootrom_usb_coldplug_and_ram_sandbox(
                    UsbDeviceDescriptorSpec(vid=SONY_USB_VENDOR_ID, pid=pid, trigger_reason=trig),
                    BootromPayloadStageRequest(
                        payload_name="fx3_sram_loader",
                        target_mode=RAM_LOAD_ONLY,
                        load_address=CXD90057_SRAM_AWAKE_MEMADDR,
                        entry_address=CXD90057_SRAM_LOADER_ENTRY,
                        payload_size=PINNED_FX3_LOADER_NOR_BIN_BYTES,
                    ),
                )
                self.assertTrue(rep_sram.passed, f"pid=0x{pid:04x} trig={trig} failed: {rep_sram.errors}")
                self.assertEqual(rep_sram.status, STATUS_VERIFIED_BOOTROM_RAM_LOAD_ONLY)
                self.assertEqual(rep_sram.memory_region, "SRAM_XIP")
                self.assertTrue(rep_sram.cold_plug_authenticated)
                self.assertTrue(rep_sram.ram_load_only_verified)
                self.assertEqual(rep_sram.emmc_persistent_program_commands, 0)
                self.assertEqual(rep_sram.physical_device_writes, 0)

        rep_dram = verify_bootrom_usb_coldplug_and_ram_sandbox(
            UsbDeviceDescriptorSpec(trigger_reason="LAB_TEST_PAD_STRAP_SIMULATION"),
            BootromPayloadStageRequest(
                payload_name="stage_b_dram_kernel",
                target_mode=RAM_LOAD_ONLY,
                load_address=CXD90057_DRAM_STAGE_B_BASE,
                entry_address=CXD90057_DRAM_STAGE_B_BASE + 0x100,
                payload_size=6_610_952,
            ),
        )
        self.assertTrue(rep_dram.passed)
        self.assertEqual(rep_dram.memory_region, "DRAM_XIP")

    def test_22_bootrom_usb_rejects_non_sony_vid(self) -> None:
        rep = verify_bootrom_usb_coldplug_and_ram_sandbox(
            UsbDeviceDescriptorSpec(vid=0x18D1, pid=0x0C90),
            BootromPayloadStageRequest(payload_name="loader"),
        )
        self.assertFalse(rep.passed)
        self.assertFalse(rep.cold_plug_authenticated)
        self.assertEqual(rep.status, STATUS_REJECTED_BOOTROM_SANDBOX)
        self.assertIn(ERR_BOOTROM_NON_SONY_USB_VID, rep.error_codes)

    def test_23_bootrom_usb_rejects_unsupported_pid(self) -> None:
        rep = verify_bootrom_usb_coldplug_and_ram_sandbox(
            UsbDeviceDescriptorSpec(vid=SONY_USB_VENDOR_ID, pid=0xDEAD),
            BootromPayloadStageRequest(payload_name="loader"),
        )
        self.assertFalse(rep.passed)
        self.assertIn(ERR_BOOTROM_UNSUPPORTED_PID, rep.error_codes)

    def test_24_bootrom_usb_rejects_invalid_bulk_endpoints_and_packet_size(self) -> None:
        for bad_in, bad_out, bad_mps in ((0x01, 0x01, 512), (0x81, 0x82, 512), (0x81, 0x01, 256)):
            rep = verify_bootrom_usb_coldplug_and_ram_sandbox(
                UsbDeviceDescriptorSpec(bulk_in_ep=bad_in, bulk_out_ep=bad_out, max_packet_size=bad_mps),
                BootromPayloadStageRequest(payload_name="loader"),
            )
            self.assertFalse(rep.passed)
            self.assertFalse(rep.bulk_endpoints_valid)
            self.assertIn(ERR_BOOTROM_INVALID_BULK_ENDPOINTS, rep.error_codes)

    def test_25_bootrom_usb_rejects_unrecognized_trigger(self) -> None:
        rep = verify_bootrom_usb_coldplug_and_ram_sandbox(
            UsbDeviceDescriptorSpec(trigger_reason="ARBITRARY_UNATTENDED_FLASH"),
            BootromPayloadStageRequest(payload_name="loader"),
        )
        self.assertFalse(rep.passed)
        self.assertIn(ERR_BOOTROM_UNRECOGNIZED_TRIGGER, rep.error_codes)

    def test_26_bootrom_usb_rejects_non_ram_load_mode(self) -> None:
        for mode in ("EMMC_BOOT0_PROGRAM", "PERSISTENT_NOR_FLASH", "FASTBOOT_FLASH"):
            rep = verify_bootrom_usb_coldplug_and_ram_sandbox(
                UsbDeviceDescriptorSpec(),
                BootromPayloadStageRequest(payload_name="writer", target_mode=mode),
            )
            self.assertFalse(rep.passed)
            self.assertFalse(rep.ram_load_only_verified)
            self.assertIn(ERR_BOOTROM_NON_RAM_LOAD_MODE_FORBIDDEN, rep.error_codes)
            self.assertEqual(rep.emmc_persistent_program_commands, 0)

    def test_27_bootrom_usb_blocks_all_forbidden_persistent_program_verbs(self) -> None:
        for verb in FORBIDDEN_BOOTROM_PROGRAM_VERBS:
            rep = verify_bootrom_usb_coldplug_and_ram_sandbox(
                UsbDeviceDescriptorSpec(),
                BootromPayloadStageRequest(
                    payload_name="blocked_cmd",
                    commands=("USB_COLD_PLUG_ENUMERATE", f"exec_{verb}"),
                ),
            )
            self.assertFalse(rep.passed)
            self.assertIn(ERR_BOOTROM_PERSISTENT_PROGRAM_COMMAND_FORBIDDEN, rep.error_codes)
            self.assertEqual(rep.emmc_persistent_program_commands, 0)
            self.assertEqual(rep.physical_device_writes, 0)

    def test_28_bootrom_usb_rejects_out_of_window_sram_dram_or_bad_entry(self) -> None:
        for load_addr, entry_addr, size in (
            (0x00000000, 0x00000100, 4096),  # BootROM / Flash space, not SRAM/DRAM
            (CXD90057_SRAM_AWAKE_MEMADDR, 0xFE040000, 1024),  # entry outside payload
            (CXD90057_DRAM_STAGE_B_BASE, CXD90057_DRAM_STAGE_B_BASE, 0),  # zero size
        ):
            rep = verify_bootrom_usb_coldplug_and_ram_sandbox(
                UsbDeviceDescriptorSpec(),
                BootromPayloadStageRequest(
                    payload_name="bad_xip",
                    load_address=load_addr,
                    entry_address=entry_addr,
                    payload_size=size,
                ),
            )
            self.assertFalse(rep.passed)
            self.assertIn(ERR_BOOTROM_INVALID_RAM_XIP_WINDOW, rep.error_codes)

    def test_29_bootrom_usb_rejects_cross_sku_fx6_payload(self) -> None:
        rep = verify_bootrom_usb_coldplug_and_ram_sandbox(
            UsbDeviceDescriptorSpec(),
            BootromPayloadStageRequest(
                payload_name="fx6_loader",
                sku_code="ILME-FX6",
                payload_size=PINNED_FX6_INTERNAL_LOADER_NOR_BIN_BYTES,
                payload_sha256=PINNED_FX6_INTERNAL_LOADER_NOR_BIN_SHA256,
            ),
        )
        self.assertFalse(rep.passed)
        self.assertIn(ERR_BOOTROM_CROSS_SKU_PAYLOAD_REJECTED, rep.error_codes)

    def test_30_bootrom_usb_5_scenario_sandbox_all_green(self) -> None:
        res = run_bootrom_usb_5_scenario_sandbox()
        self.assertTrue(res.passed, f"BootROM 5-scenario errors: {res.errors}")
        self.assertEqual(res.scenarios_passed, 5)
        self.assertEqual(res.scenarios_total, 5)
        self.assertEqual([r.scenario_id for r in res.scenario_results], list(BOOTROM_SCENARIO_IDS))
        self.assertEqual(res.emmc_persistent_program_commands, 0)

    def test_31_bootrom_and_bootpart_scenario_reports_to_dict_serializable(self) -> None:
        bp_dict = self.clean_report.emmc_bootpart_6_scenario_suite.to_dict()
        br_dict = self.clean_report.bootrom_usb_5_scenario_suite.to_dict()
        self.assertEqual(bp_dict["scenarios_passed"], 6)
        self.assertEqual(br_dict["scenarios_passed"], 5)
        self.assertEqual(br_dict["emmc_persistent_program_commands"], 0)

    # ------------------------------------------------------------------
    # Pillar C — Master Suite Determinism, CLI & >=13-Pillar Integration
    # ------------------------------------------------------------------

    def test_32_clean_room_suite_sha256_is_deterministic(self) -> None:
        r2 = run_bootrom_usb_and_emmc_bootpart_suite(force_clean_room=True)
        self.assertEqual(self.clean_report.suite_sha256, r2.suite_sha256)
        self.assertEqual(
            self.clean_report.emmc_bootpart_6_scenario_suite.suite_sha256,
            r2.emmc_bootpart_6_scenario_suite.suite_sha256,
        )
        self.assertEqual(
            self.clean_report.bootrom_usb_5_scenario_suite.suite_sha256,
            r2.bootrom_usb_5_scenario_suite.suite_sha256,
        )

    def test_33_json_serialization_no_raw_bytes_and_no_nan(self) -> None:
        rendered = json.dumps(self.suite_report.to_dict(), ensure_ascii=False, sort_keys=True, allow_nan=False)
        self.assertNotRegex(rendered, RAW_BYTES_RE)
        decoded = json.loads(rendered)
        self.assertEqual(decoded["suite_sha256"], self.suite_report.suite_sha256)
        self.assertEqual(decoded["emmc_persistent_program_commands"], 0)
        self.assertEqual(decoded["physical_device_writes"], 0)
        self.assertEqual(decoded["otp_fuse_touches"], 0)
        self.assertEqual(decoded["passive_tx_bytes_emitted"], 0)
        self.assertFalse(decoded["persistent_emmc_writes_authorized"])
        self.assertFalse(decoded["persistent_write_release"])

    def test_34_cli_verify_bootrom_bootpart_clean_room_json_and_text(self) -> None:
        buf_json = io.StringIO()
        with (
            mock.patch.object(sys, "argv", ["fx3_recovery", "verify-bootrom-bootpart", "--clean-room", "--json"]),
            redirect_stdout(buf_json),
        ):
            rc_json = fx3_cli.main()
        self.assertEqual(rc_json, 0)
        rendered = buf_json.getvalue()
        self.assertNotRegex(rendered, RAW_BYTES_RE)
        parsed = json.loads(rendered)
        self.assertEqual(parsed["status"], STATUS_VERIFIED_BOOTROM_BOOTPART_GATE)
        self.assertEqual(parsed["verification_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(parsed["emmc_persistent_program_commands"], 0)

        buf_txt = io.StringIO()
        with (
            mock.patch.object(sys, "argv", ["fx3_recovery", "verify-bootrom-bootpart", "--clean-room"]),
            redirect_stdout(buf_txt),
        ):
            rc_txt = fx3_cli.main()
        self.assertEqual(rc_txt, 0)
        txt = buf_txt.getvalue()
        self.assertIn("status=VERIFIED_BOOTROM_USB_AND_EMMC_BOOTPART_GATE", txt)
        self.assertIn("bootpart_scenarios=6/6", txt)
        self.assertIn("bootrom_scenarios=5/5", txt)
        self.assertIn("emmc_persistent_program_commands=0", txt)

    def test_35_cli_verify_bootrom_bootpart_active_mode(self) -> None:
        buf = io.StringIO()
        with (
            mock.patch.object(sys, "argv", ["fx3_recovery", "verify-bootrom-bootpart", "--json"]),
            redirect_stdout(buf),
        ):
            rc = fx3_cli.main()
        self.assertEqual(rc, 0)
        rendered = buf.getvalue()
        self.assertNotRegex(rendered, RAW_BYTES_RE)
        parsed = json.loads(rendered)
        self.assertTrue(parsed["all_passed"])
        self.assertIn(parsed["verification_mode"], ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"))

    def test_36_cli_verify_bootrom_bootpart_out_writes_artifact(self) -> None:
        scratch_root = ROOT / "work" / "_tests" / "phase124_cli_out"
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
                        "verify-bootrom-bootpart",
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
            out_file = scratch_root / "bootrom-bootpart-report.json"
            self.assertTrue(out_file.is_file())
            written = json.loads(out_file.read_text(encoding="utf-8"))
            self.assertEqual(written["status"], STATUS_VERIFIED_BOOTROM_BOOTPART_GATE)
            self.assertEqual(written["emmc_persistent_program_commands"], 0)
        finally:
            if scratch_root.exists():
                shutil.rmtree(scratch_root)

    def test_37_cli_verify_bootrom_bootpart_failure_returns_exit_2(self) -> None:
        failing = BootromUsbAndEmmcBootpartSuiteReport(
            **{**self.clean_report.__dict__, "all_passed": False, "status": STATUS_FAIL_BOOTROM_BOOTPART_GATE}
        )
        with mock.patch("fx3_recovery.__main__.run_bootrom_usb_and_emmc_bootpart_suite", return_value=failing):
            buf = io.StringIO()
            with (
                mock.patch.object(sys, "argv", ["fx3_recovery", "verify-bootrom-bootpart", "--clean-room", "--json"]),
                redirect_stdout(buf),
            ):
                rc = fx3_cli.main()
            self.assertEqual(rc, 2)
            parsed = json.loads(buf.getvalue())
            self.assertFalse(parsed["all_passed"])
            self.assertEqual(parsed["status"], STATUS_FAIL_BOOTROM_BOOTPART_GATE)

    def test_38_cli_verify_all_recovery_13_pillars_clean_room_and_failure_propagation(self) -> None:
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
        self.assertGreaterEqual(parsed["pillar_count"], 13)
        self.assertEqual(parsed["pillars_passed"], parsed["pillar_count"])
        self.assertIn("phase124_pillar13_bootrom_usb_emmc_bootpart", parsed)
        self.assertEqual(
            parsed["phase124_pillar13_bootrom_usb_emmc_bootpart"]["status"],
            STATUS_VERIFIED_BOOTROM_BOOTPART_GATE,
        )

        failing = BootromUsbAndEmmcBootpartSuiteReport(
            **{**self.clean_report.__dict__, "all_passed": False, "status": STATUS_FAIL_BOOTROM_BOOTPART_GATE}
        )
        with mock.patch("fx3_recovery.__main__.run_bootrom_usb_and_emmc_bootpart_suite", return_value=failing):
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
                        "--json",
                    ],
                ),
                redirect_stdout(buf_fail),
            ):
                rc_fail = fx3_cli.main()
            self.assertEqual(rc_fail, 2)
            parsed_fail = json.loads(buf_fail.getvalue())
            self.assertFalse(parsed_fail["all_passed"])
            self.assertGreaterEqual(parsed_fail["pillar_count"], 13)
            self.assertEqual(parsed_fail["pillars_passed"], parsed_fail["pillar_count"] - 1)

    def test_39_cli_verify_all_recovery_13_pillars_active_mode(self) -> None:
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
        self.assertGreaterEqual(parsed["pillar_count"], 13)
        self.assertEqual(parsed["pillars_passed"], parsed["pillar_count"])
        self.assertIn("phase124_pillar13_bootrom_usb_emmc_bootpart", parsed)

    def test_40_cli_verify_all_recovery_default_compat_and_text_13_pillars(self) -> None:
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
        self.assertNotIn("phase124_pillar13_bootrom_usb_emmc_bootpart", parsed_def)

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
                ],
            ),
            redirect_stdout(buf_txt),
        ):
            rc_txt = fx3_cli.main()
        self.assertEqual(rc_txt, 0)
        txt = buf_txt.getvalue()
        m = re.search(r"pillars=(\d+)/(\d+)", txt)
        self.assertIsNotNone(m)
        assert m is not None
        self.assertGreaterEqual(int(m.group(2)), 13)
        self.assertEqual(int(m.group(1)), int(m.group(2)))
        self.assertIn("physical_device_writes=0", txt)
        self.assertIn("persistent_emmc_writes_authorized=False", txt)


if __name__ == "__main__":
    unittest.main()
