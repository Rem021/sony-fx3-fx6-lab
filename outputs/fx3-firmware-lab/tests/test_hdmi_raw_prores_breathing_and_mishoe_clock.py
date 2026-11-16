"""Phase 114 Dual-Mode Unit Tests: External Atomos ProRes RAW / Blackmagic BRAW
16-Bit Linear -> 12-Bit Log Metadata Handshake, Focus-Breathing Dynamic FOV
Crop LUTs vs HDMI RAW / S&Q 120p Mutual-Exclusion Guard, 24-Pin MI-Shoe I2S
48.000 kHz Audio Master-Clock PLL Drift Firewall, & Per-Body Factory OB-Clamp
/ Black-Level Pedestal Preservation Proof.
"""

from __future__ import annotations

import io
import json
import math
import os
import re
import time
import unittest
from contextlib import redirect_stdout
from fractions import Fraction
from pathlib import Path
from unittest import mock

import fx3_firmware_lab as lab
from fx3_firmware_lab.__main__ import main as cli_main, run_audit_all
from fx3_firmware_lab.emount_af_breathing_and_ibis_auditor import _extract_uxc_labels
from fx3_firmware_lab.global_xdb_and_menu_tree_auditor import parse_global_xdb_buffer
from fx3_firmware_lab.hdmi_raw_prores_breathing_and_mishoe_clock_auditor import (
    AUDIO_SAMPLE_RATE_48K,
    BREATHING_CROP_MAX,
    BREATHING_CROP_MIN,
    COLOR_MATRIX_SGAMUT3CINE,
    CP_SHARED_PHASE114_MARKERS,
    EMOUNT_BREATHING_LENS_PROFILES,
    FRAME_RATE_RATIONAL_SPECS,
    FX3_APPFW_PHASE114_MARKERS,
    FX3_CP_EXTRA_PHASE114_MARKERS,
    FX3_LIBMPR_PHASE114_MARKERS,
    FX3_NS39_PHASE114_LABELS,
    FX3_NS3_PHASE114_LABELS,
    FX6_APPFW_PHASE114_MARKERS,
    FX6_CP_EXTRA_PHASE114_MARKERS,
    FX6_HOTSHOE_PHASE114_MARKERS,
    FX6_LIBMPR_PHASE114_MARKERS,
    FX6_NS1_PHASE114_LABELS,
    FX6_NS2_PHASE114_LABELS,
    IMX510_RAW16_OB_CLAMP_ADU,
    LONG_TAKE_DURATION_SEC,
    MAX_ALLOWED_LIPSYNC_DRIFT_MS,
    NTSC_2997_5FRAME_CADENCE,
    NTSC_5994_5FRAME_CADENCE,
    PHASE_114_SCHEMA,
    PHASE_114_VERSION,
    RAW12_MAX_CODE,
    RAW16_MAX_CODE,
    RAW16_MIN_DYNAMIC_RANGE_STOPS,
    RAW16_TO_RAW12_PIECEWISE_KNOTS,
    RAW_HDMI_METADATA_CROP_DIMS,
    RAW_HDMI_UNCROPPED_DIMS,
    RAW_META_PACKET_BYTES,
    RAW_META_PACKET_MAGIC,
    SLOG3_10BIT_BLACK_PEDESTAL,
    VALID_DUAL_BASE_ISOS,
    VALID_RAW_RECORDERS,
    analyze_hdmi_raw_prores_breathing_and_mishoe_clock,
    build_clean_room_prores_breathing_mishoe_fixtures,
    build_hdmi_raw_metadata_packet,
    compute_breathing_fov_crop_factor,
    decode_hdmi_raw_metadata_packet,
    evaluate_focus_breathing_guard,
    evaluate_hdmi_raw_metadata_handshake,
    evaluate_mishoe_i2s_clock_pll,
    evaluate_ob_clamp_write_guard,
    hdmi_raw_prores_breathing_and_mishoe_clock_report_to_dict,
    sony_raw12_log_to_raw16,
    sony_raw16_to_raw12_log,
    verify_raw16_to_raw12_dynamic_range,
)


_BYTES_REPR_RE = re.compile(r"(?<![0-9A-Za-z_/.-])b['\"]")
_AUDITOR_PATH = (
    Path(__file__).resolve().parent.parent
    / "fx3_firmware_lab"
    / "hdmi_raw_prores_breathing_and_mishoe_clock_auditor.py"
)


