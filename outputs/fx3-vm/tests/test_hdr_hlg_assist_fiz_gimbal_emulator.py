#!/usr/bin/env python3
"""Phase 112 Test Suite — Stage 19 ITU-R BT.2100 / ARIB STD-B67 HLG (HLG1/2/3 &
BT.2020 <-> BT.709), CTA-861.3 HDMI HDR 0x87 InfoFrame, EVF/LCD Gamma Display
Assist Zero-Leak Isolation, & G33/G34 Salt-Spray/Haze Duct + Wireless FIZ
Hard-Stop / Gimbal CoG Oscillation HIL.

Exercises 36 fast unit, math, fail-closed guard, Stage 19 suite integration,
CLI, and source-hygiene tests across BOTH Local Donor (`os.O_RDONLY`) and
`FX3_FX6_FORCE_CLEAN_ROOM=1` modes, strictly offline.
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import contextlib
import hashlib
import io
import json
import os
import re
import subprocess
import time
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
FX3_VM_DIR = TESTS_DIR.parent
REPO_ROOT = FX3_VM_DIR.parents[1]
if str(FX3_VM_DIR) not in sys.path:
    sys.path.insert(0, str(FX3_VM_DIR))

import fx3_vm_coemulation_suite as suite  # noqa: E402
import hdr_hlg_assist_fiz_gimbal_emulator as p112  # noqa: E402


_AUDIT_CACHE: dict = {}


def _get_clean_room_audit() -> dict:
    if "clean_room" not in _AUDIT_CACHE:
        _AUDIT_CACHE["clean_room"] = p112.run_phase112_hdr_hlg_fiz_gimbal_audit(
            force_clean_room=True
        )
    return _AUDIT_CACHE["clean_room"]


class TestPhase112DonorAuditAndRedlines(unittest.TestCase):
    """Verify O_RDONLY donor audit, clean-room fallback, and zero-mutation redlines."""

    def test_01_clean_room_donor_audit_verifies_all_10_artifacts_and_sha256(self) -> None:
        audit = p112.inspect_phase112_donors(force_clean_room=True)
        self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(audit.access_mode, "O_RDONLY")
        self.assertEqual(audit.donor_files_inspected, 0)
        self.assertTrue(audit.all_contracts_verified)
        self.assertGreaterEqual(len(audit.checked_markers), 30)
        self.assertEqual(audit.missing_markers, ())
        for key, (expected_bytes, expected_sha) in p112.PINNED_DONOR_SHA256.items():
            self.assertEqual(audit.bytes_by_artifact[key], expected_bytes)
            self.assertEqual(audit.sha256_by_artifact[key], expected_sha)

    def test_02_force_clean_room_env_disables_local_donor_paths(self) -> None:
        env = {p112.ENV_FORCE_CLEAN_ROOM: "1"}
        self.assertTrue(p112.is_forced_clean_room(env))
        paths = p112.resolve_phase112_donor_paths(env=env)
        self.assertEqual(len(paths), 10)
        for path in paths.values():
            self.assertIn(p112.CLEAN_ROOM_SENTINEL_DIRNAME, str(path))
        audit = p112.inspect_phase112_donors(env=env)
        self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_03_local_donor_o_rdonly_audit_when_present_or_clean_room(self) -> None:
        if p112.is_forced_clean_room():
            audit = p112.inspect_phase112_donors()
            self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")
            return
        paths = p112.resolve_phase112_donor_paths()
        audit = p112.inspect_phase112_donors()
        self.assertTrue(audit.all_contracts_verified)
        if all(p.is_file() for p in paths.values()):
            self.assertEqual(audit.source_mode, "LOCAL_DONOR_RDONLY")
            self.assertEqual(audit.donor_files_inspected, 10)
            for key, (expected_bytes, expected_sha) in p112.PINNED_DONOR_SHA256.items():
                self.assertEqual(audit.bytes_by_artifact[key], expected_bytes)
                self.assertEqual(audit.sha256_by_artifact[key], expected_sha)
        else:
            self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_04_missing_donor_root_falls_back_to_clean_room(self) -> None:
        env = {
            p112.ENV_MAC_WORK_ROOT: "/nonexistent_phase112_mac_work_root",
            p112.ENV_MAIN_LAB_WORK_ROOT: "/nonexistent_phase112_main_work_root",
        }
        audit = p112.inspect_phase112_donors(force_clean_room=True, env=env)
        self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(audit.donor_files_inspected, 0)
        self.assertTrue(audit.all_contracts_verified)

    def test_05_redlines_zero_mutations_zero_leakage_and_zero_damage(self) -> None:
        rep = _get_clean_room_audit()
        red = rep["redlines"]
        self.assertTrue(red["p8_cp_mutation_forbidden"])
        self.assertEqual(red["nop_count"], 0)
        self.assertEqual(red["guest_code_modification_bytes"], 0)
        self.assertEqual(red["cp_mutation_bytes"], 0)
        self.assertEqual(red["wbi_mutation_bytes"], 0)
        self.assertEqual(red["calibration_mutation_bytes"], 0)
        self.assertEqual(red["nvram_persistent_writes"], 0)
        self.assertEqual(red["bk4_persistent_nvram_writes"], 0)
        self.assertEqual(red["physical_device_writes"], 0)
        self.assertFalse(red["persistent_emmc_writes_authorized"])
        self.assertEqual(red["display_assist_burn_in_frames"], 0)
        self.assertEqual(red["xavc_clean_feed_leakage_events"], 0)
        self.assertEqual(red["fiz_gear_strip_events"], 0)
        self.assertEqual(red["ibis_coil_saturation_events"], 0)
        self.assertEqual(red["duct_salt_haze_ingestion_damage_events"], 0)
        self.assertEqual(red["donor_access_mode"], "O_RDONLY")


class TestAribStdB67HlgAndGamutMatrix(unittest.TestCase):
    """Verify ARIB STD-B67 HLG1/2/3 & FX6 HLG Live/Natural + BT.2020<->BT.709 matrix."""

    def test_06_arib_b67_oetf_breakpoint_continuity_and_inverse(self) -> None:
        self.assertAlmostEqual(p112.arib_b67_oetf(0.0), 0.0, places=12)
        self.assertAlmostEqual(p112.arib_b67_oetf(1.0 / 12.0), 0.5, places=8)
        self.assertAlmostEqual(p112.arib_b67_oetf(1.0), 1.0, places=8)
        for x in (0.0, 0.02, 1.0 / 12.0, 0.18, 0.5, 0.9, 1.0):
            ep = p112.arib_b67_oetf(x)
            x_rt = p112.arib_b67_inv_oetf(ep)
            self.assertAlmostEqual(x_rt, x, places=9)

    def test_07_hlg1_hlg2_hlg3_and_fx6_live_natural_knee_ceilings(self) -> None:
        p1 = p112.hlg_profile_oetf(1.0, p112.HLG_PROFILE_HLG1)
        p2 = p112.hlg_profile_oetf(1.0, p112.HLG_PROFILE_HLG2)
        p3 = p112.hlg_profile_oetf(1.0, p112.HLG_PROFILE_HLG3)
        pl = p112.hlg_profile_oetf(1.0, p112.HLG_PROFILE_FX6_LIVE)
        pn = p112.hlg_profile_oetf(1.0, p112.HLG_PROFILE_FX6_NATURAL)
        self.assertAlmostEqual(p1, 0.87, places=6)
        self.assertAlmostEqual(p2, 0.95, places=6)
        self.assertAlmostEqual(p3, 1.00, places=6)
        self.assertAlmostEqual(pl, 0.96, places=6)
        self.assertAlmostEqual(pn, 1.00, places=6)
        self.assertEqual(p112.encode_10bit_code_value(p1, legal_range=True), 826)
        self.assertEqual(p112.encode_10bit_code_value(p2, legal_range=True), 896)
        self.assertEqual(p112.encode_10bit_code_value(p3, legal_range=True), 940)

    def test_08_10bit_legal_and_full_code_value_roundtrip_zero_lsb_error(self) -> None:
        for pid in p112.HLG_PROFILE_SPECS:
            for e in (0.01, 0.0833333, 0.18, 0.45, 0.75, 1.0):
                sig = p112.hlg_profile_oetf(e, pid)
                for legal in (True, False):
                    cv = p112.encode_10bit_code_value(sig, legal_range=legal)
                    sig_q = p112.decode_10bit_code_value(cv, legal_range=legal)
                    e_rt = p112.hlg_profile_inv_oetf(sig_q, pid)
                    cv_rt = p112.encode_10bit_code_value(
                        p112.hlg_profile_oetf(e_rt, pid), legal_range=legal
                    )
                    self.assertEqual(cv_rt, cv, msg=f"profile={pid}, legal={legal}, e={e}")

    def test_09_bt2100_hlg_eotf_1000_nits_monotonic_and_black_zero(self) -> None:
        self.assertEqual(p112.bt2100_hlg_eotf_rgb((0.0, 0.0, 0.0)), (0.0, 0.0, 0.0))
        mid = p112.hlg_profile_oetf(0.18, p112.HLG_PROFILE_HLG3)
        hi = p112.hlg_profile_oetf(1.0, p112.HLG_PROFILE_HLG3)
        nits_mid = p112.bt2100_hlg_eotf_rgb((mid, mid, mid), peak_luminance_nits=1000.0)
        nits_hi = p112.bt2100_hlg_eotf_rgb((hi, hi, hi), peak_luminance_nits=1000.0)
        self.assertGreater(nits_mid[0], 50.0)
        self.assertLess(nits_mid[0], 250.0)
        self.assertAlmostEqual(nits_hi[0], 1000.0, places=3)

    def test_10_bt2020_bt709_gamut_matrix_preserves_d65_and_inverts_precisely(self) -> None:
        for row in p112.BT2020_TO_BT709_MATRIX:
            self.assertAlmostEqual(sum(row), 1.0, places=12)
        for row in p112.BT709_TO_BT2020_MATRIX:
            self.assertAlmostEqual(sum(row), 1.0, places=12)
        sample = (0.63, 0.41, 0.19)
        in_2020 = p112.apply_3x3_matrix(sample, p112.BT709_TO_BT2020_MATRIX)
        back_709 = p112.apply_3x3_matrix(in_2020, p112.BT2020_TO_BT709_MATRIX)
        for i in range(3):
            self.assertAlmostEqual(back_709[i], sample[i], places=12)

    def test_11_valid_bt2100_hlg_container_tags_pass(self) -> None:
        v = p112.validate_hdr_container_tags(
            profile_id=p112.HLG_PROFILE_FX6_NATURAL,
            color_primaries_cicp=p112.CICP_PRIMARIES_BT2020,
            transfer_characteristics_cicp=p112.CICP_TRANSFER_ARIB_B67_HLG,
            matrix_coefficients_cicp=p112.CICP_MATRIX_BT2020_NCL,
            container_gamut_tag="BT2020",
        )
        self.assertTrue(v.passed)
        self.assertEqual(v.violation_codes, ())

    def test_12_mismatched_bt2020_in_bt709_container_tags_rejected_fail_closed(self) -> None:
        v = p112.validate_hdr_container_tags(
            profile_id=p112.HLG_PROFILE_HLG3,
            color_primaries_cicp=p112.CICP_PRIMARIES_BT2020,
            transfer_characteristics_cicp=p112.CICP_TRANSFER_ARIB_B67_HLG,
            matrix_coefficients_cicp=p112.CICP_MATRIX_BT709,
            container_gamut_tag="BT709",
        )
        self.assertFalse(v.passed)
        self.assertIn("BLOCKED_MISMATCHED_BT2020_IN_BT709_CONTAINER", v.violation_codes)

    def test_13_invalid_cicp_transfer_or_primaries_rejected_fail_closed(self) -> None:
        v = p112.validate_hdr_container_tags(
            profile_id=p112.HLG_PROFILE_HLG2,
            color_primaries_cicp=p112.CICP_PRIMARIES_BT709,
            transfer_characteristics_cicp=p112.CICP_TRANSFER_BT709,
            matrix_coefficients_cicp=p112.CICP_MATRIX_BT709,
            container_gamut_tag="BT2020",
        )
        self.assertFalse(v.passed)
        self.assertIn("BLOCKED_MISMATCHED_BT2020_IN_BT709_CONTAINER", v.violation_codes)
        self.assertIn("BLOCKED_INVALID_BT2100_HLG_TRANSFER_TAG", v.violation_codes)

    def test_14_unknown_hlg_profile_raises_error(self) -> None:
        with self.assertRaises(p112.HdrHlgAssistFizGimbalError):
            p112.hlg_profile_oetf(0.5, "HLG99")
        with self.assertRaises(p112.HdrHlgAssistFizGimbalError):
            p112.validate_hdr_container_tags(
                profile_id="HLG99",
                color_primaries_cicp=9,
                transfer_characteristics_cicp=18,
                matrix_coefficients_cicp=9,
            )


class TestCta8613InfoFrameAndGammaAssistIsolation(unittest.TestCase):
    """Verify CTA-861.3 0x87 30B InfoFrame synthesis/validation & EVF/LCD Assist zero-leak."""

    def test_15_synthesize_30byte_cta861_3_hlg_infoframe_0x87(self) -> None:
        res = p112.synthesize_cta861_3_hdr_infoframe(eotf=p112.EOTF_HLG_BT2100)
        self.assertTrue(res.valid)
        self.assertEqual(res.infoframe_type, 0x87)
        self.assertEqual(res.infoframe_version, 0x01)
        self.assertEqual(res.payload_length, 26)
        self.assertEqual(res.packet_length, 30)
        self.assertEqual(res.checksum_sum_mod256, 0)
        self.assertEqual(res.eotf, 0x03)
        self.assertEqual(res.gamut_primaries_standard, "BT.2020")
        raw = bytes.fromhex(res.packet_hex)
        self.assertEqual(len(raw), 30)
        self.assertEqual((0x100 - (sum(raw) & 0xFF)) & 0xFF, 0)

    def test_16_synthesize_30byte_cta861_3_sdr_infoframe_0x00(self) -> None:
        res = p112.synthesize_cta861_3_hdr_infoframe(eotf=p112.EOTF_SDR_GAMMA)
        self.assertTrue(res.valid)
        self.assertEqual(res.eotf, 0x00)
        self.assertEqual(res.packet_length, 30)
        self.assertEqual(res.checksum_sum_mod256, 0)
        self.assertEqual(res.gamut_primaries_standard, "BT.709")

    def test_17_parse_and_verify_roundtrip_hlg_and_sdr_infoframes(self) -> None:
        for eotf in (p112.EOTF_HLG_BT2100, p112.EOTF_SDR_GAMMA):
            syn = p112.synthesize_cta861_3_hdr_infoframe(eotf=eotf)
            parsed = p112.parse_and_verify_cta861_3_hdr_infoframe(syn.packet_hex)
            self.assertTrue(parsed["valid"])
            self.assertEqual(parsed["eotf"], eotf)
            self.assertEqual(parsed["checksum_sum_mod256"], 0)
            self.assertEqual(parsed["packet_length"], 30)

    def test_18_corrupt_checksum_rejected_fail_closed(self) -> None:
        syn = p112.synthesize_cta861_3_hdr_infoframe(eotf=p112.EOTF_HLG_BT2100)
        bad = bytearray.fromhex(syn.packet_hex)
        bad[3] ^= 0x55
        parsed = p112.parse_and_verify_cta861_3_hdr_infoframe(bad.hex())
        self.assertFalse(parsed["valid"])
        self.assertEqual(parsed["violation_code"], "BLOCKED_INFOFRAME_CHECKSUM_MISMATCH")

    def test_19_reserved_eotf_and_bad_header_or_length_rejected_fail_closed(self) -> None:
        syn = p112.synthesize_cta861_3_hdr_infoframe(eotf=p112.EOTF_HLG_BT2100)
        bad_eotf = bytearray.fromhex(syn.packet_hex)
        bad_eotf[4] = 0x05
        bad_eotf[3] = (0x100 - ((sum(bad_eotf[:3]) + sum(bad_eotf[4:])) & 0xFF)) & 0xFF
        p_eotf = p112.parse_and_verify_cta861_3_hdr_infoframe(bad_eotf.hex())
        self.assertFalse(p_eotf["valid"])
        self.assertEqual(p_eotf["violation_code"], "BLOCKED_RESERVED_CTA861_3_EOTF")

        p_len = p112.parse_and_verify_cta861_3_hdr_infoframe(syn.packet_hex[:-4])
        self.assertFalse(p_len["valid"])
        self.assertEqual(p_len["violation_code"], "BLOCKED_INVALID_INFOFRAME_LENGTH")

        bad_hdr = bytearray.fromhex(syn.packet_hex)
        bad_hdr[0] = 0x82
        p_hdr = p112.parse_and_verify_cta861_3_hdr_infoframe(bad_hdr.hex())
        self.assertFalse(p_hdr["valid"])
        self.assertEqual(p_hdr["violation_code"], "BLOCKED_INVALID_INFOFRAME_HEADER")

    def test_20_gamma_display_assist_slog3_to_709_800pct_zero_xavc_or_hdmi_burn_in(self) -> None:
        res = p112.evaluate_gamma_display_assist_isolation(
            camera_gamma="SLOG3_SGAMUT3_CINE",
            assist_mode=p112.ASSIST_MODE_SLOG3_709_800,
        )
        self.assertTrue(res.passed)
        self.assertTrue(res.assist_applied_to_evf_lcd)
        self.assertNotEqual(res.evf_gpe0_preview_sha256, res.raw_sensor_preview_sha256)
        self.assertEqual(res.xavc_stream_sha256, res.xavc_baseline_sha256)
        self.assertEqual(res.hdmi_clean_feed_sha256, res.hdmi_baseline_sha256)
        self.assertEqual(res.xavc_assist_burn_in_bytes, 0)
        self.assertEqual(res.hdmi_clean_feed_leakage_bytes, 0)
        self.assertEqual(res.display_assist_burn_in_frames, 0)

    def test_21_gamma_display_assist_hlg_bt2020_to_709_zero_leak_with_0x03_eotf(self) -> None:
        res = p112.evaluate_gamma_display_assist_isolation(
            camera_gamma="HLG_BT2020",
            assist_mode=p112.ASSIST_MODE_HLG_BT2020_709,
        )
        self.assertTrue(res.passed)
        self.assertTrue(res.assist_applied_to_evf_lcd)
        self.assertEqual(res.hdmi_infoframe_eotf, p112.EOTF_HLG_BT2100)
        self.assertNotEqual(res.evf_gpe0_preview_sha256, res.raw_sensor_preview_sha256)
        self.assertEqual(res.xavc_stream_sha256, res.xavc_baseline_sha256)
        self.assertEqual(res.hdmi_clean_feed_sha256, res.hdmi_baseline_sha256)
        self.assertEqual(res.xavc_assist_burn_in_bytes, 0)
        self.assertEqual(res.hdmi_clean_feed_leakage_bytes, 0)

    def test_22_injected_assist_burn_in_into_xavc_or_hdmi_fails_closed(self) -> None:
        r_xavc = p112.evaluate_gamma_display_assist_isolation(
            camera_gamma="HLG_BT2020",
            assist_mode=p112.ASSIST_MODE_HLG_BT2020_709,
            inject_xavc_burn_in_fault=True,
        )
        self.assertFalse(r_xavc.passed)
        self.assertIn("BLOCKED_GAMMA_ASSIST_BURN_IN_LEAKAGE", r_xavc.violation_codes)
        self.assertGreater(r_xavc.xavc_assist_burn_in_bytes, 0)

        r_hdmi = p112.evaluate_gamma_display_assist_isolation(
            camera_gamma="SLOG3_SGAMUT3_CINE",
            assist_mode=p112.ASSIST_MODE_SLOG3_709_800,
            inject_hdmi_burn_in_fault=True,
        )
        self.assertFalse(r_hdmi.passed)
        self.assertIn("BLOCKED_GAMMA_ASSIST_BURN_IN_LEAKAGE", r_hdmi.violation_codes)
        self.assertGreater(r_hdmi.hdmi_clean_feed_leakage_bytes, 0)


class TestG33G34DuctFizGimbalHil(unittest.TestCase):
    """Verify G33 salt-spray/haze duct alerts & G34 wireless FIZ hard-stop / gimbal CoG HIL."""

    def test_23_g33_mitigated_coastal_dust_haze_passes_nominally(self) -> None:
        res = p112.simulate_g33_saltspray_haze_duct_hil(
            coastal_salt_spray_env=True,
            hydrophobic_vent_membrane_or_housing=True,
            pm10_dust_ug_m3=750.0,
            intake_hepa_mesh_installed=True,
            studio_haze_density_mg_m3=35.0,
            continuous_fan_exposure_min=60.0,
            post_wrap_isopropyl_duct_purge_scheduled=True,
        )
        self.assertTrue(res.passed)
        self.assertEqual(res.duct_protection_mode, "NOMINAL_COOLING")
        self.assertFalse(res.duct_protection_alert_active)
        self.assertEqual(res.wdt_resets, 0)
        self.assertEqual(res.duct_salt_haze_ingestion_damage_events, 0)

    def test_24_g33_unsealed_coastal_salt_spray_triggers_graceful_duct_alert(self) -> None:
        res = p112.simulate_g33_saltspray_haze_duct_hil(
            coastal_salt_spray_env=True,
            hydrophobic_vent_membrane_or_housing=False,
        )
        self.assertFalse(res.passed)
        self.assertIn("BLOCKED_CORROSIVE_SALTSPRAY_UNSEALED_DUCT", res.violation_codes)
        self.assertTrue(res.duct_protection_alert_active)
        self.assertTrue(res.graceful_alert_posted_to_gpe0)
        self.assertEqual(res.duct_protection_mode, "PROTECTIVE_THROTTLE_ALERT")
        self.assertEqual(res.wdt_resets, 0)
        self.assertEqual(res.stock_cp_fault_count, 0)
        self.assertEqual(res.duct_salt_haze_ingestion_damage_events, 0)

    def test_25_g33_heavy_glycol_haze_triggers_graceful_fouling_alert(self) -> None:
        res = p112.simulate_g33_saltspray_haze_duct_hil(
            studio_haze_density_mg_m3=42.0,
            continuous_fan_exposure_min=65.0,
            post_wrap_isopropyl_duct_purge_scheduled=False,
        )
        self.assertFalse(res.passed)
        self.assertIn("BLOCKED_OIL_GLYCOL_HAZE_FIN_FOULING", res.violation_codes)
        self.assertGreater(res.haze_exposure_dose_mg_min_m3, 1125.0)
        self.assertTrue(res.duct_protection_alert_active)
        self.assertEqual(res.wdt_resets, 0)

    def test_26_g33_fine_alkali_dust_without_hepa_triggers_graceful_alert(self) -> None:
        res = p112.simulate_g33_saltspray_haze_duct_hil(
            pm10_dust_ug_m3=850.0,
            intake_hepa_mesh_installed=False,
        )
        self.assertFalse(res.passed)
        self.assertIn("BLOCKED_FINE_ALKALI_DUST_ABRASION_HAZARD", res.violation_codes)
        self.assertTrue(res.duct_protection_alert_active)
        self.assertEqual(res.duct_salt_haze_ingestion_damage_events, 0)

    def test_27_g34_calibrated_fiz_and_autotuned_22mm_gimbal_pass(self) -> None:
        res = p112.simulate_g34_fiz_gimbal_hil(
            requested_fiz_torque_nm=2.8,
            hard_stops_calibrated=True,
            dual_rod_or_cage_bridge_clamp=True,
            gimbal_mounted=True,
            zoom_cog_shift_mm=22.0,
            gimbal_autotune_after_zoom=True,
        )
        self.assertTrue(res.passed)
        self.assertFalse(res.fiz_soft_limit_clamp_engaged)
        self.assertFalse(res.ibis_anti_saturation_engaged)
        self.assertEqual(res.fiz_gear_strip_events, 0)
        self.assertEqual(res.ibis_coil_saturation_events, 0)

    def test_28_g34_uncalibrated_gt2v5nm_fiz_hardstop_slam_engages_instant_soft_limit_clamp(self) -> None:
        res = p112.simulate_g34_fiz_gimbal_hil(
            requested_fiz_torque_nm=3.2,
            hard_stops_calibrated=False,
            fly_by_wire_infinite_ring=False,
            dual_rod_or_cage_bridge_clamp=True,
        )
        self.assertFalse(res.passed)
        self.assertIn("BLOCKED_FOLLOWFOCUS_UNCALIBRATED_HARDSTOP_TORQUE", res.violation_codes)
        self.assertTrue(res.fiz_soft_limit_clamp_engaged)
        self.assertLessEqual(res.clamped_fiz_torque_nm, p112.FIZ_SOFT_LIMIT_CLAMP_NM)
        self.assertLess(res.clamped_fiz_torque_nm, p112.FIZ_UNCALIBRATED_MAX_TORQUE_NM)
        self.assertLess(res.fiz_clamp_latency_ms, 2.0)
        self.assertEqual(res.fiz_gear_strip_events, 0)

    def test_29_g34_single_rod_fiz_deflection_slip_clamps_without_gear_strip(self) -> None:
        res = p112.simulate_g34_fiz_gimbal_hil(
            requested_fiz_torque_nm=2.6,
            hard_stops_calibrated=True,
            dual_rod_or_cage_bridge_clamp=False,
        )
        self.assertFalse(res.passed)
        self.assertIn("BLOCKED_SINGLE_ROD_FIZ_DEFLECTION_SLIP", res.violation_codes)
        self.assertTrue(res.fiz_soft_limit_clamp_engaged)
        self.assertGreater(res.single_rod_deflection_mm, 0.0)
        self.assertEqual(res.fiz_gear_strip_events, 0)

    def test_30_g34_22mm_telescoping_zoom_gimbal_cog_resonance_engages_ibis_anti_saturation(self) -> None:
        res = p112.simulate_g34_fiz_gimbal_hil(
            requested_fiz_torque_nm=0.9,
            hard_stops_calibrated=True,
            dual_rod_or_cage_bridge_clamp=True,
            gimbal_mounted=True,
            zoom_cog_shift_mm=22.0,
            gimbal_autotune_after_zoom=False,
        )
        self.assertFalse(res.passed)
        self.assertIn("BLOCKED_GIMBAL_TELESCOPING_COG_OSCILLATION", res.violation_codes)
        self.assertGreaterEqual(res.gimbal_pid_resonance_hz, p112.GIMBAL_OSCILLATION_BAND_MIN_HZ)
        self.assertLessEqual(res.gimbal_pid_resonance_hz, p112.GIMBAL_OSCILLATION_BAND_MAX_HZ)
        self.assertTrue(res.ibis_anti_saturation_engaged)
        self.assertEqual(res.ibis_center_lock_state, "ANTI_SATURATION_CENTER_DAMPED")
        self.assertLessEqual(res.ibis_coil_current_ma, p112.IBIS_COIL_SAFE_LIMIT_MA)
        self.assertEqual(res.ibis_coil_saturation_events, 0)
        self.assertEqual(res.cp_mutation_bytes, 0)


class TestStage19SuiteIntegrationCliAndHygiene(unittest.TestCase):
    """Verify Stage 19 suite integration, CLI flags, runtime budgets & strict hygiene."""

    def test_31_clean_room_audit_digest_reproducible_and_no_bytes_repr(self) -> None:
        rep1 = p112.run_phase112_hdr_hlg_fiz_gimbal_audit(force_clean_room=True)
        rep2 = p112.run_phase112_hdr_hlg_fiz_gimbal_audit(force_clean_room=True)
        self.assertTrue(rep1["all_checks_passed"])
        self.assertEqual(rep1["audit_digest_sha256"], rep2["audit_digest_sha256"])

        rendered = json.dumps(rep1, allow_nan=False)
        self.assertNotRegex(rendered, r'(?<![0-9A-Za-z_/.-])b[\'"]')

        copy = dict(rep1)
        recorded = copy.pop("audit_digest_sha256")
        expected = hashlib.sha256(
            json.dumps(copy, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        self.assertEqual(recorded, expected)

    def test_32_standalone_cli_flags_emit_valid_outputs(self) -> None:
        for argv in (
            ["--clean-room", "--summary"],
            ["--clean-room", "--hlg-matrix"],
            ["--clean-room", "--infoframe-matrix"],
            ["--clean-room", "--assist-matrix"],
            ["--clean-room", "--hil-matrix"],
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = p112.main(argv)
            self.assertEqual(rc, 0, msg=f"CLI argv={argv} failed")
            self.assertTrue(buf.getvalue().strip())

    def test_33_suite_in_process_stage19_and_skip_phase112_config(self) -> None:
        cfg_on = suite.CoEmulationConfig(force_clean_room=True)
        rep_on = suite.run_fx3_vm_coemulation_suite(cfg_on)
        self.assertTrue(rep_on["all_checks_passed"])
        self.assertIn("stage19_phase112_hdr_hlg_fiz_gimbal", rep_on)
        self.assertTrue(rep_on["stage19_phase112_hdr_hlg_fiz_gimbal"]["all_checks_passed"])

        cfg_skip = suite.CoEmulationConfig(
            force_clean_room=True,
            include_phase112_hdr_hlg_fiz_gimbal=False,
        )
        rep_skip = suite.run_fx3_vm_coemulation_suite(cfg_skip)
        self.assertTrue(rep_skip["all_checks_passed"])
        self.assertNotIn("stage19_phase112_hdr_hlg_fiz_gimbal", rep_skip)

    def test_34_suite_subprocess_summary_and_skip_phase112_flag(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        proc = subprocess.run(
            [
                "/usr/bin/python3",
                "-B",
                str(FX3_VM_DIR / "fx3_vm_coemulation_suite.py"),
                "--clean-room",
                "--summary",
            ],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        self.assertIn("hlg_assist_g33_g34=CLEAN_ROOM_SYNTHETIC", proc.stdout)

        proc_skip = subprocess.run(
            [
                "/usr/bin/python3",
                "-B",
                str(FX3_VM_DIR / "fx3_vm_coemulation_suite.py"),
                "--clean-room",
                "--skip-phase112",
                "--summary",
            ],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc_skip.returncode, 0, msg=proc_skip.stderr)
        self.assertNotIn("hlg_assist_g33_g34=", proc_skip.stdout)

    def test_35_19_stage_suite_clean_room_runtime_under_budget(self) -> None:
        t0 = time.monotonic()
        rep = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig(force_clean_room=True))
        elapsed = time.monotonic() - t0
        self.assertTrue(rep["all_checks_passed"])
        self.assertLess(elapsed, 0.65)

    def test_36_source_hygiene_o_rdonly_and_no_write_flags_or_port_8768_or_raw_bytes(self) -> None:
        src = (FX3_VM_DIR / "hdr_hlg_assist_fiz_gimbal_emulator.py").read_text(encoding="utf-8")
        self.assertIn("os.O_RDONLY", src)
        self.assertNotIn("os.O_WRONLY", src)
        self.assertNotIn("os.O_RDWR", src)
        self.assertNotIn("87" + "68", src)
        self.assertIn("sys.dont_write_bytecode = True", src)

        rep = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig(force_clean_room=True))
        rendered = json.dumps(rep, allow_nan=False)
        self.assertNotRegex(rendered, r'(?<![0-9A-Za-z_/.-])b[\'"]')
        self.assertIsNone(re.search(r"NaN|Infinity", rendered))


if __name__ == "__main__":
    unittest.main()
