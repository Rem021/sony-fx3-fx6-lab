#!/usr/bin/env python3
"""Phase 145 Test Suite — Stage 25 Real-Hardware Main Track Part 8:
FX6 `appFw.so` -> Stock FX3 `libmpr.so` / `DmmCfg.bin` Card-Recording Co-Emulator.

Exercises 46 fast dual-mode unit, `LD_PRELOAD` + `libsecvlt.so` + `ld-2.25.so`
64 KiB `PT_LOAD` alignment, Stock FX3 `DmmCfg.bin` 20-unit pool & leak verifier,
physical `REC` -> 6 `ParameterControl` -> `M4ROOT/CLIP` + NRT XML lifecycle,
fault-injection resilience, Stage 25 suite integration, CLI, runtime budget, and
source-hygiene checks across BOTH Local Donor (`os.O_RDONLY`) and
`FX3_FX6_FORCE_CLEAN_ROOM=1` modes, strictly offline with
`persistent_emmc_writes_authorized == False` and `emmc_nflasha_write_count == 0`.
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import contextlib
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
import realhw_mpr_dmm_recording_coemulator as p145  # noqa: E402


_AUDIT_CACHE: dict = {}


def _get_clean_room_audit() -> dict:
    if "clean_room" not in _AUDIT_CACHE:
        _AUDIT_CACHE["clean_room"] = p145.run_phase145_realhw_mpr_dmm_rec_coemulator(
            force_clean_room=True
        )
    return _AUDIT_CACHE["clean_room"]


class TestPhase145DonorAuditAndParsers(unittest.TestCase):
    """Verify O_RDONLY donor inspection, clean-room fallback, and binary parsers."""

    def test_01_clean_room_donor_audit_verifies_all_contracts(self) -> None:
        audit = p145.inspect_phase145_donors(force_clean_room=True)
        self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(audit.access_mode, "O_RDONLY")
        self.assertEqual(audit.donor_files_inspected, 0)
        self.assertTrue(audit.all_contracts_verified, msg=audit.errors)
        self.assertEqual(audit.errors, ())
        self.assertEqual(audit.fx3_libmpr.export_count, 3541)
        self.assertEqual(audit.fx6_libmpr.export_count, 4271)
        self.assertTrue(audit.fx3_libmpr.has_libsecvlt_dep)
        self.assertFalse(audit.fx6_libmpr.has_libsecvlt_dep)
        self.assertEqual(audit.passthrough_mpr_count, 74)
        self.assertEqual(audit.shim_required_mpr_count, 15)
        self.assertEqual(audit.shared_main_dmm_units_count, 20)
        self.assertEqual(audit.fx3_ap_dmmcfg.units_count, 603)
        self.assertEqual(audit.fx6_ap_dmmcfg.units_count, 556)
        self.assertEqual(audit.fx3_cp_dmmcfg.units_count, 348)
        self.assertIn("ilc32g12m-ipsxmp", audit.fx3_ap_dmmcfg.version_ascii)
        self.assertIn("ilc8g8g-ipsxcp", audit.fx3_cp_dmmcfg.version_ascii)

    def test_02_force_clean_room_env_disables_local_donor_paths(self) -> None:
        env = {p145.ENV_FORCE_CLEAN_ROOM: "1"}
        self.assertTrue(p145.is_forced_clean_room(env))
        paths = p145.resolve_phase145_donor_paths(env=env)
        self.assertEqual(len(paths), 9)
        for p in paths.values():
            self.assertIn(p145.CLEAN_ROOM_SENTINEL_DIRNAME, str(p))
        audit = p145.inspect_phase145_donors(env=env)
        self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(audit.all_contracts_verified)

    def test_03_local_donor_o_rdonly_audit_when_present_or_clean_room(self) -> None:
        if p145.is_forced_clean_room():
            audit = p145.inspect_phase145_donors()
            self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")
            return
        paths = p145.resolve_phase145_donor_paths()
        audit = p145.inspect_phase145_donors()
        self.assertTrue(audit.all_contracts_verified, msg=audit.errors)
        if all(p.is_file() for p in paths.values()):
            self.assertEqual(audit.source_mode, "LOCAL_DONOR_RDONLY")
            self.assertEqual(audit.donor_files_inspected, 9)
            self.assertEqual(audit.fx3_libmpr.file_bytes, 3_517_008)
            self.assertEqual(audit.fx6_libmpr.file_bytes, 28_921_824)
            self.assertEqual(audit.fx6_appfw.file_bytes, 50_520_424)
            self.assertEqual(audit.fx3_ap_dmmcfg.file_bytes, 66_796)
            self.assertEqual(audit.fx6_ap_dmmcfg.file_bytes, 59_364)
            self.assertEqual(audit.fx3_cp_dmmcfg.file_bytes, 43_320)
            self.assertEqual(audit.fx3_libsecvlt.file_bytes, 10_216)
        else:
            self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_04_missing_donor_root_falls_back_to_clean_room(self) -> None:
        env = {
            p145.ENV_MAC_WORK_ROOT: "/nonexistent_phase145_mac_work_root",
            p145.ENV_MAIN_LAB_WORK_ROOT: "/nonexistent_phase145_main_work_root",
        }
        audit = p145.inspect_phase145_donors(force_clean_room=True, env=env)
        self.assertEqual(audit.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(audit.donor_files_inspected, 0)
        self.assertTrue(audit.all_contracts_verified)

    def test_05_stage25_clean_room_and_local_execution_under_0p15s(self) -> None:
        t0 = time.monotonic()
        rep_clean = p145.run_phase145_realhw_mpr_dmm_rec_coemulator(force_clean_room=True)
        dt_clean = time.monotonic() - t0
        self.assertTrue(rep_clean["all_checks_passed"])
        self.assertLess(dt_clean, 0.15)

        t1 = time.monotonic()
        rep_mode = p145.run_phase145_realhw_mpr_dmm_rec_coemulator()
        dt_mode = time.monotonic() - t1
        self.assertTrue(rep_mode["all_checks_passed"])
        self.assertLess(dt_mode, 0.15)

    def test_06_clean_room_synthetic_dmmcfg_parser_roundtrip(self) -> None:
        raw = p145._build_synthetic_dmmcfg(
            rules_count=12,
            unit_ids=list(p145.TARGET_MAIN_DMM_UNIT_IDS) + [9991, 9992],
            version_str="for ilc32g12m-ipsxmp     2025/06/20 15:43:19",
        )
        summary, units = p145.parse_dmm_cfg_bytes(
            raw, body_label="TEST_AP", source_mode="CLEAN_ROOM_SYNTHETIC"
        )
        self.assertEqual(summary.roots_count, 1)
        self.assertEqual(summary.rules_count, 12)
        self.assertEqual(summary.units_count, 22)
        self.assertEqual(summary.target_20_units_present, 20)
        self.assertEqual(len(units), 22)

    def test_07_parse_dmm_cfg_bytes_rejects_truncated_and_trailing_bytes(self) -> None:
        raw = p145._build_synthetic_dmmcfg(
            rules_count=2,
            unit_ids=[700, 701],
            version_str="for ilc32g12m-ipsxmp     2025/06/20 15:43:19",
        )
        with self.assertRaises(ValueError):
            p145.parse_dmm_cfg_bytes(raw[:-5], body_label="TRUNC")
        with self.assertRaises(ValueError):
            p145.parse_dmm_cfg_bytes(raw + b"\x00", body_label="TRAILING")

    def test_08_parse_elf64_rejects_invalid_magic_or_unaligned_ptload(self) -> None:
        with self.assertRaises(ValueError):
            p145._parse_elf64_with_ptload(
                b"NOT_AN_ELF" * 16,
                library_name="bad.so",
                body_label="TEST",
                source_mode="CLEAN_ROOM_SYNTHETIC",
            )
        bad_elf = p145._build_synthetic_elf64_pt64k(
            exports=[("foo", 0)],
            imports=["bar"],
            dt_needed=("libc.so.6",),
            p_align=0x1000,
        )
        summary, _, _, _ = p145._parse_elf64_with_ptload(
            bad_elf,
            library_name="unaligned.so",
            body_label="TEST",
            source_mode="CLEAN_ROOM_SYNTHETIC",
        )
        self.assertFalse(summary.ld225_64k_aligned)
        self.assertEqual(summary.pt_load_align_hex, "0x1000")


class TestPhase145PillarALdPreloadLibmprShim(unittest.TestCase):
    """Pillar A — LD_PRELOAD libmpr.so + libsecvlt.so Symbol & ABI Shim Co-Emulator."""

    def test_09_all_74_passthrough_mpr_symbols_route_to_stock_fx3(self) -> None:
        self.assertEqual(len(p145.ALL_74_PASSTHROUGH_SYMBOLS), 74)
        for sym in p145.ALL_74_PASSTHROUGH_SYMBOLS:
            res = p145.simulate_libmpr_preload_call(sym)
            self.assertTrue(res.valid, msg=res)
            self.assertEqual(res.route, "PASSTHROUGH_STOCK_FX3")
            self.assertEqual(res.return_code, 0)
            self.assertTrue(res.secvlt_bound)
            self.assertTrue(res.pt_load_64k_ok)

    def test_10_core_named_recording_passthrough_exports_verified(self) -> None:
        expected_core = (
            "_ZN3mpr12ExecEncStartEPv",
            "_ZN3mpr16SetEncStartParamERNS_14execEncStart_tEP17AvbbcApi_EncStart",
            "_ZN3mpr19EnqueueExecEncStartERNS_12MovieRecInfoEhRNS_15RecSequenceInfoE",
            "_ZN3mpr18EnqueueExecEncStopERNS_12MovieRecInfoEPjjb",
            "_ZN3mpr10DmmMemInfo11GetUnitInfoEPvPjS2_S2_PmS2_",
            "_ZN3mpr17ExecAudioEncStartEPNS_10DmmMemInfo11BufferTableEP12PayloadCodec",
            "_ZN3mpr16ExecAudioEncStopEP12PayloadCodec",
        )
        for sym in expected_core:
            self.assertIn(sym, p145.ALL_74_PASSTHROUGH_SYMBOLS)
            res = p145.simulate_libmpr_preload_call(sym)
            self.assertEqual(res.route, "PASSTHROUGH_STOCK_FX3")
            self.assertEqual(res.errno_equiv, "OK")

    def test_11_all_15_fx6_shim_symbols_intercepted_safely(self) -> None:
        self.assertEqual(len(p145.FX6_SHIM_REQUIRED_MPR_SYMBOLS), 15)
        for sym in p145.FX6_SHIM_REQUIRED_MPR_SYMBOLS:
            res = p145.simulate_libmpr_preload_call(sym)
            self.assertTrue(res.valid, msg=res)
            self.assertEqual(res.route, "LD_PRELOAD_SHIM_STUB")
            self.assertEqual(res.return_code, 0)
            self.assertIn(res.errno_equiv, ("OK_ZERO", "ENOENT_SAFE"))

    def test_12_libsecvlt_9_exports_and_fx3_dt_needed_preserved(self) -> None:
        audit = p145.inspect_phase145_donors(force_clean_room=True)
        self.assertEqual(len(audit.secvlt_exports_verified), 9)
        self.assertEqual(audit.secvlt_exports_verified, p145.SECVLT_EXPECTED_EXPORTS)
        self.assertTrue(audit.fx3_libmpr.has_libsecvlt_dep)

    def test_13_mpr_state_struct_size_drift_fx3_vs_fx6_detected_and_blocked(self) -> None:
        self.assertEqual(p145.MPR_STATE_STRUCT_SIZES_FX3["_ZN3mpr16g_videoParamCombE"], 312)
        self.assertEqual(p145.MPR_STATE_STRUCT_SIZES_FX6["_ZN3mpr16g_videoParamCombE"], 480)
        self.assertEqual(p145.MPR_STATE_STRUCT_SIZES_FX3["_ZN3mpr14s_movieRecInfoE"], 3144)
        self.assertEqual(p145.MPR_STATE_STRUCT_SIZES_FX6["_ZN3mpr14s_movieRecInfoE"], 5248)
        blocked = p145.simulate_libmpr_preload_call(
            "_ZN3mpr12ExecEncStartEPv", direct_struct_deref=True
        )
        self.assertFalse(blocked.valid)
        self.assertEqual(blocked.route, "BLOCKED")
        self.assertEqual(blocked.status, "BLOCKED_DIRECT_MPR_STRUCT_DEREF_312B_VS_480B")
        self.assertFalse(blocked.struct_isolation_enforced)

    def test_14_ld225_pt_load_64k_aligned_passes_and_4k_rejected(self) -> None:
        ok, code_ok = p145.evaluate_ld_preload_pt_load_compatibility(p_align=0x10000)
        self.assertTrue(ok)
        self.assertEqual(code_ok, "PT_LOAD_64K_ALIGNED_OK")

        bad, code_bad = p145.evaluate_ld_preload_pt_load_compatibility(p_align=0x1000)
        self.assertFalse(bad)
        self.assertEqual(code_bad, "ELF_LOAD_COMMAND_ALIGNMENT_NOT_PAGE_ALIGNED")

        call_bad = p145.simulate_libmpr_preload_call(
            "_ZN3mpr12RecClipCloseERKNS_19recClipCloseInParamE",
            shim_pt_load_align=0x1000,
        )
        self.assertFalse(call_bad.valid)
        self.assertFalse(call_bad.pt_load_64k_ok)
        self.assertEqual(call_bad.errno_equiv, "ELIBBAD")

    def test_15_ld225_pt_load_vaddr_offset_mismatch_rejected(self) -> None:
        ok, code = p145.evaluate_ld_preload_pt_load_compatibility(
            p_align=0x10000, p_vaddr=0x21234, p_offset=0x10000
        )
        self.assertFalse(ok)
        self.assertEqual(code, "ELF_LOAD_COMMAND_ADDRESS_OFFSET_NOT_ALIGNED")

    def test_16_secvlt_binding_broken_and_unknown_mpr_symbol_blocked(self) -> None:
        unbound = p145.simulate_libmpr_preload_call("_ZN3mpr12ExecEncStartEPv", secvlt_bound=False)
        self.assertFalse(unbound.valid)
        self.assertEqual(unbound.status, "BLOCKED_LIBSECVLT_BINDING_BROKEN")

        unknown = p145.simulate_libmpr_preload_call("_ZN3mpr9NonExistEv")
        self.assertFalse(unknown.valid)
        self.assertEqual(unknown.status, "BLOCKED_UNKNOWN_MPR_SYMBOL")
        self.assertEqual(unknown.errno_equiv, "ENOSYS")

    def test_17_pillar_a_full_evaluation_passes(self) -> None:
        rep = _get_clean_room_audit()
        pa = rep["pillar_a_ld_preload_libmpr_secvlt_shim"]
        self.assertTrue(pa["passed"])
        self.assertEqual(pa["passthrough_verified_count"], 74)
        self.assertEqual(pa["shim_intercepted_count"], 15)
        self.assertTrue(pa["libsecvlt_binding_preserved"])
        self.assertEqual(pa["libsecvlt_export_count"], 9)
        self.assertTrue(pa["ld225_pt_load_64k_verified"])


class TestPhase145PillarBDmmPoolBudgetVerifier(unittest.TestCase):
    """Pillar B — Stock FX3 DmmCfg.bin Pool Budget & Leak Verifier."""

    def test_18_target_20_shared_main_dmm_unit_ids_and_counts(self) -> None:
        self.assertEqual(len(p145.TARGET_MAIN_DMM_UNIT_IDS), 20)
        self.assertEqual(len(set(p145.TARGET_MAIN_DMM_UNIT_IDS)), 20)
        self.assertIn(528413, p145.TARGET_MAIN_DMM_UNIT_IDS)
        self.assertIn(700, p145.TARGET_MAIN_DMM_UNIT_IDS)

    def test_19_all_4_xavc_10bit_422_mlut_profiles_within_20_units_and_512mib(self) -> None:
        self.assertEqual(len(p145.DMM_RECORDING_PROFILES), 4)
        for pid in p145.DMM_RECORDING_PROFILES:
            res = p145.simulate_dmm_pool_recording_cycle(pid, mlut_preview_active=True)
            self.assertTrue(res.valid, msg=res)
            self.assertEqual(res.bit_depth, 10)
            self.assertEqual(res.chroma, "4:2:2")
            self.assertLessEqual(res.units_allocated_peak, 20)
            self.assertLessEqual(res.pool_allocated_peak_mib, 512.0)

    def test_20_every_profile_zero_leak_and_m_user_count_zero_after_stop(self) -> None:
        for pid in p145.DMM_RECORDING_PROFILES:
            res = p145.simulate_dmm_pool_recording_cycle(pid, mlut_preview_active=True)
            self.assertEqual(res.dmm_allocated_after_stop, 0)
            self.assertEqual(res.m_user_count_after_stop, 0)
            self.assertLessEqual(res.max_unit_extents_observed, p145.DMM_MAX_EXTENTS_IN_MPR_REPLY)

    def test_21_mlut_preview_toggle_changes_peak_mib_by_12mib(self) -> None:
        with_mlut = p145.simulate_dmm_pool_recording_cycle("4K_60P_XAVC_I", mlut_preview_active=True)
        no_mlut = p145.simulate_dmm_pool_recording_cycle("4K_60P_XAVC_I", mlut_preview_active=False)
        self.assertAlmostEqual(with_mlut.pool_allocated_peak_mib - no_mlut.pool_allocated_peak_mib, 12.0)

    def test_22_unmasked_sdi_raw_pool_request_rejected_before_overflow(self) -> None:
        rej = p145.simulate_dmm_pool_recording_cycle(
            "4K_60P_XAVC_I", unmasked_fx6_pool_request="SDI_RAW_POOL"
        )
        self.assertFalse(rej.valid)
        self.assertTrue(rej.unmasked_fx6_pool_rejected)
        self.assertEqual(rej.units_allocated_peak, 0)
        self.assertEqual(rej.dmm_allocated_after_stop, 0)
        self.assertEqual(rej.m_user_count_after_stop, 0)

    def test_23_unmasked_darwin_nd_pool_request_rejected_before_overflow(self) -> None:
        rej = p145.simulate_dmm_pool_recording_cycle(
            "4K_24P_XAVC_I", unmasked_fx6_pool_request="DARWIN_ND_POOL"
        )
        self.assertFalse(rej.valid)
        self.assertTrue(rej.unmasked_fx6_pool_rejected)
        self.assertEqual(rej.status, "BLOCKED_UNMASKED_FX6_DMM_POOL_REQUEST_DARWIN_ND_POOL")

    def test_24_unsupported_dmm_profile_raises_error(self) -> None:
        with self.assertRaises(p145.RealHwMprDmmCoEmulatorError):
            p145.simulate_dmm_pool_recording_cycle("8K_RAW_INVALID")

    def test_25_pillar_b_full_evaluation_passes(self) -> None:
        rep = _get_clean_room_audit()
        pb = rep["pillar_b_stock_fx3_dmmcfg_pool_budget"]
        self.assertTrue(pb["passed"])
        self.assertEqual(pb["shared_main_dmm_units"], 20)
        self.assertEqual(pb["expected_fx3_ap_dmmcfg_bytes"], 66_796)
        self.assertEqual(pb["expected_fx3_cp_dmmcfg_bytes"], 43_320)


class TestPhase145PillarCRecParameterControlM4Root(unittest.TestCase):
    """Pillar C — Physical REC -> 6 ParameterControl -> Slot-A/B M4ROOT/CLIP Lifecycle."""

    def test_26_six_shooting_domains_exact_contract(self) -> None:
        self.assertEqual(len(p145.SHOOTING_DOMAINS), 6)
        self.assertEqual(
            p145.SHOOTING_DOMAINS,
            (
                "BASE_ISO",
                "FRAME_RATE_SQ",
                "EXPOSURE_SHUTTER_ANGLE",
                "WHITE_BALANCE",
                "COLOR_LOOK_MLUT",
                "REC_START_STOP_MEDIA",
            ),
        )

    def test_27_simul_iso800_slot_a_cfexpress_and_slot_b_sdxc_m4root_clip_and_xml(self) -> None:
        res = p145.simulate_rec_button_lifecycle(
            recording_mode="SIMUL",
            profile_id="4K_60P_XAVC_I",
            base_iso=800,
            ei_index=800,
            mlut_cube_name="SLog3_Cine_Rec709.cube",
        )
        self.assertTrue(res.valid, msg=res)
        self.assertEqual(res.parameter_control_domains_verified, 6)
        self.assertIn("M4ROOT/CLIP/", res.slot_a_clip_path)
        self.assertTrue(res.slot_a_clip_path.endswith(".MP4"))
        self.assertTrue(res.slot_a_xml_path.endswith(".XML"))
        self.assertIn("M4ROOT/CLIP/", res.slot_b_clip_path)
        self.assertTrue(res.slot_b_clip_path.endswith(".MP4"))
        self.assertTrue(res.slot_b_xml_path.endswith(".XML"))
        self.assertTrue(res.nrt_xml_contains_cine_ei)
        self.assertTrue(res.nrt_xml_contains_user_lut_tag)

    def test_28_relay_iso12800_ei6400_slot_a_only_and_nrt_xml_cine_ei_lut(self) -> None:
        res = p145.simulate_rec_button_lifecycle(
            recording_mode="RELAY",
            profile_id="4K_120P_XAVC_S",
            base_iso=12800,
            ei_index=6400,
            mlut_cube_name="FX3_User_Phantom.cube",
        )
        self.assertTrue(res.valid, msg=res)
        self.assertEqual(res.slot_b_clip_path, "")
        self.assertEqual(res.slot_b_xml_path, "")
        self.assertTrue(res.nrt_xml_contains_cine_ei)
        self.assertTrue(res.nrt_xml_contains_user_lut_tag)

    def test_29_rec_stop_balances_s_record_counter_and_uipc_lock_depth_zero(self) -> None:
        for mode in ("SIMUL", "RELAY"):
            res = p145.simulate_rec_button_lifecycle(recording_mode=mode)
            self.assertEqual(res.initial_state, "Standby")
            self.assertEqual(res.final_state, "Standby")
            self.assertEqual(res.s_record_counter_after_close, 0)
            self.assertEqual(res.uipc_lock_depth, 0)
            self.assertEqual(res.dmm_allocated_after_stop, 0)
            self.assertEqual(res.m_user_count, 0)
            self.assertEqual(res.rsv_orphan_count, 0)
            self.assertEqual(res.emmc_nflasha_write_count, 0)

    def test_30_rec_lifecycle_invalid_mode_iso_profile_or_non_cube_lut_raises(self) -> None:
        with self.assertRaises(p145.RealHwMprDmmCoEmulatorError):
            p145.simulate_rec_button_lifecycle(recording_mode="INVALID_MODE")
        with self.assertRaises(p145.RealHwMprDmmCoEmulatorError):
            p145.simulate_rec_button_lifecycle(base_iso=1600)
        with self.assertRaises(p145.RealHwMprDmmCoEmulatorError):
            p145.simulate_rec_button_lifecycle(profile_id="UNKNOWN")
        with self.assertRaises(p145.RealHwMprDmmCoEmulatorError):
            p145.simulate_rec_button_lifecycle(mlut_cube_name="bad_lut.txt")

    def test_31_build_nrt_clip_xml_contains_slog3_cine_ei_and_cube_tag(self) -> None:
        xml = p145.build_nrt_clip_xml(
            clip_id="A001C001_TEST",
            recording_mode="SIMUL",
            codec="XAVC-I",
            fps=59.94,
            base_iso=800,
            ei_index=400,
            shutter_angle_deg=180.0,
            kelvin=5600,
            tint=0,
            mlut_cube_name="TestLook.cube",
        )
        self.assertIn('gamma="S-Log3.Cine"', xml)
        self.assertIn('baseISO="800" exposureIndex="400"', xml)
        self.assertIn('<User3DLUT format=".cube">TestLook.cube</User3DLUT>', xml)

    def test_32_pillar_c_full_evaluation_passes(self) -> None:
        rep = _get_clean_room_audit()
        pc = rep["pillar_c_rec_parameter_control_m4root"]
        self.assertTrue(pc["passed"])
        self.assertTrue(pc["simul_4k60_xavc_i_iso800"]["valid"])
        self.assertTrue(pc["relay_4k120_xavc_s_iso12800"]["valid"])


class TestPhase145PillarDFaultResilienceAndRedlines(unittest.TestCase):
    """Pillar D — Fault-Injection Resilience & Hard-Locked Zero eMMC Redlines."""

    def test_33_card_full_stop_graceful_encwfistop_zero_leak_zero_rsv(self) -> None:
        res = p145.simulate_fault_injection_scenario("CARD_FULL_STOP")
        self.assertTrue(res.valid)
        self.assertEqual(res.status, "VERIFIED_CARD_FULL_GRACEFUL_ENCWFISTOP")
        self.assertTrue(res.enc_wfi_stop_executed)
        self.assertTrue(res.clip_finalized)
        self.assertEqual(res.rsv_orphan_count, 0)
        self.assertEqual(res.appfw_crashes, 0)
        self.assertEqual(res.dmm_allocated_after_stop, 0)
        self.assertEqual(res.emmc_nflasha_write_count, 0)

    def test_34_slot_a_hot_pull_relay_failover_to_slot_b_seamless(self) -> None:
        res = p145.simulate_fault_injection_scenario("SLOT_A_HOT_PULL_RELAY_FAILOVER")
        self.assertTrue(res.valid)
        self.assertEqual(res.active_slot_before, "SLOT_A")
        self.assertEqual(res.active_slot_after, "SLOT_B")
        self.assertEqual(res.rsv_orphan_count, 0)
        self.assertEqual(res.appfw_crashes, 0)
        self.assertEqual(res.uipc_lock_depth, 0)

    def test_35_low_battery_graceful_encwfistop_and_standby_recovery(self) -> None:
        res = p145.simulate_fault_injection_scenario("LOW_BATTERY_ENCWFISTOP")
        self.assertTrue(res.valid)
        self.assertEqual(res.active_slot_after, "SAFE_SHUTDOWN_STANDBY")
        self.assertTrue(res.enc_wfi_stop_executed)
        self.assertTrue(res.clip_finalized)
        self.assertEqual(res.m_user_count, 0)
        self.assertFalse(res.persistent_emmc_writes_authorized)

    def test_36_forced_emmc_write_attempt_blocked_and_zero_writes(self) -> None:
        blocked = p145.simulate_fault_injection_scenario(
            "CARD_FULL_STOP", force_emmc_write_attempt=True
        )
        self.assertFalse(blocked.valid)
        self.assertEqual(blocked.status, "BLOCKED_PERSISTENT_EMMC_WRITE_ATTEMPT")
        self.assertEqual(blocked.emmc_nflasha_write_count, 0)
        self.assertFalse(blocked.persistent_emmc_writes_authorized)

    def test_37_unsupported_fault_scenario_raises_error(self) -> None:
        with self.assertRaises(p145.RealHwMprDmmCoEmulatorError):
            p145.simulate_fault_injection_scenario("UNKNOWN_FAULT")

    def test_38_pillar_d_full_evaluation_passes(self) -> None:
        rep = _get_clean_room_audit()
        pd = rep["pillar_d_fault_injection_resilience"]
        self.assertTrue(pd["passed"])
        self.assertFalse(pd["blocked_emmc_write_attempt"]["valid"])
        self.assertEqual(pd["blocked_emmc_write_attempt"]["emmc_nflasha_write_count"], 0)


class TestPhase145SuiteCliBudgetAndHygiene(unittest.TestCase):
    """Stage 25 Suite Integration, CLI, Runtime Budget (<0.8s/<2.0s), and Hygiene."""

    def test_39_cli_main_summary_and_json_clean_room_in_process(self) -> None:
        buf_sum = io.StringIO()
        with contextlib.redirect_stdout(buf_sum):
            rc_sum = p145.main(["--clean-room", "--self-test", "--summary"])
        self.assertEqual(rc_sum, 0)
        out_sum = buf_sum.getvalue()
        self.assertIn("[PASS] Phase 145 Stage 25 Real-HW MPR/DMM/REC", out_sum)
        self.assertIn("pass=74 shim=15 dmm_units=20", out_sum)
        self.assertIn("emmc_wr=0", out_sum)

        buf_json = io.StringIO()
        with contextlib.redirect_stdout(buf_json):
            rc_json = p145.main(["--clean-room", "--json"])
        self.assertEqual(rc_json, 0)
        parsed = json.loads(buf_json.getvalue())
        self.assertTrue(parsed["all_checks_passed"])
        self.assertFalse(parsed["redlines"]["persistent_emmc_writes_authorized"])
        self.assertEqual(parsed["redlines"]["emmc_nflasha_write_count"], 0)

    def test_40_suite_in_process_ge_25_stages_and_skip_phase145_config(self) -> None:
        cfg_on = suite.CoEmulationConfig(force_clean_room=True)
        rep_on = suite.run_fx3_vm_coemulation_suite(cfg_on)
        self.assertTrue(rep_on["all_checks_passed"])
        self.assertIn("stage25_realhw_mpr_dmm_rec", rep_on)
        self.assertTrue(rep_on["stage25_realhw_mpr_dmm_rec"]["all_checks_passed"])
        self.assertFalse(
            rep_on["stage25_realhw_mpr_dmm_rec"]["persistent_emmc_writes_authorized"]
        )

        stage_keys = [k for k in rep_on if re.match(r"^stage\d+_", k)]
        self.assertGreaterEqual(len(stage_keys), 25)

        cfg_skip = suite.CoEmulationConfig(
            force_clean_room=True,
            include_phase145_realhw_mpr_dmm_rec=False,
        )
        rep_skip = suite.run_fx3_vm_coemulation_suite(cfg_skip)
        self.assertTrue(rep_skip["all_checks_passed"])
        self.assertNotIn("stage25_realhw_mpr_dmm_rec", rep_skip)
        self.assertEqual(
            len([k for k in rep_skip if re.match(r"^stage\d+_", k)]),
            len(stage_keys) - 1,
        )

    def test_41_suite_subprocess_summary_and_skip_phase145_flag(self) -> None:
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
        self.assertIn("realhw_mpr_dmm_rec=CLEAN_ROOM_SYNTHETIC", proc.stdout)

        proc_skip = subprocess.run(
            [
                "/usr/bin/python3",
                "-B",
                str(FX3_VM_DIR / "fx3_vm_coemulation_suite.py"),
                "--clean-room",
                "--skip-phase145",
                "--summary",
            ],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc_skip.returncode, 0, msg=proc_skip.stderr)
        self.assertNotIn("realhw_mpr_dmm_rec=", proc_skip.stdout)

    def test_42_suite_ge_25_stages_clean_room_lt_0p8s_and_local_lt_2p0s_and_json_cli(self) -> None:
        t0 = time.monotonic()
        rep_clean = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig(force_clean_room=True))
        dt_clean = time.monotonic() - t0
        self.assertTrue(rep_clean["all_checks_passed"])
        self.assertGreaterEqual(len([k for k in rep_clean if re.match(r"^stage\d+_", k)]), 25)
        self.assertLess(dt_clean, 0.80)

        t1 = time.monotonic()
        rep_mode = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig())
        dt_mode = time.monotonic() - t1
        self.assertTrue(rep_mode["all_checks_passed"])
        self.assertGreaterEqual(len([k for k in rep_mode if re.match(r"^stage\d+_", k)]), 25)
        self.assertLess(dt_mode, 2.00)

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
        self.assertGreaterEqual(len([k for k in d_clean if re.match(r"^stage\d+_", k)]), 25)

    def test_43_all_25_stages_present_and_passing_in_suite_report(self) -> None:
        rep = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig(force_clean_room=True))
        self.assertTrue(rep["stage1_coldboot_and_bt"]["all_checks_passed"])
        self.assertTrue(rep["stage2_dual_isa_cp_shooting"]["all_checks_passed"])
        self.assertTrue(rep["stage3_soft_gpe_hud_ramfb"]["all_checks_passed"])
        for idx in range(4, 26):
            matches = [k for k in rep if k.startswith(f"stage{idx}_")]
            self.assertEqual(len(matches), 1, msg=f"Missing or duplicate stage{idx}_* key")
            self.assertTrue(rep[matches[0]]["all_checks_passed"])

    def test_44_stage25_no_raw_bytes_repr_or_nan_in_json(self) -> None:
        rep = _get_clean_room_audit()
        rendered = json.dumps(rep, allow_nan=False)
        self.assertNotRegex(rendered, r'(?<![0-9A-Za-z_/.-])b[\'"]')
        self.assertIsNone(re.search(r"NaN|Infinity", rendered))

        rep_suite = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig(force_clean_room=True))
        rendered_suite = json.dumps(rep_suite, allow_nan=False)
        self.assertNotRegex(rendered_suite, r'(?<![0-9A-Za-z_/.-])b[\'"]')
        self.assertIsNone(re.search(r"NaN|Infinity", rendered_suite))

    def test_45_source_hygiene_o_rdonly_and_no_write_flags_or_forbidden_port(self) -> None:
        src = (FX3_VM_DIR / "realhw_mpr_dmm_recording_coemulator.py").read_text(encoding="utf-8")
        self.assertIn("os.O_RDONLY", src)
        self.assertNotIn("os.O_WRONLY", src)
        self.assertNotIn("os.O_RDWR", src)
        self.assertNotIn("87" + "68", src)
        self.assertIn("sys.dont_write_bytecode = True", src)

    def test_46_audit_digest_sha256_deterministic_across_repeated_runs(self) -> None:
        r1 = p145.run_phase145_realhw_mpr_dmm_rec_coemulator(force_clean_room=True)
        r2 = p145.run_phase145_realhw_mpr_dmm_rec_coemulator(force_clean_room=True)
        self.assertEqual(len(r1["audit_digest_sha256"]), 64)
        self.assertEqual(r1["audit_digest_sha256"], r2["audit_digest_sha256"])


if __name__ == "__main__":
    unittest.main()
