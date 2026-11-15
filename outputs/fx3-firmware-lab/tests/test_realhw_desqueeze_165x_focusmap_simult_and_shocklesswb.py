"""Phase 205 Dual-Mode Unit Tests (54 tests) — 43rd Firmware Auditor (43/43):
Real-Hardware `ILME-FX3` (`Ver. 7.02`) `[De-Squeeze Display]` (`1.6x = 1.65x` &
4 Hard Locks / HDMI RAW Bypass), External `M&C Focus Map` (`>=150fps` Cutoff) &
`[Simult. + Auto Switch]` / `[Shockless WB]` Auditor.
"""

from __future__ import annotations

import ast
import io
import json
import os
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
    ALL_FX3_MOVIE_AND_SQ_FPS_P205,
    APPFW_FX3_702_EXCLUSIVE_MARKERS_P205,
    APPFW_FX6_601_EXCLUSIVE_MARKERS_P205,
    APPFW_SHARED_WAVE27_MARKERS_P205,
    BRIDGE_CLASS_HARD_WRITE_PROTECTED,
    BRIDGE_CLASS_MASKED_ABSENT_HW,
    BRIDGE_CLASS_NATIVE_PASSTHROUGH,
    BRIDGE_CLASS_SHIM_TRANSLATED,
    CINEMASCOPE_TARGET_ASPECT_P205,
    CPAPP_BOUNDED_HEAD_BYTES_P205,
    CPAPP_BOUNDED_TAIL_BYTES_P205,
    CPAPP_FX3_FOCUSMAP_MARKERS_P205,
    CPAPP_SHARED_MARKERS_P205,
    CTEMP_FILTER_MAX_KELVIN_P205,
    CTEMP_FILTER_MIN_KELVIN_P205,
    DESQUEEZE_EFFECTIVE_HORIZONTAL_SCALE_P205,
    DESQUEEZE_FIVE_SUPPRESSION_CONDITIONS_P205,
    DESQUEEZE_FOUR_HARD_LOCKED_SETTINGS_P205,
    DONOR_COLD_SCAN_BUDGET_SEC_P205,
    EXPECTED_FX3_APPFW_BYTES_P205,
    EXPECTED_FX3_CPAPP_BYTES_P205,
    EXPECTED_FX3_UXC_EN_F_BYTES_P205,
    EXPECTED_FX6_APPFW_BYTES_P205,
    EXPECTED_FX6_CPAPP_BYTES_P205,
    EXPECTED_FX6_UXC_EN_BYTES_P205,
    FOCUS_MAP_HFR_CUTOFF_FPS_P205,
    FOCUS_MAP_MIN_FX3_FW_MAJOR_P205,
    FX3_700_PLUS_NEW_DESQUEEZE_STATES_P205,
    FX3_DESQUEEZE_DISPLAY_MENU_PATH_P205,
    FX3_DESQUEEZE_MENU_STATES_P205,
    FX3_LEGACY_PRE_700_DESQUEEZE_STATES_P205,
    FX3_SHOCKLESS_WB_MENU_PATH_P205,
    FX3_SHOCKLESS_WB_STATES_P205,
    FX6_FOCUS_MAP_LOW_FPS_CUTOFF_MAX_P205,
    IMMEDIATE_BYPASS_WB_TRIGGERS_P205,
    IN_BODY_FOCUS_MAP_CAPABLE_BODIES_P205,
    PHASE_205_SCHEMA,
    PHASE_205_VERSION,
    SHOCKLESS_WB_TAU_SECONDS_P205,
    SIMULT_CONTINUATION_MIN_FW_MAJOR_P205,
    UXC_FX3_EN_F_REQUIRED_TOKENS_P205,
    UXC_FX6_EN_REQUIRED_TOKENS_P205,
    VALID_BRIDGE_CLASSES,
    VOLATILE_WAVE27_OVERLAY_DIR_P205,
    WB_FINE_GRID_AXIS_LIMIT_P205,
    analyze_realhw_desqueeze_165x_focusmap_simult_and_shocklesswb,
    build_clean_room_realhw_desqueeze_focusmap_shocklesswb_fixtures,
    build_phase205_compat_matrix,
    compute_desqueezed_display_aspect_ratio,
    evaluate_desqueeze_display_165x_locks_and_suppression,
    evaluate_external_mc_focus_map_and_150fps_cutoff,
    evaluate_phase205_write_guard,
    evaluate_shockless_wb_and_ctemp_grid_bypass,
    evaluate_simult_recording_and_auto_switch_media,
    realhw_desqueeze_165x_focusmap_simult_and_shocklesswb_report_to_dict,
)
from fx3_firmware_lab import (  # noqa: E402
    realhw_desqueeze_165x_focusmap_simult_and_shocklesswb_auditor as mod_p205,
)
from fx3_firmware_lab.__main__ import main as cli_main  # noqa: E402
from fx3_firmware_lab.__main__ import run_audit_all  # noqa: E402


