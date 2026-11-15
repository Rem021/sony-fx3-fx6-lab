"""Phase 126 Dual-Mode Fast Unit Tests (40 tests, <0.5s clean-room):

- Pillar 0: Hard-locked safety redlines, package exports, O_RDONLY donor inspection & clean-room fallback
- Pillar A: Per-body factory calibration (`nvs` / `adj` / `cnflasha`) triple-copy parity,
  cross-serial donor poisoning firewall & cnflasha key-vault lock
- Pillar B: `IMX510` defect-pixel (`4264x2408`) / dual-base ISO (`800/12800`) column-ADC &
  5-axis `IBIS` Hall-zero / `-10°C..+60°C` `IMU` gyro temperature-bias table integrity verifier
- Pillar C: Master determinism, JSON hygiene, CLI `verify-factory-cal-guard` &
  `verify-all-recovery --with-phase94 ... --with-phase126` (`>= 14` pillars)
"""

from __future__ import annotations

from contextlib import redirect_stdout
from dataclasses import replace
import io
import json
import math
from pathlib import Path
import shutil
import sys
import time
import unittest
from unittest import mock

import fx3_recovery
from fx3_recovery import __main__ as fx3_cli
from fx3_recovery.factory_cal_ibis_defectpixel_and_nvs_verifier import (
    ALLOW_BOOT_PARTITION_TARGETING,
    ALLOW_DESTRUCTIVE_FASTBOOT,
    BLOCKED_CNFLASHA_KEY_VAULT_WRITE_OR_EXTRACTION,
    BLOCKED_CROSS_SERIAL_FACTORY_CAL_TRANSPLANT,
    BLOCKED_MISSING_TIER0_FACTORY_CAL_TRIPLE_PARITY,
    DONOR_FX3_APPFW_RELPATH,
    DONOR_FX3_BACKUP_KO_RELPATH,
    DONOR_FX3_CPAPP_B_RELPATH,
    DONOR_FX3_LIBBACKUP_RELPATH,
    DONOR_FX6_APPFW_RELPATH,
    DONOR_FX6_CPAPP_B_RELPATH,
    DONOR_FX6_LIBBACKUP_RELPATH,
    ERR_FACTORY_CAL_MUTATION_FORBIDDEN,
    ERR_FACTORY_CAL_SKU_MISMATCH,
    ERR_IBIS_AXES_MISMATCH,
    ERR_IBIS_HALL_ZERO_OUT_OF_RANGE,
    ERR_IBIS_IMU_CRC32_MISMATCH,
    ERR_IMU_GYRO_BIAS_POLY_OUT_OF_RANGE,
    ERR_IMU_TEMP_RANGE_COVERAGE_INVALID,
    ERR_IMX510_ADC_OFFSET_OUT_OF_RANGE,
    ERR_IMX510_CRC32_MISMATCH,
    ERR_IMX510_DUAL_ISO_CONFIG_INVALID,
    ERR_IMX510_EMPTY_OR_OVERSIZED_DEFECT_MAP,
    ERR_IMX510_NON_MONOTONIC_COORDINATES,
    ERR_IMX510_PIXEL_OUT_OF_BOUNDS,
    ERR_SENSOR_BODY_BINDING_MISMATCH,
    FACTORY_CAL_FIREWALL_SCENARIO_IDS,
    FACTORY_CAL_IBIS_NVS_SCHEMA,
    FACTORY_CAL_IBIS_NVS_VERSION,
    FACTORY_CAL_MUTATION_BYTES,
    FACTORY_CAL_PARTITIONS,
    FX3_CAL_MODEL_ID,
    FX3_CAL_SKU_CODE,
    FX6_CAL_MODEL_ID,
    FX6_CAL_SKU_CODE,
    IBIS_5_AXES,
    IMX510_ACTIVE_HEIGHT,
    IMX510_ACTIVE_WIDTH,
    IMX510_DUAL_BASE_ISOS,
    OTP_FUSE_TOUCHES,
    PASSIVE_TX_BYTES_EMITTED,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHYSICAL_DEVICE_WRITES,
    PINNED_FX3_APPFW_BYTES,
    PINNED_FX3_APPFW_SHA256,
    PINNED_FX3_BACKUP_KO_BYTES,
    PINNED_FX3_BACKUP_KO_SHA256,
    PINNED_FX3_CPAPP_B_BYTES,
    PINNED_FX3_CPAPP_B_SHA256,
    PINNED_FX3_LIBBACKUP_BYTES,
    PINNED_FX3_LIBBACKUP_SHA256,
    PINNED_FX6_APPFW_BYTES,
    PINNED_FX6_APPFW_SHA256,
    PINNED_FX6_CPAPP_B_BYTES,
    PINNED_FX6_CPAPP_B_SHA256,
    PINNED_FX6_LIBBACKUP_BYTES,
    PINNED_FX6_LIBBACKUP_SHA256,
    PRIVATE_KEY_BYTES_READ,
    READ_ONLY_DONOR_ACCESS,
    SENSOR_IBIS_SCENARIO_IDS,
    STATUS_FAIL_FACTORY_CAL_GUARD,
    STATUS_REJECTED_FACTORY_CAL_FIREWALL,
    STATUS_REJECTED_SENSOR_IBIS_CAL_TABLES,
    STATUS_VERIFIED_FACTORY_CAL_GUARD,
    STATUS_VERIFIED_FACTORY_CAL_PARITY,
    STATUS_VERIFIED_SENSOR_IBIS_CAL_TABLES,
    FactoryCalCopyDigest,
    FactoryCalIbisAndNvsSuiteReport,
    IbisAxisHallCalEntry,
    ImuGyroTempBiasPolyEntry,
    Imx510BaseIsoAdcProfile,
    Imx510DefectPixelCoord,
    audit_cnflasha_key_vault_operation,
    build_synthetic_factory_cal_identity,
    build_synthetic_factory_cal_manifest,
    build_synthetic_ibis_imu_cal_table,
    build_synthetic_imx510_cal_table,
    compute_ibis_imu_cal_crc32,
    compute_imx510_cal_crc32,
    inspect_factory_cal_and_sensor_donors_readonly,
    run_factory_cal_6_scenario_firewall,
    run_factory_cal_ibis_defectpixel_and_nvs_suite,
    run_sensor_ibis_cal_6_scenario_suite,
    verify_factory_cal_triple_parity_and_firewall,
    verify_imx510_and_ibis_cal_tables,
)
from fx3_recovery.files import is_forced_clean_room, resolve_donor_path

