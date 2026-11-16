"""Phase 254 dual-mode unit tests for Grand Milestone Phase 254 6-Pillar Real-Hardware Master Gate."""

from __future__ import annotations

import copy
from dataclasses import replace
import io
import json
from pathlib import Path
import re
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
from fx6_closure.realhw_milestone254_master_gate import (  # noqa: E402
    CALIBRATION_MUTATION_BYTES,
    CNFLASHA_USERSPACE_WRITE_BLOCKED,
    CP_MUTATION_BYTES,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    EMMC_WRITE_COUNT,
    E_ND_ACTUATOR_TX_COUNT,
    FIRMWARE_LAB_45_AUDITOR_KEYS,
    HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    ISP_WRITE_AUTHORIZED,
    MILESTONE254_SCHEMA_VERSION,
    OTP_FUSE_TOUCHES,
    OTP_FUSE_WRITES,
    OVERALL_READY_FOR_HARDWARE_ATTACH,
    P8_CP_MUTATION_FORBIDDEN,
    PASSIVE_TX_BYTES,
    PASSIVE_TX_BYTES_EMITTED,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHASE_254_VERSION,
    PHYSICAL_DEVICE_WRITES,
    PHYSICAL_USB_PACKETS_EMITTED,
    PILLAR_IDS,
    PILLAR_SPECS,
    PNG_MAGIC_BYTES,
    PNG_MAX_SIZE_50KIB_BYTES,
    PNG_MAX_SIZE_BYTES,
    RAW_FIRMWARE_BYTES_LEAKED,
    REALHW_MILESTONE254_SCHEMA,
    RECOVERY_41_PILLAR_IDS,
    ROUND28_TO_50_PNG_RECEIPTS,
    ROUND28_TO_50_SPECS,
    ROUND48_EXPECTED_SCHEMA,
    ROUND49_EXPECTED_SCHEMA,
    ROUND50_EXPECTED_SCHEMA,
    RPMB_COUNTER_INCREMENTS,
    RPMB_WRITES,
    SPI_NOR_WRITE_AUTHORIZED,
    STATUS_FAIL_CLOSED,
    STATUS_MILESTONE_READY,
    USB_OR_CAMERA_OPERATIONS,
    USB_PACKETS_TRANSMITTED,
    VM_COEMULATION_47_STAGE_KEYS,
    WBI_MUTATION_BYTES,
    WBI_P5_WRITE_AND_HIBERNATION_FORBIDDEN,
    RealHwMilestone254FaultInjection,
    RealHwMilestone254MasterGateReport,
    _collect_parallel_milestone254_results,
    _evaluate_pillar_1,
    _evaluate_pillar_2,
    _evaluate_pillar_3,
    _evaluate_pillar_4,
    _evaluate_pillar_5,
    _evaluate_pillar_6,
    _fault_to_96gate_worker_dict,
    _normalize_41pillar_fault_id,
    _worker_96gate_single,
    _worker_phase248,
    _worker_recovery_41pillar,
    build_realhw_milestone254_master_gate_report,
    compute_milestone254_sha256,
    evaluate_milestone254_master_gate,
    evaluate_milestone_254_master_gate,
    evaluate_realhw_milestone254_master_gate,
    render_milestone254_markdown,
    verify_milestone_254_cli,
    verify_milestone_254_master_gate,
    verify_realhw_milestone254_master_gate,
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


def _fork_child_clean_and_fault_fixtures(conn) -> None:
    from concurrent.futures import ProcessPoolExecutor
    import multiprocessing as mp

    g95_fdict = _fault_to_96gate_worker_dict(
        RealHwMilestone254FaultInjection(
            p1_lock_op_parts_kwargs={"slot_full_format_chord_invoked": True},
            p1_request_persistent_writes=True,
        )
    )
    ctx = mp.get_context("fork")
    with ProcessPoolExecutor(max_workers=2, mp_context=ctx) as pool:
        fut_g95 = pool.submit(_worker_96gate_single, (str(REPO_ROOT), True, True, g95_fdict))
        fut_p41 = pool.submit(_worker_recovery_41pillar, (True, "pillar_41"))
        bad_g95 = fut_g95.result()
        bad_p41 = fut_p41.result()
    raw_clean = _collect_parallel_milestone254_results(
        repo_root=REPO_ROOT,
        fx6_lib_dir=DEFAULT_FX6_DONOR_LIB_DIR,
        fx3_modules_dir=DEFAULT_FX3_MODULES_DIR,
        use_clean_room=True,
        faults=RealHwMilestone254FaultInjection(),
    )
    conn.send((raw_clean, bad_g95, bad_p41))
    conn.close()


class TestRealHwMilestone254MasterGate(unittest.TestCase):
    """Comprehensive 62 dual-mode tests for Grand Milestone Phase 254 (< 6.0s total)."""

    raw_bundle: tuple
    rep_default: RealHwMilestone254MasterGateReport
    rep_clean: RealHwMilestone254MasterGateReport
    bad_sim_g95: dict
    bad_rec_41: dict
    default_elapsed_s: float

    @classmethod
    def setUpClass(cls) -> None:
        from concurrent.futures import ProcessPoolExecutor
        import multiprocessing as mp

        t0 = time.monotonic()
        ctx = mp.get_context("fork")
        if _is_forced_clean_room():
            g95_fdict = _fault_to_96gate_worker_dict(
                RealHwMilestone254FaultInjection(
                    p1_lock_op_parts_kwargs={"slot_full_format_chord_invoked": True},
                    p1_request_persistent_writes=True,
                )
            )
            with ProcessPoolExecutor(max_workers=2, mp_context=ctx) as pool:
                fut_g95 = pool.submit(_worker_96gate_single, (str(REPO_ROOT), True, True, g95_fdict))
                fut_p41 = pool.submit(_worker_recovery_41pillar, (True, "pillar_41"))
                cls.bad_sim_g95 = fut_g95.result()
                cls.bad_rec_41 = fut_p41.result()
            cls.raw_bundle = _collect_parallel_milestone254_results(
                repo_root=REPO_ROOT,
                fx6_lib_dir=DEFAULT_FX6_DONOR_LIB_DIR,
                fx3_modules_dir=DEFAULT_FX3_MODULES_DIR,
                use_clean_room=True,
                faults=RealHwMilestone254FaultInjection(),
            )
            cls.rep_clean = evaluate_milestone_254_master_gate(
                force_clean_room=True,
                _raw_bundle_override=cls.raw_bundle,
            )
            cls.rep_default = cls.rep_clean
        else:
            recv_conn, send_conn = ctx.Pipe(duplex=False)
            proc = ctx.Process(
                target=_fork_child_clean_and_fault_fixtures,
                args=(send_conn,),
                daemon=False,
            )
            proc.start()
            send_conn.close()
            try:
                cls.rep_default = evaluate_milestone_254_master_gate()
                cls.raw_bundle, cls.bad_sim_g95, cls.bad_rec_41 = recv_conn.recv()
            finally:
                recv_conn.close()
                proc.join(timeout=30)
            cls.rep_clean = evaluate_milestone_254_master_gate(
                force_clean_room=True,
                _raw_bundle_override=cls.raw_bundle,
            )
        cls.default_elapsed_s = time.monotonic() - t0

    def _unpack_clean_raw(self):
        return _LazyDeepcopyBundle(self.raw_bundle)

    # --- 1. Constants, Exports & Schema ---

    def test_01_schema_and_version_constants(self) -> None:
        self.assertEqual(REALHW_MILESTONE254_SCHEMA, "realhw_milestone254_master_gate_v1")
        self.assertEqual(MILESTONE254_SCHEMA_VERSION, REALHW_MILESTONE254_SCHEMA)
        self.assertEqual(PHASE_254_VERSION, "254.0.0")
        self.assertEqual(PILLAR_IDS, ("P1", "P2", "P3", "P4", "P5", "P6"))
        self.assertEqual(len(PILLAR_SPECS), 6)
        self.assertGreaterEqual(len(RECOVERY_41_PILLAR_IDS), 41)
        self.assertGreaterEqual(len(FIRMWARE_LAB_45_AUDITOR_KEYS), 45)
        self.assertGreaterEqual(len(VM_COEMULATION_47_STAGE_KEYS), 47)
        self.assertGreaterEqual(len(ROUND28_TO_50_SPECS), 23)
        self.assertEqual(PNG_MAX_SIZE_50KIB_BYTES, 51200)
        self.assertEqual(PNG_MAX_SIZE_BYTES, 51200)

    def test_02_hard_locked_zero_write_and_attach_constants(self) -> None:
        self.assertFalse(OVERALL_READY_FOR_HARDWARE_ATTACH)
        self.assertFalse(HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(PERSISTENT_WRITE_RELEASE)
        self.assertFalse(SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        self.assertFalse(ISP_WRITE_AUTHORIZED)
        self.assertTrue(CNFLASHA_USERSPACE_WRITE_BLOCKED)
        self.assertTrue(P8_CP_MUTATION_FORBIDDEN)
        self.assertTrue(WBI_P5_WRITE_AND_HIBERNATION_FORBIDDEN)
        for zero_const in (
            USB_PACKETS_TRANSMITTED,
            PHYSICAL_USB_PACKETS_EMITTED,
            PHYSICAL_DEVICE_WRITES,
            RAW_FIRMWARE_BYTES_LEAKED,
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
            "CNFLASHA_USERSPACE_WRITE_BLOCKED",
            "FIRMWARE_LAB_45_AUDITOR_KEYS",
            "MILESTONE254_PHYSICAL_DEVICE_WRITES",
            "MILESTONE254_PILLAR_IDS",
            "MILESTONE254_PILLAR_SPECS",
            "MILESTONE254_PNG_MAX_SIZE_BYTES",
            "MILESTONE254_RAW_FIRMWARE_BYTES_LEAKED",
            "MILESTONE254_SCHEMA_VERSION",
            "OVERALL_READY_FOR_HARDWARE_ATTACH",
            "PHASE_254_VERSION",
            "PNG_MAX_SIZE_50KIB_BYTES",
            "REALHW_MILESTONE254_SCHEMA",
            "RECOVERY_41_PILLAR_IDS",
            "ROUND28_TO_50_PNG_RECEIPTS",
            "ROUND28_TO_50_SPECS",
            "ROUND48_EXPECTED_SCHEMA",
            "ROUND49_EXPECTED_SCHEMA",
            "ROUND50_EXPECTED_SCHEMA",
            "STATUS_MILESTONE254_FAIL_CLOSED",
            "STATUS_MILESTONE254_READY",
            "VM_COEMULATION_47_STAGE_KEYS",
            "Milestone254PillarResult",
            "RealHwMilestone254FaultInjection",
            "RealHwMilestone254MasterGateReport",
            "RealHwMilestone254VerifyResult",
            "build_realhw_milestone254_master_gate_report",
            "compute_milestone254_sha256",
            "evaluate_milestone254_master_gate",
            "evaluate_milestone_254_master_gate",
            "evaluate_realhw_milestone254_master_gate",
            "render_milestone254_markdown",
            "verify_milestone_254_cli",
            "verify_milestone_254_master_gate",
            "verify_realhw_milestone254_master_gate",
        }
        self.assertTrue(expected.issubset(set(fx6_closure.__all__)))
        for sym in expected:
            self.assertTrue(hasattr(fx6_closure, sym), sym)
        self.assertEqual(fx6_closure.REALHW_MILESTONE233_SCHEMA, "realhw_milestone233_master_gate_v1")
        self.assertEqual(fx6_closure.REALHW_MILESTONE221_SCHEMA, "realhw_milestone221_master_gate_v1")

    def test_04_builder_and_verifier_aliases_point_to_canonical_functions(self) -> None:
        self.assertIs(build_realhw_milestone254_master_gate_report, evaluate_realhw_milestone254_master_gate)
        self.assertIs(evaluate_milestone_254_master_gate, evaluate_realhw_milestone254_master_gate)
        self.assertIs(evaluate_milestone254_master_gate, evaluate_realhw_milestone254_master_gate)
        self.assertIs(verify_milestone_254_master_gate, verify_realhw_milestone254_master_gate)

    def test_05_round48_to_50_specs_and_png_pairs_registered(self) -> None:
        by_num = {s.round_num: s for s in ROUND28_TO_50_SPECS}
        for rnum, exp_schema in (
            (48, ROUND48_EXPECTED_SCHEMA),
            (49, ROUND49_EXPECTED_SCHEMA),
            (50, ROUND50_EXPECTED_SCHEMA),
        ):
            self.assertIn(rnum, by_num)
            self.assertEqual(by_num[rnum].expected_schema, exp_schema)
            self.assertEqual(len(by_num[rnum].run_specs), 3)
            self.assertIn(rnum, ROUND28_TO_50_PNG_RECEIPTS)
            self.assertEqual(len(ROUND28_TO_50_PNG_RECEIPTS[rnum]), 2)
        self.assertEqual(by_num[48].run_specs[1][1], 1)
        self.assertEqual(by_num[49].run_specs[0][1], 1)
        self.assertEqual(by_num[50].run_specs[0][1], 1)

    def test_06_normalize_41pillar_fault_id_resolves_short_and_full_ids(self) -> None:
        self.assertIsNone(_normalize_41pillar_fault_id(None))
        self.assertIsNone(_normalize_41pillar_fault_id(""))
        for pnum in (39, 40, 41):
            full_id = RECOVERY_41_PILLAR_IDS[pnum - 1]
            self.assertEqual(_normalize_41pillar_fault_id(f"pillar_{pnum}"), full_id)
            self.assertEqual(_normalize_41pillar_fault_id(full_id), full_id)
        self.assertEqual(
            _normalize_41pillar_fault_id("pillar_40"),
            "pillar_40_lock_op_parts_audio_timing_exp_step_vault",
        )

    # --- 2. End-to-End Dual-Mode Reports, Determinism & Markdown ---

    def test_07_default_mode_report_all_6_pillars_ready(self) -> None:
        rep = self.rep_default
        self.assertTrue(rep.all_pillars_milestone_ready, rep.errors)
        self.assertEqual(rep.status, STATUS_MILESTONE_READY)
        self.assertEqual(rep.passed_pillar_count, 6)
        self.assertEqual(rep.failed_pillar_ids, ())
        v = verify_realhw_milestone254_master_gate(rep)
        self.assertTrue(v.valid, v.errors)

    def test_08_clean_room_mode_report_all_6_pillars_ready_and_locked(self) -> None:
        rep = self.rep_clean
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(rep.all_pillars_milestone_ready, rep.errors)
        self.assertEqual(rep.status, STATUS_MILESTONE_READY)
        self.assertTrue(rep.cnflasha_userspace_write_blocked)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.hardware_live_attachment_authorized)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.spi_nor_write_authorized)
        self.assertFalse(rep.el3_payload_transmit_authorized)
        self.assertEqual(rep.usb_packets_transmitted, 0)
        self.assertEqual(rep.physical_device_writes, 0)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)
        self.assertEqual(rep.otp_fuse_touches, 0)
        self.assertEqual(rep.rpmb_counter_increments, 0)
        self.assertEqual(rep.passive_tx_bytes_emitted, 0)
        self.assertTrue(verify_realhw_milestone254_master_gate(rep.to_dict()).valid)

    def test_09_forward_compatible_lower_bounds_on_clean_report(self) -> None:
        rep = self.rep_clean
        self.assertGreaterEqual(rep.gate96_total_gates, 96)
        self.assertGreaterEqual(rep.gate96_offline_verified, 93)
        self.assertEqual(rep.gate96_offline_verified, rep.gate96_total_gates - 3)
        self.assertEqual(rep.gate96_simulated_verified, rep.gate96_total_gates)
        self.assertTrue(rep.gate96_all_verified)
        self.assertGreaterEqual(rep.recovery_pillar_count, 41)
        self.assertEqual(rep.recovery_pillars_passed, rep.recovery_pillar_count)
        self.assertGreaterEqual(rep.auditors_passed, 45)
        self.assertEqual(rep.auditors_passed, rep.auditors_total)
        self.assertGreaterEqual(rep.vm_stages_passed, 47)
        self.assertEqual(rep.vm_stages_passed, rep.vm_stages_total)
        self.assertGreaterEqual(rep.qemu_rounds_verified, 23)
        self.assertGreaterEqual(rep.qemu_runs_verified, 69)
        self.assertGreaterEqual(rep.qemu_png_receipts_verified, 46)
        self.assertLess(rep.qemu_png_max_bytes, PNG_MAX_SIZE_50KIB_BYTES)
        self.assertEqual(rep.h0_equals_h3_count, 16)
        self.assertEqual(rep.e_nd_actuator_tx_count, 0)

    def test_10_deterministic_json_and_sha256_recomputation(self) -> None:
        j1 = self.rep_clean.to_deterministic_json()
        parsed = json.loads(j1)
        self.assertEqual(compute_milestone254_sha256(parsed), self.rep_clean.milestone254_sha256)
        rep2 = evaluate_milestone_254_master_gate(
            force_clean_room=True,
            _raw_bundle_override=self._unpack_clean_raw(),
        )
        self.assertEqual(rep2.milestone254_sha256, self.rep_clean.milestone254_sha256)

    def test_11_no_raw_bytes_repr_in_serialized_reports(self) -> None:
        for rep in (self.rep_default, self.rep_clean):
            self.assertIsNone(re.search(_RAW_BYTES_REPR_REGEX, rep.to_deterministic_json()))

    def test_12_markdown_renderer_contains_bilingual_headers_and_6_pillars(self) -> None:
        md = render_milestone254_markdown(self.rep_clean)
        for token in (
            "Grand Milestone Phase 254",
            "realhw_milestone254_master_gate_v1",
            "MILESTONE_254_PREBENCH_MASTER_VERIFIED",
            "96-Gate Preflight",
            "41-Pillar Recovery Master",
            "Ph248=",
            "| `P1` |",
            "| `P6` |",
        ):
            self.assertIn(token, md)

    # --- 3. Pillar 1: >= 96 Safety Gates (`fx3_safety.evaluate_96gate_preflight`) ---

    def test_13_pillar1_96gate_happy_path_and_g63_to_g96_valid(self) -> None:
        raw_off, raw_sim = self._unpack_clean_raw()[:2]
        p1 = _evaluate_pillar_1(raw_off, raw_sim)
        self.assertTrue(p1.passed, p1.errors)
        self.assertGreaterEqual(p1.evidence["offline_verified_gates"], 93)
        self.assertGreaterEqual(p1.evidence["simulated_verified_gates"], 96)
        self.assertTrue(p1.evidence["all_96_gates_verified"])
        for idx in range(63, 97):
            self.assertTrue(p1.evidence["g63_to_g96_valid"][f"g{idx}"], f"g{idx}")

    def test_14_pillar1_forward_compatible_with_98_gates(self) -> None:
        raw_off, raw_sim = self._unpack_clean_raw()[:2]
        raw_off["total_gates"] = 98
        raw_off["verified_gates"] = 95
        raw_sim["total_gates"] = 98
        raw_sim["verified_gates"] = 98
        p1 = _evaluate_pillar_1(raw_off, raw_sim)
        self.assertTrue(p1.passed, p1.errors)

    def test_15_pillar1_fails_when_offline_tier0_gates_not_blocked(self) -> None:
        raw_off, raw_sim = self._unpack_clean_raw()[:2]
        raw_off["verified_gates"] = raw_off["total_gates"]
        raw_off["blocked_or_pending_gates"] = 0
        self.assertFalse(_evaluate_pillar_1(raw_off, raw_sim).passed)

    def test_16_pillar1_fails_when_all_96_gates_verified_false_in_dry_run(self) -> None:
        raw_off, raw_sim = self._unpack_clean_raw()[:2]
        raw_sim["all_96_gates_verified"] = False
        self.assertFalse(_evaluate_pillar_1(raw_off, raw_sim).passed)

    def test_17_pillar1_fails_when_hardware_attach_or_write_unlocked(self) -> None:
        for field in (
            "overall_ready_for_hardware_attach",
            "hardware_live_attachment_authorized",
            "persistent_emmc_writes_authorized",
            "spi_nor_write_authorized",
            "el3_payload_transmit_authorized",
        ):
            raw_off, raw_sim = self._unpack_clean_raw()[:2]
            raw_sim[field] = True
            self.assertFalse(_evaluate_pillar_1(raw_off, raw_sim).passed, field)

    def test_18_pillar1_fails_when_usb_packets_or_leak_or_end_tx_nonzero(self) -> None:
        for field in ("usb_packets_transmitted", "raw_firmware_bytes_leaked", "g71_e_nd_actuator_tx_count"):
            raw_off, raw_sim = self._unpack_clean_raw()[:2]
            raw_sim[field] = 1
            self.assertFalse(_evaluate_pillar_1(raw_off, raw_sim).passed, field)

    def test_19_pillar1_fails_when_any_g91_to_g96_gate_invalid(self) -> None:
        for gtag in ("g91", "g92", "g93", "g94", "g95", "g96"):
            raw_off, raw_sim = self._unpack_clean_raw()[:2]
            raw_sim["nested_g_valid"][gtag] = False
            p1 = _evaluate_pillar_1(raw_off, raw_sim)
            self.assertFalse(p1.passed, gtag)
            self.assertIn(gtag.upper(), p1.errors[-1])

    def test_20_pillar1_worker_live_g95_destructive_chord_and_persistent_write_fault(self) -> None:
        raw_sim_bad = copy.deepcopy(self.bad_sim_g95)
        raw_off = self._unpack_clean_raw()[0]
        p1 = _evaluate_pillar_1(raw_off, raw_sim_bad)
        self.assertFalse(p1.passed)
        self.assertFalse(raw_sim_bad["nested_g_valid"]["g95"])

    # --- 4. Pillar 2: >= 41 Recovery Pillars (`evaluate_realhw_41pillar_recovery_master`) ---

    def test_21_pillar2_41pillar_happy_path_and_cnflasha_ro(self) -> None:
        rec_41 = self._unpack_clean_raw()[2]
        p2, meta2 = _evaluate_pillar_2(rec_41, RealHwMilestone254FaultInjection())
        self.assertTrue(p2.passed, p2.errors)
        self.assertGreaterEqual(meta2["recovery_pillar_count"], 41)
        self.assertEqual(meta2["recovery_pillars_passed"], meta2["recovery_pillar_count"])
        self.assertTrue(meta2["cnflasha_userspace_write_blocked"])
        self.assertEqual(meta2["otp_fuse_writes"], 0)
        self.assertEqual(meta2["rpmb_writes"], 0)
        self.assertEqual(meta2["passive_tx_bytes"], 0)
        self.assertEqual(meta2["physical_usb_packets_emitted"], 0)
        self.assertEqual(meta2["physical_device_writes"], 0)
        self.assertEqual(meta2["raw_firmware_bytes_leaked"], 0)

    def test_22_pillar2_forward_compatible_with_42_pillars(self) -> None:
        rec_41 = self._unpack_clean_raw()[2]
        rec_41["pillar_count"] = 42
        rec_41["pillars_passed"] = 42
        rec_41["status"] = "VERIFIED_42OF42_PILLAR_RECOVERY_MASTER"
        p2, meta2 = _evaluate_pillar_2(rec_41, RealHwMilestone254FaultInjection())
        self.assertTrue(p2.passed, p2.errors)
        self.assertEqual(meta2["recovery_pillar_count"], 42)

    def test_23_pillar2_fails_when_cnflasha_userspace_write_unblocked(self) -> None:
        rec_41 = self._unpack_clean_raw()[2]
        p2, _ = _evaluate_pillar_2(
            rec_41,
            RealHwMilestone254FaultInjection(p2_cnflasha_write_unblocked_fault=True),
        )
        self.assertFalse(p2.passed)

    def test_24_pillar2_fails_on_otp_rpmb_passive_tx_usb_devwrite_or_leak_overrides(self) -> None:
        rec_41 = self._unpack_clean_raw()[2]
        for kw in (
            {"p2_otp_fuse_touches_override": 1},
            {"p2_rpmb_counter_increments_override": 1},
            {"p2_passive_tx_bytes_override": 4},
            {"p2_physical_usb_packets_override": 1},
            {"p2_physical_device_writes_override": 1},
            {"p2_raw_firmware_bytes_leaked_override": 8},
        ):
            p2, _ = _evaluate_pillar_2(rec_41, RealHwMilestone254FaultInjection(**kw))
            self.assertFalse(p2.passed, kw)

    def test_25_pillar2_fails_when_41a_or_41b_vault_subsuite_fails(self) -> None:
        for sub_key in (
            "pillar41_a_display_quality_bt_rmt_vault",
            "pillar41_b_my_menu_camset_vault",
        ):
            rec_41 = self._unpack_clean_raw()[2]
            rec_41[sub_key]["passed"] = False
            self.assertFalse(_evaluate_pillar_2(rec_41, RealHwMilestone254FaultInjection())[0].passed, sub_key)

    def test_26_pillar2_live_worker_fault_inject_pillar_41_fails_closed(self) -> None:
        bad_41 = copy.deepcopy(self.bad_rec_41)
        p2, _ = _evaluate_pillar_2(bad_41, RealHwMilestone254FaultInjection())
        self.assertFalse(p2.passed)

    def test_27_pillar2_fails_on_p39_to_p41_violation_counters_or_var_shutter_true(self) -> None:
        for vkey in (
            "unbuffered_battery_pull_events",
            "destructive_menu_delete_confusions",
            "tier0_battery_high_display_violations",
            "slot1_mymenu_vault_mutation_bytes",
            "shutter_angle_exposure_step_drift_events",
        ):
            rec_41 = self._unpack_clean_raw()[2]
            rec_41[vkey] = 1
            self.assertFalse(_evaluate_pillar_2(rec_41, RealHwMilestone254FaultInjection())[0].passed, vkey)

        rec_vs = self._unpack_clean_raw()[2]
        rec_vs["fx3_has_var_shutter"] = True
        self.assertFalse(_evaluate_pillar_2(rec_vs, RealHwMilestone254FaultInjection())[0].passed)

    # --- 5. Pillar 3: >= 45 Firmware Auditors (`outputs/fx3-firmware-lab`) ---

    def test_28_pillar3_45_auditors_happy_path(self) -> None:
        auditors = self._unpack_clean_raw()[3]
        p3, meta3 = _evaluate_pillar_3(auditors, RealHwMilestone254FaultInjection())
        self.assertTrue(p3.passed, p3.errors)
        self.assertGreaterEqual(meta3["auditor_count"], 45)
        self.assertEqual(meta3["passed_count"], meta3["auditor_count"])
        self.assertEqual(meta3["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(meta3["e_nd_actuator_tx_count"], 0)
        self.assertTrue(
            p3.evidence["auditor_statuses"]["realhw_filesettings_shotmark_tcregen_and_reclamp_audit"]
        )

    def test_29_pillar3_forward_compatible_with_46_plus_auditors(self) -> None:
        auditors = self._unpack_clean_raw()[3]
        auditors["realhw_future_wave40_audit"] = {"all_checks_passed": True}
        p3, meta3 = _evaluate_pillar_3(auditors, RealHwMilestone254FaultInjection())
        self.assertTrue(p3.passed, p3.errors)
        self.assertGreaterEqual(meta3["auditor_count"], 46)
        self.assertEqual(meta3["passed_count"], meta3["auditor_count"])

    def test_30_pillar3_fails_on_auditor45_guard_fault_or_subpillar_failure(self) -> None:
        auditors = self._unpack_clean_raw()[3]
        p3_fault, _ = _evaluate_pillar_3(
            auditors,
            RealHwMilestone254FaultInjection(p3_filesettings_tcregen_reclamp_guard_fault=True),
        )
        self.assertFalse(p3_fault.passed)

        auditors2 = self._unpack_clean_raw()[3]
        auditors2["realhw_filesettings_shotmark_tcregen_and_reclamp_audit"][
            "pillar_2_tc_regenerate_slot1_and_ext_lk"
        ]["passed"] = False
        self.assertFalse(_evaluate_pillar_3(auditors2, RealHwMilestone254FaultInjection())[0].passed)

    def test_31_pillar3_fails_on_raw_firmware_bytes_leaked_override(self) -> None:
        auditors = self._unpack_clean_raw()[3]
        p3, _ = _evaluate_pillar_3(
            auditors,
            RealHwMilestone254FaultInjection(p3_raw_firmware_bytes_leaked_override=16),
        )
        self.assertFalse(p3.passed)

    def test_32_pillar3_fails_when_forward_compat_46th_auditor_fails(self) -> None:
        auditors = self._unpack_clean_raw()[3]
        auditors["realhw_broken_future_audit"] = {"all_checks_passed": False}
        self.assertFalse(_evaluate_pillar_3(auditors, RealHwMilestone254FaultInjection())[0].passed)

    # --- 6. Pillar 4: >= 47 VM Co-Emulation Stages (`outputs/fx3-vm`) ---

    def test_33_pillar4_47_stages_happy_path(self) -> None:
        raw_vm = self._unpack_clean_raw()[4]
        p4, meta4 = _evaluate_pillar_4(raw_vm, RealHwMilestone254FaultInjection())
        self.assertTrue(p4.passed, p4.errors)
        self.assertGreaterEqual(meta4["stage_count"], 47)
        self.assertEqual(meta4["passed_count"], meta4["stage_count"])
        self.assertEqual(meta4["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(meta4["physical_device_writes"], 0)
        self.assertEqual(meta4["emmc_corruptions"], 0)
        for dkey in ("stage45_digest_sha256", "stage46_digest_sha256", "stage47_digest_sha256"):
            self.assertEqual(len(str(p4.evidence[dkey])), 64, dkey)

    def test_34_pillar4_forward_compatible_with_48_plus_stages(self) -> None:
        raw_vm = self._unpack_clean_raw()[4]
        raw_vm["stage48_realhw_future_wave40_hil"] = {"all_checks_passed": True}
        p4, meta4 = _evaluate_pillar_4(raw_vm, RealHwMilestone254FaultInjection())
        self.assertTrue(p4.passed, p4.errors)
        self.assertGreaterEqual(meta4["stage_count"], 48)
        self.assertEqual(meta4["passed_count"], meta4["stage_count"])

    def test_35_pillar4_fails_on_stage45_through_stage47_fault_injections(self) -> None:
        raw_vm = self._unpack_clean_raw()[4]
        for kw in (
            {"p4_stage45_emphasized_rec_touch_sunny_faults": 1},
            {"p4_stage46_shoe_audio_wind_saveload_faults": 1},
            {"p4_stage47_framing_usbpower_antiflicker_faults": 1},
        ):
            p4, _ = _evaluate_pillar_4(raw_vm, RealHwMilestone254FaultInjection(**kw))
            self.assertFalse(p4.passed, kw)

    def test_36_pillar4_fails_on_physical_device_writes_or_raw_leak(self) -> None:
        raw_vm = self._unpack_clean_raw()[4]
        for kw in (
            {"p4_physical_device_writes_override": 1},
            {"p4_raw_firmware_bytes_leaked_override": 4},
        ):
            p4, _ = _evaluate_pillar_4(raw_vm, RealHwMilestone254FaultInjection(**kw))
            self.assertFalse(p4.passed, kw)

    def test_37_pillar4_fails_on_stage47_var_shutter_or_250th_milestone_or_cnflasha_tamper(self) -> None:
        raw_vm = self._unpack_clean_raw()[4]
        raw_vm["stage47_realhw_framing_usbpower_lun_antiflicker_hil"]["fx3_has_var_shutter"] = True
        self.assertFalse(_evaluate_pillar_4(raw_vm, RealHwMilestone254FaultInjection())[0].passed)

        raw_vm2 = self._unpack_clean_raw()[4]
        raw_vm2["stage47_realhw_framing_usbpower_lun_antiflicker_hil"]["is_250th_phase_milestone"] = False
        self.assertFalse(_evaluate_pillar_4(raw_vm2, RealHwMilestone254FaultInjection())[0].passed)

        raw_vm3 = self._unpack_clean_raw()[4]
        raw_vm3["stage46_realhw_shoe_audio_wind_saveload_c3_hil"]["cnflasha_userspace_write_blocked"] = False
        self.assertFalse(_evaluate_pillar_4(raw_vm3, RealHwMilestone254FaultInjection())[0].passed)

    def test_38_pillar4_fails_when_future_stage48_fails(self) -> None:
        raw_vm = self._unpack_clean_raw()[4]
        raw_vm["stage48_broken_hil"] = {"all_checks_passed": False}
        self.assertFalse(_evaluate_pillar_4(raw_vm, RealHwMilestone254FaultInjection())[0].passed)

    # --- 7. Pillar 5: ALL 5 Bench Readiness Verifiers (`P186`, `P204`, `P216`, `P227`, `P248`) ---

    def test_39_pillar5_quintuple_bench_preflights_happy_path(self) -> None:
        b = self._unpack_clean_raw()
        p5, meta5 = _evaluate_pillar_5(*b[5:18], RealHwMilestone254FaultInjection())
        self.assertTrue(p5.passed, p5.errors)
        self.assertFalse(meta5["overall_ready_for_hardware_attach"])
        for off_k, sim_k in (
            ("p186_offline_go_no_go", "p186_sim_go_no_go"),
            ("p204_offline_go_no_go", "p204_sim_go_no_go"),
            ("p216_offline_go_no_go", "p216_sim_go_no_go"),
            ("p227_offline_go_no_go", "p227_sim_go_no_go"),
            ("p248_offline_go_no_go", "p248_sim_go_no_go"),
        ):
            self.assertEqual(meta5[off_k], GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT, off_k)
            self.assertEqual(meta5[sim_k], GO_NO_GO_DRY_RUN_SIMULATED_READY, sim_k)
        self.assertEqual(meta5["p248_sim_check_groups_passed"], 4)
        self.assertEqual(meta5["p248_h0_equals_h3_count"], 16)
        self.assertEqual(meta5["p204_e_nd_actuator_tx_count"], 0)
        self.assertFalse(meta5["p248_hardware_live_attachment_authorized"])

    def test_40_pillar5_rejects_phase248_imagedb_slot1_vault_and_touch_bench_tap_faults(self) -> None:
        b = self._unpack_clean_raw()
        p248_off, p248_sim = _worker_phase248(
            (
                str(DEFAULT_FX6_DONOR_LIB_DIR),
                str(DEFAULT_FX3_MODULES_DIR),
                True,
                {"imagedb_slot1_vault": True, "touch_bench_tap": True},
            )
        )
        p5, _ = _evaluate_pillar_5(
            *b[5:16], p248_off, p248_sim, RealHwMilestone254FaultInjection()
        )
        self.assertFalse(p5.passed)

    def test_41_pillar5_rejects_phase248_shoe_audio_sq_lockout_and_destructive_chord_faults(self) -> None:
        b = self._unpack_clean_raw()
        p248_off, p248_sim = _worker_phase248(
            (
                str(DEFAULT_FX6_DONOR_LIB_DIR),
                str(DEFAULT_FX3_MODULES_DIR),
                True,
                {"shoe_audio_sq_lockout": True, "lockop_destructive_chord": True},
            )
        )
        p5, _ = _evaluate_pillar_5(
            *b[5:16], p248_off, p248_sim, RealHwMilestone254FaultInjection()
        )
        self.assertFalse(p5.passed)

    def test_42_pillar5_rejects_phase248_usb_power_no_battery_and_h0_h3_drift_faults(self) -> None:
        b = self._unpack_clean_raw()
        p248_off, p248_sim = _worker_phase248(
            (
                str(DEFAULT_FX6_DONOR_LIB_DIR),
                str(DEFAULT_FX3_MODULES_DIR),
                True,
                {"usb_power_no_battery": True, "h0_h3_drift": True},
            )
        )
        p5, _ = _evaluate_pillar_5(
            *b[5:16], p248_off, p248_sim, RealHwMilestone254FaultInjection()
        )
        self.assertFalse(p5.passed)

    def test_43_pillar5_rejects_phase248_usb_packets_override(self) -> None:
        b = self._unpack_clean_raw()
        p5, _ = _evaluate_pillar_5(
            *b[5:18],
            RealHwMilestone254FaultInjection(p5_inject_p248_usb_packets_override=1),
        )
        self.assertFalse(p5.passed)

    def test_44_pillar5_rejects_phase248_offline_if_not_blocked_awaiting_tier0(self) -> None:
        b = list(self._unpack_clean_raw())
        b[16]["go_no_go"] = GO_NO_GO_DRY_RUN_SIMULATED_READY
        p5, _ = _evaluate_pillar_5(*b[5:18], RealHwMilestone254FaultInjection())
        self.assertFalse(p5.passed)

    def test_45_pillar5_rejects_overall_ready_for_hardware_attach_true_in_p248(self) -> None:
        b = list(self._unpack_clean_raw())
        b[17]["overall_ready_for_hardware_attach"] = True
        p5, _ = _evaluate_pillar_5(*b[5:18], RealHwMilestone254FaultInjection())
        self.assertFalse(p5.passed)

    # --- 8. Pillar 6: Live FX3 7.02 QEMU Rounds 28..50+ & < 50 KiB PNG Receipts ---

    def _clean_p1_to_p5_metas(self):
        cls = type(self)
        cached = getattr(cls, "_cached_p1_to_p5_metas", None)
        if cached is None:
            b = self.raw_bundle
            f = RealHwMilestone254FaultInjection()
            p1 = _evaluate_pillar_1(b[0], b[1])
            _, m2 = _evaluate_pillar_2(b[2], f)
            _, m3 = _evaluate_pillar_3(b[3], f)
            _, m4 = _evaluate_pillar_4(b[4], f)
            _, m5 = _evaluate_pillar_5(*b[5:18], f)
            cached = (p1.evidence, m2, m3, m4, m5)
            cls._cached_p1_to_p5_metas = cached
        return cached

    def test_46_pillar6_rounds_28_to_50_at_least_23_rounds_69_runs_46_pngs(self) -> None:
        m1, m2, m3, m4, m5 = self._clean_p1_to_p5_metas()
        p6, meta6 = _evaluate_pillar_6(
            repo_root=REPO_ROOT,
            use_clean_room=True,
            faults=RealHwMilestone254FaultInjection(),
            p1_meta=m1,
            p2_meta=m2,
            p3_meta=m3,
            p4_meta=m4,
            p5_meta=m5,
        )
        self.assertTrue(p6.passed, p6.errors)
        self.assertGreaterEqual(meta6["qemu_rounds_verified"], 23)
        self.assertGreaterEqual(meta6["qemu_runs_verified"], 69)
        self.assertGreaterEqual(meta6["qemu_png_receipts_verified"], 46)
        self.assertLess(meta6["qemu_png_max_bytes"], PNG_MAX_SIZE_50KIB_BYTES)
        self.assertEqual(meta6["qemu_raw_firmware_bytes_leaked"], 0)
        for rnum in (48, 49, 50):
            self.assertEqual(meta6["qemu_round_runs_by_round"][f"r{rnum}"], 3)

    def test_47_pillar6_committed_round48_to_50_png_headers_under_50kib(self) -> None:
        for rnum in range(48, 51):
            for rel in ROUND28_TO_50_PNG_RECEIPTS[rnum]:
                p = REPO_ROOT / rel
                if p.is_file():
                    raw = p.read_bytes()
                    self.assertTrue(raw.startswith(PNG_MAGIC_BYTES), rel)
                    self.assertLess(len(raw), PNG_MAX_SIZE_50KIB_BYTES, rel)

    def test_48_pillar6_forward_compatible_with_round51_directory_discovery(self) -> None:
        m1, m2, m3, m4, m5 = self._clean_p1_to_p5_metas()
        with tempfile.TemporaryDirectory() as tmp:
            tmp_root = Path(tmp)
            r51_dir = tmp_root / "reports" / "2026-11-16-round51-realhw-future-wave40-qemu"
            assets_dir = r51_dir / "assets"
            assets_dir.mkdir(parents=True, exist_ok=True)
            for name in ("r51a-alpha.png", "r51a-composited.png"):
                (assets_dir / name).write_bytes(PNG_MAGIC_BYTES + b"\x00" * 128)
            summary = {
                "schema": "fx6-on-fx3-round51-realhw-future-wave40-qemu-v1",
                "round": 51,
                "kernel_version": "Linux version 4.9.337-scel+ (clean-room-synthetic)",
                "raw_firmware_bytes_leaked": 0,
                "runs": {
                    "r51a_run": {"nop_count": 0, "crashes": 0, "emmc_write_count": 0, "stage_b": {"manifest_count": 13}},
                    "r51b_run": {"nop_count": None, "crashes": 0, "emmc_write_count": 0, "stage_b": {"manifest_count": 13}},
                    "r51c_run": {"nop_count": None, "crashes": 0, "emmc_write_count": 0, "stage_b": {"manifest_count": 13}},
                },
                "r51_realhw_future_wave40_audit": {
                    "all_3_runs_crashes_zero": True,
                    "all_3_runs_emmc_write_zero": True,
                    "fx3_has_var_shutter": False,
                },
            }
            (r51_dir / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
            p6, meta6 = _evaluate_pillar_6(
                repo_root=tmp_root,
                use_clean_room=True,
                faults=RealHwMilestone254FaultInjection(),
                p1_meta=m1,
                p2_meta=m2,
                p3_meta=m3,
                p4_meta=m4,
                p5_meta=m5,
            )
            self.assertTrue(p6.passed, p6.errors)
            self.assertEqual(meta6["qemu_rounds_verified"], 24)
            self.assertEqual(meta6["qemu_runs_verified"], 72)
            self.assertEqual(meta6["qemu_png_receipts_verified"], 48)

    def test_49_pillar6_forward_compatible_round51_rejects_bad_audit_flag_or_kernel(self) -> None:
        m1, m2, m3, m4, m5 = self._clean_p1_to_p5_metas()
        with tempfile.TemporaryDirectory() as tmp:
            tmp_root = Path(tmp)
            r51_dir = tmp_root / "reports" / "2026-11-16-round51-realhw-broken-qemu"
            r51_dir.mkdir(parents=True, exist_ok=True)
            summary = {
                "schema": "fx6-on-fx3-round51-broken-v1",
                "round": 51,
                "kernel_version": "Linux version 4.9.337-scel+ (clean-room-synthetic)",
                "raw_firmware_bytes_leaked": 0,
                "runs": {
                    "r51a_run": {"nop_count": 0, "crashes": 0, "emmc_write_count": 0, "stage_b": {"manifest_count": 13}},
                },
                "r51_broken_audit": {
                    "all_3_runs_crashes_zero": True,
                    "fx3_has_var_shutter": True,
                },
            }
            (r51_dir / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
            p6, _ = _evaluate_pillar_6(
                repo_root=tmp_root,
                use_clean_room=True,
                faults=RealHwMilestone254FaultInjection(),
                p1_meta=m1,
                p2_meta=m2,
                p3_meta=m3,
                p4_meta=m4,
                p5_meta=m5,
            )
            self.assertFalse(p6.passed)

    def test_50_pillar6_fails_on_round48_to_50_schema_tamper(self) -> None:
        m1, m2, m3, m4, m5 = self._clean_p1_to_p5_metas()
        for rnum in (48, 49, 50):
            p6, _ = _evaluate_pillar_6(
                repo_root=REPO_ROOT,
                use_clean_room=True,
                faults=RealHwMilestone254FaultInjection(p6_tamper_schema_round_num=rnum),
                p1_meta=m1,
                p2_meta=m2,
                p3_meta=m3,
                p4_meta=m4,
                p5_meta=m5,
            )
            self.assertFalse(p6.passed, rnum)

    def test_51_pillar6_fails_on_round50_nop_crash_emmc_write_or_raw_leak(self) -> None:
        m1, m2, m3, m4, m5 = self._clean_p1_to_p5_metas()
        for fkw in (
            {"p6_round_nop_override_num": 50, "p6_round_nop_count_override": 1},
            {"p6_round_crash_override_num": 50, "p6_round_crashes_override": 1},
            {"p6_round_emmc_override_num": 50, "p6_round_emmc_writes_override": 1},
            {"p6_raw_firmware_bytes_leaked_override": 8},
        ):
            p6, _ = _evaluate_pillar_6(
                repo_root=REPO_ROOT,
                use_clean_room=True,
                faults=RealHwMilestone254FaultInjection(**fkw),
                p1_meta=m1,
                p2_meta=m2,
                p3_meta=m3,
                p4_meta=m4,
                p5_meta=m5,
            )
            self.assertFalse(p6.passed, fkw)

    def test_52_pillar6_fails_when_png_receipt_reaches_or_exceeds_50kib_ceiling(self) -> None:
        m1, m2, m3, m4, m5 = self._clean_p1_to_p5_metas()
        p6, _ = _evaluate_pillar_6(
            repo_root=REPO_ROOT,
            use_clean_room=True,
            faults=RealHwMilestone254FaultInjection(
                p6_png_size_override_round_num=50,
                p6_png_size_override_bytes=PNG_MAX_SIZE_50KIB_BYTES,
            ),
            p1_meta=m1,
            p2_meta=m2,
            p3_meta=m3,
            p4_meta=m4,
            p5_meta=m5,
        )
        self.assertFalse(p6.passed)

    def test_53_pillar6_cross_pillar_p248_h0_h3_and_cnflasha_invariants_fail_closed(self) -> None:
        m1, m2, m3, m4, m5 = self._clean_p1_to_p5_metas()
        m5_bad = dict(m5)
        m5_bad["p248_h0_equals_h3_count"] = 15
        p6_bad5, _ = _evaluate_pillar_6(
            repo_root=REPO_ROOT,
            use_clean_room=True,
            faults=RealHwMilestone254FaultInjection(),
            p1_meta=m1,
            p2_meta=m2,
            p3_meta=m3,
            p4_meta=m4,
            p5_meta=m5_bad,
        )
        self.assertFalse(p6_bad5.passed)

        m2_bad = dict(m2)
        m2_bad["cnflasha_userspace_write_blocked"] = False
        p6_bad2, _ = _evaluate_pillar_6(
            repo_root=REPO_ROOT,
            use_clean_room=True,
            faults=RealHwMilestone254FaultInjection(),
            p1_meta=m1,
            p2_meta=m2_bad,
            p3_meta=m3,
            p4_meta=m4,
            p5_meta=m5,
        )
        self.assertFalse(p6_bad2.passed)

    # --- 9. Fail-Closed Verifier & CLI `verify-milestone-254` ---

    def test_54_verifier_rejects_non_mapping_payload(self) -> None:
        self.assertFalse(verify_realhw_milestone254_master_gate("not-a-dict").valid)
        self.assertFalse(verify_realhw_milestone254_master_gate(123).valid)
        self.assertFalse(verify_realhw_milestone254_master_gate(None).valid)  # type: ignore[arg-type]

    def test_55_verifier_rejects_sha256_tamper_and_schema_tamper(self) -> None:
        d = self.rep_clean.to_dict()
        d["milestone254_sha256"] = "f" * 64
        self.assertFalse(verify_realhw_milestone254_master_gate(d).valid)

        d2 = self.rep_clean.to_dict()
        d2["schema"] = "wrong_schema_v1"
        d2["milestone254_sha256"] = compute_milestone254_sha256(d2)
        self.assertFalse(verify_realhw_milestone254_master_gate(d2).valid)

    def test_56_verifier_rejects_redline_tamper_even_when_rehashed(self) -> None:
        for k, v in (
            ("overall_ready_for_hardware_attach", True),
            ("hardware_live_attachment_authorized", True),
            ("persistent_emmc_writes_authorized", True),
            ("spi_nor_write_authorized", True),
            ("el3_payload_transmit_authorized", True),
            ("cnflasha_userspace_write_blocked", False),
            ("usb_packets_transmitted", 1),
            ("physical_device_writes", 1),
            ("raw_firmware_bytes_leaked", 1),
            ("otp_fuse_touches", 1),
            ("rpmb_counter_increments", 1),
            ("passive_tx_bytes_emitted", 1),
            ("p248_hardware_live_attachment_authorized", True),
        ):
            d = self.rep_clean.to_dict()
            d[k] = v
            d["milestone254_sha256"] = compute_milestone254_sha256(d)
            self.assertFalse(verify_realhw_milestone254_master_gate(d).valid, k)

    def test_57_verifier_accepts_forward_compatible_higher_counts(self) -> None:
        d = self.rep_clean.to_dict()
        d["gate96_total_gates"] = 98
        d["gate96_offline_verified"] = 95
        d["gate96_simulated_verified"] = 98
        d["recovery_pillar_count"] = 42
        d["recovery_pillars_passed"] = 42
        d["auditors_total"] = 46
        d["auditors_passed"] = 46
        d["vm_stages_total"] = 48
        d["vm_stages_passed"] = 48
        d["qemu_rounds_total"] = 24
        d["qemu_rounds_verified"] = 24
        d["qemu_runs_total"] = 72
        d["qemu_runs_verified"] = 72
        d["qemu_png_receipts_total"] = 48
        d["qemu_png_receipts_verified"] = 48
        d["milestone254_sha256"] = compute_milestone254_sha256(d)
        v = verify_realhw_milestone254_master_gate(d)
        self.assertTrue(v.valid, v.errors)

    def test_58_verifier_rejects_sub_threshold_or_mismatched_counts_and_raw_bytes(self) -> None:
        for k, v in (
            ("gate96_simulated_verified", 95),
            ("recovery_pillar_count", 40),
            ("auditors_passed", 44),
            ("vm_stages_passed", 46),
            ("p248_sim_check_groups_passed", 3),
            ("qemu_rounds_verified", 22),
            ("qemu_runs_verified", 68),
            ("qemu_png_receipts_verified", 45),
            ("qemu_png_max_bytes", PNG_MAX_SIZE_50KIB_BYTES),
        ):
            d = self.rep_clean.to_dict()
            d[k] = v
            d["milestone254_sha256"] = compute_milestone254_sha256(d)
            self.assertFalse(verify_realhw_milestone254_master_gate(d).valid, k)

        d_raw = self.rep_clean.to_dict()
        d_raw["pillars"][0]["summary"] = "leaked b'\\x7fELF'"
        d_raw["milestone254_sha256"] = compute_milestone254_sha256(d_raw)
        self.assertFalse(verify_realhw_milestone254_master_gate(d_raw).valid)

    def test_59_cli_verify_milestone_254_summary_and_out_alias_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            out_json = tmp_path / "m254.json"
            out_md = tmp_path / "m254.md"
            buf = io.StringIO()
            with (
                mock.patch(
                    "fx6_closure.realhw_milestone254_master_gate.evaluate_realhw_milestone254_master_gate",
                    return_value=self.rep_clean,
                ),
                mock.patch("sys.stdout", buf),
            ):
                rc = fx6_cli_main(
                    [
                        "verify-milestone-254",
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
            self.assertIn("schema=realhw_milestone254_master_gate_v1", text)
            self.assertIn("cnflasha_ro=True", text)
            self.assertIn("p248_off=BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT", text)
            self.assertIn("p248_sim=DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH", text)
            self.assertIn("ready_attach=False", text)
            self.assertIsNotNone(re.search(r"gate96=(\d+)/(\d+)", text))
            self.assertIsNotNone(re.search(r"qemu=(\d+)/(\d+)\((\d+)/(\d+)\)", text))
            self.assertTrue(out_json.is_file())
            self.assertTrue(out_md.is_file())
            self.assertTrue(
                verify_realhw_milestone254_master_gate(json.loads(out_json.read_text())).valid
            )

    def test_60_cli_verify_milestone_254_json_stdout_and_failure_exit_code(self) -> None:
        buf = io.StringIO()
        with (
            mock.patch(
                "fx6_closure.realhw_milestone254_master_gate.evaluate_realhw_milestone254_master_gate",
                return_value=self.rep_clean,
            ),
            mock.patch("sys.stdout", buf),
        ):
            rc = fx6_cli_main(["verify-milestone-254", "--clean-room", "--json"])
        self.assertEqual(rc, 0)
        parsed = json.loads(buf.getvalue())
        self.assertEqual(parsed["schema"], REALHW_MILESTONE254_SCHEMA)
        self.assertEqual(parsed["usb_packets_transmitted"], 0)
        self.assertFalse(parsed["overall_ready_for_hardware_attach"])

        bad_rep = replace(
            self.rep_clean,
            all_pillars_milestone_ready=False,
            status=STATUS_FAIL_CLOSED,
            passed_pillar_count=5,
            failed_pillar_ids=("P1",),
            milestone254_sha256="0" * 64,
        )
        buf2 = io.StringIO()
        with (
            mock.patch(
                "fx6_closure.realhw_milestone254_master_gate.evaluate_realhw_milestone254_master_gate",
                return_value=bad_rep,
            ),
            mock.patch("sys.stdout", buf2),
        ):
            rc2 = fx6_cli_main(["verify-milestone-254", "--force-clean-room"])
        self.assertEqual(rc2, 1)
        self.assertIn("status=FAILED", buf2.getvalue())

    def test_61_verify_milestone_254_cli_direct_helper_entrypoint(self) -> None:
        buf = io.StringIO()
        with (
            mock.patch(
                "fx6_closure.realhw_milestone254_master_gate.evaluate_realhw_milestone254_master_gate",
                return_value=self.rep_clean,
            ),
            mock.patch("sys.stdout", buf),
        ):
            rc = verify_milestone_254_cli(["--clean-room", "--json"])
        self.assertEqual(rc, 0)
        parsed = json.loads(buf.getvalue())
        self.assertEqual(parsed["schema"], REALHW_MILESTONE254_SCHEMA)
        self.assertTrue(parsed["cnflasha_userspace_write_blocked"])

    def test_62_synthetic_clean_room_kwarg_alias_and_suite_runtime_budget(self) -> None:
        rep = evaluate_milestone_254_master_gate(
            synthetic_clean_room=True,
            _raw_bundle_override=self._unpack_clean_raw(),
        )
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(rep.all_pillars_milestone_ready)
        self.assertLess(self.default_elapsed_s, 7.5)


if __name__ == "__main__":
    unittest.main()
