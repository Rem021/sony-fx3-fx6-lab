"""Phase 160 (Pillar 21 / 21/21 Recovery Pillars) Dual-Mode Fast Unit Tests (48 tests, <1s):

- Group 0 (01..10): Hard-locked safety redlines, __init__ exports, O_RDONLY bounded donor inspection (BODYDATA.DAT <= 64 KiB), clean-room parity & zero raw byte leakage
- Group A (11..24): Official Sony BODYDATA.DAT (\\x89UFU Ver. 7.02) TLV header parser, FDAT 1024 B framing, cross-body rejection (ILME-FX30 / ILCE-7SM3 / ILCE-7M4 / ILME-FX6 / ILME-FX3A), dirty p15 .orig rejection & 8-scenario Pillar A suite
- Group B (25..34): CXD90057 (Mira) 15-Pin Multi/Micro-USB (Pin 7 XRESET_REQ, Pin 8 UART_TX, Pin 9 UART_RX 1.8V CMOS, Pin 10 AD_JACK_IN) EL3 (0xfe020000) Cold-Boot Guard & 6-scenario Pillar B suite
- Group C (35..43): Deterministic 5-Tier Unbrickable Hardware Recovery Escalation Ladder (Tier-1..Tier-5, dirty p15 -> Tier-2 redirect, CID-bound Tier-5 vault, write lock) & 8-scenario Pillar C suite
- Group D (44..48): Suite determinism in both modes, CLI `verify-realhw-5tier-el3-ufu` & `verify-all-recovery --with-phase160` (21/21 pillars while keeping 7/7 & 20/20 backward compatibility)
"""

from __future__ import annotations

from contextlib import redirect_stdout
from hashlib import sha256
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
ROOT = HERE.parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import fx3_recovery
from fx3_recovery import __main__ as fx3_cli
from fx3_recovery.files import resolve_donor_path
from fx3_recovery.realhw_bootrom_el3_and_ufu_stock_reflash_verifier import (
    ALLOW_BOOT_PARTITION_TARGETING,
    ALLOW_DESTRUCTIVE_FASTBOOT,
    BLOCKED_CROSS_BODY_MODEL_ID_MISMATCH,
    BLOCKED_CROSS_CAMERA_CID_VAULT_OR_WRITE_LOCKED,
    BLOCKED_DIRTY_P15_STAGEB_CLEAN_UNINSTALL_REQUIRED,
    BLOCKED_EL3_PAYLOAD_TRANSMIT_LOCKED_FALSE,
    BLOCKED_EL3_SRAM_WINDOW_OR_ALIGN_INVALID,
    BLOCKED_MULTI_USB_1V8_CMOS_OVERVOLTAGE,
    BLOCKED_MULTI_USB_PINOUT_INCOMPLETE,
    BLOCKED_OTA_BATTERY_OR_REGION_PREFLIGHT,
    BLOCKED_PERSISTENT_WRITE_AUTHORIZED_FALSE,
    BLOCKED_PIN10_AD_JACK_IN_LTC_COLLISION,
    BLOCKED_UFU_EPOCH_DOWNGRADE,
    BLOCKED_UFU_OR_FDAT_1024B_FRAMING_INVALID,
    BODYDATA_BOUNDED_HEADER_BYTES,
    BOUNDED_HEADER_MAX_BYTES,
    CROSS_BODY_MODEL_IDS,
    EL3_COLD_BOOT_MAX_PAYLOAD_BYTES,
    EL3_COLD_BOOT_SRAM_BASE,
    EL3_COLD_BOOT_SRAM_LIMIT,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    FDAT_BLOCK_BYTES,
    FDAT_TERMINAL_FLAG,
    FIVE_TIER_ORDER,
    FX3_MODEL_ID,
    FX3_MODEL_NAME,
    FX3_SOC_AP,
    FX3_SOC_CP,
    FX3_STOCK_EPOCH,
    FX3_STOCK_VERSION,
    ISP_WRITE_AUTHORIZED,
    LANC_OHM_NOMINAL,
    LOADER_NOR_SRAM_ENTRY,
    MULTI_USB_1V8_MAX_V,
    MULTI_USB_1V8_MIN_V,
    MULTI_USB_1V8_NOMINAL_V,
    MULTI_USB_REQUIRED_PINS,
    OTP_FUSE_TOUCHES,
    OTP_FUSE_WRITES,
    P160_DONOR_FX3_702_INIT_RELPATH,
    P160_DONOR_FX3_BACKUP_BIN_RELPATH,
    P160_DONOR_FX3_BODYDATA_RELPATH,
    P160_DONOR_FX3_CPAPP_B_RELPATH,
    P160_DONOR_FX3_LOADER_NOR_RELPATH,
    P160_DONOR_FX3_P1_205_RELPATH,
    P160_PILLAR_A_SCENARIO_IDS,
    P160_PILLAR_B_SCENARIO_IDS,
    P160_PILLAR_C_SCENARIO_IDS,
    P160_PINNED_FX3_702_INIT_BYTES,
    P160_PINNED_FX3_702_INIT_SHA256,
    P160_PINNED_FX3_BACKUP_BIN_BYTES,
    P160_PINNED_FX3_BACKUP_BIN_SHA256,
    P160_PINNED_FX3_BODYDATA_BYTES,
    P160_PINNED_FX3_BODYDATA_HDR4K_SHA256,
    P160_PINNED_FX3_CPAPP_B_BYTES,
    P160_PINNED_FX3_CPAPP_B_HDR4K_SHA256,
    P160_PINNED_FX3_LOADER_NOR_BYTES,
    P160_PINNED_FX3_LOADER_NOR_SHA256,
    P160_PINNED_FX3_P1_205_BYTES,
    P160_PINNED_FX3_P1_205_SHA256,
    P160_PINNED_FX3_P1_SBIN_INIT_BYTES,
    P160_PINNED_FX3_P1_SBIN_INIT_SHA256,
    P160_STATUS_VERIFIED_PILLAR_A,
    P160_STATUS_VERIFIED_PILLAR_B,
    P160_STATUS_VERIFIED_PILLAR_C,
    P160_STATUS_VERIFIED_SUITE,
    PASSIVE_TX_BYTES_EMITTED,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHASE160_SCHEMA,
    PHASE160_VERSION,
    PHYSICAL_DEVICE_WRITES,
    PHYSICAL_USB_PACKETS_EMITTED,
    RAW_FIRMWARE_BYTES_LEAKED,
    READ_ONLY_DONOR_ACCESS,
    SONY_FX3_JIRITSU_SEQUENCE,
    SONY_FX3_MSC_PID,
    SONY_FX3_SERVICE_PID,
    SONY_MIN_UPDATE_BATTERY_PCT,
    SPI_NOR_WRITE_AUTHORIZED,
    TIER_0_HEALTHY_NO_RECOVERY_NEEDED,
    TIER_1_EH1_SD_47US_BYPASS,
    TIER_2_P15_ORIG_ATOMIC_ROLLBACK,
    TIER_3_OFFICIAL_UFU_BODYDATA_STOCK_REFLASH,
    TIER_4_CXD90057_MULTI_USB_EL3_COLDBOOT_DIAG,
    TIER_5_OFFCHIP_8BIT_ISP_AND_SPI_NOR_VAULT,
    TIER_BLOCKED_UNSAFE_REQUEST,
    UFU_MAGIC,
    UFU_MAGIC_HEX,
    VMC_BNCM1_LTC_OHM_NOMINAL,
    RecoverySymptomInput,
    UfuStockReflashRequest,
    audit_cxd90057_el3_coldboot_guard,
    build_default_multi_usb_el3_spec,
    build_fdat_1024b_chunk_stream,
    build_synthetic_ufu_bodydata_header,
    evaluate_5tier_recovery_escalation,
    inspect_phase160_5tier_donors_readonly,
    parse_ufu_tlv_envelope_header,
    run_pillar_a_ufu_stock_reflash_8_scenario_suite,
    run_pillar_b_el3_coldboot_guard_6_scenario_suite,
    run_pillar_c_5tier_escalation_8_scenario_suite,
    run_realhw_bootrom_el3_and_ufu_stock_reflash_suite,
    verify_fdat_1024b_chunk_stream,
    verify_stock_ufu_reflash_preflight,
)


