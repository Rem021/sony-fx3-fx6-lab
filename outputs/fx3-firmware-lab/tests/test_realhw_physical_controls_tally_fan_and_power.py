"""Phase 149 Dual-Mode Unit Tests (46 tests): Real-Hardware ILME-FX3 Physical Body
Controls (`6x Custom` + Dials + `T/W` Zoom Rocker + 5-Way Joystick), Active Cooling Fan
PWM & Thermal Emergency Override, 3x Physical Red Tally LEDs, and `NP-FZ100` (`7.2V`) /
`USB-PD` (`9V/3A`) -> FX6 `appFw.so` Power Telemetry & `EncWfiStop` Bridge.
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
    BRIDGE_CLASS_HARD_WRITE_PROTECTED,
    BRIDGE_CLASS_MASKED_ABSENT_HW,
    BRIDGE_CLASS_NATIVE_PASSTHROUGH,
    BRIDGE_CLASS_SHIM_TRANSLATED,
    EXPECTED_SENCORE_EXPORTS,
    EXPECTED_SENCORE_IMPORTS,
)
from fx3_firmware_lab.realhw_physical_controls_tally_fan_and_power_auditor import (
    ESCAPE_HATCH_PHYSICAL_KEYS,
    EXPECTED_IM_ELF_BYTES,
    EXPECTED_IM_ELF_EXPORTS,
    EXPECTED_IM_ELF_IMPORTS,
    FAN_APPFW_FX3_MARKERS,
    FAN_APPFW_FX6_MARKERS,
    FAN_CP_SHARED_MARKERS,
    FX3_ACTIVE_4K60_POWER_W,
    FX3_PHYSICAL_KEYMAP_SPECS,
    FX3_PHYSICAL_TALLY_LEDS,
    FX6_ABSENT_BODY_CONTROLS,
    FX6_BPU_NOMINAL_MV,
    FX6_DC_IN_LOW_ALARM_MV,
    FX6_DC_IN_NOMINAL_MV_P149,
    KEYMAP_APPFW_FX3_MARKERS,
    KEYMAP_APPFW_FX6_MARKERS,
    NP_FZ100_ENC_WFI_STOP_MV_P149,
    NP_FZ100_ENC_WFI_STOP_SOC_PCT,
    NP_FZ100_MAX_MV_P149,
    NP_FZ100_MIN_OPERATING_MV_P149,
    NP_FZ100_NEAR_END_MV_P149,
    NP_FZ100_NEAR_END_SOC_PCT,
    NP_FZ100_NOMINAL_MV_P149,
    NP_FZ100_WH_P149,
    PHASE_149_SCHEMA,
    PHASE_149_VERSION,
    POWER_APPFW_FX3_MARKERS,
    POWER_APPFW_FX6_MARKERS,
    POWER_CP_SHARED_MARKERS,
    POWER_MPR_SHARED_MARKERS,
    REQUIRED_FX6_REACHABLE_FUNCTIONS,
    SENCORE_CONTROLS_TALLY_FAN_POWER_MARKERS,
    TALLY_APPFW_FX3_MARKERS,
    TALLY_APPFW_FX6_MARKERS,
    TALLY_CP_SHARED_MARKERS,
    THERMAL_CRITICAL_SHUTDOWN_C,
    THERMAL_EMERGENCY_SPINUP_C,
    THERMAL_PREHIGH_C,
    USB_PD_MIN_REC_POWER_MW,
    USB_PD_NOMINAL_MA,
    USB_PD_NOMINAL_MV,
    USB_PD_POWER_MW,
    VALID_FAN_MODES,
    VALID_TALLY_BRIGHTNESS_P149,
    VALID_TALLY_COLORS,
    VALID_USB_PD_PROFILES,
    analyze_realhw_physical_controls_tally_fan_and_power,
    build_clean_room_realhw_controls_fan_power_fixtures,
    build_phase149_controls_matrix,
    evaluate_cooling_fan_thermal_bridge,
    evaluate_phase149_write_guard,
    evaluate_physical_keymap_bridge,
    evaluate_power_telemetry_bridge,
    evaluate_tally_lamps_bridge,
    realhw_physical_controls_tally_fan_and_power_report_to_dict,
)


_BYTES_REPR_RE = re.compile(r"(?<![0-9A-Za-z_/.-])b['\"]")
_AUDITOR_PATH = (
    Path(__file__).resolve().parent.parent
    / "fx3_firmware_lab"
    / "realhw_physical_controls_tally_fan_and_power_auditor.py"
)


class TestRealhwPhysicalControlsTallyFanAndPower(unittest.TestCase):
    """Comprehensive dual-mode tests (46 tests) for the 30th unified auditor."""

    # ---- Mode, Runtime, Determinism & Structural Hygiene ----

    def test_01_clean_room_report_all_pillars_and_runtime(self) -> None:
        t0 = time.perf_counter()
        rep = analyze_realhw_physical_controls_tally_fan_and_power(clean_room=True)
        dt_cold = time.perf_counter() - t0
        t1 = time.perf_counter()
        rep_warm = analyze_realhw_physical_controls_tally_fan_and_power(clean_room=True)
        dt_warm = time.perf_counter() - t1

        self.assertTrue(rep.all_checks_passed, rep.errors)
        self.assertEqual(rep.mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(rep.schema_version, PHASE_149_SCHEMA)
        self.assertEqual(rep.phase_version, PHASE_149_VERSION)
        self.assertTrue(rep.o_rdonly_enforced)
        self.assertTrue(rep.all_fx6_core_functions_reachable)
        self.assertTrue(rep.escape_hatch_preserved)
        self.assertTrue(rep.thermal_emergency_override_intact)
        self.assertTrue(rep.zero_gpio_mismatch_verified)
        self.assertTrue(rep.false_dcin_alarm_eliminated)
        self.assertTrue(rep.enc_wfi_low_batt_autosave_verified)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertEqual(rep.emmc_mutation_bytes, 0)
        self.assertEqual(rep.calibration_mutation_bytes, 0)
        self.assertTrue(rep.pillar1_keymap.passed)
        self.assertTrue(rep.pillar2_fan_thermal.passed)
        self.assertTrue(rep.pillar3_tally_lamps.passed)
        self.assertTrue(rep.pillar4_power_telemetry.passed)
        self.assertEqual(rep.report_sha256, rep_warm.report_sha256)
        self.assertEqual(len(rep.report_sha256), 64)
        self.assertLess(dt_cold, 0.25)
        self.assertLess(dt_warm, 0.10)

    def test_02_auto_mode_or_local_donor_runtime_under_1500ms(self) -> None:
        t0 = time.perf_counter()
        rep = analyze_realhw_physical_controls_tally_fan_and_power()
        dt = time.perf_counter() - t0
        self.assertTrue(rep.all_checks_passed, rep.errors)
        self.assertIn(rep.mode, ("LOCAL_DONOR_VERIFIED", "CLEAN_ROOM_SYNTHETIC"))
        self.assertLess(dt, 1.5)
        if rep.mode == "LOCAL_DONOR_VERIFIED":
            self.assertEqual(rep.donor_file_sizes.get("fx3_appfw"), 79_015_712)
            self.assertEqual(rep.donor_file_sizes.get("fx6_appfw"), 50_520_424)
            self.assertEqual(rep.donor_file_sizes.get("fx3_sencore"), 377_328)
            self.assertEqual(rep.donor_file_sizes.get("fx6_sencore"), 401_952)
            self.assertEqual(rep.donor_file_sizes.get("fx3_libmpr"), 3_517_008)
            self.assertEqual(rep.donor_file_sizes.get("fx6_libmpr"), 28_921_824)
            self.assertEqual(rep.donor_file_sizes.get("fx3_im_elf"), EXPECTED_IM_ELF_BYTES)
            self.assertEqual(rep.donor_file_sizes.get("fx6_im_elf"), EXPECTED_IM_ELF_BYTES)
            self.assertEqual(rep.donor_file_sizes.get("fx3_cpapp"), 15_980_568)
            self.assertEqual(rep.donor_file_sizes.get("fx6_cpapp"), 17_952_816)
            self.assertEqual(rep.donor_file_sizes.get("fx3_backup"), 2_229_740)
            self.assertEqual(rep.donor_file_sizes.get("fx6_backup"), 2_253_333)

    def test_03_forced_clean_room_env_flag_respected(self) -> None:
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}, clear=False):
            rep = analyze_realhw_physical_controls_tally_fan_and_power()
        self.assertTrue(rep.all_checks_passed, rep.errors)
        self.assertEqual(rep.mode, "CLEAN_ROOM_SYNTHETIC")

    def test_04_missing_donor_falls_back_to_clean_room(self) -> None:
        with mock.patch(
            "fx3_firmware_lab.realhw_physical_controls_tally_fan_and_power_auditor.resolve_donor_file",
            return_value=None,
        ):
            rep = analyze_realhw_physical_controls_tally_fan_and_power(clean_room=False)
        self.assertTrue(rep.all_checks_passed, rep.errors)
        self.assertEqual(rep.mode, "CLEAN_ROOM_SYNTHETIC")

    def test_05_json_serialization_has_zero_bytes_repr(self) -> None:
        rep = analyze_realhw_physical_controls_tally_fan_and_power(clean_room=True)
        payload = realhw_physical_controls_tally_fan_and_power_report_to_dict(rep)
        json_str = json.dumps(payload, sort_keys=True)
        self.assertIsNone(_BYTES_REPR_RE.search(json_str), "Unexpected Python bytes repr in JSON")
        self.assertIn(PHASE_149_SCHEMA, json_str)

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

    def test_07_package_exports_and_all_include_phase149_symbols(self) -> None:
        expected_symbols = (
            "PHASE_149_SCHEMA",
            "PHASE_149_VERSION",
            "EXPECTED_IM_ELF_BYTES",
            "EXPECTED_IM_ELF_EXPORTS",
            "EXPECTED_IM_ELF_IMPORTS",
            "ESCAPE_HATCH_PHYSICAL_KEYS",
            "REQUIRED_FX6_REACHABLE_FUNCTIONS",
            "FX3_PHYSICAL_KEYMAP_SPECS",
            "FX6_ABSENT_BODY_CONTROLS",
            "VALID_FAN_MODES",
            "THERMAL_EMERGENCY_SPINUP_C",
            "THERMAL_CRITICAL_SHUTDOWN_C",
            "FX3_PHYSICAL_TALLY_LEDS",
            "VALID_TALLY_COLORS",
            "VALID_USB_PD_PROFILES",
            "NP_FZ100_NOMINAL_MV_P149",
            "USB_PD_POWER_MW",
            "FX6_DC_IN_LOW_ALARM_MV",
            "RealhwPhysicalControlsTallyFanAndPowerReport",
            "analyze_realhw_physical_controls_tally_fan_and_power",
            "build_clean_room_realhw_controls_fan_power_fixtures",
            "build_phase149_controls_matrix",
            "evaluate_physical_keymap_bridge",
            "evaluate_cooling_fan_thermal_bridge",
            "evaluate_tally_lamps_bridge",
            "evaluate_power_telemetry_bridge",
            "evaluate_phase149_write_guard",
            "realhw_physical_controls_tally_fan_and_power_report_to_dict",
        )
        for sym in expected_symbols:
            self.assertTrue(hasattr(lab, sym), f"Missing export {sym} on fx3_firmware_lab")
            self.assertIn(sym, lab.__all__, f"Missing {sym} in fx3_firmware_lab.__all__")

    def test_08_clean_room_fixtures_roundtrip_and_counts(self) -> None:
        fx = build_clean_room_realhw_controls_fan_power_fixtures()
        self.assertEqual(len(fx), 12)
        for key, buf in fx.items():
            self.assertIsInstance(buf, bytes, key)
            self.assertGreater(len(buf), 64, key)

    def test_09_cli_audit_realhw_controls_fan_power_clean_room_and_auto(self) -> None:
        for argv in (
            ["audit-realhw-controls-fan-power", "--clean-room", "--json"],
            ["audit-realhw-controls-fan-power", "--json"],
        ):
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = cli_main(argv)
            self.assertEqual(rc, 0)
            obj = json.loads(buf.getvalue())
            self.assertTrue(obj["all_checks_passed"])
            self.assertTrue(obj["o_rdonly_enforced"])
            self.assertTrue(obj["all_fx6_core_functions_reachable"])
            self.assertTrue(obj["escape_hatch_preserved"])
            self.assertTrue(obj["thermal_emergency_override_intact"])
            self.assertTrue(obj["zero_gpio_mismatch_verified"])
            self.assertTrue(obj["false_dcin_alarm_eliminated"])
            self.assertTrue(obj["enc_wfi_low_batt_autosave_verified"])
            self.assertFalse(obj["persistent_emmc_writes_authorized"])

    def test_10_run_audit_all_reaches_30_auditors(self) -> None:
        summary = run_audit_all(clean_room=True)
        self.assertTrue(summary["all_checks_passed"])
        audit_keys = [k for k in summary if k.endswith("_audit")]
        self.assertGreaterEqual(len(audit_keys), 30)
        self.assertIn("realhw_physical_controls_tally_fan_and_power_audit", summary)
        self.assertEqual(
            summary["realhw_physical_controls_tally_fan_and_power_audit"]["schema_version"],
            PHASE_149_SCHEMA,
        )

    def test_11_cli_audit_all_clean_room_returns_zero_with_30_keys(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cli_main(["audit-all", "--clean-room", "--json"])
        self.assertEqual(rc, 0)
        obj = json.loads(buf.getvalue())
        self.assertTrue(obj["all_checks_passed"])
        self.assertGreaterEqual(len([k for k in obj if k.endswith("_audit")]), 30)

    # ---- Pillar 1: Physical Body Keymap & Ergonomic Navigation Bridge ----

    def test_12_pillar1_report_im_elf_sencore_and_backup_abi_identical(self) -> None:
        rep = analyze_realhw_physical_controls_tally_fan_and_power(clean_room=True)
        p1 = rep.pillar1_keymap
        self.assertTrue(p1.passed)
        self.assertEqual(p1.fx3_appfw_keymap_hits, len(KEYMAP_APPFW_FX3_MARKERS))
        self.assertEqual(p1.fx6_appfw_keymap_hits, len(KEYMAP_APPFW_FX6_MARKERS))
        self.assertTrue(p1.sencore_exports_identical)
        self.assertEqual(p1.fx3_sencore.export_count, EXPECTED_SENCORE_EXPORTS)
        self.assertEqual(p1.fx3_sencore.import_count, EXPECTED_SENCORE_IMPORTS)
        self.assertTrue(p1.im_elf_abi_identical)
        self.assertEqual(p1.fx3_im_elf.export_count, EXPECTED_IM_ELF_EXPORTS)
        self.assertEqual(p1.fx3_im_elf.import_count, EXPECTED_IM_ELF_IMPORTS)
        self.assertEqual(p1.fx3_backup_subsystems, 819)
        self.assertEqual(p1.fx6_backup_subsystems, 840)
        self.assertTrue(p1.fx3_backup_checksums_valid)
        self.assertTrue(p1.fx6_backup_checksums_valid)
        self.assertTrue(p1.all_fx6_core_functions_reachable)
        self.assertTrue(p1.escape_hatch_preserved)

    def test_13_pillar1_all_fx3_physical_controls_valid_and_reachable(self) -> None:
        self.assertGreaterEqual(len(FX3_PHYSICAL_KEYMAP_SPECS), 15)
        mapped_functions = set()
        for ctrl in FX3_PHYSICAL_KEYMAP_SPECS:
            res = evaluate_physical_keymap_bridge(physical_control=ctrl)
            self.assertTrue(res.valid, (ctrl, res.errors))
            self.assertTrue(res.one_handed_reachable, ctrl)
            self.assertTrue(res.escape_hatch_preserved, ctrl)
            self.assertEqual(res.missing_gpio_faults, 0, ctrl)
            mapped_functions.add(res.fx6_target_function)
        for req_fn in REQUIRED_FX6_REACHABLE_FUNCTIONS:
            self.assertIn(req_fn, mapped_functions)

    def test_14_pillar1_escape_hatch_keys_protected_and_preemption_blocked(self) -> None:
        self.assertEqual(ESCAPE_HATCH_PHYSICAL_KEYS, ("MENU", "SHUTTER_HALF_FULL", "POWER_SWITCH"))
        for key in ESCAPE_HATCH_PHYSICAL_KEYS:
            ok = evaluate_physical_keymap_bridge(physical_control=key)
            self.assertTrue(ok.valid, key)
            self.assertTrue(ok.escape_hatch_preserved, key)

            blocked_override = evaluate_physical_keymap_bridge(
                physical_control=key, override_escape_hatch=True
            )
            self.assertFalse(blocked_override.valid, key)
            self.assertFalse(blocked_override.escape_hatch_preserved, key)
            self.assertEqual(blocked_override.status, "BLOCKED_ESCAPE_HATCH_PREEMPTION")

            blocked_remap = evaluate_physical_keymap_bridge(
                physical_control=key, requested_fx6_function="ASSIGN_9_ZEBRA"
            )
            self.assertFalse(blocked_remap.valid, key)
            self.assertFalse(blocked_remap.escape_hatch_preserved, key)
            self.assertEqual(blocked_remap.status, "BLOCKED_ESCAPE_HATCH_PREEMPTION")

    def test_15_pillar1_absent_fx6_body_controls_soft_mapped_and_unmasked_blocked(self) -> None:
        self.assertEqual(len(FX6_ABSENT_BODY_CONTROLS), 3)
        for ctrl in FX6_ABSENT_BODY_CONTROLS:
            ok = evaluate_physical_keymap_bridge(
                physical_control=ctrl, mask_absent_fx6_controls=True
            )
            self.assertTrue(ok.valid, ctrl)
            self.assertEqual(ok.status, "ABSENT_FX6_CONTROL_SOFT_MAPPED")
            self.assertEqual(ok.missing_gpio_faults, 0)

            bad = evaluate_physical_keymap_bridge(
                physical_control=ctrl, mask_absent_fx6_controls=False
            )
            self.assertFalse(bad.valid, ctrl)
            self.assertEqual(bad.status, "BLOCKED_UNMASKED_ABSENT_FX6_CONTROL")

    def test_16_pillar1_unknown_physical_control_rejected(self) -> None:
        bad = evaluate_physical_keymap_bridge(physical_control="FX6_REAR_SDI_GENLOCK_SWITCH")
        self.assertFalse(bad.valid)
        self.assertEqual(bad.status, "BLOCKED_UNKNOWN_FX3_CONTROL")
        self.assertEqual(bad.missing_gpio_faults, 1)

    def test_17_pillar1_zoom_rocker_and_dual_rec_native_passthrough(self) -> None:
        for ctrl, expected_fn in (
            ("ZOOM_ROCKER_T_W", "SERVO_ZOOM_8STEP"),
            ("REC_TOP", "REC_START_STOP"),
            ("REC_FRONT", "REC_START_STOP"),
            ("LENS_FOCUS_HOLD", "ASSIGN_7_LENS_FH"),
            ("JOYSTICK_5WAY", "DIRECT_TOUCH_JOYSTICK"),
        ):
            res = evaluate_physical_keymap_bridge(physical_control=ctrl)
            self.assertTrue(res.valid)
            self.assertEqual(res.classification, BRIDGE_CLASS_NATIVE_PASSTHROUGH)
            self.assertEqual(res.fx6_target_function, expected_fn)

    # ---- Pillar 2: Active Cooling Fan & Thermal Emergency Override ----

    def test_18_pillar2_report_fan_markers_cp_and_sencore_pwm(self) -> None:
        rep = analyze_realhw_physical_controls_tally_fan_and_power(clean_room=True)
        p2 = rep.pillar2_fan_thermal
        self.assertTrue(p2.passed)
        self.assertEqual(p2.fx3_appfw_fan_hits, len(FAN_APPFW_FX3_MARKERS))
        self.assertEqual(p2.fx6_appfw_fan_hits, len(FAN_APPFW_FX6_MARKERS))
        for m in FAN_CP_SHARED_MARKERS:
            self.assertGreater(p2.fx3_cp_fan_hits.get(m, 0), 0, m)
            self.assertGreater(p2.fx6_cp_fan_hits.get(m, 0), 0, m)
        self.assertTrue(p2.sencore_fan_pwm_verified)
        self.assertTrue(p2.thermal_emergency_override_intact)

    def test_19_pillar2_auto1_auto2_minimum_and_off_in_rec_nominal_pwm(self) -> None:
        self.assertEqual(
            VALID_FAN_MODES, ("AUTO1", "AUTO2", "MINIMUM", "OFF_IN_REC", "ALWAYS_OFF")
        )
        a1 = evaluate_cooling_fan_thermal_bridge(requested_fan_mode="AUTO1", sensor_temp_c=40.0)
        a2 = evaluate_cooling_fan_thermal_bridge(requested_fan_mode="AUTO2", sensor_temp_c=40.0)
        mn = evaluate_cooling_fan_thermal_bridge(requested_fan_mode="MINIMUM", sensor_temp_c=40.0)
        oir = evaluate_cooling_fan_thermal_bridge(
            requested_fan_mode="OFF_IN_REC", is_recording=True, sensor_temp_c=40.0
        )
        self.assertTrue(a1.valid and a2.valid and mn.valid and oir.valid)
        self.assertGreater(a1.effective_pwm_pct, a2.effective_pwm_pct)
        self.assertGreater(a2.effective_pwm_pct, mn.effective_pwm_pct)
        self.assertEqual(oir.effective_pwm_pct, 0)
        self.assertEqual(oir.classification, BRIDGE_CLASS_SHIM_TRANSLATED)
        self.assertTrue(oir.thermal_emergency_override_intact)

    def test_20_pillar2_off_in_rec_prehigh_and_emergency_spinup_override(self) -> None:
        pre = evaluate_cooling_fan_thermal_bridge(
            requested_fan_mode="OFF_IN_REC", is_recording=True, sensor_temp_c=THERMAL_PREHIGH_C
        )
        self.assertTrue(pre.valid)
        self.assertGreater(pre.effective_pwm_pct, 0)

        emg = evaluate_cooling_fan_thermal_bridge(
            requested_fan_mode="OFF_IN_REC",
            is_recording=True,
            sensor_temp_c=THERMAL_EMERGENCY_SPINUP_C,
        )
        self.assertTrue(emg.valid)
        self.assertEqual(emg.effective_pwm_pct, 100)
        self.assertTrue(emg.thermal_emergency_override_active)
        self.assertTrue(emg.thermal_emergency_override_intact)
        self.assertEqual(emg.status, "THERMAL_EMERGENCY_CP_OVERRIDE_SPINUP")

    def test_21_pillar2_critical_thermal_triggers_graceful_enc_wfi_stop(self) -> None:
        crit = evaluate_cooling_fan_thermal_bridge(
            requested_fan_mode="OFF_IN_REC",
            is_recording=True,
            sensor_temp_c=THERMAL_CRITICAL_SHUTDOWN_C,
        )
        self.assertTrue(crit.valid)
        self.assertEqual(crit.effective_pwm_pct, 100)
        self.assertTrue(crit.thermal_emergency_override_active)
        self.assertTrue(crit.thermal_emergency_override_intact)
        self.assertTrue(crit.graceful_enc_wfi_stop_triggered)
        self.assertEqual(crit.status, "THERMAL_CRITICAL_GRACEFUL_ENC_WFI_STOP")

    def test_22_pillar2_broken_fan_hot_triggers_graceful_enc_wfi_stop(self) -> None:
        brk = evaluate_cooling_fan_thermal_bridge(
            requested_fan_mode="AUTO1",
            is_recording=True,
            sensor_temp_c=THERMAL_PREHIGH_C + 2.0,
            fan_broken=True,
        )
        self.assertTrue(brk.valid)
        self.assertEqual(brk.effective_pwm_pct, 0)
        self.assertTrue(brk.thermal_emergency_override_active)
        self.assertTrue(brk.graceful_enc_wfi_stop_triggered)

    def test_23_pillar2_always_off_in_rec_and_override_bypass_blocked(self) -> None:
        always_off_rec = evaluate_cooling_fan_thermal_bridge(
            requested_fan_mode="ALWAYS_OFF", is_recording=True, sensor_temp_c=40.0
        )
        self.assertFalse(always_off_rec.valid)
        self.assertEqual(always_off_rec.status, "BLOCKED_UNSAFE_ALWAYS_OFF_IN_REC")

        always_off_idle = evaluate_cooling_fan_thermal_bridge(
            requested_fan_mode="ALWAYS_OFF", is_recording=False, sensor_temp_c=35.0
        )
        self.assertTrue(always_off_idle.valid)
        self.assertEqual(always_off_idle.effective_pwm_pct, 0)

        bypass = evaluate_cooling_fan_thermal_bridge(
            requested_fan_mode="OFF_IN_REC",
            is_recording=True,
            sensor_temp_c=68.0,
            allow_cp_thermal_override=False,
        )
        self.assertFalse(bypass.valid)
        self.assertFalse(bypass.thermal_emergency_override_intact)
        self.assertEqual(bypass.status, "BLOCKED_THERMAL_OVERRIDE_BYPASS")

        unk = evaluate_cooling_fan_thermal_bridge(requested_fan_mode="TURBO_UNKNOWN")
        self.assertFalse(unk.valid)
        self.assertEqual(unk.status, "BLOCKED_UNKNOWN_FAN_MODE")

    # ---- Pillar 3: 3x Physical Body Red Tally LEDs Sync ----

    def test_24_pillar3_report_tally_markers_cp_and_sencore_led(self) -> None:
        rep = analyze_realhw_physical_controls_tally_fan_and_power(clean_room=True)
        p3 = rep.pillar3_tally_lamps
        self.assertTrue(p3.passed)
        self.assertEqual(p3.fx3_appfw_tally_hits, len(TALLY_APPFW_FX3_MARKERS))
        self.assertEqual(p3.fx6_appfw_tally_hits, len(TALLY_APPFW_FX6_MARKERS))
        self.assertGreater(p3.fx3_cp_tally_hits, 0)
        self.assertGreater(p3.fx6_cp_tally_hits, 0)
        self.assertTrue(p3.sencore_tally_led_verified)
        self.assertTrue(p3.zero_gpio_mismatch_verified)
        self.assertEqual(
            FX3_PHYSICAL_TALLY_LEDS,
            ("FRONT_TALLY_LED", "TOP_REC_TALLY_LED", "REAR_TALLY_LED"),
        )

    def test_25_pillar3_red_tally_all_front_rear_and_standby_opcodes(self) -> None:
        all_up = evaluate_tally_lamps_bridge(
            front_tally_enabled=True, rear_tally_enabled=True, is_recording=True, tally_color="RED"
        )
        self.assertTrue(all_up.valid)
        self.assertEqual(all_up.rec_lamp_opcode, "REC_LAMP_ALL_LIGHTS_UP")
        self.assertTrue(all_up.front_led_lit and all_up.top_rec_led_lit and all_up.rear_led_lit)
        self.assertFalse(all_up.osd_only_tally)
        self.assertEqual(all_up.gpio_mismatch_count, 0)

        front_off = evaluate_tally_lamps_bridge(
            front_tally_enabled=False, rear_tally_enabled=True, is_recording=True, tally_color="RED"
        )
        self.assertEqual(front_off.rec_lamp_opcode, "REC_LAMP_ONLY_FRONT_OFF")
        self.assertFalse(front_off.front_led_lit)
        self.assertTrue(front_off.top_rec_led_lit and front_off.rear_led_lit)

        front_only = evaluate_tally_lamps_bridge(
            front_tally_enabled=True, rear_tally_enabled=False, is_recording=True, tally_color="RED"
        )
        self.assertEqual(front_only.rec_lamp_opcode, "REC_LAMP_LIGHT_UP_ONLY_ONE")
        self.assertTrue(front_only.front_led_lit)
        self.assertFalse(front_only.top_rec_led_lit or front_only.rear_led_lit)

        standby = evaluate_tally_lamps_bridge(
            front_tally_enabled=True, rear_tally_enabled=True, is_recording=False, tally_color="RED"
        )
        self.assertEqual(standby.rec_lamp_opcode, "REC_LAMP_ALL_LIGHTS_OUT")
        self.assertFalse(standby.front_led_lit or standby.top_rec_led_lit or standby.rear_led_lit)

    def test_26_pillar3_brightness_off_and_blink_supported(self) -> None:
        for bri in VALID_TALLY_BRIGHTNESS_P149:
            res = evaluate_tally_lamps_bridge(
                front_tally_enabled=True,
                rear_tally_enabled=True,
                brightness=bri,
                rec_tally_blink=(bri == "HIGH"),
                is_recording=True,
            )
            self.assertTrue(res.valid, bri)
            if bri == "OFF":
                self.assertEqual(res.rec_lamp_opcode, "REC_LAMP_ALL_LIGHTS_OUT")
                self.assertFalse(res.front_led_lit or res.top_rec_led_lit or res.rear_led_lit)

    def test_27_pillar3_green_and_yellow_tally_strictly_osd_only(self) -> None:
        self.assertEqual(VALID_TALLY_COLORS, ("RED", "GREEN", "YELLOW"))
        for col in ("GREEN", "YELLOW"):
            res = evaluate_tally_lamps_bridge(
                is_recording=True, tally_color=col, allow_non_red_on_red_gpio=False
            )
            self.assertTrue(res.valid, col)
            self.assertTrue(res.osd_only_tally, col)
            self.assertEqual(res.rec_lamp_opcode, "OSD_BORDER_ONLY_NO_RED_LED")
            self.assertFalse(res.front_led_lit or res.top_rec_led_lit or res.rear_led_lit)
            self.assertEqual(res.gpio_mismatch_count, 0)
            self.assertEqual(res.classification, BRIDGE_CLASS_MASKED_ABSENT_HW)

    def test_28_pillar3_non_red_on_red_gpio_and_invalid_inputs_blocked(self) -> None:
        bad_gpio = evaluate_tally_lamps_bridge(
            is_recording=True, tally_color="GREEN", allow_non_red_on_red_gpio=True
        )
        self.assertFalse(bad_gpio.valid)
        self.assertEqual(bad_gpio.status, "BLOCKED_TALLY_GPIO_COLOR_MISMATCH")
        self.assertEqual(bad_gpio.gpio_mismatch_count, 1)

        bad_bri = evaluate_tally_lamps_bridge(brightness="ULTRA")
        self.assertFalse(bad_bri.valid)
        self.assertEqual(bad_bri.status, "BLOCKED_UNKNOWN_TALLY_BRIGHTNESS")

        bad_col = evaluate_tally_lamps_bridge(tally_color="BLUE")
        self.assertFalse(bad_col.valid)
        self.assertEqual(bad_col.status, "BLOCKED_UNKNOWN_TALLY_COLOR")

    # ---- Pillar 4: NP-FZ100 (7.2V) + USB-PD (9V/3A) Power Telemetry Bridge ----

    def test_29_pillar4_report_power_mpr_wfi_cp_and_sencore_usb(self) -> None:
        rep = analyze_realhw_physical_controls_tally_fan_and_power(clean_room=True)
        p4 = rep.pillar4_power_telemetry
        self.assertTrue(p4.passed)
        self.assertEqual(p4.fx3_appfw_power_hits, len(POWER_APPFW_FX3_MARKERS))
        self.assertEqual(p4.fx6_appfw_power_hits, len(POWER_APPFW_FX6_MARKERS))
        self.assertEqual(p4.fx3_mpr_wfi_hits, len(POWER_MPR_SHARED_MARKERS))
        self.assertEqual(p4.fx6_mpr_wfi_hits, len(POWER_MPR_SHARED_MARKERS))
        self.assertEqual(p4.fx3_cp_batt_hits, len(POWER_CP_SHARED_MARKERS))
        self.assertEqual(p4.fx6_cp_batt_hits, len(POWER_CP_SHARED_MARKERS))
        self.assertTrue(p4.sencore_usb_buspower_verified)
        self.assertTrue(p4.false_dcin_alarm_eliminated)
        self.assertTrue(p4.enc_wfi_low_batt_autosave_verified)

    def test_30_pillar4_np_fz100_nominal_and_usb_pd_27w_15w_hud_badges(self) -> None:
        self.assertEqual(NP_FZ100_NOMINAL_MV_P149, 7200)
        self.assertEqual(USB_PD_NOMINAL_MV * USB_PD_NOMINAL_MA // 1000, USB_PD_POWER_MW)
        self.assertGreater(USB_PD_POWER_MW, USB_PD_MIN_REC_POWER_MW)
        self.assertEqual(FX6_BPU_NOMINAL_MV, 14400)
        self.assertEqual(FX6_DC_IN_NOMINAL_MV_P149, 19500)
        self.assertEqual(FX6_DC_IN_LOW_ALARM_MV, 18000)

        batt_only = evaluate_power_telemetry_bridge(
            battery_voltage_mv=7600, soc_pct=75, usb_pd_profile="NONE"
        )
        self.assertTrue(batt_only.valid)
        self.assertFalse(batt_only.usb_pd_attached)
        self.assertFalse(batt_only.false_dcin_low_voltage_alarm)
        self.assertIn("75%", batt_only.hud_display_badge)
        self.assertIn("min)", batt_only.hud_display_badge)
        expected_min = int(round((NP_FZ100_WH_P149 * 0.75 / FX3_ACTIVE_4K60_POWER_W) * 60.0))
        self.assertEqual(batt_only.remain_minutes, expected_min)

        pd27 = evaluate_power_telemetry_bridge(
            battery_voltage_mv=7400, soc_pct=62, usb_pd_profile="USB_PD_9V_3A_27W"
        )
        self.assertTrue(pd27.valid)
        self.assertTrue(pd27.usb_pd_attached)
        self.assertEqual(pd27.hud_display_badge, "62% + USB-PD (9V/3A)")

        pd15 = evaluate_power_telemetry_bridge(
            battery_voltage_mv=7300, soc_pct=50, usb_pd_profile="USB_PD_5V_3A_15W"
        )
        self.assertTrue(pd15.valid)
        self.assertTrue(pd15.usb_pd_attached)
        self.assertEqual(pd15.hud_display_badge, "50% + USB-PD (5V/3A)")

    def test_31_pillar4_near_end_and_enc_wfi_stop_autosave(self) -> None:
        near = evaluate_power_telemetry_bridge(
            battery_voltage_mv=NP_FZ100_NEAR_END_MV_P149,
            soc_pct=NP_FZ100_NEAR_END_SOC_PCT,
            usb_pd_profile="NONE",
            is_recording=True,
        )
        self.assertTrue(near.valid)
        self.assertTrue(near.near_end_warning)
        self.assertFalse(near.enc_wfi_graceful_stop_triggered)
        self.assertEqual(near.status, "SONY_INFO_BATTERY_NEAR_END_WARNING")

        stop = evaluate_power_telemetry_bridge(
            battery_voltage_mv=NP_FZ100_ENC_WFI_STOP_MV_P149,
            soc_pct=NP_FZ100_ENC_WFI_STOP_SOC_PCT,
            usb_pd_profile="NONE",
            is_recording=True,
        )
        self.assertTrue(stop.valid)
        self.assertTrue(stop.near_end_warning)
        self.assertTrue(stop.enc_wfi_graceful_stop_triggered)
        self.assertTrue(stop.corrupt_rsv_clip_prevented)
        self.assertEqual(stop.status, "LOW_BATT_GRACEFUL_ENC_WFI_STOP")

        # When USB-PD is attached, low battery SoC should NOT trigger false EncWfiStop
        pd_saved = evaluate_power_telemetry_bridge(
            battery_voltage_mv=6080,
            soc_pct=2,
            usb_pd_profile="USB_PD_9V_3A_27W",
            is_recording=True,
        )
        self.assertTrue(pd_saved.valid)
        self.assertFalse(pd_saved.enc_wfi_graceful_stop_triggered)

    def test_32_pillar4_false_19v5_dcin_alarm_and_invalid_states_blocked(self) -> None:
        false_alarm = evaluate_power_telemetry_bridge(
            battery_voltage_mv=7200,
            soc_pct=80,
            usb_pd_profile="USB_PD_9V_3A_27W",
            apply_fx6_18v_dcin_threshold=True,
        )
        self.assertFalse(false_alarm.valid)
        self.assertTrue(false_alarm.false_dcin_low_voltage_alarm)
        self.assertEqual(false_alarm.status, "BLOCKED_FALSE_FX6_DCIN_19V5_ALARM")

        unauth = evaluate_power_telemetry_bridge(battery_authenticated=False)
        self.assertFalse(unauth.valid)
        self.assertEqual(unauth.status, "BLOCKED_UNAUTHENTICATED_BATTERY")

        overv = evaluate_power_telemetry_bridge(battery_voltage_mv=NP_FZ100_MAX_MV_P149 + 200)
        self.assertFalse(overv.valid)
        self.assertEqual(overv.status, "BLOCKED_BATT_OVERVOLTAGE")

        dead = evaluate_power_telemetry_bridge(battery_voltage_mv=5500)
        self.assertFalse(dead.valid)
        self.assertEqual(dead.status, "BLOCKED_BATT_UNDERVOLTAGE_DEAD")

        bad_soc = evaluate_power_telemetry_bridge(soc_pct=105)
        self.assertFalse(bad_soc.valid)
        self.assertEqual(bad_soc.status, "BLOCKED_OUT_OF_RANGE_SOC_PCT")

        bad_pd = evaluate_power_telemetry_bridge(usb_pd_profile="USB_PD_20V_5A_100W")
        self.assertFalse(bad_pd.valid)
        self.assertEqual(bad_pd.status, "BLOCKED_UNKNOWN_USB_PD_PROFILE")

        legacy_low = evaluate_power_telemetry_bridge(
            battery_voltage_mv=6300,
            soc_pct=4,
            usb_pd_profile="USB_LEGACY_5V_500MA",
            is_recording=True,
        )
        self.assertFalse(legacy_low.valid)
        self.assertEqual(legacy_low.status, "BLOCKED_INSUFFICIENT_USB_POWER_FOR_REC")

    # ---- Compatibility Matrix & Persistent Write-Guard ----

    def test_33_compatibility_matrix_structure_and_four_classes(self) -> None:
        matrix = build_phase149_controls_matrix()
        self.assertEqual(matrix.total_touchpoints, 12)
        self.assertEqual(len(matrix.touchpoints), 12)
        self.assertEqual(sum(matrix.class_counts.values()), 12)
        self.assertEqual(sum(matrix.subsystem_counts.values()), 12)
        for cls in (
            BRIDGE_CLASS_NATIVE_PASSTHROUGH,
            BRIDGE_CLASS_SHIM_TRANSLATED,
            BRIDGE_CLASS_MASKED_ABSENT_HW,
            BRIDGE_CLASS_HARD_WRITE_PROTECTED,
        ):
            self.assertGreater(matrix.class_counts[cls], 0, cls)
        for sub in ("CONTROLS_KEYMAP", "FAN_THERMAL", "TALLY_LEDS", "POWER_TELEMETRY"):
            self.assertGreater(matrix.subsystem_counts[sub], 0, sub)

    def test_34_write_guard_allows_volatile_ram_only(self) -> None:
        for path in (
            "/tmp/stage_b/keymap_override.json",
            "ram://stage_b/fan_tally_state.json",
            "ramdisk://power_hud_cache",
            "mem://bk4_shadow",
        ):
            res = evaluate_phase149_write_guard(path)
            self.assertTrue(res.valid, path)
            self.assertTrue(res.volatile_ram_staged)
            self.assertFalse(res.persistent_write_blocked)
            self.assertEqual(res.emmc_mutation_bytes, 0)
            self.assertEqual(res.calibration_mutation_bytes, 0)

    def test_35_write_guard_blocks_backup_cpapp_emmc_and_calibration(self) -> None:
        for bad_path in (
            "p2:/setting/Backup.bin",
            "/dev/nflasha8/cpapp-b.bin",
            "/dev/cnflasha0",
            "/dev/mmcblk0p2",
            "p18:/lens/lensfile.bin",
            "/tmp/Backup.bin",
            "nvram://fan_curve",
        ):
            res = evaluate_phase149_write_guard(bad_path)
            self.assertFalse(res.valid, bad_path)
            self.assertFalse(res.volatile_ram_staged)
            self.assertTrue(res.persistent_write_blocked)
            self.assertEqual(res.emmc_mutation_bytes, 0)
            self.assertEqual(res.calibration_mutation_bytes, 0)
            self.assertEqual(res.status, "BLOCKED_PERSISTENT_EMMC_OR_NVS_WRITE")

    # ---- Cross-Checks & Invariants ----

    def test_36_sencore_markers_all_8_present_in_both_bodies(self) -> None:
        self.assertEqual(len(SENCORE_CONTROLS_TALLY_FAN_POWER_MARKERS), 8)
        rep = analyze_realhw_physical_controls_tally_fan_and_power(clean_room=True)
        for marker in SENCORE_CONTROLS_TALLY_FAN_POWER_MARKERS:
            self.assertGreater(rep.pillar1_keymap.fx3_sencore.marker_hits.get(marker, 0), 0, marker)
            self.assertGreater(rep.pillar1_keymap.fx6_sencore.marker_hits.get(marker, 0), 0, marker)

    def test_37_im_elf_dt_needed_identical_between_fx3_and_fx6(self) -> None:
        rep = analyze_realhw_physical_controls_tally_fan_and_power(clean_room=True)
        p1 = rep.pillar1_keymap
        self.assertEqual(p1.fx3_im_elf.dt_needed, p1.fx6_im_elf.dt_needed)
        self.assertIn("libIMDB.so", p1.fx3_im_elf.dt_needed)
        self.assertIn("libbackup.so", p1.fx3_im_elf.dt_needed)
        self.assertIn("libosal_uipc.so", p1.fx3_im_elf.dt_needed)

    def test_38_voltage_bounds_constants_consistent(self) -> None:
        self.assertGreater(NP_FZ100_MAX_MV_P149, NP_FZ100_NOMINAL_MV_P149)
        self.assertGreater(NP_FZ100_NOMINAL_MV_P149, NP_FZ100_NEAR_END_MV_P149)
        self.assertGreater(NP_FZ100_NEAR_END_MV_P149, NP_FZ100_ENC_WFI_STOP_MV_P149)
        self.assertGreater(NP_FZ100_ENC_WFI_STOP_MV_P149, NP_FZ100_MIN_OPERATING_MV_P149)
        self.assertLess(NP_FZ100_ENC_WFI_STOP_SOC_PCT, NP_FZ100_NEAR_END_SOC_PCT)

    def test_39_thermal_threshold_ordering_monotonic(self) -> None:
        self.assertLess(THERMAL_PREHIGH_C, THERMAL_EMERGENCY_SPINUP_C)
        self.assertLess(THERMAL_EMERGENCY_SPINUP_C, THERMAL_CRITICAL_SHUTDOWN_C)

    def test_40_valid_usb_pd_profiles_all_handled(self) -> None:
        for prof in VALID_USB_PD_PROFILES:
            res = evaluate_power_telemetry_bridge(
                battery_voltage_mv=7400, soc_pct=50, usb_pd_profile=prof, is_recording=True
            )
            self.assertTrue(res.valid, (prof, res.errors))

    def test_41_report_dict_roundtrip_top_level_keys(self) -> None:
        rep = analyze_realhw_physical_controls_tally_fan_and_power(clean_room=True)
        d = realhw_physical_controls_tally_fan_and_power_report_to_dict(rep)
        for key in (
            "schema_version",
            "phase_version",
            "mode",
            "all_checks_passed",
            "o_rdonly_enforced",
            "all_fx6_core_functions_reachable",
            "escape_hatch_preserved",
            "thermal_emergency_override_intact",
            "zero_gpio_mismatch_verified",
            "false_dcin_alarm_eliminated",
            "enc_wfi_low_batt_autosave_verified",
            "persistent_emmc_writes_authorized",
            "emmc_mutation_bytes",
            "calibration_mutation_bytes",
            "donor_file_sizes",
            "pillar1_keymap",
            "pillar2_fan_thermal",
            "pillar3_tally_lamps",
            "pillar4_power_telemetry",
            "compatibility_matrix",
            "volatile_guard_ok",
            "forbidden_backup_guard_blocked",
            "forbidden_cpapp_guard_blocked",
            "forbidden_emmc_guard_blocked",
            "report_sha256",
            "errors",
        ):
            self.assertIn(key, d)

    def test_42_corrupted_cpapp_fixture_fails_closed(self) -> None:
        fx = build_clean_room_realhw_controls_fan_power_fixtures()
        fx["fx3_cpapp"] = b"\x00" * 128
        with mock.patch(
            "fx3_firmware_lab.realhw_physical_controls_tally_fan_and_power_auditor.build_clean_room_realhw_controls_fan_power_fixtures",
            return_value=fx,
        ):
            rep = analyze_realhw_physical_controls_tally_fan_and_power(clean_room=True)
        self.assertFalse(rep.all_checks_passed)
        self.assertFalse(rep.pillar2_fan_thermal.passed)
        self.assertFalse(rep.pillar3_tally_lamps.passed)
        self.assertFalse(rep.pillar4_power_telemetry.passed)

    def test_43_corrupted_libmpr_fixture_fails_closed(self) -> None:
        fx = build_clean_room_realhw_controls_fan_power_fixtures()
        fx["fx6_libmpr"] = fx["fx3_sencore"]
        with mock.patch(
            "fx3_firmware_lab.realhw_physical_controls_tally_fan_and_power_auditor.build_clean_room_realhw_controls_fan_power_fixtures",
            return_value=fx,
        ):
            rep = analyze_realhw_physical_controls_tally_fan_and_power(clean_room=True)
        self.assertFalse(rep.all_checks_passed)
        self.assertFalse(rep.pillar4_power_telemetry.passed)

    def test_44_auto_mode_sha256_deterministic_across_runs(self) -> None:
        r1 = analyze_realhw_physical_controls_tally_fan_and_power()
        r2 = analyze_realhw_physical_controls_tally_fan_and_power()
        self.assertEqual(r1.mode, r2.mode)
        self.assertEqual(r1.report_sha256, r2.report_sha256)

    def test_45_write_guards_in_report_consistent(self) -> None:
        rep = analyze_realhw_physical_controls_tally_fan_and_power(clean_room=True)
        self.assertTrue(rep.volatile_guard_ok.valid)
        self.assertTrue(rep.volatile_guard_ok.volatile_ram_staged)
        self.assertTrue(rep.forbidden_backup_guard_blocked.persistent_write_blocked)
        self.assertTrue(rep.forbidden_cpapp_guard_blocked.persistent_write_blocked)
        self.assertTrue(rep.forbidden_emmc_guard_blocked.persistent_write_blocked)

    def test_46_local_donor_specific_invariants_when_present(self) -> None:
        rep = analyze_realhw_physical_controls_tally_fan_and_power()
        if rep.mode != "LOCAL_DONOR_VERIFIED":
            self.skipTest("Local BYOF donors absent in clean-room environment")
        self.assertEqual(rep.pillar1_keymap.fx3_im_elf.export_count, 11)
        self.assertEqual(rep.pillar1_keymap.fx3_im_elf.import_count, 85)
        self.assertEqual(rep.pillar1_keymap.fx3_sencore.export_count, 355)
        self.assertEqual(rep.pillar1_keymap.fx3_sencore.import_count, 130)
        self.assertEqual(rep.pillar1_keymap.fx3_backup_subsystems, 819)
        self.assertEqual(rep.pillar1_keymap.fx6_backup_subsystems, 840)
        self.assertGreaterEqual(rep.pillar2_fan_thermal.fx3_cp_fan_hits.get("PWM", 0), 12)
        self.assertGreaterEqual(rep.pillar2_fan_thermal.fx3_cp_fan_hits.get("THERM", 0), 10)
        self.assertGreaterEqual(rep.pillar3_tally_lamps.fx3_cp_tally_hits, 1)


if __name__ == "__main__":
    unittest.main()
