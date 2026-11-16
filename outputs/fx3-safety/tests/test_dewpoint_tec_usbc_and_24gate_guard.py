"""Fast dual-mode unit tests for Phase 84 — Dew-Point/TEC Condensation Firewall, PMIC 5V/USB-C Strain Guard & 24-Gate Preflight (`G01..G24`)."""

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
from fx3_safety.dewpoint_tec_usbc_and_24gate_guard import (
    COOLING_METHOD_EXTERNAL_AIR_FAN,
    COOLING_METHOD_EXTERNAL_PELTIER_TEC,
    COOLING_METHOD_INTERNAL_CENTRIFUGAL_AIR,
    COOLING_METHOD_PASSIVE,
    DEWPOINT_SAFETY_MARGIN_C,
    DEWPOINT_TEC_USBC_24GATE_SCHEMA,
    DEWPOINT_TEC_USBC_24GATE_VERSION,
    G23_GATE_CODE,
    G23_GATE_ID,
    G24_GATE_CODE,
    G24_GATE_ID,
    HDMI_PIN18_5V_MAX_MA,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PMIC_5V_CONTINUOUS_BUDGET_MA,
    RIG_MODE_BENCH,
    RIG_MODE_GIMBAL,
    RIG_MODE_HANDHELD,
    STATUS_BLOCKED_COLD_TO_WARM_CONDENSATION_SHOCK,
    STATUS_BLOCKED_DEWPOINT_TELEMETRY_INVALID,
    STATUS_BLOCKED_DONOR_INTEGRITY,
    STATUS_BLOCKED_PERSISTENT_EMMC_WRITE,
    STATUS_BLOCKED_PMIC_5V_ACCESSORY_OVERBUDGET,
    STATUS_BLOCKED_PMIC_TELEMETRY_INVALID,
    STATUS_BLOCKED_SUB_DEWPOINT_TEC_CONDENSATION_HAZARD,
    STATUS_BLOCKED_UNCLAMPED_CABLE_STRAIN,
    STATUS_BLOCKED_USBC_CABLE_IR_DROOP,
    STATUS_SAFE,
    STATUS_VERIFIED_G23,
    STATUS_VERIFIED_G24,
    STATUS_VERIFIED_SAFE,
    USBC_CABLE_MAX_IR_DROP_V,
    audit_phase84_donor_contracts,
    compute_magnus_tetens_dew_point_c,
    evaluate_24gate_preflight,
    evaluate_g23_dewpoint_and_tec_condensation,
    evaluate_g24_pmic_5v_and_usbc_strain,
    main as module_cli_main,
    verify_dewpoint_tec_condensation_firewall,
    verify_pmic_5v_accessory_and_usbc_strain_guard,
)
from fx3_safety.master_16gate_preflight import DEFAULT_REPO_ROOT
from fx3_safety.phantom48v_gimbal_and_22gate_guard import (
    SOURCE_PASSIVE_RIBBON,
    STATUS_BLOCKED_GIMBAL_DUAL_BUS_CONFLICT,
    STATUS_BLOCKED_PHANTOM_48V_TRANSDUCER_HAZARD,
    XLR_H1_INPUT1,
    XLR_MODE_MIC_48V,
    evaluate_22gate_preflight,
)
from fx3_safety.rig_groundloop_lensrail_and_20gate_guard import (
    STATUS_FAIL_OFFLINE_HARDWARE_NOT_ATTACHED,
)


