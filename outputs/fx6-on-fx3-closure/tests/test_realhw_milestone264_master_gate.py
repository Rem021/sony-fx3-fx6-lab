"""Phase 264 dual-mode unit tests for Grand Milestone Phase 264 6-Pillar Real-Hardware Master Gate."""

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
    RealHwMilestone254FaultInjection,
    _worker_phase248,
)
from fx6_closure.realhw_milestone264_master_gate import (  # noqa: E402
    CALIBRATION_MUTATION_BYTES,
    CNFLASHA_USERSPACE_WRITE_BLOCKED,
    CP_MUTATION_BYTES,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    EMMC_WRITE_COUNT,
    E_ND_ACTUATOR_TX_COUNT,
    FIRMWARE_LAB_45_AUDITOR_KEYS,
    HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    ISP_WRITE_AUTHORIZED,
    MILESTONE264_SCHEMA_VERSION,
    OTP_FUSE_TOUCHES,
    OTP_FUSE_WRITES,
    OVERALL_READY_FOR_HARDWARE_ATTACH,
    P264_PHYSICAL_DEVICE_WRITES,
    P264_PILLAR_IDS,
    P264_PILLAR_SPECS,
    P264_PNG_MAX_SIZE_BYTES,
    P264_RAW_FIRMWARE_BYTES_LEAKED,
    P264_SCHEMA,
    P264_STATUS_FAIL_CLOSED,
    P264_STATUS_MILESTONE_READY,
    P264_VERSION,
    P8_CP_MUTATION_FORBIDDEN,
    PASSIVE_TX_BYTES,
    PASSIVE_TX_BYTES_EMITTED,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHASE_264_VERSION,
    PHYSICAL_DEVICE_WRITES,
    PHYSICAL_USB_PACKETS_EMITTED,
    PILLAR_IDS,
    PILLAR_SPECS,
    PNG_MAGIC_BYTES,
    PNG_MAX_SIZE_50KIB_BYTES,
    PNG_MAX_SIZE_BYTES,
    RAW_FIRMWARE_BYTES_LEAKED,
    REALHW_MILESTONE264_SCHEMA,
    RECOVERY_44_PILLAR_IDS,
    ROUND28_TO_52_PNG_RECEIPTS,
    ROUND28_TO_52_SPECS,
    ROUND51_EXPECTED_SCHEMA,
    ROUND52_EXPECTED_SCHEMA,
    RPMB_COUNTER_INCREMENTS,
    RPMB_WRITES,
    SPI_NOR_WRITE_AUTHORIZED,
    STATUS_FAIL_CLOSED,
    STATUS_MILESTONE_READY,
    USB_OR_CAMERA_OPERATIONS,
    USB_PACKETS_TRANSMITTED,
    VM_COEMULATION_50_STAGE_KEYS,
    WBI_MUTATION_BYTES,
    WBI_P5_WRITE_AND_HIBERNATION_FORBIDDEN,
    RealHwMilestone264FaultInjection,
    RealHwMilestone264MasterGateReport,
    _collect_parallel_milestone264_results,
    _evaluate_pillar_1,
    _evaluate_pillar_2,
    _evaluate_pillar_3,
    _evaluate_pillar_4,
    _evaluate_pillar_5,
    _evaluate_pillar_6,
    _fault_to_102gate_worker_dict,
    _normalize_44pillar_fault_id,
    _worker_102gate_single,
    _worker_phase261,
    _worker_recovery_44pillar,
    build_realhw_milestone264_master_gate_report,
    compute_milestone264_sha256,
    evaluate_milestone264_master_gate,
    evaluate_milestone_264_master_gate,
    evaluate_realhw_milestone264_master_gate,
    render_milestone264_markdown,
    verify_milestone_264_cli,
    verify_milestone_264_master_gate,
    verify_realhw_milestone264_master_gate,
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

    g101_fdict = _fault_to_102gate_worker_dict(
        RealHwMilestone264FaultInjection(
            p1_auto_slow_shutter_breathing_kwargs={"auto_slow_shutter_lockout_bypass_events": 1},
            p1_request_persistent_writes=True,
        )
    )
    fx6_s = str(DEFAULT_FX6_DONOR_LIB_DIR)
    fx3_s = str(DEFAULT_FX3_MODULES_DIR)
    ctx = mp.get_context("fork")
    with ProcessPoolExecutor(max_workers=4, mp_context=ctx) as pool:
        fut_g101 = pool.submit(_worker_102gate_single, (str(REPO_ROOT), True, True, g101_fdict))
        fut_p44 = pool.submit(_worker_recovery_44pillar, (True, "pillar_44"))
        fut_261_ab = pool.submit(
            _worker_phase261,
            (fx6_s, fx3_s, True, {"diffset_customkey_vault": True, "autoslow_hdmi_rec_ctrl": True}),
        )
        fut_261_cd = pool.submit(
            _worker_phase261,
            (fx6_s, fx3_s, True, {"apsc_4k_or_bodydata_flash": True, "end_uart_or_copyright_pii": True}),
        )
        fut_261_drift = pool.submit(_worker_phase261, (fx6_s, fx3_s, True, {"h0_h3_drift": True}))
        fut_248_bad = pool.submit(_worker_phase248, (fx6_s, fx3_s, True, {"imagedb_slot1_vault": True}))
        bad_g101 = fut_g101.result()
        bad_p44 = fut_p44.result()
        p261_bad_ab = fut_261_ab.result()
        p261_bad_cd = fut_261_cd.result()
        p261_bad_drift = fut_261_drift.result()
        p248_bad = fut_248_bad.result()
    conn.send((bad_g101, bad_p44, p261_bad_ab, p261_bad_cd, p261_bad_drift, p248_bad))
    conn.close()


class TestRealHwMilestone264MasterGate(unittest.TestCase):
    """Comprehensive 66 dual-mode tests for Grand Milestone Phase 264 (< 6.5s donor / < 3.5s clean)."""

    raw_bundle: tuple
    rep_default: RealHwMilestone264MasterGateReport
    rep_clean: RealHwMilestone264MasterGateReport
    bad_sim_g101: dict
    bad_rec_44: dict
    p261_bad_ab: tuple
    p261_bad_cd: tuple
    p261_bad_drift: tuple
    p248_bad: tuple
    default_elapsed_s: float

    @classmethod
    def setUpClass(cls) -> None:
        import multiprocessing as mp

        t0 = time.monotonic()
        ctx = mp.get_context("fork")
        if not _is_forced_clean_room():
            cls.rep_default = evaluate_milestone_264_master_gate()
        recv_conn, send_conn = ctx.Pipe(duplex=False)
        proc = ctx.Process(
            target=_fork_child_fault_fixtures_only,
            args=(send_conn,),
            daemon=False,
        )
        proc.start()
        send_conn.close()
        try:
            cls.raw_bundle = _collect_parallel_milestone264_results(
                repo_root=REPO_ROOT,
                fx6_lib_dir=DEFAULT_FX6_DONOR_LIB_DIR,
                fx3_modules_dir=DEFAULT_FX3_MODULES_DIR,
                use_clean_room=True,
                faults=RealHwMilestone264FaultInjection(),
            )
            (
                cls.bad_sim_g101,
                cls.bad_rec_44,
                cls.p261_bad_ab,
                cls.p261_bad_cd,
                cls.p261_bad_drift,
                cls.p248_bad,
            ) = recv_conn.recv()
        finally:
            recv_conn.close()
            proc.join(timeout=30)
        cls.rep_clean = evaluate_milestone_264_master_gate(
            force_clean_room=True,
            _raw_bundle_override=cls.raw_bundle,
        )
        if _is_forced_clean_room():
            cls.rep_default = cls.rep_clean
        cls.default_elapsed_s = time.monotonic() - t0

    def _unpack_clean_raw(self):
        return _LazyDeepcopyBundle(self.raw_bundle)

    # --- 1. Constants, Exports & Schema ---

    def test_01_schema_and_version_constants(self) -> None:
        self.assertEqual(REALHW_MILESTONE264_SCHEMA, "realhw_milestone264_master_gate_v1")
        self.assertEqual(MILESTONE264_SCHEMA_VERSION, REALHW_MILESTONE264_SCHEMA)
        self.assertEqual(P264_SCHEMA, REALHW_MILESTONE264_SCHEMA)
        self.assertEqual(PHASE_264_VERSION, "264.0.0")
        self.assertEqual(P264_VERSION, "264.0.0")
        self.assertEqual(PILLAR_IDS, ("P1", "P2", "P3", "P4", "P5", "P6"))
        self.assertEqual(P264_PILLAR_IDS, PILLAR_IDS)
        self.assertEqual(len(PILLAR_SPECS), 6)
        self.assertEqual(P264_PILLAR_SPECS, PILLAR_SPECS)
        self.assertGreaterEqual(len(RECOVERY_44_PILLAR_IDS), 44)
        self.assertGreaterEqual(len(FIRMWARE_LAB_45_AUDITOR_KEYS), 45)
        self.assertGreaterEqual(len(VM_COEMULATION_50_STAGE_KEYS), 50)
        self.assertGreaterEqual(len(ROUND28_TO_52_SPECS), 25)
        self.assertEqual(PNG_MAX_SIZE_50KIB_BYTES, 51200)
        self.assertEqual(PNG_MAX_SIZE_BYTES, 51200)
        self.assertEqual(P264_PNG_MAX_SIZE_BYTES, 51200)

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
        self.assertEqual(P264_STATUS_MILESTONE_READY, STATUS_MILESTONE_READY)
        self.assertEqual(P264_STATUS_FAIL_CLOSED, STATUS_FAIL_CLOSED)
        for zero_const in (
            USB_PACKETS_TRANSMITTED,
            PHYSICAL_USB_PACKETS_EMITTED,
            PHYSICAL_DEVICE_WRITES,
            P264_PHYSICAL_DEVICE_WRITES,
            RAW_FIRMWARE_BYTES_LEAKED,
            P264_RAW_FIRMWARE_BYTES_LEAKED,
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
            "MILESTONE264_PHYSICAL_DEVICE_WRITES",
            "MILESTONE264_PILLAR_IDS",
            "MILESTONE264_PILLAR_SPECS",
            "MILESTONE264_PNG_MAX_SIZE_BYTES",
            "MILESTONE264_RAW_FIRMWARE_BYTES_LEAKED",
            "MILESTONE264_SCHEMA_VERSION",
            "P264_PHYSICAL_DEVICE_WRITES",
            "P264_PILLAR_IDS",
            "P264_PILLAR_SPECS",
            "P264_PNG_MAX_SIZE_BYTES",
            "P264_RAW_FIRMWARE_BYTES_LEAKED",
            "P264_SCHEMA",
            "P264_STATUS_FAIL_CLOSED",
            "P264_STATUS_MILESTONE_READY",
            "P264_VERSION",
            "PHASE_264_VERSION",
            "REALHW_MILESTONE264_SCHEMA",
            "RECOVERY_44_PILLAR_IDS",
            "ROUND28_TO_52_PNG_RECEIPTS",
            "ROUND28_TO_52_SPECS",
            "ROUND51_EXPECTED_SCHEMA",
            "ROUND52_EXPECTED_SCHEMA",
            "STATUS_MILESTONE264_FAIL_CLOSED",
            "STATUS_MILESTONE264_READY",
            "VM_COEMULATION_50_STAGE_KEYS",
            "Milestone264PillarResult",
            "RealHwMilestone264FaultInjection",
            "RealHwMilestone264MasterGateReport",
            "RealHwMilestone264VerifyResult",
            "build_realhw_milestone264_master_gate_report",
            "compute_milestone264_sha256",
            "evaluate_milestone264_master_gate",
            "evaluate_milestone_264_master_gate",
            "evaluate_realhw_milestone264_master_gate",
            "render_milestone264_markdown",
            "verify_milestone_264_cli",
            "verify_milestone_264_master_gate",
            "verify_realhw_milestone264_master_gate",
        }
        self.assertTrue(expected.issubset(set(fx6_closure.__all__)))
        for sym in expected:
            self.assertTrue(hasattr(fx6_closure, sym), sym)
        self.assertEqual(fx6_closure.REALHW_MILESTONE254_SCHEMA, "realhw_milestone254_master_gate_v1")
        self.assertEqual(fx6_closure.REALHW_MILESTONE233_SCHEMA, "realhw_milestone233_master_gate_v1")
        self.assertEqual(fx6_closure.REALHW_MILESTONE221_SCHEMA, "realhw_milestone221_master_gate_v1")

    def test_04_builder_and_verifier_aliases_point_to_canonical_functions(self) -> None:
        self.assertIs(build_realhw_milestone264_master_gate_report, evaluate_realhw_milestone264_master_gate)
        self.assertIs(evaluate_milestone_264_master_gate, evaluate_realhw_milestone264_master_gate)
        self.assertIs(evaluate_milestone264_master_gate, evaluate_realhw_milestone264_master_gate)
        self.assertIs(verify_milestone_264_master_gate, verify_realhw_milestone264_master_gate)

    def test_05_round51_and_round52_specs_and_png_pairs_registered(self) -> None:
        by_num = {s.round_num: s for s in ROUND28_TO_52_SPECS}
        for rnum, exp_schema in (
            (51, ROUND51_EXPECTED_SCHEMA),
            (52, ROUND52_EXPECTED_SCHEMA),
        ):
            self.assertIn(rnum, by_num)
            self.assertEqual(by_num[rnum].expected_schema, exp_schema)
            self.assertEqual(len(by_num[rnum].run_specs), 3)
            self.assertIn(rnum, ROUND28_TO_52_PNG_RECEIPTS)
            self.assertEqual(len(ROUND28_TO_52_PNG_RECEIPTS[rnum]), 2)
        for _, exp_faithful in by_num[51].run_specs:
            self.assertEqual(exp_faithful, 1)
        for _, exp_faithful in by_num[52].run_specs:
            self.assertEqual(exp_faithful, 1)

    def test_06_normalize_44pillar_fault_id_resolves_short_and_full_ids(self) -> None:
        self.assertIsNone(_normalize_44pillar_fault_id(None))
        self.assertIsNone(_normalize_44pillar_fault_id(""))
        for pnum in (42, 43, 44):
            full_id = RECOVERY_44_PILLAR_IDS[pnum - 1]
            self.assertEqual(_normalize_44pillar_fault_id(f"pillar_{pnum}"), full_id)
            self.assertEqual(_normalize_44pillar_fault_id(full_id), full_id)
        self.assertEqual(
            _normalize_44pillar_fault_id("pillar_44"),
            "pillar_44_apsc_s35_face_eye_af_version_vault",
        )

    # --- 2. End-to-End Dual-Mode Reports, Determinism & Markdown ---

    def test_07_default_mode_report_all_6_pillars_ready(self) -> None:
        rep = self.rep_default
        self.assertTrue(rep.all_pillars_milestone_ready, rep.errors)
        self.assertEqual(rep.status, STATUS_MILESTONE_READY)
        self.assertEqual(rep.passed_pillar_count, 6)
        self.assertEqual(rep.failed_pillar_ids, ())
        v = verify_realhw_milestone264_master_gate(rep)
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
        self.assertEqual(rep.e_nd_actuator_tx_count, 0)
        self.assertEqual(rep.otp_fuse_touches, 0)
        self.assertEqual(rep.rpmb_counter_increments, 0)
        self.assertEqual(rep.passive_tx_bytes_emitted, 0)
        self.assertTrue(verify_realhw_milestone264_master_gate(rep.to_dict()).valid)

    def test_09_forward_compatible_lower_bounds_on_clean_report(self) -> None:
        rep = self.rep_clean
        self.assertGreaterEqual(rep.gate102_total_gates, 102)
        self.assertGreaterEqual(rep.gate102_offline_verified, 99)
        self.assertEqual(rep.gate102_offline_verified, rep.gate102_total_gates - 3)
        self.assertEqual(rep.gate102_simulated_verified, rep.gate102_total_gates)
        self.assertTrue(rep.gate102_all_verified)
        self.assertGreaterEqual(rep.recovery_pillar_count, 44)
        self.assertEqual(rep.recovery_pillars_passed, rep.recovery_pillar_count)
        self.assertGreaterEqual(rep.auditors_passed, 45)
        self.assertEqual(rep.auditors_passed, rep.auditors_total)
        self.assertGreaterEqual(rep.vm_stages_passed, 50)
        self.assertEqual(rep.vm_stages_passed, rep.vm_stages_total)
        self.assertGreaterEqual(rep.qemu_rounds_verified, 25)
        self.assertGreaterEqual(rep.qemu_runs_verified, 75)
        self.assertGreaterEqual(rep.qemu_png_receipts_verified, 50)
        self.assertLess(rep.qemu_png_max_bytes, PNG_MAX_SIZE_50KIB_BYTES)
        self.assertEqual(rep.h0_equals_h3_count, 16)
        self.assertEqual(rep.e_nd_actuator_tx_count, 0)
        self.assertEqual(rep.p261_e_nd_uart_bytes_transmitted, 0)

    def test_10_deterministic_json_and_sha256_recomputation(self) -> None:
        j1 = self.rep_clean.to_deterministic_json()
        parsed = json.loads(j1)
        self.assertEqual(compute_milestone264_sha256(parsed), self.rep_clean.milestone264_sha256)
        rep2 = evaluate_milestone_264_master_gate(
            force_clean_room=True,
            _raw_bundle_override=self._unpack_clean_raw(),
        )
        self.assertEqual(rep2.milestone264_sha256, self.rep_clean.milestone264_sha256)

    def test_11_no_raw_bytes_repr_in_serialized_reports(self) -> None:
        for rep in (self.rep_default, self.rep_clean):
            self.assertIsNone(re.search(_RAW_BYTES_REPR_REGEX, rep.to_deterministic_json()))

    def test_12_markdown_renderer_contains_bilingual_headers_and_6_pillars(self) -> None:
        md = render_milestone264_markdown(self.rep_clean)
        for token in (
            "Grand Milestone Phase 264",
            "realhw_milestone264_master_gate_v1",
            "MILESTONE_264_PREBENCH_MASTER_VERIFIED",
            "102-Gate Preflight",
            "44-Pillar Recovery Master",
            "50+ Stage VM HIL",
            "Ph261=",
            "Rounds 28..52+",
            "| `P1` |",
            "| `P6` |",
        ):
            self.assertIn(token, md)

    # --- 3. Pillar 1: >= 102 Safety Gates (`fx3_safety.evaluate_102gate_preflight`) ---

    def test_13_pillar1_102gate_happy_path_and_g63_to_g102_valid(self) -> None:
        raw_off, raw_sim = self._unpack_clean_raw()[:2]
        p1 = _evaluate_pillar_1(raw_off, raw_sim)
        self.assertTrue(p1.passed, p1.errors)
        self.assertGreaterEqual(p1.evidence["offline_verified_gates"], 99)
        self.assertGreaterEqual(p1.evidence["simulated_verified_gates"], 102)
        self.assertTrue(p1.evidence["all_102_gates_verified"])
        for idx in range(63, 103):
            self.assertTrue(p1.evidence["g63_to_g102_valid"][f"g{idx}"], f"g{idx}")

    def test_14_pillar1_forward_compatible_with_104_gates(self) -> None:
        raw_off, raw_sim = self._unpack_clean_raw()[:2]
        raw_off["total_gates"] = 104
        raw_off["verified_gates"] = 101
        raw_sim["total_gates"] = 104
        raw_sim["verified_gates"] = 104
        p1 = _evaluate_pillar_1(raw_off, raw_sim)
        self.assertTrue(p1.passed, p1.errors)

    def test_15_pillar1_fails_when_offline_tier0_gates_not_blocked(self) -> None:
        raw_off, raw_sim = self._unpack_clean_raw()[:2]
        raw_off["verified_gates"] = raw_off["total_gates"]
        raw_off["blocked_or_pending_gates"] = 0
        self.assertFalse(_evaluate_pillar_1(raw_off, raw_sim).passed)

    def test_16_pillar1_fails_when_all_102_gates_verified_false_in_dry_run(self) -> None:
        raw_off, raw_sim = self._unpack_clean_raw()[:2]
        raw_sim["all_102_gates_verified"] = False
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
        for field in (
            "usb_packets_transmitted",
            "raw_firmware_bytes_leaked",
            "g71_e_nd_actuator_tx_count",
        ):
            raw_off, raw_sim = self._unpack_clean_raw()[:2]
            raw_sim[field] = 1
            self.assertFalse(_evaluate_pillar_1(raw_off, raw_sim).passed, field)

    def test_19_pillar1_fails_when_any_g97_to_g102_gate_invalid(self) -> None:
        for gtag in ("g97", "g98", "g99", "g100", "g101", "g102"):
            raw_off, raw_sim = self._unpack_clean_raw()[:2]
            raw_sim["nested_g_valid"][gtag] = False
            p1 = _evaluate_pillar_1(raw_off, raw_sim)
            self.assertFalse(p1.passed, gtag)
            self.assertIn(gtag.upper(), p1.errors[-1])

    def test_20_pillar1_worker_live_g101_auto_slow_shutter_and_persistent_write_fault(self) -> None:
        raw_sim_bad = copy.deepcopy(self.bad_sim_g101)
        raw_off = self._unpack_clean_raw()[0]
        p1 = _evaluate_pillar_1(raw_off, raw_sim_bad)
        self.assertFalse(p1.passed)
        self.assertFalse(raw_sim_bad["nested_g_valid"]["g101"])

    def test_21_fault_to_102gate_worker_dict_propagates_g97_to_g102_and_m254_faults(self) -> None:
        f = RealHwMilestone264FaultInjection(
            p1_display_quality_bt_rmt_kwargs={"tier0_battery_high_display_violations": 1},
            p1_hdmi_reccontrol_4chaudio_kwargs={"hdmi_rec_ctrl_without_tc_violations": 1},
            m254_faults=RealHwMilestone254FaultInjection(p1_request_persistent_writes=True),
        )
        w = _fault_to_102gate_worker_dict(f)
        self.assertTrue(w["p1_request_persistent_writes"])
        self.assertEqual(
            w["p1_display_quality_bt_rmt_kwargs"],
            {"tier0_battery_high_display_violations": 1},
        )
        self.assertEqual(
            w["p1_hdmi_reccontrol_4chaudio_kwargs"],
            {"hdmi_rec_ctrl_without_tc_violations": 1},
        )

    # --- 4. Pillar 2: >= 44 Recovery Pillars (`evaluate_realhw_44pillar_recovery_master`) ---

    def test_22_pillar2_44pillar_happy_path_and_cnflasha_ro(self) -> None:
        rec_44 = self._unpack_clean_raw()[2]
        p2, meta2 = _evaluate_pillar_2(rec_44, RealHwMilestone264FaultInjection())
        self.assertTrue(p2.passed, p2.errors)
        self.assertGreaterEqual(meta2["recovery_pillar_count"], 44)
        self.assertEqual(meta2["recovery_pillars_passed"], meta2["recovery_pillar_count"])
        self.assertTrue(meta2["cnflasha_userspace_write_blocked"])
        self.assertFalse(p2.evidence["fx3_has_builtin_evf"])
        self.assertEqual(meta2["otp_fuse_writes"], 0)
        self.assertEqual(meta2["rpmb_writes"], 0)
        self.assertEqual(meta2["passive_tx_bytes"], 0)
        self.assertEqual(meta2["physical_usb_packets_emitted"], 0)
        self.assertEqual(meta2["physical_device_writes"], 0)
        self.assertEqual(meta2["raw_firmware_bytes_leaked"], 0)

    def test_23_pillar2_forward_compatible_with_45_pillars(self) -> None:
        rec_44 = self._unpack_clean_raw()[2]
        rec_44["pillar_count"] = 45
        rec_44["pillars_passed"] = 45
        rec_44["status"] = "VERIFIED_45OF45_PILLAR_RECOVERY_MASTER"
        p2, meta2 = _evaluate_pillar_2(rec_44, RealHwMilestone264FaultInjection())
        self.assertTrue(p2.passed, p2.errors)
        self.assertEqual(meta2["recovery_pillar_count"], 45)

    def test_24_pillar2_fails_when_cnflasha_userspace_write_unblocked(self) -> None:
        rec_44 = self._unpack_clean_raw()[2]
        p2, _ = _evaluate_pillar_2(
            rec_44,
            RealHwMilestone264FaultInjection(p2_cnflasha_write_unblocked_fault=True),
        )
        self.assertFalse(p2.passed)

    def test_25_pillar2_fails_on_otp_rpmb_passive_tx_usb_devwrite_or_leak_overrides(self) -> None:
        rec_44 = self._unpack_clean_raw()[2]
        for kw in (
            {"p2_otp_fuse_touches_override": 1},
            {"p2_rpmb_counter_increments_override": 1},
            {"p2_passive_tx_bytes_override": 4},
            {"p2_physical_usb_packets_override": 1},
            {"p2_physical_device_writes_override": 1},
            {"p2_raw_firmware_bytes_leaked_override": 8},
        ):
            p2, _ = _evaluate_pillar_2(rec_44, RealHwMilestone264FaultInjection(**kw))
            self.assertFalse(p2.passed, kw)

    def test_26_pillar2_fails_when_44a_or_44b_vault_subsuite_fails(self) -> None:
        for sub_key in (
            "pillar44_a_apsc_s35_face_eye_af_vault",
            "pillar44_b_version_readonly_bodydata_vault",
        ):
            rec_44 = self._unpack_clean_raw()[2]
            rec_44[sub_key]["passed"] = False
            self.assertFalse(
                _evaluate_pillar_2(rec_44, RealHwMilestone264FaultInjection())[0].passed,
                sub_key,
            )

    def test_27_pillar2_live_worker_fault_inject_pillar_44_fails_closed(self) -> None:
        bad_44 = copy.deepcopy(self.bad_rec_44)
        p2, _ = _evaluate_pillar_2(bad_44, RealHwMilestone264FaultInjection())
        self.assertFalse(p2.passed)

    def test_28_pillar2_fails_on_p42_to_p44_violation_counters_or_evf_or_var_shutter(self) -> None:
        for vkey in (
            "slot1_custom_key_vault_mutation_bytes",
            "auto_slow_shutter_angle_overlap_events",
            "apsc_s35_4k_or_raw_bypass_events",
            "bodydata_flash_from_version_dialog_attempts",
            "hdmi_clean_feed_eye_frame_baked_pixels",
        ):
            rec_44 = self._unpack_clean_raw()[2]
            rec_44[vkey] = 1
            self.assertFalse(
                _evaluate_pillar_2(rec_44, RealHwMilestone264FaultInjection())[0].passed,
                vkey,
            )
        for neg_flag in ("fx3_has_builtin_evf", "fx3_has_var_shutter"):
            rec_neg = self._unpack_clean_raw()[2]
            rec_neg[neg_flag] = True
            self.assertFalse(
                _evaluate_pillar_2(rec_neg, RealHwMilestone264FaultInjection())[0].passed,
                neg_flag,
            )

    # --- 5. Pillar 3: >= 45 Firmware Auditors (`outputs/fx3-firmware-lab`) ---

    def test_29_pillar3_45_auditors_happy_path(self) -> None:
        auditors = self._unpack_clean_raw()[3]
        p3, meta3 = _evaluate_pillar_3(auditors, RealHwMilestone264FaultInjection())
        self.assertTrue(p3.passed, p3.errors)
        self.assertGreaterEqual(meta3["auditor_count"], 45)
        self.assertEqual(meta3["passed_count"], meta3["auditor_count"])
        self.assertEqual(meta3["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(meta3["e_nd_actuator_tx_count"], 0)
        self.assertEqual(meta3["calibration_mutation_bytes"], 0)

    def test_30_pillar3_forward_compatible_with_46_plus_auditors(self) -> None:
        auditors = self._unpack_clean_raw()[3]
        auditors["realhw_future_wave44_audit"] = {"all_checks_passed": True}
        p3, meta3 = _evaluate_pillar_3(auditors, RealHwMilestone264FaultInjection())
        self.assertTrue(p3.passed, p3.errors)
        self.assertGreaterEqual(meta3["auditor_count"], 46)
        self.assertEqual(meta3["passed_count"], meta3["auditor_count"])

    def test_31_pillar3_fails_on_auditor45_guard_fault_or_subpillar_failure(self) -> None:
        auditors = self._unpack_clean_raw()[3]
        p3_fault, _ = _evaluate_pillar_3(
            auditors,
            RealHwMilestone264FaultInjection(p3_filesettings_tcregen_reclamp_guard_fault=True),
        )
        self.assertFalse(p3_fault.passed)

        auditors2 = self._unpack_clean_raw()[3]
        auditors2["realhw_filesettings_shotmark_tcregen_and_reclamp_audit"][
            "pillar_2_tc_regenerate_slot1_and_ext_lk"
        ]["passed"] = False
        self.assertFalse(_evaluate_pillar_3(auditors2, RealHwMilestone264FaultInjection())[0].passed)

    def test_32_pillar3_fails_on_raw_firmware_bytes_leaked_override(self) -> None:
        auditors = self._unpack_clean_raw()[3]
        p3, _ = _evaluate_pillar_3(
            auditors,
            RealHwMilestone264FaultInjection(p3_raw_firmware_bytes_leaked_override=16),
        )
        self.assertFalse(p3.passed)

    def test_33_pillar3_fails_when_forward_compat_46th_auditor_fails(self) -> None:
        auditors = self._unpack_clean_raw()[3]
        auditors["realhw_broken_future_audit"] = {"all_checks_passed": False}
        self.assertFalse(_evaluate_pillar_3(auditors, RealHwMilestone264FaultInjection())[0].passed)

    # --- 6. Pillar 4: >= 50 VM Co-Emulation Stages (`outputs/fx3-vm`) ---

    def test_34_pillar4_50_stages_happy_path_and_milestone_50of50(self) -> None:
        raw_vm = self._unpack_clean_raw()[4]
        p4, meta4 = _evaluate_pillar_4(raw_vm, RealHwMilestone264FaultInjection())
        self.assertTrue(p4.passed, p4.errors)
        self.assertGreaterEqual(meta4["stage_count"], 50)
        self.assertEqual(meta4["passed_count"], meta4["stage_count"])
        self.assertEqual(meta4["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(meta4["physical_device_writes"], 0)
        self.assertEqual(meta4["emmc_corruptions"], 0)
        self.assertEqual(p4.evidence["stage50_milestone"], "50/50")
        self.assertFalse(p4.evidence["stage50_fx3_has_builtin_evf"])
        for dkey in ("stage48_digest_sha256", "stage49_digest_sha256", "stage50_digest_sha256"):
            self.assertEqual(len(str(p4.evidence[dkey])), 64, dkey)

    def test_35_pillar4_forward_compatible_with_51_plus_stages(self) -> None:
        raw_vm = self._unpack_clean_raw()[4]
        raw_vm["stage51_realhw_future_wave43_hil"] = {"all_checks_passed": True}
        p4, meta4 = _evaluate_pillar_4(raw_vm, RealHwMilestone264FaultInjection())
        self.assertTrue(p4.passed, p4.errors)
        self.assertGreaterEqual(meta4["stage_count"], 51)
        self.assertEqual(meta4["passed_count"], meta4["stage_count"])

    def test_36_pillar4_fails_on_stage48_through_stage50_fault_injections(self) -> None:
        raw_vm = self._unpack_clean_raw()[4]
        for kw in (
            {"p4_stage48_lock_op_audio_timing_exp_step_faults": 1},
            {"p4_stage49_display_quality_bt_rmt_mymenu_faults": 1},
            {"p4_stage50_diff_set_custom_key_remain_shoot_faults": 1},
        ):
            p4, _ = _evaluate_pillar_4(raw_vm, RealHwMilestone264FaultInjection(**kw))
            self.assertFalse(p4.passed, kw)

    def test_37_pillar4_fails_on_physical_device_writes_or_raw_leak(self) -> None:
        raw_vm = self._unpack_clean_raw()[4]
        for kw in (
            {"p4_physical_device_writes_override": 1},
            {"p4_raw_firmware_bytes_leaked_override": 4},
        ):
            p4, _ = _evaluate_pillar_4(raw_vm, RealHwMilestone264FaultInjection(**kw))
            self.assertFalse(p4.passed, kw)

    def test_38_pillar4_fails_on_stage50_evf_milestone_or_stage48_menu_delete_tamper(self) -> None:
        raw_vm = self._unpack_clean_raw()[4]
        raw_vm["stage50_realhw_diff_set_still_mv_custom_key_remain_shoot_hil"][
            "fx3_has_builtin_evf"
        ] = True
        self.assertFalse(_evaluate_pillar_4(raw_vm, RealHwMilestone264FaultInjection())[0].passed)

        raw_vm2 = self._unpack_clean_raw()[4]
        raw_vm2["stage50_realhw_diff_set_still_mv_custom_key_remain_shoot_hil"]["milestone"] = "49/50"
        self.assertFalse(_evaluate_pillar_4(raw_vm2, RealHwMilestone264FaultInjection())[0].passed)

        raw_vm3 = self._unpack_clean_raw()[4]
        raw_vm3["stage48_realhw_lock_op_parts_audio_timing_exp_step_hil"][
            "destructive_menu_delete_confusions"
        ] = 1
        self.assertFalse(_evaluate_pillar_4(raw_vm3, RealHwMilestone264FaultInjection())[0].passed)

    def test_39_pillar4_fails_when_future_stage51_fails(self) -> None:
        raw_vm = self._unpack_clean_raw()[4]
        raw_vm["stage51_broken_hil"] = {"all_checks_passed": False}
        self.assertFalse(_evaluate_pillar_4(raw_vm, RealHwMilestone264FaultInjection())[0].passed)

    def test_40_pillar4_preserves_stage45_to_47_redline_enforcement(self) -> None:
        raw_vm = self._unpack_clean_raw()[4]
        raw_vm["stage47_realhw_framing_usbpower_lun_antiflicker_hil"]["fx3_has_var_shutter"] = True
        self.assertFalse(_evaluate_pillar_4(raw_vm, RealHwMilestone264FaultInjection())[0].passed)

    # --- 7. Pillar 5: ALL 6 Bench Readiness Verifiers (`P186`..`P261`) ---

    def test_41_pillar5_sextuple_bench_preflights_happy_path(self) -> None:
        b = self._unpack_clean_raw()
        p5, meta5 = _evaluate_pillar_5(*b[5:20], RealHwMilestone264FaultInjection())
        self.assertTrue(p5.passed, p5.errors)
        self.assertFalse(meta5["overall_ready_for_hardware_attach"])
        for off_k, sim_k in (
            ("p186_offline_go_no_go", "p186_sim_go_no_go"),
            ("p204_offline_go_no_go", "p204_sim_go_no_go"),
            ("p216_offline_go_no_go", "p216_sim_go_no_go"),
            ("p227_offline_go_no_go", "p227_sim_go_no_go"),
            ("p248_offline_go_no_go", "p248_sim_go_no_go"),
            ("p261_offline_go_no_go", "p261_sim_go_no_go"),
        ):
            self.assertEqual(meta5[off_k], GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT, off_k)
            self.assertEqual(meta5[sim_k], GO_NO_GO_DRY_RUN_SIMULATED_READY, sim_k)
        self.assertEqual(meta5["p261_sim_check_groups_passed"], 4)
        self.assertEqual(meta5["p261_h0_equals_h3_count"], 16)
        self.assertEqual(meta5["p204_e_nd_actuator_tx_count"], 0)
        self.assertEqual(meta5["p261_e_nd_uart_bytes_transmitted"], 0)
        self.assertFalse(meta5["p261_hardware_live_attachment_authorized"])
        self.assertFalse(p5.evidence["p261_fx3_has_builtin_evf"])

    def test_42_pillar5_rejects_phase261_diffset_customkey_vault_and_autoslow_hdmi_faults(self) -> None:
        b = self._unpack_clean_raw()
        p261_off, p261_sim = copy.deepcopy(self.p261_bad_ab)
        p5, _ = _evaluate_pillar_5(
            *b[5:18], p261_off, p261_sim, RealHwMilestone264FaultInjection()
        )
        self.assertFalse(p5.passed)

    def test_43_pillar5_rejects_phase261_apsc_4k_bodydata_and_end_uart_pii_faults(self) -> None:
        b = self._unpack_clean_raw()
        p261_off, p261_sim = copy.deepcopy(self.p261_bad_cd)
        p5, _ = _evaluate_pillar_5(
            *b[5:18], p261_off, p261_sim, RealHwMilestone264FaultInjection()
        )
        self.assertFalse(p5.passed)

    def test_44_pillar5_rejects_phase261_h0_h3_drift_fault(self) -> None:
        b = self._unpack_clean_raw()
        p261_off, p261_sim = copy.deepcopy(self.p261_bad_drift)
        p5, _ = _evaluate_pillar_5(
            *b[5:18], p261_off, p261_sim, RealHwMilestone264FaultInjection()
        )
        self.assertFalse(p5.passed)

    def test_45_pillar5_rejects_phase261_usb_packets_and_end_uart_overrides(self) -> None:
        b = self._unpack_clean_raw()
        for fkw in (
            {"p5_inject_p261_usb_packets_override": 1},
            {"p5_inject_p261_end_uart_bytes_override": 1},
        ):
            p5, _ = _evaluate_pillar_5(*b[5:20], RealHwMilestone264FaultInjection(**fkw))
            self.assertFalse(p5.passed, fkw)

    def test_46_pillar5_rejects_phase261_offline_if_not_blocked_awaiting_tier0(self) -> None:
        p5_slice = list(self._unpack_clean_raw()[5:20])
        p5_slice[13]["go_no_go"] = GO_NO_GO_DRY_RUN_SIMULATED_READY
        p5, _ = _evaluate_pillar_5(*p5_slice, RealHwMilestone264FaultInjection())
        self.assertFalse(p5.passed)

    def test_47_pillar5_rejects_phase261_sim_sha256_tamper_via_verify_phase261_report(self) -> None:
        p5_slice = list(self._unpack_clean_raw()[5:20])
        p5_slice[14]["report_sha256"] = "0" * 64
        p5, _ = _evaluate_pillar_5(*p5_slice, RealHwMilestone264FaultInjection())
        self.assertFalse(p5.passed)

    def test_48_pillar5_rejects_overall_ready_for_hardware_attach_true_in_p261(self) -> None:
        p5_slice = list(self._unpack_clean_raw()[5:20])
        p5_slice[14]["overall_ready_for_hardware_attach"] = True
        p5, _ = _evaluate_pillar_5(*p5_slice, RealHwMilestone264FaultInjection())
        self.assertFalse(p5.passed)

    def test_49_pillar5_propagates_earlier_phase248_preflight_failure(self) -> None:
        b = self._unpack_clean_raw()
        p248_off, p248_sim = copy.deepcopy(self.p248_bad)
        p5, _ = _evaluate_pillar_5(
            *b[5:16], p248_off, p248_sim, b[18], b[19], RealHwMilestone264FaultInjection()
        )
        self.assertFalse(p5.passed)

    # --- 8. Pillar 6: Live FX3 7.02 QEMU Rounds 28..52+ & < 50 KiB PNG Receipts ---

    def _clean_p1_to_p5_metas(self):
        cls = type(self)
        cached = getattr(cls, "_cached_p1_to_p5_metas", None)
        if cached is None:
            b = self.raw_bundle
            f = RealHwMilestone264FaultInjection()
            p1 = _evaluate_pillar_1(b[0], b[1])
            _, m2 = _evaluate_pillar_2(b[2], f)
            _, m3 = _evaluate_pillar_3(b[3], f)
            _, m4 = _evaluate_pillar_4(b[4], f)
            _, m5 = _evaluate_pillar_5(*b[5:20], f)
            cached = (p1.evidence, m2, m3, m4, m5)
            cls._cached_p1_to_p5_metas = cached
        return cached

    def test_50_pillar6_rounds_28_to_52_at_least_25_rounds_75_runs_50_pngs(self) -> None:
        m1, m2, m3, m4, m5 = self._clean_p1_to_p5_metas()
        p6, meta6 = _evaluate_pillar_6(
            repo_root=REPO_ROOT,
            use_clean_room=True,
            faults=RealHwMilestone264FaultInjection(),
            p1_meta=m1,
            p2_meta=m2,
            p3_meta=m3,
            p4_meta=m4,
            p5_meta=m5,
        )
        self.assertTrue(p6.passed, p6.errors)
        self.assertGreaterEqual(meta6["qemu_rounds_verified"], 25)
        self.assertGreaterEqual(meta6["qemu_runs_verified"], 75)
        self.assertGreaterEqual(meta6["qemu_png_receipts_verified"], 50)
        self.assertLess(meta6["qemu_png_max_bytes"], PNG_MAX_SIZE_50KIB_BYTES)
        self.assertEqual(meta6["qemu_raw_firmware_bytes_leaked"], 0)
        for rnum in (50, 51, 52):
            self.assertEqual(meta6["qemu_round_runs_by_round"][f"r{rnum}"], 3)

    def test_51_pillar6_committed_round51_and_round52_png_headers_under_50kib(self) -> None:
        for rnum in (51, 52):
            for rel in ROUND28_TO_52_PNG_RECEIPTS[rnum]:
                p = REPO_ROOT / rel
                if p.is_file():
                    raw = p.read_bytes()
                    self.assertTrue(raw.startswith(PNG_MAGIC_BYTES), rel)
                    self.assertLess(len(raw), PNG_MAX_SIZE_50KIB_BYTES, rel)

    def test_52_pillar6_forward_compatible_with_round53_directory_discovery(self) -> None:
        m1, m2, m3, m4, m5 = self._clean_p1_to_p5_metas()
        with tempfile.TemporaryDirectory() as tmp:
            tmp_root = Path(tmp)
            r53_dir = tmp_root / "reports" / "2026-11-16-round53-realhw-future-wave43-qemu"
            assets_dir = r53_dir / "assets"
            assets_dir.mkdir(parents=True, exist_ok=True)
            for name in ("r53a-alpha.png", "r53a-composited.png"):
                (assets_dir / name).write_bytes(PNG_MAGIC_BYTES + b"\x00" * 128)
            summary = {
                "schema": "fx6-on-fx3-round53-realhw-future-wave43-qemu-v1",
                "round": 53,
                "kernel_version": "Linux version 4.9.337-scel+ (clean-room-synthetic)",
                "raw_firmware_bytes_leaked": 0,
                "runs": {
                    "r53a_run": {"nop_count": 0, "crashes": 0, "emmc_write_count": 0, "stage_b": {"manifest_count": 13}},
                    "r53b_run": {"nop_count": 0, "crashes": 0, "emmc_write_count": 0, "stage_b": {"manifest_count": 13}},
                    "r53c_run": {"nop_count": 0, "crashes": 0, "emmc_write_count": 0, "stage_b": {"manifest_count": 13}},
                },
                "r53_realhw_future_wave43_audit": {
                    "all_3_runs_crashes_zero": True,
                    "all_3_runs_emmc_write_zero": True,
                    "fx3_has_builtin_evf": False,
                    "fx3_has_var_shutter": False,
                },
            }
            (r53_dir / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
            p6, meta6 = _evaluate_pillar_6(
                repo_root=tmp_root,
                use_clean_room=True,
                faults=RealHwMilestone264FaultInjection(),
                p1_meta=m1,
                p2_meta=m2,
                p3_meta=m3,
                p4_meta=m4,
                p5_meta=m5,
            )
            self.assertTrue(p6.passed, p6.errors)
            self.assertEqual(meta6["qemu_rounds_verified"], 26)
            self.assertEqual(meta6["qemu_runs_verified"], 78)
            self.assertEqual(meta6["qemu_png_receipts_verified"], 52)

    def test_53_pillar6_forward_compatible_round53_rejects_bad_audit_flag_or_kernel(self) -> None:
        m1, m2, m3, m4, m5 = self._clean_p1_to_p5_metas()
        with tempfile.TemporaryDirectory() as tmp:
            tmp_root = Path(tmp)
            r53_dir = tmp_root / "reports" / "2026-11-16-round53-realhw-broken-qemu"
            r53_dir.mkdir(parents=True, exist_ok=True)
            summary = {
                "schema": "fx6-on-fx3-round53-broken-v1",
                "round": 53,
                "kernel_version": "Linux version 4.9.337-scel+ (clean-room-synthetic)",
                "raw_firmware_bytes_leaked": 0,
                "runs": {
                    "r53a_run": {"nop_count": 0, "crashes": 0, "emmc_write_count": 0, "stage_b": {"manifest_count": 13}},
                },
                "r53_broken_audit": {
                    "all_3_runs_crashes_zero": True,
                    "fx3_has_builtin_evf": True,
                },
            }
            (r53_dir / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
            p6, _ = _evaluate_pillar_6(
                repo_root=tmp_root,
                use_clean_room=True,
                faults=RealHwMilestone264FaultInjection(),
                p1_meta=m1,
                p2_meta=m2,
                p3_meta=m3,
                p4_meta=m4,
                p5_meta=m5,
            )
            self.assertFalse(p6.passed)

    def test_54_pillar6_fails_on_round51_and_round52_schema_tamper(self) -> None:
        m1, m2, m3, m4, m5 = self._clean_p1_to_p5_metas()
        for rnum in (51, 52):
            p6, _ = _evaluate_pillar_6(
                repo_root=REPO_ROOT,
                use_clean_room=True,
                faults=RealHwMilestone264FaultInjection(p6_tamper_schema_round_num=rnum),
                p1_meta=m1,
                p2_meta=m2,
                p3_meta=m3,
                p4_meta=m4,
                p5_meta=m5,
            )
            self.assertFalse(p6.passed, rnum)

    def test_55_pillar6_fails_on_round52_nop_crash_emmc_write_or_raw_leak(self) -> None:
        m1, m2, m3, m4, m5 = self._clean_p1_to_p5_metas()
        for fkw in (
            {"p6_round_nop_override_num": 52, "p6_round_nop_count_override": 1},
            {"p6_round_crash_override_num": 52, "p6_round_crashes_override": 1},
            {"p6_round_emmc_override_num": 52, "p6_round_emmc_writes_override": 1},
            {"p6_raw_firmware_bytes_leaked_override": 8},
        ):
            p6, _ = _evaluate_pillar_6(
                repo_root=REPO_ROOT,
                use_clean_room=True,
                faults=RealHwMilestone264FaultInjection(**fkw),
                p1_meta=m1,
                p2_meta=m2,
                p3_meta=m3,
                p4_meta=m4,
                p5_meta=m5,
            )
            self.assertFalse(p6.passed, fkw)

    def test_56_pillar6_fails_when_png_receipt_reaches_or_exceeds_50kib_ceiling(self) -> None:
        m1, m2, m3, m4, m5 = self._clean_p1_to_p5_metas()
        p6, _ = _evaluate_pillar_6(
            repo_root=REPO_ROOT,
            use_clean_room=True,
            faults=RealHwMilestone264FaultInjection(
                p6_png_size_override_round_num=52,
                p6_png_size_override_bytes=PNG_MAX_SIZE_50KIB_BYTES,
            ),
            p1_meta=m1,
            p2_meta=m2,
            p3_meta=m3,
            p4_meta=m4,
            p5_meta=m5,
        )
        self.assertFalse(p6.passed)

    def test_57_pillar6_cross_pillar_p261_h0_h3_end_uart_and_cnflasha_invariants_fail_closed(self) -> None:
        m1, m2, m3, m4, m5 = self._clean_p1_to_p5_metas()
        for bad_k, bad_v in (
            ("p261_h0_equals_h3_count", 15),
            ("p261_e_nd_uart_bytes_transmitted", 1),
            ("p261_hardware_live_attachment_authorized", True),
        ):
            m5_bad = dict(m5)
            m5_bad[bad_k] = bad_v
            p6_bad5, _ = _evaluate_pillar_6(
                repo_root=REPO_ROOT,
                use_clean_room=True,
                faults=RealHwMilestone264FaultInjection(),
                p1_meta=m1,
                p2_meta=m2,
                p3_meta=m3,
                p4_meta=m4,
                p5_meta=m5_bad,
            )
            self.assertFalse(p6_bad5.passed, bad_k)

        m2_bad = dict(m2)
        m2_bad["cnflasha_userspace_write_blocked"] = False
        p6_bad2, _ = _evaluate_pillar_6(
            repo_root=REPO_ROOT,
            use_clean_room=True,
            faults=RealHwMilestone264FaultInjection(),
            p1_meta=m1,
            p2_meta=m2_bad,
            p3_meta=m3,
            p4_meta=m4,
            p5_meta=m5,
        )
        self.assertFalse(p6_bad2.passed)

    # --- 9. Fail-Closed Verifier & CLI `verify-milestone-264` ---

    def test_58_verifier_rejects_non_mapping_payload(self) -> None:
        self.assertFalse(verify_realhw_milestone264_master_gate("not-a-dict").valid)
        self.assertFalse(verify_realhw_milestone264_master_gate(123).valid)
        self.assertFalse(verify_realhw_milestone264_master_gate(None).valid)  # type: ignore[arg-type]

    def test_59_verifier_rejects_sha256_tamper_and_schema_tamper(self) -> None:
        d = self.rep_clean.to_dict()
        d["milestone264_sha256"] = "f" * 64
        self.assertFalse(verify_realhw_milestone264_master_gate(d).valid)

        d2 = self.rep_clean.to_dict()
        d2["schema"] = "wrong_schema_v1"
        d2["milestone264_sha256"] = compute_milestone264_sha256(d2)
        self.assertFalse(verify_realhw_milestone264_master_gate(d2).valid)

    def test_60_verifier_rejects_redline_tamper_even_when_rehashed(self) -> None:
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
            ("e_nd_actuator_tx_count", 1),
            ("otp_fuse_touches", 1),
            ("rpmb_counter_increments", 1),
            ("passive_tx_bytes_emitted", 1),
            ("p261_hardware_live_attachment_authorized", True),
            ("p261_e_nd_uart_bytes_transmitted", 1),
        ):
            d = self.rep_clean.to_dict()
            d[k] = v
            d["milestone264_sha256"] = compute_milestone264_sha256(d)
            self.assertFalse(verify_realhw_milestone264_master_gate(d).valid, k)

    def test_61_verifier_accepts_forward_compatible_higher_counts(self) -> None:
        d = self.rep_clean.to_dict()
        d["gate102_total_gates"] = 104
        d["gate102_offline_verified"] = 101
        d["gate102_simulated_verified"] = 104
        d["recovery_pillar_count"] = 45
        d["recovery_pillars_passed"] = 45
        d["auditors_total"] = 46
        d["auditors_passed"] = 46
        d["vm_stages_total"] = 51
        d["vm_stages_passed"] = 51
        d["qemu_rounds_total"] = 26
        d["qemu_rounds_verified"] = 26
        d["qemu_runs_total"] = 78
        d["qemu_runs_verified"] = 78
        d["qemu_png_receipts_total"] = 52
        d["qemu_png_receipts_verified"] = 52
        d["milestone264_sha256"] = compute_milestone264_sha256(d)
        v = verify_realhw_milestone264_master_gate(d)
        self.assertTrue(v.valid, v.errors)

    def test_62_verifier_rejects_sub_threshold_or_mismatched_counts_and_raw_bytes(self) -> None:
        for k, v in (
            ("gate102_simulated_verified", 101),
            ("recovery_pillar_count", 43),
            ("auditors_passed", 44),
            ("vm_stages_passed", 49),
            ("p261_sim_check_groups_passed", 3),
            ("qemu_rounds_verified", 24),
            ("qemu_runs_verified", 74),
            ("qemu_png_receipts_verified", 49),
            ("qemu_png_max_bytes", PNG_MAX_SIZE_50KIB_BYTES),
        ):
            d = self.rep_clean.to_dict()
            d[k] = v
            d["milestone264_sha256"] = compute_milestone264_sha256(d)
            self.assertFalse(verify_realhw_milestone264_master_gate(d).valid, k)

        d_raw = self.rep_clean.to_dict()
        d_raw["pillars"][0]["summary"] = "leaked b'\\x7fELF'"
        d_raw["milestone264_sha256"] = compute_milestone264_sha256(d_raw)
        self.assertFalse(verify_realhw_milestone264_master_gate(d_raw).valid)

    def test_63_cli_verify_milestone_264_summary_and_out_alias_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            out_json = tmp_path / "m264.json"
            out_md = tmp_path / "m264.md"
            buf = io.StringIO()
            with (
                mock.patch(
                    "fx6_closure.realhw_milestone264_master_gate.evaluate_realhw_milestone264_master_gate",
                    return_value=self.rep_clean,
                ),
                mock.patch("sys.stdout", buf),
            ):
                rc = fx6_cli_main(
                    [
                        "verify-milestone-264",
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
            self.assertIn("schema=realhw_milestone264_master_gate_v1", text)
            self.assertIn("cnflasha_ro=True", text)
            self.assertIn("p261_off=BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT", text)
            self.assertIn("p261_sim=DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH", text)
            self.assertIn("ready_attach=False", text)
            self.assertIsNotNone(re.search(r"gate102=(\d+)/(\d+)", text))
            self.assertIsNotNone(re.search(r"qemu=(\d+)/(\d+)\((\d+)/(\d+)\)", text))
            self.assertTrue(out_json.is_file())
            self.assertTrue(out_md.is_file())
            self.assertTrue(
                verify_realhw_milestone264_master_gate(json.loads(out_json.read_text())).valid
            )

    def test_64_cli_verify_milestone_264_json_stdout_and_failure_exit_code(self) -> None:
        buf = io.StringIO()
        with (
            mock.patch(
                "fx6_closure.realhw_milestone264_master_gate.evaluate_realhw_milestone264_master_gate",
                return_value=self.rep_clean,
            ),
            mock.patch("sys.stdout", buf),
        ):
            rc = fx6_cli_main(["verify-milestone-264", "--clean-room", "--json"])
        self.assertEqual(rc, 0)
        parsed = json.loads(buf.getvalue())
        self.assertEqual(parsed["schema"], REALHW_MILESTONE264_SCHEMA)
        self.assertEqual(parsed["usb_packets_transmitted"], 0)
        self.assertFalse(parsed["overall_ready_for_hardware_attach"])

        bad_rep = replace(
            self.rep_clean,
            all_pillars_milestone_ready=False,
            status=STATUS_FAIL_CLOSED,
            passed_pillar_count=5,
            failed_pillar_ids=("P1",),
            milestone264_sha256="0" * 64,
        )
        buf2 = io.StringIO()
        with (
            mock.patch(
                "fx6_closure.realhw_milestone264_master_gate.evaluate_realhw_milestone264_master_gate",
                return_value=bad_rep,
            ),
            mock.patch("sys.stdout", buf2),
        ):
            rc2 = fx6_cli_main(["verify-milestone-264", "--force-clean-room"])
        self.assertEqual(rc2, 1)
        self.assertIn("status=FAILED", buf2.getvalue())

    def test_65_verify_milestone_264_cli_direct_helper_entrypoint(self) -> None:
        buf = io.StringIO()
        with (
            mock.patch(
                "fx6_closure.realhw_milestone264_master_gate.evaluate_realhw_milestone264_master_gate",
                return_value=self.rep_clean,
            ),
            mock.patch("sys.stdout", buf),
        ):
            rc = verify_milestone_264_cli(["--clean-room", "--json"])
        self.assertEqual(rc, 0)
        parsed = json.loads(buf.getvalue())
        self.assertEqual(parsed["schema"], REALHW_MILESTONE264_SCHEMA)
        self.assertTrue(parsed["cnflasha_userspace_write_blocked"])

    def test_66_synthetic_clean_room_kwarg_alias_and_suite_runtime_budget(self) -> None:
        rep = evaluate_milestone_264_master_gate(
            synthetic_clean_room=True,
            _raw_bundle_override=self._unpack_clean_raw(),
        )
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(rep.all_pillars_milestone_ready)
        budget = (
            15.0
            if __import__("os").environ.get("GITHUB_ACTIONS") == "true"
            else (3.5 if _is_forced_clean_room() else 6.5)
        )
        self.assertLess(self.default_elapsed_s, budget)


if __name__ == "__main__":
    unittest.main()
