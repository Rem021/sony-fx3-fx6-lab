"""Fast dual-mode unit tests for Phase 142 — Real-Hardware Main Track Part 9:
Gate G43 (`AdjustControl 0x40` / `libJiritsu.so` Electrical, `/tmp/jbusy` Precheck &
`p6` `25 MiB` Quota Guard), Gate G44 (`/dev/cnflasha15` SPACC Cipher-Boundary, Tier-0
Cold-Backup Receipt, SD Escape-Hatch & `p1`/`p3` Mutual-Exclusion Preflight), and
Unified 44-Gate Master Safety Preflight (`G01..G44` / `verify-44-gates`).
"""

from __future__ import annotations

import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import fx3_safety
from fx3_safety.__main__ import main as package_cli_main
from fx3_safety.master_16gate_preflight import DEFAULT_REPO_ROOT
from fx3_safety.realhw_jiritsu_cnflasha_and_44gate_guard import (
    FX3_MODEL_ID_STR,
    G43_GATE_CODE,
    G43_GATE_ID,
    G44_GATE_CODE,
    G44_GATE_ID,
    JIRITSU_ELF_REQUIRED_DT_HASH,
    JIRITSU_ELF_REQUIRED_PT_LOAD_ALIGN,
    JIRITSU_JBUSY_BUSY_CODE,
    JIRITSU_JBUSY_ENOENT_CODE,
    JIRITSU_MIN_BATTERY_LOAD_VOLTAGE_V,
    JIRITSU_MIN_BATTERY_SOC_PCT,
    JIRITSU_WIRE_PREFIX_HEX,
    P1_KEMCO_REQUIRED_CFG_UART,
    P6_MAX_SAFE_STAGING_BYTES,
    P6_PARTITION_CAPACITY_BYTES,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PINNED_PHASE142_DONOR_SPECS,
    REALHW_JIRITSU_CNFLASHA_44GATE_SCHEMA,
    REALHW_JIRITSU_CNFLASHA_44GATE_VERSION,
    SD_ESCAPE_HATCH_MAX_US,
    SD_ESCAPE_HATCH_NOMINAL_US,
    SD_ESCAPE_HATCH_STOCK_TARGET,
    SPACC_ENCRYPTED_TYPE5_FLAG1_PARTITIONS,
    SPI_NOR_DDRTRAINING_OFFSET,
    STATUS_BLOCKED_DONOR_INTEGRITY,
    STATUS_BLOCKED_G43_TELEMETRY_INVALID,
    STATUS_BLOCKED_G44_TELEMETRY_INVALID,
    STATUS_BLOCKED_JIRITSU_ELECTRICAL_BROWNOUT_RISK,
    STATUS_BLOCKED_JIRITSU_ELF_ALIGNMENT_OR_SELFDELETE,
    STATUS_BLOCKED_JIRITSU_JBUSY_ACTIVE_0X10000011,
    STATUS_BLOCKED_JIRITSU_WIRE_FRAMING_OR_FORBIDDEN_OPCODE,
    STATUS_BLOCKED_P1_P3_MUTUAL_EXCLUSION_OR_UART_TRAP,
    STATUS_BLOCKED_P6_QUOTA_OR_RESIDUAL_EXHAUSTION,
    STATUS_BLOCKED_PERSISTENT_EMMC_WRITE,
    STATUS_BLOCKED_RAW_PNFLASHA_OR_FORBIDDEN_FLASH_TOOL,
    STATUS_BLOCKED_SD_ESCAPE_HATCH_MISSING_OR_SLOW,
    STATUS_BLOCKED_TIER0_COLD_BACKUP_RECEIPT_INVALID,
    STATUS_SAFE,
    STATUS_VERIFIED_G43,
    STATUS_VERIFIED_G44,
    STATUS_VERIFIED_SAFE,
    TIER0_COLD_BACKUP_REQUIRED_KEYS,
    TIER0_SECTOR0_MAGIC,
    TIER0_SECTOR0_VERSION,
    audit_phase142_donor_contracts,
    classify_spacc_block_device,
    compute_p6_quota_utilization_pct,
    default_verified_tier0_sha256_receipts,
    evaluate_44_master_safety_gates,
    evaluate_44gate_preflight,
    evaluate_g43_jiritsu_service,
    evaluate_g44_cnflasha_dualboot,
    main as module_cli_main,
    validate_elf_64k_alignment_and_hash,
    validate_tier0_cold_backup_receipt,
    verify_cnflasha_spacc_sd_escape_and_p1_p3_guard,
    verify_jiritsu_service_session_and_p6_guard,
)
from fx3_safety.rig_groundloop_lensrail_and_20gate_guard import (
    STATUS_FAIL_OFFLINE_HARDWARE_NOT_ATTACHED,
)
from fx3_safety.vp_strobe_vehiclerig_ibis_and_42gate_guard import (
    STATUS_BLOCKED_GENLOCK_TRILEVEL_INTO_FX3_LTC_TERMINAL,
    STATUS_BLOCKED_IBIS_ACTIVE_UNDER_SUSTAINED_ENGINE_RESONANCE,
    evaluate_42gate_preflight,
)


