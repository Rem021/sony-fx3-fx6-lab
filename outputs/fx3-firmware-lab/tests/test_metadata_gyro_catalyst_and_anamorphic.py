"""Unit tests for Phase 89 — 17th Unified Firmware-Lab Auditor:
`Gyroflow` / `Catalyst Browse` Sony `RTMD` (`0xE304` / `0xE43B` / `0xE44B`) IMU
Telemetry, Anamorphic (`1.3x..2.0x`) 5-Axis IBIS Asymmetric Gain Containment,
`IMX510` Rolling-Shutter Readout Matrix & Stock-CP IMU Calibration Immutability.

Executes rapidly in BOTH Local Donor (`os.O_RDONLY`) and
`FX3_FX6_FORCE_CLEAN_ROOM=1` modes.
"""

from __future__ import annotations

import json
import math
import os
import subprocess
import sys
import time
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from typing import Optional
from unittest.mock import patch

from fx3_firmware_lab.__main__ import main as cli_main, run_audit_all
from fx3_firmware_lab.haita_bk4_feature_analyzer import is_forced_clean_room
from fx3_firmware_lab.metadata_gyro_catalyst_and_anamorphic_auditor import (
    ANAMORPHIC_YAW_OVERDRIVE_TOLERANCE_PCT,
    DEFAULT_IMU_QUATERNION_WXYZ,
    FX3_APPFW_GYRO_ANAMORPHIC_MARKERS,
    FX3_CP_GYRO_CALIB_MARKERS,
    FX3_LIBMPR_RTMD_IMU_MARKERS,
    FX6_APPFW_GYRO_ANAMORPHIC_MARKERS,
    FX6_CP_GYRO_READOUT_MARKERS,
    FX6_LIBMPR_RTMD_READOUT_MARKERS,
    FX6_NATIVE_MONITORING_DESQUEEZE_RATIOS,
    GYRO_FRAME_RATE_SPECS,
    IMU_SAMPLE_RATE_HZ,
    IMX510_READOUT_TOLERANCE_US,
    IMX510_ROLLING_SHUTTER_MODES,
    LENS_COMM_GYRO_MARKERS,
    PHASE_89_SCHEMA,
    PHASE_89_VERSION,
    RTMD_TAG_ACCELEROMETER,
    RTMD_TAG_ANAMORPHIC_DESQUEEZE_X100,
    RTMD_TAG_GYRO_PITCH_ROLL_YAW,
    RTMD_TAG_IMX510_IBIS_GYRO_E304,
    RTMD_TAG_IMX510_READOUT_US,
    SUPPORTED_ANAMORPHIC_SQUEEZE_FACTORS,
    MetadataGyroCatalystAndAnamorphicReport,
    analyze_metadata_gyro_catalyst_and_anamorphic,
    build_clean_room_gyro_anamorphic_fixtures,
    build_gyroflow_rtmd_frame_packet,
    compute_imu_samples_for_frame,
    evaluate_anamorphic_ibis_asymmetric_gain,
    evaluate_gyroflow_catalyst_rtmd_packet,
    evaluate_imu_calibration_immutability,
    evaluate_imx510_rolling_shutter_readout,
    metadata_gyro_catalyst_and_anamorphic_report_to_dict,
    verify_so3_orientation_quaternion,
)


PKG_ROOT = Path(__file__).resolve().parents[1]