ROOT = Path(__file__).resolve().parents[3]
RAW_BYTES_RE = r'(?<![0-9A-Za-z_/.-])b[\'\"]'


class TestFactoryCalIbisDefectpixelAndNvsVerifier(unittest.TestCase):
    """40 dual-mode tests covering Phase 126 per-body factory-cal firewall, IMX510/IBIS tables & >=14-pillar gate."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.suite_report = run_factory_cal_ibis_defectpixel_and_nvs_suite()
        cls.clean_report = run_factory_cal_ibis_defectpixel_and_nvs_suite(force_clean_room=True)

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
        self.assertEqual(FACTORY_CAL_MUTATION_BYTES, 0)
        self.assertEqual(PRIVATE_KEY_BYTES_READ, 0)
        self.assertEqual(FACTORY_CAL_IBIS_NVS_SCHEMA, "fx3-factory-cal-ibis-defectpixel-and-nvs-verifier-v1")
        self.assertEqual(FACTORY_CAL_IBIS_NVS_VERSION, "1.0.0")

    def test_02_package_exports_preserve_prior_symbols_and_expose_phase126(self) -> None:
        expected_symbols = (
            "run_factory_cal_ibis_defectpixel_and_nvs_suite",
            "run_factory_cal_6_scenario_firewall",
            "run_sensor_ibis_cal_6_scenario_suite",
            "inspect_factory_cal_and_sensor_donors_readonly",
            "audit_cnflasha_key_vault_operation",
            "verify_factory_cal_triple_parity_and_firewall",
            "verify_imx510_and_ibis_cal_tables",
            "BLOCKED_CROSS_SERIAL_FACTORY_CAL_TRANSPLANT",
            "BLOCKED_MISSING_TIER0_FACTORY_CAL_TRIPLE_PARITY",
            "BLOCKED_CNFLASHA_KEY_VAULT_WRITE_OR_EXTRACTION",
            "IMX510_ACTIVE_WIDTH",
            "IMX510_ACTIVE_HEIGHT",
            "IMX510_DUAL_BASE_ISOS",
            "IBIS_5_AXES",
            "DonorArtifactDigest",
            "BootromBootpartDonorArtifactDigest",
            "FactoryCalDonorArtifactDigest",
            "run_recovery_master_suite",
            "run_bootrom_usb_and_emmc_bootpart_suite",
        )
        for sym in expected_symbols:
            self.assertIn(sym, fx3_recovery.__all__)
            self.assertTrue(hasattr(fx3_recovery, sym), f"Missing export: {sym}")

    def test_03_clean_room_donor_snapshot_uses_pinned_anchors(self) -> None:
        snap = inspect_factory_cal_and_sensor_donors_readonly(force_clean_room=True)
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(snap.read_only_access)
        self.assertTrue(snap.cross_sku_distinct)
        self.assertEqual(snap.fx3_libbackup_sha256, PINNED_FX3_LIBBACKUP_SHA256)
        self.assertEqual(snap.fx6_libbackup_sha256, PINNED_FX6_LIBBACKUP_SHA256)
        self.assertEqual(snap.fx3_backup_ko_sha256, PINNED_FX3_BACKUP_KO_SHA256)
        self.assertEqual(snap.fx3_appfw_sha256, PINNED_FX3_APPFW_SHA256)
        self.assertEqual(snap.fx6_appfw_sha256, PINNED_FX6_APPFW_SHA256)
        self.assertEqual(snap.fx3_cpapp_b_sha256, PINNED_FX3_CPAPP_B_SHA256)
        self.assertEqual(snap.fx6_cpapp_b_sha256, PINNED_FX6_CPAPP_B_SHA256)
        self.assertEqual(len(snap.artifacts), 7)
        by_label = {a.label: a for a in snap.artifacts}
        self.assertEqual(by_label["fx3_v702_libbackup_so"].byte_length, PINNED_FX3_LIBBACKUP_BYTES)
        self.assertEqual(by_label["fx6_v601_libbackup_so"].byte_length, PINNED_FX6_LIBBACKUP_BYTES)
        self.assertEqual(by_label["fx3_v702_backup_ko"].byte_length, PINNED_FX3_BACKUP_KO_BYTES)
        self.assertEqual(by_label["fx3_v702_appfw_so"].byte_length, PINNED_FX3_APPFW_BYTES)
        self.assertEqual(by_label["fx6_v601_appfw_so"].byte_length, PINNED_FX6_APPFW_BYTES)
        self.assertEqual(by_label["fx3_v702_cpapp_b_bin"].byte_length, PINNED_FX3_CPAPP_B_BYTES)
        self.assertEqual(by_label["fx6_v601_cpapp_b_bin"].byte_length, PINNED_FX6_CPAPP_B_BYTES)

    def test_04_active_donor_mode_o_rdonly_matches_pinned_or_falls_back(self) -> None:
        donor_paths = [
            resolve_donor_path(rel, require_file=True)
            for rel in (
                DONOR_FX3_LIBBACKUP_RELPATH,
                DONOR_FX6_LIBBACKUP_RELPATH,
                DONOR_FX3_BACKUP_KO_RELPATH,
                DONOR_FX3_APPFW_RELPATH,
                DONOR_FX6_APPFW_RELPATH,
                DONOR_FX3_CPAPP_B_RELPATH,
                DONOR_FX6_CPAPP_B_RELPATH,
            )
        ]
        if (not is_forced_clean_room()) and all(p.is_file() for p in donor_paths):
            self.assertEqual(self.suite_report.verification_mode, "LOCAL_DONOR_O_RDONLY")
            self.assertEqual(
                self.suite_report.donor_snapshot.fx3_appfw_sha256,
                self.clean_report.donor_snapshot.fx3_appfw_sha256,
            )
            self.assertEqual(
                self.suite_report.donor_snapshot.fx6_cpapp_b_sha256,
                self.clean_report.donor_snapshot.fx6_cpapp_b_sha256,
            )
            self.assertTrue(all(a.inspected for a in self.suite_report.donor_snapshot.artifacts))
        else:
            self.assertEqual(self.suite_report.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(self.suite_report.all_passed)
        self.assertTrue(self.clean_report.all_passed)

    def test_05_include_cpapp_false_skips_cpapp_inspection(self) -> None:
        snap = inspect_factory_cal_and_sensor_donors_readonly(include_cpapp=False)
        by_label = {a.label: a for a in snap.artifacts}
        self.assertFalse(snap.include_cpapp)
        self.assertFalse(by_label["fx3_v702_cpapp_b_bin"].inspected)
        self.assertFalse(by_label["fx6_v601_cpapp_b_bin"].inspected)
        self.assertEqual(by_label["fx3_v702_cpapp_b_bin"].source_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_06_clean_room_suite_completes_under_half_second(self) -> None:
        t0 = time.monotonic()
        rep = run_factory_cal_ibis_defectpixel_and_nvs_suite(force_clean_room=True)
        elapsed = time.monotonic() - t0
        self.assertTrue(rep.all_passed)
        self.assertLess(elapsed, 0.5)

    def test_07_clean_room_fallback_does_not_open_donor_files(self) -> None:
        with mock.patch("fx3_recovery.files.os.open") as m_open:
            m_open.side_effect = OSError("sentinel stop")
            snap = inspect_factory_cal_and_sensor_donors_readonly(force_clean_room=True)
            self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            m_open.assert_not_called()

    # ------------------------------------------------------------------
    # Pillar A — Factory Cal (`nvs`/`adj`/`cnflasha`) Triple Parity & Firewall
    # ------------------------------------------------------------------

    def test_08_same_body_3of3_triple_parity_passes(self) -> None:
        target = build_synthetic_factory_cal_identity("fx3-alpha")
        manifest = build_synthetic_factory_cal_manifest(target)
        rep = verify_factory_cal_triple_parity_and_firewall(target, manifest)
        self.assertTrue(rep.passed)
        self.assertEqual(rep.status, STATUS_VERIFIED_FACTORY_CAL_PARITY)
        self.assertTrue(rep.triple_parity_verified)
        self.assertTrue(rep.identity_match_verified)
        self.assertTrue(rep.cnflasha_vault_protected)
        self.assertEqual(len(rep.partition_parity), len(FACTORY_CAL_PARTITIONS))
        self.assertTrue(all(p.independent_matching_copies == 3 and p.quorum_met for p in rep.partition_parity))
        self.assertEqual(rep.physical_device_writes, 0)
        self.assertEqual(rep.factory_cal_mutation_bytes, 0)
        self.assertEqual(rep.private_key_bytes_read, 0)

    def test_09_same_body_2of3_quorum_survives_single_corruption(self) -> None:
        target = build_synthetic_factory_cal_identity("fx3-alpha")
        manifest = build_synthetic_factory_cal_manifest(
            target, matching_copies_by_partition={"nvs": 2, "adj": 2, "cnflasha": 2}
        )
        rep = verify_factory_cal_triple_parity_and_firewall(target, manifest)
        self.assertTrue(rep.passed)
        self.assertTrue(rep.triple_parity_verified)
        self.assertTrue(all(p.independent_matching_copies == 2 and p.quorum_met for p in rep.partition_parity))

    def test_10_cross_serial_donor_body_hash_mismatch_blocked(self) -> None:
        target = build_synthetic_factory_cal_identity("fx3-alpha")
        donor = build_synthetic_factory_cal_identity("fx3-beta-donor")
        manifest = build_synthetic_factory_cal_manifest(target, donor_identity=donor)
        rep = verify_factory_cal_triple_parity_and_firewall(target, manifest)
        self.assertFalse(rep.passed)
        self.assertEqual(rep.status, STATUS_REJECTED_FACTORY_CAL_FIREWALL)
        self.assertTrue(rep.cross_serial_blocked)
        self.assertFalse(rep.identity_match_verified)
        self.assertIn(BLOCKED_CROSS_SERIAL_FACTORY_CAL_TRANSPLANT, rep.error_codes)

    def test_11_board_uid_only_mismatch_or_malformed_hash_blocked(self) -> None:
        target = build_synthetic_factory_cal_identity("fx3-alpha")
        same_serial_other_board = replace(
            target, board_uid_hash="f" * 64
        )
        rep_board = verify_factory_cal_triple_parity_and_firewall(
            target, build_synthetic_factory_cal_manifest(target, donor_identity=same_serial_other_board)
        )
        self.assertFalse(rep_board.passed)
        self.assertIn(BLOCKED_CROSS_SERIAL_FACTORY_CAL_TRANSPLANT, rep_board.error_codes)

        bad_hex = replace(target, body_serial_hash="not-64-hex")
        rep_bad = verify_factory_cal_triple_parity_and_firewall(
            target, build_synthetic_factory_cal_manifest(bad_hex)
        )
        self.assertFalse(rep_bad.passed)
        self.assertIn(BLOCKED_CROSS_SERIAL_FACTORY_CAL_TRANSPLANT, rep_bad.error_codes)

    def test_12_cross_sku_fx6_manifest_rejected(self) -> None:
        target = build_synthetic_factory_cal_identity("fx3-alpha")
        fx6_donor = build_synthetic_factory_cal_identity(
            "fx6-donor", sku_code=FX6_CAL_SKU_CODE, model_id=FX6_CAL_MODEL_ID
        )
        manifest = build_synthetic_factory_cal_manifest(target, donor_identity=fx6_donor)
        rep = verify_factory_cal_triple_parity_and_firewall(target, manifest)
        self.assertFalse(rep.passed)
        self.assertIn(ERR_FACTORY_CAL_SKU_MISMATCH, rep.error_codes)
        self.assertIn(BLOCKED_CROSS_SERIAL_FACTORY_CAL_TRANSPLANT, rep.error_codes)

    def test_13_missing_tier0_triple_parity_under_2_copies_blocked(self) -> None:
        target = build_synthetic_factory_cal_identity("fx3-alpha")
        for bad_counts in (
            {"nvs": 1, "adj": 3, "cnflasha": 3},
            {"nvs": 3, "adj": 0, "cnflasha": 3},
            {"nvs": 3, "adj": 3, "cnflasha": 1},
        ):
            manifest = build_synthetic_factory_cal_manifest(
                target, matching_copies_by_partition=bad_counts
            )
            rep = verify_factory_cal_triple_parity_and_firewall(target, manifest)
            self.assertFalse(rep.passed)
            self.assertTrue(rep.missing_triple_parity_blocked)
            self.assertIn(BLOCKED_MISSING_TIER0_FACTORY_CAL_TRIPLE_PARITY, rep.error_codes)

    def test_14_duplicate_media_location_does_not_forge_independent_quorum(self) -> None:
        target = build_synthetic_factory_cal_identity("fx3-alpha")
        base_manifest = build_synthetic_factory_cal_manifest(target)
        # Collapse all `nvs` copies onto the exact same media_location (single point of failure)
        forged_copies = tuple(
            replace(c, media_location="same_single_sd_card/nvs.sha256")
            if c.partition_name == "nvs"
            else c
            for c in base_manifest.partition_copies
        )
        forged_manifest = replace(base_manifest, partition_copies=forged_copies)
        rep = verify_factory_cal_triple_parity_and_firewall(target, forged_manifest)
        self.assertFalse(rep.passed)
        self.assertIn(BLOCKED_MISSING_TIER0_FACTORY_CAL_TRIPLE_PARITY, rep.error_codes)

    def test_15_blank_erased_or_zero_byte_copies_excluded_from_quorum(self) -> None:
        target = build_synthetic_factory_cal_identity("fx3-alpha")
        base_manifest = build_synthetic_factory_cal_manifest(target)
        # Mark 2 of 3 `adj` copies blank_or_erased or zero-length -> only 1 valid remains
        modified = []
        adj_idx = 0
        for c in base_manifest.partition_copies:
            if c.partition_name == "adj":
                if adj_idx == 0:
                    modified.append(replace(c, blank_or_erased=True))
                elif adj_idx == 1:
                    modified.append(replace(c, byte_length=0))
                else:
                    modified.append(c)
                adj_idx += 1
            else:
                modified.append(c)
        rep = verify_factory_cal_triple_parity_and_firewall(
            target, replace(base_manifest, partition_copies=tuple(modified))
        )
        self.assertFalse(rep.passed)
        self.assertIn(BLOCKED_MISSING_TIER0_FACTORY_CAL_TRIPLE_PARITY, rep.error_codes)

    def test_16_cnflasha_key_vault_audit_blocks_writes_and_private_key_reads(self) -> None:
        ok = audit_cnflasha_key_vault_operation("verify_parity_readonly", target_partition="nvs")
        self.assertTrue(ok.allowed)
        self.assertEqual(ok.private_key_bytes_read, 0)
        self.assertEqual(ok.factory_cal_mutation_bytes, 0)

        for op, part, kreq, wreq in (
            ("write_cnflasha", "cnflasha", 0, 4096),
            ("erase_cnflasha", "cnflasha", 0, 0),
            ("dd_overlay", "cnflasha", 0, 512),
            ("extract_private_key", "cnflasha", 256, 0),
            ("export_ecdsa_key", "factory_cal", 0, 0),
            ("verify_parity_readonly", "nvs", 128, 0),
        ):
            dec = audit_cnflasha_key_vault_operation(
                op,
                target_partition=part,
                read_private_key_bytes_requested=kreq,
                write_bytes_requested=wreq,
            )
            self.assertFalse(dec.allowed, f"Expected vault block for {op}")
            self.assertIn(BLOCKED_CNFLASHA_KEY_VAULT_WRITE_OR_EXTRACTION, dec.error_codes)
            self.assertEqual(dec.private_key_bytes_read, 0)
            self.assertEqual(dec.factory_cal_mutation_bytes, 0)
            self.assertEqual(dec.physical_device_writes, 0)

        mut_dec = audit_cnflasha_key_vault_operation("write_nvs", target_partition="nvs", write_bytes_requested=512)
        self.assertFalse(mut_dec.allowed)
        self.assertIn(ERR_FACTORY_CAL_MUTATION_FORBIDDEN, mut_dec.error_codes)

    def test_17_manifest_cnflasha_write_or_extract_triggers_vault_firewall(self) -> None:
        target = build_synthetic_factory_cal_identity("fx3-alpha")
        rep_w = verify_factory_cal_triple_parity_and_firewall(
            target,
            build_synthetic_factory_cal_manifest(
                target, requested_operations=("write_cnflasha",), write_bytes_requested=4096
            ),
        )
        self.assertFalse(rep_w.passed)
        self.assertTrue(rep_w.cnflasha_vault_blocked)
        self.assertFalse(rep_w.cnflasha_vault_protected)
        self.assertIn(BLOCKED_CNFLASHA_KEY_VAULT_WRITE_OR_EXTRACTION, rep_w.error_codes)
        self.assertEqual(rep_w.private_key_bytes_read, 0)
        self.assertEqual(rep_w.factory_cal_mutation_bytes, 0)

        rep_k = verify_factory_cal_triple_parity_and_firewall(
            target,
            build_synthetic_factory_cal_manifest(
                target, requested_operations=("dump_key_vault",), read_private_key_bytes_requested=64
            ),
        )
        self.assertFalse(rep_k.passed)
        self.assertTrue(rep_k.cnflasha_vault_blocked)
        self.assertIn(BLOCKED_CNFLASHA_KEY_VAULT_WRITE_OR_EXTRACTION, rep_k.error_codes)

    def test_18_factory_cal_6_scenario_firewall_all_green(self) -> None:
        res = run_factory_cal_6_scenario_firewall()
        self.assertTrue(res.passed, f"Pillar A errors: {res.errors}")
        self.assertEqual(res.scenarios_passed, 6)
        self.assertEqual(res.scenarios_total, 6)
        self.assertEqual([r.scenario_id for r in res.scenario_results], list(FACTORY_CAL_FIREWALL_SCENARIO_IDS))
        self.assertEqual(res.physical_device_writes, 0)
        self.assertEqual(res.factory_cal_mutation_bytes, 0)
        self.assertEqual(res.private_key_bytes_read, 0)

    # ------------------------------------------------------------------
    # Pillar B — IMX510 Defect-Pixel / Dual-ISO & 5-Axis IBIS / IMU Tables
    # ------------------------------------------------------------------

    def test_19_healthy_imx510_and_5axis_ibis_imu_tables_pass(self) -> None:
        target = build_synthetic_factory_cal_identity("fx3-alpha")
        imx = build_synthetic_imx510_cal_table(target.body_serial_hash)
        ibis = build_synthetic_ibis_imu_cal_table(target.body_serial_hash)
        rep = verify_imx510_and_ibis_cal_tables(target, imx, ibis)
        self.assertTrue(rep.passed)
        self.assertEqual(rep.status, STATUS_VERIFIED_SENSOR_IBIS_CAL_TABLES)
        self.assertEqual(rep.imx510_defect_count, 6)
        self.assertTrue(rep.imx510_monotonic_in_bounds)
        self.assertTrue(rep.imx510_dual_iso_offsets_bounded)
        self.assertTrue(rep.imx510_crc32_valid)
        self.assertTrue(rep.ibis_5axis_hall_zero_bounded)
        self.assertTrue(rep.imu_gyro_temp_poly_bounded)
        self.assertTrue(rep.ibis_imu_crc32_valid)
        self.assertTrue(rep.body_serial_binding_valid)

    def test_20_imx510_out_of_bounds_4264x2408_rejected(self) -> None:
        target = build_synthetic_factory_cal_identity("fx3-alpha")
        ibis = build_synthetic_ibis_imu_cal_table(target.body_serial_hash)
        for bad_px in (
            Imx510DefectPixelCoord(IMX510_ACTIVE_WIDTH, 100),
            Imx510DefectPixelCoord(100, IMX510_ACTIVE_HEIGHT),
            Imx510DefectPixelCoord(-1, 50),
            Imx510DefectPixelCoord(50, -1),
        ):
            imx = build_synthetic_imx510_cal_table(
                target.body_serial_hash,
                defect_pixels=(Imx510DefectPixelCoord(10, 10), bad_px),
            )
            rep = verify_imx510_and_ibis_cal_tables(target, imx, ibis)
            self.assertFalse(rep.passed)
            self.assertFalse(rep.imx510_monotonic_in_bounds)
            self.assertIn(ERR_IMX510_PIXEL_OUT_OF_BOUNDS, rep.error_codes)

    def test_21_imx510_non_monotonic_or_duplicate_pixels_rejected(self) -> None:
        target = build_synthetic_factory_cal_identity("fx3-alpha")
        ibis = build_synthetic_ibis_imu_cal_table(target.body_serial_hash)
        for bad_seq in (
            (Imx510DefectPixelCoord(200, 100), Imx510DefectPixelCoord(100, 100)),  # backward x on same y
            (Imx510DefectPixelCoord(100, 200), Imx510DefectPixelCoord(500, 100)),  # backward y
            (Imx510DefectPixelCoord(500, 500), Imx510DefectPixelCoord(500, 500)),  # duplicate
        ):
            imx = build_synthetic_imx510_cal_table(target.body_serial_hash, defect_pixels=bad_seq)
            rep = verify_imx510_and_ibis_cal_tables(target, imx, ibis)
            self.assertFalse(rep.passed)
            self.assertFalse(rep.imx510_monotonic_in_bounds)
            self.assertIn(ERR_IMX510_NON_MONOTONIC_COORDINATES, rep.error_codes)

    def test_22_imx510_empty_map_or_wrong_dimensions_rejected(self) -> None:
        target = build_synthetic_factory_cal_identity("fx3-alpha")
        ibis = build_synthetic_ibis_imu_cal_table(target.body_serial_hash)
        empty_imx = build_synthetic_imx510_cal_table(target.body_serial_hash, defect_pixels=())
        rep_empty = verify_imx510_and_ibis_cal_tables(target, empty_imx, ibis)
        self.assertFalse(rep_empty.passed)
        self.assertIn(ERR_IMX510_EMPTY_OR_OVERSIZED_DEFECT_MAP, rep_empty.error_codes)

        bad_dim = replace(
            build_synthetic_imx510_cal_table(target.body_serial_hash),
            active_width=3840,
        )
        rep_dim = verify_imx510_and_ibis_cal_tables(target, bad_dim, ibis)
        self.assertFalse(rep_dim.passed)
        self.assertIn(ERR_IMX510_PIXEL_OUT_OF_BOUNDS, rep_dim.error_codes)

    def test_23_imx510_dual_base_iso_800_12800_and_gain_ratio_enforced(self) -> None:
        target = build_synthetic_factory_cal_identity("fx3-alpha")
        ibis = build_synthetic_ibis_imu_cal_table(target.body_serial_hash)
        base_imx = build_synthetic_imx510_cal_table(target.body_serial_hash)

        wrong_iso = replace(
            base_imx,
            iso_12800_profile=replace(base_imx.iso_12800_profile, base_iso=6400),
        )
        rep_iso = verify_imx510_and_ibis_cal_tables(target, wrong_iso, ibis)
        self.assertFalse(rep_iso.passed)
        self.assertEqual((base_imx.iso_800_profile.base_iso, base_imx.iso_12800_profile.base_iso), IMX510_DUAL_BASE_ISOS)
        self.assertIn(ERR_IMX510_DUAL_ISO_CONFIG_INVALID, rep_iso.error_codes)

        bad_ratio = replace(
            base_imx,
            iso_12800_profile=replace(base_imx.iso_12800_profile, analog_gain=1.5),
        )
        rep_ratio = verify_imx510_and_ibis_cal_tables(target, bad_ratio, ibis)
        self.assertFalse(rep_ratio.passed)
        self.assertIn(ERR_IMX510_DUAL_ISO_CONFIG_INVALID, rep_ratio.error_codes)

    def test_24_imx510_dark_current_column_fpn_and_nan_rejected(self) -> None:
        target = build_synthetic_factory_cal_identity("fx3-alpha")
        ibis = build_synthetic_ibis_imu_cal_table(target.body_serial_hash)

        rep_dark = verify_imx510_and_ibis_cal_tables(
            target,
            build_synthetic_imx510_cal_table(target.body_serial_hash, iso_12800_dark_lsb=512.0),
            ibis,
        )
        self.assertFalse(rep_dark.passed)
        self.assertIn(ERR_IMX510_ADC_OFFSET_OUT_OF_RANGE, rep_dark.error_codes)

        rep_fpn = verify_imx510_and_ibis_cal_tables(
            target,
            build_synthetic_imx510_cal_table(target.body_serial_hash, iso_12800_col_fpn_peak_lsb=-45.0),
            ibis,
        )
        self.assertFalse(rep_fpn.passed)
        self.assertIn(ERR_IMX510_ADC_OFFSET_OUT_OF_RANGE, rep_fpn.error_codes)

        base_imx = build_synthetic_imx510_cal_table(target.body_serial_hash)
        nan_imx = replace(
            base_imx,
            iso_800_profile=replace(base_imx.iso_800_profile, dark_current_offset_lsb=math.nan),
        )
        rep_nan = verify_imx510_and_ibis_cal_tables(target, nan_imx, ibis)
        self.assertFalse(rep_nan.passed)
        self.assertIn(ERR_IMX510_ADC_OFFSET_OUT_OF_RANGE, rep_nan.error_codes)

    def test_25_ibis_incomplete_axes_rejected(self) -> None:
        target = build_synthetic_factory_cal_identity("fx3-alpha")
        imx = build_synthetic_imx510_cal_table(target.body_serial_hash)
        ibis = build_synthetic_ibis_imu_cal_table(target.body_serial_hash)
        four_axes = tuple(ax for ax in ibis.ibis_axes if ax.axis_name != "roll")
        bad_ibis = replace(
            ibis,
            ibis_axes=four_axes,
            crc32=compute_ibis_imu_cal_crc32(
                body_serial_hash=ibis.body_serial_hash,
                temp_min_c=ibis.temp_min_c,
                temp_max_c=ibis.temp_max_c,
                ibis_axes=four_axes,
                imu_gyro_polys=ibis.imu_gyro_polys,
            ),
        )
        rep = verify_imx510_and_ibis_cal_tables(target, imx, bad_ibis)
        self.assertFalse(rep.passed)
        self.assertFalse(rep.ibis_5axis_hall_zero_bounded)
        self.assertIn(ERR_IBIS_AXES_MISMATCH, rep.error_codes)

    def test_26_ibis_hall_zero_rail_and_stroke_overflow_rejected(self) -> None:
        target = build_synthetic_factory_cal_identity("fx3-alpha")
        imx = build_synthetic_imx510_cal_table(target.body_serial_hash)

        for ax_name, bad_zero in (("pitch", 512), ("yaw", 4090), ("x", 3500)):
            ibis = build_synthetic_ibis_imu_cal_table(
                target.body_serial_hash, hall_zero_overrides={ax_name: bad_zero}
            )
            rep = verify_imx510_and_ibis_cal_tables(target, imx, ibis)
            self.assertFalse(rep.passed)
            self.assertFalse(rep.ibis_5axis_hall_zero_bounded)
            self.assertIn(ERR_IBIS_HALL_ZERO_OUT_OF_RANGE, rep.error_codes)

        # Zero near upper valid bound (3072) + stroke 1200 overflows 12-bit 4095 ADC
        base_ibis = build_synthetic_ibis_imu_cal_table(target.body_serial_hash)
        over_axes = tuple(
            IbisAxisHallCalEntry(ax.axis_name, 3072, 1200, 640) if ax.axis_name == "y" else ax
            for ax in base_ibis.ibis_axes
        )
        rep_stroke = verify_imx510_and_ibis_cal_tables(
            target, imx, replace(base_ibis, ibis_axes=over_axes)
        )
        self.assertFalse(rep_stroke.passed)
        self.assertIn(ERR_IBIS_HALL_ZERO_OUT_OF_RANGE, rep_stroke.error_codes)

    def test_27_imu_temp_envelope_must_cover_minus10_to_plus60(self) -> None:
        target = build_synthetic_factory_cal_identity("fx3-alpha")
        imx = build_synthetic_imx510_cal_table(target.body_serial_hash)
        for tmin, tmax in ((0.0, 60.0), (-10.0, 45.0), (20.0, 10.0)):
            ibis = build_synthetic_ibis_imu_cal_table(
                target.body_serial_hash, temp_min_c=tmin, temp_max_c=tmax
            )
            rep = verify_imx510_and_ibis_cal_tables(target, imx, ibis)
            self.assertFalse(rep.passed)
            self.assertFalse(rep.imu_gyro_temp_poly_bounded)
            self.assertIn(ERR_IMU_TEMP_RANGE_COVERAGE_INVALID, rep.error_codes)

    def test_28_imu_gyro_bias_polynomial_divergence_and_nan_rejected(self) -> None:
        target = build_synthetic_factory_cal_identity("fx3-alpha")
        imx = build_synthetic_imx510_cal_table(target.body_serial_hash)
        rep_div = verify_imx510_and_ibis_cal_tables(
            target, imx, build_synthetic_ibis_imu_cal_table(target.body_serial_hash, pitch_c1_override=0.25)
        )
        self.assertFalse(rep_div.passed)
        self.assertIn(ERR_IMU_GYRO_BIAS_POLY_OUT_OF_RANGE, rep_div.error_codes)

        base_ibis = build_synthetic_ibis_imu_cal_table(target.body_serial_hash)
        nan_polys = tuple(
            ImuGyroTempBiasPolyEntry(g.axis_name, math.inf, g.c1_dps_per_c, g.c2_dps_per_c2)
            if g.axis_name == "yaw"
            else g
            for g in base_ibis.imu_gyro_polys
        )
        rep_nan = verify_imx510_and_ibis_cal_tables(
            target, imx, replace(base_ibis, imu_gyro_polys=nan_polys)
        )
        self.assertFalse(rep_nan.passed)
        self.assertIn(ERR_IMU_GYRO_BIAS_POLY_OUT_OF_RANGE, rep_nan.error_codes)

    def test_29_sensor_and_ibis_crc32_tamper_and_body_mismatch_rejected(self) -> None:
        target = build_synthetic_factory_cal_identity("fx3-alpha")
        other = build_synthetic_factory_cal_identity("fx3-donor")
        valid_imx = build_synthetic_imx510_cal_table(target.body_serial_hash)
        valid_ibis = build_synthetic_ibis_imu_cal_table(target.body_serial_hash)

        rep_crc = verify_imx510_and_ibis_cal_tables(
            target,
            build_synthetic_imx510_cal_table(target.body_serial_hash, corrupt_crc32=True),
            build_synthetic_ibis_imu_cal_table(target.body_serial_hash, corrupt_crc32=True),
        )
        self.assertFalse(rep_crc.passed)
        self.assertFalse(rep_crc.imx510_crc32_valid)
        self.assertFalse(rep_crc.ibis_imu_crc32_valid)
        self.assertIn(ERR_IMX510_CRC32_MISMATCH, rep_crc.error_codes)
        self.assertIn(ERR_IBIS_IMU_CRC32_MISMATCH, rep_crc.error_codes)

        rep_bind = verify_imx510_and_ibis_cal_tables(
            target, build_synthetic_imx510_cal_table(other.body_serial_hash), valid_ibis
        )
        self.assertFalse(rep_bind.passed)
        self.assertFalse(rep_bind.body_serial_binding_valid)
        self.assertIn(ERR_SENSOR_BODY_BINDING_MISMATCH, rep_bind.error_codes)

        rep_bind2 = verify_imx510_and_ibis_cal_tables(
            target, valid_imx, build_synthetic_ibis_imu_cal_table(other.body_serial_hash)
        )
        self.assertFalse(rep_bind2.passed)
        self.assertFalse(rep_bind2.body_serial_binding_valid)
        self.assertIn(ERR_SENSOR_BODY_BINDING_MISMATCH, rep_bind2.error_codes)

    def test_30_sensor_ibis_6_scenario_suite_all_green(self) -> None:
        res = run_sensor_ibis_cal_6_scenario_suite()
        self.assertTrue(res.passed, f"Pillar B errors: {res.errors}")
        self.assertEqual(res.scenarios_passed, 6)
        self.assertEqual(res.scenarios_total, 6)
        self.assertEqual([r.scenario_id for r in res.scenario_results], list(SENSOR_IBIS_SCENARIO_IDS))

    def test_31_pillar_a_and_b_reports_to_dict_serializable(self) -> None:
        fw_dict = self.clean_report.factory_cal_6_scenario_firewall.to_dict()
        sens_dict = self.clean_report.sensor_ibis_6_scenario_suite.to_dict()
        self.assertEqual(fw_dict["scenarios_passed"], 6)
        self.assertEqual(sens_dict["scenarios_passed"], 6)
        self.assertEqual(fw_dict["private_key_bytes_read"], 0)
        self.assertEqual(fw_dict["factory_cal_mutation_bytes"], 0)

    # ------------------------------------------------------------------
    # Pillar C — Master Suite Determinism, CLI & >=14-Pillar Integration
    # ------------------------------------------------------------------

    def test_32_clean_room_suite_sha256_is_deterministic(self) -> None:
        r2 = run_factory_cal_ibis_defectpixel_and_nvs_suite(force_clean_room=True)
        self.assertEqual(self.clean_report.suite_sha256, r2.suite_sha256)
        self.assertEqual(
            self.clean_report.factory_cal_6_scenario_firewall.suite_sha256,
            r2.factory_cal_6_scenario_firewall.suite_sha256,
        )
        self.assertEqual(
            self.clean_report.sensor_ibis_6_scenario_suite.suite_sha256,
            r2.sensor_ibis_6_scenario_suite.suite_sha256,
        )

    def test_33_json_serialization_no_raw_bytes_and_no_nan(self) -> None:
        rendered = json.dumps(self.suite_report.to_dict(), ensure_ascii=False, sort_keys=True, allow_nan=False)
        self.assertNotRegex(rendered, RAW_BYTES_RE)
        decoded = json.loads(rendered)
        self.assertEqual(decoded["suite_sha256"], self.suite_report.suite_sha256)
        self.assertEqual(decoded["factory_cal_mutation_bytes"], 0)
        self.assertEqual(decoded["private_key_bytes_read"], 0)
        self.assertEqual(decoded["physical_device_writes"], 0)
        self.assertEqual(decoded["otp_fuse_touches"], 0)
        self.assertEqual(decoded["passive_tx_bytes_emitted"], 0)
        self.assertFalse(decoded["persistent_emmc_writes_authorized"])
        self.assertFalse(decoded["persistent_write_release"])

    def test_34_cli_verify_factory_cal_guard_clean_room_json_and_text(self) -> None:
        buf_json = io.StringIO()
        with (
            mock.patch.object(sys, "argv", ["fx3_recovery", "verify-factory-cal-guard", "--clean-room", "--json"]),
            redirect_stdout(buf_json),
        ):
            rc_json = fx3_cli.main()
        self.assertEqual(rc_json, 0)
        rendered = buf_json.getvalue()
        self.assertNotRegex(rendered, RAW_BYTES_RE)
        parsed = json.loads(rendered)
        self.assertEqual(parsed["status"], STATUS_VERIFIED_FACTORY_CAL_GUARD)
        self.assertEqual(parsed["verification_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(parsed["factory_cal_mutation_bytes"], 0)
        self.assertEqual(parsed["private_key_bytes_read"], 0)

        buf_txt = io.StringIO()
        with (
            mock.patch.object(sys, "argv", ["fx3_recovery", "verify-factory-cal-guard", "--clean-room"]),
            redirect_stdout(buf_txt),
        ):
            rc_txt = fx3_cli.main()
        self.assertEqual(rc_txt, 0)
        txt = buf_txt.getvalue()
        self.assertIn("status=VERIFIED_FACTORY_CAL_IBIS_AND_NVS_GUARD", txt)
        self.assertIn("factory_cal_scenarios=6/6", txt)
        self.assertIn("sensor_ibis_scenarios=6/6", txt)
        self.assertIn("factory_cal_mutation_bytes=0", txt)
        self.assertIn("private_key_bytes_read=0", txt)

    def test_35_cli_verify_factory_cal_guard_active_mode(self) -> None:
        buf = io.StringIO()
        with (
            mock.patch.object(sys, "argv", ["fx3_recovery", "verify-factory-cal-guard", "--json"]),
            redirect_stdout(buf),
        ):
            rc = fx3_cli.main()
        self.assertEqual(rc, 0)
        rendered = buf.getvalue()
        self.assertNotRegex(rendered, RAW_BYTES_RE)
        parsed = json.loads(rendered)
        self.assertTrue(parsed["all_passed"])
        self.assertIn(parsed["verification_mode"], ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"))

    def test_36_cli_verify_factory_cal_guard_out_writes_artifact(self) -> None:
        scratch_root = ROOT / "work" / "_tests" / "phase126_cli_out"
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
                        "verify-factory-cal-guard",
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
            out_file = scratch_root / "factory-cal-guard-report.json"
            self.assertTrue(out_file.is_file())
            written = json.loads(out_file.read_text(encoding="utf-8"))
            self.assertEqual(written["status"], STATUS_VERIFIED_FACTORY_CAL_GUARD)
            self.assertEqual(written["private_key_bytes_read"], 0)
        finally:
            if scratch_root.exists():
                shutil.rmtree(scratch_root)

    def test_37_cli_verify_factory_cal_guard_failure_returns_exit_2(self) -> None:
        failing = FactoryCalIbisAndNvsSuiteReport(
            **{**self.clean_report.__dict__, "all_passed": False, "status": STATUS_FAIL_FACTORY_CAL_GUARD}
        )
        with mock.patch("fx3_recovery.__main__.run_factory_cal_ibis_defectpixel_and_nvs_suite", return_value=failing):
            buf = io.StringIO()
            with (
                mock.patch.object(sys, "argv", ["fx3_recovery", "verify-factory-cal-guard", "--clean-room", "--json"]),
                redirect_stdout(buf),
            ):
                rc = fx3_cli.main()
            self.assertEqual(rc, 2)
            parsed = json.loads(buf.getvalue())
            self.assertFalse(parsed["all_passed"])
            self.assertEqual(parsed["status"], STATUS_FAIL_FACTORY_CAL_GUARD)

    def test_38_cli_verify_all_recovery_14_pillars_clean_room_and_failure_propagation(self) -> None:
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
        self.assertGreaterEqual(parsed["pillar_count"], 14)
        self.assertEqual(parsed["pillars_passed"], parsed["pillar_count"])
        self.assertIn("phase126_pillar14_factory_cal_ibis_defectpixel_nvs", parsed)
        self.assertEqual(
            parsed["phase126_pillar14_factory_cal_ibis_defectpixel_nvs"]["status"],
            STATUS_VERIFIED_FACTORY_CAL_GUARD,
        )

        failing = FactoryCalIbisAndNvsSuiteReport(
            **{**self.clean_report.__dict__, "all_passed": False, "status": STATUS_FAIL_FACTORY_CAL_GUARD}
        )
        with mock.patch("fx3_recovery.__main__.run_factory_cal_ibis_defectpixel_and_nvs_suite", return_value=failing):
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
                        "--json",
                    ],
                ),
                redirect_stdout(buf_fail),
            ):
                rc_fail = fx3_cli.main()
            self.assertEqual(rc_fail, 2)
            parsed_fail = json.loads(buf_fail.getvalue())
            self.assertFalse(parsed_fail["all_passed"])
            self.assertGreaterEqual(parsed_fail["pillar_count"], 14)
            self.assertEqual(parsed_fail["pillars_passed"], parsed_fail["pillar_count"] - 1)

    def test_39_cli_verify_all_recovery_14_pillars_active_mode(self) -> None:
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
        self.assertGreaterEqual(parsed["pillar_count"], 14)
        self.assertEqual(parsed["pillars_passed"], parsed["pillar_count"])
        self.assertIn("phase126_pillar14_factory_cal_ibis_defectpixel_nvs", parsed)

    def test_40_cli_verify_all_recovery_default_compat_and_text_14_pillars(self) -> None:
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
        self.assertNotIn("phase126_pillar14_factory_cal_ibis_defectpixel_nvs", parsed_def)

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
                ],
            ),
            redirect_stdout(buf_txt),
        ):
            rc_txt = fx3_cli.main()
        self.assertEqual(rc_txt, 0)
        txt = buf_txt.getvalue()
        self.assertIn("status=VERIFIED_RECOVERY_MASTER_SUITE", txt)
        self.assertIn("pillars=14/14", txt)


if __name__ == "__main__":
    unittest.main()
