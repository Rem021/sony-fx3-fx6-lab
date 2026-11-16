#!/usr/bin/env python3
"""Unit tests for Phase 222 Stage 40 (`40/40` Milestone):
Real-Hardware `ILME-FX3` (`0x91030080`, `Ver. 7.02`) `[Auto Pixel Mapping]` / Manual
`[Pixel Mapping]` Auto-Restart & `cnflasha` Read-Only Firewall, `[NTSC/PAL Selector]`
Exclusive Frame-Rate / `DF-NDF` Tables & `[Camera Settings Reset]` Persistence, and
`[Gamma Display Assist]` 4-Mode Table vs `[Log Shooting]` `[Display LUT]` Lockout &
Camera-LCD-Only Scope HIL Co-Emulator.
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import contextlib
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
import realhw_pixelmap_ntscpal_gammaassist_displaylut_coemulator as p222  # noqa: E402


_CLEAN_ROOM_AUDIT_CACHE = None
_DEFAULT_AUDIT_CACHE = None
_CLEAN_SUITE_CACHE = None
_CLEAN_SUITE_ELAPSED = None
_DEFAULT_SUITE_CACHE = None
_DEFAULT_SUITE_ELAPSED = None


def _get_clean_room_audit():
    global _CLEAN_ROOM_AUDIT_CACHE
    if _CLEAN_ROOM_AUDIT_CACHE is None:
        _CLEAN_ROOM_AUDIT_CACHE = (
            p222.run_phase222_realhw_pixelmap_ntscpal_gammaassist_displaylut_hil(
                force_clean_room=True
            )
        )
    return _CLEAN_ROOM_AUDIT_CACHE


def _get_default_audit():
    global _DEFAULT_AUDIT_CACHE
    if _DEFAULT_AUDIT_CACHE is None:
        _DEFAULT_AUDIT_CACHE = (
            p222.run_phase222_realhw_pixelmap_ntscpal_gammaassist_displaylut_hil()
        )
    return _DEFAULT_AUDIT_CACHE


def _get_clean_room_suite():
    global _CLEAN_SUITE_CACHE, _CLEAN_SUITE_ELAPSED
    if _CLEAN_SUITE_CACHE is None:
        t0 = time.monotonic()
        _CLEAN_SUITE_CACHE = suite.run_fx3_vm_coemulation_suite(
            suite.CoEmulationConfig(force_clean_room=True)
        )
        _CLEAN_SUITE_ELAPSED = time.monotonic() - t0
    return _CLEAN_SUITE_CACHE, float(_CLEAN_SUITE_ELAPSED)


def _get_default_suite():
    global _DEFAULT_SUITE_CACHE, _DEFAULT_SUITE_ELAPSED
    if _DEFAULT_SUITE_CACHE is None:
        t0 = time.monotonic()
        _DEFAULT_SUITE_CACHE = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig())
        _DEFAULT_SUITE_ELAPSED = time.monotonic() - t0
    return _DEFAULT_SUITE_CACHE, float(_DEFAULT_SUITE_ELAPSED)


class TestPhase222PixelMapNtscPalGammaAssistDisplayLutCoEmulator(unittest.TestCase):
    def test_01_schema_version_stage_40_milestone_and_redline_constants(self) -> None:
        self.assertEqual(
            p222.PHASE_222_SCHEMA,
            "phase222_realhw_pixelmap_ntscpal_gammaassist_displaylut_coemulator_v1",
        )
        self.assertEqual(p222.PHASE_222_VERSION, "222.0.0")
        self.assertEqual(p222.STAGE_INDEX, 40)
        self.assertEqual(p222.STAGE_TOTAL, 40)
        self.assertEqual(p222.MILESTONE_LABEL, "40/40")
        self.assertEqual(
            p222.STAGE_NAME,
            "stage40_realhw_pixelmap_ntscpal_gammaassist_displaylut_hil",
        )
        self.assertEqual(p222.FX3_MODEL_ID, 0x91030080)
        self.assertTrue(p222.P8_CP_MUTATION_FORBIDDEN)
        self.assertTrue(p222.CNFLASHA_USERSPACE_WRITE_BLOCKED)
        self.assertEqual(p222.CNFLASHA_MUTATION_BYTES, 0)
        self.assertFalse(p222.PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(p222.SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(p222.EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        self.assertEqual(p222.PHYSICAL_USB_PACKETS_EMITTED, 0)
        self.assertEqual(p222.OTP_FUSE_TOUCHES, 0)
        self.assertEqual(p222.RPMB_COUNTER_INCREMENTS, 0)
        self.assertEqual(p222.STAGE_B_TMP_MOUNT_RESIDUALS_AFTER_PIXELMAP_REBOOT, 0)
        self.assertEqual(p222.NTSC_PAL_CROSS_REGION_DB_CONTAMINATION_EVENTS, 0)
        self.assertEqual(p222.LOG_SHOOTING_GAMMA_ASSIST_OR_HDMI_LEAKAGE_EVENTS, 0)
        self.assertEqual(p222.RAW_FIRMWARE_BYTES_LEAKED, 0)
        self.assertEqual(p222.DONOR_ACCESS_MODE, "O_RDONLY")

    def test_02_donor_inspection_fast_bounded_and_cached(self) -> None:
        p222._DONOR_AUDIT_CACHE.clear()
        t0 = time.monotonic()
        da1 = p222.inspect_phase222_donors(force_clean_room=False)
        dt1 = time.monotonic() - t0
        t1 = time.monotonic()
        da2 = p222.inspect_phase222_donors(force_clean_room=False)
        dt2 = time.monotonic() - t1
        self.assertLess(dt1, 0.05)
        self.assertLess(dt2, 0.01)
        self.assertEqual(da1.donor_files_inspected, 12)
        self.assertEqual(da1.raw_firmware_bytes_leaked, 0)
        self.assertTrue(da1.all_contracts_verified)
        self.assertEqual(da1.errors, ())
        if da1.source_mode == "LOCAL_DONOR_RDONLY":
            self.assertIs(da1, da2)

    def test_03_clean_room_donor_fallback_via_flag_and_env(self) -> None:
        da_flag = p222.inspect_phase222_donors(force_clean_room=True)
        self.assertEqual(da_flag.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(da_flag.access_mode, "O_RDONLY")
        self.assertEqual(da_flag.donor_files_inspected, 12)
        self.assertEqual(da_flag.raw_firmware_bytes_leaked, 0)
        self.assertTrue(da_flag.all_contracts_verified)

        da_env = p222.inspect_phase222_donors(env={"FX3_FX6_FORCE_CLEAN_ROOM": "1"})
        self.assertEqual(da_env.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertIs(da_env, da_flag)

    def test_04_clean_room_sentinel_paths_do_not_touch_local_donors(self) -> None:
        paths_clean = p222.resolve_phase222_donor_paths(env={"FX3_FX6_FORCE_CLEAN_ROOM": "1"})
        self.assertEqual(len(paths_clean), 12)
        for p in paths_clean.values():
            self.assertIn(p222.CLEAN_ROOM_SENTINEL_DIRNAME, str(p))
            self.assertFalse(p.exists())
        da = p222.inspect_phase222_donors(env={"FX3_FX6_FORCE_CLEAN_ROOM": "1"})
        self.assertEqual(da.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(da.all_contracts_verified)
        self.assertEqual(da.raw_firmware_bytes_leaked, 0)

    def test_05_twelve_donors_expected_sizes_and_bounded_windows(self) -> None:
        da = p222.inspect_phase222_donors()
        self.assertEqual(da.fx3_lens_comm.file_bytes, 14_544)
        self.assertEqual(da.fx6_lens_comm.file_bytes, 14_544)
        self.assertEqual(da.fx3_media_cfg.file_bytes, 52_312)
        self.assertEqual(da.fx3_adj_media.file_bytes, 318_152)
        self.assertEqual(da.fx3_string_en_f.file_bytes, 373_820)
        self.assertEqual(da.fx6_string_en.file_bytes, 118_208)
        self.assertEqual(da.fx3_appfw.file_bytes, 79_015_712)
        self.assertEqual(da.fx6_appfw.file_bytes, 50_520_424)
        self.assertEqual(da.fx3_cpapp.file_bytes, 15_980_568)
        self.assertEqual(da.fx6_cpapp.file_bytes, 17_952_816)
        self.assertEqual(da.fx3_libmpr.file_bytes, 3_517_008)
        self.assertEqual(da.fx6_libmpr.file_bytes, 28_921_824)
        for key, large in (
            ("fx3_appfw", da.fx3_appfw),
            ("fx6_appfw", da.fx6_appfw),
            ("fx3_cpapp", da.fx3_cpapp),
            ("fx6_cpapp", da.fx6_cpapp),
            ("fx3_libmpr", da.fx3_libmpr),
            ("fx6_libmpr", da.fx6_libmpr),
        ):
            self.assertTrue(large.bounded_windows_only, msg=key)
            self.assertLessEqual(
                large.bytes_read_total,
                (len(p222.LARGE_DONOR_WINDOWS[key]) + 1) * p222.BOUNDED_WINDOW_MAX_BYTES,
                msg=key,
            )

    def test_06_donor_wave30_menu_and_symbol_proofs(self) -> None:
        da = p222.inspect_phase222_donors()
        self.assertTrue(da.pixel_mapping_reboot_and_cnflasha_ro_proven)
        self.assertTrue(da.ntsc_pal_reset_persistence_and_db_split_proven)
        self.assertTrue(da.gamma_assist_4mode_vs_display_lut_split_proven)
        hits = da.fx3_string_en_f.marker_hits
        for token in (
            "Auto Pixel Mapping",
            "Pixel Mapping",
            "Silent Mode",
            "NTSC/PAL Selector",
            "Camera Settings Reset",
            "Initialize",
            "TC Format",
            "23.98p",
            "25p",
            "Gamma Display Assist",
            "Gamma Disp. Assist Typ.",
            "S-Log3\u2192709(800%)",
            "HLG(BT.2020)",
            "HLG(709)",
            "HLG Still Image",
            "Log Shooting",
            "Cine EI",
            "Cine EI Quick",
            "Flexible ISO",
            "Display LUT",
            "Display LUT Switch",
        ):
            self.assertEqual(hits.get(token), 1, msg=token)
        self.assertEqual(da.fx3_appfw.window_hits.get("AUTO_PIXEL_MAPPING"), 1)
        self.assertEqual(da.fx3_appfw.window_hits.get("PIXEL_MAPPING"), 1)
        self.assertEqual(da.fx3_appfw.window_hits.get("NTSC_PAL"), 1)
        self.assertEqual(da.fx3_appfw.window_hits.get("AVCHD"), 1)
        self.assertEqual(da.fx3_appfw.window_hits.get("GAMMA_DISP"), 1)
        self.assertEqual(da.fx3_appfw.window_hits.get("LOG_SHOOTING"), 1)
        self.assertEqual(da.fx6_appfw.window_hits.get("APR"), 1)

    def test_07_submodel_a_auto_pixel_mapping_default_on_poweroff_darkframe_even_in_silent_mode(
        self,
    ) -> None:
        res = p222.probe_pixel_mapping_reboot_and_cnflasha_firewall_hil(
            auto_pixel_mapping="On",
            trigger=p222.TRIGGER_POWER_OFF,
            silent_mode="On",
            battery_charge_pct=80,
            auto_interval_due=True,
            days_since_last_pixel_mapping=4,
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.auto_pixel_mapping, "On")
        self.assertTrue(res.calibration_executed)
        self.assertTrue(res.power_off_shutter_dark_frame_sound_emitted)
        self.assertTrue(res.silent_mode_shutter_sound_permitted)
        self.assertTrue(res.operator_controls_locked_during_calibration)
        self.assertFalse(res.automatic_camera_restart_triggered)
        self.assertEqual(res.days_since_last_pixel_mapping, 0)
        self.assertEqual(res.post_reboot_tmp_stage_b_mounts, ())
        self.assertTrue(res.stage_b_tmp_mounts_wiped_clean)
        self.assertTrue(res.cnflasha_userspace_write_blocked)

    def test_08_submodel_a_poweroff_skips_auto_pixel_mapping_when_off_not_due_or_low_battery(
        self,
    ) -> None:
        off_po = p222.probe_pixel_mapping_reboot_and_cnflasha_firewall_hil(
            auto_pixel_mapping="Off",
            trigger=p222.TRIGGER_POWER_OFF,
            battery_charge_pct=85,
            days_since_last_pixel_mapping=2,
        )
        self.assertTrue(off_po.admitted)
        self.assertFalse(off_po.calibration_executed)
        self.assertFalse(off_po.power_off_shutter_dark_frame_sound_emitted)

        not_due = p222.probe_pixel_mapping_reboot_and_cnflasha_firewall_hil(
            auto_pixel_mapping="On",
            trigger=p222.TRIGGER_POWER_OFF,
            auto_interval_due=False,
            battery_charge_pct=85,
        )
        self.assertFalse(not_due.calibration_executed)

        low_batt_po = p222.probe_pixel_mapping_reboot_and_cnflasha_firewall_hil(
            auto_pixel_mapping="On",
            trigger=p222.TRIGGER_POWER_OFF,
            auto_interval_due=True,
            battery_charge_pct=15,
        )
        self.assertTrue(low_batt_po.admitted)
        self.assertFalse(low_batt_po.calibration_executed)
        self.assertTrue(low_batt_po.low_battery_rejected)

    def test_09_submodel_a_auto_pixel_mapping_off_emits_3day_manual_cadence_warning(self) -> None:
        day2 = p222.probe_pixel_mapping_reboot_and_cnflasha_firewall_hil(
            auto_pixel_mapping="Off",
            trigger=p222.TRIGGER_IDLE_STANDBY,
            days_since_last_pixel_mapping=2,
        )
        self.assertFalse(day2.three_day_manual_cadence_warning)

        day3 = p222.probe_pixel_mapping_reboot_and_cnflasha_firewall_hil(
            auto_pixel_mapping="Off",
            trigger=p222.TRIGGER_IDLE_STANDBY,
            days_since_last_pixel_mapping=3,
        )
        self.assertTrue(day3.three_day_manual_cadence_warning)
        self.assertEqual(day3.recommended_manual_cadence_days, 3)

        auto_on_day5 = p222.probe_pixel_mapping_reboot_and_cnflasha_firewall_hil(
            auto_pixel_mapping="On",
            trigger=p222.TRIGGER_IDLE_STANDBY,
            days_since_last_pixel_mapping=5,
        )
        self.assertFalse(auto_on_day5.three_day_manual_cadence_warning)

    def test_10_submodel_a_manual_pixel_mapping_auto_restart_wipes_tmp_stage_b_mounts_h0_eq_h2(
        self,
    ) -> None:
        manual = p222.probe_pixel_mapping_reboot_and_cnflasha_firewall_hil(
            trigger=p222.TRIGGER_MANUAL_OK,
            silent_mode="On",
            battery_charge_pct=20,
            days_since_last_pixel_mapping=7,
            prior_tmp_stage_b_mounts=p222.DEFAULT_VOLATILE_STAGE_B_MOUNTS,
        )
        self.assertTrue(manual.admitted)
        self.assertTrue(manual.calibration_executed)
        self.assertTrue(manual.power_off_shutter_dark_frame_sound_emitted)
        self.assertTrue(manual.operator_controls_locked_during_calibration)
        self.assertTrue(manual.automatic_camera_restart_triggered)
        self.assertEqual(len(manual.prior_tmp_stage_b_mounts), 2)
        self.assertEqual(manual.post_reboot_tmp_stage_b_mounts, ())
        self.assertTrue(manual.stage_b_tmp_mounts_wiped_clean)
        self.assertEqual(manual.booted_firmware_after_restart, p222.STOCK_FX3_BOOT_IDENTITY)
        self.assertTrue(manual.h0_equals_h2_verified)
        self.assertEqual(manual.stage_b_tmp_mount_residuals_after_pixelmap_reboot, 0)
        self.assertEqual(manual.errno_code, 0)

    def test_11_submodel_a_manual_pixel_mapping_low_battery_lt20pct_rejected_eopnotsupp(
        self,
    ) -> None:
        low_batt = p222.probe_pixel_mapping_reboot_and_cnflasha_firewall_hil(
            trigger=p222.TRIGGER_MANUAL_OK,
            battery_charge_pct=19,
        )
        self.assertFalse(low_batt.admitted)
        self.assertTrue(low_batt.low_battery_rejected)
        self.assertFalse(low_batt.calibration_executed)
        self.assertFalse(low_batt.automatic_camera_restart_triggered)
        self.assertEqual(low_batt.errno_code, p222.EOPNOTSUPP_ERRNO)

    def test_12_submodel_a_operator_controls_locked_ebusy_during_calibration(self) -> None:
        locked = p222.probe_pixel_mapping_reboot_and_cnflasha_firewall_hil(
            trigger=p222.TRIGGER_MANUAL_OK,
            battery_charge_pct=90,
            attempt_operator_input_during_calibration=True,
        )
        self.assertFalse(locked.admitted)
        self.assertTrue(locked.operator_controls_locked_during_calibration)
        self.assertEqual(locked.errno_code, p222.EBUSY_ERRNO)

    def test_13_submodel_a_cnflasha_userspace_write_blocked_erofs_and_tmp_persistence_blocked(
        self,
    ) -> None:
        cnfl = p222.probe_pixel_mapping_reboot_and_cnflasha_firewall_hil(
            attempt_userspace_cnflasha_write=True
        )
        self.assertFalse(cnfl.admitted)
        self.assertTrue(cnfl.cnflasha_userspace_write_blocked)
        self.assertEqual(cnfl.cnflasha_mutation_bytes, 0)
        self.assertEqual(cnfl.errno_code, p222.EROFS_ERRNO)

        tmp_persist = p222.probe_pixel_mapping_reboot_and_cnflasha_firewall_hil(
            attempt_preserve_tmp_mount_across_reboot=True
        )
        self.assertFalse(tmp_persist.admitted)
        self.assertEqual(tmp_persist.stage_b_tmp_mount_residuals_after_pixelmap_reboot, 0)
        self.assertEqual(tmp_persist.errno_code, p222.EOPNOTSUPP_ERRNO)

    def test_14_submodel_a_idle_standby_retains_session_and_rejects_invalid_arguments(self) -> None:
        idle = p222.probe_pixel_mapping_reboot_and_cnflasha_firewall_hil(
            trigger=p222.TRIGGER_IDLE_STANDBY,
            prior_tmp_stage_b_mounts=("/tmp/fx6_stageb_overlay/appFw.so",),
        )
        self.assertTrue(idle.admitted)
        self.assertEqual(idle.post_reboot_tmp_stage_b_mounts, ("/tmp/fx6_stageb_overlay/appFw.so",))
        self.assertFalse(idle.stage_b_tmp_mounts_wiped_clean)
        self.assertEqual(idle.booted_firmware_after_restart, "ACTIVE_STANDBY_SESSION")

        with self.assertRaises(p222.RealHwPixelMapNtscPalGammaAssistDisplayLutError):
            p222.probe_pixel_mapping_reboot_and_cnflasha_firewall_hil(auto_pixel_mapping="Auto")
        with self.assertRaises(p222.RealHwPixelMapNtscPalGammaAssistDisplayLutError):
            p222.probe_pixel_mapping_reboot_and_cnflasha_firewall_hil(trigger="APR")
        with self.assertRaises(p222.RealHwPixelMapNtscPalGammaAssistDisplayLutError):
            p222.probe_pixel_mapping_reboot_and_cnflasha_firewall_hil(battery_charge_pct=101)
        with self.assertRaises(p222.RealHwPixelMapNtscPalGammaAssistDisplayLutError):
            p222.probe_pixel_mapping_reboot_and_cnflasha_firewall_hil(
                days_since_last_pixel_mapping=-1
            )

    def test_15_pillar_a_evaluator_matrix_passes_100pct(self) -> None:
        pa = p222.evaluate_pillar_a_pixel_mapping_reboot_and_cnflasha_hil()
        self.assertTrue(pa["passed"])
        self.assertTrue(pa["manual_pixel_mapping_auto_restart_h0_eq_h2"]["h0_equals_h2_verified"])
        self.assertTrue(pa["cnflasha_userspace_write_blocked"]["cnflasha_userspace_write_blocked"])

    def test_16_submodel_b_ntsc_exclusive_frame_rates_dci_24p_and_df_ndf_tc_format(self) -> None:
        for fps in ("23.98p", "29.97p", "59.94p", "119.88p"):
            res = p222.probe_ntsc_pal_selector_reset_persistence_hil(
                configured_ntsc_pal=p222.VIDEO_SYSTEM_NTSC,
                requested_fps=fps,
                requested_tc_format=p222.TC_FORMAT_DF,
            )
            self.assertTrue(res.admitted, msg=fps)
            self.assertTrue(res.fps_23_98p_available)
            self.assertTrue(res.tc_format_menu_available)
            self.assertEqual(res.available_tc_formats, ("DF", "NDF"))
            expected_tc = "NDF" if fps == "23.98p" else "DF"
            self.assertEqual(res.effective_tc_format, expected_tc)

        dci = p222.probe_ntsc_pal_selector_reset_persistence_hil(
            configured_ntsc_pal=p222.VIDEO_SYSTEM_NTSC,
            dci_24p_enabled=True,
            requested_fps="24.00p",
            requested_tc_format=p222.TC_FORMAT_DF,
        )
        self.assertTrue(dci.admitted)
        self.assertIn("24.00p", dci.available_frame_rates)
        self.assertEqual(dci.effective_tc_format, "NDF")

        dci_disabled = p222.probe_ntsc_pal_selector_reset_persistence_hil(
            configured_ntsc_pal=p222.VIDEO_SYSTEM_NTSC,
            dci_24p_enabled=False,
            requested_fps="24.00p",
        )
        self.assertFalse(dci_disabled.admitted)
        self.assertEqual(dci_disabled.errno_code, p222.EOPNOTSUPP_ERRNO)

    def test_17_submodel_b_pal_exclusive_frame_rates_blocks_2398p_and_blocks_df_ndf(self) -> None:
        for fps in ("25p", "50p", "100p"):
            pal_ok = p222.probe_ntsc_pal_selector_reset_persistence_hil(
                regional_factory_default=p222.VIDEO_SYSTEM_PAL,
                configured_ntsc_pal=p222.VIDEO_SYSTEM_PAL,
                requested_fps=fps,
            )
            self.assertTrue(pal_ok.admitted, msg=fps)
            self.assertFalse(pal_ok.fps_23_98p_available)
            self.assertFalse(pal_ok.tc_format_menu_available)
            self.assertEqual(pal_ok.available_tc_formats, ())
            self.assertEqual(pal_ok.effective_tc_format, p222.TC_FORMAT_PAL_LOCKED)

        pal_2398 = p222.probe_ntsc_pal_selector_reset_persistence_hil(
            configured_ntsc_pal=p222.VIDEO_SYSTEM_PAL,
            requested_fps="23.98p",
        )
        self.assertFalse(pal_2398.admitted)
        self.assertEqual(pal_2398.errno_code, p222.EOPNOTSUPP_ERRNO)

        for tc_fmt in (p222.TC_FORMAT_DF, p222.TC_FORMAT_NDF):
            pal_tc = p222.probe_ntsc_pal_selector_reset_persistence_hil(
                configured_ntsc_pal=p222.VIDEO_SYSTEM_PAL,
                requested_fps="25p",
                requested_tc_format=tc_fmt,
            )
            self.assertFalse(pal_tc.admitted, msg=tc_fmt)
            self.assertEqual(pal_tc.errno_code, p222.EOPNOTSUPP_ERRNO)

        pal_toggle = p222.probe_ntsc_pal_selector_reset_persistence_hil(
            configured_ntsc_pal=p222.VIDEO_SYSTEM_PAL,
            attempt_tc_format_toggle_in_pal=True,
        )
        self.assertFalse(pal_toggle.admitted)
        self.assertEqual(pal_toggle.errno_code, p222.EOPNOTSUPP_ERRNO)

    def test_18_submodel_b_running_on_ntsc_and_running_on_pal_startup_banners(self) -> None:
        same_ntsc = p222.probe_ntsc_pal_selector_reset_persistence_hil(
            regional_factory_default=p222.VIDEO_SYSTEM_NTSC,
            configured_ntsc_pal=p222.VIDEO_SYSTEM_NTSC,
        )
        self.assertFalse(same_ntsc.startup_banner_displayed)
        self.assertEqual(same_ntsc.startup_banner, "")

        pal_on_ntsc = p222.probe_ntsc_pal_selector_reset_persistence_hil(
            regional_factory_default=p222.VIDEO_SYSTEM_NTSC,
            configured_ntsc_pal=p222.VIDEO_SYSTEM_PAL,
        )
        self.assertTrue(pal_on_ntsc.startup_banner_displayed)
        self.assertEqual(pal_on_ntsc.startup_banner, "Running on PAL.")

        ntsc_on_pal = p222.probe_ntsc_pal_selector_reset_persistence_hil(
            regional_factory_default=p222.VIDEO_SYSTEM_PAL,
            configured_ntsc_pal=p222.VIDEO_SYSTEM_NTSC,
        )
        self.assertTrue(ntsc_on_pal.startup_banner_displayed)
        self.assertEqual(ntsc_on_pal.startup_banner, "Running on NTSC.")

    def test_19_submodel_b_camera_settings_reset_preserves_ntsc_pal_selector(self) -> None:
        cam_rst_pal = p222.probe_ntsc_pal_selector_reset_persistence_hil(
            regional_factory_default=p222.VIDEO_SYSTEM_NTSC,
            configured_ntsc_pal=p222.VIDEO_SYSTEM_PAL,
            reset_action=p222.RESET_ACTION_CAMERA_SETTINGS,
            requested_fps="50p",
        )
        self.assertTrue(cam_rst_pal.admitted)
        self.assertTrue(cam_rst_pal.preserved_across_camera_settings_reset)
        self.assertFalse(cam_rst_pal.restored_to_factory_by_initialize)
        self.assertEqual(cam_rst_pal.effective_ntsc_pal, "PAL")
        self.assertEqual(cam_rst_pal.startup_banner, "Running on PAL.")

    def test_20_submodel_b_full_initialize_restores_regional_factory_default_and_clears_banner(
        self,
    ) -> None:
        init_ntsc = p222.probe_ntsc_pal_selector_reset_persistence_hil(
            regional_factory_default=p222.VIDEO_SYSTEM_NTSC,
            configured_ntsc_pal=p222.VIDEO_SYSTEM_PAL,
            reset_action=p222.RESET_ACTION_INITIALIZE,
            requested_fps="59.94p",
            requested_tc_format="NDF",
        )
        self.assertTrue(init_ntsc.admitted)
        self.assertTrue(init_ntsc.restored_to_factory_by_initialize)
        self.assertFalse(init_ntsc.preserved_across_camera_settings_reset)
        self.assertEqual(init_ntsc.effective_ntsc_pal, "NTSC")
        self.assertFalse(init_ntsc.startup_banner_displayed)
        self.assertEqual(init_ntsc.startup_banner, "")
        self.assertEqual(init_ntsc.effective_tc_format, "NDF")

    def test_21_submodel_b_dualslot_media_database_region_mismatch_blocked_unless_reinit(
        self,
    ) -> None:
        blocked = p222.probe_ntsc_pal_selector_reset_persistence_hil(
            configured_ntsc_pal=p222.VIDEO_SYSTEM_PAL,
            recording_media="Simult. Recording",
            slot1_db_region="PAL",
            slot2_db_region="NTSC",
            allow_media_db_reinit=False,
        )
        self.assertFalse(blocked.admitted)
        self.assertTrue(blocked.media_db_region_mismatch)
        self.assertTrue(blocked.card_db_reinit_prompt_required)
        self.assertFalse(blocked.media_db_reinitialized)
        self.assertEqual(blocked.ntsc_pal_cross_region_db_contamination_events, 0)
        self.assertEqual(blocked.errno_code, p222.EOPNOTSUPP_ERRNO)

        reinit_ok = p222.probe_ntsc_pal_selector_reset_persistence_hil(
            configured_ntsc_pal=p222.VIDEO_SYSTEM_PAL,
            recording_media="Simult. Recording",
            slot1_db_region="PAL",
            slot2_db_region="NTSC",
            allow_media_db_reinit=True,
        )
        self.assertTrue(reinit_ok.admitted)
        self.assertTrue(reinit_ok.media_db_region_mismatch)
        self.assertTrue(reinit_ok.media_db_reinitialized)
        self.assertEqual(reinit_ok.active_slot_db_regions_after, {"Slot 1": "PAL", "Slot 2": "PAL"})

    def test_22_submodel_b_single_slot_db_isolation_ignores_inactive_slot_region(self) -> None:
        s1_only = p222.probe_ntsc_pal_selector_reset_persistence_hil(
            configured_ntsc_pal=p222.VIDEO_SYSTEM_NTSC,
            recording_media="Slot 1",
            slot1_db_region="NTSC",
            slot2_db_region="PAL",
            allow_media_db_reinit=False,
        )
        self.assertTrue(s1_only.admitted)
        self.assertFalse(s1_only.media_db_region_mismatch)
        self.assertEqual(s1_only.active_slot_db_regions_after, {"Slot 1": "NTSC"})

    def test_23_submodel_b_invalid_fps_tc_format_and_config_errors(self) -> None:
        bad_fps = p222.probe_ntsc_pal_selector_reset_persistence_hil(requested_fps="48p")
        self.assertFalse(bad_fps.admitted)
        self.assertEqual(bad_fps.errno_code, p222.EINVAL_ERRNO)

        ntsc_pal_fps = p222.probe_ntsc_pal_selector_reset_persistence_hil(
            configured_ntsc_pal="NTSC",
            requested_fps="25p",
        )
        self.assertFalse(ntsc_pal_fps.admitted)
        self.assertEqual(ntsc_pal_fps.errno_code, p222.EOPNOTSUPP_ERRNO)

        bad_tc_ntsc = p222.probe_ntsc_pal_selector_reset_persistence_hil(
            configured_ntsc_pal="NTSC",
            requested_tc_format="DROP_25",
        )
        self.assertFalse(bad_tc_ntsc.admitted)
        self.assertEqual(bad_tc_ntsc.errno_code, p222.EINVAL_ERRNO)

        bad_tc_pal = p222.probe_ntsc_pal_selector_reset_persistence_hil(
            configured_ntsc_pal="PAL",
            requested_tc_format="DROP_25",
        )
        self.assertFalse(bad_tc_pal.admitted)
        self.assertEqual(bad_tc_pal.errno_code, p222.EINVAL_ERRNO)

        with self.assertRaises(p222.RealHwPixelMapNtscPalGammaAssistDisplayLutError):
            p222.probe_ntsc_pal_selector_reset_persistence_hil(configured_ntsc_pal="SECAM")
        with self.assertRaises(p222.RealHwPixelMapNtscPalGammaAssistDisplayLutError):
            p222.probe_ntsc_pal_selector_reset_persistence_hil(slot1_db_region="SECAM")

    def test_24_pillar_b_evaluator_matrix_passes_100pct(self) -> None:
        pb = p222.evaluate_pillar_b_ntsc_pal_reset_persistence_hil()
        self.assertTrue(pb["passed"])
        self.assertEqual(
            pb["ntsc_on_pal_body_preserved_across_camera_settings_reset"]["effective_ntsc_pal"],
            "NTSC",
        )
        self.assertEqual(
            pb["full_initialize_restores_regional_default"]["effective_ntsc_pal"],
            "NTSC",
        )

    def test_25_submodel_c_gamma_disp_assist_exact_4mode_table_and_slog2_rejection(self) -> None:
        self.assertEqual(
            p222.VALID_GAMMA_DISP_ASSIST_TYPES,
            ("Auto", "S-Log3->709(800%)", "HLG(BT.2020)", "HLG(709)"),
        )
        for bad_slog2 in ("S-Log2->709(800%)", "S-Log2"):
            rej = p222.probe_gamma_display_assist_vs_display_lut_hil(
                gamma_disp_assist_type=bad_slog2
            )
            self.assertFalse(rej.admitted, msg=bad_slog2)
            self.assertTrue(rej.slog2_assist_rejected)
            self.assertEqual(rej.errno_code, p222.EINVAL_ERRNO)

        rej_other = p222.probe_gamma_display_assist_vs_display_lut_hil(
            gamma_disp_assist_type="Cinetone->709"
        )
        self.assertFalse(rej_other.admitted)
        self.assertFalse(rej_other.slog2_assist_rejected)
        self.assertEqual(rej_other.errno_code, p222.EINVAL_ERRNO)

    def test_26_submodel_c_auto_gamma_assist_maps_slog3_hlg_and_bypasses_rec709_scinetone(
        self,
    ) -> None:
        slog3_auto = p222.probe_gamma_display_assist_vs_display_lut_hil(
            log_shooting="Off",
            requested_gamma_display_assist="On",
            gamma_disp_assist_type="Auto",
            source_gamma="S-Log3",
        )
        self.assertTrue(slog3_auto.admitted)
        self.assertTrue(slog3_auto.camera_lcd_gamma_assist_applied)
        self.assertEqual(slog3_auto.applied_lcd_assist_curve, "S-Log3->709(800%)")
        self.assertFalse(slog3_auto.external_hdmi_gamma_assist_applied)

        for hlg_g in ("HLG1", "HLG2", "HLG3"):
            hlg_auto = p222.probe_gamma_display_assist_vs_display_lut_hil(
                log_shooting="Off",
                requested_gamma_display_assist="On",
                gamma_disp_assist_type="Auto",
                source_gamma=hlg_g,
            )
            self.assertTrue(hlg_auto.camera_lcd_gamma_assist_applied, msg=hlg_g)
            self.assertEqual(hlg_auto.applied_lcd_assist_curve, "HLG(709)")

        for std_g in ("ITU709", "S-Cinetone", "None"):
            std_auto = p222.probe_gamma_display_assist_vs_display_lut_hil(
                log_shooting="Off",
                requested_gamma_display_assist="On",
                gamma_disp_assist_type="Auto",
                source_gamma=std_g,
            )
            self.assertTrue(std_auto.admitted, msg=std_g)
            self.assertFalse(std_auto.camera_lcd_gamma_assist_applied)
            self.assertEqual(std_auto.applied_lcd_assist_curve, "NONE")

    def test_27_submodel_c_gamma_display_assist_off_leaves_native_unconverted_lcd_pipeline(
        self,
    ) -> None:
        off_pp = p222.probe_gamma_display_assist_vs_display_lut_hil(
            log_shooting="Off",
            requested_gamma_display_assist="Off",
            gamma_disp_assist_type="S-Log3->709(800%)",
            source_gamma="S-Log3",
        )
        self.assertTrue(off_pp.admitted)
        self.assertEqual(off_pp.effective_gamma_display_assist, "Off")
        self.assertFalse(off_pp.camera_lcd_gamma_assist_applied)
        self.assertEqual(off_pp.camera_lcd_preview_pipeline, "NATIVE:S-Log3")

    def test_28_submodel_c_still_playback_hlg_still_image_gate_and_slog3_exclusion(self) -> None:
        hlg_still_on = p222.probe_gamma_display_assist_vs_display_lut_hil(
            log_shooting="Off",
            requested_gamma_display_assist="On",
            gamma_disp_assist_type="HLG(BT.2020)",
            source_gamma="HLG3",
            view_context="StillPlayback",
            hlg_still_image="On",
        )
        self.assertTrue(hlg_still_on.camera_lcd_gamma_assist_applied)
        self.assertEqual(hlg_still_on.applied_lcd_assist_curve, "HLG(BT.2020)")

        hlg_still_off = p222.probe_gamma_display_assist_vs_display_lut_hil(
            log_shooting="Off",
            requested_gamma_display_assist="On",
            gamma_disp_assist_type="HLG(709)",
            source_gamma="HLG3",
            view_context="StillPlayback",
            hlg_still_image="Off",
        )
        self.assertFalse(hlg_still_off.camera_lcd_gamma_assist_applied)

        slog3_still = p222.probe_gamma_display_assist_vs_display_lut_hil(
            log_shooting="Off",
            requested_gamma_display_assist="On",
            gamma_disp_assist_type="S-Log3->709(800%)",
            source_gamma="S-Log3",
            view_context="StillPlayback",
            hlg_still_image="On",
        )
        self.assertFalse(slog3_still.camera_lcd_gamma_assist_applied)

    def test_29_submodel_c_log_shooting_3modes_hard_lock_gamma_assist_off_and_delegate_display_lut(
        self,
    ) -> None:
        for mode in ("Cine EI", "Cine EI Quick", "Flexible ISO"):
            res = p222.probe_gamma_display_assist_vs_display_lut_hil(
                log_shooting=mode,
                requested_gamma_display_assist="On",
                requested_display_lut="On",
            )
            self.assertTrue(res.admitted, msg=mode)
            self.assertTrue(res.gamma_display_assist_locked_off)
            self.assertEqual(res.effective_gamma_display_assist, "Off")
            self.assertFalse(res.camera_lcd_gamma_assist_applied)
            self.assertTrue(res.display_lut_available)
            self.assertEqual(res.effective_display_lut, "On")
            self.assertEqual(res.camera_lcd_preview_pipeline, "DISPLAY_LUT_3D")
            self.assertFalse(res.external_hdmi_gamma_assist_applied)

    def test_30_submodel_c_display_lut_switch_toggle_and_force_gamma_assist_in_log_blocked(
        self,
    ) -> None:
        toggled_off = p222.probe_gamma_display_assist_vs_display_lut_hil(
            log_shooting="Cine EI",
            requested_display_lut="On",
            display_lut_switch_pressed=True,
        )
        self.assertTrue(toggled_off.admitted)
        self.assertEqual(toggled_off.effective_display_lut, "Off")
        self.assertEqual(toggled_off.camera_lcd_preview_pipeline, "UNCONVERTED_SLOG3")

        toggled_on = p222.probe_gamma_display_assist_vs_display_lut_hil(
            log_shooting="Flexible ISO",
            requested_display_lut="Off",
            display_lut_switch_pressed=True,
        )
        self.assertEqual(toggled_on.effective_display_lut, "On")
        self.assertEqual(toggled_on.camera_lcd_preview_pipeline, "DISPLAY_LUT_3D")

        blk = p222.probe_gamma_display_assist_vs_display_lut_hil(
            log_shooting="Cine EI Quick",
            attempt_force_gamma_assist_in_log_shooting=True,
        )
        self.assertFalse(blk.admitted)
        self.assertTrue(blk.gamma_display_assist_locked_off)
        self.assertEqual(blk.errno_code, p222.EOPNOTSUPP_ERRNO)

    def test_31_submodel_c_camera_lcd_only_scope_never_applies_gamma_assist_to_external_hdmi(
        self,
    ) -> None:
        pp_hdmi = p222.probe_gamma_display_assist_vs_display_lut_hil(
            log_shooting="Off",
            requested_gamma_display_assist="On",
            gamma_disp_assist_type="S-Log3->709(800%)",
            source_gamma="S-Log3",
            hdmi_monitor_connected=True,
        )
        self.assertTrue(pp_hdmi.camera_lcd_gamma_assist_applied)
        self.assertFalse(pp_hdmi.external_hdmi_gamma_assist_applied)
        self.assertEqual(pp_hdmi.external_hdmi_signal_mode, "UNASSISTED_RAW_PP:S-Log3")

        hdmi_blk = p222.probe_gamma_display_assist_vs_display_lut_hil(
            log_shooting="Off",
            attempt_apply_gamma_assist_to_external_hdmi=True,
        )
        self.assertFalse(hdmi_blk.admitted)
        self.assertFalse(hdmi_blk.external_hdmi_gamma_assist_applied)
        self.assertEqual(hdmi_blk.log_shooting_gamma_assist_or_hdmi_leakage_events, 0)
        self.assertEqual(hdmi_blk.errno_code, p222.EOPNOTSUPP_ERRNO)

    def test_32_submodel_c_invalid_argument_validation_raises_error(self) -> None:
        with self.assertRaises(p222.RealHwPixelMapNtscPalGammaAssistDisplayLutError):
            p222.probe_gamma_display_assist_vs_display_lut_hil(log_shooting="Custom")
        with self.assertRaises(p222.RealHwPixelMapNtscPalGammaAssistDisplayLutError):
            p222.probe_gamma_display_assist_vs_display_lut_hil(source_gamma="S-Log2")
        with self.assertRaises(p222.RealHwPixelMapNtscPalGammaAssistDisplayLutError):
            p222.probe_gamma_display_assist_vs_display_lut_hil(view_context="EVF")

    def test_33_hard_safety_redline_baseline_and_all_9_forbidden_actions(self) -> None:
        base = p222.probe_hard_safety_redline()
        self.assertTrue(base.valid)
        self.assertFalse(base.persistent_emmc_writes_authorized)
        self.assertFalse(base.spi_nor_write_authorized)
        self.assertFalse(base.el3_payload_transmit_authorized)
        self.assertTrue(base.cnflasha_userspace_write_blocked)
        self.assertEqual(base.cnflasha_mutation_bytes, 0)
        self.assertEqual(base.physical_usb_packets_emitted, 0)
        self.assertEqual(base.otp_fuse_touches, 0)
        self.assertEqual(base.rpmb_counter_increments, 0)
        self.assertEqual(base.stage_b_tmp_mount_residuals_after_pixelmap_reboot, 0)
        self.assertEqual(base.ntsc_pal_cross_region_db_contamination_events, 0)
        self.assertEqual(base.log_shooting_gamma_assist_or_hdmi_leakage_events, 0)

        for flag_name in (
            "authorize_persistent_emmc_writes",
            "authorize_spi_nor_write",
            "authorize_el3_payload_transmit",
            "emit_physical_usb_packet",
            "touch_otp_fuse",
            "increment_rpmb_counter",
            "write_userspace_cnflasha_or_leave_tmp_residual",
            "contaminate_ntsc_pal_cross_region_media_db",
            "leak_gamma_assist_into_log_shooting_or_hdmi",
        ):
            bad = p222.probe_hard_safety_redline(**{flag_name: True})
            self.assertFalse(bad.valid, msg=flag_name)
            self.assertFalse(bad.persistent_emmc_writes_authorized)
            self.assertFalse(bad.spi_nor_write_authorized)
            self.assertFalse(bad.el3_payload_transmit_authorized)
            self.assertTrue(bad.cnflasha_userspace_write_blocked)
            self.assertEqual(bad.cnflasha_mutation_bytes, 0)
            self.assertEqual(bad.physical_usb_packets_emitted, 0)
            self.assertEqual(bad.otp_fuse_touches, 0)
            self.assertEqual(bad.rpmb_counter_increments, 0)
            self.assertEqual(bad.stage_b_tmp_mount_residuals_after_pixelmap_reboot, 0)
            self.assertEqual(bad.ntsc_pal_cross_region_db_contamination_events, 0)
            self.assertEqual(bad.log_shooting_gamma_assist_or_hdmi_leakage_events, 0)
            self.assertTrue(bad.status_code.startswith("FAIL_CLOSED_REDLINE_BLOCKED:"))

    def test_34_combined_multi_redline_violation_blocked(self) -> None:
        combo = p222.probe_hard_safety_redline(
            authorize_persistent_emmc_writes=True,
            write_userspace_cnflasha_or_leave_tmp_residual=True,
            contaminate_ntsc_pal_cross_region_media_db=True,
            leak_gamma_assist_into_log_shooting_or_hdmi=True,
        )
        self.assertFalse(combo.valid)
        self.assertIn("PERSISTENT_EMMC_WRITE", combo.blocked_action)
        self.assertIn("CNFLASHA_WRITE_OR_TMP_MOUNT_RESIDUAL", combo.blocked_action)
        self.assertIn("NTSC_PAL_CROSS_REGION_DB_CONTAMINATION", combo.blocked_action)
        self.assertIn("LOG_SHOOTING_OR_HDMI_GAMMA_ASSIST_LEAKAGE", combo.blocked_action)

    def test_35_pillar_c_d_evaluator_matrix_passes_100pct(self) -> None:
        pcd = p222.evaluate_pillar_c_d_gamma_assist_display_lut_and_redlines()
        self.assertTrue(pcd["passed"])
        self.assertEqual(len(pcd["gamma_disp_assist_4mode_matrix"]), 4)
        self.assertEqual(len(pcd["blocked_redline_probes"]), 9)

    def test_36_clean_room_audit_deterministic_digest_and_zero_leaks(self) -> None:
        r1 = _get_clean_room_audit()
        r2 = p222.run_phase222_realhw_pixelmap_ntscpal_gammaassist_displaylut_hil(
            force_clean_room=True
        )
        self.assertTrue(r1["all_checks_passed"])
        self.assertEqual(r1["source_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(r1["stage_index"], 40)
        self.assertEqual(r1["stage_total"], 40)
        self.assertEqual(r1["milestone"], "40/40")
        self.assertEqual(r1["audit_digest_sha256"], r2["audit_digest_sha256"])
        self.assertEqual(r1["redlines"]["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(r1["donor_audit"]["raw_firmware_bytes_leaked"], 0)

    def test_37_default_mode_audit_passes_all_pillars_and_redlines(self) -> None:
        rep = _get_default_audit()
        self.assertTrue(rep["all_checks_passed"])
        self.assertIn(rep["source_mode"], ("LOCAL_DONOR_RDONLY", "CLEAN_ROOM_SYNTHETIC"))
        self.assertTrue(rep["pillar_a_pixel_mapping_reboot_and_cnflasha_hil"]["passed"])
        self.assertTrue(rep["pillar_b_ntsc_pal_reset_persistence_hil"]["passed"])
        self.assertTrue(rep["pillar_c_d_gamma_assist_display_lut_and_redlines"]["passed"])
        self.assertTrue(rep["redlines"]["cnflasha_userspace_write_blocked"])
        self.assertEqual(rep["redlines"]["cnflasha_mutation_bytes"], 0)
        self.assertFalse(rep["redlines"]["persistent_emmc_writes_authorized"])
        self.assertFalse(rep["redlines"]["spi_nor_write_authorized"])
        self.assertFalse(rep["redlines"]["el3_payload_transmit_authorized"])
        self.assertEqual(rep["redlines"]["physical_usb_packets_emitted"], 0)
        self.assertEqual(rep["redlines"]["otp_fuse_touches"], 0)
        self.assertEqual(rep["redlines"]["rpmb_counter_increments"], 0)
        self.assertEqual(rep["redlines"]["stage_b_tmp_mount_residuals_after_pixelmap_reboot"], 0)
        self.assertEqual(rep["redlines"]["ntsc_pal_cross_region_db_contamination_events"], 0)
        self.assertEqual(rep["redlines"]["log_shooting_gamma_assist_or_hdmi_leakage_events"], 0)

    def test_38_standalone_cli_self_test_summary_and_clean_room_json(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        p_sum = subprocess.run(
            [
                sys.executable,
                "-B",
                str(
                    FX3_VM_DIR
                    / "realhw_pixelmap_ntscpal_gammaassist_displaylut_coemulator.py"
                ),
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
        self.assertIn("[PASS] Phase 222 Stage 40 (40/40)", p_sum.stdout)

        p_json = subprocess.run(
            [
                sys.executable,
                "-B",
                str(
                    FX3_VM_DIR
                    / "realhw_pixelmap_ntscpal_gammaassist_displaylut_coemulator.py"
                ),
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
        self.assertEqual(parsed["stage_index"], 40)
        self.assertEqual(parsed["milestone"], "40/40")

    def test_39_inprocess_main_summary_and_clean_room_exit_zero(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = p222.main(["--self-test", "--clean-room", "--summary"])
        self.assertEqual(rc, 0)
        self.assertIn("[PASS] Phase 222 Stage 40 (40/40)", buf.getvalue())

    def test_40_fx3_vm_coemulation_suite_includes_stage40_and_skip_phase222(self) -> None:
        rep_on, _dt = _get_clean_room_suite()
        self.assertTrue(rep_on["all_checks_passed"])
        self.assertIn(
            "stage40_realhw_pixelmap_ntscpal_gammaassist_displaylut_hil",
            rep_on,
        )
        s40 = rep_on["stage40_realhw_pixelmap_ntscpal_gammaassist_displaylut_hil"]
        self.assertTrue(s40["all_checks_passed"])
        self.assertTrue(s40["cnflasha_userspace_write_blocked"])
        self.assertEqual(s40["cnflasha_mutation_bytes"], 0)
        self.assertFalse(s40["persistent_emmc_writes_authorized"])
        self.assertFalse(s40["spi_nor_write_authorized"])
        self.assertFalse(s40["el3_payload_transmit_authorized"])
        self.assertEqual(s40["physical_usb_packets_emitted"], 0)
        self.assertEqual(s40["otp_fuse_touches"], 0)
        self.assertEqual(s40["rpmb_counter_increments"], 0)
        self.assertEqual(s40["stage_b_tmp_mount_residuals_after_pixelmap_reboot"], 0)
        self.assertEqual(s40["ntsc_pal_cross_region_db_contamination_events"], 0)
        self.assertEqual(s40["log_shooting_gamma_assist_or_hdmi_leakage_events"], 0)
        self.assertEqual(s40["raw_firmware_bytes_leaked"], 0)

        stage_keys = [k for k in rep_on if re.match(r"^stage\d+_", k)]
        self.assertGreaterEqual(len(stage_keys), 40)

        rep_skip = suite.run_fx3_vm_coemulation_suite(
            suite.CoEmulationConfig(
                force_clean_room=True,
                include_phase222_realhw_pixelmap_ntscpal_gammaassist_displaylut_hil=False,
            )
        )
        self.assertTrue(rep_skip["all_checks_passed"])
        self.assertNotIn(
            "stage40_realhw_pixelmap_ntscpal_gammaassist_displaylut_hil",
            rep_skip,
        )
        self.assertGreaterEqual(len([k for k in rep_skip if re.match(r"^stage\d+_", k)]), 39)

    def test_41_all_40_of_40_milestone_stages_present_and_passing_in_suite(self) -> None:
        rep, _dt = _get_clean_room_suite()
        self.assertTrue(rep["stage1_coldboot_and_bt"]["all_checks_passed"])
        self.assertTrue(rep["stage2_dual_isa_cp_shooting"]["all_checks_passed"])
        self.assertTrue(rep["stage3_soft_gpe_hud_ramfb"]["all_checks_passed"])
        for idx in range(4, 41):
            matches = [k for k in rep if k.startswith(f"stage{idx}_")]
            self.assertEqual(len(matches), 1, msg=f"Missing or duplicate stage{idx}_* key")
            self.assertTrue(rep[matches[0]]["all_checks_passed"], msg=matches[0])

    def test_42_suite_subprocess_summary_and_skip_phase222_flag(self) -> None:
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
        self.assertIn(
            "realhw_pixelmap_ntscpal_gammaassist_displaylut_hil=CLEAN_ROOM_SYNTHETIC",
            proc.stdout,
        )

        proc_skip = subprocess.run(
            [
                sys.executable,
                "-B",
                str(FX3_VM_DIR / "fx3_vm_coemulation_suite.py"),
                "--clean-room",
                "--skip-phase222",
                "--summary",
            ],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc_skip.returncode, 0, msg=proc_skip.stderr)
        self.assertNotIn(
            "realhw_pixelmap_ntscpal_gammaassist_displaylut_hil=",
            proc_skip.stdout,
        )

    def test_43_suite_40_stages_under_wall_clock_ceiling_and_json_cli(self) -> None:
        rep_clean, dt_clean = _get_clean_room_suite()
        self.assertTrue(rep_clean["all_checks_passed"])
        self.assertGreaterEqual(len([k for k in rep_clean if re.match(r"^stage\d+_", k)]), 40)
        self.assertLess(dt_clean, 6.0)

        rep_def, dt_def = _get_default_suite()
        self.assertTrue(rep_def["all_checks_passed"])
        self.assertGreaterEqual(len([k for k in rep_def if re.match(r"^stage\d+_", k)]), 40)
        self.assertLess(dt_def, 6.0)

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc_json = suite.main(["--clean-room", "--json"])
        self.assertEqual(rc_json, 0)
        parsed = json.loads(buf.getvalue())
        self.assertTrue(parsed["all_checks_passed"])
        self.assertIn(
            "stage40_realhw_pixelmap_ntscpal_gammaassist_displaylut_hil",
            parsed,
        )

    def test_44_source_hygiene_rdonly_only_and_no_forbidden_write_flags_or_ports(self) -> None:
        src = (
            FX3_VM_DIR / "realhw_pixelmap_ntscpal_gammaassist_displaylut_coemulator.py"
        ).read_text(encoding="utf-8")
        self.assertIn("os.O_RDONLY", src)
        self.assertNotIn("O_WR" + "ONLY", src)
        self.assertNotIn("O_RD" + "WR", src)
        self.assertNotIn("87" + "68", src)

    def test_45_is_forced_clean_room_truthy_and_falsy_values(self) -> None:
        for truthy in ("1", "true", "TRUE", "yes", "on", " 1 "):
            self.assertTrue(
                p222.is_forced_clean_room({"FX3_FX6_FORCE_CLEAN_ROOM": truthy}),
                msg=truthy,
            )
        for falsy in ("", "0", "false", "no", "off"):
            self.assertFalse(
                p222.is_forced_clean_room({"FX3_FX6_FORCE_CLEAN_ROOM": falsy}),
                msg=falsy,
            )

    def test_46_missing_work_root_gracefully_falls_back_to_clean_room_synthetic(self) -> None:
        non_existent = str(REPO_ROOT / "work" / "__nonexistent_phase222_donor_root__")
        env_missing = {
            "FX3_FX6_FORCE_CLEAN_ROOM": "0",
            "FX3_FX6_MAC_WORK_ROOT": non_existent,
            "FX3_FX6_MAC_ROOT": non_existent,
            "FX3_FX6_MAIN_LAB_WORK_ROOT": non_existent,
        }
        paths = p222.resolve_phase222_donor_paths(env=env_missing)
        self.assertEqual(len(paths), 12)
        da = p222.inspect_phase222_donors(force_clean_room=True, env=env_missing)
        self.assertEqual(da.source_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_47_hdmi_disconnected_signal_modes_for_log_and_picture_profile(self) -> None:
        log_no_hdmi = p222.probe_gamma_display_assist_vs_display_lut_hil(
            log_shooting="Cine EI",
            hdmi_monitor_connected=False,
        )
        self.assertEqual(log_no_hdmi.external_hdmi_signal_mode, "HDMI_DISCONNECTED")
        self.assertFalse(log_no_hdmi.external_hdmi_gamma_assist_applied)

        pp_no_hdmi = p222.probe_gamma_display_assist_vs_display_lut_hil(
            log_shooting="Off",
            hdmi_monitor_connected=False,
        )
        self.assertEqual(pp_no_hdmi.external_hdmi_signal_mode, "HDMI_DISCONNECTED")
        self.assertFalse(pp_no_hdmi.external_hdmi_gamma_assist_applied)

    def test_48_run_stage40_runner_directly_matches_phase222_digest(self) -> None:
        cfg = suite.CoEmulationConfig(force_clean_room=True)
        s40 = suite.run_stage40_realhw_pixelmap_ntscpal_gammaassist_displaylut_hil(cfg)
        rep = _get_clean_room_audit()
        self.assertEqual(
            s40["stage"], "stage40_realhw_pixelmap_ntscpal_gammaassist_displaylut_hil"
        )
        self.assertTrue(s40["all_checks_passed"])
        self.assertEqual(s40["phase222_audit_digest_sha256"], rep["audit_digest_sha256"])


if __name__ == "__main__":
    unittest.main()
