"""Phase 186 dual-mode unit tests for Real-Hardware Final Card-Insert Pre-Flight Verifier."""

from __future__ import annotations

import copy
import hashlib
import io
import json
import os
from pathlib import Path
import re
import struct
import sys
import tempfile
import time
import unittest
from unittest import mock

sys.dont_write_bytecode = True

REPO_ROOT = Path(__file__).resolve().parents[3]
for _rel in (
    "outputs/fx3-safety",
    "outputs/fx3-recovery-adapter",
    "outputs/fx6-on-fx3-closure",
):
    _cand = str(REPO_ROOT / _rel)
    if _cand not in sys.path:
        sys.path.insert(0, _cand)

import fx6_closure  # noqa: E402
from fx6_closure.__main__ import main as fx6_cli_main  # noqa: E402
from fx6_closure.donor_paths import is_forced_clean_room  # noqa: E402
from fx6_closure.realhw_card_insert_readiness_verifier import (  # noqa: E402
    C1_ERR_ARTIFACT_SHA256_MISMATCH,
    C1_ERR_CLUSTER_SIZE_BELOW_128KIB,
    C1_ERR_ELF64_NOT_AARCH64,
    C1_ERR_EXFAT_BOOT_CHECKSUM_MISMATCH,
    C1_ERR_EXFAT_DIRTY_OR_MEDIA_FAILURE,
    C1_ERR_FILESYSTEM_NOT_EXFAT_APFS,
    C1_ERR_FILESYSTEM_NOT_EXFAT_FAT32,
    C1_ERR_FILESYSTEM_NOT_EXFAT_HFS_PLUS,
    C1_ERR_FILESYSTEM_NOT_EXFAT_NTFS,
    C1_ERR_FORBIDDEN_FLASH_TRIGGER,
    C1_ERR_LIBJIT_EXCEEDS_64KIB,
    C1_ERR_MACOS_METADATA_JUNK_DETECTED,
    C1_ERR_SLOT1_BODYDATA_COPRESENCE,
    C1_ERR_SYMLINK_REJECTED,
    C2_ERR_BODY_IDENTITY_INVALID,
    C2_ERR_FW_BELOW_204_FLOOR,
    C2_ERR_FW_NOT_TARGET_702,
    C2_ERR_H0_BASELINE_MISSING_OR_MISMATCH,
    C2_ERR_MODEL_ID_MISMATCH,
    C2_ERR_RECEIPT_INVALID_528B,
    C2_ERR_RECEIPT_NOT_PROVIDED,
    C2_ERR_RECEIPT_PAIR_MISMATCH,
    C2_ERR_SINGLE_DEVICE_ST_DEV_COLLISION,
    C3_ERR_BATTERY_OVERVOLTAGE,
    C3_ERR_BATTERY_SOC_BELOW_80PCT,
    C3_ERR_BATTERY_VOLTAGE_BELOW_7V6,
    C3_ERR_BODY_TEMP_AT_OR_ABOVE_45C,
    C3_ERR_BODY_TEMP_OUT_OF_RANGE,
    C3_ERR_HDMI_ACTIVE_OR_BACKFEED,
    C3_ERR_PIN_8_9_10_VMC_BNCM1_UART_CONTENTION,
    C3_ERR_UART_VOLTAGE_NOT_1V8,
    C3_ERR_USB_PD_UNSAFE,
    C4_ERR_EH1_LATENCY_OR_BYPASS_FAILED,
    C4_ERR_EH2_SAFE_COLD_BOOT_FAILED,
    C4_ERR_EH3_CRC32_TAMPER_FALLBACK_FAILED,
    C4_ERR_H0_H3_SURFACE_DRIFT,
    CARD_INSERT_GATE_IDS,
    DONOR_INSPECTION_MAX_SECONDS,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    EM_AARCH64,
    EXFAT_FLAG_MEDIA_FAILURE,
    EXFAT_FLAG_VOLUME_DIRTY,
    GATE_C1_ID,
    GATE_C2_ID,
    GATE_C3_ID,
    GATE_C4_ID,
    GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT,
    GO_NO_GO_BLOCKED_GATE_FAILURE,
    GO_NO_GO_DRY_RUN_SIMULATED_READY,
    GO_NO_GO_PHYSICAL_PREFLIGHT_VERIFIED,
    LIBJIT_MAX_SIZE_BYTES,
    MIN_EXFAT_CLUSTER_BYTES,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHASE_186_SCHEMA,
    PHASE_186_VERSION,
    PHYSICAL_USB_PACKETS_EMITTED,
    RAW_FIRMWARE_BYTES_LEAKED,
    REQUIRED_H0_BASELINE_KEYS,
    SD_PHYSICAL_MEDIA_WRITTEN,
    SPI_NOR_WRITE_AUTHORIZED,
    TARGET_BODY_FW,
    TARGET_MODEL_ID_INT,
    audit_exfat_slot_boot_sector,
    build_clean_room_libjit_so,
    build_default_h0_baselines,
    build_simulated_dual_receipts_and_h0,
    build_simulated_staged_elf64_artifacts,
    build_synthetic_exfat_boot_region,
    evaluate_c1_slot1_exfat_geometry_and_hygiene,
    evaluate_c2_tier0_dual_media_binding,
    evaluate_c3_electrical_cable_thermal_interlock,
    evaluate_c4_escape_hatch_and_uninstall_dryrun,
    inspect_card_insert_donors_bounded,
    render_phase186_markdown,
    run_card_insert_preflight,
    verify_phase186_report,
)

_RAW_BYTES_REPR_REGEX = r"(?<![0-9A-Za-z_/.-])b['\"]"