class RealHwJiritsuCnflashaAnd44GateGuardTests(unittest.TestCase):
    # --- 1. Hard Redlines, Package Exports & O_RDONLY Donor Audit ---

    def test_01_hard_locked_redlines_and_package_exports(self) -> None:
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(PERSISTENT_WRITE_RELEASE)
        self.assertEqual(
            REALHW_JIRITSU_CNFLASHA_44GATE_SCHEMA,
            "fx3-realhw-jiritsu-cnflasha-44gate-preflight-v1",
        )
        self.assertEqual(REALHW_JIRITSU_CNFLASHA_44GATE_VERSION, "1.0.0")
        for sym in (
            "REALHW_JIRITSU_CNFLASHA_44GATE_SCHEMA",
            "G43_GATE_ID",
            "G43_GATE_CODE",
            "G44_GATE_ID",
            "G44_GATE_CODE",
            "STATUS_VERIFIED_G43",
            "STATUS_VERIFIED_G44",
            "STATUS_BLOCKED_JIRITSU_ELECTRICAL_BROWNOUT_RISK",
            "STATUS_BLOCKED_JIRITSU_JBUSY_ACTIVE_0X10000011",
            "STATUS_BLOCKED_JIRITSU_WIRE_FRAMING_OR_FORBIDDEN_OPCODE",
            "STATUS_BLOCKED_JIRITSU_ELF_ALIGNMENT_OR_SELFDELETE",
            "STATUS_BLOCKED_P6_QUOTA_OR_RESIDUAL_EXHAUSTION",
            "STATUS_BLOCKED_TIER0_COLD_BACKUP_RECEIPT_INVALID",
            "STATUS_BLOCKED_RAW_PNFLASHA_OR_FORBIDDEN_FLASH_TOOL",
            "STATUS_BLOCKED_SD_ESCAPE_HATCH_MISSING_OR_SLOW",
            "STATUS_BLOCKED_P1_P3_MUTUAL_EXCLUSION_OR_UART_TRAP",
            "audit_phase142_donor_contracts",
            "compute_p6_quota_utilization_pct",
            "validate_elf_64k_alignment_and_hash",
            "classify_spacc_block_device",
            "validate_tier0_cold_backup_receipt",
            "default_verified_tier0_sha256_receipts",
            "verify_jiritsu_service_session_and_p6_guard",
            "verify_cnflasha_spacc_sd_escape_and_p1_p3_guard",
            "evaluate_g43_jiritsu_service",
            "evaluate_g44_cnflasha_dualboot",
            "evaluate_44gate_preflight",
            "evaluate_44_master_safety_gates",
            "realhw_jiritsu_cnflasha_and_44gate_guard",
        ):
            self.assertIn(sym, fx3_safety.__all__)
            self.assertTrue(hasattr(fx3_safety, sym))
        # Prior Phase exports must remain completely intact
        self.assertEqual(fx3_safety.FAN_MODE_AUTO1, "AUTO1")
        self.assertEqual(
            fx3_safety.STATUS_BLOCKED_DONOR_INTEGRITY,
            "BLOCKED_USBLAN_PTPIP_DONOR_INTEGRITY_MISMATCH",
        )
        self.assertEqual(
            fx3_safety.VP_STROBE_VEHICLERIG_42GATE_SCHEMA,
            "fx3-vp-strobe-vehiclerig-ibis-42gate-preflight-v1",
        )

    def test_02_donor_audit_o_rdonly_and_clean_room_fallback(self) -> None:
        observed_flags = []
        orig_open = os.open

        def spy_open(path, flags, *args, **kwargs):
            observed_flags.append((str(path), flags))
            return orig_open(path, flags, *args, **kwargs)

        with patch("os.open", side_effect=spy_open):
            res_default = audit_phase142_donor_contracts()
        self.assertTrue(res_default.valid)
        self.assertEqual(res_default.status, STATUS_VERIFIED_SAFE)
        self.assertEqual(res_default.access_mode, "O_RDONLY")
        self.assertTrue(res_default.jiritsu_contracts_verified)
        self.assertTrue(res_default.partition_table_contracts_verified)
        self.assertTrue(res_default.updater_uart_contracts_verified)
        self.assertEqual(res_default.missing_markers, ())

        if res_default.verification_mode == "LOCAL_DONOR_O_RDONLY":
            self.assertEqual(res_default.files_inspected, 8)
            self.assertGreaterEqual(len(observed_flags), 8)
            for _path, flags in observed_flags:
                self.assertEqual(flags & 3, os.O_RDONLY)
        else:
            self.assertEqual(res_default.files_inspected, 0)

        res_clean = audit_phase142_donor_contracts(force_clean_room=True)
        self.assertTrue(res_clean.valid)
        self.assertEqual(res_clean.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(res_clean.files_inspected, 0)
        self.assertEqual(len(res_clean.sha256_by_artifact), 8)

        with tempfile.TemporaryDirectory() as missing_dir:
            res_missing = audit_phase142_donor_contracts(
                work_root=Path(missing_dir), force_clean_room=False
            )
            self.assertTrue(res_missing.valid)
            self.assertEqual(res_missing.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_03_donor_audit_integrity_mismatch_and_missing_marker_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            for key, (_body, rel_path, _sz, _sha, _toks, _lbl) in PINNED_PHASE142_DONOR_SPECS.items():
                dst = tmp / rel_path
                dst.parent.mkdir(parents=True, exist_ok=True)
                if key == "fx3_lib_jiritsu":
                    dst.write_bytes(b"corrupted-jiritsu")
                else:
                    dst.write_bytes(b"corrupted-donor")
            res = audit_phase142_donor_contracts(work_root=tmp, force_clean_room=False)
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_DONOR_INTEGRITY)
        self.assertFalse(res.jiritsu_contracts_verified)
        self.assertFalse(res.partition_table_contracts_verified)
        self.assertFalse(res.updater_uart_contracts_verified)
        self.assertGreaterEqual(len(res.missing_markers), 8)

    def test_04_donor_audit_large_binaries_dual_mode(self) -> None:
        res = audit_phase142_donor_contracts(include_large_binaries=True)
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_VERIFIED_SAFE)
        self.assertEqual(res.access_mode, "O_RDONLY")
        if res.verification_mode == "LOCAL_DONOR_O_RDONLY":
            self.assertTrue(res.large_binaries_scanned)
            self.assertGreaterEqual(res.files_inspected, 10)
        else:
            self.assertFalse(res.large_binaries_scanned)

    # --- 2. Pure Helper Functions ---

    def test_05_helper_compute_p6_quota_utilization_pct_and_validation(self) -> None:
        pct_probe = compute_p6_quota_utilization_pct(10_032, P6_PARTITION_CAPACITY_BYTES)
        self.assertAlmostEqual(pct_probe, (10_032 / 26_214_400) * 100.0, places=5)
        pct_limit = compute_p6_quota_utilization_pct(
            P6_MAX_SAFE_STAGING_BYTES, P6_PARTITION_CAPACITY_BYTES
        )
        self.assertAlmostEqual(pct_limit, (8 * 1024 * 1024 / 26_214_400) * 100.0, places=4)
        self.assertEqual(compute_p6_quota_utilization_pct(0), 0.0)
        with self.assertRaises(ValueError):
            compute_p6_quota_utilization_pct(-1)
        with self.assertRaises(ValueError):
            compute_p6_quota_utilization_pct(True)  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            compute_p6_quota_utilization_pct(100, 0)

    def test_06_helper_validate_elf_64k_alignment_and_hash(self) -> None:
        self.assertTrue(
            validate_elf_64k_alignment_and_hash(
                JIRITSU_ELF_REQUIRED_PT_LOAD_ALIGN, JIRITSU_ELF_REQUIRED_DT_HASH
            )
        )
        self.assertFalse(
            validate_elf_64k_alignment_and_hash(0x1000, JIRITSU_ELF_REQUIRED_DT_HASH)
        )
        self.assertFalse(
            validate_elf_64k_alignment_and_hash(
                JIRITSU_ELF_REQUIRED_PT_LOAD_ALIGN, (2, 1, 0, 0)
            )
        )
        self.assertFalse(validate_elf_64k_alignment_and_hash(-1, (1, 1, 0, 0)))
        self.assertFalse(validate_elf_64k_alignment_and_hash(0x10000, (1, 1, 0)))
        self.assertFalse(validate_elf_64k_alignment_and_hash(0x10000, (True, 1, 0, 0)))

    def test_07_helper_classify_spacc_block_device(self) -> None:
        ok_cn, reason_cn = classify_spacc_block_device(15, "/dev/cnflasha15", write_mode=True)
        self.assertTrue(ok_cn)
        self.assertEqual(reason_cn, "SPACC_TRANSPARENT_DEVICE_OK")

        ok_nf, reason_nf = classify_spacc_block_device(15, "/dev/nflasha15", write_mode=True)
        self.assertTrue(ok_nf)
        self.assertEqual(reason_nf, "SPACC_TRANSPARENT_DEVICE_OK")

        ok_pn_w, reason_pn_w = classify_spacc_block_device(15, "/dev/pnflasha15", write_mode=True)
        self.assertFalse(ok_pn_w)
        self.assertEqual(reason_pn_w, "RAW_PNFLASHA_WRITE_BLOCKED")

        ok_pn_r, reason_pn_r = classify_spacc_block_device(15, "/dev/pnflasha15", write_mode=False)
        self.assertTrue(ok_pn_r)
        self.assertEqual(reason_pn_r, "RAW_PNFLASHA_READONLY_INSPECT")

        ok_mismatch, reason_mismatch = classify_spacc_block_device(
            15, "/dev/cnflasha7", write_mode=True
        )
        self.assertFalse(ok_mismatch)
        self.assertEqual(reason_mismatch, "SPACC_TARGET_DEVICE_MISMATCH")

        ok_bad_part, _ = classify_spacc_block_device(0, "/dev/nflasha0", write_mode=True)
        self.assertFalse(ok_bad_part)

    def test_08_helper_validate_tier0_cold_backup_receipt(self) -> None:
        receipts = default_verified_tier0_sha256_receipts()
        ok, bad = validate_tier0_cold_backup_receipt(receipts)
        self.assertTrue(ok)
        self.assertEqual(bad, ())
        self.assertEqual(tuple(receipts.keys()), TIER0_COLD_BACKUP_REQUIRED_KEYS)

        broken = dict(receipts)
        broken["p18"] = "not-a-sha256"
        ok_b, bad_b = validate_tier0_cold_backup_receipt(broken)
        self.assertFalse(ok_b)
        self.assertEqual(bad_b, ("p18",))

        ok_nonmap, _ = validate_tier0_cold_backup_receipt(["sector0"])  # type: ignore[arg-type]
        self.assertFalse(ok_nonmap)

    # --- 3. Gate G43 Unit Tests ---

    def test_09_g43_default_nominal_passes(self) -> None:
        res = verify_jiritsu_service_session_and_p6_guard()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_SAFE)
        self.assertEqual(res.violation_codes, ())
        self.assertTrue(res.electrical_power_safe)
        self.assertTrue(res.jbusy_precheck_safe)
        self.assertTrue(res.wire_framing_and_opcodes_safe)
        self.assertTrue(res.elf_alignment_and_selfdelete_safe)
        self.assertTrue(res.p6_quota_and_cleanup_safe)
        self.assertFalse(res.persistent_emmc_writes_authorized)
        self.assertFalse(res.persistent_write_release)
        self.assertEqual(res.p6_capacity_bytes, 26_214_400)

    def test_10_g43_blocks_low_battery_soc_and_low_load_voltage(self) -> None:
        res_soc = verify_jiritsu_service_session_and_p6_guard(np_fz100_soc_pct=74.9)
        self.assertFalse(res_soc.valid)
        self.assertEqual(res_soc.status, STATUS_BLOCKED_JIRITSU_ELECTRICAL_BROWNOUT_RISK)
        self.assertFalse(res_soc.electrical_power_safe)

        res_v = verify_jiritsu_service_session_and_p6_guard(np_fz100_load_voltage_v=7.39)
        self.assertFalse(res_v.valid)
        self.assertEqual(res_v.status, STATUS_BLOCKED_JIRITSU_ELECTRICAL_BROWNOUT_RISK)
        self.assertFalse(res_v.electrical_power_safe)

        res_boundary = verify_jiritsu_service_session_and_p6_guard(
            np_fz100_soc_pct=JIRITSU_MIN_BATTERY_SOC_PCT,
            np_fz100_load_voltage_v=JIRITSU_MIN_BATTERY_LOAD_VOLTAGE_V,
        )
        self.assertTrue(res_boundary.valid)

    def test_11_g43_regulated_usbpd_mitigates_low_battery_and_blocks_weak_pd(self) -> None:
        res_pd_ok = verify_jiritsu_service_session_and_p6_guard(
            np_fz100_soc_pct=50.0,
            np_fz100_load_voltage_v=7.1,
            usb_pd_regulated_supply_active=True,
            usb_pd_voltage_v=9.0,
            usb_pd_contract_watts=27.0,
        )
        self.assertTrue(res_pd_ok.valid)
        self.assertEqual(res_pd_ok.status, STATUS_SAFE)
        self.assertGreaterEqual(len(res_pd_ok.warnings), 1)

        res_pd_weak = verify_jiritsu_service_session_and_p6_guard(
            np_fz100_soc_pct=90.0,
            np_fz100_load_voltage_v=8.0,
            usb_pd_regulated_supply_active=True,
            usb_pd_voltage_v=5.0,
            usb_pd_contract_watts=15.0,
        )
        self.assertFalse(res_pd_weak.valid)
        self.assertEqual(res_pd_weak.status, STATUS_BLOCKED_JIRITSU_ELECTRICAL_BROWNOUT_RISK)

    def test_12_g43_blocks_jbusy_active_0x10000011(self) -> None:
        res_exists = verify_jiritsu_service_session_and_p6_guard(jbusy_file_exists=True)
        self.assertFalse(res_exists.valid)
        self.assertEqual(res_exists.status, STATUS_BLOCKED_JIRITSU_JBUSY_ACTIVE_0X10000011)
        self.assertFalse(res_exists.jbusy_precheck_safe)

        res_code = verify_jiritsu_service_session_and_p6_guard(
            jbusy_precheck_code=JIRITSU_JBUSY_BUSY_CODE
        )
        self.assertFalse(res_code.valid)
        self.assertEqual(res_code.status, STATUS_BLOCKED_JIRITSU_JBUSY_ACTIVE_0X10000011)
        self.assertEqual(res_code.jbusy_precheck_code_hex, "0x10000011")

    def test_13_g43_blocks_wire_prefix_selector2_and_forbidden_opcodes(self) -> None:
        res_prefix = verify_jiritsu_service_session_and_p6_guard(wire_prefix_hex="00ff01")
        self.assertFalse(res_prefix.valid)
        self.assertEqual(
            res_prefix.status, STATUS_BLOCKED_JIRITSU_WIRE_FRAMING_OR_FORBIDDEN_OPCODE
        )

        res_sel2 = verify_jiritsu_service_session_and_p6_guard(wire_selector=2)
        self.assertFalse(res_sel2.valid)
        self.assertEqual(
            res_sel2.status, STATUS_BLOCKED_JIRITSU_WIRE_FRAMING_OR_FORBIDDEN_OPCODE
        )

        for bad_op in ("MODE", "START", "FORMAT", "MOUNT", "JIRITSU_FORMAT"):
            res_op = verify_jiritsu_service_session_and_p6_guard(
                session_opcodes=("JIRITSU_SET_FILE2", bad_op)
            )
            self.assertFalse(res_op.valid)
            self.assertEqual(
                res_op.status, STATUS_BLOCKED_JIRITSU_WIRE_FRAMING_OR_FORBIDDEN_OPCODE
            )
            self.assertIn(bad_op, res_op.forbidden_opcodes_detected)

    def test_14_g43_blocks_elf_alignment_dt_hash_and_missing_unlinkat(self) -> None:
        res_align = verify_jiritsu_service_session_and_p6_guard(
            elf_pt_load_align_bytes=0x1000
        )
        self.assertFalse(res_align.valid)
        self.assertEqual(
            res_align.status, STATUS_BLOCKED_JIRITSU_ELF_ALIGNMENT_OR_SELFDELETE
        )

        res_hash = verify_jiritsu_service_session_and_p6_guard(
            elf_dt_hash_tuple=(0, 1, 0, 0)
        )
        self.assertFalse(res_hash.valid)
        self.assertEqual(
            res_hash.status, STATUS_BLOCKED_JIRITSU_ELF_ALIGNMENT_OR_SELFDELETE
        )

        res_unlink = verify_jiritsu_service_session_and_p6_guard(
            constructor_unlinkat_self_delete_enabled=False
        )
        self.assertFalse(res_unlink.valid)
        self.assertEqual(
            res_unlink.status, STATUS_BLOCKED_JIRITSU_ELF_ALIGNMENT_OR_SELFDELETE
        )

    def test_15_g43_blocks_p6_quota_exceeded_and_residual_files(self) -> None:
        res_limit = verify_jiritsu_service_session_and_p6_guard(
            peak_p6_bytes=P6_MAX_SAFE_STAGING_BYTES,
            p6_residual_files=0,
        )
        self.assertTrue(res_limit.valid)

        res_over = verify_jiritsu_service_session_and_p6_guard(
            peak_p6_bytes=P6_MAX_SAFE_STAGING_BYTES + 1
        )
        self.assertFalse(res_over.valid)
        self.assertEqual(res_over.status, STATUS_BLOCKED_P6_QUOTA_OR_RESIDUAL_EXHAUSTION)

        res_res = verify_jiritsu_service_session_and_p6_guard(p6_residual_files=1)
        self.assertFalse(res_res.valid)
        self.assertEqual(res_res.status, STATUS_BLOCKED_P6_QUOTA_OR_RESIDUAL_EXHAUSTION)

    def test_16_g43_blocks_invalid_telemetry_and_persistent_emmc_write_request(self) -> None:
        for bad_kw in (
            {"np_fz100_soc_pct": float("nan")},
            {"np_fz100_soc_pct": 105.0},
            {"np_fz100_load_voltage_v": -1.0},
            {"wire_prefix_hex": "zz"},
            {"wire_selector": True},
            {"session_opcodes": "MODE"},
            {"elf_dt_hash_tuple": (1, 1, 0)},
            {"peak_p6_bytes": True},
            {"p6_residual_files": -1},
        ):
            res_bad = verify_jiritsu_service_session_and_p6_guard(**bad_kw)
            self.assertFalse(res_bad.valid)
            self.assertEqual(res_bad.status, STATUS_BLOCKED_G43_TELEMETRY_INVALID)

        res_emmc = verify_jiritsu_service_session_and_p6_guard(
            request_persistent_emmc_writes=True
        )
        self.assertFalse(res_emmc.valid)
        self.assertEqual(res_emmc.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        self.assertFalse(res_emmc.persistent_emmc_writes_authorized)

    def test_17_g43_accumulates_multiple_violations(self) -> None:
        res = verify_jiritsu_service_session_and_p6_guard(
            np_fz100_soc_pct=50.0,
            jbusy_file_exists=True,
            wire_selector=2,
            elf_pt_load_align_bytes=0x1000,
            p6_residual_files=2,
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            res.violation_codes,
            (
                STATUS_BLOCKED_JIRITSU_ELECTRICAL_BROWNOUT_RISK,
                STATUS_BLOCKED_JIRITSU_JBUSY_ACTIVE_0X10000011,
                STATUS_BLOCKED_JIRITSU_WIRE_FRAMING_OR_FORBIDDEN_OPCODE,
                STATUS_BLOCKED_JIRITSU_ELF_ALIGNMENT_OR_SELFDELETE,
                STATUS_BLOCKED_P6_QUOTA_OR_RESIDUAL_EXHAUSTION,
            ),
        )

    # --- 4. Gate G44 Unit Tests ---

    def test_18_g44_default_nominal_passes_and_single_bank_transactions_emit_warnings(self) -> None:
        res_default = verify_cnflasha_spacc_sd_escape_and_p1_p3_guard()
        self.assertTrue(res_default.valid)
        self.assertEqual(res_default.status, STATUS_SAFE)
        self.assertTrue(res_default.tier0_cold_backup_safe)
        self.assertTrue(res_default.spacc_boundary_and_flasher_safe)
        self.assertTrue(res_default.sd_escape_hatch_safe)
        self.assertTrue(res_default.p1_p3_mutex_and_uart_safe)
        self.assertFalse(res_default.persistent_emmc_writes_authorized)
        self.assertFalse(res_default.persistent_write_release)

        res_p1 = verify_cnflasha_spacc_sd_escape_and_p1_p3_guard(
            target_partition_num=1,
            target_block_device="/dev/nflasha1",
            modify_p1_in_transaction=True,
            modify_p3_in_transaction=False,
        )
        self.assertTrue(res_p1.valid)
        self.assertGreaterEqual(len(res_p1.warnings), 1)

        res_p3 = verify_cnflasha_spacc_sd_escape_and_p1_p3_guard(
            target_partition_num=3,
            target_block_device="/dev/cnflasha3",
            modify_p1_in_transaction=False,
            modify_p3_in_transaction=True,
        )
        self.assertTrue(res_p3.valid)
        self.assertGreaterEqual(len(res_p3.warnings), 1)

    def test_19_g44_blocks_incomplete_or_invalid_tier0_cold_backup_receipts(self) -> None:
        for bad_kw in (
            {"tier0_receipt_verified": False},
            {"sector0_magic": "0000"},
            {"sector0_version": "1.00"},
            {"p1_dat2_model_id": "91030000"},
            {"p1_dat3_present": False},
            {"p2_backup_bin_present": False},
            {"p2_psd_bin_present": False},
            {"p2_defdet_bin_present": False},
            {"p6_jiritsu_backed_up": False},
            {"p12_cert_backed_up": False},
            {"p18_lensfile_backed_up": False},
            {"spi_nor_ddrtraining_backed_up": False},
            {"spi_nor_ddrtraining_offset": 0x0},
            {"two_pass_sha256_verified": False},
            {"tier0_sha256_receipts": {"sector0": "bad"}},
        ):
            res = verify_cnflasha_spacc_sd_escape_and_p1_p3_guard(**bad_kw)
            self.assertFalse(res.valid, f"expected fail for {bad_kw}")
            self.assertEqual(res.status, STATUS_BLOCKED_TIER0_COLD_BACKUP_RECEIPT_INVALID)
            self.assertFalse(res.tier0_cold_backup_safe)

    def test_20_g44_blocks_raw_pnflasha_writes_across_all_spacc_type5_flag1_partitions(self) -> None:
        for part_num in SPACC_ENCRYPTED_TYPE5_FLAG1_PARTITIONS:
            res_pn = verify_cnflasha_spacc_sd_escape_and_p1_p3_guard(
                target_partition_num=part_num,
                target_block_device=f"/dev/pnflasha{part_num}",
            )
            self.assertFalse(res_pn.valid)
            self.assertEqual(
                res_pn.status, STATUS_BLOCKED_RAW_PNFLASHA_OR_FORBIDDEN_FLASH_TOOL
            )
            self.assertTrue(res_pn.target_is_type5_flag1_encrypted)
            self.assertIn(f"/dev/pnflasha{part_num}", res_pn.forbidden_tools_or_paths_detected)

            res_cn = verify_cnflasha_spacc_sd_escape_and_p1_p3_guard(
                target_partition_num=part_num,
                target_block_device=f"/dev/cnflasha{part_num}",
            )
            self.assertTrue(res_cn.valid)

    def test_21_g44_blocks_forbidden_spi_nor_darwin_and_edisx_tools(self) -> None:
        for bad_kw in (
            {"spi_nor_overwrite_requested": True},
            {"sector0_repartition_requested": True},
            {"planned_commands": ("/usr/sbin/nor_loader_writer.sh",)},
            {"planned_commands": ("/usr/sbin/us_spi_firmup.sh /tmp/mew.bin",)},
            {"planned_commands": ("/usr/sbin/us_darwin_firm.sh nd",)},
            {"planned_commands": ("edisx.elf --repartition",)},
            {"planned_commands": ("dd if=/tmp/p15.img of=/dev/pnflasha15 bs=4096",)},
        ):
            res = verify_cnflasha_spacc_sd_escape_and_p1_p3_guard(**bad_kw)
            self.assertFalse(res.valid, f"expected fail for {bad_kw}")
            self.assertEqual(
                res.status, STATUS_BLOCKED_RAW_PNFLASHA_OR_FORBIDDEN_FLASH_TOOL
            )
            self.assertGreaterEqual(len(res.forbidden_tools_or_paths_detected), 1)

    def test_22_g44_blocks_missing_slow_or_wrong_target_sd_escape_hatch(self) -> None:
        for bad_kw in (
            {"sd_escape_hatch_enabled": False},
            {"sd_escape_exec_wrapper_verified": False},
            {"sd_escape_target": "/usr/bin/custom_im.elf"},
            {"sd_escape_bypass_latency_us": SD_ESCAPE_HATCH_MAX_US + 1.0},
        ):
            res = verify_cnflasha_spacc_sd_escape_and_p1_p3_guard(**bad_kw)
            self.assertFalse(res.valid)
            self.assertEqual(res.status, STATUS_BLOCKED_SD_ESCAPE_HATCH_MISSING_OR_SLOW)
            self.assertFalse(res.sd_escape_hatch_safe)

    def test_23_g44_blocks_p1_p3_simultaneous_modification_and_bad_uart_or_line1(self) -> None:
        res_mutex = verify_cnflasha_spacc_sd_escape_and_p1_p3_guard(
            modify_p1_in_transaction=True,
            modify_p3_in_transaction=True,
        )
        self.assertFalse(res_mutex.valid)
        self.assertEqual(
            res_mutex.status, STATUS_BLOCKED_P1_P3_MUTUAL_EXCLUSION_OR_UART_TRAP
        )

        res_uart = verify_cnflasha_spacc_sd_escape_and_p1_p3_guard(
            p1_kemco_cfg_uart=9
        )
        self.assertFalse(res_uart.valid)
        self.assertEqual(
            res_uart.status, STATUS_BLOCKED_P1_P3_MUTUAL_EXCLUSION_OR_UART_TRAP
        )

        for bad_line1 in (
            "echo noop",
            "rm -f /setting/updater/mode*",
            "rm -rf /setting/updater/mode* && sync",
        ):
            res_line = verify_cnflasha_spacc_sd_escape_and_p1_p3_guard(
                p1_init_first_line=bad_line1
            )
            self.assertFalse(res_line.valid)
            self.assertEqual(
                res_line.status, STATUS_BLOCKED_P1_P3_MUTUAL_EXCLUSION_OR_UART_TRAP
            )

    def test_24_g44_blocks_invalid_telemetry_and_persistent_emmc_write_request(self) -> None:
        for bad_kw in (
            {"target_partition_num": 0},
            {"target_partition_num": True},
            {"target_partition_num": 31},
            {"target_block_device": ""},
            {"spi_nor_ddrtraining_offset": -1},
            {"planned_commands": "nor_loader_writer.sh"},
            {"sd_escape_bypass_latency_us": 0.0},
            {"sd_escape_bypass_latency_us": float("nan")},
            {"p1_kemco_cfg_uart": True},
            {"p1_init_first_line": None},
        ):
            res_bad = verify_cnflasha_spacc_sd_escape_and_p1_p3_guard(**bad_kw)  # type: ignore[arg-type]
            self.assertFalse(res_bad.valid)
            self.assertEqual(res_bad.status, STATUS_BLOCKED_G44_TELEMETRY_INVALID)

        res_emmc = verify_cnflasha_spacc_sd_escape_and_p1_p3_guard(
            request_persistent_emmc_writes=True
        )
        self.assertFalse(res_emmc.valid)
        self.assertEqual(res_emmc.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        self.assertFalse(res_emmc.persistent_emmc_writes_authorized)

    def test_25_g44_accumulates_multiple_violations(self) -> None:
        res = verify_cnflasha_spacc_sd_escape_and_p1_p3_guard(
            tier0_receipt_verified=False,
            target_block_device="/dev/pnflasha15",
            sd_escape_hatch_enabled=False,
            modify_p1_in_transaction=True,
            modify_p3_in_transaction=True,
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            res.violation_codes,
            (
                STATUS_BLOCKED_TIER0_COLD_BACKUP_RECEIPT_INVALID,
                STATUS_BLOCKED_RAW_PNFLASHA_OR_FORBIDDEN_FLASH_TOOL,
                STATUS_BLOCKED_SD_ESCAPE_HATCH_MISSING_OR_SLOW,
                STATUS_BLOCKED_P1_P3_MUTUAL_EXCLUSION_OR_UART_TRAP,
            ),
        )

    # --- 5. Gate G43 & G44 Evaluators + 44-Gate Master Safety Preflight ---

    def test_26_evaluate_g43_and_g44_gate_verdicts_dual_mode(self) -> None:
        v43, r43 = evaluate_g43_jiritsu_service()
        self.assertTrue(v43.passed)
        self.assertTrue(r43.valid)
        self.assertEqual(v43.gate_id, G43_GATE_ID)
        self.assertEqual(v43.gate_code, G43_GATE_CODE)
        self.assertEqual(v43.status, STATUS_VERIFIED_G43)
        self.assertEqual(r43.status, STATUS_VERIFIED_G43)
        self.assertFalse(r43.persistent_emmc_writes_authorized)
        self.assertFalse(r43.persistent_write_release)
        self.assertTrue(v43.details["p6_quota_and_cleanup_safe"])

        v44, r44 = evaluate_g44_cnflasha_dualboot()
        self.assertTrue(v44.passed)
        self.assertTrue(r44.valid)
        self.assertEqual(v44.gate_id, G44_GATE_ID)
        self.assertEqual(v44.gate_code, G44_GATE_CODE)
        self.assertEqual(v44.status, STATUS_VERIFIED_G44)
        self.assertEqual(r44.status, STATUS_VERIFIED_G44)
        self.assertFalse(r44.persistent_emmc_writes_authorized)
        self.assertFalse(r44.persistent_write_release)
        self.assertTrue(v44.details["spacc_boundary_and_flasher_safe"])

    def test_27_44gate_offline_41_of_44_and_dry_run_44_of_44_dual_mode(self) -> None:
        rep_off = evaluate_44gate_preflight(DEFAULT_REPO_ROOT)
        self.assertEqual(rep_off.schema, REALHW_JIRITSU_CNFLASHA_44GATE_SCHEMA)
        self.assertEqual(rep_off.version, REALHW_JIRITSU_CNFLASHA_44GATE_VERSION)
        self.assertEqual(rep_off.summary["total_gates"], 44)
        self.assertEqual(rep_off.summary["verified_gates"], 41)
        self.assertEqual(rep_off.summary["blocked_or_pending_gates"], 3)
        self.assertTrue(rep_off.offline_41_gates_verified)
        self.assertFalse(rep_off.all_44_gates_verified)
        self.assertTrue(rep_off.g13_to_g44_all_passed)
        self.assertTrue(rep_off.g43_to_g44_all_passed)
        self.assertFalse(rep_off.dry_run_rehearsal_only)
        self.assertFalse(rep_off.overall_ready_for_hardware_attach)
        self.assertFalse(rep_off.persistent_emmc_writes_authorized)
        self.assertFalse(rep_off.persistent_write_release)
        self.assertEqual(rep_off.status, "VERIFIED_41_OF_44_AWAITING_PHYSICAL_TIER0")
        for idx in (9, 10, 11):
            self.assertFalse(rep_off.gates[idx]["passed"])
            self.assertEqual(
                rep_off.gates[idx]["status"], STATUS_FAIL_OFFLINE_HARDWARE_NOT_ATTACHED
            )

        rep_dry = evaluate_44gate_preflight(
            DEFAULT_REPO_ROOT, dry_run_simulated_backup=True
        )
        self.assertEqual(rep_dry.summary["verified_gates"], 44)
        self.assertEqual(rep_dry.summary["blocked_or_pending_gates"], 0)
        self.assertTrue(rep_dry.offline_41_gates_verified)
        self.assertTrue(rep_dry.all_44_gates_verified)
        self.assertTrue(rep_dry.dry_run_rehearsal_only)
        self.assertFalse(rep_dry.overall_ready_for_hardware_attach)
        self.assertFalse(rep_dry.persistent_emmc_writes_authorized)
        self.assertFalse(rep_dry.persistent_write_release)
        self.assertEqual(
            rep_dry.status, "VERIFIED_ALL_44_GATES_DRY_RUN_SIMULATED_BACKUP"
        )

    def test_28_44gate_preserves_g01_to_g42_untouched(self) -> None:
        r42 = evaluate_42gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
        )
        r44 = evaluate_44gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
        )
        self.assertEqual(len(r42.gates), 42)
        self.assertEqual(len(r44.gates), 44)
        self.assertEqual(
            [g["gate_id"] for g in r42.gates],
            [g["gate_id"] for g in r44.gates[:42]],
        )
        self.assertEqual(
            [g["status"] for g in r42.gates],
            [g["status"] for g in r44.gates[:42]],
        )

    def test_29_44gate_propagates_g43_failures(self) -> None:
        for kwargs, expected_code in (
            (
                {"np_fz100_soc_pct": 60.0},
                STATUS_BLOCKED_JIRITSU_ELECTRICAL_BROWNOUT_RISK,
            ),
            (
                {"jbusy_file_exists": True},
                STATUS_BLOCKED_JIRITSU_JBUSY_ACTIVE_0X10000011,
            ),
            (
                {"wire_selector": 2, "session_opcodes": ("FORMAT",)},
                STATUS_BLOCKED_JIRITSU_WIRE_FRAMING_OR_FORBIDDEN_OPCODE,
            ),
            (
                {"elf_pt_load_align_bytes": 0x1000},
                STATUS_BLOCKED_JIRITSU_ELF_ALIGNMENT_OR_SELFDELETE,
            ),
            (
                {"peak_p6_bytes": 9 * 1024 * 1024},
                STATUS_BLOCKED_P6_QUOTA_OR_RESIDUAL_EXHAUSTION,
            ),
        ):
            rep = evaluate_44gate_preflight(
                DEFAULT_REPO_ROOT,
                force_clean_room=True,
                dry_run_simulated_backup=True,
                jiritsu_service_kwargs=kwargs,
            )
            self.assertFalse(rep.all_44_gates_verified)
            self.assertFalse(rep.offline_41_gates_verified)
            self.assertFalse(rep.g43_to_g44_all_passed)
            self.assertFalse(rep.gates[42]["passed"])
            self.assertEqual(rep.gates[42]["status"], expected_code)
            self.assertEqual(rep.status, expected_code)

    def test_30_44gate_propagates_g44_failures(self) -> None:
        for kwargs, expected_code in (
            (
                {"tier0_receipt_verified": False},
                STATUS_BLOCKED_TIER0_COLD_BACKUP_RECEIPT_INVALID,
            ),
            (
                {"target_block_device": "/dev/pnflasha15"},
                STATUS_BLOCKED_RAW_PNFLASHA_OR_FORBIDDEN_FLASH_TOOL,
            ),
            (
                {"planned_commands": ("/usr/sbin/nor_loader_writer.sh",)},
                STATUS_BLOCKED_RAW_PNFLASHA_OR_FORBIDDEN_FLASH_TOOL,
            ),
            (
                {"sd_escape_hatch_enabled": False},
                STATUS_BLOCKED_SD_ESCAPE_HATCH_MISSING_OR_SLOW,
            ),
            (
                {"modify_p1_in_transaction": True, "modify_p3_in_transaction": True},
                STATUS_BLOCKED_P1_P3_MUTUAL_EXCLUSION_OR_UART_TRAP,
            ),
        ):
            rep = evaluate_44gate_preflight(
                DEFAULT_REPO_ROOT,
                force_clean_room=True,
                dry_run_simulated_backup=True,
                cnflasha_dualboot_kwargs=kwargs,
            )
            self.assertFalse(rep.all_44_gates_verified)
            self.assertFalse(rep.offline_41_gates_verified)
            self.assertFalse(rep.g43_to_g44_all_passed)
            self.assertFalse(rep.gates[43]["passed"])
            self.assertEqual(rep.gates[43]["status"], expected_code)
            self.assertEqual(rep.status, expected_code)

    def test_31_44gate_propagates_g41_g42_and_emmc_redline(self) -> None:
        rep_g41_g42 = evaluate_44gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            vp_strobe_genlock_kwargs={
                "connected_to_fx3_multiterminal": True,
                "bnc_sync_signal_type": "TRILEVEL_GENLOCK",
            },
            vehiclerig_ibis_kwargs={
                "vibration_rms_g": 1.6,
                "dominant_vibration_hz": 50.0,
                "ibis_steadyshot_mode": "ACTIVE",
            },
        )
        self.assertFalse(rep_g41_g42.all_44_gates_verified)
        self.assertFalse(rep_g41_g42.gates[40]["passed"])
        self.assertFalse(rep_g41_g42.gates[41]["passed"])
        self.assertEqual(
            rep_g41_g42.gates[40]["status"],
            STATUS_BLOCKED_GENLOCK_TRILEVEL_INTO_FX3_LTC_TERMINAL,
        )
        self.assertEqual(
            rep_g41_g42.gates[41]["status"],
            STATUS_BLOCKED_IBIS_ACTIVE_UNDER_SUSTAINED_ENGINE_RESONANCE,
        )
        self.assertEqual(
            rep_g41_g42.status,
            STATUS_BLOCKED_GENLOCK_TRILEVEL_INTO_FX3_LTC_TERMINAL,
        )

        for emmc_kw in (
            {"request_persistent_emmc_writes": True},
            {"jiritsu_service_kwargs": {"request_persistent_emmc_writes": True}},
            {"cnflasha_dualboot_kwargs": {"request_persistent_emmc_writes": True}},
        ):
            rep_emmc = evaluate_44gate_preflight(
                DEFAULT_REPO_ROOT,
                force_clean_room=True,
                dry_run_simulated_backup=True,
                **emmc_kw,
            )
            self.assertFalse(rep_emmc.all_44_gates_verified)
            self.assertFalse(rep_emmc.offline_41_gates_verified)
            self.assertFalse(rep_emmc.overall_ready_for_hardware_attach)
            self.assertFalse(rep_emmc.persistent_emmc_writes_authorized)
            self.assertEqual(rep_emmc.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)

    def test_32_donor_corruption_propagates_to_g43_g44_and_44gate_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            for _key, (_body, rel_path, _sz, _sha, _toks, _lbl) in PINNED_PHASE142_DONOR_SPECS.items():
                dst = tmp / rel_path
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_bytes(b"corrupted")
            v43, r43 = evaluate_g43_jiritsu_service(
                work_root=tmp, force_clean_room=False
            )
            v44, r44 = evaluate_g44_cnflasha_dualboot(
                work_root=tmp, force_clean_room=False
            )
            rep = evaluate_44gate_preflight(
                DEFAULT_REPO_ROOT,
                work_root=tmp,
                force_clean_room=False,
                dry_run_simulated_backup=True,
            )
        self.assertFalse(v43.passed)
        self.assertFalse(r43.valid)
        self.assertEqual(v43.status, STATUS_BLOCKED_DONOR_INTEGRITY)
        self.assertFalse(v44.passed)
        self.assertFalse(r44.valid)
        self.assertEqual(v44.status, STATUS_BLOCKED_DONOR_INTEGRITY)
        self.assertFalse(rep.all_44_gates_verified)
        self.assertFalse(rep.gates[42]["passed"])
        self.assertFalse(rep.gates[43]["passed"])

    def test_33_h0_h1_trial_entry_allowed_and_g13_to_g44_flags(self) -> None:
        rep_off = evaluate_44gate_preflight(DEFAULT_REPO_ROOT, force_clean_room=True)
        self.assertTrue(rep_off.h0_h1_trial_entry_allowed)
        self.assertTrue(rep_off.g13_to_g44_all_passed)
        self.assertTrue(rep_off.g43_to_g44_all_passed)
        self.assertFalse(rep_off.overall_ready_for_hardware_attach)

        rep_bad = evaluate_44gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            cnflasha_dualboot_kwargs={"target_block_device": "/dev/pnflasha15"},
        )
        self.assertFalse(rep_bad.h0_h1_trial_entry_allowed)
        self.assertFalse(rep_bad.g13_to_g44_all_passed)
        self.assertFalse(rep_bad.offline_41_gates_verified)

    def test_34_serialized_json_contains_zero_raw_bytes_repr(self) -> None:
        rep = evaluate_44gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
        )
        rendered = json.dumps(rep.to_dict(), ensure_ascii=False)
        self.assertNotRegex(rendered, r'(?<![0-9A-Za-z_/.-])b[\x27"]')

    # --- 6. CLI & Integration Tests ---

    def test_35_cli_verify_g43_jiritsu_service_summary_and_json(self) -> None:
        buf_sum = io.StringIO()
        with contextlib.redirect_stdout(buf_sum):
            rc_sum = package_cli_main(["verify-g43-jiritsu-service", "--clean-room"])
        self.assertEqual(rc_sum, 0)
        out = buf_sum.getvalue()
        self.assertIn(f"gate={G43_GATE_ID}", out)
        self.assertIn("persistent_emmc_writes_authorized=False", out)

        buf_json = io.StringIO()
        with contextlib.redirect_stdout(buf_json):
            rc_json = package_cli_main(
                ["verify-g43-jiritsu-service", "--clean-room", "--json"]
            )
        self.assertEqual(rc_json, 0)
        payload = json.loads(buf_json.getvalue())
        self.assertTrue(payload["valid"])
        self.assertEqual(payload["status"], STATUS_VERIFIED_G43)
        self.assertFalse(payload["persistent_emmc_writes_authorized"])

    def test_36_cli_verify_g44_cnflasha_dualboot_summary_and_json(self) -> None:
        buf_sum = io.StringIO()
        with contextlib.redirect_stdout(buf_sum):
            rc_sum = package_cli_main(["verify-g44-cnflasha-dualboot", "--clean-room"])
        self.assertEqual(rc_sum, 0)
        out = buf_sum.getvalue()
        self.assertIn(f"gate={G44_GATE_ID}", out)
        self.assertIn("dev=/dev/cnflasha15", out)
        self.assertIn("persistent_emmc_writes_authorized=False", out)

        buf_json = io.StringIO()
        with contextlib.redirect_stdout(buf_json):
            rc_json = package_cli_main(
                ["verify-g44-cnflasha-dualboot", "--clean-room", "--json"]
            )
        self.assertEqual(rc_json, 0)
        payload = json.loads(buf_json.getvalue())
        self.assertTrue(payload["valid"])
        self.assertEqual(payload["status"], STATUS_VERIFIED_G44)
        self.assertFalse(payload["persistent_emmc_writes_authorized"])

    def test_37_cli_verify_44_gates_offline_and_dry_run_json(self) -> None:
        buf_off = io.StringIO()
        with contextlib.redirect_stdout(buf_off):
            rc_off = package_cli_main(["verify-44-gates", "--clean-room", "--json"])
        self.assertEqual(rc_off, 0)
        p_off = json.loads(buf_off.getvalue())
        self.assertEqual(p_off["schema"], REALHW_JIRITSU_CNFLASHA_44GATE_SCHEMA)
        self.assertEqual(p_off["summary"]["verified_gates"], 41)
        self.assertFalse(p_off["dry_run_rehearsal_only"])
        self.assertFalse(p_off["overall_ready_for_hardware_attach"])
        self.assertFalse(p_off["persistent_emmc_writes_authorized"])

        buf_dry = io.StringIO()
        with contextlib.redirect_stdout(buf_dry):
            rc_dry = package_cli_main(
                ["verify-44-gates", "--clean-room", "--dry-run-simulated-backup", "--json"]
            )
        self.assertEqual(rc_dry, 0)
        p_dry = json.loads(buf_dry.getvalue())
        self.assertEqual(p_dry["summary"]["verified_gates"], 44)
        self.assertTrue(p_dry["all_44_gates_verified"])
        self.assertTrue(p_dry["dry_run_rehearsal_only"])
        self.assertFalse(p_dry["overall_ready_for_hardware_attach"])
        self.assertFalse(p_dry["persistent_emmc_writes_authorized"])

    def test_38_cli_verify_44_gates_summary_and_failure_exit_code(self) -> None:
        buf_mod = io.StringIO()
        with contextlib.redirect_stdout(buf_mod):
            rc_mod = module_cli_main(["--clean-room"])
        self.assertEqual(rc_mod, 0)
        out = buf_mod.getvalue()
        self.assertIn("verified=41/44", out)
        self.assertIn("overall_ready_for_hardware_attach=False", out)
        self.assertIn("persistent_emmc_writes_authorized=False", out)

        buf_pkg = io.StringIO()
        with contextlib.redirect_stdout(buf_pkg):
            rc_pkg = package_cli_main(["verify-44-gates", "--clean-room"])
        self.assertEqual(rc_pkg, 0)
        self.assertIn("verified=41/44", buf_pkg.getvalue())

        with tempfile.TemporaryDirectory() as empty_dir:
            buf_fail = io.StringIO()
            with contextlib.redirect_stdout(buf_fail):
                rc_fail = package_cli_main(
                    ["verify-44-gates", "--repo-root", empty_dir, "--clean-room"]
                )
            self.assertEqual(rc_fail, 1)

    def test_39_module_cli_json_dry_run_output(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = module_cli_main(
                ["--clean-room", "--dry-run-simulated-backup", "--json"]
            )
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["schema"], REALHW_JIRITSU_CNFLASHA_44GATE_SCHEMA)
        self.assertTrue(payload["all_44_gates_verified"])
        self.assertFalse(payload["persistent_emmc_writes_authorized"])

    def test_40_env_force_clean_room_honored_end_to_end(self) -> None:
        with patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            rep = evaluate_44gate_preflight(DEFAULT_REPO_ROOT)
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(rep.clean_room_forced)
        self.assertTrue(rep.offline_41_gates_verified)
        self.assertFalse(rep.persistent_emmc_writes_authorized)

    def test_41_evaluate_44_master_safety_gates_alias_and_default_mode(self) -> None:
        self.assertIs(evaluate_44_master_safety_gates, evaluate_44gate_preflight)
        rep = evaluate_44_master_safety_gates(
            DEFAULT_REPO_ROOT, dry_run_simulated_backup=True
        )
        self.assertTrue(rep.all_44_gates_verified)
        self.assertEqual(rep.summary["verified_gates"], 44)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.persistent_write_release)

    def test_42_prior_cli_subcommands_verify_16_through_42_remain_intact(self) -> None:
        for subcmd in (
            "verify-16-gates",
            "verify-18-gates",
            "verify-20-gates",
            "verify-22-gates",
            "verify-24-gates",
            "verify-26-gates",
            "verify-28-gates",
            "verify-30-gates",
            "verify-32-gates",
            "verify-34-gates",
            "verify-36-gates",
            "verify-38-gates",
            "verify-40-gates",
            "verify-42-gates",
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = package_cli_main([subcmd, "--clean-room", "--json"])
            self.assertEqual(rc, 0, f"{subcmd} failed with rc={rc}")
            payload = json.loads(buf.getvalue())
            self.assertFalse(payload["persistent_emmc_writes_authorized"])

    def test_43_g43_g44_gate_ids_and_report_to_dict_keys(self) -> None:
        rep = evaluate_44gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
        )
        self.assertEqual(rep.gates[42]["gate_id"], G43_GATE_ID)
        self.assertEqual(rep.gates[42]["gate_code"], G43_GATE_CODE)
        self.assertEqual(rep.gates[43]["gate_id"], G44_GATE_ID)
        self.assertEqual(rep.gates[43]["gate_code"], G44_GATE_CODE)
        d = rep.to_dict()
        for key in (
            "schema",
            "version",
            "verification_mode",
            "offline_41_gates_verified",
            "all_44_gates_verified",
            "g13_to_g44_all_passed",
            "g43_to_g44_all_passed",
            "overall_ready_for_hardware_attach",
            "persistent_emmc_writes_authorized",
            "persistent_write_release",
            "summary",
            "gates",
            "master_42_report",
            "g43_result",
            "g44_result",
        ):
            self.assertIn(key, d)

    def test_44_g44_spacc_partition_device_mismatch_blocked(self) -> None:
        res_mismatch = verify_cnflasha_spacc_sd_escape_and_p1_p3_guard(
            target_partition_num=15,
            target_block_device="/dev/cnflasha30",
        )
        self.assertFalse(res_mismatch.valid)
        self.assertEqual(
            res_mismatch.status, STATUS_BLOCKED_RAW_PNFLASHA_OR_FORBIDDEN_FLASH_TOOL
        )
        self.assertFalse(res_mismatch.spacc_boundary_and_flasher_safe)


if __name__ == "__main__":
    unittest.main()