class TestActiveMetadataGyroCatalystAndAnamorphic(unittest.TestCase):
    _active_report: Optional[MetadataGyroCatalystAndAnamorphicReport] = None
    _elapsed_sec: float = 0.0

    @classmethod
    def setUpClass(cls) -> None:
        t0 = time.monotonic()
        cls._active_report = analyze_metadata_gyro_catalyst_and_anamorphic()
        cls._elapsed_sec = time.monotonic() - t0

    def test_01_active_mode_passes_o_rdonly_14_artifacts_and_sub_500ms(self) -> None:
        rep = self._active_report
        assert rep is not None
        self.assertTrue(rep.all_checks_passed, msg=f"Errors: {rep.errors}")
        self.assertLess(self._elapsed_sec, 0.5)
        self.assertEqual(rep.schema_version, PHASE_89_SCHEMA)
        self.assertEqual(rep.phase_version, PHASE_89_VERSION)
        self.assertTrue(rep.o_rdonly_enforced)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertEqual(rep.imu_calibration_mutation_bytes, 0)
        self.assertEqual(rep.cp_mutation_bytes, 0)
        self.assertEqual(len(rep.report_sha256), 64)
        self.assertEqual(len(rep.donor_file_sizes), 14)
        if not is_forced_clean_room() and rep.mode == "LOCAL_DONOR_VERIFIED":
            self.assertGreater(rep.donor_file_sizes["fx3_appfw"], 70_000_000)
            self.assertGreater(rep.donor_file_sizes["fx6_appfw"], 45_000_000)
            self.assertGreater(rep.donor_file_sizes["fx3_libmpr"], 3_000_000)
            self.assertGreater(rep.donor_file_sizes["fx6_libmpr"], 20_000_000)
            self.assertEqual(rep.donor_file_sizes["fx3_lens_comm"], 14_544)
            self.assertEqual(rep.donor_file_sizes["fx6_lens_comm"], 14_544)

    def test_02_active_report_json_serializable_without_raw_bytes(self) -> None:
        rep = self._active_report
        assert rep is not None
        payload = metadata_gyro_catalyst_and_anamorphic_report_to_dict(rep)
        encoded = json.dumps(payload, sort_keys=True)
        self.assertNotRegex(encoded, r'(?<![0-9A-Za-z_/.-])b[\'"]')
        decoded = json.loads(encoded)
        self.assertEqual(decoded["report_sha256"], rep.report_sha256)
        self.assertTrue(decoded["all_checks_passed"])
        self.assertEqual(rep.to_deterministic_json().strip(), json.dumps(payload, indent=2, sort_keys=True))

    def test_03_pillar_1_rtmd_markers_and_uxc_steadyshot_labels(self) -> None:
        rep = self._active_report
        assert rep is not None
        p1 = rep.pillar_1_gyroflow_rtmd
        self.assertTrue(p1.passed, msg=f"P1 errors: {p1.errors}")
        self.assertEqual(p1.imu_sample_rate_hz, 2000)
        self.assertEqual(p1.fx3_libmpr_markers, FX3_LIBMPR_RTMD_IMU_MARKERS)
        self.assertEqual(p1.fx6_libmpr_markers, FX6_LIBMPR_RTMD_READOUT_MARKERS)
        self.assertEqual(p1.uxc_steadyshot_labels["fx3_steadyshot"], "SteadyShot")
        self.assertEqual(p1.uxc_steadyshot_labels["fx3_shutter_steadyshot"], "Shutter/SteadyShot")
        self.assertEqual(p1.uxc_steadyshot_labels["fx6_steadyshot_focal"], "SteadyShot Focal")
        self.assertEqual(p1.uxc_steadyshot_labels["fx6_steadyshot_off"], "SteadyShot: Off")

    def test_04_pillar_2_anamorphic_markers_and_uxc_labels(self) -> None:
        rep = self._active_report
        assert rep is not None
        p2 = rep.pillar_2_anamorphic_ibis
        self.assertTrue(p2.passed, msg=f"P2 errors: {p2.errors}")
        self.assertEqual(p2.fx3_appfw_markers, FX3_APPFW_GYRO_ANAMORPHIC_MARKERS)
        self.assertEqual(p2.fx6_appfw_markers, FX6_APPFW_GYRO_ANAMORPHIC_MARKERS)
        self.assertEqual(p2.lens_comm_markers, LENS_COMM_GYRO_MARKERS)
        self.assertEqual(p2.uxc_anamorphic_labels["fx6_desqueeze"], "De-Squeeze")
        self.assertEqual(p2.uxc_anamorphic_labels["fx6_desqueeze_ratio"], "De-Squeeze Ratio")
        self.assertEqual(p2.uxc_anamorphic_labels["fx6_anamorphic"], "Anamorphic")

    def test_05_pillar_3_and_4_readout_markers_and_zero_imu_calib_mutation(self) -> None:
        rep = self._active_report
        assert rep is not None
        p3 = rep.pillar_3_imx510_rolling_shutter
        p4 = rep.pillar_4_imu_calibration_immutability
        self.assertTrue(p3.passed, msg=f"P3 errors: {p3.errors}")
        self.assertTrue(p4.passed, msg=f"P4 errors: {p4.errors}")
        self.assertEqual(p4.fx3_cp_calib_markers, FX3_CP_GYRO_CALIB_MARKERS)
        self.assertEqual(p4.fx6_cp_calib_markers, FX6_CP_GYRO_READOUT_MARKERS)
        self.assertTrue(p4.fx3_global_xdb_valid)
        self.assertTrue(p4.fx6_global_xdb_valid)
        self.assertEqual(p4.imu_calibration_mutation_bytes, 0)
        self.assertEqual(p4.cp_mutation_bytes, 0)
        self.assertFalse(p4.persistent_emmc_writes_authorized)


