"""Phase 174 Dual-Mode Unit Tests (48 tests): Real-Hardware `p5:/wbi` (`WBI2` /
`hibdrv.ko`) Hibernation Snapshot Isolation, Zero-Write Lock (`wbi_mutation_bytes == 0`),
Stage-A Cold-Boot vs Warm-Boot (`BIS`) Entry Isolation, and Stage-B
`POWEROFF_CLEAN_NO_WBI` Determinism Auditor (`36/36`).
"""

from __future__ import annotations

import ast
import io
import json
import os
import re
import time
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

import fx3_firmware_lab as lab
from fx3_firmware_lab.__main__ import main as cli_main, run_audit_all
from fx3_firmware_lab.realhw_lens_ibis_audio_hdmi_peripheral_bridge_auditor import (
    BRIDGE_CLASS_HARD_WRITE_PROTECTED,
    BRIDGE_CLASS_MASKED_ABSENT_HW,
    BRIDGE_CLASS_NATIVE_PASSTHROUGH,
    BRIDGE_CLASS_SHIM_TRANSLATED,
    EXPECTED_SENCORE_EXPORTS,
    EXPECTED_SENCORE_IMPORTS,
    VALID_BRIDGE_CLASSES,
)
from fx3_firmware_lab.realhw_wbi2_hibdrv_hibernation_isolation_auditor import (
    APPFW_BIS_POWEROFF_MARKERS_P174,
    CPAPP_POWEROFF_MARKERS_P174,
    EXPECTED_FX3_APPFW_BYTES_P174,
    EXPECTED_FX3_BACKUP_BYTES_P174,
    EXPECTED_FX3_CPAPP_BYTES_P174,
    EXPECTED_FX3_IM_ELF_BYTES_P174,
    EXPECTED_FX3_MPR_BYTES_P174,
    EXPECTED_FX3_SENCORE_BYTES_P174,
    EXPECTED_FX3_WBI2_BYTES_P174,
    EXPECTED_FX6_APPFW_BYTES_P174,
    EXPECTED_FX6_BACKUP_BYTES_P174,
    EXPECTED_FX6_CPAPP_BYTES_P174,
    EXPECTED_FX6_IM_ELF_BYTES_P174,
    EXPECTED_FX6_MPR_BYTES_P174,
    EXPECTED_FX6_SENCORE_BYTES_P174,
    EXPECTED_FX6_WBI2_BYTES_P174,
    EXPECTED_IM_ELF_EXPORTS_P174,
    EXPECTED_IM_ELF_IMPORTS_P174,
    FX3_WBIMEM_SPAN_BYTES,
    FX6_WBIMEM_SPAN_BYTES,
    HIBDRV_MODULE_NAME,
    IM_ELF_HIB_MARKERS_P174,
    MPR_POWEROFF_MARKERS_P174,
    P5_WBI_CRYPTO_DEVICE,
    P5_WBI_DEVICE,
    P5_WBI_MOUNT_POINT,
    P5_WBI_PARTITION_BYTES,
    P5_WBI_PHY_DEVICE,
    P5_WBI_SECTORS,
    P5_WBI_START_LBA,
    PHASE_174_SCHEMA,
    PHASE_174_VERSION,
    POWEROFF_CLEAN_NO_WBI_POLICY,
    SENCORE_WBI_MARKERS_P174,
    STAGE_A_ARM_TOKEN_PATH,
    STAGE_A_COLD_ONLY_BOOTARGS,
    STAGE_A_REENTRY_LOCK_PATH,
    STAGE_B_WBI_INHIBIT_LOCK_PATH,
    SYS_POWER_STATE_PATH,
    UPM_BOOTMODE_SYSFS_PATH,
    VALID_POWER_EXIT_MODES,
    VALID_POWER_STATES_REQUESTED,
    VALID_UPM_BOOTMODES,
    WBI2_HIBDRV_IMAGE_MARKERS_P174,
    WBIMEM_COLLISION_DELTA_BYTES,
    WBI_SAVE_INHIBITED_POLICY,
    analyze_realhw_wbi2_hibdrv_hibernation_isolation,
    build_clean_room_realhw_wbi2_hibdrv_fixtures,
    build_phase174_hibernation_isolation_matrix,
    evaluate_p5_wbi2_hibdrv_zero_write_lock,
    evaluate_phase174_write_guard,
    evaluate_stage_a_cold_vs_warm_boot_entry,
    evaluate_stage_b_poweroff_determinism,
    realhw_wbi2_hibdrv_hibernation_isolation_report_to_dict,
)


_BYTES_REPR_RE = re.compile(r"(?<![0-9A-Za-z_/.-])b['\"]")
_AUDITOR_PATH = (
    Path(__file__).resolve().parent.parent
    / "fx3_firmware_lab"
    / "realhw_wbi2_hibdrv_hibernation_isolation_auditor.py"
)


