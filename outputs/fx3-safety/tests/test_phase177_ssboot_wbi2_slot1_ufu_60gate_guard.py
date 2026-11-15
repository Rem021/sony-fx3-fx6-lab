"""Fast dual-mode unit tests for Phase 177 — Real-Hardware Main Track Part 17:
Gate G59 (`ssboot` / `WBI2` `prsv-img` Bootloader-Bypass Guard + `liro.ko` /
`BLKROSET=1` / `/proc/udm` Stage-B Write-Block + `H0 == H3` Clean Uninstall),
Gate G60 (`FX3 7.02 >= 2.04` UFU Floor + Slot-1 Root & Duplicate Filename
Guard + C2PA 100-License Ceiling / `p12:/cert/RQ_LIC.DAT` `BLKROSET=1` +
`Ver. 7.00+` Wireless Security Floor), and
60-Gate Milestone Master Preflight (`G01..G60` / `verify-60-gates`).
"""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import fx3_safety
from fx3_safety.__main__ import main as package_cli_main
from fx3_safety.master_16gate_preflight import DEFAULT_REPO_ROOT
from fx3_safety.realhw_dualmedia_bench_interlock_and_58gate_guard import (
    STATUS_BLOCKED_G58_AUTO_FLASH_INTERLOCK_VIOLATION,
    evaluate_58gate_preflight,
)
from fx3_safety.realhw_ssboot_wbi2_slot1_ufu_and_60gate_guard import (
    ALLOWED_WIRELESS_PROTOCOLS,
    BODYDATA_702_EXACT_BYTES,
    BODYDATA_FILENAME,
    BODYDATA_UFU_MAGIC_HEX,
    C2PA_MAX_LICENSES_CEILING,
    DEFAULT_SYNTHETIC_NFLASHA5_FULL_SHA256,
    DEFAULT_SYNTHETIC_WBI2_SECTOR0_SHA256,
    DEPRECATED_WIRELESS_PROTOCOLS,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    FX3_BRICK_LED_BELOW_FLOOR,
    FX3_MIN_BODY_FIRMWARE_FLOOR,
    FX3_MODEL_ID_HEX,
    FX3_MODEL_ID_INT,
    FX3_MODEL_NAME,
    FX3_UFU_TARGET_VERSION,
    FX3RCPT1_MAGIC,
    FX3RCPT1_PACKET_BYTES,
    G59_GATE_CODE,
    G59_GATE_ID,
    G60_GATE_CODE,
    G60_GATE_ID,
    GATE_G59_SSBOOT_WBI2_PRSVIMG_AND_LIRO_BYPASS_GUARD,
    GATE_G60_FX3_702_UFU_VERSION_FLOOR_AND_SLOT1_C2PA_GUARD,
    P12_DEVICE_NODE,
    P12_REQUIRED_MOUNT_FLAG,
    P12_RQ_LIC_PATH,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED,
    PHYSICAL_USB_PACKETS_EMITTED,
    PINNED_BODYDATA_HEADER_RELPATH,
    PINNED_PHASE177_DONOR_SPECS,
    RAW_FIRMWARE_BYTES_LEAKED,
    REALHW_SSBOOT_WBI2_SLOT1_UFU_60GATE_SCHEMA,
    REALHW_SSBOOT_WBI2_SLOT1_UFU_60GATE_VERSION,
    REQUIRED_SLOT1_BODYDATA_PATH,
    REQUIRED_UPDATE_SLOT,
    SPI_NOR_WRITE_AUTHORIZED,
    STATUS_BLOCKED_G59_SSBOOT_RESUME_INIT_BYPASS_TRAP,
    STATUS_BLOCKED_G59_TELEMETRY_INVALID,
    STATUS_BLOCKED_G59_WBI2_CLEAN_UNINSTALL_H0_H3_MISMATCH,
    STATUS_BLOCKED_G59_WBI2_STAGEB_WRITE_OR_BLKROSET_UNPROTECTED,
    STATUS_BLOCKED_G59_WBI2_TIER0_RECEIPT_MISSING,
    STATUS_BLOCKED_G60_BODY_VERSION_BELOW_204_FLOOR,
    STATUS_BLOCKED_G60_C2PA_100_LICENSE_CEILING_OR_P12_RO,
    STATUS_BLOCKED_G60_INSECURE_WIRELESS_WEP_WPA1_IPSEC,
    STATUS_BLOCKED_G60_SLOT1_ROOT_OR_DUPLICATE_BODYDATA,
    STATUS_BLOCKED_G60_TELEMETRY_INVALID,
    STATUS_BLOCKED_PERSISTENT_EMMC_WRITE,
    STATUS_BLOCKED_PHASE177_DONOR_INTEGRITY,
    STATUS_SAFE,
    STATUS_VERIFIED_G59,
    STATUS_VERIFIED_G60,
    STATUS_VERIFIED_SAFE,
    WBI2_MAGIC_BYTES,
    WBI2_MAGIC_HEX,
    WBI_COMPRESSION_CODEC,
    WBI_MOUNT_POINT,
    WBI_PARTITION_APPROX_MIB,
    WBI_PARTITION_DEV,
    WBI_RAW_PARTITION_DEV,
    WBI_SECTOR0_BYTES,
    WBI_SNAPSHOT_IMAGE_NAME,
    audit_phase177_donor_contracts,
    build_synthetic_wbi2_sector0,
    evaluate_60_master_safety_gates,
    evaluate_60gate_preflight,
    evaluate_g59_ssboot_wbi2_guard,
    evaluate_g60_slot1_ufu_c2pa_guard,
    main as module_cli_main,
    parse_firmware_version_tuple,
    verify_fx3_702_ufu_floor_and_slot1_c2pa_guard,
    verify_ssboot_wbi2_prsvimg_and_liro_guard,
)
from fx3_safety.rig_groundloop_lensrail_and_20gate_guard import (
    STATUS_FAIL_OFFLINE_HARDWARE_NOT_ATTACHED,
)


