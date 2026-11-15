#!/usr/bin/env python3
"""Phase 81 Unit & Integration Tests: Interactive Click-to-Track 627-pt PDAF Reticle,
Focus Magnifier x4.0, S-Log3 False Color / EL-Zone, Clear Image Zoom & Coupling.

Dual-mode safe:
- Passes 100% in both Local Donor mode and `FX3_FX6_FORCE_CLEAN_ROOM=1` mode.
- Never spawns any QEMU process and never touches port 8768.
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import json
import os
import re
import struct
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

TRIAL_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = TRIAL_DIR.parents[1]
if str(TRIAL_DIR) not in sys.path:
    sys.path.insert(0, str(TRIAL_DIR))

import build_live700  # noqa: E402
import run_fx6_menu_trial  # noqa: E402


def _force_clean_room() -> bool:
    return os.environ.get("FX3_FX6_FORCE_CLEAN_ROOM", "").strip().lower() in ("1", "true", "yes")


class TestPhase81TouchAfFalseColorCiz(unittest.TestCase):
    def _new_session(self, td: str) -> run_fx6_menu_trial.FX6LiveGpe0Session:
        return run_fx6_menu_trial.FX6LiveGpe0Session(Path(td) / "sess", port=18777)

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

    def test_p81_01_specs_and_defaults(self) -> None:
        specs = run_fx6_menu_trial.TOUCH_FOCUS_CIZ_SPECS
        self.assertEqual(specs["touch_af_modes"], ["off", "touch_focus", "touch_tracking"])
        self.assertEqual(specs["touch_x_range"], [0, 959])
        self.assertEqual(specs["touch_y_range"], [0, 539])
        self.assertEqual(specs["pdaf_cols"], 33)
        self.assertEqual(specs["pdaf_rows"], 19)
        self.assertEqual(specs["pdaf_total_points"], 627)
        self.assertEqual(specs["focus_mag_modes"], ["1.0x", "2.0x", "4.0x"])
        self.assertTrue(specs["clean_hdmi_unmagnified"])
        self.assertEqual(specs["false_color_modes"], ["off", "slog3_ire", "el_zone"])
        self.assertEqual(specs["ciz_res_modes"], ["4K", "FHD"])
        self.assertEqual(specs["ciz_res_max_scale"], {"4K": 1.50, "FHD": 2.00})
        self.assertEqual(specs["zoom_rocker_speed_range"], [1, 8])

        with tempfile.TemporaryDirectory(prefix="fx6_p81_01_") as td:
            sess = self._new_session(td)
            tfc = sess.get_touch_focus_ciz()
            self.assertEqual(tfc["touch_af_mode"], "off")
            self.assertEqual(tfc["touch_x"], 480)
            self.assertEqual(tfc["touch_y"], 270)
            self.assertEqual(tfc["pdaf_col"], 16)
            self.assertEqual(tfc["pdaf_row"], 9)
            self.assertEqual(tfc["pdaf_index"], 313)
            self.assertEqual(tfc["focus_mag"], "1.0x")
            self.assertTrue(tfc["clean_hdmi_unmagnified"])
            self.assertEqual(tfc["false_color_mode"], "off")
            self.assertEqual(tfc["ciz_res_mode"], "4K")
            self.assertEqual(tfc["ciz_scale"], 1.00)
            self.assertEqual(tfc["effective_ciz_scale"], 1.00)
            self.assertFalse(tfc["letterbox_ignored"])
            self.assertFalse(tfc["slog3_zebra100_clip_warning"])
            self.assertFalse(tfc["ciz_clamped_by_exclusion"])
            self.assertEqual(sess.get_status()["touch_focus_ciz"], tfc)

    def test_p81_02_pdaf_627_grid_corners_and_center(self) -> None:
        c0 = run_fx6_menu_trial.compute_imx510_pdaf_cell(0, 0)
        self.assertEqual(c0, {"pdaf_col": 0, "pdaf_row": 0, "pdaf_index": 0})

        c_mid = run_fx6_menu_trial.compute_imx510_pdaf_cell(480, 270)
        self.assertEqual(c_mid, {"pdaf_col": 16, "pdaf_row": 9, "pdaf_index": 313})

        c_640 = run_fx6_menu_trial.compute_imx510_pdaf_cell(640, 260)
        self.assertEqual(c_640["pdaf_col"], 22)
        self.assertEqual(c_640["pdaf_row"], 9)
        self.assertEqual(c_640["pdaf_index"], 9 * 33 + 22)

        c_max = run_fx6_menu_trial.compute_imx510_pdaf_cell(959, 539)
        self.assertEqual(c_max, {"pdaf_col": 32, "pdaf_row": 18, "pdaf_index": 626})

    def test_p81_03_touch_af_modes_and_aliases(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p81_03_") as td:
            sess = self._new_session(td)
            r1 = sess.set_touch_focus_ciz({"touch_af_mode": "Real-time Tracking AF", "touch_x": 640, "touch_y": 260})
            self.assertTrue(r1["ok"])
            self.assertEqual(r1["touch_focus_ciz"]["touch_af_mode"], "touch_tracking")
            self.assertEqual(r1["touch_focus_ciz"]["touch_x"], 640)
            self.assertEqual(r1["touch_focus_ciz"]["touch_y"], 260)

            r2 = sess.set_touch_focus_ciz({"touch_af_mode": "spot"})
            self.assertTrue(r2["ok"])
            self.assertEqual(r2["touch_focus_ciz"]["touch_af_mode"], "touch_focus")

            r3 = sess.set_touch_focus_ciz({"touch_af_mode": "off"})
            self.assertTrue(r3["ok"])
            self.assertEqual(r3["touch_focus_ciz"]["touch_af_mode"], "off")

    def test_p81_04_letterbox_rejection_aspect_239_1(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p81_04_") as td:
            sess = self._new_session(td)
            sess.set_assist_tools({"aspect_marker": "2.39:1"})
            r_in = sess.set_touch_focus_ciz({"touch_af_mode": "touch_tracking", "touch_x": 640, "touch_y": 260})
            self.assertTrue(r_in["ok"])
            self.assertFalse(r_in["letterbox_ignored"])
            self.assertEqual((r_in["touch_focus_ciz"]["touch_x"], r_in["touch_focus_ciz"]["touch_y"]), (640, 260))

            # Top matte bar (y=12 < 56) -> letterbox_ignored=True, AF stays locked at (640, 260)
            r_top = sess.set_touch_focus_ciz({"touch_af_mode": "touch_focus", "touch_x": 120, "touch_y": 12})
            self.assertTrue(r_top["ok"])
            self.assertTrue(r_top["letterbox_ignored"])
            self.assertTrue(r_top["touch_focus_ciz"]["letterbox_ignored"])
            self.assertEqual(r_top["touch_focus_ciz"]["touch_af_mode"], "touch_tracking")
            self.assertEqual((r_top["touch_focus_ciz"]["touch_x"], r_top["touch_focus_ciz"]["touch_y"]), (640, 260))

            # Bottom matte bar (y=520 > 483)
            r_bot = sess.set_touch_focus_ciz({"touch_x": 300, "touch_y": 520})
            self.assertTrue(r_bot["ok"])
            self.assertTrue(r_bot["letterbox_ignored"])
            self.assertEqual((r_bot["touch_focus_ciz"]["touch_x"], r_bot["touch_focus_ciz"]["touch_y"]), (640, 260))

            # Inside active 2.39:1 sensor zone (y=180) moves lock & clears letterbox_ignored
            r_ok = sess.set_touch_focus_ciz({"touch_x": 300, "touch_y": 180})
            self.assertTrue(r_ok["ok"])
            self.assertFalse(r_ok["letterbox_ignored"])
            self.assertEqual((r_ok["touch_focus_ciz"]["touch_x"], r_ok["touch_focus_ciz"]["touch_y"]), (300, 180))

    def test_p81_05_letterbox_rejection_9_16_and_185_1(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p81_05_") as td:
            sess = self._new_session(td)
            sess.set_assist_tools({"aspect_marker": "9:16"})
            # Default (480, 270) is inside [341..618]; left pillar x=150 is rejected
            r_left = sess.set_touch_focus_ciz({"touch_af_mode": "touch_tracking", "touch_x": 150, "touch_y": 270})
            self.assertTrue(r_left["ok"])
            self.assertTrue(r_left["letterbox_ignored"])
            self.assertEqual(r_left["touch_focus_ciz"]["touch_x"], 480)
            self.assertEqual(r_left["touch_focus_ciz"]["touch_af_mode"], "off")

            r_mid = sess.set_touch_focus_ciz({"touch_af_mode": "touch_tracking", "touch_x": 500, "touch_y": 270})
            self.assertTrue(r_mid["ok"])
            self.assertFalse(r_mid["letterbox_ignored"])
            self.assertEqual(r_mid["touch_focus_ciz"]["touch_x"], 500)

            sess.set_assist_tools({"aspect_marker": "1.85:1"})
            r_edge = sess.set_touch_focus_ciz({"touch_x": 4, "touch_y": 270})
            self.assertTrue(r_edge["ok"])
            self.assertTrue(r_edge["letterbox_ignored"])
            self.assertEqual(r_edge["touch_focus_ciz"]["touch_x"], 500)

    def test_p81_06_anamorphic_desqueeze_letterbox_awareness(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p81_06_") as td:
            sess = self._new_session(td)
            r_a = sess.set_assist_tools({"desqueeze": "1.3x"})
            self.assertTrue(r_a["ok"])
            self.assertEqual(r_a["assist_tools"]["desqueeze"], "1.33x")

            # For 1.33x, active y is [68..471]
            r_out = sess.set_touch_focus_ciz({"touch_af_mode": "touch_tracking", "touch_x": 480, "touch_y": 30})
            self.assertTrue(r_out["letterbox_ignored"])
            self.assertEqual(r_out["touch_focus_ciz"]["touch_y"], 270)

            # For 2.0x desqueeze, active y is [135..404]
            sess.set_assist_tools({"desqueeze": "2.0x"})
            r_out2 = sess.set_touch_focus_ciz({"touch_x": 480, "touch_y": 100})
            self.assertTrue(r_out2["letterbox_ignored"])
            r_in2 = sess.set_touch_focus_ciz({"touch_x": 400, "touch_y": 200})
            self.assertFalse(r_in2["letterbox_ignored"])
            self.assertEqual((r_in2["touch_focus_ciz"]["touch_x"], r_in2["touch_focus_ciz"]["touch_y"]), (400, 200))

    def test_p81_07_focus_magnifier_roi_and_clean_hdmi(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p81_07_") as td:
            sess = self._new_session(td)
            r2 = sess.set_touch_focus_ciz({"touch_x": 480, "touch_y": 270, "focus_mag": "2.0x"})
            self.assertTrue(r2["ok"])
            self.assertTrue(r2["clean_hdmi_unmagnified"])
            self.assertEqual(r2["touch_focus_ciz"]["focus_mag_roi"], {"x": 240, "y": 135, "w": 480, "h": 270})

            r4 = sess.set_touch_focus_ciz({"touch_x": 640, "touch_y": 260, "focus_mag": "4.0x"})
            self.assertTrue(r4["ok"])
            self.assertTrue(r4["touch_focus_ciz"]["clean_hdmi_unmagnified"])
            self.assertEqual(r4["touch_focus_ciz"]["focus_mag_factor"], 4.0)
            self.assertEqual(r4["touch_focus_ciz"]["focus_mag_roi"], {"x": 520, "y": 193, "w": 240, "h": 135})

            # Corner clamping: ROI never exceeds 960x540 bounds
            r_corner = sess.set_touch_focus_ciz({"touch_x": 940, "touch_y": 520, "focus_mag": "4.0x"})
            roi = r_corner["touch_focus_ciz"]["focus_mag_roi"]
            self.assertEqual((roi["w"], roi["h"]), (240, 135))
            self.assertEqual((roi["x"], roi["y"]), (720, 405))

    def test_p81_08_slog3_ire_landmarks_and_el_zone(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p81_08_") as td:
            sess = self._new_session(td)
            for fc_mode in ("slog3_ire", "el_zone"):
                r = sess.set_touch_focus_ciz({"false_color_mode": fc_mode})
                self.assertTrue(r["ok"])
                tfc = r["touch_focus_ciz"]
                self.assertEqual(tfc["false_color_mode"], fc_mode)
                lm = tfc["slog3_ire_landmarks"]
                self.assertEqual(lm["black_clip"]["ire"], 3.5)
                self.assertEqual(lm["black_clip"]["color"], "purple")
                self.assertEqual(lm["middle_grey"]["ire"], 41.0)
                self.assertEqual(lm["middle_grey"]["color"], "green")
                self.assertEqual(lm["skin_plus1ev"]["ire"], 52.0)
                self.assertEqual(lm["skin_plus1ev"]["color"], "pink")
                self.assertEqual(lm["sensor_clip"]["ire"], 94.0)
                self.assertEqual(lm["sensor_clip"]["color"], "red")

    def test_p81_09_slog3_zebra100_clip_warning_coupling(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p81_09_") as td:
            sess = self._new_session(td)
            # S-Cinetone + Zebra 100% does NOT warn for S-Log3 94% clip
            sess.set_color_and_media({"base_look": "S-Cinetone"})
            sess.set_assist_tools({"zebra_mode": "100%"})
            self.assertFalse(sess.get_touch_focus_ciz()["slog3_zebra100_clip_warning"])

            # Switching base_look to S-Log3 while Zebra is 100% triggers warning immediately
            r_sl3 = sess.set_color_and_media({"base_look": "S-Log3 / S-Gamut3.Cine"})
            self.assertTrue(r_sl3["ok"])
            tfc = sess.get_touch_focus_ciz()
            self.assertTrue(tfc["slog3_zebra100_clip_warning"])
            self.assertIn("94%", tfc["slog3_zebra100_warning_message"])
            self.assertIn("100%", tfc["slog3_zebra100_warning_message"])

            # Changing zebra_mode to 94%_SLog3 clears the warning
            sess.set_assist_tools({"zebra_mode": "94%_SLog3"})
            self.assertFalse(sess.get_touch_focus_ciz()["slog3_zebra100_clip_warning"])

    def test_p81_10_ciz_scale_4k_vs_fhd_limits_and_rocker_speed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p81_10_") as td:
            sess = self._new_session(td)
            r_4k = sess.set_touch_focus_ciz({"ciz_res_mode": "4K", "ciz_scale": 1.85, "zoom_rocker_speed": 7})
            self.assertTrue(r_4k["ok"])
            tfc4 = r_4k["touch_focus_ciz"]
            self.assertEqual(tfc4["ciz_res_mode"], "4K")
            self.assertEqual(tfc4["ciz_max_scale"], 1.50)
            self.assertEqual(tfc4["ciz_scale"], 1.85)
            self.assertEqual(tfc4["effective_ciz_scale"], 1.50)
            self.assertTrue(tfc4["ciz_clamped_by_res_limit"])
            self.assertEqual(tfc4["zoom_rocker_speed"], 7)

            r_fhd = sess.set_touch_focus_ciz({"ciz_res_mode": "FHD"})
            self.assertTrue(r_fhd["ok"])
            tfc_hd = r_fhd["touch_focus_ciz"]
            self.assertEqual(tfc_hd["ciz_max_scale"], 2.00)
            self.assertEqual(tfc_hd["effective_ciz_scale"], 1.85)
            self.assertFalse(tfc_hd["ciz_clamped_by_res_limit"])

    def test_p81_11_ciz_exclusion_hdmi_raw16_coupling(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p81_11_") as td:
            sess = self._new_session(td)
            sess.set_touch_focus_ciz({"ciz_res_mode": "4K", "ciz_scale": 1.40})
            self.assertEqual(sess.get_touch_focus_ciz()["effective_ciz_scale"], 1.40)

            # Enabling Phase 64 HDMI 16-bit RAW forces effective_ciz_scale -> 1.00
            r_raw = sess.set_cine_exposure({"wired_io_mode": "hdmi_raw16"})
            self.assertTrue(r_raw["ok"])
            tfc = sess.get_touch_focus_ciz()
            self.assertTrue(tfc["ciz_clamped_by_exclusion"])
            self.assertEqual(tfc["effective_ciz_scale"], 1.00)
            self.assertIn("hdmi_raw16", tfc["ciz_exclusion_reasons"])
            self.assertIn("RAW", tfc["ciz_exclusion_reason"])

            # Disabling hdmi_raw16 restores requested CIZ scale 1.40x
            sess.set_cine_exposure({"wired_io_mode": "off"})
            tfc_restored = sess.get_touch_focus_ciz()
            self.assertFalse(tfc_restored["ciz_clamped_by_exclusion"])
            self.assertEqual(tfc_restored["effective_ciz_scale"], 1.40)

    def test_p81_12_ciz_exclusion_sq_120fps_coupling(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p81_12_") as td:
            sess = self._new_session(td)
            sess.set_touch_focus_ciz({"ciz_res_mode": "FHD", "ciz_scale": 1.75})

            # S&Q 60fps does NOT disable CIZ
            sess.set_cine_exposure({"sq_enabled": True, "sq_fps": 60})
            self.assertFalse(sess.get_touch_focus_ciz()["ciz_clamped_by_exclusion"])
            self.assertEqual(sess.get_touch_focus_ciz()["effective_ciz_scale"], 1.75)

            # S&Q >= 120fps clamps CIZ -> 1.00x
            sess.set_cine_exposure({"sq_enabled": True, "sq_fps": 120})
            tfc = sess.get_touch_focus_ciz()
            self.assertTrue(tfc["ciz_clamped_by_exclusion"])
            self.assertEqual(tfc["effective_ciz_scale"], 1.00)
            self.assertIn("sq_120fps_plus", tfc["ciz_exclusion_reasons"])
            self.assertIn("120fps", tfc["ciz_exclusion_reason"])

    def test_p81_13_ciz_combined_exclusions_and_reset(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p81_13_") as td:
            sess = self._new_session(td)
            sess.set_cine_exposure({"wired_io_mode": "hdmi_raw16", "sq_enabled": True, "sq_fps": 240})
            sess.set_touch_focus_ciz({
                "touch_af_mode": "touch_tracking",
                "touch_x": 640,
                "touch_y": 260,
                "focus_mag": "4.0x",
                "false_color_mode": "el_zone",
                "ciz_scale": 1.90,
                "ciz_res_mode": "FHD",
                "zoom_rocker_speed": 8,
            })
            tfc = sess.get_touch_focus_ciz()
            self.assertEqual(tfc["ciz_exclusion_reasons"], ["hdmi_raw16", "sq_120fps_plus"])
            self.assertEqual(tfc["effective_ciz_scale"], 1.00)

            r_reset = sess.set_touch_focus_ciz({"reset": True})
            self.assertTrue(r_reset["ok"])
            rst = r_reset["touch_focus_ciz"]
            self.assertEqual(rst["touch_af_mode"], "off")
            self.assertEqual((rst["touch_x"], rst["touch_y"]), (480, 270))
            self.assertEqual(rst["focus_mag"], "1.0x")
            self.assertEqual(rst["false_color_mode"], "off")
            self.assertEqual(rst["ciz_scale"], 1.00)

    def test_p81_14_validation_rejects_invalid_inputs_http_400(self) -> None:
        bad_cases = [
            {"touch_af_mode": "continuous_magic"},
            {"touch_af_mode": True},
            {"touch_x": -1},
            {"touch_x": 960},
            {"touch_x": 123.5},
            {"touch_x": True},
            {"touch_y": -1},
            {"touch_y": 540},
            {"focus_mag": "8.0x"},
            {"focus_mag": False},
            {"false_color_mode": "rainbow"},
            {"ciz_res_mode": "8K"},
            {"ciz_scale": 0.99},
            {"ciz_scale": 2.01},
            {"ciz_scale": True},
            {"ciz_scale": "zoom"},
            {"zoom_rocker_speed": 0},
            {"zoom_rocker_speed": 9},
            {"zoom_rocker_speed": True},
        ]
        with tempfile.TemporaryDirectory(prefix="fx6_p81_14_") as td:
            _, srv, t, base = self._start_http_server(td)
            try:
                for bad in bad_cases:
                    st, res = self._http_post_json(f"{base}/api/touch_focus_ciz", bad)
                    self.assertEqual(st, 400, msg=f"bad={bad!r} got st={st} res={res}")
                    self.assertFalse(res["ok"])
                    self.assertTrue(str(res.get("error", "")).startswith("invalid_"))

                # Non-object and malformed JSON
                st_arr, res_arr = self._http_post_json(f"{base}/api/touch_focus_ciz", b"[1, 2, 3]")
                self.assertEqual(st_arr, 400)
                self.assertFalse(res_arr["ok"])

                st_mal, res_mal = self._http_post_json(f"{base}/api/touch_focus_ciz", b"{broken json")
                self.assertEqual(st_mal, 400)
                self.assertEqual(res_mal["error"], "invalid_json")
            finally:
                srv.shutdown()
                srv.server_close()
                t.join(timeout=2)

    def test_p81_15_http_get_post_api_touch_focus_ciz_and_status(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p81_15_") as td:
            _, srv, t, base = self._start_http_server(td)
            try:
                st_g, g_res = self._http_get_json(f"{base}/api/touch_focus_ciz")
                self.assertEqual(st_g, 200)
                self.assertTrue(g_res["ok"])
                self.assertEqual(g_res["touch_focus_ciz"]["pdaf_total_points"] if "pdaf_total_points" in g_res["touch_focus_ciz"] else g_res["specs"]["pdaf_total_points"], 627)

                st_p, p_res = self._http_post_json(
                    f"{base}/api/touch_focus_ciz",
                    {
                        "touch_af_mode": "touch_tracking",
                        "touch_x": 640,
                        "touch_y": 260,
                        "focus_mag": "4.0x",
                        "false_color_mode": "slog3_ire",
                        "ciz_res_mode": "4K",
                        "ciz_scale": 1.40,
                        "zoom_rocker_speed": 6,
                    },
                )
                self.assertEqual(st_p, 200)
                self.assertTrue(p_res["ok"])
                tfc = p_res["touch_focus_ciz"]
                self.assertEqual(tfc["touch_af_mode"], "touch_tracking")
                self.assertEqual((tfc["touch_x"], tfc["touch_y"]), (640, 260))
                self.assertEqual(tfc["focus_mag"], "4.0x")
                self.assertEqual(tfc["false_color_mode"], "slog3_ire")
                self.assertEqual(tfc["effective_ciz_scale"], 1.40)

                _, status_res = self._http_get_json(f"{base}/api/status")
                self.assertEqual(status_res["touch_focus_ciz"]["touch_x"], 640)
                self.assertEqual(status_res["touch_focus_ciz"]["effective_ciz_scale"], 1.40)
            finally:
                srv.shutdown()
                srv.server_close()
                t.join(timeout=2)

    def test_p81_16_camset_roundtrip_and_legacy_compat(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p81_16_") as td:
            sess = self._new_session(td)
            sess.set_touch_focus_ciz({
                "touch_af_mode": "touch_tracking",
                "touch_x": 700,
                "touch_y": 220,
                "focus_mag": "2.0x",
                "false_color_mode": "el_zone",
                "ciz_res_mode": "FHD",
                "ciz_scale": 1.65,
                "zoom_rocker_speed": 3,
            })
            preset = sess.export_camset_preset()
            self.assertIn("touch_focus_ciz", preset)
            self.assertEqual(preset["touch_focus_ciz"]["touch_x"], 700)
            self.assertEqual(preset["touch_focus_ciz"]["false_color_mode"], "el_zone")

            # Reset, then re-import -> restores exact Phase 81 state
            sess.set_touch_focus_ciz({"reset": True})
            self.assertEqual(sess.get_touch_focus_ciz()["touch_af_mode"], "off")
            imp = sess.import_camset_preset(preset)
            self.assertTrue(imp["ok"])
            restored = sess.get_touch_focus_ciz()
            self.assertEqual(restored["touch_af_mode"], "touch_tracking")
            self.assertEqual((restored["touch_x"], restored["touch_y"]), (700, 220))
            self.assertEqual(restored["focus_mag"], "2.0x")
            self.assertEqual(restored["false_color_mode"], "el_zone")
            self.assertEqual(restored["ciz_res_mode"], "FHD")
            self.assertEqual(restored["ciz_scale"], 1.65)
            self.assertEqual(restored["zoom_rocker_speed"], 3)

            # Legacy CAMSET JSON without `touch_focus_ciz` remains 100% compatible
            legacy_preset = dict(preset)
            legacy_preset.pop("touch_focus_ciz", None)
            imp_legacy = sess.import_camset_preset(legacy_preset)
            self.assertTrue(imp_legacy["ok"])

            # Invalid touch_focus_ciz fails closed without corrupting session state
            bad_preset = dict(preset)
            bad_preset["touch_focus_ciz"] = {"touch_x": 9999}
            imp_bad = sess.import_camset_preset(bad_preset)
            self.assertFalse(imp_bad["ok"])
            self.assertEqual(imp_bad["error"], "invalid_touch_x")
            self.assertEqual(sess.get_touch_focus_ciz()["touch_x"], 700)

    def test_p81_17_guest_mailbox_pack_mb36_39_and_existing_lengths(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p81_17_") as td:
            sess = self._new_session(td)
            self.assertEqual(len(sess._pack_full_mailbox_bytes()), 128)
            self.assertEqual(len(sess._pack_phase73_mailbox_bytes()), 16)

            sess.set_color_and_media({"base_look": "S-Log3 / S-Gamut3.Cine"})
            sess.set_assist_tools({"zebra_mode": "100%"})
            sess.set_touch_focus_ciz({
                "touch_af_mode": "touch_tracking",
                "touch_x": 640,
                "touch_y": 260,
                "focus_mag": "4.0x",
                "false_color_mode": "slog3_ire",
                "ciz_res_mode": "4K",
                "ciz_scale": 1.40,
                "zoom_rocker_speed": 5,
            })
            raw81 = sess._pack_phase81_mailbox_bytes()
            self.assertEqual(len(raw81), 16)
            mb36, mb37, mb38, mb39 = struct.unpack("<4I", raw81)
            self.assertEqual(mb39, 0x54414643)  # 'TAFC'
            self.assertEqual(mb36 & 0x3, 2)  # touch_tracking
            self.assertEqual((mb36 >> 2) & 0x3FF, 640)
            self.assertEqual((mb36 >> 12) & 0x3FF, 260)
            self.assertEqual((mb36 >> 22) & 0x3FF, 9 * 33 + 22)
            self.assertEqual(mb37 & 0x3F, 22)
            self.assertEqual((mb37 >> 6) & 0x1F, 9)
            self.assertEqual((mb37 >> 11) & 0x3, 2)  # 4.0x
            self.assertEqual((mb37 >> 13) & 0x3, 1)  # slog3_ire
            self.assertEqual((mb37 >> 15) & 0x1, 1)  # clean_hdmi_unmagnified
            self.assertEqual((mb37 >> 16) & 0xFF, 140)
            self.assertEqual((mb37 >> 24) & 0xFF, 140)
            self.assertEqual(mb38 & 0xF, 5)
            self.assertEqual((mb38 >> 4) & 0x1, 0)  # 4K
            self.assertEqual((mb38 >> 7) & 0x1, 1)  # slog3_zebra100_clip_warning
            self.assertEqual((mb38 >> 31) & 0x1, 1)  # valid bit

    def test_p81_18_format_command_deterministic(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p81_18_") as td:
            sess = self._new_session(td)
            r = sess.set_touch_focus_ciz({
                "touch_af_mode": "touch_tracking",
                "touch_x": 640,
                "touch_y": 260,
                "focus_mag": "4.0x",
                "false_color_mode": "slog3_ire",
                "ciz_scale": 1.40,
            })
            cmd = r["touch_af_ciz_cmd"]
            self.assertIn("TOUCH_CIZ", cmd)
            self.assertIn("af=touch_tracking@(640,260)", cmd)
            self.assertIn("mag=4.0x(hdmi=1.0x)", cmd)
            self.assertIn("fc=slog3_ire", cmd)
            self.assertIn("ciz=1.40x(eff=1.40x,res=4K", cmd)

    def test_p81_19_ui_html_click_canvas_to_focus_markers(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p81_19_") as td:
            _, srv, t, base = self._start_http_server(td)
            try:
                st, html = self._http_get_text(f"{base}/")
                self.assertEqual(st, 200)
                self.assertIn("phase81-touchaf-ciz-card", html)
                self.assertIn("p81-canvas-reticle", html)
                self.assertIn("toggleClickCanvasToFocus", html)
                self.assertIn("syncTouchFocusCizUI", html)
                self.assertIn("setTouchFocusCiz", html)
                self.assertIn("/api/touch_focus_ciz", html)
                self.assertIn("Touch-AF, S-Log3 False Color &amp; CIZ", html)
                _, tfc_json = self._http_get_json(f"{base}/api/touch_focus_ciz")
                self.assertNotRegex(json.dumps(tfc_json), r'(?<![0-9A-Za-z_/.-])b[\'"]')
            finally:
                srv.shutdown()
                srv.server_close()
                t.join(timeout=2)

    def test_p81_20_guest_c_source_phase81_invariants_and_clean_build(self) -> None:
        c_src = (TRIAL_DIR / "src" / "fx6_live_guest.c").read_text(encoding="utf-8")
        self.assertIn("0x54414643u", c_src.lower())
        self.assertIn("g_live_p81_touch_af", c_src)
        self.assertIn("g_live_p81_pdaf_mag_fc", c_src)
        self.assertIn("g_live_p81_ciz_flags", c_src)
        self.assertIn("fx6_render_phase81_touchaf_falsecolor_ciz_overlay", c_src)
        self.assertIn("TAFC=0x%08x:0x%08x:0x%08x", c_src)

        m = re.search(r"static void fx6_render_phase81_touchaf_falsecolor_ciz_overlay.*?\n\}", c_src, flags=re.S)
        self.assertIsNotNone(m)
        body = m.group(0)
        for forbidden in ("malloc(", "calloc(", "realloc(", "dlsym(", " abs("):
            self.assertNotIn(forbidden, body)

        zig = build_live700.resolve_default_zig()
        if not _force_clean_room() and zig.exists():
            with tempfile.TemporaryDirectory(prefix="fx6_p81_zig_") as td:
                out_so = Path(td) / "shim_p81.so"
                meta = build_live700.compile_shim(zig, out_so)
                self.assertTrue(out_so.exists())
                self.assertGreater(out_so.stat().st_size, 100_000)
                self.assertIn("sha256", meta)

    def test_p81_21_assist_desqueeze_13x_alias(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p81_21_") as td:
            sess = self._new_session(td)
            r = sess.set_assist_tools({"desqueeze": "1.3x"})
            self.assertTrue(r["ok"])
            self.assertEqual(r["assist_tools"]["desqueeze"], "1.33x")

    def test_p81_22_state_isolation_across_sessions(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p81_22_") as td:
            s1 = self._new_session(str(Path(td) / "a"))
            s2 = self._new_session(str(Path(td) / "b"))
            s1.set_touch_focus_ciz({"touch_af_mode": "touch_tracking", "touch_x": 800, "ciz_scale": 1.45})
            self.assertEqual(s1.get_touch_focus_ciz()["touch_x"], 800)
            self.assertEqual(s2.get_touch_focus_ciz()["touch_x"], 480)
            self.assertEqual(s2.get_touch_focus_ciz()["touch_af_mode"], "off")
            self.assertEqual(s2.get_touch_focus_ciz()["ciz_scale"], 1.00)

    def test_p81_23_clean_room_invariants(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p81_23_") as td:
            sess = self._new_session(td)
            sidecar = sess.get_xml_sidecar()
            self.assertFalse(sidecar["persistent_emmc_writes_authorized"])
            self.assertFalse(sidecar["c2pa_spoofed"])

    def test_p81_24_pdaf_exhaustive_627_bounds(self) -> None:
        seen_indices: set[int] = set()
        for y in range(0, 540, 5):
            for x in range(0, 960, 5):
                cell = run_fx6_menu_trial.compute_imx510_pdaf_cell(x, y)
                self.assertGreaterEqual(cell["pdaf_col"], 0)
                self.assertLess(cell["pdaf_col"], 33)
                self.assertGreaterEqual(cell["pdaf_row"], 0)
                self.assertLess(cell["pdaf_row"], 19)
                self.assertEqual(cell["pdaf_index"], cell["pdaf_row"] * 33 + cell["pdaf_col"])
                self.assertGreaterEqual(cell["pdaf_index"], 0)
                self.assertLess(cell["pdaf_index"], 627)
                seen_indices.add(cell["pdaf_index"])
        self.assertEqual(len(seen_indices), 627)

    def test_p81_25_http_sequential_coupling_workflow(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p81_25_") as td:
            _, srv, t, base = self._start_http_server(td)
            try:
                self._http_post_json(f"{base}/api/color_and_media", {"base_look": "S-Log3 / S-Gamut3"})
                self._http_post_json(f"{base}/api/assist_tools", {"zebra_mode": "100%", "aspect_marker": "2.39:1"})
                st, r = self._http_post_json(
                    f"{base}/api/touch_focus_ciz",
                    {"touch_af_mode": "touch_tracking", "touch_x": 640, "touch_y": 260, "ciz_scale": 1.35},
                )
                self.assertEqual(st, 200)
                self.assertTrue(r["touch_focus_ciz"]["slog3_zebra100_clip_warning"])
                self.assertEqual(r["touch_focus_ciz"]["effective_ciz_scale"], 1.35)

                # Turn on S&Q 120fps -> clamps CIZ via REST
                self._http_post_json(f"{base}/api/cine_exposure", {"sq_enabled": True, "sq_fps": 120})
                _, g = self._http_get_json(f"{base}/api/touch_focus_ciz")
                self.assertTrue(g["touch_focus_ciz"]["ciz_clamped_by_exclusion"])
                self.assertEqual(g["touch_focus_ciz"]["effective_ciz_scale"], 1.00)
            finally:
                srv.shutdown()
                srv.server_close()
                t.join(timeout=2)

    def test_p81_26_ciz_scale_rounding_and_rocker_presets(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p81_26_") as td:
            sess = self._new_session(td)
            for spd in range(1, 9):
                r = sess.set_touch_focus_ciz({"ciz_res_mode": "FHD", "ciz_scale": 1.234, "zoom_rocker_speed": spd})
                self.assertTrue(r["ok"])
                self.assertEqual(r["touch_focus_ciz"]["ciz_scale"], 1.23)
                self.assertEqual(r["touch_focus_ciz"]["effective_ciz_scale"], 1.23)
                self.assertEqual(r["touch_focus_ciz"]["zoom_rocker_speed"], spd)

    def test_p81_27_slog3_all_variants_trigger_zebra100_warning(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p81_27_") as td:
            sess = self._new_session(td)
            sess.set_assist_tools({"zebra_mode": "100%"})
            for look, expected in (
                ("S-Log3 / S-Gamut3.Cine", True),
                ("S-Log3 / S-Gamut3", True),
                ("S-Cinetone", False),
                ("ITU709", False),
                ("709(800%)", False),
            ):
                sess.set_color_and_media({"base_look": look})
                self.assertEqual(sess.get_touch_focus_ciz()["slog3_zebra100_clip_warning"], expected, msg=f"look={look}")

    def test_p81_28_el_zone_stops_order_and_hex(self) -> None:
        stops = run_fx6_menu_trial.EL_ZONE_STOPS
        self.assertEqual(len(stops), 7)
        ires = [s["ire"] for s in stops]
        self.assertEqual(ires, sorted(ires))
        self.assertEqual(ires, [3.5, 12.0, 31.0, 41.0, 52.0, 74.0, 94.0])
        for s in stops:
            self.assertRegex(s["hex"], r"^#[0-9A-Fa-f]{6}$")


if __name__ == "__main__":
    unittest.main()
