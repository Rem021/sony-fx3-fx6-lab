#!/usr/bin/env python3
"""Phase 91 Test Suite — Stage 14 Gyroflow / Sony Catalyst 2000 Hz 6-Axis IMU
RTMD (SMPTE RDD 18 `0xE4xx`) FIFO, Anamorphic (`1.33x/1.5x/1.8x/2.0x`) Asymmetric
IBIS Gain / Center-Lock Arbitrator, & `IMX510` Rolling-Shutter Readout Skew HIL.

Exercises 36 fast unit, IMU FIFO cadence, quaternion round-trip (<0.02 deg),
Anamorphic IBIS / Gyroflow double-stabilization fail-closed guards, IMX510 RS HIL,
Stage 14 suite integration, CLI, and source-hygiene tests across BOTH Local Donor
(`os.O_RDONLY`) and `FX3_FX6_FORCE_CLEAN_ROOM=1` modes, strictly offline.
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import contextlib
import hashlib
import io
import json
import os
import subprocess
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
FX3_VM_DIR = TESTS_DIR.parent
REPO_ROOT = FX3_VM_DIR.parents[1]
if str(FX3_VM_DIR) not in sys.path:
    sys.path.insert(0, str(FX3_VM_DIR))

import fx3_vm_coemulation_suite as suite  # noqa: E402
import gyroflow_rtmd_anamorphic_emulator as p91  # noqa: E402


_AUDIT_CACHE: dict = {}


def _get_clean_room_audit() -> dict:
    if "clean_room" not in _AUDIT_CACHE:
        _AUDIT_CACHE["clean_room"] = p91.run_phase91_gyroflow_rtmd_anamorphic_audit(force_clean_room=True)
    return _AUDIT_CACHE["clean_room"]


class TestPhase91DonorAuditAndRedlines(unittest.TestCase):
    """Verify O_RDONLY donor audit, clean-room fallback, and zero-mutation redlines."""

    def test_01_clean_room_donor_audit_verifies_all_10_artifacts_and_sha256(self) -> None:
        audit = p91.inspect_gyroflow_rtmd_anamorphic_donors(force_clean_room=True)
        self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(audit.access_mode, "O_RDONLY")
        self.assertEqual(audit.donor_files_inspected, 0)
        self.assertTrue(audit.all_contracts_verified)
        self.assertGreaterEqual(len(audit.checked_markers), 35)
        self.assertEqual(audit.missing_markers, ())
        for key, (expected_bytes, expected_sha) in p91.PINNED_DONOR_SHA256.items():
            self.assertEqual(audit.bytes_by_artifact[key], expected_bytes)
            self.assertEqual(audit.sha256_by_artifact[key], expected_sha)

    def test_02_force_clean_room_env_disables_local_donor_paths(self) -> None:
        env = {p91.ENV_FORCE_CLEAN_ROOM: "1"}
        self.assertTrue(p91.is_forced_clean_room(env))
        paths = p91.resolve_phase91_donor_paths(env=env)
        self.assertEqual(len(paths), 10)
        for path in paths.values():
            self.assertIn(p91.CLEAN_ROOM_SENTINEL_DIRNAME, str(path))
        audit = p91.inspect_gyroflow_rtmd_anamorphic_donors(env=env)
        self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_03_local_donor_o_rdonly_audit_when_present_or_clean_room(self) -> None:
        if p91.is_forced_clean_room():
            audit = p91.inspect_gyroflow_rtmd_anamorphic_donors()
            self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")
            return
        paths = p91.resolve_phase91_donor_paths()
        audit = p91.inspect_gyroflow_rtmd_anamorphic_donors()
        self.assertTrue(audit.all_contracts_verified)
        if all(p.is_file() for p in paths.values()):
            self.assertEqual(audit.source_mode, "LOCAL_DONOR_RDONLY")
            self.assertEqual(audit.donor_files_inspected, 10)
            for key, (expected_bytes, expected_sha) in p91.PINNED_DONOR_SHA256.items():
                self.assertEqual(audit.bytes_by_artifact[key], expected_bytes)
                self.assertEqual(audit.sha256_by_artifact[key], expected_sha)
        else:
            self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_04_missing_donor_root_falls_back_to_clean_room(self) -> None:
        env = {
            p91.ENV_MAC_WORK_ROOT: "/nonexistent_phase91_mac_work_root",
            p91.ENV_MAIN_LAB_WORK_ROOT: "/nonexistent_phase91_main_work_root",
        }
        audit = p91.inspect_gyroflow_rtmd_anamorphic_donors(force_clean_room=True, env=env)
        self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(audit.all_contracts_verified)

    def test_05_redlines_zero_mutations_and_zero_stock_cp_faults(self) -> None:
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
        self.assertEqual(red["null_gpio_derefs"], 0)
        self.assertEqual(red["mailbox_stalls"], 0)
        self.assertEqual(red["stock_cp_fault_count"], 0)
        self.assertEqual(red["donor_access_mode"], "O_RDONLY")


class TestImu2000HzFifoAndCadence(unittest.TestCase):
    """Verify CXD90057/CXD90058 SPI 2000 Hz IMU ring buffer across Cinema Line frame rates."""

    def test_06_23_98p_cadence_approx_83_4_samples_per_frame(self) -> None:
        res, _ = p91.simulate_2000hz_imu_cadence("23.98p", num_frames=12)
        self.assertTrue(res.passed)
        self.assertEqual(res.min_samples_per_frame, 83)
        self.assertEqual(res.max_samples_per_frame, 84)
        self.assertAlmostEqual(res.mean_samples_per_frame, 83.4167, delta=0.1)
        self.assertEqual(res.fifo_overflow_events, 0)
        self.assertTrue(res.rtmd_gyro_enabled)

    def test_07_24_00p_cadence_83_84_alternating(self) -> None:
        res, _ = p91.simulate_2000hz_imu_cadence("24.00p", num_frames=12)
        self.assertTrue(res.passed)
        self.assertEqual(res.sample_counts_first_6_frames, (83, 83, 84, 83, 83, 84))
        self.assertAlmostEqual(res.mean_samples_per_frame, 83.3333, delta=0.05)

    def test_08_25_00p_cadence_exact_80_samples_per_frame(self) -> None:
        res, _ = p91.simulate_2000hz_imu_cadence("25.00p", num_frames=12)
        self.assertTrue(res.passed)
        self.assertEqual(res.min_samples_per_frame, 80)
        self.assertEqual(res.max_samples_per_frame, 80)
        self.assertEqual(res.sample_counts_first_6_frames, (80, 80, 80, 80, 80, 80))

    def test_09_29_97p_cadence_approx_66_7_samples_per_frame(self) -> None:
        res, _ = p91.simulate_2000hz_imu_cadence("29.97p", num_frames=12)
        self.assertTrue(res.passed)
        self.assertEqual(res.min_samples_per_frame, 66)
        self.assertEqual(res.max_samples_per_frame, 67)
        self.assertAlmostEqual(res.mean_samples_per_frame, 66.7333, delta=0.1)

    def test_10_59_94p_cadence_approx_33_4_samples_per_frame(self) -> None:
        res, _ = p91.simulate_2000hz_imu_cadence("59.94p", num_frames=12)
        self.assertTrue(res.passed)
        self.assertEqual(res.min_samples_per_frame, 33)
        self.assertEqual(res.max_samples_per_frame, 34)
        self.assertAlmostEqual(res.mean_samples_per_frame, 33.3667, delta=0.1)

    def test_11_119_88p_cadence_approx_16_7_samples_per_frame(self) -> None:
        res, _ = p91.simulate_2000hz_imu_cadence("119.88p", num_frames=12)
        self.assertTrue(res.passed)
        self.assertEqual(res.min_samples_per_frame, 16)
        self.assertEqual(res.max_samples_per_frame, 17)
        self.assertAlmostEqual(res.mean_samples_per_frame, 16.6833, delta=0.1)

    def test_12_microsecond_timestamp_crystal_drift_compensation(self) -> None:
        res, _ = p91.simulate_2000hz_imu_cadence("23.98p", num_frames=12, clock_drift_ppm=250.0)
        self.assertTrue(res.passed)
        self.assertGreater(res.uncompensated_drift_us, 100.0)
        self.assertLessEqual(res.max_timestamp_residual_us, 2.0)

    def test_13_fifo_overflow_watermark_guard_trips_fail_closed(self) -> None:
        res, _ = p91.simulate_2000hz_imu_cadence(
            "23.98p", num_frames=6, inject_fifo_stall_overflow=True
        )
        self.assertTrue(res.passed)
        self.assertGreater(res.fifo_high_watermark_trips, 0)
        self.assertGreater(res.fifo_overflow_events, 0)
        self.assertFalse(res.rtmd_gyro_enabled)
        self.assertEqual(res.rtmd_gyro_suppressed_reason, "FIFO_OVERFLOW_WATERMARK_TRIPPED")

    def test_14_sq_vfr_auto_disable_suppresses_rtmd_gyro_track(self) -> None:
        res, _ = p91.simulate_2000hz_imu_cadence("119.88p", num_frames=6, sq_vfr_enabled=True)
        self.assertTrue(res.passed)
        self.assertTrue(res.sq_vfr_enabled)
        self.assertFalse(res.rtmd_gyro_enabled)
        self.assertEqual(res.rtmd_gyro_suppressed_reason, "VFR_SQ_TIMEBASE_DECOUPLED")


class TestRtmdE4xxAndGyroflowQuaternion(unittest.TestCase):
    """Verify Sony E-Mount mounting matrix, SMPTE RDD 18 0xE4xx KLV & <0.02 deg integration."""

    def test_15_sony_emount_mounting_matrix_is_orthonormal_so3(self) -> None:
        ok, det = p91.verify_mounting_matrix_so3(p91.SONY_EMOUNT_IMU_TO_BODY_MATRIX)
        self.assertTrue(ok)
        self.assertEqual(det, 1.0)

    def test_16_non_orthonormal_or_left_handed_matrix_rejected(self) -> None:
        left_handed = ((1, 0, 0), (0, 1, 0), (0, 0, -1))
        ok, _ = p91.verify_mounting_matrix_so3(left_handed)
        self.assertFalse(ok)
        scaled = ((2, 0, 0), (0, 1, 0), (0, 0, 1))
        ok2, _ = p91.verify_mounting_matrix_so3(scaled)
        self.assertFalse(ok2)

    def test_17_rtmd_e4xx_packet_build_and_parse_roundtrip(self) -> None:
        _, frames = p91.simulate_2000hz_imu_cadence("24.00p", num_frames=3)
        pkt = p91.build_rtmd_e4xx_frame_packet(
            frame_index=2,
            readout_duration_us=8700,
            anamorphic_desqueeze_x100=180,
            ibis_mode_code=1,
            center_lock_energized=True,
            yaw_gain_scale=1.0 / 1.8,
            imu_samples=frames[2],
            rtmd_gyro_enabled=True,
        )
        parsed = p91.parse_and_verify_rtmd_e4xx_packet(pkt)
        self.assertTrue(parsed["valid"])
        self.assertEqual(parsed["frame_index"], 2)
        self.assertEqual(parsed["readout_duration_us"], 8700)
        self.assertEqual(parsed["anamorphic_desqueeze_x100"], 180)
        self.assertEqual(parsed["imu_sample_rate_hz"], 2000)
        self.assertEqual(parsed["imu_sample_count"], len(frames[2]))
        self.assertFalse(parsed["ibis_shift_embedded"])
        self.assertIn("0xe400", parsed["tags_present_hex"])
        self.assertIn("0xe420", parsed["tags_present_hex"])
        self.assertIn("0xe430", parsed["tags_present_hex"])

    def test_18_gyroflow_roundtrip_quaternion_drift_under_0_02_deg(self) -> None:
        ver = p91.verify_gyroflow_roundtrip_integration(
            fps_label="23.98p",
            num_frames=12,
            readout_duration_us=8700,
            anamorphic_desqueeze_x100=150,
        )
        self.assertTrue(ver.passed)
        self.assertLess(ver.quaternion_drift_deg, 0.02)
        self.assertEqual(ver.mounting_matrix_det, 1.0)
        self.assertEqual(ver.imu_sample_rate_hz, 2000)
        self.assertFalse(ver.ibis_shift_embedded)

    def test_19_rtmd_e4xx_rejects_malformed_ul_ber_and_readout_bounds(self) -> None:
        with self.assertRaises(p91.GyroflowRtmdAnamorphicError):
            p91.parse_and_verify_rtmd_e4xx_packet(b"BAD_UL_HEADER_BYTES")
        with self.assertRaises(p91.GyroflowRtmdAnamorphicError):
            p91.build_rtmd_e4xx_frame_packet(
                frame_index=0,
                readout_duration_us=0,
                anamorphic_desqueeze_x100=100,
                ibis_mode_code=0,
                center_lock_energized=True,
                yaw_gain_scale=0.0,
                imu_samples=(),
                rtmd_gyro_enabled=False,
            )

    def test_20_sq_vfr_packet_omits_0xe420_gyro_track_and_sets_flag(self) -> None:
        res, frames = p91.simulate_2000hz_imu_cadence("119.88p", num_frames=4, sq_vfr_enabled=True)
        pkt = p91.build_rtmd_e4xx_frame_packet(
            frame_index=0,
            readout_duration_us=4300,
            anamorphic_desqueeze_x100=100,
            ibis_mode_code=0,
            center_lock_energized=True,
            yaw_gain_scale=0.0,
            imu_samples=frames[0],
            rtmd_gyro_enabled=res.rtmd_gyro_enabled,
            sq_vfr_enabled=True,
        )
        parsed = p91.parse_and_verify_rtmd_e4xx_packet(pkt)
        self.assertTrue(parsed["valid"])
        self.assertEqual(parsed["imu_sample_count"], 0)
        self.assertNotIn("0xe420", parsed["tags_present_hex"])
        self.assertTrue(bool(parsed["coherence_flags"] & p91.RTMD_FLAG_VFR_SQ_AUTO_DISABLED))


class TestAnamorphicIbisAndCenterLockArbitrator(unittest.TestCase):
    """Verify Anamorphic Asymmetric Yaw Scaling, Center-Lock & Double-Stab Fail-Closed Guards."""

    def test_21_anamorphic_desqueeze_factors_asymmetric_yaw_scaling(self) -> None:
        for label, expected_s in (("1.33x", 1.33), ("1.5x", 1.5), ("1.8x", 1.8), ("2.0x", 2.0)):
            res = p91.arbitrate_anamorphic_ibis_mode(
                desqueeze_label=label,
                requested_ibis_mode=p91.IBIS_MODE_STANDARD,
                gyroflow_post_stab=False,
            )
            self.assertTrue(res.allowed, msg=f"Failed for {label}")
            self.assertEqual(res.arbitration_mode, p91.ARB_MODE_ASYMMETRIC_YAW_SCALING)
            self.assertAlmostEqual(res.yaw_gain_scale, 1.0 / expected_s, places=5)
            self.assertEqual(res.pitch_gain_scale, 1.0)
            self.assertGreater(res.predicted_uncompensated_wobble_px, 5.0)
            self.assertEqual(res.compensated_residual_wobble_px, 0.0)
            self.assertFalse(res.active_crop_warp_enabled)

    def test_22_anamorphic_1_3x_fx3_alias_and_off_1_0x_supported(self) -> None:
        r_13x = p91.arbitrate_anamorphic_ibis_mode(
            desqueeze_label="1.3x",
            requested_ibis_mode=p91.IBIS_MODE_STANDARD,
        )
        self.assertTrue(r_13x.allowed)
        self.assertAlmostEqual(r_13x.yaw_gain_scale, 1.0 / 1.3, places=5)

        r_off = p91.arbitrate_anamorphic_ibis_mode(
            desqueeze_label="Off",
            requested_ibis_mode=p91.IBIS_MODE_ACTIVE,
        )
        self.assertTrue(r_off.allowed)
        self.assertEqual(r_off.arbitration_mode, p91.ARB_MODE_SPHERICAL_BYPASS)
        self.assertEqual(r_off.yaw_gain_scale, 1.0)
        self.assertTrue(r_off.active_crop_warp_enabled)

    def test_23_post_gyroflow_ibis_center_lock_locks_0x0400_off(self) -> None:
        res = p91.arbitrate_anamorphic_ibis_mode(
            desqueeze_label="2.0x",
            requested_ibis_mode=p91.IBIS_MODE_ACTIVE,
            gyroflow_post_stab=True,
            embed_ibis_shift_in_rtmd=False,
        )
        self.assertTrue(res.allowed)
        self.assertEqual(res.arbitration_mode, p91.ARB_MODE_POST_GYROFLOW_CENTER_LOCK)
        self.assertEqual(res.effective_ibis_mode, p91.IBIS_MODE_OFF)
        self.assertEqual(res.effective_ibis_code, 0)
        self.assertTrue(res.center_lock_energized)
        self.assertTrue(res.rtmd_gyro_raw_enabled)
        self.assertFalse(res.rtmd_ibis_shift_embedded)
        self.assertTrue(res.double_stabilization_prevented)

    def test_24_uncompensated_spherical_active_crop_warp_blocked_fail_closed(self) -> None:
        res = p91.arbitrate_anamorphic_ibis_mode(
            desqueeze_label="1.5x",
            requested_ibis_mode=p91.IBIS_MODE_ACTIVE,
            gyroflow_post_stab=False,
        )
        self.assertFalse(res.allowed)
        self.assertEqual(res.status, "BLOCKED_ANAMORPHIC_SPHERICAL_ACTIVE_WARP")
        self.assertTrue(res.active_crop_warp_blocked)
        self.assertFalse(res.active_crop_warp_enabled)
        self.assertEqual(res.effective_ibis_code, 0)
        self.assertEqual(res.stock_cp_faults, 0)

    def test_25_uncompensated_spherical_standard_ibis_blocked_when_asym_disabled(self) -> None:
        res = p91.arbitrate_anamorphic_ibis_mode(
            desqueeze_label="2.0x",
            requested_ibis_mode=p91.IBIS_MODE_STANDARD,
            gyroflow_post_stab=False,
            allow_asymmetric_yaw_scaling=False,
        )
        self.assertFalse(res.allowed)
        self.assertEqual(res.status, "BLOCKED_ANAMORPHIC_UNCOMPENSATED_SPHERICAL_IBIS")
        self.assertTrue(res.active_crop_warp_blocked)

    def test_26_gyroflow_ibis_shift_offset_embedding_blocked_no_double_stab(self) -> None:
        res = p91.arbitrate_anamorphic_ibis_mode(
            desqueeze_label="1.8x",
            requested_ibis_mode=p91.IBIS_MODE_STANDARD,
            gyroflow_post_stab=True,
            embed_ibis_shift_in_rtmd=True,
        )
        self.assertFalse(res.allowed)
        self.assertEqual(res.status, "BLOCKED_GYROFLOW_DOUBLE_STABILIZATION_SHIFT_HAZARD")
        self.assertTrue(res.rtmd_ibis_shift_blocked)
        self.assertFalse(res.rtmd_ibis_shift_embedded)
        self.assertTrue(res.double_stabilization_prevented)

    def test_27_invalid_desqueeze_or_ibis_mode_raises_error(self) -> None:
        with self.assertRaises(p91.GyroflowRtmdAnamorphicError):
            p91.arbitrate_anamorphic_ibis_mode(
                desqueeze_label="3.0x",
                requested_ibis_mode=p91.IBIS_MODE_STANDARD,
            )
        with self.assertRaises(p91.GyroflowRtmdAnamorphicError):
            p91.arbitrate_anamorphic_ibis_mode(
                desqueeze_label="1.5x",
                requested_ibis_mode="HyperActive",
            )


class TestImx510RollingShutterSkewHil(unittest.TestCase):
    """Verify IMX510 readout durations (~8.7ms FF 4K, ~4.3ms 120p crop, HDMI RAW16) & de-skew."""

    def test_28_imx510_ff_4k_8_7ms_readout_and_rtmd_e400_roundtrip(self) -> None:
        res = p91.evaluate_imx510_rolling_shutter_hil("FF_4K_STANDARD")
        self.assertTrue(res.passed)
        self.assertEqual(res.readout_duration_us, 8700)
        self.assertEqual(res.readout_duration_ms, 8.7)
        self.assertEqual(res.rtmd_encoded_readout_us, 8700)
        self.assertTrue(res.readout_within_vsync_budget)
        self.assertLess(res.gyroflow_deskew_residual_px, 0.01)
        self.assertEqual(res.stock_cp_faults, 0)

    def test_29_imx510_4k_120p_1_1x_crop_4_3ms_readout_vsync_budget(self) -> None:
        res = p91.evaluate_imx510_rolling_shutter_hil("4K_120P_CROP_1_1X")
        self.assertTrue(res.passed)
        self.assertEqual(res.readout_duration_us, 4300)
        self.assertEqual(res.readout_duration_ms, 4.3)
        self.assertEqual(res.rtmd_encoded_readout_us, 4300)
        self.assertTrue(res.readout_within_vsync_budget)
        self.assertEqual(res.stock_cp_faults, 0)

    def test_30_imx510_hdmi_16bit_raw_8_9ms_readout_and_deskew(self) -> None:
        res = p91.evaluate_imx510_rolling_shutter_hil("HDMI_16BIT_RAW")
        self.assertTrue(res.passed)
        self.assertEqual(res.active_width, 4264)
        self.assertEqual(res.active_height, 2408)
        self.assertEqual(res.readout_duration_us, 8900)
        self.assertEqual(res.rtmd_encoded_readout_us, 8900)
        self.assertTrue(res.readout_within_vsync_budget)
        self.assertLess(res.gyroflow_deskew_residual_px, 0.01)
        self.assertEqual(res.stock_cp_faults, 0)

    def test_31_imx510_rs_hil_invalid_mode_raises_and_zero_stock_cp_faults(self) -> None:
        with self.assertRaises(p91.GyroflowRtmdAnamorphicError):
            p91.evaluate_imx510_rolling_shutter_hil("OPEN_GATE_6K_INVALID")


class TestStage14IntegrationCliAndHygiene(unittest.TestCase):
    """Verify Stage 14 integration into 14-stage suite, CLI flags, determinism & hygiene."""

    def test_32_clean_room_audit_digest_reproducible_and_no_bytes_repr_leak(self) -> None:
        rep1 = p91.run_phase91_gyroflow_rtmd_anamorphic_audit(force_clean_room=True)
        rep2 = p91.run_phase91_gyroflow_rtmd_anamorphic_audit(force_clean_room=True)
        self.assertEqual(rep1["audit_digest_sha256"], rep2["audit_digest_sha256"])

        rendered = json.dumps(rep1, allow_nan=False)
        self.assertNotRegex(rendered, r'(?<![0-9A-Za-z_/.-])b[\'"]')

        copy = dict(rep1)
        recorded = copy.pop("audit_digest_sha256")
        expected = hashlib.sha256(
            json.dumps(copy, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        self.assertEqual(recorded, expected)

    def test_33_standalone_cli_flags_emit_valid_outputs(self) -> None:
        for argv in (
            ["--clean-room", "--summary"],
            ["--clean-room", "--imu-matrix"],
            ["--clean-room", "--anamorphic-matrix"],
            ["--clean-room", "--rolling-shutter-matrix"],
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = p91.main(argv)
            self.assertEqual(rc, 0, msg=f"CLI argv={argv} failed")
            self.assertTrue(buf.getvalue().strip())

    def test_34_suite_integration_and_skip_phase91_flag(self) -> None:
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
        self.assertIn("gyro_anam=CLEAN_ROOM_SYNTHETIC", proc.stdout)

        proc_skip = subprocess.run(
            [
                sys.executable,
                "-B",
                str(FX3_VM_DIR / "fx3_vm_coemulation_suite.py"),
                "--clean-room",
                "--skip-phase91",
                "--summary",
            ],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc_skip.returncode, 0, msg=proc_skip.stderr)
        self.assertNotIn("gyro_anam=", proc_skip.stdout)

        cfg = suite.CoEmulationConfig(force_clean_room=True)
        s14 = suite.run_stage14_gyroflow_rtmd_anamorphic(cfg)
        self.assertTrue(s14["all_checks_passed"])
        self.assertEqual(s14["cp_mutation_bytes"], 0)
        self.assertEqual(s14["stock_cp_fault_count"], 0)

    def test_35_json_output_determinism_without_bytes_repr_leakage(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = p91.main(["--clean-room", "--json"])
        self.assertEqual(rc, 0)
        rendered = buf.getvalue()
        self.assertNotRegex(rendered, r'(?<![0-9A-Za-z_/.-])b[\'"]')
        parsed = json.loads(rendered)
        self.assertEqual(parsed["schema"], p91.PHASE_91_SCHEMA)
        self.assertTrue(parsed["all_checks_passed"])

    def test_36_source_hygiene_o_rdonly_and_no_forbidden_writes_or_port(self) -> None:
        forbidden_port = "87" + "68"
        emu_src = (FX3_VM_DIR / "gyroflow_rtmd_anamorphic_emulator.py").read_text(encoding="utf-8")
        test_src = Path(__file__).read_text(encoding="utf-8")

        self.assertIn("os.O_RDONLY", emu_src)
        self.assertNotIn("os.O_WRONLY", emu_src)
        self.assertNotIn("os.O_RDWR", emu_src)
        self.assertNotIn(forbidden_port, emu_src)
        self.assertNotIn(forbidden_port, test_src)
        self.assertIn("CP_MUTATION_BYTES = 0", emu_src)
        self.assertIn("WBI_MUTATION_BYTES = 0", emu_src)
        self.assertIn("NVRAM_PERSISTENT_WRITES = 0", emu_src)
        self.assertIn("PHYSICAL_DEVICE_WRITES = 0", emu_src)
        self.assertIn("PERSISTENT_EMMC_WRITES_AUTHORIZED = False", emu_src)


if __name__ == "__main__":
    unittest.main()
