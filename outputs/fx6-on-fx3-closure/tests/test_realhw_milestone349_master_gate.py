"""Phase 349 4-mode unit tests for Grand Milestone Phase 349 6-Pillar Real-Hardware Master Gate."""

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
    _worker_phase316_321,
)
from fx6_closure.realhw_milestone349_master_gate import (  # noqa: E402
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
    MILESTONE349_SCHEMA_VERSION,
    OTP_FUSE_TOUCHES,
    OTP_FUSE_WRITES,
    OVERALL_READY_FOR_HARDWARE_ATTACH,
    P8_CP_MUTATION_FORBIDDEN,
    P349_BASELINE_PNG_MAX_OBSERVED_BYTES,
    P349_PHYSICAL_DEVICE_WRITES,
    P349_PILLAR_IDS,
    P349_PILLAR_SPECS,
    P349_PNG_MAX_SIZE_BYTES,
    P349_RAW_FIRMWARE_BYTES_LEAKED,
    P349_SCHEMA,
    P349_STATUS_FAIL_CLOSED,
    P349_STATUS_MILESTONE_READY,
    P349_VERSION,
    PASSIVE_TX_BYTES,
    PASSIVE_TX_BYTES_EMITTED,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHASE_349_VERSION,
    PHYSICAL_DEVICE_WRITES,
    PHYSICAL_USB_PACKETS_EMITTED,
    PILLAR_IDS,
    PILLAR_SPECS,
    PNG_MAGIC_BYTES,
    PNG_MAX_SIZE_50KIB_BYTES,
    PNG_MAX_SIZE_BYTES,
    RAW_FIRMWARE_BYTES_LEAKED,
    REALHW_MILESTONE349_SCHEMA,
    RECOVERY_62_PILLAR_IDS,
    ROUND28_TO_72_PNG_RECEIPTS,
    ROUND28_TO_72_SPECS,
    ROUND66_EXPECTED_SCHEMA,
    ROUND67_EXPECTED_SCHEMA,
    ROUND68_EXPECTED_SCHEMA,
    ROUND69_EXPECTED_SCHEMA,
    ROUND70_EXPECTED_SCHEMA,
    ROUND71_EXPECTED_SCHEMA,
    ROUND72_EXPECTED_SCHEMA,
    RPMB_COUNTER_INCREMENTS,
    RPMB_WRITES,
    SPI_NOR_WRITE_AUTHORIZED,
    STATUS_FAIL_CLOSED,
    STATUS_MILESTONE_READY,
    USB_OR_CAMERA_OPERATIONS,
    USB_PACKETS_TRANSMITTED,
    VM_COEMULATION_75_STAGE_KEYS,
    WBI_MUTATION_BYTES,
    WBI_P5_WRITE_AND_HIBERNATION_FORBIDDEN,
    RealHwMilestone349FaultInjection,
    RealHwMilestone349MasterGateReport,
    _collect_parallel_milestone349_results,
    _discover_highest_recovery_master,
    _discover_highest_safety_gate_evaluator,
    _evaluate_pillar_1,
    _evaluate_pillar_2,
    _evaluate_pillar_3,
    _evaluate_pillar_4,
    _evaluate_pillar_5,
    _evaluate_pillar_6,
    _fault_to_148gate_worker_dict,
    _normalize_62plus_pillar_fault_id,
    _worker_148plus_gate_single,
    _worker_phase329_334,
    _worker_phase338_341,
    _worker_phase342_345,
    _worker_recovery_62plus_pillar,
    build_realhw_milestone349_master_gate_report,
    compute_milestone349_sha256,
    evaluate_milestone349_master_gate,
    evaluate_milestone_349_master_gate,
    evaluate_realhw_milestone349_master_gate,
    render_milestone349_markdown,
    verify_milestone_349_cli,
    verify_milestone_349_master_gate,
    verify_realhw_milestone349_master_gate,
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

    g148_fdict = _fault_to_148gate_worker_dict(
        RealHwMilestone349FaultInjection(
            p1_breathing_camid_reel_kwargs={
                "card_type": "SDHC",
                "sdhc_4gb_split_bypass_requested": True,
            },
            p1_copyright_powersave_ntscpal_kwargs={
                "claimed_camset_reset_clears_copyright_strings": True
            },
            p1_request_persistent_writes=True,
        )
    )
    fx6_s = str(DEFAULT_FX6_DONOR_LIB_DIR)
    fx3_s = str(DEFAULT_FX3_MODULES_DIR)
    ctx = mp.get_context("fork")
    with ProcessPoolExecutor(max_workers=6, mp_context=ctx) as pool:
        fut_g148 = pool.submit(
            _worker_148plus_gate_single,
            (str(REPO_ROOT), True, True, g148_fdict, False),
        )
        fut_p62 = pool.submit(_worker_recovery_62plus_pillar, (True, "pillar_62"))
        fut_329_334_fault = pool.submit(
            _worker_phase329_334,
            (
                fx6_s,
                fx3_s,
                True,
                False,
                {"shoe_audio_subject_hdmi_raw_desqueeze_varshutter": True},
                {"breathing_camid_copyright_powersave_zoom_rawcomp_usblun": True},
            ),
        )
        fut_329_334_drift = pool.submit(
            _worker_phase329_334,
            (fx6_s, fx3_s, True, False, {"h0_h3_drift": True}, {"h0_h3_drift": True}),
        )
        fut_338_341_fault = pool.submit(
            _worker_phase338_341,
            (
                fx6_s,
                fx3_s,
                True,
                False,
                {"drive_focusbracket_efcs_creativelook_pixelmap_monitor_recallhold_hdmi_tc": True},
                {"area_date_dst_grid_cleanhdmi_camset_mishoe_pb_magnify_wifi_5ghz_cec": True},
            ),
        )
        fut_338_341_drift = pool.submit(
            _worker_phase338_341,
            (fx6_s, fx3_s, True, False, {"h0_h3_drift": True}, {"h0_h3_drift": True}),
        )
        fut_342_345_fault = pool.submit(
            _worker_phase342_345,
            (
                fx6_s,
                fx3_s,
                True,
                False,
                {"peaking_audio_wind_usb_pd_ntsc_pal_antidust_focus_mag_expstd_usbtether": True},
                {"audio_reclevel_outtiming_4ch_mon_touch_dormant_remote_shoot": True},
            ),
        )
        fut_342_345_drift = pool.submit(
            _worker_phase342_345,
            (fx6_s, fx3_s, True, False, {"h0_h3_drift": True}, {"h0_h3_drift": True}),
        )
        fut_316_321_fault = pool.submit(
            _worker_phase316_321,
            (fx6_s, fx3_s, True, {}, {"rec_media_proxy_cloud_mymenu_ftpes": True}),
        )
        bad_g148 = fut_g148.result()
        bad_p62 = fut_p62.result()
        p329_334_bad = fut_329_334_fault.result()
        p329_334_drift = fut_329_334_drift.result()
        p338_341_bad = fut_338_341_fault.result()
        p338_341_drift = fut_338_341_drift.result()
        p342_345_bad = fut_342_345_fault.result()
        p342_345_drift = fut_342_345_drift.result()
        p316_321_bad = fut_316_321_fault.result()
    conn.send(
        (
            bad_g148,
            bad_p62,
            p329_334_bad,
            p329_334_drift,
            p338_341_bad,
            p338_341_drift,
            p342_345_bad,
            p342_345_drift,
            p316_321_bad,
        )
    )
    conn.close()


class TestRealHwMilestone349MasterGate(unittest.TestCase):
    """Comprehensive 92 4-mode unit tests for Grand Milestone Phase 349."""

    raw_bundle: tuple
    rep_default: RealHwMilestone349MasterGateReport
    rep_clean: RealHwMilestone349MasterGateReport
    bad_sim_g148: dict
    bad_rec_62: dict
    p329_334_bad: tuple
    p329_334_drift: tuple
    p338_341_bad: tuple
    p338_341_drift: tuple
    p342_345_bad: tuple
    p342_345_drift: tuple
    p316_321_bad: tuple
    default_elapsed_s: float

    @classmethod
    def setUpClass(cls) -> None:
        import multiprocessing as mp

        t0 = time.monotonic()
        ctx = mp.get_context("fork")
        if not _is_forced_clean_room():
            cls.rep_default = evaluate_milestone_349_master_gate()
        recv_conn, send_conn = ctx.Pipe(duplex=False)
        proc = ctx.Process(
            target=_fork_child_fault_fixtures_only,
            args=(send_conn,),
            daemon=False,
        )
        proc.start()
        send_conn.close()
        try:
            cls.raw_bundle = _collect_parallel_milestone349_results(
                repo_root=REPO_ROOT,
                fx6_lib_dir=DEFAULT_FX6_DONOR_LIB_DIR,
                fx3_modules_dir=DEFAULT_FX3_MODULES_DIR,
                use_clean_room=True,
                faults=RealHwMilestone349FaultInjection(),
            )
            (
                cls.bad_sim_g148,
                cls.bad_rec_62,
                cls.p329_334_bad,
                cls.p329_334_drift,
                cls.p338_341_bad,
                cls.p338_341_drift,
                cls.p342_345_bad,
                cls.p342_345_drift,
                cls.p316_321_bad,
            ) = recv_conn.recv()
        finally:
            recv_conn.close()
            proc.join(timeout=60)
        cls.rep_clean = evaluate_milestone_349_master_gate(
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
        self.assertEqual(REALHW_MILESTONE349_SCHEMA, "realhw_milestone349_master_gate_v1")
        self.assertEqual(MILESTONE349_SCHEMA_VERSION, REALHW_MILESTONE349_SCHEMA)
        self.assertEqual(P349_SCHEMA, REALHW_MILESTONE349_SCHEMA)
        self.assertEqual(PHASE_349_VERSION, "349.0.0")
        self.assertEqual(P349_VERSION, "349.0.0")
        self.assertEqual(PILLAR_IDS, ("P1", "P2", "P3", "P4", "P5", "P6"))
        self.assertEqual(P349_PILLAR_IDS, PILLAR_IDS)
        self.assertEqual(len(PILLAR_SPECS), 6)
        self.assertEqual(P349_PILLAR_SPECS, PILLAR_SPECS)
        self.assertGreaterEqual(len(RECOVERY_62_PILLAR_IDS), 62)
        self.assertGreaterEqual(len(FIRMWARE_LAB_45_AUDITOR_KEYS), 45)
        self.assertGreaterEqual(len(VM_COEMULATION_75_STAGE_KEYS), 75)
        self.assertGreaterEqual(len(ROUND28_TO_72_SPECS), 45)
        self.assertEqual(PNG_MAX_SIZE_50KIB_BYTES, 51200)
        self.assertEqual(PNG_MAX_SIZE_BYTES, 51200)
        self.assertEqual(P349_PNG_MAX_SIZE_BYTES, 51200)
        self.assertEqual(P349_BASELINE_PNG_MAX_OBSERVED_BYTES, 27467)

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
        self.assertEqual(P349_STATUS_MILESTONE_READY, STATUS_MILESTONE_READY)
        self.assertEqual(P349_STATUS_FAIL_CLOSED, STATUS_FAIL_CLOSED)
        for zero_const in (
            USB_PACKETS_TRANSMITTED,
            PHYSICAL_USB_PACKETS_EMITTED,
            PHYSICAL_DEVICE_WRITES,
            P349_PHYSICAL_DEVICE_WRITES,
            RAW_FIRMWARE_BYTES_LEAKED,
            P349_RAW_FIRMWARE_BYTES_LEAKED,
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
            "P349_CROSS_MODEL_FLASH_AUTHORIZED",
            "MILESTONE349_PHYSICAL_DEVICE_WRITES",
            "MILESTONE349_PILLAR_IDS",
            "MILESTONE349_PILLAR_SPECS",
            "MILESTONE349_PNG_MAX_SIZE_BYTES",
            "MILESTONE349_RAW_FIRMWARE_BYTES_LEAKED",
            "MILESTONE349_SCHEMA_VERSION",
            "P349_BASELINE_PNG_MAX_OBSERVED_BYTES",
            "P349_PHYSICAL_DEVICE_WRITES",
            "P349_PILLAR_IDS",
            "P349_PILLAR_SPECS",
            "P349_PNG_MAX_SIZE_BYTES",
            "P349_RAW_FIRMWARE_BYTES_LEAKED",
            "P349_SCHEMA",
            "P349_STATUS_FAIL_CLOSED",
            "P349_STATUS_MILESTONE_READY",
            "P349_VERSION",
            "PHASE_349_VERSION",
            "REALHW_MILESTONE349_SCHEMA",
            "RECOVERY_62_PILLAR_IDS",
            "ROUND28_TO_72_PNG_RECEIPTS",
            "ROUND28_TO_72_SPECS",
            "ROUND66_EXPECTED_SCHEMA",
            "ROUND67_EXPECTED_SCHEMA",
            "ROUND68_EXPECTED_SCHEMA",
            "ROUND69_EXPECTED_SCHEMA",
            "ROUND70_EXPECTED_SCHEMA",
            "ROUND71_EXPECTED_SCHEMA",
            "ROUND72_EXPECTED_SCHEMA",
            "STATUS_MILESTONE349_FAIL_CLOSED",
            "STATUS_MILESTONE349_READY",
            "VM_COEMULATION_75_STAGE_KEYS",
            "Milestone349PillarResult",
            "RealHwMilestone349FaultInjection",
            "RealHwMilestone349MasterGateReport",
            "RealHwMilestone349VerifyResult",
            "build_realhw_milestone349_master_gate_report",
            "compute_milestone349_sha256",
            "evaluate_milestone349_master_gate",
            "evaluate_milestone_349_master_gate",
            "evaluate_realhw_milestone349_master_gate",
            "render_milestone349_markdown",
            "verify_milestone_349_cli",
            "verify_milestone_349_master_gate",
            "verify_realhw_milestone349_master_gate",
        }
        self.assertTrue(expected.issubset(set(fx6_closure.__all__)))
        for sym in expected:
            self.assertTrue(hasattr(fx6_closure, sym), sym)
        self.assertEqual(fx6_closure.REALHW_MILESTONE324_SCHEMA, "realhw_milestone324_master_gate_v1")
        self.assertEqual(fx6_closure.REALHW_MILESTONE311_SCHEMA, "realhw_milestone311_master_gate_v1")
        self.assertEqual(fx6_closure.REALHW_MILESTONE295_SCHEMA, "realhw_milestone295_master_gate_v1")
        self.assertEqual(fx6_closure.REALHW_MILESTONE264_SCHEMA, "realhw_milestone264_master_gate_v1")
        self.assertEqual(fx6_closure.REALHW_MILESTONE254_SCHEMA, "realhw_milestone254_master_gate_v1")

    def test_04_builder_and_verifier_aliases_point_to_canonical_functions(self) -> None:
        self.assertIs(build_realhw_milestone349_master_gate_report, evaluate_realhw_milestone349_master_gate)
        self.assertIs(evaluate_milestone_349_master_gate, evaluate_realhw_milestone349_master_gate)
        self.assertIs(evaluate_milestone349_master_gate, evaluate_realhw_milestone349_master_gate)
        self.assertIs(verify_milestone_349_master_gate, verify_realhw_milestone349_master_gate)

    def test_05_rounds66_to_72_specs_and_png_pairs_registered(self) -> None:
        by_num = {s.round_num: s for s in ROUND28_TO_72_SPECS}
        self.assertGreaterEqual(len(by_num), 45)
        self.assertGreaterEqual(len(ROUND28_TO_72_PNG_RECEIPTS), 45)
        for rnum, exp_schema in (
            (66, ROUND66_EXPECTED_SCHEMA),
            (67, ROUND67_EXPECTED_SCHEMA),
            (68, ROUND68_EXPECTED_SCHEMA),
            (69, ROUND69_EXPECTED_SCHEMA),
            (70, ROUND70_EXPECTED_SCHEMA),
            (71, ROUND71_EXPECTED_SCHEMA),
            (72, ROUND72_EXPECTED_SCHEMA),
        ):
            self.assertIn(rnum, by_num)
            self.assertEqual(by_num[rnum].expected_schema, exp_schema)
            self.assertEqual(len(by_num[rnum].run_specs), 3)
            self.assertIn(rnum, ROUND28_TO_72_PNG_RECEIPTS)
            self.assertEqual(len(ROUND28_TO_72_PNG_RECEIPTS[rnum]), 2)
            for _, exp_faithful in by_num[rnum].run_specs:
                self.assertEqual(exp_faithful, 1)

    def test_06_normalize_62plus_pillar_fault_id_resolves_short_and_full_ids(self) -> None:
        self.assertIsNone(_normalize_62plus_pillar_fault_id(None))
        self.assertIsNone(_normalize_62plus_pillar_fault_id(""))
        for pnum in range(55, 63):
            full_id = RECOVERY_62_PILLAR_IDS[pnum - 1]
            self.assertEqual(_normalize_62plus_pillar_fault_id(f"pillar_{pnum}"), full_id)
            self.assertEqual(_normalize_62plus_pillar_fault_id(full_id), full_id)

    def test_07_dynamic_safety_evaluator_discovery_prefers_highest_148plus(self) -> None:
        real_n, real_fn = _discover_highest_safety_gate_evaluator()
        self.assertGreaterEqual(real_n, 148)
        self.assertTrue(callable(real_fn))

        class _FakeSafetyMod:
            @staticmethod
            def evaluate_148gate_preflight():
                return "148"

            @staticmethod
            def evaluate_150gate_preflight():
                return "150"

        best_n, best_fn = _discover_highest_safety_gate_evaluator(_FakeSafetyMod)
        self.assertEqual(best_n, 150)
        self.assertEqual(best_fn(), "150")

    def test_08_dynamic_recovery_master_discovery_prefers_highest_62plus(self) -> None:
        real_m, real_fn, real_ids = _discover_highest_recovery_master()
        self.assertGreaterEqual(real_m, 62)
        self.assertTrue(callable(real_fn))
        self.assertGreaterEqual(len(real_ids), 62)

        class _FakeRecoveryMod:
            MASTER_62_PILLAR_IDS = tuple(f"p_{i}" for i in range(1, 63))
            MASTER_63_PILLAR_IDS = tuple(f"p_{i}" for i in range(1, 64))

            @staticmethod
            def evaluate_realhw_62pillar_recovery_master():
                return 62

            @staticmethod
            def evaluate_realhw_63pillar_recovery_master():
                return 63

        best_m, best_fn, best_ids = _discover_highest_recovery_master(_FakeRecoveryMod)
        self.assertEqual(best_m, 63)
        self.assertEqual(best_fn(), 63)
        self.assertEqual(len(best_ids), 63)

    # --- 2. End-to-End 4-Mode Reports, Determinism & Markdown ---

    def test_09_default_mode_report_all_6_pillars_ready(self) -> None:
        rep = self.rep_default
        self.assertTrue(rep.all_pillars_milestone_ready, rep.errors)
        self.assertEqual(rep.status, STATUS_MILESTONE_READY)
        self.assertEqual(rep.passed_pillar_count, 6)
        self.assertEqual(rep.failed_pillar_ids, ())
        v = verify_realhw_milestone349_master_gate(rep)
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
        for tag in ("p316", "p321", "p329", "p334", "p338", "p341", "p342", "p345"):
            self.assertEqual(getattr(rep, f"{tag}_wireless_rf_packets_emitted"), 0, tag)
            self.assertEqual(getattr(rep, f"{tag}_rf_packets_transmitted"), 0, tag)
            self.assertEqual(getattr(rep, f"{tag}_e_nd_actuator_tx_count"), 0, tag)
            self.assertEqual(getattr(rep, f"{tag}_slot1_data_sector_writes"), 0, tag)
        self.assertTrue(verify_realhw_milestone349_master_gate(rep.to_dict()).valid)

    def test_11_fx3_clean_room_test_env_var_compatibility(self) -> None:
        with mock.patch.dict(os.environ, {"FX3_CLEAN_ROOM_TEST": "1"}, clear=False):
            rep = evaluate_milestone_349_master_gate(_raw_bundle_override=self._unpack_clean_raw())
            self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertTrue(rep.all_pillars_milestone_ready, rep.errors)
            self.assertEqual(rep.passed_pillar_count, 6)
            self.assertTrue(verify_realhw_milestone349_master_gate(rep).valid)

    def test_12_mocked_donorless_work_root_none_mode_passes_cleanly(self) -> None:
        rep = evaluate_realhw_milestone349_master_gate(
            fx6_lib_dir=None,
            fx3_modules_dir=None,
            work_root=None,
        )
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(rep.all_pillars_milestone_ready, rep.errors)
        self.assertEqual(rep.passed_pillar_count, 6)
        self.assertEqual(rep.bench_preflight_verifier_count, 20)
        self.assertGreaterEqual(rep.gate148_simulated_verified, 148)
        self.assertTrue(verify_realhw_milestone349_master_gate(rep).valid)

    def test_13_forward_compatible_lower_bounds_on_clean_report(self) -> None:
        rep = self.rep_clean
        self.assertGreaterEqual(rep.gate148_total_gates, 148)
        self.assertGreaterEqual(rep.gate148_offline_verified, 145)
        self.assertEqual(rep.gate148_offline_verified, rep.gate148_total_gates - 3)
        self.assertGreaterEqual(rep.gate148_simulated_verified, 148)
        self.assertEqual(rep.gate148_simulated_verified, rep.gate148_total_gates)
        self.assertTrue(rep.gate148_all_verified)
        self.assertGreaterEqual(rep.recovery_pillar_count, 62)
        self.assertEqual(rep.recovery_pillars_passed, rep.recovery_pillar_count)
        self.assertGreaterEqual(rep.auditors_passed, 45)
        self.assertEqual(rep.auditors_passed, rep.auditors_total)
        self.assertGreaterEqual(rep.vm_stages_passed, 75)
        self.assertEqual(rep.vm_stages_passed, rep.vm_stages_total)
        self.assertEqual(rep.bench_preflight_verifier_count, 20)
        self.assertGreaterEqual(rep.qemu_rounds_verified, 45)
        self.assertGreaterEqual(rep.qemu_runs_verified, 135)
        self.assertGreaterEqual(rep.qemu_png_receipts_verified, 90)
        self.assertLess(rep.qemu_png_max_bytes, PNG_MAX_SIZE_50KIB_BYTES)
        self.assertEqual(rep.h0_equals_h3_count, 16)
        self.assertEqual(rep.e_nd_actuator_tx_count, 0)
        self.assertEqual(rep.emmc_write_count, 0)

    def test_14_deterministic_json_and_sha256_recomputation(self) -> None:
        j1 = self.rep_clean.to_deterministic_json()
        parsed = json.loads(j1)
        self.assertEqual(compute_milestone349_sha256(parsed), self.rep_clean.milestone349_sha256)
        rep2 = evaluate_milestone_349_master_gate(
            force_clean_room=True,
            _raw_bundle_override=self._unpack_clean_raw(),
        )
        self.assertEqual(rep2.milestone349_sha256, self.rep_clean.milestone349_sha256)

    def test_15_no_raw_bytes_repr_in_serialized_reports(self) -> None:
        for rep in (self.rep_default, self.rep_clean):
            self.assertIsNone(re.search(_RAW_BYTES_REPR_REGEX, rep.to_deterministic_json()))

    def test_16_markdown_renderer_contains_bilingual_headers_and_20_preflights(self) -> None:
        md = render_milestone349_markdown(self.rep_clean)
        for token in (
            "Grand Milestone Phase 349",
            "realhw_milestone349_master_gate_v1",
            "MILESTONE_349_PREBENCH_MASTER_VERIFIED",
            "cross_model_flash_authorized = False",
            "148+-Gate Preflight",
            "62+-Pillar Recovery Master",
            "75+ Stage VM HIL",
            "20/20",
            "Ph186=",
            "Ph321=",
            "Ph329=",
            "Ph334=",
            "Ph338=",
            "Ph341=",
            "Ph342=",
            "Ph345=",
            "Rounds 28..72+",
            "| `P1` |",
            "| `P6` |",
        ):
            self.assertIn(token, md)

    # --- 3. Pillar 1: >= 148 Safety Gates (`evaluate_148gate_preflight`) ---

    def test_17_pillar1_148gate_happy_path_and_g63_to_g148_valid(self) -> None:
        raw_off, raw_sim = self._unpack_clean_raw()[:2]
        p1 = _evaluate_pillar_1(raw_off, raw_sim)
        self.assertTrue(p1.passed, p1.errors)
        self.assertGreaterEqual(p1.evidence["offline_verified_gates"], 145)
        self.assertGreaterEqual(p1.evidence["simulated_verified_gates"], 148)
        self.assertTrue(p1.evidence["all_148plus_gates_verified"])
        self.assertFalse(p1.evidence["cross_model_flash_authorized"])
        for idx in range(63, 149):
            self.assertTrue(p1.evidence["g63_to_gn_valid"][f"g{idx}"], f"g{idx}")

    def test_18_pillar1_forward_compatible_with_150_gates(self) -> None:
        raw_off, raw_sim = self._unpack_clean_raw()[:2]
        raw_off["total_gates"] = 150
        raw_off["verified_gates"] = 147
        raw_off["offline_minus3_verified"] = True
        raw_sim["total_gates"] = 150
        raw_sim["verified_gates"] = 150
        raw_sim["all_n_gates_verified"] = True
        raw_sim["nested_g_valid"]["g149"] = True
        raw_sim["nested_g_valid"]["g150"] = True
        p1 = _evaluate_pillar_1(raw_off, raw_sim)
        self.assertTrue(p1.passed, p1.errors)
        self.assertGreaterEqual(p1.evidence["simulated_verified_gates"], 150)

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

    def test_23_pillar1_fails_when_any_g143_to_g148_wave_gate_invalid(self) -> None:
        for gtag in ("g143", "g144", "g145", "g146", "g147", "g148"):
            raw_off, raw_sim = self._unpack_clean_raw()[:2]
            raw_sim["nested_g_valid"][gtag] = False
            p1 = _evaluate_pillar_1(raw_off, raw_sim)
            self.assertFalse(p1.passed, gtag)
            self.assertIn(gtag.upper(), p1.errors[-1])

    def test_24_pillar1_live_worker_g147_g148_and_persistent_write_fault(self) -> None:
        raw_sim_bad = copy.deepcopy(self.bad_sim_g148)
        raw_off = self._unpack_clean_raw()[0]
        p1 = _evaluate_pillar_1(raw_off, raw_sim_bad)
        self.assertFalse(p1.passed)
        self.assertFalse(raw_sim_bad["nested_g_valid"]["g147"])
        self.assertFalse(raw_sim_bad["nested_g_valid"]["g148"])

    def test_25_fault_to_148gate_worker_dict_propagates_wave62_to_65_and_m324(self) -> None:
        f = RealHwMilestone349FaultInjection(
            p1_shoe_audio_subject_recog_kwargs={"dormant_bird_subject_requested": True},
            p1_hdmi_raw_desqueeze_kwargs={"desqueeze_1_8x_requested": True},
            p1_breathing_camid_reel_kwargs={"sdhc_exfat_simult_requested": True},
            p1_copyright_powersave_ntscpal_kwargs={"copyright_reset_wipe_claimed": True},
            m324_faults=RealHwMilestone324FaultInjection(p1_request_persistent_writes=True),
        )
        w = _fault_to_148gate_worker_dict(f)
        self.assertTrue(w["p1_request_persistent_writes"])
        self.assertEqual(w["p1_shoe_audio_subject_recog_kwargs"], {"dormant_bird_subject_requested": True})
        self.assertEqual(w["p1_hdmi_raw_desqueeze_kwargs"], {"desqueeze_1_8x_requested": True})
        self.assertEqual(w["p1_breathing_camid_reel_kwargs"], {"sdhc_exfat_simult_requested": True})
        self.assertEqual(w["p1_copyright_powersave_ntscpal_kwargs"], {"copyright_reset_wipe_claimed": True})

    def test_26_worker_148plus_gate_handles_pre_g147_fault_chain_override(self) -> None:
        f = RealHwMilestone349FaultInjection(
            m324_faults=RealHwMilestone324FaultInjection(
                p1_ftp_ftpes_customwb_kwargs={"ftp_avf_db_recover_requested": True},
            )
        )
        w = _fault_to_148gate_worker_dict(f)
        bad_sim = _worker_148plus_gate_single((str(REPO_ROOT), True, True, w, True))
        raw_off = self._unpack_clean_raw()[0]
        self.assertFalse(_evaluate_pillar_1(raw_off, bad_sim).passed)

    # --- 4. Pillar 2: >= 62 Recovery Pillars (`evaluate_realhw_62pillar_recovery_master`) ---

    def test_27_pillar2_62pillar_happy_path_and_cnflasha_ro(self) -> None:
        rec_62 = self._unpack_clean_raw()[2]
        p2, meta2 = _evaluate_pillar_2(rec_62, RealHwMilestone349FaultInjection())
        self.assertTrue(p2.passed, p2.errors)
        self.assertGreaterEqual(meta2["recovery_pillar_count"], 62)
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

    def test_28_pillar2_forward_compatible_with_63_pillars(self) -> None:
        rec_62 = self._unpack_clean_raw()[2]
        rec_62["pillar_count"] = 63
        rec_62["pillars_passed"] = 63
        rec_62["status"] = "VERIFIED_63OF63_PILLAR_RECOVERY_MASTER"
        rec_62["pillars"] = list(rec_62["pillars"]) + [
            {"pillar_id": "pillar_63_future_vault", "passed": True}
        ]
        p2, meta2 = _evaluate_pillar_2(rec_62, RealHwMilestone349FaultInjection())
        self.assertTrue(p2.passed, p2.errors)
        self.assertGreaterEqual(meta2["recovery_pillar_count"], 63)

    def test_29_pillar2_fails_when_cnflasha_userspace_write_unblocked(self) -> None:
        rec_62 = self._unpack_clean_raw()[2]
        p2, _ = _evaluate_pillar_2(
            rec_62,
            RealHwMilestone349FaultInjection(p2_cnflasha_write_unblocked_fault=True),
        )
        self.assertFalse(p2.passed)

    def test_30_pillar2_fails_on_otp_rpmb_passive_tx_usb_devwrite_or_leak_overrides(self) -> None:
        rec_62 = self._unpack_clean_raw()[2]
        for kw in (
            {"p2_otp_fuse_touches_override": 1},
            {"p2_rpmb_counter_increments_override": 1},
            {"p2_passive_tx_bytes_override": 4},
            {"p2_physical_usb_packets_override": 1},
            {"p2_physical_device_writes_override": 1},
            {"p2_raw_firmware_bytes_leaked_override": 8},
        ):
            p2, _ = _evaluate_pillar_2(rec_62, RealHwMilestone349FaultInjection(**kw))
            self.assertFalse(p2.passed, kw)

    def test_31_pillar2_fails_when_62a_or_62b_vault_subsuite_fails_safely(self) -> None:
        for sub_key in (
            "pillar62_a_rec_media_autoswitch_proxy_vault",
            "pillar62_b_cloud_poweroff_ble_mymenu_vault",
        ):
            rec_62 = self._unpack_clean_raw()[2]
            rec_62.setdefault(sub_key, {})["passed"] = False
            self.assertFalse(
                _evaluate_pillar_2(rec_62, RealHwMilestone349FaultInjection())[0].passed,
                sub_key,
            )

    def test_32_pillar2_live_worker_fault_inject_pillar_62_fails_closed(self) -> None:
        bad_62 = copy.deepcopy(self.bad_rec_62)
        p2, _ = _evaluate_pillar_2(bad_62, RealHwMilestone349FaultInjection())
        self.assertFalse(p2.passed)

    def test_33_pillar2_fails_on_p57_to_p62_violation_counters_or_hw_flags(self) -> None:
        for vkey in (
            "access_authen_ssh_tls_or_fan_max_drift_events",
            "big6_home_or_lower_left_nd_drift_events",
            "card_speed_vpg200_vpg400_gate_drift_events",
            "cloud_init_persist_or_power_off_ble_rf_events",
            "dial_customize_dormant_trap_or_reset_drift_events",
            "rec_media_prioritize_or_autoswitch_drift_events",
            "rf_nvs_mutation_bytes",
            "slot1_dcim_m4root_avf_mutation_bytes",
        ):
            rec_62 = self._unpack_clean_raw()[2]
            rec_62[vkey] = 1
            self.assertFalse(
                _evaluate_pillar_2(rec_62, RealHwMilestone349FaultInjection())[0].passed,
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
                _evaluate_pillar_2(rec_neg, RealHwMilestone349FaultInjection())[0].passed,
                neg_flag,
            )

    def test_34_pillar2_passes_with_optional_p62_subkeys_present_and_63_compat(self) -> None:
        rec_62 = self._unpack_clean_raw()[2]
        rec_62["pillar_count"] = 63
        rec_62["pillars_passed"] = 63
        rec_62["status"] = "VERIFIED_63OF63_PILLAR_RECOVERY_MASTER"
        rec_62["pillars"] = list(rec_62["pillars"]) + [{"pillar_id": "pillar_63", "passed": True}]
        rec_62["pillar63_a_extra_vault"] = {"passed": True}
        self.assertTrue(_evaluate_pillar_2(rec_62, RealHwMilestone349FaultInjection())[0].passed)

    # --- 5. Pillar 3: >= 45 Firmware Auditors (`outputs/fx3-firmware-lab`) ---

    def test_35_pillar3_45plus_auditors_happy_path(self) -> None:
        auditors = self._unpack_clean_raw()[3]
        p3, meta3 = _evaluate_pillar_3(auditors, RealHwMilestone349FaultInjection())
        self.assertTrue(p3.passed, p3.errors)
        self.assertGreaterEqual(meta3["auditor_count"], 45)
        self.assertEqual(meta3["passed_count"], meta3["auditor_count"])
        self.assertEqual(meta3["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(meta3["e_nd_actuator_tx_count"], 0)
        self.assertEqual(meta3["calibration_mutation_bytes"], 0)

    def test_36_pillar3_forward_compatible_with_46_plus_auditors(self) -> None:
        auditors = self._unpack_clean_raw()[3]
        auditors["realhw_future_wave72_audit"] = {"all_checks_passed": True}
        p3, meta3 = _evaluate_pillar_3(auditors, RealHwMilestone349FaultInjection())
        self.assertTrue(p3.passed, p3.errors)
        self.assertGreaterEqual(meta3["auditor_count"], 46)
        self.assertEqual(meta3["passed_count"], meta3["auditor_count"])

    def test_37_pillar3_fails_on_auditor45_guard_fault_or_subpillar_failure(self) -> None:
        auditors = self._unpack_clean_raw()[3]
        p3_fault, _ = _evaluate_pillar_3(
            auditors,
            RealHwMilestone349FaultInjection(p3_filesettings_tcregen_reclamp_guard_fault=True),
        )
        self.assertFalse(p3_fault.passed)

        auditors2 = self._unpack_clean_raw()[3]
        auditors2["realhw_filesettings_shotmark_tcregen_and_reclamp_audit"].setdefault(
            "pillar_2_tc_regenerate_slot1_and_ext_lk", {}
        )["passed"] = False
        self.assertFalse(_evaluate_pillar_3(auditors2, RealHwMilestone349FaultInjection())[0].passed)

    def test_38_pillar3_fails_on_raw_firmware_bytes_leaked_override(self) -> None:
        auditors = self._unpack_clean_raw()[3]
        p3, _ = _evaluate_pillar_3(
            auditors,
            RealHwMilestone349FaultInjection(p3_raw_firmware_bytes_leaked_override=16),
        )
        self.assertFalse(p3.passed)

    def test_39_pillar3_fails_when_forward_compat_46th_auditor_fails(self) -> None:
        auditors = self._unpack_clean_raw()[3]
        auditors["realhw_broken_future_audit"] = {"all_checks_passed": False}
        self.assertFalse(_evaluate_pillar_3(auditors, RealHwMilestone349FaultInjection())[0].passed)

    # --- 6. Pillar 4: >= 75 VM HIL Co-Emulation Stages (`outputs/fx3-vm`) ---

    def test_40_pillar4_75plus_stages_happy_path_and_milestone_75of75(self) -> None:
        raw_vm = self._unpack_clean_raw()[4]
        p4, meta4 = _evaluate_pillar_4(raw_vm, RealHwMilestone349FaultInjection())
        self.assertTrue(p4.passed, p4.errors)
        self.assertGreaterEqual(meta4["stage_count"], 75)
        self.assertEqual(meta4["passed_count"], meta4["stage_count"])
        self.assertEqual(meta4["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(meta4["physical_device_writes"], 0)
        self.assertEqual(meta4["emmc_corruptions"], 0)
        self.assertEqual(p4.evidence["stage75_milestone"], "75/75")
        for dkey in (
            "stage67_digest_sha256",
            "stage72_digest_sha256",
            "stage75_digest_sha256",
        ):
            self.assertEqual(len(str(p4.evidence[dkey])), 64, dkey)

    def test_41_pillar4_forward_compatible_with_stage76_plus(self) -> None:
        raw_vm = self._unpack_clean_raw()[4]
        raw_vm["stage76_realhw_future_wave72_hil"] = {
            "all_checks_passed": True,
            "physical_device_writes": 0,
            "raw_firmware_bytes_leaked": 0,
            "cp_mutation_bytes": 0,
            "bk4_persistent_nvram_writes": 0,
            "wf12_00342260_hits": 0,
            "emmc_corruptions": 0,
            "slot1_avf_info_mutated": False,
        }
        p4, meta4 = _evaluate_pillar_4(raw_vm, RealHwMilestone349FaultInjection())
        self.assertTrue(p4.passed, p4.errors)
        self.assertGreaterEqual(meta4["stage_count"], 76)
        self.assertEqual(meta4["passed_count"], meta4["stage_count"])

    def test_42_pillar4_fails_on_stage67_through_stage75_fault_injections(self) -> None:
        raw_vm = self._unpack_clean_raw()[4]
        for kw in (
            {"p4_stage67_steadyshot_47focal_selftimer_zebra_streaming_faults": 1},
            {"p4_stage68_bright_mon_shotmark_usblan_bulb_dormant_faults": 1},
            {"p4_stage69_big6_home_framing_interval_tc_ssh_fan_faults": 1},
            {"p4_stage70_rec_media_autoswitch_proxy_cloud_mymenu_faults": 1},
            {"p4_stage71_ftp_ftpes_usblan_customwb_af_focusmap_marker_faults": 1},
            {"p4_stage72_shoe_audio_4ch_subject_recog_silent_target_version_faults": 1},
            {"p4_stage73_hdmi_raw_desqueeze_reclamp_varshutter_apsc_faults": 1},
            {"p4_stage74_breathing_camid_copyright_powersave_ntsc_pal_faults": 1},
            {"p4_stage75_zoom_ciz_autoslow_iso_arw_rawcomp_usblun_uvc_faults": 1},
        ):
            p4, _ = _evaluate_pillar_4(raw_vm, RealHwMilestone349FaultInjection(**kw))
            self.assertFalse(p4.passed, kw)

    def test_43_pillar4_fails_on_stage63_through_stage66_cascaded_fault_injections(self) -> None:
        raw_vm = self._unpack_clean_raw()[4]
        for m324_kw in (
            {"p4_stage63_lens_comp_af_illum_folder_rating_faults": 1},
            {"p4_stage64_switch_vh_stdadj_tcub_copy_faults": 1},
            {"p4_stage65_touch_disp_zero_evf_interval_pb_faults": 1},
            {"p4_stage66_dial_customize_mydial_fn_lut_embed_faults": 1},
        ):
            f = RealHwMilestone349FaultInjection(
                m324_faults=RealHwMilestone324FaultInjection(**m324_kw)
            )
            p4, _ = _evaluate_pillar_4(raw_vm, f)
            self.assertFalse(p4.passed, m324_kw)

    def test_44_pillar4_fails_on_physical_device_writes_or_raw_leak(self) -> None:
        raw_vm = self._unpack_clean_raw()[4]
        for kw in (
            {"p4_physical_device_writes_override": 1},
            {"p4_raw_firmware_bytes_leaked_override": 4},
        ):
            p4, _ = _evaluate_pillar_4(raw_vm, RealHwMilestone349FaultInjection(**kw))
            self.assertFalse(p4.passed, kw)

    def test_45_pillar4_fails_on_stage67_to_75_milestone_or_digest_tamper(self) -> None:
        raw_vm = self._unpack_clean_raw()[4]
        raw_vm["stage75_realhw_zoom_ciz_autoslow_iso_arw_rawcomp_usblun_uvc_hil"]["milestone"] = "74/75"
        self.assertFalse(_evaluate_pillar_4(raw_vm, RealHwMilestone349FaultInjection())[0].passed)

        raw_vm2 = self._unpack_clean_raw()[4]
        raw_vm2["stage72_realhw_shoe_audio_4ch_subject_recog_silent_target_version_hil"][
            "phase335_audit_digest_sha256"
        ] = "bad"
        self.assertFalse(_evaluate_pillar_4(raw_vm2, RealHwMilestone349FaultInjection())[0].passed)

    def test_46_pillar4_fails_on_stage67_to_75_redline_counters_and_emmc_mutation(self) -> None:
        for skey, bad_counter in (
            ("stage67_realhw_steadyshot_47focal_selftimer_zebra_streaming_hil", "streaming_rec_4k_lock_bypass_events"),
            ("stage68_realhw_bright_mon_shotmark_usblan_bulb_dormant_hil", "slot1_vault_shotmark_edit_mutation_bytes"),
            ("stage69_realhw_big6_home_framing_interval_tc_ssh_fan_hil", "fan_control_max_exposed_events"),
            ("stage70_realhw_rec_media_autoswitch_proxy_cloud_mymenu_hil", "slot2_to_slot1_overflow_bypass_events"),
            ("stage71_realhw_ftp_ftpes_usblan_customwb_af_focusmap_marker_hil", "usblan_zero_rf_bypass_events"),
            ("stage72_realhw_shoe_audio_4ch_subject_recog_silent_target_version_hil", "cross_model_flash_attempt_admitted_events"),
            ("stage73_realhw_hdmi_raw_desqueeze_reclamp_varshutter_apsc_hil", "dormant_var_shutter_exposed_events"),
            ("stage74_realhw_breathing_camid_copyright_powersave_ntsc_pal_hil", "photographer_copyright_pii_leaked_bytes"),
            ("stage75_realhw_zoom_ciz_autoslow_iso_arw_rawcomp_usblun_uvc_hil", "usb_lun_slot1_host_pollution_events"),
            ("stage75_realhw_zoom_ciz_autoslow_iso_arw_rawcomp_usblun_uvc_hil", "emmc_mutation_bytes"),
        ):
            raw_vm = self._unpack_clean_raw()[4]
            raw_vm[skey][bad_counter] = 1
            self.assertFalse(
                _evaluate_pillar_4(raw_vm, RealHwMilestone349FaultInjection())[0].passed,
                f"{skey}:{bad_counter}",
            )

    def test_47_pillar4_fails_when_future_stage76_fails_or_mutates_avf_info(self) -> None:
        raw_vm = self._unpack_clean_raw()[4]
        raw_vm["stage76_broken_hil"] = {"all_checks_passed": False}
        self.assertFalse(_evaluate_pillar_4(raw_vm, RealHwMilestone349FaultInjection())[0].passed)

        raw_vm2 = self._unpack_clean_raw()[4]
        raw_vm2["stage76_realhw_wave72_hil"] = {
            "all_checks_passed": True,
            "slot1_avf_info_mutated": True,
        }
        self.assertFalse(_evaluate_pillar_4(raw_vm2, RealHwMilestone349FaultInjection())[0].passed)

    def test_48_pillar4_fails_on_wf12_hits_in_stage72_to_75(self) -> None:
        raw_vm = self._unpack_clean_raw()[4]
        raw_vm["stage73_realhw_hdmi_raw_desqueeze_reclamp_varshutter_apsc_hil"]["wf12_00342260_hits"] = 1
        p4, meta4 = _evaluate_pillar_4(raw_vm, RealHwMilestone349FaultInjection())
        self.assertEqual(meta4["wf12_00342260_hits"], 1)
        self.assertFalse(p4.passed)  # stage73 redlines + P6 cross-pillar check both catch wf12
        m1 = _evaluate_pillar_1(self.raw_bundle[0], self.raw_bundle[1]).evidence
        _, m2 = _evaluate_pillar_2(self.raw_bundle[2], RealHwMilestone349FaultInjection())
        _, m3 = _evaluate_pillar_3(self.raw_bundle[3], RealHwMilestone349FaultInjection())
        _, m5 = _evaluate_pillar_5(*self._unpack_clean_raw()[5:48], RealHwMilestone349FaultInjection())
        p6, _ = _evaluate_pillar_6(
            repo_root=REPO_ROOT,
            use_clean_room=True,
            faults=RealHwMilestone349FaultInjection(),
            p1_meta=m1,
            p2_meta=m2,
            p3_meta=m3,
            p4_meta=meta4,
            p5_meta=m5,
        )
        self.assertFalse(p6.passed)

    def test_49_pillar4_fails_if_passed_stage_count_below_75(self) -> None:
        raw_vm = self._unpack_clean_raw()[4]
        raw_vm["stage75_realhw_zoom_ciz_autoslow_iso_arw_rawcomp_usblun_uvc_hil"]["all_checks_passed"] = False
        self.assertFalse(_evaluate_pillar_4(raw_vm, RealHwMilestone349FaultInjection())[0].passed)

    # --- 7. Pillar 5: ALL 20 Bench Readiness Verifiers (`Ph186`..`Ph345`) ---

    def test_50_pillar5_icosuple_20of20_bench_preflights_happy_path(self) -> None:
        b = self._unpack_clean_raw()
        p5, meta5 = _evaluate_pillar_5(*b[5:48], RealHwMilestone349FaultInjection())
        self.assertTrue(p5.passed, p5.errors)
        self.assertEqual(meta5["bench_preflight_verifier_count"], 20)
        self.assertFalse(meta5["overall_ready_for_hardware_attach"])
        all_20 = (
            "p186", "p204", "p216", "p227", "p248", "p261",
            "p275", "p279", "p284", "p291", "p302", "p307",
            "p316", "p321", "p329", "p334", "p338", "p341",
            "p342", "p345",
        )
        for tag in all_20:
            off_k = f"{tag}_offline_go_no_go"
            sim_k = f"{tag}_sim_go_no_go"
            self.assertEqual(meta5[off_k], GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT, off_k)
            self.assertEqual(meta5[sim_k], GO_NO_GO_DRY_RUN_SIMULATED_READY, sim_k)
            self.assertEqual(meta5[f"{tag}_h0_equals_h3_count"], 16, tag)
        self.assertFalse(meta5["p186_card_insert_authorized"])
        for tag in all_20[1:]:
            self.assertFalse(meta5[f"{tag}_hardware_live_attachment_authorized"], tag)
        for tag in ("p316", "p321", "p329", "p334", "p338", "p341", "p342", "p345"):
            self.assertEqual(meta5[f"{tag}_sim_check_groups_passed"], 4, tag)
            self.assertEqual(meta5[f"{tag}_sim_usb_packets_transmitted"], 0, tag)
            self.assertEqual(meta5[f"{tag}_sim_passive_tx_bytes_emitted"], 0, tag)
            self.assertEqual(meta5[f"{tag}_wireless_rf_packets_emitted"], 0, tag)
            self.assertEqual(meta5[f"{tag}_rf_packets_transmitted"], 0, tag)
            self.assertEqual(meta5[f"{tag}_e_nd_actuator_tx_count"], 0, tag)
            self.assertEqual(meta5[f"{tag}_slot1_data_sector_writes"], 0, tag)

    def test_51_pillar5_rejects_phase329_shoe_audio_subject_hdmi_raw_faults(self) -> None:
        b = list(self._unpack_clean_raw())
        p329_off, p329_sim, _, _ = copy.deepcopy(self.p329_334_bad)
        p5, _ = _evaluate_pillar_5(
            *b[5:36], p329_off, p329_sim, *b[38:48], RealHwMilestone349FaultInjection()
        )
        self.assertFalse(p5.passed)

    def test_52_pillar5_rejects_phase334_breathing_camid_usblun_faults(self) -> None:
        b = list(self._unpack_clean_raw())
        _, _, p334_off, p334_sim = copy.deepcopy(self.p329_334_bad)
        p5, _ = _evaluate_pillar_5(
            *b[5:38], p334_off, p334_sim, *b[40:48], RealHwMilestone349FaultInjection()
        )
        self.assertFalse(p5.passed)

    def test_53_pillar5_rejects_phase338_drive_creativelook_pixelmap_hdmi_faults(self) -> None:
        b = list(self._unpack_clean_raw())
        p338_off, p338_sim, _, _ = copy.deepcopy(self.p338_341_bad)
        p5, _ = _evaluate_pillar_5(
            *b[5:40], p338_off, p338_sim, *b[42:48], RealHwMilestone349FaultInjection()
        )
        self.assertFalse(p5.passed)

    def test_54_pillar5_rejects_phase341_area_date_camset_wifi_cec_faults(self) -> None:
        b = list(self._unpack_clean_raw())
        _, _, p341_off, p341_sim = copy.deepcopy(self.p338_341_bad)
        p5, _ = _evaluate_pillar_5(
            *b[5:42], p341_off, p341_sim, *b[44:48], RealHwMilestone349FaultInjection()
        )
        self.assertFalse(p5.passed)

    def test_55_pillar5_rejects_phase342_peaking_usbpd_antidust_usbtether_faults(self) -> None:
        b = list(self._unpack_clean_raw())
        p342_off, p342_sim, _, _ = copy.deepcopy(self.p342_345_bad)
        p5, _ = _evaluate_pillar_5(
            *b[5:44], p342_off, p342_sim, *b[46:48], RealHwMilestone349FaultInjection()
        )
        self.assertFalse(p5.passed)

    def test_56_pillar5_rejects_phase345_audio_4ch_touch_remoteshoot_faults(self) -> None:
        b = list(self._unpack_clean_raw())
        _, _, p345_off, p345_sim = copy.deepcopy(self.p342_345_bad)
        p5, _ = _evaluate_pillar_5(
            *b[5:46], p345_off, p345_sim, RealHwMilestone349FaultInjection()
        )
        self.assertFalse(p5.passed)

    def test_57_pillar5_rejects_h0_h3_drift_across_p329_to_p345(self) -> None:
        b = list(self._unpack_clean_raw())
        d329_o, d329_s, d334_o, d334_s = copy.deepcopy(self.p329_334_drift)
        d338_o, d338_s, d341_o, d341_s = copy.deepcopy(self.p338_341_drift)
        d342_o, d342_s, d345_o, d345_s = copy.deepcopy(self.p342_345_drift)
        for sl_idx, (ro, rs) in (
            (36, (d329_o, d329_s)),
            (38, (d334_o, d334_s)),
            (40, (d338_o, d338_s)),
            (42, (d341_o, d341_s)),
            (44, (d342_o, d342_s)),
            (46, (d345_o, d345_s)),
        ):
            mod_b = list(b)
            mod_b[sl_idx] = ro
            mod_b[sl_idx + 1] = rs
            p5, _ = _evaluate_pillar_5(*mod_b[5:48], RealHwMilestone349FaultInjection())
            self.assertFalse(p5.passed, sl_idx)

    def test_58_pillar5_rejects_p329_to_p345_usb_passive_and_wireless_rf_overrides(self) -> None:
        b = self._unpack_clean_raw()
        for tag in ("p329", "p334", "p338", "p341", "p342", "p345"):
            for fkw in (
                {f"p5_inject_{tag}_usb_packets_override": 1},
                {f"p5_inject_{tag}_passive_tx_bytes_override": 4},
                {f"p5_inject_{tag}_wireless_rf_packets_override": 1},
            ):
                p5, _ = _evaluate_pillar_5(*b[5:48], RealHwMilestone349FaultInjection(**fkw))
                self.assertFalse(p5.passed, fkw)

    def test_59_pillar5_rejects_p329_to_p345_rf_nvs_auth_or_slot1_tier0_mutated(self) -> None:
        # indices inside p5_slice (b[5:48]): p329_sim=32, p334_sim=34, p338_sim=36, p341_sim=38, p342_sim=40, p345_sim=42
        for sim_idx in (32, 34, 36, 38, 40, 42):
            for bad_k, bad_v in (
                ("rf_nvs_p12_p13_writes_authorized", True),
                ("slot1_tier0_vault_mutated", True),
                ("slot1_data_sector_writes", 1),
                ("e_nd_actuator_tx_count", 1),
            ):
                p5_slice = list(self._unpack_clean_raw()[5:48])
                p5_slice[sim_idx][bad_k] = bad_v
                p5, _ = _evaluate_pillar_5(*p5_slice, RealHwMilestone349FaultInjection())
                self.assertFalse(p5.passed, f"idx={sim_idx}:{bad_k}")

    def test_60_pillar5_rejects_offline_if_not_blocked_awaiting_tier0(self) -> None:
        for off_idx in (31, 33, 35, 37, 39, 41):
            p5_slice = list(self._unpack_clean_raw()[5:48])
            p5_slice[off_idx]["go_no_go"] = GO_NO_GO_DRY_RUN_SIMULATED_READY
            p5, _ = _evaluate_pillar_5(*p5_slice, RealHwMilestone349FaultInjection())
            self.assertFalse(p5.passed, off_idx)

    def test_61_pillar5_rejects_sim_sha256_tamper_and_attach_ready_true(self) -> None:
        for sim_idx in (32, 34, 36, 38, 40, 42):
            p5_slice = list(self._unpack_clean_raw()[5:48])
            p5_slice[sim_idx]["report_sha256"] = "0" * 64
            p5, _ = _evaluate_pillar_5(*p5_slice, RealHwMilestone349FaultInjection())
            self.assertFalse(p5.passed, sim_idx)

            p5_slice2 = list(self._unpack_clean_raw()[5:48])
            p5_slice2[sim_idx]["overall_ready_for_hardware_attach"] = True
            p5_2, _ = _evaluate_pillar_5(*p5_slice2, RealHwMilestone349FaultInjection())
            self.assertFalse(p5_2.passed, sim_idx)

    def test_62_pillar5_rejects_p329_to_p345_check_groups_count_mismatch(self) -> None:
        for sim_idx in (32, 34, 36, 38, 40, 42):
            p5_slice = list(self._unpack_clean_raw()[5:48])
            p5_slice[sim_idx]["check_groups_passed"] = 3
            p5, _ = _evaluate_pillar_5(*p5_slice, RealHwMilestone349FaultInjection())
            self.assertFalse(p5.passed, sim_idx)

    def test_63_pillar5_propagates_upstream_phase321_failure(self) -> None:
        b = list(self._unpack_clean_raw())
        _, _, p321_off, p321_sim = copy.deepcopy(self.p316_321_bad)
        p5, _ = _evaluate_pillar_5(
            *b[5:34], p321_off, p321_sim, *b[36:48], RealHwMilestone349FaultInjection()
        )
        self.assertFalse(p5.passed)

    def test_64_pillar5_enforces_20_of_20_bench_preflight_count(self) -> None:
        b = self._unpack_clean_raw()
        p5, meta5 = _evaluate_pillar_5(*b[5:48], RealHwMilestone349FaultInjection())
        self.assertEqual(p5.evidence["bench_preflight_verifier_count"], 20)
        self.assertEqual(meta5["bench_preflight_verifier_count"], 20)

    # --- 8. Pillar 6: Live FX3 7.02 QEMU Rounds 28..72+ & < 50 KiB PNG Receipts ---

    def _clean_p1_to_p5_metas(self):
        cls = type(self)
        cached = getattr(cls, "_cached_p1_to_p5_metas", None)
        if cached is None:
            b = self.raw_bundle
            f = RealHwMilestone349FaultInjection()
            p1 = _evaluate_pillar_1(b[0], b[1])
            _, m2 = _evaluate_pillar_2(b[2], f)
            _, m3 = _evaluate_pillar_3(b[3], f)
            _, m4 = _evaluate_pillar_4(b[4], f)
            _, m5 = _evaluate_pillar_5(*b[5:48], f)
            cached = (p1.evidence, m2, m3, m4, m5)
            cls._cached_p1_to_p5_metas = cached
        return cached

    def test_65_pillar6_rounds_28_to_72_at_least_45_rounds_135_runs_90_pngs(self) -> None:
        m1, m2, m3, m4, m5 = self._clean_p1_to_p5_metas()
        p6, meta6 = _evaluate_pillar_6(
            repo_root=REPO_ROOT,
            use_clean_room=True,
            faults=RealHwMilestone349FaultInjection(),
            p1_meta=m1,
            p2_meta=m2,
            p3_meta=m3,
            p4_meta=m4,
            p5_meta=m5,
        )
        self.assertTrue(p6.passed, p6.errors)
        self.assertGreaterEqual(meta6["qemu_rounds_verified"], 45)
        self.assertGreaterEqual(meta6["qemu_runs_verified"], 135)
        self.assertGreaterEqual(meta6["qemu_png_receipts_verified"], 90)
        self.assertLess(meta6["qemu_png_max_bytes"], PNG_MAX_SIZE_50KIB_BYTES)
        self.assertEqual(meta6["qemu_raw_firmware_bytes_leaked"], 0)
        self.assertEqual(meta6["qemu_real_kernel_nop_count"], 0)
        self.assertEqual(meta6["qemu_real_kernel_crashes"], 0)
        self.assertEqual(meta6["qemu_real_kernel_emmc_writes"], 0)
        for rnum in range(66, 73):
            self.assertEqual(meta6["qemu_round_runs_by_round"][f"r{rnum}"], 3)

    def test_66_pillar6_committed_rounds66_to_72_png_headers_and_baseline_max_27467b(self) -> None:
        observed_max = 0
        for rnum in range(28, 73):
            for rel in ROUND28_TO_72_PNG_RECEIPTS[rnum]:
                p = REPO_ROOT / rel
                if p.is_file():
                    raw = p.read_bytes()
                    self.assertTrue(raw.startswith(PNG_MAGIC_BYTES), rel)
                    self.assertLess(len(raw), PNG_MAX_SIZE_50KIB_BYTES, rel)
                    if len(raw) > observed_max:
                        observed_max = len(raw)
        if observed_max > 0:
            self.assertLessEqual(observed_max, P349_BASELINE_PNG_MAX_OBSERVED_BYTES)

    def test_67_pillar6_forward_compatible_with_round73_directory_discovery(self) -> None:
        m1, m2, m3, m4, m5 = self._clean_p1_to_p5_metas()
        with tempfile.TemporaryDirectory() as tmp:
            tmp_root = Path(tmp)
            r73_dir = tmp_root / "reports" / "2026-11-18-round73-realhw-wave59-qemu"
            assets_dir = r73_dir / "assets"
            assets_dir.mkdir(parents=True, exist_ok=True)
            for name in ("r73a-alpha.png", "r73a-composited.png"):
                (assets_dir / name).write_bytes(PNG_MAGIC_BYTES + b"\x00" * 128)
            summary = {
                "schema": "fx6-on-fx3-round73-realhw-wave59-qemu-v1",
                "round": 73,
                "kernel_version": "Linux version 4.9.337-scel+ (clean-room-synthetic)",
                "raw_firmware_bytes_leaked": 0,
                "runs": {
                    "r73a_run": {"nop_count": 0, "crashes": 0, "emmc_write_count": 0, "stage_b": {"manifest_count": 13}},
                    "r73b_run": {"nop_count": 0, "crashes": 0, "emmc_write_count": 0, "stage_b": {"manifest_count": 13}},
                    "r73c_run": {"nop_count": 0, "crashes": 0, "emmc_write_count": 0, "stage_b": {"manifest_count": 13}},
                },
                "r73_realhw_wave59_audit": {
                    "all_3_runs_crashes_zero": True,
                    "all_3_runs_emmc_write_zero": True,
                    "fx3_has_builtin_evf": False,
                    "fx3_has_var_shutter": False,
                },
            }
            (r73_dir / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
            p6, meta6 = _evaluate_pillar_6(
                repo_root=tmp_root,
                use_clean_room=True,
                faults=RealHwMilestone349FaultInjection(),
                p1_meta=m1,
                p2_meta=m2,
                p3_meta=m3,
                p4_meta=m4,
                p5_meta=m5,
            )
            self.assertTrue(p6.passed, p6.errors)
            self.assertGreaterEqual(meta6["qemu_rounds_verified"], 46)
            self.assertGreaterEqual(meta6["qemu_runs_verified"], 138)
            self.assertGreaterEqual(meta6["qemu_png_receipts_verified"], 92)

    def test_68_pillar6_forward_compatible_round73_rejects_bad_audit_flag_or_kernel(self) -> None:
        m1, m2, m3, m4, m5 = self._clean_p1_to_p5_metas()
        with tempfile.TemporaryDirectory() as tmp:
            tmp_root = Path(tmp)
            r73_dir = tmp_root / "reports" / "2026-11-18-round73-realhw-broken-qemu"
            r73_dir.mkdir(parents=True, exist_ok=True)
            summary = {
                "schema": "fx6-on-fx3-round73-broken-v1",
                "round": 73,
                "kernel_version": "Linux version 4.9.337-scel+ (clean-room-synthetic)",
                "raw_firmware_bytes_leaked": 0,
                "runs": {
                    "r73a_run": {"nop_count": 0, "crashes": 0, "emmc_write_count": 0, "stage_b": {"manifest_count": 13}},
                },
                "r73_broken_audit": {
                    "all_3_runs_crashes_zero": True,
                    "fx3_has_builtin_evf": True,
                },
            }
            (r73_dir / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
            p6, _ = _evaluate_pillar_6(
                repo_root=tmp_root,
                use_clean_room=True,
                faults=RealHwMilestone349FaultInjection(),
                p1_meta=m1,
                p2_meta=m2,
                p3_meta=m3,
                p4_meta=m4,
                p5_meta=m5,
            )
            self.assertFalse(p6.passed)

    def test_69_pillar6_fails_on_rounds66_to_72_schema_tamper(self) -> None:
        m1, m2, m3, m4, m5 = self._clean_p1_to_p5_metas()
        for rnum in range(66, 73):
            p6, _ = _evaluate_pillar_6(
                repo_root=REPO_ROOT,
                use_clean_room=True,
                faults=RealHwMilestone349FaultInjection(p6_tamper_schema_round_num=rnum),
                p1_meta=m1,
                p2_meta=m2,
                p3_meta=m3,
                p4_meta=m4,
                p5_meta=m5,
            )
            self.assertFalse(p6.passed, rnum)

    def test_70_pillar6_fails_on_round72_nop_crash_emmc_write_or_raw_leak(self) -> None:
        m1, m2, m3, m4, m5 = self._clean_p1_to_p5_metas()
        for fkw in (
            {"p6_round_nop_override_num": 72, "p6_round_nop_count_override": 1},
            {"p6_round_crash_override_num": 72, "p6_round_crashes_override": 1},
            {"p6_round_emmc_override_num": 72, "p6_round_emmc_writes_override": 1},
            {"p6_raw_firmware_bytes_leaked_override": 8},
        ):
            p6, _ = _evaluate_pillar_6(
                repo_root=REPO_ROOT,
                use_clean_room=True,
                faults=RealHwMilestone349FaultInjection(**fkw),
                p1_meta=m1,
                p2_meta=m2,
                p3_meta=m3,
                p4_meta=m4,
                p5_meta=m5,
            )
            self.assertFalse(p6.passed, fkw)

    def test_71_pillar6_fails_when_png_receipt_reaches_or_exceeds_50kib_ceiling(self) -> None:
        m1, m2, m3, m4, m5 = self._clean_p1_to_p5_metas()
        p6, _ = _evaluate_pillar_6(
            repo_root=REPO_ROOT,
            use_clean_room=True,
            faults=RealHwMilestone349FaultInjection(
                p6_png_size_override_round_num=72,
                p6_png_size_override_bytes=PNG_MAX_SIZE_50KIB_BYTES,
            ),
            p1_meta=m1,
            p2_meta=m2,
            p3_meta=m3,
            p4_meta=m4,
            p5_meta=m5,
        )
        self.assertFalse(p6.passed)

    def test_72_pillar6_cross_pillar_p1_cross_model_and_p2_cnflasha_invariants_fail(self) -> None:
        m1, m2, m3, m4, m5 = self._clean_p1_to_p5_metas()
        m1_bad = dict(m1)
        m1_bad["cross_model_flash_authorized"] = True
        self.assertFalse(
            _evaluate_pillar_6(
                repo_root=REPO_ROOT,
                use_clean_room=True,
                faults=RealHwMilestone349FaultInjection(),
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
                faults=RealHwMilestone349FaultInjection(),
                p1_meta=m1,
                p2_meta=m2_bad,
                p3_meta=m3,
                p4_meta=m4,
                p5_meta=m5,
            )[0].passed
        )

    def test_73_pillar6_cross_pillar_p3_and_p4_mutation_invariants_fail(self) -> None:
        m1, m2, m3, m4, m5 = self._clean_p1_to_p5_metas()
        m3_bad = dict(m3)
        m3_bad["calibration_mutation_bytes"] = 4
        self.assertFalse(
            _evaluate_pillar_6(
                repo_root=REPO_ROOT,
                use_clean_room=True,
                faults=RealHwMilestone349FaultInjection(),
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
                faults=RealHwMilestone349FaultInjection(),
                p1_meta=m1,
                p2_meta=m2,
                p3_meta=m3,
                p4_meta=m4_bad,
                p5_meta=m5,
            )[0].passed
        )

    def test_74_pillar6_cross_pillar_p329_to_p345_h0_h3_rf_end_slot1_fail_closed(self) -> None:
        m1, m2, m3, m4, m5 = self._clean_p1_to_p5_metas()
        for tag in ("p329", "p334", "p338", "p341", "p342", "p345"):
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
                    faults=RealHwMilestone349FaultInjection(),
                    p1_meta=m1,
                    p2_meta=m2,
                    p3_meta=m3,
                    p4_meta=m4,
                    p5_meta=m5_bad,
                )
                self.assertFalse(p6_bad.passed, bad_k)

    def test_75_pillar6_fails_if_bench_preflight_verifier_count_not_20(self) -> None:
        m1, m2, m3, m4, m5 = self._clean_p1_to_p5_metas()
        m5_bad = dict(m5)
        m5_bad["bench_preflight_verifier_count"] = 19
        p6_bad, _ = _evaluate_pillar_6(
            repo_root=REPO_ROOT,
            use_clean_room=True,
            faults=RealHwMilestone349FaultInjection(),
            p1_meta=m1,
            p2_meta=m2,
            p3_meta=m3,
            p4_meta=m4,
            p5_meta=m5_bad,
        )
        self.assertFalse(p6_bad.passed)

    def test_76_pillar6_records_historical_milestone_schema_anchors(self) -> None:
        p6_ev = self.rep_clean.pillars[5].evidence
        for m_num in (175, 193, 209, 221, 233, 254, 264, 295, 311, 324):
            key = f"milestone{m_num}_schema_anchor"
            self.assertEqual(p6_ev[key], f"realhw_milestone{m_num}_master_gate_v1", key)

    # --- 9. Fail-Closed Verifier, CLI, 4-Mode & Donorless CI ---

    def test_77_verifier_rejects_non_mapping_payload(self) -> None:
        self.assertFalse(verify_realhw_milestone349_master_gate("not-a-dict").valid)
        self.assertFalse(verify_realhw_milestone349_master_gate(123).valid)
        self.assertFalse(verify_realhw_milestone349_master_gate(None).valid)  # type: ignore[arg-type]

    def test_78_verifier_rejects_sha256_tamper_and_schema_tamper(self) -> None:
        d = self.rep_clean.to_dict()
        d["milestone349_sha256"] = "f" * 64
        self.assertFalse(verify_realhw_milestone349_master_gate(d).valid)

        d2 = self.rep_clean.to_dict()
        d2["schema"] = "wrong_schema_v1"
        d2["milestone349_sha256"] = compute_milestone349_sha256(d2)
        self.assertFalse(verify_realhw_milestone349_master_gate(d2).valid)

    def test_79_verifier_rejects_redline_tamper_even_when_rehashed(self) -> None:
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
        for tag in ("p316", "p321", "p329", "p334", "p338", "p341", "p342", "p345"):
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
            d["milestone349_sha256"] = compute_milestone349_sha256(d)
            self.assertFalse(verify_realhw_milestone349_master_gate(d).valid, k)

    def test_80_verifier_accepts_forward_compatible_higher_counts(self) -> None:
        d = self.rep_clean.to_dict()
        d["gate148_total_gates"] = 150
        d["gate148_offline_verified"] = 147
        d["gate148_simulated_verified"] = 150
        d["recovery_pillar_count"] = 63
        d["recovery_pillars_passed"] = 63
        d["auditors_total"] = 46
        d["auditors_passed"] = 46
        d["vm_stages_total"] = 76
        d["vm_stages_passed"] = 76
        d["qemu_rounds_total"] = 46
        d["qemu_rounds_verified"] = 46
        d["qemu_runs_total"] = 138
        d["qemu_runs_verified"] = 138
        d["qemu_png_receipts_total"] = 92
        d["qemu_png_receipts_verified"] = 92
        d["milestone349_sha256"] = compute_milestone349_sha256(d)
        v = verify_realhw_milestone349_master_gate(d)
        self.assertTrue(v.valid, v.errors)

    def test_81_verifier_rejects_sub_threshold_counts_and_raw_bytes(self) -> None:
        for k, v in (
            ("gate148_simulated_verified", 147),
            ("recovery_pillar_count", 61),
            ("auditors_passed", 44),
            ("vm_stages_passed", 74),
            ("bench_preflight_verifier_count", 19),
            ("p329_sim_check_groups_passed", 3),
            ("p345_sim_check_groups_passed", 3),
            ("qemu_rounds_verified", 44),
            ("qemu_runs_verified", 134),
            ("qemu_png_receipts_verified", 89),
            ("qemu_png_max_bytes", PNG_MAX_SIZE_50KIB_BYTES),
        ):
            d = self.rep_clean.to_dict()
            d[k] = v
            d["milestone349_sha256"] = compute_milestone349_sha256(d)
            self.assertFalse(verify_realhw_milestone349_master_gate(d).valid, k)

        d_raw = self.rep_clean.to_dict()
        d_raw["pillars"][0]["summary"] = "leaked b'\\x7fELF'"
        d_raw["milestone349_sha256"] = compute_milestone349_sha256(d_raw)
        self.assertFalse(verify_realhw_milestone349_master_gate(d_raw).valid)

    def test_82_verifier_rejects_h0_h3_drift_when_rehashed(self) -> None:
        for k, v in (
            ("p143_h0_equals_h3_count", 15),
            ("p154_bench_go", False),
            ("p329_h0_equals_h3_count", 15),
            ("p334_h0_equals_h3_count", 15),
            ("p338_h0_equals_h3_count", 15),
            ("p341_h0_equals_h3_count", 15),
            ("p342_h0_equals_h3_count", 15),
            ("p345_h0_equals_h3_count", 15),
            ("h0_equals_h3_count", 15),
        ):
            d = self.rep_clean.to_dict()
            d[k] = v
            d["milestone349_sha256"] = compute_milestone349_sha256(d)
            self.assertFalse(verify_realhw_milestone349_master_gate(d).valid, k)

    def test_83_cli_verify_milestone_349_summary_and_out_alias_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            out_json = tmp_path / "m349.json"
            out_md = tmp_path / "m349.md"
            buf = io.StringIO()
            with (
                mock.patch(
                    "fx6_closure.realhw_milestone349_master_gate.evaluate_realhw_milestone349_master_gate",
                    return_value=self.rep_clean,
                ),
                mock.patch("sys.stdout", buf),
            ):
                rc = fx6_cli_main(
                    [
                        "verify-milestone-349",
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
            self.assertIn("schema=realhw_milestone349_master_gate_v1", text)
            self.assertIn("cnflasha_ro=True", text)
            self.assertIn("cross_model_flash_auth=False", text)
            self.assertIn("preflights=20/20", text)
            self.assertIn("p329=DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH", text)
            self.assertIn("p345=DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH", text)
            self.assertIn("rf_pkts=0", text)
            self.assertIn("slot1_writes=0", text)
            self.assertIn("ready_attach=False", text)
            self.assertIsNotNone(re.search(r"gate148=(\d+)/(\d+)", text))
            self.assertIsNotNone(re.search(r"qemu=(\d+)/(\d+)\((\d+)/(\d+)\)", text))
            self.assertTrue(out_json.is_file())
            self.assertTrue(out_md.is_file())
            self.assertTrue(
                verify_realhw_milestone349_master_gate(json.loads(out_json.read_text())).valid
            )

    def test_84_cli_verify_milestone_349_json_stdout_and_failure_exit_code(self) -> None:
        buf = io.StringIO()
        with (
            mock.patch(
                "fx6_closure.realhw_milestone349_master_gate.evaluate_realhw_milestone349_master_gate",
                return_value=self.rep_clean,
            ),
            mock.patch("sys.stdout", buf),
        ):
            rc = fx6_cli_main(["verify-milestone-349", "--clean-room", "--json"])
        self.assertEqual(rc, 0)
        parsed = json.loads(buf.getvalue())
        self.assertEqual(parsed["schema"], REALHW_MILESTONE349_SCHEMA)
        self.assertEqual(parsed["usb_packets_transmitted"], 0)
        self.assertEqual(parsed["bench_preflight_verifier_count"], 20)
        self.assertFalse(parsed["overall_ready_for_hardware_attach"])
        self.assertFalse(parsed["cross_model_flash_authorized"])

        bad_rep = replace(
            self.rep_clean,
            all_pillars_milestone_ready=False,
            status=STATUS_FAIL_CLOSED,
            passed_pillar_count=5,
            failed_pillar_ids=("P1",),
            milestone349_sha256="0" * 64,
        )
        buf2 = io.StringIO()
        with (
            mock.patch(
                "fx6_closure.realhw_milestone349_master_gate.evaluate_realhw_milestone349_master_gate",
                return_value=bad_rep,
            ),
            mock.patch("sys.stdout", buf2),
        ):
            rc2 = fx6_cli_main(["verify-milestone-349", "--force-clean-room"])
        self.assertEqual(rc2, 1)
        self.assertIn("status=FAILED", buf2.getvalue())

    def test_85_cli_verify_milestone_349_simulate_bench_dry_run_flag(self) -> None:
        captured: dict = {}

        def _fake_eval(**kwargs):
            captured.update(kwargs)
            return self.rep_clean

        buf = io.StringIO()
        with (
            mock.patch(
                "fx6_closure.realhw_milestone349_master_gate.evaluate_realhw_milestone349_master_gate",
                side_effect=_fake_eval,
            ),
            mock.patch("sys.stdout", buf),
        ):
            rc = fx6_cli_main(
                ["verify-milestone-349", "--force-clean-room", "--simulate-bench-dry-run", "--json"]
            )
        self.assertEqual(rc, 0)
        self.assertTrue(captured.get("simulate_bench_dry_run"))
        self.assertTrue(captured.get("force_clean_room"))

    def test_86_verify_milestone_349_cli_direct_helper_entrypoint(self) -> None:
        buf = io.StringIO()
        with (
            mock.patch(
                "fx6_closure.realhw_milestone349_master_gate.evaluate_realhw_milestone349_master_gate",
                return_value=self.rep_clean,
            ),
            mock.patch("sys.stdout", buf),
        ):
            rc = verify_milestone_349_cli(["--clean-room", "--simulate-bench-dry-run", "--json"])
        self.assertEqual(rc, 0)
        parsed = json.loads(buf.getvalue())
        self.assertEqual(parsed["schema"], REALHW_MILESTONE349_SCHEMA)
        self.assertTrue(parsed["cnflasha_userspace_write_blocked"])

    def test_87_argparse_help_formatting_safe_for_python_314_and_macos(self) -> None:
        buf_top = io.StringIO()
        with mock.patch("sys.stdout", buf_top):
            with self.assertRaises(SystemExit) as ctx_top:
                fx6_cli_main(["--help"])
        self.assertEqual(ctx_top.exception.code, 0)
        self.assertIn("verify-milestone-349", buf_top.getvalue())

        buf_sub = io.StringIO()
        with mock.patch("sys.stdout", buf_sub):
            with self.assertRaises(SystemExit) as ctx_sub:
                fx6_cli_main(["verify-milestone-349", "--help"])
        self.assertEqual(ctx_sub.exception.code, 0)
        self.assertIn("--force-clean-room", buf_sub.getvalue())
        self.assertIn("--simulate-bench-dry-run", buf_sub.getvalue())
        self.assertNotIn("%(", buf_sub.getvalue())

    def test_88_subprocess_cli_clean_room_via_fx3_fx6_force_clean_room(self) -> None:
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
                "verify-milestone-349",
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
        self.assertEqual(payload["schema"], REALHW_MILESTONE349_SCHEMA)
        self.assertTrue(payload["all_pillars_milestone_ready"])
        self.assertGreaterEqual(payload["gate148_simulated_verified"], 148)
        self.assertGreaterEqual(payload["recovery_pillars_passed"], 62)
        self.assertGreaterEqual(payload["auditors_passed"], 45)
        self.assertGreaterEqual(payload["vm_stages_passed"], 75)
        self.assertEqual(payload["bench_preflight_verifier_count"], 20)
        self.assertGreaterEqual(payload["qemu_rounds_verified"], 45)
        self.assertGreaterEqual(payload["qemu_runs_verified"], 135)
        self.assertGreaterEqual(payload["qemu_png_receipts_verified"], 90)
        self.assertLess(elapsed, _ci_time_budget(30.0))

    def test_89_subprocess_cli_clean_room_via_fx3_clean_room_test_env(self) -> None:
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
                "verify-milestone-349",
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
        self.assertEqual(payload["schema"], REALHW_MILESTONE349_SCHEMA)
        self.assertTrue(payload["all_pillars_milestone_ready"])
        self.assertGreaterEqual(payload["gate148_simulated_verified"], 148)
        self.assertGreaterEqual(payload["recovery_pillars_passed"], 62)
        self.assertEqual(payload["bench_preflight_verifier_count"], 20)
        self.assertLess(elapsed, _ci_time_budget(30.0))

    def test_90_synthetic_clean_room_kwarg_alias_and_suite_runtime_budget(self) -> None:
        rep = evaluate_milestone_349_master_gate(
            synthetic_clean_room=True,
            _raw_bundle_override=self._unpack_clean_raw(),
        )
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(rep.all_pillars_milestone_ready)
        self.assertLess(self.default_elapsed_s, _ci_time_budget(30.0))

    def test_91_donorless_linux_ci_repo_without_mac_work_auto_clean_room(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            troot = Path(tmp)
            for item in REPO_ROOT.iterdir():
                if item.name != "Mac":
                    (troot / item.name).symlink_to(item.resolve())
            rep = evaluate_realhw_milestone349_master_gate(
                repo_root=troot,
                fx6_lib_dir=troot / "nonexistent_fx6",
                fx3_modules_dir=troot / "nonexistent_fx3",
                work_root=None,
                force_clean_room=None,
            )
            self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertTrue(rep.all_pillars_milestone_ready, rep.errors)
            self.assertEqual(rep.passed_pillar_count, 6)
            self.assertTrue(verify_realhw_milestone349_master_gate(rep).valid)

    def test_92_preserves_milestone_324_and_earlier_and_readme_section_63(self) -> None:
        self.assertTrue(hasattr(fx6_closure, "evaluate_realhw_milestone324_master_gate"))
        self.assertTrue(hasattr(fx6_closure, "evaluate_realhw_milestone311_master_gate"))
        self.assertTrue(hasattr(fx6_closure, "evaluate_realhw_milestone295_master_gate"))
        self.assertTrue(hasattr(fx6_closure, "evaluate_realhw_milestone264_master_gate"))
        self.assertTrue(hasattr(fx6_closure, "evaluate_realhw_milestone254_master_gate"))
        self.assertNotEqual(fx6_closure.REALHW_MILESTONE324_SCHEMA, fx6_closure.REALHW_MILESTONE349_SCHEMA)
        self.assertEqual(
            fx6_closure.evaluate_realhw_milestone349_master_gate,
            evaluate_realhw_milestone349_master_gate,
        )
        readme_text = (REPO_ROOT / "outputs" / "fx6-on-fx3-closure" / "README.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("# 63.", readme_text)
        self.assertIn("verify-milestone-349", readme_text)
        self.assertIn("realhw_milestone349_master_gate_v1", readme_text)


if __name__ == "__main__":
    unittest.main()
