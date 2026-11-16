#!/usr/bin/env python3
"""Phase 117 Test Suite — Stage 20 External Atomos/Blackmagic ProRes RAW / BRAW
16->12-Bit Log Metadata Handshake, E-Mount 12-Pin Focus Breathing FOV Crop vs
PL/RAW Identity Bypass, MI-Shoe I2S 48kHz Master-Clock PLL Lock, & G35/G36
AOC HDMI +5V / CFexpress NVMe Thermal & Door-Open FAT Journal HIL.

Exercises 40 fast unit, math, fail-closed guard, Stage 20 suite integration,
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
import hdmi_raw_prores_breathing_mishoe_aoc_emulator as p117  # noqa: E402


_AUDIT_CACHE: dict = {}


def _get_clean_room_audit() -> dict:
    if "clean_room" not in _AUDIT_CACHE:
        _AUDIT_CACHE["clean_room"] = p117.run_phase117_proresraw_breathing_mishoe_aoc_audit(
            force_clean_room=True
        )
    return _AUDIT_CACHE["clean_room"]


class TestPhase117DonorAuditAndRedlines(unittest.TestCase):
    """Verify O_RDONLY donor audit, clean-room fallback, and zero-mutation redlines."""

    def test_01_clean_room_donor_audit_verifies_all_10_artifacts_and_sha256(self) -> None:
        audit = p117.inspect_phase117_donors(force_clean_room=True)
        self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(audit.access_mode, "O_RDONLY")
        self.assertEqual(audit.donor_files_inspected, 0)
        self.assertTrue(audit.all_contracts_verified)
        self.assertGreaterEqual(len(audit.checked_markers), 30)
        self.assertEqual(audit.missing_markers, ())
        for key, (expected_bytes, expected_sha) in p117.PINNED_DONOR_SHA256.items():
            self.assertEqual(audit.bytes_by_artifact[key], expected_bytes)
            self.assertEqual(audit.sha256_by_artifact[key], expected_sha)

    def test_02_force_clean_room_env_disables_local_donor_paths(self) -> None:
        env = {p117.ENV_FORCE_CLEAN_ROOM: "1"}
        self.assertTrue(p117.is_forced_clean_room(env))
        paths = p117.resolve_phase117_donor_paths(env=env)
        self.assertEqual(len(paths), 10)
        for path in paths.values():
            self.assertIn(p117.CLEAN_ROOM_SENTINEL_DIRNAME, str(path))
        audit = p117.inspect_phase117_donors(env=env)
        self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_03_local_donor_o_rdonly_audit_when_present_or_clean_room(self) -> None:
        if p117.is_forced_clean_room():
            audit = p117.inspect_phase117_donors()
            self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")
            return
        paths = p117.resolve_phase117_donor_paths()
        audit = p117.inspect_phase117_donors()
        self.assertTrue(audit.all_contracts_verified)
        if all(p.is_file() for p in paths.values()):
            self.assertEqual(audit.source_mode, "LOCAL_DONOR_RDONLY")
            self.assertEqual(audit.donor_files_inspected, 10)
            for key, (expected_bytes, expected_sha) in p117.PINNED_DONOR_SHA256.items():
                self.assertEqual(audit.bytes_by_artifact[key], expected_bytes)
                self.assertEqual(audit.sha256_by_artifact[key], expected_sha)
        else:
            self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_04_missing_donor_root_falls_back_to_clean_room(self) -> None:
        env = {
            p117.ENV_MAC_WORK_ROOT: "/nonexistent_phase117_mac_work_root",
            p117.ENV_MAIN_LAB_WORK_ROOT: "/nonexistent_phase117_main_work_root",
        }
        audit = p117.inspect_phase117_donors(force_clean_room=True, env=env)
        self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(audit.donor_files_inspected, 0)
        self.assertTrue(audit.all_contracts_verified)

    def test_05_redlines_zero_mutations_zero_burn_in_and_zero_damage(self) -> None:
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
        self.assertEqual(red["raw_lut_burn_in_frames"], 0)
        self.assertEqual(red["pl_breathing_stale_crop_frames"], 0)
        self.assertEqual(red["audio_pop_click_frames"], 0)
        self.assertEqual(red["sy1129_hdmi_fuse_damage_events"], 0)
        self.assertEqual(red["cfexpress_fat_corruption_events"], 0)
        self.assertEqual(red["donor_access_mode"], "O_RDONLY")


class TestPillarAHdmiRawProResBraw(unittest.TestCase):
    """Verify 16->12-bit Log companding, CTA-861 VSIF, SONYRAW1 metadata & clean RAW isolation."""

    def test_06_raw16_to_raw12_log_companding_monotonic_shadow_injective_and_c1_continuous(self) -> None:
        comp = p117.verify_raw16_to_raw12_companding()
        self.assertTrue(comp["passed"])
        self.assertTrue(comp["shadow_0_512_injective"])
        self.assertTrue(comp["full_range_monotone"])
        self.assertLess(comp["c0_breakpoint_error"], 1e-7)
        self.assertLess(comp["c1_slope_error"], 1e-3)
        self.assertLess(comp["max_relative_quant_error_ge64"], 0.01)

    def test_07_ob_clamp_2048_roundtrip_zero_drift_and_dynamic_range_ge_14_5_stops(self) -> None:
        comp = p117.verify_raw16_to_raw12_companding()
        self.assertEqual(comp["ob_clamp_adu_in"], 2048)
        self.assertEqual(comp["ob_clamp_adu_roundtrip"], 2048)
        self.assertEqual(comp["ob_clamp_drift_adu"], 0)
        self.assertGreaterEqual(comp["effective_dynamic_range_stops"], 14.5)
        self.assertEqual(p117.raw16_to_raw12_log(0), 0)
        self.assertEqual(p117.raw16_to_raw12_log(65535), 4095)

    def test_08_synthesize_31byte_cta861_vsif_0x81_atomos_and_braw(self) -> None:
        for rec in (p117.RECORDER_ATOMOS_PRORES_RAW, p117.RECORDER_BLACKMAGIC_BRAW):
            vsif = p117.synthesize_hdmi_raw_vsif(recorder_target=rec, fps_code=24)
            self.assertTrue(vsif.valid)
            self.assertEqual(vsif.infoframe_type, 0x81)
            self.assertEqual(vsif.infoframe_version, 0x01)
            self.assertEqual(vsif.payload_length, 27)
            self.assertEqual(vsif.packet_length, 31)
            self.assertEqual(vsif.checksum_sum_mod256, 0)
            self.assertEqual(vsif.ieee_oui, p117.SONY_IEEE_OUI_24BIT)
            parsed = p117.parse_and_verify_hdmi_raw_vsif(vsif.packet_hex)
            self.assertTrue(parsed["valid"])
            self.assertEqual(parsed["recorder_target"], rec)
            self.assertTrue(parsed["raw_12bit_log_active"])
            self.assertTrue(parsed["lut_burn_in_disabled"])
            self.assertEqual(parsed["width"], 4264)
            self.assertEqual(parsed["height"], 2408)

    def test_09_bad_vsif_checksum_length_header_rejected_fail_closed(self) -> None:
        vsif = p117.synthesize_hdmi_raw_vsif(recorder_target=p117.RECORDER_ATOMOS_PRORES_RAW)
        bad_csum = bytearray.fromhex(vsif.packet_hex)
        bad_csum[3] ^= 0x22
        r_csum = p117.parse_and_verify_hdmi_raw_vsif(bad_csum.hex())
        self.assertFalse(r_csum["valid"])
        self.assertEqual(r_csum["violation_code"], "BLOCKED_RAW_HANDSHAKE_CHECKSUM_MISMATCH")

        r_len = p117.parse_and_verify_hdmi_raw_vsif(vsif.packet_hex[:-4])
        self.assertFalse(r_len["valid"])
        self.assertEqual(r_len["violation_code"], "BLOCKED_RAW_VSIF_BAD_LENGTH")

        bad_hdr = bytearray.fromhex(vsif.packet_hex)
        bad_hdr[0] = 0x82
        r_hdr = p117.parse_and_verify_hdmi_raw_vsif(bad_hdr.hex())
        self.assertFalse(r_hdr["valid"])
        self.assertEqual(r_hdr["violation_code"], "BLOCKED_RAW_VSIF_BAD_HEADER")

    def test_10_build_and_decode_56byte_sonyraw1_metadata_packet_crc32(self) -> None:
        pkt_hex = p117.build_hdmi_raw_metadata_packet(
            recorder_target=p117.RECORDER_ATOMOS_PRORES_RAW,
            base_iso=800,
            exposure_index=1600,
            wb_kelvin=5600,
            wb_tint=3,
            focal_length_mm=35.0,
            t_stop=1.4,
        )
        self.assertEqual(len(bytes.fromhex(pkt_hex)), 56)
        dec = p117.decode_hdmi_raw_metadata_packet(pkt_hex)
        self.assertTrue(dec["valid"])
        self.assertEqual(dec["magic"], "SONYRAW1")
        self.assertEqual(dec["recorder_target"], p117.RECORDER_ATOMOS_PRORES_RAW)
        self.assertEqual(dec["base_iso"], 800)
        self.assertEqual(dec["exposure_index"], 1600)
        self.assertEqual(dec["wb_kelvin"], 5600)
        self.assertEqual(dec["wb_tint"], 3)
        self.assertAlmostEqual(dec["focal_length_mm"], 35.0, places=1)
        self.assertAlmostEqual(dec["t_stop"], 1.4, places=2)
        self.assertEqual(dec["sensor_active_dims"], [4264, 2408])
        self.assertEqual(dec["metadata_crop_width"], 4240)

    def test_11_corrupt_sonyraw1_crc_magic_length_rejected_fail_closed(self) -> None:
        pkt_hex = p117.build_hdmi_raw_metadata_packet(
            recorder_target=p117.RECORDER_BLACKMAGIC_BRAW,
            base_iso=12800,
            exposure_index=12800,
            wb_kelvin=3200,
            wb_tint=-2,
            focal_length_mm=50.0,
            t_stop=2.0,
        )
        bad_crc = bytearray.fromhex(pkt_hex)
        bad_crc[10] ^= 0x0F
        r_crc = p117.decode_hdmi_raw_metadata_packet(bad_crc.hex())
        self.assertFalse(r_crc["valid"])
        self.assertEqual(r_crc["violation_code"], "BLOCKED_RAW_META_CRC_MISMATCH")

        r_len = p117.decode_hdmi_raw_metadata_packet(pkt_hex[:-4])
        self.assertFalse(r_len["valid"])
        self.assertEqual(r_len["violation_code"], "BLOCKED_RAW_META_BAD_LENGTH")

        with self.assertRaises(p117.HdmiRawBreathingMishoeAocError):
            p117.build_hdmi_raw_metadata_packet(
                recorder_target=p117.RECORDER_ATOMOS_PRORES_RAW,
                base_iso=640,  # invalid Dual Base ISO
                exposure_index=640,
                wb_kelvin=5600,
                wb_tint=0,
                focal_length_mm=35.0,
                t_stop=2.0,
            )

    def test_12_atomos_prores_raw_iso800_and_braw_iso12800_unbaked_clean_stream(self) -> None:
        prores = p117.evaluate_hdmi_raw_handshake(
            recorder_target=p117.RECORDER_ATOMOS_PRORES_RAW,
            base_iso=800,
            exposure_index=800,
            wb_kelvin=5600,
            wb_tint=2,
            fps=23.976,
        )
        self.assertTrue(prores.passed)
        self.assertTrue(prores.wb_iso_unlocked_in_nle)
        self.assertTrue(prores.lut_applied_to_local_gpe0_only)
        self.assertEqual(prores.raw_lut_burn_in_frames, 0)
        self.assertEqual(prores.raw_osd_burn_in_frames, 0)
        self.assertNotEqual(prores.hdmi_raw_stream_sha256, prores.local_gpe0_monitor_sha256)

        braw = p117.evaluate_hdmi_raw_handshake(
            recorder_target=p117.RECORDER_BLACKMAGIC_BRAW,
            base_iso=12800,
            exposure_index=12800,
            wb_kelvin=3200,
            wb_tint=-4,
            fps=59.94,
        )
        self.assertTrue(braw.passed)
        self.assertFalse(braw.wb_iso_unlocked_in_nle)
        self.assertEqual(braw.raw_lut_burn_in_frames, 0)
        self.assertTrue(braw.lut_applied_to_local_gpe0_only)

    def test_13_injected_lut_or_osd_burn_in_fault_blocked_fail_closed(self) -> None:
        r_lut = p117.evaluate_hdmi_raw_handshake(inject_lut_burn_in_fault=True)
        self.assertFalse(r_lut.passed)
        self.assertIn("BLOCKED_RAW_LUT_BURN_IN_CONTAMINATION", r_lut.violation_codes)
        self.assertEqual(r_lut.raw_lut_burn_in_frames, 1)

        r_osd = p117.evaluate_hdmi_raw_handshake(inject_osd_burn_in_fault=True)
        self.assertFalse(r_osd.passed)
        self.assertIn("BLOCKED_RAW_OSD_CONTAMINATION", r_osd.violation_codes)
        self.assertEqual(r_osd.raw_osd_burn_in_frames, 1)

    def test_14_non_log_shooting_or_unsupported_fps_blocked_fail_closed(self) -> None:
        r_log = p117.evaluate_hdmi_raw_handshake(log_shooting_enabled=False)
        self.assertFalse(r_log.passed)
        self.assertIn("BLOCKED_RAW_REQUIRES_LOG_SHOOTING", r_log.violation_codes)

        r_fps = p117.evaluate_hdmi_raw_handshake(fps=119.88)
        self.assertFalse(r_fps.passed)
        self.assertIn("BLOCKED_UNSUPPORTED_HDMI_RAW_FPS", r_fps.violation_codes)


class TestPillarBFocusBreathingArbitrator(unittest.TestCase):
    """Verify E-Mount 12-pin focus breathing FOV crop (1.00x..1.08x) vs <0.5ms PL/RAW bypass."""

    def test_15_emount_12pin_breathing_curve_interpolates_1_00_to_1_08_across_distances(self) -> None:
        c_mod = p117.compute_breathing_fov_crop_factor("SEL50F12GM", 400.0)
        c_mid = p117.compute_breathing_fov_crop_factor("SEL50F12GM", 1200.0)
        c_far = p117.compute_breathing_fov_crop_factor("SEL50F12GM", 4000.0)
        c_inf = p117.compute_breathing_fov_crop_factor("SEL50F12GM", 20000.0)
        self.assertEqual(c_mod, 1.080)
        self.assertEqual(c_inf, 1.000)
        self.assertGreater(c_mid, c_far)
        self.assertGreater(c_mod, c_mid)
        self.assertGreater(c_far, c_inf)

    def test_16_all_6_emount_12pin_profiles_bounded_and_unknown_or_bad_dist_raises(self) -> None:
        for lens_id, prof in p117.EMOUNT_12PIN_BREATHING_PROFILES.items():
            c_min = p117.compute_breathing_fov_crop_factor(lens_id, prof["min_focus_mm"])
            c_inf = p117.compute_breathing_fov_crop_factor(lens_id, 20000.0)
            self.assertAlmostEqual(c_min, prof["max_crop"], places=4)
            self.assertEqual(c_inf, 1.000)
        with self.assertRaises(p117.HdmiRawBreathingMishoeAocError):
            p117.compute_breathing_fov_crop_factor("UNKNOWN_LENS", 1000.0)
        with self.assertRaises(p117.HdmiRawBreathingMishoeAocError):
            p117.compute_breathing_fov_crop_factor("SEL2470GM2", 0.0)

    def test_17_unchipped_pl_adapter_identity_bypass_1_00x_under_0_5ms(self) -> None:
        res = p117.evaluate_focus_breathing_arbitrator(
            lens_id="UNCHIPPED_PL_ADAPTER",
            focus_distance_mm=800.0,
            emount_12pin_authenticated=False,
            unchipped_pl_adapter_mounted=True,
        )
        self.assertTrue(res.passed)
        self.assertTrue(res.identity_bypass_active)
        self.assertEqual(res.applied_fov_crop_factor, 1.000)
        self.assertEqual(res.bypass_reason, "BYPASSED_UNCHIPPED_PL_ADAPTER")
        self.assertLess(res.bypass_latency_ms, 0.50)
        self.assertEqual(res.pl_breathing_stale_crop_frames, 0)

    def test_18_hdmi_raw_and_sq_120p_identity_bypass_1_00x_under_0_5ms(self) -> None:
        r_raw = p117.evaluate_focus_breathing_arbitrator(
            lens_id="SEL50F12GM",
            focus_distance_mm=400.0,
            emount_12pin_authenticated=True,
            hdmi_raw_output_active=True,
        )
        self.assertTrue(r_raw.passed)
        self.assertTrue(r_raw.identity_bypass_active)
        self.assertEqual(r_raw.applied_fov_crop_factor, 1.000)
        self.assertEqual(r_raw.bypass_reason, "BYPASSED_HDMI_RAW_NO_SENSOR_CROP")
        self.assertLess(r_raw.bypass_latency_ms, 0.50)

        r_sq = p117.evaluate_focus_breathing_arbitrator(
            lens_id="SEL2470GM2",
            focus_distance_mm=300.0,
            emount_12pin_authenticated=True,
            sq_hfr_120p_active=True,
        )
        self.assertTrue(r_sq.passed)
        self.assertTrue(r_sq.identity_bypass_active)
        self.assertEqual(r_sq.applied_fov_crop_factor, 1.000)
        self.assertEqual(r_sq.bypass_reason, "BYPASSED_SQ_HFR_120P")
        self.assertLess(r_sq.bypass_latency_ms, 0.50)

    def test_19_forced_crop_on_hdmi_raw_blocked_fail_closed(self) -> None:
        res = p117.evaluate_focus_breathing_arbitrator(
            lens_id="SEL50F12GM",
            focus_distance_mm=400.0,
            hdmi_raw_output_active=True,
            force_sensor_crop_on_raw_fault=True,
        )
        self.assertFalse(res.passed)
        self.assertIn("BLOCKED_BREATHING_CROP_ON_HDMI_RAW_ILLEGAL", res.violation_codes)
        self.assertGreater(res.applied_fov_crop_factor, 1.000)

    def test_20_stale_pl_breathing_crop_fault_blocked_fail_closed(self) -> None:
        res = p117.evaluate_focus_breathing_arbitrator(
            lens_id="UNCHIPPED_PL_ADAPTER",
            focus_distance_mm=1000.0,
            emount_12pin_authenticated=False,
            unchipped_pl_adapter_mounted=True,
            inject_stale_pl_crop_fault=True,
        )
        self.assertFalse(res.passed)
        self.assertIn("BLOCKED_STALE_BREATHING_CROP_ON_PL_ADAPTER", res.violation_codes)
        self.assertEqual(res.pl_breathing_stale_crop_frames, 1)


class TestPillarCMiShoeI2sPllLock(unittest.TestCase):
    """Verify MI-Shoe 4ch 24-bit/48kHz I2S Fractional-N PLL lock over 12h & zero-pop hot-unplug."""

    def test_21_xlr_h1_5994p_and_wireless_rx_2997p_12h_pll_drift_under_0_20_smp_hr(self) -> None:
        xlr = p117.evaluate_mishoe_i2s_pll_lock(
            device_type="XLR_H1",
            fps_label="59.94p",
            duration_hours=12.0,
        )
        self.assertTrue(xlr.passed)
        self.assertEqual(xlr.channels, 4)
        self.assertEqual(xlr.bit_depth, 24)
        self.assertEqual(xlr.sample_rate_hz, 48_000)
        self.assertEqual(xlr.pll_state, "FRACTIONAL_N_LOCKED")
        self.assertLess(xlr.drift_samples_per_hour, 0.20)
        self.assertEqual(xlr.drift_samples_per_hour, 0.0)
        self.assertEqual(xlr.total_drift_samples_12h, 0.0)

        wlx = p117.evaluate_mishoe_i2s_pll_lock(
            device_type="WIRELESS_DIGITAL_RX",
            fps_label="29.97p",
            duration_hours=12.0,
        )
        self.assertTrue(wlx.passed)
        self.assertLess(wlx.drift_samples_per_hour, 0.20)
        self.assertEqual(wlx.total_drift_samples_12h, 0.0)

    def test_22_ntsc_2997p_and_5994p_5frame_audio_cadences_and_4608kbps_i2s(self) -> None:
        r29 = p117.evaluate_mishoe_i2s_pll_lock(fps_label="29.97p")
        r59 = p117.evaluate_mishoe_i2s_pll_lock(fps_label="59.94p")
        self.assertEqual(r29.cadence_samples_per_frame, (1602, 1601, 1602, 1601, 1602))
        self.assertEqual(sum(r29.cadence_samples_per_frame), 8008)
        self.assertEqual(r59.cadence_samples_per_frame, (801, 801, 801, 801, 800))
        self.assertEqual(sum(r59.cadence_samples_per_frame), 4004)
        self.assertEqual(r59.i2s_bitrate_bps, 4_608_000)

    def test_23_all_frame_rates_fractional_n_locked_over_12h(self) -> None:
        for fps_label in p117.FRAME_RATE_PLL_SPECS:
            res = p117.evaluate_mishoe_i2s_pll_lock(fps_label=fps_label, duration_hours=12.0)
            self.assertTrue(res.passed, msg=f"fps={fps_label} failed")
            self.assertLess(res.drift_samples_per_hour, 0.20)
            self.assertEqual(res.audio_pop_click_frames, 0)

    def test_24_mishoe_hot_unplug_p11_fallback_to_internal_crystal_zero_pop(self) -> None:
        res = p117.evaluate_mishoe_i2s_pll_lock(
            device_type="XLR_H1",
            fps_label="59.94p",
            hot_unplugged_mid_take=True,
            zero_cross_ramp_enabled=True,
        )
        self.assertTrue(res.passed)
        self.assertTrue(res.internal_crystal_fallback_active)
        self.assertEqual(res.pll_state, "INTERNAL_CRYSTAL_HOLDOVER")
        self.assertEqual(res.p11_queue_id, p117.P11_SMART_HANDLE_QUEUE_ID)
        self.assertEqual(res.p11_event_code, p117.P11_SMART_HANDLE_DETACHED_EVT)
        self.assertEqual(res.audio_pop_click_frames, 0)
        self.assertEqual(res.ivshmem_tx_leaks, 0)
        self.assertEqual(res.cp_mutation_bytes, 0)

    def test_25_unlocked_crystal_50ppm_slip_blocked_fail_closed(self) -> None:
        res = p117.evaluate_mishoe_i2s_pll_lock(
            fractional_n_pll_locked=False,
            unlocked_crystal_ppm=50.0,
            duration_hours=12.0,
        )
        self.assertFalse(res.passed)
        self.assertIn("BLOCKED_MISHOE_PLL_DRIFT_EXCEEDED", res.violation_codes)
        self.assertGreater(res.drift_samples_per_hour, p117.MAX_AUDIO_DRIFT_SAMPLES_PER_HOUR)
        self.assertEqual(res.pll_state, "UNLOCKED_SLIP")

    def test_26_unramped_hot_unplug_pop_click_and_invalid_args_fail_closed(self) -> None:
        res = p117.evaluate_mishoe_i2s_pll_lock(
            hot_unplugged_mid_take=True,
            zero_cross_ramp_enabled=False,
        )
        self.assertFalse(res.passed)
        self.assertIn("BLOCKED_HOT_UNPLUG_AUDIO_POP_CLICK", res.violation_codes)
        self.assertGreater(res.audio_pop_click_frames, 0)
        with self.assertRaises(p117.HdmiRawBreathingMishoeAocError):
            p117.evaluate_mishoe_i2s_pll_lock(device_type="UNKNOWN_SHOE")
        with self.assertRaises(p117.HdmiRawBreathingMishoeAocError):
            p117.evaluate_mishoe_i2s_pll_lock(fps_label="120.00p")


class TestPillarDG35G36AocCfexpressHil(unittest.TestCase):
    """Verify G35 AOC HDMI +5V clamp/isolation & G36 CFexpress NVMe thermal/VPG/door HIL."""

    def test_27_g35_passive_and_externally_powered_aoc_pass_nominally(self) -> None:
        passive = p117.simulate_g35_aoc_hdmi_5v_hil(
            hdmi_pin18_requested_ma=42.0,
            external_5v_injector_present=False,
            sink_backfeed_voltage_v=5.02,
        )
        self.assertTrue(passive.passed)
        self.assertFalse(passive.load_switch_clamp_engaged)
        self.assertFalse(passive.reverse_backfeed_isolated)
        self.assertEqual(passive.sy1129_hdmi_fuse_damage_events, 0)

        injected = p117.simulate_g35_aoc_hdmi_5v_hil(
            hdmi_pin18_requested_ma=140.0,
            external_5v_injector_present=True,
            sink_backfeed_voltage_v=5.00,
        )
        self.assertTrue(injected.passed)
        self.assertEqual(injected.clamped_pin18_ma, 0.0)
        self.assertEqual(injected.sy1129_hdmi_fuse_damage_events, 0)

    def test_28_g35_pin18_gt55ma_overcurrent_clamps_with_zero_sy1129_damage(self) -> None:
        res = p117.simulate_g35_aoc_hdmi_5v_hil(
            hdmi_pin18_requested_ma=125.0,
            external_5v_injector_present=False,
            sink_backfeed_voltage_v=5.00,
        )
        self.assertFalse(res.passed)
        self.assertIn("BLOCKED_AOC_HDMI_5V_OVERCURRENT_CLAMPED", res.violation_codes)
        self.assertTrue(res.load_switch_clamp_engaged)
        self.assertLessEqual(res.clamped_pin18_ma, p117.HDMI_PIN18_CURRENT_LIMIT_MA)
        self.assertEqual(res.sy1129_hdmi_fuse_damage_events, 0)
        self.assertEqual(res.wdt_resets, 0)

    def test_29_g35_gt5v35_reverse_backfeed_isolates_under_40us_with_zero_damage(self) -> None:
        res = p117.simulate_g35_aoc_hdmi_5v_hil(
            hdmi_pin18_requested_ma=40.0,
            external_5v_injector_present=False,
            sink_backfeed_voltage_v=5.85,
        )
        self.assertFalse(res.passed)
        self.assertIn("BLOCKED_HDMI_5V_REVERSE_BACKFEED_ISOLATED", res.violation_codes)
        self.assertTrue(res.reverse_backfeed_isolated)
        self.assertGreater(res.isolation_latency_us, 0.0)
        self.assertLess(res.isolation_latency_us, p117.HDMI_BACKFEED_MAX_ISOLATION_US)
        self.assertEqual(res.sy1129_hdmi_fuse_damage_events, 0)
        self.assertEqual(res.wdt_resets, 0)

    def test_30_g36_vpg400_and_vpg200_4k120p_600mbps_pass_write_floor_guard(self) -> None:
        v400 = p117.simulate_g36_cfexpress_nvme_door_hil(
            cfexpress_temp_c=64.0,
            card_vpg_profile="VPG400",
            sustained_p99_write_mb_s=420.0,
        )
        self.assertTrue(v400.passed)
        self.assertEqual(v400.required_write_floor_mb_s, 93.75)
        self.assertTrue(v400.vpg_write_floor_satisfied)
        self.assertEqual(v400.nvme_power_state, "PS0_NOMINAL")
        self.assertEqual(v400.cfexpress_fat_corruption_events, 0)

        v200 = p117.simulate_g36_cfexpress_nvme_door_hil(
            cfexpress_temp_c=71.0,
            card_vpg_profile="VPG200",
            sustained_p99_write_mb_s=215.0,
        )
        self.assertTrue(v200.passed)
        self.assertTrue(v200.vpg_write_floor_satisfied)

    def test_31_g36_cfexpress_gt82c_triggers_nvme_ps1_thermal_prewarning(self) -> None:
        res = p117.simulate_g36_cfexpress_nvme_door_hil(
            cfexpress_temp_c=84.5,
            card_vpg_profile="VPG400",
            sustained_p99_write_mb_s=410.0,
        )
        self.assertFalse(res.passed)
        self.assertIn("BLOCKED_CFEXPRESS_NVME_THERMAL_PREWARNING", res.violation_codes)
        self.assertTrue(res.nvme_thermal_prewarning_active)
        self.assertEqual(res.nvme_power_state, "PS1_THROTTLED")
        self.assertEqual(res.cfexpress_fat_corruption_events, 0)
        self.assertEqual(res.wdt_resets, 0)

    def test_32_g36_v30_or_low_write_speed_blocked_for_4k120p_600mbps(self) -> None:
        r_v30 = p117.simulate_g36_cfexpress_nvme_door_hil(
            cfexpress_temp_c=52.0,
            card_vpg_profile="V30",
            sustained_p99_write_mb_s=65.0,
        )
        self.assertFalse(r_v30.passed)
        self.assertIn("BLOCKED_VPG_WRITE_FLOOR_BELOW_600MBPS", r_v30.violation_codes)
        self.assertFalse(r_v30.vpg_write_floor_satisfied)

        r_slow = p117.simulate_g36_cfexpress_nvme_door_hil(
            cfexpress_temp_c=60.0,
            card_vpg_profile="VPG200",
            sustained_p99_write_mb_s=80.0,
        )
        self.assertFalse(r_slow.passed)
        self.assertIn("BLOCKED_VPG_WRITE_FLOOR_BELOW_600MBPS", r_slow.violation_codes)

    def test_33_g36_card_door_open_during_flush_commits_emergency_fat_journal_zero_corruption(self) -> None:
        res = p117.simulate_g36_cfexpress_nvme_door_hil(
            cfexpress_temp_c=60.0,
            card_vpg_profile="VPG400",
            sustained_p99_write_mb_s=420.0,
            slot_door_open_during_flush=True,
            flush_pending=True,
        )
        self.assertFalse(res.passed)
        self.assertIn("BLOCKED_CARD_DOOR_OPEN_DURING_FLUSH", res.violation_codes)
        self.assertTrue(res.emergency_fat_journal_committed)
        self.assertGreater(res.journal_commit_latency_ms, 0.0)
        self.assertEqual(res.exfat_volume_dirty_bit, 0)
        self.assertEqual(res.cfexpress_fat_corruption_events, 0)
        self.assertEqual(res.wdt_resets, 0)

    def test_34_g35_g36_negative_telemetry_or_unknown_vpg_raises(self) -> None:
        with self.assertRaises(p117.HdmiRawBreathingMishoeAocError):
            p117.simulate_g35_aoc_hdmi_5v_hil(hdmi_pin18_requested_ma=-1.0)
        with self.assertRaises(p117.HdmiRawBreathingMishoeAocError):
            p117.simulate_g36_cfexpress_nvme_door_hil(card_vpg_profile="VPG999")


class TestStage20SuiteIntegrationCliAndHygiene(unittest.TestCase):
    """Verify Stage 20 suite integration, CLI flags, runtime budgets & strict hygiene."""

    def test_35_clean_room_audit_digest_reproducible_and_no_bytes_repr(self) -> None:
        rep1 = p117.run_phase117_proresraw_breathing_mishoe_aoc_audit(force_clean_room=True)
        rep2 = p117.run_phase117_proresraw_breathing_mishoe_aoc_audit(force_clean_room=True)
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

    def test_36_standalone_cli_flags_emit_valid_outputs(self) -> None:
        for argv in (
            ["--clean-room", "--summary"],
            ["--clean-room", "--raw-matrix"],
            ["--clean-room", "--breathing-matrix"],
            ["--clean-room", "--mishoe-matrix"],
            ["--clean-room", "--hil-matrix"],
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = p117.main(argv)
            self.assertEqual(rc, 0, msg=f"CLI argv={argv} failed")
            self.assertTrue(buf.getvalue().strip())

    def test_37_suite_in_process_stage20_ge20_stages_and_skip_phase117_config(self) -> None:
        cfg_on = suite.CoEmulationConfig(force_clean_room=True)
        rep_on = suite.run_fx3_vm_coemulation_suite(cfg_on)
        self.assertTrue(rep_on["all_checks_passed"])
        self.assertIn("stage20_proresraw_breathing_mishoe_hil", rep_on)
        self.assertTrue(rep_on["stage20_proresraw_breathing_mishoe_hil"]["all_checks_passed"])

        stage_keys = [k for k in rep_on if re.match(r"^stage\d+_", k)]
        self.assertGreaterEqual(len(stage_keys), 20)

        cfg_skip = suite.CoEmulationConfig(
            force_clean_room=True,
            include_phase117_proresraw_breathing_mishoe_hil=False,
        )
        rep_skip = suite.run_fx3_vm_coemulation_suite(cfg_skip)
        self.assertTrue(rep_skip["all_checks_passed"])
        self.assertNotIn("stage20_proresraw_breathing_mishoe_hil", rep_skip)

    def test_38_suite_subprocess_summary_and_skip_phase117_flag(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        proc = subprocess.run(
            [
                sys.executable,
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
        self.assertIn("prores_breath_mi_g35_g36=CLEAN_ROOM_SYNTHETIC", proc.stdout)

        proc_skip = subprocess.run(
            [
                sys.executable,
                "-B",
                str(FX3_VM_DIR / "fx3_vm_coemulation_suite.py"),
                "--clean-room",
                "--skip-phase117",
                "--summary",
            ],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc_skip.returncode, 0, msg=proc_skip.stderr)
        self.assertNotIn("prores_breath_mi_g35_g36=", proc_skip.stdout)

    def test_39_20_stage_suite_clean_room_and_local_runtime_under_budget(self) -> None:
        t0 = time.monotonic()
        rep_clean = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig(force_clean_room=True))
        elapsed_clean = time.monotonic() - t0
        self.assertTrue(rep_clean["all_checks_passed"])
        self.assertLess(elapsed_clean, 3.50 if __import__("os").environ.get("GITHUB_ACTIONS") == "true" else 0.70)

        t1 = time.monotonic()
        rep_mode = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig())
        elapsed_mode = time.monotonic() - t1
        self.assertTrue(rep_mode["all_checks_passed"])
        self.assertLess(elapsed_mode, 9.00 if __import__("os").environ.get("GITHUB_ACTIONS") == "true" else 1.80)

    def test_40_source_hygiene_o_rdonly_and_no_write_flags_or_port_8768_or_raw_bytes(self) -> None:
        src = (FX3_VM_DIR / "hdmi_raw_prores_breathing_mishoe_aoc_emulator.py").read_text(encoding="utf-8")
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
