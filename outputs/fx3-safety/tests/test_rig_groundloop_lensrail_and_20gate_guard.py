"""Fast dual-mode unit tests for Phase 69 — Rig D-Tap/HDMI Ground-Loop, E-Mount Rail Guard, .RSV Salvage & 20-Gate Preflight (`G01..G20`)."""

from __future__ import annotations

import contextlib
import io
import json
import os
from pathlib import Path
import struct
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
from fx3_safety.rig_groundloop_lensrail_and_20gate_guard import (
    CAMERA_POWER_DUMMY_COUPLER_SHARED_DTAP,
    CAMERA_POWER_INTERNAL_NPFZ100_ISOLATED_USBPD,
    CAMERA_POWER_ISOLATED_DCDC_BOX,
    EMOUNT_PIN_COUNT,
    EMOUNT_ROTARY_WIPE_WINDOW_MS,
    G19_GATE_CODE,
    G19_GATE_ID,
    G20_GATE_CODE,
    G20_GATE_ID,
    HDMI_CABLE_COPPER,
    HDMI_CABLE_OPTICAL_FIBER,
    MONITOR_POWER_DEDICATED_BATTERY,
    MONITOR_POWER_ISOLATED_DCDC_BOX,
    MONITOR_POWER_SHARED_DTAP_14V8,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    POWER_UP_SEQUENCE_CANONICAL,
    RIG_GROUNDLOOP_20GATE_SCHEMA,
    RIG_GROUNDLOOP_20GATE_VERSION,
    STATUS_BLOCKED_BATTERY_RESERVE_INSUFFICIENT,
    STATUS_BLOCKED_DONOR_INTEGRITY,
    STATUS_BLOCKED_EMOUNT_HOT_DETACH_HAZARD,
    STATUS_BLOCKED_GROUND_LOOP_HAZARD,
    STATUS_BLOCKED_HDMI_PIN18_BACKFEED,
    STATUS_BLOCKED_IBIS_UNPARKED_IMPACT,
    STATUS_BLOCKED_PERSISTENT_EMMC_WRITE,
    STATUS_BLOCKED_POWER_SEQUENCE_VIOLATION,
    STATUS_BLOCKED_RSV_SALVAGE_INVALID,
    STATUS_BLOCKED_UPS_SWITCHOVER_DROP,
    STATUS_BLOCKED_VLENS_CROWBAR_TIMEOUT,
    STATUS_FAIL_OFFLINE_HARDWARE_NOT_ATTACHED,
    STATUS_SAFE,
    STATUS_VERIFIED_G19,
    STATUS_VERIFIED_G20,
    STATUS_VERIFIED_SAFE,
    STOCK_CP_IBIS_CENTER_LOCK_OPCODE,
    TEARDOWN_SEQUENCE_CANONICAL,
    V_LENS_CROWBAR_MAX_MS,
    audit_rig_20gate_donor_contracts,
    build_synthetic_sony_rsv_payload,
    evaluate_20gate_preflight,
    evaluate_g19_rig_groundloop_and_lensrail,
    evaluate_g20_power_failover_ups_and_rsv_salvage,
    inspect_sony_rsv_salvage_structure,
    main as module_cli_main,
    verify_emount_hot_detach_rail_and_ibis_park,
    verify_power_failover_ups_and_rsv_salvage,
    verify_rig_dtap_hdmi_groundloop_firewall,
    verify_rig_power_sequence,
)
from fx3_safety.usblan_ptpip_and_18gate_preflight import evaluate_18_master_safety_gates


