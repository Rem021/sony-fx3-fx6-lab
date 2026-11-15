#!/usr/bin/env python3
"""Phase 150 Test Suite — Stage 26 (`26/26`) Real-Hardware Main Track Part 9:
FX3 Body Controls, 5-Axis IBIS `0x0400 -> 0x1400` Center-Lock Parking,
`XLR-H1` Hot-Plug, Cooling Fan PWM & `NP-FZ100`/`USB-PD` HIL Co-Emulator.

Exercises 46 fast dual-mode unit, integration, Pillar A–D HIL, Stage 26 suite
orchestration, CLI, runtime budget (< 0.9s clean-room / < 2.2s local), and
source hygiene tests, strictly offline and hardware-free.
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

TESTS_DIR = Path(__file__).resolve().parent
FX3_VM_DIR = TESTS_DIR.parent
REPO_ROOT = FX3_VM_DIR.parents[1]
if str(FX3_VM_DIR) not in sys.path:
    sys.path.insert(0, str(FX3_VM_DIR))

import fx3_vm_coemulation_suite as suite  # noqa: E402
import realhw_body_peripheral_ibis_fan_power_coemulator as p150  # noqa: E402


_AUDIT_CACHE: dict = {}


def _get_clean_room_audit() -> dict:
    if "clean" not in _AUDIT_CACHE:
        _AUDIT_CACHE["clean"] = p150.run_phase150_realhw_body_peripheral_hil(force_clean_room=True)
    return _AUDIT_CACHE["clean"]


class TestPhase150DonorInspectionAndCleanRoom(unittest.TestCase):
    """Dual-mode O_RDONLY donor audit and deterministic clean-room baseline."""

    def test_01_clean_room_donor_audit_verifies_all_13_artifacts(self) -> None:
        rep = _get_clean_room_audit()
        self.assertEqual(rep["schema"], p150.PHASE_150_SCHEMA)
        self.assertEqual(rep["version"], p150.PHASE_150_VERSION)
        self.assertTrue(rep["all_checks_passed"])
        self.assertEqual(rep["source_mode"], "CLEAN_ROOM_SYNTHETIC")
        da = rep["donor_audit"]
        self.assertEqual(da["access_mode"], "O_RDONLY")
        self.assertEqual(da["donor_files_inspected"], 13)
        self.assertTrue(da["lens_comm_1to1_match"])
        self.assertTrue(da["sencore_1to1_match"])
        self.assertTrue(da["all_contracts_verified"])

    def test_02_clean_room_lens_comm_and_sencore_exact_export_import_counts(self) -> None:
        da = _get_clean_room_audit()["donor_audit"]
        self.assertEqual(da["fx3_lens_comm"]["export_count"], 27)
        self.assertEqual(da["fx3_lens_comm"]["import_count"], 25)
        self.assertEqual(da["fx6_lens_comm"]["export_count"], 27)
        self.assertEqual(da["fx6_lens_comm"]["import_count"], 25)
        self.assertEqual(da["fx3_sencore"]["export_count"], 355)
        self.assertEqual(da["fx3_sencore"]["import_count"], 130)
        self.assertEqual(da["fx6_sencore"]["export_count"], 355)
        self.assertEqual(da["fx6_sencore"]["import_count"], 130)

    def test_03_clean_room_cpapp_liroseq_lensfile_and_bk4_counts(self) -> None:
        da = _get_clean_room_audit()["donor_audit"]
        self.assertEqual(da["fx3_cpapp"]["liroseq_count"], 529)
        self.assertEqual(da["fx6_cpapp"]["liroseq_count"], 148)
        self.assertEqual(da["fx6_lensfile"]["magic_tag_ascii"], "VX8900")
        self.assertTrue(da["fx6_lensfile"]["read_only_verified"])
        self.assertEqual(da["fx3_backup"]["magic_ascii"], "BK4")
        self.assertEqual(da["fx3_backup"]["subsystem_count"], 819)
        self.assertEqual(da["fx6_backup"]["magic_ascii"], "BK4")
        self.assertEqual(da["fx6_backup"]["subsystem_count"], 840)

    def test_04_local_donor_o_rdonly_parity_when_present(self) -> None:
        if p150.is_forced_clean_room():
            self.skipTest("Forced clean-room via FX3_FX6_FORCE_CLEAN_ROOM=1")
        paths = p150.resolve_phase150_donor_paths()
        if not all(p.is_file() for p in paths.values()):
            self.skipTest("Optional local Sony BYOF donor binaries absent on this host")
        rep = p150.run_phase150_realhw_body_peripheral_hil(force_clean_room=False)
        self.assertTrue(rep["all_checks_passed"])
        self.assertEqual(rep["source_mode"], "LOCAL_DONOR_RDONLY")
        da = rep["donor_audit"]
        for key, exp_bytes in p150.EXPECTED_DONOR_BYTES.items():
            self.assertEqual(da[key]["file_bytes"], exp_bytes, msg=f"size mismatch for {key}")
        self.assertEqual(da["fx3_cpapp"]["liroseq_count"], 529)
        self.assertEqual(da["fx6_cpapp"]["liroseq_count"], 148)
        self.assertEqual(da["fx6_lensfile"]["magic_tag_ascii"], "VX8900")
        self.assertEqual(da["fx3_backup"]["subsystem_count"], 819)
        self.assertEqual(da["fx6_backup"]["subsystem_count"], 840)

    def test_05_stage26_clean_room_execution_fast_and_redlines_locked(self) -> None:
        t0 = time.monotonic()
        rep = p150.run_phase150_realhw_body_peripheral_hil(force_clean_room=True)
        dt = time.monotonic() - t0
        self.assertLess(dt, 0.15)
        self.assertTrue(rep["all_checks_passed"])
        red = rep["redlines"]
        self.assertTrue(red["p8_cp_mutation_forbidden"])
        self.assertEqual(red["cp_mutation_bytes"], 0)
        self.assertEqual(red["p18_mutation_bytes"], 0)
        self.assertFalse(red["p18_lens_writes_permitted"])
        self.assertEqual(red["floating_coil_ms"], 0)
        self.assertEqual(red["sdi_blocking_wait_ms"], 0.0)
        self.assertEqual(red["false_19v5_dcin_alarms"], 0)
        self.assertEqual(red["emmc_nflasha_write_count"], 0)
        self.assertFalse(red["persistent_emmc_writes_authorized"])


class TestPillarAIbisCenterLockAndEmountP18RoGuard(unittest.TestCase):
    """Pillar A: 5-axis IBIS LiroSeq 0x0400->0x1400 Center-Lock & p18:/lens RO guard."""

    def test_06_ibis_full_lifecycle_zero_floating_coil_ms(self) -> None:
        res = p150.simulate_ibis_center_lock_lifecycle()
        self.assertTrue(res.valid)
        self.assertTrue(res.rigid_sensor_query_masked)
        self.assertEqual(res.fx3_liroseq_sites, 529)
        self.assertEqual(res.floating_coil_ms, 0)
        self.assertTrue(res.ibis_coil_safe_park_verified)
        self.assertEqual(res.ibis_endstop_slam_events, 0)
        self.assertEqual(len(res.transitions), 5)

    def test_07_ibis_off_and_power_down_engage_0x0400_to_0x1400(self) -> None:
        res = p150.simulate_ibis_center_lock_lifecycle()
        off_t = res.transitions[3]
        pd_t = res.transitions[4]
        for tr in (off_t, pd_t):
            self.assertEqual(tr.cmd_opcode_hex, "0x0400")
            self.assertEqual(tr.ack_opcode_hex, "0x1400")
            self.assertTrue(tr.center_lock_engaged)
            self.assertEqual(tr.floating_coil_ms, 0)

    def test_08_ibis_unmasked_fx6_rigid_sensor_query_detected_and_blocked(self) -> None:
        res = p150.simulate_ibis_center_lock_lifecycle(mask_fx6_rigid_sensor_query=False)
        self.assertFalse(res.valid)
        self.assertEqual(res.status, "BLOCKED_FLOATING_IBIS_COIL_HAZARD")
        self.assertGreater(res.floating_coil_ms, 0)
        self.assertFalse(res.ibis_coil_safe_park_verified)

    def test_09_ibis_park_abort_fault_injection_detected(self) -> None:
        res = p150.simulate_ibis_center_lock_lifecycle(abort_park_fault=True)
        self.assertFalse(res.valid)
        self.assertEqual(res.status, "BLOCKED_IBIS_CENTER_LOCK_TIMEOUT")
        self.assertGreater(res.floating_coil_ms, 0)
        self.assertEqual(res.ibis_endstop_slam_events, 1)

    def test_10_ibis_invalid_step_raises_error(self) -> None:
        with self.assertRaises(p150.RealHwBodyPeripheralCoEmulatorError):
            p150.simulate_ibis_center_lock_lifecycle(requested_sequence=("INVALID_STEP",))
        with self.assertRaises(p150.RealHwBodyPeripheralCoEmulatorError):
            p150.simulate_ibis_center_lock_lifecycle(requested_sequence=())

    def test_11_emount_12pin_telemetry_tstop_fstop_and_breathing(self) -> None:
        t_res = p150.evaluate_emount_p18_ro_telemetry(
            focal_length_mm=50.0,
            aperture_value=1.4,
            aperture_unit="T_STOP",
            breathing_comp_enabled=True,
            power_zoom_step=6,
        )
        self.assertTrue(t_res.valid)
        self.assertEqual(t_res.aperture_display, "T1.4")
        self.assertEqual(t_res.p18_lensfile_tag, "VX8900")
        self.assertEqual(t_res.p18_mutation_bytes, 0)
        self.assertFalse(t_res.p18_lens_writes_permitted)

        f_res = p150.evaluate_emount_p18_ro_telemetry(
            focal_length_mm=24.0,
            aperture_value=2.8,
            aperture_unit="F_STOP",
            breathing_comp_enabled=False,
        )
        self.assertTrue(f_res.valid)
        self.assertEqual(f_res.aperture_display, "F2.8")

    def test_12_emount_p18_and_emmc_write_attempts_hard_blocked(self) -> None:
        for target in (
            "p18:/lens/lensfile.bin",
            "/dev/nflasha18",
            "/lens/lensfile.bin",
            "p2:/Backup.bin",
            "p8:/cpapp-b.bin",
            "/dev/cnflasha15",
        ):
            res = p150.evaluate_emount_p18_ro_telemetry(write_target=target)
            self.assertFalse(res.valid, msg=f"Write target {target} was not blocked")
            self.assertTrue(res.write_blocked)
            self.assertEqual(res.status, "BLOCKED_P18_RO_GUARD")
            self.assertEqual(res.p18_mutation_bytes, 0)
            self.assertFalse(res.p18_lens_writes_permitted)

    def test_13_emount_invalid_params_raise_error(self) -> None:
        with self.assertRaises(p150.RealHwBodyPeripheralCoEmulatorError):
            p150.evaluate_emount_p18_ro_telemetry(aperture_unit="C_STOP")
        with self.assertRaises(p150.RealHwBodyPeripheralCoEmulatorError):
            p150.evaluate_emount_p18_ro_telemetry(focal_length_mm=0.0)
        with self.assertRaises(p150.RealHwBodyPeripheralCoEmulatorError):
            p150.evaluate_emount_p18_ro_telemetry(power_zoom_step=9)

    def test_14_pillar_a_full_evaluation_passes(self) -> None:
        pa = _get_clean_room_audit()["pillar_a_ibis_center_lock_and_emount_ro"]
        self.assertTrue(pa["passed"])
        self.assertEqual(pa["floating_coil_ms"], 0)
        self.assertEqual(pa["p18_mutation_bytes"], 0)
        self.assertFalse(pa["p18_lens_writes_permitted"])


class TestPillarBXlrh1HotplugVmcBncm1AndHdmiVsSdi(unittest.TestCase):
    """Pillar B: XLR-H1 hot-plug 0ms fallback, VMC-BNCM1 LTC & HDMI RAW vs masked SDI."""

    def test_15_xlrh1_attach_and_reattach_4ch_24bit_48khz_lpcm(self) -> None:
        for act in ("ATTACH", "REATTACH"):
            res = p150.simulate_xlrh1_hotplug_transition(camera_state="RECORDING", action=act)
            self.assertTrue(res.valid)
            self.assertEqual(res.active_channels, 4)
            self.assertEqual(res.sample_rate_hz, 48_000)
            self.assertEqual(res.bit_depth, 24)
            self.assertEqual(res.bitrate_bps, 4_608_000)
            self.assertEqual(res.ui_freeze_ms, 0.0)
            self.assertTrue(res.clip_integrity_ok)

    def test_16_xlrh1_hot_unplug_in_standby_and_recording_0ms_fallback(self) -> None:
        res_stby = p150.simulate_xlrh1_hotplug_transition(
            camera_state="STANDBY",
            action="HOT_UNPLUG",
            fallback_sink="TRS_3_5MM_MIC",
        )
        self.assertTrue(res_stby.valid)
        self.assertEqual(res_stby.p11_queue_id_hex, "0x91db059b")
        self.assertEqual(res_stby.p11_return_code_hex, "0x8000")
        self.assertEqual(res_stby.active_sink, "TRS_3_5MM_MIC")
        self.assertEqual(res_stby.hot_unplug_fallback_latency_ms, 0.0)
        self.assertEqual(res_stby.ui_freeze_ms, 0.0)

        res_rec = p150.simulate_xlrh1_hotplug_transition(
            camera_state="RECORDING",
            action="HOT_UNPLUG",
            fallback_sink="INTERNAL_STEREO_MIC",
        )
        self.assertTrue(res_rec.valid)
        self.assertEqual(res_rec.p11_return_code_hex, "0x8000")
        self.assertEqual(res_rec.active_sink, "INTERNAL_STEREO_MIC")
        self.assertEqual(res_rec.active_channels, 2)
        self.assertEqual(res_rec.hot_unplug_fallback_latency_ms, 0.0)
        self.assertEqual(res_rec.ui_freeze_ms, 0.0)
        self.assertTrue(res_rec.clip_integrity_ok)
        self.assertEqual(res_rec.appfw_crashes, 0)

    def test_17_xlrh1_without_p11_shim_exhibits_etmo_minus50_freeze(self) -> None:
        res = p150.simulate_xlrh1_hotplug_transition(
            camera_state="RECORDING",
            action="HOT_UNPLUG",
            p11_shim_enabled=False,
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.status, "BLOCKED_PHANTOM_HANDLE_ETMO_FREEZE")
        self.assertEqual(res.p11_return_code_hex, "E_TMO(-50)")
        self.assertGreater(res.ui_freeze_ms, 0.0)
        self.assertFalse(res.clip_integrity_ok)

    def test_18_xlrh1_invalid_args_raise_error(self) -> None:
        with self.assertRaises(p150.RealHwBodyPeripheralCoEmulatorError):
            p150.simulate_xlrh1_hotplug_transition(camera_state="PLAYBACK")
        with self.assertRaises(p150.RealHwBodyPeripheralCoEmulatorError):
            p150.simulate_xlrh1_hotplug_transition(action="YANK")
        with self.assertRaises(p150.RealHwBodyPeripheralCoEmulatorError):
            p150.simulate_xlrh1_hotplug_transition(fallback_sink="BLUETOOTH_MIC")

    def test_19_vmc_bncm1_ltc_locks_normally_and_blocks_during_h0_uart_boot(self) -> None:
        ok = p150.evaluate_vmc_bncm1_ltc_bridge(uart_boot_active=False, ltc_signal_vpp=2.2)
        self.assertTrue(ok.valid)
        self.assertTrue(ok.ltc_locked)
        self.assertEqual(ok.id_resistor_ohm, 680_000)
        self.assertEqual(ok.ltc_pin, 3)

        blk = p150.evaluate_vmc_bncm1_ltc_bridge(uart_boot_active=True, ltc_signal_vpp=2.2)
        self.assertFalse(blk.valid)
        self.assertFalse(blk.ltc_locked)
        self.assertTrue(blk.pin_conflict_prevented)
        self.assertEqual(blk.status, "BLOCKED_H0_UART_BOOT_PIN_CONFLICT")

    def test_20_vmc_bncm1_out_of_range_signal_rejected(self) -> None:
        low = p150.evaluate_vmc_bncm1_ltc_bridge(uart_boot_active=False, ltc_signal_vpp=0.2)
        self.assertFalse(low.valid)
        self.assertEqual(low.status, "BLOCKED_LTC_SIGNAL_OUT_OF_RANGE")
        with self.assertRaises(p150.RealHwBodyPeripheralCoEmulatorError):
            p150.evaluate_vmc_bncm1_ltc_bridge(ltc_signal_vpp=0.0)

    def test_21_hdmi_raw16_active_and_sdi_bnc_masked_with_zero_blocking_wait(self) -> None:
        res = p150.evaluate_hdmi_raw_vs_masked_sdi_bnc()
        self.assertTrue(res.valid)
        self.assertTrue(res.hdmi_active)
        self.assertEqual(res.sdi_stub_rc_hex, "0x8000")
        self.assertEqual(res.sdi_blocking_wait_ms, 0.0)
        self.assertTrue(res.sdi_blocking_wait_eliminated)

        unmasked = p150.evaluate_hdmi_raw_vs_masked_sdi_bnc(sdi_stub_enabled=False)
        self.assertFalse(unmasked.valid)
        self.assertEqual(unmasked.status, "BLOCKED_SDI_BLOCKING_WAIT")
        self.assertGreater(unmasked.sdi_blocking_wait_ms, 0.0)

    def test_22_pillar_b_full_evaluation_passes(self) -> None:
        pb = _get_clean_room_audit()["pillar_b_xlrh1_hotplug_hdmi_ltc"]
        self.assertTrue(pb["passed"])
        self.assertEqual(pb["sdi_blocking_wait_ms"], 0.0)
        self.assertEqual(pb["hot_unplug_fallback_latency_ms"], 0.0)
        self.assertEqual(pb["appfw_crashes"], 0)


class TestPillarCFx3KeymapReachabilityAndTally(unittest.TestCase):
    """Pillar C: FX3 Custom 1..6, T/W, MODE->Big-6, DISP->Status, 3x Tally & Escape Hatch."""

    def test_23_fx3_keymap_achieves_100pct_fx6_reachability_and_3x_tally(self) -> None:
        res = p150.evaluate_fx3_keymap_ergonomic_reachability(
            recording_active=True,
            tally_lamp_enabled=True,
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.custom_buttons_count, 6)
        self.assertEqual(res.reachability_pct, 100.0)
        self.assertEqual(res.unreachable_targets, ())
        self.assertTrue(res.tally_front_lit)
        self.assertTrue(res.tally_top_lit)
        self.assertTrue(res.tally_rear_lit)
        self.assertEqual(res.escape_hatch_combo, ("MENU", "SHUTTER", "POWER"))
        self.assertTrue(res.escape_hatch_preserved)
        self.assertEqual(res.null_gpio_derefs, 0)

    def test_24_standby_turns_off_tally_and_absent_fx6_keys_contained(self) -> None:
        res = p150.evaluate_fx3_keymap_ergonomic_reachability(
            recording_active=False,
            tally_lamp_enabled=True,
        )
        self.assertTrue(res.valid)
        self.assertFalse(res.tally_front_lit)
        self.assertFalse(res.tally_top_lit)
        self.assertFalse(res.tally_rear_lit)
        for btn in p150.FX6_ABSENT_PHYSICAL_BUTTONS:
            self.assertEqual(res.absent_buttons_route[btn], "CONTAINED_NO_OP_TOAST")

    def test_25_escape_hatch_shadowing_is_strictly_blocked(self) -> None:
        res = p150.evaluate_fx3_keymap_ergonomic_reachability(shadow_escape_hatch=True)
        self.assertFalse(res.valid)
        self.assertFalse(res.escape_hatch_preserved)
        self.assertEqual(res.status, "BLOCKED_ESCAPE_HATCH_SHADOW_FORBIDDEN")

    def test_26_unmapping_required_target_drops_reachability_below_100pct(self) -> None:
        res = p150.evaluate_fx3_keymap_ergonomic_reachability(
            custom_overrides={"MODE_BUTTON": "ZEBRA_TOGGLE"}
        )
        self.assertFalse(res.valid)
        self.assertIn("BIG6_HOME", res.unreachable_targets)
        self.assertLess(res.reachability_pct, 100.0)

    def test_27_unknown_physical_key_raises_error(self) -> None:
        with self.assertRaises(p150.RealHwBodyPeripheralCoEmulatorError):
            p150.evaluate_fx3_keymap_ergonomic_reachability(
                custom_overrides={"ND_DIAL": "AUTO_ND"}
            )

    def test_28_pillar_c_full_evaluation_passes(self) -> None:
        pc = _get_clean_room_audit()["pillar_c_fx3_keymap_reachability_and_tally"]
        self.assertTrue(pc["passed"])
        self.assertEqual(pc["null_gpio_derefs"], 0)


class TestPillarDFanThermalOverrideAndNpFz100UsbPd(unittest.TestCase):
    """Pillar D: Active Cooling Fan Off-in-Rec Override & NP-FZ100 / USB-PD HIL."""

    def test_29_fan_modes_auto1_auto2_minimum_and_off_in_rec_quiet(self) -> None:
        off_q = p150.evaluate_cooling_fan_pwm(fan_mode="OFF_IN_REC", recording_active=True, sensor_temp_c=42.0)
        self.assertTrue(off_q.valid)
        self.assertEqual(off_q.pwm_pct, 0)
        self.assertFalse(off_q.emergency_override_active)

        m_res = p150.evaluate_cooling_fan_pwm(fan_mode="MINIMUM", recording_active=True, sensor_temp_c=42.0)
        self.assertTrue(m_res.valid)
        self.assertEqual(m_res.pwm_pct, 25)

        a1 = p150.evaluate_cooling_fan_pwm(fan_mode="AUTO1", recording_active=True, sensor_temp_c=42.0)
        a2 = p150.evaluate_cooling_fan_pwm(fan_mode="AUTO2", recording_active=True, sensor_temp_c=42.0)
        self.assertTrue(a1.valid)
        self.assertTrue(a2.valid)
        self.assertGreater(a2.pwm_pct, a1.pwm_pct)

    def test_30_fan_off_in_rec_mandatory_high_temp_emergency_override(self) -> None:
        ovr_60 = p150.evaluate_cooling_fan_pwm(
            fan_mode="OFF_IN_REC",
            recording_active=True,
            sensor_temp_c=60.5,
        )
        self.assertTrue(ovr_60.valid)
        self.assertTrue(ovr_60.emergency_override_active)
        self.assertGreaterEqual(ovr_60.pwm_pct, 90)
        self.assertTrue(ovr_60.cmos_thermal_trip_prevented)
        self.assertEqual(ovr_60.thermal_shutdown_events, 0)

        ovr_68 = p150.evaluate_cooling_fan_pwm(
            fan_mode="OFF_IN_REC",
            recording_active=True,
            sensor_temp_c=68.0,
        )
        self.assertTrue(ovr_68.valid)
        self.assertEqual(ovr_68.pwm_pct, 100)

    def test_31_fan_without_override_at_high_temp_causes_thermal_trip(self) -> None:
        fail = p150.evaluate_cooling_fan_pwm(
            fan_mode="OFF_IN_REC",
            recording_active=True,
            sensor_temp_c=62.0,
            allow_emergency_override=False,
        )
        self.assertFalse(fail.valid)
        self.assertEqual(fail.status, "BLOCKED_THERMAL_TRIP_WITHOUT_FAN_OVERRIDE")
        self.assertFalse(fail.cmos_thermal_trip_prevented)
        self.assertEqual(fail.thermal_shutdown_events, 1)

    def test_32_fan_invalid_mode_or_temp_raises_error(self) -> None:
        with self.assertRaises(p150.RealHwBodyPeripheralCoEmulatorError):
            p150.evaluate_cooling_fan_pwm(fan_mode="TURBO")
        with self.assertRaises(p150.RealHwBodyPeripheralCoEmulatorError):
            p150.evaluate_cooling_fan_pwm(sensor_temp_c=200.0)

    def test_33_npfz100_7v2_and_usbpd_9v3a_zero_false_19v5_dcin_alarms(self) -> None:
        nom = p150.evaluate_npfz100_usbpd_power_hil(
            np_fz100_voltage_v=7.2,
            usb_pd_attached=True,
            usb_pd_voltage_v=9.0,
            usb_pd_current_a=3.0,
        )
        self.assertTrue(nom.valid)
        self.assertEqual(nom.usb_pd_power_w, 27.0)
        self.assertTrue(nom.fx6_19v5_dcin_alarm_masked)
        self.assertEqual(nom.false_19v5_dcin_alarms, 0)
        self.assertEqual(nom.emmc_nflasha_write_count, 0)
        self.assertFalse(nom.persistent_emmc_writes_authorized)

    def test_34_unmasked_fx6_19v5_dcin_alarm_detected(self) -> None:
        bad = p150.evaluate_npfz100_usbpd_power_hil(
            np_fz100_voltage_v=7.2,
            usb_pd_attached=False,
            mask_fx6_19v5_dcin_alarm=False,
        )
        self.assertFalse(bad.valid)
        self.assertEqual(bad.status, "BLOCKED_FALSE_FX6_19V5_DCIN_ALARM")
        self.assertEqual(bad.false_19v5_dcin_alarms, 1)

    def test_35_npfz100_low_voltage_cutoff_executes_graceful_encwfistop(self) -> None:
        low = p150.evaluate_npfz100_usbpd_power_hil(
            np_fz100_voltage_v=6.20,
            usb_pd_attached=False,
            recording_active=True,
        )
        self.assertTrue(low.valid)
        self.assertEqual(low.status, "NP_FZ100_LOW_VOLTAGE_GRACEFUL_ENCWFISTOP_CLEAN")
        self.assertTrue(low.enc_wfi_stop_executed)
        self.assertTrue(low.clip_finalized)
        self.assertEqual(low.s_record_counter_after_close, 0)
        self.assertEqual(low.rsv_orphan_count, 0)
        self.assertEqual(low.false_19v5_dcin_alarms, 0)
        self.assertEqual(low.emmc_nflasha_write_count, 0)
        self.assertFalse(low.persistent_emmc_writes_authorized)

    def test_36_unnegotiated_20v_usbpd_decoy_isolated_with_clean_clip_close(self) -> None:
        ovp = p150.evaluate_npfz100_usbpd_power_hil(
            np_fz100_voltage_v=7.2,
            usb_pd_attached=True,
            usb_pd_voltage_v=20.0,
            usb_pd_current_a=3.0,
            recording_active=True,
        )
        self.assertFalse(ovp.valid)
        self.assertEqual(ovp.status, "BLOCKED_USBPD_OVP_CROWBAR_ISOLATED")
        self.assertTrue(ovp.ovp_crowbar_tripped)
        self.assertTrue(ovp.enc_wfi_stop_executed)
        self.assertTrue(ovp.clip_finalized)
        self.assertEqual(ovp.rsv_orphan_count, 0)

    def test_37_power_invalid_args_raise_error(self) -> None:
        with self.assertRaises(p150.RealHwBodyPeripheralCoEmulatorError):
            p150.evaluate_npfz100_usbpd_power_hil(np_fz100_voltage_v=24.0)
        with self.assertRaises(p150.RealHwBodyPeripheralCoEmulatorError):
            p150.evaluate_npfz100_usbpd_power_hil(usb_pd_voltage_v=-5.0)

    def test_38_pillar_d_full_evaluation_passes(self) -> None:
        pd = _get_clean_room_audit()["pillar_d_fan_override_and_npfz100_usbpd"]
        self.assertTrue(pd["passed"])
        self.assertEqual(pd["false_19v5_dcin_alarms"], 0)
        self.assertEqual(pd["rsv_orphan_count"], 0)
        self.assertEqual(pd["emmc_nflasha_write_count"], 0)
        self.assertFalse(pd["persistent_emmc_writes_authorized"])


class TestPhase150SuiteCliBudgetAndHygiene(unittest.TestCase):
    """Stage 26 Suite Integration (26/26), CLI, Runtime Budget (<0.9s/<2.2s), and Hygiene."""

    def test_39_cli_main_summary_and_json_clean_room_in_process(self) -> None:
        buf_sum = io.StringIO()
        with contextlib.redirect_stdout(buf_sum):
            rc_sum = p150.main(["--clean-room", "--self-test", "--summary"])
        self.assertEqual(rc_sum, 0)
        out_sum = buf_sum.getvalue()
        self.assertIn("[PASS] Phase 150 Stage 26 Real-HW Body/Peripheral HIL", out_sum)
        self.assertIn("ibis_float_ms=0", out_sum)
        self.assertIn("p18_mut=0", out_sum)
        self.assertIn("dcin_alarm=0", out_sum)
        self.assertIn("emmc_wr=0", out_sum)

        buf_json = io.StringIO()
        with contextlib.redirect_stdout(buf_json):
            rc_json = p150.main(["--clean-room", "--json"])
        self.assertEqual(rc_json, 0)
        parsed = json.loads(buf_json.getvalue())
        self.assertTrue(parsed["all_checks_passed"])
        self.assertFalse(parsed["redlines"]["persistent_emmc_writes_authorized"])
        self.assertEqual(parsed["redlines"]["emmc_nflasha_write_count"], 0)

    def test_40_suite_in_process_26_stages_and_skip_phase150_config(self) -> None:
        cfg_on = suite.CoEmulationConfig(force_clean_room=True)
        rep_on = suite.run_fx3_vm_coemulation_suite(cfg_on)
        self.assertTrue(rep_on["all_checks_passed"])
        self.assertIn("stage26_realhw_body_peripheral_hil", rep_on)
        s26 = rep_on["stage26_realhw_body_peripheral_hil"]
        self.assertTrue(s26["all_checks_passed"])
        self.assertFalse(s26["persistent_emmc_writes_authorized"])
        self.assertEqual(s26["p18_mutation_bytes"], 0)
        self.assertEqual(s26["floating_coil_ms"], 0)

        stage_keys = [k for k in rep_on if re.match(r"^stage\d+_", k)]
        self.assertGreaterEqual(len(stage_keys), 26)

        cfg_skip = suite.CoEmulationConfig(
            force_clean_room=True,
            include_phase150_realhw_body_peripheral_hil=False,
        )
        rep_skip = suite.run_fx3_vm_coemulation_suite(cfg_skip)
        self.assertTrue(rep_skip["all_checks_passed"])
        self.assertNotIn("stage26_realhw_body_peripheral_hil", rep_skip)
        self.assertEqual(
            len([k for k in rep_skip if re.match(r"^stage\d+_", k)]),
            len(stage_keys) - 1,
        )

    def test_41_suite_subprocess_summary_and_skip_phase150_flag(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        proc = subprocess.run(
            [
                "/usr/bin/python3",
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
        self.assertIn("realhw_body_peripheral_hil=CLEAN_ROOM_SYNTHETIC", proc.stdout)

        proc_skip = subprocess.run(
            [
                "/usr/bin/python3",
                "-B",
                str(FX3_VM_DIR / "fx3_vm_coemulation_suite.py"),
                "--clean-room",
                "--skip-phase150",
                "--summary",
            ],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc_skip.returncode, 0, msg=proc_skip.stderr)
        self.assertNotIn("realhw_body_peripheral_hil=", proc_skip.stdout)

    def test_42_suite_26_stages_clean_room_lt_0p9s_and_local_lt_2p2s_and_json_cli(self) -> None:
        t0 = time.monotonic()
        rep_clean = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig(force_clean_room=True))
        dt_clean = time.monotonic() - t0
        self.assertTrue(rep_clean["all_checks_passed"])
        self.assertGreaterEqual(len([k for k in rep_clean if re.match(r"^stage\d+_", k)]), 26)
        self.assertLess(dt_clean, 0.90)

        t1 = time.monotonic()
        rep_mode = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig())
        dt_mode = time.monotonic() - t1
        self.assertTrue(rep_mode["all_checks_passed"])
        self.assertGreaterEqual(len([k for k in rep_mode if re.match(r"^stage\d+_", k)]), 26)
        self.assertLess(dt_mode, 2.20)

        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        p_clean = subprocess.run(
            [
                "/usr/bin/python3",
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
        self.assertGreaterEqual(len([k for k in d_clean if re.match(r"^stage\d+_", k)]), 26)

    def test_43_all_26_stages_present_and_passing_in_suite_report(self) -> None:
        rep = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig(force_clean_room=True))
        self.assertTrue(rep["stage1_coldboot_and_bt"]["all_checks_passed"])
        self.assertTrue(rep["stage2_dual_isa_cp_shooting"]["all_checks_passed"])
        self.assertTrue(rep["stage3_soft_gpe_hud_ramfb"]["all_checks_passed"])
        for idx in range(4, 27):
            matches = [k for k in rep if k.startswith(f"stage{idx}_")]
            self.assertEqual(len(matches), 1, msg=f"Missing or duplicate stage{idx}_* key")
            self.assertTrue(rep[matches[0]]["all_checks_passed"])

    def test_44_stage26_no_raw_bytes_repr_or_nan_in_json(self) -> None:
        rep = _get_clean_room_audit()
        rendered = json.dumps(rep, allow_nan=False)
        self.assertNotRegex(rendered, r'(?<![0-9A-Za-z_/.-])b[\'"]')
        self.assertIsNone(re.search(r"NaN|Infinity", rendered))

        rep_suite = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig(force_clean_room=True))
        rendered_suite = json.dumps(rep_suite, allow_nan=False)
        self.assertNotRegex(rendered_suite, r'(?<![0-9A-Za-z_/.-])b[\'"]')
        self.assertIsNone(re.search(r"NaN|Infinity", rendered_suite))

    def test_45_source_hygiene_o_rdonly_and_no_write_flags_or_forbidden_port(self) -> None:
        src = (FX3_VM_DIR / "realhw_body_peripheral_ibis_fan_power_coemulator.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("os.O_RDONLY", src)
        self.assertNotIn("os.O_WRONLY", src)
        self.assertNotIn("os.O_RDWR", src)
        self.assertNotIn("87" + "68", src)
        self.assertIn("sys.dont_write_bytecode = True", src)

    def test_46_audit_digest_sha256_deterministic_across_repeated_runs(self) -> None:
        r1 = p150.run_phase150_realhw_body_peripheral_hil(force_clean_room=True)
        r2 = p150.run_phase150_realhw_body_peripheral_hil(force_clean_room=True)
        self.assertEqual(len(r1["audit_digest_sha256"]), 64)
        self.assertEqual(r1["audit_digest_sha256"], r2["audit_digest_sha256"])

        copy = dict(r1)
        recorded = copy.pop("audit_digest_sha256")
        expected = hashlib.sha256(
            json.dumps(copy, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        self.assertEqual(recorded, expected)


if __name__ == "__main__":
    unittest.main()
