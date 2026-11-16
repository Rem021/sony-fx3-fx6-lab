"""Phase 144 Dual-Mode Fast Unit Tests (46 tests, <1.0s):

- Group 0 (01..08): Hard-locked passive/USB/eMMC safety redlines, package exports, O_RDONLY donor inspection & clean-room parity
- Group A (09..24): Stage-285/286 `054C:0DA1 -> 054C:0336` exclusive session, Level 2/3 auth, `read0`, DMM `1->4->16`, `op=0xFF` RAM canary gate & passive `ioreg` XML/text parser
- Group B (25..42): Stage-288 §4 (1..6) hardened ARM64 `libJit.so` ELF64 builder, static disassembly gate, syscall/token firewall & Unicorn ARM64 emulation
- Group C (43..46): CLI `verify-service-usb-libjit`, `--out`, JSON/text hygiene & 18-pillar `verify-all-recovery --with-phase144` backward compatibility
"""

from __future__ import annotations

from contextlib import redirect_stdout
from hashlib import sha256
import io
import json
import os
from pathlib import Path
import re
import shutil
import struct
import sys
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import fx3_recovery
from fx3_recovery import __main__ as fx3_cli
from fx3_recovery.files import resolve_donor_path
from fx3_recovery.realhw_service_usb_session_and_libjit_elf_hardener import (
    ALLOW_BOOT_PARTITION_TARGETING,
    ALLOW_DESTRUCTIVE_FASTBOOT,
    ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS,
    ALLOW_PERSISTENT_JIRITSU_WRITES,
    AT_FDCWD,
    AUTH_TABLE_LEVEL_1,
    AUTH_TABLE_LEVEL_2,
    AUTH_TABLE_LEVEL_3,
    DMM_INLINE_THRESHOLD_BYTES,
    DMM_PHASES,
    ELF_MACHINE_AARCH64,
    ELF_PT_LOAD_PAGE_ALIGN,
    ELF_TYPE_DYN,
    ERR_AUTH_LEVEL1_REJECTED,
    ERR_CONCURRENT_OVERLAPPING_SEQ,
    ERR_LIBJIT_RULE1_NO_UNLINK_FIRST,
    ERR_LIBJIT_RULE2_NO_READ_FIRST_CLOEXEC,
    ERR_LIBJIT_RULE3_NO_528B_FRAME,
    ERR_LIBJIT_RULE4_NO_BLK_FALLBACK_OR_ERR_RECEIPT,
    ERR_LIBJIT_RULE5_ELF_LAYOUT_OR_64K_ALIGN,
    ERR_LIBJIT_RULE6_FIREWALL_VIOLATION,
    ERR_MISSING_TEARDOWN_SEQUENCE,
    ERR_OP00_BLOCKED_WITHOUT_OP_FF,
    ERR_OP_FF_SIZE_OUT_OF_RANGE,
    ERR_OP_FF_SLOT_OUT_OF_RANGE,
    FORBIDDEN_ELF_STRING_TOKENS,
    FX3S0ERR_FRAME_BYTES,
    FX3S0ERR_MAGIC,
    FX3S0OK_FRAME_BYTES,
    FX3S0OK_MAGIC,
    FX3_MSC_PID,
    FX3_MSC_VID_PID,
    LIBJIT_TARGET_PATH,
    LINUX_O_CLOEXEC,
    LINUX_O_RDONLY,
    LINUX_O_RDWR,
    LINUX_O_WRONLY,
    LIVE_USB_IOKIT_TRANSMIT_ENABLED,
    MAX_LIBJIT_ELF_BYTES,
    MAX_OP_FF_MODE,
    MAX_OP_FF_PAYLOAD_BYTES,
    MAX_OP_FF_SLOT,
    NFLASH_FALLBACK_NODE,
    NFLASH_WHOLE_NODE,
    OP_FILESYSTEM_MOUNT,
    OP_RAM_CACHE_SLOT,
    OTP_FUSE_TOUCHES,
    OTP_FUSE_WRITES,
    P144_DONOR_LIBJIRITSU_RELPATH,
    P144_DONOR_LIBJIT_TEST_RELPATH,
    P144_DONOR_LIBSENCORE_RELPATH,
    P144_PINNED_LIBJIRITSU_BYTES,
    P144_PINNED_LIBJIRITSU_SHA256,
    P144_PINNED_LIBJIT_TEST_BYTES,
    P144_PINNED_LIBJIT_TEST_SHA256,
    P144_PINNED_LIBSENCORE_BYTES,
    P144_PINNED_LIBSENCORE_SHA256,
    PASSIVE_TX_BYTES_EMITTED,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PFUNC_ADJUST_CONTROL,
    PFUNC_PRODUCT_INFO,
    PHASE144_SCHEMA,
    PHYSICAL_DEVICE_WRITES,
    PROC_PARTITIONS_PATH,
    PRODUCT_INFO_REQ_BYTES,
    PRODUCT_INFO_RESP_BODY_BYTES,
    READ_ONLY_DONOR_ACCESS,
    REQ_VERSION_ADJUST,
    SECTOR0_BYTES,
    SECTOR0_EXPECTED_P1,
    SECTOR0_EXPECTED_PARTITIONS,
    SECTOR0_MAGIC,
    SECTOR0_VERSION,
    SONY_SERVICE_PID,
    SONY_SERVICE_VID_PID,
    SONY_USB_VID,
    STAGE285_9_STEP_CONTRACT,
    STATUS_VERIFIED_PILLAR_A,
    STATUS_VERIFIED_PILLAR_B,
    STATUS_VERIFIED_SUITE,
    SYS_AARCH64_IOCTL,
    SYS_AARCH64_MOUNT,
    SYS_AARCH64_OPENAT,
    SYS_AARCH64_PWRITE64,
    SYS_AARCH64_UNLINKAT,
    SYS_AARCH64_WRITE,
    USB_TX_PACKETS_EMITTED,
    ServiceSessionStateMachine,
    _build_legacy_unhardened_so_stub,
    _build_malicious_syscall_so,
    build_fx3_sector0_err_receipt,
    build_fx3_sector0_ok_frame,
    build_hardened_libjit_elf64,
    build_op_ff_get_request,
    build_op_ff_set_request,
    build_product_info_read0_request,
    build_synthetic_ioreg_text_snapshot,
    build_synthetic_ioreg_xml_snapshot,
    build_synthetic_sector0_fx3_table,
    check_auth_level_for_category_0x1001,
    emulate_hardened_libjit_in_unicorn,
    inspect_service_usb_and_libjit_donors_readonly,
    parse_fx3_sector0_err_receipt,
    parse_fx3_sector0_ok_frame,
    parse_passive_ioreg_usb_topology,
    parse_product_info_read0_response,
    parse_senser_adjust_response,
    run_pillar_a_service_usb_session_8_scenario_suite,
    run_pillar_b_hardened_libjit_elf_8_scenario_suite,
    run_realhw_service_usb_and_libjit_hardener_suite,
    verify_hardened_libjit_elf64,
)

