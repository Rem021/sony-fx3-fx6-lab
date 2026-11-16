"""Unit tests for Phase 189 (39th Auditor, 39/39):
Real-Hardware ILME-FX3 (Ver. 7.02) vs ILME-FX3A (Ver. 2.02) LCD/NFC/IR Branch
Divergence & XLR-H1 MI-Shoe 48kHz/24bit 4ch Audio Bridge Auditor.

Runs cleanly in BOTH Local Donor mode (when local Sony donors are present) and
Clean-Room mode (`FX3_FX6_FORCE_CLEAN_ROOM=1` / `clean_room=True`).
"""

from __future__ import annotations

import ast
import io
import json
import os
import sys
import time
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

sys.dont_write_bytecode = True

import fx3_firmware_lab as pkg  # noqa: E402
from fx3_firmware_lab import (  # noqa: E402
    APPFW_FX3_BRANCH_MARKERS_P189,
    APPFW_FX3_JACK_AND_SQ_MARKERS_P189,
    APPFW_FX3_MISHOE_AUDIO_MARKERS_P189,
    APPFW_FX6_HANDLE_AUDIO_MARKERS_P189,
    AVBB_AUDIO_MARKERS_P189,
    CPAPP_FX3_MISHOE_MARKERS_P189,
    CPAPP_SHARED_SHOE_PANEL_MARKERS_P189,
    DEFAULT_BACKUP_SUBSYSTEMS_FX3,
    DEFAULT_BACKUP_SUBSYSTEMS_FX6,
    EXPECTED_FX3_APPFW_BYTES_P189,
    EXPECTED_FX3_BACKUP_BYTES_P189,
    EXPECTED_FX3_CPAPP_BYTES_P189,
    EXPECTED_FX3_MPR_BYTES_P189,
    EXPECTED_FX3_UPDATERUFP_BYTES_P189,
    EXPECTED_FX6_APPFW_BYTES_P189,
    EXPECTED_FX6_AVBB_AUDIO_BYTES_P189,
    EXPECTED_FX6_BACKUP_BYTES_P189,
    EXPECTED_FX6_CPAPP_BYTES_P189,
    EXPECTED_FX6_HOTSHOE_BYTES_P189,
    EXPECTED_FX6_MPR_BYTES_P189,
    FX3A_202_FW_VERSION,
    FX3A_LCD_DOTS,
    FX3_702_FW_VERSION,
    FX3_LCD_DOTS,
    HARDWARE_BRANCH_SPECS,
    MISHOE_AUDIO_FORMATS,
    MODEL_ID_FX30_P189,
    MODEL_ID_FX3A_P189,
    MODEL_ID_FX3_P189,
    MODEL_ID_FX6_P189,
    MONITOR_MODE_TO_APPFW_TOKEN,
    MPR_AUDIO_SHARED_MARKERS_P189,
    PHASE_189_SCHEMA,
    PHASE_189_VERSION,
    POST_UFU_DEFAULT_AUDIO_FORMAT,
    STAGE_A_REJECT_BUDGET_US,
    VALID_4CH_MONITOR_MODES,
    analyze_realhw_fx3_vs_fx3a_and_xlrh1_mishoe,
    build_clean_room_realhw_fx3_vs_fx3a_and_xlrh1_fixtures,
    build_phase189_compat_matrix,
    evaluate_body_35mm_jack_override_and_sq_mute,
    evaluate_fx3_vs_fx3a_hardware_branch,
    evaluate_phase189_write_guard,
    evaluate_post_ufu_audio_default_hygiene,
    evaluate_xlrh1_mishoe_4ch_bridge,
    realhw_fx3_vs_fx3a_and_xlrh1_mishoe_report_to_dict,
)
from fx3_firmware_lab.__main__ import main as cli_main  # noqa: E402
from fx3_firmware_lab.__main__ import run_audit_all  # noqa: E402

AUDITOR_PATH = (
    Path(__file__).resolve().parent.parent
    / "fx3_firmware_lab"
    / "realhw_fx3_vs_fx3a_and_xlrh1_mishoe_auditor.py"
)


