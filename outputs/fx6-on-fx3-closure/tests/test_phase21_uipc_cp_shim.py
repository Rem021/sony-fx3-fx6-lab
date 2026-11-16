"""Phase 21 (P11) Unit Tests — AP-Side Dual-Blocking UIPC Queue Synthesizer & Cine EI / LUT / IBIS Bridge.

Covers both:
1. Local Read-Only Donor mode (real FX6 6.01 & FX3 7.02 binaries via `O_RDONLY` + `donor_paths.py`).
2. Clean-Room Synthetic CI mode (`FX3_FX6_FORCE_CLEAN_ROOM=1` synthetic ELF64 + AArch64 + Thumb-2 fixtures).
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import io
import json
import os
import struct
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from fx6_closure.uipc_cp_shim_verifier import (
    CP_MUTATION_BYTES,
    DUAL_NATIVE_ISO_BASES,
    FX3_SUPPORTED_0X92840747_DEVELOP_OPCODES,
    FX6_APPFW_HANDLE_REG_ASSERT_LINE,
    HANDLE_EVENT_ATTACHED_ID,
    HANDLE_EVENT_DETACHED_ID,
    HANDLE_EVT_ATTACHED_CMD,
    HANDLE_EVT_DETACHED_CMD,
    HANDLE_QUEUE_ID,
    HANDLE_REG_CMD,
    HANDLE_UNREG_CMD,
    LUT_8BIT_ALIGNED_BYTES,
    LUT_8BIT_RAW_BYTES,
    LUT_16BIT_BYTES,
    LUT_CUBE_ALLOC_BYTES,
    LUT_DMA_ENABLE_SIZE,
    LUT_TOGGLE_SIZE,
    MPR_SET_LUT_DESCRIPTOR_BYTES,
    P8_CP_MUTATION_FORBIDDEN,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHASE_21_SCHEMA,
    RTC_GET_STATUS_CMD_BYTE,
    RTC_QUEUE_ID,
    UDATE_TIME_TYPE_LOCAL,
    UDATE_TIME_TYPE_UNSET,
    UIPC_BB_FLAGS,
    UIPC_BB_MAGIC,
    UIPC_BB_OPCODE_P5_AUDIO_HDMI,
    UIPC_BB_TARGET_QUEUE,
    CineEiLutDmaStateMachine,
    LinuxRtcTime,
    Phase21ProtocolError,
    UipcCpShimRuntime,
    build_0x0165_lut_dma_packet,
    build_0x0166_lut_toggle_packet,
    build_clean_room_phase21_fixtures,
    build_mpr_set_lut_descriptor,
    decode_udate_notification,
    evaluate_ibis_steadyshot_bridge,
    is_phase21_clean_room_mode,
    main as cli_main,
    parse_smart_handle_request,
    resolve_phase21_donor_paths,
    rtc_time_to_udate_notification,
    run_phase21_uipc_cp_shim_verification,
    synthesize_smart_handle_ack,
    translate_developing_mode_fhd,
    translate_rtc0_to_0x92d2091c_reply,
)


class Phase21UipcCpShimTests(unittest.TestCase):
    """Comprehensive Phase 21 (`P11`) verification test suite (20 tests)."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.report = run_phase21_uipc_cp_shim_verification()
        cls.clean_fixtures = build_clean_room_phase21_fixtures()

    def test_01_end_to_end_verification_passes_and_locks_redlines(self) -> None:
        self.assertTrue(self.report.passed, msg=f"Phase 21 errors: {self.report.errors}")
        self.assertEqual(self.report.schema, PHASE_21_SCHEMA)
        self.assertFalse(self.report.persistent_emmc_writes_authorized)
        self.assertFalse(self.report.persistent_write_release)
        self.assertTrue(self.report.p8_cp_mutation_forbidden)
        self.assertEqual(self.report.cp_mutation_bytes, 0)
        self.assertEqual(self.report.donor_access_mode, "O_RDONLY")
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(PERSISTENT_WRITE_RELEASE)
        self.assertTrue(P8_CP_MUTATION_FORBIDDEN)
        self.assertEqual(CP_MUTATION_BYTES, 0)

    def test_02_deterministic_report_hash_and_json_roundtrip(self) -> None:
        r2 = run_phase21_uipc_cp_shim_verification()
        self.assertEqual(self.report.report_sha256, r2.report_sha256)
        self.assertEqual(len(self.report.report_sha256), 64)
        parsed = json.loads(self.report.to_deterministic_json())
        self.assertEqual(parsed["report_sha256"], self.report.report_sha256)
        self.assertTrue(parsed["passed"])
        self.assertFalse(parsed["persistent_emmc_writes_authorized"])

    def test_03_exact_two_fx6_exclusive_blocking_queues_absent_in_fx3_cp(self) -> None:
        self.assertEqual(
            set(self.report.fx6_exclusive_blocking_queues),
            {f"0x{RTC_QUEUE_ID:08x}", f"0x{HANDLE_QUEUE_ID:08x}"},
        )
        self.assertTrue(self.report.libmpr_cube_alloc_verified)

    def test_04_queue1_rtc_unicorn_unintercepted_hang_proven(self) -> None:
        hang_case = self.report.queue1_rtc_cases[0]
        self.assertEqual(hang_case.case_name, "q1_unintercepted_future_wait_hang")
        self.assertTrue(hang_case.hang_detected)
        self.assertFalse(hang_case.completed_normally)
        self.assertEqual(hang_case.destination_queue, RTC_QUEUE_ID)
        self.assertEqual(hang_case.request_hex, "0300")
        self.assertTrue(hang_case.sp_preserved)

    def test_05_queue1_rtc_unicorn_synthesized_reply_unblocks_promise_and_frees_msg(self) -> None:
        send_case = self.report.queue1_rtc_cases[1]
        self.assertTrue(send_case.completed_normally)
        self.assertFalse(send_case.hang_detected)
        self.assertEqual(send_case.reply_hex, "0300")

        cb_ok = self.report.queue1_rtc_cases[2]
        self.assertTrue(cb_ok.completed_normally)
        self.assertEqual(cb_ok.promise_bool_value, 1)
        self.assertEqual(cb_ok.expected_get_rtc_status_rc, 0)
        self.assertTrue(cb_ok.free_msg_called)
        self.assertTrue(cb_ok.sp_preserved)

    def test_06_queue1_rtc_unicorn_unset_rtc_and_wrong_src_negative_cases(self) -> None:
        cb_unset = self.report.queue1_rtc_cases[3]
        self.assertEqual(cb_unset.reply_hex, "0301")
        self.assertEqual(cb_unset.promise_bool_value, 0)
        self.assertEqual(cb_unset.expected_get_rtc_status_rc, 2)
        self.assertTrue(cb_unset.free_msg_called)

        cb_wrong_src = self.report.queue1_rtc_cases[4]
        self.assertIsNone(cb_wrong_src.promise_bool_value)
        self.assertTrue(cb_wrong_src.free_msg_called)

    def test_07_linux_rtc0_to_udate_notification_struct_roundtrip(self) -> None:
        rtc = LinuxRtcTime(tm_sec=12, tm_min=34, tm_hour=15, tm_mday=14, tm_mon=10, tm_year=126)
        raw = rtc_time_to_udate_notification(rtc, time_type=UDATE_TIME_TYPE_LOCAL, td_minutes=540)
        self.assertEqual(len(raw), 44)
        udate = decode_udate_notification(raw)
        self.assertEqual(udate.year, 2026)
        self.assertEqual(udate.month, 11)
        self.assertEqual(udate.day, 14)
        self.assertEqual(udate.hour, 15)
        self.assertEqual(udate.minute, 34)
        self.assertEqual(udate.second, 12)
        self.assertEqual(udate.time_type, UDATE_TIME_TYPE_LOCAL)
        self.assertEqual(udate.td_minutes, 540)

        reply, u2 = translate_rtc0_to_0x92d2091c_reply(b"\x03\x00", rtc)
        self.assertEqual(reply, b"\x03\x00")
        self.assertEqual(u2.year, 2026)

        bad_rtc = LinuxRtcTime(tm_sec=0, tm_min=0, tm_hour=0, tm_mday=31, tm_mon=1, tm_year=126)  # Feb 31 invalid
        reply_bad, u_bad = translate_rtc0_to_0x92d2091c_reply(b"\x03\x00", bad_rtc)
        self.assertEqual(reply_bad, b"\x03\x01")
        self.assertEqual(u_bad.time_type, UDATE_TIME_TYPE_UNSET)

    def test_08_queue2_handle_unicorn_unintercepted_assert_line_123(self) -> None:
        assert_case = self.report.queue2_handle_cases[0]
        self.assertTrue(assert_case.assert_hit)
        self.assertEqual(assert_case.assert_line, FX6_APPFW_HANDLE_REG_ASSERT_LINE)
        self.assertFalse(assert_case.completed_normally)
        self.assertEqual(assert_case.destination_queue, HANDLE_QUEUE_ID)

    def test_09_queue2_handle_unicorn_detached_ack_callbacks_and_unregister(self) -> None:
        reg_ok = self.report.queue2_handle_cases[1]
        self.assertFalse(reg_ok.assert_hit)
        self.assertIn(HANDLE_EVENT_DETACHED_ID, reg_ok.posted_events)
        self.assertEqual(reg_ok.request_hex[:8], "01000081")
        self.assertEqual(reg_ok.reply_hex[:8], "01000081")

        cb_det = self.report.queue2_handle_cases[2]
        self.assertEqual(cb_det.posted_events, (HANDLE_EVENT_DETACHED_ID,))
        self.assertTrue(cb_det.free_msg_called)

        cb_att = self.report.queue2_handle_cases[3]
        self.assertEqual(cb_att.posted_events, (HANDLE_EVENT_ATTACHED_ID,))
        self.assertTrue(cb_att.free_msg_called)

        unreg_ok = self.report.queue2_handle_cases[4]
        self.assertFalse(unreg_ok.assert_hit)
        self.assertEqual(unreg_ok.request_hex[:8], "02000081")

    def test_10_xlr_h1_mi_shoe_audio_coexistence_verified(self) -> None:
        self.assertEqual(len(self.report.xlr_h1_digmic_markers_present), 2)
        for case in self.report.queue2_handle_cases:
            self.assertEqual(case.xlr_h1_hotshoe_rc, 0)
            self.assertTrue(case.sp_preserved)

        req_12b = struct.pack("<III", HANDLE_REG_CMD, 0, 0x81CC0501)
        decoded = parse_smart_handle_request(req_12b)
        self.assertEqual(decoded["operation"], "register_callback")
        sync_ack, async_msg, evt = synthesize_smart_handle_ack(req_12b, grip_attached=False)
        self.assertEqual(evt, HANDLE_EVENT_DETACHED_ID)
        self.assertEqual(struct.unpack("<III", sync_ack)[0], HANDLE_REG_CMD | 0x01000000)
        self.assertEqual(struct.unpack("<III", async_msg)[0], HANDLE_EVT_DETACHED_CMD)

    def test_11_developing_mode_fhd_translation_and_validation(self) -> None:
        dev = self.report.developing_fhd_translation
        self.assertEqual(dev.source_pid_hex, "0x0362")
        self.assertEqual(dev.source_reply_pid_hex, "0x10c1")
        self.assertEqual(dev.source_liroseq_key, "developing_mode_FHD")
        self.assertEqual(dev.target_resolution, "1920x1080")
        self.assertEqual(dev.mapped_liroseq_keys["mov_size_req"], 2)
        self.assertEqual(dev.mapped_liroseq_keys["frate_req"], 59)
        self.assertEqual(len(dev.uipc_0x92840747_packets_hex), 4)
        self.assertEqual(len(dev.fx3_cp_opcodes_verified), len(FX3_SUPPORTED_0X92840747_DEVELOP_OPCODES))

        with self.assertRaises(Phase21ProtocolError):
            translate_developing_mode_fhd(developing_mode_fhd=99)
        with self.assertRaises(Phase21ProtocolError):
            translate_developing_mode_fhd(fps=48)

    def test_12_mpr_set_lut_164b_descriptor_and_cube_alloc(self) -> None:
        desc = build_mpr_set_lut_descriptor(
            enable=True,
            cube_path="/usr/data/lut/SLog3SGamut3Cine.cube",
            lut_payload_bytes=LUT_8BIT_ALIGNED_BYTES,
            base_iso=800,
            ei_index=800,
        )
        self.assertEqual(len(desc), MPR_SET_LUT_DESCRIPTOR_BYTES)
        self.assertEqual(desc[0x04], 1)
        path_slice = desc[0x1F : 0x5F].split(b"\x00", 1)[0].decode("latin1")
        self.assertEqual(path_slice, "/usr/data/lut/SLog3SGamut3Cine.cube")
        self.assertIn(LUT_CUBE_ALLOC_BYTES, struct.unpack_from("<BBHIIIIII", desc, 0x05))

    def test_13_unicorn_0x0165_0x0166_dma_threshold_matches_state_machine(self) -> None:
        img_8bit = self.report.imaging_bridge_cases[0]
        img_16bit = self.report.imaging_bridge_cases[1]
        img_0166 = self.report.imaging_bridge_cases[2]

        self.assertEqual(img_8bit.packet_bytes, LUT_DMA_ENABLE_SIZE)
        self.assertEqual(img_16bit.packet_bytes, LUT_DMA_ENABLE_SIZE)
        self.assertEqual(img_0166.packet_bytes, LUT_TOGGLE_SIZE)
        self.assertEqual(img_0166.packet_hex, "0d2066010a0001800100")

        # Verify <= 48,000 B takes inline SRAM path while > 48,000 B (107,812 / 215,622) takes DMA SRAM+REG
        small_pkt = build_0x0165_lut_dma_packet(
            category=3, look_name=0, exist_user_lut=1, data_size=4096,
            data_offset_sram=0x1000, data_size_sram=4096, data_offset_reg=0x20000, data_size_reg=0x400,
        )
        self.assertEqual(struct.unpack_from("<IIIII", small_pkt, 0x10), (4096, 0, 0, 0, 0))
        dma_pkt = build_0x0165_lut_dma_packet(
            category=3, look_name=0, exist_user_lut=1, data_size=LUT_16BIT_BYTES,
            data_offset_sram=0x1000, data_size_sram=LUT_16BIT_BYTES, data_offset_reg=0x20000, data_size_reg=0x400,
        )
        self.assertEqual(dma_pkt.hex(), img_16bit.packet_hex)

    def test_14_cine_ei_lut_roundtrip_state_machine_and_dual_base_iso(self) -> None:
        trace = self.report.lut_state_machine_trace
        self.assertEqual([t.state for t in trace], [
            "CUBE_STAGED",
            "DMA_0165_ARMED",
            "LOOKNAME_0166_ENABLED",
            "LOOKNAME_0166_ENABLED",
            "RESET_DISABLED",
        ])
        self.assertEqual(trace[0].base_iso, 800)
        self.assertEqual(trace[0].liroseq_params["baseSensitivity"], 0)
        self.assertEqual(trace[3].base_iso, 12800)
        self.assertEqual(trace[3].liroseq_params["baseSensitivity"], 1)
        self.assertEqual(trace[3].liroseq_params["HyperGainMode"], 1)
        self.assertEqual(trace[3].liroseq_params["uc_HighGainMode"], 1)
        self.assertEqual(trace[4].toggle_packet_0166_hex, build_0x0166_lut_toggle_packet(enable=False).hex())

    def test_15_cine_ei_and_lut_negative_fault_injections(self) -> None:
        fsm = CineEiLutDmaStateMachine()
        with self.assertRaises(Phase21ProtocolError):
            fsm.arm_dma_0165()
        with self.assertRaises(Phase21ProtocolError):
            fsm.enable_look_0166()
        with self.assertRaises(Phase21ProtocolError):
            fsm.stage_cube_lut("/tmp/bad.cube", lut_payload_bytes=12345)
        with self.assertRaises(Phase21ProtocolError):
            fsm.stage_cube_lut("/" + "a" * 70 + ".cube", lut_payload_bytes=LUT_8BIT_RAW_BYTES)
        with self.assertRaises(Phase21ProtocolError):
            fsm.set_cine_ei(base_iso=3200, ei_index=3200)
        with self.assertRaises(Phase21ProtocolError):
            fsm.set_cine_ei(base_iso=DUAL_NATIVE_ISO_BASES[0], ei_index=50)

    def test_16_fx3_5axis_ibis_steadyshot_bridge_and_unicorn_tc_mapping(self) -> None:
        off_s, std_s, act_s = self.report.ibis_telemetry_bridge
        self.assertEqual((off_s.is_on_movie, off_s.is_mode), (0, 0))
        self.assertTrue(off_s.center_lock_energized)
        self.assertFalse(off_s.floating_sensor_hazard)

        self.assertEqual((std_s.is_on_movie, std_s.is_mode), (1, 1))
        self.assertTrue(std_s.center_lock_energized)

        self.assertEqual((act_s.is_on_movie, act_s.is_mode), (1, 1))
        self.assertFalse(act_s.floating_sensor_hazard)
        act_bridged = evaluate_ibis_steadyshot_bridge("Active", ap_active_extension_enabled=True)
        self.assertTrue(act_bridged.active_electronic_crop_bridged)
        self.assertEqual(act_bridged.is_mode, 2)

        with self.assertRaises(Phase21ProtocolError):
            evaluate_ibis_steadyshot_bridge("InvalidMode")

        self.assertEqual(self.report.imaging_bridge_cases[3].return_code, 1)  # Standard -> 1
        self.assertEqual(self.report.imaging_bridge_cases[4].return_code, 0)  # Off -> 0

    def test_17_uipc_cp_shim_runtime_dispatcher_and_malformed_rejection(self) -> None:
        rt = UipcCpShimRuntime()
        r1 = rt.dispatch(RTC_QUEUE_ID, bytes((RTC_GET_STATUS_CMD_BYTE, 0x00)))
        self.assertTrue(r1.intercepted_by_shim)
        self.assertEqual(r1.reply_hex, "0300")

        r2 = rt.dispatch(HANDLE_QUEUE_ID, struct.pack("<III", HANDLE_UNREG_CMD, 0, 0x81CC0501))
        self.assertTrue(r2.intercepted_by_shim)
        self.assertEqual(r2.raw_status, 0)

        p5_req = struct.pack("<HHHHH", UIPC_BB_MAGIC, UIPC_BB_OPCODE_P5_AUDIO_HDMI, 10, UIPC_BB_FLAGS, 0)
        r3 = rt.dispatch(UIPC_BB_TARGET_QUEUE, p5_req)
        self.assertEqual(r3.raw_status, 0x00580000)

        with self.assertRaises(Phase21ProtocolError):
            rt.dispatch(0x99999999, b"\x00\x01")
        with self.assertRaises(Phase21ProtocolError):
            rt.dispatch(UIPC_BB_TARGET_QUEUE, b"\x01\x02")
        with self.assertRaises(Phase21ProtocolError):
            rt.dispatch(RTC_QUEUE_ID, b"\x09\x00")

    def test_18_clean_room_fault_injection_fixtures_detect_regressions(self) -> None:
        bad_q = build_clean_room_phase21_fixtures(inject_blocking_queue_into_fx3_cp=True)
        r_bad_q = run_phase21_uipc_cp_shim_verification(donor_blobs=bad_q, synthetic_mode=True)
        self.assertFalse(r_bad_q.passed)

        bad_op = build_clean_room_phase21_fixtures(drop_develop_opcode=0x0416)
        r_bad_op = run_phase21_uipc_cp_shim_verification(donor_blobs=bad_op, synthetic_mode=True)
        self.assertFalse(r_bad_op.passed)

        bad_ibis = build_clean_room_phase21_fixtures(strip_fx3_ibis_markers=True)
        r_bad_ibis = run_phase21_uipc_cp_shim_verification(donor_blobs=bad_ibis, synthetic_mode=True)
        self.assertFalse(r_bad_ibis.passed)

        bad_cube = build_clean_room_phase21_fixtures(corrupt_cube_alloc_bytes=True)
        r_bad_cube = run_phase21_uipc_cp_shim_verification(donor_blobs=bad_cube, synthetic_mode=True)
        self.assertFalse(r_bad_cube.passed)

    def test_19_forced_clean_room_mode_isolation(self) -> None:
        with patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            paths = resolve_phase21_donor_paths()
            self.assertTrue(is_phase21_clean_room_mode(paths))
            for p in paths.values():
                self.assertIn("__fx3_fx6_clean_room_donor_disabled__", str(p))
            cr_report = run_phase21_uipc_cp_shim_verification()
            self.assertTrue(cr_report.passed, msg=f"Clean-room failed: {cr_report.errors}")
            self.assertEqual(cr_report.verification_mode, "CLEAN_ROOM_SYNTHETIC_VERIFIED")

    def test_20_cli_entrypoint_json_and_text_exit_zero(self) -> None:
        buf_txt = io.StringIO()
        with redirect_stdout(buf_txt):
            rc_txt = cli_main([])
        self.assertEqual(rc_txt, 0)
        self.assertIn("PASS", buf_txt.getvalue())

        buf_json = io.StringIO()
        with redirect_stdout(buf_json):
            rc_json = cli_main(["--json"])
        self.assertEqual(rc_json, 0)
        parsed = json.loads(buf_json.getvalue())
        self.assertEqual(parsed["schema"], PHASE_21_SCHEMA)
        self.assertTrue(parsed["passed"])


if __name__ == "__main__":
    unittest.main()
