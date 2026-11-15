"""Phase 156 Dual-Mode Unit Tests (48 tests): Real-Hardware IMX510 10.2MP CMOS Sensor
Calibration (p2:/setting/psd.bin & defdet.bin), Dual-Base ISO 800 / 12800 (LCG / HCG)
& Cine EI Pipeline, and S-Log3 / S-Cinetone / 709tone / 16-Slot .cube 3D MLUT Stage-B
Color Pipeline.
"""

from __future__ import annotations

import ast
import io
import json
import os
import re
import time
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

import fx3_firmware_lab as lab
from fx3_firmware_lab.__main__ import main as cli_main, run_audit_all
from fx3_firmware_lab.realhw_imx510_cmos_dualbase_iso_lut_color_pipeline_auditor import (
    APPFW_USER_LUT_REL_PATH,
    EXPECTED_FX3_APPFW_BYTES_P156,
    EXPECTED_FX3_BACKUP_SUBSYSTEMS_P156,
    EXPECTED_FX3_MPR_EXPORTS_P156,
    EXPECTED_FX3_MPR_IMPORTS_P156,
    EXPECTED_FX3_SENCORE_EXPORTS_P156,
    EXPECTED_FX6_APPFW_BYTES_P156,
    EXPECTED_FX6_BACKUP_SUBSYSTEMS_P156,
    EXPECTED_FX6_MPR_EXPORTS_P156,
    EXPECTED_FX6_MPR_IMPORTS_P156,
    EXPECTED_FX6_SENCORE_EXPORTS_P156,
    EXPECTED_S709_CUBE_BYTES,
    FX3_P2_DEFDET_DDR_ADDR,
    FX3_P2_PSD_DDR_ADDR,
    FX6_P2_DEFDET_DDR_ADDR,
    FX6_P2_PSD_DDR_ADDR,
    IMX510_BASE_ISO_HIGH_HCG,
    IMX510_BASE_ISO_LOW_LCG,
    IMX510_CINE_EI_HIGH_RANGE,
    IMX510_CINE_EI_LOW_RANGE,
    IMX510_CINE_EI_SWITCHOVER_EI,
    IMX510_DCI_4K_RES,
    IMX510_EFFECTIVE_MP,
    IMX510_QFHD_4K_RES,
    IMX510_RAW_ACTIVE_RES,
    IMX510_SENSOR_MODEL,
    MAX_CUBE_FILE_BYTES_P156,
    MAX_USER_LUT_SLOTS,
    P2_CAL_BLOB_SPAN_BYTES,
    P2_P23_P30_LUT_IMMUTABLE_PARTITIONS,
    P2_SENSOR_CAL_IMMUTABLE_PATHS,
    PHASE_156_SCHEMA,
    PHASE_156_VERSION,
    SD_USER_LUT_DIR,
    SUPPORTED_CUBE_GRID_SIZES,
    VALID_BASE_LOOKS_P156,
    VALID_DUAL_BASE_ISOS_P156,
    VALID_EXPOSURE_MODES_P156,
    analyze_realhw_imx510_cmos_dualbase_iso_lut_color_pipeline,
    build_clean_room_realhw_imx510_color_fixtures,
    build_phase156_imx510_color_matrix,
    evaluate_cube_mlut_color_pipeline,
    evaluate_dual_base_iso_cine_ei,
    evaluate_imx510_sensor_cal_preservation,
    evaluate_phase156_write_guard,
    realhw_imx510_cmos_dualbase_iso_lut_color_pipeline_report_to_dict,
)
from fx3_firmware_lab.realhw_lens_ibis_audio_hdmi_peripheral_bridge_auditor import (
    BRIDGE_CLASS_HARD_WRITE_PROTECTED,
    BRIDGE_CLASS_MASKED_ABSENT_HW,
    BRIDGE_CLASS_NATIVE_PASSTHROUGH,
    BRIDGE_CLASS_SHIM_TRANSLATED,
    EXPECTED_SENCORE_EXPORTS,
)


_BYTES_REPR_RE = re.compile(r"(?<![0-9A-Za-z_/.-])b['\"]")
_AUDITOR_PATH = (
    Path(__file__).resolve().parent.parent
    / "fx3_firmware_lab"
    / "realhw_imx510_cmos_dualbase_iso_lut_color_pipeline_auditor.py"
)


