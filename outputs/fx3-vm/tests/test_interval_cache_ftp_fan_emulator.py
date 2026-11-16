#!/usr/bin/env python3
"""Phase 96 Test Suite — Stage 15 Interval Recording (Time-Lapse Electronic-Shutter XAVC),
Picture Cache (DDR Circular Pre-Rec Ring-Buffer), Wired USB-LAN FTPS (P12 RF-Off Verified),
& Sigma Fan / Underwater Housing Vacuum HIL.

Exercises 36 fast unit, simulation, firewall, Stage 15 suite integration, CLI,
and source-hygiene tests across BOTH Local Donor (`os.O_RDONLY`) and
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
import subprocess
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
FX3_VM_DIR = TESTS_DIR.parent
REPO_ROOT = FX3_VM_DIR.parents[1]
if str(FX3_VM_DIR) not in sys.path:
    sys.path.insert(0, str(FX3_VM_DIR))

import fx3_vm_coemulation_suite as suite  # noqa: E402
import interval_cache_ftp_fan_emulator as p96  # noqa: E402


_AUDIT_CACHE: dict = {}


def _get_clean_room_audit() -> dict:
    if "clean_room" not in _AUDIT_CACHE:
        _AUDIT_CACHE["clean_room"] = p96.run_phase96_interval_cache_ftp_fan_audit(force_clean_room=True)
    return _AUDIT_CACHE["clean_room"]


class TestPhase96DonorAuditAndRedlines(unittest.TestCase):
    """Verify O_RDONLY donor audit, clean-room fallback, and zero-mutation redlines."""

    def test_01_clean_room_donor_audit_verifies_all_10_artifacts_and_sha256(self) -> None:
        audit = p96.inspect_interval_cache_ftp_fan_donors(force_clean_room=True)
        self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(audit.access_mode, "O_RDONLY")
        self.assertEqual(audit.donor_files_inspected, 0)
        self.assertTrue(audit.all_contracts_verified)
        self.assertGreaterEqual(len(audit.checked_markers), 25)
        self.assertEqual(audit.missing_markers, ())
        for key, (expected_bytes, expected_sha) in p96.PINNED_DONOR_SHA256.items():
            self.assertEqual(audit.bytes_by_artifact[key], expected_bytes)
            self.assertEqual(audit.sha256_by_artifact[key], expected_sha)

    def test_02_force_clean_room_env_disables_local_donor_paths(self) -> None:
        env = {p96.ENV_FORCE_CLEAN_ROOM: "1"}
        self.assertTrue(p96.is_forced_clean_room(env))
        paths = p96.resolve_phase96_donor_paths(env=env)
        self.assertEqual(len(paths), 10)
        for path in paths.values():
            self.assertIn(p96.CLEAN_ROOM_SENTINEL_DIRNAME, str(path))
        audit = p96.inspect_interval_cache_ftp_fan_donors(env=env)
        self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_03_local_donor_o_rdonly_audit_when_present_or_clean_room(self) -> None:
        if p96.is_forced_clean_room():
            audit = p96.inspect_interval_cache_ftp_fan_donors()
            self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")
            return
        paths = p96.resolve_phase96_donor_paths()
        audit = p96.inspect_interval_cache_ftp_fan_donors()
        self.assertTrue(audit.all_contracts_verified)
        if all(p.is_file() for p in paths.values()):
            self.assertEqual(audit.source_mode, "LOCAL_DONOR_RDONLY")
            self.assertEqual(audit.donor_files_inspected, 10)
            for key, (expected_bytes, expected_sha) in p96.PINNED_DONOR_SHA256.items():
                self.assertEqual(audit.bytes_by_artifact[key], expected_bytes)
                self.assertEqual(audit.sha256_by_artifact[key], expected_sha)
        else:
            self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_04_missing_donor_root_falls_back_to_clean_room(self) -> None:
        env = {
            p96.ENV_MAC_WORK_ROOT: "/nonexistent_phase96_mac_work_root",
            p96.ENV_MAIN_LAB_WORK_ROOT: "/nonexistent_phase96_main_work_root",
        }
        audit = p96.inspect_interval_cache_ftp_fan_donors(force_clean_room=True, env=env)
        self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(audit.all_contracts_verified)

    def test_05_redlines_zero_mutations_wf12_zero_and_emmc_locked(self) -> None:
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
        self.assertEqual(red["wf12_00342260_hits"], 0)
        self.assertEqual(red["emmc_partition_mutations"], 0)
        self.assertEqual(red["donor_access_mode"], "O_RDONLY")


class TestIntervalRecordingAndAeSmoother(unittest.TestCase):
    """Verify Electronic-Shutter Interval Rec, 6-stop sunset AE smoothing & NonRealTimeMeta."""

    def test_06_interval_recording_enforces_electronic_shutter_zero_curtain_wear(self) -> None:
        res = p96.simulate_interval_recording_session(
            interval_sec=5,
            shot_count=9999,
            ae_sensitivity="Mid",
            container_format="MXF",
            request_mechanical_shutter=True,
        )
        self.assertTrue(res.passed)
        self.assertEqual(res.shutter_mode, "ELECTRONIC_SHUTTER")
        self.assertEqual(res.mechanical_curtain_actuations, 0)
        self.assertTrue(res.mechanical_shutter_requested)
        self.assertTrue(res.mechanical_shutter_blocked)
        self.assertEqual(res.status, "ELECTRONIC_SHUTTER_FORCED_ZERO_WEAR")
        self.assertEqual(res.packed_frames, 9999)

    def test_07_sunset_6stop_ae_smoothing_across_high_mid_low_lock(self) -> None:
        r_high = p96.simulate_interval_recording_session(ae_sensitivity="High", shot_count=120)
        r_mid = p96.simulate_interval_recording_session(ae_sensitivity="Mid", shot_count=120)
        r_low = p96.simulate_interval_recording_session(ae_sensitivity="Low", shot_count=120)
        r_lock = p96.simulate_interval_recording_session(ae_sensitivity="Lock", shot_count=120)

        for r in (r_high, r_mid, r_low, r_lock):
            self.assertTrue(r.passed)
            self.assertEqual(r.mechanical_curtain_actuations, 0)
            self.assertGreater(r.flicker_suppression_ratio, 1.5)

        self.assertLessEqual(r_low.smoothed_max_step_ev, r_mid.smoothed_max_step_ev)
        self.assertLessEqual(r_mid.smoothed_max_step_ev, r_high.smoothed_max_step_ev)
        self.assertEqual(r_lock.ae_applied_span_ev, 0.0)
        self.assertEqual(r_lock.smoothed_max_step_ev, 0.0)
        self.assertGreater(r_mid.ae_applied_span_ev, 5.0)

    def test_08_single_mxf_and_mp4_frame_packing_and_nonrealtimemeta_tags(self) -> None:
        r_mxf = p96.simulate_interval_recording_session(
            interval_sec=10, shot_count=240, container_format="MXF", fps_label="24.00p"
        )
        r_mp4 = p96.simulate_interval_recording_session(
            interval_sec=2, shot_count=600, container_format="MP4", fps_label="59.94p"
        )
        self.assertTrue(r_mxf.nonrealtimemeta_xml_valid)
        self.assertTrue(r_mp4.nonrealtimemeta_xml_valid)
        self.assertEqual(r_mxf.codec_name, "XAVC-I")
        self.assertEqual(r_mp4.codec_name, "XAVC S-I")
        self.assertAlmostEqual(r_mxf.timelapse_speedup_factor, 240.0, places=2)
        self.assertGreater(r_mxf.packed_container_bytes, 240 * 1_000_000)

    def test_09_interval_bounds_reject_out_of_range_parameters(self) -> None:
        for kwargs in (
            {"interval_sec": 0},
            {"interval_sec": 61},
            {"shot_count": 0},
            {"shot_count": 10000},
            {"ae_sensitivity": "Ultra"},
            {"container_format": "AVI"},
            {"fps_label": "120.00p"},
        ):
            with self.assertRaises(p96.IntervalCacheFtpFanError):
                p96.simulate_interval_recording_session(**kwargs)

    def test_10_interval_1s_60s_boundary_values_succeed(self) -> None:
        r_min = p96.simulate_interval_recording_session(interval_sec=1, shot_count=1)
        r_max = p96.simulate_interval_recording_session(interval_sec=60, shot_count=9999)
        self.assertTrue(r_min.passed)
        self.assertTrue(r_max.passed)
        self.assertEqual(r_min.mechanical_curtain_actuations, 0)
        self.assertEqual(r_max.mechanical_curtain_actuations, 0)


class TestPictureCacheCircularRingArbitrator(unittest.TestCase):
    """Verify FX6 Picture Cache circular DDR ring-buffer within FX3 384 MiB safe pool."""

    def test_11_xavc_i_4k60_16s_clamps_to_384mib_preserving_appfw_headroom(self) -> None:
        res = p96.arbitrate_picture_cache_ring_buffer(
            codec_profile="XAVC-I 4K60",
            requested_cache_sec=16,
            target_slot="Slot A",
        )
        self.assertTrue(res.passed)
        self.assertTrue(res.clamped_to_safe_pool)
        self.assertEqual(res.status, "CLAMPED_TO_384MIB_POOL")
        self.assertEqual(res.effective_cache_sec, 5.0)
        self.assertLessEqual(res.allocated_pool_mib, 384.0)
        self.assertGreaterEqual(res.appfw_gpe0_kernel_headroom_mib, 1664.0)
        self.assertEqual(res.dropped_gops, 0)
        self.assertEqual(res.dropped_frames, 0)
        self.assertTrue(res.flush_idr_aligned)
        self.assertEqual(res.oom_events, 0)

    def test_12_xavc_i_4k24_10s_fits_unclamped_while_16s_clamps(self) -> None:
        r_10 = p96.arbitrate_picture_cache_ring_buffer(
            codec_profile="XAVC-I 4K24",
            requested_cache_sec=10,
        )
        r_16 = p96.arbitrate_picture_cache_ring_buffer(
            codec_profile="XAVC-I 4K24",
            requested_cache_sec=16,
        )
        self.assertTrue(r_10.passed)
        self.assertFalse(r_10.clamped_to_safe_pool)
        self.assertEqual(r_10.effective_cache_sec, 10.0)
        self.assertLessEqual(r_10.allocated_pool_mib, 384.0)

        self.assertTrue(r_16.passed)
        self.assertTrue(r_16.clamped_to_safe_pool)
        self.assertEqual(r_16.effective_cache_sec, 13.0)
        self.assertLessEqual(r_16.allocated_pool_mib, 384.0)

    def test_13_xavc_l_and_fhd_full_16s_long_gop_alignment(self) -> None:
        for prof in ("XAVC-L 4K30", "XAVC-L FHD60"):
            res = p96.arbitrate_picture_cache_ring_buffer(
                codec_profile=prof,
                requested_cache_sec=16,
                target_slot="Slot A+B",
            )
            self.assertTrue(res.passed)
            self.assertFalse(res.clamped_to_safe_pool)
            self.assertEqual(res.effective_cache_sec, 16.0)
            self.assertTrue(res.flush_idr_aligned)
            self.assertEqual(res.dropped_gops, 0)
            self.assertEqual(res.flushed_prerec_frames % res.gop_len_frames, 0)

    def test_14_picture_cache_auto_suspends_for_sq_hdmi_raw_and_interval(self) -> None:
        r_sq = p96.arbitrate_picture_cache_ring_buffer(sq_vfr_active=True)
        r_raw = p96.arbitrate_picture_cache_ring_buffer(hdmi_raw_active=True)
        r_ivl = p96.arbitrate_picture_cache_ring_buffer(interval_rec_active=True)
        for r, expected_reason in (
            (r_sq, "SQ_VFR_ACTIVE"),
            (r_raw, "HDMI_RAW16_ACTIVE"),
            (r_ivl, "INTERVAL_REC_ACTIVE"),
        ):
            self.assertTrue(r.passed)
            self.assertTrue(r.suspended_by_exclusion)
            self.assertEqual(r.status, "SUSPENDED_BY_EXCLUSION")
            self.assertEqual(r.exclusion_reason, expected_reason)
            self.assertEqual(r.allocated_pool_mib, 0.0)
            self.assertEqual(r.appfw_gpe0_kernel_headroom_mib, 2048.0)

    def test_15_picture_cache_invalid_inputs_raise_error(self) -> None:
        with self.assertRaises(p96.IntervalCacheFtpFanError):
            p96.arbitrate_picture_cache_ring_buffer(requested_cache_sec=1)
        with self.assertRaises(p96.IntervalCacheFtpFanError):
            p96.arbitrate_picture_cache_ring_buffer(requested_cache_sec=17)
        with self.assertRaises(p96.IntervalCacheFtpFanError):
            p96.arbitrate_picture_cache_ring_buffer(codec_profile="PRORES_4444")
        with self.assertRaises(p96.IntervalCacheFtpFanError):
            p96.arbitrate_picture_cache_ring_buffer(target_slot="Slot C")


class TestWiredUsblanFtpsAndP12EmmcFirewall(unittest.TestCase):
    """Verify wired USB-LAN FTPS TLS 1.3 + REST resume, P12 RF-off & eMMC firewall."""

    def test_16_proxy_only_and_original_and_proxy_ftps_rest_resume_parity(self) -> None:
        r_proxy = p96.execute_wired_usblan_ftps_transfer(
            queue_mode=p96.FTPS_QUEUE_PROXY_ONLY,
            inject_link_blip=True,
        )
        r_orig = p96.execute_wired_usblan_ftps_transfer(
            queue_mode=p96.FTPS_QUEUE_ORIGINAL_AND_PROXY,
            inject_link_blip=True,
        )
        for r in (r_proxy, r_orig):
            self.assertTrue(r.allowed)
            self.assertEqual(r.status, "FTPS_TLS13_REST_RESUMED_OK")
            self.assertEqual(r.tls_version, "TLSv1.3")
            self.assertGreater(r.blip_injected_at_byte, 0)
            self.assertGreater(r.rest_resume_offset_bytes, 0)
            self.assertEqual(r.rest_resume_offset_bytes % 512, 0)
            self.assertGreater(r.resumed_bytes_transferred, 0)
            self.assertTrue(r.bytes_sha256_matched)
            self.assertEqual(r.wifi_rf_tx_packets, 0)
            self.assertEqual(r.bt_hci_tx_packets, 0)
            self.assertEqual(r.wf12_00342260_hits, 0)
            self.assertTrue(r.p12_rf_fenced)
            self.assertEqual(r.emmc_partition_writes, 0)

        self.assertEqual(len(r_proxy.files_transferred), 2)
        self.assertEqual(len(r_orig.files_transferred), 3)

    def test_17_clean_ftps_transfer_without_blip(self) -> None:
        res = p96.execute_wired_usblan_ftps_transfer(inject_link_blip=False, passive_mode="PASV")
        self.assertTrue(res.allowed)
        self.assertEqual(res.status, "FTPS_TLS13_COMPLETED_OK")
        self.assertEqual(res.rest_resume_offset_bytes, 0)
        self.assertEqual(res.resumed_bytes_transferred, 0)
        self.assertTrue(res.bytes_sha256_matched)

    def test_18_p12_blocks_wifi_bt_interfaces_and_radio_wake(self) -> None:
        for kwargs in (
            {"interface_name": "wlan0"},
            {"interface_name": "bt0"},
            {"wifi_radio_requested": True},
            {"p12_rf_off_enforced": False},
        ):
            res = p96.execute_wired_usblan_ftps_transfer(**kwargs)
            self.assertFalse(res.allowed)
            self.assertEqual(res.status, "BLOCKED_RF_INTERFACE_FORBIDDEN_BY_P12")
            self.assertEqual(res.wifi_rf_tx_packets, 0)
            self.assertEqual(res.bt_hci_tx_packets, 0)
            self.assertEqual(res.wf12_00342260_hits, 0)

    def test_19_unsupported_usb_class_and_insecure_ftp_blocked(self) -> None:
        r_rndis = p96.execute_wired_usblan_ftps_transfer(usb_class="RNDIS")
        r_ecm = p96.execute_wired_usblan_ftps_transfer(usb_class="CDC-ECM")
        r_tls12 = p96.execute_wired_usblan_ftps_transfer(tls_version="TLSv1.2")
        r_active = p96.execute_wired_usblan_ftps_transfer(passive_mode="PORT")
        self.assertFalse(r_rndis.allowed)
        self.assertEqual(r_rndis.status, "BLOCKED_UNSUPPORTED_USBLAN_TRANSPORT")
        self.assertFalse(r_ecm.allowed)
        self.assertFalse(r_tls12.allowed)
        self.assertEqual(r_tls12.status, "BLOCKED_INSECURE_OR_ACTIVE_FTP_REJECTED")
        self.assertFalse(r_active.allowed)

    def test_20_emmc_p1_to_p15_and_path_traversal_100pct_blocked(self) -> None:
        bad_paths = (
            "/dev/mmcblk0p1",
            "/dev/mmcblk0p12",
            "/dev/mmcblk0p15",
            "/dev/nflasha15",
            "/mnt/nflasha12/RQ_LIC.DAT",
            "/media/slot_a/../../dev/mmcblk0p1",
            "bk4://persistent/0x019e0012",
            "/cert/RQ_LIC.DAT",
            "/etc/passwd",
        )
        for p in bad_paths:
            res = p96.execute_wired_usblan_ftps_transfer(source_path=p)
            self.assertFalse(res.allowed, msg=f"Path unexpectedly allowed: {p}")
            self.assertEqual(res.status, "BLOCKED_INTERNAL_EMMC_PATH_TRAVERSAL")
            self.assertTrue(res.emmc_traversal_blocked)
            self.assertEqual(res.emmc_partition_writes, 0)


class TestSigmaFanAndUnderwaterHousingHil(unittest.TestCase):
    """Verify Sigma fan stall, side exhaust occlusion & housing vacuum HIL."""

    def test_21_nominal_sealed_housing_continues_recording_green(self) -> None:
        res = p96.evaluate_fan_and_housing_hil(
            scenario_id="HIL_NOMINAL",
            pwm_duty_pct=45.0,
            measured_rpm=2650,
            intake_clearance_mm=15.0,
            exhaust_clearance_mm=18.0,
            underwater_housing_active=True,
            vacuum_drop_mbar_per_10min=0.3,
            vacuum_check_elapsed_min=15.0,
        )
        self.assertTrue(res.passed)
        self.assertFalse(res.fault_detected)
        self.assertEqual(res.fault_code, "NONE")
        self.assertEqual(res.action_taken, "CONTINUE_NOMINAL_RECORDING")
        self.assertFalse(res.rsv_flush_executed)
        self.assertEqual(res.emmc_corruptions, 0)

    def test_22_hall_tachometer_rotor_stall_triggers_rsv_flush_and_shutdown(self) -> None:
        res = p96.evaluate_fan_and_housing_hil(
            scenario_id="HIL_ROTOR_STALL",
            pwm_duty_pct=65.0,
            measured_rpm=0,
            active_recording_frames=240,
        )
        self.assertTrue(res.passed)
        self.assertTrue(res.fault_detected)
        self.assertEqual(res.fault_code, "FAN_TACHOMETER_ROTOR_STALL")
        self.assertTrue(res.rsv_flush_executed)
        self.assertEqual(res.rsv_committed_frames, 240)
        self.assertEqual(res.rsv_salvageable_frames, 240)
        self.assertEqual(res.exfat_volume_dirty_bit, 0)
        self.assertTrue(res.safe_shutdown_executed)
        self.assertEqual(res.emmc_corruptions, 0)
        self.assertFalse(res.persistent_emmc_writes_authorized)

    def test_23_blocked_side_exhaust_under_5mm_triggers_graceful_rsv_flush(self) -> None:
        res = p96.evaluate_fan_and_housing_hil(
            scenario_id="HIL_EXHAUST_OCCLUDED",
            pwm_duty_pct=70.0,
            measured_rpm=2850,
            exhaust_clearance_mm=3.2,
            active_recording_frames=180,
        )
        self.assertTrue(res.passed)
        self.assertTrue(res.fault_detected)
        self.assertEqual(res.fault_code, "BLOCKED_SIDE_EXHAUST_BACKPRESSURE")
        self.assertTrue(res.rsv_flush_executed)
        self.assertEqual(res.rsv_salvageable_frames, 180)
        self.assertTrue(res.safe_shutdown_executed)
        self.assertEqual(res.emmc_corruptions, 0)

    def test_24_housing_vacuum_drop_over_1_5mbar_10min_triggers_rsv_shutdown(self) -> None:
        res = p96.evaluate_fan_and_housing_hil(
            scenario_id="HIL_VACUUM_LEAK",
            underwater_housing_active=True,
            vacuum_drop_mbar_per_10min=1.9,
            vacuum_check_elapsed_min=12.0,
            active_recording_frames=300,
        )
        self.assertTrue(res.passed)
        self.assertTrue(res.fault_detected)
        self.assertEqual(res.fault_code, "HOUSING_VACUUM_LEAK_EXCEEDED")
        self.assertTrue(res.rsv_flush_executed)
        self.assertEqual(res.rsv_committed_frames, 300)
        self.assertEqual(res.rsv_salvageable_frames, 300)
        self.assertEqual(res.exfat_volume_dirty_bit, 0)
        self.assertTrue(res.safe_shutdown_executed)
        self.assertEqual(res.emmc_corruptions, 0)

    def test_25_housing_moisture_and_short_check_trigger_fail_closed_rsv(self) -> None:
        r_moist = p96.evaluate_fan_and_housing_hil(
            scenario_id="HIL_MOISTURE",
            underwater_housing_active=True,
            moisture_sensor_triggered=True,
        )
        r_short = p96.evaluate_fan_and_housing_hil(
            scenario_id="HIL_SHORT_VACUUM_CHECK",
            underwater_housing_active=True,
            vacuum_drop_mbar_per_10min=0.1,
            vacuum_check_elapsed_min=4.0,
        )
        self.assertEqual(r_moist.fault_code, "HOUSING_MOISTURE_INTRUSION_ALERT")
        self.assertTrue(r_moist.rsv_flush_executed)
        self.assertTrue(r_moist.safe_shutdown_executed)
        self.assertEqual(r_short.fault_code, "HOUSING_VACUUM_LEAK_EXCEEDED")
        self.assertTrue(r_short.rsv_flush_executed)

    def test_26_invalid_fan_hil_telemetry_raises_error(self) -> None:
        with self.assertRaises(p96.IntervalCacheFtpFanError):
            p96.evaluate_fan_and_housing_hil(scenario_id="BAD", pwm_duty_pct=110.0)
        with self.assertRaises(p96.IntervalCacheFtpFanError):
            p96.evaluate_fan_and_housing_hil(scenario_id="BAD", measured_rpm=-5)
        with self.assertRaises(p96.IntervalCacheFtpFanError):
            p96.evaluate_fan_and_housing_hil(scenario_id="BAD", exhaust_clearance_mm=-1.0)


class TestStage15IntegrationCliAndHygiene(unittest.TestCase):
    """Verify Stage 15 integration into 15-stage suite, CLI flags, determinism & hygiene."""

    def test_27_clean_room_audit_digest_reproducible_and_no_bytes_repr(self) -> None:
        rep1 = p96.run_phase96_interval_cache_ftp_fan_audit(force_clean_room=True)
        rep2 = p96.run_phase96_interval_cache_ftp_fan_audit(force_clean_room=True)
        self.assertEqual(rep1["audit_digest_sha256"], rep2["audit_digest_sha256"])

        rendered = json.dumps(rep1, allow_nan=False)
        self.assertNotRegex(rendered, r'(?<![0-9A-Za-z_/.-])b[\'"]')

        copy = dict(rep1)
        recorded = copy.pop("audit_digest_sha256")
        expected = hashlib.sha256(
            json.dumps(copy, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        self.assertEqual(recorded, expected)

    def test_28_standalone_cli_flags_emit_valid_outputs(self) -> None:
        for argv in (
            ["--clean-room", "--summary"],
            ["--clean-room", "--interval-matrix"],
            ["--clean-room", "--cache-matrix"],
            ["--clean-room", "--ftps-matrix"],
            ["--clean-room", "--fan-housing-matrix"],
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = p96.main(argv)
            self.assertEqual(rc, 0, msg=f"CLI argv={argv} failed")
            self.assertTrue(buf.getvalue().strip())

    def test_29_suite_integration_and_skip_phase96_flag(self) -> None:
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
        self.assertIn("ivl_cache_ftp_fan=CLEAN_ROOM_SYNTHETIC", proc.stdout)

        proc_skip = subprocess.run(
            [
                sys.executable,
                "-B",
                str(FX3_VM_DIR / "fx3_vm_coemulation_suite.py"),
                "--clean-room",
                "--skip-phase96",
                "--summary",
            ],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc_skip.returncode, 0, msg=proc_skip.stderr)
        self.assertNotIn("ivl_cache_ftp_fan=", proc_skip.stdout)

        cfg = suite.CoEmulationConfig(force_clean_room=True)
        s15 = suite.run_stage15_interval_cache_ftp_fan(cfg)
        self.assertTrue(s15["all_checks_passed"])
        self.assertEqual(s15["cp_mutation_bytes"], 0)
        self.assertEqual(s15["wf12_00342260_hits"], 0)
        self.assertEqual(s15["emmc_partition_mutations"], 0)

    def test_30_json_output_determinism_without_bytes_repr_leakage(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = p96.main(["--clean-room", "--json"])
        self.assertEqual(rc, 0)
        rendered = buf.getvalue()
        self.assertNotRegex(rendered, r'(?<![0-9A-Za-z_/.-])b[\'"]')
        parsed = json.loads(rendered)
        self.assertEqual(parsed["schema"], p96.PHASE_96_SCHEMA)
        self.assertTrue(parsed["all_checks_passed"])

    def test_31_suite_direct_stage15_and_config_toggle(self) -> None:
        cfg_on = suite.CoEmulationConfig(force_clean_room=True, include_phase96_interval_cache_ftp_fan=True)
        rep_on = suite.run_fx3_vm_coemulation_suite(cfg_on)
        self.assertTrue(rep_on["all_checks_passed"])
        self.assertIn("stage15_phase96_interval_cache_ftp_fan", rep_on)

        cfg_off = suite.CoEmulationConfig(force_clean_room=True, include_phase96_interval_cache_ftp_fan=False)
        rep_off = suite.run_fx3_vm_coemulation_suite(cfg_off)
        self.assertTrue(rep_off["all_checks_passed"])
        self.assertNotIn("stage15_phase96_interval_cache_ftp_fan", rep_off)

    def test_32_picture_cache_fhd_222mbps_clamping_math(self) -> None:
        res = p96.arbitrate_picture_cache_ring_buffer(
            codec_profile="XAVC-I FHD60",
            requested_cache_sec=16,
        )
        self.assertTrue(res.passed)
        self.assertTrue(res.clamped_to_safe_pool)
        self.assertEqual(res.effective_cache_sec, 14.0)
        self.assertLessEqual(res.allocated_pool_mib, 384.0)

    def test_33_ftps_queue_validation_rejects_unknown_mode(self) -> None:
        with self.assertRaises(p96.IntervalCacheFtpFanError):
            p96.execute_wired_usblan_ftps_transfer(queue_mode="RAW_DUMP")

    def test_34_thermal_ceiling_90c_triggers_graceful_rsv_shutdown(self) -> None:
        res = p96.evaluate_fan_and_housing_hil(
            scenario_id="HIL_THERMAL_90C",
            pwm_duty_pct=100.0,
            measured_rpm=3200,
            soc_temp_c=91.5,
        )
        self.assertTrue(res.passed)
        self.assertTrue(res.fault_detected)
        self.assertEqual(res.fault_code, "SOC_THERMAL_CEILING_SHUTDOWN")
        self.assertTrue(res.rsv_flush_executed)
        self.assertTrue(res.safe_shutdown_executed)
        self.assertEqual(res.emmc_corruptions, 0)

    def test_35_dual_mode_suite_json_no_bytes_repr_leakage(self) -> None:
        rep = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig(force_clean_room=True))
        rendered = json.dumps(rep, allow_nan=False)
        self.assertNotRegex(rendered, r'(?<![0-9A-Za-z_/.-])b[\'"]')

    def test_36_source_hygiene_o_rdonly_and_no_forbidden_writes_or_port(self) -> None:
        forbidden_port = "87" + "68"
        emu_src = (FX3_VM_DIR / "interval_cache_ftp_fan_emulator.py").read_text(encoding="utf-8")
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
