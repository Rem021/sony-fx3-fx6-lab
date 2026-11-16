"""Phase 140 Dual-Mode Unit Tests (45 tests): Real-Hardware Main Track Part 6 —
FX6 `appFw.so` -> Stock FX3 `libMpr.so` / `osal_uipc` / `DMM` `MAIN` Card-Recording
& Live-View Parameter-Binding ABI Bridge Auditor.
"""

from __future__ import annotations

import ast
import io
import json
import os
import re
import struct
import time
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

import fx3_firmware_lab as lab
from fx3_firmware_lab.__main__ import main as cli_main, run_audit_all
from fx3_firmware_lab.realhw_mpr_dmm_rec_pipeline_bridge_auditor import (
    CORE_MPR_LIFECYCLE_SYMBOLS,
    DMM_MAX_EXTENTS_IN_MPR_REPLY,
    DMM_MODE_ROW_COUNTS,
    FIXED_AREA_TABLE,
    FIXED_AREA_TOTAL_BYTES,
    FX3_DMMCFG_EXPECTED_RULES,
    FX3_DMMCFG_EXPECTED_UNITS,
    FX6_APPFW_SHIM_REQUIRED_MPR_SYMBOLS,
    FX6_DMMCFG_EXPECTED_RULES,
    FX6_DMMCFG_EXPECTED_UNITS,
    FX6_ONLY_MASKED_DMM_SINKS,
    MPR_STATE_STRUCT_SIZES_FX3,
    MPR_STATE_STRUCT_SIZES_FX6,
    PHASE_140_SCHEMA,
    PHASE_140_VERSION,
    SUPPORTED_FX3_DMM_SINKS,
    TARGET_MAIN_DMM_UNIT_IDS,
    UIPC_DATAFLOW_ASYNC_CAP_BYTES,
    UIPC_EXEC_TASK_DESC_BYTES,
    UIPC_MAX_IOCTL_OP,
    UIPC_MOVIE_REC_STATUS_BYTES,
    UNSUPPORTED_FX6_CP_MODES,
    analyze_realhw_mpr_dmm_rec_pipeline_bridge,
    build_clean_room_realhw_mpr_dmm_fixtures,
    evaluate_dmm_sink_topology_and_pool_request,
    evaluate_libmpr_shim_and_abi_compat,
    evaluate_phase140_write_guard,
    evaluate_uipc_queue_and_close_safety,
    parse_dmm_cfg_bytes,
    realhw_mpr_dmm_rec_pipeline_bridge_report_to_dict,
    translate_menu_event_to_cp_parameter,
)


_BYTES_REPR_RE = re.compile(r"(?<![0-9A-Za-z_/.-])b['\"]")
_AUDITOR_PATH = (
    Path(__file__).resolve().parent.parent
    / "fx3_firmware_lab"
    / "realhw_mpr_dmm_rec_pipeline_bridge_auditor.py"
)


