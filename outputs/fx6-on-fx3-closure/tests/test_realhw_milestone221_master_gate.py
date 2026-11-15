"""Phase 221 dual-mode unit tests for Grand Milestone Phase 221 6-Pillar Real-Hardware Master Gate."""

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
from fx6_closure.realhw_milestone221_master_gate import (  # noqa: E402
    CALIBRATION_MUTATION_BYTES,
    CP_MUTATION_BYTES,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    EMMC_WRITE_COUNT,
    E_ND_ACTUATOR_TX_COUNT,
    FIRMWARE_LAB_44_AUDITOR_KEYS,
    HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    ISP_WRITE_AUTHORIZED,
    MILESTONE221_SCHEMA_VERSION,
    OTP_FUSE_TOUCHES,
    OTP_FUSE_WRITES,
    P8_CP_MUTATION_FORBIDDEN,
    PASSIVE_TX_BYTES,
    PASSIVE_TX_BYTES_EMITTED,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHASE_221_VERSION,
    PHYSICAL_USB_PACKETS_EMITTED,
    PILLAR_IDS,
    PILLAR_SPECS,
    PNG_MAGIC_BYTES,
    PNG_MAX_SIZE_BYTES,
    RAW_FIRMWARE_BYTES_LEAKED,
    REALHW_MILESTONE221_SCHEMA,
    RECOVERY_31_PILLAR_IDS,
    ROUND28_TO_42_PNG_RECEIPTS,
    ROUND28_TO_42_SPECS,
    ROUND41_EXPECTED_SCHEMA,
    ROUND42_EXPECTED_SCHEMA,
    RPMB_COUNTER_INCREMENTS,
    RPMB_WRITES,
    SPI_NOR_WRITE_AUTHORIZED,
    STATUS_FAIL_CLOSED,
    STATUS_MILESTONE_READY,
    USB_OR_CAMERA_OPERATIONS,
    USB_PACKETS_TRANSMITTED,
    VM_COEMULATION_38_STAGE_KEYS,
    WBI_MUTATION_BYTES,
    WBI_P5_WRITE_AND_HIBERNATION_FORBIDDEN,
    RealHwMilestone221FaultInjection,
    RealHwMilestone221MasterGateReport,
    _collect_parallel_milestone221_results,
    _evaluate_pillar_1,
    _evaluate_pillar_2,
    _evaluate_pillar_3,
    _evaluate_pillar_4,
    _evaluate_pillar_5,
    _evaluate_pillar_6,
    _fault_to_78gate_worker_dict,
    _normalize_31pillar_fault_id,
    _worker_78gate_single,
    _worker_phase216,
    _worker_recovery_31pillar,
    build_realhw_milestone221_master_gate_report,
    compute_milestone221_sha256,
    evaluate_milestone221_master_gate,
    evaluate_realhw_milestone221_master_gate,
    render_milestone221_markdown,
    verify_realhw_milestone221_master_gate,
)

_RAW_BYTES_REPR_REGEX = r"(?<![0-9A-Za-z_/.-])b['\"]"


