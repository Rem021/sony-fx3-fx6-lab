"""Phase 136 dual-mode test suite: Stage-288 SET_FILE2 P0 hardening, U4/U5/U6 closures, and Tier-0 stop-gate."""

from __future__ import annotations

import copy
import json
import os
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.dont_write_bytecode = True

import fx6_closure
from fx6_closure.__main__ import main as cli_main
from fx6_closure.donor_paths import is_forced_clean_room
from fx6_closure.realhw_jiritsu_and_tier0_dumper_auditor import (
    JBUSY_PRESENT_STATUS,
    JIRITSU_0X1001_COMMANDS,
    KERNEL_4K_PAGE_ALIGN,
    KERNEL_64K_PAGE_ALIGN,
    LIBJIRITSU_EXPECTED_SHA256,
    LIBJIRITSU_EXPECTED_SIZE,
    LIBJIRITSU_PINNED_INSNS,
    PHASE_136_SCHEMA,
    STAGE288_FRAME_MAGIC,
    STAGE288_HEADER_SIZE,
    audit_elf64_payload_so,
    audit_pillar1_jiritsu_dispatch_and_stage288_p0,
    audit_pillar2_u4_zero_sector0_bridge,
    audit_pillar3_u5_p1_oneshot_fallback,
    audit_pillar4_tier0_cold_backup_gate,
    build_hardened_jit_so_fixture,
    decode_aarch64_insn,
    decode_and_verify_stage288_output_frame,
    disassemble_aarch64_window,
    encode_stage288_output_frame,
    populate_phase136_tier0_bundle,
    read_only_mmap_bytes,
    run_phase136_realhw_jiritsu_tier0_audit,
    validate_jiritsu_wire_sequence,
    validate_stage288_hardened_payload_contract,
    verify_p1_oneshot_clear_state,
    verify_phase136_report,
    verify_strategy_a_bridge_state,
)


def _valid_wire_payloads() -> tuple[bytes, bytes, bytes]:
    so = build_hardened_jit_so_fixture()
    set_path = b"\x00/tmp/jiritsu/out.bin\x00"
    set_file2 = b"\x00\xff\x00" + so
    get_file2 = b"\x00\xff\x00"
    return set_path, set_file2, get_file2


