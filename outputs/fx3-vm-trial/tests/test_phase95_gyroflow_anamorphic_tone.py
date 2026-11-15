#!/usr/bin/env python3
"""Phase 95 Unit & Integration Tests: Anamorphic (1.0/1.3/1.33/1.5/1.8/2.0x) IBIS
Asymmetric Yaw-Gain / 0x0400 Center-Lock Arbitrator, Gyroflow 2000Hz RTMD Readiness
& IMX510 Skew Telemetry, 1kHz -20dBFS Reference Tone / SMPTE Bars & 4-Ch -3.0dBFS Limiter,
Touch-AF Inverse De-Squeeze Sync, SMPTE RDD 18 / NonRealTimeMeta <Lenses> XML, & GPE0 mb[44..47] HUD.

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


class TestPhase95GyroflowAnamorphicTone(unittest.TestCase):
    def _new_session(self, td: str) -> run_fx6_menu_trial.FX6LiveGpe0Session:
        return run_fx6_menu_trial.FX6LiveGpe0Session(Path(td) / "sess", port=18779)

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

    def test_p95_01_specs_and_defaults(self) -> None:
        specs = run_fx6_menu_trial.GYROFLOW_ANAMORPHIC_SPECS
        self.assertEqual(specs["squeeze_factors"], [1.0, 1.3, 1.33, 1.5, 1.8, 2.0])
        self.assertEqual(
            specs["ibis_modes"],
            ["Off", "Standard", "Active", "Anamorphic_Asymmetric", "Center_Lock_Gyroflow"],
        )
        self.assertEqual(specs["anamorphic_fallback_modes"], ["Anamorphic_Asymmetric", "Center_Lock_Gyroflow"])
        self.assertEqual(specs["imu_rate_hz"], 2000)
        self.assertEqual(specs["rolling_shutter_skew_ff_4k_ms"], 8.7)
        self.assertEqual(specs["rolling_shutter_skew_4k120_ms"], 4.3)
        self.assertEqual(specs["ref_tone_freq_hz"], 1000)
        self.assertEqual(specs["ref_tone_level_dbfs"], -20.0)
        self.assertEqual(specs["limiter_ceiling_dbfs"], -3.0)

        with tempfile.TemporaryDirectory(prefix="fx6_p95_01_") as td:
            sess = self._new_session(td)
            ga = sess.get_gyroflow_anamorphic()
            self.assertEqual(ga["squeeze_factor"], 1.0)
            self.assertEqual(ga["ibis_mode"], "Standard")
            self.assertEqual(ga["effective_ibis_mode"], "Standard")
            self.assertFalse(ga["ibis_arbitrated"])
            self.assertFalse(ga["center_lock_0x0400"])
            self.assertEqual(ga["horizontal_yaw_gain"], 1.0)
            self.assertEqual(ga["vertical_pitch_gain"], 1.0)
            self.assertEqual(ga["imu_samples_per_frame"], 83.4)
            self.assertEqual(ga["rolling_shutter_skew_ms"], 8.7)
            self.assertEqual(ga["rtmd_status"], "RTMD_READY")
            self.assertTrue(ga["gyroflow_ready"])
            self.assertFalse(ga["ref_tone_enabled"])
            self.assertFalse(ga["color_bars_enabled"])
            self.assertFalse(ga["limiter_enabled"])
            self.assertEqual(sess.get_status()["gyroflow_anamorphic"], ga)

    def test_p95_02_all_supported_squeeze_factors_accepted(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p95_02_") as td:
            sess = self._new_session(td)
            for val_in, expected in (
                (1.0, 1.0),
                ("1.3x", 1.3),
                (1.33, 1.33),
                ("1.50x", 1.5),
                (1.8, 1.8),
                ("2.0", 2.0),
            ):
                r = sess.set_gyroflow_anamorphic({"squeeze_factor": val_in})
                self.assertTrue(r["ok"], msg=f"Failed squeeze_factor={val_in!r}: {r}")
                self.assertEqual(r["gyroflow_anamorphic"]["squeeze_factor"], expected)

    def test_p95_03_reject_invalid_squeeze_factor_bool_nan_and_unsupported(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p95_03_") as td:
            sess = self._new_session(td)
            for bad in (True, False, 1.25, 1.6, 2.5, 0.0, -1.5, float("nan"), float("inf"), "abc"):
                r = sess.set_gyroflow_anamorphic({"squeeze_factor": bad})
                self.assertFalse(r["ok"], msg=f"Should reject squeeze_factor={bad!r}")
                self.assertEqual(r["error"], "invalid_squeeze_factor")

    def test_p95_04_reject_invalid_ibis_fallback_and_booleans(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p95_04_") as td:
            sess = self._new_session(td)
            r1 = sess.set_gyroflow_anamorphic({"ibis_mode": "HyperSmooth"})
            self.assertFalse(r1["ok"])
            self.assertEqual(r1["error"], "invalid_ibis_mode")

            r2 = sess.set_gyroflow_anamorphic({"anamorphic_fallback_mode": "Active"})
            self.assertFalse(r2["ok"])
            self.assertEqual(r2["error"], "invalid_anamorphic_fallback_mode")

            r3 = sess.set_gyroflow_anamorphic({"ref_tone_enabled": "maybe"})
            self.assertFalse(r3["ok"])
            self.assertEqual(r3["error"], "invalid_ref_tone_enabled")

            r4 = sess.set_gyroflow_anamorphic({"limiter_enabled": 2})
            self.assertFalse(r4["ok"])
            self.assertEqual(r4["error"], "invalid_limiter_enabled")

    def test_p95_05_spherical_1x_allows_active_ibis_full_gain(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p95_05_") as td:
            sess = self._new_session(td)
            r = sess.set_gyroflow_anamorphic({"squeeze_factor": 1.0, "ibis_mode": "Active"})
            self.assertTrue(r["ok"])
            ga = r["gyroflow_anamorphic"]
            self.assertEqual(ga["ibis_mode"], "Active")
            self.assertEqual(ga["effective_ibis_mode"], "Active")
            self.assertFalse(ga["ibis_arbitrated"])
            self.assertEqual(ga["horizontal_yaw_gain"], 1.0)
            self.assertEqual(ga["vertical_pitch_gain"], 1.0)
            self.assertFalse(ga["center_lock_0x0400"])

    def test_p95_06_arbitrator_active_plus_2x_routes_to_asymmetric_yaw_half(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p95_06_") as td:
            sess = self._new_session(td)
            r = sess.set_gyroflow_anamorphic({
                "squeeze_factor": 2.0,
                "ibis_mode": "Active",
                "anamorphic_fallback_mode": "Anamorphic_Asymmetric",
            })
            self.assertTrue(r["ok"])
            ga = r["gyroflow_anamorphic"]
            self.assertEqual(ga["ibis_mode"], "Active")
            self.assertEqual(ga["effective_ibis_mode"], "Anamorphic_Asymmetric")
            self.assertTrue(ga["ibis_arbitrated"])
            self.assertTrue(ga["anamorphic_edge_wobble_prevented"])
            self.assertEqual(ga["horizontal_yaw_gain"], 0.5)
            self.assertEqual(ga["vertical_pitch_gain"], 1.0)
            self.assertFalse(ga["center_lock_0x0400"])
            self.assertEqual(ga["rtmd_status"], "RTMD_READY")

    def test_p95_07_arbitrator_asymmetric_yaw_gain_across_all_squeeze_factors(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p95_07_") as td:
            sess = self._new_session(td)
            expected = {
                1.3: 0.7692,
                1.33: 0.7519,
                1.5: 0.6667,
                1.8: 0.5556,
                2.0: 0.5,
            }
            for sq, exp_yaw in expected.items():
                r = sess.set_gyroflow_anamorphic({
                    "squeeze_factor": sq,
                    "ibis_mode": "Anamorphic_Asymmetric",
                })
                self.assertTrue(r["ok"])
                ga = r["gyroflow_anamorphic"]
                self.assertEqual(ga["effective_ibis_mode"], "Anamorphic_Asymmetric")
                self.assertAlmostEqual(ga["horizontal_yaw_gain"], exp_yaw, places=4)
                self.assertEqual(ga["vertical_pitch_gain"], 1.0)
                self.assertTrue(ga["anamorphic_edge_wobble_prevented"])

    def test_p95_08_arbitrator_active_plus_18x_routes_to_center_lock_0x0400(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p95_08_") as td:
            sess = self._new_session(td)
            r = sess.set_gyroflow_anamorphic({
                "squeeze_factor": 1.8,
                "ibis_mode": "Active",
                "anamorphic_fallback_mode": "Center_Lock_Gyroflow",
            })
            self.assertTrue(r["ok"])
            ga = r["gyroflow_anamorphic"]
            self.assertEqual(ga["effective_ibis_mode"], "Center_Lock_Gyroflow")
            self.assertTrue(ga["ibis_arbitrated"])
            self.assertTrue(ga["center_lock_0x0400"])
            self.assertEqual(ga["horizontal_yaw_gain"], 0.0)
            self.assertEqual(ga["vertical_pitch_gain"], 0.0)
            self.assertEqual(ga["rtmd_status"], "RTMD_CENTER_LOCKED")
            self.assertEqual(sess.rtmd_0xe304_ibis_lock, "OFF_CENTER_LOCKED")

    def test_p95_09_set_cinema_param_active_ibis_with_squeeze_arbitrates(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p95_09_") as td:
            sess = self._new_session(td)
            sess.set_gyroflow_anamorphic({"squeeze_factor": 1.5, "ibis_mode": "Standard"})
            r = sess.set_cinema_param("rtmd_0xe304_ibis_lock", preset="ACTIVE_5AXIS")
            self.assertTrue(r["ok"])
            ga = sess.get_gyroflow_anamorphic()
            self.assertEqual(ga["ibis_mode"], "Active")
            self.assertEqual(ga["effective_ibis_mode"], "Anamorphic_Asymmetric")
            self.assertTrue(ga["ibis_arbitrated"])
            self.assertEqual(ga["horizontal_yaw_gain"], 0.6667)

    def test_p95_10_assist_tools_desqueeze_syncs_phase95_squeeze_factor(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p95_10_") as td:
            sess = self._new_session(td)
            r1 = sess.set_assist_tools({"desqueeze": "1.33x"})
            self.assertTrue(r1["ok"])
            self.assertEqual(sess.get_gyroflow_anamorphic()["squeeze_factor"], 1.33)
            r2 = sess.set_assist_tools({"desqueeze": "2.0x"})
            self.assertTrue(r2["ok"])
            self.assertEqual(sess.get_gyroflow_anamorphic()["squeeze_factor"], 2.0)

    def test_p95_11_touch_af_inverse_desqueeze_sync_2x_and_15x(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p95_11_") as td:
            sess = self._new_session(td)
            # 2.0x squeeze: desqueezed width = 1920; clicking center-right 1440 maps to sensor X = 720
            r = sess.set_gyroflow_anamorphic({
                "squeeze_factor": 2.0,
                "desqueezed_touch_x": 1440,
                "coordinate_space": "desqueezed",
                "touch_af_mode": "touch_tracking",
                "touch_y": 270,
            })
            self.assertTrue(r["ok"])
            ga = r["gyroflow_anamorphic"]
            tfc = r["touch_focus_ciz"]
            self.assertEqual(ga["touch_x"], 720)
            self.assertEqual(ga["desqueezed_width"], 1920)
            self.assertEqual(ga["desqueezed_touch_x"], 1440)
            self.assertEqual(ga["touch_af_inverse_desqueeze_scale"], 0.5)
            self.assertTrue(ga["touch_af_desqueeze_synced"])
            self.assertEqual(tfc["touch_x"], 720)
            self.assertEqual(tfc["desqueezed_touch_x"], 1440)
            self.assertEqual(tfc["squeeze_factor"], 2.0)

            # 1.5x squeeze via /api/touch_focus_ciz directly
            sess.set_gyroflow_anamorphic({"squeeze_factor": 1.5})
            r_tfc = sess.set_touch_focus_ciz({
                "touch_af_mode": "touch_focus",
                "desqueezed_touch_x": 900,
                "coordinate_space": "desqueezed",
                "touch_y": 240,
            })
            self.assertTrue(r_tfc["ok"])
            self.assertEqual(r_tfc["touch_focus_ciz"]["touch_x"], 600)
            self.assertEqual(r_tfc["touch_focus_ciz"]["touch_af_inverse_desqueeze_scale"], 0.6667)

    def test_p95_12_touch_af_letterbox_detection_with_18x_and_239_aspect(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p95_12_") as td:
            sess = self._new_session(td)
            sess.set_assist_tools({"aspect_marker": "2.39:1"})
            sess.set_gyroflow_anamorphic({"squeeze_factor": 1.8})
            rect = run_fx6_menu_trial.compute_active_sensor_rect("2.39:1", "1.80x")
            self.assertEqual((rect["x_min"], rect["y_min"], rect["x_max"], rect["y_max"]), (0, 120, 959, 419))
            # Clicking y=10 (top matte bar) preserves previous touch_y=270
            r_lb = sess.set_touch_focus_ciz({"touch_af_mode": "touch_tracking", "touch_x": 500, "touch_y": 10})
            self.assertTrue(r_lb["ok"])
            self.assertTrue(r_lb["touch_focus_ciz"]["letterbox_ignored"])
            self.assertEqual(r_lb["touch_focus_ciz"]["touch_y"], 270)

    def test_p95_13_gyroflow_2000hz_imu_samples_and_imx510_skew_at_24_60_120fps(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p95_13_") as td:
            sess = self._new_session(td)
            # 23.98p -> 2000 / 23.98 = 83.4 samples/frame, 8.7ms skew
            ga24 = sess.get_gyroflow_anamorphic()
            self.assertEqual(ga24["imu_samples_per_frame"], 83.4)
            self.assertEqual(ga24["rolling_shutter_skew_ms"], 8.7)
            self.assertEqual(ga24["rtmd_status"], "RTMD_READY")

            # 59.94p -> 2000 / 59.94 = 33.4 samples/frame, 8.7ms skew
            sess.set_cinema_param("fps", preset="59.94p")
            ga60 = sess.get_gyroflow_anamorphic()
            self.assertEqual(ga60["imu_samples_per_frame"], 33.4)
            self.assertEqual(ga60["rolling_shutter_skew_ms"], 8.7)
            self.assertEqual(ga60["rtmd_status"], "RTMD_READY")

            # 119.88p (S&Q) -> 16.7 samples/frame, 4.3ms skew, RTMD_SUSPENDED_BY_SQ
            sess.set_cinema_param("fps", preset="119.88p (S&Q)")
            ga120 = sess.get_gyroflow_anamorphic()
            self.assertEqual(ga120["imu_samples_per_frame"], 16.7)
            self.assertEqual(ga120["rolling_shutter_skew_ms"], 4.3)
            self.assertTrue(ga120["rtmd_suspended_by_sq"])
            self.assertFalse(ga120["gyroflow_ready"])
            self.assertEqual(ga120["rtmd_status"], "RTMD_SUSPENDED_BY_SQ")

    def test_p95_14_sq_vfr_via_cine_exposure_suspends_rtmd_and_resumes_when_off(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p95_14_") as td:
            sess = self._new_session(td)
            r_sq = sess.set_cine_exposure({"sq_enabled": True, "sq_fps": 120})
            self.assertTrue(r_sq["ok"])
            ga = sess.get_gyroflow_anamorphic()
            self.assertTrue(ga["rtmd_suspended_by_sq"])
            self.assertEqual(ga["rtmd_status"], "RTMD_SUSPENDED_BY_SQ")
            self.assertEqual(ga["imu_samples_per_frame"], 16.7)
            self.assertEqual(ga["rolling_shutter_skew_ms"], 4.3)

            r_off = sess.set_cine_exposure({"sq_enabled": False})
            self.assertTrue(r_off["ok"])
            ga2 = sess.get_gyroflow_anamorphic()
            self.assertFalse(ga2["rtmd_suspended_by_sq"])
            self.assertEqual(ga2["rtmd_status"], "RTMD_READY")
            self.assertEqual(ga2["imu_samples_per_frame"], 83.4)

    def test_p95_15_ref_tone_1khz_minus20dbfs_and_bars_active_in_stby(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p95_15_") as td:
            sess = self._new_session(td)
            r = sess.set_gyroflow_anamorphic({"ref_tone_enabled": True, "color_bars_enabled": True})
            self.assertTrue(r["ok"])
            ga = r["gyroflow_anamorphic"]
            self.assertEqual(ga["rec_state"], "STBY")
            self.assertTrue(ga["ref_tone_enabled"])
            self.assertTrue(ga["ref_tone_effective_active"])
            self.assertFalse(ga["ref_tone_inhibited_by_rec"])
            self.assertEqual(ga["ref_tone_freq_hz"], 1000)
            self.assertEqual(ga["ref_tone_level_dbfs"], -20.0)
            self.assertTrue(ga["color_bars_enabled"])
            self.assertTrue(ga["color_bars_effective_active"])
            self.assertFalse(ga["color_bars_inhibited_by_rec"])

    def test_p95_16_ref_tone_and_bars_auto_inhibited_while_rec_tally_active(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p95_16_") as td:
            sess = self._new_session(td)
            sess.set_gyroflow_anamorphic({"ref_tone_enabled": True, "color_bars_enabled": True})
            r_rec = sess.set_cine_exposure({"rec_state": "REC"})
            self.assertTrue(r_rec["ok"])
            ga_rec = sess.get_gyroflow_anamorphic()
            self.assertEqual(ga_rec["rec_state"], "REC")
            self.assertTrue(ga_rec["ref_tone_enabled"])
            self.assertFalse(ga_rec["ref_tone_effective_active"])
            self.assertTrue(ga_rec["ref_tone_inhibited_by_rec"])
            self.assertFalse(ga_rec["color_bars_effective_active"])
            self.assertTrue(ga_rec["color_bars_inhibited_by_rec"])

            # Stop REC -> returns to STBY and resumes test tone cleanly
            sess.set_cine_exposure({"rec_state": "STBY"})
            ga_stby = sess.get_gyroflow_anamorphic()
            self.assertTrue(ga_stby["ref_tone_effective_active"])
            self.assertFalse(ga_stby["ref_tone_inhibited_by_rec"])
            self.assertTrue(ga_stby["color_bars_effective_active"])

    def test_p95_17_audio_4ch_soft_knee_limiter_clamps_above_minus3_dbfs(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p95_17_") as td:
            sess = self._new_session(td)
            # Push Ch1=+6 dB, Ch2=+2 dB, Ch3=-6 dB, Ch4=-18 dB via cinema_param flat audio keys
            r_aud = sess.set_cinema_param(payload={"ch1_db": 6, "ch2_db": 2, "ch3_db": -6, "ch4_db": -18})
            self.assertTrue(r_aud["ok"])
            r_off = sess.set_gyroflow_anamorphic({"limiter_enabled": False})
            self.assertTrue(r_off["ok"])
            ga_off = r_off["gyroflow_anamorphic"]
            self.assertFalse(ga_off["limiter_engaging"])
            self.assertEqual(ga_off["effective_ch_db"], [6.0, 2.0, -6.0, -18.0])

            r_on = sess.set_gyroflow_anamorphic({"limiter_enabled": True})
            self.assertTrue(r_on["ok"])
            ga_on = r_on["gyroflow_anamorphic"]
            self.assertTrue(ga_on["limiter_enabled"])
            self.assertTrue(ga_on["limiter_engaging"])
            self.assertEqual(ga_on["limiter_ceiling_dbfs"], -3.0)
            self.assertEqual(ga_on["ch_clamped"], [True, True, False, False])
            self.assertEqual(ga_on["ch_clamped_mask"], 0b0011)
            self.assertEqual(ga_on["effective_ch_db"], [-3.0, -3.0, -6.0, -18.0])

    def test_p95_18_xml_sidecar_embeds_lenses_and_acquisition_record_rtmd_tone(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p95_18_") as td:
            sess = self._new_session(td)
            sess.set_gyroflow_anamorphic({
                "squeeze_factor": 1.8,
                "ibis_mode": "Active",
                "anamorphic_fallback_mode": "Center_Lock_Gyroflow",
                "ref_tone_enabled": True,
                "color_bars_enabled": True,
                "limiter_enabled": True,
            })
            sidecar = sess.get_xml_sidecar()
            xml_text = sidecar["xml"]
            root = ET.fromstring(xml_text)
            ns = {"n": run_fx6_menu_trial.NRTM_NAMESPACE_V220}

            lenses = root.findall(".//n:Lenses/n:Lens", ns)
            self.assertEqual(len(lenses), 1)
            self.assertEqual(lenses[0].attrib["anamorphicSqueezeFactor"], "1.80")
            self.assertEqual(lenses[0].attrib["desqueezeDisplay"], "1.80x")
            self.assertEqual(lenses[0].attrib["desqueezedAspectRatio"], "3.20:1")

            groups = {g.attrib.get("name"): g for g in root.findall(".//n:AcquisitionRecord/n:Group", ns)}
            self.assertIn("AnamorphicGyroflowRtmd", groups)
            self.assertIn("AudioReferenceAndLimiter", groups)

            gyro_items = {it.attrib["name"]: it.attrib["value"] for it in groups["AnamorphicGyroflowRtmd"]}
            self.assertEqual(gyro_items["IbisEffectiveMode"], "Center_Lock_Gyroflow")
            self.assertEqual(gyro_items["IbisCenterLock0x0400"], "true")
            self.assertEqual(gyro_items["ImuSampleRateHz"], "2000")
            self.assertEqual(gyro_items["GyroflowRtmdStatus"], "RTMD_CENTER_LOCKED")
            self.assertEqual(gyro_items["Imx510ReadoutSkewMs"], "8.7")
            self.assertEqual(gyro_items["IbisArbitrated"], "true")

            aud_items = {it.attrib["name"]: it.attrib["value"] for it in groups["AudioReferenceAndLimiter"]}
            self.assertEqual(aud_items["ReferenceToneFreqHz"], "1000")
            self.assertEqual(aud_items["ReferenceToneLevelDbfs"], "-20.0")
            self.assertEqual(aud_items["ReferenceToneEffectiveActive"], "true")
            self.assertEqual(aud_items["SmpteColorBarsEffective"], "true")
            self.assertEqual(aud_items["PeakLimiterEnabled"], "true")
            self.assertEqual(aud_items["PeakLimiterCeilingDbfs"], "-3.0")

    def test_p95_19_camset_export_import_roundtrip_preserves_phase95_and_p4(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p95_19_") as td:
            s1 = self._new_session(td + "_a")
            s1.set_gyroflow_anamorphic({
                "squeeze_factor": 2.0,
                "ibis_mode": "Active",
                "anamorphic_fallback_mode": "Anamorphic_Asymmetric",
                "ref_tone_enabled": True,
                "color_bars_enabled": True,
                "limiter_enabled": True,
            })
            exported = s1.export_camset_preset()
            self.assertTrue(exported["ok"])
            self.assertIn("gyroflow_anamorphic", exported)
            self.assertEqual(exported["gyroflow_anamorphic"]["squeeze_factor"], 2.0)

            s2 = self._new_session(td + "_b")
            imp = s2.import_camset_preset(exported)
            self.assertTrue(imp["ok"])
            ga2 = s2.get_gyroflow_anamorphic()
            self.assertEqual(ga2["squeeze_factor"], 2.0)
            self.assertEqual(ga2["effective_ibis_mode"], "Anamorphic_Asymmetric")
            self.assertEqual(ga2["horizontal_yaw_gain"], 0.5)
            self.assertTrue(ga2["ref_tone_enabled"])
            self.assertTrue(ga2["color_bars_enabled"])
            self.assertTrue(ga2["limiter_enabled"])
            self.assertEqual(s2.get_cinema_params()["values"]["nd"], "Clear [FX3 P4 Locked]")

    def test_p95_20_camset_backward_compat_without_gyroflow_anamorphic_key(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p95_20_") as td:
            sess = self._new_session(td)
            legacy_camset = {
                "schema": "fx6_on_fx3_camset_v1",
                "cinema_params": {"fps": "23.98p", "ei": "800 EI (800 Base)"},
            }
            imp = sess.import_camset_preset(legacy_camset)
            self.assertTrue(imp["ok"])
            self.assertEqual(sess.get_gyroflow_anamorphic()["squeeze_factor"], 1.0)
            self.assertEqual(sess.get_gyroflow_anamorphic()["effective_ibis_mode"], "Standard")

    def test_p95_21_camset_rejects_malformed_gyroflow_anamorphic_section(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p95_21_") as td:
            sess = self._new_session(td)
            bad_camset = {
                "schema": "fx6_on_fx3_camset_v1",
                "gyroflow_anamorphic": {"squeeze_factor": 9.9},
            }
            imp = sess.import_camset_preset(bad_camset)
            self.assertFalse(imp["ok"])
            self.assertEqual(imp["error"], "invalid_squeeze_factor")

    def test_p95_22_mailbox_mb44_47_default_words_match_c_boot_defaults(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p95_22_") as td:
            sess = self._new_session(td)
            packed = sess._pack_phase95_mailbox_bytes()
            self.assertEqual(len(packed), 16)
            mb44, mb45, mb46, mb47 = struct.unpack("<4I", packed)
            self.assertEqual(mb44, 0x8F032048)
            self.assertEqual(mb45, 0x64857342)
            self.assertEqual(mb46, 0x80507800)
            self.assertEqual(mb47, 0x4759524F)  # 'GYRO'

    def test_p95_23_mailbox_mb44_47_bitfields_after_2x_asym_tone_bars_limiter(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p95_23_") as td:
            sess = self._new_session(td)
            r_aud = sess.set_cinema_param(payload={"ch1_db": 4, "ch2_db": -12, "ch3_db": -12, "ch4_db": -12})
            self.assertTrue(r_aud["ok"])
            sess.set_gyroflow_anamorphic({
                "squeeze_factor": 2.0,
                "ibis_mode": "Active",
                "anamorphic_fallback_mode": "Anamorphic_Asymmetric",
                "desqueezed_touch_x": 1200,
                "coordinate_space": "desqueezed",
                "touch_af_mode": "touch_tracking",
                "ref_tone_enabled": True,
                "color_bars_enabled": True,
                "limiter_enabled": True,
            })
            packed = sess._pack_phase95_mailbox_bytes()
            mb44, mb45, mb46, mb47 = struct.unpack("<4I", packed)
            self.assertEqual(mb44 & 0x7, 5)               # sq_idx=5 (2.00x)
            self.assertEqual((mb44 >> 3) & 0x7, 3)        # eff_ibis_idx=3 (Anamorphic_Asymmetric)
            self.assertEqual((mb44 >> 6) & 0x7, 2)        # req_ibis_idx=2 (Active)
            self.assertEqual((mb44 >> 9) & 0x1, 1)        # ibis_arbitrated
            self.assertEqual((mb44 >> 10) & 0x1, 0)       # center_lock=0
            self.assertEqual((mb44 >> 11) & 0xFF, 50)     # yaw_gain=50%
            self.assertEqual((mb44 >> 19) & 0x3FF, 600)   # touch_x=1200/2=600
            self.assertEqual((mb44 >> 29) & 0x1, 1)       # touch_af_desqueeze_synced
            self.assertEqual((mb44 >> 30) & 0x1, 1)       # wobble_prevented
            self.assertEqual((mb44 >> 31) & 0x1, 1)       # phase95_valid

            self.assertEqual(mb45 & 0xFFF, 834)           # 83.4 samples/frame
            self.assertEqual((mb45 >> 12) & 0xFF, 87)     # 8.7ms skew
            self.assertEqual((mb45 >> 20) & 0x3, 0)       # RTMD_READY
            self.assertEqual((mb45 >> 22) & 0x1, 0)       # susp_sq=0
            self.assertEqual((mb45 >> 23) & 0x1, 1)       # gyroflow_ready=1
            self.assertEqual((mb45 >> 25) & 0x7F, 100)    # 2.0 * 50

            self.assertEqual(mb46 & 0x1, 1)               # tone_req
            self.assertEqual((mb46 >> 1) & 0x1, 1)        # tone_eff
            self.assertEqual((mb46 >> 2) & 0x1, 0)        # tone_inhib
            self.assertEqual((mb46 >> 3) & 0x1, 1)        # bars_eff
            self.assertEqual((mb46 >> 4) & 0x1, 1)        # lim_en
            self.assertEqual((mb46 >> 5) & 0x1, 1)        # lim_eng (ch1=+4 > -3)
            self.assertEqual((mb46 >> 6) & 0xF, 0b0001)   # ch1 clamped
            self.assertEqual((mb46 >> 31) & 0x1, 1)       # phase95_tone_valid
            self.assertEqual(mb47, 0x4759524F)            # 'GYRO'

    def test_p95_24_reset_action_restores_defaults(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p95_24_") as td:
            sess = self._new_session(td)
            sess.set_gyroflow_anamorphic({
                "squeeze_factor": 2.0,
                "ibis_mode": "Center_Lock_Gyroflow",
                "ref_tone_enabled": True,
                "color_bars_enabled": True,
                "limiter_enabled": True,
            })
            r = sess.set_gyroflow_anamorphic({"reset": True})
            self.assertTrue(r["ok"])
            ga = r["gyroflow_anamorphic"]
            self.assertEqual(ga["squeeze_factor"], 1.0)
            self.assertEqual(ga["effective_ibis_mode"], "Standard")
            self.assertFalse(ga["ref_tone_enabled"])
            self.assertFalse(ga["color_bars_enabled"])
            self.assertFalse(ga["limiter_enabled"])

    def test_p95_25_http_get_post_gyroflow_anamorphic_and_malformed_json(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p95_25_") as td:
            _sess, srv, t, base = self._start_http_server(td)
            try:
                st, g = self._http_get_json(f"{base}/api/gyroflow_anamorphic")
                self.assertEqual(st, 200)
                self.assertTrue(g["ok"])
                self.assertEqual(g["gyroflow_anamorphic"]["squeeze_factor"], 1.0)

                st_p, p = self._http_post_json(
                    f"{base}/api/gyroflow_anamorphic",
                    {"squeeze_factor": 1.8, "ibis_mode": "Active", "anamorphic_fallback_mode": "Center_Lock_Gyroflow"},
                )
                self.assertEqual(st_p, 200)
                self.assertTrue(p["ok"])
                self.assertTrue(p["gyroflow_anamorphic"]["center_lock_0x0400"])
                self.assertEqual(p["gyroflow_anamorphic"]["rtmd_status"], "RTMD_CENTER_LOCKED")

                st_bad, bad = self._http_post_json(f"{base}/api/gyroflow_anamorphic", b"{broken-json")
                self.assertEqual(st_bad, 400)
                self.assertEqual(bad["error"], "invalid_json")

                st_inv, inv = self._http_post_json(f"{base}/api/gyroflow_anamorphic", {"squeeze_factor": 3.0})
                self.assertEqual(st_inv, 400)
                self.assertEqual(inv["error"], "invalid_squeeze_factor")
            finally:
                srv.shutdown()
                srv.server_close()
                t.join(timeout=2)

    def test_p95_26_http_xml_sidecar_live_lenses_integration(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p95_26_") as td:
            _sess, srv, t, base = self._start_http_server(td)
            try:
                self._http_post_json(
                    f"{base}/api/gyroflow_anamorphic",
                    {"squeeze_factor": 2.0, "ibis_mode": "Active", "ref_tone_enabled": True, "limiter_enabled": True},
                )
                st_x, xml_body = self._http_get_text(f"{base}/api/xml_sidecar")
                self.assertEqual(st_x, 200)
                self.assertIn("<Lenses>", xml_body)
                self.assertIn('anamorphicSqueezeFactor="2.00"', xml_body)
                self.assertIn('<Item name="IbisEffectiveMode" value="Anamorphic_Asymmetric" />', xml_body)
                self.assertIn('name="AnamorphicGyroflowRtmd"', xml_body)
                self.assertIn('name="AudioReferenceAndLimiter"', xml_body)

                st_j, j = self._http_get_json(f"{base}/api/xml_sidecar?format=json")
                self.assertEqual(st_j, 200)
                self.assertEqual(j["gyroflow_anamorphic"]["squeeze_factor"], 2.0)
                self.assertNotRegex(json.dumps(j), r'(?<![0-9A-Za-z_/.-])b[\'"]')
            finally:
                srv.shutdown()
                srv.server_close()
                t.join(timeout=2)

    def test_p95_27_http_web_ui_4_language_controls_and_ids_present(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p95_27_") as td:
            _sess, srv, t, base = self._start_http_server(td)
            try:
                st, html = self._http_get_text(f"{base}/")
                self.assertEqual(st, 200)
                self.assertIn("phase95-gyroflow-anamorphic-card", html)
                self.assertIn("/api/gyroflow_anamorphic", html)
                self.assertIn("syncGyroflowAnamorphicUI", html)
                self.assertIn("P95_I18N", html)
                # Verify EN / ZH-CN / ZH-TW / JA all exist
                self.assertIn("Anamorphic & IBIS Arbitrator", html)
                self.assertIn("变形反挤压 & IBIS 仲裁器", html)
                self.assertIn("變形反擠壓 & IBIS 仲裁器", html)
                self.assertIn("アナモルフィック & IBIS 調停", html)
            finally:
                srv.shutdown()
                srv.server_close()
                t.join(timeout=2)

    def test_p95_28_assist_tools_specs_preserved_for_phase56_compatibility(self) -> None:
        self.assertEqual(
            set(run_fx6_menu_trial.ASSIST_TOOLS_SPECS.keys()),
            {"aspect_marker", "zebra_mode", "peaking_mode", "desqueeze"},
        )
        self.assertEqual(
            tuple(run_fx6_menu_trial.ASSIST_TOOLS_SPECS["desqueeze"]["choices"]),
            ("1.0x", "1.33x", "2.0x"),
        )

    def test_p95_29_guest_c_source_mb44_47_hud_and_heap_free_hygiene(self) -> None:
        c_path = TRIAL_DIR / "src" / "fx6_live_guest.c"
        c_src = c_path.read_text(encoding="utf-8")
        self.assertIn("0x4759524fu", c_src)
        self.assertIn("g_live_p95_anamorphic_ibis", c_src)
        self.assertIn("g_live_p95_gyro_rtmd", c_src)
        self.assertIn("g_live_p95_tone_limiter", c_src)
        self.assertIn("fx6_render_phase95_gyroflow_anamorphic_tone_overlay", c_src)
        self.assertIn("[1kHz -20dBFS TONE", c_src)
        self.assertIn("[1kHz INHIBITED:REC", c_src)
        self.assertIn("SUSP_BY_SQ]", c_src)
        self.assertIn("RTMD_READY]", c_src)
        self.assertIn("for (int i = 0; i < 48; i++) mb[i] = 0;", c_src)
        # Ensure zero malloc/printf inside Phase 95 overlay function
        start_idx = c_src.index("fx6_render_phase95_gyroflow_anamorphic_tone_overlay")
        end_idx = c_src.index("/* ---------------- Frame Cache", start_idx)
        overlay_body = c_src[start_idx:end_idx]
        self.assertNotIn("malloc(", overlay_body)
        self.assertNotIn("calloc(", overlay_body)
        self.assertNotIn("realloc(", overlay_body)
        self.assertNotIn("printf(", overlay_body)
        _ = _force_clean_room()

    def test_p95_30_port_isolation_no_hardcoded_8768_in_phase95_code(self) -> None:
        # Clean check that our Phase 95 test module and Phase 95 API paths never reference 8768
        c_src = (TRIAL_DIR / "src" / "fx6_live_guest.c").read_text(encoding="utf-8")
        self.assertNotIn("8768", c_src)
        # Check Phase 95 python slice doesn't mention 8768
        py_src = (TRIAL_DIR / "run_fx6_menu_trial.py").read_text(encoding="utf-8")
        p95_start = py_src.index("ANAMORPHIC_SQUEEZE_FACTORS")
        p95_end = py_src.index("CINEMA_PARAM_SPECS", p95_start)
        self.assertNotIn("8768", py_src[p95_start:p95_end])


if __name__ == "__main__":
    unittest.main()
