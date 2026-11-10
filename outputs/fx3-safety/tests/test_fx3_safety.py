"""Comprehensive unit tests for the fx3_safety v2.0 Flash Safety & Brick Recovery Suite."""

from __future__ import annotations

import json
import struct
import tempfile
import unittest
from pathlib import Path

from fx3_safety.boot_contracts import (
    BK4_HEADER_SIZE,
    BK4_MAGIC,
    BK4_SYNC_MARKER,
    BKSB_MAGIC,
    FA0080_SLOT_COUNT,
    FA0080_SLOT_STRIDE,
    FA0080_TOTAL_BYTES,
    SONY_PTBL_ENTRY_COUNT,
    SONY_PTBL_MAGIC,
    SONY_PTBL_VERSION,
    parse_bk4_record,
    parse_fa0080_table,
    verify_bksb_ldr_bkup,
    verify_boot_screen_enum_contract,
    verify_sector0_partition_table,
)
from fx3_safety.brick_classifier import classify_brick_state, generate_failsafe_init2_overlay_hook
from fx3_safety.preflight import (
    TIER0_CANONICAL_SOURCES,
    TIER0_REQUIRED_BACKUPS,
    audit_tier0_worker_syscall_trace,
    evaluate_12_safety_gates,
    verify_failsafe_hook_script,
    verify_tier0_backup_manifest,
)


def _build_synthetic_sector0(profile: str = "FX3_702") -> bytes:
    buf = bytearray(512)
    buf[0:4] = SONY_PTBL_MAGIC
    buf[4:8] = SONY_PTBL_VERSION
    struct.pack_into("<I", buf, 8, SONY_PTBL_ENTRY_COUNT)

    # Canonical non-overlapping entries
    entries = {
        1: (0x00000080, 0x0000BF80, 4, 1),
        2: (0x0000C000, 0x0000A000, 4, 1),
        3: (0x00016000, 0x00025800, 5, 1),
        5: (0x00042000, 0x00096000, 6, 1),
        6: (0x000D8000, 0x0000C800, 4, 1),
        7: (0x000E4800, 0x00019000 if profile == "FX3_702" else 0, 5, 1),
        8: (0x000FD800, 0x00032000, 5, 1),
        12: (0x0020C000, 0x00014000 if profile == "FX3_702" else 0x0000A000, 5, 1),
        15: (0x0022A000 if profile == "FX3_702" else 0x00220000, 0x000FA000, 5, 1),
        18: (0x00324000 if profile == "CUSTOM" else (0x0031C000 if profile == "FX3_702" else 0x00312000), 0x0000A000, 4, 1),
        20: (0x00330000, 0 if profile == "FX3_702" else 0x00032000, 5, 1),
        21: (0x00362000, 0 if profile == "FX3_702" else 0x00016400, 5, 1),
    }
    # Ensure p15 and p18 don't overlap in synthetic table:
    if profile == "FX3_702":
        entries[15] = (0x00220000, 0x000FA000, 5, 1)  # ends at 0x31A000 < 0x31C000
    elif profile == "FX6_601":
        entries[15] = (0x00216000, 0x000FA000, 5, 1)  # ends at 0x310000 < 0x312000

    for pid, (start_s, size_s, ptype, flag) in entries.items():
        off = 32 + (pid - 1) * 16
        struct.pack_into("<IIII", buf, off, start_s, size_s, ptype, flag)
    return bytes(buf)


def _build_synthetic_bk4(active_byte8: int = 1, subs: int = 819, word2c: int = 5) -> bytes:
    dataoff = BK4_HEADER_SIZE
    payload = b"\x11\x22\x33\x44" * 64
    datasize = len(payload)
    buf = bytearray(dataoff + datasize)
    struct.pack_into("<I", buf, 0x04, BK4_SYNC_MARKER)
    buf[0x08] = active_byte8
    buf[0x0C:0x10] = BK4_MAGIC
    struct.pack_into("<IIIII", buf, 0x10, subs, 42, dataoff, datasize, 0)
    struct.pack_into("<i", buf, 0x2C, word2c)
    buf[dataoff : dataoff + datasize] = payload
    csum = (sum(buf[0:0x20]) + sum(buf[0x24 : dataoff + datasize])) & 0xFFFFFFFF
    struct.pack_into("<I", buf, 0x20, csum)
    return bytes(buf)