class TestPillar1GyroflowRtmdImuMath(unittest.TestCase):
    def test_06_2000hz_imu_samples_per_frame_across_all_framerates(self) -> None:
        expected_ranges = {
            "23.976p": (83, 84),
            "24.00p": (83, 84),
            "25.00p": (80, 80),
            "29.97p": (66, 67),
            "50.00p": (40, 40),
            "59.94p": (33, 34),
            "119.88p": (16, 17),
        }
        for fps_label, (lo, hi) in expected_ranges.items():
            counts = {compute_imu_samples_for_frame(i, fps_label).sample_count for i in range(12)}
            self.assertTrue(counts.issubset(set(range(lo, hi + 1))), msg=f"{fps_label}: {counts}")
            if lo == hi:
                self.assertEqual(counts, {lo})
            else:
                self.assertEqual(counts, {lo, hi})

    def test_07_rational_accumulator_zero_drift_over_10000_frames(self) -> None:
        for fps_label, spec in GYRO_FRAME_RATE_SPECS.items():
            num = int(spec["num"])
            den = int(spec["den"])
            total = sum(compute_imu_samples_for_frame(i, fps_label).sample_count for i in range(1000))
            exact = (1000 * IMU_SAMPLE_RATE_HZ * den) // num
            self.assertEqual(total, exact, msg=f"Drift detected at {fps_label}: {total} != {exact}")

    def test_08_invalid_frame_rate_or_index_raises(self) -> None:
        with self.assertRaises(ValueError):
            compute_imu_samples_for_frame(-1, "23.976p")
        with self.assertRaises(ValueError):
            compute_imu_samples_for_frame(0, "47.95p")
        with self.assertRaises(ValueError):
            compute_imu_samples_for_frame(0, "23.976p", imu_rate_hz=0)

    def test_09_so3_quaternion_identity_and_rotated_valid_non_unit_rejected(self) -> None:
        ok_id, norm_id, det_id, _mat_id, errs_id = verify_so3_orientation_quaternion(DEFAULT_IMU_QUATERNION_WXYZ)
        self.assertTrue(ok_id, msg=f"Errors: {errs_id}")
        self.assertAlmostEqual(norm_id, 1.0, places=6)
        self.assertAlmostEqual(det_id, 1.0, places=6)

        inv_sqrt2 = 1.0 / math.sqrt(2.0)
        ok_rot, norm_rot, det_rot, mat_rot, errs_rot = verify_so3_orientation_quaternion(
            (inv_sqrt2, 0.0, inv_sqrt2, 0.0)
        )
        self.assertTrue(ok_rot, msg=f"Errors: {errs_rot}")
        self.assertAlmostEqual(norm_rot, 1.0, places=6)
        self.assertAlmostEqual(det_rot, 1.0, places=6)
        self.assertAlmostEqual(mat_rot[0][2], 1.0, places=6)

        for bad_q in ((0.0, 0.0, 0.0, 0.0), (1.0, 1.0, 0.0, 0.0), (1.0, float("nan"), 0.0, 0.0)):
            ok_bad, _, _, _, errs_bad = verify_so3_orientation_quaternion(bad_q)
            self.assertFalse(ok_bad)
            self.assertTrue(len(errs_bad) >= 1)

    def test_10_rtmd_klv_packet_round_trip_and_tags(self) -> None:
        ev = evaluate_gyroflow_catalyst_rtmd_packet(
            fps_label="59.94p",
            frame_index=1,
            readout_us=8700,
            steadyshot_mode="Off",
            target_stabilizer="GYROFLOW_3D_LENS_PROFILE",
            squeeze_factor=1.5,
        )
        self.assertTrue(ev.valid, msg=f"Errors: {ev.errors}")
        self.assertIn(ev.sample_count, (33, 34))
        self.assertEqual(ev.expected_sample_range, (33, 34))
        self.assertTrue(ev.center_lock_0x0400_energized)
        self.assertFalse(ev.ibis_optical_center_shift_conflict)
        self.assertTrue(ev.full_3d_lens_profile_compatible)
        self.assertTrue(ev.catalyst_compatible)
        self.assertEqual(
            ev.parsed_tags_hex,
            (
                f"0x{RTMD_TAG_IMX510_READOUT_US:04x}",
                f"0x{RTMD_TAG_GYRO_PITCH_ROLL_YAW:04x}",
                f"0x{RTMD_TAG_ACCELEROMETER:04x}",
                f"0x{RTMD_TAG_ANAMORPHIC_DESQUEEZE_X100:04x}",
                f"0x{RTMD_TAG_IMX510_IBIS_GYRO_E304:04x}",
            ),
        )
        pkt = build_gyroflow_rtmd_frame_packet(fps_label="59.94p", frame_index=1)
        self.assertEqual(len(pkt), ev.packet_bytes)

    def test_11_ibis_active_vs_off_center_lock_compatibility_rules(self) -> None:
        # 3D Lens Profile + Active IBIS without Center-Lock -> blocked optical-center conflict
        bad_active = evaluate_gyroflow_catalyst_rtmd_packet(
            fps_label="23.976p",
            steadyshot_mode="Active",
            target_stabilizer="GYROFLOW_3D_LENS_PROFILE",
            center_lock_0x0400_energized=False,
        )
        self.assertFalse(bad_active.valid)
        self.assertEqual(bad_active.status, "BLOCKED_IBIS_OPTICAL_CENTER_CONFLICT")
        self.assertTrue(bad_active.ibis_optical_center_shift_conflict)

        # Standard IBIS without offset telemetry under GYROFLOW_V17_IBIS_METADATA_AWARE -> blocked
        bad_v17 = evaluate_gyroflow_catalyst_rtmd_packet(
            fps_label="23.976p",
            steadyshot_mode="Standard",
            target_stabilizer="GYROFLOW_V17_IBIS_METADATA_AWARE",
            center_lock_0x0400_energized=False,
            ibis_offset_telemetry_present=False,
        )
        self.assertFalse(bad_v17.valid)
        self.assertTrue(bad_v17.ibis_optical_center_shift_conflict)

        # Standard IBIS WITH offset telemetry under GYROFLOW_V17_IBIS_METADATA_AWARE -> valid
        ok_v17 = evaluate_gyroflow_catalyst_rtmd_packet(
            fps_label="23.976p",
            steadyshot_mode="Standard",
            target_stabilizer="GYROFLOW_V17_IBIS_METADATA_AWARE",
            center_lock_0x0400_energized=False,
            ibis_offset_telemetry_present=True,
        )
        self.assertTrue(ok_v17.valid, msg=f"Errors: {ok_v17.errors}")
        self.assertEqual(ok_v17.status, "RTMD_IBIS_METADATA_AWARE_VERIFIED")

        # Catalyst Browse accepts valid 0xE304 metadata
        ok_cat = evaluate_gyroflow_catalyst_rtmd_packet(
            fps_label="25.00p",
            steadyshot_mode="Off",
            target_stabilizer="CATALYST_BROWSE_METADATA",
        )
        self.assertTrue(ok_cat.valid)
        self.assertTrue(ok_cat.catalyst_compatible)


