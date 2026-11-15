"""Phase 118 Dual-Mode Unit Tests: USB-C UVC 1.5 / UAC 2.0 Streaming,
Wired P12-Safe SRT / RTMPS Network Streaming, & Sony Camera Remote SDK (CRSDK)
PTP / PTP-IP Vendor Property Translator & Destructive Flash-Opcode Firewall.
"""

from __future__ import annotations

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
from fx3_firmware_lab.emount_af_breathing_and_ibis_auditor import _extract_uxc_labels
from fx3_firmware_lab.global_xdb_and_menu_tree_auditor import parse_global_xdb_buffer
from fx3_firmware_lab.usb_uvc_uac_srt_and_crsdk_ptp_auditor import (
    CRSDK_PROPERTY_PTP_MAP,
    FORBIDDEN_CRSDK_FW_UPDATE_COMMANDS,
    FORBIDDEN_FIRMWARE_PAYLOAD_PATTERNS,
    FORBIDDEN_PTP_FLASH_OPCODES,
    FORBIDDEN_RF_TRANSPORTS,
    FX3_APPFW_PHASE118_MARKERS,
    FX3_LIBMPR_PHASE118_MARKERS,
    FX3_NS39_PHASE118_LABELS,
    FX3_NS3_PHASE118_LABELS,
    FX6_APPFW_PHASE118_MARKERS,
    FX6_LIBINFRA_PTP_PHASE118_MARKERS,
    FX6_LIBMPR_PHASE118_MARKERS,
    FX6_LIBNET_ETHER_PHASE118_MARKERS,
    FX6_LIBVERIC_LIVE_PHASE118_MARKERS,
    FX6_NS1_PHASE118_LABELS,
    FX6_NS2_PHASE118_LABELS,
    PHASE_118_SCHEMA,
    PHASE_118_VERSION,
    SONY_FX3_STREAMING_BITRATE_ENVELOPES,
    SONY_SAFE_PTP_OPCODES,
    UAC_CHANNELS,
    UAC_SAMPLE_RATE_HZ,
    UAC_VERSION_20,
    USB2_HIGHSPEED_480MBPS_USABLE_MBPS,
    USB3_SUPERSPEED_5GBPS_USABLE_MBPS,
    USB_VID_SONY,
    UVC_DESCRIPTOR_BUNDLE_BYTES,
    UVC_VERSION_15,
    analyze_usb_uvc_uac_srt_and_crsdk_ptp,
    build_clean_room_uvc_srt_crsdk_fixtures,
    build_uvc15_uac20_descriptor_bundle,
    decode_uvc15_uac20_descriptor_bundle,
    evaluate_phase118_write_guard,
    evaluate_ptp_flash_opcode_firewall,
    evaluate_uvc_uac_bandwidth_and_compat,
    evaluate_wired_srt_rtmps_stream,
    translate_crsdk_property_to_ptp,
    usb_uvc_uac_srt_and_crsdk_ptp_report_to_dict,
)


_BYTES_REPR_RE = re.compile(r"(?<![0-9A-Za-z_/.-])b['\"]")
_AUDITOR_PATH = (
    Path(__file__).resolve().parent.parent
    / "fx3_firmware_lab"
    / "usb_uvc_uac_srt_and_crsdk_ptp_auditor.py"
)


