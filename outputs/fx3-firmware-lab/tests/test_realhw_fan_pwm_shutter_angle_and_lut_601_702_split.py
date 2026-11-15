"""Phase 197 Dual-Mode Unit Tests (55 tests) — 41st Firmware Auditor (41/41):
Real-Hardware `ILME-FX3` (`Ver. 7.02`) 4-Mode Fan PWM (`Auto/Minimum/Off in Rec/
Always Off`, Zero `Auto1/Auto2`), Independent `[Shutter Mode]` (`Speed` vs
`Angle` `5.6°..64F / 360°`) & `Ver. 6.01` vs `Ver. 7.00/7.02` `p2:/setting` User
LUT Binary Slot Split Auditor.
"""

from __future__ import annotations

import ast
import io
import json
import os
import struct
import sys
import tempfile
import time
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

sys.dont_write_bytecode = True

import fx3_firmware_lab as pkg  # noqa: E402
from fx3_firmware_lab import (  # noqa: E402
    ADJUST_CONTROL_OPCODE_HEX_P197,
    ALL_VALID_REC_FRAME_RATES_P197,
    APPFW_FORBIDDEN_AUTO12_MARKERS_P197,
    APPFW_FX3_702_EXCLUSIVE_MARKERS_P197,
    APPFW_FX6_601_EXCLUSIVE_LUT_MARKERS_P197,
    APPFW_SHARED_FAN_SHUTTER_MARKERS_P197,
    BK4_PROP_SHUTTER_ANGLE_HEX_P197,
    BK4_PROP_SHUTTER_MODE_HEX_P197,
    BRIDGE_CLASS_HARD_WRITE_PROTECTED,
    BRIDGE_CLASS_MASKED_ABSENT_HW,
    BRIDGE_CLASS_NATIVE_PASSTHROUGH,
    BRIDGE_CLASS_SHIM_TRANSLATED,
    CANONICAL_SHUTTER_ANGLES_DEG_P197,
    CANONICAL_SLOW_SHUTTER_FRAME_MULTIPLES_P197,
    COLD_DUMP_P3_SIZE_MIB_P197,
    DONOR_COLD_SCAN_BUDGET_SEC_P197,
    EMERGENCY_THERMAL_TEMP_HIGH_C_P197,
    EMERGENCY_THERMAL_TEMP_STANDARD_C_P197,
    EXPECTED_FX3_APPFW_BYTES_P197,
    EXPECTED_FX3_BACKUP_BYTES_P197,
    EXPECTED_FX3_BK4_SUBSYSTEMS_P197,
    EXPECTED_FX3_CPAPP_BYTES_P197,
    EXPECTED_FX3_UXC_EN_F_BYTES_P197,
    EXPECTED_FX6_APPFW_BYTES_P197,
    EXPECTED_FX6_BACKUP_BYTES_P197,
    EXPECTED_FX6_BK4_SUBSYSTEMS_P197,
    EXPECTED_FX6_CPAPP_BYTES_P197,
    EXPECTED_FX6_UXC_EN_BYTES_P197,
    FAN_PWM_EMERGENCY_MAX_PCT_P197,
    FAN_PWM_MINIMUM_FLOOR_PCT_P197,
    FAN_PWM_OFF_PCT_P197,
    FAN_PWM_STANDBY_PURGE_MAX_PCT_P197,
    FORBIDDEN_NON_FX3_FAN_MODES_P197,
    FX3_FAN_CONTROL_MENU_PATH_P197,
    FX3_FAN_CONTROL_MODES_P197,
    LUT_SLOT_SCHEMA_LEGACY_LE_601_P197,
    LUT_SLOT_SCHEMA_OPT_GE_700_P197,
    LUT_SLOT_V1_RECORD_BYTES_P197,
    LUT_SLOT_V2_MAGIC_BYTES_P197,
    LUT_SLOT_V2_RECORD_BYTES_P197,
    PHASE_197_SCHEMA,
    PHASE_197_VERSION,
    SHUTTER_ANGLE_64F_EQUIV_DEG_P197,
    SHUTTER_ANGLE_MIN_DEG_P197,
    SHUTTER_ANGLE_STD_MAX_DEG_P197,
    VALID_BRIDGE_CLASSES,
    VOLATILE_FX6_LUT_OVERLAY_DIR_P197,
    analyze_realhw_fan_pwm_shutter_angle_and_lut_601_702_split,
    build_clean_room_realhw_fan_pwm_shutter_lut_split_fixtures,
    build_phase197_compat_matrix,
    evaluate_fx3_fan_pwm_and_prebackup_thermal_guard,
    evaluate_independent_shutter_mode_and_angle_range,
    evaluate_phase197_write_guard,
    evaluate_user_lut_601_vs_702_binary_split_firewall,
    parse_shutter_angle_token,
    realhw_fan_pwm_shutter_angle_and_lut_601_702_split_report_to_dict,
    serialize_user_lut_slot_header,
    simulate_backup_bin_shutter_slot_transitions,
    verify_stock_702_user_lut_slot_deserialization,
)
from fx3_firmware_lab import (  # noqa: E402
    realhw_fan_pwm_shutter_angle_and_lut_601_702_split_auditor as mod_p197,
)
from fx3_firmware_lab.__main__ import main as cli_main  # noqa: E402
from fx3_firmware_lab.__main__ import run_audit_all  # noqa: E402


