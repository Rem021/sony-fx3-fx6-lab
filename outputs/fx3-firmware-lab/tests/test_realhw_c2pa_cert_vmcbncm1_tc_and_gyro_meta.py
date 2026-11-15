"""Phase 169 Dual-Mode Unit Tests (48 tests): Real-Hardware `p12:/cert/RQ_LIC.DAT`
C2PA Authenticity License Lock, `VMC-BNCM1` (`EXT-LK`) SMPTE-12M Timecode &
`/dev/rtc0` (`0x92d2091c`) User-Bit Bridge, and `Catalyst / Resolve` `IMX510`
Gyro / E-Mount Lens `NonRealTimeMeta.xml` Provenance Auditor (`35/35`).
"""

from __future__ import annotations

import ast
import io
import json
import os
import re
import time
import unittest
import xml.etree.ElementTree as ET
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

import fx3_firmware_lab as lab
from fx3_firmware_lab.__main__ import main as cli_main, run_audit_all
from fx3_firmware_lab.realhw_c2pa_cert_vmcbncm1_tc_and_gyro_meta_auditor import (
    AVBBC_TCUB_MARKERS_P169,
    C2PA_APPFW_FX3_MARKERS_P169,
    C2PA_APPFW_FX6_MARKERS_P169,
    C2PA_MPR_FX3_SIGN_MARKERS_P169,
    C2PA_MPR_SHARED_MARKERS_P169,
    CERTMGR_SHARED_MARKERS_P169,
    COMPATIBLE_MULTI_TC_CABLES,
    DROP_FRAME_TC_FPS_P169,
    EXPECTED_FX3_APPFW_BYTES_P169,
    EXPECTED_FX3_AVBBC_BYTES_P169,
    EXPECTED_FX3_CERTMGR_BYTES_P169,
    EXPECTED_FX3_CERTMGR_EXPORTS_P169,
    EXPECTED_FX3_CERTMGR_IMPORTS_P169,
    EXPECTED_FX3_CPAPP_BYTES_P169,
    EXPECTED_FX3_MPR_BYTES_P169,
    EXPECTED_FX3_SENCORE_BYTES_P169,
    EXPECTED_FX6_APPFW_BYTES_P169,
    EXPECTED_FX6_AVBBC_BYTES_P169,
    EXPECTED_FX6_CERTMGR_BYTES_P169,
    EXPECTED_FX6_CERTMGR_EXPORTS_P169,
    EXPECTED_FX6_CERTMGR_IMPORTS_P169,
    EXPECTED_FX6_CPAPP_BYTES_P169,
    EXPECTED_FX6_MPR_BYTES_P169,
    EXPECTED_FX6_SENCORE_BYTES_P169,
    FX3_FW_VERSION_STR,
    FX3_MODEL_ID_HEX,
    FX3_MODEL_NAME,
    IMU_GYRO_SAMPLE_RATE_HZ_P169,
    IMX510_GYRO_LENS_CP_MARKERS_P169,
    IMX510_READOUT_US_BY_SCAN_MODE,
    NRTM_GYRO_LENS_MPR_MARKERS_P169,
    NRTM_NAMESPACE_V220_P169,
    P12_CERT_CRYPTO_DEVICE,
    P12_CERT_DEVICE,
    P12_CERT_MOUNT_POINT,
    P12_MOUNT_MODE_REQUIRED,
    P12_RQ_LIC_PATH,
    PHASE_169_SCHEMA,
    PHASE_169_VERSION,
    SGAMUT3_CINE_PRIMARIES_UL_HEX,
    SLOG3_GAMMA_UL_HEX,
    TC_APPFW_FX3_MARKERS_P169,
    TC_APPFW_FX6_MARKERS_P169,
    TC_CP_SHARED_MARKERS_P169,
    TC_SENCORE_SHARED_MARKERS_P169,
    VALID_NLE_CONSUMERS_P169,
    VALID_SMPTE_TC_FPS_P169,
    VALID_TC_MODES_P169,
    VALID_UB_MODES_P169,
    VMC_BNCM1_AD_JACK_PIN,
    VMC_BNCM1_LTC_VPP_MAX,
    VMC_BNCM1_LTC_VPP_MIN,
    VMC_BNCM1_PART_NO,
    analyze_realhw_c2pa_cert_vmcbncm1_tc_and_gyro_meta,
    build_clean_room_realhw_c2pa_vmcbncm1_gyro_fixtures,
    build_phase169_provenance_matrix,
    encode_smpte12m_tc_and_ub,
    evaluate_nrtm_gyro_lens_provenance,
    evaluate_p12_c2pa_cert_immutability,
    evaluate_phase169_write_guard,
    evaluate_vmc_bncm1_ext_lk_tc_bridge,
    realhw_c2pa_cert_vmcbncm1_tc_and_gyro_meta_report_to_dict,
    synthesize_and_verify_phase169_nrtm_xml,
)
from fx3_firmware_lab.realhw_lens_ibis_audio_hdmi_peripheral_bridge_auditor import (
    BRIDGE_CLASS_HARD_WRITE_PROTECTED,
    BRIDGE_CLASS_MASKED_ABSENT_HW,
    BRIDGE_CLASS_NATIVE_PASSTHROUGH,
    BRIDGE_CLASS_SHIM_TRANSLATED,
    P18_LENS_CALIB_FILE,
    P18_LENS_PARTITION_DEVICE,
    VALID_BRIDGE_CLASSES,
)
from fx3_firmware_lab.c2pa_lens_shading_and_mc_fleet_auditor import (
    C2PA_MAX_LICENSES_PER_RQ_LIC_FX3,
    STAGE_B_CLEAN_ROOM_RESEARCH_LABEL,
)


_BYTES_REPR_RE = re.compile(r"(?<![0-9A-Za-z_/.-])b['\"]")
_AUDITOR_PATH = (
    Path(__file__).resolve().parent.parent
    / "fx3_firmware_lab"
    / "realhw_c2pa_cert_vmcbncm1_tc_and_gyro_meta_auditor.py"
)


