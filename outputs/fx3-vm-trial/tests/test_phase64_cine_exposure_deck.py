#!/usr/bin/env python3
"""Phase 64 Unit & Integration Tests: Cinema Line Cine EI, Shutter Angle/ECS, S&Q (1-240fps), REC Tally & Wired I/O Deck.

Dual-mode safe:
- Passes 100% in both Local Donor mode and `FX3_FX6_FORCE_CLEAN_ROOM=1` mode.
- Never spawns any QEMU process and never touches port 8768.
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import json
import math
import os
import re
import shutil
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


class TestPhase64CineExposureDeck(unittest.TestCase):
    def _new_session(self, td: str) -> run_fx6_menu_trial.FX6LiveGpe0Session:
        return run_fx6_menu_trial.FX6LiveGpe0Session(Path(td) / "sess", port=18775)

    def test_p64_01_defaults_and_specs_complete(self) -> None:
        specs = run_fx6_menu_trial.CINE_EXPOSURE_SPECS
        self.assertEqual(specs["cine_ei_base"], ["800", "12800"])
        self.assertEqual(len(specs["ei_steps"]["800"]), 13)
        self.assertEqual(len(specs["ei_steps"]["12800"]), 13)
        self.assertEqual(specs["shutter_modes"], ["angle", "speed", "ecs"])
        self.assertEqual(specs["shutter_angle_range"], [5.6, 360.0])
        self.assertEqual(specs["shutter_speed_denom_range"], [24, 8000])
        self.assertEqual(specs["ecs_freq_hz_range"], [23.98, 7900.0])
        self.assertEqual(specs["sq_fps_range"], [1, 240])
        self.assertEqual(specs["tally_lamp_modes"], ["on", "front_only", "rear_only", "off"])
        self.assertEqual(specs["wired_io_modes"], ["off", "usblan_ptpip", "hdmi_raw16"])
        self.assertTrue(specs["p4_nd_hardware_absent"])
        self.assertTrue(specs["p12_bk4_airplane_mode_locked"])

        with tempfile.TemporaryDirectory(prefix="fx6_p64_01_") as td:
            sess = self._new_session(td)
            ce = sess.get_cine_exposure()
            self.assertEqual(ce["cine_ei_base"], "800")
            self.assertEqual(ce["ei_index"], 800)
            self.assertEqual(ce["over_stops"], 6.0)
            self.assertEqual(ce["under_stops"], 8.0)
            self.assertEqual(ce["total_stops"], 14.0)
            self.assertEqual(ce["shutter_mode"], "angle")
            self.assertEqual(ce["shutter_angle_deg"], 180.0)
            self.assertFalse(ce["sq_enabled"])
            self.assertFalse(ce["audio_rec_muted_by_sq"])
            self.assertEqual(ce["rec_state"], "STBY")
            self.assertEqual(ce["tally_lamp_mode"], "on")
            self.assertFalse(ce["tally_front_lit"])
            self.assertFalse(ce["tally_rear_lit"])
            self.assertEqual(ce["wired_io_mode"], "off")
            self.assertEqual(ce["nd_preset"], "Clear")
            self.assertTrue(ce["p4_nd_hardware_absent"])
            self.assertTrue(ce["wifi_bt_rf_disabled"])
            self.assertTrue(ce["p12_bk4_airplane_mode_locked"])
            self.assertEqual(sess.get_status()["cine_exposure"], ce)

    def test_p64_02_cine_ei_latitude_math_all_steps(self) -> None:
        # Low Base 800
        lat_400 = run_fx6_menu_trial.compute_cine_ei_latitude("800", 400)
        self.assertEqual((lat_400["over_stops"], lat_400["under_stops"]), (5.0, 9.0))
        self.assertEqual(lat_400["latitude_label"], "+5 / -9")

        lat_800 = run_fx6_menu_trial.compute_cine_ei_latitude("800", 800)
        self.assertEqual((lat_800["over_stops"], lat_800["under_stops"]), (6.0, 8.0))
        self.assertEqual(lat_800["latitude_label"], "+6 / -8")

        lat_1600 = run_fx6_menu_trial.compute_cine_ei_latitude("800", 1600)
        self.assertEqual((lat_1600["over_stops"], lat_1600["under_stops"]), (7.0, 7.0))
        self.assertEqual(lat_1600["latitude_label"], "+7 / -7")

        for base in ("800", "12800"):
            for idx, ei in enumerate(run_fx6_menu_trial.CINE_EI_STEPS[base]):
                lat = run_fx6_menu_trial.compute_cine_ei_latitude(base, ei)
                self.assertEqual(lat["ei_step_idx"], idx)
                self.assertAlmostEqual(lat["over_stops"] + lat["under_stops"], 14.0, places=2)

        # High Base 12800 bounds
        lat_low = run_fx6_menu_trial.compute_cine_ei_latitude("12800", 3200)
        lat_high = run_fx6_menu_trial.compute_cine_ei_latitude("12800", 51200)
        self.assertEqual((lat_low["over_stops"], lat_low["under_stops"]), (4.0, 10.0))
        self.assertEqual((lat_high["over_stops"], lat_high["under_stops"]), (8.0, 6.0))

    def test_p64_03_dual_base_ei_switching_and_mismatched_ei_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p64_03_") as td:
            sess = self._new_session(td)
            # Switching base without explicit ei_index snaps to new base ISO
            res1 = sess.set_cine_exposure({"cine_ei_base": "12800"})
            self.assertTrue(res1["ok"])
            self.assertEqual(res1["cine_exposure"]["cine_ei_base"], "12800")
            self.assertEqual(res1["cine_exposure"]["ei_index"], 12800)

            # Valid step on High Base
            res2 = sess.set_cine_exposure({"cine_ei_base": "12800", "ei_index": 25600})
            self.assertTrue(res2["ok"])
            self.assertEqual(res2["cine_exposure"]["over_stops"], 7.0)
            self.assertEqual(res2["cine_exposure"]["under_stops"], 7.0)

            # Invalid: EI 400 on High Base 12800
            bad1 = sess.set_cine_exposure({"ei_index": 400})
            self.assertFalse(bad1["ok"])
            self.assertEqual(bad1["error"], "invalid_ei_index")

            # Invalid: non-existent EI step 300 on Low Base 800
            bad2 = sess.set_cine_exposure({"cine_ei_base": "800", "ei_index": 300})
            self.assertFalse(bad2["ok"])
            self.assertEqual(bad2["error"], "invalid_ei_index")

            # State remains unchanged after fail-closed rejection
            self.assertEqual(sess.get_cine_exposure()["ei_index"], 25600)

    def test_p64_04_shutter_angle_presets_and_range_validation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p64_04_") as td:
            sess = self._new_session(td)
            for ang in (180.0, 172.8, 90.0, 45.0, 360.0, 5.6):
                r = sess.set_cine_exposure({"shutter_mode": "angle", "shutter_angle_deg": ang})
                self.assertTrue(r["ok"], msg=f"angle={ang} failed: {r}")
                self.assertEqual(r["cine_exposure"]["shutter_angle_deg"], ang)
                self.assertIn("°", r["cine_exposure"]["shutter_display"])

            for bad_ang in (5.5, 360.1, -90.0, True, "fast", float("nan")):
                r = sess.set_cine_exposure({"shutter_mode": "angle", "shutter_angle_deg": bad_ang})
                self.assertFalse(r["ok"], msg=f"bad_ang={bad_ang!r} should have been rejected")
                self.assertEqual(r["error"], "invalid_shutter_angle_deg")

    def test_p64_05_shutter_speed_and_ecs_modes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p64_05_") as td:
            sess = self._new_session(td)
            r_spd = sess.set_cine_exposure({"shutter_mode": "speed", "shutter_speed_denom": 96})
            self.assertTrue(r_spd["ok"])
            self.assertEqual(r_spd["cine_exposure"]["shutter_display"], "1/96")

            for bad_spd in (23, 8001, 48.5, False, "1/48"):
                r = sess.set_cine_exposure({"shutter_mode": "speed", "shutter_speed_denom": bad_spd})
                self.assertFalse(r["ok"])
                self.assertEqual(r["error"], "invalid_shutter_speed_denom")

            for ecs_hz in (23.98, 50.0, 60.0, 100.2, 120.0, 7900.0):
                r_ecs = sess.set_cine_exposure({"shutter_mode": "ecs", "ecs_freq_hz": ecs_hz})
                self.assertTrue(r_ecs["ok"])
                self.assertEqual(r_ecs["cine_exposure"]["shutter_mode"], "ecs")
                self.assertIn("ECS", r_ecs["cine_exposure"]["shutter_display"])

            for bad_ecs in (23.9, 7900.1, True, float("inf")):
                r = sess.set_cine_exposure({"shutter_mode": "ecs", "ecs_freq_hz": bad_ecs})
                self.assertFalse(r["ok"])
                self.assertEqual(r["error"], "invalid_ecs_freq_hz")

            r_mode = sess.set_cine_exposure({"shutter_mode": "shutter_sync"})
            self.assertFalse(r_mode["ok"])
            self.assertEqual(r_mode["error"], "invalid_shutter_mode")

    def test_p64_06_sq_motion_ratio_and_audio_mute_invariant(self) -> None:
        m_slow = run_fx6_menu_trial.compute_sq_motion_metrics(True, 23.98, 120)
        self.assertEqual(m_slow["motion_ratio"], 5.0)
        self.assertEqual(m_slow["motion_label"], "5.00x Slow")
        self.assertTrue(m_slow["audio_rec_muted_by_sq"])
        self.assertEqual(m_slow["effective_fps"], 120.0)

        m_quick = run_fx6_menu_trial.compute_sq_motion_metrics(True, 24.0, 4)
        self.assertEqual(m_quick["motion_ratio"], 0.17)
        self.assertEqual(m_quick["motion_label"], "0.17x Quick")
        self.assertTrue(m_quick["audio_rec_muted_by_sq"])

        m_norm = run_fx6_menu_trial.compute_sq_motion_metrics(False, 23.98, 120)
        self.assertEqual(m_norm["motion_ratio"], 1.0)
        self.assertEqual(m_norm["motion_label"], "1.00x Normal")
        self.assertFalse(m_norm["audio_rec_muted_by_sq"])
        self.assertEqual(m_norm["effective_fps"], 23.98)

        with tempfile.TemporaryDirectory(prefix="fx6_p64_06_") as td:
            sess = self._new_session(td)
            for bf in run_fx6_menu_trial.SQ_BASE_FPS_VALUES:
                r = sess.set_cine_exposure({"sq_enabled": True, "base_fps": bf, "sq_fps": 240})
                self.assertTrue(r["ok"])
                self.assertTrue(r["cine_exposure"]["audio_rec_muted_by_sq"])
            r_min = sess.set_cine_exposure({"sq_enabled": True, "base_fps": 24.0, "sq_fps": 1})
            self.assertTrue(r_min["ok"])
            self.assertIn("Quick", r_min["cine_exposure"]["motion_label"])

            r_off = sess.set_cine_exposure({"sq_enabled": False})
            self.assertTrue(r_off["ok"])
            self.assertFalse(r_off["cine_exposure"]["audio_rec_muted_by_sq"])

    def test_p64_07_sq_invalid_inputs_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p64_07_") as td:
            sess = self._new_session(td)
            for bad_sq in (0, 241, -1, 120.5, True, "abc"):
                r = sess.set_cine_exposure({"sq_fps": bad_sq})
                self.assertFalse(r["ok"])
                self.assertEqual(r["error"], "invalid_sq_fps")
            for bad_bf in (30.0, 120.0, True, "24p"):
                r = sess.set_cine_exposure({"base_fps": bad_bf})
                self.assertFalse(r["ok"])
                self.assertEqual(r["error"], "invalid_base_fps")
            for bad_en in ("yes", 1, 0):
                r = sess.set_cine_exposure({"sq_enabled": bad_en})
                self.assertFalse(r["ok"])
                self.assertEqual(r["error"], "invalid_sq_enabled")

    def test_p64_08_rec_state_timecode_and_tally_lamp_truth_table(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p64_08_") as td:
            sess = self._new_session(td)
            # STBY keeps tally lamps off regardless of tally_lamp_mode
            for mode in ("on", "front_only", "rear_only", "off"):
                r = sess.set_cine_exposure({"rec_state": "STBY", "tally_lamp_mode": mode})
                self.assertTrue(r["ok"])
                self.assertFalse(r["cine_exposure"]["tally_front_lit"])
                self.assertFalse(r["cine_exposure"]["tally_rear_lit"])

            # REC lights tally lamps according to tally_lamp_mode and advances rec_tc_frames
            r1 = sess.set_cine_exposure({"rec_state": "REC", "tally_lamp_mode": "on"})
            self.assertTrue(r1["ok"])
            self.assertTrue(r1["cine_exposure"]["tally_front_lit"])
            self.assertTrue(r1["cine_exposure"]["tally_rear_lit"])
            self.assertGreaterEqual(r1["cine_exposure"]["rec_tc_frames"], 1)

            r2 = sess.set_cine_exposure({"rec_state": "REC", "tally_lamp_mode": "front_only"})
            self.assertTrue(r2["cine_exposure"]["tally_front_lit"])
            self.assertFalse(r2["cine_exposure"]["tally_rear_lit"])
            self.assertGreater(r2["cine_exposure"]["rec_tc_frames"], r1["cine_exposure"]["rec_tc_frames"])

            r3 = sess.set_cine_exposure({"rec_state": "REC", "tally_lamp_mode": "rear_only"})
            self.assertFalse(r3["cine_exposure"]["tally_front_lit"])
            self.assertTrue(r3["cine_exposure"]["tally_rear_lit"])

            r4 = sess.set_cine_exposure({"rec_state": "REC", "tally_lamp_mode": "off"})
            self.assertFalse(r4["cine_exposure"]["tally_front_lit"])
            self.assertFalse(r4["cine_exposure"]["tally_rear_lit"])

            bad_rec = sess.set_cine_exposure({"rec_state": "PAUSE"})
            self.assertFalse(bad_rec["ok"])
            self.assertEqual(bad_rec["error"], "invalid_rec_state")

            bad_tally = sess.set_cine_exposure({"tally_lamp_mode": "blink"})
            self.assertFalse(bad_tally["ok"])
            self.assertEqual(bad_tally["error"], "invalid_tally_lamp_mode")

    def test_p64_09_wired_io_modes_and_p12_rf_off_invariant(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p64_09_") as td:
            sess = self._new_session(td)
            r_lan = sess.set_cine_exposure({"wired_io_mode": "usblan_ptpip"})
            self.assertTrue(r_lan["ok"])
            d_lan = r_lan["cine_exposure"]["wired_io_detail"]
            self.assertEqual(d_lan["usb_class"], "CDC-NCM")
            self.assertEqual(d_lan["ptpip_port"], 15740)
            self.assertTrue(d_lan["wifi_off"])
            self.assertTrue(d_lan["bt_off"])
            self.assertTrue(d_lan["p12_safe"])

            r_hdmi = sess.set_cine_exposure({"wired_io_mode": "hdmi_raw16"})
            self.assertTrue(r_hdmi["ok"])
            d_hdmi = r_hdmi["cine_exposure"]["wired_io_detail"]
            self.assertEqual(d_hdmi["resolution"], "4264x2408")
            self.assertEqual(d_hdmi["bit_depth"], 16)
            self.assertTrue(d_hdmi["mlut_clean_feed"])
            self.assertTrue(d_hdmi["wifi_off"])
            self.assertTrue(d_hdmi["bt_off"])

            # P12 Airplane-Mode strict rejections
            for tamper in (
                {"wifi_enabled": True},
                {"bt_enabled": True},
                {"wifi_bt_rf_disabled": False},
                {"p12_bk4_airplane_mode_locked": False},
            ):
                r_bad = sess.set_cine_exposure(tamper)
                self.assertFalse(r_bad["ok"])
                self.assertEqual(r_bad["error"], "p12_airplane_mode_locked")
                self.assertTrue(r_bad["wifi_bt_rf_disabled"])

            bad_io = sess.set_cine_exposure({"wired_io_mode": "wifi_ftp"})
            self.assertFalse(bad_io["ok"])
            self.assertEqual(bad_io["error"], "invalid_wired_io_mode")

    def test_p64_10_p4_nd_hardware_absence_lock_enforced(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p64_10_") as td:
            sess = self._new_session(td)
            # Clear is accepted
            r_clr = sess.set_cine_exposure({"nd_preset": "Clear"})
            self.assertTrue(r_clr["ok"])
            self.assertEqual(r_clr["cine_exposure"]["nd_preset"], "Clear")
            self.assertEqual(sess.p4_nd_reject_count, 0)

            # Any non-Clear preset rejects with p4_nd_hardware_absent and increments telemetry counters
            for bad_nd in ("1/4 ND", "1/16 ND", "1/128 ND", "Auto", 4):
                r_bad = sess.set_cine_exposure({"nd_preset": bad_nd})
                self.assertFalse(r_bad["ok"])
                self.assertEqual(r_bad["error"], "p4_nd_hardware_absent")
                self.assertTrue(r_bad["p4_nd_hardware_absent"])
                self.assertEqual(r_bad["nd_preset"], "Clear")
            self.assertEqual(sess.p4_nd_reject_count, 5)
            self.assertEqual(sess.p4_lock_attempts, 5)
            self.assertEqual(sess.cell_vals[3], 0)

    def test_p64_11_mailbox_mb28_31_packing_and_legacy_112b_compat(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p64_11_") as td:
            sess = self._new_session(td)
            # Legacy _pack_mailbox_bytes must stay 28*4=112 bytes for Phase 56 compat
            self.assertEqual(len(sess._pack_mailbox_bytes()), 28 * 4)
            self.assertEqual(len(sess._pack_phase64_mailbox_bytes()), 16)
            self.assertEqual(len(sess._pack_full_mailbox_bytes()), 32 * 4)

            sess.set_cine_exposure({
                "cine_ei_base": "12800",
                "ei_index": 25600,
                "shutter_mode": "ecs",
                "ecs_freq_hz": 100.2,
                "sq_enabled": True,
                "base_fps": 29.97,
                "sq_fps": 120,
                "rec_state": "REC",
                "tally_lamp_mode": "rear_only",
                "wired_io_mode": "hdmi_raw16",
            })
            mb28, mb29, mb30, mb31 = struct.unpack("<4I", sess._pack_phase64_mailbox_bytes())
            self.assertEqual(mb31, 0x43494E45)
            self.assertEqual(mb28 & 1, 1)  # base 12800
            self.assertEqual((mb28 >> 1) & 0xF, 9)  # 25600 is index 9 in Base 12800 steps
            self.assertEqual((mb28 >> 5) & 0x3, 2)  # ecs
            self.assertEqual((mb28 >> 7) & 0x1, 1)  # sq_enabled
            self.assertEqual((mb28 >> 8) & 0x7, 3)  # 29.97
            self.assertEqual((mb28 >> 11) & 0x1, 1)  # REC
            self.assertEqual((mb28 >> 12) & 0x3, 2)  # rear_only
            self.assertEqual((mb28 >> 14) & 0x3, 2)  # hdmi_raw16
            self.assertEqual((mb28 >> 16) & 0x3, 3)  # P4=1, P12=1
            self.assertEqual((mb28 >> 31) & 0x1, 1)  # valid
            self.assertEqual(mb29 & 0xFFFFF, 10020)  # 100.2 * 100
            self.assertEqual((mb29 >> 20) & 0xFF, 120)
            self.assertGreaterEqual(mb30, 1)

    def test_p64_12_cine_exp_command_formatting(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p64_12_") as td:
            sess = self._new_session(td)
            r = sess.set_cine_exposure({
                "cine_ei_base": "800",
                "ei_index": 1600,
                "shutter_mode": "ecs",
                "ecs_freq_hz": 100.2,
                "sq_enabled": True,
                "base_fps": 23.98,
                "sq_fps": 120,
                "rec_state": "REC",
                "tally_lamp_mode": "front_only",
                "wired_io_mode": "usblan_ptpip",
            })
            cmd = r["cine_exp_cmd"]
            self.assertIn("CINE_EXP base=800 ei=1600 lat=+7/-7", cmd)
            self.assertIn("shutter=ecs:100.20Hz", cmd)
            self.assertIn("sq=1:23.98:120", cmd)
            self.assertIn("rec=REC tally=front_only io=usblan_ptpip", cmd)
            self.assertIn("nd=Clear p12=1", cmd)

    def test_p64_13_guest_c_source_phase64_invariants(self) -> None:
        c_path = TRIAL_DIR / "src" / "fx6_live_guest.c"
        src = c_path.read_text(encoding="utf-8")
        for token in (
            "fx6_render_phase64_cine_exposure_overlay",
            "g_live_p64_flags",
            "g_live_p64_shutter_sq",
            "g_live_p64_tc",
            "0x43494e45u",
            "CH1-4 MUTE",
            "HDMI RAW16 4.2K",
            "LAN PTP-IP P12-SAFE",
            "P4:ND-CLR",
            "CINE_EXP=0x%08x:0x%08x:%u",
        ):
            self.assertIn(token, src)

        # Ensure Phase 64 C helper remains allocation-free and avoids abs()
        m_start = src.index("static void fx6_render_phase64_cine_exposure_overlay")
        m_end = src.index("static uint64_t fx6_state_hash", m_start)
        region = src[m_start:m_end]
        for forbidden in ("malloc(", "calloc(", "realloc(", "dlsym(", " abs("):
            self.assertNotIn(forbidden, region)

    def test_p64_14_guest_c_shim_compiles_if_zig_available(self) -> None:
        zig = build_live700.resolve_default_zig()
        if _force_clean_room() or not zig.is_file():
            self.skipTest("zig compiler skipped in clean-room / zig-absent environment")
        with tempfile.TemporaryDirectory(prefix="fx6_p64_zig_") as td:
            out_so = Path(td) / "fx6_live_guest_test.so"
            info = build_live700.compile_shim(zig, out_so)
            self.assertTrue(out_so.is_file())
            self.assertGreater(int(info.get("bytes", out_so.stat().st_size)), 16384)

    def test_p64_15_camset_export_and_import_roundtrip_with_cine_exposure(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p64_camset_") as td:
            sess = self._new_session(td)
            sess.set_cine_exposure({
                "cine_ei_base": "12800",
                "ei_index": 25600,
                "shutter_mode": "ecs",
                "ecs_freq_hz": 100.2,
                "sq_enabled": True,
                "base_fps": 29.97,
                "sq_fps": 120,
                "rec_state": "REC",
                "tally_lamp_mode": "rear_only",
                "wired_io_mode": "hdmi_raw16",
            })
            exported = sess.export_camset_preset()
            self.assertTrue(exported["ok"])
            self.assertIn("cine_exposure", exported)
            self.assertEqual(exported["cine_exposure"]["ei_index"], 25600)
            self.assertEqual(exported["cine_exposure"]["ecs_freq_hz"], 100.2)
            self.assertEqual(exported["cine_exposure"]["wired_io_mode"], "hdmi_raw16")

            # Mutate everything back to defaults
            sess.set_cine_exposure({"reset": True})
            self.assertEqual(sess.get_cine_exposure()["ei_index"], 800)
            self.assertEqual(sess.get_cine_exposure()["wired_io_mode"], "off")

            imp = sess.import_camset_preset(exported)
            self.assertTrue(imp["ok"])
            ce = imp["cine_exposure"]
            self.assertEqual(ce["cine_ei_base"], "12800")
            self.assertEqual(ce["ei_index"], 25600)
            self.assertEqual(ce["shutter_mode"], "ecs")
            self.assertEqual(ce["ecs_freq_hz"], 100.2)
            self.assertTrue(ce["sq_enabled"])
            self.assertEqual(ce["sq_fps"], 120)
            self.assertEqual(ce["rec_state"], "REC")
            self.assertEqual(ce["tally_lamp_mode"], "rear_only")
            self.assertEqual(ce["wired_io_mode"], "hdmi_raw16")
            self.assertTrue(ce["audio_rec_muted_by_sq"])

    def test_p64_16_camset_legacy_backward_compat_and_fail_closed_tamper(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p64_legacy_") as td:
            sess = self._new_session(td)
            legacy_camset = sess.export_camset_preset()
            legacy_camset.pop("cine_exposure", None)
            legacy_camset.pop("assist_tools", None)
            legacy_camset["cinema_params"]["wb"] = "3200K"
            imp_ok = sess.import_camset_preset(legacy_camset)
            self.assertTrue(imp_ok["ok"])
            self.assertEqual(imp_ok["cinema_params"]["values"]["wb"], "3200K")

            # Invalid cine_exposure in CAMSET fails closed without mutating
            bad_camset = sess.export_camset_preset()
            bad_camset["cine_exposure"]["sq_fps"] = 999
            bad_camset["cinema_params"]["wb"] = "4300K"
            imp_bad = sess.import_camset_preset(bad_camset)
            self.assertFalse(imp_bad["ok"])
            self.assertEqual(imp_bad["error"], "invalid_sq_fps")
            self.assertEqual(sess.get_cinema_params()["values"]["wb"], "3200K")

            # P4 ND tamper + P12 RF tamper inside cine_exposure clamps & records telemetry
            tamper_camset = sess.export_camset_preset()
            tamper_camset["cine_exposure"]["nd_preset"] = "1/64 ND"
            tamper_camset["cine_exposure"]["wifi_enabled"] = True
            imp_t = sess.import_camset_preset(tamper_camset)
            self.assertTrue(imp_t["ok"])
            self.assertTrue(imp_t["p4_nd_rejected"])
            self.assertTrue(imp_t["p12_bk4_clamped"])
            self.assertEqual(imp_t["cine_exposure"]["nd_preset"], "Clear")
            self.assertTrue(imp_t["cine_exposure"]["wifi_bt_rf_disabled"])

    def test_p64_17_set_cinema_param_syncs_cine_exposure(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p64_sync_") as td:
            sess = self._new_session(td)
            sess.set_cinema_param("fps", preset="59.94p")
            sess.set_cinema_param("ei", preset="12800 EI (12800 Base)")
            sess.set_cinema_param("shutter", preset="1/100")
            ce = sess.get_cine_exposure()
            self.assertEqual(ce["base_fps"], 59.94)
            self.assertEqual(ce["cine_ei_base"], "12800")
            self.assertEqual(ce["ei_index"], 12800)
            self.assertEqual(ce["shutter_mode"], "speed")
            self.assertEqual(ce["shutter_speed_denom"], 100)

    def test_p64_18_http_api_get_post_cine_exposure_and_status(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p64_http_") as td:
            sess = self._new_session(td)
            srv = run_fx6_menu_trial.HardenedThreadingHTTPServer(
                ("127.0.0.1", 0), run_fx6_menu_trial.make_handler(sess)
            )
            port = srv.server_address[1]
            t = threading.Thread(target=srv.serve_forever, kwargs={"poll_interval": 0.02}, daemon=True)
            t.start()
            try:
                base = f"http://127.0.0.1:{port}"
                g0 = json.loads(urllib.request.urlopen(f"{base}/api/cine_exposure", timeout=5).read().decode("utf-8"))
                self.assertTrue(g0["ok"])
                self.assertEqual(g0["cine_exposure"]["ei_index"], 800)
                self.assertIn("specs", g0)

                req = urllib.request.Request(
                    f"{base}/api/cine_exposure",
                    data=json.dumps({
                        "rec_state": "REC",
                        "tally_lamp_mode": "front_only",
                        "sq_enabled": True,
                        "base_fps": 23.98,
                        "sq_fps": 120,
                        "shutter_mode": "ecs",
                        "ecs_freq_hz": 100.2,
                        "wired_io_mode": "usblan_ptpip",
                    }).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                p_res = json.loads(urllib.request.urlopen(req, timeout=5).read().decode("utf-8"))
                self.assertTrue(p_res["ok"])
                self.assertEqual(p_res["cine_exposure"]["rec_state"], "REC")
                self.assertTrue(p_res["cine_exposure"]["tally_front_lit"])
                self.assertFalse(p_res["cine_exposure"]["tally_rear_lit"])
                self.assertEqual(p_res["cine_exposure"]["motion_label"], "5.00x Slow")
                self.assertTrue(p_res["cine_exposure"]["audio_rec_muted_by_sq"])
                self.assertEqual(p_res["cine_exposure"]["wired_io_detail"]["ptpip_port"], 15740)

                st = json.loads(urllib.request.urlopen(f"{base}/api/status", timeout=5).read().decode("utf-8"))
                self.assertEqual(st["cine_exposure"]["rec_state"], "REC")
                self.assertEqual(st["cine_exposure"]["ecs_freq_hz"], 100.2)
            finally:
                srv.shutdown()
                srv.server_close()

    def test_p64_19_http_api_post_cine_exposure_400_on_bad_inputs(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p64_http_err_") as td:
            sess = self._new_session(td)
            srv = run_fx6_menu_trial.HardenedThreadingHTTPServer(
                ("127.0.0.1", 0), run_fx6_menu_trial.make_handler(sess)
            )
            port = srv.server_address[1]
            t = threading.Thread(target=srv.serve_forever, kwargs={"poll_interval": 0.02}, daemon=True)
            t.start()
            try:
                base = f"http://127.0.0.1:{port}"
                for raw_body, expected_err in (
                    (b"{bad json", "invalid_json"),
                    (json.dumps({"sq_fps": 300}).encode("utf-8"), "invalid_sq_fps"),
                    (json.dumps({"nd_preset": "1/8 ND"}).encode("utf-8"), "p4_nd_hardware_absent"),
                    (json.dumps({"wifi_enabled": True}).encode("utf-8"), "p12_airplane_mode_locked"),
                ):
                    req = urllib.request.Request(
                        f"{base}/api/cine_exposure",
                        data=raw_body,
                        headers={"Content-Type": "application/json"},
                        method="POST",
                    )
                    with self.assertRaises(urllib.error.HTTPError) as ctx:
                        urllib.request.urlopen(req, timeout=5)
                    self.assertEqual(ctx.exception.code, 400)
                    err_obj = json.loads(ctx.exception.read().decode("utf-8"))
                    self.assertFalse(err_obj["ok"])
                    self.assertEqual(err_obj["error"], expected_err)
            finally:
                srv.shutdown()
                srv.server_close()

    def test_p64_20_http_api_camset_export_and_import_aliases(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p64_http_camset_") as td:
            sess = self._new_session(td)
            srv = run_fx6_menu_trial.HardenedThreadingHTTPServer(
                ("127.0.0.1", 0), run_fx6_menu_trial.make_handler(sess)
            )
            port = srv.server_address[1]
            t = threading.Thread(target=srv.serve_forever, kwargs={"poll_interval": 0.02}, daemon=True)
            t.start()
            try:
                base = f"http://127.0.0.1:{port}"
                sess.set_cine_exposure({"ei_index": 1600, "wired_io_mode": "hdmi_raw16", "rec_state": "REC"})
                c_exp = json.loads(urllib.request.urlopen(f"{base}/api/camset_export", timeout=5).read().decode("utf-8"))
                p_exp = json.loads(urllib.request.urlopen(f"{base}/api/preset_export", timeout=5).read().decode("utf-8"))
                self.assertEqual(c_exp["preset_sha256"], p_exp["preset_sha256"])
                self.assertEqual(c_exp["cine_exposure"]["wired_io_mode"], "hdmi_raw16")

                sess.set_cine_exposure({"reset": True})
                req = urllib.request.Request(
                    f"{base}/api/camset_import",
                    data=json.dumps(c_exp).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                imp = json.loads(urllib.request.urlopen(req, timeout=5).read().decode("utf-8"))
                self.assertTrue(imp["ok"])
                self.assertEqual(imp["cine_exposure"]["ei_index"], 1600)
                self.assertEqual(imp["cine_exposure"]["wired_io_mode"], "hdmi_raw16")
                self.assertEqual(imp["cine_exposure"]["rec_state"], "REC")
            finally:
                srv.shutdown()
                srv.server_close()

    def test_p64_21_html_ui_contains_phase64_deck_and_bilingual_controls(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p64_html_") as td:
            sess = self._new_session(td)
            srv = run_fx6_menu_trial.HardenedThreadingHTTPServer(
                ("127.0.0.1", 0), run_fx6_menu_trial.make_handler(sess)
            )
            port = srv.server_address[1]
            t = threading.Thread(target=srv.serve_forever, kwargs={"poll_interval": 0.02}, daemon=True)
            t.start()
            try:
                html = urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=5).read().decode("utf-8")
                for needle in (
                    "phase64-cine-exposure-card",
                    "/api/cine_exposure",
                    "p64-ei-base-select",
                    "p64-ei-index-select",
                    "p64-shutter-mode-select",
                    "p64-sq-btn",
                    "p64-rec-btn",
                    "p64-tally-select",
                    "p64-wired-io-select",
                    "HDMI 16-bit Linear RAW 4264x2408",
                    "USB-LAN CDC-NCM + PTP-IP 15740",
                    "简体中文",
                    "繁體中文",
                    "日本語",
                ):
                    self.assertIn(needle, html)
            finally:
                srv.shutdown()
                srv.server_close()

    def test_p64_22_json_serialization_clean_without_bytes_repr(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p64_json_") as td:
            sess = self._new_session(td)
            sess.set_cine_exposure({"rec_state": "REC", "sq_enabled": True, "sq_fps": 120, "wired_io_mode": "hdmi_raw16"})
            rendered = json.dumps(sess.export_camset_preset(), ensure_ascii=False)
            self.assertNotRegex(rendered, r'(?<![0-9A-Za-z_/.-])b[\'"]')

    def test_p64_23_shutter_angle_rounding_and_ecs_precision(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p64_round_") as td:
            sess = self._new_session(td)
            r1 = sess.set_cine_exposure({"shutter_mode": "angle", "shutter_angle_deg": 172.84})
            self.assertTrue(r1["ok"])
            self.assertEqual(r1["cine_exposure"]["shutter_angle_deg"], 172.8)
            r2 = sess.set_cine_exposure({"shutter_mode": "ecs", "ecs_freq_hz": 100.246})
            self.assertTrue(r2["ok"])
            self.assertEqual(r2["cine_exposure"]["ecs_freq_hz"], 100.25)

    def test_p64_24_rec_tc_reset_on_explicit_reset(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p64_tc_") as td:
            sess = self._new_session(td)
            sess.set_cine_exposure({"rec_state": "REC"})
            sess.set_cine_exposure({"rec_state": "REC"})
            self.assertGreaterEqual(sess.get_cine_exposure()["rec_tc_frames"], 2)
            r_rst = sess.set_cine_exposure({"reset": True})
            self.assertTrue(r_rst["ok"])
            self.assertEqual(r_rst["cine_exposure"]["rec_state"], "STBY")
            self.assertEqual(r_rst["cine_exposure"]["rec_tc_frames"], 0)
            self.assertEqual(r_rst["cine_exposure"]["rec_tc"], "00:00:00:00")

    def test_p64_25_clean_room_mode_compatibility(self) -> None:
        prev = os.environ.get("FX3_FX6_FORCE_CLEAN_ROOM")
        os.environ["FX3_FX6_FORCE_CLEAN_ROOM"] = "1"
        try:
            with tempfile.TemporaryDirectory(prefix="fx6_p64_cr_") as td:
                sess = self._new_session(td)
                r = sess.set_cine_exposure({
                    "cine_ei_base": "12800",
                    "ei_index": 6400,
                    "shutter_mode": "ecs",
                    "ecs_freq_hz": 50.0,
                    "sq_enabled": True,
                    "sq_fps": 60,
                    "wired_io_mode": "usblan_ptpip",
                })
                self.assertTrue(r["ok"])
                self.assertEqual(r["cine_exposure"]["over_stops"], 5.0)
                self.assertEqual(r["cine_exposure"]["under_stops"], 9.0)
                self.assertFalse(r["wrote_mailbox"])
                self.assertFalse(r["guest_synced"])
        finally:
            if prev is None:
                os.environ.pop("FX3_FX6_FORCE_CLEAN_ROOM", None)
            else:
                os.environ["FX3_FX6_FORCE_CLEAN_ROOM"] = prev

    def test_p64_26_backward_compatibility_phases_19_through_56_endpoints(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p64_compat_") as td:
            sess = self._new_session(td)
            srv = run_fx6_menu_trial.HardenedThreadingHTTPServer(
                ("127.0.0.1", 0), run_fx6_menu_trial.make_handler(sess)
            )
            port = srv.server_address[1]
            t = threading.Thread(target=srv.serve_forever, kwargs={"poll_interval": 0.02}, daemon=True)
            t.start()
            try:
                base = f"http://127.0.0.1:{port}"
                st = json.loads(urllib.request.urlopen(f"{base}/api/status", timeout=5).read().decode("utf-8"))
                self.assertIn("cine_exposure", st)
                self.assertIn("assist_tools", st)
                p128 = json.loads(urllib.request.urlopen(f"{base}/api/pages128", timeout=5).read().decode("utf-8"))
                self.assertIsInstance(p128, list)
                self.assertGreaterEqual(len(p128), 128)
                for route in (
                    "/api/menu_catalog",
                    "/api/assist_tools",
                    "/api/scope_stats",
                    "/api/cine_exposure",
                    "/api/camset_export",
                    "/api/preset_export",
                ):
                    obj = json.loads(urllib.request.urlopen(f"{base}{route}", timeout=5).read().decode("utf-8"))
                    self.assertTrue(obj["ok"], msg=f"{route} returned ok=False: {obj}")
            finally:
                srv.shutdown()
                srv.server_close()


if __name__ == "__main__":
    unittest.main()
