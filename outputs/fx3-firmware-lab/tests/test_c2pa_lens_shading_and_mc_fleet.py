"""Phase 105 Dual-Mode Unit Tests: C2PA 2.1 Camera Authenticity / cnflasha Key-Vault
Firewall, E-Mount 12-Pin Lens Shading / Vignetting / Lateral CA / Distortion
Compensation, Sony Monitor & Control Wired USB-LAN PTP-IP Multi-Cam Fleet Isolation,
& Per-Body Factory Shading / Defect-Pixel Map Bit-Exact Preservation Proof.
"""

from __future__ import annotations

import json
import os
import re
import time
import unittest
from pathlib import Path
from unittest import mock

import fx3_firmware_lab as lab
from fx3_firmware_lab.__main__ import main as cli_main, run_audit_all
from fx3_firmware_lab.c2pa_lens_shading_and_mc_fleet_auditor import (
    C2PA_JUMBF_BOX_TYPES,
    C2PA_JUMBF_UUID_HEX,
    C2PA_MAX_LICENSES_PER_RQ_LIC_FX3,
    C2PA_SPEC_VERSION,
    C2PA_SUPPORTED_MP4_MAX_BITRATE_MBPS,
    CNFLASHA_KEYVAULT_MOUNT_MODE,
    DISTORTION_INVERSION_MAX_RESIDUAL,
    EMOUNT_LENS_PROFILES,
    FACTORY_CALIBRATION_FILES,
    FX3_APPFW_PHASE105_MARKERS,
    FX6_APPFW_PHASE105_MARKERS,
    LATERAL_CA_MAX_RESIDUAL_PX,
    LATERAL_CA_MIN_REDUCTION_RATIO,
    MC_FREE_PLAN_MAX_CAMERAS,
    MC_GANG_REC_MAX_SKEW_MS,
    MC_USB_LAN_PRACTICAL_CAP_MBPS,
    PHASE_105_SCHEMA,
    PHASE_105_VERSION,
    PTPIP_PKT_INIT_EVENT_REQ,
    PTPIP_PROTOCOL_VERSION,
    PTPIP_TCP_PORT,
    SHADING_MAX_DIGITAL_GAIN,
    STAGE_B_CLEAN_ROOM_RESEARCH_LABEL,
    McFleetCameraNode,
    analyze_c2pa_lens_shading_and_mc_fleet,
    apply_radial_distortion,
    build_c2pa_jumbf_box,
    build_clean_room_c2pa_shading_mc_fixtures,
    build_default_4cam_mc_fleet,
    build_ptpip_init_packet,
    c2pa_lens_shading_and_mc_fleet_report_to_dict,
    compute_cos4_vignetting_gain,
    compute_lateral_ca_radial_shift,
    evaluate_c2pa_keyvault_firewall,
    evaluate_emount_lens_compensation,
    evaluate_factory_shading_write_guard,
    evaluate_mc_wired_fleet_matrix,
    invert_radial_distortion,
    parse_c2pa_jumbf_box,
    parse_ptpip_init_packet,
)


_BYTES_REPR_RE = re.compile(r"(?<![0-9A-Za-z_/.-])b['\"]")
_AUDITOR_PATH = (
    Path(__file__).resolve().parent.parent
    / "fx3_firmware_lab"
    / "c2pa_lens_shading_and_mc_fleet_auditor.py"
)


