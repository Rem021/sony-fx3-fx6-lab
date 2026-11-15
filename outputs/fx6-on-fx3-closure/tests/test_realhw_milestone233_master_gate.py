"""Phase 233 dual-mode unit tests for Grand Milestone Phase 233 6-Pillar Real-Hardware Master Gate."""

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
from fx6_closure.realhw_milestone233_master_gate import (  # noqa: E402
    CALIBRATION_MUTATION_BYTES,
    CP_MUTATION_BYTES,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    EMMC_WRITE_COUNT,
    E_ND_ACTUATOR_TX_COUNT,
    FIRMWARE_LAB_45_AUDITOR_KEYS,
    HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    ISP_WRITE_AUTHORIZED,
    MILESTONE233_SCHEMA_VERSION,
    OTP_FUSE_TOUCHES,
    OTP_FUSE_WRITES,
    OVERALL_READY_FOR_HARDWARE_ATTACH,
    P8_CP_MUTATION_FORBIDDEN,
    PASSIVE_TX_BYTES,
    PASSIVE_TX_BYTES_EMITTED,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHASE_233_VERSION,
    PHYSICAL_DEVICE_WRITES,
    PHYSICAL_USB_PACKETS_EMITTED,
    PILLAR_IDS,
    PILLAR_SPECS,
    PNG_MAGIC_BYTES,
    PNG_MAX_SIZE_50KIB_BYTES,
    PNG_MAX_SIZE_BYTES,
    RAW_FIRMWARE_BYTES_LEAKED,
    REALHW_MILESTONE233_SCHEMA,
    RECOVERY_38_PILLAR_IDS,
    ROUND28_TO_47_PNG_RECEIPTS,
    ROUND28_TO_47_SPECS,
    ROUND43_EXPECTED_SCHEMA,
    ROUND44_EXPECTED_SCHEMA,
    ROUND45_EXPECTED_SCHEMA,
    ROUND46_EXPECTED_SCHEMA,
    ROUND47_EXPECTED_SCHEMA,
    RPMB_COUNTER_INCREMENTS,
    RPMB_WRITES,
    SPI_NOR_WRITE_AUTHORIZED,
    STATUS_FAIL_CLOSED,
    STATUS_MILESTONE_READY,
    USB_OR_CAMERA_OPERATIONS,
    USB_PACKETS_TRANSMITTED,
    VM_COEMULATION_44_STAGE_KEYS,
    WBI_MUTATION_BYTES,
    WBI_P5_WRITE_AND_HIBERNATION_FORBIDDEN,
    RealHwMilestone233FaultInjection,
    RealHwMilestone233MasterGateReport,
    _collect_parallel_milestone233_results,
    _evaluate_pillar_1,
    _evaluate_pillar_2,
    _evaluate_pillar_3,
    _evaluate_pillar_4,
    _evaluate_pillar_5,
    _evaluate_pillar_6,
    _fault_to_90gate_worker_dict,
    _normalize_38pillar_fault_id,
    _worker_90gate_single,
    _worker_phase227,
    _worker_recovery_38pillar,
    build_realhw_milestone233_master_gate_report,
    compute_milestone233_sha256,
    evaluate_milestone233_master_gate,
    evaluate_realhw_milestone233_master_gate,
    render_milestone233_markdown,
    verify_realhw_milestone233_master_gate,
)

_RAW_BYTES_REPR_REGEX = r"(?<![0-9A-Za-z_/.-])b['\"]"


