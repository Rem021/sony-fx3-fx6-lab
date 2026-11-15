#!/usr/bin/env python3
"""Phase 132 Test Suite — Stage 23 Virtual Production LED-Volume Brompton/Megapixel
Anti-Banding Fractional ECS Solver, Wired FreeD (0xD1 29-Byte) Lens Tracking ->
Unreal LiveLink Bridge, P12-Safe Art-Net 4 / sACN Lighting Sync, & G41/G42
Genlock-Clash / Helicopter IBIS Resonance HIL.

Exercises 40 fast unit, protocol, fail-closed guard, Stage 23 suite integration,
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
import vp_ledwall_freed_artnet_vib_emulator as p132  # noqa: E402


_AUDIT_CACHE: dict = {}


def _get_clean_room_audit() -> dict:
    if "clean_room" not in _AUDIT_CACHE:
        _AUDIT_CACHE["clean_room"] = p132.run_phase132_vp_ledwall_freed_artnet_audit(
            force_clean_room=True
        )
    return _AUDIT_CACHE["clean_room"]


class TestPhase132DonorAuditAndRedlines(unittest.TestCase):
    """Verify O_RDONLY donor audit, clean-room fallback, and zero-mutation redlines."""

    def test_01_clean_room_donor_audit_verifies_all_16_artifacts_and_sha256(self) -> None:
        audit = p132.inspect_phase132_donors(force_clean_room=True)
        self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(audit.access_mode, "O_RDONLY")
        self.assertEqual(audit.donor_files_inspected, 0)
        self.assertTrue(audit.all_contracts_verified)
        self.assertGreaterEqual(len(audit.checked_markers), 34)
        self.assertEqual(audit.missing_markers, ())
        for key, (expected_bytes, expected_sha) in p132.PINNED_DONOR_SHA256.items():
            self.assertEqual(audit.bytes_by_artifact[key], expected_bytes)
            self.assertEqual(audit.sha256_by_artifact[key], expected_sha)

    def test_02_force_clean_room_env_disables_local_donor_paths(self) -> None:
        env = {p132.ENV_FORCE_CLEAN_ROOM: "1"}
        self.assertTrue(p132.is_forced_clean_room(env))
        paths = p132.resolve_phase132_donor_paths(env=env)
        self.assertEqual(len(paths), 16)
        for path in paths.values():
            self.assertIn(p132.CLEAN_ROOM_SENTINEL_DIRNAME, str(path))
        audit = p132.inspect_phase132_donors(env=env)
        self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_03_local_donor_o_rdonly_audit_when_present_or_clean_room(self) -> None:
        if p132.is_forced_clean_room():
            audit = p132.inspect_phase132_donors()
            self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")
            return
        paths = p132.resolve_phase132_donor_paths()
        audit = p132.inspect_phase132_donors()
        self.assertTrue(audit.all_contracts_verified)
        if all(p.is_file() for p in paths.values()):
            self.assertEqual(audit.source_mode, "LOCAL_DONOR_RDONLY")
            self.assertEqual(audit.donor_files_inspected, 16)
            for key, (expected_bytes, expected_sha) in p132.PINNED_DONOR_SHA256.items():
                self.assertEqual(audit.bytes_by_artifact[key], expected_bytes)
                self.assertEqual(audit.sha256_by_artifact[key], expected_sha)
        else:
            self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_04_missing_donor_root_falls_back_to_clean_room(self) -> None:
        env = {
            p132.ENV_MAC_WORK_ROOT: "/nonexistent_phase132_mac_work_root",
            p132.ENV_MAIN_LAB_WORK_ROOT: "/nonexistent_phase132_main_work_root",
        }
        audit = p132.inspect_phase132_donors(force_clean_room=True, env=env)
        self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(audit.donor_files_inspected, 0)
        self.assertTrue(audit.all_contracts_verified)

    def test_05_redlines_zero_mutations_zero_wf12_and_zero_hw_damage(self) -> None:
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
        self.assertEqual(red["emmc_mutation_bytes"], 0)
        self.assertEqual(red["wf12_00342260_hits"], 0)
        self.assertEqual(red["flash_split_band_frames"], 0)
        self.assertEqual(red["cxd90057_pin_damage_events"], 0)
        self.assertEqual(red["imx510_sensor_burn_events"], 0)
        self.assertEqual(red["ibis_endstop_slam_events"], 0)
        self.assertEqual(red["ibis_coil_thermal_runaway_events"], 0)
        self.assertEqual(red["donor_access_mode"], "O_RDONLY")


class TestPillarAVpLedwallEcsSolver(unittest.TestCase):
    """Verify IMX510 rolling shutter + Brompton/Megapixel Fractional ECS Solver."""

    def test_06_brompton_4k24_1_8_3840hz_locked_under_0p5pct_residual(self) -> None:
        res = p132.solve_fractional_ecs_shutter(
            sensor_mode="4K24P",
            processor="BROMPTON_TESSERA_SX40",
            scan_mux="1/8",
            pwm_hz=3840.0,
            target_shutter_hz=48.0,
            frame_rate_hz=24.0,
            genlock_locked=True,
        )
        self.assertTrue(res.passed)
        self.assertEqual(res.imx510_readout_ms, 13.2)
        self.assertTrue(res.ecs_locked_to_integer_pwm)
        self.assertFalse(res.banding_fault_detected)
        self.assertLess(res.luminance_banding_residual_pct, 0.5)

    def test_07_megapixel_4k120_1_16_7680hz_locked_8p7ms_readout(self) -> None:
        res = p132.solve_fractional_ecs_shutter(
            sensor_mode="4K120P",
            processor="MEGAPIXEL_HELIOS",
            scan_mux="1/16",
            pwm_hz=7680.0,
            target_shutter_hz=240.0,
            frame_rate_hz=120.0,
            genlock_locked=True,
        )
        self.assertTrue(res.passed)
        self.assertEqual(res.imx510_readout_ms, 8.7)
        self.assertEqual(res.scan_mux_divisor, 16)
        self.assertTrue(res.ecs_locked_to_integer_pwm)
        self.assertLess(res.luminance_banding_residual_pct, 0.5)

    def test_08_960hz_1_16_scan_mux_solves_integer_locked_shutter(self) -> None:
        res = p132.solve_fractional_ecs_shutter(
            sensor_mode="4K24P",
            processor="BROMPTON_TESSERA_SX40",
            scan_mux="1/16",
            pwm_hz=960.0,
            target_shutter_hz=47.3,
            frame_rate_hz=24.0,
            genlock_locked=True,
        )
        self.assertTrue(res.passed)
        self.assertEqual(res.applied_shutter_hz, 60.0)
        self.assertTrue(res.ecs_locked_to_integer_pwm)
        self.assertLess(res.luminance_banding_residual_pct, 0.5)

    def test_09_unlocked_shutter_triggers_gt_18pct_banding_fault(self) -> None:
        res = p132.simulate_led_wall_ecs_capture(
            sensor_mode="4K24P",
            processor="BROMPTON_TESSERA_SX40",
            scan_mux="1/16",
            pwm_hz=960.0,
            shutter_hz=125.0,
            frame_rate_hz=24.0,
            genlock_locked=True,
        )
        self.assertFalse(res.passed)
        self.assertFalse(res.ecs_locked_to_integer_pwm)
        self.assertTrue(res.banding_fault_detected)
        self.assertGreater(res.luminance_banding_residual_pct, 18.0)
        self.assertIn("BLOCKED_ECS_PWM_PERIOD_MISMATCH", res.violation_codes)
        self.assertIn("BLOCKED_LEDWALL_BANDING_FAULT_GT_18PCT", res.violation_codes)

    def test_10_genlock_unlocked_triggers_banding_fault_even_at_nominal_shutter(self) -> None:
        res = p132.simulate_led_wall_ecs_capture(
            sensor_mode="4K120P",
            processor="MEGAPIXEL_HELIOS",
            scan_mux="1/8",
            pwm_hz=3840.0,
            shutter_hz=240.0,
            frame_rate_hz=120.0,
            genlock_locked=False,
        )
        self.assertFalse(res.passed)
        self.assertTrue(res.banding_fault_detected)
        self.assertGreater(res.luminance_banding_residual_pct, 18.0)
        self.assertIn("BLOCKED_LEDWALL_GENLOCK_UNLOCKED", res.violation_codes)

    def test_11_invalid_ecs_parameters_raise_domain_error(self) -> None:
        with self.assertRaises(p132.VpLedwallFreedArtnetError):
            p132.solve_fractional_ecs_shutter(sensor_mode="8K30P")
        with self.assertRaises(p132.VpLedwallFreedArtnetError):
            p132.solve_fractional_ecs_shutter(processor="UNKNOWN_WALL")
        with self.assertRaises(p132.VpLedwallFreedArtnetError):
            p132.solve_fractional_ecs_shutter(scan_mux="1/32")
        with self.assertRaises(p132.VpLedwallFreedArtnetError):
            p132.solve_fractional_ecs_shutter(pwm_hz=500.0)


class TestPillarBFreed0xD1LiveLinkBridge(unittest.TestCase):
    """Verify FreeD 0xD1 29-byte packet, checksum, 60/120Hz LiveLink & PL fallback."""

    def test_12_freed_0xd1_packet_is_29_bytes_with_0x40_minus_sum_checksum(self) -> None:
        pkt_hex = p132.encode_freed_d1_packet(
            camera_id=7,
            pan_deg=-45.25,
            tilt_deg=14.125,
            roll_deg=0.5,
            x_mm=2100.0,
            y_mm=-850.0,
            z_mm=1640.0,
            focus_encoder=0x123456,
            zoom_encoder=0x654321,
            iris_spare=0xABCD,
        )
        raw = bytes.fromhex(pkt_hex)
        self.assertEqual(len(raw), 29)
        self.assertEqual(raw[0], 0xD1)
        self.assertEqual(raw[1], 7)
        self.assertEqual(raw[28], (0x40 - sum(raw[:28])) & 0xFF)

        dec = p132.decode_freed_d1_packet(pkt_hex)
        self.assertTrue(dec["valid"])
        self.assertTrue(dec["checksum_valid"])
        self.assertAlmostEqual(dec["pan_deg"], -45.25, places=3)
        self.assertAlmostEqual(dec["tilt_deg"], 14.125, places=3)
        self.assertAlmostEqual(dec["x_mm"], 2100.0, places=2)
        self.assertAlmostEqual(dec["y_mm"], -850.0, places=2)
        self.assertEqual(dec["focus_encoder"], 0x123456)
        self.assertEqual(dec["zoom_encoder"], 0x654321)
        self.assertEqual(dec["iris_spare"], 0xABCD)

    def test_13_freed_emount_12pin_120hz_and_60hz_livelink_under_1p2ms(self) -> None:
        r120 = p132.bridge_emount_to_freed_livelink(
            lens_profile="SEL2470GM2_EMOUNT_12PIN",
            lens_12pin_present=True,
            focal_length_mm=50.0,
            focus_distance_m=3.2,
            f_stop=2.8,
            rate_hz=120.0,
            transport_driver="CDC_NCM_RTL8153",
            glass_to_engine_latency_ms=0.54,
        )
        self.assertTrue(r120.passed)
        self.assertEqual(r120.packet_bytes, 29)
        self.assertTrue(r120.checksum_valid)
        self.assertLess(r120.glass_to_engine_latency_ms, 1.2)
        self.assertEqual(r120.wf12_00342260_hits, 0)
        self.assertFalse(r120.neutral_encoder_fallback_active)

        r60 = p132.bridge_emount_to_freed_livelink(
            rate_hz=60.0,
            transport_driver="CDC_NCM_AX88179",
            glass_to_engine_latency_ms=0.72,
        )
        self.assertTrue(r60.passed)
        self.assertLess(r60.glass_to_engine_latency_ms, 1.2)

    def test_14_freed_unchipped_pl_lens_graceful_neutral_encoder_fallback(self) -> None:
        pl = p132.bridge_emount_to_freed_livelink(
            lens_profile="COOKE_S4_32MM_PL_UNCHIPPED",
            lens_12pin_present=False,
            rate_hz=60.0,
            transport_driver="CDC_NCM_RTL8153",
            glass_to_engine_latency_ms=0.61,
        )
        self.assertTrue(pl.passed)
        self.assertTrue(pl.neutral_encoder_fallback_active)
        self.assertEqual(pl.status, "VERIFIED_FREED_UNCHIPPED_PL_NEUTRAL_FALLBACK")
        self.assertEqual(pl.decoded_packet["focus_encoder"], 0x800000)
        self.assertEqual(pl.decoded_packet["zoom_encoder"], 0x800000)
        self.assertEqual(pl.decoded_packet["iris_spare"], 0x0000)
        self.assertEqual(pl.livelink_focal_length_mm, 0.0)

    def test_15_freed_bad_checksum_length_and_msg_type_rejected(self) -> None:
        bad_csum = p132.bridge_emount_to_freed_livelink(corrupt_checksum=True)
        self.assertFalse(bad_csum.passed)
        self.assertIn("BLOCKED_FREED_D1_CHECKSUM_MISMATCH", bad_csum.violation_codes)

        bad_len = p132.decode_freed_d1_packet("d10100")
        self.assertFalse(bad_len["valid"])
        self.assertEqual(bad_len["violation_code"], "BLOCKED_FREED_D1_BAD_LENGTH")

        bad_type = bytearray.fromhex(p132.encode_freed_d1_packet())
        bad_type[0] = 0xD2
        dec_type = p132.decode_freed_d1_packet(bad_type.hex())
        self.assertFalse(dec_type["valid"])
        self.assertEqual(dec_type["violation_code"], "BLOCKED_FREED_D1_BAD_MESSAGE_TYPE")

    def test_16_freed_wifi_p12_and_latency_exceeded_blocked(self) -> None:
        wifi = p132.bridge_emount_to_freed_livelink(transport_driver="WIFI_WLAN0")
        self.assertFalse(wifi.passed)
        self.assertIn("BLOCKED_P12_RF_OFF_VIOLATION_00342260", wifi.violation_codes)
        self.assertEqual(wifi.wf12_00342260_hits, 0)

        slow = p132.bridge_emount_to_freed_livelink(glass_to_engine_latency_ms=1.45)
        self.assertFalse(slow.passed)
        self.assertIn("BLOCKED_FREED_LATENCY_EXCEEDED", slow.violation_codes)

        with self.assertRaises(p132.VpLedwallFreedArtnetError):
            p132.bridge_emount_to_freed_livelink(rate_hz=48.0)


class TestPillarCArtNet4AndSacnLightingSync(unittest.TestCase):
    """Verify Art-Net 4 (OpDmx 0x5000 UDP 6454) & sACN (E1.31) VSYNC boundary sync."""

    def test_17_artnet4_opdmx_0x5000_udp_6454_roundtrip(self) -> None:
        pkt = p132.encode_artnet4_opdmx_packet(universe=3, sequence=9, dmx_slots=(255, 128, 64, 32, 16))
        dec = p132.decode_artnet4_opdmx_packet(pkt)
        self.assertTrue(dec["valid"])
        self.assertEqual(dec["protocol"], "ARTNET_4")
        self.assertEqual(dec["udp_port"], 6454)
        self.assertEqual(dec["opcode_hex"], "0x5000")
        self.assertEqual(dec["universe"], 3)
        self.assertEqual(dec["sequence"], 9)
        self.assertEqual(dec["dmx_length"], 6)

    def test_18_sacn_e131_packet_roundtrip(self) -> None:
        pkt = p132.encode_sacn_e131_packet(
            universe=5,
            sequence=17,
            priority=120,
            source_name="FX3-STAGE23-CTRL",
            dmx_slots=(255, 200, 100, 50),
        )
        dec = p132.decode_sacn_e131_packet(pkt)
        self.assertTrue(dec["valid"])
        self.assertEqual(dec["protocol"], "SACN_E131")
        self.assertEqual(dec["udp_port"], 5568)
        self.assertEqual(dec["universe"], 5)
        self.assertEqual(dec["sequence"], 17)
        self.assertEqual(dec["priority"], 120)
        self.assertEqual(dec["source_name"], "FX3-STAGE23-CTRL")
        self.assertEqual(dec["dmx_length"], 4)

    def test_19_artnet_and_sacn_vsync_boundary_sync_prevents_split_bands(self) -> None:
        an = p132.synchronize_dmx_flash_cue_to_vsync(
            protocol="ARTNET_4",
            transport_driver="CDC_NCM_RTL8153",
            sensor_mode="4K24P",
            incoming_phase_ms=6.6,
            boundary_sync_enabled=True,
            vsync_genlock_locked=True,
        )
        self.assertTrue(an.passed)
        self.assertEqual(an.aligned_fire_phase_ms, 0.0)
        self.assertFalse(an.half_frame_split_detected)
        self.assertEqual(an.flash_split_band_frames, 0)
        self.assertEqual(an.wf12_00342260_hits, 0)

        sc = p132.synchronize_dmx_flash_cue_to_vsync(
            protocol="SACN_E131",
            transport_driver="USB_RNDIS_WIRED",
            sensor_mode="4K120P",
            incoming_phase_ms=4.35,
            boundary_sync_enabled=True,
            vsync_genlock_locked=True,
        )
        self.assertTrue(sc.passed)
        self.assertEqual(sc.flash_split_band_frames, 0)

    def test_20_unsynced_mid_frame_flash_detects_half_frame_split_band(self) -> None:
        bad = p132.synchronize_dmx_flash_cue_to_vsync(
            protocol="ARTNET_4",
            transport_driver="CDC_NCM_RTL8153",
            sensor_mode="4K24P",
            incoming_phase_ms=6.6,
            boundary_sync_enabled=False,
            vsync_genlock_locked=True,
        )
        self.assertFalse(bad.passed)
        self.assertTrue(bad.half_frame_split_detected)
        self.assertEqual(bad.flash_split_band_frames, 1)
        self.assertIn("BLOCKED_IMX510_HALF_FRAME_FLASH_SPLIT_BAND", bad.violation_codes)

    def test_21_dmx_p12_wifi_off_and_bad_packet_headers_rejected(self) -> None:
        for rf in ("WIFI_WLAN0", "WIFI_DIRECT_P2P", "BT_PAN", "MODEM_CELLULAR"):
            res = p132.synchronize_dmx_flash_cue_to_vsync(transport_driver=rf)
            self.assertFalse(res.passed)
            self.assertIn("BLOCKED_P12_RF_OFF_VIOLATION_00342260", res.violation_codes)
            self.assertEqual(res.wf12_00342260_hits, 0)

        self.assertFalse(p132.decode_artnet4_opdmx_packet("00" * 24)["valid"])
        self.assertFalse(p132.decode_sacn_e131_packet("00" * 130)["valid"])


class TestPillarDG41G42GenlockAndHelicopterIbisHil(unittest.TestCase):
    """Verify G41 Genlock/Word-Clock & UV-Arc HIL and G42 Helicopter IBIS Resonance HIL."""

    def test_22_g41_valid_ltc_on_multi_terminal_passes_with_zero_isolation_trip(self) -> None:
        res = p132.simulate_g41_genlock_clash_and_uv_irradiance_hil(
            multi_terminal_signal="LTC_AUDIO_VALID",
            signal_vpp=2.0,
            signal_freq_hz=1920.0,
            uv_irradiance_mw_cm2=0.8,
            strobe_peak_lux=18_000.0,
        )
        self.assertTrue(res.passed)
        self.assertFalse(res.overvoltage_isolation_tripped)
        self.assertFalse(res.uv_irradiance_guard_tripped)
        self.assertEqual(res.cxd90057_pin_damage_events, 0)
        self.assertEqual(res.imx510_sensor_burn_events, 0)

    def test_23_g41_tri_level_genlock_on_ltc_pin_isolates_under_20us(self) -> None:
        res = p132.simulate_g41_genlock_clash_and_uv_irradiance_hil(
            multi_terminal_signal="TRI_LEVEL_GENLOCK",
            signal_vpp=0.6,
            signal_freq_hz=27_000_000.0,
        )
        self.assertFalse(res.passed)
        self.assertTrue(res.overvoltage_isolation_tripped)
        self.assertGreater(res.isolation_latency_us, 0.0)
        self.assertLess(res.isolation_latency_us, 20.0)
        self.assertEqual(res.cxd90057_pin_damage_events, 0)
        self.assertEqual(res.wdt_resets, 0)
        self.assertIn("BLOCKED_G41_GENLOCK_OR_WORDCLOCK_ON_LTC_ONLY_PIN", res.violation_codes)

    def test_24_g41_5v_ttl_word_clock_on_ltc_pin_isolates_under_20us(self) -> None:
        res = p132.simulate_g41_genlock_clash_and_uv_irradiance_hil(
            multi_terminal_signal="WORD_CLOCK_5V_TTL",
            signal_vpp=5.0,
            signal_freq_hz=48_000.0,
        )
        self.assertFalse(res.passed)
        self.assertTrue(res.overvoltage_isolation_tripped)
        self.assertLess(res.isolation_latency_us, 20.0)
        self.assertEqual(res.cxd90057_pin_damage_events, 0)
        self.assertIn("BLOCKED_G41_GENLOCK_OR_WORDCLOCK_ON_LTC_ONLY_PIN", res.violation_codes)

    def test_25_g41_close_range_uv_arc_and_strobe_irradiance_guard(self) -> None:
        res = p132.simulate_g41_genlock_clash_and_uv_irradiance_hil(
            multi_terminal_signal="LTC_AUDIO_VALID",
            uv_irradiance_mw_cm2=38.0,
            strobe_peak_lux=350_000.0,
        )
        self.assertFalse(res.passed)
        self.assertTrue(res.uv_irradiance_guard_tripped)
        self.assertEqual(res.imx510_sensor_burn_events, 0)
        self.assertIn("BLOCKED_G41_UV_ARC_STROBE_IRRADIANCE_EXCEEDED", res.violation_codes)

    def test_26_g42_helicopter_gt_1p8g_20_200hz_auto_parks_ibis_with_2000hz_rtmd(self) -> None:
        res = p132.simulate_g42_helicopter_ibis_resonance_hil(
            platform="HELICOPTER_AIRFRAME",
            vibration_g=2.65,
            resonance_freq_hz=48.0,
            auto_park_on_high_vib=True,
        )
        self.assertTrue(res.passed)
        self.assertTrue(res.high_vib_resonance_detected)
        self.assertEqual(res.ibis_state, "OFF_MECHANICAL_PARK")
        self.assertEqual(res.vcm_drive_ma, 0.0)
        self.assertTrue(res.rtmd_gyroflow_2000hz_active)
        self.assertTrue(res.cp_0x0400_park_dispatched)
        self.assertEqual(res.cp_mutation_bytes, 0)
        self.assertEqual(res.ibis_endstop_slam_events, 0)
        self.assertEqual(res.ibis_coil_thermal_runaway_events, 0)

    def test_27_g42_chase_car_arm_high_vib_autoparks_while_forced_active_blocked(self) -> None:
        chase = p132.simulate_g42_helicopter_ibis_resonance_hil(
            platform="CHASE_CAR_ARM",
            vibration_g=3.40,
            resonance_freq_hz=115.0,
            auto_park_on_high_vib=True,
        )
        self.assertTrue(chase.passed)
        self.assertEqual(chase.ibis_state, "OFF_MECHANICAL_PARK")
        self.assertEqual(chase.ibis_endstop_slam_events, 0)

        forced = p132.simulate_g42_helicopter_ibis_resonance_hil(
            platform="HELICOPTER_AIRFRAME",
            vibration_g=2.90,
            resonance_freq_hz=64.0,
            auto_park_on_high_vib=False,
        )
        self.assertFalse(forced.passed)
        self.assertEqual(forced.ibis_state, "EMERGENCY_PARK_LOCKED")
        self.assertIn("BLOCKED_G42_HIGH_VIB_IBIS_PARK_REQUIRED", forced.violation_codes)
        self.assertEqual(forced.ibis_endstop_slam_events, 0)
        self.assertEqual(forced.ibis_coil_thermal_runaway_events, 0)

    def test_28_g42_nominal_handheld_gimbal_keeps_requested_ibis_active(self) -> None:
        nom = p132.simulate_g42_helicopter_ibis_resonance_hil(
            platform="HANDHELD_GIMBAL",
            vibration_g=0.45,
            resonance_freq_hz=18.0,
            auto_park_on_high_vib=True,
            requested_ibis_mode="Active",
        )
        self.assertTrue(nom.passed)
        self.assertFalse(nom.high_vib_resonance_detected)
        self.assertEqual(nom.ibis_state, "Active")
        self.assertGreater(nom.vcm_drive_ma, 0.0)
        self.assertTrue(nom.rtmd_gyroflow_2000hz_active)

    def test_29_g41_g42_invalid_telemetry_raises_domain_error(self) -> None:
        with self.assertRaises(p132.VpLedwallFreedArtnetError):
            p132.simulate_g41_genlock_clash_and_uv_irradiance_hil(multi_terminal_signal="SDI_12G")
        with self.assertRaises(p132.VpLedwallFreedArtnetError):
            p132.simulate_g41_genlock_clash_and_uv_irradiance_hil(signal_vpp=-1.0)
        with self.assertRaises(p132.VpLedwallFreedArtnetError):
            p132.simulate_g42_helicopter_ibis_resonance_hil(platform="SUBMARINE")
        with self.assertRaises(p132.VpLedwallFreedArtnetError):
            p132.simulate_g42_helicopter_ibis_resonance_hil(vibration_g=-0.2)


class TestStage23SuiteIntegrationCliAndHygiene(unittest.TestCase):
    """Verify Stage 23 suite integration, CLI flags, runtime budgets & strict hygiene."""

    def test_30_pillar_a_b_c_d_evaluators_all_pass_independently(self) -> None:
        self.assertTrue(p132.evaluate_pillar_a_vp_ledwall_ecs()["passed"])
        self.assertTrue(p132.evaluate_pillar_b_freed_livelink()["passed"])
        self.assertTrue(p132.evaluate_pillar_c_artnet_sacn_sync()["passed"])
        self.assertTrue(p132.evaluate_pillar_d_g41_g42_hil()["passed"])

    def test_31_clean_room_audit_digest_reproducible_and_no_bytes_repr(self) -> None:
        rep1 = p132.run_phase132_vp_ledwall_freed_artnet_audit(force_clean_room=True)
        rep2 = p132.run_phase132_vp_ledwall_freed_artnet_audit(force_clean_room=True)
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
            ["--clean-room", "--ecs-matrix"],
            ["--clean-room", "--freed-matrix"],
            ["--clean-room", "--dmx-matrix"],
            ["--clean-room", "--hil-matrix"],
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = p132.main(argv)
            self.assertEqual(rc, 0, msg=f"CLI argv={argv} failed")
            self.assertTrue(buf.getvalue().strip())

    def test_33_standalone_json_cli_matches_run_audit(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = p132.main(["--clean-room", "--json"])
        self.assertEqual(rc, 0)
        parsed = json.loads(buf.getvalue())
        self.assertEqual(parsed["schema"], p132.PHASE_132_SCHEMA)
        self.assertTrue(parsed["all_checks_passed"])

    def test_34_suite_in_process_stage23_ge23_stages_and_skip_phase132_config(self) -> None:
        cfg_on = suite.CoEmulationConfig(force_clean_room=True)
        rep_on = suite.run_fx3_vm_coemulation_suite(cfg_on)
        self.assertTrue(rep_on["all_checks_passed"])
        self.assertIn("stage23_vp_ledwall_freed_artnet_hil", rep_on)
        self.assertTrue(rep_on["stage23_vp_ledwall_freed_artnet_hil"]["all_checks_passed"])

        stage_keys = [k for k in rep_on if re.match(r"^stage\d+_", k)]
        self.assertGreaterEqual(len(stage_keys), 23)

        cfg_skip = suite.CoEmulationConfig(
            force_clean_room=True,
            include_phase132_vp_ledwall_freed_artnet_hil=False,
        )
        rep_skip = suite.run_fx3_vm_coemulation_suite(cfg_skip)
        self.assertTrue(rep_skip["all_checks_passed"])
        self.assertNotIn("stage23_vp_ledwall_freed_artnet_hil", rep_skip)

    def test_35_suite_subprocess_summary_and_skip_phase132_flag(self) -> None:
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
        self.assertIn("vp_ledwall_freed_artnet=CLEAN_ROOM_SYNTHETIC", proc.stdout)

        proc_skip = subprocess.run(
            [
                "/usr/bin/python3",
                "-B",
                str(FX3_VM_DIR / "fx3_vm_coemulation_suite.py"),
                "--clean-room",
                "--skip-phase132",
                "--summary",
            ],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc_skip.returncode, 0, msg=proc_skip.stderr)
        self.assertNotIn("vp_ledwall_freed_artnet=", proc_skip.stdout)

    def test_36_23_stage_suite_clean_room_and_local_runtime_under_budget(self) -> None:
        t0 = time.monotonic()
        rep_clean = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig(force_clean_room=True))
        elapsed_clean = time.monotonic() - t0
        self.assertTrue(rep_clean["all_checks_passed"])
        self.assertLess(elapsed_clean, 0.70)

        t1 = time.monotonic()
        rep_mode = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig())
        elapsed_mode = time.monotonic() - t1
        self.assertTrue(rep_mode["all_checks_passed"])
        self.assertLess(elapsed_mode, 1.80)

    def test_37_stages_1_to_22_remain_intact_in_23_stage_report(self) -> None:
        rep = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig(force_clean_room=True))
        self.assertTrue(rep["stage1_coldboot_and_bt"]["all_checks_passed"])
        self.assertTrue(rep["stage2_dual_isa_cp_shooting"]["all_checks_passed"])
        self.assertTrue(rep["stage3_soft_gpe_hud_ramfb"]["all_checks_passed"])
        for idx in range(4, 24):
            matches = [k for k in rep if k.startswith(f"stage{idx}_")]
            self.assertEqual(len(matches), 1, msg=f"Missing or duplicate stage{idx}_* key")
            self.assertTrue(rep[matches[0]]["all_checks_passed"])

    def test_38_invalid_dmx_and_freed_hex_rejected_gracefully(self) -> None:
        self.assertFalse(p132.decode_freed_d1_packet("zzzz")["valid"])
        self.assertFalse(p132.decode_artnet4_opdmx_packet("zzzz")["valid"])
        self.assertFalse(p132.decode_sacn_e131_packet("zzzz")["valid"])
        with self.assertRaises(p132.VpLedwallFreedArtnetError):
            p132.encode_artnet4_opdmx_packet(dmx_slots=(255,))
        with self.assertRaises(p132.VpLedwallFreedArtnetError):
            p132.encode_sacn_e131_packet(dmx_slots=())

    def test_39_dmx_sync_invalid_protocol_or_negative_phase_raises_domain_error(self) -> None:
        with self.assertRaises(p132.VpLedwallFreedArtnetError):
            p132.synchronize_dmx_flash_cue_to_vsync(protocol="DMX512_RDM")
        with self.assertRaises(p132.VpLedwallFreedArtnetError):
            p132.synchronize_dmx_flash_cue_to_vsync(sensor_mode="2K_RAW")
        with self.assertRaises(p132.VpLedwallFreedArtnetError):
            p132.synchronize_dmx_flash_cue_to_vsync(incoming_phase_ms=-0.5)

    def test_40_source_hygiene_o_rdonly_and_no_write_flags_or_port_8768_or_raw_bytes(self) -> None:
        src = (FX3_VM_DIR / "vp_ledwall_freed_artnet_vib_emulator.py").read_text(encoding="utf-8")
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
