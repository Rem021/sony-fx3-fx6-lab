#!/usr/bin/env python3
"""Phase 129 Unit & Integration Tests:
- XAVC MXF OP1a <-> MP4 RDD-18/UMID Lossless Container Bridge (SMPTE 330M 32B UMID + CRC32 RDD-18 KLV, eMMC=0B)
- SMPTE ST 2059-2 PTPv2 (<500ns) vs 15-Pin Multi-Terminal LTC Glitch-Free Holdover + Hard P12 Wi-Fi-OFF
- TSL UMD v5.0 Studio Broadcast Red/Green Tally (UDP & TCP DLE/STX 0xFE 0x02) + 16-Char Dynamic Camera UMD + Stealth Mute
- NonRealTimeMeta XML Sidecar, /api/camset Export/Import Roundtrip, 4-Language Web Console Card, and GPE0 mb[64..71] ('MXFT') HUD.

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


class TestPhase129MxfPtpv2TslTally(unittest.TestCase):
    def _new_session(self, td: str) -> run_fx6_menu_trial.FX6LiveGpe0Session:
        return run_fx6_menu_trial.FX6LiveGpe0Session(Path(td) / "sess", port=18784)

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

    def test_p129_01_specs_and_defaults(self) -> None:
        specs = run_fx6_menu_trial.MXF_PTPV2_TALLY_SPECS
        self.assertEqual(
            specs["container_modes"],
            ["MP4_ISOBMFF_RTMD", "MXF_OP1A_RDD09_WRAP", "DUAL_MP4_PLUS_MXF_SIDECAR"],
        )
        self.assertEqual(specs["smpte330_umid_bytes"], 32)
        self.assertEqual(specs["ptpv2_standard"], "SMPTE_ST_2059_2")
        self.assertEqual(specs["ptpv2_default_domain"], 127)
        self.assertEqual(specs["ptpv2_max_offset_ns"], 499)
        self.assertTrue(specs["p12_wlan_off_enforced"])
        self.assertEqual(specs["tally_states"], ["OFF", "PVW_GREEN", "PGM_RED", "PGM_PLUS_PVW"])
        self.assertEqual(specs["tsl_framing_modes"], ["UDP", "TCP_DLE_STX"])
        self.assertEqual(specs["tsl_umd_version"], "5.0")
        self.assertEqual(specs["umd_max_chars"], 16)
        self.assertEqual(specs["mailbox_magic"], "0x4D584654")
        self.assertEqual(specs["mailbox_slots"], "mb[64..67]")
        self.assertEqual(specs["supported_langs"], ["en", "zh-CN", "zh-TW", "ja"])

        with tempfile.TemporaryDirectory(prefix="fx6_p129_01_") as td:
            sess = self._new_session(td)
            p = sess.get_mxf_ptpv2_tally()
            self.assertEqual(p["container_mode"], "MP4_ISOBMFF_RTMD")
            self.assertEqual(p["essence_reencode_loss"], 0)
            self.assertEqual(p["emmc_mutation_bytes"], 0)
            self.assertFalse(p["persistent_emmc_writes_authorized"])
            self.assertTrue(p["rdd18_klv_crc32_valid"])
            self.assertEqual(p["effective_sync_mode"], "OFF")
            self.assertTrue(p["p12_wlan_off"])
            self.assertEqual(p["wf12_00342260_hits"], 0)
            self.assertEqual(p["tally_state"], "OFF")
            self.assertFalse(p["stealth_led_mute"])
            self.assertTrue(p["osd_tally_indicator"])
            self.assertEqual(p["fx6_green_gpio_faults"], 0)
            self.assertEqual(p["umd_camera_index"], 1)
            self.assertEqual(p["umd_camera_slot"], "CAM1")
            self.assertEqual(p["umd_label"], "FX3-CAM1-STUDIO")
            self.assertTrue(p["tsl_packet_valid"])

    def test_p129_02_smpte330_umid_format_and_uniqueness(self) -> None:
        u1 = run_fx6_menu_trial.build_p129_smpte330_umid_hex(cam_id="A", reel_num=1, clip_seq=1)
        u2 = run_fx6_menu_trial.build_p129_smpte330_umid_hex(cam_id="A", reel_num=1, clip_seq=2)
        u3 = run_fx6_menu_trial.build_p129_smpte330_umid_hex(cam_id="B", reel_num=1, clip_seq=1)
        self.assertEqual(len(u1), 64)
        self.assertTrue(u1.startswith(run_fx6_menu_trial.SMPTE_330M_BASIC_UMID_PREFIX))
        self.assertNotEqual(u1, u2)
        self.assertNotEqual(u1, u3)

    def test_p129_03_rdd18_klv_roundtrip_and_crc32_tamper_detection(self) -> None:
        pkt_hex = run_fx6_menu_trial.encode_p129_rdd18_klv_hex(
            exposure_index=12800,
            base_iso=12800,
            gamma_eq="s-log3-cine",
            primaries="s-gamut3-cine",
            fps_x1000=24000,
            shutter_angle_x10=1800,
            wb_kelvin=3200,
            cube_lut_path="Sony_SLog3.cube",
        )
        dec = run_fx6_menu_trial.decode_p129_rdd18_klv_hex(pkt_hex)
        self.assertTrue(dec["valid"])
        self.assertTrue(dec["crc32_valid"])
        self.assertEqual(dec["exposure_index"], 12800)
        self.assertEqual(dec["base_iso"], 12800)
        self.assertEqual(dec["capture_gamma_equation"], "s-log3-cine")
        self.assertEqual(dec["capture_color_primaries"], "s-gamut3-cine")
        self.assertEqual(dec["wb_kelvin"], 3200)
        self.assertEqual(dec["cube_lut_path"], "Sony_SLog3.cube")

        # Flip last byte -> CRC32 must fail
        corrupted = pkt_hex[:-2] + f"{int(pkt_hex[-2:], 16) ^ 0xFF:02x}"
        bad = run_fx6_menu_trial.decode_p129_rdd18_klv_hex(corrupted)
        self.assertFalse(bad["valid"])
        self.assertFalse(bad["crc32_valid"])

    def test_p129_04_mxf_container_modes_and_aliases(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p129_04_") as td:
            sess = self._new_session(td)
            for alias, canonical in (
                ("op1a", "MXF_OP1A_RDD09_WRAP"),
                ("dual", "DUAL_MP4_PLUS_MXF_SIDECAR"),
                ("mp4", "MP4_ISOBMFF_RTMD"),
            ):
                res = sess.set_mxf_ptpv2_tally({"container_mode": alias})
                self.assertTrue(res["ok"])
                p = res["mxf_ptpv2_tally"]
                self.assertEqual(p["container_mode"], canonical)
                self.assertEqual(p["essence_reencode_loss"], 0)
                self.assertEqual(p["frame_essence_reencode_loss"], 0)
                self.assertTrue(p["essence_sha256_preserved"])
                self.assertEqual(p["dropped_klv_tags"], 0)
                self.assertEqual(p["emmc_mutation_bytes"], 0)

    def test_p129_05_raw_mxf_slot_write_and_spvc_spoof_blocked(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p129_05_") as td:
            sess = self._new_session(td)
            r1 = sess.set_mxf_ptpv2_tally({"raw_mxf_on_mp4_slot": True})
            self.assertFalse(r1["ok"])
            self.assertEqual(r1["error"], "raw_mxf_slot_write_blocked")
            self.assertEqual(r1["emmc_mutation_bytes"], 0)
            self.assertEqual(r1["mxf_blocked_count"], 1)

            r2 = sess.set_mxf_ptpv2_tally({"spoof_spvc": True})
            self.assertFalse(r2["ok"])
            self.assertEqual(r2["error"], "spvc_cert_spoof_blocked")
            self.assertEqual(r2["emmc_mutation_bytes"], 0)
            self.assertEqual(r2["mxf_blocked_count"], 2)

            r3 = sess.set_mxf_ptpv2_tally({"emmc_write": True})
            self.assertFalse(r3["ok"])
            self.assertEqual(r3["error"], "spvc_cert_spoof_blocked")
            self.assertEqual(r3["mxf_blocked_count"], 3)

    def test_p129_06_cross_codec_lossless_rewrap_blocked(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p129_06_") as td:
            sess = self._new_session(td)
            # Valid same-family Long-GOP rewrap succeeds
            ok_res = sess.set_mxf_ptpv2_tally({
                "source_codec": "XAVC_S_LONG_422",
                "target_codec": "XAVC_L_MXF_422",
            })
            self.assertTrue(ok_res["ok"])

            # Cross-family Intra -> Long-GOP lossless rewrap blocked
            bad_res = sess.set_mxf_ptpv2_tally({
                "source_codec": "XAVC_S_I_422_10B",
                "target_codec": "XAVC_L_MXF_422",
            })
            self.assertFalse(bad_res["ok"])
            self.assertEqual(bad_res["error"], "cross_codec_lossless_rewrap_blocked")
            self.assertEqual(bad_res["essence_reencode_loss"], 0)

    def test_p129_07_ptpv2_servo_submicrosecond_and_validation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p129_07_") as td:
            sess = self._new_session(td)
            res = sess.set_mxf_ptpv2_tally({
                "sync_mode": "PTPV2_SLAVE_WIRED",
                "ptpv2_grandmaster_id": "00-1b-1b-ff-fe-20-59-aa",
                "ptpv2_domain": 127,
                "ethernet_link_up": True,
                "offset_ns": 142,
            })
            self.assertTrue(res["ok"])
            p = res["mxf_ptpv2_tally"]
            self.assertEqual(p["effective_sync_mode"], "PTPV2_SLAVE_WIRED")
            self.assertEqual(p["ptpv2_grandmaster_id"], "00:1B:1B:FF:FE:20:59:AA")
            self.assertEqual(p["offset_ns"], 142)
            self.assertTrue(p["servo_locked"])
            self.assertFalse(p["ltc_holdover_active"])
            self.assertEqual(p["sync_transport"], "CDC_NCM_WIRED_ETHERNET")

            # Exceeding 499ns ST 2059-2 budget fails closed
            bad_off = sess.set_mxf_ptpv2_tally({"offset_ns": 500})
            self.assertFalse(bad_off["ok"])
            self.assertEqual(bad_off["error"], "ptpv2_offset_budget_exceeded")

            bad_gm = sess.set_mxf_ptpv2_tally({"ptpv2_grandmaster_id": "NOT_EUI64"})
            self.assertFalse(bad_gm["ok"])
            self.assertEqual(bad_gm["error"], "invalid_ptpv2_grandmaster_id")

            bad_dom = sess.set_mxf_ptpv2_tally({"ptpv2_domain": 256})
            self.assertFalse(bad_dom["ok"])
            self.assertEqual(bad_dom["error"], "invalid_ptpv2_domain")

    def test_p129_08_ptpv2_to_ltc_glitch_free_holdover_and_recovery(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p129_08_") as td:
            sess = self._new_session(td)
            r1 = sess.set_mxf_ptpv2_tally({
                "sync_mode": "PTPV2_SLAVE_WIRED",
                "ethernet_link_up": True,
                "ltc_multiterminal_attached": True,
                "offset_ns": 115,
            })
            self.assertTrue(r1["ok"])
            self.assertEqual(r1["mxf_ptpv2_tally"]["effective_sync_mode"], "PTPV2_SLAVE_WIRED")

            # Unplug wired Ethernet -> immediate glitch-free Multi-Terminal LTC holdover
            r2 = sess.set_mxf_ptpv2_tally({"ethernet_link_up": False})
            self.assertTrue(r2["ok"])
            p2 = r2["mxf_ptpv2_tally"]
            self.assertEqual(p2["effective_sync_mode"], "LTC_MULTITERMINAL_FALLBACK")
            self.assertTrue(p2["servo_locked"])
            self.assertTrue(p2["ltc_holdover_active"])
            self.assertTrue(p2["glitch_free_holdover"])
            self.assertEqual(p2["dropped_frames"], 0)
            self.assertLess(p2["holdover_slip_frames"], 0.05)
            self.assertEqual(p2["sync_transport"], "15PIN_MULTITERMINAL_LTC")

            # Re-plug Ethernet -> seamless relock to PTPv2
            r3 = sess.set_mxf_ptpv2_tally({"ethernet_link_up": True})
            self.assertTrue(r3["ok"])
            p3 = r3["mxf_ptpv2_tally"]
            self.assertEqual(p3["effective_sync_mode"], "PTPV2_SLAVE_WIRED")
            self.assertFalse(p3["ltc_holdover_active"])

    def test_p129_09_ptpip_confusion_uart_conflict_and_ltc_absent_blocked(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p129_09_") as td:
            sess = self._new_session(td)
            r1 = sess.set_mxf_ptpv2_tally({"ptp_ip_15740_as_st2059": True})
            self.assertFalse(r1["ok"])
            self.assertEqual(r1["error"], "ptpip_not_st2059_ptpv2")

            r2 = sess.set_mxf_ptpv2_tally({"uart_boot_active": True})
            self.assertFalse(r2["ok"])
            self.assertEqual(r2["error"], "uart_boot_ltc_pin_conflict")

            r3 = sess.set_mxf_ptpv2_tally({
                "sync_mode": "LTC_MULTITERMINAL_FALLBACK",
                "ltc_multiterminal_attached": False,
            })
            self.assertFalse(r3["ok"])
            self.assertEqual(r3["error"], "ltc_source_absent")

    def test_p129_10_p12_wlan_off_hard_enforced(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p129_10_") as td:
            sess = self._new_session(td)
            for bad_patch in (
                {"use_wifi": True},
                {"enable_wlan": True},
                {"enable_bt": True},
                {"p12_wlan_off": False},
                {"network_interface": "wlan0"},
                {"tsl_interface": "wifi"},
            ):
                res = sess.set_mxf_ptpv2_tally(bad_patch)
                self.assertFalse(res["ok"])
                self.assertEqual(res["error"], "p12_wlan_off_enforced")
                self.assertTrue(res["p12_wlan_off"])
                self.assertEqual(res["wf12_00342260_hits"], 0)
            self.assertEqual(sess.get_mxf_ptpv2_tally()["p12_blocked_count"], 6)

    def test_p129_11_tsl_umd_v5_udp_and_tcp_dle_stx_codec(self) -> None:
        # UDP v5.0 packet
        udp_hex = run_fx6_menu_trial.encode_p129_tsl_umd_v5_packet(
            screen=0,
            index=3,
            tally_state="PGM_RED",
            brightness=3,
            text="CAM-C JIB 35GM",
            tcp_dle_stx=False,
        )
        dec_udp = run_fx6_menu_trial.decode_p129_tsl_umd_v5_packet(udp_hex, tcp_dle_stx=False)
        self.assertTrue(dec_udp["valid"])
        self.assertEqual(dec_udp["index"], 3)
        self.assertEqual(dec_udp["tally_state"], "PGM_RED")
        self.assertEqual(dec_udp["text"], "CAM-C JIB 35GM")
        self.assertFalse(dec_udp["tcp_dle_stx"])

        # TCP DLE/STX (0xFE 0x02) packet with index=0xFE to verify byte-stuffing
        tcp_hex = run_fx6_menu_trial.encode_p129_tsl_umd_v5_packet(
            screen=0,
            index=0x00FE,
            tally_state="PVW_GREEN",
            brightness=2,
            text="STUFF\xfeTEST"[:16],
            tcp_dle_stx=True,
        )
        self.assertTrue(tcp_hex.startswith("fe02"))
        dec_tcp = run_fx6_menu_trial.decode_p129_tsl_umd_v5_packet(tcp_hex, tcp_dle_stx=True)
        self.assertTrue(dec_tcp["valid"])
        self.assertEqual(dec_tcp["index"], 0x00FE)
        self.assertEqual(dec_tcp["tally_state"], "PVW_GREEN")
        self.assertTrue(dec_tcp["tcp_dle_stx"])

    def test_p129_12_tsl_packet_hex_injection_and_rejection(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p129_12_") as td:
            sess = self._new_session(td)
            pkt = run_fx6_menu_trial.encode_p129_tsl_umd_v5_packet(
                index=5,
                tally_state="PGM_PLUS_PVW",
                text="CAM5-DOLLY-MAIN",
                tcp_dle_stx=True,
            )
            res = sess.set_mxf_ptpv2_tally({"tsl_packet_hex": pkt})
            self.assertTrue(res["ok"])
            p = res["mxf_ptpv2_tally"]
            self.assertEqual(p["tally_state"], "PGM_PLUS_PVW")
            self.assertEqual(p["umd_camera_index"], 5)
            self.assertEqual(p["umd_camera_slot"], "CAM5")
            self.assertEqual(p["umd_label"], "CAM5-DOLLY-MAIN")
            self.assertEqual(p["tsl_framing"], "TCP_DLE_STX")

            bad = sess.set_mxf_ptpv2_tally({"tsl_packet_hex": "050000"})
            self.assertFalse(bad["ok"])
            self.assertEqual(bad["error"], "invalid_tsl_umd_v5_packet")

    def test_p129_13_stealth_mute_and_fx6_green_gpio_zero_fault(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p129_13_") as td:
            sess = self._new_session(td)
            # PVW_GREEN keeps physical red LEDs OFF and OSD border GREEN
            r_pvw = sess.set_mxf_ptpv2_tally({"tally_state": "PVW_GREEN"})
            self.assertTrue(r_pvw["ok"])
            p1 = r_pvw["mxf_ptpv2_tally"]
            self.assertFalse(p1["fx3_front_led_on"])
            self.assertFalse(p1["fx3_top_led_on"])
            self.assertFalse(p1["fx3_rear_led_on"])
            self.assertEqual(p1["fx6_green_gpio_faults"], 0)
            self.assertEqual(p1["osd_tally_border_color"], "GREEN")

            # PGM_RED turns physical red LEDs ON unless stealth_led_mute is True
            r_pgm = sess.set_mxf_ptpv2_tally({"tally_state": "PGM_RED", "stealth_led_mute": False})
            self.assertTrue(r_pgm["mxf_ptpv2_tally"]["fx3_front_led_on"])
            self.assertTrue(r_pgm["mxf_ptpv2_tally"]["fx3_rear_led_on"])
            self.assertEqual(r_pgm["mxf_ptpv2_tally"]["osd_tally_border_color"], "RED")

            r_stl = sess.set_mxf_ptpv2_tally({"stealth_led_mute": True, "osd_tally_indicator": True})
            p3 = r_stl["mxf_ptpv2_tally"]
            self.assertFalse(p3["fx3_front_led_on"])
            self.assertFalse(p3["fx3_top_led_on"])
            self.assertFalse(p3["fx3_rear_led_on"])
            self.assertEqual(p3["osd_tally_border_color"], "RED")
            self.assertEqual(p3["fx6_green_gpio_faults"], 0)

            r_hide = sess.set_mxf_ptpv2_tally({"osd_tally_indicator": False})
            self.assertEqual(r_hide["mxf_ptpv2_tally"]["osd_tally_border_color"], "HIDDEN")

    def test_p129_14_umd_16char_sanitization(self) -> None:
        cleaned = run_fx6_menu_trial.sanitize_p129_umd_label_16("\x1b[31m  CAM-A-STUDIO-LONGER-NAME \n\x7f")
        self.assertEqual(cleaned, "CAM-A-STUDIO-LON")
        self.assertEqual(len(cleaned), 16)

        with tempfile.TemporaryDirectory(prefix="fx6_p129_14_") as td:
            sess = self._new_session(td)
            res = sess.set_mxf_ptpv2_tally({"umd_label": "  CAM-2 STADIUM 85GM EXTRA  "})
            self.assertTrue(res["ok"])
            self.assertEqual(res["mxf_ptpv2_tally"]["umd_label"], "CAM-2 STADIUM 85")
            self.assertEqual(res["mxf_ptpv2_tally"]["umd_label_len"], 16)

            bad_empty = sess.set_mxf_ptpv2_tally({"umd_label": "   \x00\x01  "})
            self.assertFalse(bad_empty["ok"])
            self.assertEqual(bad_empty["error"], "invalid_umd_label")

    def test_p129_15_mailbox_bit_packing_and_c_default_parity(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p129_15_") as td:
            sess = self._new_session(td)
            mb64, mb65, mb66, mb67 = struct.unpack("<4I", sess._pack_phase129_mailbox_bytes())
            self.assertEqual(mb64, 0x870203C4)
            self.assertEqual(mb65, 0x80000070)
            self.assertEqual(mb66, 0xB3B11858)
            self.assertEqual(mb67, 0x4D584654)
            u_raw = sess._pack_phase129_umd_bytes()
            self.assertEqual(len(u_raw), 16)
            self.assertEqual(u_raw.rstrip(b"\x00"), b"FX3-CAM1-STUDIO")

            # Active mode packing verification
            sess.set_mxf_ptpv2_tally({
                "container_mode": "DUAL_MP4_PLUS_MXF_SIDECAR",
                "sync_mode": "PTPV2_SLAVE_WIRED",
                "ethernet_link_up": False,
                "offset_ns": 212,
                "tally_state": "PGM_PLUS_PVW",
                "stealth_led_mute": True,
                "umd_camera_index": 4,
                "umd_label": "CAM4-STEADICAM-X",
                "tsl_framing": "TCP_DLE_STX",
            })
            mb64b, mb65b, mb66b, mb67b = struct.unpack("<4I", sess._pack_phase129_mailbox_bytes())
            self.assertEqual(mb64b & 0x03, 2)  # DUAL_MP4_PLUS_MXF_SIDECAR
            self.assertEqual((mb64b >> 24) & 0x07, 0b111)  # loss0, emmc0, klv_valid
            self.assertEqual(mb65b & 0x03, 2)  # LTC_MULTITERMINAL_FALLBACK
            self.assertEqual((mb65b >> 2) & 0x01, 1)  # servo_locked
            self.assertEqual((mb65b >> 3) & 0x01, 1)  # ltc_holdover_active
            self.assertEqual((mb65b >> 4) & 0x07, 0b111)  # p12=1, wf12=0, cdc_ncm=1
            self.assertEqual(mb66b & 0x03, 3)  # PGM_PLUS_PVW
            self.assertEqual((mb66b >> 2) & 0x01, 1)  # stealth_mute
            self.assertEqual((mb66b >> 5) & 0x01, 1)  # tcp_dle_stx
            self.assertEqual((mb66b >> 6) & 0x01, 1)  # fx6_green_gpio_zero_fault
            self.assertEqual((mb66b >> 7) & 0x07, 3)  # CAM4 -> slot index 3
            self.assertEqual(mb67b, 0x4D584654)
            self.assertEqual(sess._pack_phase129_umd_bytes(), b"CAM4-STEADICAM-X")

    def test_p129_16_cross_phase_ei_and_look_propagation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p129_16_") as td:
            sess = self._new_session(td)
            sess.set_cine_exposure({"cine_ei_base": "12800", "ei_index": 25600})
            sess.set_color_and_media({"base_look": "S-Log3 / S-Gamut3.Cine"})
            p129 = sess.get_mxf_ptpv2_tally()
            self.assertEqual(p129["rdd18_exposure_index"], 25600)
            self.assertEqual(p129["rdd18_base_iso"], 12800)
            self.assertEqual(p129["rdd18_capture_gamma_equation"], "s-log3-cine")
            self.assertIn("ei=25600,gamma=s-log3-cine", sess.last_mxf_ptpv2_tally_cmd)

    def test_p129_17_http_api_get_post_and_malformed_json(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p129_17_") as td:
            _sess, srv, _t, base = self._start_http_server(td)
            try:
                st, g0 = self._http_get_json(f"{base}/api/mxf_ptpv2_tally")
                self.assertEqual(st, 200)
                self.assertTrue(g0["ok"])
                self.assertEqual(g0["specs"]["mailbox_magic"], "0x4D584654")
                self.assertEqual(g0["mxf_ptpv2_tally"]["container_mode"], "MP4_ISOBMFF_RTMD")

                st2, p2 = self._http_post_json(
                    f"{base}/api/mxf_ptpv2_tally",
                    {
                        "container_mode": "MXF_OP1A_RDD09_WRAP",
                        "sync_mode": "PTPV2_SLAVE_WIRED",
                        "offset_ns": 136,
                        "tally_state": "PGM_RED",
                        "umd_camera_index": 2,
                        "umd_label": "STUDIO-CAM-2",
                    },
                )
                self.assertEqual(st2, 200)
                self.assertTrue(p2["ok"])
                self.assertEqual(p2["mxf_ptpv2_tally"]["container_mode"], "MXF_OP1A_RDD09_WRAP")
                self.assertEqual(p2["mxf_ptpv2_tally"]["tally_state"], "PGM_RED")
                self.assertEqual(p2["status"]["mxf_ptpv2_tally"]["umd_label"], "STUDIO-CAM-2")

                # Malformed JSON -> 400
                st_bad, j_bad = self._http_post_json(f"{base}/api/mxf_ptpv2_tally", b"{bad")
                self.assertEqual(st_bad, 400)
                self.assertEqual(j_bad["error"], "invalid_json")

                # P12 Wi-Fi block -> 400
                st_wifi, j_wifi = self._http_post_json(f"{base}/api/mxf_ptpv2_tally", {"use_wifi": True})
                self.assertEqual(st_wifi, 400)
                self.assertEqual(j_wifi["error"], "p12_wlan_off_enforced")
            finally:
                srv.shutdown()
                srv.server_close()

    def test_p129_18_xml_sidecar_contains_umid_rdd18_ptpv2_tsl(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p129_18_") as td:
            _sess, srv, _t, base = self._start_http_server(td)
            try:
                self._http_post_json(
                    f"{base}/api/mxf_ptpv2_tally",
                    {
                        "container_mode": "DUAL_MP4_PLUS_MXF_SIDECAR",
                        "sync_mode": "PTPV2_SLAVE_WIRED",
                        "ptpv2_grandmaster_id": "00:1B:1B:FF:FE:20:59:99",
                        "offset_ns": 95,
                        "tally_state": "PVW_GREEN",
                        "umd_camera_index": 6,
                        "umd_label": "CAM6-DOLLY-A",
                    },
                )
                st, sidecar = self._http_get_json(f"{base}/api/xml_sidecar?format=json")
                self.assertEqual(st, 200)
                self.assertEqual(sidecar["mxf_ptpv2_tally"]["umd_label"], "CAM6-DOLLY-A")
                xml_txt = sidecar["xml"]
                root = ET.fromstring(xml_txt)
                ns = {"n": run_fx6_menu_trial.NRTM_NAMESPACE_V220}
                target_mat = root.find("n:TargetMaterial", ns)
                self.assertIsNotNone(target_mat)
                umid_attr = target_mat.attrib.get("umidRef", "")
                self.assertTrue(umid_attr.startswith("060A2B34"))
                self.assertEqual(umid_attr, sidecar["mxf_ptpv2_tally"]["smpte330_umid_hex"].upper())
                grp = root.find(".//n:Group[@name='MxfRdd18Ptpv2TslTallyBridge']", ns)
                self.assertIsNotNone(grp)
                items = {el.attrib["name"]: el.attrib["value"] for el in grp.findall("n:Item", ns)}
                self.assertEqual(items["ContainerMode"], "DUAL_MP4_PLUS_MXF_SIDECAR")
                self.assertEqual(items["Ptpv2GrandmasterId"], "00:1B:1B:FF:FE:20:59:99")
                self.assertEqual(items["TslUmdCameraSlot"], "CAM6")
                self.assertEqual(items["TslUmdCameraName"], "CAM6-DOLLY-A")
                self.assertEqual(items["P12WlanOff"], "true")
                self.assertEqual(items["EmmcMutationBytes"], "0")
            finally:
                srv.shutdown()
                srv.server_close()

    def test_p129_19_camset_roundtrip_and_tamper_guards(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p129_19_") as td:
            _sess, srv, _t, base = self._start_http_server(td)
            try:
                self._http_post_json(
                    f"{base}/api/mxf_ptpv2_tally",
                    {
                        "container_mode": "MXF_OP1A_RDD09_WRAP",
                        "sync_mode": "PTPV2_SLAVE_WIRED",
                        "offset_ns": 128,
                        "tally_state": "PGM_RED",
                        "stealth_led_mute": True,
                        "umd_camera_index": 7,
                        "umd_label": "CAM7-STEALTH",
                        "tsl_framing": "TCP_DLE_STX",
                    },
                )
                st_exp, exported = self._http_get_json(f"{base}/api/camset")
                self.assertEqual(st_exp, 200)
                self.assertEqual(exported["mxf_ptpv2_tally"]["umd_label"], "CAM7-STEALTH")

                # Reset then re-import via /api/camset
                self._http_post_json(f"{base}/api/mxf_ptpv2_tally", {"reset": True})
                self.assertEqual(
                    self._http_get_json(f"{base}/api/mxf_ptpv2_tally")[1]["mxf_ptpv2_tally"]["tally_state"],
                    "OFF",
                )
                st_imp, imported = self._http_post_json(f"{base}/api/camset", exported)
                self.assertEqual(st_imp, 200)
                self.assertTrue(imported["ok"])
                p_imp = imported["mxf_ptpv2_tally"]
                self.assertEqual(p_imp["container_mode"], "MXF_OP1A_RDD09_WRAP")
                self.assertEqual(p_imp["tally_state"], "PGM_RED")
                self.assertTrue(p_imp["stealth_led_mute"])
                self.assertEqual(p_imp["umd_camera_index"], 7)
                self.assertEqual(p_imp["umd_label"], "CAM7-STEALTH")
                self.assertEqual(p_imp["tsl_framing"], "TCP_DLE_STX")

                # Tamper guards: eMMC != 0, loss != 0, fx6_green_gpio_faults != 0
                bad_emmc = json.loads(json.dumps(exported))
                bad_emmc["mxf_ptpv2_tally"]["emmc_mutation_bytes"] = 64
                st_b1, j_b1 = self._http_post_json(f"{base}/api/camset", bad_emmc)
                self.assertEqual(st_b1, 400)
                self.assertEqual(j_b1["error"], "spvc_cert_spoof_blocked")

                bad_loss = json.loads(json.dumps(exported))
                bad_loss["mxf_ptpv2_tally"]["essence_reencode_loss"] = 1
                st_b2, j_b2 = self._http_post_json(f"{base}/api/camset", bad_loss)
                self.assertEqual(st_b2, 400)
                self.assertEqual(j_b2["error"], "cross_codec_lossless_rewrap_blocked")

                bad_gpio = json.loads(json.dumps(exported))
                bad_gpio["mxf_ptpv2_tally"]["fx6_green_gpio_faults"] = 1
                st_b3, j_b3 = self._http_post_json(f"{base}/api/camset", bad_gpio)
                self.assertEqual(st_b3, 400)
                self.assertEqual(j_b3["error"], "invalid_mxf_ptpv2_tally")
            finally:
                srv.shutdown()
                srv.server_close()

    def test_p129_20_4lang_html_ui_and_c_guest_parity(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p129_20_") as td:
            _sess, srv, _t, base = self._start_http_server(td)
            try:
                st, html = self._http_get_text(f"{base}/")
                self.assertEqual(st, 200)
                for marker in (
                    'id="phase129-mxf-ptpv2-tally-card"',
                    '<details id="p129-details">',
                    'id="p129-summary-pill"',
                    "const P129_I18N",
                    "setP129Lang('en')",
                    "setP129Lang('zh-CN')",
                    "setP129Lang('zh-TW')",
                    "setP129Lang('ja')",
                    "syncPhase129MxfPtpv2TallyUI",
                    "/api/mxf_ptpv2_tally",
                ):
                    self.assertIn(marker, html)
                self.assertNotIn('<details id="p129-details" open', html)
                self.assertGreater(html.index('id="phase129-mxf-ptpv2-tally-card"'), html.index('id="page-buttons"'))
                self.assertGreater(html.index('id="phase129-mxf-ptpv2-tally-card"'), html.index('id="cat-buttons"'))
            finally:
                srv.shutdown()
                srv.server_close()

        c_src = (TRIAL_DIR / "src" / "fx6_live_guest.c").read_text(encoding="utf-8")
        for c_marker in (
            "0x4d584654u",
            "0x870203c4u",
            "0x80000070u",
            "0xb3b11858u",
            "fx6_render_phase129_mxf_ptpv2_tsl_tally_overlay",
            "& ~0x80000000u",
            "MXFT=0x%08x:0x%08x:0x%08x",
        ):
            self.assertIn(c_marker, c_src)

    def test_p129_21_reset_restores_defaults_and_clears_block_counters(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p129_21_") as td:
            sess = self._new_session(td)
            sess.set_mxf_ptpv2_tally({"raw_mxf_on_mp4_slot": True})
            sess.set_mxf_ptpv2_tally({"use_wifi": True})
            sess.set_mxf_ptpv2_tally({
                "container_mode": "MXF_OP1A_RDD09_WRAP",
                "sync_mode": "PTPV2_SLAVE_WIRED",
                "tally_state": "PGM_RED",
                "umd_camera_index": 8,
                "umd_label": "CAM8-TOWER",
            })
            res = sess.set_mxf_ptpv2_tally({"reset": True})
            self.assertTrue(res["ok"])
            p = res["mxf_ptpv2_tally"]
            self.assertEqual(p["container_mode"], "MP4_ISOBMFF_RTMD")
            self.assertEqual(p["sync_mode"], "OFF")
            self.assertEqual(p["tally_state"], "OFF")
            self.assertEqual(p["umd_camera_index"], 1)
            self.assertEqual(p["umd_label"], "FX3-CAM1-STUDIO")
            self.assertEqual(p["mxf_blocked_count"], 0)
            self.assertEqual(p["p12_blocked_count"], 0)

    def test_p129_22_invalid_field_types_and_bounds(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p129_22_") as td:
            sess = self._new_session(td)
            for payload, expected_err in (
                ("not-a-dict", "invalid_mxf_ptpv2_tally"),
                ({"container_mode": "AVI"}, "invalid_container_mode"),
                ({"sync_mode": "GENLOCK_ANALOG"}, "invalid_sync_mode"),
                ({"tally_state": "BLUE"}, "invalid_tally_state"),
                ({"tsl_framing": "RS422"}, "invalid_tsl_framing"),
                ({"umd_camera_index": 0}, "invalid_umd_camera_index"),
                ({"umd_camera_index": 9}, "invalid_umd_camera_index"),
                ({"umd_camera_index": True}, "invalid_umd_camera_index"),
                ({"stealth_led_mute": "yes"}, "invalid_stealth_led_mute"),
                ({"osd_tally_indicator": 1}, "invalid_osd_tally_indicator"),
                ({"ethernet_link_up": "up"}, "invalid_ethernet_link_up"),
                ({"ltc_multiterminal_attached": 0}, "invalid_ltc_multiterminal_attached"),
                ({"offset_ns": -5}, "invalid_offset_ns"),
                ({"offset_ns": True}, "invalid_offset_ns"),
                ({"ptpv2_domain": True}, "invalid_ptpv2_domain"),
            ):
                res = sess.set_mxf_ptpv2_tally(payload)
                self.assertFalse(res["ok"], f"Expected failure for {payload!r}")
                self.assertEqual(res["error"], expected_err)

    def test_p129_23_tsl_dle_stx_malformed_packet_rejections(self) -> None:
        for bad_hex, expected in (
            ("zz", "invalid_tsl_hex"),
            ("fe0200fe01", "unescaped_tsl_dle"),
            ("040000", "tsl_packet_too_short"),
            ("080001000000010000000000", "bad_tsl_pbc_or_version"),
        ):
            dec = run_fx6_menu_trial.decode_p129_tsl_umd_v5_packet(bad_hex)
            self.assertFalse(dec["valid"])
            self.assertEqual(dec["error"], expected)

    def test_p129_24_clean_room_donor_mode_awareness(self) -> None:
        donor_dir = run_fx6_menu_trial._resolve_donor_app_dir()
        if _force_clean_room():
            self.assertIsNone(donor_dir)
        with tempfile.TemporaryDirectory(prefix="fx6_p129_24_") as td:
            sess = self._new_session(td)
            res = sess.set_mxf_ptpv2_tally({
                "container_mode": "MXF_OP1A_RDD09_WRAP",
                "sync_mode": "PTPV2_SLAVE_WIRED",
                "tally_state": "PGM_RED",
                "umd_camera_index": 4,
                "umd_label": "CAM4-CLEAN",
            })
            self.assertTrue(res["ok"])
            self.assertEqual(res["mxf_ptpv2_tally"]["emmc_mutation_bytes"], 0)
            self.assertEqual(res["mxf_ptpv2_tally"]["wf12_00342260_hits"], 0)

    def test_p129_25_alias_variants_for_sync_tally_framing(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p129_25_") as td:
            sess = self._new_session(td)
            res = sess.set_mxf_ptpv2_tally({
                "container_mode": "both",
                "sync_mode": "st2059",
                "tally_state": "red",
                "tsl_framing": "dle_stx",
            })
            self.assertTrue(res["ok"])
            p = res["mxf_ptpv2_tally"]
            self.assertEqual(p["container_mode"], "DUAL_MP4_PLUS_MXF_SIDECAR")
            self.assertEqual(p["sync_mode"], "PTPV2_SLAVE_WIRED")
            self.assertEqual(p["tally_state"], "PGM_RED")
            self.assertEqual(p["tsl_framing"], "TCP_DLE_STX")

    def test_p129_26_status_endpoint_and_mailbox_length(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p129_26_") as td:
            sess = self._new_session(td)
            st = sess.get_status()
            self.assertIn("mxf_ptpv2_tally", st)
            self.assertEqual(st["mxf_ptpv2_tally"]["umd_camera_slot"], "CAM1")
            total_len = (
                len(sess._pack_full_mailbox_bytes())
                + len(sess._pack_phase73_mailbox_bytes())
                + len(sess._pack_phase81_mailbox_bytes())
                + len(sess._pack_phase88_mailbox_bytes())
                + len(sess._pack_phase95_mailbox_bytes())
                + len(sess._pack_phase102_mailbox_bytes())
                + len(sess._pack_phase109_mailbox_bytes())
                + len(sess._pack_phase116_mailbox_bytes())
                + len(sess._pack_phase123_mailbox_bytes())
                + len(sess._pack_phase129_mailbox_bytes())
                + len(sess._pack_phase129_umd_bytes())
            )
            self.assertEqual(total_len, 288)  # mb[0..71] = 72 * 4 = 288 bytes <= 512

    def test_p129_27_camset_export_sha256_determinism(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p129_27_") as td:
            sess = self._new_session(td)
            e1 = sess.export_camset_preset()
            e2 = sess.export_camset_preset()
            self.assertEqual(e1["preset_sha256"], e2["preset_sha256"])
            sess.set_mxf_ptpv2_tally({"tally_state": "PGM_RED", "umd_label": "CAM1-STAGE-MAIN"})
            e3 = sess.export_camset_preset()
            self.assertNotEqual(e1["preset_sha256"], e3["preset_sha256"])

    def test_p129_28_xml_sidecar_raw_download_contains_bridge_group(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p129_28_") as td:
            _sess, srv, _t, base = self._start_http_server(td)
            try:
                st, xml_body = self._http_get_text(f"{base}/api/xml_sidecar")
                self.assertEqual(st, 200)
                self.assertIn("MxfRdd18Ptpv2TslTallyBridge", xml_body)
                self.assertIn("Smpte330mUmidHex", xml_body)
                self.assertIn("Rdd18KlvCrc32Valid", xml_body)
            finally:
                srv.shutdown()
                srv.server_close()

    def test_p129_29_camset_p12_tamper_and_invalid_type_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p129_29_") as td:
            sess = self._new_session(td)
            exp = sess.export_camset_preset()
            exp["mxf_ptpv2_tally"]["p12_wlan_off"] = False
            res = sess.import_camset_preset(exp)
            self.assertFalse(res["ok"])
            self.assertEqual(res["error"], "p12_wlan_off_enforced")

            exp2 = sess.export_camset_preset()
            exp2["mxf_ptpv2_tally"] = "invalid"
            res2 = sess.import_camset_preset(exp2)
            self.assertFalse(res2["ok"])
            self.assertEqual(res2["error"], "invalid_mxf_ptpv2_tally")

    def test_p129_30_all_8_camera_umd_slots_and_command_format(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p129_30_") as td:
            sess = self._new_session(td)
            for idx in range(1, 9):
                res = sess.set_mxf_ptpv2_tally({
                    "umd_camera_index": idx,
                    "umd_label": f"FX3-STUDIO-C{idx}",
                    "tally_state": "PVW_GREEN" if idx % 2 == 0 else "PGM_RED",
                })
                self.assertTrue(res["ok"])
                self.assertEqual(res["mxf_ptpv2_tally"]["umd_camera_slot"], f"CAM{idx}")
                self.assertIn(f"CAM{idx},\"FX3-STUDIO-C{idx}\"", res["mxf_ptpv2_tally_cmd"])

    def test_p129_31_ptpv2_p12_interface_rejection_preserves_state(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p129_31_") as td:
            sess = self._new_session(td)
            sess.set_mxf_ptpv2_tally({
                "container_mode": "MXF_OP1A_RDD09_WRAP",
                "sync_mode": "PTPV2_SLAVE_WIRED",
                "offset_ns": 150,
                "tally_state": "PGM_RED",
            })
            bad = sess.set_mxf_ptpv2_tally({"sync_interface": "bt", "offset_ns": 200})
            self.assertFalse(bad["ok"])
            self.assertEqual(bad["error"], "p12_wlan_off_enforced")
            cur = sess.get_mxf_ptpv2_tally()
            self.assertEqual(cur["offset_ns"], 150)
            self.assertEqual(cur["container_mode"], "MXF_OP1A_RDD09_WRAP")

    def test_p129_32_unicode_16char_umd_and_byte_budget(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p129_32_") as td:
            sess = self._new_session(td)
            res = sess.set_mxf_ptpv2_tally({"umd_label": "CAM1 主机位 A-01"})
            self.assertTrue(res["ok"])
            self.assertLessEqual(len(res["mxf_ptpv2_tally"]["umd_label"]), 16)
            self.assertEqual(len(sess._pack_phase129_umd_bytes()), 16)


if __name__ == "__main__":
    unittest.main(verbosity=2)