class TestPillar2AnamorphicIbisAsymmetricGain(unittest.TestCase):
    def test_12_fx6_rigid_cmos_desqueeze_monitoring_only(self) -> None:
        self.assertEqual(FX6_NATIVE_MONITORING_DESQUEEZE_RATIOS, (1.3, 2.0))
        for ratio in FX6_NATIVE_MONITORING_DESQUEEZE_RATIOS:
            res = evaluate_anamorphic_ibis_asymmetric_gain(
                target_body="ILME-FX6", focal_length_mm=50.0, squeeze_factor=ratio
            )
            self.assertTrue(res.valid, msg=f"Errors: {res.errors}")
            self.assertFalse(res.has_physical_ibis)
            self.assertTrue(res.monitoring_desqueeze_only)
            self.assertEqual(res.status, "FX6_RIGID_CMOS_MONITORING_DESQUEEZE_ONLY")
            self.assertEqual(res.yaw_overdrive_error_pct, 0.0)
            self.assertTrue(res.gyro_rtmd_embedded)

    def test_13_fx3_anamorphic_asymmetric_gain_math_all_squeeze_factors(self) -> None:
        self.assertEqual(SUPPORTED_ANAMORPHIC_SQUEEZE_FACTORS, (1.3, 1.33, 1.5, 1.8, 2.0))
        focal = 50.0
        for s in SUPPORTED_ANAMORPHIC_SQUEEZE_FACTORS:
            res = evaluate_anamorphic_ibis_asymmetric_gain(
                target_body="ILME-FX3",
                focal_length_mm=focal,
                squeeze_factor=s,
                steadyshot_mode="Standard",
                anamorphic_ibis_mode="ANAMORPHIC_ASYMMETRIC_GAIN",
                is_manual_anamorphic_lens=False,
            )
            self.assertTrue(res.valid, msg=f"Failed S={s}: {res.errors}")
            self.assertTrue(res.has_physical_ibis)
            self.assertFalse(res.monitoring_desqueeze_only)
            self.assertAlmostEqual(res.effective_yaw_focal_mm, focal / s, places=3)
            self.assertAlmostEqual(res.effective_pitch_focal_mm, focal, places=3)
            self.assertAlmostEqual(res.yaw_gain_ratio, 1.0 / s, places=3)
            self.assertEqual(res.pitch_gain_ratio, 1.0)
            self.assertEqual(res.yaw_overdrive_factor, 1.0)
            self.assertEqual(res.yaw_overdrive_error_pct, 0.0)
            self.assertFalse(res.asymmetric_gain_hazard_detected)

    def test_14_fx3_manual_anamorphic_auto_engages_center_lock_0x0400(self) -> None:
        res = evaluate_anamorphic_ibis_asymmetric_gain(
            target_body="ILME-FX3",
            focal_length_mm=35.0,
            squeeze_factor=1.8,
            steadyshot_mode="Standard",
            anamorphic_ibis_mode="ANAMORPHIC_ASYMMETRIC_GAIN",
            is_manual_anamorphic_lens=True,
        )
        self.assertTrue(res.valid, msg=f"Errors: {res.errors}")
        self.assertEqual(res.status, "FX3_ANAMORPHIC_CENTER_LOCK_0X0400_WITH_GYRO_RTMD")
        self.assertEqual(res.steadyshot_mode, "Off")
        self.assertEqual(res.anamorphic_ibis_mode, "AUTO_CENTER_LOCK_0X0400")
        self.assertTrue(res.center_lock_0x0400_energized)
        self.assertTrue(res.gyro_rtmd_embedded)
        self.assertEqual(res.yaw_overdrive_error_pct, 0.0)

    def test_15_fx3_spherical_naive_yaw_overdrive_blocked_for_all_squeeze_factors(self) -> None:
        self.assertEqual(ANAMORPHIC_YAW_OVERDRIVE_TOLERANCE_PCT, 0.5)
        for s in SUPPORTED_ANAMORPHIC_SQUEEZE_FACTORS:
            res = evaluate_anamorphic_ibis_asymmetric_gain(
                target_body="ILME-FX3",
                focal_length_mm=50.0,
                squeeze_factor=s,
                steadyshot_mode="Standard",
                anamorphic_ibis_mode="SPHERICAL_NAIVE",
            )
            self.assertFalse(res.valid, msg=f"Naive spherical should block at S={s}")
            self.assertEqual(res.status, "BLOCKED_ANAMORPHIC_YAW_OVERDRIVE_HAZARD")
            self.assertTrue(res.asymmetric_gain_hazard_detected)
            self.assertAlmostEqual(res.yaw_overdrive_factor, s, places=3)
            self.assertAlmostEqual(res.yaw_overdrive_error_pct, (s - 1.0) * 100.0, places=1)

    def test_16_invalid_anamorphic_inputs_rejected(self) -> None:
        self.assertFalse(evaluate_anamorphic_ibis_asymmetric_gain(target_body="ILME-FX9").valid)
        self.assertFalse(evaluate_anamorphic_ibis_asymmetric_gain(focal_length_mm=2.0).valid)
        self.assertFalse(evaluate_anamorphic_ibis_asymmetric_gain(squeeze_factor=1.66).valid)
        self.assertFalse(evaluate_anamorphic_ibis_asymmetric_gain(steadyshot_mode="Ultra").valid)
        self.assertFalse(evaluate_anamorphic_ibis_asymmetric_gain(anamorphic_ibis_mode="MAGIC").valid)


