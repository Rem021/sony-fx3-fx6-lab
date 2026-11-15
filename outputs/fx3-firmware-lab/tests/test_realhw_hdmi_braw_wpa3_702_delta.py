"""Phase 179 (37th Auditor, 37/37) dual-mode unit tests for
`realhw_hdmi_braw_wpa3_702_delta_auditor` (50 tests).
"""

from __future__ import annotations

import ast
import io
import json
import os
import sys
import time
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

sys.dont_write_bytecode = True

_LAB_PKG_ROOT = str(Path(__file__).resolve().parent.parent)
if _LAB_PKG_ROOT not in sys.path:
    sys.path.insert(0, _LAB_PKG_ROOT)

import fx3_firmware_lab as ffl
from fx3_firmware_lab.__main__ import main as cli_main, run_audit_all
from fx3_firmware_lab.haita_bk4_feature_analyzer import is_forced_clean_room
from fx3_firmware_lab.realhw_hdmi_braw_wpa3_702_delta_auditor import (
    ALLOWED_702_SECURITY_PROFILES,
    APPFW_DESQUEEZE_702_FX3_MARKERS_P179,
    APPFW_HDMI_RAW_FX3_MARKERS_P179,
    APPFW_LEGACY_WEP_FX6_MARKER_P179,
    APPFW_SDI_FX6_EXCLUSIVE_MARKERS_P179,
    BIG6_SID_HEX,
    CPAPP_FX6_SDI_MARKER_P179,
    DEPRECATED_702_SECURITY_PROFILES,
    EXPECTED_ASIX_KO_BYTES,
    EXPECTED_AX88179_KO_BYTES,
    EXPECTED_CDC_NCM_KO_BYTES,
    EXPECTED_FX3_APPFW_BYTES_P179,
    EXPECTED_FX3_WPA_SUPPLICANT_BYTES_P179,
    EXPECTED_FX6_APPFW_BYTES_P179,
    EXPECTED_FX6_GEMINI_GRM_BYTES_P179,
    EXPECTED_FX6_WPA_SUPPLICANT_BYTES_P179,
    EXPECTED_GRM_MA_KO_BYTES,
    EXPECTED_R8152_KO_BYTES,
    EXPECTED_WLAN_ADJUST_BYTES_P179,
    FX3_4K_DCI_RES,
    FX3_4K_UHD_RES,
    FX3_700_RELEASE_DATE,
    FX3_702_DESQUEEZE_RATIOS,
    FX3_702_EXCLUSIVE_DESQUEEZE_RATIOS,
    FX3_702_RELEASE_DATE,
    FX3_OSD_GRM_PLANE_RES,
    FX3_RAW_SENSOR_RES,
    FX6_601_NATIVE_DESQUEEZE_RATIOS,
    MPR_CALC_REMAIN_FX3_MARKER_P179,
    PHASE_179_SCHEMA,
    PHASE_179_VERSION,
    SCEL_KERNEL_VERMAGIC_P179,
    SUPPORTED_FX3_HDMI_OUTPUT_MODES,
    SUPPORTED_USBLAN_DRIVERS_P179,
    VALID_DUAL_SLOT_REC_MODES_P179,
    VALID_MAGNIFIER_SCALES_P179,
    analyze_realhw_hdmi_braw_wpa3_702_delta,
    build_clean_room_realhw_hdmi_braw_wpa3_702_fixtures,
    build_phase179_delta_compat_matrix,
    evaluate_anamorphic_desqueeze_grm_compat,
    evaluate_auto_usblan_recognition,
    evaluate_dual_slot_remaining_time_telemetry,
    evaluate_hdmi_braw_vs_masked_12g_sdi_bridge,
    evaluate_phase179_write_guard,
    evaluate_wpa2_wpa3_security_shim,
    realhw_hdmi_braw_wpa3_702_delta_report_to_dict,
)


MODULE_PATH = (
    Path(__file__).resolve().parent.parent
    / "fx3_firmware_lab"
    / "realhw_hdmi_braw_wpa3_702_delta_auditor.py"
)


