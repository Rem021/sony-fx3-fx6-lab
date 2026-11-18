"""Phase 324 dual-mode unit tests for Grand Milestone Phase 324 6-Pillar Real-Hardware Master Gate."""

from __future__ import annotations

import copy
from dataclasses import replace
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

sys.dont_write_bytecode = True

REPO_ROOT = Path(__file__).resolve().parents[3]
for _rel in (
    "outputs/fx3-safety",
    "outputs/fx3-recovery-adapter",
    "outputs/fx3-firmware-lab",
    "outputs/fx3-vm",
    "outputs/fx6-on-fx3-closure",
    "outputs/fx6-on-fx3-closure/tests",
):
    _cand = str(REPO_ROOT / _rel)
    if _cand not in sys.path:
        sys.path.insert(0, _cand)

import fx6_closure  # noqa: E402
from fx6_closure.__main__ import main as fx6_cli_main  # noqa: E402
from fx6_closure.hardware_readiness_packet import _is_forced_clean_room  # noqa: E402
from fx6_closure.patcher import DEFAULT_FX3_MODULES_DIR, DEFAULT_FX6_DONOR_LIB_DIR  # noqa: E402
from fx6_closure.realhw_bench_cable_fan_and_slot1_verifier import (  # noqa: E402
    GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT,
    GO_NO_GO_DRY_RUN_SIMULATED_READY,
)
from fx6_closure.realhw_milestone311_master_gate import (  # noqa: E402
    RealHwMilestone311FaultInjection,
    _worker_phase302_307,
)
from fx6_closure.realhw_milestone324_master_gate import (  # noqa: E402
    CALIBRATION_MUTATION_BYTES,
    CNFLASHA_USERSPACE_WRITE_BLOCKED,
    CP_MUTATION_BYTES,
    CROSS_MODEL_FLASH_AUTHORIZED,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    EMMC_WRITE_COUNT,
    E_ND_ACTUATOR_TX_COUNT,
    FIRMWARE_LAB_45_AUDITOR_KEYS,
    HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    ISP_WRITE_AUTHORIZED,
    MILESTONE324_SCHEMA_VERSION,
    OTP_FUSE_TOUCHES,
    OTP_FUSE_WRITES,
    OVERALL_READY_FOR_HARDWARE_ATTACH,
    P8_CP_MUTATION_FORBIDDEN,
    P324_BASELINE_PNG_MAX_OBSERVED_BYTES,
    P324_PHYSICAL_DEVICE_WRITES,
    P324_PILLAR_IDS,
    P324_PILLAR_SPECS,
    P324_PNG_MAX_SIZE_BYTES,
    P324_RAW_FIRMWARE_BYTES_LEAKED,
    P324_SCHEMA,
    P324_STATUS_FAIL_CLOSED,
    P324_STATUS_MILESTONE_READY,
    P324_VERSION,
    PASSIVE_TX_BYTES,
    PASSIVE_TX_BYTES_EMITTED,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHASE_324_VERSION,
    PHYSICAL_DEVICE_WRITES,
    PHYSICAL_USB_PACKETS_EMITTED,
    PILLAR_IDS,
    PILLAR_SPECS,
    PNG_MAGIC_BYTES,
    PNG_MAX_SIZE_50KIB_BYTES,
    PNG_MAX_SIZE_BYTES,
    RAW_FIRMWARE_BYTES_LEAKED,
    REALHW_MILESTONE324_SCHEMA,
    RECOVERY_56_PILLAR_IDS,
    ROUND28_TO_65_PNG_RECEIPTS,
    ROUND28_TO_65_SPECS,
    ROUND63_EXPECTED_SCHEMA,
    ROUND64_EXPECTED_SCHEMA,
    ROUND65_EXPECTED_SCHEMA,
    RPMB_COUNTER_INCREMENTS,
    RPMB_WRITES,
    SPI_NOR_WRITE_AUTHORIZED,
    STATUS_FAIL_CLOSED,
    STATUS_MILESTONE_READY,
    USB_OR_CAMERA_OPERATIONS,
    USB_PACKETS_TRANSMITTED,
    VM_COEMULATION_66_STAGE_KEYS,
    WBI_MUTATION_BYTES,
    WBI_P5_WRITE_AND_HIBERNATION_FORBIDDEN,
    RealHwMilestone324FaultInjection,
    RealHwMilestone324MasterGateReport,
    _collect_parallel_milestone324_results,
    _discover_highest_recovery_master,
    _discover_highest_safety_gate_evaluator,
    _evaluate_pillar_1,
    _evaluate_pillar_2,
    _evaluate_pillar_3,
    _evaluate_pillar_4,
    _evaluate_pillar_5,
    _evaluate_pillar_6,
    _fault_to_142gate_worker_dict,
    _normalize_56plus_pillar_fault_id,
    _worker_142plus_gate_single,
    _worker_phase316_321,
    _worker_recovery_56plus_pillar,
    build_realhw_milestone324_master_gate_report,
    compute_milestone324_sha256,
    evaluate_milestone324_master_gate,
    evaluate_milestone_324_master_gate,
    evaluate_realhw_milestone324_master_gate,
    render_milestone324_markdown,
    verify_milestone_324_cli,
    verify_milestone_324_master_gate,
    verify_realhw_milestone324_master_gate,
)

_RAW_BYTES_REPR_REGEX = r"(?<![0-9A-Za-z_/.-])b['\"]"


def _ci_time_budget(base_seconds: float) -> float:
    return base_seconds + (30.0 if os.environ.get("GITHUB_ACTIONS") == "true" else 15.0)


class _LazyDeepcopyBundle:
    """Slice/index-aware lazy deepcopy wrapper so per-pillar tests copy only needed elements."""

    def __init__(self, data: tuple) -> None:
        self._data = data

    def __len__(self) -> int:
        return len(self._data)

    def __iter__(self):
        for item in self._data:
            yield copy.deepcopy(item)

    def __getitem__(self, key):
        return copy.deepcopy(self._data[key])


def _fork_child_fault_fixtures_only(conn) -> None:
    from concurrent.futures import ProcessPoolExecutor
    import multiprocessing as mp

    g142_fdict = _fault_to_142gate_worker_dict(
        RealHwMilestone324FaultInjection(
            p1_ftp_ftpes_customwb_kwargs={"ftp_avf_db_recover_requested": True},
            p1_movie_af_focusmap_marker_kwargs={"requested_fx3_onbody_focus_map": True},
            p1_request_persistent_writes=True,
        )
    )
    fx6_s = str(DEFAULT_FX6_DONOR_LIB_DIR)
    fx3_s = str(DEFAULT_FX3_MODULES_DIR)
    ctx = mp.get_context("fork")
    with ProcessPoolExecutor(max_workers=4, mp_context=ctx) as pool:
        fut_g142 = pool.submit(_worker_142plus_gate_single, (str(REPO_ROOT), True, True, g142_fdict))
        fut_p56 = pool.submit(_worker_recovery_56plus_pillar, (True, "pillar_56"))
        fut_316_321_fault = pool.submit(
            _worker_phase316_321,
            (
                fx6_s,
                fx3_s,
                True,
                {"bright_mon_shotmark_big6_ssh": True},
                {"rec_media_proxy_cloud_mymenu_ftpes": True},
            ),
        )
        fut_316_321_drift = pool.submit(
            _worker_phase316_321,
            (fx6_s, fx3_s, True, {"h0_h3_drift": True}, {"h0_h3_drift": True}),
        )
        fut_302_307_fault = pool.submit(
            _worker_phase302_307,
            (fx6_s, fx3_s, True, {}, {"dial_lut_ibis_rf_slot1": True}),
        )
        bad_g142 = fut_g142.result()
        bad_p56 = fut_p56.result()
        p316_321_bad = fut_316_321_fault.result()
        p316_321_drift = fut_316_321_drift.result()
        p302_307_bad = fut_302_307_fault.result()
    conn.send((bad_g142, bad_p56, p316_321_bad, p316_321_drift, p302_307_bad))
    conn.close()


