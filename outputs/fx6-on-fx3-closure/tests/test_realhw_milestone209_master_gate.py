"""Phase 209 dual-mode unit tests for Grand Milestone Phase 209 6-Pillar Master Gate."""

from __future__ import annotations

import copy
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
from fx6_closure.realhw_milestone209_master_gate import (  # noqa: E402
    CALIBRATION_MUTATION_BYTES,
    CP_MUTATION_BYTES,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    E_ND_ACTUATOR_TX_COUNT,
    FIRMWARE_LAB_42_AUDITOR_KEYS,
    HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    ISP_WRITE_AUTHORIZED,
    MILESTONE209_SCHEMA_VERSION,
    OTP_FUSE_TOUCHES,
    P8_CP_MUTATION_FORBIDDEN,
    PASSIVE_TX_BYTES_EMITTED,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHASE_209_VERSION,
    PHYSICAL_USB_PACKETS_EMITTED,
    PILLAR_IDS,
    PILLAR_SPECS,
    PNG_MAGIC_BYTES,
    PNG_MAX_SIZE_BYTES,
    RAW_FIRMWARE_BYTES_LEAKED,
    REALHW_MILESTONE209_SCHEMA,
    RECOVERY_28_PILLAR_IDS,
    ROUND28_TO_40_PNG_RECEIPTS,
    ROUND28_TO_40_SPECS,
    ROUND38_EXPECTED_SCHEMA,
    ROUND39_EXPECTED_SCHEMA,
    ROUND40_EXPECTED_SCHEMA,
    RPMB_COUNTER_INCREMENTS,
    SPI_NOR_WRITE_AUTHORIZED,
    STATUS_FAIL_CLOSED,
    STATUS_MILESTONE_READY,
    USB_OR_CAMERA_OPERATIONS,
    VM_COEMULATION_36_STAGE_KEYS,
    WBI_MUTATION_BYTES,
    WBI_P5_WRITE_AND_HIBERNATION_FORBIDDEN,
    RealHwMilestone209FaultInjection,
    RealHwMilestone209MasterGateReport,
    _collect_parallel_milestone209_results,
    _evaluate_pillar_1,
    _evaluate_pillar_2,
    _evaluate_pillar_3,
    _evaluate_pillar_4,
    _evaluate_pillar_5,
    _evaluate_pillar_6,
    _worker_phase204,
    build_realhw_milestone209_master_gate_report,
    compute_milestone209_sha256,
    evaluate_milestone209_master_gate,
    render_milestone209_markdown,
    verify_realhw_milestone209_master_gate,
)

_RAW_BYTES_REPR_REGEX = r"(?<![0-9A-Za-z_/.-])b['\"]"