class TestRealHwMilestone233MasterGate(unittest.TestCase):
    """Comprehensive >= 55 dual-mode tests for Grand Milestone Phase 233 (< 8.0s total)."""

    raw_bundle: tuple
    rep_default: RealHwMilestone233MasterGateReport
    rep_clean: RealHwMilestone233MasterGateReport
    default_elapsed_s: float

    @classmethod
    def setUpClass(cls) -> None:
        from concurrent.futures import ThreadPoolExecutor

        def _get_clean():
            return _collect_parallel_milestone233_results(
                repo_root=REPO_ROOT,
                fx6_lib_dir=DEFAULT_FX6_DONOR_LIB_DIR,
                fx3_modules_dir=DEFAULT_FX3_MODULES_DIR,
                use_clean_room=True,
                faults=RealHwMilestone233FaultInjection(),
            )

        t0 = time.monotonic()
        if _is_forced_clean_room():
            cls.raw_bundle = _get_clean()
            cls.rep_clean = evaluate_realhw_milestone233_master_gate(
                force_clean_room=True,
                _raw_bundle_override=cls.raw_bundle,
            )
            cls.rep_default = cls.rep_clean
        else:
            with ThreadPoolExecutor(max_workers=2) as pool:
                fut_clean = pool.submit(_get_clean)
                fut_def = pool.submit(evaluate_realhw_milestone233_master_gate)
                cls.raw_bundle = fut_clean.result()
                cls.rep_default = fut_def.result()
            cls.rep_clean = evaluate_realhw_milestone233_master_gate(
                force_clean_room=True,
                _raw_bundle_override=cls.raw_bundle,
            )
        cls.default_elapsed_s = time.monotonic() - t0

    def _unpack_clean_raw(self):
        return copy.deepcopy(self.raw_bundle)

    # --- 1. Constants, Exports & Schema ---

    def test_01_schema_and_version_constants(self) -> None:
        self.assertEqual(REALHW_MILESTONE233_SCHEMA, "realhw_milestone233_master_gate_v1")
        self.assertEqual(MILESTONE233_SCHEMA_VERSION, REALHW_MILESTONE233_SCHEMA)
        self.assertEqual(PHASE_233_VERSION, "233.0.0")
        self.assertEqual(PILLAR_IDS, ("P1", "P2", "P3", "P4", "P5", "P6"))
        self.assertEqual(len(PILLAR_SPECS), 6)
        self.assertGreaterEqual(len(RECOVERY_38_PILLAR_IDS), 38)
        self.assertGreaterEqual(len(FIRMWARE_LAB_45_AUDITOR_KEYS), 45)
        self.assertGreaterEqual(len(VM_COEMULATION_44_STAGE_KEYS), 44)
        self.assertGreaterEqual(len(ROUND28_TO_47_SPECS), 20)
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
            "FIRMWARE_LAB_45_AUDITOR_KEYS",
            "MILESTONE233_PHYSICAL_DEVICE_WRITES",
            "MILESTONE233_PILLAR_IDS",
            "MILESTONE233_PILLAR_SPECS",
            "MILESTONE233_PNG_MAX_SIZE_BYTES",
            "MILESTONE233_RAW_FIRMWARE_BYTES_LEAKED",
            "MILESTONE233_SCHEMA_VERSION",
            "OVERALL_READY_FOR_HARDWARE_ATTACH",
            "PHASE_233_VERSION",
            "PNG_MAX_SIZE_50KIB_BYTES",
            "REALHW_MILESTONE233_SCHEMA",
            "RECOVERY_38_PILLAR_IDS",
            "ROUND28_TO_47_PNG_RECEIPTS",
            "ROUND28_TO_47_SPECS",
            "ROUND43_EXPECTED_SCHEMA",
            "ROUND44_EXPECTED_SCHEMA",
            "ROUND45_EXPECTED_SCHEMA",
            "ROUND46_EXPECTED_SCHEMA",
            "ROUND47_EXPECTED_SCHEMA",
            "STATUS_MILESTONE233_FAIL_CLOSED",
            "STATUS_MILESTONE233_READY",
            "VM_COEMULATION_44_STAGE_KEYS",
            "Milestone233PillarResult",
            "RealHwMilestone233FaultInjection",
            "RealHwMilestone233MasterGateReport",
            "RealHwMilestone233VerifyResult",
            "build_realhw_milestone233_master_gate_report",
            "compute_milestone233_sha256",
            "evaluate_milestone233_master_gate",
            "evaluate_realhw_milestone233_master_gate",
            "render_milestone233_markdown",
            "verify_realhw_milestone233_master_gate",
        }
        self.assertTrue(expected.issubset(set(fx6_closure.__all__)))
        for sym in expected:
            self.assertTrue(hasattr(fx6_closure, sym), sym)
        # Prior Milestone 221 exports must remain intact
        self.assertEqual(fx6_closure.REALHW_MILESTONE221_SCHEMA, "realhw_milestone221_master_gate_v1")

    def test_04_builder_aliases_point_to_evaluate(self) -> None:
        self.assertIs(build_realhw_milestone233_master_gate_report, evaluate_realhw_milestone233_master_gate)
        self.assertIs(evaluate_milestone233_master_gate, evaluate_realhw_milestone233_master_gate)

    def test_05_round43_to_47_specs_and_png_pairs_registered(self) -> None:
        by_num = {s.round_num: s for s in ROUND28_TO_47_SPECS}
        for rnum, exp_schema in (
            (43, ROUND43_EXPECTED_SCHEMA),
            (44, ROUND44_EXPECTED_SCHEMA),
            (45, ROUND45_EXPECTED_SCHEMA),
            (46, ROUND46_EXPECTED_SCHEMA),
            (47, ROUND47_EXPECTED_SCHEMA),
        ):
            self.assertIn(rnum, by_num)
            self.assertEqual(by_num[rnum].expected_schema, exp_schema)
            self.assertEqual(len(by_num[rnum].run_specs), 3)
            self.assertIn(rnum, ROUND28_TO_47_PNG_RECEIPTS)
            self.assertEqual(len(ROUND28_TO_47_PNG_RECEIPTS[rnum]), 2)

    def test_06_normalize_38pillar_fault_id_resolves_short_and_full_ids(self) -> None:
        self.assertIsNone(_normalize_38pillar_fault_id(None))
        self.assertIsNone(_normalize_38pillar_fault_id(""))
        self.assertEqual(
            _normalize_38pillar_fault_id("pillar_38"),
            "pillar_38_shoe_audio_wind_saveload_vault",
        )
        self.assertEqual(
            _normalize_38pillar_fault_id("pillar_38_shoe_audio_wind_saveload_vault"),
            "pillar_38_shoe_audio_wind_saveload_vault",
        )

    # --- 2. End-to-End Dual-Mode Reports, Determinism & Markdown ---

    def test_07_default_mode_report_all_6_pillars_ready(self) -> None:
        rep = self.rep_default
        self.assertTrue(rep.all_pillars_milestone_ready, rep.errors)
        self.assertEqual(rep.status, STATUS_MILESTONE_READY)
        self.assertEqual(rep.passed_pillar_count, 6)
        self.assertEqual(rep.failed_pillar_ids, ())
        self.assertLess(self.default_elapsed_s, 7.5)
        v = verify_realhw_milestone233_master_gate(rep)
        self.assertTrue(v.valid, v.errors)

    def test_08_clean_room_mode_report_all_6_pillars_ready(self) -> None:
        rep = self.rep_clean
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(rep.all_pillars_milestone_ready, rep.errors)
        self.assertEqual(rep.status, STATUS_MILESTONE_READY)
        self.assertTrue(rep.cnflasha_userspace_write_blocked)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.hardware_live_attachment_authorized)
        self.assertEqual(rep.usb_packets_transmitted, 0)
        self.assertEqual(rep.physical_device_writes, 0)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)
        self.assertTrue(verify_realhw_milestone233_master_gate(rep.to_dict()).valid)

    def test_09_forward_compatible_lower_bounds_on_clean_report(self) -> None:
        rep = self.rep_clean
        self.assertGreaterEqual(rep.gate90_total_gates, 90)
        self.assertGreaterEqual(rep.gate90_offline_verified, 87)
        self.assertEqual(rep.gate90_offline_verified, rep.gate90_total_gates - 3)
        self.assertEqual(rep.gate90_simulated_verified, rep.gate90_total_gates)
        self.assertTrue(rep.gate90_all_verified)
        self.assertGreaterEqual(rep.recovery_pillar_count, 38)
        self.assertEqual(rep.recovery_pillars_passed, rep.recovery_pillar_count)
        self.assertGreaterEqual(rep.auditors_passed, 45)
        self.assertEqual(rep.auditors_passed, rep.auditors_total)
        self.assertGreaterEqual(rep.vm_stages_passed, 44)
        self.assertEqual(rep.vm_stages_passed, rep.vm_stages_total)
        self.assertGreaterEqual(rep.qemu_rounds_verified, 20)
        self.assertGreaterEqual(rep.qemu_runs_verified, 60)
        self.assertGreaterEqual(rep.qemu_png_receipts_verified, 40)
        self.assertLess(rep.qemu_png_max_bytes, PNG_MAX_SIZE_50KIB_BYTES)
        self.assertEqual(rep.h0_equals_h3_count, 16)

    def test_10_deterministic_json_and_sha256_recomputation(self) -> None:
        j1 = self.rep_clean.to_deterministic_json()
        parsed = json.loads(j1)
        self.assertEqual(compute_milestone233_sha256(parsed), self.rep_clean.milestone233_sha256)
        rep2 = evaluate_realhw_milestone233_master_gate(
            force_clean_room=True,
            _raw_bundle_override=self._unpack_clean_raw(),
        )
        self.assertEqual(rep2.milestone233_sha256, self.rep_clean.milestone233_sha256)

    def test_11_no_raw_bytes_repr_in_serialized_reports(self) -> None:
        for rep in (self.rep_default, self.rep_clean):
            self.assertIsNone(re.search(_RAW_BYTES_REPR_REGEX, rep.to_deterministic_json()))

    def test_12_markdown_renderer_contains_bilingual_headers_and_6_pillars(self) -> None:
        md = render_milestone233_markdown(self.rep_clean)
        for token in (
            "Grand Milestone Phase 233",
            "realhw_milestone233_master_gate_v1",
            "MILESTONE_233_PREBENCH_MASTER_VERIFIED",
            "90-Gate Preflight",
            "38-Pillar Recovery Master",
            "Ph227=",
            "| `P1` |",
            "| `P6` |",
        ):
            self.assertIn(token, md)

    # --- 3. Pillar 1: >= 90 Safety Gates (`fx3_safety.evaluate_90gate_preflight`) ---

    def test_13_pillar1_90gate_happy_path_and_g63_to_g90_valid(self) -> None:
        raw_off, raw_sim = self._unpack_clean_raw()[:2]
        p1 = _evaluate_pillar_1(raw_off, raw_sim)
        self.assertTrue(p1.passed, p1.errors)
        self.assertGreaterEqual(p1.evidence["offline_verified_gates"], 87)
        self.assertGreaterEqual(p1.evidence["simulated_verified_gates"], 90)
        self.assertTrue(p1.evidence["all_90_gates_verified"])
        for idx in range(63, 91):
            self.assertTrue(p1.evidence["g63_to_g90_valid"][f"g{idx}"], f"g{idx}")

    def test_14_pillar1_forward_compatible_with_92_gates(self) -> None:
        raw_off, raw_sim = self._unpack_clean_raw()[:2]
        raw_off["total_gates"] = 92
        raw_off["verified_gates"] = 89
        raw_sim["total_gates"] = 92
        raw_sim["verified_gates"] = 92
        p1 = _evaluate_pillar_1(raw_off, raw_sim)
        self.assertTrue(p1.passed, p1.errors)

    def test_15_pillar1_fails_when_offline_tier0_gates_not_blocked(self) -> None:
        raw_off, raw_sim = self._unpack_clean_raw()[:2]
        raw_off["verified_gates"] = 90
        raw_off["blocked_or_pending_gates"] = 0
        self.assertFalse(_evaluate_pillar_1(raw_off, raw_sim).passed)

    def test_16_pillar1_fails_when_all_90_gates_verified_false_in_dry_run(self) -> None:
        raw_off, raw_sim = self._unpack_clean_raw()[:2]
        raw_sim["all_90_gates_verified"] = False
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

    def test_19_pillar1_fails_when_any_g79_to_g90_gate_invalid(self) -> None:
        for gtag in ("g79", "g82", "g85", "g88", "g89", "g90"):
            raw_off, raw_sim = self._unpack_clean_raw()[:2]
            raw_sim["nested_g_valid"][gtag] = False
            p1 = _evaluate_pillar_1(raw_off, raw_sim)
            self.assertFalse(p1.passed, gtag)
            self.assertIn(gtag.upper(), p1.errors[-1])

    def test_20_pillar1_worker_live_g90_touch_fault_and_persistent_write_fault(self) -> None:
        fdict = _fault_to_90gate_worker_dict(
            RealHwMilestone233FaultInjection(
                p1_touch_op_sunny_weather_kwargs={"observed_accidental_fn_swipe_triggered": True},
                p1_request_persistent_writes=True,
            )
        )
        raw_sim_bad = _worker_90gate_single((str(REPO_ROOT), True, True, fdict))
        raw_off = self._unpack_clean_raw()[0]
        p1 = _evaluate_pillar_1(raw_off, raw_sim_bad)
        self.assertFalse(p1.passed)
        self.assertFalse(raw_sim_bad["nested_g_valid"]["g90"])

    # --- 4. Pillar 2: >= 38 Recovery Pillars (`evaluate_realhw_38pillar_recovery_master`) ---

    def test_21_pillar2_38pillar_happy_path_and_cnflasha_ro(self) -> None:
        rec_38 = self._unpack_clean_raw()[2]
        p2, meta2 = _evaluate_pillar_2(rec_38, RealHwMilestone233FaultInjection())
        self.assertTrue(p2.passed, p2.errors)
        self.assertGreaterEqual(meta2["recovery_pillar_count"], 38)
        self.assertEqual(meta2["recovery_pillars_passed"], meta2["recovery_pillar_count"])
        self.assertTrue(meta2["cnflasha_userspace_write_blocked"])
        self.assertEqual(meta2["otp_fuse_writes"], 0)
        self.assertEqual(meta2["rpmb_writes"], 0)

    def test_22_pillar2_forward_compatible_with_40_pillars(self) -> None:
        rec_38 = self._unpack_clean_raw()[2]
        rec_38["pillar_count"] = 40
        rec_38["pillars_passed"] = 40
        rec_38["status"] = "VERIFIED_40OF40_PILLAR_RECOVERY_MASTER"
        p2, meta2 = _evaluate_pillar_2(rec_38, RealHwMilestone233FaultInjection())
        self.assertTrue(p2.passed, p2.errors)
        self.assertEqual(meta2["recovery_pillar_count"], 40)

    def test_23_pillar2_fails_when_cnflasha_userspace_write_unblocked(self) -> None:
        rec_38 = self._unpack_clean_raw()[2]
        p2, _ = _evaluate_pillar_2(
            rec_38,
            RealHwMilestone233FaultInjection(p2_cnflasha_write_unblocked_fault=True),
        )
        self.assertFalse(p2.passed)

    def test_24_pillar2_fails_on_otp_rpmb_passive_tx_usb_devwrite_or_leak_overrides(self) -> None:
        rec_38 = self._unpack_clean_raw()[2]
        for kw in (
            {"p2_otp_fuse_touches_override": 1},
            {"p2_rpmb_counter_increments_override": 1},
            {"p2_passive_tx_bytes_override": 4},
            {"p2_physical_usb_packets_override": 1},
            {"p2_physical_device_writes_override": 1},
            {"p2_raw_firmware_bytes_leaked_override": 8},
        ):
            p2, _ = _evaluate_pillar_2(rec_38, RealHwMilestone233FaultInjection(**kw))
            self.assertFalse(p2.passed, kw)

    def test_25_pillar2_fails_when_38a_or_38b_vault_subsuite_fails(self) -> None:
        for sub_key in ("pillar38_a_shoe_audio_wind_vault", "pillar38_b_saveload_c3_exclusion_vault"):
            rec_38 = self._unpack_clean_raw()[2]
            rec_38[sub_key]["passed"] = False
            self.assertFalse(_evaluate_pillar_2(rec_38, RealHwMilestone233FaultInjection())[0].passed)

    def test_26_pillar2_live_worker_fault_inject_pillar_38_fails_closed(self) -> None:
        bad_38 = _worker_recovery_38pillar((True, "pillar_38"))
        p2, _ = _evaluate_pillar_2(bad_38, RealHwMilestone233FaultInjection())
        self.assertFalse(p2.passed)

    def test_27_pillar2_fails_on_secret_leak_or_unverified_slot1_camset_mutation(self) -> None:
        rec_38 = self._unpack_clean_raw()[2]
        rec_38["excluded_secret_or_cal_leak_count"] = 1
        self.assertFalse(_evaluate_pillar_2(rec_38, RealHwMilestone233FaultInjection())[0].passed)

    # --- 5. Pillar 3: >= 45 Firmware Auditors (`outputs/fx3-firmware-lab`) ---

    def test_28_pillar3_45_auditors_happy_path(self) -> None:
        auditors = self._unpack_clean_raw()[3]
        p3, meta3 = _evaluate_pillar_3(auditors, RealHwMilestone233FaultInjection())
        self.assertTrue(p3.passed, p3.errors)
        self.assertGreaterEqual(meta3["auditor_count"], 45)
        self.assertEqual(meta3["passed_count"], meta3["auditor_count"])
        self.assertEqual(meta3["raw_firmware_bytes_leaked"], 0)
        self.assertTrue(
            p3.evidence["auditor_statuses"]["realhw_filesettings_shotmark_tcregen_and_reclamp_audit"]
        )

    def test_29_pillar3_forward_compatible_with_46_plus_auditors(self) -> None:
        auditors = self._unpack_clean_raw()[3]
        auditors["realhw_future_wave33_audit"] = {"all_checks_passed": True}
        p3, meta3 = _evaluate_pillar_3(auditors, RealHwMilestone233FaultInjection())
        self.assertTrue(p3.passed, p3.errors)
        self.assertGreaterEqual(meta3["auditor_count"], 46)
        self.assertEqual(meta3["passed_count"], meta3["auditor_count"])

    def test_30_pillar3_fails_on_auditor45_guard_fault_or_subpillar_failure(self) -> None:
        auditors = self._unpack_clean_raw()[3]
        p3_fault, _ = _evaluate_pillar_3(
            auditors,
            RealHwMilestone233FaultInjection(p3_filesettings_tcregen_reclamp_guard_fault=True),
        )
        self.assertFalse(p3_fault.passed)

        auditors2 = self._unpack_clean_raw()[3]
        auditors2["realhw_filesettings_shotmark_tcregen_and_reclamp_audit"][
            "pillar_2_tc_regenerate_slot1_and_ext_lk"
        ]["passed"] = False
        self.assertFalse(_evaluate_pillar_3(auditors2, RealHwMilestone233FaultInjection())[0].passed)

    def test_31_pillar3_fails_on_raw_firmware_bytes_leaked_override(self) -> None:
        auditors = self._unpack_clean_raw()[3]
        p3, _ = _evaluate_pillar_3(
            auditors,
            RealHwMilestone233FaultInjection(p3_raw_firmware_bytes_leaked_override=16),
        )
        self.assertFalse(p3.passed)

    def test_32_pillar3_fails_when_forward_compat_46th_auditor_fails(self) -> None:
        auditors = self._unpack_clean_raw()[3]
        auditors["realhw_broken_future_audit"] = {"all_checks_passed": False}
        self.assertFalse(_evaluate_pillar_3(auditors, RealHwMilestone233FaultInjection())[0].passed)

    # --- 6. Pillar 4: >= 44 VM Co-Emulation Stages (`outputs/fx3-vm`) ---

    def test_33_pillar4_44_stages_happy_path(self) -> None:
        raw_vm = self._unpack_clean_raw()[4]
        p4, meta4 = _evaluate_pillar_4(raw_vm, RealHwMilestone233FaultInjection())
        self.assertTrue(p4.passed, p4.errors)
        self.assertGreaterEqual(meta4["stage_count"], 44)
        self.assertEqual(meta4["passed_count"], meta4["stage_count"])
        self.assertEqual(meta4["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(meta4["physical_device_writes"], 0)
        self.assertEqual(meta4["emmc_corruptions"], 0)

    def test_34_pillar4_forward_compatible_with_45_plus_stages(self) -> None:
        raw_vm = self._unpack_clean_raw()[4]
        raw_vm["stage45_realhw_future_wave33_hil"] = {"all_checks_passed": True}
        p4, meta4 = _evaluate_pillar_4(raw_vm, RealHwMilestone233FaultInjection())
        self.assertTrue(p4.passed, p4.errors)
        self.assertGreaterEqual(meta4["stage_count"], 45)
        self.assertEqual(meta4["passed_count"], meta4["stage_count"])

    def test_35_pillar4_fails_on_stage39_through_stage44_fault_injections(self) -> None:
        raw_vm = self._unpack_clean_raw()[4]
        for kw in (
            {"p4_stage39_filesettings_tcregen_faults": 1},
            {"p4_stage40_pixelmap_ntscpal_faults": 1},
            {"p4_stage41_steadyshot_ciz_powersave_faults": 1},
            {"p4_stage42_sq_zebra_fullformat_faults": 1},
            {"p4_stage43_silent_autopixelmap_marker_faults": 1},
            {"p4_stage44_recover_imagedb_flip_af_faults": 1},
        ):
            p4, _ = _evaluate_pillar_4(raw_vm, RealHwMilestone233FaultInjection(**kw))
            self.assertFalse(p4.passed, kw)

    def test_36_pillar4_fails_on_physical_device_writes_or_raw_leak(self) -> None:
        raw_vm = self._unpack_clean_raw()[4]
        for kw in (
            {"p4_physical_device_writes_override": 1},
            {"p4_raw_firmware_bytes_leaked_override": 4},
        ):
            p4, _ = _evaluate_pillar_4(raw_vm, RealHwMilestone233FaultInjection(**kw))
            self.assertFalse(p4.passed, kw)

    def test_37_pillar4_fails_on_stage44_cnflasha_unblocked_or_emmc_mutation(self) -> None:
        raw_vm = self._unpack_clean_raw()[4]
        raw_vm["stage44_realhw_recover_imagedb_monitor_flip_af_sens_hil"][
            "cnflasha_userspace_write_blocked"
        ] = False
        self.assertFalse(_evaluate_pillar_4(raw_vm, RealHwMilestone233FaultInjection())[0].passed)

        raw_vm2 = self._unpack_clean_raw()[4]
        raw_vm2["stage42_realhw_sq_fixedvar_zebra_peaking_fullformat_hil"]["emmc_mutation_bytes"] = 64
        self.assertFalse(_evaluate_pillar_4(raw_vm2, RealHwMilestone233FaultInjection())[0].passed)

    def test_38_pillar4_fails_when_future_stage45_fails(self) -> None:
        raw_vm = self._unpack_clean_raw()[4]
        raw_vm["stage45_broken_hil"] = {"all_checks_passed": False}
        self.assertFalse(_evaluate_pillar_4(raw_vm, RealHwMilestone233FaultInjection())[0].passed)

    # --- 7. Pillar 5: 4 Bench Readiness Verifiers (`P186`, `P204`, `P216`, `P227`) ---

    def test_39_pillar5_quad_bench_preflights_happy_path(self) -> None:
        b = self._unpack_clean_raw()
        p5, meta5 = _evaluate_pillar_5(*b[5:16], RealHwMilestone233FaultInjection())
        self.assertTrue(p5.passed, p5.errors)
        self.assertFalse(meta5["overall_ready_for_hardware_attach"])
        for off_k, sim_k in (
            ("p186_offline_go_no_go", "p186_sim_go_no_go"),
            ("p204_offline_go_no_go", "p204_sim_go_no_go"),
            ("p216_offline_go_no_go", "p216_sim_go_no_go"),
            ("p227_offline_go_no_go", "p227_sim_go_no_go"),
        ):
            self.assertEqual(meta5[off_k], GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT)
            self.assertEqual(meta5[sim_k], GO_NO_GO_DRY_RUN_SIMULATED_READY)
        self.assertEqual(meta5["p227_sim_check_groups_passed"], 3)
        self.assertEqual(meta5["p227_h0_equals_h3_count"], 16)
        self.assertFalse(meta5["p227_hardware_live_attachment_authorized"])

    def test_40_pillar5_rejects_phase227_lowbatt_and_ntscpal_fps_conflict(self) -> None:
        b = self._unpack_clean_raw()
        p227_off, p227_sim = _worker_phase227(
            (
                str(DEFAULT_FX6_DONOR_LIB_DIR),
                str(DEFAULT_FX3_MODULES_DIR),
                True,
                {"pixelmap_lowbatt": True, "ntscpal_fps_conflict": True},
            )
        )
        p5, _ = _evaluate_pillar_5(
            *b[5:14], p227_off, p227_sim, RealHwMilestone233FaultInjection()
        )
        self.assertFalse(p5.passed)

    def test_41_pillar5_rejects_phase227_powersave_p3_sleep_and_autotemp_no_tripod(self) -> None:
        b = self._unpack_clean_raw()
        p227_off, p227_sim = _worker_phase227(
            (
                str(DEFAULT_FX6_DONOR_LIB_DIR),
                str(DEFAULT_FX3_MODULES_DIR),
                True,
                {"powersave_p3_sleep": True, "autotemp_no_tripod": True},
            )
        )
        p5, _ = _evaluate_pillar_5(
            *b[5:14], p227_off, p227_sim, RealHwMilestone233FaultInjection()
        )
        self.assertFalse(p5.passed)

    def test_42_pillar5_rejects_phase227_h0_h3_drift(self) -> None:
        b = list(self._unpack_clean_raw())
        b[15]["h0_equals_h3_count"] = 15
        p5, _ = _evaluate_pillar_5(*b[5:16], RealHwMilestone233FaultInjection())
        self.assertFalse(p5.passed)

    def test_43_pillar5_rejects_phase227_usb_packets_override(self) -> None:
        b = self._unpack_clean_raw()
        p5, _ = _evaluate_pillar_5(
            *b[5:16],
            RealHwMilestone233FaultInjection(p5_inject_p227_usb_packets_override=1),
        )
        self.assertFalse(p5.passed)

    def test_44_pillar5_rejects_phase227_offline_if_not_blocked_awaiting_tier0(self) -> None:
        b = list(self._unpack_clean_raw())
        b[14]["go_no_go"] = GO_NO_GO_DRY_RUN_SIMULATED_READY
        p5, _ = _evaluate_pillar_5(*b[5:16], RealHwMilestone233FaultInjection())
        self.assertFalse(p5.passed)

    def test_45_pillar5_rejects_overall_ready_for_hardware_attach_true(self) -> None:
        b = list(self._unpack_clean_raw())
        b[15]["overall_ready_for_hardware_attach"] = True
        p5, _ = _evaluate_pillar_5(*b[5:16], RealHwMilestone233FaultInjection())
        self.assertFalse(p5.passed)

    # --- 8. Pillar 6: Live FX3 7.02 QEMU Rounds 28..47+ & < 50 KiB PNG Receipts ---

    def _clean_p1_to_p5_metas(self):
        b = self._unpack_clean_raw()
        f = RealHwMilestone233FaultInjection()
        p1 = _evaluate_pillar_1(b[0], b[1])
        _, m2 = _evaluate_pillar_2(b[2], f)
        _, m3 = _evaluate_pillar_3(b[3], f)
        _, m4 = _evaluate_pillar_4(b[4], f)
        _, m5 = _evaluate_pillar_5(*b[5:16], f)
        return p1.evidence, m2, m3, m4, m5

    def test_46_pillar6_rounds_28_to_47_at_least_20_rounds_60_runs_40_pngs(self) -> None:
        m1, m2, m3, m4, m5 = self._clean_p1_to_p5_metas()
        p6, meta6 = _evaluate_pillar_6(
            repo_root=REPO_ROOT,
            use_clean_room=True,
            faults=RealHwMilestone233FaultInjection(),
            p1_meta=m1,
            p2_meta=m2,
            p3_meta=m3,
            p4_meta=m4,
            p5_meta=m5,
        )
        self.assertTrue(p6.passed, p6.errors)
        self.assertGreaterEqual(meta6["qemu_rounds_verified"], 20)
        self.assertGreaterEqual(meta6["qemu_runs_verified"], 60)
        self.assertGreaterEqual(meta6["qemu_png_receipts_verified"], 40)
        for rnum in (43, 44, 45, 46, 47):
            self.assertEqual(meta6["qemu_round_runs_by_round"][f"r{rnum}"], 3)

    def test_47_pillar6_committed_round43_to_47_png_headers_under_50kib(self) -> None:
        for rnum in range(43, 48):
            for rel in ROUND28_TO_47_PNG_RECEIPTS[rnum]:
                p = REPO_ROOT / rel
                if p.is_file():
                    raw = p.read_bytes()
                    self.assertTrue(raw.startswith(PNG_MAGIC_BYTES), rel)
                    self.assertLess(len(raw), PNG_MAX_SIZE_50KIB_BYTES, rel)

    def test_48_pillar6_forward_compatible_with_round48_directory_discovery(self) -> None:
        m1, m2, m3, m4, m5 = self._clean_p1_to_p5_metas()
        with tempfile.TemporaryDirectory() as tmp:
            tmp_root = Path(tmp)
            r48_dir = tmp_root / "reports" / "2026-11-16-round48-realhw-future-wave33-qemu"
            assets_dir = r48_dir / "assets"
            assets_dir.mkdir(parents=True, exist_ok=True)
            for name in ("r48a-alpha.png", "r48a-composited.png"):
                (assets_dir / name).write_bytes(PNG_MAGIC_BYTES + b"\x00" * 128)
            summary = {
                "schema": "fx6-on-fx3-round48-realhw-future-wave33-qemu-v1",
                "round": 48,
                "kernel_version": "Linux version 4.9.337-scel+ (clean-room-synthetic)",
                "raw_firmware_bytes_leaked": 0,
                "runs": {
                    "r48a_run": {"nop_count": 0, "crashes": 0, "emmc_write_count": 0, "stage_b": {"manifest_count": 13}},
                    "r48b_run": {"nop_count": None, "crashes": 0, "emmc_write_count": 0, "stage_b": {"manifest_count": 13}},
                    "r48c_run": {"nop_count": None, "crashes": 0, "emmc_write_count": 0, "stage_b": {"manifest_count": 13}},
                },
                "r48_realhw_future_wave33_audit": {
                    "all_3_runs_crashes_zero": True,
                    "all_3_runs_emmc_write_zero": True,
                },
            }
            (r48_dir / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
            p6, meta6 = _evaluate_pillar_6(
                repo_root=tmp_root,
                use_clean_room=True,
                faults=RealHwMilestone233FaultInjection(),
                p1_meta=m1,
                p2_meta=m2,
                p3_meta=m3,
                p4_meta=m4,
                p5_meta=m5,
            )
            self.assertTrue(p6.passed, p6.errors)
            self.assertEqual(meta6["qemu_rounds_verified"], 21)
            self.assertEqual(meta6["qemu_runs_verified"], 63)
            self.assertEqual(meta6["qemu_png_receipts_verified"], 42)

    def test_49_pillar6_fails_on_round44_to_47_schema_tamper(self) -> None:
        m1, m2, m3, m4, m5 = self._clean_p1_to_p5_metas()
        for rnum in (44, 45, 46, 47):
            p6, _ = _evaluate_pillar_6(
                repo_root=REPO_ROOT,
                use_clean_room=True,
                faults=RealHwMilestone233FaultInjection(p6_tamper_schema_round_num=rnum),
                p1_meta=m1,
                p2_meta=m2,
                p3_meta=m3,
                p4_meta=m4,
                p5_meta=m5,
            )
            self.assertFalse(p6.passed, rnum)

    def test_50_pillar6_fails_on_round47_nop_crash_or_emmc_write(self) -> None:
        m1, m2, m3, m4, m5 = self._clean_p1_to_p5_metas()
        for fkw in (
            {"p6_round_nop_override_num": 47, "p6_round_nop_count_override": 1},
            {"p6_round_crash_override_num": 47, "p6_round_crashes_override": 1},
            {"p6_round_emmc_override_num": 47, "p6_round_emmc_writes_override": 1},
        ):
            p6, _ = _evaluate_pillar_6(
                repo_root=REPO_ROOT,
                use_clean_room=True,
                faults=RealHwMilestone233FaultInjection(**fkw),
                p1_meta=m1,
                p2_meta=m2,
                p3_meta=m3,
                p4_meta=m4,
                p5_meta=m5,
            )
            self.assertFalse(p6.passed, fkw)

    def test_51_pillar6_fails_when_png_receipt_exceeds_50kib_ceiling(self) -> None:
        m1, m2, m3, m4, m5 = self._clean_p1_to_p5_metas()
        p6, _ = _evaluate_pillar_6(
            repo_root=REPO_ROOT,
            use_clean_room=True,
            faults=RealHwMilestone233FaultInjection(
                p6_png_size_override_round_num=47,
                p6_png_size_override_bytes=PNG_MAX_SIZE_50KIB_BYTES,
            ),
            p1_meta=m1,
            p2_meta=m2,
            p3_meta=m3,
            p4_meta=m4,
            p5_meta=m5,
        )
        self.assertFalse(p6.passed)

    def test_52_pillar6_cross_pillar_invariants_fail_closed(self) -> None:
        m1, m2, m3, m4, m5 = self._clean_p1_to_p5_metas()
        m5_bad = dict(m5)
        m5_bad["p227_h0_equals_h3_count"] = 15
        p6, _ = _evaluate_pillar_6(
            repo_root=REPO_ROOT,
            use_clean_room=True,
            faults=RealHwMilestone233FaultInjection(),
            p1_meta=m1,
            p2_meta=m2,
            p3_meta=m3,
            p4_meta=m4,
            p5_meta=m5_bad,
        )
        self.assertFalse(p6.passed)

    # --- 9. Fail-Closed Verifier & CLI `verify-milestone-233` ---

    def test_53_verifier_rejects_non_mapping_payload(self) -> None:
        self.assertFalse(verify_realhw_milestone233_master_gate("not-a-dict").valid)
        self.assertFalse(verify_realhw_milestone233_master_gate(123).valid)

    def test_54_verifier_rejects_sha256_tamper_and_schema_tamper(self) -> None:
        d = self.rep_clean.to_dict()
        d["milestone233_sha256"] = "f" * 64
        self.assertFalse(verify_realhw_milestone233_master_gate(d).valid)

        d2 = self.rep_clean.to_dict()
        d2["schema"] = "wrong_schema_v1"
        d2["milestone233_sha256"] = compute_milestone233_sha256(d2)
        self.assertFalse(verify_realhw_milestone233_master_gate(d2).valid)

    def test_55_verifier_rejects_redline_tamper_even_when_rehashed(self) -> None:
        for k, v in (
            ("overall_ready_for_hardware_attach", True),
            ("hardware_live_attachment_authorized", True),
            ("cnflasha_userspace_write_blocked", False),
            ("usb_packets_transmitted", 1),
            ("physical_device_writes", 1),
            ("raw_firmware_bytes_leaked", 1),
            ("p227_hardware_live_attachment_authorized", True),
        ):
            d = self.rep_clean.to_dict()
            d[k] = v
            d["milestone233_sha256"] = compute_milestone233_sha256(d)
            self.assertFalse(verify_realhw_milestone233_master_gate(d).valid, k)

    def test_56_verifier_accepts_forward_compatible_higher_counts(self) -> None:
        d = self.rep_clean.to_dict()
        d["gate90_total_gates"] = 92
        d["gate90_offline_verified"] = 89
        d["gate90_simulated_verified"] = 92
        d["recovery_pillar_count"] = 40
        d["recovery_pillars_passed"] = 40
        d["auditors_total"] = 46
        d["auditors_passed"] = 46
        d["vm_stages_total"] = 46
        d["vm_stages_passed"] = 46
        d["qemu_rounds_total"] = 21
        d["qemu_rounds_verified"] = 21
        d["qemu_runs_total"] = 63
        d["qemu_runs_verified"] = 63
        d["qemu_png_receipts_total"] = 42
        d["qemu_png_receipts_verified"] = 42
        d["milestone233_sha256"] = compute_milestone233_sha256(d)
        v = verify_realhw_milestone233_master_gate(d)
        self.assertTrue(v.valid, v.errors)

    def test_57_verifier_rejects_sub_threshold_or_mismatched_counts_and_raw_bytes(self) -> None:
        for k, v in (
            ("gate90_simulated_verified", 89),
            ("recovery_pillar_count", 37),
            ("auditors_passed", 44),
            ("vm_stages_passed", 43),
            ("p227_sim_check_groups_passed", 2),
            ("qemu_rounds_verified", 19),
            ("qemu_runs_verified", 59),
            ("qemu_png_receipts_verified", 39),
        ):
            d = self.rep_clean.to_dict()
            d[k] = v
            d["milestone233_sha256"] = compute_milestone233_sha256(d)
            self.assertFalse(verify_realhw_milestone233_master_gate(d).valid, k)

        d_raw = self.rep_clean.to_dict()
        d_raw["pillars"][0]["summary"] = "leaked b'\\x7fELF'"
        d_raw["milestone233_sha256"] = compute_milestone233_sha256(d_raw)
        self.assertFalse(verify_realhw_milestone233_master_gate(d_raw).valid)

    def test_58_cli_verify_milestone_233_summary_and_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            out_json = tmp_path / "m233.json"
            out_md = tmp_path / "m233.md"
            buf = io.StringIO()
            with (
                mock.patch(
                    "fx6_closure.realhw_milestone233_master_gate.evaluate_realhw_milestone233_master_gate",
                    return_value=self.rep_clean,
                ),
                mock.patch("sys.stdout", buf),
            ):
                rc = fx6_cli_main(
                    [
                        "verify-milestone-233",
                        "--force-clean-room",
                        "--output",
                        str(out_json),
                        "--markdown-out",
                        str(out_md),
                    ]
                )
            self.assertEqual(rc, 0)
            text = buf.getvalue()
            self.assertIn("status=OK", text)
            self.assertIn("schema=realhw_milestone233_master_gate_v1", text)
            self.assertIn("cnflasha_ro=True", text)
            self.assertIn("p227_off=BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT", text)
            self.assertIn("p227_sim=DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH", text)
            self.assertIn("ready_attach=False", text)
            self.assertIsNotNone(re.search(r"gate90=(\d+)/(\d+)", text))
            self.assertIsNotNone(re.search(r"qemu=(\d+)/(\d+)\((\d+)/(\d+)\)", text))
            self.assertTrue(out_json.is_file())
            self.assertTrue(out_md.is_file())
            self.assertTrue(
                verify_realhw_milestone233_master_gate(json.loads(out_json.read_text())).valid
            )

    def test_59_cli_verify_milestone_233_json_stdout_and_failure_exit_code(self) -> None:
        buf = io.StringIO()
        with (
            mock.patch(
                "fx6_closure.realhw_milestone233_master_gate.evaluate_realhw_milestone233_master_gate",
                return_value=self.rep_clean,
            ),
            mock.patch("sys.stdout", buf),
        ):
            rc = fx6_cli_main(["verify-milestone-233", "--clean-room", "--json"])
        self.assertEqual(rc, 0)
        parsed = json.loads(buf.getvalue())
        self.assertEqual(parsed["schema"], REALHW_MILESTONE233_SCHEMA)
        self.assertEqual(parsed["usb_packets_transmitted"], 0)
        self.assertFalse(parsed["overall_ready_for_hardware_attach"])

        bad_rep = replace(
            self.rep_clean,
            all_pillars_milestone_ready=False,
            status=STATUS_FAIL_CLOSED,
            passed_pillar_count=5,
            failed_pillar_ids=("P1",),
            milestone233_sha256="0" * 64,
        )
        buf2 = io.StringIO()
        with (
            mock.patch(
                "fx6_closure.realhw_milestone233_master_gate.evaluate_realhw_milestone233_master_gate",
                return_value=bad_rep,
            ),
            mock.patch("sys.stdout", buf2),
        ):
            rc2 = fx6_cli_main(["verify-milestone-233", "--force-clean-room"])
        self.assertEqual(rc2, 1)
        self.assertIn("status=FAILED", buf2.getvalue())

    def test_60_synthetic_clean_room_kwarg_alias_supported(self) -> None:
        rep = evaluate_realhw_milestone233_master_gate(
            synthetic_clean_room=True,
            _raw_bundle_override=self._unpack_clean_raw(),
        )
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(rep.all_pillars_milestone_ready)


if __name__ == "__main__":
    unittest.main()