class TestRealhwWbi2HibdrvHibernationIsolation(unittest.TestCase):
    """Comprehensive dual-mode tests (48 tests) for the 36th unified auditor (36/36)."""

    # ---- Mode, Runtime, Determinism & Structural Hygiene ----

    def test_01_clean_room_report_all_pillars_and_runtime(self) -> None:
        t0 = time.perf_counter()
        rep = analyze_realhw_wbi2_hibdrv_hibernation_isolation(clean_room=True)
        dt_cold = time.perf_counter() - t0
        t1 = time.perf_counter()
        rep_warm = analyze_realhw_wbi2_hibdrv_hibernation_isolation(clean_room=True)
        dt_warm = time.perf_counter() - t1

        self.assertTrue(rep.all_checks_passed, rep.errors)
        self.assertEqual(rep.mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(rep.schema_version, PHASE_174_SCHEMA)
        self.assertEqual(rep.phase_version, PHASE_174_VERSION)
        self.assertTrue(rep.o_rdonly_enforced)
        self.assertEqual(rep.wbi_save_policy, WBI_SAVE_INHIBITED_POLICY)
        self.assertTrue(rep.wbi_save_inhibited)
        self.assertEqual(rep.wbi_mutation_bytes, 0)
        self.assertTrue(rep.stock_fx3_wbi2_preserved)
        self.assertTrue(rep.bis_warm_boot_isolated)
        self.assertTrue(rep.poweroff_clean_no_wbi)
        self.assertTrue(rep.stale_ram_cp_carryover_prevented)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.spi_nor_write_authorized)
        self.assertTrue(rep.pillar1_p5_wbi2_zero_write.passed)
        self.assertTrue(rep.pillar2_cold_vs_warm_entry.passed)
        self.assertTrue(rep.pillar3_poweroff_determinism.passed)
        self.assertTrue(rep.pillar4_firewall_matrix.passed)
        self.assertEqual(rep.report_sha256, rep_warm.report_sha256)
        self.assertEqual(len(rep.report_sha256), 64)
        self.assertLess(dt_cold, 0.35)
        self.assertLess(dt_warm, 0.15)

    def test_02_auto_mode_or_local_donor_runtime_under_1500ms(self) -> None:
        t0 = time.perf_counter()
        rep = analyze_realhw_wbi2_hibdrv_hibernation_isolation()
        dt = time.perf_counter() - t0
        self.assertTrue(rep.all_checks_passed, rep.errors)
        self.assertIn(rep.mode, ("LOCAL_DONOR_VERIFIED", "CLEAN_ROOM_SYNTHETIC"))
        self.assertLess(dt, 1.5)
        if rep.mode == "LOCAL_DONOR_VERIFIED":
            self.assertEqual(len(rep.donor_file_sizes), 14)
            self.assertEqual(rep.donor_file_sizes.get("fx3_im_elf"), EXPECTED_FX3_IM_ELF_BYTES_P174)
            self.assertEqual(rep.donor_file_sizes.get("fx6_im_elf"), EXPECTED_FX6_IM_ELF_BYTES_P174)
            self.assertEqual(rep.donor_file_sizes.get("fx3_sencore"), EXPECTED_FX3_SENCORE_BYTES_P174)
            self.assertEqual(rep.donor_file_sizes.get("fx6_sencore"), EXPECTED_FX6_SENCORE_BYTES_P174)
            self.assertEqual(rep.donor_file_sizes.get("fx3_mpr"), EXPECTED_FX3_MPR_BYTES_P174)
            self.assertEqual(rep.donor_file_sizes.get("fx6_mpr"), EXPECTED_FX6_MPR_BYTES_P174)
            self.assertEqual(rep.donor_file_sizes.get("fx3_appfw"), EXPECTED_FX3_APPFW_BYTES_P174)
            self.assertEqual(rep.donor_file_sizes.get("fx6_appfw"), EXPECTED_FX6_APPFW_BYTES_P174)
            self.assertEqual(rep.donor_file_sizes.get("fx3_cpapp"), EXPECTED_FX3_CPAPP_BYTES_P174)
            self.assertEqual(rep.donor_file_sizes.get("fx6_cpapp"), EXPECTED_FX6_CPAPP_BYTES_P174)
            self.assertEqual(rep.donor_file_sizes.get("fx3_backup"), EXPECTED_FX3_BACKUP_BYTES_P174)
            self.assertEqual(rep.donor_file_sizes.get("fx6_backup"), EXPECTED_FX6_BACKUP_BYTES_P174)
            self.assertEqual(rep.donor_file_sizes.get("fx3_wbi2"), EXPECTED_FX3_WBI2_BYTES_P174)
            self.assertEqual(rep.donor_file_sizes.get("fx6_wbi2"), EXPECTED_FX6_WBI2_BYTES_P174)

    def test_03_forced_clean_room_env_flag_respected(self) -> None:
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}, clear=False):
            rep = analyze_realhw_wbi2_hibdrv_hibernation_isolation()
        self.assertTrue(rep.all_checks_passed, rep.errors)
        self.assertEqual(rep.mode, "CLEAN_ROOM_SYNTHETIC")

    def test_04_missing_donor_falls_back_to_clean_room(self) -> None:
        with mock.patch(
            "fx3_firmware_lab.realhw_wbi2_hibdrv_hibernation_isolation_auditor.resolve_donor_file",
            return_value=None,
        ):
            rep = analyze_realhw_wbi2_hibdrv_hibernation_isolation()
        self.assertTrue(rep.all_checks_passed, rep.errors)
        self.assertEqual(rep.mode, "CLEAN_ROOM_SYNTHETIC")

    def test_05_json_serialization_no_raw_bytes_repr_leak(self) -> None:
        rep = analyze_realhw_wbi2_hibdrv_hibernation_isolation(clean_room=True)
        payload = realhw_wbi2_hibdrv_hibernation_isolation_report_to_dict(rep)
        dumped = json.dumps(payload, sort_keys=True)
        self.assertIsNone(_BYTES_REPR_RE.search(dumped), "Unexpected raw bytes repr in JSON")
        self.assertNotIn("BEGIN RSA PRIVATE KEY", dumped)
        self.assertNotIn("BEGIN CERTIFICATE", dumped)
        self.assertIn(PHASE_174_SCHEMA, dumped)

    def test_06_ast_enforces_strictly_o_rdonly_and_zero_writes(self) -> None:
        src = _AUDITOR_PATH.read_text(encoding="utf-8")
        tree = ast.parse(src)
        forbidden_attrs = {"O_WRONLY", "O_RDWR", "O_CREAT", "O_TRUNC", "O_APPEND", "ACCESS_WRITE"}
        forbidden_calls = {"write", "write_bytes", "write_text"}
        os_open_count = 0
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute):
                self.assertNotIn(node.attr, forbidden_attrs)
                if (
                    isinstance(node.value, ast.Name)
                    and node.value.id == "os"
                    and node.attr == "open"
                ):
                    os_open_count += 1
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    self.assertNotEqual(node.func.id, "open")
                elif isinstance(node.func, ast.Attribute):
                    self.assertNotIn(node.func.attr, forbidden_calls)
        self.assertGreaterEqual(os_open_count, 3)

    def test_07_package_init_exports_and_all(self) -> None:
        required = (
            "PHASE_174_SCHEMA",
            "PHASE_174_VERSION",
            "FX3_WBIMEM_SPAN_BYTES",
            "FX6_WBIMEM_SPAN_BYTES",
            "WBIMEM_COLLISION_DELTA_BYTES",
            "P5_WBI_DEVICE",
            "P5_WBI_CRYPTO_DEVICE",
            "P5_WBI_PHY_DEVICE",
            "P5_WBI_MOUNT_POINT",
            "P5_WBI_PARTITION_BYTES",
            "P5_WBI_START_LBA",
            "P5_WBI_SECTORS",
            "STAGE_B_WBI_INHIBIT_LOCK_PATH",
            "STAGE_A_ARM_TOKEN_PATH",
            "STAGE_A_REENTRY_LOCK_PATH",
            "UPM_BOOTMODE_SYSFS_PATH",
            "SYS_POWER_STATE_PATH",
            "HIBDRV_MODULE_NAME",
            "WBI_SAVE_INHIBITED_POLICY",
            "POWEROFF_CLEAN_NO_WBI_POLICY",
            "STAGE_A_COLD_ONLY_BOOTARGS",
            "Wbi2HeaderSnapshotSummary",
            "BackupBinHeaderSummary",
            "P5Wbi2ZeroWriteEvalResult",
            "StageAColdVsWarmBootEvalResult",
            "StageBPoweroffDeterminismEvalResult",
            "Phase174WriteGuardResult",
            "Phase174TouchpointEntry",
            "Phase174CompatMatrixSummary",
            "Pillar1P5Wbi2ZeroWriteReport",
            "Pillar2ColdVsWarmEntryReport",
            "Pillar3PoweroffDeterminismReport",
            "Pillar4WbiFirewallMatrixReport",
            "RealhwWbi2HibdrvHibernationIsolationReport",
            "evaluate_p5_wbi2_hibdrv_zero_write_lock",
            "evaluate_stage_a_cold_vs_warm_boot_entry",
            "evaluate_stage_b_poweroff_determinism",
            "evaluate_phase174_write_guard",
            "build_phase174_hibernation_isolation_matrix",
            "build_clean_room_realhw_wbi2_hibdrv_fixtures",
            "analyze_realhw_wbi2_hibdrv_hibernation_isolation",
            "realhw_wbi2_hibdrv_hibernation_isolation_report_to_dict",
        )
        for name in required:
            self.assertTrue(hasattr(lab, name), f"Missing export {name} in fx3_firmware_lab")
            self.assertIn(name, lab.__all__, f"Missing {name} in fx3_firmware_lab.__all__")

    def test_08_run_audit_all_and_cli_integration_36_of_36(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cli_main(["audit-realhw-wbi2-hibdrv-isolation", "--clean-room", "--json"])
        self.assertEqual(rc, 0)
        parsed = json.loads(buf.getvalue())
        self.assertTrue(parsed["all_checks_passed"])
        self.assertEqual(parsed["schema_version"], PHASE_174_SCHEMA)
        self.assertFalse(parsed["persistent_emmc_writes_authorized"])
        self.assertFalse(parsed["spi_nor_write_authorized"])
        self.assertEqual(parsed["wbi_mutation_bytes"], 0)
        self.assertTrue(parsed["wbi_save_inhibited"])
        self.assertTrue(parsed["stock_fx3_wbi2_preserved"])
        self.assertTrue(parsed["bis_warm_boot_isolated"])
        self.assertTrue(parsed["poweroff_clean_no_wbi"])
        self.assertTrue(parsed["stale_ram_cp_carryover_prevented"])

        all_summary = run_audit_all(clean_room=True)
        self.assertTrue(all_summary["all_checks_passed"])
        self.assertIn("realhw_wbi2_hibdrv_hibernation_isolation_audit", all_summary)
        audit_keys = [k for k in all_summary.keys() if k.endswith("_audit")]
        self.assertGreaterEqual(len(audit_keys), 36)

    def test_09_cli_audit_all_clean_room_smoke(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cli_main(["audit-all", "--clean-room", "--json"])
        self.assertEqual(rc, 0)
        parsed = json.loads(buf.getvalue())
        self.assertTrue(parsed["all_checks_passed"])
        self.assertIn("realhw_wbi2_hibdrv_hibernation_isolation_audit", parsed)

    def test_10_clean_room_fixtures_structure_valid(self) -> None:
        fx = build_clean_room_realhw_wbi2_hibdrv_fixtures()
        expected_keys = {
            "fx3_im_elf",
            "fx6_im_elf",
            "fx3_sencore",
            "fx6_sencore",
            "fx3_mpr",
            "fx6_mpr",
            "fx3_appfw",
            "fx6_appfw",
            "fx3_cpapp",
            "fx6_cpapp",
            "fx3_backup",
            "fx6_backup",
            "fx3_wbi2",
            "fx6_wbi2",
        }
        self.assertEqual(set(fx.keys()), expected_keys)
        for k, blob in fx.items():
            self.assertGreater(len(blob), 8, k)
            if k in ("fx3_im_elf", "fx6_im_elf", "fx3_sencore", "fx6_sencore", "fx3_mpr", "fx6_mpr", "fx3_appfw", "fx6_appfw"):
                self.assertEqual(blob[:4], b"\x7fELF", k)
            elif k in ("fx3_backup", "fx6_backup"):
                self.assertEqual(blob[12:16], b"BK4\x00", k)
            elif k in ("fx3_wbi2", "fx6_wbi2"):
                self.assertEqual(blob[:4], b"WBI2", k)

    # ---- Pillar 1: p5:/wbi (WBI2 / hibdrv.ko) Zero-Write Lock ----

    def test_11_pillar1_wbi2_headers_and_sencore_markers(self) -> None:
        rep = analyze_realhw_wbi2_hibdrv_hibernation_isolation(clean_room=True)
        p1 = rep.pillar1_p5_wbi2_zero_write
        self.assertTrue(p1.passed, p1.errors)
        self.assertEqual(p1.fx3_wbi2_summary.magic_ascii, "WBI2")
        self.assertEqual(p1.fx6_wbi2_summary.magic_ascii, "WBI2")
        self.assertNotEqual(p1.fx3_wbi2_summary.resume_vector_hex, p1.fx6_wbi2_summary.resume_vector_hex)
        self.assertEqual(p1.fx3_sencore_summary.export_count, EXPECTED_SENCORE_EXPORTS)
        self.assertEqual(p1.fx3_sencore_summary.import_count, EXPECTED_SENCORE_IMPORTS)
        self.assertEqual(p1.fx6_sencore_summary.export_count, EXPECTED_SENCORE_EXPORTS)
        self.assertEqual(p1.fx6_sencore_summary.import_count, EXPECTED_SENCORE_IMPORTS)
        for m in SENCORE_WBI_MARKERS_P174:
            self.assertGreater(p1.fx3_sencore_summary.marker_hits[m], 0)
            self.assertGreater(p1.fx6_sencore_summary.marker_hits[m], 0)
        for m in WBI2_HIBDRV_IMAGE_MARKERS_P174:
            self.assertGreater(p1.fx3_wbi2_summary.hibdrv_marker_hits[m], 0)
            self.assertGreater(p1.fx6_wbi2_summary.hibdrv_marker_hits[m], 0)

    def test_12_pillar1_local_donor_wbi2_section_counts_if_present(self) -> None:
        rep = analyze_realhw_wbi2_hibdrv_hibernation_isolation()
        if rep.mode != "LOCAL_DONOR_VERIFIED":
            self.skipTest("Local Sony donor images absent; tested cleanly in synthetic mode")
        p1 = rep.pillar1_p5_wbi2_zero_write
        self.assertEqual(p1.fx3_wbi2_summary.sections, 1399)
        self.assertEqual(p1.fx3_wbi2_summary.zero_sections, 82)
        self.assertEqual(p1.fx3_wbi2_summary.resume_vector_hex, "0x4004a67f0")
        self.assertEqual(p1.fx6_wbi2_summary.sections, 1197)
        self.assertEqual(p1.fx6_wbi2_summary.zero_sections, 54)
        self.assertEqual(p1.fx6_wbi2_summary.resume_vector_hex, "0x4004a87f0")
        self.assertEqual(p1.fx3_wbi2_summary.dversion_hex, "0x20060224")
        self.assertEqual(p1.fx6_wbi2_summary.dversion_hex, "0x20060224")

    def test_13_wbimem_collision_delta_positive_13_47_mib(self) -> None:
        self.assertEqual(FX3_WBIMEM_SPAN_BYTES, 0x00BA0000)
        self.assertEqual(FX6_WBIMEM_SPAN_BYTES, 0x01919000)
        self.assertEqual(WBIMEM_COLLISION_DELTA_BYTES, 0x00D79000)
        self.assertEqual(WBIMEM_COLLISION_DELTA_BYTES, 14_127_104)

    def test_14_stage_b_wbi_save_inhibit_nominal_unmounted(self) -> None:
        res = evaluate_p5_wbi2_hibdrv_zero_write_lock()
        self.assertTrue(res.valid, res.errors)
        self.assertTrue(res.wbi_save_inhibited)
        self.assertEqual(res.wbi_mutation_bytes, 0)
        self.assertEqual(res.wbi_save_policy, WBI_SAVE_INHIBITED_POLICY)
        self.assertEqual(res.wbi_inhibit_lock_path, STAGE_B_WBI_INHIBIT_LOCK_PATH)
        self.assertTrue(res.cross_kernel_wbi_blocked)
        self.assertTrue(res.stock_fx3_wbi2_preserved)
        self.assertTrue(res.sd_removed_stock_boot_clean)

    def test_15_stage_b_wbi_save_inhibit_p5_ro_allowed(self) -> None:
        res = evaluate_p5_wbi2_hibdrv_zero_write_lock(p5_mount_mode="MS_RDONLY")
        self.assertTrue(res.valid, res.errors)
        self.assertEqual(res.p5_mount_mode, "MS_RDONLY")
        self.assertEqual(res.wbi_mutation_bytes, 0)
        self.assertTrue(res.stock_fx3_wbi2_preserved)

    def test_16_stage_b_rejects_p5_rdwr_mount(self) -> None:
        res = evaluate_p5_wbi2_hibdrv_zero_write_lock(p5_mount_mode="MS_RDWR")
        self.assertFalse(res.valid)
        self.assertIn("P5_WBI_RDWR_MOUNT_FORBIDDEN", res.errors)
        self.assertEqual(res.wbi_mutation_bytes, 0)
        self.assertFalse(res.stock_fx3_wbi2_preserved)

    def test_17_stage_b_rejects_unknown_p5_mount_mode(self) -> None:
        res = evaluate_p5_wbi2_hibdrv_zero_write_lock(p5_mount_mode="INVALID_RW")
        self.assertFalse(res.valid)
        self.assertTrue(any("UNKNOWN_P5_MOUNT_MODE" in e for e in res.errors))
        self.assertEqual(res.wbi_mutation_bytes, 0)

    def test_18_stage_b_requires_inhibit_lock_when_active(self) -> None:
        res = evaluate_p5_wbi2_hibdrv_zero_write_lock(
            stage_b_active=True,
            wbi_inhibit_lock_active=False,
        )
        self.assertFalse(res.valid)
        self.assertIn("MISSING_STAGE_B_WBI_INHIBIT_LOCK", res.errors)
        self.assertEqual(res.wbi_mutation_bytes, 0)

    def test_19_stage_b_blocks_wbi_snapshot_write_with_zero_bytes(self) -> None:
        res = evaluate_p5_wbi2_hibdrv_zero_write_lock(
            attempt_wbi_snapshot_write=True,
            requested_mutation_bytes=65536,
        )
        self.assertFalse(res.valid)
        self.assertIn("P5_WBI_SNAPSHOT_WRITE_BLOCKED", res.errors)
        self.assertEqual(res.requested_mutation_bytes, 65536)
        self.assertEqual(res.wbi_mutation_bytes, 0)
        self.assertFalse(res.stock_fx3_wbi2_preserved)

    def test_20_stage_b_blocks_cross_kernel_wbi_resume(self) -> None:
        res = evaluate_p5_wbi2_hibdrv_zero_write_lock(attempt_cross_kernel_wbi_resume=True)
        self.assertFalse(res.valid)
        self.assertIn("BLOCKED_CROSS_KERNEL_WBI2_EL1_MISMATCH", res.errors)
        self.assertTrue(res.cross_kernel_wbi_blocked)
        self.assertEqual(res.wbi_mutation_bytes, 0)
        self.assertFalse(res.sd_removed_stock_boot_clean)

    def test_21_sd_card_removed_stock_recovery_verified(self) -> None:
        res = evaluate_p5_wbi2_hibdrv_zero_write_lock(
            stage_b_active=False,
            wbi_inhibit_lock_active=False,
            p5_mount_mode="MS_RDONLY",
            sd_card_removed_after_exit=True,
        )
        self.assertTrue(res.valid, res.errors)
        self.assertTrue(res.stock_fx3_wbi2_preserved)
        self.assertTrue(res.sd_removed_stock_boot_clean)
        self.assertEqual(res.wbi_mutation_bytes, 0)

    def test_22_p5_partition_geometry_constants_pinned(self) -> None:
        self.assertEqual(P5_WBI_DEVICE, "/dev/nflasha5")
        self.assertEqual(P5_WBI_CRYPTO_DEVICE, "/dev/cnflasha5")
        self.assertEqual(P5_WBI_PHY_DEVICE, "/dev/pnflasha5")
        self.assertEqual(P5_WBI_MOUNT_POINT, "/wbi")
        self.assertEqual(P5_WBI_START_LBA, 0x00042000)
        self.assertEqual(P5_WBI_SECTORS, 0x00096000)
        self.assertGreater(P5_WBI_PARTITION_BYTES, FX6_WBIMEM_SPAN_BYTES)
        self.assertEqual(HIBDRV_MODULE_NAME, "hibdrv.ko")

    # ---- Pillar 2: Cold-Boot vs Warm-Boot Stage-A Entry Isolation ----

    def test_23_pillar2_im_elf_abi_and_backup_bk4_verified(self) -> None:
        rep = analyze_realhw_wbi2_hibdrv_hibernation_isolation(clean_room=True)
        p2 = rep.pillar2_cold_vs_warm_entry
        self.assertTrue(p2.passed, p2.errors)
        self.assertEqual(p2.fx3_im_elf_summary.export_count, EXPECTED_IM_ELF_EXPORTS_P174)
        self.assertEqual(p2.fx3_im_elf_summary.import_count, EXPECTED_IM_ELF_IMPORTS_P174)
        self.assertEqual(p2.fx6_im_elf_summary.export_count, EXPECTED_IM_ELF_EXPORTS_P174)
        self.assertEqual(p2.fx6_im_elf_summary.import_count, EXPECTED_IM_ELF_IMPORTS_P174)
        for m in IM_ELF_HIB_MARKERS_P174:
            self.assertGreater(p2.fx3_im_elf_summary.marker_hits[m], 0)
            self.assertGreater(p2.fx6_im_elf_summary.marker_hits[m], 0)
        for m in APPFW_BIS_POWEROFF_MARKERS_P174:
            self.assertGreater(p2.fx3_appfw_bis_hits[m], 0)
            self.assertGreater(p2.fx6_appfw_bis_hits[m], 0)
        self.assertTrue(p2.fx3_backup_summary.header_valid)
        self.assertTrue(p2.fx6_backup_summary.header_valid)
        self.assertEqual(p2.fx3_backup_summary.magic_ascii, "BK4\x00")
        self.assertEqual(p2.fx6_backup_summary.magic_ascii, "BK4\x00")

    def test_24_stage_a_activates_only_on_clean_normal_cold_boot(self) -> None:
        res = evaluate_stage_a_cold_vs_warm_boot_entry(
            upm_bootmode="NORMAL",
            arm_token_present=True,
            reentry_lock_present=False,
            p5_already_mounted=False,
            bootargs=STAGE_A_COLD_ONLY_BOOTARGS,
        )
        self.assertTrue(res.valid, res.errors)
        self.assertTrue(res.stage_a_activated)
        self.assertTrue(res.arm_token_cleared_before_exec)
        self.assertTrue(res.bootargs_noresume_present)
        self.assertTrue(res.bis_warm_boot_isolated)
        self.assertEqual(res.fallback_target, "STAGE_B_FX6_USERLAND")
        self.assertEqual(res.status, "STAGE_A_COLD_BOOT_ACTIVATED")

    def test_25_stage_a_rejects_bis_warm_boot_to_stock_fallback(self) -> None:
        res = evaluate_stage_a_cold_vs_warm_boot_entry(
            upm_bootmode="BIS",
            arm_token_present=True,
        )
        self.assertFalse(res.valid)
        self.assertFalse(res.stage_a_activated)
        self.assertTrue(res.bis_warm_boot_isolated)
        self.assertIn("ERR_WBI_BIS_MODE_FORBIDDEN", res.errors)
        self.assertEqual(res.fallback_target, "STOCK_FX3_FALLBACK")

    def test_26_stage_a_rejects_updater_and_service_bootmodes(self) -> None:
        for bm in ("UPDATER", "SERVICE"):
            res = evaluate_stage_a_cold_vs_warm_boot_entry(
                upm_bootmode=bm,
                arm_token_present=True,
            )
            self.assertFalse(res.valid, bm)
            self.assertFalse(res.stage_a_activated, bm)
            self.assertIn("ERR_NON_NORMAL_BOOTMODE_PASSTHROUGH", res.errors)
            self.assertEqual(res.fallback_target, "STOCK_FX3_FALLBACK")

    def test_27_stage_a_rejects_unknown_bootmode(self) -> None:
        res = evaluate_stage_a_cold_vs_warm_boot_entry(
            upm_bootmode="UNKNOWN_MODE",
            arm_token_present=True,
        )
        self.assertFalse(res.valid)
        self.assertFalse(res.stage_a_activated)
        self.assertTrue(any("INVALID_UPM_BOOTMODE" in e for e in res.errors))

    def test_28_stage_a_rejects_premounted_p5_wbi(self) -> None:
        res = evaluate_stage_a_cold_vs_warm_boot_entry(
            upm_bootmode="NORMAL",
            arm_token_present=True,
            p5_already_mounted=True,
        )
        self.assertFalse(res.valid)
        self.assertFalse(res.stage_a_activated)
        self.assertIn("ERR_WBI_P5_ALREADY_MOUNTED", res.errors)
        self.assertEqual(res.fallback_target, "STOCK_FX3_FALLBACK")

    def test_29_stage_a_blocks_idempotent_reentry_lock(self) -> None:
        res = evaluate_stage_a_cold_vs_warm_boot_entry(
            upm_bootmode="NORMAL",
            arm_token_present=True,
            reentry_lock_present=True,
        )
        self.assertFalse(res.valid)
        self.assertFalse(res.stage_a_activated)
        self.assertFalse(res.arm_token_cleared_before_exec)
        self.assertIn("ERR_IDEMPOTENT_REENTRY_BLOCKED", res.errors)

    def test_30_stage_a_requires_noresume_or_hibdrv_resume_zero(self) -> None:
        res_bad = evaluate_stage_a_cold_vs_warm_boot_entry(
            upm_bootmode="NORMAL",
            arm_token_present=True,
            bootargs=("console=ttyAMA0", "resume=/dev/nflasha5"),
        )
        self.assertFalse(res_bad.valid)
        self.assertFalse(res_bad.stage_a_activated)
        self.assertIn("MISSING_NORESUME_COLD_BOOT_ARG", res_bad.errors)

        res_ok = evaluate_stage_a_cold_vs_warm_boot_entry(
            upm_bootmode="NORMAL",
            arm_token_present=True,
            bootargs=("hibdrv.resume=0",),
        )
        self.assertTrue(res_ok.valid, res_ok.errors)
        self.assertTrue(res_ok.stage_a_activated)

    def test_31_unarmed_cold_boot_passes_cleanly_to_stock_fx3(self) -> None:
        res = evaluate_stage_a_cold_vs_warm_boot_entry(
            upm_bootmode="NORMAL",
            arm_token_present=False,
        )
        self.assertTrue(res.valid, res.errors)
        self.assertFalse(res.stage_a_activated)
        self.assertEqual(res.fallback_target, "STOCK_FX3_UNARMED_COLD_PASSTHROUGH")
        self.assertEqual(res.status, "STOCK_FX3_COLD_BOOT_PASSTHROUGH")

    # ---- Pillar 3: Stage-B Clean Power-Off (POWEROFF_CLEAN_NO_WBI) ----

    def test_32_pillar3_libmpr_and_cpapp_poweroff_markers_verified(self) -> None:
        rep = analyze_realhw_wbi2_hibdrv_hibernation_isolation(clean_room=True)
        p3 = rep.pillar3_poweroff_determinism
        self.assertTrue(p3.passed, p3.errors)
        for m in MPR_POWEROFF_MARKERS_P174:
            self.assertGreater(p3.fx3_mpr_summary.marker_hits[m], 0)
            self.assertGreater(p3.fx6_mpr_summary.marker_hits[m], 0)
        for m in CPAPP_POWEROFF_MARKERS_P174:
            self.assertGreater(p3.fx3_cpapp_poweroff_hits[m], 0)
            self.assertGreater(p3.fx6_cpapp_poweroff_hits[m], 0)

    def test_33_nominal_poweroff_forces_clean_no_wbi_across_all_exit_triggers(self) -> None:
        for trig in VALID_POWER_EXIT_MODES:
            res = evaluate_stage_b_poweroff_determinism(
                exit_trigger=trig,
                requested_power_state="poweroff",
                sd_card_present_on_next_boot=False,
            )
            self.assertTrue(res.valid, f"{trig}: {res.errors}")
            self.assertFalse(res.hibdrv_snapshot_triggered)
            self.assertEqual(res.wbi_mutation_bytes, 0)
            self.assertEqual(res.poweroff_policy, POWEROFF_CLEAN_NO_WBI_POLICY)
            self.assertTrue(res.stale_ram_cp_carryover_prevented)
            self.assertEqual(res.sd_removed_next_boot_mode, "STOCK_FX3_7_02_COLD_BOOT")

    def test_34_sd_present_next_boot_routes_through_stage_a_cold_check(self) -> None:
        res = evaluate_stage_b_poweroff_determinism(
            exit_trigger="POWER_SWITCH_OFF",
            requested_power_state="poweroff",
            sd_card_present_on_next_boot=True,
        )
        self.assertTrue(res.valid, res.errors)
        self.assertEqual(res.sd_removed_next_boot_mode, "STAGE_A_COLD_CHECK")

    def test_35_rejects_disk_mem_and_standby_power_states(self) -> None:
        for bad_state in ("disk", "mem", "standby"):
            res = evaluate_stage_b_poweroff_determinism(requested_power_state=bad_state)
            self.assertFalse(res.valid, bad_state)
            self.assertFalse(res.hibdrv_snapshot_triggered)
            self.assertEqual(res.wbi_mutation_bytes, 0)
            self.assertFalse(res.stale_ram_cp_carryover_prevented)
            self.assertTrue(
                any("HIBERNATION_OR_SUSPEND_STATE_FORBIDDEN_IN_STAGE_B" in e for e in res.errors)
            )

    def test_36_rejects_unknown_exit_trigger_and_power_state(self) -> None:
        res1 = evaluate_stage_b_poweroff_determinism(exit_trigger="MAGIC_RESET")
        self.assertFalse(res1.valid)
        self.assertTrue(any("UNKNOWN_EXIT_TRIGGER" in e for e in res1.errors))

        res2 = evaluate_stage_b_poweroff_determinism(requested_power_state="hibernate_fast")
        self.assertFalse(res2.valid)
        self.assertTrue(any("UNKNOWN_POWER_STATE" in e for e in res2.errors))

    def test_37_cp_handshake_timeout_aborts_cleanly_with_zero_wbi(self) -> None:
        res = evaluate_stage_b_poweroff_determinism(
            exit_trigger="POWER_SWITCH_OFF",
            requested_power_state="poweroff",
            cp_poweroff_handshake_ok=False,
        )
        self.assertFalse(res.valid)
        self.assertIn("CP_POWEROFF_HANDSHAKE_TIMEOUT_SAFE_COLD_ABORT", res.errors)
        self.assertFalse(res.hibdrv_snapshot_triggered)
        self.assertEqual(res.wbi_mutation_bytes, 0)

    def test_38_unflushed_media_or_incomplete_lifo_unmount_or_dirty_tmpfs_rejected(self) -> None:
        r_media = evaluate_stage_b_poweroff_determinism(fsys_media_flushed=False)
        self.assertFalse(r_media.valid)
        self.assertIn("FSYS_ASYNC_MEDIA_NOT_FLUSHED", r_media.errors)

        r_lifo = evaluate_stage_b_poweroff_determinism(lifo_unmount_complete=False)
        self.assertFalse(r_lifo.valid)
        self.assertFalse(r_lifo.stale_ram_cp_carryover_prevented)
        self.assertIn("STAGE_B_LIFO_UNMOUNT_INCOMPLETE", r_lifo.errors)

        r_tmp = evaluate_stage_b_poweroff_determinism(tmpfs_overlay_wiped=False)
        self.assertFalse(r_tmp.valid)
        self.assertFalse(r_tmp.stale_ram_cp_carryover_prevented)
        self.assertIn("TMPFS_RAM_OVERLAY_NOT_WIPED", r_tmp.errors)

    # ---- Pillar 4: Write Firewall & 12-Touchpoint Compatibility Matrix ----

    def test_39_write_firewall_allows_volatile_tmp_and_external_media(self) -> None:
        allowed_paths = (
            STAGE_B_WBI_INHIBIT_LOCK_PATH,
            STAGE_A_ARM_TOKEN_PATH,
            STAGE_A_REENTRY_LOCK_PATH,
            "/tmp/fx6_stage_b/stage_b_state.env",
            "ram://stage_b/shadow_config",
            "memfd:fx6_stage_b_env",
            "/mnt/sd/PRIVATE/M4ROOT/CLIP/C0001.MP4",
            "/mnt/sd2/XDROOT/Clip/C0002.MXF",
            "/mnt/cfexpress_a/PRIVATE/M4ROOT/CLIP/C0003.MP4",
        )
        for path in allowed_paths:
            g = evaluate_phase174_write_guard(path)
            self.assertTrue(g.valid, f"{path}: {g.errors}")
            self.assertTrue(g.volatile_or_ext_allowed)
            self.assertFalse(g.persistent_write_blocked)
            self.assertFalse(g.persistent_emmc_writes_authorized)
            self.assertFalse(g.spi_nor_write_authorized)
            self.assertEqual(g.wbi_mutation_bytes, 0)

    def test_40_write_firewall_blocks_p5_wbi_devices_and_hibdrv(self) -> None:
        blocked = (
            P5_WBI_DEVICE,
            P5_WBI_CRYPTO_DEVICE,
            P5_WBI_PHY_DEVICE,
            "p5:/wbi",
            "p5:/wbi/hiber_img",
            "/wbi",
            "/wbi/snapshot.bin",
            "/lib/modules/hibdrv.ko",
            "/tmp/nflasha5.img",
            SYS_POWER_STATE_PATH,
            UPM_BOOTMODE_SYSFS_PATH,
        )
        for path in blocked:
            g = evaluate_phase174_write_guard(path)
            self.assertFalse(g.valid, f"Expected block for {path}")
            self.assertFalse(g.volatile_or_ext_allowed)
            self.assertTrue(g.persistent_write_blocked)
            self.assertFalse(g.persistent_emmc_writes_authorized)
            self.assertFalse(g.spi_nor_write_authorized)
            self.assertEqual(g.wbi_mutation_bytes, 0)
            self.assertEqual(g.emmc_mutation_bytes, 0)
            self.assertEqual(g.cp_mutation_bytes, 0)

    def test_41_write_firewall_blocks_emmc_nvs_and_spi_nor_partitions(self) -> None:
        blocked = (
            "/dev/nflasha1",
            "/dev/nflasha2",
            "/dev/nflasha8",
            "/dev/cnflasha12",
            "/dev/mmcblk0p1",
            "/dev/mmcblk0rpmb",
            "/dev/rtc0",
            "p2:/Backup.bin",
            "p6:/psd.bin",
            "p8:/cpapp-b.bin",
            "p12:/cert/RQ_LIC.DAT",
            "p13:/rf_cal.bin",
            "p15:/usr/bin/im.elf",
            "p18:/lens/lensfile.bin",
            "/setting/defdet.bin",
            "/cert/RQ_LIC.DAT",
            "/lens/lensfile.bin",
            "spi_nor:/loader_nor.bin",
            "sector0:/gpt",
        )
        for path in blocked:
            g = evaluate_phase174_write_guard(path)
            self.assertFalse(g.valid, f"Expected block for {path}")
            self.assertTrue(g.persistent_write_blocked)
            self.assertFalse(g.persistent_emmc_writes_authorized)
            self.assertFalse(g.spi_nor_write_authorized)
            self.assertEqual(g.status, "BLOCKED_WBI_PERSISTENT_EMMC_OR_SPINOR_TARGET")

    def test_42_write_firewall_fail_closes_unlisted_paths(self) -> None:
        g = evaluate_phase174_write_guard("/usr/bin/appFw.so")
        self.assertFalse(g.valid)
        self.assertTrue(g.persistent_write_blocked)
        self.assertEqual(g.status, "UNLISTED_NON_VOLATILE_TARGET_BLOCKED")
        self.assertFalse(g.persistent_emmc_writes_authorized)
        self.assertFalse(g.spi_nor_write_authorized)

    def test_43_compatibility_matrix_12_touchpoints_and_4_classes(self) -> None:
        matrix = build_phase174_hibernation_isolation_matrix()
        self.assertEqual(matrix.total_touchpoints, 12)
        self.assertEqual(len(matrix.touchpoints), 12)
        self.assertEqual(sum(matrix.class_counts.values()), 12)
        self.assertEqual(sum(matrix.subsystem_counts.values()), 12)
        self.assertEqual(set(matrix.class_counts.keys()), set(VALID_BRIDGE_CLASSES))
        self.assertEqual(matrix.class_counts[BRIDGE_CLASS_HARD_WRITE_PROTECTED], 4)
        self.assertEqual(matrix.class_counts[BRIDGE_CLASS_SHIM_TRANSLATED], 4)
        self.assertEqual(matrix.class_counts[BRIDGE_CLASS_NATIVE_PASSTHROUGH], 3)
        self.assertEqual(matrix.class_counts[BRIDGE_CLASS_MASKED_ABSENT_HW], 1)

    def test_44_compatibility_matrix_ids_unique_and_nonempty_fields(self) -> None:
        matrix = build_phase174_hibernation_isolation_matrix()
        ids = [tp.touchpoint_id for tp in matrix.touchpoints]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(ids, [f"P174-{i:02d}" for i in range(1, 13)])
        for tp in matrix.touchpoints:
            self.assertTrue(tp.subsystem)
            self.assertTrue(tp.fx6_component)
            self.assertTrue(tp.fx3_target)
            self.assertIn(tp.bridge_class, VALID_BRIDGE_CLASSES)
            self.assertTrue(tp.safety_invariant)

    def test_45_catalog_constants_complete_and_immutable(self) -> None:
        self.assertEqual(VALID_UPM_BOOTMODES, ("NORMAL", "BIS", "UPDATER", "SERVICE"))
        self.assertEqual(
            VALID_POWER_STATES_REQUESTED,
            ("poweroff", "disk", "mem", "standby"),
        )
        self.assertEqual(len(VALID_POWER_EXIT_MODES), 4)
        self.assertEqual(len(IM_ELF_HIB_MARKERS_P174), 4)
        self.assertEqual(len(SENCORE_WBI_MARKERS_P174), 4)
        self.assertEqual(len(MPR_POWEROFF_MARKERS_P174), 5)
        self.assertEqual(len(APPFW_BIS_POWEROFF_MARKERS_P174), 3)
        self.assertEqual(len(CPAPP_POWEROFF_MARKERS_P174), 2)
        self.assertEqual(len(WBI2_HIBDRV_IMAGE_MARKERS_P174), 8)

    def test_46_report_to_dict_roundtrip_json_types(self) -> None:
        rep = analyze_realhw_wbi2_hibdrv_hibernation_isolation(clean_room=True)
        d = realhw_wbi2_hibdrv_hibernation_isolation_report_to_dict(rep)
        raw = json.dumps(d)
        back = json.loads(raw)
        self.assertEqual(back["schema_version"], PHASE_174_SCHEMA)
        self.assertEqual(back["wbi_mutation_bytes"], 0)
        self.assertFalse(back["persistent_emmc_writes_authorized"])
        self.assertFalse(back["spi_nor_write_authorized"])
        self.assertEqual(back["pillar4_firewall_matrix"]["compatibility_matrix"]["total_touchpoints"], 12)

    def test_47_clean_room_wbi2_mismatch_verdict_string(self) -> None:
        rep = analyze_realhw_wbi2_hibdrv_hibernation_isolation(clean_room=True)
        self.assertEqual(
            rep.pillar1_p5_wbi2_zero_write.cross_kernel_mismatch_verdict,
            "BLOCKED_CROSS_KERNEL_WBI2_EL1_MISMATCH",
        )
        self.assertEqual(
            rep.pillar1_p5_wbi2_zero_write.wbimem_collision_delta_bytes,
            WBIMEM_COLLISION_DELTA_BYTES,
        )

    def test_48_cli_help_includes_phase174_subcommand(self) -> None:
        buf = io.StringIO()
        with self.assertRaises(SystemExit) as ctx:
            with redirect_stdout(buf):
                cli_main(["--help"])
        self.assertEqual(ctx.exception.code, 0)
        help_text = buf.getvalue()
        self.assertIn("audit-realhw-wbi2-hibdrv-isolation", help_text)
        self.assertIn("36", help_text)

    def test_49_wave21_ssboot_scel_and_8b_wbi2_magic_exports(self) -> None:
        for name in (
            "SCEL_KERNEL_RELEASE_P174",
            "WBI2_MAGIC_8B_HEX",
            "BLKROSET_IOCTL_VALUE",
            "SSBOOT_PRSV_MODULES_P174",
            "P5Wbi2H0H3ConservationResult",
            "evaluate_p5_wbi2_h0_h3_conservation",
        ):
            self.assertTrue(hasattr(lab, name), name)
            self.assertIn(name, lab.__all__, name)
        self.assertEqual(lab.SCEL_KERNEL_RELEASE_P174, "4.9.337-scel+")
        self.assertEqual(lab.WBI2_MAGIC_8B_HEX, "5742493200000000")
        self.assertEqual(lab.BLKROSET_IOCTL_VALUE, 1)
        self.assertIn("ssboot", lab.SSBOOT_PRSV_MODULES_P174)
        self.assertIn("liro.ko", lab.SSBOOT_PRSV_MODULES_P174)
        self.assertIn("LZO", lab.SSBOOT_PRSV_MODULES_P174)

    def test_50_write_firewall_blocks_all_proc_udm_and_liro_ko(self) -> None:
        for path in ("/proc/udm/upm_bootmode", "/proc/udm/ssboot_state", "/proc/udm", "/lib/modules/liro.ko"):
            g = evaluate_phase174_write_guard(path)
            self.assertFalse(g.valid, path)
            self.assertTrue(g.persistent_write_blocked, path)
            self.assertEqual(g.wbi_mutation_bytes, 0)

    def test_51_p5_wbi2_h0_h3_conservation_and_blkroset_pass(self) -> None:
        digest = "a" * 64
        res = lab.evaluate_p5_wbi2_h0_h3_conservation(
            h0_header_sha256=digest,
            h3_header_sha256=digest,
            blkroset_ioctl_value=1,
            wbi2_magic_8b_hex="5742493200000000",
        )
        self.assertTrue(res.valid, res.errors)
        self.assertTrue(res.h0_equals_h3)
        self.assertEqual(res.blkroset_ioctl_value, 1)
        self.assertEqual(res.wbi_mutation_bytes, 0)
        self.assertEqual(res.status, "P5_WBI2_H0_EQ_H3_BLKROSET_CONSERVED")

    def test_52_p5_wbi2_h0_h3_drift_or_unlocked_blkroset_fails_closed(self) -> None:
        res_drift = lab.evaluate_p5_wbi2_h0_h3_conservation(
            h0_header_sha256="a" * 64,
            h3_header_sha256="b" * 64,
            blkroset_ioctl_value=1,
        )
        self.assertFalse(res_drift.valid)
        self.assertFalse(res_drift.h0_equals_h3)
        self.assertIn("P5_WBI2_HEADER_H0_H3_DRIFT_DETECTED", res_drift.errors)
        self.assertEqual(res_drift.wbi_mutation_bytes, 0)

        res_unlocked = lab.evaluate_p5_wbi2_h0_h3_conservation(
            h0_header_sha256="c" * 64,
            h3_header_sha256="c" * 64,
            blkroset_ioctl_value=0,
        )
        self.assertFalse(res_unlocked.valid)
        self.assertTrue(any("BLKROSET_NOT_LOCKED_READONLY" in e for e in res_unlocked.errors))

        res_bad_magic = lab.evaluate_p5_wbi2_h0_h3_conservation(
            h0_header_sha256="c" * 64,
            h3_header_sha256="c" * 64,
            wbi2_magic_8b_hex="deadbeef00000000",
        )
        self.assertFalse(res_bad_magic.valid)
        self.assertTrue(any("WBI2_8B_MAGIC_MISMATCH" in e for e in res_bad_magic.errors))


if __name__ == "__main__":
    unittest.main()
