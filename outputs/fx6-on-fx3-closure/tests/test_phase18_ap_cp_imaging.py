"""Phase 18 Unit Tests — Cross-Generation AP (FX6 6.01) <-> Stock-CP (FX3 7.02) Imaging Pipeline.

Covers all 4 Phase 18 pillars in BOTH:
1. Local Read-Only Donor mode (when local FX6 6.01 & FX3 7.02 donors exist under
   `~/AI-Workspace/AI/Projects/Mac/work` and `FX3_FX6_FORCE_CLEAN_ROOM != 1`).
2. Clean-Room Synthetic CI mode (`FX3_FX6_FORCE_CLEAN_ROOM=1` / `clean_room_overrides`),
   including positive ABI / Unicorn AArch64 execution tests and negative fault-injection tests.
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import json
import os
import struct
import unittest
from pathlib import Path

from fx6_closure.ap_cp_imaging_pipeline_verifier import (
    EXPECTED_FX6_0X92840747_OPCODES,
    EXPECTED_LENS_COMM_BYTES,
    FX3_MPR_SET_MOVIE_REC_PARAM_BYTES,
    FX6_EXCLUSIVE_CP_QUEUES,
    FX6_MPR_SET_MOVIE_REC_PARAM_BYTES,
    HANDLE_QUEUE_ID,
    HANDLE_REG_CMD,
    HANDLE_UNREG_CMD,
    LUT_33_CUBE_BUFFER_BYTES,
    LUT_DMA_ENABLE_CMD,
    LUT_DMA_ENABLE_SIZE,
    LUT_TOGGLE_CMD,
    LUT_TOGGLE_SIZE,
    PHASE_18_SCHEMA,
    RTC_GET_STATUS_CMD_BYTE,
    RTC_QUEUE_ID,
    SHARED_AP_CP_QUEUES,
    UIPC_BB_COMPLETION_BYTES,
    UIPC_BB_COMPLETION_MASK,
    UIPC_BB_FLAGS,
    UIPC_BB_MAGIC,
    UIPC_BB_TARGET_QUEUE,
    Phase18ProtocolError,
    build_clean_room_phase18_fixtures,
    is_forced_clean_room,
    parse_phase18_uipc_request,
    scan_uipc_queues_and_opcodes,
    synthesize_phase18_uipc_reply,
    verify_ap_cp_imaging_pipeline,
    verify_fx3_ibis_stock_cp_safety_contract,
    verify_lut_cine_ei_and_dual_iso_abi,
    verify_xavc_recording_and_af_contracts,
)


class Phase18ApCpImagingPipelineTests(unittest.TestCase):
    """Comprehensive Phase 18 AP<->Stock-CP verification suite (18 test cases)."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.report = verify_ap_cp_imaging_pipeline()
        cls.clean_fixtures = build_clean_room_phase18_fixtures()

    def test_01_end_to_end_pipeline_passes_and_obeys_u2_redline(self) -> None:
        self.assertTrue(self.report.passed, msg=f"Phase 18 failed: {self.report.errors}")
        self.assertEqual(self.report.schema, PHASE_18_SCHEMA)
        self.assertTrue(self.report.p8_cp_mutation_forbidden)
        self.assertEqual(self.report.cp_mutation_bytes, 0)
        if os.environ.get("FX3_FX6_FORCE_CLEAN_ROOM", "").strip() == "1":
            self.assertEqual(self.report.verification_mode, "clean_room_synthetic")
        else:
            self.assertIn(
                self.report.verification_mode,
                ("local_donor_read_only", "clean_room_synthetic"),
            )

    def test_02_deterministic_report_hash_and_json_serialization(self) -> None:
        r2 = verify_ap_cp_imaging_pipeline()
        self.assertEqual(self.report.report_sha256, r2.report_sha256)
        self.assertEqual(len(self.report.report_sha256), 64)
        parsed = json.loads(self.report.to_deterministic_json())
        self.assertEqual(parsed["report_sha256"], self.report.report_sha256)
        self.assertEqual(parsed["p8_cp_mutation_forbidden"], True)

    def test_03_p1_all_44_uipc_bb_0x92840747_opcodes_matched_in_fx3_cp(self) -> None:
        scan = self.report.uipc_queue_scan
        self.assertTrue(scan.passed, msg=f"UIPC scan errors: {scan.errors}")
        self.assertEqual(scan.total_0x92840747_opcodes_expected, 44)
        self.assertEqual(scan.total_0x92840747_opcodes_matched_in_fx3_cp, 44)
        self.assertEqual(scan.missing_0x92840747_opcodes_in_fx3_cp, ())
        self.assertEqual(len(EXPECTED_FX6_0X92840747_OPCODES), 44)

    def test_04_p1_shared_queues_and_exact_two_fx6_exclusive_queues(self) -> None:
        scan = self.report.uipc_queue_scan
        self.assertEqual(
            scan.shared_queues_verified,
            tuple(f"0x{q:08x}" for q in SHARED_AP_CP_QUEUES),
        )
        self.assertEqual(scan.missing_shared_queues, ())
        self.assertEqual(scan.unexpected_missing_cp_queues, ())
        self.assertEqual(
            set(scan.fx6_exclusive_cp_queues_absent_in_fx3),
            {f"0x{q:08x}" for q in FX6_EXCLUSIVE_CP_QUEUES},
        )
        self.assertEqual(scan.interception_rules_count, 12)

    def test_05_p1_packet_parse_and_synthesize_rtc_handle_and_lut(self) -> None:
        # 1) RTC 0x92d2091c 2B sync request -> [0x03, 0x00] reply
        rtc_req = bytes((RTC_GET_STATUS_CMD_BYTE, 0x00))
        decoded_rtc = parse_phase18_uipc_request(RTC_QUEUE_ID, rtc_req)
        self.assertEqual(decoded_rtc["subsystem"], "infra_wrapper_rtc")
        self.assertEqual(synthesize_phase18_uipc_reply(RTC_QUEUE_ID, rtc_req), b"\x03\x00")

        # 2) Handle 0x91db059b 12B register & unregister
        for cmd in (HANDLE_REG_CMD, HANDLE_UNREG_CMD):
            h_req = struct.pack("<III", cmd, 0, 0x91DB059C)
            decoded_h = parse_phase18_uipc_request(HANDLE_QUEUE_ID, h_req)
            self.assertEqual(decoded_h["subsystem"], "infra_wrapper_handle")
            h_rep = synthesize_phase18_uipc_reply(HANDLE_QUEUE_ID, h_req)
            self.assertEqual(len(h_rep), 12)
            r_cmd, r_status, r_cb = struct.unpack("<III", h_rep)
            self.assertEqual(r_cmd, cmd | 0x01000000)
            self.assertEqual(r_status, 0)
            self.assertEqual(r_cb, 0x91DB059C)

        # 3) 3D LUT DMA 0x0165 (36B) and toggle 0x0166 (10B) on 0x92840747
        lut_dma_req = struct.pack("<HHHH", UIPC_BB_MAGIC, LUT_DMA_ENABLE_CMD, LUT_DMA_ENABLE_SIZE, UIPC_BB_FLAGS) + b"\x00" * (LUT_DMA_ENABLE_SIZE - 8)
        lut_dma_rep = synthesize_phase18_uipc_reply(UIPC_BB_TARGET_QUEUE, lut_dma_req)
        self.assertEqual(len(lut_dma_rep), UIPC_BB_COMPLETION_BYTES)
        magic, cmp_op, cmp_len, cmp_flags, status = struct.unpack("<HHHHI", lut_dma_rep)
        self.assertEqual(magic, UIPC_BB_MAGIC)
        self.assertEqual(cmp_op, LUT_DMA_ENABLE_CMD | UIPC_BB_COMPLETION_MASK)
        self.assertEqual(cmp_len, UIPC_BB_COMPLETION_BYTES)
        self.assertEqual(cmp_flags, UIPC_BB_FLAGS)
        self.assertEqual(status, 0)

        lut_tog_req = struct.pack("<HHHHH", UIPC_BB_MAGIC, LUT_TOGGLE_CMD, LUT_TOGGLE_SIZE, UIPC_BB_FLAGS, 1)
        lut_tog_rep = synthesize_phase18_uipc_reply(UIPC_BB_TARGET_QUEUE, lut_tog_req)
        self.assertEqual(struct.unpack("<HHHHI", lut_tog_rep)[1], LUT_TOGGLE_CMD | UIPC_BB_COMPLETION_MASK)

    def test_06_p1_rejects_malformed_uipc_requests(self) -> None:
        with self.assertRaises(Phase18ProtocolError):
            parse_phase18_uipc_request(RTC_QUEUE_ID, b"\x03")
        with self.assertRaises(Phase18ProtocolError):
            parse_phase18_uipc_request(RTC_QUEUE_ID, b"\x09\x00")
        with self.assertRaises(Phase18ProtocolError):
            parse_phase18_uipc_request(HANDLE_QUEUE_ID, struct.pack("<III", 0xDEAD0001, 0, 0))
        with self.assertRaises(Phase18ProtocolError):
            parse_phase18_uipc_request(
                UIPC_BB_TARGET_QUEUE,
                struct.pack("<HHHH", UIPC_BB_MAGIC, LUT_DMA_ENABLE_CMD, 10, UIPC_BB_FLAGS) + b"\x00\x00",
            )
        with self.assertRaises(Phase18ProtocolError):
            parse_phase18_uipc_request(0x9000FFFF, b"\x00\x00")

    def test_07_p1_negative_fault_injection_missing_0x0165_lut_opcode(self) -> None:
        bad = verify_ap_cp_imaging_pipeline(clean_room_overrides={"drop_0x92840747_opcode": 0x0165})
        self.assertFalse(bad.passed)
        self.assertFalse(bad.uipc_queue_scan.passed)
        self.assertIn("0x0165", bad.uipc_queue_scan.missing_0x92840747_opcodes_in_fx3_cp)

    def test_08_p1_negative_fault_injection_fx3_cp_contains_unexpected_exclusive_queue_mismatch(self) -> None:
        bad = verify_ap_cp_imaging_pipeline(clean_room_overrides={"include_fx6_only_queues_in_fx3_cp": True})
        self.assertFalse(bad.passed)
        self.assertFalse(bad.uipc_queue_scan.passed)
        self.assertEqual(bad.uipc_queue_scan.fx6_exclusive_cp_queues_absent_in_fx3, ())

    def test_09_p2_33_cube_lut_allocation_and_cxd90057_isp_markers(self) -> None:
        lut = self.report.lut_cine_ei_dual_iso
        self.assertTrue(lut.passed, msg=f"LUT/CineEI/ISO failed: {lut.errors}")
        self.assertEqual(lut.fx3_cube_alloc_bytes, LUT_33_CUBE_BUFFER_BYTES)
        self.assertEqual(lut.fx6_cube_alloc_bytes, LUT_33_CUBE_BUFFER_BYTES)
        self.assertEqual(lut.fx3_set_lut_bytes, 164)
        self.assertEqual(lut.fx6_set_lut_bytes, 164)
        self.assertEqual(lut.dual_native_iso_bases, (800, 12800))
        self.assertEqual(lut.missing_shared_liroseq_keys, ())
        self.assertEqual(len(lut.fx3_cp_isp_mlut_markers_present), 6)
        self.assertEqual(len(lut.fx6_cp_isp_mlut_markers_present), 6)
        self.assertIn("uc_HighGainMode", lut.fx6_only_ei_iso_keys)
        self.assertIn("HyperGainMode", lut.fx3_only_ei_iso_keys)

    def test_10_p2_unicorn_aarch64_mpr_set_and_execute_lut_all_branches(self) -> None:
        cases = {(c.target_model, c.case_name): c for c in self.report.lut_cine_ei_dual_iso.unicorn_mpr_cases}
        self.assertEqual(len(cases), 6)
        for model, expected_tag in (("FX6_6.01", 0x7B), ("FX3_7.02", 0x6F)):
            c_dis = cases[(model, "disable_reset_lut")]
            self.assertEqual(c_dis.return_code, 0)
            self.assertTrue(c_dis.reset_lut_called)
            self.assertFalse(c_dis.execute_lut_called)
            self.assertEqual(c_dis.notify_tag, expected_tag)
            self.assertTrue(c_dis.sp_preserved)

            c_emp = cases[(model, "enable_empty_path_error")]
            self.assertEqual(c_emp.return_code, 2)
            self.assertTrue(c_emp.execute_lut_called)
            self.assertEqual(c_emp.malloc_size, 0)
            self.assertTrue(c_emp.sp_preserved)

            c_ok = cases[(model, "enable_33_cube_valid")]
            self.assertEqual(c_ok.return_code, 0)
            self.assertTrue(c_ok.execute_lut_called)
            self.assertEqual(c_ok.malloc_size, 434617)
            self.assertTrue(c_ok.state_26b_copied)
            self.assertEqual(c_ok.state_64b_path, "/usr/data/lut/SLog3SGamut3Cine.cube")
            self.assertEqual(c_ok.notify_tag, expected_tag)
            self.assertTrue(c_ok.sp_preserved)

    def test_11_p2_unicorn_aarch64_appfw_0166_and_rtc_hang_vs_intercepted(self) -> None:
        by_name = {c.case_name: c for c in self.report.lut_cine_ei_dual_iso.unicorn_appfw_cases}
        self.assertEqual(len(by_name), 4)

        c_lut = by_name["appfw_lookname_0166_enable"]
        self.assertTrue(c_lut.completed_normally)
        self.assertEqual(c_lut.return_value, 0)
        self.assertEqual(c_lut.destination_queue, UIPC_BB_TARGET_QUEUE)
        self.assertEqual(c_lut.request_hex, "0d2066010a0001800100")
        self.assertEqual(c_lut.reply_hex, "0d2066110c00018000000000")
        self.assertTrue(c_lut.sp_preserved)

        c_ok = by_name["appfw_rtc_get_status_intercepted"]
        self.assertTrue(c_ok.completed_normally)
        self.assertFalse(c_ok.hang_detected)
        self.assertEqual(c_ok.destination_queue, RTC_QUEUE_ID)
        self.assertEqual(c_ok.request_hex, "0300")
        self.assertEqual(c_ok.reply_hex, "0300")

        c_hang = by_name["appfw_rtc_get_status_unintercepted_hang"]
        self.assertFalse(c_hang.completed_normally)
        self.assertTrue(c_hang.hang_detected)
        self.assertEqual(c_hang.destination_queue, RTC_QUEUE_ID)

        c_cb = by_name["appfw_rtc_reply_ok_0x92d2091c"]
        self.assertTrue(c_cb.completed_normally)
        self.assertEqual(c_cb.return_value, 1)

    def test_12_p2_negative_fault_injection_corrupt_cube_alloc_size(self) -> None:
        bad = verify_ap_cp_imaging_pipeline(clean_room_overrides={"corrupt_cube_alloc_bytes": True})
        self.assertFalse(bad.passed)
        self.assertFalse(bad.lut_cine_ei_dual_iso.passed)
        self.assertEqual(bad.lut_cine_ei_dual_iso.fx6_cube_alloc_bytes, 0)

    def test_13_p3_xavc_recording_matrix_and_lens_comm_zero_code_diff(self) -> None:
        xavc = self.report.xavc_and_af
        self.assertTrue(xavc.passed, msg=f"XAVC/AF failed: {xavc.errors}")
        self.assertEqual(xavc.fx3_movie_rec_param_bytes, FX3_MPR_SET_MOVIE_REC_PARAM_BYTES)
        self.assertEqual(xavc.fx6_movie_rec_param_bytes, FX6_MPR_SET_MOVIE_REC_PARAM_BYTES)
        self.assertEqual(xavc.lens_comm_fx3_bytes, EXPECTED_LENS_COMM_BYTES)
        self.assertEqual(xavc.lens_comm_fx6_bytes, EXPECTED_LENS_COMM_BYTES)
        self.assertEqual(xavc.lens_comm_loadable_segment_diff_bytes, 0)
        self.assertEqual(xavc.lens_comm_total_diff_bytes, 6)
        self.assertEqual(xavc.lens_comm_comment_diff_bytes, 6)

        fmt_map = {e.format_id: e for e in xavc.recording_matrix}
        self.assertTrue(fmt_map["XAVC_I_DCI_4K"].fx3_stock_cp_supported)
        self.assertTrue(fmt_map["XAVC_I_QFHD"].fx3_stock_cp_supported)
        self.assertTrue(fmt_map["XAVC_L_QFHD"].fx3_stock_cp_supported)
        self.assertEqual(fmt_map["XAVC_I_L_FHD"].status, "SUPPORTED_WITH_LIROSEQ_GUARD")
        self.assertTrue(fmt_map["SQ_HFR_4K_120P"].fx3_stock_cp_supported)

    def test_14_p3_negative_fault_injection_tampered_lens_comm_text(self) -> None:
        bad = verify_ap_cp_imaging_pipeline(clean_room_overrides={"tamper_lens_comm_text": True})
        self.assertFalse(bad.passed)
        self.assertFalse(bad.xavc_and_af.passed)
        self.assertGreater(bad.xavc_and_af.lens_comm_loadable_segment_diff_bytes, 0)

    def test_15_p4_fx3_five_axis_ibis_center_lock_and_stock_restore_proof(self) -> None:
        ibis = self.report.ibis_safety
        self.assertTrue(ibis.passed, msg=f"IBIS safety failed: {ibis.errors}")
        self.assertTrue(ibis.fx6_has_imager_fixed_param)
        self.assertFalse(ibis.fx6_has_set_steadyshot_advanced_movie_i)
        self.assertFalse(ibis.fx6_cp_has_body_axis_ibis)
        self.assertEqual(ibis.fx3_cp_ibis_markers_missing, ())
        self.assertEqual(ibis.shared_is_mode_keys_present, ("is_mode", "is_on_movie", "is_type"))
        self.assertTrue(ibis.center_lock_mechanism_verified)
        self.assertIn("HallPIDOUT_0", ibis.fx3_cp_ibis_markers_present)
        self.assertIn("CheckSetSteadyShotAdvancedMovie", ibis.fx3_cp_ibis_markers_present)
        self.assertIn("LiroSeq: Restore.", ibis.fx3_cp_ibis_markers_present)

    def test_16_p4_negative_fault_injection_stripped_fx3_ibis_markers(self) -> None:
        bad = verify_ap_cp_imaging_pipeline(clean_room_overrides={"strip_fx3_ibis_markers": True})
        self.assertFalse(bad.passed)
        self.assertFalse(bad.ibis_safety.passed)
        self.assertFalse(bad.ibis_safety.center_lock_mechanism_verified)
        self.assertGreater(len(bad.ibis_safety.fx3_cp_ibis_markers_missing), 0)

    def test_17_clean_room_component_helpers_run_independently(self) -> None:
        fx = self.clean_fixtures
        r_uipc = scan_uipc_queues_and_opcodes(fx["fx6_appfw"], fx["fx3_cpapp"], fx["fx6_cpapp"])
        r_lut = verify_lut_cine_ei_and_dual_iso_abi(
            fx["fx3_libmpr"], fx["fx6_libmpr"], fx["fx6_appfw"], fx["fx3_cpapp"], fx["fx6_cpapp"], synthetic_mode=True
        )
        r_xavc = verify_xavc_recording_and_af_contracts(
            fx["fx3_lens_comm"], fx["fx6_lens_comm"], fx["fx3_cpapp"], fx["fx6_cpapp"]
        )
        r_ibis = verify_fx3_ibis_stock_cp_safety_contract(
            fx["fx6_appfw"], fx["fx3_cpapp"], fx["fx6_cpapp"]
        )
        self.assertTrue(r_uipc.passed and r_lut.passed and r_xavc.passed and r_ibis.passed)

    def test_18_path_hygiene_and_forced_clean_room_env_contract(self) -> None:
        verifier_path = Path(__file__).resolve().parents[1] / "fx6_closure" / "ap_cp_imaging_pipeline_verifier.py"
        verifier_src = verifier_path.read_text(encoding="utf-8")
        forbidden_prefix = "/Volumes/" + "KAFU2T"
        self.assertNotIn(forbidden_prefix, verifier_src)
        self.assertIn("AI-Workspace", verifier_src)
        if os.environ.get("FX3_FX6_FORCE_CLEAN_ROOM", "").strip() == "1":
            self.assertTrue(is_forced_clean_room())


if __name__ == "__main__":
    unittest.main()