class TestFX3SafetySuite(unittest.TestCase):
    def test_sector0_fx3_and_fx6_validation(self) -> None:
        fx3_s0 = _build_synthetic_sector0("FX3_702")
        res_fx3 = verify_sector0_partition_table(fx3_s0)
        self.assertTrue(res_fx3.valid, res_fx3.errors)
        self.assertEqual(res_fx3.layout_profile, "FX3_702")
        self.assertTrue(res_fx3.calibration_partitions_intact)

        fx6_s0 = _build_synthetic_sector0("FX6_601")
        res_fx6 = verify_sector0_partition_table(fx6_s0)
        self.assertTrue(res_fx6.valid, res_fx6.errors)
        self.assertEqual(res_fx6.layout_profile, "FX6_601")
        self.assertTrue(any("p18 (/lens/lensfile.bin) is shifted" in w for w in res_fx6.warnings))

    def test_sector0_detects_bad_magic_and_overlap(self) -> None:
        bad = bytearray(_build_synthetic_sector0("FX3_702"))
        bad[0:4] = b"DEAD"
        # Also make p2 overlap p1
        struct.pack_into("<IIII", bad, 32 + 1 * 16, 0x00000100, 0x0000A000, 4, 1)
        res = verify_sector0_partition_table(bytes(bad))
        self.assertFalse(res.valid)
        self.assertFalse(res.magic_ok)
        self.assertTrue(res.has_overlaps)

    def test_bk4_record_checksum_and_strict_byte8_selector(self) -> None:
        # Active runtime BK4 (byte8 == 1) -> selectable by loader_nor.bin 0xfe04c7a8
        rec_active = _build_synthetic_bk4(active_byte8=1, subs=819, word2c=10)
        summary, errs = parse_bk4_record(rec_active)
        self.assertEqual(errs, [])
        self.assertIsNotNone(summary)
        assert summary is not None
        self.assertTrue(summary.checksum_ok)
        self.assertTrue(summary.strict_loader_selectable)

        # Uninitialized template BK4 (byte8 == 0) -> valid checksum, but strict_loader_selectable is False
        rec_tmpl = _build_synthetic_bk4(active_byte8=0, subs=840, word2c=0)
        summary_tmpl, errs_tmpl = parse_bk4_record(rec_tmpl)
        self.assertEqual(errs_tmpl, [])
        assert summary_tmpl is not None
        self.assertTrue(summary_tmpl.checksum_ok)
        self.assertFalse(summary_tmpl.strict_loader_selectable)

        # Corrupted byte -> checksum fails
        corrupted = bytearray(rec_active)
        corrupted[-1] ^= 0xFF
        summary_bad, errs_bad = parse_bk4_record(bytes(corrupted))
        assert summary_bad is not None
        self.assertFalse(summary_bad.checksum_ok)
        self.assertTrue(len(errs_bad) > 0)

    def test_fa0080_descriptor_table_parser(self) -> None:
        tbl = bytearray(FA0080_TOTAL_BYTES)
        # Slot 0: p3 \av-cam.bin -> 0x401000000 .. 0x401ffffff
        struct.pack_into("<QQII", tbl, 0, 0x401000000, 0x401FFFFFF, 3, 0x05000000)
        tbl[0x18 : 0x18 + 11] = b"\\av-cam.bin"
        # Slot 3: p3 \vmlinux.bin -> 0x400080000 .. 0x4005fffff
        off3 = 3 * FA0080_SLOT_STRIDE
        struct.pack_into("<QQII", tbl, off3, 0x400080000, 0x4005FFFFF, 3, 0x05000000)
        tbl[off3 + 0x18 : off3 + 0x18 + 12] = b"\\vmlinux.bin"

        slots, errs = parse_fa0080_table(bytes(tbl))
        self.assertEqual(errs, [])
        self.assertEqual(len(slots), 2)
        self.assertEqual(slots[0].path, "\\av-cam.bin")
        self.assertEqual(slots[0].capacity_bytes, 16 * 1024 * 1024)
        self.assertEqual(slots[1].path, "\\vmlinux.bin")

    def test_bksb_ldr_bkup_and_boot_screen_contract(self) -> None:
        buf = bytearray(64)
        struct.pack_into("<II", buf, 0, BKSB_MAGIC, 2)
        struct.pack_into("<III", buf, 8, 0x00510015, 32, 4)
        struct.pack_into("<III", buf, 20, 0x00510016, 36, 4)
        res = verify_bksb_ldr_bkup(bytes(buf))
        self.assertTrue(res["valid"])
        self.assertEqual(res["key_count"], 2)

        # Boot screen contract: FX3 16161616 / 19191919 fails on FX6_601 but passes on FX3_702
        c_fail = verify_boot_screen_enum_contract(b"\x16\x16\x16\x16", b"\x19\x19\x19\x19", "FX6_601")
        self.assertFalse(c_fail["valid"])
        self.assertEqual(len(c_fail["errors"]), 2)

        c_pass = verify_boot_screen_enum_contract(b"\x00", b"\x01", "FX6_601")
        self.assertTrue(c_pass["valid"])

    def test_brick_classifier_all_5_levels(self) -> None:
        # Level 0: One-shot overlay auto-recoverable
        d0 = classify_brick_state(
            corrupted_regions=["p15_usr"],
            oneshot_overlay_used=True,
        )
        self.assertEqual(d0.level, "LEVEL_0_TRANSIENT_OR_ONESHOT_OVERLAY")
        self.assertTrue(d0.software_usb_or_sd_recoverable)
        self.assertFalse(d0.hardware_programmer_required)

        # Level 1: Userland appFw soft brick with USB MSC alive
        d1 = classify_brick_state(
            usb_vid_pid="054C:0DA1",
            corrupted_regions=["p15_usr"],
        )
        self.assertEqual(d1.level, "LEVEL_1_USERLAND_APPFW_SOFT_BRICK")
        self.assertTrue(d1.software_usb_or_sd_recoverable)

        # Level 2 Armed: p3 broken but p1 updater armed
        d2_armed = classify_brick_state(
            corrupted_regions=["p3_system"],
            updater_mode_armed=True,
        )
        self.assertEqual(d2_armed.level, "LEVEL_2_BOOT_CHAIN_FAULT_WITH_P1_ARMED")
        self.assertTrue(d2_armed.software_usb_or_sd_recoverable)

        # Level 2 Unarmed: p3 or p10_preload broken and p1 NOT armed -> no auto-failover in loader_nor.bin,
        # but recoverable without disassembly via Multi-Terminal 1.8V UART BootROM -> 18D1:4EE0 Fastboot!
        d2_unarmed = classify_brick_state(
            corrupted_regions=["p3_system", "p10_preload"],
            updater_mode_armed=False,
        )
        self.assertEqual(d2_unarmed.level, "LEVEL_2_UNARMED_P2_P3_P7_BOOT_HANG")
        self.assertFalse(d2_unarmed.software_usb_or_sd_recoverable)
        self.assertTrue(d2_unarmed.disassembly_free_uart_bootrom_recoverable)
        self.assertFalse(d2_unarmed.hardware_programmer_required)

        # Level 2 Blink Loop: 5L+6S or 7L+7S SD recovery loop
        d2_blink = classify_brick_state(led_symptom="red_5L_6S")
        self.assertEqual(d2_blink.level, "LEVEL_2_UPDATER_BLINK_LOOP_SD_RECOVERABLE")
        self.assertTrue(d2_blink.software_usb_or_sd_recoverable)

        # Level 3: p1 updater corrupted while main UI works
        d3 = classify_brick_state(
            display_state="normal_ui",
            corrupted_regions=["p1_updater"],
        )
        self.assertEqual(d3.level, "LEVEL_3_P1_UPDATER_CORRUPTION")
        self.assertTrue(d3.software_usb_or_sd_recoverable)

        # Level 4: SPI NOR or 6-Long-Blink SPOF hardware brick
        d4 = classify_brick_state(led_symptom="red_6L", corrupted_regions=["spi_nor"])
        self.assertEqual(d4.level, "LEVEL_4_SPOF_HARDWARE_BRICK")
        self.assertTrue(d4.hardware_programmer_required)

    def test_tier0_backup_manifest_verifier(self) -> None:
        good_items = {}
        for k, spec in TIER0_REQUIRED_BACKUPS.items():
            sz = spec.get("exact_bytes") or spec.get("min_bytes") or 4096
            digest = "a" * 64
            good_items[k] = {"bytes": sz, "pass1_sha256": digest, "pass2_sha256": digest}

        manifest = {
            "camera_body_tag": "b" * 64,
            "model_id": "0x91030080",
            "items": good_items,
        }
        res = verify_tier0_backup_manifest(manifest)
        self.assertTrue(res.valid, res.errors)

        # Introduce a two-pass readback mismatch on p6_jiritsu
        bad_items = dict(good_items)
        bad_items["p6_jiritsu"] = {
            "bytes": 26214400,
            "pass1_sha256": "a" * 64,
            "pass2_sha256": "c" * 64,
        }
        res_bad = verify_tier0_backup_manifest(
            {"camera_body_tag": "b" * 64, "items": bad_items}
        )
        self.assertFalse(res_bad.valid)
        self.assertIn("p6_jiritsu", res_bad.mismatched_two_pass_items)

    def test_failsafe_hook_and_12_gate_preflight(self) -> None:
        hook = generate_failsafe_init2_overlay_hook()
        self.assertIn('rm -f "/tmp/mod_arm_once"', hook)
        self.assertIn("busybox mount --bind", hook)
        self.assertIn("/setting/updater/mode5", hook)

        hook_audit = verify_failsafe_hook_script(hook)
        self.assertTrue(hook_audit.valid, hook_audit.errors)
        self.assertTrue(bool(hook_audit))
        self.assertTrue(hook_audit.clear_before_exec_ok)
        self.assertTrue(hook_audit.ram_bind_mount_ok)
        self.assertTrue(hook_audit.watchdog_guard_ok)
        self.assertTrue(hook_audit.updater_mode5_fallback_ok)

        # Commenting out Clear-Before-Exec unlink or moving it after mount --bind must fail closed
        commented = hook.replace('rm -f "/tmp/mod_arm_once"', '# rm -f "/tmp/mod_arm_once"')
        self.assertFalse(verify_failsafe_hook_script(commented).valid)
        reversed_order = (
            'busybox mount --bind /a /b\nrm -f "/tmp/mod_arm_once"\nsleep 45\nbusybox reboot -f\n: > /setting/updater/mode5\n'
        )
        self.assertFalse(verify_failsafe_hook_script(reversed_order).valid)
        forbidden_flash = hook + "\ndd if=/tmp/x of=/dev/nflasha15 bs=4096\n"
        self.assertFalse(verify_failsafe_hook_script(forbidden_flash).valid)

        repo_root = Path(__file__).resolve().parents[3]
        preflight = evaluate_12_safety_gates(repo_root)
        self.assertEqual(preflight["schema"], "fx3-research-safety-inventory-v2")
        self.assertFalse(preflight["persistent_write_release"])
        self.assertEqual(preflight["summary"]["total_gates"], 12)
        self.assertGreaterEqual(preflight["summary"]["verified_gates"], 9)

    def test_tier0_canonical_sources_and_syscall_trace_auditor(self) -> None:
        self.assertEqual(set(TIER0_CANONICAL_SOURCES.keys()), set(TIER0_REQUIRED_BACKUPS.keys()))

        valid_trace = [
            {"nr": 35, "dirfd": -100, "path": "/tmp/jiritsu/libJit.so", "flags": 0, "ret": 0},
            {"nr": 34, "dirfd": -100, "path": "/mnt/fx3_tier0_backup", "flags": 0o700, "ret": 0},
            {"nr": 56, "dirfd": -100, "path": "/dev/nflasha", "flags": 0x28000, "ret": 10},
            {"nr": 67, "fd": 10, "ret": 512},
            {"nr": 56, "dirfd": -100, "path": "/mnt/fx3_tier0_backup/sector0.bin", "flags": 0x280C1, "ret": 11},
            {"nr": 64, "fd": 11, "ret": 512},
            {"nr": 82, "fd": 11, "ret": 0},
            {"nr": 57, "fd": 11, "ret": 0},
            {"nr": 57, "fd": 10, "ret": 0},
        ]
        audit_ok = audit_tier0_worker_syscall_trace(valid_trace)
        self.assertTrue(audit_ok.valid, audit_ok.errors)
        self.assertTrue(audit_ok.first_path_op_unlink_libjit)
        self.assertEqual(audit_ok.dev_write_open_count, 0)
        self.assertEqual(audit_ok.source_fd_write_count, 0)

        # Redline violation 1: missing initial unlinkat
        bad_entry = valid_trace[1:]
        audit_bad_entry = audit_tier0_worker_syscall_trace(bad_entry)
        self.assertFalse(audit_bad_entry.valid)
        self.assertFalse(audit_bad_entry.first_path_op_unlink_libjit)

        # Redline violation 2: O_RDWR on /dev/nflasha + write to source fd + O_TRUNC on output
        bad_rw = [
            {"nr": 35, "dirfd": -100, "path": "/tmp/jiritsu/libJit.so", "flags": 0, "ret": 0},
            {"nr": 56, "dirfd": -100, "path": "/dev/nflasha", "flags": 0x2, "ret": 10},
            {"nr": 64, "fd": 10, "ret": 512},
            {"nr": 56, "dirfd": -100, "path": "/mnt/fx3_tier0_backup/sector0.bin", "flags": 0x241, "ret": 11},
        ]
        audit_bad_rw = audit_tier0_worker_syscall_trace(bad_rw)
        self.assertFalse(audit_bad_rw.valid)
        self.assertEqual(audit_bad_rw.dev_write_open_count, 1)
        self.assertEqual(audit_bad_rw.source_fd_write_count, 1)
        self.assertEqual(audit_bad_rw.missing_nofollow_source_opens, 1)
        self.assertEqual(audit_bad_rw.non_excl_output_opens, 1)

    def test_12_gate_dry_run_candidate_integration(self) -> None:
        repo_root = Path(__file__).resolve().parents[3]
        good_items = {
            k: {
                "bytes": spec.get("exact_bytes") or spec.get("min_bytes") or 4096,
                "pass1_sha256": "d" * 64,
                "pass2_sha256": "d" * 64,
            }
            for k, spec in TIER0_REQUIRED_BACKUPS.items()
        }
        manifest = {"camera_body_tag": "e" * 64, "model_id": "0x91030080", "items": good_items}
        trace = [{"nr": 35, "dirfd": -100, "path": "/tmp/jiritsu/libJit.so", "flags": 0, "ret": 0}]
        hook = generate_failsafe_init2_overlay_hook()

        ok_rep = evaluate_12_safety_gates(
            repo_root,
            tier0_manifest=manifest,
            worker_syscall_trace=trace,
            init2_failsafe_hook=hook,
            candidate_bundle_verified=True,
            allow_dry_run_gate12=True,
        )
        self.assertEqual(ok_rep["summary"]["verified_gates"], 12)
        self.assertEqual(ok_rep["summary"]["blocked_or_pending_gates"], 0)
        self.assertTrue(ok_rep["summary"]["all_12_gates_verified"])
        self.assertFalse(ok_rep["persistent_write_release"])

        bad_rep = evaluate_12_safety_gates(
            repo_root,
            tier0_manifest=manifest,
            worker_syscall_trace=trace,
            init2_failsafe_hook=hook,
            candidate_bundle_verified=False,
            allow_dry_run_gate12=True,
        )
        self.assertEqual(bad_rep["summary"]["verified_gates"], 11)
        self.assertFalse(bad_rep["summary"]["all_12_gates_verified"])

    def test_phase6_gate12_backup_mount_tolerance_redline(self) -> None:
        repo_root = Path(__file__).resolve().parents[3]
        good_items = {
            k: {
                "bytes": spec.get("exact_bytes") or spec.get("min_bytes") or 4096,
                "pass1_sha256": "d" * 64,
                "pass2_sha256": "d" * 64,
            }
            for k, spec in TIER0_REQUIRED_BACKUPS.items()
        }
        manifest = {"camera_body_tag": "e" * 64, "model_id": "0x91030080", "items": good_items}
        trace = [{"nr": 35, "dirfd": -100, "path": "/tmp/jiritsu/libJit.so", "flags": 0, "ret": 0}]
        hook = generate_failsafe_init2_overlay_hook()

        ok_bmt = evaluate_12_safety_gates(
            repo_root,
            tier0_manifest=manifest,
            worker_syscall_trace=trace,
            init2_failsafe_hook=hook,
            candidate_bundle_verified=True,
            allow_dry_run_gate12=True,
            backup_mount_tolerance_ok=True,
        )
        self.assertEqual(ok_bmt["summary"]["verified_gates"], 12)
        self.assertTrue(ok_bmt["backup_mount_tolerance_ok"])

        blocked_bmt = evaluate_12_safety_gates(
            repo_root,
            tier0_manifest=manifest,
            worker_syscall_trace=trace,
            init2_failsafe_hook=hook,
            candidate_bundle_verified=True,
            allow_dry_run_gate12=True,
            backup_mount_tolerance_ok=False,
        )
        self.assertEqual(blocked_bmt["summary"]["verified_gates"], 11)
        self.assertFalse(blocked_bmt["summary"]["all_12_gates_verified"])
        self.assertFalse(blocked_bmt["backup_mount_tolerance_ok"])
        g12_entry = [g for g in blocked_bmt["gates"] if g["gate_id"] == "G12_persistent_flash_write_authorization"][0]
        self.assertEqual(g12_entry["status"], "BLOCKED_BY_BACKUP_OR_MOUNT_TOLERANCE_REDLINE")

    def test_phase7_gate12_boot_selector_and_banks_redline(self) -> None:
        repo_root = Path(__file__).resolve().parents[3]
        good_items = {
            k: {
                "bytes": spec.get("exact_bytes") or spec.get("min_bytes") or 4096,
                "pass1_sha256": "d" * 64,
                "pass2_sha256": "d" * 64,
            }
            for k, spec in TIER0_REQUIRED_BACKUPS.items()
        }
        manifest = {"camera_body_tag": "e" * 64, "model_id": "0x91030080", "items": good_items}
        trace = [{"nr": 35, "dirfd": -100, "path": "/tmp/jiritsu/libJit.so", "flags": 0, "ret": 0}]
        hook = generate_failsafe_init2_overlay_hook()

        ok_bsb = evaluate_12_safety_gates(
            repo_root,
            tier0_manifest=manifest,
            worker_syscall_trace=trace,
            init2_failsafe_hook=hook,
            candidate_bundle_verified=True,
            allow_dry_run_gate12=True,
            backup_mount_tolerance_ok=True,
            boot_selector_and_banks_ok=True,
        )
        self.assertEqual(ok_bsb["summary"]["verified_gates"], 12)
        self.assertTrue(ok_bsb["boot_selector_and_banks_ok"])

        blocked_bsb = evaluate_12_safety_gates(
            repo_root,
            tier0_manifest=manifest,
            worker_syscall_trace=trace,
            init2_failsafe_hook=hook,
            candidate_bundle_verified=True,
            allow_dry_run_gate12=True,
            backup_mount_tolerance_ok=True,
            boot_selector_and_banks_ok=False,
        )
        self.assertEqual(blocked_bsb["summary"]["verified_gates"], 11)
        self.assertFalse(blocked_bsb["summary"]["all_12_gates_verified"])
        self.assertFalse(blocked_bsb["boot_selector_and_banks_ok"])
        g12_entry = [g for g in blocked_bsb["gates"] if g["gate_id"] == "G12_persistent_flash_write_authorization"][0]
        self.assertEqual(g12_entry["status"], "BLOCKED_BY_BOOT_SELECTOR_OR_BANK_REDLINE")


if __name__ == "__main__":
    unittest.main()