class TestRealhwC2paCertVmcBncm1TcAndGyroMeta(unittest.TestCase):
    """Comprehensive dual-mode tests (48 tests) for the 35th unified auditor (35/35)."""

    # ---- Mode, Runtime, Determinism & Structural Hygiene ----

    def test_01_clean_room_report_all_pillars_and_runtime(self) -> None:
        t0 = time.perf_counter()
        rep = analyze_realhw_c2pa_cert_vmcbncm1_tc_and_gyro_meta(clean_room=True)
        dt_cold = time.perf_counter() - t0
        t1 = time.perf_counter()
        rep_warm = analyze_realhw_c2pa_cert_vmcbncm1_tc_and_gyro_meta(clean_room=True)
        dt_warm = time.perf_counter() - t1

        self.assertTrue(rep.all_checks_passed, rep.errors)
        self.assertEqual(rep.mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(rep.schema_version, PHASE_169_SCHEMA)
        self.assertEqual(rep.phase_version, PHASE_169_VERSION)
        self.assertTrue(rep.o_rdonly_enforced)
        self.assertEqual(rep.p12_mount_mode, P12_MOUNT_MODE_REQUIRED)
        self.assertEqual(rep.c2pa_cert_mutation_bytes, 0)
        self.assertTrue(rep.c2pa_cross_model_signing_blocked)
        self.assertTrue(rep.vmc_bncm1_ext_lk_verified)
        self.assertTrue(rep.bnc_tc_out_masked_cleanly)
        self.assertTrue(rep.imu_gyro_metadata_intact)
        self.assertTrue(rep.catalyst_resolve_nle_compatible)
        self.assertEqual(rep.cp_mutation_bytes, 0)
        self.assertEqual(rep.p18_lens_mutation_bytes, 0)
        self.assertEqual(rep.emmc_mutation_bytes, 0)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.spi_nor_write_authorized)
        self.assertTrue(rep.pillar1_p12_c2pa_cert.passed)
        self.assertTrue(rep.pillar2_vmc_bncm1_tc_ub.passed)
        self.assertTrue(rep.pillar3_nrtm_gyro_lens.passed)
        self.assertTrue(rep.pillar4_nvs_firewall_matrix.passed)
        self.assertEqual(rep.report_sha256, rep_warm.report_sha256)
        self.assertEqual(len(rep.report_sha256), 64)
        self.assertLess(dt_cold, 0.35)
        self.assertLess(dt_warm, 0.15)

    def test_02_auto_mode_or_local_donor_runtime_under_1500ms(self) -> None:
        t0 = time.perf_counter()
        rep = analyze_realhw_c2pa_cert_vmcbncm1_tc_and_gyro_meta()
        dt = time.perf_counter() - t0
        self.assertTrue(rep.all_checks_passed, rep.errors)
        self.assertIn(rep.mode, ("LOCAL_DONOR_VERIFIED", "CLEAN_ROOM_SYNTHETIC"))
        self.assertLess(dt, 1.5)
        if rep.mode == "LOCAL_DONOR_VERIFIED":
            self.assertEqual(len(rep.donor_file_sizes), 12)
            self.assertEqual(rep.donor_file_sizes.get("fx3_certmgr"), EXPECTED_FX3_CERTMGR_BYTES_P169)
            self.assertEqual(rep.donor_file_sizes.get("fx6_certmgr"), EXPECTED_FX6_CERTMGR_BYTES_P169)
            self.assertEqual(rep.donor_file_sizes.get("fx3_appfw"), EXPECTED_FX3_APPFW_BYTES_P169)
            self.assertEqual(rep.donor_file_sizes.get("fx6_appfw"), EXPECTED_FX6_APPFW_BYTES_P169)
            self.assertEqual(rep.donor_file_sizes.get("fx3_mpr"), EXPECTED_FX3_MPR_BYTES_P169)
            self.assertEqual(rep.donor_file_sizes.get("fx6_mpr"), EXPECTED_FX6_MPR_BYTES_P169)
            self.assertEqual(rep.donor_file_sizes.get("fx3_sencore"), EXPECTED_FX3_SENCORE_BYTES_P169)
            self.assertEqual(rep.donor_file_sizes.get("fx6_sencore"), EXPECTED_FX6_SENCORE_BYTES_P169)
            self.assertEqual(rep.donor_file_sizes.get("fx3_avbbc"), EXPECTED_FX3_AVBBC_BYTES_P169)
            self.assertEqual(rep.donor_file_sizes.get("fx6_avbbc"), EXPECTED_FX6_AVBBC_BYTES_P169)
            self.assertEqual(rep.donor_file_sizes.get("fx3_cpapp"), EXPECTED_FX3_CPAPP_BYTES_P169)
            self.assertEqual(rep.donor_file_sizes.get("fx6_cpapp"), EXPECTED_FX6_CPAPP_BYTES_P169)

    def test_03_forced_clean_room_env_flag_respected(self) -> None:
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}, clear=False):
            rep = analyze_realhw_c2pa_cert_vmcbncm1_tc_and_gyro_meta()
        self.assertTrue(rep.all_checks_passed, rep.errors)
        self.assertEqual(rep.mode, "CLEAN_ROOM_SYNTHETIC")

    def test_04_missing_donor_falls_back_to_clean_room(self) -> None:
        with mock.patch(
            "fx3_firmware_lab.realhw_c2pa_cert_vmcbncm1_tc_and_gyro_meta_auditor.resolve_donor_file",
            return_value=None,
        ):
            rep = analyze_realhw_c2pa_cert_vmcbncm1_tc_and_gyro_meta()
        self.assertTrue(rep.all_checks_passed, rep.errors)
        self.assertEqual(rep.mode, "CLEAN_ROOM_SYNTHETIC")

    def test_05_json_serialization_no_raw_bytes_repr_leak(self) -> None:
        rep = analyze_realhw_c2pa_cert_vmcbncm1_tc_and_gyro_meta(clean_room=True)
        payload = realhw_c2pa_cert_vmcbncm1_tc_and_gyro_meta_report_to_dict(rep)
        dumped = json.dumps(payload, sort_keys=True)
        self.assertIsNone(_BYTES_REPR_RE.search(dumped), "Unexpected raw bytes repr in JSON")
        self.assertNotIn("BEGIN RSA PRIVATE KEY", dumped)
        self.assertNotIn("BEGIN CERTIFICATE", dumped)
        self.assertIn(PHASE_169_SCHEMA, dumped)

    def test_06_ast_enforces_strictly_o_rdonly_and_zero_writes(self) -> None:
        src = _AUDITOR_PATH.read_text(encoding="utf-8")
        tree = ast.parse(src)
        forbidden_attrs = {"O_WRONLY", "O_RDWR", "O_CREAT", "O_TRUNC", "O_APPEND", "ACCESS_WRITE"}
        forbidden_calls = {"write", "write_bytes", "write_text"}
        os_open_count = 0
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute):
                self.assertNotIn(node.attr, forbidden_attrs)
                if (
                    isinstance(node.value, ast.Name)
                    and node.value.id == "os"
                    and node.attr == "open"
                ):
                    os_open_count += 1
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    self.assertNotEqual(node.func.id, "open")
                elif isinstance(node.func, ast.Attribute):
                    self.assertNotIn(node.func.attr, forbidden_calls)
        self.assertGreaterEqual(os_open_count, 1)

    def test_07_package_init_exports_and_all(self) -> None:
        required = (
            "PHASE_169_SCHEMA",
            "PHASE_169_VERSION",
            "FX3_MODEL_ID_HEX",
            "FX3_MODEL_NAME",
            "FX3_FW_VERSION_STR",
            "P12_CERT_DEVICE",
            "P12_CERT_MOUNT_POINT",
            "P12_RQ_LIC_PATH",
            "P12_MOUNT_MODE_REQUIRED",
            "VMC_BNCM1_PART_NO",
            "VMC_BNCM1_AD_JACK_PIN",
            "COMPATIBLE_MULTI_TC_CABLES",
            "IMX510_READOUT_US_BY_SCAN_MODE",
            "IMU_GYRO_SAMPLE_RATE_HZ_P169",
            "SLOG3_GAMMA_UL_HEX",
            "SGAMUT3_CINE_PRIMARIES_UL_HEX",
            "C2paCertP12ImmutabilityEvalResult",
            "Smpte12mTcAndUbEncoded",
            "VmcBncm1ExtLkBridgeEvalResult",
            "NrtmGyroLensProvenanceEvalResult",
            "Phase169WriteGuardResult",
            "Phase169TouchpointEntry",
            "Phase169CompatMatrixSummary",
            "RealhwC2paCertVmcBncm1TcAndGyroMetaReport",
            "evaluate_p12_c2pa_cert_immutability",
            "encode_smpte12m_tc_and_ub",
            "evaluate_vmc_bncm1_ext_lk_tc_bridge",
            "synthesize_and_verify_phase169_nrtm_xml",
            "evaluate_nrtm_gyro_lens_provenance",
            "evaluate_phase169_write_guard",
            "build_phase169_provenance_matrix",
            "build_clean_room_realhw_c2pa_vmcbncm1_gyro_fixtures",
            "analyze_realhw_c2pa_cert_vmcbncm1_tc_and_gyro_meta",
            "realhw_c2pa_cert_vmcbncm1_tc_and_gyro_meta_report_to_dict",
        )
        for name in required:
            self.assertTrue(hasattr(lab, name), f"Missing export {name} in fx3_firmware_lab")
            self.assertIn(name, lab.__all__, f"Missing {name} in fx3_firmware_lab.__all__")

    def test_08_run_audit_all_and_cli_integration_35_of_35(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cli_main(["audit-realhw-c2pa-tc-gyro-meta", "--clean-room", "--json"])
        self.assertEqual(rc, 0)
        parsed = json.loads(buf.getvalue())
        self.assertTrue(parsed["all_checks_passed"])
        self.assertEqual(parsed["schema_version"], PHASE_169_SCHEMA)
        self.assertFalse(parsed["persistent_emmc_writes_authorized"])
        self.assertFalse(parsed["spi_nor_write_authorized"])
        self.assertEqual(parsed["c2pa_cert_mutation_bytes"], 0)
        self.assertTrue(parsed["c2pa_cross_model_signing_blocked"])
        self.assertTrue(parsed["vmc_bncm1_ext_lk_verified"])
        self.assertTrue(parsed["imu_gyro_metadata_intact"])

        all_summary = run_audit_all(clean_room=True)
        self.assertTrue(all_summary["all_checks_passed"])
        self.assertIn("realhw_c2pa_cert_vmcbncm1_tc_gyro_meta_audit", all_summary)
        audit_keys = [k for k in all_summary.keys() if k.endswith("_audit")]
        self.assertEqual(len(audit_keys), 35)

    def test_09_cli_audit_all_clean_room_smoke(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cli_main(["audit-all", "--clean-room", "--json"])
        self.assertEqual(rc, 0)
        parsed = json.loads(buf.getvalue())
        self.assertTrue(parsed["all_checks_passed"])
        self.assertIn("realhw_c2pa_cert_vmcbncm1_tc_gyro_meta_audit", parsed)

    def test_10_clean_room_fixtures_structure_valid(self) -> None:
        fx = build_clean_room_realhw_c2pa_vmcbncm1_gyro_fixtures()
        expected_keys = {
            "fx3_certmgr",
            "fx6_certmgr",
            "fx3_appfw",
            "fx6_appfw",
            "fx3_mpr",
            "fx6_mpr",
            "fx3_sencore",
            "fx6_sencore",
            "fx3_avbbc",
            "fx6_avbbc",
            "fx3_cpapp",
            "fx6_cpapp",
        }
        self.assertEqual(set(fx.keys()), expected_keys)
        for k, blob in fx.items():
            self.assertGreater(len(blob), 16, k)
            if k not in ("fx3_cpapp", "fx6_cpapp"):
                self.assertEqual(blob[:4], b"\x7fELF", k)

    # ---- Pillar 1: p12:/cert/RQ_LIC.DAT C2PA Authenticity License Lock ----

    def test_11_pillar1_certmgr_and_c2pa_markers_verified(self) -> None:
        rep = analyze_realhw_c2pa_cert_vmcbncm1_tc_and_gyro_meta(clean_room=True)
        p1 = rep.pillar1_p12_c2pa_cert
        self.assertTrue(p1.passed, p1.errors)
        self.assertEqual(p1.fx3_certmgr_summary.export_count, EXPECTED_FX3_CERTMGR_EXPORTS_P169)
        self.assertEqual(p1.fx3_certmgr_summary.import_count, EXPECTED_FX3_CERTMGR_IMPORTS_P169)
        self.assertEqual(p1.fx6_certmgr_summary.export_count, EXPECTED_FX6_CERTMGR_EXPORTS_P169)
        self.assertEqual(p1.fx6_certmgr_summary.import_count, EXPECTED_FX6_CERTMGR_IMPORTS_P169)
        self.assertTrue(p1.fx6_sencore_has_init_license)
        for m in CERTMGR_SHARED_MARKERS_P169:
            self.assertGreater(p1.fx3_certmgr_summary.marker_hits.get(m, 0), 0, m)
            self.assertGreater(p1.fx6_certmgr_summary.marker_hits.get(m, 0), 0, m)
        for m in C2PA_APPFW_FX3_MARKERS_P169:
            self.assertGreater(p1.fx3_appfw_summary.marker_hits.get(m, 0), 0, m)
        for m in C2PA_APPFW_FX6_MARKERS_P169:
            self.assertGreater(p1.fx6_appfw_summary.marker_hits.get(m, 0), 0, m)
        for m in C2PA_MPR_SHARED_MARKERS_P169 + C2PA_MPR_FX3_SIGN_MARKERS_P169:
            self.assertGreater(p1.fx3_mpr_summary.marker_hits.get(m, 0), 0, m)
        for m in C2PA_MPR_SHARED_MARKERS_P169:
            self.assertGreater(p1.fx6_mpr_summary.marker_hits.get(m, 0), 0, m)

    def test_12_p12_rq_lic_nominal_ms_rdonly_lock(self) -> None:
        res = evaluate_p12_c2pa_cert_immutability()
        self.assertTrue(res.valid)
        self.assertEqual(res.partition_path, P12_RQ_LIC_PATH)
        self.assertEqual(res.mount_mode, P12_MOUNT_MODE_REQUIRED)
        self.assertEqual(res.model_id, FX3_MODEL_ID_HEX)
        self.assertEqual(res.c2pa_cert_mutation_bytes, 0)
        self.assertTrue(res.c2pa_cross_model_signing_blocked)
        self.assertTrue(res.o_rdonly_enforced)
        self.assertEqual(res.stage_b_provenance_label, STAGE_B_CLEAN_ROOM_RESEARCH_LABEL)
        self.assertEqual(res.status, "P12_CERT_RQ_LIC_LOCKED_RDONLY")

    def test_13_p12_blocks_ms_rdwr_remount(self) -> None:
        res = evaluate_p12_c2pa_cert_immutability(mount_mode="MS_RDWR")
        self.assertFalse(res.valid)
        self.assertFalse(res.o_rdonly_enforced)
        self.assertEqual(res.c2pa_cert_mutation_bytes, 0)
        self.assertIn("BLOCKED_P12_NON_RDONLY_MOUNT", res.status)

    def test_14_p12_blocks_rq_lic_byte_mutation(self) -> None:
        res = evaluate_p12_c2pa_cert_immutability(requested_mutation_bytes=128)
        self.assertFalse(res.valid)
        self.assertEqual(res.c2pa_cert_mutation_bytes, 0)
        self.assertIn("BLOCKED_P12_RQ_LIC_MUTATION", res.status)

    def test_15_p12_blocks_cross_model_c2pa_signing_and_forging(self) -> None:
        res = evaluate_p12_c2pa_cert_immutability(
            camera_model_id=FX3_MODEL_ID_HEX,
            signing_target_model_id="0x91030099",
            attempt_cross_model_sign=True,
        )
        self.assertFalse(res.valid)
        self.assertTrue(res.c2pa_cross_model_signing_blocked)
        self.assertIn("BLOCKED_C2PA_CROSS_MODEL_SIGNING", res.status)

    def test_16_p12_blocks_same_model_explicit_forge_attempt(self) -> None:
        res = evaluate_p12_c2pa_cert_immutability(attempt_cross_model_sign=True)
        self.assertFalse(res.valid)
        self.assertTrue(res.c2pa_cross_model_signing_blocked)

    def test_17_p12_enforces_rq_lic_max_100_licenses(self) -> None:
        ok_max = evaluate_p12_c2pa_cert_immutability(rq_lic_count=C2PA_MAX_LICENSES_PER_RQ_LIC_FX3)
        self.assertTrue(ok_max.valid)
        bad_over = evaluate_p12_c2pa_cert_immutability(rq_lic_count=C2PA_MAX_LICENSES_PER_RQ_LIC_FX3 + 1)
        self.assertFalse(bad_over.valid)
        self.assertIn("RQ_LIC_PACKAGE_COUNT_OUT_OF_RANGE", bad_over.status)
        bad_neg = evaluate_p12_c2pa_cert_immutability(rq_lic_count=-1)
        self.assertFalse(bad_neg.valid)

    def test_18_p12_blocks_invalid_keyvault_partition_transplant(self) -> None:
        res = evaluate_p12_c2pa_cert_immutability(partition_path="p15:/usr/share/fake_cert/RQ_LIC.DAT")
        self.assertFalse(res.valid)
        self.assertIn("INVALID_C2PA_KEYVAULT_PARTITION", res.status)

    def test_19_p12_stock_fx3_label_when_stage_b_inactive(self) -> None:
        res = evaluate_p12_c2pa_cert_immutability(stage_b_overlay_active=False)
        self.assertTrue(res.valid)
        self.assertEqual(res.stage_b_provenance_label, "STOCK_FX3_C2PA_NATIVE")

    # ---- Pillar 2: VMC-BNCM1 (EXT-LK) SMPTE-12M TC & /dev/rtc0 User-Bit Bridge ----

    def test_20_pillar2_tc_markers_verified_across_4_binaries(self) -> None:
        rep = analyze_realhw_c2pa_cert_vmcbncm1_tc_and_gyro_meta(clean_room=True)
        p2 = rep.pillar2_vmc_bncm1_tc_ub
        self.assertTrue(p2.passed, p2.errors)
        for m in TC_APPFW_FX3_MARKERS_P169:
            self.assertGreater(p2.fx3_appfw_tc_hits.get(m, 0), 0, m)
        for m in TC_APPFW_FX6_MARKERS_P169:
            self.assertGreater(p2.fx6_appfw_tc_hits.get(m, 0), 0, m)
        for m in TC_SENCORE_SHARED_MARKERS_P169:
            self.assertGreater(p2.fx3_sencore_summary.marker_hits.get(m, 0), 0, m)
            self.assertGreater(p2.fx6_sencore_summary.marker_hits.get(m, 0), 0, m)
        for m in AVBBC_TCUB_MARKERS_P169:
            self.assertGreater(p2.fx3_avbbc_summary.marker_hits.get(m, 0), 0, m)
            self.assertGreater(p2.fx6_avbbc_summary.marker_hits.get(m, 0), 0, m)
        for m in TC_CP_SHARED_MARKERS_P169:
            self.assertGreater(p2.fx3_cp_tc_hits.get(m, 0), 0, m)
            self.assertGreater(p2.fx6_cp_tc_hits.get(m, 0), 0, m)

    def test_21_smpte12m_bcd_and_user_bits_encoding_ndf_23976(self) -> None:
        enc = encode_smpte12m_tc_and_ub(
            hours=12, minutes=34, seconds=56, frames=18, fps=23.976, user_bits_hex="a001cafe"
        )
        self.assertTrue(enc.valid, enc.errors)
        self.assertFalse(enc.drop_frame)
        self.assertEqual(enc.tc_str, "12:34:56:18")
        self.assertEqual(enc.user_bits_hex, "A001CAFE")
        self.assertEqual(enc.user_bits_u32, 0xA001CAFE)
        self.assertEqual(enc.tc_bcd_bytes_hex, "18563412")

    def test_22_smpte12m_drop_frame_2997_and_5994_validation(self) -> None:
        for df_fps in DROP_FRAME_TC_FPS_P169:
            ok = encode_smpte12m_tc_and_ub(hours=1, minutes=10, seconds=0, frames=0, fps=df_fps)
            self.assertTrue(ok.valid, (df_fps, ok.errors))
            self.assertTrue(ok.drop_frame)
            self.assertIn(";", ok.tc_str)

            # Frame 00 and 01 at non-tenth minute transitions are invalid in Drop-Frame
            bad = encode_smpte12m_tc_and_ub(hours=1, minutes=1, seconds=0, frames=1, fps=df_fps)
            self.assertFalse(bad.valid)
            self.assertIn("INVALID_DROP_FRAME_SKIPPED_TC", bad.errors)

    def test_23_smpte12m_rejects_invalid_fps_ranges_and_ub_hex(self) -> None:
        bad_fps = encode_smpte12m_tc_and_ub(hours=0, minutes=0, seconds=0, frames=0, fps=15.0)
        self.assertFalse(bad_fps.valid)
        bad_hr = encode_smpte12m_tc_and_ub(hours=24, minutes=0, seconds=0, frames=0, fps=24.0)
        self.assertFalse(bad_hr.valid)
        bad_ub = encode_smpte12m_tc_and_ub(
            hours=0, minutes=0, seconds=0, frames=0, fps=24.0, user_bits_hex="ZZZZ1234"
        )
        self.assertFalse(bad_ub.valid)
        self.assertIn("INVALID_USER_BITS_HEX", bad_ub.errors[0])

    def test_24_vmc_bncm1_and_third_party_cables_ext_lk_bridge_pass(self) -> None:
        self.assertEqual(VMC_BNCM1_PART_NO, "A-5051-506-A")
        self.assertEqual(VMC_BNCM1_AD_JACK_PIN, 10)
        for cable in COMPATIBLE_MULTI_TC_CABLES:
            res = evaluate_vmc_bncm1_ext_lk_tc_bridge(cable_type=cable, tc_mode="EXT_LK", ltc_vpp=2.2)
            self.assertTrue(res.valid, (cable, res.errors))
            self.assertTrue(res.vmc_bncm1_ext_lk_verified)
            self.assertTrue(res.big6_tc_pill_text.startswith("TC EXT-LK "))
            self.assertEqual(res.big6_ub_pill_text, "UB A0:01:00:01")

    def test_25_vmc_bncm1_blocks_ltc_voltage_out_of_spec(self) -> None:
        low = evaluate_vmc_bncm1_ext_lk_tc_bridge(tc_mode="EXT_LK", ltc_vpp=VMC_BNCM1_LTC_VPP_MIN - 0.1)
        self.assertFalse(low.valid)
        self.assertIn("LTC_SIGNAL_OUT_OF_RANGE", low.status)

        high = evaluate_vmc_bncm1_ext_lk_tc_bridge(tc_mode="EXT_LK", ltc_vpp=VMC_BNCM1_LTC_VPP_MAX + 0.5)
        self.assertFalse(high.valid)
        self.assertIn("LTC_SIGNAL_OUT_OF_RANGE", high.status)

    def test_26_vmc_bncm1_requires_ad_jack_pin10_and_valid_cable_in_ext_lk(self) -> None:
        no_pin10 = evaluate_vmc_bncm1_ext_lk_tc_bridge(tc_mode="EXT_LK", ad_jack_pin10_detected=False)
        self.assertFalse(no_pin10.valid)
        self.assertIn("AD_JACK_IN_PIN10_NOT_DETECTED", no_pin10.errors)

        bad_cable = evaluate_vmc_bncm1_ext_lk_tc_bridge(tc_mode="EXT_LK", cable_type="GENERIC_USB")
        self.assertFalse(bad_cable.valid)
        self.assertIn("UNSUPPORTED_MULTI_TC_CABLE", bad_cable.errors[0])

    def test_27_vmc_bncm1_blocks_phase38_uart_boot_pins_7_8_9_contention(self) -> None:
        res = evaluate_vmc_bncm1_ext_lk_tc_bridge(tc_mode="EXT_LK", uart_boot_active=True)
        self.assertFalse(res.valid)
        self.assertEqual(res.status, "BLOCKED_PHASE38_UART_BOOT_MULTI_PORT_PINS_7_8_9_CONTENTION")

    def test_28_vmc_bncm1_masks_fx6_bnc_tc_out_and_preserves_hdmi_tc_out(self) -> None:
        res = evaluate_vmc_bncm1_ext_lk_tc_bridge(
            tc_mode="EXT_LK",
            request_bnc_tc_out=True,
            hdmi_tc_out_enabled=True,
        )
        self.assertTrue(res.valid, res.errors)
        self.assertTrue(res.bnc_tc_out_masked)
        self.assertTrue(res.hdmi_tc_out_enabled)
        self.assertEqual(res.status, "BNC_TC_OUT_MASKED_HDMI_TC_PRESERVED")

    def test_29_vmc_bncm1_requires_p11_rtc0_udate_shim_and_valid_modes(self) -> None:
        no_rtc = evaluate_vmc_bncm1_ext_lk_tc_bridge(tc_mode="FREE_RUN", rtc0_udate_shim_active=False)
        self.assertFalse(no_rtc.valid)
        self.assertIn("P11_RTC0_UDATE_SHIM_INACTIVE", no_rtc.errors)

        for tc_mode in VALID_TC_MODES_P169:
            for ub_mode in VALID_UB_MODES_P169:
                ok = evaluate_vmc_bncm1_ext_lk_tc_bridge(tc_mode=tc_mode, ub_mode=ub_mode)
                self.assertTrue(ok.valid, (tc_mode, ub_mode, ok.errors))

    # ---- Pillar 3: NonRealTimeMeta.xml IMX510 Gyro & E-Mount Lens Provenance ----

    def test_30_pillar3_nrtm_mpr_and_cpapp_markers_verified(self) -> None:
        rep = analyze_realhw_c2pa_cert_vmcbncm1_tc_and_gyro_meta(clean_room=True)
        p3 = rep.pillar3_nrtm_gyro_lens
        self.assertTrue(p3.passed, p3.errors)
        for m in NRTM_GYRO_LENS_MPR_MARKERS_P169:
            self.assertGreater(p3.fx3_mpr_nrtm_hits.get(m, 0), 0, m)
            self.assertGreater(p3.fx6_mpr_nrtm_hits.get(m, 0), 0, m)
        for m in IMX510_GYRO_LENS_CP_MARKERS_P169:
            self.assertGreater(p3.fx3_cp_imx510_gyro_hits.get(m, 0), 0, m)
            self.assertGreater(p3.fx6_cp_imx510_gyro_hits.get(m, 0), 0, m)

    def test_31_nrtm_xml_roundtrip_schema_and_smpte_uls(self) -> None:
        xml_str, ok, sha, errs = synthesize_and_verify_phase169_nrtm_xml()
        self.assertTrue(ok, errs)
        self.assertEqual(len(sha), 64)
        root = ET.fromstring(xml_str)
        self.assertIn(NRTM_NAMESPACE_V220_P169, root.tag)
        items = {
            el.attrib.get("name", ""): el.attrib.get("value", "")
            for el in root.iter()
            if el.tag.endswith("Item")
        }
        self.assertEqual(items["ImagerSensorModel"], "IMX510")
        self.assertEqual(items["ReadoutDurationUs"], "8700")
        self.assertEqual(items["ImuGyro6AxisRateHz"], str(IMU_GYRO_SAMPLE_RATE_HZ_P169))
        self.assertEqual(items["CaptureGammaEquation"], "s-log3")
        self.assertEqual(items["CaptureGammaEquationUL"], SLOG3_GAMMA_UL_HEX)
        self.assertEqual(items["CaptureColorPrimaries"], "s-gamut3-cine")
        self.assertEqual(items["CaptureColorPrimariesUL"], SGAMUT3_CINE_PRIMARIES_UL_HEX)
        self.assertEqual(items["P18LensCalibAccess"], "O_RDONLY")

    def test_32_nrtm_imx510_readout_all_scan_modes_pass(self) -> None:
        for scan_mode, us in IMX510_READOUT_US_BY_SCAN_MODE.items():
            res = evaluate_nrtm_gyro_lens_provenance(
                scan_mode=scan_mode,
                readout_duration_us=us,
            )
            self.assertTrue(res.valid, (scan_mode, res.errors))
            self.assertTrue(res.imu_gyro_metadata_intact)
            self.assertTrue(res.catalyst_resolve_nle_compatible)

    def test_33_nrtm_blocks_mismatched_imx510_readout_duration(self) -> None:
        res = evaluate_nrtm_gyro_lens_provenance(
            scan_mode="4K_120P_BINNING",
            readout_duration_us=8700,  # wrong for 120p (should be 4350)
        )
        self.assertFalse(res.valid)
        self.assertFalse(res.imu_gyro_metadata_intact)
        self.assertIn("IMX510_READOUT_MISMATCH", res.status)

    def test_34_nrtm_blocks_non_stock_cpapp_or_libmpr_mutation(self) -> None:
        no_cp = evaluate_nrtm_gyro_lens_provenance(stock_cpapp_preserved=False)
        self.assertFalse(no_cp.valid)
        self.assertFalse(no_cp.imu_gyro_metadata_intact)
        self.assertIn("STOCK_CPAPP_B_NOT_PRESERVED_IMU_AT_RISK", no_cp.errors)

        no_mpr = evaluate_nrtm_gyro_lens_provenance(stock_libmpr_preserved=False)
        self.assertFalse(no_mpr.valid)
        self.assertFalse(no_mpr.imu_gyro_metadata_intact)
        self.assertIn("STOCK_LIBMPR_NOT_PRESERVED_UDAM_AT_RISK", no_mpr.errors)

    def test_35_nrtm_blocks_missing_imu_gyro_packets_or_wrong_sample_rate(self) -> None:
        zero_pkts = evaluate_nrtm_gyro_lens_provenance(imu_gyro_packet_count=0)
        self.assertFalse(zero_pkts.valid)
        self.assertFalse(zero_pkts.imu_gyro_metadata_intact)

        bad_rate = evaluate_nrtm_gyro_lens_provenance(imu_gyro_rate_hz=400)
        self.assertFalse(bad_rate.valid)
        self.assertFalse(bad_rate.imu_gyro_metadata_intact)

    def test_36_nrtm_blocks_wrong_slog3_or_sgamut3_cine_tags(self) -> None:
        bad_gamma = evaluate_nrtm_gyro_lens_provenance(capture_gamma_equation="rec709")
        self.assertFalse(bad_gamma.valid)
        self.assertIn("SLOG3_GAMMA_TAG_MISMATCH", bad_gamma.status)

        bad_gamut = evaluate_nrtm_gyro_lens_provenance(capture_color_primaries="rec709")
        self.assertFalse(bad_gamut.valid)
        self.assertIn("SGAMUT3_CINE_PRIMARIES_MISMATCH", bad_gamut.status)

    def test_37_nrtm_blocks_forged_c2pa_hardware_signature_claim(self) -> None:
        res = evaluate_nrtm_gyro_lens_provenance(
            c2pa_provenance_status="FORGED_HARDWARE_C2PA_SIGNATURE"
        )
        self.assertFalse(res.valid)
        self.assertIn("BLOCKED_FORGED_C2PA_SIGNATURE_CLAIM", res.errors)

    def test_38_nrtm_unchipped_manual_lens_fails_safe_preserving_gyro(self) -> None:
        res = evaluate_nrtm_gyro_lens_provenance(
            lens_mounted=False,
            focal_length_mm=50.0,
            breathing_comp_enabled=True,
        )
        self.assertTrue(res.valid, res.errors)
        self.assertFalse(res.lens_mounted)
        self.assertEqual(res.focal_length_mm, 0.0)
        self.assertFalse(res.breathing_comp_enabled)
        self.assertTrue(res.imu_gyro_metadata_intact)
        self.assertTrue(res.catalyst_resolve_nle_compatible)

    # ---- Pillar 4: NVS Write Firewall & 12-Touchpoint Provenance Matrix ----

    def test_39_write_firewall_allows_volatile_ram_and_external_sidecars(self) -> None:
        allowed_targets = (
            "/tmp/tmp_certmgr/session.pem",
            "ram://stageb_tc_ub_pill.json",
            "memfd:nrtm_preview",
            "/mnt/sd/PRIVATE/M4ROOT/CLIP/A001C001M01.XML",
            "/mnt/sd2/PRIVATE/M4ROOT/CLIP/A001C002M01.XML",
            "/mnt/cfexpress_a/PRIVATE/M4ROOT/CLIP/A001C003M01.XML",
        )
        for tgt in allowed_targets:
            res = evaluate_phase169_write_guard(tgt)
            self.assertTrue(res.valid, (tgt, res.errors))
            self.assertTrue(res.volatile_or_ext_allowed)
            self.assertFalse(res.persistent_write_blocked)
            self.assertFalse(res.persistent_emmc_writes_authorized)
            self.assertFalse(res.spi_nor_write_authorized)

    def test_40_write_firewall_blocks_p12_cert_rq_lic_and_nflasha12(self) -> None:
        forbidden_p12 = (
            P12_RQ_LIC_PATH,
            P12_CERT_MOUNT_POINT + "/certification.pem",
            P12_CERT_DEVICE,
            P12_CERT_CRYPTO_DEVICE,
            "/cert/RQ_LIC.DAT",
            "/cert/HTTPS_AUTH_certification.pem",
        )
        for tgt in forbidden_p12:
            res = evaluate_phase169_write_guard(tgt)
            self.assertFalse(res.valid, tgt)
            self.assertTrue(res.persistent_write_blocked)
            self.assertFalse(res.persistent_emmc_writes_authorized)
            self.assertFalse(res.spi_nor_write_authorized)
            self.assertEqual(res.c2pa_cert_mutation_bytes, 0)

    def test_41_write_firewall_blocks_p18_lens_p2_backup_p8_cp_rtc0_and_spinor(self) -> None:
        forbidden = (
            P18_LENS_CALIB_FILE,
            P18_LENS_PARTITION_DEVICE,
            "/lens/lensfile.bin",
            "p2:/Backup.bin",
            "/setting/psd.bin",
            "/setting/defdet.bin",
            "p8:/cpapp-b.bin",
            "/dev/rtc0",
            "/dev/mmcblk0p1",
            "/dev/mmcblk0rpmb",
            "spi_nor:/loader_nor.bin",
            "sector0:/boot.bin",
        )
        for tgt in forbidden:
            res = evaluate_phase169_write_guard(tgt)
            self.assertFalse(res.valid, tgt)
            self.assertTrue(res.persistent_write_blocked)
            self.assertFalse(res.persistent_emmc_writes_authorized)
            self.assertFalse(res.spi_nor_write_authorized)
            self.assertEqual(res.p18_lens_mutation_bytes, 0)
            self.assertEqual(res.emmc_mutation_bytes, 0)

    def test_42_write_firewall_blocks_unlisted_arbitrary_paths(self) -> None:
        res = evaluate_phase169_write_guard("/usr/lib/libCertificateManager.so")
        self.assertFalse(res.valid)
        self.assertTrue(res.persistent_write_blocked)
        self.assertEqual(res.status, "UNLISTED_NON_VOLATILE_TARGET_BLOCKED")

    def test_43_provenance_matrix_12_touchpoints_and_4_classes(self) -> None:
        mat = build_phase169_provenance_matrix()
        self.assertEqual(mat.total_touchpoints, 12)
        self.assertEqual(len(mat.touchpoints), 12)
        ids = [t.touchpoint_id for t in mat.touchpoints]
        self.assertEqual(len(set(ids)), 12)
        self.assertEqual(ids[0], "P169-01")
        self.assertEqual(ids[-1], "P169-12")
        for cls in VALID_BRIDGE_CLASSES:
            self.assertGreater(mat.class_counts.get(cls, 0), 0, cls)
        self.assertEqual(sum(mat.class_counts.values()), 12)
        self.assertEqual(
            set(mat.subsystem_counts.keys()),
            {"C2PA_CERT_P12", "VMC_BNCM1_TC_UB", "NRTM_GYRO_LENS", "NVS_FIREWALL"},
        )

    def test_44_provenance_matrix_classes_cover_expected_touchpoints(self) -> None:
        mat = build_phase169_provenance_matrix()
        by_id = {e.touchpoint_id: e for e in mat.touchpoints}
        self.assertEqual(by_id["P169-01"].bridge_class, BRIDGE_CLASS_HARD_WRITE_PROTECTED)
        self.assertEqual(by_id["P169-02"].bridge_class, BRIDGE_CLASS_HARD_WRITE_PROTECTED)
        self.assertEqual(by_id["P169-04"].bridge_class, BRIDGE_CLASS_SHIM_TRANSLATED)
        self.assertEqual(by_id["P169-06"].bridge_class, BRIDGE_CLASS_MASKED_ABSENT_HW)
        self.assertEqual(by_id["P169-07"].bridge_class, BRIDGE_CLASS_NATIVE_PASSTHROUGH)
        self.assertEqual(by_id["P169-08"].bridge_class, BRIDGE_CLASS_NATIVE_PASSTHROUGH)
        self.assertEqual(by_id["P169-10"].bridge_class, BRIDGE_CLASS_HARD_WRITE_PROTECTED)
        self.assertEqual(by_id["P169-12"].bridge_class, BRIDGE_CLASS_HARD_WRITE_PROTECTED)

    def test_45_constants_sanity_and_nle_consumers(self) -> None:
        self.assertEqual(FX3_MODEL_NAME, "ILME-FX3")
        self.assertEqual(FX3_FW_VERSION_STR, "7.02")
        self.assertIn("CATALYST_BROWSE", VALID_NLE_CONSUMERS_P169)
        self.assertIn("DAVINCI_RESOLVE", VALID_NLE_CONSUMERS_P169)
        self.assertIn(23.976, VALID_SMPTE_TC_FPS_P169)
        self.assertIn(59.94, VALID_SMPTE_TC_FPS_P169)

    def test_46_negative_clean_room_missing_marker_detected(self) -> None:
        fx = build_clean_room_realhw_c2pa_vmcbncm1_gyro_fixtures()
        fx_corrupt = dict(fx)
        fx_corrupt["fx3_mpr"] = fx["fx3_mpr"].replace(b"c2pa.claim.v2", b"XXXX.XXXXX.XX")
        with mock.patch(
            "fx3_firmware_lab.realhw_c2pa_cert_vmcbncm1_tc_and_gyro_meta_auditor.build_clean_room_realhw_c2pa_vmcbncm1_gyro_fixtures",
            return_value=fx_corrupt,
        ):
            rep = analyze_realhw_c2pa_cert_vmcbncm1_tc_and_gyro_meta(clean_room=True)
        self.assertFalse(rep.all_checks_passed)
        self.assertFalse(rep.pillar1_p12_c2pa_cert.passed)
        self.assertTrue(any("c2pa.claim.v2" in err for err in rep.pillar1_p12_c2pa_cert.errors))

    def test_47_negative_clean_room_missing_imu_marker_detected(self) -> None:
        fx = build_clean_room_realhw_c2pa_vmcbncm1_gyro_fixtures()
        fx_corrupt = dict(fx)
        fx_corrupt["fx3_cpapp"] = fx["fx3_cpapp"].replace(b"GyroStart", b"XxxxXxxxx")
        with mock.patch(
            "fx3_firmware_lab.realhw_c2pa_cert_vmcbncm1_tc_and_gyro_meta_auditor.build_clean_room_realhw_c2pa_vmcbncm1_gyro_fixtures",
            return_value=fx_corrupt,
        ):
            rep = analyze_realhw_c2pa_cert_vmcbncm1_tc_and_gyro_meta(clean_room=True)
        self.assertFalse(rep.all_checks_passed)
        self.assertFalse(rep.pillar3_nrtm_gyro_lens.passed)
        self.assertTrue(any("GyroStart" in err for err in rep.pillar3_nrtm_gyro_lens.errors))

    def test_48_negative_clean_room_missing_extlk_marker_detected(self) -> None:
        fx = build_clean_room_realhw_c2pa_vmcbncm1_gyro_fixtures()
        fx_corrupt = dict(fx)
        fx_corrupt["fx3_appfw"] = fx["fx3_appfw"].replace(b"No301_EXTLK", b"No000_XXXXX")
        with mock.patch(
            "fx3_firmware_lab.realhw_c2pa_cert_vmcbncm1_tc_and_gyro_meta_auditor.build_clean_room_realhw_c2pa_vmcbncm1_gyro_fixtures",
            return_value=fx_corrupt,
        ):
            rep = analyze_realhw_c2pa_cert_vmcbncm1_tc_and_gyro_meta(clean_room=True)
        self.assertFalse(rep.all_checks_passed)
        self.assertFalse(rep.pillar2_vmc_bncm1_tc_ub.passed)
        self.assertTrue(any("No301_EXTLK" in err for err in rep.pillar2_vmc_bncm1_tc_ub.errors))


if __name__ == "__main__":
    unittest.main()