class TestUsbUvcUacSrtAndCrsdkPtp(unittest.TestCase):
    """Comprehensive dual-mode tests (>= 42) for the 23rd unified auditor."""

    # ---- Mode, Runtime, Determinism & Structural Hygiene ----

    def test_01_clean_room_report_all_pillars_and_warm_runtime(self) -> None:
        t0 = time.perf_counter()
        rep = analyze_usb_uvc_uac_srt_and_crsdk_ptp(clean_room=True)
        dt_cold = time.perf_counter() - t0
        t1 = time.perf_counter()
        rep_warm = analyze_usb_uvc_uac_srt_and_crsdk_ptp(clean_room=True)
        dt_warm = time.perf_counter() - t1

        self.assertTrue(rep.all_checks_passed, rep.errors)
        self.assertEqual(rep.mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(rep.schema_version, PHASE_118_SCHEMA)
        self.assertEqual(rep.phase_version, PHASE_118_VERSION)
        self.assertTrue(rep.pillar_1_uvc_uac_streaming.passed)
        self.assertTrue(rep.pillar_2_wired_srt_rtmps_p12.passed)
        self.assertTrue(rep.pillar_3_crsdk_ptp_firewall.passed)
        self.assertTrue(rep.pillar_4_zero_mutation_emmc_preservation.passed)
        self.assertEqual(rep.report_sha256, rep_warm.report_sha256)
        self.assertEqual(len(rep.report_sha256), 64)
        self.assertLess(dt_cold, 0.08)
        self.assertLess(dt_warm, 0.02)

    def test_02_auto_mode_or_local_donor_runtime_and_sizes(self) -> None:
        t0 = time.perf_counter()
        rep = analyze_usb_uvc_uac_srt_and_crsdk_ptp()
        dt = time.perf_counter() - t0
        self.assertTrue(rep.all_checks_passed, rep.errors)
        self.assertIn(rep.mode, ("LOCAL_DONOR_VERIFIED", "CLEAN_ROOM_SYNTHETIC"))
        self.assertLess(dt, 0.35)
        if rep.mode == "LOCAL_DONOR_VERIFIED":
            self.assertGreater(rep.donor_file_sizes.get("fx3_appfw", 0), 70_000_000)
            self.assertGreater(rep.donor_file_sizes.get("fx6_appfw", 0), 45_000_000)
            self.assertGreater(rep.donor_file_sizes.get("fx3_libmpr", 0), 3_000_000)
            self.assertGreater(rep.donor_file_sizes.get("fx6_libmpr", 0), 25_000_000)
            self.assertGreater(rep.donor_file_sizes.get("fx6_libinfra_ptp", 0), 100_000)
            self.assertGreater(rep.donor_file_sizes.get("fx6_libnet_ether", 0), 100_000)
            self.assertGreater(rep.donor_file_sizes.get("fx6_libveric_live", 0), 100_000)

    def test_03_forced_clean_room_env_flag_respected(self) -> None:
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}, clear=False):
            rep = analyze_usb_uvc_uac_srt_and_crsdk_ptp()
        self.assertTrue(rep.all_checks_passed, rep.errors)
        self.assertEqual(rep.mode, "CLEAN_ROOM_SYNTHETIC")

    def test_04_missing_donor_falls_back_to_clean_room(self) -> None:
        with mock.patch(
            "fx3_firmware_lab.usb_uvc_uac_srt_and_crsdk_ptp_auditor.resolve_donor_file",
            return_value=None,
        ):
            rep = analyze_usb_uvc_uac_srt_and_crsdk_ptp(clean_room=False)
        self.assertTrue(rep.all_checks_passed, rep.errors)
        self.assertEqual(rep.mode, "CLEAN_ROOM_SYNTHETIC")

    def test_05_json_serialization_has_no_bytes_repr(self) -> None:
        rep = analyze_usb_uvc_uac_srt_and_crsdk_ptp(clean_room=True)
        payload = usb_uvc_uac_srt_and_crsdk_ptp_report_to_dict(rep)
        json_str = json.dumps(payload, sort_keys=True)
        self.assertIsNone(_BYTES_REPR_RE.search(json_str), "Unexpected Python bytes repr in JSON")
        self.assertIn(PHASE_118_SCHEMA, json_str)

    def test_06_auditor_source_strictly_uses_os_o_rdonly_and_mmap_access_read(self) -> None:
        src = _AUDITOR_PATH.read_text(encoding="utf-8")
        self.assertIn("os.O_RDONLY", src)
        self.assertIn("mmap.ACCESS_READ", src)
        for forbidden in ("os.O_WRONLY", "os.O_RDWR", "os.O_CREAT", "mmap.ACCESS_WRITE", ".write_bytes(", ".write_text("):
            self.assertNotIn(forbidden, src)

    def test_07_package_exports_and_all_include_phase118_symbols(self) -> None:
        expected_symbols = (
            "PHASE_118_SCHEMA",
            "PHASE_118_VERSION",
            "UVC_STREAM_PROFILES",
            "SONY_FX3_STREAMING_BITRATE_ENVELOPES",
            "SONY_SAFE_PTP_OPCODES",
            "FORBIDDEN_PTP_FLASH_OPCODES",
            "FORBIDDEN_CRSDK_FW_UPDATE_COMMANDS",
            "CRSDK_PROPERTY_PTP_MAP",
            "UsbUvcUacSrtAndCrsdkPtpReport",
            "build_uvc15_uac20_descriptor_bundle",
            "decode_uvc15_uac20_descriptor_bundle",
            "evaluate_uvc_uac_bandwidth_and_compat",
            "evaluate_wired_srt_rtmps_stream",
            "translate_crsdk_property_to_ptp",
            "evaluate_ptp_flash_opcode_firewall",
            "evaluate_phase118_write_guard",
            "analyze_usb_uvc_uac_srt_and_crsdk_ptp",
            "usb_uvc_uac_srt_and_crsdk_ptp_report_to_dict",
        )
        for sym in expected_symbols:
            self.assertTrue(hasattr(lab, sym), f"Missing package export: {sym}")
            self.assertIn(sym, lab.__all__, f"Missing __all__ entry: {sym}")

    def test_08_clean_room_fixtures_parse_as_elf64_xdb_and_uxc(self) -> None:
        fx = build_clean_room_uvc_srt_crsdk_fixtures()
        for k in (
            "fx3_appfw",
            "fx6_appfw",
            "fx3_libmpr",
            "fx6_libmpr",
            "fx6_libinfra_ptp",
            "fx6_libnet_ether",
            "fx6_libveric_live",
        ):
            self.assertTrue(fx[k].startswith(b"\x7fELF\x02\x01\x01"))
        xdb3 = parse_global_xdb_buffer(fx["fx3_global_xdb"])
        xdb6 = parse_global_xdb_buffer(fx["fx6_global_xdb"])
        self.assertGreater(xdb3.top_slot_count, 0)
        self.assertGreater(xdb6.active_slot_count, 0)

        lbl3, err3 = _extract_uxc_labels(fx["fx3_str_en"], FX3_NS39_PHASE118_LABELS)
        self.assertEqual(err3, ())
        self.assertEqual(lbl3["0x0004e244"], FX3_NS39_PHASE118_LABELS[0x0004E244])

    # ---- Pillar 1: USB-C UVC 1.5 / UAC 2.0 & Bandwidth ----

    def test_09_uvc15_uac20_descriptor_bundle_roundtrip_and_crc32(self) -> None:
        for depth in (16, 24):
            pkt = build_uvc15_uac20_descriptor_bundle(
                width=3840,
                height=2160,
                fps_x100=2997,
                pixel_format="MJPEG",
                uac_bit_depth=depth,
            )
            self.assertEqual(len(pkt), UVC_DESCRIPTOR_BUNDLE_BYTES)
            dec = decode_uvc15_uac20_descriptor_bundle(pkt)
            self.assertTrue(dec.valid, dec.errors)
            self.assertTrue(dec.crc32_valid)
            self.assertEqual(dec.vendor_id, USB_VID_SONY)
            self.assertEqual(dec.uvc_bcd, UVC_VERSION_15)
            self.assertEqual(dec.uac_bcd, UAC_VERSION_20)
            self.assertEqual(dec.width, 3840)
            self.assertEqual(dec.height, 2160)
            self.assertEqual(dec.fps_x100, 2997)
            self.assertEqual(dec.pixel_format, "MJPEG")
            self.assertEqual(dec.uac_sample_rate_hz, UAC_SAMPLE_RATE_HZ)
            self.assertEqual(dec.uac_channels, UAC_CHANNELS)
            self.assertEqual(dec.uac_bit_depth, depth)

    def test_10_uvc15_uac20_descriptor_corrupt_crc_and_bad_size_rejected(self) -> None:
        pkt = bytearray(build_uvc15_uac20_descriptor_bundle())
        pkt[-1] ^= 0xFF
        dec_bad_crc = decode_uvc15_uac20_descriptor_bundle(bytes(pkt))
        self.assertFalse(dec_bad_crc.valid)
        self.assertFalse(dec_bad_crc.crc32_valid)

        dec_short = decode_uvc15_uac20_descriptor_bundle(b"SHORT")
        self.assertFalse(dec_short.valid)
        self.assertEqual(dec_short.pixel_format, "INVALID")

        with self.assertRaises(ValueError):
            build_uvc15_uac20_descriptor_bundle(uac_sample_rate_hz=44100)
        with self.assertRaises(ValueError):
            build_uvc15_uac20_descriptor_bundle(uac_bit_depth=32)

    def test_11_uvc_4k30_mjpeg_usb3_bridge_and_fx30_sim_allowed(self) -> None:
        for mode in ("HDMI_TO_UVC_BRIDGE", "FX30_A7S3_UVC_DESCRIPTOR_SIM"):
            res = evaluate_uvc_uac_bandwidth_and_compat(
                profile_id="4K30P_MJPEG",
                usb_link_speed="USB3_SUPERSPEED_5G",
                stage_b_mode=mode,
            )
            self.assertTrue(res.valid, res.errors)
            self.assertEqual(res.status, "UVC15_UAC20_STAGE_B_COMPAT_VERIFIED")
            self.assertTrue(res.fx3_native_uvc_absent_contained)
            self.assertAlmostEqual(res.total_payload_mbps, 151.536, places=3)
            self.assertEqual(res.link_usable_ceiling_mbps, USB3_SUPERSPEED_5GBPS_USABLE_MBPS)
            self.assertGreater(res.headroom_mbps, 3000.0)

    def test_12_uvc_1080p60_mjpeg_fits_usb2_high_speed(self) -> None:
        res = evaluate_uvc_uac_bandwidth_and_compat(
            profile_id="1080P60P_MJPEG",
            usb_link_speed="USB2_HIGHSPEED_480M",
            stage_b_mode="HDMI_TO_UVC_BRIDGE",
        )
        self.assertTrue(res.valid, res.errors)
        self.assertAlmostEqual(res.total_payload_mbps, 76.536, places=3)
        self.assertEqual(res.link_usable_ceiling_mbps, USB2_HIGHSPEED_480MBPS_USABLE_MBPS)

    def test_13_uvc_1080p60_yuy2_fits_usb3_but_blocked_on_usb2_high_speed(self) -> None:
        ok_ss = evaluate_uvc_uac_bandwidth_and_compat(
            profile_id="1080P60P_YUY2",
            usb_link_speed="USB3_SUPERSPEED_5G",
            stage_b_mode="HDMI_TO_UVC_BRIDGE",
            uac_bit_depth=24,
        )
        self.assertTrue(ok_ss.valid, ok_ss.errors)
        self.assertAlmostEqual(ok_ss.audio_mbps, 2.304, places=3)
        self.assertAlmostEqual(ok_ss.total_payload_mbps, 1992.96, places=2)

        blk_hs = evaluate_uvc_uac_bandwidth_and_compat(
            profile_id="1080P60P_YUY2",
            usb_link_speed="USB2_HIGHSPEED_480M",
            stage_b_mode="HDMI_TO_UVC_BRIDGE",
        )
        self.assertFalse(blk_hs.valid)
        self.assertEqual(blk_hs.status, "BLOCKED_USB2_HS_480M_BANDWIDTH_EXCEEDED")
        self.assertLess(blk_hs.headroom_mbps, 0.0)

    def test_14_uvc_4k30_yuy2_exceeds_usb3_superspeed_ceiling(self) -> None:
        blk = evaluate_uvc_uac_bandwidth_and_compat(
            profile_id="4K30P_YUY2",
            usb_link_speed="USB3_SUPERSPEED_5G",
            stage_b_mode="HDMI_TO_UVC_BRIDGE",
        )
        self.assertFalse(blk.valid)
        self.assertEqual(blk.status, "BLOCKED_USB3_SS_5G_BANDWIDTH_EXCEEDED")
        self.assertGreater(blk.total_payload_mbps, USB3_SUPERSPEED_5GBPS_USABLE_MBPS)

    def test_15_uvc_4k30_nv12_fits_usb3_superspeed(self) -> None:
        ok = evaluate_uvc_uac_bandwidth_and_compat(
            profile_id="4K30P_NV12_YUV420",
            usb_link_speed="USB3_SUPERSPEED_5G",
            stage_b_mode="FX30_A7S3_UVC_DESCRIPTOR_SIM",
        )
        self.assertTrue(ok.valid, ok.errors)
        self.assertLess(ok.total_payload_mbps, USB3_SUPERSPEED_5GBPS_USABLE_MBPS)

    def test_16_uvc_direct_fx3_native_gadget_blocked(self) -> None:
        blk = evaluate_uvc_uac_bandwidth_and_compat(
            profile_id="4K30P_MJPEG",
            usb_link_speed="USB3_SUPERSPEED_5G",
            stage_b_mode="DIRECT_FX3_NATIVE_UVC_GADGET",
        )
        self.assertFalse(blk.valid)
        self.assertFalse(blk.fx3_native_uvc_absent_contained)
        self.assertEqual(blk.status, "BLOCKED_FX3_NATIVE_UVC_GADGET_ABSENT")

    def test_17_uvc_sq_motion_and_hdmi_raw16_exclusions_blocked(self) -> None:
        blk_sq = evaluate_uvc_uac_bandwidth_and_compat(sq_motion_active=True)
        self.assertFalse(blk_sq.valid)
        self.assertEqual(blk_sq.status, "BLOCKED_UVC_SQ_MOTION_EXCLUSION")

        blk_raw = evaluate_uvc_uac_bandwidth_and_compat(hdmi_raw_active=True)
        self.assertFalse(blk_raw.valid)
        self.assertEqual(blk_raw.status, "BLOCKED_UVC_HDMI_RAW16_EXCLUSION")

        blk_crc = evaluate_uvc_uac_bandwidth_and_compat(corrupt_descriptor_crc=True)
        self.assertFalse(blk_crc.valid)
        self.assertFalse(blk_crc.descriptor_decoded.crc32_valid)

    def test_18_uvc_invalid_enum_inputs_raise_value_error(self) -> None:
        with self.assertRaises(ValueError):
            evaluate_uvc_uac_bandwidth_and_compat(profile_id="8K30P_RAW")
        with self.assertRaises(ValueError):
            evaluate_uvc_uac_bandwidth_and_compat(usb_link_speed="USB1_FULLSPEED")
        with self.assertRaises(ValueError):
            evaluate_uvc_uac_bandwidth_and_compat(stage_b_mode="UNKNOWN_MODE")
        with self.assertRaises(ValueError):
            evaluate_uvc_uac_bandwidth_and_compat(uac_bit_depth=8)

    # ---- Pillar 2: Wired USB-LAN SRT & RTMPS + P12 RF-Off ----

    def test_19_wired_srt_caller_aes256_4k30_cdc_ncm_p12_verified(self) -> None:
        res = evaluate_wired_srt_rtmps_stream(
            protocol="SRT_CALLER",
            transport_driver="CDC_NCM_RTL8153",
            p12_airplane_rf_off=True,
            resolution_key="4K_2997P",
            bitrate_mbps=34.0,
            internal_4k_rec_requested=True,
            srt_pbkeylen_bytes=32,
            srt_arq_latency_ms=120,
            rtt_ms=25,
        )
        self.assertTrue(res.valid, res.errors)
        self.assertEqual(res.status, "WIRED_SRT_CALLER_P12_ISOLATED_VERIFIED")
        self.assertEqual(res.wf12_00342260_risk, 0)
        self.assertEqual(res.hci_rf_tx_packets, 0)

    def test_20_wired_srt_listener_aes128_rndis_and_ax88179_verified(self) -> None:
        for drv in ("USB_RNDIS_WIRED", "CDC_NCM_AX88179"):
            res = evaluate_wired_srt_rtmps_stream(
                protocol="SRT_LISTENER",
                transport_driver=drv,
                resolution_key="1080P_5994P",
                bitrate_mbps=20.0,
                internal_4k_rec_requested=True,
                srt_pbkeylen_bytes=16,
                srt_arq_latency_ms=180,
                rtt_ms=30,
            )
            self.assertTrue(res.valid, res.errors)
            self.assertEqual(res.wf12_00342260_risk, 0)

    def test_21_wired_rtmps_tls13_and_tls12_ca_verified_allowed_and_plain_blocked(self) -> None:
        for tls_ver in ("TLS_1_3", "TLS_1_2"):
            ok = evaluate_wired_srt_rtmps_stream(
                protocol="RTMPS_TLS13",
                transport_driver="CDC_NCM_AX88179",
                resolution_key="1080P_5994P",
                bitrate_mbps=15.0,
                tls_version=tls_ver,
                root_ca_verified=True,
            )
            self.assertTrue(ok.valid, ok.errors)

        blk_weak = evaluate_wired_srt_rtmps_stream(
            protocol="RTMPS_TLS13",
            transport_driver="CDC_NCM_RTL8153",
            resolution_key="1080P_5994P",
            bitrate_mbps=15.0,
            tls_version="TLS_1_0",
        )
        self.assertFalse(blk_weak.valid)
        self.assertEqual(blk_weak.status, "BLOCKED_RTMPS_WEAK_TLS")

        blk_ca = evaluate_wired_srt_rtmps_stream(
            protocol="RTMPS_TLS13",
            transport_driver="CDC_NCM_RTL8153",
            resolution_key="1080P_5994P",
            bitrate_mbps=15.0,
            root_ca_verified=False,
        )
        self.assertFalse(blk_ca.valid)
        self.assertEqual(blk_ca.status, "BLOCKED_RTMPS_ROOT_CERT_UNVERIFIED")

        blk_plain = evaluate_wired_srt_rtmps_stream(
            protocol="RTMP_PLAIN",
            transport_driver="CDC_NCM_RTL8153",
            resolution_key="1080P_5994P",
            bitrate_mbps=10.0,
            require_encryption=True,
        )
        self.assertFalse(blk_plain.valid)
        self.assertEqual(blk_plain.status, "BLOCKED_PLAINTEXT_RTMP_WHEN_TLS_REQUIRED")

    def test_22_p12_rf_off_firewall_blocks_wifi_p2p_bt_pan_and_cellular(self) -> None:
        for rf_drv in FORBIDDEN_RF_TRANSPORTS:
            blk = evaluate_wired_srt_rtmps_stream(
                protocol="SRT_CALLER",
                transport_driver=rf_drv,
                p12_airplane_rf_off=True,
            )
            self.assertFalse(blk.valid)
            self.assertEqual(blk.wf12_00342260_risk, 1)
            self.assertEqual(blk.status, "BLOCKED_P12_RF_OFF_VIOLATION_00342260")
            if rf_drv == "BT_PAN":
                self.assertEqual(blk.hci_rf_tx_packets, 1)
            else:
                self.assertEqual(blk.hci_rf_tx_packets, 0)

    def test_23_srt_pbkeylen_passphrase_length_and_arq_bounds(self) -> None:
        blk_key = evaluate_wired_srt_rtmps_stream(srt_pbkeylen_bytes=24)
        self.assertFalse(blk_key.valid)
        self.assertEqual(blk_key.status, "BLOCKED_SRT_INVALID_PBKEYLEN")

        blk_short = evaluate_wired_srt_rtmps_stream(srt_passphrase="too_short")
        self.assertFalse(blk_short.valid)
        self.assertEqual(blk_short.status, "BLOCKED_SRT_PASSPHRASE_LENGTH")

        blk_long = evaluate_wired_srt_rtmps_stream(srt_passphrase="x" * 80)
        self.assertFalse(blk_long.valid)
        self.assertEqual(blk_long.status, "BLOCKED_SRT_PASSPHRASE_LENGTH")

        blk_arq_low = evaluate_wired_srt_rtmps_stream(srt_arq_latency_ms=10, rtt_ms=2)
        self.assertFalse(blk_arq_low.valid)
        self.assertEqual(blk_arq_low.status, "BLOCKED_SRT_ARQ_LATENCY_OUT_OF_RANGE")

        blk_arq_hi = evaluate_wired_srt_rtmps_stream(srt_arq_latency_ms=1200)
        self.assertFalse(blk_arq_hi.valid)
        self.assertEqual(blk_arq_hi.status, "BLOCKED_SRT_ARQ_LATENCY_OUT_OF_RANGE")

        blk_rtt = evaluate_wired_srt_rtmps_stream(srt_arq_latency_ms=60, rtt_ms=40)
        self.assertFalse(blk_rtt.valid)
        self.assertEqual(blk_rtt.status, "BLOCKED_SRT_ARQ_RTT_MARGIN")

    def test_24_sony_4k5994_streaming_blocks_internal_4k_rec_and_bitrate_bounds(self) -> None:
        blk_rec = evaluate_wired_srt_rtmps_stream(
            resolution_key="4K_5994P",
            bitrate_mbps=38.0,
            internal_4k_rec_requested=True,
        )
        self.assertFalse(blk_rec.valid)
        self.assertEqual(blk_rec.status, "BLOCKED_4K5994_INTERNAL_4K_REC_EXCLUSION")

        ok_no_rec = evaluate_wired_srt_rtmps_stream(
            resolution_key="4K_5994P",
            bitrate_mbps=38.0,
            internal_4k_rec_requested=False,
        )
        self.assertTrue(ok_no_rec.valid, ok_no_rec.errors)

        blk_bw = evaluate_wired_srt_rtmps_stream(
            resolution_key="720P_5994P",
            bitrate_mbps=25.0,
            internal_4k_rec_requested=False,
        )
        self.assertFalse(blk_bw.valid)
        self.assertEqual(blk_bw.status, "BLOCKED_BITRATE_OUT_OF_ENVELOPE")
        self.assertIn("4K_5994P", SONY_FX3_STREAMING_BITRATE_ENVELOPES)

        with self.assertRaises(ValueError):
            evaluate_wired_srt_rtmps_stream(protocol="NDI_HX")
        with self.assertRaises(ValueError):
            evaluate_wired_srt_rtmps_stream(resolution_key="8K_24P")

    # ---- Pillar 3: CRSDK PTP / PTP-IP Translator & Flash-Opcode Firewall ----

    def test_25_crsdk_ptp_translation_all_safe_properties_over_usb_and_ptpip(self) -> None:
        samples = (
            ("CINE_EI_LOG_MODE", "CINE_EI", "0xD243", "0x02CF1443", "USB_PTP"),
            ("BASE_ISO", 800, "0xD244", "0x02CF1444", "USB_PTP"),
            ("BASE_ISO", 12800, "0xD244", "0x02CF1444", "WIRED_PTPIP_15740"),
            ("EXPOSURE_INDEX", 3200, "0xD245", "0x02CF1445", "WIRED_PTPIP_15740"),
            ("USER_3D_LUT", "USER2", "0xD253", "0x02CF1453", "USB_PTP"),
            ("SHUTTER_ANGLE_X10", 1728, "0xD20D", "0x02CF1704", "USB_PTP"),
            ("IRIS_FNUMBER_X100", 280, "0x5007", "0x02CF0100", "WIRED_PTPIP_15740"),
            ("REC_CONTROL", "REC_START", "0xD215", "0x02CF0010", "USB_PTP"),
        )
        for key, val, exp_ptp, exp_bk4, tr in samples:
            tr_res = translate_crsdk_property_to_ptp(
                target_body="ILME-FX3",
                property_key=key,
                value=val,
                transport=tr,
                bulk_read_bytes=1024,
            )
            self.assertTrue(tr_res.valid, tr_res.errors)
            self.assertEqual(tr_res.ptp_prop_code_hex, exp_ptp)
            self.assertEqual(tr_res.bk4_prop_id_hex, exp_bk4)
            self.assertFalse(tr_res.p4_nd_clamped_clear)

    def test_26_crsdk_p4_variable_nd_clamped_clear_on_fx3_vs_accepted_on_fx6(self) -> None:
        fx3_nd9 = translate_crsdk_property_to_ptp(
            target_body="ILME-FX3",
            property_key="ND_FILTER_OD_X10",
            value=9,
            transport="USB_PTP",
        )
        self.assertTrue(fx3_nd9.valid)
        self.assertTrue(fx3_nd9.p4_nd_clamped_clear)
        self.assertEqual(fx3_nd9.effective_value, "0_CLEAR_P4_CLAMP")
        self.assertEqual(fx3_nd9.status, "P4_ABSENT_ND_CLAMPED_CLEAR")

        fx3_nd0 = translate_crsdk_property_to_ptp(
            target_body="ILME-FX3",
            property_key="ND_FILTER_OD_X10",
            value=0,
            transport="USB_PTP",
        )
        self.assertTrue(fx3_nd0.valid)
        self.assertFalse(fx3_nd0.p4_nd_clamped_clear)
        self.assertEqual(fx3_nd0.effective_value, "0_CLEAR")

        fx6_nd9 = translate_crsdk_property_to_ptp(
            target_body="ILME-FX6",
            property_key="ND_FILTER_OD_X10",
            value=9,
            transport="WIRED_PTPIP_15740",
        )
        self.assertTrue(fx6_nd9.valid)
        self.assertFalse(fx6_nd9.p4_nd_clamped_clear)
        self.assertEqual(fx6_nd9.status, "CRSDK_PTP_PROPERTY_TRANSLATED")

    def test_27_usb_ptp_0x9209_bulk_512b_alignment_enforced(self) -> None:
        for sz in (512, 1024, 1536):
            ok = translate_crsdk_property_to_ptp(
                property_key="SHUTTER_ANGLE_X10",
                value=1800,
                transport="USB_PTP",
                bulk_read_bytes=sz,
            )
            self.assertTrue(ok.valid)
            self.assertTrue(ok.bulk_512b_aligned)

        for bad_sz in (0, 12, 513):
            blk = translate_crsdk_property_to_ptp(
                property_key="SHUTTER_ANGLE_X10",
                value=1800,
                transport="USB_PTP",
                bulk_read_bytes=bad_sz,
            )
            self.assertFalse(blk.valid)
            self.assertFalse(blk.bulk_512b_aligned)
            self.assertEqual(blk.status, "BLOCKED_PTP_0x9209_BULK_UNALIGNED_READ")

    def test_28_crsdk_invalid_property_body_transport_or_value_rejected(self) -> None:
        with self.assertRaises(ValueError):
            translate_crsdk_property_to_ptp(target_body="ILCE-9M3")
        with self.assertRaises(ValueError):
            translate_crsdk_property_to_ptp(property_key="UNKNOWN_PROP")
        with self.assertRaises(ValueError):
            translate_crsdk_property_to_ptp(transport="BLE_GATT")

        bad_val = translate_crsdk_property_to_ptp(
            property_key="BASE_ISO",
            value=99999,
            transport="USB_PTP",
        )
        self.assertFalse(bad_val.valid)
        self.assertEqual(bad_val.status, "BLOCKED_INVALID_CRSDK_PROPERTY_VALUE")
        self.assertEqual(len(CRSDK_PROPERTY_PTP_MAP), 8)

    def test_29_ptp_firewall_blocks_all_forbidden_flash_opcodes(self) -> None:
        for opcode in FORBIDDEN_PTP_FLASH_OPCODES:
            verdict = evaluate_ptp_flash_opcode_firewall(opcode=opcode)
            self.assertFalse(verdict.allowed, f"Opcode 0x{opcode:04X} was allowed!")
            self.assertEqual(verdict.status, "BLOCKED_STAGE_B_PTP_FLASH_OPCODE_FIREWALL")
            self.assertFalse(verdict.flash_write_executed)
            self.assertTrue(verdict.brick_risk_prevented)
            self.assertEqual(verdict.emmc_mutation_bytes, 0)

    def test_30_ptp_firewall_blocks_all_crsdk_fw_update_commands_even_on_0x9207(self) -> None:
        for cmd in FORBIDDEN_CRSDK_FW_UPDATE_COMMANDS:
            verdict = evaluate_ptp_flash_opcode_firewall(opcode=0x9207, command_name=cmd)
            self.assertFalse(verdict.allowed)
            self.assertEqual(verdict.status, "BLOCKED_STAGE_B_PTP_FLASH_OPCODE_FIREWALL")
            self.assertTrue(verdict.brick_risk_prevented)
            self.assertEqual(verdict.emmc_mutation_bytes, 0)

    def test_31_ptp_firewall_blocks_firmware_payload_magic_and_emmc_targets(self) -> None:
        for magic in FORBIDDEN_FIRMWARE_PAYLOAD_PATTERNS:
            verdict = evaluate_ptp_flash_opcode_firewall(
                opcode=0x9205,
                payload_prefix=magic + b"\x00\x01",
            )
            self.assertFalse(verdict.allowed)
            self.assertEqual(verdict.status, "BLOCKED_STAGE_B_PTP_FLASH_OPCODE_FIREWALL")

        verdict_tgt = evaluate_ptp_flash_opcode_firewall(
            opcode=0x9205,
            target_or_filename="/dev/nflasha5",
        )
        self.assertFalse(verdict_tgt.allowed)
        self.assertEqual(verdict_tgt.status, "BLOCKED_STAGE_B_PTP_FLASH_OPCODE_FIREWALL")

    def test_32_ptp_firewall_allows_safe_opcodes_and_blocks_unlisted(self) -> None:
        for opcode in SONY_SAFE_PTP_OPCODES:
            verdict = evaluate_ptp_flash_opcode_firewall(opcode=opcode)
            self.assertTrue(verdict.allowed, verdict.errors)
            self.assertEqual(verdict.status, "SAFE_CRSDK_PTP_OPCODE_ALLOWED")
            self.assertFalse(verdict.flash_write_executed)
            self.assertFalse(verdict.brick_risk_prevented)

        unlisted = evaluate_ptp_flash_opcode_firewall(opcode=0x92FF, command_name="VENDOR_UNKNOWN")
        self.assertFalse(unlisted.allowed)
        self.assertEqual(unlisted.status, "BLOCKED_UNLISTED_PTP_VENDOR_OPCODE")
        self.assertTrue(unlisted.brick_risk_prevented)

    # ---- Pillar 4: Volatile RAM Staging & Zero eMMC/Calibration Mutation ----

    def test_33_phase118_write_guard_allows_volatile_and_blocks_persistent_targets(self) -> None:
        for good in ("/tmp/fx3_crsdk_shadow.json", "ram://uvc_cfg.bin", "memory://srt_state"):
            res = evaluate_phase118_write_guard(good)
            self.assertTrue(res.valid, res.errors)
            self.assertTrue(res.volatile_ram_staged)
            self.assertFalse(res.persistent_write_blocked)
            self.assertEqual(res.emmc_mutation_bytes, 0)
            self.assertEqual(res.calibration_mutation_bytes, 0)

        for bad in (
            "/mnt/sd/BODYDATA.DAT",
            "/dev/nflasha15",
            "/dev/cnflasha0",
            "p2:/setting/Backup.bin",
            "p2:/setting/psd.bin",
            "p2:/setting/defdet.bin",
            "p6:/tmp/jiritsu",
            "/dev/mmcblk0rpmb",
            "updater://fw_stage",
        ):
            blk = evaluate_phase118_write_guard(bad)
            self.assertFalse(blk.valid, f"Failed to block persistent target {bad}")
            self.assertTrue(blk.persistent_write_blocked)
            self.assertEqual(blk.status, "BLOCKED_PERSISTENT_EMMC_OR_OTA_WRITE")
            self.assertEqual(blk.emmc_mutation_bytes, 0)
            self.assertEqual(blk.calibration_mutation_bytes, 0)

    # ---- Pillar Report Integrity, Negative Tests & CLI ----

    def test_34_pillar1_marker_and_uxc_label_integrity(self) -> None:
        rep = analyze_usb_uvc_uac_srt_and_crsdk_ptp(clean_room=True)
        p1 = rep.pillar_1_uvc_uac_streaming
        self.assertEqual(len(p1.fx3_appfw_uvc_markers), 4)
        self.assertEqual(len(p1.fx6_appfw_uvc_markers), 4)
        self.assertEqual(len(p1.fx3_libmpr_uac_markers), 4)
        self.assertEqual(len(p1.fx6_libmpr_uac_markers), 3)
        self.assertEqual(p1.uxc_uvc_labels["fx3_usb_streaming_invalid"], "Invalid during USB Streaming.")
        self.assertEqual(p1.uxc_uvc_labels["fx6_lpcm_1"], "LPCM")

    def test_35_pillar2_marker_and_uxc_label_integrity(self) -> None:
        rep = analyze_usb_uvc_uac_srt_and_crsdk_ptp(clean_room=True)
        p2 = rep.pillar_2_wired_srt_rtmps_p12
        self.assertEqual(len(p2.fx3_appfw_srt_markers), 4)
        self.assertEqual(len(p2.fx6_appfw_srt_markers), 3)
        self.assertEqual(len(p2.fx6_libnet_ether_markers), 3)
        self.assertEqual(len(p2.fx6_libveric_live_markers), 1)
        self.assertEqual(p2.uxc_srt_rtmps_labels["fx6_rtmp_rtmps"], "RTMP/RTMPS")
        self.assertEqual(p2.uxc_srt_rtmps_labels["fx6_srt_caller_1"], "SRT-Caller 1")

    def test_36_pillar3_marker_and_uxc_label_integrity(self) -> None:
        rep = analyze_usb_uvc_uac_srt_and_crsdk_ptp(clean_room=True)
        p3 = rep.pillar_3_crsdk_ptp_firewall
        self.assertEqual(len(p3.fx3_appfw_crsdk_markers), 5)
        self.assertEqual(len(p3.fx6_appfw_crsdk_markers), 5)
        self.assertEqual(len(p3.fx6_libinfra_ptp_markers), 4)
        self.assertIn("Connected to PC Remote.", p3.uxc_crsdk_labels["fx3_pc_remote_busy"])

    def test_37_pillar4_xdb_validity_and_zero_mutation_proof(self) -> None:
        rep = analyze_usb_uvc_uac_srt_and_crsdk_ptp(clean_room=True)
        p4 = rep.pillar_4_zero_mutation_emmc_preservation
        self.assertTrue(p4.passed)
        self.assertTrue(p4.fx3_global_xdb_valid)
        self.assertTrue(p4.fx6_global_xdb_valid)
        self.assertTrue(p4.firmware_flash_opcodes_blocked)
        self.assertEqual(p4.emmc_mutation_bytes, 0)
        self.assertEqual(p4.calibration_mutation_bytes, 0)
        self.assertFalse(p4.persistent_emmc_writes_authorized)

    def test_38_negative_missing_marker_detection_in_all_four_pillars(self) -> None:
        b1 = lab.evaluate_pillar_1_uvc_uac_streaming(
            fx3_appfw_uvc_markers=(),
            fx6_appfw_uvc_markers=(),
            fx3_libmpr_uac_markers=(),
            fx6_libmpr_uac_markers=(),
            uxc_uvc_labels={},
            extra_errors=("Simulated P1 missing marker",),
        )
        b2 = lab.evaluate_pillar_2_wired_srt_rtmps_p12(
            fx3_appfw_srt_markers=(),
            fx6_appfw_srt_markers=(),
            fx6_libnet_ether_markers=(),
            fx6_libveric_live_markers=(),
            uxc_srt_rtmps_labels={},
            extra_errors=("Simulated P2 missing marker",),
        )
        b3 = lab.evaluate_pillar_3_crsdk_ptp_firewall(
            fx3_appfw_crsdk_markers=(),
            fx6_appfw_crsdk_markers=(),
            fx6_libinfra_ptp_markers=(),
            uxc_crsdk_labels={},
            extra_errors=("Simulated P3 missing marker",),
        )
        b4 = lab.evaluate_pillar_4_zero_mutation_emmc_preservation(
            fx3_global_xdb_valid=False,
            fx6_global_xdb_valid=False,
            extra_errors=("Simulated P4 XDB failure",),
        )
        self.assertFalse(b1.passed)
        self.assertFalse(b2.passed)
        self.assertFalse(b3.passed)
        self.assertFalse(b4.passed)

    def test_39_cli_audit_uvc_srt_crsdk_clean_room_json(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cli_main(["audit-uvc-srt-crsdk", "--clean-room", "--json"])
        self.assertEqual(rc, 0)
        raw = buf.getvalue()
        self.assertIsNone(_BYTES_REPR_RE.search(raw))
        data = json.loads(raw)
        self.assertTrue(data["all_checks_passed"])
        self.assertEqual(data["mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(data["schema_version"], PHASE_118_SCHEMA)

    def test_40_cli_audit_uvc_srt_crsdk_auto_mode_json(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cli_main(["audit-uvc-srt-crsdk", "--json"])
        self.assertEqual(rc, 0)
        raw = buf.getvalue()
        self.assertIsNone(_BYTES_REPR_RE.search(raw))
        data = json.loads(raw)
        self.assertTrue(data["all_checks_passed"])
        self.assertIn(data["mode"], ("LOCAL_DONOR_VERIFIED", "CLEAN_ROOM_SYNTHETIC"))

    def test_41_run_audit_all_includes_at_least_23_auditors_and_passes(self) -> None:
        summary = run_audit_all(clean_room=True)
        self.assertTrue(summary["all_checks_passed"])
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
            "emount_af_breathing_and_ibis_audit",
            "shutter_ecs_sq_and_tally_audit",
            "wb_color_matrix_and_look_audit",
            "proxy_clipname_and_sidecar_audit",
            "assignable_zoom_ciz_and_fn_audit",
            "falsecolor_lpcm_tc_ub_audit",
            "playback_shotmark_and_ae_audit",
            "metadata_gyro_catalyst_and_anamorphic_audit",
            "interval_cache_and_ftp_audit",
            "lut3d_cube_tetrahedral_and_sdi_hdmi_audit",
            "c2pa_lens_shading_and_mc_fleet_audit",
            "hdr_hlg_bt2100_and_display_assist_audit",
            "hdmi_raw_prores_breathing_and_mishoe_clock_audit",
            "usb_uvc_uac_srt_and_crsdk_ptp_audit",
        }
        self.assertGreaterEqual(len(expected_keys), 23)
        self.assertTrue(expected_keys.issubset(set(summary.keys())))
        audit_keys = [k for k in summary if k.endswith("_audit")]
        self.assertGreaterEqual(len(audit_keys), 23)
        for key in expected_keys:
            self.assertTrue(summary[key]["all_checks_passed"], f"Failed auditor: {key}")

    def test_42_cli_audit_all_clean_room_json_passes_23_plus(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cli_main(["audit-all", "--clean-room", "--json"])
        self.assertEqual(rc, 0)
        data = json.loads(buf.getvalue())
        self.assertTrue(data["all_checks_passed"])
        self.assertTrue(data["usb_uvc_uac_srt_and_crsdk_ptp_audit"]["all_checks_passed"])


if __name__ == "__main__":
    unittest.main()
