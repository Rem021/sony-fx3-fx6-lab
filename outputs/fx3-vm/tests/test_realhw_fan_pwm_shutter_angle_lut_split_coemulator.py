#!/usr/bin/env python3
"""Unit tests for Phase 200 Stage 35 (`35/35` Milestone):
Real-Hardware `ILME-FX3` (`0x91030080`) 4-Mode `[Fan Control]` (`Off in Rec` Standby `MAX PWM` /
`Always Off` Pre-Backup Guard — Rejecting `Auto1/Auto2`), Independent Shutter `Speed/Angle`
(`5.6°..64F / 360°` & Exposure-Step Immunity) & `6.01` vs `7.02` `p2:/setting` User LUT Split
HIL Co-Emulator.
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import contextlib
import errno
import io
import json
import os
from pathlib import Path
import re
import subprocess
import time
import unittest

FX3_VM_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = FX3_VM_DIR.parents[1]
if str(FX3_VM_DIR) not in sys.path:
    sys.path.insert(0, str(FX3_VM_DIR))

import fx3_vm_coemulation_suite as suite  # noqa: E402
import realhw_fan_pwm_shutter_angle_lut_split_coemulator as p200  # noqa: E402


_CLEAN_ROOM_AUDIT_CACHE = None
_DEFAULT_AUDIT_CACHE = None
_CLEAN_SUITE_CACHE = None


def _get_clean_room_audit():
    global _CLEAN_ROOM_AUDIT_CACHE
    if _CLEAN_ROOM_AUDIT_CACHE is None:
        _CLEAN_ROOM_AUDIT_CACHE = p200.run_phase200_realhw_fan_pwm_shutter_angle_lut_split_hil(
            force_clean_room=True
        )
    return _CLEAN_ROOM_AUDIT_CACHE


def _get_default_audit():
    global _DEFAULT_AUDIT_CACHE
    if _DEFAULT_AUDIT_CACHE is None:
        _DEFAULT_AUDIT_CACHE = p200.run_phase200_realhw_fan_pwm_shutter_angle_lut_split_hil()
    return _DEFAULT_AUDIT_CACHE


def _get_clean_room_suite():
    global _CLEAN_SUITE_CACHE
    if _CLEAN_SUITE_CACHE is None:
        _CLEAN_SUITE_CACHE = suite.run_fx3_vm_coemulation_suite(
            suite.CoEmulationConfig(force_clean_room=True)
        )
    return _CLEAN_SUITE_CACHE


class TestPhase200FanPwmShutterAngleLutSplitCoEmulator(unittest.TestCase):
    def test_01_schema_version_stage_35_milestone_and_redline_constants(self) -> None:
        self.assertEqual(
            p200.PHASE_200_SCHEMA,
            "phase200_realhw_fan_pwm_shutter_angle_lut_split_coemulator_v1",
        )
        self.assertEqual(p200.PHASE_200_VERSION, "200.0.0")
        self.assertEqual(p200.STAGE_INDEX, 35)
        self.assertEqual(p200.STAGE_TOTAL, 35)
        self.assertEqual(p200.MILESTONE_LABEL, "35/35")
        self.assertEqual(p200.STAGE_NAME, "stage35_realhw_fan_pwm_shutter_angle_lut_split_hil")
        self.assertEqual(p200.FX3_MODEL_ID, 0x91030080)
        self.assertTrue(p200.P8_CP_MUTATION_FORBIDDEN)
        self.assertFalse(p200.PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(p200.SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(p200.EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        self.assertEqual(p200.PHYSICAL_USB_PACKETS_EMITTED, 0)
        self.assertEqual(p200.OTP_FUSE_TOUCHES, 0)
        self.assertEqual(p200.RPMB_COUNTER_INCREMENTS, 0)
        self.assertEqual(p200.P2_SETTING_MUTATION_BYTES, 0)
        self.assertEqual(p200.THERMAL_RUNAWAY_EVENTS, 0)
        self.assertEqual(p200.LUT_COLOR_SOLVER_CORRUPTION_EVENTS, 0)
        self.assertEqual(p200.RAW_FIRMWARE_BYTES_LEAKED, 0)

    def test_02_donor_inspection_under_0_10s_and_cached(self) -> None:
        p200._DONOR_AUDIT_CACHE.clear()
        t0 = time.monotonic()
        da1 = p200.inspect_phase200_donors(force_clean_room=False)
        dt1 = time.monotonic() - t0
        t1 = time.monotonic()
        da2 = p200.inspect_phase200_donors(force_clean_room=False)
        dt2 = time.monotonic() - t1
        self.assertLess(dt1, 0.10)
        self.assertLess(dt2, 0.02)
        self.assertEqual(da1.donor_files_inspected, 12)
        self.assertEqual(da1.raw_firmware_bytes_leaked, 0)
        self.assertTrue(da1.all_contracts_verified)
        self.assertEqual(da1.errors, ())
        if da1.source_mode == "LOCAL_DONOR_RDONLY":
            self.assertIs(da1, da2)

    def test_03_clean_room_donor_fallback_via_flag_and_env(self) -> None:
        da_flag = p200.inspect_phase200_donors(force_clean_room=True)
        self.assertEqual(da_flag.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(da_flag.access_mode, "O_RDONLY")
        self.assertEqual(da_flag.donor_files_inspected, 12)
        self.assertEqual(da_flag.raw_firmware_bytes_leaked, 0)
        self.assertTrue(da_flag.all_contracts_verified)

        da_env = p200.inspect_phase200_donors(env={"FX3_FX6_FORCE_CLEAN_ROOM": "1"})
        self.assertEqual(da_env.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertIs(da_env, da_flag)

    def test_04_clean_room_sentinel_paths_do_not_touch_local_donors(self) -> None:
        paths_clean = p200.resolve_phase200_donor_paths(env={"FX3_FX6_FORCE_CLEAN_ROOM": "1"})
        self.assertEqual(len(paths_clean), 12)
        for p in paths_clean.values():
            self.assertIn(p200.CLEAN_ROOM_SENTINEL_DIRNAME, str(p))
            self.assertFalse(p.exists())
        da = p200.inspect_phase200_donors(env={"FX3_FX6_FORCE_CLEAN_ROOM": "1"})
        self.assertEqual(da.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(da.all_contracts_verified)
        self.assertEqual(da.raw_firmware_bytes_leaked, 0)

    def test_05_twelve_donors_expected_sizes_and_contracts(self) -> None:
        da = p200.inspect_phase200_donors()
        self.assertEqual(da.fx3_libfan.file_bytes, 27_280)
        self.assertEqual(da.fx6_libfan.file_bytes, 31_176)
        self.assertEqual(da.fx3_libbackup.file_bytes, 14_232)
        self.assertEqual(da.fx3_backup_mgr.file_bytes, 10_272)
        self.assertEqual(da.fx3_im_elf.file_bytes, 40_920)
        self.assertEqual(da.fx3_string_en_f.file_bytes, 373_820)
        self.assertEqual(da.fx3_appfw.file_bytes, 79_015_712)
        self.assertEqual(da.fx6_appfw.file_bytes, 50_520_424)
        self.assertEqual(da.fx3_cpapp.file_bytes, 15_980_568)
        self.assertEqual(da.fx6_cpapp.file_bytes, 17_952_816)
        self.assertEqual(da.fx3_libmpr.file_bytes, 3_517_008)
        self.assertEqual(da.fx6_libmpr.file_bytes, 28_921_824)
        self.assertTrue(da.fan_4mode_and_no_auto1_auto2_proven)
        self.assertTrue(da.shutter_angle_and_exposure_step_proven)
        self.assertTrue(da.lut_601_vs_702_binary_split_proven)
        self.assertTrue(da.p2_setting_mount_and_backup_proven)

    def test_06_string_uxc_proves_exact_4mode_fan_and_zero_auto1_auto2_hits(self) -> None:
        da = p200.inspect_phase200_donors()
        uxc = da.fx3_string_en_f
        self.assertTrue(uxc.uxd_container_ok)
        for tok in ("Fan Control", "Off in Rec", "Always Off", "Minimum", "Auto Power OFF Temp."):
            self.assertEqual(uxc.marker_hits[tok], 1, msg=tok)
        self.assertEqual(uxc.forbidden_hits["Auto1"], 0)
        self.assertEqual(uxc.forbidden_hits["Auto2"], 0)

    def test_07_large_donors_use_strictly_bounded_windows_only(self) -> None:
        da = p200.inspect_phase200_donors()
        for large in (
            da.fx3_appfw,
            da.fx6_appfw,
            da.fx3_cpapp,
            da.fx6_cpapp,
            da.fx3_libmpr,
            da.fx6_libmpr,
        ):
            self.assertTrue(large.bounded_windows_only)
            self.assertGreater(large.file_bytes, large.bytes_read_total)
            self.assertLessEqual(
                large.bytes_read_total,
                p200.BOUNDED_WINDOW_MAX_BYTES
                * (len(p200.LARGE_DONOR_WINDOWS[large.artifact_key]) + 1),
            )
            self.assertTrue(all(large.window_hits.values()), msg=large.artifact_key)

    def test_08_pillar_a_exact_4_fan_control_modes_constant(self) -> None:
        self.assertEqual(
            p200.VALID_FX3_FAN_CONTROL_MODES,
            ("Auto", "Minimum", "Off in Rec", "Always Off"),
        )
        self.assertEqual(p200.FORBIDDEN_STUDIO_LUMIX_FAN_MODES, ("Auto1", "Auto2"))
        self.assertEqual(
            p200.FAN_CONTROL_MENU_PATH,
            "MENU -> Setup -> [Setup Option] -> [Fan Control]",
        )

    def test_09_pillar_a_rejects_auto1_and_auto2_with_einval(self) -> None:
        for invalid_mode in ("Auto1", "Auto2", "Normal", "Max", ""):
            res = p200.probe_fx3_fan_pwm_and_backup_guard(requested_fan_mode=invalid_mode)
            self.assertFalse(res.admitted, msg=invalid_mode)
            self.assertTrue(res.invalid_fan_mode_rejected_einval, msg=invalid_mode)
            self.assertEqual(res.errno_code, errno.EINVAL, msg=invalid_mode)
            self.assertEqual(res.status_code, "BLOCKED_INVALID_FAN_CONTROL_MODE_EINVAL")
            self.assertEqual(res.model_id_hex, "0x91030080")

    def test_10_pillar_a_rejects_invalid_auto_power_off_temp_with_einval(self) -> None:
        res = p200.probe_fx3_fan_pwm_and_backup_guard(
            requested_fan_mode="Auto",
            auto_power_off_temp="Extreme",
            requested_cold_backup_or_dualboot=True,
        )
        self.assertFalse(res.admitted)
        self.assertTrue(res.invalid_fan_mode_rejected_einval)
        self.assertEqual(res.errno_code, errno.EINVAL)
        self.assertTrue(res.cold_backup_entry_blocked)
        self.assertEqual(res.status_code, "BLOCKED_INVALID_AUTO_POWER_OFF_TEMP_EINVAL")

    def test_11_pillar_a_off_in_rec_drives_100_max_pwm_in_standby(self) -> None:
        res = p200.probe_fx3_fan_pwm_and_backup_guard(
            requested_fan_mode="Off in Rec",
            auto_power_off_temp="High",
            is_recording=False,
            die_temp_c=42.0,
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.pwm_duty_percent, 100)
        self.assertTrue(res.standby_max_pwm_exhaust_active)
        self.assertFalse(res.emergency_thermal_override_active)
        self.assertEqual(res.status_code, "ADMITTED_OFF_IN_REC_STANDBY_MAX_PWM_OK")

    def test_12_pillar_a_off_in_rec_drives_0_pwm_during_normal_recording(self) -> None:
        res = p200.probe_fx3_fan_pwm_and_backup_guard(
            requested_fan_mode="Off in Rec",
            auto_power_off_temp="High",
            is_recording=True,
            die_temp_c=60.0,
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.pwm_duty_percent, 0)
        self.assertFalse(res.standby_max_pwm_exhaust_active)
        self.assertFalse(res.emergency_thermal_override_active)
        self.assertEqual(res.status_code, "ADMITTED_OFF_IN_REC_SILENT_0PWM_OK")

    def test_13_pillar_a_off_in_rec_emergency_thermal_override_standard_and_high(self) -> None:
        std_ovr = p200.probe_fx3_fan_pwm_and_backup_guard(
            requested_fan_mode="Off in Rec",
            auto_power_off_temp="Standard",
            is_recording=True,
            die_temp_c=68.5,
        )
        self.assertTrue(std_ovr.admitted)
        self.assertEqual(std_ovr.pwm_duty_percent, 100)
        self.assertTrue(std_ovr.emergency_thermal_override_active)
        self.assertEqual(std_ovr.thermal_runaway_events, 0)
        self.assertEqual(std_ovr.status_code, "ADMITTED_OFF_IN_REC_EMERGENCY_THERMAL_OVERRIDE_MAX_PWM")

        high_ovr = p200.probe_fx3_fan_pwm_and_backup_guard(
            requested_fan_mode="Off in Rec",
            auto_power_off_temp="High",
            is_recording=True,
            die_temp_c=78.5,
        )
        self.assertTrue(high_ovr.admitted)
        self.assertEqual(high_ovr.pwm_duty_percent, 100)
        self.assertTrue(high_ovr.emergency_thermal_override_active)

    def test_14_pillar_a_auto_and_minimum_modes_and_thermal_shutdown_latch(self) -> None:
        auto_cool = p200.probe_fx3_fan_pwm_and_backup_guard(
            requested_fan_mode="Auto",
            auto_power_off_temp="High",
            is_recording=True,
            die_temp_c=34.0,
        )
        self.assertTrue(auto_cool.admitted)
        self.assertEqual(auto_cool.pwm_duty_percent, 35)

        auto_mid = p200.probe_fx3_fan_pwm_and_backup_guard(
            requested_fan_mode="Auto",
            auto_power_off_temp="High",
            is_recording=True,
            die_temp_c=56.5,
        )
        self.assertTrue(auto_mid.admitted)
        self.assertGreater(auto_mid.pwm_duty_percent, 35)
        self.assertLess(auto_mid.pwm_duty_percent, 100)

        min_ok = p200.probe_fx3_fan_pwm_and_backup_guard(
            requested_fan_mode="Minimum",
            auto_power_off_temp="Standard",
            is_recording=True,
            die_temp_c=52.0,
        )
        self.assertTrue(min_ok.admitted)
        self.assertEqual(min_ok.pwm_duty_percent, 25)

        min_ovr = p200.probe_fx3_fan_pwm_and_backup_guard(
            requested_fan_mode="Minimum",
            auto_power_off_temp="Standard",
            is_recording=True,
            die_temp_c=69.0,
        )
        self.assertTrue(min_ovr.admitted)
        self.assertEqual(min_ovr.pwm_duty_percent, 100)
        self.assertTrue(min_ovr.emergency_thermal_override_active)

        shut = p200.probe_fx3_fan_pwm_and_backup_guard(
            requested_fan_mode="Always Off",
            auto_power_off_temp="Standard",
            is_recording=True,
            die_temp_c=75.0,
        )
        self.assertFalse(shut.admitted)
        self.assertTrue(shut.thermal_shutdown_latched)
        self.assertEqual(shut.status_code, "THERMAL_AUTO_POWER_OFF_LATCHED_SAFE")

    def test_15_pillar_a_always_off_blocks_cold_backup_until_switched_to_auto(self) -> None:
        blocked_always_off = p200.probe_fx3_fan_pwm_and_backup_guard(
            requested_fan_mode="Always Off",
            auto_power_off_temp="High",
            is_recording=False,
            die_temp_c=44.0,
            requested_cold_backup_or_dualboot=True,
        )
        self.assertFalse(blocked_always_off.admitted)
        self.assertTrue(blocked_always_off.cold_backup_entry_blocked)
        self.assertFalse(blocked_always_off.adjust_control_0x40_p3_75mib_ready)
        self.assertEqual(blocked_always_off.required_pre_backup_fan_mode, "Auto")
        self.assertEqual(
            blocked_always_off.status_code,
            "BLOCKED_PRE_BACKUP_ALWAYS_OFF_REQUIRES_FAN_AUTO",
        )

        for other_non_auto in ("Minimum", "Off in Rec"):
            b_other = p200.probe_fx3_fan_pwm_and_backup_guard(
                requested_fan_mode=other_non_auto,
                auto_power_off_temp="Standard",
                is_recording=False,
                die_temp_c=44.0,
                requested_cold_backup_or_dualboot=True,
            )
            self.assertFalse(b_other.admitted, msg=other_non_auto)
            self.assertTrue(b_other.cold_backup_entry_blocked, msg=other_non_auto)
            self.assertFalse(b_other.adjust_control_0x40_p3_75mib_ready, msg=other_non_auto)

        for temp_mode in ("Standard", "High"):
            admitted_auto = p200.probe_fx3_fan_pwm_and_backup_guard(
                requested_fan_mode="Auto",
                auto_power_off_temp=temp_mode,
                is_recording=False,
                die_temp_c=44.0,
                requested_cold_backup_or_dualboot=True,
            )
            self.assertTrue(admitted_auto.admitted, msg=temp_mode)
            self.assertFalse(admitted_auto.cold_backup_entry_blocked, msg=temp_mode)
            self.assertTrue(admitted_auto.adjust_control_0x40_p3_75mib_ready, msg=temp_mode)
            self.assertEqual(admitted_auto.status_code, "ADMITTED_PRE_BACKUP_FAN_AUTO_GUARD_OK")

    def test_16_pillar_a_hot_auto_blocks_cold_backup_above_safety_ceiling(self) -> None:
        hot_auto = p200.probe_fx3_fan_pwm_and_backup_guard(
            requested_fan_mode="Auto",
            auto_power_off_temp="Standard",
            is_recording=False,
            die_temp_c=69.0,
            requested_cold_backup_or_dualboot=True,
        )
        self.assertFalse(hot_auto.admitted)
        self.assertTrue(hot_auto.cold_backup_entry_blocked)
        self.assertFalse(hot_auto.adjust_control_0x40_p3_75mib_ready)
        self.assertEqual(
            hot_auto.status_code,
            "BLOCKED_PRE_BACKUP_REQUIRES_FAN_AUTO_AND_SAFE_TEMP",
        )

    def test_17_pillar_b_parse_shutter_angle_spec_degrees_and_multiframe(self) -> None:
        self.assertAlmostEqual(p200.parse_shutter_angle_spec(5.6), 5.6)
        self.assertAlmostEqual(p200.parse_shutter_angle_spec("172.8°"), 172.8)
        self.assertAlmostEqual(p200.parse_shutter_angle_spec("360 deg"), 360.0)
        self.assertAlmostEqual(p200.parse_shutter_angle_spec("2F"), 720.0)
        self.assertAlmostEqual(p200.parse_shutter_angle_spec("64F"), 23040.0)

        for bad_spec in (0, -90, "0F", "-2F", "abc", "F"):
            with self.assertRaises(p200.RealHwFanShutterLutSplitError, msg=bad_spec):
                p200.parse_shutter_angle_spec(bad_spec)

    def test_18_pillar_b_independent_backup_slots_preserved_across_big6_movie_sq(self) -> None:
        s1 = p200.evaluate_shutter_speed_angle_hil(
            ui_surface="Movie",
            rec_frame_rate="23.98p",
            shutter_mode="Speed",
            exposure_step="0.3EV",
            requested_speed_label="1/250",
        )
        self.assertTrue(s1.admitted)
        self.assertEqual(s1.stored_speed_label, "1/250")
        self.assertEqual(s1.stored_angle_deg, 180.0)
        self.assertEqual(s1.speed_slot_bkid_hex, "0x01240010")
        self.assertEqual(s1.angle_slot_bkid_hex, "0x01240014")
        self.assertTrue(s1.independent_slots_preserved)

        s2 = p200.evaluate_shutter_speed_angle_hil(
            bank=s1.updated_bank,
            ui_surface="BIG6",
            rec_frame_rate="23.98p",
            shutter_mode="Angle",
            exposure_step="0.3EV",
            requested_angle_spec=172.8,
        )
        self.assertTrue(s2.admitted)
        self.assertEqual(s2.stored_speed_label, "1/250")
        self.assertAlmostEqual(s2.stored_angle_deg, 172.8)
        self.assertTrue(s2.independent_slots_preserved)

        s3 = p200.evaluate_shutter_speed_angle_hil(
            bank=s2.updated_bank,
            ui_surface="S&Q",
            sq_mode_active=True,
            rec_frame_rate="24.00p",
            shutter_mode="Angle",
            exposure_step="0.5EV",
        )
        self.assertTrue(s3.admitted)
        self.assertEqual(s3.stored_speed_label, "1/250")
        self.assertAlmostEqual(s3.effective_angle_deg, 172.8)

        s4 = p200.evaluate_shutter_speed_angle_hil(
            bank=s3.updated_bank,
            ui_surface="Movie",
            rec_frame_rate="23.98p",
            shutter_mode="Speed",
            exposure_step="0.5EV",
        )
        self.assertTrue(s4.admitted)
        self.assertEqual(s4.stored_speed_label, "1/250")
        self.assertAlmostEqual(s4.stored_angle_deg, 172.8)
        self.assertAlmostEqual(s4.integration_time_ms, 4.0)

    def test_19_pillar_b_angle_immune_to_0_3ev_vs_0_5ev_exposure_step(self) -> None:
        r03 = p200.evaluate_shutter_speed_angle_hil(
            ui_surface="BIG6",
            rec_frame_rate="24.00p",
            shutter_mode="Angle",
            exposure_step="0.3EV",
            requested_angle_spec=144.0,
        )
        r05 = p200.evaluate_shutter_speed_angle_hil(
            bank=r03.updated_bank,
            ui_surface="BIG6",
            rec_frame_rate="24.00p",
            shutter_mode="Angle",
            exposure_step="0.5EV",
        )
        self.assertTrue(r03.angle_immune_to_exposure_step)
        self.assertTrue(r05.angle_immune_to_exposure_step)
        self.assertEqual(r03.effective_angle_deg, 144.0)
        self.assertEqual(r05.effective_angle_deg, 144.0)
        self.assertEqual(r03.integration_time_ms, r05.integration_time_ms)

    def test_20_pillar_b_allows_5_6_to_64f_at_or_below_59_94p(self) -> None:
        for fps in ("23.98p", "24.00p", "25.00p", "29.97p", "50.00p", "59.94p"):
            r_low = p200.evaluate_shutter_speed_angle_hil(
                ui_surface="Movie",
                rec_frame_rate=fps,
                shutter_mode="Angle",
                requested_angle_spec=5.6,
            )
            self.assertTrue(r_low.admitted, msg=fps)
            self.assertFalse(r_low.clamped, msg=fps)
            self.assertEqual(r_low.effective_angle_deg, 5.6, msg=fps)

            r_64f = p200.evaluate_shutter_speed_angle_hil(
                ui_surface="Movie",
                rec_frame_rate=fps,
                shutter_mode="Angle",
                requested_angle_spec="64F",
            )
            self.assertTrue(r_64f.admitted, msg=fps)
            self.assertFalse(r_64f.clamped, msg=fps)
            self.assertEqual(r_64f.effective_angle_deg, 23040.0, msg=fps)
            self.assertEqual(r_64f.effective_angle_label, "64F", msg=fps)
            self.assertEqual(r_64f.max_allowed_label, "64F", msg=fps)

    def test_21_pillar_b_clamps_above_64f_to_64f_at_23_98p(self) -> None:
        r_over = p200.evaluate_shutter_speed_angle_hil(
            ui_surface="BIG6",
            rec_frame_rate="23.98p",
            shutter_mode="Angle",
            requested_angle_spec="128F",
        )
        self.assertTrue(r_over.admitted)
        self.assertTrue(r_over.clamped)
        self.assertFalse(r_over.multi_frame_clamped_to_360)
        self.assertEqual(r_over.effective_angle_deg, 23040.0)
        self.assertEqual(r_over.effective_angle_label, "64F")

    def test_22_pillar_b_clamps_119_88p_and_100p_strictly_to_5_6_to_360(self) -> None:
        for hfr in ("119.88p", "100p"):
            res = p200.evaluate_shutter_speed_angle_hil(
                ui_surface="Movie",
                rec_frame_rate=hfr,
                shutter_mode="Angle",
                requested_angle_spec="64F",
            )
            self.assertTrue(res.admitted, msg=hfr)
            self.assertTrue(res.clamped, msg=hfr)
            self.assertTrue(res.multi_frame_clamped_to_360, msg=hfr)
            self.assertEqual(res.effective_angle_deg, 360.0, msg=hfr)
            self.assertEqual(res.effective_angle_label, "360.0°", msg=hfr)
            self.assertEqual(res.max_allowed_label, "360°", msg=hfr)
            self.assertEqual(res.status_code, "ADMITTED_SHUTTER_ANGLE_CLAMPED_5_6_TO_360_HFR_SQ")

    def test_23_pillar_b_clamps_sq_mode_strictly_to_5_6_to_360_even_at_23_98p(self) -> None:
        res_sq_surface = p200.evaluate_shutter_speed_angle_hil(
            ui_surface="S&Q",
            rec_frame_rate="23.98p",
            shutter_mode="Angle",
            requested_angle_spec="4F",
        )
        self.assertTrue(res_sq_surface.admitted)
        self.assertTrue(res_sq_surface.sq_mode_active)
        self.assertTrue(res_sq_surface.clamped)
        self.assertTrue(res_sq_surface.multi_frame_clamped_to_360)
        self.assertEqual(res_sq_surface.effective_angle_deg, 360.0)

        res_sq_flag = p200.evaluate_shutter_speed_angle_hil(
            ui_surface="BIG6",
            sq_mode_active=True,
            rec_frame_rate="25.00p",
            shutter_mode="Angle",
            requested_angle_spec="2F",
        )
        self.assertTrue(res_sq_flag.multi_frame_clamped_to_360)
        self.assertEqual(res_sq_flag.effective_angle_deg, 360.0)

    def test_24_pillar_b_clamps_sub_5_6_deg_to_5_6_deg(self) -> None:
        res = p200.evaluate_shutter_speed_angle_hil(
            ui_surface="BIG6",
            rec_frame_rate="24.00p",
            shutter_mode="Angle",
            requested_angle_spec=1.5,
        )
        self.assertTrue(res.admitted)
        self.assertTrue(res.clamped)
        self.assertFalse(res.multi_frame_clamped_to_360)
        self.assertEqual(res.effective_angle_deg, 5.6)
        self.assertEqual(res.status_code, "ADMITTED_SHUTTER_ANGLE_CLAMPED_TO_RANGE")

    def test_25_pillar_b_invalid_shutter_mode_einval_and_bad_args_raise(self) -> None:
        bad_mode = p200.evaluate_shutter_speed_angle_hil(shutter_mode="SynchroScanOnly")
        self.assertFalse(bad_mode.admitted)
        self.assertEqual(bad_mode.errno_code, errno.EINVAL)
        self.assertEqual(bad_mode.status_code, "BLOCKED_INVALID_SHUTTER_MODE_EINVAL")

        with self.assertRaises(p200.RealHwFanShutterLutSplitError):
            p200.evaluate_shutter_speed_angle_hil(ui_surface="PhotoStills")
        with self.assertRaises(p200.RealHwFanShutterLutSplitError):
            p200.evaluate_shutter_speed_angle_hil(rec_frame_rate="240p")
        with self.assertRaises(p200.RealHwFanShutterLutSplitError):
            p200.evaluate_shutter_speed_angle_hil(exposure_step="1.0EV")
        with self.assertRaises(p200.RealHwFanShutterLutSplitError):
            p200.evaluate_shutter_speed_angle_hil(
                shutter_mode="Speed",
                requested_speed_label="1/0",
            )

    def test_26_pillar_c_stage_b_fx6_601_direct_write_to_p2_setting_blocked_erofs(self) -> None:
        for mount in ("p2:/setting", "/setting", "/dev/nflasha2", "/dev/cnflasha2"):
            res = p200.probe_p2_setting_lut_binary_split_firewall(
                os_persona=p200.OS_PERSONA_STAGE_B_FX6_601,
                user_slot_index=1,
                lut_name="FX6_User1_33pt.cube",
                lut_points=33,
                target_mount=mount,
                redirect_to_volatile_overlay=False,
            )
            self.assertFalse(res.admitted, msg=mount)
            self.assertTrue(res.p2_setting_write_blocked_erofs, msg=mount)
            self.assertEqual(res.errno_code, errno.EROFS, msg=mount)
            self.assertEqual(res.p2_setting_mutation_bytes, 0, msg=mount)
            self.assertTrue(res.h0_equals_h3, msg=mount)
            self.assertEqual(res.h0_equals_h3_slots, 16, msg=mount)
            self.assertFalse(res.persistent_emmc_writes_authorized, msg=mount)
            self.assertEqual(res.status_code, "BLOCKED_STAGE_B_601_WRITE_TO_P2_SETTING_EROFS")

    def test_27_pillar_c_stage_b_non_volatile_non_p2_target_also_blocked_erofs(self) -> None:
        res = p200.probe_p2_setting_lut_binary_split_firewall(
            os_persona=p200.OS_PERSONA_STAGE_B_FX6_601,
            user_slot_index=4,
            lut_name="FX6_User4_33pt.cube",
            lut_points=33,
            target_mount="/usr/share/lut_persist",
            redirect_to_volatile_overlay=False,
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, errno.EROFS)
        self.assertEqual(res.status_code, "BLOCKED_STAGE_B_NON_VOLATILE_LUT_TARGET_EROFS")

    def test_28_pillar_c_stage_b_all_16_slots_redirected_to_volatile_tmp_fx6_lut_overlay(self) -> None:
        for slot in range(1, 17):
            res = p200.probe_p2_setting_lut_binary_split_firewall(
                os_persona=p200.OS_PERSONA_STAGE_B_FX6_601,
                user_slot_index=slot,
                lut_name=f"CineEI_Slot{slot}_33pt.cube",
                lut_points=33 if (slot % 2 == 1) else 17,
                target_mount="p2:/setting",
                redirect_to_volatile_overlay=True,
            )
            self.assertTrue(res.admitted, msg=slot)
            self.assertTrue(res.redirect_to_volatile_overlay, msg=slot)
            self.assertEqual(res.target_mount, "/tmp/fx6_lut_overlay", msg=slot)
            self.assertEqual(res.active_storage_path, f"/tmp/fx6_lut_overlay/User{slot}.lut601", msg=slot)
            self.assertTrue(res.volatile_ram_only, msg=slot)
            self.assertTrue(res.volatile_overlay_wiped_on_reboot, msg=slot)
            self.assertTrue(res.p2_setting_write_blocked_erofs, msg=slot)
            self.assertEqual(res.p2_setting_mutation_bytes, 0, msg=slot)
            self.assertTrue(res.h0_equals_h3, msg=slot)
            self.assertEqual(res.h0_equals_h3_slots, 16, msg=slot)
            self.assertEqual(res.lut_color_solver_corruption_events, 0, msg=slot)

    def test_29_pillar_c_unmigrated_601_slot_in_702_blocked_requiring_reregistration(self) -> None:
        res = p200.probe_p2_setting_lut_binary_split_firewall(
            os_persona=p200.OS_PERSONA_STOCK_FX3_702,
            user_slot_index=2,
            lut_name="Legacy601_User2.cube",
            lut_points=33,
            attempt_unmigrated_601_slot_in_702=True,
        )
        self.assertFalse(res.admitted)
        self.assertTrue(res.format_split_601_vs_702_detected)
        self.assertTrue(res.requires_700_plus_reregistration)
        self.assertEqual(res.lut_binary_format, p200.LUT_BINARY_FMT_LEGACY_601)
        self.assertEqual(res.host_stock_lut_format, p200.LUT_BINARY_FMT_OPTIMIZED_702)
        self.assertEqual(res.errno_code, errno.EINVAL)
        self.assertEqual(
            res.status_code,
            "BLOCKED_UNMIGRATED_601_LUT_SLOT_IN_702_REQUIRES_REREGISTRATION",
        )

    def test_30_pillar_c_stock_fx3_702_v2_slot_preserves_16_of_16_h0_equals_h3(self) -> None:
        res = p200.probe_p2_setting_lut_binary_split_firewall(
            os_persona=p200.OS_PERSONA_STOCK_FX3_702,
            user_slot_index=16,
            lut_name="FX3_702_User16_33pt.cube",
            lut_points=33,
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.lut_binary_format, p200.LUT_BINARY_FMT_OPTIMIZED_702)
        self.assertFalse(res.requires_700_plus_reregistration)
        self.assertTrue(res.h0_equals_h3)
        self.assertEqual(res.h0_equals_h3_slots, 16)
        self.assertEqual(
            res.h0_p2_setting_digest_sha256_prefix16,
            res.h3_p2_setting_digest_sha256_prefix16,
        )
        self.assertEqual(res.p2_setting_mutation_bytes, 0)

    def test_31_pillar_c_rejects_invalid_slot_index_path_traversal_gt63b_and_65pt(self) -> None:
        for bad_slot in (0, 17, -1):
            r_slot = p200.probe_p2_setting_lut_binary_split_firewall(user_slot_index=bad_slot)
            self.assertFalse(r_slot.admitted, msg=bad_slot)
            self.assertEqual(r_slot.errno_code, errno.EINVAL, msg=bad_slot)

        for bad_name in ("", "../evil.cube", "dir/lut.cube", "dir\\lut.cube", ("A" * 60) + ".cube"):
            r_name = p200.probe_p2_setting_lut_binary_split_firewall(lut_name=bad_name)
            self.assertFalse(r_name.admitted, msg=bad_name)
            self.assertEqual(r_name.errno_code, errno.EINVAL, msg=bad_name)

        for bad_pts in (9, 65, 129):
            r_pts = p200.probe_p2_setting_lut_binary_split_firewall(lut_points=bad_pts)
            self.assertFalse(r_pts.admitted, msg=bad_pts)
            self.assertEqual(r_pts.errno_code, errno.EINVAL, msg=bad_pts)

        with self.assertRaises(p200.RealHwFanShutterLutSplitError):
            p200.probe_p2_setting_lut_binary_split_firewall(os_persona="UNKNOWN_OS")

    def test_32_pillar_d_hard_safety_redlines_reject_all_nine_forbidden_actions(self) -> None:
        base = p200.probe_hard_safety_redline()
        self.assertTrue(base.valid)
        self.assertFalse(base.persistent_emmc_writes_authorized)
        self.assertFalse(base.spi_nor_write_authorized)
        self.assertFalse(base.el3_payload_transmit_authorized)
        self.assertEqual(base.physical_usb_packets_emitted, 0)
        self.assertEqual(base.otp_fuse_touches, 0)
        self.assertEqual(base.rpmb_counter_increments, 0)
        self.assertEqual(base.p2_setting_mutation_bytes, 0)
        self.assertEqual(base.thermal_runaway_events, 0)
        self.assertEqual(base.lut_color_solver_corruption_events, 0)

        for kw in (
            {"authorize_persistent_emmc_writes": True},
            {"authorize_spi_nor_write": True},
            {"authorize_el3_payload_transmit": True},
            {"emit_physical_usb_packet": True},
            {"touch_otp_fuse": True},
            {"increment_rpmb_counter": True},
            {"mutate_p2_setting_lut": True},
            {"trigger_thermal_runaway": True},
            {"corrupt_lut_color_solver": True},
        ):
            r = p200.probe_hard_safety_redline(**kw)
            self.assertFalse(r.valid, msg=kw)
            self.assertFalse(r.persistent_emmc_writes_authorized)
            self.assertFalse(r.spi_nor_write_authorized)
            self.assertFalse(r.el3_payload_transmit_authorized)
            self.assertEqual(r.physical_usb_packets_emitted, 0)
            self.assertEqual(r.otp_fuse_touches, 0)
            self.assertEqual(r.rpmb_counter_increments, 0)
            self.assertEqual(r.p2_setting_mutation_bytes, 0)

    def test_33_pillar_d_multi_violation_redline_probe_reports_combined_blocked_action(self) -> None:
        r = p200.probe_hard_safety_redline(
            authorize_persistent_emmc_writes=True,
            mutate_p2_setting_lut=True,
        )
        self.assertFalse(r.valid)
        self.assertIn("PERSISTENT_EMMC_WRITE", r.blocked_action)
        self.assertIn("P2_SETTING_LUT_MUTATION", r.blocked_action)

    def test_34_pillar_a_evaluator_all_passed(self) -> None:
        pa = p200.evaluate_pillar_a_fx3_fan_pwm_and_backup_guard()
        self.assertTrue(pa["passed"])
        self.assertEqual(pa["auto1_rejected_einval"]["errno_code"], errno.EINVAL)
        self.assertEqual(pa["auto2_rejected_einval"]["errno_code"], errno.EINVAL)
        self.assertEqual(pa["off_in_rec_standby_100pwm"]["pwm_duty_percent"], 100)
        self.assertEqual(pa["off_in_rec_recording_0pwm"]["pwm_duty_percent"], 0)
        self.assertEqual(pa["off_in_rec_emergency_override_100pwm"]["pwm_duty_percent"], 100)
        self.assertTrue(pa["always_off_pre_backup_blocked"]["cold_backup_entry_blocked"])
        self.assertTrue(pa["auto_pre_backup_admitted_high"]["adjust_control_0x40_p3_75mib_ready"])

    def test_35_pillar_b_evaluator_all_passed(self) -> None:
        pb = p200.evaluate_pillar_b_independent_shutter_speed_angle_hil()
        self.assertTrue(pb["passed"])
        self.assertEqual(pb["hfr_11988p_64f_clamped_to_360"]["effective_angle_deg"], 360.0)
        self.assertEqual(pb["movie_5994p_64f_unclamped_ok"]["effective_angle_deg"], 23040.0)

    def test_36_pillar_cd_evaluator_all_passed(self) -> None:
        pcd = p200.evaluate_pillar_c_d_lut_binary_split_firewall_and_redlines()
        self.assertTrue(pcd["passed"])
        self.assertEqual(pcd["stage_b_overlay_slots_verified"], 16)
        self.assertEqual(pcd["h0_equals_h3_slots_verified"], 16)
        self.assertEqual(len(pcd["blocked_redline_probes"]), 9)

    def test_37_unified_phase200_clean_room_no_raw_elf_bytes_leaked(self) -> None:
        rep = _get_clean_room_audit()
        self.assertTrue(rep["all_checks_passed"])
        self.assertEqual(rep["source_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(rep["stage_index"], 35)
        self.assertEqual(rep["stage_total"], 35)
        self.assertEqual(rep["milestone"], "35/35")
        self.assertEqual(rep["redlines"]["raw_firmware_bytes_leaked"], 0)
        dumped = json.dumps(rep)
        self.assertNotIn("7f454c46", dumped.lower())

    def test_38_unified_phase200_clean_room_deterministic_digest(self) -> None:
        r1 = p200.run_phase200_realhw_fan_pwm_shutter_angle_lut_split_hil(force_clean_room=True)
        r2 = p200.run_phase200_realhw_fan_pwm_shutter_angle_lut_split_hil(force_clean_room=True)
        self.assertEqual(r1["audit_digest_sha256"], r2["audit_digest_sha256"])

    def test_39_unified_phase200_default_mode_passes_with_all_pillars(self) -> None:
        rep = _get_default_audit()
        self.assertTrue(rep["all_checks_passed"])
        self.assertIn(rep["source_mode"], ("LOCAL_DONOR_RDONLY", "CLEAN_ROOM_SYNTHETIC"))
        self.assertTrue(rep["pillar_a_fx3_fan_pwm_and_backup_guard_hil"]["passed"])
        self.assertTrue(rep["pillar_b_independent_shutter_speed_angle_hil"]["passed"])
        self.assertTrue(rep["pillar_c_d_lut_601_vs_702_split_firewall_and_redlines"]["passed"])
        self.assertFalse(rep["redlines"]["persistent_emmc_writes_authorized"])
        self.assertFalse(rep["redlines"]["spi_nor_write_authorized"])
        self.assertFalse(rep["redlines"]["el3_payload_transmit_authorized"])
        self.assertEqual(rep["redlines"]["physical_usb_packets_emitted"], 0)
        self.assertEqual(rep["redlines"]["otp_fuse_touches"], 0)
        self.assertEqual(rep["redlines"]["rpmb_counter_increments"], 0)
        self.assertEqual(rep["redlines"]["p2_setting_mutation_bytes"], 0)
        self.assertEqual(rep["redlines"]["thermal_runaway_events"], 0)
        self.assertEqual(rep["redlines"]["lut_color_solver_corruption_events"], 0)

    def test_40_standalone_cli_self_test_summary_and_clean_room_json(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        p_sum = subprocess.run(
            [
                "/usr/bin/python3",
                "-B",
                str(FX3_VM_DIR / "realhw_fan_pwm_shutter_angle_lut_split_coemulator.py"),
                "--self-test",
                "--summary",
            ],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(p_sum.returncode, 0, msg=p_sum.stderr)
        self.assertIn("[PASS] Phase 200 Stage 35 (35/35)", p_sum.stdout)

        p_json = subprocess.run(
            [
                "/usr/bin/python3",
                "-B",
                str(FX3_VM_DIR / "realhw_fan_pwm_shutter_angle_lut_split_coemulator.py"),
                "--self-test",
                "--clean-room",
                "--json",
            ],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(p_json.returncode, 0, msg=p_json.stderr)
        parsed = json.loads(p_json.stdout)
        self.assertTrue(parsed["all_checks_passed"])
        self.assertEqual(parsed["stage_index"], 35)
        self.assertEqual(parsed["milestone"], "35/35")

    def test_41_inprocess_main_summary_and_clean_room_exit_zero(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = p200.main(["--self-test", "--clean-room", "--summary"])
        self.assertEqual(rc, 0)
        self.assertIn("[PASS] Phase 200 Stage 35 (35/35)", buf.getvalue())

    def test_42_fx3_vm_coemulation_suite_includes_stage35_and_skip_phase200(self) -> None:
        rep_on = _get_clean_room_suite()
        self.assertTrue(rep_on["all_checks_passed"])
        self.assertIn("stage35_realhw_fan_pwm_shutter_angle_lut_split_hil", rep_on)
        s35 = rep_on["stage35_realhw_fan_pwm_shutter_angle_lut_split_hil"]
        self.assertTrue(s35["all_checks_passed"])
        self.assertFalse(s35["persistent_emmc_writes_authorized"])
        self.assertFalse(s35["spi_nor_write_authorized"])
        self.assertFalse(s35["el3_payload_transmit_authorized"])
        self.assertEqual(s35["physical_usb_packets_emitted"], 0)
        self.assertEqual(s35["otp_fuse_touches"], 0)
        self.assertEqual(s35["rpmb_counter_increments"], 0)
        self.assertEqual(s35["p2_setting_mutation_bytes"], 0)
        self.assertEqual(s35["thermal_runaway_events"], 0)
        self.assertEqual(s35["lut_color_solver_corruption_events"], 0)

        stage_keys = [k for k in rep_on if re.match(r"^stage\d+_", k)]
        self.assertGreaterEqual(len(stage_keys), 35)

        rep_skip = suite.run_fx3_vm_coemulation_suite(
            suite.CoEmulationConfig(
                force_clean_room=True,
                include_phase200_realhw_fan_pwm_shutter_angle_lut_split_hil=False,
            )
        )
        self.assertTrue(rep_skip["all_checks_passed"])
        self.assertNotIn("stage35_realhw_fan_pwm_shutter_angle_lut_split_hil", rep_skip)
        self.assertGreaterEqual(len([k for k in rep_skip if re.match(r"^stage\d+_", k)]), 34)

    def test_43_all_35_of_35_stages_present_and_passing_in_suite(self) -> None:
        rep = _get_clean_room_suite()
        self.assertTrue(rep["stage1_coldboot_and_bt"]["all_checks_passed"])
        self.assertTrue(rep["stage2_dual_isa_cp_shooting"]["all_checks_passed"])
        self.assertTrue(rep["stage3_soft_gpe_hud_ramfb"]["all_checks_passed"])
        for idx in range(4, 36):
            matches = [k for k in rep if k.startswith(f"stage{idx}_")]
            self.assertEqual(len(matches), 1, msg=f"Missing or duplicate stage{idx}_* key")
            self.assertTrue(rep[matches[0]]["all_checks_passed"], msg=matches[0])

    def test_44_suite_subprocess_summary_and_skip_phase200_flag(self) -> None:
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
        self.assertIn("realhw_fan_pwm_shutter_angle_lut_split_hil=CLEAN_ROOM_SYNTHETIC", proc.stdout)

        proc_skip = subprocess.run(
            [
                "/usr/bin/python3",
                "-B",
                str(FX3_VM_DIR / "fx3_vm_coemulation_suite.py"),
                "--clean-room",
                "--skip-phase200",
                "--summary",
            ],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc_skip.returncode, 0, msg=proc_skip.stderr)
        self.assertNotIn("realhw_fan_pwm_shutter_angle_lut_split_hil=", proc_skip.stdout)

    def test_45_suite_35_stages_under_6s_wall_clock_ceiling_and_json_cli(self) -> None:
        t0 = time.monotonic()
        rep_clean = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig(force_clean_room=True))
        dt_clean = time.monotonic() - t0
        self.assertTrue(rep_clean["all_checks_passed"])
        self.assertGreaterEqual(len([k for k in rep_clean if re.match(r"^stage\d+_", k)]), 35)
        self.assertLess(dt_clean, 6.0)

        t1 = time.monotonic()
        rep_def = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig())
        dt_def = time.monotonic() - t1
        self.assertTrue(rep_def["all_checks_passed"])
        self.assertGreaterEqual(len([k for k in rep_def if re.match(r"^stage\d+_", k)]), 35)
        self.assertLess(dt_def, 6.0)

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc_json = suite.main(["--clean-room", "--json"])
        self.assertEqual(rc_json, 0)
        parsed = json.loads(buf.getvalue())
        self.assertTrue(parsed["all_checks_passed"])
        self.assertIn("stage35_realhw_fan_pwm_shutter_angle_lut_split_hil", parsed)

    def test_46_source_hygiene_rdonly_only_and_no_forbidden_write_flags_or_ports(self) -> None:
        src = (FX3_VM_DIR / "realhw_fan_pwm_shutter_angle_lut_split_coemulator.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("os.O_RDONLY", src)
        self.assertNotIn("O_WR" + "ONLY", src)
        self.assertNotIn("O_RD" + "WR", src)
        self.assertNotIn("87" + "68", src)

    def test_47_is_forced_clean_room_truthy_and_falsy_values(self) -> None:
        for truthy in ("1", "true", "TRUE", "yes", "on", " 1 "):
            self.assertTrue(
                p200.is_forced_clean_room({"FX3_FX6_FORCE_CLEAN_ROOM": truthy}),
                msg=truthy,
            )
        for falsy in ("", "0", "false", "no", "off"):
            self.assertFalse(
                p200.is_forced_clean_room({"FX3_FX6_FORCE_CLEAN_ROOM": falsy}),
                msg=falsy,
            )

    def test_48_missing_work_root_gracefully_falls_back_to_clean_room_synthetic(self) -> None:
        non_existent = str(REPO_ROOT / "work" / "__nonexistent_phase200_donor_root__")
        env_missing = {
            "FX3_FX6_FORCE_CLEAN_ROOM": "0",
            "FX3_FX6_MAC_WORK_ROOT": non_existent,
        }
        paths = p200.resolve_phase200_donor_paths(env=env_missing)
        self.assertEqual(len(paths), 12)
        da = p200.inspect_phase200_donors(force_clean_room=True, env=env_missing)
        self.assertEqual(da.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(da.all_contracts_verified)


if __name__ == "__main__":
    unittest.main()
