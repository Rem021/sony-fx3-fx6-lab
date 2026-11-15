"""Phase 146 Dual-Mode Unit Tests (46 tests): Real-Hardware Stage-B Peripheral Bridge Auditor —
E-Mount Lens & `p18:/lens`, 5-Axis IBIS vs Catalyst Gyro, MI-Shoe `XLR-H1` 4ch Audio,
and HDMI Type-A / Multi-USB `TC-IN` vs `12G-SDI` / `BNC`.
"""

from __future__ import annotations

import ast
import io
import json
import os
import re
import time
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

import fx3_firmware_lab as lab
from fx3_firmware_lab.__main__ import main as cli_main, run_audit_all
from fx3_firmware_lab.realhw_lens_ibis_audio_hdmi_peripheral_bridge_auditor import (
    AUDIO_APPFW_FX3_MARKERS,
    AUDIO_APPFW_FX6_MARKERS,
    AUDIO_LPCM_4CH_BPS,
    AUDIO_LPCM_4CH_COUNT,
    AUDIO_LPCM_BIT_DEPTH,
    AUDIO_LPCM_SAMPLE_RATE_HZ,
    AVBBC_BRIDGE_SYMBOLS,
    AVBB_AUDIO_MARKERS,
    BRIDGE_CLASS_HARD_WRITE_PROTECTED,
    BRIDGE_CLASS_MASKED_ABSENT_HW,
    BRIDGE_CLASS_NATIVE_PASSTHROUGH,
    BRIDGE_CLASS_SHIM_TRANSLATED,
    CATALYST_IMU_SAMPLE_RATE_HZ,
    EXPECTED_LENS_COMM_BYTES,
    EXPECTED_LENS_COMM_EXPORTS,
    EXPECTED_LENS_COMM_IMPORTS,
    EXPECTED_SENCORE_EXPORTS,
    EXPECTED_SENCORE_IMPORTS,
    FX6_ABSENT_HW_PERIPHERALS,
    FX6_RIGID_SENSOR_PARAM,
    HDMI_APPFW_FX3_MARKERS,
    HDMI_SDI_APPFW_FX6_MARKERS,
    HDMI_TYPE_A_CAPABILITIES,
    HOTSHOE_E_TMO,
    HOTSHOE_MARKERS,
    HOTSHOE_NONBLOCK_SAFE_RC,
    IBIS_APPFW_FX3_MARKERS,
    IBIS_APPFW_FX6_MARKERS,
    IBIS_CENTER_LOCK_CMD_OPCODE,
    IBIS_CENTER_LOCK_DONE_OPCODE,
    IBIS_CP_SHARED_MARKERS,
    IBIS_MODES_FX3,
    IBIS_MODES_FX6_UI,
    IBIS_MPR_GYRO_FX3_MARKERS,
    IBIS_MPR_GYRO_FX6_MARKERS,
    LENS_APPFW_FX3_MARKERS,
    LENS_APPFW_FX6_MARKERS,
    P11_HOTSHOE_ATTACHED_EVT,
    P11_HOTSHOE_DETACHED_EVT,
    P11_RTC_UDATE_QUEUE_ID,
    P11_SMART_HANDLE_QUEUE_ID,
    P18_FX3_SECTORS,
    P18_FX3_START_LBA,
    P18_FX6_START_LBA,
    P18_LENS_CALIB_FILE,
    P18_LENS_MOUNT_PATH,
    P18_LENS_PARTITION_DEVICE,
    PHASE_146_SCHEMA,
    PHASE_146_VERSION,
    SENCORE_SHARED_MARKERS,
    UART_BOOT_SHARED_PINS,
    VALID_AUDIO_HANDLE_STATES,
    VALID_BRIDGE_CLASSES,
    VALID_FOCUS_DISTANCE_UNITS,
    VALID_IRIS_DISPLAY_UNITS,
    VMC_BNCM1_ID_OHM,
    VMC_BNCM1_ID_PIN,
    VMC_BNCM1_LTC_PIN,
    analyze_realhw_lens_ibis_audio_hdmi_peripheral_bridge,
    build_clean_room_realhw_peripheral_bridge_fixtures,
    build_phase146_compatibility_matrix,
    evaluate_emount_lens_p18_bridge,
    evaluate_hdmi_sdi_tc_bridge,
    evaluate_ibis_vs_catalyst_bridge,
    evaluate_mishoe_xlrh1_audio_bridge,
    evaluate_phase146_write_guard,
    realhw_lens_ibis_audio_hdmi_peripheral_bridge_report_to_dict,
)


_BYTES_REPR_RE = re.compile(r"(?<![0-9A-Za-z_/.-])b['\"]")
_AUDITOR_PATH = (
    Path(__file__).resolve().parent.parent
    / "fx3_firmware_lab"
    / "realhw_lens_ibis_audio_hdmi_peripheral_bridge_auditor.py"
)