class TestRealHwMilestone209MasterGate(unittest.TestCase):
    """Comprehensive >= 52 dual-mode tests for Grand Milestone Phase 209 (< 8.0s ceiling)."""

    raw_bundle: tuple
    rep_default: RealHwMilestone209MasterGateReport
    rep_clean: RealHwMilestone209MasterGateReport
    default_elapsed_s: float

    @classmethod
    def setUpClass(cls) -> None:
        t0 = time.monotonic()
        cls.rep_default = build_realhw_milestone209_master_gate_report()
        cls.default_elapsed_s = time.monotonic() - t0
        if _is_forced_clean_room():
            cls.rep_clean = cls.rep_default
        else:
            cls.rep_clean = build_realhw_milestone209_master_gate_report(synthetic_clean_room=True)
        cls.raw_bundle = _collect_parallel_milestone209_results(
            repo_root=REPO_ROOT,
            fx6_lib_dir=DEFAULT_FX6_DONOR_LIB_DIR,
            fx3_modules_dir=DEFAULT_FX3_MODULES_DIR,
            use_clean_room=True,
            faults=RealHwMilestone209FaultInjection(),
        )

    def _unpack_clean_raw(self):
        return copy.deepcopy(self.raw_bundle)

    # --- 1. Constants, Exports & Schema ---

    def test_01_schema_and_version_constants(self) -> None:
        self.assertEqual(REALHW_MILESTONE209_SCHEMA, "realhw_milestone209_master_gate_v1")
        self.assertEqual(MILESTONE209_SCHEMA_VERSION, REALHW_MILESTONE209_SCHEMA)
        self.assertEqual(PHASE_209_VERSION, "209.0.0")
        self.assertEqual(PILLAR_IDS, ("P1", "P2", "P3", "P4", "P5", "P6"))
        self.assertEqual(len(PILLAR_SPECS), 6)
        self.assertEqual(len(RECOVERY_28_PILLAR_IDS), 28)
        self.assertEqual(len(FIRMWARE_LAB_42_AUDITOR_KEYS), 42)
        self.assertEqual(len(VM_COEMULATION_36_STAGE_KEYS), 36)
        self.assertEqual(len(ROUND28_TO_40_SPECS), 13)
        self.assertEqual(len(ROUND28_TO_40_PNG_RECEIPTS), 13)

    def test_02_hard_locked_zero_write_constants(self) -> None:
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(PERSISTENT_WRITE_RELEASE)
        self.assertFalse(SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        self.assertFalse(ISP_WRITE_AUTHORIZED)
        self.assertFalse(HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        self.assertTrue(P8_CP_MUTATION_FORBIDDEN)
        self.assertTrue(WBI_P5_WRITE_AND_HIBERNATION_FORBIDDEN)
        self.assertEqual(PHYSICAL_USB_PACKETS_EMITTED, 0)
        self.assertEqual(RAW_FIRMWARE_BYTES_LEAKED, 0)
        self.assertEqual(E_ND_ACTUATOR_TX_COUNT, 0)
        self.assertEqual(OTP_FUSE_TOUCHES, 0)
        self.assertEqual(RPMB_COUNTER_INCREMENTS, 0)
        self.assertEqual(PASSIVE_TX_BYTES_EMITTED, 0)
        self.assertEqual(CP_MUTATION_BYTES, 0)
        self.assertEqual(WBI_MUTATION_BYTES, 0)
        self.assertEqual(CALIBRATION_MUTATION_BYTES, 0)
        self.assertEqual(USB_OR_CAMERA_OPERATIONS, 0)

    def test_03_package_top_level_exports(self) -> None:
        for sym in (
            "REALHW_MILESTONE209_SCHEMA",
            "PHASE_209_VERSION",
            "MILESTONE209_PILLAR_IDS",
            "FIRMWARE_LAB_42_AUDITOR_KEYS",
            "RECOVERY_28_PILLAR_IDS",
            "VM_COEMULATION_36_STAGE_KEYS",
            "ROUND28_TO_40_SPECS",
            "ROUND28_TO_40_PNG_RECEIPTS",
            "ROUND38_EXPECTED_SCHEMA",
            "ROUND39_EXPECTED_SCHEMA",
            "ROUND40_EXPECTED_SCHEMA",
            "E_ND_ACTUATOR_TX_COUNT",
            "build_realhw_milestone209_master_gate_report",
            "evaluate_milestone209_master_gate",
            "verify_realhw_milestone209_master_gate",
            "render_milestone209_markdown",
        ):
            self.assertTrue(hasattr(fx6_closure, sym), f"Missing export {sym}")
        self.assertIs(evaluate_milestone209_master_gate, build_realhw_milestone209_master_gate_report)

    # --- 2. End-to-End Dual-Mode Happy Path & Performance ---

    def test_04_wall_clock_under_8s_ceiling(self) -> None:
        self.assertLess(self.default_elapsed_s, 8.0)

    def test_05_default_mode_report_green_and_verified(self) -> None:
        rep = self.rep_default
        expected_mode = "CLEAN_ROOM_SYNTHETIC" if _is_forced_clean_room() else "LOCAL_DONOR_O_RDONLY"
        self.assertEqual(rep.verification_mode, expected_mode)
        self.assertTrue(rep.all_pillars_milestone_ready)
        self.assertEqual(rep.status, STATUS_MILESTONE_READY)
        self.assertEqual(rep.passed_pillar_count, 6)
        self.assertEqual(rep.failed_pillar_ids, ())
        self.assertEqual(rep.errors, ())
        v = verify_realhw_milestone209_master_gate(rep)
        self.assertTrue(v.valid, v.errors)

    def test_06_clean_room_synthetic_mode_green_and_deterministic(self) -> None:
        rep1 = self.rep_clean
        self.assertEqual(rep1.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(rep1.all_pillars_milestone_ready)
        v = verify_realhw_milestone209_master_gate(rep1.to_dict())
        self.assertTrue(v.valid, v.errors)
        self.assertEqual(v.expected_milestone209_sha256, rep1.milestone209_sha256)

    def test_07_zero_raw_bytes_repr_and_valid_json_roundtrip(self) -> None:
        rendered = self.rep_default.to_deterministic_json(indent=2)
        self.assertIsNone(re.search(_RAW_BYTES_REPR_REGEX, rendered))
        parsed = json.loads(rendered)
        self.assertTrue(verify_realhw_milestone209_master_gate(parsed).valid)

    def test_08_markdown_rendering_contains_all_6_pillars_and_redlines(self) -> None:
        md = render_milestone209_markdown(self.rep_default)
        self.assertIn("Grand Milestone Phase 209", md)
        self.assertIn(self.rep_default.milestone209_sha256, md)
        self.assertIn("e_nd_actuator_tx_count = 0", md)
        for pid in PILLAR_IDS:
            self.assertIn(f"| `{pid}` |", md)

    def test_09_all_hard_locked_report_fields(self) -> None:
        for rep in (self.rep_default, self.rep_clean):
            self.assertTrue(rep.o_rdonly_enforced)
            self.assertFalse(rep.persistent_emmc_writes_authorized)
            self.assertFalse(rep.persistent_write_release)
            self.assertFalse(rep.spi_nor_write_authorized)
            self.assertFalse(rep.el3_payload_transmit_authorized)
            self.assertFalse(rep.isp_write_authorized)
            self.assertFalse(rep.hardware_live_attachment_authorized)
            self.assertEqual(rep.physical_usb_packets_emitted, 0)
            self.assertEqual(rep.raw_firmware_bytes_leaked, 0)
            self.assertEqual(rep.e_nd_actuator_tx_count, 0)
            self.assertEqual(rep.otp_fuse_touches, 0)
            self.assertEqual(rep.rpmb_counter_increments, 0)
            self.assertEqual(rep.passive_tx_bytes_emitted, 0)
            self.assertEqual(rep.cp_mutation_bytes, 0)
            self.assertEqual(rep.wbi_mutation_bytes, 0)
            self.assertEqual(rep.calibration_mutation_bytes, 0)

    # --- 3. Pillar 1: 72-Gate Hardware Safety Master (`>= 72` Forward-Compat) ---

    def test_10_pillar1_72gate_thresholds_and_g67_to_g72(self) -> None:
        raw_1_off, raw_1_sim = self._unpack_clean_raw()[:2]
        p1 = _evaluate_pillar_1(raw_1_off, raw_1_sim)
        self.assertTrue(p1.passed, p1.errors)
        self.assertGreaterEqual(p1.evidence["total_gates"], 72)
        self.assertGreaterEqual(p1.evidence["offline_verified_gates"], 69)
        self.assertEqual(p1.evidence["simulated_verified_gates"], p1.evidence["total_gates"])
        self.assertFalse(p1.evidence["offline_ready_for_hardware_attach"])
        self.assertFalse(p1.evidence["simulated_ready_for_hardware_attach"])
        self.assertEqual(p1.evidence["g71_e_nd_actuator_tx_count"], 0)
        for gk in ("g67", "g68", "g69", "g70", "g71", "g72"):
            self.assertTrue(p1.evidence["nested_g63_to_g72_valid"].get(gk))

    def test_11_pillar1_forward_compatible_with_74_gates(self) -> None:
        raw_1_off, raw_1_sim = self._unpack_clean_raw()[:2]
        raw_1_off["total_gates"] = 74
        raw_1_off["verified_gates"] = 71
        raw_1_sim["total_gates"] = 74
        raw_1_sim["verified_gates"] = 74
        p1 = _evaluate_pillar_1(raw_1_off, raw_1_sim)
        self.assertTrue(p1.passed, p1.errors)
        self.assertEqual(p1.evidence["total_gates"], 74)

    def test_12_pillar1_fails_when_g71_end_tx_nonzero(self) -> None:
        raw_1_off, raw_1_sim = self._unpack_clean_raw()[:2]
        raw_1_sim["g71_e_nd_actuator_tx_count"] = 1
        p1 = _evaluate_pillar_1(raw_1_off, raw_1_sim)
        self.assertFalse(p1.passed)
        self.assertEqual(p1.status, STATUS_FAIL_CLOSED)

    def test_13_pillar1_fails_when_g69_or_g70_or_g72_nested_invalid(self) -> None:
        for gk in ("g69", "g70", "g71", "g72"):
            raw_1_off, raw_1_sim = self._unpack_clean_raw()[:2]
            raw_1_sim["nested_g63_to_g72_valid"][gk] = False
            p1 = _evaluate_pillar_1(raw_1_off, raw_1_sim)
            self.assertFalse(p1.passed, gk)

    def test_14_pillar1_fails_when_hardware_attach_unlocked(self) -> None:
        raw_1_off, raw_1_sim = self._unpack_clean_raw()[:2]
        raw_1_sim["overall_ready_for_hardware_attach"] = True
        p1 = _evaluate_pillar_1(raw_1_off, raw_1_sim)
        self.assertFalse(p1.passed)

    def test_15_pillar1_fails_when_emmc_or_spinor_or_el3_write_authorized(self) -> None:
        for field_name in (
            "persistent_emmc_writes_authorized",
            "spi_nor_write_authorized",
            "el3_payload_transmit_authorized",
        ):
            raw_1_off, raw_1_sim = self._unpack_clean_raw()[:2]
            raw_1_sim[field_name] = True
            p1 = _evaluate_pillar_1(raw_1_off, raw_1_sim)
            self.assertFalse(p1.passed, field_name)

    def test_16_pillar1_fails_when_usb_packets_or_leaked_bytes_nonzero(self) -> None:
        for field_name in ("physical_usb_packets_emitted", "raw_firmware_bytes_leaked"):
            raw_1_off, raw_1_sim = self._unpack_clean_raw()[:2]
            raw_1_sim[field_name] = 4
            p1 = _evaluate_pillar_1(raw_1_off, raw_1_sim)
            self.assertFalse(p1.passed, field_name)

    # --- 4. Pillar 2: 28-Pillar Recovery & Vault Master (`>= 28` Forward-Compat) ---

    def test_17_pillar2_28pillar_recovery_happy_path(self) -> None:
        raw_28p = self._unpack_clean_raw()[2]
        p2, meta2 = _evaluate_pillar_2(raw_28p, RealHwMilestone209FaultInjection())
        self.assertTrue(p2.passed, p2.errors)
        self.assertGreaterEqual(meta2["recovery_pillar_count"], 28)
        self.assertEqual(meta2["recovery_pillars_passed"], meta2["recovery_pillar_count"])
        self.assertEqual(meta2["otp_fuse_touches"], 0)
        self.assertEqual(meta2["rpmb_counter_increments"], 0)

    def test_18_pillar2_forward_compatible_with_30_pillars(self) -> None:
        raw_28p = self._unpack_clean_raw()[2]
        raw_28p["pillars"] = list(raw_28p["pillars"]) + [
            {"pillar_id": "pillar_29_wave27_future", "passed": True, "errors": []},
            {"pillar_id": "pillar_30_wave27_future", "passed": True, "errors": []},
        ]
        p2, meta2 = _evaluate_pillar_2(raw_28p, RealHwMilestone209FaultInjection())
        self.assertTrue(p2.passed, p2.errors)
        self.assertEqual(meta2["recovery_pillar_count"], 30)

    def test_19_pillar2_fails_when_pillar28a_fan_pwm_or_28b_lut_shutter_fails(self) -> None:
        for subkey in ("pillar28_a_fan_pwm_interlock", "pillar28_b_lut_split_shutter_vault"):
            raw_28p = self._unpack_clean_raw()[2]
            raw_28p[subkey]["passed"] = False
            p2, _ = _evaluate_pillar_2(raw_28p, RealHwMilestone209FaultInjection())
            self.assertFalse(p2.passed, subkey)

    def test_20_pillar2_fails_on_otp_rpmb_tx_usb_or_leak_faults(self) -> None:
        raw_28p = self._unpack_clean_raw()[2]
        for kw in (
            {"p2_otp_fuse_touches_override": 1},
            {"p2_rpmb_increments_override": 1},
            {"p2_passive_tx_bytes_override": 1},
            {"p2_physical_usb_packets_override": 1},
            {"p2_physical_device_writes_override": 1},
            {"p2_raw_firmware_bytes_leaked_override": 8},
        ):
            p2, _ = _evaluate_pillar_2(raw_28p, RealHwMilestone209FaultInjection(**kw))
            self.assertFalse(p2.passed, kw)

    def test_21_pillar2_fails_when_future_pillar29_fails(self) -> None:
        raw_28p = self._unpack_clean_raw()[2]
        raw_28p["pillars"] = list(raw_28p["pillars"]) + [
            {"pillar_id": "pillar_29_broken", "passed": False, "errors": ["broken"]},
        ]
        p2, _ = _evaluate_pillar_2(raw_28p, RealHwMilestone209FaultInjection())
        self.assertFalse(p2.passed)

    # --- 5. Pillar 3: 42-Auditor Binary & Kernel Master (`>= 42` Forward-Compat) ---

    def test_22_pillar3_42_auditors_happy_path(self) -> None:
        auditors = self._unpack_clean_raw()[3]
        p3, meta3 = _evaluate_pillar_3(auditors, RealHwMilestone209FaultInjection())
        self.assertTrue(p3.passed, p3.errors)
        self.assertGreaterEqual(meta3["auditor_count"], 42)
        self.assertEqual(meta3["passed_count"], meta3["auditor_count"])
        self.assertEqual(meta3["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(meta3["e_nd_actuator_tx_count"], 0)

    def test_23_pillar3_forward_compatible_with_44_auditors(self) -> None:
        auditors = self._unpack_clean_raw()[3]
        auditors["wave27_future_43_audit"] = {"all_checks_passed": True, "report_sha256": "a" * 64}
        auditors["wave27_future_44_audit"] = {"all_checks_passed": True, "report_sha256": "b" * 64}
        p3, meta3 = _evaluate_pillar_3(auditors, RealHwMilestone209FaultInjection())
        self.assertTrue(p3.passed, p3.errors)
        self.assertEqual(meta3["auditor_count"], 44)

    def test_24_pillar3_fails_when_auditor41_fan_shutter_lut_mutates_p2(self) -> None:
        auditors = self._unpack_clean_raw()[3]
        p3, _ = _evaluate_pillar_3(
            auditors,
            RealHwMilestone209FaultInjection(p3_fan_shutter_lut_p2_mutation_override=16),
        )
        self.assertFalse(p3.passed)

    def test_25_pillar3_fails_when_auditor42_emits_end_actuator_tx(self) -> None:
        auditors = self._unpack_clean_raw()[3]
        p3, meta3 = _evaluate_pillar_3(
            auditors,
            RealHwMilestone209FaultInjection(p3_big6_camset_vmc_end_tx_override=1),
        )
        self.assertFalse(p3.passed)
        self.assertEqual(meta3["e_nd_actuator_tx_count"], 1)

    def test_26_pillar3_fails_when_raw_firmware_bytes_leaked(self) -> None:
        auditors = self._unpack_clean_raw()[3]
        p3, _ = _evaluate_pillar_3(
            auditors,
            RealHwMilestone209FaultInjection(p3_raw_firmware_bytes_leaked_override=32),
        )
        self.assertFalse(p3.passed)

    def test_27_pillar3_fails_when_forward_compat_auditor_fails(self) -> None:
        auditors = self._unpack_clean_raw()[3]
        auditors["wave27_broken_audit"] = {"all_checks_passed": False}
        p3, _ = _evaluate_pillar_3(auditors, RealHwMilestone209FaultInjection())
        self.assertFalse(p3.passed)

    # --- 6. Pillar 4: 36-Stage VM HIL Co-Emulation (`>= 36` Forward-Compat) ---

    def test_28_pillar4_36_stages_happy_path(self) -> None:
        raw_vm = self._unpack_clean_raw()[4]
        p4, meta4 = _evaluate_pillar_4(raw_vm, RealHwMilestone209FaultInjection())
        self.assertTrue(p4.passed, p4.errors)
        self.assertGreaterEqual(meta4["stage_count"], 36)
        self.assertEqual(meta4["passed_count"], meta4["stage_count"])
        self.assertEqual(meta4["emmc_corruptions"], 0)
        self.assertEqual(meta4["wf12_00342260_hits"], 0)
        self.assertEqual(meta4["e_nd_actuator_tx_count"], 0)

    def test_29_pillar4_forward_compatible_with_38_stages(self) -> None:
        raw_vm = self._unpack_clean_raw()[4]
        raw_vm["stage37_wave27_future_hil"] = {"all_checks_passed": True}
        raw_vm["stage38_wave27_future_hil"] = {"all_checks_passed": True}
        p4, meta4 = _evaluate_pillar_4(raw_vm, RealHwMilestone209FaultInjection())
        self.assertTrue(p4.passed, p4.errors)
        self.assertEqual(meta4["stage_count"], 38)

    def test_30_pillar4_fails_on_stage34_stage35_or_stage36_faults(self) -> None:
        raw_vm = self._unpack_clean_raw()[4]
        for kw in (
            {"p4_stage34_nouvc_or_pd_faults": 1},
            {"p4_stage35_thermal_or_lut_faults": 1},
            {"p4_stage36_end_or_camset_or_vmc_faults": 1},
        ):
            p4, _ = _evaluate_pillar_4(raw_vm, RealHwMilestone209FaultInjection(**kw))
            self.assertFalse(p4.passed, kw)

    def test_31_pillar4_fails_when_stage36_end_tx_or_emmc_mutation_nonzero(self) -> None:
        raw_vm = self._unpack_clean_raw()[4]
        raw_vm["stage36_realhw_big6_noend_camset_slot1_vmcbncm1_hil"]["e_nd_actuator_tx_count"] = 2
        p4, _ = _evaluate_pillar_4(raw_vm, RealHwMilestone209FaultInjection())
        self.assertFalse(p4.passed)

        raw_vm2 = self._unpack_clean_raw()[4]
        raw_vm2["stage35_realhw_fan_pwm_shutter_angle_lut_split_hil"]["emmc_mutation_bytes"] = 512
        p4b, _ = _evaluate_pillar_4(raw_vm2, RealHwMilestone209FaultInjection())
        self.assertFalse(p4b.passed)

    def test_32_pillar4_fails_when_forward_compat_stage37_fails(self) -> None:
        raw_vm = self._unpack_clean_raw()[4]
        raw_vm["stage37_broken_hil"] = {"all_checks_passed": False}
        p4, _ = _evaluate_pillar_4(raw_vm, RealHwMilestone209FaultInjection())
        self.assertFalse(p4.passed)

    # --- 7. Pillar 5: Card-Insert & Bench Cable/Fan/Slot-1 Readiness ---

    def test_33_pillar5_card_insert_and_phase204_happy_path(self) -> None:
        _, _, _, _, _, p136, p143, p154, p186_off, p186_sim, p204_off, p204_sim = self._unpack_clean_raw()
        p5, meta5 = _evaluate_pillar_5(
            p136, p143, p154, p186_off, p186_sim, p204_off, p204_sim, RealHwMilestone209FaultInjection()
        )
        self.assertTrue(p5.passed, p5.errors)
        self.assertEqual(meta5["p204_offline_go_no_go"], GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT)
        self.assertEqual(meta5["p204_sim_go_no_go"], GO_NO_GO_DRY_RUN_SIMULATED_READY)
        self.assertEqual(meta5["p204_sim_groups_passed"], 3)
        self.assertFalse(meta5["p204_hardware_live_attachment_authorized"])
        self.assertEqual(meta5["p204_h0_equals_h3_count"], 16)
        self.assertEqual(meta5["p204_e_nd_actuator_tx_count"], 0)

    def test_34_pillar5_rejects_phase204_bogus_auto1_fan_mode(self) -> None:
        _, _, _, _, _, p136, p143, p154, p186_off, p186_sim, _, _ = self._unpack_clean_raw()
        p204_off, p204_sim = _worker_phase204(
            (str(DEFAULT_FX6_DONOR_LIB_DIR), str(DEFAULT_FX3_MODULES_DIR), True, {"fan_auto1": True})
        )
        p5, _ = _evaluate_pillar_5(
            p136, p143, p154, p186_off, p186_sim, p204_off, p204_sim, RealHwMilestone209FaultInjection()
        )
        self.assertFalse(p5.passed)

    def test_35_pillar5_rejects_phase204_always_off_thermal_block(self) -> None:
        _, _, _, _, _, p136, p143, p154, p186_off, p186_sim, _, _ = self._unpack_clean_raw()
        p204_off, p204_sim = _worker_phase204(
            (str(DEFAULT_FX6_DONOR_LIB_DIR), str(DEFAULT_FX3_MODULES_DIR), True, {"always_off": True})
        )
        p5, _ = _evaluate_pillar_5(
            p136, p143, p154, p186_off, p186_sim, p204_off, p204_sim, RealHwMilestone209FaultInjection()
        )
        self.assertFalse(p5.passed)

    def test_36_pillar5_rejects_phase204_camset_slot2_and_vmc_xlrh1_port(self) -> None:
        _, _, _, _, _, p136, p143, p154, p186_off, p186_sim, _, _ = self._unpack_clean_raw()
        for fdict in ({"camset_slot2": True}, {"vmc_xlrh1_port": True}, {"end_tx": True}, {"h0_h3_drift": True}):
            p204_off, p204_sim = _worker_phase204(
                (str(DEFAULT_FX6_DONOR_LIB_DIR), str(DEFAULT_FX3_MODULES_DIR), True, fdict)
            )
            p5, _ = _evaluate_pillar_5(
                p136, p143, p154, p186_off, p186_sim, p204_off, p204_sim, RealHwMilestone209FaultInjection()
            )
            self.assertFalse(p5.passed, fdict)

    def test_37_pillar5_rejects_phase204_usb_packets_or_unlocked_live_attach(self) -> None:
        _, _, _, _, _, p136, p143, p154, p186_off, p186_sim, p204_off, p204_sim = self._unpack_clean_raw()
        p5, _ = _evaluate_pillar_5(
            p136,
            p143,
            p154,
            p186_off,
            p186_sim,
            p204_off,
            p204_sim,
            RealHwMilestone209FaultInjection(p5_inject_p204_usb_packets_override=2),
        )
        self.assertFalse(p5.passed)

        p204_sim_bad = copy.deepcopy(p204_sim)
        p204_sim_bad["hardware_live_attachment_authorized"] = True
        p5b, _ = _evaluate_pillar_5(
            p136, p143, p154, p186_off, p186_sim, p204_off, p204_sim_bad, RealHwMilestone209FaultInjection()
        )
        self.assertFalse(p5b.passed)

    # --- 8. Pillar 6: Rounds 28..40 (`13/13` Rounds, `39/39` Runs, `26/26` PNGs) ---

    def _clean_p1_to_p5_metas(self):
        r1_off, r1_sim, r28, aud, vm, p136, p143, p154, p186_off, p186_sim, p204_off, p204_sim = (
            self._unpack_clean_raw()
        )
        f = RealHwMilestone209FaultInjection()
        p1 = _evaluate_pillar_1(r1_off, r1_sim)
        _, m2 = _evaluate_pillar_2(r28, f)
        _, m3 = _evaluate_pillar_3(aud, f)
        _, m4 = _evaluate_pillar_4(vm, f)
        _, m5 = _evaluate_pillar_5(p136, p143, p154, p186_off, p186_sim, p204_off, p204_sim, f)
        return p1.evidence, m2, m3, m4, m5

    def test_38_pillar6_rounds_28_to_40_39_runs_and_26_pngs(self) -> None:
        m1, m2, m3, m4, m5 = self._clean_p1_to_p5_metas()
        p6, meta6 = _evaluate_pillar_6(
            repo_root=REPO_ROOT,
            use_clean_room=_is_forced_clean_room(),
            faults=RealHwMilestone209FaultInjection(),
            p1_meta=m1,
            p2_meta=m2,
            p3_meta=m3,
            p4_meta=m4,
            p5_meta=m5,
        )
        self.assertTrue(p6.passed, p6.errors)
        self.assertEqual(meta6["qemu_rounds_verified"], 13)
        self.assertEqual(meta6["qemu_runs_verified"], 39)
        self.assertEqual(meta6["qemu_png_receipts_verified"], 26)
        self.assertGreater(meta6["qemu_png_max_bytes"], 0)
        self.assertLess(meta6["qemu_png_max_bytes"], PNG_MAX_SIZE_BYTES)
        self.assertEqual(meta6["qemu_real_kernel_nop_count"], 0)
        self.assertEqual(meta6["qemu_real_kernel_crashes"], 0)
        self.assertEqual(meta6["qemu_real_kernel_emmc_writes"], 0)
        for rnum in range(28, 41):
            self.assertEqual(meta6["qemu_round_runs_by_round"][f"r{rnum}"], 3)

    def test_39_pillar6_committed_round38_39_40_png_headers_under_28kib(self) -> None:
        for rnum in (38, 39, 40):
            for rel in ROUND28_TO_40_PNG_RECEIPTS[rnum]:
                fpath = REPO_ROOT / rel
                if fpath.is_file():
                    raw = fpath.read_bytes()
                    self.assertTrue(raw.startswith(PNG_MAGIC_BYTES), rel)
                    self.assertLess(len(raw), PNG_MAX_SIZE_BYTES, rel)

    def test_40_pillar6_fails_on_round38_39_40_schema_tamper(self) -> None:
        m1, m2, m3, m4, m5 = self._clean_p1_to_p5_metas()
        for rnum in (38, 39, 40):
            p6, _ = _evaluate_pillar_6(
                repo_root=REPO_ROOT,
                use_clean_room=True,
                faults=RealHwMilestone209FaultInjection(p6_tamper_schema_round_num=rnum),
                p1_meta=m1,
                p2_meta=m2,
                p3_meta=m3,
                p4_meta=m4,
                p5_meta=m5,
            )
            self.assertFalse(p6.passed, f"r{rnum}")

    def test_41_pillar6_fails_on_round40_nop_crash_or_emmc_write(self) -> None:
        m1, m2, m3, m4, m5 = self._clean_p1_to_p5_metas()
        for kw in (
            {"p6_round_nop_override_num": 40, "p6_round_nop_count_override": 1},
            {"p6_round_crash_override_num": 39, "p6_round_crashes_override": 1},
            {"p6_round_emmc_override_num": 38, "p6_round_emmc_writes_override": 1},
        ):
            p6, _ = _evaluate_pillar_6(
                repo_root=REPO_ROOT,
                use_clean_room=True,
                faults=RealHwMilestone209FaultInjection(**kw),
                p1_meta=m1,
                p2_meta=m2,
                p3_meta=m3,
                p4_meta=m4,
                p5_meta=m5,
            )
            self.assertFalse(p6.passed, kw)

    def test_42_pillar6_fails_when_png_receipt_exceeds_28kib_ceiling(self) -> None:
        m1, m2, m3, m4, m5 = self._clean_p1_to_p5_metas()
        p6, _ = _evaluate_pillar_6(
            repo_root=REPO_ROOT,
            use_clean_room=True,
            faults=RealHwMilestone209FaultInjection(
                p6_png_size_override_round_num=40,
                p6_png_size_override_bytes=PNG_MAX_SIZE_BYTES,
            ),
            p1_meta=m1,
            p2_meta=m2,
            p3_meta=m3,
            p4_meta=m4,
            p5_meta=m5,
        )
        self.assertFalse(p6.passed)

    def test_43_pillar6_cross_pillar_end_tx_and_p204_lock_enforcement(self) -> None:
        m1, m2, m3, m4, m5 = self._clean_p1_to_p5_metas()
        m3_bad = dict(m3, e_nd_actuator_tx_count=1)
        p6, _ = _evaluate_pillar_6(
            repo_root=REPO_ROOT,
            use_clean_room=True,
            faults=RealHwMilestone209FaultInjection(),
            p1_meta=m1,
            p2_meta=m2,
            p3_meta=m3_bad,
            p4_meta=m4,
            p5_meta=m5,
        )
        self.assertFalse(p6.passed)

    # --- 9. Tamper-Evident Verifier (`verify_realhw_milestone209_master_gate`) ---

    def test_44_verifier_rejects_non_mapping_payload(self) -> None:
        res = verify_realhw_milestone209_master_gate("invalid")
        self.assertFalse(res.valid)
        self.assertFalse(res.schema_ok)

    def test_45_verifier_rejects_sha256_tamper_and_schema_tamper(self) -> None:
        d = self.rep_clean.to_dict()
        d["milestone209_sha256"] = "0" * 64
        self.assertFalse(verify_realhw_milestone209_master_gate(d).digest_matched)

        d2 = self.rep_clean.to_dict()
        d2["schema_version"] = "wrong_schema"
        d2["milestone209_sha256"] = compute_milestone209_sha256(d2)
        v2 = verify_realhw_milestone209_master_gate(d2)
        self.assertFalse(v2.valid)
        self.assertFalse(v2.schema_ok)

    def test_46_verifier_rejects_redline_tamper_even_when_rehashed(self) -> None:
        for key, bad_val in (
            ("persistent_emmc_writes_authorized", True),
            ("spi_nor_write_authorized", True),
            ("el3_payload_transmit_authorized", True),
            ("hardware_live_attachment_authorized", True),
            ("physical_usb_packets_emitted", 1),
            ("raw_firmware_bytes_leaked", 1),
            ("e_nd_actuator_tx_count", 1),
            ("p204_hardware_live_attachment_authorized", True),
        ):
            d = self.rep_clean.to_dict()
            d[key] = bad_val
            d["milestone209_sha256"] = compute_milestone209_sha256(d)
            res = verify_realhw_milestone209_master_gate(d)
            self.assertFalse(res.valid, key)
            self.assertFalse(res.safety_redlines_ok, key)

    def test_47_verifier_accepts_forward_compatible_wave27_plus_counts(self) -> None:
        d = self.rep_clean.to_dict()
        d["gate72_total_gates"] = 76
        d["gate72_offline_verified"] = 73
        d["gate72_simulated_verified"] = 76
        d["recovery_pillar_count"] = 30
        d["recovery_pillars_passed"] = 30
        d["firmware_lab_auditor_count"] = 45
        d["firmware_lab_auditors_passed"] = 45
        d["vm_coemulation_stage_count"] = 39
        d["vm_coemulation_stages_passed"] = 39
        d["milestone209_sha256"] = compute_milestone209_sha256(d)
        v = verify_realhw_milestone209_master_gate(d)
        self.assertTrue(v.valid, v.errors)

    def test_48_verifier_rejects_raw_bytes_repr_in_payload(self) -> None:
        d = self.rep_clean.to_dict()
        d["pillars"][0]["summary"] = "leaked b'\\x7fELF'"
        d["milestone209_sha256"] = compute_milestone209_sha256(d)
        v = verify_realhw_milestone209_master_gate(d)
        self.assertFalse(v.valid)

    def test_49_verifier_rejects_sub_threshold_gate_pillar_auditor_or_stage_counts(self) -> None:
        for key, val in (
            ("gate72_simulated_verified", 71),
            ("recovery_pillar_count", 27),
            ("firmware_lab_auditor_count", 41),
            ("vm_coemulation_stage_count", 35),
            ("qemu_rounds_verified", 12),
            ("qemu_runs_verified", 38),
            ("qemu_png_receipts_verified", 25),
        ):
            d = self.rep_clean.to_dict()
            d[key] = val
            d["milestone209_sha256"] = compute_milestone209_sha256(d)
            self.assertFalse(verify_realhw_milestone209_master_gate(d).valid, key)

    # --- 10. CLI `verify-milestone-209` Integration (Fast Mocked Builder) ---

    def test_50_cli_verify_milestone_209_summary_and_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            out_json = tmp_path / "m209.json"
            out_md = tmp_path / "m209.md"
            buf = io.StringIO()
            with (
                mock.patch(
                    "fx6_closure.realhw_milestone209_master_gate.build_realhw_milestone209_master_gate_report",
                    return_value=self.rep_clean,
                ),
                mock.patch("sys.stdout", buf),
            ):
                rc = fx6_cli_main(
                    [
                        "verify-milestone-209",
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
            self.assertIn("schema=realhw_milestone209_master_gate_v1", text)
            self.assertIn("qemu=13/13(39/39)", text)
            self.assertIn("pngs=26/26", text)
            self.assertTrue(out_json.is_file())
            self.assertTrue(out_md.is_file())
            self.assertTrue(verify_realhw_milestone209_master_gate(json.loads(out_json.read_text())).valid)

    def test_51_cli_verify_milestone_209_json_stdout(self) -> None:
        buf = io.StringIO()
        with (
            mock.patch(
                "fx6_closure.realhw_milestone209_master_gate.build_realhw_milestone209_master_gate_report",
                return_value=self.rep_clean,
            ),
            mock.patch("sys.stdout", buf),
        ):
            rc = fx6_cli_main(["verify-milestone-209", "--clean-room", "--json"])
        self.assertEqual(rc, 0)
        parsed = json.loads(buf.getvalue())
        self.assertEqual(parsed["schema_version"], REALHW_MILESTONE209_SCHEMA)
        self.assertEqual(parsed["e_nd_actuator_tx_count"], 0)

    def test_52_cli_verify_milestone_209_returns_1_on_failed_report(self) -> None:
        bad_dict = self.rep_clean.to_dict()
        bad_dict["all_pillars_milestone_ready"] = False
        bad_dict["status"] = STATUS_FAIL_CLOSED
        bad_rep = mock.MagicMock()
        bad_rep.all_pillars_milestone_ready = False
        bad_rep.schema_version = REALHW_MILESTONE209_SCHEMA
        bad_rep.verification_mode = "CLEAN_ROOM_SYNTHETIC"
        bad_rep.passed_pillar_count = 5
        bad_rep.pillar_count = 6
        bad_rep.gate72_offline_verified = 68
        bad_rep.gate72_simulated_verified = 71
        bad_rep.recovery_pillars_passed = 28
        bad_rep.recovery_pillar_count = 28
        bad_rep.otp_fuse_touches = 0
        bad_rep.rpmb_counter_increments = 0
        bad_rep.passive_tx_bytes_emitted = 0
        bad_rep.firmware_lab_auditors_passed = 42
        bad_rep.firmware_lab_auditor_count = 42
        bad_rep.vm_coemulation_stages_passed = 36
        bad_rep.vm_coemulation_stage_count = 36
        bad_rep.p136_u4_u5_u6_closed = True
        bad_rep.p143_sd_escape_absent_us = 47
        bad_rep.p143_h0_equals_h3_count = 16
        bad_rep.p143_h0_h3_surface_count = 16
        bad_rep.p154_bench_go = True
        bad_rep.p186_offline_go_no_go = GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT
        bad_rep.p186_sim_go_no_go = GO_NO_GO_DRY_RUN_SIMULATED_READY
        bad_rep.p204_offline_go_no_go = GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT
        bad_rep.p204_sim_go_no_go = GO_NO_GO_DRY_RUN_SIMULATED_READY
        bad_rep.e_nd_actuator_tx_count = 0
        bad_rep.qemu_rounds_verified = 13
        bad_rep.qemu_runs_verified = 39
        bad_rep.qemu_png_receipts_verified = 26
        bad_rep.qemu_png_max_bytes = 27467
        bad_rep.hardware_live_attachment_authorized = False
        bad_rep.persistent_emmc_writes_authorized = False
        bad_rep.spi_nor_write_authorized = False
        bad_rep.el3_payload_transmit_authorized = False
        bad_rep.physical_usb_packets_emitted = 0
        bad_rep.raw_firmware_bytes_leaked = 0
        bad_rep.milestone209_sha256 = "0" * 64
        bad_rep.to_deterministic_json.return_value = json.dumps(bad_dict)
        bad_rep.to_dict.return_value = bad_dict
        buf = io.StringIO()
        with (
            mock.patch(
                "fx6_closure.realhw_milestone209_master_gate.build_realhw_milestone209_master_gate_report",
                return_value=bad_rep,
            ),
            mock.patch("sys.stdout", buf),
        ):
            rc = fx6_cli_main(["verify-milestone-209", "--force-clean-room"])
        self.assertEqual(rc, 1)
        self.assertIn("status=FAILED", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