class TestRealHwMilestone221MasterGate(unittest.TestCase):
    """Comprehensive >= 55 dual-mode tests for Grand Milestone Phase 221 (< 5.0s per mode)."""

    raw_bundle: tuple
    rep_default: RealHwMilestone221MasterGateReport
    rep_clean: RealHwMilestone221MasterGateReport
    default_elapsed_s: float

    @classmethod
    def setUpClass(cls) -> None:
        t0 = time.monotonic()
        cls.rep_default = evaluate_realhw_milestone221_master_gate()
        cls.default_elapsed_s = time.monotonic() - t0
        if _is_forced_clean_room():
            cls.rep_clean = cls.rep_default
        else:
            cls.rep_clean = evaluate_realhw_milestone221_master_gate(force_clean_room=True)
        cls.raw_bundle = _collect_parallel_milestone221_results(
            repo_root=REPO_ROOT,
            fx6_lib_dir=DEFAULT_FX6_DONOR_LIB_DIR,
            fx3_modules_dir=DEFAULT_FX3_MODULES_DIR,
            use_clean_room=True,
            faults=RealHwMilestone221FaultInjection(),
        )

    def _unpack_clean_raw(self):
        return copy.deepcopy(self.raw_bundle)

    # --- 1. Constants, Exports & Schema ---

    def test_01_schema_and_version_constants(self) -> None:
        self.assertEqual(REALHW_MILESTONE221_SCHEMA, "realhw_milestone221_master_gate_v1")
        self.assertEqual(MILESTONE221_SCHEMA_VERSION, REALHW_MILESTONE221_SCHEMA)
        self.assertEqual(PHASE_221_VERSION, "221.0.0")
        self.assertEqual(PILLAR_IDS, ("P1", "P2", "P3", "P4", "P5", "P6"))
        self.assertEqual(len(PILLAR_SPECS), 6)
        self.assertEqual(len(RECOVERY_31_PILLAR_IDS), 31)
        self.assertEqual(len(FIRMWARE_LAB_44_AUDITOR_KEYS), 44)
        self.assertEqual(len(VM_COEMULATION_38_STAGE_KEYS), 38)
        self.assertEqual(len(ROUND28_TO_42_SPECS), 15)
        self.assertEqual(len(ROUND28_TO_42_PNG_RECEIPTS), 15)

    def test_02_hard_locked_zero_write_constants(self) -> None:
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(PERSISTENT_WRITE_RELEASE)
        self.assertFalse(SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        self.assertFalse(ISP_WRITE_AUTHORIZED)
        self.assertFalse(HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        self.assertTrue(P8_CP_MUTATION_FORBIDDEN)
        self.assertTrue(WBI_P5_WRITE_AND_HIBERNATION_FORBIDDEN)
        self.assertEqual(USB_PACKETS_TRANSMITTED, 0)
        self.assertEqual(PHYSICAL_USB_PACKETS_EMITTED, 0)
        self.assertEqual(RAW_FIRMWARE_BYTES_LEAKED, 0)
        self.assertEqual(E_ND_ACTUATOR_TX_COUNT, 0)
        self.assertEqual(EMMC_WRITE_COUNT, 0)
        self.assertEqual(OTP_FUSE_WRITES, 0)
        self.assertEqual(OTP_FUSE_TOUCHES, 0)
        self.assertEqual(RPMB_WRITES, 0)
        self.assertEqual(RPMB_COUNTER_INCREMENTS, 0)
        self.assertEqual(PASSIVE_TX_BYTES, 0)
        self.assertEqual(PASSIVE_TX_BYTES_EMITTED, 0)
        self.assertEqual(CP_MUTATION_BYTES, 0)
        self.assertEqual(WBI_MUTATION_BYTES, 0)
        self.assertEqual(CALIBRATION_MUTATION_BYTES, 0)
        self.assertEqual(USB_OR_CAMERA_OPERATIONS, 0)

    def test_03_package_top_level_exports(self) -> None:
        for sym in (
            "REALHW_MILESTONE221_SCHEMA",
            "MILESTONE221_SCHEMA_VERSION",
            "PHASE_221_VERSION",
            "MILESTONE221_PILLAR_IDS",
            "FIRMWARE_LAB_44_AUDITOR_KEYS",
            "RECOVERY_31_PILLAR_IDS",
            "VM_COEMULATION_38_STAGE_KEYS",
            "ROUND28_TO_42_SPECS",
            "ROUND28_TO_42_PNG_RECEIPTS",
            "ROUND41_EXPECTED_SCHEMA",
            "ROUND42_EXPECTED_SCHEMA",
            "evaluate_realhw_milestone221_master_gate",
            "build_realhw_milestone221_master_gate_report",
            "evaluate_milestone221_master_gate",
            "verify_realhw_milestone221_master_gate",
            "render_milestone221_markdown",
        ):
            self.assertTrue(hasattr(fx6_closure, sym), f"Missing export {sym}")
        self.assertIs(build_realhw_milestone221_master_gate_report, evaluate_realhw_milestone221_master_gate)
        self.assertIs(evaluate_milestone221_master_gate, evaluate_realhw_milestone221_master_gate)

    # --- 2. End-to-End Dual-Mode Happy Path & Performance ---

    def test_04_wall_clock_under_5s_budget(self) -> None:
        self.assertLess(self.default_elapsed_s, 5.0)

    def test_05_default_mode_report_green_and_verified(self) -> None:
        rep = self.rep_default
        expected_mode = "CLEAN_ROOM_SYNTHETIC" if _is_forced_clean_room() else "LOCAL_DONOR_O_RDONLY"
        self.assertEqual(rep.schema, REALHW_MILESTONE221_SCHEMA)
        self.assertEqual(rep.schema_version, REALHW_MILESTONE221_SCHEMA)
        self.assertEqual(rep.verification_mode, expected_mode)
        self.assertTrue(rep.all_pillars_milestone_ready)
        self.assertEqual(rep.status, STATUS_MILESTONE_READY)
        self.assertEqual(rep.passed_pillar_count, 6)
        self.assertEqual(rep.failed_pillar_ids, ())
        self.assertEqual(rep.errors, ())
        v = verify_realhw_milestone221_master_gate(rep)
        self.assertTrue(v.valid, v.errors)

    def test_06_clean_room_synthetic_mode_green_and_deterministic(self) -> None:
        rep1 = self.rep_clean
        self.assertEqual(rep1.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(rep1.all_pillars_milestone_ready)
        v = verify_realhw_milestone221_master_gate(rep1.to_dict())
        self.assertTrue(v.valid, v.errors)
        self.assertEqual(v.expected_milestone221_sha256, rep1.milestone221_sha256)

    def test_07_zero_raw_bytes_repr_and_valid_json_roundtrip(self) -> None:
        rendered = self.rep_default.to_deterministic_json(indent=2)
        self.assertIsNone(re.search(_RAW_BYTES_REPR_REGEX, rendered))
        parsed = json.loads(rendered)
        self.assertEqual(parsed["schema"], "realhw_milestone221_master_gate_v1")
        self.assertTrue(verify_realhw_milestone221_master_gate(parsed).valid)

    def test_08_markdown_rendering_contains_all_6_pillars_and_redlines(self) -> None:
        md = render_milestone221_markdown(self.rep_default)
        self.assertIn("Grand Milestone Phase 221", md)
        self.assertIn(self.rep_default.milestone221_sha256, md)
        self.assertIn("e_nd_actuator_tx_count = 0", md)
        self.assertIn("usb_packets_transmitted = 0", md)
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
            self.assertEqual(rep.usb_packets_transmitted, 0)
            self.assertEqual(rep.physical_usb_packets_emitted, 0)
            self.assertEqual(rep.raw_firmware_bytes_leaked, 0)
            self.assertEqual(rep.e_nd_actuator_tx_count, 0)
            self.assertEqual(rep.emmc_write_count, 0)
            self.assertEqual(rep.otp_fuse_writes, 0)
            self.assertEqual(rep.otp_fuse_touches, 0)
            self.assertEqual(rep.rpmb_writes, 0)
            self.assertEqual(rep.rpmb_counter_increments, 0)
            self.assertEqual(rep.passive_tx_bytes, 0)
            self.assertEqual(rep.passive_tx_bytes_emitted, 0)
            self.assertEqual(rep.cp_mutation_bytes, 0)
            self.assertEqual(rep.wbi_mutation_bytes, 0)
            self.assertEqual(rep.calibration_mutation_bytes, 0)
            self.assertEqual(rep.h0_equals_h3_count, 16)

    # --- 3. Pillar 1: 78-Gate Hardware Safety Master (`75/78` Offline, `78/78` Sim) ---

    def test_10_pillar1_78gate_thresholds_and_g73_to_g78(self) -> None:
        raw_1_off, raw_1_sim = self._unpack_clean_raw()[:2]
        p1 = _evaluate_pillar_1(raw_1_off, raw_1_sim)
        self.assertTrue(p1.passed, p1.errors)
        self.assertGreaterEqual(p1.evidence["offline_total_gates"], 78)
        self.assertGreaterEqual(p1.evidence["offline_verified_gates"], 75)
        self.assertEqual(
            p1.evidence["offline_verified_gates"],
            p1.evidence["offline_total_gates"] - 3,
        )
        self.assertEqual(
            p1.evidence["simulated_verified_gates"],
            p1.evidence["simulated_total_gates"],
        )
        self.assertFalse(p1.evidence["offline_ready_for_hardware_attach"])
        self.assertFalse(p1.evidence["simulated_ready_for_hardware_attach"])
        self.assertFalse(p1.evidence["hardware_live_attachment_authorized"])
        self.assertEqual(p1.evidence["g71_e_nd_actuator_tx_count"], 0)
        for gk in ("g73", "g74", "g75", "g76", "g77", "g78"):
            self.assertTrue(p1.evidence["g63_to_g78_valid"].get(gk), gk)

    def test_11_pillar1_forward_compatible_with_80_gates(self) -> None:
        raw_1_off, raw_1_sim = self._unpack_clean_raw()[:2]
        raw_1_off["total_gates"] = 80
        raw_1_off["verified_gates"] = 77
        raw_1_sim["total_gates"] = 80
        raw_1_sim["verified_gates"] = 80
        p1 = _evaluate_pillar_1(raw_1_off, raw_1_sim)
        self.assertTrue(p1.passed, p1.errors)
        self.assertEqual(p1.evidence["simulated_total_gates"], 80)

    def test_12_pillar1_live_fault_g73_desqueeze_165x_and_focusmap(self) -> None:
        raw_1_off, _ = self._unpack_clean_raw()[:2]
        f = RealHwMilestone221FaultInjection(
            p1_desqueeze_focusmap_kwargs={
                "desqueeze_menu_option": "1.6x",
                "effective_horizontal_factor": 1.60,
                "in_body_fx3_focus_map_menu_claimed": True,
            }
        )
        raw_1_sim = _worker_78gate_single(
            (str(REPO_ROOT), True, True, _fault_to_78gate_worker_dict(f))
        )
        p1 = _evaluate_pillar_1(raw_1_off, raw_1_sim)
        self.assertFalse(p1.passed)
        self.assertFalse(raw_1_sim["nested_g_valid"]["g73"])

    def test_13_pillar1_live_fault_g74_simult_autoswitch_and_shockless_wb(self) -> None:
        raw_1_off, _ = self._unpack_clean_raw()[:2]
        f = RealHwMilestone221FaultInjection(
            p1_simult_autoswitch_shocklesswb_kwargs={
                "rec_media_mode": "SIMULT",
                "auto_switch_media": True,
                "strict_dual_vault_parity_required": True,
                "observed_wb_ramp_frames": 8,
                "wb_operation_type": "KELVIN_CHANGE",
            }
        )
        raw_1_sim = _worker_78gate_single(
            (str(REPO_ROOT), True, True, _fault_to_78gate_worker_dict(f))
        )
        p1 = _evaluate_pillar_1(raw_1_off, raw_1_sim)
        self.assertFalse(p1.passed)
        self.assertFalse(raw_1_sim["nested_g_valid"]["g74"])

    def test_14_pillar1_live_fault_g75_hdmi_log1080_vs_hdmionly_4k(self) -> None:
        raw_1_off, _ = self._unpack_clean_raw()[:2]
        f = RealHwMilestone221FaultInjection(
            p1_hdmi_log1080_hdmionly_kwargs={
                "simultaneous_internal_rec_and_nonraw_4k_log_hdmi_claimed": True,
            }
        )
        raw_1_sim = _worker_78gate_single(
            (str(REPO_ROOT), True, True, _fault_to_78gate_worker_dict(f))
        )
        p1 = _evaluate_pillar_1(raw_1_off, raw_1_sim)
        self.assertFalse(p1.passed)
        self.assertFalse(raw_1_sim["nested_g_valid"]["g75"])

    def test_15_pillar1_live_fault_g76_proxy_vault_and_focusmag_brightmon(self) -> None:
        raw_1_off, _ = self._unpack_clean_raw()[:2]
        f = RealHwMilestone221FaultInjection(
            p1_proxy_focusmag_brightmon_kwargs={
                "uncoupled_single_side_incamera_op_attempted": True,
            }
        )
        raw_1_sim = _worker_78gate_single(
            (str(REPO_ROOT), True, True, _fault_to_78gate_worker_dict(f))
        )
        p1 = _evaluate_pillar_1(raw_1_off, raw_1_sim)
        self.assertFalse(p1.passed)
        self.assertFalse(raw_1_sim["nested_g_valid"]["g76"])

    def test_16_pillar1_live_fault_g77_filesettings_37char_limit(self) -> None:
        raw_1_off, _ = self._unpack_clean_raw()[:2]
        f = RealHwMilestone221FaultInjection(
            p1_filesettings_shotmark_kwargs={"title_name": "A" * 40}
        )
        raw_1_sim = _worker_78gate_single(
            (str(REPO_ROOT), True, True, _fault_to_78gate_worker_dict(f))
        )
        p1 = _evaluate_pillar_1(raw_1_off, raw_1_sim)
        self.assertFalse(p1.passed)
        self.assertFalse(raw_1_sim["nested_g_valid"]["g77"])

    def test_17_pillar1_live_fault_g78_tcregen_slot2_violation(self) -> None:
        raw_1_off, _ = self._unpack_clean_raw()[:2]
        f = RealHwMilestone221FaultInjection(
            p1_tcregen_reclamp_kwargs={
                "time_code_make": "REGENERATE",
                "regenerate_reference_slot": "SLOT_2",
            }
        )
        raw_1_sim = _worker_78gate_single(
            (str(REPO_ROOT), True, True, _fault_to_78gate_worker_dict(f))
        )
        p1 = _evaluate_pillar_1(raw_1_off, raw_1_sim)
        self.assertFalse(p1.passed)
        self.assertFalse(raw_1_sim["nested_g_valid"]["g78"])

    def test_18_pillar1_fails_on_persistent_write_request_or_redline_tamper(self) -> None:
        raw_1_off, _ = self._unpack_clean_raw()[:2]
        f = RealHwMilestone221FaultInjection(p1_request_persistent_writes=True)
        raw_1_sim = _worker_78gate_single(
            (str(REPO_ROOT), True, True, _fault_to_78gate_worker_dict(f))
        )
        self.assertFalse(_evaluate_pillar_1(raw_1_off, raw_1_sim).passed)

        for field_name, bad_val in (
            ("overall_ready_for_hardware_attach", True),
            ("hardware_live_attachment_authorized", True),
            ("persistent_emmc_writes_authorized", True),
            ("spi_nor_write_authorized", True),
            ("el3_payload_transmit_authorized", True),
            ("usb_packets_transmitted", 1),
            ("raw_firmware_bytes_leaked", 4),
            ("g71_e_nd_actuator_tx_count", 1),
        ):
            r_off, r_sim = self._unpack_clean_raw()[:2]
            r_sim[field_name] = bad_val
            self.assertFalse(_evaluate_pillar_1(r_off, r_sim).passed, field_name)

    # --- 4. Pillar 2: 31-Pillar Recovery Master (`VERIFIED_31OF31_PILLAR_RECOVERY_MASTER`) ---

    def test_19_pillar2_31pillar_recovery_happy_path(self) -> None:
        raw_31p = self._unpack_clean_raw()[2]
        p2, meta2 = _evaluate_pillar_2(raw_31p, RealHwMilestone221FaultInjection())
        self.assertTrue(p2.passed, p2.errors)
        self.assertEqual(meta2["recovery_status"], "VERIFIED_31OF31_PILLAR_RECOVERY_MASTER")
        self.assertGreaterEqual(meta2["recovery_pillar_count"], 31)
        self.assertEqual(meta2["recovery_pillars_passed"], meta2["recovery_pillar_count"])
        self.assertEqual(meta2["otp_fuse_writes"], 0)
        self.assertEqual(meta2["rpmb_writes"], 0)
        self.assertEqual(meta2["passive_tx_bytes"], 0)

    def test_20_pillar2_normalize_shorthand_and_live_fault_pillars_29_30_31(self) -> None:
        self.assertEqual(_normalize_31pillar_fault_id("pillar_29"), RECOVERY_31_PILLAR_IDS[28])
        self.assertEqual(_normalize_31pillar_fault_id("pillar_30"), RECOVERY_31_PILLAR_IDS[29])
        self.assertEqual(_normalize_31pillar_fault_id("pillar_31"), RECOVERY_31_PILLAR_IDS[30])
        for pid in ("pillar_29", "pillar_30", "pillar_31"):
            raw_bad = _worker_recovery_31pillar((True, pid))
            p2, _ = _evaluate_pillar_2(raw_bad, RealHwMilestone221FaultInjection())
            self.assertFalse(p2.passed, pid)
            self.assertEqual(p2.status, STATUS_FAIL_CLOSED)

    def test_21_pillar2_forward_compatible_with_32_pillars(self) -> None:
        raw_31p = self._unpack_clean_raw()[2]
        raw_31p["pillar_count"] = 32
        raw_31p["pillars_passed"] = 32
        raw_31p["status"] = "VERIFIED_32OF32_PILLAR_RECOVERY_MASTER"
        p2, meta2 = _evaluate_pillar_2(raw_31p, RealHwMilestone221FaultInjection())
        self.assertTrue(p2.passed, p2.errors)
        self.assertEqual(meta2["recovery_pillar_count"], 32)

    def test_22_pillar2_fails_when_pillar31a_or_31b_subvault_fails(self) -> None:
        for subkey in (
            "pillar31_a_filesettings_shotmark_vault",
            "pillar31_b_tcregen_slot1_extlk_vault",
        ):
            raw_31p = self._unpack_clean_raw()[2]
            raw_31p[subkey]["passed"] = False
            p2, _ = _evaluate_pillar_2(raw_31p, RealHwMilestone221FaultInjection())
            self.assertFalse(p2.passed, subkey)

    def test_23_pillar2_fails_on_otp_rpmb_passive_tx_usb_or_leak_overrides(self) -> None:
        raw_31p = self._unpack_clean_raw()[2]
        for kw in (
            {"p2_otp_fuse_writes_override": 1},
            {"p2_rpmb_writes_override": 1},
            {"p2_passive_tx_bytes_override": 1},
            {"p2_physical_usb_packets_override": 1},
            {"p2_physical_device_writes_override": 1},
            {"p2_raw_firmware_bytes_leaked_override": 8},
        ):
            p2, _ = _evaluate_pillar_2(raw_31p, RealHwMilestone221FaultInjection(**kw))
            self.assertFalse(p2.passed, kw)

    # --- 5. Pillar 3: Firmware Lab Auditors (`44/44+` Forward-Compatible) ---

    def test_24_pillar3_44_auditors_happy_path_including_43_and_44(self) -> None:
        auditors = self._unpack_clean_raw()[3]
        p3, meta3 = _evaluate_pillar_3(auditors, RealHwMilestone221FaultInjection())
        self.assertTrue(p3.passed, p3.errors)
        self.assertGreaterEqual(meta3["auditor_count"], 44)
        self.assertEqual(meta3["passed_count"], meta3["auditor_count"])
        self.assertEqual(meta3["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(meta3["e_nd_actuator_tx_count"], 0)
        self.assertTrue(
            p3.evidence["auditor_statuses"][
                "realhw_desqueeze_165x_focusmap_simult_and_shocklesswb_audit"
            ]
        )
        self.assertTrue(
            p3.evidence["auditor_statuses"][
                "realhw_hdmi_log1080_proxy_vault_and_focusmag_brightmon_audit"
            ]
        )

    def test_25_pillar3_forward_compatible_with_45_and_46_auditors(self) -> None:
        auditors = self._unpack_clean_raw()[3]
        auditors["realhw_future_wave29_45_audit"] = {
            "all_checks_passed": True,
            "report_sha256": "a" * 64,
        }
        auditors["realhw_future_wave30_46_audit"] = {
            "all_checks_passed": True,
            "report_sha256": "b" * 64,
        }
        p3, meta3 = _evaluate_pillar_3(auditors, RealHwMilestone221FaultInjection())
        self.assertTrue(p3.passed, p3.errors)
        self.assertGreaterEqual(meta3["auditor_count"], 46)
        self.assertEqual(meta3["passed_count"], meta3["auditor_count"])

    def test_26_pillar3_fails_when_future_45th_auditor_fails(self) -> None:
        auditors = self._unpack_clean_raw()[3]
        auditors["realhw_future_wave29_broken_audit"] = {"all_checks_passed": False}
        p3, _ = _evaluate_pillar_3(auditors, RealHwMilestone221FaultInjection())
        self.assertFalse(p3.passed)
        self.assertEqual(p3.status, STATUS_FAIL_CLOSED)

    def test_27_pillar3_fails_on_auditor43_desqueeze_focusmap_overlay_fault(self) -> None:
        auditors = self._unpack_clean_raw()[3]
        p3, _ = _evaluate_pillar_3(
            auditors,
            RealHwMilestone221FaultInjection(p3_desqueeze_focusmap_overlay_fault=True),
        )
        self.assertFalse(p3.passed)

    def test_28_pillar3_fails_on_auditor44_hdmi_proxy_focusmag_guard_fault(self) -> None:
        auditors = self._unpack_clean_raw()[3]
        p3, _ = _evaluate_pillar_3(
            auditors,
            RealHwMilestone221FaultInjection(p3_hdmi_proxy_focusmag_guard_fault=True),
        )
        self.assertFalse(p3.passed)

    def test_29_pillar3_fails_when_raw_firmware_bytes_leaked(self) -> None:
        auditors = self._unpack_clean_raw()[3]
        p3, _ = _evaluate_pillar_3(
            auditors,
            RealHwMilestone221FaultInjection(p3_raw_firmware_bytes_leaked_override=16),
        )
        self.assertFalse(p3.passed)

    # --- 6. Pillar 4: VM HIL Co-Emulation (`38/38+` Forward-Compatible) ---

    def test_30_pillar4_38_stages_happy_path_including_37_and_38(self) -> None:
        raw_vm = self._unpack_clean_raw()[4]
        p4, meta4 = _evaluate_pillar_4(raw_vm, RealHwMilestone221FaultInjection())
        self.assertTrue(p4.passed, p4.errors)
        self.assertGreaterEqual(meta4["stage_count"], 38)
        self.assertEqual(meta4["passed_count"], meta4["stage_count"])
        self.assertEqual(meta4["emmc_corruptions"], 0)
        self.assertEqual(meta4["wf12_00342260_hits"], 0)
        self.assertEqual(meta4["e_nd_actuator_tx_count"], 0)
        self.assertTrue(
            p4.evidence["stage_statuses"][
                "stage37_realhw_desqueeze_165x_focusmap_simult_shocklesswb_hil"
            ]
        )
        self.assertTrue(
            p4.evidence["stage_statuses"][
                "stage38_realhw_hdmi_log1080_proxy_vault_focusmag_brightmon_hil"
            ]
        )

    def test_31_pillar4_forward_compatible_with_stage39_and_stage40(self) -> None:
        raw_vm = self._unpack_clean_raw()[4]
        raw_vm["stage39_realhw_future_wave29_hil"] = {"all_checks_passed": True}
        raw_vm["stage40_realhw_future_wave30_hil"] = {"all_checks_passed": True}
        p4, meta4 = _evaluate_pillar_4(raw_vm, RealHwMilestone221FaultInjection())
        self.assertTrue(p4.passed, p4.errors)
        self.assertGreaterEqual(meta4["stage_count"], 40)
        self.assertEqual(meta4["passed_count"], meta4["stage_count"])

    def test_32_pillar4_fails_when_future_stage39_fails(self) -> None:
        raw_vm = self._unpack_clean_raw()[4]
        raw_vm["stage39_realhw_broken_hil"] = {"all_checks_passed": False}
        p4, _ = _evaluate_pillar_4(raw_vm, RealHwMilestone221FaultInjection())
        self.assertFalse(p4.passed)

    def test_33_pillar4_fails_on_stage37_or_stage38_fault_injections(self) -> None:
        raw_vm = self._unpack_clean_raw()[4]
        for kw in (
            {"p4_stage37_desqueeze_or_focusmap_faults": 1},
            {"p4_stage38_hdmi_or_proxy_or_focusmag_faults": 1},
        ):
            p4, _ = _evaluate_pillar_4(raw_vm, RealHwMilestone221FaultInjection(**kw))
            self.assertFalse(p4.passed, kw)

    def test_34_pillar4_fails_on_stage37_or_38_emmc_mutation_or_wf12_hit(self) -> None:
        raw_vm = self._unpack_clean_raw()[4]
        raw_vm["stage37_realhw_desqueeze_165x_focusmap_simult_shocklesswb_hil"][
            "emmc_mutation_bytes"
        ] = 64
        self.assertFalse(_evaluate_pillar_4(raw_vm, RealHwMilestone221FaultInjection())[0].passed)

        raw_vm2 = self._unpack_clean_raw()[4]
        raw_vm2["stage38_realhw_hdmi_log1080_proxy_vault_focusmag_brightmon_hil"][
            "wf12_00342260_hits"
        ] = 1
        self.assertFalse(_evaluate_pillar_4(raw_vm2, RealHwMilestone221FaultInjection())[0].passed)

    # --- 7. Pillar 5: Triple Bench Readiness Preflights (`Ph186` + `Ph204` + `Ph216`) ---

    def test_35_pillar5_triple_bench_preflights_happy_path(self) -> None:
        (
            _,
            _,
            _,
            _,
            _,
            p136,
            p143,
            p154,
            p186_off,
            p186_sim,
            p204_off,
            p204_sim,
            p216_off,
            p216_sim,
        ) = self._unpack_clean_raw()
        p5, meta5 = _evaluate_pillar_5(
            p136,
            p143,
            p154,
            p186_off,
            p186_sim,
            p204_off,
            p204_sim,
            p216_off,
            p216_sim,
            RealHwMilestone221FaultInjection(),
        )
        self.assertTrue(p5.passed, p5.errors)
        for prefix in ("p186", "p204", "p216"):
            self.assertEqual(
                meta5[f"{prefix}_offline_go_no_go"],
                GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT,
                prefix,
            )
            self.assertEqual(
                meta5[f"{prefix}_sim_go_no_go"],
                GO_NO_GO_DRY_RUN_SIMULATED_READY,
                prefix,
            )
        self.assertEqual(meta5["p186_sim_gates_passed"], 4)
        self.assertEqual(meta5["p204_sim_groups_passed"], 3)
        self.assertEqual(meta5["p216_sim_checklists_passed"], 5)
        self.assertFalse(meta5["p186_card_insert_authorized"])
        self.assertFalse(meta5["p204_hardware_live_attachment_authorized"])
        self.assertFalse(meta5["p216_hardware_live_attachment_authorized"])
        self.assertEqual(meta5["p216_h0_equals_h3_count"], 16)

    def test_36_pillar5_rejects_phase216_desqueeze_lock_and_hdmi_only_card_rec(self) -> None:
        (
            _,
            _,
            _,
            _,
            _,
            p136,
            p143,
            p154,
            p186_off,
            p186_sim,
            p204_off,
            p204_sim,
            _,
            _,
        ) = self._unpack_clean_raw()
        for fdict in ({"desqueeze_lock": True}, {"hdmi_only_card_rec": True}):
            p216_off, p216_sim = _worker_phase216(
                (str(DEFAULT_FX6_DONOR_LIB_DIR), str(DEFAULT_FX3_MODULES_DIR), True, fdict)
            )
            p5, _ = _evaluate_pillar_5(
                p136,
                p143,
                p154,
                p186_off,
                p186_sim,
                p204_off,
                p204_sim,
                p216_off,
                p216_sim,
                RealHwMilestone221FaultInjection(),
            )
            self.assertFalse(p5.passed, fdict)

    def test_37_pillar5_rejects_phase216_proxy_orphan_title38_and_h0_h3_drift(self) -> None:
        (
            _,
            _,
            _,
            _,
            _,
            p136,
            p143,
            p154,
            p186_off,
            p186_sim,
            p204_off,
            p204_sim,
            _,
            _,
        ) = self._unpack_clean_raw()
        for fdict in ({"proxy_orphan": True}, {"title_38char": True}, {"h0_h3_drift": True}):
            p216_off, p216_sim = _worker_phase216(
                (str(DEFAULT_FX6_DONOR_LIB_DIR), str(DEFAULT_FX3_MODULES_DIR), True, fdict)
            )
            p5, _ = _evaluate_pillar_5(
                p136,
                p143,
                p154,
                p186_off,
                p186_sim,
                p204_off,
                p204_sim,
                p216_off,
                p216_sim,
                RealHwMilestone221FaultInjection(),
            )
            self.assertFalse(p5.passed, fdict)

    def test_38_pillar5_rejects_phase216_usb_packets_or_unlocked_live_attach(self) -> None:
        (
            _,
            _,
            _,
            _,
            _,
            p136,
            p143,
            p154,
            p186_off,
            p186_sim,
            p204_off,
            p204_sim,
            p216_off,
            p216_sim,
        ) = self._unpack_clean_raw()
        p5, _ = _evaluate_pillar_5(
            p136,
            p143,
            p154,
            p186_off,
            p186_sim,
            p204_off,
            p204_sim,
            p216_off,
            p216_sim,
            RealHwMilestone221FaultInjection(p5_inject_p216_usb_packets_override=2),
        )
        self.assertFalse(p5.passed)

        p216_sim_bad = copy.deepcopy(p216_sim)
        p216_sim_bad["hardware_live_attachment_authorized"] = True
        p5b, _ = _evaluate_pillar_5(
            p136,
            p143,
            p154,
            p186_off,
            p186_sim,
            p204_off,
            p204_sim,
            p216_off,
            p216_sim_bad,
            RealHwMilestone221FaultInjection(),
        )
        self.assertFalse(p5b.passed)

    def test_39_pillar5_rejects_phase216_offline_if_not_blocked_awaiting_tier0(self) -> None:
        (
            _,
            _,
            _,
            _,
            _,
            p136,
            p143,
            p154,
            p186_off,
            p186_sim,
            p204_off,
            p204_sim,
            p216_off,
            p216_sim,
        ) = self._unpack_clean_raw()
        p216_off_bad = copy.deepcopy(p216_off)
        p216_off_bad["go_no_go"] = GO_NO_GO_DRY_RUN_SIMULATED_READY
        p5, _ = _evaluate_pillar_5(
            p136,
            p143,
            p154,
            p186_off,
            p186_sim,
            p204_off,
            p204_sim,
            p216_off_bad,
            p216_sim,
            RealHwMilestone221FaultInjection(),
        )
        self.assertFalse(p5.passed)

    # --- 8. Pillar 6: Rounds 28..42 (`15/15` Rounds, `45/45` Runs, `30/30` PNGs) ---

    def _clean_p1_to_p5_metas(self):
        (
            r1_off,
            r1_sim,
            r31,
            aud,
            vm,
            p136,
            p143,
            p154,
            p186_off,
            p186_sim,
            p204_off,
            p204_sim,
            p216_off,
            p216_sim,
        ) = self._unpack_clean_raw()
        f = RealHwMilestone221FaultInjection()
        p1 = _evaluate_pillar_1(r1_off, r1_sim)
        _, m2 = _evaluate_pillar_2(r31, f)
        _, m3 = _evaluate_pillar_3(aud, f)
        _, m4 = _evaluate_pillar_4(vm, f)
        _, m5 = _evaluate_pillar_5(
            p136, p143, p154, p186_off, p186_sim, p204_off, p204_sim, p216_off, p216_sim, f
        )
        return p1.evidence, m2, m3, m4, m5

    def test_40_pillar6_rounds_28_to_42_45_runs_and_30_pngs(self) -> None:
        m1, m2, m3, m4, m5 = self._clean_p1_to_p5_metas()
        p6, meta6 = _evaluate_pillar_6(
            repo_root=REPO_ROOT,
            use_clean_room=_is_forced_clean_room(),
            faults=RealHwMilestone221FaultInjection(),
            p1_meta=m1,
            p2_meta=m2,
            p3_meta=m3,
            p4_meta=m4,
            p5_meta=m5,
        )
        self.assertTrue(p6.passed, p6.errors)
        self.assertEqual(meta6["qemu_rounds_verified"], 15)
        self.assertEqual(meta6["qemu_runs_verified"], 45)
        self.assertEqual(meta6["qemu_png_receipts_verified"], 30)
        self.assertGreater(meta6["qemu_png_max_bytes"], 0)
        self.assertLess(meta6["qemu_png_max_bytes"], PNG_MAX_SIZE_BYTES)
        self.assertEqual(meta6["qemu_real_kernel_nop_count"], 0)
        self.assertEqual(meta6["qemu_real_kernel_crashes"], 0)
        self.assertEqual(meta6["qemu_real_kernel_emmc_writes"], 0)
        self.assertEqual(p6.evidence["h0_equals_h3_count"], 16)
        self.assertEqual(p6.evidence["emmc_write_count"], 0)
        self.assertEqual(p6.evidence["e_nd_actuator_tx_count"], 0)
        for rnum in range(28, 43):
            self.assertEqual(meta6["qemu_round_runs_by_round"][f"r{rnum}"], 3)

    def test_41_pillar6_committed_round41_and_42_png_headers_under_28kib(self) -> None:
        for rnum in (41, 42):
            for rel in ROUND28_TO_42_PNG_RECEIPTS[rnum]:
                fpath = REPO_ROOT / rel
                if fpath.is_file():
                    raw = fpath.read_bytes()
                    self.assertTrue(raw.startswith(PNG_MAGIC_BYTES), rel)
                    self.assertLess(len(raw), PNG_MAX_SIZE_BYTES, rel)

    def test_42_pillar6_fails_on_round41_and_42_schema_tamper(self) -> None:
        m1, m2, m3, m4, m5 = self._clean_p1_to_p5_metas()
        for rnum in (41, 42):
            p6, _ = _evaluate_pillar_6(
                repo_root=REPO_ROOT,
                use_clean_room=True,
                faults=RealHwMilestone221FaultInjection(p6_tamper_schema_round_num=rnum),
                p1_meta=m1,
                p2_meta=m2,
                p3_meta=m3,
                p4_meta=m4,
                p5_meta=m5,
            )
            self.assertFalse(p6.passed, f"r{rnum}")

    def test_43_pillar6_fails_on_round41_or_42_nop_crash_or_emmc_write(self) -> None:
        m1, m2, m3, m4, m5 = self._clean_p1_to_p5_metas()
        for kw in (
            {"p6_round_nop_override_num": 42, "p6_round_nop_count_override": 1},
            {"p6_round_crash_override_num": 42, "p6_round_crashes_override": 1},
            {"p6_round_emmc_override_num": 41, "p6_round_emmc_writes_override": 1},
        ):
            p6, _ = _evaluate_pillar_6(
                repo_root=REPO_ROOT,
                use_clean_room=True,
                faults=RealHwMilestone221FaultInjection(**kw),
                p1_meta=m1,
                p2_meta=m2,
                p3_meta=m3,
                p4_meta=m4,
                p5_meta=m5,
            )
            self.assertFalse(p6.passed, kw)

    def test_44_pillar6_fails_when_round42_png_receipt_exceeds_28kib_ceiling(self) -> None:
        m1, m2, m3, m4, m5 = self._clean_p1_to_p5_metas()
        p6, _ = _evaluate_pillar_6(
            repo_root=REPO_ROOT,
            use_clean_room=True,
            faults=RealHwMilestone221FaultInjection(
                p6_png_size_override_round_num=42,
                p6_png_size_override_bytes=PNG_MAX_SIZE_BYTES,
            ),
            p1_meta=m1,
            p2_meta=m2,
            p3_meta=m3,
            p4_meta=m4,
            p5_meta=m5,
        )
        self.assertFalse(p6.passed)

    def test_45_pillar6_cross_pillar_invariants_fail_closed(self) -> None:
        m1, m2, m3, m4, m5 = self._clean_p1_to_p5_metas()
        for bad_kwargs in (
            {"p1_meta": dict(m1, g71_e_nd_actuator_tx_count=1)},
            {"p2_meta": dict(m2, otp_fuse_writes=1)},
            {"p3_meta": dict(m3, e_nd_actuator_tx_count=1)},
            {"p4_meta": dict(m4, emmc_corruptions=1)},
            {"p5_meta": dict(m5, p216_h0_equals_h3_count=15)},
        ):
            base = {
                "p1_meta": m1,
                "p2_meta": m2,
                "p3_meta": m3,
                "p4_meta": m4,
                "p5_meta": m5,
            }
            base.update(bad_kwargs)
            p6, _ = _evaluate_pillar_6(
                repo_root=REPO_ROOT,
                use_clean_room=True,
                faults=RealHwMilestone221FaultInjection(),
                **base,
            )
            self.assertFalse(p6.passed, bad_kwargs)

    # --- 9. Tamper-Evident Verifier (`verify_realhw_milestone221_master_gate`) ---

    def test_46_verifier_rejects_non_mapping_payload(self) -> None:
        res = verify_realhw_milestone221_master_gate("invalid")
        self.assertFalse(res.valid)
        self.assertFalse(res.schema_ok)

    def test_47_verifier_rejects_sha256_tamper_and_schema_tamper(self) -> None:
        d = self.rep_clean.to_dict()
        d["milestone221_sha256"] = "0" * 64
        self.assertFalse(verify_realhw_milestone221_master_gate(d).digest_matched)

        d2 = self.rep_clean.to_dict()
        d2["schema"] = "wrong_schema"
        d2["milestone221_sha256"] = compute_milestone221_sha256(d2)
        v2 = verify_realhw_milestone221_master_gate(d2)
        self.assertFalse(v2.valid)
        self.assertFalse(v2.schema_ok)

    def test_48_verifier_rejects_redline_tamper_even_when_rehashed(self) -> None:
        for key, bad_val in (
            ("hardware_live_attachment_authorized", True),
            ("persistent_emmc_writes_authorized", True),
            ("spi_nor_write_authorized", True),
            ("el3_payload_transmit_authorized", True),
            ("usb_packets_transmitted", 1),
            ("raw_firmware_bytes_leaked", 1),
            ("e_nd_actuator_tx_count", 1),
            ("emmc_write_count", 1),
            ("otp_fuse_writes", 1),
            ("rpmb_writes", 1),
            ("passive_tx_bytes", 1),
            ("p216_hardware_live_attachment_authorized", True),
        ):
            d = self.rep_clean.to_dict()
            d[key] = bad_val
            d["milestone221_sha256"] = compute_milestone221_sha256(d)
            res = verify_realhw_milestone221_master_gate(d)
            self.assertFalse(res.valid, key)
            self.assertFalse(res.safety_redlines_ok, key)

    def test_49_verifier_accepts_forward_compatible_45_auditor_and_39_stage_counts(self) -> None:
        d = self.rep_clean.to_dict()
        d["gate78_total_gates"] = 80
        d["gate78_offline_verified"] = 77
        d["gate78_simulated_verified"] = 80
        d["recovery_pillar_count"] = 32
        d["recovery_pillars_passed"] = 32
        d["auditors_total"] = 45
        d["auditors_passed"] = 45
        d["firmware_lab_auditor_count"] = 45
        d["firmware_lab_auditors_passed"] = 45
        d["vm_stages_total"] = 39
        d["vm_stages_passed"] = 39
        d["vm_coemulation_stage_count"] = 39
        d["vm_coemulation_stages_passed"] = 39
        d["milestone221_sha256"] = compute_milestone221_sha256(d)
        v = verify_realhw_milestone221_master_gate(d)
        self.assertTrue(v.valid, v.errors)

    def test_50_verifier_rejects_partial_forward_compat_mismatch(self) -> None:
        for key_pair in (
            ("auditors_total", 45, "auditors_passed", 44),
            ("vm_stages_total", 39, "vm_stages_passed", 38),
        ):
            k_tot, v_tot, k_pass, v_pass = key_pair
            d = self.rep_clean.to_dict()
            d[k_tot] = v_tot
            d[k_pass] = v_pass
            d["milestone221_sha256"] = compute_milestone221_sha256(d)
            self.assertFalse(verify_realhw_milestone221_master_gate(d).valid, key_pair)

    def test_51_verifier_rejects_sub_threshold_counts(self) -> None:
        for key, val in (
            ("gate78_simulated_verified", 77),
            ("recovery_pillar_count", 30),
            ("auditors_passed", 43),
            ("vm_stages_passed", 37),
            ("p216_sim_checklists_passed", 4),
            ("h0_equals_h3_count", 15),
            ("qemu_rounds_verified", 14),
            ("qemu_runs_verified", 44),
            ("qemu_png_receipts_verified", 29),
        ):
            d = self.rep_clean.to_dict()
            d[key] = val
            d["milestone221_sha256"] = compute_milestone221_sha256(d)
            self.assertFalse(verify_realhw_milestone221_master_gate(d).valid, key)

    def test_52_verifier_rejects_raw_bytes_repr_in_payload(self) -> None:
        d = self.rep_clean.to_dict()
        d["pillars"][0]["summary"] = "leaked b'\\x7fELF'"
        d["milestone221_sha256"] = compute_milestone221_sha256(d)
        self.assertFalse(verify_realhw_milestone221_master_gate(d).valid)

    # --- 10. CLI `verify-milestone-221` Integration (Fast Mocked Builder) ---

    def test_53_cli_verify_milestone_221_summary_and_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            out_json = tmp_path / "m221.json"
            out_md = tmp_path / "m221.md"
            buf = io.StringIO()
            with (
                mock.patch(
                    "fx6_closure.realhw_milestone221_master_gate.evaluate_realhw_milestone221_master_gate",
                    return_value=self.rep_clean,
                ),
                mock.patch("sys.stdout", buf),
            ):
                rc = fx6_cli_main(
                    [
                        "verify-milestone-221",
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
            self.assertIn("schema=realhw_milestone221_master_gate_v1", text)
            self.assertIn(
                f"gate78={self.rep_clean.gate78_offline_verified}/{self.rep_clean.gate78_total_gates}",
                text,
            )
            self.assertIn(
                f"recovery={self.rep_clean.recovery_pillars_passed}/{self.rep_clean.recovery_pillar_count}",
                text,
            )
            self.assertIn(
                f"auditors={self.rep_clean.auditors_passed}/{self.rep_clean.auditors_total}",
                text,
            )
            self.assertIn(
                f"vm_stages={self.rep_clean.vm_stages_passed}/{self.rep_clean.vm_stages_total}",
                text,
            )
            self.assertIn("qemu=15/15(45/45)", text)
            self.assertIn("pngs=30/30", text)
            self.assertTrue(out_json.is_file())
            self.assertTrue(out_md.is_file())
            self.assertTrue(
                verify_realhw_milestone221_master_gate(json.loads(out_json.read_text())).valid
            )

    def test_54_cli_verify_milestone_221_json_stdout(self) -> None:
        buf = io.StringIO()
        with (
            mock.patch(
                "fx6_closure.realhw_milestone221_master_gate.evaluate_realhw_milestone221_master_gate",
                return_value=self.rep_clean,
            ),
            mock.patch("sys.stdout", buf),
        ):
            rc = fx6_cli_main(["verify-milestone-221", "--clean-room", "--json"])
        self.assertEqual(rc, 0)
        parsed = json.loads(buf.getvalue())
        self.assertEqual(parsed["schema"], REALHW_MILESTONE221_SCHEMA)
        self.assertEqual(parsed["usb_packets_transmitted"], 0)
        self.assertEqual(parsed["e_nd_actuator_tx_count"], 0)

    def test_55_cli_verify_milestone_221_returns_1_on_failed_report(self) -> None:
        from dataclasses import replace

        bad_rep = replace(
            self.rep_clean,
            all_pillars_milestone_ready=False,
            status=STATUS_FAIL_CLOSED,
            passed_pillar_count=5,
            failed_pillar_ids=("P1",),
            milestone221_sha256="0" * 64,
        )
        buf = io.StringIO()
        with (
            mock.patch(
                "fx6_closure.realhw_milestone221_master_gate.evaluate_realhw_milestone221_master_gate",
                return_value=bad_rep,
            ),
            mock.patch("sys.stdout", buf),
        ):
            rc = fx6_cli_main(["verify-milestone-221", "--force-clean-room"])
        self.assertEqual(rc, 1)
        self.assertIn("status=FAILED", buf.getvalue())

    def test_56_synthetic_clean_room_kwarg_alias_supported(self) -> None:
        self.assertEqual(self.rep_clean.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(self.rep_clean.qemu_rounds_verified, 15)
        self.assertEqual(self.rep_clean.qemu_runs_verified, 45)
        self.assertEqual(self.rep_clean.qemu_png_receipts_verified, 30)


if __name__ == "__main__":
    unittest.main()