class TestRealHwMilestone324MasterGate(unittest.TestCase):
    """Comprehensive 84 dual-mode unit tests for Grand Milestone Phase 324."""

    raw_bundle: tuple
    rep_default: RealHwMilestone324MasterGateReport
    rep_clean: RealHwMilestone324MasterGateReport
    bad_sim_g142: dict
    bad_rec_56: dict
    p316_321_bad: tuple
    p316_321_drift: tuple
    p302_307_bad: tuple
    default_elapsed_s: float

    @classmethod
    def setUpClass(cls) -> None:
        import multiprocessing as mp

        t0 = time.monotonic()
        ctx = mp.get_context("fork")
        if not _is_forced_clean_room():
            cls.rep_default = evaluate_milestone_324_master_gate()
        recv_conn, send_conn = ctx.Pipe(duplex=False)
        proc = ctx.Process(
            target=_fork_child_fault_fixtures_only,
            args=(send_conn,),
            daemon=False,
        )
        proc.start()
        send_conn.close()
        try:
            cls.raw_bundle = _collect_parallel_milestone324_results(
                repo_root=REPO_ROOT,
                fx6_lib_dir=DEFAULT_FX6_DONOR_LIB_DIR,
                fx3_modules_dir=DEFAULT_FX3_MODULES_DIR,
                use_clean_room=True,
                faults=RealHwMilestone324FaultInjection(),
            )
            (
                cls.bad_sim_g142,
                cls.bad_rec_56,
                cls.p316_321_bad,
                cls.p316_321_drift,
                cls.p302_307_bad,
            ) = recv_conn.recv()
        finally:
            recv_conn.close()
            proc.join(timeout=60)
        cls.rep_clean = evaluate_milestone_324_master_gate(
            force_clean_room=True,
            _raw_bundle_override=cls.raw_bundle,
        )
        if _is_forced_clean_room():
            cls.rep_default = cls.rep_clean
        cls.default_elapsed_s = time.monotonic() - t0

    def _unpack_clean_raw(self):
        return _LazyDeepcopyBundle(self.raw_bundle)

    # --- 1. Constants, Package Exports & Dynamic Discovery ---

    def test_01_schema_and_version_constants(self) -> None:
        self.assertEqual(REALHW_MILESTONE324_SCHEMA, "realhw_milestone324_master_gate_v1")
        self.assertEqual(MILESTONE324_SCHEMA_VERSION, REALHW_MILESTONE324_SCHEMA)
        self.assertEqual(P324_SCHEMA, REALHW_MILESTONE324_SCHEMA)
        self.assertEqual(PHASE_324_VERSION, "324.0.0")
        self.assertEqual(P324_VERSION, "324.0.0")
        self.assertEqual(PILLAR_IDS, ("P1", "P2", "P3", "P4", "P5", "P6"))
        self.assertEqual(P324_PILLAR_IDS, PILLAR_IDS)
        self.assertEqual(len(PILLAR_SPECS), 6)
        self.assertEqual(P324_PILLAR_SPECS, PILLAR_SPECS)
        self.assertGreaterEqual(len(RECOVERY_56_PILLAR_IDS), 56)
        self.assertGreaterEqual(len(FIRMWARE_LAB_45_AUDITOR_KEYS), 45)
        self.assertGreaterEqual(len(VM_COEMULATION_66_STAGE_KEYS), 66)
        self.assertGreaterEqual(len(ROUND28_TO_65_SPECS), 38)
        self.assertEqual(PNG_MAX_SIZE_50KIB_BYTES, 51200)
        self.assertEqual(PNG_MAX_SIZE_BYTES, 51200)
        self.assertEqual(P324_PNG_MAX_SIZE_BYTES, 51200)
        self.assertEqual(P324_BASELINE_PNG_MAX_OBSERVED_BYTES, 27467)

    def test_02_hard_locked_zero_write_and_attach_constants(self) -> None:
        self.assertFalse(OVERALL_READY_FOR_HARDWARE_ATTACH)
        self.assertFalse(HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        self.assertFalse(CROSS_MODEL_FLASH_AUTHORIZED)
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(PERSISTENT_WRITE_RELEASE)
        self.assertFalse(SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        self.assertFalse(ISP_WRITE_AUTHORIZED)
        self.assertTrue(CNFLASHA_USERSPACE_WRITE_BLOCKED)
        self.assertTrue(P8_CP_MUTATION_FORBIDDEN)
        self.assertTrue(WBI_P5_WRITE_AND_HIBERNATION_FORBIDDEN)
        self.assertEqual(P324_STATUS_MILESTONE_READY, STATUS_MILESTONE_READY)
        self.assertEqual(P324_STATUS_FAIL_CLOSED, STATUS_FAIL_CLOSED)
        for zero_const in (
            USB_PACKETS_TRANSMITTED,
            PHYSICAL_USB_PACKETS_EMITTED,
            PHYSICAL_DEVICE_WRITES,
            P324_PHYSICAL_DEVICE_WRITES,
            RAW_FIRMWARE_BYTES_LEAKED,
            P324_RAW_FIRMWARE_BYTES_LEAKED,
            E_ND_ACTUATOR_TX_COUNT,
            EMMC_WRITE_COUNT,
            CP_MUTATION_BYTES,
            WBI_MUTATION_BYTES,
            CALIBRATION_MUTATION_BYTES,
            USB_OR_CAMERA_OPERATIONS,
            OTP_FUSE_WRITES,
            OTP_FUSE_TOUCHES,
            RPMB_WRITES,
            RPMB_COUNTER_INCREMENTS,
            PASSIVE_TX_BYTES,
            PASSIVE_TX_BYTES_EMITTED,
        ):
            self.assertEqual(zero_const, 0)

    def test_03_public_package_exports_present_and_unshadowed(self) -> None:
        expected = {
            "P324_CROSS_MODEL_FLASH_AUTHORIZED",
            "MILESTONE324_PHYSICAL_DEVICE_WRITES",
            "MILESTONE324_PILLAR_IDS",
            "MILESTONE324_PILLAR_SPECS",
            "MILESTONE324_PNG_MAX_SIZE_BYTES",
            "MILESTONE324_RAW_FIRMWARE_BYTES_LEAKED",
            "MILESTONE324_SCHEMA_VERSION",
            "P324_BASELINE_PNG_MAX_OBSERVED_BYTES",
            "P324_PHYSICAL_DEVICE_WRITES",
            "P324_PILLAR_IDS",
            "P324_PILLAR_SPECS",
            "P324_PNG_MAX_SIZE_BYTES",
            "P324_RAW_FIRMWARE_BYTES_LEAKED",
            "P324_SCHEMA",
            "P324_STATUS_FAIL_CLOSED",
            "P324_STATUS_MILESTONE_READY",
            "P324_VERSION",
            "PHASE_324_VERSION",
            "REALHW_MILESTONE324_SCHEMA",
            "RECOVERY_56_PILLAR_IDS",
            "ROUND28_TO_65_PNG_RECEIPTS",
            "ROUND28_TO_65_SPECS",
            "ROUND63_EXPECTED_SCHEMA",
            "ROUND64_EXPECTED_SCHEMA",
            "ROUND65_EXPECTED_SCHEMA",
            "STATUS_MILESTONE324_FAIL_CLOSED",
            "STATUS_MILESTONE324_READY",
            "VM_COEMULATION_66_STAGE_KEYS",
            "Milestone324PillarResult",
            "RealHwMilestone324FaultInjection",
            "RealHwMilestone324MasterGateReport",
            "RealHwMilestone324VerifyResult",
            "build_realhw_milestone324_master_gate_report",
            "compute_milestone324_sha256",
            "evaluate_milestone324_master_gate",
            "evaluate_milestone_324_master_gate",
            "evaluate_realhw_milestone324_master_gate",
            "render_milestone324_markdown",
            "verify_milestone_324_cli",
            "verify_milestone_324_master_gate",
            "verify_realhw_milestone324_master_gate",
        }
        self.assertTrue(expected.issubset(set(fx6_closure.__all__)))
        for sym in expected:
            self.assertTrue(hasattr(fx6_closure, sym), sym)
        self.assertEqual(fx6_closure.REALHW_MILESTONE311_SCHEMA, "realhw_milestone311_master_gate_v1")
        self.assertEqual(fx6_closure.REALHW_MILESTONE295_SCHEMA, "realhw_milestone295_master_gate_v1")
        self.assertEqual(fx6_closure.REALHW_MILESTONE264_SCHEMA, "realhw_milestone264_master_gate_v1")
        self.assertEqual(fx6_closure.REALHW_MILESTONE254_SCHEMA, "realhw_milestone254_master_gate_v1")
        self.assertEqual(fx6_closure.REALHW_MILESTONE233_SCHEMA, "realhw_milestone233_master_gate_v1")

    def test_04_builder_and_verifier_aliases_point_to_canonical_functions(self) -> None:
        self.assertIs(build_realhw_milestone324_master_gate_report, evaluate_realhw_milestone324_master_gate)
        self.assertIs(evaluate_milestone_324_master_gate, evaluate_realhw_milestone324_master_gate)
        self.assertIs(evaluate_milestone324_master_gate, evaluate_realhw_milestone324_master_gate)
        self.assertIs(verify_milestone_324_master_gate, verify_realhw_milestone324_master_gate)

    def test_05_rounds63_to_65_specs_and_png_pairs_registered(self) -> None:
        by_num = {s.round_num: s for s in ROUND28_TO_65_SPECS}
        self.assertGreaterEqual(len(by_num), 38)
        self.assertGreaterEqual(len(ROUND28_TO_65_PNG_RECEIPTS), 38)
        for rnum, exp_schema in (
            (63, ROUND63_EXPECTED_SCHEMA),
            (64, ROUND64_EXPECTED_SCHEMA),
            (65, ROUND65_EXPECTED_SCHEMA),
        ):
            self.assertIn(rnum, by_num)
            self.assertEqual(by_num[rnum].expected_schema, exp_schema)
            self.assertEqual(len(by_num[rnum].run_specs), 3)
            self.assertIn(rnum, ROUND28_TO_65_PNG_RECEIPTS)
            self.assertEqual(len(ROUND28_TO_65_PNG_RECEIPTS[rnum]), 2)
            for _, exp_faithful in by_num[rnum].run_specs:
                self.assertEqual(exp_faithful, 1)

    def test_06_normalize_56plus_pillar_fault_id_resolves_short_and_full_ids(self) -> None:
        self.assertIsNone(_normalize_56plus_pillar_fault_id(None))
        self.assertIsNone(_normalize_56plus_pillar_fault_id(""))
        for pnum in range(45, 57):
            full_id = RECOVERY_56_PILLAR_IDS[pnum - 1]
            self.assertEqual(_normalize_56plus_pillar_fault_id(f"pillar_{pnum}"), full_id)
            self.assertEqual(_normalize_56plus_pillar_fault_id(full_id), full_id)

    def test_07_dynamic_safety_evaluator_discovery_prefers_highest_142plus(self) -> None:
        real_n, real_fn = _discover_highest_safety_gate_evaluator()
        self.assertGreaterEqual(real_n, 142)
        self.assertTrue(callable(real_fn))

        class _FakeSafetyMod:
            @staticmethod
            def evaluate_142gate_preflight():
                return "142"

            @staticmethod
            def evaluate_144gate_preflight():
                return "144"

        best_n, best_fn = _discover_highest_safety_gate_evaluator(_FakeSafetyMod)
        self.assertEqual(best_n, 144)
        self.assertEqual(best_fn(), "144")

    def test_08_dynamic_recovery_master_discovery_prefers_highest_56plus(self) -> None:
        real_m, real_fn, real_ids = _discover_highest_recovery_master()
        self.assertGreaterEqual(real_m, 56)
        self.assertTrue(callable(real_fn))
        self.assertGreaterEqual(len(real_ids), 56)

        class _FakeRecoveryMod:
            MASTER_56_PILLAR_IDS = tuple(f"p_{i}" for i in range(1, 57))
            MASTER_57_PILLAR_IDS = tuple(f"p_{i}" for i in range(1, 58))

            @staticmethod
            def evaluate_realhw_56pillar_recovery_master():
                return 56

            @staticmethod
            def evaluate_realhw_57pillar_recovery_master():
                return 57

        best_m, best_fn, best_ids = _discover_highest_recovery_master(_FakeRecoveryMod)
        self.assertEqual(best_m, 57)
        self.assertEqual(best_fn(), 57)
        self.assertEqual(len(best_ids), 57)

    # --- 2. End-to-End Dual-Mode Reports, Determinism & Markdown ---

    def test_09_default_mode_report_all_6_pillars_ready(self) -> None:
        rep = self.rep_default
        self.assertTrue(rep.all_pillars_milestone_ready, rep.errors)
        self.assertEqual(rep.status, STATUS_MILESTONE_READY)
        self.assertEqual(rep.passed_pillar_count, 6)
        self.assertEqual(rep.failed_pillar_ids, ())
        v = verify_realhw_milestone324_master_gate(rep)
        self.assertTrue(v.valid, v.errors)

    def test_10_clean_room_mode_report_all_6_pillars_ready_and_locked(self) -> None:
        rep = self.rep_clean
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(rep.all_pillars_milestone_ready, rep.errors)
        self.assertEqual(rep.status, STATUS_MILESTONE_READY)
        self.assertTrue(rep.cnflasha_userspace_write_blocked)
        self.assertFalse(rep.cross_model_flash_authorized)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.hardware_live_attachment_authorized)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.spi_nor_write_authorized)
        self.assertFalse(rep.el3_payload_transmit_authorized)
        self.assertEqual(rep.usb_packets_transmitted, 0)
        self.assertEqual(rep.physical_device_writes, 0)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)
        self.assertEqual(rep.e_nd_actuator_tx_count, 0)
        self.assertEqual(rep.rf_packets_transmitted, 0)
        self.assertEqual(rep.slot1_data_sector_writes, 0)
        self.assertEqual(rep.otp_fuse_touches, 0)
        self.assertEqual(rep.rpmb_counter_increments, 0)
        self.assertEqual(rep.passive_tx_bytes_emitted, 0)
        self.assertEqual(rep.p316_wireless_rf_packets_emitted, 0)
        self.assertEqual(rep.p316_slot1_data_sector_writes, 0)
        self.assertEqual(rep.p321_wireless_rf_packets_emitted, 0)
        self.assertEqual(rep.p321_slot1_data_sector_writes, 0)
        self.assertTrue(verify_realhw_milestone324_master_gate(rep.to_dict()).valid)

    def test_11_fx3_clean_room_test_env_var_compatibility(self) -> None:
        with mock.patch.dict(os.environ, {"FX3_CLEAN_ROOM_TEST": "1"}, clear=False):
            rep = evaluate_milestone_324_master_gate(_raw_bundle_override=self._unpack_clean_raw())
            self.assertTrue(rep.all_pillars_milestone_ready, rep.errors)
            self.assertEqual(rep.passed_pillar_count, 6)
            self.assertTrue(verify_realhw_milestone324_master_gate(rep).valid)

    def test_12_forward_compatible_lower_bounds_on_clean_report(self) -> None:
        rep = self.rep_clean
        self.assertGreaterEqual(rep.gate142_total_gates, 142)
        self.assertGreaterEqual(rep.gate142_offline_verified, 139)
        self.assertEqual(rep.gate142_offline_verified, rep.gate142_total_gates - 3)
        self.assertGreaterEqual(rep.gate142_simulated_verified, 142)
        self.assertEqual(rep.gate142_simulated_verified, rep.gate142_total_gates)
        self.assertTrue(rep.gate142_all_verified)
        self.assertGreaterEqual(rep.recovery_pillar_count, 56)
        self.assertEqual(rep.recovery_pillars_passed, rep.recovery_pillar_count)
        self.assertGreaterEqual(rep.auditors_passed, 45)
        self.assertEqual(rep.auditors_passed, rep.auditors_total)
        self.assertGreaterEqual(rep.vm_stages_passed, 66)
        self.assertEqual(rep.vm_stages_passed, rep.vm_stages_total)
        self.assertGreaterEqual(rep.qemu_rounds_verified, 38)
        self.assertGreaterEqual(rep.qemu_runs_verified, 114)
        self.assertGreaterEqual(rep.qemu_png_receipts_verified, 76)
        self.assertLess(rep.qemu_png_max_bytes, PNG_MAX_SIZE_50KIB_BYTES)
        self.assertEqual(rep.h0_equals_h3_count, 16)
        self.assertEqual(rep.e_nd_actuator_tx_count, 0)
        self.assertEqual(rep.emmc_write_count, 0)

    def test_13_deterministic_json_and_sha256_recomputation(self) -> None:
        j1 = self.rep_clean.to_deterministic_json()
        parsed = json.loads(j1)
        self.assertEqual(compute_milestone324_sha256(parsed), self.rep_clean.milestone324_sha256)
        rep2 = evaluate_milestone_324_master_gate(
            force_clean_room=True,
            _raw_bundle_override=self._unpack_clean_raw(),
        )
        self.assertEqual(rep2.milestone324_sha256, self.rep_clean.milestone324_sha256)

    def test_14_no_raw_bytes_repr_in_serialized_reports(self) -> None:
        for rep in (self.rep_default, self.rep_clean):
            self.assertIsNone(re.search(_RAW_BYTES_REPR_REGEX, rep.to_deterministic_json()))

    def test_15_markdown_renderer_contains_bilingual_headers_and_14_preflights(self) -> None:
        md = render_milestone324_markdown(self.rep_clean)
        for token in (
            "Grand Milestone Phase 324",
            "realhw_milestone324_master_gate_v1",
            "MILESTONE_324_PREBENCH_MASTER_VERIFIED",
            "cross_model_flash_authorized = False",
            "142+-Gate Preflight",
            "56+-Pillar Recovery Master",
            "66+ Stage VM HIL",
            "Ph186=",
            "Ph302=",
            "Ph307=",
            "Ph316=",
            "Ph321=",
            "Rounds 28..65+",
            "| `P1` |",
            "| `P6` |",
        ):
            self.assertIn(token, md)

    # --- 3. Pillar 1: >= 142 Safety Gates (`evaluate_142gate_preflight`) ---

    def test_16_pillar1_142gate_happy_path_and_g63_to_g142_valid(self) -> None:
        raw_off, raw_sim = self._unpack_clean_raw()[:2]
        p1 = _evaluate_pillar_1(raw_off, raw_sim)
        self.assertTrue(p1.passed, p1.errors)
        self.assertGreaterEqual(p1.evidence["offline_verified_gates"], 139)
        self.assertGreaterEqual(p1.evidence["simulated_verified_gates"], 142)
        self.assertTrue(p1.evidence["all_142plus_gates_verified"])
        self.assertFalse(p1.evidence["cross_model_flash_authorized"])
        for idx in range(63, 143):
            self.assertTrue(p1.evidence["g63_to_gn_valid"][f"g{idx}"], f"g{idx}")

    def test_17_pillar1_forward_compatible_with_144_gates(self) -> None:
        raw_off, raw_sim = self._unpack_clean_raw()[:2]
        raw_off["total_gates"] = 144
        raw_off["verified_gates"] = 141
        raw_off["offline_minus3_verified"] = True
        raw_sim["total_gates"] = 144
        raw_sim["verified_gates"] = 144
        raw_sim["all_n_gates_verified"] = True
        raw_sim["nested_g_valid"]["g143"] = True
        raw_sim["nested_g_valid"]["g144"] = True
        p1 = _evaluate_pillar_1(raw_off, raw_sim)
        self.assertTrue(p1.passed, p1.errors)
        self.assertGreaterEqual(p1.evidence["simulated_verified_gates"], 144)

    def test_18_pillar1_fails_when_offline_tier0_gates_not_blocked(self) -> None:
        raw_off, raw_sim = self._unpack_clean_raw()[:2]
        raw_off["verified_gates"] = raw_off["total_gates"]
        raw_off["blocked_or_pending_gates"] = 0
        self.assertFalse(_evaluate_pillar_1(raw_off, raw_sim).passed)

    def test_19_pillar1_fails_when_all_n_gates_verified_false_in_dry_run(self) -> None:
        raw_off, raw_sim = self._unpack_clean_raw()[:2]
        raw_sim["all_n_gates_verified"] = False
        self.assertFalse(_evaluate_pillar_1(raw_off, raw_sim).passed)

    def test_20_pillar1_fails_when_hardware_attach_cross_model_or_write_unlocked(self) -> None:
        for field in (
            "overall_ready_for_hardware_attach",
            "hardware_live_attachment_authorized",
            "cross_model_flash_authorized",
            "persistent_emmc_writes_authorized",
            "spi_nor_write_authorized",
            "el3_payload_transmit_authorized",
        ):
            raw_off, raw_sim = self._unpack_clean_raw()[:2]
            raw_sim[field] = True
            self.assertFalse(_evaluate_pillar_1(raw_off, raw_sim).passed, field)

    def test_21_pillar1_fails_when_usb_packets_or_leak_or_end_tx_nonzero(self) -> None:
        for field in (
            "usb_packets_transmitted",
            "raw_firmware_bytes_leaked",
            "g71_e_nd_actuator_tx_count",
        ):
            raw_off, raw_sim = self._unpack_clean_raw()[:2]
            raw_sim[field] = 1
            self.assertFalse(_evaluate_pillar_1(raw_off, raw_sim).passed, field)

    def test_22_pillar1_fails_when_any_g135_to_g142_wave_gate_invalid(self) -> None:
        for gtag in ("g135", "g136", "g137", "g138", "g139", "g140", "g141", "g142"):
            raw_off, raw_sim = self._unpack_clean_raw()[:2]
            raw_sim["nested_g_valid"][gtag] = False
            p1 = _evaluate_pillar_1(raw_off, raw_sim)
            self.assertFalse(p1.passed, gtag)
            self.assertIn(gtag.upper(), p1.errors[-1])

    def test_23_pillar1_live_worker_g141_g142_and_persistent_write_fault(self) -> None:
        raw_sim_bad = copy.deepcopy(self.bad_sim_g142)
        raw_off = self._unpack_clean_raw()[0]
        p1 = _evaluate_pillar_1(raw_off, raw_sim_bad)
        self.assertFalse(p1.passed)
        self.assertFalse(raw_sim_bad["nested_g_valid"]["g141"])
        self.assertFalse(raw_sim_bad["nested_g_valid"]["g142"])

    def test_24_fault_to_142gate_worker_dict_propagates_wave58_to_61_and_m311(self) -> None:
        f = RealHwMilestone324FaultInjection(
            p1_bright_mon_shotmark_kwargs={"shot_mark_slot": 1},
            p1_ftp_ftpes_customwb_kwargs={"ftp_avf_db_recover_requested": True},
            p1_movie_af_focusmap_marker_kwargs={"requested_fx3_onbody_focus_map": True},
            m311_faults=RealHwMilestone311FaultInjection(p1_request_persistent_writes=True),
        )
        w = _fault_to_142gate_worker_dict(f)
        self.assertTrue(w["p1_request_persistent_writes"])
        self.assertEqual(w["p1_bright_mon_shotmark_kwargs"], {"shot_mark_slot": 1})
        self.assertEqual(w["p1_ftp_ftpes_customwb_kwargs"], {"ftp_avf_db_recover_requested": True})
        self.assertEqual(
            w["p1_movie_af_focusmap_marker_kwargs"],
            {"requested_fx3_onbody_focus_map": True},
        )

    # --- 4. Pillar 2: >= 56 Recovery Pillars (`evaluate_realhw_56pillar_recovery_master`) ---

    def test_25_pillar2_56pillar_happy_path_and_cnflasha_ro(self) -> None:
        rec_56 = self._unpack_clean_raw()[2]
        p2, meta2 = _evaluate_pillar_2(rec_56, RealHwMilestone324FaultInjection())
        self.assertTrue(p2.passed, p2.errors)
        self.assertGreaterEqual(meta2["recovery_pillar_count"], 56)
        self.assertEqual(meta2["recovery_pillars_passed"], meta2["recovery_pillar_count"])
        self.assertTrue(meta2["cnflasha_userspace_write_blocked"])
        self.assertFalse(p2.evidence.get("fx3_has_builtin_evf", False))
        self.assertFalse(p2.evidence.get("fx3_has_builtin_end_filter", False))
        self.assertEqual(meta2["otp_fuse_writes"], 0)
        self.assertEqual(meta2["rpmb_writes"], 0)
        self.assertEqual(meta2["passive_tx_bytes"], 0)
        self.assertEqual(meta2["physical_usb_packets_emitted"], 0)
        self.assertEqual(meta2["physical_device_writes"], 0)
        self.assertEqual(meta2["raw_firmware_bytes_leaked"], 0)

    def test_26_pillar2_forward_compatible_with_57_pillars(self) -> None:
        rec_56 = self._unpack_clean_raw()[2]
        rec_56["pillar_count"] = 57
        rec_56["pillars_passed"] = 57
        rec_56["status"] = "VERIFIED_57OF57_PILLAR_RECOVERY_MASTER"
        rec_56["pillars"] = list(rec_56["pillars"]) + [{"pillar_id": "pillar_57_future_vault", "passed": True}]
        p2, meta2 = _evaluate_pillar_2(rec_56, RealHwMilestone324FaultInjection())
        self.assertTrue(p2.passed, p2.errors)
        self.assertGreaterEqual(meta2["recovery_pillar_count"], 57)

    def test_27_pillar2_fails_when_cnflasha_userspace_write_unblocked(self) -> None:
        rec_56 = self._unpack_clean_raw()[2]
        p2, _ = _evaluate_pillar_2(
            rec_56,
            RealHwMilestone324FaultInjection(p2_cnflasha_write_unblocked_fault=True),
        )
        self.assertFalse(p2.passed)

    def test_28_pillar2_fails_on_otp_rpmb_passive_tx_usb_devwrite_or_leak_overrides(self) -> None:
        rec_56 = self._unpack_clean_raw()[2]
        for kw in (
            {"p2_otp_fuse_touches_override": 1},
            {"p2_rpmb_counter_increments_override": 1},
            {"p2_passive_tx_bytes_override": 4},
            {"p2_physical_usb_packets_override": 1},
            {"p2_physical_device_writes_override": 1},
            {"p2_raw_firmware_bytes_leaked_override": 8},
        ):
            p2, _ = _evaluate_pillar_2(rec_56, RealHwMilestone324FaultInjection(**kw))
            self.assertFalse(p2.passed, kw)

    def test_29_pillar2_fails_when_56a_or_56b_vault_subsuite_fails_safely(self) -> None:
        for sub_key in (
            "pillar56_a_switch_vh_af_focus_limit_color_vault",
            "pillar56_b_exposure_std_tcub_reverse_copy_vault",
        ):
            rec_56 = self._unpack_clean_raw()[2]
            rec_56.setdefault(sub_key, {})["passed"] = False
            self.assertFalse(
                _evaluate_pillar_2(rec_56, RealHwMilestone324FaultInjection())[0].passed,
                sub_key,
            )

    def test_30_pillar2_live_worker_fault_inject_pillar_56_fails_closed(self) -> None:
        bad_56 = copy.deepcopy(self.bad_rec_56)
        p2, _ = _evaluate_pillar_2(bad_56, RealHwMilestone324FaultInjection())
        self.assertFalse(p2.passed)

    def test_31_pillar2_fails_on_p55_to_p56_violation_counters_or_hw_flags(self) -> None:
        for vkey in (
            "dormant_shading_auto_low_exposure_events",
            "af_illuminator_gate_or_fx6_spoof_events",
            "slot1_folder_dir_mutation_bytes",
            "slot1_rating_avf_info_mutation_bytes",
            "switch_vh_af_lockout_or_coords_drift_events",
            "reverse_copy_slot2_to_slot1_bypass_events",
            "slot1_copy_avf_info_mutation_bytes",
        ):
            rec_56 = self._unpack_clean_raw()[2]
            rec_56[vkey] = 1
            self.assertFalse(
                _evaluate_pillar_2(rec_56, RealHwMilestone324FaultInjection())[0].passed,
                vkey,
            )
        for neg_flag in (
            "fx3_has_builtin_evf",
            "fx3_has_var_shutter",
            "fx3_has_builtin_end_filter",
            "fx3_exposes_shading_auto_low",
            "fx6_has_switch_vh_af_area",
            "fx6_has_builtin_af_illuminator",
            "fx6_has_exp_std_adj",
        ):
            rec_neg = self._unpack_clean_raw()[2]
            rec_neg[neg_flag] = True
            self.assertFalse(
                _evaluate_pillar_2(rec_neg, RealHwMilestone324FaultInjection())[0].passed,
                neg_flag,
            )

    # --- 5. Pillar 3: >= 45 Firmware Auditors (`outputs/fx3-firmware-lab`) ---

    def test_32_pillar3_45plus_auditors_happy_path(self) -> None:
        auditors = self._unpack_clean_raw()[3]
        p3, meta3 = _evaluate_pillar_3(auditors, RealHwMilestone324FaultInjection())
        self.assertTrue(p3.passed, p3.errors)
        self.assertGreaterEqual(meta3["auditor_count"], 45)
        self.assertEqual(meta3["passed_count"], meta3["auditor_count"])
        self.assertEqual(meta3["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(meta3["e_nd_actuator_tx_count"], 0)
        self.assertEqual(meta3["calibration_mutation_bytes"], 0)

    def test_33_pillar3_forward_compatible_with_46_plus_auditors(self) -> None:
        auditors = self._unpack_clean_raw()[3]
        auditors["realhw_future_wave62_audit"] = {"all_checks_passed": True}
        p3, meta3 = _evaluate_pillar_3(auditors, RealHwMilestone324FaultInjection())
        self.assertTrue(p3.passed, p3.errors)
        self.assertGreaterEqual(meta3["auditor_count"], 46)
        self.assertEqual(meta3["passed_count"], meta3["auditor_count"])

    def test_34_pillar3_fails_on_auditor45_guard_fault_or_subpillar_failure(self) -> None:
        auditors = self._unpack_clean_raw()[3]
        p3_fault, _ = _evaluate_pillar_3(
            auditors,
            RealHwMilestone324FaultInjection(p3_filesettings_tcregen_reclamp_guard_fault=True),
        )
        self.assertFalse(p3_fault.passed)

        auditors2 = self._unpack_clean_raw()[3]
        auditors2["realhw_filesettings_shotmark_tcregen_and_reclamp_audit"].setdefault(
            "pillar_2_tc_regenerate_slot1_and_ext_lk", {}
        )["passed"] = False
        self.assertFalse(_evaluate_pillar_3(auditors2, RealHwMilestone324FaultInjection())[0].passed)

    def test_35_pillar3_fails_on_raw_firmware_bytes_leaked_override(self) -> None:
        auditors = self._unpack_clean_raw()[3]
        p3, _ = _evaluate_pillar_3(
            auditors,
            RealHwMilestone324FaultInjection(p3_raw_firmware_bytes_leaked_override=16),
        )
        self.assertFalse(p3.passed)

    def test_36_pillar3_fails_when_forward_compat_46th_auditor_fails(self) -> None:
        auditors = self._unpack_clean_raw()[3]
        auditors["realhw_broken_future_audit"] = {"all_checks_passed": False}
        self.assertFalse(_evaluate_pillar_3(auditors, RealHwMilestone324FaultInjection())[0].passed)

    # --- 6. Pillar 4: >= 66 VM Co-Emulation Stages (`outputs/fx3-vm`) ---

    def test_37_pillar4_66plus_stages_happy_path_and_milestone_66of66(self) -> None:
        raw_vm = self._unpack_clean_raw()[4]
        p4, meta4 = _evaluate_pillar_4(raw_vm, RealHwMilestone324FaultInjection())
        self.assertTrue(p4.passed, p4.errors)
        self.assertGreaterEqual(meta4["stage_count"], 66)
        self.assertEqual(meta4["passed_count"], meta4["stage_count"])
        self.assertEqual(meta4["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(meta4["physical_device_writes"], 0)
        self.assertEqual(meta4["emmc_corruptions"], 0)
        self.assertEqual(p4.evidence["stage66_milestone"], "66/66")
        for dkey in (
            "stage63_digest_sha256",
            "stage64_digest_sha256",
            "stage65_digest_sha256",
            "stage66_digest_sha256",
        ):
            self.assertEqual(len(str(p4.evidence[dkey])), 64, dkey)

    def test_38_pillar4_forward_compatible_with_stage67_plus(self) -> None:
        raw_vm = self._unpack_clean_raw()[4]
        raw_vm["stage67_realhw_future_wave58_hil"] = {"all_checks_passed": True}
        p4, meta4 = _evaluate_pillar_4(raw_vm, RealHwMilestone324FaultInjection())
        self.assertTrue(p4.passed, p4.errors)
        self.assertGreaterEqual(meta4["stage_count"], 67)
        self.assertEqual(meta4["passed_count"], meta4["stage_count"])

    def test_39_pillar4_fails_on_stage63_through_stage66_fault_injections(self) -> None:
        raw_vm = self._unpack_clean_raw()[4]
        for kw in (
            {"p4_stage63_lens_comp_af_illum_folder_rating_faults": 1},
            {"p4_stage64_switch_vh_stdadj_tcub_copy_faults": 1},
            {"p4_stage65_touch_disp_zero_evf_interval_pb_faults": 1},
            {"p4_stage66_dial_customize_mydial_fn_lut_embed_faults": 1},
        ):
            p4, _ = _evaluate_pillar_4(raw_vm, RealHwMilestone324FaultInjection(**kw))
            self.assertFalse(p4.passed, kw)

    def test_40_pillar4_fails_on_stage59_through_stage62_cascaded_fault_injections(self) -> None:
        raw_vm = self._unpack_clean_raw()[4]
        for m311_kw in (
            {"p4_stage59_raw_heif_colorspace_shutter_nr_faults": 1},
            {"p4_stage60_focus_zoom_iso_minss_flash_faults": 1},
            {"p4_stage61_dci4k_aspect_hold_camset_photo_faults": 1},
            {"p4_stage62_sensor_cleaning_ev_focus_rotate_faults": 1},
        ):
            f = RealHwMilestone324FaultInjection(
                m311_faults=RealHwMilestone311FaultInjection(**m311_kw)
            )
            p4, _ = _evaluate_pillar_4(raw_vm, f)
            self.assertFalse(p4.passed, m311_kw)

    def test_41_pillar4_fails_on_physical_device_writes_or_raw_leak(self) -> None:
        raw_vm = self._unpack_clean_raw()[4]
        for kw in (
            {"p4_physical_device_writes_override": 1},
            {"p4_raw_firmware_bytes_leaked_override": 4},
        ):
            p4, _ = _evaluate_pillar_4(raw_vm, RealHwMilestone324FaultInjection(**kw))
            self.assertFalse(p4.passed, kw)

    def test_42_pillar4_fails_on_stage63_to_66_milestone_or_digest_tamper(self) -> None:
        raw_vm = self._unpack_clean_raw()[4]
        raw_vm["stage66_realhw_dial_customize_mydial_fn_liveview_lut_embed_hil"]["milestone"] = "65/66"
        self.assertFalse(_evaluate_pillar_4(raw_vm, RealHwMilestone324FaultInjection())[0].passed)

        raw_vm2 = self._unpack_clean_raw()[4]
        raw_vm2["stage64_realhw_switch_vh_af_stdadj_tcub_copy_slot_hil"]["phase312_audit_digest_sha256"] = "bad"
        self.assertFalse(_evaluate_pillar_4(raw_vm2, RealHwMilestone324FaultInjection())[0].passed)

    def test_43_pillar4_fails_on_stage63_to_66_redline_counters_and_emmc_mutation(self) -> None:
        for skey, bad_counter in (
            ("stage63_realhw_lens_comp_af_illuminator_folder_rating_hil", "slot1_vault_folder_or_rating_mutation_bytes"),
            ("stage64_realhw_switch_vh_af_stdadj_tcub_copy_slot_hil", "reverse_copy_slot2_to_slot1_vault_bypass_events"),
            ("stage65_realhw_touch_shooting_disp_zero_evf_interval_pb_hil", "zero_evf_finder_monitor_blackout_trap_events"),
            ("stage66_realhw_dial_customize_mydial_fn_liveview_lut_embed_hil", "slot1_vault_lut_mutation_bytes"),
            ("stage66_realhw_dial_customize_mydial_fn_liveview_lut_embed_hil", "emmc_mutation_bytes"),
        ):
            raw_vm = self._unpack_clean_raw()[4]
            raw_vm[skey][bad_counter] = 1
            self.assertFalse(
                _evaluate_pillar_4(raw_vm, RealHwMilestone324FaultInjection())[0].passed,
                f"{skey}:{bad_counter}",
            )

    def test_44_pillar4_fails_when_future_stage67_fails(self) -> None:
        raw_vm = self._unpack_clean_raw()[4]
        raw_vm["stage67_broken_hil"] = {"all_checks_passed": False}
        self.assertFalse(_evaluate_pillar_4(raw_vm, RealHwMilestone324FaultInjection())[0].passed)

    def test_45_pillar4_enforces_stage65_zero_evf_and_stage66_three_dial_redlines(self) -> None:
        for evf_k in ("fx3_has_builtin_evf", "fx3_has_eye_sensor", "fx6_has_still_flash_stack"):
            raw_vm = self._unpack_clean_raw()[4]
            raw_vm["stage65_realhw_touch_shooting_disp_zero_evf_interval_pb_hil"][evf_k] = True
            self.assertFalse(_evaluate_pillar_4(raw_vm, RealHwMilestone324FaultInjection())[0].passed, evf_k)

        raw_vm2 = self._unpack_clean_raw()[4]
        raw_vm2["stage66_realhw_dial_customize_mydial_fn_liveview_lut_embed_hil"]["fx3_physical_dial_count"] = 2
        self.assertFalse(_evaluate_pillar_4(raw_vm2, RealHwMilestone324FaultInjection())[0].passed)

    # --- 7. Pillar 5: ALL 14 Bench Readiness Verifiers (`Ph186`..`Ph321`) ---

    def test_46_pillar5_tetradecuple_14of14_bench_preflights_happy_path(self) -> None:
        b = self._unpack_clean_raw()
        p5, meta5 = _evaluate_pillar_5(*b[5:36], RealHwMilestone324FaultInjection())
        self.assertTrue(p5.passed, p5.errors)
        self.assertFalse(meta5["overall_ready_for_hardware_attach"])
        for tag in (
            "p186", "p204", "p216", "p227", "p248", "p261",
            "p275", "p279", "p284", "p291", "p302", "p307",
            "p316", "p321",
        ):
            off_k = f"{tag}_offline_go_no_go"
            sim_k = f"{tag}_sim_go_no_go"
            self.assertEqual(meta5[off_k], GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT, off_k)
            self.assertEqual(meta5[sim_k], GO_NO_GO_DRY_RUN_SIMULATED_READY, sim_k)
            self.assertEqual(meta5[f"{tag}_h0_equals_h3_count"], 16, tag)
        self.assertFalse(meta5["p186_card_insert_authorized"])
        for tag in (
            "p204", "p216", "p227", "p248", "p261", "p275",
            "p279", "p284", "p291", "p302", "p307", "p316", "p321",
        ):
            self.assertFalse(meta5[f"{tag}_hardware_live_attachment_authorized"], tag)
        for tag in ("p302", "p307", "p316", "p321"):
            self.assertEqual(meta5[f"{tag}_sim_check_groups_passed"], 4, tag)
            self.assertEqual(meta5[f"{tag}_sim_usb_packets_transmitted"], 0, tag)
            self.assertEqual(meta5[f"{tag}_sim_passive_tx_bytes_emitted"], 0, tag)
        for tag in ("p316", "p321"):
            self.assertEqual(meta5[f"{tag}_wireless_rf_packets_emitted"], 0, tag)
            self.assertEqual(meta5[f"{tag}_rf_packets_transmitted"], 0, tag)
            self.assertEqual(meta5[f"{tag}_e_nd_actuator_tx_count"], 0, tag)
            self.assertEqual(meta5[f"{tag}_slot1_data_sector_writes"], 0, tag)

    def test_47_pillar5_rejects_phase316_bright_mon_shotmark_big6_ssh_faults(self) -> None:
        b = list(self._unpack_clean_raw())
        p316_off, p316_sim, _, _ = copy.deepcopy(self.p316_321_bad)
        p5, _ = _evaluate_pillar_5(
            *b[5:32], p316_off, p316_sim, b[34], b[35], RealHwMilestone324FaultInjection()
        )
        self.assertFalse(p5.passed)

    def test_48_pillar5_rejects_phase316_h0_h3_drift_fault(self) -> None:
        b = list(self._unpack_clean_raw())
        p316_off, p316_sim, _, _ = copy.deepcopy(self.p316_321_drift)
        p5, _ = _evaluate_pillar_5(
            *b[5:32], p316_off, p316_sim, b[34], b[35], RealHwMilestone324FaultInjection()
        )
        self.assertFalse(p5.passed)

    def test_49_pillar5_rejects_phase321_rec_media_proxy_cloud_mymenu_ftpes_faults(self) -> None:
        b = list(self._unpack_clean_raw())
        _, _, p321_off, p321_sim = copy.deepcopy(self.p316_321_bad)
        p5, _ = _evaluate_pillar_5(
            *b[5:34], p321_off, p321_sim, RealHwMilestone324FaultInjection()
        )
        self.assertFalse(p5.passed)

    def test_50_pillar5_rejects_phase321_h0_h3_drift_fault(self) -> None:
        b = list(self._unpack_clean_raw())
        _, _, p321_off, p321_sim = copy.deepcopy(self.p316_321_drift)
        p5, _ = _evaluate_pillar_5(
            *b[5:34], p321_off, p321_sim, RealHwMilestone324FaultInjection()
        )
        self.assertFalse(p5.passed)

    def test_51_pillar5_rejects_phase316_and_321_usb_passive_and_wireless_rf_overrides(self) -> None:
        b = self._unpack_clean_raw()
        for fkw in (
            {"p5_inject_p316_usb_packets_override": 1},
            {"p5_inject_p316_passive_tx_bytes_override": 4},
            {"p5_inject_p316_wireless_rf_packets_override": 1},
            {"p5_inject_p321_usb_packets_override": 1},
            {"p5_inject_p321_passive_tx_bytes_override": 4},
            {"p5_inject_p321_wireless_rf_packets_override": 1},
        ):
            p5, _ = _evaluate_pillar_5(*b[5:36], RealHwMilestone324FaultInjection(**fkw))
            self.assertFalse(p5.passed, fkw)

    def test_52_pillar5_rejects_phase316_and_321_rf_nvs_auth_or_slot1_tier0_mutated(self) -> None:
        # indices inside p5_slice (b[5:36]): 28=p316_sim, 30=p321_sim
        for sim_idx in (28, 30):
            for bad_k, bad_v in (
                ("rf_nvs_p12_p13_writes_authorized", True),
                ("slot1_tier0_vault_mutated", True),
                ("slot1_data_sector_writes", 1),
                ("e_nd_actuator_tx_count", 1),
            ):
                p5_slice = list(self._unpack_clean_raw()[5:36])
                p5_slice[sim_idx][bad_k] = bad_v
                p5, _ = _evaluate_pillar_5(*p5_slice, RealHwMilestone324FaultInjection())
                self.assertFalse(p5.passed, f"idx={sim_idx}:{bad_k}")

    def test_53_pillar5_rejects_offline_if_not_blocked_awaiting_tier0(self) -> None:
        # indices inside p5_slice (b[5:36]): 25=p307_off, 27=p316_off, 29=p321_off
        for off_idx in (25, 27, 29):
            p5_slice = list(self._unpack_clean_raw()[5:36])
            p5_slice[off_idx]["go_no_go"] = GO_NO_GO_DRY_RUN_SIMULATED_READY
            p5, _ = _evaluate_pillar_5(*p5_slice, RealHwMilestone324FaultInjection())
            self.assertFalse(p5.passed, off_idx)

    def test_54_pillar5_rejects_sim_sha256_tamper_and_attach_ready_true(self) -> None:
        # indices inside p5_slice (b[5:36]): 28=p316_sim, 30=p321_sim
        for sim_idx in (28, 30):
            p5_slice = list(self._unpack_clean_raw()[5:36])
            p5_slice[sim_idx]["report_sha256"] = "0" * 64
            p5, _ = _evaluate_pillar_5(*p5_slice, RealHwMilestone324FaultInjection())
            self.assertFalse(p5.passed, sim_idx)

            p5_slice2 = list(self._unpack_clean_raw()[5:36])
            p5_slice2[sim_idx]["overall_ready_for_hardware_attach"] = True
            p5_2, _ = _evaluate_pillar_5(*p5_slice2, RealHwMilestone324FaultInjection())
            self.assertFalse(p5_2.passed, sim_idx)

    def test_55_pillar5_propagates_upstream_phase307_failure(self) -> None:
        b = list(self._unpack_clean_raw())
        _, _, p307_off, p307_sim = copy.deepcopy(self.p302_307_bad)
        p5, _ = _evaluate_pillar_5(
            *b[5:30], p307_off, p307_sim, *b[32:36], RealHwMilestone324FaultInjection()
        )
        self.assertFalse(p5.passed)

    # --- 8. Pillar 6: Live FX3 7.02 QEMU Rounds 28..65+ & < 50 KiB PNG Receipts ---

    def _clean_p1_to_p5_metas(self):
        cls = type(self)
        cached = getattr(cls, "_cached_p1_to_p5_metas", None)
        if cached is None:
            b = self.raw_bundle
            f = RealHwMilestone324FaultInjection()
            p1 = _evaluate_pillar_1(b[0], b[1])
            _, m2 = _evaluate_pillar_2(b[2], f)
            _, m3 = _evaluate_pillar_3(b[3], f)
            _, m4 = _evaluate_pillar_4(b[4], f)
            _, m5 = _evaluate_pillar_5(*b[5:36], f)
            cached = (p1.evidence, m2, m3, m4, m5)
            cls._cached_p1_to_p5_metas = cached
        return cached

    def test_56_pillar6_rounds_28_to_65_at_least_38_rounds_114_runs_76_pngs(self) -> None:
        m1, m2, m3, m4, m5 = self._clean_p1_to_p5_metas()
        p6, meta6 = _evaluate_pillar_6(
            repo_root=REPO_ROOT,
            use_clean_room=True,
            faults=RealHwMilestone324FaultInjection(),
            p1_meta=m1,
            p2_meta=m2,
            p3_meta=m3,
            p4_meta=m4,
            p5_meta=m5,
        )
        self.assertTrue(p6.passed, p6.errors)
        self.assertGreaterEqual(meta6["qemu_rounds_verified"], 38)
        self.assertGreaterEqual(meta6["qemu_runs_verified"], 114)
        self.assertGreaterEqual(meta6["qemu_png_receipts_verified"], 76)
        self.assertLess(meta6["qemu_png_max_bytes"], PNG_MAX_SIZE_50KIB_BYTES)
        self.assertEqual(meta6["qemu_raw_firmware_bytes_leaked"], 0)
        for rnum in range(63, 66):
            self.assertEqual(meta6["qemu_round_runs_by_round"][f"r{rnum}"], 3)

    def test_57_pillar6_committed_rounds63_to_65_png_headers_and_baseline_max_27467b(self) -> None:
        observed_max = 0
        for rnum in range(28, 66):
            for rel in ROUND28_TO_65_PNG_RECEIPTS[rnum]:
                p = REPO_ROOT / rel
                if p.is_file():
                    raw = p.read_bytes()
                    self.assertTrue(raw.startswith(PNG_MAGIC_BYTES), rel)
                    self.assertLess(len(raw), PNG_MAX_SIZE_50KIB_BYTES, rel)
                    if len(raw) > observed_max:
                        observed_max = len(raw)
        if observed_max > 0:
            self.assertLessEqual(observed_max, P324_BASELINE_PNG_MAX_OBSERVED_BYTES)

    def test_58_pillar6_forward_compatible_with_round66_directory_discovery(self) -> None:
        m1, m2, m3, m4, m5 = self._clean_p1_to_p5_metas()
        with tempfile.TemporaryDirectory() as tmp:
            tmp_root = Path(tmp)
            r66_dir = tmp_root / "reports" / "2026-11-18-round66-realhw-wave52-qemu"
            assets_dir = r66_dir / "assets"
            assets_dir.mkdir(parents=True, exist_ok=True)
            for name in ("r66a-alpha.png", "r66a-composited.png"):
                (assets_dir / name).write_bytes(PNG_MAGIC_BYTES + b"\x00" * 128)
            summary = {
                "schema": "fx6-on-fx3-round66-realhw-wave52-qemu-v1",
                "round": 66,
                "kernel_version": "Linux version 4.9.337-scel+ (clean-room-synthetic)",
                "raw_firmware_bytes_leaked": 0,
                "runs": {
                    "r66a_run": {"nop_count": 0, "crashes": 0, "emmc_write_count": 0, "stage_b": {"manifest_count": 13}},
                    "r66b_run": {"nop_count": 0, "crashes": 0, "emmc_write_count": 0, "stage_b": {"manifest_count": 13}},
                    "r66c_run": {"nop_count": 0, "crashes": 0, "emmc_write_count": 0, "stage_b": {"manifest_count": 13}},
                },
                "r66_realhw_wave52_audit": {
                    "all_3_runs_crashes_zero": True,
                    "all_3_runs_emmc_write_zero": True,
                    "fx3_has_builtin_evf": False,
                    "fx3_has_var_shutter": False,
                },
            }
            (r66_dir / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
            p6, meta6 = _evaluate_pillar_6(
                repo_root=tmp_root,
                use_clean_room=True,
                faults=RealHwMilestone324FaultInjection(),
                p1_meta=m1,
                p2_meta=m2,
                p3_meta=m3,
                p4_meta=m4,
                p5_meta=m5,
            )
            self.assertTrue(p6.passed, p6.errors)
            self.assertGreaterEqual(meta6["qemu_rounds_verified"], 39)
            self.assertGreaterEqual(meta6["qemu_runs_verified"], 117)
            self.assertGreaterEqual(meta6["qemu_png_receipts_verified"], 78)

    def test_59_pillar6_forward_compatible_round66_rejects_bad_audit_flag_or_kernel(self) -> None:
        m1, m2, m3, m4, m5 = self._clean_p1_to_p5_metas()
        with tempfile.TemporaryDirectory() as tmp:
            tmp_root = Path(tmp)
            r66_dir = tmp_root / "reports" / "2026-11-18-round66-realhw-broken-qemu"
            r66_dir.mkdir(parents=True, exist_ok=True)
            summary = {
                "schema": "fx6-on-fx3-round66-broken-v1",
                "round": 66,
                "kernel_version": "Linux version 4.9.337-scel+ (clean-room-synthetic)",
                "raw_firmware_bytes_leaked": 0,
                "runs": {
                    "r66a_run": {"nop_count": 0, "crashes": 0, "emmc_write_count": 0, "stage_b": {"manifest_count": 13}},
                },
                "r66_broken_audit": {
                    "all_3_runs_crashes_zero": True,
                    "fx3_has_builtin_evf": True,
                },
            }
            (r66_dir / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
            p6, _ = _evaluate_pillar_6(
                repo_root=tmp_root,
                use_clean_room=True,
                faults=RealHwMilestone324FaultInjection(),
                p1_meta=m1,
                p2_meta=m2,
                p3_meta=m3,
                p4_meta=m4,
                p5_meta=m5,
            )
            self.assertFalse(p6.passed)

    def test_60_pillar6_fails_on_rounds63_to_65_schema_tamper(self) -> None:
        m1, m2, m3, m4, m5 = self._clean_p1_to_p5_metas()
        for rnum in range(63, 66):
            p6, _ = _evaluate_pillar_6(
                repo_root=REPO_ROOT,
                use_clean_room=True,
                faults=RealHwMilestone324FaultInjection(p6_tamper_schema_round_num=rnum),
                p1_meta=m1,
                p2_meta=m2,
                p3_meta=m3,
                p4_meta=m4,
                p5_meta=m5,
            )
            self.assertFalse(p6.passed, rnum)

    def test_61_pillar6_fails_on_round65_nop_crash_emmc_write_or_raw_leak(self) -> None:
        m1, m2, m3, m4, m5 = self._clean_p1_to_p5_metas()
        for fkw in (
            {"p6_round_nop_override_num": 65, "p6_round_nop_count_override": 1},
            {"p6_round_crash_override_num": 65, "p6_round_crashes_override": 1},
            {"p6_round_emmc_override_num": 65, "p6_round_emmc_writes_override": 1},
            {"p6_raw_firmware_bytes_leaked_override": 8},
        ):
            p6, _ = _evaluate_pillar_6(
                repo_root=REPO_ROOT,
                use_clean_room=True,
                faults=RealHwMilestone324FaultInjection(**fkw),
                p1_meta=m1,
                p2_meta=m2,
                p3_meta=m3,
                p4_meta=m4,
                p5_meta=m5,
            )
            self.assertFalse(p6.passed, fkw)

    def test_62_pillar6_fails_when_png_receipt_reaches_or_exceeds_50kib_ceiling(self) -> None:
        m1, m2, m3, m4, m5 = self._clean_p1_to_p5_metas()
        p6, _ = _evaluate_pillar_6(
            repo_root=REPO_ROOT,
            use_clean_room=True,
            faults=RealHwMilestone324FaultInjection(
                p6_png_size_override_round_num=65,
                p6_png_size_override_bytes=PNG_MAX_SIZE_50KIB_BYTES,
            ),
            p1_meta=m1,
            p2_meta=m2,
            p3_meta=m3,
            p4_meta=m4,
            p5_meta=m5,
        )
        self.assertFalse(p6.passed)

    def test_63_pillar6_cross_pillar_p1_cross_model_and_p2_cnflasha_invariants_fail(self) -> None:
        m1, m2, m3, m4, m5 = self._clean_p1_to_p5_metas()
        m1_bad = dict(m1)
        m1_bad["cross_model_flash_authorized"] = True
        self.assertFalse(
            _evaluate_pillar_6(
                repo_root=REPO_ROOT,
                use_clean_room=True,
                faults=RealHwMilestone324FaultInjection(),
                p1_meta=m1_bad,
                p2_meta=m2,
                p3_meta=m3,
                p4_meta=m4,
                p5_meta=m5,
            )[0].passed
        )

        m2_bad = dict(m2)
        m2_bad["cnflasha_userspace_write_blocked"] = False
        self.assertFalse(
            _evaluate_pillar_6(
                repo_root=REPO_ROOT,
                use_clean_room=True,
                faults=RealHwMilestone324FaultInjection(),
                p1_meta=m1,
                p2_meta=m2_bad,
                p3_meta=m3,
                p4_meta=m4,
                p5_meta=m5,
            )[0].passed
        )

    def test_64_pillar6_cross_pillar_p316_and_p321_h0_h3_rf_end_slot1_fail_closed(self) -> None:
        m1, m2, m3, m4, m5 = self._clean_p1_to_p5_metas()
        for bad_k, bad_v in (
            ("p316_h0_equals_h3_count", 15),
            ("p316_hardware_live_attachment_authorized", True),
            ("p316_wireless_rf_packets_emitted", 1),
            ("p316_e_nd_actuator_tx_count", 1),
            ("p316_slot1_data_sector_writes", 1),
            ("p321_h0_equals_h3_count", 15),
            ("p321_hardware_live_attachment_authorized", True),
            ("p321_sim_passive_tx_bytes_emitted", 1),
            ("p321_wireless_rf_packets_emitted", 1),
            ("p321_e_nd_actuator_tx_count", 1),
            ("p321_slot1_data_sector_writes", 1),
        ):
            m5_bad = dict(m5)
            m5_bad[bad_k] = bad_v
            p6_bad, _ = _evaluate_pillar_6(
                repo_root=REPO_ROOT,
                use_clean_room=True,
                faults=RealHwMilestone324FaultInjection(),
                p1_meta=m1,
                p2_meta=m2,
                p3_meta=m3,
                p4_meta=m4,
                p5_meta=m5_bad,
            )
            self.assertFalse(p6_bad.passed, bad_k)

    # --- 9. Fail-Closed Verifier, CLI & Donorless CI ---

    def test_65_verifier_rejects_non_mapping_payload(self) -> None:
        self.assertFalse(verify_realhw_milestone324_master_gate("not-a-dict").valid)
        self.assertFalse(verify_realhw_milestone324_master_gate(123).valid)
        self.assertFalse(verify_realhw_milestone324_master_gate(None).valid)  # type: ignore[arg-type]

    def test_66_verifier_rejects_sha256_tamper_and_schema_tamper(self) -> None:
        d = self.rep_clean.to_dict()
        d["milestone324_sha256"] = "f" * 64
        self.assertFalse(verify_realhw_milestone324_master_gate(d).valid)

        d2 = self.rep_clean.to_dict()
        d2["schema"] = "wrong_schema_v1"
        d2["milestone324_sha256"] = compute_milestone324_sha256(d2)
        self.assertFalse(verify_realhw_milestone324_master_gate(d2).valid)

    def test_67_verifier_rejects_redline_tamper_even_when_rehashed(self) -> None:
        for k, v in (
            ("overall_ready_for_hardware_attach", True),
            ("hardware_live_attachment_authorized", True),
            ("cross_model_flash_authorized", True),
            ("persistent_emmc_writes_authorized", True),
            ("spi_nor_write_authorized", True),
            ("el3_payload_transmit_authorized", True),
            ("cnflasha_userspace_write_blocked", False),
            ("usb_packets_transmitted", 1),
            ("physical_device_writes", 1),
            ("raw_firmware_bytes_leaked", 1),
            ("e_nd_actuator_tx_count", 1),
            ("rf_packets_transmitted", 1),
            ("slot1_data_sector_writes", 1),
            ("otp_fuse_touches", 1),
            ("rpmb_counter_increments", 1),
            ("passive_tx_bytes_emitted", 1),
            ("p316_hardware_live_attachment_authorized", True),
            ("p316_wireless_rf_packets_emitted", 1),
            ("p316_slot1_data_sector_writes", 1),
            ("p321_hardware_live_attachment_authorized", True),
            ("p321_wireless_rf_packets_emitted", 1),
            ("p321_slot1_data_sector_writes", 1),
        ):
            d = self.rep_clean.to_dict()
            d[k] = v
            d["milestone324_sha256"] = compute_milestone324_sha256(d)
            self.assertFalse(verify_realhw_milestone324_master_gate(d).valid, k)

    def test_68_verifier_accepts_forward_compatible_higher_counts(self) -> None:
        d = self.rep_clean.to_dict()
        d["gate142_total_gates"] = 144
        d["gate142_offline_verified"] = 141
        d["gate142_simulated_verified"] = 144
        d["recovery_pillar_count"] = 57
        d["recovery_pillars_passed"] = 57
        d["auditors_total"] = 46
        d["auditors_passed"] = 46
        d["vm_stages_total"] = 67
        d["vm_stages_passed"] = 67
        d["qemu_rounds_total"] = 39
        d["qemu_rounds_verified"] = 39
        d["qemu_runs_total"] = 117
        d["qemu_runs_verified"] = 117
        d["qemu_png_receipts_total"] = 78
        d["qemu_png_receipts_verified"] = 78
        d["milestone324_sha256"] = compute_milestone324_sha256(d)
        v = verify_realhw_milestone324_master_gate(d)
        self.assertTrue(v.valid, v.errors)

    def test_69_verifier_rejects_sub_threshold_counts_and_raw_bytes(self) -> None:
        for k, v in (
            ("gate142_simulated_verified", 141),
            ("recovery_pillar_count", 55),
            ("auditors_passed", 44),
            ("vm_stages_passed", 65),
            ("p316_sim_check_groups_passed", 3),
            ("p321_sim_check_groups_passed", 3),
            ("qemu_rounds_verified", 37),
            ("qemu_runs_verified", 113),
            ("qemu_png_receipts_verified", 75),
            ("qemu_png_max_bytes", PNG_MAX_SIZE_50KIB_BYTES),
        ):
            d = self.rep_clean.to_dict()
            d[k] = v
            d["milestone324_sha256"] = compute_milestone324_sha256(d)
            self.assertFalse(verify_realhw_milestone324_master_gate(d).valid, k)

        d_raw = self.rep_clean.to_dict()
        d_raw["pillars"][0]["summary"] = "leaked b'\\x7fELF'"
        d_raw["milestone324_sha256"] = compute_milestone324_sha256(d_raw)
        self.assertFalse(verify_realhw_milestone324_master_gate(d_raw).valid)

    def test_70_cli_verify_milestone_324_summary_and_out_alias_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            out_json = tmp_path / "m324.json"
            out_md = tmp_path / "m324.md"
            buf = io.StringIO()
            with (
                mock.patch(
                    "fx6_closure.realhw_milestone324_master_gate.evaluate_realhw_milestone324_master_gate",
                    return_value=self.rep_clean,
                ),
                mock.patch("sys.stdout", buf),
            ):
                rc = fx6_cli_main(
                    [
                        "verify-milestone-324",
                        "--force-clean-room",
                        "--out",
                        str(out_json),
                        "--markdown-out",
                        str(out_md),
                    ]
                )
            self.assertEqual(rc, 0)
            text = buf.getvalue()
            self.assertIn("status=OK", text)
            self.assertIn("schema=realhw_milestone324_master_gate_v1", text)
            self.assertIn("cnflasha_ro=True", text)
            self.assertIn("cross_model_flash_auth=False", text)
            self.assertIn(
                "p316=BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT/DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH",
                text,
            )
            self.assertIn(
                "p321=BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT/DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH",
                text,
            )
            self.assertIn("rf_pkts=0", text)
            self.assertIn("slot1_writes=0", text)
            self.assertIn("ready_attach=False", text)
            self.assertIsNotNone(re.search(r"gate142=(\d+)/(\d+)", text))
            self.assertIsNotNone(re.search(r"qemu=(\d+)/(\d+)\((\d+)/(\d+)\)", text))
            self.assertTrue(out_json.is_file())
            self.assertTrue(out_md.is_file())
            self.assertTrue(
                verify_realhw_milestone324_master_gate(json.loads(out_json.read_text())).valid
            )

    def test_71_cli_verify_milestone_324_json_stdout_and_failure_exit_code(self) -> None:
        buf = io.StringIO()
        with (
            mock.patch(
                "fx6_closure.realhw_milestone324_master_gate.evaluate_realhw_milestone324_master_gate",
                return_value=self.rep_clean,
            ),
            mock.patch("sys.stdout", buf),
        ):
            rc = fx6_cli_main(["verify-milestone-324", "--clean-room", "--json"])
        self.assertEqual(rc, 0)
        parsed = json.loads(buf.getvalue())
        self.assertEqual(parsed["schema"], REALHW_MILESTONE324_SCHEMA)
        self.assertEqual(parsed["usb_packets_transmitted"], 0)
        self.assertFalse(parsed["overall_ready_for_hardware_attach"])
        self.assertFalse(parsed["cross_model_flash_authorized"])

        bad_rep = replace(
            self.rep_clean,
            all_pillars_milestone_ready=False,
            status=STATUS_FAIL_CLOSED,
            passed_pillar_count=5,
            failed_pillar_ids=("P1",),
            milestone324_sha256="0" * 64,
        )
        buf2 = io.StringIO()
        with (
            mock.patch(
                "fx6_closure.realhw_milestone324_master_gate.evaluate_realhw_milestone324_master_gate",
                return_value=bad_rep,
            ),
            mock.patch("sys.stdout", buf2),
        ):
            rc2 = fx6_cli_main(["verify-milestone-324", "--force-clean-room"])
        self.assertEqual(rc2, 1)
        self.assertIn("status=FAILED", buf2.getvalue())

    def test_72_cli_verify_milestone_324_simulate_bench_dry_run_flag(self) -> None:
        captured: dict = {}

        def _fake_eval(**kwargs):
            captured.update(kwargs)
            return self.rep_clean

        buf = io.StringIO()
        with (
            mock.patch(
                "fx6_closure.realhw_milestone324_master_gate.evaluate_realhw_milestone324_master_gate",
                side_effect=_fake_eval,
            ),
            mock.patch("sys.stdout", buf),
        ):
            rc = fx6_cli_main(
                ["verify-milestone-324", "--force-clean-room", "--simulate-bench-dry-run", "--json"]
            )
        self.assertEqual(rc, 0)
        self.assertTrue(captured.get("simulate_bench_dry_run"))
        self.assertTrue(captured.get("force_clean_room"))

    def test_73_verify_milestone_324_cli_direct_helper_entrypoint(self) -> None:
        buf = io.StringIO()
        with (
            mock.patch(
                "fx6_closure.realhw_milestone324_master_gate.evaluate_realhw_milestone324_master_gate",
                return_value=self.rep_clean,
            ),
            mock.patch("sys.stdout", buf),
        ):
            rc = verify_milestone_324_cli(["--clean-room", "--simulate-bench-dry-run", "--json"])
        self.assertEqual(rc, 0)
        parsed = json.loads(buf.getvalue())
        self.assertEqual(parsed["schema"], REALHW_MILESTONE324_SCHEMA)
        self.assertTrue(parsed["cnflasha_userspace_write_blocked"])

    def test_74_argparse_help_formatting_safe_for_python_314_and_macos(self) -> None:
        buf_top = io.StringIO()
        with mock.patch("sys.stdout", buf_top):
            with self.assertRaises(SystemExit) as ctx_top:
                fx6_cli_main(["--help"])
        self.assertEqual(ctx_top.exception.code, 0)
        self.assertIn("verify-milestone-324", buf_top.getvalue())

        buf_sub = io.StringIO()
        with mock.patch("sys.stdout", buf_sub):
            with self.assertRaises(SystemExit) as ctx_sub:
                fx6_cli_main(["verify-milestone-324", "--help"])
        self.assertEqual(ctx_sub.exception.code, 0)
        self.assertIn("--force-clean-room", buf_sub.getvalue())
        self.assertIn("--simulate-bench-dry-run", buf_sub.getvalue())
        self.assertNotIn("%(", buf_sub.getvalue())

    def test_75_subprocess_cli_clean_room_via_sys_executable(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["FX3_FX6_FORCE_CLEAN_ROOM"] = "1"
        env["PYTHONPATH"] = os.pathsep.join(
            str(REPO_ROOT / rel)
            for rel in (
                "outputs/fx3-safety",
                "outputs/fx3-recovery-adapter",
                "outputs/fx3-firmware-lab",
                "outputs/fx3-vm",
                "outputs/fx6-on-fx3-closure",
            )
        )
        t0 = time.monotonic()
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "fx6_closure",
                "verify-milestone-324",
                "--force-clean-room",
                "--simulate-bench-dry-run",
                "--json",
            ],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        elapsed = time.monotonic() - t0
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["schema"], REALHW_MILESTONE324_SCHEMA)
        self.assertTrue(payload["all_pillars_milestone_ready"])
        self.assertGreaterEqual(payload["gate142_simulated_verified"], 142)
        self.assertGreaterEqual(payload["recovery_pillars_passed"], 56)
        self.assertGreaterEqual(payload["auditors_passed"], 45)
        self.assertGreaterEqual(payload["vm_stages_passed"], 66)
        self.assertGreaterEqual(payload["qemu_rounds_verified"], 38)
        self.assertGreaterEqual(payload["qemu_runs_verified"], 114)
        self.assertGreaterEqual(payload["qemu_png_receipts_verified"], 76)
        self.assertLess(elapsed, _ci_time_budget(30.0))

    def test_76_subprocess_cli_clean_room_via_fx3_clean_room_test_env(self) -> None:
        env = dict(os.environ)
        env.pop("FX3_FX6_FORCE_CLEAN_ROOM", None)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["FX3_CLEAN_ROOM_TEST"] = "1"
        env["PYTHONPATH"] = os.pathsep.join(
            str(REPO_ROOT / rel)
            for rel in (
                "outputs/fx3-safety",
                "outputs/fx3-recovery-adapter",
                "outputs/fx3-firmware-lab",
                "outputs/fx3-vm",
                "outputs/fx6-on-fx3-closure",
            )
        )
        t0 = time.monotonic()
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "fx6_closure",
                "verify-milestone-324",
                "--json",
            ],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        elapsed = time.monotonic() - t0
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["schema"], REALHW_MILESTONE324_SCHEMA)
        self.assertTrue(payload["all_pillars_milestone_ready"])
        self.assertGreaterEqual(payload["gate142_simulated_verified"], 142)
        self.assertGreaterEqual(payload["recovery_pillars_passed"], 56)
        self.assertLess(elapsed, _ci_time_budget(30.0))

    def test_77_synthetic_clean_room_kwarg_alias_and_suite_runtime_budget(self) -> None:
        rep = evaluate_milestone_324_master_gate(
            synthetic_clean_room=True,
            _raw_bundle_override=self._unpack_clean_raw(),
        )
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(rep.all_pillars_milestone_ready)
        self.assertLess(self.default_elapsed_s, _ci_time_budget(30.0))

    def test_78_preserves_milestone_311_295_264_254_entrypoints_and_non_overlapping_exports(self) -> None:
        self.assertTrue(hasattr(fx6_closure, "evaluate_realhw_milestone311_master_gate"))
        self.assertTrue(hasattr(fx6_closure, "evaluate_realhw_milestone295_master_gate"))
        self.assertTrue(hasattr(fx6_closure, "evaluate_realhw_milestone264_master_gate"))
        self.assertTrue(hasattr(fx6_closure, "evaluate_realhw_milestone254_master_gate"))
        self.assertNotEqual(fx6_closure.REALHW_MILESTONE311_SCHEMA, fx6_closure.REALHW_MILESTONE324_SCHEMA)
        self.assertEqual(
            fx6_closure.evaluate_realhw_milestone324_master_gate,
            evaluate_realhw_milestone324_master_gate,
        )

    def test_79_donorless_linux_ci_repo_without_mac_work_auto_clean_room(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            troot = Path(tmp)
            for item in REPO_ROOT.iterdir():
                if item.name != "Mac":
                    (troot / item.name).symlink_to(item.resolve())
            rep = evaluate_realhw_milestone324_master_gate(
                repo_root=troot,
                fx6_lib_dir=troot / "nonexistent_fx6",
                fx3_modules_dir=troot / "nonexistent_fx3",
                force_clean_room=None,
            )
            self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertTrue(rep.all_pillars_milestone_ready, rep.errors)
            self.assertEqual(rep.passed_pillar_count, 6)
            self.assertTrue(verify_realhw_milestone324_master_gate(rep).valid)

    def test_80_pillar1_142gate_rejects_persistent_write_and_cross_model_via_live_dict(self) -> None:
        f = RealHwMilestone324FaultInjection(
            p1_rec_media_autoswitch_proxy_kwargs={"bypass_slot1_vault_firewall": True},
            p1_creators_cloud_mymenu_kwargs={"slot1_vault_overwrite_requested": True},
            p1_request_persistent_writes=True,
        )
        w = _fault_to_142gate_worker_dict(f)
        self.assertTrue(w["p1_request_persistent_writes"])
        self.assertEqual(w["p1_rec_media_autoswitch_proxy_kwargs"], {"bypass_slot1_vault_firewall": True})
        self.assertEqual(w["p1_creators_cloud_mymenu_kwargs"], {"slot1_vault_overwrite_requested": True})

        raw_off, raw_sim = self._unpack_clean_raw()[:2]
        raw_sim["persistent_emmc_writes_authorized"] = True
        raw_sim["persistent_write_release"] = True
        self.assertFalse(_evaluate_pillar_1(raw_off, raw_sim).passed)

    def test_81_pillar2_passes_with_optional_p55_subkeys_present_and_fails_if_tampered(self) -> None:
        rec_56 = self._unpack_clean_raw()[2]
        rec_56["pillar55_a_lens_comp_af_illuminator_vault"] = {"passed": True}
        rec_56["pillar55_b_aperture_drive_folder_rating_vault"] = {"passed": True}
        self.assertTrue(_evaluate_pillar_2(rec_56, RealHwMilestone324FaultInjection())[0].passed)

        rec_56_bad = self._unpack_clean_raw()[2]
        rec_56_bad["pillar55_a_lens_comp_af_illuminator_vault"] = {"passed": False}
        self.assertFalse(_evaluate_pillar_2(rec_56_bad, RealHwMilestone324FaultInjection())[0].passed)

    def test_82_pillar5_14_of_14_preflights_reject_p316_and_p321_group_count_mismatch(self) -> None:
        for sim_idx in (28, 30):
            p5_slice = list(self._unpack_clean_raw()[5:36])
            p5_slice[sim_idx]["check_groups_passed"] = 3
            p5, _ = _evaluate_pillar_5(*p5_slice, RealHwMilestone324FaultInjection())
            self.assertFalse(p5.passed, sim_idx)

    def test_83_verifier_rejects_p136_p143_p154_or_p316_p321_h0_h3_drift_when_rehashed(self) -> None:
        for k, v in (
            ("p143_h0_equals_h3_count", 15),
            ("p154_bench_go", False),
            ("p316_h0_equals_h3_count", 15),
            ("p321_h0_equals_h3_count", 15),
            ("h0_equals_h3_count", 15),
        ):
            d = self.rep_clean.to_dict()
            d[k] = v
            d["milestone324_sha256"] = compute_milestone324_sha256(d)
            self.assertFalse(verify_realhw_milestone324_master_gate(d).valid, k)

    def test_84_makefile_and_clean_room_ci_wire_verify_milestone_324(self) -> None:
        makefile_text = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
        self.assertIn("verify-milestone-324:", makefile_text)
        self.assertIn("verify-milestone-324", makefile_text.split("verify-fast:", 1)[1].splitlines()[0])

        ci_text = (REPO_ROOT / ".github" / "workflows" / "clean-room-ci.yml").read_text(encoding="utf-8")
        self.assertIn("verify-142-gates --force-clean-room --simulate-bench-dry-run", ci_text)
        self.assertIn("verify-56pillar-recovery --clean-room", ci_text)
        self.assertIn("verify-milestone-324 --force-clean-room", ci_text)


if __name__ == "__main__":
    unittest.main()