class TestRealhwImx510CmosDualbaseIsoLutColorPipeline(unittest.TestCase):
    """Comprehensive dual-mode tests (48 tests) for the 32nd unified auditor."""

    # ---- Mode, Runtime, Determinism & Structural Hygiene ----

    def test_01_clean_room_report_all_pillars_and_runtime(self) -> None:
        t0 = time.perf_counter()
        rep = analyze_realhw_imx510_cmos_dualbase_iso_lut_color_pipeline(clean_room=True)
        dt_cold = time.perf_counter() - t0
        t1 = time.perf_counter()
        rep_warm = analyze_realhw_imx510_cmos_dualbase_iso_lut_color_pipeline(clean_room=True)
        dt_warm = time.perf_counter() - t1

        self.assertTrue(rep.all_checks_passed, rep.errors)
        self.assertEqual(rep.mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(rep.schema_version, PHASE_156_SCHEMA)
        self.assertEqual(rep.phase_version, PHASE_156_VERSION)
        self.assertTrue(rep.o_rdonly_enforced)
        self.assertFalse(rep.sensor_cal_p2_writes_permitted)
        self.assertEqual(rep.sensor_cal_mutation_bytes, 0)
        self.assertTrue(rep.dual_base_iso_800_12800_hcg_aligned)
        self.assertTrue(rep.slog3_double_bake_prevented)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertEqual(rep.emmc_mutation_bytes, 0)
        self.assertEqual(rep.calibration_mutation_bytes, 0)
        self.assertTrue(rep.pillar1_imx510_sensor_cal.passed)
        self.assertTrue(rep.pillar2_dual_base_iso_cine_ei.passed)
        self.assertTrue(rep.pillar3_slog3_cube_mlut.passed)
        self.assertTrue(rep.pillar4_nvs_isolation_matrix.passed)
        self.assertEqual(rep.report_sha256, rep_warm.report_sha256)
        self.assertEqual(len(rep.report_sha256), 64)
        self.assertLess(dt_cold, 0.35)
        self.assertLess(dt_warm, 0.15)

    def test_02_auto_mode_or_local_donor_runtime_under_1500ms(self) -> None:
        t0 = time.perf_counter()
        rep = analyze_realhw_imx510_cmos_dualbase_iso_lut_color_pipeline()
        dt = time.perf_counter() - t0
        self.assertTrue(rep.all_checks_passed, rep.errors)
        self.assertIn(rep.mode, ("LOCAL_DONOR_VERIFIED", "CLEAN_ROOM_SYNTHETIC"))
        self.assertLess(dt, 1.5)
        if rep.mode == "LOCAL_DONOR_VERIFIED":
            self.assertEqual(rep.donor_file_sizes.get("fx3_appfw"), EXPECTED_FX3_APPFW_BYTES_P156)
            self.assertEqual(rep.donor_file_sizes.get("fx6_appfw"), EXPECTED_FX6_APPFW_BYTES_P156)
            self.assertEqual(rep.donor_file_sizes.get("fx3_sencore"), 377_328)
            self.assertEqual(rep.donor_file_sizes.get("fx6_sencore"), 401_952)
            self.assertEqual(rep.donor_file_sizes.get("fx3_mpr"), 3_517_008)
            self.assertEqual(rep.donor_file_sizes.get("fx6_mpr"), 28_921_824)
            self.assertEqual(rep.donor_file_sizes.get("fx3_cpapp"), 15_980_568)
            self.assertEqual(rep.donor_file_sizes.get("fx6_cpapp"), 17_952_816)
            self.assertEqual(rep.donor_file_sizes.get("fx3_backup"), 2_229_740)
            self.assertEqual(rep.donor_file_sizes.get("fx6_backup"), 2_253_333)
            self.assertEqual(rep.donor_file_sizes.get("fx6_s709_cube"), EXPECTED_S709_CUBE_BYTES)

    def test_03_forced_clean_room_env_flag_respected(self) -> None:
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}, clear=False):
            rep = analyze_realhw_imx510_cmos_dualbase_iso_lut_color_pipeline()
        self.assertTrue(rep.all_checks_passed, rep.errors)
        self.assertEqual(rep.mode, "CLEAN_ROOM_SYNTHETIC")

    def test_04_missing_donor_falls_back_to_clean_room(self) -> None:
        with mock.patch(
            "fx3_firmware_lab.realhw_imx510_cmos_dualbase_iso_lut_color_pipeline_auditor.resolve_donor_file",
            return_value=None,
        ):
            rep = analyze_realhw_imx510_cmos_dualbase_iso_lut_color_pipeline(clean_room=False)
        self.assertTrue(rep.all_checks_passed, rep.errors)
        self.assertEqual(rep.mode, "CLEAN_ROOM_SYNTHETIC")

    def test_05_json_serialization_has_zero_bytes_repr(self) -> None:
        rep = analyze_realhw_imx510_cmos_dualbase_iso_lut_color_pipeline(clean_room=True)
        payload = realhw_imx510_cmos_dualbase_iso_lut_color_pipeline_report_to_dict(rep)
        json_str = json.dumps(payload, sort_keys=True)
        self.assertIsNone(_BYTES_REPR_RE.search(json_str), "Unexpected Python bytes repr in JSON")
        self.assertIn(PHASE_156_SCHEMA, json_str)

    def test_06_auditor_source_strictly_uses_os_o_rdonly_and_mmap_access_read(self) -> None:
        src = _AUDITOR_PATH.read_text(encoding="utf-8")
        self.assertIn("os.O_RDONLY", src)
        self.assertIn("mmap.ACCESS_READ", src)
        for forbidden in (
            "os.O_WRONLY",
            "os.O_RDWR",
            "os.O_CREAT",
            "mmap.ACCESS_WRITE",
            ".write_bytes(",
            ".write_text(",
        ):
            self.assertNotIn(forbidden, src)
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr in (
                "O_WRONLY",
                "O_RDWR",
                "O_CREAT",
                "ACCESS_WRITE",
            ):
                self.fail(f"Forbidden write attribute {node.attr} in auditor AST")

    def test_07_package_exports_and_all_include_phase156_symbols(self) -> None:
        expected_symbols = (
            "PHASE_156_SCHEMA",
            "PHASE_156_VERSION",
            "IMX510_SENSOR_MODEL",
            "IMX510_BASE_ISO_LOW_LCG",
            "IMX510_BASE_ISO_HIGH_HCG",
            "IMX510_CINE_EI_LOW_RANGE",
            "IMX510_CINE_EI_HIGH_RANGE",
            "IMX510_CINE_EI_SWITCHOVER_EI",
            "MAX_USER_LUT_SLOTS",
            "SD_USER_LUT_DIR",
            "SUPPORTED_CUBE_GRID_SIZES",
            "VALID_BASE_LOOKS_P156",
            "VALID_EXPOSURE_MODES_P156",
            "VALID_DUAL_BASE_ISOS_P156",
            "P2_SENSOR_CAL_IMMUTABLE_PATHS",
            "P2_P23_P30_LUT_IMMUTABLE_PARTITIONS",
            "RealhwImx510CmosDualbaseIsoLutColorPipelineReport",
            "analyze_realhw_imx510_cmos_dualbase_iso_lut_color_pipeline",
            "build_clean_room_realhw_imx510_color_fixtures",
            "build_phase156_imx510_color_matrix",
            "evaluate_imx510_sensor_cal_preservation",
            "evaluate_dual_base_iso_cine_ei",
            "evaluate_cube_mlut_color_pipeline",
            "evaluate_phase156_write_guard",
            "realhw_imx510_cmos_dualbase_iso_lut_color_pipeline_report_to_dict",
        )
        for sym in expected_symbols:
            self.assertTrue(hasattr(lab, sym), f"Missing export {sym} on fx3_firmware_lab")
            self.assertIn(sym, lab.__all__, f"Missing {sym} in fx3_firmware_lab.__all__")

    def test_08_clean_room_fixtures_roundtrip_and_counts(self) -> None:
        fx = build_clean_room_realhw_imx510_color_fixtures()
        self.assertEqual(len(fx), 11)
        for key, buf in fx.items():
            self.assertIsInstance(buf, bytes, key)
            self.assertGreater(len(buf), 64, key)

    def test_09_clean_room_report_safety_invariants(self) -> None:
        rep = analyze_realhw_imx510_cmos_dualbase_iso_lut_color_pipeline(clean_room=True)
        self.assertFalse(rep.sensor_cal_p2_writes_permitted)
        self.assertTrue(rep.dual_base_iso_800_12800_hcg_aligned)
        self.assertTrue(rep.slog3_double_bake_prevented)
        self.assertFalse(rep.persistent_emmc_writes_authorized)

    def test_10_run_audit_all_reaches_32_auditors(self) -> None:
        summary = run_audit_all(clean_room=True)
        self.assertTrue(summary["all_checks_passed"])
        audit_keys = [k for k in summary if k.endswith("_audit")]
        self.assertGreaterEqual(len(audit_keys), 32)
        self.assertIn("realhw_imx510_cmos_dualbase_iso_lut_color_pipeline_audit", summary)
        sub_rep = summary["realhw_imx510_cmos_dualbase_iso_lut_color_pipeline_audit"]
        self.assertIsInstance(sub_rep, dict)
        self.assertTrue(sub_rep["all_checks_passed"])

    def test_11_cli_audit_all_clean_room_returns_zero_with_32_keys(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cli_main(["audit-all", "--clean-room", "--json"])
        self.assertEqual(rc, 0)
        obj = json.loads(buf.getvalue())
        self.assertTrue(obj["all_checks_passed"])
        self.assertGreaterEqual(len([k for k in obj if k.endswith("_audit")]), 32)

    def test_12_cli_audit_realhw_imx510_color_pipeline_clean_room(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cli_main(["audit-realhw-imx510-color-pipeline", "--clean-room", "--json"])
        self.assertEqual(rc, 0)
        obj = json.loads(buf.getvalue())
        self.assertTrue(obj["all_checks_passed"])
        self.assertEqual(obj["schema_version"], PHASE_156_SCHEMA)
        self.assertFalse(obj["sensor_cal_p2_writes_permitted"])
        self.assertTrue(obj["dual_base_iso_800_12800_hcg_aligned"])
        self.assertTrue(obj["slog3_double_bake_prevented"])

    # ---- Pillar 1: IMX510 CMOS Sensor Calibration & p2:/setting/psd.bin / defdet.bin ----

    def test_13_imx510_sensor_geometry_constants(self) -> None:
        self.assertEqual(IMX510_SENSOR_MODEL, "IMX510")
        self.assertEqual(IMX510_EFFECTIVE_MP, 10.2)
        self.assertEqual(IMX510_RAW_ACTIVE_RES, (4264, 2408))
        self.assertEqual(IMX510_DCI_4K_RES, (4096, 2160))
        self.assertEqual(IMX510_QFHD_4K_RES, (3840, 2160))
        self.assertEqual(P2_CAL_BLOB_SPAN_BYTES, 5_242_880)

    def test_14_own_body_p2_psd_rdonly_allowed(self) -> None:
        ev = evaluate_imx510_sensor_cal_preservation(
            calibration_source_body="FX3_OWN_BODY",
            target_path="p2:/setting/psd.bin",
            write_requested=False,
        )
        self.assertTrue(ev.valid)
        self.assertEqual(ev.status, "OWN_FX3_P2_CAL_RDONLY_PRESERVED")
        self.assertFalse(ev.sensor_cal_p2_writes_permitted)
        self.assertEqual(ev.sensor_cal_mutation_bytes, 0)
        self.assertEqual(ev.classification, BRIDGE_CLASS_HARD_WRITE_PROTECTED)

    def test_15_own_body_p2_defdet_rdonly_allowed(self) -> None:
        ev = evaluate_imx510_sensor_cal_preservation(
            calibration_source_body="FX3_OWN_BODY",
            target_path="p2:/setting/defdet.bin",
            write_requested=False,
        )
        self.assertTrue(ev.valid)
        self.assertEqual(ev.fx3_defdet_ddr_addr_hex, hex(FX3_P2_DEFDET_DDR_ADDR))
        self.assertEqual(ev.fx3_psd_ddr_addr_hex, hex(FX3_P2_PSD_DDR_ADDR))

    def test_16_donor_fx6_calibration_substitution_blocked(self) -> None:
        ev = evaluate_imx510_sensor_cal_preservation(
            calibration_source_body="FX6_DONOR_CALIBRATION",
            target_path="p2:/setting/psd.bin",
            write_requested=False,
        )
        self.assertFalse(ev.valid)
        self.assertIn("BLOCKED_CROSS_BODY_SENSOR_CAL_SUBSTITUTION", ev.errors[0])
        self.assertEqual(ev.sensor_cal_mutation_bytes, 0)

    def test_17_p2_sensor_cal_write_attempt_blocked(self) -> None:
        ev = evaluate_imx510_sensor_cal_preservation(
            calibration_source_body="FX3_OWN_BODY",
            target_path="p2:/setting/defdet.bin",
            write_requested=True,
        )
        self.assertFalse(ev.valid)
        self.assertIn("BLOCKED_P2_SENSOR_CAL_WRITE", ev.errors[0])
        self.assertFalse(ev.sensor_cal_p2_writes_permitted)
        self.assertEqual(ev.sensor_cal_mutation_bytes, 0)

    def test_18_unrecognized_calibration_target_blocked(self) -> None:
        ev = evaluate_imx510_sensor_cal_preservation(
            calibration_source_body="FX3_OWN_BODY",
            target_path="unknown://cal.bin",
            write_requested=False,
        )
        self.assertFalse(ev.valid)
        self.assertIn("BLOCKED_UNRECOGNIZED_CAL_TARGET", ev.errors[0])

    def test_19_pillar1_backup_subsystems_and_p2_ddr_addresses(self) -> None:
        rep = analyze_realhw_imx510_cmos_dualbase_iso_lut_color_pipeline(clean_room=True)
        p1 = rep.pillar1_imx510_sensor_cal
        self.assertTrue(p1.passed)
        self.assertEqual(p1.fx3_backup_subsystems, EXPECTED_FX3_BACKUP_SUBSYSTEMS_P156)
        self.assertEqual(p1.fx6_backup_subsystems, EXPECTED_FX6_BACKUP_SUBSYSTEMS_P156)
        self.assertEqual(p1.fx3_p2_defdet_addr_hex, hex(FX3_P2_DEFDET_DDR_ADDR))
        self.assertEqual(p1.fx6_p2_defdet_addr_hex, hex(FX6_P2_DEFDET_DDR_ADDR))
        self.assertEqual(p1.fx3_p2_psd_addr_hex, hex(FX3_P2_PSD_DDR_ADDR))
        self.assertEqual(p1.fx6_p2_psd_addr_hex, hex(FX6_P2_PSD_DDR_ADDR))
        self.assertTrue(p1.own_body_rdonly_eval.valid)
        self.assertFalse(p1.cross_body_substitution_blocked.valid)
        self.assertFalse(p1.p2_write_attempt_blocked.valid)

    # ---- Pillar 2: Dual-Base ISO 800 / 12800 (LCG / HCG) & Cine EI ----

    def test_20_cine_ei_low_base_800_lcg_nominal_and_bounds(self) -> None:
        for ei, expected_stops in ((200, -2.0), (400, -1.0), (800, 0.0), (1600, 1.0), (3200, 2.0)):
            ev = evaluate_dual_base_iso_cine_ei(
                exposure_mode="CINE_EI",
                base_iso=800,
                exposure_index=ei,
            )
            self.assertTrue(ev.valid, ev.errors)
            self.assertEqual(ev.base_iso, IMX510_BASE_ISO_LOW_LCG)
            self.assertEqual(ev.gain_stage, "LCG")
            self.assertAlmostEqual(ev.ei_stop_shift, expected_stops, places=4)
            self.assertTrue(ev.hcg_lcg_aligned)
            self.assertTrue(ev.slog3_master_preserved)
            self.assertTrue(ev.m4root_clip_recording)
            self.assertTrue(ev.xml_ei_metadata_intact)

    def test_21_cine_ei_high_base_12800_hcg_nominal_and_bounds(self) -> None:
        for ei, expected_stops in ((3200, -2.0), (6400, -1.0), (12800, 0.0), (25600, 1.0), (51200, 2.0)):
            ev = evaluate_dual_base_iso_cine_ei(
                exposure_mode="CINE_EI",
                base_iso=12800,
                exposure_index=ei,
            )
            self.assertTrue(ev.valid, ev.errors)
            self.assertEqual(ev.base_iso, IMX510_BASE_ISO_HIGH_HCG)
            self.assertEqual(ev.gain_stage, "HCG")
            self.assertAlmostEqual(ev.ei_stop_shift, expected_stops, places=4)
            self.assertIn("HCG_12800", ev.cp_gain_command)

    def test_22_cine_ei_quick_auto_lcg_hcg_switchover_at_3200_ei(self) -> None:
        ev_low = evaluate_dual_base_iso_cine_ei(
            exposure_mode="CINE_EI_QUICK",
            exposure_index=1600,
        )
        self.assertTrue(ev_low.valid)
        self.assertEqual(ev_low.base_iso, 800)
        self.assertEqual(ev_low.gain_stage, "LCG")

        ev_sw = evaluate_dual_base_iso_cine_ei(
            exposure_mode="CINE_EI_QUICK",
            exposure_index=IMX510_CINE_EI_SWITCHOVER_EI,
        )
        self.assertTrue(ev_sw.valid)
        self.assertEqual(ev_sw.base_iso, 12800)
        self.assertEqual(ev_sw.gain_stage, "HCG")

        ev_hi = evaluate_dual_base_iso_cine_ei(
            exposure_mode="CINE_EI_QUICK",
            exposure_index=25600,
        )
        self.assertTrue(ev_hi.valid)
        self.assertEqual(ev_hi.base_iso, 12800)
        self.assertEqual(ev_hi.gain_stage, "HCG")

    def test_23_flexible_iso_supports_wide_range_and_non_slog3(self) -> None:
        ev = evaluate_dual_base_iso_cine_ei(
            exposure_mode="FLEXIBLE_ISO",
            base_iso=12800,
            exposure_index=102400,
            slog3_active=True,
        )
        self.assertTrue(ev.valid)
        self.assertEqual(ev.exposure_mode, "FLEXIBLE_ISO")
        self.assertEqual(ev.gain_stage, "HCG")

    def test_24_invalid_base_iso_rejected(self) -> None:
        ev = evaluate_dual_base_iso_cine_ei(
            exposure_mode="CINE_EI",
            base_iso=2500,
            exposure_index=2500,
        )
        self.assertFalse(ev.valid)
        self.assertIn("BLOCKED_INVALID_IMX510_BASE_ISO", ev.errors[0])

    def test_25_cine_ei_out_of_range_ei_rejected(self) -> None:
        ev_hi = evaluate_dual_base_iso_cine_ei(
            exposure_mode="CINE_EI",
            base_iso=800,
            exposure_index=6400,
        )
        self.assertFalse(ev_hi.valid)
        self.assertIn("BLOCKED_EI_OUT_OF_BASE_RANGE", ev_hi.errors[0])

        ev_lo = evaluate_dual_base_iso_cine_ei(
            exposure_mode="CINE_EI",
            base_iso=12800,
            exposure_index=1600,
        )
        self.assertFalse(ev_lo.valid)
        self.assertIn("BLOCKED_EI_OUT_OF_BASE_RANGE", ev_lo.errors[0])

    def test_26_cine_ei_requires_slog3_and_m4root_clip(self) -> None:
        ev_no_log = evaluate_dual_base_iso_cine_ei(
            exposure_mode="CINE_EI",
            base_iso=800,
            exposure_index=800,
            slog3_active=False,
        )
        self.assertFalse(ev_no_log.valid)
        self.assertIn("BLOCKED_CINE_EI_REQUIRES_SLOG3_MASTER", ev_no_log.errors[0])

        ev_no_m4 = evaluate_dual_base_iso_cine_ei(
            exposure_mode="CINE_EI",
            base_iso=800,
            exposure_index=800,
            m4root_clip_recording=False,
        )
        self.assertFalse(ev_no_m4.valid)
        self.assertIn("BLOCKED_RECORDING_PATH_MUST_TARGET_M4ROOT_CLIP", ev_no_m4.errors[0])

    def test_27_unsupported_exposure_mode_rejected(self) -> None:
        ev = evaluate_dual_base_iso_cine_ei(exposure_mode="AUTO_MAGIC_GAIN")
        self.assertFalse(ev.valid)
        self.assertIn("BLOCKED_UNSUPPORTED_EXPOSURE_MODE", ev.errors[0])

    def test_28_cine_ei_ranges_and_modes_constants(self) -> None:
        self.assertEqual(IMX510_CINE_EI_LOW_RANGE, (200, 3200))
        self.assertEqual(IMX510_CINE_EI_HIGH_RANGE, (3200, 51200))
        self.assertEqual(VALID_DUAL_BASE_ISOS_P156, (800, 12800))
        self.assertEqual(VALID_EXPOSURE_MODES_P156, ("CINE_EI", "CINE_EI_QUICK", "FLEXIBLE_ISO"))

    # ---- Pillar 3: S-Log3, S-Cinetone, 709tone & 16-Slot .cube 3D MLUT ----

    def test_29_slog3_mlut_monitor_only_preserves_unbaked_master(self) -> None:
        ev = evaluate_cube_mlut_color_pipeline(
            base_look="S-Gamut3.Cine/S-Log3",
            cube_grid_size=33,
            lut_slot=1,
            sd_lut_path="/mnt/sd/PRIVATE/SONY/PRO/LUT/S709C.cube",
            ram_staging_path="/tmp/fx6_mlut_slot01.dma",
            mlut_lcd_hdmi_on=True,
            lut_burn_in_requested=False,
        )
        self.assertTrue(ev.valid, ev.errors)
        self.assertEqual(ev.status, "SLOG3_UNBAKED_MASTER_WITH_MLUT_MONITOR")
        self.assertTrue(ev.is_raw_or_log_master)
        self.assertTrue(ev.slog3_double_bake_prevented)
        self.assertTrue(ev.nvs_overflow_prevented)
        self.assertIn("MLUT_L3D_ON", ev.isp_stages_active)

    def test_30_all_16_cube_slots_and_both_17_33_grids_supported(self) -> None:
        for grid in SUPPORTED_CUBE_GRID_SIZES:
            for slot in (1, 8, MAX_USER_LUT_SLOTS):
                ev = evaluate_cube_mlut_color_pipeline(
                    base_look="S-Gamut3/S-Log3",
                    cube_grid_size=grid,
                    lut_slot=slot,
                    sd_lut_path=f"{SD_USER_LUT_DIR}Slot{slot}_{grid}.cube",
                    ram_staging_path=f"ram://mlut_slot{slot}.dma",
                )
                self.assertTrue(ev.valid, ev.errors)

    def test_31_all_four_base_looks_supported(self) -> None:
        for look in VALID_BASE_LOOKS_P156:
            ev = evaluate_cube_mlut_color_pipeline(
                base_look=look,
                cube_grid_size=33,
                lut_slot=2,
                mlut_lcd_hdmi_on=False,
            )
            self.assertTrue(ev.valid, ev.errors)
            self.assertEqual(ev.isp_stages_active, ("MLUT_BYPASS_LOG",))

    def test_32_silent_slog3_double_bake_blocked(self) -> None:
        ev = evaluate_cube_mlut_color_pipeline(
            base_look="S-Gamut3.Cine/S-Log3",
            lut_burn_in_requested=True,
            explicit_burn_in_confirmed=False,
        )
        self.assertFalse(ev.valid)
        self.assertTrue(ev.slog3_double_bake_prevented)
        self.assertTrue(any("BLOCKED_SILENT_SLOG3_DOUBLE_BAKE" in e for e in ev.errors))

    def test_33_confirmed_burnin_on_slog3_still_blocked_to_protect_log_master(self) -> None:
        ev = evaluate_cube_mlut_color_pipeline(
            base_look="S-Gamut3/S-Log3",
            lut_burn_in_requested=True,
            explicit_burn_in_confirmed=True,
        )
        self.assertFalse(ev.valid)
        self.assertIn("BLOCKED_SLOG3_MASTER_DOUBLE_BAKE", ev.errors[0])

    def test_34_confirmed_burnin_allowed_on_709tone_and_scinetone(self) -> None:
        for look in ("S-Cinetone", "709tone"):
            ev = evaluate_cube_mlut_color_pipeline(
                base_look=look,
                lut_burn_in_requested=True,
                explicit_burn_in_confirmed=True,
            )
            self.assertTrue(ev.valid, ev.errors)

    def test_35_invalid_cube_grid_size_and_slot_bounds_blocked(self) -> None:
        ev_grid = evaluate_cube_mlut_color_pipeline(cube_grid_size=65)
        self.assertFalse(ev_grid.valid)
        self.assertIn("BLOCKED_UNSUPPORTED_CUBE_GRID_SIZE", ev_grid.errors[0])

        for bad_slot in (0, 17, -1):
            ev_slot = evaluate_cube_mlut_color_pipeline(lut_slot=bad_slot)
            self.assertFalse(ev_slot.valid)
            self.assertIn("BLOCKED_LUT_SLOT_OUT_OF_RANGE", ev_slot.errors[0])

    def test_36_bad_sd_lut_path_and_oversized_cube_blocked(self) -> None:
        ev_path = evaluate_cube_mlut_color_pipeline(sd_lut_path="/tmp/bad_lut.txt")
        self.assertFalse(ev_path.valid)
        self.assertIn("BLOCKED_SD_LUT_PATH", ev_path.errors[0])

        ev_big = evaluate_cube_mlut_color_pipeline(cube_bytes=MAX_CUBE_FILE_BYTES_P156 + 1)
        self.assertFalse(ev_big.valid)
        self.assertIn("BLOCKED_CUBE_FILE_SIZE_OVERFLOW", ev_big.errors[0])

    def test_37_persistent_nvs_lut_staging_blocked(self) -> None:
        for bad_stage in ("p30:/usr/data/lut/User1.cube", "/dev/nflasha30/User1.cube", "p23:/INFO/LUT.TXT"):
            ev = evaluate_cube_mlut_color_pipeline(ram_staging_path=bad_stage)
            self.assertFalse(ev.valid, bad_stage)
            self.assertIn("BLOCKED_PERSISTENT_NVS_LUT_STAGING", ev.errors[0])

    def test_38_pillar3_s709_cube_33_parsed_cleanly(self) -> None:
        rep = analyze_realhw_imx510_cmos_dualbase_iso_lut_color_pipeline(clean_room=True)
        p3 = rep.pillar3_slog3_cube_mlut
        self.assertTrue(p3.passed)
        self.assertEqual(p3.s709_cube_grid_size, 33)
        self.assertGreater(p3.s709_cube_bytes, 64)
        self.assertEqual(APPFW_USER_LUT_REL_PATH, "/Private/Sony/PRO/LUT")

    # ---- Pillar 4: Write-Guard, ELF ABI & 12-Touchpoint Matrix ----

    def test_39_write_guard_allows_volatile_ram_and_sd_read_paths(self) -> None:
        for path in ("/tmp/fx6_mlut_slot01.dma", "ram://cine_ei_shadow.json", "/mnt/sd/PRIVATE/SONY/PRO/LUT/S709.cube"):
            wg = evaluate_phase156_write_guard(path)
            self.assertTrue(wg.valid, path)
            self.assertTrue(wg.volatile_or_sd_allowed)
            self.assertFalse(wg.persistent_write_blocked)
            self.assertFalse(wg.sensor_cal_p2_writes_permitted)
            self.assertFalse(wg.persistent_emmc_writes_authorized)
            self.assertEqual(wg.emmc_mutation_bytes, 0)
            self.assertEqual(wg.sensor_cal_mutation_bytes, 0)

    def test_40_write_guard_blocks_all_p2_p23_p30_and_emmc_targets(self) -> None:
        bad_targets = (
            "p2:/setting/psd.bin",
            "p2:/setting/defdet.bin",
            "p2:/Backup.bin",
            "p23:/INFO/WIFI_INF.TXT",
            "p30:/usr/data/lut/User1.cube",
            "/dev/nflasha2",
            "/dev/cnflasha30",
            "/dev/mmcblk0p2",
        )
        for tgt in bad_targets:
            wg = evaluate_phase156_write_guard(tgt)
            self.assertFalse(wg.valid, tgt)
            self.assertTrue(wg.persistent_write_blocked, tgt)
            self.assertFalse(wg.sensor_cal_p2_writes_permitted)
            self.assertFalse(wg.persistent_emmc_writes_authorized)
            self.assertEqual(wg.emmc_mutation_bytes, 0)

    def test_41_immutable_partition_constants_complete(self) -> None:
        self.assertIn("p2:/setting/psd.bin", P2_SENSOR_CAL_IMMUTABLE_PATHS)
        self.assertIn("p2:/setting/defdet.bin", P2_SENSOR_CAL_IMMUTABLE_PATHS)
        self.assertIn("p23:/INFO", P2_P23_P30_LUT_IMMUTABLE_PARTITIONS)
        self.assertIn("p30:/usr/data/lut", P2_P23_P30_LUT_IMMUTABLE_PARTITIONS)

    def test_42_compatibility_matrix_has_12_touchpoints_and_all_subsystems(self) -> None:
        matrix = build_phase156_imx510_color_matrix()
        self.assertEqual(matrix.total_touchpoints, 12)
        self.assertEqual(sum(matrix.class_counts.values()), 12)
        self.assertEqual(
            set(matrix.subsystem_counts.keys()),
            {"SENSOR_CAL", "DUAL_BASE_ISO", "CUBE_MLUT", "NVS_ISOLATION"},
        )
        self.assertGreaterEqual(matrix.class_counts[BRIDGE_CLASS_NATIVE_PASSTHROUGH], 1)
        self.assertGreaterEqual(matrix.class_counts[BRIDGE_CLASS_SHIM_TRANSLATED], 1)
        self.assertGreaterEqual(matrix.class_counts[BRIDGE_CLASS_MASKED_ABSENT_HW], 1)
        self.assertGreaterEqual(matrix.class_counts[BRIDGE_CLASS_HARD_WRITE_PROTECTED], 1)

    def test_43_pillar4_elf_export_import_counts_verified(self) -> None:
        rep = analyze_realhw_imx510_cmos_dualbase_iso_lut_color_pipeline(clean_room=True)
        p4 = rep.pillar4_nvs_isolation_matrix
        self.assertTrue(p4.passed)
        self.assertEqual(p4.fx3_sencore_summary.export_count, EXPECTED_SENCORE_EXPORTS)
        self.assertEqual(p4.fx6_sencore_summary.export_count, EXPECTED_SENCORE_EXPORTS)
        self.assertEqual(p4.fx3_mpr_summary.export_count, EXPECTED_FX3_MPR_EXPORTS_P156)
        self.assertEqual(p4.fx3_mpr_summary.import_count, EXPECTED_FX3_MPR_IMPORTS_P156)
        self.assertEqual(p4.fx6_mpr_summary.export_count, EXPECTED_FX6_MPR_EXPORTS_P156)
        self.assertEqual(p4.fx6_mpr_summary.import_count, EXPECTED_FX6_MPR_IMPORTS_P156)

    def test_44_local_donor_mode_smoke_or_clean_fallback(self) -> None:
        rep = analyze_realhw_imx510_cmos_dualbase_iso_lut_color_pipeline(clean_room=False)
        self.assertTrue(rep.all_checks_passed, rep.errors)
        if rep.mode == "LOCAL_DONOR_VERIFIED":
            p2 = rep.pillar2_dual_base_iso_cine_ei
            p3 = rep.pillar3_slog3_cube_mlut
            self.assertGreater(p2.fx3_appfw_markers["BASE_ISO_LOW_800"], 0)
            self.assertGreater(p2.fx3_appfw_markers["BASE_ISO_HIGH_12800"], 0)
            self.assertGreater(p3.fx6_sencore_lut_markers["SET_MONITOR_MLUT"], 0)
            self.assertGreater(p3.fx3_cpapp_mlut_markers["MLUT_L3D_ON"], 0)
            self.assertGreater(p3.fx6_cpapp_mlut_markers["MLUT_L3D_ON"], 0)

    def test_45_corrupted_cpapp_markers_fail_closed(self) -> None:
        bad_fx = build_clean_room_realhw_imx510_color_fixtures()
        bad_fx["fx3_cpapp"] = b"CPAPP_EMPTY\x00"
        with (
            mock.patch(
                "fx3_firmware_lab.realhw_imx510_cmos_dualbase_iso_lut_color_pipeline_auditor.build_clean_room_realhw_imx510_color_fixtures",
                return_value=bad_fx,
            ),
        ):
            rep = analyze_realhw_imx510_cmos_dualbase_iso_lut_color_pipeline(clean_room=True)
        self.assertFalse(rep.all_checks_passed)
        self.assertFalse(rep.pillar1_imx510_sensor_cal.passed)
        self.assertFalse(rep.pillar2_dual_base_iso_cine_ei.passed)
        self.assertFalse(rep.pillar3_slog3_cube_mlut.passed)

    def test_46_corrupted_s709_cube_header_fails_closed(self) -> None:
        bad_fx = build_clean_room_realhw_imx510_color_fixtures()
        bad_fx["fx6_s709_cube_header"] = b"# corrupt\nLUT_3D_SIZE 16\n"
        with (
            mock.patch(
                "fx3_firmware_lab.realhw_imx510_cmos_dualbase_iso_lut_color_pipeline_auditor.build_clean_room_realhw_imx510_color_fixtures",
                return_value=bad_fx,
            ),
        ):
            rep = analyze_realhw_imx510_cmos_dualbase_iso_lut_color_pipeline(clean_room=True)
        self.assertFalse(rep.all_checks_passed)
        self.assertFalse(rep.pillar3_slog3_cube_mlut.passed)

    def test_47_report_to_dict_top_level_fields_complete(self) -> None:
        rep = analyze_realhw_imx510_cmos_dualbase_iso_lut_color_pipeline(clean_room=True)
        d = realhw_imx510_cmos_dualbase_iso_lut_color_pipeline_report_to_dict(rep)
        for key in (
            "schema_version",
            "phase_version",
            "mode",
            "all_checks_passed",
            "o_rdonly_enforced",
            "sensor_cal_p2_writes_permitted",
            "sensor_cal_mutation_bytes",
            "dual_base_iso_800_12800_hcg_aligned",
            "slog3_double_bake_prevented",
            "persistent_emmc_writes_authorized",
            "emmc_mutation_bytes",
            "calibration_mutation_bytes",
            "donor_file_sizes",
            "pillar1_imx510_sensor_cal",
            "pillar2_dual_base_iso_cine_ei",
            "pillar3_slog3_cube_mlut",
            "pillar4_nvs_isolation_matrix",
            "report_sha256",
            "errors",
        ):
            self.assertIn(key, d)

    def test_48_unrecognized_write_guard_path_blocked(self) -> None:
        wg = evaluate_phase156_write_guard("/etc/passwd")
        self.assertFalse(wg.valid)
        self.assertTrue(wg.persistent_write_blocked)
        self.assertIn("BLOCKED_UNKNOWN_STORAGE_TARGET", wg.errors[0])


if __name__ == "__main__":
    unittest.main()