class TestRealhwDesqueeze165xFocusmapSimultAndShocklesswb(unittest.TestCase):
    """54 dual-mode unit tests for Phase 205 (43rd Auditor `43/43`)."""

    # ------------------------------------------------------------------
    # Group A: AST Zero-Write Proof, Cold/Warm SLA, Clean-Room & Safety
    # ------------------------------------------------------------------

    def test_01_ast_strictly_o_rdonly_and_zero_write_calls(self) -> None:
        src_path = Path(mod_p205.__file__)
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
        rep = analyze_realhw_desqueeze_165x_focusmap_simult_and_shocklesswb(
            clean_room=True
        )
        dt = time.monotonic() - t0
        self.assertLess(dt, 6.0)
        self.assertEqual(rep.schema_version, PHASE_205_SCHEMA)
        self.assertEqual(rep.phase_version, PHASE_205_VERSION)
        self.assertEqual(rep.auditor_index, "43/43")
        self.assertEqual(rep.mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(rep.all_checks_passed)
        self.assertEqual(rep.errors, ())

    def test_03_hard_safety_invariants_enforced_in_both_modes(self) -> None:
        for cr in (True, False):
            rep = analyze_realhw_desqueeze_165x_focusmap_simult_and_shocklesswb(
                clean_room=cr
            )
            self.assertTrue(rep.all_checks_passed)
            self.assertTrue(rep.o_rdonly_enforced)
            self.assertEqual(rep.raw_firmware_bytes_leaked, 0)
            self.assertFalse(rep.persistent_emmc_writes_authorized)
            self.assertFalse(rep.spi_nor_write_authorized)
            self.assertFalse(rep.el3_payload_transmit_authorized)
            self.assertEqual(rep.physical_usb_packets_emitted, 0)
            self.assertFalse(rep.in_body_focus_map_overlay_injected)
            self.assertEqual(rep.persistent_writes, 0)
            self.assertEqual(rep.calibration_mutation_bytes, 0)

    def test_04_auto_mode_donor_or_clean_room_cold_and_cached_sla(self) -> None:
        t0 = time.monotonic()
        rep1 = analyze_realhw_desqueeze_165x_focusmap_simult_and_shocklesswb(
            clean_room=False
        )
        dt1 = time.monotonic() - t0
        self.assertLess(dt1, 6.0)
        self.assertTrue(rep1.all_checks_passed)

        if os.environ.get("FX3_FX6_FORCE_CLEAN_ROOM") == "1":
            self.assertEqual(rep1.mode, "CLEAN_ROOM_SYNTHETIC")
        elif rep1.mode == "LOCAL_DONOR_RDONLY":
            self.assertEqual(
                rep1.donor_file_sizes["fx3_appfw"], EXPECTED_FX3_APPFW_BYTES_P205
            )
            self.assertEqual(
                rep1.donor_file_sizes["fx6_appfw"], EXPECTED_FX6_APPFW_BYTES_P205
            )
            self.assertEqual(
                rep1.donor_file_sizes["fx3_string_english_f_uxc"],
                EXPECTED_FX3_UXC_EN_F_BYTES_P205,
            )
            self.assertEqual(
                rep1.donor_file_sizes["fx6_string_english_uxc"],
                EXPECTED_FX6_UXC_EN_BYTES_P205,
            )
            self.assertEqual(
                rep1.donor_file_sizes["fx3_cpapp_b_bin"], EXPECTED_FX3_CPAPP_BYTES_P205
            )
            self.assertEqual(
                rep1.donor_file_sizes["fx6_cpapp_b_bin"], EXPECTED_FX6_CPAPP_BYTES_P205
            )
            rep2 = analyze_realhw_desqueeze_165x_focusmap_simult_and_shocklesswb(
                clean_room=False
            )
            self.assertTrue(rep2.cache_hit)
            self.assertLess(rep2.cold_or_cached_scan_elapsed_sec, 0.05)

    def test_05_cold_donor_scan_under_budget_when_donors_present(self) -> None:
        if os.environ.get("FX3_FX6_FORCE_CLEAN_ROOM") == "1":
            rep = analyze_realhw_desqueeze_165x_focusmap_simult_and_shocklesswb()
            self.assertEqual(rep.mode, "CLEAN_ROOM_SYNTHETIC")
            return
        mod_p205._DONOR_SCAN_CACHE_P205.clear()
        rep = analyze_realhw_desqueeze_165x_focusmap_simult_and_shocklesswb(
            clean_room=False
        )
        self.assertTrue(rep.all_checks_passed)
        if rep.mode == "LOCAL_DONOR_RDONLY":
            self.assertFalse(rep.cache_hit)
            self.assertLess(rep.cold_or_cached_scan_elapsed_sec, 0.50)
            self.assertEqual(DONOR_COLD_SCAN_BUDGET_SEC_P205, 0.15)

    def test_06_missing_donor_falls_back_to_clean_room_deterministically(self) -> None:
        with mock.patch.object(mod_p205, "resolve_donor_file", return_value=None):
            rep = analyze_realhw_desqueeze_165x_focusmap_simult_and_shocklesswb(
                clean_room=False,
            )
            self.assertEqual(rep.mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertTrue(rep.all_checks_passed)
            self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_07_env_var_force_clean_room_override(self) -> None:
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            rep = analyze_realhw_desqueeze_165x_focusmap_simult_and_shocklesswb(
                clean_room=False
            )
            self.assertEqual(rep.mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertTrue(rep.all_checks_passed)

    def test_08_clean_room_report_sha256_and_json_deterministic(self) -> None:
        r1 = analyze_realhw_desqueeze_165x_focusmap_simult_and_shocklesswb(
            clean_room=True
        )
        r2 = analyze_realhw_desqueeze_165x_focusmap_simult_and_shocklesswb(
            clean_room=True
        )
        self.assertEqual(r1.report_sha256, r2.report_sha256)
        self.assertEqual(len(r1.report_sha256), 64)
        d1 = realhw_desqueeze_165x_focusmap_simult_and_shocklesswb_report_to_dict(r1)
        d2 = realhw_desqueeze_165x_focusmap_simult_and_shocklesswb_report_to_dict(r2)
        d1.pop("cold_or_cached_scan_elapsed_sec", None)
        d2.pop("cold_or_cached_scan_elapsed_sec", None)
        self.assertEqual(json.dumps(d1, sort_keys=True), json.dumps(d2, sort_keys=True))

    def test_09_clean_room_fixtures_contain_zero_raw_donor_slices(self) -> None:
        fx = build_clean_room_realhw_desqueeze_focusmap_shocklesswb_fixtures()
        self.assertEqual(
            set(fx.keys()),
            {
                "fx3_appfw",
                "fx6_appfw",
                "fx3_uxc_en_f",
                "fx6_uxc_en",
                "fx3_cpapp",
                "fx6_cpapp",
            },
        )
        self.assertTrue(fx["fx3_appfw"].startswith(b"\x7fELF"))
        self.assertTrue(fx["fx6_appfw"].startswith(b"\x7fELF"))
        self.assertTrue(fx["fx3_uxc_en_f"].startswith(b"uxd\x07"))
        self.assertTrue(fx["fx6_uxc_en"].startswith(b"uxd\x07"))
        self.assertLess(len(fx["fx3_cpapp"]), 4096)

    # ------------------------------------------------------------------
    # Group B: Pillar 1 — `[De-Squeeze Display]` (`1.6x=1.65x`, 4 Locks, 5 Bypasses)
    # ------------------------------------------------------------------

    def test_10_desqueeze_menu_states_and_165x_scale_table(self) -> None:
        self.assertEqual(
            FX3_DESQUEEZE_DISPLAY_MENU_PATH_P205,
            "MENU -> Setup -> [Display Option] -> [De-Squeeze Display]",
        )
        self.assertEqual(
            FX3_DESQUEEZE_MENU_STATES_P205, ("Off", "1.3x", "1.5x", "1.6x", "2.0x")
        )
        self.assertEqual(FX3_LEGACY_PRE_700_DESQUEEZE_STATES_P205, ("Off", "1.3x", "2.0x"))
        self.assertEqual(FX3_700_PLUS_NEW_DESQUEEZE_STATES_P205, ("1.5x", "1.6x"))
        self.assertAlmostEqual(DESQUEEZE_EFFECTIVE_HORIZONTAL_SCALE_P205["1.6x"], 1.65)
        self.assertAlmostEqual(CINEMASCOPE_TARGET_ASPECT_P205, 2.39)

    def test_11_compute_desqueezed_display_aspect_ratio_16x_is_165x(self) -> None:
        scale_16, aspect_16 = compute_desqueezed_display_aspect_ratio("1.6x", (16, 9))
        self.assertAlmostEqual(scale_16, 1.65)
        self.assertAlmostEqual(aspect_16, round((16.0 / 9.0) * 1.65, 4))

        scale_144, aspect_144 = compute_desqueezed_display_aspect_ratio("1.6x", (36, 25))
        self.assertAlmostEqual(scale_144, 1.65)
        self.assertAlmostEqual(aspect_144, round(1.44 * 1.65, 4))

        with self.assertRaises(ValueError):
            compute_desqueezed_display_aspect_ratio("1.8x")
        with self.assertRaises(ValueError):
            compute_desqueezed_display_aspect_ratio("1.6x", (0, 9))

    def test_12_desqueeze_16x_enforces_165x_and_all_4_hard_locks(self) -> None:
        res = evaluate_desqueeze_display_165x_locks_and_suppression(menu_state="1.6x")
        self.assertTrue(res.valid)
        self.assertAlmostEqual(res.nominal_label_ratio, 1.6)
        self.assertAlmostEqual(res.configured_horizontal_scale, 1.65)
        self.assertAlmostEqual(res.effective_horizontal_scale, 1.65)
        self.assertTrue(res.cinemascope_165x_stretch_applied)
        self.assertTrue(res.four_hard_locks_active)
        self.assertEqual(res.locked_settings, DESQUEEZE_FOUR_HARD_LOCKED_SETTINGS_P205)
        self.assertEqual(res.bridge_class, BRIDGE_CLASS_SHIM_TRANSLATED)

    def test_13_desqueeze_13x_15x_20x_active_scales_verified(self) -> None:
        for state, expected_scale in (("1.3x", 1.30), ("1.5x", 1.50), ("2.0x", 2.00)):
            res = evaluate_desqueeze_display_165x_locks_and_suppression(menu_state=state)
            self.assertTrue(res.valid)
            self.assertAlmostEqual(res.effective_horizontal_scale, expected_scale)
            self.assertFalse(res.cinemascope_165x_stretch_applied)
            self.assertTrue(res.four_hard_locks_active)

    def test_14_desqueeze_off_unlocks_autofocus_steadyshot_and_face_metering(self) -> None:
        res = evaluate_desqueeze_display_165x_locks_and_suppression(
            menu_state="Off",
            focus_mode="AF-C",
            focus_area="Tracking: Spot M",
            steady_shot="Active",
            face_priority_in_multi_metering="On",
        )
        self.assertTrue(res.valid)
        self.assertFalse(res.four_hard_locks_active)
        self.assertAlmostEqual(res.effective_horizontal_scale, 1.0)
        self.assertEqual(res.status, "OK_DESQUEEZE_OFF_AF_AND_IBIS_UNLOCKED")

    def test_15_desqueeze_each_of_4_hard_locks_rejects_violation_individually(self) -> None:
        r_fm = evaluate_desqueeze_display_165x_locks_and_suppression(
            menu_state="1.6x", focus_mode="AF-C"
        )
        self.assertFalse(r_fm.valid)
        self.assertTrue(any("FOCUS_MODE_MUST_BE_MF" in e for e in r_fm.errors))

        r_fa = evaluate_desqueeze_display_165x_locks_and_suppression(
            menu_state="1.6x", focus_area="Spot: M"
        )
        self.assertFalse(r_fa.valid)
        self.assertTrue(any("FOCUS_AREA_MUST_BE_WIDE" in e for e in r_fa.errors))

        r_ss = evaluate_desqueeze_display_165x_locks_and_suppression(
            menu_state="1.6x", steady_shot="Active"
        )
        self.assertFalse(r_ss.valid)
        self.assertTrue(any("STEADYSHOT_MUST_BE_OFF" in e for e in r_ss.errors))

        r_fp = evaluate_desqueeze_display_165x_locks_and_suppression(
            menu_state="1.6x", face_priority_in_multi_metering="On"
        )
        self.assertFalse(r_fp.valid)
        self.assertTrue(any("FACE_PRIORITY_MULTI_MUST_BE_OFF" in e for e in r_fp.errors))

    def test_16_desqueeze_suppressed_by_hdmi_raw_output_on(self) -> None:
        res = evaluate_desqueeze_display_165x_locks_and_suppression(
            menu_state="1.6x",
            hdmi_raw_output="On",
        )
        self.assertTrue(res.valid)
        self.assertTrue(res.desqueeze_suppressed)
        self.assertIn("HDMI_RAW_OUTPUT_ON", res.suppression_reasons)
        self.assertAlmostEqual(res.effective_horizontal_scale, 1.0)
        self.assertFalse(res.cinemascope_165x_stretch_applied)

    def test_17_desqueeze_suppressed_by_off_hdmi_only_and_forces_hdmi_info_off(self) -> None:
        res = evaluate_desqueeze_display_165x_locks_and_suppression(
            menu_state="2.0x",
            rec_media_dur_hdmi_output="Off(HDMI Only)",
            hdmi_info_display="On",
        )
        self.assertTrue(res.valid)
        self.assertTrue(res.desqueeze_suppressed)
        self.assertIn(
            "REC_MEDIA_DUR_HDMI_OUTPUT_OFF_HDMI_ONLY", res.suppression_reasons
        )
        self.assertTrue(res.hdmi_info_display_forced_off)
        self.assertEqual(res.effective_hdmi_info_display, "Off")
        self.assertAlmostEqual(res.effective_horizontal_scale, 1.0)

    def test_18_desqueeze_suppressed_by_log_off_remote_shooting_and_photo_mode(self) -> None:
        self.assertEqual(len(DESQUEEZE_FIVE_SUPPRESSION_CONDITIONS_P205), 5)
        r_log = evaluate_desqueeze_display_165x_locks_and_suppression(
            menu_state="1.3x", log_shooting="Off"
        )
        self.assertTrue(r_log.desqueeze_suppressed)
        self.assertEqual(r_log.suppression_reasons, ("LOG_SHOOTING_OFF",))

        r_rem = evaluate_desqueeze_display_165x_locks_and_suppression(
            menu_state="1.5x", remote_shooting_active=True
        )
        self.assertTrue(r_rem.desqueeze_suppressed)
        self.assertEqual(r_rem.suppression_reasons, ("REMOTE_SHOOTING_ACTIVE",))

        r_pho = evaluate_desqueeze_display_165x_locks_and_suppression(
            menu_state="1.6x", capture_mode="Photo"
        )
        self.assertTrue(r_pho.desqueeze_suppressed)
        self.assertEqual(r_pho.suppression_reasons, ("PHOTO_STILL_CAPTURE_MODE",))

    def test_19_stage_b_forced_desqueeze_during_suppression_rejected(self) -> None:
        res = evaluate_desqueeze_display_165x_locks_and_suppression(
            menu_state="1.6x",
            hdmi_raw_output="On",
            stage_b_force_desqueeze_during_suppression=True,
        )
        self.assertFalse(res.valid)
        self.assertTrue(
            any("STAGE_B_FORBIDDEN_DESQUEEZE_OVERRIDE" in e for e in res.errors)
        )

    def test_20_pre_700_firmware_rejects_15x_and_16x_but_allows_13x_and_20x(self) -> None:
        for st in ("1.5x", "1.6x"):
            rej = evaluate_desqueeze_display_165x_locks_and_suppression(
                menu_state=st, firmware_version="6.01"
            )
            self.assertFalse(rej.valid)
            self.assertTrue(
                any("REQUIRES_FX3_FW_7_00_OR_NEWER" in e for e in rej.errors)
            )
        for st in ("1.3x", "2.0x"):
            ok = evaluate_desqueeze_display_165x_locks_and_suppression(
                menu_state=st, firmware_version="6.01"
            )
            self.assertTrue(ok.valid)

    def test_21_desqueeze_invalid_parameters_rejected(self) -> None:
        res = evaluate_desqueeze_display_165x_locks_and_suppression(
            menu_state="1.8x",
            firmware_version="bad_fw",
            focus_mode="DMF",
            focus_area="InvalidArea",
            steady_shot="DynamicActive",
            face_priority_in_multi_metering="Auto",
            hdmi_raw_output="Maybe",
            rec_media_dur_hdmi_output="InvalidHDMI",
            hdmi_info_display="Partial",
            log_shooting="SLog2",
            capture_mode="Burst",
        )
        self.assertFalse(res.valid)
        self.assertEqual(len(res.errors), 11)

    # ------------------------------------------------------------------
    # Group C: Pillar 2 — External `M&C Focus Map` & `>=150fps` Cutoff
    # ------------------------------------------------------------------

    def test_22_fx3_lacks_inbody_focus_map_menu_in_donor_and_clean_room(self) -> None:
        self.assertEqual(
            IN_BODY_FOCUS_MAP_CAPABLE_BODIES_P205, ("ILME-FX30", "ILME-FX6")
        )
        for cr in (True, False):
            rep = analyze_realhw_desqueeze_165x_focusmap_simult_and_shocklesswb(
                clean_room=cr
            )
            p2 = rep.pillar_2_external_mc_focus_map
            self.assertTrue(p2.passed)
            for k, v in p2.fx6_appfw_inbody_focusmap_hits_in_fx3.items():
                self.assertEqual(v, 0, f"FX3 must have 0 hits for {k}")
            for k, v in p2.fx6_appfw_inbody_focusmap_hits_in_fx6.items():
                self.assertGreaterEqual(v, 1, f"FX6 must have >=1 hit for {k}")
            self.assertGreaterEqual(
                p2.fx3_appfw_focusmap_hits["to_remote_event_focus_map"], 1
            )

    def test_23_fx3_stage_b_inbody_focus_map_overlay_injection_hard_blocked(self) -> None:
        r1 = evaluate_external_mc_focus_map_and_150fps_cutoff(
            camera_body="ILME-FX3",
            requested_render_target="FX3_IN_BODY_LCD_OSD_OVERLAY",
        )
        self.assertFalse(r1.valid)
        self.assertFalse(r1.in_body_focus_map_menu_present)
        self.assertFalse(r1.in_body_focus_map_overlay_injected)
        self.assertEqual(r1.bridge_class, BRIDGE_CLASS_MASKED_ABSENT_HW)

        r2 = evaluate_external_mc_focus_map_and_150fps_cutoff(
            camera_body="ILME-FX3",
            requested_render_target="EXTERNAL_MONITOR_AND_CONTROL_APP",
            stage_b_inject_in_body_focus_map_overlay=True,
        )
        self.assertFalse(r2.valid)
        self.assertTrue(
            any("FX3_ABSENT_IN_BODY_FOCUS_MAP" in e for e in r2.errors)
        )

    def test_24_fx30_and_fx6_permit_inbody_focus_map_render_target(self) -> None:
        for body, fw in (("ILME-FX30", "5.00"), ("ILME-FX6", "6.01")):
            res = evaluate_external_mc_focus_map_and_150fps_cutoff(
                camera_body=body,
                firmware_version=fw,
                requested_render_target="IN_BODY_NATIVE_LCD_EVF",
                sensor_fps=24,
            )
            self.assertTrue(res.valid)
            self.assertTrue(res.in_body_focus_map_menu_present)
            self.assertTrue(res.external_mc_focus_map_available)

    def test_25_fx3_external_mc_focus_map_150fps_exact_cutoff_boundary(self) -> None:
        self.assertEqual(FOCUS_MAP_HFR_CUTOFF_FPS_P205, 150)
        for ok_fps in (24, 60, 100, 120, 149):
            ok = evaluate_external_mc_focus_map_and_150fps_cutoff(sensor_fps=ok_fps)
            self.assertTrue(ok.valid)
            self.assertTrue(ok.external_mc_focus_map_available)
            self.assertFalse(ok.hfr_150fps_cutoff_triggered)

        for blocked_fps in (150, 200, 240):
            cut = evaluate_external_mc_focus_map_and_150fps_cutoff(
                sensor_fps=blocked_fps
            )
            self.assertTrue(cut.valid)
            self.assertFalse(cut.external_mc_focus_map_available)
            self.assertTrue(cut.hfr_150fps_cutoff_triggered)
            self.assertIn("BLOCKED_FPS_GE_150_HFR_CUTOFF", cut.cutoff_reasons)

    def test_26_fx3_allows_1_to_6_fps_unlike_fx6_low_fps_cutoff(self) -> None:
        self.assertEqual(FX6_FOCUS_MAP_LOW_FPS_CUTOFF_MAX_P205, 6)
        for low_fps in (1, 3, 6):
            r_fx3 = evaluate_external_mc_focus_map_and_150fps_cutoff(
                camera_body="ILME-FX3", sensor_fps=low_fps
            )
            self.assertTrue(r_fx3.external_mc_focus_map_available)
            self.assertTrue(r_fx3.fx3_low_fps_1_to_6_permitted)

            r_fx6 = evaluate_external_mc_focus_map_and_150fps_cutoff(
                camera_body="ILME-FX6", firmware_version="6.01", sensor_fps=low_fps
            )
            self.assertFalse(r_fx6.external_mc_focus_map_available)
            self.assertIn("BLOCKED_FX6_LOW_FPS_LE_6_CUTOFF", r_fx6.cutoff_reasons)

    def test_27_fx3_pre_600_fw_blocks_external_focus_map(self) -> None:
        self.assertEqual(FOCUS_MAP_MIN_FX3_FW_MAJOR_P205, 6)
        res = evaluate_external_mc_focus_map_and_150fps_cutoff(
            camera_body="ILME-FX3", firmware_version="5.00", sensor_fps=24
        )
        self.assertTrue(res.valid)
        self.assertFalse(res.external_mc_focus_map_available)
        self.assertIn("BLOCKED_FX3_REQUIRES_FW_6_00_OR_NEWER", res.cutoff_reasons)

    def test_28_focus_map_blocked_for_adapter_non_pdaf_uvc_and_playback(self) -> None:
        for lens in (
            "NO_LENS_ATTACHED",
            "MOUNT_ADAPTER_LA_EA5_OR_MANUAL",
            "NON_PDAF_LENS",
        ):
            r_lens = evaluate_external_mc_focus_map_and_150fps_cutoff(lens_state=lens)
            self.assertFalse(r_lens.external_mc_focus_map_available)
            self.assertTrue(
                any("BLOCKED_LENS_PDAF_UNAVAILABLE" in c for c in r_lens.cutoff_reasons)
            )

        r_uvc = evaluate_external_mc_focus_map_and_150fps_cutoff(
            usb_uvc_streaming_active=True
        )
        self.assertFalse(r_uvc.external_mc_focus_map_available)
        self.assertIn("BLOCKED_DURING_UVC_USB_STREAMING", r_uvc.cutoff_reasons)

        r_play = evaluate_external_mc_focus_map_and_150fps_cutoff(
            camera_operating_state="PLAYBACK"
        )
        self.assertFalse(r_play.external_mc_focus_map_available)
        self.assertIn("BLOCKED_DURING_IN_CAMERA_PLAYBACK", r_play.cutoff_reasons)

    def test_29_focus_map_invalid_inputs_rejected(self) -> None:
        res = evaluate_external_mc_focus_map_and_150fps_cutoff(
            camera_body="ILCE-7SM3",
            firmware_version="vX",
            requested_render_target="SDI_OUT",
            sensor_fps=0,
            lens_state="UNKNOWN_LENS",
            camera_operating_state="USB_MSC",
        )
        self.assertFalse(res.valid)
        self.assertEqual(len(res.errors), 6)

    # ------------------------------------------------------------------
    # Group D: Pillar 3 — `[Simult. + Auto Switch]` & `[Shockless WB]` Bypass
    # ------------------------------------------------------------------

    def test_30_simult_recording_both_slots_have_space_active_dual(self) -> None:
        res = evaluate_simult_recording_and_auto_switch_media(
            recording_media_mode="Simult. Recording",
            auto_switch_media="On",
            slot1_remaining_sec=600.0,
            slot2_remaining_sec=1200.0,
            elapsed_rec_sec=300.0,
        )
        self.assertTrue(res.valid)
        self.assertTrue(res.recording_continues)
        self.assertFalse(res.single_card_continuation_active)
        self.assertEqual(res.active_slots, ("Slot 1", "Slot 2"))
        self.assertEqual(res.frames_dropped, 0)

    def test_31_simult_auto_switch_on_slot1_exhausted_continues_on_slot2(self) -> None:
        self.assertEqual(SIMULT_CONTINUATION_MIN_FW_MAJOR_P205, 2)
        res = evaluate_simult_recording_and_auto_switch_media(
            firmware_version="7.02",
            recording_media_mode="Simult. Recording",
            auto_switch_media="On",
            slot1_remaining_sec=120.0,
            slot2_remaining_sec=1800.0,
            elapsed_rec_sec=300.0,
        )
        self.assertTrue(res.valid)
        self.assertTrue(res.recording_continues)
        self.assertTrue(res.single_card_continuation_active)
        self.assertFalse(res.strict_dual_backup_halt_enforced)
        self.assertEqual(res.active_slots, ("Slot 2",))
        self.assertEqual(res.frames_dropped, 0)
        self.assertEqual(res.recording_state, "SINGLE_CARD_CONTINUATION_ON_SLOT_2")

    def test_32_simult_auto_switch_on_slot2_exhausted_continues_on_slot1(self) -> None:
        res = evaluate_simult_recording_and_auto_switch_media(
            firmware_version="2.00",
            recording_media_mode="Simult. Recording",
            auto_switch_media="On",
            slot1_remaining_sec=1800.0,
            slot2_remaining_sec=90.0,
            elapsed_rec_sec=150.0,
        )
        self.assertTrue(res.valid)
        self.assertTrue(res.recording_continues)
        self.assertTrue(res.single_card_continuation_active)
        self.assertEqual(res.active_slots, ("Slot 1",))
        self.assertEqual(res.recording_state, "SINGLE_CARD_CONTINUATION_ON_SLOT_1")

    def test_33_simult_auto_switch_on_hotswap_fresh_card_resumes_dual_slot(self) -> None:
        res = evaluate_simult_recording_and_auto_switch_media(
            firmware_version="7.02",
            recording_media_mode="Simult. Recording",
            auto_switch_media="On",
            slot1_remaining_sec=100.0,
            slot2_remaining_sec=1800.0,
            elapsed_rec_sec=200.0,
            hot_swap_fresh_card_into_exhausted_slot=True,
        )
        self.assertTrue(res.valid)
        self.assertTrue(res.recording_continues)
        self.assertTrue(res.resumed_dual_slot_after_card_swap)
        self.assertFalse(res.single_card_continuation_active)
        self.assertEqual(res.active_slots, ("Slot 1", "Slot 2"))
        self.assertEqual(
            res.recording_state, "RESUMED_DUAL_SLOT_AFTER_FRESH_CARD_HOTSWAP"
        )

    def test_34_simult_auto_switch_off_strict_dual_parity_halts_on_one_card_full(
        self,
    ) -> None:
        res = evaluate_simult_recording_and_auto_switch_media(
            firmware_version="7.02",
            recording_media_mode="Simult. Recording",
            auto_switch_media="Off",
            slot1_remaining_sec=100.0,
            slot2_remaining_sec=1800.0,
            elapsed_rec_sec=100.0,
        )
        self.assertTrue(res.valid)
        self.assertFalse(res.recording_continues)
        self.assertTrue(res.strict_dual_backup_halt_enforced)
        self.assertFalse(res.single_card_continuation_active)
        self.assertEqual(res.active_slots, ())
        self.assertEqual(
            res.recording_state, "HALTED_STRICT_DUAL_PARITY_ONE_CARD_FULL"
        )

    def test_35_simult_pre_200_fw_halts_even_when_auto_switch_on(self) -> None:
        res = evaluate_simult_recording_and_auto_switch_media(
            firmware_version="1.01",
            recording_media_mode="Simult. Recording",
            auto_switch_media="On",
            slot1_remaining_sec=60.0,
            slot2_remaining_sec=600.0,
            elapsed_rec_sec=120.0,
        )
        self.assertTrue(res.valid)
        self.assertFalse(res.recording_continues)
        self.assertTrue(res.strict_dual_backup_halt_enforced)

    def test_36_simult_both_slots_full_halts_cleanly(self) -> None:
        res = evaluate_simult_recording_and_auto_switch_media(
            recording_media_mode="Simult. Recording",
            auto_switch_media="On",
            slot1_remaining_sec=100.0,
            slot2_remaining_sec=150.0,
            elapsed_rec_sec=200.0,
        )
        self.assertTrue(res.valid)
        self.assertFalse(res.recording_continues)
        self.assertEqual(res.recording_state, "HALTED_BOTH_SLOTS_FULL")

    def test_37_simult_missing_card_at_rec_start_triggers_2card_caution(self) -> None:
        res = evaluate_simult_recording_and_auto_switch_media(
            recording_media_mode="Simult. Recording",
            slot1_inserted=True,
            slot2_inserted=False,
        )
        self.assertFalse(res.valid)
        self.assertTrue(
            any(
                "CAUTION_ID_2CARD_REQUIRED_SIMULTANEOIUS_FOR_MOVIE_RECORD" in e
                for e in res.errors
            )
        )

    def test_38_single_slot1_relay_switch_to_slot2_and_invalid_inputs(self) -> None:
        relay = evaluate_simult_recording_and_auto_switch_media(
            recording_media_mode="Slot 1",
            auto_switch_media="On",
            slot1_remaining_sec=60.0,
            slot2_remaining_sec=600.0,
            elapsed_rec_sec=120.0,
        )
        self.assertTrue(relay.valid)
        self.assertTrue(relay.recording_continues)
        self.assertEqual(relay.active_slots, ("Slot 2",))
        self.assertEqual(relay.recording_state, "RELAY_SWITCHED_SLOT_1_TO_SLOT_2")

        inv = evaluate_simult_recording_and_auto_switch_media(
            firmware_version="bad",
            recording_media_mode="Slot 3",
            auto_switch_media="Maybe",
            slot1_remaining_sec=-5.0,
        )
        self.assertFalse(inv.valid)
        self.assertEqual(len(inv.errors), 4)

    def test_39_shockless_wb_states_and_all_frame_rates_24p_to_240fps(self) -> None:
        self.assertEqual(
            FX3_SHOCKLESS_WB_MENU_PATH_P205,
            "MENU -> Exposure/Color -> [White Balance] -> [Shockless WB]",
        )
        self.assertEqual(
            FX3_SHOCKLESS_WB_STATES_P205, ("Off", "1 (Fast)", "2", "3 (Slow)")
        )
        self.assertLess(
            SHOCKLESS_WB_TAU_SECONDS_P205["1 (Fast)"],
            SHOCKLESS_WB_TAU_SECONDS_P205["2"],
        )
        self.assertLess(
            SHOCKLESS_WB_TAU_SECONDS_P205["2"],
            SHOCKLESS_WB_TAU_SECONDS_P205["3 (Slow)"],
        )
        for fps in ALL_FX3_MOVIE_AND_SQ_FPS_P205:
            res = evaluate_shockless_wb_and_ctemp_grid_bypass(
                shockless_wb_setting="3 (Slow)",
                frame_rate_fps=fps,
                trigger_type="WB_MODE_SWITCH_PRESET_TO_CUSTOM",
            )
            self.assertTrue(res.valid)
            self.assertTrue(res.supported_at_all_fps)
            self.assertTrue(res.shockless_smoothing_applied)
            self.assertGreaterEqual(res.transition_frames, 1)

    def test_40_shockless_wb_off_switches_immediately_in_0_frames(self) -> None:
        res = evaluate_shockless_wb_and_ctemp_grid_bypass(
            shockless_wb_setting="Off",
            frame_rate_fps=59.94,
            trigger_type="WB_MODE_SWITCH_MEMORY_A_TO_B",
        )
        self.assertTrue(res.valid)
        self.assertFalse(res.shockless_smoothing_applied)
        self.assertFalse(res.immediate_bypass_triggered)
        self.assertEqual(res.transition_frames, 0)

    def test_41_shockless_wb_ctemp_kelvin_direct_edit_0_frame_immediate_bypass(
        self,
    ) -> None:
        self.assertIn("CTEMP_KELVIN_DIRECT_EDIT", IMMEDIATE_BYPASS_WB_TRIGGERS_P205)
        for swb in ("1 (Fast)", "2", "3 (Slow)"):
            res = evaluate_shockless_wb_and_ctemp_grid_bypass(
                shockless_wb_setting=swb,
                frame_rate_fps=240.0,
                trigger_type="CTEMP_KELVIN_DIRECT_EDIT",
                ctemp_kelvin=3200,
            )
            self.assertTrue(res.valid)
            self.assertFalse(res.shockless_smoothing_applied)
            self.assertTrue(res.immediate_bypass_triggered)
            self.assertAlmostEqual(res.tau_seconds, 0.0)
            self.assertEqual(res.transition_frames, 0)
            self.assertEqual(res.bridge_class, BRIDGE_CLASS_SHIM_TRANSLATED)

    def test_42_shockless_wb_ab_gm_fine_grid_shift_0_frame_immediate_bypass(
        self,
    ) -> None:
        self.assertIn("AB_GM_FINE_GRID_SHIFT", IMMEDIATE_BYPASS_WB_TRIGGERS_P205)
        res = evaluate_shockless_wb_and_ctemp_grid_bypass(
            shockless_wb_setting="3 (Slow)",
            frame_rate_fps=23.976,
            trigger_type="AB_GM_FINE_GRID_SHIFT",
            ab_grid_offset=-3.5,
            gm_grid_offset=2.25,
        )
        self.assertTrue(res.valid)
        self.assertFalse(res.shockless_smoothing_applied)
        self.assertTrue(res.immediate_bypass_triggered)
        self.assertEqual(res.transition_frames, 0)

    def test_43_shockless_wb_out_of_range_kelvin_grid_fps_rejected(self) -> None:
        self.assertEqual(CTEMP_FILTER_MIN_KELVIN_P205, 2500)
        self.assertEqual(CTEMP_FILTER_MAX_KELVIN_P205, 9900)
        self.assertAlmostEqual(WB_FINE_GRID_AXIS_LIMIT_P205, 7.0)
        res = evaluate_shockless_wb_and_ctemp_grid_bypass(
            shockless_wb_setting="4 (Ultra Slow)",
            frame_rate_fps=300.0,
            trigger_type="UNKNOWN_TRIGGER",
            ctemp_kelvin=10500,
            ab_grid_offset=8.0,
        )
        self.assertFalse(res.valid)
        self.assertEqual(len(res.errors), 5)

    # ------------------------------------------------------------------
    # Group E: Pillar 4 — Write Firewall, 12-Touchpoint Matrix, CLI & Exports
    # ------------------------------------------------------------------

    def test_44_write_guard_blocks_persistent_setting_backup_cpapp_lensfile_spinor(
        self,
    ) -> None:
        for p in (
            "p2:/setting/Backup.bin",
            "/setting/Backup.bin",
            "/dev/nflasha2",
            "/dev/mmcblk0p5",
            "p18:/lens/LENSFILE.BIN",
            "/firmware/CPAPP-B.BIN",
            "/firmware/cpapp-b.bin",
            "/mnt/sd/BODYDATA.DAT",
            "spi_nor:/boot0",
            "sector0:/mbr",
        ):
            g = evaluate_phase205_write_guard(p)
            self.assertFalse(g.valid, f"expected blocked: {p}")
            self.assertTrue(g.persistent_write_blocked)
            self.assertFalse(g.persistent_emmc_writes_authorized)
            self.assertFalse(g.spi_nor_write_authorized)
            self.assertFalse(g.el3_payload_transmit_authorized)
            self.assertEqual(g.physical_usb_packets_emitted, 0)
            self.assertEqual(g.persistent_writes, 0)
            self.assertEqual(g.calibration_mutation_bytes, 0)

    def test_45_write_guard_blocks_path_traversal_empty_and_unapproved_paths(
        self,
    ) -> None:
        for p in (
            "/tmp/fx6_wave27_overlay/../../dev/nflasha2",
            "",
            "   ",
            "/var/log/wave27_state.json",
            "/etc/desqueeze.conf",
        ):
            g = evaluate_phase205_write_guard(p)
            self.assertFalse(g.valid, f"expected blocked: {p!r}")
            self.assertTrue(g.persistent_write_blocked)

    def test_46_write_guard_permits_volatile_wave27_overlay_and_ram_shadow(self) -> None:
        for p in (
            f"{VOLATILE_WAVE27_OVERLAY_DIR_P205}/desqueeze_focusmap_state.json",
            "/tmp/fx6_stage_b_volatile/wb_state.json",
            "ram://fx6_wave27_shadow/desqueeze_165x",
            "memfd:wave27_mc_focus_map_telemetry",
        ):
            g = evaluate_phase205_write_guard(p)
            self.assertTrue(g.valid, f"expected allowed: {p}")
            self.assertTrue(g.volatile_overlay_allowed)
            self.assertFalse(g.persistent_write_blocked)
            self.assertFalse(g.persistent_emmc_writes_authorized)

    def test_47_phase205_compat_matrix_12_touchpoints_and_4_classes(self) -> None:
        m = build_phase205_compat_matrix()
        self.assertEqual(m.total_touchpoints, 12)
        self.assertEqual(len(m.touchpoints), 12)
        ids = [tp.touchpoint_id for tp in m.touchpoints]
        self.assertEqual(ids, [f"P205-{i:02d}" for i in range(1, 13)])
        self.assertEqual(sum(m.class_counts.values()), 12)
        for cls_name in VALID_BRIDGE_CLASSES:
            self.assertGreaterEqual(m.class_counts[cls_name], 1)
        self.assertEqual(
            m.pillar_counts,
            {
                "PILLAR_1_DESQUEEZE_165X_LOCKS": 4,
                "PILLAR_2_EXTERNAL_MC_FOCUS_MAP": 4,
                "PILLAR_3_SIMULT_AND_SHOCKLESS_WB": 4,
            },
        )

    def test_48_marker_catalogs_and_cpapp_bounded_constants_verified(self) -> None:
        self.assertEqual(len(APPFW_SHARED_WAVE27_MARKERS_P205), 16)
        self.assertEqual(len(APPFW_FX3_702_EXCLUSIVE_MARKERS_P205), 13)
        self.assertEqual(len(APPFW_FX6_601_EXCLUSIVE_MARKERS_P205), 7)
        self.assertEqual(len(UXC_FX3_EN_F_REQUIRED_TOKENS_P205), 22)
        self.assertEqual(len(UXC_FX6_EN_REQUIRED_TOKENS_P205), 11)
        self.assertEqual(len(CPAPP_SHARED_MARKERS_P205), 3)
        self.assertEqual(len(CPAPP_FX3_FOCUSMAP_MARKERS_P205), 3)
        self.assertEqual(CPAPP_BOUNDED_HEAD_BYTES_P205, 768 * 1024)
        self.assertEqual(CPAPP_BOUNDED_TAIL_BYTES_P205, 6 * 1024 * 1024)

    def test_49_donor_and_clean_room_markers_verified_across_all_pillars(self) -> None:
        for cr in (True, False):
            rep = analyze_realhw_desqueeze_165x_focusmap_simult_and_shocklesswb(
                clean_room=cr
            )
            p1 = rep.pillar_1_desqueeze_165x_locks
            p2 = rep.pillar_2_external_mc_focus_map
            p3 = rep.pillar_3_simult_and_shockless_wb
            self.assertGreaterEqual(
                p1.fx3_appfw_desqueeze_hits["BKID_APP_setting_de_squeeze_disp"], 1
            )
            self.assertGreaterEqual(
                p1.fx3_appfw_desqueeze_hits[
                    "VAL_HAITA_setting_de_squeeze_disp_general_shooting_mode_DE_SQUEEZE_DISP_1_6X"
                ],
                1,
            )
            self.assertGreaterEqual(
                p2.fx3_cpapp_summary.fx3_focusmap_marker_hits["cpActFocusMap"], 1
            )
            self.assertGreaterEqual(
                p3.fx3_appfw_simult_wb_hits[
                    "CAUTION_ID_2CARD_REQUIRED_SIMULTANEOIUS_FOR_MOVIE_RECORD"
                ],
                1,
            )
            self.assertGreaterEqual(
                p3.fx3_appfw_simult_wb_hits["BKID_APP_setting_movie_shockless_wb"], 1
            )

    def test_50_package_init_exports_all_phase205_symbols(self) -> None:
        expected_exports = (
            "PHASE_205_SCHEMA",
            "PHASE_205_VERSION",
            "RealhwDesqueeze165xFocusmapSimultAndShocklesswbReport",
            "Pillar1Desqueeze165xAndLocksReport",
            "Pillar2ExternalMcFocusMapReport",
            "Pillar3SimultAutoSwitchAndShocklessWbReport",
            "Pillar4Phase205WriteGuardAndMatrixReport",
            "analyze_realhw_desqueeze_165x_focusmap_simult_and_shocklesswb",
            "realhw_desqueeze_165x_focusmap_simult_and_shocklesswb_report_to_dict",
            "compute_desqueezed_display_aspect_ratio",
            "evaluate_desqueeze_display_165x_locks_and_suppression",
            "evaluate_external_mc_focus_map_and_150fps_cutoff",
            "evaluate_simult_recording_and_auto_switch_media",
            "evaluate_shockless_wb_and_ctemp_grid_bypass",
            "evaluate_phase205_write_guard",
            "build_phase205_compat_matrix",
            "build_clean_room_realhw_desqueeze_focusmap_shocklesswb_fixtures",
        )
        for sym in expected_exports:
            self.assertIn(sym, pkg.__all__)
            self.assertTrue(hasattr(pkg, sym))

    def test_51_cli_subcommand_clean_room_json_exit_zero(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cli_main(
                [
                    "audit-realhw-desqueeze-focusmap-shocklesswb",
                    "--clean-room",
                    "--json",
                ]
            )
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())
        self.assertTrue(payload["all_checks_passed"])
        self.assertEqual(payload["auditor_index"], "43/43")
        self.assertEqual(payload["mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(payload["schema_version"], PHASE_205_SCHEMA)

    def test_52_cli_subcommand_auto_mode_json_exit_zero(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cli_main(
                ["audit-realhw-desqueeze-focusmap-shocklesswb", "--json"]
            )
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())
        self.assertTrue(payload["all_checks_passed"])
        self.assertEqual(payload["auditor_index"], "43/43")
        self.assertFalse(payload["in_body_focus_map_overlay_injected"])
        self.assertEqual(payload["raw_firmware_bytes_leaked"], 0)

    def test_53_run_audit_all_includes_43rd_auditor_clean_room(self) -> None:
        t0 = time.monotonic()
        agg = run_audit_all(clean_room=True)
        dt = time.monotonic() - t0
        self.assertLess(dt, 6.0)
        self.assertTrue(agg["all_checks_passed"])
        self.assertIn(
            "realhw_desqueeze_165x_focusmap_simult_and_shocklesswb_audit", agg
        )
        sub = agg["realhw_desqueeze_165x_focusmap_simult_and_shocklesswb_audit"]
        self.assertTrue(sub["all_checks_passed"])
        self.assertEqual(sub["auditor_index"], "43/43")
        audit_keys = [k for k in agg.keys() if k.endswith("_audit")]
        self.assertGreaterEqual(len(audit_keys), 43)

    def test_54_shockless_wb_atw_convergence_smoothed_proportionally_to_fps(
        self,
    ) -> None:
        r_25 = evaluate_shockless_wb_and_ctemp_grid_bypass(
            shockless_wb_setting="2",
            frame_rate_fps=25.0,
            trigger_type="ATW_CONVERGENCE",
        )
        r_100 = evaluate_shockless_wb_and_ctemp_grid_bypass(
            shockless_wb_setting="2",
            frame_rate_fps=100.0,
            trigger_type="ATW_CONVERGENCE",
        )
        r_200 = evaluate_shockless_wb_and_ctemp_grid_bypass(
            shockless_wb_setting="2",
            frame_rate_fps=200.0,
            trigger_type="ATW_CONVERGENCE",
        )
        self.assertTrue(r_25.shockless_smoothing_applied)
        self.assertTrue(r_100.shockless_smoothing_applied)
        self.assertTrue(r_200.shockless_smoothing_applied)
        self.assertEqual(r_25.transition_frames, 40)
        self.assertEqual(r_100.transition_frames, r_25.transition_frames * 4)
        self.assertEqual(r_200.transition_frames, r_25.transition_frames * 8)


if __name__ == "__main__":
    unittest.main()