ROOT = Path(__file__).resolve().parents[3]


class TestRealHwServiceUsbAndLibJitHardener(unittest.TestCase):
    # ------------------------------------------------------------------
    # Group 0: Redlines, Exports, O_RDONLY Donor Inspection & Clean-Room
    # ------------------------------------------------------------------

    def test_01_hard_locked_passive_safety_redlines(self) -> None:
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(PERSISTENT_WRITE_RELEASE)
        self.assertFalse(LIVE_USB_IOKIT_TRANSMIT_ENABLED)
        self.assertFalse(ALLOW_BOOT_PARTITION_TARGETING)
        self.assertFalse(ALLOW_DESTRUCTIVE_FASTBOOT)
        self.assertFalse(ALLOW_PERSISTENT_JIRITSU_WRITES)
        self.assertFalse(ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS)
        self.assertTrue(READ_ONLY_DONOR_ACCESS)
        self.assertEqual(USB_TX_PACKETS_EMITTED, 0)
        self.assertEqual(OTP_FUSE_TOUCHES, 0)
        self.assertEqual(OTP_FUSE_WRITES, 0)
        self.assertEqual(PHYSICAL_DEVICE_WRITES, 0)
        self.assertEqual(PASSIVE_TX_BYTES_EMITTED, 0)

    def test_02_package_exports_and_schema_constants(self) -> None:
        self.assertEqual(PHASE144_SCHEMA, "fx3-realhw-service-usb-session-and-libjit-hardener-v1")
        for sym in (
            "realhw_service_usb_session_and_libjit_elf_hardener",
            "ServiceSessionStateMachine",
            "build_hardened_libjit_elf64",
            "verify_hardened_libjit_elf64",
            "emulate_hardened_libjit_in_unicorn",
            "run_realhw_service_usb_and_libjit_hardener_suite",
            "parse_passive_ioreg_usb_topology",
            "run_adjustcontrol_streaming_backup_suite",
        ):
            self.assertTrue(hasattr(fx3_recovery, sym), f"missing package export: {sym}")
            if sym != "run_adjustcontrol_streaming_backup_suite":
                self.assertIn(sym, fx3_recovery.__all__)

    def test_03_dual_mode_donor_inspection_o_rdonly_and_clean_room_fallback(self) -> None:
        real_open = os.open
        opened_flags: list[tuple[str, int]] = []

        def spy_open(path: str | bytes, flags: int, *args: object, **kwargs: object) -> int:
            opened_flags.append((str(path), flags))
            return real_open(path, flags, *args, **kwargs)

        with mock.patch("os.open", side_effect=spy_open):
            snap_local, legacy_local = inspect_service_usb_and_libjit_donors_readonly(force_clean_room=False)

        self.assertTrue(snap_local.read_only_access)
        self.assertTrue(snap_local.o_rdonly_enforced)
        self.assertEqual(snap_local.libjiritsu_descriptor.byte_length, P144_PINNED_LIBJIRITSU_BYTES)
        self.assertEqual(snap_local.libjiritsu_descriptor.sha256_digest, P144_PINNED_LIBJIRITSU_SHA256)
        self.assertEqual(snap_local.libsencore_descriptor.byte_length, P144_PINNED_LIBSENCORE_BYTES)
        self.assertEqual(snap_local.libsencore_descriptor.sha256_digest, P144_PINNED_LIBSENCORE_SHA256)
        self.assertTrue(snap_local.legacy_libjit_test_prehardening_rejected)

        for path_str, flags in opened_flags:
            self.assertEqual(flags & os.O_ACCMODE, os.O_RDONLY, f"non-O_RDONLY open on {path_str}")

        snap_cr, legacy_cr = inspect_service_usb_and_libjit_donors_readonly(force_clean_room=True)
        self.assertEqual(snap_cr.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertIsNone(legacy_cr)
        self.assertFalse(snap_cr.libjiritsu_descriptor.present)
        self.assertFalse(snap_cr.libsencore_descriptor.present)
        self.assertEqual(snap_cr.libjiritsu_descriptor.sha256_digest, P144_PINNED_LIBJIRITSU_SHA256)
        self.assertTrue(snap_cr.legacy_libjit_test_prehardening_rejected)

        donor_jir = resolve_donor_path(P144_DONOR_LIBJIRITSU_RELPATH)
        if donor_jir is not None and donor_jir.is_file():
            self.assertEqual(snap_local.verification_mode, "LOCAL_DONOR_O_RDONLY")
            self.assertTrue(snap_local.libjiritsu_descriptor.present)
            self.assertEqual(snap_local.libjiritsu_descriptor.pt_load_alignments, (0x10000, 0x10000))
            self.assertEqual(snap_local.libsencore_descriptor.pt_load_alignments, (0x10000, 0x10000))

    def test_04_json_zero_raw_proprietary_firmware_bytes_and_no_nan(self) -> None:
        raw_byte_re = re.compile(r"(?<![0-9A-Za-z_/.-])b['\"]")
        for cr in (False, True):
            rep = run_realhw_service_usb_and_libjit_hardener_suite(force_clean_room=cr)
            serialized = json.dumps(rep.to_dict(), ensure_ascii=False, sort_keys=True, allow_nan=False)
            self.assertIsNone(raw_byte_re.search(serialized), f"raw byte literal leaked in clean_room={cr}")

    def test_05_legacy_libjit_test_so_donor_or_stub_flagged_prehardening(self) -> None:
        donor_test = resolve_donor_path(P144_DONOR_LIBJIT_TEST_RELPATH)
        if donor_test is not None and donor_test.is_file():
            fd = os.open(donor_test, os.O_RDONLY)
            try:
                raw = os.read(fd, 65536)
            finally:
                os.close(fd)
            self.assertEqual(len(raw), P144_PINNED_LIBJIT_TEST_BYTES)
            self.assertEqual(sha256(raw).hexdigest(), P144_PINNED_LIBJIT_TEST_SHA256)
            rep = verify_hardened_libjit_elf64(raw)
        else:
            rep = verify_hardened_libjit_elf64(_build_legacy_unhardened_so_stub())
        self.assertFalse(rep.passed)
        self.assertFalse(rep.rule1_self_unlink_first_ok)
        self.assertFalse(rep.rule2_read_first_cloexec_ok)
        self.assertFalse(rep.rule3_framed_528b_output_ok)
        self.assertFalse(rep.rule4_blk_node_and_fallback_ok)
        self.assertFalse(rep.rule5_64k_pt_load_and_dt_bounds_ok)

    def test_06_clean_room_and_local_donor_suites_both_pass(self) -> None:
        rep_cr = run_realhw_service_usb_and_libjit_hardener_suite(force_clean_room=True)
        rep_auto = run_realhw_service_usb_and_libjit_hardener_suite(force_clean_room=False)
        for rep in (rep_cr, rep_auto):
            self.assertTrue(rep.all_passed)
            self.assertEqual(rep.status, STATUS_VERIFIED_SUITE)
            self.assertEqual(rep.pillar_a_service_usb_8_scenarios.scenarios_passed, 8)
            self.assertEqual(rep.pillar_b_hardened_libjit_8_scenarios.scenarios_passed, 8)
            self.assertFalse(rep.live_usb_iokit_transmit_enabled)
            self.assertFalse(rep.persistent_emmc_writes_authorized)
            self.assertEqual(rep.usb_tx_packets_emitted, 0)

    def test_07_suite_sha256_determinism(self) -> None:
        r1 = run_realhw_service_usb_and_libjit_hardener_suite(force_clean_room=True)
        r2 = run_realhw_service_usb_and_libjit_hardener_suite(force_clean_room=True)
        self.assertEqual(r1.suite_sha256, r2.suite_sha256)
        self.assertEqual(
            r1.pillar_b_hardened_libjit_8_scenarios.hardened_elf_sha256,
            r2.pillar_b_hardened_libjit_8_scenarios.hardened_elf_sha256,
        )

    def test_08_module_never_imports_live_usb_iokit_bindings(self) -> None:
        import ast

        mod_path = ROOT / "outputs" / "fx3-recovery-adapter" / "fx3_recovery" / "realhw_service_usb_session_and_libjit_elf_hardener.py"
        tree = ast.parse(mod_path.read_text(encoding="utf-8"))
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0].lower() for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0].lower())
        for forbidden in ("usb", "usb1", "libusb", "iokit", "objc", "pyobjc", "ctypes"):
            self.assertNotIn(forbidden, imported)

    # ------------------------------------------------------------------
    # Group A: Stage-285/286 SERVICE USB, DMM Phase 1->4->16 & op=0xFF
    # ------------------------------------------------------------------

    def test_09_auth_level_gate_level2_and_level3_admitted_level1_rejected(self) -> None:
        g1 = check_auth_level_for_category_0x1001(AUTH_TABLE_LEVEL_1, 0x4010)
        g2 = check_auth_level_for_category_0x1001(AUTH_TABLE_LEVEL_2, 0x4010)
        g3 = check_auth_level_for_category_0x1001(AUTH_TABLE_LEVEL_3, 0x4013)
        self.assertFalse(g1.admitted)
        self.assertEqual(g1.reason_code, ERR_AUTH_LEVEL1_REJECTED)
        self.assertTrue(g2.admitted)
        self.assertTrue(g3.admitted)

    def test_10_auth_table_bit15_flags_mask_0xe000_eq_0x4000_enforced(self) -> None:
        self.assertTrue(check_auth_level_for_category_0x1001(AUTH_TABLE_LEVEL_2, 0x4001).admitted)
        self.assertFalse(check_auth_level_for_category_0x1001(AUTH_TABLE_LEVEL_3, 0x8001).admitted)
        self.assertFalse(check_auth_level_for_category_0x1001(AUTH_TABLE_LEVEL_3, 0x2000).admitted)

    def test_11_product_info_read0_12b_req_and_12b_hdr_plus_88b_body(self) -> None:
        req = build_product_info_read0_request(seq=5)
        self.assertEqual(len(req), PRODUCT_INFO_REQ_BYTES)
        size, pfunc, seq, ver, flag, resv, res = struct.unpack("<IHHBBBB", req)
        self.assertEqual((size, pfunc, seq, ver, flag, resv, res), (0, PFUNC_PRODUCT_INFO, 5, REQ_VERSION_ADJUST, 0, 0, 0))
        hdr = struct.pack("<IHHBBBB", PRODUCT_INFO_RESP_BODY_BYTES, PFUNC_PRODUCT_INFO, 5, 3, 0, 0, 1)
        body = b"A" * PRODUCT_INFO_RESP_BODY_BYTES
        parsed = parse_product_info_read0_response(hdr, body, expected_seq=5)
        self.assertTrue(parsed.valid)
        self.assertEqual(parsed.version, 3)
        self.assertEqual(parsed.res, 1)
        self.assertEqual(parsed.body_bytes, 88)

    def test_12_product_info_read0_rejects_bad_version_res_seq_or_size(self) -> None:
        body88 = b"B" * 88
        bad_ver = struct.pack("<IHHBBBB", 88, PFUNC_PRODUCT_INFO, 1, 2, 0, 0, 1)
        bad_res = struct.pack("<IHHBBBB", 88, PFUNC_PRODUCT_INFO, 1, 3, 0, 0, 0)
        bad_seq = struct.pack("<IHHBBBB", 88, PFUNC_PRODUCT_INFO, 2, 3, 0, 0, 1)
        self.assertFalse(parse_product_info_read0_response(bad_ver, body88, 1).valid)
        self.assertFalse(parse_product_info_read0_response(bad_res, body88, 1).valid)
        self.assertFalse(parse_product_info_read0_response(bad_seq, body88, 1).valid)
        self.assertFalse(parse_product_info_read0_response(struct.pack("<IHHBBBB", 88, PFUNC_PRODUCT_INFO, 1, 3, 0, 0, 1), b"short", 1).valid)

    def test_13_op_ff_set_and_get_wire_frame_exact_layout(self) -> None:
        payload = b"CANARY_1234"
        set_wf = build_op_ff_set_request(seq=11, slot=0x03, data=payload, mode=0x02)
        size, pfunc, seq, ver, f, r, res = struct.unpack_from("<IHHBBBB", set_wf, 0)
        cat, cmd = struct.unpack_from("<HH", set_wf, 12)
        self.assertEqual(size, 4 + 3 + len(payload))
        self.assertEqual((pfunc, seq, ver, f, r, res), (PFUNC_ADJUST_CONTROL, 11, 2, 0, 0, 0))
        self.assertEqual((cat, cmd), (0x1001, 0x0010))
        self.assertEqual(list(set_wf[16:19]), [OP_RAM_CACHE_SLOT, 0x03, 0x02])
        self.assertEqual(set_wf[19:], payload)

        get_wf = build_op_ff_get_request(seq=12, slot=0x03, mode=0x02)
        g_size, g_pfunc, g_seq, g_ver, *_ = struct.unpack_from("<IHHBBBB", get_wf, 0)
        g_cat, g_cmd = struct.unpack_from("<HH", get_wf, 12)
        self.assertEqual((g_size, g_pfunc, g_seq, g_ver, g_cat, g_cmd), (7, 0x0040, 12, 2, 0x1001, 0x0011))
        self.assertEqual(list(get_wf[16:19]), [OP_RAM_CACHE_SLOT, 0x03, 0x02])

    def test_14_op_ff_inline_and_dmm_paths_execute_phases_1_4_16(self) -> None:
        sm = ServiceSessionStateMachine()
        sm.detect_msc()
        sm.run_msc_handshake()
        sm.seize_service_same_port()
        sm.authenticate_service(auth_level=AUTH_TABLE_LEVEL_2)
        sm.execute_product_info_read0(seq=1)

        inline_payload = b"X" * (DMM_INLINE_THRESHOLD_BYTES - 3)
        ok1, echo1, (t_set1, t_get1) = sm.run_op_ff_ram_canary_roundtrip(
            slot=0, canary_payload=inline_payload, seq_base=10
        )
        self.assertTrue(ok1)
        self.assertEqual(echo1, sha256(inline_payload).hexdigest())
        self.assertTrue(t_set1.inline_path)
        self.assertEqual(t_set1.phases_executed, DMM_PHASES)
        self.assertEqual(t_get1.phases_executed, DMM_PHASES)

        big_payload = b"Y" * (DMM_INLINE_THRESHOLD_BYTES + 256)
        ok2, echo2, (t_set2, _t_get2) = sm.run_op_ff_ram_canary_roundtrip(
            slot=MAX_OP_FF_SLOT, mode=MAX_OP_FF_MODE, canary_payload=big_payload, seq_base=20
        )
        self.assertTrue(ok2)
        self.assertEqual(echo2, sha256(big_payload).hexdigest())
        self.assertFalse(t_set2.inline_path)
        self.assertEqual(t_set2.phases_executed, DMM_PHASES)

    def test_15_op_ff_roundtrip_zero_sys_mount_zero_dlopen_zero_fs(self) -> None:
        sm = ServiceSessionStateMachine()
        sm.detect_msc()
        sm.run_msc_handshake()
        sm.seize_service_same_port()
        sm.authenticate_service(auth_level=AUTH_TABLE_LEVEL_3)
        sm.execute_product_info_read0(seq=1)
        canary = b"RAM_ONLY_CANARY"
        ok, echo, _ = sm.run_op_ff_ram_canary_roundtrip(slot=5, canary_payload=canary, seq_base=30)
        self.assertTrue(ok)
        self.assertEqual(echo, sha256(canary).hexdigest())
        self.assertEqual(sm.sys_mount_calls, 0)
        self.assertEqual(sm.dlopen_calls, 0)
        self.assertFalse(sm.touches_filesystem)

    def test_16_op_ff_slot_gt_0x11_rejected(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            build_op_ff_set_request(seq=1, slot=0x12, data=b"A")
        self.assertIn(ERR_OP_FF_SLOT_OUT_OF_RANGE, str(ctx.exception))
        with self.assertRaises(ValueError):
            build_op_ff_get_request(seq=2, slot=0xFF)

    def test_17_op_ff_mode_gt_0x11_rejected(self) -> None:
        with self.assertRaises(ValueError):
            build_op_ff_set_request(seq=1, slot=0, data=b"A", mode=0x12)
        with self.assertRaises(ValueError):
            build_op_ff_get_request(seq=2, slot=0, mode=0x12)

    def test_18_op_ff_size_zero_and_gt_5mib_rejected(self) -> None:
        wf_max = build_op_ff_set_request(seq=1, slot=0x11, data=b"\x5a" * MAX_OP_FF_PAYLOAD_BYTES)
        self.assertGreater(len(wf_max), MAX_OP_FF_PAYLOAD_BYTES)
        with self.assertRaises(ValueError) as ctx0:
            build_op_ff_set_request(seq=2, slot=0, data=b"")
        self.assertIn(ERR_OP_FF_SIZE_OUT_OF_RANGE, str(ctx0.exception))
        with self.assertRaises(ValueError) as ctx_big:
            build_op_ff_set_request(seq=3, slot=0, data=b"\x00" * (MAX_OP_FF_PAYLOAD_BYTES + 1))
        self.assertIn(ERR_OP_FF_SIZE_OUT_OF_RANGE, str(ctx_big.exception))

    def test_19_op_00_blocked_before_op_ff_ram_canary_succeeds(self) -> None:
        sm = ServiceSessionStateMachine()
        sm.detect_msc()
        sm.run_msc_handshake()
        sm.seize_service_same_port()
        sm.authenticate_service(auth_level=AUTH_TABLE_LEVEL_2)
        sm.execute_product_info_read0(seq=1)
        dec = sm.authorize_op00_command(OP_FILESYSTEM_MOUNT)
        self.assertFalse(dec.authorized)
        self.assertEqual(dec.reason_code, ERR_OP00_BLOCKED_WITHOUT_OP_FF)
        wf0 = struct.pack("<IHHBBBB", 4 + 7, PFUNC_ADJUST_CONTROL, 9, REQ_VERSION_ADJUST, 0, 0, 0) + struct.pack(
            "<HH", 0x1001, 0x0010
        ) + b"\x00\xff\x00test"
        with self.assertRaises(ValueError) as ctx:
            sm.execute_adjust_wire_frame(wf0)
        self.assertIn(ERR_OP00_BLOCKED_WITHOUT_OP_FF, str(ctx.exception))

    def test_20_concurrent_overlapping_seq_in_single_flight_session_rejected(self) -> None:
        sm = ServiceSessionStateMachine()
        sm.detect_msc()
        sm.run_msc_handshake()
        sm.seize_service_same_port()
        sm.authenticate_service(auth_level=AUTH_TABLE_LEVEL_2)
        sm.execute_product_info_read0(seq=1)
        sm.begin_flight(100)
        with self.assertRaises(ValueError) as ctx:
            sm.execute_adjust_wire_frame(build_op_ff_get_request(seq=101, slot=0))
        self.assertIn(ERR_CONCURRENT_OVERLAPPING_SEQ, str(ctx.exception))
        sm.end_flight(100)

    def test_21_same_port_continuity_enforced_between_msc_0da1_and_service_0336(self) -> None:
        sm = ServiceSessionStateMachine(port_node_id=1001, location_id=0x01100000)
        sm.detect_msc(SONY_USB_VID, FX3_MSC_PID)
        sm.run_msc_handshake()
        with self.assertRaises(ValueError):
            sm.seize_service_same_port(vid=SONY_USB_VID, pid=SONY_SERVICE_PID, port_node_id=9999, location_id=0x01100000)
        with self.assertRaises(ValueError):
            sm.seize_service_same_port(vid=SONY_USB_VID, pid=SONY_SERVICE_PID, port_node_id=1001, location_id=0x02200000)

    def test_22_incomplete_teardown_missing_stop_release_or_0da1_9_rejected(self) -> None:
        sm = ServiceSessionStateMachine()
        sm.detect_msc()
        sm.run_msc_handshake()
        sm.seize_service_same_port()
        sm.authenticate_service(auth_level=AUTH_TABLE_LEVEL_2)
        sm.execute_product_info_read0(seq=1)
        sm.run_op_ff_ram_canary_roundtrip(slot=0, canary_payload=b"OK", seq_base=10)
        sm.send_stop_0336_7()
        td_partial = sm.verify_complete_session_teardown()
        self.assertFalse(td_partial.complete)
        self.assertIn(ERR_MISSING_TEARDOWN_SEQUENCE, td_partial.error_codes)
        sm.release_service_0336_8()
        sm.observe_msc_return_and_release_0da1_9()
        td_full = sm.verify_complete_session_teardown()
        self.assertTrue(td_full.complete)
        self.assertEqual(tuple(sm.steps_completed), STAGE285_9_STEP_CONTRACT)

    def test_23_passive_ioreg_xml_and_text_topology_dryrun_parser(self) -> None:
        xml_snap = build_synthetic_ioreg_xml_snapshot(include_msc=True, include_service=True)
        txt_snap = build_synthetic_ioreg_text_snapshot()
        rep_xml = parse_passive_ioreg_usb_topology(xml_snap)
        rep_txt = parse_passive_ioreg_usb_topology(txt_snap)
        self.assertTrue(rep_xml.valid)
        self.assertEqual(rep_xml.snapshot_format, "xml")
        self.assertTrue(rep_xml.msc_0da1_present)
        self.assertTrue(rep_xml.service_0336_present)
        self.assertTrue(rep_xml.same_port_continuity_verified)
        self.assertEqual(rep_xml.usb_tx_packets_emitted, 0)
        self.assertFalse(rep_xml.live_usb_iokit_transmit_enabled)
        self.assertFalse(rep_xml.persistent_emmc_writes_authorized)
        self.assertTrue(rep_txt.valid)
        self.assertEqual(rep_txt.snapshot_format, "text")
        self.assertTrue(rep_txt.msc_0da1_present)
        self.assertEqual(FX3_MSC_VID_PID, "054C:0DA1")
        self.assertEqual(SONY_SERVICE_VID_PID, "054C:0336")

    def test_24_pillar_a_8_scenario_suite_all_pass(self) -> None:
        res = run_pillar_a_service_usb_session_8_scenario_suite()
        self.assertTrue(res.passed)
        self.assertEqual(res.status, STATUS_VERIFIED_PILLAR_A)
        self.assertEqual(res.scenarios_passed, 8)
        self.assertEqual(res.scenarios_total, 8)
        self.assertEqual(res.usb_tx_packets_emitted, 0)

    # ------------------------------------------------------------------
    # Group B: Stage-288 §4 (1..6) Hardened ARM64 libJit.so ELF Gate
    # ------------------------------------------------------------------

    def test_25_hardened_libjit_elf64_under_16kib_aarch64_et_dyn(self) -> None:
        so = build_hardened_libjit_elf64()
        self.assertLess(len(so), MAX_LIBJIT_ELF_BYTES)
        rep = verify_hardened_libjit_elf64(so)
        self.assertTrue(rep.passed, f"hardened verification errors: {rep.errors}")
        self.assertTrue(rep.under_16kib)
        self.assertEqual(rep.e_machine, ELF_MACHINE_AARCH64)
        self.assertEqual(rep.e_type, ELF_TYPE_DYN)

    def test_26_rule1_first_syscall_is_unlinkat_at_fdcwd_libjit_so(self) -> None:
        so = build_hardened_libjit_elf64()
        rep = verify_hardened_libjit_elf64(so)
        self.assertTrue(rep.rule1_self_unlink_first_ok)
        self.assertGreater(len(rep.decoded_syscalls), 0)
        first = rep.decoded_syscalls[0]
        self.assertEqual(first.syscall_num, SYS_AARCH64_UNLINKAT)
        self.assertEqual(first.arg0, AT_FDCWD)
        self.assertEqual(first.arg1_str, LIBJIT_TARGET_PATH)
        self.assertEqual(first.arg2, 0)

        no_unlink = _build_legacy_unhardened_so_stub(dt_out_of_bounds=False)
        rep_no = verify_hardened_libjit_elf64(no_unlink)
        self.assertFalse(rep_no.passed)
        self.assertFalse(rep_no.rule1_self_unlink_first_ok)
        self.assertIn(ERR_LIBJIT_RULE1_NO_UNLINK_FIRST, rep_no.error_codes)

    def test_27_rule2_openat_o_rdonly_cloexec_read512_before_open_out(self) -> None:
        so = build_hardened_libjit_elf64()
        rep = verify_hardened_libjit_elf64(so)
        self.assertTrue(rep.rule2_read_first_cloexec_ok)
        nflasha_opens = [s for s in rep.decoded_syscalls if s.syscall_num == SYS_AARCH64_OPENAT and s.arg1_str == NFLASH_WHOLE_NODE]
        self.assertEqual(len(nflasha_opens), 1)
        self.assertEqual(nflasha_opens[0].arg2, LINUX_O_RDONLY | LINUX_O_CLOEXEC)

        no_cloexec = build_hardened_libjit_elf64(replace_open_flags_with=LINUX_O_RDONLY)
        rep_noc = verify_hardened_libjit_elf64(no_cloexec)
        self.assertFalse(rep_noc.passed)
        self.assertFalse(rep_noc.rule2_read_first_cloexec_ok)
        self.assertIn(ERR_LIBJIT_RULE2_NO_READ_FIRST_CLOEXEC, rep_noc.error_codes)

    def test_28_rule3_528b_fx3s0ok_frame_crc32_and_sector0_8246_30_partitions(self) -> None:
        s0 = build_synthetic_sector0_fx3_table()
        self.assertEqual(len(s0), SECTOR0_BYTES)
        self.assertEqual(s0[0:4], SECTOR0_MAGIC)
        self.assertEqual(s0[4:8], SECTOR0_VERSION)
        frame = build_fx3_sector0_ok_frame(s0)
        self.assertEqual(len(frame), FX3S0OK_FRAME_BYTES)
        self.assertTrue(frame.startswith(FX3S0OK_MAGIC))
        info = parse_fx3_sector0_ok_frame(frame)
        self.assertTrue(info.valid)
        self.assertEqual(info.payload_len, 512)
        self.assertEqual(info.n_partitions, SECTOR0_EXPECTED_PARTITIONS)
        self.assertEqual((info.p1_start_lba, info.p1_size_sectors), SECTOR0_EXPECTED_P1)
        self.assertTrue(verify_hardened_libjit_elf64(build_hardened_libjit_elf64()).rule3_framed_528b_output_ok)

    def test_29_rule3_rejects_bad_magic_crc32_or_partition_count(self) -> None:
        frame = bytearray(build_fx3_sector0_ok_frame(build_synthetic_sector0_fx3_table()))
        bad_magic = b"BADMAGIC" + bytes(frame[8:])
        self.assertFalse(parse_fx3_sector0_ok_frame(bad_magic).valid)
        bad_crc = bytes(frame[:100]) + bytes([frame[100] ^ 0xFF]) + bytes(frame[101:])
        self.assertFalse(parse_fx3_sector0_ok_frame(bad_crc).valid)
        s0_badp = bytearray(build_synthetic_sector0_fx3_table())
        struct.pack_into("<I", s0_badp, 8, 29)
        self.assertFalse(parse_fx3_sector0_ok_frame(build_fx3_sector0_ok_frame(bytes(s0_badp))).valid)

    def test_30_rule4_newfstatat_proc_partitions_nflasha1_and_16b_fx3s0err(self) -> None:
        rep = verify_hardened_libjit_elf64(build_hardened_libjit_elf64())
        self.assertTrue(rep.rule4_blk_node_and_fallback_ok)
        paths = [s.arg1_str for s in rep.decoded_syscalls if s.arg1_str]
        self.assertIn(NFLASH_WHOLE_NODE, paths)
        self.assertIn(PROC_PARTITIONS_PATH, paths)
        self.assertIn(NFLASH_FALLBACK_NODE, paths)

    def test_31_rule4_fx3s0err_receipt_roundtrip_and_corruption_rejected(self) -> None:
        err_bin = build_fx3_sector0_err_receipt(stage=3, errno_val=5)
        self.assertEqual(len(err_bin), FX3S0ERR_FRAME_BYTES)
        self.assertTrue(err_bin.startswith(FX3S0ERR_MAGIC))
        parsed = parse_fx3_sector0_err_receipt(err_bin)
        self.assertTrue(parsed.valid)
        self.assertEqual((parsed.stage, parsed.errno_val), (3, 5))
        self.assertFalse(parse_fx3_sector0_err_receipt(b"SHORT").valid)
        self.assertFalse(parse_fx3_sector0_err_receipt(b"WRONGErr" + err_bin[8:]).valid)

    def test_32_rule5_64k_pt_load_alignment_non_overlapping_rx_rw_no_wx(self) -> None:
        rep = verify_hardened_libjit_elf64(build_hardened_libjit_elf64())
        self.assertTrue(rep.rule5_64k_pt_load_and_dt_bounds_ok)
        self.assertEqual(rep.pt_load_count, 2)
        self.assertEqual(rep.pt_load_alignments, (ELF_PT_LOAD_PAGE_ALIGN, ELF_PT_LOAD_PAGE_ALIGN))
        self.assertFalse(rep.has_wx_segment)
        self.assertFalse(rep.has_overlapping_pt_load)
        self.assertTrue(rep.dt_symtab_in_bounds)
        self.assertTrue(rep.dt_strtab_in_bounds)
        self.assertTrue(rep.dt_hash_in_bounds)
        self.assertTrue(rep.dt_init_in_bounds)

    def test_33_rule5_rejects_4k_alignment_and_wx_segment_and_overlapping_pt_load(self) -> None:
        r4k = verify_hardened_libjit_elf64(build_hardened_libjit_elf64(pt_load_align=0x1000))
        self.assertFalse(r4k.passed)
        self.assertFalse(r4k.rule5_64k_pt_load_and_dt_bounds_ok)
        self.assertIn(ERR_LIBJIT_RULE5_ELF_LAYOUT_OR_64K_ALIGN, r4k.error_codes)

        rwx = verify_hardened_libjit_elf64(build_hardened_libjit_elf64(inject_wx_segment=True))
        self.assertFalse(rwx.passed)
        self.assertTrue(rwx.has_wx_segment)
        self.assertFalse(rwx.rule5_64k_pt_load_and_dt_bounds_ok)

    def test_34_rule5_catches_legacy_out_of_bounds_dt_0x2100(self) -> None:
        oob = _build_legacy_unhardened_so_stub(dt_out_of_bounds=True)
        rep = verify_hardened_libjit_elf64(oob)
        self.assertFalse(rep.passed)
        self.assertFalse(rep.dt_symtab_in_bounds)
        self.assertFalse(rep.dt_strtab_in_bounds)
        self.assertFalse(rep.dt_hash_in_bounds)
        self.assertIn(ERR_LIBJIT_RULE5_ELF_LAYOUT_OR_64K_ALIGN, rep.error_codes)

    def test_35_rule5_rejects_empty_zero_dt_hash(self) -> None:
        so = bytearray(build_hardened_libjit_elf64())
        # Corrupt DT_HASH nbucket/nchain inside the ELF's PT_DYNAMIC hash words (last 16 bytes? locate via DT_HASH)
        e_phoff = struct.unpack_from("<Q", so, 32)[0]
        e_phentsz, e_phnum = struct.unpack_from("<HH", so, 54)
        loads = []
        dyn_off = 0
        for idx in range(e_phnum):
            pt, _pf, po, pva, _pp, pfs, _ms, _al = struct.unpack_from("<IIQQQQQQ", so, e_phoff + idx * e_phentsz)
            if pt == 1:
                loads.append((po, pva, pfs))
            elif pt == 2:
                dyn_off = po
        hash_va = 0
        while True:
            tag, val = struct.unpack_from("<QQ", so, dyn_off)
            if tag == 0:
                break
            if tag == 4:
                hash_va = val
                break
            dyn_off += 16
        for po, pva, pfs in loads:
            if pva <= hash_va < pva + pfs:
                struct.pack_into("<IIII", so, po + (hash_va - pva), 0, 0, 0, 0)
        rep = verify_hardened_libjit_elf64(bytes(so))
        self.assertFalse(rep.passed)
        self.assertFalse(rep.rule5_64k_pt_load_and_dt_bounds_ok)
        self.assertEqual(rep.dt_hash_words, (0, 0, 0, 0))

    def test_36_rule6_firewall_rejects_wronly_rdwr_on_all_protected_nodes(self) -> None:
        for node in ("/dev/nflasha", "/dev/cnflasha3", "/dev/pnflasha1", "/dev/mtd0", "/setting/updater/mode"):
            for fl in (LINUX_O_WRONLY, LINUX_O_RDWR):
                so = _build_malicious_syscall_so(SYS_AARCH64_OPENAT, target_path=node, arg2_val=fl)
                rep = verify_hardened_libjit_elf64(so)
                self.assertFalse(rep.rule6_static_syscall_token_firewall_ok, f"missed {node} flags={fl}")
                self.assertIn(ERR_LIBJIT_RULE6_FIREWALL_VIOLATION, rep.error_codes)

    def test_37_rule6_firewall_rejects_write_pwrite64_ioctl_mount_syscalls(self) -> None:
        for sc in (SYS_AARCH64_WRITE, SYS_AARCH64_PWRITE64, SYS_AARCH64_IOCTL, SYS_AARCH64_MOUNT):
            so = _build_malicious_syscall_so(sc)
            rep = verify_hardened_libjit_elf64(so)
            self.assertFalse(rep.rule6_static_syscall_token_firewall_ok, f"missed syscall {sc}")
            self.assertIn(ERR_LIBJIT_RULE6_FIREWALL_VIOLATION, rep.error_codes)

    def test_38_rule6_firewall_rejects_edisx_uc_mkfs_nor_loader_writer(self) -> None:
        for tok in FORBIDDEN_ELF_STRING_TOKENS:
            rep = verify_hardened_libjit_elf64(build_hardened_libjit_elf64(inject_forbidden_token=tok))
            self.assertFalse(rep.passed)
            self.assertFalse(rep.rule6_static_syscall_token_firewall_ok)
            self.assertIn(f"forbidden_token:{tok}", rep.firewall_violations)
            self.assertIn(ERR_LIBJIT_RULE6_FIREWALL_VIOLATION, rep.error_codes)

    def test_39_unicorn_happy_path_unlinks_first_and_writes_valid_528b_fx3s0ok(self) -> None:
        emu = emulate_hardened_libjit_in_unicorn(build_hardened_libjit_elf64())
        if not emu.unicorn_available:
            self.skipTest("Unicorn unavailable")
        self.assertTrue(emu.executed)
        self.assertTrue(emu.passed)
        self.assertTrue(emu.unlinked_libjit_first)
        self.assertTrue(emu.sector0_file_present)
        self.assertEqual(emu.sector0_file_bytes, FX3S0OK_FRAME_BYTES)
        self.assertTrue(emu.ok_frame_valid)
        self.assertFalse(emu.err_receipt_valid)
        self.assertTrue(emu.syscall_sequence[0].startswith("unlinkat:"))

    def test_40_unicorn_short_read_256b_no_truncation_emits_fx3s0err_eio(self) -> None:
        emu = emulate_hardened_libjit_in_unicorn(build_hardened_libjit_elf64(), short_read_len=256)
        if not emu.unicorn_available:
            self.skipTest("Unicorn unavailable")
        self.assertTrue(emu.executed)
        self.assertTrue(emu.passed)
        self.assertTrue(emu.unlinked_libjit_first)
        self.assertEqual(emu.sector0_file_bytes, FX3S0ERR_FRAME_BYTES)
        self.assertTrue(emu.err_receipt_valid)
        self.assertEqual((emu.err_stage, emu.err_errno), (3, 5))

    def test_41_unicorn_missing_nflasha_probes_proc_partitions_and_nflasha1_emits_fx3s0err(self) -> None:
        emu = emulate_hardened_libjit_in_unicorn(build_hardened_libjit_elf64(), nflasha_present=False)
        if not emu.unicorn_available:
            self.skipTest("Unicorn unavailable")
        self.assertTrue(emu.executed)
        self.assertTrue(emu.passed)
        self.assertTrue(emu.unlinked_libjit_first)
        self.assertTrue(emu.probed_proc_partitions)
        self.assertTrue(emu.probed_nflasha1_fallback)
        self.assertEqual(emu.sector0_file_bytes, FX3S0ERR_FRAME_BYTES)
        self.assertTrue(emu.err_receipt_valid)
        self.assertEqual((emu.err_stage, emu.err_errno), (1, 2))

    def test_42_pillar_b_8_scenario_suite_all_pass(self) -> None:
        res = run_pillar_b_hardened_libjit_elf_8_scenario_suite()
        self.assertTrue(res.passed)
        self.assertEqual(res.status, STATUS_VERIFIED_PILLAR_B)
        self.assertEqual(res.scenarios_passed, 8)
        self.assertEqual(res.scenarios_total, 8)
        self.assertLess(res.hardened_elf_bytes, MAX_LIBJIT_ELF_BYTES)

    # ------------------------------------------------------------------
    # Group C: CLI & 18-Pillar verify-all-recovery Integration
    # ------------------------------------------------------------------

    def test_43_cli_verify_service_usb_libjit_clean_room_json_and_out_dir(self) -> None:
        buf = io.StringIO()
        with (
            mock.patch.object(sys, "argv", ["fx3_recovery", "verify-service-usb-libjit", "--clean-room", "--json"]),
            redirect_stdout(buf),
        ):
            rc = fx3_cli.main()
        self.assertEqual(rc, 0)
        parsed = json.loads(buf.getvalue())
        self.assertTrue(parsed["all_passed"])
        self.assertEqual(parsed["verification_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(parsed["pillar_a_service_usb_8_scenarios"]["scenarios_passed"], 8)
        self.assertEqual(parsed["pillar_b_hardened_libjit_8_scenarios"]["scenarios_passed"], 8)

        scratch_root = ROOT / "work" / "_tests" / "phase144_cli_out"
        if scratch_root.exists():
            shutil.rmtree(scratch_root)
        scratch_root.parent.mkdir(parents=True, exist_ok=True)
        try:
            buf_out = io.StringIO()
            with (
                mock.patch.object(
                    sys,
                    "argv",
                    [
                        "fx3_recovery",
                        "verify-service-usb-libjit",
                        "--clean-room",
                        "--json",
                        "--out",
                        str(scratch_root),
                    ],
                ),
                redirect_stdout(buf_out),
            ):
                rc_out = fx3_cli.main()
            self.assertEqual(rc_out, 0)
            rep_file = scratch_root / "service-usb-libjit-report.json"
            self.assertTrue(rep_file.is_file())
            written = json.loads(rep_file.read_text(encoding="utf-8"))
            self.assertEqual(written["schema"], PHASE144_SCHEMA)
        finally:
            if scratch_root.exists():
                shutil.rmtree(scratch_root)

    def test_44_cli_verify_service_usb_libjit_text_and_nonzero_on_failure(self) -> None:
        buf_txt = io.StringIO()
        with (
            mock.patch.object(sys, "argv", ["fx3_recovery", "verify-service-usb-libjit", "--clean-room"]),
            redirect_stdout(buf_txt),
        ):
            rc_txt = fx3_cli.main()
        self.assertEqual(rc_txt, 0)
        txt = buf_txt.getvalue()
        self.assertIn("status=VERIFIED_SERVICE_USB_SESSION_AND_LIBJIT_ELF_HARDENER", txt)
        self.assertIn("service_usb_scenarios=8/8", txt)
        self.assertIn("hardened_libjit_scenarios=8/8", txt)
        self.assertIn("usb_tx_packets_emitted=0", txt)
        self.assertIn("persistent_emmc_writes_authorized=False", txt)

        rep = run_realhw_service_usb_and_libjit_hardener_suite(force_clean_room=True)
        failing = type(rep)(**{**rep.__dict__, "all_passed": False, "status": "REJECTED_FOR_TEST"})
        buf_fail = io.StringIO()
        with (
            mock.patch.object(fx3_cli, "run_realhw_service_usb_and_libjit_hardener_suite", return_value=failing),
            mock.patch.object(sys, "argv", ["fx3_recovery", "verify-service-usb-libjit", "--clean-room", "--json"]),
            redirect_stdout(buf_fail),
        ):
            rc_fail = fx3_cli.main()
        self.assertEqual(rc_fail, 2)
        self.assertFalse(json.loads(buf_fail.getvalue())["all_passed"])

    def test_45_cli_verify_all_recovery_with_phase144_reaches_at_least_18_pillars(self) -> None:
        argv_18 = [
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
            "--json",
        ]
        buf = io.StringIO()
        with mock.patch.object(sys, "argv", argv_18), redirect_stdout(buf):
            rc = fx3_cli.main()
        self.assertEqual(rc, 0)
        parsed = json.loads(buf.getvalue())
        self.assertTrue(parsed["all_passed"])
        self.assertGreaterEqual(parsed["pillar_count"], 18)
        self.assertEqual(parsed["pillars_passed"], parsed["pillar_count"])
        self.assertIn("phase144_pillar18_service_usb_libjit_hardener", parsed)

        buf_txt = io.StringIO()
        with mock.patch.object(sys, "argv", argv_18[:-1]), redirect_stdout(buf_txt):
            rc_txt = fx3_cli.main()
        self.assertEqual(rc_txt, 0)
        self.assertIn("pillars=18/18", buf_txt.getvalue())

    def test_46_cli_verify_all_recovery_backward_compat_7_and_17(self) -> None:
        buf_def = io.StringIO()
        with (
            mock.patch.object(sys, "argv", ["fx3_recovery", "verify-all-recovery", "--clean-room", "--json"]),
            redirect_stdout(buf_def),
        ):
            rc_def = fx3_cli.main()
        self.assertEqual(rc_def, 0)
        parsed_def = json.loads(buf_def.getvalue())
        self.assertEqual(parsed_def["pillar_count"], 7)
        self.assertNotIn("phase144_pillar18_service_usb_libjit_hardener", parsed_def)

        buf_17 = io.StringIO()
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
                    "--with-phase138",
                    "--with-phase139",
                    "--json",
                ],
            ),
            redirect_stdout(buf_17),
        ):
            rc_17 = fx3_cli.main()
        self.assertEqual(rc_17, 0)
        parsed_17 = json.loads(buf_17.getvalue())
        self.assertEqual(parsed_17["pillar_count"], 17)
        self.assertNotIn("phase144_pillar18_service_usb_libjit_hardener", parsed_17)


if __name__ == "__main__":
    unittest.main()
