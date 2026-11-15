"""Phase 139 Dual-Mode Fast Unit Tests (46 tests, <1.0s):

- Pillar 0: Hard-locked passive/USB/eMMC safety redlines, package exports, O_RDONLY donor inspection & clean-room parity
- Pillar A: Stage-288 `AdjustControl (0x40)` wire frames, selector-2 & MODE/START/FORMAT/MOUNT firewall, `/tmp/jbusy` preflight probe & immediate no-retry abort state machine
- Pillar B: Dual-path cold backup — Path 1 SD ExFAT 16-item stream + `528 B` receipt & Path 2 `p6`-bounded (`<= 4 MiB`) sliding-window `75 MiB` `p3` USB pull with `FX3CHK1\\0` framing
- Pillar C: Stateful `FakeIOKitAdjustControlCamera` (`054C:0336`, `25 MiB` `p6` quota, ELF `DT_HASH (1,1,0,0)` + `PT_LOAD 0x10000`, post-session residual audit, hard-locked passive lock)
- Master & CLI: Determinism, JSON hygiene, `verify-adjustcontrol-backup-client` & 17-pillar `verify-all-recovery`
"""

from __future__ import annotations

from contextlib import redirect_stdout
from dataclasses import replace
from hashlib import sha256
import io
import json
from pathlib import Path
import shutil
import struct
import sys
import unittest
from unittest import mock

import fx3_recovery
from fx3_recovery import __main__ as fx3_cli
from fx3_recovery.files import is_forced_clean_room, resolve_donor_path
from fx3_recovery.realhw_adjustcontrol_streaming_backup_client import (
    ABORT_BAD_FRAME_0X10000201,
    ABORT_BUSY_0X10000011,
    ABORT_DLOPEN_FAIL_0X10000000,
    ABORT_MOUNT_FAIL_0X10000004,
    ABORT_P6_FULL_0X1000000F,
    ABORT_USB_TIMEOUT,
    ADJUSTCONTROL_BACKUP_SCHEMA,
    ADJUSTCONTROL_BACKUP_VERSION,
    ALLOW_BOOT_PARTITION_TARGETING,
    ALLOW_DESTRUCTIVE_FASTBOOT,
    ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS,
    ALLOW_PERSISTENT_JIRITSU_WRITES,
    BLOCKED_FORBIDDEN_JIRITSU_COMMAND,
    BLOCKED_JBUSY_PRESENT_ABORT,
    BLOCKED_LIVE_USB_IOKIT_TRANSMIT_LOCKED,
    BLOCKED_PATH_TRAVERSAL,
    BLOCKED_PERSISTENT_EMMC_WRITES_LOCKED,
    BLOCKED_SELECTOR_2_REJECTED,
    CATEGORY_JIRITSU,
    CHUNK_HEADER_MAGIC,
    CMD_GET_FILE2,
    CMD_JIRITSU_DEBUG,
    CMD_JIRITSU_FIRMUP,
    CMD_JIRITSU_FORMAT,
    CMD_JIRITSU_MODE,
    CMD_JIRITSU_MOUNT,
    CMD_JIRITSU_START,
    CMD_SET_FILE2,
    CMD_SET_FILE_PATH,
    COLD_BACKUP_ITEMS,
    ELF_PT_LOAD_PAGE_ALIGN,
    ERR_CHUNK_HEADER_CORRUPT,
    ERR_ELF_DT_HASH_INVALID,
    ERR_ELF_PT_LOAD_NOT_64K_ALIGNED,
    ERR_SD_RECEIPT_INVALID,
    FORBIDDEN_JIRITSU_COMMANDS,
    FX3_MODEL_ID_STR,
    FX3_REGION_TAG_STR,
    JBUSY_PROBE_PATH,
    LIBJIT_PATH,
    LIVE_USB_IOKIT_TRANSMIT_ENABLED,
    OTP_FUSE_TOUCHES,
    OTP_FUSE_WRITES,
    P3_PARTITION_CAPACITY_BYTES,
    P6_PARTITION_QUOTA_BYTES,
    P15_PARTITION_CAPACITY_BYTES,
    P139_DONOR_FAKE_CAM_RELPATH,
    P139_DONOR_FX3_LIBJIRITSU_RELPATH,
    P139_DONOR_FX3_PARTINF_RELPATH,
    P139_DONOR_FX3_PFORMAT_RELPATH,
    P139_DONOR_STAGE288_SO_RELPATH,
    P139_DONOR_WIRE_PY_RELPATH,
    P139_PINNED_FAKE_CAM_BYTES,
    P139_PINNED_FAKE_CAM_SHA256,
    P139_PINNED_FX3_LIBJIRITSU_BYTES,
    P139_PINNED_FX3_LIBJIRITSU_SHA256,
    P139_PINNED_FX3_PARTINF_BYTES,
    P139_PINNED_FX3_PARTINF_SHA256,
    P139_PINNED_FX3_PFORMAT_BYTES,
    P139_PINNED_FX3_PFORMAT_SHA256,
    P139_PINNED_STAGE288_SO_BYTES,
    P139_PINNED_STAGE288_SO_SHA256,
    P139_PINNED_WIRE_PY_BYTES,
    P139_PINNED_WIRE_PY_SHA256,
    PASSIVE_TX_BYTES_EMITTED,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PFUNC_ADJUST_CONTROL,
    PHYSICAL_DEVICE_WRITES,
    PHYSICAL_USB_BYTES_TRANSMITTED,
    PILLAR_A_SCENARIO_IDS,
    PILLAR_B_SCENARIO_IDS,
    PILLAR_C_SCENARIO_IDS,
    READ_ONLY_DONOR_ACCESS,
    REQUIRED_COLD_BACKUP_ITEM_IDS,
    SD_BACKUP_MANIFEST_NAME,
    SD_BACKUP_MOUNT_DIR,
    SD_RECEIPT_BYTES,
    SD_RECEIPT_MAGIC,
    SLIDING_CHUNK_PATH,
    SLIDING_WINDOW_CHUNK_BYTES,
    SLIDING_WINDOW_MAX_PEAK_P6_BYTES,
    SONY_SERVICE_PID,
    SONY_SERVICE_VID_PID,
    SONY_USB_VID,
    SPI_NOR_DDRTRAINING_OFFSET,
    STATUS_BAD_FRAME,
    STATUS_BUSY,
    STATUS_DLOPEN_FAIL,
    STATUS_FAIL_SUITE,
    STATUS_GET_ABSENT,
    STATUS_MOUNT_FAIL,
    STATUS_OK,
    STATUS_P6_NO_SPACE,
    STATUS_REJECTED_P6_RESIDUAL_FILES,
    STATUS_USB_TIMEOUT,
    STATUS_VERIFIED_PILLAR_A,
    STATUS_VERIFIED_PILLAR_B,
    STATUS_VERIFIED_PILLAR_C,
    STATUS_VERIFIED_SUITE,
    AdjustControlDonorSnapshot,
    AdjustControlSessionClient,
    AdjustControlStreamingBackupSuiteReport,
    FakeIOKitAdjustControlCamera,
    PassiveHardwareLockRequest,
    audit_passive_iokit_and_emmc_lock,
    build_forbidden_command_guard,
    build_sd_backup_receipt_bytes,
    build_synthetic_jiritsu_so_64k,
    execute_p6_sliding_window_usb_pull,
    execute_sd_streaming_cold_backup,
    frame_sliding_chunk,
    get_file2_request,
    inspect_adjustcontrol_donors_readonly,
    parse_adjust_response_header,
    parse_adjust_response_raw,
    parse_sd_backup_receipt_bytes,
    run_adjustcontrol_streaming_backup_suite,
    run_pillar_a_wire_and_preflight_7_scenario_suite,
    run_pillar_b_dual_path_backup_6_scenario_suite,
    run_pillar_c_fake_iokit_regression_5_scenario_suite,
    set_file2_request,
    set_file_path_request,
    validate_elf64_so_for_fx3_64k,
    validate_jiritsu_path,
    verify_and_unframe_sliding_chunk,
)

