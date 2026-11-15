"""Phase 183 (38th Auditor, 38/38) dual-mode unit tests for
`realhw_emount_info3d_breathing_02cf0232_auditor` (50 tests).
"""

from __future__ import annotations

import ast
import io
import json
import os
import struct
import sys
import time
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

sys.dont_write_bytecode = True

_LAB_PKG_ROOT = str(Path(__file__).resolve().parent.parent)
if _LAB_PKG_ROOT not in sys.path:
    sys.path.insert(0, _LAB_PKG_ROOT)

import fx3_firmware_lab as ffl
from fx3_firmware_lab.__main__ import main as cli_main, run_audit_all
from fx3_firmware_lab.haita_bk4_feature_analyzer import is_forced_clean_room
from fx3_firmware_lab.realhw_emount_info3d_breathing_02cf0232_auditor import (
    APPFW_BREATHING_FX3_MARKERS_P183,
    APPFW_BREATHING_FX6_MARKERS_P183,
    BKID_APP_MR_SETTING_LENS_COMP_BREATHING,
    BREATHING_CROP_MAX_P183,
    BREATHING_CROP_MIN_P183,
    CPAPP_FX3_FOCUSMAP_MODELID_MARKERS_P183,
    CPAPP_FX6_LENSFILE_SET_MARKER_P183,
    CPAPP_SHARED_EMOUNT_INFO_MARKERS_P183,
    EMOUNT_INFO3D_PACKET_BYTES,
    EMOUNT_INFO7_PACKET_BYTES,
    EMOUNT_INFO8_PACKET_BYTES,
    EXPECTED_FX3_APPFW_BYTES_P183,
    EXPECTED_FX3_CPAPP_BYTES_P183,
    EXPECTED_FX3_MPR_BYTES_P183,
    EXPECTED_FX3_PTP_BYTES_P183,
    EXPECTED_FX6_APPFW_BYTES_P183,
    EXPECTED_FX6_CPAPP_BYTES_P183,
    EXPECTED_FX6_LENSFILE_BYTES_P183,
    EXPECTED_FX6_LENSFILE_ENTRY_COUNT,
    EXPECTED_FX6_MPR_BYTES_P183,
    EXPECTED_FX6_PTP_BYTES_P183,
    EXPECTED_LENS_COMM_BYTES_P183,
    MC_MIN_SUPPORTED_VERSION,
    MPR_BREATHING_SHARED_MARKERS_P183,
    P18_BLKROSET_VALUE,
    P18_LENSFILE_VIRTUAL_PATH,
    P2_BACKUP_BIN_VIRTUAL_PATH,
    PHASE_183_SCHEMA,
    PHASE_183_VERSION,
    PTP_CONTROL_SHARED_MARKERS_P183,
    UNSUPPORTED_MANUAL_ADAPTER_LENS_ID,
    _build_synthetic_lensfile_bin,
    _inspect_lensfile_bin_buf,
    analyze_realhw_emount_info3d_breathing_02cf0232,
    build_clean_room_realhw_emount_info3d_breathing_fixtures,
    build_emount_info3d_packet,
    build_emount_info7_packet,
    build_emount_info8_packet,
    build_phase183_emount_compat_matrix,
    decode_emount_info3d_packet,
    decode_emount_info7_packet,
    decode_emount_info8_packet,
    evaluate_emount_info7_8_3d_handshake,
    evaluate_monitor_control_focus_map_stream,
    evaluate_p18_lensfile_vs_cinealta_slots,
    evaluate_phase183_write_guard,
    evaluate_sony_lens_id_and_breathing_02cf0232,
    is_sony_first_party_emount_lens,
    realhw_emount_info3d_breathing_02cf0232_report_to_dict,
)


MODULE_PATH = (
    Path(__file__).resolve().parent.parent
    / "fx3_firmware_lab"
    / "realhw_emount_info3d_breathing_02cf0232_auditor.py"
)


