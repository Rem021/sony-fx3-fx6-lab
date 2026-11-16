#!/usr/bin/env python3
"""Phase 73 Unit & Integration Tests: Live White Balance (Shockless WB / Kelvin / Tint), Base Look (S-Cinetone / S-Log3), Dual-Slot CamID/Reel & NonRealTimeMeta M01.XML Sidecar Export.

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


class TestPhase73WbLookDualSlotXml(unittest.TestCase):
    def _new_session(self, td: str) -> run_fx6_menu_trial.FX6LiveGpe0Session:
        return run_fx6_menu_trial.FX6LiveGpe0Session(Path(td) / "sess", port=18776)

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
    def _http_get_raw(url: str) -> tuple[int, dict[str, str], bytes]:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            hdrs = {k.lower(): v for k, v in resp.headers.items()}
            return resp.status, hdrs, resp.read()

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

    def test_p73_01_specs_and_defaults(self) -> None:
        specs = run_fx6_menu_trial.COLOR_AND_MEDIA_SPECS
        self.assertEqual(
            specs["wb_modes"],
            ["preset_3200k", "preset_4300k", "preset_5600k", "mem_a", "mem_b", "atw"],
        )
        self.assertEqual(specs["kelvin_range"], [2000, 15000])
        self.assertEqual(specs["kelvin_step"], 50)
        self.assertEqual(specs["tint_gm_range"], [-99, 99])
        self.assertEqual(specs["shockless_wb_modes"], ["off", "1", "2", "3"])
        self.assertEqual(
            specs["base_looks"],
            [
                "S-Cinetone",
                "S-Log3 / S-Gamut3.Cine",
                "S-Log3 / S-Gamut3",
                "ITU709",
                "709(800%)",
                "HLG Live",
                "User 3D LUT",
            ],
        )
        self.assertEqual(specs["cam_pos_values"], ["C", "L", "R"])
        self.assertEqual(specs["dual_slot_modes"], ["simul", "relay", "sort_main_proxy", "single_slot_a"])
        self.assertEqual(
            specs["proxy_modes"],
            ["xavc_hs_1080p_16m", "xavc_hs_1080p_9m", "xavc_s_720p_6m", "off"],
        )
        self.assertTrue(specs["fx3_wb_switch_soft_mapped"])

        with tempfile.TemporaryDirectory(prefix="fx6_p73_01_") as td:
            sess = self._new_session(td)
            cm = sess.get_color_and_media()
            self.assertEqual(cm["wb_mode"], "preset_5600k")
            self.assertEqual(cm["kelvin"], 5600)
            self.assertTrue(cm["kelvin_locked"])
            self.assertEqual(cm["tint_gm"], 0)
            self.assertEqual(cm["shockless_wb"], "off")
            self.assertTrue(cm["fx3_wb_switch_soft_mapped"])
            self.assertEqual(cm["base_look"], "S-Cinetone")
            self.assertEqual(cm["capture_gamma_equation"], "s-cinetone")
            self.assertEqual(cm["capture_color_primaries"], "rec709")
            self.assertEqual(cm["cam_id"], "A")
            self.assertEqual(cm["reel_num"], 1)
            self.assertEqual(cm["cam_pos"], "C")
            self.assertEqual(cm["clip_seq"], 1)
            self.assertEqual(cm["clip_id"], "A001C001")
            self.assertEqual(cm["main_clip_name"], "A001C001_261114_FX3B.MP4")
            self.assertEqual(cm["proxy_clip_name"], "A001C001_261114_FX3BS03.MP4")
            self.assertEqual(cm["sidecar_xml_name"], "A001C001_261114_FX3BM01.XML")
            self.assertEqual(cm["dual_slot_mode"], "simul")
            self.assertEqual(cm["proxy_mode"], "xavc_hs_1080p_16m")
            self.assertTrue(cm["proxy_effective_active"])
            self.assertFalse(cm["proxy_auto_suspended_by_sq"])
            self.assertEqual(sess.get_status()["color_and_media"], cm)

    def test_p73_02_wb_presets_lock_kelvin_and_soft_mapped(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p73_02_") as td:
            sess = self._new_session(td)
            for mode, expected_k in (
                ("preset_3200k", 3200),
                ("preset_4300k", 4300),
                ("preset_5600k", 5600),
            ):
                r = sess.set_color_and_media({"wb_mode": mode})
                self.assertTrue(r["ok"], msg=f"mode={mode}: {r}")
                self.assertEqual(r["color_and_media"]["kelvin"], expected_k)
                self.assertTrue(r["color_and_media"]["kelvin_locked"])
                self.assertTrue(r["color_and_media"]["fx3_wb_switch_soft_mapped"])

            # Switching from custom 6500K mem_a into preset_3200k locks back to 3200K
            sess.set_color_and_media({"wb_mode": "mem_a", "kelvin": 6500})
            self.assertEqual(sess.get_color_and_media()["kelvin"], 6500)
            self.assertFalse(sess.get_color_and_media()["kelvin_locked"])
            r_back = sess.set_color_and_media({"wb_mode": "preset_3200k"})
            self.assertTrue(r_back["ok"])
            self.assertEqual(r_back["color_and_media"]["kelvin"], 3200)
            self.assertTrue(r_back["color_and_media"]["kelvin_locked"])

    def test_p73_03_wb_custom_kelvin_50k_snap_and_bounds(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p73_03_") as td:
            sess = self._new_session(td)
            for mode in ("mem_a", "mem_b", "atw"):
                r = sess.set_color_and_media({"wb_mode": mode, "kelvin": 4725})
                self.assertTrue(r["ok"])
                self.assertEqual(r["color_and_media"]["kelvin"] % 50, 0)
                self.assertEqual(r["color_and_media"]["kelvin"], 4700)

            r_min = sess.set_color_and_media({"wb_mode": "mem_a", "kelvin": 2000})
            self.assertTrue(r_min["ok"])
            self.assertEqual(r_min["color_and_media"]["kelvin"], 2000)

            r_max = sess.set_color_and_media({"wb_mode": "mem_b", "kelvin": 15000})
            self.assertTrue(r_max["ok"])
            self.assertEqual(r_max["color_and_media"]["kelvin"], 15000)

            for bad_k in (1950, 15050, -5000, True, "warm"):
                bad = sess.set_color_and_media({"wb_mode": "mem_a", "kelvin": bad_k})
                self.assertFalse(bad["ok"], msg=f"bad_k={bad_k!r}")
                self.assertEqual(bad["error"], "invalid_kelvin")

            # Custom kelvin must remain 15000 after rejected calls
            self.assertEqual(sess.get_color_and_media()["kelvin"], 15000)

    def test_p73_04_wb_tint_gm_and_shockless_validation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p73_04_") as td:
            sess = self._new_session(td)
            r1 = sess.set_color_and_media({"tint_gm": -12, "shockless_wb": "2"})
            self.assertTrue(r1["ok"])
            self.assertEqual(r1["color_and_media"]["tint_gm"], -12)
            self.assertEqual(r1["color_and_media"]["wb_display"], "5600K-12")
            self.assertEqual(r1["color_and_media"]["shockless_wb"], "2")

            r2 = sess.set_color_and_media({"tint_gm": 99, "shockless_wb": "3"})
            self.assertTrue(r2["ok"])
            self.assertEqual(r2["color_and_media"]["wb_display"], "5600K+99")

            r3 = sess.set_color_and_media({"tint_gm": -99, "shockless_wb": "1"})
            self.assertTrue(r3["ok"])
            self.assertEqual(r3["color_and_media"]["wb_display"], "5600K-99")

            for bad_tint in (-100, 100, 1.5, True, "green"):
                b = sess.set_color_and_media({"tint_gm": bad_tint})
                self.assertFalse(b["ok"])
                self.assertEqual(b["error"], "invalid_tint_gm")

            for bad_sl in ("4", "turbo", True, -1):
                b = sess.set_color_and_media({"shockless_wb": bad_sl})
                self.assertFalse(b["ok"])
                self.assertEqual(b["error"], "invalid_shockless_wb")

            bad_mode = sess.set_color_and_media({"wb_mode": "incandescent"})
            self.assertFalse(bad_mode["ok"])
            self.assertEqual(bad_mode["error"], "invalid_wb_mode")

    def test_p73_05_base_look_and_nle_gamma_primaries_mapping(self) -> None:
        expected = {
            "S-Cinetone": ("s-cinetone", "rec709"),
            "S-Log3 / S-Gamut3.Cine": ("s-log3-cine", "s-gamut3-cine"),
            "S-Log3 / S-Gamut3": ("s-log3", "s-gamut3"),
            "ITU709": ("rec709", "rec709"),
            "709(800%)": ("rec709-800", "rec709"),
            "HLG Live": ("rec2100-hlg", "rec2020"),
            "User 3D LUT": ("s-log3-cine", "s-gamut3-cine"),
        }
        with tempfile.TemporaryDirectory(prefix="fx6_p73_05_") as td:
            sess = self._new_session(td)
            for look, (gamma_eq, primaries) in expected.items():
                r = sess.set_color_and_media({"base_look": look})
                self.assertTrue(r["ok"], msg=f"look={look}: {r}")
                cm = r["color_and_media"]
                self.assertEqual(cm["base_look"], look)
                self.assertEqual(cm["capture_gamma_equation"], gamma_eq)
                self.assertEqual(cm["capture_color_primaries"], primaries)

            bad = sess.set_color_and_media({"base_look": "ACEScct"})
            self.assertFalse(bad["ok"])
            self.assertEqual(bad["error"], "invalid_base_look")

    def test_p73_06_user_3d_lut_linkage_with_cube_upload(self) -> None:
        cube_text = (
            'TITLE "WarmKodak2383"\n'
            "LUT_3D_SIZE 2\n"
            "0.0 0.0 0.0\n1.0 0.0 0.0\n0.0 1.0 0.0\n1.0 1.0 0.0\n"
            "0.0 0.0 1.0\n1.0 0.0 1.0\n0.0 1.0 1.0\n1.0 1.0 1.0\n"
        )
        with tempfile.TemporaryDirectory(prefix="fx6_p73_06_") as td:
            sess = self._new_session(td)
            up = sess.upload_cube_lut(
                {"slot": "User2", "name": "WarmKodak2383.cube", "cube_text": cube_text},
                allow_mini_grid=True,
            )
            self.assertTrue(up["ok"], msg=f"upload_cube_lut failed: {up}")
            cm = sess.get_color_and_media()
            self.assertEqual(cm["base_look"], "User 3D LUT")
            self.assertEqual(cm["active_user_lut_slot"], "User2")
            self.assertIsNotNone(cm["active_user_lut"])
            self.assertEqual(cm["active_user_lut"]["name"], "WarmKodak2383.cube")
            self.assertTrue(cm["active_user_lut"]["uploaded"])
            self.assertEqual(len(cm["active_user_lut"]["sha256"]), 64)

            # Selecting User3 via user_lut_slot links cleanly
            r_u3 = sess.set_color_and_media({"user_lut_slot": "User3"})
            self.assertTrue(r_u3["ok"])
            self.assertEqual(r_u3["color_and_media"]["base_look"], "User 3D LUT")
            self.assertEqual(r_u3["color_and_media"]["active_user_lut_slot"], "User3")

            bad_slot = sess.set_color_and_media({"user_lut_slot": "User9"})
            self.assertFalse(bad_slot["ok"])
            self.assertEqual(bad_slot["error"], "invalid_user_lut_slot")

    def test_p73_07_cinema_line_clip_naming_and_sub_proxy_names(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p73_07_") as td:
            sess = self._new_session(td)
            r = sess.set_color_and_media({
                "cam_id": "b",
                "reel_num": 4,
                "cam_pos": "r",
                "clip_seq": 12,
            })
            self.assertTrue(r["ok"])
            cm = r["color_and_media"]
            self.assertEqual(cm["cam_id"], "B")
            self.assertEqual(cm["reel_num"], 4)
            self.assertEqual(cm["cam_pos"], "R")
            self.assertEqual(cm["clip_seq"], 12)
            self.assertEqual(cm["clip_id"], "B004R012")
            self.assertEqual(cm["main_clip_name"], "B004R012_261114_FX3B.MP4")
            self.assertEqual(cm["proxy_clip_name"], "B004R012_261114_FX3BS03.MP4")
            self.assertEqual(cm["sidecar_xml_name"], "B004R012_261114_FX3BM01.XML")

            for field, bad_val, err_code in (
                ("cam_id", "AB", "invalid_cam_id"),
                ("cam_id", "1", "invalid_cam_id"),
                ("reel_num", 0, "invalid_reel_num"),
                ("reel_num", 1000, "invalid_reel_num"),
                ("reel_num", True, "invalid_reel_num"),
                ("cam_pos", "X", "invalid_cam_pos"),
                ("clip_seq", 0, "invalid_clip_seq"),
                ("clip_seq", 1000, "invalid_clip_seq"),
            ):
                bad = sess.set_color_and_media({field: bad_val})
                self.assertFalse(bad["ok"], msg=f"{field}={bad_val!r}")
                self.assertEqual(bad["error"], err_code)

    def test_p73_08_dual_slot_modes_and_slot_paths(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p73_08_") as td:
            sess = self._new_session(td)
            for mode in ("simul", "relay", "sort_main_proxy", "single_slot_a"):
                r = sess.set_color_and_media({"dual_slot_mode": mode})
                self.assertTrue(r["ok"])
                cm = r["color_and_media"]
                self.assertEqual(cm["dual_slot_mode"], mode)
                self.assertEqual(cm["main_relpath"], "M4ROOT/CLIP/A001C001_261114_FX3B.MP4")
                self.assertEqual(cm["proxy_relpath"], "M4ROOT/SUB/A001C001_261114_FX3BS03.MP4")
                self.assertEqual(cm["sidecar_xml_relpath"], "M4ROOT/CLIP/A001C001_261114_FX3BM01.XML")

            bad = sess.set_color_and_media({"dual_slot_mode": "raid0"})
            self.assertFalse(bad["ok"])
            self.assertEqual(bad["error"], "invalid_dual_slot_mode")

    def test_p73_09_sq_enabled_auto_suspends_proxy_coupling(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p73_09_") as td:
            sess = self._new_session(td)
            # Initially proxy is active
            cm0 = sess.get_color_and_media()
            self.assertTrue(cm0["proxy_effective_active"])
            self.assertFalse(cm0["proxy_auto_suspended_by_sq"])
            self.assertEqual(cm0["proxy_active_clip_name"], "A001C001_261114_FX3BS03.MP4")

            # Enabling Phase 64 S&Q immediately suspends proxy recording
            r_sq = sess.set_cine_exposure({"sq_enabled": True, "base_fps": 23.98, "sq_fps": 120})
            self.assertTrue(r_sq["ok"])
            cm1 = r_sq["status"]["color_and_media"]
            self.assertFalse(cm1["proxy_effective_active"])
            self.assertTrue(cm1["proxy_auto_suspended_by_sq"])
            self.assertIsNone(cm1["proxy_active_clip_name"])
            self.assertIn("eff=0 sq_susp=1", cm1["wb_media_cmd"])

            # Disabling S&Q automatically restores proxy recording
            r_off = sess.set_cine_exposure({"sq_enabled": False})
            self.assertTrue(r_off["ok"])
            cm2 = r_off["status"]["color_and_media"]
            self.assertTrue(cm2["proxy_effective_active"])
            self.assertFalse(cm2["proxy_auto_suspended_by_sq"])
            self.assertEqual(cm2["proxy_active_clip_name"], "A001C001_261114_FX3BS03.MP4")

    def test_p73_10_proxy_off_mode_vs_sq_off(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p73_10_") as td:
            sess = self._new_session(td)
            r = sess.set_color_and_media({"proxy_mode": "off"})
            self.assertTrue(r["ok"])
            cm = r["color_and_media"]
            self.assertFalse(cm["proxy_effective_active"])
            self.assertFalse(cm["proxy_auto_suspended_by_sq"])
            self.assertIsNone(cm["proxy_active_clip_name"])

            bad = sess.set_color_and_media({"proxy_mode": "prores_422_proxy"})
            self.assertFalse(bad["ok"])
            self.assertEqual(bad["error"], "invalid_proxy_mode")

    def test_p73_11_reset_restores_defaults(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p73_11_") as td:
            sess = self._new_session(td)
            sess.set_color_and_media({
                "wb_mode": "mem_a",
                "kelvin": 7200,
                "tint_gm": 14,
                "shockless_wb": "3",
                "base_look": "S-Log3 / S-Gamut3",
                "cam_id": "D",
                "reel_num": 19,
                "cam_pos": "L",
                "clip_seq": 88,
                "dual_slot_mode": "relay",
                "proxy_mode": "xavc_s_720p_6m",
            })
            r = sess.set_color_and_media({"reset": True})
            self.assertTrue(r["ok"])
            cm = r["color_and_media"]
            self.assertEqual(cm["wb_mode"], "preset_5600k")
            self.assertEqual(cm["kelvin"], 5600)
            self.assertEqual(cm["tint_gm"], 0)
            self.assertEqual(cm["shockless_wb"], "off")
            self.assertEqual(cm["base_look"], "S-Cinetone")
            self.assertEqual(cm["cam_id"], "A")
            self.assertEqual(cm["reel_num"], 1)
            self.assertEqual(cm["cam_pos"], "C")
            self.assertEqual(cm["clip_seq"], 1)
            self.assertEqual(cm["dual_slot_mode"], "simul")
            self.assertEqual(cm["proxy_mode"], "xavc_hs_1080p_16m")

    def test_p73_12_set_cinema_param_wb_lut_bidirectional_sync(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p73_12_") as td:
            sess = self._new_session(td)
            r_wb = sess.set_cinema_param("wb", preset="3200K")
            self.assertTrue(r_wb["ok"])
            cm = sess.get_color_and_media()
            self.assertEqual(cm["wb_mode"], "preset_3200k")
            self.assertEqual(cm["kelvin"], 3200)

            r_lut = sess.set_cinema_param("lut", preset="S-Log3.Cine / S-Gamut3.Cine")
            self.assertTrue(r_lut["ok"], msg=f"set_cinema_param lut failed: {r_lut}")
            self.assertEqual(sess.get_color_and_media()["base_look"], "S-Log3 / S-Gamut3.Cine")

    def test_p73_13_xml_sidecar_nrtm_v220_elementtree_parse(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p73_13_") as td:
            sess = self._new_session(td)
            side = sess.get_xml_sidecar()
            self.assertTrue(side["ok"])
            self.assertEqual(side["filename"], "A001C001_261114_FX3BM01.XML")
            self.assertEqual(side["nrtm_namespace"], "urn:schemas-professionalDisc:nonRealTimeMeta:ver.2.20")
            self.assertFalse(side["c2pa_spoofed"])
            self.assertFalse(side["persistent_emmc_writes_authorized"])
            self.assertEqual(len(side["xml_sha256"]), 64)

            ns = {"n": "urn:schemas-professionalDisc:nonRealTimeMeta:ver.2.20"}
            root = ET.fromstring(side["xml"])
            self.assertEqual(root.tag, f"{{{ns['n']}}}NonRealTimeMeta")
            dev = root.find("n:Device", ns)
            self.assertIsNotNone(dev)
            assert dev is not None
            self.assertEqual(dev.attrib["manufacturer"], "Sony")
            self.assertEqual(dev.attrib["modelName"], "ILME-FX3")

            items = {el.attrib["name"]: el.attrib["value"] for el in root.findall(".//n:Item", ns)}
            self.assertEqual(items["CaptureGammaEquation"], "s-cinetone")
            self.assertEqual(items["CaptureColorPrimaries"], "rec709")
            self.assertEqual(items["ExposureIndexOfPhotoMeter"], "800")
            self.assertEqual(items["WhiteBalance"], "preset_5600k:5600K")
            self.assertEqual(items["DualSlotMode"], "simul")
            self.assertEqual(items["MainClipName"], "A001C001_261114_FX3B.MP4")
            self.assertEqual(items["SidecarFileName"], "A001C001_261114_FX3BM01.XML")
            self.assertEqual(items["C2PASpoofAttempted"], "false")
            self.assertEqual(items["PersistentEmmcWritesAuthorized"], "false")

    def test_p73_14_xml_sidecar_updates_with_live_cine_ei_sq_ecs_and_lut(self) -> None:
        cube_text = (
            'TITLE "CineFilm709"\n'
            "LUT_3D_SIZE 2\n"
            "0.0 0.0 0.0\n1.0 0.0 0.0\n0.0 1.0 0.0\n1.0 1.0 0.0\n"
            "0.0 0.0 1.0\n1.0 0.0 1.0\n0.0 1.0 1.0\n1.0 1.0 1.0\n"
        )
        with tempfile.TemporaryDirectory(prefix="fx6_p73_14_") as td:
            sess = self._new_session(td)
            sha_before = sess.get_xml_sidecar()["xml_sha256"]

            sess.set_cine_exposure({
                "cine_ei_base": "12800",
                "ei_index": 25600,
                "shutter_mode": "ecs",
                "ecs_freq_hz": 100.2,
                "sq_enabled": True,
                "base_fps": 23.98,
                "sq_fps": 120,
            })
            up = sess.upload_cube_lut(
                {"slot": "User1", "name": "CineFilm709.cube", "cube_text": cube_text},
                allow_mini_grid=True,
            )
            self.assertTrue(up["ok"])
            sess.set_color_and_media({
                "wb_mode": "mem_b",
                "kelvin": 4450,
                "tint_gm": -7,
                "shockless_wb": "3",
                "cam_id": "C",
                "reel_num": 12,
                "cam_pos": "L",
                "clip_seq": 7,
                "dual_slot_mode": "relay",
            })
            side = sess.get_xml_sidecar()
            self.assertNotEqual(side["xml_sha256"], sha_before)
            self.assertEqual(side["filename"], "C012L007_261114_FX3BM01.XML")

            ns = {"n": "urn:schemas-professionalDisc:nonRealTimeMeta:ver.2.20"}
            root = ET.fromstring(side["xml"])
            vf = root.find("n:VideoFormat/n:VideoFrame", ns)
            assert vf is not None
            self.assertEqual(vf.attrib["captureFps"], "120.00p")
            self.assertEqual(vf.attrib["formatFps"], "23.98p")

            items = {el.attrib["name"]: el.attrib["value"] for el in root.findall(".//n:Item", ns)}
            self.assertEqual(items["ExposureIndexOfPhotoMeter"], "25600")
            self.assertEqual(items["BaseISO"], "12800")
            self.assertEqual(items["CaptureGammaEquation"], "s-log3-cine")
            self.assertEqual(items["CaptureColorPrimaries"], "s-gamut3-cine")
            self.assertEqual(items["WhiteBalance"], "mem_b:4450K")
            self.assertEqual(items["WhiteBalanceTint"], "-7")
            self.assertEqual(items["ShocklessWhiteBalance"], "3")
            self.assertEqual(items["ShutterDisplay"], "ECS 100.20Hz")
            self.assertEqual(items["SlowAndQuickMotion"], "on:23.98->120fps")
            self.assertEqual(items["MonitoringLutName"], "CineFilm709.cube")
            self.assertIn("effective=false", items["ProxyRecording"])

    def test_p73_15_mailbox_words_32_to_35_and_full_128b_preserved(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p73_15_") as td:
            sess = self._new_session(td)
            self.assertEqual(len(sess._pack_mailbox_bytes()), 28 * 4)
            self.assertEqual(len(sess._pack_phase64_mailbox_bytes()), 16)
            self.assertEqual(len(sess._pack_full_mailbox_bytes()), 32 * 4)
            self.assertEqual(len(sess._pack_phase73_mailbox_bytes()), 16)

            sess.set_color_and_media({
                "wb_mode": "preset_3200k",
                "tint_gm": -5,
                "shockless_wb": "2",
                "base_look": "S-Log3 / S-Gamut3.Cine",
                "cam_id": "B",
                "reel_num": 4,
                "cam_pos": "R",
                "clip_seq": 12,
                "dual_slot_mode": "relay",
                "proxy_mode": "xavc_hs_1080p_9m",
            })
            sess.set_cine_exposure({"sq_enabled": True, "base_fps": 23.98, "sq_fps": 120})

            mb32, mb33, mb34, mb35 = struct.unpack("<4I", sess._pack_phase73_mailbox_bytes())
            self.assertEqual(mb35, 0x57424C4D)  # 'WBLM'
            self.assertEqual(mb32 & 0x7, 0)  # preset_3200k
            self.assertEqual((mb32 >> 3) & 0x3FFF, 3200)
            self.assertEqual(((mb32 >> 17) & 0xFF) - 99, -5)
            self.assertEqual((mb32 >> 25) & 0x3, 2)  # shockless 2
            self.assertEqual((mb32 >> 27) & 0x7, 1)  # S-Log3 / S-Gamut3.Cine
            self.assertEqual((mb32 >> 30) & 0x1, 1)  # fx3_wb_switch_soft_mapped
            self.assertEqual((mb32 >> 31) & 0x1, 1)  # valid
            self.assertEqual(mb33 & 0x1F, 1)  # 'B' - 'A'
            self.assertEqual((mb33 >> 5) & 0x3FF, 4)  # reel 4
            self.assertEqual((mb33 >> 15) & 0x3, 2)  # 'R'
            self.assertEqual((mb33 >> 17) & 0x3FF, 12)  # clip 12
            self.assertEqual((mb33 >> 27) & 0x3, 1)  # relay
            self.assertEqual((mb33 >> 29) & 0x3, 2)  # xavc_hs_1080p_9m -> 2
            self.assertEqual((mb33 >> 31) & 0x1, 0)  # proxy_effective_active = False (suspended by S&Q)
            self.assertEqual(mb34 & 0x1, 1)  # sq_enabled = True

    def test_p73_16_wb_media_command_formatter_and_session_track(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p73_16_") as td:
            sess = self._new_session(td)
            r = sess.set_color_and_media({
                "wb_mode": "preset_3200k",
                "tint_gm": -5,
                "shockless_wb": "1",
                "base_look": "S-Log3 / S-Gamut3.Cine",
                "cam_id": "B",
                "reel_num": 4,
                "clip_seq": 12,
                "dual_slot_mode": "relay",
            })
            cmd = r["wb_media_cmd"]
            self.assertIn("WB_MEDIA wb=preset_3200k:3200K:-5", cmd)
            self.assertIn("shockless=1", cmd)
            self.assertIn('look="S-Log3 / S-Gamut3.Cine"', cmd)
            self.assertIn("clip=B004C012_261114_FX3B.MP4 slot=relay", cmd)
            self.assertEqual(sess.last_wb_media_cmd, cmd)

    def test_p73_17_camset_export_and_import_roundtrip_with_color_and_media(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p73_17_") as td:
            sess = self._new_session(td)
            sess.set_color_and_media({
                "wb_mode": "mem_a",
                "kelvin": 4850,
                "tint_gm": 8,
                "shockless_wb": "2",
                "base_look": "S-Log3 / S-Gamut3.Cine",
                "cam_id": "D",
                "reel_num": 27,
                "cam_pos": "L",
                "clip_seq": 14,
                "dual_slot_mode": "sort_main_proxy",
                "proxy_mode": "xavc_s_720p_6m",
            })
            exported = sess.export_camset_preset()
            self.assertTrue(exported["ok"])
            self.assertIn("color_and_media", exported)
            rendered = json.dumps(exported)
            self.assertNotRegex(rendered, r'(?<![0-9A-Za-z_/.-])b[\'"]')
            self.assertEqual(exported["color_and_media"]["kelvin"], 4850)
            self.assertEqual(exported["color_and_media"]["clip_id"], "D027L014")

            sess.set_color_and_media({"reset": True})
            self.assertEqual(sess.get_color_and_media()["clip_id"], "A001C001")

            imp = sess.import_camset_preset(exported)
            self.assertTrue(imp["ok"])
            cm = imp["color_and_media"]
            self.assertEqual(cm["wb_mode"], "mem_a")
            self.assertEqual(cm["kelvin"], 4850)
            self.assertEqual(cm["tint_gm"], 8)
            self.assertEqual(cm["shockless_wb"], "2")
            self.assertEqual(cm["base_look"], "S-Log3 / S-Gamut3.Cine")
            self.assertEqual(cm["clip_id"], "D027L014")
            self.assertEqual(cm["dual_slot_mode"], "sort_main_proxy")
            self.assertEqual(cm["proxy_mode"], "xavc_s_720p_6m")

    def test_p73_18_camset_backward_compatibility_without_color_and_media(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p73_18_") as td:
            sess = self._new_session(td)
            legacy = sess.export_camset_preset()
            legacy.pop("color_and_media", None)
            legacy.pop("cine_exposure", None)
            legacy["cinema_params"]["wb"] = "3200K"
            imp = sess.import_camset_preset(legacy)
            self.assertTrue(imp["ok"])
            self.assertEqual(imp["cinema_params"]["values"]["wb"], "3200K")

    def test_p73_19_camset_import_rejects_invalid_color_and_media_without_mutating(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p73_19_") as td:
            sess = self._new_session(td)
            sess.set_color_and_media({"cam_id": "C", "reel_num": 5})
            bad_camset = sess.export_camset_preset()
            bad_camset["color_and_media"]["cam_id"] = "INVALID"
            imp_bad = sess.import_camset_preset(bad_camset)
            self.assertFalse(imp_bad["ok"])
            self.assertEqual(imp_bad["error"], "invalid_cam_id")
            self.assertEqual(sess.get_color_and_media()["cam_id"], "C")
            self.assertEqual(sess.get_color_and_media()["reel_num"], 5)

    def test_p73_20_http_api_get_and_post_color_and_media(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p73_20_") as td:
            _, srv, t, base = self._start_http_server(td)
            try:
                st0, g0 = self._http_get_json(f"{base}/api/color_and_media")
                self.assertEqual(st0, 200)
                self.assertTrue(g0["ok"])
                self.assertEqual(g0["color_and_media"]["wb_mode"], "preset_5600k")

                st1, p1 = self._http_post_json(
                    f"{base}/api/color_and_media",
                    {
                        "wb_mode": "preset_3200k",
                        "tint_gm": -5,
                        "shockless_wb": "2",
                        "base_look": "S-Log3 / S-Gamut3.Cine",
                        "cam_id": "B",
                        "reel_num": 4,
                        "clip_seq": 12,
                        "dual_slot_mode": "relay",
                    },
                )
                self.assertEqual(st1, 200)
                self.assertTrue(p1["ok"])
                self.assertEqual(p1["color_and_media"]["clip_id"], "B004C012")
                self.assertEqual(p1["status"]["color_and_media"]["wb_display"], "3200K-5")

                st2, status_body = self._http_get_json(f"{base}/api/status")
                self.assertEqual(st2, 200)
                self.assertEqual(status_body["color_and_media"]["dual_slot_mode"], "relay")
            finally:
                srv.shutdown()
                srv.server_close()
                t.join(timeout=2)

    def test_p73_21_http_api_color_and_media_rejects_bad_inputs_and_malformed_json_400(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p73_21_") as td:
            _, srv, t, base = self._start_http_server(td)
            try:
                st_mal, mal = self._http_post_json(f"{base}/api/color_and_media", b"{bad-json")
                self.assertEqual(st_mal, 400)
                self.assertFalse(mal["ok"])
                self.assertEqual(mal["error"], "invalid_json")

                st_list, lst = self._http_post_json(f"{base}/api/color_and_media", [1, 2, 3])
                self.assertEqual(st_list, 400)
                self.assertFalse(lst["ok"])
                self.assertEqual(lst["error"], "invalid_json_object")

                for payload, exp_err in (
                    ({"kelvin": 1800, "wb_mode": "mem_a"}, "invalid_kelvin"),
                    ({"tint_gm": 120}, "invalid_tint_gm"),
                    ({"cam_id": "AA"}, "invalid_cam_id"),
                    ({"base_look": "BadLook"}, "invalid_base_look"),
                    ({"dual_slot_mode": "invalid"}, "invalid_dual_slot_mode"),
                ):
                    st_bad, body_bad = self._http_post_json(f"{base}/api/color_and_media", payload)
                    self.assertEqual(st_bad, 400)
                    self.assertFalse(body_bad["ok"])
                    self.assertEqual(body_bad["error"], exp_err)
            finally:
                srv.shutdown()
                srv.server_close()
                t.join(timeout=2)

    def test_p73_22_http_api_get_xml_sidecar_raw_xml_and_json_format(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p73_22_") as td:
            _, srv, t, base = self._start_http_server(td)
            try:
                self._http_post_json(
                    f"{base}/api/color_and_media",
                    {
                        "wb_mode": "preset_3200k",
                        "tint_gm": -5,
                        "base_look": "S-Log3 / S-Gamut3.Cine",
                        "cam_id": "B",
                        "reel_num": 4,
                        "clip_seq": 12,
                        "dual_slot_mode": "relay",
                    },
                )
                st_xml, hdrs, raw_xml = self._http_get_raw(f"{base}/api/xml_sidecar")
                self.assertEqual(st_xml, 200)
                self.assertIn("application/xml", hdrs.get("content-type", ""))
                self.assertIn("B004C012_261114_FX3BM01.XML", hdrs.get("content-disposition", ""))
                root = ET.fromstring(raw_xml.decode("utf-8"))
                self.assertTrue(root.tag.endswith("NonRealTimeMeta"))

                st_j, j = self._http_get_json(f"{base}/api/xml_sidecar?format=json")
                self.assertEqual(st_j, 200)
                self.assertTrue(j["ok"])
                self.assertFalse(j["c2pa_spoofed"])
                self.assertEqual(j["filename"], "B004C012_261114_FX3BM01.XML")
                self.assertIn("<Device manufacturer=\"Sony\" modelName=\"ILME-FX3\"", j["xml"])
            finally:
                srv.shutdown()
                srv.server_close()
                t.join(timeout=2)

    def test_p73_23_http_api_camset_roundtrip_with_color_and_media(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p73_23_") as td:
            _, srv, t, base = self._start_http_server(td)
            try:
                self._http_post_json(
                    f"{base}/api/color_and_media",
                    {
                        "wb_mode": "atw",
                        "kelvin": 6150,
                        "shockless_wb": "3",
                        "base_look": "HLG Live",
                        "cam_id": "E",
                        "reel_num": 9,
                        "clip_seq": 3,
                    },
                )
                st_e, exp = self._http_get_json(f"{base}/api/camset_export")
                self.assertEqual(st_e, 200)
                self.assertEqual(exp["color_and_media"]["clip_id"], "E009C003")

                self._http_post_json(f"{base}/api/color_and_media", {"reset": True})
                st_i, imp = self._http_post_json(f"{base}/api/camset_import", exp)
                self.assertEqual(st_i, 200)
                self.assertTrue(imp["ok"])
                self.assertEqual(imp["color_and_media"]["clip_id"], "E009C003")
                self.assertEqual(imp["color_and_media"]["base_look"], "HLG Live")
                self.assertEqual(imp["color_and_media"]["kelvin"], 6150)
            finally:
                srv.shutdown()
                srv.server_close()
                t.join(timeout=2)

    def test_p73_24_html_ui_contains_phase73_card_and_xml_controls(self) -> None:
        html = run_fx6_menu_trial.HTML_UI
        for token in (
            "phase73-color-media-card",
            "色彩白平衡 / 双卡槽场记命名 &amp; 达芬奇 M01.XML 导出",
            "p73-wb-mode-select",
            "p73-kelvin-input",
            "p73-tint-input",
            "p73-shockless-select",
            "p73-base-look-select",
            "p73-cam-id-input",
            "p73-reel-input",
            "p73-dualslot-select",
            "p73-proxy-select",
            "p73-sq-proxy-badge",
            "downloadXmlSidecar",
            "refreshXmlSidecarPreview",
            "syncColorAndMediaUI",
            "/api/color_and_media",
            "/api/xml_sidecar",
        ):
            self.assertIn(token, html)

    def test_p73_25_guest_c_source_phase73_invariants(self) -> None:
        c_path = TRIAL_DIR / "src" / "fx6_live_guest.c"
        src = c_path.read_text(encoding="utf-8")
        for token in (
            "fx6_render_phase73_wb_look_dualslot_overlay",
            "g_live_p73_wb_look",
            "g_live_p73_media_clip",
            "g_live_p73_flags2",
            "0x57424c4du",
            "S-Cinetone",
            "S-Log3.Cine",
            "PRX:OFF(S&Q)",
            "WB_MEDIA=0x%08x:0x%08x:0x%08x",
        ):
            self.assertIn(token, src)

        m_start = src.index("static void fx6_render_phase73_wb_look_dualslot_overlay")
        m_end = src.index("static uint64_t fx6_state_hash", m_start)
        region = src[m_start:m_end]
        for forbidden in ("malloc(", "calloc(", "realloc(", "dlsym(", " abs("):
            self.assertNotIn(forbidden, region)

    def test_p73_26_guest_c_shim_compiles_if_zig_available(self) -> None:
        zig = build_live700.resolve_default_zig()
        if _force_clean_room() or not zig.is_file():
            self.skipTest("zig compiler skipped in clean-room / zig-absent environment")
        with tempfile.TemporaryDirectory(prefix="fx6_p73_zig_") as td:
            out_so = Path(td) / "fx6_live_guest_p73_test.so"
            info = build_live700.compile_shim(zig, out_so)
            self.assertTrue(out_so.is_file())
            self.assertGreater(int(info.get("bytes", out_so.stat().st_size)), 16384)


if __name__ == "__main__":
    unittest.main()
