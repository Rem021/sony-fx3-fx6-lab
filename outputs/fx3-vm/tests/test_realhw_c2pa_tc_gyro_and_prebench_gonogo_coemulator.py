#!/usr/bin/env python3
"""Phase 172 Test Suite — Stage 30 (`30/30` Milestone Stage) Real-Hardware Main Track:
`p12:/cert/RQ_LIC.DAT` C2PA Lock, `VMC-BNCM1` (`EXT-LK`) SMPTE-12M Timecode,
`IMX510` 6-Axis IMU Gyro `NonRealTimeMeta.xml` & 10-Step Pre-Bench Go/No-Go HIL Co-Emulator.

Exercises 46 fast dual-mode unit, integration, Pillar A-D HIL, XML schema,
10-step pre-bench Go/No-Go lifecycle, 30/30 suite orchestration, CLI, runtime-budget,
and clean-room hygiene checks.
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import contextlib
import hashlib
import io
import json
import os
import re
import subprocess
import time
import unittest
from pathlib import Path
import xml.etree.ElementTree as ET

TESTS_DIR = Path(__file__).resolve().parent
FX3_VM_DIR = TESTS_DIR.parent
REPO_ROOT = FX3_VM_DIR.parents[1]
if str(FX3_VM_DIR) not in sys.path:
    sys.path.insert(0, str(FX3_VM_DIR))

import fx3_vm_coemulation_suite as suite  # noqa: E402
import realhw_c2pa_tc_gyro_and_prebench_gonogo_coemulator as p172  # noqa: E402


_AUDIT_CACHE: dict = {}


def _get_default_audit() -> dict:
    key = ("default", p172.is_forced_clean_room())
    if key not in _AUDIT_CACHE:
        _AUDIT_CACHE[key] = p172.run_phase172_realhw_c2pa_tc_gyro_prebench_hil(env=os.environ)
    return _AUDIT_CACHE[key]


def _get_clean_room_audit() -> dict:
    key = ("clean_room", True)
    if key not in _AUDIT_CACHE:
        _AUDIT_CACHE[key] = p172.run_phase172_realhw_c2pa_tc_gyro_prebench_hil(
            force_clean_room=True,
            env=os.environ,
        )
    return _AUDIT_CACHE[key]


class TestStage30DualModeDonorsAndRedlines(unittest.TestCase):
    """Dual-mode O_RDONLY donor inspection, parity contracts & hard-locked safety redlines."""

    def test_01_donor_path_resolution_honors_clean_room_toggle(self) -> None:
        self.assertTrue(p172.is_forced_clean_room({"FX3_FX6_FORCE_CLEAN_ROOM": "1"}))
        self.assertFalse(p172.is_forced_clean_room({"FX3_FX6_FORCE_CLEAN_ROOM": "0"}))
        paths_clean = p172.resolve_phase172_donor_paths(env={"FX3_FX6_FORCE_CLEAN_ROOM": "1"})
        self.assertEqual(len(paths_clean), 10)
        for p in paths_clean.values():
            self.assertIn(p172.CLEAN_ROOM_SENTINEL_DIRNAME, str(p))
            self.assertFalse(p.exists())

    def test_02_clean_room_synthetic_fixtures_valid_cpapp_elf_and_bk4(self) -> None:
        fx = p172.build_clean_room_phase172_fixtures()
        self.assertEqual(len(fx), 10)
        for k in ("fx3_libmpr", "fx6_libmpr", "fx3_sencore", "fx6_sencore", "fx3_im_elf", "fx6_im_elf"):
            self.assertEqual(fx[k][:4], b"\x7fELF")
        self.assertEqual(fx["fx3_backup"][12:16], b"BK4\x00")
        self.assertEqual(fx["fx6_backup"][12:16], b"BK4\x00")
        self.assertIn(b"InfraC2PA", fx["fx3_libmpr"])
        self.assertNotIn(b"InfraC2PA", fx["fx6_libmpr"])
        self.assertIn(b"ILME-FX3", fx["fx3_cpapp"])
        self.assertNotIn(b"ILME-FX3", fx["fx6_cpapp"])

    def test_03_clean_room_donor_audit_verifies_all_10_donors(self) -> None:
        da = p172.inspect_phase172_donors(force_clean_room=True)
        self.assertEqual(da.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(da.access_mode, "O_RDONLY")
        self.assertEqual(da.donor_files_inspected, 10)
        self.assertTrue(da.all_contracts_verified, msg=str(da.errors))
        self.assertEqual(da.errors, ())

    def test_04_default_mode_donor_audit_passes_in_current_env(self) -> None:
        rep = _get_default_audit()
        self.assertTrue(rep["all_checks_passed"])
        da = rep["donor_audit"]
        self.assertTrue(da["all_contracts_verified"], msg=str(da["errors"]))
        self.assertEqual(da["donor_files_inspected"], 10)
        self.assertIn(rep["source_mode"], ("LOCAL_DONOR_RDONLY", "CLEAN_ROOM_SYNTHETIC"))

    def test_05_cpapp_arm32_entry_and_fx3_c2pa_markers_absent_in_fx6_libmpr(self) -> None:
        da = _get_default_audit()["donor_audit"]
        self.assertTrue(da["fx3_cpapp"]["arm32_entry_ok"])
        self.assertTrue(da["fx6_cpapp"]["arm32_entry_ok"])
        self.assertEqual(da["fx3_cpapp"]["load_base_hex"], "0x00108000")
        self.assertTrue(da["fx3_only_cp_markers_absent_in_fx6_cp"])
        self.assertTrue(da["fx3_c2pa_markers_absent_in_fx6_libmpr"])
        self.assertEqual(da["fx3_libmpr"]["marker_hits"]["InfraC2PA"], 1)
        self.assertEqual(da["fx6_libmpr"]["marker_hits"]["InfraC2PA"], 0)
        self.assertEqual(da["fx6_libmpr"]["marker_hits"]["NonRealTimeMeta"], 1)

    def test_06_elf_parity_libmpr_sencore_im_elf_and_backup_bk4(self) -> None:
        da = _get_default_audit()["donor_audit"]
        self.assertEqual(da["fx3_libmpr"]["export_count"], p172.EXPECTED_FX3_LIBMPR_EXPORTS)
        self.assertEqual(da["fx6_libmpr"]["export_count"], p172.EXPECTED_FX6_LIBMPR_EXPORTS)
        self.assertTrue(da["sencore_symbol_parity"])
        self.assertEqual(da["fx3_sencore"]["export_count"], 355)
        self.assertEqual(da["fx3_sencore"]["import_count"], 130)
        self.assertTrue(da["im_elf_abi_zero_diff"])
        self.assertEqual(da["fx3_im_elf"]["export_count"], 11)
        self.assertEqual(da["fx3_im_elf"]["import_count"], 85)
        self.assertEqual(da["fx3_backup"]["magic_ascii"], "BK4")
        self.assertEqual(da["fx3_backup"]["subsystem_count"], 819)
        self.assertEqual(da["fx6_backup"]["subsystem_count"], 840)

    def test_07_hard_locked_safety_redlines_enforced_in_both_modes(self) -> None:
        for rep in (_get_clean_room_audit(), _get_default_audit()):
            red = rep["redlines"]
            self.assertTrue(red["p8_cp_mutation_forbidden"])
            self.assertEqual(red["nop_count"], 0)
            self.assertEqual(red["guest_code_modification_bytes"], 0)
            self.assertEqual(red["cp_mutation_bytes"], 0)
            self.assertEqual(red["wbi_mutation_bytes"], 0)
            self.assertEqual(red["calibration_mutation_bytes"], 0)
            self.assertEqual(red["c2pa_cert_mutation_bytes"], 0)
            self.assertEqual(red["p12_cert_mount_flags"], "MS_RDONLY")
            self.assertEqual(red["p2_mutation_bytes"], 0)
            self.assertEqual(red["p18_mutation_bytes"], 0)
            self.assertEqual(red["nvram_persistent_writes"], 0)
            self.assertEqual(red["bk4_persistent_nvram_writes"], 0)
            self.assertEqual(red["physical_device_writes"], 0)
            self.assertFalse(red["persistent_emmc_writes_authorized"])
            self.assertEqual(red["emmc_nflasha_write_count"], 0)
            self.assertFalse(red["spi_nor_write_authorized"])
            self.assertEqual(red["otp_write_count"], 0)
            self.assertEqual(red["rpmb_write_count"], 0)
            self.assertEqual(red["orig_residual_count"], 0)
            self.assertEqual(red["tmp_jiritsu_residual_count"], 0)
            self.assertEqual(red["p6_chunk_residual_count"], 0)
            self.assertEqual(red["uart_contention_damage_events"], 0)
            self.assertEqual(red["over_voltage_damage_events"], 0)
            self.assertEqual(red["donor_access_mode"], "O_RDONLY")

    def test_08_donor_cache_returns_identical_audit_object(self) -> None:
        a1 = p172.inspect_phase172_donors(force_clean_room=True)
        a2 = p172.inspect_phase172_donors(force_clean_room=True)
        self.assertIs(a1, a2)


class TestStage30PillarAC2paRqLicLockAndFirewall(unittest.TestCase):
    """Pillar A — p12:/cert/RQ_LIC.DAT MS_RDONLY immutability & anti-forgery firewall."""

    def test_09_c2pa_rq_lic_3phase_lifecycle_ms_rdonly_zero_mutation(self) -> None:
        res = p172.simulate_c2pa_rq_lic_lifecycle()
        self.assertTrue(res.valid)
        self.assertEqual(res.phases_verified, p172.C2PA_LIFECYCLE_PHASES)
        self.assertEqual(res.p12_mount_point, "p12:/cert")
        self.assertEqual(res.p12_mount_flags, "MS_RDONLY")
        self.assertEqual(res.rq_lic_path, "p12:/cert/RQ_LIC.DAT")
        self.assertEqual(res.c2pa_cert_mutation_bytes, 0)
        self.assertTrue(res.rq_lic_sha256_h0_to_h3_identical)
        self.assertEqual(res.private_key_reads, 0)
        self.assertEqual(res.private_key_exports, 0)
        self.assertEqual(res.status_code, "C2PA_RQ_LIC_MS_RDONLY_IMMUTABLE_OK")

    def test_10_p12_write_request_or_rw_remount_blocked_fail_closed(self) -> None:
        w = p172.simulate_c2pa_rq_lic_lifecycle(write_requested=True)
        self.assertFalse(w.valid)
        self.assertEqual(w.c2pa_cert_mutation_bytes, 0)
        self.assertEqual(w.status_code, "BLOCKED_P12_CERT_NON_RDONLY_OR_WRITE")

        rw = p172.simulate_c2pa_rq_lic_lifecycle(p12_mount_flags="MS_RDWR")
        self.assertFalse(rw.valid)
        self.assertEqual(rw.status_code, "BLOCKED_P12_CERT_NON_RDONLY_OR_WRITE")

    def test_11_rq_lic_sha256_drift_or_invalid_license_count_blocked(self) -> None:
        drift = p172.simulate_c2pa_rq_lic_lifecycle(sha256_by_epoch={"H2": "deadbeef" * 8})
        self.assertFalse(drift.valid)
        self.assertFalse(drift.rq_lic_sha256_h0_to_h3_identical)
        self.assertEqual(drift.status_code, "BLOCKED_RQ_LIC_SHA256_DRIFT")

        bad_lic0 = p172.simulate_c2pa_rq_lic_lifecycle(license_count=0)
        self.assertFalse(bad_lic0.valid)
        self.assertEqual(bad_lic0.status_code, "BLOCKED_RQ_LIC_INVALID_LICENSE_COUNT")

        bad_lic101 = p172.simulate_c2pa_rq_lic_lifecycle(license_count=101)
        self.assertFalse(bad_lic101.valid)
        self.assertEqual(bad_lic101.status_code, "BLOCKED_RQ_LIC_INVALID_LICENSE_COUNT")

    def test_12_same_body_fx3_stock_and_unsigned_research_modes_admitted(self) -> None:
        r_stock = p172.evaluate_c2pa_signing_firewall(signing_mode="SAME_BODY_STOCK_C2PA")
        self.assertTrue(r_stock.admitted)
        self.assertFalse(r_stock.firewall_blocked)
        self.assertEqual(r_stock.c2pa_cert_mutation_bytes, 0)

        r_unsig = p172.evaluate_c2pa_signing_firewall(signing_mode="UNSIGNED_STAGE_B_RESEARCH_OVERLAY")
        self.assertTrue(r_unsig.admitted)
        self.assertFalse(r_unsig.firewall_blocked)

    def test_13_cross_body_cloning_and_cross_model_signing_blocked(self) -> None:
        xb = p172.evaluate_c2pa_signing_firewall(target_body_serial="FX3-CLONE-999")
        self.assertFalse(xb.admitted)
        self.assertTrue(xb.firewall_blocked)
        self.assertTrue(xb.cross_body_blocked)
        self.assertFalse(xb.cross_model_blocked)
        self.assertEqual(xb.status_code, "BLOCKED_CROSS_BODY_C2PA_SIGNING")

        for model_name, model_id in p172.SUPPORTED_FOREIGN_MODEL_IDS.items():
            xm = p172.evaluate_c2pa_signing_firewall(
                requested_model_name=model_name,
                requested_model_id=model_id,
            )
            self.assertFalse(xm.admitted, msg=model_name)
            self.assertTrue(xm.firewall_blocked)
            self.assertTrue(xm.cross_model_blocked)
            self.assertEqual(xm.status_code, "BLOCKED_CROSS_MODEL_C2PA_SIGNING")

    def test_14_sigcert_p12_extraction_and_unknown_signing_mode_blocked(self) -> None:
        ext = p172.evaluate_c2pa_signing_firewall(extract_sigcert_p12=True)
        self.assertFalse(ext.admitted)
        self.assertTrue(ext.firewall_blocked)
        self.assertEqual(ext.status_code, "BLOCKED_SIGCERT_P12_EXTRACTION_DENIED")

        unk = p172.evaluate_c2pa_signing_firewall(signing_mode="FORGED_X509_INJECT")
        self.assertFalse(unk.admitted)
        self.assertTrue(unk.firewall_blocked)
        self.assertEqual(unk.status_code, "BLOCKED_UNSUPPORTED_C2PA_SIGNING_MODE")

    def test_15_pillar_a_aggregate_passes(self) -> None:
        pa = p172.evaluate_pillar_a_c2pa_lock_and_firewall()
        self.assertTrue(pa["passed"])


class TestStage30PillarBVmcBncm1LtcAndUartInterlock(unittest.TestCase):
    """Pillar B — VMC-BNCM1 EXT-LK SMPTE-12M LTC-IN, User-Bits & Multi-USB UART interlock."""

    def test_16_all_five_smpte_framerates_jam_sync_with_user_bits_and_zero_slip(self) -> None:
        for fps in ("23.98", "24", "25", "29.97", "59.94"):
            res = p172.simulate_vmc_bncm1_ltc_jam_sync(
                fps_label=fps,
                ltc_vpp_mv=2200,
                user_bits_hex="CAFE1720",
            )
            self.assertTrue(res.valid, msg=f"fps={fps}")
            self.assertEqual(res.adapter_name, "VMC-BNCM1")
            self.assertEqual(res.ad_jack_in_pin, 10)
            self.assertEqual(res.id_resistor_ohm, 680_000)
            self.assertEqual(res.ltc_sync_word_hex, "0x3ffd")
            self.assertEqual(res.user_bits_hex, "0xCAFE1720")
            self.assertTrue(res.ub_preserved)
            self.assertEqual(res.frame_slip, 0)
            self.assertEqual(res.tc_direction, "IN")
            self.assertTrue(res.fx6_tc_out_bnc_masked)
            self.assertFalse(res.multi_usb_uart_1v8_active)
            self.assertEqual(res.uart_contention_damage_events, 0)
            self.assertEqual(res.over_voltage_damage_events, 0)

    def test_17_ltc_voltage_boundaries_0v5_to_4v5_accepted_and_gt5v_rejected(self) -> None:
        self.assertTrue(p172.simulate_vmc_bncm1_ltc_jam_sync(ltc_vpp_mv=500).valid)
        self.assertTrue(p172.simulate_vmc_bncm1_ltc_jam_sync(ltc_vpp_mv=4500).valid)

        ovp = p172.simulate_vmc_bncm1_ltc_jam_sync(ltc_vpp_mv=5001)
        self.assertFalse(ovp.valid)
        self.assertEqual(ovp.over_voltage_damage_events, 0)
        self.assertEqual(ovp.status_code, "BLOCKED_LTC_OVERVOLTAGE_GT_5V")

        mid_high = p172.simulate_vmc_bncm1_ltc_jam_sync(ltc_vpp_mv=4800)
        self.assertFalse(mid_high.valid)
        self.assertEqual(mid_high.status_code, "BLOCKED_LTC_VOLTAGE_OUT_OF_RANGE_0V5_4V5")

        low = p172.simulate_vmc_bncm1_ltc_jam_sync(ltc_vpp_mv=400)
        self.assertFalse(low.valid)
        self.assertEqual(low.status_code, "BLOCKED_LTC_VOLTAGE_OUT_OF_RANGE_0V5_4V5")

    def test_18_wrong_vmc_bncm1_id_resistor_rejected(self) -> None:
        bad_id = p172.simulate_vmc_bncm1_ltc_jam_sync(id_resistor_ohm=100_000)
        self.assertFalse(bad_id.valid)
        self.assertEqual(bad_id.status_code, "BLOCKED_VMC_BNCM1_ID_RESISTOR_MISMATCH")

    def test_19_multi_usb_1v8_uart_contention_interlock_trips_fail_closed(self) -> None:
        clash = p172.simulate_vmc_bncm1_ltc_jam_sync(multi_usb_uart_1v8_requested=True)
        self.assertFalse(clash.valid)
        self.assertFalse(clash.multi_usb_uart_1v8_active)
        self.assertEqual(clash.uart_contention_damage_events, 0)
        self.assertEqual(clash.status_code, "BLOCKED_MULTI_USB_1V8_UART_CONTENTION")

    def test_20_fx6_tc_out_bnc_drive_masked_fail_closed(self) -> None:
        tc_out = p172.simulate_vmc_bncm1_ltc_jam_sync(tc_out_bnc_drive_requested=True)
        self.assertFalse(tc_out.valid)
        self.assertTrue(tc_out.fx6_tc_out_bnc_masked)
        self.assertEqual(tc_out.tc_direction, "IN")
        self.assertEqual(tc_out.status_code, "BLOCKED_FX6_TC_OUT_BNC_MASKED")

    def test_21_invalid_fps_or_user_bits_raises_value_error(self) -> None:
        with self.assertRaises(p172.RealHwC2paTcGyroPrebenchError):
            p172.simulate_vmc_bncm1_ltc_jam_sync(fps_label="48.00")
        with self.assertRaises(p172.RealHwC2paTcGyroPrebenchError):
            p172.simulate_vmc_bncm1_ltc_jam_sync(user_bits_hex="ZZZZ")

    def test_22_pillar_b_aggregate_passes(self) -> None:
        pb = p172.evaluate_pillar_b_vmc_bncm1_ltc_interlock()
        self.assertTrue(pb["passed"])


class TestStage30PillarCImx510GyroP18NrtmPipeline(unittest.TestCase):
    """Pillar C — IMX510 8.7 ms + 6-axis IMU + p18:/lens NonRealTimeMeta.xml pipeline."""

    def test_23_xavc_si_mp4_and_xavc_i_mxf_nrtm_catalyst_resolve_valid(self) -> None:
        si = p172.simulate_imx510_gyro_nrtm_clip(clip_format="XAVC S-I", fps_label="23.98", focal_length_mm=24.0)
        self.assertTrue(si.valid)
        self.assertEqual(si.container, "MP4")
        self.assertEqual(si.sensor_name, "IMX510")
        self.assertAlmostEqual(si.readout_ms, 8.7)
        self.assertEqual(si.imu_axes, 6)
        self.assertEqual(si.imu_sample_rate_hz, 2000)
        self.assertGreater(si.imu_samples_total, 1500)
        self.assertTrue(si.monotonically_increasing_timestamps)
        self.assertTrue(si.crc32_valid)
        self.assertTrue(si.catalyst_schema_valid)
        self.assertTrue(si.resolve_schema_valid)
        self.assertEqual(si.p2_mutation_bytes, 0)
        self.assertEqual(si.p18_mutation_bytes, 0)
        self.assertEqual(si.p18_mount_flags, "MS_RDONLY")

        mxf = p172.simulate_imx510_gyro_nrtm_clip(clip_format="XAVC-I", fps_label="59.94", focal_length_mm=50.0)
        self.assertTrue(mxf.valid)
        self.assertEqual(mxf.container, "MXF")
        self.assertTrue(mxf.catalyst_schema_valid)
        self.assertTrue(mxf.resolve_schema_valid)

    def test_24_build_and_validate_nrtm_xml_roundtrip(self) -> None:
        ok, xml_bytes_len = p172.build_and_validate_nrtm_xml(
            clip_format="XAVC S-I",
            fps_label="23.98",
            focal_length_mm=35.0,
            frames_recorded=24,
            imu_samples_total=2002,
            readout_ms=8.7,
            user_bits_hex="0xA3F12026",
            ibis_center_lock=True,
        )
        self.assertTrue(ok)
        self.assertGreater(xml_bytes_len, 400)

    def test_25_p18_and_p2_write_requests_blocked_fail_closed(self) -> None:
        b18 = p172.simulate_imx510_gyro_nrtm_clip(p18_write_requested=True)
        self.assertFalse(b18.valid)
        self.assertEqual(b18.p18_mutation_bytes, 0)
        self.assertEqual(b18.status_code, "BLOCKED_P2_OR_P18_WRITE_REQUEST")

        b2 = p172.simulate_imx510_gyro_nrtm_clip(p2_write_requested=True)
        self.assertFalse(b2.valid)
        self.assertEqual(b2.p2_mutation_bytes, 0)
        self.assertEqual(b2.status_code, "BLOCKED_P2_OR_P18_WRITE_REQUEST")

    def test_26_gyro_crc_fault_and_non_monotonic_timestamp_and_readout_drift_blocked(self) -> None:
        crc_bad = p172.simulate_imx510_gyro_nrtm_clip(inject_imu_crc_fault=True)
        self.assertFalse(crc_bad.valid)
        self.assertFalse(crc_bad.crc32_valid)
        self.assertFalse(crc_bad.catalyst_schema_valid)
        self.assertEqual(crc_bad.status_code, "BLOCKED_GYRO_CRC32_CORRUPTION")

        ts_bad = p172.simulate_imx510_gyro_nrtm_clip(inject_timestamp_backwards=True)
        self.assertFalse(ts_bad.valid)
        self.assertFalse(ts_bad.monotonically_increasing_timestamps)
        self.assertEqual(ts_bad.status_code, "BLOCKED_GYRO_TIMESTAMP_NON_MONOTONIC")

        rs_bad = p172.simulate_imx510_gyro_nrtm_clip(readout_ms=14.2)
        self.assertFalse(rs_bad.valid)
        self.assertEqual(rs_bad.status_code, "BLOCKED_IMX510_READOUT_MISMATCH")

    def test_27_invalid_clip_format_or_fps_raises(self) -> None:
        with self.assertRaises(p172.RealHwC2paTcGyroPrebenchError):
            p172.simulate_imx510_gyro_nrtm_clip(clip_format="PRORES_RAW")
        with self.assertRaises(p172.RealHwC2paTcGyroPrebenchError):
            p172.simulate_imx510_gyro_nrtm_clip(fps_label="120")

    def test_28_pillar_c_aggregate_passes(self) -> None:
        pc = p172.evaluate_pillar_c_imx510_gyro_nrtm()
        self.assertTrue(pc["passed"])


class TestStage30PillarD10StepPrebenchGonogoLifecycle(unittest.TestCase):
    """Pillar D — Complete 10-step pre-bench operator Go/No-Go dry-run lifecycle."""

    def test_29_clean_10step_prebench_dryrun_completes_16of16_h0_eq_h3_with_zero_writes(self) -> None:
        res = p172.run_10step_prebench_gonogo_lifecycle()
        self.assertTrue(res.valid)
        self.assertEqual(res.steps_completed, 10)
        self.assertEqual(res.steps_total, 10)
        self.assertEqual(len(res.steps), 10)
        self.assertTrue(all(s.passed for s in res.steps))
        self.assertEqual(res.usb_vid_msc, "0x054C")
        self.assertEqual(res.usb_pid_msc, "0x0DA1")
        self.assertEqual(res.usb_pid_ufu, "0x0336")
        self.assertEqual(res.ufu_canary_opcode_hex, "0xFF")
        self.assertEqual(res.stage_b_target_partition, "/dev/cnflasha15")
        self.assertEqual(res.surfaces_total, 16)
        self.assertEqual(res.surfaces_h0_eq_h3, 16)
        self.assertEqual(res.dryrun_go_nogo, "GO_DRYRUN_HIL")
        self.assertTrue(res.dryrun_hil_coemulation_passed)
        self.assertFalse(res.physical_camera_bench_attached)
        self.assertFalse(res.persistent_emmc_writes_authorized)
        self.assertEqual(res.emmc_nflasha_write_count, 0)
        self.assertEqual(res.c2pa_cert_mutation_bytes, 0)
        self.assertEqual(res.p2_mutation_bytes, 0)
        self.assertEqual(res.p18_mutation_bytes, 0)
        self.assertEqual(res.cp_mutation_bytes, 0)
        self.assertEqual(res.otp_write_count, 0)
        self.assertEqual(res.rpmb_write_count, 0)
        self.assertEqual(res.status_code, "PREBENCH_10STEP_DRYRUN_GO_HIL")

    def test_30_incomplete_tier0_backup_forces_no_go(self) -> None:
        res = p172.run_10step_prebench_gonogo_lifecycle(tier0_backup_complete=False)
        self.assertFalse(res.valid)
        self.assertEqual(res.dryrun_go_nogo, "NO_GO")
        self.assertLess(res.steps_completed, 10)
        self.assertFalse(res.steps[2].passed)  # step 3: Tier-0 backup
        self.assertFalse(res.steps[4].passed)  # step 5: cnflasha15 staging blocked

    def test_31_h3_surface_drift_forces_no_go(self) -> None:
        for surf in ("p12", "p15", "p18"):
            res = p172.run_10step_prebench_gonogo_lifecycle(corrupt_h3_surface=surf)
            self.assertFalse(res.valid, msg=surf)
            self.assertEqual(res.surfaces_h0_eq_h3, 15)
            self.assertEqual(res.dryrun_go_nogo, "NO_GO")
            self.assertFalse(res.steps[9].passed)

    def test_32_residual_orig_tmp_or_p6_forces_no_go(self) -> None:
        for kwargs in (
            {"orig_residual_count": 1},
            {"tmp_jiritsu_residual_count": 1},
            {"p6_chunk_residual_count": 1},
        ):
            res = p172.run_10step_prebench_gonogo_lifecycle(**kwargs)
            self.assertFalse(res.valid, msg=str(kwargs))
            self.assertEqual(res.dryrun_go_nogo, "NO_GO")
            self.assertFalse(res.steps[8].passed)
            self.assertFalse(res.steps[9].passed)

    def test_33_persistent_emmc_write_authorization_blocked_fail_closed(self) -> None:
        res = p172.run_10step_prebench_gonogo_lifecycle(authorize_persistent_emmc_writes=True)
        self.assertFalse(res.valid)
        self.assertEqual(res.dryrun_go_nogo, "NO_GO")
        self.assertFalse(res.persistent_emmc_writes_authorized)
        self.assertEqual(res.emmc_nflasha_write_count, 0)
        self.assertEqual(res.status_code, "NO_GO_BLOCKED_PERSISTENT_EMMC_WRITE_REQUEST")

    def test_34_pillar_d_aggregate_passes(self) -> None:
        pd = p172.evaluate_pillar_d_10step_prebench_lifecycle()
        self.assertTrue(pd["passed"])


class TestStage30CliSuite30of30AndHygiene(unittest.TestCase):
    """CLI self-test, 30/30 milestone suite orchestration, runtime budget & BYOF hygiene."""

    def test_35_standalone_cli_clean_room_summary_and_json(self) -> None:
        buf_sum = io.StringIO()
        with contextlib.redirect_stdout(buf_sum):
            rc = p172.main(["--clean-room", "--summary"])
        self.assertEqual(rc, 0)
        out = buf_sum.getvalue()
        self.assertIn("[PASS] Phase 172 Stage 30 (30/30)", out)
        self.assertIn("mode=CLEAN_ROOM_SYNTHETIC", out)
        self.assertIn("steps=10/10", out)
        self.assertIn("h0_eq_h3=16/16", out)
        self.assertIn("go=GO_DRYRUN_HIL", out)

        buf_json = io.StringIO()
        with contextlib.redirect_stdout(buf_json):
            rc2 = p172.main(["--clean-room", "--json"])
        self.assertEqual(rc2, 0)
        data = json.loads(buf_json.getvalue())
        self.assertEqual(data["schema"], p172.PHASE_172_SCHEMA)
        self.assertEqual(data["stage_index"], 30)
        self.assertEqual(data["stage_total"], 30)
        self.assertEqual(data["milestone"], "30/30")
        self.assertTrue(data["all_checks_passed"])

    def test_36_standalone_cli_subprocess_default_mode(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                str(FX3_VM_DIR / "realhw_c2pa_tc_gyro_and_prebench_gonogo_coemulator.py"),
                "--self-test",
                "--json",
            ],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        parsed = json.loads(proc.stdout)
        self.assertTrue(parsed["all_checks_passed"])
        self.assertEqual(parsed["milestone"], "30/30")

    def test_37_invalid_cli_flag_exits_nonzero(self) -> None:
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as ctx:
                p172.main(["--no-such-phase172-flag"])
            self.assertNotEqual(ctx.exception.code, 0)

    def test_38_suite_in_process_30_of_30_stages_and_skip_phase172_config(self) -> None:
        rep_on = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig(force_clean_room=True))
        self.assertTrue(rep_on["all_checks_passed"])
        self.assertIn("stage30_realhw_c2pa_tc_gyro_prebench_hil", rep_on)
        s30 = rep_on["stage30_realhw_c2pa_tc_gyro_prebench_hil"]
        self.assertTrue(s30["all_checks_passed"])
        self.assertEqual(s30["c2pa_cert_mutation_bytes"], 0)
        self.assertEqual(s30["p12_cert_mount_flags"], "MS_RDONLY")
        self.assertEqual(s30["p2_mutation_bytes"], 0)
        self.assertEqual(s30["p18_mutation_bytes"], 0)
        self.assertEqual(s30["cp_mutation_bytes"], 0)
        self.assertEqual(s30["emmc_nflasha_write_count"], 0)
        self.assertFalse(s30["persistent_emmc_writes_authorized"])

        stage_keys = [k for k in rep_on if re.match(r"^stage\d+_", k)]
        self.assertGreaterEqual(len(stage_keys), 30)

        rep_skip = suite.run_fx3_vm_coemulation_suite(
            suite.CoEmulationConfig(
                force_clean_room=True,
                include_phase172_realhw_c2pa_tc_gyro_prebench_hil=False,
            )
        )
        self.assertTrue(rep_skip["all_checks_passed"])
        self.assertNotIn("stage30_realhw_c2pa_tc_gyro_prebench_hil", rep_skip)
        self.assertEqual(len([k for k in rep_skip if re.match(r"^stage\d+_", k)]), len(stage_keys) - 1)

    def test_39_suite_subprocess_summary_and_skip_phase172_flag(self) -> None:
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
        self.assertIn("realhw_c2pa_tc_gyro_prebench_hil=CLEAN_ROOM_SYNTHETIC", proc.stdout)

        proc_skip = subprocess.run(
            [
                sys.executable,
                "-B",
                str(FX3_VM_DIR / "fx3_vm_coemulation_suite.py"),
                "--clean-room",
                "--skip-phase172",
                "--summary",
            ],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc_skip.returncode, 0, msg=proc_skip.stderr)
        self.assertNotIn("realhw_c2pa_tc_gyro_prebench_hil=", proc_skip.stdout)

    def test_40_suite_30_stages_clean_room_lt_1p3s_and_local_lt_2p7s_and_json_cli(self) -> None:
        t0 = time.monotonic()
        rep_clean = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig(force_clean_room=True))
        dt_clean = time.monotonic() - t0
        self.assertTrue(rep_clean["all_checks_passed"])
        self.assertGreaterEqual(len([k for k in rep_clean if re.match(r"^stage\d+_", k)]), 30)
        self.assertLess(dt_clean, 1.30)

        t1 = time.monotonic()
        rep_mode = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig())
        dt_mode = time.monotonic() - t1
        self.assertTrue(rep_mode["all_checks_passed"])
        self.assertGreaterEqual(len([k for k in rep_mode if re.match(r"^stage\d+_", k)]), 30)
        self.assertLess(dt_mode, 2.70)

        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        p_clean = subprocess.run(
            [
                sys.executable,
                "-B",
                str(FX3_VM_DIR / "fx3_vm_coemulation_suite.py"),
                "--clean-room",
                "--json",
            ],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(p_clean.returncode, 0, msg=p_clean.stderr)
        d_clean = json.loads(p_clean.stdout)
        self.assertTrue(d_clean["all_checks_passed"])
        self.assertGreaterEqual(len([k for k in d_clean if re.match(r"^stage\d+_", k)]), 30)

    def test_41_all_30_of_30_stages_present_and_passing_in_suite_report(self) -> None:
        rep = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig(force_clean_room=True))
        self.assertTrue(rep["stage1_coldboot_and_bt"]["all_checks_passed"])
        self.assertTrue(rep["stage2_dual_isa_cp_shooting"]["all_checks_passed"])
        self.assertTrue(rep["stage3_soft_gpe_hud_ramfb"]["all_checks_passed"])
        for idx in range(4, 31):
            matches = [k for k in rep if k.startswith(f"stage{idx}_")]
            self.assertEqual(len(matches), 1, msg=f"Missing or duplicate stage{idx}_* key")
            self.assertTrue(rep[matches[0]]["all_checks_passed"])

    def test_42_stage30_no_raw_bytes_repr_or_nan_in_json(self) -> None:
        rep = _get_clean_room_audit()
        rendered = json.dumps(rep, allow_nan=False)
        self.assertNotRegex(rendered, r"(?<![0-9A-Za-z_/.-])b[\'\"]")
        self.assertIsNone(re.search(r"NaN|Infinity", rendered))

        rep_suite = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig(force_clean_room=True))
        rendered_suite = json.dumps(rep_suite, allow_nan=False)
        self.assertNotRegex(rendered_suite, r"(?<![0-9A-Za-z_/.-])b[\'\"]")
        self.assertIsNone(re.search(r"NaN|Infinity", rendered_suite))

    def test_43_source_hygiene_o_rdonly_and_no_write_flags_or_forbidden_port(self) -> None:
        src = (FX3_VM_DIR / "realhw_c2pa_tc_gyro_and_prebench_gonogo_coemulator.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("os.O_RDONLY", src)
        self.assertNotIn("os.O_WRONLY", src)
        self.assertNotIn("os.O_RDWR", src)
        self.assertNotIn("87" + "68", src)
        self.assertIn("sys.dont_write_bytecode = True", src)

    def test_44_audit_digest_sha256_deterministic_across_repeated_runs(self) -> None:
        r1 = p172.run_phase172_realhw_c2pa_tc_gyro_prebench_hil(force_clean_room=True)
        r2 = p172.run_phase172_realhw_c2pa_tc_gyro_prebench_hil(force_clean_room=True)
        self.assertEqual(len(r1["audit_digest_sha256"]), 64)
        self.assertEqual(r1["audit_digest_sha256"], r2["audit_digest_sha256"])

    def test_45_suite_audit_digest_matches_recomputed_sha256(self) -> None:
        rep = dict(suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig(force_clean_room=True)))
        recorded = rep.pop("audit_digest_sha256")
        expected = hashlib.sha256(
            json.dumps(rep, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        self.assertEqual(recorded, expected)

    def test_46_nrtm_xml_namespace_constant_matches_sony_ver_2_20(self) -> None:
        self.assertEqual(
            p172.NRTM_XML_NAMESPACE,
            "urn:schemas-professionalDisc:nonRealTimeMeta:ver.2.20",
        )
        # Verify ElementTree parses clean XML namespace without error
        ns = p172.NRTM_XML_NAMESPACE
        root = ET.Element(f"{{{ns}}}NonRealTimeMeta")
        self.assertEqual(root.tag, f"{{{ns}}}NonRealTimeMeta")


if __name__ == "__main__":
    unittest.main()
