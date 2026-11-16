"""Phase 111 Dual-Mode Unit Tests: ITU-R BT.2100 / ARIB STD-B67 HLG
(`HLG1` / `HLG2` / `HLG3` / `HLG Live` / `HLG Natural` & `BT.2020` vs `BT.709`),
Gamma Display Assist EVF/LCD Tone-Mapping Isolation (`S-Log3 -> ITU709(800%)`,
`HLG(BT.2020) -> 709`), CTA-861.3 HDMI HDR Dynamic Range & Mastering InfoFrame
(`0x87`) Synthesizer & Checksum Guard, and `NonRealTimeMeta` SMPTE UL Parity +
Zero-Calibration-Mutation Proof.
"""

from __future__ import annotations

import io
import json
import math
import os
import re
import struct
import time
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

import fx3_firmware_lab as lab
from fx3_firmware_lab.__main__ import main as cli_main, run_audit_all
from fx3_firmware_lab.emount_af_breathing_and_ibis_auditor import _extract_uxc_labels
from fx3_firmware_lab.global_xdb_and_menu_tree_auditor import parse_global_xdb_buffer
from fx3_firmware_lab.hdr_hlg_bt2100_and_display_assist_auditor import (
    BT2020_TO_BT709_MATRIX_3X3,
    CIE_PRIMARIES_XY,
    CP_SHARED_PHASE111_MARKERS,
    CTA861_EOTF_CODES,
    CTA861_EOTF_NAMES,
    CTA861_HDR_DRM_INFOFRAME_TYPE,
    CTA861_HDR_DRM_INFOFRAME_VERSION,
    CTA861_HDR_DRM_PAYLOAD_LEN,
    CTA861_HDR_DRM_TOTAL_BYTES,
    CTA861_STATIC_METADATA_TYPE_1_ID,
    FX3_APPFW_PHASE111_MARKERS,
    FX3_NS39_PHASE111_LABELS,
    FX3_NS3_PHASE111_LABELS,
    FX6_APPFW_PHASE111_MARKERS,
    FX6_CP_EXTRA_PHASE111_MARKERS,
    FX6_LIBMPR_EXTRA_PHASE111_MARKERS,
    FX6_NS1_PHASE111_LABELS,
    FX6_NS2_PHASE111_LABELS,
    HLG_ARIB_B67_A,
    HLG_ARIB_B67_B,
    HLG_ARIB_B67_BREAKPOINT_E,
    HLG_ARIB_B67_BREAKPOINT_EP,
    HLG_ARIB_B67_C,
    LIBMPR_SHARED_PHASE111_MARKERS,
    NRTM_GAMMA_TO_SMPTE_UL,
    NRTM_PRIMARIES_TO_SMPTE_UL,
    PHASE_111_SCHEMA,
    PHASE_111_VERSION,
    SMPTE_UL_HEX_CATALOG,
    SONY_HLG_CURVE_PROFILES,
    VALID_EXTERNAL_HDR_MONITORS,
    VALID_GAMMA_DISPLAY_ASSIST_TYPES,
    analyze_hdr_hlg_bt2100_and_display_assist,
    arib_b67_hlg_inverse_oetf,
    arib_b67_hlg_oetf,
    build_clean_room_hdr_hlg_assist_fixtures,
    build_cta861_3_hdr_infoframe,
    compute_display_assist_preview_rgb,
    decode_cta861_3_hdr_infoframe,
    evaluate_gamma_display_assist_isolation,
    evaluate_hdmi_hdr_infoframe_handshake,
    evaluate_hdr_calibration_write_guard,
    evaluate_hlg_gamut_transfer_contract,
    hdr_hlg_bt2100_and_display_assist_report_to_dict,
    oetf_norm_to_10bit_code,
    parse_and_verify_hlg_nrtm_xml,
    sony_hlg_variant_oetf,
    synthesize_hlg_nrtm_xml,
    verify_arib_b67_oetf_roundtrip,
)


_BYTES_REPR_RE = re.compile(r"(?<![0-9A-Za-z_/.-])b['\"]")
_AUDITOR_PATH = (
    Path(__file__).resolve().parent.parent
    / "fx3_firmware_lab"
    / "hdr_hlg_bt2100_and_display_assist_auditor.py"
)


