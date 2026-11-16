"""Fast dual-mode unit tests for Phase 77 — XLR-H1 +48V Phantom Firewall, Gimbal/Follow-Focus/Laser-CMOS/Shutter Guard & 22-Gate Preflight (`G01..G22`)."""

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
from fx3_safety.phantom48v_gimbal_and_22gate_guard import (
    BALANCED_48V_CONDENSER_ALLOWLIST,
    FOLLOW_FOCUS_MOTOR_MAX_TORQUE_NM_UNCLAMPED,
    G21_GATE_CODE,
    G21_GATE_ID,
    G22_GATE_CODE,
    G22_GATE_ID,
    IBIS_MODE_ACTIVE,
    IBIS_MODE_OFF,
    IBIS_MODE_STANDARD,
    INPUT3_MODE_MIC_PIP_OFF,
    INPUT3_MODE_PLUG_IN_POWER_2V5,
    INPUT3_PIP_NOMINAL_V,
    LASER_CLASS_3B,
    LASER_CLASS_4,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHANTOM48V_GIMBAL_22GATE_SCHEMA,
    PHANTOM48V_GIMBAL_22GATE_VERSION,
    PHANTOM_48V_NOMINAL_V,
    PHANTOM_48V_SAFE_BLEED_MAX_V,
    SHUTTER_WHEN_POWER_OFF_CLOSED,
    SHUTTER_WHEN_POWER_OFF_OPEN,
    SOURCE_CONDENSER_BALANCED,
    SOURCE_DYNAMIC_MIC,
    SOURCE_LAV_PIP_3V5MM,
    SOURCE_LINE_MIXER,
    SOURCE_PASSIVE_RIBBON,
    SOURCE_SMPTE_LTC_GENERATOR,
    SOURCE_WIRELESS_RECEIVER_TRS_XLR,
    STATUS_BLOCKED_DONOR_INTEGRITY,
    STATUS_BLOCKED_GIMBAL_ACTIVE_IBIS_DRIFT,
    STATUS_BLOCKED_GIMBAL_DUAL_BUS_CONFLICT,
    STATUS_BLOCKED_PERSISTENT_EMMC_WRITE,
    STATUS_BLOCKED_PHANTOM_48V_HOTPLUG_TRANSIENT,
    STATUS_BLOCKED_PHANTOM_48V_TRANSDUCER_HAZARD,
    STATUS_BLOCKED_SHUTTER_CURTAIN_EXPOSED,
    STATUS_BLOCKED_UNCLAMPED_MOTOR_MOUNT_SHEAR,
    STATUS_BLOCKED_VENUE_LASER_CMOS_HAZARD,
    STATUS_BLOCKED_XLR_H1_MISHOE_ELECTRICAL,
    STATUS_SAFE,
    STATUS_VERIFIED_G21,
    STATUS_VERIFIED_G22,
    STATUS_VERIFIED_SAFE,
    XLR_H1_INPUT1,
    XLR_H1_INPUT2,
    XLR_H1_INPUT3,
    XLR_MODE_LINE,
    XLR_MODE_MIC,
    XLR_MODE_MIC_48V,
    audit_phase77_donor_contracts,
    default_safe_xlr_h1_channels,
    evaluate_22gate_preflight,
    evaluate_g21_xlr_phantom48v_and_hotpatch,
    evaluate_g22_gimbal_focus_torque_and_sensor_curtain,
    main as module_cli_main,
    verify_gimbal_focus_torque_and_laser_shutter_guard,
    verify_xlr_h1_channel,
    verify_xlr_h1_phantom_48v_firewall,
)
from fx3_safety.rig_groundloop_lensrail_and_20gate_guard import (
    STATUS_BLOCKED_GROUND_LOOP_HAZARD,
    STATUS_FAIL_OFFLINE_HARDWARE_NOT_ATTACHED,
    evaluate_20gate_preflight,
)