class TestRealhwMprDmmRecPipelineBridge(unittest.TestCase):
    """Comprehensive dual-mode tests (45 tests) for the 28th unified auditor."""

    # ---- Mode, Runtime, Determinism & Structural Hygiene ----

    def test_01_clean_room_report_all_pillars_and_runtime(self) -> None:
        t0 = time.perf_counter()
        rep = analyze_realhw_mpr_dmm_rec_pipeline_bridge(clean_room=True)
        dt_cold = time.perf_counter() - t0
        t1 = time.perf_counter()
        rep_warm = analyze_realhw_mpr_dmm_rec_pipeline_bridge(clean_room=True)
        dt_warm = time.perf_counter() - t1

        self.assertTrue(rep.all_checks_passed, rep.errors)
        self.assertEqual(rep.mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(rep.schema_version, PHASE_140_SCHEMA)
        self.assertEqual(rep.phase_version, PHASE_140_VERSION)
        self.assertTrue(rep.o_rdonly_enforced)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertTrue(rep.pillar1_libmpr_abi_diff.passed)
        self.assertTrue(rep.pillar2_dmm_topology.passed)
        self.assertTrue(rep.pillar3_menu_cp_binding.passed)
        self.assertTrue(rep.pillar4_uipc_record_lock.passed)
        self.assertEqual(rep.report_sha256, rep_warm.report_sha256)
        self.assertEqual(len(rep.report_sha256), 64)
        self.assertLess(dt_cold, 0.50 if __import__("os").environ.get("GITHUB_ACTIONS") == "true" else 0.08)
        self.assertLess(dt_warm, 0.25 if __import__("os").environ.get("GITHUB_ACTIONS") == "true" else 0.03)

    def test_02_auto_mode_or_local_donor_runtime_under_025s_and_sizes(self) -> None:
        t0 = time.perf_counter()
        rep = analyze_realhw_mpr_dmm_rec_pipeline_bridge()
        dt = time.perf_counter() - t0
        self.assertTrue(rep.all_checks_passed, rep.errors)
        self.assertIn(rep.mode, ("LOCAL_DONOR_VERIFIED", "CLEAN_ROOM_SYNTHETIC"))
        self.assertLess(dt, 0.25)
        if rep.mode == "LOCAL_DONOR_VERIFIED":
            self.assertEqual(rep.donor_file_sizes.get("fx3_libmpr"), 3_517_008)
            self.assertEqual(rep.donor_file_sizes.get("fx6_libmpr"), 28_921_824)
            self.assertEqual(rep.donor_file_sizes.get("fx6_appfw"), 50_520_424)
            self.assertEqual(rep.donor_file_sizes.get("fx3_dmmcfg"), 66_796)
            self.assertEqual(rep.donor_file_sizes.get("fx6_dmmcfg"), 59_364)
            self.assertEqual(rep.donor_file_sizes.get("fx3_osal_ko"), 76_168)
            self.assertEqual(rep.donor_file_sizes.get("fx6_osal_ko"), 76_360)

    def test_03_forced_clean_room_env_flag_respected(self) -> None:
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}, clear=False):
            rep = analyze_realhw_mpr_dmm_rec_pipeline_bridge()
        self.assertTrue(rep.all_checks_passed, rep.errors)
        self.assertEqual(rep.mode, "CLEAN_ROOM_SYNTHETIC")

    def test_04_missing_donor_falls_back_to_clean_room(self) -> None:
        with mock.patch(
            "fx3_firmware_lab.realhw_mpr_dmm_rec_pipeline_bridge_auditor.resolve_donor_file",
            return_value=None,
        ):
            rep = analyze_realhw_mpr_dmm_rec_pipeline_bridge(clean_room=False)
        self.assertTrue(rep.all_checks_passed, rep.errors)
        self.assertEqual(rep.mode, "CLEAN_ROOM_SYNTHETIC")

    def test_05_json_serialization_has_zero_bytes_repr(self) -> None:
        rep = analyze_realhw_mpr_dmm_rec_pipeline_bridge(clean_room=True)
        payload = realhw_mpr_dmm_rec_pipeline_bridge_report_to_dict(rep)
        json_str = json.dumps(payload, sort_keys=True)
        self.assertIsNone(_BYTES_REPR_RE.search(json_str), "Unexpected Python bytes repr in JSON")
        self.assertIn(PHASE_140_SCHEMA, json_str)

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

    def test_07_package_exports_and_all_include_phase140_symbols(self) -> None:
        expected_symbols = (
            "PHASE_140_SCHEMA",
            "PHASE_140_VERSION",
            "CORE_MPR_LIFECYCLE_SYMBOLS",
            "FX6_APPFW_SHIM_REQUIRED_MPR_SYMBOLS",
            "MPR_STATE_STRUCT_SIZES_FX3",
            "MPR_STATE_STRUCT_SIZES_FX6",
            "TARGET_MAIN_DMM_UNIT_IDS",
            "DMM_MODE_ROW_COUNTS",
            "DMM_MAX_EXTENTS_IN_MPR_REPLY",
            "SUPPORTED_FX3_DMM_SINKS",
            "FX6_ONLY_MASKED_DMM_SINKS",
            "FIXED_AREA_TABLE",
            "FIXED_AREA_TOTAL_BYTES",
            "UIPC_DATAFLOW_ASYNC_CAP_BYTES",
            "RealhwMprDmmRecPipelineBridgeReport",
            "analyze_realhw_mpr_dmm_rec_pipeline_bridge",
            "build_clean_room_realhw_mpr_dmm_fixtures",
            "evaluate_libmpr_shim_and_abi_compat",
            "evaluate_dmm_sink_topology_and_pool_request",
            "translate_menu_event_to_cp_parameter",
            "evaluate_uipc_queue_and_close_safety",
            "evaluate_phase140_write_guard",
            "parse_dmm_cfg_bytes",
            "realhw_mpr_dmm_rec_pipeline_bridge_report_to_dict",
        )
        for sym in expected_symbols:
            self.assertTrue(hasattr(lab, sym), f"Missing export {sym} on fx3_firmware_lab")
            self.assertIn(sym, lab.__all__, f"Missing {sym} in fx3_firmware_lab.__all__")

    def test_08_clean_room_fixtures_roundtrip_and_counts(self) -> None:
        fx = build_clean_room_realhw_mpr_dmm_fixtures()
        self.assertEqual(len(fx), 14)
        d3_sum, d3_units = parse_dmm_cfg_bytes(fx["fx3_dmmcfg"], body_label="FX3_SYNTH", source_mode="SYNTHETIC")
        d6_sum, d6_units = parse_dmm_cfg_bytes(fx["fx6_dmmcfg"], body_label="FX6_SYNTH", source_mode="SYNTHETIC")
        self.assertEqual(d3_sum.units_count, FX3_DMMCFG_EXPECTED_UNITS)
        self.assertEqual(d6_sum.units_count, FX6_DMMCFG_EXPECTED_UNITS)
        self.assertEqual(d3_sum.rules_count, FX3_DMMCFG_EXPECTED_RULES)
        self.assertEqual(d6_sum.rules_count, FX6_DMMCFG_EXPECTED_RULES)
        self.assertEqual(d3_sum.target_20_units_present, 20)
        self.assertEqual(d6_sum.target_20_units_present, 20)
        self.assertEqual(len(set(d3_units) & set(d6_units)), 548)
        self.assertEqual(len(set(d3_units) - set(d6_units)), 55)
        self.assertEqual(len(set(d6_units) - set(d3_units)), 8)

    def test_09_cli_audit_realhw_mpr_dmm_bridge_clean_room_and_auto(self) -> None:
        for argv in (
            ["audit-realhw-mpr-dmm-bridge", "--clean-room", "--json"],
            ["audit-realhw-mpr-dmm-bridge", "--json"],
        ):
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = cli_main(argv)
            self.assertEqual(rc, 0)
            obj = json.loads(buf.getvalue())
            self.assertTrue(obj["all_checks_passed"])
            self.assertTrue(obj["o_rdonly_enforced"])
            self.assertFalse(obj["persistent_emmc_writes_authorized"])

    def test_10_run_audit_all_reaches_28_auditors(self) -> None:
        summary = run_audit_all(clean_room=True)
        self.assertTrue(summary["all_checks_passed"])
        audit_keys = [k for k in summary if k.endswith("_audit")]
        self.assertGreaterEqual(len(audit_keys), 28)
        self.assertIn("realhw_mpr_dmm_rec_pipeline_bridge_audit", summary)

    def test_11_cli_audit_all_clean_room_returns_zero_with_28_keys(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cli_main(["audit-all", "--clean-room", "--json"])
        self.assertEqual(rc, 0)
        obj = json.loads(buf.getvalue())
        self.assertTrue(obj["all_checks_passed"])
        self.assertGreaterEqual(len([k for k in obj if k.endswith("_audit")]), 28)

    # ---- Pillar 1: LIBMPR_EXPORT_AND_OPEN_START_CLOSE_ABI_DIFF ----

    def test_12_pillar1_shared_core_lifecycle_and_parameter_control_parity(self) -> None:
        rep = analyze_realhw_mpr_dmm_rec_pipeline_bridge(clean_room=True)
        p1 = rep.pillar1_libmpr_abi_diff
        self.assertTrue(p1.passed)
        self.assertEqual(p1.core_lifecycle_symbols_present_count, len(CORE_MPR_LIFECYCLE_SYMBOLS))
        self.assertGreater(p1.parameter_control_fx3_count, 0)
        self.assertGreater(p1.parameter_control_fx6_count, 0)
        self.assertTrue(p1.fx3_libmpr.has_libsecvlt_dep)
        self.assertFalse(p1.fx6_libmpr.has_libsecvlt_dep)

    def test_13_pillar1_fx6_appfw_passthrough_vs_15_shim_symbols(self) -> None:
        rep = analyze_realhw_mpr_dmm_rec_pipeline_bridge(clean_room=True)
        p1 = rep.pillar1_libmpr_abi_diff
        self.assertGreater(p1.fx6_appfw_passthrough_count, 0)
        self.assertEqual(len(p1.fx6_appfw_shim_required_symbols), 15)
        self.assertEqual(
            p1.fx6_appfw_shim_required_symbols,
            tuple(sorted(FX6_APPFW_SHIM_REQUIRED_MPR_SYMBOLS)),
        )

    def test_14_pillar1_libosal_uipc_and_im_elf_dt_needed_parity(self) -> None:
        rep = analyze_realhw_mpr_dmm_rec_pipeline_bridge(clean_room=True)
        p1 = rep.pillar1_libmpr_abi_diff
        self.assertTrue(p1.libosal_uipc_exports_identical)
        for im_elf in (p1.fx3_im_elf, p1.fx6_im_elf):
            self.assertIn("libosal_uipc.so", im_elf.dt_needed)
            self.assertIn("libbackup.so", im_elf.dt_needed)
            self.assertIn("libIMDB.so", im_elf.dt_needed)

    def test_15_pillar1_struct_size_divergence_isolated(self) -> None:
        rep = analyze_realhw_mpr_dmm_rec_pipeline_bridge(clean_room=True)
        p1 = rep.pillar1_libmpr_abi_diff
        self.assertEqual(p1.g_videoparamcomb_bytes_fx3, 312)
        self.assertEqual(p1.g_videoparamcomb_bytes_fx6, 480)
        self.assertEqual(p1.s_movierecinfo_bytes_fx3, 3144)
        self.assertEqual(p1.s_movierecinfo_bytes_fx6, 5248)
        self.assertTrue(p1.direct_struct_dereference_blocked)
        self.assertEqual(MPR_STATE_STRUCT_SIZES_FX3["_ZN3mpr16s_movieRecStatusE"], MPR_STATE_STRUCT_SIZES_FX6["_ZN3mpr16s_movieRecStatusE"])
        self.assertEqual(MPR_STATE_STRUCT_SIZES_FX3["_ZN3mpr13s_movieRWlockE"], MPR_STATE_STRUCT_SIZES_FX6["_ZN3mpr13s_movieRWlockE"])

    def test_16_eval_libmpr_passthrough_symbol_passes(self) -> None:
        for sym in CORE_MPR_LIFECYCLE_SYMBOLS:
            res = evaluate_libmpr_shim_and_abi_compat(symbol_name=sym)
            self.assertTrue(res.valid, sym)
            self.assertEqual(res.status, "PASS_THROUGH_COMPATIBLE")
            self.assertFalse(res.shim_interceptor_needed)

    def test_17_eval_libmpr_15_shim_required_symbols_classified(self) -> None:
        self.assertEqual(len(FX6_APPFW_SHIM_REQUIRED_MPR_SYMBOLS), 15)
        for sym in FX6_APPFW_SHIM_REQUIRED_MPR_SYMBOLS:
            res = evaluate_libmpr_shim_and_abi_compat(symbol_name=sym)
            self.assertTrue(res.valid, sym)
            self.assertEqual(res.status, "LD_PRELOAD_SHIM_REQUIRED")
            self.assertTrue(res.shim_interceptor_needed)
            self.assertTrue(res.struct_isolation_required)

    def test_18_eval_libmpr_direct_struct_dereference_blocked(self) -> None:
        res = evaluate_libmpr_shim_and_abi_compat(
            symbol_name="_ZN3mpr16g_videoParamCombE",
            direct_struct_deref_attempted=True,
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.status, "BLOCKED_STRUCT_ABI_MISMATCH")
        self.assertTrue(res.struct_isolation_required)

    def test_19_eval_libmpr_unknown_symbol_blocked(self) -> None:
        res = evaluate_libmpr_shim_and_abi_compat(symbol_name="_ZN3mpr22NonExistentFx6SymbolEv")
        self.assertFalse(res.valid)
        self.assertEqual(res.status, "BLOCKED_UNRESOLVED_MPR_SYMBOL")

    # ---- Pillar 2: DMM_CFG_NODE_TOPOLOGY_AND_UNSUPPORTED_SINK_MASK ----

    def test_20_pillar2_dmmcfg_counts_and_cross_body_diff(self) -> None:
        rep = analyze_realhw_mpr_dmm_rec_pipeline_bridge(clean_room=True)
        p2 = rep.pillar2_dmm_topology
        self.assertTrue(p2.passed)
        self.assertEqual(p2.fx3_dmmcfg.units_count, 603)
        self.assertEqual(p2.fx3_dmmcfg.rules_count, 290)
        self.assertEqual(p2.fx6_dmmcfg.units_count, 556)
        self.assertEqual(p2.fx6_dmmcfg.rules_count, 259)
        self.assertEqual(p2.shared_unit_count, 548)
        self.assertEqual(p2.fx3_only_unit_count, 55)
        self.assertEqual(p2.fx6_only_unit_count, 8)

    def test_21_pillar2_all_20_target_main_units_present_with_1_extent(self) -> None:
        rep = analyze_realhw_mpr_dmm_rec_pipeline_bridge(clean_room=True)
        p2 = rep.pillar2_dmm_topology
        self.assertEqual(len(TARGET_MAIN_DMM_UNIT_IDS), 20)
        self.assertEqual(p2.fx3_dmmcfg.target_20_units_present, 20)
        self.assertEqual(p2.fx6_dmmcfg.target_20_units_present, 20)
        self.assertEqual(p2.fx3_dmmcfg.target_units_max_extent, 1)
        self.assertEqual(p2.fx6_dmmcfg.target_units_max_extent, 1)
        self.assertLessEqual(p2.fx3_dmmcfg.max_extents_per_unit, DMM_MAX_EXTENTS_IN_MPR_REPLY)
        self.assertLessEqual(p2.fx6_dmmcfg.max_extents_per_unit, DMM_MAX_EXTENTS_IN_MPR_REPLY)

    def test_22_pillar2_mode_row_counts_21_25_31_32_verified(self) -> None:
        rep = analyze_realhw_mpr_dmm_rec_pipeline_bridge(clean_room=True)
        p2 = rep.pillar2_dmm_topology
        self.assertEqual(
            p2.mode_row_counts_verified,
            {"21": 7, "25": 10, "31": 13, "32": 19},
        )

    def test_23_eval_dmm_sink_fx3_supported_sinks_verified(self) -> None:
        for sink, mode in zip(SUPPORTED_FX3_DMM_SINKS, sorted(DMM_MODE_ROW_COUNTS)):
            res = evaluate_dmm_sink_topology_and_pool_request(sink_name=sink, dmm_mode=mode, extent_count=1)
            self.assertTrue(res.valid, sink)
            self.assertEqual(res.status, "FX3_DMM_SINK_VERIFIED")
            self.assertFalse(res.masked_to_stub)
            self.assertTrue(res.cp_pool_request_issued)
            self.assertEqual(res.reply_bytes, 0x18 + 16)

    def test_24_eval_dmm_sink_fx6_only_masked_to_stub(self) -> None:
        for sink in FX6_ONLY_MASKED_DMM_SINKS:
            res = evaluate_dmm_sink_topology_and_pool_request(
                sink_name=sink, dmm_mode=21, extent_count=1, mask_fx6_only_sinks=True
            )
            self.assertTrue(res.valid, sink)
            self.assertEqual(res.status, "MASKED_FX6_ONLY_SINK_STUB")
            self.assertTrue(res.masked_to_stub)
            self.assertFalse(res.cp_pool_request_issued)

    def test_25_eval_dmm_sink_unmasked_fx6_only_blocked(self) -> None:
        for sink in FX6_ONLY_MASKED_DMM_SINKS:
            res = evaluate_dmm_sink_topology_and_pool_request(
                sink_name=sink, dmm_mode=21, extent_count=1, mask_fx6_only_sinks=False
            )
            self.assertFalse(res.valid)
            self.assertEqual(res.status, "BLOCKED_UNMASKED_FX6_ONLY_DMM_SINK")

    def test_26_eval_dmm_sink_extent_overflow_and_invalid_reply_type_blocked(self) -> None:
        over = evaluate_dmm_sink_topology_and_pool_request(sink_name="MAIN_CARD_RECORDER", extent_count=9)
        self.assertFalse(over.valid)
        self.assertEqual(over.status, "BLOCKED_DMM_EXTENT_OVERFLOW")

        zero = evaluate_dmm_sink_topology_and_pool_request(sink_name="MAIN_CARD_RECORDER", extent_count=0)
        self.assertFalse(zero.valid)

        bad_type = evaluate_dmm_sink_topology_and_pool_request(
            sink_name="MAIN_CARD_RECORDER", reply_type=0x9999
        )
        self.assertFalse(bad_type.valid)
        self.assertEqual(bad_type.status, "BLOCKED_INVALID_DMM_REPLY_TYPE")

        bad_mode = evaluate_dmm_sink_topology_and_pool_request(
            sink_name="MAIN_CARD_RECORDER", dmm_mode=99
        )
        self.assertFalse(bad_mode.valid)
        self.assertEqual(bad_mode.status, "BLOCKED_UNSUPPORTED_DMM_MODE")

    def test_27_parse_dmm_cfg_bytes_rejects_truncated_buffer(self) -> None:
        with self.assertRaises(ValueError):
            parse_dmm_cfg_bytes(b"\x00" * 16, body_label="TRUNCATED", source_mode="SYNTHETIC")

    # ---- Pillar 3: MENU_EVENT_TO_CP_PARAMETER_BINDING_CONTRACT ----

    def test_28_pillar3_appfw_marker_hits_and_6_domains_verified(self) -> None:
        rep = analyze_realhw_mpr_dmm_rec_pipeline_bridge(clean_room=True)
        p3 = rep.pillar3_menu_cp_binding
        self.assertTrue(p3.passed)
        self.assertEqual(p3.fx3_appfw_marker_hits, 10)
        self.assertEqual(p3.fx6_appfw_marker_hits, 10)
        self.assertEqual(p3.domains_verified_count, 6)
        self.assertEqual(p3.unsupported_modes_blocked, UNSUPPORTED_FX6_CP_MODES)

    def test_29_domain_base_iso_800_and_12800_positive_and_invalid_rejected(self) -> None:
        for base in (800, 12800):
            res = translate_menu_event_to_cp_parameter(
                domain="BASE_ISO", params={"base_iso": base, "ei_index": base}
            )
            self.assertTrue(res.valid)
            self.assertEqual(res.cp_payload["base_iso"], base)
        bad_iso = translate_menu_event_to_cp_parameter(domain="BASE_ISO", params={"base_iso": 3200})
        self.assertFalse(bad_iso.valid)
        self.assertEqual(bad_iso.status, "BLOCKED_INVALID_BASE_ISO")
        bad_ei = translate_menu_event_to_cp_parameter(
            domain="BASE_ISO", params={"base_iso": 800, "ei_index": 102400}
        )
        self.assertFalse(bad_ei.valid)
        self.assertEqual(bad_ei.status, "BLOCKED_INVALID_EI_INDEX")

    def test_30_domain_frame_rate_sq_positive_and_4k_over_120_rejected(self) -> None:
        fhd_240 = translate_menu_event_to_cp_parameter(
            domain="FRAME_RATE_SQ",
            params={"resolution": "FHD", "sensor_fps": 240.0, "project_fps": 23.976},
        )
        self.assertTrue(fhd_240.valid)
        self.assertTrue(fhd_240.cp_payload["sq_off_speed"])
        self.assertTrue(fhd_240.cp_payload["audio_muted"])

        bad_4k_240 = translate_menu_event_to_cp_parameter(
            domain="FRAME_RATE_SQ",
            params={"resolution": "4K_DCI", "sensor_fps": 240.0, "project_fps": 24.0},
        )
        self.assertFalse(bad_4k_240.valid)
        self.assertEqual(bad_4k_240.status, "BLOCKED_4K_OVER_120FPS")

    def test_31_domain_frame_rate_5k_open_gate_blocked(self) -> None:
        res = translate_menu_event_to_cp_parameter(
            domain="FRAME_RATE_SQ",
            params={"resolution": "5K_OPEN_GATE", "sensor_fps": 24.0, "project_fps": 24.0},
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.status, "BLOCKED_5K_OPEN_GATE_UNSUPPORTED_ON_FX3_CP")

    def test_32_domain_shutter_angle_180_at_24p_and_bounds(self) -> None:
        res = translate_menu_event_to_cp_parameter(
            domain="EXPOSURE_SHUTTER_ANGLE",
            params={"shutter_angle_deg": 180.0, "fps": 24.0},
        )
        self.assertTrue(res.valid)
        self.assertAlmostEqual(float(res.cp_payload["cp_exposure_sec"]), 1.0 / 48.0, places=6)
        self.assertEqual(res.cp_payload["cp_shutter_speed_reciprocal"], 48.0)
        self.assertEqual(res.mech_shutter_actuations, 0)
        self.assertTrue(res.cp_payload["electronic_rolling_shutter"])

        bad = translate_menu_event_to_cp_parameter(
            domain="EXPOSURE_SHUTTER_ANGLE",
            params={"shutter_angle_deg": 720.0, "fps": 24.0},
        )
        self.assertFalse(bad.valid)
        self.assertEqual(bad.status, "BLOCKED_SHUTTER_ANGLE_OUT_OF_RANGE")

    def test_33_domain_white_balance_kelvin_and_tint_bounds(self) -> None:
        ok = translate_menu_event_to_cp_parameter(
            domain="WHITE_BALANCE", params={"kelvin": 5600, "tint": -12, "preset": "MEMORY_B"}
        )
        self.assertTrue(ok.valid)
        self.assertTrue(ok.cp_payload["soft_mapped_wht_bal_switch"])
        self.assertEqual(ok.gpio_faults, 0)

        bad_k = translate_menu_event_to_cp_parameter(domain="WHITE_BALANCE", params={"kelvin": 18000})
        self.assertFalse(bad_k.valid)
        self.assertEqual(bad_k.status, "BLOCKED_WB_KELVIN_OUT_OF_RANGE")
        bad_t = translate_menu_event_to_cp_parameter(domain="WHITE_BALANCE", params={"tint": 120})
        self.assertFalse(bad_t.valid)
        self.assertEqual(bad_t.status, "BLOCKED_WB_TINT_OUT_OF_RANGE")

    def test_34_domain_color_look_mlut_profiles_and_slot_bounds(self) -> None:
        ok = translate_menu_event_to_cp_parameter(
            domain="COLOR_LOOK_MLUT", params={"look_profile": "S_CINETONE", "mlut_slot": 4}
        )
        self.assertTrue(ok.valid)
        self.assertTrue(ok.cp_payload["volatile_ram_staged"])

        bad_look = translate_menu_event_to_cp_parameter(
            domain="COLOR_LOOK_MLUT", params={"look_profile": "NONEXISTENT_LOG"}
        )
        self.assertFalse(bad_look.valid)
        self.assertEqual(bad_look.status, "BLOCKED_UNKNOWN_LOOK_PROFILE")
        bad_slot = translate_menu_event_to_cp_parameter(
            domain="COLOR_LOOK_MLUT", params={"look_profile": "SLOG3_SGAMUT3_CINE", "mlut_slot": 99}
        )
        self.assertFalse(bad_slot.valid)
        self.assertEqual(bad_slot.status, "BLOCKED_INVALID_MLUT_SLOT")

    def test_35_domain_rec_start_stop_and_card_class_gate(self) -> None:
        stop_ev = translate_menu_event_to_cp_parameter(
            domain="REC_START_STOP_MEDIA",
            params={"action": "REC_STOP", "slot_mode": "RELAY", "rec_format": "XAVC_S_HD", "card_speed_class": "V60"},
        )
        self.assertTrue(stop_ev.valid)
        self.assertEqual(stop_ev.cp_payload["enc_open_file_format"], 3)
        self.assertEqual(stop_ev.cp_payload["mpr_sequence"], ("RecStop", "ExecEncStop", "ExecEncClose"))

        slow_card = translate_menu_event_to_cp_parameter(
            domain="REC_START_STOP_MEDIA",
            params={"action": "REC_START", "slot_mode": "SLOT_A", "rec_format": "XAVC_S_I_4K", "card_speed_class": "V30"},
        )
        self.assertFalse(slow_card.valid)
        self.assertEqual(slow_card.status, "BLOCKED_INSUFFICIENT_CARD_SPEED_CLASS")

    def test_36_unsupported_fx6_hardware_modes_and_unknown_domain_blocked(self) -> None:
        for mode_flag in UNSUPPORTED_FX6_CP_MODES:
            res = translate_menu_event_to_cp_parameter(
                domain="BASE_ISO", params={"unsupported_mode": mode_flag}
            )
            self.assertFalse(res.valid)
            self.assertEqual(res.status, "BLOCKED_UNSUPPORTED_FX6_HARDWARE_MODE")
        unk = translate_menu_event_to_cp_parameter(domain="UNKNOWN_DOMAIN", params={})
        self.assertFalse(unk.valid)
        self.assertEqual(unk.status, "BLOCKED_UNKNOWN_PARAMETER_DOMAIN")

    # ---- Pillar 4: UIPC_QUEUE_GUARD_AND_RECORD_LOCK_SAFETY ----

    def test_37_pillar4_osal_ko_and_zero_persistent_emmc_auth(self) -> None:
        rep = analyze_realhw_mpr_dmm_rec_pipeline_bridge(clean_room=True)
        p4 = rep.pillar4_uipc_record_lock
        self.assertTrue(p4.passed)
        self.assertEqual(p4.fixed_area_total_bytes, FIXED_AREA_TOTAL_BYTES)
        self.assertEqual(p4.dataflow_async_cap_bytes, UIPC_DATAFLOW_ASYNC_CAP_BYTES)
        self.assertEqual(p4.exec_task_desc_bytes, UIPC_EXEC_TASK_DESC_BYTES)
        self.assertEqual(p4.movie_rec_status_bytes, UIPC_MOVIE_REC_STATUS_BYTES)
        self.assertFalse(p4.persistent_emmc_writes_authorized)
        self.assertEqual(p4.emmc_mutation_bytes, 0)
        self.assertEqual(p4.calibration_mutation_bytes, 0)

    def test_38_eval_uipc_fixed_area_0_to_4_bounds_and_overflow_blocked(self) -> None:
        self.assertEqual(sum(ln for _, ln in FIXED_AREA_TABLE.values()), FIXED_AREA_TOTAL_BYTES)
        ok_area2 = evaluate_uipc_queue_and_close_safety(area_type=2, payload_bytes=384)
        self.assertTrue(ok_area2.valid)
        overflow_area2 = evaluate_uipc_queue_and_close_safety(area_type=2, payload_bytes=513)
        self.assertFalse(overflow_area2.valid)
        self.assertIn("BLOCKED_FIXED_AREA_OVERFLOW", overflow_area2.errors[0])
        bad_area = evaluate_uipc_queue_and_close_safety(area_type=9, payload_bytes=128)
        self.assertFalse(bad_area.valid)
        self.assertEqual(bad_area.status, "BLOCKED_INVALID_FIXED_AREA_TYPE")

    def test_39_eval_uipc_valloc_align64_and_dataflow_384b_cap(self) -> None:
        # align64(align4(152) + 24 + 4 + 40) = align64(220) = 256
        res = evaluate_uipc_queue_and_close_safety(area_type=2, payload_bytes=152)
        self.assertTrue(res.valid)
        self.assertEqual(res.alloc_bytes, 256)

        over_cap = evaluate_uipc_queue_and_close_safety(area_type=0, payload_bytes=385)
        self.assertFalse(over_cap.valid)
        self.assertEqual(over_cap.status, "BLOCKED_DATAFLOW_PAYLOAD_CAP_EXCEEDED")

    def test_40_eval_uipc_ioctl_op_range_unmapped_base_and_addr_limit_blocked(self) -> None:
        bad_op = evaluate_uipc_queue_and_close_safety(ioctl_op=UIPC_MAX_IOCTL_OP + 1)
        self.assertFalse(bad_op.valid)
        self.assertEqual(bad_op.status, "BLOCKED_UIPC_OP_OUT_OF_RANGE")

        no_base = evaluate_uipc_queue_and_close_safety(ioctl_op=10, user_map_base=0)
        self.assertFalse(no_base.valid)
        self.assertEqual(no_base.status, "BLOCKED_UIPC_UNMAPPED_USER_BASE")

        # op 16 explicitly permits zero user_map_base in osal_uipc.ko
        op16_ok = evaluate_uipc_queue_and_close_safety(ioctl_op=16, user_map_base=0)
        self.assertTrue(op16_ok.valid)

        bad_lim = evaluate_uipc_queue_and_close_safety(ptr_addr=0x7FFFF000, addr_limit=0x7FFFF000)
        self.assertFalse(bad_lim.valid)
        self.assertEqual(bad_lim.status, "BLOCKED_UIPC_ADDR_LIMIT_EXCEEDED")

    def test_41_eval_uipc_virtual_domain_ptr_required_vs_physical_blocked(self) -> None:
        res = evaluate_uipc_queue_and_close_safety(uses_virtual_domain_ptr=False)
        self.assertFalse(res.valid)
        self.assertEqual(res.status, "BLOCKED_PHYSICAL_PTR_DOMAIN_DEREF")

    def test_42_eval_uipc_callback_copy_before_free_and_rwlock_pairing(self) -> None:
        uaf = evaluate_uipc_queue_and_close_safety(copied_before_free=False)
        self.assertFalse(uaf.valid)
        self.assertEqual(uaf.status, "BLOCKED_USE_AFTER_FREE_CALLBACK_PTR")

        leak = evaluate_uipc_queue_and_close_safety(rwlock_paired=False)
        self.assertFalse(leak.valid)
        self.assertEqual(leak.status, "BLOCKED_MOVIE_RWLOCK_LEAK")

    def test_43_eval_uipc_exec_enc_close_counter_prevents_rsv_hang(self) -> None:
        # counter 1 -> 0 executes Codec::EncClose
        c1 = evaluate_uipc_queue_and_close_safety(close_counter_before=1, decrement_flag=0)
        self.assertTrue(c1.valid)
        self.assertEqual(c1.close_counter_after, 0)
        self.assertTrue(c1.codec_close_executed)
        self.assertTrue(c1.rsv_corruption_prevented)

        # counter 2 -> 1 skips close because active writer remains
        c2 = evaluate_uipc_queue_and_close_safety(close_counter_before=2, decrement_flag=0)
        self.assertFalse(c2.valid)
        self.assertEqual(c2.close_counter_after, 1)
        self.assertFalse(c2.codec_close_executed)
        self.assertEqual(c2.status, "CLOSE_SKIPPED_ACTIVE_WRITER_REMAINING")

    def test_44_eval_phase140_write_guard_allows_volatile_and_blocks_emmc(self) -> None:
        ok = evaluate_phase140_write_guard("/tmp/stage_b/dmm_pool_mask.json")
        self.assertTrue(ok.valid)
        self.assertTrue(ok.volatile_ram_staged)
        self.assertFalse(ok.persistent_write_blocked)

        for target in (
            "/dev/nflasha15/usr/lib/libmpr.so",
            "/dev/cnflasha0",
            "/dev/mmcblk0p2",
            "p2:/Backup.bin",
            "/tmp/Backup.bin",
            "p8:/cpapp-b.bin",
        ):
            blk = evaluate_phase140_write_guard(target)
            self.assertFalse(blk.valid, target)
            self.assertTrue(blk.persistent_write_blocked, target)
            self.assertEqual(blk.emmc_mutation_bytes, 0)
            self.assertEqual(blk.calibration_mutation_bytes, 0)

    def test_45_local_donor_specific_invariants_when_present(self) -> None:
        rep = analyze_realhw_mpr_dmm_rec_pipeline_bridge()
        self.assertTrue(rep.all_checks_passed, rep.errors)
        if rep.mode == "LOCAL_DONOR_VERIFIED":
            p1 = rep.pillar1_libmpr_abi_diff
            p2 = rep.pillar2_dmm_topology
            self.assertEqual(p1.shared_export_count, 3102)
            self.assertEqual(p1.fx3_only_export_count, 439)
            self.assertEqual(p1.fx6_only_export_count, 1169)
            self.assertEqual(p1.fx6_appfw_mpr_import_count, 89)
            self.assertEqual(p1.fx6_appfw_passthrough_count, 74)
            self.assertEqual(len(p1.fx6_appfw_shim_required_symbols), 15)
            self.assertEqual(p1.parameter_control_fx3_count, 738)
            self.assertEqual(p1.parameter_control_fx6_count, 720)
            self.assertEqual(p2.fx3_dmmcfg.file_bytes, 66_796)
            self.assertEqual(p2.fx6_dmmcfg.file_bytes, 59_364)
            self.assertEqual(p2.shared_unit_count, 548)
            self.assertEqual(p2.fx3_only_unit_count, 55)
            self.assertEqual(p2.fx6_only_unit_count, 8)


if __name__ == "__main__":
    unittest.main()
