"""Phase 193 dual-mode unit tests for Grand Milestone Phase 193 6-Pillar Master Gate."""

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
from fx3_recovery.realhw_26pillar_master_recovery_verifier import MASTER_26_PILLAR_IDS  # noqa: E402
from fx6_closure.realhw_milestone147_master_gate import (  # noqa: E402
    _worker_phase136,
)
from fx6_closure.realhw_milestone175_master_gate import (  # noqa: E402
    FIRMWARE_LAB_36_AUDITOR_KEYS,
    VM_COEMULATION_30_STAGE_KEYS,
)
from fx6_closure.realhw_milestone193_master_gate import (  # noqa: E402
    CALIBRATION_MUTATION_BYTES,
    CP_MUTATION_BYTES,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    FIRMWARE_LAB_40_AUDITOR_KEYS,
    HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    HARDWARE_LIVE_ATTACHMENT_REQUIREMENTS,
    ISP_WRITE_AUTHORIZED,
    MILESTONE193_SCHEMA_VERSION,
    OTP_FUSE_TOUCHES,
    P8_CP_MUTATION_FORBIDDEN,
    PASSIVE_TX_BYTES_EMITTED,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHASE_193_VERSION,
    PHYSICAL_USB_PACKETS_EMITTED,
    PILLAR_IDS,
    PILLAR_SPECS,
    PNG_MAGIC_BYTES,
    PNG_MAX_SIZE_BYTES,
    RAW_FIRMWARE_BYTES_LEAKED,
    REALHW_MILESTONE193_SCHEMA,
    RECOVERY_26_PILLAR_IDS,
    ROUND28_TO_37_PNG_RECEIPTS,
    ROUND28_TO_37_SPECS,
    ROUND35_EXPECTED_SCHEMA,
    ROUND36_EXPECTED_SCHEMA,
    ROUND37_EXPECTED_SCHEMA,
    RPMB_COUNTER_INCREMENTS,
    SPI_NOR_WRITE_AUTHORIZED,
    STATUS_FAIL_CLOSED,
    STATUS_MILESTONE_READY,
    USB_OR_CAMERA_OPERATIONS,
    VM_COEMULATION_33_STAGE_KEYS,
    WBI_MUTATION_BYTES,
    WBI_P5_WRITE_AND_HIBERNATION_FORBIDDEN,
    RealHwMilestone193FaultInjection,
    RealHwMilestone193MasterGateReport,
    _evaluate_pillar_1,
    _evaluate_pillar_2,
    _evaluate_pillar_3,
    _evaluate_pillar_4,
    _evaluate_pillar_5,
    _evaluate_pillar_6,
    _inspect_round_png_receipt,
    _load_round28_to_37_summary,
    _worker_phase143_154_186,
    _worker_recovery_26pillar,
    build_realhw_milestone193_master_gate_report,
    compute_milestone193_sha256,
    evaluate_milestone193_master_gate,
    render_milestone193_markdown,
    verify_realhw_milestone193_master_gate,
)
from test_milestone175_realhw_master_gate import (  # noqa: E402
    _make_clean_p3_36_auditors,
    _make_clean_p4_30_vm,
)

_RAW_BYTES_REPR_REGEX = r"(?<![0-9A-Za-z_/.-])b['\"]"


def _make_clean_p1_off(*, total_gates: int = 66, verified_gates: int = 63) -> dict:
    return {
        "schema": "fx3-safety-66gate-preflight-v1",
        "verification_mode": "CLEAN_ROOM_SYNTHETIC",
        "total_gates": total_gates,
        "verified_gates": verified_gates,
        "offline_63_gates_verified": True,
        "all_66_gates_verified": False,
        "g13_to_g66_all_passed": True,
        "g65_to_g66_all_passed": True,
        "dry_run_rehearsal_only": False,
        "overall_ready_for_hardware_attach": False,
        "agent_auto_flash_blocked": True,
        "el3_payload_transmit_authorized": False,
        "spi_nor_write_authorized": False,
        "persistent_emmc_writes_authorized": False,
        "persistent_write_release": False,
        "nested_g45_to_g66_valid": {f"g{n}": True for n in range(45, 67)},
        "gates_45_to_66": [
            {"gate_id": f"G{n}", "gate_code": f"G{n}", "status": "PASS", "passed": True, "violation_codes": ()}
            for n in range(45, 67)
        ],
        "errors": [],
    }


def _make_clean_p1_sim(*, total_gates: int = 66, verified_gates: int = 66) -> dict:
    gates_45_to_66 = [
        {"gate_id": f"G{n}", "gate_code": f"G{n}", "status": "PASS", "passed": True, "violation_codes": ()}
        for n in range(45, 45 + max(22, total_gates - 44))
    ]
    return {
        "schema": "fx3-safety-66gate-preflight-v1",
        "verification_mode": "CLEAN_ROOM_SYNTHETIC",
        "total_gates": total_gates,
        "verified_gates": verified_gates,
        "offline_63_gates_verified": True,
        "all_66_gates_verified": True,
        "g13_to_g66_all_passed": True,
        "g65_to_g66_all_passed": True,
        "dry_run_rehearsal_only": True,
        "overall_ready_for_hardware_attach": False,
        "agent_auto_flash_blocked": True,
        "el3_payload_transmit_authorized": False,
        "spi_nor_write_authorized": False,
        "persistent_emmc_writes_authorized": False,
        "persistent_write_release": False,
        "nested_g45_to_g66_valid": {f"g{n}": True for n in range(45, 67)},
        "gates_45_to_66": gates_45_to_66,
        "errors": [],
    }


def _make_clean_p2_26pillar() -> dict:
    return {
        "schema": "fx3-realhw-26pillar-recovery-master-verifier-v1",
        "version": "1.0.0",
        "verification_mode": "CLEAN_ROOM_SYNTHETIC",
        "all_passed": True,
        "status": "VERIFIED_26OF26_PILLAR_RECOVERY_MASTER",
        "pillar_count": len(RECOVERY_26_PILLAR_IDS),
        "pillars_passed": len(RECOVERY_26_PILLAR_IDS),
        "failed_pillars": [],
        "pillars": [
            {"pillar_number": idx, "pillar_id": pid, "passed": True, "errors": ()}
            for idx, pid in enumerate(RECOVERY_26_PILLAR_IDS, start=1)
        ],
        "pillar23_wbi": {"passed": True},
        "pillar24_slot1_ufu": {"passed": True},
        "pillar24_master_digest": "a" * 64,
        "pillar25_airgap_sd_bundle": {
            "all_passed": True,
            "status": "VERIFIED_PILLAR25_AIRGAP_SD_BUNDLE_MANIFEST",
            "suite_sha256": "b" * 64,
            "airgap_sockets_opened": 0,
        },
        "pillar26_a_fx3a_firewall": {"passed": True},
        "pillar26_b_xlrh1_hygiene": {"passed": True},
        "master_26pillar_sha256": "c" * 64,
        "otp_fuse_touches": 0,
        "otp_fuse_writes": 0,
        "rpmb_counter_increments": 0,
        "passive_tx_bytes_emitted": 0,
        "physical_usb_packets_emitted": 0,
        "physical_device_writes": 0,
        "raw_firmware_bytes_leaked": 0,
        "airgap_sockets_opened": 0,
        "el3_payload_transmit_authorized": False,
        "isp_write_authorized": False,
        "spi_nor_write_authorized": False,
        "persistent_emmc_writes_authorized": False,
        "persistent_write_release": False,
        "live_usb_iokit_transmit_enabled": False,
        "errors": [],
    }


