"""Fast dual-mode unit tests for Phase 104 — Heavy Cinema PL-to-E Adapter / Matte-Box
Cantilever Bending-Moment & 15mm LWS Lens-Support Guard (Gate G31), Unregulated
14.8V/26V V-Mount -> NP-FZ100 Dummy-Battery Over-Voltage Blowout Firewall (Gate G32),
and Unified 32-Gate Master Safety Preflight (`G01..G32`).
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
    CANTILEVER_DEFAULT_SHOCK_FACTOR_G,
    DUMMY_BATTERY_OPEN_CIRCUIT_MAX_V,
    EMOUNT_BACKFOCUS_TOLERANCE_MM,
    EMOUNT_FLANGE_FOCAL_DISTANCE_MM,
    EMOUNT_UNSUPPORTED_MAX_MASS_KG,
    EMOUNT_UNSUPPORTED_MAX_STATIC_MOMENT_NM,
    G31_GATE_CODE,
    G31_GATE_ID,
    G32_GATE_CODE,
    G32_GATE_ID,
    NP_FZ100_MAX_CHARGED_VOLTAGE_V,
    NP_FZ100_NOMINAL_VOLTAGE_V,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PL_ADAPTER_UNBOLTED_MAX_MASS_KG,
    PL_CANTILEVER_DUMMYBATT_32GATE_SCHEMA,
    PL_CANTILEVER_DUMMYBATT_32GATE_VERSION,
    SONY_CINEMA_SOP_POWER_TOPOLOGY,
    STATUS_BLOCKED_CLAMP_ON_MATTEBOX_TELESCOPING_BARREL,
    STATUS_BLOCKED_DONOR_INTEGRITY,
    STATUS_BLOCKED_DUMMY_BATTERY_OVER_VOLTAGE_BLOWOUT,
    STATUS_BLOCKED_DUMMY_BATT_TELEMETRY_INVALID,
    STATUS_BLOCKED_PERSISTENT_EMMC_WRITE,
    STATUS_BLOCKED_PL_CANTILEVER_TELEMETRY_INVALID,
    STATUS_BLOCKED_REVERSE_POLARITY_UNKEYED_DTAP,
    STATUS_BLOCKED_UNAUTHENTICATED_NON_INFOLITHIUM_SPOOF,
    STATUS_BLOCKED_UNSHIMMED_PL_ADAPTER_BACKFOCUS_DRIFT,
    STATUS_BLOCKED_UNSUPPORTED_CANTILEVER_FLANGE_WARP,
    STATUS_SAFE,
    STATUS_VERIFIED_G31,
    STATUS_VERIFIED_G32,
    STATUS_VERIFIED_SAFE,
    VMOUNT_HIGH_VOLTAGE_CINEMA_THRESHOLD_V,
    audit_phase104_donor_contracts,
    compute_cantilever_bending_moment_nm,
    compute_pmic_overvoltage_stress_ratio,
    evaluate_32_master_safety_gates,
    evaluate_32gate_preflight,
    evaluate_g31_pl_cantilever_and_lws_support,
    evaluate_g32_dummy_battery_overvoltage_firewall,
    main as module_cli_main,
    verify_dummy_battery_overvoltage_firewall,
    verify_pl_cantilever_and_emount_flange_guard,
)
from fx3_safety.rig_groundloop_lensrail_and_20gate_guard import (
    STATUS_FAIL_OFFLINE_HARDWARE_NOT_ATTACHED,
)
from fx3_safety.wireless_tx_emi_endurance_and_30gate_guard import (
    STATUS_BLOCKED_FAT32_4GIB_SPANNING_TRAP,
    STATUS_BLOCKED_NEARFIELD_WIRELESS_TX_EMI_DESENSE,
    evaluate_30gate_preflight,
)


class PlCantileverDummyBattAnd32GateGuardTests(unittest.TestCase):
    # --- 1. Hard Redlines, Package Exports & O_RDONLY Donor Audit ---

    def test_01_hard_locked_redlines_and_package_exports(self) -> None:
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(PERSISTENT_WRITE_RELEASE)
        self.assertEqual(
            PL_CANTILEVER_DUMMYBATT_32GATE_SCHEMA,
            "fx3-pl-cantilever-dummybatt-32gate-preflight-v1",
        )
        self.assertEqual(PL_CANTILEVER_DUMMYBATT_32GATE_VERSION, "1.0.0")
        for sym in (
            "PL_CANTILEVER_DUMMYBATT_32GATE_SCHEMA",
            "G31_GATE_ID",
            "G31_GATE_CODE",
            "G32_GATE_ID",
            "G32_GATE_CODE",
            "STATUS_BLOCKED_UNSUPPORTED_CANTILEVER_FLANGE_WARP",
            "STATUS_BLOCKED_UNSHIMMED_PL_ADAPTER_BACKFOCUS_DRIFT",
            "STATUS_BLOCKED_CLAMP_ON_MATTEBOX_TELESCOPING_BARREL",
            "STATUS_BLOCKED_DUMMY_BATTERY_OVER_VOLTAGE_BLOWOUT",
            "STATUS_BLOCKED_REVERSE_POLARITY_UNKEYED_DTAP",
            "STATUS_BLOCKED_UNAUTHENTICATED_NON_INFOLITHIUM_SPOOF",
            "audit_phase104_donor_contracts",
            "compute_cantilever_bending_moment_nm",
            "compute_pmic_overvoltage_stress_ratio",
            "verify_pl_cantilever_and_emount_flange_guard",
            "verify_dummy_battery_overvoltage_firewall",
            "evaluate_g31_pl_cantilever_and_lws_support",
            "evaluate_g32_dummy_battery_overvoltage_firewall",
            "evaluate_32gate_preflight",
            "evaluate_32_master_safety_gates",
            "pl_cantilever_dummybatt_and_32gate_guard",
        ):
            self.assertIn(sym, fx3_safety.__all__)
            self.assertTrue(hasattr(fx3_safety, sym))
        # Prior Phase exports must remain intact
        self.assertEqual(fx3_safety.FAN_MODE_AUTO1, "AUTO1")
        self.assertEqual(
            fx3_safety.STATUS_BLOCKED_DONOR_INTEGRITY,
            "BLOCKED_USBLAN_PTPIP_DONOR_INTEGRITY_MISMATCH",
        )
        self.assertEqual(fx3_safety.NP_FZ100_NOMINAL_MV, 7200)

    def test_02_donor_audit_o_rdonly_and_clean_room_fallback(self) -> None:
        observed_flags = []
        orig_open = os.open

        def spy_open(path, flags, *args, **kwargs):
            observed_flags.append((str(path), flags))
            return orig_open(path, flags, *args, **kwargs)

        with patch("os.open", side_effect=spy_open):
            res_default = audit_phase104_donor_contracts()
        self.assertTrue(res_default.valid)
        self.assertEqual(res_default.status, STATUS_VERIFIED_SAFE)
        self.assertEqual(res_default.access_mode, "O_RDONLY")
        self.assertEqual(len(res_default.missing_markers), 0)
        self.assertTrue(res_default.emount_lens_comm_tokens_verified)
        self.assertTrue(res_default.usbpd_bus_power_tokens_verified)
        self.assertTrue(res_default.batt_auth_infolithium_tokens_verified)
        for path, flags in observed_flags:
            if any(
                k in path
                for k in (
                    "libInfraLensCommunicator",
                    "libBusPower",
                    "libUsbBusPower",
                )
            ):
                self.assertEqual(flags & os.O_ACCMODE, os.O_RDONLY, f"Non-O_RDONLY open on {path}")

        res_clean = audit_phase104_donor_contracts(force_clean_room=True)
        self.assertTrue(res_clean.valid)
        self.assertEqual(res_clean.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(res_clean.files_inspected, 0)
        self.assertEqual(len(res_clean.sha256_by_artifact), 6)

    def test_03_donor_audit_blocks_integrity_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            fx3_lib = tmp / "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib"
            fx6_lib = tmp / "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib"
            fx3_lib.mkdir(parents=True)
            fx6_lib.mkdir(parents=True)
            for d in (fx3_lib, fx6_lib):
                for name in ("libInfraLensCommunicator.so", "libBusPower.so", "libUsbBusPower.so"):
                    (d / name).write_bytes(b"corrupt")
            res = audit_phase104_donor_contracts(work_root=tmp, force_clean_room=False)
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_DONOR_INTEGRITY)
        self.assertEqual(len(res.missing_markers), 6)
        self.assertFalse(res.emount_lens_comm_tokens_verified)
        self.assertFalse(res.usbpd_bus_power_tokens_verified)
        self.assertFalse(res.batt_auth_infolithium_tokens_verified)

    def test_04_donor_audit_clean_room_and_missing_work_root_fallback(self) -> None:
        res_clean = audit_phase104_donor_contracts(force_clean_room=True, include_large_binaries=True)
        self.assertTrue(res_clean.valid)
        self.assertFalse(res_clean.large_binaries_scanned)

        with tempfile.TemporaryDirectory() as empty_dir:
            res_absent = audit_phase104_donor_contracts(work_root=Path(empty_dir), force_clean_room=False)
        self.assertTrue(res_absent.valid)
        self.assertEqual(res_absent.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(res_absent.files_inspected, 0)

    # --- 2. Physics & Electrical Helpers ---

    def test_05_cantilever_moment_and_pmic_overvoltage_helpers(self) -> None:
        m_static = compute_cantilever_bending_moment_nm(2.0, 150.0)
        m_peak = compute_cantilever_bending_moment_nm(2.0, 150.0, shock_g=CANTILEVER_DEFAULT_SHOCK_FACTOR_G)
        self.assertAlmostEqual(m_static, 2.0 * 9.80665 * 0.15, places=6)
        self.assertAlmostEqual(m_peak, m_static * 2.5, places=6)
        self.assertEqual(compute_cantilever_bending_moment_nm(0.0, 100.0), 0.0)
        with self.assertRaises(ValueError):
            compute_cantilever_bending_moment_nm(1.5, 0.0)
        with self.assertRaises(ValueError):
            compute_cantilever_bending_moment_nm(1.5, 100.0, shock_g=0.5)

        self.assertAlmostEqual(compute_pmic_overvoltage_stress_ratio(8.40), 1.0, places=6)
        self.assertGreater(compute_pmic_overvoltage_stress_ratio(14.8), 1.75)
        self.assertGreater(compute_pmic_overvoltage_stress_ratio(26.0), 3.0)
        with self.assertRaises(ValueError):
            compute_pmic_overvoltage_stress_ratio(-1.0)

    # --- 3. Gate G31 — Heavy PL-to-E Cantilever & 15mm LWS Lens Support ---

    def test_06_g31_default_compact_emount_passes(self) -> None:
        res = verify_pl_cantilever_and_emount_flange_guard()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_SAFE)
        self.assertEqual(res.violation_codes, ())
        self.assertEqual(res.flange_focal_distance_mm, EMOUNT_FLANGE_FOCAL_DISTANCE_MM)
        self.assertEqual(res.backfocus_tolerance_mm, EMOUNT_BACKFOCUS_TOLERANCE_MM)
        self.assertTrue(res.cantilever_flange_safe)
        self.assertTrue(res.pl_adapter_backfocus_safe)
        self.assertTrue(res.mattebox_barrel_safe)
        self.assertFalse(res.persistent_emmc_writes_authorized)

    def test_07_g31_blocks_unsupported_heavy_mass_and_high_moment_cantilever(self) -> None:
        # > 1.2 kg even with short L_cg -> BLOCKED_UNSUPPORTED_CANTILEVER_FLANGE_WARP
        res_mass = verify_pl_cantilever_and_emount_flange_guard(
            rig_profile="ANAMORPHIC_2X_NO_RODS",
            lens_plus_mattebox_kg=1.45,
            l_cg_mm=70.0,
            lws_15mm_y_support_engaged=False,
        )
        self.assertFalse(res_mass.valid)
        self.assertFalse(res_mass.cantilever_flange_safe)
        self.assertEqual(res_mass.status, STATUS_BLOCKED_UNSUPPORTED_CANTILEVER_FLANGE_WARP)

        # <= 1.2 kg (1.1 kg) but long L_cg=200mm -> M_static=2.157 N*m > 1.8 N*m -> BLOCKED
        res_moment = verify_pl_cantilever_and_emount_flange_guard(
            rig_profile="LONG_TELEPHOTO_NO_Y_SUPPORT",
            lens_plus_mattebox_kg=1.10,
            l_cg_mm=200.0,
            lws_15mm_y_support_engaged=False,
        )
        self.assertFalse(res_moment.valid)
        self.assertFalse(res_moment.cantilever_flange_safe)
        self.assertGreater(res_moment.static_moment_nm, EMOUNT_UNSUPPORTED_MAX_STATIC_MOMENT_NM)
        self.assertGreater(res_moment.peak_moment_nm, 5.0)
        self.assertEqual(res_moment.status, STATUS_BLOCKED_UNSUPPORTED_CANTILEVER_FLANGE_WARP)

    def test_08_g31_cantilever_exact_boundaries_and_15mm_lws_mitigation(self) -> None:
        # Exact 1.2 kg mass & M_static <= 1.8 N*m passes
        res_mass_edge = verify_pl_cantilever_and_emount_flange_guard(
            lens_plus_mattebox_kg=EMOUNT_UNSUPPORTED_MAX_MASS_KG,
            l_cg_mm=100.0,
            lws_15mm_y_support_engaged=False,
        )
        self.assertTrue(res_mass_edge.valid)

        # Heavy 3.2 kg PL cinema zoom + swing-away matte box WITH 15mm LWS Y-support + bolted foot passes
        res_supported = verify_pl_cantilever_and_emount_flange_guard(
            rig_profile="ANGENIEUX_EZ_PL_15MM_LWS",
            lens_plus_mattebox_kg=3.20,
            l_cg_mm=145.0,
            lws_15mm_y_support_engaged=True,
            pl_to_e_adapter_used=True,
            adapter_foot_bolted_to_cage=True,
            clamp_on_mattebox=False,
        )
        self.assertTrue(res_supported.valid)
        self.assertTrue(res_supported.cantilever_flange_safe)
        self.assertTrue(res_supported.pl_adapter_backfocus_safe)
        self.assertGreaterEqual(len(res_supported.warnings), 1)

    def test_09_g31_blocks_unbolted_pl_adapter_backfocus_drift(self) -> None:
        res_unbolted = verify_pl_cantilever_and_emount_flange_guard(
            lens_plus_mattebox_kg=1.05,
            l_cg_mm=100.0,
            lws_15mm_y_support_engaged=True,
            pl_to_e_adapter_used=True,
            adapter_foot_bolted_to_cage=False,
        )
        self.assertFalse(res_unbolted.valid)
        self.assertFalse(res_unbolted.pl_adapter_backfocus_safe)
        self.assertEqual(res_unbolted.status, STATUS_BLOCKED_UNSHIMMED_PL_ADAPTER_BACKFOCUS_DRIFT)

        # At exact 0.9 kg boundary, unbolted adapter passes
        res_edge = verify_pl_cantilever_and_emount_flange_guard(
            lens_plus_mattebox_kg=PL_ADAPTER_UNBOLTED_MAX_MASS_KG,
            l_cg_mm=90.0,
            pl_to_e_adapter_used=True,
            adapter_foot_bolted_to_cage=False,
        )
        self.assertTrue(res_edge.valid)

    def test_10_g31_blocks_clamp_on_mattebox_on_telescoping_barrel(self) -> None:
        res_bad = verify_pl_cantilever_and_emount_flange_guard(
            lens_plus_mattebox_kg=0.95,
            l_cg_mm=90.0,
            clamp_on_mattebox=True,
            lens_front_rotates_or_telescopes=True,
        )
        self.assertFalse(res_bad.valid)
        self.assertFalse(res_bad.mattebox_barrel_safe)
        self.assertEqual(res_bad.status, STATUS_BLOCKED_CLAMP_ON_MATTEBOX_TELESCOPING_BARREL)

        # Fixed internal-focus front allows clamp-on matte box if mass/moment safe
        res_fixed = verify_pl_cantilever_and_emount_flange_guard(
            lens_plus_mattebox_kg=0.95,
            l_cg_mm=90.0,
            clamp_on_mattebox=True,
            lens_front_rotates_or_telescopes=False,
        )
        self.assertTrue(res_fixed.valid)

        # Rod-mounted swing-away matte box (clamp_on_mattebox=False) passes even on telescoping barrel
        res_swing = verify_pl_cantilever_and_emount_flange_guard(
            lens_plus_mattebox_kg=0.95,
            l_cg_mm=90.0,
            clamp_on_mattebox=False,
            lens_front_rotates_or_telescopes=True,
        )
        self.assertTrue(res_swing.valid)

    def test_11_g31_rejects_invalid_telemetry_and_persistent_emmc_write(self) -> None:
        for kw in (
            {"lens_plus_mattebox_kg": float("nan")},
            {"lens_plus_mattebox_kg": -0.2},
            {"l_cg_mm": 0.0},
            {"l_cg_mm": -10.0},
            {"shock_g": 0.8},
        ):
            res_bad = verify_pl_cantilever_and_emount_flange_guard(**kw)
            self.assertFalse(res_bad.valid)
            self.assertEqual(res_bad.status, STATUS_BLOCKED_PL_CANTILEVER_TELEMETRY_INVALID)

        res_emmc = verify_pl_cantilever_and_emount_flange_guard(request_persistent_emmc_writes=True)
        self.assertFalse(res_emmc.valid)
        self.assertEqual(res_emmc.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        self.assertFalse(res_emmc.persistent_emmc_writes_authorized)

    def test_12_g31_accumulates_all_three_violations_deterministically(self) -> None:
        res = verify_pl_cantilever_and_emount_flange_guard(
            lens_plus_mattebox_kg=2.6,
            l_cg_mm=160.0,
            lws_15mm_y_support_engaged=False,
            pl_to_e_adapter_used=True,
            adapter_foot_bolted_to_cage=False,
            clamp_on_mattebox=True,
            lens_front_rotates_or_telescopes=True,
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            set(res.violation_codes),
            {
                STATUS_BLOCKED_UNSUPPORTED_CANTILEVER_FLANGE_WARP,
                STATUS_BLOCKED_UNSHIMMED_PL_ADAPTER_BACKFOCUS_DRIFT,
                STATUS_BLOCKED_CLAMP_ON_MATTEBOX_TELESCOPING_BARREL,
            },
        )

    # --- 4. Gate G32 — Dummy-Battery Over-Voltage Blowout Firewall ---

    def test_13_g32_default_sony_cinema_sop_usbc_pd_plus_ups_passes(self) -> None:
        res = verify_dummy_battery_overvoltage_firewall()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_SAFE)
        self.assertEqual(res.violation_codes, ())
        self.assertEqual(res.power_topology, SONY_CINEMA_SOP_POWER_TOPOLOGY)
        self.assertFalse(res.dummy_battery_installed)
        self.assertTrue(res.dummy_battery_voltage_safe)
        self.assertTrue(res.dtap_polarity_safe)
        self.assertTrue(res.infolithium_auth_safe)
        self.assertFalse(res.persistent_emmc_writes_authorized)

    def test_14_g32_blocks_unregulated_14v8_dummy_battery_blowout(self) -> None:
        res = verify_dummy_battery_overvoltage_firewall(
            power_topology="UNREGULATED_DTAP_TO_NPFZ100_DUMMY",
            dummy_battery_installed=True,
            measured_open_circuit_v=14.8,
            buck_regulator_ovp_crowbar_verified=False,
            v_mount_nominal_v=14.8,
            dtap_source_used=True,
        )
        self.assertFalse(res.valid)
        self.assertFalse(res.dummy_battery_voltage_safe)
        self.assertEqual(res.status, STATUS_BLOCKED_DUMMY_BATTERY_OVER_VOLTAGE_BLOWOUT)
        self.assertGreater(res.pmic_overvoltage_stress_ratio, 1.75)

    def test_15_g32_blocks_26v_vmount_and_unverified_buck_crowbar(self) -> None:
        # 26V cinema V-Mount -> dummy battery is hard-blocked even if OCV currently reads 8.2V
        res_26v = verify_dummy_battery_overvoltage_firewall(
            dummy_battery_installed=True,
            measured_open_circuit_v=8.20,
            buck_regulator_ovp_crowbar_verified=True,
            v_mount_nominal_v=26.0,
            dtap_source_used=True,
        )
        self.assertFalse(res_26v.valid)
        self.assertFalse(res_26v.dummy_battery_voltage_safe)
        self.assertEqual(res_26v.status, STATUS_BLOCKED_DUMMY_BATTERY_OVER_VOLTAGE_BLOWOUT)

        # Exact 24.0V threshold also triggers blowout guard
        res_24v = verify_dummy_battery_overvoltage_firewall(
            dummy_battery_installed=True,
            measured_open_circuit_v=8.0,
            buck_regulator_ovp_crowbar_verified=True,
            v_mount_nominal_v=VMOUNT_HIGH_VOLTAGE_CINEMA_THRESHOLD_V,
        )
        self.assertFalse(res_24v.valid)
        self.assertEqual(res_24v.status, STATUS_BLOCKED_DUMMY_BATTERY_OVER_VOLTAGE_BLOWOUT)

        # Unverified buck OVP crowbar triggers blowout guard even at 8.0V
        res_no_crowbar = verify_dummy_battery_overvoltage_firewall(
            dummy_battery_installed=True,
            measured_open_circuit_v=8.0,
            buck_regulator_ovp_crowbar_verified=False,
            v_mount_nominal_v=14.8,
        )
        self.assertFalse(res_no_crowbar.valid)
        self.assertEqual(res_no_crowbar.status, STATUS_BLOCKED_DUMMY_BATTERY_OVER_VOLTAGE_BLOWOUT)

    def test_16_g32_ocv_boundary_and_regulated_dummy_warning(self) -> None:
        res_over = verify_dummy_battery_overvoltage_firewall(
            dummy_battery_installed=True,
            measured_open_circuit_v=8.46,
            buck_regulator_ovp_crowbar_verified=True,
            v_mount_nominal_v=14.8,
        )
        self.assertFalse(res_over.valid)
        self.assertEqual(res_over.status, STATUS_BLOCKED_DUMMY_BATTERY_OVER_VOLTAGE_BLOWOUT)

        res_edge_ok = verify_dummy_battery_overvoltage_firewall(
            dummy_battery_installed=True,
            measured_open_circuit_v=DUMMY_BATTERY_OPEN_CIRCUIT_MAX_V,
            buck_regulator_ovp_crowbar_verified=True,
            v_mount_nominal_v=14.8,
            dtap_source_used=True,
            reverse_polarity_diode_or_smart_dtap=True,
            infolithium_thermistor_ntc_valid=True,
        )
        self.assertTrue(res_edge_ok.valid)
        self.assertGreaterEqual(len(res_edge_ok.warnings), 1)

    def test_17_g32_blocks_reverse_polarity_unkeyed_dtap(self) -> None:
        res = verify_dummy_battery_overvoltage_firewall(
            dummy_battery_installed=False,
            dtap_source_used=True,
            reverse_polarity_diode_or_smart_dtap=False,
        )
        self.assertFalse(res.valid)
        self.assertFalse(res.dtap_polarity_safe)
        self.assertEqual(res.status, STATUS_BLOCKED_REVERSE_POLARITY_UNKEYED_DTAP)

    def test_18_g32_blocks_unauthenticated_non_infolithium_spoof(self) -> None:
        res = verify_dummy_battery_overvoltage_firewall(
            dummy_battery_installed=True,
            measured_open_circuit_v=8.0,
            buck_regulator_ovp_crowbar_verified=True,
            v_mount_nominal_v=14.8,
            infolithium_thermistor_ntc_valid=False,
        )
        self.assertFalse(res.valid)
        self.assertFalse(res.infolithium_auth_safe)
        self.assertEqual(res.status, STATUS_BLOCKED_UNAUTHENTICATED_NON_INFOLITHIUM_SPOOF)

    def test_19_g32_rejects_invalid_telemetry_and_persistent_emmc_write(self) -> None:
        for kw in (
            {"measured_open_circuit_v": float("nan")},
            {"measured_open_circuit_v": -0.5},
            {"measured_open_circuit_v": 65.0},
            {"v_mount_nominal_v": -1.0},
            {"v_mount_nominal_v": 80.0},
        ):
            res_bad = verify_dummy_battery_overvoltage_firewall(**kw)
            self.assertFalse(res_bad.valid)
            self.assertEqual(res_bad.status, STATUS_BLOCKED_DUMMY_BATT_TELEMETRY_INVALID)

        res_emmc = verify_dummy_battery_overvoltage_firewall(request_persistent_emmc_writes=True)
        self.assertFalse(res_emmc.valid)
        self.assertEqual(res_emmc.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        self.assertFalse(res_emmc.persistent_emmc_writes_authorized)

    def test_20_g32_accumulates_all_three_violations_deterministically(self) -> None:
        res = verify_dummy_battery_overvoltage_firewall(
            dummy_battery_installed=True,
            measured_open_circuit_v=16.8,
            buck_regulator_ovp_crowbar_verified=False,
            v_mount_nominal_v=26.0,
            dtap_source_used=True,
            reverse_polarity_diode_or_smart_dtap=False,
            infolithium_thermistor_ntc_valid=False,
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            set(res.violation_codes),
            {
                STATUS_BLOCKED_DUMMY_BATTERY_OVER_VOLTAGE_BLOWOUT,
                STATUS_BLOCKED_REVERSE_POLARITY_UNKEYED_DTAP,
                STATUS_BLOCKED_UNAUTHENTICATED_NON_INFOLITHIUM_SPOOF,
            },
        )

    # --- 5. Gate G31 & G32 Evaluators & Unified 32-Gate Master Preflight ---

    def test_21_g31_and_g32_verdicts_dual_mode(self) -> None:
        v31, r31 = evaluate_g31_pl_cantilever_and_lws_support(force_clean_room=True)
        self.assertTrue(v31.passed)
        self.assertEqual(v31.gate_id, G31_GATE_ID)
        self.assertEqual(v31.gate_code, G31_GATE_CODE)
        self.assertEqual(v31.status, STATUS_VERIFIED_G31)
        self.assertFalse(r31.persistent_emmc_writes_authorized)

        v32, r32 = evaluate_g32_dummy_battery_overvoltage_firewall(force_clean_room=True)
        self.assertTrue(v32.passed)
        self.assertEqual(v32.gate_id, G32_GATE_ID)
        self.assertEqual(v32.gate_code, G32_GATE_CODE)
        self.assertEqual(v32.status, STATUS_VERIFIED_G32)
        self.assertFalse(r32.persistent_emmc_writes_authorized)

    def test_22_32gate_offline_default_29_of_32_and_g10_g12_fail_offline(self) -> None:
        rep = evaluate_32gate_preflight(DEFAULT_REPO_ROOT, force_clean_room=True)
        self.assertEqual(rep.schema, PL_CANTILEVER_DUMMYBATT_32GATE_SCHEMA)
        self.assertEqual(len(rep.gates), 32)
        self.assertEqual(rep.summary["total_gates"], 32)
        self.assertEqual(rep.summary["verified_gates"], 29)
        self.assertEqual(rep.summary["blocked_or_pending_gates"], 3)
        self.assertTrue(rep.offline_29_gates_verified)
        self.assertFalse(rep.all_32_gates_verified)
        self.assertFalse(rep.dry_run_rehearsal_only)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.persistent_write_release)
        self.assertEqual(rep.status, "VERIFIED_29_OF_32_AWAITING_PHYSICAL_TIER0")
        for idx in (9, 10, 11):
            self.assertFalse(rep.gates[idx]["passed"])
            self.assertEqual(rep.gates[idx]["status"], STATUS_FAIL_OFFLINE_HARDWARE_NOT_ATTACHED)

    def test_23_32gate_dry_run_simulated_backup_32_of_32_and_redlines_locked(self) -> None:
        rep = evaluate_32gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
        )
        self.assertEqual(len(rep.gates), 32)
        self.assertEqual(rep.summary["verified_gates"], 32)
        self.assertEqual(rep.summary["blocked_or_pending_gates"], 0)
        self.assertEqual(rep.summary["g01_to_g12_verified"], 12)
        self.assertEqual(rep.summary["g13_to_g30_verified"], 18)
        self.assertEqual(rep.summary["g31_to_g32_verified"], 2)
        self.assertTrue(rep.all_32_gates_verified)
        self.assertTrue(rep.dry_run_rehearsal_only)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.persistent_write_release)
        self.assertEqual(rep.status, "VERIFIED_ALL_32_GATES_DRY_RUN_SIMULATED_BACKUP")
        self.assertTrue(all(g["passed"] for g in rep.gates))

    def test_24_32gate_propagates_g31_cantilever_pl_and_mattebox_failures(self) -> None:
        rep_warp = evaluate_32gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            pl_cantilever_kwargs={
                "lens_plus_mattebox_kg": 2.4,
                "l_cg_mm": 130.0,
                "lws_15mm_y_support_engaged": False,
            },
        )
        self.assertFalse(rep_warp.all_32_gates_verified)
        self.assertFalse(rep_warp.g31_to_g32_all_passed)
        self.assertFalse(rep_warp.gates[30]["passed"])
        self.assertEqual(rep_warp.status, STATUS_BLOCKED_UNSUPPORTED_CANTILEVER_FLANGE_WARP)

        rep_drift = evaluate_32gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            pl_cantilever_kwargs={
                "lens_plus_mattebox_kg": 1.1,
                "l_cg_mm": 90.0,
                "pl_to_e_adapter_used": True,
                "adapter_foot_bolted_to_cage": False,
            },
        )
        self.assertFalse(rep_drift.all_32_gates_verified)
        self.assertEqual(rep_drift.status, STATUS_BLOCKED_UNSHIMMED_PL_ADAPTER_BACKFOCUS_DRIFT)

        rep_mb = evaluate_32gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            pl_cantilever_kwargs={
                "clamp_on_mattebox": True,
                "lens_front_rotates_or_telescopes": True,
            },
        )
        self.assertFalse(rep_mb.all_32_gates_verified)
        self.assertEqual(rep_mb.status, STATUS_BLOCKED_CLAMP_ON_MATTEBOX_TELESCOPING_BARREL)

    def test_25_32gate_propagates_g32_ovp_polarity_and_infolithium_failures(self) -> None:
        rep_ovp = evaluate_32gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            dummy_battery_kwargs={
                "dummy_battery_installed": True,
                "measured_open_circuit_v": 15.2,
                "buck_regulator_ovp_crowbar_verified": False,
            },
        )
        self.assertFalse(rep_ovp.all_32_gates_verified)
        self.assertFalse(rep_ovp.gates[31]["passed"])
        self.assertEqual(rep_ovp.status, STATUS_BLOCKED_DUMMY_BATTERY_OVER_VOLTAGE_BLOWOUT)

        rep_pol = evaluate_32gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            dummy_battery_kwargs={
                "dtap_source_used": True,
                "reverse_polarity_diode_or_smart_dtap": False,
            },
        )
        self.assertFalse(rep_pol.all_32_gates_verified)
        self.assertEqual(rep_pol.status, STATUS_BLOCKED_REVERSE_POLARITY_UNKEYED_DTAP)

        rep_spoof = evaluate_32gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            dummy_battery_kwargs={
                "dummy_battery_installed": True,
                "infolithium_thermistor_ntc_valid": False,
            },
        )
        self.assertFalse(rep_spoof.all_32_gates_verified)
        self.assertEqual(rep_spoof.status, STATUS_BLOCKED_UNAUTHENTICATED_NON_INFOLITHIUM_SPOOF)

    def test_26_32gate_propagates_g29_g30_and_emmc_redline(self) -> None:
        rep_g29_g30 = evaluate_32gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            wireless_tx_emi_kwargs={
                "wireless_tx_power_mw": 600.0,
                "antenna_to_mishoe_or_hdmi_mm": 18.0,
                "shielded_coax_hdmi_cable": False,
            },
            longform_endurance_kwargs={
                "planned_continuous_min": 420.0,
                "filesystem": "FAT32",
            },
        )
        self.assertFalse(rep_g29_g30.all_32_gates_verified)
        self.assertFalse(rep_g29_g30.gates[28]["passed"])
        self.assertFalse(rep_g29_g30.gates[29]["passed"])
        self.assertEqual(rep_g29_g30.gates[28]["status"], STATUS_BLOCKED_NEARFIELD_WIRELESS_TX_EMI_DESENSE)
        self.assertEqual(rep_g29_g30.gates[29]["status"], STATUS_BLOCKED_FAT32_4GIB_SPANNING_TRAP)
        self.assertEqual(rep_g29_g30.status, STATUS_BLOCKED_NEARFIELD_WIRELESS_TX_EMI_DESENSE)

        rep_emmc = evaluate_32gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            request_persistent_emmc_writes=True,
        )
        self.assertFalse(rep_emmc.all_32_gates_verified)
        self.assertFalse(rep_emmc.offline_29_gates_verified)
        self.assertFalse(rep_emmc.overall_ready_for_hardware_attach)
        self.assertFalse(rep_emmc.persistent_emmc_writes_authorized)
        self.assertEqual(rep_emmc.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)

    def test_27_32gate_preserves_g01_to_g30_untouched(self) -> None:
        r30 = evaluate_30gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
        )
        r32 = evaluate_32gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
        )
        self.assertEqual(len(r30.gates), 30)
        self.assertEqual(len(r32.gates), 32)
        self.assertEqual(
            [g["gate_id"] for g in r30.gates],
            [g["gate_id"] for g in r32.gates[:30]],
        )
        self.assertEqual(
            [g["status"] for g in r30.gates],
            [g["status"] for g in r32.gates[:30]],
        )

    def test_28_serialized_json_contains_zero_raw_bytes_repr(self) -> None:
        rep = evaluate_32gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
        )
        rendered = json.dumps(rep.to_dict(), ensure_ascii=False)
        self.assertNotRegex(rendered, r'(?<![0-9A-Za-z_/.-])b[\x27"]')

    def test_29_cli_verify_32_gates_offline_and_dry_run_json(self) -> None:
        buf_off = io.StringIO()
        with contextlib.redirect_stdout(buf_off):
            rc_off = package_cli_main(["verify-32-gates", "--clean-room", "--json"])
        self.assertEqual(rc_off, 0)
        p_off = json.loads(buf_off.getvalue())
        self.assertEqual(p_off["schema"], PL_CANTILEVER_DUMMYBATT_32GATE_SCHEMA)
        self.assertEqual(p_off["summary"]["verified_gates"], 29)
        self.assertFalse(p_off["dry_run_rehearsal_only"])
        self.assertFalse(p_off["overall_ready_for_hardware_attach"])
        self.assertFalse(p_off["persistent_emmc_writes_authorized"])

        buf_dry = io.StringIO()
        with contextlib.redirect_stdout(buf_dry):
            rc_dry = package_cli_main(["verify-32-gates", "--clean-room", "--dry-run-simulated-backup", "--json"])
        self.assertEqual(rc_dry, 0)
        p_dry = json.loads(buf_dry.getvalue())
        self.assertEqual(p_dry["summary"]["verified_gates"], 32)
        self.assertTrue(p_dry["all_32_gates_verified"])
        self.assertTrue(p_dry["dry_run_rehearsal_only"])
        self.assertFalse(p_dry["overall_ready_for_hardware_attach"])
        self.assertFalse(p_dry["persistent_emmc_writes_authorized"])

    def test_30_cli_verify_32_gates_summary_and_failure_exit_code(self) -> None:
        buf_mod = io.StringIO()
        with contextlib.redirect_stdout(buf_mod):
            rc_mod = module_cli_main(["--clean-room"])
        self.assertEqual(rc_mod, 0)
        out = buf_mod.getvalue()
        self.assertIn("verified=29/32", out)
        self.assertIn("overall_ready_for_hardware_attach=False", out)
        self.assertIn("persistent_emmc_writes_authorized=False", out)

        buf_pkg = io.StringIO()
        with contextlib.redirect_stdout(buf_pkg):
            rc_pkg = package_cli_main(["verify-32-gates", "--clean-room"])
        self.assertEqual(rc_pkg, 0)
        self.assertIn("verified=29/32", buf_pkg.getvalue())

        with tempfile.TemporaryDirectory() as empty_dir:
            buf_fail = io.StringIO()
            with contextlib.redirect_stdout(buf_fail):
                rc_fail = package_cli_main(["verify-32-gates", "--repo-root", empty_dir, "--clean-room"])
            self.assertEqual(rc_fail, 1)

    def test_31_env_force_clean_room_honored_end_to_end(self) -> None:
        with patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            rep = evaluate_32gate_preflight(DEFAULT_REPO_ROOT)
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(rep.clean_room_forced)
        self.assertTrue(rep.offline_29_gates_verified)
        self.assertFalse(rep.persistent_emmc_writes_authorized)

    def test_32_evaluate_32_master_safety_gates_alias_and_default_mode(self) -> None:
        self.assertIs(evaluate_32_master_safety_gates, evaluate_32gate_preflight)
        rep = evaluate_32_master_safety_gates(DEFAULT_REPO_ROOT, dry_run_simulated_backup=True)
        self.assertTrue(rep.all_32_gates_verified)
        self.assertEqual(rep.summary["verified_gates"], 32)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.persistent_write_release)

    def test_33_donor_corruption_propagates_to_g31_g32_and_32gate_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            fx3_lib = tmp / "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib"
            fx6_lib = tmp / "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib"
            fx3_lib.mkdir(parents=True)
            fx6_lib.mkdir(parents=True)
            for d in (fx3_lib, fx6_lib):
                for name in ("libInfraLensCommunicator.so", "libBusPower.so", "libUsbBusPower.so"):
                    (d / name).write_bytes(b"bad")
            v31, r31 = evaluate_g31_pl_cantilever_and_lws_support(work_root=tmp, force_clean_room=False)
            v32, r32 = evaluate_g32_dummy_battery_overvoltage_firewall(work_root=tmp, force_clean_room=False)
        self.assertFalse(v31.passed)
        self.assertFalse(r31.valid)
        self.assertEqual(v31.status, STATUS_BLOCKED_DONOR_INTEGRITY)
        self.assertFalse(v32.passed)
        self.assertFalse(r32.valid)
        self.assertEqual(v32.status, STATUS_BLOCKED_DONOR_INTEGRITY)

    def test_34_prior_cli_subcommands_verify_16_through_30_remain_intact(self) -> None:
        for subcmd in (
            "verify-16-gates",
            "verify-18-gates",
            "verify-20-gates",
            "verify-22-gates",
            "verify-24-gates",
            "verify-26-gates",
            "verify-28-gates",
            "verify-30-gates",
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = package_cli_main([subcmd, "--clean-room", "--json"])
            self.assertEqual(rc, 0, f"{subcmd} failed with rc={rc}")
            payload = json.loads(buf.getvalue())
            self.assertFalse(payload["persistent_emmc_writes_authorized"])

    def test_35_g31_dynamic_2_5g_peak_moment_and_unbolted_pl_boundary(self) -> None:
        res = verify_pl_cantilever_and_emount_flange_guard(
            rig_profile="PL_PRIME_85MM_NO_SUPPORT",
            lens_plus_mattebox_kg=1.20,
            l_cg_mm=160.0,
            shock_g=2.5,
            lws_15mm_y_support_engaged=False,
        )
        # mass=1.20 kg is at edge, but static_moment_nm=1.883 > 1.8 N*m -> BLOCKED
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_UNSUPPORTED_CANTILEVER_FLANGE_WARP)
        self.assertAlmostEqual(res.peak_moment_nm, res.static_moment_nm * 2.5, places=3)

    def test_36_g32_dummy_battery_constants_and_gate_ids_in_32gate_report(self) -> None:
        self.assertEqual(NP_FZ100_NOMINAL_VOLTAGE_V, 7.20)
        self.assertEqual(NP_FZ100_MAX_CHARGED_VOLTAGE_V, 8.40)
        rep = evaluate_32gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            soc_start_ceiling_c=58.0,
        )
        self.assertTrue(rep.all_32_gates_verified)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertEqual(rep.gates[30]["gate_id"], G31_GATE_ID)
        self.assertEqual(rep.gates[31]["gate_id"], G32_GATE_ID)

    def test_37_32gate_summary_blocks_if_g31_or_g32_requests_emmc_write(self) -> None:
        rep_31 = evaluate_32gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            pl_cantilever_kwargs={"request_persistent_emmc_writes": True},
        )
        self.assertFalse(rep_31.all_32_gates_verified)
        self.assertFalse(rep_31.g31_to_g32_all_passed)
        self.assertFalse(rep_31.gates[30]["passed"])
        self.assertEqual(rep_31.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        self.assertFalse(rep_31.persistent_emmc_writes_authorized)

        rep_32 = evaluate_32gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            dummy_battery_kwargs={"request_persistent_emmc_writes": True},
        )
        self.assertFalse(rep_32.all_32_gates_verified)
        self.assertFalse(rep_32.g31_to_g32_all_passed)
        self.assertFalse(rep_32.gates[31]["passed"])
        self.assertEqual(rep_32.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        self.assertFalse(rep_32.persistent_emmc_writes_authorized)


if __name__ == "__main__":
    unittest.main()