def _donors_present_and_not_forced_clean_room() -> bool:
    if os.environ.get("FX3_FX6_FORCE_CLEAN_ROOM") == "1":
        return False
    rels = (
        P160_DONOR_FX3_LOADER_NOR_RELPATH,
        P160_DONOR_FX3_P1_205_RELPATH,
        P160_DONOR_FX3_702_INIT_RELPATH,
        P160_DONOR_FX3_BACKUP_BIN_RELPATH,
        P160_DONOR_FX3_CPAPP_B_RELPATH,
        P160_DONOR_FX3_BODYDATA_RELPATH,
    )
    return all(resolve_donor_path(rel, require_file=True) is not None for rel in rels)


class TestPhase160RealHw5TierEl3UfuVerifier(unittest.TestCase):
    # ------------------------------------------------------------------
    # Group 0 (01..10): Hard-Locked Redlines, Exports & Bounded Donors
    # ------------------------------------------------------------------

    def test_01_hard_locked_safety_constants(self):
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        self.assertFalse(ISP_WRITE_AUTHORIZED)
        self.assertFalse(PERSISTENT_WRITE_RELEASE)
        self.assertFalse(ALLOW_BOOT_PARTITION_TARGETING)
        self.assertFalse(ALLOW_DESTRUCTIVE_FASTBOOT)
        self.assertTrue(READ_ONLY_DONOR_ACCESS)
        self.assertEqual(PHYSICAL_USB_PACKETS_EMITTED, 0)
        self.assertEqual(PHYSICAL_DEVICE_WRITES, 0)
        self.assertEqual(PASSIVE_TX_BYTES_EMITTED, 0)
        self.assertEqual(OTP_FUSE_TOUCHES, 0)
        self.assertEqual(OTP_FUSE_WRITES, 0)
        self.assertEqual(RAW_FIRMWARE_BYTES_LEAKED, 0)

    def test_02_identity_and_framing_constants(self):
        self.assertEqual(FX3_MODEL_ID, 0x91030080)
        self.assertEqual(FX3_MODEL_NAME, "ILME-FX3")
        self.assertEqual(FX3_STOCK_VERSION, "7.02")
        self.assertEqual(FX3_STOCK_EPOCH, 5)
        self.assertEqual(FX3_SOC_AP, "CXD90057")
        self.assertEqual(FX3_SOC_CP, "CXD90058")
        self.assertEqual(UFU_MAGIC, b"\x89UFU\r\n\x1a\n")
        self.assertEqual(UFU_MAGIC_HEX, "895546550d0a1a0a")
        self.assertEqual(FDAT_BLOCK_BYTES, 1024)
        self.assertEqual(FDAT_TERMINAL_FLAG, 0x8000)
        self.assertEqual(SONY_MIN_UPDATE_BATTERY_PCT, 51)
        self.assertEqual(EL3_COLD_BOOT_SRAM_BASE, 0xFE020000)
        self.assertEqual(LOADER_NOR_SRAM_ENTRY, 0xFE049000)
        self.assertEqual(len(FIVE_TIER_ORDER), 5)

    def test_03_package_init_exports_and_no_phase155_shadowing(self):
        expected_symbols = (
            "PHASE160_SCHEMA",
            "PHASE160_VERSION",
            "EL3_PAYLOAD_TRANSMIT_AUTHORIZED",
            "ISP_WRITE_AUTHORIZED",
            "PHYSICAL_USB_PACKETS_EMITTED",
            "FIVE_TIER_ORDER",
            "CROSS_BODY_MODEL_IDS",
            "parse_ufu_tlv_envelope_header",
            "build_fdat_1024b_chunk_stream",
            "verify_fdat_1024b_chunk_stream",
            "verify_stock_ufu_reflash_preflight",
            "audit_cxd90057_el3_coldboot_guard",
            "evaluate_5tier_recovery_escalation",
            "inspect_phase160_5tier_donors_readonly",
            "run_realhw_bootrom_el3_and_ufu_stock_reflash_suite",
        )
        for sym in expected_symbols:
            self.assertIn(sym, fx3_recovery.__all__)
            self.assertTrue(hasattr(fx3_recovery, sym), f"Missing export {sym}")
        # Phase 155 Pillar 20 suite function remains intact
        self.assertTrue(hasattr(fx3_recovery, "run_realhw_uart_460800_post_triage_and_isp_suite"))
        self.assertEqual(fx3_recovery.PHASE155_SCHEMA, "fx3-realhw-uart-460800-post-triage-and-isp-guard-v1")
        self.assertEqual(fx3_recovery.PHASE160_SCHEMA, PHASE160_SCHEMA)

    def test_04_clean_room_donor_snapshot_exact_mode_and_zero_leak(self):
        snap = inspect_phase160_5tier_donors_readonly(force_clean_room=True)
        self.assertTrue(snap.all_passed)
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(snap.access_mode, "SYNTHETIC_METADATA_ONLY")
        self.assertEqual(snap.donor_files_inspected, 0)
        self.assertEqual(snap.raw_firmware_bytes_leaked, 0)
        self.assertEqual(snap.bodydata_total_bytes, P160_PINNED_FX3_BODYDATA_BYTES)
        self.assertTrue(snap.bodydata_ufu_magic_ok)
        self.assertTrue(snap.bodydata_fdat_1024b_aligned)
        self.assertTrue(snap.loader_nor_el3_vbar_ok)
        self.assertTrue(snap.backup_bin_model_ok)
        self.assertEqual(len(snap.artifacts), 6)
        dumped = json.dumps(snap.to_dict(), sort_keys=True)
        self.assertIn("EL3_VBAR_0xD51EC001", dumped)
        self.assertNotIn("raw_bytes", dumped)
        self.assertLess(len(dumped), 12000)

    def test_05_env_force_clean_room_overrides_local_donors(self):
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            snap = inspect_phase160_5tier_donors_readonly()
            self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertEqual(snap.donor_files_inspected, 0)

    def test_06_local_or_clean_room_dual_mode_donor_inspection_and_bounded_read(self):
        t0 = time.monotonic()
        snap = inspect_phase160_5tier_donors_readonly()
        elapsed = time.monotonic() - t0
        self.assertLess(elapsed, 0.8)
        self.assertTrue(snap.all_passed, f"Donor errors: {snap.errors}")
        self.assertEqual(snap.raw_firmware_bytes_leaked, 0)
        self.assertEqual(len(snap.artifacts), 6)
        self.assertLessEqual(BODYDATA_BOUNDED_HEADER_BYTES, BOUNDED_HEADER_MAX_BYTES)
        self.assertEqual(BODYDATA_BOUNDED_HEADER_BYTES, 4096)

        if _donors_present_and_not_forced_clean_room():
            self.assertEqual(snap.verification_mode, "LOCAL_DONOR_RDONLY")
            self.assertEqual(snap.access_mode, "O_RDONLY_BOUNDED")
            self.assertEqual(snap.donor_files_inspected, 6)
            by_label = {a.label: a for a in snap.artifacts}
            self.assertEqual(by_label["fx3_loader_nor_bin"].byte_length, P160_PINNED_FX3_LOADER_NOR_BYTES)
            self.assertEqual(by_label["fx3_loader_nor_bin"].sha256, P160_PINNED_FX3_LOADER_NOR_SHA256)
            self.assertEqual(by_label["fx3_p1_205_nflasha1_sbin_init"].byte_length, P160_PINNED_FX3_P1_205_BYTES)
            self.assertEqual(by_label["fx3_p1_205_nflasha1_sbin_init"].sha256, P160_PINNED_FX3_P1_205_SHA256)
            self.assertEqual(by_label["fx3_p1_205_nflasha1_sbin_init"].bounded_header_sha256, P160_PINNED_FX3_P1_SBIN_INIT_SHA256)
            self.assertEqual(by_label["fx3_702_p3_sbin_init"].byte_length, P160_PINNED_FX3_702_INIT_BYTES)
            self.assertEqual(by_label["fx3_702_p3_sbin_init"].sha256, P160_PINNED_FX3_702_INIT_SHA256)
            self.assertEqual(by_label["fx3_backup_bin_bk4"].byte_length, P160_PINNED_FX3_BACKUP_BIN_BYTES)
            self.assertEqual(by_label["fx3_backup_bin_bk4"].sha256, P160_PINNED_FX3_BACKUP_BIN_SHA256)
            self.assertEqual(by_label["fx3_cpapp_b_bin"].byte_length, P160_PINNED_FX3_CPAPP_B_BYTES)
            self.assertEqual(by_label["fx3_cpapp_b_bin"].bounded_header_sha256, P160_PINNED_FX3_CPAPP_B_HDR4K_SHA256)
            self.assertEqual(by_label["fx3_702_bodydata_dat"].byte_length, P160_PINNED_FX3_BODYDATA_BYTES)
            self.assertEqual(by_label["fx3_702_bodydata_dat"].bounded_header_sha256, P160_PINNED_FX3_BODYDATA_HDR4K_SHA256)
            self.assertEqual(snap.bodydata_datv_version, 1)
            self.assertEqual(snap.bodydata_prov_value, 1)
            self.assertEqual(snap.bodydata_udid_count, 10)
            self.assertIn("UDID_054C:0DA1", by_label["fx3_702_bodydata_dat"].verified_markers)
        else:
            self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_07_local_donor_missing_falls_back_deterministically(self):
        with mock.patch("fx3_recovery.realhw_bootrom_el3_and_ufu_stock_reflash_verifier.resolve_donor_path", return_value=None):
            snap = inspect_phase160_5tier_donors_readonly(force_clean_room=False)
            self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertTrue(snap.all_passed)

    def test_08_o_rdonly_open_flags_enforced_in_report(self):
        snap = inspect_phase160_5tier_donors_readonly(force_clean_room=True)
        for art in snap.artifacts:
            self.assertEqual(art.open_flags, "SYNTHETIC_METADATA")
        if _donors_present_and_not_forced_clean_room():
            real_snap = inspect_phase160_5tier_donors_readonly(force_clean_room=False)
            for art in real_snap.artifacts:
                self.assertEqual(art.open_flags, "O_RDONLY|O_NOFOLLOW|O_NONBLOCK")

    def test_09_pinned_artifact_constants_sanity(self):
        self.assertEqual(P160_PINNED_FX3_LOADER_NOR_BYTES, 101888)
        self.assertEqual(P160_PINNED_FX3_P1_SBIN_INIT_BYTES, 1438)
        self.assertEqual(P160_PINNED_FX3_702_INIT_BYTES, 735)
        self.assertEqual(P160_PINNED_FX3_BACKUP_BIN_BYTES, 2229740)
        self.assertEqual(P160_PINNED_FX3_BODYDATA_BYTES, 811876768)

    def test_10_bodydata_fdat_1024b_real_math_alignment(self):
        # 811,876,624 = 272 (16B IV + 256B RSA-2048) + 792,848 * 1024 B blocks
        expected_fdat = 272 + 792848 * 1024
        self.assertEqual(expected_fdat, 811876624)

    # ------------------------------------------------------------------
    # Group A (11..24): BODYDATA.DAT (\x89UFU) Stock Reflash Verifier
    # ------------------------------------------------------------------

    def test_11_parse_ufu_tlv_envelope_synthetic_valid(self):
        hdr = build_synthetic_ufu_bodydata_header(fdat_payload_bytes=4096)
        res = parse_ufu_tlv_envelope_header(hdr)
        self.assertTrue(res.valid, res.errors)
        self.assertTrue(res.ufu_magic_ok)
        self.assertTrue(res.datv_present)
        self.assertEqual(res.datv_version, 1)
        self.assertTrue(res.prov_present)
        self.assertEqual(res.prov_value, 1)
        self.assertTrue(res.udid_present)
        self.assertTrue(res.msc_054c_0da1_present)
        self.assertIn("054C:0DA1", res.udid_usb_ids)
        self.assertTrue(res.fdat_present)
        self.assertTrue(res.fdat_payload_1024b_aligned)

    def test_12_parse_ufu_rejects_bad_magic_and_missing_udid(self):
        bad_magic = b"\x89PNG\r\n\x1a\n" + build_synthetic_ufu_bodydata_header()[8:]
        res_bad = parse_ufu_tlv_envelope_header(bad_magic)
        self.assertFalse(res_bad.valid)
        self.assertFalse(res_bad.ufu_magic_ok)

        no_fx3_udid = build_synthetic_ufu_bodydata_header(usb_ids=((0x054C, 0x0999, 1),))
        res_no_fx3 = parse_ufu_tlv_envelope_header(no_fx3_udid)
        self.assertFalse(res_no_fx3.valid)
        self.assertFalse(res_no_fx3.msc_054c_0da1_present)

    def test_13_parse_ufu_rejects_unaligned_fdat_and_missing_dend_tail(self):
        bad_fdat = UFU_MAGIC + struct.pack(">I4s", 4, b"DATV") + struct.pack("<I", 1)
        bad_fdat += struct.pack(">I4s", 4, b"PROV") + struct.pack("<I", 1)
        udid_body = struct.pack(">IHHI", 1, SONY_FX3_MSC_PID, 0x054C, 1)
        bad_fdat += struct.pack(">I4s", len(udid_body), b"UDID") + udid_body
        # Invalid FDAT length (272 + 17 = unaligned to 1024)
        bad_fdat += struct.pack(">I4s", 289, b"FDAT") + b"\x00" * 16
        res = parse_ufu_tlv_envelope_header(
            bad_fdat,
            total_file_bytes=4096,
            tail_bytes=b"\x00" * 12,
        )
        self.assertFalse(res.valid)
        self.assertFalse(res.fdat_payload_1024b_aligned)
        self.assertFalse(res.dend_present)

    def test_14_fdat_1024b_chunk_stream_roundtrip_and_terminal_flag(self):
        payload = b"SONY-ILME-FX3-V702-UPDATER-" * 100
        stream = build_fdat_1024b_chunk_stream(payload)
        self.assertEqual(len(stream) % FDAT_BLOCK_BYTES, 0)
        res = verify_fdat_1024b_chunk_stream(stream)
        self.assertTrue(res.valid, (res.checksum_errors, res.framing_errors))
        self.assertTrue(res.terminal_flag_seen)
        self.assertEqual(res.reconstructed_bytes, len(payload))
        self.assertEqual(res.reconstructed_sha256, sha256(payload).hexdigest())

    def test_15_fdat_1024b_rejects_checksum_corruption_and_missing_terminal(self):
        stream = bytearray(build_fdat_1024b_chunk_stream(b"FX3_PAYLOAD_DATA_" * 80))
        stream[12] ^= 0x55
        res_chk = verify_fdat_1024b_chunk_stream(bytes(stream))
        self.assertFalse(res_chk.valid)
        self.assertGreater(len(res_chk.checksum_errors), 0)

        # Strip terminal flag from single chunk
        one = bytearray(build_fdat_1024b_chunk_stream(b"SHORT_PAYLOAD"))
        chk, raw_len = struct.unpack_from("<HH", one, 0)
        struct.pack_into("<HH", one, 0, chk, raw_len & 0x7FFF)
        res_noterm = verify_fdat_1024b_chunk_stream(bytes(one))
        self.assertFalse(res_noterm.valid)
        self.assertFalse(res_noterm.terminal_flag_seen)

    def test_16_ufu_preflight_approves_valid_fx3_702_offline_only(self):
        rep = verify_stock_ufu_reflash_preflight(UfuStockReflashRequest())
        self.assertTrue(rep.passed, rep.errors)
        self.assertEqual(rep.status, P160_STATUS_VERIFIED_PILLAR_A)
        self.assertTrue(rep.model_match_fx3_0x91030080)
        self.assertTrue(rep.ufu_envelope_ok)
        self.assertTrue(rep.fdat_1024b_framing_ok)
        self.assertTrue(rep.p15_clean_uninstall_verified)
        self.assertTrue(rep.preflight_approved_offline_only)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertEqual(rep.physical_usb_packets_emitted, 0)
        self.assertEqual(rep.physical_device_writes, 0)

    def test_17_ufu_preflight_hard_rejects_all_cross_body_models(self):
        for model_name, model_id in CROSS_BODY_MODEL_IDS.items():
            with self.subTest(model=model_name):
                rep = verify_stock_ufu_reflash_preflight(
                    UfuStockReflashRequest(target_model_name=model_name, target_model_id=model_id)
                )
                self.assertFalse(rep.passed)
                self.assertFalse(rep.model_match_fx3_0x91030080)
                self.assertIn(BLOCKED_CROSS_BODY_MODEL_ID_MISMATCH, rep.blocked_codes)
        # Also reject matching name with wrong model_id
        rep_id_mismatch = verify_stock_ufu_reflash_preflight(
            UfuStockReflashRequest(target_model_name=FX3_MODEL_NAME, target_model_id=0x910300A0)
        )
        self.assertFalse(rep_id_mismatch.passed)
        self.assertIn(BLOCKED_CROSS_BODY_MODEL_ID_MISMATCH, rep_id_mismatch.blocked_codes)

    def test_18_ufu_preflight_mandates_p15_orig_clean_uninstall(self):
        # Dirty: overlay installed & not uninstalled
        rep_dirty = verify_stock_ufu_reflash_preflight(
            UfuStockReflashRequest(
                p15_stageb_overlay_installed=True,
                p15_orig_uninstalled=False,
                p15_orig_16of16_sha256_h0_eq_h3=False,
            )
        )
        self.assertFalse(rep_dirty.passed)
        self.assertFalse(rep_dirty.p15_clean_uninstall_verified)
        self.assertIn(BLOCKED_DIRTY_P15_STAGEB_CLEAN_UNINSTALL_REQUIRED, rep_dirty.blocked_codes)

        # Clean: overlay was installed, then 16/16 H0==H3 clean uninstaller succeeded
        rep_cleaned = verify_stock_ufu_reflash_preflight(
            UfuStockReflashRequest(
                p15_stageb_overlay_installed=True,
                p15_orig_uninstalled=True,
                p15_orig_16of16_sha256_h0_eq_h3=True,
            )
        )
        self.assertTrue(rep_cleaned.passed, rep_cleaned.errors)
        self.assertTrue(rep_cleaned.p15_clean_uninstall_verified)

    def test_19_ufu_preflight_blocks_low_battery_and_region_mismatch(self):
        rep_bat = verify_stock_ufu_reflash_preflight(UfuStockReflashRequest(battery_pct=50))
        self.assertFalse(rep_bat.passed)
        self.assertIn(BLOCKED_OTA_BATTERY_OR_REGION_PREFLIGHT, rep_bat.blocked_codes)

        rep_reg = verify_stock_ufu_reflash_preflight(
            UfuStockReflashRequest(package_region="PAL", camera_region="NTSC")
        )
        self.assertFalse(rep_reg.passed)
        self.assertIn(BLOCKED_OTA_BATTERY_OR_REGION_PREFLIGHT, rep_reg.blocked_codes)

    def test_20_ufu_preflight_blocks_version_downgrade(self):
        rep = verify_stock_ufu_reflash_preflight(
            UfuStockReflashRequest(package_version="6.01", camera_current_version="7.02")
        )
        self.assertFalse(rep.passed)
        self.assertIn(BLOCKED_UFU_EPOCH_DOWNGRADE, rep.blocked_codes)

    def test_21_ufu_preflight_blocks_sha256_unverified(self):
        rep = verify_stock_ufu_reflash_preflight(UfuStockReflashRequest(sha256_verified=False))
        self.assertFalse(rep.passed)
        self.assertIn(BLOCKED_OTA_BATTERY_OR_REGION_PREFLIGHT, rep.blocked_codes)

    def test_22_ufu_preflight_blocks_persistent_emmc_write_request(self):
        rep = verify_stock_ufu_reflash_preflight(
            UfuStockReflashRequest(request_persistent_emmc_writes=True)
        )
        self.assertFalse(rep.passed)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertIn(BLOCKED_PERSISTENT_WRITE_AUTHORIZED_FALSE, rep.blocked_codes)

    def test_23_fdat_1024b_rejects_unaligned_and_trailing_chunks(self):
        res_unaligned = verify_fdat_1024b_chunk_stream(b"\x00" * 512)
        self.assertFalse(res_unaligned.valid)

        s1 = build_fdat_1024b_chunk_stream(b"FIRST")
        s2 = build_fdat_1024b_chunk_stream(b"SECOND")
        res_trailing = verify_fdat_1024b_chunk_stream(s1 + s2)
        self.assertFalse(res_trailing.valid)

    def test_24_pillar_a_8_scenario_suite_passes_all_8(self):
        res = run_pillar_a_ufu_stock_reflash_8_scenario_suite()
        self.assertTrue(res.passed)
        self.assertEqual(res.status, P160_STATUS_VERIFIED_PILLAR_A)
        self.assertEqual(res.scenarios_passed, 8)
        self.assertEqual(res.scenarios_total, 8)
        self.assertFalse(res.persistent_emmc_writes_authorized)
        self.assertEqual(res.physical_usb_packets_emitted, 0)
        self.assertEqual(tuple(o.scenario_id for o in res.scenarios), P160_PILLAR_A_SCENARIO_IDS)

    # ------------------------------------------------------------------
    # Group B (25..34): CXD90057 (Mira) Multi-USB 1.8V UART EL3 Guard
    # ------------------------------------------------------------------

    def test_25_el3_coldboot_readonly_audit_passes_and_locks_transmit_false(self):
        spec = build_default_multi_usb_el3_spec()
        rep = audit_cxd90057_el3_coldboot_guard(spec)
        self.assertTrue(rep.passed, rep.errors)
        self.assertEqual(rep.status, P160_STATUS_VERIFIED_PILLAR_B)
        self.assertEqual(rep.el3_load_addr_hex, "0xfe020000")
        self.assertTrue(rep.el3_sram_window_ok)
        self.assertTrue(rep.multi_usb_pinout_ok)
        self.assertTrue(rep.io_1v8_cmos_ok)
        self.assertTrue(rep.ad_jack_in_ltc_isolated)
        self.assertFalse(rep.el3_payload_transmit_authorized)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.spi_nor_write_authorized)
        self.assertEqual(rep.physical_usb_packets_emitted, 0)

    def test_26_el3_coldboot_hard_blocks_payload_transmit_and_tx_bytes(self):
        rep1 = audit_cxd90057_el3_coldboot_guard(
            build_default_multi_usb_el3_spec(authorize_el3_payload_transmit=True)
        )
        self.assertFalse(rep1.passed)
        self.assertFalse(rep1.el3_payload_transmit_authorized)
        self.assertIn(BLOCKED_EL3_PAYLOAD_TRANSMIT_LOCKED_FALSE, rep1.blocked_codes)

        rep2 = audit_cxd90057_el3_coldboot_guard(
            build_default_multi_usb_el3_spec(tx_bytes_requested=128)
        )
        self.assertFalse(rep2.passed)
        self.assertIn(BLOCKED_EL3_PAYLOAD_TRANSMIT_LOCKED_FALSE, rep2.blocked_codes)

        rep3 = audit_cxd90057_el3_coldboot_guard(
            build_default_multi_usb_el3_spec(diagnostic_only_before_offchip_solder=False)
        )
        self.assertFalse(rep3.passed)
        self.assertIn(BLOCKED_EL3_PAYLOAD_TRANSMIT_LOCKED_FALSE, rep3.blocked_codes)

    def test_27_multi_usb_1v8_cmos_voltage_boundaries_and_overvoltage_block(self):
        self.assertTrue(
            audit_cxd90057_el3_coldboot_guard(
                build_default_multi_usb_el3_spec(io_voltage_v=MULTI_USB_1V8_MIN_V)
            ).passed
        )
        self.assertTrue(
            audit_cxd90057_el3_coldboot_guard(
                build_default_multi_usb_el3_spec(io_voltage_v=MULTI_USB_1V8_MAX_V)
            ).passed
        )
        for bad_v in (1.20, 3.30, 5.00):
            rep = audit_cxd90057_el3_coldboot_guard(
                build_default_multi_usb_el3_spec(io_voltage_v=bad_v)
            )
            self.assertFalse(rep.passed)
            self.assertFalse(rep.io_1v8_cmos_ok)
            self.assertIn(BLOCKED_MULTI_USB_1V8_CMOS_OVERVOLTAGE, rep.blocked_codes)

    def test_28_pin10_ad_jack_in_blocks_vmc_bncm1_680k_and_lanc_100k(self):
        rep_ltc = audit_cxd90057_el3_coldboot_guard(
            build_default_multi_usb_el3_spec(ad_jack_in_ohm=VMC_BNCM1_LTC_OHM_NOMINAL)
        )
        self.assertFalse(rep_ltc.passed)
        self.assertFalse(rep_ltc.ad_jack_in_ltc_isolated)
        self.assertIn(BLOCKED_PIN10_AD_JACK_IN_LTC_COLLISION, rep_ltc.blocked_codes)

        rep_lanc = audit_cxd90057_el3_coldboot_guard(
            build_default_multi_usb_el3_spec(ad_jack_in_ohm=LANC_OHM_NOMINAL, lanc_attached=True)
        )
        self.assertFalse(rep_lanc.passed)
        self.assertIn(BLOCKED_PIN10_AD_JACK_IN_LTC_COLLISION, rep_lanc.blocked_codes)

    def test_29_multi_usb_15pin_pinout_rejects_missing_pin7_8_9_10(self):
        for pin_num in MULTI_USB_REQUIRED_PINS:
            broken = dict(MULTI_USB_REQUIRED_PINS)
            broken.pop(pin_num)
            rep = audit_cxd90057_el3_coldboot_guard(build_default_multi_usb_el3_spec(pin_map=broken))
            self.assertFalse(rep.passed)
            self.assertFalse(rep.multi_usb_pinout_ok)
            self.assertIn(BLOCKED_MULTI_USB_PINOUT_INCOMPLETE, rep.blocked_codes)

    def test_30_el3_sram_window_rejects_bad_addr_or_oversize(self):
        rep_addr = audit_cxd90057_el3_coldboot_guard(
            build_default_multi_usb_el3_spec(el3_load_addr=0x40000000)
        )
        self.assertFalse(rep_addr.passed)
        self.assertIn(BLOCKED_EL3_SRAM_WINDOW_OR_ALIGN_INVALID, rep_addr.blocked_codes)

        rep_size = audit_cxd90057_el3_coldboot_guard(
            build_default_multi_usb_el3_spec(el3_payload_bytes=EL3_COLD_BOOT_MAX_PAYLOAD_BYTES + 4096)
        )
        self.assertFalse(rep_size.passed)
        self.assertIn(BLOCKED_EL3_SRAM_WINDOW_OR_ALIGN_INVALID, rep_size.blocked_codes)

        rep_limit = audit_cxd90057_el3_coldboot_guard(
            build_default_multi_usb_el3_spec(
                el3_load_addr=EL3_COLD_BOOT_SRAM_LIMIT - 1024,
                el3_payload_bytes=4096,
            )
        )
        self.assertFalse(rep_limit.passed)

    def test_31_el3_coldboot_blocks_persistent_emmc_and_spinor_write_requests(self):
        rep = audit_cxd90057_el3_coldboot_guard(
            build_default_multi_usb_el3_spec(request_persistent_emmc_writes=True, request_spi_nor_write=True)
        )
        self.assertFalse(rep.passed)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.spi_nor_write_authorized)
        self.assertIn(BLOCKED_PERSISTENT_WRITE_AUTHORIZED_FALSE, rep.blocked_codes)

    def test_32_multi_usb_pinout_exact_mapping_check(self):
        self.assertEqual(MULTI_USB_REQUIRED_PINS[7], "XRESET_REQ")
        self.assertEqual(MULTI_USB_REQUIRED_PINS[8], "UART_TX")
        self.assertEqual(MULTI_USB_REQUIRED_PINS[9], "UART_RX")
        self.assertEqual(MULTI_USB_REQUIRED_PINS[10], "AD_JACK_IN")

    def test_33_el3_coldboot_unaligned_payload_boundary(self):
        rep_zero = audit_cxd90057_el3_coldboot_guard(
            build_default_multi_usb_el3_spec(el3_payload_bytes=0)
        )
        self.assertFalse(rep_zero.passed)
        self.assertIn(BLOCKED_EL3_SRAM_WINDOW_OR_ALIGN_INVALID, rep_zero.blocked_codes)

    def test_34_pillar_b_6_scenario_suite_passes_all_6(self):
        res = run_pillar_b_el3_coldboot_guard_6_scenario_suite()
        self.assertTrue(res.passed)
        self.assertEqual(res.status, P160_STATUS_VERIFIED_PILLAR_B)
        self.assertEqual(res.scenarios_passed, 6)
        self.assertEqual(res.scenarios_total, 6)
        for o in res.scenarios:
            self.assertFalse(o.el3_payload_transmit_authorized)
        self.assertEqual(tuple(o.scenario_id for o in res.scenarios), P160_PILLAR_B_SCENARIO_IDS)

    # ------------------------------------------------------------------
    # Group C (35..43): Deterministic 5-Tier Unbrickable Recovery Ladder
    # ------------------------------------------------------------------

    def test_35_tier1_sd_removal_eh1_47us_bypass_zero_writes(self):
        dec = evaluate_5tier_recovery_escalation(
            RecoverySymptomInput(
                scenario_id="t1",
                stage_reached="STAGE_4_IM_ELF_SD_ESCAPE_WRAPPER",
                sd_stageb_active=True,
                p15_overlay_installed=False,
            )
        )
        self.assertTrue(dec.passed)
        self.assertEqual(dec.selected_tier, TIER_1_EH1_SD_47US_BYPASS)
        self.assertEqual(dec.tier_rank, 1)
        self.assertIn("47 us", dec.action_summary)
        self.assertFalse(dec.persistent_emmc_writes_authorized)
        self.assertEqual(dec.physical_device_writes, 0)

    def test_36_tier2_p15_orig_rollback_via_eh2_16of16_jiritsu(self):
        dec = evaluate_5tier_recovery_escalation(
            RecoverySymptomInput(
                scenario_id="t2",
                stage_reached="STAGE_5_STAGEB_APPFW_BIG6_READY",
                p15_overlay_installed=True,
                eh2_16of16_h0_eq_h3_ready=True,
                jiritsu_0da1_to_0336_available=True,
            )
        )
        self.assertTrue(dec.passed)
        self.assertEqual(dec.selected_tier, TIER_2_P15_ORIG_ATOMIC_ROLLBACK)
        self.assertEqual(dec.tier_rank, 2)
        self.assertIn(SONY_FX3_JIRITSU_SEQUENCE, dec.action_summary)
        self.assertIn("16/16", dec.action_summary)

    def test_37_tier3_redirects_dirty_p15_to_tier2_before_bodydata_reflash(self):
        dec = evaluate_5tier_recovery_escalation(
            RecoverySymptomInput(
                scenario_id="t3_dirty_redirect",
                stage_reached="STAGE_5_STAGEB_APPFW_BIG6_READY",
                p15_overlay_installed=True,
                eh2_16of16_h0_eq_h3_ready=True,
                jiritsu_0da1_to_0336_available=True,
                ufu_reflash_request=UfuStockReflashRequest(
                    p15_stageb_overlay_installed=True,
                    p15_orig_uninstalled=False,
                    p15_orig_16of16_sha256_h0_eq_h3=False,
                ),
            )
        )
        self.assertTrue(dec.passed)
        self.assertEqual(dec.selected_tier, TIER_2_P15_ORIG_ATOMIC_ROLLBACK)
        self.assertTrue(dec.requires_clean_p15_uninstall_first)

    def test_38_tier3_valid_fx3_702_ufu_reflash_clean_p15(self):
        dec = evaluate_5tier_recovery_escalation(
            RecoverySymptomInput(
                scenario_id="t3_valid",
                stage_reached="STAGE_3_SPACC_CNFLASHA15_EXT2_USR",
                p15_overlay_installed=False,
                ufu_reflash_request=UfuStockReflashRequest(),
            )
        )
        self.assertTrue(dec.passed)
        self.assertEqual(dec.selected_tier, TIER_3_OFFICIAL_UFU_BODYDATA_STOCK_REFLASH)
        self.assertEqual(dec.tier_rank, 3)
        self.assertFalse(dec.requires_clean_p15_uninstall_first)

    def test_39_tier4_bootrom_el3_coldboot_readonly_audit(self):
        dec = evaluate_5tier_recovery_escalation(
            RecoverySymptomInput(
                scenario_id="t4_el3",
                stage_reached="STAGE_0_BOOTROM_SPI_NOR_IPL",
                bootrom_cold_hang_or_bloader_corrupt=True,
                el3_coldboot_spec=build_default_multi_usb_el3_spec(),
            )
        )
        self.assertTrue(dec.passed)
        self.assertEqual(dec.selected_tier, TIER_4_CXD90057_MULTI_USB_EL3_COLDBOOT_DIAG)
        self.assertEqual(dec.tier_rank, 4)
        self.assertFalse(dec.el3_payload_transmit_authorized)

    def test_40_tier5_cid_bound_offchip_isp_and_spinor_vault_audit(self):
        cid = sha256(b"fx3-unit-cid-ok").hexdigest()
        dec = evaluate_5tier_recovery_escalation(
            RecoverySymptomInput(
                scenario_id="t5_ok",
                stage_reached="STAGE_0_BOOTROM_SPI_NOR_IPL",
                emmc_and_spinor_offchip_isp_needed=True,
                isp_cid_sha256=cid,
                vault_cid_sha256=cid,
                pnflasha_and_mtd0ro_verified=True,
            )
        )
        self.assertTrue(dec.passed)
        self.assertEqual(dec.selected_tier, TIER_5_OFFCHIP_8BIT_ISP_AND_SPI_NOR_VAULT)
        self.assertEqual(dec.tier_rank, 5)
        self.assertFalse(dec.isp_write_authorized)
        self.assertFalse(dec.spi_nor_write_authorized)

    def test_41_tier5_blocks_cross_camera_cid_and_write_unlock_requests(self):
        cid_a = sha256(b"fx3-unit-A").hexdigest()
        cid_b = sha256(b"fx3-unit-B").hexdigest()
        dec = evaluate_5tier_recovery_escalation(
            RecoverySymptomInput(
                scenario_id="t5_bad",
                stage_reached="STAGE_0_BOOTROM_SPI_NOR_IPL",
                emmc_and_spinor_offchip_isp_needed=True,
                isp_cid_sha256=cid_a,
                vault_cid_sha256=cid_b,
                pnflasha_and_mtd0ro_verified=True,
                request_isp_write_unlock=True,
                request_spi_nor_write=True,
                request_persistent_emmc_writes=True,
            )
        )
        self.assertFalse(dec.passed)
        self.assertEqual(dec.selected_tier, TIER_BLOCKED_UNSAFE_REQUEST)
        self.assertFalse(dec.isp_write_authorized)
        self.assertFalse(dec.spi_nor_write_authorized)
        self.assertFalse(dec.persistent_emmc_writes_authorized)
        self.assertIn(BLOCKED_CROSS_CAMERA_CID_VAULT_OR_WRITE_LOCKED, dec.blocked_codes)
        self.assertIn(BLOCKED_PERSISTENT_WRITE_AUTHORIZED_FALSE, dec.blocked_codes)

    def test_42_healthy_baseline_returns_tier0_no_recovery_needed(self):
        dec = evaluate_5tier_recovery_escalation(
            RecoverySymptomInput(scenario_id="healthy", stage_reached="STAGE_5_STAGEB_APPFW_BIG6_READY")
        )
        self.assertTrue(dec.passed)
        self.assertEqual(dec.selected_tier, TIER_0_HEALTHY_NO_RECOVERY_NEEDED)
        self.assertEqual(dec.tier_rank, 0)

    def test_43_pillar_c_8_scenario_suite_passes_all_8(self):
        res = run_pillar_c_5tier_escalation_8_scenario_suite()
        self.assertTrue(res.passed)
        self.assertEqual(res.status, P160_STATUS_VERIFIED_PILLAR_C)
        self.assertEqual(res.scenarios_passed, 8)
        self.assertEqual(res.scenarios_total, 8)
        self.assertEqual(tuple(o.scenario_id for o in res.scenarios), P160_PILLAR_C_SCENARIO_IDS)

    # ------------------------------------------------------------------
    # Group D (44..48): Suite Determinism, CLI & 21/21 Recovery Integration
    # ------------------------------------------------------------------

    def test_44_unified_suite_deterministic_and_hard_locked(self):
        r1 = run_realhw_bootrom_el3_and_ufu_stock_reflash_suite(force_clean_room=True)
        r2 = run_realhw_bootrom_el3_and_ufu_stock_reflash_suite(force_clean_room=True)
        self.assertTrue(r1.all_passed)
        self.assertEqual(r1.status, P160_STATUS_VERIFIED_SUITE)
        self.assertEqual(r1.schema, PHASE160_SCHEMA)
        self.assertEqual(r1.version, PHASE160_VERSION)
        self.assertEqual(r1.suite_sha256, r2.suite_sha256)
        self.assertFalse(r1.persistent_emmc_writes_authorized)
        self.assertFalse(r1.spi_nor_write_authorized)
        self.assertFalse(r1.el3_payload_transmit_authorized)
        self.assertFalse(r1.isp_write_authorized)
        self.assertFalse(r1.persistent_write_release)
        self.assertEqual(r1.physical_usb_packets_emitted, 0)
        self.assertEqual(r1.physical_device_writes, 0)
        self.assertEqual(r1.raw_firmware_bytes_leaked, 0)

    def test_45_cli_verify_realhw_5tier_el3_ufu_json_and_out_dir(self):
        out_dir = ROOT / "work" / "_tests" / "test_p160_cli_out"
        if out_dir.exists():
            shutil.rmtree(out_dir)
        out_dir.parent.mkdir(parents=True, exist_ok=True)
        try:
            buf = io.StringIO()
            argv = [
                "fx3_recovery",
                "verify-realhw-5tier-el3-ufu",
                "--clean-room",
                "--json",
                "--out",
                str(out_dir),
            ]
            with mock.patch.object(sys, "argv", argv), redirect_stdout(buf):
                rc = fx3_cli.main()
            self.assertEqual(rc, 0)
            parsed = json.loads(buf.getvalue())
            self.assertTrue(parsed["all_passed"])
            self.assertEqual(parsed["status"], P160_STATUS_VERIFIED_SUITE)
            self.assertFalse(parsed["el3_payload_transmit_authorized"])
            self.assertFalse(parsed["isp_write_authorized"])
            self.assertFalse(parsed["spi_nor_write_authorized"])
            self.assertFalse(parsed["persistent_emmc_writes_authorized"])
            self.assertEqual(parsed["physical_usb_packets_emitted"], 0)
            self.assertTrue((out_dir / "realhw-5tier-el3-ufu-report.json").is_file())
        finally:
            if out_dir.exists():
                shutil.rmtree(out_dir)

    def test_46_cli_verify_realhw_5tier_el3_ufu_text_and_nonzero_on_failure(self):
        buf = io.StringIO()
        argv = ["fx3_recovery", "verify-realhw-5tier-el3-ufu", "--clean-room"]
        with mock.patch.object(sys, "argv", argv), redirect_stdout(buf):
            rc = fx3_cli.main()
        self.assertEqual(rc, 0)
        line = buf.getvalue().strip()
        self.assertIn("status=VERIFIED_REALHW_5TIER_EL3_UFU_21PILLAR_GATE", line)
        self.assertIn("pillar_a_ufu=8/8", line)
        self.assertIn("pillar_b_el3=6/6", line)
        self.assertIn("pillar_c_5tier=8/8", line)
        self.assertIn("el3_payload_transmit_authorized=False", line)
        self.assertIn("isp_write_authorized=False", line)

        # Force failure via mocked suite return
        bad_report = mock.Mock()
        bad_report.all_passed = False
        bad_report.status = "FAIL_REALHW_5TIER_EL3_UFU_21PILLAR_GATE"
        bad_report.verification_mode = "CLEAN_ROOM_SYNTHETIC"
        bad_report.suite_sha256 = "0" * 64
        bad_report.el3_payload_transmit_authorized = False
        bad_report.isp_write_authorized = False
        bad_report.spi_nor_write_authorized = False
        bad_report.persistent_emmc_writes_authorized = False
        bad_report.physical_usb_packets_emitted = 0
        bad_report.physical_device_writes = 0
        bad_report.pillar_a_ufu_8_scenarios = mock.Mock(scenarios_passed=0, scenarios_total=8)
        bad_report.pillar_b_el3_6_scenarios = mock.Mock(scenarios_passed=0, scenarios_total=6)
        bad_report.pillar_c_5tier_8_scenarios = mock.Mock(scenarios_passed=0, scenarios_total=8)
        bad_report.to_dict.return_value = {"all_passed": False, "status": bad_report.status}
        buf_fail = io.StringIO()
        with (
            mock.patch(
                "fx3_recovery.__main__.run_realhw_bootrom_el3_and_ufu_stock_reflash_suite",
                return_value=bad_report,
            ),
            mock.patch.object(sys, "argv", ["fx3_recovery", "verify-realhw-5tier-el3-ufu", "--json"]),
            redirect_stdout(buf_fail),
        ):
            rc_fail = fx3_cli.main()
        self.assertEqual(rc_fail, 2)

    def test_47_verify_all_recovery_reaches_21_of_21_and_keeps_backward_compat(self):
        # Default (no --with-phase* flags): preserves 7/7
        buf_7 = io.StringIO()
        with (
            mock.patch.object(sys, "argv", ["fx3_recovery", "verify-all-recovery", "--clean-room", "--json"]),
            redirect_stdout(buf_7),
        ):
            rc_7 = fx3_cli.main()
        self.assertEqual(rc_7, 0)
        d7 = json.loads(buf_7.getvalue())
        self.assertEqual(d7["pillar_count"], 7)
        self.assertEqual(d7["pillars_passed"], 7)

        # Opt-in all 21 pillars: reaches 21/21
        buf_21 = io.StringIO()
        argv_21 = [
            "fx3_recovery",
            "verify-all-recovery",
            "--clean-room",
            "--json",
            "--with-phase94",
            "--with-phase101",
            "--with-phase106",
            "--with-phase113",
            "--with-phase119",
            "--with-phase124",
            "--with-phase126",
            "--with-phase134",
            "--with-phase138",
            "--with-phase139",
            "--with-phase144",
            "--with-phase151",
            "--with-phase155",
            "--with-phase160",
        ]
        with mock.patch.object(sys, "argv", argv_21), redirect_stdout(buf_21):
            rc_21 = fx3_cli.main()
        self.assertEqual(rc_21, 0)
        d21 = json.loads(buf_21.getvalue())
        self.assertTrue(d21["all_passed"])
        self.assertEqual(d21["pillar_count"], 21)
        self.assertEqual(d21["pillars_passed"], 21)
        self.assertIn("phase160_pillar21_5tier_el3_ufu_recovery", d21)
        p21 = d21["phase160_pillar21_5tier_el3_ufu_recovery"]
        self.assertTrue(p21["all_passed"])
        self.assertFalse(p21["el3_payload_transmit_authorized"])
        self.assertFalse(p21["isp_write_authorized"])
        self.assertFalse(p21["spi_nor_write_authorized"])
        self.assertFalse(p21["persistent_emmc_writes_authorized"])

    def test_48_verify_all_recovery_text_prints_21_of_21_pillars(self):
        buf = io.StringIO()
        argv_21 = [
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
            "--with-phase139",
            "--with-phase144",
            "--with-phase151",
            "--with-phase155",
            "--with-phase160",
        ]
        with mock.patch.object(sys, "argv", argv_21), redirect_stdout(buf):
            rc = fx3_cli.main()
        self.assertEqual(rc, 0)
        self.assertIn("pillars=21/21", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
