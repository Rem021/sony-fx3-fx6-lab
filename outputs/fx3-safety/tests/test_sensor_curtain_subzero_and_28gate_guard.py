"""Fast dual-mode unit tests for Phase 97 — IMX510 Sensor Laser/Solar, Anti-Dust Curtain &
IBIS Transport Lock Guard (G27), Sub-Zero NP-FZ100 ESR Sag & High-Altitude Cooling
Firewall (G28), and Unified 28-Gate Master Safety Preflight (`G01..G28`).
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
from fx3_safety.intake_occlusion_tripod_and_26gate_guard import (
    STATUS_BLOCKED_FAN_TACHOMETER_ROTOR_STALL,
    STATUS_BLOCKED_TRIPOD_SCREW_BOTTOM_OUT_DAMAGE,
    evaluate_26gate_preflight,
)
from fx3_safety.master_16gate_preflight import DEFAULT_REPO_ROOT
from fx3_safety.rig_groundloop_lensrail_and_20gate_guard import (
    STATUS_FAIL_OFFLINE_HARDWARE_NOT_ATTACHED,
)
from fx3_safety.sensor_curtain_subzero_and_28gate_guard import (
    FAST_LENS_SOLAR_BURN_MAX_F_NUMBER,
    FX3_SEA_LEVEL_COOLING_HEADROOM_WATTS,
    FX3_SHUTTER_BLADE_THICKNESS_MM,
    G27_GATE_CODE,
    G27_GATE_ID,
    G28_GATE_CODE,
    G28_GATE_ID,
    HIGH_ALTITUDE_DERATING_THRESHOLD_M,
    HIGH_ALTITUDE_PRESSURE_THRESHOLD_KPA,
    ISA_SEA_LEVEL_AIR_DENSITY_KG_M3,
    ISA_SEA_LEVEL_PRESSURE_KPA,
    MAX_UNPOWERED_IBIS_VIBRATION_GRMS,
    NPFZ100_PMIC_UVLO_CUTOFF_V,
    NPFZ100_REF_ESR_25C_OHM,
    NPFZ100_SAFE_VTERM_MIN_V,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    SENSOR_CURTAIN_SUBZERO_28GATE_SCHEMA,
    SENSOR_CURTAIN_SUBZERO_28GATE_VERSION,
    STATUS_BLOCKED_DONOR_INTEGRITY,
    STATUS_BLOCKED_FRAGILE_CURTAIN_AT_LENS_CHANGE,
    STATUS_BLOCKED_HIGH_ALTITUDE_CONVECTIVE_DERATING,
    STATUS_BLOCKED_LASER_OR_SOLAR_IRRADIANCE_HAZARD,
    STATUS_BLOCKED_LIION_SUBZERO_CHARGING_PLATING,
    STATUS_BLOCKED_PERSISTENT_EMMC_WRITE,
    STATUS_BLOCKED_SENSOR_CURTAIN_TELEMETRY_INVALID,
    STATUS_BLOCKED_SUBZERO_ALTITUDE_TELEMETRY_INVALID,
    STATUS_BLOCKED_SUBZERO_LIION_ESR_BROWNOUT_RISK,
    STATUS_BLOCKED_UNPOWERED_IBIS_HARD_VIBRATION,
    STATUS_SAFE,
    STATUS_VERIFIED_G27,
    STATUS_VERIFIED_G28,
    STATUS_VERIFIED_SAFE,
    audit_phase97_donor_contracts,
    compute_arrhenius_npfz100_esr_ohm,
    compute_isa_atmosphere,
    compute_npfz100_ocv_v,
    evaluate_28_master_safety_gates,
    evaluate_28gate_preflight,
    evaluate_g27_sensor_curtain_and_ibis_transport,
    evaluate_g28_subzero_esr_and_altitude,
    main as module_cli_main,
    predict_npfz100_terminal_voltage_v,
    verify_sensor_curtain_and_ibis_transport_guard,
    verify_subzero_esr_and_altitude_firewall,
)


class SensorCurtainSubzeroAnd28GateGuardTests(unittest.TestCase):
    # --- 1. Hard Redlines, Package Exports & O_RDONLY Donor Audit ---

    def test_01_hard_locked_redlines_and_package_exports(self) -> None:
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(PERSISTENT_WRITE_RELEASE)
        self.assertEqual(
            SENSOR_CURTAIN_SUBZERO_28GATE_SCHEMA,
            "fx3-sensor-curtain-subzero-28gate-preflight-v1",
        )
        self.assertEqual(SENSOR_CURTAIN_SUBZERO_28GATE_VERSION, "1.0.0")
        for sym in (
            "SENSOR_CURTAIN_SUBZERO_28GATE_SCHEMA",
            "G27_GATE_ID",
            "G28_GATE_ID",
            "STATUS_BLOCKED_LASER_OR_SOLAR_IRRADIANCE_HAZARD",
            "STATUS_BLOCKED_FRAGILE_CURTAIN_AT_LENS_CHANGE",
            "STATUS_BLOCKED_UNPOWERED_IBIS_HARD_VIBRATION",
            "STATUS_BLOCKED_SUBZERO_LIION_ESR_BROWNOUT_RISK",
            "STATUS_BLOCKED_LIION_SUBZERO_CHARGING_PLATING",
            "STATUS_BLOCKED_HIGH_ALTITUDE_CONVECTIVE_DERATING",
            "audit_phase97_donor_contracts",
            "compute_arrhenius_npfz100_esr_ohm",
            "compute_isa_atmosphere",
            "predict_npfz100_terminal_voltage_v",
            "verify_sensor_curtain_and_ibis_transport_guard",
            "verify_subzero_esr_and_altitude_firewall",
            "evaluate_g27_sensor_curtain_and_ibis_transport",
            "evaluate_g28_subzero_esr_and_altitude",
            "evaluate_28gate_preflight",
            "evaluate_28_master_safety_gates",
            "sensor_curtain_subzero_and_28gate_guard",
        ):
            self.assertIn(sym, fx3_safety.__all__)
            self.assertTrue(hasattr(fx3_safety, sym))
        # Ensure prior Phase 44/77 exports were NOT overwritten
        self.assertEqual(fx3_safety.FAN_MODE_AUTO1, "AUTO1")
        self.assertEqual(fx3_safety.SHUTTER_WHEN_POWER_OFF_OPEN, "OFF")
        self.assertEqual(fx3_safety.NP_FZ100_NOMINAL_MV, 7200)

    def test_02_donor_audit_o_rdonly_and_clean_room_fallback(self) -> None:
        observed_flags = []
        orig_open = os.open

        def spy_open(path, flags, *args, **kwargs):
            observed_flags.append((str(path), flags))
            return orig_open(path, flags, *args, **kwargs)

        with patch("os.open", side_effect=spy_open):
            res_default = audit_phase97_donor_contracts()
        self.assertTrue(res_default.valid)
        self.assertEqual(res_default.status, STATUS_VERIFIED_SAFE)
        self.assertEqual(res_default.access_mode, "O_RDONLY")
        self.assertEqual(len(res_default.missing_markers), 0)
        self.assertTrue(res_default.fx6_internal_evnd_present)
        self.assertTrue(res_default.fx3_open_throat_sensor_cavities)
        self.assertEqual(res_default.bk4_overtemp_thresholds_c["fx3"]["overtemp_warn_c"], 82)
        self.assertEqual(res_default.bk4_overtemp_thresholds_c["fx6"]["overtemp_warn_c"], 76)
        for path, flags in observed_flags:
            if any(k in path for k in ("libfan.so", "libBusPower", "libUsbBusPower", "FX3-CX95900", "CX95898_NTSC")):
                self.assertEqual(flags & os.O_ACCMODE, os.O_RDONLY, f"Non-O_RDONLY open on {path}")

        res_clean = audit_phase97_donor_contracts(force_clean_room=True)
        self.assertTrue(res_clean.valid)
        self.assertEqual(res_clean.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(res_clean.files_inspected, 0)
        self.assertEqual(len(res_clean.sha256_by_artifact), 6)

    def test_03_donor_audit_blocks_integrity_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            fx3_lib = tmp / "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib"
            fx3_seed = tmp / "fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds"
            fx6_lib = tmp / "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib"
            fx6_seed = tmp / "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/tree/0110_backup/SYSIPSX-DSLR/CHAPLIN"
            for d in (fx3_lib, fx3_seed, fx6_lib, fx6_seed):
                d.mkdir(parents=True)
            (fx3_lib / "libfan.so").write_bytes(b"corrupt")
            (fx3_lib / "libBusPower.so").write_bytes(b"corrupt")
            (fx3_lib / "libUsbBusPower.so").write_bytes(b"corrupt")
            (fx6_lib / "libfan.so").write_bytes(b"corrupt")
            (fx3_seed / "FX3-CX95900_ALLLANG-Backup.bin").write_bytes(b"corrupt")
            (fx6_seed / "CX95898_NTSC.bin").write_bytes(b"corrupt")
            res = audit_phase97_donor_contracts(work_root=tmp, force_clean_room=False)
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_DONOR_INTEGRITY)
        self.assertEqual(len(res.missing_markers), 6)

    def test_04_donor_audit_optional_large_binary_token_scan_when_present(self) -> None:
        res_clean = audit_phase97_donor_contracts(force_clean_room=True, include_large_binaries=True)
        self.assertTrue(res_clean.valid)
        self.assertFalse(res_clean.large_binaries_scanned)

        res_local = audit_phase97_donor_contracts(include_large_binaries=False)
        self.assertTrue(res_local.valid)
        if res_local.verification_mode == "LOCAL_DONOR_O_RDONLY":
            self.assertEqual(res_local.files_inspected, 6)

    # --- 2. Gate G27 — IMX510 Irradiance, Shutter Curtain & IBIS Transport ---

    def test_05_g27_default_healthy_configuration_passes(self) -> None:
        res = verify_sensor_curtain_and_ibis_transport_guard()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_SAFE)
        self.assertEqual(res.violation_codes, ())
        self.assertTrue(res.irradiance_safe)
        self.assertTrue(res.curtain_safe)
        self.assertTrue(res.ibis_transport_safe)
        self.assertTrue(res.fx3_no_internal_evnd_glass)
        self.assertEqual(res.shutter_blade_thickness_mm, FX3_SHUTTER_BLADE_THICKNESS_MM)
        self.assertFalse(res.persistent_emmc_writes_authorized)

    def test_06_g27_blocks_concert_laser_or_lidar_without_optical_filter(self) -> None:
        res_bad = verify_sensor_curtain_and_ibis_transport_guard(
            concert_show_laser_or_automotive_lidar_env=True,
            laser_rated_optical_filter_installed=False,
        )
        self.assertFalse(res_bad.valid)
        self.assertFalse(res_bad.irradiance_safe)
        self.assertEqual(res_bad.status, STATUS_BLOCKED_LASER_OR_SOLAR_IRRADIANCE_HAZARD)

        res_ok = verify_sensor_curtain_and_ibis_transport_guard(
            concert_show_laser_or_automotive_lidar_env=True,
            laser_rated_optical_filter_installed=True,
        )
        self.assertTrue(res_ok.valid)
        self.assertTrue(res_ok.irradiance_safe)

    def test_07_g27_blocks_uncapped_fast_lens_pointed_at_direct_sun(self) -> None:
        res_explicit = verify_sensor_curtain_and_ibis_transport_guard(
            uncapped_fast_lens_pointed_at_direct_sun=True,
        )
        self.assertFalse(res_explicit.valid)
        self.assertFalse(res_explicit.irradiance_safe)
        self.assertEqual(res_explicit.status, STATUS_BLOCKED_LASER_OR_SOLAR_IRRADIANCE_HAZARD)

        res_derived = verify_sensor_curtain_and_ibis_transport_guard(
            direct_sun_in_fov=True,
            lens_uncapped=True,
            lens_f_number=1.4,
            solar_rated_nd_filter_installed=False,
        )
        self.assertFalse(res_derived.valid)
        self.assertEqual(res_derived.status, STATUS_BLOCKED_LASER_OR_SOLAR_IRRADIANCE_HAZARD)

        res_filtered = verify_sensor_curtain_and_ibis_transport_guard(
            direct_sun_in_fov=True,
            lens_uncapped=True,
            lens_f_number=FAST_LENS_SOLAR_BURN_MAX_F_NUMBER,
            solar_rated_nd_filter_installed=True,
        )
        self.assertTrue(res_filtered.valid)

    def test_08_g27_blocks_fragile_curtain_with_manual_swab_or_rocket_blower(self) -> None:
        res = verify_sensor_curtain_and_ibis_transport_guard(
            shutter_when_power_off=True,
            manual_swab_or_rocket_blower_active=True,
        )
        self.assertFalse(res.valid)
        self.assertFalse(res.curtain_safe)
        self.assertEqual(res.status, STATUS_BLOCKED_FRAGILE_CURTAIN_AT_LENS_CHANGE)

    def test_09_g27_blocks_fragile_curtain_with_outdoor_direct_sun_lens_off(self) -> None:
        res = verify_sensor_curtain_and_ibis_transport_guard(
            shutter_when_power_off=True,
            outdoor_direct_sun_lens_off=True,
        )
        self.assertFalse(res.valid)
        self.assertFalse(res.curtain_safe)
        self.assertEqual(res.status, STATUS_BLOCKED_FRAGILE_CURTAIN_AT_LENS_CHANGE)

    def test_10_g27_allows_shutter_open_for_cleaning_and_shaded_closed_swap(self) -> None:
        res_open_clean = verify_sensor_curtain_and_ibis_transport_guard(
            shutter_when_power_off=False,
            manual_swab_or_rocket_blower_active=True,
            sensor_cleaning_ultrasonic_shake=True,
        )
        self.assertTrue(res_open_clean.valid)
        self.assertTrue(res_open_clean.curtain_safe)

        res_closed_shaded = verify_sensor_curtain_and_ibis_transport_guard(
            shutter_when_power_off=True,
            manual_swab_or_rocket_blower_active=False,
            outdoor_direct_sun_lens_off=False,
        )
        self.assertTrue(res_closed_shaded.valid)
        self.assertGreaterEqual(len(res_closed_shaded.warnings), 1)

    def test_11_g27_blocks_unpowered_ibis_hard_mount_vibration_over_1_8_grms(self) -> None:
        res = verify_sensor_curtain_and_ibis_transport_guard(
            vehicle_hard_mount_vibration_grms=2.4,
            power_off_ibis_parking_verified=False,
        )
        self.assertFalse(res.valid)
        self.assertFalse(res.ibis_transport_safe)
        self.assertEqual(res.status, STATUS_BLOCKED_UNPOWERED_IBIS_HARD_VIBRATION)

    def test_12_g27_allows_1_8_grms_boundary_and_verified_ibis_parking(self) -> None:
        res_boundary = verify_sensor_curtain_and_ibis_transport_guard(
            vehicle_hard_mount_vibration_grms=MAX_UNPOWERED_IBIS_VIBRATION_GRMS,
            power_off_ibis_parking_verified=False,
        )
        self.assertTrue(res_boundary.valid)
        self.assertTrue(res_boundary.ibis_transport_safe)

        res_parked = verify_sensor_curtain_and_ibis_transport_guard(
            vehicle_hard_mount_vibration_grms=3.2,
            power_off_ibis_parking_verified=True,
        )
        self.assertTrue(res_parked.valid)
        self.assertGreaterEqual(len(res_parked.warnings), 1)

    def test_13_g27_rejects_invalid_telemetry_and_persistent_emmc_write(self) -> None:
        res_nan = verify_sensor_curtain_and_ibis_transport_guard(
            vehicle_hard_mount_vibration_grms=float("nan"),
        )
        self.assertFalse(res_nan.valid)
        self.assertEqual(res_nan.status, STATUS_BLOCKED_SENSOR_CURTAIN_TELEMETRY_INVALID)

        res_neg = verify_sensor_curtain_and_ibis_transport_guard(
            vehicle_hard_mount_vibration_grms=-0.2,
        )
        self.assertFalse(res_neg.valid)
        self.assertEqual(res_neg.status, STATUS_BLOCKED_SENSOR_CURTAIN_TELEMETRY_INVALID)

        res_fnum = verify_sensor_curtain_and_ibis_transport_guard(lens_f_number=0.0)
        self.assertFalse(res_fnum.valid)
        self.assertEqual(res_fnum.status, STATUS_BLOCKED_SENSOR_CURTAIN_TELEMETRY_INVALID)

        res_emmc = verify_sensor_curtain_and_ibis_transport_guard(request_persistent_emmc_writes=True)
        self.assertFalse(res_emmc.valid)
        self.assertEqual(res_emmc.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        self.assertFalse(res_emmc.persistent_emmc_writes_authorized)

    def test_14_g27_accumulates_multiple_violations_deterministically(self) -> None:
        res = verify_sensor_curtain_and_ibis_transport_guard(
            concert_show_laser_or_automotive_lidar_env=True,
            laser_rated_optical_filter_installed=False,
            shutter_when_power_off=True,
            manual_swab_or_rocket_blower_active=True,
            vehicle_hard_mount_vibration_grms=2.8,
            power_off_ibis_parking_verified=False,
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            set(res.violation_codes),
            {
                STATUS_BLOCKED_LASER_OR_SOLAR_IRRADIANCE_HAZARD,
                STATUS_BLOCKED_FRAGILE_CURTAIN_AT_LENS_CHANGE,
                STATUS_BLOCKED_UNPOWERED_IBIS_HARD_VIBRATION,
            },
        )

    # --- 3. Gate G28 — Arrhenius Sub-Zero NP-FZ100 ESR & ISA Altitude ---

    def test_15_g28_arrhenius_esr_and_isa_atmosphere_physics(self) -> None:
        r_25 = compute_arrhenius_npfz100_esr_ohm(25.0)
        r_m10 = compute_arrhenius_npfz100_esr_ohm(-10.0)
        r_m20 = compute_arrhenius_npfz100_esr_ohm(-20.0)
        self.assertAlmostEqual(r_25, NPFZ100_REF_ESR_25C_OHM, places=6)
        self.assertGreater(r_m10 / r_25, 3.0)
        self.assertLess(r_m10 / r_25, 5.0)
        self.assertGreater(r_m20 / r_25, 5.5)
        self.assertGreater(r_m20, r_m10)

        v_oc_45 = compute_npfz100_ocv_v(45.0)
        self.assertAlmostEqual(v_oc_45, 7.28, places=3)
        _, _, vt_m20_45 = predict_npfz100_terminal_voltage_v(-20.0, soc_pct=45.0, peak_load_watts=8.5)
        self.assertLess(vt_m20_45, NPFZ100_SAFE_VTERM_MIN_V)
        self.assertLess(vt_m20_45, NPFZ100_PMIC_UVLO_CUTOFF_V)

        p0, rho0, ratio0 = compute_isa_atmosphere(0.0)
        self.assertAlmostEqual(p0, ISA_SEA_LEVEL_PRESSURE_KPA, places=3)
        self.assertAlmostEqual(rho0, ISA_SEA_LEVEL_AIR_DENSITY_KG_M3, places=4)
        self.assertAlmostEqual(ratio0, 1.0, places=6)

        p3500, _, ratio3500 = compute_isa_atmosphere(3500.0)
        p5500, _, ratio5500 = compute_isa_atmosphere(5500.0)
        self.assertLess(p3500, HIGH_ALTITUDE_PRESSURE_THRESHOLD_KPA)
        self.assertLess(ratio3500, 0.71)
        self.assertLess(ratio5500, 0.58)

    def test_16_g28_default_healthy_configuration_passes(self) -> None:
        res = verify_subzero_esr_and_altitude_firewall()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_SAFE)
        self.assertEqual(res.violation_codes, ())
        self.assertTrue(res.subzero_esr_brownout_safe)
        self.assertTrue(res.subzero_charging_safe)
        self.assertTrue(res.altitude_convective_cooling_safe)
        self.assertGreaterEqual(res.predicted_v_term_min_v, NPFZ100_SAFE_VTERM_MIN_V)
        self.assertFalse(res.persistent_emmc_writes_authorized)

    def test_17_g28_blocks_subzero_45pct_soc_8_5w_esr_brownout_without_usbpd(self) -> None:
        res = verify_subzero_esr_and_altitude_firewall(
            battery_cell_temp_c=-20.0,
            battery_soc_pct=45.0,
            peak_load_watts=8.5,
            insulated_usb_pd_backup=False,
        )
        self.assertFalse(res.valid)
        self.assertFalse(res.subzero_esr_brownout_safe)
        self.assertLess(res.predicted_v_term_min_v, NPFZ100_SAFE_VTERM_MIN_V)
        self.assertEqual(res.status, STATUS_BLOCKED_SUBZERO_LIION_ESR_BROWNOUT_RISK)

    def test_18_g28_allows_subzero_with_insulated_usbpd_or_high_soc(self) -> None:
        res_usbpd = verify_subzero_esr_and_altitude_firewall(
            battery_cell_temp_c=-20.0,
            battery_soc_pct=45.0,
            peak_load_watts=8.5,
            insulated_usb_pd_backup=True,
            usb_pd_charging_enabled=False,
        )
        self.assertTrue(res_usbpd.valid)
        self.assertTrue(res_usbpd.subzero_esr_brownout_safe)
        self.assertGreaterEqual(len(res_usbpd.warnings), 1)

        res_high_soc = verify_subzero_esr_and_altitude_firewall(
            battery_cell_temp_c=-10.0,
            battery_soc_pct=90.0,
            peak_load_watts=8.5,
            insulated_usb_pd_backup=False,
        )
        self.assertTrue(res_high_soc.valid)
        self.assertGreaterEqual(res_high_soc.predicted_v_term_min_v, NPFZ100_SAFE_VTERM_MIN_V)

    def test_19_g28_blocks_subzero_usbpd_charging_dendrite_plating(self) -> None:
        res_zero = verify_subzero_esr_and_altitude_firewall(
            battery_cell_temp_c=0.0,
            usb_pd_charging_enabled=True,
        )
        self.assertFalse(res_zero.valid)
        self.assertFalse(res_zero.subzero_charging_safe)
        self.assertEqual(res_zero.status, STATUS_BLOCKED_LIION_SUBZERO_CHARGING_PLATING)

        res_cold = verify_subzero_esr_and_altitude_firewall(
            battery_cell_temp_c=-12.0,
            battery_soc_pct=90.0,
            insulated_usb_pd_backup=True,
            usb_pd_charging_enabled=True,
        )
        self.assertFalse(res_cold.valid)
        self.assertEqual(res_cold.status, STATUS_BLOCKED_LIION_SUBZERO_CHARGING_PLATING)

        res_warm = verify_subzero_esr_and_altitude_firewall(
            battery_cell_temp_c=5.0,
            usb_pd_charging_enabled=True,
        )
        self.assertTrue(res_warm.valid)

    def test_20_g28_blocks_high_altitude_over_3000m_convective_derating(self) -> None:
        res = verify_subzero_esr_and_altitude_firewall(
            altitude_m=4500.0,
            cooling_headroom_watts=FX3_SEA_LEVEL_COOLING_HEADROOM_WATTS,
            workload_thermal_watts=8.5,
        )
        self.assertFalse(res.valid)
        self.assertFalse(res.altitude_convective_cooling_safe)
        self.assertLess(res.atmospheric_pressure_kpa, HIGH_ALTITUDE_PRESSURE_THRESHOLD_KPA)
        self.assertLess(res.derated_cooling_capacity_watts, res.workload_thermal_watts)
        self.assertEqual(res.status, STATUS_BLOCKED_HIGH_ALTITUDE_CONVECTIVE_DERATING)

    def test_21_g28_allows_3000m_boundary_and_derated_4500m_low_power_workload(self) -> None:
        res_3000 = verify_subzero_esr_and_altitude_firewall(
            altitude_m=HIGH_ALTITUDE_DERATING_THRESHOLD_M,
            workload_thermal_watts=8.5,
        )
        self.assertTrue(res_3000.valid)
        self.assertTrue(res_3000.altitude_convective_cooling_safe)

        res_4500_ok = verify_subzero_esr_and_altitude_firewall(
            altitude_m=4500.0,
            cooling_headroom_watts=FX3_SEA_LEVEL_COOLING_HEADROOM_WATTS,
            workload_thermal_watts=5.5,
        )
        self.assertTrue(res_4500_ok.valid)
        self.assertGreaterEqual(res_4500_ok.derated_cooling_capacity_watts, 5.5)
        self.assertGreaterEqual(len(res_4500_ok.warnings), 1)

    def test_22_g28_rejects_invalid_telemetry_and_persistent_emmc_write(self) -> None:
        res_nan = verify_subzero_esr_and_altitude_firewall(altitude_m=float("nan"))
        self.assertFalse(res_nan.valid)
        self.assertEqual(res_nan.status, STATUS_BLOCKED_SUBZERO_ALTITUDE_TELEMETRY_INVALID)

        res_strat = verify_subzero_esr_and_altitude_firewall(altitude_m=15000.0)
        self.assertFalse(res_strat.valid)
        self.assertEqual(res_strat.status, STATUS_BLOCKED_SUBZERO_ALTITUDE_TELEMETRY_INVALID)

        res_soc = verify_subzero_esr_and_altitude_firewall(battery_soc_pct=120.0)
        self.assertFalse(res_soc.valid)
        self.assertEqual(res_soc.status, STATUS_BLOCKED_SUBZERO_ALTITUDE_TELEMETRY_INVALID)

        res_emmc = verify_subzero_esr_and_altitude_firewall(request_persistent_emmc_writes=True)
        self.assertFalse(res_emmc.valid)
        self.assertEqual(res_emmc.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        self.assertFalse(res_emmc.persistent_emmc_writes_authorized)

    def test_23_g28_accumulates_all_three_violations_deterministically(self) -> None:
        res = verify_subzero_esr_and_altitude_firewall(
            battery_cell_temp_c=-20.0,
            battery_soc_pct=45.0,
            peak_load_watts=8.5,
            insulated_usb_pd_backup=False,
            usb_pd_charging_enabled=True,
            altitude_m=5200.0,
            workload_thermal_watts=8.5,
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            set(res.violation_codes),
            {
                STATUS_BLOCKED_SUBZERO_LIION_ESR_BROWNOUT_RISK,
                STATUS_BLOCKED_LIION_SUBZERO_CHARGING_PLATING,
                STATUS_BLOCKED_HIGH_ALTITUDE_CONVECTIVE_DERATING,
            },
        )

    # --- 4. Gate G27 & G28 Evaluators & 28-Gate Master Safety Preflight ---

    def test_24_g27_and_g28_verdicts_dual_mode(self) -> None:
        v27, r27 = evaluate_g27_sensor_curtain_and_ibis_transport(force_clean_room=True)
        self.assertTrue(v27.passed)
        self.assertEqual(v27.gate_id, G27_GATE_ID)
        self.assertEqual(v27.gate_code, G27_GATE_CODE)
        self.assertEqual(v27.status, STATUS_VERIFIED_G27)
        self.assertFalse(r27.persistent_emmc_writes_authorized)

        v28, r28 = evaluate_g28_subzero_esr_and_altitude(force_clean_room=True)
        self.assertTrue(v28.passed)
        self.assertEqual(v28.gate_id, G28_GATE_ID)
        self.assertEqual(v28.gate_code, G28_GATE_CODE)
        self.assertEqual(v28.status, STATUS_VERIFIED_G28)
        self.assertFalse(r28.persistent_emmc_writes_authorized)

    def test_25_28gate_offline_default_25_of_28_and_g10_g12_fail_offline(self) -> None:
        rep = evaluate_28gate_preflight(DEFAULT_REPO_ROOT, force_clean_room=True)
        self.assertEqual(rep.schema, SENSOR_CURTAIN_SUBZERO_28GATE_SCHEMA)
        self.assertEqual(len(rep.gates), 28)
        self.assertEqual(rep.summary["total_gates"], 28)
        self.assertEqual(rep.summary["verified_gates"], 25)
        self.assertEqual(rep.summary["blocked_or_pending_gates"], 3)
        self.assertTrue(rep.offline_25_gates_verified)
        self.assertFalse(rep.all_28_gates_verified)
        self.assertFalse(rep.dry_run_rehearsal_only)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.persistent_write_release)
        self.assertEqual(rep.status, "VERIFIED_25_OF_28_AWAITING_PHYSICAL_TIER0")
        for idx in (9, 10, 11):
            self.assertFalse(rep.gates[idx]["passed"])
            self.assertEqual(rep.gates[idx]["status"], STATUS_FAIL_OFFLINE_HARDWARE_NOT_ATTACHED)

    def test_26_28gate_dry_run_simulated_backup_28_of_28_and_redlines_locked(self) -> None:
        rep = evaluate_28gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
        )
        self.assertEqual(len(rep.gates), 28)
        self.assertEqual(rep.summary["verified_gates"], 28)
        self.assertEqual(rep.summary["blocked_or_pending_gates"], 0)
        self.assertTrue(rep.all_28_gates_verified)
        self.assertTrue(rep.dry_run_rehearsal_only)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.persistent_write_release)
        self.assertEqual(rep.status, "VERIFIED_ALL_28_GATES_DRY_RUN_SIMULATED_BACKUP")
        self.assertTrue(all(g["passed"] for g in rep.gates))

    def test_27_28gate_propagates_g27_laser_curtain_and_ibis_failures(self) -> None:
        rep_laser = evaluate_28gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            sensor_curtain_kwargs={"concert_show_laser_or_automotive_lidar_env": True},
        )
        self.assertFalse(rep_laser.all_28_gates_verified)
        self.assertFalse(rep_laser.g27_to_g28_all_passed)
        self.assertFalse(rep_laser.gates[26]["passed"])
        self.assertEqual(rep_laser.status, STATUS_BLOCKED_LASER_OR_SOLAR_IRRADIANCE_HAZARD)

        rep_curtain = evaluate_28gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            sensor_curtain_kwargs={"shutter_when_power_off": True, "manual_swab_or_rocket_blower_active": True},
        )
        self.assertFalse(rep_curtain.all_28_gates_verified)
        self.assertEqual(rep_curtain.status, STATUS_BLOCKED_FRAGILE_CURTAIN_AT_LENS_CHANGE)

        rep_ibis = evaluate_28gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            sensor_curtain_kwargs={"vehicle_hard_mount_vibration_grms": 2.5, "power_off_ibis_parking_verified": False},
        )
        self.assertFalse(rep_ibis.all_28_gates_verified)
        self.assertEqual(rep_ibis.status, STATUS_BLOCKED_UNPOWERED_IBIS_HARD_VIBRATION)

    def test_28_28gate_propagates_g28_subzero_plating_and_altitude_failures(self) -> None:
        rep_esr = evaluate_28gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            subzero_altitude_kwargs={"battery_cell_temp_c": -20.0, "battery_soc_pct": 45.0, "peak_load_watts": 8.5},
        )
        self.assertFalse(rep_esr.all_28_gates_verified)
        self.assertFalse(rep_esr.gates[27]["passed"])
        self.assertEqual(rep_esr.status, STATUS_BLOCKED_SUBZERO_LIION_ESR_BROWNOUT_RISK)

        rep_plate = evaluate_28gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            subzero_altitude_kwargs={"battery_cell_temp_c": -5.0, "battery_soc_pct": 90.0, "usb_pd_charging_enabled": True},
        )
        self.assertFalse(rep_plate.all_28_gates_verified)
        self.assertEqual(rep_plate.status, STATUS_BLOCKED_LIION_SUBZERO_CHARGING_PLATING)

        rep_alt = evaluate_28gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            subzero_altitude_kwargs={"altitude_m": 4800.0, "workload_thermal_watts": 8.5},
        )
        self.assertFalse(rep_alt.all_28_gates_verified)
        self.assertEqual(rep_alt.status, STATUS_BLOCKED_HIGH_ALTITUDE_CONVECTIVE_DERATING)

    def test_29_28gate_propagates_g25_g26_and_emmc_redline(self) -> None:
        rep_g25_g26 = evaluate_28gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            intake_fan_kwargs={"pwm_duty_pct": 50.0, "measured_rpm": 100.0},
            tripod_housing_kwargs={"effective_screw_protrusion_mm": 6.8},
        )
        self.assertFalse(rep_g25_g26.all_28_gates_verified)
        self.assertFalse(rep_g25_g26.gates[24]["passed"])
        self.assertFalse(rep_g25_g26.gates[25]["passed"])
        self.assertEqual(rep_g25_g26.gates[24]["status"], STATUS_BLOCKED_FAN_TACHOMETER_ROTOR_STALL)
        self.assertEqual(rep_g25_g26.gates[25]["status"], STATUS_BLOCKED_TRIPOD_SCREW_BOTTOM_OUT_DAMAGE)
        self.assertEqual(rep_g25_g26.status, STATUS_BLOCKED_FAN_TACHOMETER_ROTOR_STALL)

        rep_emmc = evaluate_28gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            request_persistent_emmc_writes=True,
        )
        self.assertFalse(rep_emmc.all_28_gates_verified)
        self.assertFalse(rep_emmc.offline_25_gates_verified)
        self.assertFalse(rep_emmc.overall_ready_for_hardware_attach)
        self.assertFalse(rep_emmc.persistent_emmc_writes_authorized)
        self.assertEqual(rep_emmc.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)

    def test_30_28gate_preserves_g01_to_g26_untouched(self) -> None:
        r26 = evaluate_26gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
        )
        r28 = evaluate_28gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
        )
        self.assertEqual(len(r26.gates), 26)
        self.assertEqual(len(r28.gates), 28)
        self.assertEqual(
            [g["gate_id"] for g in r26.gates],
            [g["gate_id"] for g in r28.gates[:26]],
        )
        self.assertEqual(
            [g["status"] for g in r26.gates],
            [g["status"] for g in r28.gates[:26]],
        )

    def test_31_serialized_json_contains_zero_raw_bytes_repr(self) -> None:
        rep = evaluate_28gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
        )
        rendered = json.dumps(rep.to_dict(), ensure_ascii=False)
        self.assertNotRegex(rendered, r'(?<![0-9A-Za-z_/.-])b[\'"]')

    def test_32_cli_verify_28_gates_offline_and_dry_run_json(self) -> None:
        buf_off = io.StringIO()
        with contextlib.redirect_stdout(buf_off):
            rc_off = package_cli_main(["verify-28-gates", "--clean-room", "--json"])
        self.assertEqual(rc_off, 0)
        p_off = json.loads(buf_off.getvalue())
        self.assertEqual(p_off["schema"], SENSOR_CURTAIN_SUBZERO_28GATE_SCHEMA)
        self.assertEqual(p_off["summary"]["verified_gates"], 25)
        self.assertFalse(p_off["dry_run_rehearsal_only"])
        self.assertFalse(p_off["overall_ready_for_hardware_attach"])
        self.assertFalse(p_off["persistent_emmc_writes_authorized"])

        buf_dry = io.StringIO()
        with contextlib.redirect_stdout(buf_dry):
            rc_dry = package_cli_main(["verify-28-gates", "--clean-room", "--dry-run-simulated-backup", "--json"])
        self.assertEqual(rc_dry, 0)
        p_dry = json.loads(buf_dry.getvalue())
        self.assertEqual(p_dry["summary"]["verified_gates"], 28)
        self.assertTrue(p_dry["all_28_gates_verified"])
        self.assertTrue(p_dry["dry_run_rehearsal_only"])
        self.assertFalse(p_dry["overall_ready_for_hardware_attach"])
        self.assertFalse(p_dry["persistent_emmc_writes_authorized"])

    def test_33_cli_verify_28_gates_summary_and_failure_exit_code(self) -> None:
        buf_mod = io.StringIO()
        with contextlib.redirect_stdout(buf_mod):
            rc_mod = module_cli_main(["--clean-room"])
        self.assertEqual(rc_mod, 0)
        out = buf_mod.getvalue()
        self.assertIn("verified=25/28", out)
        self.assertIn("overall_ready_for_hardware_attach=False", out)
        self.assertIn("persistent_emmc_writes_authorized=False", out)

        buf_pkg = io.StringIO()
        with contextlib.redirect_stdout(buf_pkg):
            rc_pkg = package_cli_main(["verify-28-gates", "--clean-room"])
        self.assertEqual(rc_pkg, 0)
        self.assertIn("verified=25/28", buf_pkg.getvalue())

        with tempfile.TemporaryDirectory() as empty_dir:
            buf_fail = io.StringIO()
            with contextlib.redirect_stdout(buf_fail):
                rc_fail = package_cli_main(["verify-28-gates", "--repo-root", empty_dir, "--clean-room"])
            self.assertEqual(rc_fail, 1)

    def test_34_env_force_clean_room_honored_end_to_end(self) -> None:
        with patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            rep = evaluate_28gate_preflight(DEFAULT_REPO_ROOT)
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(rep.clean_room_forced)
        self.assertTrue(rep.offline_25_gates_verified)
        self.assertFalse(rep.persistent_emmc_writes_authorized)

    def test_35_evaluate_28_master_safety_gates_alias_and_local_donor_mode(self) -> None:
        self.assertIs(evaluate_28_master_safety_gates, evaluate_28gate_preflight)
        rep = evaluate_28_master_safety_gates(DEFAULT_REPO_ROOT, dry_run_simulated_backup=True)
        self.assertTrue(rep.all_28_gates_verified)
        self.assertEqual(rep.summary["verified_gates"], 28)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.persistent_write_release)

    def test_36_donor_corruption_propagates_and_prior_cli_subcommands_intact(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            fx3_lib = tmp / "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib"
            fx3_seed = tmp / "fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds"
            fx6_lib = tmp / "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib"
            fx6_seed = tmp / "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/tree/0110_backup/SYSIPSX-DSLR/CHAPLIN"
            for d in (fx3_lib, fx3_seed, fx6_lib, fx6_seed):
                d.mkdir(parents=True)
            (fx3_lib / "libfan.so").write_bytes(b"bad")
            (fx3_lib / "libBusPower.so").write_bytes(b"bad")
            (fx3_lib / "libUsbBusPower.so").write_bytes(b"bad")
            (fx6_lib / "libfan.so").write_bytes(b"bad")
            (fx3_seed / "FX3-CX95900_ALLLANG-Backup.bin").write_bytes(b"bad")
            (fx6_seed / "CX95898_NTSC.bin").write_bytes(b"bad")
            v27, r27 = evaluate_g27_sensor_curtain_and_ibis_transport(work_root=tmp, force_clean_room=False)
            v28, r28 = evaluate_g28_subzero_esr_and_altitude(work_root=tmp, force_clean_room=False)
        self.assertFalse(v27.passed)
        self.assertFalse(r27.valid)
        self.assertEqual(v27.status, STATUS_BLOCKED_DONOR_INTEGRITY)
        self.assertFalse(v28.passed)
        self.assertFalse(r28.valid)
        self.assertEqual(v28.status, STATUS_BLOCKED_DONOR_INTEGRITY)

        for subcmd in (
            "verify-16-gates",
            "verify-18-gates",
            "verify-20-gates",
            "verify-22-gates",
            "verify-24-gates",
            "verify-26-gates",
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = package_cli_main([subcmd, "--clean-room", "--json"])
            self.assertEqual(rc, 0, f"{subcmd} failed with rc={rc}")
            payload = json.loads(buf.getvalue())
            self.assertFalse(payload["persistent_emmc_writes_authorized"])


if __name__ == "__main__":
    unittest.main()
