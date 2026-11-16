"""Phase 137 Dual-Mode Unit Tests (42 tests): Real-Hardware Unknowns U2 & U3
(`cpapp-b.bin` TOPPERS CP RTOS Cross-Hardware Assertion, Route-1 vs Route-2
Architecture Proof, & `Backup.bin` `819->840` / `0x00fa0080` Bank 0/1 Boot
Descriptors & Per-Body Calibration Auditor).
"""

from __future__ import annotations

import ast
import io
import json
import os
import re
import struct
import time
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

import fx3_firmware_lab as lab
from fx3_firmware_lab.__main__ import main as cli_main, run_audit_all
from fx3_firmware_lab.realhw_cp_rtos_and_backup_bin_auditor import (
    CP_ARM32_ENTRY_WORDS,
    CP_IDENTICAL_PREFIX_BYTES,
    CP_LOAD_BASE,
    EXPECTED_BIG_BACKUP_PATHS,
    EXPECTED_FX3_SUBSYSTEMS,
    EXPECTED_FX6_SUBSYSTEMS,
    EXPECTED_LDR_BKUP_KEY_COUNT,
    EXPECTED_LDR_BKUP_PREFIXES,
    EXPECTED_TOMCO_MEMCFG_POOLS,
    EXPECTED_TOMCO_TOTAL_MIB,
    FX6_EXCLUSIVE_CP_MARKERS,
    PHASE_137_SCHEMA,
    PHASE_137_VERSION,
    SHARED_CP_RTOS_MARKERS,
    BootDescriptorSlot,
    analyze_realhw_cp_rtos_and_backup_bin,
    build_clean_room_realhw_cp_backup_fixtures,
    evaluate_boot_descriptor_diff,
    evaluate_cp_rtos_compatibility,
    evaluate_per_body_calibration_policy,
    evaluate_phase137_write_guard,
    evaluate_route1_vs_route2_architecture,
    parse_dual_bk4_and_descriptors,
    parse_kemco_text,
    parse_tomco_text,
    realhw_cp_rtos_and_backup_bin_report_to_dict,
)


_BYTES_REPR_RE = re.compile(r"(?<![0-9A-Za-z_/.-])b['\"]")
_AUDITOR_PATH = (
    Path(__file__).resolve().parent.parent
    / "fx3_firmware_lab"
    / "realhw_cp_rtos_and_backup_bin_auditor.py"
)