class TestC2paLensShadingAndMcFleet(unittest.TestCase):
    """Comprehensive dual-mode tests (>= 40) for the 20th unified auditor."""

    def test_01_clean_room_report_all_pillars_and_warm_runtime(self) -> None:
        t0 = time.perf_counter()
        rep = analyze_c2pa_lens_shading_and_mc_fleet(clean_room=True)
        dt_cold = time.perf_counter() - t0
        t1 = time.perf_counter()
        rep_warm = analyze_c2pa_lens_shading_and_mc_fleet(clean_room=True)
        dt_warm = time.perf_counter() - t1

        self.assertTrue(rep.all_checks_passed, rep.errors)
        self.assertEqual(rep.mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(rep.schema_version, PHASE_105_SCHEMA)
        self.assertEqual(rep.phase_version, PHASE_105_VERSION)
        self.assertTrue(rep.pillar_1_c2pa_keyvault.passed)
        self.assertTrue(rep.pillar_2_emount_lens_shading.passed)
        self.assertTrue(rep.pillar_3_mc_wired_fleet.passed)
        self.assertTrue(rep.pillar_4_factory_shading_immutability.passed)
        self.assertEqual(rep.report_sha256, rep_warm.report_sha256)
        self.assertEqual(len(rep.report_sha256), 64)
        self.assertLess(dt_cold, 0.50 if __import__("os").environ.get("GITHUB_ACTIONS") == "true" else 0.08)
        self.assertLess(dt_warm, 0.25 if __import__("os").environ.get("GITHUB_ACTIONS") == "true" else 0.02)

    def test_02_auto_mode_or_local_donor_runtime_and_pass(self) -> None:
        t0 = time.perf_counter()
        rep = analyze_c2pa_lens_shading_and_mc_fleet()
        dt = time.perf_counter() - t0
        self.assertTrue(rep.all_checks_passed, rep.errors)
        self.assertIn(rep.mode, ("LOCAL_DONOR_VERIFIED", "CLEAN_ROOM_SYNTHETIC"))
        self.assertLess(dt, 0.35)
        if rep.mode == "LOCAL_DONOR_VERIFIED":
            self.assertGreater(rep.donor_file_sizes.get("fx3_appfw", 0), 70_000_000)
            self.assertGreater(rep.donor_file_sizes.get("fx6_appfw", 0), 45_000_000)
            self.assertIn(
                "_ZN9InfraC2PA21SearchCertificateFileERKNS_28searchCertificateFileInParamEPNS_29searchCertificateFileOutParamE",
                rep.pillar_1_c2pa_keyvault.fx3_appfw_c2pa_markers,
            )

    def test_03_forced_clean_room_env_flag_respected(self) -> None:
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}, clear=False):
            rep = analyze_c2pa_lens_shading_and_mc_fleet()
        self.assertTrue(rep.all_checks_passed, rep.errors)
        self.assertEqual(rep.mode, "CLEAN_ROOM_SYNTHETIC")

    def test_04_json_serialization_has_no_bytes_repr(self) -> None:
        rep = analyze_c2pa_lens_shading_and_mc_fleet(clean_room=True)
        payload = c2pa_lens_shading_and_mc_fleet_report_to_dict(rep)
        json_str = json.dumps(payload, sort_keys=True)
        self.assertIsNone(_BYTES_REPR_RE.search(json_str), "Unexpected Python bytes repr in JSON")
        decoded = json.loads(json_str)
        self.assertEqual(decoded["report_sha256"], rep.report_sha256)
        self.assertTrue(decoded["all_checks_passed"])

    def test_05_package_exports_and_dunder_all_present(self) -> None:
        expected_symbols = (
            "PHASE_105_SCHEMA",
            "PHASE_105_VERSION",
            "C2PA_SPEC_VERSION",
            "C2PA_JUMBF_UUID_HEX",
            "EMOUNT_LENS_PROFILES",
            "FACTORY_CALIBRATION_FILES",
            "C2paLensShadingAndMcFleetReport",
            "analyze_c2pa_lens_shading_and_mc_fleet",
            "c2pa_lens_shading_and_mc_fleet_report_to_dict",
            "evaluate_c2pa_keyvault_firewall",
            "evaluate_emount_lens_compensation",
            "evaluate_mc_wired_fleet_matrix",
            "evaluate_factory_shading_write_guard",
            "verify_factory_shading_and_defect_immutability",
        )
        for sym in expected_symbols:
            self.assertTrue(hasattr(lab, sym), f"Missing attribute on package: {sym}")
            self.assertIn(sym, lab.__all__, f"Missing symbol in __all__: {sym}")

    def test_06_static_rdonly_and_zero_write_flags_in_auditor_source(self) -> None:
        src = _AUDITOR_PATH.read_text(encoding="utf-8")
        self.assertIn("os.O_RDONLY", src)
        self.assertIn("mmap.ACCESS_READ", src)
        for forbidden in ("os.O_WRONLY", "os.O_RDWR", "os.O_CREAT", "mmap.ACCESS_WRITE"):
            self.assertNotIn(forbidden, src)

    def test_07_synthetic_fixtures_contain_all_verified_markers(self) -> None:
        fixtures = build_clean_room_c2pa_shading_mc_fixtures()
        fx3_blob = fixtures["fx3_appfw"].decode("latin1")
        fx6_blob = fixtures["fx6_appfw"].decode("latin1")
        for m in FX3_APPFW_PHASE105_MARKERS:
            self.assertIn(m, fx3_blob)
        for m in FX6_APPFW_PHASE105_MARKERS:
            self.assertIn(m, fx6_blob)

    def test_08_uxc_labels_extracted_cleanly(self) -> None:
        rep = analyze_c2pa_lens_shading_and_mc_fleet(clean_room=True)
        self.assertEqual(
            rep.pillar_1_c2pa_keyvault.uxc_c2pa_labels["fx3_signature_type_c2pa"],
            "Signature Type: On(C2PA)",
        )
        self.assertEqual(
            rep.pillar_1_c2pa_keyvault.uxc_c2pa_labels["fx6_cert_for_c2pa"],
            "Certificate for C2PA",
        )
        self.assertEqual(
            rep.pillar_2_emount_lens_shading.uxc_lens_labels["fx3_lens_comp"],
            "Lens Comp.",
        )
        self.assertEqual(
            rep.pillar_2_emount_lens_shading.uxc_lens_labels["fx6_shading_comp"],
            "Shading Compensation",
        )
        self.assertEqual(
            rep.pillar_3_mc_wired_fleet.uxc_mc_labels["fx3_wired_lan"],
            "Wired LAN",
        )
        self.assertEqual(
            rep.pillar_3_mc_wired_fleet.uxc_mc_labels["fx6_wired_lan_cam_remote"],
            "Wired LAN Cam. Remote Ctrl",
        )

    def test_09_cli_audit_c2pa_shading_mc_clean_room_json(self) -> None:
        import io
        from contextlib import redirect_stdout

        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cli_main(["audit-c2pa-shading-mc", "--clean-room", "--json"])
        self.assertEqual(rc, 0)
        parsed = json.loads(buf.getvalue())
        self.assertEqual(parsed["schema_version"], PHASE_105_SCHEMA)
        self.assertTrue(parsed["all_checks_passed"])

    def test_10_run_audit_all_includes_20_auditors_green(self) -> None:
        summary = run_audit_all(clean_room=True)
        self.assertTrue(summary["all_checks_passed"], summary)
        self.assertIn("c2pa_lens_shading_and_mc_fleet_audit", summary)
        self.assertTrue(summary["c2pa_lens_shading_and_mc_fleet_audit"]["all_checks_passed"])
        audit_keys = [k for k in summary if k.endswith("_audit")]
        self.assertGreaterEqual(len(audit_keys), 20)

    # ---- Pillar 1: C2PA 2.1 & cnflasha Key-Vault Firewall ----

    def test_11_jumbf_build_and_parse_with_hw_sig(self) -> None:
        blob = build_c2pa_jumbf_box(include_hardware_cose_sig=True)
        summary = parse_c2pa_jumbf_box(blob)
        self.assertTrue(summary.valid, summary.errors)
        self.assertEqual(summary.box_type, "jumb")
        self.assertEqual(summary.jumd_uuid_hex, C2PA_JUMBF_UUID_HEX)
        self.assertEqual(summary.manifest_label, "lc2pa.createdlsony.created")
        self.assertEqual(summary.claim_generator, "ILME-FX3/7.02")
        self.assertEqual(summary.action_name, "c2pa.created")
        self.assertEqual(len(summary.hard_binding_sha256_hex), 64)
        self.assertTrue(summary.cose_hardware_sig_present)
        self.assertEqual(C2PA_SPEC_VERSION, "2.1")
        self.assertIn("c2cs", C2PA_JUMBF_BOX_TYPES)

    def test_12_jumbf_rejects_malformed_or_truncated_box(self) -> None:
        s_short = parse_c2pa_jumbf_box(b"jumb")
        self.assertFalse(s_short.valid)
        s_bad_uuid = parse_c2pa_jumbf_box(
            build_c2pa_jumbf_box().replace(bytes.fromhex(C2PA_JUMBF_UUID_HEX), b"\x00" * 16, 1)
        )
        self.assertFalse(s_bad_uuid.valid)

    def test_13_stock_fx3_mp4_readonly_cnflasha_passes(self) -> None:
        ev = evaluate_c2pa_keyvault_firewall(
            build_mode="STOCK_FX3_FIRMWARE",
            camera_body="FX3",
            container_format="MP4",
            bitrate_mbps=C2PA_SUPPORTED_MP4_MAX_BITRATE_MBPS,
            sq_mode_active=False,
            rq_lic_count=C2PA_MAX_LICENSES_PER_RQ_LIC_FX3,
            keyvault_target_path="/dev/cnflasha0",
            keyvault_mount_mode=CNFLASHA_KEYVAULT_MOUNT_MODE,
        )
        self.assertTrue(ev.valid, ev.errors)
        self.assertEqual(ev.status, "VALID_STOCK_C2PA_READONLY_KEYVAULT")
        self.assertTrue(ev.c2pa_hardware_signature_written)
        self.assertFalse(ev.clean_room_research_marked)
        self.assertEqual(ev.keyvault_writes, 0)
        self.assertEqual(ev.key_extraction_attempts, 0)

    def test_14_stageb_overlay_transparently_marked_unsigned(self) -> None:
        ev = evaluate_c2pa_keyvault_firewall(
            build_mode="STAGE_B_USERLAND_OVERLAY",
            camera_body="FX3",
            container_format="MP4",
            bitrate_mbps=300.0,
            keyvault_target_path="/dev/cnflasha0",
            keyvault_mount_mode="O_RDONLY",
            attempt_forge_c2pa_hw_signature=False,
        )
        self.assertTrue(ev.valid, ev.errors)
        self.assertEqual(ev.status, "VALID_STAGE_B_TRANSPARENT_UNSIGNED_OVERLAY")
        self.assertFalse(ev.c2pa_hardware_signature_written)
        self.assertTrue(ev.clean_room_research_marked)
        self.assertEqual(ev.overlay_disclaimer, STAGE_B_CLEAN_ROOM_RESEARCH_LABEL)
        self.assertFalse(ev.jumbf_summary.cose_hardware_sig_present)

    def test_15_blocks_cnflasha_rdwr_and_write_attempts(self) -> None:
        ev = evaluate_c2pa_keyvault_firewall(
            build_mode="STAGE_B_USERLAND_OVERLAY",
            camera_body="FX3",
            keyvault_target_path="/dev/cnflasha0",
            keyvault_mount_mode="O_RDWR",
            requested_keyvault_writes=512,
        )
        self.assertFalse(ev.valid)
        self.assertEqual(ev.status, "BLOCKED_CNFLASHA_RPMB_KEYVAULT_MUTATION")

    def test_16_blocks_rpmb_and_p12_cert_key_extraction(self) -> None:
        for target in ("/dev/mmcblk0rpmb", "p12:/cert", "RQ_LIC.DAT"):
            ev = evaluate_c2pa_keyvault_firewall(
                build_mode="STAGE_B_USERLAND_OVERLAY",
                camera_body="FX3",
                keyvault_target_path=target,
                keyvault_mount_mode="O_RDONLY",
                requested_key_extractions=1,
            )
            self.assertFalse(ev.valid, f"Expected block for {target}")
            self.assertEqual(ev.status, "BLOCKED_CNFLASHA_RPMB_KEYVAULT_MUTATION")

    def test_17_blocks_forged_c2cs_signature_on_stageb_overlay(self) -> None:
        ev = evaluate_c2pa_keyvault_firewall(
            build_mode="STAGE_B_USERLAND_OVERLAY",
            camera_body="FX3",
            attempt_forge_c2pa_hw_signature=True,
        )
        self.assertFalse(ev.valid)
        self.assertEqual(ev.status, "BLOCKED_FORGED_C2PA_SIGNATURE_ON_STAGE_B_OVERLAY")
        self.assertFalse(ev.c2pa_hardware_signature_written)

    def test_18_blocks_cross_body_certificate_spoofing(self) -> None:
        ev = evaluate_c2pa_keyvault_firewall(
            build_mode="STOCK_FX3_FIRMWARE",
            camera_body="FX6",
            cert_body_origin="FX3",
        )
        self.assertFalse(ev.valid)
        self.assertTrue(ev.cross_body_cert_spoof_blocked)
        self.assertEqual(ev.status, "BLOCKED_CROSS_BODY_CERT_SPOOF")

    def test_19_blocks_over_222mbps_mp4_and_sq_mode(self) -> None:
        ev_bw = evaluate_c2pa_keyvault_firewall(
            build_mode="STOCK_FX3_FIRMWARE",
            camera_body="FX3",
            container_format="MP4",
            bitrate_mbps=222.1,
        )
        self.assertFalse(ev_bw.valid)
        self.assertEqual(ev_bw.status, "BLOCKED_C2PA_BITRATE_LIMIT")

        ev_sq = evaluate_c2pa_keyvault_firewall(
            build_mode="STOCK_FX3_FIRMWARE",
            camera_body="FX3",
            container_format="MP4",
            bitrate_mbps=100.0,
            sq_mode_active=True,
        )
        self.assertFalse(ev_sq.valid)
        self.assertEqual(ev_sq.status, "BLOCKED_C2PA_SQ_MODE_UNSUPPORTED")

    def test_20_blocks_over_100_licenses_in_rq_lic_dat(self) -> None:
        ev = evaluate_c2pa_keyvault_firewall(
            build_mode="STOCK_FX3_FIRMWARE",
            camera_body="FX3",
            rq_lic_count=101,
        )
        self.assertFalse(ev.valid)
        self.assertEqual(ev.status, "BLOCKED_RQ_LIC_PACKAGE_LIMIT")

    # ---- Pillar 2: E-Mount Lens Shading, Lateral CA & Distortion ----

    def test_21_cos4_vignetting_gain_modes_and_clamp(self) -> None:
        nat0, g0 = compute_cos4_vignetting_gain(0.0, 32.5, 0.14, "AUTO")
        nat_mid, g_mid = compute_cos4_vignetting_gain(0.5, 32.5, 0.14, "AUTO")
        nat_c, g_c = compute_cos4_vignetting_gain(1.0, 32.5, 0.14, "AUTO")
        self.assertAlmostEqual(nat0, 1.0, places=9)
        self.assertAlmostEqual(g0, 1.0, places=9)
        self.assertGreater(g_c, g_mid)
        self.assertGreater(g_mid, g0)
        self.assertLessEqual(g_c, SHADING_MAX_DIGITAL_GAIN)
        self.assertAlmostEqual(nat_c * g_c, 1.0, places=6)

        _, g_low = compute_cos4_vignetting_gain(1.0, 32.5, 0.14, "AUTO_LOW")
        _, g_off = compute_cos4_vignetting_gain(1.0, 32.5, 0.14, "OFF")
        self.assertAlmostEqual(g_off, 1.0, places=9)
        self.assertGreater(g_c, g_low)
        self.assertGreater(g_low, 1.0)
        with self.assertRaises(ValueError):
            compute_cos4_vignetting_gain(1.0, 20.0, 0.1, "INVALID_MODE")

    def test_22_gm_1635_wide_barrel_compensation_bounds(self) -> None:
        ev = evaluate_emount_lens_compensation("SEL1635GM2_16MM", shading_mode="AUTO")
        self.assertTrue(ev.valid, ev.errors)
        self.assertTrue(ev.mount_pins_detected)
        self.assertFalse(ev.identity_failsafe_active)
        self.assertLess(ev.corner_uniformity_error, 1e-6)
        self.assertGreaterEqual(ev.ca_reduction_ratio, LATERAL_CA_MIN_REDUCTION_RATIO)
        self.assertLessEqual(abs(ev.ca_r_residual_px), LATERAL_CA_MAX_RESIDUAL_PX)
        self.assertLessEqual(abs(ev.ca_b_residual_px), LATERAL_CA_MAX_RESIDUAL_PX)
        self.assertLess(ev.distorted_r_norm, ev.distortion_test_r_norm)  # barrel
        self.assertLess(ev.distortion_inversion_residual, DISTORTION_INVERSION_MAX_RESIDUAL)

    def test_23_gm_50_standard_auto_low_compensation(self) -> None:
        ev = evaluate_emount_lens_compensation("SEL50F12GM", shading_mode="AUTO_LOW")
        self.assertTrue(ev.valid, ev.errors)
        self.assertEqual(ev.shading_mode, "AUTO_LOW")
        self.assertGreater(ev.shading_gain_corner, 1.0)
        self.assertLess(ev.distortion_inversion_residual, DISTORTION_INVERSION_MAX_RESIDUAL)

    def test_24_gm_70200_tele_pincushion_compensation(self) -> None:
        ev = evaluate_emount_lens_compensation("SEL70200GM2_200MM", shading_mode="AUTO")
        self.assertTrue(ev.valid, ev.errors)
        self.assertGreater(ev.distorted_r_norm, ev.distortion_test_r_norm)  # pincushion
        self.assertLess(ev.distortion_inversion_residual, DISTORTION_INVERSION_MAX_RESIDUAL)

    def test_25_lateral_ca_radial_shift_zero_at_optical_axis(self) -> None:
        self.assertEqual(compute_lateral_ca_radial_shift(0.0, -0.00145, 0.00028), 0.0)
        shift = compute_lateral_ca_radial_shift(1.0, -0.00145, 0.00028)
        self.assertLess(shift, 0.0)

    def test_26_radial_distortion_newton_raphson_roundtrip(self) -> None:
        for r in (0.15, 0.5, 0.85, 1.0):
            for k1, k2 in ((-0.072, 0.011), (0.038, -0.004)):
                r_d = apply_radial_distortion(r, k1, k2)
                r_rec = invert_radial_distortion(r_d, k1, k2)
                self.assertLess(abs(r_rec - r), 1e-11)

    def test_27_unchipped_pl_and_anamorphic_strict_identity_1x_failsafe(self) -> None:
        for lens_id in ("UNCHIPPED_PL_CINE_PRIME", "MANUAL_ANAMORPHIC_2X"):
            ev = evaluate_emount_lens_compensation(
                lens_id, shading_mode="AUTO", ca_comp_enabled=True, distortion_comp_enabled=True
            )
            self.assertTrue(ev.valid, ev.errors)
            self.assertFalse(ev.mount_pins_detected)
            self.assertTrue(ev.identity_failsafe_active)
            self.assertEqual(ev.shading_mode, "IDENTITY_1X")
            self.assertFalse(ev.ca_comp_enabled)
            self.assertFalse(ev.distortion_comp_enabled)
            self.assertEqual(ev.shading_gain_center, 1.0)
            self.assertEqual(ev.shading_gain_mid, 1.0)
            self.assertEqual(ev.shading_gain_corner, 1.0)
            self.assertEqual(ev.distorted_r_norm, ev.distortion_test_r_norm)
            self.assertEqual(ev.recovered_r_norm, ev.distortion_test_r_norm)

    def test_28_blocks_stale_electronic_coefficients_on_unchipped_lens(self) -> None:
        for lens_id in ("UNCHIPPED_PL_CINE_PRIME", "MANUAL_ANAMORPHIC_2X"):
            ev = evaluate_emount_lens_compensation(lens_id, force_stale_coefficients=True)
            self.assertFalse(ev.valid)
            self.assertTrue(ev.stale_coeff_leak_detected)
            self.assertFalse(ev.identity_failsafe_active)
            self.assertEqual(ev.status, "BLOCKED_STALE_ELECTRONIC_LENS_COEFF_ON_UNCHIPPED_LENS")
        self.assertIn("SEL1635GM2_16MM", EMOUNT_LENS_PROFILES)

    # ---- Pillar 3: Sony Monitor & Control Wired USB-LAN PTP-IP Multi-Cam ----

    def test_29_ptpip_packet_build_and_parse_roundtrip(self) -> None:
        guid = b"\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10"
        pkt = build_ptpip_init_packet(
            packet_type=PTPIP_PKT_INIT_EVENT_REQ,
            guid_bytes=guid,
            friendly_name="Sony-MC-iPad",
        )
        ptype, pguid, pname, pver = parse_ptpip_init_packet(pkt)
        self.assertEqual(ptype, PTPIP_PKT_INIT_EVENT_REQ)
        self.assertEqual(pguid, guid)
        self.assertEqual(pname, "Sony-MC-iPad")
        self.assertEqual(pver, PTPIP_PROTOCOL_VERSION)

    def test_30_ptpip_rejects_bad_guid_or_truncated_packet(self) -> None:
        with self.assertRaises(ValueError):
            build_ptpip_init_packet(guid_bytes=b"short")
        with self.assertRaises(ValueError):
            parse_ptpip_init_packet(b"\x08\x00\x00\x00\x01\x00\x00\x00")

    def test_31_default_4cam_wired_ptpip_fleet_p12_isolated(self) -> None:
        fleet = build_default_4cam_mc_fleet()
        ev = evaluate_mc_wired_fleet_matrix(fleet)
        self.assertTrue(ev.valid, ev.errors)
        self.assertEqual(ev.camera_count, MC_FREE_PLAN_MAX_CAMERAS)
        self.assertLessEqual(ev.total_fleet_bandwidth_mbps, MC_USB_LAN_PRACTICAL_CAP_MBPS)
        self.assertLessEqual(ev.max_gang_rec_skew_ms, MC_GANG_REC_MAX_SKEW_MS)
        self.assertTrue(ev.access_auth_all_verified)
        self.assertTrue(ev.false_color_synced)
        self.assertTrue(ev.waveform_synced)
        self.assertTrue(ev.focus_map_synced)
        self.assertTrue(ev.gang_rec_triggered)
        self.assertTrue(ev.p12_airplane_mode_on)
        self.assertFalse(ev.wifi_rf_enabled)
        self.assertFalse(ev.bt_rf_enabled)
        self.assertEqual(ev.hci_tx_packets, 0)
        self.assertEqual(ev.wf12_00342260_hits, 0)

    def test_32_blocks_unsupported_direct_ethernet_and_fx6_usb_tether(self) -> None:
        fleet = build_default_4cam_mc_fleet()
        for topo in ("DIRECT_ETHERNET_NO_ROUTER", "FX6_USB_TETHER_IPADOS"):
            ev = evaluate_mc_wired_fleet_matrix(fleet, topology=topo)
            self.assertFalse(ev.valid)
            self.assertEqual(ev.status, "BLOCKED_UNSUPPORTED_MC_TOPOLOGY")

    def test_33_blocks_over_4cam_on_free_plan_and_allows_5cam_on_premium(self) -> None:
        fleet5 = build_default_4cam_mc_fleet() + (
            McFleetCameraNode(
                cam_id="CAM_E",
                camera_body="FX3",
                ip_address="192.168.50.105",
                nic_driver="CDC_NCM_RTL8153",
                access_auth_enabled=True,
                ptpip_port=PTPIP_TCP_PORT,
                telemetry_bitrate_mbps=8.2,
                false_color_enabled=True,
                waveform_enabled=True,
                focus_map_enabled=True,
                gang_rec_skew_ms=5.0,
            ),
        )
        ev_free = evaluate_mc_wired_fleet_matrix(fleet5, plan_tier="FREE_4CAM")
        self.assertFalse(ev_free.valid)
        self.assertEqual(ev_free.status, "BLOCKED_MC_PLAN_CAMERA_LIMIT")

        ev_prem = evaluate_mc_wired_fleet_matrix(fleet5, plan_tier="PREMIUM_20CAM")
        self.assertTrue(ev_prem.valid, ev_prem.errors)

    def test_34_blocks_p12_rf_or_wf12_violation(self) -> None:
        fleet = build_default_4cam_mc_fleet()
        for kwargs in (
            {"p12_airplane_mode_on": False},
            {"wifi_rf_enabled": True},
            {"bt_rf_enabled": True},
            {"hci_tx_packets": 1},
            {"wf12_00342260_hits": 1},
        ):
            ev = evaluate_mc_wired_fleet_matrix(fleet, **kwargs)  # type: ignore[arg-type]
            self.assertFalse(ev.valid, f"Expected P12 RF block for {kwargs}")
            self.assertEqual(ev.status, "BLOCKED_P12_RF_OR_WF12_VIOLATION")

    def test_35_blocks_unauthenticated_ptpip_and_unverified_nic(self) -> None:
        fleet = build_default_4cam_mc_fleet()
        bad_auth = McFleetCameraNode(
            cam_id="CAM_A",
            camera_body="FX3",
            ip_address="192.168.50.101",
            nic_driver="CDC_NCM_RTL8153",
            access_auth_enabled=False,
            ptpip_port=PTPIP_TCP_PORT,
            telemetry_bitrate_mbps=8.2,
            false_color_enabled=True,
            waveform_enabled=True,
            focus_map_enabled=True,
            gang_rec_skew_ms=4.1,
        )
        ev_auth = evaluate_mc_wired_fleet_matrix((bad_auth,) + fleet[1:])
        self.assertFalse(ev_auth.valid)
        self.assertEqual(ev_auth.status, "BLOCKED_UNAUTHENTICATED_PTPIP_SESSION")

        bad_nic = McFleetCameraNode(
            cam_id="CAM_A",
            camera_body="FX3",
            ip_address="192.168.50.101",
            nic_driver="UNSUPPORTED_AQUANTIA_10G",
            access_auth_enabled=True,
            ptpip_port=PTPIP_TCP_PORT,
            telemetry_bitrate_mbps=8.2,
            false_color_enabled=True,
            waveform_enabled=True,
            focus_map_enabled=True,
            gang_rec_skew_ms=4.1,
        )
        ev_nic = evaluate_mc_wired_fleet_matrix((bad_nic,) + fleet[1:])
        self.assertFalse(ev_nic.valid)
        self.assertEqual(ev_nic.status, "BLOCKED_UNVERIFIED_NIC_DRIVER")

    def test_36_blocks_duplicate_ip_bandwidth_overflow_and_gang_skew(self) -> None:
        fleet = build_default_4cam_mc_fleet()
        dup_cam = McFleetCameraNode(
            cam_id="CAM_X",
            camera_body="FX3",
            ip_address=fleet[1].ip_address,
            nic_driver="CDC_NCM_RTL8153",
            access_auth_enabled=True,
            ptpip_port=PTPIP_TCP_PORT,
            telemetry_bitrate_mbps=8.2,
            false_color_enabled=True,
            waveform_enabled=True,
            focus_map_enabled=True,
            gang_rec_skew_ms=4.1,
        )
        self.assertFalse(evaluate_mc_wired_fleet_matrix((dup_cam,) + fleet[1:]).valid)

        high_bw = McFleetCameraNode(
            cam_id="CAM_BW",
            camera_body="FX3",
            ip_address="192.168.50.110",
            nic_driver="CDC_NCM_RTL8153",
            access_auth_enabled=True,
            ptpip_port=PTPIP_TCP_PORT,
            telemetry_bitrate_mbps=310.0,
            false_color_enabled=True,
            waveform_enabled=True,
            focus_map_enabled=True,
            gang_rec_skew_ms=4.0,
        )
        self.assertFalse(evaluate_mc_wired_fleet_matrix((high_bw,)).valid)

        high_skew = McFleetCameraNode(
            cam_id="CAM_SK",
            camera_body="FX3",
            ip_address="192.168.50.111",
            nic_driver="CDC_NCM_RTL8153",
            access_auth_enabled=True,
            ptpip_port=PTPIP_TCP_PORT,
            telemetry_bitrate_mbps=8.0,
            false_color_enabled=True,
            waveform_enabled=True,
            focus_map_enabled=True,
            gang_rec_skew_ms=25.0,
        )
        self.assertFalse(evaluate_mc_wired_fleet_matrix((high_skew,)).valid)

    # ---- Pillar 4: Per-Body Factory Shading & Defect-Pixel Immutability ----

    def test_37_factory_shading_digests_bit_exact_and_zero_mutations(self) -> None:
        rep = analyze_c2pa_lens_shading_and_mc_fleet(clean_room=True)
        p4 = rep.pillar_4_factory_shading_immutability
        self.assertTrue(p4.passed, p4.errors)
        self.assertTrue(p4.fx3_global_xdb_valid)
        self.assertTrue(p4.fx6_global_xdb_valid)
        self.assertTrue(p4.bit_exact_preservation_verified)
        self.assertEqual(p4.factory_digests_before, p4.factory_digests_after)
        self.assertEqual(len(p4.factory_digests_before), len(FACTORY_CALIBRATION_FILES))
        self.assertEqual(p4.calibration_mutation_bytes, 0)
        self.assertEqual(p4.emmc_mutation_bytes, 0)
        self.assertFalse(p4.persistent_emmc_writes_authorized)

    def test_38_volatile_ram_staging_allowed_for_tmp_and_ram(self) -> None:
        for path in ("/tmp/fx3_stageb_lens_shading_lut.bin", "ram://lens_ca_poly_cache"):
            ev = evaluate_factory_shading_write_guard(path)
            self.assertTrue(ev.valid, ev.errors)
            self.assertTrue(ev.volatile_ram_staged)
            self.assertEqual(ev.calibration_mutation_bytes, 0)
            self.assertEqual(ev.emmc_mutation_bytes, 0)
            self.assertFalse(ev.persistent_emmc_writes_authorized)

    def test_39_blocks_all_persistent_factory_shading_defdet_and_emmc_paths(self) -> None:
        forbidden_targets = (
            "p2:/setting/psd.bin",
            "p2:/setting/defdet.bin",
            "p2:/setting/Backup.bin",
            "p6:/tmp/jiritsu",
            "p18:/lens/lensfile.bin",
            "p12:/cert",
            "/dev/cnflasha0",
            "/dev/mmcblk0p2",
            "/tmp/../nflasha2/setting/psd.bin",
        )
        for target in forbidden_targets:
            ev = evaluate_factory_shading_write_guard(target)
            self.assertFalse(ev.valid, f"Expected persistent target block for {target}")
            self.assertFalse(ev.volatile_ram_staged)
            self.assertEqual(ev.status, "BLOCKED_PERSISTENT_TARGET")
            self.assertEqual(ev.calibration_mutation_bytes, 0)
            self.assertEqual(ev.emmc_mutation_bytes, 0)
            self.assertFalse(ev.persistent_emmc_writes_authorized)

    def test_40_unknown_lens_profile_fails_closed(self) -> None:
        ev = evaluate_emount_lens_compensation("NONEXISTENT_LENS_XYZ")
        self.assertFalse(ev.valid)
        self.assertEqual(ev.status, "UNKNOWN_LENS_PROFILE")


if __name__ == "__main__":
    unittest.main()
