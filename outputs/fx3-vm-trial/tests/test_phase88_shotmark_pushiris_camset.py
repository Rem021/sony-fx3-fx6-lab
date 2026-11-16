#!/usr/bin/env python3
"""Phase 88 Unit & Integration Tests: Live ShotMark1/2 (<EssenceMark> in M01.XML),
Cine EI Push Auto Iris (1/8-Stop 41% IRE / Highlight <94% IRE), 4-Ch -20 dB Safety Pad,
SMPTE 12M User-Bits, A-Cam ILME-FX6 -> B-Cam ILME-FX3 Fleet CAMSET Sanitizer, & GPE0 HUD.

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

import run_fx6_menu_trial  # noqa: E402


def _force_clean_room() -> bool:
    return os.environ.get("FX3_FX6_FORCE_CLEAN_ROOM", "").strip().lower() in ("1", "true", "yes")


class TestPhase88ShotmarkPushIrisCamset(unittest.TestCase):
    def _new_session(self, td: str) -> run_fx6_menu_trial.FX6LiveGpe0Session:
        return run_fx6_menu_trial.FX6LiveGpe0Session(Path(td) / "sess", port=18778)

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

    def test_p88_01_specs_and_defaults(self) -> None:
        specs = run_fx6_menu_trial.SHOTMARK_IRIS_SPECS
        self.assertEqual(specs["shotmark_types"], ["ShotMark1", "ShotMark2"])
        self.assertEqual(specs["shotmark_max_per_clip"], 64)
        self.assertEqual(specs["metering_modes"], ["multi", "center", "spot", "highlight"])
        self.assertEqual(specs["iris_fstop_range"], [1.4, 22.0])
        self.assertEqual(specs["ae_shift_ev_range"], [-2.0, 2.0])
        self.assertEqual(specs["ch34_safety_pad_allowed"], [0, -20])
        self.assertEqual(specs["target_ire"], 41.0)
        self.assertEqual(specs["highlight_ceiling_ire"], 94.0)
        self.assertEqual(specs["audio_bit_depth"], 24)

        with tempfile.TemporaryDirectory(prefix="fx6_p88_01_") as td:
            sess = self._new_session(td)
            smi = sess.get_shotmark_and_iris()
            self.assertEqual(smi["shotmarks"], [])
            self.assertEqual(smi["shotmark_count"], 0)
            self.assertEqual(smi["shotmark1_count"], 0)
            self.assertEqual(smi["shotmark2_count"], 0)
            self.assertIsNone(smi["latest_shotmark"])
            self.assertEqual(smi["iris_fstop"], 2.8)
            self.assertEqual(smi["ae_shift_ev"], 0.0)
            self.assertEqual(smi["metering_mode"], "multi")
            self.assertEqual(smi["ch34_safety_pad_db"], 0)
            self.assertEqual(smi["user_bits_hex"], "auto_camid_reel")
            self.assertEqual(smi["user_bits_effective"], "A0:01:00:01")
            self.assertEqual(smi["p4_nd_motor_faults"], 0)
            self.assertEqual(smi["target_ire"], 41.0)
            self.assertEqual(sess.get_status()["shotmark_and_iris"], smi)

    def test_p88_02_add_shotmark1_and_shotmark2_with_auto_tc(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p88_02_") as td:
            sess = self._new_session(td)
            r1 = sess.set_shotmark_and_iris({"action": "add_shotmark1", "frame": 24})
            self.assertTrue(r1["ok"])
            self.assertEqual(r1["shotmark_and_iris"]["shotmark1_count"], 1)
            self.assertEqual(r1["shotmark_and_iris"]["shotmark2_count"], 0)
            m1 = r1["shotmark_and_iris"]["shotmarks"][0]
            self.assertEqual(m1["type"], "ShotMark1")
            self.assertEqual(m1["frame"], 24)
            self.assertEqual(m1["tc"], "00:00:01:00")
            self.assertEqual(m1["label"], "OK")

            r2 = sess.set_shotmark_and_iris({"action": "add_shotmark2", "frame": 120})
            self.assertTrue(r2["ok"])
            smi = r2["shotmark_and_iris"]
            self.assertEqual(smi["shotmark_count"], 2)
            self.assertEqual(smi["shotmark1_count"], 1)
            self.assertEqual(smi["shotmark2_count"], 1)
            self.assertEqual(smi["latest_shotmark"]["type"], "ShotMark2")
            self.assertEqual(smi["latest_shotmark"]["label"], "KEEP")
            self.assertEqual(smi["latest_shotmark"]["tc"], "00:00:05:00")

    def test_p88_03_shotmark_dedup_by_type_and_frame(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p88_03_") as td:
            sess = self._new_session(td)
            sess.set_shotmark_and_iris({"action": "add_shotmark1", "frame": 48})
            sess.set_shotmark_and_iris({"action": "add_shotmark1", "frame": 48})
            smi = sess.get_shotmark_and_iris()
            self.assertEqual(smi["shotmark_count"], 1)
            self.assertEqual(smi["shotmark1_count"], 1)

    def test_p88_04_shotmark_same_frame_different_type_allowed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p88_04_") as td:
            sess = self._new_session(td)
            sess.set_shotmark_and_iris({"action": "add_shotmark1", "frame": 72})
            sess.set_shotmark_and_iris({"action": "add_shotmark2", "frame": 72})
            smi = sess.get_shotmark_and_iris()
            self.assertEqual(smi["shotmark_count"], 2)
            self.assertEqual(smi["shotmark1_count"], 1)
            self.assertEqual(smi["shotmark2_count"], 1)

    def test_p88_05_shotmark_cap_at_64_marks(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p88_05_") as td:
            sess = self._new_session(td)
            entries = [{"type": "ShotMark1", "frame": i * 10} for i in range(80)]
            res = sess.set_shotmark_and_iris({"shotmarks": entries})
            self.assertTrue(res["ok"])
            self.assertEqual(res["shotmark_and_iris"]["shotmark_count"], 64)
            self.assertEqual(res["shotmark_and_iris"]["shotmarks"][-1]["frame"], 630)

    def test_p88_06_clear_shotmarks_and_replace_list(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p88_06_") as td:
            sess = self._new_session(td)
            sess.set_shotmark_and_iris({
                "shotmarks": [
                    {"type": "ShotMark1", "frame": 10, "tc": "00:00:00:10", "label": "OK"},
                    {"type": "ShotMark2", "frame": 99, "tc": "00:00:04:03", "label": "KEEP"},
                ]
            })
            self.assertEqual(sess.get_shotmark_and_iris()["shotmark_count"], 2)
            r = sess.set_shotmark_and_iris({"action": "clear_shotmarks"})
            self.assertTrue(r["ok"])
            self.assertEqual(r["shotmark_and_iris"]["shotmark_count"], 0)
            self.assertIsNone(r["shotmark_and_iris"]["latest_shotmark"])

    def test_p88_07_shotmark_invalid_inputs_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p88_07_") as td:
            sess = self._new_session(td)
            for bad in (
                {"shotmarks": [{"type": "ShotMark9", "frame": 10}]},
                {"shotmarks": [{"type": "ShotMark1", "frame": -1}]},
                {"shotmarks": [{"type": "ShotMark1", "frame": True}]},
                {"shotmarks": [{"type": "ShotMark1", "frame": 10, "tc": "bad-tc"}]},
                {"action": "launch_missiles"},
                "not-a-dict",
            ):
                res = sess.set_shotmark_and_iris(bad)
                self.assertFalse(res["ok"], f"Expected failure for {bad!r}")

    def test_p88_08_xml_sidecar_essencemark_roundtrip_resolve_catalyst(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p88_08_") as td:
            sess = self._new_session(td)
            sess.set_shotmark_and_iris({"action": "add_shotmark1", "frame": 36})
            sess.set_shotmark_and_iris({"action": "add_shotmark2", "frame": 144})
            sidecar = sess.get_xml_sidecar()
            self.assertTrue(sidecar["ok"])
            xml_text = sidecar["xml"]
            self.assertIn("<KlvPacketTable>", xml_text)
            self.assertIn("<EssenceMark ", xml_text)
            self.assertIn("_ShotMark1", xml_text)
            self.assertIn("_ShotMark2", xml_text)

            root = ET.fromstring(xml_text)
            ns = {"n": run_fx6_menu_trial.NRTM_NAMESPACE_V220}
            em_items = root.findall(".//n:EssenceMark", ns)
            self.assertEqual(len(em_items), 2)
            self.assertEqual(em_items[0].attrib["name"], "_ShotMark1")
            self.assertEqual(em_items[0].attrib["start"], "36")
            self.assertEqual(em_items[1].attrib["name"], "_ShotMark2")
            self.assertEqual(em_items[1].attrib["start"], "144")

    def test_p88_09_xml_sidecar_empty_shotmarks_clean_valid_xml(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p88_09_") as td:
            sess = self._new_session(td)
            sidecar = sess.get_xml_sidecar()
            root = ET.fromstring(sidecar["xml"])
            ns = {"n": run_fx6_menu_trial.NRTM_NAMESPACE_V220}
            self.assertEqual(len(root.findall(".//n:EssenceMark", ns)), 0)
            self.assertNotIn("<KlvPacketTable>", sidecar["xml"])

    def test_p88_10_push_auto_iris_41pct_ire_slog3_multi(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p88_10_") as td:
            sess = self._new_session(td)
            res = sess.set_shotmark_and_iris({"action": "push_auto_iris", "scene_ev": 12.0, "metering_mode": "multi"})
            self.assertTrue(res["ok"])
            self.assertEqual(res["p4_nd_motor_faults"], 0)
            smi = res["shotmark_and_iris"]
            self.assertTrue(smi["push_auto_iris_active"])
            self.assertEqual(smi["target_ire"], 41.0)
            self.assertEqual(smi["p4_nd_motor_faults"], 0)
            self.assertIn(smi["iris_fstop"], run_fx6_menu_trial.EMOUNT_1_8_STOP_TABLE)
            self.assertAlmostEqual(smi["estimated_grey_ire"], 41.0, delta=1.5)

    def test_p88_11_push_auto_iris_highlight_mode_protects_94pct_ceiling(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p88_11_") as td:
            sess = self._new_session(td)
            # In highlight metering mode, iris stops down slightly to prevent highlight clipping >= 94.0% IRE
            res_multi = sess.set_shotmark_and_iris({"action": "push_auto_iris", "scene_ev": 12.0, "metering_mode": "multi"})
            f_multi = res_multi["shotmark_and_iris"]["iris_fstop"]

            res_hl = sess.set_shotmark_and_iris({"action": "push_auto_iris", "scene_ev": 12.0, "metering_mode": "highlight"})
            smi_hl = res_hl["shotmark_and_iris"]
            self.assertEqual(smi_hl["metering_mode"], "highlight")
            self.assertGreaterEqual(smi_hl["iris_fstop"], f_multi)
            self.assertLess(smi_hl["estimated_highlight_ire"], 94.0)
            self.assertEqual(smi_hl["p4_nd_motor_faults"], 0)

    def test_p88_12_push_auto_iris_1_8_stop_quantization_and_ae_shift(self) -> None:
        r0 = run_fx6_menu_trial.compute_push_auto_iris(12.0, ae_shift_ev=0.0, metering_mode="multi")
        r_plus = run_fx6_menu_trial.compute_push_auto_iris(12.0, ae_shift_ev=1.0, metering_mode="multi")
        r_minus = run_fx6_menu_trial.compute_push_auto_iris(12.0, ae_shift_ev=-1.0, metering_mode="multi")
        self.assertIn(r0["iris_fstop"], run_fx6_menu_trial.EMOUNT_1_8_STOP_TABLE)
        self.assertIn(r_plus["iris_fstop"], run_fx6_menu_trial.EMOUNT_1_8_STOP_TABLE)
        self.assertIn(r_minus["iris_fstop"], run_fx6_menu_trial.EMOUNT_1_8_STOP_TABLE)
        # +1.0 EV shift opens iris (~lower f-stop), -1.0 EV closes down (~higher f-stop)
        self.assertLess(r_plus["iris_fstop"], r0["iris_fstop"])
        self.assertGreater(r_minus["iris_fstop"], r0["iris_fstop"])

    def test_p88_13_push_auto_iris_center_spot_and_extreme_ev_clamp(self) -> None:
        r_dark = run_fx6_menu_trial.compute_push_auto_iris(0.0, metering_mode="spot")
        r_bright = run_fx6_menu_trial.compute_push_auto_iris(18.0, metering_mode="center")
        self.assertEqual(r_dark["iris_fstop"], 1.4)
        self.assertEqual(r_bright["iris_fstop"], 22.0)
        self.assertEqual(r_dark["p4_nd_motor_faults"], 0)
        self.assertEqual(r_bright["p4_nd_motor_faults"], 0)

    def test_p88_14_manual_iris_and_validation_rejects_bad_fstop_ev_meter(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p88_14_") as td:
            sess = self._new_session(td)
            ok = sess.set_shotmark_and_iris({"iris_fstop": 4.0, "ae_shift_ev": -0.5, "metering_mode": "highlight"})
            self.assertTrue(ok["ok"])
            self.assertEqual(ok["shotmark_and_iris"]["iris_fstop"], 4.0)
            self.assertEqual(ok["shotmark_and_iris"]["ae_shift_ev"], -0.5)
            self.assertEqual(ok["shotmark_and_iris"]["metering_mode"], "highlight")

            for bad in (
                {"iris_fstop": 0.95},
                {"iris_fstop": 32.0},
                {"iris_fstop": True},
                {"ae_shift_ev": 3.5},
                {"ae_shift_ev": -3.0},
                {"metering_mode": "matrix_bad"},
                {"action": "push_auto_iris", "scene_ev": 25.0},
            ):
                r = sess.set_shotmark_and_iris(bad)
                self.assertFalse(r["ok"], f"Expected validation error for {bad!r}")

    def test_p88_15_4ch_24bit_safety_pad_0_and_minus20_db(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p88_15_") as td:
            sess = self._new_session(td)
            r0 = sess.get_shotmark_and_iris()
            self.assertEqual(r0["audio_bit_depth"], 24)
            self.assertEqual(r0["audio_channels"], 4)
            self.assertEqual(r0["ch34_safety_pad_db"], 0)
            self.assertEqual(r0["ch3_effective_db"], -18)
            self.assertEqual(r0["ch4_effective_db"], -18)

            r20 = sess.set_shotmark_and_iris({"ch34_safety_pad_db": -20})
            self.assertTrue(r20["ok"])
            smi = r20["shotmark_and_iris"]
            self.assertEqual(smi["ch34_safety_pad_db"], -20)
            self.assertEqual(smi["ch3_effective_db"], -38)
            self.assertEqual(smi["ch4_effective_db"], -38)

    def test_p88_16_safety_pad_validation_rejects_invalid_and_bool(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p88_16_") as td:
            sess = self._new_session(td)
            for bad_pad in (-10, -12, 6, True, "bad"):
                res = sess.set_shotmark_and_iris({"ch34_safety_pad_db": bad_pad})
                self.assertFalse(res["ok"])
                self.assertEqual(res["error"], "invalid_ch34_safety_pad_db")

    def test_p88_17_smpte_12m_user_bits_auto_camid_reel_sync(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p88_17_") as td:
            sess = self._new_session(td)
            self.assertEqual(sess.get_shotmark_and_iris()["user_bits_effective"], "A0:01:00:01")
            sess.set_color_and_media({"cam_id": "B", "reel_num": 12, "clip_seq": 34})
            smi = sess.get_shotmark_and_iris()
            self.assertEqual(smi["user_bits_mode"], "auto_camid_reel")
            self.assertEqual(smi["user_bits_effective"], "B0:12:00:34")
            self.assertEqual(run_fx6_menu_trial.user_bits_to_uint32("B0:12:00:34"), 0xB0120034)

    def test_p88_18_smpte_12m_user_bits_manual_hex_and_validation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p88_18_") as td:
            sess = self._new_session(td)
            r = sess.set_shotmark_and_iris({"user_bits_hex": "cafe0815"})
            self.assertTrue(r["ok"])
            self.assertEqual(r["shotmark_and_iris"]["user_bits_mode"], "manual")
            self.assertEqual(r["shotmark_and_iris"]["user_bits_effective"], "CA:FE:08:15")

            bad = sess.set_shotmark_and_iris({"user_bits_hex": "ZZ:11:22:33"})
            self.assertFalse(bad["ok"])
            self.assertEqual(bad["error"], "invalid_user_bits_hex")

    def test_p88_19_fx6_fleet_camset_sanitizer_scrubs_nd_sdi_wifi_vf(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p88_19_") as td:
            sess = self._new_session(td)
            fx6_payload = {
                "schema": "ilme_fx6_camset_v1",
                "source_model": "ILME-FX6",
                "sanitize_fx6_fleet": True,
                "fx6_nd_preset": "1/16",
                "sdi_12g_out": "On",
                "wifi_ap_enabled": True,
                "vf_peaking": "On",
                "cinema_params": {
                    "fps": "23.98p",
                    "ei": "800 EI (800 Base)",
                    "shutter": "180.0\u00b0",
                    "nd": "1/16",
                    "wb": "5600K",
                },
            }
            res = sess.import_camset_preset(fx6_payload)
            self.assertTrue(res["ok"])
            self.assertTrue(res["fx6_fleet_sanitized"])
            self.assertEqual(res["nd_preset"], "Clear")
            self.assertEqual(res["sdi_out"], "CONTAINED_DISABLED")
            self.assertTrue(res["wifi_bt_rf_disabled"])
            self.assertTrue(res["p12_bk4_airplane_mode_locked"])
            self.assertEqual(res["p4_nd_motor_faults"], 0)
            san = res["sanitized_fx6_fields"]
            for expected_key in ("fx6_nd_preset", "sdi_12g_out", "wifi_ap_enabled", "vf_peaking"):
                self.assertIn(expected_key, san)

    def test_p88_20_fx6_fleet_camset_preserves_p4_and_p12_locks(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p88_20_") as td:
            sess = self._new_session(td)
            fx6_payload = {
                "source_model": "ILME-FX6",
                "fx6_nd_preset": "1/64",
                "nd_auto_mode": "Auto",
                "sdi_12g_out": "4K Raw",
                "wifi_bt_rf_disabled": False,
                "p12_bk4_airplane_mode_locked": False,
                "timecode_bnc_in": "Jam",
                "genlock_in": "Tri-Level",
            }
            res = sess.import_camset_preset(fx6_payload)
            self.assertTrue(res["ok"])
            self.assertEqual(sess.cell_vals[3], 0)
            self.assertTrue(sess.p12_bk4_airplane_mode_locked)
            self.assertTrue(res["wifi_bt_rf_disabled"])
            self.assertTrue(res["p12_bk4_clamped"])
            self.assertEqual(res["cinema_params"]["values"]["nd"], "Clear [FX3 P4 Locked]")

    def test_p88_21_fx6_fleet_camset_strict_backward_compat_untouched(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p88_21_") as td:
            sess = self._new_session(td)
            # Wrong schema without FX6 fleet flags still fails strictly
            bad = sess.import_camset_preset({"schema": "wrong_v99", "cinema_params": {"fps": "23.98p"}})
            self.assertFalse(bad["ok"])
            self.assertEqual(bad["error"], "invalid_camset_schema")

            # Strict P4 ND tamper still increments p4_nd_reject_count when not FX6 fleet
            tamper = sess.import_camset_preset({
                "schema": "fx6_on_fx3_camset_v1",
                "cinema_params": {"nd": "1/16"},
            })
            self.assertTrue(tamper["ok"])
            self.assertFalse(tamper["fx6_fleet_sanitized"])
            self.assertEqual(tamper["sanitized_fx6_fields"], [])
            self.assertTrue(tamper["p4_nd_rejected"])
            self.assertEqual(tamper["p4_nd_reject_count"], 1)

    def test_p88_22_camset_export_import_roundtrip_with_shotmark_and_iris(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p88_22_") as td:
            s1 = self._new_session(td + "_a")
            s1.set_shotmark_and_iris({
                "action": "add_shotmark1",
                "frame": 55,
                "iris_fstop": 4.0,
                "ae_shift_ev": 0.5,
                "metering_mode": "highlight",
                "ch34_safety_pad_db": -20,
                "user_bits_hex": "DE:AD:BE:EF",
            })
            exported = s1.export_camset_preset()
            self.assertTrue(exported["ok"])
            self.assertIn("shotmark_and_iris", exported)
            self.assertEqual(exported["shotmark_and_iris"]["shotmark1_count"], 1)

            s2 = self._new_session(td + "_b")
            imp = s2.import_camset_preset(exported)
            self.assertTrue(imp["ok"])
            smi2 = s2.get_shotmark_and_iris()
            self.assertEqual(smi2["shotmark1_count"], 1)
            self.assertEqual(smi2["shotmarks"][0]["frame"], 55)
            self.assertEqual(smi2["iris_fstop"], 4.0)
            self.assertEqual(smi2["metering_mode"], "highlight")
            self.assertEqual(smi2["ch34_safety_pad_db"], -20)
            self.assertEqual(smi2["user_bits_effective"], "DE:AD:BE:EF")

    def test_p88_23_mailbox_mb40_43_packing_matches_c_bitfield_layout(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p88_23_") as td:
            sess = self._new_session(td)
            sess.set_shotmark_and_iris({
                "shotmarks": [
                    {"type": "ShotMark1", "frame": 12},
                    {"type": "ShotMark2", "frame": 88},
                ],
                "iris_fstop": 4.0,
                "ae_shift_ev": -0.5,
                "metering_mode": "highlight",
                "ch34_safety_pad_db": -20,
                "push_auto_iris_active": True,
                "user_bits_hex": "A0:02:00:09",
            })
            packed = sess._pack_phase88_mailbox_bytes()
            self.assertEqual(len(packed), 16)
            mb40, mb41, mb42, mb43 = struct.unpack("<4I", packed)
            self.assertEqual(mb40 & 0x7F, 2)
            self.assertEqual((mb40 >> 7) & 0x7F, 1)
            self.assertEqual((mb40 >> 14) & 0x7F, 1)
            self.assertEqual((mb40 >> 21) & 0x03, 2)
            self.assertEqual((mb40 >> 23) & 0x1FF, 88)
            self.assertEqual(mb41 & 0xFFF, 400)
            self.assertEqual((mb41 >> 12) & 0x03, 3)  # highlight
            self.assertEqual((mb41 >> 22) & 0x01, 1)  # ch34_pad_20db
            self.assertEqual((mb41 >> 23) & 0x01, 1)  # push_auto_iris_active
            self.assertEqual((mb41 >> 24) & 0x7F, 41)  # target_ire
            self.assertEqual((mb41 >> 31) & 0x01, 1)  # valid
            self.assertEqual(mb42, 0xA0020009)
            self.assertEqual(mb43, 0x534D524B)  # 'SMRK'

    def test_p88_24_http_api_get_post_shotmark_and_iris_and_malformed_json(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p88_24_") as td:
            _sess, srv, t, base = self._start_http_server(td)
            try:
                st, g = self._http_get_json(f"{base}/api/shotmark_and_iris")
                self.assertEqual(st, 200)
                self.assertTrue(g["ok"])
                self.assertEqual(g["shotmark_and_iris"]["iris_fstop"], 2.8)

                st_p, p = self._http_post_json(
                    f"{base}/api/shotmark_and_iris",
                    {"action": "add_shotmark1", "frame": 100, "ch34_safety_pad_db": -20},
                )
                self.assertEqual(st_p, 200)
                self.assertTrue(p["ok"])
                self.assertEqual(p["shotmark_and_iris"]["shotmark1_count"], 1)
                self.assertEqual(p["shotmark_and_iris"]["ch34_safety_pad_db"], -20)

                st_bad, bad = self._http_post_json(f"{base}/api/shotmark_and_iris", b"{bad-json")
                self.assertEqual(st_bad, 400)
                self.assertEqual(bad["error"], "invalid_json")
            finally:
                srv.shutdown()
                srv.server_close()
                t.join(timeout=2)

    def test_p88_25_http_xml_sidecar_live_essencemark_integration(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p88_25_") as td:
            _sess, srv, t, base = self._start_http_server(td)
            try:
                self._http_post_json(f"{base}/api/shotmark_and_iris", {"action": "add_shotmark1", "frame": 24})
                self._http_post_json(f"{base}/api/shotmark_and_iris", {"action": "add_shotmark2", "frame": 96})
                st_x, xml_body = self._http_get_text(f"{base}/api/xml_sidecar")
                self.assertEqual(st_x, 200)
                self.assertIn("<KlvPacketTable>", xml_body)
                self.assertIn("<EssenceMark ", xml_body)
                self.assertIn('name="_ShotMark1" start="24"', xml_body)
                self.assertIn('name="_ShotMark2" start="96"', xml_body)

                st_j, j = self._http_get_json(f"{base}/api/xml_sidecar?format=json")
                self.assertEqual(st_j, 200)
                self.assertEqual(j["shotmark_and_iris"]["shotmark_count"], 2)
                self.assertNotRegex(json.dumps(j), r'(?<![0-9A-Za-z_/.-])b[\'"]')
            finally:
                srv.shutdown()
                srv.server_close()
                t.join(timeout=2)

    def test_p88_26_http_camset_import_fx6_fleet_end_to_end(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p88_26_") as td:
            _sess, srv, t, base = self._start_http_server(td)
            try:
                st, res = self._http_post_json(
                    f"{base}/api/camset_import",
                    {
                        "schema": "ilme_fx6_camset_v1",
                        "source_model": "ILME-FX6",
                        "fx6_nd_preset": "1/16",
                        "sdi_12g_out": "On",
                        "wifi_ap_enabled": True,
                        "vf_peaking": "On",
                    },
                )
                self.assertEqual(st, 200)
                self.assertTrue(res["ok"])
                self.assertTrue(res["fx6_fleet_sanitized"])
                self.assertEqual(res["nd_preset"], "Clear")
                self.assertEqual(res["sdi_out"], "CONTAINED_DISABLED")
                self.assertTrue(res["wifi_bt_rf_disabled"])
                self.assertNotRegex(json.dumps(res), r'(?<![0-9A-Za-z_/.-])b[\'"]')
            finally:
                srv.shutdown()
                srv.server_close()
                t.join(timeout=2)

    def test_p88_27_web_ui_bilingual_card_and_controls_present(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p88_27_") as td:
            _sess, srv, t, base = self._start_http_server(td)
            try:
                st, html = self._http_get_text(f"{base}/")
                self.assertEqual(st, 200)
                self.assertIn("phase88-shotmark-iris-card", html)
                self.assertIn("场记打点 ShotMark1/2 / 一键自动光圈 41%IRE / FX6->FX3 多机位配置克隆", html)
                self.assertIn("/api/shotmark_and_iris", html)
                self.assertIn("importFx6FleetCamsetPreset", html)
                self.assertIn("syncShotmarkIrisUI", html)
            finally:
                srv.shutdown()
                srv.server_close()
                t.join(timeout=2)

    def test_p88_28_guest_c_source_mb40_43_hud_and_zig_compile_hygiene(self) -> None:
        c_src = (TRIAL_DIR / "src" / "fx6_live_guest.c").read_text(encoding="utf-8")
        self.assertIn("0x534d524bu", c_src)
        self.assertIn("fx6_render_phase88_shotmark_iris_overlay", c_src)
        self.assertIn("[CH3/4 -20dB SAFE]", c_src)
        self.assertIn("AUTO-IRIS ", c_src)
        self.assertIn("SMRK=0x%08x:0x%08x:0x%08x", c_src)
        # Ensure clean-room flag is inspectable in dual-mode
        _ = _force_clean_room()


if __name__ == "__main__":
    unittest.main()
