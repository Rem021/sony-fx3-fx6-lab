"""Dual-mode unit tests for Phase 44 FX3 Fan PWM, NP-FZ100 & USB-PD Guard."""

from __future__ import annotations

import contextlib
import io
import json
import math
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
from fx3_safety.thermal_pwm_and_power_guard import (
    BP_U_EMERGENCY_CUTOFF_MV,
    CFEXPRESS_FAN_OVERRIDE_TEMP_C,
    COMPARATOR_INFOLITHIUM_SOC,
    COMPARATOR_RAW_19V5_DC_IN,
    COMPARATOR_RAW_BPU_11500MV,
    FAIL_CLOSED_TEARDOWN_TEMP_C,
    FAN_MODE_ALWAYS_OFF,
    FAN_MODE_AUTO1,
    FAN_MODE_AUTO2,
    FAN_MODE_MINIMUM,
    FAN_MODE_OFF_IN_REC,
    H0_H1_REHEARSAL_MIN_BATT_MV,
    H0_H1_REHEARSAL_MIN_SOC_PCT,
    NP_FZ100_MAX_OPERATING_MV,
    NP_FZ100_MIN_OPERATING_MV,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    SESSION_H0_REHEARSAL,
    SESSION_H1_REHEARSAL,
    SESSION_STANDARD_RUNTIME,
    SOC_FAN_OVERRIDE_TEMP_C,
    SOFT_RECORDING_WARNING_TEMP_C,
    STATUS_BLOCKED_BATT_COMPARATOR_MISMATCH,
    STATUS_BLOCKED_DONOR_AUDIT_MISMATCH,
    STATUS_BLOCKED_FAN_CONTROLLER_FAULT,
    STATUS_BLOCKED_FAN_MODE_UNSAFE,
    STATUS_BLOCKED_NPFZ100_BROWNOUT,
    STATUS_BLOCKED_PERSISTENT_EMMC_WRITE,
    STATUS_BLOCKED_THERMAL_RUNAWAY,
    STATUS_BLOCKED_THERMAL_TELEMETRY_INVALID,
    STATUS_BLOCKED_USBPD_CONTRACT_INSUFFICIENT,
    STATUS_BLOCKED_USBPD_VBUS_DROOP,
    STATUS_THERMAL_SOFT_WARNING,
    STATUS_VERIFIED_SAFE,
    THERMAL_PWM_POWER_GUARD_SCHEMA,
    USBPD_MAX_VBUS_DROOP_MV,
    USBPD_REQUIRED_CURRENT_MA,
    USBPD_REQUIRED_POWER_MW,
    USBPD_REQUIRED_VOLTAGE_MV,
    VALID_MENU_FAN_MODES,
    audit_donor_thermal_fan_power_contracts,
    compute_fan_pwm_duty_pct,
    evaluate_fan_mode_matrix,
    evaluate_thermal_pwm_and_power_guard,
    main as module_cli_main,
    normalize_npfz100_infolithium_mv,
    verify_battery_and_usbpd_firewall,
    verify_fan_thermal_envelope,
)


