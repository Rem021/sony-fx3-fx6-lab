"""Fast dual-mode unit tests for Phase 148 — Real-Hardware Main Track Part 10:
Gate G45 (`054C:0DA1 -> 054C:0336` `SERVICE` Session `op=0xFF` RAM Canary,
Single-Flight `SenserPacket`, `64 KiB` ELF Self-Unlink + `528B` `FX3S0OK` &
Deterministic `MSC` Return Watchdog Guard), Gate G46 (Stage-B `p18:/lens`
`MS_RDONLY` Lock, 5-Axis IBIS Safe Coil Park & Stock `66,796B` `DmmCfg.bin`
20-Pool Guard), and Unified 46-Gate Master Safety Preflight (`G01..G46` /
`verify-46-gates`).
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
from fx3_safety.monsoon_mishoe_cagetwist_and_40gate_guard import (
    evaluate_40gate_preflight,
)
from fx3_safety.realhw_jiritsu_cnflasha_and_44gate_guard import (
    REALHW_JIRITSU_CNFLASHA_44GATE_SCHEMA,
    STATUS_BLOCKED_JIRITSU_JBUSY_ACTIVE_0X10000011,
    STATUS_BLOCKED_RAW_PNFLASHA_OR_FORBIDDEN_FLASH_TOOL,
    evaluate_44gate_preflight,
)
from fx3_safety.realhw_service0336_mpr_ibis_and_46gate_guard import (
    CANONICAL_TEARDOWN_STEPS,
    FORBIDDEN_FX6_UNMASKED_DMM_POOLS,
    FX3S0OK_HEADER_MAGIC,
    FX3S0OK_PACKET_BYTES,
    FX3S0OK_PAYLOAD_LEN_BYTES,
    G45_GATE_CODE,
    G45_GATE_ID,
    G46_GATE_CODE,
    G46_GATE_ID,
    IBIS_CENTER_LOCK_ACK_OPCODE,
    IBIS_CENTER_LOCK_CMD_OPCODE,
    IBIS_SAFE_COIL_CURRENT_LIMIT_MA,
    IBIS_SAFE_STAGEB_SERVO_STATES,
    LIBJIT_REQUIRED_PT_LOAD_ALIGN,
    MAX_CONCURRENT_INFLIGHT_PACKETS,
    MSC_RETURN_WATCHDOG_MAX_MS,
    OP_FF_CANARY_OPCODE,
    OP_FF_MAX_SIZE_BYTES,
    OP_FF_MAX_SLOT,
    OP_FS_JIRITSU_OPCODE,
    P18_DEVICE_NODE,
    P18_LENSFILE_EXPECTED_BYTES,
    P18_LENSFILE_PATH,
    P18_MOUNT_POINT,
    P18_REQUIRED_MOUNT_FLAG,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PINNED_PHASE148_DONOR_SPECS,
    REALHW_SERVICE0336_MPR_IBIS_46GATE_SCHEMA,
    REALHW_SERVICE0336_MPR_IBIS_46GATE_VERSION,
    SENSER_PACKET_CATEGORY_JIRITSU,
    SENSER_PACKET_PFUNC_ADJUST_CONTROL,
    SERVICE_USB_VID_PID_MSC,
    SERVICE_USB_VID_PID_SERVICE,
    STATUS_BLOCKED_DONOR_INTEGRITY,
    STATUS_BLOCKED_G45_ELF_64K_UNLINK_OR_FX3S0OK_INVALID,
    STATUS_BLOCKED_G45_MSC_RETURN_WATCHDOG_STRANDED_0336,
    STATUS_BLOCKED_G45_OP_FF_CANARY_MISSING_OR_UNSAFE,
    STATUS_BLOCKED_G45_SENSER_PACKET_CONCURRENT_INFLIGHT,
    STATUS_BLOCKED_G45_TELEMETRY_INVALID,
    STATUS_BLOCKED_G46_DMMCFG_POOL_OVERFLOW_OR_SDI_BLOCKING,
    STATUS_BLOCKED_G46_IBIS_FLOATING_COIL_OR_CURRENT_HAZARD,
    STATUS_BLOCKED_G46_P18_LENS_RO_OR_MUTATION,
    STATUS_BLOCKED_G46_TELEMETRY_INVALID,
    STATUS_BLOCKED_PERSISTENT_EMMC_WRITE,
    STATUS_SAFE,
    STATUS_VERIFIED_G45,
    STATUS_VERIFIED_G46,
    STATUS_VERIFIED_SAFE,
    STOCK_FX3_AP_DMMCFG_BYTES,
    STOCK_FX3_AP_DMMCFG_STAMP,
    STOCK_FX3_SHARED_MAIN_POOLS,
    audit_phase148_donor_contracts,
    compute_dmm_pool_utilization_pct,
    evaluate_46_master_safety_gates,
    evaluate_46gate_preflight,
    evaluate_g45_service_0336_canary,
    evaluate_g46_mpr_ibis_p18_guard,
    main as module_cli_main,
    validate_fx3s0ok_packet_header,
    validate_ibis_coil_park_state,
    validate_op_ff_ram_canary,
    verify_service0336_canary_64k_unlink_and_msc_return,
    verify_stageb_p18_ibis_park_and_dmmcfg_guard,
)
from fx3_safety.rig_groundloop_lensrail_and_20gate_guard import (
    STATUS_FAIL_OFFLINE_HARDWARE_NOT_ATTACHED,
)


class RealHwService0336MprIbisAnd46GateGuardTests(unittest.TestCase):
    # --- 1. Hard Redlines, Package Exports & O_RDONLY Donor Audit ---

    def test_01_hard_locked_redlines_and_package_exports(self) -> None:
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(PERSISTENT_WRITE_RELEASE)
        self.assertEqual(
            REALHW_SERVICE0336_MPR_IBIS_46GATE_SCHEMA,
            "fx3-realhw-service0336-mpr-ibis-46gate-preflight-v1",
        )
        self.assertEqual(REALHW_SERVICE0336_MPR_IBIS_46GATE_VERSION, "1.0.0")
        for sym in (
            "REALHW_SERVICE0336_MPR_IBIS_46GATE_SCHEMA",
            "REALHW_SERVICE0336_MPR_IBIS_46GATE_VERSION",
            "G45_GATE_ID",
            "G45_GATE_CODE",
            "G46_GATE_ID",
            "G46_GATE_CODE",
            "STATUS_VERIFIED_G45",
            "STATUS_VERIFIED_G46",
            "STATUS_BLOCKED_G45_OP_FF_CANARY_MISSING_OR_UNSAFE",
            "STATUS_BLOCKED_G45_SENSER_PACKET_CONCURRENT_INFLIGHT",
            "STATUS_BLOCKED_G45_ELF_64K_UNLINK_OR_FX3S0OK_INVALID",
            "STATUS_BLOCKED_G45_MSC_RETURN_WATCHDOG_STRANDED_0336",
            "STATUS_BLOCKED_G45_TELEMETRY_INVALID",
            "STATUS_BLOCKED_G46_P18_LENS_RO_OR_MUTATION",
            "STATUS_BLOCKED_G46_IBIS_FLOATING_COIL_OR_CURRENT_HAZARD",
            "STATUS_BLOCKED_G46_DMMCFG_POOL_OVERFLOW_OR_SDI_BLOCKING",
            "STATUS_BLOCKED_G46_TELEMETRY_INVALID",
            "PINNED_PHASE148_DONOR_SPECS",
            "Phase148DonorAuditResult",
            "Service0336CanaryGuardResult",
            "StageBMprIbisP18GuardResult",
            "G45Service0336CanaryResult",
            "G46MprIbisP18GuardResult",
            "Master46GateReport",
            "audit_phase148_donor_contracts",
            "validate_op_ff_ram_canary",
            "validate_fx3s0ok_packet_header",
            "validate_ibis_coil_park_state",
            "compute_dmm_pool_utilization_pct",
            "verify_service0336_canary_64k_unlink_and_msc_return",
            "verify_stageb_p18_ibis_park_and_dmmcfg_guard",
            "evaluate_g45_service_0336_canary",
            "evaluate_g46_mpr_ibis_p18_guard",
            "evaluate_46gate_preflight",
            "evaluate_46_master_safety_gates",
            "realhw_service0336_mpr_ibis_and_46gate_guard",
        ):
            self.assertIn(sym, fx3_safety.__all__)
            self.assertTrue(hasattr(fx3_safety, sym))
        # Prior Phase exports must remain completely intact (zero collision)
        self.assertEqual(fx3_safety.FAN_MODE_AUTO1, "AUTO1")
        self.assertEqual(
            fx3_safety.STATUS_BLOCKED_DONOR_INTEGRITY,
            "BLOCKED_USBLAN_PTPIP_DONOR_INTEGRITY_MISMATCH",
        )
        self.assertEqual(
            fx3_safety.REALHW_JIRITSU_CNFLASHA_44GATE_SCHEMA,
            REALHW_JIRITSU_CNFLASHA_44GATE_SCHEMA,
        )

    def test_02_donor_audit_o_rdonly_and_clean_room_fallback(self) -> None:
        observed_flags = []
        orig_open = os.open

        def spy_open(path, flags, *args, **kwargs):
            observed_flags.append((str(path), flags))
            return orig_open(path, flags, *args, **kwargs)

        with patch("os.open", side_effect=spy_open):
            res_default = audit_phase148_donor_contracts()
        self.assertTrue(res_default.valid)
        self.assertEqual(res_default.status, STATUS_VERIFIED_SAFE)
        self.assertEqual(res_default.access_mode, "O_RDONLY")
        self.assertTrue(res_default.service_0336_contracts_verified)
        self.assertTrue(res_default.mpr_dmmcfg_contracts_verified)
        self.assertTrue(res_default.ibis_p18_contracts_verified)
        self.assertEqual(res_default.missing_markers, ())

        if res_default.verification_mode == "LOCAL_DONOR_O_RDONLY":
            self.assertEqual(res_default.files_inspected, 6)
            self.assertGreaterEqual(len(observed_flags), 6)
            for _path, flags in observed_flags:
                self.assertEqual(flags & 3, os.O_RDONLY)
        else:
            self.assertEqual(res_default.files_inspected, 0)

        res_clean = audit_phase148_donor_contracts(force_clean_room=True)
        self.assertTrue(res_clean.valid)
        self.assertEqual(res_clean.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(res_clean.files_inspected, 0)
        self.assertEqual(len(res_clean.sha256_by_artifact), 6)

        with tempfile.TemporaryDirectory() as missing_dir:
            res_missing = audit_phase148_donor_contracts(
                work_root=Path(missing_dir), force_clean_room=False
            )
            self.assertTrue(res_missing.valid)
            self.assertEqual(res_missing.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_03_donor_audit_integrity_mismatch_and_missing_marker_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            for _key, (
                _body,
                rel_path,
                _sz,
                _sha,
                _toks,
                _lbl,
            ) in PINNED_PHASE148_DONOR_SPECS.items():
                dst = tmp / rel_path
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_bytes(b"corrupted-phase148-donor")
            res = audit_phase148_donor_contracts(work_root=tmp, force_clean_room=False)
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_DONOR_INTEGRITY)
        self.assertFalse(res.service_0336_contracts_verified)
        self.assertFalse(res.mpr_dmmcfg_contracts_verified)
        self.assertFalse(res.ibis_p18_contracts_verified)
        self.assertEqual(len(res.missing_markers), 6)

    def test_04_donor_audit_pinned_hashes_and_sizes_match_specs(self) -> None:
        for forced in (False, True):
            res = audit_phase148_donor_contracts(force_clean_room=forced)
            self.assertTrue(res.valid)
            for key, (_body, _rel, exp_sz, exp_sha, _toks, _lbl) in PINNED_PHASE148_DONOR_SPECS.items():
                self.assertEqual(res.bytes_by_artifact[key], exp_sz)
                self.assertEqual(res.sha256_by_artifact[key], exp_sha)
            rendered = json.dumps(res.to_dict(), ensure_ascii=False)
            self.assertNotRegex(rendered, r'(?<![0-9A-Za-z_/.-])b[\x27"]')

    # --- 2. Pure Helper Functions ---

    def test_05_helper_validate_op_ff_ram_canary(self) -> None:
        self.assertTrue(validate_op_ff_ram_canary(0x00, 64, 0, 0))
        self.assertTrue(validate_op_ff_ram_canary(OP_FF_MAX_SLOT, OP_FF_MAX_SIZE_BYTES, 0, 0))
        self.assertFalse(validate_op_ff_ram_canary(OP_FF_MAX_SLOT + 1, 64, 0, 0))
        self.assertFalse(validate_op_ff_ram_canary(0x00, 0, 0, 0))
        self.assertFalse(validate_op_ff_ram_canary(0x00, OP_FF_MAX_SIZE_BYTES + 1, 0, 0))
        self.assertFalse(validate_op_ff_ram_canary(0x00, 64, 1, 0))
        self.assertFalse(validate_op_ff_ram_canary(0x00, 64, 0, 1))
        self.assertFalse(validate_op_ff_ram_canary(-1, 64, 0, 0))
        self.assertFalse(validate_op_ff_ram_canary(True, 64, 0, 0))  # type: ignore[arg-type]

    def test_06_helper_validate_fx3s0ok_packet_header(self) -> None:
        self.assertTrue(validate_fx3s0ok_packet_header(FX3S0OK_PACKET_BYTES, FX3S0OK_HEADER_MAGIC, FX3S0OK_PAYLOAD_LEN_BYTES))
        self.assertTrue(validate_fx3s0ok_packet_header(528, "FX3S0OK\x00", 512))
        self.assertFalse(validate_fx3s0ok_packet_header(512, FX3S0OK_HEADER_MAGIC, 512))
        self.assertFalse(validate_fx3s0ok_packet_header(528, "FX3S0ER", 512))
        self.assertFalse(validate_fx3s0ok_packet_header(528, FX3S0OK_HEADER_MAGIC, 256))
        self.assertFalse(validate_fx3s0ok_packet_header(True, FX3S0OK_HEADER_MAGIC, 512))  # type: ignore[arg-type]

    def test_07_helper_validate_ibis_coil_park_state(self) -> None:
        self.assertTrue(
            validate_ibis_coil_park_state(
                "CENTER_LOCK_PARK", "OFF", "STANDARD", 120.0, IBIS_SAFE_COIL_CURRENT_LIMIT_MA
            )
        )
        self.assertFalse(
            validate_ibis_coil_park_state(
                "ACTIVE", "OFF", "CENTER_LOCK_PARK", 120.0, IBIS_SAFE_COIL_CURRENT_LIMIT_MA
            )
        )
        self.assertFalse(
            validate_ibis_coil_park_state(
                "OFF", "OFF", "OFF", 500.0, IBIS_SAFE_COIL_CURRENT_LIMIT_MA
            )
        )
        self.assertFalse(
            validate_ibis_coil_park_state(
                "OFF", "OFF", "OFF", 120.0, IBIS_SAFE_COIL_CURRENT_LIMIT_MA, floating_coil_fault=True
            )
        )
        self.assertFalse(
            validate_ibis_coil_park_state(
                "OFF", "OFF", "OFF", -1.0, IBIS_SAFE_COIL_CURRENT_LIMIT_MA
            )
        )

    def test_08_helper_compute_dmm_pool_utilization_pct(self) -> None:
        self.assertAlmostEqual(compute_dmm_pool_utilization_pct(16, STOCK_FX3_SHARED_MAIN_POOLS), 80.0)
        self.assertAlmostEqual(compute_dmm_pool_utilization_pct(20, 20), 100.0)
        self.assertEqual(compute_dmm_pool_utilization_pct(0, 20), 0.0)
        with self.assertRaises(ValueError):
            compute_dmm_pool_utilization_pct(-1, 20)
        with self.assertRaises(ValueError):
            compute_dmm_pool_utilization_pct(True, 20)  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            compute_dmm_pool_utilization_pct(10, 0)

    # --- 3. Gate G45 Unit & Fault-Injection Tests ---

    def test_09_g45_default_safe_profile_passes(self) -> None:
        res = verify_service0336_canary_64k_unlink_and_msc_return()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_SAFE)
        self.assertEqual(res.violation_codes, ())
        self.assertEqual(res.usb_initial_vid_pid, SERVICE_USB_VID_PID_MSC)
        self.assertEqual(res.usb_service_vid_pid, SERVICE_USB_VID_PID_SERVICE)
        self.assertEqual(res.usb_reenum_msc_vid_pid, SERVICE_USB_VID_PID_MSC)
        self.assertTrue(res.op_ff_canary_safe)
        self.assertTrue(res.senser_packet_serialization_safe)
        self.assertTrue(res.elf_64k_unlink_and_fx3s0ok_safe)
        self.assertTrue(res.msc_return_watchdog_safe)
        self.assertFalse(res.persistent_emmc_writes_authorized)
        self.assertFalse(res.persistent_write_release)

    def test_10_g45_blocks_op_00_without_prior_op_ff_canary(self) -> None:
        res = verify_service0336_canary_64k_unlink_and_msc_return(
            op_ff_canary_executed_before_op_00=False,
            op_00_frame_queued=True,
        )
        self.assertFalse(res.valid)
        self.assertFalse(res.op_ff_canary_safe)
        self.assertEqual(res.status, STATUS_BLOCKED_G45_OP_FF_CANARY_MISSING_OR_UNSAFE)

    def test_11_g45_blocks_op_ff_echo_unverified_or_wrong_vid_pid(self) -> None:
        for kw in (
            {"op_ff_canary_echo_verified": False},
            {"usb_initial_vid_pid": "054C:0994"},
            {"usb_service_vid_pid": "054C:0DA1"},
        ):
            res = verify_service0336_canary_64k_unlink_and_msc_return(**kw)
            self.assertFalse(res.valid)
            self.assertEqual(res.status, STATUS_BLOCKED_G45_OP_FF_CANARY_MISSING_OR_UNSAFE)

    def test_12_g45_blocks_op_ff_slot_size_mount_dlopen_bounds(self) -> None:
        for kw in (
            {"op_ff_canary_slot": OP_FF_MAX_SLOT + 1},
            {"op_ff_canary_size_bytes": OP_FF_MAX_SIZE_BYTES + 1},
            {"op_ff_canary_size_bytes": 0},
            {"op_ff_sys_mount_calls": 1},
            {"op_ff_dlopen_calls": 1},
        ):
            res = verify_service0336_canary_64k_unlink_and_msc_return(**kw)
            self.assertFalse(res.valid)
            self.assertEqual(res.status, STATUS_BLOCKED_G45_OP_FF_CANARY_MISSING_OR_UNSAFE)

    def test_13_g45_blocks_concurrent_senser_packets_or_non_monotonic_seq(self) -> None:
        for kw in (
            {"concurrent_inflight_packets": 2},
            {"seq_monotonic_strict": False},
            {"inconcurrent_lock_held": False},
            {"senser_packet_pfunc": 0x0041},
            {"senser_packet_category": 0x1002},
        ):
            res = verify_service0336_canary_64k_unlink_and_msc_return(**kw)
            self.assertFalse(res.valid)
            self.assertFalse(res.senser_packet_serialization_safe)
            self.assertEqual(res.status, STATUS_BLOCKED_G45_SENSER_PACKET_CONCURRENT_INFLIGHT)

    def test_14_g45_blocks_misaligned_elf_or_missing_unlinkat_or_residual(self) -> None:
        for kw in (
            {"elf_pt_load_align_bytes": 0x1000},
            {"libjit_entry_unlinkat_executed": False},
            {"libjit_unlink_residual_present": True},
        ):
            res = verify_service0336_canary_64k_unlink_and_msc_return(**kw)
            self.assertFalse(res.valid)
            self.assertFalse(res.elf_64k_unlink_and_fx3s0ok_safe)
            self.assertEqual(res.status, STATUS_BLOCKED_G45_ELF_64K_UNLINK_OR_FX3S0OK_INVALID)

    def test_15_g45_blocks_truncated_fx3s0ok_or_bad_magic_or_crc(self) -> None:
        for kw in (
            {"fx3s0ok_packet_bytes": 512},
            {"fx3s0ok_header_magic": "BAD0000"},
            {"fx3s0ok_payload_len_bytes": 256},
            {"fx3s0ok_non_truncating_read_verified": False},
            {"fx3s0ok_crc32_verified": False},
        ):
            res = verify_service0336_canary_64k_unlink_and_msc_return(**kw)
            self.assertFalse(res.valid)
            self.assertEqual(res.status, STATUS_BLOCKED_G45_ELF_64K_UNLINK_OR_FX3S0OK_INVALID)

    def test_16_g45_blocks_msc_return_watchdog_timeout_or_stranded_0336(self) -> None:
        for kw in (
            {"msc_return_elapsed_ms": 5000.1},
            {"stranded_in_service_0336": True},
            {"usb_reenum_msc_vid_pid": "054C:0336"},
            {"teardown_stop_0336_7_sent": False},
            {"teardown_release_0336_8_done": False},
            {"teardown_0da1_9_driver_released": False},
        ):
            res = verify_service0336_canary_64k_unlink_and_msc_return(**kw)
            self.assertFalse(res.valid)
            self.assertFalse(res.msc_return_watchdog_safe)
            self.assertEqual(res.status, STATUS_BLOCKED_G45_MSC_RETURN_WATCHDOG_STRANDED_0336)

    def test_17_g45_blocks_out_of_order_teardown_steps_and_warns_slow_msc(self) -> None:
        bad_order = verify_service0336_canary_64k_unlink_and_msc_return(
            teardown_steps_order=("RELEASE_0336_8", "STOP_0336_7", "MSC_REENUM_054C_0DA1", "DRIVER_RELEASE_0DA1_9")
        )
        self.assertFalse(bad_order.valid)
        self.assertEqual(bad_order.status, STATUS_BLOCKED_G45_MSC_RETURN_WATCHDOG_STRANDED_0336)

        slow_ok = verify_service0336_canary_64k_unlink_and_msc_return(msc_return_elapsed_ms=3500.0)
        self.assertTrue(slow_ok.valid)
        self.assertGreaterEqual(len(slow_ok.warnings), 1)

    def test_18_g45_blocks_invalid_telemetry_types_and_emmc_write_redline(self) -> None:
        for kw in (
            {"op_ff_canary_slot": True},
            {"msc_return_elapsed_ms": 0.0},
            {"msc_return_elapsed_ms": float("nan")},
            {"teardown_steps_order": "STOP_0336_7"},
        ):
            res = verify_service0336_canary_64k_unlink_and_msc_return(**kw)  # type: ignore[arg-type]
            self.assertFalse(res.valid)
            self.assertIn(STATUS_BLOCKED_G45_TELEMETRY_INVALID, res.violation_codes)

        res_emmc = verify_service0336_canary_64k_unlink_and_msc_return(
            request_persistent_emmc_writes=True
        )
        self.assertFalse(res_emmc.valid)
        self.assertEqual(res_emmc.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        self.assertFalse(res_emmc.persistent_emmc_writes_authorized)

    # --- 4. Gate G46 Unit & Fault-Injection Tests ---

    def test_19_g46_default_safe_profile_passes(self) -> None:
        res = verify_stageb_p18_ibis_park_and_dmmcfg_guard()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_SAFE)
        self.assertEqual(res.violation_codes, ())
        self.assertTrue(res.p18_lens_ro_lock_safe)
        self.assertTrue(res.ibis_5axis_coil_park_safe)
        self.assertTrue(res.dmmcfg_pool_budget_safe)
        self.assertAlmostEqual(res.dmm_pool_utilization_pct, 80.0)
        self.assertFalse(res.persistent_emmc_writes_authorized)
        self.assertFalse(res.persistent_write_release)

    def test_20_g46_blocks_p18_rw_remount_or_write_or_mutation(self) -> None:
        for kw in (
            {"p18_mount_flags": "MS_RDWR"},
            {"p18_mount_flags": "rw,relatime"},
            {"p18_write_attempts_blocked": False},
            {"p18_mutation_bytes": 4},
            {"p18_writes_requested": 1},
            {"p18_device_node": "/dev/nflasha15"},
            {"p18_mount_point": "/tmp/lens"},
            {"p18_lensfile_bytes": 1234},
        ):
            res = verify_stageb_p18_ibis_park_and_dmmcfg_guard(**kw)
            self.assertFalse(res.valid)
            self.assertFalse(res.p18_lens_ro_lock_safe)
            self.assertEqual(res.status, STATUS_BLOCKED_G46_P18_LENS_RO_OR_MUTATION)

    def test_21_g46_blocks_ibis_active_or_floating_coil_across_lifecycle(self) -> None:
        for kw in (
            {"ibis_boot_servo_state": "ACTIVE"},
            {"ibis_sleep_servo_state": "ACTIVE"},
            {"ibis_shutdown_servo_state": "FLOATING"},
            {"ibis_floating_coil_fault": True},
        ):
            res = verify_stageb_p18_ibis_park_and_dmmcfg_guard(**kw)
            self.assertFalse(res.valid)
            self.assertFalse(res.ibis_5axis_coil_park_safe)
            self.assertEqual(res.status, STATUS_BLOCKED_G46_IBIS_FLOATING_COIL_OR_CURRENT_HAZARD)

    def test_22_g46_blocks_ibis_overcurrent_center_lock_mismatch_or_fx6_query(self) -> None:
        for kw in (
            {"coil_current_ma": 460.0},
            {"ibis_center_lock_opcode": 0x0401},
            {"ibis_center_lock_ack": 0x0000},
            {"fx6_rigid_sensor_query_masked": False},
        ):
            res = verify_stageb_p18_ibis_park_and_dmmcfg_guard(**kw)
            self.assertFalse(res.valid)
            self.assertFalse(res.ibis_5axis_coil_park_safe)
            self.assertEqual(res.status, STATUS_BLOCKED_G46_IBIS_FLOATING_COIL_OR_CURRENT_HAZARD)

    def test_23_g46_blocks_dmmcfg_tamper_or_pool_overflow(self) -> None:
        for kw in (
            {"dmmcfg_bytes": 131_072},
            {"dmmcfg_stamp": "for fx6-ilme"},
            {"shared_main_pools_count": 24},
            {"allocated_main_pools": 21},
            {"dmm_pool_overflow_bytes": 4096},
        ):
            res = verify_stageb_p18_ibis_park_and_dmmcfg_guard(**kw)
            self.assertFalse(res.valid)
            self.assertFalse(res.dmmcfg_pool_budget_safe)
            self.assertEqual(res.status, STATUS_BLOCKED_G46_DMMCFG_POOL_OVERFLOW_OR_SDI_BLOCKING)

    def test_24_g46_blocks_fx6_sdi_darwin_unmasked_pools_and_sdi_wait(self) -> None:
        for kw in (
            {"requested_fx6_unmasked_pools": ("12G-SDI",)},
            {"requested_fx6_unmasked_pools": ("SDI-RAW",)},
            {"requested_fx6_unmasked_pools": ("Darwin-ND",)},
            {"sdi_blocking_wait_ms": 12.5},
            {"fx6_sdi_raw_darwin_pools_masked": False},
        ):
            res = verify_stageb_p18_ibis_park_and_dmmcfg_guard(**kw)
            self.assertFalse(res.valid)
            self.assertFalse(res.dmmcfg_pool_budget_safe)
            self.assertEqual(res.status, STATUS_BLOCKED_G46_DMMCFG_POOL_OVERFLOW_OR_SDI_BLOCKING)

    def test_25_g46_high_pool_utilization_warning_within_budget(self) -> None:
        res = verify_stageb_p18_ibis_park_and_dmmcfg_guard(allocated_main_pools=19)
        self.assertTrue(res.valid)
        self.assertAlmostEqual(res.dmm_pool_utilization_pct, 95.0)
        self.assertGreaterEqual(len(res.warnings), 1)

    def test_26_g46_blocks_invalid_telemetry_and_emmc_write_redline(self) -> None:
        for kw in (
            {"p18_mutation_bytes": -1},
            {"coil_current_ma": float("inf")},
            {"shared_main_pools_count": 0},
            {"requested_fx6_unmasked_pools": "12G-SDI"},
        ):
            res = verify_stageb_p18_ibis_park_and_dmmcfg_guard(**kw)  # type: ignore[arg-type]
            self.assertFalse(res.valid)
            self.assertIn(STATUS_BLOCKED_G46_TELEMETRY_INVALID, res.violation_codes)

        res_emmc = verify_stageb_p18_ibis_park_and_dmmcfg_guard(
            request_persistent_emmc_writes=True
        )
        self.assertFalse(res_emmc.valid)
        self.assertEqual(res_emmc.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        self.assertFalse(res_emmc.persistent_emmc_writes_authorized)

    # --- 5. Gate G45/G46 Evaluators & Master 46-Gate Preflight ---

    def test_27_evaluate_g45_and_g46_dual_mode_verdicts(self) -> None:
        for forced in (True, False):
            v45, r45 = evaluate_g45_service_0336_canary(force_clean_room=forced)
            self.assertTrue(v45.passed)
            self.assertTrue(r45.valid)
            self.assertEqual(v45.gate_id, G45_GATE_ID)
            self.assertEqual(v45.gate_code, G45_GATE_CODE)
            self.assertEqual(v45.status, STATUS_VERIFIED_G45)
            self.assertFalse(r45.persistent_emmc_writes_authorized)

            v46, r46 = evaluate_g46_mpr_ibis_p18_guard(force_clean_room=forced)
            self.assertTrue(v46.passed)
            self.assertTrue(r46.valid)
            self.assertEqual(v46.gate_id, G46_GATE_ID)
            self.assertEqual(v46.gate_code, G46_GATE_CODE)
            self.assertEqual(v46.status, STATUS_VERIFIED_G46)
            self.assertFalse(r46.persistent_emmc_writes_authorized)

    def test_28_master_46gate_offline_mode_43_of_46(self) -> None:
        rep = evaluate_46gate_preflight(DEFAULT_REPO_ROOT, force_clean_room=True)
        self.assertEqual(rep.schema, REALHW_SERVICE0336_MPR_IBIS_46GATE_SCHEMA)
        self.assertEqual(rep.version, REALHW_SERVICE0336_MPR_IBIS_46GATE_VERSION)
        self.assertGreaterEqual(len(rep.gates), 46)
        self.assertEqual(rep.summary["total_gates"], 46)
        self.assertEqual(rep.summary["verified_gates"], 43)
        self.assertEqual(rep.summary["blocked_or_pending_gates"], 3)
        self.assertEqual(rep.summary["g01_to_g12_verified"], 9)
        self.assertEqual(rep.summary["g13_to_g44_verified"], 32)
        self.assertEqual(rep.summary["g45_to_g46_verified"], 2)
        self.assertTrue(rep.offline_43_gates_verified)
        self.assertFalse(rep.all_46_gates_verified)
        self.assertFalse(rep.dry_run_rehearsal_only)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.persistent_write_release)
        self.assertEqual(rep.status, "VERIFIED_43_OF_46_AWAITING_PHYSICAL_TIER0")
        for idx in (9, 10, 11):
            self.assertFalse(rep.gates[idx]["passed"])
            self.assertEqual(rep.gates[idx]["status"], STATUS_FAIL_OFFLINE_HARDWARE_NOT_ATTACHED)
        self.assertTrue(rep.gates[44]["passed"])
        self.assertEqual(rep.gates[44]["gate_id"], G45_GATE_ID)
        self.assertTrue(rep.gates[45]["passed"])
        self.assertEqual(rep.gates[45]["gate_id"], G46_GATE_ID)

    def test_29_master_46gate_dry_run_simulated_backup_46_of_46(self) -> None:
        rep = evaluate_46gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
        )
        self.assertGreaterEqual(len(rep.gates), 46)
        self.assertEqual(rep.summary["verified_gates"], 46)
        self.assertEqual(rep.summary["blocked_or_pending_gates"], 0)
        self.assertTrue(rep.offline_43_gates_verified)
        self.assertTrue(rep.all_46_gates_verified)
        self.assertTrue(rep.dry_run_rehearsal_only)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.persistent_write_release)
        self.assertEqual(rep.status, "VERIFIED_ALL_46_GATES_DRY_RUN_SIMULATED_BACKUP")
        for g in rep.gates:
            self.assertTrue(g["passed"], f"Gate {g['gate_id']} failed: {g['status']}")

    def test_30_46gate_propagates_g45_failures(self) -> None:
        for kwargs, expected_code in (
            (
                {"op_ff_canary_executed_before_op_00": False, "op_00_frame_queued": True},
                STATUS_BLOCKED_G45_OP_FF_CANARY_MISSING_OR_UNSAFE,
            ),
            (
                {"concurrent_inflight_packets": 3},
                STATUS_BLOCKED_G45_SENSER_PACKET_CONCURRENT_INFLIGHT,
            ),
            (
                {"elf_pt_load_align_bytes": 0x1000},
                STATUS_BLOCKED_G45_ELF_64K_UNLINK_OR_FX3S0OK_INVALID,
            ),
            (
                {"stranded_in_service_0336": True},
                STATUS_BLOCKED_G45_MSC_RETURN_WATCHDOG_STRANDED_0336,
            ),
        ):
            rep = evaluate_46gate_preflight(
                DEFAULT_REPO_ROOT,
                force_clean_room=True,
                dry_run_simulated_backup=True,
                service_0336_canary_kwargs=kwargs,
            )
            self.assertFalse(rep.all_46_gates_verified)
            self.assertFalse(rep.offline_43_gates_verified)
            self.assertFalse(rep.g45_to_g46_all_passed)
            self.assertFalse(rep.gates[44]["passed"])
            self.assertEqual(rep.gates[44]["status"], expected_code)
            self.assertEqual(rep.status, expected_code)

    def test_31_46gate_propagates_g46_failures(self) -> None:
        for kwargs, expected_code in (
            (
                {"p18_mount_flags": "MS_RDWR"},
                STATUS_BLOCKED_G46_P18_LENS_RO_OR_MUTATION,
            ),
            (
                {"ibis_floating_coil_fault": True},
                STATUS_BLOCKED_G46_IBIS_FLOATING_COIL_OR_CURRENT_HAZARD,
            ),
            (
                {"requested_fx6_unmasked_pools": ("12G-SDI",)},
                STATUS_BLOCKED_G46_DMMCFG_POOL_OVERFLOW_OR_SDI_BLOCKING,
            ),
            (
                {"sdi_blocking_wait_ms": 5.0},
                STATUS_BLOCKED_G46_DMMCFG_POOL_OVERFLOW_OR_SDI_BLOCKING,
            ),
        ):
            rep = evaluate_46gate_preflight(
                DEFAULT_REPO_ROOT,
                force_clean_room=True,
                dry_run_simulated_backup=True,
                stageb_mpr_ibis_p18_kwargs=kwargs,
            )
            self.assertFalse(rep.all_46_gates_verified)
            self.assertFalse(rep.offline_43_gates_verified)
            self.assertFalse(rep.g45_to_g46_all_passed)
            self.assertFalse(rep.gates[45]["passed"])
            self.assertEqual(rep.gates[45]["status"], expected_code)
            self.assertEqual(rep.status, expected_code)

    def test_32_46gate_propagates_g43_g44_and_emmc_redline(self) -> None:
        rep_g43_g44 = evaluate_46gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            jiritsu_service_kwargs={"jbusy_precheck_code": 0x10000011},
            cnflasha_dualboot_kwargs={"target_block_device": "/dev/pnflasha15"},
        )
        self.assertFalse(rep_g43_g44.all_46_gates_verified)
        self.assertFalse(rep_g43_g44.gates[42]["passed"])
        self.assertFalse(rep_g43_g44.gates[43]["passed"])
        self.assertEqual(
            rep_g43_g44.gates[42]["status"],
            STATUS_BLOCKED_JIRITSU_JBUSY_ACTIVE_0X10000011,
        )
        self.assertEqual(
            rep_g43_g44.gates[43]["status"],
            STATUS_BLOCKED_RAW_PNFLASHA_OR_FORBIDDEN_FLASH_TOOL,
        )
        self.assertEqual(rep_g43_g44.status, STATUS_BLOCKED_JIRITSU_JBUSY_ACTIVE_0X10000011)

        for emmc_kw in (
            {"request_persistent_emmc_writes": True},
            {"service_0336_canary_kwargs": {"request_persistent_emmc_writes": True}},
            {"stageb_mpr_ibis_p18_kwargs": {"request_persistent_emmc_writes": True}},
        ):
            rep_emmc = evaluate_46gate_preflight(
                DEFAULT_REPO_ROOT,
                force_clean_room=True,
                dry_run_simulated_backup=True,
                **emmc_kw,
            )
            self.assertFalse(rep_emmc.all_46_gates_verified)
            self.assertFalse(rep_emmc.offline_43_gates_verified)
            self.assertFalse(rep_emmc.overall_ready_for_hardware_attach)
            self.assertFalse(rep_emmc.persistent_emmc_writes_authorized)
            self.assertEqual(rep_emmc.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)

    def test_33_donor_corruption_propagates_to_g45_g46_and_46gate_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            for _key, (
                _body,
                rel_path,
                _sz,
                _sha,
                _toks,
                _lbl,
            ) in PINNED_PHASE148_DONOR_SPECS.items():
                dst = tmp / rel_path
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_bytes(b"corrupted")
            v45, r45 = evaluate_g45_service_0336_canary(
                work_root=tmp, force_clean_room=False
            )
            v46, r46 = evaluate_g46_mpr_ibis_p18_guard(
                work_root=tmp, force_clean_room=False
            )
            rep = evaluate_46gate_preflight(
                DEFAULT_REPO_ROOT,
                work_root=tmp,
                force_clean_room=False,
                dry_run_simulated_backup=True,
            )
        self.assertFalse(v45.passed)
        self.assertFalse(r45.valid)
        self.assertEqual(v45.status, STATUS_BLOCKED_DONOR_INTEGRITY)
        self.assertFalse(v46.passed)
        self.assertFalse(r46.valid)
        self.assertEqual(v46.status, STATUS_BLOCKED_DONOR_INTEGRITY)
        self.assertFalse(rep.all_46_gates_verified)
        self.assertFalse(rep.gates[44]["passed"])
        self.assertFalse(rep.gates[45]["passed"])

    def test_34_h0_h1_trial_entry_allowed_and_g13_to_g46_flags(self) -> None:
        rep_off = evaluate_46gate_preflight(DEFAULT_REPO_ROOT, force_clean_room=True)
        self.assertTrue(rep_off.h0_h1_trial_entry_allowed)
        self.assertTrue(rep_off.g13_to_g46_all_passed)
        self.assertTrue(rep_off.g45_to_g46_all_passed)
        self.assertFalse(rep_off.overall_ready_for_hardware_attach)

        rep_bad = evaluate_46gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            service_0336_canary_kwargs={"stranded_in_service_0336": True},
        )
        self.assertFalse(rep_bad.h0_h1_trial_entry_allowed)
        self.assertFalse(rep_bad.g13_to_g46_all_passed)
        self.assertFalse(rep_bad.offline_43_gates_verified)

    def test_35_serialized_json_contains_zero_raw_bytes_repr(self) -> None:
        for forced in (True, False):
            rep = evaluate_46gate_preflight(
                DEFAULT_REPO_ROOT,
                force_clean_room=forced,
                dry_run_simulated_backup=True,
            )
            rendered = json.dumps(rep.to_dict(), ensure_ascii=False)
            self.assertNotRegex(rendered, r'(?<![0-9A-Za-z_/.-])b[\x27"]')

    # --- 6. CLI & Backward-Compatibility Tests ---

    def test_36_cli_verify_g45_service_0336_canary_summary_and_json(self) -> None:
        buf_sum = io.StringIO()
        with contextlib.redirect_stdout(buf_sum):
            rc_sum = package_cli_main(["verify-g45-service-0336-canary", "--clean-room"])
        self.assertEqual(rc_sum, 0)
        out = buf_sum.getvalue()
        self.assertIn(f"gate={G45_GATE_ID}", out)
        self.assertIn("persistent_emmc_writes_authorized=False", out)

        buf_json = io.StringIO()
        with contextlib.redirect_stdout(buf_json):
            rc_json = package_cli_main(
                ["verify-g45-service-0336-canary", "--clean-room", "--json"]
            )
        self.assertEqual(rc_json, 0)
        payload = json.loads(buf_json.getvalue())
        self.assertTrue(payload["valid"])
        self.assertEqual(payload["status"], STATUS_VERIFIED_G45)
        self.assertFalse(payload["persistent_emmc_writes_authorized"])

    def test_37_cli_verify_g46_mpr_ibis_p18_guard_summary_and_json(self) -> None:
        buf_sum = io.StringIO()
        with contextlib.redirect_stdout(buf_sum):
            rc_sum = package_cli_main(["verify-g46-mpr-ibis-p18-guard", "--clean-room"])
        self.assertEqual(rc_sum, 0)
        out = buf_sum.getvalue()
        self.assertIn(f"gate={G46_GATE_ID}", out)
        self.assertIn("p18_flags=MS_RDONLY", out)
        self.assertIn("dmm_pools=16/20", out)
        self.assertIn("persistent_emmc_writes_authorized=False", out)

        buf_json = io.StringIO()
        with contextlib.redirect_stdout(buf_json):
            rc_json = package_cli_main(
                ["verify-g46-mpr-ibis-p18-guard", "--clean-room", "--json"]
            )
        self.assertEqual(rc_json, 0)
        payload = json.loads(buf_json.getvalue())
        self.assertTrue(payload["valid"])
        self.assertEqual(payload["status"], STATUS_VERIFIED_G46)
        self.assertFalse(payload["persistent_emmc_writes_authorized"])

    def test_38_cli_verify_46_gates_offline_and_dry_run_json(self) -> None:
        buf_off = io.StringIO()
        with contextlib.redirect_stdout(buf_off):
            rc_off = package_cli_main(["verify-46-gates", "--clean-room", "--json"])
        self.assertEqual(rc_off, 0)
        p_off = json.loads(buf_off.getvalue())
        self.assertEqual(p_off["schema"], REALHW_SERVICE0336_MPR_IBIS_46GATE_SCHEMA)
        self.assertEqual(p_off["summary"]["verified_gates"], 43)
        self.assertFalse(p_off["dry_run_rehearsal_only"])
        self.assertFalse(p_off["overall_ready_for_hardware_attach"])
        self.assertFalse(p_off["persistent_emmc_writes_authorized"])

        buf_dry = io.StringIO()
        with contextlib.redirect_stdout(buf_dry):
            rc_dry = package_cli_main(
                ["verify-46-gates", "--clean-room", "--dry-run-simulated-backup", "--json"]
            )
        self.assertEqual(rc_dry, 0)
        p_dry = json.loads(buf_dry.getvalue())
        self.assertEqual(p_dry["summary"]["verified_gates"], 46)
        self.assertTrue(p_dry["all_46_gates_verified"])
        self.assertTrue(p_dry["dry_run_rehearsal_only"])
        self.assertFalse(p_dry["overall_ready_for_hardware_attach"])
        self.assertFalse(p_dry["persistent_emmc_writes_authorized"])

    def test_39_cli_verify_46_gates_summary_and_failure_exit_code(self) -> None:
        buf_mod = io.StringIO()
        with contextlib.redirect_stdout(buf_mod):
            rc_mod = module_cli_main(["--clean-room"])
        self.assertEqual(rc_mod, 0)
        out = buf_mod.getvalue()
        self.assertIn("verified=43/46", out)
        self.assertIn("overall_ready_for_hardware_attach=False", out)
        self.assertIn("persistent_emmc_writes_authorized=False", out)

        buf_pkg = io.StringIO()
        with contextlib.redirect_stdout(buf_pkg):
            rc_pkg = package_cli_main(["verify-46-gates", "--clean-room"])
        self.assertEqual(rc_pkg, 0)
        self.assertIn("verified=43/46", buf_pkg.getvalue())

        with tempfile.TemporaryDirectory() as empty_dir:
            buf_fail = io.StringIO()
            with contextlib.redirect_stdout(buf_fail):
                rc_fail = package_cli_main(
                    ["verify-46-gates", "--repo-root", empty_dir, "--clean-room"]
                )
            self.assertEqual(rc_fail, 1)

    def test_40_module_cli_json_dry_run_output(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = module_cli_main(
                ["--clean-room", "--dry-run-simulated-backup", "--json"]
            )
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["schema"], REALHW_SERVICE0336_MPR_IBIS_46GATE_SCHEMA)
        self.assertTrue(payload["all_46_gates_verified"])
        self.assertFalse(payload["persistent_emmc_writes_authorized"])

    def test_41_env_force_clean_room_honored_end_to_end(self) -> None:
        with patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            rep = evaluate_46gate_preflight(DEFAULT_REPO_ROOT)
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(rep.clean_room_forced)
        self.assertTrue(rep.offline_43_gates_verified)
        self.assertFalse(rep.persistent_emmc_writes_authorized)

    def test_42_evaluate_46_master_safety_gates_alias_and_default_mode(self) -> None:
        self.assertIs(evaluate_46_master_safety_gates, evaluate_46gate_preflight)
        rep = evaluate_46_master_safety_gates(
            DEFAULT_REPO_ROOT, dry_run_simulated_backup=True
        )
        self.assertTrue(rep.all_46_gates_verified)
        self.assertEqual(rep.summary["verified_gates"], 46)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.persistent_write_release)

    def test_43_prior_cli_subcommands_verify_16_through_44_remain_intact(self) -> None:
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
            "verify-44-gates",
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = package_cli_main([subcmd, "--clean-room", "--json"])
            self.assertEqual(rc, 0, f"{subcmd} failed with rc={rc}")

    def test_44_backward_compatibility_40gate_and_44gate_reports_unmodified(self) -> None:
        r40 = evaluate_40gate_preflight(DEFAULT_REPO_ROOT, force_clean_room=True)
        self.assertEqual(len(r40.gates), 40)
        self.assertEqual(r40.summary["verified_gates"], 37)
        self.assertTrue(r40.offline_37_gates_verified)
        self.assertFalse(r40.persistent_emmc_writes_authorized)

        r44 = evaluate_44gate_preflight(DEFAULT_REPO_ROOT, force_clean_room=True)
        self.assertEqual(len(r44.gates), 44)
        self.assertEqual(r44.summary["verified_gates"], 41)
        self.assertTrue(r44.offline_41_gates_verified)
        self.assertFalse(r44.persistent_emmc_writes_authorized)

    def test_45_g45_boundary_values_exact_ceilings(self) -> None:
        ok = verify_service0336_canary_64k_unlink_and_msc_return(
            op_ff_canary_slot=OP_FF_MAX_SLOT,
            op_ff_canary_size_bytes=OP_FF_MAX_SIZE_BYTES,
            concurrent_inflight_packets=MAX_CONCURRENT_INFLIGHT_PACKETS,
            msc_return_elapsed_ms=MSC_RETURN_WATCHDOG_MAX_MS,
        )
        self.assertTrue(ok.valid)
        self.assertGreaterEqual(len(ok.warnings), 1)

        bad_slot = verify_service0336_canary_64k_unlink_and_msc_return(
            op_ff_canary_slot=OP_FF_MAX_SLOT + 1
        )
        self.assertFalse(bad_slot.valid)

        bad_watchdog = verify_service0336_canary_64k_unlink_and_msc_return(
            msc_return_elapsed_ms=MSC_RETURN_WATCHDOG_MAX_MS + 0.1
        )
        self.assertFalse(bad_watchdog.valid)

    def test_46_g46_boundary_values_exact_ceilings(self) -> None:
        ok = verify_stageb_p18_ibis_park_and_dmmcfg_guard(
            p18_mount_flags="MS_RDONLY,MS_NOATIME",
            coil_current_ma=IBIS_SAFE_COIL_CURRENT_LIMIT_MA,
            allocated_main_pools=STOCK_FX3_SHARED_MAIN_POOLS,
            sdi_blocking_wait_ms=0.0,
        )
        self.assertTrue(ok.valid)
        self.assertAlmostEqual(ok.dmm_pool_utilization_pct, 100.0)
        self.assertGreaterEqual(len(ok.warnings), 1)

        bad_coil = verify_stageb_p18_ibis_park_and_dmmcfg_guard(
            coil_current_ma=IBIS_SAFE_COIL_CURRENT_LIMIT_MA + 0.1
        )
        self.assertFalse(bad_coil.valid)

        bad_pools = verify_stageb_p18_ibis_park_and_dmmcfg_guard(
            allocated_main_pools=STOCK_FX3_SHARED_MAIN_POOLS + 1
        )
        self.assertFalse(bad_pools.valid)


if __name__ == "__main__":
    unittest.main()
