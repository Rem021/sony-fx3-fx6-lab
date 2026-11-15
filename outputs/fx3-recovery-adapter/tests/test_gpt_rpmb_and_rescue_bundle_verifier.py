"""Dual-mode unit tests for Phase 94 CXD90057 GPT CRC32 Healer, RPMB Replay Guard & SD-Rescue Verifier.

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
from fx3_recovery.emmc_dump_forensic_verifier import (
    FX3_PRODUCT_MODEL_ID,
    build_synthetic_sector0_fx3,
)
from fx3_recovery.files import ROOT, is_forced_clean_room
from fx3_recovery.firmware_updata_and_antirollback_guard import FX3_SKU_CODE, FX6_SKU_CODE
from fx3_recovery.gpt_rpmb_and_rescue_bundle_verifier import (
    ALLOW_BOOT_PARTITION_TARGETING,
    ALLOW_DESTRUCTIVE_FASTBOOT,
    CXD90057_FX3_15_PARTITIONS,
    ERR_AIR_GAP_VIOLATION,
    ERR_BLANK_RESCUE_ARTIFACT,
    ERR_CROSS_SKU_FX6_GPT_TRANSPLANT,
    ERR_GPT_BAD_ARRAY_CRC32,
    ERR_GPT_BAD_HEADER_CRC32,
    ERR_GPT_BAD_SIGNATURE,
    ERR_GPT_BOTH_COPIES_CORRUPTED,
    ERR_GPT_MISALIGNED_4K,
    ERR_GPT_OUT_OF_USABLE_RANGE,
    ERR_GPT_PARTITION_OVERLAP,
    ERR_MISSING_SENTINEL_FLAG,
    ERR_PARTIAL_RESCUE_BUNDLE,
    ERR_RESCUE_BODY_BINDING_MISMATCH,
    ERR_RESCUE_PARITY_FAILURE,
    ERR_RESCUE_SHA256_MISMATCH,
    ERR_RPMB_AUTH_FAILURE,
    ERR_RPMB_COUNTER_EXPIRED,
    ERR_RPMB_COUNTER_FAILURE,
    ERR_RPMB_NONCE_MISMATCH,
    ERR_RPMB_PHYSICAL_WRITE_FORBIDDEN,
    ERR_TRUNCATED_RESCUE_ARTIFACT,
    ERR_TWO_MAN_RULE_VIOLATION,
    FX3_GPT_DISK_GUID,
    FX3_LENS_CAL_START_LBA,
    FX6_GPT_DISK_GUID,
    FX6_SHIFTED_LENS_CAL_START_LBA,
    GPT_4K_ALIGNMENT_SECTORS,
    GPT_ARRAY_BYTES,
    GPT_DEFAULT_TOTAL_LBAS,
    GPT_ENTRY_COUNT,
    GPT_ENTRY_SIZE,
    GPT_HEADER_SIZE,
    GPT_RPMB_RESCUE_SCHEMA,
    GPT_SECTOR_SIZE,
    OTP_FUSE_TOUCHES,
    PASSIVE_TX_BYTES_EMITTED,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHYSICAL_DEVICE_WRITES,
    READ_ONLY_DONOR_ACCESS,
    RESCUE_KIT_PARTITION_NAMES,
    RPMB_DATA_BYTES,
    RPMB_FRAME_BYTES,
    RPMB_MAC_BYTES,
    RPMB_MAC_PAYLOAD_BYTES,
    RPMB_MAX_WRITE_COUNTER,
    RPMB_NONCE_BYTES,
    RPMB_REQ_DATA_READ,
    RPMB_REQ_DATA_WRITE,
    RPMB_REQ_GET_WRITE_COUNTER,
    RPMB_RESP_DATA_READ,
    RPMB_RESP_DATA_WRITE,
    RPMB_RESP_GET_WRITE_COUNTER,
    RPMB_RESULT_ADDR_FAILURE,
    RPMB_RESULT_AUTH_FAILURE,
    RPMB_RESULT_COUNTER_EXPIRED,
    RPMB_RESULT_COUNTER_FAILURE,
    RPMB_RESULT_OK,
    RPMB_STUFF_BYTES,
    RPMB_WRITES_EMITTED,
    STATUS_FAIL_GPT_RPMB_BUNDLE,
    STATUS_VERIFIED_GPT_RPMB_BUNDLE,
    SYNTHETIC_RPMB_TEST_KEY,
    GptRpmbAndRescueSuiteReport,
    RpmbSandboxController,
    SdRescueBundleManifest,
    TwoManAttestation,
    build_cxd90057_gpt_pair,
    build_rpmb_frame,
    build_synthetic_sd_rescue_bundle,
    heal_gpt_pair_ram_only,
    inspect_donor_partition_metadata_readonly,
    parse_rpmb_frame,
    prove_stage_b_zero_rpmb_writes,
    run_gpt_rpmb_and_rescue_bundle_suite,
    validate_gpt_side,
    verify_sd_rescue_bundle,
)
from fx3_recovery.tier0_backup_parity_and_manifest_guard import build_body_hardware_identity


def _flip_byte(data: bytes, offset: int) -> bytes:
    buf = bytearray(data)
    buf[offset] ^= 0x5A
    return bytes(buf)


class GptRpmbAndRescueBundleVerifierTests(unittest.TestCase):
    suite_report: GptRpmbAndRescueSuiteReport

    @classmethod
    def setUpClass(cls) -> None:
        cls.suite_report = run_gpt_rpmb_and_rescue_bundle_suite()

    def setUp(self) -> None:
        self._sandbox = (
            ROOT / "outputs" / "fx3-recovery-adapter" / f".tmp-phase94-test-{os.getpid()}-{time.time_ns()}"
        )

    def tearDown(self) -> None:
        shutil.rmtree(self._sandbox, ignore_errors=True)

    # ------------------------------------------------------------------
    # Safety Constants, Exports & Donor Read-Only Inspection
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
        self.assertEqual(RPMB_WRITES_EMITTED, 0)
        self.assertEqual(len(CXD90057_FX3_15_PARTITIONS), 15)
        self.assertEqual(len(RESCUE_KIT_PARTITION_NAMES), 15)
        self.assertEqual(fx3_recovery.GPT_RPMB_RESCUE_SCHEMA, GPT_RPMB_RESCUE_SCHEMA)
        for symbol in (
            "build_cxd90057_gpt_pair",
            "validate_gpt_side",
            "heal_gpt_pair_ram_only",
            "build_rpmb_frame",
            "parse_rpmb_frame",
            "RpmbSandboxController",
            "prove_stage_b_zero_rpmb_writes",
            "build_synthetic_sd_rescue_bundle",
            "verify_sd_rescue_bundle",
            "run_gpt_rpmb_and_rescue_bundle_suite",
        ):
            self.assertIn(symbol, fx3_recovery.__all__)

    def test_02_donor_inspection_dual_mode_and_readonly_sha256(self) -> None:
        snap_default = inspect_donor_partition_metadata_readonly()
        snap_clean = inspect_donor_partition_metadata_readonly(force_clean_room=True)

        if is_forced_clean_room():
            self.assertEqual(snap_default.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertEqual(snap_default.snapshot_sha256, snap_clean.snapshot_sha256)
        else:
            self.assertIn(snap_default.verification_mode, ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"))
        self.assertEqual(snap_clean.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(snap_default.read_only_access)
        self.assertEqual(len(snap_default.artifacts), 4)
        for art in snap_default.artifacts:
            self.assertTrue(art.magic_ok, f"magic check failed for {art.label}: {art.details}")
            self.assertEqual(len(art.sha256), 64)

    # ------------------------------------------------------------------
    # Pillar 1: Primary vs Backup GPT CRC32 & Partition Overlap Healer
    # ------------------------------------------------------------------

    def test_03_gpt_15_partition_cxd90057_geometry_and_4k_alignment(self) -> None:
        self.assertEqual(GPT_HEADER_SIZE, 92)
        self.assertEqual(GPT_ENTRY_COUNT * GPT_ENTRY_SIZE, GPT_ARRAY_BYTES)
        self.assertEqual(GPT_ARRAY_BYTES, 16384)
        pri_hdr, pri_arr, bak_hdr, bak_arr = build_cxd90057_gpt_pair(sku=FX3_SKU_CODE)
        self.assertEqual(len(pri_hdr), GPT_SECTOR_SIZE)
        self.assertEqual(len(bak_hdr), GPT_SECTOR_SIZE)
        self.assertEqual(len(pri_arr), GPT_ARRAY_BYTES)
        self.assertEqual(pri_arr, bak_arr)

        pri_audit = validate_gpt_side(
            pri_hdr,
            pri_arr,
            side="primary_lba1",
            expected_my_lba=1,
            expected_alt_lba=GPT_DEFAULT_TOTAL_LBAS - 1,
            expected_entry_lba=2,
        )
        self.assertTrue(pri_audit.valid)
        self.assertTrue(pri_audit.header_crc32_ok)
        self.assertTrue(pri_audit.array_crc32_ok)
        self.assertTrue(pri_audit.alignment_4k_ok)
        self.assertTrue(pri_audit.no_overlaps_ok)
        self.assertTrue(pri_audit.sku_match_ok)
        self.assertEqual(pri_audit.active_partition_count, 15)
        self.assertEqual(pri_audit.partitions[-1].starting_lba, FX3_LENS_CAL_START_LBA)
        for part in pri_audit.partitions:
            self.assertEqual(part.starting_lba % GPT_4K_ALIGNMENT_SECTORS, 0)
            self.assertEqual(part.size_lbas % GPT_4K_ALIGNMENT_SECTORS, 0)
            self.assertTrue(part.aligned_4k)

    def test_04_gpt_healthy_pair_requires_no_heal(self) -> None:
        pri_hdr, pri_arr, bak_hdr, bak_arr = build_cxd90057_gpt_pair(sku=FX3_SKU_CODE)
        res, out = heal_gpt_pair_ram_only(pri_hdr, pri_arr, bak_hdr, bak_arr)
        self.assertTrue(res.passed)
        self.assertEqual(res.action, "HEALTHY_NO_HEAL_NEEDED")
        self.assertTrue(res.ram_only)
        self.assertEqual(res.physical_device_writes, 0)
        self.assertFalse(res.persistent_emmc_writes_authorized)
        self.assertIsNotNone(out)

    def test_05_gpt_reconstructs_corrupted_primary_from_backup_ram_only(self) -> None:
        pri_hdr, pri_arr, bak_hdr, bak_arr = build_cxd90057_gpt_pair(sku=FX3_SKU_CODE)
        bad_pri_hdr = _flip_byte(pri_hdr, 0)  # Corrupt 'EFI PART' signature
        bad_pri_arr = _flip_byte(pri_arr, 128)
        res, out = heal_gpt_pair_ram_only(bad_pri_hdr, bad_pri_arr, bak_hdr, bak_arr)
        self.assertTrue(res.passed)
        self.assertEqual(res.action, "RECONSTRUCTED_PRIMARY_FROM_BACKUP_RAM_ONLY")
        self.assertFalse(res.primary_before_valid)
        self.assertTrue(res.backup_before_valid)
        self.assertTrue(res.primary_after_valid)
        self.assertTrue(res.backup_after_valid)
        self.assertEqual(res.physical_device_writes, 0)
        self.assertIsNotNone(out)
        assert out is not None
        self.assertEqual(out[0], pri_hdr)
        self.assertEqual(out[1], pri_arr)

    def test_06_gpt_reconstructs_corrupted_primary_header_crc32_from_backup(self) -> None:
        pri_hdr, pri_arr, bak_hdr, bak_arr = build_cxd90057_gpt_pair(sku=FX3_SKU_CODE)
        bad_crc_hdr = _flip_byte(pri_hdr, 16)
        res, out = heal_gpt_pair_ram_only(bad_crc_hdr, pri_arr, bak_hdr, bak_arr)
        self.assertTrue(res.passed)
        self.assertIsNotNone(out)
        assert out is not None
        self.assertEqual(out[0], pri_hdr)

    def test_07_gpt_reconstructs_corrupted_backup_from_primary_ram_only(self) -> None:
        pri_hdr, pri_arr, bak_hdr, bak_arr = build_cxd90057_gpt_pair(sku=FX3_SKU_CODE)
        bad_bak_hdr = _flip_byte(bak_hdr, 20)
        bad_bak_arr = _flip_byte(bak_arr, 40)
        res, out = heal_gpt_pair_ram_only(pri_hdr, pri_arr, bad_bak_hdr, bad_bak_arr)
        self.assertTrue(res.passed)
        self.assertEqual(res.action, "RECONSTRUCTED_BACKUP_FROM_PRIMARY_RAM_ONLY")
        self.assertTrue(res.primary_before_valid)
        self.assertFalse(res.backup_before_valid)
        self.assertTrue(res.primary_after_valid)
        self.assertTrue(res.backup_after_valid)
        self.assertIsNotNone(out)
        assert out is not None
        self.assertEqual(out[2], bak_hdr)
        self.assertEqual(out[3], bak_arr)

    def test_08_gpt_dual_corruption_fails_closed(self) -> None:
        pri_hdr, pri_arr, bak_hdr, bak_arr = build_cxd90057_gpt_pair(sku=FX3_SKU_CODE)
        bad_pri = _flip_byte(pri_hdr, 16)
        bad_bak = _flip_byte(bak_hdr, 16)
        res, out = heal_gpt_pair_ram_only(bad_pri, pri_arr, bad_bak, bak_arr)
        self.assertFalse(res.passed)
        self.assertIsNone(out)
        self.assertIn(ERR_GPT_BOTH_COPIES_CORRUPTED, res.error_codes)
        self.assertIn(ERR_GPT_BAD_HEADER_CRC32, res.primary_audit.error_codes)

    def test_09_gpt_blocks_bad_signature_and_bad_array_crc32(self) -> None:
        pri_hdr, pri_arr, _bak_hdr, _bak_arr = build_cxd90057_gpt_pair(sku=FX3_SKU_CODE)
        bad_sig = validate_gpt_side(
            _flip_byte(pri_hdr, 0),
            pri_arr,
            side="pri",
            expected_my_lba=1,
            expected_alt_lba=GPT_DEFAULT_TOTAL_LBAS - 1,
            expected_entry_lba=2,
        )
        self.assertFalse(bad_sig.valid)
        self.assertIn(ERR_GPT_BAD_SIGNATURE, bad_sig.error_codes)

        bad_arr = validate_gpt_side(
            pri_hdr,
            _flip_byte(pri_arr, 60),
            side="pri",
            expected_my_lba=1,
            expected_alt_lba=GPT_DEFAULT_TOTAL_LBAS - 1,
            expected_entry_lba=2,
        )
        self.assertFalse(bad_arr.valid)
        self.assertIn(ERR_GPT_BAD_ARRAY_CRC32, bad_arr.error_codes)

    def test_10_gpt_blocks_overlapping_lba_ranges(self) -> None:
        parts = list(CXD90057_FX3_15_PARTITIONS)
        parts[1] = (2, "p2_overlap", 0x0000B000, 0x0000B000, "bk4_overlap")
        ph, pa, bh, ba = build_cxd90057_gpt_pair(sku=FX3_SKU_CODE, partitions=parts)
        res, out = heal_gpt_pair_ram_only(ph, pa, bh, ba)
        self.assertFalse(res.passed)
        self.assertIsNone(out)
        self.assertIn(ERR_GPT_PARTITION_OVERLAP, res.primary_audit.error_codes)

    def test_11_gpt_blocks_misaligned_4k_boundaries(self) -> None:
        parts = list(CXD90057_FX3_15_PARTITIONS)
        parts[1] = (2, "p2_misaligned", 0x0000C001, 0x00009FFF, "bk4_misaligned")
        ph, pa, bh, ba = build_cxd90057_gpt_pair(sku=FX3_SKU_CODE, partitions=parts)
        res, out = heal_gpt_pair_ram_only(ph, pa, bh, ba)
        self.assertFalse(res.passed)
        self.assertIsNone(out)
        self.assertIn(ERR_GPT_MISALIGNED_4K, res.primary_audit.error_codes)

    def test_12_gpt_blocks_out_of_usable_range_partition(self) -> None:
        parts = list(CXD90057_FX3_15_PARTITIONS)
        parts[0] = (1, "p1_too_low", 0x00000028, 0x0000BF80, "vfat")
        ph, pa, bh, ba = build_cxd90057_gpt_pair(sku=FX3_SKU_CODE, partitions=parts)
        res, out = heal_gpt_pair_ram_only(ph, pa, bh, ba)
        self.assertFalse(res.passed)
        self.assertIsNone(out)
        self.assertIn(ERR_GPT_OUT_OF_USABLE_RANGE, res.primary_audit.error_codes)

    def test_13_gpt_blocks_cross_sku_fx6_geometry_transplant_onto_fx3(self) -> None:
        fx6_ph, fx6_pa, fx6_bh, fx6_ba = build_cxd90057_gpt_pair(sku=FX6_SKU_CODE)
        self.assertNotEqual(FX6_GPT_DISK_GUID, FX3_GPT_DISK_GUID)
        res, out = heal_gpt_pair_ram_only(fx6_ph, fx6_pa, fx6_bh, fx6_ba, target_sku=FX3_SKU_CODE)
        self.assertFalse(res.passed)
        self.assertIsNone(out)
        self.assertIn(ERR_CROSS_SKU_FX6_GPT_TRANSPLANT, res.primary_audit.error_codes)
        self.assertIn(FX6_SHIFTED_LENS_CAL_START_LBA, [p.starting_lba for p in res.primary_audit.partitions])

    def test_14_gpt_blocks_divergent_primary_and_backup_arrays(self) -> None:
        ph, pa, bh, ba = build_cxd90057_gpt_pair(sku=FX3_SKU_CODE)
        alt_parts = list(CXD90057_FX3_15_PARTITIONS)
        alt_parts[12] = (13, "p13_renamed_cfg", 0x00220000, 0x00002000, "userdata")
        _, _, alt_bh, alt_ba = build_cxd90057_gpt_pair(sku=FX3_SKU_CODE, partitions=alt_parts)
        res, out = heal_gpt_pair_ram_only(ph, pa, alt_bh, alt_ba)
        self.assertFalse(res.passed)
        self.assertIsNone(out)
        self.assertEqual(res.action, "REJECTED_PRIMARY_BACKUP_ARRAY_DIVERGENCE")

    def test_15_gpt_blocks_fx6_shifted_sony_sector0_with_valid_gpt(self) -> None:
        ph, pa, bh, ba = build_cxd90057_gpt_pair(sku=FX3_SKU_CODE)
        sec0_fx6 = bytearray(build_synthetic_sector0_fx3())
        # Shift p7=0, p12=0xA000, p18=0x312000, p20=0x32000, p21=0x16400 (FX6 Sector0 signature)
        struct.pack_into("<I", sec0_fx6, 32 + 6 * 16 + 4, 0)
        struct.pack_into("<I", sec0_fx6, 32 + 11 * 16 + 4, 0x0000A000)
        struct.pack_into("<I", sec0_fx6, 32 + 17 * 16, 0x00312000)
        struct.pack_into("<II", sec0_fx6, 32 + 19 * 16, 0x00350000, 0x00032000)
        struct.pack_into("<II", sec0_fx6, 32 + 20 * 16, 0x00382000, 0x00016400)
        res, out = heal_gpt_pair_ram_only(ph, pa, bh, ba, sector0_bytes=bytes(sec0_fx6))
        self.assertFalse(res.passed)
        self.assertFalse(res.sector0_fx3_valid)
        self.assertIsNone(out)

    # ------------------------------------------------------------------
    # Pillar 2: JEDEC eMMC 5.1 RPMB Monotonic Write-Counter & Replay Guard
    # ------------------------------------------------------------------

    def test_16_rpmb_frame_layout_512_bytes_and_synthetic_key(self) -> None:
        self.assertEqual(RPMB_STUFF_BYTES + RPMB_MAC_BYTES + RPMB_MAC_PAYLOAD_BYTES, RPMB_FRAME_BYTES)
        self.assertEqual(RPMB_FRAME_BYTES, 512)
        self.assertEqual(RPMB_DATA_BYTES + RPMB_NONCE_BYTES + 4 + 2 + 2 + 2 + 2, 284)
        self.assertEqual(len(SYNTHETIC_RPMB_TEST_KEY), 32)

        nonce = bytes.fromhex("00112233445566778899aabbccddeeff")
        frame = build_rpmb_frame(
            req_resp=RPMB_REQ_DATA_WRITE,
            data=b"HELLO_FX3_RPMB",
            nonce=nonce,
            write_counter=100,
            address=5,
            block_count=1,
        )
        self.assertEqual(len(frame), 512)
        info = parse_rpmb_frame(frame)
        self.assertEqual(info.req_resp, RPMB_REQ_DATA_WRITE)
        self.assertEqual(info.write_counter, 100)
        self.assertEqual(info.address, 5)
        self.assertEqual(info.block_count, 1)
        self.assertEqual(info.nonce_hex, nonce.hex())

    def test_17_rpmb_get_write_counter_and_read_roundtrip(self) -> None:
        box = RpmbSandboxController(initial_counter=77)
        nonce = b"\x12" * 16
        get_req = build_rpmb_frame(req_resp=RPMB_REQ_GET_WRITE_COUNTER, nonce=nonce)
        resp_info, resp_bytes = box.process_frame(get_req, expected_nonce=nonce)
        self.assertTrue(resp_info.accepted)
        self.assertEqual(resp_info.req_resp, RPMB_RESP_GET_WRITE_COUNTER)
        self.assertEqual(resp_info.result_code, RPMB_RESULT_OK)
        self.assertEqual(resp_info.write_counter_after, 77)
        self.assertEqual(resp_info.rpmb_writes_emitted, 0)
        self.assertEqual(parse_rpmb_frame(resp_bytes).write_counter, 77)

        read_req = build_rpmb_frame(req_resp=RPMB_REQ_DATA_READ, nonce=nonce, address=2)
        read_info, read_bytes = box.process_frame(read_req)
        self.assertTrue(read_info.accepted)
        self.assertEqual(read_info.req_resp, RPMB_RESP_DATA_READ)
        self.assertEqual(read_info.rpmb_writes_emitted, 0)
        self.assertEqual(len(read_bytes), 512)

    def test_18_rpmb_authenticated_write_increments_sandbox_counter_zero_hw_writes(self) -> None:
        box = RpmbSandboxController(initial_counter=10)
        nonce = b"\x33" * 16
        box.issue_challenge_nonce(nonce)
        req = build_rpmb_frame(
            req_resp=RPMB_REQ_DATA_WRITE,
            data=b"FX3_CLEAN_ROOM_TEST_BLOCK",
            nonce=nonce,
            write_counter=10,
            address=1,
            block_count=1,
        )
        res, resp_bytes = box.process_frame(req, expected_nonce=nonce)
        self.assertTrue(res.accepted)
        self.assertEqual(res.result_code, RPMB_RESULT_OK)
        self.assertEqual(res.req_resp, RPMB_RESP_DATA_WRITE)
        self.assertEqual(res.write_counter_before, 10)
        self.assertEqual(res.write_counter_after, 11)
        self.assertEqual(box.write_counter, 11)
        self.assertEqual(res.rpmb_writes_emitted, 0)
        self.assertEqual(res.physical_device_writes, 0)
        self.assertFalse(res.persistent_emmc_writes_authorized)
        self.assertEqual(parse_rpmb_frame(resp_bytes).write_counter, 11)

    def test_19_rpmb_rejects_stale_counter_replay_0x0003(self) -> None:
        box = RpmbSandboxController(initial_counter=10)
        n1 = b"\x01" * 16
        box.issue_challenge_nonce(n1)
        req1 = build_rpmb_frame(req_resp=RPMB_REQ_DATA_WRITE, data=b"A", nonce=n1, write_counter=10, address=0)
        res1, _ = box.process_frame(req1, expected_nonce=n1)
        self.assertTrue(res1.accepted)

        # Replay counter=10 with a fresh nonce -> RESULT_COUNTER_FAILURE (0x0003)
        n2 = b"\x02" * 16
        box.issue_challenge_nonce(n2)
        stale = build_rpmb_frame(req_resp=RPMB_REQ_DATA_WRITE, data=b"A", nonce=n2, write_counter=10, address=0)
        res2, _ = box.process_frame(stale, expected_nonce=n2)
        self.assertFalse(res2.accepted)
        self.assertEqual(res2.result_code, RPMB_RESULT_COUNTER_FAILURE)
        self.assertIn(ERR_RPMB_COUNTER_FAILURE, res2.error_codes)
        self.assertEqual(box.write_counter, 11)

    def test_20_rpmb_rejects_future_counter_jump_0x0003(self) -> None:
        box = RpmbSandboxController(initial_counter=10)
        n = b"\x05" * 16
        box.issue_challenge_nonce(n)
        jump = build_rpmb_frame(req_resp=RPMB_REQ_DATA_WRITE, data=b"B", nonce=n, write_counter=12, address=0)
        res, _ = box.process_frame(jump, expected_nonce=n)
        self.assertFalse(res.accepted)
        self.assertEqual(res.result_code, RPMB_RESULT_COUNTER_FAILURE)
        self.assertEqual(box.write_counter, 10)

    def test_21_rpmb_rejects_nonce_mismatch(self) -> None:
        box = RpmbSandboxController(initial_counter=10)
        expected_n = b"\xAA" * 16
        replayed_n = b"\xBB" * 16
        box.issue_challenge_nonce(expected_n)
        req = build_rpmb_frame(req_resp=RPMB_REQ_DATA_WRITE, data=b"C", nonce=replayed_n, write_counter=10, address=0)
        res, _ = box.process_frame(req, expected_nonce=expected_n)
        self.assertFalse(res.accepted)
        self.assertFalse(res.nonce_valid)
        self.assertIn(ERR_RPMB_NONCE_MISMATCH, res.error_codes)
        self.assertEqual(box.write_counter, 10)

    def test_22_rpmb_rejects_mac_forgery_0x0002(self) -> None:
        box = RpmbSandboxController(initial_counter=10)
        n = b"\x44" * 16
        box.issue_challenge_nonce(n)
        forged = build_rpmb_frame(
            req_resp=RPMB_REQ_DATA_WRITE,
            data=b"FORGED_PAYLOAD",
            nonce=n,
            write_counter=10,
            address=0,
            override_mac=b"\x00" * 32,
        )
        res, _ = box.process_frame(forged, expected_nonce=n)
        self.assertFalse(res.accepted)
        self.assertFalse(res.mac_valid)
        self.assertEqual(res.result_code, RPMB_RESULT_AUTH_FAILURE)
        self.assertIn(ERR_RPMB_AUTH_FAILURE, res.error_codes)
        self.assertEqual(box.write_counter, 10)

    def test_23_rpmb_rejects_counter_exhaustion_0xffffffff_0x0080(self) -> None:
        box = RpmbSandboxController(initial_counter=RPMB_MAX_WRITE_COUNTER)
        n = b"\x77" * 16
        box.issue_challenge_nonce(n)
        req = build_rpmb_frame(
            req_resp=RPMB_REQ_DATA_WRITE,
            data=b"EXHAUSTED",
            nonce=n,
            write_counter=RPMB_MAX_WRITE_COUNTER,
            address=0,
        )
        res, _ = box.process_frame(req, expected_nonce=n)
        self.assertFalse(res.accepted)
        self.assertTrue(res.counter_expired)
        self.assertEqual(res.result_code, RPMB_RESULT_COUNTER_EXPIRED)
        self.assertIn(ERR_RPMB_COUNTER_EXPIRED, res.error_codes)

        get_req = build_rpmb_frame(req_resp=RPMB_REQ_GET_WRITE_COUNTER, nonce=n)
        get_res, _ = box.process_frame(get_req, expected_nonce=n)
        self.assertFalse(get_res.accepted)
        self.assertEqual(get_res.result_code, RPMB_RESULT_COUNTER_EXPIRED)

    def test_24_rpmb_rejects_out_of_range_addr_and_physical_write_attempt(self) -> None:
        box = RpmbSandboxController(initial_counter=5, max_blocks=8)
        n = b"\x88" * 16
        bad_read = build_rpmb_frame(req_resp=RPMB_REQ_DATA_READ, nonce=n, address=99)
        r_res, _ = box.process_frame(bad_read)
        self.assertFalse(r_res.accepted)
        self.assertEqual(r_res.result_code, RPMB_RESULT_ADDR_FAILURE)

        box.issue_challenge_nonce(n)
        req = build_rpmb_frame(req_resp=RPMB_REQ_DATA_WRITE, data=b"X", nonce=n, write_counter=5, address=1)
        phys_res, _ = box.process_frame(req, allow_physical_rpmb_write=True)
        self.assertFalse(phys_res.accepted)
        self.assertIn(ERR_RPMB_PHYSICAL_WRITE_FORBIDDEN, phys_res.error_codes)
        self.assertEqual(phys_res.rpmb_writes_emitted, 0)

    def test_25_stage_b_overlay_proves_zero_rpmb_writes(self) -> None:
        proof = prove_stage_b_zero_rpmb_writes()
        self.assertTrue(proof.passed)
        self.assertEqual(proof.rpmb_writes_emitted, 0)
        self.assertEqual(proof.otp_fuse_touches, 0)
        self.assertEqual(proof.physical_device_writes, 0)
        self.assertFalse(proof.persistent_emmc_writes_authorized)
        self.assertFalse(proof.persistent_write_release)

        bad_proof = prove_stage_b_zero_rpmb_writes(mount_base="/mnt/emmc_persistent")
        self.assertFalse(bad_proof.passed)

    # ------------------------------------------------------------------
    # Pillar 3: Offline Air-Gapped SD-Rescue Bundle & Two-Man Integrity
    # ------------------------------------------------------------------

    def test_26_sd_rescue_valid_bundle_permits_stage_b_rehearsal(self) -> None:
        parts, sentinel, p_par, q_par, body_id, manifest = build_synthetic_sd_rescue_bundle()
        rep = verify_sd_rescue_bundle(
            parts,
            sentinel,
            p_par,
            q_par,
            manifest,
            target_body_identity=body_id,
        )
        self.assertTrue(rep.passed)
        self.assertTrue(rep.stage_b_rehearsal_permitted)
        self.assertEqual(rep.status, STATUS_VERIFIED_GPT_RPMB_BUNDLE)
        self.assertTrue(rep.sentinel_verified)
        self.assertEqual(rep.partition_count_verified, 15)
        self.assertTrue(rep.parity_verified)
        self.assertTrue(rep.parity_single_loss_heal_verified)
        self.assertTrue(rep.body_binding_verified)
        self.assertTrue(rep.two_man_rule_verified)
        self.assertTrue(rep.air_gapped_verified)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertEqual(rep.physical_device_writes, 0)

    def test_27_sd_rescue_blocks_missing_or_tampered_sentinel(self) -> None:
        parts, sentinel, p_par, q_par, body_id, manifest = build_synthetic_sd_rescue_bundle()
        rep_none = verify_sd_rescue_bundle(parts, None, p_par, q_par, manifest, target_body_identity=body_id)
        self.assertFalse(rep_none.passed)
        self.assertFalse(rep_none.stage_b_rehearsal_permitted)
        self.assertIn(ERR_MISSING_SENTINEL_FLAG, rep_none.error_codes)

        rep_bad = verify_sd_rescue_bundle(parts, b"TAMPERED", p_par, q_par, manifest, target_body_identity=body_id)
        self.assertFalse(rep_bad.passed)
        self.assertIn(ERR_MISSING_SENTINEL_FLAG, rep_bad.error_codes)

    def test_28_sd_rescue_blocks_missing_or_truncated_partition(self) -> None:
        parts, sentinel, p_par, q_par, body_id, manifest = build_synthetic_sd_rescue_bundle()

        partial = dict(parts)
        partial["p7_rootfs"] = None  # type: ignore[assignment]
        rep_part = verify_sd_rescue_bundle(partial, sentinel, p_par, q_par, manifest, target_body_identity=body_id)
        self.assertFalse(rep_part.passed)
        self.assertFalse(rep_part.stage_b_rehearsal_permitted)
        self.assertIn(ERR_PARTIAL_RESCUE_BUNDLE, rep_part.error_codes)

        trunc = dict(parts)
        trunc["p5_wbi2_hibdrv"] = parts["p5_wbi2_hibdrv"][:512]
        rep_trunc = verify_sd_rescue_bundle(trunc, sentinel, p_par, q_par, manifest, target_body_identity=body_id)
        self.assertFalse(rep_trunc.passed)
        self.assertFalse(rep_trunc.stage_b_rehearsal_permitted)
        self.assertIn(ERR_TRUNCATED_RESCUE_ARTIFACT, rep_trunc.error_codes)

    def test_29_sd_rescue_blocks_blank_and_sha256_mismatch_artifacts(self) -> None:
        parts, sentinel, p_par, q_par, body_id, manifest = build_synthetic_sd_rescue_bundle()

        blank = dict(parts)
        blank["p3_kernel_scel"] = b"\x00" * len(parts["p3_kernel_scel"])
        rep_blank = verify_sd_rescue_bundle(blank, sentinel, p_par, q_par, manifest, target_body_identity=body_id)
        self.assertFalse(rep_blank.passed)
        self.assertIn(ERR_BLANK_RESCUE_ARTIFACT, rep_blank.error_codes)

        corrupt = dict(parts)
        corrupt["p3_kernel_scel"] = _flip_byte(parts["p3_kernel_scel"], 12)
        rep_sha = verify_sd_rescue_bundle(corrupt, sentinel, p_par, q_par, manifest, target_body_identity=body_id)
        self.assertFalse(rep_sha.passed)
        self.assertIn(ERR_RESCUE_SHA256_MISMATCH, rep_sha.error_codes)

    def test_30_sd_rescue_blocks_corrupted_gf256_parity(self) -> None:
        parts, sentinel, p_par, q_par, body_id, manifest = build_synthetic_sd_rescue_bundle()
        bad_q = _flip_byte(q_par, 10)
        rep = verify_sd_rescue_bundle(parts, sentinel, p_par, bad_q, manifest, target_body_identity=body_id)
        self.assertFalse(rep.passed)
        self.assertFalse(rep.parity_verified)
        self.assertIn(ERR_RESCUE_PARITY_FAILURE, rep.error_codes)

    def test_31_sd_rescue_blocks_cross_body_serial_transplant(self) -> None:
        parts, sentinel, p_par, q_par, _body_id, manifest = build_synthetic_sd_rescue_bundle()
        other_body = build_body_hardware_identity(
            camera_model=FX3_SKU_CODE,
            body_serial_hash="b" * 64,
            cnflasha_calibration_sha256=manifest.cnflasha_calibration_sha256,
            c2pa_rq_lic_sha256=manifest.c2pa_rq_lic_sha256,
        )
        rep = verify_sd_rescue_bundle(parts, sentinel, p_par, q_par, manifest, target_body_identity=other_body)
        self.assertFalse(rep.passed)
        self.assertFalse(rep.body_binding_verified)
        self.assertFalse(rep.stage_b_rehearsal_permitted)
        self.assertIn(ERR_RESCUE_BODY_BINDING_MISMATCH, rep.error_codes)

    def test_32_sd_rescue_blocks_two_man_and_air_gap_violations(self) -> None:
        parts, sentinel, p_par, q_par, body_id, manifest = build_synthetic_sd_rescue_bundle()

        same_op = TwoManAttestation(
            operator_a_id="op-alpha-bench",
            operator_a_signature_sha256=manifest.two_man_attestation.operator_a_signature_sha256,
            operator_b_id="op-alpha-bench",
            operator_b_signature_sha256=manifest.two_man_attestation.operator_a_signature_sha256,
            air_gapped=True,
            network_interfaces_disabled=True,
        )
        m_same = SdRescueBundleManifest(**{**manifest.__dict__, "two_man_attestation": same_op})
        rep_same = verify_sd_rescue_bundle(parts, sentinel, p_par, q_par, m_same, target_body_identity=body_id)
        self.assertFalse(rep_same.passed)
        self.assertIn(ERR_TWO_MAN_RULE_VIOLATION, rep_same.error_codes)

        net_on = TwoManAttestation(
            operator_a_id=manifest.two_man_attestation.operator_a_id,
            operator_a_signature_sha256=manifest.two_man_attestation.operator_a_signature_sha256,
            operator_b_id=manifest.two_man_attestation.operator_b_id,
            operator_b_signature_sha256=manifest.two_man_attestation.operator_b_signature_sha256,
            air_gapped=False,
            network_interfaces_disabled=False,
        )
        m_net = SdRescueBundleManifest(**{**manifest.__dict__, "two_man_attestation": net_on})
        rep_net = verify_sd_rescue_bundle(parts, sentinel, p_par, q_par, m_net, target_body_identity=body_id)
        self.assertFalse(rep_net.passed)
        self.assertIn(ERR_AIR_GAP_VIOLATION, rep_net.error_codes)

    # ------------------------------------------------------------------
    # Unified Suite, Determinism, CLI & Clean-Room JSON Hygiene
    # ------------------------------------------------------------------

    def test_33_unified_suite_all_passed_and_determinism(self) -> None:
        rep = self.suite_report
        self.assertTrue(rep.all_passed)
        self.assertEqual(rep.status, STATUS_VERIFIED_GPT_RPMB_BUNDLE)
        self.assertEqual(len(rep.suite_sha256), 64)
        self.assertEqual(rep.otp_fuse_touches, 0)
        self.assertEqual(rep.passive_tx_bytes_emitted, 0)
        self.assertEqual(rep.rpmb_writes_emitted, 0)
        self.assertEqual(rep.physical_device_writes, 0)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.persistent_write_release)
        self.assertTrue(rep.gpt_reject_overlap_passed)
        self.assertTrue(rep.gpt_reject_misaligned_4k_passed)
        self.assertTrue(rep.gpt_reject_fx6_transplant_passed)
        self.assertTrue(rep.gpt_reject_both_corrupted_passed)
        self.assertTrue(rep.rpmb_authenticated_write_passed)
        self.assertTrue(rep.rpmb_reject_stale_counter_passed)
        self.assertTrue(rep.rpmb_reject_nonce_mismatch_passed)
        self.assertTrue(rep.rpmb_reject_mac_forgery_passed)
        self.assertTrue(rep.rpmb_reject_counter_expired_passed)
        self.assertTrue(rep.sd_rescue_reject_missing_sentinel_passed)
        self.assertTrue(rep.sd_rescue_reject_truncated_artifact_passed)
        self.assertTrue(rep.sd_rescue_reject_cross_body_passed)
        self.assertTrue(rep.sd_rescue_reject_single_operator_passed)

        t0 = time.monotonic()
        clean_rep = run_gpt_rpmb_and_rescue_bundle_suite(force_clean_room=True)
        elapsed = time.monotonic() - t0
        self.assertLess(elapsed, 0.5)
        self.assertTrue(clean_rep.all_passed)
        self.assertEqual(clean_rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        clean_rep2 = run_gpt_rpmb_and_rescue_bundle_suite(force_clean_room=True)
        self.assertEqual(clean_rep.suite_sha256, clean_rep2.suite_sha256)

    def test_34_cli_verify_gpt_rpmb_bundle_json_text_out_and_fail_rc(self) -> None:
        self._sandbox.mkdir(parents=True, exist_ok=True)
        out_dir = self._sandbox / "cli_p94_out"

        buf_json = io.StringIO()
        with (
            mock.patch.object(sys, "argv", ["fx3_recovery", "verify-gpt-rpmb-bundle", "--clean-room", "--json", "--out", str(out_dir)]),
            redirect_stdout(buf_json),
        ):
            rc = fx3_cli.main()
        self.assertEqual(rc, 0)
        rendered = buf_json.getvalue()
        self.assertNotRegex(rendered, r'(?<![0-9A-Za-z_/.-])b[\'"]')
        parsed = json.loads(rendered)
        self.assertEqual(parsed["schema"], GPT_RPMB_RESCUE_SCHEMA)
        self.assertTrue(parsed["all_passed"])
        self.assertEqual(parsed["rpmb_writes_emitted"], 0)
        self.assertTrue((out_dir / "gpt-rpmb-bundle-report.json").is_file())

        buf_text = io.StringIO()
        with mock.patch.object(sys, "argv", ["fx3_recovery", "verify-gpt-rpmb-bundle"]), redirect_stdout(buf_text):
            rc_txt = fx3_cli.main()
        self.assertEqual(rc_txt, 0)
        self.assertIn("status=VERIFIED_GPT_RPMB_RESCUE_BUNDLE", buf_text.getvalue())
        self.assertIn("gpt_partitions=15", buf_text.getvalue())

        failing = GptRpmbAndRescueSuiteReport(
            **{**self.suite_report.__dict__, "all_passed": False, "status": STATUS_FAIL_GPT_RPMB_BUNDLE}
        )
        with mock.patch("fx3_recovery.__main__.run_gpt_rpmb_and_rescue_bundle_suite", return_value=failing):
            buf_fail = io.StringIO()
            with mock.patch.object(sys, "argv", ["fx3_recovery", "verify-gpt-rpmb-bundle", "--json"]), redirect_stdout(buf_fail):
                rc_fail = fx3_cli.main()
            self.assertEqual(rc_fail, 2)

    def test_35_cli_verify_all_recovery_with_phase94_pillar8(self) -> None:
        buf = io.StringIO()
        with (
            mock.patch.object(sys, "argv", ["fx3_recovery", "verify-all-recovery", "--clean-room", "--with-phase94", "--json"]),
            redirect_stdout(buf),
        ):
            rc = fx3_cli.main()
        self.assertEqual(rc, 0)
        rendered = buf.getvalue()
        self.assertNotRegex(rendered, r'(?<![0-9A-Za-z_/.-])b[\'"]')
        parsed = json.loads(rendered)
        self.assertTrue(parsed["all_passed"])
        self.assertEqual(parsed["pillar_count"], 8)
        self.assertEqual(parsed["pillars_passed"], 8)
        self.assertIn("phase94_pillar8_gpt_rpmb_rescue", parsed)
        self.assertTrue(parsed["phase94_pillar8_gpt_rpmb_rescue"]["all_passed"])

    def test_36_json_serialization_no_raw_bytes_and_no_nan(self) -> None:
        rendered = json.dumps(self.suite_report.to_dict(), ensure_ascii=False, sort_keys=True, allow_nan=False)
        self.assertNotRegex(rendered, r'(?<![0-9A-Za-z_/.-])b[\'"]')
        decoded = json.loads(rendered)
        self.assertEqual(decoded["suite_sha256"], self.suite_report.suite_sha256)
        self.assertEqual(decoded["otp_fuse_touches"], 0)
        self.assertEqual(decoded["rpmb_writes_emitted"], 0)
        self.assertFalse(decoded["persistent_emmc_writes_authorized"])
        self.assertFalse(decoded["persistent_write_release"])


if __name__ == "__main__":
    unittest.main()
