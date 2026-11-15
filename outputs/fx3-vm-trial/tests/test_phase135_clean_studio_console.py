#!/usr/bin/env python3
"""Phase 135 Unit & Integration Tests:
- Clean Camera Studio Console UI Refactor (First-Screen Monitor + Native Page/Menu Nav + Big-6 + Sticky FX6/FX3 Decks)
- Default-Collapsed Advanced Engineering Lab Drawer (`#studio-advanced-lab-drawer`) with 6 Category Tabs + Show All
- Clean `<h3>` Headings & JS `P*_I18N` Titles (Zero raw `Phase XX ·` or `(/api/...)` clutter)
- Pure Native Screen Mode (`bit 30 = 0x40000000` on `p40_flags_word`) & 1-Click Clear All Overlays (`/api/studio_screen_mode`)
- Zero Python 3.14 `SyntaxWarning`s in `run_fx6_menu_trial.py`

Dual-mode safe:
- Passes 100% in both Local Donor mode and `FX3_FX6_FORCE_CLEAN_ROOM=1` mode.
- Never spawns any QEMU process and never touches port 8768.
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import ast
import json
import os
import re
import shutil
import struct
import subprocess
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
import warnings
from pathlib import Path

TRIAL_DIR = Path(__file__).resolve().parents[1]
if str(TRIAL_DIR) not in sys.path:
    sys.path.insert(0, str(TRIAL_DIR))

import run_fx6_menu_trial  # noqa: E402


def _force_clean_room() -> bool:
    return os.environ.get("FX3_FX6_FORCE_CLEAN_ROOM", "").strip().lower() in ("1", "true", "yes")


class TestPhase135CleanStudioConsole(unittest.TestCase):
    def _new_session(self, td: str) -> run_fx6_menu_trial.FX6LiveGpe0Session:
        return run_fx6_menu_trial.FX6LiveGpe0Session(Path(td) / "sess", port=18785)

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

    def test_p135_01_default_pure_native_off_for_headless_compat(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p135_01_") as td:
            sess = self._new_session(td)
            self.assertFalse(sess.pure_native_screen)
            self.assertFalse(sess.studio_overlays_cleared)
            self.assertEqual(sess.studio_screen_mode_seq, 0)
            mode = sess.get_studio_screen_mode()
            self.assertFalse(mode["pure_native_screen"])
            self.assertFalse(mode["overlays_cleared"])
            self.assertEqual(mode["guest_bit30_pure_native"], 0)
            self.assertEqual(mode["active_overlay_count"], 0)

    def test_p135_02_studio_screen_mode_status_fields(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p135_02_") as td:
            sess = self._new_session(td)
            st = sess.get_status()
            self.assertIn("pure_native_screen", st)
            self.assertIn("studio_screen_mode", st)
            self.assertFalse(st["pure_native_screen"])
            sm = st["studio_screen_mode"]
            for k in (
                "pure_native_screen",
                "overlays_cleared",
                "studio_overlays_cleared",
                "active_overlay_count",
                "guest_bit30_pure_native",
                "studio_screen_mode_seq",
                "active_overlay_summary",
            ):
                self.assertIn(k, sm)

    @staticmethod
    def _pack_all_mailbox_words(sess: run_fx6_menu_trial.FX6LiveGpe0Session) -> tuple[int, ...]:
        raw = (
            sess._pack_full_mailbox_bytes()
            + sess._pack_phase73_mailbox_bytes()
            + sess._pack_phase81_mailbox_bytes()
            + sess._pack_phase88_mailbox_bytes()
            + sess._pack_phase95_mailbox_bytes()
            + sess._pack_phase102_mailbox_bytes()
            + sess._pack_phase109_mailbox_bytes()
            + sess._pack_phase116_mailbox_bytes()
            + sess._pack_phase123_mailbox_bytes()
            + sess._pack_phase129_mailbox_bytes()
            + sess._pack_phase129_umd_bytes()
        )
        return struct.unpack("<72I", raw)

    def test_p135_03_set_pure_native_true_sets_mb_p40_bit30(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p135_03_") as td:
            sess = self._new_session(td)
            res = sess.set_studio_screen_mode({"pure_native_screen": True})
            self.assertTrue(res["ok"])
            self.assertTrue(res["pure_native_screen"])
            self.assertEqual(res["studio_screen_mode"]["guest_bit30_pure_native"], 1)
            mb = self._pack_all_mailbox_words(sess)
            self.assertEqual(mb[27] & 0x40000000, 0x40000000)

    def test_p135_04_set_pure_native_false_clears_mb_p40_bit30(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p135_04_") as td:
            sess = self._new_session(td)
            sess.set_studio_screen_mode({"pure_native_screen": True})
            res = sess.set_studio_screen_mode({"pure_native_screen": False})
            self.assertTrue(res["ok"])
            self.assertFalse(res["pure_native_screen"])
            mb = self._pack_all_mailbox_words(sess)
            self.assertEqual(mb[27] & 0x40000000, 0)

    def test_p135_05_toggle_flips_pure_native_state(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p135_05_") as td:
            sess = self._new_session(td)
            r1 = sess.set_studio_screen_mode({"toggle": True})
            self.assertTrue(r1["pure_native_screen"])
            self.assertEqual(r1["studio_screen_mode"]["studio_screen_mode_seq"], 1)
            r2 = sess.set_studio_screen_mode({"toggle": True})
            self.assertFalse(r2["pure_native_screen"])
            self.assertEqual(r2["studio_screen_mode"]["studio_screen_mode_seq"], 2)

    def test_p135_06_clear_all_overlays_resets_every_phase_overlay(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p135_06_") as td:
            sess = self._new_session(td)
            sess.set_assist_tools({"aspect_marker": "2.39:1", "zebra_mode": "70%", "peaking_mode": "Red", "desqueeze": "2.0x"})
            sess.set_touch_focus_ciz({"touch_af_mode": "touch_tracking", "focus_mag": "4.0x", "false_color_mode": "slog3_ire"})
            sess.set_gyroflow_anamorphic({"squeeze_factor": 2.0, "color_bars_enabled": True, "ref_tone_enabled": True})
            sess.set_mxf_ptpv2_tally({"tally_state": "PGM_RED", "osd_tally_indicator": True})
            self.assertGreater(sess.get_studio_screen_mode()["active_overlay_count"], 0)

            res = sess.set_studio_screen_mode({"clear_all_overlays": True})
            self.assertTrue(res["ok"])
            self.assertTrue(res["pure_native_screen"])
            self.assertTrue(res["overlays_cleared"])
            self.assertEqual(res["studio_screen_mode"]["active_overlay_count"], 0)
            self.assertEqual(sess.aspect_marker, "Off")
            self.assertEqual(sess.zebra_mode, "Off")
            self.assertEqual(sess.peaking_mode, "Off")
            self.assertEqual(sess.desqueeze, "1.0x")
            self.assertEqual(sess.touch_af_mode, "off")
            self.assertEqual(sess.focus_mag, "1.0x")
            self.assertEqual(sess.false_color_mode, "off")
            self.assertFalse(sess.color_bars_enabled)
            self.assertFalse(sess.ref_tone_enabled)
            self.assertEqual(sess.tally_state, "OFF")
            self.assertFalse(sess.osd_tally_indicator)

    def test_p135_07_clear_all_overlays_gates_mailbox_bit31_and_p56(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p135_07_") as td:
            sess = self._new_session(td)
            sess.set_studio_screen_mode({"clear_all_overlays": True})
            mb = self._pack_all_mailbox_words(sess)
            self.assertEqual(mb[27] & 0x40000000, 0x40000000)
            self.assertEqual((mb[27] >> 24) & 1, 0)
            for idx in (28, 32, 38, 41, 44, 46, 48, 50, 52, 53, 54, 56, 57, 58, 60, 61, 62, 64, 65, 66):
                self.assertEqual(mb[idx] & 0x80000000, 0, msg=f"mb[{idx}] bit31 should be cleared")

    def test_p135_08_subsequent_phase_setter_rearms_overlays(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p135_08_") as td:
            sess = self._new_session(td)
            sess.set_studio_screen_mode({"clear_all_overlays": True})
            self.assertTrue(sess.studio_overlays_cleared)
            sess.set_assist_tools({"aspect_marker": "1.85:1"})
            self.assertFalse(sess.studio_overlays_cleared)
            mb = self._pack_all_mailbox_words(sess)
            self.assertEqual((mb[27] >> 24) & 1, 1)

    def test_p135_09_reset_restores_initial_screen_mode(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p135_09_") as td:
            sess = self._new_session(td)
            sess.set_studio_screen_mode({"pure_native_screen": True, "clear_all_overlays": True})
            res = sess.set_studio_screen_mode({"reset": True})
            self.assertTrue(res["ok"])
            self.assertFalse(res["pure_native_screen"])
            self.assertFalse(res["overlays_cleared"])

    def test_p135_10_validation_rejects_invalid_and_missing_params(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p135_10_") as td:
            sess = self._new_session(td)
            self.assertEqual(sess.set_studio_screen_mode("bad")["error"], "invalid_request_body")
            self.assertEqual(sess.set_studio_screen_mode({})["error"], "missing_studio_screen_mode_param")
            self.assertEqual(sess.set_studio_screen_mode({"pure_native_screen": "maybe"})["error"], "invalid_pure_native_screen")
            self.assertEqual(sess.set_studio_screen_mode({"clear_all_overlays": "maybe"})["error"], "invalid_clear_all_overlays")
            self.assertEqual(sess.set_studio_screen_mode({"toggle": "maybe"})["error"], "invalid_toggle")
            self.assertEqual(sess.set_studio_screen_mode({"reset": "maybe"})["error"], "invalid_reset")

    def test_p135_11_http_get_and_post_studio_screen_mode_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p135_11_") as td:
            _sess, srv, _t, base = self._start_http_server(td)
            try:
                st, g0 = self._http_get_json(f"{base}/api/studio_screen_mode")
                self.assertEqual(st, 200)
                self.assertFalse(g0["pure_native_screen"])

                st, p1 = self._http_post_json(f"{base}/api/studio_screen_mode", {"pure_native_screen": True, "clear_all_overlays": True})
                self.assertEqual(st, 200)
                self.assertTrue(p1["ok"])
                self.assertTrue(p1["pure_native_screen"])
                self.assertTrue(p1["overlays_cleared"])

                st_bad, err_bad = self._http_post_json(f"{base}/api/studio_screen_mode", b"{bad-json")
                self.assertEqual(st_bad, 400)
                self.assertEqual(err_bad["error"], "invalid_json")
            finally:
                srv.shutdown()
                srv.server_close()

    def test_p135_12_http_query_param_fallback_post(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p135_12_") as td:
            _sess, srv, _t, base = self._start_http_server(td)
            try:
                st, res = self._http_post_json(f"{base}/api/studio_screen_mode?pure_native_screen=true&clear_all_overlays=true", b"")
                self.assertEqual(st, 200)
                self.assertTrue(res["ok"])
                self.assertTrue(res["pure_native_screen"])
                self.assertTrue(res["overlays_cleared"])
            finally:
                srv.shutdown()
                srv.server_close()

    def test_p135_13_first_screen_html_layout_order(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p135_13_") as td:
            _sess, srv, _t, base = self._start_http_server(td)
            try:
                st, html = self._http_get_text(f"{base}/")
                self.assertEqual(st, 200)
                idx_bar = html.index('id="studio-top-bar"')
                idx_screen = html.index('id="screen-wrap"')
                idx_nav = html.index('id="fx6-native-nav-card"')
                idx_pages = html.index('id="page-buttons"')
                idx_cats = html.index('id="cat-buttons"')
                idx_128 = html.index('id="all128-pages-details"')
                idx_big6 = html.index('id="cinema-big6-card"')
                idx_drawer = html.index('id="studio-advanced-lab-drawer"')
                self.assertLess(idx_bar, idx_screen)
                self.assertLess(idx_screen, idx_nav)
                self.assertLess(idx_nav, idx_pages)
                self.assertLess(idx_pages, idx_128)
                self.assertLess(idx_128, idx_cats)
                self.assertLess(idx_cats, idx_big6)
                self.assertLess(idx_big6, idx_drawer)
            finally:
                srv.shutdown()
                srv.server_close()

    def test_p135_14_right_column_sticky_fx6_and_fx3_decks(self) -> None:
        html = run_fx6_menu_trial.HTML_UI
        idx_right = html.index('class="studio-right-col"')
        idx_drawer = html.index('id="studio-advanced-lab-drawer"')
        right_chunk = html[idx_right:idx_drawer]
        self.assertIn("FX6 机身按键面板", right_chunk)
        self.assertIn("ILME-FX3 物理机身控制面板", right_chunk)
        self.assertIn("sendKey('SET')", right_chunk)
        self.assertIn("sendFx3Button('FN')", right_chunk)
        self.assertIn(".studio-right-col {\n    position: sticky;", html)

    def test_p135_15_advanced_lab_drawer_collapsed_by_default(self) -> None:
        html = run_fx6_menu_trial.HTML_UI
        self.assertIn('<details id="studio-advanced-lab-drawer" class="lab-drawer">', html)
        self.assertNotIn('<details id="studio-advanced-lab-drawer" class="lab-drawer" open', html)
        self.assertNotIn('<details id="studio-advanced-lab-drawer" open', html)

    def test_p135_16_128_page_selector_folded_inside_details(self) -> None:
        html = run_fx6_menu_trial.HTML_UI
        self.assertIn('<details id="all128-pages-details" class="studio-sub-details">', html)
        self.assertNotIn('<details id="all128-pages-details" open', html)
        idx_det = html.index('id="all128-pages-details"')
        idx_sel = html.index('id="all128-select"')
        idx_end = html.index("</details>", idx_det)
        self.assertLess(idx_det, idx_sel)
        self.assertLess(idx_sel, idx_end)

    def test_p135_17_six_category_tabs_and_show_all_present(self) -> None:
        html = run_fx6_menu_trial.HTML_UI
        for tab in ("exposure", "focus", "monitor", "audio", "stream", "debug", "all"):
            self.assertIn(f'data-lab-tab="{tab}"', html)
        for panel in ("exposure", "focus", "monitor", "audio", "stream", "debug"):
            self.assertIn(f'id="lab-panel-{panel}"', html)

    def test_p135_18_all_12_cards_and_debug_widgets_grouped_in_correct_tabs(self) -> None:
        html = run_fx6_menu_trial.HTML_UI
        drawer = html[html.index('id="studio-advanced-lab-drawer"'):]
        panels = {
            "exposure": drawer[drawer.index('id="lab-panel-exposure"'):drawer.index('id="lab-panel-focus"')],
            "focus": drawer[drawer.index('id="lab-panel-focus"'):drawer.index('id="lab-panel-monitor"')],
            "monitor": drawer[drawer.index('id="lab-panel-monitor"'):drawer.index('id="lab-panel-audio"')],
            "audio": drawer[drawer.index('id="lab-panel-audio"'):drawer.index('id="lab-panel-stream"')],
            "stream": drawer[drawer.index('id="lab-panel-stream"'):drawer.index('id="lab-panel-debug"')],
            "debug": drawer[drawer.index('id="lab-panel-debug"'):],
        }
        for cid in ("phase64-cine-exposure-card", "phase73-color-media-card", "phase116-hlg-raw-breathing-card"):
            self.assertIn(f'id="{cid}"', panels["exposure"])
        for cid in ("phase81-touchaf-ciz-card", "phase95-gyroflow-anamorphic-card"):
            self.assertIn(f'id="{cid}"', panels["focus"])
        for cid in ("phase56-assist-scope-card", "phase102-cache-lut-ftp-card"):
            self.assertIn(f'id="{cid}"', panels["monitor"])
        for cid in ("phase40-audio-lut-camset-card", "phase88-shotmark-iris-card", "phase129-mxf-ptpv2-tally-card"):
            self.assertIn(f'id="{cid}"', panels["audio"])
        for cid in ("phase123-uvc-srt-crsdk-ptp-card", "phase109-mcfleet-sdi-c2pa-card"):
            self.assertIn(f'id="{cid}"', panels["stream"])
        for cid in ("stage-b-telemetry-strip", "multilang-diff-readout", "menu-search-jump-bar", "serial-box"):
            self.assertIn(f'id="{cid}"', panels["debug"])

    def test_p135_19_all_h3_headings_clean_no_phase_or_api(self) -> None:
        html = run_fx6_menu_trial.HTML_UI
        h3s = re.findall(r"<h3[^>]*>(.*?)</h3>", html, re.DOTALL)
        self.assertGreaterEqual(len(h3s), 15)
        for h in h3s:
            self.assertIsNone(re.search(r"Phase\s+\d+", h), msg=f"Unexpected Phase label in <h3>: {h}")
            self.assertNotIn("(/api/", h, msg=f"Unexpected (/api/...) suffix in <h3>: {h}")

    def test_p135_20_i18n_js_titles_clean_no_phase_prefix(self) -> None:
        html = run_fx6_menu_trial.HTML_UI
        for const_name in ("P95_I18N", "P102_I18N", "P109_I18N", "P116_I18N", "P123_I18N", "P129_I18N"):
            idx = html.index(f"const {const_name}")
            block = html[idx : idx + 3500]
            titles = re.findall(r"title:\s*'([^']*)'", block)
            self.assertEqual(len(titles), 4, msg=f"{const_name} should have 4 localized titles")
            for t in titles:
                self.assertIsNone(re.search(r"Phase\s+\d+", t), msg=f"Phase prefix left in {const_name}: {t}")

    def test_p135_21_top_studio_bar_controls_and_js_helpers(self) -> None:
        html = run_fx6_menu_trial.HTML_UI
        for marker in (
            'id="studio-lang-en"',
            'id="studio-lang-zh-CN"',
            'id="studio-lang-zh-TW"',
            'id="studio-lang-ja"',
            'id="pure-native-screen-toggle"',
            'id="reset-all-overlays-btn"',
            'id="studio-screen-mode-badge"',
            "function selectLabTab(",
            "function setStudioLanguage(",
            "function syncStudioScreenModeUI(",
            "function setStudioScreenMode(",
            "function togglePureNativeScreen(",
            "function clearAllStudioHuds(",
        ):
            self.assertIn(marker, html)

    def test_p135_22_zero_syntax_warnings_under_w_error(self) -> None:
        py_path = TRIAL_DIR / "run_fx6_menu_trial.py"
        src = py_path.read_text(encoding="utf-8")
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", SyntaxWarning)
            ast.parse(src, filename=str(py_path))
            compile(src, str(py_path), "exec")
        syntax_warns = [w for w in caught if issubclass(w.category, SyntaxWarning)]
        self.assertEqual(syntax_warns, [], msg=f"SyntaxWarnings found: {[str(w.message) for w in syntax_warns]}")

    def test_p135_23_guest_c_pure_native_bit30_and_overlay_suppression(self) -> None:
        c_src = (TRIAL_DIR / "src" / "fx6_live_guest.c").read_text(encoding="utf-8")
        self.assertIn("0x40000000u", c_src)
        self.assertIn("g_live_p40_flags & 0x40000000u", c_src)
        self.assertIn("!(g_live_p40_flags & 0x40000000u)", c_src)
        for magic in (
            "0x43494e45u",
            "0x57424c4du",
            "0x54414643u",
            "0x534d524bu",
            "0x4759524fu",
            "0x49434c46u",
            "0x4d43464cu",
            "0x484c4741u",
            "0x55564353u",
        ):
            self.assertIn(magic, c_src)

    def test_p135_24_guest_c_arm64_cross_compile_if_zig_present(self) -> None:
        if _force_clean_room():
            self.skipTest("clean-room mode skips local zig toolchain")
        import build_live700  # noqa: E402

        zig_path = build_live700.resolve_default_zig()
        if not zig_path.is_file():
            w = shutil.which("zig")
            if not w:
                self.skipTest("zig toolchain not present")
            zig_path = Path(w)
        c_path = TRIAL_DIR / "src" / "fx6_live_guest.c"
        with tempfile.TemporaryDirectory(prefix="fx6_p135_zig_") as td:
            out_so = Path(td) / "libfx6_live_guest_p135_test.so"
            env = os.environ.copy()
            env["ZIG_GLOBAL_CACHE_DIR"] = str(Path(td) / "zig-global")
            env["ZIG_LOCAL_CACHE_DIR"] = str(Path(td) / "zig-local")
            proc = subprocess.run(
                [str(zig_path), "cc", "-target", "aarch64-linux-gnu", "-shared", "-fPIC", "-O2", "-Wall", "-Wextra", str(c_path), "-o", str(out_so)],
                env=env,
                capture_output=True,
                text=True,
                timeout=60,
            )
            self.assertEqual(proc.returncode, 0, msg=f"zig cc failed:\n{proc.stderr}")
            self.assertTrue(out_so.exists() and out_so.stat().st_size > 0)

    def test_p135_25_start_vm_resets_studio_screen_mode_state(self) -> None:
        py_src = (TRIAL_DIR / "run_fx6_menu_trial.py").read_text(encoding="utf-8")
        idx_start = py_src.index("def start_vm(self)")
        idx_end = py_src.index("def stop_vm(self)", idx_start)
        start_chunk = py_src[idx_start:idx_end]
        self.assertIn("self.pure_native_screen = False", start_chunk)
        self.assertIn("self.studio_overlays_cleared = False", start_chunk)
        self.assertIn("self.studio_screen_mode_seq = 0", start_chunk)

    def test_p135_26_all_11_setters_clear_studio_overlays_cleared(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p135_26_") as td:
            sess = self._new_session(td)
            calls = [
                lambda: sess.set_assist_tools({"aspect_marker": "2.39:1"}),
                lambda: sess.set_cine_exposure({"ei_index": 1600}),
                lambda: sess.set_color_and_media({"wb_mode": "preset_3200k"}),
                lambda: sess.set_touch_focus_ciz({"touch_af_mode": "touch_focus"}),
                lambda: sess.set_shotmark_and_iris({"action": "add_shotmark1"}),
                lambda: sess.set_gyroflow_anamorphic({"squeeze_factor": 1.33}),
                lambda: sess.set_interval_cache_lut_ftp({"cache_seconds": 4}),
                lambda: sess.set_mc_fleet_sdi_c2pa({"fleet_cams_online": 2}),
                lambda: sess.set_hdr_hlg_raw_breathing({"hlg_profile": "HLG2"}),
                lambda: sess.set_uvc_srt_crsdk_ptp({"uvc_mode": "UVC_4K30P_MJPEG_5G"}),
                lambda: sess.set_mxf_ptpv2_tally({"tally_state": "PVW_GREEN"}),
            ]
            for fn in calls:
                sess.set_studio_screen_mode({"clear_all_overlays": True})
                self.assertTrue(sess.studio_overlays_cleared)
                fn()
                self.assertFalse(sess.studio_overlays_cleared)

    def test_p135_27_p4_nd_lock_and_p12_safe_preserved_across_studio_clear(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p135_27_") as td:
            sess = self._new_session(td)
            sess.set_cinema_param("nd", 1)
            camset = sess.export_camset_preset()
            camset["cinema_params"]["nd"] = "1/16 ND"
            sess.import_camset_preset(camset)
            att_before = sess.p4_lock_attempts
            rej_before = sess.p4_nd_reject_count
            self.assertGreater(att_before, 0)
            self.assertGreater(rej_before, 0)
            res = sess.set_studio_screen_mode({"pure_native_screen": True, "clear_all_overlays": True})
            self.assertTrue(res["ok"])
            self.assertEqual(sess.p4_lock_attempts, att_before)
            self.assertEqual(sess.p4_nd_reject_count, rej_before)
            self.assertEqual(sess.get_cinema_params()["values"]["nd"], "Clear [FX3 P4 Locked]")
            self.assertTrue(sess.p12_bk4_airplane_mode_locked)

    def test_p135_28_studio_screen_mode_does_not_touch_port_8768(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p135_28_") as td:
            sess, srv, _t, base = self._start_http_server(td)
            try:
                self.assertNotEqual(srv.server_address[1], 8768)
                self.assertEqual(sess.port, 18785)
                self.assertTrue(base.startswith("http://127.0.0.1:"))
            finally:
                srv.shutdown()
                srv.server_close()

    def test_p135_29_preserved_legacy_dom_ids_and_buttons(self) -> None:
        html = run_fx6_menu_trial.HTML_UI
        for dom_id in (
            "gpe0-img",
            "p81-canvas-reticle",
            "lang-toggle-btn",
            "lbtn-en",
            "lbtn-zh",
            "lbtn-ja",
            "btn-verify-multilang",
            "waveform-scope-panel",
            "scope-waveform-canvas",
            "scope-hist-canvas",
            "camset-json-box",
            "serial-box",
            "p129-details",
            "p129-summary-pill",
        ):
            self.assertIn(f'id="{dom_id}"', html)

    def test_p135_30_dual_mode_clean_room_safe(self) -> None:
        # Must work seamlessly in both normal and FX3_FX6_FORCE_CLEAN_ROOM=1 modes without QEMU
        _ = _force_clean_room()
        with tempfile.TemporaryDirectory(prefix="fx6_p135_30_") as td:
            sess = self._new_session(td)
            self.assertFalse(sess.is_running())
            res = sess.set_studio_screen_mode({"pure_native_screen": True, "clear_all_overlays": True})
            self.assertTrue(res["ok"])
            self.assertTrue(res["pure_native_screen"])
            self.assertEqual(res["studio_screen_mode"]["guest_bit30_pure_native"], 1)


if __name__ == "__main__":
    unittest.main()