class TestHdrHlgBt2100AndDisplayAssist(unittest.TestCase):
    """Comprehensive dual-mode tests (>= 38) for the 21st unified auditor."""

    # ---- Mode, Runtime, Determinism & Structural Hygiene ----

    def test_01_clean_room_report_all_pillars_and_warm_runtime(self) -> None:
        t0 = time.perf_counter()
        rep = analyze_hdr_hlg_bt2100_and_display_assist(clean_room=True)
        dt_cold = time.perf_counter() - t0
        t1 = time.perf_counter()
        rep_warm = analyze_hdr_hlg_bt2100_and_display_assist(clean_room=True)
        dt_warm = time.perf_counter() - t1

        self.assertTrue(rep.all_checks_passed, rep.errors)
        self.assertEqual(rep.mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(rep.schema_version, PHASE_111_SCHEMA)
        self.assertEqual(rep.phase_version, PHASE_111_VERSION)
        self.assertTrue(rep.pillar_1_hlg_bt2100_curves.passed)
        self.assertTrue(rep.pillar_2_gamma_display_assist.passed)
        self.assertTrue(rep.pillar_3_cta861_3_hdr_infoframe.passed)
        self.assertTrue(rep.pillar_4_nrtm_smpte_ul_immutability.passed)
        self.assertEqual(rep.report_sha256, rep_warm.report_sha256)
        self.assertEqual(len(rep.report_sha256), 64)
        self.assertLess(dt_cold, 0.50 if __import__("os").environ.get("GITHUB_ACTIONS") == "true" else 0.08)
        self.assertLess(dt_warm, 0.25 if __import__("os").environ.get("GITHUB_ACTIONS") == "true" else 0.02)

    def test_02_auto_mode_or_local_donor_runtime_and_markers(self) -> None:
        t0 = time.perf_counter()
        rep = analyze_hdr_hlg_bt2100_and_display_assist()
        dt = time.perf_counter() - t0
        self.assertTrue(rep.all_checks_passed, rep.errors)
        self.assertIn(rep.mode, ("LOCAL_DONOR_VERIFIED", "CLEAN_ROOM_SYNTHETIC"))
        self.assertLess(dt, 0.35)
        if rep.mode == "LOCAL_DONOR_VERIFIED":
            self.assertGreater(rep.donor_file_sizes.get("fx3_appfw", 0), 70_000_000)
            self.assertGreater(rep.donor_file_sizes.get("fx6_appfw", 0), 45_000_000)
            self.assertGreater(rep.donor_file_sizes.get("fx3_libmpr", 0), 3_000_000)
            self.assertGreater(rep.donor_file_sizes.get("fx6_libmpr", 0), 25_000_000)
            self.assertEqual(
                len(rep.pillar_4_nrtm_smpte_ul_immutability.fx3_smpte_uls_verified),
                len(SMPTE_UL_HEX_CATALOG),
            )
            self.assertEqual(
                len(rep.pillar_4_nrtm_smpte_ul_immutability.fx6_smpte_uls_verified),
                len(SMPTE_UL_HEX_CATALOG),
            )

    def test_03_forced_clean_room_env_flag_respected(self) -> None:
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}, clear=False):
            rep = analyze_hdr_hlg_bt2100_and_display_assist()
        self.assertTrue(rep.all_checks_passed, rep.errors)
        self.assertEqual(rep.mode, "CLEAN_ROOM_SYNTHETIC")

    def test_04_missing_donor_falls_back_to_clean_room(self) -> None:
        with mock.patch(
            "fx3_firmware_lab.hdr_hlg_bt2100_and_display_assist_auditor.resolve_donor_file",
            return_value=None,
        ):
            rep = analyze_hdr_hlg_bt2100_and_display_assist(clean_room=False)
        self.assertTrue(rep.all_checks_passed, rep.errors)
        self.assertEqual(rep.mode, "CLEAN_ROOM_SYNTHETIC")

    def test_05_json_serialization_has_no_bytes_repr(self) -> None:
        rep = analyze_hdr_hlg_bt2100_and_display_assist(clean_room=True)
        payload = hdr_hlg_bt2100_and_display_assist_report_to_dict(rep)
        json_str = json.dumps(payload, sort_keys=True)
        self.assertIsNone(_BYTES_REPR_RE.search(json_str), "Unexpected Python bytes repr in JSON")
        self.assertIn(PHASE_111_SCHEMA, json_str)

    def test_06_auditor_source_strictly_uses_os_o_rdonly_and_mmap_access_read(self) -> None:
        src = _AUDITOR_PATH.read_text(encoding="utf-8")
        self.assertIn("os.O_RDONLY", src)
        self.assertIn("mmap.ACCESS_READ", src)
        for forbidden in ("os.O_WRONLY", "os.O_RDWR", "os.O_CREAT", "mmap.ACCESS_WRITE", ".write_bytes(", ".write_text("):
            self.assertNotIn(forbidden, src)

    def test_07_package_exports_and_all_include_phase111_symbols(self) -> None:
        expected_symbols = (
            "PHASE_111_SCHEMA",
            "PHASE_111_VERSION",
            "SONY_HLG_CURVE_PROFILES",
            "CTA861_EOTF_CODES",
            "SMPTE_UL_HEX_CATALOG",
            "HdrHlgBt2100AndDisplayAssistReport",
            "analyze_hdr_hlg_bt2100_and_display_assist",
            "hdr_hlg_bt2100_and_display_assist_report_to_dict",
            "arib_b67_hlg_oetf",
            "arib_b67_hlg_inverse_oetf",
            "sony_hlg_variant_oetf",
            "evaluate_hlg_gamut_transfer_contract",
            "evaluate_gamma_display_assist_isolation",
            "build_cta861_3_hdr_infoframe",
            "decode_cta861_3_hdr_infoframe",
            "evaluate_hdmi_hdr_infoframe_handshake",
            "synthesize_hlg_nrtm_xml",
            "parse_and_verify_hlg_nrtm_xml",
            "evaluate_hdr_calibration_write_guard",
        )
        for sym in expected_symbols:
            self.assertTrue(hasattr(lab, sym), f"Missing package export: {sym}")
            self.assertIn(sym, lab.__all__, f"Missing from __all__: {sym}")

    def test_08_synthetic_fixtures_carry_all_markers_uxc_labels_and_xdb(self) -> None:
        fx = build_clean_room_hdr_hlg_assist_fixtures()
        self.assertEqual(len(fx), 12)
        for m in FX3_APPFW_PHASE111_MARKERS:
            self.assertIn(m.encode("latin1"), fx["fx3_appfw"])
        for m in FX6_APPFW_PHASE111_MARKERS:
            self.assertIn(m.encode("latin1"), fx["fx6_appfw"])
        for m in LIBMPR_SHARED_PHASE111_MARKERS:
            self.assertIn(m.encode("latin1"), fx["fx3_libmpr"])
            self.assertIn(m.encode("latin1"), fx["fx6_libmpr"])
        for m in FX6_LIBMPR_EXTRA_PHASE111_MARKERS:
            self.assertIn(m.encode("latin1"), fx["fx6_libmpr"])
        for ul_hex in SMPTE_UL_HEX_CATALOG.values():
            self.assertIn(bytes.fromhex(ul_hex), fx["fx3_libmpr"])
            self.assertIn(bytes.fromhex(ul_hex), fx["fx6_libmpr"])
        for m in CP_SHARED_PHASE111_MARKERS:
            self.assertIn(m.encode("latin1"), fx["fx3_cpapp"])
            self.assertIn(m.encode("latin1"), fx["fx6_cpapp"])
        for m in FX6_CP_EXTRA_PHASE111_MARKERS:
            self.assertIn(m.encode("latin1"), fx["fx6_cpapp"])

        parse_global_xdb_buffer(fx["fx3_global_xdb"])
        parse_global_xdb_buffer(fx["fx6_global_xdb"])
        for pack_key, expected in (
            ("fx3_str_en", FX3_NS39_PHASE111_LABELS),
            ("fx3_str_en_g", FX3_NS3_PHASE111_LABELS),
            ("fx6_str_en_1", FX6_NS1_PHASE111_LABELS),
            ("fx6_str_en_2", FX6_NS2_PHASE111_LABELS),
        ):
            labels, errs = _extract_uxc_labels(fx[pack_key], expected)
            self.assertEqual(errs, (), f"{pack_key}: {errs}")
            self.assertEqual(len(labels), len(expected))

    # ---- Pillar 1: ITU-R BT.2100 / ARIB STD-B67 HLG & Sony Variants ----

    def test_09_arib_b67_piecewise_continuity_slope_and_roundtrip(self) -> None:
        proof = verify_arib_b67_oetf_roundtrip()
        self.assertTrue(proof.passed, proof.errors)
        self.assertEqual(proof.status, "ARIB_B67_HLG_OETF_VERIFIED")
        self.assertTrue(proof.monotonic_verified)
        self.assertLess(proof.c0_continuity_error, 1e-6)
        self.assertAlmostEqual(proof.c1_slope_left, 3.0, places=6)
        self.assertLess(proof.c1_slope_error, 1e-5)
        self.assertLess(proof.max_roundtrip_error, 1e-10)
        self.assertEqual(proof.code10_legal_black, 64)
        self.assertEqual(proof.code10_legal_breakpoint, 502)
        self.assertEqual(proof.code10_legal_peak, 940)

    def test_10_arib_b67_oetf_exact_landmarks_and_nan_rejection(self) -> None:
        self.assertEqual(arib_b67_hlg_oetf(0.0), 0.0)
        self.assertAlmostEqual(arib_b67_hlg_oetf(HLG_ARIB_B67_BREAKPOINT_E), HLG_ARIB_B67_BREAKPOINT_EP, places=10)
        self.assertAlmostEqual(arib_b67_hlg_oetf(1.0), 1.0, places=6)
        self.assertAlmostEqual(
            arib_b67_hlg_oetf(0.5),
            HLG_ARIB_B67_A * math.log(12.0 * 0.5 - HLG_ARIB_B67_B) + HLG_ARIB_B67_C,
            places=12,
        )
        for bad in (float("nan"), float("inf"), float("-inf")):
            with self.assertRaises(ValueError):
                arib_b67_hlg_oetf(bad)
            with self.assertRaises(ValueError):
                arib_b67_hlg_inverse_oetf(bad)

    def test_11_sony_hlg1_hlg2_hlg3_and_fx6_live_natural_profiles(self) -> None:
        self.assertAlmostEqual(sony_hlg_variant_oetf(1.0, "HLG1") * 100.0, 87.0, places=4)
        self.assertAlmostEqual(sony_hlg_variant_oetf(1.0, "HLG2") * 100.0, 95.0, places=4)
        self.assertAlmostEqual(sony_hlg_variant_oetf(1.0, "HLG3") * 100.0, 100.0, places=4)
        self.assertAlmostEqual(sony_hlg_variant_oetf(1.0, "HLG_LIVE") * 100.0, 100.0, places=4)
        self.assertAlmostEqual(sony_hlg_variant_oetf(1.0, "HLG_NATURAL") * 100.0, 100.0, places=4)
        self.assertAlmostEqual(sony_hlg_variant_oetf(1.0, "HLG_MILD") * 100.0, 100.0, places=4)
        self.assertEqual(SONY_HLG_CURVE_PROFILES["HLG1"]["dynamic_range_stops"], 11.5)
        self.assertEqual(SONY_HLG_CURVE_PROFILES["HLG2"]["dynamic_range_stops"], 12.3)
        self.assertEqual(SONY_HLG_CURVE_PROFILES["HLG3"]["dynamic_range_stops"], 13.0)
        self.assertEqual(oetf_norm_to_10bit_code(1.0, full_range=True), 1023)
        with self.assertRaises(ValueError):
            sony_hlg_variant_oetf(0.5, "HLG99")

    def test_12_hlg_bt2020_valid_variants_pass_gamut_transfer_contract(self) -> None:
        for var in ("HLG", "HLG1", "HLG2", "HLG3", "HLG_LIVE", "HLG_NATURAL", "HLG_MILD"):
            ev = evaluate_hlg_gamut_transfer_contract(
                hlg_variant=var,
                transfer_family="REC2100_HLG",
                recorded_primaries="BT.2020",
                signaled_primaries="BT.2020",
                target_display="HDR_HLG",
            )
            self.assertTrue(ev.valid, f"{var}: {ev.errors}")
            self.assertEqual(ev.status, "HLG_GAMUT_TRANSFER_VERIFIED")
            self.assertFalse(ev.hue_shift_risk)
            self.assertEqual(ev.saturation_collapse_pct, 0.0)

    def test_13_blocks_bt2020_recorded_tagged_as_bt709_without_matrix(self) -> None:
        ev = evaluate_hlg_gamut_transfer_contract(
            hlg_variant="HLG3",
            transfer_family="REC2100_HLG",
            recorded_primaries="BT.2020",
            signaled_primaries="BT.709",
            matrix_conversion_applied=False,
        )
        self.assertFalse(ev.valid)
        self.assertEqual(ev.status, "BLOCKED_BT2020_TAGGED_AS_BT709_WITHOUT_MATRIX")
        self.assertTrue(ev.hue_shift_risk)
        self.assertGreater(ev.saturation_collapse_pct, 40.0)
        self.assertLess(ev.gamut_area_ratio_vs_bt2020, 0.60)

    def test_14_allows_bt2020_to_bt709_only_when_matrix_conversion_applied(self) -> None:
        ev = evaluate_hlg_gamut_transfer_contract(
            hlg_variant="HLG3",
            transfer_family="REC2100_HLG",
            recorded_primaries="BT.2020",
            signaled_primaries="BT.709",
            matrix_conversion_applied=True,
            target_display="HDR_HLG",
        )
        self.assertTrue(ev.valid, ev.errors)
        self.assertFalse(ev.hue_shift_risk)

    def test_15_blocks_bt709_tagged_bt2020_slog3_mismatch_and_raw_sdr_target(self) -> None:
        b1 = evaluate_hlg_gamut_transfer_contract(
            hlg_variant="HLG3",
            recorded_primaries="BT.709",
            signaled_primaries="BT.2020",
            matrix_conversion_applied=False,
        )
        self.assertFalse(b1.valid)
        self.assertEqual(b1.status, "BLOCKED_BT709_TAGGED_AS_BT2020_OVER_SATURATION")
        self.assertTrue(b1.hue_shift_risk)

        b2 = evaluate_hlg_gamut_transfer_contract(
            hlg_variant="HLG3",
            transfer_family="S_LOG3",
            recorded_primaries="BT.2020",
            signaled_primaries="BT.2020",
        )
        self.assertFalse(b2.valid)
        self.assertEqual(b2.status, "BLOCKED_TRANSFER_METADATA_MISMATCH")

        b3 = evaluate_hlg_gamut_transfer_contract(
            hlg_variant="HLG3",
            recorded_primaries="BT.2020",
            signaled_primaries="BT.2020",
            target_display="SDR_BT_709",
            matrix_conversion_applied=False,
        )
        self.assertFalse(b3.valid)
        self.assertEqual(b3.status, "BLOCKED_SDR_TARGET_HLG_BT2020_MISMATCH")

    # ---- Pillar 2: Gamma Display Assist EVF/LCD Isolation ----

    def test_16_bt2087_linear_matrix_rows_sum_to_unity(self) -> None:
        for row in BT2020_TO_BT709_MATRIX_3X3:
            self.assertAlmostEqual(sum(row), 1.0, places=9)
        neutral = compute_display_assist_preview_rgb((0.5, 0.5, 0.5), assist_mode="HLG_BT2020_TO_709")
        self.assertAlmostEqual(neutral[0], neutral[1], places=5)
        self.assertAlmostEqual(neutral[1], neutral[2], places=5)

    def test_17_gamma_display_assist_auto_resolves_slog3_slog2_and_hlg_modes(self) -> None:
        s3 = evaluate_gamma_display_assist_isolation(
            assist_display_on=True,
            assist_type="AUTO",
            capture_gamma="S_LOG3",
            capture_primaries="S-GAMUT3.CINE",
        )
        self.assertTrue(s3.valid, s3.errors)
        self.assertEqual(s3.resolved_transform, "SLOG3_TO_709_800")
        self.assertTrue(s3.lcd_evf_receives_tone_mapped_preview)
        self.assertTrue(s3.xavc_main_preserves_native_gamma)
        self.assertTrue(s3.clean_hdmi_preserves_native_gamma)

        s2 = evaluate_gamma_display_assist_isolation(
            assist_display_on=True,
            assist_type="AUTO",
            capture_gamma="S_LOG2",
            capture_primaries="S-GAMUT",
        )
        self.assertTrue(s2.valid)
        self.assertEqual(s2.resolved_transform, "SLOG2_TO_709_800")

        h2020 = evaluate_gamma_display_assist_isolation(
            assist_display_on=True,
            assist_type="AUTO",
            capture_gamma="REC2100_HLG",
            capture_primaries="BT.2020",
        )
        self.assertTrue(h2020.valid)
        self.assertEqual(h2020.resolved_transform, "HLG_BT2020_TO_709")

        h709 = evaluate_gamma_display_assist_isolation(
            assist_display_on=True,
            assist_type="AUTO",
            capture_gamma="REC2100_HLG",
            capture_primaries="BT.709",
        )
        self.assertTrue(h709.valid)
        self.assertEqual(h709.resolved_transform, "HLG_709_TO_709")

    def test_18_gamma_display_assist_off_and_explicit_modes(self) -> None:
        self.assertEqual(len(VALID_GAMMA_DISPLAY_ASSIST_TYPES), 6)
        off_res = evaluate_gamma_display_assist_isolation(
            assist_display_on=False,
            assist_type="SLOG3_TO_709_800",
            capture_gamma="S_LOG3",
        )
        self.assertTrue(off_res.valid)
        self.assertEqual(off_res.resolved_transform, "BYPASS_OFF")
        self.assertFalse(off_res.lcd_evf_receives_tone_mapped_preview)
        self.assertEqual(off_res.sample_midgrey_evf_rgb, off_res.sample_midgrey_in_rgb)

    def test_19_mlut_active_defers_gamma_display_assist_no_double_tonemap(self) -> None:
        ev = evaluate_gamma_display_assist_isolation(
            assist_display_on=True,
            assist_type="AUTO",
            capture_gamma="S_LOG3",
            capture_primaries="S-GAMUT3.CINE",
            lcd_evf_mlut_active=True,
        )
        self.assertTrue(ev.valid, ev.errors)
        self.assertEqual(ev.status, "DISPLAY_ASSIST_DEFERRED_TO_MLUT")
        self.assertEqual(ev.resolved_transform, "DEFERRED_TO_ACTIVE_MLUT")
        self.assertTrue(ev.double_tone_map_prevented)
        self.assertFalse(ev.lcd_evf_assist_burned_into_xavc)
        self.assertFalse(ev.lcd_evf_assist_burned_into_clean_hdmi)

    def test_20_blocks_display_assist_leak_into_xavc_main_or_clean_hdmi(self) -> None:
        leak_xavc = evaluate_gamma_display_assist_isolation(
            assist_display_on=True,
            assist_type="SLOG3_TO_709_800",
            capture_gamma="S_LOG3",
            xavc_main_mlut_burn_in=False,
            lcd_evf_assist_leaked_to_xavc=True,
        )
        self.assertFalse(leak_xavc.valid)
        self.assertEqual(leak_xavc.status, "BLOCKED_DISPLAY_ASSIST_BURN_IN_LEAK_XAVC")
        self.assertTrue(leak_xavc.lcd_evf_assist_burned_into_xavc)
        self.assertFalse(leak_xavc.xavc_main_preserves_native_gamma)

        leak_hdmi = evaluate_gamma_display_assist_isolation(
            assist_display_on=True,
            assist_type="HLG_BT2020_TO_709",
            capture_gamma="REC2100_HLG",
            clean_hdmi_mlut_enabled=False,
            lcd_evf_assist_leaked_to_clean_hdmi=True,
        )
        self.assertFalse(leak_hdmi.valid)
        self.assertEqual(leak_hdmi.status, "BLOCKED_DISPLAY_ASSIST_BURN_IN_LEAK_HDMI")
        self.assertTrue(leak_hdmi.lcd_evf_assist_burned_into_clean_hdmi)
        self.assertFalse(leak_hdmi.clean_hdmi_preserves_native_gamma)

    def test_21_explicit_mlut_burn_in_opt_in_is_distinguished_from_assist_leak(self) -> None:
        ev = evaluate_gamma_display_assist_isolation(
            assist_display_on=True,
            assist_type="SLOG3_TO_709_800",
            capture_gamma="S_LOG3",
            xavc_main_mlut_burn_in=True,
            clean_hdmi_mlut_enabled=True,
        )
        self.assertTrue(ev.valid, ev.errors)
        self.assertFalse(ev.lcd_evf_assist_burned_into_xavc)
        self.assertFalse(ev.lcd_evf_assist_burned_into_clean_hdmi)
        self.assertFalse(ev.xavc_main_preserves_native_gamma)
        self.assertFalse(ev.clean_hdmi_preserves_native_gamma)

    def test_22_compute_display_assist_preview_rejects_unknown_mode(self) -> None:
        with self.assertRaises(ValueError):
            compute_display_assist_preview_rgb((0.5, 0.5, 0.5), assist_mode="INVALID_MODE")

    # ---- Pillar 3: CTA-861.3 HDMI HDR InfoFrame 0x87 ----

    def test_23_build_and_decode_30byte_cta861_3_hlg_infoframe(self) -> None:
        pkt = build_cta861_3_hdr_infoframe(
            eotf_code=CTA861_EOTF_CODES["BT2100_HLG"],
            primaries_set="BT.2020",
            max_display_mastering_luminance_nits=1000,
            min_display_mastering_luminance_0001_nits=50,
            max_cll_nits=1000,
            max_fall_nits=400,
        )
        self.assertEqual(len(pkt), CTA861_HDR_DRM_TOTAL_BYTES)
        self.assertEqual(pkt[0], CTA861_HDR_DRM_INFOFRAME_TYPE)
        self.assertEqual(pkt[1], CTA861_HDR_DRM_INFOFRAME_VERSION)
        self.assertEqual(pkt[2], CTA861_HDR_DRM_PAYLOAD_LEN)
        self.assertEqual(sum(pkt) & 0xFF, 0)

        dec = decode_cta861_3_hdr_infoframe(pkt)
        self.assertTrue(dec.valid, dec.errors)
        self.assertTrue(dec.checksum_valid)
        self.assertEqual(dec.eotf_code, 0x03)
        self.assertEqual(dec.eotf_name, "BT2100_HLG")
        self.assertEqual(dec.static_metadata_descriptor_id, CTA861_STATIC_METADATA_TYPE_1_ID)
        # Verify CTA-861.3 G, B, R, W 0.00002 scaling for BT.2020
        self.assertEqual(dec.primaries_xy_50k[0], (8500, 39850))  # G(0.170, 0.797) * 50000
        self.assertEqual(dec.primaries_xy_50k[1], (6550, 2300))   # B(0.131, 0.046) * 50000
        self.assertEqual(dec.primaries_xy_50k[2], (35400, 14600)) # R(0.708, 0.292) * 50000
        self.assertEqual(dec.white_point_xy_50k, (15635, 16450))  # D65(0.3127, 0.3290) * 50000
        self.assertEqual(dec.max_display_mastering_luminance_nits, 1000)
        self.assertEqual(dec.min_display_mastering_luminance_0001_nits, 50)
        self.assertEqual(dec.max_cll_nits, 1000)
        self.assertEqual(dec.max_fall_nits, 400)

    def test_24_cta861_3_supports_sdr_pq_and_hlg_eotf_codes(self) -> None:
        self.assertEqual(CTA861_EOTF_NAMES[0x00], "SDR_GAMMA")
        self.assertEqual(CTA861_EOTF_NAMES[0x02], "SMPTE_ST2084_PQ")
        self.assertEqual(CTA861_EOTF_NAMES[0x03], "BT2100_HLG")
        for name, code in (("SDR_GAMMA", 0x00), ("SMPTE_ST2084_PQ", 0x02), ("BT2100_HLG", 0x03)):
            pkt = build_cta861_3_hdr_infoframe(eotf_code=code, primaries_set="BT.2020")
            dec = decode_cta861_3_hdr_infoframe(pkt)
            self.assertTrue(dec.valid, dec.errors)
            self.assertEqual(dec.eotf_name, name)

    def test_25_external_hdr_monitors_auto_switch_into_hlg_bt2020_mode(self) -> None:
        for mon in VALID_EXTERNAL_HDR_MONITORS:
            ev = evaluate_hdmi_hdr_infoframe_handshake(
                camera_gamma="REC2100_HLG",
                camera_primaries="BT.2020",
                avi_colorimetry="BT2020_NCL",
                target_monitor=mon,
            )
            self.assertTrue(ev.valid, f"{mon}: {ev.errors}")
            self.assertEqual(ev.monitor_detected_mode, "HLG_BT2020_HDR")
            self.assertTrue(ev.monitor_auto_switched_hlg_bt2020)
            self.assertEqual(ev.decoded_infoframe.eotf_code, 0x03)

    def test_26_blocks_corrupt_checksum_wrong_length_or_bad_header(self) -> None:
        ev = evaluate_hdmi_hdr_infoframe_handshake(
            camera_gamma="REC2100_HLG",
            camera_primaries="BT.2020",
            avi_colorimetry="BT2020_NCL",
            corrupt_checksum=True,
        )
        self.assertFalse(ev.valid)
        self.assertEqual(ev.status, "BLOCKED_INFOFRAME_CHECKSUM_MISMATCH")
        self.assertFalse(ev.decoded_infoframe.checksum_valid)
        self.assertFalse(ev.monitor_auto_switched_hlg_bt2020)

        short_dec = decode_cta861_3_hdr_infoframe(b"\x87\x01\x1a\x00")
        self.assertFalse(short_dec.valid)

        bad_type = bytearray(build_cta861_3_hdr_infoframe())
        bad_type[0] = 0x82  # AVI type instead of 0x87 HDR DRM
        bad_type[3] = (256 - ((sum(bad_type[:3]) + sum(bad_type[4:])) & 0xFF)) & 0xFF
        dec_bad_type = decode_cta861_3_hdr_infoframe(bytes(bad_type))
        self.assertFalse(dec_bad_type.valid)

    def test_27_blocks_hlg_signaled_as_sdr_eotf_bt709_avi_or_raw16(self) -> None:
        b_sdr_eotf = evaluate_hdmi_hdr_infoframe_handshake(
            camera_gamma="REC2100_HLG",
            camera_primaries="BT.2020",
            avi_colorimetry="BT2020_NCL",
            eotf_code_override=CTA861_EOTF_CODES["SDR_GAMMA"],
        )
        self.assertFalse(b_sdr_eotf.valid)
        self.assertEqual(b_sdr_eotf.status, "BLOCKED_EOTF_TRANSFER_MISMATCH")

        b_avi = evaluate_hdmi_hdr_infoframe_handshake(
            camera_gamma="REC2100_HLG",
            camera_primaries="BT.2020",
            avi_colorimetry="BT709",
        )
        self.assertFalse(b_avi.valid)
        self.assertEqual(b_avi.status, "BLOCKED_HLG_AVI_COLORIMETRY_MISMATCH")

        b_raw16 = evaluate_hdmi_hdr_infoframe_handshake(
            camera_gamma="REC2100_HLG",
            camera_primaries="BT.2020",
            avi_colorimetry="BT2020_NCL",
            hdmi_raw16_active=True,
        )
        self.assertFalse(b_raw16.valid)
        self.assertEqual(b_raw16.status, "BLOCKED_RAW16_HDR_INFOFRAME_CONFLICT")

    # ---- Pillar 4: NonRealTimeMeta SMPTE UL Parity & Zero Mutation ----

    def test_28_smpte_ul_catalog_lengths_and_nrtm_roundtrip_parity(self) -> None:
        self.assertEqual(len(SMPTE_UL_HEX_CATALOG), 8)
        for name, ul_hex in SMPTE_UL_HEX_CATALOG.items():
            self.assertEqual(len(bytes.fromhex(ul_hex)), 16, f"{name} UL != 16 bytes")

        xml_str = synthesize_hlg_nrtm_xml(
            capture_gamma_equation="rec2100-hlg",
            capture_color_primaries="rec2020",
            hlg_variant="HLG3",
            device_model_name="ILME-FX3",
        )
        res = parse_and_verify_hlg_nrtm_xml(xml_str)
        self.assertTrue(res.valid, res.errors)
        self.assertTrue(res.smpte_ul_parity_ok)
        self.assertEqual(res.smpte_ul_gamma_hex, NRTM_GAMMA_TO_SMPTE_UL["rec2100-hlg"])
        self.assertEqual(res.smpte_ul_primaries_hex, NRTM_PRIMARIES_TO_SMPTE_UL["rec2020"])
        self.assertEqual(res.status, "NRTM_HLG_SMPTE_UL_PARITY_VERIFIED")

    def test_29_nrtm_xml_blocks_hlg_bt709_unless_compat_and_blocks_ul_tampering(self) -> None:
        xml_709 = synthesize_hlg_nrtm_xml(
            capture_gamma_equation="rec2100-hlg",
            capture_color_primaries="rec709",
            hlg_variant="HLG2",
        )
        blk = parse_and_verify_hlg_nrtm_xml(xml_709, allow_hlg_bt709_compat=False)
        self.assertFalse(blk.valid)
        self.assertEqual(blk.status, "BLOCKED_NRTM_HLG_BT709_PRIMARIES_MISMATCH")

        ok_compat = parse_and_verify_hlg_nrtm_xml(xml_709, allow_hlg_bt709_compat=True)
        self.assertTrue(ok_compat.valid, ok_compat.errors)

        xml_tampered = synthesize_hlg_nrtm_xml(
            capture_gamma_equation="rec2100-hlg",
            capture_color_primaries="rec2020",
            smpte_ul_gamma_hex="060e2b340401010d0401010101020000",  # wrong UL
        )
        blk_ul = parse_and_verify_hlg_nrtm_xml(xml_tampered)
        self.assertFalse(blk_ul.valid)
        self.assertFalse(blk_ul.smpte_ul_parity_ok)
        self.assertEqual(blk_ul.status, "BLOCKED_SMPTE_UL_MISMATCH")

    def test_30_nrtm_xml_rejects_malformed_xml_and_unknown_device(self) -> None:
        bad_xml = parse_and_verify_hlg_nrtm_xml("<NonRealTimeMeta><unclosed")
        self.assertFalse(bad_xml.valid)
        self.assertEqual(bad_xml.status, "BLOCKED_INVALID_NRTM_XML")

        bad_dev = synthesize_hlg_nrtm_xml(device_model_name="UNKNOWN-CAM")
        res_dev = parse_and_verify_hlg_nrtm_xml(bad_dev)
        self.assertFalse(res_dev.valid)

    def test_31_volatile_ram_staging_allowed_for_tmp_and_ram(self) -> None:
        for path in ("/tmp/fx3_hlg_display_assist.bin", "ram://cta861_hdr_infoframe", "memory://nrtm"):
            g = evaluate_hdr_calibration_write_guard(path)
            self.assertTrue(g.valid, g.errors)
            self.assertTrue(g.volatile_ram_staged)
            self.assertFalse(g.persistent_write_blocked)
            self.assertEqual(g.calibration_mutation_bytes, 0)
            self.assertEqual(g.emmc_mutation_bytes, 0)

    def test_32_blocks_all_persistent_calibration_and_emmc_targets(self) -> None:
        forbidden = (
            "p2:/setting/psd.bin",
            "p2:/setting/defdet.bin",
            "p2:/setting/Backup.bin",
            "p6:/tmp/jiritsu",
            "p12:/cert",
            "/dev/cnflasha0",
            "/dev/nflasha2",
            "/dev/mmcblk0p1",
            "/tmp/../nflasha1/psd.bin",
            "nvram://product_model",
        )
        for target in forbidden:
            g = evaluate_hdr_calibration_write_guard(target)
            self.assertFalse(g.valid, f"Expected block for {target}")
            self.assertFalse(g.volatile_ram_staged)
            self.assertTrue(g.persistent_write_blocked)
            self.assertEqual(g.status, "BLOCKED_PERSISTENT_CALIBRATION_OR_EMMC_WRITE")
            self.assertEqual(g.calibration_mutation_bytes, 0)
            self.assertEqual(g.emmc_mutation_bytes, 0)

    def test_33_report_pillar4_zero_calibration_and_emmc_mutations(self) -> None:
        rep = analyze_hdr_hlg_bt2100_and_display_assist(clean_room=True)
        p4 = rep.pillar_4_nrtm_smpte_ul_immutability
        self.assertTrue(p4.passed, p4.errors)
        self.assertTrue(p4.fx3_global_xdb_valid)
        self.assertTrue(p4.fx6_global_xdb_valid)
        self.assertEqual(p4.calibration_mutation_bytes, 0)
        self.assertEqual(p4.emmc_mutation_bytes, 0)
        self.assertFalse(p4.persistent_emmc_writes_authorized)

    # ---- CLI & Unified 21-Auditor Integration ----

    def test_34_cli_audit_hdr_hlg_assist_clean_room_json(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cli_main(["audit-hdr-hlg-assist", "--clean-room", "--json"])
        self.assertEqual(rc, 0)
        raw = buf.getvalue()
        self.assertIsNone(_BYTES_REPR_RE.search(raw))
        data = json.loads(raw)
        self.assertTrue(data["all_checks_passed"])
        self.assertEqual(data["mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(data["schema_version"], PHASE_111_SCHEMA)

    def test_35_run_audit_all_includes_all_21_auditors_and_passes(self) -> None:
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
        }
        self.assertEqual(len(expected_keys), 21)
        self.assertTrue(expected_keys.issubset(set(summary.keys())))
        audit_keys = [k for k in summary if k.endswith("_audit")]
        self.assertGreaterEqual(len(audit_keys), 21)
        for key in expected_keys:
            self.assertTrue(summary[key]["all_checks_passed"], f"Failed auditor: {key}")

    def test_36_cli_audit_all_clean_room_json_passes_21_of_21(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cli_main(["audit-all", "--clean-room", "--json"])
        self.assertEqual(rc, 0)
        data = json.loads(buf.getvalue())
        self.assertTrue(data["all_checks_passed"])
        self.assertTrue(data["hdr_hlg_bt2100_and_display_assist_audit"]["all_checks_passed"])

    def test_37_cta861_3_builder_input_validation_errors(self) -> None:
        with self.assertRaises(ValueError):
            build_cta861_3_hdr_infoframe(eotf_code=0x07)
        with self.assertRaises(ValueError):
            build_cta861_3_hdr_infoframe(static_metadata_descriptor_id=1)
        with self.assertRaises(ValueError):
            build_cta861_3_hdr_infoframe(primaries_set="DCI_P3")

    def test_38_cie_primaries_bt2020_vs_bt709_chromaticity_constants(self) -> None:
        self.assertEqual(CIE_PRIMARIES_XY["BT.2020"]["R"], (0.7080, 0.2920))
        self.assertEqual(CIE_PRIMARIES_XY["BT.2020"]["G"], (0.1700, 0.7970))
        self.assertEqual(CIE_PRIMARIES_XY["BT.2020"]["B"], (0.1310, 0.0460))
        self.assertEqual(CIE_PRIMARIES_XY["BT.709"]["W"], (0.3127, 0.3290))


if __name__ == "__main__":
    unittest.main()