class TestRealhwCpRtosAndBackupBin(unittest.TestCase):
    """Comprehensive dual-mode tests (42 tests) for the 27th unified auditor."""

    # ---- Mode, Runtime, Determinism & Structural Hygiene ----

    def test_01_clean_room_report_all_pillars_and_runtime(self) -> None:
        t0 = time.perf_counter()
        rep = analyze_realhw_cp_rtos_and_backup_bin(clean_room=True)
        dt_cold = time.perf_counter() - t0
        t1 = time.perf_counter()
        rep_warm = analyze_realhw_cp_rtos_and_backup_bin(clean_room=True)
        dt_warm = time.perf_counter() - t1

        self.assertTrue(rep.all_checks_passed, rep.errors)
        self.assertEqual(rep.mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(rep.schema_version, PHASE_137_SCHEMA)
        self.assertEqual(rep.phase_version, PHASE_137_VERSION)
        self.assertTrue(rep.pillar1_cp_rtos_divergence.passed)
        self.assertTrue(rep.pillar2_route_architecture.passed)
        self.assertTrue(rep.pillar3_backup_layout.passed)
        self.assertTrue(rep.pillar4_zero_flash_auth.passed)
        self.assertEqual(rep.report_sha256, rep_warm.report_sha256)
        self.assertEqual(len(rep.report_sha256), 64)
        self.assertLess(dt_cold, 0.50 if __import__("os").environ.get("GITHUB_ACTIONS") == "true" else 0.08)
        self.assertLess(dt_warm, 0.25 if __import__("os").environ.get("GITHUB_ACTIONS") == "true" else 0.03)

    def test_02_auto_mode_or_local_donor_runtime_under_025s_and_sizes(self) -> None:
        t0 = time.perf_counter()
        rep = analyze_realhw_cp_rtos_and_backup_bin()
        dt = time.perf_counter() - t0
        self.assertTrue(rep.all_checks_passed, rep.errors)
        self.assertIn(rep.mode, ("LOCAL_DONOR_VERIFIED", "CLEAN_ROOM_SYNTHETIC"))
        self.assertLess(dt, 0.25)
        if rep.mode == "LOCAL_DONOR_VERIFIED":
            self.assertEqual(rep.donor_file_sizes.get("fx3_cp"), 15_980_568)
            self.assertEqual(rep.donor_file_sizes.get("fx6_cp"), 17_952_816)
            self.assertEqual(rep.donor_file_sizes.get("fx3_backup"), 2_229_740)
            self.assertEqual(rep.donor_file_sizes.get("fx6_backup"), 2_253_333)
            self.assertEqual(rep.donor_file_sizes.get("mew_bin"), 6_692_572)
            self.assertEqual(rep.donor_file_sizes.get("darwin_core_bin"), 126_956)

    def test_03_forced_clean_room_env_flag_respected(self) -> None:
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}, clear=False):
            rep = analyze_realhw_cp_rtos_and_backup_bin()
        self.assertTrue(rep.all_checks_passed, rep.errors)
        self.assertEqual(rep.mode, "CLEAN_ROOM_SYNTHETIC")

    def test_04_missing_donor_falls_back_to_clean_room(self) -> None:
        with mock.patch(
            "fx3_firmware_lab.realhw_cp_rtos_and_backup_bin_auditor.resolve_donor_file",
            return_value=None,
        ):
            rep = analyze_realhw_cp_rtos_and_backup_bin(clean_room=False)
        self.assertTrue(rep.all_checks_passed, rep.errors)
        self.assertEqual(rep.mode, "CLEAN_ROOM_SYNTHETIC")

    def test_05_json_serialization_has_zero_bytes_repr(self) -> None:
        rep = analyze_realhw_cp_rtos_and_backup_bin(clean_room=True)
        payload = realhw_cp_rtos_and_backup_bin_report_to_dict(rep)
        json_str = json.dumps(payload, sort_keys=True)
        self.assertIsNone(_BYTES_REPR_RE.search(json_str), "Unexpected Python bytes repr in JSON")
        self.assertIn(PHASE_137_SCHEMA, json_str)

    def test_06_auditor_source_strictly_uses_os_o_rdonly_and_mmap_access_read(self) -> None:
        src = _AUDITOR_PATH.read_text(encoding="utf-8")
        self.assertIn("os.O_RDONLY", src)
        self.assertIn("mmap.ACCESS_READ", src)
        for forbidden in (
            "os.O_WRONLY",
            "os.O_RDWR",
            "os.O_CREAT",
            "mmap.ACCESS_WRITE",
            ".write_bytes(",
            ".write_text(",
        ):
            self.assertNotIn(forbidden, src)
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr in (
                "O_WRONLY",
                "O_RDWR",
                "O_CREAT",
                "ACCESS_WRITE",
            ):
                self.fail(f"Forbidden write attribute {node.attr} in auditor AST")

    def test_07_package_exports_and_all_include_phase137_symbols(self) -> None:
        expected_symbols = (
            "PHASE_137_SCHEMA",
            "PHASE_137_VERSION",
            "CP_LOAD_BASE",
            "CP_IDENTICAL_PREFIX_BYTES",
            "CP_ARM32_ENTRY_WORDS",
            "FX6_EXCLUSIVE_CP_MARKERS",
            "SHARED_CP_RTOS_MARKERS",
            "EXPECTED_FX3_SUBSYSTEMS",
            "EXPECTED_FX6_SUBSYSTEMS",
            "EXPECTED_LDR_BKUP_KEY_COUNT",
            "RealhwCpRtosAndBackupBinReport",
            "analyze_realhw_cp_rtos_and_backup_bin",
            "build_clean_room_realhw_cp_backup_fixtures",
            "evaluate_cp_rtos_compatibility",
            "evaluate_route1_vs_route2_architecture",
            "evaluate_boot_descriptor_diff",
            "evaluate_per_body_calibration_policy",
            "evaluate_phase137_write_guard",
            "parse_dual_bk4_and_descriptors",
            "parse_tomco_text",
            "parse_kemco_text",
            "realhw_cp_rtos_and_backup_bin_report_to_dict",
        )
        for sym in expected_symbols:
            self.assertTrue(hasattr(lab, sym), f"Missing export {sym} on fx3_firmware_lab")
            self.assertIn(sym, lab.__all__, f"Missing {sym} in fx3_firmware_lab.__all__")

    def test_08_clean_room_fixtures_roundtrip_and_counts(self) -> None:
        fx = build_clean_room_realhw_cp_backup_fixtures()
        self.assertEqual(len(fx), 18)
        self.assertEqual(fx["fx3_cp"][:CP_IDENTICAL_PREFIX_BYTES], fx["fx6_cp"][:CP_IDENTICAL_PREFIX_BYTES])
        b3, b3_0, b3_1 = parse_dual_bk4_and_descriptors(fx["fx3_backup"], body="FX3_SYNTH")
        b6, b6_0, b6_1 = parse_dual_bk4_and_descriptors(fx["fx6_backup"], body="FX6_SYNTH")
        self.assertEqual(b3.rec0_subsystems, 819)
        self.assertEqual(b6.rec0_subsystems, 840)
        self.assertTrue(b3.rec0_checksum_valid and b3.rec1_checksum_valid)
        self.assertTrue(b6.rec0_checksum_valid and b6.rec1_checksum_valid)
        self.assertEqual(len(b3_0), 9)
        self.assertEqual(len(b6_0), 5)
        self.assertEqual(len(b3_1), 11)
        self.assertEqual(len(b6_1), 10)

    def test_09_cli_audit_realhw_cp_backup_clean_room_and_auto(self) -> None:
        for argv in (["audit-realhw-cp-backup", "--clean-room", "--json"], ["audit-realhw-cp-backup", "--json"]):
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = cli_main(argv)
            self.assertEqual(rc, 0)
            obj = json.loads(buf.getvalue())
            self.assertTrue(obj["all_checks_passed"])
            self.assertFalse(obj["persistent_emmc_writes_authorized"])
            self.assertFalse(obj["spi_nor_write_authorized"])

    def test_10_run_audit_all_reaches_27_auditors(self) -> None:
        summary = run_audit_all(clean_room=True)
        self.assertTrue(summary["all_checks_passed"])
        audit_keys = [k for k in summary if k.endswith("_audit")]
        self.assertGreaterEqual(len(audit_keys), 27)
        self.assertIn("realhw_cp_rtos_and_backup_bin_audit", summary)

    def test_11_cli_audit_all_clean_room_returns_zero_with_27_keys(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cli_main(["audit-all", "--clean-room", "--json"])
        self.assertEqual(rc, 0)
        obj = json.loads(buf.getvalue())
        self.assertTrue(obj["all_checks_passed"])
        self.assertGreaterEqual(len([k for k in obj if k.endswith("_audit")]), 27)

    # ---- Pillar 1: Unknown U2 cpapp-b.bin CP RTOS & Cmdline Divergence ----

    def test_12_cp_arm32_startup_vector_and_load_base(self) -> None:
        rep = analyze_realhw_cp_rtos_and_backup_bin(clean_room=True)
        expected = tuple(f"0x{w:08x}" for w in CP_ARM32_ENTRY_WORDS)
        p1 = rep.pillar1_cp_rtos_divergence
        self.assertEqual(p1.fx3_cp.load_base_hex, f"0x{CP_LOAD_BASE:08x}")
        self.assertEqual(p1.fx6_cp.load_base_hex, f"0x{CP_LOAD_BASE:08x}")
        self.assertEqual(p1.fx3_cp.arm32_entry_words_hex, expected)
        self.assertEqual(p1.fx6_cp.arm32_entry_words_hex, expected)

    def test_13_cp_128k_prefix_identical_across_fx3_and_fx6(self) -> None:
        rep = analyze_realhw_cp_rtos_and_backup_bin(clean_room=True)
        p1 = rep.pillar1_cp_rtos_divergence
        self.assertTrue(p1.prefix_128k_identical)
        self.assertEqual(p1.fx3_cp.prefix_128k_sha256, p1.fx6_cp.prefix_128k_sha256)

    def test_14_fx6_exclusive_peripheral_markers_zero_in_fx3(self) -> None:
        rep = analyze_realhw_cp_rtos_and_backup_bin(clean_room=True)
        p1 = rep.pillar1_cp_rtos_divergence
        for m in FX6_EXCLUSIVE_CP_MARKERS:
            self.assertEqual(p1.fx3_cp.exclusive_marker_counts[m], 0)
            self.assertGreater(p1.fx6_cp.exclusive_marker_counts[m], 0)

    def test_15_shared_cxd90057_toppers_imx510_markers_present(self) -> None:
        rep = analyze_realhw_cp_rtos_and_backup_bin(clean_room=True)
        p1 = rep.pillar1_cp_rtos_divergence
        for m in SHARED_CP_RTOS_MARKERS:
            self.assertGreater(p1.fx3_cp.shared_marker_counts[m], 0)
            self.assertGreater(p1.fx6_cp.shared_marker_counts[m], 0)

    def test_16_tomco_memcfg_pools_total_1724_mib_and_shared_irqs(self) -> None:
        rep = analyze_realhw_cp_rtos_and_backup_bin(clean_room=True)
        p1 = rep.pillar1_cp_rtos_divergence
        self.assertEqual(p1.fx3_tomco.memcfg_pools, EXPECTED_TOMCO_MEMCFG_POOLS)
        self.assertEqual(p1.fx6_tomco.memcfg_pools, EXPECTED_TOMCO_MEMCFG_POOLS)
        self.assertEqual(p1.fx3_tomco.memcfg_total_mib, EXPECTED_TOMCO_TOTAL_MIB)
        self.assertEqual(p1.fx6_tomco.memcfg_total_mib, EXPECTED_TOMCO_TOTAL_MIB)
        self.assertEqual(p1.fx3_tomco.mpcp_exception_int_no, 296)
        self.assertEqual(p1.fx3_tomco.reset_req_int_no, 307)
        self.assertEqual(p1.fx3_tomco.uart_baudrate, 460800)

    def test_17_tomco_fx3_vs_fx6_wdt_and_xreset_divergence(self) -> None:
        rep = analyze_realhw_cp_rtos_and_backup_bin(clean_room=True)
        p1 = rep.pillar1_cp_rtos_divergence
        self.assertEqual(p1.fx3_tomco.wdt_on, 1)
        self.assertEqual(p1.fx6_tomco.wdt_on, 0)
        self.assertEqual(p1.fx6_tomco.exception_reboot, "Y")
        self.assertEqual(p1.fx6_tomco.xreset_req_port, "0:22")
        self.assertIsNone(p1.fx3_tomco.xreset_req_port)

    def test_18_kemco_uart_led_gpio_wbimem_divergence(self) -> None:
        rep = analyze_realhw_cp_rtos_and_backup_bin(clean_room=True)
        p1 = rep.pillar1_cp_rtos_divergence
        self.assertEqual(p1.fx3_kemco.cfg_uart, 1)
        self.assertEqual(p1.fx6_kemco.cfg_uart, 9)
        self.assertEqual(p1.fx3_kemco.error_led, "18,0")
        self.assertEqual(p1.fx6_kemco.error_led, "13,3")
        self.assertEqual(p1.fx6_kemco.error_led_2, "13,1")
        self.assertEqual(p1.fx6_kemco.gpio_port, "0x5")
        self.assertEqual(p1.fx3_kemco.wbimem_large_pool, "0x00BA0000@0x410524000")
        self.assertEqual(p1.fx6_kemco.wbimem_large_pool, "0x01919000@0x410524000")

    def test_19_evaluate_cp_rtos_compat_route1_stock_fx3_passes(self) -> None:
        ev = evaluate_cp_rtos_compatibility(
            target_body="ILME_FX3",
            cp_source_body="FX3_STOCK_702",
            route="ROUTE_1_HYBRID_STAGE_B",
            kemco_uart=1,
            has_darwin_nd_driver=False,
            has_mew_fpga_driver=False,
        )
        self.assertTrue(ev.valid)
        self.assertEqual(ev.status, "FX3_STOCK_CP_RTOS_VERIFIED")
        self.assertTrue(ev.uart_match)
        self.assertEqual(ev.hardware_faults, ())

    def test_20_evaluate_cp_rtos_compat_blocks_fx6_cp_uart_darwin_mew(self) -> None:
        bad_cp = evaluate_cp_rtos_compatibility(
            target_body="ILME_FX3",
            cp_source_body="FX6_STOCK_601",
            route="ROUTE_2_FULL_FX6_NAND_NOR",
            kemco_uart=9,
            has_darwin_nd_driver=True,
            has_mew_fpga_driver=True,
        )
        self.assertFalse(bad_cp.valid)
        self.assertFalse(bad_cp.uart_match)
        self.assertIn("AP_CP_KEMCO_UART_MISMATCH", bad_cp.hardware_faults)
        self.assertIn("DARWIN_ELECTRONIC_ND_ABSENT_ON_FX3", bad_cp.hardware_faults)
        self.assertIn("MEW_12G_SDI_FPGA_ABSENT_ON_FX3", bad_cp.hardware_faults)

    def test_21_evaluate_cp_rtos_compat_rejects_unknown_route(self) -> None:
        with self.assertRaises(ValueError):
            evaluate_cp_rtos_compatibility(route="ROUTE_99_INVALID")

    # ---- Pillar 2: Route-1 vs Route-2 Architecture & Brick Hazards ----

    def test_22_nor_loader_writer_markers_verified(self) -> None:
        rep = analyze_realhw_cp_rtos_and_backup_bin(clean_room=True)
        p2 = rep.pillar2_route_architecture
        self.assertTrue(all(p2.nor_loader_writer_markers.values()))
        self.assertIn("0x51", p2.nor_loader_writer_markers)
        self.assertIn("0x92", p2.nor_loader_writer_markers)

    def test_23_spi_fpga_and_darwin_nd_updater_markers_verified(self) -> None:
        rep = analyze_realhw_cp_rtos_and_backup_bin(clean_room=True)
        p2 = rep.pillar2_route_architecture
        self.assertTrue(all(p2.us_spi_firmup_markers.values()))
        self.assertTrue(all(p2.us_darwin_firm_markers.values()))
        self.assertTrue(p2.us_spi_firmup_markers["0x68"])
        self.assertTrue(p2.us_darwin_firm_markers["0x63"])

    def test_24_pformat_config_six_boot_images_present(self) -> None:
        rep = analyze_realhw_cp_rtos_and_backup_bin(clean_room=True)
        self.assertEqual(len(rep.pillar2_route_architecture.pformat_files), 6)
        self.assertIn("loader_nor.bin", rep.pillar2_route_architecture.pformat_files)
        self.assertIn("cpapp-b.bin", rep.pillar2_route_architecture.pformat_files)

    def test_25_route1_hybrid_stage_b_preserves_imx510_and_zero_brick_hazard(self) -> None:
        r1 = evaluate_route1_vs_route2_architecture(route="ROUTE_1_HYBRID_STAGE_B")
        self.assertTrue(r1.valid)
        self.assertTrue(r1.native_imx510_isp_preserved)
        self.assertTrue(r1.usr_overlay_reversible)
        self.assertFalse(r1.spi_nor_brick_hazard)
        self.assertFalse(r1.fpga_mew_mismatch_hazard)
        self.assertFalse(r1.darwin_nd_fault_hazard)
        self.assertFalse(r1.calibration_overwrite_hazard)

    def test_26_route2_and_non_stock_partitions_blocked(self) -> None:
        r2 = evaluate_route1_vs_route2_architecture(
            route="ROUTE_2_FULL_FX6_NAND_NOR",
            loader_nor_source="FX6_LOADER_NOR",
            p3_kernel_source="FX6_P3_KERNEL",
            p8_cp_rtos_source="FX6_P8_CPAPP",
            p2_backup_source="FX6_P2_BACKUP_BIN",
            usr_overlay_reversible=False,
        )
        self.assertFalse(r2.valid)
        self.assertEqual(r2.status, "BLOCKED_ROUTE2_SPI_NOR_AND_FPGA_BRICK_HAZARD")
        self.assertTrue(r2.spi_nor_brick_hazard)
        self.assertTrue(r2.fpga_mew_mismatch_hazard)
        self.assertTrue(r2.darwin_nd_fault_hazard)
        self.assertTrue(r2.calibration_overwrite_hazard)
        self.assertFalse(r2.native_imx510_isp_preserved)

        # Non-reversible overlay on Route-1 must also fail
        non_rev = evaluate_route1_vs_route2_architecture(
            route="ROUTE_1_HYBRID_STAGE_B",
            usr_overlay_reversible=False,
        )
        self.assertFalse(non_rev.valid)

    def test_27_route_eval_rejects_unknown_route(self) -> None:
        with self.assertRaises(ValueError):
            evaluate_route1_vs_route2_architecture(route="ROUTE_UNKNOWN")

    # ---- Pillar 3: Unknown U3 Backup.bin 819->840 & 0x00fa0080 ----

    def test_28_fx3_bk4_dual_record_819_subsystems_and_checksums(self) -> None:
        rep = analyze_realhw_cp_rtos_and_backup_bin(clean_room=True)
        b3 = rep.pillar3_backup_layout.fx3_bk4
        self.assertEqual(b3.rec0_subsystems, EXPECTED_FX3_SUBSYSTEMS)
        self.assertEqual(b3.rec1_subsystems, EXPECTED_FX3_SUBSYSTEMS)
        self.assertTrue(b3.rec0_checksum_valid)
        self.assertTrue(b3.rec1_checksum_valid)

    def test_29_fx6_bk4_dual_record_840_subsystems_and_checksums(self) -> None:
        rep = analyze_realhw_cp_rtos_and_backup_bin(clean_room=True)
        b6 = rep.pillar3_backup_layout.fx6_bk4
        self.assertEqual(b6.rec0_subsystems, EXPECTED_FX6_SUBSYSTEMS)
        self.assertEqual(b6.rec1_subsystems, EXPECTED_FX6_SUBSYSTEMS)
        self.assertTrue(b6.rec0_checksum_valid)
        self.assertTrue(b6.rec1_checksum_valid)

    def test_30_bk4_parser_detects_corrupt_checksum_and_truncated_input(self) -> None:
        fx = build_clean_room_realhw_cp_backup_fixtures()
        corrupt = bytearray(fx["fx3_backup"])
        corrupt[100] ^= 0xFF
        summary, _, _ = parse_dual_bk4_and_descriptors(bytes(corrupt), body="CORRUPT")
        self.assertFalse(summary.rec0_checksum_valid)

        with self.assertRaises(ValueError):
            parse_dual_bk4_and_descriptors(b"SHORT", body="SHORT")

    def test_31_bank0_ap_slots_identical_and_fx3_bt_wole_slots_present(self) -> None:
        rep = analyze_realhw_cp_rtos_and_backup_bin(clean_room=True)
        p3 = rep.pillar3_backup_layout
        self.assertTrue(p3.descriptor_diff.bank0_core_ap_identical)
        self.assertEqual(p3.descriptor_diff.fx3_bank0_count, 9)
        self.assertEqual(p3.descriptor_diff.fx6_bank0_count, 5)
        fx3_paths = [s.path for s in p3.fx3_bank0_slots]
        self.assertIn("\\bt_conf.cnf", fx3_paths)
        self.assertIn("\\wole_app.bin", fx3_paths)

    def test_32_bank1_identical_core_cp_entries_verified(self) -> None:
        rep = analyze_realhw_cp_rtos_and_backup_bin(clean_room=True)
        ident = rep.pillar3_backup_layout.descriptor_diff.bank1_identical_paths
        for path in ("\\sabin\\idt_cam.bin", "\\bonobo.bin", "\\tomco.txt", "\\cpapp-b.bin"):
            self.assertIn(path, ident)

    def test_33_bank1_ddr_shifts_0x14000_and_0xe0000_exact(self) -> None:
        rep = analyze_realhw_cp_rtos_and_backup_bin(clean_room=True)
        deltas = rep.pillar3_backup_layout.descriptor_diff.bank1_shifted_deltas_hex
        self.assertEqual(deltas["\\DmmCfg.bin"], "+0x14000")
        self.assertEqual(deltas["\\defdet.bin"], "+0x14000")
        self.assertEqual(deltas["\\OldAmtCL.bin"], "+0xe0000")
        self.assertEqual(deltas["\\psd.bin"], "+0xe0000")
        self.assertEqual(deltas["\\lensfile.bin"], "+0xe0000")

    def test_34_bank1_partition_and_file_forks_verified(self) -> None:
        rep = analyze_realhw_cp_rtos_and_backup_bin(clean_room=True)
        forks = rep.pillar3_backup_layout.descriptor_diff.bank1_forked_paths
        self.assertIn("\\cpImg.dat", forks)
        self.assertIn("\\SysSound.bin", forks)
        self.assertIn("\\cmrbnb.bin", forks)
        self.assertTrue(forks["\\cpImg.dat"].startswith("FX3_ONLY"))
        self.assertTrue(forks["\\cmrbnb.bin"].startswith("FX6_ONLY"))

    def test_35_bank1_ddr_non_overlap_positive_and_negative(self) -> None:
        rep = analyze_realhw_cp_rtos_and_backup_bin(clean_room=True)
        diff = rep.pillar3_backup_layout.descriptor_diff
        self.assertTrue(diff.valid)
        self.assertTrue(diff.fx3_bank1_ddr_non_overlapping)
        self.assertTrue(diff.fx6_bank1_ddr_non_overlapping)

        # Negative test: overlapping Bank 1 DDR slot must fail
        p3 = rep.pillar3_backup_layout
        overlapping_fx3_b1 = list(p3.fx3_bank1_slots)
        overlapping_fx3_b1[-1] = BootDescriptorSlot(
            slot_index=10,
            partition=18,
            mode_hex="0x05000000",
            start_addr_hex="0x808730000",  # overlaps \psd.bin!
            end_addr_hex="0x808800000",
            path="\\lensfile.bin",
            span_bytes=0xD0001,
        )
        bad_diff = evaluate_boot_descriptor_diff(
            fx3_bank0=p3.fx3_bank0_slots,
            fx6_bank0=p3.fx6_bank0_slots,
            fx3_bank1=overlapping_fx3_b1,
            fx6_bank1=p3.fx6_bank1_slots,
        )
        self.assertFalse(bad_diff.valid)
        self.assertFalse(bad_diff.fx3_bank1_ddr_non_overlapping)

    def test_36_ldr_bkup_list_big_backup_and_ud_keep_backup_verified(self) -> None:
        rep = analyze_realhw_cp_rtos_and_backup_bin(clean_room=True)
        p3 = rep.pillar3_backup_layout
        self.assertEqual(p3.ldr_bkup_key_count, EXPECTED_LDR_BKUP_KEY_COUNT)
        self.assertEqual(p3.ldr_bkup_prefixes, EXPECTED_LDR_BKUP_PREFIXES)
        self.assertEqual(p3.big_backup_paths, EXPECTED_BIG_BACKUP_PATHS)
        self.assertTrue(all(p3.ud_keep_backup_markers.values()))

    def test_37_per_body_calibration_policy_positive(self) -> None:
        ok = evaluate_per_body_calibration_policy(
            target_body="ILME_FX3",
            preserve_factory_backup_bin=True,
            preserve_psd_and_defdet=True,
            use_ud_keep_backup_r_merge=True,
            cross_camera_raw_flash_attempted=False,
            ldr_bkup_key_count=EXPECTED_LDR_BKUP_KEY_COUNT,
        )
        self.assertTrue(ok.valid)
        self.assertEqual(ok.status, "PER_BODY_CALIBRATION_PRESERVED")

    def test_38_per_body_calibration_policy_blocks_cross_camera_and_missing_merge(self) -> None:
        bad = evaluate_per_body_calibration_policy(
            target_body="ILME_FX3",
            preserve_factory_backup_bin=False,
            preserve_psd_and_defdet=False,
            use_ud_keep_backup_r_merge=False,
            cross_camera_raw_flash_attempted=True,
            ldr_bkup_key_count=10,
        )
        self.assertFalse(bad.valid)
        self.assertEqual(bad.status, "BLOCKED_CROSS_CAMERA_CALIBRATION_DESTRUCTION")
        self.assertGreaterEqual(len(bad.errors), 5)

    # ---- Pillar 4: Volatile RAM Staging & Zero eMMC / SPI NOR Write Auth ----

    def test_39_zero_emmc_and_spi_nor_authorization_flags(self) -> None:
        rep = analyze_realhw_cp_rtos_and_backup_bin(clean_room=True)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.spi_nor_write_authorized)
        p4 = rep.pillar4_zero_flash_auth
        self.assertFalse(p4.persistent_emmc_writes_authorized)
        self.assertFalse(p4.spi_nor_write_authorized)
        self.assertEqual(p4.emmc_mutation_bytes, 0)
        self.assertEqual(p4.spi_nor_mutation_bytes, 0)
        self.assertEqual(p4.calibration_mutation_bytes, 0)

    def test_40_write_guard_allows_volatile_ram_and_tmp_staging(self) -> None:
        for path in ("/tmp/stage_b_cp_shadow.json", "ram://bk4_overlay_shadow", "/ramdsk/rtos_probe.json"):
            res = evaluate_phase137_write_guard(path)
            self.assertTrue(res.valid, f"Unexpectedly blocked {path}")
            self.assertTrue(res.volatile_ram_staged)
            self.assertFalse(res.persistent_write_blocked)

    def test_41_write_guard_blocks_all_emmc_spi_nor_and_calibration_targets(self) -> None:
        for path in (
            "/dev/nflasha8",
            "/dev/nflasha2",
            "/dev/cnflasha0",
            "/dev/mmcblk0p1",
            "/dev/mtd0",
            "spi_nor://loader_nor.bin",
            "p2:/Backup.bin",
            "/setting/psd.bin",
            "/setting/defdet.bin",
            "/lens/lensfile.bin",
            "/1010_spi/mew.bin",
            "/0640_darwin/darwin_core.bin",
        ):
            res = evaluate_phase137_write_guard(path)
            self.assertFalse(res.valid, f"Failed to block forbidden path {path}")
            self.assertTrue(res.persistent_write_blocked)
            self.assertEqual(res.emmc_mutation_bytes, 0)
            self.assertEqual(res.spi_nor_mutation_bytes, 0)

    def test_42_write_guard_blocks_forbidden_filenames_inside_volatile_prefix(self) -> None:
        for sneaky in ("/tmp/Backup.bin", "ram://psd.bin", "/ramdsk/nor_loader_writer"):
            res = evaluate_phase137_write_guard(sneaky)
            self.assertFalse(res.valid, f"Failed to block sneaky path {sneaky}")
            self.assertTrue(res.persistent_write_blocked)


if __name__ == "__main__":
    unittest.main()
