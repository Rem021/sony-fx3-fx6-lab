#!/usr/bin/env python3
"""Phase 123 Unit & Integration Tests:
- Live USB-C UVC 1.5 / UAC 2.0 Streaming (4K30p MJPEG / 1080p60 YUY2 / USB 2.0 480Mbps Auto-Stepdown 720p30) + Clean Feed No-OSD Guard
- Wired CDC-NCM SRT (Caller/Listener, NONE/AES-128/AES-256, ARQ 20..1000ms) & RTMPS TLS 1.3 Live Streaming with Hard-Enforced P12 Wi-Fi-OFF
- Sony CRSDK PTP / PTP-IP (0x054C) Remote Control (0xD2xx Cine EI / Base ISO / Look / P4 ND-Clear Clamp)
- Destructive PTP Flash-Opcode Firewall (0x9280..0x92FF blocked, emmc_mutation_bytes == 0)
- NonRealTimeMeta XML Sidecar, CAMSET Export/Import Roundtrip, 4-Language Web Console Card, and GPE0 mb[60..63] ('UVCS') HUD.

Dual-mode safe:
- Passes 100% in both Local Donor mode and `FX3_FX6_FORCE_CLEAN_ROOM=1` mode.
- Never spawns any QEMU process and never touches port 8768.
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import json
import os
import struct
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

TRIAL_DIR = Path(__file__).resolve().parents[1]
if str(TRIAL_DIR) not in sys.path:
    sys.path.insert(0, str(TRIAL_DIR))

import build_live700  # noqa: E402
import run_fx6_menu_trial  # noqa: E402


def _force_clean_room() -> bool:
    return os.environ.get("FX3_FX6_FORCE_CLEAN_ROOM", "").strip().lower() in ("1", "true", "yes")


class TestPhase123UvcSrtCrsdkPtp(unittest.TestCase):
    def _new_session(self, td: str) -> run_fx6_menu_trial.FX6LiveGpe0Session:
        return run_fx6_menu_trial.FX6LiveGpe0Session(Path(td) / "sess", port=18783)

    def _start_http_server(
        self, td: str
    ) -> tuple[run_fx6_menu_trial.FX6LiveGpe0Session, run_fx6_menu_trial.HardenedThreadingHTTPServer, threading.Thread, str]:
        sess = self._new_session(td)
        handler = run_fx6_menu_trial.make_handler(sess)
        srv = run_fx6_menu_trial.HardenedThreadingHTTPServer(("127.0.0.1", 0), handler)
        t = threading.Thread(target=srv.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
        t.start()
        base = f"http://127.0.0.1:{srv.server_address[1]}"
        return sess, srv, t, base

    @staticmethod
    def _http_get_json(url: str) -> tuple[int, dict]:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))

    @staticmethod
    def _http_get_text(url: str) -> tuple[int, str]:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")

    @staticmethod
    def _http_post_json(url: str, payload: object) -> tuple[int, dict]:
        raw = payload if isinstance(payload, (bytes, bytearray)) else json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=raw,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status, json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as err:
            return err.code, json.loads(err.read().decode("utf-8"))

    def test_p123_01_specs_and_defaults(self) -> None:
        specs = run_fx6_menu_trial.UVC_SRT_CRSDK_PTP_SPECS
        self.assertEqual(
            specs["uvc_modes"],
            ["OFF", "UVC_4K30P_MJPEG_5G", "UVC_1080P60P_YUY2_5G", "UVC_720P30P_MJPEG_USB2_FALLBACK"],
        )
        self.assertEqual(specs["usb_link_speeds"], ["USB3_5G", "USB2_480M"])
        self.assertEqual(specs["uac_audio_spec"], "48kHz_16bit_2ch_PCM")
        self.assertTrue(specs["uvc_clean_feed_enforced"])
        self.assertEqual(specs["srt_modes"], ["OFF", "SRT_CALLER", "SRT_LISTENER"])
        self.assertEqual(specs["srt_pbkeylen_modes"], ["NONE", "AES-128", "AES-256"])
        self.assertEqual(specs["srt_latency_range_ms"], [20, 1000])
        self.assertEqual(specs["rtmps_modes"], ["OFF", "RTMPS_TLS13"])
        self.assertEqual(specs["stream_transport"], "CDC_NCM_WIRED_ETHERNET")
        self.assertTrue(specs["p12_wlan_off_enforced"])
        self.assertEqual(specs["crsdk_ptp_modes"], ["OFF", "USB_PTP", "WIRED_PTPIP"])
        self.assertEqual(specs["crsdk_usb_vid"], "0x054C")
        self.assertEqual(specs["crsdk_ptpip_tcp_port"], 15740)
        self.assertEqual(specs["ptp_flash_firewall_range"], ["0x9280", "0x92FF"])
        self.assertEqual(specs["mailbox_magic"], "0x55564353")
        self.assertEqual(specs["mailbox_slots"], "mb[60..63]")
        self.assertEqual(specs["supported_langs"], ["en", "zh-CN", "zh-TW", "ja"])

        with tempfile.TemporaryDirectory(prefix="fx6_p123_01_") as td:
            sess = self._new_session(td)
            p = sess.get_uvc_srt_crsdk_ptp()
            self.assertEqual(p["uvc_mode"], "OFF")
            self.assertEqual(p["effective_uvc_mode"], "OFF")
            self.assertEqual(p["usb_link_speed"], "USB3_5G")
            self.assertTrue(p["uac_audio_enabled"])
            self.assertEqual(p["uac_audio_spec"], "48kHz_16bit_2ch_PCM")
            self.assertTrue(p["uvc_clean_feed_no_osd"])
            self.assertEqual(p["uvc_osd_burnin_px"], 0)
            self.assertEqual(p["srt_mode"], "OFF")
            self.assertEqual(p["srt_pbkeylen"], "AES-256")
            self.assertEqual(p["srt_latency_ms"], 120)
            self.assertEqual(p["rtmps_mode"], "OFF")
            self.assertTrue(p["p12_wlan_off"])
            self.assertEqual(p["wf12_00342260_hits"], 0)
            self.assertEqual(p["crsdk_ptp_mode"], "OFF")
            self.assertTrue(p["ptp_flash_opcodes_blocked"])
            self.assertEqual(p["emmc_mutation_bytes"], 0)
            self.assertTrue(p["p4_nd_clear_enforced"])
            self.assertEqual(sess.get_status()["uvc_srt_crsdk_ptp"], p)

    def test_p123_02_uvc_4k30p_mjpeg_and_uac_48k_16b_2ch(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p123_02_") as td:
            sess = self._new_session(td)
            res = sess.set_uvc_srt_crsdk_ptp({"uvc_mode": "4k30p", "usb_link_speed": "5gbps"})
            self.assertTrue(res["ok"])
            p = res["uvc_srt_crsdk_ptp"]
            self.assertEqual(p["uvc_mode"], "UVC_4K30P_MJPEG_5G")
            self.assertEqual(p["effective_uvc_mode"], "UVC_4K30P_MJPEG_5G")
            self.assertEqual(p["usb_link_speed"], "USB3_5G")
            self.assertFalse(p["uvc_usb2_stepdown_active"])
            self.assertEqual(p["uvc_resolution"], "3840x2160")
            self.assertEqual(p["uvc_fps"], 30)
            self.assertEqual(p["uvc_codec"], "MJPEG")
            self.assertEqual(p["uvc_bitrate_mbps"], 250)
            self.assertEqual(p["uac_audio_spec"], "48kHz_16bit_2ch_PCM")
            self.assertEqual(p["uac_sample_rate_hz"], 48000)
            self.assertEqual(p["uac_bit_depth"], 16)
            self.assertEqual(p["uac_channels"], 2)

    def test_p123_03_uvc_1080p60_yuy2_and_uac_toggle(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p123_03_") as td:
            sess = self._new_session(td)
            res = sess.set_uvc_srt_crsdk_ptp({"uvc_mode": "1080p60p", "uac_audio_enabled": False})
            self.assertTrue(res["ok"])
            p = res["uvc_srt_crsdk_ptp"]
            self.assertEqual(p["effective_uvc_mode"], "UVC_1080P60P_YUY2_5G")
            self.assertEqual(p["uvc_resolution"], "1920x1080")
            self.assertEqual(p["uvc_fps"], 60)
            self.assertEqual(p["uvc_codec"], "YUY2")
            self.assertEqual(p["uvc_bitrate_mbps"], 400)
            self.assertFalse(p["uac_audio_enabled"])
            self.assertEqual(p["uac_audio_spec"], "OFF")
            self.assertEqual(p["uac_channels"], 0)

    def test_p123_04_usb2_480mbps_automatic_stepdown_and_recovery(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p123_04_") as td:
            sess = self._new_session(td)
            r_step = sess.set_uvc_srt_crsdk_ptp({"uvc_mode": "UVC_4K30P_MJPEG_5G", "usb_link_speed": "USB2_480M"})
            self.assertTrue(r_step["ok"])
            p = r_step["uvc_srt_crsdk_ptp"]
            self.assertEqual(p["uvc_mode"], "UVC_4K30P_MJPEG_5G")
            self.assertEqual(p["effective_uvc_mode"], "UVC_720P30P_MJPEG_USB2_FALLBACK")
            self.assertTrue(p["uvc_usb2_stepdown_active"])
            self.assertEqual(p["uvc_stepdown_reason"], "NON_SUPERSPEED_USB2_480MBPS_STEPDOWN")
            self.assertEqual(p["uvc_resolution"], "1280x720")
            self.assertEqual(p["uvc_fps"], 30)
            self.assertEqual(p["uvc_bitrate_mbps"], 35)

            # Plugging a USB3 5Gbps SuperSpeed cable restores full 4K30p
            r_rec = sess.set_uvc_srt_crsdk_ptp({"usb_link_speed": "USB3_5G"})
            self.assertTrue(r_rec["ok"])
            self.assertEqual(r_rec["uvc_srt_crsdk_ptp"]["effective_uvc_mode"], "UVC_4K30P_MJPEG_5G")
            self.assertFalse(r_rec["uvc_srt_crsdk_ptp"]["uvc_usb2_stepdown_active"])

            # 1080p60 YUY2 also steps down on USB2 480Mbps
            r_step2 = sess.set_uvc_srt_crsdk_ptp({"uvc_mode": "UVC_1080P60P_YUY2_5G", "usb_link_speed": "non_superspeed"})
            self.assertTrue(r_step2["ok"])
            self.assertEqual(r_step2["uvc_srt_crsdk_ptp"]["effective_uvc_mode"], "UVC_720P30P_MJPEG_USB2_FALLBACK")
            self.assertTrue(r_step2["uvc_srt_crsdk_ptp"]["uvc_usb2_stepdown_active"])

    def test_p123_05_uvc_clean_feed_no_osd_guard_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p123_05_") as td:
            sess = self._new_session(td)
            for bad_payload in (
                {"uvc_bake_osd": True},
                {"bake_osd_into_uvc": True},
                {"uvc_clean_feed_no_osd": False},
            ):
                err = sess.set_uvc_srt_crsdk_ptp(bad_payload)
                self.assertFalse(err["ok"])
                self.assertEqual(err["error"], "uvc_osd_burnin_blocked")
                self.assertTrue(err["uvc_clean_feed_no_osd"])
                self.assertEqual(err["uvc_osd_burnin_px"], 0)
            self.assertEqual(sess.get_uvc_srt_crsdk_ptp()["uvc_osd_blocked_count"], 3)

    def test_p123_06_invalid_uvc_inputs_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p123_06_") as td:
            sess = self._new_session(td)
            for bad, exp_err in (
                ({"uvc_mode": "UVC_8K120"}, "invalid_uvc_mode"),
                ({"uvc_mode": 123}, "invalid_uvc_mode"),
                ({"usb_link_speed": "USB1_12M"}, "invalid_usb_link_speed"),
                ({"uac_audio_enabled": "yes"}, "invalid_uac_audio_enabled"),
            ):
                err = sess.set_uvc_srt_crsdk_ptp(bad)
                self.assertFalse(err["ok"])
                self.assertEqual(err["error"], exp_err)

    def test_p123_07_wired_cdc_ncm_srt_caller_listener_aes128_256_arq(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p123_07_") as td:
            sess = self._new_session(td)
            r1 = sess.set_uvc_srt_crsdk_ptp({
                "srt_mode": "caller",
                "srt_pbkeylen": "aes128",
                "srt_latency_ms": 20,
                "stream_bitrate_mbps": 25,
            })
            self.assertTrue(r1["ok"])
            p1 = r1["uvc_srt_crsdk_ptp"]
            self.assertEqual(p1["srt_mode"], "SRT_CALLER")
            self.assertEqual(p1["srt_pbkeylen"], "AES-128")
            self.assertEqual(p1["srt_pbkeylen_bytes"], 16)
            self.assertEqual(p1["srt_latency_ms"], 20)
            self.assertTrue(p1["srt_arq_enabled"])
            self.assertEqual(p1["stream_transport"], "CDC_NCM_WIRED_ETHERNET")
            self.assertTrue(p1["p12_wlan_off"])
            self.assertEqual(p1["wf12_00342260_hits"], 0)

            r2 = sess.set_uvc_srt_crsdk_ptp({
                "srt_mode": "listener",
                "srt_pbkeylen": "aes256",
                "srt_latency_ms": 1000,
            })
            self.assertTrue(r2["ok"])
            p2 = r2["uvc_srt_crsdk_ptp"]
            self.assertEqual(p2["srt_mode"], "SRT_LISTENER")
            self.assertEqual(p2["srt_pbkeylen"], "AES-256")
            self.assertEqual(p2["srt_pbkeylen_bytes"], 32)
            self.assertEqual(p2["srt_latency_ms"], 1000)

            r3 = sess.set_uvc_srt_crsdk_ptp({"srt_pbkeylen": "NONE"})
            self.assertTrue(r3["ok"])
            self.assertEqual(r3["uvc_srt_crsdk_ptp"]["srt_pbkeylen_bytes"], 0)

    def test_p123_08_srt_bounds_and_invalid_inputs_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p123_08_") as td:
            sess = self._new_session(td)
            for bad_lat in (19, 1001, 120.5, True, "abc", float("nan")):
                err = sess.set_uvc_srt_crsdk_ptp({"srt_latency_ms": bad_lat})
                self.assertFalse(err["ok"])
                self.assertEqual(err["error"], "invalid_srt_latency_ms")
            for bad_br in (0, 51, 12.2, False, "fast"):
                err = sess.set_uvc_srt_crsdk_ptp({"stream_bitrate_mbps": bad_br})
                self.assertFalse(err["ok"])
                self.assertEqual(err["error"], "invalid_stream_bitrate_mbps")
            self.assertEqual(sess.set_uvc_srt_crsdk_ptp({"srt_mode": "SRT_RENDEZVOUS"})["error"], "invalid_srt_mode")
            self.assertEqual(sess.set_uvc_srt_crsdk_ptp({"srt_pbkeylen": "AES-512"})["error"], "invalid_srt_pbkeylen")

    def test_p123_09_rtmps_tls13_required_and_plain_rtmp_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p123_09_") as td:
            sess = self._new_session(td)
            r_ok = sess.set_uvc_srt_crsdk_ptp({"rtmps_mode": "rtmps", "stream_bitrate_mbps": 18})
            self.assertTrue(r_ok["ok"])
            self.assertEqual(r_ok["uvc_srt_crsdk_ptp"]["rtmps_mode"], "RTMPS_TLS13")
            self.assertEqual(r_ok["uvc_srt_crsdk_ptp"]["rtmps_tls_version"], "TLS_1_3")
            self.assertEqual(r_ok["uvc_srt_crsdk_ptp"]["stream_bitrate_mbps"], 18)

            for bad_rtmp in (
                {"rtmps_mode": "rtmp"},
                {"rtmps_mode": "rtmp_plain"},
                {"rtmps_mode": "RTMPS_TLS13", "use_tls": False},
            ):
                err = sess.set_uvc_srt_crsdk_ptp(bad_rtmp)
                self.assertFalse(err["ok"])
                self.assertEqual(err["error"], "rtmps_tls13_required")

    def test_p123_10_p12_wlan_off_hard_enforced_rejects_wifi_and_bt(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p123_10_") as td:
            sess = self._new_session(td)
            for wifi_req in (
                {"use_wifi": True},
                {"enable_wlan": True},
                {"enable_wifi": True},
                {"enable_bt": True},
                {"p12_wlan_off": False},
                {"stream_interface": "wlan0"},
                {"network_interface": "wifi"},
            ):
                err = sess.set_uvc_srt_crsdk_ptp(wifi_req)
                self.assertFalse(err["ok"])
                self.assertEqual(err["error"], "p12_wlan_off_enforced")
                self.assertTrue(err["p12_wlan_off"])
                self.assertEqual(err["wf12_00342260_hits"], 0)
            p = sess.get_uvc_srt_crsdk_ptp()
            self.assertEqual(p["p12_blocked_count"], 7)
            self.assertTrue(p["p12_wlan_off"])
            self.assertEqual(p["wf12_00342260_hits"], 0)

    def test_p123_11_crsdk_ptp_and_ptpip_modes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p123_11_") as td:
            sess = self._new_session(td)
            r1 = sess.set_uvc_srt_crsdk_ptp({"crsdk_ptp_mode": "usb"})
            self.assertTrue(r1["ok"])
            self.assertEqual(r1["uvc_srt_crsdk_ptp"]["crsdk_ptp_mode"], "USB_PTP")
            self.assertEqual(r1["uvc_srt_crsdk_ptp"]["crsdk_usb_vid"], "0x054C")

            r2 = sess.set_uvc_srt_crsdk_ptp({"crsdk_ptp_mode": "ptpip"})
            self.assertTrue(r2["ok"])
            self.assertEqual(r2["uvc_srt_crsdk_ptp"]["crsdk_ptp_mode"], "WIRED_PTPIP")
            self.assertEqual(r2["uvc_srt_crsdk_ptp"]["crsdk_ptpip_tcp_port"], 15740)

            err = sess.set_uvc_srt_crsdk_ptp({"crsdk_ptp_mode": "BLE_PTP"})
            self.assertFalse(err["ok"])
            self.assertEqual(err["error"], "invalid_crsdk_ptp_mode")

    def test_p123_12_crsdk_safe_d2xx_opcodes_cine_ei_and_look_sync(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p123_12_") as td:
            sess = self._new_session(td)
            for op_hex, prop_name in run_fx6_menu_trial.CRSDK_SAFE_D2XX_OPCODES.items():
                r = sess.set_uvc_srt_crsdk_ptp({"crsdk_ptp_mode": "WIRED_PTPIP", "ptp_opcode": f"0x{op_hex:04X}"})
                self.assertTrue(r["ok"])
                self.assertEqual(r["uvc_srt_crsdk_ptp"]["crsdk_last_safe_opcode"], f"0x{op_hex:04X}")
                self.assertEqual(r["uvc_srt_crsdk_ptp"]["crsdk_last_safe_prop"], prop_name)

            r_ei = sess.set_uvc_srt_crsdk_ptp({
                "ptp_opcode": 0xD210,
                "crsdk_cine_ei_base": "12800",
                "crsdk_ei_index": 25600,
                "crsdk_base_look": "S-Log3 / S-Gamut3.Cine",
            })
            self.assertTrue(r_ei["ok"])
            self.assertEqual(sess.cine_ei_base, "12800")
            self.assertEqual(sess.ei_index, 25600)
            self.assertEqual(sess.base_look, "S-Log3 / S-Gamut3.Cine")
            self.assertEqual(r_ei["uvc_srt_crsdk_ptp"]["crsdk_cine_ei_base"], "12800")
            self.assertEqual(r_ei["uvc_srt_crsdk_ptp"]["crsdk_ei_index"], 25600)
            self.assertEqual(r_ei["uvc_srt_crsdk_ptp"]["crsdk_base_look"], "S-Log3 / S-Gamut3.Cine")

    def test_p123_13_crsdk_0xd224_p4_nd_clear_clamp(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p123_13_") as td:
            sess = self._new_session(td)
            r = sess.set_uvc_srt_crsdk_ptp({
                "crsdk_ptp_mode": "USB_PTP",
                "ptp_opcode": "0xD224",
                "crsdk_nd_preset": "1/16",
            })
            self.assertTrue(r["ok"])
            self.assertTrue(r["p4_nd_clear_enforced"])
            self.assertTrue(r["crsdk_nd_clamped"])
            self.assertEqual(sess.cell_vals[3], 0)
            self.assertEqual(r["uvc_srt_crsdk_ptp"]["crsdk_nd_preset"], "Clear [FX3 P4 Locked]")
            self.assertEqual(r["uvc_srt_crsdk_ptp"]["crsdk_nd_clamp_count"], 1)
            self.assertGreaterEqual(sess.p4_lock_attempts, 1)

            # Requesting Clear does not increment clamp count
            r2 = sess.set_uvc_srt_crsdk_ptp({"ptp_opcode": "0xD224", "crsdk_nd_preset": "Clear"})
            self.assertTrue(r2["ok"])
            self.assertFalse(r2["crsdk_nd_clamped"])
            self.assertEqual(r2["uvc_srt_crsdk_ptp"]["crsdk_nd_clamp_count"], 1)

    def test_p123_14_destructive_ptp_flash_opcode_firewall_0x9280_0x92ff(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p123_14_") as td:
            sess = self._new_session(td)
            blocked_ops = ("0x9280", "0x9281", "0x9285", "0x92A0", "0x92FF", 0x9201, 0x920F)
            for idx, op in enumerate(blocked_ops, start=1):
                err = sess.set_uvc_srt_crsdk_ptp({"ptp_opcode": op})
                self.assertFalse(err["ok"])
                self.assertEqual(err["error"], "ptp_flash_opcode_blocked")
                self.assertTrue(err["ptp_flash_opcodes_blocked"])
                self.assertEqual(err["emmc_mutation_bytes"], 0)
                self.assertEqual(err["blocked_flash_opcode_count"], idx)

            # Action tokens / boolean flags also blocked fail-closed
            for bad_act in (
                {"firmware_flash": True},
                {"emmc_write": True},
                {"nvram_tamper": True},
                {"crsdk_action": "start_ufu_firmware_flash"},
            ):
                err = sess.set_uvc_srt_crsdk_ptp(bad_act)
                self.assertFalse(err["ok"])
                self.assertEqual(err["error"], "ptp_flash_opcode_blocked")
                self.assertEqual(err["emmc_mutation_bytes"], 0)

            p = sess.get_uvc_srt_crsdk_ptp()
            self.assertEqual(p["blocked_flash_opcode_count"], len(blocked_ops) + 4)
            self.assertFalse(p["persistent_emmc_writes_authorized"])
            self.assertEqual(p["emmc_mutation_bytes"], 0)

    def test_p123_15_unsupported_non_d2xx_ptp_opcodes_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p123_15_") as td:
            sess = self._new_session(td)
            err1 = sess.set_uvc_srt_crsdk_ptp({"ptp_opcode": "0x1001"})
            self.assertFalse(err1["ok"])
            self.assertEqual(err1["error"], "unsupported_ptp_opcode")

            err2 = sess.set_uvc_srt_crsdk_ptp({"ptp_opcode": "not_hex"})
            self.assertFalse(err2["ok"])
            self.assertEqual(err2["error"], "invalid_ptp_opcode")

            err3 = sess.set_uvc_srt_crsdk_ptp({"ptp_opcode": True})
            self.assertFalse(err3["ok"])
            self.assertEqual(err3["error"], "invalid_ptp_opcode")

    def test_p123_16_reset_restores_defaults_and_preserves_invariants(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p123_16_") as td:
            sess = self._new_session(td)
            sess.set_uvc_srt_crsdk_ptp({
                "uvc_mode": "UVC_4K30P_MJPEG_5G",
                "srt_mode": "SRT_CALLER",
                "rtmps_mode": "RTMPS_TLS13",
                "crsdk_ptp_mode": "WIRED_PTPIP",
                "ptp_opcode": "0xD220",
            })
            sess.set_uvc_srt_crsdk_ptp({"ptp_opcode": "0x9280"})
            self.assertEqual(sess.get_uvc_srt_crsdk_ptp()["blocked_flash_opcode_count"], 1)

            r = sess.set_uvc_srt_crsdk_ptp({"reset": True})
            self.assertTrue(r["ok"])
            p = r["uvc_srt_crsdk_ptp"]
            self.assertEqual(p["uvc_mode"], "OFF")
            self.assertEqual(p["srt_mode"], "OFF")
            self.assertEqual(p["rtmps_mode"], "OFF")
            self.assertEqual(p["crsdk_ptp_mode"], "OFF")
            self.assertEqual(p["crsdk_last_safe_opcode"], "0xD210")
            self.assertEqual(p["blocked_flash_opcode_count"], 0)
            self.assertTrue(p["p12_wlan_off"])
            self.assertTrue(p["uvc_clean_feed_no_osd"])
            self.assertTrue(p["ptp_flash_opcodes_blocked"])

    def test_p123_17_mailbox_mb60_63_uvcs_packing_256_bytes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p123_17_") as td:
            sess = self._new_session(td)
            sess.set_uvc_srt_crsdk_ptp({
                "uvc_mode": "UVC_4K30P_MJPEG_5G",
                "usb_link_speed": "USB2_480M",
                "uac_audio_enabled": True,
                "srt_mode": "SRT_CALLER",
                "srt_pbkeylen": "AES-128",
                "srt_latency_ms": 240,
                "rtmps_mode": "RTMPS_TLS13",
                "stream_bitrate_mbps": 22,
                "crsdk_ptp_mode": "WIRED_PTPIP",
                "ptp_opcode": "0xD2C1",
            })
            sess.set_uvc_srt_crsdk_ptp({"ptp_opcode": "0x9280"})
            sess.set_uvc_srt_crsdk_ptp({"use_wifi": True})
            sess.set_uvc_srt_crsdk_ptp({"uvc_bake_osd": True})

            raw_p123 = sess._pack_phase123_mailbox_bytes()
            self.assertEqual(len(raw_p123), 16)
            mb60, mb61, mb62, mb63 = struct.unpack("<4I", raw_p123)
            self.assertEqual(mb63, 0x55564353)  # 'UVCS'
            # mb60 checks
            self.assertEqual((mb60 >> 31) & 1, 1)
            self.assertEqual(mb60 & 0x3, 1)  # req UVC_4K30P_MJPEG_5G
            self.assertEqual((mb60 >> 2) & 0x3, 3)  # eff UVC_720P30P_MJPEG_USB2_FALLBACK
            self.assertEqual((mb60 >> 4) & 1, 1)  # usb2_non_ss
            self.assertEqual((mb60 >> 5) & 1, 1)  # stepdown
            self.assertEqual((mb60 >> 6) & 1, 1)  # uac_en
            self.assertEqual((mb60 >> 7) & 1, 1)  # uvc_clean
            self.assertEqual((mb60 >> 8) & 0x3F, 30)  # fps
            self.assertEqual((mb60 >> 14) & 0x3FF, 35)  # bitrate
            self.assertEqual((mb60 >> 24) & 0xF, 2)  # 2ch PCM
            self.assertEqual((mb60 >> 28) & 1, 1)  # osd_blk
            # mb61 checks
            self.assertEqual((mb61 >> 31) & 1, 1)
            self.assertEqual(mb61 & 0x3, 1)  # SRT_CALLER
            self.assertEqual((mb61 >> 2) & 0x3, 1)  # AES-128
            self.assertEqual((mb61 >> 4) & 0x3FF, 240)
            self.assertEqual((mb61 >> 14) & 1, 1)  # rtmps
            self.assertEqual((mb61 >> 15) & 0x3F, 22)
            self.assertEqual((mb61 >> 21) & 1, 1)  # p12_wlan_off
            self.assertEqual((mb61 >> 22) & 1, 1)  # cdc_ncm_ok
            self.assertEqual((mb61 >> 23) & 0x7F, 1)  # p12_blk_cnt
            self.assertEqual((mb61 >> 30) & 1, 1)  # arq_en
            # mb62 checks
            self.assertEqual((mb62 >> 31) & 1, 1)
            self.assertEqual(mb62 & 0x3, 2)  # WIRED_PTPIP
            self.assertEqual((mb62 >> 2) & 1, 1)  # flash_blk
            self.assertEqual((mb62 >> 3) & 1, 1)  # emmc_zero
            self.assertEqual((mb62 >> 4) & 1, 1)  # p12_ptp
            self.assertEqual((mb62 >> 5) & 1, 1)  # p4_nd_clr
            self.assertEqual((mb62 >> 6) & 0xFF, 0xC1)  # 0xD2C1
            self.assertEqual((mb62 >> 14) & 0x7F, 1)  # blk_flash_cnt

            full_mb = (
                sess._pack_full_mailbox_bytes()
                + sess._pack_phase73_mailbox_bytes()
                + sess._pack_phase81_mailbox_bytes()
                + sess._pack_phase88_mailbox_bytes()
                + sess._pack_phase95_mailbox_bytes()
                + sess._pack_phase102_mailbox_bytes()
                + sess._pack_phase109_mailbox_bytes()
                + sess._pack_phase116_mailbox_bytes()
                + sess._pack_phase123_mailbox_bytes()
            )
            self.assertEqual(len(full_mb), 256)
            self.assertEqual(struct.unpack_from("<I", full_mb, 252)[0], 0x55564353)

    def test_p123_18_xml_sidecar_uvcs_group_and_items(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p123_18_") as td:
            sess = self._new_session(td)
            sess.set_uvc_srt_crsdk_ptp({
                "uvc_mode": "UVC_4K30P_MJPEG_5G",
                "usb_link_speed": "USB2_480M",
                "srt_mode": "SRT_LISTENER",
                "srt_pbkeylen": "AES-256",
                "srt_latency_ms": 180,
                "rtmps_mode": "RTMPS_TLS13",
                "crsdk_ptp_mode": "WIRED_PTPIP",
            })
            sess.set_uvc_srt_crsdk_ptp({"ptp_opcode": "0x9281"})
            sidecar = sess.get_xml_sidecar()
            xml_text = sidecar["xml"]
            root = ET.fromstring(xml_text)
            self.assertIn('name="UvcSrtRtmpsAndCrsdkPtpFirewall"', xml_text)
            items = {el.attrib.get("name"): el.attrib.get("value") for el in root.findall(".//{*}Item")}
            self.assertEqual(items["UvcRequestedMode"], "UVC_4K30P_MJPEG_5G")
            self.assertEqual(items["UvcEffectiveMode"], "UVC_720P30P_MJPEG_USB2_FALLBACK")
            self.assertEqual(items["UvcUsb2StepdownActive"], "true")
            self.assertEqual(items["UvcCleanFeedNoOsd"], "true")
            self.assertEqual(items["SrtMode"], "SRT_LISTENER")
            self.assertEqual(items["SrtPbKeyLen"], "AES-256")
            self.assertEqual(items["SrtArqLatencyMs"], "180")
            self.assertEqual(items["RtmpsMode"], "RTMPS_TLS13")
            self.assertEqual(items["StreamTransport"], "CDC_NCM_WIRED_ETHERNET")
            self.assertEqual(items["P12WlanOff"], "true")
            self.assertEqual(items["Wf12Calls"], "0")
            self.assertEqual(items["CrsdkPtpMode"], "WIRED_PTPIP")
            self.assertEqual(items["CrsdkUsbVid"], "0x054C")
            self.assertEqual(items["PtpFlashOpcodesBlocked"], "true")
            self.assertEqual(items["EmmcMutationBytes"], "0")
            self.assertEqual(items["BlockedFlashOpcodeCount"], "1")
            self.assertEqual(items["P4NdClearEnforced"], "true")

    def test_p123_19_camset_export_import_roundtrip_and_tamper_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p123_19_") as td:
            sess = self._new_session(td)
            sess.set_uvc_srt_crsdk_ptp({
                "uvc_mode": "UVC_1080P60P_YUY2_5G",
                "usb_link_speed": "USB3_5G",
                "uac_audio_enabled": True,
                "srt_mode": "SRT_CALLER",
                "srt_pbkeylen": "AES-128",
                "srt_latency_ms": 90,
                "rtmps_mode": "RTMPS_TLS13",
                "stream_bitrate_mbps": 20,
                "crsdk_ptp_mode": "USB_PTP",
                "ptp_opcode": "0xD21C",
            })
            exported = sess.export_camset_preset()
            self.assertIn("uvc_srt_crsdk_ptp", exported)
            self.assertEqual(exported["uvc_srt_crsdk_ptp"]["uvc_mode"], "UVC_1080P60P_YUY2_5G")
            self.assertEqual(exported["uvc_srt_crsdk_ptp"]["srt_pbkeylen"], "AES-128")

            sess2 = self._new_session(td + "_2")
            imp = sess2.import_camset_preset(exported)
            self.assertTrue(imp["ok"])
            p2 = sess2.get_uvc_srt_crsdk_ptp()
            self.assertEqual(p2["uvc_mode"], "UVC_1080P60P_YUY2_5G")
            self.assertEqual(p2["srt_mode"], "SRT_CALLER")
            self.assertEqual(p2["srt_pbkeylen"], "AES-128")
            self.assertEqual(p2["srt_latency_ms"], 90)
            self.assertEqual(p2["rtmps_mode"], "RTMPS_TLS13")
            self.assertEqual(p2["stream_bitrate_mbps"], 20)
            self.assertEqual(p2["crsdk_ptp_mode"], "USB_PTP")
            self.assertEqual(p2["crsdk_last_safe_opcode"], "0xD21C")

            # Tampered emmc_mutation_bytes -> fail closed
            bad1 = json.loads(json.dumps(exported))
            bad1["uvc_srt_crsdk_ptp"]["emmc_mutation_bytes"] = 4096
            self.assertEqual(sess2.import_camset_preset(bad1)["error"], "ptp_flash_opcode_blocked")

            # Tampered uvc_osd_burnin_px -> fail closed
            bad2 = json.loads(json.dumps(exported))
            bad2["uvc_srt_crsdk_ptp"]["uvc_osd_burnin_px"] = 128
            self.assertEqual(sess2.import_camset_preset(bad2)["error"], "uvc_osd_burnin_blocked")

            # Tampered p12_wlan_off -> fail closed
            bad3 = json.loads(json.dumps(exported))
            bad3["uvc_srt_crsdk_ptp"]["p12_wlan_off"] = False
            self.assertEqual(sess2.import_camset_preset(bad3)["error"], "p12_wlan_off_enforced")

    def test_p123_20_http_get_and_post_uvc_srt_crsdk_ptp(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p123_20_") as td:
            sess, srv, thr, base = self._start_http_server(td)
            try:
                st_code, get_res = self._http_get_json(f"{base}/api/uvc_srt_crsdk_ptp")
                self.assertEqual(st_code, 200)
                self.assertTrue(get_res["ok"])
                self.assertEqual(get_res["uvc_srt_crsdk_ptp"]["uvc_mode"], "OFF")
                self.assertEqual(get_res["specs"]["mailbox_magic"], "0x55564353")

                p_code, post_res = self._http_post_json(
                    f"{base}/api/uvc_srt_crsdk_ptp",
                    {
                        "uvc_mode": "UVC_4K30P_MJPEG_5G",
                        "srt_mode": "SRT_CALLER",
                        "srt_pbkeylen": "AES-256",
                        "srt_latency_ms": 150,
                        "rtmps_mode": "RTMPS_TLS13",
                        "crsdk_ptp_mode": "WIRED_PTPIP",
                        "ptp_opcode": "0xD210",
                    },
                )
                self.assertEqual(p_code, 200)
                self.assertTrue(post_res["ok"])
                self.assertEqual(post_res["uvc_srt_crsdk_ptp"]["effective_uvc_mode"], "UVC_4K30P_MJPEG_5G")
                self.assertEqual(post_res["uvc_srt_crsdk_ptp"]["srt_latency_ms"], 150)
                self.assertEqual(post_res["status"]["uvc_srt_crsdk_ptp"]["crsdk_ptp_mode"], "WIRED_PTPIP")

                x_code, xml_txt = self._http_get_text(f"{base}/api/xml_sidecar")
                self.assertEqual(x_code, 200)
                self.assertIn("UvcSrtRtmpsAndCrsdkPtpFirewall", xml_txt)
            finally:
                srv.shutdown()
                srv.server_close()
                thr.join(timeout=2)

    def test_p123_21_http_malformed_json_and_firewall_rejections(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p123_21_") as td:
            sess, srv, thr, base = self._start_http_server(td)
            try:
                c1, r1 = self._http_post_json(f"{base}/api/uvc_srt_crsdk_ptp", b"{bad-json")
                self.assertEqual(c1, 400)
                self.assertEqual(r1["error"], "invalid_json")

                c2, r2 = self._http_post_json(f"{base}/api/uvc_srt_crsdk_ptp", [1, 2, 3])
                self.assertEqual(c2, 400)
                self.assertEqual(r2["error"], "invalid_json_object")

                c3, r3 = self._http_post_json(f"{base}/api/uvc_srt_crsdk_ptp", {"ptp_opcode": "0x9280"})
                self.assertEqual(c3, 400)
                self.assertEqual(r3["error"], "ptp_flash_opcode_blocked")
                self.assertEqual(r3["emmc_mutation_bytes"], 0)
                self.assertEqual(r3["blocked_flash_opcode_count"], 1)

                c4, r4 = self._http_post_json(f"{base}/api/uvc_srt_crsdk_ptp", {"use_wifi": True})
                self.assertEqual(c4, 400)
                self.assertEqual(r4["error"], "p12_wlan_off_enforced")
                self.assertEqual(r4["wf12_00342260_hits"], 0)

                c5, r5 = self._http_post_json(f"{base}/api/uvc_srt_crsdk_ptp", {"uvc_bake_osd": True})
                self.assertEqual(c5, 400)
                self.assertEqual(r5["error"], "uvc_osd_burnin_blocked")
            finally:
                srv.shutdown()
                srv.server_close()
                thr.join(timeout=2)

    def test_p123_22_cinema_param_ei_and_look_cross_sync(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p123_22_") as td:
            sess = self._new_session(td)
            sess.set_cinema_param("ei", preset="12800")
            sess.set_cinema_param("lut", preset="S-Log3")
            p = sess.get_uvc_srt_crsdk_ptp()
            self.assertEqual(p["crsdk_cine_ei_base"], "12800")
            self.assertEqual(p["crsdk_ei_index"], 12800)
            self.assertEqual(p["crsdk_base_look"], "S-Log3 / S-Gamut3.Cine")

    def test_p123_23_format_uvcs_command_string(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p123_23_") as td:
            sess = self._new_session(td)
            r = sess.set_uvc_srt_crsdk_ptp({
                "uvc_mode": "UVC_4K30P_MJPEG_5G",
                "srt_mode": "SRT_CALLER",
                "srt_pbkeylen": "AES-256",
                "rtmps_mode": "RTMPS_TLS13",
                "crsdk_ptp_mode": "WIRED_PTPIP",
            })
            cmd = r["uvc_srt_crsdk_ptp_cmd"]
            self.assertIn("UVCS uvc=UVC_4K30P_MJPEG_5G", cmd)
            self.assertIn("srt=SRT_CALLER(AES-256,arq=120ms)", cmd)
            self.assertIn("p12_wlan_off=1,wf12=0", cmd)
            self.assertIn("flash_blk=1,emmc=0", cmd)

    def test_p123_24_web_ui_4lang_i18n_card_and_endpoints_present(self) -> None:
        html = run_fx6_menu_trial.HTML_UI
        for token in (
            "phase123-uvc-srt-crsdk-ptp-card",
            "p123-lang-en",
            "p123-lang-zh-CN",
            "p123-lang-zh-TW",
            "p123-lang-ja",
            "P123_I18N",
            "setP123Lang",
            "syncPhase123UvcSrtCrsdkPtpUI",
            "setPhase123State",
            "/api/uvc_srt_crsdk_ptp",
            "简体中文",
            "繁體中文",
            "日本語",
            "0x9280",
            "0x054C",
        ):
            self.assertIn(token, html)

    def test_p123_25_guest_c_uvcs_tokens_and_zero_heap_no_printf(self) -> None:
        c_src = (TRIAL_DIR / "src" / "fx6_live_guest.c").read_text(encoding="utf-8")
        for token in (
            "0x55564353u",
            "fx6_render_phase123_uvc_srt_crsdk_ptp_overlay",
            "UVCS=0x%08x:0x%08x:0x%08x",
            "g_live_p123_uvc_uac = uvc_w | (1u << 7);",
            "g_live_p123_srt_rtmps = mb[61] | (1u << 21) | (1u << 22);",
            "g_live_p123_crsdk_ptp = mb[62] | (1u << 2) | (1u << 3) | (1u << 4);",
            "g_live_p123_uvc_uac = 0x820000c0u;",
            "g_live_p123_srt_rtmps = 0x80660788u;",
            "g_live_p123_crsdk_ptp = 0x8000043cu;",
        ):
            self.assertIn(token, c_src)
        self.assertNotIn("8768", c_src)
        idx_start = c_src.index("fx6_render_phase123_uvc_srt_crsdk_ptp_overlay")
        idx_end = c_src.index("/* ---------------- Frame Cache", idx_start)
        fn_body = c_src[idx_start:idx_end]
        for forbidden in ("malloc(", "calloc(", "realloc(", "printf("):
            self.assertNotIn(forbidden, fn_body)

    def test_p123_26_guest_c_compiles_cleanly_for_arm64(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p123_26_") as td:
            out_so = Path(td) / "libfx6_live_guest.so"
            res = build_live700.compile_shim(build_live700.DEFAULT_ZIG, out_so)
            self.assertTrue(out_so.exists())
            self.assertGreater(res["bytes"], 500000)

    def test_p123_27_port_isolation_no_8768_and_scoped_18783(self) -> None:
        py_src = (TRIAL_DIR / "run_fx6_menu_trial.py").read_text(encoding="utf-8")
        idx_p123 = py_src.index("Phase 123: Live USB-C UVC 1.5")
        idx_gpe = py_src.index("def _png_chunk", idx_p123)
        self.assertNotIn("8768", py_src[idx_p123:idx_gpe])
        scoped = run_fx6_menu_trial.resolve_port_scoped_workdir(18783, Path("/private/tmp/fx6_p123_trial_18783"))
        self.assertEqual(str(scoped), "/private/tmp/fx6_p123_trial_18783")

    def test_p123_28_ram_only_zero_persistent_emmc_and_wf12(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p123_28_") as td:
            sess = self._new_session(td)
            res = sess.set_uvc_srt_crsdk_ptp({
                "uvc_mode": "UVC_4K30P_MJPEG_5G",
                "srt_mode": "SRT_CALLER",
                "rtmps_mode": "RTMPS_TLS13",
                "crsdk_ptp_mode": "WIRED_PTPIP",
            })
            self.assertTrue(res["ok"])
            self.assertFalse(res["uvc_srt_crsdk_ptp"]["persistent_emmc_writes_authorized"])
            self.assertEqual(res["emmc_mutation_bytes"], 0)
            self.assertEqual(res["wf12_00342260_hits"], 0)
            self.assertEqual(sess.get_mc_fleet_sdi_c2pa()["cnflasha_writes"], 0)

    def test_p123_29_uvc_alias_normalization_and_direct_720p_fallback(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p123_29_") as td:
            sess = self._new_session(td)
            r = sess.set_uvc_srt_crsdk_ptp({"uvc_mode": "usb2_fallback", "usb_link_speed": "USB3_5G"})
            self.assertTrue(r["ok"])
            p = r["uvc_srt_crsdk_ptp"]
            self.assertEqual(p["effective_uvc_mode"], "UVC_720P30P_MJPEG_USB2_FALLBACK")
            self.assertFalse(p["uvc_usb2_stepdown_active"])
            self.assertEqual(p["uvc_resolution"], "1280x720")

    def test_p123_30_invalid_crsdk_ei_and_look_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p123_30_") as td:
            sess = self._new_session(td)
            e1 = sess.set_uvc_srt_crsdk_ptp({"crsdk_cine_ei_base": "3200"})
            self.assertEqual(e1["error"], "invalid_crsdk_cine_ei_base")
            e2 = sess.set_uvc_srt_crsdk_ptp({"crsdk_ei_index": 99999})
            self.assertEqual(e2["error"], "invalid_crsdk_ei_index")
            e3 = sess.set_uvc_srt_crsdk_ptp({"crsdk_base_look": "UnknownLook"})
            self.assertEqual(e3["error"], "invalid_crsdk_base_look")

    def test_p123_31_combined_invalid_payload_types(self) -> None:
        ok, _, err = run_fx6_menu_trial.validate_uvc_srt_crsdk_ptp_patch(["not", "dict"])
        self.assertFalse(ok)
        self.assertEqual(err["error"], "invalid_uvc_srt_crsdk_ptp")

    def test_p123_32_dual_mode_clean_room_and_local_donor_parity(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p123_32_") as td:
            sess = self._new_session(td)
            mode = "CLEAN_ROOM" if _force_clean_room() else "LOCAL_DONOR"
            self.assertIn(mode, ("CLEAN_ROOM", "LOCAL_DONOR"))
            r = sess.set_uvc_srt_crsdk_ptp({
                "uvc_mode": "UVC_4K30P_MJPEG_5G",
                "usb_link_speed": "USB2_480M",
                "srt_mode": "SRT_CALLER",
                "srt_pbkeylen": "AES-256",
                "srt_latency_ms": 120,
                "rtmps_mode": "RTMPS_TLS13",
                "crsdk_ptp_mode": "WIRED_PTPIP",
                "ptp_opcode": "0xD210",
            })
            self.assertTrue(r["ok"])
            p = r["uvc_srt_crsdk_ptp"]
            self.assertEqual(p["effective_uvc_mode"], "UVC_720P30P_MJPEG_USB2_FALLBACK")
            self.assertTrue(p["uvc_clean_feed_no_osd"])
            self.assertTrue(p["p12_wlan_off"])
            self.assertTrue(p["ptp_flash_opcodes_blocked"])
            self.assertEqual(p["emmc_mutation_bytes"], 0)
            self.assertEqual(p["wf12_00342260_hits"], 0)


if __name__ == "__main__":
    unittest.main()