ROOT = Path(__file__).resolve().parents[3]
RAW_BYTES_RE = r"(?<![0-9A-Za-z_/.-])b[\x27\x22]"


class TestRealHwAdjustControlStreamingBackupClient(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.suite_report = run_adjustcontrol_streaming_backup_suite()
        cls.clean_report = run_adjustcontrol_streaming_backup_suite(force_clean_room=True)
        cls.so_64k = build_synthetic_jiritsu_so_64k()

    # ------------------------------------------------------------------
    # Pillar 0 — Safety Constants, Package Exports & O_RDONLY Donor Inspection
    # ------------------------------------------------------------------

    def test_01_safety_redlines_hard_locked(self) -> None:
        self.assertFalse(LIVE_USB_IOKIT_TRANSMIT_ENABLED)
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(PERSISTENT_WRITE_RELEASE)
        self.assertFalse(ALLOW_BOOT_PARTITION_TARGETING)
        self.assertFalse(ALLOW_DESTRUCTIVE_FASTBOOT)
        self.assertFalse(ALLOW_PERSISTENT_JIRITSU_WRITES)
        self.assertFalse(ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS)
        self.assertTrue(READ_ONLY_DONOR_ACCESS)
        self.assertEqual(OTP_FUSE_TOUCHES, 0)
        self.assertEqual(OTP_FUSE_WRITES, 0)
        self.assertEqual(PASSIVE_TX_BYTES_EMITTED, 0)
        self.assertEqual(PHYSICAL_DEVICE_WRITES, 0)
        self.assertEqual(PHYSICAL_USB_BYTES_TRANSMITTED, 0)

    def test_02_package_level_exports_complete(self) -> None:
        expected = [
            "ADJUSTCONTROL_BACKUP_SCHEMA",
            "LIVE_USB_IOKIT_TRANSMIT_ENABLED",
            "FakeIOKitAdjustControlCamera",
            "AdjustControlSessionClient",
            "inspect_adjustcontrol_donors_readonly",
            "run_pillar_a_wire_and_preflight_7_scenario_suite",
            "run_pillar_b_dual_path_backup_6_scenario_suite",
            "run_pillar_c_fake_iokit_regression_5_scenario_suite",
            "run_adjustcontrol_streaming_backup_suite",
            "execute_sd_streaming_cold_backup",
            "execute_p6_sliding_window_usb_pull",
            "validate_elf64_so_for_fx3_64k",
            "build_synthetic_jiritsu_so_64k",
        ]
        for sym in expected:
            self.assertIn(sym, fx3_recovery.__all__)
            self.assertTrue(hasattr(fx3_recovery, sym), f"Missing export: {sym}")

    def test_03_donor_inspection_dual_mode_and_parity(self) -> None:
        snap_active = inspect_adjustcontrol_donors_readonly()
        snap_clean = inspect_adjustcontrol_donors_readonly(force_clean_room=True)
        self.assertIsInstance(snap_active, AdjustControlDonorSnapshot)
        self.assertTrue(snap_active.read_only_access)
        self.assertEqual(snap_clean.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        if not is_forced_clean_room() and resolve_donor_path(P139_DONOR_WIRE_PY_RELPATH, require_file=True).is_file():
            self.assertEqual(snap_active.verification_mode, "LOCAL_DONOR_O_RDONLY")
        else:
            self.assertEqual(snap_active.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(snap_active.p6_quota_bytes, P6_PARTITION_QUOTA_BYTES)
        self.assertEqual(snap_active.p3_capacity_bytes, P3_PARTITION_CAPACITY_BYTES)
        self.assertEqual(snap_active.p15_capacity_bytes, P15_PARTITION_CAPACITY_BYTES)
        self.assertEqual(snap_active.partinf_partition_count, 30)
        self.assertEqual(snap_active.stage288_so_pt_load_align, 0x1000)
        self.assertEqual(snap_active.fx3_libjiritsu_pt_load_align, ELF_PT_LOAD_PAGE_ALIGN)
        self.assertEqual(
            [a.sha256_digest for a in snap_active.artifacts],
            [a.sha256_digest for a in snap_clean.artifacts],
        )
        self.assertEqual(
            [a.byte_length for a in snap_active.artifacts],
            [a.byte_length for a in snap_clean.artifacts],
        )

    def test_04_pinned_donor_digests_and_absent_fallback(self) -> None:
        pinned = {
            P139_DONOR_WIRE_PY_RELPATH: (P139_PINNED_WIRE_PY_BYTES, P139_PINNED_WIRE_PY_SHA256),
            P139_DONOR_FAKE_CAM_RELPATH: (P139_PINNED_FAKE_CAM_BYTES, P139_PINNED_FAKE_CAM_SHA256),
            P139_DONOR_STAGE288_SO_RELPATH: (P139_PINNED_STAGE288_SO_BYTES, P139_PINNED_STAGE288_SO_SHA256),
            P139_DONOR_FX3_LIBJIRITSU_RELPATH: (P139_PINNED_FX3_LIBJIRITSU_BYTES, P139_PINNED_FX3_LIBJIRITSU_SHA256),
            P139_DONOR_FX3_PARTINF_RELPATH: (P139_PINNED_FX3_PARTINF_BYTES, P139_PINNED_FX3_PARTINF_SHA256),
            P139_DONOR_FX3_PFORMAT_RELPATH: (P139_PINNED_FX3_PFORMAT_BYTES, P139_PINNED_FX3_PFORMAT_SHA256),
        }
        snap = inspect_adjustcontrol_donors_readonly(force_clean_room=True)
        self.assertEqual(len(snap.artifacts), len(pinned))
        for art, (_rel, (sz, digest)) in zip(snap.artifacts, pinned.items()):
            self.assertEqual(art.byte_length, sz)
            self.assertEqual(art.sha256_digest, digest)

        # Simulate missing donor path -> clean-room fallback
        with mock.patch(
            "fx3_recovery.realhw_adjustcontrol_streaming_backup_client._read_donor_readonly",
            return_value=(None, "CLEAN_ROOM_SYNTHETIC"),
        ):
            snap_missing = inspect_adjustcontrol_donors_readonly(force_clean_room=False)
            self.assertEqual(snap_missing.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertEqual([a.sha256_digest for a in snap_missing.artifacts], [a.sha256_digest for a in snap.artifacts])
            self.assertEqual([a.byte_length for a in snap_missing.artifacts], [a.byte_length for a in snap.artifacts])

    def test_05_cold_backup_manifest_covers_stage288_and_report_5_2_items(self) -> None:
        expected_ids = {
            "sector0",
            "p2",
            "p6",
            "p12",
            "p18",
            "spi_nor_ddrtraining",
            "spi_nor_loader",
            "p1",
            "p3",
            "p7",
            "p8",
            "p5",
            "p13",
            "p15",
            "p23",
            "p30",
        }
        self.assertEqual(set(REQUIRED_COLD_BACKUP_ITEM_IDS), expected_ids)
        self.assertEqual(len(COLD_BACKUP_ITEMS), 16)
        by_id = {item.item_id: item for item in COLD_BACKUP_ITEMS}
        self.assertEqual(by_id["sector0"].size_bytes, 512)
        self.assertEqual(by_id["p6"].size_bytes, P6_PARTITION_QUOTA_BYTES)
        self.assertEqual(by_id["p3"].size_bytes, P3_PARTITION_CAPACITY_BYTES)
        self.assertEqual(by_id["p15"].size_bytes, P15_PARTITION_CAPACITY_BYTES)
        self.assertEqual(by_id["spi_nor_ddrtraining"].offset_bytes, SPI_NOR_DDRTRAINING_OFFSET)

    def test_06_pformat_sections_present_in_donor_snapshot(self) -> None:
        snap = self.clean_report.donor_snapshot
        for req_sec in ("loader_nor.bin", "LdrBkup.bin", "cpapp-b.bin"):
            self.assertIn(req_sec, snap.pformat_sections)

    def test_07_master_suite_passes_in_both_modes(self) -> None:
        for rep in (self.suite_report, self.clean_report):
            self.assertTrue(rep.all_passed, f"Master suite failed: {rep.errors}")
            self.assertEqual(rep.status, STATUS_VERIFIED_SUITE)
            self.assertEqual(rep.schema, ADJUSTCONTROL_BACKUP_SCHEMA)
            self.assertEqual(rep.version, ADJUSTCONTROL_BACKUP_VERSION)
            self.assertFalse(rep.live_usb_iokit_transmit_enabled)
            self.assertFalse(rep.persistent_emmc_writes_authorized)
            self.assertEqual(rep.physical_device_writes, 0)
            self.assertEqual(rep.physical_usb_bytes_transmitted, 0)

    # ------------------------------------------------------------------
    # Pillar A — ADJUSTCONTROL_0X40_WIRE_TRANSPORT_AND_PREFLIGHT_ABORT
    # ------------------------------------------------------------------

    def test_08_exact_stage288_wire_frame_encodings(self) -> None:
        w_path = set_file_path_request(1, LIBJIT_PATH).to_wire_bytes()
        size_p, pfunc_p, seq_p, ver_p, flg_p, resv_p, res_p = struct.unpack_from("<IHHBBBB", w_path, 0)
        cat_p, cmd_p = struct.unpack_from("<HH", w_path, 12)
        self.assertEqual((pfunc_p, seq_p, ver_p, flg_p, resv_p, res_p), (PFUNC_ADJUST_CONTROL, 1, 2, 0, 0, 0))
        self.assertEqual((cat_p, cmd_p), (CATEGORY_JIRITSU, CMD_SET_FILE_PATH))
        self.assertEqual(w_path[16:], b"\x00" + LIBJIT_PATH.encode("ascii") + b"\x00")
        self.assertEqual(size_p, len(w_path) - 12)

        payload = b"\x7fELF_TEST_BODY"
        w_set = set_file2_request(2, payload).to_wire_bytes()
        cat_s, cmd_s = struct.unpack_from("<HH", w_set, 12)
        self.assertEqual((cat_s, cmd_s), (CATEGORY_JIRITSU, CMD_SET_FILE2))
        self.assertEqual(w_set[16:19], b"\x00\xff\x00")
        self.assertEqual(w_set[19:], payload)

        w_get = get_file2_request(3).to_wire_bytes()
        cat_g, cmd_g = struct.unpack_from("<HH", w_get, 12)
        self.assertEqual((cat_g, cmd_g), (CATEGORY_JIRITSU, CMD_GET_FILE2))
        self.assertEqual(w_get[16:], b"\x00\xff\x00")
        self.assertEqual(len(w_get), 19)

    def test_09_selector_2_and_zero_rejected_in_set_and_get_file2(self) -> None:
        for bad_sel in (0, 2, 3, 0xFE):
            with self.assertRaises(ValueError) as ctx_s:
                set_file2_request(1, b"abc", selector=bad_sel)
            self.assertIn(BLOCKED_SELECTOR_2_REJECTED, str(ctx_s.exception))

            with self.assertRaises(ValueError) as ctx_g:
                get_file2_request(1, selector=bad_sel)
            self.assertIn(BLOCKED_SELECTOR_2_REJECTED, str(ctx_g.exception))

    def test_10_forbidden_mode_mount_format_start_commands_blocked(self) -> None:
        self.assertEqual(
            FORBIDDEN_JIRITSU_COMMANDS,
            (
                CMD_JIRITSU_MODE,
                CMD_JIRITSU_MOUNT,
                CMD_JIRITSU_FORMAT,
                CMD_JIRITSU_START,
                CMD_JIRITSU_DEBUG,
                CMD_JIRITSU_FIRMUP,
            ),
        )
        for cmd in FORBIDDEN_JIRITSU_COMMANDS:
            env = build_forbidden_command_guard(1, cmd, b"\x01")
            with self.assertRaises(ValueError) as ctx:
                env.to_wire_bytes()
            self.assertIn(BLOCKED_FORBIDDEN_JIRITSU_COMMAND, str(ctx.exception))

    def test_11_forbidden_tool_tokens_and_path_traversal_blocked(self) -> None:
        for tok in ("edisx", "uc_mkfs", "nor_loader_writer"):
            with self.assertRaises(ValueError) as ctx_s:
                set_file2_request(1, f"payload_{tok}".encode("ascii"))
            self.assertIn(BLOCKED_FORBIDDEN_JIRITSU_COMMAND, str(ctx_s.exception))
            with self.assertRaises(ValueError) as ctx_p:
                validate_jiritsu_path(f"/tmp/jiritsu/{tok}.bin")
            self.assertIn(BLOCKED_FORBIDDEN_JIRITSU_COMMAND, str(ctx_p.exception))

        for bad_path in ("/etc/passwd", "/tmp/other/a.bin", "/tmp/jiritsu/../setting/Backup.bin", JBUSY_PROBE_PATH):
            with self.assertRaises(ValueError):
                validate_jiritsu_path(bad_path, allow_jbusy_probe=False)
        self.assertEqual(validate_jiritsu_path(JBUSY_PROBE_PATH, allow_jbusy_probe=True), JBUSY_PROBE_PATH)

    def test_12_response_header_and_raw_parser_preserve_native_status(self) -> None:
        body = struct.pack("<I", STATUS_GET_ABSENT)
        hdr = struct.pack("<IHHBBBB", len(body), PFUNC_ADJUST_CONTROL, 7, 3, 0, 0, 1)
        self.assertEqual(parse_adjust_response_header(hdr, expected_seq=7), 4)
        parsed, payload = parse_adjust_response_raw(hdr + body, expected_seq=7)
        self.assertEqual(parsed.native_status, STATUS_GET_ABSENT)
        self.assertEqual(payload, b"")

        # Sequence mismatch rejected
        with self.assertRaises(ValueError):
            parse_adjust_response_raw(hdr + body, expected_seq=8)

    def test_13_mandatory_jbusy_preflight_blocks_set_file2_when_busy(self) -> None:
        cam = FakeIOKitAdjustControlCamera(jbusy=True)
        client = AdjustControlSessionClient(cam.handle)
        ok = client.probe_jbusy_absent()
        self.assertFalse(ok)
        self.assertTrue(client.jbusy_preflight_checked)
        self.assertFalse(client.jbusy_absent_confirmed)
        self.assertTrue(client.aborted)
        self.assertEqual(client.abort_reason_code, BLOCKED_JBUSY_PRESENT_ABORT)
        self.assertFalse(client.send_file2_once(self.so_64k))
        self.assertEqual(client.set_file2_sent_count, 0)

    def test_14_send_file2_without_preflight_rejected(self) -> None:
        cam = FakeIOKitAdjustControlCamera(jbusy=False)
        client = AdjustControlSessionClient(cam.handle)
        self.assertFalse(client.send_file2_once(self.so_64k))
        self.assertTrue(client.aborted)
        self.assertEqual(client.abort_reason_code, BLOCKED_JBUSY_PRESENT_ABORT)
        self.assertEqual(client.set_file2_sent_count, 0)

    def test_15_immediate_abort_no_retry_on_busy_and_bad_frame(self) -> None:
        for fault, expected_code, expected_status in (
            ("busy", ABORT_BUSY_0X10000011, STATUS_BUSY),
            ("bad_frame", ABORT_BAD_FRAME_0X10000201, STATUS_BAD_FRAME),
        ):
            cam = FakeIOKitAdjustControlCamera(jbusy=False, inject_fault=fault)
            client = AdjustControlSessionClient(cam.handle)
            self.assertTrue(client.probe_jbusy_absent())
            self.assertTrue(client.select_path(LIBJIT_PATH))
            self.assertFalse(client.send_file2_once(self.so_64k))
            self.assertTrue(client.aborted)
            self.assertEqual(client.last_native_status, expected_status)
            self.assertEqual(client.abort_reason_code, expected_code)
            self.assertEqual(client.set_file2_sent_count, 1)
            self.assertEqual(client.set_file2_retry_count, 0)
            self.assertFalse(client.blind_second_set_file2_sent)

    def test_16_immediate_abort_no_retry_on_dlopen_mount_and_p6_full(self) -> None:
        for fault, expected_code in (
            ("dlopen_fail", ABORT_DLOPEN_FAIL_0X10000000),
            ("mount_fail", ABORT_MOUNT_FAIL_0X10000004),
            ("p6_full", ABORT_P6_FULL_0X1000000F),
        ):
            cam = FakeIOKitAdjustControlCamera(jbusy=False, inject_fault=fault)
            client = AdjustControlSessionClient(cam.handle)
            self.assertTrue(client.probe_jbusy_absent())
            self.assertTrue(client.select_path(LIBJIT_PATH))
            self.assertFalse(client.send_file2_once(self.so_64k))
            self.assertTrue(client.aborted)
            self.assertEqual(client.abort_reason_code, expected_code)
            self.assertEqual(client.set_file2_sent_count, 1)
            self.assertEqual(client.set_file2_retry_count, 0)
            self.assertFalse(client.send_file2_once(self.so_64k))
            self.assertEqual(client.set_file2_sent_count, 1)

    def test_17_usb_timeout_aborts_immediately_and_blocks_blind_second_send(self) -> None:
        cam = FakeIOKitAdjustControlCamera(jbusy=False, inject_fault="usb_timeout")
        client = AdjustControlSessionClient(cam.handle)
        self.assertTrue(client.probe_jbusy_absent())
        self.assertTrue(client.select_path(LIBJIT_PATH))
        self.assertFalse(client.send_file2_once(self.so_64k))
        self.assertTrue(client.aborted)
        self.assertEqual(client.last_native_status, STATUS_USB_TIMEOUT)
        self.assertEqual(client.abort_reason_code, ABORT_USB_TIMEOUT)
        self.assertEqual(client.set_file2_sent_count, 1)
        self.assertEqual(client.set_file2_retry_count, 0)

        # Attempting a low-level _exchange(SET_FILE2) after abort raises hard violation
        with self.assertRaises(RuntimeError):
            client._exchange(set_file2_request(99, b"blind_retry"))
        self.assertTrue(client.blind_second_set_file2_sent)

    def test_18_usb_timeout_also_caught_during_preflight_or_select_path(self) -> None:
        def _always_timeout(_wire: bytes) -> bytes:
            raise TimeoutError("USB pipe timeout")

        c1 = AdjustControlSessionClient(_always_timeout)
        self.assertFalse(c1.probe_jbusy_absent())
        self.assertTrue(c1.aborted)
        self.assertEqual(c1.abort_reason_code, ABORT_USB_TIMEOUT)

        cam = FakeIOKitAdjustControlCamera()
        c2 = AdjustControlSessionClient(cam.handle)
        self.assertTrue(c2.probe_jbusy_absent())
        c2._handler = _always_timeout
        self.assertFalse(c2.select_path(LIBJIT_PATH))
        self.assertTrue(c2.aborted)
        self.assertEqual(c2.abort_reason_code, ABORT_USB_TIMEOUT)

    def test_19_pillar_a_7_scenario_suite_all_green(self) -> None:
        pa = run_pillar_a_wire_and_preflight_7_scenario_suite(so_bytes=self.so_64k)
        self.assertTrue(pa.passed, f"Pillar A errors: {pa.errors}")
        self.assertEqual(pa.status, STATUS_VERIFIED_PILLAR_A)
        self.assertEqual(pa.scenarios_passed, 7)
        self.assertEqual(pa.scenarios_total, 7)
        self.assertEqual([r.scenario_id for r in pa.scenario_results], list(PILLAR_A_SCENARIO_IDS))
        self.assertEqual(pa.physical_usb_bytes_transmitted, 0)

    # ------------------------------------------------------------------
    # Pillar B — DUAL_PATH_SD_STREAM_AND_P6_SLIDING_WINDOW_COLD_BACKUP
    # ------------------------------------------------------------------

    def test_20_path1_sd_streaming_full_16_items_and_528b_receipt(self) -> None:
        cam = FakeIOKitAdjustControlCamera(sd_writable=True, action_mode="sd_stream")
        res = execute_sd_streaming_cold_backup(cam, self.so_64k)
        self.assertTrue(res.passed, f"Path 1 errors: {res.errors}")
        self.assertEqual(res.mount_dir, SD_BACKUP_MOUNT_DIR)
        self.assertEqual(res.manifest_entry_count, 16)
        self.assertEqual(res.covered_item_ids, REQUIRED_COLD_BACKUP_ITEM_IDS)
        self.assertEqual(res.dat2_model_id, FX3_MODEL_ID_STR)
        self.assertEqual(res.dat3_region_tag, FX3_REGION_TAG_STR)
        self.assertEqual(res.p6_receipt_bytes, SD_RECEIPT_BYTES)
        self.assertLess(res.p6_receipt_bytes, 1024)
        self.assertLess(res.p6_peak_bytes, P6_PARTITION_QUOTA_BYTES)
        self.assertEqual(res.p6_residual_files, 0)
        self.assertTrue(res.receipt_valid)
        self.assertIn(f"{SD_BACKUP_MOUNT_DIR}/{SD_BACKUP_MANIFEST_NAME}", cam.sd_files)
        self.assertEqual(len(cam.sd_manifest_text.strip().splitlines()), 16)

    def test_21_sd_528b_receipt_roundtrip_and_tamper_detection(self) -> None:
        item_hashes = {item.item_id: sha256(item.item_id.encode("ascii")).hexdigest() for item in COLD_BACKUP_ITEMS}
        manifest_sha = sha256(b"manifest").hexdigest()
        raw = build_sd_backup_receipt_bytes(
            manifest_sha256=manifest_sha,
            item_hashes=item_hashes,
            total_dumped_bytes=123456789,
        )
        self.assertEqual(len(raw), SD_RECEIPT_BYTES)
        parsed = parse_sd_backup_receipt_bytes(raw)
        self.assertTrue(parsed.valid)
        self.assertEqual(parsed.magic, SD_RECEIPT_MAGIC.decode("ascii"))
        self.assertEqual(parsed.manifest_sha256, manifest_sha)
        self.assertEqual(parsed.sector0_sha256, item_hashes["sector0"])
        self.assertEqual(parsed.p1_sha256, item_hashes["p1"])
        self.assertEqual(parsed.spi_nor_ddrtraining_sha256, item_hashes["spi_nor_ddrtraining"])
        self.assertEqual(parsed.total_dumped_bytes, 123456789)

        # Flip 1 byte in integrity-covered region
        tampered = bytearray(raw)
        tampered[42] ^= 0x01
        bad = parse_sd_backup_receipt_bytes(bytes(tampered))
        self.assertFalse(bad.valid)
        self.assertTrue(any(ERR_SD_RECEIPT_INVALID in e for e in bad.errors))

    def test_22_sd_receipt_wrong_size_magic_or_version_rejected(self) -> None:
        self.assertFalse(parse_sd_backup_receipt_bytes(b"short").valid)
        raw = bytearray(
            build_sd_backup_receipt_bytes(
                manifest_sha256="1" * 64,
                item_hashes={k: "2" * 64 for k in REQUIRED_COLD_BACKUP_ITEM_IDS},
                total_dumped_bytes=512,
            )
        )
        raw[0:8] = b"BADMAGC!"
        self.assertFalse(parse_sd_backup_receipt_bytes(bytes(raw)).valid)

    def test_23_path2_sliding_window_75mib_p3_exact_sha256_and_bounded_p6(self) -> None:
        p3_bytes = (b"FX3_REALHW_75MIB_P3_" * (P3_PARTITION_CAPACITY_BYTES // 20 + 1))[:P3_PARTITION_CAPACITY_BYTES]
        expected_sha = sha256(p3_bytes).hexdigest()
        cam = FakeIOKitAdjustControlCamera(
            sd_writable=False,
            action_mode="sliding_pull",
            partition_overrides={"p3": p3_bytes},
        )
        res = execute_p6_sliding_window_usb_pull(
            cam,
            self.so_64k,
            partition_name="p3",
            chunk_size_bytes=SLIDING_WINDOW_CHUNK_BYTES,
        )
        self.assertTrue(res.passed, f"Sliding pull errors: {res.errors}")
        self.assertEqual(res.chunks_pulled, 19)  # ceil(75 MiB / 4 MiB) == 19
        self.assertEqual(res.total_pulled_bytes, P3_PARTITION_CAPACITY_BYTES)
        self.assertEqual(res.source_sha256, expected_sha)
        self.assertEqual(res.reassembled_sha256, expected_sha)
        self.assertTrue(res.sha256_exact_match)
        self.assertLessEqual(res.peak_p6_bytes, SLIDING_WINDOW_MAX_PEAK_P6_BYTES)
        self.assertLess(res.peak_p6_bytes, P6_PARTITION_QUOTA_BYTES)
        self.assertEqual(res.p6_residual_files, 0)
        self.assertEqual(res.set_file2_retry_count, 0)

    def test_24_path2_rejects_chunk_size_over_4mib(self) -> None:
        cam = FakeIOKitAdjustControlCamera(action_mode="sliding_pull")
        with self.assertRaises(ValueError):
            execute_p6_sliding_window_usb_pull(
                cam,
                self.so_64k,
                partition_name="p13",
                chunk_size_bytes=SLIDING_WINDOW_CHUNK_BYTES + 1,
            )

    def test_25_fx3chk1_chunk_frame_valid_and_fault_modes(self) -> None:
        payload = b"CHUNK_DATA_" * 128
        framed = frame_sliding_chunk(4096, payload)
        self.assertEqual(framed[:8], CHUNK_HEADER_MAGIC)
        ok, decoded, err = verify_and_unframe_sliding_chunk(framed, expected_offset=4096)
        self.assertTrue(ok, err)
        self.assertEqual(decoded, payload)

        # Bad magic
        ok_m, _, err_m = verify_and_unframe_sliding_chunk(b"BADMAGIC" + framed[8:], expected_offset=4096)
        self.assertFalse(ok_m)
        self.assertIn(ERR_CHUNK_HEADER_CORRUPT, err_m)

        # Offset mismatch
        ok_o, _, err_o = verify_and_unframe_sliding_chunk(framed, expected_offset=8192)
        self.assertFalse(ok_o)
        self.assertIn(ERR_CHUNK_HEADER_CORRUPT, err_o)

        # CRC32 mismatch
        bad_crc = bytearray(framed)
        bad_crc[-1] ^= 0xFF
        ok_c, _, err_c = verify_and_unframe_sliding_chunk(bytes(bad_crc), expected_offset=4096)
        self.assertFalse(ok_c)
        self.assertIn(ERR_CHUNK_HEADER_CORRUPT, err_c)

        # Truncated frame
        ok_t, _, err_t = verify_and_unframe_sliding_chunk(framed[:16], expected_offset=4096)
        self.assertFalse(ok_t)
        self.assertIn(ERR_CHUNK_HEADER_CORRUPT, err_t)

    def test_26_unbounded_75mib_p3_staging_fails_with_0x1000000f(self) -> None:
        cam = FakeIOKitAdjustControlCamera(action_mode="unbounded_p3_stage")
        client = AdjustControlSessionClient(cam.handle)
        self.assertTrue(client.probe_jbusy_absent())
        self.assertTrue(client.select_path(LIBJIT_PATH))
        self.assertFalse(client.send_file2_once(self.so_64k))
        self.assertTrue(client.aborted)
        self.assertEqual(client.last_native_status, STATUS_P6_NO_SPACE)
        self.assertEqual(client.abort_reason_code, ABORT_P6_FULL_0X1000000F)

    def test_27_sliding_pull_aborts_when_chunk_temp_file_not_unlinked(self) -> None:
        cam = FakeIOKitAdjustControlCamera(
            action_mode="sliding_pull",
            unlink_staged_artifact_on_get=False,
        )
        res = execute_p6_sliding_window_usb_pull(cam, self.so_64k, partition_name="p13")
        self.assertFalse(res.passed)
        self.assertIn(STATUS_REJECTED_P6_RESIDUAL_FILES, res.error_codes)
        self.assertGreaterEqual(res.p6_residual_files, 1)

    def test_28_sd_unwritable_triggers_mount_fail_0x10000004(self) -> None:
        cam = FakeIOKitAdjustControlCamera(sd_writable=False, action_mode="sd_stream")
        res = execute_sd_streaming_cold_backup(cam, self.so_64k)
        self.assertFalse(res.passed)
        self.assertIn(ABORT_MOUNT_FAIL_0X10000004, res.error_codes)
        self.assertEqual(res.p6_residual_files, 0)

    def test_29_path2_corrupted_chunk_crc_aborts_immediately(self) -> None:
        cam = FakeIOKitAdjustControlCamera(action_mode="sliding_pull", inject_fault="corrupt_chunk_crc")
        res = execute_p6_sliding_window_usb_pull(cam, self.so_64k, partition_name="p13")
        self.assertFalse(res.passed)
        self.assertIn(ERR_CHUNK_HEADER_CORRUPT, res.error_codes)
        self.assertFalse(res.sha256_exact_match)

    def test_30_spi_nor_exact_offset_and_virtual_slice_determinism(self) -> None:
        cam = FakeIOKitAdjustControlCamera()
        backing = cam.partitions["spi_nor_ddrtraining"]
        self.assertEqual(backing.spec.offset_bytes, SPI_NOR_DDRTRAINING_OFFSET)
        self.assertEqual(backing.size_bytes, 4096)
        sl = backing.read_slice(0, 4096)
        self.assertEqual(sha256(sl).hexdigest(), backing.digest_sha256)

    def test_31_pillar_b_6_scenario_suite_all_green(self) -> None:
        pb = run_pillar_b_dual_path_backup_6_scenario_suite(so_bytes=self.so_64k)
        self.assertTrue(pb.passed, f"Pillar B errors: {pb.errors}")
        self.assertEqual(pb.status, STATUS_VERIFIED_PILLAR_B)
        self.assertEqual(pb.scenarios_passed, 6)
        self.assertEqual(pb.scenarios_total, 6)
        self.assertEqual([r.scenario_id for r in pb.scenario_results], list(PILLAR_B_SCENARIO_IDS))
        self.assertTrue(pb.sd_backup_result.passed)
        self.assertTrue(pb.sliding_75mib_result.passed)

    # ------------------------------------------------------------------
    # Pillar C — FAKE_IOKIT_USB_CAMERA_REGRESSION_AND_PASSIVE_LOCK
    # ------------------------------------------------------------------

    def test_32_fake_iokit_camera_sony_vid_pid_and_passive_flags(self) -> None:
        cam = FakeIOKitAdjustControlCamera()
        self.assertEqual(cam.usb_vid, SONY_USB_VID)
        self.assertEqual(cam.usb_pid, SONY_SERVICE_PID)
        self.assertEqual(cam.usb_vid_pid, SONY_SERVICE_VID_PID)
        self.assertFalse(cam.live_usb_iokit_transmit_enabled)
        self.assertFalse(cam.persistent_emmc_writes_authorized)
        self.assertEqual(cam.physical_usb_bytes_transmitted, 0)
        self.assertEqual(cam.physical_device_writes, 0)

    def test_33_fake_iokit_25mib_p6_quota_enforcement(self) -> None:
        cam = FakeIOKitAdjustControlCamera(p6_quota_bytes=P6_PARTITION_QUOTA_BYTES)
        self.assertEqual(cam.stage_p6_file_direct("/tmp/jiritsu/chunk_a.bin", b"A" * (25 * 1024 * 1024)), STATUS_OK)
        self.assertEqual(cam.stage_p6_file_direct("/tmp/jiritsu/chunk_b.bin", b"B"), STATUS_P6_NO_SPACE)
        self.assertEqual(cam.p6_used_bytes, P6_PARTITION_QUOTA_BYTES)

    def test_34_elf64_64k_pt_load_and_dt_hash_validation(self) -> None:
        res_ok = validate_elf64_so_for_fx3_64k(self.so_64k, require_64k_pt_load=True)
        self.assertTrue(res_ok.valid, res_ok.reason)
        self.assertTrue(res_ok.all_pt_load_64k_aligned)
        self.assertEqual(res_ok.dt_hash_words, (1, 1, 0, 0))
        self.assertTrue(res_ok.dt_hash_valid)

        so_4k = build_synthetic_jiritsu_so_64k(pt_load_align=0x1000)
        res_4k = validate_elf64_so_for_fx3_64k(so_4k, require_64k_pt_load=True)
        self.assertFalse(res_4k.valid)
        self.assertIn(ERR_ELF_PT_LOAD_NOT_64K_ALIGNED, res_4k.error_codes)

        so_bad_hash = build_synthetic_jiritsu_so_64k(pt_load_align=0x10000, dt_hash_words=(0, 1, 0, 0))
        res_bad_hash = validate_elf64_so_for_fx3_64k(so_bad_hash, require_64k_pt_load=True)
        self.assertFalse(res_bad_hash.valid)
        self.assertIn(ERR_ELF_DT_HASH_INVALID, res_bad_hash.error_codes)

        res_junk = validate_elf64_so_for_fx3_64k(b"NOT_AN_ELF")
        self.assertFalse(res_junk.valid)
        self.assertIn(ERR_ELF_DT_HASH_INVALID, res_junk.error_codes)

    def test_35_fake_iokit_rejects_4k_aligned_so_with_0x10000000(self) -> None:
        so_4k = build_synthetic_jiritsu_so_64k(pt_load_align=0x1000)
        cam = FakeIOKitAdjustControlCamera(require_64k_pt_load_align=True)
        client = AdjustControlSessionClient(cam.handle)
        self.assertTrue(client.probe_jbusy_absent())
        self.assertTrue(client.select_path(LIBJIT_PATH))
        self.assertFalse(client.send_file2_once(so_4k))
        self.assertEqual(client.last_native_status, STATUS_DLOPEN_FAIL)
        self.assertEqual(client.abort_reason_code, ABORT_DLOPEN_FAIL_0X10000000)

    def test_36_post_session_residual_file_audit_detects_leftovers(self) -> None:
        cam = FakeIOKitAdjustControlCamera(unlink_libjit_on_dlopen=False, action_mode="sd_stream")
        res = execute_sd_streaming_cold_backup(cam, self.so_64k)
        self.assertFalse(res.passed)
        audit = cam.audit_post_session()
        self.assertFalse(audit.clean)
        self.assertEqual(audit.status, STATUS_REJECTED_P6_RESIDUAL_FILES)
        self.assertIn(LIBJIT_PATH, audit.residual_paths)
        self.assertEqual(audit.p6_residual_files, 1)

    def test_37_passive_iokit_and_emmc_lock_guard(self) -> None:
        safe = audit_passive_iokit_and_emmc_lock(PassiveHardwareLockRequest())
        self.assertTrue(safe.allowed)
        self.assertFalse(safe.live_usb_iokit_transmit_enabled)
        self.assertFalse(safe.persistent_emmc_writes_authorized)
        self.assertEqual(safe.physical_usb_bytes_transmitted, 0)
        self.assertEqual(safe.physical_device_writes, 0)

        bad_usb = audit_passive_iokit_and_emmc_lock(
            PassiveHardwareLockRequest(live_usb_iokit_transmit_enabled=True, usb_bytes_requested=19)
        )
        self.assertFalse(bad_usb.allowed)
        self.assertIn(BLOCKED_LIVE_USB_IOKIT_TRANSMIT_LOCKED, bad_usb.error_codes)

        bad_emmc = audit_passive_iokit_and_emmc_lock(
            PassiveHardwareLockRequest(persistent_emmc_writes_authorized=True, emmc_write_bytes_requested=512)
        )
        self.assertFalse(bad_emmc.allowed)
        self.assertIn(BLOCKED_PERSISTENT_EMMC_WRITES_LOCKED, bad_emmc.error_codes)

    def test_38_session_client_constructor_blocks_unlocked_flags(self) -> None:
        cam = FakeIOKitAdjustControlCamera()
        with self.assertRaises(PermissionError):
            AdjustControlSessionClient(cam.handle, live_usb_iokit_transmit_enabled=True)
        with self.assertRaises(PermissionError):
            AdjustControlSessionClient(cam.handle, persistent_emmc_writes_authorized=True)

    def test_39_pillar_c_5_scenario_suite_all_green(self) -> None:
        pc = run_pillar_c_fake_iokit_regression_5_scenario_suite(so_bytes=self.so_64k)
        self.assertTrue(pc.passed, f"Pillar C errors: {pc.errors}")
        self.assertEqual(pc.status, STATUS_VERIFIED_PILLAR_C)
        self.assertEqual(pc.scenarios_passed, 5)
        self.assertEqual(pc.scenarios_total, 5)
        self.assertEqual([r.scenario_id for r in pc.scenario_results], list(PILLAR_C_SCENARIO_IDS))

    # ------------------------------------------------------------------
    # Master Suite, Determinism, JSON Hygiene & CLI 17-Pillar Integration
    # ------------------------------------------------------------------

    def test_40_clean_room_suite_sha256_is_deterministic(self) -> None:
        r2 = run_adjustcontrol_streaming_backup_suite(force_clean_room=True)
        self.assertEqual(self.clean_report.suite_sha256, r2.suite_sha256)
        self.assertEqual(
            self.clean_report.pillar_a_wire_and_preflight_7_scenarios.suite_sha256,
            r2.pillar_a_wire_and_preflight_7_scenarios.suite_sha256,
        )
        self.assertEqual(
            self.clean_report.pillar_b_dual_path_backup_6_scenarios.suite_sha256,
            r2.pillar_b_dual_path_backup_6_scenarios.suite_sha256,
        )
        self.assertEqual(
            self.clean_report.pillar_c_fake_iokit_regression_5_scenarios.suite_sha256,
            r2.pillar_c_fake_iokit_regression_5_scenarios.suite_sha256,
        )

    def test_41_json_serialization_no_raw_bytes_and_no_nan(self) -> None:
        for rep in (self.suite_report, self.clean_report):
            rendered = json.dumps(rep.to_dict(), ensure_ascii=False, sort_keys=True, allow_nan=False)
            self.assertNotRegex(rendered, RAW_BYTES_RE)
            decoded = json.loads(rendered)
            self.assertEqual(decoded["suite_sha256"], rep.suite_sha256)
            self.assertEqual(decoded["physical_device_writes"], 0)
            self.assertEqual(decoded["physical_usb_bytes_transmitted"], 0)
            self.assertFalse(decoded["live_usb_iokit_transmit_enabled"])
            self.assertFalse(decoded["persistent_emmc_writes_authorized"])

    def test_42_cli_verify_adjustcontrol_backup_client_clean_room_json_and_text(self) -> None:
        buf_json = io.StringIO()
        with (
            mock.patch.object(sys, "argv", ["fx3_recovery", "verify-adjustcontrol-backup-client", "--clean-room", "--json"]),
            redirect_stdout(buf_json),
        ):
            rc_json = fx3_cli.main()
        self.assertEqual(rc_json, 0)
        rendered = buf_json.getvalue()
        self.assertNotRegex(rendered, RAW_BYTES_RE)
        parsed = json.loads(rendered)
        self.assertEqual(parsed["status"], STATUS_VERIFIED_SUITE)
        self.assertEqual(parsed["verification_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertFalse(parsed["live_usb_iokit_transmit_enabled"])
        self.assertEqual(parsed["physical_usb_bytes_transmitted"], 0)

        buf_txt = io.StringIO()
        with (
            mock.patch.object(sys, "argv", ["fx3_recovery", "verify-adjustcontrol-backup-client", "--clean-room"]),
            redirect_stdout(buf_txt),
        ):
            rc_txt = fx3_cli.main()
        self.assertEqual(rc_txt, 0)
        txt = buf_txt.getvalue()
        self.assertIn(f"status={STATUS_VERIFIED_SUITE}", txt)
        self.assertIn("wire_preflight_scenarios=7/7", txt)
        self.assertIn("dual_path_backup_scenarios=6/6", txt)
        self.assertIn("fake_iokit_scenarios=5/5", txt)
        self.assertIn("live_usb_iokit_transmit_enabled=False", txt)
        self.assertIn("persistent_emmc_writes_authorized=False", txt)

    def test_43_cli_verify_adjustcontrol_backup_client_active_and_out_dir(self) -> None:
        buf = io.StringIO()
        with (
            mock.patch.object(sys, "argv", ["fx3_recovery", "verify-adjustcontrol-backup-client", "--json"]),
            redirect_stdout(buf),
        ):
            rc = fx3_cli.main()
        self.assertEqual(rc, 0)
        parsed = json.loads(buf.getvalue())
        self.assertTrue(parsed["all_passed"])
        self.assertIn(parsed["verification_mode"], ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"))

        scratch_root = ROOT / "work" / "_tests" / "phase139_cli_out"
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
                        "verify-adjustcontrol-backup-client",
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
            out_file = scratch_root / "adjustcontrol-streaming-backup-report.json"
            self.assertTrue(out_file.is_file())
            written = json.loads(out_file.read_text(encoding="utf-8"))
            self.assertEqual(written["status"], STATUS_VERIFIED_SUITE)
            self.assertEqual(written["physical_usb_bytes_transmitted"], 0)
        finally:
            if scratch_root.exists():
                shutil.rmtree(scratch_root)

    def test_44_cli_verify_adjustcontrol_backup_client_failure_returns_exit_2(self) -> None:
        failing = AdjustControlStreamingBackupSuiteReport(
            **{**self.clean_report.__dict__, "all_passed": False, "status": STATUS_FAIL_SUITE}
        )
        with mock.patch(
            "fx3_recovery.__main__.run_adjustcontrol_streaming_backup_suite",
            return_value=failing,
        ):
            buf = io.StringIO()
            with (
                mock.patch.object(sys, "argv", ["fx3_recovery", "verify-adjustcontrol-backup-client", "--clean-room", "--json"]),
                redirect_stdout(buf),
            ):
                rc = fx3_cli.main()
            self.assertEqual(rc, 2)
            parsed = json.loads(buf.getvalue())
            self.assertFalse(parsed["all_passed"])
            self.assertEqual(parsed["status"], STATUS_FAIL_SUITE)

    def test_45_cli_verify_all_recovery_17_pillars_clean_and_active_and_failure_prop(self) -> None:
        argv_17 = [
            "fx3_recovery",
            "verify-all-recovery",
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
        ]
        # Clean-room 17/17
        buf_c = io.StringIO()
        with mock.patch.object(sys, "argv", argv_17 + ["--clean-room"]), redirect_stdout(buf_c):
            rc_c = fx3_cli.main()
        self.assertEqual(rc_c, 0)
        raw_c = buf_c.getvalue()
        self.assertNotRegex(raw_c, RAW_BYTES_RE)
        parsed_c = json.loads(raw_c)
        self.assertTrue(parsed_c["all_passed"])
        self.assertEqual(parsed_c["pillar_count"], 17)
        self.assertEqual(parsed_c["pillars_passed"], 17)
        self.assertEqual(
            parsed_c["phase139_pillar17_adjustcontrol_streaming_backup"]["status"],
            STATUS_VERIFIED_SUITE,
        )

        # Active mode 17/17
        buf_a = io.StringIO()
        with mock.patch.object(sys, "argv", argv_17), redirect_stdout(buf_a):
            rc_a = fx3_cli.main()
        self.assertEqual(rc_a, 0)
        parsed_a = json.loads(buf_a.getvalue())
        self.assertTrue(parsed_a["all_passed"])
        self.assertEqual(parsed_a["pillar_count"], 17)
        self.assertEqual(parsed_a["pillars_passed"], 17)

        # Failure propagation -> exit 2, 16/17
        failing = AdjustControlStreamingBackupSuiteReport(
            **{**self.clean_report.__dict__, "all_passed": False, "status": STATUS_FAIL_SUITE}
        )
        with mock.patch(
            "fx3_recovery.__main__.run_adjustcontrol_streaming_backup_suite",
            return_value=failing,
        ):
            buf_f = io.StringIO()
            with mock.patch.object(sys, "argv", argv_17 + ["--clean-room"]), redirect_stdout(buf_f):
                rc_f = fx3_cli.main()
            self.assertEqual(rc_f, 2)
            parsed_f = json.loads(buf_f.getvalue())
            self.assertFalse(parsed_f["all_passed"])
            self.assertEqual(parsed_f["pillar_count"], 17)
            self.assertEqual(parsed_f["pillars_passed"], 16)

    def test_46_cli_verify_all_recovery_backward_compat_7_16_and_17_text(self) -> None:
        buf_def = io.StringIO()
        with (
            mock.patch.object(sys, "argv", ["fx3_recovery", "verify-all-recovery", "--clean-room", "--json"]),
            redirect_stdout(buf_def),
        ):
            rc_def = fx3_cli.main()
        self.assertEqual(rc_def, 0)
        parsed_def = json.loads(buf_def.getvalue())
        self.assertEqual(parsed_def["pillar_count"], 7)
        self.assertNotIn("phase139_pillar17_adjustcontrol_streaming_backup", parsed_def)

        buf_16 = io.StringIO()
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
                    "--json",
                ],
            ),
            redirect_stdout(buf_16),
        ):
            rc_16 = fx3_cli.main()
        self.assertEqual(rc_16, 0)
        parsed_16 = json.loads(buf_16.getvalue())
        self.assertEqual(parsed_16["pillar_count"], 16)
        self.assertNotIn("phase139_pillar17_adjustcontrol_streaming_backup", parsed_16)

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
                    "--with-phase134",
                    "--with-phase138",
                    "--with-phase139",
                ],
            ),
            redirect_stdout(buf_txt),
        ):
            rc_txt = fx3_cli.main()
        self.assertEqual(rc_txt, 0)
        txt = buf_txt.getvalue()
        self.assertIn("status=VERIFIED_RECOVERY_MASTER_SUITE", txt)
        self.assertIn("pillars=17/17", txt)


if __name__ == "__main__":
    unittest.main()