class ThermalPwmAndPowerGuardTests(unittest.TestCase):
    def test_01_safety_redlines_and_package_exports(self) -> None:
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(PERSISTENT_WRITE_RELEASE)
        for name in (
            "THERMAL_PWM_POWER_GUARD_SCHEMA",
            "STATUS_BLOCKED_THERMAL_RUNAWAY",
            "STATUS_BLOCKED_BATT_COMPARATOR_MISMATCH",
            "STATUS_BLOCKED_USBPD_VBUS_DROOP",
            "audit_donor_thermal_fan_power_contracts",
            "compute_fan_pwm_duty_pct",
            "verify_fan_thermal_envelope",
            "evaluate_fan_mode_matrix",
            "normalize_npfz100_infolithium_mv",
            "verify_battery_and_usbpd_firewall",
            "evaluate_thermal_pwm_and_power_guard",
        ):
            self.assertIn(name, fx3_safety.__all__)
            self.assertTrue(hasattr(fx3_safety, name))

    # --- Deliverable 1: O_RDONLY Donor Audit & Clean-Room Fallback ---

    def test_02_donor_audit_uses_o_rdonly_and_passes_in_current_mode(self) -> None:
        observed_flags = []
        orig_open = os.open

        def spy_open(path, flags, *args, **kwargs):
            observed_flags.append(flags)
            return orig_open(path, flags, *args, **kwargs)

        with patch("fx3_safety.thermal_pwm_and_power_guard.os.open", side_effect=spy_open):
            res = audit_donor_thermal_fan_power_contracts(include_large_binaries=False)

        self.assertTrue(res.valid, res.errors)
        self.assertEqual(res.status, STATUS_VERIFIED_SAFE)
        self.assertTrue(res.o_rdonly_enforced)
        self.assertTrue(res.libfan_patch_verified)
        self.assertEqual(res.fan_modes_verified, VALID_MENU_FAN_MODES)
        for flag in observed_flags:
            self.assertEqual(flag, os.O_RDONLY)

    def test_03_clean_room_forced_returns_pinned_metadata(self) -> None:
        with patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            res = audit_donor_thermal_fan_power_contracts()
        self.assertTrue(res.valid)
        self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(res.clean_room_forced)
        self.assertIn("libfan.so", res.fx3_artifacts_checked)
        self.assertIn("libfan.so", res.fx6_artifacts_checked)
        self.assertIn("0x2380009", res.bk4_thermal_diff_summary)

    def test_04_missing_donor_root_gracefully_falls_back_to_clean_room(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            with patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "0"}):
                res = audit_donor_thermal_fan_power_contracts(work_root=Path(td))
        self.assertTrue(res.valid)
        self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertFalse(res.clean_room_forced)

    def test_05_corrupted_donor_libfan_blocks_audit(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            fx3_lib = root / "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib"
            fx6_lib = root / "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib"
            fx3_lib.mkdir(parents=True)
            fx6_lib.mkdir(parents=True)
            for d in (fx3_lib, fx6_lib):
                for fn in ("libfan.so", "libBusPower.so", "libUsbBusPower.so"):
                    (d / fn).write_bytes(b"\x7fELF\x02\x01\x01" + b"\x00" * 128)
            with patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "0"}):
                res = audit_donor_thermal_fan_power_contracts(
                    work_root=root,
                    force_clean_room=False,
                    include_large_binaries=False,
                )
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_DONOR_AUDIT_MISMATCH)
        self.assertTrue(len(res.errors) > 0)

    # --- Deliverable 2: FX3 Compact Fan PWM Thermal Runaway Guard ---

    def test_06_all_4_menu_fan_modes_nominal_pwm_ordering(self) -> None:
        temps = {"imx510_sensor_c": 48.0, "cxd90057_soc_c": 52.0, "cfexpress_slot_a_c": 49.0, "cfexpress_slot_b_c": 47.0}
        d_auto1, m1, ov1, _ = compute_fan_pwm_duty_pct(FAN_MODE_AUTO1, **temps)
        d_auto2, m2, ov2, _ = compute_fan_pwm_duty_pct(FAN_MODE_AUTO2, **temps)
        d_min, m3, ov3, _ = compute_fan_pwm_duty_pct(FAN_MODE_MINIMUM, **temps)
        d_off, m4, ov4, _ = compute_fan_pwm_duty_pct(FAN_MODE_OFF_IN_REC, **temps)

        self.assertEqual((m1, m2, m3, m4), VALID_MENU_FAN_MODES)
        self.assertFalse(any((ov1, ov2, ov3, ov4)))
        self.assertGreater(d_auto1, d_auto2)
        self.assertGreaterEqual(d_auto2, d_min)
        self.assertEqual(d_off, 0)

    def test_07_fan_mode_matrix_covers_all_4_modes_and_5_thermal_points(self) -> None:
        matrix = evaluate_fan_mode_matrix()
        self.assertEqual(set(matrix.keys()), set(VALID_MENU_FAN_MODES))
        for mode in VALID_MENU_FAN_MODES:
            self.assertTrue(matrix[mode]["nominal_45c"]["valid"])
            self.assertEqual(matrix[mode]["soft_warning_82c"]["status"], STATUS_THERMAL_SOFT_WARNING)
            self.assertEqual(matrix[mode]["soft_warning_82c"]["target_pwm_duty_pct"], 100)
            self.assertFalse(matrix[mode]["fail_closed_90c"]["valid"])
            self.assertEqual(matrix[mode]["fail_closed_90c"]["status"], STATUS_BLOCKED_THERMAL_RUNAWAY)
            self.assertTrue(matrix[mode]["fail_closed_90c"]["graceful_unmount_required"])
            self.assertTrue(matrix[mode]["fail_closed_90c"]["ram_overlay_teardown_required"])

    def test_08_off_in_rec_remains_0pct_below_62c_soc_and_68c_cfexpress(self) -> None:
        res = verify_fan_thermal_envelope(
            fan_mode=FAN_MODE_OFF_IN_REC,
            imx510_sensor_c=55.0,
            cxd90057_soc_c=61.9,
            cfexpress_slot_a_c=67.9,
            cfexpress_slot_b_c=65.0,
            observed_fan_rpm=0,
        )
        self.assertTrue(res.valid, res.errors)
        self.assertEqual(res.status, STATUS_VERIFIED_SAFE)
        self.assertFalse(res.thermal_override_engaged)
        self.assertEqual(res.effective_fan_mode, FAN_MODE_OFF_IN_REC)
        self.assertEqual(res.target_pwm_duty_pct, 0)

    def test_09_off_in_rec_mandatory_override_at_62c_soc(self) -> None:
        res = verify_fan_thermal_envelope(
            fan_mode=FAN_MODE_OFF_IN_REC,
            imx510_sensor_c=54.0,
            cxd90057_soc_c=SOC_FAN_OVERRIDE_TEMP_C,
            cfexpress_slot_a_c=55.0,
            cfexpress_slot_b_c=52.0,
            observed_fan_rpm=4100,
        )
        self.assertTrue(res.valid, res.errors)
        self.assertTrue(res.thermal_override_engaged)
        self.assertEqual(res.effective_fan_mode, "AUTO1_THERMAL_OVERRIDE")
        self.assertGreaterEqual(res.target_pwm_duty_pct, 65)
        self.assertTrue(any("62.0C" in r for r in res.override_reasons))

    def test_10_off_in_rec_mandatory_override_at_68c_cfexpress_slot_a_or_b(self) -> None:
        for slot_kwargs in (
            {"cfexpress_slot_a_c": CFEXPRESS_FAN_OVERRIDE_TEMP_C, "cfexpress_slot_b_c": 50.0},
            {"cfexpress_slot_a_c": 50.0, "cfexpress_slot_b_c": CFEXPRESS_FAN_OVERRIDE_TEMP_C},
        ):
            res = verify_fan_thermal_envelope(
                fan_mode=FAN_MODE_OFF_IN_REC,
                imx510_sensor_c=54.0,
                cxd90057_soc_c=58.0,
                observed_fan_rpm=4200,
                **slot_kwargs,
            )
            self.assertTrue(res.valid, res.errors)
            self.assertTrue(res.thermal_override_engaged)
            self.assertGreaterEqual(res.target_pwm_duty_pct, 65)
            self.assertTrue(any("68.0C" in r for r in res.override_reasons))

    def test_11_off_in_rec_with_override_disabled_fails_closed(self) -> None:
        res = verify_fan_thermal_envelope(
            fan_mode=FAN_MODE_OFF_IN_REC,
            cxd90057_soc_c=64.0,
            allow_thermal_override=False,
            observed_fan_rpm=0,
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_FAN_MODE_UNSAFE)
        self.assertFalse(res.recording_allowed)

    def test_12_always_off_and_unknown_fan_modes_blocked(self) -> None:
        for bad_mode in (FAN_MODE_ALWAYS_OFF, "TURBO_INVALID"):
            res = verify_fan_thermal_envelope(fan_mode=bad_mode)
            self.assertFalse(res.valid)
            self.assertEqual(res.status, STATUS_BLOCKED_FAN_MODE_UNSAFE)

    def test_13_soft_recording_warning_at_82c(self) -> None:
        res = verify_fan_thermal_envelope(
            fan_mode=FAN_MODE_MINIMUM,
            imx510_sensor_c=SOFT_RECORDING_WARNING_TEMP_C,
            cxd90057_soc_c=78.0,
            cfexpress_slot_a_c=79.0,
            cfexpress_slot_b_c=75.0,
            observed_fan_rpm=5400,
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_THERMAL_SOFT_WARNING)
        self.assertTrue(res.recording_warning)
        self.assertEqual(res.target_pwm_duty_pct, 100)
        self.assertFalse(res.graceful_unmount_required)
        self.assertFalse(res.abort_required)

    def test_14_fail_closed_teardown_at_90c_on_any_zone(self) -> None:
        for zone_kw in (
            {"imx510_sensor_c": FAIL_CLOSED_TEARDOWN_TEMP_C},
            {"cxd90057_soc_c": FAIL_CLOSED_TEARDOWN_TEMP_C},
            {"cfexpress_slot_a_c": FAIL_CLOSED_TEARDOWN_TEMP_C},
            {"cfexpress_slot_b_c": FAIL_CLOSED_TEARDOWN_TEMP_C},
        ):
            res = verify_fan_thermal_envelope(fan_mode=FAN_MODE_AUTO1, observed_fan_rpm=5500, **zone_kw)
            self.assertFalse(res.valid)
            self.assertEqual(res.status, STATUS_BLOCKED_THERMAL_RUNAWAY)
            self.assertTrue(res.graceful_unmount_required)
            self.assertTrue(res.ram_overlay_teardown_required)
            self.assertTrue(res.abort_required)
            self.assertFalse(res.recording_allowed)

    def test_15_broken_fan_stalled_rotor_and_unpatched_libfan_blocked(self) -> None:
        broken = verify_fan_thermal_envelope(fan_broken_status="FAN_BROKEN_STATUS_BROKEN")
        self.assertFalse(broken.valid)
        self.assertEqual(broken.status, STATUS_BLOCKED_FAN_CONTROLLER_FAULT)

        stalled = verify_fan_thermal_envelope(fan_mode=FAN_MODE_AUTO1, observed_fan_rpm=0)
        self.assertFalse(stalled.valid)
        self.assertEqual(stalled.status, STATUS_BLOCKED_FAN_CONTROLLER_FAULT)

        unpatched = verify_fan_thermal_envelope(libfan_stage_patch_verified=False, fan_i_bkup_is_valid_rc=9)
        self.assertFalse(unpatched.valid)
        self.assertEqual(unpatched.status, STATUS_BLOCKED_FAN_CONTROLLER_FAULT)

    def test_16_thermistor_fault_and_non_finite_temp_fail_closed(self) -> None:
        tfault = verify_fan_thermal_envelope(thermistor_fault=True)
        self.assertFalse(tfault.valid)
        self.assertEqual(tfault.status, STATUS_BLOCKED_THERMAL_TELEMETRY_INVALID)
        self.assertTrue(tfault.graceful_unmount_required)

        nan_temp = verify_fan_thermal_envelope(cxd90057_soc_c=float("nan"))
        self.assertFalse(nan_temp.valid)
        self.assertEqual(nan_temp.status, STATUS_BLOCKED_THERMAL_TELEMETRY_INVALID)

        absurd = verify_fan_thermal_envelope(cfexpress_slot_a_c=200.0)
        self.assertFalse(absurd.valid)
        self.assertEqual(absurd.status, STATUS_BLOCKED_THERMAL_TELEMETRY_INVALID)

    # --- Deliverable 3: NP-FZ100 (7.2V) vs BP-U (14.4V) & USB-PD 9V/3A Firewall ---

    def test_17_infolithium_normalization_prevents_false_0pct_boot_shutdown(self) -> None:
        for mv in (NP_FZ100_MIN_OPERATING_MV, 7200, 7800, NP_FZ100_MAX_OPERATING_MV):
            info = normalize_npfz100_infolithium_mv(mv)
            self.assertTrue(info["bpu_11500mv_would_false_trip"])
            self.assertFalse(info["false_zero_pct_boot_shutdown_triggered"])
            self.assertTrue(info["false_zero_pct_boot_shutdown_prevented"])
            self.assertGreaterEqual(info["infolithium_soc_pct"], 0)
            self.assertLessEqual(info["infolithium_soc_pct"], 100)

        bpu_trip = normalize_npfz100_infolithium_mv(8200, comparator_mode=COMPARATOR_RAW_BPU_11500MV)
        self.assertTrue(bpu_trip["false_zero_pct_boot_shutdown_triggered"])
        self.assertFalse(bpu_trip["false_zero_pct_boot_shutdown_prevented"])

    def test_18_h0_and_h1_rehearsal_healthy_npfz100_and_usbpd_9v3a_pass(self) -> None:
        for sess in (SESSION_H0_REHEARSAL, SESSION_H1_REHEARSAL):
            res = verify_battery_and_usbpd_firewall(
                session_mode=sess,
                raw_batt_mv=H0_H1_REHEARSAL_MIN_BATT_MV,
                infolithium_soc_pct=H0_H1_REHEARSAL_MIN_SOC_PCT,
                remaining_minutes=60,
                usbpd_attached=True,
                usbpd_contract_mv=USBPD_REQUIRED_VOLTAGE_MV,
                usbpd_contract_ma=USBPD_REQUIRED_CURRENT_MA,
                usbpd_measured_vbus_mv=USBPD_REQUIRED_VOLTAGE_MV - USBPD_MAX_VBUS_DROOP_MV,
            )
            self.assertTrue(res.valid, res.errors)
            self.assertEqual(res.status, STATUS_VERIFIED_SAFE)
            self.assertTrue(res.false_zero_pct_boot_shutdown_prevented)
            self.assertTrue(res.rehearsal_battery_gate_passed)
            self.assertTrue(res.usbpd_stability_passed)
            self.assertEqual(res.usbpd_contract_mw, USBPD_REQUIRED_POWER_MW)
            self.assertEqual(res.usbpd_vbus_droop_mv, USBPD_MAX_VBUS_DROOP_MV)
            self.assertFalse(res.persistent_emmc_writes_authorized)

    def test_19_raw_bpu_11500mv_and_19v5_dcin_comparators_blocked(self) -> None:
        bpu_comp = verify_battery_and_usbpd_firewall(comparator_mode=COMPARATOR_RAW_BPU_11500MV)
        self.assertFalse(bpu_comp.valid)
        self.assertEqual(bpu_comp.status, STATUS_BLOCKED_BATT_COMPARATOR_MISMATCH)

        bpu_flag = verify_battery_and_usbpd_firewall(bp_u_11500mv_comparator_enabled=True)
        self.assertFalse(bpu_flag.valid)
        self.assertEqual(bpu_flag.status, STATUS_BLOCKED_BATT_COMPARATOR_MISMATCH)

        dcin_comp = verify_battery_and_usbpd_firewall(comparator_mode=COMPARATOR_RAW_19V5_DC_IN)
        self.assertFalse(dcin_comp.valid)
        self.assertEqual(dcin_comp.status, STATUS_BLOCKED_BATT_COMPARATOR_MISMATCH)

    def test_20_wrong_bpu_chemistry_and_cell_overvoltage_blocked(self) -> None:
        bpu_chem = verify_battery_and_usbpd_firewall(battery_chemistry="BP-U", raw_batt_mv=14400)
        self.assertFalse(bpu_chem.valid)
        self.assertEqual(bpu_chem.status, STATUS_BLOCKED_BATT_COMPARATOR_MISMATCH)

        ov = verify_battery_and_usbpd_firewall(raw_batt_mv=11500)
        self.assertFalse(ov.valid)
        self.assertEqual(ov.status, STATUS_BLOCKED_BATT_COMPARATOR_MISMATCH)

    def test_21_h0_h1_rehearsal_blocks_below_80pct_soc_or_below_7800mv(self) -> None:
        low_soc = verify_battery_and_usbpd_firewall(
            session_mode=SESSION_H0_REHEARSAL,
            infolithium_soc_pct=79,
            raw_batt_mv=7900,
        )
        self.assertFalse(low_soc.valid)
        self.assertEqual(low_soc.status, STATUS_BLOCKED_NPFZ100_BROWNOUT)

        low_mv = verify_battery_and_usbpd_firewall(
            session_mode=SESSION_H1_REHEARSAL,
            infolithium_soc_pct=85,
            raw_batt_mv=7799,
        )
        self.assertFalse(low_mv.valid)
        self.assertEqual(low_mv.status, STATUS_BLOCKED_NPFZ100_BROWNOUT)

    def test_22_npfz100_deep_brownout_fake_thermal_and_overcurrent_blocked(self) -> None:
        deep = verify_battery_and_usbpd_firewall(
            session_mode=SESSION_STANDARD_RUNTIME,
            raw_batt_mv=6100,
            infolithium_soc_pct=5,
            remaining_minutes=3,
        )
        self.assertFalse(deep.valid)
        self.assertEqual(deep.status, STATUS_BLOCKED_NPFZ100_BROWNOUT)

        fake = verify_battery_and_usbpd_firewall(battery_auth_status="BATT_END_FAKE")
        self.assertFalse(fake.valid)
        self.assertEqual(fake.status, STATUS_BLOCKED_NPFZ100_BROWNOUT)

        therm = verify_battery_and_usbpd_firewall(battery_thermal_fault=True)
        self.assertFalse(therm.valid)
        self.assertEqual(therm.status, STATUS_BLOCKED_NPFZ100_BROWNOUT)

        oc = verify_battery_and_usbpd_firewall(battery_overcurrent_fault=True)
        self.assertFalse(oc.valid)
        self.assertEqual(oc.status, STATUS_BLOCKED_NPFZ100_BROWNOUT)

    def test_23_usbpd_below_9v3a_27w_blocked_for_rehearsal(self) -> None:
        unattached = verify_battery_and_usbpd_firewall(session_mode=SESSION_H0_REHEARSAL, usbpd_attached=False)
        self.assertFalse(unattached.valid)
        self.assertEqual(unattached.status, STATUS_BLOCKED_USBPD_CONTRACT_INSUFFICIENT)

        legacy_5v = verify_battery_and_usbpd_firewall(
            session_mode=SESSION_H0_REHEARSAL,
            usbpd_contract_mv=5000,
            usbpd_contract_ma=3000,
            usbpd_measured_vbus_mv=4950,
        )
        self.assertFalse(legacy_5v.valid)
        self.assertEqual(legacy_5v.status, STATUS_BLOCKED_USBPD_CONTRACT_INSUFFICIENT)

        pd_18w = verify_battery_and_usbpd_firewall(
            session_mode=SESSION_H1_REHEARSAL,
            usbpd_contract_mv=9000,
            usbpd_contract_ma=2000,
            usbpd_measured_vbus_mv=8900,
        )
        self.assertFalse(pd_18w.valid)
        self.assertEqual(pd_18w.status, STATUS_BLOCKED_USBPD_CONTRACT_INSUFFICIENT)

    def test_24_usbpd_vbus_droop_above_450mv_blocked(self) -> None:
        droop = verify_battery_and_usbpd_firewall(
            session_mode=SESSION_H0_REHEARSAL,
            usbpd_contract_mv=9000,
            usbpd_contract_ma=3000,
            usbpd_measured_vbus_mv=8549,  # 451 mV droop > 450 mV
        )
        self.assertFalse(droop.valid)
        self.assertEqual(droop.status, STATUS_BLOCKED_USBPD_VBUS_DROOP)
        self.assertEqual(droop.usbpd_vbus_droop_mv, 451)

        runtime_droop = verify_battery_and_usbpd_firewall(
            session_mode=SESSION_STANDARD_RUNTIME,
            usbpd_contract_mv=9000,
            usbpd_contract_ma=3000,
            usbpd_measured_vbus_mv=8400,
        )
        self.assertFalse(runtime_droop.valid)
        self.assertEqual(runtime_droop.status, STATUS_BLOCKED_USBPD_VBUS_DROOP)

    def test_25_persistent_emmc_write_request_hard_blocked(self) -> None:
        res = verify_battery_and_usbpd_firewall(request_persistent_emmc_write=True)
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        self.assertFalse(res.persistent_emmc_writes_authorized)

    # --- Deliverable 4: Unified Evaluator, Dual-Mode & CLI ---

    def test_26_unified_evaluator_passes_in_local_or_current_mode(self) -> None:
        report = evaluate_thermal_pwm_and_power_guard(include_large_binaries=False)
        self.assertEqual(report.schema, THERMAL_PWM_POWER_GUARD_SCHEMA)
        self.assertTrue(report.all_passed, report.errors)
        self.assertEqual(report.status, STATUS_VERIFIED_SAFE)
        self.assertFalse(report.persistent_emmc_writes_authorized)
        self.assertFalse(report.persistent_write_release)

    def test_27_unified_evaluator_passes_in_clean_room_mode(self) -> None:
        with patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            report = evaluate_thermal_pwm_and_power_guard()
        self.assertTrue(report.all_passed, report.errors)
        self.assertEqual(report.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(report.clean_room_forced)
        self.assertFalse(report.persistent_emmc_writes_authorized)

    def test_28_unified_evaluator_propagates_thermal_runaway_and_power_faults(self) -> None:
        bad_therm = evaluate_thermal_pwm_and_power_guard(
            force_clean_room=True,
            fan_kwargs={"cxd90057_soc_c": 91.0},
        )
        self.assertFalse(bad_therm.all_passed)
        self.assertEqual(bad_therm.status, STATUS_BLOCKED_THERMAL_RUNAWAY)

        bad_pwr = evaluate_thermal_pwm_and_power_guard(
            force_clean_room=True,
            power_kwargs={"comparator_mode": COMPARATOR_RAW_BPU_11500MV},
        )
        self.assertFalse(bad_pwr.all_passed)
        self.assertEqual(bad_pwr.status, STATUS_BLOCKED_BATT_COMPARATOR_MISMATCH)

    def test_29_package_cli_verify_thermal_power_guard_clean_room_json(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = package_cli_main(["verify-thermal-power-guard", "--clean-room", "--json"])
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["schema"], THERMAL_PWM_POWER_GUARD_SCHEMA)
        self.assertTrue(payload["all_passed"])
        self.assertTrue(payload["clean_room_forced"])
        self.assertEqual(payload["verification_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertFalse(payload["persistent_emmc_writes_authorized"])
        self.assertFalse(payload["persistent_write_release"])

    def test_30_module_cli_flags_and_fail_closed_exit_code(self) -> None:
        ok_buf = io.StringIO()
        with contextlib.redirect_stdout(ok_buf):
            rc_ok = module_cli_main(["--clean-room", "--fan-mode", "OFF_IN_REC", "--soc-c", "64.0", "--json"])
        self.assertEqual(rc_ok, 0)
        ok_data = json.loads(ok_buf.getvalue())
        self.assertTrue(ok_data["thermal_envelope"]["thermal_override_engaged"])

        bad_buf = io.StringIO()
        with contextlib.redirect_stdout(bad_buf):
            rc_bad = module_cli_main(["--clean-room", "--soc-c", "92.0", "--json"])
        self.assertEqual(rc_bad, 1)
        bad_data = json.loads(bad_buf.getvalue())
        self.assertEqual(bad_data["status"], STATUS_BLOCKED_THERMAL_RUNAWAY)


if __name__ == "__main__":
    unittest.main()