class TestPhase186RealHwCardInsertReadinessVerifier(unittest.TestCase):
    """Dual-mode unit tests (>= 48) for Phase 186 preflight-card-insert."""

    def _valid_exfat_128kib(self, *, volume_serial: int = 0x46583336) -> bytes:
        return build_synthetic_exfat_boot_region(
            bytes_per_sector_shift=9,
            sectors_per_cluster_shift=8,
            volume_serial=volume_serial,
        )

    def test_01_public_exports_in_fx6_closure_init(self) -> None:
        required = (
            "PHASE_186_SCHEMA",
            "PHASE_186_VERSION",
            "CARD_INSERT_GATE_IDS",
            "GATE_C1_ID",
            "GATE_C2_ID",
            "GATE_C3_ID",
            "GATE_C4_ID",
            "inspect_card_insert_donors_bounded",
            "audit_exfat_slot_boot_sector",
            "evaluate_c1_slot1_exfat_geometry_and_hygiene",
            "evaluate_c2_tier0_dual_media_binding",
            "evaluate_c3_electrical_cable_thermal_interlock",
            "evaluate_c4_escape_hatch_and_uninstall_dryrun",
            "run_card_insert_preflight",
            "verify_phase186_report",
            "render_phase186_markdown",
        )
        for name in required:
            self.assertIn(name, fx6_closure.__all__)
            self.assertTrue(hasattr(fx6_closure, name))

    def test_02_hard_safety_locks_constants(self) -> None:
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(PERSISTENT_WRITE_RELEASE)
        self.assertFalse(SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        self.assertFalse(SD_PHYSICAL_MEDIA_WRITTEN)
        self.assertEqual(PHYSICAL_USB_PACKETS_EMITTED, 0)
        self.assertEqual(RAW_FIRMWARE_BYTES_LEAKED, 0)
        self.assertEqual(CARD_INSERT_GATE_IDS, (GATE_C1_ID, GATE_C2_ID, GATE_C3_ID, GATE_C4_ID))

    def test_03_bounded_donor_inspection_active_mode_under_150ms(self) -> None:
        res = inspect_card_insert_donors_bounded()
        self.assertTrue(res.passed, msg=str(res.errors))
        self.assertTrue(res.read_only_o_rdonly_enforced)
        self.assertLess(res.elapsed_seconds, DONOR_INSPECTION_MAX_SECONDS)
        self.assertTrue(res.within_150ms_budget)
        self.assertEqual(res.raw_firmware_bytes_leaked, 0)
        if is_forced_clean_room():
            self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        else:
            self.assertIn(res.verification_mode, ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"))
        self.assertEqual(
            res.inspected_artifacts,
            ("im.elf", "libJiritsu.so", "appFw.so", "libWlanResource.so", "upm.ko"),
        )

    def test_04_bounded_donor_inspection_forced_clean_room(self) -> None:
        res = inspect_card_insert_donors_bounded(synthetic_clean_room=True)
        self.assertTrue(res.passed)
        self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertLess(res.elapsed_seconds, DONOR_INSPECTION_MAX_SECONDS)
        self.assertEqual(res.raw_firmware_bytes_leaked, 0)

    def test_05_bounded_donor_inspection_missing_donors_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "no_such_donors"
            res = inspect_card_insert_donors_bounded(
                fx6_lib_dir=missing,
                fx3_modules_dir=missing,
                synthetic_clean_room=False,
            )
            self.assertFalse(res.passed)
            self.assertEqual(res.verification_mode, "LOCAL_DONOR_O_RDONLY")
            self.assertEqual(res.raw_firmware_bytes_leaked, 0)
            self.assertTrue(len(res.errors) >= 1)

    def test_06_c1_valid_exfat_128kib_and_256kib_cluster_alignment(self) -> None:
        artifacts = build_simulated_staged_elf64_artifacts()
        for spc_shift, expected_bpc in ((8, MIN_EXFAT_CLUSTER_BYTES), (9, 256 * 1024)):
            vbr = build_synthetic_exfat_boot_region(
                bytes_per_sector_shift=9,
                sectors_per_cluster_shift=spc_shift,
            )
            c1 = evaluate_c1_slot1_exfat_geometry_and_hygiene(
                slot1_exfat_boot_bytes=vbr,
                staged_artifacts=artifacts,
            )
            self.assertTrue(c1.passed, msg=str(c1.errors))
            self.assertTrue(c1.slot1_exfat.is_exfat)
            self.assertEqual(c1.slot1_exfat.bytes_per_cluster, expected_bpc)
            self.assertTrue(c1.slot1_exfat.cluster_ge_128kib)
            self.assertTrue(c1.slot1_exfat.boot_checksum_ok)
            self.assertTrue(c1.libjit_within_64kib)

    def test_07_c1_rejects_exfat_cluster_below_128kib(self) -> None:
        artifacts = build_simulated_staged_elf64_artifacts()
        for spc_shift in (3, 6, 7):  # 4 KiB, 32 KiB, 64 KiB
            vbr = build_synthetic_exfat_boot_region(
                bytes_per_sector_shift=9,
                sectors_per_cluster_shift=spc_shift,
            )
            c1 = evaluate_c1_slot1_exfat_geometry_and_hygiene(
                slot1_exfat_boot_bytes=vbr,
                staged_artifacts=artifacts,
            )
            self.assertFalse(c1.passed)
            self.assertIn(C1_ERR_CLUSTER_SIZE_BELOW_128KIB, c1.error_codes)

    def test_08_c1_rejects_fat32_filesystem(self) -> None:
        buf = bytearray(512)
        buf[82:90] = b"FAT32   "
        struct.pack_into("<H", buf, 510, 0xAA55)
        res = audit_exfat_slot_boot_sector("SLOT_1", bytes(buf))
        self.assertFalse(res.passed)
        self.assertEqual(res.detected_filesystem, "FAT32")
        self.assertIn(C1_ERR_FILESYSTEM_NOT_EXFAT_FAT32, res.error_codes)

    def test_09_c1_rejects_ntfs_filesystem(self) -> None:
        buf = bytearray(512)
        buf[3:11] = b"NTFS    "
        struct.pack_into("<H", buf, 510, 0xAA55)
        res = audit_exfat_slot_boot_sector("SLOT_1", bytes(buf))
        self.assertFalse(res.passed)
        self.assertEqual(res.detected_filesystem, "NTFS")
        self.assertIn(C1_ERR_FILESYSTEM_NOT_EXFAT_NTFS, res.error_codes)

    def test_10_c1_rejects_apfs_filesystem(self) -> None:
        buf = bytearray(512)
        buf[32:36] = b"NXSB"
        res = audit_exfat_slot_boot_sector("SLOT_1", bytes(buf))
        self.assertFalse(res.passed)
        self.assertEqual(res.detected_filesystem, "APFS")
        self.assertIn(C1_ERR_FILESYSTEM_NOT_EXFAT_APFS, res.error_codes)

    def test_11_c1_rejects_hfs_plus_filesystem(self) -> None:
        buf = bytearray(2048)
        buf[1024:1026] = b"H+"
        res = audit_exfat_slot_boot_sector("SLOT_1", bytes(buf))
        self.assertFalse(res.passed)
        self.assertEqual(res.detected_filesystem, "HFS+")
        self.assertIn(C1_ERR_FILESYSTEM_NOT_EXFAT_HFS_PLUS, res.error_codes)

    def test_12_c1_rejects_exfat_dirty_and_media_failure_flags(self) -> None:
        for flag in (EXFAT_FLAG_VOLUME_DIRTY, EXFAT_FLAG_MEDIA_FAILURE):
            vbr = build_synthetic_exfat_boot_region(
                bytes_per_sector_shift=9,
                sectors_per_cluster_shift=8,
                volume_flags=flag,
            )
            res = audit_exfat_slot_boot_sector("SLOT_1", vbr)
            self.assertFalse(res.passed)
            self.assertIn(C1_ERR_EXFAT_DIRTY_OR_MEDIA_FAILURE, res.error_codes)

    def test_13_c1_rejects_exfat_12sector_boot_checksum_tamper(self) -> None:
        vbr = bytearray(self._valid_exfat_128kib())
        vbr[2 * 512 + 17] ^= 0x5A
        res = audit_exfat_slot_boot_sector("SLOT_1", bytes(vbr))
        self.assertFalse(res.passed)
        self.assertTrue(res.boot_checksum_checked)
        self.assertFalse(res.boot_checksum_ok)
        self.assertIn(C1_ERR_EXFAT_BOOT_CHECKSUM_MISMATCH, res.error_codes)

    def test_14_c1_rejects_macos_appledouble_and_ds_store_in_fx6_stageb(self) -> None:
        vbr = self._valid_exfat_128kib()
        artifacts = build_simulated_staged_elf64_artifacts()
        for junk in ("FX6_STAGEB/._appFw.so", "FX6_STAGEB/.DS_Store", "FX6_STAGEB/shim/._libgrm.so"):
            c1 = evaluate_c1_slot1_exfat_geometry_and_hygiene(
                slot1_exfat_boot_bytes=vbr,
                slot1_relpaths=[junk],
                staged_artifacts=artifacts,
            )
            self.assertFalse(c1.passed)
            self.assertIn(C1_ERR_MACOS_METADATA_JUNK_DETECTED, c1.error_codes)
            self.assertIn(junk, c1.macos_junk_in_fx6_stageb)

    def test_15_c1_rejects_slot1_bodydata_dat(self) -> None:
        vbr = self._valid_exfat_128kib()
        artifacts = build_simulated_staged_elf64_artifacts()
        c1 = evaluate_c1_slot1_exfat_geometry_and_hygiene(
            slot1_exfat_boot_bytes=vbr,
            slot1_relpaths=["BODYDATA.DAT"],
            staged_artifacts=artifacts,
        )
        self.assertFalse(c1.passed)
        self.assertIn(C1_ERR_SLOT1_BODYDATA_COPRESENCE, c1.error_codes)

    def test_16_c1_rejects_slot1_bodydata_duplicate_1_dat(self) -> None:
        vbr = self._valid_exfat_128kib()
        artifacts = build_simulated_staged_elf64_artifacts()
        for bd in ("BODYDATA (1).DAT", "PRIVATE/BODYDATA (2).DAT"):
            c1 = evaluate_c1_slot1_exfat_geometry_and_hygiene(
                slot1_exfat_boot_bytes=vbr,
                slot1_relpaths=[bd],
                staged_artifacts=artifacts,
            )
            self.assertFalse(c1.passed)
            self.assertIn(C1_ERR_SLOT1_BODYDATA_COPRESENCE, c1.error_codes)

    def test_17_c1_rejects_forbidden_flash_triggers(self) -> None:
        vbr = self._valid_exfat_128kib()
        artifacts = build_simulated_staged_elf64_artifacts()
        for trig in ("edisx.elf", "FX6_STAGEB/nor_loader_writer.sh", "setting/updater/mode"):
            c1 = evaluate_c1_slot1_exfat_geometry_and_hygiene(
                slot1_exfat_boot_bytes=vbr,
                slot1_relpaths=[trig],
                staged_artifacts=artifacts,
            )
            self.assertFalse(c1.passed)
            self.assertIn(C1_ERR_FORBIDDEN_FLASH_TRIGGER, c1.error_codes)

    def test_18_c1_rejects_symlinks_in_sd_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stageb = root / "FX6_STAGEB" / "stage_a"
            stageb.mkdir(parents=True)
            real_jit = stageb / "libJit.so"
            real_jit.write_bytes(build_clean_room_libjit_so())
            sym = root / "FX6_STAGEB" / "evil_link"
            os.symlink(real_jit, sym)

            c1 = evaluate_c1_slot1_exfat_geometry_and_hygiene(
                slot1_exfat_boot_bytes=self._valid_exfat_128kib(),
                sd_dir=root,
            )
            self.assertFalse(c1.passed)
            self.assertGreaterEqual(c1.symlinks_rejected, 1)
            self.assertIn(C1_ERR_SYMLINK_REJECTED, c1.error_codes)

    def test_19_c1_rejects_libjit_exceeding_64kib(self) -> None:
        oversize = build_clean_room_libjit_so(size_bytes=LIBJIT_MAX_SIZE_BYTES + 1)
        artifacts = build_simulated_staged_elf64_artifacts(libjit_bytes=oversize)
        c1 = evaluate_c1_slot1_exfat_geometry_and_hygiene(
            slot1_exfat_boot_bytes=self._valid_exfat_128kib(),
            staged_artifacts=artifacts,
        )
        self.assertFalse(c1.passed)
        self.assertFalse(c1.libjit_within_64kib)
        self.assertIn(C1_ERR_LIBJIT_EXCEEDS_64KIB, c1.error_codes)

    def test_20_c1_rejects_non_aarch64_elf_machine(self) -> None:
        bad_jit = build_clean_room_libjit_so(e_machine=62)  # EM_X86_64
        artifacts = build_simulated_staged_elf64_artifacts(libjit_bytes=bad_jit)
        c1 = evaluate_c1_slot1_exfat_geometry_and_hygiene(
            slot1_exfat_boot_bytes=self._valid_exfat_128kib(),
            staged_artifacts=artifacts,
        )
        self.assertFalse(c1.passed)
        self.assertIn(C1_ERR_ELF64_NOT_AARCH64, c1.error_codes)

    def test_21_c1_rejects_non_64k_pt_load_alignment_on_libjit(self) -> None:
        unaligned_jit = build_clean_room_libjit_so(pt_load_align=0x1000)
        artifacts = build_simulated_staged_elf64_artifacts(libjit_bytes=unaligned_jit)
        c1 = evaluate_c1_slot1_exfat_geometry_and_hygiene(
            slot1_exfat_boot_bytes=self._valid_exfat_128kib(),
            staged_artifacts=artifacts,
        )
        self.assertFalse(c1.passed)
        self.assertIn(C1_ERR_ELF64_NOT_AARCH64, c1.error_codes)

    def test_22_c1_rejects_staged_artifact_sha256_mismatch(self) -> None:
        artifacts = build_simulated_staged_elf64_artifacts()
        blob, _sha = artifacts["FX6_STAGEB/stage_a/libJit.so"]
        artifacts["FX6_STAGEB/stage_a/libJit.so"] = (blob, "f" * 64)
        c1 = evaluate_c1_slot1_exfat_geometry_and_hygiene(
            slot1_exfat_boot_bytes=self._valid_exfat_128kib(),
            staged_artifacts=artifacts,
        )
        self.assertFalse(c1.passed)
        self.assertIn(C1_ERR_ARTIFACT_SHA256_MISMATCH, c1.error_codes)

    def test_23_c1_real_tempdir_sd_dir_and_vbr_file_o_rdonly_pass(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_p = Path(tmp)
            vbr_path = tmp_p / "slot1.vbr"
            vbr_path.write_bytes(self._valid_exfat_128kib())
            sd_root = tmp_p / "sd_card"
            for rel, (blob, _sha) in build_simulated_staged_elf64_artifacts().items():
                dest = sd_root / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(blob)

            c1 = evaluate_c1_slot1_exfat_geometry_and_hygiene(
                slot1_exfat_vbr_path=vbr_path,
                sd_dir=sd_root,
            )
            self.assertTrue(c1.passed, msg=str(c1.errors))
            self.assertEqual(c1.staged_elf64_count, 6)
            self.assertEqual(c1.libjit_size_bytes, 8192)
            self.assertTrue(all(a.elf_machine_aarch64 == EM_AARCH64 for a in c1.staged_artifacts))

    def test_24_c1_rejects_unhealthy_slot2_exfat_if_provided(self) -> None:
        vbr_ok = self._valid_exfat_128kib()
        vbr_slot2_bad = build_synthetic_exfat_boot_region(
            bytes_per_sector_shift=9,
            sectors_per_cluster_shift=5,  # 16 KiB < 128 KiB
        )
        c1 = evaluate_c1_slot1_exfat_geometry_and_hygiene(
            slot1_exfat_boot_bytes=vbr_ok,
            slot2_exfat_boot_bytes=vbr_slot2_bad,
            staged_artifacts=build_simulated_staged_elf64_artifacts(),
        )
        self.assertFalse(c1.passed)
        self.assertIsNotNone(c1.slot2_exfat)
        assert c1.slot2_exfat is not None
        self.assertFalse(c1.slot2_exfat.passed)
        self.assertIn(C1_ERR_CLUSTER_SIZE_BELOW_128KIB, c1.error_codes)

    def test_25_c2_valid_dual_receipts_distinct_st_dev_702(self) -> None:
        sim = build_simulated_dual_receipts_and_h0()
        c2 = evaluate_c2_tier0_dual_media_binding(
            receipt_a_bytes=sim["receipt_a_bytes"],
            receipt_b_bytes=sim["receipt_b_bytes"],
            st_dev_a_override=sim["st_dev_a"],
            st_dev_b_override=sim["st_dev_b"],
            model_id=sim["model_id"],
            body_fw=sim["body_fw"],
            body_serial=sim["body_serial"],
            emmc_cid=sim["emmc_cid"],
            h0_baselines_a=sim["h0_baselines_a"],
            h0_baselines_b=sim["h0_baselines_b"],
        )
        self.assertTrue(c2.passed, msg=str(c2.errors))
        self.assertTrue(c2.distinct_physical_devices)
        self.assertTrue(c2.crc32_parity_ok)
        self.assertTrue(c2.sha256_parity_ok)
        self.assertTrue(c2.model_id_match)
        self.assertTrue(c2.body_fw_match_702)
        self.assertTrue(c2.body_fw_ge_204_floor)
        self.assertTrue(c2.h0_baselines_all_verified)
        self.assertEqual(len(c2.h0_baseline_keys_verified), len(REQUIRED_H0_BASELINE_KEYS))

    def test_26_c2_rejects_missing_receipts(self) -> None:
        c2 = evaluate_c2_tier0_dual_media_binding()
        self.assertFalse(c2.passed)
        self.assertFalse(c2.receipts_provided)
        self.assertIn(C2_ERR_RECEIPT_NOT_PROVIDED, c2.error_codes)

    def test_27_c2_rejects_same_st_dev_collision_override(self) -> None:
        sim = build_simulated_dual_receipts_and_h0()
        c2 = evaluate_c2_tier0_dual_media_binding(
            receipt_a_bytes=sim["receipt_a_bytes"],
            receipt_b_bytes=sim["receipt_b_bytes"],
            st_dev_a_override=123456,
            st_dev_b_override=123456,
            model_id=sim["model_id"],
            body_fw=sim["body_fw"],
            body_serial=sim["body_serial"],
            emmc_cid=sim["emmc_cid"],
            h0_baselines_a=sim["h0_baselines_a"],
        )
        self.assertFalse(c2.passed)
        self.assertFalse(c2.distinct_physical_devices)
        self.assertIn(C2_ERR_SINGLE_DEVICE_ST_DEV_COLLISION, c2.error_codes)

    def test_28_c2_rejects_two_files_on_same_real_tempdir_st_dev(self) -> None:
        sim = build_simulated_dual_receipts_and_h0()
        with tempfile.TemporaryDirectory() as tmp:
            ra = Path(tmp) / "copy_a.bin"
            rb = Path(tmp) / "copy_b.bin"
            ra.write_bytes(sim["receipt_a_bytes"])
            rb.write_bytes(sim["receipt_b_bytes"])
            c2 = evaluate_c2_tier0_dual_media_binding(
                receipt_a_path=ra,
                receipt_b_path=rb,
                model_id=sim["model_id"],
                body_fw=sim["body_fw"],
                body_serial=sim["body_serial"],
                emmc_cid=sim["emmc_cid"],
                h0_baselines_a=sim["h0_baselines_a"],
            )
            self.assertFalse(c2.passed)
            self.assertEqual(c2.st_dev_a, c2.st_dev_b)
            self.assertIn(C2_ERR_SINGLE_DEVICE_ST_DEV_COLLISION, c2.error_codes)

    def test_29_c2_rejects_truncated_or_invalid_528b_receipt(self) -> None:
        sim = build_simulated_dual_receipts_and_h0()
        c2 = evaluate_c2_tier0_dual_media_binding(
            receipt_a_bytes=sim["receipt_a_bytes"][:128],
            receipt_b_bytes=sim["receipt_b_bytes"][:128],
            st_dev_a_override=1,
            st_dev_b_override=2,
            model_id=sim["model_id"],
            body_fw=sim["body_fw"],
            body_serial=sim["body_serial"],
            emmc_cid=sim["emmc_cid"],
            h0_baselines_a=sim["h0_baselines_a"],
        )
        self.assertFalse(c2.passed)
        self.assertIn(C2_ERR_RECEIPT_INVALID_528B, c2.error_codes)

    def test_30_c2_rejects_dual_copy_crc32_sha256_mismatch(self) -> None:
        sim = build_simulated_dual_receipts_and_h0()
        alt = build_simulated_dual_receipts_and_h0(body_serial="9998887")
        c2 = evaluate_c2_tier0_dual_media_binding(
            receipt_a_bytes=sim["receipt_a_bytes"],
            receipt_b_bytes=alt["receipt_b_bytes"],
            st_dev_a_override=1,
            st_dev_b_override=2,
            model_id=sim["model_id"],
            body_fw=sim["body_fw"],
            body_serial=sim["body_serial"],
            emmc_cid=sim["emmc_cid"],
            h0_baselines_a=sim["h0_baselines_a"],
        )
        self.assertFalse(c2.passed)
        self.assertFalse(c2.sha256_parity_ok)
        self.assertIn(C2_ERR_RECEIPT_PAIR_MISMATCH, c2.error_codes)

    def test_31_c2_rejects_wrong_camera_model_id(self) -> None:
        sim = build_simulated_dual_receipts_and_h0()
        c2 = evaluate_c2_tier0_dual_media_binding(
            receipt_a_bytes=sim["receipt_a_bytes"],
            receipt_b_bytes=sim["receipt_b_bytes"],
            st_dev_a_override=1,
            st_dev_b_override=2,
            model_id=0x91030070,
            body_fw=sim["body_fw"],
            body_serial=sim["body_serial"],
            emmc_cid=sim["emmc_cid"],
            h0_baselines_a=sim["h0_baselines_a"],
        )
        self.assertFalse(c2.passed)
        self.assertIn(C2_ERR_MODEL_ID_MISMATCH, c2.error_codes)

    def test_32_c2_rejects_fw_below_204_floor(self) -> None:
        sim = build_simulated_dual_receipts_and_h0()
        c2 = evaluate_c2_tier0_dual_media_binding(
            receipt_a_bytes=sim["receipt_a_bytes"],
            receipt_b_bytes=sim["receipt_b_bytes"],
            st_dev_a_override=1,
            st_dev_b_override=2,
            model_id=TARGET_MODEL_ID_INT,
            body_fw="2.03",
            body_serial=sim["body_serial"],
            emmc_cid=sim["emmc_cid"],
            h0_baselines_a=sim["h0_baselines_a"],
        )
        self.assertFalse(c2.passed)
        self.assertFalse(c2.body_fw_ge_204_floor)
        self.assertIn(C2_ERR_FW_BELOW_204_FLOOR, c2.error_codes)
        self.assertIn(C2_ERR_FW_NOT_TARGET_702, c2.error_codes)

    def test_33_c2_rejects_fw_not_702(self) -> None:
        sim = build_simulated_dual_receipts_and_h0()
        c2 = evaluate_c2_tier0_dual_media_binding(
            receipt_a_bytes=sim["receipt_a_bytes"],
            receipt_b_bytes=sim["receipt_b_bytes"],
            st_dev_a_override=1,
            st_dev_b_override=2,
            model_id=TARGET_MODEL_ID_INT,
            body_fw="6.00",
            body_serial=sim["body_serial"],
            emmc_cid=sim["emmc_cid"],
            h0_baselines_a=sim["h0_baselines_a"],
        )
        self.assertFalse(c2.passed)
        self.assertTrue(c2.body_fw_ge_204_floor)
        self.assertFalse(c2.body_fw_match_702)
        self.assertIn(C2_ERR_FW_NOT_TARGET_702, c2.error_codes)

    def test_34_c2_rejects_trivial_body_serial_or_emmc_cid(self) -> None:
        sim = build_simulated_dual_receipts_and_h0()
        c2 = evaluate_c2_tier0_dual_media_binding(
            receipt_a_bytes=sim["receipt_a_bytes"],
            receipt_b_bytes=sim["receipt_b_bytes"],
            st_dev_a_override=1,
            st_dev_b_override=2,
            model_id=TARGET_MODEL_ID_INT,
            body_fw=TARGET_BODY_FW,
            body_serial="0000000",
            emmc_cid="0" * 32,
            h0_baselines_a=sim["h0_baselines_a"],
        )
        self.assertFalse(c2.passed)
        self.assertIn(C2_ERR_BODY_IDENTITY_INVALID, c2.error_codes)

    def test_35_c2_rejects_each_missing_or_mismatched_h0_baseline_key(self) -> None:
        sim = build_simulated_dual_receipts_and_h0()
        for key in REQUIRED_H0_BASELINE_KEYS:
            bad_h0 = dict(sim["h0_baselines_a"])
            bad_h0.pop(key)
            c2_missing = evaluate_c2_tier0_dual_media_binding(
                receipt_a_bytes=sim["receipt_a_bytes"],
                receipt_b_bytes=sim["receipt_b_bytes"],
                st_dev_a_override=1,
                st_dev_b_override=2,
                model_id=TARGET_MODEL_ID_INT,
                body_fw=TARGET_BODY_FW,
                body_serial=sim["body_serial"],
                emmc_cid=sim["emmc_cid"],
                h0_baselines_a=bad_h0,
                h0_baselines_b=sim["h0_baselines_b"],
            )
            self.assertFalse(c2_missing.passed)
            self.assertIn(key, c2_missing.h0_baseline_missing_or_mismatched)
            self.assertIn(C2_ERR_H0_BASELINE_MISSING_OR_MISMATCH, c2_missing.error_codes)

            mismatch_h0 = dict(sim["h0_baselines_b"])
            mismatch_h0[key] = hashlib.sha256(b"DRIFT").hexdigest()
            c2_mismatch = evaluate_c2_tier0_dual_media_binding(
                receipt_a_bytes=sim["receipt_a_bytes"],
                receipt_b_bytes=sim["receipt_b_bytes"],
                st_dev_a_override=1,
                st_dev_b_override=2,
                model_id=TARGET_MODEL_ID_INT,
                body_fw=TARGET_BODY_FW,
                body_serial=sim["body_serial"],
                emmc_cid=sim["emmc_cid"],
                h0_baselines_a=sim["h0_baselines_a"],
                h0_baselines_b=mismatch_h0,
            )
            self.assertFalse(c2_mismatch.passed)
            self.assertIn(key, c2_mismatch.h0_baseline_missing_or_mismatched)

    def test_36_c3_valid_electrical_cable_thermal_interlock(self) -> None:
        c3 = evaluate_c3_electrical_cable_thermal_interlock()
        self.assertTrue(c3.passed, msg=str(c3.errors))
        self.assertTrue(c3.battery_soc_ge_80pct)
        self.assertTrue(c3.battery_voltage_ge_7v6)
        self.assertTrue(c3.body_temp_under_45c)
        self.assertTrue(c3.pin_8_9_10_contention_free)
        self.assertTrue(c3.hdmi_type_a_passive_safe)
        self.assertTrue(c3.usb_pd_passive_safe)
        self.assertEqual(c3.physical_usb_packets_emitted, 0)

    def test_37_c3_rejects_battery_soc_below_80pct(self) -> None:
        c3 = evaluate_c3_electrical_cable_thermal_interlock(np_fz100_soc_pct=79.9)
        self.assertFalse(c3.passed)
        self.assertFalse(c3.battery_soc_ge_80pct)
        self.assertIn(C3_ERR_BATTERY_SOC_BELOW_80PCT, c3.error_codes)

    def test_38_c3_rejects_battery_voltage_below_7v6_and_ovp(self) -> None:
        c3_low = evaluate_c3_electrical_cable_thermal_interlock(np_fz100_voltage_v=7.59)
        self.assertFalse(c3_low.passed)
        self.assertIn(C3_ERR_BATTERY_VOLTAGE_BELOW_7V6, c3_low.error_codes)

        c3_ovp = evaluate_c3_electrical_cable_thermal_interlock(np_fz100_voltage_v=8.51)
        self.assertFalse(c3_ovp.passed)
        self.assertIn(C3_ERR_BATTERY_OVERVOLTAGE, c3_ovp.error_codes)

    def test_39_c3_rejects_body_temp_at_or_above_45c_and_implausible(self) -> None:
        c3_hot = evaluate_c3_electrical_cable_thermal_interlock(body_temp_c=45.0)
        self.assertFalse(c3_hot.passed)
        self.assertIn(C3_ERR_BODY_TEMP_AT_OR_ABOVE_45C, c3_hot.error_codes)

        c3_cold = evaluate_c3_electrical_cable_thermal_interlock(body_temp_c=-25.0)
        self.assertFalse(c3_cold.passed)
        self.assertIn(C3_ERR_BODY_TEMP_OUT_OF_RANGE, c3_cold.error_codes)

    def test_40_c3_rejects_vmc_bncm1_when_1v8_uart_attached(self) -> None:
        c3 = evaluate_c3_electrical_cable_thermal_interlock(
            uart_rx_1v8_attached=True,
            vmc_bncm1_ltc_attached=True,
        )
        self.assertFalse(c3.passed)
        self.assertFalse(c3.pin_8_9_10_contention_free)
        self.assertIn(C3_ERR_PIN_8_9_10_VMC_BNCM1_UART_CONTENTION, c3.error_codes)

        c3_ltc_only = evaluate_c3_electrical_cable_thermal_interlock(
            uart_rx_1v8_attached=False,
            vmc_bncm1_ltc_attached=True,
        )
        self.assertTrue(c3_ltc_only.passed)

    def test_41_c3_rejects_non_1v8_uart_logic_level(self) -> None:
        c3 = evaluate_c3_electrical_cable_thermal_interlock(
            uart_rx_1v8_attached=True,
            uart_logic_voltage_v=3.3,
        )
        self.assertFalse(c3.passed)
        self.assertIn(C3_ERR_UART_VOLTAGE_NOT_1V8, c3.error_codes)

    def test_42_c3_rejects_hdmi_active_or_pin18_backfeed_and_unsafe_pd(self) -> None:
        c3_backfeed = evaluate_c3_electrical_cable_thermal_interlock(hdmi_pin18_5v_backfeed=True)
        self.assertFalse(c3_backfeed.passed)
        self.assertIn(C3_ERR_HDMI_ACTIVE_OR_BACKFEED, c3_backfeed.error_codes)

        c3_hdmi = evaluate_c3_electrical_cable_thermal_interlock(hdmi_type_a_passive_safe=False)
        self.assertFalse(c3_hdmi.passed)
        self.assertIn(C3_ERR_HDMI_ACTIVE_OR_BACKFEED, c3_hdmi.error_codes)

        c3_pd = evaluate_c3_electrical_cable_thermal_interlock(usb_pd_passive_safe=False)
        self.assertFalse(c3_pd.passed)
        self.assertIn(C3_ERR_USB_PD_UNSAFE, c3_pd.error_codes)

    def test_43_c4_valid_eh1_eh2_eh3_and_h0_h3_16_of_16(self) -> None:
        c4 = evaluate_c4_escape_hatch_and_uninstall_dryrun()
        self.assertTrue(c4.passed, msg=str(c4.errors))
        self.assertTrue(c4.eh1_passed)
        self.assertLess(c4.eh1_observed_latency_us, 50)
        self.assertEqual(c4.eh2_combo_keys, "DISP+MENU+SHUTTER")
        self.assertTrue(c4.eh2_passed)
        self.assertFalse(c4.eh2_stageb_loaded)
        self.assertTrue(c4.eh3_passed)
        self.assertNotEqual(c4.eh3_baseline_crc32_hex, c4.eh3_tampered_crc32_hex)
        self.assertLess(c4.eh3_observed_latency_us, 1000)
        self.assertEqual(c4.h0_h3_surface_count, 16)
        self.assertEqual(c4.h0_equals_h3_count, 16)
        self.assertTrue(c4.h0_equals_h3_all_16)
        self.assertEqual(c4.emmc_writes_during_dryrun, 0)

    def test_44_c4_fault_injection_eh1_latency_ge_50us(self) -> None:
        c4 = evaluate_c4_escape_hatch_and_uninstall_dryrun(inject_eh1_latency_us=50)
        self.assertFalse(c4.passed)
        self.assertFalse(c4.eh1_passed)
        self.assertIn(C4_ERR_EH1_LATENCY_OR_BYPASS_FAILED, c4.error_codes)

    def test_45_c4_fault_injection_eh2_and_eh3(self) -> None:
        c4_eh2 = evaluate_c4_escape_hatch_and_uninstall_dryrun(inject_eh2_bypass_failure=True)
        self.assertFalse(c4_eh2.passed)
        self.assertIn(C4_ERR_EH2_SAFE_COLD_BOOT_FAILED, c4_eh2.error_codes)

        c4_eh3_ign = evaluate_c4_escape_hatch_and_uninstall_dryrun(inject_eh3_crc32_ignored=True)
        self.assertFalse(c4_eh3_ign.passed)
        self.assertIn(C4_ERR_EH3_CRC32_TAMPER_FALLBACK_FAILED, c4_eh3_ign.error_codes)

        c4_eh3_slow = evaluate_c4_escape_hatch_and_uninstall_dryrun(inject_eh3_latency_us=1000)
        self.assertFalse(c4_eh3_slow.passed)
        self.assertIn(C4_ERR_EH3_CRC32_TAMPER_FALLBACK_FAILED, c4_eh3_slow.error_codes)

    def test_46_c4_fault_injection_h0_h3_surface_drift(self) -> None:
        c4 = evaluate_c4_escape_hatch_and_uninstall_dryrun(inject_h0_h3_drift_surface="p12")
        self.assertFalse(c4.passed)
        self.assertFalse(c4.h0_equals_h3_all_16)
        self.assertEqual(c4.h0_equals_h3_count, 15)
        self.assertIn(C4_ERR_H0_H3_SURFACE_DRIFT, c4.error_codes)

    def test_47_default_mode_blocked_awaiting_physical_tier0_receipt(self) -> None:
        rep = run_card_insert_preflight()
        self.assertEqual(rep.schema, PHASE_186_SCHEMA)
        self.assertEqual(rep.phase_version, PHASE_186_VERSION)
        self.assertEqual(rep.go_no_go, GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT)
        self.assertFalse(rep.card_insert_authorized)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.spi_nor_write_authorized)
        self.assertFalse(rep.el3_payload_transmit_authorized)
        self.assertEqual(rep.physical_usb_packets_emitted, 0)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)
        v = verify_phase186_report(rep.to_dict())
        self.assertTrue(v.valid, msg=str(v.errors))

    def test_48_dry_run_simulated_mode_never_authorizes_physical_insert(self) -> None:
        for clean_mode in (None, True):
            rep = run_card_insert_preflight(
                dry_run_simulated=True,
                force_clean_room=clean_mode,
            )
            self.assertEqual(rep.go_no_go, GO_NO_GO_DRY_RUN_SIMULATED_READY)
            self.assertTrue(rep.simulated_dry_run)
            self.assertTrue(rep.all_4_gates_passed)
            self.assertEqual(rep.gates_passed, 4)
            self.assertFalse(rep.card_insert_authorized)
            self.assertFalse(rep.persistent_emmc_writes_authorized)
            self.assertFalse(rep.spi_nor_write_authorized)
            self.assertFalse(rep.el3_payload_transmit_authorized)
            self.assertEqual(rep.physical_usb_packets_emitted, 0)
            self.assertEqual(rep.raw_firmware_bytes_leaked, 0)
            v = verify_phase186_report(rep.to_dict())
            self.assertTrue(v.valid, msg=str(v.errors))

    def test_49_physical_authorized_mode_keeps_emmc_spinor_el3_usb_locked(self) -> None:
        sim = build_simulated_dual_receipts_and_h0()
        rep = run_card_insert_preflight(
            dry_run_simulated=False,
            force_clean_room=True,
            slot1_exfat_boot_bytes=self._valid_exfat_128kib(),
            slot2_exfat_boot_bytes=self._valid_exfat_128kib(volume_serial=0x46583339),
            staged_artifacts=build_simulated_staged_elf64_artifacts(),
            receipt_a_bytes=sim["receipt_a_bytes"],
            receipt_b_bytes=sim["receipt_b_bytes"],
            st_dev_a_override=sim["st_dev_a"],
            st_dev_b_override=sim["st_dev_b"],
            model_id=sim["model_id"],
            body_fw=sim["body_fw"],
            body_serial=sim["body_serial"],
            emmc_cid=sim["emmc_cid"],
            h0_baselines_a=sim["h0_baselines_a"],
            h0_baselines_b=sim["h0_baselines_b"],
        )
        self.assertEqual(rep.go_no_go, GO_NO_GO_PHYSICAL_PREFLIGHT_VERIFIED)
        self.assertTrue(rep.all_4_gates_passed)
        self.assertTrue(rep.card_insert_authorized)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.persistent_write_release)
        self.assertFalse(rep.spi_nor_write_authorized)
        self.assertFalse(rep.el3_payload_transmit_authorized)
        self.assertFalse(rep.sd_physical_media_written)
        self.assertEqual(rep.physical_usb_packets_emitted, 0)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)
        v = verify_phase186_report(rep.to_dict())
        self.assertTrue(v.valid, msg=str(v.errors))

    def test_50_verify_phase186_report_detects_tamper_and_lock_violation(self) -> None:
        rep = run_card_insert_preflight(dry_run_simulated=True, force_clean_room=True)
        base = rep.to_dict()
        self.assertTrue(verify_phase186_report(base).valid)

        for key, bad_val in (
            ("card_insert_authorized", True),
            ("persistent_emmc_writes_authorized", True),
            ("spi_nor_write_authorized", True),
            ("el3_payload_transmit_authorized", True),
            ("physical_usb_packets_emitted", 1),
            ("raw_firmware_bytes_leaked", 4),
            ("go_no_go", "FORGED_PASS"),
        ):
            mutated = copy.deepcopy(base)
            mutated[key] = bad_val
            res = verify_phase186_report(mutated)
            self.assertFalse(res.valid, msg=f"Expected failure for mutated {key}={bad_val}")

    def test_51_no_raw_bytes_literal_repr_in_serialized_json(self) -> None:
        rep = run_card_insert_preflight(dry_run_simulated=True)
        rendered = rep.to_deterministic_json()
        self.assertIsNone(re.search(_RAW_BYTES_REPR_REGEX, rendered))

    def test_52_render_phase186_markdown_contains_gates_and_locks(self) -> None:
        rep = run_card_insert_preflight(dry_run_simulated=True, force_clean_room=True)
        md = render_phase186_markdown(rep)
        for gid in CARD_INSERT_GATE_IDS:
            self.assertIn(gid, md)
        self.assertIn(rep.report_sha256, md)
        self.assertIn("card_insert_authorized=False", md)
        self.assertIn("persistent_emmc_writes_authorized=False", md)

    def test_53_cli_dry_run_simulated_clean_room_and_default_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_p = Path(tmp)
            out_json = tmp_p / "phase186.json"
            out_md = tmp_p / "phase186.md"
            buf = io.StringIO()
            with mock.patch("sys.stdout", buf):
                rc = fx6_cli_main(
                    [
                        "preflight-card-insert",
                        "--force-clean-room",
                        "--dry-run-simulated",
                        "--json",
                        "--output",
                        str(out_json),
                        "--markdown-out",
                        str(out_md),
                    ]
                )
            self.assertEqual(rc, 0)
            payload = json.loads(buf.getvalue())
            self.assertEqual(payload["schema"], PHASE_186_SCHEMA)
            self.assertEqual(payload["go_no_go"], GO_NO_GO_DRY_RUN_SIMULATED_READY)
            self.assertFalse(payload["card_insert_authorized"])
            self.assertTrue(out_json.is_file())
            self.assertTrue(out_md.is_file())
            self.assertTrue(verify_phase186_report(json.loads(out_json.read_text(encoding="utf-8"))).valid)

            buf_blocked = io.StringIO()
            with mock.patch("sys.stdout", buf_blocked):
                rc_blocked = fx6_cli_main(["preflight-card-insert"])
            self.assertEqual(rc_blocked, 1)
            self.assertIn(GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT, buf_blocked.getvalue())

    def test_54_wall_clock_ceiling_under_6_seconds(self) -> None:
        t0 = time.perf_counter()
        rep_clean = run_card_insert_preflight(dry_run_simulated=True, force_clean_room=True)
        rep_auto = run_card_insert_preflight(dry_run_simulated=True)
        elapsed = time.perf_counter() - t0
        self.assertTrue(rep_clean.all_4_gates_passed)
        self.assertTrue(rep_auto.all_4_gates_passed)
        self.assertLess(elapsed, 6.0)


if __name__ == "__main__":
    unittest.main()
