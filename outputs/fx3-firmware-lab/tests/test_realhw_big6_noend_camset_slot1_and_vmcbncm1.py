"""Phase 203 Dual-Mode Unit Tests (56 tests) — 42nd Firmware Auditor (42/42):
Real-Hardware `ILME-FX3` (`Ver. 7.02`) `BIG6` `[Home (Lower Left)]` Zero e-ND
Actuator Boundary, Slot-1 `CAMSET` Dual-Media Path Split & `VMC-BNCM1` Body-Only
`TC IN` / HDMI `TC OUT` Auditor.
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
    APPFW_FX3_702_EXCLUSIVE_MARKERS_P203,
    APPFW_FX6_601_EXCLUSIVE_END_AND_SDI_MARKERS_P203,
    APPFW_SHARED_WAVE26_MARKERS_P203,
    BRIDGE_CLASS_HARD_WRITE_PROTECTED,
    BRIDGE_CLASS_MASKED_ABSENT_HW,
    BRIDGE_CLASS_NATIVE_PASSTHROUGH,
    BRIDGE_CLASS_SHIM_TRANSLATED,
    CAMSET_ALLOWED_SLOT_P203,
    CAMSET_APPFW_PRINTF_TEMPLATE_P203,
    CAMSET_CANONICAL_FILENAMES_P203,
    CAMSET_CFEXPRESS_A_ROOT_DIR_P203,
    CAMSET_DAT_HEADER_BYTES_P203,
    CAMSET_DISALLOWED_SLOT_P203,
    CAMSET_MAX_PROFILES_PER_CARD_P203,
    CAMSET_MODEL_SPECS_P203,
    CAMSET_SD_ROOT_DIR_P203,
    CPAPP_BOUNDED_HEAD_BYTES_P203,
    CPAPP_BOUNDED_TAIL_BYTES_P203,
    CPAPP_FORBIDDEN_END_ACTUATOR_MARKERS_P203,
    CPAPP_SHARED_TC_IMAGER_MARKERS_P203,
    DONOR_COLD_SCAN_BUDGET_SEC_P203,
    EXCLUDED_MACHINE_BOUND_CAMSET_FIELDS_P203,
    EXPECTED_FX3_APPFW_BYTES_P203,
    EXPECTED_FX3_CPAPP_BYTES_P203,
    EXPECTED_FX3_UXC_EN_F_BYTES_P203,
    EXPECTED_FX6_APPFW_BYTES_P203,
    EXPECTED_FX6_CPAPP_BYTES_P203,
    EXPECTED_FX6_UXC_EN_BYTES_P203,
    EXT_LK_MIN_LOCK_DWELL_SEC_P203,
    FTPSET_APPFW_PRINTF_TEMPLATE_P203,
    FX3_BIG6_PREREQ_MODE_SETTINGS_P203,
    FX3_BIG6_SEVENTH_STATUS_REGION_P203,
    FX3_BIG6_SIX_TILE_TOPOLOGY_P203,
    FX3_HOME_LOWER_LEFT_MENU_PATH_P203,
    FX6_MOTORIZED_END_RANGE_FRACTIONS_P203,
    HDMI_TC_OUT_MENU_PATH_P203,
    PHASE_203_SCHEMA,
    PHASE_203_VERSION,
    UXC_FX3_EN_F_REQUIRED_TOKENS_P203,
    UXC_FX6_EN_REQUIRED_TOKENS_P203,
    VALID_BRIDGE_CLASSES,
    VMC_BNCM1_CABLE_LENGTH_M_P203,
    VMC_BNCM1_PART_NUMBER_P203,
    VOLATILE_FX6_CAMSET_OVERLAY_DIR_P203,
    analyze_realhw_big6_noend_camset_slot1_and_vmcbncm1,
    build_clean_room_realhw_big6_noend_camset_vmcbncm1_fixtures,
    build_phase203_compat_matrix,
    evaluate_camset_slot1_path_and_cross_model_firewall,
    evaluate_fx3_big6_home_and_zero_end_boundary,
    evaluate_phase203_write_guard,
    evaluate_vmcbncm1_tcin_and_hdmi_tcout_routing,
    realhw_big6_noend_camset_slot1_and_vmcbncm1_report_to_dict,
    resolve_expected_camset_directory,
    serialize_camset_dat_header,
    verify_camset_dat_model_compatibility,
)
from fx3_firmware_lab import (  # noqa: E402
    realhw_big6_noend_camset_slot1_and_vmcbncm1_auditor as mod_p203,
)
from fx3_firmware_lab.__main__ import main as cli_main  # noqa: E402
from fx3_firmware_lab.__main__ import run_audit_all  # noqa: E402


class TestRealhwBig6NoendCamsetSlot1AndVmcbncm1(unittest.TestCase):
    """56 dual-mode unit tests for Phase 203 (42nd Auditor `42/42`)."""

    # ------------------------------------------------------------------
    # Group A: AST Zero-Write Proof, Cold/Warm SLA, Clean-Room & Safety
    # ------------------------------------------------------------------

    def test_01_ast_strictly_o_rdonly_and_zero_write_calls(self) -> None:
        src_path = Path(mod_p203.__file__)
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
        rep = analyze_realhw_big6_noend_camset_slot1_and_vmcbncm1(clean_room=True)
        dt = time.monotonic() - t0
        self.assertLess(dt, 6.0)
        self.assertEqual(rep.schema_version, PHASE_203_SCHEMA)
        self.assertEqual(rep.phase_version, PHASE_203_VERSION)
        self.assertEqual(rep.auditor_index, "42/42")
        self.assertEqual(rep.mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(rep.all_checks_passed)
        self.assertEqual(rep.errors, ())
        self.assertTrue(rep.o_rdonly_enforced)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_03_auto_mode_under_cold_sla_and_cache_hit_on_second_call(self) -> None:
        mod_p203._DONOR_SCAN_CACHE_P203.clear()
        t0 = time.monotonic()
        r1 = analyze_realhw_big6_noend_camset_slot1_and_vmcbncm1(clean_room=False)
        dt1 = time.monotonic() - t0
        self.assertLess(dt1, 6.0)
        self.assertTrue(r1.all_checks_passed)
        self.assertEqual(r1.errors, ())
        if r1.mode == "LOCAL_DONOR_RDONLY":
            self.assertFalse(r1.cache_hit)
            self.assertLess(r1.cold_or_cached_scan_elapsed_sec, 6.0)
            self.assertEqual(DONOR_COLD_SCAN_BUDGET_SEC_P203, 0.15)
            r2 = analyze_realhw_big6_noend_camset_slot1_and_vmcbncm1(clean_room=False)
            self.assertTrue(r2.cache_hit)
            self.assertEqual(r1.report_sha256, r2.report_sha256)
            self.assertEqual(
                r1.donor_file_sizes["fx3_appfw"], EXPECTED_FX3_APPFW_BYTES_P203
            )
            self.assertEqual(
                r1.donor_file_sizes["fx6_appfw"], EXPECTED_FX6_APPFW_BYTES_P203
            )
            self.assertEqual(
                r1.donor_file_sizes["fx3_string_english_f_uxc"],
                EXPECTED_FX3_UXC_EN_F_BYTES_P203,
            )
            self.assertEqual(
                r1.donor_file_sizes["fx6_string_english_uxc"],
                EXPECTED_FX6_UXC_EN_BYTES_P203,
            )
            self.assertEqual(
                r1.donor_file_sizes["fx3_cpapp_b_bin"], EXPECTED_FX3_CPAPP_BYTES_P203
            )
            self.assertEqual(
                r1.donor_file_sizes["fx6_cpapp_b_bin"], EXPECTED_FX6_CPAPP_BYTES_P203
            )

    def test_04_hard_safety_invariants_across_both_modes(self) -> None:
        for cr in (True, False):
            rep = analyze_realhw_big6_noend_camset_slot1_and_vmcbncm1(clean_room=cr)
            self.assertFalse(rep.persistent_emmc_writes_authorized)
            self.assertFalse(rep.spi_nor_write_authorized)
            self.assertFalse(rep.el3_payload_transmit_authorized)
            self.assertEqual(rep.physical_usb_packets_emitted, 0)
            self.assertEqual(rep.e_nd_actuator_tx_count, 0)
            self.assertEqual(rep.persistent_writes, 0)
            self.assertEqual(rep.p2_setting_mutation_bytes, 0)
            self.assertEqual(rep.calibration_mutation_bytes, 0)
            self.assertEqual(rep.raw_firmware_bytes_leaked, 0)
            self.assertTrue(rep.big6_6tile_and_zero_end_boundary_verified)
            self.assertTrue(rep.camset_slot1_dual_path_and_firewall_verified)
            self.assertTrue(rep.vmcbncm1_body_tcin_and_hdmi_tcout_verified)
            self.assertTrue(rep.zero_write_firewall_and_matrix_verified)

    def test_05_clean_room_deterministic_sha256_and_json_no_hex_leak(self) -> None:
        r1 = analyze_realhw_big6_noend_camset_slot1_and_vmcbncm1(clean_room=True)
        r2 = analyze_realhw_big6_noend_camset_slot1_and_vmcbncm1(clean_room=True)
        self.assertEqual(r1.report_sha256, r2.report_sha256)
        self.assertEqual(len(r1.report_sha256), 64)
        d = realhw_big6_noend_camset_slot1_and_vmcbncm1_report_to_dict(r1)
        s = json.dumps(d, sort_keys=True)
        parsed = json.loads(s)
        self.assertEqual(parsed["auditor_index"], "42/42")
        self.assertEqual(parsed["raw_firmware_bytes_leaked"], 0)
        self.assertNotIn("7f454c46", s.lower())

    def test_06_env_force_clean_room_and_missing_donor_fallback(self) -> None:
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            rep_env = analyze_realhw_big6_noend_camset_slot1_and_vmcbncm1(
                clean_room=False
            )
            self.assertEqual(rep_env.mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertTrue(rep_env.all_checks_passed)
        with mock.patch.object(mod_p203, "resolve_donor_file", return_value=None):
            rep_missing = analyze_realhw_big6_noend_camset_slot1_and_vmcbncm1(
                clean_room=False
            )
            self.assertEqual(rep_missing.mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertTrue(rep_missing.all_checks_passed)

    def test_07_clean_room_synthetic_fixtures_structure(self) -> None:
        fx = build_clean_room_realhw_big6_noend_camset_vmcbncm1_fixtures()
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
        for m in APPFW_FX6_601_EXCLUSIVE_END_AND_SDI_MARKERS_P203:
            self.assertNotIn(m.encode("ascii"), fx["fx3_appfw"])
            self.assertIn(m.encode("ascii"), fx["fx6_appfw"])
        for m in CPAPP_FORBIDDEN_END_ACTUATOR_MARKERS_P203:
            self.assertNotIn(m.encode("ascii"), fx["fx3_cpapp"])
            self.assertNotIn(m.encode("ascii"), fx["fx6_cpapp"])

    # ------------------------------------------------------------------
    # Group B: Pillar 1 — `BIG6` Home 6-Tile Topology & Zero Physical e-ND
    # ------------------------------------------------------------------

    def test_08_big6_six_tile_and_seventh_status_bar_constants(self) -> None:
        self.assertEqual(len(FX3_BIG6_SIX_TILE_TOPOLOGY_P203), 6)
        indices = [idx for idx, _tid, _lbl in FX3_BIG6_SIX_TILE_TOPOLOGY_P203]
        self.assertEqual(indices, [1, 2, 3, 4, 5, 6])
        self.assertEqual(
            FX3_BIG6_SIX_TILE_TOPOLOGY_P203[3][2],
            "Aperture / ND Filter ([Home (Lower Left)])",
        )
        self.assertEqual(
            FX3_BIG6_SEVENTH_STATUS_REGION_P203, "REGION_7_STATUS_BAR_TC_AUDIO_MEDIA"
        )
        self.assertEqual(
            FX3_HOME_LOWER_LEFT_MENU_PATH_P203,
            "MENU -> Setup -> [Operation Customize] -> [Home (Lower Left)]",
        )
        self.assertEqual(FX3_BIG6_PREREQ_MODE_SETTINGS_P203, "Fixed/Variable")

    def test_09_big6_default_aperture_lower_left_verified(self) -> None:
        res = evaluate_fx3_big6_home_and_zero_end_boundary(
            mode_settings="Fixed/Variable",
            home_custom_key_bound=True,
            home_lower_left_choice="Aperture",
            requested_nd_label="Clear",
            stage_b_end_actuator_tx_blocked=True,
        )
        self.assertTrue(res.valid)
        self.assertTrue(res.big6_home_accessible)
        self.assertEqual(res.tile_count, 6)
        self.assertEqual(res.appfw_lower_left_enum, "MOVIE_HOME_LOWER_LEFT_APERTURE")
        self.assertEqual(res.tile_4_effective_binding, "EMOUNT_LENS_APERTURE_IRIS_SERVO")
        self.assertFalse(res.physical_internal_end_present_on_fx3)
        self.assertTrue(res.physical_internal_end_present_on_fx6)
        self.assertFalse(res.nd_treated_as_manual_reference_only)
        self.assertEqual(res.e_nd_actuator_tx_count, 0)
        self.assertEqual(res.bridge_class, BRIDGE_CLASS_NATIVE_PASSTHROUGH)
        self.assertEqual(res.status, "OK_BIG6_TILE4_EMOUNT_APERTURE_ZERO_END_TX")

    def test_10_big6_nd_filter_lower_left_manual_metadata_only_all_fractions(self) -> None:
        for frac in ("Clear", *FX6_MOTORIZED_END_RANGE_FRACTIONS_P203):
            res = evaluate_fx3_big6_home_and_zero_end_boundary(
                mode_settings="Fixed/Variable",
                home_custom_key_bound=True,
                home_lower_left_choice="ND Filter",
                requested_nd_label=frac,
                stage_b_end_actuator_tx_blocked=True,
            )
            self.assertTrue(res.valid, f"failed for {frac}: {res.errors}")
            self.assertEqual(
                res.appfw_lower_left_enum, "MOVIE_HOME_LOWER_LEFT_ND_FILTER"
            )
            self.assertTrue(res.nd_treated_as_manual_reference_only)
            self.assertEqual(
                res.tile_4_effective_binding,
                f"MANUAL_ND_FRACTION_METADATA_ONLY:{frac}",
            )
            self.assertEqual(res.e_nd_actuator_tx_count, 0)
            self.assertEqual(res.bridge_class, BRIDGE_CLASS_MASKED_ABSENT_HW)

    def test_11_big6_unavailable_when_mode_settings_not_fixed_variable(self) -> None:
        for non_fv in ("Normal_Movie_Non_FixedVariable", "S&Q_Legacy"):
            res = evaluate_fx3_big6_home_and_zero_end_boundary(
                mode_settings=non_fv,
                home_custom_key_bound=True,
                home_lower_left_choice="Aperture",
            )
            self.assertFalse(res.valid)
            self.assertFalse(res.big6_home_accessible)
            self.assertIn(
                "BIG6_HOME_UNAVAILABLE_REQUIRES_MODE_SETTINGS_FIXED_VARIABLE",
                res.errors,
            )
            self.assertEqual(res.e_nd_actuator_tx_count, 0)

    def test_12_big6_unavailable_when_home_custom_key_unbound(self) -> None:
        res = evaluate_fx3_big6_home_and_zero_end_boundary(
            mode_settings="Fixed/Variable",
            home_custom_key_bound=False,
            home_lower_left_choice="Aperture",
        )
        self.assertFalse(res.valid)
        self.assertFalse(res.big6_home_accessible)
        self.assertIn(
            "BIG6_HOME_UNAVAILABLE_REQUIRES_CUSTOM_KEY_HOME_BINDING", res.errors
        )

    def test_13_stage_b_unblocked_end_actuator_tx_rejected_fail_closed(self) -> None:
        res = evaluate_fx3_big6_home_and_zero_end_boundary(
            mode_settings="Fixed/Variable",
            home_custom_key_bound=True,
            home_lower_left_choice="ND Filter",
            requested_nd_label="1/64",
            stage_b_end_actuator_tx_blocked=False,
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.e_nd_actuator_tx_count, 0)
        self.assertTrue(
            any("FX3_ABSENT_PHYSICAL_END_ACTUATOR_TX_FORBIDDEN" in e for e in res.errors)
        )

    def test_14_big6_invalid_enum_inputs_rejected(self) -> None:
        r_mode = evaluate_fx3_big6_home_and_zero_end_boundary(mode_settings="UnknownMode")
        self.assertFalse(r_mode.valid)
        self.assertTrue(any("INVALID_MODE_SETTINGS_VALUE" in e for e in r_mode.errors))

        r_ll = evaluate_fx3_big6_home_and_zero_end_boundary(
            home_lower_left_choice="GainDb"
        )
        self.assertFalse(r_ll.valid)
        self.assertTrue(any("INVALID_HOME_LOWER_LEFT_CHOICE" in e for e in r_ll.errors))

        r_nd = evaluate_fx3_big6_home_and_zero_end_boundary(requested_nd_label="1/256")
        self.assertFalse(r_nd.valid)
        self.assertTrue(any("INVALID_ND_FILTER_LABEL" in e for e in r_nd.errors))

    def test_15_pillar_1_donor_and_clean_room_zero_fx3_motorized_end_hits(self) -> None:
        for cr in (True, False):
            rep = analyze_realhw_big6_noend_camset_slot1_and_vmcbncm1(clean_room=cr)
            p1 = rep.pillar_1_big6_zero_end
            p3 = rep.pillar_3_vmcbncm1_hdmi_tc
            self.assertTrue(p1.passed)
            self.assertEqual(len(p1.fx6_exclusive_end_hits_in_fx3), 7)
            for m, cnt_fx3 in p1.fx6_exclusive_end_hits_in_fx3.items():
                self.assertEqual(cnt_fx3, 0)
                self.assertGreaterEqual(p1.fx6_exclusive_end_hits_in_fx6[m], 1)
            self.assertGreaterEqual(
                p3.fx6_appfw_tc_hits["PRM_HAITA_setting_hdmi_tc_output_sdi_output"], 1
            )
            self.assertTrue(p1.fx3_uxc_en_f_summary.uxc_magic_valid)
            self.assertTrue(p1.fx6_uxc_en_summary.uxc_magic_valid)
            for tok in UXC_FX3_EN_F_REQUIRED_TOKENS_P203:
                self.assertGreaterEqual(
                    p1.fx3_uxc_en_f_summary.required_token_hits[tok], 1
                )
            for tok in UXC_FX6_EN_REQUIRED_TOKENS_P203:
                self.assertGreaterEqual(
                    p1.fx6_uxc_en_summary.required_token_hits[tok], 1
                )
            for m in CPAPP_SHARED_TC_IMAGER_MARKERS_P203:
                self.assertGreaterEqual(p1.fx3_cpapp_summary.marker_hits[m], 1)
                self.assertGreaterEqual(p1.fx6_cpapp_summary.marker_hits[m], 1)
            for fb in CPAPP_FORBIDDEN_END_ACTUATOR_MARKERS_P203:
                self.assertEqual(
                    p1.fx3_cpapp_summary.forbidden_end_actuator_hits[fb], 0
                )
            if rep.mode == "LOCAL_DONOR_RDONLY":
                expected_bounded = (
                    CPAPP_BOUNDED_HEAD_BYTES_P203 + CPAPP_BOUNDED_TAIL_BYTES_P203
                )
                self.assertEqual(p1.fx3_cpapp_summary.bounded_bytes_read, expected_bounded)
                self.assertEqual(p1.fx6_cpapp_summary.bounded_bytes_read, expected_bounded)

    # ------------------------------------------------------------------
    # Group C: Pillar 2 — Slot-1 `CAMSET`, Dual-Media Path & `.DAT` Firewall
    # ------------------------------------------------------------------

    def test_16_camset_constants_and_printf_templates(self) -> None:
        self.assertEqual(CAMSET_MAX_PROFILES_PER_CARD_P203, 10)
        self.assertEqual(CAMSET_ALLOWED_SLOT_P203, "Slot 1")
        self.assertEqual(CAMSET_DISALLOWED_SLOT_P203, "Slot 2")
        self.assertEqual(len(CAMSET_CANONICAL_FILENAMES_P203), 10)
        self.assertEqual(CAMSET_CANONICAL_FILENAMES_P203[0], "CAMSET01.DAT")
        self.assertEqual(CAMSET_CANONICAL_FILENAMES_P203[-1], "CAMSET10.DAT")
        self.assertEqual(CAMSET_SD_ROOT_DIR_P203, "/PRIVATE/SONY/SETTING/FX3/CAMSET/")
        self.assertEqual(
            CAMSET_CFEXPRESS_A_ROOT_DIR_P203, "/SONY/SETTING/FX3/CAMSET/"
        )
        self.assertEqual(
            CAMSET_APPFW_PRINTF_TEMPLATE_P203, "%c:%s/SONY/SETTING/%s/CAMSET/%s.DAT"
        )
        self.assertEqual(
            FTPSET_APPFW_PRINTF_TEMPLATE_P203, "%c:%s/SONY/SETTING/%s/FTPSET/%s.DAT"
        )

    def test_17_resolve_expected_camset_directory_sd_vs_cfexpress_a(self) -> None:
        for sd_t in ("SD", "SDHC", "SDXC", "sdxc"):
            self.assertEqual(
                resolve_expected_camset_directory(sd_t),
                "/PRIVATE/SONY/SETTING/FX3/CAMSET/",
            )
        self.assertEqual(
            resolve_expected_camset_directory("CFEXPRESS_TYPE_A"),
            "/SONY/SETTING/FX3/CAMSET/",
        )
        with self.assertRaises(ValueError):
            resolve_expected_camset_directory("CFEXPRESS_TYPE_B")

    def test_18_slot1_sd_and_cfexpress_a_all_10_profiles_pass(self) -> None:
        for idx in range(1, 11):
            r_sd = evaluate_camset_slot1_path_and_cross_model_firewall(
                target_slot="Slot 1",
                media_type="SDXC",
                profile_index=idx,
            )
            self.assertTrue(r_sd.valid)
            self.assertTrue(r_sd.dual_media_path_valid)
            self.assertEqual(
                r_sd.requested_card_path,
                f"/PRIVATE/SONY/SETTING/FX3/CAMSET/CAMSET{idx:02d}.DAT",
            )
            r_cf = evaluate_camset_slot1_path_and_cross_model_firewall(
                target_slot="Slot 1",
                media_type="CFEXPRESS_TYPE_A",
                profile_index=idx,
            )
            self.assertTrue(r_cf.valid)
            self.assertTrue(r_cf.dual_media_path_valid)
            self.assertEqual(
                r_cf.requested_card_path,
                f"/SONY/SETTING/FX3/CAMSET/CAMSET{idx:02d}.DAT",
            )

    def test_19_slot2_rejected_slot1_only_lock(self) -> None:
        res = evaluate_camset_slot1_path_and_cross_model_firewall(
            target_slot="Slot 2",
            media_type="SDXC",
            profile_index=1,
        )
        self.assertFalse(res.valid)
        self.assertFalse(res.slot1_only_enforced)
        self.assertTrue(any("CAMSET_SLOT2_DISALLOWED_SLOT1_ONLY" in e for e in res.errors))

    def test_20_camset_profile_index_0_and_11_rejected(self) -> None:
        for bad_idx in (0, 11, -1, 99):
            res = evaluate_camset_slot1_path_and_cross_model_firewall(
                target_slot="Slot 1",
                media_type="SDXC",
                profile_index=bad_idx,
            )
            self.assertFalse(res.valid)
            self.assertTrue(
                any("CAMSET_PROFILE_INDEX_OUT_OF_RANGE_1_TO_10" in e for e in res.errors)
            )

    def test_21_mr_recall_camera_setting_mode_greyed_out_rejected(self) -> None:
        res = evaluate_camset_slot1_path_and_cross_model_firewall(
            camera_mode="MR_RECALL_CAMERA_SETTING",
            target_slot="Slot 1",
            media_type="SDXC",
            profile_index=1,
        )
        self.assertFalse(res.valid)
        self.assertTrue(res.menu_greyed_out)
        self.assertIn("CAMSET_GREYED_OUT_IN_MR_RECALL_MODE", res.errors)

    def test_22_sd_missing_private_prefix_and_cfexpress_extra_private_rejected(self) -> None:
        r_sd_bad = evaluate_camset_slot1_path_and_cross_model_firewall(
            target_slot="Slot 1",
            media_type="SDXC",
            profile_index=1,
            requested_card_path="/SONY/SETTING/FX3/CAMSET/CAMSET01.DAT",
        )
        self.assertFalse(r_sd_bad.valid)
        self.assertIn("CAMSET_SD_MISSING_PRIVATE_ROOT_PREFIX", r_sd_bad.errors)

        r_cf_bad = evaluate_camset_slot1_path_and_cross_model_firewall(
            target_slot="Slot 1",
            media_type="CFEXPRESS_TYPE_A",
            profile_index=1,
            requested_card_path="/PRIVATE/SONY/SETTING/FX3/CAMSET/CAMSET01.DAT",
        )
        self.assertFalse(r_cf_bad.valid)
        self.assertIn("CAMSET_CFEXPRESS_A_FORBIDDEN_PRIVATE_PREFIX", r_cf_bad.errors)

    def test_23_excluded_machine_bound_fields_stripped_and_forced_rejected(self) -> None:
        self.assertEqual(
            EXCLUDED_MACHINE_BOUND_CAMSET_FIELDS_P203,
            (
                "Custom WB 1/2/3",
                "FTP",
                "Network Streaming",
                "IP/Cert",
                "Date/Time",
            ),
        )
        r_strip = evaluate_camset_slot1_path_and_cross_model_firewall(
            requested_payload_fields=(
                "FPS",
                "Custom WB 1/2/3",
                "FTP",
                "Network Streaming",
                "IP/Cert",
                "Date/Time",
            ),
            force_include_machine_bound_fields=False,
        )
        self.assertTrue(r_strip.valid)
        self.assertEqual(
            r_strip.stripped_machine_bound_fields,
            EXCLUDED_MACHINE_BOUND_CAMSET_FIELDS_P203,
        )

        r_forced = evaluate_camset_slot1_path_and_cross_model_firewall(
            requested_payload_fields=("FPS", "Custom WB 1/2/3", "FTP"),
            force_include_machine_bound_fields=True,
        )
        self.assertFalse(r_forced.valid)
        self.assertTrue(
            any("CAMSET_MACHINE_BOUND_FIELDS_FORBIDDEN" in e for e in r_forced.errors)
        )

    def test_24_camset_dat_header_serialization_and_cross_model_rejection(self) -> None:
        fx3_raw, fx3_sum = serialize_camset_dat_header(model_name="ILME-FX3", profile_index=1)
        fx3a_raw, fx3a_sum = serialize_camset_dat_header(model_name="ILME-FX3A", profile_index=1)
        fx6_raw, fx6_sum = serialize_camset_dat_header(model_name="ILME-FX6", profile_index=1)

        self.assertEqual(len(fx3_raw), CAMSET_DAT_HEADER_BYTES_P203)
        self.assertEqual(fx3_sum.model_id_hex, "0x91030080")
        self.assertEqual(fx3a_sum.model_id_hex, "0x91030082")
        self.assertEqual(fx6_sum.model_id_hex, "0x91030060")

        ok_same, reason_same = verify_camset_dat_model_compatibility(
            fx3_raw, expected_reader_model="ILME-FX3"
        )
        self.assertTrue(ok_same)
        self.assertEqual(reason_same, "OK_CAMSET_DAT_MODEL_EXACT_MATCH")

        for foreign_raw in (fx3a_raw, fx6_raw):
            ok_cross, reason_cross = verify_camset_dat_model_compatibility(
                foreign_raw, expected_reader_model="ILME-FX3"
            )
            self.assertFalse(ok_cross)
            self.assertEqual(reason_cross, "CAMSET_CROSS_MODEL_DAT_INCOMPATIBLE")

        ok_fx3_on_fx3a, reason_rev = verify_camset_dat_model_compatibility(
            fx3_raw, expected_reader_model="ILME-FX3A"
        )
        self.assertFalse(ok_fx3_on_fx3a)
        self.assertEqual(reason_rev, "CAMSET_CROSS_MODEL_DAT_INCOMPATIBLE")

    def test_25_camset_dat_header_corrupt_crc_truncated_and_bad_args(self) -> None:
        fx3_raw, _ = serialize_camset_dat_header(model_name="ILME-FX3", profile_index=5)
        corrupt = fx3_raw[:-1] + bytes([fx3_raw[-1] ^ 0xFF])
        ok_crc, r_crc = verify_camset_dat_model_compatibility(
            corrupt, expected_reader_model="ILME-FX3"
        )
        self.assertFalse(ok_crc)
        self.assertEqual(r_crc, "CAMSET_DAT_CRC32_CORRUPT")

        ok_trunc, r_trunc = verify_camset_dat_model_compatibility(
            fx3_raw[:16], expected_reader_model="ILME-FX3"
        )
        self.assertFalse(ok_trunc)
        self.assertEqual(r_trunc, "CAMSET_DAT_TRUNCATED_OR_INVALID_SIZE")

        ok_unk, r_unk = verify_camset_dat_model_compatibility(
            fx3_raw, expected_reader_model="ILME-FX9"
        )
        self.assertFalse(ok_unk)
        self.assertIn("UNKNOWN_READER_MODEL", r_unk)

        with self.assertRaises(ValueError):
            serialize_camset_dat_header(model_name="ILME-FX9", profile_index=1)
        with self.assertRaises(ValueError):
            serialize_camset_dat_header(model_name="ILME-FX3", profile_index=11)

    def test_26_cross_model_camset_evaluator_and_stage_b_volatile_overlay_h0_eq_h3(self) -> None:
        for writer in ("ILME-FX3A", "ILME-FX6"):
            r_cross = evaluate_camset_slot1_path_and_cross_model_firewall(
                writer_model=writer,
                reader_model="ILME-FX3",
                stage_b_active=False,
            )
            self.assertFalse(r_cross.valid)
            self.assertTrue(r_cross.cross_model_incompatible_blocked)
            self.assertEqual(r_cross.bridge_class, BRIDGE_CLASS_HARD_WRITE_PROTECTED)

        r_bad_stage_b = evaluate_camset_slot1_path_and_cross_model_firewall(
            writer_model="ILME-FX6",
            reader_model="ILME-FX3",
            stage_b_active=True,
            stage_b_storage_target="/PRIVATE/SONY/SETTING/FX3/CAMSET/CAMSET01.DAT",
            lifecycle_stage="H2",
        )
        self.assertFalse(r_bad_stage_b.valid)
        self.assertTrue(
            any("STAGE_B_CAMSET_WRITE_TO_STOCK_PATH_BLOCKED" in e for e in r_bad_stage_b.errors)
        )

        r_ok_stage_b = evaluate_camset_slot1_path_and_cross_model_firewall(
            writer_model="ILME-FX6",
            reader_model="ILME-FX3",
            stage_b_active=True,
            stage_b_storage_target=f"{VOLATILE_FX6_CAMSET_OVERLAY_DIR_P203}/CAMSET01.json",
            lifecycle_stage="H3",
        )
        self.assertTrue(r_ok_stage_b.valid)
        self.assertTrue(r_ok_stage_b.redirected_to_volatile_camset_overlay)
        self.assertTrue(r_ok_stage_b.h0_equals_h3)
        self.assertEqual(r_ok_stage_b.h0_state_sha256, r_ok_stage_b.h3_state_sha256)
        self.assertEqual(r_ok_stage_b.p2_setting_mutation_bytes, 0)
        self.assertEqual(r_ok_stage_b.stock_slot1_camset_mutation_bytes, 0)
        self.assertEqual(r_ok_stage_b.bridge_class, BRIDGE_CLASS_SHIM_TRANSLATED)

    def test_27_camset_invalid_mode_media_model_and_stage_rejected(self) -> None:
        res = evaluate_camset_slot1_path_and_cross_model_firewall(
            camera_mode="INVALID_MODE",
            media_type="COMPACT_FLASH",
            writer_model="UNKNOWN_WRITER",
            reader_model="UNKNOWN_READER",
            lifecycle_stage="H9",
        )
        self.assertFalse(res.valid)
        self.assertGreaterEqual(len(res.errors), 5)

    # ------------------------------------------------------------------
    # Group D: Pillar 3 — `VMC-BNCM1` Body-Only `TC IN` & HDMI `TC OUT`
    # ------------------------------------------------------------------

    def test_28_vmcbncm1_part_number_cable_length_and_dwell_constants(self) -> None:
        self.assertEqual(VMC_BNCM1_PART_NUMBER_P203, "A-5051-506-A")
        self.assertAlmostEqual(VMC_BNCM1_CABLE_LENGTH_M_P203, 0.2)
        self.assertAlmostEqual(EXT_LK_MIN_LOCK_DWELL_SEC_P203, 10.0)
        self.assertEqual(
            HDMI_TC_OUT_MENU_PATH_P203,
            "MENU -> Setup -> [External Output] -> [HDMI Output Settings] -> [Time Code Output]",
        )

    def test_29_body_multi_usb_tcin_movie_preset_freerun_10s_achieves_ext_lk(self) -> None:
        for dwell in (10.0, 12.5, 60.0):
            res = evaluate_vmcbncm1_tcin_and_hdmi_tcout_routing(
                physical_port="BODY_MULTI_MICRO_USB",
                requested_direction="TC_IN",
                boot_context="NORMAL_OS",
                shooting_mode="Movie",
                tc_make="Preset",
                tc_run="Free Run",
                lock_dwell_sec=dwell,
                tc_setting_edited_after_lock=False,
                hdmi_tc_output_menu_setting="On",
            )
            self.assertTrue(res.valid)
            self.assertTrue(res.ext_lk_locked)
            self.assertEqual(res.ext_lk_state_label, "EXT-LK")
            self.assertEqual(res.adapter_part_number, "A-5051-506-A")
            self.assertEqual(res.bnc_tc_out_tx_packets, 0)
            self.assertTrue(res.hdmi_tc_out_active)
            self.assertEqual(res.bridge_class, BRIDGE_CLASS_NATIVE_PASSTHROUGH)

    def test_30_body_multi_usb_tcin_under_10s_acquiring_not_yet_locked(self) -> None:
        for dwell in (0.0, 4.5, 9.99):
            res = evaluate_vmcbncm1_tcin_and_hdmi_tcout_routing(
                physical_port="BODY_MULTI_MICRO_USB",
                requested_direction="TC_IN",
                shooting_mode="Movie",
                tc_make="Preset",
                tc_run="Free Run",
                lock_dwell_sec=dwell,
            )
            self.assertTrue(res.valid)
            self.assertFalse(res.ext_lk_locked)
            self.assertEqual(res.ext_lk_state_label, "ACQUIRING_EXT_LK_UNDER_10S")

    def test_31_sq_mode_unlocks_ext_lk_and_auto_disables_hdmi_tc_out(self) -> None:
        res = evaluate_vmcbncm1_tcin_and_hdmi_tcout_routing(
            physical_port="BODY_MULTI_MICRO_USB",
            requested_direction="TC_IN",
            shooting_mode="S&Q",
            tc_make="Preset",
            tc_run="Free Run",
            lock_dwell_sec=15.0,
            hdmi_tc_output_menu_setting="On",
        )
        self.assertTrue(res.valid)
        self.assertFalse(res.ext_lk_locked)
        self.assertEqual(res.ext_lk_state_label, "UNLOCKED_NON_MOVIE_OR_SQ_MODE")
        self.assertFalse(res.hdmi_tc_out_active)
        self.assertTrue(res.hdmi_tc_out_disabled_in_sq)

    def test_32_regenerate_or_rec_run_prevents_ext_lk_lock(self) -> None:
        r_regen = evaluate_vmcbncm1_tcin_and_hdmi_tcout_routing(
            tc_make="Regenerate",
            tc_run="Free Run",
            lock_dwell_sec=15.0,
        )
        self.assertTrue(r_regen.valid)
        self.assertFalse(r_regen.ext_lk_locked)
        self.assertEqual(
            r_regen.ext_lk_state_label, "UNLOCKED_REQUIRES_PRESET_AND_FREE_RUN"
        )

        r_recrun = evaluate_vmcbncm1_tcin_and_hdmi_tcout_routing(
            tc_make="Preset",
            tc_run="Rec Run",
            lock_dwell_sec=15.0,
        )
        self.assertTrue(r_recrun.valid)
        self.assertFalse(r_recrun.ext_lk_locked)
        self.assertEqual(
            r_recrun.ext_lk_state_label, "UNLOCKED_REQUIRES_PRESET_AND_FREE_RUN"
        )

    def test_33_tc_setting_edit_after_lock_immediately_unlocks_ext_lk(self) -> None:
        res = evaluate_vmcbncm1_tcin_and_hdmi_tcout_routing(
            physical_port="BODY_MULTI_MICRO_USB",
            requested_direction="TC_IN",
            shooting_mode="Movie",
            tc_make="Preset",
            tc_run="Free Run",
            lock_dwell_sec=30.0,
            tc_setting_edited_after_lock=True,
        )
        self.assertTrue(res.valid)
        self.assertFalse(res.ext_lk_locked)
        self.assertEqual(res.ext_lk_state_label, "UNLOCKED_BY_TC_SETTING_EDIT")

    def test_34_xlr_h1_handle_micro_usb_port_strictly_prohibited(self) -> None:
        res = evaluate_vmcbncm1_tcin_and_hdmi_tcout_routing(
            physical_port="XLR_H1_HANDLE_MICRO_USB",
            requested_direction="TC_IN",
            shooting_mode="Movie",
            tc_make="Preset",
            tc_run="Free Run",
            lock_dwell_sec=15.0,
        )
        self.assertFalse(res.valid)
        self.assertTrue(res.xlr_h1_handle_port_prohibited)
        self.assertFalse(res.ext_lk_locked)
        self.assertEqual(res.bridge_class, BRIDGE_CLASS_HARD_WRITE_PROTECTED)
        self.assertTrue(
            any("VMC_BNCM1_PROHIBITED_ON_XLR_H1_HANDLE_MICRO_USB" in e for e in res.errors)
        )

    def test_35_h0_uart_boot_pin_7_8_9_contention_blocks_vmcbncm1(self) -> None:
        res = evaluate_vmcbncm1_tcin_and_hdmi_tcout_routing(
            physical_port="BODY_MULTI_MICRO_USB",
            requested_direction="TC_IN",
            boot_context="H0_UART_BOOT",
            shooting_mode="Movie",
            lock_dwell_sec=15.0,
        )
        self.assertFalse(res.valid)
        self.assertTrue(res.uart_boot_pin_contention_blocked)
        self.assertEqual(res.bridge_class, BRIDGE_CLASS_HARD_WRITE_PROTECTED)
        self.assertTrue(
            any("VMC_BNCM1_FORBIDDEN_DURING_UART_BOOT_PINS_7_8_9" in e for e in res.errors)
        )

    def test_36_reverse_ltc_bnc_tc_out_rejected_eopnotsupp_zero_tx_packets(self) -> None:
        for port in ("BODY_MULTI_MICRO_USB", "FX6_VIRTUAL_BNC_PORT"):
            res = evaluate_vmcbncm1_tcin_and_hdmi_tcout_routing(
                physical_port=port,
                requested_direction="TC_OUT",
                shooting_mode="Movie",
            )
            self.assertFalse(res.valid)
            self.assertTrue(res.bnc_tc_out_rejected_eopnotsupp)
            self.assertEqual(res.errno_code, "EOPNOTSUPP")
            self.assertEqual(res.bnc_tc_out_tx_packets, 0)
            self.assertEqual(res.bridge_class, BRIDGE_CLASS_MASKED_ABSENT_HW)

    def test_37_hdmi_type_a_digital_tc_out_on_off_and_sq_matrix(self) -> None:
        r_on = evaluate_vmcbncm1_tcin_and_hdmi_tcout_routing(
            physical_port="HDMI_TYPE_A",
            requested_direction="TC_OUT",
            shooting_mode="Movie",
            hdmi_tc_output_menu_setting="On",
        )
        self.assertTrue(r_on.valid)
        self.assertTrue(r_on.hdmi_tc_out_active)
        self.assertEqual(r_on.ext_lk_state_label, "HDMI_DIGITAL_TC_OUT_ACTIVE")
        self.assertEqual(r_on.bridge_class, BRIDGE_CLASS_SHIM_TRANSLATED)

        r_off = evaluate_vmcbncm1_tcin_and_hdmi_tcout_routing(
            physical_port="HDMI_TYPE_A",
            requested_direction="TC_OUT",
            shooting_mode="Movie",
            hdmi_tc_output_menu_setting="Off",
        )
        self.assertTrue(r_off.valid)
        self.assertFalse(r_off.hdmi_tc_out_active)
        self.assertEqual(r_off.ext_lk_state_label, "HDMI_TC_OUT_OFF")

        r_sq = evaluate_vmcbncm1_tcin_and_hdmi_tcout_routing(
            physical_port="HDMI_TYPE_A",
            requested_direction="TC_OUT",
            shooting_mode="S&Q",
            hdmi_tc_output_menu_setting="On",
        )
        self.assertTrue(r_sq.valid)
        self.assertFalse(r_sq.hdmi_tc_out_active)
        self.assertTrue(r_sq.hdmi_tc_out_disabled_in_sq)
        self.assertEqual(r_sq.ext_lk_state_label, "HDMI_TC_OUT_AUTO_DISABLED_IN_SQ")

    def test_38_hdmi_tc_in_and_fx6_virtual_bnc_tc_in_rejected(self) -> None:
        r_hdmi_in = evaluate_vmcbncm1_tcin_and_hdmi_tcout_routing(
            physical_port="HDMI_TYPE_A",
            requested_direction="TC_IN",
        )
        self.assertFalse(r_hdmi_in.valid)
        self.assertEqual(r_hdmi_in.errno_code, "EOPNOTSUPP")

        r_fx6_bnc_in = evaluate_vmcbncm1_tcin_and_hdmi_tcout_routing(
            physical_port="FX6_VIRTUAL_BNC_PORT",
            requested_direction="TC_IN",
        )
        self.assertFalse(r_fx6_bnc_in.valid)
        self.assertIn(
            "FX6_DEDICATED_BNC_ABSENT_USE_BODY_MULTI_USB_VMC_BNCM1",
            r_fx6_bnc_in.errors,
        )

    def test_39_vmcbncm1_invalid_parameters_rejected(self) -> None:
        res = evaluate_vmcbncm1_tcin_and_hdmi_tcout_routing(
            physical_port="USB_TYPE_C_PD",
            requested_direction="BIDIR",
            boot_context="UNKNOWN_BOOT",
            shooting_mode="PhotoBurst",
            tc_make="AutoMake",
            tc_run="HoldRun",
            lock_dwell_sec=-1.0,
            hdmi_tc_output_menu_setting="Auto",
        )
        self.assertFalse(res.valid)
        self.assertEqual(len(res.errors), 8)

    # ------------------------------------------------------------------
    # Group E: Pillar 4 — Write Firewall, 12-Touchpoint Matrix, CLI & Exports
    # ------------------------------------------------------------------

    def test_40_write_guard_blocks_p2_setting_backup_bin_and_stock_camset(self) -> None:
        for p in (
            "p2:/setting/Backup.bin",
            "/setting/CAMSET01.DAT",
            "/PRIVATE/SONY/SETTING/FX3/CAMSET/CAMSET01.DAT",
            "/SONY/SETTING/FX3/CAMSET/CAMSET10.DAT",
            "/PRIVATE/SONY/SETTING/FX3/FTPSET/FTPSET01.DAT",
        ):
            g = evaluate_phase203_write_guard(p)
            self.assertFalse(g.valid, f"expected blocked: {p}")
            self.assertTrue(g.persistent_write_blocked)
            self.assertFalse(g.persistent_emmc_writes_authorized)
            self.assertFalse(g.spi_nor_write_authorized)
            self.assertFalse(g.el3_payload_transmit_authorized)
            self.assertEqual(g.physical_usb_packets_emitted, 0)

    def test_41_write_guard_blocks_emmc_spinor_cpapp_bodydata_and_traversal(self) -> None:
        for p in (
            "/dev/nflasha2",
            "/dev/mmcblk0p5",
            "spi_nor:/boot0",
            "/firmware/CPAPP-B.BIN",
            "/mnt/sd/BODYDATA.DAT",
            "/tmp/fx6_camset_overlay/../../dev/nflasha2",
            "",
            "   ",
            "/var/log/unapproved_camset.dat",
        ):
            g = evaluate_phase203_write_guard(p)
            self.assertFalse(g.valid, f"expected blocked: {p!r}")
            self.assertTrue(g.persistent_write_blocked)

    def test_42_write_guard_permits_volatile_camset_overlay_and_ram_shadow(self) -> None:
        for p in (
            "/tmp/fx6_camset_overlay/CAMSET01.json",
            "/tmp/fx6_stage_b_volatile/big6_state.json",
            "ram://fx6_big6_camset_shadow/slot1",
        ):
            g = evaluate_phase203_write_guard(p)
            self.assertTrue(g.valid, f"expected allowed: {p}")
            self.assertTrue(g.volatile_overlay_allowed)
            self.assertFalse(g.persistent_write_blocked)
            self.assertFalse(g.persistent_emmc_writes_authorized)

    def test_43_phase203_compat_matrix_12_touchpoints_and_4_classes(self) -> None:
        m = build_phase203_compat_matrix()
        self.assertEqual(m.total_touchpoints, 12)
        self.assertEqual(len(m.touchpoints), 12)
        ids = [tp.touchpoint_id for tp in m.touchpoints]
        self.assertEqual(ids, [f"P203-{i:02d}" for i in range(1, 13)])
        self.assertEqual(sum(m.class_counts.values()), 12)
        for cls_name in VALID_BRIDGE_CLASSES:
            self.assertGreaterEqual(m.class_counts[cls_name], 1)
        self.assertEqual(
            m.pillar_counts,
            {
                "PILLAR_1_BIG6_ZERO_END": 4,
                "PILLAR_2_CAMSET_SLOT1_FIREWALL": 4,
                "PILLAR_3_VMC_BNCM1_HDMI_TC": 4,
            },
        )

    def test_44_shared_and_fx3_exclusive_appfw_markers_present_in_both_modes(self) -> None:
        for cr in (True, False):
            rep = analyze_realhw_big6_noend_camset_slot1_and_vmcbncm1(clean_room=cr)
            p1 = rep.pillar_1_big6_zero_end
            p2 = rep.pillar_2_camset_slot1_firewall
            p3 = rep.pillar_3_vmcbncm1_hdmi_tc
            self.assertGreaterEqual(
                p1.fx3_appfw_big6_hits["MOVIE_HOME_LOWER_LEFT_APERTURE"], 1
            )
            self.assertGreaterEqual(
                p1.fx3_appfw_big6_hits["MOVIE_HOME_LOWER_LEFT_ND_FILTER"], 1
            )
            self.assertGreaterEqual(
                p1.fx3_appfw_big6_hits["26view_tp_button_01_for_big6"], 1
            )
            self.assertGreaterEqual(
                p2.fx3_appfw_camset_hits["%c:%s/SONY/SETTING/%s/CAMSET/%s.DAT"], 1
            )
            self.assertGreaterEqual(p2.fx3_appfw_camset_hits["CAMSET%02d"], 1)
            self.assertGreaterEqual(p3.fx3_appfw_tc_hits["No301_EXTLK"], 1)
            self.assertGreaterEqual(p3.fx3_appfw_tc_hits["MSG_ID_TCUB_TC_SYNC"], 1)
            self.assertGreaterEqual(
                p3.fx3_appfw_tc_hits[
                    "VAL_setting_hdmi_tc_output_EXTERNAL_HDMI_TC_OUTPUT_ON"
                ],
                1,
            )

    def test_45_marker_catalog_sizes_verified(self) -> None:
        self.assertGreaterEqual(len(APPFW_SHARED_WAVE26_MARKERS_P203), 16)
        self.assertGreaterEqual(len(APPFW_FX3_702_EXCLUSIVE_MARKERS_P203), 8)
        self.assertGreaterEqual(
            len(APPFW_FX6_601_EXCLUSIVE_END_AND_SDI_MARKERS_P203), 8
        )
        self.assertEqual(len(CAMSET_MODEL_SPECS_P203), 3)

    def test_46_package_init_exports_all_phase203_symbols(self) -> None:
        expected_exports = (
            "PHASE_203_SCHEMA",
            "PHASE_203_VERSION",
            "RealhwBig6NoendCamsetSlot1AndVmcbncm1Report",
            "Pillar1Big6HomeAndZeroEndReport",
            "Pillar2CamsetSlot1AndFirewallReport",
            "Pillar3VmcBncm1AndHdmiTcOutReport",
            "Pillar4Phase203WriteGuardAndMatrixReport",
            "analyze_realhw_big6_noend_camset_slot1_and_vmcbncm1",
            "realhw_big6_noend_camset_slot1_and_vmcbncm1_report_to_dict",
            "evaluate_fx3_big6_home_and_zero_end_boundary",
            "evaluate_camset_slot1_path_and_cross_model_firewall",
            "evaluate_vmcbncm1_tcin_and_hdmi_tcout_routing",
            "evaluate_phase203_write_guard",
            "build_phase203_compat_matrix",
            "serialize_camset_dat_header",
            "verify_camset_dat_model_compatibility",
            "resolve_expected_camset_directory",
        )
        for sym in expected_exports:
            self.assertIn(sym, pkg.__all__)
            self.assertTrue(hasattr(pkg, sym))

    def test_47_cli_subcommand_clean_room_json_exit_zero(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cli_main(
                ["audit-realhw-big6-noend-camset-vmcbncm1", "--clean-room", "--json"]
            )
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())
        self.assertTrue(payload["all_checks_passed"])
        self.assertEqual(payload["auditor_index"], "42/42")
        self.assertEqual(payload["mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(payload["schema_version"], PHASE_203_SCHEMA)

    def test_48_cli_subcommand_auto_mode_json_exit_zero(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cli_main(["audit-realhw-big6-noend-camset-vmcbncm1", "--json"])
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())
        self.assertTrue(payload["all_checks_passed"])
        self.assertEqual(payload["auditor_index"], "42/42")
        self.assertEqual(payload["e_nd_actuator_tx_count"], 0)

    def test_49_run_audit_all_includes_42nd_auditor_clean_room(self) -> None:
        t0 = time.monotonic()
        agg = run_audit_all(clean_room=True)
        dt = time.monotonic() - t0
        self.assertLess(dt, 6.0)
        self.assertTrue(agg["all_checks_passed"])
        self.assertIn("realhw_big6_noend_camset_slot1_and_vmcbncm1_audit", agg)
        sub = agg["realhw_big6_noend_camset_slot1_and_vmcbncm1_audit"]
        self.assertTrue(sub["all_checks_passed"])
        self.assertEqual(sub["auditor_index"], "42/42")
        audit_keys = [k for k in agg.keys() if k.endswith("_audit")]
        self.assertGreaterEqual(len(audit_keys), 42)

    def test_50_camset_cine_ei_operating_mode_allowed_on_slot1(self) -> None:
        res = evaluate_camset_slot1_path_and_cross_model_firewall(
            camera_mode="CINE_EI",
            target_slot="Slot 1",
            media_type="CFEXPRESS_TYPE_A",
            profile_index=10,
        )
        self.assertTrue(res.valid)
        self.assertFalse(res.menu_greyed_out)
        self.assertEqual(res.canonical_filename, "CAMSET10.DAT")

    def test_51_camset_dat_header_invalid_embedded_profile_index_rejected(self) -> None:
        model_id_u32, magic8, bk4_subsys = CAMSET_MODEL_SPECS_P203["ILME-FX3"]
        body_zero = struct.pack(
            "<8sIIHH8s",
            magic8,
            model_id_u32,
            bk4_subsys,
            0,
            CAMSET_DAT_HEADER_BYTES_P203,
            b"CAMSETv7",
        )
        crc = mod_p203.zlib.crc32(body_zero) & 0xFFFFFFFF
        raw_zero = body_zero + struct.pack("<I", crc)
        ok, reason = verify_camset_dat_model_compatibility(
            raw_zero, expected_reader_model="ILME-FX3"
        )
        self.assertFalse(ok)
        self.assertEqual(reason, "CAMSET_DAT_PROFILE_INDEX_INVALID")

    def test_52_camset_arbitrary_wrong_filename_mismatch_rejected(self) -> None:
        res = evaluate_camset_slot1_path_and_cross_model_firewall(
            target_slot="Slot 1",
            media_type="SD",
            profile_index=2,
            requested_card_path="/PRIVATE/SONY/SETTING/FX3/CAMSET/CAMSET03.DAT",
        )
        self.assertFalse(res.valid)
        self.assertTrue(any("CAMSET_CARD_PATH_MISMATCH" in e for e in res.errors))

    def test_53_stills_mode_vmcbncm1_tc_in_remains_unlocked(self) -> None:
        res = evaluate_vmcbncm1_tcin_and_hdmi_tcout_routing(
            physical_port="BODY_MULTI_MICRO_USB",
            requested_direction="TC_IN",
            shooting_mode="Stills",
            tc_make="Preset",
            tc_run="Free Run",
            lock_dwell_sec=20.0,
        )
        self.assertTrue(res.valid)
        self.assertFalse(res.ext_lk_locked)
        self.assertEqual(res.ext_lk_state_label, "UNLOCKED_NON_MOVIE_OR_SQ_MODE")

    def test_54_big6_aperture_with_fx6_nd_fraction_label_and_unblocked_stage_b_rejected(self) -> None:
        res = evaluate_fx3_big6_home_and_zero_end_boundary(
            mode_settings="Fixed/Variable",
            home_custom_key_bound=True,
            home_lower_left_choice="Aperture",
            requested_nd_label="1/128",
            stage_b_end_actuator_tx_blocked=False,
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.e_nd_actuator_tx_count, 0)
        self.assertTrue(
            any("FX3_ABSENT_PHYSICAL_END_ACTUATOR_TX_FORBIDDEN" in e for e in res.errors)
        )

    def test_55_all_four_pillar_subreports_pass_in_clean_room(self) -> None:
        rep = analyze_realhw_big6_noend_camset_slot1_and_vmcbncm1(clean_room=True)
        self.assertTrue(rep.pillar_1_big6_zero_end.passed)
        self.assertTrue(rep.pillar_2_camset_slot1_firewall.passed)
        self.assertTrue(rep.pillar_3_vmcbncm1_hdmi_tc.passed)
        self.assertTrue(rep.pillar_4_write_guard_matrix.passed)

    def test_56_bounded_uxc_and_cpapp_rdonly_scanners_on_temp_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            uxc_p = Path(tmpdir) / "sample.uxc"
            uxc_p.write_bytes(b"uxd\x07\x00\x00\x00\x00Home (Lower Left)\x00ND Filter\x00")
            u_sum = mod_p203._scan_uxc_bounded_rdonly_p203(
                uxc_p,
                pack_name="sample.uxc",
                body_label="TEST",
                required_tokens=("Home (Lower Left)", "ND Filter"),
            )
            self.assertTrue(u_sum.uxc_magic_valid)
            self.assertEqual(u_sum.required_token_hits["Home (Lower Left)"], 1)

            cp_p = Path(tmpdir) / "sample_cp.bin"
            cp_p.write_bytes(b"\x00EXTERNALTC_LOCK\x00HDMI::MSG_PARAM_SET_TC_OUTPUT\x00")
            c_sum = mod_p203._scan_cpapp_bounded_rdonly_p203(
                cp_p,
                binary_name="sample_cp.bin",
                body_label="TEST",
                tokens=("EXTERNALTC_LOCK", "HDMI::MSG_PARAM_SET_TC_OUTPUT"),
                forbidden_tokens=("PID_SET_VARIABLE_ND_VALUE",),
            )
            self.assertEqual(c_sum.marker_hits["EXTERNALTC_LOCK"], 1)
            self.assertEqual(
                c_sum.forbidden_end_actuator_hits["PID_SET_VARIABLE_ND_VALUE"], 0
            )


if __name__ == "__main__":
    unittest.main()
