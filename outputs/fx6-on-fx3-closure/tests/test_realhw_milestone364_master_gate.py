"""Phase 364 4-mode unit tests for Grand Milestone Phase 364 6-Pillar Real-Hardware Master Gate."""

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
from fx6_closure.realhw_milestone324_master_gate import (  # noqa: E402
    RealHwMilestone324FaultInjection,
)
from fx6_closure.realhw_milestone349_master_gate import (  # noqa: E402
    RealHwMilestone349FaultInjection,
    _worker_phase342_345,
)
from fx6_closure.realhw_milestone364_master_gate import (  # noqa: E402
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
    MILESTONE364_SCHEMA_VERSION,
    OTP_FUSE_TOUCHES,
    OTP_FUSE_WRITES,
    OVERALL_READY_FOR_HARDWARE_ATTACH,
    P8_CP_MUTATION_FORBIDDEN,
    P364_BASELINE_PNG_MAX_OBSERVED_BYTES,
    P364_PHYSICAL_DEVICE_WRITES,
    P364_PILLAR_IDS,
    P364_PILLAR_SPECS,
    P364_PNG_MAX_SIZE_BYTES,
    P364_RAW_FIRMWARE_BYTES_LEAKED,
    P364_SCHEMA,
    P364_STATUS_FAIL_CLOSED,
    P364_STATUS_MILESTONE_READY,
    P364_VERSION,
    PASSIVE_TX_BYTES,
    PASSIVE_TX_BYTES_EMITTED,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHASE_364_VERSION,
    PHYSICAL_DEVICE_WRITES,
    PHYSICAL_USB_PACKETS_EMITTED,
    PILLAR_IDS,
    PILLAR_SPECS,
    PNG_MAGIC_BYTES,
    PNG_MAX_SIZE_50KIB_BYTES,
    PNG_MAX_SIZE_BYTES,
    RAW_FIRMWARE_BYTES_LEAKED,
    REALHW_MILESTONE364_SCHEMA,
    RECOVERY_65_PILLAR_IDS,
    ROUND28_TO_75_PNG_RECEIPTS,
    ROUND28_TO_75_SPECS,
    ROUND73_EXPECTED_SCHEMA,
    ROUND74_EXPECTED_SCHEMA,
    ROUND75_EXPECTED_SCHEMA,
    RPMB_COUNTER_INCREMENTS,
    RPMB_WRITES,
    SPI_NOR_WRITE_AUTHORIZED,
    STATUS_FAIL_CLOSED,
    STATUS_MILESTONE_READY,
    USB_OR_CAMERA_OPERATIONS,
    USB_PACKETS_TRANSMITTED,
    VM_COEMULATION_80_STAGE_KEYS,
    WBI_MUTATION_BYTES,
    WBI_P5_WRITE_AND_HIBERNATION_FORBIDDEN,
    RealHwMilestone364FaultInjection,
    RealHwMilestone364MasterGateReport,
    _collect_parallel_milestone364_results,
    _discover_highest_recovery_master,
    _discover_highest_safety_gate_evaluator,
    _evaluate_pillar_1,
    _evaluate_pillar_2,
    _evaluate_pillar_3,
    _evaluate_pillar_4,
    _evaluate_pillar_5,
    _evaluate_pillar_6,
    _fault_to_156gate_worker_dict,
    _is_negative_audit_bool_key,
    _normalize_65plus_pillar_fault_id,
    _worker_156plus_gate_single,
    _worker_phase354_358,
    _worker_recovery_65plus_pillar,
    build_realhw_milestone364_master_gate_report,
    compute_milestone364_sha256,
    evaluate_milestone364_master_gate,
    evaluate_milestone_364_master_gate,
    evaluate_realhw_milestone364_master_gate,
    render_milestone364_markdown,
    verify_milestone_364_cli,
    verify_milestone_364_master_gate,
    verify_realhw_milestone364_master_gate,
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

    g156_fdict = _fault_to_156gate_worker_dict(
        RealHwMilestone364FaultInjection(
            p1_areadate_grid_cleanhdmi_kwargs={
                "claimed_camset_reset_clears_area_date": True,
            },
            p1_saveload_camset_mishoe_genlock_kwargs={
                "requested_write_operation": True,
            },
            p1_request_persistent_writes=True,
        )
    )
    fx6_s = str(DEFAULT_FX6_DONOR_LIB_DIR)
    fx3_s = str(DEFAULT_FX3_MODULES_DIR)
    ctx = mp.get_context("fork")
    with ProcessPoolExecutor(max_workers=6, mp_context=ctx) as pool:
        fut_g156 = pool.submit(
            _worker_156plus_gate_single,
            (str(REPO_ROOT), True, True, g156_fdict, False),
        )
        fut_p65 = pool.submit(_worker_recovery_65plus_pillar, (True, "pillar_65"))
        fut_354_358_fault = pool.submit(
            _worker_phase354_358,
            (
                fx6_s,
                fx3_s,
                True,
                False,
                {"lockop_shocklesswb_focusmag_afspeed_zebra_saveload_camset": True},
                {"metering_pplut_ibis_customkey_diffset8_gammadisp_usblan_cleaning": True},
            ),
        )
        fut_354_358_drift = pool.submit(
            _worker_phase354_358,
            (fx6_s, fx3_s, True, False, {"h0_h3_drift": True}, {"h0_h3_drift": True}),
        )
        fut_342_345_fault = pool.submit(
            _worker_phase342_345,
            (
                fx6_s,
                fx3_s,
                True,
                False,
                {},
                {"audio_reclevel_outtiming_4ch_mon_touch_dormant_remote_shoot": True},
            ),
        )
        bad_g156 = fut_g156.result()
        bad_p65 = fut_p65.result()
        p354_358_bad = fut_354_358_fault.result()
        p354_358_drift = fut_354_358_drift.result()
        p342_345_bad = fut_342_345_fault.result()
    conn.send((bad_g156, bad_p65, p354_358_bad, p354_358_drift, p342_345_bad))
    conn.close()


class TestRealHwMilestone364MasterGate(unittest.TestCase):
    """Comprehensive 96 4-mode unit tests for Grand Milestone Phase 364."""

    raw_bundle: tuple
    rep_default: RealHwMilestone364MasterGateReport
    rep_clean: RealHwMilestone364MasterGateReport
    bad_sim_g156: dict
    bad_rec_65: dict
    p354_358_bad: tuple
    p354_358_drift: tuple
    p342_345_bad: tuple
    default_elapsed_s: float

    @classmethod
    def setUpClass(cls) -> None:
        import multiprocessing as mp

        t0 = time.monotonic()
        ctx = mp.get_context("fork")
        if not _is_forced_clean_room():
            cls.rep_default = evaluate_milestone_364_master_gate()
        recv_conn, send_conn = ctx.Pipe(duplex=False)
        proc = ctx.Process(
            target=_fork_child_fault_fixtures_only,
            args=(send_conn,),
            daemon=False,
        )
        proc.start()
        send_conn.close()
        try:
            cls.raw_bundle = _collect_parallel_milestone364_results(
                repo_root=REPO_ROOT,
                fx6_lib_dir=DEFAULT_FX6_DONOR_LIB_DIR,
                fx3_modules_dir=DEFAULT_FX3_MODULES_DIR,
                use_clean_room=True,
                faults=RealHwMilestone364FaultInjection(),
                donorless_work_root_none=False,
            )
            (
                cls.bad_sim_g156,
                cls.bad_rec_65,
                cls.p354_358_bad,
                cls.p354_358_drift,
                cls.p342_345_bad,
            ) = recv_conn.recv()
        finally:
            recv_conn.close()
            proc.join(timeout=60)
        cls.rep_clean = evaluate_milestone_364_master_gate(
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
        self.assertEqual(REALHW_MILESTONE364_SCHEMA, "realhw_milestone364_master_gate_v1")
        self.assertEqual(MILESTONE364_SCHEMA_VERSION, REALHW_MILESTONE364_SCHEMA)
        self.assertEqual(P364_SCHEMA, REALHW_MILESTONE364_SCHEMA)
        self.assertEqual(PHASE_364_VERSION, "364.0.0")
        self.assertEqual(P364_VERSION, "364.0.0")
        self.assertEqual(PILLAR_IDS, ("P1", "P2", "P3", "P4", "P5", "P6"))
        self.assertEqual(P364_PILLAR_IDS, PILLAR_IDS)
        self.assertEqual(len(PILLAR_SPECS), 6)
        self.assertEqual(P364_PILLAR_SPECS, PILLAR_SPECS)
        self.assertGreaterEqual(len(RECOVERY_65_PILLAR_IDS), 65)
        self.assertGreaterEqual(len(FIRMWARE_LAB_45_AUDITOR_KEYS), 45)
        self.assertGreaterEqual(len(VM_COEMULATION_80_STAGE_KEYS), 80)
        self.assertGreaterEqual(len(ROUND28_TO_75_SPECS), 48)
        self.assertEqual(PNG_MAX_SIZE_50KIB_BYTES, 51200)
        self.assertEqual(PNG_MAX_SIZE_BYTES, 51200)
        self.assertEqual(P364_PNG_MAX_SIZE_BYTES, 51200)
        self.assertEqual(P364_BASELINE_PNG_MAX_OBSERVED_BYTES, 27467)

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
        self.assertEqual(P364_STATUS_MILESTONE_READY, STATUS_MILESTONE_READY)
        self.assertEqual(P364_STATUS_FAIL_CLOSED, STATUS_FAIL_CLOSED)
        for zero_const in (
            USB_PACKETS_TRANSMITTED,
            PHYSICAL_USB_PACKETS_EMITTED,
            PHYSICAL_DEVICE_WRITES,
            P364_PHYSICAL_DEVICE_WRITES,
            RAW_FIRMWARE_BYTES_LEAKED,
            P364_RAW_FIRMWARE_BYTES_LEAKED,
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
            "P364_CROSS_MODEL_FLASH_AUTHORIZED",
            "MILESTONE364_PHYSICAL_DEVICE_WRITES",
            "MILESTONE364_PILLAR_IDS",
            "MILESTONE364_PILLAR_SPECS",
            "MILESTONE364_PNG_MAX_SIZE_BYTES",
            "MILESTONE364_RAW_FIRMWARE_BYTES_LEAKED",
            "MILESTONE364_SCHEMA_VERSION",
            "P364_BASELINE_PNG_MAX_OBSERVED_BYTES",
            "P364_PHYSICAL_DEVICE_WRITES",
            "P364_PILLAR_IDS",
            "P364_PILLAR_SPECS",
            "P364_PNG_MAX_SIZE_BYTES",
            "P364_RAW_FIRMWARE_BYTES_LEAKED",
            "P364_SCHEMA",
            "P364_STATUS_FAIL_CLOSED",
            "P364_STATUS_MILESTONE_READY",
            "P364_VERSION",
            "PHASE_364_VERSION",
            "REALHW_MILESTONE364_SCHEMA",
            "RECOVERY_65_PILLAR_IDS",
            "ROUND28_TO_75_PNG_RECEIPTS",
            "ROUND28_TO_75_SPECS",
            "ROUND73_EXPECTED_SCHEMA",
            "ROUND74_EXPECTED_SCHEMA",
            "ROUND75_EXPECTED_SCHEMA",
            "STATUS_MILESTONE364_FAIL_CLOSED",
            "STATUS_MILESTONE364_READY",
            "VM_COEMULATION_80_STAGE_KEYS",
            "Milestone364PillarResult",
            "RealHwMilestone364FaultInjection",
            "RealHwMilestone364MasterGateReport",
            "RealHwMilestone364VerifyResult",
            "build_realhw_milestone364_master_gate_report",
            "compute_milestone364_sha256",
            "evaluate_milestone364_master_gate",
            "evaluate_milestone_364_master_gate",
            "evaluate_realhw_milestone364_master_gate",
            "render_milestone364_markdown",
            "verify_milestone_364_cli",
            "verify_milestone_364_master_gate",
            "verify_realhw_milestone364_master_gate",
        }
        self.assertTrue(expected.issubset(set(fx6_closure.__all__)))
        for sym in expected:
            self.assertTrue(hasattr(fx6_closure, sym), sym)
        self.assertEqual(fx6_closure.REALHW_MILESTONE349_SCHEMA, "realhw_milestone349_master_gate_v1")
        self.assertEqual(fx6_closure.REALHW_MILESTONE324_SCHEMA, "realhw_milestone324_master_gate_v1")
        self.assertEqual(fx6_closure.REALHW_MILESTONE311_SCHEMA, "realhw_milestone311_master_gate_v1")
        self.assertEqual(fx6_closure.REALHW_MILESTONE295_SCHEMA, "realhw_milestone295_master_gate_v1")
        self.assertEqual(fx6_closure.REALHW_MILESTONE264_SCHEMA, "realhw_milestone264_master_gate_v1")
        self.assertEqual(fx6_closure.REALHW_MILESTONE254_SCHEMA, "realhw_milestone254_master_gate_v1")
        self.assertEqual(
            fx6_closure.STATUS_MILESTONE349_READY,
            "MILESTONE_349_PREBENCH_MASTER_VERIFIED",
        )
        self.assertEqual(
            fx6_closure.STATUS_MILESTONE364_READY,
            "MILESTONE_364_PREBENCH_MASTER_VERIFIED",
        )

    def test_04_builder_and_verifier_aliases_point_to_canonical_functions(self) -> None:
        self.assertIs(build_realhw_milestone364_master_gate_report, evaluate_realhw_milestone364_master_gate)
        self.assertIs(evaluate_milestone_364_master_gate, evaluate_realhw_milestone364_master_gate)
        self.assertIs(evaluate_milestone364_master_gate, evaluate_realhw_milestone364_master_gate)
        self.assertIs(verify_milestone_364_master_gate, verify_realhw_milestone364_master_gate)

    def test_05_rounds73_to_75_specs_and_png_pairs_registered(self) -> None:
        by_num = {s.round_num: s for s in ROUND28_TO_75_SPECS}
        self.assertGreaterEqual(len(by_num), 48)
        self.assertGreaterEqual(len(ROUND28_TO_75_PNG_RECEIPTS), 48)
        for rnum, exp_schema in (
            (73, ROUND73_EXPECTED_SCHEMA),
            (74, ROUND74_EXPECTED_SCHEMA),
            (75, ROUND75_EXPECTED_SCHEMA),
        ):
            self.assertIn(rnum, by_num)
            self.assertEqual(by_num[rnum].expected_schema, exp_schema)
            self.assertEqual(len(by_num[rnum].run_specs), 3)
            self.assertIn(rnum, ROUND28_TO_75_PNG_RECEIPTS)
            self.assertEqual(len(ROUND28_TO_75_PNG_RECEIPTS[rnum]), 2)
            for _, exp_faithful in by_num[rnum].run_specs:
                self.assertEqual(exp_faithful, 1)

    def test_06_normalize_65plus_pillar_fault_id_resolves_short_and_full_ids(self) -> None:
        self.assertIsNone(_normalize_65plus_pillar_fault_id(None))
        self.assertIsNone(_normalize_65plus_pillar_fault_id(""))
        for pnum in range(60, 66):
            full_id = RECOVERY_65_PILLAR_IDS[pnum - 1]
            self.assertEqual(_normalize_65plus_pillar_fault_id(f"pillar_{pnum}"), full_id)
            self.assertEqual(_normalize_65plus_pillar_fault_id(full_id), full_id)

    def test_07_dynamic_safety_evaluator_discovery_prefers_highest_156plus(self) -> None:
        real_n, real_fn = _discover_highest_safety_gate_evaluator()
        self.assertGreaterEqual(real_n, 156)
        self.assertTrue(callable(real_fn))

        class _FakeSafetyMod:
            @staticmethod
            def evaluate_156gate_preflight():
                return "156"

            @staticmethod
            def evaluate_158gate_preflight():
                return "158"

        best_n, best_fn = _discover_highest_safety_gate_evaluator(_FakeSafetyMod)
        self.assertEqual(best_n, 158)
        self.assertEqual(best_fn(), "158")

    def test_08_dynamic_recovery_master_discovery_prefers_highest_65plus(self) -> None:
        real_m, real_fn, real_ids = _discover_highest_recovery_master()
        self.assertGreaterEqual(real_m, 65)
        self.assertTrue(callable(real_fn))
        self.assertGreaterEqual(len(real_ids), 65)

        class _FakeRecoveryMod:
            MASTER_65_PILLAR_IDS = tuple(f"p_{i}" for i in range(1, 66))
            MASTER_66_PILLAR_IDS = tuple(f"p_{i}" for i in range(1, 67))

            @staticmethod
            def evaluate_realhw_65pillar_recovery_master():
                return 65

            @staticmethod
            def evaluate_realhw_66pillar_recovery_master():
                return 66

        best_m, best_fn, best_ids = _discover_highest_recovery_master(_FakeRecoveryMod)
        self.assertEqual(best_m, 66)
        self.assertEqual(best_fn(), 66)
        self.assertEqual(len(best_ids), 66)

    # --- 2. End-to-End 4-Mode Reports, Determinism & Markdown ---

    def test_09_default_mode_report_all_6_pillars_ready(self) -> None:
        rep = self.rep_default
        self.assertTrue(rep.all_pillars_milestone_ready, rep.errors)
        self.assertEqual(rep.status, STATUS_MILESTONE_READY)
        self.assertEqual(rep.passed_pillar_count, 6)
        self.assertEqual(rep.failed_pillar_ids, ())
        v = verify_realhw_milestone364_master_gate(rep)
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
        for tag in ("p316", "p321", "p329", "p334", "p338", "p341", "p342", "p345", "p354", "p358"):
            self.assertEqual(getattr(rep, f"{tag}_wireless_rf_packets_emitted"), 0, tag)
            self.assertEqual(getattr(rep, f"{tag}_rf_packets_transmitted"), 0, tag)
            self.assertEqual(getattr(rep, f"{tag}_e_nd_actuator_tx_count"), 0, tag)
            self.assertEqual(getattr(rep, f"{tag}_slot1_data_sector_writes"), 0, tag)
        self.assertTrue(verify_realhw_milestone364_master_gate(rep.to_dict()).valid)

    def test_11_fx3_clean_room_test_env_var_compatibility(self) -> None:
        with mock.patch.dict(os.environ, {"FX3_CLEAN_ROOM_TEST": "1"}, clear=False):
            rep = evaluate_milestone_364_master_gate(_raw_bundle_override=self._unpack_clean_raw())
            self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertTrue(rep.all_pillars_milestone_ready, rep.errors)
            self.assertEqual(rep.passed_pillar_count, 6)
            self.assertTrue(verify_realhw_milestone364_master_gate(rep).valid)

    def test_12_mocked_donorless_work_root_none_mode_passes_cleanly(self) -> None:
        rep = evaluate_realhw_milestone364_master_gate(
            fx6_lib_dir=None,
            fx3_modules_dir=None,
            work_root=None,
        )
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(rep.all_pillars_milestone_ready, rep.errors)
        self.assertEqual(rep.passed_pillar_count, 6)
        self.assertEqual(rep.bench_preflight_verifier_count, 22)
        self.assertGreaterEqual(rep.gate156_simulated_verified, 156)
        self.assertTrue(verify_realhw_milestone364_master_gate(rep).valid)

    def test_13_forward_compatible_lower_bounds_on_clean_report(self) -> None:
        rep = self.rep_clean
        self.assertGreaterEqual(rep.gate156_total_gates, 156)
        self.assertGreaterEqual(rep.gate156_offline_verified, 153)
        self.assertEqual(rep.gate156_offline_verified, rep.gate156_total_gates - 3)
        self.assertGreaterEqual(rep.gate156_simulated_verified, 156)
        self.assertEqual(rep.gate156_simulated_verified, rep.gate156_total_gates)
        self.assertTrue(rep.gate156_all_verified)
        self.assertGreaterEqual(rep.recovery_pillar_count, 65)
        self.assertEqual(rep.recovery_pillars_passed, rep.recovery_pillar_count)
        self.assertGreaterEqual(rep.auditors_passed, 45)
        self.assertEqual(rep.auditors_passed, rep.auditors_total)
        self.assertGreaterEqual(rep.vm_stages_passed, 80)
        self.assertEqual(rep.vm_stages_passed, rep.vm_stages_total)
        self.assertEqual(rep.bench_preflight_verifier_count, 22)
        self.assertGreaterEqual(rep.qemu_rounds_verified, 48)
        self.assertGreaterEqual(rep.qemu_runs_verified, 144)
        self.assertGreaterEqual(rep.qemu_png_receipts_verified, 96)
        self.assertLess(rep.qemu_png_max_bytes, PNG_MAX_SIZE_50KIB_BYTES)
        self.assertEqual(rep.h0_equals_h3_count, 16)
        self.assertEqual(rep.e_nd_actuator_tx_count, 0)
        self.assertEqual(rep.emmc_write_count, 0)

    def test_14_deterministic_json_and_sha256_recomputation(self) -> None:
        j1 = self.rep_clean.to_deterministic_json()
        parsed = json.loads(j1)
        self.assertEqual(compute_milestone364_sha256(parsed), self.rep_clean.milestone364_sha256)
        rep2 = evaluate_milestone_364_master_gate(
            force_clean_room=True,
            _raw_bundle_override=self._unpack_clean_raw(),
        )
        self.assertEqual(rep2.milestone364_sha256, self.rep_clean.milestone364_sha256)

    def test_15_no_raw_bytes_repr_in_serialized_reports(self) -> None:
        for rep in (self.rep_default, self.rep_clean):
            self.assertIsNone(re.search(_RAW_BYTES_REPR_REGEX, rep.to_deterministic_json()))

    def test_16_markdown_renderer_contains_bilingual_headers_and_22_preflights(self) -> None:
        md = render_milestone364_markdown(self.rep_clean)
        for token in (
            "Grand Milestone Phase 364",
            "realhw_milestone364_master_gate_v1",
            "MILESTONE_364_PREBENCH_MASTER_VERIFIED",
            "cross_model_flash_authorized = False",
            "156+-Gate Preflight",
            "65+-Pillar Recovery Master",
            "80+ Stage VM HIL",
            "22/22",
            "Ph186=",
            "Ph345=",
            "Ph354=",
            "Ph358=",
            "Rounds 28..75+",
            "| `P1` |",
            "| `P6` |",
        ):
            self.assertIn(token, md)

    # --- 3. Pillar 1: >= 156 Safety Gates (`evaluate_156gate_preflight`) ---

    def test_17_pillar1_156gate_happy_path_and_g63_to_g156_valid(self) -> None:
        raw_off, raw_sim = self._unpack_clean_raw()[:2]
        p1 = _evaluate_pillar_1(raw_off, raw_sim)
        self.assertTrue(p1.passed, p1.errors)
        self.assertGreaterEqual(p1.evidence["offline_verified_gates"], 153)
        self.assertGreaterEqual(p1.evidence["simulated_verified_gates"], 156)
        self.assertTrue(p1.evidence["all_156plus_gates_verified"])
        self.assertFalse(p1.evidence["cross_model_flash_authorized"])
        for idx in range(63, 157):
            self.assertTrue(p1.evidence["g63_to_gn_valid"][f"g{idx}"], f"g{idx}")

    def test_18_pillar1_forward_compatible_with_158_gates(self) -> None:
        raw_off, raw_sim = self._unpack_clean_raw()[:2]
        raw_off["total_gates"] = 158
        raw_off["verified_gates"] = 155
        raw_off["offline_minus3_verified"] = True
        raw_sim["total_gates"] = 158
        raw_sim["verified_gates"] = 158
        raw_sim["all_n_gates_verified"] = True
        raw_sim["nested_g_valid"]["g157"] = True
        raw_sim["nested_g_valid"]["g158"] = True
        p1 = _evaluate_pillar_1(raw_off, raw_sim)
        self.assertTrue(p1.passed, p1.errors)
        self.assertGreaterEqual(p1.evidence["simulated_verified_gates"], 158)

    def test_19_pillar1_fails_when_offline_tier0_gates_not_blocked(self) -> None:
        raw_off, raw_sim = self._unpack_clean_raw()[:2]
        raw_off["verified_gates"] = raw_off["total_gates"]
        raw_off["blocked_or_pending_gates"] = 0
        self.assertFalse(_evaluate_pillar_1(raw_off, raw_sim).passed)

    def test_20_pillar1_fails_when_all_n_gates_verified_false_in_dry_run(self) -> None:
        raw_off, raw_sim = self._unpack_clean_raw()[:2]
        raw_sim["all_n_gates_verified"] = False
        self.assertFalse(_evaluate_pillar_1(raw_off, raw_sim).passed)

    def test_21_pillar1_fails_when_hardware_attach_cross_model_or_write_unlocked(self) -> None:
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

    def test_22_pillar1_fails_when_usb_packets_or_leak_or_end_tx_nonzero(self) -> None:
        for field in (
            "usb_packets_transmitted",
            "raw_firmware_bytes_leaked",
            "g71_e_nd_actuator_tx_count",
        ):
            raw_off, raw_sim = self._unpack_clean_raw()[:2]
            raw_sim[field] = 1
            self.assertFalse(_evaluate_pillar_1(raw_off, raw_sim).passed, field)

    def test_23_pillar1_fails_when_any_g149_to_g156_wave_gate_invalid(self) -> None:
        for gtag in ("g149", "g150", "g151", "g152", "g153", "g154", "g155", "g156"):
            raw_off, raw_sim = self._unpack_clean_raw()[:2]
            raw_sim["nested_g_valid"][gtag] = False
            p1 = _evaluate_pillar_1(raw_off, raw_sim)
            self.assertFalse(p1.passed, gtag)
            self.assertIn(gtag.upper(), p1.errors[-1])

    def test_24_pillar1_live_worker_g155_g156_and_persistent_write_fault(self) -> None:
        raw_sim_bad = copy.deepcopy(self.bad_sim_g156)
        raw_off = self._unpack_clean_raw()[0]
        p1 = _evaluate_pillar_1(raw_off, raw_sim_bad)
        self.assertFalse(p1.passed)
        self.assertFalse(raw_sim_bad["nested_g_valid"]["g155"])
        self.assertFalse(raw_sim_bad["nested_g_valid"]["g156"])

    def test_25_fault_to_156gate_worker_dict_propagates_wave66_to_76_and_m349(self) -> None:
        f = RealHwMilestone364FaultInjection(
            p1_drive_focusbracket_shutter_efcs_nr_kwargs={"dormant_focus_bracket_requested": True},
            p1_areadate_grid_cleanhdmi_kwargs={"claimed_camset_reset_clears_area_date": True},
            p1_saveload_camset_mishoe_genlock_kwargs={"requested_write_operation": True},
            m349_faults=RealHwMilestone349FaultInjection(p1_request_persistent_writes=True),
        )
        w = _fault_to_156gate_worker_dict(f)
        self.assertTrue(w["p1_request_persistent_writes"])
        self.assertEqual(
            w["p1_drive_focusbracket_shutter_efcs_nr_kwargs"],
            {"dormant_focus_bracket_requested": True},
        )
        self.assertEqual(
            w["p1_areadate_grid_cleanhdmi_kwargs"],
            {"claimed_camset_reset_clears_area_date": True},
        )
        self.assertEqual(
            w["p1_saveload_camset_mishoe_genlock_kwargs"],
            {"requested_write_operation": True},
        )

    def test_26_worker_156plus_gate_handles_pre_g155_fault_chain_override(self) -> None:
        f = RealHwMilestone364FaultInjection(
            p1_pixelmap_apr_monitor_vfadjust_kwargs={"requested_fx6_dormant_abb_menu": True},
        )
        w = _fault_to_156gate_worker_dict(f)
        bad_sim = _worker_156plus_gate_single((str(REPO_ROOT), True, True, w, True))
        raw_off = self._unpack_clean_raw()[0]
        self.assertFalse(_evaluate_pillar_1(raw_off, bad_sim).passed)

    # --- 4. Pillar 2: >= 65 Recovery Pillars (`evaluate_realhw_65pillar_recovery_master`) ---

    def test_27_pillar2_65pillar_happy_path_and_cnflasha_ro(self) -> None:
        rec_65 = self._unpack_clean_raw()[2]
        p2, meta2 = _evaluate_pillar_2(rec_65, RealHwMilestone364FaultInjection())
        self.assertTrue(p2.passed, p2.errors)
        self.assertGreaterEqual(meta2["recovery_pillar_count"], 65)
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

    def test_28_pillar2_forward_compatible_with_66_pillars(self) -> None:
        rec_65 = self._unpack_clean_raw()[2]
        rec_65["pillar_count"] = 66
        rec_65["pillars_passed"] = 66
        rec_65["status"] = "VERIFIED_66OF66_PILLAR_RECOVERY_MASTER"
        rec_65["pillars"] = list(rec_65["pillars"]) + [
            {"pillar_id": "pillar_66_future_vault", "passed": True}
        ]
        p2, meta2 = _evaluate_pillar_2(rec_65, RealHwMilestone364FaultInjection())
        self.assertTrue(p2.passed, p2.errors)
        self.assertGreaterEqual(meta2["recovery_pillar_count"], 66)

    def test_29_pillar2_fails_when_cnflasha_userspace_write_unblocked(self) -> None:
        rec_65 = self._unpack_clean_raw()[2]
        p2, _ = _evaluate_pillar_2(
            rec_65,
            RealHwMilestone364FaultInjection(p2_cnflasha_write_unblocked_fault=True),
        )
        self.assertFalse(p2.passed)

    def test_30_pillar2_fails_on_otp_rpmb_passive_tx_usb_devwrite_or_leak_overrides(self) -> None:
        rec_65 = self._unpack_clean_raw()[2]
        for kw in (
            {"p2_otp_fuse_touches_override": 1},
            {"p2_rpmb_counter_increments_override": 1},
            {"p2_passive_tx_bytes_override": 4},
            {"p2_physical_usb_packets_override": 1},
            {"p2_physical_device_writes_override": 1},
            {"p2_raw_firmware_bytes_leaked_override": 8},
        ):
            p2, _ = _evaluate_pillar_2(rec_65, RealHwMilestone364FaultInjection(**kw))
            self.assertFalse(p2.passed, kw)

    def test_31_pillar2_fails_when_65a_or_65b_vault_subsuite_fails_safely(self) -> None:
        for sub_key in (
            "pillar65_a_hdmi_raw_16bit_rec_media_vault",
            "pillar65_b_desqueeze_reclamp_varshutter_apsc_vault",
        ):
            rec_65 = self._unpack_clean_raw()[2]
            rec_65.setdefault(sub_key, {})["passed"] = False
            self.assertFalse(
                _evaluate_pillar_2(rec_65, RealHwMilestone364FaultInjection())[0].passed,
                sub_key,
            )

    def test_32_pillar2_live_worker_fault_inject_pillar_65_fails_closed(self) -> None:
        bad_65 = copy.deepcopy(self.bad_rec_65)
        p2, _ = _evaluate_pillar_2(bad_65, RealHwMilestone364FaultInjection())
        self.assertFalse(p2.passed)

    def test_33_pillar2_fails_on_p63_to_p65_violation_counters_or_hw_flags(self) -> None:
        for vkey in (
            "bodydata_version_flash_or_slot1_vault_drift_events",
            "desqueeze_ratio_lock_or_bypass_drift_events",
            "ftp_protocol_sftp_or_jpeg_size_drift_events",
            "hdmi_raw_output_or_media_vault_drift_events",
            "marker_15ratio_peaking_hdmi_leak_events",
            "slot1_avf_info_mutation_bytes",
            "usblan_packets_transmitted",
            "zero_rf_usblan_or_slot1_avf_bypass_events",
        ):
            rec_65 = self._unpack_clean_raw()[2]
            rec_65[vkey] = 1
            self.assertFalse(
                _evaluate_pillar_2(rec_65, RealHwMilestone364FaultInjection())[0].passed,
                vkey,
            )
        for neg_flag in (
            "fx3_has_builtin_evf",
            "fx3_has_var_shutter",
            "fx3_has_builtin_end_filter",
            "fx3_has_bt_timecode_link",
            "fx3_has_fan_control_max",
            "fx6_has_ibis",
            "fx6_has_bluetooth_hardware",
        ):
            rec_neg = self._unpack_clean_raw()[2]
            rec_neg[neg_flag] = True
            self.assertFalse(
                _evaluate_pillar_2(rec_neg, RealHwMilestone364FaultInjection())[0].passed,
                neg_flag,
            )

    def test_34_pillar2_passes_with_optional_p65_subkeys_present_and_66_compat(self) -> None:
        rec_65 = self._unpack_clean_raw()[2]
        rec_65["pillar_count"] = 66
        rec_65["pillars_passed"] = 66
        rec_65["status"] = "VERIFIED_66OF66_PILLAR_RECOVERY_MASTER"
        rec_65["pillars"] = list(rec_65["pillars"]) + [{"pillar_id": "pillar_66", "passed": True}]
        rec_65["pillar66_a_extra_vault"] = {"passed": True}
        self.assertTrue(_evaluate_pillar_2(rec_65, RealHwMilestone364FaultInjection())[0].passed)

    # --- 5. Pillar 3: >= 45 Firmware Auditors (`outputs/fx3-firmware-lab`) ---

    def test_35_pillar3_45plus_auditors_happy_path(self) -> None:
        auditors = self._unpack_clean_raw()[3]
        p3, meta3 = _evaluate_pillar_3(auditors, RealHwMilestone364FaultInjection())
        self.assertTrue(p3.passed, p3.errors)
        self.assertGreaterEqual(meta3["auditor_count"], 45)
        self.assertEqual(meta3["passed_count"], meta3["auditor_count"])
        self.assertEqual(meta3["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(meta3["e_nd_actuator_tx_count"], 0)
        self.assertEqual(meta3["calibration_mutation_bytes"], 0)

    def test_36_pillar3_forward_compatible_with_46_plus_auditors(self) -> None:
        auditors = self._unpack_clean_raw()[3]
        auditors["realhw_future_wave76_audit"] = {"all_checks_passed": True}
        p3, meta3 = _evaluate_pillar_3(auditors, RealHwMilestone364FaultInjection())
        self.assertTrue(p3.passed, p3.errors)
        self.assertGreaterEqual(meta3["auditor_count"], 46)
        self.assertEqual(meta3["passed_count"], meta3["auditor_count"])

    def test_37_pillar3_fails_on_auditor45_guard_fault_or_subpillar_failure(self) -> None:
        auditors = self._unpack_clean_raw()[3]
        p3_fault, _ = _evaluate_pillar_3(
            auditors,
            RealHwMilestone364FaultInjection(p3_filesettings_tcregen_reclamp_guard_fault=True),
        )
        self.assertFalse(p3_fault.passed)

        auditors2 = self._unpack_clean_raw()[3]
        auditors2["realhw_filesettings_shotmark_tcregen_and_reclamp_audit"].setdefault(
            "pillar_2_tc_regenerate_slot1_and_ext_lk", {}
        )["passed"] = False
        self.assertFalse(_evaluate_pillar_3(auditors2, RealHwMilestone364FaultInjection())[0].passed)

    def test_38_pillar3_fails_on_raw_firmware_bytes_leaked_override(self) -> None:
        auditors = self._unpack_clean_raw()[3]
        p3, _ = _evaluate_pillar_3(
            auditors,
            RealHwMilestone364FaultInjection(p3_raw_firmware_bytes_leaked_override=16),
        )
        self.assertFalse(p3.passed)

    def test_39_pillar3_fails_when_forward_compat_46th_auditor_fails(self) -> None:
        auditors = self._unpack_clean_raw()[3]
        auditors["realhw_broken_future_audit"] = {"all_checks_passed": False}
        self.assertFalse(_evaluate_pillar_3(auditors, RealHwMilestone364FaultInjection())[0].passed)

    # --- 6. Pillar 4: >= 80 VM HIL Co-Emulation Stages (`outputs/fx3-vm`) ---

    def test_40_pillar4_80plus_stages_happy_path_and_milestone_80of80(self) -> None:
        raw_vm = self._unpack_clean_raw()[4]
        p4, meta4 = _evaluate_pillar_4(raw_vm, RealHwMilestone364FaultInjection())
        self.assertTrue(p4.passed, p4.errors)
        self.assertGreaterEqual(meta4["stage_count"], 80)
        self.assertEqual(meta4["passed_count"], meta4["stage_count"])
        self.assertEqual(meta4["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(meta4["physical_device_writes"], 0)
        self.assertEqual(meta4["emmc_corruptions"], 0)
        self.assertEqual(p4.evidence["stage80_milestone"], "80/80")
        for dkey in (
            "stage76_digest_sha256",
            "stage78_digest_sha256",
            "stage80_digest_sha256",
        ):
            self.assertEqual(len(str(p4.evidence[dkey])), 64, dkey)

    def test_41_pillar4_forward_compatible_with_stage81_plus(self) -> None:
        raw_vm = self._unpack_clean_raw()[4]
        raw_vm["stage81_realhw_future_wave77_hil"] = {
            "all_checks_passed": True,
            "physical_device_writes": 0,
            "raw_firmware_bytes_leaked": 0,
            "cp_mutation_bytes": 0,
            "bk4_persistent_nvram_writes": 0,
            "wf12_00342260_hits": 0,
            "emmc_corruptions": 0,
            "slot1_avf_info_mutated": False,
        }
        p4, meta4 = _evaluate_pillar_4(raw_vm, RealHwMilestone364FaultInjection())
        self.assertTrue(p4.passed, p4.errors)
        self.assertGreaterEqual(meta4["stage_count"], 81)
        self.assertEqual(meta4["passed_count"], meta4["stage_count"])

    def test_42_pillar4_fails_on_stage76_through_stage80_fault_injections(self) -> None:
        raw_vm = self._unpack_clean_raw()[4]
        for kw in (
            {"p4_stage76_drive_focusbracket_shutter_efcs_creativelook_recoverdb_faults": 1},
            {"p4_stage77_pixelmap_apr_monitor_vfadjust_customhold_hdmi_reccontrol_faults": 1},
            {"p4_stage78_areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_faults": 1},
            {"p4_stage79_pbmag_varshutter_ecs_wifi5ghz_nvs_ir_lanc_cec_faults": 1},
            {"p4_stage80_peaking_cleanhdmi_audiometer_wind_usbpd_dcc1_ntscpal_avfinfo_faults": 1},
        ):
            p4, _ = _evaluate_pillar_4(raw_vm, RealHwMilestone364FaultInjection(**kw))
            self.assertFalse(p4.passed, kw)

    def test_43_pillar4_fails_on_stage72_through_stage75_cascaded_fault_injections(self) -> None:
        raw_vm = self._unpack_clean_raw()[4]
        for m349_kw in (
            {"p4_stage72_shoe_audio_4ch_subject_recog_silent_target_version_faults": 1},
            {"p4_stage73_hdmi_raw_desqueeze_reclamp_varshutter_apsc_faults": 1},
            {"p4_stage74_breathing_camid_copyright_powersave_ntsc_pal_faults": 1},
            {"p4_stage75_zoom_ciz_autoslow_iso_arw_rawcomp_usblun_uvc_faults": 1},
        ):
            f = RealHwMilestone364FaultInjection(
                m349_faults=RealHwMilestone349FaultInjection(**m349_kw)
            )
            p4, _ = _evaluate_pillar_4(raw_vm, f)
            self.assertFalse(p4.passed, m349_kw)

    def test_44_pillar4_fails_on_physical_device_writes_or_raw_leak(self) -> None:
        raw_vm = self._unpack_clean_raw()[4]
        for kw in (
            {"p4_physical_device_writes_override": 1},
            {"p4_raw_firmware_bytes_leaked_override": 4},
        ):
            p4, _ = _evaluate_pillar_4(raw_vm, RealHwMilestone364FaultInjection(**kw))
            self.assertFalse(p4.passed, kw)

    def test_45_pillar4_fails_on_stage76_to_80_milestone_or_digest_tamper(self) -> None:
        raw_vm = self._unpack_clean_raw()[4]
        raw_vm["stage80_realhw_peaking_cleanhdmi_audiometer_wind_usbpd_dcc1_ntscpal_avfinfo_hil"][
            "milestone"
        ] = "79/80"
        self.assertFalse(_evaluate_pillar_4(raw_vm, RealHwMilestone364FaultInjection())[0].passed)

        raw_vm2 = self._unpack_clean_raw()[4]
        raw_vm2["stage78_realhw_areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_hil"][
            "phase353_audit_digest_sha256"
        ] = "bad"
        self.assertFalse(_evaluate_pillar_4(raw_vm2, RealHwMilestone364FaultInjection())[0].passed)

    def test_46_pillar4_fails_on_stage76_to_80_redline_counters_and_emmc_mutation(self) -> None:
        for skey, bad_counter in (
            ("stage76_realhw_drive_focusbracket_shutter_efcs_creativelook_recoverdb_hil", "dormant_focus_bracket_exposed_events"),
            ("stage77_realhw_pixelmap_apr_monitor_vfadjust_customhold_hdmi_reccontrol_hil", "dormant_evf_menus_exposed_events"),
            ("stage78_realhw_areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_hil", "camset_slot1_erofs_bypass_events"),
            ("stage79_realhw_pbmag_varshutter_ecs_wifi5ghz_nvs_ir_lanc_cec_hil", "p12_p13_write_bypass_events"),
            ("stage80_realhw_peaking_cleanhdmi_audiometer_wind_usbpd_dcc1_ntscpal_avfinfo_hil", "slot1_avf_info_or_format_write_bypass_events"),
            ("stage80_realhw_peaking_cleanhdmi_audiometer_wind_usbpd_dcc1_ntscpal_avfinfo_hil", "emmc_mutation_bytes"),
        ):
            raw_vm = self._unpack_clean_raw()[4]
            raw_vm[skey][bad_counter] = 1
            self.assertFalse(
                _evaluate_pillar_4(raw_vm, RealHwMilestone364FaultInjection())[0].passed,
                f"{skey}:{bad_counter}",
            )

    def test_47_pillar4_fails_when_future_stage81_fails_or_mutates_avf_info(self) -> None:
        raw_vm = self._unpack_clean_raw()[4]
        raw_vm["stage81_broken_hil"] = {"all_checks_passed": False}
        self.assertFalse(_evaluate_pillar_4(raw_vm, RealHwMilestone364FaultInjection())[0].passed)

        raw_vm2 = self._unpack_clean_raw()[4]
        raw_vm2["stage81_realhw_wave77_hil"] = {
            "all_checks_passed": True,
            "slot1_avf_info_mutated": True,
        }
        self.assertFalse(_evaluate_pillar_4(raw_vm2, RealHwMilestone364FaultInjection())[0].passed)

    def test_48_pillar4_fails_on_wf12_hits_in_stage76_to_80(self) -> None:
        raw_vm = self._unpack_clean_raw()[4]
        raw_vm["stage78_realhw_areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_hil"][
            "wf12_00342260_hits"
        ] = 1
        p4, meta4 = _evaluate_pillar_4(raw_vm, RealHwMilestone364FaultInjection())
        self.assertEqual(meta4["wf12_00342260_hits"], 1)
        self.assertFalse(p4.passed)
        m1 = _evaluate_pillar_1(self.raw_bundle[0], self.raw_bundle[1]).evidence
        _, m2 = _evaluate_pillar_2(self.raw_bundle[2], RealHwMilestone364FaultInjection())
        _, m3 = _evaluate_pillar_3(self.raw_bundle[3], RealHwMilestone364FaultInjection())
        _, m5 = _evaluate_pillar_5(*self._unpack_clean_raw()[5:52], RealHwMilestone364FaultInjection())
        p6, _ = _evaluate_pillar_6(
            repo_root=REPO_ROOT,
            use_clean_room=True,
            faults=RealHwMilestone364FaultInjection(),
            p1_meta=m1,
            p2_meta=m2,
            p3_meta=m3,
            p4_meta=meta4,
            p5_meta=m5,
        )
        self.assertFalse(p6.passed)

    def test_49_pillar4_fails_if_passed_stage_count_below_80(self) -> None:
        raw_vm = self._unpack_clean_raw()[4]
        raw_vm["stage80_realhw_peaking_cleanhdmi_audiometer_wind_usbpd_dcc1_ntscpal_avfinfo_hil"][
            "all_checks_passed"
        ] = False
        self.assertFalse(_evaluate_pillar_4(raw_vm, RealHwMilestone364FaultInjection())[0].passed)

    # --- 7. Pillar 5: ALL 22 Bench Readiness Verifiers (`Ph186`..`Ph358`) ---

    def test_50_pillar5_duovigesuple_22of22_bench_preflights_happy_path(self) -> None:
        b = self._unpack_clean_raw()
        p5, meta5 = _evaluate_pillar_5(*b[5:52], RealHwMilestone364FaultInjection())
        self.assertTrue(p5.passed, p5.errors)
        self.assertEqual(meta5["bench_preflight_verifier_count"], 22)
        self.assertFalse(meta5["overall_ready_for_hardware_attach"])
        all_22 = (
            "p186", "p204", "p216", "p227", "p248", "p261",
            "p275", "p279", "p284", "p291", "p302", "p307",
            "p316", "p321", "p329", "p334", "p338", "p341",
            "p342", "p345", "p354", "p358",
        )
        for tag in all_22:
            off_k = f"{tag}_offline_go_no_go"
            sim_k = f"{tag}_sim_go_no_go"
            self.assertEqual(meta5[off_k], GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT, off_k)
            self.assertEqual(meta5[sim_k], GO_NO_GO_DRY_RUN_SIMULATED_READY, sim_k)
            self.assertEqual(meta5[f"{tag}_h0_equals_h3_count"], 16, tag)
        self.assertFalse(meta5["p186_card_insert_authorized"])
        for tag in all_22[1:]:
            self.assertFalse(meta5[f"{tag}_hardware_live_attachment_authorized"], tag)
        for tag in ("p316", "p321", "p329", "p334", "p338", "p341", "p342", "p345", "p354", "p358"):
            self.assertEqual(meta5[f"{tag}_sim_check_groups_passed"], 4, tag)
            self.assertEqual(meta5[f"{tag}_sim_usb_packets_transmitted"], 0, tag)
            self.assertEqual(meta5[f"{tag}_sim_passive_tx_bytes_emitted"], 0, tag)
            self.assertEqual(meta5[f"{tag}_wireless_rf_packets_emitted"], 0, tag)
            self.assertEqual(meta5[f"{tag}_rf_packets_transmitted"], 0, tag)
            self.assertEqual(meta5[f"{tag}_e_nd_actuator_tx_count"], 0, tag)
            self.assertEqual(meta5[f"{tag}_slot1_data_sector_writes"], 0, tag)

    def test_51_pillar5_rejects_phase354_lockop_shocklesswb_zebra_camset_faults(self) -> None:
        b = list(self._unpack_clean_raw())
        p354_off, p354_sim, _, _ = copy.deepcopy(self.p354_358_bad)
        p5, _ = _evaluate_pillar_5(
            *b[5:48], p354_off, p354_sim, *b[50:52], RealHwMilestone364FaultInjection()
        )
        self.assertFalse(p5.passed)

    def test_52_pillar5_rejects_phase358_metering_pplut_ibis_usblan_cleaning_faults(self) -> None:
        b = list(self._unpack_clean_raw())
        _, _, p358_off, p358_sim = copy.deepcopy(self.p354_358_bad)
        p5, _ = _evaluate_pillar_5(
            *b[5:50], p358_off, p358_sim, RealHwMilestone364FaultInjection()
        )
        self.assertFalse(p5.passed)

    def test_53_pillar5_rejects_h0_h3_drift_across_p354_and_p358(self) -> None:
        b = list(self._unpack_clean_raw())
        d354_o, d354_s, d358_o, d358_s = copy.deepcopy(self.p354_358_drift)
        for sl_idx, (ro, rs) in (
            (48, (d354_o, d354_s)),
            (50, (d358_o, d358_s)),
        ):
            mod_b = list(b)
            mod_b[sl_idx] = ro
            mod_b[sl_idx + 1] = rs
            p5, _ = _evaluate_pillar_5(*mod_b[5:52], RealHwMilestone364FaultInjection())
            self.assertFalse(p5.passed, sl_idx)

    def test_54_pillar5_rejects_p354_and_p358_usb_passive_and_wireless_rf_overrides(self) -> None:
        b = self._unpack_clean_raw()
        for tag in ("p354", "p358"):
            for fkw in (
                {f"p5_inject_{tag}_usb_packets_override": 1},
                {f"p5_inject_{tag}_passive_tx_bytes_override": 4},
                {f"p5_inject_{tag}_wireless_rf_packets_override": 1},
            ):
                p5, _ = _evaluate_pillar_5(*b[5:52], RealHwMilestone364FaultInjection(**fkw))
                self.assertFalse(p5.passed, fkw)

    def test_55_pillar5_rejects_p354_and_p358_rf_nvs_auth_or_slot1_tier0_mutated(self) -> None:
        # indices inside p5_slice (b[5:52]): p354_sim=44, p358_sim=46
        for sim_idx in (44, 46):
            for bad_k, bad_v in (
                ("rf_nvs_p12_p13_writes_authorized", True),
                ("slot1_tier0_vault_mutated", True),
                ("slot1_data_sector_writes", 1),
                ("e_nd_actuator_tx_count", 1),
            ):
                p5_slice = list(self._unpack_clean_raw()[5:52])
                p5_slice[sim_idx][bad_k] = bad_v
                p5, _ = _evaluate_pillar_5(*p5_slice, RealHwMilestone364FaultInjection())
                self.assertFalse(p5.passed, f"idx={sim_idx}:{bad_k}")

    def test_56_pillar5_rejects_offline_if_not_blocked_awaiting_tier0(self) -> None:
        for off_idx in (43, 45):
            p5_slice = list(self._unpack_clean_raw()[5:52])
            p5_slice[off_idx]["go_no_go"] = GO_NO_GO_DRY_RUN_SIMULATED_READY
            p5, _ = _evaluate_pillar_5(*p5_slice, RealHwMilestone364FaultInjection())
            self.assertFalse(p5.passed, off_idx)

    def test_57_pillar5_rejects_sim_sha256_tamper_and_attach_ready_true(self) -> None:
        for sim_idx in (44, 46):
            p5_slice = list(self._unpack_clean_raw()[5:52])
            p5_slice[sim_idx]["report_sha256"] = "0" * 64
            p5, _ = _evaluate_pillar_5(*p5_slice, RealHwMilestone364FaultInjection())
            self.assertFalse(p5.passed, sim_idx)

            p5_slice2 = list(self._unpack_clean_raw()[5:52])
            p5_slice2[sim_idx]["overall_ready_for_hardware_attach"] = True
            p5_2, _ = _evaluate_pillar_5(*p5_slice2, RealHwMilestone364FaultInjection())
            self.assertFalse(p5_2.passed, sim_idx)

    def test_58_pillar5_rejects_p354_and_p358_check_groups_count_mismatch(self) -> None:
        for sim_idx in (44, 46):
            p5_slice = list(self._unpack_clean_raw()[5:52])
            p5_slice[sim_idx]["check_groups_passed"] = 3
            p5, _ = _evaluate_pillar_5(*p5_slice, RealHwMilestone364FaultInjection())
            self.assertFalse(p5.passed, sim_idx)

    def test_59_pillar5_propagates_upstream_phase345_failure(self) -> None:
        b = list(self._unpack_clean_raw())
        _, _, p345_off, p345_sim = copy.deepcopy(self.p342_345_bad)
        p5, _ = _evaluate_pillar_5(
            *b[5:46], p345_off, p345_sim, *b[48:52], RealHwMilestone364FaultInjection()
        )
        self.assertFalse(p5.passed)

    def test_60_pillar5_enforces_22_of_22_bench_preflight_count(self) -> None:
        b = self._unpack_clean_raw()
        p5, meta5 = _evaluate_pillar_5(*b[5:52], RealHwMilestone364FaultInjection())
        self.assertEqual(p5.evidence["bench_preflight_verifier_count"], 22)
        self.assertEqual(meta5["bench_preflight_verifier_count"], 22)

    # --- 8. Pillar 6: Live FX3 7.02 QEMU Rounds 28..75+ & < 50 KiB PNG Receipts ---

    def _clean_p1_to_p5_metas(self):
        cls = type(self)
        cached = getattr(cls, "_cached_p1_to_p5_metas", None)
        if cached is None:
            b = self.raw_bundle
            f = RealHwMilestone364FaultInjection()
            p1 = _evaluate_pillar_1(b[0], b[1])
            _, m2 = _evaluate_pillar_2(b[2], f)
            _, m3 = _evaluate_pillar_3(b[3], f)
            _, m4 = _evaluate_pillar_4(b[4], f)
            _, m5 = _evaluate_pillar_5(*b[5:52], f)
            cached = (p1.evidence, m2, m3, m4, m5)
            cls._cached_p1_to_p5_metas = cached
        return cached

    def test_61_pillar6_rounds_28_to_75_at_least_48_rounds_144_runs_96_pngs(self) -> None:
        m1, m2, m3, m4, m5 = self._clean_p1_to_p5_metas()
        p6, meta6 = _evaluate_pillar_6(
            repo_root=REPO_ROOT,
            use_clean_room=True,
            faults=RealHwMilestone364FaultInjection(),
            p1_meta=m1,
            p2_meta=m2,
            p3_meta=m3,
            p4_meta=m4,
            p5_meta=m5,
        )
        self.assertTrue(p6.passed, p6.errors)
        self.assertGreaterEqual(meta6["qemu_rounds_verified"], 48)
        self.assertGreaterEqual(meta6["qemu_runs_verified"], 144)
        self.assertGreaterEqual(meta6["qemu_png_receipts_verified"], 96)
        self.assertLess(meta6["qemu_png_max_bytes"], PNG_MAX_SIZE_50KIB_BYTES)
        self.assertEqual(meta6["qemu_raw_firmware_bytes_leaked"], 0)
        self.assertEqual(meta6["qemu_real_kernel_nop_count"], 0)
        self.assertEqual(meta6["qemu_real_kernel_crashes"], 0)
        self.assertEqual(meta6["qemu_real_kernel_emmc_writes"], 0)
        for rnum in range(73, 76):
            self.assertEqual(meta6["qemu_round_runs_by_round"][f"r{rnum}"], 3)

    def test_62_pillar6_committed_rounds73_to_75_png_headers_and_baseline_max_27467b(self) -> None:
        observed_max = 0
        for rnum in range(28, 76):
            for rel in ROUND28_TO_75_PNG_RECEIPTS[rnum]:
                p = REPO_ROOT / rel
                if p.is_file():
                    raw = p.read_bytes()
                    self.assertTrue(raw.startswith(PNG_MAGIC_BYTES), rel)
                    self.assertLess(len(raw), PNG_MAX_SIZE_50KIB_BYTES, rel)
                    if len(raw) > observed_max:
                        observed_max = len(raw)
        if observed_max > 0:
            self.assertLessEqual(observed_max, P364_BASELINE_PNG_MAX_OBSERVED_BYTES)

    def test_63_pillar6_forward_compatible_with_round76_directory_discovery_and_f141c0e17(self) -> None:
        m1, m2, m3, m4, m5 = self._clean_p1_to_p5_metas()
        with tempfile.TemporaryDirectory() as tmp:
            tmp_root = Path(tmp)
            r76_dir = tmp_root / "reports" / "2026-11-18-round76-realhw-wave62-qemu"
            assets_dir = r76_dir / "assets"
            assets_dir.mkdir(parents=True, exist_ok=True)
            for name in ("r76a-alpha.png", "r76a-composited.png"):
                (assets_dir / name).write_bytes(PNG_MAGIC_BYTES + b"\x00" * 128)
            summary = {
                "schema": "fx6-on-fx3-round76-realhw-wave62-qemu-v1",
                "round": 76,
                "kernel_version": "Linux version 4.9.337-scel+ (clean-room-synthetic)",
                "raw_firmware_bytes_leaked": 0,
                "runs": {
                    "r76a_run": {"nop_count": 0, "crashes": 0, "emmc_write_count": 0, "stage_b": {"manifest_count": 13}},
                    "r76b_run": {"nop_count": 0, "crashes": 0, "emmc_write_count": 0, "stage_b": {"manifest_count": 13}},
                    "r76c_run": {"nop_count": 0, "crashes": 0, "emmc_write_count": 0, "stage_b": {"manifest_count": 13}},
                },
                "r76_realhw_wave62_audit": {
                    "all_3_runs_crashes_zero": True,
                    "all_3_runs_emmc_write_zero": True,
                    # f141c0e17 negative bool rule: fx3_*/fx6_* ending in _present/_only/_exposed/_supported or containing _has_
                    "fx3_has_builtin_evf": False,
                    "fx3_future_dormant_present": False,
                    "fx6_only_sdi_genlock_only": False,
                    "fx3_unexposed_feature_exposed": False,
                    "fx6_body_ibis_supported": False,
                    "fx6_has_future_nd_knob": False,
                },
            }
            (r76_dir / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
            p6, meta6 = _evaluate_pillar_6(
                repo_root=tmp_root,
                use_clean_room=True,
                faults=RealHwMilestone364FaultInjection(),
                p1_meta=m1,
                p2_meta=m2,
                p3_meta=m3,
                p4_meta=m4,
                p5_meta=m5,
            )
            self.assertTrue(p6.passed, p6.errors)
            self.assertGreaterEqual(meta6["qemu_rounds_verified"], 49)
            self.assertGreaterEqual(meta6["qemu_runs_verified"], 147)
            self.assertGreaterEqual(meta6["qemu_png_receipts_verified"], 98)

    def test_64_pillar6_f141c0e17_negative_bool_rule_enforces_broken_audit_fail_closed(self) -> None:
        for k in (
            "fx3_has_builtin_evf",
            "fx3_future_dormant_present",
            "fx6_sdi_only",
            "fx3_dormant_exposed",
            "fx6_ibis_supported",
            "fx6_has_fan_control_max",
        ):
            self.assertTrue(_is_negative_audit_bool_key(k), k)
        for k in (
            "all_3_runs_crashes_zero",
            "r76a_stageb_verified",
            "fx3_702_baseline_verified",
        ):
            self.assertFalse(_is_negative_audit_bool_key(k), k)

        m1, m2, m3, m4, m5 = self._clean_p1_to_p5_metas()
        with tempfile.TemporaryDirectory() as tmp:
            tmp_root = Path(tmp)
            r76_dir = tmp_root / "reports" / "2026-11-18-round76-realhw-broken-qemu"
            r76_dir.mkdir(parents=True, exist_ok=True)
            summary = {
                "schema": "fx6-on-fx3-round76-broken-v1",
                "round": 76,
                "kernel_version": "Linux version 4.9.337-scel+ (clean-room-synthetic)",
                "raw_firmware_bytes_leaked": 0,
                "runs": {
                    "r76a_run": {"nop_count": 0, "crashes": 0, "emmc_write_count": 0, "stage_b": {"manifest_count": 13}},
                },
                "r76_broken_audit": {
                    "all_3_runs_crashes_zero": True,
                    "fx3_has_builtin_evf": True,
                },
            }
            (r76_dir / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
            p6, _ = _evaluate_pillar_6(
                repo_root=tmp_root,
                use_clean_room=True,
                faults=RealHwMilestone364FaultInjection(),
                p1_meta=m1,
                p2_meta=m2,
                p3_meta=m3,
                p4_meta=m4,
                p5_meta=m5,
            )
            self.assertFalse(p6.passed)

            # Also verify non-negative audit bool=False fails closed
            summary["r76_broken_audit"] = {
                "all_3_runs_crashes_zero": False,
                "fx3_has_builtin_evf": False,
            }
            (r76_dir / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
            p6_b, _ = _evaluate_pillar_6(
                repo_root=tmp_root,
                use_clean_room=True,
                faults=RealHwMilestone364FaultInjection(),
                p1_meta=m1,
                p2_meta=m2,
                p3_meta=m3,
                p4_meta=m4,
                p5_meta=m5,
            )
            self.assertFalse(p6_b.passed)

    def test_65_pillar6_fails_on_rounds73_to_75_schema_tamper(self) -> None:
        m1, m2, m3, m4, m5 = self._clean_p1_to_p5_metas()
        for rnum in range(73, 76):
            p6, _ = _evaluate_pillar_6(
                repo_root=REPO_ROOT,
                use_clean_room=True,
                faults=RealHwMilestone364FaultInjection(p6_tamper_schema_round_num=rnum),
                p1_meta=m1,
                p2_meta=m2,
                p3_meta=m3,
                p4_meta=m4,
                p5_meta=m5,
            )
            self.assertFalse(p6.passed, rnum)

    def test_66_pillar6_fails_on_round75_nop_crash_emmc_write_or_raw_leak(self) -> None:
        m1, m2, m3, m4, m5 = self._clean_p1_to_p5_metas()
        for fkw in (
            {"p6_round_nop_override_num": 75, "p6_round_nop_count_override": 1},
            {"p6_round_crash_override_num": 75, "p6_round_crashes_override": 1},
            {"p6_round_emmc_override_num": 75, "p6_round_emmc_writes_override": 1},
            {"p6_raw_firmware_bytes_leaked_override": 8},
        ):
            p6, _ = _evaluate_pillar_6(
                repo_root=REPO_ROOT,
                use_clean_room=True,
                faults=RealHwMilestone364FaultInjection(**fkw),
                p1_meta=m1,
                p2_meta=m2,
                p3_meta=m3,
                p4_meta=m4,
                p5_meta=m5,
            )
            self.assertFalse(p6.passed, fkw)

    def test_67_pillar6_fails_when_png_receipt_reaches_or_exceeds_50kib_ceiling(self) -> None:
        m1, m2, m3, m4, m5 = self._clean_p1_to_p5_metas()
        p6, _ = _evaluate_pillar_6(
            repo_root=REPO_ROOT,
            use_clean_room=True,
            faults=RealHwMilestone364FaultInjection(
                p6_png_size_override_round_num=75,
                p6_png_size_override_bytes=PNG_MAX_SIZE_50KIB_BYTES,
            ),
            p1_meta=m1,
            p2_meta=m2,
            p3_meta=m3,
            p4_meta=m4,
            p5_meta=m5,
        )
        self.assertFalse(p6.passed)

    def test_68_pillar6_cross_pillar_p1_cross_model_and_p2_cnflasha_invariants_fail(self) -> None:
        m1, m2, m3, m4, m5 = self._clean_p1_to_p5_metas()
        m1_bad = dict(m1)
        m1_bad["cross_model_flash_authorized"] = True
        self.assertFalse(
            _evaluate_pillar_6(
                repo_root=REPO_ROOT,
                use_clean_room=True,
                faults=RealHwMilestone364FaultInjection(),
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
                faults=RealHwMilestone364FaultInjection(),
                p1_meta=m1,
                p2_meta=m2_bad,
                p3_meta=m3,
                p4_meta=m4,
                p5_meta=m5,
            )[0].passed
        )

    def test_69_pillar6_cross_pillar_p3_and_p4_mutation_invariants_fail(self) -> None:
        m1, m2, m3, m4, m5 = self._clean_p1_to_p5_metas()
        m3_bad = dict(m3)
        m3_bad["calibration_mutation_bytes"] = 4
        self.assertFalse(
            _evaluate_pillar_6(
                repo_root=REPO_ROOT,
                use_clean_room=True,
                faults=RealHwMilestone364FaultInjection(),
                p1_meta=m1,
                p2_meta=m2,
                p3_meta=m3_bad,
                p4_meta=m4,
                p5_meta=m5,
            )[0].passed
        )

        m4_bad = dict(m4)
        m4_bad["cp_mutation_bytes"] = 16
        self.assertFalse(
            _evaluate_pillar_6(
                repo_root=REPO_ROOT,
                use_clean_room=True,
                faults=RealHwMilestone364FaultInjection(),
                p1_meta=m1,
                p2_meta=m2,
                p3_meta=m3,
                p4_meta=m4_bad,
                p5_meta=m5,
            )[0].passed
        )

    def test_70_pillar6_cross_pillar_p354_and_p358_h0_h3_rf_end_slot1_fail_closed(self) -> None:
        m1, m2, m3, m4, m5 = self._clean_p1_to_p5_metas()
        for tag in ("p354", "p358"):
            for bad_k, bad_v in (
                (f"{tag}_h0_equals_h3_count", 15),
                (f"{tag}_hardware_live_attachment_authorized", True),
                (f"{tag}_wireless_rf_packets_emitted", 1),
                (f"{tag}_e_nd_actuator_tx_count", 1),
                (f"{tag}_slot1_data_sector_writes", 1),
            ):
                m5_bad = dict(m5)
                m5_bad[bad_k] = bad_v
                p6_bad, _ = _evaluate_pillar_6(
                    repo_root=REPO_ROOT,
                    use_clean_room=True,
                    faults=RealHwMilestone364FaultInjection(),
                    p1_meta=m1,
                    p2_meta=m2,
                    p3_meta=m3,
                    p4_meta=m4,
                    p5_meta=m5_bad,
                )
                self.assertFalse(p6_bad.passed, bad_k)

    def test_71_pillar6_fails_if_bench_preflight_verifier_count_not_22(self) -> None:
        m1, m2, m3, m4, m5 = self._clean_p1_to_p5_metas()
        m5_bad = dict(m5)
        m5_bad["bench_preflight_verifier_count"] = 21
        p6_bad, _ = _evaluate_pillar_6(
            repo_root=REPO_ROOT,
            use_clean_room=True,
            faults=RealHwMilestone364FaultInjection(),
            p1_meta=m1,
            p2_meta=m2,
            p3_meta=m3,
            p4_meta=m4,
            p5_meta=m5_bad,
        )
        self.assertFalse(p6_bad.passed)

    def test_72_pillar6_records_historical_milestone_schema_anchors(self) -> None:
        p6_ev = self.rep_clean.pillars[5].evidence
        for m_num in (175, 193, 209, 221, 233, 254, 264, 295, 311, 324, 349):
            key = f"milestone{m_num}_schema_anchor"
            self.assertEqual(p6_ev[key], f"realhw_milestone{m_num}_master_gate_v1", key)

    # --- 9. Fail-Closed Verifier, CLI, 4-Mode & Donorless CI ---

    def test_73_verifier_rejects_non_mapping_payload(self) -> None:
        self.assertFalse(verify_realhw_milestone364_master_gate("not-a-dict").valid)
        self.assertFalse(verify_realhw_milestone364_master_gate(123).valid)
        self.assertFalse(verify_realhw_milestone364_master_gate(None).valid)  # type: ignore[arg-type]

    def test_74_verifier_rejects_sha256_tamper_and_schema_tamper(self) -> None:
        d = self.rep_clean.to_dict()
        d["milestone364_sha256"] = "f" * 64
        self.assertFalse(verify_realhw_milestone364_master_gate(d).valid)

        d2 = self.rep_clean.to_dict()
        d2["schema"] = "wrong_schema_v1"
        d2["milestone364_sha256"] = compute_milestone364_sha256(d2)
        self.assertFalse(verify_realhw_milestone364_master_gate(d2).valid)

    def test_75_verifier_rejects_redline_tamper_even_when_rehashed(self) -> None:
        tamper_cases = [
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
        ]
        for tag in ("p316", "p321", "p329", "p334", "p338", "p341", "p342", "p345", "p354", "p358"):
            tamper_cases.extend(
                [
                    (f"{tag}_hardware_live_attachment_authorized", True),
                    (f"{tag}_wireless_rf_packets_emitted", 1),
                    (f"{tag}_slot1_data_sector_writes", 1),
                ]
            )
        for k, v in tamper_cases:
            d = self.rep_clean.to_dict()
            d[k] = v
            d["milestone364_sha256"] = compute_milestone364_sha256(d)
            self.assertFalse(verify_realhw_milestone364_master_gate(d).valid, k)

    def test_76_verifier_accepts_forward_compatible_higher_counts(self) -> None:
        d = self.rep_clean.to_dict()
        d["gate156_total_gates"] = 158
        d["gate156_offline_verified"] = 155
        d["gate156_simulated_verified"] = 158
        d["recovery_pillar_count"] = 66
        d["recovery_pillars_passed"] = 66
        d["auditors_total"] = 46
        d["auditors_passed"] = 46
        d["vm_stages_total"] = 81
        d["vm_stages_passed"] = 81
        d["qemu_rounds_total"] = 49
        d["qemu_rounds_verified"] = 49
        d["qemu_runs_total"] = 147
        d["qemu_runs_verified"] = 147
        d["qemu_png_receipts_total"] = 98
        d["qemu_png_receipts_verified"] = 98
        d["milestone364_sha256"] = compute_milestone364_sha256(d)
        v = verify_realhw_milestone364_master_gate(d)
        self.assertTrue(v.valid, v.errors)

    def test_77_verifier_rejects_sub_threshold_counts_and_raw_bytes(self) -> None:
        for k, v in (
            ("gate156_simulated_verified", 155),
            ("recovery_pillar_count", 64),
            ("auditors_passed", 44),
            ("vm_stages_passed", 79),
            ("bench_preflight_verifier_count", 21),
            ("p354_sim_check_groups_passed", 3),
            ("p358_sim_check_groups_passed", 3),
            ("qemu_rounds_verified", 47),
            ("qemu_runs_verified", 143),
            ("qemu_png_receipts_verified", 95),
            ("qemu_png_max_bytes", PNG_MAX_SIZE_50KIB_BYTES),
        ):
            d = self.rep_clean.to_dict()
            d[k] = v
            d["milestone364_sha256"] = compute_milestone364_sha256(d)
            self.assertFalse(verify_realhw_milestone364_master_gate(d).valid, k)

        d_raw = self.rep_clean.to_dict()
        d_raw["pillars"][0]["summary"] = "leaked b'\\x7fELF'"
        d_raw["milestone364_sha256"] = compute_milestone364_sha256(d_raw)
        self.assertFalse(verify_realhw_milestone364_master_gate(d_raw).valid)

    def test_78_verifier_rejects_h0_h3_drift_when_rehashed(self) -> None:
        for k, v in (
            ("p143_h0_equals_h3_count", 15),
            ("p154_bench_go", False),
            ("p354_h0_equals_h3_count", 15),
            ("p358_h0_equals_h3_count", 15),
            ("h0_equals_h3_count", 15),
        ):
            d = self.rep_clean.to_dict()
            d[k] = v
            d["milestone364_sha256"] = compute_milestone364_sha256(d)
            self.assertFalse(verify_realhw_milestone364_master_gate(d).valid, k)

    def test_79_cli_verify_milestone_364_summary_and_out_alias_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            out_json = tmp_path / "m364.json"
            out_md = tmp_path / "m364.md"
            buf = io.StringIO()
            with (
                mock.patch(
                    "fx6_closure.realhw_milestone364_master_gate.evaluate_realhw_milestone364_master_gate",
                    return_value=self.rep_clean,
                ),
                mock.patch("sys.stdout", buf),
            ):
                rc = fx6_cli_main(
                    [
                        "verify-milestone-364",
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
            self.assertIn("schema=realhw_milestone364_master_gate_v1", text)
            self.assertIn("cnflasha_ro=True", text)
            self.assertIn("cross_model_flash_auth=False", text)
            self.assertIn("preflights=22/22", text)
            self.assertIn("p354=DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH", text)
            self.assertIn("p358=DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH", text)
            self.assertIn("rf_pkts=0", text)
            self.assertIn("slot1_writes=0", text)
            self.assertIn("ready_attach=False", text)
            self.assertIsNotNone(re.search(r"gate156=(\d+)/(\d+)", text))
            self.assertIsNotNone(re.search(r"qemu=(\d+)/(\d+)\((\d+)/(\d+)\)", text))
            self.assertTrue(out_json.is_file())
            self.assertTrue(out_md.is_file())
            self.assertTrue(
                verify_realhw_milestone364_master_gate(json.loads(out_json.read_text())).valid
            )

    def test_80_cli_verify_milestone_364_json_stdout_and_failure_exit_code(self) -> None:
        buf = io.StringIO()
        with (
            mock.patch(
                "fx6_closure.realhw_milestone364_master_gate.evaluate_realhw_milestone364_master_gate",
                return_value=self.rep_clean,
            ),
            mock.patch("sys.stdout", buf),
        ):
            rc = fx6_cli_main(["verify-milestone-364", "--clean-room", "--json"])
        self.assertEqual(rc, 0)
        parsed = json.loads(buf.getvalue())
        self.assertEqual(parsed["schema"], REALHW_MILESTONE364_SCHEMA)
        self.assertEqual(parsed["usb_packets_transmitted"], 0)
        self.assertEqual(parsed["bench_preflight_verifier_count"], 22)
        self.assertFalse(parsed["overall_ready_for_hardware_attach"])
        self.assertFalse(parsed["cross_model_flash_authorized"])

        bad_rep = replace(
            self.rep_clean,
            all_pillars_milestone_ready=False,
            status=STATUS_FAIL_CLOSED,
            passed_pillar_count=5,
            failed_pillar_ids=("P1",),
            milestone364_sha256="0" * 64,
        )
        buf2 = io.StringIO()
        with (
            mock.patch(
                "fx6_closure.realhw_milestone364_master_gate.evaluate_realhw_milestone364_master_gate",
                return_value=bad_rep,
            ),
            mock.patch("sys.stdout", buf2),
        ):
            rc2 = fx6_cli_main(["verify-milestone-364", "--force-clean-room"])
        self.assertEqual(rc2, 1)
        self.assertIn("status=FAILED", buf2.getvalue())

    def test_81_cli_verify_milestone_364_simulate_bench_dry_run_flag(self) -> None:
        captured: dict = {}

        def _fake_eval(**kwargs):
            captured.update(kwargs)
            return self.rep_clean

        buf = io.StringIO()
        with (
            mock.patch(
                "fx6_closure.realhw_milestone364_master_gate.evaluate_realhw_milestone364_master_gate",
                side_effect=_fake_eval,
            ),
            mock.patch("sys.stdout", buf),
        ):
            rc = fx6_cli_main(
                ["verify-milestone-364", "--force-clean-room", "--simulate-bench-dry-run", "--json"]
            )
        self.assertEqual(rc, 0)
        self.assertTrue(captured.get("simulate_bench_dry_run"))
        self.assertTrue(captured.get("force_clean_room"))

    def test_82_verify_milestone_364_cli_direct_helper_entrypoint(self) -> None:
        buf = io.StringIO()
        with (
            mock.patch(
                "fx6_closure.realhw_milestone364_master_gate.evaluate_realhw_milestone364_master_gate",
                return_value=self.rep_clean,
            ),
            mock.patch("sys.stdout", buf),
        ):
            rc = verify_milestone_364_cli(["--clean-room", "--simulate-bench-dry-run", "--json"])
        self.assertEqual(rc, 0)
        parsed = json.loads(buf.getvalue())
        self.assertEqual(parsed["schema"], REALHW_MILESTONE364_SCHEMA)
        self.assertTrue(parsed["cnflasha_userspace_write_blocked"])

    def test_83_argparse_help_formatting_safe_for_python_314_and_macos(self) -> None:
        buf_top = io.StringIO()
        with mock.patch("sys.stdout", buf_top):
            with self.assertRaises(SystemExit) as ctx_top:
                fx6_cli_main(["--help"])
        self.assertEqual(ctx_top.exception.code, 0)
        self.assertIn("verify-milestone-364", buf_top.getvalue())

        buf_sub = io.StringIO()
        with mock.patch("sys.stdout", buf_sub):
            with self.assertRaises(SystemExit) as ctx_sub:
                fx6_cli_main(["verify-milestone-364", "--help"])
        self.assertEqual(ctx_sub.exception.code, 0)
        self.assertIn("--force-clean-room", buf_sub.getvalue())
        self.assertIn("--simulate-bench-dry-run", buf_sub.getvalue())
        self.assertNotIn("%(", buf_sub.getvalue())

    def test_84_subprocess_cli_clean_room_via_fx3_fx6_force_clean_room(self) -> None:
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
                "verify-milestone-364",
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
        self.assertEqual(payload["schema"], REALHW_MILESTONE364_SCHEMA)
        self.assertTrue(payload["all_pillars_milestone_ready"])
        self.assertGreaterEqual(payload["gate156_simulated_verified"], 156)
        self.assertGreaterEqual(payload["recovery_pillars_passed"], 65)
        self.assertGreaterEqual(payload["auditors_passed"], 45)
        self.assertGreaterEqual(payload["vm_stages_passed"], 80)
        self.assertEqual(payload["bench_preflight_verifier_count"], 22)
        self.assertGreaterEqual(payload["qemu_rounds_verified"], 48)
        self.assertGreaterEqual(payload["qemu_runs_verified"], 144)
        self.assertGreaterEqual(payload["qemu_png_receipts_verified"], 96)
        self.assertLess(elapsed, _ci_time_budget(30.0))

    def test_85_subprocess_cli_clean_room_via_fx3_clean_room_test_env(self) -> None:
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
                "verify-milestone-364",
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
        self.assertEqual(payload["schema"], REALHW_MILESTONE364_SCHEMA)
        self.assertTrue(payload["all_pillars_milestone_ready"])
        self.assertGreaterEqual(payload["gate156_simulated_verified"], 156)
        self.assertGreaterEqual(payload["recovery_pillars_passed"], 65)
        self.assertEqual(payload["bench_preflight_verifier_count"], 22)
        self.assertLess(elapsed, _ci_time_budget(30.0))

    def test_86_synthetic_clean_room_kwarg_alias_and_suite_runtime_budget(self) -> None:
        rep = evaluate_milestone_364_master_gate(
            synthetic_clean_room=True,
            _raw_bundle_override=self._unpack_clean_raw(),
        )
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(rep.all_pillars_milestone_ready)
        self.assertLess(self.default_elapsed_s, _ci_time_budget(30.0))

    def test_87_donorless_linux_ci_repo_without_mac_work_auto_clean_room(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            troot = Path(tmp)
            for item in REPO_ROOT.iterdir():
                if item.name != "Mac":
                    (troot / item.name).symlink_to(item.resolve())
            rep = evaluate_realhw_milestone364_master_gate(
                repo_root=troot,
                fx6_lib_dir=troot / "nonexistent_fx6",
                fx3_modules_dir=troot / "nonexistent_fx3",
                work_root=None,
                force_clean_room=None,
            )
            self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertTrue(rep.all_pillars_milestone_ready, rep.errors)
            self.assertEqual(rep.passed_pillar_count, 6)
            self.assertTrue(verify_realhw_milestone364_master_gate(rep).valid)

    def test_88_preserves_milestone_349_and_earlier_and_readme_section_66(self) -> None:
        self.assertTrue(hasattr(fx6_closure, "evaluate_realhw_milestone349_master_gate"))
        self.assertTrue(hasattr(fx6_closure, "evaluate_realhw_milestone324_master_gate"))
        self.assertTrue(hasattr(fx6_closure, "evaluate_realhw_milestone311_master_gate"))
        self.assertTrue(hasattr(fx6_closure, "evaluate_realhw_milestone295_master_gate"))
        self.assertTrue(hasattr(fx6_closure, "evaluate_realhw_milestone264_master_gate"))
        self.assertTrue(hasattr(fx6_closure, "evaluate_realhw_milestone254_master_gate"))
        self.assertNotEqual(fx6_closure.REALHW_MILESTONE349_SCHEMA, fx6_closure.REALHW_MILESTONE364_SCHEMA)
        self.assertEqual(
            fx6_closure.evaluate_realhw_milestone364_master_gate,
            evaluate_realhw_milestone364_master_gate,
        )
        readme_text = (REPO_ROOT / "outputs" / "fx6-on-fx3-closure" / "README.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("# 66.", readme_text)
        self.assertIn("verify-milestone-364", readme_text)
        self.assertIn("realhw_milestone364_master_gate_v1", readme_text)

    def test_89_pillar1_rejects_m349_or_m324_cascaded_faults(self) -> None:
        f = RealHwMilestone364FaultInjection(
            m349_faults=RealHwMilestone349FaultInjection(
                p1_breathing_camid_reel_kwargs={
                    "fx6_breathing_under_sq_or_raw_or_distortion_off_requested": True
                }
            )
        )
        w = _fault_to_156gate_worker_dict(f)
        bad_sim = _worker_156plus_gate_single((str(REPO_ROOT), True, True, w, True))
        raw_off = self._unpack_clean_raw()[0]
        self.assertFalse(_evaluate_pillar_1(raw_off, bad_sim).passed)

    def test_90_pillar2_fails_on_missing_or_mismatched_pillar_count(self) -> None:
        rec_65 = self._unpack_clean_raw()[2]
        rec_65["pillar_count"] = 64
        rec_65["pillars_passed"] = 64
        rec_65["status"] = "VERIFIED_64OF64_PILLAR_RECOVERY_MASTER"
        self.assertFalse(_evaluate_pillar_2(rec_65, RealHwMilestone364FaultInjection())[0].passed)

    def test_91_pillar5_propagates_phase354_and_phase358_via_fault_injection(self) -> None:
        raw_p136 = self.raw_bundle[5]
        _ = raw_p136  # confirm clean fixture loaded
        o54, s54, o58, s58 = _worker_phase354_358(
            (
                None,
                None,
                True,
                True,
                {"lockop_shocklesswb_focusmag_afspeed_zebra_saveload_camset": True},
                {"metering_pplut_ibis_customkey_diffset8_gammadisp_usblan_cleaning": True},
            )
        )
        b = list(self._unpack_clean_raw())
        b[48], b[49], b[50], b[51] = o54, s54, o58, s58
        p5, _ = _evaluate_pillar_5(*b[5:52], RealHwMilestone364FaultInjection())
        self.assertFalse(p5.passed)
        self.assertTrue(any("p354" in e for e in p5.errors))
        self.assertTrue(any("p358" in e for e in p5.errors))

    def test_92_pillar6_rejects_round76plus_invalid_png_or_kernel_mismatch(self) -> None:
        m1, m2, m3, m4, m5 = self._clean_p1_to_p5_metas()
        with tempfile.TemporaryDirectory() as tmp:
            tmp_root = Path(tmp)
            r76_dir = tmp_root / "reports" / "2026-11-18-round76-bad-png-qemu"
            assets_dir = r76_dir / "assets"
            assets_dir.mkdir(parents=True, exist_ok=True)
            (assets_dir / "bad.png").write_bytes(b"NOTPNG" + b"\x00" * 32)
            summary = {
                "schema": "fx6-on-fx3-round76-bad-png-v1",
                "round": 76,
                "kernel_version": "Linux version 5.15.0-wrong (clean-room)",
                "raw_firmware_bytes_leaked": 0,
                "runs": {
                    "r76a_run": {"nop_count": 0, "crashes": 0, "emmc_write_count": 0, "stage_b": {"manifest_count": 13}},
                },
                "r76_bad_audit": {"all_3_runs_crashes_zero": True},
            }
            (r76_dir / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
            p6, _ = _evaluate_pillar_6(
                repo_root=tmp_root,
                use_clean_room=True,
                faults=RealHwMilestone364FaultInjection(),
                p1_meta=m1,
                p2_meta=m2,
                p3_meta=m3,
                p4_meta=m4,
                p5_meta=m5,
            )
            self.assertFalse(p6.passed)

    def test_93_verifier_rejects_missing_or_failed_pillar_entries(self) -> None:
        d = self.rep_clean.to_dict()
        d["pillars"][3]["passed"] = False
        d["pillars"][3]["status"] = STATUS_FAIL_CLOSED
        d["milestone364_sha256"] = compute_milestone364_sha256(d)
        v = verify_realhw_milestone364_master_gate(d)
        self.assertFalse(v.valid)
        self.assertFalse(v.all_6_pillars_ok)

    def test_94_all_pillars_evidence_keys_present_and_typed(self) -> None:
        self.assertEqual(len(self.rep_clean.pillars), 6)
        for p in self.rep_clean.pillars:
            self.assertTrue(p.passed, p.errors)
            self.assertEqual(p.status, STATUS_MILESTONE_READY)
            self.assertIsInstance(p.evidence, dict)
            self.assertGreater(len(p.evidence), 0)

    def test_95_report_hardware_live_attachment_requirements_preserved(self) -> None:
        self.assertGreaterEqual(len(self.rep_clean.hardware_live_attachment_requirements), 1)
        self.assertFalse(self.rep_clean.hardware_live_attachment_authorized)
        self.assertFalse(self.rep_clean.overall_ready_for_hardware_attach)

    def test_96_subprocess_dual_cli_m349_also_green_in_clean_room(self) -> None:
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
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "fx6_closure",
                "verify-milestone-349",
                "--force-clean-room",
                "--json",
            ],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["schema"], "realhw_milestone349_master_gate_v1")
        self.assertTrue(payload["all_pillars_milestone_ready"])
        self.assertEqual(payload["bench_preflight_verifier_count"], 20)


if __name__ == "__main__":
    unittest.main()
