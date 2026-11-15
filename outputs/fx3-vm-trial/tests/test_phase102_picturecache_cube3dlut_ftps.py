#!/usr/bin/env python3
"""Phase 102 Unit & Integration Tests: Picture Cache (Pre-Rec Circular DDR
Ring-Buffer <= 384 MiB on 2048 MiB DRAM), Interval Recording (Electronic Shutter
Protection, Mechanical Curtain == 0), Live User .cube (17^3/33^3/65^3 -> 33^3
Tetrahedral) 3D-LUT Sanitizer & Volatile RAM Loader, Wired USB-LAN FTPS
Background Queue (P12 RF-Off Enforced & eMMC p1..p15 Traversal Blocked),
SMPTE RDD 18 / NonRealTimeMeta XML Sidecar, CAMSET Roundtrip, 4-Language UI,
and GPE0 mb[48..51] ('ICLF') HUD.

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

import run_fx6_menu_trial  # noqa: E402


def _force_clean_room() -> bool:
    return os.environ.get("FX3_FX6_FORCE_CLEAN_ROOM", "").strip().lower() in ("1", "true", "yes")


def _make_sample_cube(size: int = 17, title: str = "Phase102_TealGold", domain_min=(0.0, 0.0, 0.0), domain_max=(1.0, 1.0, 1.0)) -> str:
    lines = [
        f'TITLE "{title}"',
        f"LUT_3D_SIZE {size}",
        f"DOMAIN_MIN {domain_min[0]:.6f} {domain_min[1]:.6f} {domain_min[2]:.6f}",
        f"DOMAIN_MAX {domain_max[0]:.6f} {domain_max[1]:.6f} {domain_max[2]:.6f}",
    ]
    denom = max(1, size - 1)
    for b_i in range(size):
        b = b_i / denom
        for g_i in range(size):
            g = g_i / denom
            for r_i in range(size):
                r = r_i / denom
                # Mild warm-highlight / cool-shadow cinema curve with contrast push
                ro = min(1.0, max(0.0, (r ** 0.92) * 1.04))
                go = min(1.0, max(0.0, (g ** 0.98) * 1.00))
                bo = min(1.0, max(0.0, (b ** 1.06) * 0.94))
                lines.append(f"{ro:.6f} {go:.6f} {bo:.6f}")
    return "\n".join(lines) + "\n"


class TestPhase102PictureCacheCube3DLutFtps(unittest.TestCase):
    def _new_session(self, td: str) -> run_fx6_menu_trial.FX6LiveGpe0Session:
        return run_fx6_menu_trial.FX6LiveGpe0Session(Path(td) / "sess", port=18780)

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

    def test_p102_01_specs_and_defaults(self) -> None:
        specs = run_fx6_menu_trial.INTERVAL_CACHE_LUT_FTP_SPECS
        self.assertEqual(specs["fx3_total_dram_mib"], 2048.0)
        self.assertEqual(specs["ddr_budget_mib"], 384.0)
        self.assertEqual(specs["cache_seconds_choices"], [0, 2, 4, 8, 16])
        self.assertEqual(specs["interval_sec_range"], [1, 60])
        self.assertEqual(specs["target_shots_range"], [1, 9999])
        self.assertEqual(specs["ae_tracking_modes"], ["High", "Mid", "Low", "Lock"])
        self.assertEqual(specs["cube_supported_sizes"], [17, 33, 65])
        self.assertEqual(specs["cube_target_size"], 33)
        self.assertEqual(specs["cube_resampling_method"], "tetrahedral")
        self.assertEqual(specs["ftps_modes"], ["Off", "Proxy_Only", "Original_And_Proxy"])

        with tempfile.TemporaryDirectory(prefix="fx6_p102_01_") as td:
            sess = self._new_session(td)
            p102 = sess.get_interval_cache_lut_ftp()
            self.assertEqual(p102["cache_seconds"], 0)
            self.assertEqual(p102["effective_cache_seconds"], 0)
            self.assertEqual(p102["allocated_ddr_mib"], 0.0)
            self.assertEqual(p102["ddr_budget_mib"], 384.0)
            self.assertEqual(p102["fx3_total_dram_mib"], 2048.0)
            self.assertFalse(p102["interval_rec_enabled"])
            self.assertEqual(p102["interval_sec"], 5)
            self.assertEqual(p102["target_shots"], 120)
            self.assertEqual(p102["shots_taken"], 0)
            self.assertEqual(p102["ae_tracking"], "Mid")
            self.assertEqual(p102["shutter_type"], "ELECTRONIC")
            self.assertTrue(p102["electronic_shutter_enforced"])
            self.assertEqual(p102["mechanical_curtain_actuations"], 0)
            self.assertEqual(p102["ftps_mode"], "Off")
            self.assertTrue(p102["p12_rf_off_enforced"])
            self.assertEqual(p102["wf12_00342260_hits"], 0)
            self.assertEqual(p102["emmc_mutation_bytes"], 0)
            self.assertEqual(sess.get_status()["interval_cache_lut_ftp"], p102)

    def test_p102_02_picture_cache_allowed_seconds_and_footprints(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p102_02_") as td:
            sess = self._new_session(td)
            for sec in (0, 2, 4, 8, 16):
                r = sess.set_interval_cache_lut_ftp({"cache_seconds": sec, "codec_profile": "XAVC_L_4K30"})
                self.assertTrue(r["ok"], msg=f"Failed cache_seconds={sec}: {r}")
                p102 = r["interval_cache_lut_ftp"]
                self.assertEqual(p102["effective_cache_seconds"], sec)
                self.assertEqual(p102["allocated_ddr_mib"], round(sec * 12.5, 2))
                self.assertLessEqual(p102["allocated_ddr_mib"], 384.0)
                self.assertFalse(p102["clamped_by_ddr_budget"])
                self.assertEqual(p102["timecode_forced_free_run"], sec > 0)

    def test_p102_03_picture_cache_rejects_invalid_seconds_and_codec_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p102_03_") as td:
            sess = self._new_session(td)
            for bad in (True, False, 1, 3, 5, 10, 32, -2, 2.5, float("nan"), float("inf"), "abc"):
                r = sess.set_interval_cache_lut_ftp({"cache_seconds": bad})
                self.assertFalse(r["ok"], msg=f"Should reject cache_seconds={bad!r}")
                self.assertEqual(r["error"], "invalid_cache_seconds")
            r_bad_codec = sess.set_interval_cache_lut_ftp({"codec_profile": "PRORES_8K_RAW"})
            self.assertFalse(r_bad_codec["ok"])
            self.assertEqual(r_bad_codec["error"], "invalid_codec_profile")

    def test_p102_04_picture_cache_deterministic_384mib_ddr_clamp(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p102_04_") as td:
            sess = self._new_session(td)
            r = sess.set_interval_cache_lut_ftp({"cache_seconds": 8, "codec_profile": "XAVC_I_4K60"})
            self.assertTrue(r["ok"])
            p102 = r["interval_cache_lut_ftp"]
            # 8s * 75 MiB/s = 600 MiB requested > 384 MiB -> clamped deterministically to 5s (375.0 MiB)
            self.assertEqual(p102["cache_seconds"], 8)
            self.assertEqual(p102["requested_ddr_mib"], 600.0)
            self.assertEqual(p102["max_safe_cache_seconds"], 5)
            self.assertEqual(p102["effective_cache_seconds"], 5)
            self.assertEqual(p102["allocated_ddr_mib"], 375.0)
            self.assertLessEqual(p102["allocated_ddr_mib"], 384.0)
            self.assertTrue(p102["clamped_by_ddr_budget"])
            self.assertGreaterEqual(p102["remaining_ddr_headroom_mib"], 0.0)

    def test_p102_05_picture_cache_auto_suspended_by_sq_and_restored(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p102_05_") as td:
            sess = self._new_session(td)
            sess.set_interval_cache_lut_ftp({"cache_seconds": 4, "codec_profile": "XAVC_I_4K24"})
            self.assertEqual(sess.get_interval_cache_lut_ftp()["effective_cache_seconds"], 4)

            # Activate S&Q VFR -> Picture Cache must suspend automatically
            r_sq = sess.set_cinema_param("fps", preset="119.88p (S&Q)")
            self.assertTrue(r_sq["ok"])
            p102_sq = sess.get_interval_cache_lut_ftp()
            self.assertTrue(p102_sq["picture_cache_suspended"])
            self.assertEqual(p102_sq["picture_cache_suspension_reason"], "S&Q_VFR_ACTIVE")
            self.assertEqual(p102_sq["effective_cache_seconds"], 0)
            self.assertEqual(p102_sq["allocated_ddr_mib"], 0.0)

            # Return to standard project fps -> Picture Cache automatically resumes 4s
            r_back = sess.set_cinema_param("fps", preset="23.98p")
            self.assertTrue(r_back["ok"])
            p102_resumed = sess.get_interval_cache_lut_ftp()
            self.assertFalse(p102_resumed["picture_cache_suspended"])
            self.assertEqual(p102_resumed["effective_cache_seconds"], 4)
            self.assertEqual(p102_resumed["allocated_ddr_mib"], 120.0)

    def test_p102_06_picture_cache_auto_suspended_by_interval_and_raw16(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p102_06_") as td:
            sess = self._new_session(td)
            sess.set_interval_cache_lut_ftp({"cache_seconds": 8, "codec_profile": "XAVC_L_4K60"})
            self.assertEqual(sess.get_interval_cache_lut_ftp()["effective_cache_seconds"], 8)

            # Enable Interval Rec -> Picture Cache auto-suspended
            sess.set_interval_cache_lut_ftp({"interval_rec_enabled": True})
            p_int = sess.get_interval_cache_lut_ftp()
            self.assertTrue(p_int["picture_cache_suspended"])
            self.assertEqual(p_int["picture_cache_suspension_reason"], "INTERVAL_REC_ACTIVE")
            self.assertEqual(p_int["effective_cache_seconds"], 0)

            # Disable Interval Rec, enable HDMI RAW16 -> suspended by HDMI_RAW16_ACTIVE
            sess.set_interval_cache_lut_ftp({"interval_rec_enabled": False})
            sess.set_cine_exposure({"wired_io_mode": "hdmi_raw16"})
            p_raw = sess.get_interval_cache_lut_ftp()
            self.assertTrue(p_raw["picture_cache_suspended"])
            self.assertEqual(p_raw["picture_cache_suspension_reason"], "HDMI_RAW16_ACTIVE")

    def test_p102_07_interval_rec_params_and_boundary_rejections(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p102_07_") as td:
            sess = self._new_session(td)
            for ae in ("High", "Mid", "Low", "Lock"):
                r = sess.set_interval_cache_lut_ftp(
                    {"interval_rec_enabled": True, "interval_sec": 1, "target_shots": 9999, "ae_tracking": ae}
                )
                self.assertTrue(r["ok"])
                self.assertEqual(r["interval_cache_lut_ftp"]["ae_tracking"], ae)
                self.assertEqual(r["interval_cache_lut_ftp"]["interval_sec"], 1)
                self.assertEqual(r["interval_cache_lut_ftp"]["target_shots"], 9999)

            for bad_sec in (0, 61, -1, 1.5, True, "bad"):
                r = sess.set_interval_cache_lut_ftp({"interval_sec": bad_sec})
                self.assertFalse(r["ok"])
                self.assertEqual(r["error"], "invalid_interval_sec")

            for bad_shots in (0, 10000, -5, True, "bad"):
                r = sess.set_interval_cache_lut_ftp({"target_shots": bad_shots})
                self.assertFalse(r["ok"])
                self.assertEqual(r["error"], "invalid_target_shots")

            r_ae = sess.set_interval_cache_lut_ftp({"ae_tracking": "UltraFast"})
            self.assertFalse(r_ae["ok"])
            self.assertEqual(r_ae["error"], "invalid_ae_tracking")

    def test_p102_08_interval_rec_electronic_shutter_enforced_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p102_08_") as td:
            sess = self._new_session(td)
            r_mech = sess.set_interval_cache_lut_ftp({"interval_rec_enabled": True, "mechanical_shutter": True})
            self.assertFalse(r_mech["ok"])
            self.assertEqual(r_mech["error"], "mechanical_shutter_forbidden_in_interval_rec")
            self.assertEqual(sess.get_interval_cache_lut_ftp()["mechanical_curtain_actuations"], 0)

            r_stype = sess.set_interval_cache_lut_ftp({"shutter_type": "MECHANICAL"})
            self.assertFalse(r_stype["ok"])
            self.assertEqual(r_stype["error"], "mechanical_shutter_forbidden_in_interval_rec")

    def test_p102_09_interval_rec_shot_counter_and_zero_curtain_actuations(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p102_09_") as td:
            sess = self._new_session(td)
            sess.set_interval_cache_lut_ftp({"interval_rec_enabled": True, "interval_sec": 2, "target_shots": 5})
            r1 = sess.set_interval_cache_lut_ftp({"trigger_shot": True})
            self.assertEqual(r1["interval_cache_lut_ftp"]["shots_taken"], 1)
            self.assertEqual(r1["mechanical_curtain_actuations"], 0)

            r2 = sess.set_interval_cache_lut_ftp({"advance_shots": 10})
            self.assertEqual(r2["interval_cache_lut_ftp"]["shots_taken"], 5)
            self.assertEqual(r2["interval_cache_lut_ftp"]["mechanical_curtain_actuations"], 0)

            r3 = sess.set_interval_cache_lut_ftp({"reset_shots": True})
            self.assertEqual(r3["interval_cache_lut_ftp"]["shots_taken"], 0)

    def test_p102_10_interval_rec_and_sq_mutual_exclusion(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p102_10_") as td:
            sess = self._new_session(td)
            r0 = sess.set_cinema_param("fps", preset="119.88p (S&Q)")
            self.assertTrue(r0["ok"])
            self.assertTrue(sess.sq_enabled)

            # Enabling Interval Rec disables S&Q
            r = sess.set_interval_cache_lut_ftp({"interval_rec_enabled": True})
            self.assertTrue(r["ok"])
            self.assertFalse(sess.sq_enabled)
            self.assertTrue(r["interval_cache_lut_ftp"]["interval_rec_enabled"])

            # Enabling S&Q via set_cine_exposure disables Interval Rec
            r2 = sess.set_cine_exposure({"sq_enabled": True, "sq_fps": 60})
            self.assertTrue(r2["ok"], msg=r2)
            self.assertTrue(sess.sq_enabled)
            self.assertFalse(sess.get_interval_cache_lut_ftp()["interval_rec_enabled"])

    def test_p102_11_cube_lut_17_to_33_tetrahedral_ram_only(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p102_11_") as td:
            sess = self._new_session(td)
            cube_17 = _make_sample_cube(size=17, title="Kafu_17_TealGold")
            res = sess.upload_cube_lut({"slot": "User2", "cube_text": cube_17})
            self.assertTrue(res["ok"], msg=res)
            lut = res["lut"]
            self.assertEqual(lut["source_grid_size"], 17)
            self.assertEqual(lut["target_grid_size"], 33)
            self.assertEqual(lut["triplets"], 17 ** 3)
            self.assertEqual(lut["resampled_33_triplets"], 33 ** 3)
            self.assertEqual(lut["resampling_method"], "tetrahedral")
            self.assertEqual(lut["title"], "Kafu_17_TealGold")
            self.assertTrue(res["volatile_ram_only"])
            self.assertFalse(res["persistent_emmc_writes_authorized"])
            self.assertEqual(res["emmc_mutation_bytes"], 0)
            self.assertEqual(len(sess._user_lut_33_ram_tables["User2"]), 33 ** 3)

    def test_p102_12_cube_lut_33_to_33_parity(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p102_12_") as td:
            sess = self._new_session(td)
            cube_33 = _make_sample_cube(size=33, title="Sony_33_Direct")
            res = sess.upload_cube_lut({"slot": "User1", "cube_text": cube_33})
            self.assertTrue(res["ok"])
            lut = res["lut"]
            self.assertEqual(lut["source_grid_size"], 33)
            self.assertEqual(lut["target_grid_size"], 33)
            self.assertEqual(lut["resampled_33_triplets"], 33 ** 3)
            self.assertEqual(len(lut["resampled_33_sha256"]), 64)

    def test_p102_13_cube_lut_65_to_33_tetrahedral_resampler(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p102_13_") as td:
            sess = self._new_session(td)
            cube_65 = _make_sample_cube(size=65, title="ARRI_65_CineLogC")
            res = sess.upload_cube_lut({"slot": "User3", "cube_text": cube_65})
            self.assertTrue(res["ok"], msg=res)
            lut = res["lut"]
            self.assertEqual(lut["source_grid_size"], 65)
            self.assertEqual(lut["target_grid_size"], 33)
            self.assertEqual(lut["triplets"], 65 ** 3)
            self.assertEqual(lut["resampled_33_triplets"], 33 ** 3)
            self.assertEqual(lut["resampling_method"], "tetrahedral")
            self.assertEqual(lut["emmc_mutation_bytes"], 0)
            self.assertEqual(len(sess._user_lut_33_ram_tables["User3"]), 33 ** 3)

    def test_p102_14_cube_lut_domain_min_max_scaling_and_title(self) -> None:
        cube_scaled = _make_sample_cube(
            size=17,
            title="Scaled_Domain_LUT",
            domain_min=(-0.1, -0.05, 0.0),
            domain_max=(1.2, 1.15, 1.1),
        )
        res = run_fx6_menu_trial.validate_and_sanitize_cube_lut(cube_scaled, include_33_table=True)
        self.assertTrue(res["ok"], msg=res)
        self.assertEqual(res["title"], "Scaled_Domain_LUT")
        self.assertEqual(res["domain_min"], [-0.1, -0.05, 0.0])
        self.assertEqual(res["domain_max"], [1.2, 1.15, 1.1])
        self.assertEqual(res["resampled_33_triplets"], 33 ** 3)
        self.assertEqual(len(res["_table_33"]), 33 ** 3)

    def test_p102_15_cube_lut_fail_closed_rejections_nan_inf_inverted_domain(self) -> None:
        # 1) NaN triplet
        bad_nan = _make_sample_cube(size=17, title="BadNaN").replace("\n0.000000 0.000000 0.000000\n", "\nNaN 0.0 0.0\n", 1)
        r_nan = run_fx6_menu_trial.validate_and_sanitize_cube_lut(bad_nan)
        self.assertFalse(r_nan["ok"])
        self.assertEqual(r_nan["error"], "nan_or_inf_triplet")

        # 2) Inf triplet
        bad_inf = _make_sample_cube(size=17, title="BadInf").replace("1.000000 1.000000 0.940000", "inf 1.0 1.0", 1)
        r_inf = run_fx6_menu_trial.validate_and_sanitize_cube_lut(bad_inf)
        self.assertFalse(r_inf["ok"])
        self.assertEqual(r_inf["error"], "nan_or_inf_triplet")

        # 3) Inverted DOMAIN_MIN >= DOMAIN_MAX
        bad_dom = _make_sample_cube(size=17, title="InvDom", domain_min=(1.0, 0.0, 0.0), domain_max=(0.5, 1.0, 1.0))
        r_dom = run_fx6_menu_trial.validate_and_sanitize_cube_lut(bad_dom)
        self.assertFalse(r_dom["ok"])
        self.assertEqual(r_dom["error"], "invalid_domain_bounds")

        # 4) Truncated triplet count
        lines = _make_sample_cube(size=17, title="Trunc").splitlines()
        r_trunc = run_fx6_menu_trial.validate_and_sanitize_cube_lut("\n".join(lines[:-10]))
        self.assertFalse(r_trunc["ok"])
        self.assertEqual(r_trunc["error"], "triplet_count_mismatch")

        # 5) Unsupported LUT_3D_SIZE (e.g. 9)
        r_size = run_fx6_menu_trial.validate_and_sanitize_cube_lut("LUT_3D_SIZE 9\n0 0 0\n")
        self.assertFalse(r_size["ok"])
        self.assertEqual(r_size["error"], "unsupported_lut_3d_size")

    def test_p102_16_cube_lut_scope_preview_preserves_phase56_keys(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p102_16_") as td:
            sess = self._new_session(td)
            base_scope = sess.get_scope_stats(refresh=False)
            self.assertIn("histograms", base_scope)
            self.assertIn("waveform", base_scope)
            self.assertIn("lut_preview", base_scope)
            self.assertFalse(base_scope["lut_preview"]["active"])

            sess.upload_cube_lut({"slot": "User4", "cube_text": _make_sample_cube(size=17, title="ScopeTint")})
            lut_scope = sess.get_scope_stats(refresh=False)
            self.assertTrue(lut_scope["lut_preview"]["active"])
            self.assertEqual(lut_scope["lut_preview"]["slot"], "User4")
            self.assertEqual(lut_scope["lut_preview"]["title"], "ScopeTint")
            self.assertEqual(len(lut_scope["lut_preview"]["resampled_33_sha256"]), 64)

    def test_p102_17_wired_usblan_ftps_queue_and_completion(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p102_17_") as td:
            sess = self._new_session(td)
            r1 = sess.set_interval_cache_lut_ftp({"ftps_mode": "Original_And_Proxy", "enqueue_current_clip": True})
            self.assertTrue(r1["ok"])
            p1 = r1["interval_cache_lut_ftp"]
            self.assertEqual(p1["ftps_mode"], "Original_And_Proxy")
            self.assertEqual(p1["ftps_transport"], "USB_LAN_CDC_NCM_RTL8153")
            self.assertEqual(p1["ftps_queued_count"], 2)  # main MXF + proxy MP4
            self.assertEqual(p1["ftps_completed_count"], 0)
            self.assertEqual(p1["wf12_00342260_hits"], 0)

            r2 = sess.set_interval_cache_lut_ftp({"process_next_job": True})
            self.assertTrue(r2["ok"])
            p2 = r2["interval_cache_lut_ftp"]
            self.assertEqual(p2["ftps_queued_count"], 1)
            self.assertEqual(p2["ftps_completed_count"], 1)
            self.assertEqual(p2["ftps_completed"][0]["status"], "COMPLETED")
            self.assertEqual(p2["ftps_completed"][0]["wf12_00342260_hits"], 0)

    def test_p102_18_ftps_p12_rf_off_enforced_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p102_18_") as td:
            sess = self._new_session(td)
            for bad_patch in (
                {"wifi_enabled": True},
                {"bt_enabled": True},
                {"wifi_bt_rf_disabled": False},
                {"p12_rf_off_enforced": False},
                {"ftps_transport": "WiFi_80211ac"},
                {"ftps_nic_driver": "BCM4375_WIFI"},
            ):
                r = sess.set_interval_cache_lut_ftp(bad_patch)
                self.assertFalse(r["ok"], msg=f"Should reject P12 RF tampering: {bad_patch}")
                self.assertEqual(r["error"], "p12_rf_off_violation")
                self.assertEqual(sess.get_interval_cache_lut_ftp()["wf12_00342260_hits"], 0)

    def test_p102_19_ftps_blocks_emmc_p1_p15_path_traversal_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p102_19_") as td:
            sess = self._new_session(td)
            bad_paths = [
                "/dev/mmcblk0p1",
                "/dev/mmcblk0p12",
                "/dev/mmcblk0p15",
                "/dev/block/by-name/p4",
                "/mnt/slot_a/../../dev/mmcblk0p8",
                "/dev/nflasha",
                "/setting/cam_calib/p12_rf.bin",
                "/mnt/slot_a/..\\..\\etc\\passwd",
                "/var/log/syslog",
            ]
            for idx, bp in enumerate(bad_paths, 1):
                r = sess.set_interval_cache_lut_ftp({"ftps_mode": "Proxy_Only", "enqueue_path": bp})
                self.assertFalse(r["ok"], msg=f"Should block traversal path {bp!r}")
                self.assertEqual(r["error"], "emmc_path_traversal_blocked")
                self.assertEqual(r["ftps_blocked_traversal_count"], idx)

            p102 = sess.get_interval_cache_lut_ftp()
            self.assertEqual(p102["ftps_queued_count"], 0)
            self.assertEqual(p102["ftps_blocked_traversal_count"], len(bad_paths))

    def test_p102_20_mailbox_mb48_51_iclf_packing_and_defaults(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p102_20_") as td:
            sess = self._new_session(td)
            raw = sess._pack_phase102_mailbox_bytes()
            self.assertEqual(len(raw), 16)
            mb48, mb49, mb50, mb51 = struct.unpack("<4I", raw)
            self.assertEqual(mb48, 0xA2800000)
            self.assertEqual(mb49, 0xC01E0000)
            self.assertEqual(mb50, 0x80001900)
            self.assertEqual(mb51, 0x49434C46)  # 'ICLF'

            sess.set_interval_cache_lut_ftp(
                {
                    "cache_seconds": 8,
                    "codec_profile": "XAVC_I_4K60",
                    "ftps_mode": "Proxy_Only",
                    "enqueue_current_clip": True,
                }
            )
            sess.upload_cube_lut({"slot": "User2", "cube_text": _make_sample_cube(size=65, title="HUD_LUT")})
            mb48_2, mb49_2, mb50_2, mb51_2 = struct.unpack("<4I", sess._pack_phase102_mailbox_bytes())
            self.assertEqual(mb51_2, 0x49434C46)
            self.assertEqual(mb48_2 & 0x1F, 5)  # clamped effective 5s
            self.assertEqual((mb48_2 >> 5) & 0x1F, 8)  # requested 8s
            self.assertEqual((mb48_2 >> 10) & 0x1FF, 375)  # 375 MiB
            self.assertEqual((mb48_2 >> 21) & 0x01, 1)  # clamped flag
            self.assertEqual((mb49_2 >> 28) & 0x03, 1)  # Proxy_Only
            self.assertEqual((mb49_2 >> 30) & 0x03, 3)  # p12_safe & e_shutter
            self.assertEqual(mb50_2 & 0x07, 2)  # User2
            self.assertEqual((mb50_2 >> 3) & 0x01, 1)  # resampled 33^3
            self.assertEqual((mb50_2 >> 4) & 0x03, 3)  # source size 65
            self.assertEqual((mb50_2 >> 14) & 0xFF, 1)  # ftps_queued_count == 1

    def test_p102_21_xml_sidecar_includes_cube_title_sha256_and_p102_group(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p102_21_") as td:
            sess = self._new_session(td)
            sess.set_interval_cache_lut_ftp(
                {"cache_seconds": 4, "codec_profile": "XAVC_I_4K24", "ftps_mode": "Proxy_Only"}
            )
            up = sess.upload_cube_lut({"slot": "User1", "cube_text": _make_sample_cube(size=17, title="XML_Check_LUT")})
            sha33 = up["resampled_33_sha256"]

            sidecar = sess.get_xml_sidecar()
            xml_str = sidecar["xml"]
            root = ET.fromstring(xml_str)
            self.assertIsNotNone(root)
            self.assertIn('<Item name="MonitoringLutTitle" value="XML_Check_LUT" />', xml_str)
            self.assertIn(f'<Item name="MonitoringLutResampled33Sha256" value="{sha33}" />', xml_str)
            self.assertIn('<Group name="PictureCacheIntervalCubeFtps">', xml_str)
            self.assertIn('<Item name="ElectronicShutterEnforced" value="true" />', xml_str)
            self.assertIn('<Item name="P12RfOffEnforced" value="true" />', xml_str)
            self.assertIn('<Item name="Wf12Calls" value="0" />', xml_str)

    def test_p102_22_camset_export_import_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p102_22_") as td:
            s1 = self._new_session(td + "_1")
            s1.set_interval_cache_lut_ftp(
                {
                    "cache_seconds": 4,
                    "codec_profile": "XAVC_L_4K60",
                    "interval_rec_enabled": True,
                    "interval_sec": 7,
                    "target_shots": 300,
                    "advance_shots": 12,
                    "ae_tracking": "Low",
                    "ftps_mode": "Original_And_Proxy",
                }
            )
            exported = s1.export_camset_preset()
            self.assertIn("interval_cache_lut_ftp", exported)
            self.assertEqual(exported["interval_cache_lut_ftp"]["shots_taken"], 12)

            s2 = self._new_session(td + "_2")
            imp = s2.import_camset_preset(exported)
            self.assertTrue(imp["ok"], msg=imp)
            p2 = s2.get_interval_cache_lut_ftp()
            self.assertEqual(p2["cache_seconds"], 4)
            self.assertEqual(p2["codec_profile"], "XAVC_L_4K60")
            self.assertTrue(p2["interval_rec_enabled"])
            self.assertEqual(p2["interval_sec"], 7)
            self.assertEqual(p2["target_shots"], 300)
            self.assertEqual(p2["shots_taken"], 12)
            self.assertEqual(p2["ae_tracking"], "Low")
            self.assertEqual(p2["ftps_mode"], "Original_And_Proxy")
            self.assertEqual(p2["mechanical_curtain_actuations"], 0)
            self.assertEqual(p2["wf12_00342260_hits"], 0)

    def test_p102_23_camset_import_rejects_p102_tampering_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p102_23_") as td:
            sess = self._new_session(td)
            base = sess.export_camset_preset()

            tamper_mech = json.loads(json.dumps(base))
            tamper_mech["interval_cache_lut_ftp"]["mechanical_shutter"] = True
            r1 = sess.import_camset_preset(tamper_mech)
            self.assertFalse(r1["ok"])
            self.assertEqual(r1["error"], "mechanical_shutter_forbidden_in_interval_rec")

            tamper_rf = json.loads(json.dumps(base))
            tamper_rf["interval_cache_lut_ftp"]["wifi_enabled"] = True
            r2 = sess.import_camset_preset(tamper_rf)
            self.assertFalse(r2["ok"])
            self.assertEqual(r2["error"], "p12_rf_off_violation")

            tamper_cache = json.loads(json.dumps(base))
            tamper_cache["interval_cache_lut_ftp"]["cache_seconds"] = 99
            r3 = sess.import_camset_preset(tamper_cache)
            self.assertFalse(r3["ok"])
            self.assertEqual(r3["error"], "invalid_cache_seconds")

    def test_p102_24_http_get_post_interval_cache_lut_ftp_and_errors(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p102_24_") as td:
            _sess, srv, t, base = self._start_http_server(td)
            try:
                st_g, body_g = self._http_get_json(f"{base}/api/interval_cache_lut_ftp")
                self.assertEqual(st_g, 200)
                self.assertTrue(body_g["ok"])
                self.assertEqual(body_g["interval_cache_lut_ftp"]["ddr_budget_mib"], 384.0)

                st_p, body_p = self._http_post_json(
                    f"{base}/api/interval_cache_lut_ftp",
                    {"cache_seconds": 8, "codec_profile": "XAVC_I_4K60", "ftps_mode": "Proxy_Only"},
                )
                self.assertEqual(st_p, 200)
                self.assertTrue(body_p["ok"])
                self.assertEqual(body_p["interval_cache_lut_ftp"]["effective_cache_seconds"], 5)

                st_bad_json, body_bad_json = self._http_post_json(f"{base}/api/interval_cache_lut_ftp", b"{broken")
                self.assertEqual(st_bad_json, 400)
                self.assertEqual(body_bad_json["error"], "invalid_json")

                st_trav, body_trav = self._http_post_json(
                    f"{base}/api/interval_cache_lut_ftp",
                    {"enqueue_path": "/dev/mmcblk0p12"},
                )
                self.assertEqual(st_trav, 400)
                self.assertEqual(body_trav["error"], "emmc_path_traversal_blocked")
            finally:
                srv.shutdown()
                srv.server_close()
                t.join(timeout=2)

    def test_p102_25_http_upload_cube_lut_valid_and_fail_closed_400(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p102_25_") as td:
            _sess, srv, t, base = self._start_http_server(td)
            try:
                st_g, body_g = self._http_get_json(f"{base}/api/upload_cube_lut")
                self.assertEqual(st_g, 200)
                self.assertIn("slots", body_g)

                st_ok, body_ok = self._http_post_json(
                    f"{base}/api/upload_cube_lut",
                    {"slot": "User2", "cube_text": _make_sample_cube(size=17, title="HTTP_17_Cube")},
                )
                self.assertEqual(st_ok, 200)
                self.assertTrue(body_ok["ok"])
                self.assertEqual(body_ok["lut"]["source_grid_size"], 17)
                self.assertEqual(body_ok["lut"]["target_grid_size"], 33)
                self.assertEqual(body_ok["emmc_mutation_bytes"], 0)

                bad_nan = _make_sample_cube(size=17, title="HTTP_NaN").replace("\n0.000000 0.000000 0.000000\n", "\nnan 0 0\n", 1)
                st_nan, body_nan = self._http_post_json(
                    f"{base}/api/upload_cube_lut",
                    {"slot": "User2", "cube_text": bad_nan},
                )
                self.assertEqual(st_nan, 400)
                self.assertFalse(body_nan["ok"])
                self.assertEqual(body_nan["error"], "nan_or_inf_triplet")

                bad_dom = _make_sample_cube(size=17, title="HTTP_InvDom", domain_min=(1, 0, 0), domain_max=(0, 1, 1))
                st_dom, body_dom = self._http_post_json(
                    f"{base}/api/upload_cube_lut",
                    {"slot": "User2", "cube_text": bad_dom},
                )
                self.assertEqual(st_dom, 400)
                self.assertFalse(body_dom["ok"])
                self.assertEqual(body_dom["error"], "invalid_domain_bounds")
            finally:
                srv.shutdown()
                srv.server_close()
                t.join(timeout=2)

    def test_p102_26_http_xml_sidecar_live_lut_sha256_and_p102_group(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p102_26_") as td:
            _sess, srv, t, base = self._start_http_server(td)
            try:
                _st, up = self._http_post_json(
                    f"{base}/api/upload_cube_lut",
                    {"slot": "User1", "cube_text": _make_sample_cube(size=17, title="HTTP_Sidecar_LUT")},
                )
                sha33 = up["resampled_33_sha256"]
                st_x, xml_body = self._http_get_text(f"{base}/api/xml_sidecar")
                self.assertEqual(st_x, 200)
                self.assertIn("HTTP_Sidecar_LUT", xml_body)
                self.assertIn(sha33, xml_body)
                self.assertIn("PictureCacheIntervalCubeFtps", xml_body)

                st_j, j = self._http_get_json(f"{base}/api/xml_sidecar?format=json")
                self.assertEqual(st_j, 200)
                self.assertEqual(j["interval_cache_lut_ftp"]["active_user_lut_resampled_33_sha256"], sha33)
            finally:
                srv.shutdown()
                srv.server_close()
                t.join(timeout=2)

    def test_p102_27_http_web_ui_4_language_controls_present(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p102_27_") as td:
            _sess, srv, t, base = self._start_http_server(td)
            try:
                st, html = self._http_get_text(f"{base}/")
                self.assertEqual(st, 200)
                self.assertIn("phase102-cache-lut-ftp-card", html)
                self.assertIn("/api/interval_cache_lut_ftp", html)
                self.assertIn("/api/upload_cube_lut", html)
                self.assertIn("syncPhase102IntervalCacheLutFtpUI", html)
                self.assertIn("P102_I18N", html)
                # Verify all 4 languages exist in Web UI
                self.assertIn("Picture Cache (Pre-Rec DDR)", html)
                self.assertIn("预录制 Picture Cache (DDR 环缓)", html)
                self.assertIn("預錄製 Picture Cache (DDR 環緩)", html)
                self.assertIn("ピクチャーキャッシュ (Pre-Rec DDR)", html)
            finally:
                srv.shutdown()
                srv.server_close()
                t.join(timeout=2)

    def test_p102_28_reset_clears_phase102_state_cleanly(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p102_28_") as td:
            sess = self._new_session(td)
            sess.set_interval_cache_lut_ftp(
                {
                    "cache_seconds": 8,
                    "interval_rec_enabled": True,
                    "advance_shots": 15,
                    "ftps_mode": "Proxy_Only",
                    "enqueue_current_clip": True,
                    "process_next_job": True,
                }
            )
            sess.set_interval_cache_lut_ftp({"enqueue_path": "/dev/mmcblk0p5"})
            res = sess.set_interval_cache_lut_ftp({"reset": True})
            self.assertTrue(res["ok"])
            p102 = res["interval_cache_lut_ftp"]
            self.assertEqual(p102["cache_seconds"], 0)
            self.assertFalse(p102["interval_rec_enabled"])
            self.assertEqual(p102["shots_taken"], 0)
            self.assertEqual(p102["ftps_mode"], "Off")
            self.assertEqual(p102["ftps_queued_count"], 0)
            self.assertEqual(p102["ftps_completed_count"], 0)
            self.assertEqual(p102["ftps_blocked_traversal_count"], 0)

    def test_p102_29_cli_workdir_and_work_dir_alias_supported(self) -> None:
        py_src = (TRIAL_DIR / "run_fx6_menu_trial.py").read_text(encoding="utf-8")
        self.assertIn('"--workdir"', py_src)
        self.assertIn('"--work-dir"', py_src)
        self.assertIn('dest="workdir"', py_src)

    def test_p102_30_guest_c_source_mb48_51_iclf_hud_and_heap_free_hygiene(self) -> None:
        c_path = TRIAL_DIR / "src" / "fx6_live_guest.c"
        c_src = c_path.read_text(encoding="utf-8")
        self.assertIn("0x49434c46u", c_src)
        self.assertIn("g_live_p102_cache_interval", c_src)
        self.assertIn("g_live_p102_interval_ftp", c_src)
        self.assertIn("g_live_p102_lut_ftps", c_src)
        self.assertIn("fx6_render_phase102_cache_interval_lut_ftps_overlay", c_src)
        self.assertIn('"[CACHE "', c_src)
        self.assertIn('"[INTVL "', c_src)
        self.assertIn('"[LUT U"', c_src)
        self.assertIn('"[FTPS:"', c_src)
        self.assertIn("for (int i = 0; i < 48; i++) mb[i] = 0;", c_src)

        start_idx = c_src.index("fx6_render_phase102_cache_interval_lut_ftps_overlay")
        end_idx = c_src.index("/* ---------------- Frame Cache", start_idx)
        overlay_body = c_src[start_idx:end_idx]
        self.assertNotIn("malloc(", overlay_body)
        self.assertNotIn("calloc(", overlay_body)
        self.assertNotIn("realloc(", overlay_body)
        self.assertNotIn("printf(", overlay_body)

    def test_p102_31_port_isolation_no_hardcoded_live_port(self) -> None:
        c_src = (TRIAL_DIR / "src" / "fx6_live_guest.c").read_text(encoding="utf-8")
        self.assertNotIn("8768", c_src)
        py_src = (TRIAL_DIR / "run_fx6_menu_trial.py").read_text(encoding="utf-8")
        p102_start = py_src.index("FX3_TOTAL_AP_DRAM_MIB")
        p102_end = py_src.index("def _relocate_migrated_path", p102_start)
        self.assertNotIn("8768", py_src[p102_start:p102_end])

    def test_p102_32_dual_mode_clean_room_and_zero_emmc_mutation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p102_32_") as td:
            sess = self._new_session(td)
            up = sess.upload_cube_lut({"slot": "User1", "preset": "teal_orange", "size": 17})
            self.assertTrue(up["ok"])
            self.assertFalse(up["persistent_emmc_writes_authorized"])
            self.assertEqual(up["emmc_mutation_bytes"], 0)
            st = sess.get_interval_cache_lut_ftp()
            self.assertFalse(st["persistent_emmc_writes_authorized"])
            self.assertEqual(st["emmc_mutation_bytes"], 0)
            _ = _force_clean_room()


if __name__ == "__main__":
    unittest.main()
