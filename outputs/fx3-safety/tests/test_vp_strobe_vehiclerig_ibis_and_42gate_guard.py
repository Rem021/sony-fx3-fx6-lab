"""Fast dual-mode unit tests for Phase 131 — Virtual Production DMX Strobe / UV-Arc
IMX510 Sensor Overload & External Tri-Level Sync / Multi-Terminal Backfeed Firewall
(Gate G41), Vehicle / Helicopter Hard-Mount Vibration (20..200 Hz) IBIS Voice-Coil
Thermal Resonance & Secondary Steel-Tether Guard (Gate G42), and Unified 42-Gate Master
Safety Preflight (`G01..G42`).
"""

from __future__ import annotations

import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import fx3_safety
from fx3_safety.__main__ import main as package_cli_main
from fx3_safety.master_16gate_preflight import DEFAULT_REPO_ROOT
from fx3_safety.monsoon_mishoe_cagetwist_and_40gate_guard import (
    STATUS_BLOCKED_BODY_QUARTER20_OVERTORQUE_THREAD_STRIP,
    STATUS_BLOCKED_UNCAPPED_MISHOE_RAIN_GALVANIC_SHORT,
    evaluate_40gate_preflight,
)
from fx3_safety.rig_groundloop_lensrail_and_20gate_guard import (
    STATUS_FAIL_OFFLINE_HARDWARE_NOT_ATTACHED,
)
from fx3_safety.vp_strobe_vehiclerig_ibis_and_42gate_guard import (
    ENGINE_RESONANCE_MIN_HZ,
    G41_GATE_CODE,
    G41_GATE_ID,
    G42_GATE_CODE,
    G42_GATE_ID,
    IBIS_MODE_OFF_MECHANICAL_PARK,
    IMX510_MAX_SAFE_PEAK_IRRADIANCE_W_CM2,
    LED_WALL_MIN_ALIAS_FREE_PWM_HZ,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    STATUS_BLOCKED_CLOSE_RANGE_ARC_OR_STROBE_SENSOR_HAZARD,
    STATUS_BLOCKED_DONOR_INTEGRITY,
    STATUS_BLOCKED_GENLOCK_TRILEVEL_INTO_FX3_LTC_TERMINAL,
    STATUS_BLOCKED_HARDMOUNT_HIGH_G_VIBRATION_NO_WIRE_ISOLATOR,
    STATUS_BLOCKED_IBIS_ACTIVE_UNDER_SUSTAINED_ENGINE_RESONANCE,
    STATUS_BLOCKED_LEDWALL_SCAN_ALIASING_NO_ECS_LOCK,
    STATUS_BLOCKED_PERSISTENT_EMMC_WRITE,
    STATUS_BLOCKED_VEHICLE_EXTERIOR_RIG_MISSING_SECONDARY_STEEL_TETHER,
    STATUS_BLOCKED_VEHICLERIG_IBIS_TELEMETRY_INVALID,
    STATUS_BLOCKED_VP_STROBE_GENLOCK_TELEMETRY_INVALID,
    STATUS_SAFE,
    STATUS_VERIFIED_G41,
    STATUS_VERIFIED_G42,
    STATUS_VERIFIED_SAFE,
    VEHICLE_EXTERIOR_MIN_STEEL_TETHER_KG,
    VEHICLE_EXTERIOR_MIN_SUCTION_CUPS,
    VIBRATION_IBIS_PARK_MAX_RMS_G,
    VIBRATION_WIRE_ISOLATOR_MAX_RMS_G,
    VP_STROBE_VEHICLERIG_42GATE_SCHEMA,
    VP_STROBE_VEHICLERIG_42GATE_VERSION,
    audit_phase131_donor_contracts,
    compute_led_wall_ecs_beat_ratio,
    compute_tether_static_safety_factor,
    estimate_ibis_voice_coil_excursion_mm,
    estimate_imx510_microlens_flash_temp_rise_c,
    evaluate_42_master_safety_gates,
    evaluate_42gate_preflight,
    evaluate_g41_vp_strobe_and_genlock,
    evaluate_g42_vehiclerig_ibis_and_tether,
    main as module_cli_main,
    verify_vehiclerig_vibration_ibis_and_tether_guard,
    verify_vp_strobe_uvarc_and_genlock_firewall,
)


