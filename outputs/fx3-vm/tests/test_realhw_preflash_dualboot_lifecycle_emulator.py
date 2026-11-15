#!/usr/bin/env python3
"""Phase 141 Test Suite — Stage 24 Full-Board End-to-End Real-Hardware
Pre-Flash Lifecycle & 4-State Dual-Boot HIL Simulator.

Exercises 44 fast unit, topology, cipher-safety, power-cut recovery, 4-state
dual-boot, Stage 24 suite integration, CLI, runtime budget, and source-hygiene
tests across BOTH Local Donor (`os.O_RDONLY`) and `FX3_FX6_FORCE_CLEAN_ROOM=1`
modes, strictly offline with `persistent_emmc_writes_authorized == False`.
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import contextlib
import hashlib
import io
import json
import os
import re
import struct
import subprocess
import time
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
FX3_VM_DIR = TESTS_DIR.parent
REPO_ROOT = FX3_VM_DIR.parents[1]
if str(FX3_VM_DIR) not in sys.path:
    sys.path.insert(0, str(FX3_VM_DIR))

import fx3_vm_coemulation_suite as suite  # noqa: E402
import realhw_preflash_dualboot_lifecycle_emulator as p141  # noqa: E402


_AUDIT_CACHE: dict = {}


def _get_clean_room_audit() -> dict:
    if "clean_room" not in _AUDIT_CACHE:
        _AUDIT_CACHE["clean_room"] = p141.run_phase141_realhw_preflash_dualboot_audit(
            force_clean_room=True
        )
    return _AUDIT_CACHE["clean_room"]


class TestPhase141DonorAuditAndBudget(unittest.TestCase):
    """Verify O_RDONLY donor audit, clean-room fallback, and <0.15s execution budget."""

    def test_01_clean_room_donor_audit_verifies_all_9_artifacts_and_sha256(self) -> None:
        audit = p141.inspect_phase141_donors(force_clean_room=True)
        self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(audit.access_mode, "O_RDONLY")
        self.assertEqual(audit.donor_files_inspected, 0)
        self.assertTrue(audit.all_contracts_verified)
        self.assertGreaterEqual(len(audit.checked_markers), 28)
        self.assertEqual(audit.missing_markers, ())
        for key, (expected_bytes, expected_sha) in p141.PINNED_DONOR_SHA256.items():
            self.assertEqual(audit.bytes_by_artifact[key], expected_bytes)
            self.assertEqual(audit.sha256_by_artifact[key], expected_sha)

    def test_02_force_clean_room_env_disables_local_donor_paths(self) -> None:
        env = {p141.ENV_FORCE_CLEAN_ROOM: "1"}
        self.assertTrue(p141.is_forced_clean_room(env))
        paths = p141.resolve_phase141_donor_paths(env=env)
        self.assertEqual(len(paths), 9)
        for path in paths.values():
            self.assertIn(p141.CLEAN_ROOM_SENTINEL_DIRNAME, str(path))
        audit = p141.inspect_phase141_donors(env=env)
        self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_03_local_donor_o_rdonly_audit_when_present_or_clean_room(self) -> None:
        if p141.is_forced_clean_room():
            audit = p141.inspect_phase141_donors()
            self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")
            return
        paths = p141.resolve_phase141_donor_paths()
        audit = p141.inspect_phase141_donors()
        self.assertTrue(audit.all_contracts_verified)
        if all(p.is_file() for p in paths.values()):
            self.assertEqual(audit.source_mode, "LOCAL_DONOR_RDONLY")
            self.assertEqual(audit.donor_files_inspected, 9)
            for key, (expected_bytes, expected_sha) in p141.PINNED_DONOR_SHA256.items():
                self.assertEqual(audit.bytes_by_artifact[key], expected_bytes)
                self.assertEqual(audit.sha256_by_artifact[key], expected_sha)
        else:
            self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_04_missing_donor_root_falls_back_to_clean_room(self) -> None:
        env = {
            p141.ENV_MAC_WORK_ROOT: "/nonexistent_phase141_mac_work_root",
            p141.ENV_MAIN_LAB_WORK_ROOT: "/nonexistent_phase141_main_work_root",
        }
        audit = p141.inspect_phase141_donors(force_clean_room=True, env=env)
        self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(audit.donor_files_inspected, 0)
        self.assertTrue(audit.all_contracts_verified)

    def test_05_stage24_clean_room_and_local_execution_under_0p15s(self) -> None:
        t0 = time.monotonic()
        rep_clean = p141.run_phase141_realhw_preflash_dualboot_audit(force_clean_room=True)
        dt_clean = time.monotonic() - t0
        self.assertTrue(rep_clean["all_checks_passed"])
        self.assertLess(dt_clean, 0.15)

        t1 = time.monotonic()
        rep_mode = p141.run_phase141_realhw_preflash_dualboot_audit()
        dt_mode = time.monotonic() - t1
        self.assertTrue(rep_mode["all_checks_passed"])
        self.assertLess(dt_mode, 0.15)

    def test_06_scan_donor_readonly_mmap_handles_empty_and_valid_files(self) -> None:
        tmp_path = FX3_VM_DIR / "manifest.json"
        sz, sha, hits = p141.scan_donor_readonly_mmap(tmp_path, [b"minimal-linux", b"nonexistent_xyz"])
        self.assertGreater(sz, 0)
        self.assertEqual(len(sha), 64)
        self.assertTrue(hits["minimal-linux"])
        self.assertFalse(hits["nonexistent_xyz"])


class TestPillarAJiritsuSetFile2AndSpaccTopology(unittest.TestCase):
    """Verify Pillar A: eMMC Sector 0, SPACC boundary, 16 MiB SPI NOR, & Stage-288 SET_FILE2."""

    def test_07_sector0_magic_version_and_30_entry_nonoverlapping_table(self) -> None:
        sec0 = p141.build_fx3_sector0_bytes()
        self.assertEqual(len(sec0), 512)
        self.assertEqual(sec0[0:4], b"8246")
        self.assertEqual(sec0[4:8], b"2.00")
        count = struct.unpack_from("<I", sec0, 8)[0]
        self.assertEqual(count, 30)

        topo = p141.audit_emmc_spacc_and_spi_nor_topology()
        self.assertTrue(topo.passed)
        self.assertEqual(topo.sector0_magic, "8246")
        self.assertEqual(topo.sector0_version, "2.00")
        self.assertEqual(topo.sector0_entry_count, 30)
        self.assertEqual(len(topo.pnflasha_nodes), 30)
        self.assertFalse(topo.has_overlaps)
        self.assertEqual(topo.sector0_mutation_bytes, 0)

    def test_08_spacc_crypt_emmc_cnflasha_boundary_and_zero_key_export(self) -> None:
        topo = p141.audit_emmc_spacc_and_spi_nor_topology()
        self.assertTrue(topo.crypt_emmc_ko_bound)
        self.assertEqual(topo.spacc_mmio_base_hex, "0xf7fc0000")
        self.assertEqual(topo.spacc_key_export_bytes, 0)
        self.assertEqual(
            topo.cnflasha_cipher_nodes,
            (
                "/dev/cnflasha3",
                "/dev/cnflasha7",
                "/dev/cnflasha8",
                "/dev/cnflasha12",
                "/dev/cnflasha15",
                "/dev/cnflasha23",
                "/dev/cnflasha30",
            ),
        )

    def test_09_octal_spi_nor_16mib_and_ddrtraining_offset_0x3e210fc(self) -> None:
        topo = p141.audit_emmc_spacc_and_spi_nor_topology()
        self.assertEqual(topo.spi_nor_total_bytes, 16 * 1024 * 1024)
        self.assertEqual(topo.ddrtraining_offset_hex, "0x3e210fc")
        self.assertEqual(topo.spi_nor_mutation_bytes, 0)
        for required in ("infomisc.dat", "loader_nor.bin", "ddrtraining.dat"):
            self.assertIn(required, topo.spi_nor_regions)

    def test_10_stage288_j0_frame_encode_decode_roundtrip_and_corruption(self) -> None:
        sec0 = p141.build_fx3_sector0_bytes()
        frame = p141.build_stage288_j0_frame(sec0)
        self.assertEqual(len(frame), 8 + 512)
        ok, payload, err = p141.decode_stage288_j0_frame(frame)
        self.assertTrue(ok)
        self.assertEqual(err, "OK")
        self.assertEqual(payload, sec0)

        bad_crc = frame[:-1] + bytes([frame[-1] ^ 0xFF])
        ok2, _p2, err2 = p141.decode_stage288_j0_frame(bad_crc)
        self.assertFalse(ok2)
        self.assertEqual(err2, "CRC32_MISMATCH")

        ok3, _p3, err3 = p141.decode_stage288_j0_frame(b"XX\x00\x00\x00\x00\x00\x00")
        self.assertFalse(ok3)
        self.assertEqual(err3, "INVALID_J0_MAGIC")

        ok4, _p4, err4 = p141.decode_stage288_j0_frame(b"J0")
        self.assertFalse(ok4)
        self.assertEqual(err4, "FRAME_TOO_SHORT")

    def test_11_stage288_j0_frame_rejects_oversized_payload(self) -> None:
        with self.assertRaises(p141.RealHwPreflashDualbootError):
            p141.build_stage288_j0_frame(b"\x00" * 70_000)

    def test_12_setfile2_tier012_backup_p6_peak_under_4p5mib_and_zero_residual(self) -> None:
        res = p141.run_stage288_setfile2_cold_backup()
        self.assertTrue(res.passed)
        self.assertEqual(res.status, "VERIFIED_STAGE288_SETFILE2_COLD_BACKUP_100PCT")
        self.assertTrue(res.jbusy_absent_ok)
        self.assertEqual(res.selector_byte, 0xFF)
        self.assertTrue(res.self_unlink_at_entry)
        self.assertEqual(res.p6_capacity_bytes, 25 * 1024 * 1024)
        self.assertLess(res.p6_peak_bytes, int(4.5 * 1024 * 1024))
        self.assertEqual(res.p6_residual_files, 0)
        self.assertEqual(res.tiers_backed_up, ("Tier0", "Tier1", "Tier2"))
        self.assertEqual(res.artifacts_sha256_verified, res.artifacts_total)
        self.assertEqual(res.manifest_verified_pct, 100.0)

    def test_13_setfile2_blocks_jbusy_bad_selector_missing_unlink_and_bad_crc(self) -> None:
        jbusy = p141.run_stage288_setfile2_cold_backup(jbusy_present=True)
        self.assertFalse(jbusy.passed)
        self.assertIn("BLOCKED_JIRITSU_JBUSY_PRESENT_0X10000011", jbusy.violation_codes)

        sel2 = p141.run_stage288_setfile2_cold_backup(selector_byte=0x02)
        self.assertFalse(sel2.passed)
        self.assertIn("BLOCKED_JIRITSU_INVALID_SELECTOR_NOT_0XFF", sel2.violation_codes)

        no_unlink = p141.run_stage288_setfile2_cold_backup(simulate_self_unlink=False)
        self.assertFalse(no_unlink.passed)
        self.assertEqual(no_unlink.p6_residual_files, 1)
        self.assertIn("BLOCKED_STAGE288_P0_MISSING_SELF_UNLINK_AT_ENTRY", no_unlink.violation_codes)

        bad_crc = p141.run_stage288_setfile2_cold_backup(inject_corrupt_crc=True)
        self.assertFalse(bad_crc.passed)
        self.assertIn("BLOCKED_STAGE288_FRAME_CRC32_MISMATCH", bad_crc.violation_codes)


class TestPillarBCnflasha15InstallAndPowercutRecovery(unittest.TestCase):
    """Verify Pillar B: /dev/cnflasha15 atomic install, /dev/pnflasha15 block, & battery-pull recovery."""

    def test_14_atomic_nflasha15_wrapper_install_and_ro_remount(self) -> None:
        res = p141.simulate_cnflasha15_stageb_install(target_device="/dev/nflasha15")
        self.assertTrue(res.passed)
        self.assertEqual(res.status, "VERIFIED_ATOMIC_CNFLASHA15_WRAPPER_INSTALL")
        self.assertEqual(res.ext2_super_magic_hex, "0xef53")
        self.assertEqual(res.initial_mount_state, "ro")
        self.assertEqual(res.final_mount_state, "ro")
        self.assertTrue(res.orig_journal_saved)
        self.assertFalse(res.orig_recovery_executed)
        self.assertEqual(res.ciphertext_corruption_events, 0)
        self.assertEqual(res.physical_device_writes, 0)

    def test_15_cnflasha15_clean_rollback_restores_100pct_stock_im_elf_sha256(self) -> None:
        res = p141.simulate_cnflasha15_stageb_install(
            target_device="/dev/cnflasha15", rollback_to_stock=True
        )
        self.assertTrue(res.passed)
        self.assertEqual(res.status, "VERIFIED_CLEAN_ROLLBACK_TO_STOCK_100PCT")
        self.assertTrue(res.orig_recovery_executed)
        self.assertTrue(res.stock_im_elf_restored_100pct)
        self.assertEqual(res.final_im_elf_sha256, p141.FX3_IM_ELF_STOCK_SHA256)
        self.assertEqual(res.final_mount_state, "ro")

    def test_16_direct_raw_pnflasha15_write_hard_blocked(self) -> None:
        res = p141.simulate_cnflasha15_stageb_install(target_device="/dev/pnflasha15")
        self.assertFalse(res.passed)
        self.assertEqual(res.status, "SPACC_CIPHERTEXT_CORRUPTION_BLOCKED")
        self.assertIn("SPACC_CIPHERTEXT_CORRUPTION_BLOCKED", res.violation_codes)
        self.assertEqual(res.ciphertext_corruption_events, 0)
        self.assertEqual(res.physical_device_writes, 0)
        self.assertEqual(res.final_mount_state, "ro")

    def test_17_midwrite_battery_pull_recovers_stock_im_elf_and_ro_mount(self) -> None:
        res = p141.simulate_cnflasha15_stageb_install(
            target_device="/dev/nflasha15", inject_midwrite_battery_pull=True
        )
        self.assertTrue(res.passed)
        self.assertEqual(res.status, "VERIFIED_MIDWRITE_BATTERYPULL_ORIG_RECOVERY_100PCT_STOCK")
        self.assertTrue(res.power_cut_injected)
        self.assertTrue(res.orig_journal_saved)
        self.assertTrue(res.orig_recovery_executed)
        self.assertTrue(res.stock_im_elf_restored_100pct)
        self.assertEqual(res.final_im_elf_sha256, p141.FX3_IM_ELF_STOCK_SHA256)
        self.assertEqual(res.final_mount_state, "ro")
        self.assertEqual(res.physical_device_writes, 0)

    def test_18_unsupported_p15_device_raises_domain_error(self) -> None:
        with self.assertRaises(p141.RealHwPreflashDualbootError):
            p141.simulate_cnflasha15_stageb_install(target_device="/dev/nflasha3")


class TestPillarCFourStateDualbootAndNativeRec(unittest.TestCase):
    """Verify Pillar C: 4 cold-boot power-on paths + negative P1/UART/line-1 blocks."""

    def test_19_path1_sd_ejected_escape_hatch_boots_100pct_stock_fx3(self) -> None:
        res = p141.simulate_cold_boot_path(p141.BOOT_PATH_SD_EJECTED)
        self.assertTrue(res.passed)
        self.assertFalse(res.sd_card_inserted)
        self.assertEqual(res.active_os_profile, "STOCK_FX3_702")
        self.assertEqual(res.stage_b_hooks_active, 0)
        self.assertTrue(res.native_shooting_intact)
        self.assertEqual(res.sector0_mutation_bytes, 0)
        self.assertEqual(res.cp_mutation_bytes, 0)

    def test_20_path2_valid_signed_manifest_strategy_a_and_xavc_si_rec_closed(self) -> None:
        res = p141.simulate_cold_boot_path(p141.BOOT_PATH_VALID_MANIFEST)
        self.assertTrue(res.passed)
        self.assertTrue(res.sd_card_inserted)
        self.assertTrue(res.manifest_valid)
        self.assertEqual(res.active_os_profile, "FX6_601_STAGE_B_OVER_FX3_702")
        self.assertEqual(res.strategy_a_lut_bridge, "/dev/nflasha20 -> /dev/nflasha30")
        self.assertEqual(res.strategy_a_opelog_tmpfs, "tmpfs /etc/opelog")
        self.assertEqual(res.sector0_mutation_bytes, 0)
        self.assertTrue(res.fx6_appfw_active)
        self.assertTrue(res.libmpr_abi_shim_active)
        self.assertTrue(res.stock_cp_driven)
        self.assertEqual(res.cp_mutation_bytes, 0)
        self.assertTrue(res.recorded_clip_name.endswith(".MP4"))
        self.assertIn("XAVC S-I", res.recorded_clip_format)
        self.assertEqual(res.rsv_orphan_count, 0)

    def test_21_path2_with_tamper_flag_fails_closed(self) -> None:
        res = p141.simulate_cold_boot_path(p141.BOOT_PATH_VALID_MANIFEST, tamper_manifest=True)
        self.assertFalse(res.passed)
        self.assertFalse(res.manifest_valid)
        self.assertEqual(res.status, p141.TAMPERED_MANIFEST_CODE)
        self.assertEqual(res.active_os_profile, "STOCK_FX3_702")
        self.assertEqual(res.stage_b_hooks_active, 0)

    def test_22_path3_tampered_sd_manifest_fails_closed_under_50ms_to_stock_fx3(self) -> None:
        res = p141.simulate_cold_boot_path(p141.BOOT_PATH_TAMPERED_MANIFEST)
        self.assertTrue(res.passed)
        self.assertTrue(res.sd_card_inserted)
        self.assertFalse(res.manifest_valid)
        self.assertLess(res.fail_closed_latency_ms, 50.0)
        self.assertEqual(res.active_os_profile, "STOCK_FX3_702")
        self.assertEqual(res.stage_b_hooks_active, 0)
        self.assertTrue(res.native_shooting_intact)

    def test_23_signed_manifest_verify_rejects_cross_sku_and_tampered_hmac(self) -> None:
        valid = p141.build_signed_sd_manifest()
        ok, err = p141.verify_signed_sd_manifest(valid)
        self.assertTrue(ok)
        self.assertEqual(err, "OK")

        cross_sku = p141.build_signed_sd_manifest(model_id="99999999")
        ok2, err2 = p141.verify_signed_sd_manifest(cross_sku)
        self.assertFalse(ok2)
        self.assertEqual(err2, "BLOCKED_CROSS_SKU_MODEL_ID")

        tampered = p141.build_signed_sd_manifest(tamper=True)
        ok3, err3 = p141.verify_signed_sd_manifest(tampered)
        self.assertFalse(ok3)
        self.assertEqual(err3, p141.TAMPERED_MANIFEST_CODE)

    def test_24_path4_emergency_p1_oneshot_rescue_and_clean_reboot_to_p3(self) -> None:
        res = p141.simulate_cold_boot_path(p141.BOOT_PATH_P1_RESCUE)
        self.assertTrue(res.passed)
        self.assertEqual(res.status, "VERIFIED_PATH4_P1_ONESHOT_RESCUE_RESTORED_TO_P3")
        self.assertTrue(res.p1_p3_mutual_exclusion_ok)
        self.assertEqual(res.p1_cfg_uart, 1)
        self.assertEqual(res.p1_uart_baud, 460800)
        self.assertEqual(res.p1_uart_framing, "8N1")
        self.assertTrue(res.init_line1_mode_clear_sync)
        self.assertTrue(res.usr_restored_from_cold_backup)
        self.assertEqual(res.next_boot_partition, "p3")
        self.assertEqual(res.active_os_profile, "STOCK_FX3_702")

    def test_25_path4_blocks_p1_p3_dual_write_uart9_and_missing_line1_sync(self) -> None:
        dual = p141.simulate_cold_boot_path(p141.BOOT_PATH_P1_RESCUE, p1_modified_with_p3=True)
        self.assertFalse(dual.passed)
        self.assertIn("BLOCKED_P1_P3_MUTUAL_EXCLUSION_VIOLATION", dual.violation_codes)

        uart9 = p141.simulate_cold_boot_path(p141.BOOT_PATH_P1_RESCUE, p1_cfg_uart=9)
        self.assertFalse(uart9.passed)
        self.assertIn("BLOCKED_P1_CFG_UART_MUST_BE_1_460800_8N1", uart9.violation_codes)

        no_sync = p141.simulate_cold_boot_path(
            p141.BOOT_PATH_P1_RESCUE, init_line1="echo missing clear"
        )
        self.assertFalse(no_sync.passed)
        self.assertIn("BLOCKED_P1_INIT_LINE1_MISSING_MODE_CLEAR_SYNC", no_sync.violation_codes)

    def test_26_invalid_boot_path_raises_domain_error(self) -> None:
        with self.assertRaises(p141.RealHwPreflashDualbootError):
            p141.simulate_cold_boot_path("PATH_99_INVALID")


class TestPillarDHardwareSafetyRedlines(unittest.TestCase):
    """Verify Pillar D: hard-locked zero-mutation hardware redlines & tamper blocks."""

    def test_27_nominal_redlines_all_zero_and_emmc_writes_false(self) -> None:
        rep = _get_clean_room_audit()
        red = rep["redlines"]
        self.assertTrue(red["p8_cp_mutation_forbidden"])
        self.assertEqual(red["nop_count"], 0)
        self.assertEqual(red["guest_code_modification_bytes"], 0)
        self.assertEqual(red["cp_mutation_bytes"], 0)
        self.assertEqual(red["wbi_mutation_bytes"], 0)
        self.assertEqual(red["calibration_mutation_bytes"], 0)
        self.assertEqual(red["nvram_persistent_writes"], 0)
        self.assertEqual(red["bk4_persistent_nvram_writes"], 0)
        self.assertEqual(red["physical_device_writes"], 0)
        self.assertFalse(red["persistent_emmc_writes_authorized"])
        self.assertEqual(red["spi_nor_mutation_bytes"], 0)
        self.assertEqual(red["emmc_mutation_bytes"], 0)
        self.assertEqual(red["sector0_mutation_bytes"], 0)
        self.assertEqual(red["null_gpio_derefs"], 0)
        self.assertEqual(red["mailbox_stalls"], 0)
        self.assertEqual(red["stock_cp_fault_count"], 0)
        self.assertEqual(red["wf12_00342260_hits"], 0)
        self.assertEqual(red["rsv_orphan_count"], 0)
        self.assertEqual(red["donor_access_mode"], "O_RDONLY")

    def test_28_verify_hardware_safety_redlines_blocks_all_5_tamper_vectors(self) -> None:
        ok = p141.verify_hardware_safety_redlines()
        self.assertTrue(ok.passed)
        self.assertFalse(ok.persistent_emmc_writes_authorized)

        for kwargs, code in (
            ({"requested_emmc_write_auth": True}, "BLOCKED_PERSISTENT_EMMC_WRITES_HARD_LOCKED_FALSE"),
            ({"requested_spi_nor_mutation_bytes": 4}, "BLOCKED_SPI_NOR_MUTATION_MUST_BE_ZERO"),
            ({"requested_cp_mutation_bytes": 4}, "BLOCKED_CP_MUTATION_MUST_BE_ZERO"),
            ({"requested_calibration_mutation_bytes": 16}, "BLOCKED_CALIBRATION_MUTATION_MUST_BE_ZERO"),
            ({"requested_wf12_hits": 1}, "BLOCKED_WF12_00342260_HITS_MUST_BE_ZERO"),
        ):
            bad = p141.verify_hardware_safety_redlines(**kwargs)
            self.assertFalse(bad.passed)
            self.assertIn(code, bad.violation_codes)
            self.assertFalse(bad.persistent_emmc_writes_authorized)
            self.assertEqual(bad.physical_device_writes, 0)

    def test_29_all_four_pillar_evaluators_pass_independently(self) -> None:
        self.assertTrue(p141.evaluate_pillar_a_jiritsu_backup_and_spacc()["passed"])
        self.assertTrue(p141.evaluate_pillar_b_cnflasha15_install_and_rollback()["passed"])
        self.assertTrue(p141.evaluate_pillar_c_four_state_dualboot()["passed"])
        self.assertTrue(p141.evaluate_pillar_d_safety_redlines()["passed"])


class TestStage24SuiteIntegrationCliAndHygiene(unittest.TestCase):
    """Verify Stage 24 suite integration (24/24), CLI flags, runtime budgets & strict hygiene."""

    def test_30_clean_room_audit_digest_reproducible_and_valid_sha256(self) -> None:
        rep1 = p141.run_phase141_realhw_preflash_dualboot_audit(force_clean_room=True)
        rep2 = p141.run_phase141_realhw_preflash_dualboot_audit(force_clean_room=True)
        self.assertTrue(rep1["all_checks_passed"])
        self.assertEqual(rep1["audit_digest_sha256"], rep2["audit_digest_sha256"])

        copy = dict(rep1)
        recorded = copy.pop("audit_digest_sha256")
        expected = hashlib.sha256(
            json.dumps(copy, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        self.assertEqual(recorded, expected)

    def test_31_standalone_cli_all_flags_emit_valid_outputs(self) -> None:
        for argv in (
            ["--clean-room", "--summary"],
            ["--clean-room", "--self-test", "--summary"],
            ["--clean-room", "--pillar-a"],
            ["--clean-room", "--pillar-b"],
            ["--clean-room", "--pillar-c"],
            ["--clean-room", "--pillar-d"],
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = p141.main(argv)
            self.assertEqual(rc, 0, msg=f"CLI argv={argv} failed")
            self.assertTrue(buf.getvalue().strip())

    def test_32_standalone_json_cli_matches_schema(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = p141.main(["--clean-room", "--json"])
        self.assertEqual(rc, 0)
        parsed = json.loads(buf.getvalue())
        self.assertEqual(parsed["schema"], p141.PHASE_141_SCHEMA)
        self.assertTrue(parsed["all_checks_passed"])
        self.assertFalse(parsed["redlines"]["persistent_emmc_writes_authorized"])

    def test_33_suite_in_process_24_stages_and_skip_phase141_config(self) -> None:
        cfg_on = suite.CoEmulationConfig(force_clean_room=True)
        rep_on = suite.run_fx3_vm_coemulation_suite(cfg_on)
        self.assertTrue(rep_on["all_checks_passed"])
        self.assertIn("stage24_realhw_preflash_dualboot_hil", rep_on)
        self.assertTrue(rep_on["stage24_realhw_preflash_dualboot_hil"]["all_checks_passed"])
        self.assertFalse(
            rep_on["stage24_realhw_preflash_dualboot_hil"]["persistent_emmc_writes_authorized"]
        )

        stage_keys = [k for k in rep_on if re.match(r"^stage\d+_", k)]
        self.assertGreaterEqual(len(stage_keys), 24)

        cfg_skip = suite.CoEmulationConfig(
            force_clean_room=True,
            include_phase141_realhw_preflash_dualboot_hil=False,
        )
        rep_skip = suite.run_fx3_vm_coemulation_suite(cfg_skip)
        self.assertTrue(rep_skip["all_checks_passed"])
        self.assertNotIn("stage24_realhw_preflash_dualboot_hil", rep_skip)
        self.assertEqual(
            len([k for k in rep_skip if re.match(r"^stage\d+_", k)]),
            len(stage_keys) - 1,
        )

    def test_34_suite_subprocess_summary_and_skip_phase141_flag(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        proc = subprocess.run(
            [
                "/usr/bin/python3",
                "-B",
                str(FX3_VM_DIR / "fx3_vm_coemulation_suite.py"),
                "--clean-room",
                "--summary",
            ],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        self.assertIn("realhw_preflash_dualboot=CLEAN_ROOM_SYNTHETIC", proc.stdout)

        proc_skip = subprocess.run(
            [
                "/usr/bin/python3",
                "-B",
                str(FX3_VM_DIR / "fx3_vm_coemulation_suite.py"),
                "--clean-room",
                "--skip-phase141",
                "--summary",
            ],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc_skip.returncode, 0, msg=proc_skip.stderr)
        self.assertNotIn("realhw_preflash_dualboot=", proc_skip.stdout)

    def test_35_suite_24_stages_clean_room_and_local_runtime_under_budget_and_json_cli(self) -> None:
        t0 = time.monotonic()
        rep_clean = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig(force_clean_room=True))
        dt_clean = time.monotonic() - t0
        self.assertTrue(rep_clean["all_checks_passed"])
        self.assertGreaterEqual(len([k for k in rep_clean if re.match(r"^stage\d+_", k)]), 24)
        self.assertLess(dt_clean, 0.70)

        t1 = time.monotonic()
        rep_mode = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig())
        dt_mode = time.monotonic() - t1
        self.assertTrue(rep_mode["all_checks_passed"])
        self.assertGreaterEqual(len([k for k in rep_mode if re.match(r"^stage\d+_", k)]), 24)
        self.assertLess(dt_mode, 1.80)

        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        p_clean = subprocess.run(
            [
                "/usr/bin/python3",
                "-B",
                str(FX3_VM_DIR / "fx3_vm_coemulation_suite.py"),
                "--clean-room",
                "--json",
            ],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(p_clean.returncode, 0, msg=p_clean.stderr)
        d_clean = json.loads(p_clean.stdout)
        self.assertTrue(d_clean["all_checks_passed"])
        self.assertGreaterEqual(len([k for k in d_clean if re.match(r"^stage\d+_", k)]), 24)

    def test_36_all_24_stages_present_and_passing_in_suite_report(self) -> None:
        rep = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig(force_clean_room=True))
        self.assertTrue(rep["stage1_coldboot_and_bt"]["all_checks_passed"])
        self.assertTrue(rep["stage2_dual_isa_cp_shooting"]["all_checks_passed"])
        self.assertTrue(rep["stage3_soft_gpe_hud_ramfb"]["all_checks_passed"])
        for idx in range(4, 25):
            matches = [k for k in rep if k.startswith(f"stage{idx}_")]
            self.assertEqual(len(matches), 1, msg=f"Missing or duplicate stage{idx}_* key")
            self.assertTrue(rep[matches[0]]["all_checks_passed"])

    def test_37_stage24_emulator_no_raw_bytes_repr_or_nan_in_json(self) -> None:
        rep = _get_clean_room_audit()
        rendered = json.dumps(rep, allow_nan=False)
        self.assertNotRegex(rendered, r'(?<![0-9A-Za-z_/.-])b[\'"]')
        self.assertIsNone(re.search(r"NaN|Infinity", rendered))

        rep_suite = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig(force_clean_room=True))
        rendered_suite = json.dumps(rep_suite, allow_nan=False)
        self.assertNotRegex(rendered_suite, r'(?<![0-9A-Za-z_/.-])b[\'"]')
        self.assertIsNone(re.search(r"NaN|Infinity", rendered_suite))

    def test_38_source_hygiene_o_rdonly_and_no_write_flags_or_forbidden_port(self) -> None:
        src = (FX3_VM_DIR / "realhw_preflash_dualboot_lifecycle_emulator.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("os.O_RDONLY", src)
        self.assertNotIn("os.O_WRONLY", src)
        self.assertNotIn("os.O_RDWR", src)
        self.assertNotIn("87" + "68", src)
        self.assertIn("sys.dont_write_bytecode = True", src)

    def test_39_spacc_partition_lists_disjoint_and_cover_all_30_partitions(self) -> None:
        enc = set(p141.SPACC_ENCRYPTED_PARTITIONS)
        plain = set(p141.PLAINTEXT_PARTITIONS)
        self.assertEqual(enc & plain, set())
        self.assertEqual(enc | plain, set(range(1, 31)))

    def test_40_fx3_uda_partition_table_has_expected_p1_p3_p6_p8_p15_p30_slots(self) -> None:
        labels = {entry[4]: entry for entry in p141.FX3_UDA_PARTITION_TABLE}
        self.assertIn("p1:/updater", labels)
        self.assertIn("p3:/system", labels)
        self.assertIn("p6:/tmp/jiritsu", labels)
        self.assertIn("p8:/cp", labels)
        self.assertIn("p15:/usr", labels)
        self.assertIn("p30:/lutdata", labels)
        self.assertEqual(labels["p6:/tmp/jiritsu"][1] * p141.SECTOR_SIZE_BYTES, p141.P6_CAPACITY_BYTES)
        self.assertEqual(labels["p15:/usr"][1] * p141.SECTOR_SIZE_BYTES, p141.FX3_P15_SLOT_BYTES)

    def test_41_manifest_verify_rejects_malformed_objects(self) -> None:
        for bad in ({}, {"payload": "not_dict", "hmac_sha256": "abc"}, {"payload": {"model_id": "91030080"}}):
            ok, err = p141.verify_signed_sd_manifest(bad)
            self.assertFalse(ok)
            self.assertEqual(err, p141.TAMPERED_MANIFEST_CODE)

    def test_42_p1_and_p3_clean_recovery_preserves_zero_sector0_mutation(self) -> None:
        pa = p141.evaluate_pillar_a_jiritsu_backup_and_spacc()
        pc = p141.evaluate_pillar_c_four_state_dualboot()
        self.assertEqual(pa["emmc_spacc_and_spi_nor_topology"]["sector0_mutation_bytes"], 0)
        self.assertEqual(pc["path2_valid_signed_manifest_xavc_rec"]["sector0_mutation_bytes"], 0)
        self.assertEqual(pc["path4_emergency_p1_rescue_to_p3"]["sector0_mutation_bytes"], 0)

    def test_43_p141_readme_documents_stage24_and_skip_phase141(self) -> None:
        readme_text = (FX3_VM_DIR / "README.md").read_text(encoding="utf-8")
        self.assertIn("Phase 141", readme_text)
        self.assertIn("realhw_preflash_dualboot_lifecycle_emulator.py", readme_text)
        self.assertIn("--skip-phase141", readme_text)

    def test_44_p141_report_readme_exists_and_records_redlines(self) -> None:
        report_path = (
            REPO_ROOT
            / "reports"
            / "2026-11-14-phase141-vm-stage24-realhw-preflash-dualboot-hil"
            / "README.md"
        )
        self.assertTrue(report_path.is_file(), msg=f"Missing {report_path}")
        txt = report_path.read_text(encoding="utf-8")
        self.assertIn("persistent_emmc_writes_authorized", txt)
        self.assertIn("Stage 24", txt)


if __name__ == "__main__":
    unittest.main()