class TestHdmiRawProresBreathingAndMishoeClock(unittest.TestCase):
    """Comprehensive dual-mode tests (>= 40) for the 22nd unified auditor."""

    # ---- Mode, Runtime, Determinism & Structural Hygiene ----

    def test_01_clean_room_report_all_pillars_and_warm_runtime(self) -> None:
        t0 = time.perf_counter()
        rep = analyze_hdmi_raw_prores_breathing_and_mishoe_clock(clean_room=True)
        dt_cold = time.perf_counter() - t0
        t1 = time.perf_counter()
        rep_warm = analyze_hdmi_raw_prores_breathing_and_mishoe_clock(clean_room=True)
        dt_warm = time.perf_counter() - t1

        self.assertTrue(rep.all_checks_passed, rep.errors)
        self.assertEqual(rep.mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(rep.schema_version, PHASE_114_SCHEMA)
        self.assertEqual(rep.phase_version, PHASE_114_VERSION)
        self.assertTrue(rep.pillar_1_raw16_prores_braw.passed)
        self.assertTrue(rep.pillar_2_focus_breathing_guard.passed)
        self.assertTrue(rep.pillar_3_mishoe_48k_pll_clock.passed)
        self.assertTrue(rep.pillar_4_ob_clamp_preservation.passed)
        self.assertEqual(rep.report_sha256, rep_warm.report_sha256)
        self.assertEqual(len(rep.report_sha256), 64)
        self.assertLess(dt_cold, 0.50 if __import__("os").environ.get("GITHUB_ACTIONS") == "true" else 0.08)
        self.assertLess(dt_warm, 0.25 if __import__("os").environ.get("GITHUB_ACTIONS") == "true" else 0.02)

    def test_02_auto_mode_or_local_donor_runtime_and_sizes(self) -> None:
        t0 = time.perf_counter()
        rep = analyze_hdmi_raw_prores_breathing_and_mishoe_clock()
        dt = time.perf_counter() - t0
        self.assertTrue(rep.all_checks_passed, rep.errors)
        self.assertIn(rep.mode, ("LOCAL_DONOR_VERIFIED", "CLEAN_ROOM_SYNTHETIC"))
        self.assertLess(dt, 0.35)
        if rep.mode == "LOCAL_DONOR_VERIFIED":
            self.assertGreater(rep.donor_file_sizes.get("fx3_appfw", 0), 70_000_000)
            self.assertGreater(rep.donor_file_sizes.get("fx6_appfw", 0), 45_000_000)
            self.assertGreater(rep.donor_file_sizes.get("fx3_libmpr", 0), 3_000_000)
            self.assertGreater(rep.donor_file_sizes.get("fx6_libmpr", 0), 25_000_000)
            self.assertGreater(rep.donor_file_sizes.get("fx6_hotshoe", 0), 5_000)

    def test_03_forced_clean_room_env_flag_respected(self) -> None:
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}, clear=False):
            rep = analyze_hdmi_raw_prores_breathing_and_mishoe_clock()
        self.assertTrue(rep.all_checks_passed, rep.errors)
        self.assertEqual(rep.mode, "CLEAN_ROOM_SYNTHETIC")

    def test_04_missing_donor_falls_back_to_clean_room(self) -> None:
        with mock.patch(
            "fx3_firmware_lab.hdmi_raw_prores_breathing_and_mishoe_clock_auditor.resolve_donor_file",
            return_value=None,
        ):
            rep = analyze_hdmi_raw_prores_breathing_and_mishoe_clock(clean_room=False)
        self.assertTrue(rep.all_checks_passed, rep.errors)
        self.assertEqual(rep.mode, "CLEAN_ROOM_SYNTHETIC")

    def test_05_json_serialization_has_no_bytes_repr(self) -> None:
        rep = analyze_hdmi_raw_prores_breathing_and_mishoe_clock(clean_room=True)
        payload = hdmi_raw_prores_breathing_and_mishoe_clock_report_to_dict(rep)
        json_str = json.dumps(payload, sort_keys=True)
        self.assertIsNone(_BYTES_REPR_RE.search(json_str), "Unexpected Python bytes repr in JSON")
        self.assertIn(PHASE_114_SCHEMA, json_str)

    def test_06_auditor_source_strictly_uses_os_o_rdonly_and_mmap_access_read(self) -> None:
        src = _AUDITOR_PATH.read_text(encoding="utf-8")
        self.assertIn("os.O_RDONLY", src)
        self.assertIn("mmap.ACCESS_READ", src)
        for forbidden in ("os.O_WRONLY", "os.O_RDWR", "os.O_CREAT", "mmap.ACCESS_WRITE", ".write_bytes(", ".write_text("):
            self.assertNotIn(forbidden, src)

    def test_07_package_exports_and_all_include_phase114_symbols(self) -> None:
        expected_symbols = (
            "PHASE_114_SCHEMA",
            "PHASE_114_VERSION",
            "RAW16_MIN_DYNAMIC_RANGE_STOPS",
            "COLOR_MATRIX_SGAMUT3CINE",
            "EMOUNT_BREATHING_LENS_PROFILES",
            "NTSC_2997_5FRAME_CADENCE",
            "NTSC_5994_5FRAME_CADENCE",
            "IMX510_RAW16_OB_CLAMP_ADU",
            "SLOG3_10BIT_BLACK_PEDESTAL",
            "HdmiRawProresBreathingMishoeReport",
            "analyze_hdmi_raw_prores_breathing_and_mishoe_clock",
            "hdmi_raw_prores_breathing_and_mishoe_clock_report_to_dict",
            "sony_raw16_to_raw12_log",
            "sony_raw12_log_to_raw16",
            "verify_raw16_to_raw12_dynamic_range",
            "build_hdmi_raw_metadata_packet",
            "decode_hdmi_raw_metadata_packet",
            "evaluate_hdmi_raw_metadata_handshake",
            "compute_breathing_fov_crop_factor",
            "evaluate_focus_breathing_guard",
            "evaluate_mishoe_i2s_clock_pll",
            "evaluate_ob_clamp_write_guard",
        )
        for sym in expected_symbols:
            self.assertTrue(hasattr(lab, sym), f"Missing package export: {sym}")
            self.assertIn(sym, lab.__all__, f"Missing from __all__: {sym}")

    def test_08_synthetic_fixtures_carry_all_markers_uxc_labels_and_xdb(self) -> None:
        fx = build_clean_room_prores_breathing_mishoe_fixtures()
        self.assertEqual(len(fx), 13)
        for m in FX3_APPFW_PHASE114_MARKERS:
            self.assertIn(m.encode("latin1"), fx["fx3_appfw"])
        for m in FX6_APPFW_PHASE114_MARKERS:
            self.assertIn(m.encode("latin1"), fx["fx6_appfw"])
        for m in FX3_LIBMPR_PHASE114_MARKERS:
            self.assertIn(m.encode("latin1"), fx["fx3_libmpr"])
        for m in FX6_LIBMPR_PHASE114_MARKERS:
            self.assertIn(m.encode("latin1"), fx["fx6_libmpr"])
        for m in CP_SHARED_PHASE114_MARKERS + FX3_CP_EXTRA_PHASE114_MARKERS:
            self.assertIn(m.encode("latin1"), fx["fx3_cpapp"])
        for m in CP_SHARED_PHASE114_MARKERS + FX6_CP_EXTRA_PHASE114_MARKERS:
            self.assertIn(m.encode("latin1"), fx["fx6_cpapp"])
        for m in FX6_HOTSHOE_PHASE114_MARKERS:
            self.assertIn(m.encode("latin1"), fx["fx6_hotshoe"])

        parse_global_xdb_buffer(fx["fx3_global_xdb"])
        parse_global_xdb_buffer(fx["fx6_global_xdb"])
        for pack_key, expected in (
            ("fx3_str_en", FX3_NS39_PHASE114_LABELS),
            ("fx3_str_en_g", FX3_NS3_PHASE114_LABELS),
            ("fx6_str_en_1", FX6_NS1_PHASE114_LABELS),
            ("fx6_str_en_2", FX6_NS2_PHASE114_LABELS),
        ):
            labels, errs = _extract_uxc_labels(fx[pack_key], expected)
            self.assertEqual(errs, (), f"{pack_key}: {errs}")
            self.assertEqual(len(labels), len(expected))

    # ---- Pillar 1: 16-Bit Linear -> 12-Bit Log RAW & ProRes RAW / BRAW Metadata ----

    def test_09_raw16_to_raw12_dynamic_range_continuity_and_shadow_toe_injective(self) -> None:
        proof = verify_raw16_to_raw12_dynamic_range()
        self.assertTrue(proof.passed, proof.errors)
        self.assertEqual(proof.status, "RAW16_TO_RAW12_LOG_DR_VERIFIED")
        self.assertTrue(proof.monotonic_verified)
        self.assertTrue(proof.shadow_toe_injective_0_to_512)
        self.assertGreaterEqual(proof.dynamic_range_stops_16bit, RAW16_MIN_DYNAMIC_RANGE_STOPS)
        self.assertGreaterEqual(proof.dynamic_range_stops_12bit_log, RAW16_MIN_DYNAMIC_RANGE_STOPS)
        self.assertLess(proof.c0_continuity_error, 1e-6)
        self.assertLess(proof.c1_slope_error, 1e-3)
        self.assertLess(proof.max_relative_roundtrip_error_above_64, 0.01)

    def test_10_raw16_to_raw12_piecewise_knots_and_roundtrip_landmarks(self) -> None:
        self.assertEqual(sony_raw16_to_raw12_log(0), 0)
        self.assertEqual(sony_raw16_to_raw12_log(RAW16_MAX_CODE), RAW12_MAX_CODE)
        self.assertEqual(sony_raw12_log_to_raw16(0), 0)
        self.assertEqual(sony_raw12_log_to_raw16(RAW12_MAX_CODE), RAW16_MAX_CODE)
        for c16, expected_c12 in RAW16_TO_RAW12_PIECEWISE_KNOTS:
            actual_c12 = sony_raw16_to_raw12_log(c16)
            self.assertLessEqual(abs(actual_c12 - expected_c12), 1, f"knot ({c16}, {expected_c12}) -> {actual_c12}")

    def test_11_raw16_raw12_codecs_reject_bad_types_and_bounds(self) -> None:
        for bad16 in (-1, RAW16_MAX_CODE + 1, True, 12.5, "100"):
            with self.assertRaises(ValueError):
                sony_raw16_to_raw12_log(bad16)  # type: ignore[arg-type]
        for bad12 in (-1, RAW12_MAX_CODE + 1, False, 1.5, "10"):
            with self.assertRaises(ValueError):
                sony_raw12_log_to_raw16(bad12)  # type: ignore[arg-type]

    def test_12_hdmi_raw_metadata_packet_roundtrip_and_sgamut3cine_matrix(self) -> None:
        self.assertEqual(VALID_RAW_RECORDERS, ("ATOMOS_PRORES_RAW", "BLACKMAGIC_BRAW"))
        self.assertEqual(VALID_DUAL_BASE_ISOS, (640, 800, 12800))
        for row in COLOR_MATRIX_SGAMUT3CINE:
            self.assertAlmostEqual(sum(row), 1.0, places=5)

        pkt = build_hdmi_raw_metadata_packet(
            recorder_type="ATOMOS_PRORES_RAW",
            wb_kelvin=5600,
            tint=2,
            base_iso=800,
            exposure_index=1600,
            raw_dims=RAW_HDMI_UNCROPPED_DIMS,
            crop_dims=RAW_HDMI_METADATA_CROP_DIMS,
        )
        self.assertEqual(len(pkt), RAW_META_PACKET_BYTES)
        self.assertEqual(pkt[:8], RAW_META_PACKET_MAGIC)

        dec = decode_hdmi_raw_metadata_packet(pkt)
        self.assertTrue(dec.valid, dec.errors)
        self.assertTrue(dec.crc32_valid)
        self.assertEqual(dec.recorder_type, "ATOMOS_PRORES_RAW")
        self.assertEqual(dec.wb_kelvin, 5600)
        self.assertEqual(dec.tint, 2)
        self.assertEqual(dec.base_iso, 800)
        self.assertEqual(dec.exposure_index, 1600)
        self.assertEqual((dec.raw_width, dec.raw_height), (4264, 2408))
        self.assertEqual((dec.crop_width, dec.crop_height), (4240, 2385))
        for rs in dec.color_matrix_row_sums:
            self.assertAlmostEqual(rs, 1.0, places=3)

    def test_13_prores_raw_vs_braw_nle_wb_iso_unlock_asymmetry(self) -> None:
        atomos = evaluate_hdmi_raw_metadata_handshake(
            recorder_type="ATOMOS_PRORES_RAW",
            wb_kelvin=3200,
            tint=-3,
            base_iso=12800,
            exposure_index=12800,
            fps=59.94,
        )
        self.assertTrue(atomos.valid, atomos.errors)
        self.assertTrue(atomos.wb_iso_unlocked_in_nle)
        self.assertFalse(atomos.wb_iso_locked_in_resolve_braw)

        braw = evaluate_hdmi_raw_metadata_handshake(
            recorder_type="BLACKMAGIC_BRAW",
            wb_kelvin=5600,
            tint=0,
            base_iso=800,
            exposure_index=800,
            fps=23.976,
        )
        self.assertTrue(braw.valid, braw.errors)
        self.assertFalse(braw.wb_iso_unlocked_in_nle)
        self.assertTrue(braw.wb_iso_locked_in_resolve_braw)

    def test_14_hdmi_raw_blocks_mlut_osd_log_off_sq_fps_and_crc_tamper(self) -> None:
        blk_mlut = evaluate_hdmi_raw_metadata_handshake(mlut_burn_in_enabled=True)
        self.assertFalse(blk_mlut.valid)
        self.assertEqual(blk_mlut.status, "BLOCKED_RAW_HDMI_MLUT_CONTAMINATION")

        blk_osd = evaluate_hdmi_raw_metadata_handshake(hdmi_info_display_on=True)
        self.assertFalse(blk_osd.valid)
        self.assertEqual(blk_osd.status, "BLOCKED_RAW_HDMI_OSD_CONTAMINATION")

        blk_log = evaluate_hdmi_raw_metadata_handshake(log_shooting_enabled=False)
        self.assertFalse(blk_log.valid)
        self.assertEqual(blk_log.status, "BLOCKED_RAW_REQUIRES_LOG_SHOOTING")

        blk_sq = evaluate_hdmi_raw_metadata_handshake(sq_motion_active=True)
        self.assertFalse(blk_sq.valid)
        self.assertEqual(blk_sq.status, "BLOCKED_RAW_HDMI_SQ_EXCLUSION")

        blk_fps = evaluate_hdmi_raw_metadata_handshake(fps=119.88)
        self.assertFalse(blk_fps.valid)
        self.assertEqual(blk_fps.status, "BLOCKED_RAW_UNSUPPORTED_FPS")

        blk_crc = evaluate_hdmi_raw_metadata_handshake(corrupt_crc=True)
        self.assertFalse(blk_crc.valid)
        self.assertEqual(blk_crc.status, "BLOCKED_RAW_METADATA_CHECKSUM_MISMATCH")

    def test_15_metadata_packet_builder_and_decoder_reject_invalid_inputs(self) -> None:
        with self.assertRaises(ValueError):
            build_hdmi_raw_metadata_packet(recorder_type="RED_R3D")
        with self.assertRaises(ValueError):
            build_hdmi_raw_metadata_packet(wb_kelvin=1500)
        with self.assertRaises(ValueError):
            build_hdmi_raw_metadata_packet(tint=120)
        with self.assertRaises(ValueError):
            build_hdmi_raw_metadata_packet(base_iso=3200)
        with self.assertRaises(ValueError):
            build_hdmi_raw_metadata_packet(exposure_index=50)
        with self.assertRaises(ValueError):
            build_hdmi_raw_metadata_packet(color_matrix=((1.0, 0.0), (0.0, 1.0)))

        short_dec = decode_hdmi_raw_metadata_packet(b"SONYRAW1")
        self.assertFalse(short_dec.valid)

        bad_magic = bytearray(build_hdmi_raw_metadata_packet())
        bad_magic[:8] = b"BADMAGIC"
        bad_dec = decode_hdmi_raw_metadata_packet(bytes(bad_magic))
        self.assertFalse(bad_dec.valid)
        self.assertFalse(bad_dec.crc32_valid)

    # ---- Pillar 2: Focus-Breathing Dynamic FOV Crop & Exclusion Guards ----

    def test_16_breathing_fov_crop_polynomial_monotonic_within_1000_to_1125(self) -> None:
        for lens_id, spec in EMOUNT_BREATHING_LENS_PROFILES.items():
            c_mod = compute_breathing_fov_crop_factor(lens_id, spec["min_focus_mm"])
            c_mid = compute_breathing_fov_crop_factor(lens_id, spec["min_focus_mm"] * 3.0)
            c_inf = compute_breathing_fov_crop_factor(lens_id, 10_000_000.0)
            self.assertGreaterEqual(c_mod, BREATHING_CROP_MIN)
            self.assertLessEqual(c_mod, BREATHING_CROP_MAX)
            self.assertGreater(c_mod, c_mid)
            self.assertGreater(c_mid, c_inf)
            self.assertAlmostEqual(c_inf, 1.0, places=4)

    def test_17_breathing_crop_rejects_unknown_lens_or_nonpositive_focus(self) -> None:
        with self.assertRaises(ValueError):
            compute_breathing_fov_crop_factor("UNKNOWN_LENS", 500.0)
        for bad_u in (0.0, -100.0, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                compute_breathing_fov_crop_factor("SEL50F12GM", bad_u)

    def test_18_breathing_guard_applies_crop_in_normal_xavc_mode(self) -> None:
        ev = evaluate_focus_breathing_guard(
            lens_id="SEL50F12GM",
            focus_distance_mm=400.0,
            breathing_comp_requested=True,
        )
        self.assertTrue(ev.valid, ev.errors)
        self.assertEqual(ev.status, "BREATHING_COMP_ACTIVE_FOV_CROP_APPLIED")
        self.assertTrue(ev.breathing_comp_active)
        self.assertFalse(ev.isp_geometric_resampler_bypassed)
        self.assertAlmostEqual(ev.applied_crop_factor, 1.105, places=4)

        ev_off = evaluate_focus_breathing_guard(
            lens_id="SEL50F12GM",
            focus_distance_mm=400.0,
            breathing_comp_requested=False,
        )
        self.assertTrue(ev_off.valid)
        self.assertEqual(ev_off.status, "BREATHING_COMP_OFF_IDENTITY")
        self.assertEqual(ev_off.applied_crop_factor, 1.000)

    def test_19_breathing_guard_auto_bypasses_for_hdmi_raw_and_sq_120p(self) -> None:
        raw_bypass = evaluate_focus_breathing_guard(
            lens_id="SEL50F12GM", focus_distance_mm=400.0, hdmi_raw_enabled=True
        )
        self.assertTrue(raw_bypass.valid, raw_bypass.errors)
        self.assertEqual(raw_bypass.status, "BYPASSED_FOR_HDMI_RAW_BAYER_STREAM")
        self.assertFalse(raw_bypass.breathing_comp_active)
        self.assertTrue(raw_bypass.isp_geometric_resampler_bypassed)
        self.assertEqual(raw_bypass.applied_crop_factor, 1.000)

        sq_bypass = evaluate_focus_breathing_guard(
            lens_id="SEL70200GM2", focus_distance_mm=400.0, sq_120p_active=True
        )
        self.assertTrue(sq_bypass.valid, sq_bypass.errors)
        self.assertEqual(sq_bypass.status, "BYPASSED_FOR_HFR_SQ_120P")
        self.assertFalse(sq_bypass.breathing_comp_active)
        self.assertTrue(sq_bypass.isp_geometric_resampler_bypassed)
        self.assertEqual(sq_bypass.applied_crop_factor, 1.000)

    def test_20_breathing_guard_bypasses_manual_lens_teleconverter_and_macro_ring(self) -> None:
        manual = evaluate_focus_breathing_guard(
            lens_id="COOKE_ANAMORPHIC_50MM", focus_distance_mm=800.0, unchipped_manual_lens=True
        )
        self.assertTrue(manual.valid)
        self.assertEqual(manual.status, "BYPASSED_UNSUPPORTED_OR_UNCHIPPED_LENS")
        self.assertEqual(manual.applied_crop_factor, 1.000)

        tc = evaluate_focus_breathing_guard(
            lens_id="SEL70200GM2", focus_distance_mm=500.0, teleconverter_attached=True
        )
        self.assertTrue(tc.valid)
        self.assertEqual(tc.status, "BYPASSED_UNSUPPORTED_OR_UNCHIPPED_LENS")
        self.assertEqual(tc.applied_crop_factor, 1.000)

        macro = evaluate_focus_breathing_guard(
            lens_id="SEL70200GM2", focus_distance_mm=600.0, macro_ring_057_100=True
        )
        self.assertTrue(macro.valid)
        self.assertEqual(macro.status, "BYPASSED_UNSUPPORTED_OR_UNCHIPPED_LENS")
        self.assertEqual(macro.applied_crop_factor, 1.000)

    def test_21_breathing_guard_blocks_forced_isp_crop_on_hdmi_raw(self) -> None:
        blk = evaluate_focus_breathing_guard(
            lens_id="SEL50F12GM",
            focus_distance_mm=400.0,
            hdmi_raw_enabled=True,
            force_isp_crop_on_raw=True,
        )
        self.assertFalse(blk.valid)
        self.assertEqual(blk.status, "BLOCKED_BREATHING_CROP_ON_HDMI_RAW_ILLEGAL")
        self.assertFalse(blk.isp_geometric_resampler_bypassed)
        self.assertGreater(blk.applied_crop_factor, 1.0)

        bad_u = evaluate_focus_breathing_guard(lens_id="SEL50F12GM", focus_distance_mm=-5.0)
        self.assertFalse(bad_u.valid)
        self.assertEqual(bad_u.status, "BLOCKED_INVALID_FOCUS_DISTANCE")

    # ---- Pillar 3: MI-Shoe 48.000 kHz I2S Master-Clock PLL & Long-Take Drift ----

    def test_22_mishoe_ntsc_2997p_and_5994p_exact_5frame_cadences(self) -> None:
        e_2997 = evaluate_mishoe_i2s_clock_pll(frame_rate_key="29.97p")
        self.assertTrue(e_2997.valid, e_2997.errors)
        self.assertEqual(e_2997.status, "MISHOE_I2S_48KHZ_PLL_LOCKED_VERIFIED")
        self.assertTrue(e_2997.fractional_ntsc)
        self.assertEqual(e_2997.cadence_samples_per_frame, NTSC_2997_5FRAME_CADENCE)
        self.assertEqual(sum(NTSC_2997_5FRAME_CADENCE), 8008)
        self.assertAlmostEqual(e_2997.samples_per_frame_exact, 1601.6, places=4)
        self.assertEqual(e_2997.bitrate_bps, AUDIO_SAMPLE_RATE_48K * 24 * 4)
        self.assertLess(e_2997.cumulative_drift_ms_6h, MAX_ALLOWED_LIPSYNC_DRIFT_MS)
        self.assertLess(e_2997.max_cadence_phase_jitter_ms, 0.02)

        e_5994 = evaluate_mishoe_i2s_clock_pll(frame_rate_key="59.94p")
        self.assertTrue(e_5994.valid, e_5994.errors)
        self.assertEqual(e_5994.cadence_samples_per_frame, NTSC_5994_5FRAME_CADENCE)
        self.assertEqual(sum(NTSC_5994_5FRAME_CADENCE), 4004)
        self.assertAlmostEqual(e_5994.samples_per_frame_exact, 800.8, places=4)
        self.assertEqual(e_5994.cumulative_drift_ms_6h, 0.0)

    def test_23_mishoe_all_rational_framerates_zero_drift_across_6h(self) -> None:
        self.assertEqual(LONG_TAKE_DURATION_SEC, 21_600.0)
        for key, spec in FRAME_RATE_RATIONAL_SPECS.items():
            ev = evaluate_mishoe_i2s_clock_pll(frame_rate_key=key)
            self.assertTrue(ev.valid, f"{key}: {ev.errors}")
            self.assertEqual(ev.cumulative_drift_ms_6h, 0.0)
            cad = spec["cadence"]
            fps = Fraction(int(spec["num"]), int(spec["den"]))
            self.assertEqual(Fraction(sum(cad), len(cad)), Fraction(AUDIO_SAMPLE_RATE_48K) / fps)  # type: ignore[arg-type]

    def test_24_mishoe_blocks_unlocked_1000ppm_ntsc_crystal_slip(self) -> None:
        blk = evaluate_mishoe_i2s_clock_pll(
            frame_rate_key="29.97p", audio_pll_locked_to_video_crystal=False
        )
        self.assertFalse(blk.valid)
        self.assertEqual(blk.status, "BLOCKED_NTSC_FRACTIONAL_PLL_DRIFT_HAZARD")
        self.assertGreater(blk.cumulative_drift_ms_6h, 20_000.0)

    def test_25_mishoe_p11_hot_detach_fallback_and_sq_audio_mute(self) -> None:
        detach = evaluate_mishoe_i2s_clock_pll(frame_rate_key="29.97p", hot_detach_event=True)
        self.assertTrue(detach.valid, detach.errors)
        self.assertEqual(detach.status, "P11_HOT_DETACH_INTERNAL_MIC_FALLBACK_SAFE")
        self.assertTrue(detach.hot_detach_fallback_active)
        self.assertEqual(detach.channels, 2)
        self.assertEqual(detach.bitrate_bps, AUDIO_SAMPLE_RATE_48K * 24 * 2)

        sq = evaluate_mishoe_i2s_clock_pll(frame_rate_key="29.97p", sq_motion_active=True)
        self.assertTrue(sq.valid, sq.errors)
        self.assertEqual(sq.status, "SQ_AUDIO_MUTED_SHOE_DISABLED_SAFE")
        self.assertTrue(sq.sq_audio_muted)
        self.assertEqual(sq.bitrate_bps, 0)

    def test_26_mishoe_rejects_unsupported_fps_or_audio_format(self) -> None:
        with self.assertRaises(ValueError):
            evaluate_mishoe_i2s_clock_pll(frame_rate_key="14.985p")
        with self.assertRaises(ValueError):
            evaluate_mishoe_i2s_clock_pll(channels=8)
        with self.assertRaises(ValueError):
            evaluate_mishoe_i2s_clock_pll(bit_depth=32)

    # ---- Pillar 4: Factory OB-Clamp / Black-Level Pedestal Preservation ----

    def test_27_ob_clamp_constants_and_roundtrip_fidelity(self) -> None:
        self.assertEqual(IMX510_RAW16_OB_CLAMP_ADU, 2048)
        self.assertEqual(SLOG3_10BIT_BLACK_PEDESTAL, 95)
        c12 = sony_raw16_to_raw12_log(IMX510_RAW16_OB_CLAMP_ADU)
        rec16 = sony_raw12_log_to_raw16(c12)
        self.assertLessEqual(abs(rec16 - IMX510_RAW16_OB_CLAMP_ADU), 4)

    def test_28_volatile_ram_staging_allowed_for_tmp_ram_memory(self) -> None:
        for path in ("/tmp/fx3_prores_raw_meta.json", "ram://breathing_lut", "memory://mishoe_pll"):
            g = evaluate_ob_clamp_write_guard(path)
            self.assertTrue(g.valid, g.errors)
            self.assertTrue(g.volatile_ram_staged)
            self.assertFalse(g.persistent_write_blocked)
            self.assertEqual(g.ob_clamp_calibration_mutation_bytes, 0)
            self.assertEqual(g.emmc_mutation_bytes, 0)

    def test_29_blocks_all_persistent_ob_clamp_and_emmc_targets(self) -> None:
        forbidden = (
            "p2:/setting/defdet.bin",
            "p2:/setting/psd.bin",
            "p2:/setting/Backup.bin",
            "p6:/tmp/jiritsu",
            "/dev/cnflasha0",
            "/dev/nflasha2",
            "/dev/mmcblk0p1",
            "/dev/mmcblk0rpmb",
            "/tmp/../nflasha1/defdet.bin",
            "ob_clamp://imx510_black_level",
            "nvram://factory_pedestal",
        )
        for target in forbidden:
            g = evaluate_ob_clamp_write_guard(target)
            self.assertFalse(g.valid, f"Expected block for {target}")
            self.assertFalse(g.volatile_ram_staged)
            self.assertTrue(g.persistent_write_blocked)
            self.assertEqual(g.status, "BLOCKED_PERSISTENT_OB_CLAMP_OR_EMMC_WRITE")
            self.assertEqual(g.ob_clamp_calibration_mutation_bytes, 0)
            self.assertEqual(g.emmc_mutation_bytes, 0)

    def test_30_report_pillar4_proves_zero_calibration_and_emmc_mutations(self) -> None:
        rep = analyze_hdmi_raw_prores_breathing_and_mishoe_clock(clean_room=True)
        p4 = rep.pillar_4_ob_clamp_preservation
        self.assertTrue(p4.passed, p4.errors)
        self.assertTrue(p4.fx3_global_xdb_valid)
        self.assertTrue(p4.fx6_global_xdb_valid)
        self.assertEqual(p4.imx510_raw16_ob_clamp_adu, 2048)
        self.assertEqual(p4.slog3_10bit_black_pedestal, 95)
        self.assertEqual(p4.ob_clamp_calibration_mutation_bytes, 0)
        self.assertEqual(p4.emmc_mutation_bytes, 0)
        self.assertFalse(p4.persistent_emmc_writes_authorized)

    # ---- Pillar Reports Internal Cross-Checks & CLI / Unified 22-Auditor Integration ----

    def test_31_pillar1_marker_and_uxc_label_integrity(self) -> None:
        rep = analyze_hdmi_raw_prores_breathing_and_mishoe_clock(clean_room=True)
        p1 = rep.pillar_1_raw16_prores_braw
        self.assertEqual(len(p1.fx3_appfw_raw_markers), 3)
        self.assertEqual(len(p1.fx6_appfw_raw_markers), 3)
        self.assertEqual(len(p1.fx3_cp_raw_markers), 4)
        self.assertEqual(len(p1.fx6_cp_raw_markers), 4)
        self.assertEqual(p1.fx6_libmpr_raw_markers, ("muxQtProResComponentBufferConnect",))
        self.assertIn("RAW", p1.uxc_raw_labels["fx3_raw_hdmi_invalid"])
        self.assertEqual(p1.uxc_raw_labels["fx6_prores"], "ProRes")

    def test_32_pillar2_marker_and_uxc_label_integrity(self) -> None:
        rep = analyze_hdmi_raw_prores_breathing_and_mishoe_clock(clean_room=True)
        p2 = rep.pillar_2_focus_breathing_guard
        self.assertEqual(len(p2.fx3_appfw_breathing_markers), 5)
        self.assertEqual(len(p2.fx6_appfw_breathing_markers), 4)
        self.assertEqual(len(p2.fx3_libmpr_breathing_markers), 2)
        self.assertEqual(len(p2.fx6_libmpr_breathing_markers), 5)
        self.assertEqual(p2.uxc_breathing_labels["fx6_breathing_compensation"], "Breathing Compensation")
        self.assertEqual(p2.uxc_breathing_labels["fx6_breathing_comp"], "Breathing Comp.")

    def test_33_pillar3_marker_and_uxc_label_integrity(self) -> None:
        rep = analyze_hdmi_raw_prores_breathing_and_mishoe_clock(clean_room=True)
        p3 = rep.pillar_3_mishoe_48k_pll_clock
        self.assertEqual(len(p3.fx3_appfw_mishoe_markers), 4)
        self.assertEqual(len(p3.fx6_appfw_mishoe_markers), 3)
        self.assertEqual(len(p3.fx3_cp_mishoe_markers), 3)
        self.assertEqual(len(p3.fx6_cp_mishoe_markers), 3)
        self.assertEqual(len(p3.fx6_hotshoe_markers), 4)
        self.assertEqual(p3.uxc_mishoe_labels["fx6_4ch_48khz_24bit"], "4ch/48kHz/24bit")

    def test_34_cli_audit_proresraw_breathing_mishoe_clean_room_json(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cli_main(["audit-proresraw-breathing-mishoe", "--clean-room", "--json"])
        self.assertEqual(rc, 0)
        raw = buf.getvalue()
        self.assertIsNone(_BYTES_REPR_RE.search(raw))
        data = json.loads(raw)
        self.assertTrue(data["all_checks_passed"])
        self.assertEqual(data["mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(data["schema_version"], PHASE_114_SCHEMA)

    def test_35_cli_audit_proresraw_breathing_mishoe_auto_mode_json(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cli_main(["audit-proresraw-breathing-mishoe", "--json"])
        self.assertEqual(rc, 0)
        raw = buf.getvalue()
        self.assertIsNone(_BYTES_REPR_RE.search(raw))
        data = json.loads(raw)
        self.assertTrue(data["all_checks_passed"])
        self.assertIn(data["mode"], ("LOCAL_DONOR_VERIFIED", "CLEAN_ROOM_SYNTHETIC"))

    def test_36_run_audit_all_includes_all_22_auditors_and_passes(self) -> None:
        summary = run_audit_all(clean_room=True)
        self.assertTrue(summary["all_checks_passed"])
        expected_keys = {
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
            "c2pa_lens_shading_and_mc_fleet_audit",
            "hdr_hlg_bt2100_and_display_assist_audit",
            "hdmi_raw_prores_breathing_and_mishoe_clock_audit",
        }
        self.assertGreaterEqual(len(expected_keys), 22)
        self.assertTrue(expected_keys.issubset(set(summary.keys())))
        audit_keys = [k for k in summary if k.endswith("_audit")]
        self.assertGreaterEqual(len(audit_keys), 22)
        for key in expected_keys:
            self.assertTrue(summary[key]["all_checks_passed"], f"Failed auditor: {key}")

    def test_37_cli_audit_all_clean_room_json_passes_22_of_22(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cli_main(["audit-all", "--clean-room", "--json"])
        self.assertEqual(rc, 0)
        data = json.loads(buf.getvalue())
        self.assertTrue(data["all_checks_passed"])
        self.assertTrue(data["hdmi_raw_prores_breathing_and_mishoe_clock_audit"]["all_checks_passed"])

    def test_38_raw16_piecewise_monotonic_across_full_16bit_sweep(self) -> None:
        # Exhaustive monotonic sweep across all 65,536 16-bit codes
        prev = -1
        for c16 in range(RAW16_MAX_CODE + 1):
            c12 = sony_raw16_to_raw12_log(c16)
            self.assertGreaterEqual(c12, prev)
            prev = c12
        self.assertEqual(prev, RAW12_MAX_CODE)

    def test_39_raw12_log_decode_monotonic_and_bounded(self) -> None:
        prev = -1
        for c12 in range(RAW12_MAX_CODE + 1):
            c16 = sony_raw12_log_to_raw16(c12)
            self.assertGreaterEqual(c16, prev)
            self.assertLessEqual(c16, RAW16_MAX_CODE)
            prev = c16
        self.assertEqual(prev, RAW16_MAX_CODE)

    def test_40_negative_missing_marker_detection_in_pillar_evaluators(self) -> None:
        rep = analyze_hdmi_raw_prores_breathing_and_mishoe_clock(clean_room=True)
        self.assertEqual(rep.errors, ())
        bad_p1 = lab.evaluate_pillar_1_raw16_prores_braw(
            fx3_appfw_raw_markers=(),
            fx6_appfw_raw_markers=(),
            fx3_cp_raw_markers=(),
            fx6_cp_raw_markers=(),
            fx6_libmpr_raw_markers=(),
            uxc_raw_labels={},
            extra_errors=("Simulated missing marker",),
        )
        self.assertFalse(bad_p1.passed)
        self.assertIn("Simulated missing marker", bad_p1.errors)


if __name__ == "__main__":
    unittest.main()