class TestRealhwFx3VsFx3aAndXlrh1Mishoe(unittest.TestCase):
    """50 dual-mode tests covering Phase 189 (39th Auditor, 39/39)."""

    @classmethod
    def setUpClass(cls) -> None:
        t0 = time.perf_counter()
        cls.auto_report = analyze_realhw_fx3_vs_fx3a_and_xlrh1_mishoe()
        cls.auto_elapsed = time.perf_counter() - t0

        t1 = time.perf_counter()
        cls.clean_report = analyze_realhw_fx3_vs_fx3a_and_xlrh1_mishoe(clean_room=True)
        cls.clean_elapsed = time.perf_counter() - t1

    # ------------------------------------------------------------------
    # Group 1: AST O_RDONLY / Zero-Write / Dual-Mode / Safety Locks
    # ------------------------------------------------------------------

    def test_01_ast_strictly_o_rdonly_and_zero_write_calls(self) -> None:
        tree = ast.parse(AUDITOR_PATH.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == "open":
                    self.fail("Forbidden builtin open() in auditor module")
                if isinstance(node.func, ast.Attribute):
                    self.assertNotIn(
                        node.func.attr,
                        {"write_bytes", "write_text", "unlink", "rmdir", "mkdir", "chmod", "write"},
                        f"Forbidden write attribute {node.func.attr}",
                    )
                if (
                    isinstance(node.func, ast.Attribute)
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "os"
                    and node.func.attr == "open"
                ):
                    self.assertGreaterEqual(len(node.args), 2)
                    flag = node.args[1]
                    self.assertIsInstance(flag, ast.Attribute)
                    self.assertEqual(flag.attr, "O_RDONLY")
            if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
                if node.value.id == "os":
                    self.assertNotIn(
                        node.attr,
                        {"O_WRONLY", "O_RDWR", "O_CREAT", "O_TRUNC", "O_APPEND"},
                    )

    def test_02_performance_under_6s_sla_and_fast_clean_room(self) -> None:
        self.assertLess(self.auto_elapsed, 6.0)
        self.assertLess(self.clean_elapsed, 1.0)
        if self.auto_report.mode == "LOCAL_DONOR_VERIFIED":
            self.assertLess(self.auto_elapsed, 0.25)

    def test_03_auto_and_clean_room_reports_pass(self) -> None:
        self.assertTrue(self.auto_report.all_checks_passed, self.auto_report.errors)
        self.assertTrue(self.clean_report.all_checks_passed, self.clean_report.errors)
        self.assertIn(self.auto_report.mode, {"LOCAL_DONOR_VERIFIED", "CLEAN_ROOM_SYNTHETIC"})
        self.assertEqual(self.clean_report.mode, "CLEAN_ROOM_SYNTHETIC")

    def test_04_clean_room_determinism_sha256_identical(self) -> None:
        r2 = analyze_realhw_fx3_vs_fx3a_and_xlrh1_mishoe(clean_room=True)
        self.assertEqual(self.clean_report.report_sha256, r2.report_sha256)
        self.assertEqual(len(self.clean_report.report_sha256), 64)

    def test_05_missing_donors_fallback_clean_room(self) -> None:
        with mock.patch(
            "fx3_firmware_lab.realhw_fx3_vs_fx3a_and_xlrh1_mishoe_auditor.resolve_donor_file",
            return_value=None,
        ):
            r = analyze_realhw_fx3_vs_fx3a_and_xlrh1_mishoe(
                clean_room=False,
                repo_root=Path("/nonexistent/phase189/donor/root"),
            )
            self.assertEqual(r.mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertTrue(r.all_checks_passed, r.errors)

    def test_06_env_force_clean_room_override(self) -> None:
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            r = analyze_realhw_fx3_vs_fx3a_and_xlrh1_mishoe(clean_room=False)
            self.assertEqual(r.mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertTrue(r.all_checks_passed)

    def test_07_hard_safety_locks_and_zero_bytes_leaked(self) -> None:
        for rep in (self.auto_report, self.clean_report):
            self.assertTrue(rep.o_rdonly_enforced)
            self.assertEqual(rep.raw_firmware_bytes_leaked, 0)
            self.assertFalse(rep.persistent_emmc_writes_authorized)
            self.assertFalse(rep.spi_nor_write_authorized)
            self.assertFalse(rep.el3_payload_transmit_authorized)
            self.assertEqual(rep.physical_usb_packets_emitted, 0)
            self.assertEqual(rep.persistent_writes, 0)
            self.assertEqual(rep.backup_bin_writes, 0)

    def test_08_json_serialization_zero_elf_magic_leak(self) -> None:
        for rep in (self.auto_report, self.clean_report):
            d = realhw_fx3_vs_fx3a_and_xlrh1_mishoe_report_to_dict(rep)
            raw = json.dumps(d, sort_keys=True)
            self.assertNotIn("ELF", raw)
            self.assertEqual(d["schema_version"], PHASE_189_SCHEMA)
            self.assertEqual(d["phase_version"], PHASE_189_VERSION)

    def test_09_package_exports_and_fixture_keys(self) -> None:
        self.assertIn("analyze_realhw_fx3_vs_fx3a_and_xlrh1_mishoe", pkg.__all__)
        self.assertIn("RealhwFx3VsFx3aAndXlrh1MishoeReport", pkg.__all__)
        fx = build_clean_room_realhw_fx3_vs_fx3a_and_xlrh1_fixtures()
        for k in (
            "fx3_appfw",
            "fx6_appfw",
            "fx3_mpr",
            "fx6_mpr",
            "fx3_updaterufp",
            "fx3_bodydata_head",
            "fx3_bodydata_tail",
            "fx6_hotshoe",
            "fx6_avbb_audio",
            "fx3_cpapp",
            "fx6_cpapp",
            "fx3_backup",
            "fx6_backup",
        ):
            self.assertIn(k, fx)
            self.assertGreater(len(fx[k]), 0)

    # ------------------------------------------------------------------
    # Group 2: Domain A — FX3 (7.02) vs FX3A (2.02) Hardware Branch Split
    # ------------------------------------------------------------------

    def test_10_donor_sizes_exact_when_local_verified(self) -> None:
        if self.auto_report.mode != "LOCAL_DONOR_VERIFIED":
            self.assertTrue(self.clean_report.all_checks_passed)
            return
        sz = self.auto_report.donor_file_sizes
        self.assertEqual(sz["fx3_appfw"], EXPECTED_FX3_APPFW_BYTES_P189)
        self.assertEqual(sz["fx6_appfw"], EXPECTED_FX6_APPFW_BYTES_P189)
        self.assertEqual(sz["fx3_mpr"], EXPECTED_FX3_MPR_BYTES_P189)
        self.assertEqual(sz["fx6_mpr"], EXPECTED_FX6_MPR_BYTES_P189)
        self.assertEqual(sz["fx3_cpapp"], EXPECTED_FX3_CPAPP_BYTES_P189)
        self.assertEqual(sz["fx6_cpapp"], EXPECTED_FX6_CPAPP_BYTES_P189)
        self.assertEqual(sz["fx3_backup"], EXPECTED_FX3_BACKUP_BYTES_P189)
        self.assertEqual(sz["fx6_backup"], EXPECTED_FX6_BACKUP_BYTES_P189)
        self.assertEqual(sz["fx3_updaterufp"], EXPECTED_FX3_UPDATERUFP_BYTES_P189)
        self.assertEqual(sz["fx6_hotshoe"], EXPECTED_FX6_HOTSHOE_BYTES_P189)
        self.assertEqual(sz["fx6_avbb_audio"], EXPECTED_FX6_AVBB_AUDIO_BYTES_P189)

    def test_11_domain_a_fx3_branch_markers_present(self) -> None:
        for rep in (self.auto_report, self.clean_report):
            da = rep.domain_a_fx3_vs_fx3a_branch
            self.assertTrue(da.passed, da.errors)
            for tok in APPFW_FX3_BRANCH_MARKERS_P189:
                self.assertGreater(da.fx3_appfw_branch_hits[tok], 0, f"Missing {tok}")

    def test_12_domain_a_fx3_bodydata_and_updaterufp_valid(self) -> None:
        for rep in (self.auto_report, self.clean_report):
            da = rep.domain_a_fx3_vs_fx3a_branch
            self.assertTrue(da.fx3_updaterufp_summary.file_bytes > 0)
            self.assertTrue(da.fx3_bodydata_summary.valid)
            self.assertTrue(da.fx3_bodydata_summary.ufu_magic_ok)
            self.assertTrue(da.fx3_bodydata_summary.dend_trailer_ok)
            self.assertEqual(da.fx3_bodydata_summary.total_bytes, 811_876_768)

    def test_13_fx3_702_hardware_branch_accepted(self) -> None:
        res = evaluate_fx3_vs_fx3a_hardware_branch()
        self.assertTrue(res.valid)
        self.assertTrue(res.stage_a_accepted)
        self.assertFalse(res.fail_closed_rejected)
        self.assertEqual(res.model_id, MODEL_ID_FX3_P189)
        self.assertEqual(res.lcd_dots, FX3_LCD_DOTS)
        self.assertTrue(res.has_nfc)
        self.assertTrue(res.has_ir_receiver)
        self.assertEqual(res.bridge_class, "NATIVE_PASSTHROUGH")

    def test_14_fx3a_202_hardware_branch_rejected_under_50us(self) -> None:
        res = evaluate_fx3_vs_fx3a_hardware_branch(
            target_body="ILME-FX3A",
            model_id=MODEL_ID_FX3A_P189,
            fw_version=FX3A_202_FW_VERSION,
            lcd_dots=FX3A_LCD_DOTS,
            has_nfc=False,
            has_ir_receiver=False,
            camset_profile="CAMSET_FX3A_202",
            bodydata_model_id=MODEL_ID_FX3A_P189,
        )
        self.assertTrue(res.valid)
        self.assertFalse(res.stage_a_accepted)
        self.assertTrue(res.fail_closed_rejected)
        self.assertLess(res.reject_latency_us, STAGE_A_REJECT_BUDGET_US)
        self.assertEqual(res.bridge_class, "HARD_WRITE_PROTECTED")
        self.assertFalse(res.camset_compatible)
        self.assertFalse(res.bodydata_compatible)

    def test_15_fx30_lax_rejected_fail_closed(self) -> None:
        res = evaluate_fx3_vs_fx3a_hardware_branch(
            target_body="ILME-FX30",
            model_id=MODEL_ID_FX30_P189,
            fw_version="6.00",
            lcd_dots=FX3A_LCD_DOTS,
            has_nfc=False,
            has_ir_receiver=False,
            camset_profile="CAMSET_FX30",
            bodydata_model_id=MODEL_ID_FX30_P189,
        )
        self.assertTrue(res.valid)
        self.assertFalse(res.stage_a_accepted)
        self.assertTrue(res.fail_closed_rejected)

    def test_16_fx6_601_rejected_on_fx3_stage_a(self) -> None:
        res = evaluate_fx3_vs_fx3a_hardware_branch(
            target_body="ILME-FX6",
            model_id=MODEL_ID_FX6_P189,
            fw_version="6.01",
            lcd_dots=2_764_800,
            has_nfc=True,
            has_ir_receiver=False,
            camset_profile="CAMSET_FX6_601",
            bodydata_model_id=MODEL_ID_FX6_P189,
        )
        self.assertTrue(res.valid)
        self.assertFalse(res.stage_a_accepted)
        self.assertTrue(res.fail_closed_rejected)

    def test_17_cross_camset_profile_rejected(self) -> None:
        res = evaluate_fx3_vs_fx3a_hardware_branch(camset_profile="CAMSET_FX3A_202")
        self.assertFalse(res.stage_a_accepted)
        self.assertTrue(res.fail_closed_rejected)
        self.assertFalse(res.camset_compatible)

    def test_18_cross_bodydata_model_id_rejected(self) -> None:
        res = evaluate_fx3_vs_fx3a_hardware_branch(bodydata_model_id=MODEL_ID_FX3A_P189)
        self.assertFalse(res.stage_a_accepted)
        self.assertTrue(res.fail_closed_rejected)
        self.assertFalse(res.bodydata_compatible)

    def test_19_fx3_lcd_dot_mismatch_rejected(self) -> None:
        res = evaluate_fx3_vs_fx3a_hardware_branch(lcd_dots=FX3A_LCD_DOTS)
        self.assertFalse(res.stage_a_accepted)
        self.assertTrue(res.fail_closed_rejected)

    def test_20_fx3_missing_nfc_or_ir_rejected(self) -> None:
        res_nfc = evaluate_fx3_vs_fx3a_hardware_branch(has_nfc=False)
        res_ir = evaluate_fx3_vs_fx3a_hardware_branch(has_ir_receiver=False)
        self.assertTrue(res_nfc.fail_closed_rejected)
        self.assertTrue(res_ir.fail_closed_rejected)

    def test_21_unknown_hardware_branch_invalid(self) -> None:
        res = evaluate_fx3_vs_fx3a_hardware_branch(target_body="ILME-UNKNOWN")
        self.assertFalse(res.valid)
        self.assertFalse(res.stage_a_accepted)
        self.assertTrue(res.fail_closed_rejected)

    # ------------------------------------------------------------------
    # Group 3: Domain B — XLR-H1 MI-Shoe 48kHz/24bit 4ch Audio Bridge
    # ------------------------------------------------------------------

    def test_22_domain_b_fx3_appfw_and_cpapp_mishoe_markers(self) -> None:
        for rep in (self.auto_report, self.clean_report):
            db = rep.domain_b_xlrh1_mishoe_audio
            self.assertTrue(db.passed, db.errors)
            for tok in APPFW_FX3_MISHOE_AUDIO_MARKERS_P189:
                self.assertGreater(db.fx3_appfw_mishoe_hits[tok], 0, f"Missing {tok}")
            for tok in CPAPP_SHARED_SHOE_PANEL_MARKERS_P189 + CPAPP_FX3_MISHOE_MARKERS_P189:
                self.assertGreater(db.fx3_cpapp_mishoe_hits[tok], 0, f"Missing {tok}")

    def test_23_domain_b_fx6_handle_mpr_hotshoe_avbb_markers(self) -> None:
        for rep in (self.auto_report, self.clean_report):
            db = rep.domain_b_xlrh1_mishoe_audio
            for tok in APPFW_FX6_HANDLE_AUDIO_MARKERS_P189:
                self.assertGreater(db.fx6_appfw_handle_hits[tok], 0, f"Missing {tok}")
            for tok in MPR_AUDIO_SHARED_MARKERS_P189:
                self.assertGreater(db.fx3_mpr_summary.marker_hits[tok], 0, f"FX3 MPR {tok}")
                self.assertGreater(db.fx6_mpr_summary.marker_hits[tok], 0, f"FX6 MPR {tok}")
            for tok in AVBB_AUDIO_MARKERS_P189:
                self.assertGreater(db.fx6_avbb_audio_summary.marker_hits[tok], 0, f"AVBB {tok}")

    def test_24_xlrh1_mishoe_48khz_24bit_4ch_bridge(self) -> None:
        res = evaluate_xlrh1_mishoe_4ch_bridge(
            handle_attached=True,
            audio_format="48KHZ_24BIT_4CH",
            monitor_mode="CH1_3_AND_CH2_4_MIX",
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.sample_rate_hz, 48_000)
        self.assertEqual(res.bit_depth, 24)
        self.assertEqual(res.channels, 4)
        self.assertEqual(res.bitrate_bps, 4_608_000)
        self.assertEqual(res.channel_routing["CH1"], "XLR_H1_IN1_XLR")
        self.assertEqual(res.channel_routing["CH2"], "XLR_H1_IN2_XLR")
        self.assertEqual(res.channel_routing["CH3"], "XLR_H1_IN3_35MM_L")
        self.assertEqual(res.channel_routing["CH4"], "XLR_H1_IN3_35MM_R")
        self.assertTrue(res.big6_4ch_meters_bound)
        self.assertTrue(res.mpr_alsa_backend_bound)
        self.assertFalse(res.xlr_h1_standalone_fw_pkg_required)

    def test_25_xlrh1_mishoe_24bit_2ch_bridge(self) -> None:
        res = evaluate_xlrh1_mishoe_4ch_bridge(
            handle_attached=True,
            audio_format="48KHZ_24BIT_2CH",
            monitor_mode="CH1_2",
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.bit_depth, 24)
        self.assertEqual(res.channels, 2)
        self.assertEqual(res.bitrate_bps, 2_304_000)
        self.assertEqual(res.monitor_appfw_token, MONITOR_MODE_TO_APPFW_TOKEN["CH1_2"])

    def test_26_xlrh1_mishoe_16bit_2ch_bridge(self) -> None:
        res = evaluate_xlrh1_mishoe_4ch_bridge(
            handle_attached=True,
            audio_format="48KHZ_16BIT_2CH",
            monitor_mode="CH3_4",
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.bit_depth, 16)
        self.assertEqual(res.channels, 2)
        self.assertEqual(res.bitrate_bps, 1_536_000)
        self.assertEqual(res.monitor_appfw_token, MONITOR_MODE_TO_APPFW_TOKEN["CH3_4"])

    def test_27_xlrh1_all_4ch_monitor_modes_mapped(self) -> None:
        for mode in VALID_4CH_MONITOR_MODES:
            res = evaluate_xlrh1_mishoe_4ch_bridge(
                handle_attached=True, audio_format="48KHZ_24BIT_4CH", monitor_mode=mode
            )
            self.assertTrue(res.valid)
            self.assertEqual(res.monitor_appfw_token, MONITOR_MODE_TO_APPFW_TOKEN[mode])

    def test_28_xlrh1_detached_p11_nonblock_fallback(self) -> None:
        res = evaluate_xlrh1_mishoe_4ch_bridge(handle_attached=False)
        self.assertTrue(res.valid)
        self.assertFalse(res.handle_attached)
        self.assertFalse(res.big6_4ch_meters_bound)
        self.assertTrue(res.mpr_alsa_backend_bound)
        self.assertEqual(res.p11_queue_hex, "0x91db059b")
        self.assertEqual(res.p11_nonblock_rc_hex, "0x8000")
        self.assertEqual(res.bridge_class, "SHIM_TRANSLATED")
        self.assertEqual(res.status, "P11_DETACHED_FALLBACK_INTERNAL_STEREO_OK")
        self.assertEqual(res.channel_routing["CH1"], "FX3_INTERNAL_MIC_L")
        self.assertEqual(res.channel_routing["CH2"], "FX3_INTERNAL_MIC_R")

    def test_29_xlrh1_invalid_format_rejected(self) -> None:
        res = evaluate_xlrh1_mishoe_4ch_bridge(audio_format="96KHZ_32BIT_8CH")
        self.assertFalse(res.valid)
        self.assertTrue(any("UNKNOWN_MISHOE_AUDIO_FORMAT" in e for e in res.errors))

    def test_30_xlrh1_invalid_monitor_mode_rejected(self) -> None:
        res = evaluate_xlrh1_mishoe_4ch_bridge(monitor_mode="CH5_6")
        self.assertFalse(res.valid)
        self.assertTrue(any("UNKNOWN_4CH_MONITOR_MODE" in e for e in res.errors))

    def test_31_xlrh1_requires_no_standalone_fw_package(self) -> None:
        for fmt in MISHOE_AUDIO_FORMATS:
            res = evaluate_xlrh1_mishoe_4ch_bridge(handle_attached=True, audio_format=fmt)
            self.assertFalse(res.xlr_h1_standalone_fw_pkg_required)

    # ------------------------------------------------------------------
    # Group 4: Domain C — Body 3.5mm Jack Override & S&Q Audio Mute
    # ------------------------------------------------------------------

    def test_32_domain_c_jack_and_sq_markers_present(self) -> None:
        for rep in (self.auto_report, self.clean_report):
            dc = rep.domain_c_jack_override_sq_mute
            self.assertTrue(dc.passed, dc.errors)
            for tok in APPFW_FX3_JACK_AND_SQ_MARKERS_P189:
                self.assertGreater(dc.fx3_appfw_jack_sq_hits[tok], 0, f"Missing {tok}")

    def test_33_xlrh1_attached_without_35mm_jack_unlocks_mishoe(self) -> None:
        res = evaluate_body_35mm_jack_override_and_sq_mute(
            xlr_h1_attached=True, body_35mm_jack_inserted=False, sq_mode_active=False
        )
        self.assertTrue(res.valid)
        self.assertTrue(res.mi_shoe_audio_active)
        self.assertFalse(res.mi_shoe_audio_set_locked)
        self.assertFalse(res.audio_recording_muted)
        self.assertEqual(res.active_audio_source, "XLR_H1_MISHOE_DIGITAL_AUDIO")
        self.assertEqual(res.mpr_stall_faults, 0)

    def test_34_body_35mm_jack_overrides_and_locks_mishoe(self) -> None:
        res = evaluate_body_35mm_jack_override_and_sq_mute(
            xlr_h1_attached=True, body_35mm_jack_inserted=True, sq_mode_active=False
        )
        self.assertTrue(res.valid)
        self.assertTrue(res.mi_shoe_audio_set_locked)
        self.assertFalse(res.mi_shoe_audio_active)
        self.assertFalse(res.audio_recording_muted)
        self.assertEqual(res.active_audio_source, "BODY_35MM_TRS_JACK_MIC")
        self.assertEqual(res.caution_factor_token, "CAUTION_ID_FACTOR_ANALOG_MIC_SHOEMIC_USE_MSG")
        self.assertEqual(res.mpr_stall_faults, 0)

    def test_35_sq_offspeed_mutes_audio_zero_mpr_stall(self) -> None:
        res = evaluate_body_35mm_jack_override_and_sq_mute(
            xlr_h1_attached=True,
            body_35mm_jack_inserted=False,
            sq_mode_active=True,
            rec_fps=23.976,
            sensor_fps=120.0,
        )
        self.assertTrue(res.valid)
        self.assertTrue(res.audio_recording_muted)
        self.assertTrue(res.mi_shoe_audio_set_locked)
        self.assertFalse(res.mi_shoe_audio_active)
        self.assertEqual(res.active_audio_source, "MUTED_NO_AUDIO_TRACK")
        self.assertEqual(res.mpr_stall_faults, 0)
        self.assertEqual(res.status, "SQ_OFFSPEED_AUDIO_MUTED_OK")

    def test_36_sq_matching_fps_does_not_false_mute(self) -> None:
        res = evaluate_body_35mm_jack_override_and_sq_mute(
            xlr_h1_attached=True,
            body_35mm_jack_inserted=False,
            sq_mode_active=True,
            rec_fps=24.0,
            sensor_fps=24.0,
        )
        self.assertTrue(res.valid)
        self.assertFalse(res.audio_recording_muted)
        self.assertTrue(res.mi_shoe_audio_active)
        self.assertEqual(res.active_audio_source, "XLR_H1_MISHOE_DIGITAL_AUDIO")

    def test_37_audio_recording_off_mutes_cleanly(self) -> None:
        res = evaluate_body_35mm_jack_override_and_sq_mute(
            xlr_h1_attached=True,
            body_35mm_jack_inserted=False,
            sq_mode_active=False,
            audio_recording_enabled=False,
        )
        self.assertTrue(res.valid)
        self.assertTrue(res.audio_recording_muted)
        self.assertEqual(res.caution_factor_token, "CAUTION_ID_FACTOR_AUDIO_RECORDING_OFF_MSG")
        self.assertEqual(res.mpr_stall_faults, 0)

    def test_38_unplugged_handle_and_unplugged_35mm_fallback(self) -> None:
        res = evaluate_body_35mm_jack_override_and_sq_mute(
            xlr_h1_attached=False, body_35mm_jack_inserted=False, sq_mode_active=False
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.active_audio_source, "BODY_INTERNAL_STEREO_MIC")
        self.assertTrue(res.mi_shoe_audio_set_locked)
        self.assertEqual(res.caution_factor_token, "CAUTION_ID_FACTOR_MIC_SHOEMIC_NOT_USE_MSG")

    # ------------------------------------------------------------------
    # Group 5: Domain D — Post-UFU Audio Default Hygiene, Firewall & CLI
    # ------------------------------------------------------------------

    def test_39_domain_d_backup_bin_bk4_checksums_and_subsystems(self) -> None:
        for rep in (self.auto_report, self.clean_report):
            dd = rep.domain_d_post_ufu_backup_audio
            self.assertTrue(dd.passed, dd.errors)
            self.assertTrue(dd.fx3_backup_summary.rec0_checksum_valid)
            self.assertTrue(dd.fx3_backup_summary.rec1_checksum_valid)
            self.assertTrue(dd.fx6_backup_summary.rec0_checksum_valid)
            self.assertTrue(dd.fx6_backup_summary.rec1_checksum_valid)
            self.assertEqual(dd.fx3_backup_summary.rec0_subsystems, DEFAULT_BACKUP_SUBSYSTEMS_FX3)
            self.assertEqual(dd.fx6_backup_summary.rec0_subsystems, DEFAULT_BACKUP_SUBSYSTEMS_FX6)

    def test_40_post_ufu_h0_h1_h2_h3_backup_default_16bit_2ch_conserved(self) -> None:
        h0 = evaluate_post_ufu_audio_default_hygiene(stage="H0")
        h1 = evaluate_post_ufu_audio_default_hygiene(stage="H1", h0_backup_sha256=h0.h0_backup_sha256)
        h2 = evaluate_post_ufu_audio_default_hygiene(
            stage="H2",
            stage_b_user_audio_pref="48KHZ_24BIT_4CH",
            h0_backup_sha256=h0.h0_backup_sha256,
        )
        h3 = evaluate_post_ufu_audio_default_hygiene(stage="H3", h0_backup_sha256=h0.h0_backup_sha256)
        self.assertEqual(h0.effective_audio_format, POST_UFU_DEFAULT_AUDIO_FORMAT)
        self.assertEqual(h1.effective_audio_format, POST_UFU_DEFAULT_AUDIO_FORMAT)
        self.assertEqual(h2.effective_audio_format, "48KHZ_24BIT_4CH")
        self.assertEqual(h3.effective_audio_format, POST_UFU_DEFAULT_AUDIO_FORMAT)
        for ev in (h0, h1, h2, h3):
            self.assertTrue(ev.valid)
            self.assertTrue(ev.volatile_staged)
            self.assertEqual(ev.persistent_writes, 0)
            self.assertEqual(ev.backup_bin_writes, 0)
            self.assertTrue(ev.backup_bin_hash_conserved)
            self.assertEqual(ev.h0_backup_sha256, h0.h0_backup_sha256)
            self.assertEqual(ev.stage_backup_sha256, h0.h0_backup_sha256)

    def test_41_post_ufu_invalid_stage_and_invalid_pref_rejected(self) -> None:
        bad_stage = evaluate_post_ufu_audio_default_hygiene(stage="H9")
        bad_pref = evaluate_post_ufu_audio_default_hygiene(stage_b_user_audio_pref="96KHZ_32BIT")
        self.assertFalse(bad_stage.valid)
        self.assertFalse(bad_pref.valid)

    def test_42_write_guard_allows_volatile_and_ext_media_only(self) -> None:
        for ok_target in (
            "/tmp/stage_b/xlrh1_audio_pref.json",
            "/tmp_wbshd/camset_overlay.bin",
            "ram://fx3_mishoe_state",
            "/mnt/sd/PRIVATE/M4ROOT/CLIP/C0001.MP4",
            "/mnt/cfexpress_a/stage_b/xlrh1_pref.json",
        ):
            wg = evaluate_phase189_write_guard(ok_target)
            self.assertTrue(wg.valid, ok_target)
            self.assertTrue(wg.volatile_or_ext_allowed)
            self.assertFalse(wg.persistent_write_blocked)
            self.assertEqual(wg.persistent_writes, 0)

    def test_43_write_guard_blocks_backup_bodydata_camset_emmc_spinor(self) -> None:
        for bad_target in (
            "p2:/setting/Backup.bin",
            "/mnt/sd/BODYDATA.DAT",
            "/mnt/sd/PRIVATE/SONY/CAMSET_FX3.DAT",
            "p2:/CAMSET_FX3A.DAT",
            "/dev/nflasha7",
            "/dev/cnflasha12",
            "spi_nor:loader_nor.bin",
            "p8:/cpapp-b.bin",
            "/setting/Backup.bin",
        ):
            wg = evaluate_phase189_write_guard(bad_target)
            self.assertFalse(wg.valid, bad_target)
            self.assertTrue(wg.persistent_write_blocked, bad_target)
            self.assertFalse(wg.persistent_emmc_writes_authorized)
            self.assertFalse(wg.spi_nor_write_authorized)
            self.assertEqual(wg.backup_bin_writes, 0)

    def test_44_post_ufu_hygiene_blocks_persistent_pref_staging_path(self) -> None:
        bad = evaluate_post_ufu_audio_default_hygiene(
            stage="H2",
            pref_staging_path="p2:/setting/Backup.bin",
        )
        self.assertFalse(bad.valid)
        self.assertEqual(bad.backup_bin_writes, 0)
        self.assertEqual(bad.persistent_writes, 0)

    def test_45_compat_matrix_12_touchpoints_and_all_4_classes(self) -> None:
        mat = build_phase189_compat_matrix()
        self.assertEqual(mat.total_touchpoints, 12)
        self.assertEqual(sum(mat.class_counts.values()), 12)
        self.assertEqual(sum(mat.domain_counts.values()), 12)
        for cls_name, cnt in mat.class_counts.items():
            self.assertGreater(cnt, 0, f"Class {cls_name} has 0 touchpoints")
        ids = [t.touchpoint_id for t in mat.touchpoints]
        self.assertEqual(ids, [f"P189-{i:02d}" for i in range(1, 13)])

    def test_46_cli_subcommand_auto_mode_passes(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cli_main(["audit-realhw-fx3a-and-xlrh1-mishoe", "--json"])
        self.assertEqual(rc, 0)
        parsed = json.loads(buf.getvalue())
        self.assertTrue(parsed["all_checks_passed"])
        self.assertEqual(parsed["schema_version"], PHASE_189_SCHEMA)
        self.assertEqual(parsed["raw_firmware_bytes_leaked"], 0)

    def test_47_cli_subcommand_clean_room_passes(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cli_main(["audit-realhw-fx3a-and-xlrh1-mishoe", "--clean-room", "--json"])
        self.assertEqual(rc, 0)
        parsed = json.loads(buf.getvalue())
        self.assertEqual(parsed["mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(parsed["all_checks_passed"])

    def test_48_run_audit_all_registers_39_of_39_auditors(self) -> None:
        summary = run_audit_all(clean_room=True)
        self.assertTrue(summary["all_checks_passed"])
        self.assertIn("realhw_fx3_vs_fx3a_and_xlrh1_mishoe_audit", summary)
        audit_keys = [k for k in summary.keys() if k.endswith("_audit")]
        self.assertGreaterEqual(len(audit_keys), 39)
        self.assertTrue(summary["realhw_fx3_vs_fx3a_and_xlrh1_mishoe_audit"]["all_checks_passed"])

    def test_49_hardware_branch_specs_exact(self) -> None:
        self.assertEqual(HARDWARE_BRANCH_SPECS["ILME-FX3"]["model_id"], 0x91030080)
        self.assertEqual(HARDWARE_BRANCH_SPECS["ILME-FX3"]["lcd_dots"], 1_440_000)
        self.assertTrue(HARDWARE_BRANCH_SPECS["ILME-FX3"]["has_nfc"])
        self.assertTrue(HARDWARE_BRANCH_SPECS["ILME-FX3"]["has_ir_receiver"])
        self.assertEqual(HARDWARE_BRANCH_SPECS["ILME-FX3A"]["model_id"], 0x91030082)
        self.assertEqual(HARDWARE_BRANCH_SPECS["ILME-FX3A"]["lcd_dots"], 2_359_296)
        self.assertFalse(HARDWARE_BRANCH_SPECS["ILME-FX3A"]["has_nfc"])
        self.assertFalse(HARDWARE_BRANCH_SPECS["ILME-FX3A"]["has_ir_receiver"])
        self.assertEqual(HARDWARE_BRANCH_SPECS["ILME-FX30"]["model_id"], 0x91030081)

    def test_50_phase189_constants_exact(self) -> None:
        self.assertEqual(FX3_702_FW_VERSION, "7.02")
        self.assertEqual(FX3A_202_FW_VERSION, "2.02")
        self.assertEqual(POST_UFU_DEFAULT_AUDIO_FORMAT, "48KHZ_16BIT_2CH")
        self.assertEqual(STAGE_A_REJECT_BUDGET_US, 50.0)
        self.assertEqual(DEFAULT_BACKUP_SUBSYSTEMS_FX3, 819)
        self.assertEqual(DEFAULT_BACKUP_SUBSYSTEMS_FX6, 840)


if __name__ == "__main__":
    unittest.main()