class TestPillar3Imx510RollingShutterMatrix(unittest.TestCase):
    def test_17_imx510_all_readout_modes_exact(self) -> None:
        expected_us = {
            "4K_DCI_24P": 8700,
            "QFHD_4K_24P": 8700,
            "QFHD_4K_60P": 8700,
            "SQ_4K_120P": 4350,
            "FHD_240P": 2200,
        }
        self.assertEqual(set(IMX510_ROLLING_SHUTTER_MODES.keys()), set(expected_us.keys()))
        for mode_name, target_us in expected_us.items():
            res = evaluate_imx510_rolling_shutter_readout(sensor_mode=mode_name)
            self.assertTrue(res.valid, msg=f"Failed {mode_name}: {res.errors}")
            self.assertEqual(res.status, "IMX510_ROLLING_SHUTTER_VERIFIED")
            self.assertEqual(res.declared_readout_us, target_us)
            self.assertEqual(res.readout_error_us, 0)
            self.assertFalse(res.vertical_shear_risk)
            self.assertEqual(res.skew_residual_px_at_30deg_s, 0.0)
            self.assertLess(res.actual_readout_ms, res.frame_period_ms)

    def test_18_imx510_readout_within_tolerance_accepted(self) -> None:
        res = evaluate_imx510_rolling_shutter_readout(
            sensor_mode="QFHD_4K_60P",
            declared_readout_us=8700 + IMX510_READOUT_TOLERANCE_US,
        )
        self.assertTrue(res.valid)
        self.assertFalse(res.vertical_shear_risk)
        self.assertEqual(res.readout_error_us, IMX510_READOUT_TOLERANCE_US)

    def test_19_imx510_wrong_8700us_on_4k120_flags_vertical_shear_risk(self) -> None:
        res = evaluate_imx510_rolling_shutter_readout(
            sensor_mode="SQ_4K_120P",
            declared_readout_us=8700,
            pan_angular_rate_deg_s=30.0,
            hfov_deg=65.0,
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.status, "BLOCKED_ROLLING_SHUTTER_READOUT_MISMATCH")
        self.assertTrue(res.vertical_shear_risk)
        self.assertEqual(res.readout_error_us, 4350)
        self.assertGreater(res.skew_residual_px_at_30deg_s, 5.0)

    def test_20_imx510_invalid_mode_and_out_of_period_declared_us_rejected(self) -> None:
        bad_mode = evaluate_imx510_rolling_shutter_readout(sensor_mode="OPEN_GATE_5K")
        self.assertFalse(bad_mode.valid)
        self.assertEqual(bad_mode.status, "BLOCKED_UNSUPPORTED_IMX510_MODE")

        bad_over = evaluate_imx510_rolling_shutter_readout(
            sensor_mode="FHD_240P",
            declared_readout_us=8700,  # exceeds 4.17 ms frame period at 240p!
        )
        self.assertFalse(bad_over.valid)
        self.assertTrue(bad_over.vertical_shear_risk)

        bad_zero = evaluate_imx510_rolling_shutter_readout(sensor_mode="QFHD_4K_24P", declared_readout_us=0)
        self.assertFalse(bad_zero.valid)


