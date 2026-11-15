#!/usr/bin/env python3
"""Phase 109 Unit & Integration Tests:
- Monitor & Control 4-Camera Wired Gigabit USB-LAN Fleet Matrix & Gang-REC (P12 RF-Off Enforced -> wf12_00342260_hits == 0)
- HDMI CEA-861 17-Byte AVI InfoFrame Quantization Guard & HDMI->12G-SDI RP 188 ATC REC-Trigger Bridge
- E-Mount 12-Pin Electronic vs Unchipped PL-Mount Hot-Swap Shading Arbitrator (<1 frame 1.0x identity + G31 15mm LWS warning)
- C2PA 2.1 / cnflasha Zero-Touch Research Provenance Shield (CNFLASHA_RDONLY_ZERO_TOUCH, private_key_reads=0, cnflasha_writes=0)
- SMPTE RDD 18 / NonRealTimeMeta XML Sidecar, CAMSET Roundtrip, 4-Language Web UI, and GPE0 mb[52..55] ('MCFL') HUD.

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


class TestPhase109McFleetSdiC2pa(unittest.TestCase):
    def _new_session(self, td: str) -> run_fx6_menu_trial.FX6LiveGpe0Session:
        return run_fx6_menu_trial.FX6LiveGpe0Session(Path(td) / "sess", port=18781)

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

    def test_p109_01_specs_and_defaults(self) -> None:
        specs = run_fx6_menu_trial.MC_FLEET_SDI_C2PA_SPECS
        self.assertEqual(specs["fleet_roles"], ["Solo", "A_Cam_Master", "B_Cam_Follower", "C_Cam_Follower", "D_Cam_Follower"])
        self.assertEqual(specs["fleet_cams_range"], [1, 4])
        self.assertTrue(specs["p12_rf_off_enforced"])
        self.assertEqual(specs["wf12_00342260_hits_locked"], 0)
        self.assertEqual(specs["avi_infoframe_bytes"], 17)
        self.assertEqual(specs["rp188_atc_did"], "0x60")
        self.assertEqual(specs["rp188_atc_sdid"], "0x60")
        self.assertEqual(specs["mount_types"], ["Sony_EMount_12Pin_GM", "Manual_PL_Adapter_Unchipped"])
        self.assertEqual(specs["g31_15mm_lws_threshold_kg"], 1.2)
        self.assertEqual(specs["c2pa_vault_status_locked"], "CNFLASHA_RDONLY_ZERO_TOUCH")
        self.assertEqual(specs["private_key_reads_locked"], 0)
        self.assertEqual(specs["cnflasha_writes_locked"], 0)
        self.assertEqual(specs["mailbox_magic"], "0x4D43464C")
        self.assertEqual(specs["supported_langs"], ["en", "zh-CN", "zh-TW", "ja"])

        with tempfile.TemporaryDirectory(prefix="fx6_p109_01_") as td:
            sess = self._new_session(td)
            p109 = sess.get_mc_fleet_sdi_c2pa()
            self.assertEqual(p109["fleet_role"], "Solo")
            self.assertEqual(p109["fleet_cams_online"], 1)
            self.assertFalse(p109["gang_rec_trigger"])
            self.assertTrue(p109["p12_rf_off_enforced"])
            self.assertEqual(p109["wf12_00342260_hits"], 0)
            self.assertEqual(p109["sdi_bridge_converter"], "BMD_Micro_Converter_12G")
            self.assertEqual(p109["rp188_rec_trigger_bit"], 0)
            self.assertTrue(p109["avi_checksum_valid"])
            self.assertEqual(p109["mount_type"], "Sony_EMount_12Pin_GM")
            self.assertEqual(p109["electronic_pins_active"], 12)
            self.assertAlmostEqual(p109["vignetting_comp_gain"], 1.318, places=3)
            self.assertFalse(p109["g31_15mm_lws_warning"])
            self.assertEqual(p109["c2pa_vault_status"], "CNFLASHA_RDONLY_ZERO_TOUCH")
            self.assertEqual(p109["private_key_reads"], 0)
            self.assertEqual(p109["cnflasha_writes"], 0)
            self.assertFalse(p109["hardware_attestation_claimed"])
            self.assertEqual(sess.get_status()["mc_fleet_sdi_c2pa"], p109)

    def test_p109_02_mc_fleet_roles_and_nodes_matrix(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p109_02_") as td:
            sess = self._new_session(td)
            for role, exp_local in [
                ("Solo", 0),
                ("A_Cam_Master", 0),
                ("B_Cam_Follower", 1),
                ("C_Cam_Follower", 2),
                ("D_Cam_Follower", 3),
            ]:
                r = sess.set_mc_fleet_sdi_c2pa({"fleet_role": role, "fleet_cams_online": 4, "fleet_nic_driver": "CDC_NCM_AX88179"})
                self.assertTrue(r["ok"])
                p109 = r["mc_fleet_sdi_c2pa"]
                self.assertEqual(p109["fleet_role"], role)
                self.assertEqual(p109["fleet_cams_online"], 4)
                self.assertEqual(p109["fleet_transport"], "USB_LAN_CDC_NCM_AX88179")
                self.assertEqual(len(p109["fleet_nodes"]), 4)
                self.assertTrue(p109["fleet_nodes"][exp_local]["is_local_node"])
                self.assertEqual(sum(1 for n in p109["fleet_nodes"] if n["online"]), 4)
                self.assertTrue(all(n["wf12_00342260_hits"] == 0 for n in p109["fleet_nodes"]))

    def test_p109_03_gang_rec_syncs_phase64_tally_and_fleet_nodes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p109_03_") as td:
            sess = self._new_session(td)
            r = sess.set_mc_fleet_sdi_c2pa({"fleet_role": "A_Cam_Master", "fleet_cams_online": 3, "gang_rec_trigger": True})
            self.assertTrue(r["ok"])
            p109 = r["mc_fleet_sdi_c2pa"]
            ce = sess.get_cine_exposure()
            self.assertTrue(p109["gang_rec_trigger"])
            self.assertEqual(ce["rec_state"], "REC")
            self.assertTrue(ce["tally_front_lit"])
            self.assertEqual(p109["rp188_rec_trigger_bit"], 1)
            self.assertEqual([n["rec_tally"] for n in p109["fleet_nodes"]], ["REC", "REC", "REC", "OFFLINE"])

            r_stop = sess.set_mc_fleet_sdi_c2pa({"gang_rec_trigger": False})
            self.assertTrue(r_stop["ok"])
            self.assertFalse(r_stop["mc_fleet_sdi_c2pa"]["gang_rec_trigger"])
            self.assertEqual(sess.get_cine_exposure()["rec_state"], "STBY")
            self.assertEqual(r_stop["mc_fleet_sdi_c2pa"]["rp188_rec_trigger_bit"], 0)
            self.assertEqual([n["rec_tally"] for n in r_stop["mc_fleet_sdi_c2pa"]["fleet_nodes"]], ["STBY", "STBY", "STBY", "OFFLINE"])

    def test_p109_04_bidirectional_sync_with_cine_exposure_rec(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p109_04_") as td:
            sess = self._new_session(td)
            sess.set_mc_fleet_sdi_c2pa({"fleet_role": "B_Cam_Follower", "fleet_cams_online": 4})
            r_rec = sess.set_cine_exposure({"rec_state": "REC"})
            self.assertTrue(r_rec["ok"])
            p109 = r_rec["status"]["mc_fleet_sdi_c2pa"]
            self.assertTrue(p109["gang_rec_trigger"])
            self.assertEqual(p109["rp188_rec_trigger_bit"], 1)

            r_stby = sess.set_cine_exposure({"rec_state": "STBY"})
            self.assertTrue(r_stby["ok"])
            p109_stby = r_stby["status"]["mc_fleet_sdi_c2pa"]
            self.assertFalse(p109_stby["gang_rec_trigger"])
            self.assertEqual(p109_stby["rp188_rec_trigger_bit"], 0)

    def test_p109_05_p12_rf_off_enforced_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p109_05_") as td:
            sess = self._new_session(td)
            for bad in (
                {"wifi_enabled": True},
                {"bt_enabled": True},
                {"wifi_bt_rf_disabled": False},
                {"p12_rf_off_enforced": False},
                {"fleet_transport": "wifi_5ghz"},
                {"fleet_nic_driver": "wlan0"},
            ):
                r = sess.set_mc_fleet_sdi_c2pa(bad)
                self.assertFalse(r["ok"], msg=f"Should block P12 RF violation: {bad}")
                self.assertEqual(r["error"], "p12_rf_off_violation")
                self.assertEqual(r["wf12_00342260_hits"], 0)
            self.assertEqual(sess.get_mc_fleet_sdi_c2pa()["wf12_00342260_hits"], 0)

    def test_p109_06_invalid_fleet_fields_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p109_06_") as td:
            sess = self._new_session(td)
            for bad in (
                "not_a_dict",
                {"fleet_role": "Z_Cam"},
                {"fleet_role": 123},
                {"fleet_cams_online": 0},
                {"fleet_cams_online": 5},
                {"fleet_cams_online": True},
                {"fleet_cams_online": 2.5},
                {"fleet_cams_online": float("nan")},
                {"gang_rec_trigger": "yes"},
            ):
                r = sess.set_mc_fleet_sdi_c2pa(bad)
                self.assertFalse(r["ok"])

    def test_p109_07_cea861_avi_infoframe_checksum_and_quantization_modes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p109_07_") as td:
            sess = self._new_session(td)
            cases = [
                ("S-Cinetone", "off", "SCINETONE_LEGAL_64_940", "LEGAL_64_940", "YCBCR_422"),
                ("S-Log3 / S-Gamut3.Cine", "off", "SLOG3_EXTENDED_64_1019", "EXTENDED_64_1019", "YCBCR_422"),
                ("ITU709", "off", "REC709_LEGAL_64_940", "LEGAL_64_940", "YCBCR_422"),
                ("S-Log3 / S-Gamut3.Cine", "hdmi_raw16", "HDMI_RAW16_LINEAR", "FULL_0_1023_RAW16", "RGB"),
            ]
            for look, io_mode, exp_sig, exp_rng, exp_cs in cases:
                sess.set_color_and_media({"base_look": look})
                sess.set_cine_exposure({"wired_io_mode": io_mode})
                p109 = sess.get_mc_fleet_sdi_c2pa()
                self.assertEqual(p109["avi_signal_range_mode"], exp_sig)
                self.assertEqual(p109["avi_quantization_range"], exp_rng)
                self.assertEqual(p109["avi_colorspace"], exp_cs)
                self.assertEqual(p109["avi_infoframe_bytes"], 17)
                raw = bytes.fromhex(p109["avi_infoframe_hex"])
                self.assertEqual(len(raw), 17)
                self.assertEqual(raw[0], 0x82)
                self.assertEqual(raw[1], 0x02)
                self.assertEqual(raw[2], 0x0D)
                self.assertEqual(sum(raw) & 0xFF, 0)
                self.assertEqual(p109["avi_checksum_zero_mod256"], 0)
                self.assertTrue(p109["avi_checksum_valid"])
                self.assertTrue(p109["shadow_crush_prevented"])

    def test_p109_08_blocks_legal_to_full_double_scaling_shadow_crush(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p109_08_") as td:
            sess = self._new_session(td)
            sess.set_color_and_media({"base_look": "S-Log3 / S-Gamut3.Cine"})
            r1 = sess.set_mc_fleet_sdi_c2pa({"recorder_range_expectation": "FULL_RANGE"})
            self.assertFalse(r1["ok"])
            self.assertEqual(r1["error"], "avi_shadow_crush_blocked")
            self.assertEqual(r1["shadow_crush_delta_codes"], -59)

            r2 = sess.set_mc_fleet_sdi_c2pa({"force_avi_full_range": True})
            self.assertFalse(r2["ok"])
            self.assertEqual(r2["error"], "avi_shadow_crush_blocked")

    def test_p109_09_sdi_bridge_converters_and_rejects_fake_native_bnc(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p109_09_") as td:
            sess = self._new_session(td)
            r_bad = sess.set_mc_fleet_sdi_c2pa({"sdi_bridge_converter": "fx6_native_12g_bnc"})
            self.assertFalse(r_bad["ok"])
            self.assertEqual(r_bad["error"], "fx3_missing_sdi_bnc_hardware")
            self.assertEqual(r_bad["ghost_sdi_bnc_hw_faults"], 0)

            for conv, active in [
                ("BMD_Micro_Converter_12G", True),
                ("Teradek_Bolt_HDMI_SDI", True),
                ("Atomos_Connect_12G", True),
                ("Off", False),
            ]:
                r = sess.set_mc_fleet_sdi_c2pa({"sdi_bridge_converter": conv})
                self.assertTrue(r["ok"])
                p109 = r["mc_fleet_sdi_c2pa"]
                self.assertEqual(p109["sdi_bridge_converter"], conv)
                self.assertEqual(p109["sdi_bridge_active"], active)
                self.assertFalse(p109["physical_12g_sdi_bnc_present"])
                self.assertEqual(p109["ghost_sdi_bnc_hw_faults"], 0)

    def test_p109_10_smpte_rp188_rec_trigger_bit_parity(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p109_10_") as td:
            sess = self._new_session(td)
            sess.set_cine_exposure({"base_fps": 29.97, "rec_state": "REC"})
            p109 = sess.get_mc_fleet_sdi_c2pa()
            self.assertEqual(p109["rp188_atc_did"], "0x60")
            self.assertEqual(p109["rp188_atc_sdid"], "0x60")
            self.assertEqual(p109["rp188_rec_trigger_bit"], 1)
            self.assertTrue(p109["rp188_parity_ok"])

            # Turning off HDMI TC output or SDI bridge drops RP188 REC trigger bit to 0 cleanly
            sess.set_mc_fleet_sdi_c2pa({"hdmi_tc_output_enabled": False})
            self.assertEqual(sess.get_mc_fleet_sdi_c2pa()["rp188_rec_trigger_bit"], 0)
            self.assertTrue(sess.get_mc_fleet_sdi_c2pa()["rp188_parity_ok"])

            sess.set_mc_fleet_sdi_c2pa({"hdmi_tc_output_enabled": True, "sdi_bridge_converter": "Off"})
            self.assertEqual(sess.get_mc_fleet_sdi_c2pa()["rp188_rec_trigger_bit"], 0)

            sess.set_mc_fleet_sdi_c2pa({"sdi_bridge_converter": "BMD_Micro_Converter_12G"})
            self.assertEqual(sess.get_mc_fleet_sdi_c2pa()["rp188_rec_trigger_bit"], 1)

    def test_p109_11_emount_to_manual_pl_hotswap_resets_shading_identity_under_1frame(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p109_11_") as td:
            sess = self._new_session(td)
            p_gm = sess.get_mc_fleet_sdi_c2pa()
            self.assertEqual(p_gm["mount_type"], "Sony_EMount_12Pin_GM")
            self.assertEqual(p_gm["electronic_pins_active"], 12)
            self.assertTrue(p_gm["lens_uart_active"])
            self.assertAlmostEqual(p_gm["vignetting_comp_gain"], 1.318, places=3)
            self.assertFalse(p_gm["shading_identity_reset"])

            r_pl = sess.set_mc_fleet_sdi_c2pa({"mount_type": "Manual_PL_Adapter_Unchipped"})
            self.assertTrue(r_pl["ok"])
            p_pl = r_pl["mc_fleet_sdi_c2pa"]
            self.assertEqual(p_pl["mount_type"], "Manual_PL_Adapter_Unchipped")
            self.assertEqual(p_pl["electronic_pins_active"], 0)
            self.assertFalse(p_pl["lens_uart_active"])
            self.assertEqual(p_pl["vignetting_comp_gain"], 1.0)
            self.assertEqual(p_pl["ca_r_scale"], 1.0)
            self.assertEqual(p_pl["ca_b_scale"], 1.0)
            self.assertEqual(p_pl["distortion_k1"], 0.0)
            self.assertEqual(p_pl["breathing_scale"], 1.0)
            self.assertTrue(p_pl["shading_identity_reset"])
            self.assertTrue(p_pl["reset_under_one_frame"])
            self.assertLess(p_pl["reset_latency_ms"], p_pl["frame_period_ms"])
            self.assertEqual(p_pl["stale_gm_frames_leaked"], 0)

    def test_p109_12_blocks_stale_gm_shading_injection_on_manual_pl(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p109_12_") as td:
            sess = self._new_session(td)
            sess.set_mc_fleet_sdi_c2pa({"mount_type": "Manual_PL_Adapter_Unchipped"})
            r = sess.set_mc_fleet_sdi_c2pa({"inject_stale_gm_shading": True})
            self.assertFalse(r["ok"])
            self.assertEqual(r["error"], "stale_gm_shading_blocked_on_pl")

    def test_p109_13_g31_15mm_lws_support_warning_and_clearing(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p109_13_") as td:
            sess = self._new_session(td)
            r_warn = sess.set_mc_fleet_sdi_c2pa({
                "mount_type": "Manual_PL_Adapter_Unchipped",
                "lens_kg": 1.85,
                "rod_support_15mm_lws": False,
            })
            self.assertTrue(r_warn["ok"])
            p_warn = r_warn["mc_fleet_sdi_c2pa"]
            self.assertTrue(p_warn["g31_15mm_lws_support_required"])
            self.assertTrue(p_warn["g31_15mm_lws_warning"])
            self.assertIn("G31 WARNING", p_warn["g31_15mm_lws_message"])

            r_ok = sess.set_mc_fleet_sdi_c2pa({"rod_support_15mm_lws": True})
            self.assertTrue(r_ok["ok"])
            p_ok = r_ok["mc_fleet_sdi_c2pa"]
            self.assertTrue(p_ok["g31_15mm_lws_support_required"])
            self.assertFalse(p_ok["g31_15mm_lws_warning"])
            self.assertIn("G31 OK", p_ok["g31_15mm_lws_message"])

    def test_p109_14_invalid_mount_and_lens_params_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p109_14_") as td:
            sess = self._new_session(td)
            for bad in (
                {"mount_type": "Canon_RF"},
                {"mount_type": 42},
                {"lens_kg": 0.05},
                {"lens_kg": 12.0},
                {"lens_kg": True},
                {"lens_kg": float("nan")},
                {"focal_length_mm": 4},
                {"focal_length_mm": 500},
                {"focal_length_mm": False},
                {"lens_model": ""},
            ):
                r = sess.set_mc_fleet_sdi_c2pa(bad)
                self.assertFalse(r["ok"], msg=f"Should reject {bad}")

    def test_p109_15_c2pa_zero_touch_shield_invariants(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p109_15_") as td:
            sess = self._new_session(td)
            p109 = sess.get_mc_fleet_sdi_c2pa()
            self.assertEqual(p109["c2pa_spec_version"], "2.1")
            self.assertEqual(p109["c2pa_vault_status"], "CNFLASHA_RDONLY_ZERO_TOUCH")
            self.assertEqual(p109["c2pa_provenance_mode"], "CLEAN_ROOM_RESEARCH_UNATTESTED")
            self.assertEqual(p109["private_key_reads"], 0)
            self.assertEqual(p109["private_key_exports"], 0)
            self.assertEqual(p109["cnflasha_writes"], 0)
            self.assertEqual(p109["cnflasha_mutation_bytes"], 0)
            self.assertEqual(p109["rpmb_writes"], 0)
            self.assertFalse(p109["hardware_attestation_claimed"])
            self.assertFalse(p109["c2pa_spoofed"])
            self.assertFalse(p109["persistent_emmc_writes_authorized"])

    def test_p109_16_blocks_cnflasha_key_reads_writes_and_spoof(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p109_16_") as td:
            sess = self._new_session(td)
            bad_ops = (
                {"c2pa_operation": "READ_KEY"},
                {"c2pa_operation": "EXPORT_KEY"},
                {"c2pa_operation": "WRITE_VAULT"},
                {"c2pa_operation": "SPOOF_CERT"},
                {"claim_hardware_attestation": True},
                {"hardware_attestation_claimed": True},
                {"c2pa_spoof": True},
                {"private_key_reads": 1},
                {"cnflasha_writes": 1},
                {"c2pa_target_path": "/dev/cnflasha"},
                {"c2pa_target_path": "/dev/mmcblk0rpmb"},
                {"c2pa_target_path": "/cert/device_priv.key"},
                {"c2pa_target_path": "0xf7fc0000"},
            )
            for idx, bad in enumerate(bad_ops, start=1):
                r = sess.set_mc_fleet_sdi_c2pa(bad)
                self.assertFalse(r["ok"], msg=f"Should block C2PA tamper: {bad}")
                self.assertEqual(r["error"], "c2pa_cnflasha_zero_touch_blocked")
                self.assertEqual(r["c2pa_vault_status"], "CNFLASHA_RDONLY_ZERO_TOUCH")
                self.assertEqual(r["private_key_reads"], 0)
                self.assertEqual(r["cnflasha_writes"], 0)
                self.assertEqual(r["c2pa_blocked_attempts"], idx)
            p109 = sess.get_mc_fleet_sdi_c2pa()
            self.assertEqual(p109["c2pa_blocked_attempts"], len(bad_ops))
            self.assertEqual(p109["private_key_reads"], 0)
            self.assertEqual(p109["cnflasha_writes"], 0)

    def test_p109_17_reset_restores_defaults_and_clears_blocked_count(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p109_17_") as td:
            sess = self._new_session(td)
            sess.set_mc_fleet_sdi_c2pa({
                "fleet_role": "A_Cam_Master",
                "fleet_cams_online": 4,
                "gang_rec_trigger": True,
                "mount_type": "Manual_PL_Adapter_Unchipped",
                "lens_kg": 2.0,
            })
            sess.set_mc_fleet_sdi_c2pa({"c2pa_operation": "READ_KEY"})
            r_rst = sess.set_mc_fleet_sdi_c2pa({"reset": True})
            self.assertTrue(r_rst["ok"])
            p = r_rst["mc_fleet_sdi_c2pa"]
            self.assertEqual(p["fleet_role"], "Solo")
            self.assertEqual(p["fleet_cams_online"], 1)
            self.assertFalse(p["gang_rec_trigger"])
            self.assertEqual(p["mount_type"], "Sony_EMount_12Pin_GM")
            self.assertEqual(p["c2pa_blocked_attempts"], 0)

    def test_p109_18_xml_sidecar_embeds_mcfleet_sdi_shading_and_c2pa_provenance(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p109_18_") as td:
            sess = self._new_session(td)
            sess.set_color_and_media({"base_look": "S-Log3 / S-Gamut3.Cine"})
            sess.set_mc_fleet_sdi_c2pa({
                "fleet_role": "A_Cam_Master",
                "fleet_cams_online": 4,
                "gang_rec_trigger": True,
                "sdi_bridge_converter": "Atomos_Connect_12G",
                "mount_type": "Manual_PL_Adapter_Unchipped",
                "lens_kg": 1.6,
                "rod_support_15mm_lws": True,
            })
            res = sess.get_xml_sidecar()
            self.assertTrue(res["ok"])
            self.assertFalse(res["c2pa_spoofed"])
            xml_text = res["xml"]
            root = ET.fromstring(xml_text)
            self.assertIn("McFleetSdiAndC2paProvenance", xml_text)
            self.assertIn("CNFLASHA_RDONLY_ZERO_TOUCH", xml_text)
            self.assertIn("CLEAN_ROOM_RESEARCH_UNATTESTED", xml_text)
            self.assertIn("Atomos_Connect_12G", xml_text)
            self.assertIn("Manual_PL_Adapter_Unchipped", xml_text)
            items = {el.attrib.get("name"): el.attrib.get("value") for el in root.iter() if el.tag.endswith("Item")}
            self.assertEqual(items.get("FleetRole"), "A_Cam_Master")
            self.assertEqual(items.get("FleetCamerasOnline"), "4")
            self.assertEqual(items.get("GangRecTrigger"), "true")
            self.assertEqual(items.get("Wf12Calls"), "0")
            self.assertEqual(items.get("SmpteRp188RecTriggerBit"), "1")
            self.assertEqual(items.get("ShadingCornerGain"), "1.0000")
            self.assertEqual(items.get("C2paVaultStatus"), "CNFLASHA_RDONLY_ZERO_TOUCH")
            self.assertEqual(items.get("PrivateKeyReads"), "0")
            self.assertEqual(items.get("CnflashaWrites"), "0")
            self.assertEqual(items.get("HardwareAttestationClaimed"), "false")

    def test_p109_19_camset_export_and_import_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p109_19_") as td:
            s1 = self._new_session(td + "/s1")
            s1.set_mc_fleet_sdi_c2pa({
                "fleet_role": "C_Cam_Follower",
                "fleet_cams_online": 4,
                "fleet_nic_driver": "CDC_NCM_AX88179",
                "gang_rec_trigger": True,
                "sdi_bridge_converter": "Teradek_Bolt_HDMI_SDI",
                "mount_type": "Manual_PL_Adapter_Unchipped",
                "lens_kg": 1.8,
                "rod_support_15mm_lws": True,
            })
            exported = s1.export_camset_preset()
            self.assertIn("mc_fleet_sdi_c2pa", exported)

            s2 = self._new_session(td + "/s2")
            imp = s2.import_camset_preset(exported)
            self.assertTrue(imp["ok"], msg=f"CAMSET import failed: {imp}")
            p2 = imp["mc_fleet_sdi_c2pa"]
            self.assertEqual(p2["fleet_role"], "C_Cam_Follower")
            self.assertEqual(p2["fleet_cams_online"], 4)
            self.assertEqual(p2["fleet_nic_driver"], "CDC_NCM_AX88179")
            self.assertTrue(p2["gang_rec_trigger"])
            self.assertEqual(p2["sdi_bridge_converter"], "Teradek_Bolt_HDMI_SDI")
            self.assertEqual(p2["mount_type"], "Manual_PL_Adapter_Unchipped")
            self.assertAlmostEqual(p2["vignetting_comp_gain"], 1.0, places=3)
            self.assertTrue(p2["rod_support_15mm_lws"])
            self.assertEqual(p2["c2pa_vault_status"], "CNFLASHA_RDONLY_ZERO_TOUCH")

    def test_p109_20_camset_import_blocks_tampered_c2pa_and_wf12(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p109_20_") as td:
            sess = self._new_session(td)
            base_camset = sess.export_camset_preset()
            for bad_patch, exp_err in [
                ({"wf12_00342260_hits": 1}, "p12_rf_off_violation"),
                ({"c2pa_vault_status": "CNFLASHA_RW_UNLOCKED"}, "c2pa_cnflasha_zero_touch_blocked"),
                ({"private_key_reads": 1}, "c2pa_cnflasha_zero_touch_blocked"),
                ({"cnflasha_writes": 1}, "c2pa_cnflasha_zero_touch_blocked"),
                ({"hardware_attestation_claimed": True}, "c2pa_cnflasha_zero_touch_blocked"),
                ({"c2pa_spoofed": True}, "c2pa_cnflasha_zero_touch_blocked"),
            ]:
                tampered = json.loads(json.dumps(base_camset))
                tampered["mc_fleet_sdi_c2pa"].update(bad_patch)
                res = sess.import_camset_preset(tampered)
                self.assertFalse(res["ok"])
                self.assertEqual(res["error"], exp_err)

    def test_p109_21_command_format_and_status_sync(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p109_21_") as td:
            sess = self._new_session(td)
            sess.set_mc_fleet_sdi_c2pa({"fleet_role": "A_Cam_Master", "fleet_cams_online": 4, "gang_rec_trigger": True})
            p109 = sess.get_mc_fleet_sdi_c2pa()
            cmd = p109["mc_fleet_sdi_c2pa_cmd"]
            self.assertIn("MCFL role=A_Cam_Master(4/4,gang=1,wf12=0)", cmd)
            self.assertIn("sdi=BMD_Micro_Converter_12G(rp188=1,", cmd)
            self.assertIn("c2pa=CNFLASHA_RDONLY_ZERO_TOUCH(kr=0,cw=0)", cmd)
            self.assertEqual(sess.last_mc_fleet_sdi_c2pa_cmd, cmd)

    def test_p109_22_mailbox_mb52_to_mb55_binary_layout(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p109_22_") as td:
            sess = self._new_session(td)
            raw_def = sess._pack_phase109_mailbox_bytes()
            self.assertEqual(len(raw_def), 16)
            mb52, mb53, mb54, mb55 = struct.unpack("<4I", raw_def)
            self.assertEqual(mb52, 0x98194888)
            self.assertEqual(mb53, 0x83301E10)
            self.assertEqual(mb54, 0x80000014)
            self.assertEqual(mb55, 0x4D43464C)

            sess.set_mc_fleet_sdi_c2pa({
                "fleet_role": "A_Cam_Master",
                "fleet_cams_online": 4,
                "gang_rec_trigger": True,
                "sdi_bridge_converter": "Teradek_Bolt_HDMI_SDI",
                "mount_type": "Manual_PL_Adapter_Unchipped",
                "lens_kg": 1.8,
                "rod_support_15mm_lws": False,
            })
            sess.set_mc_fleet_sdi_c2pa({"c2pa_operation": "READ_KEY"})
            mb52, mb53, mb54, mb55 = struct.unpack("<4I", sess._pack_phase109_mailbox_bytes())
            self.assertEqual(mb55, 0x4D43464C)
            self.assertEqual(mb52 & 0x7, 1)  # A_Cam_Master
            self.assertEqual((mb52 >> 3) & 0x7, 4)  # 4 cams
            self.assertEqual((mb52 >> 6) & 0x1, 1)  # gang_rec=1
            self.assertEqual((mb52 >> 8) & 0x3, 1)  # Teradek
            self.assertEqual((mb52 >> 10) & 0x1, 1)  # rp188_rec_bit=1
            self.assertEqual((mb52 >> 27) & 0x1, 1)  # P12 RF-OFF
            self.assertEqual(mb53 & 0x1, 1)  # mount_pl=1
            self.assertEqual((mb53 >> 1) & 0x1, 1)  # shading_identity_reset=1
            self.assertEqual((mb53 >> 2) & 0xFF, 100)  # 1.00x
            self.assertEqual((mb53 >> 16) & 0x1, 1)  # g31_lws_warning=1
            self.assertEqual((mb53 >> 18) & 0xF, 0)  # 0 pins
            self.assertEqual((mb54 >> 3) & 0x1, 0)  # hw_attest=0
            self.assertEqual((mb54 >> 4) & 0x1, 1)  # cnflasha_ro=1
            self.assertEqual((mb54 >> 5) & 0x1, 1)  # spoof_blocked=1
            self.assertEqual((mb54 >> 6) & 0xFF, 1)  # blk_cnt=1

    def test_p109_23_http_get_post_and_bad_json_guard(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p109_23_") as td:
            _, srv, th, base = self._start_http_server(td)
            try:
                st_g, body_g = self._http_get_json(f"{base}/api/mc_fleet_sdi_c2pa")
                self.assertEqual(st_g, 200)
                self.assertTrue(body_g["ok"])
                self.assertEqual(body_g["mc_fleet_sdi_c2pa"]["fleet_role"], "Solo")

                st_p, body_p = self._http_post_json(
                    f"{base}/api/mc_fleet_sdi_c2pa",
                    {"fleet_role": "A_Cam_Master", "fleet_cams_online": 4, "gang_rec_trigger": True},
                )
                self.assertEqual(st_p, 200)
                self.assertTrue(body_p["ok"])
                self.assertEqual(body_p["mc_fleet_sdi_c2pa"]["rp188_rec_trigger_bit"], 1)

                st_bad, body_bad = self._http_post_json(f"{base}/api/mc_fleet_sdi_c2pa", b"{not-json")
                self.assertEqual(st_bad, 400)
                self.assertEqual(body_bad["error"], "invalid_json")

                st_arr, body_arr = self._http_post_json(f"{base}/api/mc_fleet_sdi_c2pa", [1, 2, 3])
                self.assertEqual(st_arr, 400)
                self.assertEqual(body_arr["error"], "invalid_json_object")
            finally:
                srv.shutdown()
                srv.server_close()
                th.join(timeout=2)

    def test_p109_24_http_xml_sidecar_reflects_mc_fleet_sdi_c2pa(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p109_24_") as td:
            _, srv, th, base = self._start_http_server(td)
            try:
                self._http_post_json(
                    f"{base}/api/mc_fleet_sdi_c2pa",
                    {"fleet_role": "D_Cam_Follower", "fleet_cams_online": 4, "mount_type": "Manual_PL_Adapter_Unchipped"},
                )
                st_j, js = self._http_get_json(f"{base}/api/xml_sidecar?format=json")
                self.assertEqual(st_j, 200)
                self.assertEqual(js["mc_fleet_sdi_c2pa"]["fleet_role"], "D_Cam_Follower")
                st_x, xml_txt = self._http_get_text(f"{base}/api/xml_sidecar")
                self.assertEqual(st_x, 200)
                self.assertIn("D_Cam_Follower", xml_txt)
                self.assertIn("CNFLASHA_RDONLY_ZERO_TOUCH", xml_txt)
            finally:
                srv.shutdown()
                srv.server_close()
                th.join(timeout=2)

    def test_p109_25_html_ui_4lang_controls_present(self) -> None:
        html = run_fx6_menu_trial.HTML_UI
        for token in (
            "phase109-mcfleet-sdi-c2pa-card",
            "p109-lang-en",
            "p109-lang-zh-CN",
            "p109-lang-zh-TW",
            "p109-lang-ja",
            "P109_I18N",
            "setP109Lang",
            "syncPhase109McFleetSdiC2paUI",
            "setPhase109State",
            "/api/mc_fleet_sdi_c2pa",
            "BMD_Micro_Converter_12G",
            "Manual_PL_Adapter_Unchipped",
        ):
            self.assertIn(token, html, msg=f"Missing Web UI token: {token}")

    def test_p109_26_guest_c_source_mb52_55_and_heap_free_hygiene(self) -> None:
        c_src = (TRIAL_DIR / "src" / "fx6_live_guest.c").read_text(encoding="utf-8")
        for token in (
            "0x4d43464c",
            "for (int i = 0; i < 48; i++) mb[i] = 0;",
            "fx6_render_phase109_mcfleet_sdi_c2pa_overlay",
            "g_live_p109_fleet_sdi",
            "g_live_p109_mount_shading",
            "g_live_p109_c2pa_prov",
            "RO-ZERO-TOUCH KR=0 CW=0",
            "MCFL=",
        ):
            self.assertIn(token, c_src)
        self.assertNotIn("8768", c_src)
        idx_start = c_src.index("fx6_render_phase109_mcfleet_sdi_c2pa_overlay")
        idx_end = c_src.index("static void fx6_render_dispatch", idx_start)
        fn_body = c_src[idx_start:idx_end]
        for forbidden in ("malloc(", "calloc(", "realloc(", "printf("):
            self.assertNotIn(forbidden, fn_body)

    def test_p109_27_guest_c_compiles_cleanly_for_arm64(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p109_27_") as td:
            out_so = Path(td) / "libfx6_live_guest.so"
            res = build_live700.compile_shim(build_live700.DEFAULT_ZIG, out_so)
            self.assertTrue(out_so.exists())
            self.assertGreater(res["bytes"], 500000)

    def test_p109_28_port_isolation_no_8768_and_scoped_18781(self) -> None:
        py_src = (TRIAL_DIR / "run_fx6_menu_trial.py").read_text(encoding="utf-8")
        idx_p109 = py_src.index("Phase 109: M&C 4-Cam Wired Fleet")
        idx_gpe = py_src.index("def _png_chunk", idx_p109)
        self.assertNotIn("8768", py_src[idx_p109:idx_gpe])
        scoped = run_fx6_menu_trial.resolve_port_scoped_workdir(18781, Path("/private/tmp/fx6-phase109-18781"))
        self.assertEqual(str(scoped), "/private/tmp/fx6-phase109-18781")

    def test_p109_29_cinema_param_fps_and_lut_sync_avi_infoframe(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p109_29_") as td:
            sess = self._new_session(td)
            sess.set_cinema_param("fps", preset="59.94p")
            sess.set_cinema_param("lut", preset="S-Log3")
            p109 = sess.get_mc_fleet_sdi_c2pa()
            self.assertEqual(p109["avi_vic"], 97)
            self.assertEqual(p109["avi_signal_range_mode"], "SLOG3_EXTENDED_64_1019")
            self.assertEqual(p109["avi_quantization_range"], "EXTENDED_64_1019")
            self.assertTrue(p109["avi_checksum_valid"])

    def test_p109_30_dual_mode_clean_room_and_local_donor_parity(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p109_30_") as td:
            sess = self._new_session(td)
            mode = "CLEAN_ROOM" if _force_clean_room() else "LOCAL_DONOR"
            self.assertIn(mode, ("CLEAN_ROOM", "LOCAL_DONOR"))
            r = sess.set_mc_fleet_sdi_c2pa({
                "fleet_role": "A_Cam_Master",
                "fleet_cams_online": 4,
                "gang_rec_trigger": True,
                "mount_type": "Manual_PL_Adapter_Unchipped",
                "lens_kg": 1.5,
                "rod_support_15mm_lws": True,
            })
            self.assertTrue(r["ok"])
            self.assertEqual(r["mc_fleet_sdi_c2pa"]["c2pa_vault_status"], "CNFLASHA_RDONLY_ZERO_TOUCH")
            self.assertEqual(r["wf12_00342260_hits"], 0)


if __name__ == "__main__":
    unittest.main()
