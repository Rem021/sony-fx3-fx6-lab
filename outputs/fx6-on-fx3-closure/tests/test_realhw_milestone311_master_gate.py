"""Phase 311 dual-mode unit tests for Grand Milestone Phase 311 6-Pillar Real-Hardware Master Gate."""

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
from fx6_closure.realhw_milestone295_master_gate import (  # noqa: E402
    RealHwMilestone295FaultInjection,
    _worker_phase284_291,
)
from fx6_closure.realhw_milestone311_master_gate import (  # noqa: E402
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
    MILESTONE311_SCHEMA_VERSION,
    OTP_FUSE_TOUCHES,
    OTP_FUSE_WRITES,
    OVERALL_READY_FOR_HARDWARE_ATTACH,
    P311_BASELINE_PNG_MAX_OBSERVED_BYTES,
    P311_PHYSICAL_DEVICE_WRITES,
    P311_PILLAR_IDS,
    P311_PILLAR_SPECS,
    P311_PNG_MAX_SIZE_BYTES,
    P311_RAW_FIRMWARE_BYTES_LEAKED,
    P311_SCHEMA,
    P311_STATUS_FAIL_CLOSED,
    P311_STATUS_MILESTONE_READY,
    P311_VERSION,
    P8_CP_MUTATION_FORBIDDEN,
    PASSIVE_TX_BYTES,
    PASSIVE_TX_BYTES_EMITTED,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHASE_311_VERSION,
    PHYSICAL_DEVICE_WRITES,
    PHYSICAL_USB_PACKETS_EMITTED,
    PILLAR_IDS,
    PILLAR_SPECS,
    PNG_MAGIC_BYTES,
    PNG_MAX_SIZE_50KIB_BYTES,
    PNG_MAX_SIZE_BYTES,
    RAW_FIRMWARE_BYTES_LEAKED,
    REALHW_MILESTONE311_SCHEMA,
    RECOVERY_54_PILLAR_IDS,
    ROUND28_TO_62_PNG_RECEIPTS,
    ROUND28_TO_62_SPECS,
    ROUND59_EXPECTED_SCHEMA,
    ROUND60_EXPECTED_SCHEMA,
    ROUND61_EXPECTED_SCHEMA,
    ROUND62_EXPECTED_SCHEMA,
    RPMB_COUNTER_INCREMENTS,
    RPMB_WRITES,
    SPI_NOR_WRITE_AUTHORIZED,
    STATUS_FAIL_CLOSED,
    STATUS_MILESTONE_READY,
    USB_OR_CAMERA_OPERATIONS,
    USB_PACKETS_TRANSMITTED,
    VM_COEMULATION_62_STAGE_KEYS,
    WBI_MUTATION_BYTES,
    WBI_P5_WRITE_AND_HIBERNATION_FORBIDDEN,
    RealHwMilestone311FaultInjection,
    RealHwMilestone311MasterGateReport,
    _collect_parallel_milestone311_results,
    _discover_highest_recovery_master,
    _discover_highest_safety_gate_evaluator,
    _evaluate_pillar_1,
    _evaluate_pillar_2,
    _evaluate_pillar_3,
    _evaluate_pillar_4,
    _evaluate_pillar_5,
    _evaluate_pillar_6,
    _fault_to_134gate_worker_dict,
    _normalize_54plus_pillar_fault_id,
    _worker_134plus_gate_single,
    _worker_phase302_307,
    _worker_recovery_54plus_pillar,
    build_realhw_milestone311_master_gate_report,
    compute_milestone311_sha256,
    evaluate_milestone311_master_gate,
    evaluate_milestone_311_master_gate,
    evaluate_realhw_milestone311_master_gate,
    render_milestone311_markdown,
    verify_milestone_311_cli,
    verify_milestone_311_master_gate,
    verify_realhw_milestone311_master_gate,
)

_RAW_BYTES_REPR_REGEX = r"(?<![0-9A-Za-z_/.-])b['\"]"


def _ci_time_budget(base_seconds: float) -> float:
    return base_seconds + (15.0 if os.environ.get("GITHUB_ACTIONS") == "true" else 0.0)


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

    g134_fdict = _fault_to_134gate_worker_dict(
        RealHwMilestone311FaultInjection(
            p1_steadyshot_selftimer_kwargs={"movie_self_timer_requested": True},
            p1_zebra_peaking_streaming_kwargs={"rf_nvs_write_requested": True},
            p1_request_persistent_writes=True,
        )
    )
    fx6_s = str(DEFAULT_FX6_DONOR_LIB_DIR)
    fx3_s = str(DEFAULT_FX3_MODULES_DIR)
    ctx = mp.get_context("fork")
    with ProcessPoolExecutor(max_workers=4, mp_context=ctx) as pool:
        fut_g134 = pool.submit(_worker_134plus_gate_single, (str(REPO_ROOT), True, True, g134_fdict))
        fut_p54 = pool.submit(_worker_recovery_54plus_pillar, (True, "pillar_54"))
        fut_302_307_fault = pool.submit(
            _worker_phase302_307,
            (
                fx6_s,
                fx3_s,
                True,
                {"lens_af_copy_evf": True},
                {"dial_lut_ibis_rf_slot1": True},
            ),
        )
        fut_302_307_drift = pool.submit(
            _worker_phase302_307,
            (fx6_s, fx3_s, True, {"h0_h3_drift": True}, {"h0_h3_drift": True}),
        )
        fut_284_291_fault = pool.submit(
            _worker_phase284_291,
            (fx6_s, fx3_s, True, {}, {"focus_zoom_dci4k_clean": True}),
        )
        bad_g134 = fut_g134.result()
        bad_p54 = fut_p54.result()
        p302_307_bad = fut_302_307_fault.result()
        p302_307_drift = fut_302_307_drift.result()
        p284_291_bad = fut_284_291_fault.result()
    conn.send((bad_g134, bad_p54, p302_307_bad, p302_307_drift, p284_291_bad))
    conn.close()


