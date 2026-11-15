"""Fast dual-mode unit tests for Phase 108 — Coastal Salt-Spray / Studio Glycol-Haze
Fan Ingestion Firewall (Gate G33), Wireless Follow-Focus Hard-Stop Lens-Barrel Torque &
Gimbal Dynamic CoG Shift Guard (Gate G34), and Unified 34-Gate Master Safety Preflight
(`G01..G34`).
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
from fx3_safety.pl_cantilever_dummybatt_and_32gate_guard import (
    STATUS_BLOCKED_DUMMY_BATTERY_OVER_VOLTAGE_BLOWOUT,
    STATUS_BLOCKED_UNSUPPORTED_CANTILEVER_FLANGE_WARP,
    evaluate_32gate_preflight,
)
from fx3_safety.rig_groundloop_lensrail_and_20gate_guard import (
    STATUS_FAIL_OFFLINE_HARDWARE_NOT_ATTACHED,
)
from fx3_safety.saltspray_haze_followfocus_and_34gate_guard import (
    DEFAULT_15MM_ROD_CANTILEVER_MM,
    DEFAULT_FIZ_GEAR_PITCH_RADIUS_MM,
    FIZ_SINGLE_ROD_MAX_TORQUE_NM,
    FIZ_UNCALIBRATED_MAX_TORQUE_NM,
    G33_GATE_CODE,
    G33_GATE_ID,
    G34_GATE_CODE,
    G34_GATE_ID,
    GIMBAL_MAX_UNAUTOTUNED_ZOOM_COG_SHIFT_MM,
    HAZE_MAX_CONTINUOUS_FAN_MIN,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PM10_DUST_MAX_UNFILTERED_UG_M3,
    ROD_15MM_FLEXURAL_EI_NM2,
    SALTSPRAY_HAZE_FOLLOWFOCUS_34GATE_SCHEMA,
    SALTSPRAY_HAZE_FOLLOWFOCUS_34GATE_VERSION,
    SIGMA_BLOWER_NOMINAL_AIRFLOW_L_MIN,
    STATUS_BLOCKED_CORROSIVE_SALTSPRAY_UNSEALED_DUCT,
    STATUS_BLOCKED_DONOR_INTEGRITY,
    STATUS_BLOCKED_FINE_ALKALI_DUST_ABRASION_HAZARD,
    STATUS_BLOCKED_FOLLOWFOCUS_GIMBAL_TELEMETRY_INVALID,
    STATUS_BLOCKED_FOLLOWFOCUS_UNCALIBRATED_HARDSTOP_TORQUE,
    STATUS_BLOCKED_GIMBAL_TELESCOPING_COG_OSCILLATION,
    STATUS_BLOCKED_OIL_GLYCOL_HAZE_FIN_FOULING,
    STATUS_BLOCKED_PERSISTENT_EMMC_WRITE,
    STATUS_BLOCKED_SALTSPRAY_HAZE_TELEMETRY_INVALID,
    STATUS_BLOCKED_SINGLE_ROD_FIZ_DEFLECTION_SLIP,
    STATUS_SAFE,
    STATUS_VERIFIED_G33,
    STATUS_VERIFIED_G34,
    STATUS_VERIFIED_SAFE,
    STUDIO_HAZE_MAX_UNPURGED_MG_M3,
    audit_phase108_donor_contracts,
    compute_estimated_ingested_aerosol_ug,
    compute_fiz_gear_tangential_force_n,
    compute_gimbal_cog_torque_imbalance_nm,
    compute_haze_fin_fouling_dose_mg_min_m3,
    compute_single_rod_deflection_mm,
    evaluate_34_master_safety_gates,
    evaluate_34gate_preflight,
    evaluate_g33_saltspray_alkali_dust_and_haze,
    evaluate_g34_followfocus_hardstop_and_gimbal_cog,
    main as module_cli_main,
    verify_followfocus_hardstop_and_gimbal_cog_guard,
    verify_saltspray_alkali_dust_and_haze_firewall,
)


class SaltsprayHazeFollowFocusAnd34GateGuardTests(unittest.TestCase):
    # --- 1. Hard Redlines, Package Exports & O_RDONLY Donor Audit ---

    def test_01_hard_locked_redlines_and_package_exports(self) -> None:
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(PERSISTENT_WRITE_RELEASE)
        self.assertEqual(
            SALTSPRAY_HAZE_FOLLOWFOCUS_34GATE_SCHEMA,
            "fx3-saltspray-haze-followfocus-34gate-preflight-v1",
        )
        self.assertEqual(SALTSPRAY_HAZE_FOLLOWFOCUS_34GATE_VERSION, "1.0.0")
        for sym in (
            "SALTSPRAY_HAZE_FOLLOWFOCUS_34GATE_SCHEMA",
            "G33_GATE_ID",
            "G33_GATE_CODE",
            "G34_GATE_ID",
            "G34_GATE_CODE",
            "STATUS_BLOCKED_CORROSIVE_SALTSPRAY_UNSEALED_DUCT",
            "STATUS_BLOCKED_FINE_ALKALI_DUST_ABRASION_HAZARD",
            "STATUS_BLOCKED_OIL_GLYCOL_HAZE_FIN_FOULING",
            "STATUS_BLOCKED_FOLLOWFOCUS_UNCALIBRATED_HARDSTOP_TORQUE",
            "STATUS_BLOCKED_SINGLE_ROD_FIZ_DEFLECTION_SLIP",
            "STATUS_BLOCKED_GIMBAL_TELESCOPING_COG_OSCILLATION",
            "audit_phase108_donor_contracts",
            "compute_haze_fin_fouling_dose_mg_min_m3",
            "compute_estimated_ingested_aerosol_ug",
            "compute_fiz_gear_tangential_force_n",
            "compute_single_rod_deflection_mm",
            "compute_gimbal_cog_torque_imbalance_nm",
            "verify_saltspray_alkali_dust_and_haze_firewall",
            "verify_followfocus_hardstop_and_gimbal_cog_guard",
            "evaluate_g33_saltspray_alkali_dust_and_haze",
            "evaluate_g34_followfocus_hardstop_and_gimbal_cog",
            "evaluate_34gate_preflight",
            "evaluate_34_master_safety_gates",
            "saltspray_haze_followfocus_and_34gate_guard",
        ):
            self.assertIn(sym, fx3_safety.__all__)
            self.assertTrue(hasattr(fx3_safety, sym))
        # Prior Phase exports must remain intact
        self.assertEqual(fx3_safety.FAN_MODE_AUTO1, "AUTO1")
        self.assertEqual(
            fx3_safety.STATUS_BLOCKED_DONOR_INTEGRITY,
            "BLOCKED_USBLAN_PTPIP_DONOR_INTEGRITY_MISMATCH",
        )
        self.assertEqual(fx3_safety.NP_FZ100_MAX_CHARGED_VOLTAGE_V, 8.40)

    def test_02_donor_audit_o_rdonly_and_clean_room_fallback(self) -> None:
        observed_flags = []
        orig_open = os.open

        def spy_open(path, flags, *args, **kwargs):
            observed_flags.append((str(path), flags))
            return orig_open(path, flags, *args, **kwargs)

        with patch("os.open", side_effect=spy_open):
            res_default = audit_phase108_donor_contracts()
        self.assertTrue(res_default.valid)
        self.assertEqual(res_default.status, STATUS_VERIFIED_SAFE)
        self.assertEqual(res_default.access_mode, "O_RDONLY")
        self.assertEqual(len(res_default.missing_markers), 0)
        self.assertTrue(res_default.sigma_fan_tokens_verified)
        self.assertTrue(res_default.emount_lens_comm_tokens_verified)
        self.assertTrue(res_default.ext_cmd_svc_tokens_verified)
        for path, flags in observed_flags:
            if any(
                k in path
                for k in (
                    "libfan",
                    "libInfraLensCommunicator",
                    "libInfraExtCmdSvc",
                )
            ):
                self.assertEqual(
                    flags & os.O_ACCMODE,
                    os.O_RDONLY,
                    f"Non-O_RDONLY open on {path}",
                )

        res_clean = audit_phase108_donor_contracts(force_clean_room=True)
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
            for d in (fx3_lib, fx6_lib):
                for name in (
                    "libfan.so",
                    "libInfraLensCommunicator.so",
                    "libInfraExtCmdSvc.so",
                ):
                    (d / name).write_bytes(b"corrupt")
            res = audit_phase108_donor_contracts(work_root=tmp, force_clean_room=False)
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_DONOR_INTEGRITY)
        self.assertEqual(len(res.missing_markers), 6)
        self.assertFalse(res.sigma_fan_tokens_verified)
        self.assertFalse(res.emount_lens_comm_tokens_verified)
        self.assertFalse(res.ext_cmd_svc_tokens_verified)

    def test_04_donor_audit_clean_room_and_missing_work_root_fallback(self) -> None:
        res_clean = audit_phase108_donor_contracts(
            force_clean_room=True, include_large_binaries=True
        )
        self.assertTrue(res_clean.valid)
        self.assertFalse(res_clean.large_binaries_scanned)

        with tempfile.TemporaryDirectory() as empty_dir:
            res_absent = audit_phase108_donor_contracts(
                work_root=Path(empty_dir), force_clean_room=False
            )
        self.assertTrue(res_absent.valid)
        self.assertEqual(res_absent.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(res_absent.files_inspected, 0)

    # --- 2. Physics & Aerosol Helpers ---

    def test_05_aerosol_and_fouling_helpers(self) -> None:
        dose = compute_haze_fin_fouling_dose_mg_min_m3(30.0, 60.0)
        self.assertAlmostEqual(dose, 1800.0, places=6)
        ingested = compute_estimated_ingested_aerosol_ug(1000.0, 10.0)
        expected_ug = 1000.0 * (SIGMA_BLOWER_NOMINAL_AIRFLOW_L_MIN * 10.0 / 1000.0)
        self.assertAlmostEqual(ingested, expected_ug, places=6)
        with self.assertRaises(ValueError):
            compute_haze_fin_fouling_dose_mg_min_m3(-1.0, 10.0)
        with self.assertRaises(ValueError):
            compute_estimated_ingested_aerosol_ug(100.0, -5.0)

    def test_06_followfocus_rod_deflection_and_gimbal_cog_helpers(self) -> None:
        f_n = compute_fiz_gear_tangential_force_n(3.0, DEFAULT_FIZ_GEAR_PITCH_RADIUS_MM)
        self.assertAlmostEqual(f_n, 200.0, places=6)
        delta_mm = compute_single_rod_deflection_mm(f_n, DEFAULT_15MM_ROD_CANTILEVER_MM)
        expected_delta = (
            (200.0 * (0.12**3)) / (3.0 * ROD_15MM_FLEXURAL_EI_NM2)
        ) * 1000.0
        self.assertAlmostEqual(delta_mm, expected_delta, places=6)
        self.assertGreater(delta_mm, 0.5)

        tau_cog = compute_gimbal_cog_torque_imbalance_nm(2.0, 20.0)
        self.assertAlmostEqual(tau_cog, 2.0 * 9.80665 * 0.02, places=6)

        with self.assertRaises(ValueError):
            compute_fiz_gear_tangential_force_n(1.0, 0.0)
        with self.assertRaises(ValueError):
            compute_single_rod_deflection_mm(100.0, 0.0)
        with self.assertRaises(ValueError):
            compute_gimbal_cog_torque_imbalance_nm(-0.5, 10.0)

    # --- 3. Gate G33 — Coastal Salt-Spray / Alkali Dust / Studio Glycol-Haze ---

    def test_07_g33_default_clean_interior_passes(self) -> None:
        res = verify_saltspray_alkali_dust_and_haze_firewall()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_SAFE)
        self.assertEqual(res.violation_codes, ())
        self.assertTrue(res.saltspray_duct_safe)
        self.assertTrue(res.alkali_dust_filtration_safe)
        self.assertTrue(res.glycol_haze_fouling_safe)
        self.assertFalse(res.persistent_emmc_writes_authorized)

    def test_08_g33_blocks_corrosive_saltspray_unsealed_duct(self) -> None:
        res_bad = verify_saltspray_alkali_dust_and_haze_firewall(
            environment_profile="SURF_BREAK_SHORELINE",
            coastal_salt_spray_env=True,
            hydrophobic_vent_membrane_or_housing=False,
        )
        self.assertFalse(res_bad.valid)
        self.assertFalse(res_bad.saltspray_duct_safe)
        self.assertEqual(res_bad.status, STATUS_BLOCKED_CORROSIVE_SALTSPRAY_UNSEALED_DUCT)

        res_ok = verify_saltspray_alkali_dust_and_haze_firewall(
            environment_profile="SURF_BREAK_SHORELINE",
            coastal_salt_spray_env=True,
            hydrophobic_vent_membrane_or_housing=True,
        )
        self.assertTrue(res_ok.valid)
        self.assertGreaterEqual(len(res_ok.warnings), 1)

    def test_09_g33_blocks_fine_alkali_dust_abrasion_hazard_and_boundary(self) -> None:
        res_bad = verify_saltspray_alkali_dust_and_haze_firewall(
            environment_profile="BLACK_ROCK_PLAYA_DUST_STORM",
            pm10_dust_ug_m3=850.0,
            intake_hepa_mesh_installed=False,
        )
        self.assertFalse(res_bad.valid)
        self.assertFalse(res_bad.alkali_dust_filtration_safe)
        self.assertEqual(res_bad.status, STATUS_BLOCKED_FINE_ALKALI_DUST_ABRASION_HAZARD)

        # Exact 600.0 ug/m^3 boundary passes without HEPA mesh
        res_edge = verify_saltspray_alkali_dust_and_haze_firewall(
            pm10_dust_ug_m3=PM10_DUST_MAX_UNFILTERED_UG_M3,
            intake_hepa_mesh_installed=False,
        )
        self.assertTrue(res_edge.valid)

        # Above 600.0 ug/m^3 passes when intake HEPA mesh is installed
        res_hepa = verify_saltspray_alkali_dust_and_haze_firewall(
            environment_profile="SAHARA_SILICA_WIND",
            pm10_dust_ug_m3=1200.0,
            intake_hepa_mesh_installed=True,
        )
        self.assertTrue(res_hepa.valid)
        self.assertGreaterEqual(len(res_hepa.warnings), 1)

    def test_10_g33_blocks_oil_glycol_haze_fin_fouling_and_boundaries(self) -> None:
        res_bad = verify_saltspray_alkali_dust_and_haze_firewall(
            environment_profile="SOUNDSTAGE_MINERAL_OIL_HAZE",
            studio_haze_density_mg_m3=40.0,
            continuous_fan_exposure_min=90.0,
            post_wrap_isopropyl_duct_purge_scheduled=False,
        )
        self.assertFalse(res_bad.valid)
        self.assertFalse(res_bad.glycol_haze_fouling_safe)
        self.assertEqual(res_bad.status, STATUS_BLOCKED_OIL_GLYCOL_HAZE_FIN_FOULING)
        self.assertAlmostEqual(res_bad.haze_exposure_dose_mg_min_m3, 3600.0, places=2)

        # Exact 25.0 mg/m^3 or <= 45.0 min boundary passes without purge scheduled
        res_edge_density = verify_saltspray_alkali_dust_and_haze_firewall(
            studio_haze_density_mg_m3=STUDIO_HAZE_MAX_UNPURGED_MG_M3,
            continuous_fan_exposure_min=90.0,
            post_wrap_isopropyl_duct_purge_scheduled=False,
        )
        self.assertTrue(res_edge_density.valid)

        res_edge_time = verify_saltspray_alkali_dust_and_haze_firewall(
            studio_haze_density_mg_m3=45.0,
            continuous_fan_exposure_min=HAZE_MAX_CONTINUOUS_FAN_MIN,
            post_wrap_isopropyl_duct_purge_scheduled=False,
        )
        self.assertTrue(res_edge_time.valid)

        # Post-wrap isopropyl duct purge scheduled permits heavy haze shoot
        res_purged = verify_saltspray_alkali_dust_and_haze_firewall(
            environment_profile="SOUNDSTAGE_GLYCOL_FOG",
            studio_haze_density_mg_m3=45.0,
            continuous_fan_exposure_min=120.0,
            post_wrap_isopropyl_duct_purge_scheduled=True,
        )
        self.assertTrue(res_purged.valid)
        self.assertGreaterEqual(len(res_purged.warnings), 1)

    def test_11_g33_rejects_invalid_telemetry_and_persistent_emmc_write(self) -> None:
        for kw in (
            {"pm10_dust_ug_m3": float("nan")},
            {"pm10_dust_ug_m3": -10.0},
            {"studio_haze_density_mg_m3": float("inf")},
            {"studio_haze_density_mg_m3": -0.1},
            {"continuous_fan_exposure_min": -5.0},
        ):
            res_bad = verify_saltspray_alkali_dust_and_haze_firewall(**kw)
            self.assertFalse(res_bad.valid)
            self.assertEqual(res_bad.status, STATUS_BLOCKED_SALTSPRAY_HAZE_TELEMETRY_INVALID)

        res_emmc = verify_saltspray_alkali_dust_and_haze_firewall(
            request_persistent_emmc_writes=True
        )
        self.assertFalse(res_emmc.valid)
        self.assertEqual(res_emmc.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        self.assertFalse(res_emmc.persistent_emmc_writes_authorized)

    def test_12_g33_accumulates_all_three_violations_deterministically(self) -> None:
        res = verify_saltspray_alkali_dust_and_haze_firewall(
            environment_profile="BEACH_SAND_FOG_EXTREME",
            coastal_salt_spray_env=True,
            hydrophobic_vent_membrane_or_housing=False,
            pm10_dust_ug_m3=900.0,
            intake_hepa_mesh_installed=False,
            studio_haze_density_mg_m3=35.0,
            continuous_fan_exposure_min=60.0,
            post_wrap_isopropyl_duct_purge_scheduled=False,
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            set(res.violation_codes),
            {
                STATUS_BLOCKED_CORROSIVE_SALTSPRAY_UNSEALED_DUCT,
                STATUS_BLOCKED_FINE_ALKALI_DUST_ABRASION_HAZARD,
                STATUS_BLOCKED_OIL_GLYCOL_HAZE_FIN_FOULING,
            },
        )

    # --- 4. Gate G34 — Wireless Follow-Focus & Gimbal Dynamic CoG Shift Guard ---

    def test_13_g34_default_handheld_prime_passes(self) -> None:
        res = verify_followfocus_hardstop_and_gimbal_cog_guard()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_SAFE)
        self.assertEqual(res.violation_codes, ())
        self.assertTrue(res.hardstop_torque_safe)
        self.assertTrue(res.rod_deflection_mesh_safe)
        self.assertTrue(res.gimbal_cog_oscillation_safe)
        self.assertFalse(res.persistent_emmc_writes_authorized)

    def test_14_g34_blocks_uncalibrated_hardstop_torque(self) -> None:
        # 2.8 N*m Nucleus-M/Preston without A-B calibration on brass/hard-stop lens
        res_bad = verify_followfocus_hardstop_and_gimbal_cog_guard(
            rig_profile="VINTAGE_CINE_PRIME_NUCLEUS_M",
            wireless_fiz_motor_torque_nm=2.8,
            hard_stops_calibrated=False,
            fly_by_wire_infinite_ring=False,
            dual_rod_or_cage_bridge_clamp=True,
        )
        self.assertFalse(res_bad.valid)
        self.assertFalse(res_bad.hardstop_torque_safe)
        self.assertEqual(
            res_bad.status, STATUS_BLOCKED_FOLLOWFOCUS_UNCALIBRATED_HARDSTOP_TORQUE
        )

        # Exact 1.2 N*m boundary passes
        res_edge = verify_followfocus_hardstop_and_gimbal_cog_guard(
            wireless_fiz_motor_torque_nm=FIZ_UNCALIBRATED_MAX_TORQUE_NM,
            hard_stops_calibrated=False,
            fly_by_wire_infinite_ring=False,
            dual_rod_or_cage_bridge_clamp=True,
        )
        self.assertTrue(res_edge.valid)

        # Fly-by-wire infinite ring or calibrated A-B stops pass with dual-rod clamp
        res_fbw = verify_followfocus_hardstop_and_gimbal_cog_guard(
            wireless_fiz_motor_torque_nm=2.8,
            hard_stops_calibrated=False,
            fly_by_wire_infinite_ring=True,
            dual_rod_or_cage_bridge_clamp=True,
        )
        self.assertTrue(res_fbw.valid)
        self.assertGreaterEqual(len(res_fbw.warnings), 1)

        res_cal = verify_followfocus_hardstop_and_gimbal_cog_guard(
            wireless_fiz_motor_torque_nm=3.5,
            hard_stops_calibrated=True,
            fly_by_wire_infinite_ring=False,
            dual_rod_or_cage_bridge_clamp=True,
        )
        self.assertTrue(res_cal.valid)

    def test_15_g34_blocks_single_rod_fiz_deflection_slip(self) -> None:
        res_bad = verify_followfocus_hardstop_and_gimbal_cog_guard(
            rig_profile="SINGLE_15MM_ROD_TILTA_MOTOR",
            wireless_fiz_motor_torque_nm=2.6,
            hard_stops_calibrated=True,
            fly_by_wire_infinite_ring=False,
            dual_rod_or_cage_bridge_clamp=False,
        )
        self.assertFalse(res_bad.valid)
        self.assertFalse(res_bad.rod_deflection_mesh_safe)
        self.assertEqual(res_bad.status, STATUS_BLOCKED_SINGLE_ROD_FIZ_DEFLECTION_SLIP)
        self.assertGreater(res_bad.single_rod_deflection_mm, 0.5)

        # Exact 1.8 N*m boundary passes even on single rod
        res_edge = verify_followfocus_hardstop_and_gimbal_cog_guard(
            wireless_fiz_motor_torque_nm=FIZ_SINGLE_ROD_MAX_TORQUE_NM,
            hard_stops_calibrated=True,
            dual_rod_or_cage_bridge_clamp=False,
        )
        self.assertTrue(res_edge.valid)

    def test_16_g34_blocks_gimbal_telescoping_cog_oscillation(self) -> None:
        res_bad = verify_followfocus_hardstop_and_gimbal_cog_guard(
            rig_profile="RS4_PRO_24_70_GM2_TELESCOPING",
            gimbal_mounted=True,
            zoom_cog_shift_mm=21.5,
            gimbal_autotune_after_zoom=False,
            rig_mass_kg=2.1,
        )
        self.assertFalse(res_bad.valid)
        self.assertFalse(res_bad.gimbal_cog_oscillation_safe)
        self.assertEqual(res_bad.status, STATUS_BLOCKED_GIMBAL_TELESCOPING_COG_OSCILLATION)
        self.assertGreater(res_bad.gimbal_cog_torque_imbalance_nm, 0.4)

        # Exact 15.0 mm shift passes without re-autotune
        res_edge = verify_followfocus_hardstop_and_gimbal_cog_guard(
            gimbal_mounted=True,
            zoom_cog_shift_mm=GIMBAL_MAX_UNAUTOTUNED_ZOOM_COG_SHIFT_MM,
            gimbal_autotune_after_zoom=False,
        )
        self.assertTrue(res_edge.valid)

        # Re-autotuned after zoom passes with advisory warning
        res_tuned = verify_followfocus_hardstop_and_gimbal_cog_guard(
            gimbal_mounted=True,
            zoom_cog_shift_mm=22.0,
            gimbal_autotune_after_zoom=True,
        )
        self.assertTrue(res_tuned.valid)
        self.assertGreaterEqual(len(res_tuned.warnings), 1)

        # Tripod/shoulder (gimbal_mounted=False) unaffected by zoom CoG shift
        res_tripod = verify_followfocus_hardstop_and_gimbal_cog_guard(
            gimbal_mounted=False,
            zoom_cog_shift_mm=28.0,
            gimbal_autotune_after_zoom=False,
        )
        self.assertTrue(res_tripod.valid)

    def test_17_g34_rejects_invalid_telemetry_and_persistent_emmc_write(self) -> None:
        for kw in (
            {"wireless_fiz_motor_torque_nm": float("nan")},
            {"wireless_fiz_motor_torque_nm": -0.5},
            {"zoom_cog_shift_mm": float("inf")},
            {"zoom_cog_shift_mm": -1.0},
            {"rig_mass_kg": -0.1},
            {"gear_pitch_radius_mm": 0.0},
            {"rod_cantilever_mm": -10.0},
        ):
            res_bad = verify_followfocus_hardstop_and_gimbal_cog_guard(**kw)
            self.assertFalse(res_bad.valid)
            self.assertEqual(
                res_bad.status, STATUS_BLOCKED_FOLLOWFOCUS_GIMBAL_TELEMETRY_INVALID
            )

        res_emmc = verify_followfocus_hardstop_and_gimbal_cog_guard(
            request_persistent_emmc_writes=True
        )
        self.assertFalse(res_emmc.valid)
        self.assertEqual(res_emmc.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        self.assertFalse(res_emmc.persistent_emmc_writes_authorized)

    def test_18_g34_accumulates_all_three_violations_deterministically(self) -> None:
        res = verify_followfocus_hardstop_and_gimbal_cog_guard(
            wireless_fiz_motor_torque_nm=3.6,
            hard_stops_calibrated=False,
            fly_by_wire_infinite_ring=False,
            dual_rod_or_cage_bridge_clamp=False,
            gimbal_mounted=True,
            zoom_cog_shift_mm=24.0,
            gimbal_autotune_after_zoom=False,
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            set(res.violation_codes),
            {
                STATUS_BLOCKED_FOLLOWFOCUS_UNCALIBRATED_HARDSTOP_TORQUE,
                STATUS_BLOCKED_SINGLE_ROD_FIZ_DEFLECTION_SLIP,
                STATUS_BLOCKED_GIMBAL_TELESCOPING_COG_OSCILLATION,
            },
        )

    # --- 5. Gate G33 & G34 Evaluators & Unified 34-Gate Master Preflight ---

    def test_19_g33_and_g34_verdicts_dual_mode(self) -> None:
        v33, r33 = evaluate_g33_saltspray_alkali_dust_and_haze(force_clean_room=True)
        self.assertTrue(v33.passed)
        self.assertEqual(v33.gate_id, G33_GATE_ID)
        self.assertEqual(v33.gate_code, G33_GATE_CODE)
        self.assertEqual(v33.status, STATUS_VERIFIED_G33)
        self.assertFalse(r33.persistent_emmc_writes_authorized)

        v34, r34 = evaluate_g34_followfocus_hardstop_and_gimbal_cog(force_clean_room=True)
        self.assertTrue(v34.passed)
        self.assertEqual(v34.gate_id, G34_GATE_ID)
        self.assertEqual(v34.gate_code, G34_GATE_CODE)
        self.assertEqual(v34.status, STATUS_VERIFIED_G34)
        self.assertFalse(r34.persistent_emmc_writes_authorized)

    def test_20_34gate_offline_default_31_of_34_and_g10_g12_fail_offline(self) -> None:
        rep = evaluate_34gate_preflight(DEFAULT_REPO_ROOT, force_clean_room=True)
        self.assertEqual(rep.schema, SALTSPRAY_HAZE_FOLLOWFOCUS_34GATE_SCHEMA)
        self.assertEqual(len(rep.gates), 34)
        self.assertEqual(rep.summary["total_gates"], 34)
        self.assertEqual(rep.summary["verified_gates"], 31)
        self.assertEqual(rep.summary["blocked_or_pending_gates"], 3)
        self.assertTrue(rep.offline_31_gates_verified)
        self.assertFalse(rep.all_34_gates_verified)
        self.assertFalse(rep.dry_run_rehearsal_only)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.persistent_write_release)
        self.assertEqual(rep.status, "VERIFIED_31_OF_34_AWAITING_PHYSICAL_TIER0")
        for idx in (9, 10, 11):
            self.assertFalse(rep.gates[idx]["passed"])
            self.assertEqual(
                rep.gates[idx]["status"], STATUS_FAIL_OFFLINE_HARDWARE_NOT_ATTACHED
            )

    def test_21_34gate_dry_run_simulated_backup_34_of_34_and_redlines_locked(self) -> None:
        rep = evaluate_34gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
        )
        self.assertEqual(len(rep.gates), 34)
        self.assertEqual(rep.summary["verified_gates"], 34)
        self.assertEqual(rep.summary["blocked_or_pending_gates"], 0)
        self.assertEqual(rep.summary["g01_to_g12_verified"], 12)
        self.assertEqual(rep.summary["g13_to_g32_verified"], 20)
        self.assertEqual(rep.summary["g33_to_g34_verified"], 2)
        self.assertTrue(rep.all_34_gates_verified)
        self.assertTrue(rep.dry_run_rehearsal_only)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.persistent_write_release)
        self.assertEqual(rep.status, "VERIFIED_ALL_34_GATES_DRY_RUN_SIMULATED_BACKUP")
        self.assertTrue(all(g["passed"] for g in rep.gates))

    def test_22_34gate_propagates_g33_saltspray_dust_and_haze_failures(self) -> None:
        rep_salt = evaluate_34gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            saltspray_haze_kwargs={
                "coastal_salt_spray_env": True,
                "hydrophobic_vent_membrane_or_housing": False,
            },
        )
        self.assertFalse(rep_salt.all_34_gates_verified)
        self.assertFalse(rep_salt.g33_to_g34_all_passed)
        self.assertFalse(rep_salt.gates[32]["passed"])
        self.assertEqual(rep_salt.status, STATUS_BLOCKED_CORROSIVE_SALTSPRAY_UNSEALED_DUCT)

        rep_dust = evaluate_34gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            saltspray_haze_kwargs={
                "pm10_dust_ug_m3": 720.0,
                "intake_hepa_mesh_installed": False,
            },
        )
        self.assertFalse(rep_dust.all_34_gates_verified)
        self.assertEqual(rep_dust.status, STATUS_BLOCKED_FINE_ALKALI_DUST_ABRASION_HAZARD)

        rep_haze = evaluate_34gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            saltspray_haze_kwargs={
                "studio_haze_density_mg_m3": 32.0,
                "continuous_fan_exposure_min": 55.0,
                "post_wrap_isopropyl_duct_purge_scheduled": False,
            },
        )
        self.assertFalse(rep_haze.all_34_gates_verified)
        self.assertEqual(rep_haze.status, STATUS_BLOCKED_OIL_GLYCOL_HAZE_FIN_FOULING)

    def test_23_34gate_propagates_g34_fiz_rod_and_gimbal_cog_failures(self) -> None:
        rep_stop = evaluate_34gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            followfocus_gimbal_kwargs={
                "wireless_fiz_motor_torque_nm": 2.9,
                "hard_stops_calibrated": False,
                "fly_by_wire_infinite_ring": False,
            },
        )
        self.assertFalse(rep_stop.all_34_gates_verified)
        self.assertFalse(rep_stop.gates[33]["passed"])
        self.assertEqual(
            rep_stop.status, STATUS_BLOCKED_FOLLOWFOCUS_UNCALIBRATED_HARDSTOP_TORQUE
        )

        rep_rod = evaluate_34gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            followfocus_gimbal_kwargs={
                "wireless_fiz_motor_torque_nm": 2.5,
                "hard_stops_calibrated": True,
                "dual_rod_or_cage_bridge_clamp": False,
            },
        )
        self.assertFalse(rep_rod.all_34_gates_verified)
        self.assertEqual(rep_rod.status, STATUS_BLOCKED_SINGLE_ROD_FIZ_DEFLECTION_SLIP)

        rep_cog = evaluate_34gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            followfocus_gimbal_kwargs={
                "gimbal_mounted": True,
                "zoom_cog_shift_mm": 19.0,
                "gimbal_autotune_after_zoom": False,
            },
        )
        self.assertFalse(rep_cog.all_34_gates_verified)
        self.assertEqual(rep_cog.status, STATUS_BLOCKED_GIMBAL_TELESCOPING_COG_OSCILLATION)

    def test_24_34gate_propagates_g31_g32_and_emmc_redline(self) -> None:
        rep_g31_g32 = evaluate_34gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            pl_cantilever_kwargs={
                "lens_plus_mattebox_kg": 2.2,
                "l_cg_mm": 130.0,
                "lws_15mm_y_support_engaged": False,
            },
            dummy_battery_kwargs={
                "dummy_battery_installed": True,
                "measured_open_circuit_v": 15.0,
                "buck_regulator_ovp_crowbar_verified": False,
            },
        )
        self.assertFalse(rep_g31_g32.all_34_gates_verified)
        self.assertFalse(rep_g31_g32.gates[30]["passed"])
        self.assertFalse(rep_g31_g32.gates[31]["passed"])
        self.assertEqual(
            rep_g31_g32.gates[30]["status"],
            STATUS_BLOCKED_UNSUPPORTED_CANTILEVER_FLANGE_WARP,
        )
        self.assertEqual(
            rep_g31_g32.gates[31]["status"],
            STATUS_BLOCKED_DUMMY_BATTERY_OVER_VOLTAGE_BLOWOUT,
        )
        self.assertEqual(
            rep_g31_g32.status, STATUS_BLOCKED_UNSUPPORTED_CANTILEVER_FLANGE_WARP
        )

        rep_emmc = evaluate_34gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            request_persistent_emmc_writes=True,
        )
        self.assertFalse(rep_emmc.all_34_gates_verified)
        self.assertFalse(rep_emmc.offline_31_gates_verified)
        self.assertFalse(rep_emmc.overall_ready_for_hardware_attach)
        self.assertFalse(rep_emmc.persistent_emmc_writes_authorized)
        self.assertEqual(rep_emmc.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)

    def test_25_34gate_preserves_g01_to_g32_untouched(self) -> None:
        r32 = evaluate_32gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
        )
        r34 = evaluate_34gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
        )
        self.assertEqual(len(r32.gates), 32)
        self.assertEqual(len(r34.gates), 34)
        self.assertEqual(
            [g["gate_id"] for g in r32.gates],
            [g["gate_id"] for g in r34.gates[:32]],
        )
        self.assertEqual(
            [g["status"] for g in r32.gates],
            [g["status"] for g in r34.gates[:32]],
        )

    def test_26_serialized_json_contains_zero_raw_bytes_repr(self) -> None:
        rep = evaluate_34gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
        )
        rendered = json.dumps(rep.to_dict(), ensure_ascii=False)
        self.assertNotRegex(rendered, r'(?<![0-9A-Za-z_/.-])b[\x27"]')

    def test_27_cli_verify_34_gates_offline_and_dry_run_json(self) -> None:
        buf_off = io.StringIO()
        with contextlib.redirect_stdout(buf_off):
            rc_off = package_cli_main(["verify-34-gates", "--clean-room", "--json"])
        self.assertEqual(rc_off, 0)
        p_off = json.loads(buf_off.getvalue())
        self.assertEqual(p_off["schema"], SALTSPRAY_HAZE_FOLLOWFOCUS_34GATE_SCHEMA)
        self.assertEqual(p_off["summary"]["verified_gates"], 31)
        self.assertFalse(p_off["dry_run_rehearsal_only"])
        self.assertFalse(p_off["overall_ready_for_hardware_attach"])
        self.assertFalse(p_off["persistent_emmc_writes_authorized"])

        buf_dry = io.StringIO()
        with contextlib.redirect_stdout(buf_dry):
            rc_dry = package_cli_main(
                ["verify-34-gates", "--clean-room", "--dry-run-simulated-backup", "--json"]
            )
        self.assertEqual(rc_dry, 0)
        p_dry = json.loads(buf_dry.getvalue())
        self.assertEqual(p_dry["summary"]["verified_gates"], 34)
        self.assertTrue(p_dry["all_34_gates_verified"])
        self.assertTrue(p_dry["dry_run_rehearsal_only"])
        self.assertFalse(p_dry["overall_ready_for_hardware_attach"])
        self.assertFalse(p_dry["persistent_emmc_writes_authorized"])

    def test_28_cli_verify_34_gates_summary_and_failure_exit_code(self) -> None:
        buf_mod = io.StringIO()
        with contextlib.redirect_stdout(buf_mod):
            rc_mod = module_cli_main(["--clean-room"])
        self.assertEqual(rc_mod, 0)
        out = buf_mod.getvalue()
        self.assertIn("verified=31/34", out)
        self.assertIn("overall_ready_for_hardware_attach=False", out)
        self.assertIn("persistent_emmc_writes_authorized=False", out)

        buf_pkg = io.StringIO()
        with contextlib.redirect_stdout(buf_pkg):
            rc_pkg = package_cli_main(["verify-34-gates", "--clean-room"])
        self.assertEqual(rc_pkg, 0)
        self.assertIn("verified=31/34", buf_pkg.getvalue())

        with tempfile.TemporaryDirectory() as empty_dir:
            buf_fail = io.StringIO()
            with contextlib.redirect_stdout(buf_fail):
                rc_fail = package_cli_main(
                    ["verify-34-gates", "--repo-root", empty_dir, "--clean-room"]
                )
            self.assertEqual(rc_fail, 1)

    def test_29_env_force_clean_room_honored_end_to_end(self) -> None:
        with patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            rep = evaluate_34gate_preflight(DEFAULT_REPO_ROOT)
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(rep.clean_room_forced)
        self.assertTrue(rep.offline_31_gates_verified)
        self.assertFalse(rep.persistent_emmc_writes_authorized)

    def test_30_evaluate_34_master_safety_gates_alias_and_default_mode(self) -> None:
        self.assertIs(evaluate_34_master_safety_gates, evaluate_34gate_preflight)
        rep = evaluate_34_master_safety_gates(
            DEFAULT_REPO_ROOT, dry_run_simulated_backup=True
        )
        self.assertTrue(rep.all_34_gates_verified)
        self.assertEqual(rep.summary["verified_gates"], 34)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.persistent_write_release)

    def test_31_donor_corruption_propagates_to_g33_g34_and_34gate_report(self) -> None:
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
            for d in (fx3_lib, fx6_lib):
                for name in (
                    "libfan.so",
                    "libInfraLensCommunicator.so",
                    "libInfraExtCmdSvc.so",
                ):
                    (d / name).write_bytes(b"bad")
            v33, r33 = evaluate_g33_saltspray_alkali_dust_and_haze(
                work_root=tmp, force_clean_room=False
            )
            v34, r34 = evaluate_g34_followfocus_hardstop_and_gimbal_cog(
                work_root=tmp, force_clean_room=False
            )
        self.assertFalse(v33.passed)
        self.assertFalse(r33.valid)
        self.assertEqual(v33.status, STATUS_BLOCKED_DONOR_INTEGRITY)
        self.assertFalse(v34.passed)
        self.assertFalse(r34.valid)
        self.assertEqual(v34.status, STATUS_BLOCKED_DONOR_INTEGRITY)

    def test_32_prior_cli_subcommands_verify_16_through_32_remain_intact(self) -> None:
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
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = package_cli_main([subcmd, "--clean-room", "--json"])
            self.assertEqual(rc, 0, f"{subcmd} failed with rc={rc}")
            payload = json.loads(buf.getvalue())
            self.assertFalse(payload["persistent_emmc_writes_authorized"])

    def test_33_g34_gate_ids_and_soc_passthrough_in_34gate_report(self) -> None:
        rep = evaluate_34gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            soc_start_ceiling_c=58.0,
        )
        self.assertTrue(rep.all_34_gates_verified)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertEqual(rep.gates[32]["gate_id"], G33_GATE_ID)
        self.assertEqual(rep.gates[33]["gate_id"], G34_GATE_ID)

    def test_34_34gate_summary_blocks_if_g33_or_g34_requests_emmc_write(self) -> None:
        rep_33 = evaluate_34gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            saltspray_haze_kwargs={"request_persistent_emmc_writes": True},
        )
        self.assertFalse(rep_33.all_34_gates_verified)
        self.assertFalse(rep_33.g33_to_g34_all_passed)
        self.assertFalse(rep_33.gates[32]["passed"])
        self.assertEqual(rep_33.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        self.assertFalse(rep_33.persistent_emmc_writes_authorized)

        rep_34 = evaluate_34gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            followfocus_gimbal_kwargs={"request_persistent_emmc_writes": True},
        )
        self.assertFalse(rep_34.all_34_gates_verified)
        self.assertFalse(rep_34.g33_to_g34_all_passed)
        self.assertFalse(rep_34.gates[33]["passed"])
        self.assertEqual(rep_34.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        self.assertFalse(rep_34.persistent_emmc_writes_authorized)

    def test_35_g33_dual_condition_haze_requires_both_density_and_duration(self) -> None:
        # High density (30 > 25) but short duration (40 <= 45) passes
        res_short = verify_saltspray_alkali_dust_and_haze_firewall(
            studio_haze_density_mg_m3=30.0,
            continuous_fan_exposure_min=40.0,
            post_wrap_isopropyl_duct_purge_scheduled=False,
        )
        self.assertTrue(res_short.valid)

        # Long duration (120 > 45) but low density (10 <= 25) passes
        res_light = verify_saltspray_alkali_dust_and_haze_firewall(
            studio_haze_density_mg_m3=10.0,
            continuous_fan_exposure_min=120.0,
            post_wrap_isopropyl_duct_purge_scheduled=False,
        )
        self.assertTrue(res_light.valid)

    def test_36_g34_boundary_between_1_2_and_1_8_nm_on_single_rod(self) -> None:
        # 1.5 N*m on single rod: > 1.2 (needs calibrated or FBW), <= 1.8 (single rod OK)
        res_mid_ok = verify_followfocus_hardstop_and_gimbal_cog_guard(
            wireless_fiz_motor_torque_nm=1.5,
            hard_stops_calibrated=True,
            fly_by_wire_infinite_ring=False,
            dual_rod_or_cage_bridge_clamp=False,
        )
        self.assertTrue(res_mid_ok.valid)
        self.assertTrue(res_mid_ok.hardstop_torque_safe)
        self.assertTrue(res_mid_ok.rod_deflection_mesh_safe)

        res_mid_uncal = verify_followfocus_hardstop_and_gimbal_cog_guard(
            wireless_fiz_motor_torque_nm=1.5,
            hard_stops_calibrated=False,
            fly_by_wire_infinite_ring=False,
            dual_rod_or_cage_bridge_clamp=False,
        )
        self.assertFalse(res_mid_uncal.valid)
        self.assertEqual(
            res_mid_uncal.status,
            STATUS_BLOCKED_FOLLOWFOCUS_UNCALIBRATED_HARDSTOP_TORQUE,
        )
        self.assertTrue(res_mid_uncal.rod_deflection_mesh_safe)


if __name__ == "__main__":
    unittest.main()
