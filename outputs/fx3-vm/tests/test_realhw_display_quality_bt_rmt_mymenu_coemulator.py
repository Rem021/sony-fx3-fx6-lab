#!/usr/bin/env python3
"""Unit tests for Phase 257 Stage 49 (`49/49` Milestone):
Real-Hardware `ILME-FX3` (`0x91030080`, `ilc/2210`, `Ver. 2.00..7.02`) Wave-39
`[Display Quality]` (`Standard`/`High`) Battery Conservation Bench Guard & Setup
Persistence, `[Bluetooth Rmt Ctrl]` (`Off`/`On`) Infrared `SIRCS` Lockout & 3-Way
`[Reset Network Set.]` Split, and `[My Menu Setting]` / `[Display From My Menu]`
6-Operation Persistence & Slot-1 `CAMSET01.DAT` `O_RDONLY` Vault Round-Trip HIL
Co-Emulator.
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
import unittest.mock

FX3_VM_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = FX3_VM_DIR.parents[1]
if str(FX3_VM_DIR) not in sys.path:
    sys.path.insert(0, str(FX3_VM_DIR))

import fx3_vm_coemulation_suite as suite  # noqa: E402
import realhw_display_quality_bt_rmt_mymenu_coemulator as p257  # noqa: E402


def _fast_suite_kwargs(**overrides: object) -> dict:
    """Fast config skipping heavy unrelated imaging/fault Unicorn loops for <50ms flag tests."""
    base = dict(
        force_clean_room=True,
        include_phase41_dtb_mhlx=False,
        include_phase45_imx510_xavc=False,
        include_phase53_hil_fault_harness=False,
        include_phase58_qmp_introspection=False,
        include_phase63_hdmi_raw_uvc=False,
        include_phase67_tc_lens_paint=False,
        include_phase71_dualslot_ups_salvage=False,
        include_phase78_touchaf_ciz_assignable=False,
        include_phase82_camset_lpcm_tcub=False,
        include_phase87_playback_shotmark_dewpoint=False,
        include_phase91_gyroflow_rtmd_anamorphic=False,
        include_phase96_interval_cache_ftp_fan=False,
        include_phase99_lut3d_subzero_sdi=False,
        include_phase103_emi_exfat_endurance=False,
        include_phase107_c2pa_shading_mcfleet_ovp=False,
        include_phase112_hdr_hlg_fiz_gimbal=False,
        include_phase117_proresraw_breathing_mishoe_hil=False,
        include_phase121_uvc_srt_crsdk_usbpd_hil=False,
        include_phase127_mxf_ptpv2_tally_monsoon_hil=False,
        include_phase132_vp_ledwall_freed_artnet_hil=False,
        include_phase141_realhw_preflash_dualboot_hil=False,
        include_phase145_realhw_mpr_dmm_rec=False,
        include_phase150_realhw_body_peripheral_hil=False,
        include_phase157_realhw_imx510_network_usb_hil=False,
        include_phase162_realhw_cfexpress_ufu_5tier_hil=False,
        include_phase167_realhw_cxd90058_sabin_seal_hil=False,
        include_phase172_realhw_c2pa_tc_gyro_prebench_hil=False,
        include_phase178_realhw_ssboot_wbi2_powerloss_slot1_ufu_hil=False,
        include_phase182_realhw_emount_info3d_breathing_hdmi_4264_raw_hil=False,
        include_phase188_realhw_fx3a_firewall_and_xlrh1_4ch_mishoe_hil=False,
        include_phase194_realhw_nouvc_dcc1_lut_path_cineei_hil=False,
        include_phase200_realhw_fan_pwm_shutter_angle_lut_split_hil=False,
        include_phase202_realhw_big6_noend_camset_slot1_vmcbncm1_hil=False,
        include_stage44=False,
        include_stage45=False,
        include_stage46=False,
        include_stage47=False,
        include_stage48=False,
    )
    base.update(overrides)
    return base


class TestPhase257DisplayQualityBtRmtMyMenuCoEmulator(unittest.TestCase):
    clean_audit: dict = {}
    default_audit: dict = {}
    clean_suite: dict = {}
    clean_suite_elapsed: float = 0.0
    default_suite: dict = {}
    default_suite_elapsed: float = 0.0

    @classmethod
    def setUpClass(cls) -> None:
        cls.clean_audit = p257.run_phase257_realhw_display_quality_bt_rmt_mymenu_hil(
            force_clean_room=True
        )
        cls.default_audit = p257.run_phase257_realhw_display_quality_bt_rmt_mymenu_hil()

        t0 = time.monotonic()
        cls.clean_suite = suite.run_fx3_vm_coemulation_suite(
            suite.CoEmulationConfig(force_clean_room=True)
        )
        cls.clean_suite_elapsed = time.monotonic() - t0

        if p257.is_forced_clean_room():
            cls.default_suite = cls.clean_suite
            cls.default_suite_elapsed = cls.clean_suite_elapsed
        else:
            t1 = time.monotonic()
            cls.default_suite = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig())
            cls.default_suite_elapsed = time.monotonic() - t1

    # ------------------------------------------------------------------
    # Group 1: Schema, Phase 257 Stage 49 (49/49) & O_RDONLY Donors (12)
    # ------------------------------------------------------------------
    def test_01_schema_version_phase257_stage49_milestone_and_redline_constants(self) -> None:
        self.assertEqual(
            p257.SCHEMA_ID,
            "realhw_display_quality_bt_rmt_mymenu_coemulator_v1",
        )
        self.assertEqual(p257.PHASE_257_SCHEMA, p257.SCHEMA_ID)
        self.assertEqual(p257.PHASE_257_VERSION, "257.0.0")
        self.assertEqual(p257.PHASE_NUMBER, 257)
        self.assertEqual(p257.STAGE_INDEX, 49)
        self.assertEqual(p257.STAGE_TOTAL, 49)
        self.assertEqual(p257.MILESTONE_LABEL, "49/49")
        self.assertEqual(
            p257.STAGE_NAME,
            "stage49_realhw_display_quality_bt_rmt_mymenu_hil",
        )
        self.assertEqual(p257.FX3_MODEL_ID, 0x91030080)
        self.assertEqual(p257.FX6_MODEL_ID, 0x91020080)
        self.assertEqual(p257.FX3_HELP_GUIDE_ID, "ilc/2210")
        self.assertTrue(p257.P8_CP_MUTATION_FORBIDDEN)
        self.assertTrue(p257.CNFLASHA_USERSPACE_WRITE_BLOCKED)
        self.assertEqual(p257.NOP_COUNT, 0)
        self.assertEqual(p257.GUEST_CODE_MODIFICATION_BYTES, 0)
        self.assertEqual(p257.PHYSICAL_DEVICE_WRITES, 0)
        self.assertEqual(p257.RAW_FIRMWARE_BYTES_LEAKED, 0)
        self.assertEqual(p257.TIER0_BATTERY_HIGH_DISPLAY_VIOLATIONS, 0)
        self.assertEqual(p257.PASSIVE_TX_BYTES_EMITTED, 0)
        self.assertEqual(p257.BT_RMT_IR_LOCKOUT_VIOLATIONS, 0)
        self.assertEqual(p257.SLOT1_MYMENU_VAULT_MUTATION_BYTES, 0)
        self.assertFalse(p257.PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(p257.HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        self.assertFalse(p257.OVERALL_READY_FOR_HARDWARE_ATTACH)
        self.assertFalse(p257.ISP_WRITE_AUTHORIZED)
        self.assertFalse(p257.SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(p257.EL3_PAYLOAD_TRANSMIT_AUTHORIZED)

    def test_02_clean_room_donor_audit_15_artifacts_zero_leaked_bytes(self) -> None:
        self.assertTrue(self.clean_audit["all_checks_passed"])
        self.assertEqual(self.clean_audit["source_mode"], "CLEAN_ROOM_SYNTHETIC")
        da = self.clean_audit["donor_audit"]
        self.assertTrue(da["all_contracts_verified"])
        self.assertEqual(da["donor_files_inspected"], 0)
        self.assertEqual(da["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(da["access_mode"], "O_RDONLY")
        self.assertTrue(da["display_quality_and_monitor_proven"])
        self.assertTrue(da["bluetooth_rmt_and_sircs_proven"])
        self.assertTrue(da["mymenu_and_camset_proven"])
        self.assertEqual(len(p257.DONOR_RELPATHS), 15)

    def test_03_default_mode_donor_audit_valid_and_sub_100ms(self) -> None:
        self.assertTrue(self.default_audit["all_checks_passed"])
        da = self.default_audit["donor_audit"]
        self.assertIn(da["source_mode"], ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"))
        self.assertTrue(da["all_contracts_verified"])
        self.assertEqual(da["raw_firmware_bytes_leaked"], 0)
        self.assertLess(da["inspection_elapsed_s"], 0.75 if __import__("os").environ.get("GITHUB_ACTIONS") == "true" else 0.15)
        if da["source_mode"] == "LOCAL_DONOR_O_RDONLY":
            self.assertEqual(da["donor_files_inspected"], 15)

    def test_04_env_force_clean_room_toggle_matrix(self) -> None:
        for truthy in ("1", "true", "TRUE", "yes", "on", " 1 "):
            self.assertTrue(p257.is_forced_clean_room({"FX3_FX6_FORCE_CLEAN_ROOM": truthy}))
        for falsy in ("", "0", "false", "no", "off"):
            self.assertFalse(p257.is_forced_clean_room({"FX3_FX6_FORCE_CLEAN_ROOM": falsy}))

    def test_05_resolve_phase257_donor_paths_clean_room_sentinel_isolation(self) -> None:
        resolved = p257.resolve_phase257_donor_paths(env={"FX3_FX6_FORCE_CLEAN_ROOM": "1"})
        self.assertEqual(len(resolved), 15)
        for p in resolved.values():
            self.assertIn(p257.CLEAN_ROOM_SENTINEL_DIRNAME, str(p))
            self.assertFalse(p.exists())

    def test_06_missing_donor_directory_falls_back_to_clean_room_synthetic(self) -> None:
        with unittest.mock.patch.object(
            p257,
            "resolve_phase257_donor_paths",
            return_value={
                k: REPO_ROOT / "work" / "__nonexistent_wave39__" / rel
                for k, rel in p257.DONOR_RELPATHS.items()
            },
        ):
            audit = p257.inspect_phase257_donors(force_clean_room=False, env={})
        self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(audit.all_contracts_verified)

    def test_07_fx3_string_en_f_proves_all_wave39_display_bt_rmt_mymenu_tokens(self) -> None:
        for rep in (self.clean_audit, self.default_audit):
            hits = rep["donor_audit"]["fx3_string_en_f"]["marker_hits"]
            for tok in (
                "Display Quality",
                "Standard",
                "High",
                "Monitor",
                "Brightness",
                "Manual",
                "Battery",
                "Bluetooth Rmt Ctrl",
                "Bluetooth Function",
                "Airplane Mode",
                "IR Remote",
                "My Menu",
                "Display From My Menu",
                "Add Item",
                "Sort Item",
                "Delete Item",
                "Delete Page",
                "Delete All",
                "Save/Load Settings",
                "Camera Settings Reset",
                "Reset Network Set.",
                "Initialize",
            ):
                self.assertEqual(hits[tok], 1, msg=tok)

    def test_08_fx6_string_en_and_absent_non_fx3_tokens_verified(self) -> None:
        for rep in (self.clean_audit, self.default_audit):
            fx3_abs = rep["donor_audit"]["fx3_string_en_f"]["absent_marker_hits"]
            self.assertEqual(fx3_abs["Autoframing Settings"], 0)
            self.assertEqual(fx3_abs["ECS"], 0)
            fx6_hits = rep["donor_audit"]["fx6_string_en"]["marker_hits"]
            for tok in ("Display", "Monitor", "Bluetooth", "Remote", "Menu", "Save", "Load", "Reset"):
                self.assertEqual(fx6_hits[tok], 1)

    def test_09_bounded_4kib_windows_prove_sircs_mymenu_camset_bluetooth_and_display(self) -> None:
        for rep in (self.clean_audit, self.default_audit):
            da = rep["donor_audit"]
            for key in ("fx3_appfw", "fx6_appfw", "fx3_cpapp", "fx6_cpapp", "fx3_libmpr", "fx6_libmpr", "fx3_bk4", "fx6_bk4"):
                self.assertTrue(da[key]["bounded_windows_only"])
                self.assertLessEqual(da[key]["bytes_read_total"], 12 * p257.BOUNDED_WINDOW_MAX_BYTES)
            for lbl in ("DISPLAY", "MONITOR", "BLUETOOTH", "CAMSET", "SIRCS", "MYMENU"):
                self.assertEqual(da["fx3_appfw"]["window_hits"][lbl], 1)
                self.assertEqual(da["fx6_appfw"]["window_hits"][lbl], 1)
            self.assertEqual(da["fx3_cpapp"]["window_hits"]["SIRCS"], 1)
            self.assertEqual(da["fx6_cpapp"]["window_hits"]["SIRCS"], 1)

    def test_10_local_donor_audit_uses_strictly_o_rdonly_flags(self) -> None:
        if p257.is_forced_clean_room():
            audit = p257.inspect_phase257_donors(force_clean_room=True)
            self.assertEqual(audit.access_mode, "O_RDONLY")
            return
        real_open = os.open
        seen_flags = []

        def _spy_open(path: str, flags: int, *args: object) -> int:
            seen_flags.append(flags)
            return real_open(path, flags, *args)

        p257._DONOR_AUDIT_CACHE.clear()
        with unittest.mock.patch("os.open", side_effect=_spy_open):
            audit = p257.inspect_phase257_donors(force_clean_room=False)
        if audit.source_mode == "LOCAL_DONOR_O_RDONLY":
            self.assertEqual(len(seen_flags), 15)
            for fl in seen_flags:
                self.assertEqual(fl, os.O_RDONLY)

    def test_11_audit_digest_sha256_deterministic_across_repeated_runs(self) -> None:
        r2 = p257.run_phase257_realhw_display_quality_bt_rmt_mymenu_hil(force_clean_room=True)
        self.assertEqual(self.clean_audit["audit_digest_sha256"], r2["audit_digest_sha256"])

    def test_12_donor_cache_returns_singleton_on_repeat_inspection(self) -> None:
        a1 = p257.inspect_phase257_donors(force_clean_room=True)
        a2 = p257.inspect_phase257_donors(force_clean_room=True)
        self.assertIs(a1, a2)

    # ------------------------------------------------------------------
    # Group 2: Sub-Model 49A — Display Quality Standard/High Bench Guard (12)
    # ------------------------------------------------------------------
    def test_13_display_quality_default_standard_and_manual_0_power_baseline(self) -> None:
        res = p257.coemulate_display_quality_bench_guard()
        self.assertTrue(res.admitted)
        self.assertEqual(res.effective_display_quality, "Standard")
        self.assertEqual(res.effective_monitor_brightness_mode, "Manual")
        self.assertEqual(res.effective_manual_brightness_step, 0)
        self.assertFalse(res.np_fz100_accelerated_drain)
        self.assertEqual(res.estimated_live_view_watts, 3.20)
        self.assertEqual(res.tier0_battery_high_display_violations, 0)

    def test_14_display_quality_high_accelerates_np_fz100_battery_consumption(self) -> None:
        r_std = p257.coemulate_display_quality_bench_guard(
            configured_display_quality="Standard",
            power_source="NP-FZ100",
        )
        r_high = p257.coemulate_display_quality_bench_guard(
            configured_display_quality="High",
            power_source="NP-FZ100",
        )
        self.assertTrue(r_high.admitted)
        self.assertTrue(r_high.np_fz100_accelerated_drain)
        self.assertGreater(r_high.estimated_live_view_watts, r_std.estimated_live_view_watts)
        self.assertLess(r_high.estimated_np_fz100_runtime_min, r_std.estimated_np_fz100_runtime_min)

    def test_15_display_quality_high_on_external_usb_pd_does_not_flag_battery_drain(self) -> None:
        res = p257.coemulate_display_quality_bench_guard(
            configured_display_quality="High",
            power_source="USB-PD 9V/3A",
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.effective_display_quality, "High")
        self.assertFalse(res.np_fz100_accelerated_drain)

    def test_16_display_quality_survives_camera_settings_reset(self) -> None:
        res = p257.coemulate_display_quality_bench_guard(
            configured_display_quality="High",
            reset_action="Camera Settings Reset",
        )
        self.assertTrue(res.survived_camera_settings_reset)
        self.assertFalse(res.restored_by_initialize)
        self.assertEqual(res.effective_display_quality_register, "High")
        self.assertEqual(res.effective_display_quality, "High")

    def test_17_display_quality_survives_reset_network_set(self) -> None:
        res = p257.coemulate_display_quality_bench_guard(
            configured_display_quality="High",
            reset_action="Reset Network Set.",
        )
        self.assertTrue(res.survived_reset_network_set)
        self.assertFalse(res.restored_by_initialize)
        self.assertEqual(res.effective_display_quality_register, "High")
        self.assertEqual(res.effective_display_quality, "High")

    def test_18_display_quality_restored_to_standard_only_by_initialize(self) -> None:
        res = p257.coemulate_display_quality_bench_guard(
            configured_display_quality="High",
            configured_monitor_brightness_mode="Sunny Weather",
            reset_action="Initialize",
        )
        self.assertTrue(res.restored_by_initialize)
        self.assertEqual(res.effective_display_quality_register, "Standard")
        self.assertEqual(res.effective_display_quality, "Standard")
        self.assertEqual(res.effective_monitor_brightness_mode, "Manual")
        self.assertEqual(res.effective_manual_brightness_step, 0)

    def test_19_monitor_brightness_manual_steps_and_sunny_weather_power_scaling(self) -> None:
        r_m2 = p257.coemulate_display_quality_bench_guard(configured_manual_brightness_step=-2)
        r_p2 = p257.coemulate_display_quality_bench_guard(configured_manual_brightness_step=2)
        r_sw = p257.coemulate_display_quality_bench_guard(
            configured_monitor_brightness_mode="Sunny Weather"
        )
        self.assertLess(r_m2.estimated_live_view_watts, r_p2.estimated_live_view_watts)
        self.assertLess(r_p2.estimated_live_view_watts, r_sw.estimated_live_view_watts)

    def test_20_tier0_battery_dump_auto_clamps_high_and_sunny_weather_to_standard_manual0(self) -> None:
        res = p257.coemulate_display_quality_bench_guard(
            configured_display_quality="High",
            configured_monitor_brightness_mode="Sunny Weather",
            configured_manual_brightness_step=2,
            power_source="NP-FZ100",
            bench_operation="TIER0_PNFLASHA_CNFLASHA_DUMP",
            auto_clamp_tier0_battery=True,
        )
        self.assertTrue(res.admitted)
        self.assertTrue(res.tier0_bench_clamped_to_standard_manual0)
        self.assertEqual(res.effective_display_quality, "Standard")
        self.assertEqual(res.effective_monitor_brightness_mode, "Manual")
        self.assertEqual(res.effective_manual_brightness_step, 0)
        self.assertFalse(res.np_fz100_accelerated_drain)
        self.assertEqual(res.tier0_battery_high_display_violations, 0)

    def test_21_tier0_battery_dump_already_standard_manual0_admitted_without_clamp(self) -> None:
        res = p257.coemulate_display_quality_bench_guard(
            configured_display_quality="Standard",
            configured_monitor_brightness_mode="Manual",
            configured_manual_brightness_step=0,
            power_source="NP-FZ100",
            bench_operation="TIER0_PNFLASHA_CNFLASHA_DUMP",
            auto_clamp_tier0_battery=False,
        )
        self.assertTrue(res.admitted)
        self.assertFalse(res.tier0_bench_clamped_to_standard_manual0)
        self.assertEqual(res.reason_code, "TIER0_BATTERY_ALREADY_STANDARD_MANUAL0")

    def test_22_tier0_battery_dump_unclamped_high_or_brightness_blocked_eacces(self) -> None:
        r_high = p257.coemulate_display_quality_bench_guard(
            configured_display_quality="High",
            power_source="NP-FZ100",
            bench_operation="TIER0_PNFLASHA_CNFLASHA_DUMP",
            auto_clamp_tier0_battery=False,
        )
        self.assertFalse(r_high.admitted)
        self.assertEqual(r_high.errno_code, p257.EACCES_ERRNO)
        self.assertEqual(r_high.effective_display_quality, "Standard")
        self.assertEqual(r_high.tier0_battery_high_display_violations, 0)

        r_step = p257.coemulate_display_quality_bench_guard(
            configured_display_quality="Standard",
            configured_manual_brightness_step=1,
            power_source="NP-FZ100",
            bench_operation="TIER0_PNFLASHA_CNFLASHA_DUMP",
            auto_clamp_tier0_battery=False,
        )
        self.assertFalse(r_step.admitted)
        self.assertEqual(r_step.errno_code, p257.EACCES_ERRNO)

    def test_23_tier0_forced_unclamped_high_display_bypass_blocked_zero_violations(self) -> None:
        for pwr in ("NP-FZ100", "USB-PD 9V/3A"):
            res = p257.coemulate_display_quality_bench_guard(
                configured_display_quality="High",
                power_source=pwr,
                bench_operation="TIER0_PNFLASHA_CNFLASHA_DUMP",
                force_unclamped_tier0_high_display=True,
            )
            self.assertFalse(res.admitted)
            self.assertEqual(res.errno_code, p257.EACCES_ERRNO)
            self.assertEqual(res.tier0_battery_high_display_violations, 0)

    def test_24_pillar_a_evaluator_and_input_validation_guards(self) -> None:
        pa = p257.evaluate_pillar_a_display_quality_bench_guard_hil()
        self.assertTrue(pa["passed"])
        self.assertEqual(pa["all_2_display_quality_modes"], ["Standard", "High"])
        with self.assertRaises(ValueError):
            p257.coemulate_display_quality_bench_guard(configured_display_quality="Ultra")
        with self.assertRaises(ValueError):
            p257.coemulate_display_quality_bench_guard(configured_monitor_brightness_mode="Auto")
        with self.assertRaises(ValueError):
            p257.coemulate_display_quality_bench_guard(configured_manual_brightness_step=5)
        with self.assertRaises(ValueError):
            p257.coemulate_display_quality_bench_guard(power_source="AA-Battery")
        with self.assertRaises(ValueError):
            p257.coemulate_display_quality_bench_guard(bench_operation="FLASH_WRITE")
        with self.assertRaises(ValueError):
            p257.coemulate_display_quality_bench_guard(reset_action="HardWipe")

    # ------------------------------------------------------------------
    # Group 3: Sub-Model 49B — Bluetooth Rmt Ctrl IR SIRCS & 3-Way Reset (14)
    # ------------------------------------------------------------------
    def test_25_bluetooth_rmt_ctrl_default_off_and_zero_rf_bench_airplane_on(self) -> None:
        res = p257.coemulate_bluetooth_rmt_ctrl_and_ir_lockout()
        self.assertTrue(res.admitted)
        self.assertEqual(res.effective_bt_rmt_ctrl_register, "Off")
        self.assertEqual(res.effective_bluetooth_function_register, "Off")
        self.assertEqual(res.effective_airplane_mode_register, "On")
        self.assertFalse(res.bt_rmt_ctrl_active)
        self.assertFalse(res.ir_sircs_locked_out)
        self.assertEqual(res.passive_tx_bytes_emitted, 0)
        self.assertEqual(res.bt_rmt_ir_lockout_violations, 0)

    def test_26_zero_rf_bench_enforced_suppresses_bt_rmt_ctrl_zero_tx_bytes(self) -> None:
        res = p257.coemulate_bluetooth_rmt_ctrl_and_ir_lockout(
            configured_bt_rmt_ctrl="On",
            configured_bluetooth_function="On",
            configured_airplane_mode="Off",
            bench_zero_rf_enforced=True,
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.effective_airplane_mode_register, "On")
        self.assertTrue(res.suppressed_by_zero_rf_or_bt_off)
        self.assertFalse(res.bt_rmt_ctrl_active)
        self.assertEqual(res.passive_tx_bytes_emitted, 0)

    def test_27_bt_rmt_ctrl_requires_bluetooth_function_on_prerequisite(self) -> None:
        res = p257.coemulate_bluetooth_rmt_ctrl_and_ir_lockout(
            configured_bt_rmt_ctrl="On",
            configured_bluetooth_function="Off",
            configured_airplane_mode="Off",
        )
        self.assertTrue(res.admitted)
        self.assertFalse(res.radio_prerequisites_met)
        self.assertTrue(res.suppressed_by_zero_rf_or_bt_off)
        self.assertFalse(res.bt_rmt_ctrl_active)

    def test_28_bt_rmt_ctrl_requires_airplane_mode_off_prerequisite(self) -> None:
        res = p257.coemulate_bluetooth_rmt_ctrl_and_ir_lockout(
            configured_bt_rmt_ctrl="On",
            configured_bluetooth_function="On",
            configured_airplane_mode="On",
        )
        self.assertTrue(res.admitted)
        self.assertFalse(res.radio_prerequisites_met)
        self.assertTrue(res.suppressed_by_zero_rf_or_bt_off)
        self.assertFalse(res.bt_rmt_ctrl_active)

    def test_29_forced_radio_prerequisite_bypass_blocked_with_eopnotsupp(self) -> None:
        for bt_fn, air in (("Off", "Off"), ("On", "On"), ("Off", "On")):
            res = p257.coemulate_bluetooth_rmt_ctrl_and_ir_lockout(
                configured_bt_rmt_ctrl="On",
                configured_bluetooth_function=bt_fn,
                configured_airplane_mode=air,
                force_bypass_radio_prerequisites=True,
            )
            self.assertFalse(res.admitted)
            self.assertEqual(res.errno_code, p257.EOPNOTSUPP_ERRNO)
            self.assertFalse(res.bt_rmt_ctrl_active)
            self.assertEqual(res.passive_tx_bytes_emitted, 0)

    def test_30_forced_bench_rf_tx_blocked_with_eacces_zero_passive_tx_bytes(self) -> None:
        res = p257.coemulate_bluetooth_rmt_ctrl_and_ir_lockout(
            configured_bt_rmt_ctrl="On",
            configured_bluetooth_function="On",
            configured_airplane_mode="Off",
            bench_zero_rf_enforced=True,
            force_bench_rf_tx=True,
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p257.EACCES_ERRNO)
        self.assertEqual(res.passive_tx_bytes_emitted, 0)

    def test_31_bt_rmt_ctrl_on_with_prerequisites_active_locks_out_all_ir_sircs_commands(self) -> None:
        for cmd in ("SHUTTER_IMMEDIATE", "SHUTTER_2S", "REC_START_STOP"):
            res = p257.coemulate_bluetooth_rmt_ctrl_and_ir_lockout(
                configured_bt_rmt_ctrl="On",
                configured_bluetooth_function="On",
                configured_airplane_mode="Off",
                configured_ir_remote_ctrl="On",
                ir_sircs_command=cmd,
            )
            self.assertTrue(res.admitted)
            self.assertTrue(res.bt_rmt_ctrl_active)
            self.assertTrue(res.ir_sircs_locked_out)
            self.assertFalse(res.ir_sircs_command_accepted)
            self.assertEqual(res.bt_rmt_ir_lockout_violations, 0)

    def test_32_bt_rmt_ctrl_on_even_when_suppressed_still_locks_out_ir_sircs_register(self) -> None:
        res = p257.coemulate_bluetooth_rmt_ctrl_and_ir_lockout(
            configured_bt_rmt_ctrl="On",
            configured_bluetooth_function="Off",
            configured_airplane_mode="On",
            configured_ir_remote_ctrl="On",
            ir_sircs_command="SHUTTER_2S",
        )
        self.assertTrue(res.admitted)
        self.assertTrue(res.ir_sircs_locked_out)
        self.assertFalse(res.ir_sircs_command_accepted)

    def test_33_forced_ir_sircs_while_bt_rmt_ctrl_on_blocked_with_ebusy_zero_violations(self) -> None:
        res = p257.coemulate_bluetooth_rmt_ctrl_and_ir_lockout(
            configured_bt_rmt_ctrl="On",
            configured_bluetooth_function="On",
            configured_airplane_mode="Off",
            configured_ir_remote_ctrl="On",
            ir_sircs_command="REC_START_STOP",
            force_ir_sircs_while_bt_rmt_on=True,
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p257.EBUSY_ERRNO)
        self.assertFalse(res.ir_sircs_command_accepted)
        self.assertEqual(res.bt_rmt_ir_lockout_violations, 0)

    def test_34_bt_rmt_ctrl_off_allows_ir_sircs_commands_when_ir_remote_on(self) -> None:
        r_on = p257.coemulate_bluetooth_rmt_ctrl_and_ir_lockout(
            configured_bt_rmt_ctrl="Off",
            configured_ir_remote_ctrl="On",
            ir_sircs_command="REC_START_STOP",
        )
        self.assertTrue(r_on.admitted)
        self.assertFalse(r_on.ir_sircs_locked_out)
        self.assertTrue(r_on.ir_sircs_command_accepted)

        r_off = p257.coemulate_bluetooth_rmt_ctrl_and_ir_lockout(
            configured_bt_rmt_ctrl="Off",
            configured_ir_remote_ctrl="Off",
            ir_sircs_command="REC_START_STOP",
        )
        self.assertFalse(r_off.ir_sircs_command_accepted)

    def test_35_three_way_reset_split_camera_settings_reset_preserves_bt_rmt_ctrl(self) -> None:
        res = p257.coemulate_bluetooth_rmt_ctrl_and_ir_lockout(
            configured_bt_rmt_ctrl="On",
            configured_bluetooth_function="On",
            configured_airplane_mode="Off",
            configured_ir_remote_ctrl="On",
            ir_sircs_command="SHUTTER_IMMEDIATE",
            reset_action="Camera Settings Reset",
        )
        self.assertTrue(res.survived_camera_settings_reset)
        self.assertEqual(res.effective_bt_rmt_ctrl_register, "On")
        self.assertEqual(res.effective_bluetooth_function_register, "On")
        self.assertTrue(res.ir_sircs_locked_out)
        self.assertFalse(res.ir_sircs_command_accepted)

    def test_36_three_way_reset_split_reset_network_set_clears_bt_rmt_and_unlocks_ir(self) -> None:
        res = p257.coemulate_bluetooth_rmt_ctrl_and_ir_lockout(
            configured_bt_rmt_ctrl="On",
            configured_bluetooth_function="On",
            configured_airplane_mode="Off",
            configured_ir_remote_ctrl="On",
            ir_sircs_command="SHUTTER_IMMEDIATE",
            reset_action="Reset Network Set.",
        )
        self.assertTrue(res.reset_by_network_reset)
        self.assertEqual(res.effective_bt_rmt_ctrl_register, "Off")
        self.assertEqual(res.effective_bluetooth_function_register, "Off")
        self.assertTrue(res.ir_remote_survived_network_reset)
        self.assertEqual(res.effective_ir_remote_ctrl_register, "On")
        self.assertFalse(res.ir_sircs_locked_out)
        self.assertTrue(res.ir_sircs_command_accepted)

    def test_37_three_way_reset_split_initialize_resets_both_bt_rmt_and_ir_remote(self) -> None:
        res = p257.coemulate_bluetooth_rmt_ctrl_and_ir_lockout(
            configured_bt_rmt_ctrl="On",
            configured_bluetooth_function="On",
            configured_airplane_mode="Off",
            configured_ir_remote_ctrl="On",
            ir_sircs_command="SHUTTER_IMMEDIATE",
            reset_action="Initialize",
        )
        self.assertTrue(res.reset_by_initialize)
        self.assertEqual(res.effective_bt_rmt_ctrl_register, "Off")
        self.assertEqual(res.effective_bluetooth_function_register, "Off")
        self.assertEqual(res.effective_ir_remote_ctrl_register, "Off")
        self.assertFalse(res.ir_sircs_command_accepted)

    def test_38_pillar_b_evaluator_and_enum_validation_guards(self) -> None:
        pb = p257.evaluate_pillar_b_bluetooth_rmt_ctrl_ir_lockout_hil()
        self.assertTrue(pb["passed"])
        with self.assertRaises(ValueError):
            p257.coemulate_bluetooth_rmt_ctrl_and_ir_lockout(configured_bt_rmt_ctrl="Auto")
        with self.assertRaises(ValueError):
            p257.coemulate_bluetooth_rmt_ctrl_and_ir_lockout(configured_bluetooth_function="Pair")
        with self.assertRaises(ValueError):
            p257.coemulate_bluetooth_rmt_ctrl_and_ir_lockout(configured_airplane_mode="Half")
        with self.assertRaises(ValueError):
            p257.coemulate_bluetooth_rmt_ctrl_and_ir_lockout(configured_ir_remote_ctrl="Auto")
        with self.assertRaises(ValueError):
            p257.coemulate_bluetooth_rmt_ctrl_and_ir_lockout(ir_sircs_command="ZOOM_TELE")
        with self.assertRaises(ValueError):
            p257.coemulate_bluetooth_rmt_ctrl_and_ir_lockout(reset_action="UnknownReset")

    # ------------------------------------------------------------------
    # Group 4: Sub-Model 49C — My Menu 6-Op, CAMSET01.DAT & Redlines (17)
    # ------------------------------------------------------------------
    def test_39_my_menu_default_empty_and_display_from_my_menu_off_landing_tab(self) -> None:
        res = p257.coemulate_my_menu_and_camset_vault(last_visited_tab="Exposure/Color")
        self.assertTrue(res.admitted)
        self.assertEqual(res.active_page_count, 0)
        self.assertEqual(res.total_registered_items, 0)
        self.assertEqual(res.effective_display_from_my_menu, "Off")
        self.assertEqual(res.menu_button_landing_tab, "Exposure/Color")
        self.assertEqual(res.slot1_mymenu_vault_mutation_bytes, 0)

    def test_40_my_menu_op1_add_item_across_pages_and_duplicate_or_self_item_rejection(self) -> None:
        r1 = p257.coemulate_my_menu_and_camset_vault(
            operation="Add Item",
            target_page_index=1,
            item_name="Display Quality",
        )
        self.assertTrue(r1.admitted)
        self.assertEqual(r1.effective_pages, (("Display Quality",),))

        r_dup = p257.coemulate_my_menu_and_camset_vault(
            initial_pages=r1.effective_pages,
            operation="Add Item",
            target_page_index=1,
            item_name="Display Quality",
        )
        self.assertFalse(r_dup.admitted)
        self.assertEqual(r_dup.errno_code, p257.EINVAL_ERRNO)

        r_self = p257.coemulate_my_menu_and_camset_vault(
            operation="Add Item",
            target_page_index=1,
            item_name="My Menu Setting",
        )
        self.assertFalse(r_self.admitted)
        self.assertEqual(r_self.errno_code, p257.EOPNOTSUPP_ERRNO)

    def test_41_my_menu_op2_sort_item_reorders_within_and_across_pages_with_compaction(self) -> None:
        seed = (("Base ISO", "Shutter Mode"), ("Display Quality",))
        r_sorted = p257.coemulate_my_menu_and_camset_vault(
            initial_pages=seed,
            operation="Sort Item",
            item_name="Display Quality",
            sort_dest_page_index=1,
            sort_dest_slot_index=0,
        )
        self.assertTrue(r_sorted.admitted)
        self.assertEqual(
            r_sorted.effective_pages,
            (("Display Quality", "Base ISO", "Shutter Mode"),),
        )
        self.assertEqual(r_sorted.active_page_count, 1)

    def test_42_my_menu_op3_delete_item_removes_item_and_compacts_empty_page(self) -> None:
        seed = (("Base ISO",), ("Zebra Display", "Peaking Display"))
        res = p257.coemulate_my_menu_and_camset_vault(
            initial_pages=seed,
            operation="Delete Item",
            target_page_index=1,
            item_name="Base ISO",
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.effective_pages, (("Zebra Display", "Peaking Display"),))

        r_miss = p257.coemulate_my_menu_and_camset_vault(
            initial_pages=seed,
            operation="Delete Item",
            target_page_index=1,
            item_name="Peaking Display",
        )
        self.assertFalse(r_miss.admitted)
        self.assertEqual(r_miss.errno_code, p257.EINVAL_ERRNO)

    def test_43_my_menu_op4_delete_page_shifts_remaining_pages_and_rejects_empty_page(self) -> None:
        seed = (("Base ISO",), ("Zebra Display",), ("Display Quality",))
        res = p257.coemulate_my_menu_and_camset_vault(
            initial_pages=seed,
            operation="Delete Page",
            target_page_index=2,
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.effective_pages, (("Base ISO",), ("Display Quality",)))

        r_empty = p257.coemulate_my_menu_and_camset_vault(
            initial_pages=seed,
            operation="Delete Page",
            target_page_index=5,
        )
        self.assertFalse(r_empty.admitted)
        self.assertEqual(r_empty.errno_code, p257.EINVAL_ERRNO)

    def test_44_my_menu_op5_delete_all_clears_all_registered_pages(self) -> None:
        seed = (("Base ISO", "Shutter Mode"), ("Display Quality", "Bluetooth Rmt Ctrl"))
        res = p257.coemulate_my_menu_and_camset_vault(
            initial_pages=seed,
            operation="Delete All",
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.effective_pages, ())
        self.assertEqual(res.total_registered_items, 0)

    def test_45_my_menu_op6_display_from_my_menu_on_routes_menu_button_to_my_menu_first(self) -> None:
        r_on = p257.coemulate_my_menu_and_camset_vault(
            last_visited_tab="Network",
            operation="Display From My Menu",
            new_display_from_my_menu="On",
        )
        self.assertTrue(r_on.admitted)
        self.assertEqual(r_on.effective_display_from_my_menu, "On")
        self.assertEqual(r_on.menu_button_landing_tab, "My Menu")

        r_off = p257.coemulate_my_menu_and_camset_vault(
            configured_display_from_my_menu="On",
            last_visited_tab="Network",
            operation="Display From My Menu",
            new_display_from_my_menu="Off",
        )
        self.assertEqual(r_off.effective_display_from_my_menu, "Off")
        self.assertEqual(r_off.menu_button_landing_tab, "Network")

    def test_46_my_menu_6_pages_x_6_items_36_item_max_capacity_and_37th_overflow_enospc(self) -> None:
        full_36 = tuple(p257.ASSIGNABLE_MY_MENU_CATALOG[i * 6 : (i + 1) * 6] for i in range(6))
        r_ok = p257.coemulate_my_menu_and_camset_vault(initial_pages=full_36)
        self.assertTrue(r_ok.admitted)
        self.assertEqual(r_ok.active_page_count, 6)
        self.assertEqual(r_ok.total_registered_items, 36)

        r_ovf = p257.coemulate_my_menu_and_camset_vault(
            initial_pages=full_36,
            operation="Add Item",
            target_page_index=6,
            item_name=p257.ASSIGNABLE_MY_MENU_CATALOG[36],
        )
        self.assertFalse(r_ovf.admitted)
        self.assertEqual(r_ovf.errno_code, p257.ENOSPC_ERRNO)

        one_full_page = (p257.ASSIGNABLE_MY_MENU_CATALOG[:6],)
        r_pfull = p257.coemulate_my_menu_and_camset_vault(
            initial_pages=one_full_page,
            operation="Add Item",
            target_page_index=1,
            item_name=p257.ASSIGNABLE_MY_MENU_CATALOG[6],
        )
        self.assertFalse(r_pfull.admitted)
        self.assertEqual(r_pfull.errno_code, p257.ENOSPC_ERRNO)

    def test_47_my_menu_and_display_from_my_menu_survive_both_camera_and_network_resets(self) -> None:
        seed = (("Display Quality", "Bluetooth Rmt Ctrl"), ("Base ISO",))
        r_cam = p257.coemulate_my_menu_and_camset_vault(
            initial_pages=seed,
            configured_display_from_my_menu="On",
            reset_action="Camera Settings Reset",
        )
        self.assertTrue(r_cam.survived_camera_settings_reset)
        self.assertEqual(r_cam.effective_pages, seed)
        self.assertEqual(r_cam.effective_display_from_my_menu, "On")

        r_net = p257.coemulate_my_menu_and_camset_vault(
            initial_pages=seed,
            configured_display_from_my_menu="On",
            reset_action="Reset Network Set.",
        )
        self.assertTrue(r_net.survived_reset_network_set)
        self.assertEqual(r_net.effective_pages, seed)
        self.assertEqual(r_net.effective_display_from_my_menu, "On")

    def test_48_my_menu_and_display_from_my_menu_cleared_by_initialize(self) -> None:
        seed = (("Display Quality", "Bluetooth Rmt Ctrl"), ("Base ISO",))
        res = p257.coemulate_my_menu_and_camset_vault(
            initial_pages=seed,
            configured_display_from_my_menu="On",
            last_visited_tab="Setup",
            reset_action="Initialize",
        )
        self.assertTrue(res.cleared_by_initialize)
        self.assertEqual(res.effective_pages, ())
        self.assertEqual(res.total_registered_items, 0)
        self.assertEqual(res.effective_display_from_my_menu, "Off")
        self.assertEqual(res.menu_button_landing_tab, "Setup")

    def test_49_slot1_camset01_rdonly_load_restores_my_menu_pages_and_display_from_my_menu(self) -> None:
        vault_pages = (
            ("Display Quality", "Monitor Brightness", "Base ISO"),
            ("Bluetooth Rmt Ctrl", "Zebra Display"),
        )
        r_slot2 = p257.coemulate_my_menu_and_camset_vault(
            initial_pages=vault_pages,
            configured_display_from_my_menu="On",
            camset_action="SAVE_SLOT2_SCRATCH",
        )
        r_restored = p257.coemulate_my_menu_and_camset_vault(
            initial_pages=(("File Format",),),
            configured_display_from_my_menu="Off",
            reset_action="Initialize",
            camset_action="LOAD_SLOT1_VAULT_RDONLY",
            slot1_vault_camset_pages=vault_pages,
            slot1_vault_display_from_my_menu="On",
        )
        self.assertTrue(r_restored.admitted)
        self.assertTrue(r_restored.camset_roundtrip_restored)
        self.assertEqual(r_restored.effective_pages, vault_pages)
        self.assertEqual(r_restored.effective_display_from_my_menu, "On")
        self.assertEqual(r_restored.menu_button_landing_tab, "My Menu")
        self.assertEqual(
            r_restored.camset_serialized_sha256_prefix16,
            r_slot2.camset_serialized_sha256_prefix16,
        )
        self.assertEqual(r_restored.slot1_mymenu_vault_mutation_bytes, 0)

    def test_50_slot2_scratch_camset01_save_admitted_while_slot1_vault_write_blocked_erofs(self) -> None:
        seed = (("Display Quality", "Base ISO"),)
        r_s2 = p257.coemulate_my_menu_and_camset_vault(
            initial_pages=seed,
            configured_display_from_my_menu="On",
            camset_action="SAVE_SLOT2_SCRATCH",
        )
        self.assertTrue(r_s2.admitted)
        self.assertEqual(r_s2.slot1_mymenu_vault_mutation_bytes, 0)

        r_s1 = p257.coemulate_my_menu_and_camset_vault(
            initial_pages=seed,
            configured_display_from_my_menu="On",
            camset_action="SAVE_SLOT1_VAULT_MUTATE",
        )
        self.assertFalse(r_s1.admitted)
        self.assertEqual(r_s1.errno_code, p257.EROFS_ERRNO)
        self.assertEqual(r_s1.slot1_mymenu_vault_mutation_bytes, 0)

        r_force = p257.coemulate_my_menu_and_camset_vault(
            initial_pages=seed,
            force_slot1_vault_mymenu_write=True,
        )
        self.assertFalse(r_force.admitted)
        self.assertEqual(r_force.errno_code, p257.EROFS_ERRNO)
        self.assertEqual(r_force.slot1_mymenu_vault_mutation_bytes, 0)

    def test_51_my_menu_coemulator_input_validation_guards(self) -> None:
        with self.assertRaises(ValueError):
            p257.coemulate_my_menu_and_camset_vault(configured_display_from_my_menu="Maybe")
        with self.assertRaises(ValueError):
            p257.coemulate_my_menu_and_camset_vault(last_visited_tab="Cinema")
        with self.assertRaises(ValueError):
            p257.coemulate_my_menu_and_camset_vault(operation="Clone Page")
        with self.assertRaises(ValueError):
            p257.coemulate_my_menu_and_camset_vault(target_page_index=7)
        with self.assertRaises(ValueError):
            p257.coemulate_my_menu_and_camset_vault(sort_dest_page_index=0)
        with self.assertRaises(ValueError):
            p257.coemulate_my_menu_and_camset_vault(sort_dest_slot_index=6)
        with self.assertRaises(ValueError):
            p257.coemulate_my_menu_and_camset_vault(camset_action="FORMAT_SLOT1")
        with self.assertRaises(ValueError):
            p257.coemulate_my_menu_and_camset_vault(
                initial_pages=(("Base ISO", "Base ISO"),)
            )
        with self.assertRaises(ValueError):
            p257.coemulate_my_menu_and_camset_vault(
                operation="Add Item",
                item_name="Nonexistent Menu Item",
            )

    def test_52_baseline_redline_guard_valid_and_all_14_redline_probes_fail_closed(self) -> None:
        guard = p257.probe_phase257_redline_guard()
        self.assertTrue(guard.valid)
        self.assertEqual(guard.errno_code, 0)
        self.assertFalse(guard.persistent_emmc_writes_authorized)
        self.assertFalse(guard.hardware_live_attachment_authorized)
        self.assertFalse(guard.overall_ready_for_hardware_attach)
        self.assertFalse(guard.isp_write_authorized)
        self.assertFalse(guard.spi_nor_write_authorized)
        self.assertFalse(guard.el3_payload_transmit_authorized)
        self.assertTrue(guard.cnflasha_userspace_write_blocked)
        self.assertEqual(guard.physical_device_writes, 0)
        self.assertEqual(guard.nop_count, 0)
        self.assertEqual(guard.guest_code_modification_bytes, 0)

        self.assertEqual(len(p257.ALL_14_REDLINE_PROBE_FIELDS), 14)
        for field in p257.ALL_14_REDLINE_PROBE_FIELDS:
            pr = p257.probe_phase257_redline_guard(**{field: True})
            self.assertFalse(pr.valid, msg=field)
            self.assertIn(pr.errno_code, (p257.EACCES_ERRNO, p257.EROFS_ERRNO))
            self.assertFalse(pr.persistent_emmc_writes_authorized)
            self.assertFalse(pr.hardware_live_attachment_authorized)
            self.assertEqual(pr.physical_device_writes, 0)

    def test_53_unknown_redline_probe_field_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            p257.probe_phase257_redline_guard(nonexistent_probe=True)

    def test_54_pillar_c_d_evaluator_passes_all_6_ops_camset_and_redlines(self) -> None:
        pcd = p257.evaluate_pillar_c_d_mymenu_camset_and_redlines()
        self.assertTrue(pcd["passed"])
        self.assertEqual(
            pcd["all_6_my_menu_operations"],
            [
                "Add Item",
                "Sort Item",
                "Delete Item",
                "Delete Page",
                "Delete All",
                "Display From My Menu",
            ],
        )
        self.assertEqual(pcd["max_pages"], 6)
        self.assertEqual(pcd["max_items_per_page"], 6)
        self.assertEqual(pcd["max_total_items"], 36)
        self.assertEqual(len(pcd["blocked_redline_probes"]), 14)

    def test_55_top_level_redlines_locked_across_clean_room_and_default_modes(self) -> None:
        for rep in (self.clean_audit, self.default_audit):
            red = rep["redlines"]
            self.assertFalse(red["persistent_emmc_writes_authorized"])
            self.assertFalse(red["hardware_live_attachment_authorized"])
            self.assertFalse(red["overall_ready_for_hardware_attach"])
            self.assertFalse(red["isp_write_authorized"])
            self.assertFalse(red["spi_nor_write_authorized"])
            self.assertFalse(red["el3_payload_transmit_authorized"])
            self.assertTrue(red["cnflasha_userspace_write_blocked"])
            self.assertEqual(red["physical_device_writes"], 0)
            self.assertEqual(red["raw_firmware_bytes_leaked"], 0)
            self.assertEqual(red["nop_count"], 0)
            self.assertEqual(red["guest_code_modification_bytes"], 0)
            self.assertEqual(red["tier0_battery_high_display_violations"], 0)
            self.assertEqual(red["passive_tx_bytes_emitted"], 0)
            self.assertEqual(red["bt_rmt_ir_lockout_violations"], 0)
            self.assertEqual(red["slot1_mymenu_vault_mutation_bytes"], 0)

    # ------------------------------------------------------------------
    # Group 5: CLI, Suite Stage 49 (49/49) Wiring & Hygiene (11)
    # ------------------------------------------------------------------
    def test_56_in_process_cli_json_and_summary_modes(self) -> None:
        buf_json = io.StringIO()
        with contextlib.redirect_stdout(buf_json):
            rc_json = p257.main(["--self-test", "--clean-room", "--json"])
        self.assertEqual(rc_json, 0)
        parsed = json.loads(buf_json.getvalue())
        self.assertEqual(parsed["milestone"], "49/49")
        self.assertEqual(parsed["phase_number"], 257)
        self.assertTrue(parsed["all_checks_passed"])

        buf_sum = io.StringIO()
        with contextlib.redirect_stdout(buf_sum):
            rc_sum = p257.main(["--self-test", "--clean-room", "--summary"])
        self.assertEqual(rc_sum, 0)
        self.assertIn("[PASS] Phase 257 Stage 49 (49/49)", buf_sum.getvalue())

    def test_57_subprocess_cli_clean_room_and_default_modes(self) -> None:
        script = str(FX3_VM_DIR / "realhw_display_quality_bt_rmt_mymenu_coemulator.py")
        base_env = dict(os.environ)
        base_env["PYTHONDONTWRITEBYTECODE"] = "1"
        p_sum = subprocess.run(
            [sys.executable, "-B", script, "--self-test", "--summary"],
            capture_output=True,
            text=True,
            env=base_env,
            check=True,
        )
        self.assertIn("[PASS] Phase 257 Stage 49 (49/49)", p_sum.stdout)

        clean_env = dict(base_env)
        clean_env["FX3_FX6_FORCE_CLEAN_ROOM"] = "1"
        p_clean = subprocess.run(
            [sys.executable, "-B", script, "--self-test", "--summary"],
            capture_output=True,
            text=True,
            env=clean_env,
            check=True,
        )
        self.assertIn("mode=CLEAN_ROOM_SYNTHETIC", p_clean.stdout)

    def test_58_fx3_vm_coemulation_suite_includes_stage49_and_49_stage_milestone(self) -> None:
        self.assertTrue(self.clean_suite["all_checks_passed"])
        self.assertIn("stage49_realhw_display_quality_bt_rmt_mymenu_hil", self.clean_suite)
        s49 = self.clean_suite["stage49_realhw_display_quality_bt_rmt_mymenu_hil"]
        self.assertTrue(s49["all_checks_passed"])
        self.assertEqual(s49["phase_number"], 257)
        self.assertEqual(s49["milestone"], "49/49")
        self.assertEqual(
            s49["schema"],
            "realhw_display_quality_bt_rmt_mymenu_coemulator_v1",
        )
        self.assertEqual(s49["tier0_battery_high_display_violations"], 0)
        self.assertEqual(s49["passive_tx_bytes_emitted"], 0)
        self.assertEqual(s49["bt_rmt_ir_lockout_violations"], 0)
        self.assertEqual(s49["slot1_mymenu_vault_mutation_bytes"], 0)
        self.assertEqual(s49["raw_firmware_bytes_leaked"], 0)
        stage_keys = [k for k in self.clean_suite if re.match(r"^stage\d+_", k)]
        self.assertGreaterEqual(len(stage_keys), 49)
        self.assertLess(self.clean_suite_elapsed, 4.0)

    def test_59_fx3_vm_coemulation_suite_all_49_stage_indices_unique_and_present(self) -> None:
        self.assertTrue(self.default_suite["all_checks_passed"])
        for idx in range(1, 50):
            matches = [k for k in self.default_suite if re.match(rf"^stage{idx}_", k)]
            self.assertEqual(len(matches), 1, msg=f"Missing or duplicate stage{idx}_* key")
        self.assertLess(self.default_suite_elapsed, 4.0)

    def test_60_fx3_vm_coemulation_suite_skip_stage49_and_skip_phase257_config(self) -> None:
        rep_skip_p257 = suite.run_fx3_vm_coemulation_suite(
            suite.CoEmulationConfig(
                **_fast_suite_kwargs(
                    include_phase257_realhw_display_quality_bt_rmt_mymenu_hil=False
                )
            )
        )
        self.assertTrue(rep_skip_p257["all_checks_passed"])
        self.assertNotIn("stage49_realhw_display_quality_bt_rmt_mymenu_hil", rep_skip_p257)
        self.assertFalse(rep_skip_p257["config"]["include_stage49"])

        rep_skip_s49 = suite.run_fx3_vm_coemulation_suite(
            suite.CoEmulationConfig(**_fast_suite_kwargs(include_stage49=False))
        )
        self.assertTrue(rep_skip_s49["all_checks_passed"])
        self.assertNotIn("stage49_realhw_display_quality_bt_rmt_mymenu_hil", rep_skip_s49)

    def test_61_fx3_vm_coemulation_suite_include_stage49_cli_summary(self) -> None:
        fast_flags = [
            "--clean-room",
            "--skip-phase41",
            "--skip-phase45",
            "--skip-phase53",
            "--skip-phase58",
            "--skip-phase63",
            "--skip-phase67",
            "--skip-phase71",
            "--skip-phase78",
            "--skip-phase82",
            "--skip-phase87",
            "--skip-phase91",
            "--skip-phase96",
            "--skip-phase99",
            "--skip-phase103",
            "--skip-phase107",
            "--skip-phase112",
            "--skip-phase117",
            "--skip-phase121",
            "--skip-phase127",
            "--skip-phase132",
            "--skip-phase145",
            "--skip-phase162",
            "--skip-phase167",
        ]
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = suite.main(fast_flags + ["--include-stage49", "--summary"])
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("[PASS] Phase 33 FX3-VM Co-Emulation", out)
        self.assertIn("realhw_display_quality_bt_rmt_mymenu_hil=CLEAN_ROOM_SYNTHETIC", out)

    def test_62_fx3_vm_coemulation_suite_cli_skip_phase257_and_skip_stage49(self) -> None:
        fast_flags = [
            "--clean-room",
            "--skip-phase41",
            "--skip-phase45",
            "--skip-phase53",
            "--skip-phase58",
            "--skip-phase63",
            "--skip-phase67",
            "--skip-phase71",
            "--skip-phase78",
            "--skip-phase82",
            "--skip-phase87",
            "--skip-phase91",
            "--skip-phase96",
            "--skip-phase99",
            "--skip-phase103",
            "--skip-phase107",
            "--skip-phase112",
            "--skip-phase117",
            "--skip-phase121",
            "--skip-phase127",
            "--skip-phase132",
            "--skip-phase145",
            "--skip-phase162",
            "--skip-phase167",
        ]
        for flag in ("--skip-phase257", "--skip-stage49", "--no-include-stage49"):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = suite.main(fast_flags + [flag, "--json"])
            self.assertEqual(rc, 0)
            rep = json.loads(buf.getvalue())
            self.assertTrue(rep["all_checks_passed"])
            self.assertNotIn("stage49_realhw_display_quality_bt_rmt_mymenu_hil", rep)

    def test_63_run_stage49_direct_runner_matches_standalone_digest(self) -> None:
        cfg = suite.CoEmulationConfig(force_clean_room=True)
        s49 = suite.run_stage49_realhw_display_quality_bt_rmt_mymenu_hil(cfg)
        self.assertEqual(
            s49["phase257_audit_digest_sha256"],
            self.clean_audit["audit_digest_sha256"],
        )

    def test_64_menu_paths_match_official_sony_ilme_fx3_help_guide(self) -> None:
        self.assertEqual(
            p257.DISPLAY_QUALITY_MENU_PATH,
            "MENU -> Setup -> [Monitor] -> [Display Quality]",
        )
        self.assertEqual(
            p257.BLUETOOTH_RMT_CTRL_MENU_PATH,
            "MENU -> Network -> [Bluetooth] -> [Bluetooth Rmt Ctrl]",
        )
        self.assertEqual(
            p257.MY_MENU_SETTING_MENU_PATH,
            "MENU -> My Menu -> [My Menu Setting]",
        )
        self.assertEqual(
            p257.DISPLAY_FROM_MY_MENU_MENU_PATH,
            "MENU -> My Menu -> [My Menu Setting] -> [Display From My Menu]",
        )

    def test_65_fx3_vm_readme_documents_phase257_stage49_and_49_of_49(self) -> None:
        readme = (FX3_VM_DIR / "README.md").read_text(encoding="utf-8")
        self.assertIn("Phase 257", readme)
        self.assertIn("Stage 49", readme)
        self.assertIn("49/49", readme)
        self.assertIn("realhw_display_quality_bt_rmt_mymenu_coemulator.py", readme)
        self.assertIn("--include-stage49", readme)

    def test_66_zero_pyc_bytecode_files_and_sub_second_standalone_runtime(self) -> None:
        t0 = time.monotonic()
        r_clean = p257.run_phase257_realhw_display_quality_bt_rmt_mymenu_hil(
            force_clean_room=True
        )
        r_def = p257.run_phase257_realhw_display_quality_bt_rmt_mymenu_hil()
        elapsed = time.monotonic() - t0
        self.assertTrue(r_clean["all_checks_passed"])
        self.assertTrue(r_def["all_checks_passed"])
        self.assertLess(elapsed, 5.00 if __import__("os").environ.get("GITHUB_ACTIONS") == "true" else 1.0)
        pyc_files = list(FX3_VM_DIR.rglob("*.pyc"))
        self.assertEqual(pyc_files, [])


if __name__ == "__main__":
    unittest.main()