class TestRealhwLensIbisAudioHdmiPeripheralBridge(unittest.TestCase):
    """Comprehensive dual-mode tests (46 tests) for the 29th unified auditor."""

    # ---- Mode, Runtime, Determinism & Structural Hygiene ----

    def test_01_clean_room_report_all_pillars_and_runtime(self) -> None:
        t0 = time.perf_counter()
        rep = analyze_realhw_lens_ibis_audio_hdmi_peripheral_bridge(clean_room=True)
        dt_cold = time.perf_counter() - t0
        t1 = time.perf_counter()
        rep_warm = analyze_realhw_lens_ibis_audio_hdmi_peripheral_bridge(clean_room=True)
        dt_warm = time.perf_counter() - t1

        self.assertTrue(rep.all_checks_passed, rep.errors)
        self.assertEqual(rep.mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(rep.schema_version, PHASE_146_SCHEMA)
        self.assertEqual(rep.phase_version, PHASE_146_VERSION)
        self.assertTrue(rep.o_rdonly_enforced)
        self.assertFalse(rep.p18_lens_writes_permitted)
        self.assertTrue(rep.ibis_coil_safe_park_verified)
        self.assertTrue(rep.sdi_blocking_wait_eliminated)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertEqual(rep.emmc_mutation_bytes, 0)
        self.assertEqual(rep.calibration_mutation_bytes, 0)
        self.assertTrue(rep.pillar1_lens_p18.passed)
        self.assertTrue(rep.pillar2_ibis_catalyst.passed)
        self.assertTrue(rep.pillar3_audio_xlrh1.passed)
        self.assertTrue(rep.pillar4_hdmi_sdi_tc.passed)
        self.assertEqual(rep.report_sha256, rep_warm.report_sha256)
        self.assertEqual(len(rep.report_sha256), 64)
        self.assertLess(dt_cold, 0.25)
        self.assertLess(dt_warm, 0.10)

    def test_02_auto_mode_or_local_donor_runtime_under_1500ms(self) -> None:
        t0 = time.perf_counter()
        rep = analyze_realhw_lens_ibis_audio_hdmi_peripheral_bridge()
        dt = time.perf_counter() - t0
        self.assertTrue(rep.all_checks_passed, rep.errors)
        self.assertIn(rep.mode, ("LOCAL_DONOR_VERIFIED", "CLEAN_ROOM_SYNTHETIC"))
        self.assertLess(dt, 1.5)
        if rep.mode == "LOCAL_DONOR_VERIFIED":
            self.assertEqual(rep.donor_file_sizes.get("fx3_lens_comm"), EXPECTED_LENS_COMM_BYTES)
            self.assertEqual(rep.donor_file_sizes.get("fx6_lens_comm"), EXPECTED_LENS_COMM_BYTES)
            self.assertEqual(rep.donor_file_sizes.get("fx3_sencore"), 377_328)
            self.assertEqual(rep.donor_file_sizes.get("fx6_sencore"), 401_952)
            self.assertEqual(rep.donor_file_sizes.get("fx3_appfw"), 79_015_712)
            self.assertEqual(rep.donor_file_sizes.get("fx6_appfw"), 50_520_424)
            self.assertEqual(rep.donor_file_sizes.get("fx6_hotshoe"), 47_808)
            self.assertEqual(rep.donor_file_sizes.get("fx6_avbb_audio"), 70_096)

    def test_03_forced_clean_room_env_flag_respected(self) -> None:
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}, clear=False):
            rep = analyze_realhw_lens_ibis_audio_hdmi_peripheral_bridge()
        self.assertTrue(rep.all_checks_passed, rep.errors)
        self.assertEqual(rep.mode, "CLEAN_ROOM_SYNTHETIC")

    def test_04_missing_donor_falls_back_to_clean_room(self) -> None:
        with mock.patch(
            "fx3_firmware_lab.realhw_lens_ibis_audio_hdmi_peripheral_bridge_auditor.resolve_donor_file",
            return_value=None,
        ):
            rep = analyze_realhw_lens_ibis_audio_hdmi_peripheral_bridge(clean_room=False)
        self.assertTrue(rep.all_checks_passed, rep.errors)
        self.assertEqual(rep.mode, "CLEAN_ROOM_SYNTHETIC")

    def test_05_json_serialization_has_zero_bytes_repr(self) -> None:
        rep = analyze_realhw_lens_ibis_audio_hdmi_peripheral_bridge(clean_room=True)
        payload = realhw_lens_ibis_audio_hdmi_peripheral_bridge_report_to_dict(rep)
        json_str = json.dumps(payload, sort_keys=True)
        self.assertIsNone(_BYTES_REPR_RE.search(json_str), "Unexpected Python bytes repr in JSON")
        self.assertIn(PHASE_146_SCHEMA, json_str)

    def test_06_auditor_source_strictly_uses_os_o_rdonly_and_mmap_access_read(self) -> None:
        src = _AUDITOR_PATH.read_text(encoding="utf-8")
        self.assertIn("os.O_RDONLY", src)
        self.assertIn("mmap.ACCESS_READ", src)
        for forbidden in (
            "os.O_WRONLY",
            "os.O_RDWR",
            "os.O_CREAT",
            "mmap.ACCESS_WRITE",
            ".write_bytes(",
            ".write_text(",
        ):
            self.assertNotIn(forbidden, src)
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr in (
                "O_WRONLY",
                "O_RDWR",
                "O_CREAT",
                "ACCESS_WRITE",
            ):
                self.fail(f"Forbidden write attribute {node.attr} in auditor AST")

    def test_07_package_exports_and_all_include_phase146_symbols(self) -> None:
        expected_symbols = (
            "PHASE_146_SCHEMA",
            "PHASE_146_VERSION",
            "BRIDGE_CLASS_NATIVE_PASSTHROUGH",
            "BRIDGE_CLASS_SHIM_TRANSLATED",
            "BRIDGE_CLASS_MASKED_ABSENT_HW",
            "BRIDGE_CLASS_HARD_WRITE_PROTECTED",
            "VALID_BRIDGE_CLASSES",
            "P18_LENS_PARTITION_DEVICE",
            "P18_LENS_CALIB_FILE",
            "IBIS_CENTER_LOCK_CMD_OPCODE",
            "IBIS_CENTER_LOCK_DONE_OPCODE",
            "AUDIO_LPCM_4CH_BPS",
            "HOTSHOE_E_TMO",
            "HOTSHOE_NONBLOCK_SAFE_RC",
            "VMC_BNCM1_ID_OHM",
            "FX6_ABSENT_HW_PERIPHERALS",
            "RealhwLensIbisAudioHdmiPeripheralBridgeReport",
            "analyze_realhw_lens_ibis_audio_hdmi_peripheral_bridge",
            "build_clean_room_realhw_peripheral_bridge_fixtures",
            "build_phase146_compatibility_matrix",
            "evaluate_emount_lens_p18_bridge",
            "evaluate_ibis_vs_catalyst_bridge",
            "evaluate_mishoe_xlrh1_audio_bridge",
            "evaluate_hdmi_sdi_tc_bridge",
            "evaluate_phase146_write_guard",
            "realhw_lens_ibis_audio_hdmi_peripheral_bridge_report_to_dict",
        )
        for sym in expected_symbols:
            self.assertTrue(hasattr(lab, sym), f"Missing export {sym} on fx3_firmware_lab")
            self.assertIn(sym, lab.__all__, f"Missing {sym} in fx3_firmware_lab.__all__")

    def test_08_clean_room_fixtures_roundtrip_and_counts(self) -> None:
        fx = build_clean_room_realhw_peripheral_bridge_fixtures()
        self.assertEqual(len(fx), 16)
        for key, buf in fx.items():
            self.assertIsInstance(buf, bytes, key)
            self.assertGreater(len(buf), 64, key)

    def test_09_cli_audit_realhw_peripheral_bridge_clean_room_and_auto(self) -> None:
        for argv in (
            ["audit-realhw-peripheral-bridge", "--clean-room", "--json"],
            ["audit-realhw-peripheral-bridge", "--json"],
        ):
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = cli_main(argv)
            self.assertEqual(rc, 0)
            obj = json.loads(buf.getvalue())
            self.assertTrue(obj["all_checks_passed"])
            self.assertTrue(obj["o_rdonly_enforced"])
            self.assertFalse(obj["p18_lens_writes_permitted"])
            self.assertTrue(obj["ibis_coil_safe_park_verified"])
            self.assertTrue(obj["sdi_blocking_wait_eliminated"])
            self.assertFalse(obj["persistent_emmc_writes_authorized"])

    def test_10_run_audit_all_reaches_at_least_29_auditors(self) -> None:
        summary = run_audit_all(clean_room=True)
        self.assertTrue(summary["all_checks_passed"])
        audit_keys = [k for k in summary if k.endswith("_audit")]
        self.assertGreaterEqual(len(audit_keys), 29)
        self.assertIn("realhw_lens_ibis_audio_hdmi_peripheral_bridge_audit", summary)

    def test_11_cli_audit_all_clean_room_returns_zero_with_at_least_29_keys(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cli_main(["audit-all", "--clean-room", "--json"])
        self.assertEqual(rc, 0)
        obj = json.loads(buf.getvalue())
        self.assertTrue(obj["all_checks_passed"])
        self.assertGreaterEqual(len([k for k in obj if k.endswith("_audit")]), 29)

    # ---- Pillar 1: E-Mount Lens & p18:/lens Calibration ----

    def test_12_pillar1_lens_comm_and_sencore_abi_identical(self) -> None:
        rep = analyze_realhw_lens_ibis_audio_hdmi_peripheral_bridge(clean_room=True)
        p1 = rep.pillar1_lens_p18
        self.assertTrue(p1.passed)
        self.assertTrue(p1.lens_comm_exports_identical)
        self.assertEqual(p1.fx3_lens_comm.export_count, EXPECTED_LENS_COMM_EXPORTS)
        self.assertEqual(p1.fx3_lens_comm.import_count, EXPECTED_LENS_COMM_IMPORTS)
        self.assertTrue(p1.sencore_exports_identical)
        self.assertEqual(p1.fx3_sencore.export_count, EXPECTED_SENCORE_EXPORTS)
        self.assertEqual(p1.fx3_sencore.import_count, EXPECTED_SENCORE_IMPORTS)
        self.assertEqual(p1.fx3_appfw_lens_marker_hits, len(LENS_APPFW_FX3_MARKERS))
        self.assertEqual(p1.fx6_appfw_lens_marker_hits, len(LENS_APPFW_FX6_MARKERS))
        self.assertEqual(p1.p18_fx3_lba_hex, f"0x{P18_FX3_START_LBA:08x}")
        self.assertEqual(p1.p18_fx6_lba_hex, f"0x{P18_FX6_START_LBA:08x}")
        self.assertFalse(p1.p18_lens_writes_permitted)

    def test_13_pillar1_eval_emount_lens_tstop_fstop_meter_feet_positive(self) -> None:
        for ap in VALID_IRIS_DISPLAY_UNITS:
            for fd in VALID_FOCUS_DISTANCE_UNITS:
                res = evaluate_emount_lens_p18_bridge(
                    lens_mounted=True,
                    focal_length_mm=35.0,
                    aperture_display_unit=ap,
                    focus_distance_unit=fd,
                    breathing_comp_enabled=(ap == "T_STOP"),
                )
                self.assertTrue(res.valid, (ap, fd, res.errors))
                self.assertEqual(res.status, "EMOUNT_LENS_P18_READONLY_VERIFIED")
                self.assertFalse(res.p18_lens_writes_permitted)
                self.assertFalse(res.write_attempt_blocked)

    def test_14_pillar1_eval_p18_write_attempt_hard_blocked(self) -> None:
        for target in (
            P18_LENS_PARTITION_DEVICE,
            P18_LENS_CALIB_FILE,
            f"{P18_LENS_MOUNT_PATH}/lensfile.bin",
            "p18:/lens/calib.dat",
        ):
            res = evaluate_emount_lens_p18_bridge(write_target=target)
            self.assertFalse(res.valid, target)
            self.assertEqual(res.status, "BLOCKED_P18_LENS_WRITE_PROTECTED")
            self.assertEqual(res.classification, BRIDGE_CLASS_HARD_WRITE_PROTECTED)
            self.assertFalse(res.p18_lens_writes_permitted)
            self.assertTrue(res.write_attempt_blocked)

    def test_15_pillar1_eval_invalid_iris_unit_distance_unit_or_focal_rejected(self) -> None:
        bad_ap = evaluate_emount_lens_p18_bridge(aperture_display_unit="INVALID_STOP")
        self.assertFalse(bad_ap.valid)
        self.assertEqual(bad_ap.status, "BLOCKED_INVALID_IRIS_DISPLAY_UNIT")

        bad_fd = evaluate_emount_lens_p18_bridge(focus_distance_unit="YARDS")
        self.assertFalse(bad_fd.valid)
        self.assertEqual(bad_fd.status, "BLOCKED_INVALID_FOCUS_DISTANCE_UNIT")

        bad_fl = evaluate_emount_lens_p18_bridge(lens_mounted=True, focal_length_mm=0.0)
        self.assertFalse(bad_fl.valid)
        self.assertEqual(bad_fl.status, "BLOCKED_INVALID_LENS_FOCAL_LENGTH_MM")

    def test_16_pillar1_unmounted_manual_lens_gracefully_supported(self) -> None:
        res = evaluate_emount_lens_p18_bridge(
            lens_mounted=False,
            focal_length_mm=0.0,
            aperture_display_unit="F_STOP",
            focus_distance_unit="METER",
            breathing_comp_enabled=False,
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.classification, BRIDGE_CLASS_NATIVE_PASSTHROUGH)
        self.assertFalse(res.p18_lens_writes_permitted)

    # ---- Pillar 2: 5-Axis Physical IBIS vs FX6 Gyro-Only Catalyst ----

    def test_17_pillar2_report_cp_liroseq_gyro_and_backup_parity(self) -> None:
        rep = analyze_realhw_lens_ibis_audio_hdmi_peripheral_bridge(clean_room=True)
        p2 = rep.pillar2_ibis_catalyst
        self.assertTrue(p2.passed)
        self.assertEqual(p2.fx3_appfw_ibis_marker_hits, len(IBIS_APPFW_FX3_MARKERS))
        self.assertEqual(p2.fx6_appfw_ibis_marker_hits, len(IBIS_APPFW_FX6_MARKERS))
        self.assertGreater(p2.fx3_cp_liroseq_hits, p2.fx6_cp_liroseq_hits)
        self.assertEqual(p2.fx3_mpr_gyro_hits, len(IBIS_MPR_GYRO_FX3_MARKERS))
        self.assertEqual(p2.fx6_mpr_gyro_hits, len(IBIS_MPR_GYRO_FX6_MARKERS))
        self.assertEqual(p2.fx3_backup_subsystems, 819)
        self.assertEqual(p2.fx6_backup_subsystems, 840)
        self.assertTrue(p2.fx3_backup_checksums_valid)
        self.assertTrue(p2.fx6_backup_checksums_valid)
        self.assertTrue(p2.ibis_coil_safe_park_verified)

    def test_18_pillar2_eval_off_center_lock_park_positive(self) -> None:
        res = evaluate_ibis_vs_catalyst_bridge(
            requested_mode="OFF",
            catalyst_gyro_metadata=True,
            park_coils_on_off=True,
            mask_rigid_sensor_query=True,
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.status, "IBIS_CATALYST_BRIDGE_VERIFIED")
        self.assertEqual(res.fx3_effective_mode, "OFF")
        self.assertTrue(res.coil_parked_center_lock)
        self.assertTrue(res.ibis_coil_safe_park_verified)
        self.assertTrue(res.gyro_rtmd_2000hz_active)
        self.assertEqual(res.nvs_calibration_writes, 0)
        self.assertEqual(IBIS_CENTER_LOCK_CMD_OPCODE, 0x0400)
        self.assertEqual(IBIS_CENTER_LOCK_DONE_OPCODE, 0x1400)
        self.assertEqual(CATALYST_IMU_SAMPLE_RATE_HZ, 2000)

    def test_19_pillar2_eval_standard_active_and_active_plus_clamp(self) -> None:
        for mode in IBIS_MODES_FX6_UI:
            res = evaluate_ibis_vs_catalyst_bridge(requested_mode=mode)
            self.assertTrue(res.valid, mode)
            self.assertIn(res.fx3_effective_mode, IBIS_MODES_FX3)
            self.assertTrue(res.ibis_coil_safe_park_verified)
        plus = evaluate_ibis_vs_catalyst_bridge(requested_mode="ACTIVE_PLUS")
        self.assertEqual(plus.fx3_effective_mode, "ACTIVE")
        self.assertEqual(plus.classification, BRIDGE_CLASS_SHIM_TRANSLATED)

    def test_20_pillar2_eval_unparked_floating_coils_blocked(self) -> None:
        res = evaluate_ibis_vs_catalyst_bridge(requested_mode="OFF", park_coils_on_off=False)
        self.assertFalse(res.valid)
        self.assertFalse(res.coil_parked_center_lock)
        self.assertFalse(res.ibis_coil_safe_park_verified)
        self.assertEqual(res.status, "BLOCKED_UNPARKED_FLOATING_IBIS_COILS")

    def test_21_pillar2_eval_unmasked_rigid_sensor_fault_blocked(self) -> None:
        self.assertEqual(FX6_RIGID_SENSOR_PARAM, "PRM_is_imager_stabilization_unit_fixed")
        res = evaluate_ibis_vs_catalyst_bridge(
            requested_mode="STANDARD", mask_rigid_sensor_query=False
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.status, "BLOCKED_UNMASKED_RIGID_SENSOR_FAULT")

    def test_22_pillar2_eval_direct_nvs_write_and_unknown_mode_blocked(self) -> None:
        nvs = evaluate_ibis_vs_catalyst_bridge(requested_mode="STANDARD", direct_nvs_write=True)
        self.assertFalse(nvs.valid)
        self.assertEqual(nvs.classification, BRIDGE_CLASS_HARD_WRITE_PROTECTED)
        self.assertEqual(nvs.nvs_calibration_writes, 0)
        self.assertEqual(nvs.status, "BLOCKED_NVS_IBIS_CALIBRATION_WRITE")

        unk = evaluate_ibis_vs_catalyst_bridge(requested_mode="GIMBAL_INVALID")
        self.assertFalse(unk.valid)
        self.assertEqual(unk.status, "BLOCKED_UNKNOWN_STEADYSHOT_MODE")

    # ---- Pillar 3: MI-Shoe XLR-H1 4ch 24-bit LPCM Audio ----

    def test_23_pillar3_report_hotshoe_avbb_audio_and_bitrate(self) -> None:
        rep = analyze_realhw_lens_ibis_audio_hdmi_peripheral_bridge(clean_room=True)
        p3 = rep.pillar3_audio_xlrh1
        self.assertTrue(p3.passed)
        self.assertEqual(p3.fx3_appfw_audio_marker_hits, len(AUDIO_APPFW_FX3_MARKERS))
        self.assertEqual(p3.fx6_appfw_audio_marker_hits, len(AUDIO_APPFW_FX6_MARKERS))
        self.assertEqual(p3.fx6_hotshoe.export_count, 76)
        self.assertEqual(p3.fx6_hotshoe.import_count, 44)
        self.assertEqual(p3.lpcm_4ch_bitrate_bps, 4_608_000)
        self.assertEqual(p3.lpcm_4ch_bitrate_bps, AUDIO_LPCM_4CH_BPS)
        self.assertEqual(p3.p11_nonblock_safe_rc_hex, f"0x{HOTSHOE_NONBLOCK_SAFE_RC:04x}")
        self.assertTrue(p3.phantom_device_timeout_eliminated)

    def test_24_pillar3_eval_xlr_h1_attached_4ch_native_passthrough(self) -> None:
        res = evaluate_mishoe_xlrh1_audio_bridge(handle_state="XLR_H1_ATTACHED")
        self.assertTrue(res.valid)
        self.assertEqual(res.classification, BRIDGE_CLASS_NATIVE_PASSTHROUGH)
        self.assertEqual(res.active_channels, AUDIO_LPCM_4CH_COUNT)
        self.assertEqual(res.bitrate_bps, 4_608_000)
        self.assertEqual(res.channel_routing["CH1"], "XLR_H1_INPUT_1")
        self.assertEqual(res.channel_routing["CH2"], "XLR_H1_INPUT_2")
        self.assertTrue(res.phantom_device_timeout_eliminated)

    def test_25_pillar3_eval_detached_and_trs_fallback_without_timeout(self) -> None:
        for state in ("XLR_H1_DETACHED", "TRS_JACK_ONLY"):
            self.assertIn(state, VALID_AUDIO_HANDLE_STATES)
            res = evaluate_mishoe_xlrh1_audio_bridge(
                handle_state=state, enable_nonblock_hot_detach=True
            )
            self.assertTrue(res.valid, state)
            self.assertEqual(res.classification, BRIDGE_CLASS_SHIM_TRANSLATED)
            self.assertEqual(res.active_channels, 2)
            self.assertEqual(res.bitrate_bps, 2_304_000)
            self.assertEqual(res.channel_routing["CH3"], "SILENCE_ZERO_PADDED")
            self.assertEqual(res.channel_routing["CH4"], "SILENCE_ZERO_PADDED")
            self.assertTrue(res.phantom_device_timeout_eliminated)

    def test_26_pillar3_eval_phantom_handle_timeout_blocked_when_shim_off(self) -> None:
        res = evaluate_mishoe_xlrh1_audio_bridge(
            handle_state="XLR_H1_DETACHED", enable_nonblock_hot_detach=False
        )
        self.assertFalse(res.valid)
        self.assertFalse(res.phantom_device_timeout_eliminated)
        self.assertEqual(res.status, "BLOCKED_PHANTOM_SMART_HANDLE_TIMEOUT")
        self.assertEqual(P11_SMART_HANDLE_QUEUE_ID, 0x91DB059B)
        self.assertEqual(P11_HOTSHOE_ATTACHED_EVT, 0x88000001)
        self.assertEqual(P11_HOTSHOE_DETACHED_EVT, 0x88000002)
        self.assertEqual(HOTSHOE_E_TMO, -50)

    def test_27_pillar3_eval_invalid_sample_rate_bit_depth_or_state_rejected(self) -> None:
        bad_sr = evaluate_mishoe_xlrh1_audio_bridge(sample_rate_hz=44_100)
        self.assertFalse(bad_sr.valid)
        self.assertEqual(bad_sr.status, "BLOCKED_INVALID_AUDIO_SAMPLE_RATE")

        bad_bd = evaluate_mishoe_xlrh1_audio_bridge(bit_depth=16)
        self.assertFalse(bad_bd.valid)
        self.assertEqual(bad_bd.status, "BLOCKED_INVALID_AUDIO_BIT_DEPTH")

        bad_st = evaluate_mishoe_xlrh1_audio_bridge(handle_state="XLR_K3M_UNKNOWN")
        self.assertFalse(bad_st.valid)
        self.assertEqual(bad_st.status, "BLOCKED_UNKNOWN_AUDIO_HANDLE_STATE")

    # ---- Pillar 4: HDMI Type-A & Multi-USB TC-IN vs 12G-SDI & BNC ----

    def test_28_pillar4_report_avbbc_cp_hdmi_sdi_and_stub_verification(self) -> None:
        rep = analyze_realhw_lens_ibis_audio_hdmi_peripheral_bridge(clean_room=True)
        p4 = rep.pillar4_hdmi_sdi_tc
        self.assertTrue(p4.passed)
        self.assertEqual(p4.fx3_appfw_hdmi_marker_hits, len(HDMI_APPFW_FX3_MARKERS))
        self.assertEqual(p4.fx6_appfw_sdi_hdmi_marker_hits, len(HDMI_SDI_APPFW_FX6_MARKERS))
        self.assertGreater(p4.fx6_cp_sdi_hits, p4.fx3_cp_sdi_hits)
        self.assertGreater(p4.fx3_cp_hdmi_hits, 0)
        self.assertGreater(p4.fx6_cp_hdmi_hits, 0)
        self.assertTrue(p4.sdi_blocking_wait_eliminated)

    def test_29_pillar4_eval_absent_fx6_hw_masked_non_blocking(self) -> None:
        for hw in FX6_ABSENT_HW_PERIPHERALS:
            res = evaluate_hdmi_sdi_tc_bridge(
                requested_interface=hw, mask_absent_hw=True, stub_blocking_wait_ms=0
            )
            self.assertTrue(res.valid, hw)
            self.assertEqual(res.classification, BRIDGE_CLASS_MASKED_ABSENT_HW)
            self.assertEqual(res.non_blocking_stub_rc, 0)
            self.assertEqual(res.stub_blocking_wait_ms, 0)
            self.assertTrue(res.sdi_blocking_wait_eliminated)

    def test_30_pillar4_eval_unmasked_sdi_or_nonzero_wait_blocked(self) -> None:
        unmasked = evaluate_hdmi_sdi_tc_bridge(
            requested_interface="12G_SDI_OUT", mask_absent_hw=False
        )
        self.assertFalse(unmasked.valid)
        self.assertFalse(unmasked.sdi_blocking_wait_eliminated)
        self.assertEqual(unmasked.status, "BLOCKED_UNMASKED_ABSENT_FX6_HW")

        blocking = evaluate_hdmi_sdi_tc_bridge(
            requested_interface="12G_SDI_OUT", mask_absent_hw=True, stub_blocking_wait_ms=250
        )
        self.assertFalse(blocking.valid)
        self.assertFalse(blocking.sdi_blocking_wait_eliminated)
        self.assertEqual(blocking.status, "BLOCKED_SDI_BLOCKING_WAIT_TIMEOUT")

    def test_31_pillar4_eval_hdmi_type_a_native_capabilities(self) -> None:
        for cap in HDMI_TYPE_A_CAPABILITIES + ("HDMI_4K60", "HDMI_RAW16", "HDMI_CLEAN_OSD"):
            res = evaluate_hdmi_sdi_tc_bridge(requested_interface=cap)
            self.assertTrue(res.valid, cap)
            self.assertEqual(res.classification, BRIDGE_CLASS_NATIVE_PASSTHROUGH)
            self.assertEqual(res.fx3_target_interface, "HDMI_TYPE_A")
            self.assertTrue(res.sdi_blocking_wait_eliminated)

    def test_32_pillar4_eval_multi_usb_vmc_bncm1_tc_in_and_uart_boot_hazard(self) -> None:
        self.assertEqual(VMC_BNCM1_ID_OHM, 680_000)
        self.assertEqual(VMC_BNCM1_LTC_PIN, 3)
        self.assertEqual(VMC_BNCM1_ID_PIN, 6)
        self.assertEqual(UART_BOOT_SHARED_PINS, (7, 8, 9))
        self.assertEqual(P11_RTC_UDATE_QUEUE_ID, 0x92D2091C)

        ok = evaluate_hdmi_sdi_tc_bridge(requested_interface="MULTI_USB_TC_IN", in_uart_boot=False)
        self.assertTrue(ok.valid)
        self.assertEqual(ok.classification, BRIDGE_CLASS_SHIM_TRANSLATED)
        self.assertTrue(ok.in_uart_boot_safe)

        hazard = evaluate_hdmi_sdi_tc_bridge(requested_interface="MULTI_USB_TC_IN", in_uart_boot=True)
        self.assertFalse(hazard.valid)
        self.assertFalse(hazard.in_uart_boot_safe)
        self.assertEqual(hazard.status, "BLOCKED_VMC_BNCM1_DURING_UART_BOOT")

    def test_33_pillar4_eval_unknown_video_tc_interface_blocked(self) -> None:
        res = evaluate_hdmi_sdi_tc_bridge(requested_interface="UNKNOWN_SDI_BUS")
        self.assertFalse(res.valid)
        self.assertEqual(res.status, "BLOCKED_UNKNOWN_VIDEO_TC_INTERFACE")

    # ---- 4-Class 16-Touchpoint Compatibility Matrix ----

    def test_34_compat_matrix_16_touchpoints_and_4_classes(self) -> None:
        matrix = build_phase146_compatibility_matrix()
        self.assertEqual(matrix.total_touchpoints, 16)
        self.assertEqual(sum(matrix.class_counts.values()), 16)
        self.assertEqual(sum(matrix.subsystem_counts.values()), 16)
        self.assertEqual(set(matrix.class_counts.keys()), set(VALID_BRIDGE_CLASSES))
        self.assertEqual(
            matrix.class_counts,
            {
                BRIDGE_CLASS_NATIVE_PASSTHROUGH: 5,
                BRIDGE_CLASS_SHIM_TRANSLATED: 5,
                BRIDGE_CLASS_MASKED_ABSENT_HW: 3,
                BRIDGE_CLASS_HARD_WRITE_PROTECTED: 3,
            },
        )
        self.assertEqual(
            matrix.subsystem_counts,
            {"LENS_P18": 4, "IBIS_IMU": 4, "AUDIO_XLRH1": 3, "HDMI_SDI_TC": 5},
        )
        self.assertTrue(all(t.blocking_wait_eliminated for t in matrix.touchpoints))
        self.assertTrue(all(t.write_protected for t in matrix.touchpoints))

    # ---- Write-Guard & Partition Protection ----

    def test_35_write_guard_allows_volatile_ram_staging(self) -> None:
        for path in (
            "/tmp/stage_b/peripheral_bridge_shadow.json",
            "ram://stage_b/lens_meta.json",
            "ramdisk://ibis_park_policy.bin",
            "mem://audio_route.json",
        ):
            res = evaluate_phase146_write_guard(path)
            self.assertTrue(res.valid, path)
            self.assertTrue(res.volatile_ram_staged)
            self.assertFalse(res.persistent_write_blocked)
            self.assertFalse(res.p18_lens_writes_permitted)
            self.assertEqual(res.emmc_mutation_bytes, 0)
            self.assertEqual(res.calibration_mutation_bytes, 0)

    def test_36_write_guard_blocks_p18_p12_p13_backup_and_emmc(self) -> None:
        for target in (
            "/dev/nflasha18",
            "/dev/nflasha18/lensfile.bin",
            "/lens/lensfile.bin",
            "p18:/lens/lensfile.bin",
            "p12:/cert/device_key.bin",
            "p13:/setting/reserved.bin",
            "p2:/setting/Backup.bin",
            "/tmp/Backup.bin",
            "/tmp/psd.bin",
            "/tmp/defdet.bin",
            "p6:/tmp/jiritsu",
            "/dev/cnflasha0",
            "/dev/mmcblk0p18",
            "p8:/cpapp-b.bin",
        ):
            res = evaluate_phase146_write_guard(target)
            self.assertFalse(res.valid, target)
            self.assertTrue(res.persistent_write_blocked, target)
            self.assertFalse(res.p18_lens_writes_permitted)
            self.assertEqual(res.emmc_mutation_bytes, 0)
            self.assertEqual(res.calibration_mutation_bytes, 0)

    # ---- Additional Cross-Subsystem & Local Donor Invariant Tests ----

    def test_37_report_write_guards_embedded_and_passed(self) -> None:
        rep = analyze_realhw_lens_ibis_audio_hdmi_peripheral_bridge(clean_room=True)
        self.assertTrue(rep.volatile_guard_ok.valid)
        self.assertTrue(rep.forbidden_p18_guard_blocked.persistent_write_blocked)
        self.assertTrue(rep.forbidden_p12_guard_blocked.persistent_write_blocked)
        self.assertTrue(rep.forbidden_backup_guard_blocked.persistent_write_blocked)

    def test_38_audio_bitrate_math_constant_matches_4ch_24bit_48khz(self) -> None:
        self.assertEqual(AUDIO_LPCM_SAMPLE_RATE_HZ, 48_000)
        self.assertEqual(AUDIO_LPCM_BIT_DEPTH, 24)
        self.assertEqual(AUDIO_LPCM_4CH_COUNT, 4)
        self.assertEqual(AUDIO_LPCM_4CH_BPS, 48_000 * 24 * 4)

    def test_39_marker_tuples_nonempty_and_unique(self) -> None:
        for group in (
            LENS_APPFW_FX3_MARKERS,
            LENS_APPFW_FX6_MARKERS,
            SENCORE_SHARED_MARKERS,
            IBIS_APPFW_FX3_MARKERS,
            IBIS_APPFW_FX6_MARKERS,
            IBIS_CP_SHARED_MARKERS,
            IBIS_MPR_GYRO_FX3_MARKERS,
            IBIS_MPR_GYRO_FX6_MARKERS,
            AUDIO_APPFW_FX3_MARKERS,
            AUDIO_APPFW_FX6_MARKERS,
            HOTSHOE_MARKERS,
            AVBB_AUDIO_MARKERS,
            HDMI_SDI_APPFW_FX6_MARKERS,
            HDMI_APPFW_FX3_MARKERS,
            AVBBC_BRIDGE_SYMBOLS,
        ):
            self.assertGreater(len(group), 0)
            self.assertEqual(len(group), len(set(group)))

    def test_40_sencore_dt_needed_and_markers_in_clean_room(self) -> None:
        rep = analyze_realhw_lens_ibis_audio_hdmi_peripheral_bridge(clean_room=True)
        p1 = rep.pillar1_lens_p18
        for m in SENCORE_SHARED_MARKERS:
            self.assertGreater(p1.fx3_sencore.marker_hits.get(m, 0), 0, m)
            self.assertGreater(p1.fx6_sencore.marker_hits.get(m, 0), 0, m)

    def test_41_avbbc_bridge_symbols_present_on_both_bodies(self) -> None:
        rep = analyze_realhw_lens_ibis_audio_hdmi_peripheral_bridge(clean_room=True)
        p4 = rep.pillar4_hdmi_sdi_tc
        for sym in AVBBC_BRIDGE_SYMBOLS:
            self.assertGreater(p4.fx3_avbbc.marker_hits.get(sym, 0), 0, sym)
            self.assertGreater(p4.fx6_avbbc.marker_hits.get(sym, 0), 0, sym)

    def test_42_hdmi_blocking_wait_rejected_even_on_hdmi_native(self) -> None:
        res = evaluate_hdmi_sdi_tc_bridge(
            requested_interface="HDMI_4K60", stub_blocking_wait_ms=15
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.status, "BLOCKED_HDMI_BLOCKING_WAIT")

    def test_43_tc_in_blocking_wait_rejected(self) -> None:
        res = evaluate_hdmi_sdi_tc_bridge(
            requested_interface="MULTI_USB_TC_IN", in_uart_boot=False, stub_blocking_wait_ms=10
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.status, "BLOCKED_TC_BLOCKING_WAIT")

    def test_44_bnc_genlock_and_darwin_nd_target_noop_stub(self) -> None:
        for req in ("BNC_GENLOCK_IN", "DARWIN_ND"):
            res = evaluate_hdmi_sdi_tc_bridge(requested_interface=req, mask_absent_hw=True)
            self.assertTrue(res.valid)
            self.assertEqual(res.fx3_target_interface, "NO_OP_STUB")
            self.assertEqual(res.classification, BRIDGE_CLASS_MASKED_ABSENT_HW)

        bnc_tc = evaluate_hdmi_sdi_tc_bridge(requested_interface="BNC_TC_OUT", mask_absent_hw=True)
        self.assertTrue(bnc_tc.valid)
        self.assertEqual(bnc_tc.fx3_target_interface, "MULTI_USB_VMC_BNCM1_TC_IN")

    def test_45_matrix_touchpoint_ids_unique_and_complete(self) -> None:
        matrix = build_phase146_compatibility_matrix()
        ids = [t.touchpoint_id for t in matrix.touchpoints]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertIn("LENS_P18_FACTORY_CALIB", ids)
        self.assertIn("IBIS_OFF_CENTER_LOCK_PARK", ids)
        self.assertIn("AUDIO_DETACHED_FALLBACK", ids)
        self.assertIn("FX6_12G_SDI_SERIALIZER", ids)
        self.assertIn("P12_P13_CERT_NVS_FIREWALL", ids)

    def test_46_local_donor_specific_invariants_when_present(self) -> None:
        rep = analyze_realhw_lens_ibis_audio_hdmi_peripheral_bridge()
        self.assertTrue(rep.all_checks_passed, rep.errors)
        if rep.mode == "LOCAL_DONOR_VERIFIED":
            p1 = rep.pillar1_lens_p18
            p2 = rep.pillar2_ibis_catalyst
            p3 = rep.pillar3_audio_xlrh1
            p4 = rep.pillar4_hdmi_sdi_tc
            self.assertTrue(p1.lens_comm_exports_identical)
            self.assertTrue(p1.sencore_exports_identical)
            self.assertEqual(p2.fx3_cp_liroseq_hits, 529)
            self.assertEqual(p2.fx6_cp_liroseq_hits, 148)
            self.assertEqual(p2.fx3_backup_subsystems, 819)
            self.assertEqual(p2.fx6_backup_subsystems, 840)
            self.assertEqual(p3.fx6_hotshoe.file_bytes, 47_808)
            self.assertEqual(p3.fx6_avbb_audio.file_bytes, 70_096)
            self.assertEqual(p4.fx3_cp_hdmi_hits, 404)
            self.assertEqual(p4.fx3_cp_sdi_hits, 16)
            self.assertEqual(p4.fx6_cp_hdmi_hits, 421)
            self.assertEqual(p4.fx6_cp_sdi_hits, 71)


if __name__ == "__main__":
    unittest.main()