class Phantom48vGimbalAnd22GateGuardTests(unittest.TestCase):
    # --- 1. Hard Redlines, Package Exports & O_RDONLY Donor Audit ---

    def test_01_hard_locked_redlines_and_package_exports(self) -> None:
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(PERSISTENT_WRITE_RELEASE)
        self.assertEqual(PHANTOM48V_GIMBAL_22GATE_SCHEMA, "fx3-phantom48v-gimbal-22gate-preflight-v1")
        self.assertEqual(PHANTOM48V_GIMBAL_22GATE_VERSION, "1.0.0")
        for sym in (
            "PHANTOM48V_GIMBAL_22GATE_SCHEMA",
            "G21_GATE_ID",
            "G22_GATE_ID",
            "audit_phase77_donor_contracts",
            "default_safe_xlr_h1_channels",
            "verify_xlr_h1_channel",
            "verify_xlr_h1_phantom_48v_firewall",
            "verify_gimbal_focus_torque_and_laser_shutter_guard",
            "evaluate_g21_xlr_phantom48v_and_hotpatch",
            "evaluate_g22_gimbal_focus_torque_and_sensor_curtain",
            "evaluate_22gate_preflight",
            "evaluate_22_master_safety_gates",
            "phantom48v_gimbal_and_22gate_guard",
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
            res_default = audit_phase77_donor_contracts()
        self.assertTrue(res_default.valid)
        self.assertEqual(res_default.status, STATUS_VERIFIED_SAFE)
        self.assertEqual(res_default.access_mode, "O_RDONLY")
        self.assertEqual(len(res_default.missing_markers), 0)
        for path, flags in observed_flags:
            if any(k in path for k in ("libInfraHotshoe.so", "libInfraPtpExtCmd.so", "libUsbControl.so", "libInfraLensCommunicator.so")):
                self.assertEqual(flags & os.O_ACCMODE, os.O_RDONLY, f"Non-O_RDONLY open on {path}")

        res_clean = audit_phase77_donor_contracts(force_clean_room=True)
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
            for name in ("libfan.so", "libInfraPtpExtCmd.so", "libUsbControl.so", "libInfraLensCommunicator.so"):
                (fx3_lib / name).write_bytes(b"corrupt")
            for name in ("libfan.so", "libInfraHotshoe.so", "libInfraLensCommunicator.so"):
                (fx6_lib / name).write_bytes(b"corrupt")
            res = audit_phase77_donor_contracts(work_root=tmp, force_clean_room=False)
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_DONOR_INTEGRITY)
        self.assertEqual(len(res.missing_markers), 5)

    # --- 2. XLR-H1 +48V Phantom Transducer Burnout & Hot-Patch Firewall (G21) ---

    def test_04_xlr_h1_default_safe_3channel_configuration(self) -> None:
        res = verify_xlr_h1_phantom_48v_firewall()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_SAFE)
        self.assertEqual(len(res.channels), 3)
        self.assertTrue(res.hot_plug_discharge_safe)
        self.assertFalse(res.persistent_emmc_writes_authorized)

    def test_05_xlr_h1_allows_balanced_condenser_shotgun_and_boom_mics_on_48v(self) -> None:
        for mic in BALANCED_48V_CONDENSER_ALLOWLIST:
            ch = verify_xlr_h1_channel(
                channel_id=XLR_H1_INPUT1,
                input_mode=XLR_MODE_MIC_48V,
                source_type=mic,
                device_label=mic,
                phantom_48v_voltage_v=PHANTOM_48V_NOMINAL_V,
            )
            self.assertTrue(ch.valid, f"{mic} should be allowed on MIC+48V")
            self.assertTrue(ch.phantom_48v_enabled)

    def test_06_xlr_h1_blocks_passive_ribbon_mic_on_48v_without_isolation(self) -> None:
        res = verify_xlr_h1_phantom_48v_firewall(
            channel_id=XLR_H1_INPUT1,
            input_mode=XLR_MODE_MIC_48V,
            source_type=SOURCE_PASSIVE_RIBBON,
            device_label="Coles 4038 Passive Ribbon",
            cloudlifter_or_transformer_isolated=False,
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_PHANTOM_48V_TRANSDUCER_HAZARD)
        self.assertIn(STATUS_BLOCKED_PHANTOM_48V_TRANSDUCER_HAZARD, res.violation_codes)

    def test_07_xlr_h1_allows_passive_ribbon_on_mic_48v_off_or_with_cloudlifter_isolation(self) -> None:
        res_off = verify_xlr_h1_phantom_48v_firewall(
            channel_id=XLR_H1_INPUT1,
            input_mode=XLR_MODE_MIC,
            source_type=SOURCE_PASSIVE_RIBBON,
            device_label="Royer R-121 Passive Ribbon",
        )
        self.assertTrue(res_off.valid)

        res_iso = verify_xlr_h1_phantom_48v_firewall(
            channel_id=XLR_H1_INPUT1,
            input_mode=XLR_MODE_MIC_48V,
            source_type=SOURCE_PASSIVE_RIBBON,
            device_label="Royer R-121 + Cloudlifter CL-1",
            cloudlifter_or_transformer_isolated=True,
        )
        self.assertTrue(res_iso.valid)
        self.assertGreaterEqual(len(res_iso.warnings), 1)

    def test_08_xlr_h1_blocks_unbalanced_trs_to_xlr_wireless_receivers_on_48v(self) -> None:
        for rx in ("DJI Mic 2", "Rode Wireless PRO", "Sennheiser EW-DP"):
            res = verify_xlr_h1_phantom_48v_firewall(
                channel_id=XLR_H1_INPUT2,
                input_mode=XLR_MODE_MIC_48V,
                source_type=rx,
                device_label=rx,
                phantom_48v_voltage_v=48.0,
            )
            self.assertFalse(res.valid, f"{rx} on MIC+48V must be blocked")
            self.assertEqual(res.status, STATUS_BLOCKED_PHANTOM_48V_TRANSDUCER_HAZARD)

        # Safe when switched to LINE or MIC (48V OFF)
        for safe_mode in (XLR_MODE_LINE, XLR_MODE_MIC):
            res_ok = verify_xlr_h1_phantom_48v_firewall(
                channel_id=XLR_H1_INPUT2,
                input_mode=safe_mode,
                source_type=SOURCE_WIRELESS_RECEIVER_TRS_XLR,
                device_label="DJI Mic 2",
            )
            self.assertTrue(res_ok.valid)

    def test_09_xlr_h1_blocks_smpte_ltc_timecode_generator_on_48v(self) -> None:
        for ltc in ("Tentacle Sync E", "Deity TC-1"):
            res = verify_xlr_h1_phantom_48v_firewall(
                channel_id=XLR_H1_INPUT2,
                input_mode=XLR_MODE_MIC_48V,
                source_type=ltc,
                device_label=ltc,
                phantom_48v_voltage_v=48.0,
            )
            self.assertFalse(res.valid)
            self.assertEqual(res.status, STATUS_BLOCKED_PHANTOM_48V_TRANSDUCER_HAZARD)

        res_ok = verify_xlr_h1_phantom_48v_firewall(
            channel_id=XLR_H1_INPUT2,
            input_mode=XLR_MODE_MIC,
            source_type=SOURCE_SMPTE_LTC_GENERATOR,
            device_label="Tentacle Sync E",
        )
        self.assertTrue(res_ok.valid)

    def test_10_xlr_h1_blocks_dynamic_and_line_sources_on_48v_requires_48v_off(self) -> None:
        res_dyn = verify_xlr_h1_phantom_48v_firewall(
            channel_id=XLR_H1_INPUT1,
            input_mode=XLR_MODE_MIC_48V,
            source_type=SOURCE_DYNAMIC_MIC,
            device_label="Shure SM58",
        )
        self.assertFalse(res_dyn.valid)
        self.assertEqual(res_dyn.status, STATUS_BLOCKED_PHANTOM_48V_TRANSDUCER_HAZARD)

        res_dyn_ok = verify_xlr_h1_phantom_48v_firewall(
            channel_id=XLR_H1_INPUT1,
            input_mode=XLR_MODE_MIC,
            source_type=SOURCE_DYNAMIC_MIC,
            device_label="Shure SM58",
        )
        self.assertTrue(res_dyn_ok.valid)

        res_line_48 = verify_xlr_h1_phantom_48v_firewall(
            channel_id=XLR_H1_INPUT2,
            input_mode=XLR_MODE_MIC_48V,
            source_type=SOURCE_LINE_MIXER,
            device_label="Sound Devices MixPre Line Out",
            phantom_48v_voltage_v=48.0,
        )
        self.assertFalse(res_line_48.valid)

    def test_11_xlr_h1_hotplug_interlock_requires_adc_mute_boost_off_and_1v_discharge(self) -> None:
        # Fail if boost still energized
        res_boost = verify_xlr_h1_phantom_48v_firewall(
            channel_id=XLR_H1_INPUT1,
            input_mode=XLR_MODE_MIC_48V,
            source_type=SOURCE_CONDENSER_BALANCED,
            hot_plug_event=True,
            adc_mute_ramped=True,
            phantom_48v_boost_energized=True,
            residual_phantom_voltage_v=0.4,
        )
        self.assertFalse(res_boost.valid)
        self.assertFalse(res_boost.hot_plug_discharge_safe)
        self.assertEqual(res_boost.status, STATUS_BLOCKED_PHANTOM_48V_TRANSDUCER_HAZARD)
        self.assertIn(STATUS_BLOCKED_PHANTOM_48V_HOTPLUG_TRANSIENT, res_boost.violation_codes)

        # Fail if ADC mute not ramped
        res_unmuted = verify_xlr_h1_phantom_48v_firewall(
            channel_id=XLR_H1_INPUT1,
            input_mode=XLR_MODE_MIC,
            source_type=SOURCE_CONDENSER_BALANCED,
            hot_plug_event=True,
            adc_mute_ramped=False,
            phantom_48v_boost_energized=False,
            residual_phantom_voltage_v=0.2,
        )
        self.assertFalse(res_unmuted.valid)
        self.assertFalse(res_unmuted.hot_plug_discharge_safe)

        # Fail if residual phantom > 1.0V
        res_resid = verify_xlr_h1_phantom_48v_firewall(
            channel_id=XLR_H1_INPUT1,
            input_mode=XLR_MODE_MIC,
            source_type=SOURCE_CONDENSER_BALANCED,
            hot_plug_event=True,
            adc_mute_ramped=True,
            phantom_48v_boost_energized=False,
            residual_phantom_voltage_v=4.6,
        )
        self.assertFalse(res_resid.valid)
        self.assertFalse(res_resid.hot_plug_discharge_safe)

        # Pass when ADC mute ramped, boost off, and residual <= 1.0V
        res_safe = verify_xlr_h1_phantom_48v_firewall(
            channel_id=XLR_H1_INPUT1,
            input_mode=XLR_MODE_MIC,
            source_type=SOURCE_CONDENSER_BALANCED,
            hot_plug_event=True,
            adc_mute_ramped=True,
            phantom_48v_boost_energized=False,
            residual_phantom_voltage_v=PHANTOM_48V_SAFE_BLEED_MAX_V,
        )
        self.assertTrue(res_safe.valid)
        self.assertTrue(res_safe.hot_plug_discharge_safe)

    def test_12_xlr_h1_input3_3v5mm_plug_in_power_and_48v_ban(self) -> None:
        ch_ok = verify_xlr_h1_channel(
            channel_id=XLR_H1_INPUT3,
            input_mode=INPUT3_MODE_PLUG_IN_POWER_2V5,
            source_type=SOURCE_LAV_PIP_3V5MM,
            plug_in_power_v=INPUT3_PIP_NOMINAL_V,
        )
        self.assertTrue(ch_ok.valid)
        self.assertFalse(ch_ok.phantom_48v_enabled)

        ch_48_bad = verify_xlr_h1_channel(
            channel_id=XLR_H1_INPUT3,
            input_mode=XLR_MODE_MIC_48V,
            source_type=SOURCE_LAV_PIP_3V5MM,
            phantom_48v_voltage_v=48.0,
        )
        self.assertFalse(ch_48_bad.valid)
        self.assertEqual(ch_48_bad.violation_codes[0], STATUS_BLOCKED_PHANTOM_48V_TRANSDUCER_HAZARD)

        ch_over_pip = verify_xlr_h1_channel(
            channel_id=XLR_H1_INPUT3,
            input_mode=INPUT3_MODE_PLUG_IN_POWER_2V5,
            source_type=SOURCE_LAV_PIP_3V5MM,
            plug_in_power_v=5.0,
        )
        self.assertFalse(ch_over_pip.valid)

        ch_pip_off_leak = verify_xlr_h1_channel(
            channel_id=XLR_H1_INPUT3,
            input_mode=INPUT3_MODE_MIC_PIP_OFF,
            source_type=SOURCE_LAV_PIP_3V5MM,
            plug_in_power_v=2.5,
        )
        self.assertFalse(ch_pip_off_leak.valid)

    def test_13_xlr_h1_blocks_mishoe_electrical_out_of_bounds_and_multi_channel_fault(self) -> None:
        res_elec = verify_xlr_h1_phantom_48v_firewall(xlr_h1_logic_vdd_v=3.45, xlr_h1_unreg_v=9.5)
        self.assertFalse(res_elec.valid)
        self.assertEqual(res_elec.status, STATUS_BLOCKED_XLR_H1_MISHOE_ELECTRICAL)

        bad_batch = list(default_safe_xlr_h1_channels())
        bad_batch[1] = {
            "channel_id": XLR_H1_INPUT2,
            "input_mode": XLR_MODE_MIC_48V,
            "source_type": SOURCE_SMPTE_LTC_GENERATOR,
            "device_label": "Tentacle Sync E",
            "phantom_48v_voltage_v": 48.0,
        }
        res_batch = verify_xlr_h1_phantom_48v_firewall(channels=bad_batch)
        self.assertFalse(res_batch.valid)
        self.assertEqual(res_batch.status, STATUS_BLOCKED_PHANTOM_48V_TRANSDUCER_HAZARD)

    # --- 3. Gimbal, Follow-Focus Torque & Laser-CMOS / Shutter Curtain Guard (G22) ---

    def test_14_gimbal_default_safe_configuration(self) -> None:
        res = verify_gimbal_focus_torque_and_laser_shutter_guard()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_SAFE)
        self.assertTrue(res.single_control_bus_arbitrated)
        self.assertTrue(res.ibis_gimbal_drift_safe)
        self.assertTrue(res.follow_focus_shear_safe)
        self.assertTrue(res.laser_cmos_safe)
        self.assertTrue(res.shutter_curtain_safe)
        self.assertTrue(res.shutter_blade_parked_open)
        self.assertFalse(res.persistent_emmc_writes_authorized)

    def test_15_follow_focus_blocks_uncalibrated_infinite_spin_without_rod_clamp(self) -> None:
        res = verify_gimbal_focus_torque_and_laser_shutter_guard(
            fly_by_wire_emount=True,
            lens_has_hard_stops=False,
            lens_support_rod_clamp_installed=False,
            soft_ab_stops_calibrated=False,
            infinite_spin_uncalibrated=True,
            motor_voltage_v=14.8,
            motor_torque_nm=0.60,
        )
        self.assertFalse(res.valid)
        self.assertFalse(res.follow_focus_shear_safe)
        self.assertEqual(res.status, STATUS_BLOCKED_UNCLAMPED_MOTOR_MOUNT_SHEAR)

    def test_16_follow_focus_blocks_high_torque_over_035nm_without_rod_clamp(self) -> None:
        res = verify_gimbal_focus_torque_and_laser_shutter_guard(
            fly_by_wire_emount=True,
            lens_has_hard_stops=False,
            lens_support_rod_clamp_installed=False,
            soft_ab_stops_calibrated=True,
            infinite_spin_uncalibrated=False,
            motor_voltage_v=14.8,
            motor_torque_nm=0.55,
        )
        self.assertFalse(res.valid)
        self.assertFalse(res.follow_focus_shear_safe)
        self.assertEqual(res.status, STATUS_BLOCKED_UNCLAMPED_MOTOR_MOUNT_SHEAR)

    def test_17_follow_focus_allows_calibrated_low_torque_or_rod_clamp_installed(self) -> None:
        res_low_t = verify_gimbal_focus_torque_and_laser_shutter_guard(
            fly_by_wire_emount=True,
            lens_has_hard_stops=False,
            lens_support_rod_clamp_installed=False,
            soft_ab_stops_calibrated=True,
            infinite_spin_uncalibrated=False,
            motor_voltage_v=14.8,
            motor_torque_nm=FOLLOW_FOCUS_MOTOR_MAX_TORQUE_NM_UNCLAMPED,
        )
        self.assertTrue(res_low_t.valid)
        self.assertTrue(res_low_t.follow_focus_shear_safe)

        res_clamp = verify_gimbal_focus_torque_and_laser_shutter_guard(
            fly_by_wire_emount=True,
            lens_has_hard_stops=False,
            lens_support_rod_clamp_installed=True,
            soft_ab_stops_calibrated=False,
            infinite_spin_uncalibrated=True,
            motor_voltage_v=14.8,
            motor_torque_nm=0.80,
        )
        self.assertTrue(res_clamp.valid)
        self.assertTrue(res_clamp.follow_focus_shear_safe)
        self.assertGreaterEqual(len(res_clamp.warnings), 1)

    def test_18_follow_focus_blocks_infinite_spin_even_at_low_torque_without_clamp(self) -> None:
        res = verify_gimbal_focus_torque_and_laser_shutter_guard(
            fly_by_wire_emount=True,
            lens_has_hard_stops=False,
            lens_support_rod_clamp_installed=False,
            soft_ab_stops_calibrated=True,
            infinite_spin_uncalibrated=True,
            motor_torque_nm=0.20,
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_UNCLAMPED_MOTOR_MOUNT_SHEAR)

    def test_19_gimbal_blocks_simultaneous_usbc_crsdk_and_multiport_rss_conflict(self) -> None:
        res = verify_gimbal_focus_torque_and_laser_shutter_guard(
            gimbal_model="DJI RS4 Pro",
            usb_c_crsdk_active=True,
            multiport_rss_active=True,
        )
        self.assertFalse(res.valid)
        self.assertFalse(res.single_control_bus_arbitrated)
        self.assertEqual(res.status, STATUS_BLOCKED_GIMBAL_DUAL_BUS_CONFLICT)

        res_rss_only = verify_gimbal_focus_torque_and_laser_shutter_guard(
            gimbal_model="DJI RS3 Pro",
            usb_c_crsdk_active=False,
            multiport_rss_active=True,
        )
        self.assertTrue(res_rss_only.valid)
        self.assertTrue(res_rss_only.single_control_bus_arbitrated)

    def test_20_gimbal_pan_follow_blocks_active_ibis_crop_drift_allows_standard_and_off(self) -> None:
        res_active = verify_gimbal_focus_torque_and_laser_shutter_guard(
            gimbal_pan_follow_active=True,
            ibis_mode=IBIS_MODE_ACTIVE,
        )
        self.assertFalse(res_active.valid)
        self.assertFalse(res_active.ibis_gimbal_drift_safe)
        self.assertEqual(res_active.status, STATUS_BLOCKED_GIMBAL_ACTIVE_IBIS_DRIFT)

        for safe_ibis in (IBIS_MODE_STANDARD, IBIS_MODE_OFF):
            res_ok = verify_gimbal_focus_torque_and_laser_shutter_guard(
                gimbal_pan_follow_active=True,
                ibis_mode=safe_ibis,
            )
            self.assertTrue(res_ok.valid)
            self.assertTrue(res_ok.ibis_gimbal_drift_safe)

    def test_21_venue_class3b_4_laser_guard_blocks_unfiltered_and_warns_filtered(self) -> None:
        res_unfiltered = verify_gimbal_focus_torque_and_laser_shutter_guard(
            venue_laser_present=True,
            laser_class=LASER_CLASS_4,
            optical_laser_cut_filter_installed=False,
        )
        self.assertFalse(res_unfiltered.valid)
        self.assertTrue(res_unfiltered.laser_hazard_flagged)
        self.assertFalse(res_unfiltered.laser_cmos_safe)
        self.assertEqual(res_unfiltered.status, STATUS_BLOCKED_VENUE_LASER_CMOS_HAZARD)

        res_3b = verify_gimbal_focus_torque_and_laser_shutter_guard(
            venue_laser_present=False,
            laser_class=LASER_CLASS_3B,
            optical_laser_cut_filter_installed=False,
        )
        self.assertFalse(res_3b.valid)
        self.assertEqual(res_3b.status, STATUS_BLOCKED_VENUE_LASER_CMOS_HAZARD)

        res_filtered = verify_gimbal_focus_torque_and_laser_shutter_guard(
            venue_laser_present=True,
            laser_class=LASER_CLASS_4,
            optical_laser_cut_filter_installed=True,
        )
        self.assertTrue(res_filtered.valid)
        self.assertTrue(res_filtered.laser_hazard_flagged)
        self.assertTrue(res_filtered.laser_cmos_safe)
        self.assertGreaterEqual(len(res_filtered.warnings), 1)

    def test_22_shutter_dust_curtain_park_open_check_and_lens_cap_ack(self) -> None:
        res_default = verify_gimbal_focus_torque_and_laser_shutter_guard()
        self.assertTrue(res_default.valid)
        self.assertEqual(res_default.shutter_when_power_off, SHUTTER_WHEN_POWER_OFF_OPEN)
        self.assertTrue(res_default.shutter_blade_parked_open)

        res_closed_unacked = verify_gimbal_focus_torque_and_laser_shutter_guard(
            shutter_when_power_off=SHUTTER_WHEN_POWER_OFF_CLOSED,
            lens_cap_swap_rule_acknowledged=False,
        )
        self.assertFalse(res_closed_unacked.valid)
        self.assertFalse(res_closed_unacked.shutter_curtain_safe)
        self.assertEqual(res_closed_unacked.status, STATUS_BLOCKED_SHUTTER_CURTAIN_EXPOSED)

        res_closed_acked = verify_gimbal_focus_torque_and_laser_shutter_guard(
            shutter_when_power_off=SHUTTER_WHEN_POWER_OFF_CLOSED,
            lens_cap_swap_rule_acknowledged=True,
        )
        self.assertTrue(res_closed_acked.valid)
        self.assertTrue(res_closed_acked.shutter_curtain_safe)
        self.assertGreaterEqual(len(res_closed_acked.warnings), 1)

    def test_23_g21_and_g22_block_cp_mutation_and_persistent_emmc_writes(self) -> None:
        res_cp = verify_gimbal_focus_torque_and_laser_shutter_guard(cp_mutation_bytes=8)
        self.assertFalse(res_cp.valid)
        self.assertEqual(res_cp.status, STATUS_BLOCKED_UNCLAMPED_MOTOR_MOUNT_SHEAR)

        res_emmc_21 = verify_xlr_h1_phantom_48v_firewall(request_persistent_emmc_writes=True)
        self.assertFalse(res_emmc_21.valid)
        self.assertEqual(res_emmc_21.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        self.assertFalse(res_emmc_21.persistent_emmc_writes_authorized)

        res_emmc_22 = verify_gimbal_focus_torque_and_laser_shutter_guard(request_persistent_emmc_writes=True)
        self.assertFalse(res_emmc_22.valid)
        self.assertEqual(res_emmc_22.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        self.assertFalse(res_emmc_22.persistent_emmc_writes_authorized)

    # --- 4. Gate G21 & G22 Evaluators & 22-Gate Master Safety Preflight ---

    def test_24_g21_and_g22_verdicts_dual_mode(self) -> None:
        v21, r21 = evaluate_g21_xlr_phantom48v_and_hotpatch(force_clean_room=True)
        self.assertTrue(v21.passed)
        self.assertEqual(v21.gate_id, G21_GATE_ID)
        self.assertEqual(v21.gate_code, G21_GATE_CODE)
        self.assertEqual(v21.status, STATUS_VERIFIED_G21)
        self.assertFalse(r21.persistent_emmc_writes_authorized)

        v22, r22 = evaluate_g22_gimbal_focus_torque_and_sensor_curtain(force_clean_room=True)
        self.assertTrue(v22.passed)
        self.assertEqual(v22.gate_id, G22_GATE_ID)
        self.assertEqual(v22.gate_code, G22_GATE_CODE)
        self.assertEqual(v22.status, STATUS_VERIFIED_G22)
        self.assertFalse(r22.persistent_emmc_writes_authorized)

    def test_25_22gate_offline_default_19_of_22_and_g10_g12_fail_offline(self) -> None:
        rep = evaluate_22gate_preflight(DEFAULT_REPO_ROOT, force_clean_room=True)
        self.assertEqual(rep.schema, PHANTOM48V_GIMBAL_22GATE_SCHEMA)
        self.assertEqual(len(rep.gates), 22)
        self.assertEqual(rep.summary["total_gates"], 22)
        self.assertEqual(rep.summary["verified_gates"], 19)
        self.assertEqual(rep.summary["blocked_or_pending_gates"], 3)
        self.assertTrue(rep.offline_19_gates_verified)
        self.assertFalse(rep.all_22_gates_verified)
        self.assertFalse(rep.dry_run_rehearsal_only)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.persistent_write_release)
        for idx in (9, 10, 11):
            self.assertFalse(rep.gates[idx]["passed"])
            self.assertEqual(rep.gates[idx]["status"], STATUS_FAIL_OFFLINE_HARDWARE_NOT_ATTACHED)

    def test_26_22gate_dry_run_simulated_backup_22_of_22_and_redlines_locked(self) -> None:
        rep = evaluate_22gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
        )
        self.assertEqual(len(rep.gates), 22)
        self.assertEqual(rep.summary["verified_gates"], 22)
        self.assertEqual(rep.summary["blocked_or_pending_gates"], 0)
        self.assertTrue(rep.all_22_gates_verified)
        self.assertTrue(rep.dry_run_rehearsal_only)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.persistent_write_release)
        self.assertTrue(all(g["passed"] for g in rep.gates))

    def test_27_22gate_propagates_g21_g22_g19_failures_and_emmc_redline(self) -> None:
        rep_g21 = evaluate_22gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            xlr_kwargs={
                "channel_id": XLR_H1_INPUT1,
                "input_mode": XLR_MODE_MIC_48V,
                "source_type": SOURCE_PASSIVE_RIBBON,
            },
        )
        self.assertFalse(rep_g21.all_22_gates_verified)
        self.assertFalse(rep_g21.g21_to_g22_all_passed)
        self.assertEqual(rep_g21.status, STATUS_BLOCKED_PHANTOM_48V_TRANSDUCER_HAZARD)

        rep_g22 = evaluate_22gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            gimbal_kwargs={"usb_c_crsdk_active": True, "multiport_rss_active": True},
        )
        self.assertFalse(rep_g22.all_22_gates_verified)
        self.assertFalse(rep_g22.g21_to_g22_all_passed)
        self.assertEqual(rep_g22.status, STATUS_BLOCKED_GIMBAL_DUAL_BUS_CONFLICT)

        rep_g19 = evaluate_22gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            rig_kwargs={"hot_plug_hdmi_while_powered": True},
        )
        self.assertFalse(rep_g19.all_22_gates_verified)
        self.assertEqual(rep_g19.status, STATUS_BLOCKED_GROUND_LOOP_HAZARD)

        rep_emmc = evaluate_22gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            request_persistent_emmc_writes=True,
        )
        self.assertFalse(rep_emmc.all_22_gates_verified)
        self.assertFalse(rep_emmc.offline_19_gates_verified)
        self.assertFalse(rep_emmc.overall_ready_for_hardware_attach)
        self.assertFalse(rep_emmc.persistent_emmc_writes_authorized)
        self.assertEqual(rep_emmc.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)

    def test_28_22gate_preserves_g01_to_g20_untouched(self) -> None:
        r20 = evaluate_20gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
        )
        r22 = evaluate_22gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
        )
        self.assertEqual(len(r20.gates), 20)
        self.assertEqual(len(r22.gates), 22)
        self.assertEqual(
            [g["gate_id"] for g in r20.gates],
            [g["gate_id"] for g in r22.gates[:20]],
        )
        self.assertEqual(
            [g["status"] for g in r20.gates],
            [g["status"] for g in r22.gates[:20]],
        )

    def test_29_serialized_json_contains_zero_raw_bytes_repr(self) -> None:
        rep = evaluate_22gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
        )
        rendered = json.dumps(rep.to_dict(), ensure_ascii=False)
        self.assertNotRegex(rendered, r'(?<![0-9A-Za-z_/.-])b[\'"]')

    def test_30_cli_verify_22_gates_offline_and_dry_run_json(self) -> None:
        buf_off = io.StringIO()
        with contextlib.redirect_stdout(buf_off):
            rc_off = package_cli_main(["verify-22-gates", "--clean-room", "--json"])
        self.assertEqual(rc_off, 0)
        p_off = json.loads(buf_off.getvalue())
        self.assertEqual(p_off["schema"], PHANTOM48V_GIMBAL_22GATE_SCHEMA)
        self.assertEqual(p_off["summary"]["verified_gates"], 19)
        self.assertFalse(p_off["dry_run_rehearsal_only"])
        self.assertFalse(p_off["overall_ready_for_hardware_attach"])
        self.assertFalse(p_off["persistent_emmc_writes_authorized"])

        buf_dry = io.StringIO()
        with contextlib.redirect_stdout(buf_dry):
            rc_dry = package_cli_main(["verify-22-gates", "--clean-room", "--dry-run-simulated-backup", "--json"])
        self.assertEqual(rc_dry, 0)
        p_dry = json.loads(buf_dry.getvalue())
        self.assertEqual(p_dry["summary"]["verified_gates"], 22)
        self.assertTrue(p_dry["all_22_gates_verified"])
        self.assertTrue(p_dry["dry_run_rehearsal_only"])
        self.assertFalse(p_dry["overall_ready_for_hardware_attach"])
        self.assertFalse(p_dry["persistent_emmc_writes_authorized"])

    def test_31_module_cli_summary_and_failure_exit_code(self) -> None:
        buf_mod = io.StringIO()
        with contextlib.redirect_stdout(buf_mod):
            rc_mod = module_cli_main(["--clean-room"])
        self.assertEqual(rc_mod, 0)
        out = buf_mod.getvalue()
        self.assertIn("verified=19/22", out)
        self.assertIn("overall_ready_for_hardware_attach=False", out)
        self.assertIn("persistent_emmc_writes_authorized=False", out)

        with tempfile.TemporaryDirectory() as empty_dir:
            buf_fail = io.StringIO()
            with contextlib.redirect_stdout(buf_fail):
                rc_fail = package_cli_main(["verify-22-gates", "--repo-root", empty_dir, "--clean-room"])
            self.assertEqual(rc_fail, 1)

    def test_32_env_force_clean_room_honored_end_to_end(self) -> None:
        with patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            rep = evaluate_22gate_preflight(DEFAULT_REPO_ROOT)
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(rep.clean_room_forced)
        self.assertTrue(rep.offline_19_gates_verified)
        self.assertFalse(rep.persistent_emmc_writes_authorized)

    def test_33_xlr_h1_rejects_48v_voltage_leak_when_mode_is_mic_or_line(self) -> None:
        ch_leak = verify_xlr_h1_channel(
            channel_id=XLR_H1_INPUT2,
            input_mode=XLR_MODE_LINE,
            source_type=SOURCE_WIRELESS_RECEIVER_TRS_XLR,
            phantom_48v_voltage_v=12.0,
        )
        self.assertFalse(ch_leak.valid)
        self.assertIn(STATUS_BLOCKED_PHANTOM_48V_TRANSDUCER_HAZARD, ch_leak.violation_codes)

    def test_34_gimbal_detached_skips_pan_follow_ibis_drift_and_rejects_negative_torque(self) -> None:
        res_detached = verify_gimbal_focus_torque_and_laser_shutter_guard(
            gimbal_attached=False,
            usb_c_crsdk_active=False,
            multiport_rss_active=False,
            gimbal_pan_follow_active=False,
            ibis_mode=IBIS_MODE_ACTIVE,
        )
        self.assertTrue(res_detached.valid)

        res_neg = verify_gimbal_focus_torque_and_laser_shutter_guard(motor_torque_nm=-0.2)
        self.assertFalse(res_neg.valid)
        self.assertEqual(res_neg.status, STATUS_BLOCKED_UNCLAMPED_MOTOR_MOUNT_SHEAR)


if __name__ == "__main__":
    unittest.main()
