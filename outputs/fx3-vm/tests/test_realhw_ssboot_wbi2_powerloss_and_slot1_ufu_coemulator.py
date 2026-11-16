#!/usr/bin/env python3
"""Phase 178 Test Suite — Stage 31 (`31/31` Stage) Real-Hardware Main Track:
Sony SCEL `ssboot` / `WBI2` Bootloader-Bypass Firewall, 100-Cycle `NP-FZ100` Battery-Pull &
Brownout (`6.3V` `EncWfiStop`) Recovery, and Slot-1 `BODYDATA.DAT` (`>=2.04`) / C2PA 100-License HIL.

Exercises 48 fast dual-mode unit, integration, Pillar A–D HIL, bounded O_RDONLY donor
inspection, 100-cycle zero-drift recovery, 31/31 suite orchestration, CLI, runtime-budget,
and clean-room hygiene checks.
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
import realhw_ssboot_wbi2_powerloss_and_slot1_ufu_coemulator as p178  # noqa: E402


_AUDIT_CACHE: dict = {}


def _get_default_audit() -> dict:
    key = ("default", p178.is_forced_clean_room())
    if key not in _AUDIT_CACHE:
        _AUDIT_CACHE[key] = p178.run_phase178_realhw_ssboot_wbi2_powerloss_slot1_ufu_hil(
            env=os.environ
        )
    return _AUDIT_CACHE[key]


def _get_clean_room_audit() -> dict:
    key = ("clean_room", True)
    if key not in _AUDIT_CACHE:
        _AUDIT_CACHE[key] = p178.run_phase178_realhw_ssboot_wbi2_powerloss_slot1_ufu_hil(
            force_clean_room=True,
            env=os.environ,
        )
    return _AUDIT_CACHE[key]


class TestStage31DualModeDonorsAndRedlines(unittest.TestCase):
    """Dual-mode bounded O_RDONLY donor inspection, parity contracts & safety redlines."""

    def test_01_donor_path_resolution_honors_clean_room_toggle(self) -> None:
        self.assertTrue(p178.is_forced_clean_room({"FX3_FX6_FORCE_CLEAN_ROOM": "1"}))
        self.assertFalse(p178.is_forced_clean_room({"FX3_FX6_FORCE_CLEAN_ROOM": "0"}))
        paths_clean = p178.resolve_phase178_donor_paths(env={"FX3_FX6_FORCE_CLEAN_ROOM": "1"})
        self.assertEqual(len(paths_clean), 9)
        for p in paths_clean.values():
            self.assertIn(p178.CLEAN_ROOM_SENTINEL_DIRNAME, str(p))
            self.assertFalse(p.exists())

    def test_02_clean_room_donor_audit_verifies_all_9_donors(self) -> None:
        da = p178.inspect_phase178_donors(force_clean_room=True)
        self.assertEqual(da.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(da.access_mode, "O_RDONLY")
        self.assertEqual(da.donor_files_inspected, 9)
        self.assertEqual(da.raw_firmware_bytes_leaked, 0)
        self.assertTrue(da.all_contracts_verified, msg=str(da.errors))
        self.assertEqual(da.errors, ())

    def test_03_default_mode_donor_audit_passes_in_current_env(self) -> None:
        rep = _get_default_audit()
        self.assertTrue(rep["all_checks_passed"])
        da = rep["donor_audit"]
        self.assertTrue(da["all_contracts_verified"], msg=str(da["errors"]))
        self.assertEqual(da["donor_files_inspected"], 9)
        self.assertEqual(da["raw_firmware_bytes_leaked"], 0)
        self.assertIn(rep["source_mode"], ("LOCAL_DONOR_RDONLY", "CLEAN_ROOM_SYNTHETIC"))

    def test_04_bounded_4k_header_reads_for_wbi2_and_811mib_bodydata(self) -> None:
        da = _get_default_audit()["donor_audit"]
        for key in ("fx3_nflasha5", "fx6_nflasha5", "fx3_bodydata", "fx6_bodydata"):
            sec = da[key]
            self.assertTrue(sec["bounded_header_only"], msg=key)
            self.assertLessEqual(sec["bytes_read"], p178.BOUNDED_HEADER_MAX_BYTES, msg=key)
            self.assertGreater(sec["file_bytes"], sec["bytes_read"], msg=key)

    def test_05_wbi2_cross_kernel_section_mismatch_1399_vs_1197(self) -> None:
        da = _get_default_audit()["donor_audit"]
        self.assertEqual(da["fx3_nflasha5"]["magic_ascii"], "WBI2")
        self.assertEqual(da["fx3_nflasha5"]["magic_hex"], p178.WBI2_MAGIC_HEX)
        self.assertEqual(da["fx3_nflasha5"]["file_bytes"], p178.EXPECTED_FX3_NFLASHA5_BYTES)
        self.assertEqual(da["fx3_nflasha5"]["section_count"], 1399)
        self.assertEqual(da["fx6_nflasha5"]["file_bytes"], p178.EXPECTED_FX6_NFLASHA5_BYTES)
        self.assertEqual(da["fx6_nflasha5"]["section_count"], 1197)
        self.assertTrue(da["wbi2_cross_kernel_section_mismatch_proven"])

    def test_06_liro_ko_121488b_and_vmlinux_scel_markers_verified(self) -> None:
        da = _get_default_audit()["donor_audit"]
        for k in ("fx3_liro_ko", "fx6_liro_ko"):
            self.assertEqual(da[k]["file_bytes"], 121488)
            self.assertTrue(da[k]["elf64_le_ok"])
            self.assertTrue(all(da[k]["marker_hits"].values()), msg=k)
        self.assertEqual(da["fx3_vmlinux"]["file_bytes"], 6610952)
        self.assertTrue(all(da["fx3_vmlinux"]["marker_hits"].values()))

    def test_07_bodydata_ufu_model_isolation_0da1_vs_0d21(self) -> None:
        da = _get_default_audit()["donor_audit"]
        fx3 = da["fx3_bodydata"]
        fx6 = da["fx6_bodydata"]
        self.assertEqual(fx3["file_bytes"], 811876768)
        self.assertTrue(fx3["ufu_magic_ok"])
        self.assertEqual(fx3["datv_version"], 1)
        self.assertEqual(fx3["prov_version"], 1)
        self.assertTrue(fx3["fx3_0da1_pid_present"])
        self.assertEqual(fx6["file_bytes"], 847081840)
        self.assertTrue(fx6["ufu_magic_ok"])
        self.assertFalse(fx6["fx3_0da1_pid_present"])
        self.assertIn("054c:0d21", fx6["udid_pids_hex"])
        self.assertTrue(da["bodydata_ufu_model_isolation_proven"])

    def test_08_im_elf_zero_diff_abi_40920b_11_exports_85_imports(self) -> None:
        da = _get_default_audit()["donor_audit"]
        for k in ("fx3_im_elf", "fx6_im_elf"):
            self.assertEqual(da[k]["file_bytes"], 40920)
            self.assertTrue(da[k]["elf64_le_ok"])
            self.assertEqual(da[k]["export_count"], 11)
            self.assertEqual(da[k]["import_count"], 85)
            self.assertTrue(all(da[k]["marker_hits"].values()))
        self.assertTrue(da["im_elf_abi_zero_diff"])

    def test_09_parse_ufu_header_4k_rejects_oversized_or_bad_magic(self) -> None:
        with self.assertRaises(p178.RealHwSsbootWbi2Slot1Error):
            p178.parse_ufu_header_4k(
                b"\x00" * (p178.BOUNDED_HEADER_MAX_BYTES + 1),
                artifact_key="bad",
                body_label="FX3",
                source_mode="CLEAN_ROOM_SYNTHETIC",
                total_file_bytes=811876768,
            )
        bad = p178.parse_ufu_header_4k(
            b"NOT_UFU_MAGIC" * 4,
            artifact_key="bad",
            body_label="FX3",
            source_mode="CLEAN_ROOM_SYNTHETIC",
            total_file_bytes=100,
        )
        self.assertFalse(bad.ufu_magic_ok)
        self.assertFalse(bad.fx3_0da1_pid_present)

    def test_10_missing_local_donors_fallback_cleanly_to_clean_room(self) -> None:
        from unittest.mock import patch

        with patch.object(
            p178,
            "resolve_phase178_donor_paths",
            return_value={"fx3_nflasha5": Path("/nonexistent/phase178/nflasha5.img")},
        ):
            da = p178.inspect_phase178_donors(force_clean_room=False)
        self.assertEqual(da.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(da.all_contracts_verified)

    def test_11_all_global_redlines_hard_locked_to_zero_and_false(self) -> None:
        rep = _get_clean_room_audit()
        red = rep["redlines"]
        self.assertTrue(red["p8_cp_mutation_forbidden"])
        self.assertFalse(red["persistent_emmc_writes_authorized"])
        self.assertFalse(red["spi_nor_write_authorized"])
        self.assertFalse(red["el3_payload_transmit_authorized"])
        self.assertEqual(red["physical_usb_packets_emitted"], 0)
        self.assertEqual(red["otp_fuse_touches"], 0)
        self.assertEqual(red["rpmb_counter_increments"], 0)
        self.assertEqual(red["wbi_persistent_writes"], 0)
        self.assertEqual(red["emmc_nflasha_write_count"], 0)
        self.assertEqual(red["c2pa_cert_mutation_bytes"], 0)
        self.assertEqual(red["p12_cert_mount_flags"], "MS_RDONLY")
        self.assertTrue(red["p12_rq_lic_erofs_locked"])
        self.assertEqual(red["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(red["donor_access_mode"], "O_RDONLY")


class TestStage31PillarASsbootWbi2Firewall(unittest.TestCase):
    """Pillar A — Sony SCEL ssboot / WBI2 Bootloader-Bypass Firewall HIL."""

    def test_12_unaccounted_wbi2_header_trap_caught_before_dualboot_activation(self) -> None:
        res = p178.coemulate_ssboot_wbi2_boot_path(
            wbi2_header_present=True,
            stage_a_cold_boot_enforced=False,
            require_dualboot_activation=True,
        )
        self.assertFalse(res.valid)
        self.assertTrue(res.wbi2_trap_caught_before_dualboot)
        self.assertEqual(res.boot_path_taken, "WBI2_LZO_PRSV_IMG_DIRECT_RESUME")
        self.assertFalse(res.stage_a_reached)
        self.assertFalse(res.stage_b_activated)
        self.assertEqual(res.wbi_persistent_writes, 0)
        self.assertEqual(res.status_code, "WBI2_TRAP_CAUGHT_BEFORE_DUALBOOT_ACTIVATION")

    def test_13_stock_fx3_0p5s_wbi2_warm_resume_preserved_when_stock_desired(self) -> None:
        res = p178.coemulate_ssboot_wbi2_boot_path(
            wbi2_header_present=True,
            stage_a_cold_boot_enforced=False,
            require_dualboot_activation=False,
        )
        self.assertTrue(res.valid)
        self.assertTrue(res.bypassed_to_stock_fx3)
        self.assertEqual(res.status_code, "STOCK_FX3_0P5S_WBI2_WARM_RESUME_OK")

    def test_14_stage_a_cold_boot_entry_reaches_fx6_stage_b(self) -> None:
        res = p178.coemulate_ssboot_wbi2_boot_path(
            wbi2_header_present=True,
            stage_a_cold_boot_enforced=True,
            require_dualboot_activation=True,
            sd_card_inserted=True,
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.boot_path_taken, "STAGE_A_COLD_BOOT_TO_FX6_STAGE_B")
        self.assertEqual(res.stage_a_init_chain, ("/sbin/init", "fx6-stage-a-verify"))
        self.assertTrue(res.stage_a_reached)
        self.assertTrue(res.stage_b_activated)
        self.assertEqual(res.wbi_persistent_writes, 0)

    def test_15_eh1_sd_card_removal_bypasses_to_stock_fx3_under_50us(self) -> None:
        res = p178.coemulate_ssboot_wbi2_boot_path(
            wbi2_header_present=True,
            stage_a_cold_boot_enforced=True,
            sd_card_inserted=False,
        )
        self.assertTrue(res.valid)
        self.assertTrue(res.bypassed_to_stock_fx3)
        self.assertFalse(res.stage_b_activated)
        self.assertLess(res.bypass_latency_us, 50.0)
        self.assertEqual(res.nflasha5_sha256_h0, res.nflasha5_sha256_current)

    def test_16_cross_kernel_wbi2_poison_attempt_blocked_fail_closed(self) -> None:
        res = p178.coemulate_ssboot_wbi2_boot_path(cross_kernel_wbi2_poison_attempt=True)
        self.assertFalse(res.valid)
        self.assertTrue(res.wbi2_trap_caught_before_dualboot)
        self.assertEqual(res.wbi_persistent_writes, 0)
        self.assertEqual(res.status_code, "BLOCKED_CROSS_KERNEL_WBI2_POISON")

    def test_17_stage_b_locks_blkroset_1_masks_pm_suspend_and_udm_preserves_h0_eq_h3(self) -> None:
        res = p178.coemulate_stage_b_wbi2_lock_and_eh1_uninstall()
        self.assertTrue(res.valid)
        self.assertEqual(res.nflasha5_blkroset, 1)
        self.assertEqual(res.pnflasha5_blkroset, 1)
        self.assertTrue(res.pm_suspend_disk_masked)
        self.assertTrue(res.proc_udm_snapshot_writes_masked)
        self.assertEqual(res.wbi_persistent_writes, 0)
        self.assertTrue(res.eh1_sd_removal_tested)
        self.assertLess(res.eh1_bypass_latency_us, 50.0)
        self.assertTrue(res.clean_uninstall_h2_to_h3_ok)
        self.assertTrue(res.stock_warmboot_0p5s_preserved)
        self.assertTrue(res.nflasha5_h0_eq_h3)
        self.assertEqual(res.nflasha5_sha256_h0, res.nflasha5_sha256_h3)

    def test_18_unlocked_blkroset_or_unmasked_udm_write_rejected_fail_closed(self) -> None:
        for kw in (
            {"blkroset_nflasha5": 0},
            {"blkroset_pnflasha5": 0},
            {"pm_suspend_disk_masked": False},
            {"proc_udm_snapshot_masked": False},
            {"unmasked_udm_write_requested": True},
        ):
            res = p178.coemulate_stage_b_wbi2_lock_and_eh1_uninstall(**kw)
            self.assertFalse(res.valid, msg=str(kw))
            self.assertEqual(res.wbi_persistent_writes, 0)
            self.assertEqual(res.status_code, "BLOCKED_WBI2_SNAPSHOT_CONTAMINATION_ATTEMPT")

    def test_19_pillar_a_full_evaluation_passes(self) -> None:
        pa = _get_clean_room_audit()["pillar_a_ssboot_wbi2_bootloader_firewall"]
        self.assertTrue(pa["passed"])


class TestStage31PillarB100CyclePowerlossAndBrownout(unittest.TestCase):
    """Pillar B — 100-Cycle NP-FZ100 Battery-Pull, 6.3V Brownout & EH2/EH3 HIL."""

    def test_20_100_cycle_battery_pull_and_brownout_zero_drift(self) -> None:
        res = p178.run_100cycle_powerloss_and_brownout_hil(cycles=100)
        self.assertTrue(res.valid)
        self.assertEqual(res.cycles_total, 100)
        self.assertEqual(res.cycles_passed, 100)
        self.assertEqual(res.h0_eq_h3_partitions, 6)
        self.assertEqual(res.journal_metadata_drift_count, 0)
        self.assertEqual(res.rsv_orphan_count, 0)
        self.assertEqual(res.emmc_nflasha_write_count, 0)
        self.assertEqual(sum(res.scenario_counts.values()), 100)
        self.assertEqual(res.eh2_safe_boot_count, 25)
        self.assertEqual(res.eh3_crc32_fallback_count, 25)
        self.assertEqual(res.brownout_6v3_salvage_count, 25)

    def test_21_all_six_protected_partitions_audited_for_zero_drift(self) -> None:
        res = p178.run_100cycle_powerloss_and_brownout_hil(cycles=100)
        self.assertEqual(
            res.protected_partitions,
            ("p1", "p2:/setting", "p5:/wbi", "p12:/cert", "p15:/usr", "p18:/lens"),
        )
        for part in res.protected_partitions:
            drifted = p178.run_100cycle_powerloss_and_brownout_hil(
                cycles=10,
                inject_partition_drift=part,
            )
            self.assertFalse(drifted.valid, msg=part)
            self.assertEqual(drifted.journal_metadata_drift_count, 1, msg=part)
            self.assertEqual(drifted.status_code, "BLOCKED_EMMC_JOURNAL_METADATA_DRIFT")

    def test_22_brownout_6v3_enc_wfi_stop_salvages_rsv_to_mxf(self) -> None:
        ok = p178.simulate_6v3_brownout_rsv_to_mxf_salvage(voltage_mv=6300, enc_wfi_stop_enabled=True)
        self.assertTrue(ok.valid)
        self.assertTrue(ok.enc_wfi_stop_triggered)
        self.assertTrue(ok.exfat_rsv_to_mxf_salvaged)
        self.assertEqual(ok.rsv_orphan_count, 0)
        self.assertEqual(ok.emmc_nflasha_write_count, 0)

        bad = p178.simulate_6v3_brownout_rsv_to_mxf_salvage(voltage_mv=6300, enc_wfi_stop_enabled=False)
        self.assertFalse(bad.valid)
        self.assertEqual(bad.rsv_orphan_count, 1)
        self.assertEqual(bad.status_code, "BLOCKED_BROWNOUT_UNCLOSED_RSV_ORPHAN")

        corrupt = p178.simulate_6v3_brownout_rsv_to_mxf_salvage(rsv_payload_valid=False)
        self.assertFalse(corrupt.valid)
        self.assertEqual(corrupt.status_code, "BLOCKED_CORRUPT_RSV_SALVAGE_REJECTED")

    def test_23_eh2_disp_menu_shutter_safe_combo_cold_boot(self) -> None:
        ok = p178.simulate_eh2_safe_combo_cold_boot(combo="DISP+MENU+SHUTTER")
        self.assertTrue(ok.valid)
        self.assertEqual(ok.fallback_target, "STOCK_FX3_7_02_SAFE_COLD_BOOT")
        self.assertEqual(ok.emmc_nflasha_write_count, 0)

        bad = p178.simulate_eh2_safe_combo_cold_boot(combo="UNKNOWN_KEY")
        self.assertFalse(bad.valid)
        self.assertEqual(bad.status_code, "BLOCKED_UNKNOWN_EH2_SAFE_COMBO")

    def test_24_eh3_1byte_libjit_crc32_caught_fail_closed(self) -> None:
        ok = p178.simulate_eh3_libjit_1byte_crc32_fallback(inject_1byte_bitflip=True, crc32_guard_enabled=True)
        self.assertTrue(ok.valid)
        self.assertTrue(ok.crc32_verified)
        self.assertTrue(ok.corrupt_byte_detected)
        self.assertEqual(ok.fallback_target, "STOCK_FX3_7_02_FAIL_CLOSED")
        self.assertEqual(ok.status_code, "EH3_1BYTE_LIBJIT_CRC32_CAUGHT_FAIL_CLOSED_STOCK_OK")

        bypassed = p178.simulate_eh3_libjit_1byte_crc32_fallback(inject_1byte_bitflip=True, crc32_guard_enabled=False)
        self.assertFalse(bypassed.valid)
        self.assertEqual(bypassed.status_code, "BLOCKED_EH3_CRC32_BYPASS")

    def test_25_powerloss_runner_rejects_invalid_cycles_and_bypassed_guards(self) -> None:
        with self.assertRaises(p178.RealHwSsbootWbi2Slot1Error):
            p178.run_100cycle_powerloss_and_brownout_hil(cycles=0)
        b1 = p178.run_100cycle_powerloss_and_brownout_hil(cycles=8, disable_eh3_crc32_guard=True)
        self.assertFalse(b1.valid)
        b2 = p178.run_100cycle_powerloss_and_brownout_hil(cycles=8, disable_brownout_encwfistop=True)
        self.assertFalse(b2.valid)

    def test_26_pillar_b_full_evaluation_passes(self) -> None:
        pb = _get_clean_room_audit()["pillar_b_100cycle_powerloss_brownout_hil"]
        self.assertTrue(pb["passed"])


class TestStage31PillarCSlot1BodydataC2paWifi(unittest.TestCase):
    """Pillar C — Official Ver. 7.02 BODYDATA.DAT >=2.04 Floor, Slot-1 C2PA & WPA2/WPA3."""

    def test_27_ver_702_and_204_floor_admitted_slot1_under_100us_stage_a_bypass(self) -> None:
        for fw in ("2.04", "3.00", "5.00", "6.00", "7.02"):
            res = p178.evaluate_bodydata_702_slot1_ufu_gate(current_body_fw=fw, slot=1)
            self.assertTrue(res.admitted, msg=fw)
            self.assertTrue(res.stage_a_bypass_to_stock_fx3)
            self.assertLess(res.stage_a_bypass_us, 100.0)
            self.assertEqual(res.file_bytes, 811876768)

    def test_28_fw_202_or_lower_rejected_preventing_7l_7s_led_fault(self) -> None:
        for fw in ("1.00", "2.00", "2.02", "2.03"):
            res = p178.evaluate_bodydata_702_slot1_ufu_gate(current_body_fw=fw, slot=1)
            self.assertFalse(res.admitted, msg=fw)
            self.assertTrue(res.led_blink_fault_prevented)
            self.assertEqual(res.led_fault_code, "7L+7S")
            self.assertFalse(res.stage_a_bypass_to_stock_fx3)
            self.assertEqual(res.status_code, "BLOCKED_FX3_FW_BELOW_2_04_FLOOR_7L_7S")

    def test_29_slot2_placement_and_duplicate_bodydata_1_dat_rejected(self) -> None:
        s2 = p178.evaluate_bodydata_702_slot1_ufu_gate(current_body_fw="7.02", slot=2)
        self.assertFalse(s2.admitted)
        self.assertEqual(s2.status_code, "BLOCKED_BODYDATA_NOT_ON_SLOT_1_ROOT")

        dup = p178.evaluate_bodydata_702_slot1_ufu_gate(
            current_body_fw="7.02",
            slot=1,
            filename="BODYDATA (1).DAT",
            duplicate_files=("BODYDATA.DAT", "BODYDATA (1).DAT"),
        )
        self.assertFalse(dup.admitted)
        self.assertTrue(dup.duplicate_files_detected)
        self.assertEqual(dup.status_code, "BLOCKED_BODYDATA_DUPLICATE_OR_RENAMED")

    def test_30_bad_ufu_magic_or_wrong_file_bytes_rejected(self) -> None:
        bad_magic = p178.evaluate_bodydata_702_slot1_ufu_gate(ufu_magic_valid=False)
        self.assertFalse(bad_magic.admitted)
        self.assertEqual(bad_magic.status_code, "BLOCKED_INVALID_UFU_MAGIC_OR_BYTES")

        bad_size = p178.evaluate_bodydata_702_slot1_ufu_gate(file_bytes=847081840)  # FX6 size!
        self.assertFalse(bad_size.admitted)
        self.assertEqual(bad_size.status_code, "BLOCKED_INVALID_UFU_MAGIC_OR_BYTES")

    def test_31_invalid_firmware_string_raises_domain_error(self) -> None:
        with self.assertRaises(p178.RealHwSsbootWbi2Slot1Error):
            p178.evaluate_bodydata_702_slot1_ufu_gate(current_body_fw="v7.02-dirty")

    def test_32_c2pa_slot1_100_license_cap_and_p12_rq_lic_erofs_lock(self) -> None:
        ok100 = p178.evaluate_slot1_c2pa_and_wifi_security(slot=1, license_count=100, wifi_security_mode="WPA3")
        self.assertTrue(ok100.valid)
        self.assertEqual(ok100.max_licenses_allowed, 100)
        self.assertEqual(ok100.rq_lic_path, "p12:/cert/RQ_LIC.DAT")
        self.assertTrue(ok100.p12_erofs_locked)
        self.assertEqual(ok100.c2pa_cert_mutation_bytes, 0)

        over101 = p178.evaluate_slot1_c2pa_and_wifi_security(slot=1, license_count=101, wifi_security_mode="WPA3")
        self.assertFalse(over101.valid)
        self.assertEqual(over101.status_code, "BLOCKED_C2PA_EXCEEDS_100_LICENSE_CAP")

        zero_lic = p178.evaluate_slot1_c2pa_and_wifi_security(slot=1, license_count=0, wifi_security_mode="WPA3")
        self.assertFalse(zero_lic.valid)

        slot2 = p178.evaluate_slot1_c2pa_and_wifi_security(slot=2, license_count=10, wifi_security_mode="WPA3")
        self.assertFalse(slot2.valid)
        self.assertEqual(slot2.status_code, "BLOCKED_C2PA_PACKAGE_NOT_ON_SLOT_1")

        rq_write = p178.evaluate_slot1_c2pa_and_wifi_security(write_rq_lic_requested=True)
        self.assertFalse(rq_write.valid)
        self.assertEqual(rq_write.c2pa_cert_mutation_bytes, 0)
        self.assertEqual(rq_write.status_code, "BLOCKED_P12_RQ_LIC_EROFS_LOCKED")

    def test_33_wpa2_wpa3_floor_enforced_and_wep_wpa1_ipsec_rejected(self) -> None:
        for mode in ("WPA2", "WPA3"):
            ok = p178.evaluate_slot1_c2pa_and_wifi_security(wifi_security_mode=mode)
            self.assertTrue(ok.valid, msg=mode)
            self.assertTrue(ok.wifi_security_admitted, msg=mode)
        for bad in ("WEP", "WPA1", "IPsec"):
            rej = p178.evaluate_slot1_c2pa_and_wifi_security(wifi_security_mode=bad)
            self.assertFalse(rej.valid, msg=bad)
            self.assertFalse(rej.wifi_security_admitted, msg=bad)
            self.assertEqual(rej.status_code, "BLOCKED_DEPRECATED_WIFI_SECURITY_FLOOR", msg=bad)

    def test_34_pillar_c_full_evaluation_passes(self) -> None:
        pc = _get_clean_room_audit()["pillar_c_slot1_bodydata_c2pa_wifi_hil"]
        self.assertTrue(pc["passed"])


class TestStage31PillarDRedlinesAndSuiteIntegration(unittest.TestCase):
    """Pillar D hard safety redlines, suite 31/31 orchestration, CLI & hygiene."""

    def test_35_hard_safety_redline_probes_block_every_forbidden_operation(self) -> None:
        base = p178.probe_hard_safety_redline()
        self.assertTrue(base.valid)
        self.assertFalse(base.persistent_emmc_writes_authorized)
        self.assertFalse(base.spi_nor_write_authorized)
        self.assertFalse(base.el3_payload_transmit_authorized)
        self.assertEqual(base.physical_usb_packets_emitted, 0)
        self.assertEqual(base.otp_fuse_touches, 0)
        self.assertEqual(base.rpmb_counter_increments, 0)

        for flag in (
            "authorize_persistent_emmc_writes",
            "authorize_spi_nor_write",
            "authorize_el3_payload_transmit",
            "emit_physical_usb_packet",
            "touch_otp_fuse",
            "increment_rpmb_counter",
        ):
            res = p178.probe_hard_safety_redline(**{flag: True})
            self.assertFalse(res.valid, msg=flag)
            self.assertFalse(res.persistent_emmc_writes_authorized)
            self.assertFalse(res.spi_nor_write_authorized)
            self.assertFalse(res.el3_payload_transmit_authorized)
            self.assertEqual(res.physical_usb_packets_emitted, 0)
            self.assertEqual(res.otp_fuse_touches, 0)
            self.assertEqual(res.rpmb_counter_increments, 0)
            self.assertIn("BLOCKED_HARD_SAFETY_REDLINE_", res.status_code)

    def test_36_pillar_d_full_evaluation_passes(self) -> None:
        pd = _get_clean_room_audit()["pillar_d_hard_safety_redlines"]
        self.assertTrue(pd["passed"])

    def test_37_audit_digest_sha256_is_deterministic_across_repeated_runs(self) -> None:
        r1 = p178.run_phase178_realhw_ssboot_wbi2_powerloss_slot1_ufu_hil(force_clean_room=True)
        r2 = p178.run_phase178_realhw_ssboot_wbi2_powerloss_slot1_ufu_hil(force_clean_room=True)
        self.assertEqual(r1["audit_digest_sha256"], r2["audit_digest_sha256"])
        self.assertEqual(len(r1["audit_digest_sha256"]), 64)

        body = dict(r1)
        obs = body.pop("audit_digest_sha256")
        exp = hashlib.sha256(
            json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        self.assertEqual(obs, exp)

    def test_38_json_serialization_contains_no_nan_infinity_or_raw_bytes(self) -> None:
        for rep in (_get_clean_room_audit(), _get_default_audit()):
            txt = json.dumps(rep, sort_keys=True, allow_nan=False)
            self.assertNotIn("NaN", txt)
            self.assertNotIn("Infinity", txt)
            self.assertNotIn("b'", txt)
            self.assertNotIn("WBI2\\x00", txt)

    def test_39_stage31_inprocess_runtime_under_generous_5s_and_fast_0p15s_target(self) -> None:
        # Warm cache first if local mode, then verify execution well below generous 5.0s budget
        _ = p178.run_phase178_realhw_ssboot_wbi2_powerloss_slot1_ufu_hil(force_clean_room=True)
        t0 = time.monotonic()
        rep_clean = p178.run_phase178_realhw_ssboot_wbi2_powerloss_slot1_ufu_hil(force_clean_room=True)
        dt_clean = time.monotonic() - t0
        self.assertTrue(rep_clean["all_checks_passed"])
        self.assertLess(dt_clean, 5.0)
        self.assertLess(dt_clean, 0.75 if __import__("os").environ.get("GITHUB_ACTIONS") == "true" else 0.15)

        t1 = time.monotonic()
        rep_def = p178.run_phase178_realhw_ssboot_wbi2_powerloss_slot1_ufu_hil(env=os.environ)
        dt_def = time.monotonic() - t1
        self.assertTrue(rep_def["all_checks_passed"])
        self.assertLess(dt_def, 5.0)

    def test_40_cli_main_clean_room_summary_and_json_exit_0(self) -> None:
        buf_sum = io.StringIO()
        with contextlib.redirect_stdout(buf_sum):
            rc_sum = p178.main(["--self-test", "--clean-room", "--summary"])
        self.assertEqual(rc_sum, 0)
        out_sum = buf_sum.getvalue()
        self.assertIn("[PASS] Phase 178 Stage 31 (31/31)", out_sum)
        self.assertIn("mode=CLEAN_ROOM_SYNTHETIC", out_sum)
        self.assertIn("cycles=100/100", out_sum)
        self.assertIn("drift=0", out_sum)

        buf_json = io.StringIO()
        with contextlib.redirect_stdout(buf_json):
            rc_json = p178.main(["--self-test", "--clean-room", "--json"])
        self.assertEqual(rc_json, 0)
        parsed = json.loads(buf_json.getvalue())
        self.assertTrue(parsed["all_checks_passed"])
        self.assertEqual(parsed["stage_index"], 31)
        self.assertEqual(parsed["milestone"], "31/31")

    def test_41_cli_invalid_flag_exits_nonzero(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                str(FX3_VM_DIR / "realhw_ssboot_wbi2_powerloss_and_slot1_ufu_coemulator.py"),
                "--definitely-invalid-flag",
            ],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertNotEqual(proc.returncode, 0)

    def test_42_suite_wires_stage31_and_skip_phase178_toggle(self) -> None:
        rep_on = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig(force_clean_room=True))
        self.assertTrue(rep_on["all_checks_passed"])
        self.assertIn("stage31_realhw_ssboot_wbi2_powerloss_slot1_ufu_hil", rep_on)
        s31 = rep_on["stage31_realhw_ssboot_wbi2_powerloss_slot1_ufu_hil"]
        self.assertTrue(s31["all_checks_passed"])
        self.assertEqual(s31["wbi_persistent_writes"], 0)
        self.assertEqual(s31["emmc_nflasha_write_count"], 0)
        self.assertFalse(s31["persistent_emmc_writes_authorized"])
        self.assertFalse(s31["spi_nor_write_authorized"])
        self.assertFalse(s31["el3_payload_transmit_authorized"])
        self.assertEqual(s31["physical_usb_packets_emitted"], 0)
        self.assertEqual(s31["otp_fuse_touches"], 0)
        self.assertEqual(s31["rpmb_counter_increments"], 0)

        stage_keys = [k for k in rep_on if re.match(r"^stage\d+_", k)]
        self.assertGreaterEqual(len(stage_keys), 31)

        rep_skip = suite.run_fx3_vm_coemulation_suite(
            suite.CoEmulationConfig(
                force_clean_room=True,
                include_phase178_realhw_ssboot_wbi2_powerloss_slot1_ufu_hil=False,
            )
        )
        self.assertTrue(rep_skip["all_checks_passed"])
        self.assertNotIn("stage31_realhw_ssboot_wbi2_powerloss_slot1_ufu_hil", rep_skip)
        self.assertEqual(len([k for k in rep_skip if re.match(r"^stage\d+_", k)]), len(stage_keys) - 1)

    def test_43_all_31_of_31_stages_present_and_passing_in_suite(self) -> None:
        rep = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig(force_clean_room=True))
        self.assertTrue(rep["stage1_coldboot_and_bt"]["all_checks_passed"])
        self.assertTrue(rep["stage2_dual_isa_cp_shooting"]["all_checks_passed"])
        self.assertTrue(rep["stage3_soft_gpe_hud_ramfb"]["all_checks_passed"])
        for idx in range(4, 32):
            matches = [k for k in rep if k.startswith(f"stage{idx}_")]
            self.assertEqual(len(matches), 1, msg=f"Missing or duplicate stage{idx}_* key")
            self.assertTrue(rep[matches[0]]["all_checks_passed"], msg=matches[0])

    def test_44_suite_subprocess_summary_and_skip_phase178_flag(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        proc = subprocess.run(
            [
                sys.executable,
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
        self.assertIn("realhw_ssboot_wbi2_powerloss_slot1_ufu_hil=CLEAN_ROOM_SYNTHETIC", proc.stdout)

        proc_skip = subprocess.run(
            [
                sys.executable,
                "-B",
                str(FX3_VM_DIR / "fx3_vm_coemulation_suite.py"),
                "--clean-room",
                "--skip-phase178",
                "--summary",
            ],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc_skip.returncode, 0, msg=proc_skip.stderr)
        self.assertNotIn("realhw_ssboot_wbi2_powerloss_slot1_ufu_hil=", proc_skip.stdout)

    def test_45_suite_31_stages_generous_runtime_and_json_cli(self) -> None:
        t0 = time.monotonic()
        rep_clean = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig(force_clean_room=True))
        dt_clean = time.monotonic() - t0
        self.assertTrue(rep_clean["all_checks_passed"])
        self.assertGreaterEqual(len([k for k in rep_clean if re.match(r"^stage\d+_", k)]), 31)
        self.assertLess(dt_clean, 5.0)

        t1 = time.monotonic()
        rep_def = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig())
        dt_def = time.monotonic() - t1
        self.assertTrue(rep_def["all_checks_passed"])
        self.assertGreaterEqual(len([k for k in rep_def if re.match(r"^stage\d+_", k)]), 31)
        self.assertLess(dt_def, 5.0)

        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        p_json = subprocess.run(
            [
                sys.executable,
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
        self.assertEqual(p_json.returncode, 0, msg=p_json.stderr)
        d_json = json.loads(p_json.stdout)
        self.assertTrue(d_json["all_checks_passed"])
        self.assertGreaterEqual(len([k for k in d_json if re.match(r"^stage\d+_", k)]), 31)

    def test_46_source_hygiene_rdonly_and_no_forbidden_flags_or_port(self) -> None:
        src = (FX3_VM_DIR / "realhw_ssboot_wbi2_powerloss_and_slot1_ufu_coemulator.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("os.O_RDONLY", src)
        self.assertIn("sys.dont_write_bytecode = True", src)
        self.assertNotIn("O_WR" + "ONLY", src)
        self.assertNotIn("O_RD" + "WR", src)
        forbidden_port = str(87 * 100 + 68)
        self.assertNotIn(forbidden_port, src)

    def test_47_clean_room_and_local_parity_on_pillars_and_schema(self) -> None:
        r_clean = _get_clean_room_audit()
        r_def = _get_default_audit()
        self.assertEqual(r_clean["schema"], r_def["schema"])
        self.assertEqual(r_clean["stage_index"], r_def["stage_index"])
        self.assertEqual(r_clean["milestone"], r_def["milestone"])
        self.assertEqual(r_clean["redlines"], r_def["redlines"])
        self.assertEqual(
            r_clean["pillar_a_ssboot_wbi2_bootloader_firewall"],
            r_def["pillar_a_ssboot_wbi2_bootloader_firewall"],
        )
        self.assertEqual(
            r_clean["pillar_b_100cycle_powerloss_brownout_hil"],
            r_def["pillar_b_100cycle_powerloss_brownout_hil"],
        )
        self.assertEqual(
            r_clean["pillar_c_slot1_bodydata_c2pa_wifi_hil"],
            r_def["pillar_c_slot1_bodydata_c2pa_wifi_hil"],
        )
        self.assertEqual(
            r_clean["pillar_d_hard_safety_redlines"],
            r_def["pillar_d_hard_safety_redlines"],
        )

    def test_48_wbi2_header_parser_rejects_corrupt_magic_fail_closed(self) -> None:
        with self.assertRaises(p178.RealHwSsbootWbi2Slot1Error):
            p178._parse_wbi2_header_buf(
                b"BADMAGIC" + struct.pack("<II", 10, 0),
                file_bytes=1234,
                artifact_key="bad_wbi2",
                body_label="FX3_7.02",
                source_mode="CLEAN_ROOM_SYNTHETIC",
            )


if __name__ == "__main__":
    unittest.main()
