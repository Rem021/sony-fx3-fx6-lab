#!/usr/bin/env python3
"""Phase 116 Unit & Integration Tests:
- HLG1 / HLG2 / HLG3 ITU-R BT.2100 / ARIB STD-B67 HDR Pipeline & Knee / Detail
- CTA-861.3 (0x87) 30-Byte HDR Static Metadata InfoFrame (EOTF=3 HLG, 8-bit sum%256 == 0)
- Gamma Display Assist (EVF/LCD Only) vs Clean HDMI/SDI & Internal XAVC Isolation
- External HDMI 16->12-Bit Log RAW (Atomos ProRes RAW & Blackmagic BRAW) + Lens/EI/WB Metadata
- Focus Breathing Compensation (E-Mount 12-Pin 1.02x..1.08x vs PL-Mount & HDMI RAW 1.00x Bypass)
- NonRealTimeMeta XML Sidecar, CAMSET Roundtrip, 4-Language Web UI, and GPE0 mb[56..59] ('HLGA') HUD.

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
REPO_ROOT = TRIAL_DIR.parents[1]
if str(TRIAL_DIR) not in sys.path:
    sys.path.insert(0, str(TRIAL_DIR))

import build_live700  # noqa: E402
import run_fx6_menu_trial  # noqa: E402


def _force_clean_room() -> bool:
    return os.environ.get("FX3_FX6_FORCE_CLEAN_ROOM", "").strip().lower() in ("1", "true", "yes")


class TestPhase116HlgBt2100ProResRawBreathing(unittest.TestCase):
    def _new_session(self, td: str) -> run_fx6_menu_trial.FX6LiveGpe0Session:
        return run_fx6_menu_trial.FX6LiveGpe0Session(Path(td) / "sess", port=18782)

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

    def test_p116_01_specs_and_defaults(self) -> None:
        specs = run_fx6_menu_trial.HDR_HLG_RAW_BREATHING_SPECS
        self.assertEqual(specs["hlg_profiles"], ["OFF", "HLG1", "HLG2", "HLG3", "FX6_HLG_LIVE", "FX6_HLG_NATURAL"])
        self.assertEqual(specs["color_gamuts"], ["BT.709", "BT.2020", "S-Gamut3.Cine"])
        self.assertEqual(specs["knee_modes"], ["Auto", "87%", "95%", "100%"])
        self.assertEqual(specs["detail_level_range"], [-7, 7])
        self.assertEqual(
            specs["display_assist_modes"],
            ["OFF", "AUTO", "S-Log3->709(800%)", "HLG->709(BT.2020)", "HLG->709(709)"],
        )
        self.assertEqual(
            specs["ext_raw_modes"],
            ["OFF", "Atomos_ProRes_RAW_16_12L", "Blackmagic_BRAW_16_12L"],
        )
        self.assertEqual(specs["breathing_comp_modes"], ["OFF", "AUTO"])
        self.assertEqual(specs["cta861_3_infoframe_type"], "0x87")
        self.assertEqual(specs["cta861_3_infoframe_bytes"], 30)
        self.assertEqual(specs["mailbox_magic"], "0x484C4741")
        self.assertEqual(specs["supported_langs"], ["en", "zh-CN", "zh-TW", "ja"])
        self.assertTrue(specs["clean_hdmi_sdi_isolation_enforced"])

        with tempfile.TemporaryDirectory(prefix="fx6_p116_01_") as td:
            sess = self._new_session(td)
            p116 = sess.get_hdr_hlg_raw_breathing()
            self.assertEqual(p116["hlg_profile"], "OFF")
            self.assertEqual(p116["color_gamut"], "BT.709")
            self.assertEqual(p116["peak_nits"], 100)
            self.assertEqual(p116["cta_eotf"], 0)
            self.assertTrue(p116["cta_checksum_valid"])
            self.assertEqual(p116["cta_checksum_zero_mod256"], 0)
            self.assertTrue(p116["clean_hdmi_sdi_unassisted"])
            self.assertTrue(p116["xavc_internal_unassisted"])
            self.assertEqual(p116["external_output_assist_leak_px"], 0)
            self.assertEqual(p116["ext_raw_mode"], "OFF")
            self.assertEqual(p116["breathing_comp_mode"], "OFF")
            self.assertAlmostEqual(p116["breathing_crop_factor"], 1.00, places=2)
            self.assertEqual(sess.get_status()["hdr_hlg_raw_breathing"], p116)

    def test_p116_02_hlg1_87pct_925nit_bt2020_pipeline(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p116_02_") as td:
            sess = self._new_session(td)
            res = sess.set_hdr_hlg_raw_breathing({"hlg_profile": "HLG1"})
            self.assertTrue(res["ok"])
            p = res["hdr_hlg_raw_breathing"]
            self.assertEqual(p["hlg_profile"], "HLG1")
            self.assertEqual(p["color_gamut"], "BT.2020")
            self.assertEqual(p["peak_nits"], 925)
            self.assertAlmostEqual(p["knee_pct"], 87.0, places=1)
            self.assertEqual(p["cta_eotf"], 3)
            self.assertEqual(p["cta_eotf_label"], "HLG_ITU_R_BT2100")
            self.assertEqual(p["cicp_color_primaries"], 9)
            self.assertEqual(p["cicp_transfer_characteristics"], 18)
            self.assertEqual(p["cicp_matrix_coefficients"], 9)
            self.assertEqual(p["capture_gamma_equation"], "rec2100-hlg")
            self.assertEqual(p["capture_color_primaries"], "rec2020")

    def test_p116_03_hlg2_95pct_1000nit_balanced_pipeline(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p116_03_") as td:
            sess = self._new_session(td)
            res = sess.set_hdr_hlg_raw_breathing({"hlg_profile": "HLG2", "color_gamut": "BT.2020"})
            self.assertTrue(res["ok"])
            p = res["hdr_hlg_raw_breathing"]
            self.assertEqual(p["hlg_profile"], "HLG2")
            self.assertEqual(p["peak_nits"], 1000)
            self.assertAlmostEqual(p["knee_pct"], 95.0, places=1)
            self.assertAlmostEqual(p["dynamic_range_stops"], 12.6, places=1)
            self.assertEqual(p["waveform_peak_ire"], 95)

    def test_p116_04_hlg3_100pct_1090nit_wide_dr_pipeline(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p116_04_") as td:
            sess = self._new_session(td)
            res = sess.set_hdr_hlg_raw_breathing({"hlg_profile": "HLG3", "color_gamut": "BT.2020"})
            self.assertTrue(res["ok"])
            p = res["hdr_hlg_raw_breathing"]
            self.assertEqual(p["hlg_profile"], "HLG3")
            self.assertEqual(p["peak_nits"], 1090)
            self.assertAlmostEqual(p["knee_pct"], 100.0, places=1)
            self.assertAlmostEqual(p["dynamic_range_stops"], 13.4, places=1)
            self.assertEqual(p["waveform_peak_ire"], 100)

    def test_p116_05_hlg_off_sdr_vs_slog3_resolution(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p116_05_") as td:
            sess = self._new_session(td)
            sess.set_hdr_hlg_raw_breathing({"hlg_profile": "HLG3"})
            res_off = sess.set_hdr_hlg_raw_breathing({"hlg_profile": "OFF"})
            self.assertTrue(res_off["ok"])
            self.assertEqual(res_off["hdr_hlg_raw_breathing"]["color_gamut"], "BT.709")
            self.assertEqual(res_off["hdr_hlg_raw_breathing"]["cta_eotf"], 0)
            self.assertEqual(res_off["hdr_hlg_raw_breathing"]["capture_gamma_equation"], "s-cinetone")

            sess.set_cinema_param("lut", preset="S-Log3")
            p_slog = sess.get_hdr_hlg_raw_breathing()
            self.assertEqual(p_slog["capture_gamma_equation"], "s-log3")

    def test_p116_06_cta861_3_0x87_hdr_infoframe_30_byte_modulo256_checksum(self) -> None:
        cases = [
            (0, False, 100, 1000, 0, 0, "0x69"),
            (3, True, 925, 50, 925, 400, "0x26"),
            (3, True, 1000, 50, 1000, 400, "0x90"),
            (3, True, 1090, 50, 1090, 400, "0xDA"),
        ]
        for eotf, bt2020, max_m, min_m, cll, fall, exp_cs in cases:
            pkt = run_fx6_menu_trial.build_cta861_3_hdr_infoframe(
                eotf=eotf,
                use_bt2020_primaries=bt2020,
                max_mastering_nits=max_m,
                min_mastering_0001_nits=min_m,
                max_cll_nits=cll,
                max_fall_nits=fall,
            )
            self.assertEqual(pkt["packet_bytes"], 30)
            raw = bytes.fromhex(pkt["packet_hex"])
            self.assertEqual(len(raw), 30)
            self.assertEqual(raw[0], 0x87)
            self.assertEqual(raw[1], 0x01)
            self.assertEqual(raw[2], 26)
            self.assertEqual(sum(raw) & 0xFF, 0)
            self.assertTrue(pkt["checksum_valid"])
            self.assertEqual(pkt["checksum_hex"], exp_cs)

    def test_p116_07_cta861_3_0x87_primaries_bt2020_vs_bt709_coordinates(self) -> None:
        bt2020 = run_fx6_menu_trial.build_cta861_3_hdr_infoframe(eotf=3, use_bt2020_primaries=True)
        bt709 = run_fx6_menu_trial.build_cta861_3_hdr_infoframe(eotf=3, use_bt2020_primaries=False)
        raw2020 = bytes.fromhex(bt2020["packet_hex"])
        raw709 = bytes.fromhex(bt709["packet_hex"])
        # Primary Green (x, y) in CTA-861.3 is packed starting at payload offset 2 (byte 6..9 of packet)
        g2020_x, g2020_y = struct.unpack_from("<HH", raw2020, 6)
        g709_x, g709_y = struct.unpack_from("<HH", raw709, 6)
        self.assertEqual((g2020_x, g2020_y), (8500, 39850))
        self.assertEqual((g709_x, g709_y), (15000, 30000))
        self.assertEqual(bt2020["gamut_primaries_standard"], "BT.2020")
        self.assertEqual(bt709["gamut_primaries_standard"], "BT.709")

    def test_p116_08_hlg_knee_manual_and_detail_level_bounds(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p116_08_") as td:
            sess = self._new_session(td)
            r = sess.set_hdr_hlg_raw_breathing({
                "hlg_profile": "HLG2",
                "knee_mode": "87%",
                "detail_level": -5,
            })
            self.assertTrue(r["ok"])
            self.assertEqual(r["hdr_hlg_raw_breathing"]["knee_mode"], "87%")
            self.assertAlmostEqual(r["hdr_hlg_raw_breathing"]["knee_pct"], 87.0, places=1)
            self.assertEqual(r["hdr_hlg_raw_breathing"]["detail_level"], -5)

            for bad_det in (-8, 8, 1.5, True, "bad"):
                err = sess.set_hdr_hlg_raw_breathing({"detail_level": bad_det})
                self.assertFalse(err["ok"])
                self.assertEqual(err["error"], "invalid_detail_level")

    def test_p116_09_bt2020_in_bt709_container_guard_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p116_09_") as td:
            sess = self._new_session(td)
            err = sess.set_hdr_hlg_raw_breathing({
                "hlg_profile": "HLG3",
                "color_gamut": "BT.2020",
                "container_colorimetry": "BT.709",
            })
            self.assertFalse(err["ok"])
            self.assertEqual(err["error"], "bt2020_in_bt709_container_blocked")
            self.assertEqual(sess.get_hdr_hlg_raw_breathing()["bt2020_in_bt709_blocked_count"], 1)

            err2 = sess.set_hdr_hlg_raw_breathing({"force_bt2020_in_bt709": True})
            self.assertFalse(err2["ok"])
            self.assertEqual(err2["error"], "bt2020_in_bt709_container_blocked")
            self.assertEqual(sess.get_hdr_hlg_raw_breathing()["bt2020_in_bt709_blocked_count"], 2)

    def test_p116_10_display_assist_auto_and_explicit_modes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p116_10_") as td:
            sess = self._new_session(td)
            # Default S-Cinetone -> AUTO resolves to OFF
            r1 = sess.set_hdr_hlg_raw_breathing({"display_assist_mode": "AUTO"})
            self.assertTrue(r1["ok"])
            self.assertEqual(r1["hdr_hlg_raw_breathing"]["resolved_assist_mode"], "OFF")
            self.assertFalse(r1["hdr_hlg_raw_breathing"]["evf_lcd_assist_active"])

            # HLG3 BT.2020 -> AUTO resolves to HLG->709(BT.2020)
            r2 = sess.set_hdr_hlg_raw_breathing({"hlg_profile": "HLG3", "color_gamut": "BT.2020"})
            self.assertEqual(r2["hdr_hlg_raw_breathing"]["resolved_assist_mode"], "HLG->709(BT.2020)")
            self.assertTrue(r2["hdr_hlg_raw_breathing"]["evf_lcd_assist_active"])

            # HLG1 BT.709 -> AUTO resolves to HLG->709(709)
            r3 = sess.set_hdr_hlg_raw_breathing({"hlg_profile": "HLG1", "color_gamut": "BT.709"})
            self.assertEqual(r3["hdr_hlg_raw_breathing"]["resolved_assist_mode"], "HLG->709(709)")

            # S-Log3 with HLG OFF -> AUTO resolves to S-Log3->709(800%)
            sess.set_cinema_param("lut", preset="S-Log3")
            r4 = sess.set_hdr_hlg_raw_breathing({"hlg_profile": "OFF"})
            self.assertEqual(r4["hdr_hlg_raw_breathing"]["resolved_assist_mode"], "S-Log3->709(800%)")

    def test_p116_11_display_assist_vf_lcd_vs_clean_hdmi_sdi_isolation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p116_11_") as td:
            sess = self._new_session(td)
            for mode in ("S-Log3->709(800%)", "HLG->709(BT.2020)", "HLG->709(709)"):
                r = sess.set_hdr_hlg_raw_breathing({"display_assist_mode": mode})
                self.assertTrue(r["ok"])
                p = r["hdr_hlg_raw_breathing"]
                self.assertEqual(p["resolved_assist_mode"], mode)
                self.assertTrue(p["evf_lcd_assist_active"])
                self.assertTrue(p["clean_hdmi_sdi_unassisted"])
                self.assertTrue(p["xavc_internal_unassisted"])
                self.assertEqual(p["external_output_assist_leak_px"], 0)

    def test_p116_12_display_assist_clean_feed_leak_attempts_blocked(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p116_12_") as td:
            sess = self._new_session(td)
            leak_payloads = [
                {"apply_assist_to_hdmi": True},
                {"apply_assist_to_sdi": True},
                {"bake_assist_into_hdmi": True},
                {"bake_assist_into_xavc": True},
                {"clean_hdmi_sdi_unassisted": False},
                {"xavc_internal_unassisted": False},
            ]
            for idx, pay in enumerate(leak_payloads, start=1):
                err = sess.set_hdr_hlg_raw_breathing(pay)
                self.assertFalse(err["ok"])
                self.assertEqual(err["error"], "display_assist_clean_feed_leak_blocked")
                self.assertTrue(err["clean_hdmi_sdi_unassisted"])
                self.assertEqual(err["external_output_assist_leak_px"], 0)
                self.assertEqual(err["assist_leak_blocked_count"], idx)

    def test_p116_13_atomos_prores_raw_16_to_12bit_log_metadata(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p116_13_") as td:
            sess = self._new_session(td)
            r = sess.set_hdr_hlg_raw_breathing({"ext_raw_mode": "Atomos_ProRes_RAW_16_12L"})
            self.assertTrue(r["ok"])
            p = r["hdr_hlg_raw_breathing"]
            self.assertTrue(p["ext_raw_active"])
            self.assertEqual(p["raw_bit_depth_in"], 16)
            self.assertEqual(p["raw_bit_depth_packed"], 12)
            self.assertEqual(p["raw_transfer_curve"], "16bit_Linear_to_12bit_Log_Packing")
            self.assertIn("Atomos_Ninja 16->12L", p["raw_hdmi_packet_summary"])
            self.assertEqual(p["raw_base_iso"], 800)
            self.assertEqual(p["raw_kelvin"], 5600)
            self.assertEqual(p["raw_lens_metadata"]["electronic_pins"], 12)

    def test_p116_14_blackmagic_braw_16_to_12bit_log_metadata(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p116_14_") as td:
            sess = self._new_session(td)
            r = sess.set_hdr_hlg_raw_breathing({"ext_raw_mode": "Blackmagic_BRAW_16_12L"})
            self.assertTrue(r["ok"])
            p = r["hdr_hlg_raw_breathing"]
            self.assertTrue(p["ext_raw_active"])
            self.assertEqual(p["raw_bit_depth_in"], 16)
            self.assertEqual(p["raw_bit_depth_packed"], 12)
            self.assertIn("Blackmagic_VideoAssist 16->12L", p["raw_hdmi_packet_summary"])

    def test_p116_15_ext_raw_syncs_base_iso_kelvin_fps_iris_from_camera_state(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p116_15_") as td:
            sess = self._new_session(td)
            sess.set_cinema_param("ei", preset="12800")
            sess.set_cinema_param("wb", preset="3200K")
            sess.set_cinema_param("fps", preset="59.94p")
            sess.set_shotmark_and_iris({"iris_fstop": 1.4})
            sess.set_hdr_hlg_raw_breathing({"ext_raw_mode": "Atomos_ProRes_RAW_16_12L"})
            p = sess.get_hdr_hlg_raw_breathing()
            self.assertEqual(p["raw_base_iso"], 12800)
            self.assertEqual(p["raw_kelvin"], 3200)
            self.assertAlmostEqual(p["raw_fps"], 59.94, places=2)
            self.assertAlmostEqual(p["raw_lens_metadata"]["iris_fstop"], 1.4, places=1)
            self.assertIn("Base12800 3200K", p["raw_hdmi_packet_summary"])

    def test_p116_16_ext_raw_syncs_wired_io_mode_hdmi_raw16_bidirectionally(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p116_16_") as td:
            sess = self._new_session(td)
            sess.set_hdr_hlg_raw_breathing({"ext_raw_mode": "Atomos_ProRes_RAW_16_12L"})
            self.assertEqual(sess.get_cine_exposure()["wired_io_mode"], "hdmi_raw16")

            sess.set_hdr_hlg_raw_breathing({"ext_raw_mode": "OFF"})
            self.assertEqual(sess.get_cine_exposure()["wired_io_mode"], "off")

            sess.set_cine_exposure({"wired_io_mode": "hdmi_raw16"})
            self.assertEqual(sess.get_hdr_hlg_raw_breathing()["ext_raw_mode"], "Atomos_ProRes_RAW_16_12L")

    def test_p116_17_focus_breathing_emount_12pin_crop_lookup_table(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p116_17_") as td:
            sess = self._new_session(td)
            r = sess.set_hdr_hlg_raw_breathing({"breathing_comp_mode": "AUTO"})
            self.assertTrue(r["ok"])
            self.assertTrue(r["hdr_hlg_raw_breathing"]["breathing_effective_active"])
            self.assertAlmostEqual(r["hdr_hlg_raw_breathing"]["breathing_crop_factor"], 1.04, places=2)

            for fl, exp_crop in [(16, 1.02), (24, 1.04), (50, 1.06), (85, 1.07), (135, 1.08)]:
                sess.set_mc_fleet_sdi_c2pa({"focal_length_mm": fl})
                p = sess.get_hdr_hlg_raw_breathing()
                self.assertTrue(p["breathing_effective_active"])
                self.assertAlmostEqual(p["breathing_crop_factor"], exp_crop, places=2)

    def test_p116_18_focus_breathing_pl_mount_unchipped_1x_bypass(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p116_18_") as td:
            sess = self._new_session(td)
            sess.set_hdr_hlg_raw_breathing({"breathing_comp_mode": "AUTO"})
            self.assertAlmostEqual(sess.get_hdr_hlg_raw_breathing()["breathing_crop_factor"], 1.04, places=2)

            sess.set_mc_fleet_sdi_c2pa({"mount_type": "Manual_PL_Adapter_Unchipped"})
            p = sess.get_hdr_hlg_raw_breathing()
            self.assertEqual(p["breathing_comp_mode"], "AUTO")
            self.assertFalse(p["breathing_effective_active"])
            self.assertTrue(p["breathing_bypassed_by_pl_mount"])
            self.assertAlmostEqual(p["breathing_crop_factor"], 1.00, places=2)
            self.assertEqual(p["breathing_bypass_reason"], "PL_UNCHIPPED_0PIN_IDENTITY")

            # Hot-swap back to E-Mount 12-pin restores active crop
            sess.set_mc_fleet_sdi_c2pa({"mount_type": "Sony_EMount_12Pin_GM"})
            p2 = sess.get_hdr_hlg_raw_breathing()
            self.assertTrue(p2["breathing_effective_active"])
            self.assertAlmostEqual(p2["breathing_crop_factor"], 1.04, places=2)

    def test_p116_19_focus_breathing_hdmi_raw_full_sensor_1x_bypass(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p116_19_") as td:
            sess = self._new_session(td)
            sess.set_hdr_hlg_raw_breathing({
                "breathing_comp_mode": "AUTO",
                "ext_raw_mode": "Atomos_ProRes_RAW_16_12L",
            })
            p = sess.get_hdr_hlg_raw_breathing()
            self.assertFalse(p["breathing_effective_active"])
            self.assertTrue(p["breathing_bypassed_by_raw"])
            self.assertAlmostEqual(p["breathing_crop_factor"], 1.00, places=2)
            self.assertEqual(p["breathing_bypass_reason"], "HDMI_RAW_FULL_SENSOR_NO_CROP")

    def test_p116_20_focus_breathing_force_interlock_rejected_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p116_20_") as td:
            sess = self._new_session(td)
            for key in ("force_breathing_on_pl", "force_breathing_in_raw"):
                err = sess.set_hdr_hlg_raw_breathing({key: True})
                self.assertFalse(err["ok"])
                self.assertEqual(err["error"], "focus_breathing_interlock_blocked")
                self.assertAlmostEqual(err["breathing_crop_factor"], 1.00, places=2)

    def test_p116_21_mailbox_mb56_to_59_hlga_binary_layout_and_magic(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p116_21_") as td:
            sess = self._new_session(td)
            b_def = sess._pack_phase116_mailbox_bytes()
            self.assertEqual(len(b_def), 16)
            mb56, mb57, mb58, mb59 = struct.unpack("<4I", b_def)
            self.assertEqual(mb59, 0x484C4741)
            self.assertEqual(mb56, 0x829A60E0)
            self.assertEqual(mb57, 0xA90A0180)
            self.assertEqual(mb58, 0x80C809C0)

            sess.set_hdr_hlg_raw_breathing({
                "hlg_profile": "HLG3",
                "color_gamut": "BT.2020",
                "knee_mode": "100%",
                "detail_level": 4,
                "display_assist_mode": "AUTO",
                "ext_raw_mode": "Blackmagic_BRAW_16_12L",
                "breathing_comp_mode": "AUTO",
            })
            b_act = sess._pack_phase116_mailbox_bytes()
            mb56_a, mb57_a, mb58_a, mb59_a = struct.unpack("<4I", b_act)
            self.assertEqual(mb59_a, 0x484C4741)
            self.assertEqual(mb56_a & 0x7, 3)  # HLG3
            self.assertEqual((mb56_a >> 3) & 0x3, 1)  # BT.2020
            self.assertEqual((mb56_a >> 5) & 0xF, 11)  # detail +4 -> +7 biased 11
            self.assertEqual((mb56_a >> 9) & 0x3, 3)  # knee 100%
            self.assertEqual((mb56_a >> 11) & 0x3, 3)  # EOTF=3
            self.assertEqual((mb56_a >> 13) & 0x1, 1)  # CTA valid
            self.assertNotEqual(mb57_a & (1 << 7), 0)  # Clean HDMI/SDI forced
            self.assertNotEqual(mb57_a & (1 << 8), 0)  # XAVC unassisted forced
            self.assertEqual(mb58_a & 0x3, 2)  # BRAW
            self.assertEqual((mb58_a >> 13) & 0x1, 1)  # FBC requested AUTO
            self.assertEqual((mb58_a >> 14) & 0x1, 0)  # FBC bypassed because RAW active
            self.assertEqual((mb58_a >> 16) & 0x1, 1)  # bypass_by_raw

    def test_p116_22_xml_sidecar_rec2100_hlg_rec2020_raw_breathing_tags(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p116_22_") as td:
            sess = self._new_session(td)
            sess.set_hdr_hlg_raw_breathing({
                "hlg_profile": "HLG3",
                "color_gamut": "BT.2020",
                "display_assist_mode": "AUTO",
                "ext_raw_mode": "Atomos_ProRes_RAW_16_12L",
                "breathing_comp_mode": "AUTO",
            })
            sidecar = sess.get_xml_sidecar()
            xml_text = sidecar["xml"]
            root = ET.fromstring(xml_text)
            self.assertIn('name="HlgBt2100AssistRawBreathing"', xml_text)
            items = {el.attrib.get("name"): el.attrib.get("value") for el in root.findall(".//{*}Item")}
            self.assertEqual(items["CaptureGammaEquation"], "rec2100-hlg")
            self.assertEqual(items["CaptureColorPrimaries"], "rec2020")
            self.assertEqual(items["HlgProfile"], "HLG3")
            self.assertEqual(items["Cta8613Eotf"], "3")
            self.assertEqual(items["Cta8613ChecksumValid"], "true")
            self.assertEqual(items["CleanHdmiSdiUnassisted"], "true")
            self.assertEqual(items["ExternalRawOutputMode"], "Atomos_ProRes_RAW_16_12L")
            self.assertEqual(items["FocusBreathingCompEffective"], "false")
            self.assertEqual(items["FocusBreathingBypassReason"], "HDMI_RAW_FULL_SENSOR_NO_CROP")
            self.assertEqual(items["FocusBreathingCropFactor"], "1.00x")

    def test_p116_23_camset_export_and_import_roundtrip_and_invalid_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p116_23_") as td:
            sess = self._new_session(td)
            sess.set_hdr_hlg_raw_breathing({
                "hlg_profile": "HLG2",
                "color_gamut": "BT.2020",
                "knee_mode": "95%",
                "detail_level": -2,
                "display_assist_mode": "HLG->709(BT.2020)",
                "ext_raw_mode": "Blackmagic_BRAW_16_12L",
                "breathing_comp_mode": "AUTO",
            })
            exported = sess.export_camset_preset()
            self.assertIn("hdr_hlg_raw_breathing", exported)
            self.assertEqual(exported["hdr_hlg_raw_breathing"]["hlg_profile"], "HLG2")

            sess2 = self._new_session(td + "_2")
            imp = sess2.import_camset_preset(exported)
            self.assertTrue(imp["ok"])
            p2 = sess2.get_hdr_hlg_raw_breathing()
            self.assertEqual(p2["hlg_profile"], "HLG2")
            self.assertEqual(p2["color_gamut"], "BT.2020")
            self.assertEqual(p2["knee_mode"], "95%")
            self.assertEqual(p2["detail_level"], -2)
            self.assertEqual(p2["display_assist_mode"], "HLG->709(BT.2020)")
            self.assertEqual(p2["ext_raw_mode"], "Blackmagic_BRAW_16_12L")
            self.assertEqual(p2["breathing_comp_mode"], "AUTO")

            bad_export = json.loads(json.dumps(exported))
            bad_export["hdr_hlg_raw_breathing"]["hlg_profile"] = "HLG99_INVALID"
            bad_res = sess2.import_camset_preset(bad_export)
            self.assertFalse(bad_res["ok"])
            self.assertEqual(bad_res["error"], "invalid_hlg_profile")

    def test_p116_24_http_get_and_post_hdr_hlg_raw_breathing_and_status(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p116_24_") as td:
            sess, srv, thr, base = self._start_http_server(td)
            try:
                st_code, get_res = self._http_get_json(f"{base}/api/hdr_hlg_raw_breathing")
                self.assertEqual(st_code, 200)
                self.assertTrue(get_res["ok"])
                self.assertEqual(get_res["hdr_hlg_raw_breathing"]["hlg_profile"], "OFF")

                p_code, post_res = self._http_post_json(
                    f"{base}/api/hdr_hlg_raw_breathing",
                    {
                        "hlg_profile": "HLG3",
                        "color_gamut": "BT.2020",
                        "display_assist_mode": "AUTO",
                        "breathing_comp_mode": "AUTO",
                    },
                )
                self.assertEqual(p_code, 200)
                self.assertTrue(post_res["ok"])
                self.assertEqual(post_res["hdr_hlg_raw_breathing"]["hlg_profile"], "HLG3")
                self.assertAlmostEqual(post_res["hdr_hlg_raw_breathing"]["breathing_crop_factor"], 1.04, places=2)
                self.assertIn("hdr_hlg_raw_breathing", post_res["status"])
                self.assertEqual(post_res["status"]["hdr_hlg_raw_breathing"]["peak_nits"], 1090)

                x_code, xml_txt = self._http_get_text(f"{base}/api/xml_sidecar")
                self.assertEqual(x_code, 200)
                self.assertIn("rec2100-hlg", xml_txt)
            finally:
                srv.shutdown()
                srv.server_close()
                thr.join(timeout=2)

    def test_p116_25_http_malformed_json_non_object_and_negative_rejections(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p116_25_") as td:
            sess, srv, thr, base = self._start_http_server(td)
            try:
                c1, r1 = self._http_post_json(f"{base}/api/hdr_hlg_raw_breathing", b"{bad-json")
                self.assertEqual(c1, 400)
                self.assertEqual(r1["error"], "invalid_json")

                c2, r2 = self._http_post_json(f"{base}/api/hdr_hlg_raw_breathing", [1, 2, 3])
                self.assertEqual(c2, 400)
                self.assertEqual(r2["error"], "invalid_json_object")

                c3, r3 = self._http_post_json(f"{base}/api/hdr_hlg_raw_breathing", {"apply_assist_to_hdmi": True})
                self.assertEqual(c3, 400)
                self.assertEqual(r3["error"], "display_assist_clean_feed_leak_blocked")

                c4, r4 = self._http_post_json(f"{base}/api/hdr_hlg_raw_breathing", {"hlg_profile": "HDR1000"})
                self.assertEqual(c4, 400)
                self.assertEqual(r4["error"], "invalid_hlg_profile")
            finally:
                srv.shutdown()
                srv.server_close()
                thr.join(timeout=2)

    def test_p116_26_cinema_param_fps_ei_wb_lut_cross_sync(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p116_26_") as td:
            sess = self._new_session(td)
            sess.set_hdr_hlg_raw_breathing({"ext_raw_mode": "Atomos_ProRes_RAW_16_12L", "display_assist_mode": "AUTO"})
            sess.set_cinema_param("ei", preset="12800")
            sess.set_cinema_param("wb", preset="4300K")
            sess.set_cinema_param("fps", preset="25.00p")
            sess.set_cinema_param("lut", preset="S-Log3")
            p = sess.get_hdr_hlg_raw_breathing()
            self.assertEqual(p["raw_base_iso"], 12800)
            self.assertEqual(p["raw_kelvin"], 4300)
            self.assertAlmostEqual(p["raw_fps"], 25.0, places=2)
            self.assertEqual(p["resolved_assist_mode"], "S-Log3->709(800%)")
            self.assertIn("B12800,4300K", p["hdr_hlg_raw_breathing_cmd"])

    def test_p116_27_web_ui_4lang_i18n_card_and_endpoints_present(self) -> None:
        html = run_fx6_menu_trial.HTML_UI
        for token in (
            "phase116-hlg-raw-breathing-card",
            "p116-lang-en",
            "p116-lang-zh-CN",
            "p116-lang-zh-TW",
            "p116-lang-ja",
            "P116_I18N",
            "setP116Lang",
            "syncPhase116HlgRawBreathingUI",
            "/api/hdr_hlg_raw_breathing",
            "简体中文",
            "繁體中文",
            "日本語",
            "CTA-861.3 (0x87)",
        ):
            self.assertIn(token, html)

    def test_p116_28_guest_c_hlga_tokens_and_zero_heap_no_printf(self) -> None:
        c_src = (TRIAL_DIR / "src" / "fx6_live_guest.c").read_text(encoding="utf-8")
        for token in (
            "0x484c4741u",
            "fx6_render_phase116_hlg_raw_breathing_overlay",
            "HLGA=0x%08x:0x%08x:0x%08x",
            "g_live_p116_display_assist  = mb[57] | (1u << 7) | (1u << 8);",
            "g_live_p116_hlg_colorimetry = 0x829a60e0u;",
            "g_live_p116_display_assist = 0xa90a0180u;",
            "g_live_p116_raw_breathing = 0x80c809c0u;",
        ):
            self.assertIn(token, c_src)
        self.assertNotIn("8768", c_src)
        idx_start = c_src.index("fx6_render_phase116_hlg_raw_breathing_overlay")
        idx_end = c_src.index("static void fx6_render_dispatch", idx_start)
        fn_body = c_src[idx_start:idx_end]
        for forbidden in ("malloc(", "calloc(", "realloc(", "printf("):
            self.assertNotIn(forbidden, fn_body)

    def test_p116_29_guest_c_compiles_cleanly_for_arm64(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p116_29_") as td:
            out_so = Path(td) / "libfx6_live_guest.so"
            res = build_live700.compile_shim(build_live700.DEFAULT_ZIG, out_so)
            self.assertTrue(out_so.exists())
            self.assertGreater(res["bytes"], 500000)

    def test_p116_30_port_isolation_no_8768_and_scoped_18782(self) -> None:
        py_src = (TRIAL_DIR / "run_fx6_menu_trial.py").read_text(encoding="utf-8")
        idx_p116 = py_src.index("Phase 116: HLG1/HLG2/HLG3")
        idx_gpe = py_src.index("def _png_chunk", idx_p116)
        self.assertNotIn("8768", py_src[idx_p116:idx_gpe])
        scoped = run_fx6_menu_trial.resolve_port_scoped_workdir(18782, Path("/private/tmp/fx6_p116_trial_18782"))
        self.assertEqual(str(scoped), "/private/tmp/fx6_p116_trial_18782")

    def test_p116_31_ram_only_zero_persistent_emmc_mutations(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p116_31_") as td:
            sess = self._new_session(td)
            res = sess.set_hdr_hlg_raw_breathing({
                "hlg_profile": "HLG3",
                "color_gamut": "BT.2020",
                "display_assist_mode": "AUTO",
                "ext_raw_mode": "Atomos_ProRes_RAW_16_12L",
                "breathing_comp_mode": "AUTO",
            })
            self.assertTrue(res["ok"])
            self.assertFalse(res["hdr_hlg_raw_breathing"]["persistent_emmc_writes_authorized"])
            self.assertEqual(sess.get_mc_fleet_sdi_c2pa()["cnflasha_writes"], 0)
            self.assertEqual(sess.get_mc_fleet_sdi_c2pa()["wf12_00342260_hits"], 0)

    def test_p116_32_dual_mode_clean_room_and_local_donor_parity(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p116_32_") as td:
            sess = self._new_session(td)
            mode = "CLEAN_ROOM" if _force_clean_room() else "LOCAL_DONOR"
            self.assertIn(mode, ("CLEAN_ROOM", "LOCAL_DONOR"))
            r = sess.set_hdr_hlg_raw_breathing({
                "hlg_profile": "HLG2",
                "color_gamut": "BT.2020",
                "display_assist_mode": "HLG->709(BT.2020)",
                "ext_raw_mode": "Blackmagic_BRAW_16_12L",
                "breathing_comp_mode": "AUTO",
            })
            self.assertTrue(r["ok"])
            p = r["hdr_hlg_raw_breathing"]
            self.assertEqual(p["cta_checksum_zero_mod256"], 0)
            self.assertTrue(p["clean_hdmi_sdi_unassisted"])
            self.assertEqual(p["raw_bit_depth_packed"], 12)
            self.assertAlmostEqual(p["breathing_crop_factor"], 1.00, places=2)


if __name__ == "__main__":
    unittest.main()