class VpStrobeVehicleRigIbisAnd42GateGuardTests(unittest.TestCase):
    # --- 1. Hard Redlines, Package Exports & O_RDONLY Donor Audit ---

    def test_01_hard_locked_redlines_and_package_exports(self) -> None:
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(PERSISTENT_WRITE_RELEASE)
        self.assertEqual(
            VP_STROBE_VEHICLERIG_42GATE_SCHEMA,
            "fx3-vp-strobe-vehiclerig-ibis-42gate-preflight-v1",
        )
        self.assertEqual(VP_STROBE_VEHICLERIG_42GATE_VERSION, "1.0.0")
        for sym in (
            "VP_STROBE_VEHICLERIG_42GATE_SCHEMA",
            "G41_GATE_ID",
            "G41_GATE_CODE",
            "G42_GATE_ID",
            "G42_GATE_CODE",
            "STATUS_BLOCKED_CLOSE_RANGE_ARC_OR_STROBE_SENSOR_HAZARD",
            "STATUS_BLOCKED_GENLOCK_TRILEVEL_INTO_FX3_LTC_TERMINAL",
            "STATUS_BLOCKED_LEDWALL_SCAN_ALIASING_NO_ECS_LOCK",
            "STATUS_BLOCKED_HARDMOUNT_HIGH_G_VIBRATION_NO_WIRE_ISOLATOR",
            "STATUS_BLOCKED_IBIS_ACTIVE_UNDER_SUSTAINED_ENGINE_RESONANCE",
            "STATUS_BLOCKED_VEHICLE_EXTERIOR_RIG_MISSING_SECONDARY_STEEL_TETHER",
            "audit_phase131_donor_contracts",
            "estimate_imx510_microlens_flash_temp_rise_c",
            "compute_led_wall_ecs_beat_ratio",
            "estimate_ibis_voice_coil_excursion_mm",
            "compute_tether_static_safety_factor",
            "verify_vp_strobe_uvarc_and_genlock_firewall",
            "verify_vehiclerig_vibration_ibis_and_tether_guard",
            "evaluate_g41_vp_strobe_and_genlock",
            "evaluate_g42_vehiclerig_ibis_and_tether",
            "evaluate_42gate_preflight",
            "evaluate_42_master_safety_gates",
            "vp_strobe_vehiclerig_ibis_and_42gate_guard",
        ):
            self.assertIn(sym, fx3_safety.__all__)
            self.assertTrue(hasattr(fx3_safety, sym))
        # Prior Phase exports must remain intact
        self.assertEqual(fx3_safety.FAN_MODE_AUTO1, "AUTO1")
        self.assertEqual(
            fx3_safety.STATUS_BLOCKED_DONOR_INTEGRITY,
            "BLOCKED_USBLAN_PTPIP_DONOR_INTEGRITY_MISMATCH",
        )
        self.assertEqual(
            fx3_safety.MONSOON_MISHOE_CAGETWIST_40GATE_SCHEMA,
            "fx3-monsoon-mishoe-cagetwist-40gate-preflight-v1",
        )

    def test_02_donor_audit_o_rdonly_and_clean_room_fallback(self) -> None:
        observed_flags = []
        orig_open = os.open

        def spy_open(path, flags, *args, **kwargs):
            observed_flags.append((str(path), flags))
            return orig_open(path, flags, *args, **kwargs)

        with patch("os.open", side_effect=spy_open):
            res_default = audit_phase131_donor_contracts()
        self.assertTrue(res_default.valid)
        self.assertEqual(res_default.status, STATUS_VERIFIED_SAFE)
        self.assertEqual(res_default.access_mode, "O_RDONLY")
        self.assertEqual(len(res_default.missing_markers), 0)
        self.assertTrue(res_default.multi_if_lanc_tokens_verified)
        self.assertTrue(res_default.usb_multiport_tokens_verified)
        self.assertTrue(res_default.ext_cmd_svc_tokens_verified)
        for path, flags in observed_flags:
            if any(
                k in path
                for k in (
                    "libInfraMultiIF",
                    "libInfraLanc",
                    "libUsbControl",
                    "libInfraExtCmdSvc",
                )
            ):
                self.assertEqual(
                    flags & os.O_ACCMODE,
                    os.O_RDONLY,
                    f"Non-O_RDONLY open on {path}",
                )

        res_clean = audit_phase131_donor_contracts(force_clean_room=True)
        self.assertTrue(res_clean.valid)
        self.assertEqual(res_clean.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(res_clean.files_inspected, 0)
        self.assertEqual(len(res_clean.sha256_by_artifact), 6)

    def test_03_donor_audit_blocks_integrity_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            fx3_lib = (
                tmp
                / "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib"
            )
            fx6_lib = (
                tmp
                / "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib"
            )
            fx3_lib.mkdir(parents=True)
            fx6_lib.mkdir(parents=True)
            for name in ("libUsbControl.so", "libInfraExtCmdSvc.so"):
                (fx3_lib / name).write_bytes(b"corrupt")
                (fx6_lib / name).write_bytes(b"corrupt")
            for name in ("libInfraMultiIF.so", "libInfraLanc.so"):
                (fx6_lib / name).write_bytes(b"corrupt")
            res = audit_phase131_donor_contracts(work_root=tmp, force_clean_room=False)
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_DONOR_INTEGRITY)
        self.assertEqual(len(res.missing_markers), 6)
        self.assertFalse(res.multi_if_lanc_tokens_verified)
        self.assertFalse(res.usb_multiport_tokens_verified)
        self.assertFalse(res.ext_cmd_svc_tokens_verified)

    def test_04_donor_audit_clean_room_and_missing_work_root_fallback(self) -> None:
        res_clean = audit_phase131_donor_contracts(
            force_clean_room=True, include_large_binaries=True
        )
        self.assertTrue(res_clean.valid)
        self.assertFalse(res_clean.large_binaries_scanned)

        with tempfile.TemporaryDirectory() as empty_dir:
            res_absent = audit_phase131_donor_contracts(
                work_root=Path(empty_dir), force_clean_room=False
            )
        self.assertTrue(res_absent.valid)
        self.assertEqual(res_absent.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(res_absent.files_inspected, 0)

    # --- 2. Optical / Sync & Vibration / Tether Physics Helpers ---

    def test_05_imx510_microlens_flash_temp_rise_and_ecs_beat_helpers(self) -> None:
        rise_unfiltered = estimate_imx510_microlens_flash_temp_rise_c(0.5, 4.0)
        rise_nd09 = estimate_imx510_microlens_flash_temp_rise_c(
            0.5, 4.0, nd_optical_density=0.9
        )
        self.assertGreater(rise_unfiltered, rise_nd09)
        self.assertAlmostEqual(
            compute_led_wall_ecs_beat_ratio(3840.0, 24.0), 160.0, places=6
        )
        with self.assertRaises(ValueError):
            estimate_imx510_microlens_flash_temp_rise_c(-0.1, 2.0)
        with self.assertRaises(ValueError):
            estimate_imx510_microlens_flash_temp_rise_c(0.1, float("nan"))
        with self.assertRaises(ValueError):
            compute_led_wall_ecs_beat_ratio(1920.0, 0.0)

    def test_06_ibis_excursion_and_tether_safety_factor_helpers(self) -> None:
        disp_hard = estimate_ibis_voice_coil_excursion_mm(
            2.5, 20.0, isolator_transmissibility=1.0
        )
        disp_iso = estimate_ibis_voice_coil_excursion_mm(
            2.5, 20.0, isolator_transmissibility=0.25
        )
        self.assertGreater(disp_hard, disp_iso)
        self.assertAlmostEqual(
            compute_tether_static_safety_factor(35.0, 2.0, peak_shock_g=5.0),
            3.5,
            places=6,
        )
        with self.assertRaises(ValueError):
            estimate_ibis_voice_coil_excursion_mm(-1.0, 25.0)
        with self.assertRaises(ValueError):
            estimate_ibis_voice_coil_excursion_mm(1.0, 0.0)
        with self.assertRaises(ValueError):
            compute_tether_static_safety_factor(25.0, 0.0)

    # --- 3. Gate G41 — VP Strobe / UV-Arc IMX510 & Tri-Level Genlock Firewall ---

    def test_07_g41_default_safe_profile_passes(self) -> None:
        res = verify_vp_strobe_uvarc_and_genlock_firewall()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_SAFE)
        self.assertEqual(res.violation_codes, ())
        self.assertTrue(res.arc_strobe_irradiance_safe)
        self.assertTrue(res.multiterminal_genlock_safe)
        self.assertTrue(res.ledwall_ecs_sync_safe)
        self.assertFalse(res.persistent_emmc_writes_authorized)

    def test_08_g41_blocks_close_range_strobe_irradiance_and_unfiltered_uvarc(self) -> None:
        res_strobe = verify_vp_strobe_uvarc_and_genlock_firewall(
            vp_profile="CLOSE_RANGE_DMX_XENON_STROBE",
            peak_irradiance_w_cm2=0.52,
        )
        self.assertFalse(res_strobe.valid)
        self.assertFalse(res_strobe.arc_strobe_irradiance_safe)
        self.assertEqual(
            res_strobe.status, STATUS_BLOCKED_CLOSE_RANGE_ARC_OR_STROBE_SENSOR_HAZARD
        )

        res_uvarc = verify_vp_strobe_uvarc_and_genlock_firewall(
            vp_profile="UNFILTERED_ARC_WELDER_STAGE",
            peak_irradiance_w_cm2=0.20,
            uv_arc_welding_or_pyro_scene=True,
            uv_ir_cut_and_protective_nd_installed=False,
        )
        self.assertFalse(res_uvarc.valid)
        self.assertEqual(
            res_uvarc.status, STATUS_BLOCKED_CLOSE_RANGE_ARC_OR_STROBE_SENSOR_HAZARD
        )

        # Exact 0.35 W/cm^2 boundary passes when UV-IR cut + protective ND is installed
        res_edge = verify_vp_strobe_uvarc_and_genlock_firewall(
            peak_irradiance_w_cm2=IMX510_MAX_SAFE_PEAK_IRRADIANCE_W_CM2,
            uv_arc_welding_or_pyro_scene=True,
            uv_ir_cut_and_protective_nd_installed=True,
        )
        self.assertTrue(res_edge.valid)
        self.assertGreaterEqual(len(res_edge.warnings), 1)

    def test_09_g41_blocks_trilevel_blackburst_and_wordclock_into_fx3_ltc_terminal(
        self,
    ) -> None:
        for bad_sig in ("TRILEVEL_GENLOCK", "BLACKBURST_PAL_NTSC", "WORDCLOCK_5V_TTL"):
            res = verify_vp_strobe_uvarc_and_genlock_firewall(
                bnc_sync_signal_type=bad_sig,
                connected_to_fx3_multiterminal=True,
            )
            self.assertFalse(res.valid)
            self.assertFalse(res.multiterminal_genlock_safe)
            self.assertEqual(
                res.status, STATUS_BLOCKED_GENLOCK_TRILEVEL_INTO_FX3_LTC_TERMINAL
            )

        for ok_sig in ("NONE", "LTC_SMPTE_UNBALANCED", "LANC_REMOTE"):
            res_ok = verify_vp_strobe_uvarc_and_genlock_firewall(
                bnc_sync_signal_type=ok_sig,
                connected_to_fx3_multiterminal=True,
            )
            self.assertTrue(res_ok.valid)

    def test_10_g41_blocks_ledwall_low_pwm_aliasing_without_ecs_lock(self) -> None:
        res_bad = verify_vp_strobe_uvarc_and_genlock_firewall(
            led_volume_active=True,
            led_pwm_refresh_hz=960.0,
            ecs_fractional_shutter_locked=False,
        )
        self.assertFalse(res_bad.valid)
        self.assertFalse(res_bad.ledwall_ecs_sync_safe)
        self.assertEqual(
            res_bad.status, STATUS_BLOCKED_LEDWALL_SCAN_ALIASING_NO_ECS_LOCK
        )

        # Exact 1920.0 Hz boundary passes even without ECS lock
        res_edge = verify_vp_strobe_uvarc_and_genlock_firewall(
            led_volume_active=True,
            led_pwm_refresh_hz=LED_WALL_MIN_ALIAS_FREE_PWM_HZ,
            ecs_fractional_shutter_locked=False,
        )
        self.assertTrue(res_edge.valid)

        # Low PWM passes when ECS fractional shutter is locked
        res_ecs = verify_vp_strobe_uvarc_and_genlock_firewall(
            led_volume_active=True,
            led_pwm_refresh_hz=960.0,
            ecs_fractional_shutter_locked=True,
        )
        self.assertTrue(res_ecs.valid)
        self.assertGreaterEqual(len(res_ecs.warnings), 1)

    def test_11_g41_rejects_invalid_telemetry_and_persistent_emmc_write(self) -> None:
        for kw in (
            {"peak_irradiance_w_cm2": -0.01},
            {"peak_irradiance_w_cm2": float("nan")},
            {"pulse_duration_ms": -1.0},
            {"nd_optical_density": -0.3},
            {"led_pwm_refresh_hz": 0.0},
            {"shutter_rate_hz": float("inf")},
            {"bnc_sync_signal_type": "UNKNOWN_SYNC"},
        ):
            res_bad = verify_vp_strobe_uvarc_and_genlock_firewall(**kw)
            self.assertFalse(res_bad.valid)
            self.assertEqual(
                res_bad.status, STATUS_BLOCKED_VP_STROBE_GENLOCK_TELEMETRY_INVALID
            )

        res_emmc = verify_vp_strobe_uvarc_and_genlock_firewall(
            request_persistent_emmc_writes=True
        )
        self.assertFalse(res_emmc.valid)
        self.assertEqual(res_emmc.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        self.assertFalse(res_emmc.persistent_emmc_writes_authorized)

    def test_12_g41_accumulates_all_three_violations_deterministically(self) -> None:
        res = verify_vp_strobe_uvarc_and_genlock_firewall(
            peak_irradiance_w_cm2=0.80,
            uv_arc_welding_or_pyro_scene=True,
            uv_ir_cut_and_protective_nd_installed=False,
            bnc_sync_signal_type="TRILEVEL_GENLOCK",
            connected_to_fx3_multiterminal=True,
            led_volume_active=True,
            led_pwm_refresh_hz=720.0,
            ecs_fractional_shutter_locked=False,
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            set(res.violation_codes),
            {
                STATUS_BLOCKED_CLOSE_RANGE_ARC_OR_STROBE_SENSOR_HAZARD,
                STATUS_BLOCKED_GENLOCK_TRILEVEL_INTO_FX3_LTC_TERMINAL,
                STATUS_BLOCKED_LEDWALL_SCAN_ALIASING_NO_ECS_LOCK,
            },
        )

    # --- 4. Gate G42 — Vehicle / Aerial Vibration, IBIS Park & Steel Tether ---

    def test_13_g42_default_safe_profile_passes(self) -> None:
        res = verify_vehiclerig_vibration_ibis_and_tether_guard()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_SAFE)
        self.assertEqual(res.violation_codes, ())
        self.assertTrue(res.hardmount_wire_isolator_safe)
        self.assertTrue(res.ibis_resonance_park_safe)
        self.assertTrue(res.exterior_steel_tether_safe)
        self.assertFalse(res.persistent_emmc_writes_authorized)

    def test_14_g42_blocks_hardmount_high_g_vibration_without_wire_isolator(
        self,
    ) -> None:
        res_bad = verify_vehiclerig_vibration_ibis_and_tether_guard(
            rig_profile="MOTORCYCLE_CHASSIS_HARDMOUNT",
            vibration_rms_g=2.6,
            dominant_vibration_hz=28.0,
            wire_rope_or_elastomer_isolator_stage=False,
        )
        self.assertFalse(res_bad.valid)
        self.assertFalse(res_bad.hardmount_wire_isolator_safe)
        self.assertEqual(
            res_bad.status, STATUS_BLOCKED_HARDMOUNT_HIGH_G_VIBRATION_NO_WIRE_ISOLATOR
        )

        # Exact 1.8 g boundary passes
        res_edge = verify_vehiclerig_vibration_ibis_and_tether_guard(
            vibration_rms_g=VIBRATION_WIRE_ISOLATOR_MAX_RMS_G,
            dominant_vibration_hz=28.0,
            wire_rope_or_elastomer_isolator_stage=False,
        )
        self.assertTrue(res_edge.valid)

        # Wire-rope isolator stage mitigates 2.8 g vibration when IBIS is parked
        res_iso = verify_vehiclerig_vibration_ibis_and_tether_guard(
            vibration_rms_g=2.8,
            dominant_vibration_hz=60.0,
            wire_rope_or_elastomer_isolator_stage=True,
            ibis_steadyshot_mode=IBIS_MODE_OFF_MECHANICAL_PARK,
        )
        self.assertTrue(res_iso.valid)

    def test_15_g42_blocks_active_ibis_under_sustained_engine_resonance(self) -> None:
        for bad_mode in ("STANDARD", "ACTIVE", "DYNAMIC_ACTIVE"):
            res_bad = verify_vehiclerig_vibration_ibis_and_tether_guard(
                vibration_rms_g=1.5,
                dominant_vibration_hz=55.0,
                wire_rope_or_elastomer_isolator_stage=True,
                ibis_steadyshot_mode=bad_mode,
            )
            self.assertFalse(res_bad.valid)
            self.assertFalse(res_bad.ibis_resonance_park_safe)
            self.assertEqual(
                res_bad.status,
                STATUS_BLOCKED_IBIS_ACTIVE_UNDER_SUSTAINED_ENGINE_RESONANCE,
            )

        # Mechanical park + Gyroflow RTMD passes
        res_parked = verify_vehiclerig_vibration_ibis_and_tether_guard(
            vibration_rms_g=1.5,
            dominant_vibration_hz=ENGINE_RESONANCE_MIN_HZ,
            wire_rope_or_elastomer_isolator_stage=True,
            ibis_steadyshot_mode=IBIS_MODE_OFF_MECHANICAL_PARK,
            gyroflow_rtmd_logging_enabled=True,
        )
        self.assertTrue(res_parked.valid)

    def test_16_g42_blocks_exterior_mount_missing_steel_tether_or_suction_cups(
        self,
    ) -> None:
        res_weak_tether = verify_vehiclerig_vibration_ibis_and_tether_guard(
            vehicle_or_aerial_exterior_mount=True,
            secondary_steel_safety_cable_rated_kg=15.0,
            suction_cup_count=3,
        )
        self.assertFalse(res_weak_tether.valid)
        self.assertFalse(res_weak_tether.exterior_steel_tether_safe)
        self.assertEqual(
            res_weak_tether.status,
            STATUS_BLOCKED_VEHICLE_EXTERIOR_RIG_MISSING_SECONDARY_STEEL_TETHER,
        )

        res_few_cups = verify_vehiclerig_vibration_ibis_and_tether_guard(
            vehicle_or_aerial_exterior_mount=True,
            secondary_steel_safety_cable_rated_kg=30.0,
            suction_cup_count=2,
        )
        self.assertFalse(res_few_cups.valid)
        self.assertEqual(
            res_few_cups.status,
            STATUS_BLOCKED_VEHICLE_EXTERIOR_RIG_MISSING_SECONDARY_STEEL_TETHER,
        )

        # Exact 25.0 kg & 3 suction cups passes
        res_ok = verify_vehiclerig_vibration_ibis_and_tether_guard(
            vehicle_or_aerial_exterior_mount=True,
            secondary_steel_safety_cable_rated_kg=VEHICLE_EXTERIOR_MIN_STEEL_TETHER_KG,
            suction_cup_count=VEHICLE_EXTERIOR_MIN_SUCTION_CUPS,
        )
        self.assertTrue(res_ok.valid)
        self.assertGreaterEqual(len(res_ok.warnings), 1)

    def test_17_g42_rejects_invalid_telemetry_and_persistent_emmc_write(self) -> None:
        for kw in (
            {"vibration_rms_g": -0.2},
            {"vibration_rms_g": float("nan")},
            {"dominant_vibration_hz": 0.0},
            {"secondary_steel_safety_cable_rated_kg": -5.0},
            {"suction_cup_count": -1},
            {"suction_cup_count": True},
            {"camera_rig_mass_kg": 0.0},
            {"ibis_steadyshot_mode": "UNKNOWN_IBIS"},
        ):
            res_bad = verify_vehiclerig_vibration_ibis_and_tether_guard(**kw)
            self.assertFalse(res_bad.valid)
            self.assertEqual(
                res_bad.status, STATUS_BLOCKED_VEHICLERIG_IBIS_TELEMETRY_INVALID
            )

        res_emmc = verify_vehiclerig_vibration_ibis_and_tether_guard(
            request_persistent_emmc_writes=True
        )
        self.assertFalse(res_emmc.valid)
        self.assertEqual(res_emmc.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        self.assertFalse(res_emmc.persistent_emmc_writes_authorized)

    def test_18_g42_accumulates_all_three_violations_deterministically(self) -> None:
        res = verify_vehiclerig_vibration_ibis_and_tether_guard(
            vibration_rms_g=2.9,
            dominant_vibration_hz=85.0,
            wire_rope_or_elastomer_isolator_stage=False,
            ibis_steadyshot_mode="ACTIVE",
            vehicle_or_aerial_exterior_mount=True,
            secondary_steel_safety_cable_rated_kg=10.0,
            suction_cup_count=1,
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            set(res.violation_codes),
            {
                STATUS_BLOCKED_HARDMOUNT_HIGH_G_VIBRATION_NO_WIRE_ISOLATOR,
                STATUS_BLOCKED_IBIS_ACTIVE_UNDER_SUSTAINED_ENGINE_RESONANCE,
                STATUS_BLOCKED_VEHICLE_EXTERIOR_RIG_MISSING_SECONDARY_STEEL_TETHER,
            },
        )

    # --- 5. Gate G41 & G42 Evaluators & Unified 42-Gate Master Preflight ---

    def test_19_g41_and_g42_verdicts_dual_mode(self) -> None:
        v41, r41 = evaluate_g41_vp_strobe_and_genlock(force_clean_room=True)
        self.assertTrue(v41.passed)
        self.assertEqual(v41.gate_id, G41_GATE_ID)
        self.assertEqual(v41.gate_code, G41_GATE_CODE)
        self.assertEqual(v41.status, STATUS_VERIFIED_G41)
        self.assertFalse(r41.persistent_emmc_writes_authorized)

        v42, r42 = evaluate_g42_vehiclerig_ibis_and_tether(force_clean_room=True)
        self.assertTrue(v42.passed)
        self.assertEqual(v42.gate_id, G42_GATE_ID)
        self.assertEqual(v42.gate_code, G42_GATE_CODE)
        self.assertEqual(v42.status, STATUS_VERIFIED_G42)
        self.assertFalse(r42.persistent_emmc_writes_authorized)

    def test_20_42gate_offline_default_39_of_42_and_g10_g12_fail_offline(self) -> None:
        rep = evaluate_42gate_preflight(DEFAULT_REPO_ROOT, force_clean_room=True)
        self.assertEqual(rep.schema, VP_STROBE_VEHICLERIG_42GATE_SCHEMA)
        self.assertGreaterEqual(len(rep.gates), 42)
        self.assertGreaterEqual(rep.summary["total_gates"], 42)
        self.assertGreaterEqual(rep.summary["verified_gates"], 39)
        self.assertEqual(rep.summary["blocked_or_pending_gates"], 3)
        self.assertTrue(rep.offline_39_gates_verified)
        self.assertFalse(rep.all_42_gates_verified)
        self.assertFalse(rep.dry_run_rehearsal_only)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.persistent_write_release)
        self.assertEqual(rep.status, "VERIFIED_39_OF_42_AWAITING_PHYSICAL_TIER0")
        for idx in (9, 10, 11):
            self.assertFalse(rep.gates[idx]["passed"])
            self.assertEqual(
                rep.gates[idx]["status"], STATUS_FAIL_OFFLINE_HARDWARE_NOT_ATTACHED
            )

    def test_21_42gate_dry_run_simulated_backup_42_of_42_and_redlines_locked(
        self,
    ) -> None:
        rep = evaluate_42gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
        )
        self.assertGreaterEqual(len(rep.gates), 42)
        self.assertGreaterEqual(rep.summary["verified_gates"], 42)
        self.assertEqual(rep.summary["blocked_or_pending_gates"], 0)
        self.assertEqual(rep.summary["g01_to_g12_verified"], 12)
        self.assertEqual(rep.summary["g13_to_g40_verified"], 28)
        self.assertEqual(rep.summary["g41_to_g42_verified"], 2)
        self.assertTrue(rep.all_42_gates_verified)
        self.assertTrue(rep.dry_run_rehearsal_only)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.persistent_write_release)
        self.assertEqual(rep.status, "VERIFIED_ALL_42_GATES_DRY_RUN_SIMULATED_BACKUP")
        self.assertTrue(all(g["passed"] for g in rep.gates))

    def test_22_42gate_propagates_g41_strobe_genlock_and_ecs_failures(self) -> None:
        rep_strobe = evaluate_42gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            vp_strobe_genlock_kwargs={"peak_irradiance_w_cm2": 0.65},
        )
        self.assertFalse(rep_strobe.all_42_gates_verified)
        self.assertFalse(rep_strobe.g41_to_g42_all_passed)
        self.assertFalse(rep_strobe.gates[40]["passed"])
        self.assertEqual(
            rep_strobe.status, STATUS_BLOCKED_CLOSE_RANGE_ARC_OR_STROBE_SENSOR_HAZARD
        )

        rep_genlock = evaluate_42gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            vp_strobe_genlock_kwargs={"bnc_sync_signal_type": "TRILEVEL_GENLOCK"},
        )
        self.assertFalse(rep_genlock.all_42_gates_verified)
        self.assertEqual(
            rep_genlock.status, STATUS_BLOCKED_GENLOCK_TRILEVEL_INTO_FX3_LTC_TERMINAL
        )

        rep_ecs = evaluate_42gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            vp_strobe_genlock_kwargs={
                "led_volume_active": True,
                "led_pwm_refresh_hz": 1200.0,
                "ecs_fractional_shutter_locked": False,
            },
        )
        self.assertFalse(rep_ecs.all_42_gates_verified)
        self.assertEqual(
            rep_ecs.status, STATUS_BLOCKED_LEDWALL_SCAN_ALIASING_NO_ECS_LOCK
        )

    def test_23_42gate_propagates_g42_vibration_ibis_and_tether_failures(self) -> None:
        rep_vib = evaluate_42gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            vehiclerig_ibis_kwargs={
                "vibration_rms_g": 2.4,
                "wire_rope_or_elastomer_isolator_stage": False,
            },
        )
        self.assertFalse(rep_vib.all_42_gates_verified)
        self.assertFalse(rep_vib.gates[41]["passed"])
        self.assertEqual(
            rep_vib.status, STATUS_BLOCKED_HARDMOUNT_HIGH_G_VIBRATION_NO_WIRE_ISOLATOR
        )

        rep_ibis = evaluate_42gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            vehiclerig_ibis_kwargs={
                "vibration_rms_g": 1.6,
                "dominant_vibration_hz": 50.0,
                "ibis_steadyshot_mode": "ACTIVE",
            },
        )
        self.assertFalse(rep_ibis.all_42_gates_verified)
        self.assertEqual(
            rep_ibis.status,
            STATUS_BLOCKED_IBIS_ACTIVE_UNDER_SUSTAINED_ENGINE_RESONANCE,
        )

        rep_tether = evaluate_42gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            vehiclerig_ibis_kwargs={
                "vehicle_or_aerial_exterior_mount": True,
                "secondary_steel_safety_cable_rated_kg": 10.0,
            },
        )
        self.assertFalse(rep_tether.all_42_gates_verified)
        self.assertEqual(
            rep_tether.status,
            STATUS_BLOCKED_VEHICLE_EXTERIOR_RIG_MISSING_SECONDARY_STEEL_TETHER,
        )

    def test_24_42gate_propagates_g39_g40_and_emmc_redline(self) -> None:
        rep_g39_g40 = evaluate_42gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            monsoon_mishoe_kwargs={
                "precipitation_mm_hr": 5.0,
                "mi_shoe_weather_cap_installed": False,
            },
            cagetwist_xlrh1_kwargs={"body_thread_fastener_torque_nm": 4.2},
        )
        self.assertFalse(rep_g39_g40.all_42_gates_verified)
        self.assertFalse(rep_g39_g40.gates[38]["passed"])
        self.assertFalse(rep_g39_g40.gates[39]["passed"])
        self.assertEqual(
            rep_g39_g40.gates[38]["status"],
            STATUS_BLOCKED_UNCAPPED_MISHOE_RAIN_GALVANIC_SHORT,
        )
        self.assertEqual(
            rep_g39_g40.gates[39]["status"],
            STATUS_BLOCKED_BODY_QUARTER20_OVERTORQUE_THREAD_STRIP,
        )
        self.assertEqual(
            rep_g39_g40.status, STATUS_BLOCKED_UNCAPPED_MISHOE_RAIN_GALVANIC_SHORT
        )

        rep_emmc = evaluate_42gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            request_persistent_emmc_writes=True,
        )
        self.assertFalse(rep_emmc.all_42_gates_verified)
        self.assertFalse(rep_emmc.offline_39_gates_verified)
        self.assertFalse(rep_emmc.overall_ready_for_hardware_attach)
        self.assertFalse(rep_emmc.persistent_emmc_writes_authorized)
        self.assertEqual(rep_emmc.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)

    def test_25_42gate_preserves_g01_to_g40_untouched(self) -> None:
        r40 = evaluate_40gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
        )
        r42 = evaluate_42gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
        )
        self.assertGreaterEqual(len(r40.gates), 40)
        self.assertGreaterEqual(len(r42.gates), 42)
        self.assertEqual(
            [g["gate_id"] for g in r40.gates],
            [g["gate_id"] for g in r42.gates[:40]],
        )
        self.assertEqual(
            [g["status"] for g in r40.gates],
            [g["status"] for g in r42.gates[:40]],
        )

    def test_26_serialized_json_contains_zero_raw_bytes_repr(self) -> None:
        rep = evaluate_42gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
        )
        rendered = json.dumps(rep.to_dict(), ensure_ascii=False)
        self.assertNotRegex(rendered, r'(?<![0-9A-Za-z_/.-])b[\x27"]')

    def test_27_cli_verify_42_gates_offline_and_dry_run_json(self) -> None:
        buf_off = io.StringIO()
        with contextlib.redirect_stdout(buf_off):
            rc_off = package_cli_main(["verify-42-gates", "--clean-room", "--json"])
        self.assertEqual(rc_off, 0)
        p_off = json.loads(buf_off.getvalue())
        self.assertEqual(p_off["schema"], VP_STROBE_VEHICLERIG_42GATE_SCHEMA)
        self.assertGreaterEqual(p_off["summary"]["verified_gates"], 39)
        self.assertFalse(p_off["dry_run_rehearsal_only"])
        self.assertFalse(p_off["overall_ready_for_hardware_attach"])
        self.assertFalse(p_off["persistent_emmc_writes_authorized"])

        buf_dry = io.StringIO()
        with contextlib.redirect_stdout(buf_dry):
            rc_dry = package_cli_main(
                ["verify-42-gates", "--clean-room", "--dry-run-simulated-backup", "--json"]
            )
        self.assertEqual(rc_dry, 0)
        p_dry = json.loads(buf_dry.getvalue())
        self.assertGreaterEqual(p_dry["summary"]["verified_gates"], 42)
        self.assertTrue(p_dry["all_42_gates_verified"])
        self.assertTrue(p_dry["dry_run_rehearsal_only"])
        self.assertFalse(p_dry["overall_ready_for_hardware_attach"])
        self.assertFalse(p_dry["persistent_emmc_writes_authorized"])

    def test_28_cli_verify_42_gates_summary_and_failure_exit_code(self) -> None:
        buf_mod = io.StringIO()
        with contextlib.redirect_stdout(buf_mod):
            rc_mod = module_cli_main(["--clean-room"])
        self.assertEqual(rc_mod, 0)
        out = buf_mod.getvalue()
        self.assertIn("verified=39/42", out)
        self.assertIn("overall_ready_for_hardware_attach=False", out)
        self.assertIn("persistent_emmc_writes_authorized=False", out)

        buf_pkg = io.StringIO()
        with contextlib.redirect_stdout(buf_pkg):
            rc_pkg = package_cli_main(["verify-42-gates", "--clean-room"])
        self.assertEqual(rc_pkg, 0)
        self.assertIn("verified=39/42", buf_pkg.getvalue())

        with tempfile.TemporaryDirectory() as empty_dir:
            buf_fail = io.StringIO()
            with contextlib.redirect_stdout(buf_fail):
                rc_fail = package_cli_main(
                    ["verify-42-gates", "--repo-root", empty_dir, "--clean-room"]
                )
            self.assertEqual(rc_fail, 1)

    def test_29_module_cli_json_dry_run_output(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = module_cli_main(
                ["--clean-room", "--dry-run-simulated-backup", "--json"]
            )
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["schema"], VP_STROBE_VEHICLERIG_42GATE_SCHEMA)
        self.assertTrue(payload["all_42_gates_verified"])
        self.assertFalse(payload["persistent_emmc_writes_authorized"])

    def test_30_env_force_clean_room_honored_end_to_end(self) -> None:
        with patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            rep = evaluate_42gate_preflight(DEFAULT_REPO_ROOT)
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(rep.clean_room_forced)
        self.assertTrue(rep.offline_39_gates_verified)
        self.assertFalse(rep.persistent_emmc_writes_authorized)

    def test_31_evaluate_42_master_safety_gates_alias_and_default_mode(self) -> None:
        self.assertIs(evaluate_42_master_safety_gates, evaluate_42gate_preflight)
        rep = evaluate_42_master_safety_gates(
            DEFAULT_REPO_ROOT, dry_run_simulated_backup=True
        )
        self.assertTrue(rep.all_42_gates_verified)
        self.assertGreaterEqual(rep.summary["verified_gates"], 42)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.persistent_write_release)

    def test_32_donor_corruption_propagates_to_g41_g42_and_42gate_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            fx3_lib = (
                tmp
                / "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib"
            )
            fx6_lib = (
                tmp
                / "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib"
            )
            fx3_lib.mkdir(parents=True)
            fx6_lib.mkdir(parents=True)
            for name in ("libUsbControl.so", "libInfraExtCmdSvc.so"):
                (fx3_lib / name).write_bytes(b"bad")
                (fx6_lib / name).write_bytes(b"bad")
            for name in ("libInfraMultiIF.so", "libInfraLanc.so"):
                (fx6_lib / name).write_bytes(b"bad")
            v41, r41 = evaluate_g41_vp_strobe_and_genlock(
                work_root=tmp, force_clean_room=False
            )
            v42, r42 = evaluate_g42_vehiclerig_ibis_and_tether(
                work_root=tmp, force_clean_room=False
            )
        self.assertFalse(v41.passed)
        self.assertFalse(r41.valid)
        self.assertEqual(v41.status, STATUS_BLOCKED_DONOR_INTEGRITY)
        self.assertFalse(v42.passed)
        self.assertFalse(r42.valid)
        self.assertEqual(v42.status, STATUS_BLOCKED_DONOR_INTEGRITY)

    def test_33_prior_cli_subcommands_verify_16_through_40_remain_intact(self) -> None:
        for subcmd in (
            "verify-16-gates",
            "verify-18-gates",
            "verify-20-gates",
            "verify-22-gates",
            "verify-24-gates",
            "verify-26-gates",
            "verify-28-gates",
            "verify-30-gates",
            "verify-32-gates",
            "verify-34-gates",
            "verify-36-gates",
            "verify-38-gates",
            "verify-40-gates",
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = package_cli_main([subcmd, "--clean-room", "--json"])
            self.assertEqual(rc, 0, f"{subcmd} failed with rc={rc}")
            payload = json.loads(buf.getvalue())
            self.assertFalse(payload["persistent_emmc_writes_authorized"])

    def test_34_g41_g42_gate_ids_and_soc_passthrough_in_42gate_report(self) -> None:
        rep = evaluate_42gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            soc_start_ceiling_c=58.0,
        )
        self.assertTrue(rep.all_42_gates_verified)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertEqual(rep.gates[40]["gate_id"], G41_GATE_ID)
        self.assertEqual(rep.gates[40]["gate_code"], G41_GATE_CODE)
        self.assertEqual(rep.gates[41]["gate_id"], G42_GATE_ID)
        self.assertEqual(rep.gates[41]["gate_code"], G42_GATE_CODE)

    def test_35_42gate_summary_blocks_if_g41_or_g42_requests_emmc_write(self) -> None:
        rep_41 = evaluate_42gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            vp_strobe_genlock_kwargs={"request_persistent_emmc_writes": True},
        )
        self.assertFalse(rep_41.all_42_gates_verified)
        self.assertFalse(rep_41.g41_to_g42_all_passed)
        self.assertFalse(rep_41.gates[40]["passed"])
        self.assertEqual(rep_41.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        self.assertFalse(rep_41.persistent_emmc_writes_authorized)

        rep_42 = evaluate_42gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            vehiclerig_ibis_kwargs={"request_persistent_emmc_writes": True},
        )
        self.assertFalse(rep_42.all_42_gates_verified)
        self.assertFalse(rep_42.g41_to_g42_all_passed)
        self.assertFalse(rep_42.gates[41]["passed"])
        self.assertEqual(rep_42.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        self.assertFalse(rep_42.persistent_emmc_writes_authorized)

    def test_36_g41_mitigated_uvarc_and_ecs_locked_low_pwm_ledwall_pass_with_warnings(
        self,
    ) -> None:
        res = verify_vp_strobe_uvarc_and_genlock_firewall(
            vp_profile="VP_LED_WALL_PYRO_ECS_PROTECTED",
            peak_irradiance_w_cm2=0.30,
            uv_arc_welding_or_pyro_scene=True,
            uv_ir_cut_and_protective_nd_installed=True,
            nd_optical_density=0.9,
            bnc_sync_signal_type="LTC_SMPTE_UNBALANCED",
            led_volume_active=True,
            led_pwm_refresh_hz=960.0,
            ecs_fractional_shutter_locked=True,
        )
        self.assertTrue(res.valid)
        self.assertGreaterEqual(len(res.warnings), 2)

    def test_37_g42_exterior_3cup_25kg_tether_and_wire_isolator_ibis_park_pass_with_warnings(
        self,
    ) -> None:
        res = verify_vehiclerig_vibration_ibis_and_tether_guard(
            rig_profile="HELICOPTER_SKID_WIRE_ISOLATED_RIG",
            vibration_rms_g=2.4,
            dominant_vibration_hz=68.0,
            wire_rope_or_elastomer_isolator_stage=True,
            ibis_steadyshot_mode=IBIS_MODE_OFF_MECHANICAL_PARK,
            gyroflow_rtmd_logging_enabled=False,
            vehicle_or_aerial_exterior_mount=True,
            secondary_steel_safety_cable_rated_kg=35.0,
            suction_cup_count=3,
        )
        self.assertTrue(res.valid)
        self.assertGreaterEqual(len(res.warnings), 2)

    def test_38_donor_audit_large_binaries_dual_mode(self) -> None:
        res = audit_phase131_donor_contracts(include_large_binaries=True)
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_VERIFIED_SAFE)
        self.assertEqual(res.access_mode, "O_RDONLY")
        if res.verification_mode == "LOCAL_DONOR_O_RDONLY":
            self.assertTrue(res.large_binaries_scanned)
            self.assertGreaterEqual(res.files_inspected, 6)
        else:
            self.assertFalse(res.large_binaries_scanned)

    def test_39_h0_h1_trial_entry_allowed_and_g13_to_g42_flags(self) -> None:
        rep_off = evaluate_42gate_preflight(DEFAULT_REPO_ROOT, force_clean_room=True)
        self.assertTrue(rep_off.h0_h1_trial_entry_allowed)
        self.assertTrue(rep_off.g13_to_g42_all_passed)
        self.assertTrue(rep_off.g41_to_g42_all_passed)
        self.assertFalse(rep_off.overall_ready_for_hardware_attach)

        rep_bad = evaluate_42gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            vp_strobe_genlock_kwargs={"bnc_sync_signal_type": "WORDCLOCK_5V_TTL"},
        )
        self.assertFalse(rep_bad.h0_h1_trial_entry_allowed)
        self.assertFalse(rep_bad.g13_to_g42_all_passed)
        self.assertFalse(rep_bad.offline_39_gates_verified)

    def test_40_g41_external_syncbox_disconnected_from_multiterminal_passes(
        self,
    ) -> None:
        res = verify_vp_strobe_uvarc_and_genlock_firewall(
            bnc_sync_signal_type="TRILEVEL_GENLOCK",
            connected_to_fx3_multiterminal=False,
        )
        self.assertTrue(res.valid)

    def test_41_g42_sub_resonance_freq_and_low_g_ibis_standard_boundary(self) -> None:
        # Below 35 Hz OR <= 1.2 g RMS allows STANDARD IBIS
        res_low_freq = verify_vehiclerig_vibration_ibis_and_tether_guard(
            vibration_rms_g=1.5,
            dominant_vibration_hz=30.0,
            wire_rope_or_elastomer_isolator_stage=True,
            ibis_steadyshot_mode="STANDARD",
        )
        self.assertTrue(res_low_freq.valid)

        res_low_g = verify_vehiclerig_vibration_ibis_and_tether_guard(
            vibration_rms_g=VIBRATION_IBIS_PARK_MAX_RMS_G,
            dominant_vibration_hz=90.0,
            wire_rope_or_elastomer_isolator_stage=True,
            ibis_steadyshot_mode="STANDARD",
        )
        self.assertTrue(res_low_g.valid)

    def test_42_42gate_report_to_dict_has_expected_top_level_keys(self) -> None:
        rep = evaluate_42gate_preflight(DEFAULT_REPO_ROOT, force_clean_room=True)
        d = rep.to_dict()
        for key in (
            "schema",
            "version",
            "verification_mode",
            "offline_39_gates_verified",
            "all_42_gates_verified",
            "g13_to_g42_all_passed",
            "g41_to_g42_all_passed",
            "overall_ready_for_hardware_attach",
            "persistent_emmc_writes_authorized",
            "persistent_write_release",
            "summary",
            "gates",
            "master_40_report",
            "g41_result",
            "g42_result",
        ):
            self.assertIn(key, d)


if __name__ == "__main__":
    unittest.main()