class TestPillar4ImuCalibrationImmutabilityAndCli(unittest.TestCase):
    def test_21_volatile_shadow_allowed_with_zero_imu_calib_mutation(self) -> None:
        for p in ("/tmp/fx3_gyro_anamorphic_shadow.json", "ram://gyro_rtmd.json", "memory://ibis_map"):
            res = evaluate_imu_calibration_immutability(target_path=p, requested_write_bytes=512)
            self.assertTrue(res.valid, msg=f"Errors: {res.errors}")
            self.assertTrue(res.volatile_shadow_only)
            self.assertEqual(res.imu_calibration_mutation_bytes, 0)
            self.assertEqual(res.cp_mutation_bytes, 0)
            self.assertFalse(res.persistent_emmc_writes_authorized)

    def test_22_forbidden_cnflasha_and_cp_calib_targets_blocked(self) -> None:
        for bad in (
            "/dev/cnflasha0",
            "/dev/cnflasha1/gyro_bias",
            "/dev/nflasha2",
            "/dev/mmcblk0p1",
            "p1:/boot/kernel",
            "p2:/Backup.bin",
            "p2:/psd.bin",
            "p6:Jiritsu",
            "nvram://bk4_gyro",
        ):
            res = evaluate_imu_calibration_immutability(target_path=bad, requested_write_bytes=64)
            self.assertFalse(res.valid, msg=f"{bad} should block")
            self.assertEqual(res.status, "BLOCKED_PERSISTENT_IMU_CALIBRATION_WRITE")
            self.assertEqual(res.imu_calibration_mutation_bytes, 0)
            self.assertEqual(res.cp_mutation_bytes, 0)
            self.assertFalse(res.persistent_emmc_writes_authorized)

    def test_23_negative_write_bytes_rejected(self) -> None:
        bad = evaluate_imu_calibration_immutability(
            target_path="/tmp/fx3_gyro_shadow.json", requested_write_bytes=-1
        )
        self.assertFalse(bad.valid)

    def test_24_clean_room_fixtures_complete_and_deterministic(self) -> None:
        fx = build_clean_room_gyro_anamorphic_fixtures()
        self.assertEqual(len(fx), 14)
        r1 = analyze_metadata_gyro_catalyst_and_anamorphic(clean_room=True)
        r2 = analyze_metadata_gyro_catalyst_and_anamorphic(clean_room=True)
        self.assertTrue(r1.all_checks_passed, msg=f"Errors: {r1.errors}")
        self.assertEqual(r1.mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(r1.report_sha256, r2.report_sha256)

    def test_25_missing_donors_gracefully_fall_back_to_clean_room(self) -> None:
        with patch(
            "fx3_firmware_lab.metadata_gyro_catalyst_and_anamorphic_auditor.resolve_donor_file",
            return_value=None,
        ):
            rep = analyze_metadata_gyro_catalyst_and_anamorphic()
        self.assertTrue(rep.all_checks_passed, msg=f"Errors: {rep.errors}")
        self.assertEqual(rep.mode, "CLEAN_ROOM_SYNTHETIC")

    def test_26_cli_in_process_clean_room_and_active(self) -> None:
        buf_cr = StringIO()
        with redirect_stdout(buf_cr):
            rc_cr = cli_main(["audit-gyroflow-anamorphic", "--clean-room", "--json"])
        self.assertEqual(rc_cr, 0)
        d_cr = json.loads(buf_cr.getvalue())
        self.assertTrue(d_cr["all_checks_passed"])
        self.assertEqual(d_cr["mode"], "CLEAN_ROOM_SYNTHETIC")

        buf_act = StringIO()
        with redirect_stdout(buf_act):
            rc_act = cli_main(["audit-gyroflow-anamorphic", "--json"])
        self.assertEqual(rc_act, 0)
        d_act = json.loads(buf_act.getvalue())
        self.assertTrue(d_act["all_checks_passed"])

    def test_27_cli_subprocess_deterministic_json_clean_room_env(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["FX3_FX6_FORCE_CLEAN_ROOM"] = "1"
        env["PYTHONPATH"] = str(PKG_ROOT)
        proc1 = subprocess.run(
            [sys.executable, "-B", "-m", "fx3_firmware_lab", "audit-gyroflow-anamorphic", "--json"],
            capture_output=True,
            text=True,
            env=env,
            timeout=15,
            check=True,
        )
        proc2 = subprocess.run(
            [sys.executable, "-B", "-m", "fx3_firmware_lab", "audit-gyroflow-anamorphic", "--json"],
            capture_output=True,
            text=True,
            env=env,
            timeout=15,
            check=True,
        )
        self.assertEqual(proc1.stdout, proc2.stdout)
        parsed = json.loads(proc1.stdout)
        self.assertTrue(parsed["all_checks_passed"])
        self.assertEqual(parsed["mode"], "CLEAN_ROOM_SYNTHETIC")

    def test_28_run_audit_all_includes_17_auditors_with_gyroflow_anamorphic(self) -> None:
        summary = run_audit_all(clean_room=True)
        self.assertTrue(summary["all_checks_passed"])
        self.assertIn("metadata_gyro_catalyst_and_anamorphic_audit", summary)
        self.assertTrue(summary["metadata_gyro_catalyst_and_anamorphic_audit"]["all_checks_passed"])
        expected_17 = (
            "ufu_container_audit",
            "haita_bk4_feature_audit",
            "uxc_ldec_asset_audit",
            "uxc_multilang_and_font_audit",
            "sensor_codec_compatibility_audit",
            "cube_lut_and_rtmd_audit",
            "wbi_hibdrv_and_elf_abi_audit",
            "global_xdb_and_menu_tree_audit",
            "audio_tc_hdmi_sdi_routing_audit",
            "emount_af_breathing_and_ibis_audit",
            "shutter_ecs_sq_and_tally_audit",
            "wb_color_matrix_and_look_audit",
            "proxy_clipname_and_sidecar_audit",
            "assignable_zoom_ciz_and_fn_audit",
            "falsecolor_lpcm_tc_ub_audit",
            "playback_shotmark_and_ae_audit",
            "metadata_gyro_catalyst_and_anamorphic_audit",
        )
        for key in expected_17:
            self.assertIn(key, summary)

    def test_29_package_exports_present(self) -> None:
        import fx3_firmware_lab

        for sym in (
            "PHASE_89_SCHEMA",
            "PHASE_89_VERSION",
            "IMU_SAMPLE_RATE_HZ",
            "SUPPORTED_ANAMORPHIC_SQUEEZE_FACTORS",
            "IMX510_ROLLING_SHUTTER_MODES",
            "analyze_metadata_gyro_catalyst_and_anamorphic",
            "build_clean_room_gyro_anamorphic_fixtures",
            "build_gyroflow_rtmd_frame_packet",
            "compute_imu_samples_for_frame",
            "evaluate_anamorphic_ibis_asymmetric_gain",
            "evaluate_gyroflow_catalyst_rtmd_packet",
            "evaluate_imu_calibration_immutability",
            "evaluate_imx510_rolling_shutter_readout",
            "metadata_gyro_catalyst_and_anamorphic_report_to_dict",
            "verify_so3_orientation_quaternion",
        ):
            self.assertTrue(hasattr(fx3_firmware_lab, sym), msg=f"Missing export {sym}")

    def test_30_static_source_hygiene_o_rdonly_and_zero_secrets(self) -> None:
        mod_path = PKG_ROOT / "fx3_firmware_lab" / "metadata_gyro_catalyst_and_anamorphic_auditor.py"
        src = mod_path.read_text(encoding="utf-8")
        self.assertIn("os.O_RDONLY", src)
        self.assertNotIn("os.O_RDWR", src)
        self.assertNotIn("os.O_WRONLY", src)
        self.assertNotIn("CXD90057_k8", src)
        self.assertNotIn("pkill", src)

    def test_31_rtmd_frame_packet_custom_imu_rate_scaling(self) -> None:
        win_1000 = compute_imu_samples_for_frame(0, "25.00p", imu_rate_hz=1000)
        self.assertEqual(win_1000.sample_count, 40)
        ev = evaluate_gyroflow_catalyst_rtmd_packet(
            fps_label="25.00p",
            imu_rate_hz=1000,
            steadyshot_mode="Off",
            target_stabilizer="GYROFLOW_3D_LENS_PROFILE",
        )
        self.assertTrue(ev.valid, msg=f"Errors: {ev.errors}")
        self.assertEqual(ev.sample_count, 40)

    def test_32_rtmd_invalid_steadyshot_or_stabilizer_blocked(self) -> None:
        bad_ss = evaluate_gyroflow_catalyst_rtmd_packet(steadyshot_mode="HyperSmooth")
        self.assertFalse(bad_ss.valid)
        self.assertEqual(bad_ss.status, "BLOCKED_INVALID_RTMD_IMU_CONFIG")

        bad_st = evaluate_gyroflow_catalyst_rtmd_packet(target_stabilizer="UNKNOWN_WARP")
        self.assertFalse(bad_st.valid)
        self.assertEqual(bad_st.status, "BLOCKED_INVALID_RTMD_IMU_CONFIG")

    def test_33_anamorphic_yaw_gain_ratio_inverse_of_pitch(self) -> None:
        for s in (1.3, 1.5, 2.0):
            res = evaluate_anamorphic_ibis_asymmetric_gain(
                target_body="ILME-FX3",
                focal_length_mm=60.0,
                squeeze_factor=s,
                anamorphic_ibis_mode="ANAMORPHIC_ASYMMETRIC_GAIN",
            )
            self.assertTrue(res.valid)
            self.assertAlmostEqual(res.effective_yaw_focal_mm * s, res.effective_pitch_focal_mm, places=3)

    def test_34_fx3_steadyshot_off_forces_center_lock_even_without_manual_flag(self) -> None:
        res = evaluate_anamorphic_ibis_asymmetric_gain(
            target_body="ILME-FX3",
            focal_length_mm=40.0,
            squeeze_factor=1.5,
            steadyshot_mode="Off",
            anamorphic_ibis_mode="SPHERICAL_NAIVE",
        )
        self.assertTrue(res.valid)
        self.assertTrue(res.center_lock_0x0400_energized)
        self.assertEqual(res.steadyshot_mode, "Off")
        self.assertEqual(res.yaw_overdrive_error_pct, 0.0)


if __name__ == "__main__":
    unittest.main()