class TestRealHwMilestone311MasterGate(unittest.TestCase):
    """Comprehensive 78 dual-mode unit tests for Grand Milestone Phase 311."""

    raw_bundle: tuple
    rep_default: RealHwMilestone311MasterGateReport
    rep_clean: RealHwMilestone311MasterGateReport
    bad_sim_g134: dict
    bad_rec_54: dict
    p302_307_bad: tuple
    p302_307_drift: tuple
    p284_291_bad: tuple
    default_elapsed_s: float

    @classmethod
    def setUpClass(cls) -> None:
        import multiprocessing as mp

        t0 = time.monotonic()
        ctx = mp.get_context("fork")
        if not _is_forced_clean_room():
            cls.rep_default = evaluate_milestone_311_master_gate()
        recv_conn, send_conn = ctx.Pipe(duplex=False)
        proc = ctx.Process(
            target=_fork_child_fault_fixtures_only,
            args=(send_conn,),
            daemon=False,
        )
        proc.start()
        send_conn.close()
        try:
            cls.raw_bundle = _collect_parallel_milestone311_results(
                repo_root=REPO_ROOT,
                fx6_lib_dir=DEFAULT_FX6_DONOR_LIB_DIR,
                fx3_modules_dir=DEFAULT_FX3_MODULES_DIR,
                use_clean_room=True,
                faults=RealHwMilestone311FaultInjection(),
            )
            (
                cls.bad_sim_g134,
                cls.bad_rec_54,
                cls.p302_307_bad,
                cls.p302_307_drift,
                cls.p284_291_bad,
            ) = recv_conn.recv()
        finally:
            recv_conn.close()
            proc.join(timeout=30)
        cls.rep_clean = evaluate_milestone_311_master_gate(
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
        self.assertEqual(REALHW_MILESTONE311_SCHEMA, "realhw_milestone311_master_gate_v1")
        self.assertEqual(MILESTONE311_SCHEMA_VERSION, REALHW_MILESTONE311_SCHEMA)
        self.assertEqual(P311_SCHEMA, REALHW_MILESTONE311_SCHEMA)
        self.assertEqual(PHASE_311_VERSION, "311.0.0")
        self.assertEqual(P311_VERSION, "311.0.0")
        self.assertEqual(PILLAR_IDS, ("P1", "P2", "P3", "P4", "P5", "P6"))
        self.assertEqual(P311_PILLAR_IDS, PILLAR_IDS)
        self.assertEqual(len(PILLAR_SPECS), 6)
        self.assertEqual(P311_PILLAR_SPECS, PILLAR_SPECS)
        self.assertGreaterEqual(len(RECOVERY_54_PILLAR_IDS), 54)
        self.assertGreaterEqual(len(FIRMWARE_LAB_45_AUDITOR_KEYS), 45)
        self.assertGreaterEqual(len(VM_COEMULATION_62_STAGE_KEYS), 62)
        self.assertGreaterEqual(len(ROUND28_TO_62_SPECS), 35)
        self.assertEqual(PNG_MAX_SIZE_50KIB_BYTES, 51200)
        self.assertEqual(PNG_MAX_SIZE_BYTES, 51200)
        self.assertEqual(P311_PNG_MAX_SIZE_BYTES, 51200)
        self.assertEqual(P311_BASELINE_PNG_MAX_OBSERVED_BYTES, 27467)

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
        self.assertEqual(P311_STATUS_MILESTONE_READY, STATUS_MILESTONE_READY)
        self.assertEqual(P311_STATUS_FAIL_CLOSED, STATUS_FAIL_CLOSED)
        for zero_const in (
            USB_PACKETS_TRANSMITTED,
            PHYSICAL_USB_PACKETS_EMITTED,
            PHYSICAL_DEVICE_WRITES,
            P311_PHYSICAL_DEVICE_WRITES,
            RAW_FIRMWARE_BYTES_LEAKED,
            P311_RAW_FIRMWARE_BYTES_LEAKED,
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
            "P311_CROSS_MODEL_FLASH_AUTHORIZED",
            "MILESTONE311_PHYSICAL_DEVICE_WRITES",
            "MILESTONE311_PILLAR_IDS",
            "MILESTONE311_PILLAR_SPECS",
            "MILESTONE311_PNG_MAX_SIZE_BYTES",
            "MILESTONE311_RAW_FIRMWARE_BYTES_LEAKED",
            "MILESTONE311_SCHEMA_VERSION",
            "P311_BASELINE_PNG_MAX_OBSERVED_BYTES",
            "P311_PHYSICAL_DEVICE_WRITES",
            "P311_PILLAR_IDS",
            "P311_PILLAR_SPECS",
            "P311_PNG_MAX_SIZE_BYTES",
            "P311_RAW_FIRMWARE_BYTES_LEAKED",
            "P311_SCHEMA",
            "P311_STATUS_FAIL_CLOSED",
            "P311_STATUS_MILESTONE_READY",
            "P311_VERSION",
            "PHASE_311_VERSION",
            "REALHW_MILESTONE311_SCHEMA",
            "RECOVERY_54_PILLAR_IDS",
            "ROUND28_TO_62_PNG_RECEIPTS",
            "ROUND28_TO_62_SPECS",
            "ROUND59_EXPECTED_SCHEMA",
            "ROUND60_EXPECTED_SCHEMA",
            "ROUND61_EXPECTED_SCHEMA",
            "ROUND62_EXPECTED_SCHEMA",
            "STATUS_MILESTONE311_FAIL_CLOSED",
            "STATUS_MILESTONE311_READY",
            "VM_COEMULATION_62_STAGE_KEYS",
            "Milestone311PillarResult",
            "RealHwMilestone311FaultInjection",
            "RealHwMilestone311MasterGateReport",
            "RealHwMilestone311VerifyResult",
            "build_realhw_milestone311_master_gate_report",
            "compute_milestone311_sha256",
            "evaluate_milestone311_master_gate",
            "evaluate_milestone_311_master_gate",
            "evaluate_realhw_milestone311_master_gate",
            "render_milestone311_markdown",
            "verify_milestone_311_cli",
            "verify_milestone_311_master_gate",
            "verify_realhw_milestone311_master_gate",
        }
        self.assertTrue(expected.issubset(set(fx6_closure.__all__)))
        for sym in expected:
            self.assertTrue(hasattr(fx6_closure, sym), sym)
        self.assertEqual(fx6_closure.REALHW_MILESTONE295_SCHEMA, "realhw_milestone295_master_gate_v1")
        self.assertEqual(fx6_closure.REALHW_MILESTONE264_SCHEMA, "realhw_milestone264_master_gate_v1")
        self.assertEqual(fx6_closure.REALHW_MILESTONE254_SCHEMA, "realhw_milestone254_master_gate_v1")
        self.assertEqual(fx6_closure.REALHW_MILESTONE233_SCHEMA, "realhw_milestone233_master_gate_v1")

    def test_04_builder_and_verifier_aliases_point_to_canonical_functions(self) -> None:
        self.assertIs(build_realhw_milestone311_master_gate_report, evaluate_realhw_milestone311_master_gate)
        self.assertIs(evaluate_milestone_311_master_gate, evaluate_realhw_milestone311_master_gate)
        self.assertIs(evaluate_milestone311_master_gate, evaluate_realhw_milestone311_master_gate)
        self.assertIs(verify_milestone_311_master_gate, verify_realhw_milestone311_master_gate)

    def test_05_rounds59_to_62_specs_and_png_pairs_registered(self) -> None:
        by_num = {s.round_num: s for s in ROUND28_TO_62_SPECS}
        self.assertGreaterEqual(len(by_num), 35)
        self.assertGreaterEqual(len(ROUND28_TO_62_PNG_RECEIPTS), 35)
        for rnum, exp_schema in (
            (59, ROUND59_EXPECTED_SCHEMA),
            (60, ROUND60_EXPECTED_SCHEMA),
            (61, ROUND61_EXPECTED_SCHEMA),
            (62, ROUND62_EXPECTED_SCHEMA),
        ):
            self.assertIn(rnum, by_num)
            self.assertEqual(by_num[rnum].expected_schema, exp_schema)
            self.assertEqual(len(by_num[rnum].run_specs), 3)
            self.assertIn(rnum, ROUND28_TO_62_PNG_RECEIPTS)
            self.assertEqual(len(ROUND28_TO_62_PNG_RECEIPTS[rnum]), 2)
            for _, exp_faithful in by_num[rnum].run_specs:
                self.assertEqual(exp_faithful, 1)

    def test_06_normalize_54plus_pillar_fault_id_resolves_short_and_full_ids(self) -> None:
        self.assertIsNone(_normalize_54plus_pillar_fault_id(None))
        self.assertIsNone(_normalize_54plus_pillar_fault_id(""))
        for pnum in range(45, 55):
            full_id = RECOVERY_54_PILLAR_IDS[pnum - 1]
            self.assertEqual(_normalize_54plus_pillar_fault_id(f"pillar_{pnum}"), full_id)
            self.assertEqual(_normalize_54plus_pillar_fault_id(full_id), full_id)

    def test_07_dynamic_safety_evaluator_discovery_prefers_highest_134plus(self) -> None:
        real_n, real_fn = _discover_highest_safety_gate_evaluator()
        self.assertGreaterEqual(real_n, 134)
        self.assertTrue(callable(real_fn))

        class _FakeSafetyMod:
            @staticmethod
            def evaluate_134gate_preflight():
                return "134"

            @staticmethod
            def evaluate_136gate_preflight():
                return "136"

        best_n, best_fn = _discover_highest_safety_gate_evaluator(_FakeSafetyMod)
        self.assertEqual(best_n, 136)
        self.assertEqual(best_fn(), "136")

    def test_08_dynamic_recovery_master_discovery_prefers_highest_54plus(self) -> None:
        real_m, real_fn, real_ids = _discover_highest_recovery_master()
        self.assertGreaterEqual(real_m, 54)
        self.assertTrue(callable(real_fn))
        self.assertGreaterEqual(len(real_ids), 54)

        class _FakeRecoveryMod:
            MASTER_54_PILLAR_IDS = tuple(f"p_{i}" for i in range(1, 55))
            MASTER_55_PILLAR_IDS = tuple(f"p_{i}" for i in range(1, 56))

            @staticmethod
            def evaluate_realhw_54pillar_recovery_master():
                return 54

            @staticmethod
            def evaluate_realhw_55pillar_recovery_master():
                return 55

        best_m, best_fn, best_ids = _discover_highest_recovery_master(_FakeRecoveryMod)
        self.assertEqual(best_m, 55)
        self.assertEqual(best_fn(), 55)
        self.assertEqual(len(best_ids), 55)

    # --- 2. End-to-End Dual-Mode Reports, Determinism & Markdown ---

    def test_09_default_mode_report_all_6_pillars_ready(self) -> None:
        rep = self.rep_default
        self.assertTrue(rep.all_pillars_milestone_ready, rep.errors)
        self.assertEqual(rep.status, STATUS_MILESTONE_READY)
        self.assertEqual(rep.passed_pillar_count, 6)
        self.assertEqual(rep.failed_pillar_ids, ())
        v = verify_realhw_milestone311_master_gate(rep)
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
        self.assertEqual(rep.otp_fuse_touches, 0)
        self.assertEqual(rep.rpmb_counter_increments, 0)
        self.assertEqual(rep.passive_tx_bytes_emitted, 0)
        self.assertEqual(rep.p307_wireless_rf_packets_emitted, 0)
        self.assertEqual(rep.p307_slot1_data_sector_writes, 0)
        self.assertTrue(verify_realhw_milestone311_master_gate(rep.to_dict()).valid)

    def test_11_fx3_clean_room_test_env_var_compatibility(self) -> None:
        with mock.patch.dict(os.environ, {"FX3_CLEAN_ROOM_TEST": "1"}, clear=False):
            rep = evaluate_milestone_311_master_gate(_raw_bundle_override=self._unpack_clean_raw())
            self.assertTrue(rep.all_pillars_milestone_ready, rep.errors)
            self.assertEqual(rep.passed_pillar_count, 6)
            self.assertTrue(verify_realhw_milestone311_master_gate(rep).valid)

    def test_12_forward_compatible_lower_bounds_on_clean_report(self) -> None:
        rep = self.rep_clean
        self.assertGreaterEqual(rep.gate134_total_gates, 134)
        self.assertGreaterEqual(rep.gate134_offline_verified, 131)
        self.assertEqual(rep.gate134_offline_verified, rep.gate134_total_gates - 3)
        self.assertGreaterEqual(rep.gate134_simulated_verified, 134)
        self.assertEqual(rep.gate134_simulated_verified, rep.gate134_total_gates)
        self.assertTrue(rep.gate134_all_verified)
        self.assertGreaterEqual(rep.recovery_pillar_count, 54)
        self.assertEqual(rep.recovery_pillars_passed, rep.recovery_pillar_count)
        self.assertGreaterEqual(rep.auditors_passed, 45)
        self.assertEqual(rep.auditors_passed, rep.auditors_total)
        self.assertGreaterEqual(rep.vm_stages_passed, 62)
        self.assertEqual(rep.vm_stages_passed, rep.vm_stages_total)
        self.assertGreaterEqual(rep.qemu_rounds_verified, 35)
        self.assertGreaterEqual(rep.qemu_runs_verified, 105)
        self.assertGreaterEqual(rep.qemu_png_receipts_verified, 70)
        self.assertLess(rep.qemu_png_max_bytes, PNG_MAX_SIZE_50KIB_BYTES)
        self.assertEqual(rep.h0_equals_h3_count, 16)
        self.assertEqual(rep.e_nd_actuator_tx_count, 0)
        self.assertEqual(rep.emmc_write_count, 0)

    def test_13_deterministic_json_and_sha256_recomputation(self) -> None:
        j1 = self.rep_clean.to_deterministic_json()
        parsed = json.loads(j1)
        self.assertEqual(compute_milestone311_sha256(parsed), self.rep_clean.milestone311_sha256)
        rep2 = evaluate_milestone_311_master_gate(
            force_clean_room=True,
            _raw_bundle_override=self._unpack_clean_raw(),
        )
        self.assertEqual(rep2.milestone311_sha256, self.rep_clean.milestone311_sha256)

    def test_14_no_raw_bytes_repr_in_serialized_reports(self) -> None:
        for rep in (self.rep_default, self.rep_clean):
            self.assertIsNone(re.search(_RAW_BYTES_REPR_REGEX, rep.to_deterministic_json()))

    def test_15_markdown_renderer_contains_bilingual_headers_and_12_preflights(self) -> None:
        md = render_milestone311_markdown(self.rep_clean)
        for token in (
            "Grand Milestone Phase 311",
            "realhw_milestone311_master_gate_v1",
            "MILESTONE_311_PREBENCH_MASTER_VERIFIED",
            "cross_model_flash_authorized = False",
            "134+-Gate Preflight",
            "54+-Pillar Recovery Master",
            "62+ Stage VM HIL",
            "Ph186=",
            "Ph291=",
            "Ph302=",
            "Ph307=",
            "Rounds 28..62+",
            "| `P1` |",
            "| `P6` |",
        ):
            self.assertIn(token, md)

    # --- 3. Pillar 1: >= 134 Safety Gates (`evaluate_134gate_preflight`) ---

    def test_16_pillar1_134gate_happy_path_and_g63_to_g134_valid(self) -> None:
        raw_off, raw_sim = self._unpack_clean_raw()[:2]
        p1 = _evaluate_pillar_1(raw_off, raw_sim)
        self.assertTrue(p1.passed, p1.errors)
        self.assertGreaterEqual(p1.evidence["offline_verified_gates"], 131)
        self.assertGreaterEqual(p1.evidence["simulated_verified_gates"], 134)
        self.assertTrue(p1.evidence["all_134plus_gates_verified"])
        self.assertFalse(p1.evidence["cross_model_flash_authorized"])
        for idx in range(63, 135):
            self.assertTrue(p1.evidence["g63_to_gn_valid"][f"g{idx}"], f"g{idx}")

    def test_17_pillar1_forward_compatible_with_136_gates(self) -> None:
        raw_off, raw_sim = self._unpack_clean_raw()[:2]
        raw_off["total_gates"] = 136
        raw_off["verified_gates"] = 133
        raw_off["offline_minus3_verified"] = True
        raw_sim["total_gates"] = 136
        raw_sim["verified_gates"] = 136
        raw_sim["all_n_gates_verified"] = True
        raw_sim["nested_g_valid"]["g135"] = True
        raw_sim["nested_g_valid"]["g136"] = True
        p1 = _evaluate_pillar_1(raw_off, raw_sim)
        self.assertTrue(p1.passed, p1.errors)
        self.assertGreaterEqual(p1.evidence["simulated_verified_gates"], 136)

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

    def test_22_pillar1_fails_when_any_g103_to_g134_wave_gate_invalid(self) -> None:
        for gtag in ("g103", "g114", "g123", "g124", "g125", "g128", "g131", "g133", "g134"):
            raw_off, raw_sim = self._unpack_clean_raw()[:2]
            raw_sim["nested_g_valid"][gtag] = False
            p1 = _evaluate_pillar_1(raw_off, raw_sim)
            self.assertFalse(p1.passed, gtag)
            self.assertIn(gtag.upper(), p1.errors[-1])

    def test_23_pillar1_live_worker_g133_g134_and_persistent_write_fault(self) -> None:
        raw_sim_bad = copy.deepcopy(self.bad_sim_g134)
        raw_off = self._unpack_clean_raw()[0]
        p1 = _evaluate_pillar_1(raw_off, raw_sim_bad)
        self.assertFalse(p1.passed)
        self.assertFalse(raw_sim_bad["nested_g_valid"]["g133"])
        self.assertFalse(raw_sim_bad["nested_g_valid"]["g134"])

    def test_24_fault_to_134gate_worker_dict_propagates_wave53_to_57_and_m295(self) -> None:
        f = RealHwMilestone311FaultInjection(
            p1_steadyshot_selftimer_kwargs={"movie_self_timer_requested": True},
            p1_zebra_peaking_streaming_kwargs={"rf_nvs_write_requested": True},
            m295_faults=RealHwMilestone295FaultInjection(p1_request_persistent_writes=True),
        )
        w = _fault_to_134gate_worker_dict(f)
        self.assertTrue(w["p1_request_persistent_writes"])
        self.assertEqual(
            w["p1_steadyshot_selftimer_kwargs"],
            {"movie_self_timer_requested": True},
        )
        self.assertEqual(
            w["p1_zebra_peaking_streaming_kwargs"],
            {"rf_nvs_write_requested": True},
        )

    # --- 4. Pillar 2: >= 54 Recovery Pillars (`evaluate_realhw_54pillar_recovery_master`) ---

    def test_25_pillar2_54pillar_happy_path_and_cnflasha_ro(self) -> None:
        rec_54 = self._unpack_clean_raw()[2]
        p2, meta2 = _evaluate_pillar_2(rec_54, RealHwMilestone311FaultInjection())
        self.assertTrue(p2.passed, p2.errors)
        self.assertGreaterEqual(meta2["recovery_pillar_count"], 54)
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

    def test_26_pillar2_forward_compatible_with_55_pillars(self) -> None:
        rec_54 = self._unpack_clean_raw()[2]
        rec_54["pillar_count"] = 55
        rec_54["pillars_passed"] = 55
        rec_54["status"] = "VERIFIED_55OF55_PILLAR_RECOVERY_MASTER"
        rec_54["pillars"] = list(rec_54["pillars"]) + [{"pillar_id": "pillar_55_future_vault", "passed": True}]
        p2, meta2 = _evaluate_pillar_2(rec_54, RealHwMilestone311FaultInjection())
        self.assertTrue(p2.passed, p2.errors)
        self.assertGreaterEqual(meta2["recovery_pillar_count"], 55)

    def test_27_pillar2_fails_when_cnflasha_userspace_write_unblocked(self) -> None:
        rec_54 = self._unpack_clean_raw()[2]
        p2, _ = _evaluate_pillar_2(
            rec_54,
            RealHwMilestone311FaultInjection(p2_cnflasha_write_unblocked_fault=True),
        )
        self.assertFalse(p2.passed)

    def test_28_pillar2_fails_on_otp_rpmb_passive_tx_usb_devwrite_or_leak_overrides(self) -> None:
        rec_54 = self._unpack_clean_raw()[2]
        for kw in (
            {"p2_otp_fuse_touches_override": 1},
            {"p2_rpmb_counter_increments_override": 1},
            {"p2_passive_tx_bytes_override": 4},
            {"p2_physical_usb_packets_override": 1},
            {"p2_physical_device_writes_override": 1},
            {"p2_raw_firmware_bytes_leaked_override": 8},
        ):
            p2, _ = _evaluate_pillar_2(rec_54, RealHwMilestone311FaultInjection(**kw))
            self.assertFalse(p2.passed, kw)

    def test_29_pillar2_fails_when_54a_or_54b_vault_subsuite_fails_safely(self) -> None:
        # CRITICAL: Always use setdefault(sub_key, {}) so tests stay forward-compatible if Pillar 55+ becomes active.
        for sub_key in (
            "pillar54_a_sensor_cleaning_ev_comp_vault",
            "pillar54_b_focus_mode_playback_rotate_vault",
        ):
            rec_54 = self._unpack_clean_raw()[2]
            rec_54.setdefault(sub_key, {})["passed"] = False
            self.assertFalse(
                _evaluate_pillar_2(rec_54, RealHwMilestone311FaultInjection())[0].passed,
                sub_key,
            )

    def test_30_pillar2_live_worker_fault_inject_pillar_54_fails_closed(self) -> None:
        bad_54 = copy.deepcopy(self.bad_rec_54)
        p2, _ = _evaluate_pillar_2(bad_54, RealHwMilestone311FaultInjection())
        self.assertFalse(p2.passed)

    def test_31_pillar2_fails_on_p51_to_p54_violation_counters_or_hw_flags(self) -> None:
        for vkey in (
            "dci4k_long_gop_or_8k_violations",
            "sensor_cleaning_low_battery_bypass_events",
            "sensor_cleaning_no_power_off_violations",
            "slot1_rotate_exif_mutation_bytes",
            "slot1_photo_capture_write_bytes",
            "shutter_type_auto_spoof_events",
        ):
            rec_54 = self._unpack_clean_raw()[2]
            rec_54[vkey] = 1
            self.assertFalse(
                _evaluate_pillar_2(rec_54, RealHwMilestone311FaultInjection())[0].passed,
                vkey,
            )
        for neg_flag in (
            "fx3_has_builtin_evf",
            "fx3_has_var_shutter",
            "fx3_has_builtin_end_filter",
            "fx3_has_physical_ev_reset_dial",
            "fx3_ui_exposes_lossless_raw",
            "fx6_mechanical_shutter_present",
        ):
            rec_neg = self._unpack_clean_raw()[2]
            rec_neg[neg_flag] = True
            self.assertFalse(
                _evaluate_pillar_2(rec_neg, RealHwMilestone311FaultInjection())[0].passed,
                neg_flag,
            )

    # --- 5. Pillar 3: >= 45 Firmware Auditors (`outputs/fx3-firmware-lab`) ---

    def test_32_pillar3_45plus_auditors_happy_path(self) -> None:
        auditors = self._unpack_clean_raw()[3]
        p3, meta3 = _evaluate_pillar_3(auditors, RealHwMilestone311FaultInjection())
        self.assertTrue(p3.passed, p3.errors)
        self.assertGreaterEqual(meta3["auditor_count"], 45)
        self.assertEqual(meta3["passed_count"], meta3["auditor_count"])
        self.assertEqual(meta3["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(meta3["e_nd_actuator_tx_count"], 0)
        self.assertEqual(meta3["calibration_mutation_bytes"], 0)

    def test_33_pillar3_forward_compatible_with_46_plus_auditors(self) -> None:
        auditors = self._unpack_clean_raw()[3]
        auditors["realhw_future_wave58_audit"] = {"all_checks_passed": True}
        p3, meta3 = _evaluate_pillar_3(auditors, RealHwMilestone311FaultInjection())
        self.assertTrue(p3.passed, p3.errors)
        self.assertGreaterEqual(meta3["auditor_count"], 46)
        self.assertEqual(meta3["passed_count"], meta3["auditor_count"])

    def test_34_pillar3_fails_on_auditor45_guard_fault_or_subpillar_failure(self) -> None:
        auditors = self._unpack_clean_raw()[3]
        p3_fault, _ = _evaluate_pillar_3(
            auditors,
            RealHwMilestone311FaultInjection(p3_filesettings_tcregen_reclamp_guard_fault=True),
        )
        self.assertFalse(p3_fault.passed)

        auditors2 = self._unpack_clean_raw()[3]
        auditors2["realhw_filesettings_shotmark_tcregen_and_reclamp_audit"].setdefault(
            "pillar_2_tc_regenerate_slot1_and_ext_lk", {}
        )["passed"] = False
        self.assertFalse(_evaluate_pillar_3(auditors2, RealHwMilestone311FaultInjection())[0].passed)

    def test_35_pillar3_fails_on_raw_firmware_bytes_leaked_override(self) -> None:
        auditors = self._unpack_clean_raw()[3]
        p3, _ = _evaluate_pillar_3(
            auditors,
            RealHwMilestone311FaultInjection(p3_raw_firmware_bytes_leaked_override=16),
        )
        self.assertFalse(p3.passed)

    def test_36_pillar3_fails_when_forward_compat_46th_auditor_fails(self) -> None:
        auditors = self._unpack_clean_raw()[3]
        auditors["realhw_broken_future_audit"] = {"all_checks_passed": False}
        self.assertFalse(_evaluate_pillar_3(auditors, RealHwMilestone311FaultInjection())[0].passed)

    # --- 6. Pillar 4: >= 62 VM Co-Emulation Stages (`outputs/fx3-vm`) ---

    def test_37_pillar4_62plus_stages_happy_path_and_milestone_62of62(self) -> None:
        raw_vm = self._unpack_clean_raw()[4]
        p4, meta4 = _evaluate_pillar_4(raw_vm, RealHwMilestone311FaultInjection())
        self.assertTrue(p4.passed, p4.errors)
        self.assertGreaterEqual(meta4["stage_count"], 62)
        self.assertEqual(meta4["passed_count"], meta4["stage_count"])
        self.assertEqual(meta4["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(meta4["physical_device_writes"], 0)
        self.assertEqual(meta4["emmc_corruptions"], 0)
        self.assertEqual(p4.evidence["stage62_milestone"], "62/62")
        for dkey in (
            "stage59_digest_sha256",
            "stage60_digest_sha256",
            "stage61_digest_sha256",
            "stage62_digest_sha256",
        ):
            self.assertEqual(len(str(p4.evidence[dkey])), 64, dkey)

    def test_38_pillar4_forward_compatible_with_stage63_plus(self) -> None:
        raw_vm = self._unpack_clean_raw()[4]
        raw_vm["stage63_realhw_future_wave53_hil"] = {"all_checks_passed": True}
        p4, meta4 = _evaluate_pillar_4(raw_vm, RealHwMilestone311FaultInjection())
        self.assertTrue(p4.passed, p4.errors)
        self.assertGreaterEqual(meta4["stage_count"], 63)
        self.assertEqual(meta4["passed_count"], meta4["stage_count"])

    def test_39_pillar4_fails_on_stage59_through_stage62_fault_injections(self) -> None:
        raw_vm = self._unpack_clean_raw()[4]
        for kw in (
            {"p4_stage59_raw_heif_colorspace_shutter_nr_faults": 1},
            {"p4_stage60_focus_zoom_iso_minss_flash_faults": 1},
            {"p4_stage61_dci4k_aspect_hold_camset_photo_faults": 1},
            {"p4_stage62_sensor_cleaning_ev_focus_rotate_faults": 1},
        ):
            p4, _ = _evaluate_pillar_4(raw_vm, RealHwMilestone311FaultInjection(**kw))
            self.assertFalse(p4.passed, kw)

    def test_40_pillar4_fails_on_stage51_through_stage58_cascaded_fault_injections(self) -> None:
        raw_vm = self._unpack_clean_raw()[4]
        for m295_kw in (
            {"p4_stage54_file_settings_gamma_tcub_faults": 1},
            {"p4_stage56_power_save_bklang_volume_delete_faults": 1},
            {"p4_stage58_pp_scinetone_wb_metering_faults": 1},
        ):
            f = RealHwMilestone311FaultInjection(
                m295_faults=RealHwMilestone295FaultInjection(**m295_kw)
            )
            p4, _ = _evaluate_pillar_4(raw_vm, f)
            self.assertFalse(p4.passed, m295_kw)

    def test_41_pillar4_fails_on_physical_device_writes_or_raw_leak(self) -> None:
        raw_vm = self._unpack_clean_raw()[4]
        for kw in (
            {"p4_physical_device_writes_override": 1},
            {"p4_raw_firmware_bytes_leaked_override": 4},
        ):
            p4, _ = _evaluate_pillar_4(raw_vm, RealHwMilestone311FaultInjection(**kw))
            self.assertFalse(p4.passed, kw)

    def test_42_pillar4_fails_on_stage59_to_62_milestone_or_digest_tamper(self) -> None:
        raw_vm = self._unpack_clean_raw()[4]
        raw_vm["stage62_realhw_sensor_cleaning_ev_comp_focus_mode_rotate_hil"]["milestone"] = "61/62"
        self.assertFalse(_evaluate_pillar_4(raw_vm, RealHwMilestone311FaultInjection())[0].passed)

        raw_vm2 = self._unpack_clean_raw()[4]
        raw_vm2["stage60_realhw_focus_area_zoom_lever_iso_minss_flash_hil"]["phase298_audit_digest_sha256"] = "bad"
        self.assertFalse(_evaluate_pillar_4(raw_vm2, RealHwMilestone311FaultInjection())[0].passed)

    def test_43_pillar4_fails_on_stage59_to_62_redline_counters_and_emmc_mutation(self) -> None:
        for skey, bad_counter in (
            ("stage59_realhw_raw_heif_colorspace_shuttertype_nr_drive_hil", "dormant_lossless_raw_exposed_events"),
            ("stage60_realhw_focus_area_zoom_lever_iso_minss_flash_hil", "xlr_h1_phantom_zoom_or_hold_events"),
            ("stage61_realhw_dci4k_aspect_custom_hold_camset_photo_capture_hil", "slot1_vault_photo_capture_mutation_bytes"),
            ("stage62_realhw_sensor_cleaning_ev_comp_focus_mode_rotate_hil", "slot1_vault_rotate_mutation_bytes"),
            ("stage62_realhw_sensor_cleaning_ev_comp_focus_mode_rotate_hil", "emmc_mutation_bytes"),
        ):
            raw_vm = self._unpack_clean_raw()[4]
            raw_vm[skey][bad_counter] = 1
            self.assertFalse(
                _evaluate_pillar_4(raw_vm, RealHwMilestone311FaultInjection())[0].passed,
                f"{skey}:{bad_counter}",
            )

    def test_44_pillar4_fails_when_future_stage63_fails(self) -> None:
        raw_vm = self._unpack_clean_raw()[4]
        raw_vm["stage63_broken_hil"] = {"all_checks_passed": False}
        self.assertFalse(_evaluate_pillar_4(raw_vm, RealHwMilestone311FaultInjection())[0].passed)

    def test_45_pillar4_preserves_stage47_and_50_redline_enforcement(self) -> None:
        raw_vm = self._unpack_clean_raw()[4]
        raw_vm["stage47_realhw_framing_usbpower_lun_antiflicker_hil"]["fx3_has_var_shutter"] = True
        self.assertFalse(_evaluate_pillar_4(raw_vm, RealHwMilestone311FaultInjection())[0].passed)
        raw_vm2 = self._unpack_clean_raw()[4]
        raw_vm2["stage50_realhw_diff_set_still_mv_custom_key_remain_shoot_hil"]["fx3_has_builtin_evf"] = True
        self.assertFalse(_evaluate_pillar_4(raw_vm2, RealHwMilestone311FaultInjection())[0].passed)

    # --- 7. Pillar 5: ALL 12 Bench Readiness Verifiers (`Ph186`..`Ph307`) ---

    def test_46_pillar5_dodecuple_12of12_bench_preflights_happy_path(self) -> None:
        b = self._unpack_clean_raw()
        p5, meta5 = _evaluate_pillar_5(*b[5:32], RealHwMilestone311FaultInjection())
        self.assertTrue(p5.passed, p5.errors)
        self.assertFalse(meta5["overall_ready_for_hardware_attach"])
        for tag in (
            "p186", "p204", "p216", "p227", "p248", "p261",
            "p275", "p279", "p284", "p291", "p302", "p307",
        ):
            off_k = f"{tag}_offline_go_no_go"
            sim_k = f"{tag}_sim_go_no_go"
            self.assertEqual(meta5[off_k], GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT, off_k)
            self.assertEqual(meta5[sim_k], GO_NO_GO_DRY_RUN_SIMULATED_READY, sim_k)
            self.assertEqual(meta5[f"{tag}_h0_equals_h3_count"], 16, tag)
        self.assertFalse(meta5["p186_card_insert_authorized"])
        for tag in ("p204", "p216", "p227", "p248", "p261", "p275", "p279", "p284", "p291", "p302", "p307"):
            self.assertFalse(meta5[f"{tag}_hardware_live_attachment_authorized"], tag)
        for tag in ("p302", "p307"):
            self.assertEqual(meta5[f"{tag}_sim_check_groups_passed"], 4, tag)
            self.assertEqual(meta5[f"{tag}_sim_usb_packets_transmitted"], 0, tag)
            self.assertEqual(meta5[f"{tag}_sim_passive_tx_bytes_emitted"], 0, tag)
        self.assertEqual(meta5["p307_wireless_rf_packets_emitted"], 0)
        self.assertEqual(meta5["p307_slot1_data_sector_writes"], 0)

    def test_47_pillar5_rejects_phase302_lens_af_copy_evf_faults(self) -> None:
        b = list(self._unpack_clean_raw())
        p302_off, p302_sim, _, _ = copy.deepcopy(self.p302_307_bad)
        p5, _ = _evaluate_pillar_5(
            *b[5:28], p302_off, p302_sim, b[30], b[31], RealHwMilestone311FaultInjection()
        )
        self.assertFalse(p5.passed)

    def test_48_pillar5_rejects_phase302_h0_h3_drift_fault(self) -> None:
        b = list(self._unpack_clean_raw())
        p302_off, p302_sim, _, _ = copy.deepcopy(self.p302_307_drift)
        p5, _ = _evaluate_pillar_5(
            *b[5:28], p302_off, p302_sim, b[30], b[31], RealHwMilestone311FaultInjection()
        )
        self.assertFalse(p5.passed)

    def test_49_pillar5_rejects_phase307_dial_lut_ibis_rf_slot1_faults(self) -> None:
        b = list(self._unpack_clean_raw())
        _, _, p307_off, p307_sim = copy.deepcopy(self.p302_307_bad)
        p5, _ = _evaluate_pillar_5(
            *b[5:30], p307_off, p307_sim, RealHwMilestone311FaultInjection()
        )
        self.assertFalse(p5.passed)

    def test_50_pillar5_rejects_phase307_h0_h3_drift_fault(self) -> None:
        b = list(self._unpack_clean_raw())
        _, _, p307_off, p307_sim = copy.deepcopy(self.p302_307_drift)
        p5, _ = _evaluate_pillar_5(
            *b[5:30], p307_off, p307_sim, RealHwMilestone311FaultInjection()
        )
        self.assertFalse(p5.passed)

    def test_51_pillar5_rejects_phase302_and_307_usb_passive_and_wireless_rf_overrides(self) -> None:
        b = self._unpack_clean_raw()
        for fkw in (
            {"p5_inject_p302_usb_packets_override": 1},
            {"p5_inject_p302_passive_tx_bytes_override": 4},
            {"p5_inject_p307_usb_packets_override": 1},
            {"p5_inject_p307_passive_tx_bytes_override": 4},
            {"p5_inject_p307_wireless_rf_packets_override": 1},
        ):
            p5, _ = _evaluate_pillar_5(*b[5:32], RealHwMilestone311FaultInjection(**fkw))
            self.assertFalse(p5.passed, fkw)

    def test_52_pillar5_rejects_phase307_rf_nvs_auth_or_slot1_tier0_mutated(self) -> None:
        for bad_k, bad_v in (
            ("rf_nvs_p12_p13_writes_authorized", True),
            ("slot1_tier0_vault_mutated", True),
            ("slot1_data_sector_writes", 1),
        ):
            p5_slice = list(self._unpack_clean_raw()[5:32])
            p5_slice[26][bad_k] = bad_v  # 26 == raw_p307_sim
            p5, _ = _evaluate_pillar_5(*p5_slice, RealHwMilestone311FaultInjection())
            self.assertFalse(p5.passed, bad_k)

    def test_53_pillar5_rejects_offline_if_not_blocked_awaiting_tier0(self) -> None:
        # indices inside p5_slice (b[5:32]): 21=p291_off, 23=p302_off, 25=p307_off
        for off_idx in (21, 23, 25):
            p5_slice = list(self._unpack_clean_raw()[5:32])
            p5_slice[off_idx]["go_no_go"] = GO_NO_GO_DRY_RUN_SIMULATED_READY
            p5, _ = _evaluate_pillar_5(*p5_slice, RealHwMilestone311FaultInjection())
            self.assertFalse(p5.passed, off_idx)

    def test_54_pillar5_rejects_sim_sha256_tamper_and_attach_ready_true(self) -> None:
        # indices inside p5_slice (b[5:32]): 24=p302_sim, 26=p307_sim
        for sim_idx in (24, 26):
            p5_slice = list(self._unpack_clean_raw()[5:32])
            p5_slice[sim_idx]["report_sha256"] = "0" * 64
            p5, _ = _evaluate_pillar_5(*p5_slice, RealHwMilestone311FaultInjection())
            self.assertFalse(p5.passed, sim_idx)

        p5_slice2 = list(self._unpack_clean_raw()[5:32])
        p5_slice2[26]["overall_ready_for_hardware_attach"] = True
        p5_2, _ = _evaluate_pillar_5(*p5_slice2, RealHwMilestone311FaultInjection())
        self.assertFalse(p5_2.passed)

    def test_55_pillar5_propagates_upstream_phase291_failure(self) -> None:
        b = list(self._unpack_clean_raw())
        _, _, p291_off, p291_sim = copy.deepcopy(self.p284_291_bad)
        p5, _ = _evaluate_pillar_5(
            *b[5:26], p291_off, p291_sim, *b[28:32], RealHwMilestone311FaultInjection()
        )
        self.assertFalse(p5.passed)

    # --- 8. Pillar 6: Live FX3 7.02 QEMU Rounds 28..62+ & < 50 KiB PNG Receipts ---

    def _clean_p1_to_p5_metas(self):
        cls = type(self)
        cached = getattr(cls, "_cached_p1_to_p5_metas", None)
        if cached is None:
            b = self.raw_bundle
            f = RealHwMilestone311FaultInjection()
            p1 = _evaluate_pillar_1(b[0], b[1])
            _, m2 = _evaluate_pillar_2(b[2], f)
            _, m3 = _evaluate_pillar_3(b[3], f)
            _, m4 = _evaluate_pillar_4(b[4], f)
            _, m5 = _evaluate_pillar_5(*b[5:32], f)
            cached = (p1.evidence, m2, m3, m4, m5)
            cls._cached_p1_to_p5_metas = cached
        return cached

    def test_56_pillar6_rounds_28_to_62_at_least_35_rounds_105_runs_70_pngs(self) -> None:
        m1, m2, m3, m4, m5 = self._clean_p1_to_p5_metas()
        p6, meta6 = _evaluate_pillar_6(
            repo_root=REPO_ROOT,
            use_clean_room=True,
            faults=RealHwMilestone311FaultInjection(),
            p1_meta=m1,
            p2_meta=m2,
            p3_meta=m3,
            p4_meta=m4,
            p5_meta=m5,
        )
        self.assertTrue(p6.passed, p6.errors)
        self.assertGreaterEqual(meta6["qemu_rounds_verified"], 35)
        self.assertGreaterEqual(meta6["qemu_runs_verified"], 105)
        self.assertGreaterEqual(meta6["qemu_png_receipts_verified"], 70)
        self.assertLess(meta6["qemu_png_max_bytes"], PNG_MAX_SIZE_50KIB_BYTES)
        self.assertEqual(meta6["qemu_raw_firmware_bytes_leaked"], 0)
        for rnum in range(59, 63):
            self.assertEqual(meta6["qemu_round_runs_by_round"][f"r{rnum}"], 3)

    def test_57_pillar6_committed_rounds59_to_62_png_headers_and_baseline_max_27467b(self) -> None:
        observed_max = 0
        for rnum in range(28, 63):
            for rel in ROUND28_TO_62_PNG_RECEIPTS[rnum]:
                p = REPO_ROOT / rel
                if p.is_file():
                    raw = p.read_bytes()
                    self.assertTrue(raw.startswith(PNG_MAGIC_BYTES), rel)
                    self.assertLess(len(raw), PNG_MAX_SIZE_50KIB_BYTES, rel)
                    if len(raw) > observed_max:
                        observed_max = len(raw)
        if observed_max > 0:
            self.assertLessEqual(observed_max, P311_BASELINE_PNG_MAX_OBSERVED_BYTES)

    def test_58_pillar6_forward_compatible_with_round63_directory_discovery(self) -> None:
        m1, m2, m3, m4, m5 = self._clean_p1_to_p5_metas()
        with tempfile.TemporaryDirectory() as tmp:
            tmp_root = Path(tmp)
            r63_dir = tmp_root / "reports" / "2026-11-18-round63-realhw-future-wave58-qemu"
            assets_dir = r63_dir / "assets"
            assets_dir.mkdir(parents=True, exist_ok=True)
            for name in ("r63a-alpha.png", "r63a-composited.png"):
                (assets_dir / name).write_bytes(PNG_MAGIC_BYTES + b"\x00" * 128)
            summary = {
                "schema": "fx6-on-fx3-round63-realhw-future-wave58-qemu-v1",
                "round": 63,
                "kernel_version": "Linux version 4.9.337-scel+ (clean-room-synthetic)",
                "raw_firmware_bytes_leaked": 0,
                "runs": {
                    "r63a_run": {"nop_count": 0, "crashes": 0, "emmc_write_count": 0, "stage_b": {"manifest_count": 13}},
                    "r63b_run": {"nop_count": 0, "crashes": 0, "emmc_write_count": 0, "stage_b": {"manifest_count": 13}},
                    "r63c_run": {"nop_count": 0, "crashes": 0, "emmc_write_count": 0, "stage_b": {"manifest_count": 13}},
                },
                "r63_realhw_future_wave58_audit": {
                    "all_3_runs_crashes_zero": True,
                    "all_3_runs_emmc_write_zero": True,
                    "fx3_has_builtin_evf": False,
                    "fx3_has_var_shutter": False,
                },
            }
            (r63_dir / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
            p6, meta6 = _evaluate_pillar_6(
                repo_root=tmp_root,
                use_clean_room=True,
                faults=RealHwMilestone311FaultInjection(),
                p1_meta=m1,
                p2_meta=m2,
                p3_meta=m3,
                p4_meta=m4,
                p5_meta=m5,
            )
            self.assertTrue(p6.passed, p6.errors)
            self.assertGreaterEqual(meta6["qemu_rounds_verified"], 36)
            self.assertGreaterEqual(meta6["qemu_runs_verified"], 108)
            self.assertGreaterEqual(meta6["qemu_png_receipts_verified"], 72)

    def test_59_pillar6_forward_compatible_round63_rejects_bad_audit_flag_or_kernel(self) -> None:
        m1, m2, m3, m4, m5 = self._clean_p1_to_p5_metas()
        with tempfile.TemporaryDirectory() as tmp:
            tmp_root = Path(tmp)
            r63_dir = tmp_root / "reports" / "2026-11-18-round63-realhw-broken-qemu"
            r63_dir.mkdir(parents=True, exist_ok=True)
            summary = {
                "schema": "fx6-on-fx3-round63-broken-v1",
                "round": 63,
                "kernel_version": "Linux version 4.9.337-scel+ (clean-room-synthetic)",
                "raw_firmware_bytes_leaked": 0,
                "runs": {
                    "r63a_run": {"nop_count": 0, "crashes": 0, "emmc_write_count": 0, "stage_b": {"manifest_count": 13}},
                },
                "r63_broken_audit": {
                    "all_3_runs_crashes_zero": True,
                    "fx3_has_builtin_evf": True,
                },
            }
            (r63_dir / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
            p6, _ = _evaluate_pillar_6(
                repo_root=tmp_root,
                use_clean_room=True,
                faults=RealHwMilestone311FaultInjection(),
                p1_meta=m1,
                p2_meta=m2,
                p3_meta=m3,
                p4_meta=m4,
                p5_meta=m5,
            )
            self.assertFalse(p6.passed)

    def test_60_pillar6_fails_on_rounds59_to_62_schema_tamper(self) -> None:
        m1, m2, m3, m4, m5 = self._clean_p1_to_p5_metas()
        for rnum in range(59, 63):
            p6, _ = _evaluate_pillar_6(
                repo_root=REPO_ROOT,
                use_clean_room=True,
                faults=RealHwMilestone311FaultInjection(p6_tamper_schema_round_num=rnum),
                p1_meta=m1,
                p2_meta=m2,
                p3_meta=m3,
                p4_meta=m4,
                p5_meta=m5,
            )
            self.assertFalse(p6.passed, rnum)

    def test_61_pillar6_fails_on_round62_nop_crash_emmc_write_or_raw_leak(self) -> None:
        m1, m2, m3, m4, m5 = self._clean_p1_to_p5_metas()
        for fkw in (
            {"p6_round_nop_override_num": 62, "p6_round_nop_count_override": 1},
            {"p6_round_crash_override_num": 62, "p6_round_crashes_override": 1},
            {"p6_round_emmc_override_num": 62, "p6_round_emmc_writes_override": 1},
            {"p6_raw_firmware_bytes_leaked_override": 8},
        ):
            p6, _ = _evaluate_pillar_6(
                repo_root=REPO_ROOT,
                use_clean_room=True,
                faults=RealHwMilestone311FaultInjection(**fkw),
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
            faults=RealHwMilestone311FaultInjection(
                p6_png_size_override_round_num=62,
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
                faults=RealHwMilestone311FaultInjection(),
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
                faults=RealHwMilestone311FaultInjection(),
                p1_meta=m1,
                p2_meta=m2_bad,
                p3_meta=m3,
                p4_meta=m4,
                p5_meta=m5,
            )[0].passed
        )

    def test_64_pillar6_cross_pillar_p302_and_p307_h0_h3_rf_slot1_fail_closed(self) -> None:
        m1, m2, m3, m4, m5 = self._clean_p1_to_p5_metas()
        for bad_k, bad_v in (
            ("p302_h0_equals_h3_count", 15),
            ("p302_hardware_live_attachment_authorized", True),
            ("p302_sim_passive_tx_bytes_emitted", 1),
            ("p307_h0_equals_h3_count", 15),
            ("p307_hardware_live_attachment_authorized", True),
            ("p307_wireless_rf_packets_emitted", 1),
            ("p307_slot1_data_sector_writes", 1),
        ):
            m5_bad = dict(m5)
            m5_bad[bad_k] = bad_v
            p6_bad, _ = _evaluate_pillar_6(
                repo_root=REPO_ROOT,
                use_clean_room=True,
                faults=RealHwMilestone311FaultInjection(),
                p1_meta=m1,
                p2_meta=m2,
                p3_meta=m3,
                p4_meta=m4,
                p5_meta=m5_bad,
            )
            self.assertFalse(p6_bad.passed, bad_k)

    # --- 9. Fail-Closed Verifier, CLI & Cross-Platform Subprocess ---

    def test_65_verifier_rejects_non_mapping_payload(self) -> None:
        self.assertFalse(verify_realhw_milestone311_master_gate("not-a-dict").valid)
        self.assertFalse(verify_realhw_milestone311_master_gate(123).valid)
        self.assertFalse(verify_realhw_milestone311_master_gate(None).valid)  # type: ignore[arg-type]

    def test_66_verifier_rejects_sha256_tamper_and_schema_tamper(self) -> None:
        d = self.rep_clean.to_dict()
        d["milestone311_sha256"] = "f" * 64
        self.assertFalse(verify_realhw_milestone311_master_gate(d).valid)

        d2 = self.rep_clean.to_dict()
        d2["schema"] = "wrong_schema_v1"
        d2["milestone311_sha256"] = compute_milestone311_sha256(d2)
        self.assertFalse(verify_realhw_milestone311_master_gate(d2).valid)

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
            ("otp_fuse_touches", 1),
            ("rpmb_counter_increments", 1),
            ("passive_tx_bytes_emitted", 1),
            ("p302_hardware_live_attachment_authorized", True),
            ("p307_hardware_live_attachment_authorized", True),
            ("p307_wireless_rf_packets_emitted", 1),
            ("p307_slot1_data_sector_writes", 1),
        ):
            d = self.rep_clean.to_dict()
            d[k] = v
            d["milestone311_sha256"] = compute_milestone311_sha256(d)
            self.assertFalse(verify_realhw_milestone311_master_gate(d).valid, k)

    def test_68_verifier_accepts_forward_compatible_higher_counts(self) -> None:
        d = self.rep_clean.to_dict()
        d["gate134_total_gates"] = 136
        d["gate134_offline_verified"] = 133
        d["gate134_simulated_verified"] = 136
        d["recovery_pillar_count"] = 55
        d["recovery_pillars_passed"] = 55
        d["auditors_total"] = 46
        d["auditors_passed"] = 46
        d["vm_stages_total"] = 63
        d["vm_stages_passed"] = 63
        d["qemu_rounds_total"] = 36
        d["qemu_rounds_verified"] = 36
        d["qemu_runs_total"] = 108
        d["qemu_runs_verified"] = 108
        d["qemu_png_receipts_total"] = 72
        d["qemu_png_receipts_verified"] = 72
        d["milestone311_sha256"] = compute_milestone311_sha256(d)
        v = verify_realhw_milestone311_master_gate(d)
        self.assertTrue(v.valid, v.errors)

    def test_69_verifier_rejects_sub_threshold_counts_and_raw_bytes(self) -> None:
        for k, v in (
            ("gate134_simulated_verified", 133),
            ("recovery_pillar_count", 53),
            ("auditors_passed", 44),
            ("vm_stages_passed", 61),
            ("p302_sim_check_groups_passed", 3),
            ("p307_sim_check_groups_passed", 3),
            ("qemu_rounds_verified", 34),
            ("qemu_runs_verified", 104),
            ("qemu_png_receipts_verified", 69),
            ("qemu_png_max_bytes", PNG_MAX_SIZE_50KIB_BYTES),
        ):
            d = self.rep_clean.to_dict()
            d[k] = v
            d["milestone311_sha256"] = compute_milestone311_sha256(d)
            self.assertFalse(verify_realhw_milestone311_master_gate(d).valid, k)

        d_raw = self.rep_clean.to_dict()
        d_raw["pillars"][0]["summary"] = "leaked b'\\x7fELF'"
        d_raw["milestone311_sha256"] = compute_milestone311_sha256(d_raw)
        self.assertFalse(verify_realhw_milestone311_master_gate(d_raw).valid)

    def test_70_cli_verify_milestone_311_summary_and_out_alias_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            out_json = tmp_path / "m311.json"
            out_md = tmp_path / "m311.md"
            buf = io.StringIO()
            with (
                mock.patch(
                    "fx6_closure.realhw_milestone311_master_gate.evaluate_realhw_milestone311_master_gate",
                    return_value=self.rep_clean,
                ),
                mock.patch("sys.stdout", buf),
            ):
                rc = fx6_cli_main(
                    [
                        "verify-milestone-311",
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
            self.assertIn("schema=realhw_milestone311_master_gate_v1", text)
            self.assertIn("cnflasha_ro=True", text)
            self.assertIn("cross_model_flash_auth=False", text)
            self.assertIn(
                "p302=BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT/DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH",
                text,
            )
            self.assertIn(
                "p307=BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT/DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH",
                text,
            )
            self.assertIn("rf_pkts=0", text)
            self.assertIn("ready_attach=False", text)
            self.assertIsNotNone(re.search(r"gate134=(\d+)/(\d+)", text))
            self.assertIsNotNone(re.search(r"qemu=(\d+)/(\d+)\((\d+)/(\d+)\)", text))
            self.assertTrue(out_json.is_file())
            self.assertTrue(out_md.is_file())
            self.assertTrue(
                verify_realhw_milestone311_master_gate(json.loads(out_json.read_text())).valid
            )

    def test_71_cli_verify_milestone_311_json_stdout_and_failure_exit_code(self) -> None:
        buf = io.StringIO()
        with (
            mock.patch(
                "fx6_closure.realhw_milestone311_master_gate.evaluate_realhw_milestone311_master_gate",
                return_value=self.rep_clean,
            ),
            mock.patch("sys.stdout", buf),
        ):
            rc = fx6_cli_main(["verify-milestone-311", "--clean-room", "--json"])
        self.assertEqual(rc, 0)
        parsed = json.loads(buf.getvalue())
        self.assertEqual(parsed["schema"], REALHW_MILESTONE311_SCHEMA)
        self.assertEqual(parsed["usb_packets_transmitted"], 0)
        self.assertFalse(parsed["overall_ready_for_hardware_attach"])
        self.assertFalse(parsed["cross_model_flash_authorized"])

        bad_rep = replace(
            self.rep_clean,
            all_pillars_milestone_ready=False,
            status=STATUS_FAIL_CLOSED,
            passed_pillar_count=5,
            failed_pillar_ids=("P1",),
            milestone311_sha256="0" * 64,
        )
        buf2 = io.StringIO()
        with (
            mock.patch(
                "fx6_closure.realhw_milestone311_master_gate.evaluate_realhw_milestone311_master_gate",
                return_value=bad_rep,
            ),
            mock.patch("sys.stdout", buf2),
        ):
            rc2 = fx6_cli_main(["verify-milestone-311", "--force-clean-room"])
        self.assertEqual(rc2, 1)
        self.assertIn("status=FAILED", buf2.getvalue())

    def test_72_cli_verify_milestone_311_simulate_bench_dry_run_flag(self) -> None:
        captured: dict = {}

        def _fake_eval(**kwargs):
            captured.update(kwargs)
            return self.rep_clean

        buf = io.StringIO()
        with (
            mock.patch(
                "fx6_closure.realhw_milestone311_master_gate.evaluate_realhw_milestone311_master_gate",
                side_effect=_fake_eval,
            ),
            mock.patch("sys.stdout", buf),
        ):
            rc = fx6_cli_main(
                ["verify-milestone-311", "--force-clean-room", "--simulate-bench-dry-run", "--json"]
            )
        self.assertEqual(rc, 0)
        self.assertTrue(captured.get("simulate_bench_dry_run"))
        self.assertTrue(captured.get("force_clean_room"))

    def test_73_verify_milestone_311_cli_direct_helper_entrypoint(self) -> None:
        buf = io.StringIO()
        with (
            mock.patch(
                "fx6_closure.realhw_milestone311_master_gate.evaluate_realhw_milestone311_master_gate",
                return_value=self.rep_clean,
            ),
            mock.patch("sys.stdout", buf),
        ):
            rc = verify_milestone_311_cli(["--clean-room", "--simulate-bench-dry-run", "--json"])
        self.assertEqual(rc, 0)
        parsed = json.loads(buf.getvalue())
        self.assertEqual(parsed["schema"], REALHW_MILESTONE311_SCHEMA)
        self.assertTrue(parsed["cnflasha_userspace_write_blocked"])

    def test_74_argparse_help_formatting_safe_for_python_314_and_macos(self) -> None:
        buf_top = io.StringIO()
        with mock.patch("sys.stdout", buf_top):
            with self.assertRaises(SystemExit) as ctx_top:
                fx6_cli_main(["--help"])
        self.assertEqual(ctx_top.exception.code, 0)
        self.assertIn("verify-milestone-311", buf_top.getvalue())

        buf_sub = io.StringIO()
        with mock.patch("sys.stdout", buf_sub):
            with self.assertRaises(SystemExit) as ctx_sub:
                fx6_cli_main(["verify-milestone-311", "--help"])
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
                "verify-milestone-311",
                "--force-clean-room",
                "--simulate-bench-dry-run",
                "--json",
            ],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        elapsed = time.monotonic() - t0
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["schema"], REALHW_MILESTONE311_SCHEMA)
        self.assertTrue(payload["all_pillars_milestone_ready"])
        self.assertGreaterEqual(payload["gate134_simulated_verified"], 134)
        self.assertGreaterEqual(payload["recovery_pillars_passed"], 54)
        self.assertGreaterEqual(payload["auditors_passed"], 45)
        self.assertGreaterEqual(payload["vm_stages_passed"], 62)
        self.assertGreaterEqual(payload["qemu_rounds_verified"], 35)
        self.assertGreaterEqual(payload["qemu_runs_verified"], 105)
        self.assertGreaterEqual(payload["qemu_png_receipts_verified"], 70)
        self.assertLess(elapsed, _ci_time_budget(15.0))

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
                "verify-milestone-311",
                "--json",
            ],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        elapsed = time.monotonic() - t0
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["schema"], REALHW_MILESTONE311_SCHEMA)
        self.assertTrue(payload["all_pillars_milestone_ready"])
        self.assertGreaterEqual(payload["gate134_simulated_verified"], 134)
        self.assertGreaterEqual(payload["recovery_pillars_passed"], 54)
        self.assertLess(elapsed, _ci_time_budget(15.0))

    def test_77_synthetic_clean_room_kwarg_alias_and_suite_runtime_budget(self) -> None:
        rep = evaluate_milestone_311_master_gate(
            synthetic_clean_room=True,
            _raw_bundle_override=self._unpack_clean_raw(),
        )
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(rep.all_pillars_milestone_ready)
        self.assertLess(self.default_elapsed_s, _ci_time_budget(15.0))

    def test_78_preserves_milestone_295_264_254_entrypoints_and_non_overlapping_exports(self) -> None:
        self.assertTrue(hasattr(fx6_closure, "evaluate_realhw_milestone295_master_gate"))
        self.assertTrue(hasattr(fx6_closure, "evaluate_realhw_milestone264_master_gate"))
        self.assertTrue(hasattr(fx6_closure, "evaluate_realhw_milestone254_master_gate"))
        self.assertNotEqual(fx6_closure.REALHW_MILESTONE295_SCHEMA, fx6_closure.REALHW_MILESTONE311_SCHEMA)
        self.assertEqual(
            fx6_closure.evaluate_realhw_milestone311_master_gate,
            evaluate_realhw_milestone311_master_gate,
        )


if __name__ == "__main__":
    unittest.main()