class DewpointTecUsbcAnd24GateGuardTests(unittest.TestCase):
    # --- 1. Hard Redlines, Package Exports & O_RDONLY Donor Audit ---

    def test_01_hard_locked_redlines_and_package_exports(self) -> None:
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(PERSISTENT_WRITE_RELEASE)
        self.assertEqual(DEWPOINT_TEC_USBC_24GATE_SCHEMA, "fx3-dewpoint-tec-usbc-24gate-preflight-v1")
        self.assertEqual(DEWPOINT_TEC_USBC_24GATE_VERSION, "1.0.0")
        for sym in (
            "DEWPOINT_TEC_USBC_24GATE_SCHEMA",
            "G23_GATE_ID",
            "G24_GATE_ID",
            "audit_phase84_donor_contracts",
            "compute_magnus_tetens_dew_point_c",
            "verify_dewpoint_tec_condensation_firewall",
            "verify_pmic_5v_accessory_and_usbc_strain_guard",
            "evaluate_g23_dewpoint_and_tec_condensation",
            "evaluate_g24_pmic_5v_and_usbc_strain",
            "evaluate_24gate_preflight",
            "evaluate_24_master_safety_gates",
            "dewpoint_tec_usbc_and_24gate_guard",
        ):
            self.assertIn(sym, fx3_safety.__all__)
            self.assertTrue(hasattr(fx3_safety, sym))

    def test_02_donor_audit_o_rdonly_and_clean_room_fallback(self) -> None:
        observed_flags = []
        orig_open = os.open

        def spy_open(path, flags, *args, **kwargs):
            observed_flags.append((str(path), flags))
            return orig_open(path, flags, *args, **kwargs)

        with patch("os.open", side_effect=spy_open):
            res_default = audit_phase84_donor_contracts()
        self.assertTrue(res_default.valid)
        self.assertEqual(res_default.status, STATUS_VERIFIED_SAFE)
        self.assertEqual(res_default.access_mode, "O_RDONLY")
        self.assertEqual(len(res_default.missing_markers), 0)
        for path, flags in observed_flags:
            if any(k in path for k in ("libfan.so", "libBusPower.so", "libUsbBusPower.so")):
                self.assertEqual(flags & os.O_ACCMODE, os.O_RDONLY, f"Non-O_RDONLY open on {path}")

        res_clean = audit_phase84_donor_contracts(force_clean_room=True)
        self.assertTrue(res_clean.valid)
        self.assertEqual(res_clean.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(res_clean.files_inspected, 0)
        self.assertEqual(len(res_clean.sha256_by_artifact), 5)

    def test_03_donor_audit_blocks_integrity_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            fx3_lib = tmp / "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib"
            fx6_lib = tmp / "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib"
            fx3_lib.mkdir(parents=True)
            fx6_lib.mkdir(parents=True)
            for name in ("libfan.so", "libBusPower.so", "libUsbBusPower.so"):
                (fx3_lib / name).write_bytes(b"corrupt")
            for name in ("libfan.so", "libUsbBusPower.so"):
                (fx6_lib / name).write_bytes(b"corrupt")
            res = audit_phase84_donor_contracts(work_root=tmp, force_clean_room=False)
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_DONOR_INTEGRITY)
        self.assertEqual(len(res.missing_markers), 5)

    # --- 2. Magnus-Tetens Dew-Point & Peltier TEC Firewall (Gate G23) ---

    def test_04_magnus_tetens_dewpoint_formula_accuracy(self) -> None:
        # 30C / 75% RH -> ~25.08C (~25.1C)
        dp_trop = compute_magnus_tetens_dew_point_c(30.0, 75.0)
        self.assertAlmostEqual(dp_trop, 25.083, delta=0.05)

        # 26C / 65% RH -> ~18.88C
        dp_indoor = compute_magnus_tetens_dew_point_c(26.0, 65.0)
        self.assertAlmostEqual(dp_indoor, 18.883, delta=0.05)

        # 25C / 20% RH -> ~0.48C
        dp_dry = compute_magnus_tetens_dew_point_c(25.0, 20.0)
        self.assertAlmostEqual(dp_dry, 0.476, delta=0.05)

        # 100% RH -> T_dp == T_amb
        dp_sat = compute_magnus_tetens_dew_point_c(22.0, 100.0)
        self.assertAlmostEqual(dp_sat, 22.0, delta=0.001)

    def test_05_magnus_tetens_rejects_invalid_inputs(self) -> None:
        for bad_amb, bad_rh in (
            (float("nan"), 50.0),
            (25.0, float("inf")),
            (25.0, 0.0),
            (25.0, -5.0),
            (25.0, 105.0),
            (-80.0, 50.0),
            (95.0, 50.0),
        ):
            with self.assertRaises(ValueError):
                compute_magnus_tetens_dew_point_c(bad_amb, bad_rh)

    def test_06_internal_centrifugal_fan_is_dewpoint_immune(self) -> None:
        res = verify_dewpoint_tec_condensation_firewall(
            ambient_temp_c=30.0,
            relative_humidity_pct=75.0,
            body_temp_c=38.0,
            cooling_method=COOLING_METHOD_INTERNAL_CENTRIFUGAL_AIR,
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_SAFE)
        self.assertTrue(res.internal_fan_dewpoint_immune)
        self.assertGreaterEqual(res.chassis_temp_c, res.ambient_temp_c)
        self.assertGreater(res.chassis_temp_c, res.dew_point_c)
        self.assertEqual(res.condensation_risk_pct, 0.0)
        self.assertFalse(res.external_tec_attached)
        self.assertFalse(res.persistent_emmc_writes_authorized)

    def test_07_tropical_unregulated_peltier_tec_blocked_sub_dewpoint(self) -> None:
        res = verify_dewpoint_tec_condensation_firewall(
            ambient_temp_c=30.0,
            relative_humidity_pct=75.0,
            body_temp_c=32.0,
            cooling_method=COOLING_METHOD_EXTERNAL_PELTIER_TEC,
            tec_cold_plate_c=10.0,
        )
        self.assertFalse(res.valid)
        self.assertFalse(res.tec_condensation_safe)
        self.assertEqual(res.status, STATUS_BLOCKED_SUB_DEWPOINT_TEC_CONDENSATION_HAZARD)
        self.assertIn(STATUS_BLOCKED_SUB_DEWPOINT_TEC_CONDENSATION_HAZARD, res.violation_codes)
        self.assertGreater(res.condensation_risk_pct, 0.0)

    def test_08_unmonitored_peltier_tec_without_cold_plate_telemetry_blocked(self) -> None:
        res = verify_dewpoint_tec_condensation_firewall(
            ambient_temp_c=24.0,
            relative_humidity_pct=50.0,
            cooling_method=COOLING_METHOD_EXTERNAL_PELTIER_TEC,
            tec_cold_plate_c=None,
        )
        self.assertFalse(res.valid)
        self.assertFalse(res.tec_condensation_safe)
        self.assertEqual(res.status, STATUS_BLOCKED_SUB_DEWPOINT_TEC_CONDENSATION_HAZARD)

    def test_09_peltier_tec_margin_2c_boundary_and_dry_air_pass(self) -> None:
        dp = compute_magnus_tetens_dew_point_c(25.0, 20.0)
        # Just below dew_point + 2.0 -> blocked
        res_below = verify_dewpoint_tec_condensation_firewall(
            ambient_temp_c=25.0,
            relative_humidity_pct=20.0,
            body_temp_c=28.0,
            cooling_method=COOLING_METHOD_EXTERNAL_PELTIER_TEC,
            tec_cold_plate_c=dp + DEWPOINT_SAFETY_MARGIN_C - 0.1,
        )
        self.assertFalse(res_below.valid)
        self.assertEqual(res_below.status, STATUS_BLOCKED_SUB_DEWPOINT_TEC_CONDENSATION_HAZARD)

        # Regulated TEC in dry air above dew_point + 2.0 -> pass
        res_dry_ok = verify_dewpoint_tec_condensation_firewall(
            ambient_temp_c=25.0,
            relative_humidity_pct=20.0,
            body_temp_c=28.0,
            cooling_method=COOLING_METHOD_EXTERNAL_PELTIER_TEC,
            tec_cold_plate_c=15.0,
        )
        self.assertTrue(res_dry_ok.valid)
        self.assertTrue(res_dry_ok.tec_condensation_safe)
        self.assertEqual(res_dry_ok.condensation_risk_pct, 0.0)

    def test_10_cold_to_warm_unbagged_shock_blocked_and_bagged_allowed(self) -> None:
        # Moving -5C outdoor camera into +26C / 65% RH indoor room without bag -> blocked
        res_unbagged = verify_dewpoint_tec_condensation_firewall(
            ambient_temp_c=26.0,
            relative_humidity_pct=65.0,
            body_temp_c=-5.0,
            sealed_acclimation_bag_used=False,
        )
        self.assertFalse(res_unbagged.valid)
        self.assertFalse(res_unbagged.cold_to_warm_shock_safe)
        self.assertEqual(res_unbagged.status, STATUS_BLOCKED_COLD_TO_WARM_CONDENSATION_SHOCK)

        # Protected inside sealed acclimation bag -> allowed with warning
        res_bagged = verify_dewpoint_tec_condensation_firewall(
            ambient_temp_c=26.0,
            relative_humidity_pct=65.0,
            body_temp_c=-5.0,
            sealed_acclimation_bag_used=True,
        )
        self.assertTrue(res_bagged.valid)
        self.assertTrue(res_bagged.cold_to_warm_shock_safe)
        self.assertGreaterEqual(len(res_bagged.warnings), 1)
        self.assertEqual(res_bagged.condensation_risk_pct, 0.0)

        # Once acclimated above dew_point + 2.0 -> clean pass without bag
        res_warm = verify_dewpoint_tec_condensation_firewall(
            ambient_temp_c=26.0,
            relative_humidity_pct=65.0,
            body_temp_c=22.0,
            sealed_acclimation_bag_used=False,
        )
        self.assertTrue(res_warm.valid)
        self.assertEqual(len(res_warm.warnings), 0)

    def test_11_external_air_fan_and_passive_modes_safe_when_warm(self) -> None:
        for method in (COOLING_METHOD_EXTERNAL_AIR_FAN, COOLING_METHOD_PASSIVE):
            res = verify_dewpoint_tec_condensation_firewall(
                ambient_temp_c=24.0,
                relative_humidity_pct=50.0,
                body_temp_c=28.0,
                cooling_method=method,
            )
            self.assertTrue(res.valid)
            self.assertFalse(res.internal_fan_dewpoint_immune)

    def test_12_dewpoint_rejects_invalid_telemetry_and_sub_ambient_internal_fan(self) -> None:
        res_rh = verify_dewpoint_tec_condensation_firewall(ambient_temp_c=25.0, relative_humidity_pct=0.0)
        self.assertFalse(res_rh.valid)
        self.assertEqual(res_rh.status, STATUS_BLOCKED_DEWPOINT_TELEMETRY_INVALID)

        res_method = verify_dewpoint_tec_condensation_firewall(cooling_method="liquid_nitrogen")
        self.assertFalse(res_method.valid)
        self.assertEqual(res_method.status, STATUS_BLOCKED_DEWPOINT_TELEMETRY_INVALID)

        res_sub_amb = verify_dewpoint_tec_condensation_firewall(
            ambient_temp_c=25.0,
            relative_humidity_pct=40.0,
            body_temp_c=26.0,
            chassis_temp_c=20.0,
            cooling_method=COOLING_METHOD_INTERNAL_CENTRIFUGAL_AIR,
        )
        self.assertFalse(res_sub_amb.valid)
        self.assertEqual(res_sub_amb.status, STATUS_BLOCKED_DEWPOINT_TELEMETRY_INVALID)

    # --- 3. PMIC 5V Accessory Budget, USB-C Droop & Strain Guard (Gate G24) ---

    def test_13_pmic_5v_default_safe_rtl8153_xlr_h1_hdmi_multiport(self) -> None:
        res = verify_pmic_5v_accessory_and_usbc_strain_guard()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_SAFE)
        self.assertLessEqual(res.total_pmic_5v_ma, PMIC_5V_CONTINUOUS_BUDGET_MA)
        self.assertTrue(res.pmic_5v_budget_safe)
        self.assertTrue(res.usbc_cable_droop_safe)
        self.assertTrue(res.cage_cable_strain_safe)
        self.assertFalse(res.persistent_emmc_writes_authorized)

    def test_14_pmic_5v_blocks_overbudget_over_900ma_without_powered_pd_hub(self) -> None:
        res = verify_pmic_5v_accessory_and_usbc_strain_guard(
            mishoe_xlr_h1_attached=True,
            phantom_48v_load_ma=10.0,
            hdmi_attached=True,
            hdmi_pin18_5v_ma=50.0,
            usbc_host_mode_vbus_source=True,
            usbc_bus_powered_device="USBC_SSD",
            multiport_5v_ma=50.0,
            external_powered_usbc_pd_hub=False,
        )
        self.assertFalse(res.valid)
        self.assertFalse(res.pmic_5v_budget_safe)
        self.assertGreater(res.total_pmic_5v_ma, PMIC_5V_CONTINUOUS_BUDGET_MA)
        self.assertEqual(res.status, STATUS_BLOCKED_PMIC_5V_ACCESSORY_OVERBUDGET)

    def test_15_pmic_5v_powered_usbc_pd_hub_offloads_vbus_and_passes(self) -> None:
        res = verify_pmic_5v_accessory_and_usbc_strain_guard(
            mishoe_xlr_h1_attached=True,
            phantom_48v_load_ma=10.0,
            hdmi_attached=True,
            hdmi_pin18_5v_ma=50.0,
            usbc_host_mode_vbus_source=True,
            usbc_bus_powered_device="USBC_NVME_SSD",
            multiport_5v_ma=50.0,
            external_powered_usbc_pd_hub=True,
        )
        self.assertTrue(res.valid)
        self.assertTrue(res.pmic_5v_budget_safe)
        self.assertEqual(res.usbc_pmic_5v_ma, 0.0)
        self.assertLessEqual(res.total_pmic_5v_ma, PMIC_5V_CONTINUOUS_BUDGET_MA)
        self.assertGreaterEqual(len(res.warnings), 1)

    def test_16_pmic_5v_blocks_hdmi_pin18_overcurrent_and_non_usbc_overbudget(self) -> None:
        res_hdmi = verify_pmic_5v_accessory_and_usbc_strain_guard(
            hdmi_pin18_5v_ma=HDMI_PIN18_5V_MAX_MA + 15.0,
            usbc_host_mode_vbus_source=False,
        )
        self.assertFalse(res_hdmi.valid)
        self.assertEqual(res_hdmi.status, STATUS_BLOCKED_PMIC_5V_ACCESSORY_OVERBUDGET)

        res_non_usbc = verify_pmic_5v_accessory_and_usbc_strain_guard(
            mishoe_5v_ma=800.0,
            hdmi_pin18_5v_ma=50.0,
            multiport_5v_ma=100.0,
            external_powered_usbc_pd_hub=True,
        )
        self.assertFalse(res_non_usbc.valid)
        self.assertEqual(res_non_usbc.status, STATUS_BLOCKED_PMIC_5V_ACCESSORY_OVERBUDGET)

    def test_17_usbc_cable_ir_droop_and_long_un_emarked_cable_blocked(self) -> None:
        # Explicit cable IR drop > 0.65V at 3.0A -> blocked
        res_ir = verify_pmic_5v_accessory_and_usbc_strain_guard(
            usbc_cable_attached=True,
            usbc_cable_length_m=1.5,
            usbc_cable_emarked=True,
            usbc_cable_load_a=3.0,
            cable_ir_drop_v=USBC_CABLE_MAX_IR_DROP_V + 0.15,
        )
        self.assertFalse(res_ir.valid)
        self.assertFalse(res_ir.usbc_cable_droop_safe)
        self.assertEqual(res_ir.status, STATUS_BLOCKED_USBC_CABLE_IR_DROOP)

        # >2m un-E-marked USB-C cable -> blocked even without explicit IR override
        res_long = verify_pmic_5v_accessory_and_usbc_strain_guard(
            usbc_cable_attached=True,
            usbc_cable_length_m=3.0,
            usbc_cable_emarked=False,
            usbc_cable_load_a=3.0,
        )
        self.assertFalse(res_long.valid)
        self.assertFalse(res_long.usbc_cable_droop_safe)
        self.assertEqual(res_long.status, STATUS_BLOCKED_USBC_CABLE_IR_DROOP)

        # 2.0m E-marked low-droop cable -> pass
        res_ok = verify_pmic_5v_accessory_and_usbc_strain_guard(
            usbc_cable_attached=True,
            usbc_cable_length_m=2.0,
            usbc_cable_emarked=True,
            usbc_cable_load_a=3.0,
            cable_ir_drop_v=0.45,
        )
        self.assertTrue(res_ok.valid)
        self.assertTrue(res_ok.usbc_cable_droop_safe)

    def test_18_cage_cable_strain_clamp_enforced_on_handheld_and_gimbal_rigs(self) -> None:
        for rig in (RIG_MODE_HANDHELD, RIG_MODE_GIMBAL):
            res_unclamped = verify_pmic_5v_accessory_and_usbc_strain_guard(
                rig_mode=rig,
                heavy_usbc_or_hdmi_attached=True,
                cage_cable_clamp_installed=False,
            )
            self.assertFalse(res_unclamped.valid)
            self.assertFalse(res_unclamped.cage_cable_strain_safe)
            self.assertEqual(res_unclamped.status, STATUS_BLOCKED_UNCLAMPED_CABLE_STRAIN)

            res_clamped = verify_pmic_5v_accessory_and_usbc_strain_guard(
                rig_mode=rig,
                heavy_usbc_or_hdmi_attached=True,
                cage_cable_clamp_installed=True,
            )
            self.assertTrue(res_clamped.valid)
            self.assertTrue(res_clamped.cage_cable_strain_safe)

        # Bench mode without clamp requirement passes
        res_bench = verify_pmic_5v_accessory_and_usbc_strain_guard(
            rig_mode=RIG_MODE_BENCH,
            require_cage_cable_clamp=False,
            cage_cable_clamp_installed=False,
        )
        self.assertTrue(res_bench.valid)

    def test_19_pmic_rejects_negative_telemetry_and_persistent_emmc_writes(self) -> None:
        res_neg = verify_pmic_5v_accessory_and_usbc_strain_guard(multiport_5v_ma=-10.0)
        self.assertFalse(res_neg.valid)
        self.assertEqual(res_neg.status, STATUS_BLOCKED_PMIC_TELEMETRY_INVALID)

        res_emmc_dp = verify_dewpoint_tec_condensation_firewall(request_persistent_emmc_writes=True)
        self.assertFalse(res_emmc_dp.valid)
        self.assertEqual(res_emmc_dp.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        self.assertFalse(res_emmc_dp.persistent_emmc_writes_authorized)

        res_emmc_pmic = verify_pmic_5v_accessory_and_usbc_strain_guard(request_persistent_emmc_writes=True)
        self.assertFalse(res_emmc_pmic.valid)
        self.assertEqual(res_emmc_pmic.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        self.assertFalse(res_emmc_pmic.persistent_emmc_writes_authorized)

    # --- 4. Gate G23 & G24 Evaluators & 24-Gate Master Safety Preflight ---

    def test_20_g23_and_g24_verdicts_dual_mode(self) -> None:
        v23, r23 = evaluate_g23_dewpoint_and_tec_condensation(force_clean_room=True)
        self.assertTrue(v23.passed)
        self.assertEqual(v23.gate_id, G23_GATE_ID)
        self.assertEqual(v23.gate_code, G23_GATE_CODE)
        self.assertEqual(v23.status, STATUS_VERIFIED_G23)
        self.assertFalse(r23.persistent_emmc_writes_authorized)

        v24, r24 = evaluate_g24_pmic_5v_and_usbc_strain(force_clean_room=True)
        self.assertTrue(v24.passed)
        self.assertEqual(v24.gate_id, G24_GATE_ID)
        self.assertEqual(v24.gate_code, G24_GATE_CODE)
        self.assertEqual(v24.status, STATUS_VERIFIED_G24)
        self.assertFalse(r24.persistent_emmc_writes_authorized)

    def test_21_24gate_offline_default_21_of_24_and_g10_g12_fail_offline(self) -> None:
        rep = evaluate_24gate_preflight(DEFAULT_REPO_ROOT, force_clean_room=True)
        self.assertEqual(rep.schema, DEWPOINT_TEC_USBC_24GATE_SCHEMA)
        self.assertEqual(len(rep.gates), 24)
        self.assertEqual(rep.summary["total_gates"], 24)
        self.assertEqual(rep.summary["verified_gates"], 21)
        self.assertEqual(rep.summary["blocked_or_pending_gates"], 3)
        self.assertTrue(rep.offline_21_gates_verified)
        self.assertFalse(rep.all_24_gates_verified)
        self.assertFalse(rep.dry_run_rehearsal_only)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.persistent_write_release)
        self.assertEqual(rep.status, "VERIFIED_21_OF_24_AWAITING_PHYSICAL_TIER0")
        for idx in (9, 10, 11):
            self.assertFalse(rep.gates[idx]["passed"])
            self.assertEqual(rep.gates[idx]["status"], STATUS_FAIL_OFFLINE_HARDWARE_NOT_ATTACHED)

    def test_22_24gate_dry_run_simulated_backup_24_of_24_and_redlines_locked(self) -> None:
        rep = evaluate_24gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
        )
        self.assertEqual(len(rep.gates), 24)
        self.assertEqual(rep.summary["verified_gates"], 24)
        self.assertEqual(rep.summary["blocked_or_pending_gates"], 0)
        self.assertTrue(rep.all_24_gates_verified)
        self.assertTrue(rep.dry_run_rehearsal_only)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.persistent_write_release)
        self.assertEqual(rep.status, "VERIFIED_ALL_24_GATES_DRY_RUN_SIMULATED_BACKUP")
        self.assertTrue(all(g["passed"] for g in rep.gates))

    def test_23_24gate_propagates_g23_tec_failure(self) -> None:
        rep = evaluate_24gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            dewpoint_kwargs={
                "ambient_temp_c": 30.0,
                "relative_humidity_pct": 75.0,
                "cooling_method": COOLING_METHOD_EXTERNAL_PELTIER_TEC,
                "tec_cold_plate_c": 10.0,
            },
        )
        self.assertFalse(rep.all_24_gates_verified)
        self.assertFalse(rep.g23_to_g24_all_passed)
        self.assertEqual(rep.status, STATUS_BLOCKED_SUB_DEWPOINT_TEC_CONDENSATION_HAZARD)

    def test_24_24gate_propagates_g23_cold_to_warm_shock_failure(self) -> None:
        v_shock, r_shock = evaluate_g23_dewpoint_and_tec_condensation(
            force_clean_room=True,
            dewpoint_kwargs={
                "ambient_temp_c": 26.0,
                "relative_humidity_pct": 65.0,
                "body_temp_c": -5.0,
                "sealed_acclimation_bag_used": False,
            },
        )
        self.assertFalse(v_shock.passed)
        self.assertFalse(r_shock.valid)
        self.assertEqual(v_shock.status, STATUS_BLOCKED_COLD_TO_WARM_CONDENSATION_SHOCK)

    def test_25_24gate_propagates_g24_pmic_overbudget_and_cable_droop_and_strain(self) -> None:
        rep_budget = evaluate_24gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            pmic_usbc_kwargs={
                "usbc_bus_powered_device": "USBC_SSD",
                "external_powered_usbc_pd_hub": False,
            },
        )
        self.assertFalse(rep_budget.all_24_gates_verified)
        self.assertEqual(rep_budget.status, STATUS_BLOCKED_PMIC_5V_ACCESSORY_OVERBUDGET)

        v_droop, _ = evaluate_g24_pmic_5v_and_usbc_strain(
            force_clean_room=True,
            pmic_usbc_kwargs={"cable_ir_drop_v": 0.90},
        )
        self.assertFalse(v_droop.passed)
        self.assertEqual(v_droop.status, STATUS_BLOCKED_USBC_CABLE_IR_DROOP)

        v_strain, _ = evaluate_g24_pmic_5v_and_usbc_strain(
            force_clean_room=True,
            pmic_usbc_kwargs={"cage_cable_clamp_installed": False},
        )
        self.assertFalse(v_strain.passed)
        self.assertEqual(v_strain.status, STATUS_BLOCKED_UNCLAMPED_CABLE_STRAIN)

    def test_26_24gate_propagates_g21_g22_and_emmc_redline(self) -> None:
        rep_g21_g22 = evaluate_24gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            xlr_kwargs={
                "channel_id": XLR_H1_INPUT1,
                "input_mode": XLR_MODE_MIC_48V,
                "source_type": SOURCE_PASSIVE_RIBBON,
            },
            gimbal_kwargs={"usb_c_crsdk_active": True, "multiport_rss_active": True},
        )
        self.assertFalse(rep_g21_g22.all_24_gates_verified)
        self.assertFalse(rep_g21_g22.gates[20]["passed"])
        self.assertFalse(rep_g21_g22.gates[21]["passed"])
        self.assertEqual(rep_g21_g22.gates[20]["status"], STATUS_BLOCKED_PHANTOM_48V_TRANSDUCER_HAZARD)
        self.assertEqual(rep_g21_g22.gates[21]["status"], STATUS_BLOCKED_GIMBAL_DUAL_BUS_CONFLICT)
        self.assertEqual(rep_g21_g22.status, STATUS_BLOCKED_PHANTOM_48V_TRANSDUCER_HAZARD)

        rep_emmc = evaluate_24gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            request_persistent_emmc_writes=True,
        )
        self.assertFalse(rep_emmc.all_24_gates_verified)
        self.assertFalse(rep_emmc.offline_21_gates_verified)
        self.assertFalse(rep_emmc.overall_ready_for_hardware_attach)
        self.assertFalse(rep_emmc.persistent_emmc_writes_authorized)
        self.assertEqual(rep_emmc.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)

    def test_27_24gate_preserves_g01_to_g22_untouched(self) -> None:
        r22 = evaluate_22gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
        )
        r24 = evaluate_24gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
        )
        self.assertEqual(len(r22.gates), 22)
        self.assertEqual(len(r24.gates), 24)
        self.assertEqual(
            [g["gate_id"] for g in r22.gates],
            [g["gate_id"] for g in r24.gates[:22]],
        )
        self.assertEqual(
            [g["status"] for g in r22.gates],
            [g["status"] for g in r24.gates[:22]],
        )

    def test_28_serialized_json_contains_zero_raw_bytes_repr(self) -> None:
        rep = evaluate_24gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
        )
        rendered = json.dumps(rep.to_dict(), ensure_ascii=False)
        self.assertNotRegex(rendered, r'(?<![0-9A-Za-z_/.-])b[\'"]')

    def test_29_cli_verify_24_gates_offline_and_dry_run_json(self) -> None:
        buf_off = io.StringIO()
        with contextlib.redirect_stdout(buf_off):
            rc_off = package_cli_main(["verify-24-gates", "--clean-room", "--json"])
        self.assertEqual(rc_off, 0)
        p_off = json.loads(buf_off.getvalue())
        self.assertEqual(p_off["schema"], DEWPOINT_TEC_USBC_24GATE_SCHEMA)
        self.assertEqual(p_off["summary"]["verified_gates"], 21)
        self.assertFalse(p_off["dry_run_rehearsal_only"])
        self.assertFalse(p_off["overall_ready_for_hardware_attach"])
        self.assertFalse(p_off["persistent_emmc_writes_authorized"])

        buf_dry = io.StringIO()
        with contextlib.redirect_stdout(buf_dry):
            rc_dry = package_cli_main(["verify-24-gates", "--clean-room", "--dry-run-simulated-backup", "--json"])
        self.assertEqual(rc_dry, 0)
        p_dry = json.loads(buf_dry.getvalue())
        self.assertEqual(p_dry["summary"]["verified_gates"], 24)
        self.assertTrue(p_dry["all_24_gates_verified"])
        self.assertTrue(p_dry["dry_run_rehearsal_only"])
        self.assertFalse(p_dry["overall_ready_for_hardware_attach"])
        self.assertFalse(p_dry["persistent_emmc_writes_authorized"])

    def test_30_module_cli_summary_and_failure_exit_code(self) -> None:
        buf_mod = io.StringIO()
        with contextlib.redirect_stdout(buf_mod):
            rc_mod = module_cli_main(["--clean-room"])
        self.assertEqual(rc_mod, 0)
        out = buf_mod.getvalue()
        self.assertIn("verified=21/24", out)
        self.assertIn("overall_ready_for_hardware_attach=False", out)
        self.assertIn("persistent_emmc_writes_authorized=False", out)

        with tempfile.TemporaryDirectory() as empty_dir:
            buf_fail = io.StringIO()
            with contextlib.redirect_stdout(buf_fail):
                rc_fail = package_cli_main(["verify-24-gates", "--repo-root", empty_dir, "--clean-room"])
            self.assertEqual(rc_fail, 1)

    def test_31_env_force_clean_room_honored_end_to_end(self) -> None:
        with patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            rep = evaluate_24gate_preflight(DEFAULT_REPO_ROOT)
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(rep.clean_room_forced)
        self.assertTrue(rep.offline_21_gates_verified)
        self.assertFalse(rep.persistent_emmc_writes_authorized)

    def test_32_usbc_cable_detached_skips_droop_check_and_respects_bench_mode(self) -> None:
        res = verify_pmic_5v_accessory_and_usbc_strain_guard(
            usbc_host_mode_vbus_source=False,
            usbc_cable_attached=False,
            usbc_cable_length_m=5.0,
            usbc_cable_emarked=False,
            rig_mode=RIG_MODE_BENCH,
            heavy_usbc_or_hdmi_attached=False,
            cage_cable_clamp_installed=False,
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.cable_ir_drop_v, 0.0)
        self.assertFalse(res.require_cage_cable_clamp)

    def test_33_ax88179_ethernet_adapter_fits_within_900ma_pmic_budget(self) -> None:
        res = verify_pmic_5v_accessory_and_usbc_strain_guard(
            mishoe_xlr_h1_attached=True,
            phantom_48v_load_ma=10.0,
            hdmi_attached=True,
            hdmi_pin18_5v_ma=50.0,
            usbc_host_mode_vbus_source=True,
            usbc_bus_powered_device="AX88179",
            multiport_5v_ma=40.0,
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.total_pmic_5v_ma, 790.0)
        self.assertLessEqual(res.total_pmic_5v_ma, PMIC_5V_CONTINUOUS_BUDGET_MA)

    def test_34_24gate_local_donor_mode_when_available(self) -> None:
        rep = evaluate_24gate_preflight(DEFAULT_REPO_ROOT, dry_run_simulated_backup=True)
        self.assertTrue(rep.all_24_gates_verified)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.persistent_write_release)


if __name__ == "__main__":
    unittest.main()