def _make_clean_p3_40_auditors() -> dict:
    aud = _make_clean_p3_36_auditors()
    aud["realhw_hdmi_braw_wpa3_702_delta_audit"] = {
        "all_checks_passed": True,
        "o_rdonly_enforced": True,
        "hdmi_braw_bridged_sdi_masked": True,
        "wpa2_wpa3_only_enforced": True,
        "anamorphic_15x_16x_grm_unclipped": True,
        "usblan_and_dual_slot_telemetry_ready": True,
        "persistent_emmc_writes_authorized": False,
        "spi_nor_write_authorized": False,
        "el3_payload_transmit_authorized": False,
        "raw_firmware_bytes_leaked": 0,
        "report_sha256": "7" * 64,
    }
    aud["realhw_emount_info3d_breathing_02cf0232_audit"] = {
        "all_checks_passed": True,
        "o_rdonly_enforced": True,
        "emount_info3d_handshake_verified": True,
        "sony_lens_id_filter_and_02cf0232_verified": True,
        "p18_lensfile_ro_isolated": True,
        "monitor_control_210_focus_map_verified": True,
        "persistent_emmc_writes_authorized": False,
        "spi_nor_write_authorized": False,
        "el3_payload_transmit_authorized": False,
        "lens_partition_writes": 0,
        "backup_bin_writes": 0,
        "raw_firmware_bytes_leaked": 0,
        "report_sha256": "8" * 64,
    }
    aud["realhw_fx3_vs_fx3a_and_xlrh1_mishoe_audit"] = {
        "all_checks_passed": True,
        "o_rdonly_enforced": True,
        "fx3_vs_fx3a_branch_isolated": True,
        "xlrh1_mishoe_4ch_bridge_verified": True,
        "body_35mm_override_and_sq_mute_verified": True,
        "post_ufu_audio_default_hygiene_verified": True,
        "persistent_emmc_writes_authorized": False,
        "spi_nor_write_authorized": False,
        "el3_payload_transmit_authorized": False,
        "persistent_writes": 0,
        "backup_bin_writes": 0,
        "raw_firmware_bytes_leaked": 0,
        "report_sha256": "9" * 64,
    }
    aud["realhw_nouvc_dcc1_pd_lut_path_cineei_audit"] = {
        "all_checks_passed": True,
        "o_rdonly_enforced": True,
        "nouvc_and_network_streaming_verified": True,
        "power_delivery_pd_vs_dcc1_verified": True,
        "lut_path_cine_ei_and_rmt_p1bt_verified": True,
        "write_firewall_and_matrix_verified": True,
        "persistent_emmc_writes_authorized": False,
        "spi_nor_write_authorized": False,
        "el3_payload_transmit_authorized": False,
        "persistent_writes": 0,
        "raw_firmware_bytes_leaked": 0,
        "report_sha256": "a" * 64,
    }
    return aud


def _make_clean_p4_33_vm() -> dict:
    vm = _make_clean_p4_30_vm()
    vm["stage31_realhw_ssboot_wbi2_powerloss_slot1_ufu_hil"] = {
        "all_checks_passed": True,
        "nop_count": 0,
        "cp_mutation_bytes": 0,
        "wbi_mutation_bytes": 0,
        "wbi_persistent_writes": 0,
        "calibration_mutation_bytes": 0,
        "c2pa_cert_mutation_bytes": 0,
        "nvram_persistent_writes": 0,
        "bk4_persistent_nvram_writes": 0,
        "emmc_mutation_bytes": 0,
        "spi_nor_mutation_bytes": 0,
        "otp_fuse_touches": 0,
        "rpmb_counter_increments": 0,
        "p12_rq_lic_erofs_locked": True,
        "persistent_emmc_writes_authorized": False,
        "spi_nor_write_authorized": False,
        "el3_payload_transmit_authorized": False,
        "physical_usb_packets_emitted": 0,
        "raw_firmware_bytes_leaked": 0,
        "wf12_00342260_hits": 0,
        "phase178_audit_digest_sha256": "1" * 64,
    }
    vm["stage32_realhw_emount_info3d_breathing_hdmi_4264_raw_hil"] = {
        "all_checks_passed": True,
        "nop_count": 0,
        "cp_mutation_bytes": 0,
        "wbi_mutation_bytes": 0,
        "calibration_mutation_bytes": 0,
        "lens_partition_writes": 0,
        "p18_mutation_bytes": 0,
        "emmc_mutation_bytes": 0,
        "spi_nor_mutation_bytes": 0,
        "sdi_bnc_mmio_faults": 0,
        "p18_blkroset": 1,
        "persistent_emmc_writes_authorized": False,
        "spi_nor_write_authorized": False,
        "el3_payload_transmit_authorized": False,
        "raw_firmware_bytes_leaked": 0,
        "wf12_00342260_hits": 0,
        "phase182_audit_digest_sha256": "2" * 64,
    }
    vm["stage33_realhw_fx3a_firewall_and_xlrh1_4ch_mishoe_hil"] = {
        "all_checks_passed": True,
        "nop_count": 0,
        "cp_mutation_bytes": 0,
        "wbi_mutation_bytes": 0,
        "calibration_mutation_bytes": 0,
        "emmc_mutation_bytes": 0,
        "spi_nor_mutation_bytes": 0,
        "fx6_ribbon_mmio_faults": 0,
        "audio_pop_click_events": 0,
        "persistent_emmc_writes_authorized": False,
        "spi_nor_write_authorized": False,
        "el3_payload_transmit_authorized": False,
        "raw_firmware_bytes_leaked": 0,
        "wf12_00342260_hits": 0,
        "phase188_audit_digest_sha256": "3" * 64,
    }
    return vm


def _make_clean_p6_cross_pillar_kwargs() -> dict:
    return dict(
        repo_root=REPO_ROOT,
        use_clean_room=True,
        p1_meta={
            "persistent_emmc_writes_authorized": False,
            "spi_nor_write_authorized": False,
            "el3_payload_transmit_authorized": False,
            "simulated_ready_for_hardware_attach": False,
        },
        p2_meta={
            "otp_fuse_touches": 0,
            "rpmb_counter_increments": 0,
            "passive_tx_bytes_emitted": 0,
            "physical_usb_packets_emitted": 0,
            "raw_firmware_bytes_leaked": 0,
        },
        p3_meta={
            "calibration_mutation_bytes": 0,
            "wbi_mutation_bytes": 0,
            "raw_firmware_bytes_leaked": 0,
        },
        p4_meta={
            "cp_mutation_bytes": 0,
            "bk4_persistent_nvram_writes": 0,
            "wf12_00342260_hits": 0,
            "emmc_corruptions": 0,
        },
        p5_meta={
            "h0_equals_h3_count": 16,
            "p154_bench_go": True,
            "p154_usb_packets_emitted": 0,
            "p186_sim_gates_passed": 4,
            "p186_card_insert_authorized": False,
            "p186_sim_usb_packets_emitted": 0,
            "p186_sim_raw_firmware_bytes_leaked": 0,
        },
    )