class TestPhase183RealhwEmountInfo3dBreathing02cf0232(unittest.TestCase):
    """Dual-mode tests (Local O_RDONLY Donors + Forced Clean-Room)."""

    # ------------------------------------------------------------------
    # 1..8: AST safety, SLA, dual-mode determinism & exports
    # ------------------------------------------------------------------

    def test_01_ast_strictly_o_rdonly_zero_builtin_open_or_writes(self) -> None:
        src = MODULE_PATH.read_text(encoding="utf-8")
        tree = ast.parse(src)
        forbidden_calls = {"open", "write_bytes", "write_text", "unlink", "rmdir", "mkdir", "chmod"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    self.assertNotIn(node.func.id, forbidden_calls, f"Forbidden call: {node.func.id}")
                elif isinstance(node.func, ast.Attribute):
                    if (
                        node.func.attr == "open"
                        and isinstance(node.func.value, ast.Name)
                        and node.func.value.id == "os"
                    ):
                        self.assertGreaterEqual(len(node.args), 2)
                        self.assertIsInstance(node.args[1], ast.Attribute)
                        self.assertEqual(node.args[1].attr, "O_RDONLY")
                    else:
                        self.assertNotIn(
                            node.func.attr,
                            {"write", "write_bytes", "write_text", "unlink", "mkdir", "open"},
                            f"Forbidden attr call: {node.func.attr}",
                        )
            elif isinstance(node, ast.Attribute) and node.attr in {"O_RDWR", "O_WRONLY", "O_CREAT", "O_TRUNC"}:
                self.fail(f"Forbidden write flag: os.{node.attr}")
        self.assertIn("O_RDONLY", src)

    def test_02_auto_mode_report_within_sla(self) -> None:
        t0 = time.perf_counter()
        report = analyze_realhw_emount_info3d_breathing_02cf0232()
        elapsed = time.perf_counter() - t0
        self.assertLess(elapsed, 6.0)
        self.assertEqual(report.schema_version, PHASE_183_SCHEMA)
        self.assertEqual(report.phase_version, PHASE_183_VERSION)
        self.assertTrue(report.all_checks_passed, report.errors)
        self.assertEqual(report.errors, ())
        if is_forced_clean_room():
            self.assertEqual(report.mode, "CLEAN_ROOM_SYNTHETIC")
        else:
            self.assertIn(report.mode, ("LOCAL_DONOR_VERIFIED", "CLEAN_ROOM_SYNTHETIC"))

    def test_03_forced_clean_room_mode_passes_deterministically(self) -> None:
        t0 = time.perf_counter()
        r1 = analyze_realhw_emount_info3d_breathing_02cf0232(clean_room=True)
        r2 = analyze_realhw_emount_info3d_breathing_02cf0232(clean_room=True)
        elapsed = time.perf_counter() - t0
        self.assertLess(elapsed, 6.0)
        self.assertEqual(r1.mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(r1.all_checks_passed, r1.errors)
        self.assertEqual(r1.report_sha256, r2.report_sha256)

    def test_04_missing_donor_root_falls_back_to_clean_room(self) -> None:
        non_existent = Path("/tmp/non_existent_fx3_fx6_donor_root_phase183")
        with mock.patch(
            "fx3_firmware_lab.realhw_emount_info3d_breathing_02cf0232_auditor.resolve_donor_file",
            return_value=None,
        ):
            r = analyze_realhw_emount_info3d_breathing_02cf0232(repo_root=non_existent)
        self.assertEqual(r.mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(r.all_checks_passed, r.errors)

    def test_05_env_force_clean_room_override_respected(self) -> None:
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            r = analyze_realhw_emount_info3d_breathing_02cf0232()
            self.assertEqual(r.mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertTrue(r.all_checks_passed)

    def test_06_zero_hardware_write_invariants_enforced(self) -> None:
        for cr in (False, True):
            r = analyze_realhw_emount_info3d_breathing_02cf0232(clean_room=cr)
            self.assertFalse(r.persistent_emmc_writes_authorized)
            self.assertFalse(r.spi_nor_write_authorized)
            self.assertFalse(r.el3_payload_transmit_authorized)
            self.assertEqual(r.physical_usb_packets_emitted, 0)
            self.assertEqual(r.raw_firmware_bytes_leaked, 0)
            self.assertEqual(r.lens_partition_writes, 0)
            self.assertEqual(r.backup_bin_writes, 0)

    def test_07_report_to_dict_json_roundtrip_and_zero_leak(self) -> None:
        r = analyze_realhw_emount_info3d_breathing_02cf0232(clean_room=True)
        d = realhw_emount_info3d_breathing_02cf0232_report_to_dict(r)
        s = json.dumps(d, sort_keys=True)
        self.assertNotIn("ELF", s)
        parsed = json.loads(s)
        self.assertTrue(parsed["all_checks_passed"])
        self.assertEqual(parsed["lens_partition_writes"], 0)
        self.assertEqual(parsed["backup_bin_writes"], 0)

    def test_08_package_exports_phase183_symbols(self) -> None:
        self.assertTrue(hasattr(ffl, "analyze_realhw_emount_info3d_breathing_02cf0232"))
        self.assertTrue(hasattr(ffl, "realhw_emount_info3d_breathing_02cf0232_report_to_dict"))
        self.assertTrue(hasattr(ffl, "is_sony_first_party_emount_lens"))
        self.assertTrue(hasattr(ffl, "evaluate_sony_lens_id_and_breathing_02cf0232"))
        self.assertIn("analyze_realhw_emount_info3d_breathing_02cf0232", ffl.__all__)

    # ------------------------------------------------------------------
    # 9..16: Domain A — E-Mount info7/info8/info3D Serial Handshake
    # ------------------------------------------------------------------

    def test_09_donor_file_sizes_verified_when_local_donors_active(self) -> None:
        r = analyze_realhw_emount_info3d_breathing_02cf0232()
        if r.mode == "LOCAL_DONOR_VERIFIED":
            self.assertEqual(r.donor_file_sizes["fx3_appfw"], EXPECTED_FX3_APPFW_BYTES_P183)
            self.assertEqual(r.donor_file_sizes["fx6_appfw"], EXPECTED_FX6_APPFW_BYTES_P183)
            self.assertEqual(r.donor_file_sizes["fx3_mpr"], EXPECTED_FX3_MPR_BYTES_P183)
            self.assertEqual(r.donor_file_sizes["fx6_mpr"], EXPECTED_FX6_MPR_BYTES_P183)
            self.assertEqual(r.donor_file_sizes["fx3_cpapp"], EXPECTED_FX3_CPAPP_BYTES_P183)
            self.assertEqual(r.donor_file_sizes["fx6_cpapp"], EXPECTED_FX6_CPAPP_BYTES_P183)
            self.assertEqual(r.donor_file_sizes["fx3_lens_comm"], EXPECTED_LENS_COMM_BYTES_P183)
            self.assertEqual(r.donor_file_sizes["fx6_lens_comm"], EXPECTED_LENS_COMM_BYTES_P183)
            self.assertEqual(r.donor_file_sizes["fx3_ptp"], EXPECTED_FX3_PTP_BYTES_P183)
            self.assertEqual(r.donor_file_sizes["fx6_ptp"], EXPECTED_FX6_PTP_BYTES_P183)
            self.assertEqual(r.donor_file_sizes["fx6_lensfile"], EXPECTED_FX6_LENSFILE_BYTES_P183)

    def test_10_libinfralenscommunicator_abi_parity_both_bodies(self) -> None:
        for cr in (False, True):
            r = analyze_realhw_emount_info3d_breathing_02cf0232(clean_room=cr)
            da = r.domain_a_emount_handshake
            self.assertTrue(da.passed)
            self.assertEqual(da.fx3_lens_comm_summary.export_count, 27)
            self.assertEqual(da.fx3_lens_comm_summary.import_count, 25)
            self.assertEqual(da.fx6_lens_comm_summary.export_count, 27)
            self.assertEqual(da.fx6_lens_comm_summary.import_count, 25)

    def test_11_info7_packet_build_decode_and_corruption_rejected(self) -> None:
        pkt = build_emount_info7_packet(
            lens_id=0xC120,
            focal_min_mm=50,
            focal_max_mm=50,
            max_aperture_x10=12,
            pz_capable=False,
            oss_capable=False,
        )
        self.assertEqual(len(pkt), EMOUNT_INFO7_PACKET_BYTES)
        dec = decode_emount_info7_packet(pkt)
        self.assertTrue(dec.crc32_ok)
        self.assertTrue(dec.sony_first_party)
        self.assertEqual(dec.lens_id, 0xC120)
        self.assertEqual(dec.max_aperture_x10, 12)
        bad = bytearray(pkt)
        bad[8] ^= 0xFF
        self.assertFalse(decode_emount_info7_packet(bytes(bad)).crc32_ok)
        with self.assertRaises(ValueError):
            decode_emount_info7_packet(b"BAD")

    def test_12_info8_packet_build_decode_and_corruption_rejected(self) -> None:
        pkt = build_emount_info8_packet(
            lens_id=0xC205,
            focus_distance_mm=3200,
            current_f_stop_x10=28,
            zoom_pos_permille=750,
            af_switch_on=True,
            oss_active=True,
            pz_speed_step=4,
        )
        self.assertEqual(len(pkt), EMOUNT_INFO8_PACKET_BYTES)
        dec = decode_emount_info8_packet(pkt)
        self.assertTrue(dec.crc32_ok)
        self.assertEqual(dec.focus_distance_mm, 3200)
        self.assertEqual(dec.current_f_stop_x10, 28)
        self.assertEqual(dec.zoom_pos_permille, 750)
        self.assertTrue(dec.af_switch_on)
        self.assertTrue(dec.oss_active)
        self.assertEqual(dec.pz_speed_step, 4)
        bad = bytearray(pkt)
        bad[-1] ^= 0x01
        self.assertFalse(decode_emount_info8_packet(bytes(bad)).crc32_ok)

    def test_13_info3d_packet_build_decode_and_corruption_rejected(self) -> None:
        pkt = build_emount_info3d_packet(
            lens_id=0xC120,
            breathing_table_present=True,
            distortion_poly_present=True,
            shading_table_present=True,
            af_drive_curve_id=0x109,
            max_breathing_crop_x1000=1072,
        )
        self.assertEqual(len(pkt), EMOUNT_INFO3D_PACKET_BYTES)
        dec = decode_emount_info3d_packet(pkt)
        self.assertTrue(dec.crc32_ok)
        self.assertTrue(dec.breathing_table_present)
        self.assertTrue(dec.distortion_poly_present)
        self.assertTrue(dec.shading_table_present)
        self.assertEqual(dec.af_drive_curve_id, 0x109)
        self.assertEqual(dec.max_breathing_crop_x1000, 1072)
        bad = bytearray(pkt)
        bad[10] ^= 0x40
        self.assertFalse(decode_emount_info3d_packet(bytes(bad)).crc32_ok)

    def test_14_cpapp_shared_mount_divided_info_markers_present(self) -> None:
        r = analyze_realhw_emount_info3d_breathing_02cf0232()
        da = r.domain_a_emount_handshake
        for tok in CPAPP_SHARED_EMOUNT_INFO_MARKERS_P183:
            self.assertGreater(da.fx3_cpapp_shared_hits[tok], 0, f"fx3 missing {tok}")
            self.assertGreater(da.fx6_cpapp_shared_hits[tok], 0, f"fx6 missing {tok}")

    def test_15_fx3_cpapp_focusmap_and_modelid_markers_present(self) -> None:
        r = analyze_realhw_emount_info3d_breathing_02cf0232()
        for tok in CPAPP_FX3_FOCUSMAP_MODELID_MARKERS_P183:
            self.assertGreater(r.domain_a_emount_handshake.fx3_cpapp_focusmap_modelid_hits[tok], 0)

    def test_16_handshake_evaluator_sony_third_party_manual_and_abi_mismatch(self) -> None:
        sony = evaluate_emount_info7_8_3d_handshake(lens_id=0xC120)
        self.assertTrue(sony.valid and sony.cp_to_appfw_bridged)
        self.assertEqual(sony.bridge_class, "NATIVE_PASSTHROUGH")
        tp = evaluate_emount_info7_8_3d_handshake(lens_id=0x4024, breathing_table_present=False)
        self.assertTrue(tp.valid and tp.cp_to_appfw_bridged)
        self.assertEqual(tp.bridge_class, "SHIM_TRANSLATED")
        man = evaluate_emount_info7_8_3d_handshake(lens_id=UNSUPPORTED_MANUAL_ADAPTER_LENS_ID)
        self.assertTrue(man.valid)
        self.assertEqual(man.status, "MANUAL_ADAPTER_0XFFFF_PASSTHROUGH_OK")
        bad_abi = evaluate_emount_info7_8_3d_handshake(lens_id=0xC120, lens_comm_parity_ok=False)
        self.assertFalse(bad_abi.valid)
        self.assertFalse(bad_abi.cp_to_appfw_bridged)

    # ------------------------------------------------------------------
    # 17..28: Domain B — ((lens_id >> 14) == 3) & 0x02cf0232 Breathing
    # ------------------------------------------------------------------

    def test_17_sony_lens_id_bitmask_boundary_cases(self) -> None:
        self.assertTrue(is_sony_first_party_emount_lens(0xC000))
        self.assertTrue(is_sony_first_party_emount_lens(0xC120))
        self.assertTrue(is_sony_first_party_emount_lens(0xFFFE))
        self.assertTrue(is_sony_first_party_emount_lens(0xD000))  # bit13..12 = 01, low12 = 0
        self.assertFalse(is_sony_first_party_emount_lens(0xCFFF))  # low12 == 0xFFF
        self.assertFalse(is_sony_first_party_emount_lens(0xDFFF))  # low12 == 0xFFF
        self.assertFalse(is_sony_first_party_emount_lens(0xFFFF))  # manual adapter
        self.assertFalse(is_sony_first_party_emount_lens(0x0000))  # unchipped
        self.assertFalse(is_sony_first_party_emount_lens(0x4024))  # top2 == 1
        self.assertFalse(is_sony_first_party_emount_lens(0x8001))  # top2 == 2
        self.assertFalse(is_sony_first_party_emount_lens(0xBFFF))  # top2 == 2

    def test_18_fx6_appfw_contains_literal_0x02cf0232_u32_marker(self) -> None:
        for cr in (False, True):
            r = analyze_realhw_emount_info3d_breathing_02cf0232(clean_room=cr)
            self.assertGreaterEqual(r.domain_b_lens_id_breathing_02cf0232.fx6_appfw_02cf0232_u32_hits, 1)

    def test_19_appfw_and_mpr_breathing_markers_verified(self) -> None:
        r = analyze_realhw_emount_info3d_breathing_02cf0232()
        db = r.domain_b_lens_id_breathing_02cf0232
        self.assertTrue(db.passed)
        for tok in APPFW_BREATHING_FX3_MARKERS_P183:
            self.assertGreater(db.fx3_appfw_breathing_hits[tok], 0)
        for tok in APPFW_BREATHING_FX6_MARKERS_P183:
            self.assertGreater(db.fx6_appfw_breathing_hits[tok], 0)
        for tok in MPR_BREATHING_SHARED_MARKERS_P183:
            self.assertGreater(db.fx3_mpr_summary.marker_hits[tok], 0)
            self.assertGreater(db.fx6_mpr_summary.marker_hits[tok], 0)

    def test_20_sony_first_party_0xc120_enables_02cf0232_crop_and_catalyst(self) -> None:
        ev = evaluate_sony_lens_id_and_breathing_02cf0232(lens_id=0xC120, focus_position_norm=1.0)
        self.assertTrue(ev.valid)
        self.assertTrue(ev.sony_first_party_check)
        self.assertTrue(ev.breathing_comp_allowed)
        self.assertFalse(ev.degraded_gracefully)
        self.assertFalse(ev.fault_raised)
        self.assertTrue(ev.catalyst_metadata_injected)
        self.assertEqual(ev.bkid_hex, f"0x{BKID_APP_MR_SETTING_LENS_COMP_BREATHING:08x}")
        self.assertGreater(ev.dynamic_fov_crop_factor, BREATHING_CROP_MIN_P183)
        self.assertLessEqual(ev.dynamic_fov_crop_factor, BREATHING_CROP_MAX_P183)

    def test_21_third_party_emount_degrades_gracefully_no_fault(self) -> None:
        ev = evaluate_sony_lens_id_and_breathing_02cf0232(lens_id=0x4024)
        self.assertTrue(ev.valid)
        self.assertEqual(ev.lens_category, "THIRD_PARTY_EMOUNT")
        self.assertFalse(ev.sony_first_party_check)
        self.assertFalse(ev.breathing_comp_allowed)
        self.assertTrue(ev.degraded_gracefully)
        self.assertFalse(ev.fault_raised)
        self.assertEqual(ev.dynamic_fov_crop_factor, 1.0)
        self.assertFalse(ev.catalyst_metadata_injected)

    def test_22_manual_adapter_0xffff_and_0x0000_degrade_gracefully(self) -> None:
        for lid in (0xFFFF, 0x0000):
            ev = evaluate_sony_lens_id_and_breathing_02cf0232(lens_id=lid)
            self.assertTrue(ev.valid)
            self.assertEqual(ev.lens_category, "MANUAL_ADAPTER_OR_UNCHIPPED")
            self.assertFalse(ev.sony_first_party_check)
            self.assertFalse(ev.breathing_comp_allowed)
            self.assertTrue(ev.degraded_gracefully)
            self.assertFalse(ev.fault_raised)
            self.assertEqual(ev.dynamic_fov_crop_factor, 1.0)

    def test_23_sony_reserved_low12_0xcfff_rejected_gracefully(self) -> None:
        ev = evaluate_sony_lens_id_and_breathing_02cf0232(lens_id=0xCFFF)
        self.assertTrue(ev.valid)
        self.assertEqual(ev.lens_category, "INVALID_SONY_RESERVED_LOW12_0XFFF")
        self.assertFalse(ev.sony_first_party_check)
        self.assertFalse(ev.breathing_comp_allowed)
        self.assertTrue(ev.degraded_gracefully)
        self.assertFalse(ev.fault_raised)

    def test_24_hdmi_raw_active_bypasses_02cf0232_crop(self) -> None:
        ev = evaluate_sony_lens_id_and_breathing_02cf0232(lens_id=0xC120, hdmi_raw_active=True)
        self.assertTrue(ev.valid)
        self.assertFalse(ev.breathing_comp_allowed)
        self.assertTrue(ev.degraded_gracefully)
        self.assertEqual(ev.dynamic_fov_crop_factor, 1.0)
        self.assertEqual(ev.status, "BYPASSED_BY_HDMI_RAW16_ISP_BYPASS")

    def test_25_sq_120p_plus_bypasses_02cf0232_crop(self) -> None:
        ev = evaluate_sony_lens_id_and_breathing_02cf0232(lens_id=0xC120, sq_120p_plus_active=True)
        self.assertTrue(ev.valid)
        self.assertFalse(ev.breathing_comp_allowed)
        self.assertEqual(ev.dynamic_fov_crop_factor, 1.0)
        self.assertEqual(ev.status, "BYPASSED_BY_SQ_120P_PLUS")

    def test_26_teleconverter_bypasses_02cf0232_crop(self) -> None:
        ev = evaluate_sony_lens_id_and_breathing_02cf0232(lens_id=0xC120, teleconverter_attached=True)
        self.assertTrue(ev.valid)
        self.assertFalse(ev.breathing_comp_allowed)
        self.assertEqual(ev.dynamic_fov_crop_factor, 1.0)
        self.assertEqual(ev.status, "BYPASSED_BY_TELECONVERTER")

    def test_27_breathing_disabled_or_missing_info3d_table_degrades(self) -> None:
        ev1 = evaluate_sony_lens_id_and_breathing_02cf0232(lens_id=0xC120, breathing_requested=False)
        ev2 = evaluate_sony_lens_id_and_breathing_02cf0232(
            lens_id=0xC120, info3d_breathing_table_present=False
        )
        for ev in (ev1, ev2):
            self.assertTrue(ev.valid)
            self.assertFalse(ev.breathing_comp_allowed)
            self.assertTrue(ev.degraded_gracefully)
            self.assertEqual(ev.dynamic_fov_crop_factor, 1.0)

    def test_28_focus_position_norm_out_of_range_rejected(self) -> None:
        for bad in (-0.01, 1.01):
            ev = evaluate_sony_lens_id_and_breathing_02cf0232(lens_id=0xC120, focus_position_norm=bad)
            self.assertFalse(ev.valid)
            self.assertTrue(ev.fault_raised)
            self.assertFalse(ev.breathing_comp_allowed)

    # ------------------------------------------------------------------
    # 29..36: Domain C — p18:/lens/LENSFILE.BIN RO vs CineAlta Slots
    # ------------------------------------------------------------------

    def test_29_fx6_lensfile_bin_structure_and_57_entries_verified(self) -> None:
        for cr in (False, True):
            r = analyze_realhw_emount_info3d_breathing_02cf0232(clean_room=cr)
            lf = r.domain_c_p18_lensfile_isolation.fx6_lensfile_summary
            self.assertTrue(lf.header_valid)
            self.assertTrue(lf.entries_bounds_valid)
            self.assertEqual(lf.entry_count, EXPECTED_FX6_LENSFILE_ENTRY_COUNT)
            self.assertEqual(lf.blkroset_enforced, P18_BLKROSET_VALUE)
            self.assertTrue(lf.first_tag.startswith("VX89"))

    def test_30_synthetic_lensfile_bin_rejects_corrupt_or_oob(self) -> None:
        good = _build_synthetic_lensfile_bin(5)
        summ = _inspect_lensfile_bin_buf(good, source_mode="CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(summ.header_valid and summ.entries_bounds_valid)
        self.assertEqual(summ.entry_count, 5)
        self.assertFalse(_inspect_lensfile_bin_buf(b"\x01\x00", source_mode="CLEAN_ROOM_SYNTHETIC").header_valid)
        self.assertFalse(
            _inspect_lensfile_bin_buf(good[:-10], source_mode="CLEAN_ROOM_SYNTHETIC").entries_bounds_valid
        )
        zero_cnt = struct.pack("<I", 0) + b"\x00" * 64
        self.assertFalse(_inspect_lensfile_bin_buf(zero_cnt, source_mode="CLEAN_ROOM_SYNTHETIC").header_valid)

    def test_31_cpapp_setlensfile_fx6_asymmetry_verified(self) -> None:
        r = analyze_realhw_emount_info3d_breathing_02cf0232()
        dc = r.domain_c_p18_lensfile_isolation
        self.assertTrue(dc.passed)
        self.assertEqual(dc.fx3_cpapp_setlensfile_hits, 0)
        self.assertGreaterEqual(dc.fx6_cpapp_setlensfile_hits, 1)

    def test_32_p18_read_lookup_allowed_with_zero_writes(self) -> None:
        ev = evaluate_p18_lensfile_vs_cinealta_slots(
            operation="READ_LOOKUP",
            target_path=P18_LENSFILE_VIRTUAL_PATH,
            blkroset_value=1,
        )
        self.assertTrue(ev.valid)
        self.assertEqual(ev.lens_partition_writes, 0)
        self.assertEqual(ev.bridge_class, "NATIVE_PASSTHROUGH")

    def test_33_cinealta_offset_routed_to_tmpfs_and_sd_exfat_allowed(self) -> None:
        ev_tmp = evaluate_p18_lensfile_vs_cinealta_slots(
            operation="SAVE_CINEALTA_OFFSET",
            target_path="/tmp/cinealta_lens_offset_slot1.json",
            slot_target="VOLATILE_TMPFS",
        )
        ev_sd = evaluate_p18_lensfile_vs_cinealta_slots(
            operation="SAVE_CINEALTA_OFFSET",
            target_path="/mnt/sd/PRIVATE/SONY/PRO/LENS/SLOT2.BIN",
            slot_target="EXTERNAL_SD_EXFAT",
        )
        ev_cfe = evaluate_p18_lensfile_vs_cinealta_slots(
            operation="SAVE_CINEALTA_OFFSET",
            target_path="/mnt/cfexpress_a/PRIVATE/SONY/PRO/LENS/SLOT3.BIN",
            slot_target="EXTERNAL_CFEXPRESS_EXFAT",
        )
        for ev in (ev_tmp, ev_sd, ev_cfe):
            self.assertTrue(ev.valid)
            self.assertTrue(ev.volatile_or_ext_routed)
            self.assertEqual(ev.lens_partition_writes, 0)

    def test_34_write_to_p18_lensfile_or_nflasha18_hard_blocked(self) -> None:
        for bad_target in (P18_LENSFILE_VIRTUAL_PATH, "/dev/nflasha18", "/dev/cnflasha18"):
            ev = evaluate_p18_lensfile_vs_cinealta_slots(
                operation="SAVE_CINEALTA_OFFSET",
                target_path=bad_target,
                slot_target="VOLATILE_TMPFS",
            )
            self.assertFalse(ev.valid)
            self.assertTrue(ev.persistent_write_blocked)
            self.assertEqual(ev.lens_partition_writes, 0)
            self.assertEqual(ev.bridge_class, "HARD_WRITE_PROTECTED")

    def test_35_blkroset_other_than_1_rejected(self) -> None:
        ev = evaluate_p18_lensfile_vs_cinealta_slots(
            operation="READ_LOOKUP",
            target_path=P18_LENSFILE_VIRTUAL_PATH,
            blkroset_value=0,
        )
        self.assertFalse(ev.valid)
        self.assertIn("P18_BLKROSET_MUST_BE_1", ev.status)

    def test_36_unknown_lensfile_operation_or_invalid_slot_rejected(self) -> None:
        bad_op = evaluate_p18_lensfile_vs_cinealta_slots(operation="ERASE_P18", target_path="/tmp/x")
        self.assertFalse(bad_op.valid)
        self.assertTrue(bad_op.persistent_write_blocked)
        bad_slot = evaluate_p18_lensfile_vs_cinealta_slots(
            operation="SAVE_CINEALTA_OFFSET",
            target_path="/tmp/x",
            slot_target="EMMC_NVS",
        )
        self.assertFalse(bad_slot.valid)

    # ------------------------------------------------------------------
    # 37..46: Domain D — Monitor & Control 2.1.0+ Focus Map & Firewall
    # ------------------------------------------------------------------

    def test_37_ptp_control_markers_present_both_bodies(self) -> None:
        r = analyze_realhw_emount_info3d_breathing_02cf0232()
        dd = r.domain_d_monitor_control_focus_map
        self.assertTrue(dd.passed)
        for tok in PTP_CONTROL_SHARED_MARKERS_P183:
            self.assertGreater(dd.fx3_ptp_summary.marker_hits[tok], 0)
            self.assertGreater(dd.fx6_ptp_summary.marker_hits[tok], 0)

    def test_38_mc_210_wired_cdc_ncm_under_p12_safe(self) -> None:
        ev = evaluate_monitor_control_focus_map_stream(
            mc_version=MC_MIN_SUPPORTED_VERSION,
            transport="WIRED_USB_LAN_CDC_NCM",
            airplane_mode_p12=True,
            lens_id=0xC120,
        )
        self.assertTrue(ev.valid)
        self.assertTrue(ev.focus_map_active)
        self.assertFalse(ev.peaking_fallback_active)
        self.assertEqual(ev.backup_bin_writes, 0)
        self.assertEqual(ev.rf_tx_leaks, 0)
        self.assertAlmostEqual(ev.warm_zone_pct + ev.in_focus_zone_pct + ev.cool_zone_pct, 100.0)

    def test_39_mc_210_wifi_wpa2_wpa3_requires_p12_off(self) -> None:
        ok = evaluate_monitor_control_focus_map_stream(
            mc_version="2.2.0",
            transport="WIFI_WPA2_WPA3",
            airplane_mode_p12=False,
            lens_id=0xC120,
        )
        self.assertTrue(ok.valid and ok.focus_map_active)
        blocked = evaluate_monitor_control_focus_map_stream(
            mc_version="2.2.0",
            transport="WIFI_WPA2_WPA3",
            airplane_mode_p12=True,
            lens_id=0xC120,
        )
        self.assertFalse(blocked.valid)
        self.assertFalse(blocked.focus_map_active)
        self.assertIn("P12_AIRPLANE_MODE_BLOCKS_WIFI_RF", blocked.errors)

    def test_40_mc_below_210_or_deprecated_wifi_rejected(self) -> None:
        old_ver = evaluate_monitor_control_focus_map_stream(
            mc_version="2.0.0",
            transport="WIRED_USB_LAN_CDC_NCM",
        )
        self.assertFalse(old_ver.valid)
        self.assertIn("MC_VERSION_BELOW_2_1_0", old_ver.status)
        for tr in ("WIFI_WEP", "WIFI_WPA1_TKIP", "WIFI_IPSEC_LEGACY"):
            bad = evaluate_monitor_control_focus_map_stream(
                mc_version="2.1.0",
                transport=tr,
                airplane_mode_p12=False,
            )
            self.assertFalse(bad.valid)
            self.assertIn("FORBIDDEN_DEPRECATED_SECURITY_TRANSPORT", bad.status)

    def test_41_focus_map_dof_math_and_non_positive_param_guard(self) -> None:
        ev = evaluate_monitor_control_focus_map_stream(
            mc_version="2.1.0",
            transport="WIRED_USB_LAN_CDC_NCM",
            lens_id=0xC120,
            focal_length_mm=50.0,
            f_stop=1.4,
            focus_distance_m=2.0,
        )
        self.assertTrue(ev.valid)
        self.assertGreater(ev.hyperfocal_m, ev.focus_distance_m)
        self.assertLess(ev.near_dof_m, ev.focus_distance_m)
        self.assertGreater(ev.far_dof_m, ev.focus_distance_m)
        bad = evaluate_monitor_control_focus_map_stream(focal_length_mm=0.0)
        self.assertFalse(bad.valid)

    def test_42_unchipped_manual_adapter_falls_back_to_peaking(self) -> None:
        for lid in (0xFFFF, 0x0000):
            ev = evaluate_monitor_control_focus_map_stream(
                mc_version="2.1.0",
                transport="WIRED_USB_LAN_CDC_NCM",
                airplane_mode_p12=True,
                lens_id=lid,
            )
            self.assertTrue(ev.valid)
            self.assertFalse(ev.focus_map_active)
            self.assertTrue(ev.peaking_fallback_active)
            self.assertEqual(ev.backup_bin_writes, 0)

    def test_43_write_firewall_blocks_backup_bin_p18_emmc_and_spinor(self) -> None:
        forbidden = (
            P2_BACKUP_BIN_VIRTUAL_PATH,
            P18_LENSFILE_VIRTUAL_PATH,
            "p18:/lens/LENSFILE.BIN",
            "/dev/nflasha18",
            "/dev/cnflasha2",
            "p8:/cpapp-b.bin",
            "p12:/cert/RQ_LIC.DAT",
            "spi_nor:0x000000",
        )
        for path in forbidden:
            g = evaluate_phase183_write_guard(path)
            self.assertFalse(g.valid, f"Should block {path}")
            self.assertTrue(g.persistent_write_blocked)
            self.assertFalse(g.persistent_emmc_writes_authorized)
            self.assertFalse(g.spi_nor_write_authorized)
            self.assertFalse(g.el3_payload_transmit_authorized)
            self.assertEqual(g.physical_usb_packets_emitted, 0)
            self.assertEqual(g.lens_partition_writes, 0)
            self.assertEqual(g.backup_bin_writes, 0)

    def test_44_write_firewall_allows_volatile_tmpfs_and_external_exfat(self) -> None:
        allowed = (
            "/tmp/stage_b/lens_offset.json",
            "ram://emount/focus_map_state",
            "/mnt/sd/PRIVATE/SONY/PRO/LENS/SLOT1.BIN",
            "/mnt/cfexpress_a/CLIP/C0001.MP4",
        )
        for path in allowed:
            g = evaluate_phase183_write_guard(path)
            self.assertTrue(g.valid, f"Should allow {path}")
            self.assertTrue(g.volatile_or_ext_allowed)
            self.assertFalse(g.persistent_write_blocked)

    def test_45_write_firewall_blocks_unlisted_non_volatile_path(self) -> None:
        g = evaluate_phase183_write_guard("/etc/shadow")
        self.assertFalse(g.valid)
        self.assertTrue(g.persistent_write_blocked)

    def test_46_12_touchpoint_4_class_matrix_complete(self) -> None:
        m = build_phase183_emount_compat_matrix()
        self.assertEqual(m.total_touchpoints, 12)
        self.assertEqual(sum(m.class_counts.values()), 12)
        self.assertEqual(sum(m.domain_counts.values()), 12)
        for cls, cnt in m.class_counts.items():
            self.assertGreater(cnt, 0, f"Class {cls} has zero touchpoints")
        self.assertEqual(len(m.domain_counts), 4)

    # ------------------------------------------------------------------
    # 47..50: CLI subcommand, audit-all 38/38 & release constants
    # ------------------------------------------------------------------

    def test_47_cli_subcommand_donor_or_auto_passes(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cli_main(["audit-realhw-emount-info3d-breathing", "--json"])
        self.assertEqual(rc, 0)
        parsed = json.loads(buf.getvalue())
        self.assertTrue(parsed["all_checks_passed"])
        self.assertEqual(parsed["lens_partition_writes"], 0)
        self.assertEqual(parsed["backup_bin_writes"], 0)

    def test_48_cli_subcommand_clean_room_passes(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cli_main(["audit-realhw-emount-info3d-breathing", "--clean-room", "--json"])
        self.assertEqual(rc, 0)
        parsed = json.loads(buf.getvalue())
        self.assertEqual(parsed["mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(parsed["all_checks_passed"])

    def test_49_run_audit_all_registers_38_of_38_auditors(self) -> None:
        summary = run_audit_all(clean_room=True)
        self.assertTrue(summary["all_checks_passed"])
        self.assertIn("realhw_emount_info3d_breathing_02cf0232_audit", summary)
        audit_keys = [k for k in summary.keys() if k.endswith("_audit")]
        self.assertEqual(len(audit_keys), 38)
        self.assertTrue(summary["realhw_emount_info3d_breathing_02cf0232_audit"]["all_checks_passed"])

    def test_50_phase183_constants_exact(self) -> None:
        self.assertEqual(BKID_APP_MR_SETTING_LENS_COMP_BREATHING, 0x02CF0232)
        self.assertEqual(UNSUPPORTED_MANUAL_ADAPTER_LENS_ID, 0xFFFF)
        self.assertEqual(P18_BLKROSET_VALUE, 1)
        self.assertEqual(MC_MIN_SUPPORTED_VERSION, "2.1.0")
        self.assertEqual(EXPECTED_FX6_LENSFILE_ENTRY_COUNT, 57)


if __name__ == "__main__":
    unittest.main()
