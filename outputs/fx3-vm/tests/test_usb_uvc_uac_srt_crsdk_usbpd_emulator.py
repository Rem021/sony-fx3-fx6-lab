#!/usr/bin/env python3
"""Phase 121 Test Suite — Stage 21 USB-C UVC 1.5 / UAC 2.0 Isochronous/Bulk
Streaming, Wired P12-Safe SRT / RTMPS Live Streaming, CRSDK PTP / PTP-IP
Property Translator & Flash-Opcode Firewall, and G37/G38 20V USB-PD Decoy /
15-Pin Multi-Terminal / 1.8V UART HIL.

Exercises 40 fast unit, protocol, fail-closed guard, Stage 21 suite integration,
CLI, and source-hygiene tests across BOTH Local Donor (`os.O_RDONLY`) and
`FX3_FX6_FORCE_CLEAN_ROOM=1` modes, strictly offline.
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
import usb_uvc_uac_srt_crsdk_usbpd_emulator as p121  # noqa: E402


_AUDIT_CACHE: dict = {}


def _get_clean_room_audit() -> dict:
    if "clean_room" not in _AUDIT_CACHE:
        _AUDIT_CACHE["clean_room"] = p121.run_phase121_uvc_srt_crsdk_usbpd_audit(
            force_clean_room=True
        )
    return _AUDIT_CACHE["clean_room"]


class TestPhase121DonorAuditAndRedlines(unittest.TestCase):
    """Verify O_RDONLY donor audit, clean-room fallback, and zero-mutation redlines."""

    def test_01_clean_room_donor_audit_verifies_all_12_artifacts_and_sha256(self) -> None:
        audit = p121.inspect_phase121_donors(force_clean_room=True)
        self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(audit.access_mode, "O_RDONLY")
        self.assertEqual(audit.donor_files_inspected, 0)
        self.assertTrue(audit.all_contracts_verified)
        self.assertGreaterEqual(len(audit.checked_markers), 36)
        self.assertEqual(audit.missing_markers, ())
        for key, (expected_bytes, expected_sha) in p121.PINNED_DONOR_SHA256.items():
            self.assertEqual(audit.bytes_by_artifact[key], expected_bytes)
            self.assertEqual(audit.sha256_by_artifact[key], expected_sha)

    def test_02_force_clean_room_env_disables_local_donor_paths(self) -> None:
        env = {p121.ENV_FORCE_CLEAN_ROOM: "1"}
        self.assertTrue(p121.is_forced_clean_room(env))
        paths = p121.resolve_phase121_donor_paths(env=env)
        self.assertEqual(len(paths), 12)
        for path in paths.values():
            self.assertIn(p121.CLEAN_ROOM_SENTINEL_DIRNAME, str(path))
        audit = p121.inspect_phase121_donors(env=env)
        self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_03_local_donor_o_rdonly_audit_when_present_or_clean_room(self) -> None:
        if p121.is_forced_clean_room():
            audit = p121.inspect_phase121_donors()
            self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")
            return
        paths = p121.resolve_phase121_donor_paths()
        audit = p121.inspect_phase121_donors()
        self.assertTrue(audit.all_contracts_verified)
        if all(p.is_file() for p in paths.values()):
            self.assertEqual(audit.source_mode, "LOCAL_DONOR_RDONLY")
            self.assertEqual(audit.donor_files_inspected, 12)
            for key, (expected_bytes, expected_sha) in p121.PINNED_DONOR_SHA256.items():
                self.assertEqual(audit.bytes_by_artifact[key], expected_bytes)
                self.assertEqual(audit.sha256_by_artifact[key], expected_sha)
        else:
            self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_04_missing_donor_root_falls_back_to_clean_room(self) -> None:
        env = {
            p121.ENV_MAC_WORK_ROOT: "/nonexistent_phase121_mac_work_root",
            p121.ENV_MAIN_LAB_WORK_ROOT: "/nonexistent_phase121_main_work_root",
        }
        audit = p121.inspect_phase121_donors(force_clean_room=True, env=env)
        self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(audit.donor_files_inspected, 0)
        self.assertTrue(audit.all_contracts_verified)

    def test_05_redlines_zero_mutations_zero_wf12_and_zero_pad_damage(self) -> None:
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
        self.assertEqual(red["emmc_flash_mutation_bytes"], 0)
        self.assertEqual(red["wf12_00342260_hits"], 0)
        self.assertEqual(red["cxd90057_pad_damage_events"], 0)
        self.assertEqual(red["uvc_osd_burn_in_frames"], 0)
        self.assertEqual(red["srt_dropped_gops"], 0)
        self.assertEqual(red["uart_tx_bytes"], 0)
        self.assertEqual(red["donor_access_mode"], "O_RDONLY")


class TestPillarAUvcUacNegotiator(unittest.TestCase):
    """Verify UVC 1.5 / UAC 2.0 descriptors, USB3 vs USB2 step-down & clean feed."""

    def test_06_build_and_verify_44byte_uvc15_uac20_descriptor_bundle(self) -> None:
        bundle_hex = p121.build_uvc_uac_descriptor_bundle(
            width=3840,
            height=2160,
            fps_x100=3000,
            pixel_format="MJPEG",
            uac_sample_rate_hz=48_000,
            uac_channels=2,
            uac_bit_depth=16,
        )
        self.assertEqual(len(bytes.fromhex(bundle_hex)), p121.UVC_BUNDLE_BYTES)
        dec = p121.parse_and_verify_uvc_uac_descriptor_bundle(bundle_hex)
        self.assertTrue(dec["valid"])
        self.assertEqual(dec["vendor_id_hex"], "0x054c")
        self.assertEqual(dec["uvc_bcd_hex"], "0x0150")
        self.assertEqual(dec["uac_bcd_hex"], "0x0200")
        self.assertEqual(dec["width"], 3840)
        self.assertEqual(dec["height"], 2160)
        self.assertEqual(dec["fps_x100"], 3000)
        self.assertEqual(dec["pixel_format"], "MJPEG")
        self.assertEqual(dec["uac_sample_rate_hz"], 48_000)
        self.assertEqual(dec["uac_channels"], 2)
        self.assertEqual(dec["uac_bit_depth"], 16)

    def test_07_corrupt_uvc_descriptor_crc_length_magic_ids_rejected(self) -> None:
        bundle_hex = p121.build_uvc_uac_descriptor_bundle(
            width=1920,
            height=1080,
            fps_x100=6000,
            pixel_format="YUY2",
        )
        bad_crc = bytearray.fromhex(bundle_hex)
        bad_crc[12] ^= 0x5A
        r_crc = p121.parse_and_verify_uvc_uac_descriptor_bundle(bad_crc.hex())
        self.assertFalse(r_crc["valid"])
        self.assertEqual(r_crc["violation_code"], "BLOCKED_UVC_DESCRIPTOR_CRC_MISMATCH")

        r_len = p121.parse_and_verify_uvc_uac_descriptor_bundle(bundle_hex[:-4])
        self.assertFalse(r_len["valid"])
        self.assertEqual(r_len["violation_code"], "BLOCKED_UVC_DESCRIPTOR_BAD_LENGTH")

        r_hex = p121.parse_and_verify_uvc_uac_descriptor_bundle("zzzz")
        self.assertFalse(r_hex["valid"])
        self.assertEqual(r_hex["violation_code"], "BLOCKED_UVC_DESCRIPTOR_INVALID_HEX")

    def test_08_usb3_superspeed_5g_4k30p_mjpeg_and_1080p60p_yuy2_nominal(self) -> None:
        r_4k = p121.negotiate_uvc_uac_stream(
            requested_profile="4K30P_MJPEG",
            usb_link_speed=p121.USB_LINK_SUPERSPEED_5G,
            transfer_mode=p121.TRANSFER_ISOCHRONOUS,
        )
        self.assertTrue(r_4k.passed)
        self.assertFalse(r_4k.step_down_applied)
        self.assertEqual(r_4k.negotiated_profile, "4K30P_MJPEG")
        self.assertAlmostEqual(r_4k.audio_mbps, 1.536, places=3)
        self.assertAlmostEqual(r_4k.total_payload_mbps, 151.536, places=3)
        self.assertTrue(r_4k.clean_feed_verified)
        self.assertEqual(r_4k.uvc_osd_burn_in_frames, 0)

        r_fhd = p121.negotiate_uvc_uac_stream(
            requested_profile="1080P60P_YUY2",
            usb_link_speed=p121.USB_LINK_SUPERSPEED_5G,
            transfer_mode=p121.TRANSFER_BULK,
        )
        self.assertTrue(r_fhd.passed)
        self.assertFalse(r_fhd.step_down_applied)
        self.assertEqual(r_fhd.negotiated_profile, "1080P60P_YUY2")
        self.assertAlmostEqual(r_fhd.total_payload_mbps, 1992.192, places=3)
        self.assertLessEqual(r_fhd.total_payload_mbps, r_fhd.usable_ceiling_mbps)

    def test_09_usb2_highspeed_480m_cable_auto_stepdown_yuy2_to_mjpeg_under_480mbps(self) -> None:
        res = p121.negotiate_uvc_uac_stream(
            requested_profile="1080P60P_YUY2",
            usb_link_speed=p121.USB_LINK_HIGHSPEED_480M,
            transfer_mode=p121.TRANSFER_ISOCHRONOUS,
            auto_step_down=True,
        )
        self.assertTrue(res.passed)
        self.assertTrue(res.step_down_applied)
        self.assertEqual(res.negotiated_profile, "1080P60P_MJPEG")
        self.assertLess(res.total_payload_mbps, 480.0)
        self.assertLessEqual(res.total_payload_mbps, res.usable_ceiling_mbps)
        self.assertTrue(res.never_exceeds_480mbps_on_usb2)

    def test_10_usb2_4k30p_yuy2_steps_down_to_4k30p_mjpeg_under_480mbps(self) -> None:
        res = p121.negotiate_uvc_uac_stream(
            requested_profile="4K30P_YUY2",
            usb_link_speed=p121.USB_LINK_HIGHSPEED_480M,
            transfer_mode=p121.TRANSFER_BULK,
            auto_step_down=True,
        )
        self.assertTrue(res.passed)
        self.assertTrue(res.step_down_applied)
        self.assertEqual(res.negotiated_profile, "4K30P_MJPEG")
        self.assertLess(res.total_payload_mbps, 480.0)
        self.assertTrue(res.never_exceeds_480mbps_on_usb2)

    def test_11_usb2_no_stepdown_over_480mbps_blocked_fail_closed(self) -> None:
        res = p121.negotiate_uvc_uac_stream(
            requested_profile="1080P60P_YUY2",
            usb_link_speed=p121.USB_LINK_HIGHSPEED_480M,
            auto_step_down=False,
        )
        self.assertFalse(res.passed)
        self.assertIn("BLOCKED_USB2_HS_480M_BANDWIDTH_EXCEEDED", res.violation_codes)

    def test_12_uvc_clean_feed_isolates_local_osd_and_blocks_burn_in_fault(self) -> None:
        clean = p121.negotiate_uvc_uac_stream(
            requested_profile="4K30P_MJPEG",
            local_osd_enabled=True,
            inject_osd_burn_in_fault=False,
        )
        self.assertTrue(clean.passed)
        self.assertEqual(clean.uvc_osd_burn_in_frames, 0)
        self.assertNotEqual(clean.uvc_stream_sha256, clean.local_gpe0_osd_sha256)

        fault = p121.negotiate_uvc_uac_stream(
            requested_profile="4K30P_MJPEG",
            inject_osd_burn_in_fault=True,
        )
        self.assertFalse(fault.passed)
        self.assertIn("BLOCKED_UVC_OSD_BURN_IN_CONTAMINATION", fault.violation_codes)
        self.assertEqual(fault.uvc_osd_burn_in_frames, 1)

    def test_13_uvc_blocks_sq_motion_and_hdmi_raw16_exclusions(self) -> None:
        r_sq = p121.negotiate_uvc_uac_stream(sq_motion_active=True)
        self.assertFalse(r_sq.passed)
        self.assertIn("BLOCKED_UVC_SQ_MOTION_EXCLUSION", r_sq.violation_codes)

        r_raw = p121.negotiate_uvc_uac_stream(hdmi_raw_active=True)
        self.assertFalse(r_raw.passed)
        self.assertIn("BLOCKED_UVC_HDMI_RAW16_EXCLUSION", r_raw.violation_codes)

    def test_14_uvc_invalid_profile_speed_or_transfer_raises(self) -> None:
        with self.assertRaises(p121.UsbUvcSrtCrsdkUsbpdError):
            p121.negotiate_uvc_uac_stream(requested_profile="8K60_RAW")
        with self.assertRaises(p121.UsbUvcSrtCrsdkUsbpdError):
            p121.negotiate_uvc_uac_stream(usb_link_speed="USB1_FULLSPEED")
        with self.assertRaises(p121.UsbUvcSrtCrsdkUsbpdError):
            p121.negotiate_uvc_uac_stream(transfer_mode="INTERRUPT")


class TestPillarBWiredSrtRtmpsP12(unittest.TestCase):
    """Verify wired USB-LAN SRT (ARQ <=8% loss -> 0 dropped GOPs) & RTMPS under P12."""

    def test_15_srt_caller_aes256_recovers_8pct_loss_with_zero_dropped_gops(self) -> None:
        res = p121.simulate_wired_srt_rtmps_stream(
            protocol="SRT_CALLER",
            transport_driver="CDC_NCM_RTL8153",
            pbkeylen_bytes=32,
            arq_latency_ms=120,
            rtt_ms=25,
            simulated_loss_pct=8.0,
            total_gops=10,
            packets_per_gop=600,
        )
        self.assertTrue(res.passed)
        self.assertEqual(res.cipher_suite, "AES-256-CTR")
        self.assertEqual(res.lost_packets, 480)
        self.assertEqual(res.recovered_packets, 480)
        self.assertEqual(res.unrecovered_packets, 0)
        self.assertEqual(res.dropped_gops, 0)
        self.assertEqual(res.wf12_00342260_hits, 0)

    def test_16_srt_listener_aes128_rndis_1000ms_arq_recovers_loss_zero_drops(self) -> None:
        res = p121.simulate_wired_srt_rtmps_stream(
            protocol="SRT_LISTENER",
            transport_driver="USB_RNDIS_WIRED",
            pbkeylen_bytes=16,
            arq_latency_ms=1000,
            rtt_ms=100,
            simulated_loss_pct=7.5,
        )
        self.assertTrue(res.passed)
        self.assertEqual(res.cipher_suite, "AES-128-CTR")
        self.assertEqual(res.dropped_gops, 0)
        self.assertEqual(res.unrecovered_packets, 0)
        self.assertEqual(res.wf12_00342260_hits, 0)

    def test_17_rtmps_tls13_cdc_ncm_ax88179_root_ca_verified_passes(self) -> None:
        res = p121.simulate_wired_srt_rtmps_stream(
            protocol="RTMPS_TLS13",
            transport_driver="CDC_NCM_AX88179",
            simulated_loss_pct=0.0,
            tls_version="TLS_1_3",
            root_ca_verified=True,
        )
        self.assertTrue(res.passed)
        self.assertEqual(res.cipher_suite, "TLS_AES_256_GCM_SHA384")
        self.assertEqual(res.dropped_gops, 0)
        self.assertEqual(res.wf12_00342260_hits, 0)

    def test_18_all_forbidden_rf_transports_blocked_under_p12_with_zero_wf12_hits(self) -> None:
        for rf_drv in p121.FORBIDDEN_RF_TRANSPORTS:
            res = p121.simulate_wired_srt_rtmps_stream(
                protocol="SRT_CALLER",
                transport_driver=rf_drv,
                simulated_loss_pct=0.0,
            )
            self.assertFalse(res.passed, msg=f"RF transport {rf_drv} must fail closed")
            self.assertIn("BLOCKED_P12_RF_OFF_VIOLATION_00342260", res.violation_codes)
            self.assertEqual(res.wf12_00342260_hits, 0)
            self.assertEqual(res.hci_rf_tx_packets, 0)

    def test_19_srt_excessive_15pct_loss_reports_gop_loss_fail_closed(self) -> None:
        res = p121.simulate_wired_srt_rtmps_stream(
            protocol="SRT_CALLER",
            transport_driver="CDC_NCM_RTL8153",
            arq_latency_ms=120,
            rtt_ms=25,
            simulated_loss_pct=15.0,
        )
        self.assertFalse(res.passed)
        self.assertIn("BLOCKED_SRT_ARQ_GOP_LOSS", res.violation_codes)
        self.assertGreater(res.unrecovered_packets, 0)
        self.assertGreater(res.dropped_gops, 0)

    def test_20_srt_invalid_pbkeylen_passphrase_and_arq_bounds_rejected(self) -> None:
        bad_key = p121.simulate_wired_srt_rtmps_stream(pbkeylen_bytes=24)
        self.assertFalse(bad_key.passed)
        self.assertIn("BLOCKED_SRT_INVALID_PBKEYLEN", bad_key.violation_codes)

        short_pass = p121.simulate_wired_srt_rtmps_stream(passphrase="short")
        self.assertFalse(short_pass.passed)
        self.assertIn("BLOCKED_SRT_PASSPHRASE_LENGTH", short_pass.violation_codes)

        bad_arq = p121.simulate_wired_srt_rtmps_stream(arq_latency_ms=10)
        self.assertFalse(bad_arq.passed)
        self.assertIn("BLOCKED_SRT_ARQ_LATENCY_OUT_OF_RANGE", bad_arq.violation_codes)

        tight_rtt = p121.simulate_wired_srt_rtmps_stream(arq_latency_ms=40, rtt_ms=25)
        self.assertFalse(tight_rtt.passed)
        self.assertIn("BLOCKED_SRT_ARQ_RTT_MARGIN", tight_rtt.violation_codes)

    def test_21_rtmps_tls12_unverified_ca_and_plaintext_rtmp_rejected(self) -> None:
        bad_tls = p121.simulate_wired_srt_rtmps_stream(
            protocol="RTMPS_TLS13",
            tls_version="TLS_1_2",
            simulated_loss_pct=0.0,
        )
        self.assertFalse(bad_tls.passed)
        self.assertIn("BLOCKED_RTMPS_REQUIRES_TLS13", bad_tls.violation_codes)

        bad_ca = p121.simulate_wired_srt_rtmps_stream(
            protocol="RTMPS_TLS13",
            root_ca_verified=False,
            simulated_loss_pct=0.0,
        )
        self.assertFalse(bad_ca.passed)
        self.assertIn("BLOCKED_RTMPS_ROOT_CA_UNVERIFIED", bad_ca.violation_codes)

        plain = p121.simulate_wired_srt_rtmps_stream(
            protocol="RTMP_PLAIN",
            simulated_loss_pct=0.0,
        )
        self.assertFalse(plain.passed)
        self.assertIn("BLOCKED_PLAINTEXT_RTMP_FORBIDDEN", plain.violation_codes)

    def test_22_streaming_invalid_protocol_loss_or_gops_raises(self) -> None:
        with self.assertRaises(p121.UsbUvcSrtCrsdkUsbpdError):
            p121.simulate_wired_srt_rtmps_stream(protocol="RTSP_UDP")
        with self.assertRaises(p121.UsbUvcSrtCrsdkUsbpdError):
            p121.simulate_wired_srt_rtmps_stream(simulated_loss_pct=-1.0)
        with self.assertRaises(p121.UsbUvcSrtCrsdkUsbpdError):
            p121.simulate_wired_srt_rtmps_stream(total_gops=0)


class TestPillarCCrsdkPtpAndFlashFirewall(unittest.TestCase):
    """Verify Sony CRSDK PTP/PTP-IP 0x054C translator & 0x9280.. Flash Firewall."""

    def test_23_crsdk_translates_cine_ei_base_iso_3dlut_shutter_angle_and_rec(self) -> None:
        r_ei = p121.translate_crsdk_to_ptp_property(
            property_key="CINE_EI_LOG_MODE", value="CINE_EI", transport="USB_PTP"
        )
        self.assertTrue(r_ei.passed)
        self.assertEqual(r_ei.usb_vid_hex, "0x054c")
        self.assertEqual(r_ei.ptp_prop_code_hex, "0xd243")

        r_iso = p121.translate_crsdk_to_ptp_property(
            property_key="BASE_ISO", value=12800, transport="WIRED_PTPIP_15740"
        )
        self.assertTrue(r_iso.passed)
        self.assertEqual(r_iso.ptp_prop_code_hex, "0xd244")
        self.assertEqual(r_iso.translated_value, 12800)

        r_lut = p121.translate_crsdk_to_ptp_property(
            property_key="USER_3D_LUT", value="USER2", transport="WIRED_PTPIP_15740"
        )
        self.assertTrue(r_lut.passed)
        self.assertEqual(r_lut.ptp_prop_code_hex, "0xd253")

        r_shutter = p121.translate_crsdk_to_ptp_property(
            property_key="SHUTTER_ANGLE_X10", value=1800, transport="USB_PTP"
        )
        self.assertTrue(r_shutter.passed)
        self.assertEqual(r_shutter.ptp_prop_code_hex, "0xd20d")

        r_rec = p121.translate_crsdk_to_ptp_property(
            property_key="REC_CONTROL", value="REC_START", transport="USB_PTP"
        )
        self.assertTrue(r_rec.passed)
        self.assertEqual(r_rec.ptp_prop_code_hex, "0xd215")

    def test_24_fx3_p4_electronic_nd_clamps_to_clear_while_fx6_preserves(self) -> None:
        fx3_nd = p121.translate_crsdk_to_ptp_property(
            target_body="ILME-FX3",
            property_key="ND_FILTER_OD_X10",
            value=15,
            transport="USB_PTP",
        )
        self.assertTrue(fx3_nd.passed)
        self.assertTrue(fx3_nd.p4_nd_clamped_clear)
        self.assertEqual(fx3_nd.translated_value, 0)
        self.assertEqual(fx3_nd.p4_nd_motor_faults, 0)
        self.assertEqual(fx3_nd.status, "P4_ABSENT_ND_CLAMPED_CLEAR")

        fx6_nd = p121.translate_crsdk_to_ptp_property(
            target_body="ILME-FX6",
            property_key="ND_FILTER_OD_X10",
            value=15,
            transport="USB_PTP",
        )
        self.assertTrue(fx6_nd.passed)
        self.assertFalse(fx6_nd.p4_nd_clamped_clear)
        self.assertEqual(fx6_nd.translated_value, 15)

    def test_25_crsdk_bad_value_or_unaligned_usb_bulk_rejected(self) -> None:
        bad_val = p121.translate_crsdk_to_ptp_property(
            property_key="BASE_ISO", value=640, transport="USB_PTP"
        )
        self.assertFalse(bad_val.passed)
        self.assertIn("BLOCKED_CRSDK_INVALID_PROPERTY_VALUE", bad_val.violation_codes)

        bad_bulk = p121.translate_crsdk_to_ptp_property(
            property_key="CINE_EI_LOG_MODE",
            value="CINE_EI",
            transport="USB_PTP",
            bulk_packet_bytes=510,
        )
        self.assertFalse(bad_bulk.passed)
        self.assertIn("BLOCKED_PTP_USB_BULK_ALIGNMENT", bad_bulk.violation_codes)

    def test_26_crsdk_unknown_property_transport_or_body_raises(self) -> None:
        with self.assertRaises(p121.UsbUvcSrtCrsdkUsbpdError):
            p121.translate_crsdk_to_ptp_property(property_key="UNKNOWN_PROP", value=1)
        with self.assertRaises(p121.UsbUvcSrtCrsdkUsbpdError):
            p121.translate_crsdk_to_ptp_property(transport="WIFI_PTPIP")
        with self.assertRaises(p121.UsbUvcSrtCrsdkUsbpdError):
            p121.translate_crsdk_to_ptp_property(target_body="ILME-FX9")

    def test_27_ptp_firewall_hard_rejects_0x9280_to_0x928f_and_ota_opcodes(self) -> None:
        for opcode in list(range(0x9280, 0x9290)) + [0x100C, 0x100D, 0x9805, 0x92F0, 0x92F1, 0x92F2]:
            fw = p121.evaluate_ptp_firmware_opcode_firewall(opcode=opcode, hybrid_stage_b_mode=True)
            self.assertFalse(fw.allowed, msg=f"Opcode 0x{opcode:04x} must be blocked")
            self.assertTrue(fw.blocked_by_firewall)
            self.assertEqual(fw.status, "BLOCKED_PTP_DESTRUCTIVE_FLASH_OPCODE")
            self.assertEqual(fw.emmc_flash_mutation_bytes, 0)
            self.assertTrue(fw.brick_risk_prevented)

    def test_28_ptp_firewall_blocks_firmware_payload_signatures_and_command_names(self) -> None:
        for sig in p121.FORBIDDEN_FW_PAYLOAD_SIGNATURES:
            fw = p121.evaluate_ptp_firmware_opcode_firewall(
                opcode=0x9205,
                hybrid_stage_b_mode=True,
                payload_preview=b"HDR" + sig + b"TAIL",
            )
            self.assertFalse(fw.allowed)
            self.assertEqual(fw.emmc_flash_mutation_bytes, 0)

        fw_cmd = p121.evaluate_ptp_firmware_opcode_firewall(
            opcode=0x9205,
            hybrid_stage_b_mode=True,
            command_name="CRSDK_FIRMWARE_UPDATE_START",
        )
        self.assertFalse(fw_cmd.allowed)
        self.assertEqual(fw_cmd.emmc_flash_mutation_bytes, 0)

    def test_29_ptp_firewall_permits_safe_crsdk_opcodes_and_rejects_unknown(self) -> None:
        for opcode in p121.SAFE_SONY_PTP_OPCODES:
            fw = p121.evaluate_ptp_firmware_opcode_firewall(opcode=opcode, hybrid_stage_b_mode=True)
            self.assertTrue(fw.allowed, msg=f"Safe opcode 0x{opcode:04x} should be allowed")
            self.assertFalse(fw.blocked_by_firewall)
            self.assertEqual(fw.emmc_flash_mutation_bytes, 0)

        unk = p121.evaluate_ptp_firmware_opcode_firewall(opcode=0x9999, hybrid_stage_b_mode=True)
        self.assertFalse(unk.allowed)
        self.assertEqual(unk.status, "BLOCKED_UNRECOGNIZED_PTP_OPCODE_FAIL_CLOSED")


class TestPillarDG37G38UsbPdDecoyAndMultiPortHil(unittest.TestCase):
    """Verify G37 20V USB-PD decoy OVP crowbar & G38 15-pin LTC / 1.8V RX-only UART HIL."""

    def test_30_g37_valid_9v_3a_27w_pd_and_isolated_dual_source_pass(self) -> None:
        pd_ok = p121.simulate_g37_usbpd_decoy_isolator_hil(
            vbus_voltage_v=9.0,
            pd_current_a=3.0,
            pd_contract_negotiated=True,
            decoy_trigger_present=False,
        )
        self.assertTrue(pd_ok.passed)
        self.assertEqual(pd_ok.delivered_power_w, 27.0)
        self.assertFalse(pd_ok.ovp_crowbar_tripped)
        self.assertEqual(pd_ok.cxd90057_pad_damage_events, 0)
        self.assertEqual(pd_ok.pmic_ovp_damage_events, 0)

        dual_ok = p121.simulate_g37_usbpd_decoy_isolator_hil(
            vbus_voltage_v=9.0,
            pd_current_a=3.0,
            pd_contract_negotiated=True,
            dtap_connected=True,
            usbpd_connected=True,
            isolator_present=True,
        )
        self.assertTrue(dual_ok.passed)
        self.assertTrue(dual_ok.ground_loop_isolated)
        self.assertEqual(dual_ok.cross_feed_current_ma, 0.0)

    def test_31_g37_20v_dtap_decoy_trips_ovp_crowbar_under_35us_zero_damage(self) -> None:
        decoy = p121.simulate_g37_usbpd_decoy_isolator_hil(
            vbus_voltage_v=20.0,
            pd_current_a=3.0,
            pd_contract_negotiated=False,
            decoy_trigger_present=True,
        )
        self.assertFalse(decoy.passed)
        self.assertIn("BLOCKED_G37_UNNEGOTIATED_USBPD_DECOY_OVP_CROWBAR", decoy.violation_codes)
        self.assertTrue(decoy.ovp_crowbar_tripped)
        self.assertGreater(decoy.crowbar_latency_us, 0.0)
        self.assertLess(decoy.crowbar_latency_us, p121.G37_OVP_MAX_CROWBAR_US)
        self.assertLess(decoy.pmic_clamped_peak_v, p121.G37_PMIC_CLAMP_CEILING_V)
        self.assertEqual(decoy.delivered_power_w, 0.0)
        self.assertEqual(decoy.cxd90057_pad_damage_events, 0)
        self.assertEqual(decoy.pmic_ovp_damage_events, 0)
        self.assertEqual(decoy.wdt_resets, 0)

    def test_32_g37_unisolated_dtap_plus_usbpd_crossfeed_blocked(self) -> None:
        cross = p121.simulate_g37_usbpd_decoy_isolator_hil(
            vbus_voltage_v=9.0,
            pd_current_a=3.0,
            pd_contract_negotiated=True,
            dtap_connected=True,
            usbpd_connected=True,
            isolator_present=False,
        )
        self.assertFalse(cross.passed)
        self.assertIn("BLOCKED_G37_DUAL_SOURCE_DTAP_USBPD_CROSSFEED", cross.violation_codes)
        self.assertFalse(cross.ground_loop_isolated)
        self.assertGreater(cross.cross_feed_current_ma, 0.0)
        self.assertEqual(cross.cxd90057_pad_damage_events, 0)

    def test_33_g38_nominal_1v8_passive_rx_only_and_gt5vpp_ltc_clamp(self) -> None:
        nom = p121.simulate_g38_multiport_ltc_uart_hil(
            ltc_input_vpp=2.2,
            uart_logic_voltage_v=1.8,
            uart_passive_rx_only=True,
            requested_tx_bytes=0,
        )
        self.assertTrue(nom.passed)
        self.assertFalse(nom.ltc_clamp_engaged)
        self.assertEqual(nom.tx_bytes, 0)
        self.assertEqual(nom.cxd90057_pad_damage_events, 0)

        ltc_ov = p121.simulate_g38_multiport_ltc_uart_hil(
            ltc_input_vpp=6.2,
            uart_logic_voltage_v=1.8,
            uart_passive_rx_only=True,
            requested_tx_bytes=0,
        )
        self.assertFalse(ltc_ov.passed)
        self.assertIn("BLOCKED_G38_MULTIPORT_LTC_OVER_5VPP_CLAMPED", ltc_ov.violation_codes)
        self.assertTrue(ltc_ov.ltc_clamp_engaged)
        self.assertLessEqual(ltc_ov.ltc_clamped_v, p121.G38_MULTIPORT_CLAMP_CEILING_V)
        self.assertEqual(ltc_ov.cxd90057_pad_damage_events, 0)

    def test_34_g38_uart_3v3_5v_overdrive_and_active_tx_rejected_tx_bytes_zero(self) -> None:
        u33 = p121.simulate_g38_multiport_ltc_uart_hil(
            ltc_input_vpp=2.0,
            uart_logic_voltage_v=3.3,
            uart_passive_rx_only=True,
            requested_tx_bytes=0,
        )
        self.assertFalse(u33.passed)
        self.assertIn("BLOCKED_G38_UART_OVERDRIVE_ABOVE_1V8", u33.violation_codes)
        self.assertTrue(u33.uart_overdrive_rejected)
        self.assertEqual(u33.tx_bytes, 0)
        self.assertEqual(u33.cxd90057_pad_damage_events, 0)

        u50_tx = p121.simulate_g38_multiport_ltc_uart_hil(
            ltc_input_vpp=2.0,
            uart_logic_voltage_v=5.0,
            uart_passive_rx_only=False,
            requested_tx_bytes=64,
        )
        self.assertFalse(u50_tx.passed)
        self.assertIn("BLOCKED_G38_UART_OVERDRIVE_ABOVE_1V8", u50_tx.violation_codes)
        self.assertIn("BLOCKED_G38_UART_ACTIVE_TX_FORBIDDEN_RX_ONLY", u50_tx.violation_codes)
        self.assertEqual(u50_tx.tx_bytes, 0)
        self.assertEqual(u50_tx.cxd90057_pad_damage_events, 0)

        with self.assertRaises(p121.UsbUvcSrtCrsdkUsbpdError):
            p121.simulate_g37_usbpd_decoy_isolator_hil(vbus_voltage_v=-1.0)
        with self.assertRaises(p121.UsbUvcSrtCrsdkUsbpdError):
            p121.simulate_g38_multiport_ltc_uart_hil(uart_logic_voltage_v=-0.5)


class TestStage21SuiteIntegrationCliAndHygiene(unittest.TestCase):
    """Verify Stage 21 suite integration, CLI flags, runtime budgets & strict hygiene."""

    def test_35_clean_room_audit_digest_reproducible_and_no_bytes_repr(self) -> None:
        rep1 = p121.run_phase121_uvc_srt_crsdk_usbpd_audit(force_clean_room=True)
        rep2 = p121.run_phase121_uvc_srt_crsdk_usbpd_audit(force_clean_room=True)
        self.assertTrue(rep1["all_checks_passed"])
        self.assertEqual(rep1["audit_digest_sha256"], rep2["audit_digest_sha256"])

        rendered = json.dumps(rep1, allow_nan=False)
        self.assertNotRegex(rendered, r'(?<![0-9A-Za-z_/.-])b[\'"]')

        copy = dict(rep1)
        recorded = copy.pop("audit_digest_sha256")
        expected = hashlib.sha256(
            json.dumps(copy, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        self.assertEqual(recorded, expected)

    def test_36_standalone_cli_flags_emit_valid_outputs(self) -> None:
        for argv in (
            ["--clean-room", "--summary"],
            ["--clean-room", "--uvc-matrix"],
            ["--clean-room", "--srt-matrix"],
            ["--clean-room", "--crsdk-matrix"],
            ["--clean-room", "--hil-matrix"],
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = p121.main(argv)
            self.assertEqual(rc, 0, msg=f"CLI argv={argv} failed")
            self.assertTrue(buf.getvalue().strip())

    def test_37_suite_in_process_stage21_ge21_stages_and_skip_phase121_config(self) -> None:
        cfg_on = suite.CoEmulationConfig(force_clean_room=True)
        rep_on = suite.run_fx3_vm_coemulation_suite(cfg_on)
        self.assertTrue(rep_on["all_checks_passed"])
        self.assertIn("stage21_uvc_srt_crsdk_usbpd_hil", rep_on)
        self.assertTrue(rep_on["stage21_uvc_srt_crsdk_usbpd_hil"]["all_checks_passed"])

        stage_keys = [k for k in rep_on if re.match(r"^stage\d+_", k)]
        self.assertGreaterEqual(len(stage_keys), 21)

        cfg_skip = suite.CoEmulationConfig(
            force_clean_room=True,
            include_phase121_uvc_srt_crsdk_usbpd_hil=False,
        )
        rep_skip = suite.run_fx3_vm_coemulation_suite(cfg_skip)
        self.assertTrue(rep_skip["all_checks_passed"])
        self.assertNotIn("stage21_uvc_srt_crsdk_usbpd_hil", rep_skip)

    def test_38_suite_subprocess_summary_and_skip_phase121_flag(self) -> None:
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
        self.assertIn("uvc_srt_crsdk_usbpd=CLEAN_ROOM_SYNTHETIC", proc.stdout)

        proc_skip = subprocess.run(
            [
                "/usr/bin/python3",
                "-B",
                str(FX3_VM_DIR / "fx3_vm_coemulation_suite.py"),
                "--clean-room",
                "--skip-phase121",
                "--summary",
            ],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc_skip.returncode, 0, msg=proc_skip.stderr)
        self.assertNotIn("uvc_srt_crsdk_usbpd=", proc_skip.stdout)

    def test_39_21_stage_suite_clean_room_and_local_runtime_under_budget(self) -> None:
        t0 = time.monotonic()
        rep_clean = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig(force_clean_room=True))
        elapsed_clean = time.monotonic() - t0
        self.assertTrue(rep_clean["all_checks_passed"])
        self.assertLess(elapsed_clean, 0.70)

        t1 = time.monotonic()
        rep_mode = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig())
        elapsed_mode = time.monotonic() - t1
        self.assertTrue(rep_mode["all_checks_passed"])
        self.assertLess(elapsed_mode, 1.80)

    def test_40_source_hygiene_o_rdonly_and_no_write_flags_or_port_8768_or_raw_bytes(self) -> None:
        src = (FX3_VM_DIR / "usb_uvc_uac_srt_crsdk_usbpd_emulator.py").read_text(encoding="utf-8")
        self.assertIn("os.O_RDONLY", src)
        self.assertNotIn("os.O_WRONLY", src)
        self.assertNotIn("os.O_RDWR", src)
        self.assertNotIn("87" + "68", src)
        self.assertIn("sys.dont_write_bytecode = True", src)

        rep = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig(force_clean_room=True))
        rendered = json.dumps(rep, allow_nan=False)
        self.assertNotRegex(rendered, r'(?<![0-9A-Za-z_/.-])b[\'"]')
        self.assertIsNone(re.search(r"NaN|Infinity", rendered))


if __name__ == "__main__":
    unittest.main()