class RigGroundLoopLensRailAnd20GateTests(unittest.TestCase):
    # --- 1. Hard Redlines, Exports & Strictly O_RDONLY Donor Audit ---

    def test_01_hard_locked_redlines_and_package_exports(self) -> None:
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(PERSISTENT_WRITE_RELEASE)
        self.assertEqual(RIG_GROUNDLOOP_20GATE_SCHEMA, "fx3-rig-groundloop-lensrail-20gate-preflight-v1")
        self.assertEqual(RIG_GROUNDLOOP_20GATE_VERSION, "1.0.0")
        for sym in (
            "RIG_GROUNDLOOP_20GATE_SCHEMA",
            "G19_GATE_ID",
            "G20_GATE_ID",
            "audit_rig_20gate_donor_contracts",
            "verify_rig_power_sequence",
            "verify_rig_dtap_hdmi_groundloop_firewall",
            "verify_emount_hot_detach_rail_and_ibis_park",
            "build_synthetic_sony_rsv_payload",
            "inspect_sony_rsv_salvage_structure",
            "verify_power_failover_ups_and_rsv_salvage",
            "evaluate_g19_rig_groundloop_and_lensrail",
            "evaluate_g20_power_failover_ups_and_rsv_salvage",
            "evaluate_20gate_preflight",
            "rig_groundloop_lensrail_and_20gate_guard",
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
            res_default = audit_rig_20gate_donor_contracts()
        self.assertTrue(res_default.valid)
        self.assertEqual(res_default.status, STATUS_VERIFIED_SAFE)
        self.assertEqual(res_default.access_mode, "O_RDONLY")
        self.assertEqual(len(res_default.missing_markers), 0)
        for path, flags in observed_flags:
            if "libInfraLensCommunicator.so" in path or "libBusPower.so" in path or "libInfraMediaMount.so" in path:
                self.assertEqual(flags & os.O_ACCMODE, os.O_RDONLY, f"Non-O_RDONLY open on {path}")

        res_clean = audit_rig_20gate_donor_contracts(force_clean_room=True)
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
            for name in (
                "libfan.so",
                "libInfraLensCommunicator.so",
                "libBusPower.so",
                "libUsbBusPower.so",
                "libInfraMediaMount.so",
                "libInfraMediaCommon.so",
            ):
                (fx3_lib / name).write_bytes(b"corrupt")
            (fx6_lib / "libfan.so").write_bytes(b"corrupt")
            (fx6_lib / "libInfraLensCommunicator.so").write_bytes(b"corrupt")
            res = audit_rig_20gate_donor_contracts(work_root=tmp, force_clean_room=False)
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_DONOR_INTEGRITY)
        self.assertGreaterEqual(len(res.missing_markers), 1)

    # --- 2. D-Tap / HDMI Type-A Ground-Loop & Hot-Plug ESD Firewall ---

    def test_04_safe_internal_npfz100_and_isolated_usbpd_with_copper_hdmi(self) -> None:
        res = verify_rig_dtap_hdmi_groundloop_firewall(
            camera_power_mode=CAMERA_POWER_INTERNAL_NPFZ100_ISOLATED_USBPD,
            monitor_model="Atomos Ninja",
            monitor_power_mode=MONITOR_POWER_DEDICATED_BATTERY,
            hdmi_cable_type=HDMI_CABLE_COPPER,
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_SAFE)
        self.assertFalse(res.shared_unisolated_dtap)
        self.assertFalse(res.open_negative_ground_return_fault)
        self.assertFalse(res.cxd90057_esd_array_at_risk)

    def test_05_safe_shared_dtap_with_optical_fiber_hdmi_exemption(self) -> None:
        res = verify_rig_dtap_hdmi_groundloop_firewall(
            camera_power_mode=CAMERA_POWER_DUMMY_COUPLER_SHARED_DTAP,
            monitor_model="SmallHD",
            monitor_power_mode=MONITOR_POWER_SHARED_DTAP_14V8,
            shared_unisolated_dtap=True,
            galvanic_dc_dc_isolated=False,
            hdmi_cable_type=HDMI_CABLE_OPTICAL_FIBER,
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_SAFE)
        self.assertFalse(res.hdmi_pin17_shield_return_hazard)

    def test_06_safe_galvanic_isolated_dcdc_box_with_strict_sequence(self) -> None:
        res = verify_rig_dtap_hdmi_groundloop_firewall(
            camera_power_mode=CAMERA_POWER_ISOLATED_DCDC_BOX,
            monitor_model="Atomos Ninja",
            monitor_power_mode=MONITOR_POWER_ISOLATED_DCDC_BOX,
            shared_unisolated_dtap=True,
            galvanic_dc_dc_isolated=True,
            hdmi_cable_type=HDMI_CABLE_COPPER,
            power_up_sequence=POWER_UP_SEQUENCE_CANONICAL,
            teardown_sequence=TEARDOWN_SEQUENCE_CANONICAL,
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_SAFE)
        self.assertTrue(res.galvanic_dc_dc_isolated)
        self.assertFalse(res.shared_unisolated_dtap)

    def test_07_blocks_shared_unisolated_dtap_copper_hdmi_without_locking_connector(self) -> None:
        res = verify_rig_dtap_hdmi_groundloop_firewall(
            camera_power_mode=CAMERA_POWER_DUMMY_COUPLER_SHARED_DTAP,
            monitor_model="Atomos Ninja",
            monitor_power_mode=MONITOR_POWER_SHARED_DTAP_14V8,
            shared_unisolated_dtap=True,
            galvanic_dc_dc_isolated=False,
            hdmi_cable_type=HDMI_CABLE_COPPER,
            ground_first_locking_connector=False,
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_GROUND_LOOP_HAZARD)
        self.assertIn(STATUS_BLOCKED_GROUND_LOOP_HAZARD, res.violation_codes)

    def test_08_allows_shared_dtap_with_ground_first_locking_connector_and_warns(self) -> None:
        res = verify_rig_dtap_hdmi_groundloop_firewall(
            camera_power_mode=CAMERA_POWER_DUMMY_COUPLER_SHARED_DTAP,
            monitor_model="SmallHD",
            monitor_power_mode=MONITOR_POWER_SHARED_DTAP_14V8,
            shared_unisolated_dtap=True,
            galvanic_dc_dc_isolated=False,
            hdmi_cable_type=HDMI_CABLE_COPPER,
            ground_first_locking_connector=True,
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_SAFE)
        self.assertGreaterEqual(len(res.warnings), 1)

    def test_09_detects_open_negative_monitor_dtap_ground_return_fault(self) -> None:
        res = verify_rig_dtap_hdmi_groundloop_firewall(
            camera_power_mode=CAMERA_POWER_DUMMY_COUPLER_SHARED_DTAP,
            monitor_model="Atomos Ninja",
            monitor_power_mode=MONITOR_POWER_SHARED_DTAP_14V8,
            shared_unisolated_dtap=True,
            hdmi_cable_type=HDMI_CABLE_COPPER,
            ground_first_locking_connector=True,
            monitor_dtap_pos_connected=True,
            monitor_dtap_gnd_connected=False,
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_GROUND_LOOP_HAZARD)
        self.assertTrue(res.open_negative_ground_return_fault)
        self.assertTrue(res.hdmi_pin17_shield_return_hazard)
        self.assertTrue(res.cxd90057_esd_array_at_risk)

    def test_10_detects_open_negative_camera_dummy_coupler_ground_fault(self) -> None:
        res = verify_rig_dtap_hdmi_groundloop_firewall(
            camera_power_mode=CAMERA_POWER_DUMMY_COUPLER_SHARED_DTAP,
            monitor_power_mode=MONITOR_POWER_SHARED_DTAP_14V8,
            shared_unisolated_dtap=True,
            hdmi_cable_type=HDMI_CABLE_COPPER,
            camera_dtap_pos_connected=True,
            camera_dtap_gnd_connected=False,
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_GROUND_LOOP_HAZARD)
        self.assertTrue(res.open_negative_ground_return_fault)
        self.assertTrue(res.cxd90057_esd_array_at_risk)

    def test_11_power_up_and_teardown_sequence_state_machine(self) -> None:
        ok_seq = verify_rig_power_sequence()
        self.assertTrue(ok_seq.valid)
        self.assertEqual(ok_seq.status, STATUS_SAFE)

        bad_up = verify_rig_power_sequence(
            power_up_steps=("POWER_ON_CAMERA", "CONNECT_POWER_CABLES", "CONNECT_HDMI", "POWER_ON_MONITOR")
        )
        self.assertFalse(bad_up.valid)
        self.assertFalse(bad_up.power_up_valid)
        self.assertEqual(bad_up.status, STATUS_BLOCKED_GROUND_LOOP_HAZARD)

        bad_down = verify_rig_power_sequence(
            teardown_steps=("DISCONNECT_POWER_CABLES", "POWER_OFF_MONITOR", "POWER_OFF_CAMERA", "DISCONNECT_HDMI")
        )
        self.assertFalse(bad_down.valid)
        self.assertFalse(bad_down.teardown_valid)
        self.assertEqual(bad_down.status, STATUS_BLOCKED_GROUND_LOOP_HAZARD)

    def test_12_blocks_hot_plug_hdmi_while_powered_and_wrong_sequence_in_rig(self) -> None:
        res = verify_rig_dtap_hdmi_groundloop_firewall(
            galvanic_dc_dc_isolated=True,
            hot_plug_hdmi_while_powered=True,
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_GROUND_LOOP_HAZARD)
        self.assertIn(STATUS_BLOCKED_POWER_SEQUENCE_VIOLATION, res.violation_codes)

    def test_13_blocks_dtap_out_of_range_voltage(self) -> None:
        res_hi = verify_rig_dtap_hdmi_groundloop_firewall(
            camera_power_mode=CAMERA_POWER_ISOLATED_DCDC_BOX,
            monitor_power_mode=MONITOR_POWER_ISOLATED_DCDC_BOX,
            galvanic_dc_dc_isolated=True,
            dtap_bus_voltage_v=18.2,
        )
        self.assertFalse(res_hi.valid)
        self.assertEqual(res_hi.status, STATUS_BLOCKED_GROUND_LOOP_HAZARD)

    def test_14_blocks_hdmi_pin18_5v_overvoltage_overcurrent_and_reverse_backfeed(self) -> None:
        res_v = verify_rig_dtap_hdmi_groundloop_firewall(hdmi_pin18_voltage_v=5.40)
        self.assertFalse(res_v.valid)
        self.assertTrue(res_v.hdmi_pin18_backfeed_blocked)
        self.assertEqual(res_v.status, STATUS_BLOCKED_HDMI_PIN18_BACKFEED)

        res_i = verify_rig_dtap_hdmi_groundloop_firewall(hdmi_pin18_current_ma=72.0)
        self.assertFalse(res_i.valid)
        self.assertTrue(res_i.hdmi_pin18_backfeed_blocked)
        self.assertEqual(res_i.status, STATUS_BLOCKED_HDMI_PIN18_BACKFEED)

        res_rev = verify_rig_dtap_hdmi_groundloop_firewall(hdmi_pin18_reverse_backfeed=True)
        self.assertFalse(res_rev.valid)
        self.assertTrue(res_rev.hdmi_pin18_backfeed_blocked)
        self.assertEqual(res_rev.status, STATUS_BLOCKED_HDMI_PIN18_BACKFEED)

    # --- 3. E-Mount V_LENS Hot-Detach Crowbar & Stock-CP IBIS Park Verifier ---

    def test_15_emount_hot_detach_crowbar_and_ibis_0x0400_park_pass(self) -> None:
        res = verify_emount_hot_detach_rail_and_ibis_park()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_SAFE)
        self.assertEqual(res.emount_pin_count, EMOUNT_PIN_COUNT)
        self.assertLessEqual(res.v_lens_servo_crowbar_ms, V_LENS_CROWBAR_MAX_MS)
        self.assertLess(res.v_lens_servo_crowbar_ms, EMOUNT_ROTARY_WIPE_WINDOW_MS)
        self.assertEqual(res.v_lens_servo_residual_ma, 0.0)
        self.assertTrue(res.crowbar_within_budget)
        self.assertEqual(res.ibis_park_opcode_hex, f"0x{STOCK_CP_IBIS_CENTER_LOCK_OPCODE:04x}")
        self.assertTrue(res.ibis_stage_parked)
        self.assertEqual(res.cp_mutation_bytes, 0)

    def test_16_emount_blocks_missing_lens_det_interrupt(self) -> None:
        res = verify_emount_hot_detach_rail_and_ibis_park(lens_det_interrupt_triggered=False)
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_EMOUNT_HOT_DETACH_HAZARD)

    def test_17_emount_blocks_crowbar_timeout_and_wipe_window_breach(self) -> None:
        res_slow = verify_emount_hot_detach_rail_and_ibis_park(v_lens_servo_crowbar_ms=2.4)
        self.assertFalse(res_slow.valid)
        self.assertFalse(res_slow.crowbar_within_budget)
        self.assertEqual(res_slow.status, STATUS_BLOCKED_VLENS_CROWBAR_TIMEOUT)

        res_wipe = verify_emount_hot_detach_rail_and_ibis_park(v_lens_servo_crowbar_ms=3.8)
        self.assertFalse(res_wipe.valid)
        self.assertIn(STATUS_BLOCKED_VLENS_CROWBAR_TIMEOUT, res_wipe.violation_codes)

    def test_18_emount_blocks_residual_current_and_unparked_ibis_stage(self) -> None:
        res_ma = verify_emount_hot_detach_rail_and_ibis_park(v_lens_servo_residual_ma=12.5)
        self.assertFalse(res_ma.valid)
        self.assertFalse(res_ma.crowbar_within_budget)

        res_ibis = verify_emount_hot_detach_rail_and_ibis_park(ibis_stage_parked=False)
        self.assertFalse(res_ibis.valid)
        self.assertEqual(res_ibis.status, STATUS_BLOCKED_IBIS_UNPARKED_IMPACT)

        res_op = verify_emount_hot_detach_rail_and_ibis_park(ibis_park_opcode=0x0300)
        self.assertFalse(res_op.valid)
        self.assertEqual(res_op.status, STATUS_BLOCKED_IBIS_UNPARKED_IMPACT)

    def test_19_emount_blocks_rail_out_of_bounds_and_cp_mutation(self) -> None:
        res_rail = verify_emount_hot_detach_rail_and_ibis_park(v_lens_logic_v=3.8, v_lens_servo_v=5.7)
        self.assertFalse(res_rail.valid)
        self.assertEqual(res_rail.status, STATUS_BLOCKED_EMOUNT_HOT_DETACH_HAZARD)

        res_cp = verify_emount_hot_detach_rail_and_ibis_park(cp_mutation_bytes=4)
        self.assertFalse(res_cp.valid)
        self.assertEqual(res_cp.status, STATUS_BLOCKED_EMOUNT_HOT_DETACH_HAZARD)

    # --- 4. Power-Loss .RSV Salvage & USB-PD Battery-Less Trap Guard ---

    def test_20_ups_seamless_switchover_on_usbpd_unplug_with_npfz100_reserve(self) -> None:
        res = verify_power_failover_ups_and_rsv_salvage(
            usb_pd_unplug_event=True,
            np_fz100_installed=True,
            np_fz100_soc_pct=18,
            np_fz100_load_voltage_v=6.9,
            lost_frames_on_switchover=0,
            container_cleanly_closed=True,
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_SAFE)
        self.assertTrue(res.ups_switchover_seamless)
        self.assertEqual(res.lost_frames_on_switchover, 0)
        self.assertTrue(res.moov_atom_written)
        self.assertTrue(res.mxf_footer_partition_written)
        self.assertEqual(res.physical_media_writes, 0)
        self.assertFalse(res.persistent_emmc_writes_authorized)

    def test_21_blocks_battery_less_usb_pd_trap_fail_closed(self) -> None:
        res = verify_power_failover_ups_and_rsv_salvage(
            np_fz100_installed=False,
            battery_less_usb_pd=True,
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_BATTERY_RESERVE_INSUFFICIENT)
        self.assertTrue(res.battery_less_usb_pd)
        self.assertTrue(res.rsv_salvage_verified)
        self.assertEqual(res.physical_media_writes, 0)
        self.assertFalse(res.persistent_emmc_writes_authorized)

    def test_22_blocks_low_soc_and_low_load_voltage_fail_closed(self) -> None:
        res_low_soc = verify_power_failover_ups_and_rsv_salvage(np_fz100_soc_pct=8, np_fz100_load_voltage_v=7.2)
        self.assertFalse(res_low_soc.valid)
        self.assertEqual(res_low_soc.status, STATUS_BLOCKED_BATTERY_RESERVE_INSUFFICIENT)

        res_border = verify_power_failover_ups_and_rsv_salvage(np_fz100_soc_pct=14, np_fz100_load_voltage_v=7.0)
        self.assertFalse(res_border.valid)
        self.assertEqual(res_border.status, STATUS_BLOCKED_BATTERY_RESERVE_INSUFFICIENT)

        res_low_v = verify_power_failover_ups_and_rsv_salvage(np_fz100_soc_pct=25, np_fz100_load_voltage_v=6.5)
        self.assertFalse(res_low_v.valid)
        self.assertEqual(res_low_v.status, STATUS_BLOCKED_BATTERY_RESERVE_INSUFFICIENT)

    def test_23_blocks_ups_switchover_frame_drop_or_unclosed_container(self) -> None:
        res_drop = verify_power_failover_ups_and_rsv_salvage(
            usb_pd_unplug_event=True,
            lost_frames_on_switchover=2,
        )
        self.assertFalse(res_drop.valid)
        self.assertEqual(res_drop.status, STATUS_BLOCKED_UPS_SWITCHOVER_DROP)

        res_unclosed = verify_power_failover_ups_and_rsv_salvage(
            usb_pd_unplug_event=True,
            container_cleanly_closed=False,
        )
        self.assertFalse(res_unclosed.valid)
        self.assertEqual(res_unclosed.status, STATUS_BLOCKED_UPS_SWITCHOVER_DROP)

    def test_24_rsv_salvage_readonly_inspection_isobmff_mxf_and_corrupt(self) -> None:
        rsv_bytes = build_synthetic_sony_rsv_payload(brand="XAVC", frame_count=6, include_moov=False)
        res = inspect_sony_rsv_salvage_structure(rsv_bytes)
        self.assertTrue(res.valid)
        self.assertEqual(res.container_format, "ISO_BMFF_XAVC_RSV")
        self.assertEqual(res.ftyp_brand, "XAVC")
        self.assertFalse(res.has_moov_or_footer)
        self.assertTrue(res.needs_rsv_salvage)
        self.assertEqual(res.recoverable_chunks, 6)
        self.assertEqual(res.physical_media_writes, 0)
        self.assertFalse(res.persistent_emmc_writes_authorized)

        # Read-only path check with os.O_RDONLY spy
        observed = []
        orig_open = os.open

        def spy_open(path, flags, *args, **kwargs):
            observed.append((str(path), flags))
            return orig_open(path, flags, *args, **kwargs)

        with tempfile.TemporaryDirectory() as tmpdir:
            rsv_file = Path(tmpdir) / "C0001.RSV"
            rsv_file.write_bytes(rsv_bytes)
            with patch("os.open", side_effect=spy_open):
                res_file = inspect_sony_rsv_salvage_structure(rsv_path=rsv_file)
            self.assertTrue(res_file.valid)
            self.assertEqual(rsv_file.read_bytes(), rsv_bytes)
            file_opens = [(p, f) for p, f in observed if "C0001.RSV" in p]
            self.assertEqual(len(file_opens), 1)
            self.assertEqual(file_opens[0][1] & os.O_ACCMODE, os.O_RDONLY)

        # MXF KLV .RSV (without FooterPartition)
        mxf_klv = (
            b"\x06\x0e\x2b\x34\x02\x05\x01\x01\x0d\x01\x02\x01\x01\x02\x04\x00" + (b"\x00" * 16)
            + b"\x06\x0e\x2b\x34\x01\x02\x01\x01\x0d\x01\x03\x01\x15\x01\x05\x00" + (b"\x55" * 32)
        )
        res_mxf = inspect_sony_rsv_salvage_structure(mxf_klv)
        self.assertTrue(res_mxf.valid)
        self.assertEqual(res_mxf.container_format, "MXF_KLV_RSV")
        self.assertTrue(res_mxf.needs_rsv_salvage)

        # Corrupt .RSV rejected fail-closed
        bad = build_synthetic_sony_rsv_payload(corrupt_header=True)
        res_bad = inspect_sony_rsv_salvage_structure(bad)
        self.assertFalse(res_bad.valid)
        self.assertEqual(res_bad.status, STATUS_BLOCKED_RSV_SALVAGE_INVALID)

        # Unsupported ftyp brand or empty mdat rejected
        bad_brand = struct.pack(">I4s4sI4s4s", 24, b"ftyp", b"XXXX", 0, b"XXXX", b"XXXX") + struct.pack(">I4s", 0, b"mdat") + b"\x00" * 16
        res_brand = inspect_sony_rsv_salvage_structure(bad_brand)
        self.assertFalse(res_brand.valid)
        self.assertEqual(res_brand.status, STATUS_BLOCKED_RSV_SALVAGE_INVALID)

    # --- 5. Gate G19 & G20 Evaluators & 20-Gate Master Safety Preflight ---

    def test_25_g19_and_g20_verdicts_dual_mode(self) -> None:
        v19, r19 = evaluate_g19_rig_groundloop_and_lensrail(force_clean_room=True)
        self.assertTrue(v19.passed)
        self.assertEqual(v19.gate_id, G19_GATE_ID)
        self.assertEqual(v19.gate_code, G19_GATE_CODE)
        self.assertEqual(v19.status, STATUS_VERIFIED_G19)
        self.assertFalse(r19.persistent_emmc_writes_authorized)

        v20, r20 = evaluate_g20_power_failover_ups_and_rsv_salvage(force_clean_room=True)
        self.assertTrue(v20.passed)
        self.assertEqual(v20.gate_id, G20_GATE_ID)
        self.assertEqual(v20.gate_code, G20_GATE_CODE)
        self.assertEqual(v20.status, STATUS_VERIFIED_G20)
        self.assertTrue(r20.battery_less_trap_verified)
        self.assertEqual(r20.physical_media_writes, 0)
        self.assertFalse(r20.persistent_emmc_writes_authorized)

    def test_26_20gate_offline_default_17_of_20_and_g10_g12_fail_offline(self) -> None:
        rep = evaluate_20gate_preflight(DEFAULT_REPO_ROOT, force_clean_room=True)
        self.assertEqual(rep.schema, RIG_GROUNDLOOP_20GATE_SCHEMA)
        self.assertEqual(len(rep.gates), 20)
        self.assertEqual(rep.summary["total_gates"], 20)
        self.assertEqual(rep.summary["verified_gates"], 17)
        self.assertEqual(rep.summary["blocked_or_pending_gates"], 3)
        self.assertTrue(rep.offline_17_gates_verified)
        self.assertFalse(rep.all_20_gates_verified)
        self.assertFalse(rep.dry_run_rehearsal_only)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.persistent_write_release)
        for idx in (9, 10, 11):
            self.assertFalse(rep.gates[idx]["passed"])
            self.assertEqual(rep.gates[idx]["status"], STATUS_FAIL_OFFLINE_HARDWARE_NOT_ATTACHED)

    def test_27_20gate_dry_run_simulated_backup_20_of_20_and_redlines_locked(self) -> None:
        rep = evaluate_20gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
        )
        self.assertEqual(len(rep.gates), 20)
        self.assertEqual(rep.summary["verified_gates"], 20)
        self.assertEqual(rep.summary["blocked_or_pending_gates"], 0)
        self.assertTrue(rep.all_20_gates_verified)
        self.assertTrue(rep.dry_run_rehearsal_only)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.persistent_write_release)
        self.assertTrue(all(g["passed"] for g in rep.gates))

    def test_28_20gate_propagates_g19_g20_failures_and_emmc_write_redline(self) -> None:
        rep_g19 = evaluate_20gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            rig_kwargs={
                "camera_power_mode": CAMERA_POWER_DUMMY_COUPLER_SHARED_DTAP,
                "monitor_power_mode": MONITOR_POWER_SHARED_DTAP_14V8,
                "shared_unisolated_dtap": True,
                "hdmi_cable_type": HDMI_CABLE_COPPER,
                "ground_first_locking_connector": False,
            },
        )
        self.assertFalse(rep_g19.all_20_gates_verified)
        self.assertFalse(rep_g19.g19_to_g20_all_passed)
        self.assertEqual(rep_g19.status, STATUS_BLOCKED_GROUND_LOOP_HAZARD)

        rep_g20 = evaluate_20gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            power_failover_kwargs={"battery_less_usb_pd": True, "np_fz100_installed": False},
        )
        self.assertFalse(rep_g20.all_20_gates_verified)
        self.assertFalse(rep_g20.g19_to_g20_all_passed)
        self.assertEqual(rep_g20.status, STATUS_BLOCKED_BATTERY_RESERVE_INSUFFICIENT)

        rep_emmc = evaluate_20gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            request_persistent_emmc_writes=True,
        )
        self.assertFalse(rep_emmc.all_20_gates_verified)
        self.assertFalse(rep_emmc.offline_17_gates_verified)
        self.assertFalse(rep_emmc.overall_ready_for_hardware_attach)
        self.assertFalse(rep_emmc.persistent_emmc_writes_authorized)
        self.assertEqual(rep_emmc.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)

    def test_29_serialized_json_contains_zero_raw_bytes_repr(self) -> None:
        rep = evaluate_20gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
        )
        rendered = json.dumps(rep.to_dict(), ensure_ascii=False)
        self.assertNotRegex(rendered, r'(?<![0-9A-Za-z_/.-])b[\'"]')

    def test_30_20gate_preserves_g01_to_g18_untouched(self) -> None:
        r18 = evaluate_18_master_safety_gates(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            use_synthetic_dry_run_tier0=True,
        )
        r20 = evaluate_20gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
        )
        self.assertEqual(len(r18.gates), 18)
        self.assertEqual(len(r20.gates), 20)
        self.assertEqual(
            [g["gate_id"] for g in r18.gates],
            [g["gate_id"] for g in r20.gates[:18]],
        )
        self.assertEqual(
            [g["status"] for g in r18.gates],
            [g["status"] for g in r20.gates[:18]],
        )

    def test_31_cli_verify_20_gates_offline_and_dry_run_json(self) -> None:
        buf_off = io.StringIO()
        with contextlib.redirect_stdout(buf_off):
            rc_off = package_cli_main(["verify-20-gates", "--clean-room", "--json"])
        self.assertEqual(rc_off, 0)
        p_off = json.loads(buf_off.getvalue())
        self.assertEqual(p_off["schema"], RIG_GROUNDLOOP_20GATE_SCHEMA)
        self.assertEqual(p_off["summary"]["verified_gates"], 17)
        self.assertFalse(p_off["dry_run_rehearsal_only"])
        self.assertFalse(p_off["overall_ready_for_hardware_attach"])
        self.assertFalse(p_off["persistent_emmc_writes_authorized"])

        buf_dry = io.StringIO()
        with contextlib.redirect_stdout(buf_dry):
            rc_dry = package_cli_main(["verify-20-gates", "--clean-room", "--dry-run-simulated-backup", "--json"])
        self.assertEqual(rc_dry, 0)
        p_dry = json.loads(buf_dry.getvalue())
        self.assertEqual(p_dry["summary"]["verified_gates"], 20)
        self.assertTrue(p_dry["all_20_gates_verified"])
        self.assertTrue(p_dry["dry_run_rehearsal_only"])
        self.assertFalse(p_dry["overall_ready_for_hardware_attach"])
        self.assertFalse(p_dry["persistent_emmc_writes_authorized"])

    def test_32_module_cli_summary_and_failure_exit_code(self) -> None:
        buf_mod = io.StringIO()
        with contextlib.redirect_stdout(buf_mod):
            rc_mod = module_cli_main(["--clean-room"])
        self.assertEqual(rc_mod, 0)
        out = buf_mod.getvalue()
        self.assertIn("verified=17/20", out)
        self.assertIn("overall_ready_for_hardware_attach=False", out)
        self.assertIn("persistent_emmc_writes_authorized=False", out)

        with tempfile.TemporaryDirectory() as empty_dir:
            buf_fail = io.StringIO()
            with contextlib.redirect_stdout(buf_fail):
                rc_fail = package_cli_main(["verify-20-gates", "--repo-root", empty_dir, "--clean-room"])
            self.assertEqual(rc_fail, 1)


if __name__ == "__main__":
    unittest.main()
