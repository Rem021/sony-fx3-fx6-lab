"""Phase 295 dual-mode unit tests for Grand Milestone Phase 295 6-Pillar Real-Hardware Master Gate."""

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
from fx6_closure.realhw_milestone264_master_gate import (  # noqa: E402
    RealHwMilestone264FaultInjection,
    _worker_phase261,
)
from fx6_closure.realhw_milestone295_master_gate import (  # noqa: E402
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
    MILESTONE295_SCHEMA_VERSION,
    OTP_FUSE_TOUCHES,
    OTP_FUSE_WRITES,
    OVERALL_READY_FOR_HARDWARE_ATTACH,
    P295_PHYSICAL_DEVICE_WRITES,
    P295_PILLAR_IDS,
    P295_PILLAR_SPECS,
    P295_PNG_MAX_SIZE_BYTES,
    P295_RAW_FIRMWARE_BYTES_LEAKED,
    P295_SCHEMA,
    P295_STATUS_FAIL_CLOSED,
    P295_STATUS_MILESTONE_READY,
    P295_VERSION,
    P8_CP_MUTATION_FORBIDDEN,
    PASSIVE_TX_BYTES,
    PASSIVE_TX_BYTES_EMITTED,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHASE_295_VERSION,
    PHYSICAL_DEVICE_WRITES,
    PHYSICAL_USB_PACKETS_EMITTED,
    PILLAR_IDS,
    PILLAR_SPECS,
    PNG_MAGIC_BYTES,
    PNG_MAX_SIZE_50KIB_BYTES,
    PNG_MAX_SIZE_BYTES,
    RAW_FIRMWARE_BYTES_LEAKED,
    REALHW_MILESTONE295_SCHEMA,
    RECOVERY_50_PILLAR_IDS,
    ROUND28_TO_58_PNG_RECEIPTS,
    ROUND28_TO_58_SPECS,
    ROUND53_EXPECTED_SCHEMA,
    ROUND54_EXPECTED_SCHEMA,
    ROUND55_EXPECTED_SCHEMA,
    ROUND56_EXPECTED_SCHEMA,
    ROUND57_EXPECTED_SCHEMA,
    ROUND58_EXPECTED_SCHEMA,
    RPMB_COUNTER_INCREMENTS,
    RPMB_WRITES,
    SPI_NOR_WRITE_AUTHORIZED,
    STATUS_FAIL_CLOSED,
    STATUS_MILESTONE_READY,
    USB_OR_CAMERA_OPERATIONS,
    USB_PACKETS_TRANSMITTED,
    VM_COEMULATION_58_STAGE_KEYS,
    WBI_MUTATION_BYTES,
    WBI_P5_WRITE_AND_HIBERNATION_FORBIDDEN,
    RealHwMilestone295FaultInjection,
    RealHwMilestone295MasterGateReport,
    _collect_parallel_milestone295_results,
    _discover_highest_recovery_master,
    _discover_highest_safety_gate_evaluator,
    _evaluate_pillar_1,
    _evaluate_pillar_2,
    _evaluate_pillar_3,
    _evaluate_pillar_4,
    _evaluate_pillar_5,
    _evaluate_pillar_6,
    _fault_to_124gate_worker_dict,
    _normalize_50plus_pillar_fault_id,
    _worker_124plus_gate_single,
    _worker_phase275_279,
    _worker_phase284_291,
    _worker_recovery_50plus_pillar,
    build_realhw_milestone295_master_gate_report,
    compute_milestone295_sha256,
    evaluate_milestone295_master_gate,
    evaluate_milestone_295_master_gate,
    evaluate_realhw_milestone295_master_gate,
    render_milestone295_markdown,
    verify_milestone_295_cli,
    verify_milestone_295_master_gate,
    verify_realhw_milestone295_master_gate,
)

_RAW_BYTES_REPR_REGEX = r"(?<![0-9A-Za-z_/.-])b['\"]"


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

    g124_fdict = _fault_to_124gate_worker_dict(
        RealHwMilestone295FaultInjection(
            p1_sensor_cleaning_ev_comp_kwargs={"claimed_cine_ei_allows_ev_comp": True},
            p1_focus_mode_playback_rotate_kwargs={"rotate_requested": True, "playback_media_slot": 1},
            p1_request_persistent_writes=True,
        )
    )
    fx6_s = str(DEFAULT_FX6_DONOR_LIB_DIR)
    fx3_s = str(DEFAULT_FX3_MODULES_DIR)
    ctx = mp.get_context("fork")
    with ProcessPoolExecutor(max_workers=4, mp_context=ctx) as pool:
        fut_g124 = pool.submit(_worker_124plus_gate_single, (str(REPO_ROOT), True, True, g124_fdict))
        fut_p50 = pool.submit(_worker_recovery_50plus_pillar, (True, "pillar_50"))
        fut_275_279_fault = pool.submit(
            _worker_phase275_279,
            (
                fx6_s,
                fx3_s,
                True,
                {"file_gamma_focusmag_vault": True},
                {"usb_hdmi_protect_nw": True},
            ),
        )
        fut_275_279_drift = pool.submit(
            _worker_phase275_279,
            (fx6_s, fx3_s, True, {"h0_h3_drift": True}, {"h0_h3_drift": True}),
        )
        fut_284_291_fault = pool.submit(
            _worker_phase284_291,
            (
                fx6_s,
                fx3_s,
                True,
                {"pp_wb_raw_shutter": True},
                {"focus_zoom_dci4k_clean": True},
            ),
        )
        fut_284_291_drift = pool.submit(
            _worker_phase284_291,
            (fx6_s, fx3_s, True, {"h0_h3_drift": True}, {"h0_h3_drift": True}),
        )
        fut_261_bad = pool.submit(
            _worker_phase261,
            (fx6_s, fx3_s, True, {"diffset_customkey_vault": True}),
        )
        bad_g124 = fut_g124.result()
        bad_p50 = fut_p50.result()
        p275_279_bad = fut_275_279_fault.result()
        p275_279_drift = fut_275_279_drift.result()
        p284_291_bad = fut_284_291_fault.result()
        p284_291_drift = fut_284_291_drift.result()
        p261_bad = fut_261_bad.result()
    conn.send(
        (
            bad_g124,
            bad_p50,
            p275_279_bad,
            p275_279_drift,
            p284_291_bad,
            p284_291_drift,
            p261_bad,
        )
    )
    conn.close()


