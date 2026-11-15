"""Unit tests for Phase 65 White Balance (Shockless WB / ATW / WHT BAL soft-map), Base Look, Paint 3x3 Color Matrix (R-G..B-G), Knee/Black Gamma & cnflasha Factory Calibration Auditor.

Executes rapidly in BOTH Local Donor (`os.O_RDONLY`) and
`FX3_FX6_FORCE_CLEAN_ROOM=1` modes.
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
from fx3_firmware_lab.wb_color_matrix_and_look_auditor import (
    CANONICAL_BASE_LOOKS,
    CP_SHARED_CALIB_MARKERS,
    CP_SHARED_MLUT_MARKERS,
    FX3_APPFW_LOOK_MARKERS,
    FX3_APPFW_PAINT_KNEE_BLACK_MARKERS,
    FX3_APPFW_WB_MARKERS,
    FX3_CP_KNEE_BLACK_MARKERS,
    FX3_CP_WB_MARKERS,
    FX6_APPFW_LOOK_MARKERS,
    FX6_APPFW_PAINT_MATRIX_MARKERS,
    FX6_APPFW_WB_MARKERS,
    FX6_CP_PAINT_MARKERS,
    FX6_CP_WBGAIN_MARKERS,
    FX6_CP_WB_MARKERS,
    PHASE_65_SCHEMA,
    PHASE_65_VERSION,
    SHARED_APPFW_CALIB_MARKERS,
    VALID_WB_SWITCH_POSITIONS,
    WB_PRESET_KELVIN_MAP,
    WbColorMatrixAndLookReport,
    analyze_wb_color_matrix_and_look,
    build_and_verify_paint_color_matrix,
    build_clean_room_wb_color_matrix_fixtures,
    evaluate_base_look_routing,
    evaluate_factory_wb_calibration_immutability,
    evaluate_multi_matrix_and_knee_black_bounds,
    evaluate_shockless_wb_slew,
    evaluate_wb_switch_soft_mapping,
    evaluate_white_balance_kelvin_mired,
    kelvin_to_mired,
    verify_raw_3x3_color_matrix,
    wb_color_matrix_and_look_report_to_dict,
)


PKG_ROOT = Path(__file__).resolve().parents[1]


class TestActiveWbColorMatrixAndLook(unittest.TestCase):
    _active_report: Optional[WbColorMatrixAndLookReport] = None

    @classmethod
    def setUpClass(cls) -> None:
        cls._active_report = analyze_wb_color_matrix_and_look()

    def test_01_active_mode_passes_with_o_rdonly_and_10_artifacts(self) -> None:
        rep = self._active_report
        assert rep is not None
        self.assertTrue(rep.all_checks_passed, msg=f"Errors: {rep.errors}")
        self.assertEqual(rep.schema_version, PHASE_65_SCHEMA)
        self.assertEqual(rep.phase_version, PHASE_65_VERSION)
        self.assertTrue(rep.o_rdonly_enforced)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertEqual(rep.calibration_mutation_bytes, 0)
        self.assertEqual(rep.cp_mutation_bytes, 0)
        self.assertEqual(len(rep.report_sha256), 64)
        self.assertEqual(len(rep.donor_file_sizes), 10)
        if not is_forced_clean_room() and rep.mode == "LOCAL_DONOR_VERIFIED":
            self.assertGreater(rep.donor_file_sizes["fx3_appfw"], 70_000_000)
            self.assertGreater(rep.donor_file_sizes["fx6_appfw"], 45_000_000)
            self.assertGreater(rep.donor_file_sizes["fx3_cpapp"], 10_000_000)
            self.assertGreater(rep.donor_file_sizes["fx6_cpapp"], 10_000_000)

    def test_02_active_report_json_serializable_without_raw_bytes(self) -> None:
        rep = self._active_report
        assert rep is not None
        payload = wb_color_matrix_and_look_report_to_dict(rep)
        encoded = json.dumps(payload, sort_keys=True)
        self.assertNotRegex(encoded, r'(?<![0-9A-Za-z_/.-])b[\'"]')
        decoded = json.loads(encoded)
        self.assertEqual(decoded["report_sha256"], rep.report_sha256)
        self.assertTrue(decoded["all_checks_passed"])

    def test_03_pillar_a_white_balance_markers_and_uxc_labels(self) -> None:
        rep = self._active_report
        assert rep is not None
        pa = rep.pillar_a_white_balance
        self.assertTrue(pa.passed)
        self.assertEqual(pa.missing_gpio_faults, 0)
        self.assertEqual(pa.fx3_appfw_wb_markers, FX3_APPFW_WB_MARKERS)
        self.assertEqual(pa.fx3_unexpected_phys_switch_markers, ())
        self.assertEqual(pa.fx6_appfw_wb_markers, FX6_APPFW_WB_MARKERS)
        self.assertEqual(pa.fx3_cp_wb_markers, FX3_CP_WB_MARKERS)
        self.assertEqual(pa.fx6_cp_wb_markers, FX6_CP_WB_MARKERS)
        self.assertEqual(pa.uxc_wb_labels["fx3_white_balance"], "White Balance")
        self.assertEqual(pa.uxc_wb_labels["fx3_color_temp"], "Color Temp.")
        self.assertEqual(pa.uxc_wb_labels["fx6_atw"], "ATW")
        self.assertEqual(pa.uxc_wb_labels["fx6_shockless_white"], "Shockless White")
        self.assertEqual(pa.uxc_wb_labels["fx6_preset_3200k"], "Preset 3200K")
        self.assertEqual(pa.uxc_wb_labels["fx6_preset_4300k"], "Preset 4300K")
        self.assertEqual(pa.uxc_wb_labels["fx6_5600k"], "5600K")
        self.assertEqual(pa.uxc_wb_labels["fx6_memory_a"], "Memory A")
        self.assertEqual(pa.uxc_wb_labels["fx6_memory_b"], "Memory B")

    def test_04_pillar_b_base_look_markers_and_uxc_labels(self) -> None:
        rep = self._active_report
        assert rep is not None
        pb = rep.pillar_b_base_look
        self.assertTrue(pb.passed)
        self.assertEqual(pb.fx3_appfw_look_markers, FX3_APPFW_LOOK_MARKERS)
        self.assertEqual(pb.fx6_appfw_look_markers, FX6_APPFW_LOOK_MARKERS)
        self.assertEqual(pb.fx3_cp_mlut_markers, CP_SHARED_MLUT_MARKERS)
        self.assertEqual(pb.fx6_cp_mlut_markers, CP_SHARED_MLUT_MARKERS)
        self.assertEqual(len(pb.canonical_looks_verified), 8)
        self.assertEqual(pb.uxc_look_labels["fx6_s_cinetone"], "S-Cinetone")
        self.assertEqual(pb.uxc_look_labels["fx6_s_log3"], "S-Log3")
        self.assertEqual(pb.uxc_look_labels["fx6_709_800"], "709(800%)")
        self.assertEqual(pb.uxc_look_labels["fx6_itu709"], "ITU709")
        self.assertEqual(pb.uxc_look_labels["fx6_hlg_live"], "HLG Live")
        self.assertEqual(pb.uxc_look_labels["fx6_hlg_natural"], "HLG Natural")
        self.assertEqual(pb.uxc_look_labels["fx6_mlut"], "MLUT")
        self.assertEqual(pb.uxc_look_labels["fx3_itu709_matrix"], "ITU709 Matrix")

    def test_05_pillar_c_paint_matrix_knee_markers_and_uxc_labels(self) -> None:
        rep = self._active_report
        assert rep is not None
        pc = rep.pillar_c_paint_matrix_knee
        self.assertTrue(pc.passed)
        self.assertEqual(pc.fx6_appfw_paint_markers, FX6_APPFW_PAINT_MATRIX_MARKERS)
        self.assertEqual(pc.fx3_appfw_knee_black_markers, FX3_APPFW_PAINT_KNEE_BLACK_MARKERS)
        self.assertEqual(pc.fx6_cp_paint_markers, FX6_CP_PAINT_MARKERS)
        self.assertEqual(pc.fx3_cp_knee_black_markers, FX3_CP_KNEE_BLACK_MARKERS)
        self.assertEqual(pc.uxc_paint_labels["fx6_user_matrix_rg"], "User Matrix R-G")
        self.assertEqual(pc.uxc_paint_labels["fx6_user_matrix_bg"], "User Matrix B-G")
        self.assertEqual(pc.uxc_paint_labels["fx6_multi_matrix"], "Multi Matrix")
        self.assertEqual(pc.uxc_paint_labels["fx6_knee_point"], "Knee Point")
        self.assertEqual(pc.uxc_paint_labels["fx6_knee_slope"], "Knee Slope")
        self.assertEqual(pc.uxc_paint_labels["fx6_black_gamma"], "Black Gamma")
        self.assertTrue(pc.tweaked_matrix_eval.white_point_preserved)

    def test_06_pillar_d_factory_calibration_markers_and_zero_mutation(self) -> None:
        rep = self._active_report
        assert rep is not None
        pd = rep.pillar_d_factory_calibration
        self.assertTrue(pd.passed)
        self.assertEqual(pd.calibration_mutation_bytes, 0)
        self.assertEqual(pd.cp_mutation_bytes, 0)
        self.assertFalse(pd.persistent_emmc_writes_authorized)
        self.assertEqual(pd.fx3_appfw_calib_markers, SHARED_APPFW_CALIB_MARKERS)
        self.assertEqual(pd.fx6_appfw_calib_markers, SHARED_APPFW_CALIB_MARKERS)
        self.assertEqual(pd.fx3_cp_calib_markers, CP_SHARED_CALIB_MARKERS)
        self.assertEqual(pd.fx6_cp_calib_markers, CP_SHARED_CALIB_MARKERS)
        self.assertEqual(pd.fx6_cp_wbgain_markers, FX6_CP_WBGAIN_MARKERS)


class TestPillarAWhiteBalanceMathAndSwitchMapping(unittest.TestCase):
    def test_07_kelvin_to_mired_exact_conversion_and_presets(self) -> None:
        self.assertAlmostEqual(kelvin_to_mired(3200), 312.5, places=6)
        self.assertAlmostEqual(kelvin_to_mired(4300), 1_000_000.0 / 4300.0, places=6)
        self.assertAlmostEqual(kelvin_to_mired(5600), 1_000_000.0 / 5600.0, places=6)
        self.assertAlmostEqual(kelvin_to_mired(10000), 100.0, places=6)
        self.assertEqual(WB_PRESET_KELVIN_MAP["TUNGSTEN_3200K"], 3200)
        self.assertEqual(WB_PRESET_KELVIN_MAP["FLUORESCENT_4300K"], 4300)
        self.assertEqual(WB_PRESET_KELVIN_MAP["DAYLIGHT_5600K"], 5600)
        with self.assertRaises(ValueError):
            kelvin_to_mired(0.0)
        with self.assertRaises(ValueError):
            kelvin_to_mired(float("nan"))

    def test_08_memory_ab_kelvin_range_2000_to_15000_and_tint_bounds(self) -> None:
        r_min = evaluate_white_balance_kelvin_mired(kelvin=2000, tint_cc=-99, step_k=100)
        self.assertTrue(r_min.valid)
        self.assertAlmostEqual(r_min.mired, 500.0, places=4)

        r_50 = evaluate_white_balance_kelvin_mired(kelvin=5650, tint_cc=12, step_k=50)
        self.assertTrue(r_50.valid)

        r_max = evaluate_white_balance_kelvin_mired(kelvin=15000, tint_cc=99, step_k=100)
        self.assertTrue(r_max.valid)
        self.assertLess(r_min.rb_gain_ratio, r_max.rb_gain_ratio)

    def test_09_rejects_out_of_range_kelvin_step_or_tint(self) -> None:
        self.assertFalse(evaluate_white_balance_kelvin_mired(kelvin=1900).valid)
        self.assertFalse(evaluate_white_balance_kelvin_mired(kelvin=15100).valid)
        self.assertFalse(evaluate_white_balance_kelvin_mired(kelvin=5650, step_k=100).valid)
        self.assertFalse(evaluate_white_balance_kelvin_mired(kelvin=5625, step_k=50).valid)
        self.assertFalse(evaluate_white_balance_kelvin_mired(kelvin=5600, tint_cc=-100).valid)
        self.assertFalse(evaluate_white_balance_kelvin_mired(kelvin=5600, tint_cc=100).valid)
        self.assertFalse(evaluate_white_balance_kelvin_mired(kelvin=5600, step_k=25).valid)

    def test_10_shockless_wb_slew_damping_ordering_off_1_2_3(self) -> None:
        off = evaluate_shockless_wb_slew(start_kelvin=3200, target_kelvin=5600, shockless_level="OFF", dt_sec=0.8)
        lvl1 = evaluate_shockless_wb_slew(start_kelvin=3200, target_kelvin=5600, shockless_level="1", dt_sec=0.8)
        lvl2 = evaluate_shockless_wb_slew(start_kelvin=3200, target_kelvin=5600, shockless_level="2", dt_sec=0.8)
        lvl3 = evaluate_shockless_wb_slew(start_kelvin=3200, target_kelvin=5600, shockless_level="3", dt_sec=0.8)

        self.assertTrue(all(ev.valid and ev.monotonic_transition for ev in (off, lvl1, lvl2, lvl3)))
        self.assertEqual(off.intermediate_kelvin, 5600)
        self.assertAlmostEqual(off.damping_alpha, 1.0, places=6)
        # Slower level -> smaller alpha -> intermediate Kelvin closer to start (3200K)
        self.assertGreater(lvl1.damping_alpha, lvl2.damping_alpha)
        self.assertGreater(lvl2.damping_alpha, lvl3.damping_alpha)
        self.assertGreater(lvl1.intermediate_kelvin, lvl2.intermediate_kelvin)
        self.assertGreater(lvl2.intermediate_kelvin, lvl3.intermediate_kelvin)

    def test_11_shockless_wb_rejects_invalid_level_or_negative_dt(self) -> None:
        self.assertFalse(evaluate_shockless_wb_slew(shockless_level="4").valid)
        self.assertFalse(evaluate_shockless_wb_slew(dt_sec=-0.1).valid)
        self.assertFalse(evaluate_shockless_wb_slew(start_kelvin=1500).valid)

    def test_12_fx3_wht_bal_switch_soft_mapping_all_positions_and_gpio_guard(self) -> None:
        for pos in VALID_WB_SWITCH_POSITIONS:
            res = evaluate_wb_switch_soft_mapping(requested_position=pos, shockless_level="2")
            self.assertTrue(res.valid)
            self.assertFalse(res.fx3_physical_wht_bal_switch_present)
            self.assertEqual(res.missing_gpio_faults, 0)
            self.assertEqual(res.status, "FX3_WHT_BAL_SOFT_MAPPED_ZERO_GPIO_FAULTS")

        bad_gpio = evaluate_wb_switch_soft_mapping(
            requested_position="MEMORY_B",
            missing_gpio_write_attempted=True,
        )
        self.assertFalse(bad_gpio.valid)
        self.assertEqual(bad_gpio.missing_gpio_faults, 1)
        self.assertFalse(evaluate_wb_switch_soft_mapping(requested_position="INVALID_POS").valid)


class TestPillarBBaseLookAndGammaGamut(unittest.TestCase):
    def test_13_all_8_canonical_base_looks_verified(self) -> None:
        self.assertEqual(len(CANONICAL_BASE_LOOKS), 8)
        for look in CANONICAL_BASE_LOOKS:
            disp = "HDR_HLG" if "HLG" in look else "SDR_BT709"
            slot = 3 if look == "User 3D LUT (MLUT)" else None
            res = evaluate_base_look_routing(
                look_id=look,
                target_display=disp,
                mlut_internal_rec=(look == "User 3D LUT (MLUT)"),
                mlut_monitor_out=True,
                user_lut_slot=slot,
            )
            self.assertTrue(res.valid, msg=f"Failed look={look}: {res.errors}")
            self.assertEqual(res.parity_status, "FX6_V601_FX3_V702_PARITY")

    def test_14_base_look_rejects_display_mismatch_and_invalid_user_lut_slot(self) -> None:
        self.assertFalse(evaluate_base_look_routing(look_id="HLG Live", target_display="SDR_BT709").valid)
        self.assertFalse(evaluate_base_look_routing(look_id="S-Cinetone", target_display="HDR_HLG").valid)
        self.assertFalse(evaluate_base_look_routing(look_id="User 3D LUT (MLUT)", user_lut_slot=None).valid)
        self.assertFalse(evaluate_base_look_routing(look_id="User 3D LUT (MLUT)", user_lut_slot=17).valid)
        self.assertFalse(evaluate_base_look_routing(look_id="UnknownLook").valid)


class TestPillarCPaintMatrixAndKneeMath(unittest.TestCase):
    def test_15_paint_3x3_matrix_identity_and_swept_off_diagonal_row_sums_equal_one(self) -> None:
        ident = build_and_verify_paint_color_matrix()
        self.assertTrue(ident.valid)
        self.assertEqual(ident.row_sums, (1.0, 1.0, 1.0))
        self.assertEqual(ident.neutral_grey_output, (1.0, 1.0, 1.0))
        self.assertAlmostEqual(ident.determinant, 1.0, places=9)

        # Sweep across positive/negative R-G..B-G coefficients: neutral grey [1, 1, 1] must never tint-shift
        for rg, rb, gr, gb, br, bg, lvl in (
            (99.0, -99.0, 50.0, -25.0, -40.0, 80.0, 20.0),
            (-99.0, 99.0, -70.0, 60.0, 30.0, -90.0, -30.0),
            (45.0, 45.0, -45.0, -45.0, 20.0, 20.0, 99.0),
        ):
            res = build_and_verify_paint_color_matrix(
                rg=rg, rb=rb, gr=gr, gb=gb, br=br, bg=bg, level=lvl
            )
            self.assertTrue(res.valid, msg=f"Errors: {res.errors}")
            self.assertTrue(res.white_point_preserved)
            self.assertLessEqual(res.max_row_sum_error, 1e-9)
            for channel in res.neutral_grey_output:
                self.assertAlmostEqual(channel, 1.0, places=9)

    def test_16_paint_3x3_matrix_explicitly_blocks_white_point_tint_shift_and_degenerate_matrices(self) -> None:
        # Row 0 sums to 1.15 -> neutral grey shifts reddish
        tinted = verify_raw_3x3_color_matrix(
            [
                [1.15, 0.0, 0.0],
                [0.0, 1.0, 0.0],
                [0.0, 0.0, 1.0],
            ]
        )
        self.assertFalse(tinted.valid)
        self.assertFalse(tinted.white_point_preserved)
        self.assertEqual(tinted.status, "BLOCKED_PAINT_MATRIX_WHITE_POINT_DRIFT")
        self.assertAlmostEqual(tinted.max_row_sum_error, 0.15, places=6)

        # Singular matrix (rows identical -> det=0)
        singular = verify_raw_3x3_color_matrix(
            [
                [1.0 / 3.0, 1.0 / 3.0, 1.0 / 3.0],
                [1.0 / 3.0, 1.0 / 3.0, 1.0 / 3.0],
                [1.0 / 3.0, 1.0 / 3.0, 1.0 / 3.0],
            ]
        )
        self.assertFalse(singular.valid)
        self.assertFalse(build_and_verify_paint_color_matrix(rg=120.0).valid)

    def test_17_knee_point_75_to_109_pct_slope_and_black_gamma_bounds(self) -> None:
        ok_lo = evaluate_multi_matrix_and_knee_black_bounds(
            knee_mode="MANUAL", knee_point_pct=75.0, knee_slope=-99, black_level=-99, black_gamma_level=-99, black_gamma_range="NARROW"
        )
        ok_hi = evaluate_multi_matrix_and_knee_black_bounds(
            knee_mode="AUTO", knee_point_pct=109.0, knee_slope=99, black_level=99, black_gamma_level=99, black_gamma_range="WIDE", multi_matrix_hue=99, multi_matrix_sat=-99
        )
        self.assertTrue(ok_lo.valid)
        self.assertTrue(ok_hi.valid)

        self.assertFalse(evaluate_multi_matrix_and_knee_black_bounds(knee_point_pct=74.9).valid)
        self.assertFalse(evaluate_multi_matrix_and_knee_black_bounds(knee_point_pct=109.1).valid)
        self.assertFalse(evaluate_multi_matrix_and_knee_black_bounds(knee_slope=100).valid)
        self.assertFalse(evaluate_multi_matrix_and_knee_black_bounds(black_level=-100).valid)
        self.assertFalse(evaluate_multi_matrix_and_knee_black_bounds(black_gamma_level=100).valid)
        self.assertFalse(evaluate_multi_matrix_and_knee_black_bounds(black_gamma_range="ULTRA").valid)
        self.assertFalse(evaluate_multi_matrix_and_knee_black_bounds(multi_matrix_hue=100).valid)


class TestPillarDFactoryCalibrationImmutability(unittest.TestCase):
    def test_18_cnflasha_and_stock_cp_calibration_zero_mutation_enforced(self) -> None:
        ok_ro = evaluate_factory_wb_calibration_immutability(
            target_partition="/dev/cnflasha16",
            operation="READ_ONLY_AUDIT",
            calibration_mutation_bytes=0,
            cp_mutation_bytes=0,
            persistent_emmc_writes_authorized=False,
        )
        self.assertTrue(ok_ro.valid)
        self.assertTrue(ok_ro.ram_shadow_isolated)

        ok_ram = evaluate_factory_wb_calibration_immutability(
            target_partition="p2:/Backup.bin",
            operation="RAM_SHADOW_USER_WB_OFFSET",
        )
        self.assertTrue(ok_ram.valid)

        self.assertFalse(
            evaluate_factory_wb_calibration_immutability(calibration_mutation_bytes=16).valid
        )
        self.assertFalse(
            evaluate_factory_wb_calibration_immutability(cp_mutation_bytes=4).valid
        )
        self.assertFalse(
            evaluate_factory_wb_calibration_immutability(persistent_emmc_writes_authorized=True).valid
        )
        self.assertFalse(
            evaluate_factory_wb_calibration_immutability(operation="WRITE_CNFLASHA_RAW").valid
        )


class TestCleanRoomFaultInjectionAndCli(unittest.TestCase):
    def test_19_forced_clean_room_deterministic_equivalence_and_env_fallback(self) -> None:
        r1 = analyze_wb_color_matrix_and_look(clean_room=True)
        r2 = analyze_wb_color_matrix_and_look(clean_room=True)
        self.assertEqual(r1.mode, "CLEAN_ROOM_SYNTHETIC_VERIFIED")
        self.assertTrue(r1.all_checks_passed, msg=f"Errors: {r1.errors}")
        self.assertEqual(r1.report_sha256, r2.report_sha256)

        with patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            r_env = analyze_wb_color_matrix_and_look()
        self.assertEqual(r_env.mode, "CLEAN_ROOM_SYNTHETIC_VERIFIED")
        self.assertTrue(r_env.all_checks_passed)

        with patch(
            "fx3_firmware_lab.wb_color_matrix_and_look_auditor.resolve_donor_file",
            return_value=None,
        ):
            r_missing = analyze_wb_color_matrix_and_look()
        self.assertEqual(r_missing.mode, "CLEAN_ROOM_SYNTHETIC_VERIFIED")
        self.assertTrue(r_missing.all_checks_passed)

    def test_20_fault_inject_fx3_physical_wb_switch_and_drop_shockless(self) -> None:
        fx_sw = build_clean_room_wb_color_matrix_fixtures(inject_fx3_physical_wb_switch=True)
        rep_sw = analyze_wb_color_matrix_and_look(clean_room=True, synthetic_overrides=fx_sw)
        self.assertFalse(rep_sw.all_checks_passed)
        self.assertFalse(rep_sw.pillar_a_white_balance.passed)

        fx_sh = build_clean_room_wb_color_matrix_fixtures(drop_fx6_shockless_wb=True)
        rep_sh = analyze_wb_color_matrix_and_look(clean_room=True, synthetic_overrides=fx_sh)
        self.assertFalse(rep_sh.all_checks_passed)
        self.assertFalse(rep_sh.pillar_a_white_balance.passed)

    def test_21_fault_drop_base_look_slog3_and_paint_matrix_rg(self) -> None:
        fx_look = build_clean_room_wb_color_matrix_fixtures(drop_fx6_base_look_slog3=True)
        self.assertFalse(
            analyze_wb_color_matrix_and_look(clean_room=True, synthetic_overrides=fx_look).pillar_b_base_look.passed
        )

        fx_paint = build_clean_room_wb_color_matrix_fixtures(drop_fx6_paint_matrix_rg_bg=True)
        self.assertFalse(
            analyze_wb_color_matrix_and_look(
                clean_room=True, synthetic_overrides=fx_paint
            ).pillar_c_paint_matrix_knee.passed
        )

    def test_22_fault_drop_cp_calib_and_corrupt_uxc_labels(self) -> None:
        fx_cal = build_clean_room_wb_color_matrix_fixtures(drop_cp_calib_markers=True)
        self.assertFalse(
            analyze_wb_color_matrix_and_look(
                clean_room=True, synthetic_overrides=fx_cal
            ).pillar_d_factory_calibration.passed
        )

        fx_uxc = build_clean_room_wb_color_matrix_fixtures(corrupt_uxc_labels=True)
        rep_uxc = analyze_wb_color_matrix_and_look(clean_room=True, synthetic_overrides=fx_uxc)
        self.assertFalse(rep_uxc.all_checks_passed)
        self.assertTrue(any("0x00004484" in e for e in rep_uxc.errors))

    def test_23_run_audit_all_contains_12_unified_auditors(self) -> None:
        payload = run_audit_all(clean_room=True)
        self.assertTrue(payload["all_checks_passed"])
        expected_auditors = {
            "ufu_container_audit",
            "haita_bk4_feature_audit",
            "uxc_ldec_asset_audit",
            "uxc_multilang_and_font_audit",
            "sensor_codec_compatibility_audit",
            "cube_lut_and_rtmd_audit",
            "wbi_hibdrv_and_elf_abi_audit",
            "global_xdb_and_menu_tree_audit",
            "audio_tc_hdmi_sdi_routing_audit",
            "emount_af_breathing_and_ibis_audit",
            "shutter_ecs_sq_and_tally_audit",
            "wb_color_matrix_and_look_audit",
        }
        self.assertEqual(len(expected_auditors), 12)
        self.assertTrue(expected_auditors.issubset(set(payload.keys())))
        block = payload["wb_color_matrix_and_look_audit"]
        assert isinstance(block, dict)
        self.assertTrue(block["all_checks_passed"])
        self.assertEqual(block["mode"], "CLEAN_ROOM_SYNTHETIC_VERIFIED")

    def test_24_cli_audit_wb_color_look_in_process_and_subprocess_clean_room(self) -> None:
        buf = StringIO()
        with redirect_stdout(buf):
            rc = cli_main(["audit-wb-color-look", "--clean-room", "--json"])
        self.assertEqual(rc, 0)
        parsed = json.loads(buf.getvalue())
        self.assertTrue(parsed["all_checks_passed"])
        self.assertEqual(parsed["schema_version"], PHASE_65_SCHEMA)

        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONPATH"] = str(PKG_ROOT)
        proc = subprocess.run(
            [sys.executable, "-B", "-m", "fx3_firmware_lab", "audit-wb-color-look", "--clean-room"],
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        sub_data = json.loads(proc.stdout)
        self.assertTrue(sub_data["all_checks_passed"])
        self.assertEqual(len(sub_data["report_sha256"]), 64)

    def test_25_kelvin_rb_gain_monotonicity_across_2000k_to_15000k(self) -> None:
        ratios = [
            evaluate_white_balance_kelvin_mired(kelvin=k).rb_gain_ratio
            for k in (2000, 3200, 4300, 5600, 7500, 10000, 15000)
        ]
        self.assertEqual(ratios, sorted(ratios))
        self.assertAlmostEqual(
            evaluate_white_balance_kelvin_mired(kelvin=5600).rb_gain_ratio,
            1.0,
            places=6,
        )

    def test_26_shockless_wb_time_convergence_reaches_target_kelvin(self) -> None:
        res_0 = evaluate_shockless_wb_slew(start_kelvin=3200, target_kelvin=5600, shockless_level="2", dt_sec=0.0)
        res_long = evaluate_shockless_wb_slew(start_kelvin=3200, target_kelvin=5600, shockless_level="2", dt_sec=30.0)
        self.assertEqual(res_0.intermediate_kelvin, 3200)
        self.assertEqual(res_long.intermediate_kelvin, 5600)

    def test_27_paint_matrix_phase_and_level_scaling_preserves_determinant_positive(self) -> None:
        mat_neg = build_and_verify_paint_color_matrix(rg=-99.0, gb=-99.0, br=-99.0, level=-50.0)
        mat_pos = build_and_verify_paint_color_matrix(rg=99.0, gb=99.0, br=99.0, level=99.0)
        self.assertTrue(mat_neg.valid)
        self.assertTrue(mat_pos.valid)
        self.assertGreater(mat_neg.determinant, 0.05)
        self.assertGreater(mat_pos.determinant, 0.05)

    def test_28_module_uses_strict_o_rdonly_and_contains_zero_secrets_or_subprocesses(self) -> None:
        src = (PKG_ROOT / "fx3_firmware_lab" / "wb_color_matrix_and_look_auditor.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("os.O_RDONLY", src)
        self.assertNotIn("os.O_RDWR", src)
        self.assertNotIn("os.O_WRONLY", src)
        self.assertNotIn("subprocess", src)
        self.assertNotIn("socket", src)
        self.assertNotIn("CXD90057_k8", src)
        self.assertNotIn("PRIVATE KEY", src)

    def test_29_verify_raw_3x3_color_matrix_rejects_nan_and_wrong_shape(self) -> None:
        bad_nan = verify_raw_3x3_color_matrix(
            [[1.0, 0.0, 0.0], [0.0, float("nan"), 0.0], [0.0, 0.0, 1.0]]
        )
        self.assertFalse(bad_nan.valid)
        with self.assertRaises(ValueError):
            verify_raw_3x3_color_matrix([[1.0, 0.0], [0.0, 1.0]])

    def test_30_shockless_wb_reverse_cooling_to_warming_monotonic(self) -> None:
        cool_to_warm = evaluate_shockless_wb_slew(
            start_kelvin=6500, target_kelvin=3200, shockless_level="1", dt_sec=0.5
        )
        self.assertTrue(cool_to_warm.valid)
        self.assertTrue(cool_to_warm.monotonic_transition)
        self.assertGreater(cool_to_warm.intermediate_kelvin, 3200)
        self.assertLess(cool_to_warm.intermediate_kelvin, 6500)


if __name__ == "__main__":
    unittest.main()