class RealHwSsbootWbi2Slot1Ufu60GateTests(unittest.TestCase):
    # --- 1. Hard-Locked Redlines, Exports & O_RDONLY Donor Audit ---

    def test_01_hard_locked_redlines_and_package_exports(self) -> None:
        self.assertFalse(EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        self.assertFalse(SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(PERSISTENT_WRITE_RELEASE)
        self.assertFalse(PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED)
        self.assertEqual(PHYSICAL_USB_PACKETS_EMITTED, 0)
        self.assertEqual(RAW_FIRMWARE_BYTES_LEAKED, 0)
        self.assertEqual(
            REALHW_SSBOOT_WBI2_SLOT1_UFU_60GATE_SCHEMA,
            "fx3-realhw-ssboot-wbi2-slot1-ufu-60gate-preflight-v1",
        )
        self.assertEqual(REALHW_SSBOOT_WBI2_SLOT1_UFU_60GATE_VERSION, "1.0.0")
        self.assertEqual(WBI_PARTITION_DEV, "/dev/nflasha5")
        self.assertEqual(WBI_RAW_PARTITION_DEV, "/dev/pnflasha5")
        self.assertEqual(WBI_MOUNT_POINT, "/wbi")
        self.assertEqual(WBI_PARTITION_APPROX_MIB, 232.5)
        self.assertEqual(WBI_SECTOR0_BYTES, 512)
        self.assertEqual(WBI2_MAGIC_BYTES, b"WBI2\x00\x00\x00\x00")
        self.assertEqual(WBI2_MAGIC_HEX, "5742493200000000")
        self.assertEqual(WBI_COMPRESSION_CODEC, "LZO")
        self.assertEqual(WBI_SNAPSHOT_IMAGE_NAME, "prsv-img")
        self.assertEqual(FX3_MODEL_ID_INT, 0x91030080)
        self.assertEqual(FX3_MODEL_ID_HEX, "0x91030080")
        self.assertEqual(FX3_MODEL_NAME, "ILME-FX3")
        self.assertEqual(FX3_MIN_BODY_FIRMWARE_FLOOR, "2.04")
        self.assertEqual(FX3_UFU_TARGET_VERSION, "7.02")
        self.assertEqual(FX3_BRICK_LED_BELOW_FLOOR, "7L+7S")
        self.assertEqual(BODYDATA_FILENAME, "BODYDATA.DAT")
        self.assertEqual(BODYDATA_702_EXACT_BYTES, 811_876_768)
        self.assertEqual(BODYDATA_UFU_MAGIC_HEX, "895546550d0a1a0a")
        self.assertEqual(REQUIRED_UPDATE_SLOT, 1)
        self.assertEqual(REQUIRED_SLOT1_BODYDATA_PATH, "/BODYDATA.DAT")
        self.assertEqual(C2PA_MAX_LICENSES_CEILING, 100)
        self.assertEqual(P12_RQ_LIC_PATH, "p12:/cert/RQ_LIC.DAT")
        self.assertEqual(P12_DEVICE_NODE, "/dev/nflasha12")
        self.assertEqual(P12_REQUIRED_MOUNT_FLAG, "MS_RDONLY")
        self.assertEqual(STATUS_SAFE, "SAFE")
        self.assertEqual(
            GATE_G59_SSBOOT_WBI2_PRSVIMG_AND_LIRO_BYPASS_GUARD,
            G59_GATE_CODE,
        )
        self.assertEqual(
            GATE_G60_FX3_702_UFU_VERSION_FLOOR_AND_SLOT1_C2PA_GUARD,
            G60_GATE_CODE,
        )

        for sym in (
            "G59_GATE_ID",
            "G59_GATE_CODE",
            "G60_GATE_ID",
            "G60_GATE_CODE",
            "GATE_G59_SSBOOT_WBI2_PRSVIMG_AND_LIRO_BYPASS_GUARD",
            "GATE_G60_FX3_702_UFU_VERSION_FLOOR_AND_SLOT1_C2PA_GUARD",
            "STATUS_VERIFIED_G59",
            "STATUS_VERIFIED_G60",
            "Master60GateReport",
            "G59SsbootWbi2Result",
            "G60Slot1UfuC2paResult",
            "audit_phase177_donor_contracts",
            "verify_ssboot_wbi2_prsvimg_and_liro_guard",
            "verify_fx3_702_ufu_floor_and_slot1_c2pa_guard",
            "evaluate_g59_ssboot_wbi2_guard",
            "evaluate_g60_slot1_ufu_c2pa_guard",
            "evaluate_60gate_preflight",
            "evaluate_60_master_safety_gates",
        ):
            self.assertTrue(hasattr(fx3_safety, sym), f"Missing export {sym}")
            self.assertIn(sym, fx3_safety.__all__, f"Missing __all__ entry {sym}")

    def test_02_donor_audit_local_or_cleanroom_o_rdonly(self) -> None:
        res = audit_phase177_donor_contracts(repo_root=DEFAULT_REPO_ROOT)
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_VERIFIED_SAFE)
        self.assertEqual(res.access_mode, "O_RDONLY")
        self.assertTrue(res.fx3_contracts_verified)
        self.assertTrue(res.bodydata_header_verified)
        self.assertEqual(res.bodydata_total_bytes, BODYDATA_702_EXACT_BYTES)
        self.assertIn(
            res.verification_mode,
            ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"),
        )
        self.assertEqual(len(res.missing_markers), 0)

    def test_03_donor_audit_forced_clean_room(self) -> None:
        res = audit_phase177_donor_contracts(force_clean_room=True)
        self.assertTrue(res.valid)
        self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(res.files_inspected, 0)
        self.assertTrue(res.fx3_contracts_verified)
        self.assertTrue(res.bodydata_header_verified)

    def test_04_donor_audit_missing_directory_clean_room_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            res = audit_phase177_donor_contracts(
                work_root=Path(tmp) / "nonexistent",
                force_clean_room=False,
            )
        self.assertTrue(res.valid)
        self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(res.files_inspected, 0)

    def test_05_donor_audit_corrupted_file_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            wr = Path(tmp)
            for _key, (_body, rel, sz, _sha, toks, _lbl) in PINNED_PHASE177_DONOR_SPECS.items():
                p = wr / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                data = b"".join(toks).ljust(sz, b"\x00")
                p.write_bytes(data)
            bd = wr / PINNED_BODYDATA_HEADER_RELPATH
            bd.parent.mkdir(parents=True, exist_ok=True)
            bd.write_bytes(b"\x89UFU\r\n\x1a\nDATVPROVUDID".ljust(4096, b"\x00"))
            res = audit_phase177_donor_contracts(work_root=wr, force_clean_room=False)
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_PHASE177_DONOR_INTEGRITY)
        self.assertEqual(res.verification_mode, "LOCAL_DONOR_O_RDONLY")

    def test_06_donor_audit_corrupted_bodydata_header_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            wr = Path(tmp)
            for _key, (_body, rel, sz, _sha, toks, _lbl) in PINNED_PHASE177_DONOR_SPECS.items():
                p = wr / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(b"".join(toks))
            bd = wr / PINNED_BODYDATA_HEADER_RELPATH
            bd.parent.mkdir(parents=True, exist_ok=True)
            bd.write_bytes(b"CORRUPTED_HEADER" * 8)
            res = audit_phase177_donor_contracts(work_root=wr, force_clean_room=False)
        self.assertFalse(res.valid)
        self.assertFalse(res.bodydata_header_verified)
        self.assertEqual(res.status, STATUS_BLOCKED_PHASE177_DONOR_INTEGRITY)

    # --- 2. Gate G59: ssboot / WBI2 prsv-img + liro.ko + BLKROSET=1 + H0==H3 ---

    def test_07_synthetic_wbi2_sector0_and_magic_validation(self) -> None:
        sec0 = build_synthetic_wbi2_sector0()
        self.assertEqual(len(sec0), 512)
        self.assertTrue(sec0.startswith(WBI2_MAGIC_BYTES))
        sec0_sha = hashlib.sha256(sec0).hexdigest()
        res = verify_ssboot_wbi2_prsvimg_and_liro_guard(
            wbi2_sector0_bytes=sec0,
            tier0_wbi2_sector0_sha256=sec0_sha,
            h3_wbi2_sector0_sha256=sec0_sha,
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_VERIFIED_G59)

    def test_08_g59_default_safe_passes(self) -> None:
        res = verify_ssboot_wbi2_prsvimg_and_liro_guard()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_VERIFIED_G59)
        self.assertTrue(res.tier0_receipt_valid)
        self.assertTrue(res.stageb_ro_protection_valid)
        self.assertTrue(res.resume_bypass_guard_valid)
        self.assertTrue(res.clean_uninstall_valid)
        self.assertTrue(res.h0_equals_h3_wbi2)
        self.assertFalse(res.persistent_emmc_writes_authorized)
        self.assertFalse(res.persistent_write_release)

    def test_09_g59_missing_wbi2_sector0_receipt_blocked(self) -> None:
        res = verify_ssboot_wbi2_prsvimg_and_liro_guard(
            tier0_wbi2_sector0_captured=False,
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_G59_WBI2_TIER0_RECEIPT_MISSING)

    def test_10_g59_missing_full_nflasha5_h0_receipt_blocked(self) -> None:
        res = verify_ssboot_wbi2_prsvimg_and_liro_guard(
            tier0_nflasha5_full_captured=False,
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_G59_WBI2_TIER0_RECEIPT_MISSING)

    def test_11_g59_invalid_fx3rcpt1_magic_or_size_blocked(self) -> None:
        res1 = verify_ssboot_wbi2_prsvimg_and_liro_guard(fx3rcpt1_magic="BADMAGIC")
        res2 = verify_ssboot_wbi2_prsvimg_and_liro_guard(fx3rcpt1_packet_bytes=512)
        res3 = verify_ssboot_wbi2_prsvimg_and_liro_guard(fx3rcpt1_verified=False)
        for r in (res1, res2, res3):
            self.assertFalse(r.valid)
            self.assertEqual(r.status, STATUS_BLOCKED_G59_WBI2_TIER0_RECEIPT_MISSING)

    def test_12_g59_invalid_wbi2_magic_bytes_blocked(self) -> None:
        bad_sec0 = build_synthetic_wbi2_sector0(magic=b"WBI1\x00\x00\x00\x00")
        bad_sha = hashlib.sha256(bad_sec0).hexdigest()
        res = verify_ssboot_wbi2_prsvimg_and_liro_guard(
            wbi2_sector0_bytes=bad_sec0,
            tier0_wbi2_sector0_sha256=bad_sha,
            h3_wbi2_sector0_sha256=bad_sha,
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_G59_WBI2_TIER0_RECEIPT_MISSING)

    def test_13_g59_wbi2_sector0_sha_mismatch_blocked(self) -> None:
        sec0 = build_synthetic_wbi2_sector0()
        res = verify_ssboot_wbi2_prsvimg_and_liro_guard(
            wbi2_sector0_bytes=sec0,
            tier0_wbi2_sector0_sha256="a" * 64,
            h3_wbi2_sector0_sha256="a" * 64,
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_G59_WBI2_TIER0_RECEIPT_MISSING)

    def test_14_g59_wrong_wbi_partition_or_codec_blocked(self) -> None:
        res1 = verify_ssboot_wbi2_prsvimg_and_liro_guard(wbi_partition_dev="/dev/nflasha15")
        res2 = verify_ssboot_wbi2_prsvimg_and_liro_guard(wbi_compression_codec="GZIP")
        for r in (res1, res2):
            self.assertFalse(r.valid)
            self.assertEqual(r.status, STATUS_BLOCKED_G59_WBI2_TIER0_RECEIPT_MISSING)

    def test_15_g59_blkroset_nflasha5_zero_blocked(self) -> None:
        res = verify_ssboot_wbi2_prsvimg_and_liro_guard(blkroset_nflasha5=0)
        self.assertFalse(res.valid)
        self.assertEqual(
            res.status,
            STATUS_BLOCKED_G59_WBI2_STAGEB_WRITE_OR_BLKROSET_UNPROTECTED,
        )

    def test_16_g59_blkroset_pnflasha5_zero_blocked(self) -> None:
        res = verify_ssboot_wbi2_prsvimg_and_liro_guard(blkroset_pnflasha5=False)
        self.assertFalse(res.valid)
        self.assertEqual(
            res.status,
            STATUS_BLOCKED_G59_WBI2_STAGEB_WRITE_OR_BLKROSET_UNPROTECTED,
        )

    def test_17_g59_proc_udm_write_unblocked_blocked(self) -> None:
        res = verify_ssboot_wbi2_prsvimg_and_liro_guard(proc_udm_write_blocked=False)
        self.assertFalse(res.valid)
        self.assertEqual(
            res.status,
            STATUS_BLOCKED_G59_WBI2_STAGEB_WRITE_OR_BLKROSET_UNPROTECTED,
        )

    def test_18_g59_pm_suspend_disk_unblocked_blocked(self) -> None:
        res = verify_ssboot_wbi2_prsvimg_and_liro_guard(pm_suspend_disk_blocked=False)
        self.assertFalse(res.valid)
        self.assertEqual(
            res.status,
            STATUS_BLOCKED_G59_WBI2_STAGEB_WRITE_OR_BLKROSET_UNPROTECTED,
        )

    def test_19_g59_stageb_snapshot_save_or_liro_invoked_blocked(self) -> None:
        res1 = verify_ssboot_wbi2_prsvimg_and_liro_guard(stageb_snapshot_save_blocked=False)
        res2 = verify_ssboot_wbi2_prsvimg_and_liro_guard(liro_snapshot_save_invoked=True)
        for r in (res1, res2):
            self.assertFalse(r.valid)
            self.assertEqual(
                r.status,
                STATUS_BLOCKED_G59_WBI2_STAGEB_WRITE_OR_BLKROSET_UNPROTECTED,
            )

    def test_20_g59_wbi_persistent_writes_nonzero_blocked(self) -> None:
        res1 = verify_ssboot_wbi2_prsvimg_and_liro_guard(wbi_persistent_writes=1)
        res2 = verify_ssboot_wbi2_prsvimg_and_liro_guard(wbi_mutation_bytes=4096)
        for r in (res1, res2):
            self.assertFalse(r.valid)
            self.assertEqual(
                r.status,
                STATUS_BLOCKED_G59_WBI2_STAGEB_WRITE_OR_BLKROSET_UNPROTECTED,
            )

    def test_21_g59_active_unhandled_wbi2_resume_trap_blocked(self) -> None:
        res = verify_ssboot_wbi2_prsvimg_and_liro_guard(
            wbi2_active_resume_pending=True,
            wbi2_resume_bypass_verified=False,
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_G59_SSBOOT_RESUME_INIT_BYPASS_TRAP)

    def test_22_g59_sbin_init_bypassed_or_stage_a_verify_skipped_blocked(self) -> None:
        res1 = verify_ssboot_wbi2_prsvimg_and_liro_guard(sbin_init_bypassed=True)
        res2 = verify_ssboot_wbi2_prsvimg_and_liro_guard(init_entry_executed=False)
        res3 = verify_ssboot_wbi2_prsvimg_and_liro_guard(stage_a_verify_executed=False)
        for r in (res1, res2, res3):
            self.assertFalse(r.valid)
            self.assertEqual(r.status, STATUS_BLOCKED_G59_SSBOOT_RESUME_INIT_BYPASS_TRAP)

    def test_23_g59_clean_uninstall_h0_h3_sector0_drift_blocked(self) -> None:
        res = verify_ssboot_wbi2_prsvimg_and_liro_guard(
            h3_wbi2_sector0_sha256="b" * 64,
        )
        self.assertFalse(res.valid)
        self.assertFalse(res.h0_equals_h3_wbi2)
        self.assertEqual(
            res.status,
            STATUS_BLOCKED_G59_WBI2_CLEAN_UNINSTALL_H0_H3_MISMATCH,
        )

    def test_24_g59_clean_uninstall_h0_h3_full_partition_drift_blocked(self) -> None:
        res = verify_ssboot_wbi2_prsvimg_and_liro_guard(
            h3_nflasha5_full_sha256="c" * 64,
        )
        self.assertFalse(res.valid)
        self.assertFalse(res.h0_equals_h3_wbi2)
        self.assertEqual(
            res.status,
            STATUS_BLOCKED_G59_WBI2_CLEAN_UNINSTALL_H0_H3_MISMATCH,
        )

    def test_25_g59_warmboot_05s_not_preserved_blocked(self) -> None:
        res = verify_ssboot_wbi2_prsvimg_and_liro_guard(
            stock_warmboot_05s_preserved=False,
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            res.status,
            STATUS_BLOCKED_G59_WBI2_CLEAN_UNINSTALL_H0_H3_MISMATCH,
        )

    def test_26_g59_invalid_telemetry_fails_closed(self) -> None:
        res1 = verify_ssboot_wbi2_prsvimg_and_liro_guard(wbi_persistent_writes=-1)
        res2 = verify_ssboot_wbi2_prsvimg_and_liro_guard(blkroset_nflasha5=9)  # type: ignore[arg-type]
        res3 = verify_ssboot_wbi2_prsvimg_and_liro_guard(wbi_partition_dev="")
        for r in (res1, res2, res3):
            self.assertFalse(r.valid)
            self.assertEqual(r.status, STATUS_BLOCKED_G59_TELEMETRY_INVALID)

    def test_27_g59_persistent_write_request_redline_blocked(self) -> None:
        verdict, res = evaluate_g59_ssboot_wbi2_guard(
            force_clean_room=True,
            request_persistent_emmc_writes=True,
        )
        self.assertFalse(verdict.passed)
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)

    # --- 3. Gate G60: FX3 7.02 >= 2.04 UFU Floor, Slot-1 Root, C2PA <=100 & Wireless ---

    def test_28_g60_default_safe_passes(self) -> None:
        res = verify_fx3_702_ufu_floor_and_slot1_c2pa_guard()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_VERIFIED_G60)
        self.assertTrue(res.body_version_floor_valid)
        self.assertTrue(res.slot1_placement_valid)
        self.assertTrue(res.c2pa_and_p12_lock_valid)
        self.assertTrue(res.wireless_security_floor_valid)
        self.assertFalse(res.persistent_emmc_writes_authorized)
        self.assertFalse(res.persistent_write_release)

    def test_29_g60_body_version_202_and_200_blocked_7l7s(self) -> None:
        self.assertEqual(parse_firmware_version_tuple("2.02"), (2, 2, 0))
        self.assertEqual(parse_firmware_version_tuple("2.04"), (2, 4, 0))
        for ver in ("1.00", "2.00", "2.02", "2.03"):
            res = verify_fx3_702_ufu_floor_and_slot1_c2pa_guard(
                body_firmware_version=ver,
            )
            self.assertFalse(res.valid)
            self.assertEqual(res.status, STATUS_BLOCKED_G60_BODY_VERSION_BELOW_204_FLOOR)
            self.assertIn("7L+7S", " ".join(res.errors))

    def test_30_g60_body_version_204_and_702_allowed(self) -> None:
        for ver in ("2.04", "2.05", "3.00", "5.00", "6.02", "7.00", "7.02"):
            res = verify_fx3_702_ufu_floor_and_slot1_c2pa_guard(
                body_firmware_version=ver,
            )
            self.assertTrue(res.valid, f"Expected {ver} >= 2.04 to pass: {res.errors}")

    def test_31_g60_wrong_model_id_or_bodydata_size_or_ufu_magic_blocked(self) -> None:
        res1 = verify_fx3_702_ufu_floor_and_slot1_c2pa_guard(target_model_id=0x91030070)
        res2 = verify_fx3_702_ufu_floor_and_slot1_c2pa_guard(bodydata_size_bytes=847_081_840)
        res3 = verify_fx3_702_ufu_floor_and_slot1_c2pa_guard(bodydata_ufu_magic_hex="0000000000000000")
        for r in (res1, res2, res3):
            self.assertFalse(r.valid)
            self.assertEqual(r.status, STATUS_BLOCKED_G60_BODY_VERSION_BELOW_204_FLOOR)

    def test_32_g60_slot2_update_attempt_blocked(self) -> None:
        res = verify_fx3_702_ufu_floor_and_slot1_c2pa_guard(update_slot=2)
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_G60_SLOT1_ROOT_OR_DUPLICATE_BODYDATA)

    def test_33_g60_subdirectory_bodydata_path_blocked(self) -> None:
        res = verify_fx3_702_ufu_floor_and_slot1_c2pa_guard(
            bodydata_path="/PRIVATE/BODYDATA.DAT",
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_G60_SLOT1_ROOT_OR_DUPLICATE_BODYDATA)

    def test_34_g60_duplicate_renamed_bodydata_files_blocked(self) -> None:
        for entries in (
            ("BODYDATA.DAT", "BODYDATA (1).DAT"),
            ("BODYDATA.DAT", "BODYDATA_OLD.DAT"),
            ("BODYDATA.DAT", "BODYDATA.DAT"),
            ("BODYDATA (1).DAT",),
        ):
            res = verify_fx3_702_ufu_floor_and_slot1_c2pa_guard(
                slot1_root_entries=entries,
            )
            self.assertFalse(res.valid)
            self.assertEqual(res.status, STATUS_BLOCKED_G60_SLOT1_ROOT_OR_DUPLICATE_BODYDATA)

    def test_35_g60_slot2_containing_bodydata_blocked(self) -> None:
        res = verify_fx3_702_ufu_floor_and_slot1_c2pa_guard(
            slot2_root_entries=("BODYDATA.DAT",),
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_G60_SLOT1_ROOT_OR_DUPLICATE_BODYDATA)

    def test_36_g60_c2pa_import_slot2_or_subdir_blocked(self) -> None:
        res1 = verify_fx3_702_ufu_floor_and_slot1_c2pa_guard(c2pa_import_slot=2)
        res2 = verify_fx3_702_ufu_floor_and_slot1_c2pa_guard(c2pa_import_path="/cert/RQ_LIC.DAT")
        for r in (res1, res2):
            self.assertFalse(r.valid)
            self.assertEqual(r.status, STATUS_BLOCKED_G60_SLOT1_ROOT_OR_DUPLICATE_BODYDATA)

    def test_37_g60_c2pa_100_licenses_allowed_101_blocked(self) -> None:
        res_ok = verify_fx3_702_ufu_floor_and_slot1_c2pa_guard(c2pa_license_count=100)
        self.assertTrue(res_ok.valid)
        res_bad = verify_fx3_702_ufu_floor_and_slot1_c2pa_guard(c2pa_license_count=101)
        self.assertFalse(res_bad.valid)
        self.assertEqual(res_bad.status, STATUS_BLOCKED_G60_C2PA_100_LICENSE_CEILING_OR_P12_RO)

    def test_38_g60_p12_rq_lic_blkroset_zero_or_rw_mount_blocked(self) -> None:
        res1 = verify_fx3_702_ufu_floor_and_slot1_c2pa_guard(p12_blkroset=0)
        res2 = verify_fx3_702_ufu_floor_and_slot1_c2pa_guard(p12_mount_flags="rw,sync")
        res3 = verify_fx3_702_ufu_floor_and_slot1_c2pa_guard(c2pa_write_attempts_blocked=False)
        for r in (res1, res2, res3):
            self.assertFalse(r.valid)
            self.assertEqual(r.status, STATUS_BLOCKED_G60_C2PA_100_LICENSE_CEILING_OR_P12_RO)

    def test_39_g60_p12_mutation_bytes_nonzero_blocked(self) -> None:
        res = verify_fx3_702_ufu_floor_and_slot1_c2pa_guard(p12_mutation_bytes=64)
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_G60_C2PA_100_LICENSE_CEILING_OR_P12_RO)

    def test_40_g60_wireless_wep_wpa1_ipsec_rejected(self) -> None:
        for proto in ("WEP", "WEP-128", "WPA1", "WPA-PSK", "IPsec", "LEGACY_IPSEC"):
            res = verify_fx3_702_ufu_floor_and_slot1_c2pa_guard(
                stageb_wireless_profiles=("WPA2", proto),
            )
            self.assertFalse(res.valid, f"Expected deprecated {proto} to be blocked")
            self.assertEqual(res.status, STATUS_BLOCKED_G60_INSECURE_WIRELESS_WEP_WPA1_IPSEC)
            self.assertIn(proto, res.rejected_wireless_protocols)

    def test_41_g60_wireless_wpa2_wpa3_access_auth_allowed(self) -> None:
        res = verify_fx3_702_ufu_floor_and_slot1_c2pa_guard(
            stageb_wireless_profiles=("WPA2", "WPA3", "ACCESS_AUTHENTICATION"),
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.rejected_wireless_protocols, ())

    def test_42_g60_invalid_telemetry_fails_closed(self) -> None:
        res1 = verify_fx3_702_ufu_floor_and_slot1_c2pa_guard(c2pa_license_count=-1)
        res2 = verify_fx3_702_ufu_floor_and_slot1_c2pa_guard(p12_blkroset=7)  # type: ignore[arg-type]
        res3 = verify_fx3_702_ufu_floor_and_slot1_c2pa_guard(update_slot=True)  # type: ignore[arg-type]
        for r in (res1, res2, res3):
            self.assertFalse(r.valid)
            self.assertEqual(r.status, STATUS_BLOCKED_G60_TELEMETRY_INVALID)

    def test_43_g60_persistent_write_request_redline_blocked(self) -> None:
        verdict, res = evaluate_g60_slot1_ufu_c2pa_guard(
            force_clean_room=True,
            request_persistent_emmc_writes=True,
        )
        self.assertFalse(verdict.passed)
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)

    # --- 4. 60-Gate Master Preflight & Backward Compatibility ---

    def test_44_evaluate_60gate_preflight_offline_57_of_60(self) -> None:
        report = evaluate_60gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=False,
        )
        self.assertEqual(report.summary["total_gates"], 60)
        self.assertEqual(report.summary["verified_gates"], 57)
        self.assertEqual(report.summary["blocked_or_pending_gates"], 3)
        self.assertEqual(len(report.gates), 60)
        self.assertTrue(report.offline_57_gates_verified)
        self.assertFalse(report.all_60_gates_verified)
        self.assertTrue(report.g59_to_g60_all_passed)
        self.assertTrue(report.g13_to_g60_all_passed)
        self.assertFalse(report.overall_ready_for_hardware_attach)
        self.assertFalse(report.el3_payload_transmit_authorized)
        self.assertFalse(report.spi_nor_write_authorized)
        self.assertFalse(report.persistent_emmc_writes_authorized)
        self.assertFalse(report.persistent_write_release)
        self.assertEqual(report.physical_usb_packets_emitted, 0)
        self.assertEqual(report.raw_firmware_bytes_leaked, 0)
        self.assertEqual(report.status, "VERIFIED_57_OF_60_AWAITING_PHYSICAL_TIER0")
        for idx in (9, 10, 11):
            self.assertEqual(report.gates[idx]["status"], STATUS_FAIL_OFFLINE_HARDWARE_NOT_ATTACHED)

    def test_45_evaluate_60gate_preflight_dry_run_60_of_60(self) -> None:
        report = evaluate_60_master_safety_gates(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
        )
        self.assertEqual(report.summary["total_gates"], 60)
        self.assertEqual(report.summary["verified_gates"], 60)
        self.assertEqual(report.summary["blocked_or_pending_gates"], 0)
        self.assertTrue(report.all_60_gates_verified)
        self.assertTrue(report.dry_run_rehearsal_only)
        self.assertTrue(report.g59_to_g60_all_passed)
        self.assertFalse(report.overall_ready_for_hardware_attach)
        self.assertFalse(report.el3_payload_transmit_authorized)
        self.assertFalse(report.spi_nor_write_authorized)
        self.assertFalse(report.persistent_emmc_writes_authorized)
        self.assertFalse(report.persistent_write_release)
        self.assertEqual(report.physical_usb_packets_emitted, 0)
        self.assertEqual(report.raw_firmware_bytes_leaked, 0)
        self.assertEqual(report.status, "VERIFIED_ALL_60_GATES_DRY_RUN_SIMULATED_BACKUP")

    def test_46_evaluate_60gate_preflight_propagates_g59_g60_and_g58_faults(self) -> None:
        r_g59 = evaluate_60gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            ssboot_wbi2_kwargs={"blkroset_nflasha5": 0},
        )
        self.assertFalse(r_g59.all_60_gates_verified)
        self.assertEqual(
            r_g59.status,
            STATUS_BLOCKED_G59_WBI2_STAGEB_WRITE_OR_BLKROSET_UNPROTECTED,
        )

        r_g60 = evaluate_60gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            slot1_ufu_c2pa_kwargs={"body_firmware_version": "2.02"},
        )
        self.assertFalse(r_g60.all_60_gates_verified)
        self.assertEqual(r_g60.status, STATUS_BLOCKED_G60_BODY_VERSION_BELOW_204_FLOOR)

        r_g58 = evaluate_60gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            bench_interlock_kwargs={"auto_flash_requested": True},
        )
        self.assertFalse(r_g58.all_60_gates_verified)
        self.assertEqual(r_g58.status, STATUS_BLOCKED_G58_AUTO_FLASH_INTERLOCK_VIOLATION)

    def test_47_evaluate_58gate_preflight_backward_compatibility_intact(self) -> None:
        r58 = evaluate_58gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
        )
        self.assertEqual(r58.summary["total_gates"], 58)
        self.assertEqual(r58.summary["verified_gates"], 58)
        self.assertTrue(r58.all_58_gates_verified)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = package_cli_main(["verify-58-gates", "--clean-room", "--dry-run-simulated-backup", "--json"])
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["summary"]["verified_gates"], 58)

    # --- 5. CLI Entrypoints, Zero Raw Firmware Leakage & Performance ---

    def test_48_cli_subcommands_json_and_text_outputs(self) -> None:
        for subcmd in (
            ["verify-g59-ssboot-wbi2-guard", "--force-clean-room", "--json"],
            ["verify-g60-slot1-ufu-c2pa-guard", "--force-clean-room", "--json"],
            ["verify-60-gates", "--force-clean-room", "--dry-run-simulated", "--json"],
            ["verify-60-gates", "--force-clean-room"],
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = package_cli_main(subcmd)
            self.assertEqual(rc, 0, f"CLI failed for {subcmd}: {buf.getvalue()}")
            if "--json" in subcmd:
                data = json.loads(buf.getvalue())
                self.assertFalse(data["persistent_emmc_writes_authorized"])

    def test_49_module_cli_and_zero_raw_firmware_leakage_in_json(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = module_cli_main(["--force-clean-room", "--dry-run-simulated", "--json"])
        self.assertEqual(rc, 0)
        text = buf.getvalue()
        self.assertNotIn("b'\\x7fELF", text)
        self.assertNotIn('b"\\x7fELF', text)
        payload = json.loads(text)
        self.assertEqual(payload["summary"]["verified_gates"], 60)
        self.assertEqual(payload["physical_usb_packets_emitted"], 0)
        self.assertEqual(payload["raw_firmware_bytes_leaked"], 0)
        self.assertFalse(payload["overall_ready_for_hardware_attach"])

    def test_50_verify_60_gates_fast_runtime_under_6s(self) -> None:
        t0 = time.monotonic()
        report = evaluate_60gate_preflight(
            DEFAULT_REPO_ROOT,
            dry_run_simulated=True,
        )
        elapsed = time.monotonic() - t0
        self.assertTrue(report.all_60_gates_verified)
        self.assertLess(elapsed, 6.0)


if __name__ == "__main__":
    unittest.main()
