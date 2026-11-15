"""Phase 133 Dual-Mode Unit Tests (40 tests): BIONZ XR XAVC HS (HEVC 10-Bit 4:2:2)
vs XAVC S-I / XAVC-I All-Intra Matrix, ACES 1.3 / 2.0 S-Log3 & S-Gamut3(.Cine)
AP0/AP1 IDT Verifier, & NP-FZ100 InfoLITHIUM C-Pin / Stage-B 14.4V Rail Guard.
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
from fx3_firmware_lab.emount_af_breathing_and_ibis_auditor import _extract_uxc_labels
from fx3_firmware_lab.global_xdb_and_menu_tree_auditor import parse_global_xdb_buffer
from fx3_firmware_lab.xavc_hevc_intra_aces_idt_and_fz100_auditor import (
    ACES_MAX_WHITEPOINT_ERROR,
    ACES_MIN_DET_ABS,
    ACES_OCIO_CLF_TRANSFORM_IDS,
    ALL_INTRA_4K_BITRATES_MBPS,
    BP_U_SHUTDOWN_MV,
    CAT_BRADFORD_3X3,
    CAT_CAT02_3X3,
    CP_SHARED_PHASE133_MARKERS,
    FX3_APPFW_PHASE133_MARKERS,
    FX3_LIBMPR_PHASE133_MARKERS,
    FX3_NS39_PHASE133_LABELS,
    FX3_NS3_PHASE133_LABELS,
    FX6_APPFW_PHASE133_MARKERS,
    FX6_LIBMPR_PHASE133_MARKERS,
    FX6_NS1_PHASE133_LABELS,
    FX6_NS2_PHASE133_LABELS,
    MEDIA_SPEED_CLASSES_MBPS,
    NP_FZ100_CAPACITY_MAH,
    NP_FZ100_ENERGY_WH,
    NP_FZ100_FW_UPDATE_MIN_SOC_PCT,
    NP_FZ100_NOMINAL_MV,
    PHASE_133_SCHEMA,
    PHASE_133_VERSION,
    SLOG3_BLACK_CV10,
    SLOG3_BREAK_CV10,
    SLOG3_BREAK_LIN,
    SLOG3_GRAY_18_CV10,
    SLOG3_WHITE_90_CV10,
    XAVC_HS_FORBIDDEN_FPS_FX3,
    analyze_xavc_hevc_intra_aces_idt_and_fz100,
    build_clean_room_xavc_aces_fz100_fixtures,
    compute_aces_idt_matrix_3x3,
    evaluate_bionz_xr_codec_profile,
    evaluate_np_fz100_battery_handshake,
    evaluate_phase133_write_guard,
    evaluate_pillar_a_bionz_xr_codec_matrix,
    evaluate_pillar_b_aces_slog3_idt_matrix,
    evaluate_pillar_c_np_fz100_battery_handshake,
    evaluate_pillar_d_zero_mutation_phase133_guard,
    invert_3x3_matrix,
    matrix_determinant_3x3,
    slog3_linear_to_norm,
    slog3_norm_to_linear,
    verify_aces_idt_matrix,
    verify_slog3_transfer_landmarks,
    xavc_hevc_intra_aces_idt_and_fz100_report_to_dict,
)


_BYTES_REPR_RE = re.compile(r"(?<![0-9A-Za-z_/.-])b['\"]")
_AUDITOR_PATH = (
    Path(__file__).resolve().parent.parent
    / "fx3_firmware_lab"
    / "xavc_hevc_intra_aces_idt_and_fz100_auditor.py"
)


class TestXavcHevcIntraAcesIdtAndFz100(unittest.TestCase):
    """Comprehensive dual-mode tests (40 tests) for the 26th unified auditor."""

    # ---- Mode, Runtime, Determinism & Structural Hygiene ----

    def test_01_clean_room_report_all_pillars_and_warm_runtime(self) -> None:
        t0 = time.perf_counter()
        rep = analyze_xavc_hevc_intra_aces_idt_and_fz100(clean_room=True)
        dt_cold = time.perf_counter() - t0
        t1 = time.perf_counter()
        rep_warm = analyze_xavc_hevc_intra_aces_idt_and_fz100(clean_room=True)
        dt_warm = time.perf_counter() - t1

        self.assertTrue(rep.all_checks_passed, rep.errors)
        self.assertEqual(rep.mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(rep.schema_version, PHASE_133_SCHEMA)
        self.assertEqual(rep.phase_version, PHASE_133_VERSION)
        self.assertTrue(rep.pillar_a_bionz_xr_codec_matrix.passed)
        self.assertTrue(rep.pillar_b_aces_slog3_idt_matrix.passed)
        self.assertTrue(rep.pillar_c_np_fz100_battery_handshake.passed)
        self.assertTrue(rep.pillar_d_zero_mutation_guard.passed)
        self.assertEqual(rep.report_sha256, rep_warm.report_sha256)
        self.assertEqual(len(rep.report_sha256), 64)
        self.assertLess(dt_cold, 0.08)
        self.assertLess(dt_warm, 0.02)

    def test_02_auto_mode_or_local_donor_runtime_and_sizes(self) -> None:
        t0 = time.perf_counter()
        rep = analyze_xavc_hevc_intra_aces_idt_and_fz100()
        dt = time.perf_counter() - t0
        self.assertTrue(rep.all_checks_passed, rep.errors)
        self.assertIn(rep.mode, ("LOCAL_DONOR_VERIFIED", "CLEAN_ROOM_SYNTHETIC"))
        self.assertLess(dt, 0.35)
        if rep.mode == "LOCAL_DONOR_VERIFIED":
            self.assertGreater(rep.donor_file_sizes.get("fx3_appfw", 0), 70_000_000)
            self.assertGreater(rep.donor_file_sizes.get("fx6_appfw", 0), 45_000_000)
            self.assertGreater(rep.donor_file_sizes.get("fx3_libmpr", 0), 3_000_000)
            self.assertGreater(rep.donor_file_sizes.get("fx6_libmpr", 0), 25_000_000)
            self.assertGreater(rep.donor_file_sizes.get("fx3_cp", 0), 10_000_000)
            self.assertGreater(rep.donor_file_sizes.get("fx6_cp", 0), 10_000_000)

    def test_03_forced_clean_room_env_flag_respected(self) -> None:
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}, clear=False):
            rep = analyze_xavc_hevc_intra_aces_idt_and_fz100()
        self.assertTrue(rep.all_checks_passed, rep.errors)
        self.assertEqual(rep.mode, "CLEAN_ROOM_SYNTHETIC")

    def test_04_missing_donor_falls_back_to_clean_room(self) -> None:
        with mock.patch(
            "fx3_firmware_lab.xavc_hevc_intra_aces_idt_and_fz100_auditor.resolve_donor_file",
            return_value=None,
        ):
            rep = analyze_xavc_hevc_intra_aces_idt_and_fz100(clean_room=False)
        self.assertTrue(rep.all_checks_passed, rep.errors)
        self.assertEqual(rep.mode, "CLEAN_ROOM_SYNTHETIC")

    def test_05_json_serialization_has_no_bytes_repr(self) -> None:
        rep = analyze_xavc_hevc_intra_aces_idt_and_fz100(clean_room=True)
        payload = xavc_hevc_intra_aces_idt_and_fz100_report_to_dict(rep)
        json_str = json.dumps(payload, sort_keys=True)
        self.assertIsNone(_BYTES_REPR_RE.search(json_str), "Unexpected Python bytes repr in JSON")
        self.assertIn(PHASE_133_SCHEMA, json_str)

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

    def test_07_package_exports_and_all_include_phase133_symbols(self) -> None:
        expected_symbols = (
            "PHASE_133_SCHEMA",
            "PHASE_133_VERSION",
            "VALID_CODEC_PROFILES",
            "VALID_CODEC_FPS",
            "XAVC_HS_FORBIDDEN_FPS_FX3",
            "MEDIA_SPEED_CLASSES_MBPS",
            "ALL_INTRA_4K_BITRATES_MBPS",
            "XAVC_HS_4K_422_10BIT_BITRATES_MBPS",
            "XAVC_HS_4K_420_10BIT_BITRATES_MBPS",
            "FX6_XAVC_L_4K_420_8BIT_BITRATES_MBPS",
            "SLOG3_BLACK_CV10",
            "SLOG3_GRAY_18_CV10",
            "SLOG3_WHITE_90_CV10",
            "SLOG3_BREAK_CV10",
            "SLOG3_BREAK_LIN",
            "ACES_OCIO_CLF_TRANSFORM_IDS",
            "CAT_BRADFORD_3X3",
            "CAT_CAT02_3X3",
            "NP_FZ100_NOMINAL_MV",
            "NP_FZ100_ENERGY_WH",
            "NP_FZ100_CAPACITY_MAH",
            "BP_U_SHUTDOWN_MV",
            "XavcHevcIntraAcesIdtAndFz100Report",
            "evaluate_bionz_xr_codec_profile",
            "slog3_linear_to_norm",
            "slog3_norm_to_linear",
            "verify_slog3_transfer_landmarks",
            "matrix_determinant_3x3",
            "invert_3x3_matrix",
            "compute_rgb_to_xyz_3x3",
            "compute_chromatic_adaptation_3x3",
            "compute_aces_idt_matrix_3x3",
            "verify_aces_idt_matrix",
            "evaluate_np_fz100_battery_handshake",
            "evaluate_phase133_write_guard",
            "evaluate_pillar_a_bionz_xr_codec_matrix",
            "evaluate_pillar_b_aces_slog3_idt_matrix",
            "evaluate_pillar_c_np_fz100_battery_handshake",
            "evaluate_pillar_d_zero_mutation_phase133_guard",
            "build_clean_room_xavc_aces_fz100_fixtures",
            "analyze_xavc_hevc_intra_aces_idt_and_fz100",
            "xavc_hevc_intra_aces_idt_and_fz100_report_to_dict",
        )
        for sym in expected_symbols:
            self.assertTrue(hasattr(lab, sym), f"Missing export {sym} on fx3_firmware_lab")
            self.assertIn(sym, lab.__all__, f"Missing {sym} in fx3_firmware_lab.__all__")

    def test_08_clean_room_fixtures_roundtrip_and_uxc_integrity(self) -> None:
        fx = build_clean_room_xavc_aces_fz100_fixtures()
        self.assertEqual(len(fx), 12)
        for key in ("fx3_appfw", "fx6_appfw", "fx3_libmpr", "fx6_libmpr"):
            self.assertTrue(fx[key].startswith(b"\x7fELF\x02\x01\x01"))
        self.assertTrue(fx["fx3_cp"].startswith(b"CPAPP_FX3"))
        self.assertTrue(fx["fx6_cp"].startswith(b"CPAPP_FX6"))
        parse_global_xdb_buffer(fx["fx3_global_xdb"])
        parse_global_xdb_buffer(fx["fx6_global_xdb"])

        lbl_en, e1 = _extract_uxc_labels(fx["fx3_str_en"], FX3_NS39_PHASE133_LABELS)
        lbl_g, e2 = _extract_uxc_labels(fx["fx3_str_en_g"], FX3_NS3_PHASE133_LABELS)
        lbl_1, e3 = _extract_uxc_labels(fx["fx6_str_en_1"], FX6_NS1_PHASE133_LABELS)
        lbl_2, e4 = _extract_uxc_labels(fx["fx6_str_en_2"], FX6_NS2_PHASE133_LABELS)
        self.assertEqual(e1 + e2 + e3 + e4, ())
        self.assertIn("cannot be guaranteed", lbl_en["0x0000e24e"])
        self.assertIn("insufficient battery power", lbl_g["0x00006013"])
        self.assertEqual(lbl_1["0x0000219f"], "S-Log3")
        self.assertEqual(lbl_1["0x00002b03"], "XAVC S-I")
        self.assertEqual(lbl_2["0x000044fe"], "S-Gamut \u2192 S-Gamut3.Cine")

    # ---- Pillar A: BIONZ XR XAVC HS (HEVC) vs XAVC S-I / XAVC-I Codec Matrix ----

    def test_09_xavc_i_mxf_and_xavc_s_i_mp4_elementary_parity_and_rates(self) -> None:
        fx6 = evaluate_bionz_xr_codec_profile(
            codec_profile="FX6_XAVC_I_CLASS300_MXF",
            fps=23.976,
            media_card_class="CFEXPRESS_A_VPG200",
        )
        fx3 = evaluate_bionz_xr_codec_profile(
            codec_profile="FX3_XAVC_S_I_4K_MP4",
            fps=23.976,
            media_card_class="SDXC_V90",
        )
        self.assertTrue(fx6.valid and fx3.valid)
        self.assertEqual(fx6.compression_scheme, fx3.compression_scheme)
        self.assertEqual(fx6.gop_mode, "ALL_INTRA_CBG")
        self.assertEqual(fx6.bitrate_mbps, 240.0)
        self.assertEqual(fx3.bitrate_mbps, 240.0)
        self.assertEqual(fx6.container_format, "MXF_OP1A")
        self.assertEqual(fx3.container_format, "MP4_ISOBMFF")
        self.assertTrue(fx6.bitstream_lossless_rewrap_compatible)
        self.assertTrue(fx3.bitstream_lossless_rewrap_compatible)
        self.assertFalse(fx3.hw_decode_engine_recommended)

    def test_10_xavc_s_i_all_intra_4k60_600mbps_on_v90_vs_v60(self) -> None:
        ok_v90 = evaluate_bionz_xr_codec_profile(
            codec_profile="FX3_XAVC_S_I_4K_MP4",
            fps=59.94,
            media_card_class="SDXC_V90",
        )
        self.assertTrue(ok_v90.valid, ok_v90.errors)
        self.assertEqual(ok_v90.bitrate_mbps, 600.0)
        self.assertAlmostEqual(ok_v90.storage_gb_per_hour, 270.0, places=1)

        blk_v60 = evaluate_bionz_xr_codec_profile(
            codec_profile="FX3_XAVC_S_I_4K_MP4",
            fps=59.94,
            media_card_class="SDXC_V60",
        )
        self.assertFalse(blk_v60.valid)
        self.assertEqual(blk_v60.status, "BLOCKED_INSUFFICIENT_MEDIA_SPEED_CLASS")

    def test_11_xavc_s_i_sq120_1200mbps_requires_cfexpress_vpg200_or_vpg400(self) -> None:
        for card in ("CFEXPRESS_A_VPG200", "CFEXPRESS_A_VPG400"):
            ok = evaluate_bionz_xr_codec_profile(
                codec_profile="FX3_XAVC_S_I_4K_MP4",
                fps=119.88,
                media_card_class=card,
            )
            self.assertTrue(ok.valid, ok.errors)
            self.assertEqual(ok.bitrate_mbps, 1200.0)

        for card in ("SDXC_V30", "SDXC_V60", "SDXC_V90"):
            blk = evaluate_bionz_xr_codec_profile(
                codec_profile="FX3_XAVC_S_I_4K_MP4",
                fps=119.88,
                media_card_class=card,
            )
            self.assertFalse(blk.valid, card)
            self.assertEqual(blk.status, "BLOCKED_INSUFFICIENT_MEDIA_SPEED_CLASS")

    def test_12_xavc_hs_hevc_422_and_420_10bit_vbr_vbv_envelopes(self) -> None:
        hs_60 = evaluate_bionz_xr_codec_profile(
            codec_profile="FX3_XAVC_HS_4K_HEVC_422_10BIT",
            fps=59.94,
            requested_bitrate_mbps=200.0,
            media_card_class="SDXC_V60",
        )
        self.assertTrue(hs_60.valid, hs_60.errors)
        self.assertEqual(hs_60.compression_scheme, "HEVC_H265_MAIN_422_10")
        self.assertEqual(hs_60.gop_mode, "LONG_GOP_VBR")
        self.assertEqual(hs_60.bit_depth, 10)
        self.assertEqual(hs_60.chroma_subsampling, "4:2:2")
        self.assertEqual(hs_60.vbv_buffer_kbytes, 37500)
        self.assertTrue(hs_60.hw_decode_engine_recommended)

        hs_120 = evaluate_bionz_xr_codec_profile(
            codec_profile="FX3_XAVC_HS_4K_HEVC_420_10BIT",
            fps=119.88,
            requested_bitrate_mbps=200.0,
            media_card_class="SDXC_V30",
        )
        self.assertTrue(hs_120.valid, hs_120.errors)
        self.assertEqual(hs_120.chroma_subsampling, "4:2:0")

    def test_13_xavc_hs_blocks_25p_and_2997p_on_fx3_and_invalid_bitrates(self) -> None:
        for fps in XAVC_HS_FORBIDDEN_FPS_FX3:
            blk = evaluate_bionz_xr_codec_profile(
                codec_profile="FX3_XAVC_HS_4K_HEVC_422_10BIT",
                fps=fps,
                media_card_class="CFEXPRESS_A_VPG200",
            )
            self.assertFalse(blk.valid)
            self.assertEqual(blk.status, "BLOCKED_XAVC_HS_UNSUPPORTED_FPS")

        bad_rate = evaluate_bionz_xr_codec_profile(
            codec_profile="FX3_XAVC_HS_4K_HEVC_422_10BIT",
            fps=23.976,
            requested_bitrate_mbps=300.0,
            media_card_class="CFEXPRESS_A_VPG200",
        )
        self.assertFalse(bad_rate.valid)
        self.assertEqual(bad_rate.status, "BLOCKED_INVALID_XAVC_HS_BITRATE")

        bad_intra = evaluate_bionz_xr_codec_profile(
            codec_profile="FX3_XAVC_S_I_4K_MP4",
            fps=23.976,
            requested_bitrate_mbps=600.0,
            media_card_class="CFEXPRESS_A_VPG200",
        )
        self.assertFalse(bad_intra.valid)
        self.assertEqual(bad_intra.status, "BLOCKED_ALL_INTRA_FIXED_RATE_MISMATCH")

    def test_14_fx6_xavc_l_8bit_and_proxy_overhead_speed_gate(self) -> None:
        xavc_l = evaluate_bionz_xr_codec_profile(
            codec_profile="FX6_XAVC_L_4K_420_8BIT",
            fps=59.94,
            media_card_class="SDXC_V30",
        )
        self.assertTrue(xavc_l.valid, xavc_l.errors)
        self.assertEqual(xavc_l.bit_depth, 8)
        self.assertEqual(xavc_l.chroma_subsampling, "4:2:0")
        self.assertEqual(xavc_l.bitrate_mbps, 150.0)

        # 240 Mbps + 16 Mbps proxy = 256 Mbps > SDXC_V30 (240 Mbps)
        no_proxy = evaluate_bionz_xr_codec_profile(
            codec_profile="FX3_XAVC_S_I_4K_MP4",
            fps=23.976,
            media_card_class="SDXC_V30",
            proxy_enabled=False,
        )
        with_proxy = evaluate_bionz_xr_codec_profile(
            codec_profile="FX3_XAVC_S_I_4K_MP4",
            fps=23.976,
            media_card_class="SDXC_V30",
            proxy_enabled=True,
        )
        self.assertTrue(no_proxy.valid)
        self.assertFalse(with_proxy.valid)
        self.assertEqual(with_proxy.status, "BLOCKED_INSUFFICIENT_MEDIA_SPEED_CLASS")

    def test_15_codec_evaluator_rejects_unknown_enum_inputs(self) -> None:
        with self.assertRaises(ValueError):
            evaluate_bionz_xr_codec_profile(codec_profile="PRORES_4444")
        with self.assertRaises(ValueError):
            evaluate_bionz_xr_codec_profile(media_card_class="SDXC_V10")
        with self.assertRaises(ValueError):
            evaluate_bionz_xr_codec_profile(fps=48.0)

    def test_16_pillar_a_report_embeds_verified_elf_markers(self) -> None:
        rep = analyze_xavc_hevc_intra_aces_idt_and_fz100(clean_room=True)
        pa = rep.pillar_a_bionz_xr_codec_matrix
        self.assertEqual(set(pa.fx3_appfw_codec_markers), set(FX3_APPFW_PHASE133_MARKERS[:4]))
        self.assertEqual(set(pa.fx3_libmpr_codec_markers), set(FX3_LIBMPR_PHASE133_MARKERS))
        self.assertEqual(set(pa.fx6_libmpr_codec_markers), set(FX6_LIBMPR_PHASE133_MARKERS))
        self.assertEqual(len(ALL_INTRA_4K_BITRATES_MBPS), 8)
        self.assertEqual(MEDIA_SPEED_CLASSES_MBPS["CFEXPRESS_A_VPG400"], 3200.0)

    # ---- Pillar B: ACES 1.3 / 2.0 S-Log3 & S-Gamut3(.Cine) IDT Matrix Verifier ----

    def test_17_slog3_official_landmarks_95_420_598_and_c0_continuity(self) -> None:
        proof = verify_slog3_transfer_landmarks()
        self.assertTrue(proof.valid, proof.errors)
        self.assertEqual(proof.status, "SLOG3_PIECEWISE_VERIFIED")
        self.assertAlmostEqual(proof.black_0pct_cv10, SLOG3_BLACK_CV10, places=6)
        self.assertAlmostEqual(proof.gray_18pct_cv10, SLOG3_GRAY_18_CV10, places=6)
        self.assertAlmostEqual(proof.white_90pct_cv10, SLOG3_WHITE_90_CV10, delta=0.25)
        self.assertEqual(proof.breakpoint_lin, SLOG3_BREAK_LIN)
        self.assertEqual(proof.breakpoint_cv10, SLOG3_BREAK_CV10)
        self.assertLess(proof.toe_continuity_delta, 1e-6)
        self.assertLess(proof.max_roundtrip_error, 1e-11)

    def test_18_slog3_roundtrip_sweep_below_and_above_breakpoint(self) -> None:
        samples = (-0.005, 0.0, 0.005, 0.01124, 0.01125, 0.01126, 0.18, 0.90, 4.0, 38.4)
        for lin in samples:
            norm = slog3_linear_to_norm(lin)
            rt = slog3_norm_to_linear(norm)
            self.assertAlmostEqual(rt, lin, places=11)
        with self.assertRaises(ValueError):
            slog3_linear_to_norm(float("nan"))
        with self.assertRaises(ValueError):
            slog3_norm_to_linear(float("inf"))

    def test_19_all_four_bradford_aces_idt_matrices_invertible_and_wp_exact(self) -> None:
        for src in ("S_GAMUT3", "S_GAMUT3_CINE"):
            for dst in ("ACES2065_1_AP0", "ACESCG_AP1"):
                ev = verify_aces_idt_matrix(
                    source_gamut=src,
                    target_space=dst,
                    adaptation_method="BRADFORD",
                )
                self.assertTrue(ev.valid, f"{src}->{dst} failed: {ev.errors}")
                self.assertGreater(abs(ev.determinant), ACES_MIN_DET_ABS)
                self.assertLess(ev.max_inv_roundtrip_error, 1e-11)
                self.assertLess(ev.max_whitepoint_error, 1e-12)
                self.assertLess(ev.max_whitepoint_error, ACES_MAX_WHITEPOINT_ERROR)
                self.assertEqual(ev.ocio_transform_id, ACES_OCIO_CLF_TRANSFORM_IDS[src])

    def test_20_cat02_ocio_v2_matrices_match_aswf_clf_and_differ_boundedly_from_bradford(self) -> None:
        ev_c = verify_aces_idt_matrix(
            source_gamut="S_GAMUT3_CINE",
            target_space="ACES2065_1_AP0",
            adaptation_method="CAT02",
        )
        ev_b = verify_aces_idt_matrix(
            source_gamut="S_GAMUT3_CINE",
            target_space="ACES2065_1_AP0",
            adaptation_method="BRADFORD",
        )
        self.assertTrue(ev_c.valid, ev_c.errors)
        # Verified ASWF OpenColorIO-Config-ACES CAT02 row 0 for S-Gamut3.Cine -> AP0:
        self.assertAlmostEqual(ev_c.matrix_3x3[0][0], 0.638788667185978, places=4)
        self.assertAlmostEqual(ev_c.matrix_3x3[0][1], 0.272351433711262, places=4)
        self.assertAlmostEqual(ev_c.matrix_3x3[0][2], 0.088859899102760, places=4)

        delta = max(
            abs(ev_c.matrix_3x3[r][c] - ev_b.matrix_3x3[r][c])
            for r in range(3)
            for c in range(3)
        )
        self.assertGreater(delta, 1e-3)
        self.assertLess(delta, 1e-2)

        # Both CAT matrices themselves must have det ~ 1 and remain strictly invertible
        self.assertGreater(abs(matrix_determinant_3x3(CAT_BRADFORD_3X3)), 0.5)
        self.assertGreater(abs(matrix_determinant_3x3(CAT_CAT02_3X3)), 0.5)

    def test_21_aces_idt_blocks_singular_degenerate_and_whitepoint_drift_matrices(self) -> None:
        blk_sing = verify_aces_idt_matrix(
            custom_matrix=((0.5, 0.5, 0.0), (0.5, 0.5, 0.0), (0.0, 0.0, 1.0))
        )
        self.assertFalse(blk_sing.valid)
        self.assertEqual(blk_sing.status, "BLOCKED_SINGULAR_IDT_MATRIX")

        blk_deg = verify_aces_idt_matrix(
            custom_matrix=((0.9, 0.1, 0.0), (0.8, 0.2, 0.0), (0.0, 0.0, 1.0))
        )
        self.assertFalse(blk_deg.valid)
        self.assertEqual(blk_deg.status, "BLOCKED_DEGENERATE_IDT_DETERMINANT")

        blk_wp = verify_aces_idt_matrix(
            custom_matrix=((0.65, 0.27, 0.09), (0.0, 1.08, -0.08), (-0.03, -0.02, 1.05))
        )
        self.assertFalse(blk_wp.valid)
        self.assertEqual(blk_wp.status, "BLOCKED_WHITEPOINT_CONSERVATION_DRIFT")

    def test_22_matrix_helpers_and_gamut_validation_errors(self) -> None:
        with self.assertRaises(ValueError):
            invert_3x3_matrix(((1.0, 2.0, 3.0), (2.0, 4.0, 6.0), (0.0, 0.0, 1.0)))
        with self.assertRaises(ValueError):
            compute_aces_idt_matrix_3x3("REC709", "ACES2065_1_AP0")
        with self.assertRaises(ValueError):
            compute_aces_idt_matrix_3x3("S_GAMUT3", "REC2020")
        with self.assertRaises(ValueError):
            compute_aces_idt_matrix_3x3("S_GAMUT3", "ACESCG_AP1", "VON_KRIES")

    def test_23_pillar_b_report_embeds_gamut_elf_markers_and_cat_delta(self) -> None:
        rep = analyze_xavc_hevc_intra_aces_idt_and_fz100(clean_room=True)
        pb = rep.pillar_b_aces_slog3_idt_matrix
        self.assertEqual(set(pb.fx3_appfw_gamut_markers), set(FX3_APPFW_PHASE133_MARKERS[4:7]))
        self.assertEqual(set(pb.fx6_appfw_gamut_markers), set(FX6_APPFW_PHASE133_MARKERS[:3]))
        self.assertGreater(pb.cat02_vs_bradford_max_entry_delta, 0.001)
        self.assertLess(pb.cat02_vs_bradford_max_entry_delta, 0.01)

    # ---- Pillar C: NP-FZ100 InfoLITHIUM C-Pin & Cross-Rail Voltage Guard ----

    def test_24_oem_and_decoded_3p_np_fz100_pass_with_stageb_mapped_soc(self) -> None:
        self.assertEqual(NP_FZ100_NOMINAL_MV, 7200)
        self.assertEqual(NP_FZ100_ENERGY_WH, 16.4)
        self.assertEqual(NP_FZ100_CAPACITY_MAH, 2280)

        for pack in ("OEM_NP_FZ100", "DECODED_3P_NP_FZ100"):
            ev = evaluate_np_fz100_battery_handshake(
                pack_type=pack,
                camera_rail="FX3_7V2_NP_FZ100",
                pack_voltage_mv=7600,
                reported_soc_pct=78,
                stage_b_fx6_overlay_active=True,
                fx6_ui_normalized_pct_mapped=True,
            )
            self.assertTrue(ev.valid, ev.errors)
            self.assertEqual(ev.status, "INFOLITHIUM_C_PIN_VERIFIED")
            self.assertTrue(ev.c_pin_auth_passed)
            self.assertTrue(ev.percentage_display_visible)
            self.assertTrue(ev.fw_update_allowed)
            self.assertFalse(ev.degraded_power_mode)
            self.assertFalse(ev.false_low_batt_shutdown_triggered)

    def test_25_undecoded_3p_and_regulated_dummy_enter_safe_degraded_no_pct(self) -> None:
        undec = evaluate_np_fz100_battery_handshake(
            pack_type="UNDECODED_3P_NP_FZ100",
            camera_rail="FX3_7V2_NP_FZ100",
            pack_voltage_mv=7450,
            c_pin_connected=True,
            c_pin_auth_valid=False,
            user_confirmed_continue=True,
        )
        self.assertTrue(undec.valid, undec.errors)
        self.assertEqual(undec.status, "SAFE_DEGRADED_POWER_NO_PCT")
        self.assertTrue(undec.degraded_power_mode)
        self.assertFalse(undec.c_pin_auth_passed)
        self.assertFalse(undec.percentage_display_visible)
        self.assertFalse(undec.fw_update_allowed)
        self.assertIsNone(undec.soc_pct)
        self.assertTrue(undec.safe_to_operate)

        dummy = evaluate_np_fz100_battery_handshake(
            pack_type="REGULATED_DUMMY_CPIN_ABSENT",
            camera_rail="FX3_7V2_NP_FZ100",
            pack_voltage_mv=7800,
            c_pin_connected=False,
            c_pin_auth_valid=False,
            user_confirmed_continue=True,
        )
        self.assertTrue(dummy.valid, dummy.errors)
        self.assertEqual(dummy.status, "SAFE_DEGRADED_POWER_NO_PCT")
        self.assertFalse(dummy.c_pin_telemetry_present)
        self.assertFalse(dummy.percentage_display_visible)
        self.assertFalse(dummy.fw_update_allowed)

    def test_26_unmapped_fx6_14v4_threshold_on_fx3_7v2_rail_blocked(self) -> None:
        blk = evaluate_np_fz100_battery_handshake(
            pack_type="OEM_NP_FZ100",
            camera_rail="FX3_7V2_NP_FZ100",
            pack_voltage_mv=7650,
            reported_soc_pct=82,
            stage_b_fx6_overlay_active=True,
            fx6_ui_normalized_pct_mapped=False,
        )
        self.assertFalse(blk.valid)
        self.assertTrue(blk.false_low_batt_shutdown_triggered)
        self.assertFalse(blk.safe_to_operate)
        self.assertEqual(blk.status, "BLOCKED_FALSE_FX6_14V4_LOW_BATT_SHUTDOWN")
        self.assertIn(str(BP_U_SHUTDOWN_MV), blk.errors[0])

    def test_27_undecoded_user_cancel_overvolt_dummy_and_thermal_guards(self) -> None:
        cancel = evaluate_np_fz100_battery_handshake(
            pack_type="UNDECODED_3P_NP_FZ100",
            c_pin_connected=True,
            c_pin_auth_valid=False,
            user_confirmed_continue=False,
        )
        self.assertFalse(cancel.valid)
        self.assertFalse(cancel.safe_to_operate)
        self.assertEqual(cancel.status, "BLOCKED_UNVERIFIED_BATTERY_USER_CANCELLED")

        overvolt = evaluate_np_fz100_battery_handshake(
            pack_type="UNREGULATED_DANGEROUS_DUMMY",
            camera_rail="FX3_7V2_NP_FZ100",
            pack_voltage_mv=12000,
            c_pin_connected=False,
            c_pin_auth_valid=False,
        )
        self.assertFalse(overvolt.valid)
        self.assertEqual(overvolt.status, "BLOCKED_BATTERY_RAIL_OUT_OF_SAFE_ENVELOPE")

        cold = evaluate_np_fz100_battery_handshake(temp_c=-5.0)
        hot = evaluate_np_fz100_battery_handshake(temp_c=65.0)
        self.assertFalse(cold.valid)
        self.assertFalse(hot.valid)
        self.assertEqual(cold.status, "BLOCKED_BATTERY_THERMAL_SHUTDOWN")
        self.assertEqual(hot.status, "BLOCKED_BATTERY_THERMAL_SHUTDOWN")

    def test_28_fw_update_requires_at_least_51pct_soc_and_fx6_bpu_rail_checks(self) -> None:
        low_soc = evaluate_np_fz100_battery_handshake(
            pack_type="OEM_NP_FZ100",
            pack_voltage_mv=7050,
            reported_soc_pct=NP_FZ100_FW_UPDATE_MIN_SOC_PCT - 6,
        )
        self.assertTrue(low_soc.valid)
        self.assertTrue(low_soc.safe_to_operate)
        self.assertFalse(low_soc.fw_update_allowed)

        fx6_dc = evaluate_np_fz100_battery_handshake(
            pack_type="FX6_BP_U35_14V4_NATIVE",
            camera_rail="FX6_14V4_BP_U",
            pack_voltage_mv=19500,
            reported_soc_pct=100,
            stage_b_fx6_overlay_active=False,
        )
        self.assertTrue(fx6_dc.valid, fx6_dc.errors)

        fx6_low = evaluate_np_fz100_battery_handshake(
            pack_type="FX6_BP_U35_14V4_NATIVE",
            camera_rail="FX6_14V4_BP_U",
            pack_voltage_mv=11500,
            stage_b_fx6_overlay_active=False,
        )
        self.assertFalse(fx6_low.valid)
        self.assertEqual(fx6_low.status, "BLOCKED_FX6_BP_U_VOLTAGE_END")

    def test_29_battery_handshake_rejects_bad_enums_and_embeds_cp_markers(self) -> None:
        with self.assertRaises(ValueError):
            evaluate_np_fz100_battery_handshake(pack_type="NP_FW50")
        with self.assertRaises(ValueError):
            evaluate_np_fz100_battery_handshake(camera_rail="A7S3_7V2")

        rep = analyze_xavc_hevc_intra_aces_idt_and_fz100(clean_room=True)
        pc = rep.pillar_c_np_fz100_battery_handshake
        self.assertEqual(set(pc.fx3_appfw_batt_markers), set(FX3_APPFW_PHASE133_MARKERS[7:]))
        self.assertEqual(set(pc.fx6_appfw_batt_markers), set(FX6_APPFW_PHASE133_MARKERS[3:]))
        self.assertEqual(set(pc.fx3_cp_batt_markers), set(CP_SHARED_PHASE133_MARKERS))
        self.assertEqual(set(pc.fx6_cp_batt_markers), set(CP_SHARED_PHASE133_MARKERS))

    # ---- Pillar D: Volatile RAM Staging & Zero eMMC / Calibration Mutation Guard ----

    def test_30_write_guard_allows_volatile_and_blocks_all_persistent_targets(self) -> None:
        for ok_path in (
            "/tmp/fx3_stageb_xavc_aces_fz100.json",
            "ram://aces_idt_lut_cache.bin",
            "memory://fz100_telemetry_shadow",
        ):
            g = evaluate_phase133_write_guard(ok_path)
            self.assertTrue(g.valid, ok_path)
            self.assertTrue(g.volatile_ram_staged)
            self.assertFalse(g.persistent_write_blocked)
            self.assertEqual(g.emmc_mutation_bytes, 0)
            self.assertEqual(g.calibration_mutation_bytes, 0)

        for bad_path in (
            "/mnt/sd/BODYDATA.DAT",
            "/dev/nflasha15",
            "/dev/cnflasha0",
            "/dev/mmcblk0rpmb",
            "/dev/mtdblock0",
            "p2:/setting/Backup.bin",
            "p2:/setting/psd.bin",
            "p2:/setting/defdet.bin",
            "p6:/tmp/jiritsu",
            "updater://flash",
            "nvram://bk4",
            "eeprom://battery_cal",
        ):
            g = evaluate_phase133_write_guard(bad_path)
            self.assertFalse(g.valid, bad_path)
            self.assertFalse(g.volatile_ram_staged)
            self.assertTrue(g.persistent_write_blocked)
            self.assertEqual(g.emmc_mutation_bytes, 0)
            self.assertEqual(g.calibration_mutation_bytes, 0)

    def test_31_pillar_d_zero_mutation_proof_and_bad_xdb_rejection(self) -> None:
        pd_ok = evaluate_pillar_d_zero_mutation_phase133_guard(
            fx3_global_xdb_valid=True,
            fx6_global_xdb_valid=True,
        )
        self.assertTrue(pd_ok.passed)
        self.assertEqual(pd_ok.emmc_mutation_bytes, 0)
        self.assertEqual(pd_ok.calibration_mutation_bytes, 0)
        self.assertFalse(pd_ok.persistent_emmc_writes_authorized)

        pd_bad_fx3 = evaluate_pillar_d_zero_mutation_phase133_guard(
            fx3_global_xdb_valid=False,
            fx6_global_xdb_valid=True,
        )
        pd_bad_fx6 = evaluate_pillar_d_zero_mutation_phase133_guard(
            fx3_global_xdb_valid=True,
            fx6_global_xdb_valid=False,
        )
        self.assertFalse(pd_bad_fx3.passed)
        self.assertFalse(pd_bad_fx6.passed)

    # ---- Negative Donor Integrity Checks ----

    def test_32_missing_elf_markers_fail_closed_per_pillar(self) -> None:
        pa = evaluate_pillar_a_bionz_xr_codec_matrix(
            fx3_appfw_codec_markers=(),
            fx3_libmpr_codec_markers=(),
            fx6_libmpr_codec_markers=(),
            uxc_codec_labels={},
            extra_errors=("Missing FX3 libmpr Codec markers",),
        )
        pb = evaluate_pillar_b_aces_slog3_idt_matrix(
            fx3_appfw_gamut_markers=(),
            fx6_appfw_gamut_markers=(),
            uxc_gamut_labels={},
            extra_errors=("Missing FX6 appFw Gamut markers",),
        )
        pc = evaluate_pillar_c_np_fz100_battery_handshake(
            fx3_appfw_batt_markers=(),
            fx6_appfw_batt_markers=(),
            fx3_cp_batt_markers=(),
            fx6_cp_batt_markers=(),
            uxc_batt_labels={},
            extra_errors=("Missing FX3 cpapp Battery markers",),
        )
        self.assertFalse(pa.passed)
        self.assertFalse(pb.passed)
        self.assertFalse(pc.passed)

    # ---- CLI & 26-Auditor Integration ----

    def test_33_cli_audit_xavc_aces_fz100_clean_room_in_process(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cli_main(["audit-xavc-aces-fz100", "--clean-room", "--json"])
        self.assertEqual(rc, 0)
        data = json.loads(buf.getvalue())
        self.assertTrue(data["all_checks_passed"])
        self.assertEqual(data["mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(data["schema_version"], PHASE_133_SCHEMA)

    def test_34_cli_audit_xavc_aces_fz100_auto_mode_in_process(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cli_main(["audit-xavc-aces-fz100", "--json"])
        self.assertEqual(rc, 0)
        data = json.loads(buf.getvalue())
        self.assertTrue(data["all_checks_passed"])
        self.assertIn(data["mode"], ("LOCAL_DONOR_VERIFIED", "CLEAN_ROOM_SYNTHETIC"))

    def test_35_run_audit_all_includes_at_least_26_auditors_and_passes(self) -> None:
        summary_clean = run_audit_all(clean_room=True)
        self.assertTrue(summary_clean["all_checks_passed"])
        audit_keys = [k for k in summary_clean if k.endswith("_audit")]
        self.assertGreaterEqual(len(audit_keys), 26)
        self.assertIn("xavc_hevc_intra_aces_idt_and_fz100_audit", summary_clean)
        self.assertTrue(summary_clean["xavc_hevc_intra_aces_idt_and_fz100_audit"]["all_checks_passed"])

        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cli_main(["audit-all", "--clean-room", "--json"])
        self.assertEqual(rc, 0)
        cli_summary = json.loads(buf.getvalue())
        self.assertTrue(cli_summary["all_checks_passed"])
        cli_audit_keys = [k for k in cli_summary if k.endswith("_audit")]
        self.assertGreaterEqual(len(cli_audit_keys), 26)

    # ---- Cross-Pillar Consistency & Edge Checks ----

    def test_36_xavc_s_i_and_xavc_i_25p_50p_bitrates_match_sony_specs(self) -> None:
        for fps, expected in ((24.0, 240.0), (25.0, 250.0), (29.97, 300.0), (50.0, 500.0), (59.94, 600.0)):
            r3 = evaluate_bionz_xr_codec_profile(
                codec_profile="FX3_XAVC_S_I_4K_MP4",
                fps=fps,
                media_card_class="CFEXPRESS_A_VPG200",
            )
            r6 = evaluate_bionz_xr_codec_profile(
                codec_profile="FX6_XAVC_I_CLASS300_MXF",
                fps=fps,
                media_card_class="CFEXPRESS_A_VPG200",
            )
            self.assertTrue(r3.valid and r6.valid)
            self.assertEqual(r3.bitrate_mbps, expected)
            self.assertEqual(r6.bitrate_mbps, expected)

    def test_37_aces_idt_transforms_d65_unit_white_to_aces_unit_white(self) -> None:
        for cat in ("BRADFORD", "CAT02"):
            for src in ("S_GAMUT3", "S_GAMUT3_CINE"):
                for dst in ("ACES2065_1_AP0", "ACESCG_AP1"):
                    m = compute_aces_idt_matrix_3x3(src, dst, cat)
                    out = [sum(m[r][c] * 1.0 for c in range(3)) for r in range(3)]
                    for val in out:
                        self.assertAlmostEqual(val, 1.0, places=10)

    def test_38_soc_auto_estimation_when_reported_soc_is_none(self) -> None:
        ev = evaluate_np_fz100_battery_handshake(
            pack_type="OEM_NP_FZ100",
            camera_rail="FX3_7V2_NP_FZ100",
            pack_voltage_mv=7200,
            reported_soc_pct=None,
        )
        self.assertTrue(ev.valid)
        self.assertEqual(ev.soc_pct, 50)
        self.assertFalse(ev.fw_update_allowed)  # 50% < 51% threshold

    def test_39_xavc_hs_storage_savings_vs_xavc_s_i_at_4k60(self) -> None:
        si = evaluate_bionz_xr_codec_profile(
            codec_profile="FX3_XAVC_S_I_4K_MP4",
            fps=59.94,
            media_card_class="CFEXPRESS_A_VPG200",
        )
        hs = evaluate_bionz_xr_codec_profile(
            codec_profile="FX3_XAVC_HS_4K_HEVC_422_10BIT",
            fps=59.94,
            requested_bitrate_mbps=200.0,
            media_card_class="SDXC_V60",
        )
        self.assertEqual(si.storage_gb_per_hour, 270.0)
        self.assertEqual(hs.storage_gb_per_hour, 90.0)
        self.assertAlmostEqual(si.storage_gb_per_hour / hs.storage_gb_per_hour, 3.0, places=3)

    def test_40_clean_room_report_contains_all_uxc_and_xdb_fields(self) -> None:
        rep = analyze_xavc_hevc_intra_aces_idt_and_fz100(clean_room=True)
        self.assertTrue(rep.pillar_d_zero_mutation_guard.fx3_global_xdb_valid)
        self.assertTrue(rep.pillar_d_zero_mutation_guard.fx6_global_xdb_valid)
        self.assertTrue(rep.pillar_a_bionz_xr_codec_matrix.uxc_codec_labels["fx6_xavc_s_i"])
        self.assertTrue(rep.pillar_b_aces_slog3_idt_matrix.uxc_gamut_labels["fx6_slog3"])
        self.assertTrue(rep.pillar_c_np_fz100_battery_handshake.uxc_batt_labels["fx3_battery_auth_caution"])


if __name__ == "__main__":
    unittest.main()
