"""Unit tests for Phase 51 4-Ch 24-bit 48kHz Audio, SMPTE 12M Timecode & 12G-SDI->HDMI Type-A Auditor.

Designed to pass rapidly in BOTH Local Donor (`os.O_RDONLY`) and
`FX3_FX6_FORCE_CLEAN_ROOM=1` modes while keeping the full `fx3-firmware-lab`
suite (>=183 tests) under 6 seconds in clean-room mode.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from typing import Optional
from unittest.mock import patch

from fx3_firmware_lab.__main__ import main as cli_main, run_audit_all
from fx3_firmware_lab.audio_tc_hdmi_sdi_routing_auditor import (
    AUDIO_4CH_24BIT_BITRATE_BPS,
    AUDIO_BIT_DEPTH_24,
    AUDIO_CHANNELS_4CH,
    AUDIO_SAMPLE_RATE_HZ,
    FX3_APPFW_AUDIO_MARKERS,
    FX3_HDMI_RAW_SENSOR_READOUT,
    FX6_APPFW_AUDIO_MARKERS,
    FX6_APPFW_MLUT_AND_SDI_MARKERS,
    FX6_AVBB_PANELEVF_MARKERS,
    FX6_HOTSHOE_MARKERS,
    LIBINFRAHOTSHOE_TMO_SAFE_RC,
    P11_SMART_HANDLE_ATTACHED_EVT,
    P11_SMART_HANDLE_DETACHED_EVT,
    PHASE_51_SCHEMA,
    SHARED_APPFW_TIMECODE_MARKERS,
    AudioTcHdmiSdiRoutingReport,
    analyze_audio_tc_hdmi_sdi_routing,
    audio_tc_hdmi_sdi_routing_report_to_dict,
    build_clean_room_audio_tc_hdmi_fixtures,
    encode_smpte12m_bcd,
    evaluate_p11_hot_detach_audio_fallback,
    evaluate_smpte12m_tc_routing,
    evaluate_video_output_routing_policy,
)
from fx3_firmware_lab.haita_bk4_feature_analyzer import is_forced_clean_room


PKG_ROOT = Path(__file__).resolve().parents[1]


class TestActiveAudioTcHdmiSdiRouting(unittest.TestCase):
    _active_report: Optional[AudioTcHdmiSdiRoutingReport] = None

    @classmethod
    def setUpClass(cls) -> None:
        cls._active_report = analyze_audio_tc_hdmi_sdi_routing()

    def test_01_active_mode_passes_with_o_rdonly_and_sha256(self) -> None:
        rep = self._active_report
        assert rep is not None
        self.assertTrue(rep.all_checks_passed, msg=f"Errors: {rep.errors}")
        self.assertEqual(rep.schema_version, PHASE_51_SCHEMA)
        self.assertTrue(rep.o_rdonly_enforced)
        self.assertEqual(len(rep.report_sha256), 64)
        self.assertEqual(len(rep.donor_file_sizes), 9)
        if not is_forced_clean_room() and rep.mode == "LOCAL_DONOR_VERIFIED":
            self.assertGreater(rep.donor_file_sizes["fx3_appfw"], 50_000_000)
            self.assertGreater(rep.donor_file_sizes["fx6_appfw"], 40_000_000)
            self.assertGreater(rep.donor_file_sizes["fx6_hotshoe"], 40_000)
            self.assertGreater(rep.donor_file_sizes["fx6_avbb_audio"], 50_000)
            self.assertGreater(rep.donor_file_sizes["fx6_avbb_panelevf"], 200_000)

    def test_02_active_report_json_serializable_without_raw_bytes(self) -> None:
        rep = self._active_report
        assert rep is not None
        payload = audio_tc_hdmi_sdi_routing_report_to_dict(rep)
        encoded = json.dumps(payload, sort_keys=True)
        self.assertNotIn("b'", encoded)
        decoded = json.loads(encoded)
        self.assertEqual(decoded["report_sha256"], rep.report_sha256)
        self.assertTrue(decoded["all_checks_passed"])

    def test_03_pillar_a_audio_markers_present_both_bodies(self) -> None:
        rep = self._active_report
        assert rep is not None
        pa = rep.pillar_a_audio
        self.assertTrue(pa.passed)
        self.assertEqual(pa.fx3_appfw_audio_markers, FX3_APPFW_AUDIO_MARKERS)
        self.assertEqual(pa.fx6_appfw_audio_markers, FX6_APPFW_AUDIO_MARKERS)
        self.assertEqual(pa.fx6_hotshoe_markers, FX6_HOTSHOE_MARKERS)
        self.assertEqual(len(pa.fx3_mpr_audio_markers), 3)
        self.assertEqual(len(pa.fx6_mpr_audio_markers), 5)
        self.assertEqual(len(pa.fx6_avbb_audio_markers), 4)

    def test_04_pillar_a_4ch_24bit_48khz_matrix_and_hot_detach_fallback(self) -> None:
        rep = self._active_report
        assert rep is not None
        pa = rep.pillar_a_audio
        self.assertEqual(pa.attached_4ch_24bit_48khz_bitrate_bps, 4_608_000)
        self.assertTrue(pa.p11_hot_detach_non_stalling_verified)
        by_ch = {c.channel_id: c for c in pa.channel_matrix}
        self.assertEqual(
            set(by_ch.keys()),
            {"CH1", "CH2", "CH3", "CH4", "BODY_3_5MM_MIC_JACK", "HEADPHONE_3_5MM_MONITOR_BUS"},
        )
        self.assertIn("XLR-H1", by_ch["CH1"].fx3_primary_source)
        self.assertIn("Internal Stereo", by_ch["CH3"].fx3_fallback_source)
        self.assertTrue(pa.attached_scenario.recording_continues)
        self.assertTrue(pa.detached_fallback_scenario.recording_continues)
        self.assertFalse(pa.detached_fallback_scenario.recording_stalled)
        self.assertEqual(pa.detached_fallback_scenario.active_audio_bus, "INTERNAL_STEREO")

    def test_05_pillar_b_timecode_markers_and_ext_lk_matrix(self) -> None:
        rep = self._active_report
        assert rep is not None
        pb = rep.pillar_b_timecode
        self.assertTrue(pb.passed)
        self.assertEqual(pb.shared_appfw_tc_markers, SHARED_APPFW_TIMECODE_MARKERS)
        self.assertEqual(len(pb.fx6_extra_tc_markers), 4)
        self.assertEqual(len(pb.fx3_cp_tc_markers), 2)
        self.assertEqual(len(pb.fx6_cp_tc_markers), 2)
        self.assertEqual(len(pb.fx6_cp_bnc_tc_markers), 2)
        self.assertTrue(pb.normal_shooting_ext_lk_eval.valid)
        self.assertTrue(pb.normal_shooting_ext_lk_eval.ext_lk_active)
        self.assertTrue(pb.hdmi_tc_atomos_trigger_eval.valid)
        self.assertTrue(pb.hdmi_tc_atomos_trigger_eval.hdmi_tc_out_on)
        self.assertFalse(pb.phase38_uart_boot_collision_blocked.valid)
        self.assertEqual(
            pb.phase38_uart_boot_collision_blocked.status,
            "BLOCKED_VMC_BNCM1_UART_BOOT_COLLISION",
        )

    def test_06_pillar_c_hdmi_raw_mlut_and_sdi_noop_containment(self) -> None:
        rep = self._active_report
        assert rep is not None
        pc = rep.pillar_c_video_output
        self.assertTrue(pc.passed)
        self.assertTrue(pc.zero_panics_and_zero_stalls_verified)
        self.assertEqual(pc.fx3_unexpected_sdi_markers, ())
        self.assertEqual(pc.fx6_mlut_sdi_markers, FX6_APPFW_MLUT_AND_SDI_MARKERS)
        self.assertEqual(pc.fx6_avbb_panelevf_markers, FX6_AVBB_PANELEVF_MARKERS)
        self.assertEqual(pc.raw_16bit_4264x2408_eval.hdmi_raw_resolution, FX3_HDMI_RAW_SENSOR_READOUT)
        self.assertTrue(pc.clean_4k_422_10bit_mlut_eval.hdmi_mlut_on)
        self.assertTrue(pc.sdi_sub_output_noop_eval.sdi_noop_contained)
        self.assertEqual(pc.sdi_sub_output_noop_eval.missing_transceiver_panics, 0)
        self.assertEqual(pc.sdi_sub_output_noop_eval.black_screen_stalls, 0)


class TestPillarAP11AudioHotDetachPolicy(unittest.TestCase):
    def test_07_xlr_h1_attached_4ch_24bit_48khz_metrics(self) -> None:
        res = evaluate_p11_hot_detach_audio_fallback(xlr_h1_attached=True)
        self.assertTrue(res.valid)
        self.assertEqual(res.status, "XLR_H1_4CH_ACTIVE")
        self.assertEqual(res.active_channels, AUDIO_CHANNELS_4CH)
        self.assertEqual(res.sample_rate_hz, AUDIO_SAMPLE_RATE_HZ)
        self.assertEqual(res.bit_depth, AUDIO_BIT_DEPTH_24)
        self.assertEqual(res.pcm_bitrate_bps, AUDIO_4CH_24BIT_BITRATE_BPS)
        self.assertEqual(res.p11_handle_queue_hex, "0x91db059b")
        self.assertEqual(res.hotshoe_tmo_safe_rc_hex, f"0x{LIBINFRAHOTSHOE_TMO_SAFE_RC:04x}")

    def test_08_hot_detach_falls_back_to_internal_stereo_or_body_jack(self) -> None:
        res_int = evaluate_p11_hot_detach_audio_fallback(xlr_h1_attached=False, body_35mm_mic_plugged=False)
        self.assertTrue(res_int.valid)
        self.assertEqual(res_int.active_audio_bus, "INTERNAL_STEREO")
        self.assertEqual(res_int.active_channels, 2)
        self.assertTrue(res_int.recording_continues)
        self.assertFalse(res_int.recording_stalled)

        res_jack = evaluate_p11_hot_detach_audio_fallback(xlr_h1_attached=False, body_35mm_mic_plugged=True)
        self.assertTrue(res_jack.valid)
        self.assertEqual(res_jack.active_audio_bus, "BODY_3_5MM_STEREO_JACK")
        self.assertEqual(res_jack.active_channels, 2)
        self.assertTrue(res_jack.recording_continues)

    def test_09_spoofed_p11_attached_ack_blocked(self) -> None:
        res = evaluate_p11_hot_detach_audio_fallback(
            xlr_h1_attached=True,
            p11_smart_handle_event_cmd=P11_SMART_HANDLE_ATTACHED_EVT,
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.status, "BLOCKED_AUDIO_FALLBACK_STALL_OR_COLLISION")
        self.assertTrue(any("0x88000001" in e for e in res.errors))

    def test_10_blocking_hotshoe_wait_and_bad_sample_rate_rejected(self) -> None:
        res_block = evaluate_p11_hot_detach_audio_fallback(
            xlr_h1_attached=False,
            simulate_blocking_wait=True,
            p11_smart_handle_event_cmd=P11_SMART_HANDLE_DETACHED_EVT,
        )
        self.assertFalse(res_block.valid)
        self.assertTrue(res_block.recording_stalled)
        self.assertFalse(res_block.recording_continues)

        res_rate = evaluate_p11_hot_detach_audio_fallback(sample_rate_hz=44_100)
        self.assertFalse(res_rate.valid)
        self.assertTrue(any("sample rate" in e for e in res_rate.errors))


class TestPillarBSmpte12mAndPhase38CrossCheck(unittest.TestCase):
    def test_11_smpte_12m_bcd_encoding_ndf_and_df(self) -> None:
        ndf = encode_smpte12m_bcd(1, 23, 45, 12, fps=23.976, drop_frame=False)
        self.assertEqual(ndf.hex(), "12452301")
        df = encode_smpte12m_bcd(10, 20, 30, 15, fps=29.97, drop_frame=True)
        self.assertEqual(df.hex(), "55302010")

    def test_12_smpte_12m_rejects_invalid_drop_frame_rates_and_dropped_frames(self) -> None:
        with self.assertRaises(ValueError):
            encode_smpte12m_bcd(0, 0, 0, 0, fps=24.0, drop_frame=True)
        with self.assertRaises(ValueError):
            encode_smpte12m_bcd(0, 1, 0, 0, fps=29.97, drop_frame=True)
        with self.assertRaises(ValueError):
            encode_smpte12m_bcd(0, 0, 0, 24, fps=24.0, drop_frame=False)

    def test_13_normal_shooting_ext_lk_and_hdmi_tc_on_supported(self) -> None:
        res = evaluate_smpte12m_tc_routing(
            target_body="ILME-FX3",
            fps=23.976,
            tc_make_mode="PRESET",
            tc_run_mode="FREE_RUN",
            ext_lk_requested=True,
            hdmi_tc_out_on=True,
            vmc_bncm1_attached=True,
            uart_boot_active=False,
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.status, "SMPTE_12M_EXT_LK_READY")
        self.assertTrue(res.ext_lk_active)
        self.assertTrue(res.hdmi_tc_out_on)
        self.assertTrue(res.phase38_uart_boot_guard_ok)

    def test_14_phase38_vmc_bncm1_disconnected_during_h0_uart_boot_enforced(self) -> None:
        # Attached during H0/Tier-3 uart_boot -> BLOCKED
        bad = evaluate_smpte12m_tc_routing(
            target_body="ILME-FX3",
            ext_lk_requested=True,
            vmc_bncm1_attached=True,
            uart_boot_active=True,
        )
        self.assertFalse(bad.valid)
        self.assertEqual(bad.status, "BLOCKED_VMC_BNCM1_UART_BOOT_COLLISION")
        self.assertFalse(bad.phase38_uart_boot_guard_ok)

        # Disconnected during H0/Tier-3 uart_boot without EXT-LK -> SAFE
        safe = evaluate_smpte12m_tc_routing(
            target_body="ILME-FX3",
            ext_lk_requested=False,
            vmc_bncm1_attached=False,
            uart_boot_active=True,
        )
        self.assertTrue(safe.valid)
        self.assertTrue(safe.phase38_uart_boot_guard_ok)

    def test_15_fx3_blocks_bnc_tc_out_and_wrong_id_resistor_and_rec_run_ext_lk(self) -> None:
        res_bnc = evaluate_smpte12m_tc_routing(
            target_body="ILME-FX3",
            bnc_tc_out_requested=True,
            ext_lk_requested=False,
            vmc_bncm1_attached=False,
        )
        self.assertFalse(res_bnc.valid)
        self.assertEqual(res_bnc.status, "BLOCKED_FX3_NO_BNC_TC_OUT")
        self.assertTrue(res_bnc.bnc_tc_out_blocked_on_fx3)

        res_res = evaluate_smpte12m_tc_routing(
            target_body="ILME-FX3",
            ext_lk_requested=True,
            vmc_bncm1_id_ohm=100_000,
        )
        self.assertFalse(res_res.valid)

        res_rec = evaluate_smpte12m_tc_routing(
            target_body="ILME-FX3",
            ext_lk_requested=True,
            tc_run_mode="REC_RUN",
        )
        self.assertFalse(res_rec.valid)


class TestPillarCHdmiRawMlutAndSdiContainment(unittest.TestCase):
    def test_16_hdmi_type_a_16bit_raw_and_mlut_constraint(self) -> None:
        ok = evaluate_video_output_routing_policy(
            hdmi_mode="16BIT_LINEAR_RAW",
            hdmi_raw_resolution=FX3_HDMI_RAW_SENSOR_READOUT,
            lcd_mlut_on=True,
            hdmi_mlut_on=False,
        )
        self.assertTrue(ok.valid)
        self.assertEqual(ok.status, "HDMI_TYPE_A_16BIT_LINEAR_RAW_READY")
        self.assertEqual(ok.missing_transceiver_panics, 0)
        self.assertEqual(ok.black_screen_stalls, 0)

        bad_lut = evaluate_video_output_routing_policy(
            hdmi_mode="16BIT_LINEAR_RAW",
            hdmi_mlut_on=True,
        )
        self.assertFalse(bad_lut.valid)
        self.assertTrue(any("16-bit Linear RAW" in e for e in bad_lut.errors))

    def test_17_clean_feed_4k_422_10bit_requires_info_display_off(self) -> None:
        ok = evaluate_video_output_routing_policy(
            hdmi_mode="4K_DCI_10BIT_422_CLEAN",
            hdmi_raw_resolution="4096x2160",
            clean_feed_info_off=True,
            lcd_mlut_on=True,
            hdmi_mlut_on=True,
        )
        self.assertTrue(ok.valid)
        self.assertEqual(ok.status, "HDMI_TYPE_A_4K_10BIT_422_CLEAN_MLUT_READY")

        bad = evaluate_video_output_routing_policy(
            hdmi_mode="4K_DCI_10BIT_422_CLEAN",
            clean_feed_info_off=False,
        )
        self.assertFalse(bad.valid)

    def test_18_sdi_sub_output_noop_containment_and_panic_guards(self) -> None:
        noop = evaluate_video_output_routing_policy(
            hdmi_mode="QFHD_10BIT_422_CLEAN",
            sdi_sub_output_requested=True,
            sdi_transceiver_present=False,
            fx3_sdi_hw_driver_detected=False,
        )
        self.assertTrue(noop.valid)
        self.assertEqual(noop.status, "SDI_SUB_OUTPUT_NOOP_CONTAINED_TO_HDMI")
        self.assertTrue(noop.sdi_noop_contained)
        self.assertEqual(noop.missing_transceiver_panics, 0)
        self.assertEqual(noop.black_screen_stalls, 0)

        panic = evaluate_video_output_routing_policy(
            hdmi_mode="QFHD_10BIT_422_CLEAN",
            fx3_sdi_hw_driver_detected=True,
        )
        self.assertFalse(panic.valid)
        self.assertEqual(panic.missing_transceiver_panics, 1)

        stall = evaluate_video_output_routing_policy(
            hdmi_mode="QFHD_10BIT_422_CLEAN",
            hdmi_output_enabled=False,
        )
        self.assertFalse(stall.valid)
        self.assertEqual(stall.black_screen_stalls, 1)


class TestCleanRoomFaultInjectionAndCli(unittest.TestCase):
    def test_19_clean_room_forced_returns_deterministic_sha256(self) -> None:
        r1 = analyze_audio_tc_hdmi_sdi_routing(clean_room=True)
        r2 = analyze_audio_tc_hdmi_sdi_routing(env={"FX3_FX6_FORCE_CLEAN_ROOM": "1"})
        self.assertTrue(r1.all_checks_passed)
        self.assertEqual(r1.mode, "CLEAN_ROOM_SYNTHETIC_VERIFIED")
        self.assertEqual(r2.mode, "CLEAN_ROOM_SYNTHETIC_VERIFIED")
        self.assertEqual(r1.report_sha256, r2.report_sha256)

    def test_20_env_force_clean_room_never_opens_donors(self) -> None:
        with patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            rep = analyze_audio_tc_hdmi_sdi_routing()
            self.assertEqual(rep.mode, "CLEAN_ROOM_SYNTHETIC_VERIFIED")
            self.assertLess(rep.donor_file_sizes["fx3_appfw"], 8192)

    def test_21_fault_injection_drop_fx3_4ch_audio(self) -> None:
        bad = build_clean_room_audio_tc_hdmi_fixtures(drop_fx3_4ch_audio=True)
        rep = analyze_audio_tc_hdmi_sdi_routing(synthetic_overrides=bad)
        self.assertFalse(rep.all_checks_passed)
        self.assertFalse(rep.pillar_a_audio.passed)

    def test_22_fault_injection_drop_fx6_hotshoe_tmo(self) -> None:
        bad = build_clean_room_audio_tc_hdmi_fixtures(drop_fx6_hotshoe_tmo=True)
        rep = analyze_audio_tc_hdmi_sdi_routing(synthetic_overrides=bad)
        self.assertFalse(rep.all_checks_passed)
        self.assertFalse(rep.pillar_a_audio.passed)

    def test_23_fault_injection_drop_fx3_ext_tc(self) -> None:
        bad = build_clean_room_audio_tc_hdmi_fixtures(drop_fx3_ext_tc=True)
        rep = analyze_audio_tc_hdmi_sdi_routing(synthetic_overrides=bad)
        self.assertFalse(rep.all_checks_passed)
        self.assertFalse(rep.pillar_b_timecode.passed)

    def test_24_fault_injection_drop_fx6_mlut_sdi_and_inject_sdi_hw_in_fx3(self) -> None:
        bad_mlut = build_clean_room_audio_tc_hdmi_fixtures(drop_fx6_mlut_sdi=True)
        rep_mlut = analyze_audio_tc_hdmi_sdi_routing(synthetic_overrides=bad_mlut)
        self.assertFalse(rep_mlut.all_checks_passed)
        self.assertFalse(rep_mlut.pillar_c_video_output.passed)

        bad_sdi = build_clean_room_audio_tc_hdmi_fixtures(inject_sdi_hw_in_fx3=True)
        rep_sdi = analyze_audio_tc_hdmi_sdi_routing(synthetic_overrides=bad_sdi)
        self.assertFalse(rep_sdi.all_checks_passed)
        self.assertFalse(rep_sdi.pillar_c_video_output.passed)
        self.assertGreater(len(rep_sdi.pillar_c_video_output.fx3_unexpected_sdi_markers), 0)

    def test_25_run_audit_all_includes_all_9_auditors(self) -> None:
        all_res = run_audit_all(clean_room=True)
        self.assertTrue(all_res["all_checks_passed"])
        expected_keys = {
            "ufu_container_audit",
            "haita_bk4_feature_audit",
            "uxc_ldec_asset_audit",
            "uxc_multilang_and_font_audit",
            "sensor_codec_compatibility_audit",
            "cube_lut_and_rtmd_audit",
            "wbi_hibdrv_and_elf_abi_audit",
            "global_xdb_and_menu_tree_audit",
            "audio_tc_hdmi_sdi_routing_audit",
        }
        self.assertTrue(expected_keys.issubset(set(all_res.keys())))
        self.assertTrue(all_res["audio_tc_hdmi_sdi_routing_audit"]["all_checks_passed"])

    def test_26_cli_audit_audio_tc_hdmi_in_process(self) -> None:
        buf = StringIO()
        with redirect_stdout(buf):
            rc = cli_main(["audit-audio-tc-hdmi", "--clean-room"])
        self.assertEqual(rc, 0)
        data = json.loads(buf.getvalue())
        self.assertTrue(data["all_checks_passed"])
        self.assertEqual(data["mode"], "CLEAN_ROOM_SYNTHETIC_VERIFIED")
        self.assertEqual(data["schema_version"], PHASE_51_SCHEMA)

    def test_27_cli_audit_audio_tc_hdmi_subprocess_deterministic(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["FX3_FX6_FORCE_CLEAN_ROOM"] = "1"
        env["PYTHONPATH"] = str(PKG_ROOT)
        p1 = subprocess.run(
            [sys.executable, "-B", "-m", "fx3_firmware_lab", "audit-audio-tc-hdmi", "--clean-room"],
            capture_output=True,
            text=True,
            env=env,
            check=True,
        )
        p2 = subprocess.run(
            [sys.executable, "-B", "-m", "fx3_firmware_lab", "audit-audio-tc-hdmi", "--clean-room"],
            capture_output=True,
            text=True,
            env=env,
            check=True,
        )
        self.assertEqual(p1.stdout, p2.stdout)
        parsed = json.loads(p1.stdout)
        self.assertTrue(parsed["all_checks_passed"])
        self.assertNotIn("b'", p1.stdout)

    def test_28_strict_o_rdonly_and_zero_secret_keys_in_module(self) -> None:
        src_path = PKG_ROOT / "fx3_firmware_lab" / "audio_tc_hdmi_sdi_routing_auditor.py"
        src = src_path.read_text(encoding="utf-8")
        self.assertIn("os.O_RDONLY", src)
        for forbidden in ("O_WRONLY", "O_RDWR", '"wb"', "'wb'", "subprocess.", "CXD90057_k8", "BEGIN RSA PRIVATE KEY"):
            self.assertNotIn(forbidden, src)


if __name__ == "__main__":
    unittest.main()