class TestRealhwFanPwmShutterAngleAndLut601702Split(unittest.TestCase):
    """55 dual-mode unit tests for Phase 197 (41st Auditor `41/41`)."""

    # ------------------------------------------------------------------
    # Group A: AST Zero-Write Proof, Cold/Warm SLA, Clean-Room & Safety
    # ------------------------------------------------------------------

    def test_01_ast_strictly_o_rdonly_and_zero_write_calls(self) -> None:
        src_path = Path(mod_p197.__file__)
        src_text = src_path.read_text(encoding="utf-8")
        tree = ast.parse(src_text)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                self.assertNotEqual(node.func.id, "open", "builtin open() is forbidden")
            if isinstance(node, ast.Attribute):
                self.assertFalse(
                    node.attr.startswith(
                        ("write", "unlink", "rmdir", "mkdir", "chmod", "chown")
                    ),
                    f"forbidden mutating attribute: {node.attr}",
                )
        self.assertIn("os.O_RDONLY", src_text)
        self.assertIn("os.pread", src_text)

    def test_02_clean_room_report_passes_under_sla(self) -> None:
        t0 = time.monotonic()
        rep = analyze_realhw_fan_pwm_shutter_angle_and_lut_601_702_split(clean_room=True)
        dt = time.monotonic() - t0
        self.assertLess(dt, 1.0)
        self.assertEqual(rep.schema_version, PHASE_197_SCHEMA)
        self.assertEqual(rep.phase_version, PHASE_197_VERSION)
        self.assertEqual(rep.auditor_index, "41/41")
        self.assertEqual(rep.mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(rep.all_checks_passed)
        self.assertEqual(rep.errors, ())
        self.assertTrue(rep.o_rdonly_enforced)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_03_auto_mode_under_cold_sla_and_cache_hit_on_second_call(self) -> None:
        mod_p197._DONOR_SCAN_CACHE.clear()
        t0 = time.monotonic()
        r1 = analyze_realhw_fan_pwm_shutter_angle_and_lut_601_702_split(clean_room=False)
        dt1 = time.monotonic() - t0
        self.assertLess(dt1, 6.0)
        self.assertTrue(r1.all_checks_passed)
        self.assertEqual(r1.errors, ())
        if r1.mode == "LOCAL_DONOR_RDONLY":
            # Cold donor bounded O_RDONLY scan must stay within < 0.15s budget (allow tiny CI jitter ceiling < 0.40s)
            self.assertLess(r1.cold_or_cached_scan_elapsed_sec, 0.40)
            self.assertLessEqual(DONOR_COLD_SCAN_BUDGET_SEC_P197, 0.15)
            self.assertFalse(r1.cache_hit)
            t1 = time.monotonic()
            r2 = analyze_realhw_fan_pwm_shutter_angle_and_lut_601_702_split(clean_room=False)
            dt2 = time.monotonic() - t1
            self.assertTrue(r2.cache_hit)
            self.assertLess(dt2, 0.05)
            self.assertEqual(r1.report_sha256, r2.report_sha256)

    def test_04_clean_room_deterministic_sha256(self) -> None:
        r1 = analyze_realhw_fan_pwm_shutter_angle_and_lut_601_702_split(clean_room=True)
        r2 = analyze_realhw_fan_pwm_shutter_angle_and_lut_601_702_split(clean_room=True)
        self.assertEqual(r1.report_sha256, r2.report_sha256)
        self.assertEqual(len(r1.report_sha256), 64)

    def test_05_report_to_dict_json_roundtrip_leaks_zero_firmware_bytes(self) -> None:
        rep = analyze_realhw_fan_pwm_shutter_angle_and_lut_601_702_split(clean_room=False)
        payload = realhw_fan_pwm_shutter_angle_and_lut_601_702_split_report_to_dict(rep)
        encoded = json.dumps(payload, sort_keys=True)
        decoded = json.loads(encoded)
        self.assertTrue(decoded["all_checks_passed"])
        self.assertEqual(decoded["auditor_index"], "41/41")
        self.assertEqual(decoded["raw_firmware_bytes_leaked"], 0)
        self.assertNotIn("\\x7fELF", encoded)
        self.assertNotIn("uxd\\x07", encoded)

    def test_06_env_force_clean_room_override(self) -> None:
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            rep = analyze_realhw_fan_pwm_shutter_angle_and_lut_601_702_split(clean_room=False)
            self.assertEqual(rep.mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertTrue(rep.all_checks_passed)

    def test_07_missing_donor_directory_gracefully_falls_back_to_clean_room(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            with mock.patch.object(mod_p197, "resolve_donor_file", return_value=None):
                rep = analyze_realhw_fan_pwm_shutter_angle_and_lut_601_702_split(
                    clean_room=False,
                    repo_root=Path(tmpdir),
                )
                self.assertEqual(rep.mode, "CLEAN_ROOM_SYNTHETIC")
                self.assertTrue(rep.all_checks_passed)

    def test_08_hard_safety_invariants_enforced(self) -> None:
        for cr in (True, False):
            rep = analyze_realhw_fan_pwm_shutter_angle_and_lut_601_702_split(clean_room=cr)
            self.assertTrue(rep.o_rdonly_enforced)
            self.assertEqual(rep.raw_firmware_bytes_leaked, 0)
            self.assertFalse(rep.persistent_emmc_writes_authorized)
            self.assertFalse(rep.spi_nor_write_authorized)
            self.assertFalse(rep.el3_payload_transmit_authorized)
            self.assertEqual(rep.physical_usb_packets_emitted, 0)
            self.assertEqual(rep.persistent_writes, 0)
            self.assertEqual(rep.p2_setting_mutation_bytes, 0)
            self.assertEqual(rep.calibration_mutation_bytes, 0)
            self.assertTrue(rep.fan_4mode_and_prebackup_thermal_verified)
            self.assertTrue(rep.independent_shutter_speed_angle_verified)
            self.assertTrue(rep.lut_601_vs_702_binary_split_firewall_verified)
            self.assertTrue(rep.write_firewall_and_matrix_verified)

    def test_09_donor_sizes_and_bk4_subsystem_counts_verified(self) -> None:
        rep = analyze_realhw_fan_pwm_shutter_angle_and_lut_601_702_split(clean_room=False)
        self.assertEqual(
            rep.pillar_2_shutter_speed_angle.fx3_backup_header.rec0_subsystems,
            EXPECTED_FX3_BK4_SUBSYSTEMS_P197,
        )
        self.assertEqual(
            rep.pillar_2_shutter_speed_angle.fx6_backup_header.rec0_subsystems,
            EXPECTED_FX6_BK4_SUBSYSTEMS_P197,
        )
        if rep.mode == "LOCAL_DONOR_RDONLY":
            self.assertEqual(rep.donor_file_sizes["fx3_appfw"], EXPECTED_FX3_APPFW_BYTES_P197)
            self.assertEqual(rep.donor_file_sizes["fx6_appfw"], EXPECTED_FX6_APPFW_BYTES_P197)
            self.assertEqual(
                rep.donor_file_sizes["fx3_string_english_f_uxc"],
                EXPECTED_FX3_UXC_EN_F_BYTES_P197,
            )
            self.assertEqual(
                rep.donor_file_sizes["fx6_string_english_uxc"],
                EXPECTED_FX6_UXC_EN_BYTES_P197,
            )
            self.assertEqual(rep.donor_file_sizes["fx3_cpapp_b_bin"], EXPECTED_FX3_CPAPP_BYTES_P197)
            self.assertEqual(rep.donor_file_sizes["fx6_cpapp_b_bin"], EXPECTED_FX6_CPAPP_BYTES_P197)
            self.assertEqual(rep.donor_file_sizes["fx3_backup_bin"], EXPECTED_FX3_BACKUP_BYTES_P197)
            self.assertEqual(rep.donor_file_sizes["fx6_backup_bin"], EXPECTED_FX6_BACKUP_BYTES_P197)
            # Bounded CPAPP read must read strictly less than the full >15 MiB binary
            self.assertLess(
                rep.pillar_1_fan_pwm_thermal.fx3_cpapp_summary.bounded_bytes_read,
                EXPECTED_FX3_CPAPP_BYTES_P197,
            )
            self.assertLess(
                rep.pillar_1_fan_pwm_thermal.fx6_cpapp_summary.bounded_bytes_read,
                EXPECTED_FX6_CPAPP_BYTES_P197,
            )

    # ------------------------------------------------------------------
    # Group B: Pillar 1 — ILME-FX3 4-Mode Fan PWM & Pre-Backup Guard
    # ------------------------------------------------------------------

    def test_10_fx3_exact_4_fan_modes_and_menu_path(self) -> None:
        self.assertEqual(
            FX3_FAN_CONTROL_MODES_P197,
            ("Auto", "Minimum", "Off in Rec", "Always Off"),
        )
        self.assertEqual(
            FX3_FAN_CONTROL_MENU_PATH_P197,
            "MENU -> Setup -> [Setup Option] -> [Fan Control]",
        )
        for non_fx3 in ("Auto1", "Auto2"):
            self.assertNotIn(non_fx3, FX3_FAN_CONTROL_MODES_P197)
            self.assertIn(non_fx3, FORBIDDEN_NON_FX3_FAN_MODES_P197)

    def test_11_binary_proof_zero_auto1_auto2_in_appfw_and_uxc(self) -> None:
        for cr in (True, False):
            rep = analyze_realhw_fan_pwm_shutter_angle_and_lut_601_702_split(clean_room=cr)
            p1 = rep.pillar_1_fan_pwm_thermal
            self.assertTrue(p1.passed)
            for k in APPFW_FORBIDDEN_AUTO12_MARKERS_P197:
                self.assertEqual(p1.fx3_forbidden_auto12_hits[k], 0)
                self.assertEqual(p1.fx6_forbidden_auto12_hits[k], 0)
            self.assertEqual(p1.fx3_uxc_en_f_summary.forbidden_auto12_hits["Auto1"], 0)
            self.assertEqual(p1.fx3_uxc_en_f_summary.forbidden_auto12_hits["Auto2"], 0)
            self.assertEqual(p1.fx6_uxc_en_summary.forbidden_auto12_hits["Auto1"], 0)
            self.assertEqual(p1.fx6_uxc_en_summary.forbidden_auto12_hits["Auto2"], 0)

    def test_12_studio_auto1_auto2_tokens_rejected_fail_closed(self) -> None:
        for bad_tok in ("Auto1", "Auto2", "AUTO1", "AUTO2"):
            ev = evaluate_fx3_fan_pwm_and_prebackup_thermal_guard(fan_mode=bad_tok)
            self.assertFalse(ev.valid)
            self.assertTrue(ev.non_fx3_auto12_rejected)
            self.assertEqual(ev.bridge_class, BRIDGE_CLASS_MASKED_ABSENT_HW)
            self.assertIn("FORBIDDEN_NON_FX3_STUDIO_FAN_TOKEN", ev.status)

    def test_13_unknown_non_fx3_fan_modes_rejected(self) -> None:
        for bad_tok in ("Normal", "High", "Low", "Max", ""):
            ev = evaluate_fx3_fan_pwm_and_prebackup_thermal_guard(fan_mode=bad_tok)
            self.assertFalse(ev.valid)
            self.assertFalse(ev.non_fx3_auto12_rejected)
            self.assertEqual(ev.bridge_class, BRIDGE_CLASS_HARD_WRITE_PROTECTED)
            self.assertIn("INVALID_FX3_FAN_CONTROL_MODE", ev.status)

    def test_14_invalid_auto_power_off_temp_and_extreme_temp_rejected(self) -> None:
        ev_apo = evaluate_fx3_fan_pwm_and_prebackup_thermal_guard(
            fan_mode="Auto", auto_power_off_temp="Ultra"
        )
        self.assertFalse(ev_apo.valid)
        self.assertIn("INVALID_AUTO_POWER_OFF_TEMP", ev_apo.status)

        ev_cold = evaluate_fx3_fan_pwm_and_prebackup_thermal_guard(
            fan_mode="Auto", internal_temp_c=-50.0
        )
        self.assertFalse(ev_cold.valid)
        self.assertIn("OUT_OF_RANGE_INTERNAL_TEMP_C", ev_cold.status)

        ev_hot = evaluate_fx3_fan_pwm_and_prebackup_thermal_guard(
            fan_mode="Auto", internal_temp_c=150.0
        )
        self.assertFalse(ev_hot.valid)

    def test_15_fan_auto_mode_proportional_pwm_curve(self) -> None:
        ev_low = evaluate_fx3_fan_pwm_and_prebackup_thermal_guard(
            fan_mode="Auto", internal_temp_c=30.0, auto_power_off_temp="High"
        )
        ev_mid = evaluate_fx3_fan_pwm_and_prebackup_thermal_guard(
            fan_mode="Auto", internal_temp_c=47.5, auto_power_off_temp="High"
        )
        ev_high = evaluate_fx3_fan_pwm_and_prebackup_thermal_guard(
            fan_mode="Auto", internal_temp_c=62.0, auto_power_off_temp="High"
        )
        self.assertTrue(ev_low.valid and ev_mid.valid and ev_high.valid)
        self.assertEqual(ev_low.effective_pwm_duty_pct, 30)
        self.assertEqual(ev_mid.effective_pwm_duty_pct, 60)
        self.assertEqual(ev_high.effective_pwm_duty_pct, 90)
        self.assertEqual(ev_mid.appfw_enum_symbol, "FAN_CONTROL_AUTO")

    def test_16_fan_minimum_mode_quiet_floor(self) -> None:
        ev = evaluate_fx3_fan_pwm_and_prebackup_thermal_guard(
            fan_mode="Minimum", is_recording=True, internal_temp_c=45.0
        )
        self.assertTrue(ev.valid)
        self.assertEqual(ev.effective_pwm_duty_pct, FAN_PWM_MINIMUM_FLOOR_PCT_P197)
        self.assertEqual(ev.appfw_enum_symbol, "FAN_CONTROL_MINIMUM")
        self.assertFalse(ev.standby_max_pwm_heat_purge)

    def test_17_off_in_rec_zero_pwm_during_recording_below_emergency(self) -> None:
        ev = evaluate_fx3_fan_pwm_and_prebackup_thermal_guard(
            fan_mode="Off in Rec",
            is_recording=True,
            internal_temp_c=52.0,
            auto_power_off_temp="High",
        )
        self.assertTrue(ev.valid)
        self.assertEqual(ev.appfw_enum_symbol, "FAN_CONTROL_OFF_IN_REC")
        self.assertEqual(ev.effective_pwm_duty_pct, FAN_PWM_OFF_PCT_P197)
        self.assertTrue(ev.fan_stopped_for_acoustic_silence)
        self.assertFalse(ev.standby_max_pwm_heat_purge)
        self.assertFalse(ev.emergency_thermal_override_active)
        self.assertEqual(ev.status, "OFF_IN_REC_ACOUSTIC_ZERO_PWM_DURING_REC_OK")

    def test_18_off_in_rec_standby_100pct_max_pwm_active_heat_purge(self) -> None:
        ev = evaluate_fx3_fan_pwm_and_prebackup_thermal_guard(
            fan_mode="Off in Rec",
            is_recording=False,
            internal_temp_c=40.0,
            auto_power_off_temp="Standard",
        )
        self.assertTrue(ev.valid)
        self.assertTrue(ev.standby_max_pwm_heat_purge)
        self.assertFalse(ev.fan_stopped_for_acoustic_silence)
        self.assertEqual(ev.effective_pwm_duty_pct, FAN_PWM_STANDBY_PURGE_MAX_PCT_P197)
        self.assertEqual(ev.status, "OFF_IN_REC_STANDBY_MAX_PWM_HEAT_PURGE_OK")

    def test_19_off_in_rec_emergency_thermal_override_standard_vs_high(self) -> None:
        # At 70C: Standard (68C threshold) triggers 100% emergency override; High (78C) stays 0%
        ev_std = evaluate_fx3_fan_pwm_and_prebackup_thermal_guard(
            fan_mode="Off in Rec",
            is_recording=True,
            internal_temp_c=70.0,
            auto_power_off_temp="Standard",
        )
        ev_high_ok = evaluate_fx3_fan_pwm_and_prebackup_thermal_guard(
            fan_mode="Off in Rec",
            is_recording=True,
            internal_temp_c=70.0,
            auto_power_off_temp="High",
        )
        ev_high_emerg = evaluate_fx3_fan_pwm_and_prebackup_thermal_guard(
            fan_mode="Off in Rec",
            is_recording=True,
            internal_temp_c=79.0,
            auto_power_off_temp="High",
        )
        self.assertEqual(ev_std.emergency_threshold_c, EMERGENCY_THERMAL_TEMP_STANDARD_C_P197)
        self.assertTrue(ev_std.emergency_thermal_override_active)
        self.assertEqual(ev_std.effective_pwm_duty_pct, FAN_PWM_EMERGENCY_MAX_PCT_P197)

        self.assertEqual(ev_high_ok.emergency_threshold_c, EMERGENCY_THERMAL_TEMP_HIGH_C_P197)
        self.assertFalse(ev_high_ok.emergency_thermal_override_active)
        self.assertEqual(ev_high_ok.effective_pwm_duty_pct, 0)

        self.assertTrue(ev_high_emerg.emergency_thermal_override_active)
        self.assertEqual(ev_high_emerg.effective_pwm_duty_pct, 100)

    def test_20_always_off_normal_and_emergency_override(self) -> None:
        ev_norm = evaluate_fx3_fan_pwm_and_prebackup_thermal_guard(
            fan_mode="Always Off", is_recording=False, internal_temp_c=45.0
        )
        self.assertTrue(ev_norm.valid)
        self.assertEqual(ev_norm.appfw_enum_symbol, "FAN_CONTROL_ALWAYS_OFF")
        self.assertEqual(ev_norm.effective_pwm_duty_pct, 0)
        self.assertFalse(ev_norm.standby_max_pwm_heat_purge)

        ev_emerg = evaluate_fx3_fan_pwm_and_prebackup_thermal_guard(
            fan_mode="Always Off",
            is_recording=False,
            internal_temp_c=80.0,
            auto_power_off_temp="High",
        )
        self.assertTrue(ev_emerg.valid)
        self.assertTrue(ev_emerg.emergency_thermal_override_active)
        self.assertEqual(ev_emerg.effective_pwm_duty_pct, 100)

    def test_21_prebackup_75mib_p3_cold_dump_blocks_unguarded_always_off(self) -> None:
        ev = evaluate_fx3_fan_pwm_and_prebackup_thermal_guard(
            fan_mode="Always Off",
            internal_temp_c=46.0,
            auto_power_off_temp="Standard",
            cold_dump_p3_75mib_requested=True,
            auto_interlock_enforced=False,
        )
        self.assertFalse(ev.valid)
        self.assertTrue(ev.cxd90057_cxd90058_overheat_risk)
        self.assertEqual(ev.adjust_control_opcode_hex, ADJUST_CONTROL_OPCODE_HEX_P197)
        self.assertEqual(COLD_DUMP_P3_SIZE_MIB_P197, 75)
        self.assertEqual(ev.bridge_class, BRIDGE_CLASS_HARD_WRITE_PROTECTED)
        self.assertEqual(ev.status, "BLOCKED_ALWAYS_OFF_PREBACKUP_THERMAL_HAZARD")

    def test_22_prebackup_75mib_p3_cold_dump_interlock_forces_always_off_to_auto(self) -> None:
        ev = evaluate_fx3_fan_pwm_and_prebackup_thermal_guard(
            fan_mode="Always Off",
            internal_temp_c=50.0,
            auto_power_off_temp="High",
            cold_dump_p3_75mib_requested=True,
            auto_interlock_enforced=True,
        )
        self.assertTrue(ev.valid)
        self.assertEqual(ev.requested_fan_mode, "Always Off")
        self.assertEqual(ev.effective_fan_mode, "Auto")
        self.assertEqual(ev.appfw_enum_symbol, "FAN_CONTROL_AUTO")
        self.assertTrue(ev.prebackup_forced_to_auto)
        self.assertFalse(ev.cxd90057_cxd90058_overheat_risk)
        self.assertGreater(ev.effective_pwm_duty_pct, 0)
        self.assertEqual(ev.bridge_class, BRIDGE_CLASS_SHIM_TRANSLATED)
        self.assertEqual(ev.status, "PREBACKUP_INTERLOCK_FORCED_AUTO_THERMAL_SAFE_OK")

    def test_23_prebackup_75mib_p3_cold_dump_interlock_also_guards_off_in_rec(self) -> None:
        ev_blk = evaluate_fx3_fan_pwm_and_prebackup_thermal_guard(
            fan_mode="Off in Rec",
            cold_dump_p3_75mib_requested=True,
            auto_interlock_enforced=False,
        )
        self.assertFalse(ev_blk.valid)
        self.assertTrue(ev_blk.cxd90057_cxd90058_overheat_risk)

        ev_ok = evaluate_fx3_fan_pwm_and_prebackup_thermal_guard(
            fan_mode="Off in Rec",
            cold_dump_p3_75mib_requested=True,
            auto_interlock_enforced=True,
        )
        self.assertTrue(ev_ok.valid)
        self.assertEqual(ev_ok.effective_fan_mode, "Auto")
        self.assertTrue(ev_ok.prebackup_forced_to_auto)

    # ------------------------------------------------------------------
    # Group C: Pillar 2 — Independent [Shutter Mode] & Range Clamping
    # ------------------------------------------------------------------

    def test_24_parse_shutter_angle_token_accepts_canonical_degrees_and_slow_frames(self) -> None:
        for deg in CANONICAL_SHUTTER_ANGLES_DEG_P197:
            ok, val, lbl, err = parse_shutter_angle_token(f"{deg}°")
            self.assertTrue(ok, f"failed for {deg}: {err}")
            self.assertAlmostEqual(val, deg, places=4)
            self.assertTrue(lbl.endswith("deg"))
            self.assertIsNone(err)

        for mult in CANONICAL_SLOW_SHUTTER_FRAME_MULTIPLES_P197:
            ok, val, lbl, err = parse_shutter_angle_token(f"{mult}F")
            self.assertTrue(ok, f"failed for {mult}F: {err}")
            self.assertAlmostEqual(val, mult * 360.0, places=4)
            self.assertEqual(lbl, f"{mult}F")
            self.assertIsNone(err)

    def test_25_parse_shutter_angle_token_rejects_malformed_and_out_of_bounds(self) -> None:
        for bad in ("", "   ", "abc", "5.5", "0.0", "-90", "360.5", "720", "1F", "9F", "128F", "XF"):
            ok, _val, _lbl, err = parse_shutter_angle_token(bad)
            self.assertFalse(ok, f"unexpectedly accepted {bad!r}")
            self.assertIsNotNone(err)

    def test_26_backup_bin_speed_and_angle_slots_conserved_across_toggles_and_ev_steps(self) -> None:
        self.assertEqual(BK4_PROP_SHUTTER_MODE_HEX_P197, "0x02cf1702")
        self.assertEqual(BK4_PROP_SHUTTER_ANGLE_HEX_P197, "0x02cf1704")
        before, after, conserved = simulate_backup_bin_shutter_slot_transitions(
            initial_speed_token="1/60",
            initial_angle_token="172.8°",
            initial_exposure_step="0.3EV",
            updated_exposure_step="0.5EV",
        )
        self.assertTrue(conserved)
        self.assertEqual(before.shutter_mode, "Speed")
        self.assertEqual(after.shutter_mode, "Angle")
        self.assertEqual(after.stored_speed_token, "1/60")
        self.assertEqual(after.stored_angle_token, "172.8deg")
        self.assertEqual(after.exposure_step, "0.5EV")

    def test_27_simulate_backup_bin_shutter_slot_transitions_rejects_bad_inputs(self) -> None:
        with self.assertRaises(ValueError):
            simulate_backup_bin_shutter_slot_transitions(initial_speed_token="1/99999")
        with self.assertRaises(ValueError):
            simulate_backup_bin_shutter_slot_transitions(initial_angle_token="2.0")
        with self.assertRaises(ValueError):
            simulate_backup_bin_shutter_slot_transitions(updated_exposure_step="1.0EV")

    def test_28_normal_movie_accepts_full_5_6_deg_to_64f_envelope(self) -> None:
        ev_min = evaluate_independent_shutter_mode_and_angle_range(
            shooting_mode="NORMAL_MOVIE",
            rec_frame_rate="24.00p",
            shutter_mode="Angle",
            requested_angle_token="5.6",
        )
        ev_64f = evaluate_independent_shutter_mode_and_angle_range(
            shooting_mode="NORMAL_MOVIE",
            rec_frame_rate="24.00p",
            shutter_mode="Angle",
            requested_angle_token="64F",
        )
        self.assertTrue(ev_min.valid and ev_64f.valid)
        self.assertEqual(ev_min.effective_angle_deg, SHUTTER_ANGLE_MIN_DEG_P197)
        self.assertEqual(ev_64f.effective_angle_deg, SHUTTER_ANGLE_64F_EQUIV_DEG_P197)
        self.assertAlmostEqual(ev_64f.exposure_time_sec, 64.0 / 24.0, places=6)
        self.assertFalse(ev_64f.angle_clamped)
        self.assertEqual(ev_64f.bridge_class, BRIDGE_CLASS_NATIVE_PASSTHROUGH)

    def test_29_angle_mode_completely_immune_to_exposure_step_03ev_vs_05ev(self) -> None:
        ev_03 = evaluate_independent_shutter_mode_and_angle_range(
            rec_frame_rate="23.98p",
            shutter_mode="Angle",
            exposure_step="0.3EV",
            requested_angle_token="180.0",
        )
        ev_05 = evaluate_independent_shutter_mode_and_angle_range(
            rec_frame_rate="23.98p",
            shutter_mode="Angle",
            exposure_step="0.5EV",
            requested_angle_token="180.0",
        )
        self.assertTrue(ev_03.valid and ev_05.valid)
        self.assertTrue(ev_03.angle_immune_to_exposure_step)
        self.assertTrue(ev_05.angle_immune_to_exposure_step)
        self.assertEqual(ev_03.effective_angle_deg, ev_05.effective_angle_deg)
        self.assertEqual(ev_03.exposure_time_sec, ev_05.exposure_time_sec)

    def test_30_speed_mode_computes_reciprocal_exposure_and_preserves_angle_slot(self) -> None:
        ev = evaluate_independent_shutter_mode_and_angle_range(
            rec_frame_rate="25p",
            shutter_mode="Speed",
            stored_speed_slot="1/100",
            requested_angle_token="172.8",
        )
        self.assertTrue(ev.valid)
        self.assertAlmostEqual(ev.exposure_time_sec, 0.01, places=8)
        self.assertEqual(ev.effective_angle_token, "172.8deg")
        self.assertTrue(ev.speed_and_angle_slots_independent)
        self.assertEqual(ev.status, "SHUTTER_MODE_SPEED_ACTIVE_ANGLE_SLOT_PRESERVED_OK")

    def test_31_hfr_119_88p_and_100p_clamp_slow_shutter_to_360_on_transition(self) -> None:
        for hfr in ("119.88p", "100p"):
            ev = evaluate_independent_shutter_mode_and_angle_range(
                shooting_mode="NORMAL_MOVIE",
                rec_frame_rate=hfr,
                shutter_mode="Angle",
                requested_angle_token="64F",
                clamp_on_mode_transition=True,
            )
            self.assertTrue(ev.valid)
            self.assertTrue(ev.angle_clamped)
            self.assertEqual(ev.effective_angle_deg, SHUTTER_ANGLE_STD_MAX_DEG_P197)
            self.assertEqual(ev.effective_angle_token, "360.0deg")
            self.assertEqual(ev.max_allowed_angle_deg, 360.0)
            self.assertEqual(ev.bridge_class, BRIDGE_CLASS_SHIM_TRANSLATED)

    def test_32_hfr_119_88p_and_100p_reject_direct_2f_to_64f_selection(self) -> None:
        for hfr in ("119.88p", "100p"):
            for slow_tok in ("2F", "8F", "64F"):
                ev = evaluate_independent_shutter_mode_and_angle_range(
                    shooting_mode="NORMAL_MOVIE",
                    rec_frame_rate=hfr,
                    shutter_mode="Angle",
                    requested_angle_token=slow_tok,
                    clamp_on_mode_transition=False,
                )
                self.assertFalse(ev.valid)
                self.assertEqual(ev.status, "SHUTTER_ANGLE_EXCEEDS_HFR_100P_11988P_360_LIMIT")
                self.assertEqual(ev.bridge_class, BRIDGE_CLASS_HARD_WRITE_PROTECTED)

    def test_33_hfr_119_88p_and_100p_accept_5_6_to_360_deg_natively(self) -> None:
        for hfr in ("119.88p", "100p"):
            for tok in ("5.6", "180.0", "360.0"):
                ev = evaluate_independent_shutter_mode_and_angle_range(
                    shooting_mode="NORMAL_MOVIE",
                    rec_frame_rate=hfr,
                    shutter_mode="Angle",
                    requested_angle_token=tok,
                    clamp_on_mode_transition=False,
                )
                self.assertTrue(ev.valid)
                self.assertFalse(ev.angle_clamped)

    def test_34_sq_motion_enforces_5_6_to_360_deg_range(self) -> None:
        ev_ok = evaluate_independent_shutter_mode_and_angle_range(
            shooting_mode="SQ_MOTION",
            rec_frame_rate="23.98p",
            shutter_mode="Angle",
            requested_angle_token="180.0",
        )
        self.assertTrue(ev_ok.valid)
        self.assertFalse(ev_ok.angle_clamped)

        ev_clamp = evaluate_independent_shutter_mode_and_angle_range(
            shooting_mode="SQ_MOTION",
            rec_frame_rate="23.98p",
            shutter_mode="Angle",
            requested_angle_token="32F",
            clamp_on_mode_transition=True,
        )
        self.assertTrue(ev_clamp.valid)
        self.assertTrue(ev_clamp.angle_clamped)
        self.assertEqual(ev_clamp.effective_angle_deg, 360.0)

        ev_rej = evaluate_independent_shutter_mode_and_angle_range(
            shooting_mode="SQ_MOTION",
            rec_frame_rate="23.98p",
            shutter_mode="Angle",
            requested_angle_token="2F",
            clamp_on_mode_transition=False,
        )
        self.assertFalse(ev_rej.valid)
        self.assertEqual(ev_rej.status, "SHUTTER_ANGLE_EXCEEDS_SQ_360_LIMIT")

    def test_35_shutter_angle_below_5_6_deg_rejected_across_all_fps(self) -> None:
        for fps in ALL_VALID_REC_FRAME_RATES_P197:
            ev = evaluate_independent_shutter_mode_and_angle_range(
                rec_frame_rate=fps,
                shutter_mode="Angle",
                requested_angle_token="4.5",
            )
            self.assertFalse(ev.valid)
            self.assertIn("SHUTTER_ANGLE_BELOW_5_6_DEG_MINIMUM", ev.status)

    def test_36_shutter_evaluator_rejects_invalid_enums_with_zero_backup_writes(self) -> None:
        cases = [
            {"shooting_mode": "PHOTO_STILL"},
            {"rec_frame_rate": "240p"},
            {"shutter_mode": "ECS_ONLY"},
            {"exposure_step": "0.1EV"},
            {"stored_speed_slot": "1/33"},
        ]
        for kwargs in cases:
            ev = evaluate_independent_shutter_mode_and_angle_range(**kwargs)
            self.assertFalse(ev.valid)
            self.assertEqual(ev.backup_bin_writes, 0)

    # ------------------------------------------------------------------
    # Group D: Pillar 3 — Ver. 6.01 vs Ver. 7.00/7.02 User LUT Split
    # ------------------------------------------------------------------

    def test_37_donor_and_clean_room_lut_generation_split_markers_mutually_exclusive(self) -> None:
        for cr in (True, False):
            rep = analyze_realhw_fan_pwm_shutter_angle_and_lut_601_702_split(clean_room=cr)
            p3 = rep.pillar_3_lut_601_702_split
            self.assertTrue(p3.passed)
            for k, v in p3.fx3_702_lut_exclusive_hits.items():
                self.assertGreaterEqual(v, 1, f"missing FX3 7.02 LUT marker {k}")
                self.assertEqual(p3.fx3_702_cross_pollution_in_fx6[k], 0)
            for k in APPFW_FX6_601_EXCLUSIVE_LUT_MARKERS_P197:
                self.assertGreaterEqual(p3.fx6_601_lut_exclusive_hits[k], 1)
                self.assertEqual(p3.fx6_702_cross_pollution_in_fx3[k], 0)

    def test_38_serialize_user_lut_slot_header_v1_48b_vs_v2_64b(self) -> None:
        b1, s1 = serialize_user_lut_slot_header(
            schema_id=LUT_SLOT_SCHEMA_LEGACY_LE_601_P197,
            slot_index=1,
            lut_3d_size=17,
            title_ascii="LegacyDiadem601",
        )
        b2, s2 = serialize_user_lut_slot_header(
            schema_id=LUT_SLOT_SCHEMA_OPT_GE_700_P197,
            slot_index=16,
            lut_3d_size=33,
            title_ascii="Opt702WithAEOffset",
            ae_level_offset_thirds=6,
            embed_lut_enabled=True,
        )
        self.assertEqual(len(b1), LUT_SLOT_V1_RECORD_BYTES_P197)
        self.assertEqual(s1.magic_ascii, "UL61")
        self.assertIsNone(s1.ae_level_offset_thirds)
        self.assertIsNone(s1.embed_lut_enabled)

        self.assertEqual(len(b2), LUT_SLOT_V2_RECORD_BYTES_P197)
        self.assertEqual(s2.magic_ascii, "UL70")
        self.assertEqual(s2.ae_level_offset_thirds, 6)
        self.assertTrue(s2.embed_lut_enabled)

    def test_39_serialize_user_lut_slot_header_validates_bounds(self) -> None:
        with self.assertRaises(ValueError):
            serialize_user_lut_slot_header(
                schema_id=LUT_SLOT_SCHEMA_OPT_GE_700_P197, slot_index=0
            )
        with self.assertRaises(ValueError):
            serialize_user_lut_slot_header(
                schema_id=LUT_SLOT_SCHEMA_OPT_GE_700_P197, slot_index=17
            )
        with self.assertRaises(ValueError):
            serialize_user_lut_slot_header(
                schema_id=LUT_SLOT_SCHEMA_OPT_GE_700_P197, lut_3d_size=65
            )
        with self.assertRaises(ValueError):
            serialize_user_lut_slot_header(
                schema_id=LUT_SLOT_SCHEMA_OPT_GE_700_P197, ae_level_offset_thirds=7
            )
        with self.assertRaises(ValueError):
            serialize_user_lut_slot_header(schema_id="UNKNOWN_SCHEMA")

    def test_40_stock_702_deserializer_detects_601_v1_slot_corruption_and_accepts_v2(self) -> None:
        v1_pkt, _ = serialize_user_lut_slot_header(
            schema_id=LUT_SLOT_SCHEMA_LEGACY_LE_601_P197, slot_index=3
        )
        ok_v1, reason_v1 = verify_stock_702_user_lut_slot_deserialization(v1_pkt)
        self.assertFalse(ok_v1)
        self.assertEqual(reason_v1, "LUT_GENERATION_SPLIT_601_TO_702_DESERIALIZE_CORRUPTION")

        v2_pkt, _ = serialize_user_lut_slot_header(
            schema_id=LUT_SLOT_SCHEMA_OPT_GE_700_P197, slot_index=3, ae_level_offset_thirds=2
        )
        ok_v2, reason_v2 = verify_stock_702_user_lut_slot_deserialization(v2_pkt)
        self.assertTrue(ok_v2)
        self.assertEqual(reason_v2, "STOCK_702_V2_OPT_LUT_SLOT_DESERIALIZED_OK")

    def test_41_stock_702_deserializer_rejects_bad_length_magic_version_and_crc32(self) -> None:
        ok_len, r_len = verify_stock_702_user_lut_slot_deserialization(b"short")
        self.assertFalse(ok_len)
        self.assertEqual(r_len, "INVALID_V2_SLOT_LENGTH_5")

        ok_mag, r_mag = verify_stock_702_user_lut_slot_deserialization(b"XXXX" + b"\x00" * 60)
        self.assertFalse(ok_mag)
        self.assertEqual(r_mag, "INVALID_V2_SLOT_MAGIC")

        old_ver_pkt = LUT_SLOT_V2_MAGIC_BYTES_P197 + struct.pack("<H", 0x0601) + b"\x00" * 58
        ok_ver, r_ver = verify_stock_702_user_lut_slot_deserialization(old_ver_pkt)
        self.assertFalse(ok_ver)
        self.assertEqual(r_ver, "LEGACY_PRE_700_LUT_SLOT_VERSION_0x0601")

        v2_pkt, _ = serialize_user_lut_slot_header(
            schema_id=LUT_SLOT_SCHEMA_OPT_GE_700_P197, slot_index=2
        )
        bad_crc_pkt = v2_pkt[:-1] + bytes([v2_pkt[-1] ^ 0xFF])
        ok_crc, r_crc = verify_stock_702_user_lut_slot_deserialization(bad_crc_pkt)
        self.assertFalse(ok_crc)
        self.assertEqual(r_crc, "V2_SLOT_CRC32_MISMATCH")

    def test_42_direct_fx6_601_write_to_p2_setting_user1_to_user16_blocked(self) -> None:
        for slot in (1, 8, 16):
            ev = evaluate_user_lut_601_vs_702_binary_split_firewall(
                writer_firmware="FX6_6.01",
                host_reader_firmware="FX3_7.02",
                slot_index=slot,
                target_storage_path=f"p2:/setting/User{slot}.lutslot",
                lifecycle_stage="H2",
            )
            self.assertFalse(ev.valid)
            self.assertTrue(ev.generation_split_detected)
            self.assertTrue(ev.direct_p2_setting_write_blocked)
            self.assertTrue(ev.stock_702_lut_deserialize_corrupted)
            self.assertTrue(ev.stock_702_lut_corruption_prevented)
            self.assertEqual(ev.p2_setting_mutation_bytes, 0)
            self.assertEqual(ev.calibration_mutation_bytes, 0)
            self.assertTrue(ev.h0_equals_h3)
            self.assertEqual(ev.status, "BLOCKED_CROSS_GEN_601_TO_702_P2_SETTING_WRITE")

    def test_43_same_gen_702_direct_p2_setting_write_still_blocked_by_zero_write_lock(self) -> None:
        ev = evaluate_user_lut_601_vs_702_binary_split_firewall(
            writer_firmware="FX3_7.02",
            host_reader_firmware="FX3_7.02",
            slot_index=1,
            target_storage_path="p2:/setting/User1.lutslot",
            lifecycle_stage="H0",
        )
        self.assertFalse(ev.valid)
        self.assertFalse(ev.generation_split_detected)
        self.assertTrue(ev.direct_p2_setting_write_blocked)
        self.assertEqual(ev.status, "BLOCKED_PERSISTENT_P2_SETTING_WRITE")

    def test_44_stage_b_fx6_601_redirected_to_volatile_fx6_lut_overlay_all_16_slots(self) -> None:
        for slot in range(1, 17):
            ev = evaluate_user_lut_601_vs_702_binary_split_firewall(
                writer_firmware="FX6_6.01",
                host_reader_firmware="FX3_7.02",
                slot_index=slot,
                target_storage_path=f"{VOLATILE_FX6_LUT_OVERLAY_DIR_P197}/User{slot}.lutslot",
                lifecycle_stage="H2",
            )
            self.assertTrue(ev.valid)
            self.assertEqual(ev.slot_label, f"User{slot}")
            self.assertTrue(ev.generation_split_detected)
            self.assertTrue(ev.redirected_to_volatile_overlay)
            self.assertFalse(ev.stock_702_lut_deserialize_corrupted)
            self.assertTrue(ev.h0_equals_h3)
            self.assertEqual(ev.p2_setting_mutation_bytes, 0)
            self.assertEqual(ev.bridge_class, BRIDGE_CLASS_SHIM_TRANSLATED)

    def test_45_cross_gen_601_lut_write_to_non_overlay_sd_path_rejected(self) -> None:
        ev = evaluate_user_lut_601_vs_702_binary_split_firewall(
            writer_firmware="FX6_6.01",
            host_reader_firmware="FX3_7.02",
            slot_index=2,
            target_storage_path="/mnt/sd/Private/Sony/PRO/LUT/User2.lutslot",
            lifecycle_stage="H2",
        )
        self.assertFalse(ev.valid)
        self.assertEqual(ev.status, "CROSS_GEN_601_LUT_NON_OVERLAY_REJECTED")

    def test_46_h0_h1_h2_h3_lifecycle_preserves_p2_setting_sha256_bit_exact(self) -> None:
        custom_h0 = "a" * 64
        for stage in ("H0", "H1", "H2", "H3"):
            ev = evaluate_user_lut_601_vs_702_binary_split_firewall(
                writer_firmware="FX6_6.01" if stage == "H2" else "FX3_7.02",
                host_reader_firmware="FX3_7.02",
                slot_index=4,
                target_storage_path=f"{VOLATILE_FX6_LUT_OVERLAY_DIR_P197}/User4_{stage}.lutslot",
                lifecycle_stage=stage,
                h0_p2_setting_sha256=custom_h0,
            )
            self.assertTrue(ev.valid)
            self.assertEqual(ev.h0_p2_setting_sha256, custom_h0)
            self.assertEqual(ev.h3_p2_setting_sha256, custom_h0)
            self.assertTrue(ev.h0_equals_h3)

    def test_47_lut_split_firewall_rejects_invalid_firmware_slot_or_stage(self) -> None:
        self.assertFalse(
            evaluate_user_lut_601_vs_702_binary_split_firewall(writer_firmware="FX9_1.0").valid
        )
        self.assertFalse(
            evaluate_user_lut_601_vs_702_binary_split_firewall(
                host_reader_firmware="VENICE_2.0"
            ).valid
        )
        self.assertFalse(
            evaluate_user_lut_601_vs_702_binary_split_firewall(slot_index=0).valid
        )
        self.assertFalse(
            evaluate_user_lut_601_vs_702_binary_split_firewall(slot_index=17).valid
        )
        self.assertFalse(
            evaluate_user_lut_601_vs_702_binary_split_firewall(lifecycle_stage="H9").valid
        )

    # ------------------------------------------------------------------
    # Group E: Pillar 4, Matrix, Bounded Helpers, Exports & CLI (41/41)
    # ------------------------------------------------------------------

    def test_48_write_guard_blocks_all_persistent_emmc_p2_backup_cpapp_and_nor_targets(self) -> None:
        forbidden_targets = (
            "p2:/setting/User1.lutslot",
            "p2:/setting/Backup.bin",
            "/setting/UserLutSlot0.bin",
            "/dev/nflasha2",
            "/dev/cnflasha1",
            "/dev/mmcblk0p2",
            "p8:/CPAPP-B.BIN",
            "/tmp/sneaky/Backup.bin",
            "/tmp/sneaky/cpapp-b.bin",
            "/mnt/sd/BODYDATA.DAT",
            "/mnt/sd/CAMSET01.DAT",
            "spi_nor:loader_nor.bin",
            "sector0:mbr.bin",
            "/etc/passwd",
        )
        for tgt in forbidden_targets:
            res = evaluate_phase197_write_guard(tgt)
            self.assertFalse(res.valid, f"expected {tgt!r} to be blocked")
            self.assertTrue(res.persistent_write_blocked)
            self.assertFalse(res.persistent_emmc_writes_authorized)
            self.assertFalse(res.spi_nor_write_authorized)
            self.assertFalse(res.el3_payload_transmit_authorized)
            self.assertEqual(res.physical_usb_packets_emitted, 0)

    def test_49_write_guard_allows_volatile_overlay_ram_and_ext_cube_paths(self) -> None:
        allowed_targets = (
            "/tmp/fx6_lut_overlay/User1.lutslot",
            "/tmp/shutter_angle_shadow.json",
            "ram://bk4_shutter_slot_shadow",
            "memfd:fx6_lut_v1_table",
            "/mnt/sd/Private/Sony/PRO/LUT/Cine709.cube",
            "/mnt/cfexpress_a/LUT/Look1.cube",
        )
        for tgt in allowed_targets:
            res = evaluate_phase197_write_guard(tgt)
            self.assertTrue(res.valid, f"expected {tgt!r} to be allowed")
            self.assertTrue(res.volatile_or_ext_allowed)
            self.assertFalse(res.persistent_write_blocked)
            self.assertFalse(res.persistent_emmc_writes_authorized)

    def test_50_compat_matrix_has_12_touchpoints_and_all_4_bridge_classes(self) -> None:
        mat = build_phase197_compat_matrix()
        self.assertEqual(mat.total_touchpoints, 12)
        self.assertEqual(len(mat.touchpoints), 12)
        self.assertEqual(sum(mat.class_counts.values()), 12)
        for cls in VALID_BRIDGE_CLASSES:
            self.assertGreaterEqual(mat.class_counts[cls], 1, f"missing class {cls}")
        self.assertEqual(mat.pillar_counts["PILLAR_1_FAN_PWM_THERMAL"], 4)
        self.assertEqual(mat.pillar_counts["PILLAR_2_SHUTTER_SPEED_ANGLE"], 4)
        self.assertEqual(mat.pillar_counts["PILLAR_3_LUT_601_VS_702_SPLIT"], 4)

    def test_51_bounded_helper_edge_cases_short_bk4_and_bad_uxc_magic(self) -> None:
        short_bk4 = mod_p197._parse_bk4_header_bytes(
            b"short",
            file_bytes=5,
            binary_name="Backup.bin",
            body_label="TEST",
            source_mode="CLEAN_ROOM_SYNTHETIC",
        )
        self.assertFalse(short_bk4.bk4_magic_valid)
        self.assertEqual(short_bk4.rec0_subsystems, 0)

        bad_uxc = mod_p197._scan_uxc_buf_clean_room(
            b"BAD!" + b"Fan Control\x00Auto1\x00",
            pack_name="bad.uxc",
            body_label="TEST",
            required_tokens=("Fan Control",),
            forbidden_tokens=("Auto1",),
        )
        self.assertFalse(bad_uxc.uxc_magic_valid)
        self.assertEqual(bad_uxc.required_token_hits["Fan Control"], 1)
        self.assertEqual(bad_uxc.forbidden_auto12_hits["Auto1"], 1)

        fixtures = build_clean_room_realhw_fan_pwm_shutter_lut_split_fixtures()
        self.assertEqual(len(fixtures), 8)
        for shared_tok in APPFW_SHARED_FAN_SHUTTER_MARKERS_P197:
            self.assertIn(shared_tok.encode("ascii"), fixtures["fx3_appfw"])
            self.assertIn(shared_tok.encode("ascii"), fixtures["fx6_appfw"])
        for fx3_only in APPFW_FX3_702_EXCLUSIVE_MARKERS_P197:
            self.assertIn(fx3_only.encode("ascii"), fixtures["fx3_appfw"])

    def test_52_package_init_exports_phase197_symbols_cleanly(self) -> None:
        expected_symbols = (
            "PHASE_197_SCHEMA",
            "PHASE_197_VERSION",
            "Pillar1Fx3FanPwmAndThermalReport",
            "Pillar2IndependentShutterAngleReport",
            "Pillar3Lut601Vs702SplitReport",
            "Pillar4Phase197WriteGuardAndMatrixReport",
            "RealhwFanPwmShutterAngleAndLut601702SplitReport",
            "analyze_realhw_fan_pwm_shutter_angle_and_lut_601_702_split",
            "realhw_fan_pwm_shutter_angle_and_lut_601_702_split_report_to_dict",
        )
        for sym in expected_symbols:
            self.assertIn(sym, pkg.__all__)
            self.assertTrue(hasattr(pkg, sym))

    def test_53_cli_subcommand_clean_room_json_exit_0(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cli_main(["audit-realhw-fan-pwm-shutter-lut-split", "--clean-room", "--json"])
        self.assertEqual(rc, 0)
        parsed = json.loads(buf.getvalue())
        self.assertEqual(parsed["schema_version"], PHASE_197_SCHEMA)
        self.assertEqual(parsed["auditor_index"], "41/41")
        self.assertEqual(parsed["mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(parsed["all_checks_passed"])

    def test_54_cli_subcommand_auto_mode_json_exit_0_under_ceiling(self) -> None:
        t0 = time.monotonic()
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cli_main(["audit-realhw-fan-pwm-shutter-lut-split", "--json"])
        dt = time.monotonic() - t0
        self.assertLess(dt, 6.0)
        self.assertEqual(rc, 0)
        parsed = json.loads(buf.getvalue())
        self.assertTrue(parsed["all_checks_passed"])
        self.assertEqual(parsed["raw_firmware_bytes_leaked"], 0)

    def test_55_run_audit_all_wires_41st_auditor_and_passes(self) -> None:
        summary = run_audit_all(clean_room=True)
        self.assertTrue(summary["all_checks_passed"])
        self.assertIn("realhw_fan_pwm_shutter_angle_and_lut_601_702_split_audit", summary)
        sub = summary["realhw_fan_pwm_shutter_angle_and_lut_601_702_split_audit"]
        self.assertTrue(sub["all_checks_passed"])
        self.assertEqual(sub["auditor_index"], "41/41")
        audit_keys = [k for k in summary if k.endswith("_audit")]
        self.assertGreaterEqual(len(audit_keys), 41)


if __name__ == "__main__":
    unittest.main()
