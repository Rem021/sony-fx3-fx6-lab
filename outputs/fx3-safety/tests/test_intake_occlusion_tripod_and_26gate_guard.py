"""Fast dual-mode unit tests for Phase 92 — Sigma Fan Intake/Exhaust & Blimp Firewall (G25),
1/4-20 Tripod Screw Depth / Cage Torque / Underwater Housing Vacuum Guard (G26),
and Unified 26-Gate Master Safety Preflight (`G01..G26`).
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
from fx3_safety.dewpoint_tec_usbc_and_24gate_guard import (
    COOLING_METHOD_EXTERNAL_PELTIER_TEC,
    STATUS_BLOCKED_PMIC_5V_ACCESSORY_OVERBUDGET,
    STATUS_BLOCKED_SUB_DEWPOINT_TEC_CONDENSATION_HAZARD,
    evaluate_24gate_preflight,
)
from fx3_safety.intake_occlusion_tripod_and_26gate_guard import (
    FAN_MODE_AUTO1,
    FAN_MODE_AUTO2,
    FAN_MODE_MIN,
    FAN_MODE_OFF_IN_REC,
    FX3_TRIPOD_POCKET_MAX_DEPTH_MM,
    G25_GATE_CODE,
    G25_GATE_ID,
    G26_GATE_CODE,
    G26_GATE_ID,
    HIGH_LOAD_WORKLOADS,
    INTAKE_TRIPOD_26GATE_SCHEMA,
    INTAKE_TRIPOD_26GATE_VERSION,
    MAX_HOUSING_VACUUM_LEAK_MBAR_PER_10MIN,
    MAX_MOUNTING_TORQUE_NM,
    MIN_HOUSING_VACUUM_CHECK_ELAPSED_MIN,
    OFF_IN_REC_HIGH_LOAD_MAX_CLIP_MIN,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    SEALED_ENCLOSURE_MAX_TEMP_C,
    SIGMA_FAN_DEFAULT_MIN_EXPECTED_RPM,
    SIGMA_FAN_MIN_VENT_CLEARANCE_MM,
    STATUS_BLOCKED_DONOR_INTEGRITY,
    STATUS_BLOCKED_DUCT_OCCLUSION_BACKPRESSURE,
    STATUS_BLOCKED_FAN_DUCT_TELEMETRY_INVALID,
    STATUS_BLOCKED_FAN_OFF_IN_REC_HIGH_LOAD,
    STATUS_BLOCKED_FAN_TACHOMETER_ROTOR_STALL,
    STATUS_BLOCKED_HOUSING_VACUUM_LEAK_OR_MOISTURE,
    STATUS_BLOCKED_MOUNTING_HOUSING_TELEMETRY_INVALID,
    STATUS_BLOCKED_MOUNTING_OVER_TORQUE_HAZARD,
    STATUS_BLOCKED_PERSISTENT_EMMC_WRITE,
    STATUS_BLOCKED_SEALED_BLIMP_RECIRCULATION,
    STATUS_BLOCKED_TRIPOD_SCREW_BOTTOM_OUT_DAMAGE,
    STATUS_SAFE,
    STATUS_VERIFIED_G25,
    STATUS_VERIFIED_G26,
    STATUS_VERIFIED_SAFE,
    audit_phase92_donor_contracts,
    evaluate_26_master_safety_gates,
    evaluate_26gate_preflight,
    evaluate_g25_sigma_fan_intake_exhaust,
    evaluate_g26_tripod_torque_and_housing_vacuum,
    main as module_cli_main,
    verify_sigma_fan_intake_exhaust_firewall,
    verify_tripod_screw_torque_and_housing_vacuum_guard,
)
from fx3_safety.master_16gate_preflight import DEFAULT_REPO_ROOT
from fx3_safety.rig_groundloop_lensrail_and_20gate_guard import (
    STATUS_FAIL_OFFLINE_HARDWARE_NOT_ATTACHED,
)


class IntakeOcclusionTripodAnd26GateGuardTests(unittest.TestCase):
    # --- 1. Hard Redlines, Package Exports & O_RDONLY Donor Audit ---

    def test_01_hard_locked_redlines_and_package_exports(self) -> None:
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(PERSISTENT_WRITE_RELEASE)
        self.assertEqual(INTAKE_TRIPOD_26GATE_SCHEMA, "fx3-intake-occlusion-tripod-26gate-preflight-v1")
        self.assertEqual(INTAKE_TRIPOD_26GATE_VERSION, "1.0.0")
        for sym in (
            "INTAKE_TRIPOD_26GATE_SCHEMA",
            "G25_GATE_ID",
            "G26_GATE_ID",
            "STATUS_BLOCKED_FAN_TACHOMETER_ROTOR_STALL",
            "STATUS_BLOCKED_DUCT_OCCLUSION_BACKPRESSURE",
            "STATUS_BLOCKED_FAN_OFF_IN_REC_HIGH_LOAD",
            "STATUS_BLOCKED_SEALED_BLIMP_RECIRCULATION",
            "STATUS_BLOCKED_TRIPOD_SCREW_BOTTOM_OUT_DAMAGE",
            "STATUS_BLOCKED_MOUNTING_OVER_TORQUE_HAZARD",
            "STATUS_BLOCKED_HOUSING_VACUUM_LEAK_OR_MOISTURE",
            "audit_phase92_donor_contracts",
            "verify_sigma_fan_intake_exhaust_firewall",
            "verify_tripod_screw_torque_and_housing_vacuum_guard",
            "evaluate_g25_sigma_fan_intake_exhaust",
            "evaluate_g26_tripod_torque_and_housing_vacuum",
            "evaluate_26gate_preflight",
            "evaluate_26_master_safety_gates",
            "intake_occlusion_tripod_and_26gate_guard",
        ):
            self.assertIn(sym, fx3_safety.__all__)
            self.assertTrue(hasattr(fx3_safety, sym))
        # Ensure existing Phase 44 uppercase FAN_MODE_* exports were NOT overwritten
        self.assertEqual(fx3_safety.FAN_MODE_AUTO1, "AUTO1")
        self.assertEqual(fx3_safety.FAN_MODE_OFF_IN_REC, "OFF_IN_REC")

    def test_02_donor_audit_o_rdonly_and_clean_room_fallback(self) -> None:
        observed_flags = []
        orig_open = os.open

        def spy_open(path, flags, *args, **kwargs):
            observed_flags.append((str(path), flags))
            return orig_open(path, flags, *args, **kwargs)

        with patch("os.open", side_effect=spy_open):
            res_default = audit_phase92_donor_contracts()
        self.assertTrue(res_default.valid)
        self.assertEqual(res_default.status, STATUS_VERIFIED_SAFE)
        self.assertEqual(res_default.access_mode, "O_RDONLY")
        self.assertEqual(len(res_default.missing_markers), 0)
        self.assertEqual(res_default.bk4_overtemp_thresholds_c["fx3"]["overtemp_warn_c"], 82)
        self.assertEqual(res_default.bk4_overtemp_thresholds_c["fx6"]["overtemp_warn_c"], 76)
        for path, flags in observed_flags:
            if any(k in path for k in ("libfan.so", "FX3-CX95900", "CX95898_NTSC")):
                self.assertEqual(flags & os.O_ACCMODE, os.O_RDONLY, f"Non-O_RDONLY open on {path}")

        res_clean = audit_phase92_donor_contracts(force_clean_room=True)
        self.assertTrue(res_clean.valid)
        self.assertEqual(res_clean.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(res_clean.files_inspected, 0)
        self.assertEqual(len(res_clean.sha256_by_artifact), 4)
        self.assertEqual(res_clean.bk4_overtemp_thresholds_c["fx3"]["overtemp_warn_c"], 82)

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
            (fx6_lib / "libfan.so").write_bytes(b"corrupt")
            (fx3_seed / "FX3-CX95900_ALLLANG-Backup.bin").write_bytes(b"corrupt")
            (fx6_seed / "CX95898_NTSC.bin").write_bytes(b"corrupt")
            res = audit_phase92_donor_contracts(work_root=tmp, force_clean_room=False)
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_DONOR_INTEGRITY)
        self.assertEqual(len(res.missing_markers), 4)

    # --- 2. Gate G25 — Sigma Centrifugal Fan Intake/Exhaust & Blimp Firewall ---

    def test_04_g25_default_healthy_configuration_passes(self) -> None:
        res = verify_sigma_fan_intake_exhaust_firewall()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_SAFE)
        self.assertEqual(res.violation_codes, ())
        self.assertTrue(res.tachometer_rotor_ok)
        self.assertTrue(res.duct_clearance_ok)
        self.assertTrue(res.off_in_rec_high_load_safe)
        self.assertTrue(res.sealed_enclosure_safe)
        self.assertFalse(res.persistent_emmc_writes_authorized)

    def test_05_g25_blocks_fan_tachometer_rotor_stall_when_pwm_ge_25(self) -> None:
        res = verify_sigma_fan_intake_exhaust_firewall(
            pwm_duty_pct=25.0,
            measured_rpm=450.0,
            min_expected_rpm=SIGMA_FAN_DEFAULT_MIN_EXPECTED_RPM,
        )
        self.assertFalse(res.valid)
        self.assertFalse(res.tachometer_rotor_ok)
        self.assertEqual(res.status, STATUS_BLOCKED_FAN_TACHOMETER_ROTOR_STALL)
        self.assertIn(STATUS_BLOCKED_FAN_TACHOMETER_ROTOR_STALL, res.violation_codes)

    def test_06_g25_allows_zero_rpm_below_25pct_pwm_and_healthy_rpm_above_25pct(self) -> None:
        res_idle = verify_sigma_fan_intake_exhaust_firewall(
            pwm_duty_pct=20.0,
            measured_rpm=0.0,
            min_expected_rpm=1800.0,
        )
        self.assertTrue(res_idle.valid)
        self.assertTrue(res_idle.tachometer_rotor_ok)

        res_spin = verify_sigma_fan_intake_exhaust_firewall(
            pwm_duty_pct=25.0,
            measured_rpm=1800.0,
            min_expected_rpm=1800.0,
        )
        self.assertTrue(res_spin.valid)
        self.assertTrue(res_spin.tachometer_rotor_ok)

    def test_07_g25_blocks_intake_or_exhaust_occlusion_below_5mm(self) -> None:
        res_intake = verify_sigma_fan_intake_exhaust_firewall(
            intake_clearance_mm=2.5,
            exhaust_clearance_mm=10.0,
        )
        self.assertFalse(res_intake.valid)
        self.assertFalse(res_intake.duct_clearance_ok)
        self.assertEqual(res_intake.status, STATUS_BLOCKED_DUCT_OCCLUSION_BACKPRESSURE)

        res_exhaust = verify_sigma_fan_intake_exhaust_firewall(
            intake_clearance_mm=10.0,
            exhaust_clearance_mm=4.9,
        )
        self.assertFalse(res_exhaust.valid)
        self.assertFalse(res_exhaust.duct_clearance_ok)
        self.assertEqual(res_exhaust.status, STATUS_BLOCKED_DUCT_OCCLUSION_BACKPRESSURE)

        res_boundary = verify_sigma_fan_intake_exhaust_firewall(
            intake_clearance_mm=SIGMA_FAN_MIN_VENT_CLEARANCE_MM,
            exhaust_clearance_mm=SIGMA_FAN_MIN_VENT_CLEARANCE_MM,
        )
        self.assertTrue(res_boundary.valid)
        self.assertTrue(res_boundary.duct_clearance_ok)

    def test_08_g25_blocks_fan_off_in_rec_high_load_over_8_min(self) -> None:
        for wl in HIGH_LOAD_WORKLOADS:
            res = verify_sigma_fan_intake_exhaust_firewall(
                fan_mode=FAN_MODE_OFF_IN_REC,
                workload=wl,
                clip_duration_min=OFF_IN_REC_HIGH_LOAD_MAX_CLIP_MIN + 0.5,
            )
            self.assertFalse(res.valid)
            self.assertFalse(res.off_in_rec_high_load_safe)
            self.assertEqual(res.status, STATUS_BLOCKED_FAN_OFF_IN_REC_HIGH_LOAD)

    def test_09_g25_allows_short_off_in_rec_and_long_active_fan_modes(self) -> None:
        # Exactly 8.0 min is allowed (with warning)
        res_short = verify_sigma_fan_intake_exhaust_firewall(
            fan_mode=FAN_MODE_OFF_IN_REC,
            workload="4K_120p",
            clip_duration_min=OFF_IN_REC_HIGH_LOAD_MAX_CLIP_MIN,
        )
        self.assertTrue(res_short.valid)
        self.assertTrue(res_short.off_in_rec_high_load_safe)
        self.assertGreaterEqual(len(res_short.warnings), 1)

        # Auto1 / Auto2 / Min allowed for long 60 min 4K_120p takes
        for mode in (FAN_MODE_AUTO1, FAN_MODE_AUTO2, FAN_MODE_MIN):
            res_active = verify_sigma_fan_intake_exhaust_firewall(
                fan_mode=mode,
                workload="4K_120p",
                clip_duration_min=60.0,
            )
            self.assertTrue(res_active.valid)
            self.assertTrue(res_active.off_in_rec_high_load_safe)

    def test_10_g25_blocks_sealed_blimp_or_raincover_recirculation_over_42c(self) -> None:
        res_hot = verify_sigma_fan_intake_exhaust_firewall(
            enclosure_sealed_blimp_or_raincover=True,
            internal_enclosure_temp_c=SEALED_ENCLOSURE_MAX_TEMP_C + 0.5,
        )
        self.assertFalse(res_hot.valid)
        self.assertFalse(res_hot.sealed_enclosure_safe)
        self.assertEqual(res_hot.status, STATUS_BLOCKED_SEALED_BLIMP_RECIRCULATION)

        res_ok = verify_sigma_fan_intake_exhaust_firewall(
            enclosure_sealed_blimp_or_raincover=True,
            internal_enclosure_temp_c=SEALED_ENCLOSURE_MAX_TEMP_C,
        )
        self.assertTrue(res_ok.valid)
        self.assertTrue(res_ok.sealed_enclosure_safe)
        self.assertGreaterEqual(len(res_ok.warnings), 1)

        # Unsealed ambient > 42C does not trigger sealed blimp recirculation
        res_open = verify_sigma_fan_intake_exhaust_firewall(
            enclosure_sealed_blimp_or_raincover=False,
            internal_enclosure_temp_c=45.0,
        )
        self.assertTrue(res_open.valid)

    def test_11_g25_rejects_invalid_telemetry_and_persistent_emmc_write(self) -> None:
        res_mode = verify_sigma_fan_intake_exhaust_firewall(fan_mode="TURBO_UNKNOWN")
        self.assertFalse(res_mode.valid)
        self.assertEqual(res_mode.status, STATUS_BLOCKED_FAN_DUCT_TELEMETRY_INVALID)

        res_pwm = verify_sigma_fan_intake_exhaust_firewall(pwm_duty_pct=120.0)
        self.assertFalse(res_pwm.valid)
        self.assertEqual(res_pwm.status, STATUS_BLOCKED_FAN_DUCT_TELEMETRY_INVALID)

        res_neg = verify_sigma_fan_intake_exhaust_firewall(intake_clearance_mm=-1.0)
        self.assertFalse(res_neg.valid)
        self.assertEqual(res_neg.status, STATUS_BLOCKED_FAN_DUCT_TELEMETRY_INVALID)

        res_emmc = verify_sigma_fan_intake_exhaust_firewall(request_persistent_emmc_writes=True)
        self.assertFalse(res_emmc.valid)
        self.assertEqual(res_emmc.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        self.assertFalse(res_emmc.persistent_emmc_writes_authorized)

    def test_12_g25_accumulates_multiple_violations_deterministically(self) -> None:
        res = verify_sigma_fan_intake_exhaust_firewall(
            pwm_duty_pct=60.0,
            measured_rpm=0.0,
            intake_clearance_mm=1.0,
            fan_mode="off_in_rec",
            workload="4k_60p_raw_hdmi",
            clip_duration_min=15.0,
            enclosure_sealed_blimp_or_raincover=True,
            internal_enclosure_temp_c=48.0,
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            set(res.violation_codes),
            {
                STATUS_BLOCKED_FAN_TACHOMETER_ROTOR_STALL,
                STATUS_BLOCKED_DUCT_OCCLUSION_BACKPRESSURE,
                STATUS_BLOCKED_FAN_OFF_IN_REC_HIGH_LOAD,
                STATUS_BLOCKED_SEALED_BLIMP_RECIRCULATION,
            },
        )

    # --- 3. Gate G26 — 1/4-20 Tripod Screw Depth, Cage Torque & Housing Vacuum ---

    def test_13_g26_default_healthy_configuration_passes(self) -> None:
        res = verify_tripod_screw_torque_and_housing_vacuum_guard()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_SAFE)
        self.assertLessEqual(res.effective_screw_protrusion_mm, FX3_TRIPOD_POCKET_MAX_DEPTH_MM)
        self.assertLessEqual(res.applied_torque_nm, MAX_MOUNTING_TORQUE_NM)
        self.assertTrue(res.tripod_screw_depth_safe)
        self.assertTrue(res.mounting_torque_safe)
        self.assertTrue(res.housing_vacuum_and_moisture_safe)
        self.assertFalse(res.immediate_power_off_abort_required)
        self.assertFalse(res.persistent_emmc_writes_authorized)

    def test_14_g26_blocks_tripod_screw_bottom_out_over_5_5mm(self) -> None:
        res_direct = verify_tripod_screw_torque_and_housing_vacuum_guard(
            effective_screw_protrusion_mm=5.6,
        )
        self.assertFalse(res_direct.valid)
        self.assertFalse(res_direct.tripod_screw_depth_safe)
        self.assertEqual(res_direct.status, STATUS_BLOCKED_TRIPOD_SCREW_BOTTOM_OUT_DAMAGE)

        # Long 7.5mm quick-release screw without rubber washer/plate thickness
        res_unwashed = verify_tripod_screw_torque_and_housing_vacuum_guard(
            screw_thread_length_mm=7.5,
            plate_thickness_mm=1.0,
            washer_thickness_mm=0.0,
        )
        self.assertFalse(res_unwashed.valid)
        self.assertEqual(res_unwashed.effective_screw_protrusion_mm, 6.5)
        self.assertEqual(res_unwashed.status, STATUS_BLOCKED_TRIPOD_SCREW_BOTTOM_OUT_DAMAGE)

        # Adding 1.5mm rubber washer brings protrusion to 5.0mm <= 5.5mm -> pass
        res_washed = verify_tripod_screw_torque_and_housing_vacuum_guard(
            screw_thread_length_mm=7.5,
            plate_thickness_mm=1.0,
            washer_thickness_mm=1.5,
        )
        self.assertTrue(res_washed.valid)
        self.assertEqual(res_washed.effective_screw_protrusion_mm, 5.0)

        # Exact 5.5mm boundary passes
        res_exact = verify_tripod_screw_torque_and_housing_vacuum_guard(
            effective_screw_protrusion_mm=FX3_TRIPOD_POCKET_MAX_DEPTH_MM,
        )
        self.assertTrue(res_exact.valid)

    def test_15_g26_blocks_over_torque_over_3_5nm_and_unpinned_heavy_lens(self) -> None:
        res_torque = verify_tripod_screw_torque_and_housing_vacuum_guard(
            applied_torque_nm=MAX_MOUNTING_TORQUE_NM + 0.1,
        )
        self.assertFalse(res_torque.valid)
        self.assertFalse(res_torque.mounting_torque_safe)
        self.assertEqual(res_torque.status, STATUS_BLOCKED_MOUNTING_OVER_TORQUE_HAZARD)

        res_single_flag = verify_tripod_screw_torque_and_housing_vacuum_guard(
            single_screw_no_anti_twist_pin_heavy_lens=True,
        )
        self.assertFalse(res_single_flag.valid)
        self.assertEqual(res_single_flag.status, STATUS_BLOCKED_MOUNTING_OVER_TORQUE_HAZARD)

        res_derived_flag = verify_tripod_screw_torque_and_housing_vacuum_guard(
            heavy_lens_attached=True,
            anti_twist_pin_or_dual_screw_engaged=False,
        )
        self.assertFalse(res_derived_flag.valid)
        self.assertTrue(res_derived_flag.single_screw_no_anti_twist_pin_heavy_lens)
        self.assertEqual(res_derived_flag.status, STATUS_BLOCKED_MOUNTING_OVER_TORQUE_HAZARD)

        res_ok = verify_tripod_screw_torque_and_housing_vacuum_guard(
            applied_torque_nm=MAX_MOUNTING_TORQUE_NM,
            heavy_lens_attached=True,
            anti_twist_pin_or_dual_screw_engaged=True,
        )
        self.assertTrue(res_ok.valid)

    def test_16_g26_blocks_underwater_housing_vacuum_leak_moisture_and_short_hold(self) -> None:
        # Leak > 1.5 mbar/10min
        res_leak = verify_tripod_screw_torque_and_housing_vacuum_guard(
            underwater_housing_mode=True,
            housing_brand="Nauticam",
            vacuum_pressure_drop_mbar_per_10min=MAX_HOUSING_VACUUM_LEAK_MBAR_PER_10MIN + 0.2,
            moisture_sensor_triggered=False,
            vacuum_check_elapsed_min=15.0,
        )
        self.assertFalse(res_leak.valid)
        self.assertFalse(res_leak.housing_vacuum_and_moisture_safe)
        self.assertTrue(res_leak.immediate_power_off_abort_required)
        self.assertEqual(res_leak.status, STATUS_BLOCKED_HOUSING_VACUUM_LEAK_OR_MOISTURE)

        # Moisture strip triggered
        res_wet = verify_tripod_screw_torque_and_housing_vacuum_guard(
            underwater_housing_mode=True,
            housing_brand="Seafrogs",
            vacuum_pressure_drop_mbar_per_10min=0.1,
            moisture_sensor_triggered=True,
            vacuum_check_elapsed_min=20.0,
        )
        self.assertFalse(res_wet.valid)
        self.assertTrue(res_wet.immediate_power_off_abort_required)
        self.assertEqual(res_wet.status, STATUS_BLOCKED_HOUSING_VACUUM_LEAK_OR_MOISTURE)

        # Insufficient vacuum hold time < 10.0 min
        res_short = verify_tripod_screw_torque_and_housing_vacuum_guard(
            underwater_housing_mode=True,
            housing_brand="Nauticam",
            vacuum_pressure_drop_mbar_per_10min=0.0,
            moisture_sensor_triggered=False,
            vacuum_check_elapsed_min=MIN_HOUSING_VACUUM_CHECK_ELAPSED_MIN - 1.0,
        )
        self.assertFalse(res_short.valid)
        self.assertTrue(res_short.immediate_power_off_abort_required)
        self.assertEqual(res_short.status, STATUS_BLOCKED_HOUSING_VACUUM_LEAK_OR_MOISTURE)

    def test_17_g26_allows_healthy_underwater_housing_seal_and_skips_when_disabled(self) -> None:
        res_uw_ok = verify_tripod_screw_torque_and_housing_vacuum_guard(
            underwater_housing_mode=True,
            housing_brand="Nauticam",
            vacuum_pressure_drop_mbar_per_10min=MAX_HOUSING_VACUUM_LEAK_MBAR_PER_10MIN,
            moisture_sensor_triggered=False,
            vacuum_check_elapsed_min=MIN_HOUSING_VACUUM_CHECK_ELAPSED_MIN,
        )
        self.assertTrue(res_uw_ok.valid)
        self.assertTrue(res_uw_ok.housing_vacuum_and_moisture_safe)
        self.assertFalse(res_uw_ok.immediate_power_off_abort_required)

        res_dry = verify_tripod_screw_torque_and_housing_vacuum_guard(
            underwater_housing_mode=False,
            vacuum_pressure_drop_mbar_per_10min=5.0,
            vacuum_check_elapsed_min=0.0,
        )
        self.assertTrue(res_dry.valid)

    def test_18_g26_rejects_invalid_telemetry_and_persistent_emmc_write(self) -> None:
        res_nan = verify_tripod_screw_torque_and_housing_vacuum_guard(
            effective_screw_protrusion_mm=float("nan"),
        )
        self.assertFalse(res_nan.valid)
        self.assertEqual(res_nan.status, STATUS_BLOCKED_MOUNTING_HOUSING_TELEMETRY_INVALID)

        res_neg_torque = verify_tripod_screw_torque_and_housing_vacuum_guard(applied_torque_nm=-0.5)
        self.assertFalse(res_neg_torque.valid)
        self.assertEqual(res_neg_torque.status, STATUS_BLOCKED_MOUNTING_HOUSING_TELEMETRY_INVALID)

        res_emmc = verify_tripod_screw_torque_and_housing_vacuum_guard(request_persistent_emmc_writes=True)
        self.assertFalse(res_emmc.valid)
        self.assertEqual(res_emmc.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        self.assertFalse(res_emmc.persistent_emmc_writes_authorized)

    # --- 4. Gate G25 & G26 Evaluators & 26-Gate Master Safety Preflight ---

    def test_19_g25_and_g26_verdicts_dual_mode(self) -> None:
        v25, r25 = evaluate_g25_sigma_fan_intake_exhaust(force_clean_room=True)
        self.assertTrue(v25.passed)
        self.assertEqual(v25.gate_id, G25_GATE_ID)
        self.assertEqual(v25.gate_code, G25_GATE_CODE)
        self.assertEqual(v25.status, STATUS_VERIFIED_G25)
        self.assertFalse(r25.persistent_emmc_writes_authorized)

        v26, r26 = evaluate_g26_tripod_torque_and_housing_vacuum(force_clean_room=True)
        self.assertTrue(v26.passed)
        self.assertEqual(v26.gate_id, G26_GATE_ID)
        self.assertEqual(v26.gate_code, G26_GATE_CODE)
        self.assertEqual(v26.status, STATUS_VERIFIED_G26)
        self.assertFalse(r26.persistent_emmc_writes_authorized)

    def test_20_26gate_offline_default_23_of_26_and_g10_g12_fail_offline(self) -> None:
        rep = evaluate_26gate_preflight(DEFAULT_REPO_ROOT, force_clean_room=True)
        self.assertEqual(rep.schema, INTAKE_TRIPOD_26GATE_SCHEMA)
        self.assertEqual(len(rep.gates), 26)
        self.assertEqual(rep.summary["total_gates"], 26)
        self.assertEqual(rep.summary["verified_gates"], 23)
        self.assertEqual(rep.summary["blocked_or_pending_gates"], 3)
        self.assertTrue(rep.offline_23_gates_verified)
        self.assertFalse(rep.all_26_gates_verified)
        self.assertFalse(rep.dry_run_rehearsal_only)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.persistent_write_release)
        self.assertEqual(rep.status, "VERIFIED_23_OF_26_AWAITING_PHYSICAL_TIER0")
        for idx in (9, 10, 11):
            self.assertFalse(rep.gates[idx]["passed"])
            self.assertEqual(rep.gates[idx]["status"], STATUS_FAIL_OFFLINE_HARDWARE_NOT_ATTACHED)

    def test_21_26gate_dry_run_simulated_backup_26_of_26_and_redlines_locked(self) -> None:
        rep = evaluate_26gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
        )
        self.assertEqual(len(rep.gates), 26)
        self.assertEqual(rep.summary["verified_gates"], 26)
        self.assertEqual(rep.summary["blocked_or_pending_gates"], 0)
        self.assertTrue(rep.all_26_gates_verified)
        self.assertTrue(rep.dry_run_rehearsal_only)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.persistent_write_release)
        self.assertEqual(rep.status, "VERIFIED_ALL_26_GATES_DRY_RUN_SIMULATED_BACKUP")
        self.assertTrue(all(g["passed"] for g in rep.gates))

    def test_22_26gate_propagates_g25_rotor_stall_and_duct_occlusion(self) -> None:
        rep_stall = evaluate_26gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            intake_fan_kwargs={"pwm_duty_pct": 50.0, "measured_rpm": 200.0},
        )
        self.assertFalse(rep_stall.all_26_gates_verified)
        self.assertFalse(rep_stall.g25_to_g26_all_passed)
        self.assertFalse(rep_stall.gates[24]["passed"])
        self.assertEqual(rep_stall.status, STATUS_BLOCKED_FAN_TACHOMETER_ROTOR_STALL)

        rep_duct = evaluate_26gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            intake_fan_kwargs={"exhaust_clearance_mm": 1.2},
        )
        self.assertFalse(rep_duct.all_26_gates_verified)
        self.assertEqual(rep_duct.status, STATUS_BLOCKED_DUCT_OCCLUSION_BACKPRESSURE)

    def test_23_26gate_propagates_g25_off_in_rec_and_sealed_blimp(self) -> None:
        rep_off = evaluate_26gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            intake_fan_kwargs={
                "fan_mode": FAN_MODE_OFF_IN_REC,
                "workload": "XAVC_S_I_4K60_DUALSLOT",
                "clip_duration_min": 12.0,
            },
        )
        self.assertFalse(rep_off.all_26_gates_verified)
        self.assertEqual(rep_off.status, STATUS_BLOCKED_FAN_OFF_IN_REC_HIGH_LOAD)

        rep_blimp = evaluate_26gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            intake_fan_kwargs={
                "enclosure_sealed_blimp_or_raincover": True,
                "internal_enclosure_temp_c": 46.0,
            },
        )
        self.assertFalse(rep_blimp.all_26_gates_verified)
        self.assertEqual(rep_blimp.status, STATUS_BLOCKED_SEALED_BLIMP_RECIRCULATION)

    def test_24_26gate_propagates_g26_bottom_out_over_torque_and_housing_leak(self) -> None:
        rep_screw = evaluate_26gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            tripod_housing_kwargs={"effective_screw_protrusion_mm": 6.8},
        )
        self.assertFalse(rep_screw.all_26_gates_verified)
        self.assertFalse(rep_screw.gates[25]["passed"])
        self.assertEqual(rep_screw.status, STATUS_BLOCKED_TRIPOD_SCREW_BOTTOM_OUT_DAMAGE)

        rep_torque = evaluate_26gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            tripod_housing_kwargs={"applied_torque_nm": 4.2},
        )
        self.assertFalse(rep_torque.all_26_gates_verified)
        self.assertEqual(rep_torque.status, STATUS_BLOCKED_MOUNTING_OVER_TORQUE_HAZARD)

        rep_uw = evaluate_26gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            tripod_housing_kwargs={
                "underwater_housing_mode": True,
                "vacuum_pressure_drop_mbar_per_10min": 2.4,
            },
        )
        self.assertFalse(rep_uw.all_26_gates_verified)
        self.assertEqual(rep_uw.status, STATUS_BLOCKED_HOUSING_VACUUM_LEAK_OR_MOISTURE)

    def test_25_26gate_propagates_g23_g24_and_emmc_redline(self) -> None:
        rep_g23_g24 = evaluate_26gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            dewpoint_kwargs={
                "ambient_temp_c": 30.0,
                "relative_humidity_pct": 75.0,
                "cooling_method": COOLING_METHOD_EXTERNAL_PELTIER_TEC,
                "tec_cold_plate_c": 10.0,
            },
            pmic_usbc_kwargs={
                "usbc_bus_powered_device": "USBC_SSD",
                "external_powered_usbc_pd_hub": False,
            },
        )
        self.assertFalse(rep_g23_g24.all_26_gates_verified)
        self.assertFalse(rep_g23_g24.gates[22]["passed"])
        self.assertFalse(rep_g23_g24.gates[23]["passed"])
        self.assertEqual(rep_g23_g24.gates[22]["status"], STATUS_BLOCKED_SUB_DEWPOINT_TEC_CONDENSATION_HAZARD)
        self.assertEqual(rep_g23_g24.gates[23]["status"], STATUS_BLOCKED_PMIC_5V_ACCESSORY_OVERBUDGET)
        self.assertEqual(rep_g23_g24.status, STATUS_BLOCKED_SUB_DEWPOINT_TEC_CONDENSATION_HAZARD)

        rep_emmc = evaluate_26gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            request_persistent_emmc_writes=True,
        )
        self.assertFalse(rep_emmc.all_26_gates_verified)
        self.assertFalse(rep_emmc.offline_23_gates_verified)
        self.assertFalse(rep_emmc.overall_ready_for_hardware_attach)
        self.assertFalse(rep_emmc.persistent_emmc_writes_authorized)
        self.assertEqual(rep_emmc.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)

    def test_26_26gate_preserves_g01_to_g24_untouched(self) -> None:
        r24 = evaluate_24gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
        )
        r26 = evaluate_26gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
        )
        self.assertEqual(len(r24.gates), 24)
        self.assertEqual(len(r26.gates), 26)
        self.assertEqual(
            [g["gate_id"] for g in r24.gates],
            [g["gate_id"] for g in r26.gates[:24]],
        )
        self.assertEqual(
            [g["status"] for g in r24.gates],
            [g["status"] for g in r26.gates[:24]],
        )

    def test_27_serialized_json_contains_zero_raw_bytes_repr(self) -> None:
        rep = evaluate_26gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
        )
        rendered = json.dumps(rep.to_dict(), ensure_ascii=False)
        self.assertNotRegex(rendered, r'(?<![0-9A-Za-z_/.-])b[\'"]')

    def test_28_cli_verify_26_gates_offline_and_dry_run_json(self) -> None:
        buf_off = io.StringIO()
        with contextlib.redirect_stdout(buf_off):
            rc_off = package_cli_main(["verify-26-gates", "--clean-room", "--json"])
        self.assertEqual(rc_off, 0)
        p_off = json.loads(buf_off.getvalue())
        self.assertEqual(p_off["schema"], INTAKE_TRIPOD_26GATE_SCHEMA)
        self.assertEqual(p_off["summary"]["verified_gates"], 23)
        self.assertFalse(p_off["dry_run_rehearsal_only"])
        self.assertFalse(p_off["overall_ready_for_hardware_attach"])
        self.assertFalse(p_off["persistent_emmc_writes_authorized"])

        buf_dry = io.StringIO()
        with contextlib.redirect_stdout(buf_dry):
            rc_dry = package_cli_main(["verify-26-gates", "--clean-room", "--dry-run-simulated-backup", "--json"])
        self.assertEqual(rc_dry, 0)
        p_dry = json.loads(buf_dry.getvalue())
        self.assertEqual(p_dry["summary"]["verified_gates"], 26)
        self.assertTrue(p_dry["all_26_gates_verified"])
        self.assertTrue(p_dry["dry_run_rehearsal_only"])
        self.assertFalse(p_dry["overall_ready_for_hardware_attach"])
        self.assertFalse(p_dry["persistent_emmc_writes_authorized"])

    def test_29_cli_verify_26_gates_summary_and_failure_exit_code(self) -> None:
        buf_mod = io.StringIO()
        with contextlib.redirect_stdout(buf_mod):
            rc_mod = module_cli_main(["--clean-room"])
        self.assertEqual(rc_mod, 0)
        out = buf_mod.getvalue()
        self.assertIn("verified=23/26", out)
        self.assertIn("overall_ready_for_hardware_attach=False", out)
        self.assertIn("persistent_emmc_writes_authorized=False", out)

        buf_pkg = io.StringIO()
        with contextlib.redirect_stdout(buf_pkg):
            rc_pkg = package_cli_main(["verify-26-gates", "--clean-room"])
        self.assertEqual(rc_pkg, 0)
        self.assertIn("verified=23/26", buf_pkg.getvalue())

        with tempfile.TemporaryDirectory() as empty_dir:
            buf_fail = io.StringIO()
            with contextlib.redirect_stdout(buf_fail):
                rc_fail = package_cli_main(["verify-26-gates", "--repo-root", empty_dir, "--clean-room"])
            self.assertEqual(rc_fail, 1)

    def test_30_env_force_clean_room_honored_end_to_end(self) -> None:
        with patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            rep = evaluate_26gate_preflight(DEFAULT_REPO_ROOT)
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(rep.clean_room_forced)
        self.assertTrue(rep.offline_23_gates_verified)
        self.assertFalse(rep.persistent_emmc_writes_authorized)

    def test_31_evaluate_26_master_safety_gates_alias(self) -> None:
        self.assertIs(evaluate_26_master_safety_gates, evaluate_26gate_preflight)
        rep = evaluate_26_master_safety_gates(DEFAULT_REPO_ROOT, force_clean_room=True)
        self.assertEqual(rep.summary["verified_gates"], 23)

    def test_32_26gate_local_donor_mode_when_available(self) -> None:
        rep = evaluate_26gate_preflight(DEFAULT_REPO_ROOT, dry_run_simulated_backup=True)
        self.assertTrue(rep.all_26_gates_verified)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.persistent_write_release)

    def test_33_g25_donor_corruption_propagates_to_gate_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            fx3_lib = tmp / "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib"
            fx3_seed = tmp / "fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds"
            fx6_lib = tmp / "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib"
            fx6_seed = tmp / "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/tree/0110_backup/SYSIPSX-DSLR/CHAPLIN"
            for d in (fx3_lib, fx3_seed, fx6_lib, fx6_seed):
                d.mkdir(parents=True)
            (fx3_lib / "libfan.so").write_bytes(b"bad")
            (fx6_lib / "libfan.so").write_bytes(b"bad")
            (fx3_seed / "FX3-CX95900_ALLLANG-Backup.bin").write_bytes(b"bad")
            (fx6_seed / "CX95898_NTSC.bin").write_bytes(b"bad")
            v25, r25 = evaluate_g25_sigma_fan_intake_exhaust(work_root=tmp, force_clean_room=False)
            v26, r26 = evaluate_g26_tripod_torque_and_housing_vacuum(work_root=tmp, force_clean_room=False)
        self.assertFalse(v25.passed)
        self.assertFalse(r25.valid)
        self.assertEqual(v25.status, STATUS_BLOCKED_DONOR_INTEGRITY)
        self.assertFalse(v26.passed)
        self.assertFalse(r26.valid)
        self.assertEqual(v26.status, STATUS_BLOCKED_DONOR_INTEGRITY)

    def test_34_previous_cli_subcommands_verify_16_to_24_still_work(self) -> None:
        for subcmd in ("verify-16-gates", "verify-18-gates", "verify-20-gates", "verify-22-gates", "verify-24-gates"):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = package_cli_main([subcmd, "--clean-room", "--json"])
            self.assertEqual(rc, 0, f"{subcmd} failed with rc={rc}")
            payload = json.loads(buf.getvalue())
            self.assertFalse(payload["persistent_emmc_writes_authorized"])


if __name__ == "__main__":
    unittest.main()