class TestPhase136RealHwJiritsuTier0(unittest.TestCase):
    """44 dual-mode unit tests covering all 4 Phase 136 pillars and fault-injection drills."""

    # ------------------------------------------------------------------
    # Dual-mode / Decoder / Export / CLI / Tamper Baseline (1..8)
    # ------------------------------------------------------------------

    def test_01_public_exports_present_in_package_init(self) -> None:
        for sym in (
            "PHASE_136_SCHEMA",
            "run_phase136_realhw_jiritsu_tier0_audit",
            "verify_phase136_report",
            "audit_pillar1_jiritsu_dispatch_and_stage288_p0",
            "audit_pillar2_u4_zero_sector0_bridge",
            "audit_pillar3_u5_p1_oneshot_fallback",
            "audit_pillar4_tier0_cold_backup_gate",
            "populate_phase136_tier0_bundle",
        ):
            self.assertTrue(hasattr(fx6_closure, sym), f"Missing export: {sym}")

    def test_02_master_audit_passes_current_mode(self) -> None:
        rep = run_phase136_realhw_jiritsu_tier0_audit()
        self.assertTrue(rep.all_checks_passed)
        self.assertEqual(rep.schema, PHASE_136_SCHEMA)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.usb_device_attach_executed)
        self.assertFalse(rep.persistent_write_release)
        self.assertEqual(rep.emmc_bytes_mutated, 0)
        self.assertEqual(rep.raw_firmware_slices_emitted, 0)
        self.assertEqual(rep.errors, ())
        expected_mode = "CLEAN_ROOM_SYNTHETIC" if is_forced_clean_room() else "LOCAL_DONOR_O_RDONLY"
        self.assertEqual(rep.verification_mode, expected_mode)
        v = verify_phase136_report(rep.to_dict())
        self.assertTrue(v.valid, v.errors)

    def test_03_master_audit_passes_clean_room_and_deterministic_hash(self) -> None:
        r1 = run_phase136_realhw_jiritsu_tier0_audit(synthetic_clean_room=True)
        r2 = run_phase136_realhw_jiritsu_tier0_audit(synthetic_clean_room=True)
        self.assertTrue(r1.all_checks_passed)
        self.assertEqual(r1.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(r1.report_sha256, r2.report_sha256)
        self.assertTrue(verify_phase136_report(r1.to_dict()).valid)

    def test_04_read_only_mmap_bytes_reads_exact_content(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "sample.bin"
            payload = b"SONY_RO_TEST_" + bytes(range(64))
            p.write_bytes(payload)
            got = read_only_mmap_bytes(p)
            self.assertEqual(got, payload)
            empty_p = Path(td) / "empty.bin"
            empty_p.write_bytes(b"")
            self.assertEqual(read_only_mmap_bytes(empty_p), b"")

    def test_05_pure_python_aarch64_decoder_covers_pinned_opcodes(self) -> None:
        insns = [
            (0x976C, 0xF0000120, "adrp"),
            (0x9770, 0x913BD400, "add"),
            (0x9774, 0x97FFF10F, "bl"),
            (0x977C, 0x34000E40, "cbz"),
            (0x8A1C, 0x3940A280, "ldrb"),
            (0x95A4, 0x7100081F, "cmp"),
            (0x9944, 0x52800234, "movz"),
            (0x9948, 0x72A20014, "movk"),
        ]
        for pc, word, expected_mnemonic in insns:
            dec = decode_aarch64_insn(word, pc)
            self.assertEqual(dec.mnemonic, expected_mnemonic)
            self.assertEqual(dec.decoder_backend, "pure_python_aarch64")

    def test_06_disassemble_window_fallback_works_without_capstone(self) -> None:
        code = struct.pack("<IIII", 0xF0000120, 0x913BD400, 0x97FFF10F, 0x34000E40)
        res = disassemble_aarch64_window(code, 0x976C, use_capstone=False)
        self.assertEqual(len(res), 4)
        self.assertEqual([d.mnemonic for d in res], ["adrp", "add", "bl", "cbz"])

    def test_07_report_json_emits_zero_raw_firmware_slices_and_tamper_fails(self) -> None:
        rep = run_phase136_realhw_jiritsu_tier0_audit(synthetic_clean_room=True)
        raw_json = rep.to_deterministic_json()
        self.assertNotIn("ELF", raw_json)  # no raw ELF header slice serialized
        tampered = copy.deepcopy(rep.to_dict())
        tampered["pillar2_u4_zero_sector0"]["u4_closed"] = False
        res = verify_phase136_report(tampered)
        self.assertFalse(res.valid)
        self.assertTrue(any("tamper mismatch" in e for e in res.errors))

    def test_08_tamper_verifier_rejects_unlocked_emmc_or_usb_flags(self) -> None:
        rep = run_phase136_realhw_jiritsu_tier0_audit(synthetic_clean_room=True)
        for field in ("persistent_emmc_writes_authorized", "usb_device_attach_executed", "persistent_write_release"):
            d = copy.deepcopy(rep.to_dict())
            d[field] = True
            res = verify_phase136_report(d)
            self.assertFalse(res.valid)
            self.assertTrue(any(field in e for e in res.errors))

    # ------------------------------------------------------------------
    # Pillar 1: Jiritsu 0x40 U6 + Stage-288 SET_FILE2 P0 Hardening (9..24)
    # ------------------------------------------------------------------

    def test_09_pillar1_u6_dispatch_table_closes_19_opcodes(self) -> None:
        p1 = audit_pillar1_jiritsu_dispatch_and_stage288_p0()
        self.assertTrue(p1.all_checks_passed)
        self.assertTrue(p1.u6_closed)
        self.assertEqual(p1.u6_command_count, 19)
        self.assertEqual(len(JIRITSU_0X1001_COMMANDS), 19)
        self.assertEqual(p1.u6_direct_setting_or_nflasha_opcodes, ())
        self.assertEqual(p1.libjiritsu_sha256, LIBJIRITSU_EXPECTED_SHA256)
        self.assertEqual(p1.libjiritsu_size, LIBJIRITSU_EXPECTED_SIZE)
        self.assertTrue(p1.all_pinned_insns_matched)
        self.assertEqual(p1.pinned_insn_count, len(LIBJIRITSU_PINNED_INSNS))

    def test_10_pillar1_ld_emmc_devno_setup_nflash_verified(self) -> None:
        p1 = audit_pillar1_jiritsu_dispatch_and_stage288_p0()
        self.assertTrue(p1.ld_2_25_64k_align_verified)
        self.assertTrue(p1.emmc_devno_setup_nflash_verified)
        self.assertTrue(p1.dev_nflasha_whole_device_symlink_present)

    def test_11_wire_sequence_positive_nominal(self) -> None:
        sp, sf2, gf2 = _valid_wire_payloads()
        res = validate_jiritsu_wire_sequence(sp, sf2, gf2, jbusy_exists=False)
        self.assertTrue(res.valid)
        self.assertTrue(res.set_path_prefix_ok)
        self.assertTrue(res.set_file2_prefix_ok)
        self.assertTrue(res.get_file2_prefix_ok)
        self.assertTrue(res.selector_ok)
        self.assertTrue(res.jbusy_absent_ok)
        self.assertEqual(res.expected_status, 0)

    def test_12_wire_fault_jbusy_present_triggers_0x10000011(self) -> None:
        sp, sf2, gf2 = _valid_wire_payloads()
        res = validate_jiritsu_wire_sequence(sp, sf2, gf2, jbusy_exists=True)
        self.assertFalse(res.valid)
        self.assertFalse(res.jbusy_absent_ok)
        self.assertEqual(res.expected_status, JBUSY_PRESENT_STATUS)

    def test_13_wire_fault_bad_set_file2_prefix_00_ff_00_rejected(self) -> None:
        sp, sf2, gf2 = _valid_wire_payloads()
        bad_sf2 = b"\x00\x00\x00" + sf2[3:]
        res = validate_jiritsu_wire_sequence(sp, bad_sf2, gf2, jbusy_exists=False)
        self.assertFalse(res.valid)
        self.assertFalse(res.set_file2_prefix_ok)

    def test_14_wire_fault_selector_0x02_rejected(self) -> None:
        sp, sf2, gf2 = _valid_wire_payloads()
        bad_sf2 = b"\x00\x02\x00" + sf2[3:]
        res = validate_jiritsu_wire_sequence(sp, bad_sf2, gf2, jbusy_exists=False)
        self.assertFalse(res.valid)
        self.assertFalse(res.selector_ok)

    def test_15_wire_fault_bad_set_path_and_get_file2_prefix_rejected(self) -> None:
        sp, sf2, gf2 = _valid_wire_payloads()
        res = validate_jiritsu_wire_sequence(b"\x01/tmp/jiritsu/libJit.so\x00", sf2, b"\x01/tmp/jiritsu/out\x00")
        self.assertFalse(res.valid)
        self.assertFalse(res.set_path_prefix_ok)
        self.assertFalse(res.get_file2_prefix_ok)

    def test_16_elf64_64k_aligned_fixture_valid(self) -> None:
        so = build_hardened_jit_so_fixture(page_align=KERNEL_64K_PAGE_ALIGN)
        audit = audit_elf64_payload_so(so, require_64k_align=True)
        self.assertTrue(audit.valid, audit.errors)
        self.assertTrue(audit.is_aarch64_dyn)
        self.assertEqual(audit.pt_load_count, 2)
        self.assertTrue(audit.pt_load_64k_aligned)
        self.assertEqual(audit.page_align_values, (KERNEL_64K_PAGE_ALIGN, KERNEL_64K_PAGE_ALIGN))
        self.assertFalse(audit.rw_rx_page_merge_hazard)
        self.assertTrue(audit.dynamic_tables_inside_pt_load)
        self.assertEqual(audit.dt_hash_tuple, (1, 1, 0, 0))
        self.assertTrue(audit.dt_hash_valid_1100)

    def test_17_elf64_4k_page_merge_hazard_rejected(self) -> None:
        so = build_hardened_jit_so_fixture(page_align=KERNEL_4K_PAGE_ALIGN)
        audit = audit_elf64_payload_so(so, require_64k_align=True)
        self.assertFalse(audit.valid)
        self.assertFalse(audit.pt_load_64k_aligned)
        self.assertTrue(audit.rw_rx_page_merge_hazard)

    def test_18_elf64_dt_hash_oob_outside_pt_load_rejected(self) -> None:
        so = build_hardened_jit_so_fixture(dt_hash_oob=True)
        audit = audit_elf64_payload_so(so, require_64k_align=True)
        self.assertFalse(audit.valid)
        self.assertFalse(audit.dynamic_tables_inside_pt_load)

    def test_19_elf64_corrupt_dt_hash_tuple_rejected(self) -> None:
        so = build_hardened_jit_so_fixture(corrupt_dt_hash=True)
        audit = audit_elf64_payload_so(so, require_64k_align=True)
        self.assertFalse(audit.valid)
        self.assertFalse(audit.dt_hash_valid_1100)
        self.assertNotEqual(audit.dt_hash_tuple, (1, 1, 0, 0))

    def test_20_stage288_output_frame_8b_magic_len_crc32_roundtrip(self) -> None:
        payload = b"8246" + b"2.00" + bytes(504)
        frame = encode_stage288_output_frame(payload)
        self.assertEqual(len(frame), STAGE288_HEADER_SIZE + 512)
        self.assertEqual(frame[:2], STAGE288_FRAME_MAGIC)
        audit = decode_and_verify_stage288_output_frame(frame, expected_payload_len=512)
        self.assertTrue(audit.valid)
        self.assertTrue(audit.magic_ok)
        self.assertEqual(audit.declared_length, 512)
        self.assertEqual(audit.actual_payload_length, 512)
        self.assertTrue(audit.crc32_matched)

    def test_21_stage288_output_frame_fault_bad_magic_and_crc32_rejected(self) -> None:
        frame = bytearray(encode_stage288_output_frame(b"A" * 512))
        bad_magic = bytes(b"XX") + bytes(frame[2:])
        self.assertFalse(decode_and_verify_stage288_output_frame(bad_magic).valid)
        bad_crc = bytearray(frame)
        bad_crc[10] ^= 0xFF
        audit_crc = decode_and_verify_stage288_output_frame(bytes(bad_crc))
        self.assertFalse(audit_crc.valid)
        self.assertFalse(audit_crc.crc32_matched)

    def test_22_stage288_hardening_contract_nominal_passes(self) -> None:
        so = build_hardened_jit_so_fixture()
        frame = encode_stage288_output_frame(b"S" * 512)
        audit = validate_stage288_hardened_payload_contract(
            so,
            frame,
            dev_nflasha_verified=True,
            p6_persistence_acknowledged=True,
        )
        self.assertTrue(audit.all_p0_items_closed)
        self.assertTrue(audit.p0_1_self_unlink_at_entry)
        self.assertTrue(audit.p0_2_no_truncate_on_read_fail)
        self.assertTrue(audit.p0_3_fixed_8b_magic_len_crc32_header)
        self.assertTrue(audit.p0_4_dev_nflasha_node_verified)
        self.assertTrue(audit.p0_5_p6_persistence_acknowledged)
        self.assertTrue(audit.p0_6_64k_align_and_dt_hash_verified)

    def test_23_stage288_hardening_fault_missing_unlinkat_rejected(self) -> None:
        so = build_hardened_jit_so_fixture(include_self_unlink=False)
        frame = encode_stage288_output_frame(b"S" * 512)
        audit = validate_stage288_hardened_payload_contract(
            so,
            frame,
            dev_nflasha_verified=True,
            p6_persistence_acknowledged=True,
        )
        self.assertFalse(audit.all_p0_items_closed)
        self.assertFalse(audit.p0_1_self_unlink_at_entry)

    def test_24_stage288_hardening_fault_o_trunc_before_read_rejected(self) -> None:
        so = build_hardened_jit_so_fixture(truncate_before_read_check=True)
        frame = encode_stage288_output_frame(b"S" * 512)
        audit = validate_stage288_hardened_payload_contract(
            so,
            frame,
            dev_nflasha_verified=True,
            p6_persistence_acknowledged=True,
        )
        self.assertFalse(audit.all_p0_items_closed)
        self.assertFalse(audit.p0_2_no_truncate_on_read_fail)

    # ------------------------------------------------------------------
    # Pillar 2: U4 Zero-Sector0-Touch Strategy-A Bridge (25..28)
    # ------------------------------------------------------------------

    def test_25_pillar2_u4_closure_and_strategy_a_pass(self) -> None:
        p2 = audit_pillar2_u4_zero_sector0_bridge()
        self.assertTrue(p2.all_checks_passed)
        self.assertTrue(p2.u4_closed)
        self.assertEqual(p2.fx3_p20_bytes, 0)
        self.assertEqual(p2.fx3_p21_bytes, 0)
        self.assertEqual(p2.fx3_p30_bytes, 48 * 1024 * 1024)
        self.assertGreaterEqual(p2.setupfile_nflasha20_refs, 1)
        self.assertGreaterEqual(p2.appfw_nflasha20_refs, 1)
        self.assertGreaterEqual(p2.kikilog_lib_nflasha21_refs, 1)
        self.assertEqual(p2.kikilog_ko_nflasha21_refs, 0)
        self.assertTrue(p2.kikilog_ko_opelog_logs_verified)
        self.assertTrue(p2.strategy_a_bridge.valid)
        self.assertEqual(p2.negative_bridge_drills_passed, 3)

    def test_26_strategy_a_fault_broken_nflasha20_symlink_rejected(self) -> None:
        res = verify_strategy_a_bridge_state(
            {
                "sector0_untouched": True,
                "edisx_repartition_executed": False,
                "p12_cert_untouched": True,
                "p18_lens_untouched": True,
                "nflasha20_symlink_target": "/dev/nflasha20",
                "etc_opelog_fstype": "tmpfs",
            }
        )
        self.assertFalse(res.valid)
        self.assertFalse(res.nflasha20_points_to_p30)

    def test_27_strategy_a_fault_missing_tmpfs_opelog_rejected(self) -> None:
        res = verify_strategy_a_bridge_state(
            {
                "sector0_untouched": True,
                "edisx_repartition_executed": False,
                "p12_cert_untouched": True,
                "p18_lens_untouched": True,
                "nflasha20_symlink_target": "/dev/nflasha30",
                "etc_opelog_fstype": "vfat",
            }
        )
        self.assertFalse(res.valid)
        self.assertFalse(res.etc_opelog_tmpfs_ok)

    def test_28_strategy_a_fault_edisx_or_sector0_p12_p18_touch_rejected(self) -> None:
        res = verify_strategy_a_bridge_state(
            {
                "sector0_untouched": False,
                "edisx_repartition_executed": True,
                "p12_cert_untouched": False,
                "p18_lens_untouched": False,
                "nflasha20_symlink_target": "/dev/nflasha30",
                "etc_opelog_fstype": "tmpfs",
            }
        )
        self.assertFalse(res.valid)
        self.assertFalse(res.sector0_untouched)
        self.assertTrue(res.edisx_repartition_executed)
        self.assertFalse(res.p12_cert_untouched)
        self.assertFalse(res.p18_lens_untouched)

    # ------------------------------------------------------------------
    # Pillar 3: U5 p1 Single-Shot Selector & p3 Fallback (29..32)
    # ------------------------------------------------------------------

    def test_29_pillar3_u5_closure_and_cp_passivity_verified(self) -> None:
        p3 = audit_pillar3_u5_p1_oneshot_fallback()
        self.assertTrue(p3.all_checks_passed)
        self.assertTrue(p3.u5_closed)
        self.assertTrue(p3.loader_nor_mode_cmode_verified)
        self.assertTrue(p3.loader_nor_updater_mode_verified)
        self.assertTrue(p3.loader_nor_pinned_insns_matched)
        self.assertTrue(p3.up_sh_modes_verified)
        self.assertTrue(p3.ud_send_lsi_queue_0x376_verified)
        self.assertTrue(p3.cpapp_passive_to_updater_mode_verified)
        self.assertEqual(p3.fx3_cpapp_updater_mode_hits, 0)
        self.assertEqual(p3.fx6_cpapp_updater_mode_hits, 0)
        self.assertGreaterEqual(p3.fx3_cpapp_0x4b0000_refs, 1)
        self.assertEqual(p3.negative_selector_drills_passed, 3)

    def test_30_p1_oneshot_fault_uncleared_updater_mode_files_rejected(self) -> None:
        res = verify_p1_oneshot_clear_state(
            {
                "updater_mode_files": ("/setting/updater/mode", "/setting/updater/mode3"),
                "bk4_byte8_selector": 0,
                "sub_lsi_boot_mode": 0,
            }
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.next_boot_target, "p1_UPDATER_STICKY_RISK")

    def test_31_p1_oneshot_fault_nonzero_bk4_byte8_rejected(self) -> None:
        res = verify_p1_oneshot_clear_state(
            {
                "updater_mode_files": (),
                "bk4_byte8_selector": 1,
                "sub_lsi_boot_mode": 0,
            }
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.bk4_byte8_selector, 1)

    def test_32_p1_oneshot_fault_nonzero_sub_lsi_mode_rejected(self) -> None:
        res = verify_p1_oneshot_clear_state(
            {
                "updater_mode_files": (),
                "bk4_byte8_selector": 0,
                "sub_lsi_boot_mode": 3,
            }
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.sub_lsi_boot_mode, 3)

    # ------------------------------------------------------------------
    # Pillar 4: Tier-0 Complete Cold-Backup Stop-Gate (33..42)
    # ------------------------------------------------------------------

    def test_33_pillar4_sandbox_stop_gate_nominal_passes(self) -> None:
        p4 = audit_pillar4_tier0_cold_backup_gate()
        self.assertTrue(p4.all_checks_passed)
        self.assertFalse(p4.persistent_emmc_writes_authorized)
        self.assertFalse(p4.usb_device_attach_executed)
        self.assertFalse(p4.persistent_write_release)
        self.assertTrue(p4.is_non_synthetic_hardware)
        self.assertTrue(p4.manifest_audit_valid)
        self.assertTrue(p4.twopass_sha256_all_matched)
        self.assertTrue(p4.ondisk_sha256_all_matched)
        self.assertTrue(p4.sector0_magic_ok)
        self.assertTrue(p4.sector0_fx3_layout_ok)
        self.assertTrue(p4.p1_dat2_model_ok)
        self.assertTrue(p4.p2_bk4_ok)
        self.assertTrue(p4.p2_psd_ok)
        self.assertTrue(p4.p2_defdet_ok)
        self.assertTrue(p4.p2_dtb_fdt_magic_ok)
        self.assertTrue(p4.spi_nor_ddrtraining_ok)
        self.assertTrue(p4.spi_nor_loader_ok)
        self.assertEqual(p4.negative_gate_drills_passed, 5)

    def test_34_pillar4_explicit_bundle_dir_passes(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            bdir = populate_phase136_tier0_bundle(Path(td) / "tier0")
            p4 = audit_pillar4_tier0_cold_backup_gate(bdir)
            self.assertTrue(p4.all_checks_passed, p4.errors)

    def test_35_pillar4_fault_missing_psd_and_defdet_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            for missing in ("p2_psd_bin", "p2_defdet_bin"):
                bdir = populate_phase136_tier0_bundle(Path(td) / missing, omit_item=missing)
                p4 = audit_pillar4_tier0_cold_backup_gate(bdir)
                self.assertFalse(p4.all_checks_passed)

    def test_36_pillar4_fault_missing_spi_nor_ddrtraining_or_loader_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            for missing in ("spi_nor_ddrtraining", "spi_nor_loader"):
                bdir = populate_phase136_tier0_bundle(Path(td) / missing, omit_item=missing)
                p4 = audit_pillar4_tier0_cold_backup_gate(bdir)
                self.assertFalse(p4.all_checks_passed)

    def test_37_pillar4_fault_wrong_p1_dat2_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            bdir = populate_phase136_tier0_bundle(Path(td) / "bad_dat2", wrong_dat2=True)
            p4 = audit_pillar4_tier0_cold_backup_gate(bdir)
            self.assertFalse(p4.all_checks_passed)
            self.assertFalse(p4.p1_dat2_model_ok)

    def test_38_pillar4_fault_pass2_sha256_mismatch_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            bdir = populate_phase136_tier0_bundle(Path(td) / "bad_p2", corrupt_pass2_item="p6_jiritsu")
            p4 = audit_pillar4_tier0_cold_backup_gate(bdir)
            self.assertFalse(p4.all_checks_passed)
            self.assertFalse(p4.twopass_sha256_all_matched)

    def test_39_pillar4_fault_tampered_sector0_magic_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            bdir = populate_phase136_tier0_bundle(Path(td) / "bad_s0", corrupt_sector0_magic=True)
            p4 = audit_pillar4_tier0_cold_backup_gate(bdir)
            self.assertFalse(p4.all_checks_passed)
            self.assertFalse(p4.sector0_magic_ok)

    def test_40_pillar4_fault_bad_cxd90057_dtb_magic_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            bdir = populate_phase136_tier0_bundle(Path(td) / "bad_dtb")
            (bdir / "p2_cxd90057.dtb").write_bytes(b"\x00" * 64)
            p4 = audit_pillar4_tier0_cold_backup_gate(bdir)
            self.assertFalse(p4.all_checks_passed)
            self.assertFalse(p4.p2_dtb_fdt_magic_ok)

    def test_41_pillar4_fault_synthetic_identity_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            bdir = populate_phase136_tier0_bundle(
                Path(td) / "synth",
                body_serial="00000000",
                source_kind="synthetic_mock",
            )
            p4 = audit_pillar4_tier0_cold_backup_gate(bdir)
            self.assertFalse(p4.all_checks_passed)
            self.assertFalse(p4.is_non_synthetic_hardware)

    def test_42_pillar4_hard_locks_reject_emmc_write_or_usb_attach_flags(self) -> None:
        with self.assertRaises(ValueError):
            audit_pillar4_tier0_cold_backup_gate(authorize_emmc_writes=True)
        with self.assertRaises(ValueError):
            audit_pillar4_tier0_cold_backup_gate(execute_usb_attach=True)

    # ------------------------------------------------------------------
    # CLI Integration (43..44)
    # ------------------------------------------------------------------

    def test_43_cli_verify_realhw_jiritsu_tier0_clean_room_json_and_output(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            out_json = Path(td) / "phase136.json"
            with mock.patch("sys.stdout"):
                rc = cli_main(
                    ["verify-realhw-jiritsu-tier0", "--clean-room", "--json", "--output", str(out_json)]
                )
            self.assertEqual(rc, 0)
            self.assertTrue(out_json.is_file())
            parsed = json.loads(out_json.read_text(encoding="utf-8"))
            self.assertEqual(parsed["schema"], PHASE_136_SCHEMA)
            self.assertTrue(verify_phase136_report(parsed).valid)

    def test_44_cli_verify_realhw_jiritsu_tier0_with_missing_tier0_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            empty_dir = Path(td) / "empty_tier0"
            empty_dir.mkdir(parents=True, exist_ok=True)
            with mock.patch("sys.stdout"):
                rc = cli_main(
                    [
                        "verify-realhw-jiritsu-tier0",
                        "--clean-room",
                        "--tier0-bundle-dir",
                        str(empty_dir),
                    ]
                )
            self.assertEqual(rc, 1)


if __name__ == "__main__":
    unittest.main()
