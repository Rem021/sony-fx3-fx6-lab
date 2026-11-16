"""Phase 98 unit tests: User 3D LUT (.cube 17^3/33^3/65^3) Domain/NaN Sanitizer,
Tetrahedral vs Trilinear CXD90058 Quantization, S-Log3 Legal/Extended HDMI AVI
InfoFrame Guard, & HDMI-to-12G-SDI Active Converter REC-Trigger Parity.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import re
import subprocess
import sys
import time
import unittest
from pathlib import Path

import fx3_firmware_lab as lab
from fx3_firmware_lab.__main__ import main as cli_main, run_audit_all
from fx3_firmware_lab.lut3d_cube_tetrahedral_and_sdi_hdmi_auditor import (
    AVI_Q_RGB_RANGE_CODES,
    AVI_YQ_YCC_RANGE_CODES,
    AVI_Y_COLORSPACE_CODES,
    CEA861_AVI_TOTAL_BYTES,
    CXD90058_DMA_TABLE_BYTES,
    CXD90058_HW_LUT_GRID_SIZE,
    CXD90058_HW_LUT_VOXELS,
    CXD90058_MAX_USER_LUT_SLOTS,
    FX3_APPFW_LUT_HDMI_MARKERS,
    FX6_APPFW_LUT_SDI_MARKERS,
    FX6_AVBB_PANELEVF_LUT_SDI_MARKERS,
    LIBMPR_CUBE_LUT_MARKERS,
    PHASE_98_SCHEMA,
    PHASE_98_VERSION,
    SLOG3_BLACK_0PCT_CODE10,
    SLOG3_EXTENDED_CLIP_CODE10_RANGE,
    SLOG3_GREY_18PCT_CODE10,
    SLOG3_WHITE_90PCT_CODE10,
    SMPTE_RP188_ATC_DID,
    SMPTE_RP188_ATC_SDID,
    SUPPORTED_CUBE_3D_SIZES,
    TETRAHEDRAL_SLOG3_709_800_MAX_DELTA,
    CubeLut3dSanitizationError,
    analyze_lut3d_cube_tetrahedral_and_sdi_hdmi,
    build_cea861_avi_infoframe,
    build_clean_room_lut3d_sdi_hdmi_fixtures,
    build_slog3_rec709_800_cube_text,
    decode_cea861_avi_infoframe,
    evaluate_hdmi_avi_infoframe_quantization,
    evaluate_hdmi_sdi_rec_trigger_bridge,
    evaluate_lut_calibration_immutability,
    evaluate_mlut_routing_matrix,
    lut3d_cube_tetrahedral_and_sdi_hdmi_report_to_dict,
    pack_33_to_cxd90058_dma_bytes,
    parse_and_sanitize_cube_lut_3d,
    resample_cube_tetrahedral_to_33,
    sanitize_resample_and_stage_cube_lut,
    slog3_reflection_to_code10_rounded,
    tetrahedral_sample_cube,
    trilinear_sample_cube_3d,
    verify_tetrahedral_vs_trilinear_convergence,
)

LAB_ROOT = Path(__file__).resolve().parents[1]
AUDITOR_PATH = LAB_ROOT / "fx3_firmware_lab" / "lut3d_cube_tetrahedral_and_sdi_hdmi_auditor.py"
_BYTES_REPR_RE = re.compile(r"(?<![0-9A-Za-z_/.-])b['\"]")


class TestLut3dCubeTetrahedralAndSdiHdmi(unittest.TestCase):
    # ------------------------------------------------------------------
    # Dual-Mode Auditor, Donor Verification, Determinism & JSON Hygiene
    # ------------------------------------------------------------------

    def test_01_clean_room_runtime_and_all_pillars_pass(self) -> None:
        # Warm cache once and verify steady-state clean-room budget (<0.02s) + cold (<0.08s)
        t_cold0 = time.perf_counter()
        rep_cold = analyze_lut3d_cube_tetrahedral_and_sdi_hdmi(clean_room=True)
        cold_dt = time.perf_counter() - t_cold0

        t_warm0 = time.perf_counter()
        rep = analyze_lut3d_cube_tetrahedral_and_sdi_hdmi(clean_room=True)
        warm_dt = time.perf_counter() - t_warm0

        self.assertLess(cold_dt, 0.50 if __import__("os").environ.get("GITHUB_ACTIONS") == "true" else 0.08)
        self.assertLess(warm_dt, 0.25 if __import__("os").environ.get("GITHUB_ACTIONS") == "true" else 0.02)
        self.assertEqual(rep.mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(rep.schema_version, PHASE_98_SCHEMA)
        self.assertEqual(rep.phase_version, PHASE_98_VERSION)
        self.assertTrue(rep_cold.all_checks_passed)
        self.assertTrue(rep.all_checks_passed)
        self.assertTrue(rep.pillar_1_cube_lut_tetrahedral.passed)
        self.assertTrue(rep.pillar_2_slog3_avi_quantization.passed)
        self.assertTrue(rep.pillar_3_hdmi_sdi_rec_bridge.passed)
        self.assertTrue(rep.pillar_4_mlut_routing_immutability.passed)
        self.assertEqual(rep.pillar_4_mlut_routing_immutability.calibration_mutation_bytes, 0)
        self.assertEqual(rep.pillar_4_mlut_routing_immutability.emmc_mutation_bytes, 0)
        self.assertFalse(rep.pillar_4_mlut_routing_immutability.persistent_emmc_writes_authorized)
        self.assertEqual(rep.errors, ())

    def test_02_active_mode_runtime_and_donor_artifacts(self) -> None:
        t0 = time.perf_counter()
        rep = analyze_lut3d_cube_tetrahedral_and_sdi_hdmi(clean_room=False)
        elapsed = time.perf_counter() - t0
        self.assertLess(elapsed, 0.35)
        self.assertTrue(rep.all_checks_passed)
        self.assertEqual(len(rep.donor_file_sizes), 13)
        for name, sz in rep.donor_file_sizes.items():
            self.assertGreater(sz, 0, f"{name} size should be > 0")
        if os.environ.get("FX3_FX6_FORCE_CLEAN_ROOM") == "1":
            self.assertEqual(rep.mode, "CLEAN_ROOM_SYNTHETIC")
        else:
            self.assertIn(rep.mode, ("LOCAL_DONOR_VERIFIED", "CLEAN_ROOM_SYNTHETIC"))

    def test_03_report_sha256_deterministic_and_json_clean(self) -> None:
        r1 = analyze_lut3d_cube_tetrahedral_and_sdi_hdmi(clean_room=True)
        r2 = analyze_lut3d_cube_tetrahedral_and_sdi_hdmi(clean_room=True)
        self.assertEqual(r1.report_sha256, r2.report_sha256)
        self.assertEqual(len(r1.report_sha256), 64)
        payload = lut3d_cube_tetrahedral_and_sdi_hdmi_report_to_dict(r1)
        encoded = json.dumps(payload, sort_keys=True)
        parsed = json.loads(encoded)
        self.assertEqual(parsed["schema_version"], PHASE_98_SCHEMA)
        self.assertNotRegex(encoded, _BYTES_REPR_RE)

    def test_04_package_exports_and_schema_constants(self) -> None:
        for sym in (
            "PHASE_98_SCHEMA",
            "PHASE_98_VERSION",
            "CXD90058_DMA_TABLE_BYTES",
            "analyze_lut3d_cube_tetrahedral_and_sdi_hdmi",
            "lut3d_cube_tetrahedral_and_sdi_hdmi_report_to_dict",
            "tetrahedral_sample_cube",
            "resample_cube_tetrahedral_to_33",
            "pack_33_to_cxd90058_dma_bytes",
            "evaluate_hdmi_avi_infoframe_quantization",
            "evaluate_hdmi_sdi_rec_trigger_bridge",
            "evaluate_mlut_routing_matrix",
            "evaluate_lut_calibration_immutability",
        ):
            self.assertTrue(hasattr(lab, sym), f"Missing package export: {sym}")
            self.assertIn(sym, lab.__all__)
        self.assertEqual(CXD90058_HW_LUT_GRID_SIZE, 33)
        self.assertEqual(CXD90058_HW_LUT_VOXELS, 35937)
        self.assertEqual(CXD90058_DMA_TABLE_BYTES, 215622)
        self.assertEqual(SUPPORTED_CUBE_3D_SIZES, (17, 33, 65))

    def test_05_clean_room_fixtures_contain_all_markers(self) -> None:
        fx = build_clean_room_lut3d_sdi_hdmi_fixtures()
        self.assertEqual(len(fx), 13)
        for m in FX3_APPFW_LUT_HDMI_MARKERS:
            self.assertIn(m.encode("utf-8"), fx["fx3_appfw"])
        for m in FX6_APPFW_LUT_SDI_MARKERS:
            self.assertIn(m.encode("utf-8"), fx["fx6_appfw"])
        for m in LIBMPR_CUBE_LUT_MARKERS:
            self.assertIn(m.encode("utf-8"), fx["fx3_libmpr"])
            self.assertIn(m.encode("utf-8"), fx["fx6_libmpr"])
        for m in FX6_AVBB_PANELEVF_LUT_SDI_MARKERS:
            self.assertIn(m.encode("utf-8"), fx["fx6_avbb_panelevf"])

    def test_06_uxc_phase98_labels_present(self) -> None:
        rep = analyze_lut3d_cube_tetrahedral_and_sdi_hdmi(clean_room=True)
        labels = rep.pillar_1_cube_lut_tetrahedral.uxc_lut_labels
        self.assertTrue(labels["fx3_import_user_lut"])
        self.assertTrue(labels["fx3_delete_user_lut"])
        self.assertTrue(labels["fx6_mlut"])
        self.assertTrue(labels["fx6_load_user_3d_lut"])
        rec_labels = rep.pillar_3_hdmi_sdi_rec_bridge.uxc_sdi_hdmi_rec_labels
        self.assertIn("HDMI Resolution", rec_labels["fx3_hdmi_resolution"])
        self.assertIn("SDI/HDMI Rec Control", rec_labels["fx6_sdi_hdmi_rec_control"])

    def test_07_static_os_o_rdonly_and_zero_emmc_write_hygiene(self) -> None:
        src = AUDITOR_PATH.read_text(encoding="utf-8")
        self.assertIn("os.O_RDONLY", src)
        self.assertIn("mmap.ACCESS_READ", src)
        self.assertNotIn("os.O_WRONLY", src)
        self.assertNotIn("os.O_RDWR", src)
        self.assertNotIn("os.O_CREAT", src)

    def test_08_active_mode_zero_errors(self) -> None:
        rep = analyze_lut3d_cube_tetrahedral_and_sdi_hdmi(clean_room=False)
        self.assertEqual(rep.errors, ())
        self.assertEqual(rep.pillar_1_cube_lut_tetrahedral.errors, ())
        self.assertEqual(rep.pillar_2_slog3_avi_quantization.errors, ())
        self.assertEqual(rep.pillar_3_hdmi_sdi_rec_bridge.errors, ())
        self.assertEqual(rep.pillar_4_mlut_routing_immutability.errors, ())

    # ------------------------------------------------------------------
    # Pillar 1: .cube 17^3/33^3/65^3 Parser, Sanitizer & Tetrahedral DMA
    # ------------------------------------------------------------------

    def test_09_parse_valid_17_33_and_65_cube_luts(self) -> None:
        for sz in (17, 33, 65):
            txt = build_slog3_rec709_800_cube_text(grid_size=sz, title=f"LUT_{sz}")
            parsed = parse_and_sanitize_cube_lut_3d(txt)
            self.assertEqual(parsed.grid_size, sz)
            self.assertEqual(len(parsed.entries), sz ** 3)
            self.assertEqual(parsed.title, f"LUT_{sz}")
            self.assertEqual(parsed.negative_entries_detected, 0)
            self.assertEqual(len(parsed.sha256), 64)

    def test_10_parse_nonstandard_domain_min_max_and_input_range(self) -> None:
        base = build_slog3_rec709_800_cube_text(
            grid_size=17,
            title="LEGAL_DOM",
            domain_min=(0.0625, 0.0625, 0.0625),
            domain_max=(0.9188, 0.9188, 0.9188),
        )
        p1 = parse_and_sanitize_cube_lut_3d(base)
        self.assertEqual(p1.domain_min, (0.0625, 0.0625, 0.0625))
        self.assertEqual(p1.domain_max, (0.9188, 0.9188, 0.9188))

        iridas_range = base.replace(
            "DOMAIN_MIN 0.062500 0.062500 0.062500\nDOMAIN_MAX 0.918800 0.918800 0.918800",
            "LUT_3D_INPUT_RANGE 0.0928 0.9500",
            1,
        )
        p2 = parse_and_sanitize_cube_lut_3d(iridas_range)
        self.assertAlmostEqual(p2.domain_min[0], 0.0928)
        self.assertAlmostEqual(p2.domain_max[2], 0.95)

    def test_11_reject_nan_pos_inf_and_neg_inf_fail_closed(self) -> None:
        base = build_slog3_rec709_800_cube_text(grid_size=17)
        for bad_tok in ("NaN", "nan", "inf", "-inf", "Infinity"):
            bad = base.replace("0.062500 0.062500 0.062500", f"{bad_tok} 0.062500 0.062500", 1)
            with self.assertRaises(CubeLut3dSanitizationError):
                parse_and_sanitize_cube_lut_3d(bad)

    def test_12_reject_inverted_and_degenerate_domain_bounds(self) -> None:
        base = build_slog3_rec709_800_cube_text(grid_size=17)
        inv = base.replace("DOMAIN_MIN 0.000000 0.000000 0.000000", "DOMAIN_MIN 1.000000 0.000000 0.000000", 1)
        deg = base.replace("DOMAIN_MAX 1.000000 1.000000 1.000000", "DOMAIN_MAX 0.000000 1.000000 1.000000", 1)
        for payload in (inv, deg):
            res = sanitize_resample_and_stage_cube_lut(payload)
            self.assertFalse(res.valid)
            self.assertEqual(res.status, "BLOCKED_CUBE_LUT_SANITIZATION_FAILED")

    def test_13_reject_lut_1d_size_and_mismatched_voxel_counts(self) -> None:
        base = build_slog3_rec709_800_cube_text(grid_size=17)
        with self.assertRaises(CubeLut3dSanitizationError):
            parse_and_sanitize_cube_lut_3d("LUT_1D_SIZE 1024\n0.0 0.0 0.0\n")
        truncated = "\n".join(base.splitlines()[:-5]) + "\n"
        with self.assertRaises(CubeLut3dSanitizationError):
            parse_and_sanitize_cube_lut_3d(truncated)
        extra = base + "0.500000 0.500000 0.500000\n"
        with self.assertRaises(CubeLut3dSanitizationError):
            parse_and_sanitize_cube_lut_3d(extra)

    def test_14_reject_or_clamp_negative_and_oob_entries(self) -> None:
        base = build_slog3_rec709_800_cube_text(grid_size=17)
        neg = base.replace("0.062500 0.062500 0.062500", "-0.025000 1.045000 0.062500", 1)
        with self.assertRaises(CubeLut3dSanitizationError):
            parse_and_sanitize_cube_lut_3d(neg, on_negative_or_oob="REJECT")
        clamped = parse_and_sanitize_cube_lut_3d(neg, on_negative_or_oob="CLAMP")
        self.assertEqual(clamped.negative_entries_detected, 1)
        self.assertEqual(clamped.over_one_entries_detected, 1)
        self.assertEqual(clamped.clamped_entries_count, 1)
        self.assertEqual(clamped.entries[0], (0.0, 1.0, 0.0625))

    def test_15_reject_control_chars_nul_and_path_traversal_title(self) -> None:
        base = build_slog3_rec709_800_cube_text(grid_size=17)
        for bad in (
            base.replace('TITLE "SL3_SG3C_TO_709_800"', 'TITLE "../../etc/passwd"', 1),
            base.replace('TITLE "SL3_SG3C_TO_709_800"', f'TITLE "{"A" * 64}"', 1),
            base + "\x07",
            base.encode("utf-8") + b"\x00",
        ):
            with self.assertRaises(CubeLut3dSanitizationError):
                parse_and_sanitize_cube_lut_3d(bad)

    def test_16_tetrahedral_exact_on_affine_3x3_matrix(self) -> None:
        def _aff(r: float, g: float, b: float) -> tuple[float, float, float]:
            return (
                0.78 * r + 0.14 * g + 0.08 * b,
                0.05 * r + 0.88 * g + 0.07 * b,
                0.03 * r + 0.09 * g + 0.88 * b,
            )

        cube2 = [_aff(float(r), float(g), float(b)) for b in (0, 1) for g in (0, 1) for r in (0, 1)]
        for r, g, b in ((0.13, 0.41, 0.79), (0.72, 0.19, 0.54), (0.31, 0.67, 0.11)):
            got_tet = tetrahedral_sample_cube(cube2, 2, r, g, b)
            got_tri = trilinear_sample_cube_3d(cube2, 2, r, g, b)
            exp = _aff(r, g, b)
            for k in range(3):
                self.assertAlmostEqual(got_tet[k], exp[k], places=12)
                self.assertAlmostEqual(got_tri[k], exp[k], places=12)

    def test_17_tetrahedral_vs_trilinear_full_convergence_17_33_65_under_1e4(self) -> None:
        conv = verify_tetrahedral_vs_trilinear_convergence(include_full_65_table=True)
        self.assertTrue(conv.passed)
        self.assertEqual(conv.status, "TETRAHEDRAL_MONOTONIC_CONVERGENCE_PROVEN")
        self.assertTrue(conv.monotonic_convergence)
        self.assertTrue(conv.tetrahedral_beats_or_ties_trilinear)
        self.assertTrue(conv.err_65_within_1e4)
        self.assertLess(conv.err_65_tetrahedral, TETRAHEDRAL_SLOG3_709_800_MAX_DELTA)
        self.assertGreater(conv.err_17_tetrahedral, conv.err_33_tetrahedral)
        self.assertGreater(conv.err_33_tetrahedral, conv.err_65_tetrahedral)
        self.assertLess(conv.affine_matrix_max_delta, 1e-12)
        self.assertLess(conv.downsample_65_to_33_node_max_delta, 1e-12)

    def test_18_resample_65_and_17_to_33_cxd90058_u12_4_and_u16_dma(self) -> None:
        txt65 = build_slog3_rec709_800_cube_text(grid_size=65, title="RESOLVE_65")
        ev65 = sanitize_resample_and_stage_cube_lut(
            txt65,
            dma_format="U12_4",
            user_slot_index=4,
            staging_path="/tmp/fx3_resolve65_slot4.bin",
            full_dma_pack=True,
        )
        self.assertTrue(ev65.valid)
        self.assertEqual(ev65.source_grid_size, 65)
        self.assertEqual(ev65.target_grid_size, 33)
        self.assertEqual(ev65.source_voxels, 274625)
        self.assertEqual(ev65.target_voxels, CXD90058_HW_LUT_VOXELS)
        self.assertEqual(ev65.dma_table_bytes, CXD90058_DMA_TABLE_BYTES)
        self.assertLess(ev65.max_quantization_error, 2e-5)

        txt17 = build_slog3_rec709_800_cube_text(
            grid_size=17,
            title="LEGAL_17",
            domain_min=(0.0625, 0.0625, 0.0625),
            domain_max=(0.9188, 0.9188, 0.9188),
        )
        p17 = parse_and_sanitize_cube_lut_3d(txt17)
        e33 = resample_cube_tetrahedral_to_33(p17)
        dma_u16, qerr_u16 = pack_33_to_cxd90058_dma_bytes(e33, dma_format="U16")
        self.assertEqual(len(e33), 35937)
        self.assertEqual(len(dma_u16), 215622)
        self.assertLess(qerr_u16, 1e-5)

    def test_19_user_lut_slot_bounds_and_volatile_ram_guard(self) -> None:
        txt17 = build_slog3_rec709_800_cube_text(grid_size=17)
        bad_slot = sanitize_resample_and_stage_cube_lut(txt17, user_slot_index=CXD90058_MAX_USER_LUT_SLOTS + 1, full_dma_pack=False)
        self.assertFalse(bad_slot.valid)
        bad_emmc = sanitize_resample_and_stage_cube_lut(txt17, staging_path="/dev/nflasha30", full_dma_pack=False)
        self.assertFalse(bad_emmc.valid)
        self.assertFalse(bad_emmc.volatile_ram_staged)
        self.assertFalse(bad_emmc.factory_calibration_mutated)

    # ------------------------------------------------------------------
    # Pillar 2: S-Log3 Code Landmarks & CEA-861 HDMI AVI InfoFrame Guard
    # ------------------------------------------------------------------

    def test_20_slog3_10bit_code_landmarks_exact(self) -> None:
        self.assertEqual(slog3_reflection_to_code10_rounded(0.0), SLOG3_BLACK_0PCT_CODE10)
        self.assertEqual(slog3_reflection_to_code10_rounded(0.18), SLOG3_GREY_18PCT_CODE10)
        self.assertEqual(slog3_reflection_to_code10_rounded(0.90), SLOG3_WHITE_90PCT_CODE10)
        self.assertEqual(slog3_reflection_to_code10_rounded(13.0), 900)
        clip_code = slog3_reflection_to_code10_rounded(24.0)
        self.assertGreaterEqual(clip_code, SLOG3_EXTENDED_CLIP_CODE10_RANGE[0])
        self.assertLessEqual(clip_code, SLOG3_EXTENDED_CLIP_CODE10_RANGE[1])
        self.assertEqual(slog3_reflection_to_code10_rounded(37.0), SLOG3_EXTENDED_CLIP_CODE10_RANGE[1])

    def test_21_cea861_avi_infoframe_checksum_and_bitfields(self) -> None:
        for cs, y_code in AVI_Y_COLORSPACE_CODES.items():
            for q_name, q_code in AVI_Q_RGB_RANGE_CODES.items():
                for yq_name, yq_code in AVI_YQ_YCC_RANGE_CODES.items():
                    pkt = build_cea861_avi_infoframe(
                        colorspace=cs, rgb_quantization=q_name, ycc_quantization=yq_name
                    )
                    self.assertEqual(len(pkt), CEA861_AVI_TOTAL_BYTES)
                    self.assertEqual(sum(pkt) & 0xFF, 0)
                    dec = decode_cea861_avi_infoframe(pkt)
                    self.assertTrue(dec["checksum_valid"])
                    self.assertEqual(dec["y_bits"], y_code)
                    self.assertEqual(dec["q_bits"], q_code)
                    self.assertEqual(dec["yq_bits"], yq_code)

    def test_22_slog3_legal_and_extended_ycbcr422_matched(self) -> None:
        for sig in ("SLOG3_LEGAL_64_940", "SLOG3_EXTENDED_64_1019"):
            ev = evaluate_hdmi_avi_infoframe_quantization(
                signal_range_mode=sig,
                colorspace="YCBCR_422",
                ycc_quantization="LIMITED",
                recorder_expectation="LEGAL_OR_EXTENDED",
            )
            self.assertTrue(ev.valid)
            self.assertEqual(ev.status, "VALID_AVI_INFOFRAME_RANGE_MATCHED")
            self.assertTrue(ev.checksum_valid)
            self.assertEqual(ev.ycc_quantization_yq_name, "LIMITED")
            self.assertEqual(ev.shadow_crush_delta_codes, 0)
            self.assertFalse(ev.double_scaling_detected)

    def test_23_rgb_full_0_1023_matched(self) -> None:
        ev = evaluate_hdmi_avi_infoframe_quantization(
            signal_range_mode="FULL_0_1023",
            colorspace="RGB",
            rgb_quantization="FULL",
            recorder_expectation="FULL_RANGE",
        )
        self.assertTrue(ev.valid)
        self.assertEqual(ev.rgb_quantization_q_name, "FULL")
        self.assertEqual(ev.shadow_crush_delta_codes, 0)

    def test_24_block_double_scaling_shadow_crush_and_highlight_clip(self) -> None:
        ev = evaluate_hdmi_avi_infoframe_quantization(
            signal_range_mode="SLOG3_EXTENDED_64_1019",
            colorspace="YCBCR_422",
            ycc_quantization="LIMITED",
            recorder_expectation="FULL_RANGE",
        )
        self.assertFalse(ev.valid)
        self.assertEqual(ev.status, "BLOCKED_DOUBLE_SCALING_SHADOW_CRUSH_HAZARD")
        self.assertTrue(ev.double_scaling_detected)
        self.assertTrue(ev.highlight_clip_hazard)
        self.assertEqual(ev.recorder_black_code10_after_rx, 36)
        self.assertEqual(ev.shadow_crush_delta_codes, -59)

    def test_25_block_avi_yq_q_mismatch_and_raw16_ycbcr_mislabeled(self) -> None:
        b1 = evaluate_hdmi_avi_infoframe_quantization(
            signal_range_mode="SLOG3_EXTENDED_64_1019",
            colorspace="YCBCR_422",
            ycc_quantization="FULL",
            recorder_expectation="LEGAL_OR_EXTENDED",
        )
        self.assertFalse(b1.valid)
        self.assertTrue(b1.double_scaling_detected)
        b2 = evaluate_hdmi_avi_infoframe_quantization(
            signal_range_mode="HDMI_RAW16_LINEAR",
            colorspace="YCBCR_422",
            ycc_quantization="LIMITED",
            recorder_expectation="LEGAL_OR_EXTENDED",
        )
        self.assertFalse(b2.valid)
        self.assertEqual(b2.status, "BLOCKED_AVI_INFOFRAME_GUARD")

    def test_26_reject_nonfinite_slog3_or_invalid_avi_params(self) -> None:
        with self.assertRaises(ValueError):
            slog3_reflection_to_code10_rounded(float("nan"))
        bad = evaluate_hdmi_avi_infoframe_quantization(signal_range_mode="UNKNOWN_MODE")
        self.assertFalse(bad.valid)
        self.assertEqual(bad.status, "BLOCKED_INVALID_AVI_PARAMETER")

    # ------------------------------------------------------------------
    # Pillar 3: FX6 Native 12G-SDI vs FX3 HDMI->12G-SDI REC Bridge
    # ------------------------------------------------------------------

    def test_27_fx6_native_12g_sdi_rp188_atc_parallel_rec(self) -> None:
        ev = evaluate_hdmi_sdi_rec_trigger_bridge(
            camera_body="FX6",
            converter_bridge="FX6_NATIVE_12G_SDI_BNC",
            fx6_ui_rec_control_mode="PARALLEL_REC",
            hours=12,
            minutes=34,
            seconds=56,
            frames=23,
        )
        self.assertTrue(ev.valid)
        self.assertEqual(ev.status, "VALID_FX6_NATIVE_12G_SDI_RP188")
        self.assertTrue(ev.physical_12g_sdi_bnc_present)
        self.assertEqual(ev.sdi_rp188_atc_did, SMPTE_RP188_ATC_DID)
        self.assertEqual(ev.sdi_rp188_atc_sdid, SMPTE_RP188_ATC_SDID)
        self.assertEqual(ev.sdi_remote_rec_bit, 1)
        self.assertEqual(ev.timecode_bcd_str, "12:34:56:23")
        self.assertTrue(ev.tc_roundtrip_exact)

    def test_28_fx3_active_bridges_bmd_teradek_atomos_parity(self) -> None:
        for bridge, df in (
            ("BMD_MICRO_CONVERTER_HDMI_TO_SDI_12G", False),
            ("TERADEK_BOLT_HDMI_SDI_BRIDGE", True),
            ("ATOMOS_CONNECT_HDMI_SDI_BRIDGE", False),
        ):
            ev = evaluate_hdmi_sdi_rec_trigger_bridge(
                camera_body="FX3",
                converter_bridge=bridge,
                fx6_ui_rec_control_mode="SDI_HDMI_REMOTE_I_F",
                drop_frame=df,
            )
            self.assertTrue(ev.valid)
            self.assertEqual(ev.status, "VALID_FX3_HDMI_TO_12G_SDI_BRIDGE_PARITY")
            self.assertFalse(ev.physical_12g_sdi_bnc_present)
            self.assertEqual(ev.hdmi_rec_trigger_bit, 1)
            self.assertEqual(ev.sdi_remote_rec_bit, 1)
            self.assertTrue(ev.tc_roundtrip_exact)
            self.assertEqual(ev.ghost_sdi_bnc_hw_faults, 0)
            self.assertIn(";" if df else ":", ev.timecode_bcd_str)

    def test_29_block_fx3_native_sdi_bnc_and_passive_hdmi_cable(self) -> None:
        b1 = evaluate_hdmi_sdi_rec_trigger_bridge(
            camera_body="FX3",
            converter_bridge="FX6_NATIVE_12G_SDI_BNC",
        )
        self.assertFalse(b1.valid)
        self.assertEqual(b1.sdi_remote_rec_bit, 0)
        b2 = evaluate_hdmi_sdi_rec_trigger_bridge(
            camera_body="FX3",
            converter_bridge="PASSIVE_HDMI_CABLE_NO_BRIDGE",
        )
        self.assertFalse(b2.valid)
        self.assertEqual(b2.status, "BLOCKED_HDMI_SDI_REC_BRIDGE_FAULT")

    def test_30_block_hdmi_tc_off_and_raw16_parallel_rec_exclusion(self) -> None:
        b1 = evaluate_hdmi_sdi_rec_trigger_bridge(
            camera_body="FX3",
            converter_bridge="BMD_MICRO_CONVERTER_HDMI_TO_SDI_12G",
            hdmi_tc_output_enabled=False,
        )
        self.assertFalse(b1.valid)
        self.assertEqual(b1.hdmi_rec_trigger_bit, 0)
        self.assertEqual(b1.sdi_remote_rec_bit, 0)

        b2 = evaluate_hdmi_sdi_rec_trigger_bridge(
            camera_body="FX3",
            converter_bridge="ATOMOS_CONNECT_HDMI_SDI_BRIDGE",
            fx6_ui_rec_control_mode="PARALLEL_REC",
            rec_media_during_hdmi_output=True,
            hdmi_raw16_active=True,
        )
        self.assertFalse(b2.valid)

    def test_31_invalid_camera_body_or_tc_rejected(self) -> None:
        bad = evaluate_hdmi_sdi_rec_trigger_bridge(camera_body="FX9", hours=29)
        self.assertFalse(bad.valid)
        self.assertEqual(bad.sdi_remote_rec_bit, 0)

    # ------------------------------------------------------------------
    # Pillar 4 & CLI Integration
    # ------------------------------------------------------------------

    def test_32_mlut_routing_matrix_valid_profiles(self) -> None:
        p_clean = evaluate_mlut_routing_matrix(
            profile_name="SLOG3_CLEAN_HDMI_LOG_INTERNAL",
            camera_body="FX3",
            main_rec_lut_baked=False,
            proxy_rec_lut_baked=False,
            embed_lut_file_sidecar=True,
            lcd_vf_mlut_on=True,
            hdmi_mlut_on=False,
            hdmi_clean_feed_no_osd=True,
        )
        p_proxy = evaluate_mlut_routing_matrix(
            profile_name="SLOG3_PROXY_EMBED_LUT_ONLY",
            camera_body="FX3",
            main_rec_lut_baked=False,
            proxy_rec_lut_baked=True,
            embed_lut_file_sidecar=True,
        )
        p_burn = evaluate_mlut_routing_matrix(
            profile_name="FX6_BURN_IN_INTERNAL_LOOK",
            camera_body="FX6",
            main_rec_lut_baked=True,
            proxy_rec_lut_baked=True,
            embed_lut_file_sidecar=False,
            hdmi_mlut_on=True,
        )
        for ev in (p_clean, p_proxy, p_burn):
            self.assertTrue(ev.valid)
            self.assertEqual(ev.ghost_sdi_bnc_hw_faults, 0)

    def test_33_fx3_sdi1_mlut_safely_gated_without_ghost_faults(self) -> None:
        ev = evaluate_mlut_routing_matrix(
            profile_name="SLOG3_CLEAN_HDMI_LOG_INTERNAL",
            camera_body="FX3",
            sdi1_mlut_requested=True,
        )
        self.assertTrue(ev.valid)
        self.assertEqual(ev.status, "VALID_FX3_SDI1_MLUT_SAFELY_GATED")
        self.assertFalse(ev.sdi1_output_supported)
        self.assertEqual(ev.ghost_sdi_bnc_hw_faults, 0)

    def test_34_block_raw16_hdmi_mlut_bake_and_proxy_baked_main(self) -> None:
        b_raw = evaluate_mlut_routing_matrix(
            profile_name="HDMI_RAW16_CLEAN_NO_MLUT",
            camera_body="FX3",
            hdmi_raw16_active=True,
            hdmi_mlut_on=True,
        )
        self.assertFalse(b_raw.valid)
        self.assertEqual(b_raw.status, "BLOCKED_MLUT_ROUTING_CONFLICT")

        b_proxy = evaluate_mlut_routing_matrix(
            profile_name="SLOG3_PROXY_EMBED_LUT_ONLY",
            camera_body="FX3",
            main_rec_lut_baked=True,
        )
        self.assertFalse(b_proxy.valid)

    def test_35_calibration_and_emmc_zero_mutation_firewall(self) -> None:
        for ok in ("/tmp/lut_slot1.bin", "ram://fx3_lut_u12_4", "memory://lut_stage"):
            ev = evaluate_lut_calibration_immutability(ok)
            self.assertTrue(ev.valid)
            self.assertTrue(ev.volatile_ram_only)
            self.assertEqual(ev.calibration_mutation_bytes, 0)
            self.assertEqual(ev.emmc_mutation_bytes, 0)
            self.assertFalse(ev.persistent_emmc_writes_authorized)

        for bad in (
            "/dev/cnflasha0",
            "/dev/nflasha30",
            "/dev/mmcblk0p1",
            "p2:/Backup.bin",
            "p2:/psd.bin",
            "p6:Jiritsu",
            "nvram://lut_slot1",
        ):
            blk = evaluate_lut_calibration_immutability(bad)
            self.assertFalse(blk.valid)
            self.assertEqual(blk.status, "BLOCKED_PERSISTENT_CALIBRATION_OR_EMMC_WRITE")
            self.assertFalse(blk.volatile_ram_only)
            self.assertFalse(blk.persistent_emmc_writes_authorized)

    def test_36_cli_audit_lut3d_sdi_hdmi_in_process(self) -> None:
        buf_cr = io.StringIO()
        with contextlib.redirect_stdout(buf_cr):
            rc_cr = cli_main(["audit-lut3d-sdi-hdmi", "--clean-room", "--json"])
        self.assertEqual(rc_cr, 0)
        p_cr = json.loads(buf_cr.getvalue())
        self.assertTrue(p_cr["all_checks_passed"])
        self.assertEqual(p_cr["mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertNotRegex(buf_cr.getvalue(), _BYTES_REPR_RE)

        buf_act = io.StringIO()
        with contextlib.redirect_stdout(buf_act):
            rc_act = cli_main(["audit-lut3d-sdi-hdmi", "--json"])
        self.assertEqual(rc_act, 0)
        p_act = json.loads(buf_act.getvalue())
        self.assertTrue(p_act["all_checks_passed"])

    def test_37_run_audit_all_includes_19_auditors_with_lut3d_sdi_hdmi(self) -> None:
        summary = run_audit_all(clean_room=True)
        self.assertTrue(summary["all_checks_passed"])
        expected_19 = (
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
            "proxy_clipname_and_sidecar_audit",
            "assignable_zoom_ciz_and_fn_audit",
            "falsecolor_lpcm_tc_ub_audit",
            "playback_shotmark_and_ae_audit",
            "metadata_gyro_catalyst_and_anamorphic_audit",
            "interval_cache_and_ftp_audit",
            "lut3d_cube_tetrahedral_and_sdi_hdmi_audit",
        )
        self.assertEqual(len(expected_19), 19)
        for key in expected_19:
            self.assertIn(key, summary)
            self.assertTrue(summary[key]["all_checks_passed"], f"Failed auditor: {key}")

    def test_38_cli_subprocess_clean_room_and_local_mode(self) -> None:
        env_cr = os.environ.copy()
        env_cr["PYTHONPATH"] = str(LAB_ROOT)
        env_cr["PYTHONDONTWRITEBYTECODE"] = "1"
        env_cr["FX3_FX6_FORCE_CLEAN_ROOM"] = "1"
        proc_cr = subprocess.run(
            [sys.executable, "-B", "-m", "fx3_firmware_lab", "audit-lut3d-sdi-hdmi", "--json"],
            env=env_cr,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc_cr.returncode, 0, proc_cr.stderr)
        data_cr = json.loads(proc_cr.stdout)
        self.assertTrue(data_cr["all_checks_passed"])
        self.assertEqual(data_cr["mode"], "CLEAN_ROOM_SYNTHETIC")

        env_loc = os.environ.copy()
        env_loc["PYTHONPATH"] = str(LAB_ROOT)
        env_loc["PYTHONDONTWRITEBYTECODE"] = "1"
        env_loc.pop("FX3_FX6_FORCE_CLEAN_ROOM", None)
        proc_loc = subprocess.run(
            [sys.executable, "-B", "-m", "fx3_firmware_lab", "audit-lut3d-sdi-hdmi", "--json"],
            env=env_loc,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc_loc.returncode, 0, proc_loc.stderr)
        data_loc = json.loads(proc_loc.stdout)
        self.assertTrue(data_loc["all_checks_passed"])


if __name__ == "__main__":
    unittest.main()