class TestRealHwMilestone193MasterGate(unittest.TestCase):
    """52 dual-mode unit tests for Grand Milestone Phase 193 6-Pillar Master Gate."""

    report_clean: RealHwMilestone193MasterGateReport
    clean_elapsed_s: float
    report_primary: RealHwMilestone193MasterGateReport
    primary_elapsed_s: float
    _p136_clean: dict
    _p143_clean: dict
    _p154_clean: dict
    _p186_off_clean: dict
    _p186_sim_clean: dict

    @classmethod
    def setUpClass(cls) -> None:
        t0 = time.perf_counter()
        cls.report_clean = build_realhw_milestone193_master_gate_report(
            synthetic_clean_room=True
        )
        cls.clean_elapsed_s = time.perf_counter() - t0

        if _is_forced_clean_room():
            cls.report_primary = cls.report_clean
            cls.primary_elapsed_s = cls.clean_elapsed_s
        else:
            t1 = time.perf_counter()
            cls.report_primary = build_realhw_milestone193_master_gate_report(
                synthetic_clean_room=False
            )
            cls.primary_elapsed_s = time.perf_counter() - t1

        cls._p136_clean = _worker_phase136(True)
        (
            cls._p143_clean,
            cls._p154_clean,
            cls._p186_off_clean,
            cls._p186_sim_clean,
        ) = _worker_phase143_154_186(
            (str(DEFAULT_FX6_DONOR_LIB_DIR), str(DEFAULT_FX3_MODULES_DIR), True, True, {})
        )

    # ------------------------------------------------------------------
    # 1. Constants, Package Exports, E2E Dual-Mode Timing & Repeatability
    # ------------------------------------------------------------------

    def test_01_constants_and_package_exports(self) -> None:
        self.assertEqual(REALHW_MILESTONE193_SCHEMA, "realhw_milestone193_master_gate_v1")
        self.assertEqual(MILESTONE193_SCHEMA_VERSION, REALHW_MILESTONE193_SCHEMA)
        self.assertEqual(PHASE_193_VERSION, "193.0.0")
        self.assertEqual(PILLAR_IDS, ("P1", "P2", "P3", "P4", "P5", "P6"))
        self.assertEqual(len(PILLAR_SPECS), 6)
        self.assertEqual(len(RECOVERY_26_PILLAR_IDS), 26)
        self.assertEqual(len(FIRMWARE_LAB_40_AUDITOR_KEYS), 40)
        self.assertEqual(len(VM_COEMULATION_33_STAGE_KEYS), 33)
        self.assertEqual(len(ROUND28_TO_37_SPECS), 10)
        self.assertEqual(len(ROUND28_TO_37_PNG_RECEIPTS), 10)
        self.assertEqual(PNG_MAX_SIZE_BYTES, 28 * 1024)
        self.assertEqual(PNG_MAGIC_BYTES, b"\x89PNG\r\n\x1a\n")
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(PERSISTENT_WRITE_RELEASE)
        self.assertFalse(SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        self.assertFalse(ISP_WRITE_AUTHORIZED)
        self.assertFalse(HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        self.assertEqual(PHYSICAL_USB_PACKETS_EMITTED, 0)
        self.assertEqual(RAW_FIRMWARE_BYTES_LEAKED, 0)
        self.assertTrue(P8_CP_MUTATION_FORBIDDEN)
        self.assertTrue(WBI_P5_WRITE_AND_HIBERNATION_FORBIDDEN)
        self.assertEqual(CP_MUTATION_BYTES, 0)
        self.assertEqual(WBI_MUTATION_BYTES, 0)
        self.assertEqual(CALIBRATION_MUTATION_BYTES, 0)
        self.assertEqual(USB_OR_CAMERA_OPERATIONS, 0)
        self.assertEqual(OTP_FUSE_TOUCHES, 0)
        self.assertEqual(RPMB_COUNTER_INCREMENTS, 0)
        self.assertEqual(PASSIVE_TX_BYTES_EMITTED, 0)
        self.assertGreaterEqual(len(HARDWARE_LIVE_ATTACHMENT_REQUIREMENTS), 1)
        self.assertIs(
            fx6_closure.build_realhw_milestone193_master_gate_report,
            build_realhw_milestone193_master_gate_report,
        )
        self.assertIs(
            fx6_closure.evaluate_milestone193_master_gate,
            evaluate_milestone193_master_gate,
        )
        self.assertIs(
            fx6_closure.verify_realhw_milestone193_master_gate,
            verify_realhw_milestone193_master_gate,
        )
        self.assertEqual(fx6_closure.MILESTONE193_PILLAR_IDS, PILLAR_IDS)
        self.assertEqual(fx6_closure.STATUS_MILESTONE193_READY, STATUS_MILESTONE_READY)
        self.assertEqual(fx6_closure.STATUS_MILESTONE193_FAIL_CLOSED, STATUS_FAIL_CLOSED)
        self.assertEqual(fx6_closure.MILESTONE193_RAW_FIRMWARE_BYTES_LEAKED, 0)

    def test_02_clean_room_end_to_end_and_under_8s_ceiling(self) -> None:
        rep = self.report_clean
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(rep.all_pillars_milestone_ready, msg=f"errors={rep.errors}")
        self.assertEqual(rep.status, STATUS_MILESTONE_READY)
        self.assertEqual(rep.pillar_count, 6)
        self.assertEqual(rep.passed_pillar_count, 6)
        self.assertEqual(rep.failed_pillar_ids, ())
        ver = verify_realhw_milestone193_master_gate(rep)
        self.assertTrue(ver.valid, msg=f"verify errors={ver.errors}")
        self.assertLess(self.clean_elapsed_s, 8.0)

    def test_03_primary_mode_end_to_end_and_under_8s_ceiling(self) -> None:
        rep = self.report_primary
        expected_mode = "CLEAN_ROOM_SYNTHETIC" if _is_forced_clean_room() else "LOCAL_DONOR_O_RDONLY"
        self.assertEqual(rep.verification_mode, expected_mode)
        self.assertTrue(rep.all_pillars_milestone_ready, msg=f"errors={rep.errors}")
        self.assertEqual(rep.status, STATUS_MILESTONE_READY)
        self.assertEqual(rep.passed_pillar_count, 6)
        self.assertTrue(verify_realhw_milestone193_master_gate(rep).valid)
        self.assertLess(self.primary_elapsed_s, 8.0)

    def test_04_deterministic_repeatability_and_zero_raw_bytes_repr(self) -> None:
        rep_a = self.report_clean
        rep_b = build_realhw_milestone193_master_gate_report(synthetic_clean_room=True)
        self.assertEqual(rep_a.milestone193_sha256, rep_b.milestone193_sha256)
        self.assertEqual(rep_a.to_deterministic_json(), rep_b.to_deterministic_json())
        self.assertIsNone(re.search(_RAW_BYTES_REPR_REGEX, rep_a.to_deterministic_json()))

    def test_05_markdown_renderer_wave22_24_highlights(self) -> None:
        md = render_milestone193_markdown(self.report_clean)
        for token in (
            "Grand Milestone Phase 193",
            "MILESTONE_193_PREBENCH_MASTER_VERIFIED",
            "6/6",
            "persistent_emmc_writes_authorized = False",
            "spi_nor_write_authorized = False",
            "el3_payload_transmit_authorized = False",
            "hardware_live_attachment_authorized = False",
            "physical_usb_packets_emitted = 0",
            "raw_firmware_bytes_leaked = 0",
            "66-Gate Preflight",
            "26-Pillar Recovery",
            "40 Firmware-Lab Auditors",
            "33-Stage VM Co-Emulation",
            "Rounds 28..37",
            "preflight-card-insert",
            "0x02cf0232",
            "4264x2408",
            "ILME-FX3A",
            "XLR-H1",
            "DC-C1",
            ".cube",
        ):
            self.assertIn(token, md)

    # ------------------------------------------------------------------
    # 2. Pillar 1 — 66-Gate Safety Master Preflight
    # ------------------------------------------------------------------

    def test_06_p1_nominal_66gate_offline_63_vs_sim_66_and_g32_lock(self) -> None:
        p1 = next(p for p in self.report_primary.pillars if p.pillar_id == "P1")
        self.assertTrue(p1.passed, msg=f"errors={p1.errors}")
        self.assertGreaterEqual(p1.evidence["total_gates"], 66)
        self.assertGreaterEqual(p1.evidence["offline_verified_gates"], 63)
        self.assertLess(p1.evidence["offline_verified_gates"], p1.evidence["total_gates"])
        self.assertEqual(p1.evidence["simulated_verified_gates"], p1.evidence["total_gates"])
        self.assertFalse(p1.evidence["offline_ready_for_hardware_attach"])
        self.assertFalse(p1.evidence["simulated_ready_for_hardware_attach"])
        self.assertFalse(p1.evidence["persistent_emmc_writes_authorized"])
        self.assertFalse(p1.evidence["spi_nor_write_authorized"])
        self.assertFalse(p1.evidence["el3_payload_transmit_authorized"])
        self.assertTrue(all(p1.evidence["nested_g45_to_g66_valid"].values()))

    def test_07_p1_fault_offline_unlocked_or_sim_below_66_fails(self) -> None:
        raw_off_bad = _make_clean_p1_off()
        raw_off_bad["all_66_gates_verified"] = True
        raw_off_bad["overall_ready_for_hardware_attach"] = True
        p1_a = _evaluate_pillar_1(raw_off_bad, _make_clean_p1_sim())
        self.assertFalse(p1_a.passed)

        raw_sim_bad = _make_clean_p1_sim(total_gates=66, verified_gates=65)
        p1_b = _evaluate_pillar_1(_make_clean_p1_off(), raw_sim_bad)
        self.assertFalse(p1_b.passed)

    def test_08_p1_fault_nested_g59_to_g66_or_redline_breach(self) -> None:
        for gnum in (45, 59, 60, 61, 62, 63, 64, 65, 66):
            sim = _make_clean_p1_sim()
            sim["nested_g45_to_g66_valid"][f"g{gnum}"] = False
            p1 = _evaluate_pillar_1(_make_clean_p1_off(), sim)
            self.assertFalse(p1.passed, msg=f"nested g{gnum}=False should fail")

        for redline_key, bad_val in (
            ("persistent_emmc_writes_authorized", True),
            ("persistent_write_release", True),
            ("spi_nor_write_authorized", True),
            ("el3_payload_transmit_authorized", True),
            ("agent_auto_flash_blocked", False),
        ):
            sim = _make_clean_p1_sim()
            sim[redline_key] = bad_val
            p1 = _evaluate_pillar_1(_make_clean_p1_off(), sim)
            self.assertFalse(p1.passed, msg=f"{redline_key}={bad_val} should fail")

    def test_09_p1_forward_compat_67_gates_passes(self) -> None:
        off = _make_clean_p1_off(total_gates=67, verified_gates=64)
        sim = _make_clean_p1_sim(total_gates=67, verified_gates=67)
        p1 = _evaluate_pillar_1(off, sim)
        self.assertTrue(p1.passed, msg=f"errors={p1.errors}")

    def test_10_p1_live_fault_request_persistent_emmc_writes_fails_closed(self) -> None:
        rep = build_realhw_milestone193_master_gate_report(
            synthetic_clean_room=True,
            faults=RealHwMilestone193FaultInjection(p1_request_persistent_writes=True),
        )
        self.assertFalse(rep.all_pillars_milestone_ready)
        self.assertEqual(rep.status, STATUS_FAIL_CLOSED)
        self.assertIn("P1", rep.failed_pillar_ids)
        self.assertFalse(verify_realhw_milestone193_master_gate(rep).valid)

    # ------------------------------------------------------------------
    # 3. Pillar 2 — >= 26-Pillar Recovery Master & Zero-Touch Redlines
    # ------------------------------------------------------------------

    def test_11_p2_nominal_26_recovery_pillars_and_zero_touch(self) -> None:
        p2 = next(p for p in self.report_primary.pillars if p.pillar_id == "P2")
        self.assertTrue(p2.passed, msg=f"errors={p2.errors}")
        self.assertGreaterEqual(p2.evidence["recovery_pillar_count"], 26)
        self.assertEqual(p2.evidence["recovery_pillars_passed"], p2.evidence["recovery_pillar_count"])
        for pid in RECOVERY_26_PILLAR_IDS:
            self.assertTrue(p2.evidence["pillar_statuses"].get(pid), msg=f"missing/failed {pid}")
        self.assertEqual(p2.evidence["otp_fuse_touches"], 0)
        self.assertEqual(p2.evidence["rpmb_counter_increments"], 0)
        self.assertEqual(p2.evidence["passive_tx_bytes_emitted"], 0)
        self.assertEqual(p2.evidence["physical_usb_packets_emitted"], 0)
        self.assertEqual(p2.evidence["raw_firmware_bytes_leaked"], 0)
        self.assertFalse(p2.evidence["el3_payload_transmit_authorized"])
        self.assertFalse(p2.evidence["isp_write_authorized"])

    def test_12_p2_fault_recovery_pillars_23_to_26_and_subverifiers_fail_closed(self) -> None:
        for idx, pid in enumerate(RECOVERY_26_PILLAR_IDS[22:], start=23):
            raw = _make_clean_p2_26pillar()
            raw["pillars"][idx - 1]["passed"] = False
            p2, _ = _evaluate_pillar_2(raw, RealHwMilestone193FaultInjection())
            self.assertFalse(p2.passed, msg=f"Pillar {pid} failure must fail P2 closed")

        for subkey, subflag in (
            ("pillar23_wbi", "passed"),
            ("pillar24_slot1_ufu", "passed"),
            ("pillar25_airgap_sd_bundle", "all_passed"),
            ("pillar26_a_fx3a_firewall", "passed"),
            ("pillar26_b_xlrh1_hygiene", "passed"),
        ):
            raw = _make_clean_p2_26pillar()
            raw[subkey][subflag] = False
            p2_s, _ = _evaluate_pillar_2(raw, RealHwMilestone193FaultInjection())
            self.assertFalse(p2_s.passed, msg=f"{subkey}.{subflag}=False must fail P2 closed")

        raw_worker_fault = _worker_recovery_26pillar((True, MASTER_26_PILLAR_IDS[-1]))
        p2_w, _ = _evaluate_pillar_2(raw_worker_fault, RealHwMilestone193FaultInjection())
        self.assertFalse(p2_w.passed)

    def test_13_p2_fault_otp_rpmb_tx_usb_raw_leaked_or_write_auth_breach(self) -> None:
        for fault in (
            RealHwMilestone193FaultInjection(p2_otp_fuse_touches_override=1),
            RealHwMilestone193FaultInjection(p2_rpmb_increments_override=1),
            RealHwMilestone193FaultInjection(p2_passive_tx_bytes_override=1),
            RealHwMilestone193FaultInjection(p2_physical_usb_packets_override=1),
            RealHwMilestone193FaultInjection(p2_physical_device_writes_override=1),
            RealHwMilestone193FaultInjection(p2_raw_firmware_bytes_leaked_override=1),
        ):
            p2, _ = _evaluate_pillar_2(_make_clean_p2_26pillar(), fault)
            self.assertFalse(p2.passed)

        for key in (
            "el3_payload_transmit_authorized",
            "isp_write_authorized",
            "spi_nor_write_authorized",
            "persistent_emmc_writes_authorized",
            "live_usb_iokit_transmit_enabled",
        ):
            raw = _make_clean_p2_26pillar()
            raw[key] = True
            p2, _ = _evaluate_pillar_2(raw, RealHwMilestone193FaultInjection())
            self.assertFalse(p2.passed, msg=f"{key}=True must fail P2 closed")

    def test_14_p2_forward_compat_27_recovery_pillars(self) -> None:
        raw = _make_clean_p2_26pillar()
        raw["pillars"].append({"pillar_number": 27, "pillar_id": "future_pillar_27", "passed": True, "errors": ()})
        p2_ok, meta_ok = _evaluate_pillar_2(raw, RealHwMilestone193FaultInjection())
        self.assertTrue(p2_ok.passed, msg=f"errors={p2_ok.errors}")
        self.assertEqual(meta_ok["recovery_pillar_count"], 27)

        raw["pillars"][-1]["passed"] = False
        p2_bad, _ = _evaluate_pillar_2(raw, RealHwMilestone193FaultInjection())
        self.assertFalse(p2_bad.passed)

    # ------------------------------------------------------------------
    # 4. Pillar 3 — >= 40 Firmware-Lab Auditors (Auditors #1..#40)
    # ------------------------------------------------------------------

    def test_15_p3_nominal_40_auditors_zero_cal_wbi_and_raw_leaked(self) -> None:
        p3 = next(p for p in self.report_primary.pillars if p.pillar_id == "P3")
        self.assertTrue(p3.passed, msg=f"errors={p3.errors}")
        self.assertGreaterEqual(p3.evidence["auditor_count"], 40)
        self.assertEqual(p3.evidence["passed_auditor_count"], p3.evidence["auditor_count"])
        for ak in FIRMWARE_LAB_40_AUDITOR_KEYS:
            self.assertTrue(p3.evidence["auditor_statuses"].get(ak), msg=f"missing/failed {ak}")
        self.assertEqual(p3.evidence["calibration_mutation_bytes"], 0)
        self.assertEqual(p3.evidence["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(p3.evidence["wbi_mutation_bytes"], 0)

    def test_16_p3_fault_core_calibration_cp_and_wbi_regression(self) -> None:
        for fault in (
            RealHwMilestone193FaultInjection(p3_calibration_mutation_bytes=1),
            RealHwMilestone193FaultInjection(p3_realhw_cp_spi_mutation_bytes=1),
            RealHwMilestone193FaultInjection(p3_wbi2_hibdrv_mutation_bytes=1),
        ):
            p3, _ = _evaluate_pillar_3(_make_clean_p3_40_auditors(), fault)
            self.assertFalse(p3.passed)

    def test_17_p3_fault_auditor37_hdmi_braw_wpa3_702_delta(self) -> None:
        p3, _ = _evaluate_pillar_3(
            _make_clean_p3_40_auditors(),
            RealHwMilestone193FaultInjection(p3_hdmi_braw_raw_leaked_override=1),
        )
        self.assertFalse(p3.passed)

        for key, bad_val in (
            ("hdmi_braw_bridged_sdi_masked", False),
            ("wpa2_wpa3_only_enforced", False),
            ("anamorphic_15x_16x_grm_unclipped", False),
            ("el3_payload_transmit_authorized", True),
        ):
            aud = _make_clean_p3_40_auditors()
            aud["realhw_hdmi_braw_wpa3_702_delta_audit"][key] = bad_val
            p3_b, _ = _evaluate_pillar_3(aud, RealHwMilestone193FaultInjection())
            self.assertFalse(p3_b.passed, msg=f"Auditor 37 {key}={bad_val} must fail P3")

    def test_18_p3_fault_auditor38_emount_info3d_02cf0232_and_p18(self) -> None:
        p3, _ = _evaluate_pillar_3(
            _make_clean_p3_40_auditors(),
            RealHwMilestone193FaultInjection(p3_emount_lens_partition_writes_override=1),
        )
        self.assertFalse(p3.passed)

        for key, bad_val in (
            ("emount_info3d_handshake_verified", False),
            ("sony_lens_id_filter_and_02cf0232_verified", False),
            ("p18_lensfile_ro_isolated", False),
            ("monitor_control_210_focus_map_verified", False),
            ("backup_bin_writes", 1),
        ):
            aud = _make_clean_p3_40_auditors()
            aud["realhw_emount_info3d_breathing_02cf0232_audit"][key] = bad_val
            p3_b, _ = _evaluate_pillar_3(aud, RealHwMilestone193FaultInjection())
            self.assertFalse(p3_b.passed, msg=f"Auditor 38 {key}={bad_val} must fail P3")

    def test_19_p3_fault_auditor39_fx3a_branch_firewall_and_xlrh1_mishoe(self) -> None:
        p3, _ = _evaluate_pillar_3(
            _make_clean_p3_40_auditors(),
            RealHwMilestone193FaultInjection(p3_fx3a_xlrh1_persistent_writes_override=1),
        )
        self.assertFalse(p3.passed)

        for key, bad_val in (
            ("fx3_vs_fx3a_branch_isolated", False),
            ("xlrh1_mishoe_4ch_bridge_verified", False),
            ("body_35mm_override_and_sq_mute_verified", False),
            ("post_ufu_audio_default_hygiene_verified", False),
            ("backup_bin_writes", 1),
        ):
            aud = _make_clean_p3_40_auditors()
            aud["realhw_fx3_vs_fx3a_and_xlrh1_mishoe_audit"][key] = bad_val
            p3_b, _ = _evaluate_pillar_3(aud, RealHwMilestone193FaultInjection())
            self.assertFalse(p3_b.passed, msg=f"Auditor 39 {key}={bad_val} must fail P3")

    def test_20_p3_fault_auditor40_nouvc_dcc1_pd_lut_path_cineei(self) -> None:
        p3, _ = _evaluate_pillar_3(
            _make_clean_p3_40_auditors(),
            RealHwMilestone193FaultInjection(p3_nouvc_dcc1_lut_persistent_writes_override=1),
        )
        self.assertFalse(p3.passed)

        for key, bad_val in (
            ("nouvc_and_network_streaming_verified", False),
            ("power_delivery_pd_vs_dcc1_verified", False),
            ("lut_path_cine_ei_and_rmt_p1bt_verified", False),
            ("write_firewall_and_matrix_verified", False),
            ("raw_firmware_bytes_leaked", 4),
        ):
            aud = _make_clean_p3_40_auditors()
            aud["realhw_nouvc_dcc1_pd_lut_path_cineei_audit"][key] = bad_val
            p3_b, _ = _evaluate_pillar_3(aud, RealHwMilestone193FaultInjection())
            self.assertFalse(p3_b.passed, msg=f"Auditor 40 {key}={bad_val} must fail P3")

    def test_21_p3_forward_compat_41_auditors(self) -> None:
        aud = _make_clean_p3_40_auditors()
        aud["future_auditor_41"] = {"all_checks_passed": True, "report_sha256": "e" * 64}
        p3_ok, meta_ok = _evaluate_pillar_3(aud, RealHwMilestone193FaultInjection())
        self.assertTrue(p3_ok.passed, msg=f"errors={p3_ok.errors}")
        self.assertEqual(meta_ok["auditor_count"], 41)

        aud["future_auditor_41"] = {"all_checks_passed": False}
        p3_bad, _ = _evaluate_pillar_3(aud, RealHwMilestone193FaultInjection())
        self.assertFalse(p3_bad.passed)

    # ------------------------------------------------------------------
    # 5. Pillar 4 — >= 33-Stage VM HIL Co-Emulation
    # ------------------------------------------------------------------

    def test_22_p4_nominal_33_stages_zero_emmc_corruptions(self) -> None:
        p4 = next(p for p in self.report_primary.pillars if p.pillar_id == "P4")
        self.assertTrue(p4.passed, msg=f"errors={p4.errors}")
        self.assertGreaterEqual(p4.evidence["stage_count"], 33)
        self.assertEqual(p4.evidence["passed_stage_count"], p4.evidence["stage_count"])
        for sk in VM_COEMULATION_33_STAGE_KEYS:
            self.assertTrue(p4.evidence["stage_statuses"].get(sk), msg=f"missing/failed {sk}")
        self.assertEqual(p4.evidence["emmc_corruptions"], 0)
        self.assertEqual(p4.evidence["wf12_00342260_hits"], 0)

    def test_23_p4_fault_stage31_ssboot_wbi2_powerloss_slot1_ufu(self) -> None:
        p4, _ = _evaluate_pillar_4(
            _make_clean_p4_33_vm(),
            RealHwMilestone193FaultInjection(p4_stage31_wbi_or_c2pa_mutation_bytes=1),
        )
        self.assertFalse(p4.passed)

        for key, bad_val in (
            ("p12_rq_lic_erofs_locked", False),
            ("wbi_persistent_writes", 1),
            ("c2pa_cert_mutation_bytes", 1),
            ("emmc_mutation_bytes", 1),
            ("physical_usb_packets_emitted", 1),
            ("wf12_00342260_hits", 1),
        ):
            vm = _make_clean_p4_33_vm()
            vm["stage31_realhw_ssboot_wbi2_powerloss_slot1_ufu_hil"][key] = bad_val
            p4_b, _ = _evaluate_pillar_4(vm, RealHwMilestone193FaultInjection())
            self.assertFalse(p4_b.passed, msg=f"Stage 31 {key}={bad_val} must fail P4")

    def test_24_p4_fault_stage32_emount_info3d_breathing_hdmi_4264_raw(self) -> None:
        p4, _ = _evaluate_pillar_4(
            _make_clean_p4_33_vm(),
            RealHwMilestone193FaultInjection(p4_stage32_lens_or_sdi_faults=1),
        )
        self.assertFalse(p4.passed)

        for key, bad_val in (
            ("p18_blkroset", 0),
            ("lens_partition_writes", 1),
            ("sdi_bnc_mmio_faults", 1),
            ("spi_nor_write_authorized", True),
            ("wf12_00342260_hits", 1),
        ):
            vm = _make_clean_p4_33_vm()
            vm["stage32_realhw_emount_info3d_breathing_hdmi_4264_raw_hil"][key] = bad_val
            p4_b, _ = _evaluate_pillar_4(vm, RealHwMilestone193FaultInjection())
            self.assertFalse(p4_b.passed, msg=f"Stage 32 {key}={bad_val} must fail P4")

    def test_25_p4_fault_stage33_fx3a_firewall_xlrh1_4ch_mishoe(self) -> None:
        p4, _ = _evaluate_pillar_4(
            _make_clean_p4_33_vm(),
            RealHwMilestone193FaultInjection(p4_stage33_ribbon_or_audio_faults=1),
        )
        self.assertFalse(p4.passed)

        for key, bad_val in (
            ("fx6_ribbon_mmio_faults", 1),
            ("audio_pop_click_events", 1),
            ("el3_payload_transmit_authorized", True),
            ("raw_firmware_bytes_leaked", 4),
            ("wf12_00342260_hits", 1),
        ):
            vm = _make_clean_p4_33_vm()
            vm["stage33_realhw_fx3a_firewall_and_xlrh1_4ch_mishoe_hil"][key] = bad_val
            p4_b, _ = _evaluate_pillar_4(vm, RealHwMilestone193FaultInjection())
            self.assertFalse(p4_b.passed, msg=f"Stage 33 {key}={bad_val} must fail P4")

    def test_26_p4_forward_compat_34_vm_stages(self) -> None:
        vm = _make_clean_p4_33_vm()
        vm["stage34_future_realhw_hil"] = {"all_checks_passed": True}
        p4_ok, meta_ok = _evaluate_pillar_4(vm, RealHwMilestone193FaultInjection())
        self.assertTrue(p4_ok.passed, msg=f"errors={p4_ok.errors}")
        self.assertEqual(meta_ok["stage_count"], 34)

        vm["stage34_future_realhw_hil"] = {"all_checks_passed": False}
        p4_bad, _ = _evaluate_pillar_4(vm, RealHwMilestone193FaultInjection())
        self.assertFalse(p4_bad.passed)

    # ------------------------------------------------------------------
    # 6. Pillar 5 — Ph136/143/154 + Ph186 (`preflight-card-insert`)
    # ------------------------------------------------------------------

    def test_27_p5_nominal_p136_p143_p154_and_p186_card_insert_preflight(self) -> None:
        p5 = next(p for p in self.report_primary.pillars if p.pillar_id == "P5")
        self.assertTrue(p5.passed, msg=f"errors={p5.errors}")
        self.assertGreaterEqual(p5.evidence["p136_u6_command_count"], 19)
        self.assertTrue(p5.evidence["p136_u4_u5_u6_closed"])
        self.assertLessEqual(p5.evidence["p143_eh1_observed_latency_us"], 50)
        self.assertEqual(p5.evidence["p143_h0_equals_h3_count"], 16)
        self.assertTrue(p5.evidence["p154_bench_go"])
        self.assertEqual(p5.evidence["p154_usb_packets_emitted"], 0)
        self.assertEqual(p5.evidence["p186_offline_go_no_go"], "BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT")
        self.assertEqual(p5.evidence["p186_offline_gates_passed"], 2)
        self.assertEqual(p5.evidence["p186_sim_go_no_go"], "DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH")
        self.assertEqual(p5.evidence["p186_sim_gates_passed"], 4)
        self.assertFalse(p5.evidence["p186_card_insert_authorized"])
        self.assertTrue(p5.evidence["p186_body_fw_ge_204"])
        self.assertTrue(p5.evidence["p186_dual_media_serial_bound"])
        self.assertEqual(p5.evidence["p186_h0_equals_h3_count"], 16)
        self.assertEqual(p5.evidence["p186_sim_usb_packets_emitted"], 0)
        self.assertEqual(p5.evidence["p186_sim_raw_firmware_bytes_leaked"], 0)

    def test_28_p5_fault_p136_p143_and_p154_regressions_fail_closed(self) -> None:
        p5_u, _ = _evaluate_pillar_5(
            self._p136_clean,
            self._p143_clean,
            self._p154_clean,
            self._p186_off_clean,
            self._p186_sim_clean,
            RealHwMilestone193FaultInjection(p5_inject_p136_u4_u5_u6_fault=True),
        )
        self.assertFalse(p5_u.passed)

        p5_eh1, _ = _evaluate_pillar_5(
            self._p136_clean,
            self._p143_clean,
            self._p154_clean,
            self._p186_off_clean,
            self._p186_sim_clean,
            RealHwMilestone193FaultInjection(p5_inject_p143_escape_hatch_over_budget_us=10),
        )
        self.assertFalse(p5_eh1.passed)

        _, raw_p154_nogo, _, _ = _worker_phase143_154_186(
            (str(DEFAULT_FX6_DONOR_LIB_DIR), str(DEFAULT_FX3_MODULES_DIR), True, False, {})
        )
        p5_nogo, _ = _evaluate_pillar_5(
            self._p136_clean,
            self._p143_clean,
            raw_p154_nogo,
            self._p186_off_clean,
            self._p186_sim_clean,
            RealHwMilestone193FaultInjection(p5_inject_p154_no_go_fault=True),
        )
        self.assertFalse(p5_nogo.passed)

    def test_29_p5_fault_p186_appledouble_junk_fails_closed(self) -> None:
        _, _, p186_off, p186_sim = _worker_phase143_154_186(
            (
                str(DEFAULT_FX6_DONOR_LIB_DIR),
                str(DEFAULT_FX3_MODULES_DIR),
                True,
                True,
                {"inject_appledouble_fault": True},
            )
        )
        p5, _ = _evaluate_pillar_5(
            self._p136_clean,
            self._p143_clean,
            self._p154_clean,
            p186_off,
            p186_sim,
            RealHwMilestone193FaultInjection(p5_inject_p186_appledouble_fault=True),
        )
        self.assertFalse(p5.passed)

    def test_30_p5_fault_p186_fw_below_204_floor_fails_closed(self) -> None:
        _, _, p186_off, p186_sim = _worker_phase143_154_186(
            (
                str(DEFAULT_FX6_DONOR_LIB_DIR),
                str(DEFAULT_FX3_MODULES_DIR),
                True,
                True,
                {"inject_fw_below_204": True},
            )
        )
        p5, _ = _evaluate_pillar_5(
            self._p136_clean,
            self._p143_clean,
            self._p154_clean,
            p186_off,
            p186_sim,
            RealHwMilestone193FaultInjection(p5_inject_p186_fw_below_204=True),
        )
        self.assertFalse(p5.passed)

    def test_31_p5_fault_p186_single_device_st_dev_collision_fails_closed(self) -> None:
        _, _, p186_off, p186_sim = _worker_phase143_154_186(
            (
                str(DEFAULT_FX6_DONOR_LIB_DIR),
                str(DEFAULT_FX3_MODULES_DIR),
                True,
                True,
                {"inject_single_device_collision": True},
            )
        )
        p5, _ = _evaluate_pillar_5(
            self._p136_clean,
            self._p143_clean,
            self._p154_clean,
            p186_off,
            p186_sim,
            RealHwMilestone193FaultInjection(p5_inject_p186_single_device_collision=True),
        )
        self.assertFalse(p5.passed)

    def test_32_p5_fault_p186_h0_h3_drift_or_usb_packets_override_fails_closed(self) -> None:
        _, _, p186_off, p186_sim = _worker_phase143_154_186(
            (
                str(DEFAULT_FX6_DONOR_LIB_DIR),
                str(DEFAULT_FX3_MODULES_DIR),
                True,
                True,
                {"inject_h0_h3_drift": True},
            )
        )
        p5_drift, _ = _evaluate_pillar_5(
            self._p136_clean,
            self._p143_clean,
            self._p154_clean,
            p186_off,
            p186_sim,
            RealHwMilestone193FaultInjection(p5_inject_p186_h0_h3_drift=True),
        )
        self.assertFalse(p5_drift.passed)

        p5_usb, _ = _evaluate_pillar_5(
            self._p136_clean,
            self._p143_clean,
            self._p154_clean,
            self._p186_off_clean,
            self._p186_sim_clean,
            RealHwMilestone193FaultInjection(p5_inject_p186_usb_packets_override=1),
        )
        self.assertFalse(p5_usb.passed)

    # ------------------------------------------------------------------
    # 7. Pillar 6 — Live FX3 7.02 QEMU Rounds 28..37 & 20 PNG Receipts
    # ------------------------------------------------------------------

    def test_33_p6_committed_rounds_28_to_37_receipts_o_rdonly(self) -> None:
        self.assertEqual(ROUND28_TO_37_SPECS[7].expected_schema, ROUND35_EXPECTED_SCHEMA)
        self.assertEqual(ROUND28_TO_37_SPECS[8].expected_schema, ROUND36_EXPECTED_SCHEMA)
        self.assertEqual(ROUND28_TO_37_SPECS[9].expected_schema, ROUND37_EXPECTED_SCHEMA)
        for spec in ROUND28_TO_37_SPECS:
            data, src = _load_round28_to_37_summary(spec, repo_root=REPO_ROOT, use_clean_room=False)
            self.assertEqual(src, "REPO_SUMMARY_O_RDONLY")
            self.assertEqual(data["schema"], spec.expected_schema)
            self.assertIn("4.9.337-scel+", data["kernel_version"])
            self.assertEqual(len(spec.run_specs), 3)

    def test_34_p6_committed_20_png_receipts_under_28kib_and_valid_magic(self) -> None:
        total_pngs = 0
        for rnum in range(28, 38):
            pair = ROUND28_TO_37_PNG_RECEIPTS[rnum]
            self.assertEqual(len(pair), 2)
            for rel in pair:
                ok, size, src = _inspect_round_png_receipt(
                    rel, repo_root=REPO_ROOT, use_clean_room=False
                )
                self.assertTrue(ok, msg=f"PNG receipt invalid/missing: {rel} (size={size})")
                self.assertEqual(src, "REPO_PNG_O_RDONLY")
                self.assertGreater(size, 0)
                self.assertLess(size, PNG_MAX_SIZE_BYTES)
                total_pngs += 1
        self.assertEqual(total_pngs, 20)

    def test_35_p6_clean_room_fallback_all_10_rounds_and_20_pngs_when_absent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p6, meta6 = _evaluate_pillar_6(
                repo_root=Path(tmp),
                use_clean_room=True,
                faults=RealHwMilestone193FaultInjection(),
                p1_meta=_make_clean_p6_cross_pillar_kwargs()["p1_meta"],
                p2_meta=_make_clean_p6_cross_pillar_kwargs()["p2_meta"],
                p3_meta=_make_clean_p6_cross_pillar_kwargs()["p3_meta"],
                p4_meta=_make_clean_p6_cross_pillar_kwargs()["p4_meta"],
                p5_meta=_make_clean_p6_cross_pillar_kwargs()["p5_meta"],
            )
        self.assertTrue(p6.passed, msg=f"errors={p6.errors}")
        self.assertEqual(meta6["qemu_rounds_verified"], 10)
        self.assertEqual(meta6["qemu_runs_verified"], 30)
        self.assertEqual(meta6["qemu_png_receipts_verified"], 20)
        self.assertLess(meta6["qemu_png_max_bytes"], PNG_MAX_SIZE_BYTES)
        for rnum in range(28, 38):
            self.assertEqual(p6.evidence["round_sources"][f"r{rnum}"], "CLEAN_ROOM_SYNTHETIC")
            self.assertEqual(p6.evidence["png_sources_by_round"][f"r{rnum}"], "CLEAN_ROOM_SYNTHETIC")

    def test_36_p6_missing_reports_without_clean_room_raises_file_not_found(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            for spec in ROUND28_TO_37_SPECS:
                with self.assertRaises(FileNotFoundError):
                    _load_round28_to_37_summary(spec, repo_root=Path(tmp), use_clean_room=False)

    def test_37_p6_fault_rounds_28_to_37_nop_crash_emmc_or_schema_tamper(self) -> None:
        base_kw = _make_clean_p6_cross_pillar_kwargs()
        for rnum in range(28, 38):
            for fault in (
                RealHwMilestone193FaultInjection(
                    p6_round_nop_override_num=rnum, p6_round_nop_count_override=1
                ),
                RealHwMilestone193FaultInjection(
                    p6_round_crash_override_num=rnum, p6_round_crashes_override=1
                ),
                RealHwMilestone193FaultInjection(
                    p6_round_emmc_override_num=rnum, p6_round_emmc_writes_override=1
                ),
                RealHwMilestone193FaultInjection(p6_tamper_schema_round_num=rnum),
            ):
                p6, _ = _evaluate_pillar_6(faults=fault, **base_kw)
                self.assertFalse(p6.passed, msg=f"Round {rnum} fault {fault} must fail P6 closed")

    def test_38_p6_fault_png_receipt_ge_28kib_or_invalid_magic_fails_closed(self) -> None:
        base_kw = _make_clean_p6_cross_pillar_kwargs()
        for rnum in (28, 35, 36, 37):
            p6_big, _ = _evaluate_pillar_6(
                faults=RealHwMilestone193FaultInjection(
                    p6_png_size_override_round_num=rnum,
                    p6_png_size_override_bytes=PNG_MAX_SIZE_BYTES,
                ),
                **base_kw,
            )
            self.assertFalse(p6_big.passed, msg=f"Round {rnum} PNG >= 28 KiB must fail P6 closed")

        with tempfile.TemporaryDirectory() as tmp:
            bad_png = Path(tmp) / "bad.png"
            bad_png.write_bytes(b"NOT_A_PNG_HEADER")
            ok, _, _ = _inspect_round_png_receipt("bad.png", repo_root=Path(tmp), use_clean_room=False)
            self.assertFalse(ok)

    def test_39_p6_cross_pillar_redline_breaches_rejected(self) -> None:
        clean_args = _make_clean_p6_cross_pillar_kwargs()
        clean_args["faults"] = RealHwMilestone193FaultInjection()
        for block, key, val in (
            ("p1_meta", "el3_payload_transmit_authorized", True),
            ("p1_meta", "spi_nor_write_authorized", True),
            ("p2_meta", "physical_usb_packets_emitted", 1),
            ("p2_meta", "raw_firmware_bytes_leaked", 1),
            ("p3_meta", "wbi_mutation_bytes", 1),
            ("p3_meta", "raw_firmware_bytes_leaked", 1),
            ("p4_meta", "emmc_corruptions", 1),
            ("p5_meta", "p154_bench_go", False),
            ("p5_meta", "p186_card_insert_authorized", True),
            ("p5_meta", "p186_sim_gates_passed", 3),
        ):
            kw = copy.deepcopy(clean_args)
            kw[block][key] = val
            p6, _ = _evaluate_pillar_6(**kw)
            self.assertFalse(p6.passed, msg=f"Breached {block}[{key}]={val} must fail P6")

    # ------------------------------------------------------------------
    # 8. Tamper-Evident Verifier, Forward Compat & CLI Integration
    # ------------------------------------------------------------------

    def test_40_verifier_rejects_non_mapping_bad_schema_and_tampered_sha256(self) -> None:
        res_bad_type = verify_realhw_milestone193_master_gate(["not", "a", "dict"])
        self.assertFalse(res_bad_type.valid)

        d = self.report_clean.to_dict()
        d["schema_version"] = "wrong-schema"
        d["milestone193_sha256"] = compute_milestone193_sha256(d)
        res_bad_schema = verify_realhw_milestone193_master_gate(d)
        self.assertFalse(res_bad_schema.valid)
        self.assertFalse(res_bad_schema.schema_ok)

        d2 = self.report_clean.to_dict()
        d2["qemu_runs_verified"] = 29
        res_mut = verify_realhw_milestone193_master_gate(d2)
        self.assertFalse(res_mut.valid)
        self.assertFalse(res_mut.digest_matched)

    def test_41_verifier_rejects_all_breached_hardware_redlines(self) -> None:
        for key, bad_val in (
            ("persistent_emmc_writes_authorized", True),
            ("persistent_write_release", True),
            ("spi_nor_write_authorized", True),
            ("el3_payload_transmit_authorized", True),
            ("isp_write_authorized", True),
            ("hardware_live_attachment_authorized", True),
            ("p186_card_insert_authorized", True),
            ("physical_usb_packets_emitted", 1),
            ("raw_firmware_bytes_leaked", 1),
            ("otp_fuse_touches", 1),
            ("rpmb_counter_increments", 1),
            ("passive_tx_bytes_emitted", 1),
            ("p154_usb_packets_emitted", 1),
            ("p154_iokit_handles_opened", 1),
        ):
            d = copy.deepcopy(self.report_clean.to_dict())
            d[key] = bad_val
            d["milestone193_sha256"] = compute_milestone193_sha256(d)
            res = verify_realhw_milestone193_master_gate(d)
            self.assertFalse(res.valid, msg=f"Should reject breached {key}={bad_val}")
            self.assertFalse(res.safety_redlines_ok)

    def test_42_verifier_forward_compat_and_below_threshold_counts(self) -> None:
        d_high = copy.deepcopy(self.report_clean.to_dict())
        d_high["gate66_total_gates"] = 68
        d_high["gate66_offline_verified"] = 65
        d_high["gate66_simulated_verified"] = 68
        d_high["recovery_pillar_count"] = 27
        d_high["recovery_pillars_passed"] = 27
        d_high["firmware_lab_auditor_count"] = 41
        d_high["firmware_lab_auditors_passed"] = 41
        d_high["vm_coemulation_stage_count"] = 34
        d_high["vm_coemulation_stages_passed"] = 34
        d_high["milestone193_sha256"] = compute_milestone193_sha256(d_high)
        res_high = verify_realhw_milestone193_master_gate(d_high)
        self.assertTrue(res_high.valid, msg=f"errors={res_high.errors}")

        for key, bad_val in (
            ("gate66_total_gates", 65),
            ("gate66_offline_verified", 62),
            ("recovery_pillar_count", 25),
            ("firmware_lab_auditor_count", 39),
            ("vm_coemulation_stage_count", 32),
            ("qemu_rounds_verified", 9),
            ("qemu_runs_verified", 29),
            ("qemu_png_receipts_verified", 19),
            ("qemu_png_max_bytes", PNG_MAX_SIZE_BYTES),
            ("p186_sim_gates_passed", 3),
            ("p186_h0_equals_h3_count", 15),
        ):
            d_low = copy.deepcopy(self.report_clean.to_dict())
            d_low[key] = bad_val
            d_low["milestone193_sha256"] = compute_milestone193_sha256(d_low)
            res_low = verify_realhw_milestone193_master_gate(d_low)
            self.assertFalse(res_low.valid, msg=f"Should fail below/breached {key}={bad_val}")

    def test_43_verifier_rejects_missing_or_duplicate_pillar_and_raw_bytes_repr(self) -> None:
        d_dup = copy.deepcopy(self.report_clean.to_dict())
        d_dup["pillars"][5]["pillar_id"] = "P1"
        d_dup["milestone193_sha256"] = compute_milestone193_sha256(d_dup)
        self.assertFalse(verify_realhw_milestone193_master_gate(d_dup).valid)

        d_raw = copy.deepcopy(self.report_clean.to_dict())
        d_raw["errors"] = ["leaked b'rawbytes' repr"]
        d_raw["milestone193_sha256"] = compute_milestone193_sha256(d_raw)
        self.assertFalse(verify_realhw_milestone193_master_gate(d_raw).valid)

    def test_44_cli_force_clean_room_json_output_and_markdown_out(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            json_path = Path(tmp) / "m193.json"
            md_path = Path(tmp) / "m193.md"
            buf = io.StringIO()
            with mock.patch("sys.stdout", buf):
                rc = fx6_cli_main(
                    [
                        "verify-milestone-193",
                        "--force-clean-room",
                        "--json",
                        "--output",
                        str(json_path),
                        "--markdown-out",
                        str(md_path),
                    ]
                )
            self.assertEqual(rc, 0)
            self.assertTrue(json_path.exists())
            self.assertTrue(md_path.exists())
            parsed = json.loads(buf.getvalue())
            self.assertEqual(parsed["schema_version"], REALHW_MILESTONE193_SCHEMA)
            self.assertEqual(parsed["verification_mode"], "CLEAN_ROOM_SYNTHETIC")
            self.assertTrue(verify_realhw_milestone193_master_gate(parsed).valid)
            self.assertIn("MILESTONE_193_PREBENCH_MASTER_VERIFIED", md_path.read_text(encoding="utf-8"))

    def test_45_cli_clean_room_human_summary_line(self) -> None:
        buf = io.StringIO()
        with mock.patch("sys.stdout", buf):
            rc = fx6_cli_main(["verify-milestone-193", "--force-clean-room"])
        self.assertEqual(rc, 0)
        line = buf.getvalue().strip()
        for token in (
            "status=OK",
            "schema=realhw_milestone193_master_gate_v1",
            "pillars=6/6",
            "gate66=63/66",
            "recovery=26/26",
            "otp=0",
            "rpmb=0",
            "passive_tx=0",
            "auditors=40/40",
            "vm_stages=33/33",
            "h0_eq_h3=16/16",
            "p154_go=True",
            "p186_off=BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT",
            "p186_sim=DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH",
            "qemu=10/10(30/30)",
            "pngs=20/20",
            "emmc_writes_auth=False",
            "spi_nor_auth=False",
            "el3_tx_auth=False",
            "usb_tx=0",
            "leaked=0",
        ):
            self.assertIn(token, line)

    def test_46_live_fault_p2_26pillar_fails_closed(self) -> None:
        rep = build_realhw_milestone193_master_gate_report(
            synthetic_clean_room=True,
            faults=RealHwMilestone193FaultInjection(p2_otp_fuse_touches_override=1),
        )
        self.assertFalse(rep.all_pillars_milestone_ready)
        self.assertEqual(rep.status, STATUS_FAIL_CLOSED)
        self.assertIn("P2", rep.failed_pillar_ids)
        self.assertIn("P6", rep.failed_pillar_ids)

    def test_47_live_fault_p3_40auditor_raw_leak_fails_closed(self) -> None:
        rep = build_realhw_milestone193_master_gate_report(
            synthetic_clean_room=True,
            faults=RealHwMilestone193FaultInjection(p3_hdmi_braw_raw_leaked_override=1),
        )
        self.assertFalse(rep.all_pillars_milestone_ready)
        self.assertEqual(rep.status, STATUS_FAIL_CLOSED)
        self.assertIn("P3", rep.failed_pillar_ids)
        self.assertIn("P6", rep.failed_pillar_ids)

    def test_48_live_fault_p4_33stage_vm_fails_closed(self) -> None:
        rep = build_realhw_milestone193_master_gate_report(
            synthetic_clean_room=True,
            faults=RealHwMilestone193FaultInjection(p4_stage33_ribbon_or_audio_faults=1),
        )
        self.assertFalse(rep.all_pillars_milestone_ready)
        self.assertEqual(rep.status, STATUS_FAIL_CLOSED)
        self.assertIn("P4", rep.failed_pillar_ids)

    def test_49_live_fault_p5_card_insert_appledouble_fails_closed(self) -> None:
        rep = build_realhw_milestone193_master_gate_report(
            synthetic_clean_room=True,
            faults=RealHwMilestone193FaultInjection(p5_inject_p186_appledouble_fault=True),
        )
        self.assertFalse(rep.all_pillars_milestone_ready)
        self.assertEqual(rep.status, STATUS_FAIL_CLOSED)
        self.assertIn("P5", rep.failed_pillar_ids)

    def test_50_live_fault_p6_png_over_28kib_fails_closed(self) -> None:
        rep = build_realhw_milestone193_master_gate_report(
            synthetic_clean_room=True,
            faults=RealHwMilestone193FaultInjection(
                p6_png_size_override_round_num=37,
                p6_png_size_override_bytes=PNG_MAX_SIZE_BYTES + 1,
            ),
        )
        self.assertFalse(rep.all_pillars_milestone_ready)
        self.assertEqual(rep.status, STATUS_FAIL_CLOSED)
        self.assertIn("P6", rep.failed_pillar_ids)

    def test_51_backward_compat_preflight_card_insert_cli_intact(self) -> None:
        buf = io.StringIO()
        with mock.patch("sys.stdout", buf):
            rc = fx6_cli_main(
                ["preflight-card-insert", "--force-clean-room", "--dry-run-simulated"]
            )
        self.assertEqual(rc, 0)
        self.assertIn("go_no_go=DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH", buf.getvalue())

    def test_52_backward_compat_verify_milestone_175_cli_intact(self) -> None:
        buf = io.StringIO()
        with mock.patch("sys.stdout", buf):
            rc = fx6_cli_main(["verify-milestone-175", "--clean-room"])
        self.assertEqual(rc, 0)
        self.assertIn("schema=realhw_milestone175_master_gate_v1", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
