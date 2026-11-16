"""Unit tests for Phase 31 IMX510 sensor, Dual Base ISO, HDMI RAW, and XAVC compatibility verifier.

Runs in BOTH Local Donor mode (`O_RDONLY`) and `FX3_FX6_FORCE_CLEAN_ROOM=1` mode,
keeping the combined `fx3-firmware-lab` test suite (75 tests) under 4 seconds.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from typing import Optional
from unittest.mock import patch

from fx3_firmware_lab.__main__ import main as cli_main, run_audit_all
from fx3_firmware_lab.haita_bk4_feature_analyzer import is_forced_clean_room
from fx3_firmware_lab.sensor_codec_compatibility_analyzer import (
    CP_IMX510_DRIVER_MARKERS,
    CP_SHARED_SENSOR_LIROSEQ_MARKERS,
    FX3_APPFW_DUAL_BASE_ISO_MARKERS,
    FX6_APPFW_DUAL_BASE_ISO_MARKERS,
    MPR_FX6_MXF_MUX_MARKERS,
    MPR_SHARED_H264_INTRA_PROFILES,
    MPR_SHARED_H264_LONG_PROFILES,
    MPR_SHARED_HEVC_PROFILES,
    MPR_SHARED_MOVIE_REC_PARAM_CLASSES,
    OPEN_GATE_FX6_APPFW_STRINGS,
    PHASE_31_SCHEMA,
    SensorCodecCompatibilityReport,
    analyze_sensor_and_codec_compatibility,
    build_clean_room_sensor_codec_fixtures,
)


PKG_ROOT = Path(__file__).resolve().parents[1]


class TestActiveSensorAndCodecCompatibility(unittest.TestCase):
    _active_report: Optional[SensorCodecCompatibilityReport] = None

    @classmethod
    def setUpClass(cls) -> None:
        cls._active_report = analyze_sensor_and_codec_compatibility()

    def test_active_mode_passes_with_deterministic_sha256(self) -> None:
        rep = self._active_report
        assert rep is not None
        self.assertTrue(rep.all_checks_passed, msg=f"Errors: {rep.errors}")
        self.assertEqual(rep.schema_version, PHASE_31_SCHEMA)
        self.assertEqual(len(rep.report_sha256), 64)
        self.assertEqual(len(rep.donor_file_sizes), 6)
        if not is_forced_clean_room() and rep.mode == "LOCAL_DONOR_VERIFIED":
            self.assertGreater(rep.donor_file_sizes["fx3_appfw"], 50_000_000)
            self.assertGreater(rep.donor_file_sizes["fx6_appfw"], 40_000_000)
            self.assertGreater(rep.donor_file_sizes["fx3_libmpr"], 3_000_000)
            self.assertGreater(rep.donor_file_sizes["fx6_libmpr"], 20_000_000)
            self.assertGreater(rep.donor_file_sizes["fx3_cpapp"], 10_000_000)
            self.assertGreater(rep.donor_file_sizes["fx6_cpapp"], 10_000_000)

    def test_imx510_sensor_identity_and_shared_cp_liroseq(self) -> None:
        rep = self._active_report
        assert rep is not None
        sm = rep.sensor_matrix
        self.assertTrue(sm.passed)
        self.assertEqual(sm.sensor_id, "IMX510")
        self.assertEqual(sm.effective_resolution, "4264x2408")
        self.assertEqual(sm.fx3_cp_imx510_markers, CP_IMX510_DRIVER_MARKERS)
        self.assertEqual(sm.fx6_cp_imx510_markers, CP_IMX510_DRIVER_MARKERS)
        self.assertEqual(sm.shared_cp_liroseq_keys, CP_SHARED_SENSOR_LIROSEQ_MARKERS)

    def test_dual_base_iso_800_and_12800_parity(self) -> None:
        rep = self._active_report
        assert rep is not None
        sm = rep.sensor_matrix
        self.assertEqual(sm.dual_base_iso_bases, (800, 12800))
        self.assertEqual(sm.fx3_appfw_dual_base_iso_markers, FX3_APPFW_DUAL_BASE_ISO_MARKERS)
        self.assertEqual(sm.fx6_appfw_dual_base_iso_markers, FX6_APPFW_DUAL_BASE_ISO_MARKERS)

    def test_scan_mode_matrix_4k_dci_qfhd_fhd_sq_and_hdmi_raw(self) -> None:
        rep = self._active_report
        assert rep is not None
        by_id = {e.mode_id: e for e in rep.sensor_matrix.scan_mode_matrix}
        for mid in ("IMX510_FF_4K_DCI", "IMX510_FF_QFHD_4K", "IMX510_FHD_1080P", "IMX510_HDMI_16BIT_RAW"):
            self.assertIn(mid, by_id)
            self.assertTrue(by_id[mid].fx3_supported)
            self.assertTrue(by_id[mid].fx6_supported)
            self.assertTrue(by_id[mid].encoder_backed)
        self.assertEqual(len(rep.sensor_matrix.fx3_sq_hfr_markers), 3)
        self.assertEqual(len(rep.sensor_matrix.fx6_sq_hfr_markers), 3)

    def test_open_gate_5016x3344_negative_proof_both_bodies(self) -> None:
        rep = self._active_report
        assert rep is not None
        sm = rep.sensor_matrix
        self.assertFalse(sm.open_gate_5016x3344_supported)
        self.assertTrue(sm.open_gate_encoder_absence_proven)
        self.assertEqual(sm.open_gate_fx6_appfw_strings_present, OPEN_GATE_FX6_APPFW_STRINGS)
        self.assertEqual(sm.open_gate_fx3_appfw_strings_present, ())
        self.assertEqual(sm.open_gate_libmpr_hits_fx3, ())
        self.assertEqual(sm.open_gate_libmpr_hits_fx6, ())
        self.assertEqual(sm.open_gate_cp_hits_fx3, ())
        self.assertEqual(sm.open_gate_cp_hits_fx6, ())

    def test_mpr_shared_api_and_movie_rec_param_classes(self) -> None:
        rep = self._active_report
        assert rep is not None
        mpr = rep.mpr_encoder_matrix
        self.assertTrue(mpr.passed)
        self.assertEqual(mpr.shared_movie_rec_param_classes, MPR_SHARED_MOVIE_REC_PARAM_CLASSES)
        self.assertEqual(mpr.fx3_mpr_api_symbols, mpr.fx6_mpr_api_symbols)

    def test_xavc_i_and_xavc_si_share_identical_h422ip_hw_engine(self) -> None:
        rep = self._active_report
        assert rep is not None
        mpr = rep.mpr_encoder_matrix
        self.assertTrue(mpr.xavc_i_and_xavc_si_hw_engine_identical)
        self.assertEqual(mpr.shared_h264_intra_profiles, MPR_SHARED_H264_INTRA_PROFILES)
        self.assertEqual(mpr.shared_h264_long_profiles, MPR_SHARED_H264_LONG_PROFILES)
        self.assertEqual(mpr.shared_hevc_profiles, MPR_SHARED_HEVC_PROFILES)
        self.assertEqual(mpr.fx6_mxf_mux_markers, MPR_FX6_MXF_MUX_MARKERS)
        self.assertEqual(mpr.fx3_mxf_mux_markers_unexpected, ())

        by_codec = {c.codec_id: c for c in mpr.codec_matrix}
        self.assertEqual(by_codec["XAVC-I"].verdict, "SHARED_HW_ENGINE_MXF_MUX_FX6_ONLY")
        self.assertEqual(by_codec["XAVC S-I"].verdict, "FULLY_SHARED_BITSTREAM_AND_MP4")
        self.assertEqual(by_codec["XAVC HS"].verdict, "FULLY_SHARED_BITSTREAM_AND_MP4")
        self.assertEqual(by_codec["X-OCN LT (5016x3344)"].verdict, "UNSUPPORTED_ENCODER_ABSENT_BOTH_BODIES")

    def test_dual_cfexpress_sdxc_slot_parity(self) -> None:
        rep = self._active_report
        assert rep is not None
        sv = rep.media_slot_and_video_output
        self.assertTrue(sv.passed)
        self.assertTrue(sv.dual_cfexpress_sdxc_parity_ok)
        self.assertEqual(sv.slot_parity_verdict, "DUAL_CFEXPRESS_TYPE_A_SDXC_PARITY_VERIFIED")
        self.assertIn("SLOT_A", sv.fx6_dual_slot_markers)
        self.assertIn("SLOT_B", sv.fx6_dual_slot_markers)
        self.assertIn("MEDIA_SLOT_1", sv.fx3_dual_slot_markers)
        self.assertIn("MEDIA_SLOT_2", sv.fx3_dual_slot_markers)

    def test_sdi_absent_graceful_hdmi_fallback_non_blocking(self) -> None:
        rep = self._active_report
        assert rep is not None
        sv = rep.media_slot_and_video_output
        self.assertTrue(sv.sdi_absent_graceful_hdmi_fallback_non_blocking)
        self.assertEqual(sv.video_output_verdict, "SDI_ABSENT_GRACEFUL_HDMI_FALLBACK_NON_BLOCKING")
        self.assertEqual(sv.fx3_appfw_sdi_markers_unexpected, ())
        self.assertEqual(sv.fx3_cp_sdi_markers_unexpected, ())
        self.assertTrue(sv.fx3_cp_hdmi_present)
        self.assertTrue(sv.fx6_cp_hdmi_present)


class TestCleanRoomAndFaultInjectionGuards(unittest.TestCase):
    def test_clean_room_forced_returns_synthetic_verified(self) -> None:
        rep1 = analyze_sensor_and_codec_compatibility(clean_room=True)
        rep2 = analyze_sensor_and_codec_compatibility(
            env={"FX3_FX6_FORCE_CLEAN_ROOM": "1"}
        )
        self.assertEqual(rep1.mode, "CLEAN_ROOM_SYNTHETIC_VERIFIED")
        self.assertEqual(rep2.mode, "CLEAN_ROOM_SYNTHETIC_VERIFIED")
        self.assertTrue(rep1.all_checks_passed)
        self.assertEqual(rep1.report_sha256, rep2.report_sha256)

    def test_env_force_clean_room_never_opens_donors(self) -> None:
        with patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            rep = analyze_sensor_and_codec_compatibility()
            self.assertEqual(rep.mode, "CLEAN_ROOM_SYNTHETIC_VERIFIED")
            self.assertLess(rep.donor_file_sizes["fx3_appfw"], 4096)

    def test_guard_rejects_missing_imx510_cp_driver(self) -> None:
        bad = build_clean_room_sensor_codec_fixtures(drop_imx510_cp=True)
        rep = analyze_sensor_and_codec_compatibility(synthetic_overrides=bad)
        self.assertFalse(rep.all_checks_passed)
        self.assertFalse(rep.sensor_matrix.passed)

    def test_guard_rejects_missing_dual_base_iso(self) -> None:
        bad = build_clean_room_sensor_codec_fixtures(drop_dual_base_iso=True)
        rep = analyze_sensor_and_codec_compatibility(synthetic_overrides=bad)
        self.assertFalse(rep.all_checks_passed)
        self.assertFalse(rep.sensor_matrix.passed)

    def test_guard_detects_unexpected_open_gate_in_libmpr(self) -> None:
        bad = build_clean_room_sensor_codec_fixtures(inject_open_gate_in_libmpr=True)
        rep = analyze_sensor_and_codec_compatibility(synthetic_overrides=bad)
        self.assertFalse(rep.all_checks_passed)
        self.assertFalse(rep.sensor_matrix.open_gate_encoder_absence_proven)

    def test_guard_rejects_missing_h264_intra_profile(self) -> None:
        bad = build_clean_room_sensor_codec_fixtures(drop_mpr_h422_profile=True)
        rep = analyze_sensor_and_codec_compatibility(synthetic_overrides=bad)
        self.assertFalse(rep.all_checks_passed)
        self.assertFalse(rep.mpr_encoder_matrix.xavc_i_and_xavc_si_hw_engine_identical)

    def test_guard_rejects_unexpected_mxf_in_fx3_libmpr(self) -> None:
        bad = build_clean_room_sensor_codec_fixtures(inject_mxf_in_fx3_mpr=True)
        rep = analyze_sensor_and_codec_compatibility(synthetic_overrides=bad)
        self.assertFalse(rep.all_checks_passed)
        self.assertGreater(len(rep.mpr_encoder_matrix.fx3_mxf_mux_markers_unexpected), 0)

    def test_guard_rejects_missing_fx3_dual_slot(self) -> None:
        bad = build_clean_room_sensor_codec_fixtures(drop_fx3_dual_slot=True)
        rep = analyze_sensor_and_codec_compatibility(synthetic_overrides=bad)
        self.assertFalse(rep.all_checks_passed)
        self.assertFalse(rep.media_slot_and_video_output.dual_cfexpress_sdxc_parity_ok)

    def test_guard_detects_unexpected_sdi_fpga_in_fx3_cp(self) -> None:
        bad = build_clean_room_sensor_codec_fixtures(inject_sdi_fpga_in_fx3_cp=True)
        rep = analyze_sensor_and_codec_compatibility(synthetic_overrides=bad)
        self.assertFalse(rep.all_checks_passed)
        self.assertFalse(
            rep.media_slot_and_video_output.sdi_absent_graceful_hdmi_fallback_non_blocking
        )

    def test_guard_rejects_missing_cp_hdmi(self) -> None:
        bad = build_clean_room_sensor_codec_fixtures()
        bad["fx3_cpapp"] = bad["fx3_cpapp"].replace(b"HDMI", b"XXXX")
        rep = analyze_sensor_and_codec_compatibility(synthetic_overrides=bad)
        self.assertFalse(rep.all_checks_passed)
        self.assertFalse(rep.media_slot_and_video_output.fx3_cp_hdmi_present)

    def test_guard_rejects_missing_sq_240p_marker(self) -> None:
        bad = build_clean_room_sensor_codec_fixtures()
        bad["fx3_appfw"] = bad["fx3_appfw"].replace(b"FRAME_RATE_240P", b"FRAME_RATE_NONE")
        rep = analyze_sensor_and_codec_compatibility(synthetic_overrides=bad)
        self.assertFalse(rep.all_checks_passed)
        self.assertFalse(rep.sensor_matrix.passed)

    def test_guard_rejects_missing_movie_rec_param_class(self) -> None:
        bad = build_clean_room_sensor_codec_fixtures()
        bad["fx3_libmpr"] = bad["fx3_libmpr"].replace(b"AVC_Intra_4KEN3mpr13movieRecParamE", b"BROKEN")
        rep = analyze_sensor_and_codec_compatibility(synthetic_overrides=bad)
        self.assertFalse(rep.all_checks_passed)
        self.assertFalse(rep.mpr_encoder_matrix.passed)

    def test_source_read_only_compliance_and_no_embedded_keys(self) -> None:
        src_path = PKG_ROOT / "fx3_firmware_lab" / "sensor_codec_compatibility_analyzer.py"
        src = src_path.read_text(encoding="utf-8")
        for forbidden in ("O_WRONLY", "O_RDWR", '"wb"', "'wb'", "CXD90057_k8", "BEGIN RSA PRIVATE KEY"):
            self.assertNotIn(forbidden, src)


class TestSensorCodecCliAndIntegration(unittest.TestCase):
    def test_cli_audit_sensor_codec_clean_room_deterministic_json(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONPATH"] = str(PKG_ROOT)
        proc1 = subprocess.run(
            [sys.executable, "-B", "-m", "fx3_firmware_lab", "audit-sensor-codec", "--clean-room"],
            capture_output=True,
            text=True,
            env=env,
            check=True,
        )
        proc2 = subprocess.run(
            [sys.executable, "-B", "-m", "fx3_firmware_lab", "audit-sensor-codec", "--clean-room"],
            capture_output=True,
            text=True,
            env=env,
            check=True,
        )
        self.assertEqual(proc1.stdout, proc2.stdout)
        parsed = json.loads(proc1.stdout)
        self.assertTrue(parsed["all_checks_passed"])
        self.assertEqual(parsed["mode"], "CLEAN_ROOM_SYNTHETIC_VERIFIED")

    def test_cli_in_process_and_audit_all_include_sensor_codec(self) -> None:
        buf = StringIO()
        with redirect_stdout(buf):
            rc = cli_main(["audit-sensor-codec", "--clean-room"])
        self.assertEqual(rc, 0)
        parsed = json.loads(buf.getvalue())
        self.assertTrue(parsed["all_checks_passed"])

        all_res = run_audit_all(clean_room=True)
        self.assertTrue(all_res["all_checks_passed"])
        self.assertIn("sensor_codec_compatibility_audit", all_res)
        sc = all_res["sensor_codec_compatibility_audit"]
        assert isinstance(sc, dict)
        self.assertTrue(sc["all_checks_passed"])


if __name__ == "__main__":
    unittest.main()