class TestPhase179RealhwHdmiBrawWpa3702Delta(unittest.TestCase):
    """Dual-mode tests (Local O_RDONLY Donors + Forced Clean-Room)."""

    # ------------------------------------------------------------------
    # 1..8: AST safety, invariants, SLA & dual-mode top-level contracts
    # ------------------------------------------------------------------

    def test_01_ast_strictly_o_rdonly_zero_builtin_open_or_writes(self) -> None:
        src = MODULE_PATH.read_text(encoding="utf-8")
        tree = ast.parse(src)
        forbidden_calls = {"open", "write_bytes", "write_text", "unlink", "rmdir", "mkdir", "chmod"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    self.assertNotIn(node.func.id, forbidden_calls, f"Forbidden call: {node.func.id}")
                elif isinstance(node.func, ast.Attribute):
                    if (
                        node.func.attr == "open"
                        and isinstance(node.func.value, ast.Name)
                        and node.func.value.id == "os"
                    ):
                        self.assertGreaterEqual(len(node.args), 2)
                        self.assertIsInstance(node.args[1], ast.Attribute)
                        self.assertEqual(node.args[1].attr, "O_RDONLY")
                    else:
                        self.assertNotIn(
                            node.func.attr,
                            {"write", "write_bytes", "write_text", "unlink", "mkdir", "open"},
                            f"Forbidden attr call: {node.func.attr}",
                        )
            elif isinstance(node, ast.Attribute) and node.attr in {"O_RDWR", "O_WRONLY", "O_CREAT", "O_TRUNC"}:
                self.fail(f"Forbidden write flag: os.{node.attr}")
        self.assertIn("O_RDONLY", src)

    def test_02_auto_mode_report_within_sla(self) -> None:
        t0 = time.perf_counter()
        report = analyze_realhw_hdmi_braw_wpa3_702_delta()
        elapsed = time.perf_counter() - t0
        self.assertLess(elapsed, 6.0)
        self.assertEqual(report.schema_version, PHASE_179_SCHEMA)
        self.assertEqual(report.phase_version, PHASE_179_VERSION)
        self.assertTrue(report.all_checks_passed, report.errors)
        self.assertEqual(report.errors, ())
        if is_forced_clean_room():
            self.assertEqual(report.mode, "CLEAN_ROOM_SYNTHETIC")
        else:
            self.assertIn(report.mode, ("LOCAL_DONOR_VERIFIED", "CLEAN_ROOM_SYNTHETIC"))

    def test_03_forced_clean_room_mode_passes_deterministically(self) -> None:
        t0 = time.perf_counter()
        r1 = analyze_realhw_hdmi_braw_wpa3_702_delta(clean_room=True)
        r2 = analyze_realhw_hdmi_braw_wpa3_702_delta(clean_room=True)
        elapsed = time.perf_counter() - t0
        self.assertLess(elapsed, 6.0)
        self.assertEqual(r1.mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(r1.all_checks_passed, r1.errors)
        self.assertEqual(r1.report_sha256, r2.report_sha256)

    def test_04_missing_donor_root_falls_back_to_clean_room(self) -> None:
        non_existent = Path("/tmp/non_existent_fx3_fx6_donor_root_phase179")
        with mock.patch(
            "fx3_firmware_lab.realhw_hdmi_braw_wpa3_702_delta_auditor.resolve_donor_file",
            return_value=None,
        ):
            r = analyze_realhw_hdmi_braw_wpa3_702_delta(repo_root=non_existent)
        self.assertEqual(r.mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(r.all_checks_passed, r.errors)

    def test_05_env_force_clean_room_override_respected(self) -> None:
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            r = analyze_realhw_hdmi_braw_wpa3_702_delta()
            self.assertEqual(r.mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertTrue(r.all_checks_passed)

    def test_06_zero_hardware_write_invariants_enforced(self) -> None:
        for cr in (False, True):
            r = analyze_realhw_hdmi_braw_wpa3_702_delta(clean_room=cr)
            self.assertTrue(r.o_rdonly_enforced)
            self.assertEqual(r.raw_firmware_bytes_leaked, 0)
            self.assertFalse(r.persistent_emmc_writes_authorized)
            self.assertFalse(r.spi_nor_write_authorized)
            self.assertFalse(r.el3_payload_transmit_authorized)
            self.assertEqual(r.physical_usb_packets_emitted, 0)

    def test_07_report_json_roundtrip_and_zero_key_leak(self) -> None:
        r = analyze_realhw_hdmi_braw_wpa3_702_delta(clean_room=True)
        d = realhw_hdmi_braw_wpa3_702_delta_report_to_dict(r)
        text = json.dumps(d, sort_keys=True)
        parsed = json.loads(text)
        self.assertEqual(parsed["schema_version"], PHASE_179_SCHEMA)
        self.assertNotIn("CXD90057_k8", text)
        self.assertNotIn("BEGIN RSA PRIVATE KEY", text)
        self.assertTrue(parsed["hdmi_braw_bridged_sdi_masked"])
        self.assertTrue(parsed["wpa2_wpa3_only_enforced"])
        self.assertTrue(parsed["anamorphic_15x_16x_grm_unclipped"])
        self.assertTrue(parsed["usblan_and_dual_slot_telemetry_ready"])

    def test_08_local_donor_verified_exact_sizes_when_present(self) -> None:
        r = analyze_realhw_hdmi_braw_wpa3_702_delta()
        if r.mode != "LOCAL_DONOR_VERIFIED":
            self.skipTest("Clean-room forced or local donors absent")
        self.assertEqual(r.donor_file_sizes["fx3_appfw"], EXPECTED_FX3_APPFW_BYTES_P179)
        self.assertEqual(r.donor_file_sizes["fx6_appfw"], EXPECTED_FX6_APPFW_BYTES_P179)
        self.assertEqual(r.donor_file_sizes["fx3_wpa"], EXPECTED_FX3_WPA_SUPPLICANT_BYTES_P179)
        self.assertEqual(r.donor_file_sizes["fx6_wpa"], EXPECTED_FX6_WPA_SUPPLICANT_BYTES_P179)
        self.assertEqual(r.donor_file_sizes["fx3_wlan_adj"], EXPECTED_WLAN_ADJUST_BYTES_P179)
        self.assertEqual(r.donor_file_sizes["fx6_grm"], EXPECTED_FX6_GEMINI_GRM_BYTES_P179)
        self.assertEqual(r.donor_file_sizes["fx3_cdc_ncm"], EXPECTED_CDC_NCM_KO_BYTES)
        self.assertEqual(r.donor_file_sizes["fx3_r8152"], EXPECTED_R8152_KO_BYTES)
        self.assertEqual(r.donor_file_sizes["fx3_asix"], EXPECTED_ASIX_KO_BYTES)
        self.assertEqual(r.donor_file_sizes["fx3_ax88179"], EXPECTED_AX88179_KO_BYTES)
        self.assertEqual(r.donor_file_sizes["fx3_grm_ko"], EXPECTED_GRM_MA_KO_BYTES)

    # ------------------------------------------------------------------
    # 9..17: Pillar 1 — Type-A HDMI BRAW / 4K60 vs Masked 12G-SDI RAW
    # ------------------------------------------------------------------

    def test_09_pillar1_fx3_hdmi_raw_vs_fx6_sdi_marker_asymmetry(self) -> None:
        r = analyze_realhw_hdmi_braw_wpa3_702_delta()
        p1 = r.pillar1_hdmi_braw_vs_sdi
        self.assertTrue(p1.passed)
        for tok in APPFW_HDMI_RAW_FX3_MARKERS_P179:
            self.assertGreater(p1.fx3_appfw_hdmi_raw_hits[tok], 0, tok)
        for tok in APPFW_SDI_FX6_EXCLUSIVE_MARKERS_P179:
            self.assertEqual(p1.fx3_appfw_sdi_hits[tok], 0, tok)
            self.assertGreater(p1.fx6_appfw_sdi_hits[tok], 0, tok)
        self.assertEqual(p1.fx3_cpapp_sdi_hits, 0)
        self.assertGreater(p1.fx6_cpapp_sdi_hits, 0)

    def test_10_hdmi_braw_4k60_passthrough_ok(self) -> None:
        ev = evaluate_hdmi_braw_vs_masked_12g_sdi_bridge(requested_mode="HDMI_BRAW_4K60")
        self.assertTrue(ev.valid)
        self.assertTrue(ev.hdmi_raw_braw_ready)
        self.assertTrue(ev.hdmi_clean_lut_tc_bridged)
        self.assertTrue(ev.sdi_hw_probe_masked)
        self.assertFalse(ev.sdi_bnc_present)
        self.assertEqual(ev.sdi_blocking_faults, 0)

    def test_11_hdmi_prores_raw_4k60_passthrough_ok(self) -> None:
        ev = evaluate_hdmi_braw_vs_masked_12g_sdi_bridge(requested_mode="HDMI_PRORES_RAW_4K60")
        self.assertTrue(ev.valid)
        self.assertTrue(ev.hdmi_raw_braw_ready)
        self.assertEqual(ev.resolved_hdmi_mode, "HDMI_PRORES_RAW_4K60")

    def test_12_hdmi_raw_forbids_lut_burn_in(self) -> None:
        ev = evaluate_hdmi_braw_vs_masked_12g_sdi_bridge(
            requested_mode="HDMI_BRAW_4K60",
            lut_burn_in_enabled=True,
        )
        self.assertFalse(ev.valid)
        self.assertFalse(ev.hdmi_raw_braw_ready)
        self.assertIn("RAW_HDMI_FORBIDS_LUT_BURN_IN", ev.errors)

    def test_13_hdmi_raw_requires_connected_recorder(self) -> None:
        ev = evaluate_hdmi_braw_vs_masked_12g_sdi_bridge(
            requested_mode="HDMI_BRAW_4K60",
            hdmi_raw_device_connected=False,
        )
        self.assertFalse(ev.valid)
        self.assertIn("HDMI_RAW_RECORDER_DISCONNECTED", ev.errors)

    def test_14_hdmi_clean_4k60_and_1080p_osd_modes(self) -> None:
        for mode in ("HDMI_CLEAN_4K60_10BIT_LUT", "HDMI_1080P60_OSD"):
            ev = evaluate_hdmi_braw_vs_masked_12g_sdi_bridge(requested_mode=mode)
            self.assertTrue(ev.valid)
            self.assertTrue(ev.hdmi_clean_lut_tc_bridged)
            self.assertFalse(ev.hdmi_raw_braw_ready)

    def test_15_sdi_12g_raw_request_masked_without_faults(self) -> None:
        ev = evaluate_hdmi_braw_vs_masked_12g_sdi_bridge(
            requested_mode="SDI_12G_RAW_REQUEST",
            hdmi_raw_device_connected=True,
        )
        self.assertFalse(ev.valid)
        self.assertTrue(ev.sdi_hw_probe_masked)
        self.assertEqual(ev.sdi_blocking_faults, 0)
        self.assertEqual(ev.resolved_hdmi_mode, "HDMI_BRAW_4K60")
        self.assertEqual(ev.bridge_class, "MASKED_ABSENT_HW")

    def test_16_sdi_12g_monitor_request_masked_cleanly(self) -> None:
        ev = evaluate_hdmi_braw_vs_masked_12g_sdi_bridge(requested_mode="SDI_12G_MONITOR_REQUEST")
        self.assertFalse(ev.valid)
        self.assertTrue(ev.sdi_hw_probe_masked)
        self.assertEqual(ev.sdi_blocking_faults, 0)
        self.assertEqual(ev.resolved_hdmi_mode, "HDMI_CLEAN_4K60_10BIT_LUT")

    def test_17_unknown_hdmi_bridge_mode_rejected(self) -> None:
        ev = evaluate_hdmi_braw_vs_masked_12g_sdi_bridge(requested_mode="DP_ALT_8K_UNSUPPORTED")
        self.assertFalse(ev.valid)
        self.assertEqual(ev.resolved_hdmi_mode, "INVALID")
        self.assertIn("HDMI_BRAW_4K60", SUPPORTED_FX3_HDMI_OUTPUT_MODES)

    # ------------------------------------------------------------------
    # 18..26: Pillar 2 — WPA2/WPA3-Only & Access Auth vs WEP/WPA1/IPsec
    # ------------------------------------------------------------------

    def test_18_pillar2_fx3_702_stripped_wep_enum_present_in_fx6_601(self) -> None:
        r = analyze_realhw_hdmi_braw_wpa3_702_delta()
        p2 = r.pillar2_wpa2_wpa3_security
        self.assertTrue(p2.passed)
        self.assertEqual(p2.fx3_legacy_wep_enum_hits, 0)
        self.assertGreater(p2.fx6_legacy_wep_enum_hits, 0)
        self.assertIn("SAE", p2.fx3_wpa_summary.marker_hits)
        self.assertGreater(p2.fx3_wpa_summary.marker_hits["SAE"], 0)
        self.assertGreater(p2.fx3_wpa_summary.marker_hits["PMF"], 0)

    def test_19_all_deprecated_security_profiles_fail_closed(self) -> None:
        for prof in DEPRECATED_702_SECURITY_PROFILES:
            ev = evaluate_wpa2_wpa3_security_shim(requested_profile=prof)
            self.assertFalse(ev.valid, prof)
            self.assertTrue(ev.deprecated_protocol_rejected, prof)
            self.assertFalse(ev.passed_to_wpa_supplicant, prof)
            self.assertEqual(ev.rf_tx_packets_emitted, 0)

    def test_20_wpa3_sae_passes_with_pmf_required(self) -> None:
        ev = evaluate_wpa2_wpa3_security_shim(requested_profile="WPA3_SAE")
        self.assertTrue(ev.valid)
        self.assertTrue(ev.passed_to_wpa_supplicant)
        self.assertEqual(ev.resolved_wpa_key_mgmt, "SAE")
        self.assertEqual(ev.pmf_ieee80211w_mode, 2)
        self.assertFalse(ev.deprecated_protocol_rejected)

    def test_21_wpa2_profiles_pass_cleanly(self) -> None:
        for prof in ("WPA2_PSK_CCMP", "WPA2_PSK_SHA256", "WPA2_WPA3_TRANSITION"):
            ev = evaluate_wpa2_wpa3_security_shim(requested_profile=prof)
            self.assertTrue(ev.valid, prof)
            self.assertTrue(ev.passed_to_wpa_supplicant, prof)
            self.assertGreaterEqual(ev.pmf_ieee80211w_mode, 1)

    def test_22_access_auth_tls_allowed_even_under_p12(self) -> None:
        ev = evaluate_wpa2_wpa3_security_shim(
            requested_profile="ACCESS_AUTH_TLS",
            airplane_mode_p12=True,
            access_auth_enabled=True,
        )
        self.assertTrue(ev.valid)
        self.assertEqual(ev.resolved_wpa_key_mgmt, "ACCESS_AUTH_TLS_1_3")
        self.assertEqual(ev.pmf_ieee80211w_mode, 2)

    def test_23_access_auth_missing_credentials_rejected(self) -> None:
        ev = evaluate_wpa2_wpa3_security_shim(
            requested_profile="ACCESS_AUTH_TLS",
            access_auth_enabled=False,
        )
        self.assertFalse(ev.valid)
        self.assertFalse(ev.passed_to_wpa_supplicant)
        self.assertIn("ACCESS_AUTHENTICATION_CREDENTIALS_MISSING", ev.errors)

    def test_24_p12_airplane_mode_blocks_wifi_rf_tx(self) -> None:
        for prof in ("WPA3_SAE", "WPA2_PSK_CCMP", "WPA2_WPA3_TRANSITION"):
            ev = evaluate_wpa2_wpa3_security_shim(requested_profile=prof, airplane_mode_p12=True)
            self.assertFalse(ev.valid)
            self.assertFalse(ev.passed_to_wpa_supplicant)
            self.assertEqual(ev.rf_tx_packets_emitted, 0)
            self.assertEqual(ev.bridge_class, "HARD_WRITE_PROTECTED")

    def test_25_unknown_security_profile_rejected(self) -> None:
        ev = evaluate_wpa2_wpa3_security_shim(requested_profile="OPEN_UNENCRYPTED_PUBLIC")
        self.assertFalse(ev.valid)
        self.assertTrue(ev.deprecated_protocol_rejected)

    def test_26_allowed_security_tuple_contains_no_legacy_wep_or_tkip(self) -> None:
        for prof in ALLOWED_702_SECURITY_PROFILES:
            self.assertNotIn("WEP", prof)
            self.assertNotIn("TKIP", prof)
            self.assertNotIn("IPSEC", prof)

    # ------------------------------------------------------------------
    # 27..34: Pillar 3 — 1.5x/1.6x/1.3x/2.0x Anamorphic De-Squeeze & GRM
    # ------------------------------------------------------------------

    def test_27_pillar3_15x_16x_delta_present_only_in_fx3_702(self) -> None:
        r = analyze_realhw_hdmi_braw_wpa3_702_delta()
        p3 = r.pillar3_anamorphic_grm
        self.assertTrue(p3.passed)
        for tok in APPFW_DESQUEEZE_702_FX3_MARKERS_P179:
            self.assertGreater(p3.fx3_appfw_desqueeze_hits[tok], 0, tok)
        self.assertEqual(p3.fx6_appfw_desqueeze_hits["EXTERN_VAL_DE_SQUEEZE_DISP_1_5X"], 0)
        self.assertEqual(p3.fx6_appfw_desqueeze_hits["DE_SQUEEZE_DISP_1_6X"], 0)
        self.assertTrue(p3.fx3_grm_ma_ko.modinfo_valid)
        self.assertTrue(p3.fx6_grm_ma_ko.modinfo_valid)

    def test_28_all_fx3_702_desqueeze_ratios_keep_big6_unclipped(self) -> None:
        self.assertEqual(FX3_702_EXCLUSIVE_DESQUEEZE_RATIOS, (1.5, 1.6))
        self.assertEqual(FX6_601_NATIVE_DESQUEEZE_RATIOS, (1.0, 1.3, 2.0))
        for ratio in FX3_702_DESQUEEZE_RATIOS:
            ev = evaluate_anamorphic_desqueeze_grm_compat(desqueeze_ratio=ratio)
            self.assertTrue(ev.valid, ratio)
            self.assertTrue(ev.big6_hud_unclipped, ratio)
            self.assertEqual(ev.osd_grm_scale_x, 1.0)
            self.assertEqual(ev.osd_grm_scale_y, 1.0)
            self.assertAlmostEqual(ev.video_plane_scale_y, round(1.0 / ratio, 6), places=5)

    def test_29_fx3_exclusive_ratios_flagged_as_shim_translated(self) -> None:
        for ratio in (1.5, 1.6):
            ev = evaluate_anamorphic_desqueeze_grm_compat(desqueeze_ratio=ratio, magnifier_scale=1.0)
            self.assertFalse(ev.fx6_native_ratio)
            self.assertTrue(ev.fx3_702_shim_required)
            self.assertEqual(ev.bridge_class, "SHIM_TRANSLATED")

    def test_30_bright_monitoring_never_alters_recorded_gain(self) -> None:
        ev = evaluate_anamorphic_desqueeze_grm_compat(
            desqueeze_ratio=1.5,
            bright_monitoring_on=True,
            magnifier_scale=4.0,
        )
        self.assertTrue(ev.valid)
        self.assertTrue(ev.bright_monitoring_display_only)
        self.assertEqual(BIG6_SID_HEX, "0x0a")

    def test_31_magnifier_scales_stay_within_sensor_bounds(self) -> None:
        for mag in VALID_MAGNIFIER_SCALES_P179:
            ev = evaluate_anamorphic_desqueeze_grm_compat(desqueeze_ratio=1.6, magnifier_scale=mag)
            self.assertTrue(ev.valid, mag)
            self.assertGreater(ev.magnifier_roi_w_px, 0)
            self.assertLessEqual(ev.magnifier_roi_w_px, FX3_RAW_SENSOR_RES[0])
            self.assertGreater(ev.magnifier_roi_h_px, 0)
            self.assertLessEqual(ev.magnifier_roi_h_px, FX3_RAW_SENSOR_RES[1])

    def test_32_clean_hdmi_unclipped_across_ratios(self) -> None:
        for ratio in FX3_702_DESQUEEZE_RATIOS:
            ev = evaluate_anamorphic_desqueeze_grm_compat(
                desqueeze_ratio=ratio,
                clean_hdmi_mode=True,
                hdmi_raw_active=False,
            )
            self.assertTrue(ev.valid)
            self.assertTrue(ev.clean_hdmi_unclipped)

    def test_33_conflicting_clean_hdmi_and_raw16_rejected(self) -> None:
        ev = evaluate_anamorphic_desqueeze_grm_compat(
            desqueeze_ratio=1.5,
            clean_hdmi_mode=True,
            hdmi_raw_active=True,
        )
        self.assertFalse(ev.valid)
        self.assertIn("CONFLICTING_CLEAN_HDMI_AND_RAW16_ACTIVE", ev.errors)

    def test_34_unsupported_desqueeze_or_magnifier_rejected(self) -> None:
        e1 = evaluate_anamorphic_desqueeze_grm_compat(desqueeze_ratio=1.8)
        e2 = evaluate_anamorphic_desqueeze_grm_compat(desqueeze_ratio=1.5, magnifier_scale=12.0)
        self.assertFalse(e1.valid)
        self.assertFalse(e2.valid)
        self.assertEqual(FX3_OSD_GRM_PLANE_RES, (1920, 1080))
        self.assertEqual(FX3_4K_UHD_RES, (3840, 2160))
        self.assertEqual(FX3_4K_DCI_RES, (4096, 2160))

    # ------------------------------------------------------------------
    # 35..44: Pillar 4 — Auto USB-LAN, Dual-Slot Telemetry & Firewall
    # ------------------------------------------------------------------

    def test_35_pillar4_kmods_and_mpr_calc_remain_verified(self) -> None:
        r = analyze_realhw_hdmi_braw_wpa3_702_delta()
        p4 = r.pillar4_usblan_dual_slot_matrix
        self.assertTrue(p4.passed)
        self.assertEqual(len(p4.kmod_summaries), 8)
        for km in p4.kmod_summaries:
            self.assertTrue(km.modinfo_valid, km.module_name)
            self.assertTrue(km.vermagic_match, km.module_name)
        self.assertGreater(p4.fx3_mpr_summary.marker_hits[MPR_CALC_REMAIN_FX3_MARKER_P179], 0)

    def test_36_all_supported_usblan_drivers_auto_bind_eth0(self) -> None:
        for drv in SUPPORTED_USBLAN_DRIVERS_P179:
            ev = evaluate_auto_usblan_recognition(adapter_driver=drv)
            self.assertTrue(ev.valid, drv)
            self.assertEqual(ev.auto_netif_name, "eth0")
            self.assertTrue(ev.dhcp_bound)
            self.assertEqual(ev.rf_tx_leaks, 0)

    def test_37_usblan_rejects_vermagic_mismatch_or_bad_driver(self) -> None:
        bad_vm = evaluate_auto_usblan_recognition(
            adapter_driver="RTL8153",
            vermagic="5.15.0-generic",
        )
        bad_drv = evaluate_auto_usblan_recognition(adapter_driver="BROADCOM_PROPRIETARY")
        bad_spd = evaluate_auto_usblan_recognition(adapter_driver="CDC_NCM", link_speed_mbps=54)
        self.assertFalse(bad_vm.valid)
        self.assertFalse(bad_drv.valid)
        self.assertFalse(bad_spd.valid)

    def test_38_dual_slot_simultaneous_bottleneck_math(self) -> None:
        ev = evaluate_dual_slot_remaining_time_telemetry(
            rec_mode="SIMULTANEOUS",
            codec_bitrate_mbps=200.0,
            slot_a_free_mib=128_000,
            slot_b_free_mib=64_000,
        )
        self.assertTrue(ev.valid)
        self.assertEqual(ev.bottleneck_slot, "SLOT_B")
        self.assertEqual(ev.effective_remaining_min, ev.slot_b_remaining_min)
        self.assertTrue(ev.zero_frame_drop_rollover)

    def test_39_dual_slot_relay_adds_both_slots_zero_drop(self) -> None:
        ev = evaluate_dual_slot_remaining_time_telemetry(
            rec_mode="RELAY",
            codec_bitrate_mbps=200.0,
            slot_a_free_mib=128_000,
            slot_b_free_mib=64_000,
        )
        self.assertTrue(ev.valid)
        self.assertEqual(ev.bottleneck_slot, "NONE_COMBINED_RELAY")
        self.assertAlmostEqual(
            ev.effective_remaining_min,
            round(ev.slot_a_remaining_min + ev.slot_b_remaining_min, 2),
            places=2,
        )
        self.assertTrue(ev.zero_frame_drop_rollover)

    def test_40_dual_slot_sort_separates_main_and_proxy_bitrates(self) -> None:
        ev = evaluate_dual_slot_remaining_time_telemetry(
            rec_mode="SORT",
            codec_bitrate_mbps=600.0,
            slot_a_free_mib=128_000,
            slot_b_free_mib=64_000,
            proxy_bitrate_mbps=16.0,
        )
        self.assertTrue(ev.valid)
        self.assertEqual(ev.bottleneck_slot, "SLOT_A_MAIN")
        self.assertLess(ev.slot_a_remaining_min, ev.slot_b_remaining_min)

    def test_41_dual_slot_error_guards(self) -> None:
        for mode in VALID_DUAL_SLOT_REC_MODES_P179:
            self.assertIn(mode, ("SIMULTANEOUS", "RELAY", "SORT", "SINGLE_SLOT_A"))
        e_empty_sim = evaluate_dual_slot_remaining_time_telemetry(rec_mode="SIMULTANEOUS", slot_a_free_mib=100, slot_b_free_mib=0)
        e_empty_rel = evaluate_dual_slot_remaining_time_telemetry(rec_mode="RELAY", slot_a_free_mib=0, slot_b_free_mib=0)
        e_bad_mode = evaluate_dual_slot_remaining_time_telemetry(rec_mode="RAID_STRIPED")
        e_bad_br = evaluate_dual_slot_remaining_time_telemetry(codec_bitrate_mbps=0.0)
        for bad in (e_empty_sim, e_empty_rel, e_bad_mode, e_bad_br):
            self.assertFalse(bad.valid)
            self.assertFalse(bad.zero_frame_drop_rollover)

    def test_42_write_guard_allows_volatile_and_external_cards(self) -> None:
        for path in (
            "/tmp/fx6_stage_b/wpa_supplicant.conf",
            "ram://stage_b/grm_plane_cfg.json",
            "/mnt/cfexpress_a/PRIVATE/M4ROOT/CLIP/C0001.MP4",
            "/mnt/sd/PRIVATE/SONY/PRO/STAGE_B.SH",
        ):
            g = evaluate_phase179_write_guard(path)
            self.assertTrue(g.valid, path)
            self.assertTrue(g.volatile_or_ext_allowed, path)
            self.assertFalse(g.persistent_emmc_writes_authorized)
            self.assertFalse(g.spi_nor_write_authorized)

    def test_43_write_guard_hard_blocks_all_emmc_and_spinor_targets(self) -> None:
        for path in (
            "/dev/nflasha5",
            "/dev/cnflasha12",
            "/dev/mmcblk0p2",
            "p2:/Backup.bin",
            "p8:/cpapp-b.bin",
            "p12:/cert/RQ_LIC.DAT",
            "p18:/lens/lensfile.bin",
            "p5:/wbi/snapshot.bin",
            "/etc/wpa_supplicant.conf",
            "spi_nor:/loader_nor.bin",
            "/setting/psd.bin",
        ):
            g = evaluate_phase179_write_guard(path)
            self.assertFalse(g.valid, path)
            self.assertTrue(g.persistent_write_blocked, path)
            self.assertEqual(g.emmc_mutation_bytes, 0)
            self.assertFalse(g.persistent_emmc_writes_authorized)
            self.assertFalse(g.spi_nor_write_authorized)

    def test_44_12_touchpoint_4_class_matrix_complete(self) -> None:
        m = build_phase179_delta_compat_matrix()
        self.assertEqual(m.total_touchpoints, 12)
        self.assertEqual(len(m.touchpoints), 12)
        self.assertEqual(sum(m.class_counts.values()), 12)
        for cls_name in (
            "NATIVE_PASSTHROUGH",
            "SHIM_TRANSLATED",
            "MASKED_ABSENT_HW",
            "HARD_WRITE_PROTECTED",
        ):
            self.assertGreaterEqual(m.class_counts[cls_name], 1, cls_name)

    # ------------------------------------------------------------------
    # 45..50: CLI, Package Exports, Audit-All (37/37) & Fixture Checks
    # ------------------------------------------------------------------

    def test_45_clean_room_fixtures_integrity_and_headers(self) -> None:
        fx = build_clean_room_realhw_hdmi_braw_wpa3_702_fixtures()
        self.assertGreaterEqual(len(fx), 24)
        for k, blob in fx.items():
            self.assertGreater(len(blob), 16, k)
            if "cpapp" not in k:
                self.assertEqual(blob[:4], b"\x7fELF", k)
            if k.endswith(("cdc_ncm", "r8152", "asix", "ax88179", "grm_ko")):
                self.assertIn(SCEL_KERNEL_VERMAGIC_P179.encode("ascii"), blob, k)

    def test_46_package_init_exports_all_phase179_symbols(self) -> None:
        for sym in (
            "PHASE_179_SCHEMA",
            "PHASE_179_VERSION",
            "RealhwHdmiBrawWpa3702DeltaReport",
            "analyze_realhw_hdmi_braw_wpa3_702_delta",
            "realhw_hdmi_braw_wpa3_702_delta_report_to_dict",
            "evaluate_hdmi_braw_vs_masked_12g_sdi_bridge",
            "evaluate_wpa2_wpa3_security_shim",
            "evaluate_anamorphic_desqueeze_grm_compat",
            "evaluate_auto_usblan_recognition",
            "evaluate_dual_slot_remaining_time_telemetry",
            "evaluate_phase179_write_guard",
            "build_phase179_delta_compat_matrix",
            "build_clean_room_realhw_hdmi_braw_wpa3_702_fixtures",
        ):
            self.assertTrue(hasattr(ffl, sym), f"Missing export: {sym}")
            self.assertIn(sym, ffl.__all__, f"Missing __all__: {sym}")

    def test_47_cli_subcommand_clean_room_json_ok(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cli_main(["audit-realhw-hdmi-braw-wpa3-702-delta", "--clean-room", "--json"])
        self.assertEqual(rc, 0)
        parsed = json.loads(buf.getvalue())
        self.assertTrue(parsed["all_checks_passed"])
        self.assertEqual(parsed["mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(parsed["schema_version"], PHASE_179_SCHEMA)
        self.assertEqual(parsed["raw_firmware_bytes_leaked"], 0)

    def test_48_cli_subcommand_auto_mode_json_ok(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cli_main(["audit-realhw-hdmi-braw-wpa3-702-delta", "--json"])
        self.assertEqual(rc, 0)
        parsed = json.loads(buf.getvalue())
        self.assertTrue(parsed["all_checks_passed"])
        self.assertFalse(parsed["persistent_emmc_writes_authorized"])
        self.assertFalse(parsed["spi_nor_write_authorized"])
        self.assertFalse(parsed["el3_payload_transmit_authorized"])
        self.assertEqual(parsed["physical_usb_packets_emitted"], 0)

    def test_49_run_audit_all_registers_37_of_37_auditors(self) -> None:
        summary = run_audit_all(clean_room=True)
        self.assertTrue(summary["all_checks_passed"])
        self.assertIn("realhw_hdmi_braw_wpa3_702_delta_audit", summary)
        audit_keys = [k for k in summary.keys() if k.endswith("_audit")]
        self.assertEqual(len(audit_keys), 37)
        self.assertTrue(summary["realhw_hdmi_braw_wpa3_702_delta_audit"]["all_checks_passed"])

    def test_50_release_metadata_constants_accurate(self) -> None:
        self.assertEqual(FX3_702_RELEASE_DATE, "2026-03-17")
        self.assertEqual(FX3_700_RELEASE_DATE, "2025-08-26")
        self.assertEqual(CPAPP_FX6_SDI_MARKER_P179, "MoniFpgaSdi_SetRegSDIOutFormat")
        self.assertEqual(APPFW_LEGACY_WEP_FX6_MARKER_P179, "VAL_setting_wlan_security_WLAN_SECURITY_WEP")


if __name__ == "__main__":
    unittest.main()