class TestRealHwMilestone295MasterGate(unittest.TestCase):
    """Comprehensive 76 dual-mode tests for Grand Milestone Phase 295."""

    raw_bundle: tuple
    rep_default: RealHwMilestone295MasterGateReport
    rep_clean: RealHwMilestone295MasterGateReport
    bad_sim_g124: dict
    bad_rec_50: dict
    p275_279_bad: tuple
    p275_279_drift: tuple
    p284_291_bad: tuple
    p284_291_drift: tuple
    p261_bad: tuple
    default_elapsed_s: float

    @classmethod
    def setUpClass(cls) -> None:
        import multiprocessing as mp

        t0 = time.monotonic()
        ctx = mp.get_context("fork")
        if not _is_forced_clean_room():
            cls.rep_default = evaluate_milestone_295_master_gate()
        recv_conn, send_conn = ctx.Pipe(duplex=False)
        proc = ctx.Process(
            target=_fork_child_fault_fixtures_only,
            args=(send_conn,),
            daemon=False,
        )
        proc.start()
        send_conn.close()
        try:
            cls.raw_bundle = _collect_parallel_milestone295_results(
                repo_root=REPO_ROOT,
                fx6_lib_dir=DEFAULT_FX6_DONOR_LIB_DIR,
                fx3_modules_dir=DEFAULT_FX3_MODULES_DIR,
                use_clean_room=True,
                faults=RealHwMilestone295FaultInjection(),
            )
            (
                cls.bad_sim_g124,
                cls.bad_rec_50,
                cls.p275_279_bad,
                cls.p275_279_drift,
                cls.p284_291_bad,
                cls.p284_291_drift,
                cls.p261_bad,
            ) = recv_conn.recv()
        finally:
            recv_conn.close()
            proc.join(timeout=30)
        cls.rep_clean = evaluate_milestone_295_master_gate(
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
        self.assertEqual(REALHW_MILESTONE295_SCHEMA, "realhw_milestone295_master_gate_v1")
        self.assertEqual(MILESTONE295_SCHEMA_VERSION, REALHW_MILESTONE295_SCHEMA)
        self.assertEqual(P295_SCHEMA, REALHW_MILESTONE295_SCHEMA)
        self.assertEqual(PHASE_295_VERSION, "295.0.0")
        self.assertEqual(P295_VERSION, "295.0.0")
        self.assertEqual(PILLAR_IDS, ("P1", "P2", "P3", "P4", "P5", "P6"))
        self.assertEqual(P295_PILLAR_IDS, PILLAR_IDS)
        self.assertEqual(len(PILLAR_SPECS), 6)
        self.assertEqual(P295_PILLAR_SPECS, PILLAR_SPECS)
        self.assertGreaterEqual(len(RECOVERY_50_PILLAR_IDS), 50)
        self.assertGreaterEqual(len(FIRMWARE_LAB_45_AUDITOR_KEYS), 45)
        self.assertGreaterEqual(len(VM_COEMULATION_58_STAGE_KEYS), 58)
        self.assertGreaterEqual(len(ROUND28_TO_58_SPECS), 31)
        self.assertEqual(PNG_MAX_SIZE_50KIB_BYTES, 51200)
        self.assertEqual(PNG_MAX_SIZE_BYTES, 51200)
        self.assertEqual(P295_PNG_MAX_SIZE_BYTES, 51200)

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
        self.assertEqual(P295_STATUS_MILESTONE_READY, STATUS_MILESTONE_READY)
        self.assertEqual(P295_STATUS_FAIL_CLOSED, STATUS_FAIL_CLOSED)
        for zero_const in (
            USB_PACKETS_TRANSMITTED,
            PHYSICAL_USB_PACKETS_EMITTED,
            PHYSICAL_DEVICE_WRITES,
            P295_PHYSICAL_DEVICE_WRITES,
            RAW_FIRMWARE_BYTES_LEAKED,
            P295_RAW_FIRMWARE_BYTES_LEAKED,
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
            "CROSS_MODEL_FLASH_AUTHORIZED",
            "P295_CROSS_MODEL_FLASH_AUTHORIZED",
            "MILESTONE295_PHYSICAL_DEVICE_WRITES",
            "MILESTONE295_PILLAR_IDS",
            "MILESTONE295_PILLAR_SPECS",
            "MILESTONE295_PNG_MAX_SIZE_BYTES",
            "MILESTONE295_RAW_FIRMWARE_BYTES_LEAKED",
            "MILESTONE295_SCHEMA_VERSION",
            "P295_PHYSICAL_DEVICE_WRITES",
            "P295_PILLAR_IDS",
            "P295_PILLAR_SPECS",
            "P295_PNG_MAX_SIZE_BYTES",
            "P295_RAW_FIRMWARE_BYTES_LEAKED",
            "P295_SCHEMA",
            "P295_STATUS_FAIL_CLOSED",
            "P295_STATUS_MILESTONE_READY",
            "P295_VERSION",
            "PHASE_295_VERSION",
            "REALHW_MILESTONE295_SCHEMA",
            "RECOVERY_50_PILLAR_IDS",
            "ROUND28_TO_58_PNG_RECEIPTS",
            "ROUND28_TO_58_SPECS",
            "ROUND53_EXPECTED_SCHEMA",
            "ROUND54_EXPECTED_SCHEMA",
            "ROUND55_EXPECTED_SCHEMA",
            "ROUND56_EXPECTED_SCHEMA",
            "ROUND57_EXPECTED_SCHEMA",
            "ROUND58_EXPECTED_SCHEMA",
            "STATUS_MILESTONE295_FAIL_CLOSED",
            "STATUS_MILESTONE295_READY",
            "VM_COEMULATION_58_STAGE_KEYS",
            "Milestone295PillarResult",
            "RealHwMilestone295FaultInjection",
            "RealHwMilestone295MasterGateReport",
            "RealHwMilestone295VerifyResult",
            "build_realhw_milestone295_master_gate_report",
            "compute_milestone295_sha256",
            "evaluate_milestone295_master_gate",
            "evaluate_milestone_295_master_gate",
            "evaluate_realhw_milestone295_master_gate",
            "render_milestone295_markdown",
            "verify_milestone_295_cli",
            "verify_milestone_295_master_gate",
            "verify_realhw_milestone295_master_gate",
        }
        self.assertTrue(expected.issubset(set(fx6_closure.__all__)))
        for sym in expected:
            self.assertTrue(hasattr(fx6_closure, sym), sym)
        self.assertEqual(fx6_closure.REALHW_MILESTONE264_SCHEMA, "realhw_milestone264_master_gate_v1")
        self.assertEqual(fx6_closure.REALHW_MILESTONE254_SCHEMA, "realhw_milestone254_master_gate_v1")
        self.assertEqual(fx6_closure.REALHW_MILESTONE233_SCHEMA, "realhw_milestone233_master_gate_v1")

    def test_04_builder_and_verifier_aliases_point_to_canonical_functions(self) -> None:
        self.assertIs(build_realhw_milestone295_master_gate_report, evaluate_realhw_milestone295_master_gate)
        self.assertIs(evaluate_milestone_295_master_gate, evaluate_realhw_milestone295_master_gate)
        self.assertIs(evaluate_milestone295_master_gate, evaluate_realhw_milestone295_master_gate)
        self.assertIs(verify_milestone_295_master_gate, verify_realhw_milestone295_master_gate)

    def test_05_rounds53_to_58_specs_and_png_pairs_registered(self) -> None:
        by_num = {s.round_num: s for s in ROUND28_TO_58_SPECS}
        for rnum, exp_schema in (
            (53, ROUND53_EXPECTED_SCHEMA),
            (54, ROUND54_EXPECTED_SCHEMA),
            (55, ROUND55_EXPECTED_SCHEMA),
            (56, ROUND56_EXPECTED_SCHEMA),
            (57, ROUND57_EXPECTED_SCHEMA),
            (58, ROUND58_EXPECTED_SCHEMA),
        ):
            self.assertIn(rnum, by_num)
            self.assertEqual(by_num[rnum].expected_schema, exp_schema)
            self.assertEqual(len(by_num[rnum].run_specs), 3)
            self.assertIn(rnum, ROUND28_TO_58_PNG_RECEIPTS)
            self.assertEqual(len(ROUND28_TO_58_PNG_RECEIPTS[rnum]), 2)
            for _, exp_faithful in by_num[rnum].run_specs:
                self.assertEqual(exp_faithful, 1)

    def test_06_normalize_50plus_pillar_fault_id_resolves_short_and_full_ids(self) -> None:
        self.assertIsNone(_normalize_50plus_pillar_fault_id(None))
        self.assertIsNone(_normalize_50plus_pillar_fault_id(""))
        for pnum in range(45, 51):
            full_id = RECOVERY_50_PILLAR_IDS[pnum - 1]
            self.assertEqual(_normalize_50plus_pillar_fault_id(f"pillar_{pnum}"), full_id)
            self.assertEqual(_normalize_50plus_pillar_fault_id(full_id), full_id)

    def test_07_dynamic_safety_evaluator_discovery_prefers_highest_124plus(self) -> None:
        real_n, real_fn = _discover_highest_safety_gate_evaluator()
        self.assertGreaterEqual(real_n, 124)
        self.assertTrue(callable(real_fn))

        class _FakeSafetyMod:
            @staticmethod
            def evaluate_124gate_preflight():
                return "124"

            @staticmethod
            def evaluate_126gate_preflight():
                return "126"

        best_n, best_fn = _discover_highest_safety_gate_evaluator(_FakeSafetyMod)
        self.assertEqual(best_n, 126)
        self.assertEqual(best_fn(), "126")

    def test_08_dynamic_recovery_master_discovery_prefers_highest_50plus(self) -> None:
        real_m, real_fn, real_ids = _discover_highest_recovery_master()
        self.assertGreaterEqual(real_m, 50)
        self.assertTrue(callable(real_fn))
        self.assertGreaterEqual(len(real_ids), 50)

        class _FakeRecoveryMod:
            MASTER_50_PILLAR_IDS = tuple(f"p_{i}" for i in range(1, 51))
            MASTER_51_PILLAR_IDS = tuple(f"p_{i}" for i in range(1, 52))

            @staticmethod
            def evaluate_realhw_50pillar_recovery_master():
                return 50

            @staticmethod
            def evaluate_realhw_51pillar_recovery_master():
                return 51

        best_m, best_fn, best_ids = _discover_highest_recovery_master(_FakeRecoveryMod)
        self.assertEqual(best_m, 51)
        self.assertEqual(best_fn(), 51)
        self.assertEqual(len(best_ids), 51)

    # --- 2. End-to-End Dual-Mode Reports, Determinism & Markdown ---

    def test_09_default_mode_report_all_6_pillars_ready(self) -> None:
        rep = self.rep_default
        self.assertTrue(rep.all_pillars_milestone_ready, rep.errors)
        self.assertEqual(rep.status, STATUS_MILESTONE_READY)
        self.assertEqual(rep.passed_pillar_count, 6)
        self.assertEqual(rep.failed_pillar_ids, ())
        v = verify_realhw_milestone295_master_gate(rep)
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
        self.assertTrue(verify_realhw_milestone295_master_gate(rep.to_dict()).valid)

    def test_11_forward_compatible_lower_bounds_on_clean_report(self) -> None:
        rep = self.rep_clean
        self.assertGreaterEqual(rep.gate124_total_gates, 124)
        self.assertGreaterEqual(rep.gate124_offline_verified, 121)
        self.assertEqual(rep.gate124_offline_verified, rep.gate124_total_gates - 3)
        self.assertGreaterEqual(rep.gate124_simulated_verified, 124)
        self.assertEqual(rep.gate124_simulated_verified, rep.gate124_total_gates)
        self.assertTrue(rep.gate124_all_verified)
        self.assertGreaterEqual(rep.recovery_pillar_count, 50)
        self.assertEqual(rep.recovery_pillars_passed, rep.recovery_pillar_count)
        self.assertGreaterEqual(rep.auditors_passed, 45)
        self.assertEqual(rep.auditors_passed, rep.auditors_total)
        self.assertGreaterEqual(rep.vm_stages_passed, 58)
        self.assertEqual(rep.vm_stages_passed, rep.vm_stages_total)
        self.assertGreaterEqual(rep.qemu_rounds_verified, 31)
        self.assertGreaterEqual(rep.qemu_runs_verified, 93)
        self.assertGreaterEqual(rep.qemu_png_receipts_verified, 62)
        self.assertLess(rep.qemu_png_max_bytes, PNG_MAX_SIZE_50KIB_BYTES)
        self.assertEqual(rep.h0_equals_h3_count, 16)
        self.assertEqual(rep.e_nd_actuator_tx_count, 0)
        self.assertEqual(rep.emmc_write_count, 0)

    def test_12_deterministic_json_and_sha256_recomputation(self) -> None:
        j1 = self.rep_clean.to_deterministic_json()
        parsed = json.loads(j1)
        self.assertEqual(compute_milestone295_sha256(parsed), self.rep_clean.milestone295_sha256)
        rep2 = evaluate_milestone_295_master_gate(
            force_clean_room=True,
            _raw_bundle_override=self._unpack_clean_raw(),
        )
        self.assertEqual(rep2.milestone295_sha256, self.rep_clean.milestone295_sha256)

    def test_13_no_raw_bytes_repr_in_serialized_reports(self) -> None:
        for rep in (self.rep_default, self.rep_clean):
            self.assertIsNone(re.search(_RAW_BYTES_REPR_REGEX, rep.to_deterministic_json()))

    def test_14_markdown_renderer_contains_bilingual_headers_and_10_preflights(self) -> None:
        md = render_milestone295_markdown(self.rep_clean)
        for token in (
            "Grand Milestone Phase 295",
            "realhw_milestone295_master_gate_v1",
            "MILESTONE_295_PREBENCH_MASTER_VERIFIED",
            "cross_model_flash_authorized = False",
            "124+-Gate Preflight",
            "50+-Pillar Recovery Master",
            "58+ Stage VM HIL",
            "Ph275=",
            "Ph279=",
            "Ph284=",
            "Ph291=",
            "Rounds 28..58+",
            "| `P1` |",
            "| `P6` |",
        ):
            self.assertIn(token, md)

    # --- 3. Pillar 1: >= 124 Safety Gates (`evaluate_124gate_preflight`) ---

    def test_15_pillar1_124gate_happy_path_and_g63_to_g124_valid(self) -> None:
        raw_off, raw_sim = self._unpack_clean_raw()[:2]
        p1 = _evaluate_pillar_1(raw_off, raw_sim)
        self.assertTrue(p1.passed, p1.errors)
        self.assertGreaterEqual(p1.evidence["offline_verified_gates"], 121)
        self.assertGreaterEqual(p1.evidence["simulated_verified_gates"], 124)
        self.assertTrue(p1.evidence["all_124plus_gates_verified"])
        self.assertFalse(p1.evidence["cross_model_flash_authorized"])
        for idx in range(63, 125):
            self.assertTrue(p1.evidence["g63_to_gn_valid"][f"g{idx}"], f"g{idx}")

    def test_16_pillar1_forward_compatible_with_126_gates(self) -> None:
        raw_off, raw_sim = self._unpack_clean_raw()[:2]
        raw_off["total_gates"] = 126
        raw_off["verified_gates"] = 123
        raw_off["offline_minus3_verified"] = True
        raw_sim["total_gates"] = 126
        raw_sim["verified_gates"] = 126
        raw_sim["all_n_gates_verified"] = True
        raw_sim["nested_g_valid"]["g125"] = True
        raw_sim["nested_g_valid"]["g126"] = True
        p1 = _evaluate_pillar_1(raw_off, raw_sim)
        self.assertTrue(p1.passed, p1.errors)
        self.assertGreaterEqual(p1.evidence["simulated_verified_gates"], 126)

    def test_17_pillar1_fails_when_offline_tier0_gates_not_blocked(self) -> None:
        raw_off, raw_sim = self._unpack_clean_raw()[:2]
        raw_off["verified_gates"] = raw_off["total_gates"]
        raw_off["blocked_or_pending_gates"] = 0
        self.assertFalse(_evaluate_pillar_1(raw_off, raw_sim).passed)

    def test_18_pillar1_fails_when_all_n_gates_verified_false_in_dry_run(self) -> None:
        raw_off, raw_sim = self._unpack_clean_raw()[:2]
        raw_sim["all_n_gates_verified"] = False
        self.assertFalse(_evaluate_pillar_1(raw_off, raw_sim).passed)

    def test_19_pillar1_fails_when_hardware_attach_cross_model_or_write_unlocked(self) -> None:
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

    def test_20_pillar1_fails_when_usb_packets_or_leak_or_end_tx_nonzero(self) -> None:
        for field in (
            "usb_packets_transmitted",
            "raw_firmware_bytes_leaked",
            "g71_e_nd_actuator_tx_count",
        ):
            raw_off, raw_sim = self._unpack_clean_raw()[:2]
            raw_sim[field] = 1
            self.assertFalse(_evaluate_pillar_1(raw_off, raw_sim).passed, field)

    def test_21_pillar1_fails_when_any_g103_to_g124_wave_gate_invalid(self) -> None:
        for gtag in ("g103", "g108", "g114", "g119", "g123", "g124"):
            raw_off, raw_sim = self._unpack_clean_raw()[:2]
            raw_sim["nested_g_valid"][gtag] = False
            p1 = _evaluate_pillar_1(raw_off, raw_sim)
            self.assertFalse(p1.passed, gtag)
            self.assertIn(gtag.upper(), p1.errors[-1])

    def test_22_pillar1_live_worker_g123_g124_and_persistent_write_fault(self) -> None:
        raw_sim_bad = copy.deepcopy(self.bad_sim_g124)
        raw_off = self._unpack_clean_raw()[0]
        p1 = _evaluate_pillar_1(raw_off, raw_sim_bad)
        self.assertFalse(p1.passed)
        self.assertFalse(raw_sim_bad["nested_g_valid"]["g123"])
        self.assertFalse(raw_sim_bad["nested_g_valid"]["g124"])

    def test_23_fault_to_124gate_worker_dict_propagates_wave42_to_52_and_m264(self) -> None:
        f = RealHwMilestone295FaultInjection(
            p1_sensor_cleaning_ev_comp_kwargs={"claimed_cine_ei_allows_ev_comp": True},
            p1_focus_mode_playback_rotate_kwargs={"rotate_requested": True},
            m264_faults=RealHwMilestone264FaultInjection(p1_request_persistent_writes=True),
        )
        w = _fault_to_124gate_worker_dict(f)
        self.assertTrue(w["p1_request_persistent_writes"])
        self.assertEqual(
            w["p1_sensor_cleaning_ev_comp_kwargs"],
            {"claimed_cine_ei_allows_ev_comp": True},
        )
        self.assertEqual(
            w["p1_focus_mode_playback_rotate_kwargs"],
            {"rotate_requested": True},
        )

    # --- 4. Pillar 2: >= 50 Recovery Pillars (`evaluate_realhw_50pillar_recovery_master`) ---

    def test_24_pillar2_50pillar_happy_path_and_cnflasha_ro(self) -> None:
        rec_50 = self._unpack_clean_raw()[2]
        p2, meta2 = _evaluate_pillar_2(rec_50, RealHwMilestone295FaultInjection())
        self.assertTrue(p2.passed, p2.errors)
        self.assertGreaterEqual(meta2["recovery_pillar_count"], 50)
        self.assertEqual(meta2["recovery_pillars_passed"], meta2["recovery_pillar_count"])
        self.assertTrue(meta2["cnflasha_userspace_write_blocked"])
        self.assertFalse(p2.evidence["fx3_has_builtin_evf"])
        self.assertFalse(p2.evidence["fx3_has_builtin_end_filter"])
        self.assertEqual(meta2["otp_fuse_writes"], 0)
        self.assertEqual(meta2["rpmb_writes"], 0)
        self.assertEqual(meta2["passive_tx_bytes"], 0)
        self.assertEqual(meta2["physical_usb_packets_emitted"], 0)
        self.assertEqual(meta2["physical_device_writes"], 0)
        self.assertEqual(meta2["raw_firmware_bytes_leaked"], 0)

    def test_25_pillar2_forward_compatible_with_51_pillars(self) -> None:
        rec_50 = self._unpack_clean_raw()[2]
        rec_50["pillar_count"] = 51
        rec_50["pillars_passed"] = 51
        rec_50["status"] = "VERIFIED_51OF51_PILLAR_RECOVERY_MASTER"
        rec_50["pillars"] = list(rec_50["pillars"]) + [{"pillar_id": "pillar_51_future_vault", "passed": True}]
        p2, meta2 = _evaluate_pillar_2(rec_50, RealHwMilestone295FaultInjection())
        self.assertTrue(p2.passed, p2.errors)
        self.assertGreaterEqual(meta2["recovery_pillar_count"], 51)

    def test_26_pillar2_fails_when_cnflasha_userspace_write_unblocked(self) -> None:
        rec_50 = self._unpack_clean_raw()[2]
        p2, _ = _evaluate_pillar_2(
            rec_50,
            RealHwMilestone295FaultInjection(p2_cnflasha_write_unblocked_fault=True),
        )
        self.assertFalse(p2.passed)

    def test_27_pillar2_fails_on_otp_rpmb_passive_tx_usb_devwrite_or_leak_overrides(self) -> None:
        rec_50 = self._unpack_clean_raw()[2]
        for kw in (
            {"p2_otp_fuse_touches_override": 1},
            {"p2_rpmb_counter_increments_override": 1},
            {"p2_passive_tx_bytes_override": 4},
            {"p2_physical_usb_packets_override": 1},
            {"p2_physical_device_writes_override": 1},
            {"p2_raw_firmware_bytes_leaked_override": 8},
        ):
            p2, _ = _evaluate_pillar_2(rec_50, RealHwMilestone295FaultInjection(**kw))
            self.assertFalse(p2.passed, kw)

    def test_28_pillar2_fails_when_50a_or_50b_vault_subsuite_fails(self) -> None:
        for sub_key in (
            "pillar50_a_pp_scinetone_creativelook_dro_vault",
            "pillar50_b_wb_camset_exclusion_metering_vault",
        ):
            rec_50 = self._unpack_clean_raw()[2]
            rec_50[sub_key]["passed"] = False
            self.assertFalse(
                _evaluate_pillar_2(rec_50, RealHwMilestone295FaultInjection())[0].passed,
                sub_key,
            )

    def test_29_pillar2_live_worker_fault_inject_pillar_50_fails_closed(self) -> None:
        bad_50 = copy.deepcopy(self.bad_rec_50)
        p2, _ = _evaluate_pillar_2(bad_50, RealHwMilestone295FaultInjection())
        self.assertFalse(p2.passed)

    def test_30_pillar2_fails_on_p45_to_p50_violation_counters_or_hw_flags(self) -> None:
        for vkey in (
            "double_log_or_lockout_bypass_events",
            "wb_custom_camset_exclusion_drift_events",
            "nouvc_spoof_events",
            "slot1_vault_format_or_delete_events",
            "slot1_copyright_vault_mutation_bytes",
        ):
            rec_50 = self._unpack_clean_raw()[2]
            rec_50[vkey] = 1
            self.assertFalse(
                _evaluate_pillar_2(rec_50, RealHwMilestone295FaultInjection())[0].passed,
                vkey,
            )
        for neg_flag in ("fx3_has_builtin_evf", "fx3_has_var_shutter", "fx3_has_builtin_end_filter"):
            rec_neg = self._unpack_clean_raw()[2]
            rec_neg[neg_flag] = True
            self.assertFalse(
                _evaluate_pillar_2(rec_neg, RealHwMilestone295FaultInjection())[0].passed,
                neg_flag,
            )

    # --- 5. Pillar 3: >= 45 Firmware Auditors (`outputs/fx3-firmware-lab`) ---

    def test_31_pillar3_45plus_auditors_happy_path(self) -> None:
        auditors = self._unpack_clean_raw()[3]
        p3, meta3 = _evaluate_pillar_3(auditors, RealHwMilestone295FaultInjection())
        self.assertTrue(p3.passed, p3.errors)
        self.assertGreaterEqual(meta3["auditor_count"], 45)
        self.assertEqual(meta3["passed_count"], meta3["auditor_count"])
        self.assertEqual(meta3["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(meta3["e_nd_actuator_tx_count"], 0)
        self.assertEqual(meta3["calibration_mutation_bytes"], 0)

    def test_32_pillar3_forward_compatible_with_46_plus_auditors(self) -> None:
        auditors = self._unpack_clean_raw()[3]
        auditors["realhw_future_wave53_audit"] = {"all_checks_passed": True}
        p3, meta3 = _evaluate_pillar_3(auditors, RealHwMilestone295FaultInjection())
        self.assertTrue(p3.passed, p3.errors)
        self.assertGreaterEqual(meta3["auditor_count"], 46)
        self.assertEqual(meta3["passed_count"], meta3["auditor_count"])

    def test_33_pillar3_fails_on_auditor45_guard_fault_or_subpillar_failure(self) -> None:
        auditors = self._unpack_clean_raw()[3]
        p3_fault, _ = _evaluate_pillar_3(
            auditors,
            RealHwMilestone295FaultInjection(p3_filesettings_tcregen_reclamp_guard_fault=True),
        )
        self.assertFalse(p3_fault.passed)

        auditors2 = self._unpack_clean_raw()[3]
        auditors2["realhw_filesettings_shotmark_tcregen_and_reclamp_audit"][
            "pillar_2_tc_regenerate_slot1_and_ext_lk"
        ]["passed"] = False
        self.assertFalse(_evaluate_pillar_3(auditors2, RealHwMilestone295FaultInjection())[0].passed)

    def test_34_pillar3_fails_on_raw_firmware_bytes_leaked_override(self) -> None:
        auditors = self._unpack_clean_raw()[3]
        p3, _ = _evaluate_pillar_3(
            auditors,
            RealHwMilestone295FaultInjection(p3_raw_firmware_bytes_leaked_override=16),
        )
        self.assertFalse(p3.passed)

    def test_35_pillar3_fails_when_forward_compat_46th_auditor_fails(self) -> None:
        auditors = self._unpack_clean_raw()[3]
        auditors["realhw_broken_future_audit"] = {"all_checks_passed": False}
        self.assertFalse(_evaluate_pillar_3(auditors, RealHwMilestone295FaultInjection())[0].passed)

    # --- 6. Pillar 4: >= 58 VM Co-Emulation Stages (`outputs/fx3-vm`) ---

    def test_36_pillar4_58plus_stages_happy_path_and_milestone_58of58(self) -> None:
        raw_vm = self._unpack_clean_raw()[4]
        p4, meta4 = _evaluate_pillar_4(raw_vm, RealHwMilestone295FaultInjection())
        self.assertTrue(p4.passed, p4.errors)
        self.assertGreaterEqual(meta4["stage_count"], 58)
        self.assertEqual(meta4["passed_count"], meta4["stage_count"])
        self.assertEqual(meta4["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(meta4["physical_device_writes"], 0)
        self.assertEqual(meta4["emmc_corruptions"], 0)
        self.assertEqual(p4.evidence["stage58_milestone"], "58/58")
        for dkey in (
            "stage55_digest_sha256",
            "stage56_digest_sha256",
            "stage57_digest_sha256",
            "stage58_digest_sha256",
        ):
            self.assertEqual(len(str(p4.evidence[dkey])), 64, dkey)

    def test_37_pillar4_forward_compatible_with_stage59_plus(self) -> None:
        raw_vm = self._unpack_clean_raw()[4]
        raw_vm["stage59_realhw_future_wave53_hil"] = {"all_checks_passed": True}
        p4, meta4 = _evaluate_pillar_4(raw_vm, RealHwMilestone295FaultInjection())
        self.assertTrue(p4.passed, p4.errors)
        self.assertGreaterEqual(meta4["stage_count"], 59)
        self.assertEqual(meta4["passed_count"], meta4["stage_count"])

    def test_38_pillar4_fails_on_stage51_through_stage58_fault_injections(self) -> None:
        raw_vm = self._unpack_clean_raw()[4]
        for kw in (
            {"p4_stage51_autoslow_hdmi_breathing_faults": 1},
            {"p4_stage52_apsc_face_eye_version_faults": 1},
            {"p4_stage53_release_audio_copyright_faults": 1},
            {"p4_stage54_file_settings_gamma_tcub_faults": 1},
            {"p4_stage55_focus_mag_videolight_hdmires_faults": 1},
            {"p4_stage56_power_save_bklang_volume_delete_faults": 1},
            {"p4_stage57_usb_mode_hdmi_protect_nw_reset_faults": 1},
            {"p4_stage58_pp_scinetone_wb_metering_faults": 1},
        ):
            p4, _ = _evaluate_pillar_4(raw_vm, RealHwMilestone295FaultInjection(**kw))
            self.assertFalse(p4.passed, kw)

    def test_39_pillar4_fails_on_physical_device_writes_or_raw_leak(self) -> None:
        raw_vm = self._unpack_clean_raw()[4]
        for kw in (
            {"p4_physical_device_writes_override": 1},
            {"p4_raw_firmware_bytes_leaked_override": 4},
        ):
            p4, _ = _evaluate_pillar_4(raw_vm, RealHwMilestone295FaultInjection(**kw))
            self.assertFalse(p4.passed, kw)

    def test_40_pillar4_fails_on_stage58_milestone_tamper_or_emmc_mutation(self) -> None:
        raw_vm = self._unpack_clean_raw()[4]
        raw_vm["stage58_realhw_pp_scinetone_creativelook_wb_metering_hil"]["milestone"] = "57/58"
        self.assertFalse(_evaluate_pillar_4(raw_vm, RealHwMilestone295FaultInjection())[0].passed)

        raw_vm2 = self._unpack_clean_raw()[4]
        raw_vm2["stage58_realhw_pp_scinetone_creativelook_wb_metering_hil"]["emmc_mutation_bytes"] = 4
        self.assertFalse(_evaluate_pillar_4(raw_vm2, RealHwMilestone295FaultInjection())[0].passed)

    def test_41_pillar4_fails_on_stage54_to_57_redline_tamper(self) -> None:
        for skey, bad_counter in (
            ("stage54_realhw_file_settings_gamma_assist_tcub_hil", "slot1_vault_folder_mutation_events"),
            ("stage55_realhw_focus_mag_datetime_videolight_hdmires_hil", "mishoe_5v_900ma_overcurrent_events"),
            ("stage56_realhw_power_save_monitor_language_volume_delete_hil", "slot1_vault_delete_events"),
            ("stage57_realhw_usb_mode_hdmi_info_protect_network_reset_hil", "fx3_native_uvc_spoof_events"),
        ):
            raw_vm = self._unpack_clean_raw()[4]
            raw_vm[skey][bad_counter] = 1
            self.assertFalse(
                _evaluate_pillar_4(raw_vm, RealHwMilestone295FaultInjection())[0].passed,
                skey,
            )

    def test_42_pillar4_fails_when_future_stage59_fails(self) -> None:
        raw_vm = self._unpack_clean_raw()[4]
        raw_vm["stage59_broken_hil"] = {"all_checks_passed": False}
        self.assertFalse(_evaluate_pillar_4(raw_vm, RealHwMilestone295FaultInjection())[0].passed)

    def test_43_pillar4_preserves_stage47_and_50_redline_enforcement(self) -> None:
        raw_vm = self._unpack_clean_raw()[4]
        raw_vm["stage47_realhw_framing_usbpower_lun_antiflicker_hil"]["fx3_has_var_shutter"] = True
        self.assertFalse(_evaluate_pillar_4(raw_vm, RealHwMilestone295FaultInjection())[0].passed)
        raw_vm2 = self._unpack_clean_raw()[4]
        raw_vm2["stage50_realhw_diff_set_still_mv_custom_key_remain_shoot_hil"]["fx3_has_builtin_evf"] = True
        self.assertFalse(_evaluate_pillar_4(raw_vm2, RealHwMilestone295FaultInjection())[0].passed)

    # --- 7. Pillar 5: ALL 10 Bench Readiness Verifiers (`Ph186`..`Ph291`) ---

    def test_44_pillar5_decuple_10of10_bench_preflights_happy_path(self) -> None:
        b = self._unpack_clean_raw()
        p5, meta5 = _evaluate_pillar_5(*b[5:28], RealHwMilestone295FaultInjection())
        self.assertTrue(p5.passed, p5.errors)
        self.assertFalse(meta5["overall_ready_for_hardware_attach"])
        for tag in ("p186", "p204", "p216", "p227", "p248", "p261", "p275", "p279", "p284", "p291"):
            off_k = f"{tag}_offline_go_no_go"
            sim_k = f"{tag}_sim_go_no_go"
            self.assertEqual(meta5[off_k], GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT, off_k)
            self.assertEqual(meta5[sim_k], GO_NO_GO_DRY_RUN_SIMULATED_READY, sim_k)
            self.assertEqual(meta5[f"{tag}_h0_equals_h3_count"], 16, tag)
        self.assertFalse(meta5["p186_card_insert_authorized"])
        for tag in ("p204", "p216", "p227", "p248", "p261", "p275", "p279", "p284", "p291"):
            self.assertFalse(meta5[f"{tag}_hardware_live_attachment_authorized"], tag)
        for tag in ("p275", "p279", "p284", "p291"):
            self.assertEqual(meta5[f"{tag}_sim_check_groups_passed"], 4, tag)
            self.assertEqual(meta5[f"{tag}_sim_usb_packets_transmitted"], 0, tag)
            self.assertEqual(meta5[f"{tag}_sim_passive_tx_bytes_emitted"], 0, tag)

    def test_45_pillar5_rejects_phase275_vault_gamma_focusmag_faults(self) -> None:
        b = list(self._unpack_clean_raw())
        p275_off, p275_sim, _, _ = copy.deepcopy(self.p275_279_bad)
        p5, _ = _evaluate_pillar_5(
            *b[5:20], p275_off, p275_sim, *b[22:28], RealHwMilestone295FaultInjection()
        )
        self.assertFalse(p5.passed)

    def test_46_pillar5_rejects_phase275_h0_h3_drift_fault(self) -> None:
        b = list(self._unpack_clean_raw())
        p275_off, p275_sim, _, _ = copy.deepcopy(self.p275_279_drift)
        p5, _ = _evaluate_pillar_5(
            *b[5:20], p275_off, p275_sim, *b[22:28], RealHwMilestone295FaultInjection()
        )
        self.assertFalse(p5.passed)

    def test_47_pillar5_rejects_phase279_usb_hdmi_protect_nw_faults(self) -> None:
        b = list(self._unpack_clean_raw())
        _, _, p279_off, p279_sim = copy.deepcopy(self.p275_279_bad)
        p5, _ = _evaluate_pillar_5(
            *b[5:22], p279_off, p279_sim, *b[24:28], RealHwMilestone295FaultInjection()
        )
        self.assertFalse(p5.passed)

    def test_48_pillar5_rejects_phase279_h0_h3_drift_fault(self) -> None:
        b = list(self._unpack_clean_raw())
        _, _, p279_off, p279_sim = copy.deepcopy(self.p275_279_drift)
        p5, _ = _evaluate_pillar_5(
            *b[5:22], p279_off, p279_sim, *b[24:28], RealHwMilestone295FaultInjection()
        )
        self.assertFalse(p5.passed)

    def test_49_pillar5_rejects_phase284_pp_wb_raw_shutter_faults(self) -> None:
        b = list(self._unpack_clean_raw())
        p284_off, p284_sim, _, _ = copy.deepcopy(self.p284_291_bad)
        p5, _ = _evaluate_pillar_5(
            *b[5:24], p284_off, p284_sim, b[26], b[27], RealHwMilestone295FaultInjection()
        )
        self.assertFalse(p5.passed)

    def test_50_pillar5_rejects_phase284_h0_h3_drift_fault(self) -> None:
        b = list(self._unpack_clean_raw())
        p284_off, p284_sim, _, _ = copy.deepcopy(self.p284_291_drift)
        p5, _ = _evaluate_pillar_5(
            *b[5:24], p284_off, p284_sim, b[26], b[27], RealHwMilestone295FaultInjection()
        )
        self.assertFalse(p5.passed)

    def test_51_pillar5_rejects_phase291_focus_zoom_dci4k_clean_faults(self) -> None:
        b = list(self._unpack_clean_raw())
        _, _, p291_off, p291_sim = copy.deepcopy(self.p284_291_bad)
        p5, _ = _evaluate_pillar_5(
            *b[5:26], p291_off, p291_sim, RealHwMilestone295FaultInjection()
        )
        self.assertFalse(p5.passed)

    def test_52_pillar5_rejects_phase291_h0_h3_drift_fault(self) -> None:
        b = list(self._unpack_clean_raw())
        _, _, p291_off, p291_sim = copy.deepcopy(self.p284_291_drift)
        p5, _ = _evaluate_pillar_5(
            *b[5:26], p291_off, p291_sim, RealHwMilestone295FaultInjection()
        )
        self.assertFalse(p5.passed)

    def test_53_pillar5_rejects_phase291_usb_and_passive_tx_overrides(self) -> None:
        b = self._unpack_clean_raw()
        for fkw in (
            {"p5_inject_p291_usb_packets_override": 1},
            {"p5_inject_p291_passive_tx_bytes_override": 4},
        ):
            p5, _ = _evaluate_pillar_5(*b[5:28], RealHwMilestone295FaultInjection(**fkw))
            self.assertFalse(p5.passed, fkw)

    def test_54_pillar5_rejects_offline_if_not_blocked_awaiting_tier0(self) -> None:
        # indices inside p5_slice (b[5:28]): 15=p275_off, 17=p279_off, 19=p284_off, 21=p291_off
        for off_idx in (15, 17, 19, 21):
            p5_slice = list(self._unpack_clean_raw()[5:28])
            p5_slice[off_idx]["go_no_go"] = GO_NO_GO_DRY_RUN_SIMULATED_READY
            p5, _ = _evaluate_pillar_5(*p5_slice, RealHwMilestone295FaultInjection())
            self.assertFalse(p5.passed, off_idx)

    def test_55_pillar5_rejects_sim_sha256_tamper_and_attach_ready_true(self) -> None:
        # indices inside p5_slice (b[5:28]): 16=p275_sim, 18=p279_sim, 20=p284_sim, 22=p291_sim
        for sim_idx in (16, 18, 20, 22):
            p5_slice = list(self._unpack_clean_raw()[5:28])
            p5_slice[sim_idx]["report_sha256"] = "0" * 64
            p5, _ = _evaluate_pillar_5(*p5_slice, RealHwMilestone295FaultInjection())
            self.assertFalse(p5.passed, sim_idx)

        p5_slice2 = list(self._unpack_clean_raw()[5:28])
        p5_slice2[22]["overall_ready_for_hardware_attach"] = True
        p5_2, _ = _evaluate_pillar_5(*p5_slice2, RealHwMilestone295FaultInjection())
        self.assertFalse(p5_2.passed)

    def test_56_pillar5_propagates_upstream_phase261_failure(self) -> None:
        b = list(self._unpack_clean_raw())
        p261_off, p261_sim = copy.deepcopy(self.p261_bad)
        p5, _ = _evaluate_pillar_5(
            *b[5:18], p261_off, p261_sim, *b[20:28], RealHwMilestone295FaultInjection()
        )
        self.assertFalse(p5.passed)

    # --- 8. Pillar 6: Live FX3 7.02 QEMU Rounds 28..58+ & < 50 KiB PNG Receipts ---

    def _clean_p1_to_p5_metas(self):
        cls = type(self)
        cached = getattr(cls, "_cached_p1_to_p5_metas", None)
        if cached is None:
            b = self.raw_bundle
            f = RealHwMilestone295FaultInjection()
            p1 = _evaluate_pillar_1(b[0], b[1])
            _, m2 = _evaluate_pillar_2(b[2], f)
            _, m3 = _evaluate_pillar_3(b[3], f)
            _, m4 = _evaluate_pillar_4(b[4], f)
            _, m5 = _evaluate_pillar_5(*b[5:28], f)
            cached = (p1.evidence, m2, m3, m4, m5)
            cls._cached_p1_to_p5_metas = cached
        return cached

    def test_57_pillar6_rounds_28_to_58_at_least_31_rounds_93_runs_62_pngs(self) -> None:
        m1, m2, m3, m4, m5 = self._clean_p1_to_p5_metas()
        p6, meta6 = _evaluate_pillar_6(
            repo_root=REPO_ROOT,
            use_clean_room=True,
            faults=RealHwMilestone295FaultInjection(),
            p1_meta=m1,
            p2_meta=m2,
            p3_meta=m3,
            p4_meta=m4,
            p5_meta=m5,
        )
        self.assertTrue(p6.passed, p6.errors)
        self.assertGreaterEqual(meta6["qemu_rounds_verified"], 31)
        self.assertGreaterEqual(meta6["qemu_runs_verified"], 93)
        self.assertGreaterEqual(meta6["qemu_png_receipts_verified"], 62)
        self.assertLess(meta6["qemu_png_max_bytes"], PNG_MAX_SIZE_50KIB_BYTES)
        self.assertEqual(meta6["qemu_raw_firmware_bytes_leaked"], 0)
        for rnum in range(53, 59):
            self.assertEqual(meta6["qemu_round_runs_by_round"][f"r{rnum}"], 3)

    def test_58_pillar6_committed_rounds53_to_58_png_headers_under_50kib(self) -> None:
        for rnum in range(53, 59):
            for rel in ROUND28_TO_58_PNG_RECEIPTS[rnum]:
                p = REPO_ROOT / rel
                if p.is_file():
                    raw = p.read_bytes()
                    self.assertTrue(raw.startswith(PNG_MAGIC_BYTES), rel)
                    self.assertLess(len(raw), PNG_MAX_SIZE_50KIB_BYTES, rel)

    def test_59_pillar6_forward_compatible_with_round59_directory_discovery(self) -> None:
        m1, m2, m3, m4, m5 = self._clean_p1_to_p5_metas()
        with tempfile.TemporaryDirectory() as tmp:
            tmp_root = Path(tmp)
            r59_dir = tmp_root / "reports" / "2026-11-18-round59-realhw-future-wave53-qemu"
            assets_dir = r59_dir / "assets"
            assets_dir.mkdir(parents=True, exist_ok=True)
            for name in ("r59a-alpha.png", "r59a-composited.png"):
                (assets_dir / name).write_bytes(PNG_MAGIC_BYTES + b"\x00" * 128)
            summary = {
                "schema": "fx6-on-fx3-round59-realhw-future-wave53-qemu-v1",
                "round": 59,
                "kernel_version": "Linux version 4.9.337-scel+ (clean-room-synthetic)",
                "raw_firmware_bytes_leaked": 0,
                "runs": {
                    "r59a_run": {"nop_count": 0, "crashes": 0, "emmc_write_count": 0, "stage_b": {"manifest_count": 13}},
                    "r59b_run": {"nop_count": 0, "crashes": 0, "emmc_write_count": 0, "stage_b": {"manifest_count": 13}},
                    "r59c_run": {"nop_count": 0, "crashes": 0, "emmc_write_count": 0, "stage_b": {"manifest_count": 13}},
                },
                "r59_realhw_future_wave53_audit": {
                    "all_3_runs_crashes_zero": True,
                    "all_3_runs_emmc_write_zero": True,
                    "fx3_has_builtin_evf": False,
                    "fx3_has_var_shutter": False,
                },
            }
            (r59_dir / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
            p6, meta6 = _evaluate_pillar_6(
                repo_root=tmp_root,
                use_clean_room=True,
                faults=RealHwMilestone295FaultInjection(),
                p1_meta=m1,
                p2_meta=m2,
                p3_meta=m3,
                p4_meta=m4,
                p5_meta=m5,
            )
            self.assertTrue(p6.passed, p6.errors)
            self.assertGreaterEqual(meta6["qemu_rounds_verified"], 32)
            self.assertGreaterEqual(meta6["qemu_runs_verified"], 96)
            self.assertGreaterEqual(meta6["qemu_png_receipts_verified"], 64)

    def test_60_pillar6_forward_compatible_round59_rejects_bad_audit_flag_or_kernel(self) -> None:
        m1, m2, m3, m4, m5 = self._clean_p1_to_p5_metas()
        with tempfile.TemporaryDirectory() as tmp:
            tmp_root = Path(tmp)
            r59_dir = tmp_root / "reports" / "2026-11-18-round59-realhw-broken-qemu"
            r59_dir.mkdir(parents=True, exist_ok=True)
            summary = {
                "schema": "fx6-on-fx3-round59-broken-v1",
                "round": 59,
                "kernel_version": "Linux version 4.9.337-scel+ (clean-room-synthetic)",
                "raw_firmware_bytes_leaked": 0,
                "runs": {
                    "r59a_run": {"nop_count": 0, "crashes": 0, "emmc_write_count": 0, "stage_b": {"manifest_count": 13}},
                },
                "r59_broken_audit": {
                    "all_3_runs_crashes_zero": True,
                    "fx3_has_builtin_evf": True,
                },
            }
            (r59_dir / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
            p6, _ = _evaluate_pillar_6(
                repo_root=tmp_root,
                use_clean_room=True,
                faults=RealHwMilestone295FaultInjection(),
                p1_meta=m1,
                p2_meta=m2,
                p3_meta=m3,
                p4_meta=m4,
                p5_meta=m5,
            )
            self.assertFalse(p6.passed)

    def test_61_pillar6_fails_on_rounds53_to_58_schema_tamper(self) -> None:
        m1, m2, m3, m4, m5 = self._clean_p1_to_p5_metas()
        for rnum in range(53, 59):
            p6, _ = _evaluate_pillar_6(
                repo_root=REPO_ROOT,
                use_clean_room=True,
                faults=RealHwMilestone295FaultInjection(p6_tamper_schema_round_num=rnum),
                p1_meta=m1,
                p2_meta=m2,
                p3_meta=m3,
                p4_meta=m4,
                p5_meta=m5,
            )
            self.assertFalse(p6.passed, rnum)

    def test_62_pillar6_fails_on_round58_nop_crash_emmc_write_or_raw_leak(self) -> None:
        m1, m2, m3, m4, m5 = self._clean_p1_to_p5_metas()
        for fkw in (
            {"p6_round_nop_override_num": 58, "p6_round_nop_count_override": 1},
            {"p6_round_crash_override_num": 58, "p6_round_crashes_override": 1},
            {"p6_round_emmc_override_num": 58, "p6_round_emmc_writes_override": 1},
            {"p6_raw_firmware_bytes_leaked_override": 8},
        ):
            p6, _ = _evaluate_pillar_6(
                repo_root=REPO_ROOT,
                use_clean_room=True,
                faults=RealHwMilestone295FaultInjection(**fkw),
                p1_meta=m1,
                p2_meta=m2,
                p3_meta=m3,
                p4_meta=m4,
                p5_meta=m5,
            )
            self.assertFalse(p6.passed, fkw)

    def test_63_pillar6_fails_when_png_receipt_reaches_or_exceeds_50kib_ceiling(self) -> None:
        m1, m2, m3, m4, m5 = self._clean_p1_to_p5_metas()
        p6, _ = _evaluate_pillar_6(
            repo_root=REPO_ROOT,
            use_clean_room=True,
            faults=RealHwMilestone295FaultInjection(
                p6_png_size_override_round_num=58,
                p6_png_size_override_bytes=PNG_MAX_SIZE_50KIB_BYTES,
            ),
            p1_meta=m1,
            p2_meta=m2,
            p3_meta=m3,
            p4_meta=m4,
            p5_meta=m5,
        )
        self.assertFalse(p6.passed)

    def test_64_pillar6_cross_pillar_p1_cross_model_and_p2_cnflasha_invariants_fail(self) -> None:
        m1, m2, m3, m4, m5 = self._clean_p1_to_p5_metas()
        m1_bad = dict(m1)
        m1_bad["cross_model_flash_authorized"] = True
        self.assertFalse(
            _evaluate_pillar_6(
                repo_root=REPO_ROOT,
                use_clean_room=True,
                faults=RealHwMilestone295FaultInjection(),
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
                faults=RealHwMilestone295FaultInjection(),
                p1_meta=m1,
                p2_meta=m2_bad,
                p3_meta=m3,
                p4_meta=m4,
                p5_meta=m5,
            )[0].passed
        )

    def test_65_pillar6_cross_pillar_p275_to_p291_h0_h3_and_attach_fail_closed(self) -> None:
        m1, m2, m3, m4, m5 = self._clean_p1_to_p5_metas()
        for bad_k, bad_v in (
            ("p275_h0_equals_h3_count", 15),
            ("p279_hardware_live_attachment_authorized", True),
            ("p284_h0_equals_h3_count", 15),
            ("p291_h0_equals_h3_count", 15),
            ("p291_hardware_live_attachment_authorized", True),
            ("p291_sim_passive_tx_bytes_emitted", 1),
        ):
            m5_bad = dict(m5)
            m5_bad[bad_k] = bad_v
            p6_bad, _ = _evaluate_pillar_6(
                repo_root=REPO_ROOT,
                use_clean_room=True,
                faults=RealHwMilestone295FaultInjection(),
                p1_meta=m1,
                p2_meta=m2,
                p3_meta=m3,
                p4_meta=m4,
                p5_meta=m5_bad,
            )
            self.assertFalse(p6_bad.passed, bad_k)

    # --- 9. Fail-Closed Verifier, CLI & Cross-Platform Subprocess ---

    def test_66_verifier_rejects_non_mapping_payload(self) -> None:
        self.assertFalse(verify_realhw_milestone295_master_gate("not-a-dict").valid)
        self.assertFalse(verify_realhw_milestone295_master_gate(123).valid)
        self.assertFalse(verify_realhw_milestone295_master_gate(None).valid)  # type: ignore[arg-type]

    def test_67_verifier_rejects_sha256_tamper_and_schema_tamper(self) -> None:
        d = self.rep_clean.to_dict()
        d["milestone295_sha256"] = "f" * 64
        self.assertFalse(verify_realhw_milestone295_master_gate(d).valid)

        d2 = self.rep_clean.to_dict()
        d2["schema"] = "wrong_schema_v1"
        d2["milestone295_sha256"] = compute_milestone295_sha256(d2)
        self.assertFalse(verify_realhw_milestone295_master_gate(d2).valid)

    def test_68_verifier_rejects_redline_tamper_even_when_rehashed(self) -> None:
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
            ("p275_hardware_live_attachment_authorized", True),
            ("p279_hardware_live_attachment_authorized", True),
            ("p284_hardware_live_attachment_authorized", True),
            ("p291_hardware_live_attachment_authorized", True),
        ):
            d = self.rep_clean.to_dict()
            d[k] = v
            d["milestone295_sha256"] = compute_milestone295_sha256(d)
            self.assertFalse(verify_realhw_milestone295_master_gate(d).valid, k)

    def test_69_verifier_accepts_forward_compatible_higher_counts(self) -> None:
        d = self.rep_clean.to_dict()
        d["gate124_total_gates"] = 126
        d["gate124_offline_verified"] = 123
        d["gate124_simulated_verified"] = 126
        d["recovery_pillar_count"] = 51
        d["recovery_pillars_passed"] = 51
        d["auditors_total"] = 46
        d["auditors_passed"] = 46
        d["vm_stages_total"] = 59
        d["vm_stages_passed"] = 59
        d["qemu_rounds_total"] = 32
        d["qemu_rounds_verified"] = 32
        d["qemu_runs_total"] = 96
        d["qemu_runs_verified"] = 96
        d["qemu_png_receipts_total"] = 64
        d["qemu_png_receipts_verified"] = 64
        d["milestone295_sha256"] = compute_milestone295_sha256(d)
        v = verify_realhw_milestone295_master_gate(d)
        self.assertTrue(v.valid, v.errors)

    def test_70_verifier_rejects_sub_threshold_counts_and_raw_bytes(self) -> None:
        for k, v in (
            ("gate124_simulated_verified", 123),
            ("recovery_pillar_count", 49),
            ("auditors_passed", 44),
            ("vm_stages_passed", 57),
            ("p275_sim_check_groups_passed", 3),
            ("p279_sim_check_groups_passed", 3),
            ("p284_sim_check_groups_passed", 3),
            ("p291_sim_check_groups_passed", 3),
            ("qemu_rounds_verified", 30),
            ("qemu_runs_verified", 92),
            ("qemu_png_receipts_verified", 61),
            ("qemu_png_max_bytes", PNG_MAX_SIZE_50KIB_BYTES),
        ):
            d = self.rep_clean.to_dict()
            d[k] = v
            d["milestone295_sha256"] = compute_milestone295_sha256(d)
            self.assertFalse(verify_realhw_milestone295_master_gate(d).valid, k)

        d_raw = self.rep_clean.to_dict()
        d_raw["pillars"][0]["summary"] = "leaked b'\\x7fELF'"
        d_raw["milestone295_sha256"] = compute_milestone295_sha256(d_raw)
        self.assertFalse(verify_realhw_milestone295_master_gate(d_raw).valid)

    def test_71_cli_verify_milestone_295_summary_and_out_alias_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            out_json = tmp_path / "m295.json"
            out_md = tmp_path / "m295.md"
            buf = io.StringIO()
            with (
                mock.patch(
                    "fx6_closure.realhw_milestone295_master_gate.evaluate_realhw_milestone295_master_gate",
                    return_value=self.rep_clean,
                ),
                mock.patch("sys.stdout", buf),
            ):
                rc = fx6_cli_main(
                    [
                        "verify-milestone-295",
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
            self.assertIn("schema=realhw_milestone295_master_gate_v1", text)
            self.assertIn("cnflasha_ro=True", text)
            self.assertIn("cross_model_flash_auth=False", text)
            self.assertIn("p291=BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT/DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH", text)
            self.assertIn("ready_attach=False", text)
            self.assertIsNotNone(re.search(r"gate124=(\d+)/(\d+)", text))
            self.assertIsNotNone(re.search(r"qemu=(\d+)/(\d+)\((\d+)/(\d+)\)", text))
            self.assertTrue(out_json.is_file())
            self.assertTrue(out_md.is_file())
            self.assertTrue(
                verify_realhw_milestone295_master_gate(json.loads(out_json.read_text())).valid
            )

    def test_72_cli_verify_milestone_295_json_stdout_and_failure_exit_code(self) -> None:
        buf = io.StringIO()
        with (
            mock.patch(
                "fx6_closure.realhw_milestone295_master_gate.evaluate_realhw_milestone295_master_gate",
                return_value=self.rep_clean,
            ),
            mock.patch("sys.stdout", buf),
        ):
            rc = fx6_cli_main(["verify-milestone-295", "--clean-room", "--json"])
        self.assertEqual(rc, 0)
        parsed = json.loads(buf.getvalue())
        self.assertEqual(parsed["schema"], REALHW_MILESTONE295_SCHEMA)
        self.assertEqual(parsed["usb_packets_transmitted"], 0)
        self.assertFalse(parsed["overall_ready_for_hardware_attach"])
        self.assertFalse(parsed["cross_model_flash_authorized"])

        bad_rep = replace(
            self.rep_clean,
            all_pillars_milestone_ready=False,
            status=STATUS_FAIL_CLOSED,
            passed_pillar_count=5,
            failed_pillar_ids=("P1",),
            milestone295_sha256="0" * 64,
        )
        buf2 = io.StringIO()
        with (
            mock.patch(
                "fx6_closure.realhw_milestone295_master_gate.evaluate_realhw_milestone295_master_gate",
                return_value=bad_rep,
            ),
            mock.patch("sys.stdout", buf2),
        ):
            rc2 = fx6_cli_main(["verify-milestone-295", "--force-clean-room"])
        self.assertEqual(rc2, 1)
        self.assertIn("status=FAILED", buf2.getvalue())

    def test_73_verify_milestone_295_cli_direct_helper_entrypoint(self) -> None:
        buf = io.StringIO()
        with (
            mock.patch(
                "fx6_closure.realhw_milestone295_master_gate.evaluate_realhw_milestone295_master_gate",
                return_value=self.rep_clean,
            ),
            mock.patch("sys.stdout", buf),
        ):
            rc = verify_milestone_295_cli(["--clean-room", "--json"])
        self.assertEqual(rc, 0)
        parsed = json.loads(buf.getvalue())
        self.assertEqual(parsed["schema"], REALHW_MILESTONE295_SCHEMA)
        self.assertTrue(parsed["cnflasha_userspace_write_blocked"])

    def test_74_argparse_help_formatting_safe_for_python_312_and_macos(self) -> None:
        buf_top = io.StringIO()
        with mock.patch("sys.stdout", buf_top):
            with self.assertRaises(SystemExit) as ctx_top:
                fx6_cli_main(["--help"])
        self.assertEqual(ctx_top.exception.code, 0)
        self.assertIn("verify-milestone-295", buf_top.getvalue())

        buf_sub = io.StringIO()
        with mock.patch("sys.stdout", buf_sub):
            with self.assertRaises(SystemExit) as ctx_sub:
                fx6_cli_main(["verify-milestone-295", "--help"])
        self.assertEqual(ctx_sub.exception.code, 0)
        self.assertIn("--force-clean-room", buf_sub.getvalue())

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
                "verify-milestone-295",
                "--force-clean-room",
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
        self.assertEqual(payload["schema"], REALHW_MILESTONE295_SCHEMA)
        self.assertTrue(payload["all_pillars_milestone_ready"])
        self.assertGreaterEqual(payload["gate124_simulated_verified"], 124)
        self.assertGreaterEqual(payload["recovery_pillars_passed"], 50)
        self.assertGreaterEqual(payload["auditors_passed"], 45)
        self.assertGreaterEqual(payload["vm_stages_passed"], 58)
        self.assertGreaterEqual(payload["qemu_rounds_verified"], 31)
        self.assertGreaterEqual(payload["qemu_runs_verified"], 93)
        self.assertGreaterEqual(payload["qemu_png_receipts_verified"], 62)
        self.assertLess(elapsed, 15.0)

    def test_76_synthetic_clean_room_kwarg_alias_and_suite_runtime_budget(self) -> None:
        rep = evaluate_milestone_295_master_gate(
            synthetic_clean_room=True,
            _raw_bundle_override=self._unpack_clean_raw(),
        )
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(rep.all_pillars_milestone_ready)
        self.assertLess(self.default_elapsed_s, 15.0)


if __name__ == "__main__":
    unittest.main()
