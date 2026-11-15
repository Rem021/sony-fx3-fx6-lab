"""Phase 90 unit tests for Stage-B Milestone 90 Unified 24-Gate + 13-VM + 16-Auditor + Round 16 Master Gate."""

from __future__ import annotations

import copy
import io
import json
import os
from pathlib import Path
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
):
    _cand = str(REPO_ROOT / _rel)
    if _cand not in sys.path:
        sys.path.insert(0, _cand)

import fx6_closure  # noqa: E402
from fx6_closure.__main__ import main as fx6_cli_main  # noqa: E402
from fx6_closure.hardware_readiness_packet import _is_forced_clean_room  # noqa: E402
from fx6_closure.stage_b_milestone90_master_gate import (  # noqa: E402
    CALIBRATION_MUTATION_BYTES,
    CP_MUTATION_BYTES,
    DEFAULT_REPO_ROOT,
    FIRMWARE_LAB_16_AUDITOR_KEYS,
    HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    HARDWARE_LIVE_ATTACHMENT_REQUIREMENTS,
    MILESTONE90_SCHEMA_VERSION,
    OTP_FUSE_TOUCHES,
    P8_CP_MUTATION_FORBIDDEN,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHASE_90_VERSION,
    PILLAR_IDS,
    ROUND16_5TAB_PAIR_KEYS,
    ROUND16_MONITORING_PAIR_KEYS,
    ROUND16_MULTITAB_SIDS,
    ROUND16_RUN_IDS,
    ROUND16_TCMEDIA_PAIR_KEYS,
    RPMB_COUNTER_INCREMENTS,
    STAGE_B_MILESTONE90_SCHEMA,
    STATUS_FAIL_CLOSED,
    STATUS_MILESTONE_READY,
    USB_OR_CAMERA_OPERATIONS,
    VM_COEMULATION_13_STAGE_KEYS,
    WBI_MUTATION_BYTES,
    WBI_P5_WRITE_AND_HIBERNATION_FORBIDDEN,
    Milestone90FaultInjection,
    Milestone90PillarResult,
    StageBMilestone90MasterGateReport,
    _evaluate_pillar_1,
    _evaluate_pillar_2,
    _evaluate_pillar_3,
    _evaluate_pillar_4,
    _evaluate_pillar_5,
    _evaluate_pillar_6,
    _load_round16_summary,
    _worker_domain_2,
    _worker_pillar_1,
    build_stage_b_milestone90_master_gate_report,
    compute_milestone90_sha256,
    render_milestone90_markdown,
    verify_stage_b_milestone90_master_gate,
)
from fx6_closure.stage_b_release_dossier_v3 import (  # noqa: E402
    _worker_pillar_b,
    _worker_pillar_f,
)

_RAW_BYTES_REPR_REGEX = r"(?<![0-9A-Za-z_/.-])b['\"]"


def _make_clean_p2_antirollback_raw() -> dict:
    return {
        "schema": "fx3-antirollback-and-byof-guard-v1",
        "verification_mode": "CLEAN_ROOM_SYNTHETIC",
        "all_passed": True,
        "status": "SAFE_TIER_A_NO_OTP_TOUCH",
        "otp_fuse_touches": 0,
        "rpmb_counter_increments": 0,
        "antirollback_brick_risk": "ZERO_BRICK_RISK",
        "physical_device_writes": 0,
        "persistent_emmc_writes_authorized": False,
        "persistent_write_release": False,
        "allow_boot_partition_targeting": False,
        "allow_destructive_fastboot": False,
        "gold_pair_tier": "TIER_A_GOLD_VERIFIED",
        "gold_pair_compatible": True,
        "fx3_wbi2_sections": 11,
        "fx6_wbi2_sections": 11,
        "downgrade_v205_blocked_code": "BLOCKED_OTP_ROLLBACK",
        "downgrade_v600_blocked_code": "BLOCKED_OTP_ROLLBACK",
        "cross_sku_fx6_nbl_blocked_code": "BLOCKED_CROSS_SKU",
        "cross_sku_fx6_wbi2_blocked_code": "BLOCKED_CROSS_SKU",
        "ext_csd_clean_safe": True,
        "ext_csd_boot_perm_wp_status": "BLOCKED_PERMANENT_EMMC_WP_FUSE_TRAP",
        "ext_csd_user_perm_wp_status": "BLOCKED_PERMANENT_EMMC_WP_FUSE_TRAP",
        "mmc_perm_wp_cmd_status": "BLOCKED_PERMANENT_EMMC_WP_FUSE_TRAP",
        "errors": [],
    }


def _make_clean_p2_tier0_raw() -> dict:
    return {
        "tier0_schema": "fx3-tier0-backup-parity-and-manifest-guard-v1",
        "tier0_all_passed": True,
        "anti_transplant_same_body_allowed": True,
        "anti_transplant_cross_body_blocked": True,
        "heal_1_erasure_passed": True,
        "heal_2_erasures_passed": True,
        "heal_1_silent_bitrot_passed": True,
        "reject_3_losses_passed": True,
        "tier0_physical_device_writes": 0,
        "tier0_persistent_emmc_writes_authorized": False,
        "tier0_donor_p1_sha256": "a" * 64,
        "tier0_donor_p5_wbi2_sha256": "b" * 64,
        "tier0_errors": [],
        "init2_schema": "fx3-init2-escape-watchdog-fat-verifier-v1",
        "init2_all_passed": True,
        "escape_sandbox_passed": True,
        "escape_drill_count": 7,
        "escape_drills_passed": 7,
        "watchdog_suite_passed": True,
        "watchdog_scenario_count": 5,
        "watchdog_scenarios_passed": 5,
        "fat12_audit_passed": True,
        "fat16_audit_passed": True,
        "fat12_atomic_swap_passed": True,
        "fat16_atomic_swap_passed": True,
        "init2_emmc_write_bytes": 0,
        "init2_physical_writes": 0,
        "init2_persistent_emmc_writes_authorized": False,
        "init2_errors": [],
        "cross_body_transplant_rejected_by_guard": False,
    }


def _make_clean_p3_auditors() -> dict:
    aud = {
        k: {"all_checks_passed": True, "report_sha256": "c" * 64}
        for k in FIRMWARE_LAB_16_AUDITOR_KEYS[:14]
    }
    aud["wb_color_matrix_and_look_audit"] = {
        "all_checks_passed": True,
        "calibration_mutation_bytes": 0,
        "cp_mutation_bytes": 0,
        "pillar_d_factory_calibration": {"passed": True},
        "report_sha256": "d" * 64,
    }
    aud["proxy_clipname_and_sidecar_audit"] = {
        "all_checks_passed": True,
        "internal_emmc_clip_writes": 0,
        "c2pa_rq_lic_preserved": True,
        "pillar_1_clipname_proxy": {"passed": True},
        "pillar_2_dual_slot_matrix": {"passed": True},
        "pillar_3_nrtm_xml_sidecar": {"passed": True},
        "report_sha256": "e" * 64,
    }
    aud["assignable_zoom_ciz_and_fn_audit"] = {
        "all_checks_passed": True,
        "bk4_persistent_nvram_writes": 0,
        "null_gpio_faults": 0,
        "persistent_emmc_writes_authorized": False,
        "icx1295_crashed": False,
        "libcamera_crashed": False,
        "pillar_1_assignable_catalog": {"passed": True},
        "pillar_2_zoom_ciz_matrix": {"passed": True},
        "pillar_3_touch_af_desqueeze": {"passed": True},
        "pillar_4_big6_fn_shadow": {"passed": True},
        "report_sha256": "f" * 64,
    }
    aud["falsecolor_lpcm_tc_ub_audit"] = {
        "schema": "fx3-falsecolor-lpcm-tc-ub-v1",
        "all_checks_passed": True,
        "calibration_mutation_bytes": 0,
        "int24_wrap_around_count": 0,
        "bus_contention_count": 0,
        "persistent_emmc_writes_authorized": False,
        "pillar_1_false_color_el_zone": {"passed": True},
        "pillar_2_lpcm_headroom_dsp": {"passed": True},
        "pillar_3_smpte_ub_direction": {"passed": True},
        "pillar_4_zero_mutation_proof": {"passed": True},
        "report_sha256": "e" * 64,
    }
    aud["playback_shotmark_and_ae_audit"] = {
        "schema": "fx3-playback-shotmark-and-ae-v1",
        "all_checks_passed": True,
        "calibration_mutation_bytes": 0,
        "p4_nd_motor_fault_attempts": 0,
        "internal_emmc_format_possible": False,
        "persistent_emmc_writes_authorized": False,
        "pillar_1_playback_thumbnail_firewall": {"passed": True},
        "pillar_2_shotmark_essencemark_xml": {"passed": True},
        "pillar_3_push_auto_iris_ae_shift": {"passed": True},
        "pillar_4_zero_mutation_proof": {"passed": True},
        "report_sha256": "f" * 64,
    }
    return aud


def _make_clean_p4_vm_raw() -> dict:
    vm = {
        "schema": "fx3-vm-coemulation-suite-v1",
        "all_checks_passed": True,
        "audit_digest_sha256": "1" * 64,
        "redlines": {
            "p8_cp_mutation_forbidden": True,
            "cp_mutation_bytes": 0,
            "wbi_mutation_bytes": 0,
            "nvram_persistent_writes": 0,
            "physical_device_writes": 0,
        },
    }
    for sk in VM_COEMULATION_13_STAGE_KEYS:
        vm[sk] = {"all_checks_passed": True}
    vm["stage9_phase67_tc_lens_paint"] = {
        "all_checks_passed": True,
        "nop_count": 0,
        "phase67_audit_digest_sha256": "9" * 64,
    }
    vm["stage10_phase71_dualslot_ups_salvage"] = {
        "all_checks_passed": True,
        "nop_count": 0,
        "rsv_salvageable_frames": 114,
        "rsv_committed_frames": 114,
        "c2pa_license_untouched": True,
        "phase71_audit_digest_sha256": "a" * 64,
        "dualslot_proxy_pipeline": {
            "dram_elastic_fifo_mib": 256,
            "relay_auto_switch": {"dropped_frames": 0, "main_stalled": False},
        },
    }
    vm["stage11_phase78_touchaf_ciz_assignable"] = {
        "all_checks_passed": True,
        "nop_count": 0,
        "cp_mutation_bytes": 0,
        "bk4_persistent_nvram_writes": 0,
        "null_gpio_derefs": 0,
        "mailbox_stalls": 0,
        "persistent_emmc_writes_authorized": False,
        "phase78_audit_digest_sha256": "b" * 64,
    }
    vm["stage12_phase82_camset_lpcm_tcub"] = {
        "all_checks_passed": True,
        "nop_count": 0,
        "cp_mutation_bytes": 0,
        "bk4_persistent_nvram_writes": 0,
        "uart_boot_contention_events": 0,
        "persistent_emmc_writes_authorized": False,
        "phase82_audit_digest_sha256": "a" * 64,
    }
    vm["stage13_phase87_playback_shotmark_dewpoint"] = {
        "all_checks_passed": True,
        "nop_count": 0,
        "cp_mutation_bytes": 0,
        "bk4_persistent_nvram_writes": 0,
        "p1_emmc_mutations": 0,
        "internal_emmc_writes": 0,
        "p4_nd_motor_faults": 0,
        "internal_emmc_format_blocked": True,
        "c2pa_license_untouched": True,
        "persistent_emmc_writes_authorized": False,
        "phase87_audit_digest_sha256": "b" * 64,
    }
    return vm


class TestPhase90MilestoneMasterGate(unittest.TestCase):
    report_primary: StageBMilestone90MasterGateReport
    build_elapsed_s: float
    use_clean_room: bool

    @classmethod
    def setUpClass(cls) -> None:
        cls.use_clean_room = _is_forced_clean_room()
        t0 = time.monotonic()
        cls.report_primary = build_stage_b_milestone90_master_gate_report(
            synthetic_clean_room=True if cls.use_clean_room else None
        )
        cls.build_elapsed_s = time.monotonic() - t0

    # ------------------------------------------------------------------
    # 1. Contract, Performance (< 3.5s), Redlines & Tamper Evidence
    # ------------------------------------------------------------------

    def test_01_public_exports_and_schema_constants(self) -> None:
        self.assertEqual(STAGE_B_MILESTONE90_SCHEMA, "stage_b_milestone90_master_gate_v1")
        self.assertEqual(MILESTONE90_SCHEMA_VERSION, "stage_b_milestone90_master_gate_v1")
        self.assertEqual(PHASE_90_VERSION, "90.0.0")
        self.assertEqual(PILLAR_IDS, ("P1", "P2", "P3", "P4", "P5", "P6"))
        self.assertEqual(len(FIRMWARE_LAB_16_AUDITOR_KEYS), 16)
        self.assertEqual(len(VM_COEMULATION_13_STAGE_KEYS), 13)
        self.assertEqual(len(ROUND16_5TAB_PAIR_KEYS), 10)
        for sym in (
            "STAGE_B_MILESTONE90_SCHEMA",
            "MILESTONE90_PILLAR_IDS",
            "MILESTONE90_PILLAR_SPECS",
            "FIRMWARE_LAB_16_AUDITOR_KEYS",
            "VM_COEMULATION_13_STAGE_KEYS",
            "Milestone90FaultInjection",
            "Milestone90PillarResult",
            "StageBMilestone90MasterGateReport",
            "StageBMilestone90VerifyResult",
            "build_stage_b_milestone90_master_gate_report",
            "compute_milestone90_sha256",
            "render_milestone90_markdown",
            "verify_stage_b_milestone90_master_gate",
        ):
            self.assertTrue(hasattr(fx6_closure, sym), f"Missing package export: {sym}")

    def test_02_milestone90_builds_under_3500ms_and_is_ready(self) -> None:
        self.assertLess(
            self.build_elapsed_s,
            3.5,
            f"Milestone 90 gate build took {self.build_elapsed_s:.3f}s >= 3.5s",
        )
        r = self.report_primary
        self.assertEqual(r.schema_version, "stage_b_milestone90_master_gate_v1")
        self.assertEqual(r.status, STATUS_MILESTONE_READY)
        self.assertTrue(r.all_pillars_milestone_ready)
        self.assertEqual(r.pillar_count, 6)
        self.assertEqual(r.passed_pillar_count, 6)
        self.assertEqual(r.failed_pillar_ids, ())
        self.assertEqual(r.errors, ())

    def test_03_hard_locked_safety_redlines_zero_persistent_write(self) -> None:
        r = self.report_primary
        self.assertTrue(r.o_rdonly_enforced)
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(PERSISTENT_WRITE_RELEASE)
        self.assertFalse(HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        self.assertFalse(r.persistent_emmc_writes_authorized)
        self.assertFalse(r.persistent_write_release)
        self.assertFalse(r.hardware_live_attachment_authorized)
        self.assertGreaterEqual(len(HARDWARE_LIVE_ATTACHMENT_REQUIREMENTS), 3)
        self.assertTrue(P8_CP_MUTATION_FORBIDDEN)
        self.assertTrue(WBI_P5_WRITE_AND_HIBERNATION_FORBIDDEN)
        self.assertTrue(r.p8_cp_mutation_forbidden)
        self.assertTrue(r.wbi_p5_write_and_hibernation_forbidden)
        self.assertEqual(CP_MUTATION_BYTES, 0)
        self.assertEqual(WBI_MUTATION_BYTES, 0)
        self.assertEqual(CALIBRATION_MUTATION_BYTES, 0)
        self.assertEqual(USB_OR_CAMERA_OPERATIONS, 0)
        self.assertEqual(OTP_FUSE_TOUCHES, 0)
        self.assertEqual(RPMB_COUNTER_INCREMENTS, 0)
        self.assertEqual(r.cp_mutation_bytes, 0)
        self.assertEqual(r.wbi_mutation_bytes, 0)
        self.assertEqual(r.calibration_mutation_bytes, 0)
        self.assertEqual(r.usb_or_camera_operations, 0)
        self.assertEqual(r.otp_fuse_touches, 0)
        self.assertEqual(r.rpmb_counter_increments, 0)
        self.assertTrue(r.temp_dir_cleaned)

    def test_04_deterministic_sha256_and_zero_raw_bytes_repr(self) -> None:
        r1 = self.report_primary
        r2_dict = copy.deepcopy(r1.to_dict())
        recomputed = compute_milestone90_sha256(r2_dict)
        self.assertRegex(r1.milestone90_sha256, r"^[0-9a-f]{64}$")
        self.assertEqual(r1.milestone90_sha256, recomputed)

        rendered = r1.to_deterministic_json(indent=2)
        self.assertNotRegex(rendered, _RAW_BYTES_REPR_REGEX)
        parsed = json.loads(rendered)
        self.assertEqual(parsed["milestone90_sha256"], r1.milestone90_sha256)

    def test_05_tamper_evident_verifier_accepts_valid_and_rejects_mutations(self) -> None:
        vr = verify_stage_b_milestone90_master_gate(self.report_primary)
        self.assertTrue(vr.valid)
        self.assertTrue(vr.schema_ok)
        self.assertTrue(vr.digest_matched)
        self.assertTrue(vr.safety_redlines_ok)
        self.assertTrue(vr.all_6_pillars_ok)
        self.assertTrue(vr.all_pillars_milestone_ready)
        self.assertEqual(vr.errors, ())

        # Tamper digest
        bad_digest = copy.deepcopy(self.report_primary.to_dict())
        bad_digest["milestone90_sha256"] = "0" * 64
        self.assertFalse(verify_stage_b_milestone90_master_gate(bad_digest).valid)

        # Tamper schema
        bad_schema = copy.deepcopy(self.report_primary.to_dict())
        bad_schema["schema_version"] = "wrong_schema"
        self.assertFalse(verify_stage_b_milestone90_master_gate(bad_schema).valid)

        # Tamper hard-locked safety flag + recompute SHA-256 -> still fails closed!
        bad_hw = copy.deepcopy(self.report_primary.to_dict())
        bad_hw["persistent_emmc_writes_authorized"] = True
        bad_hw["milestone90_sha256"] = compute_milestone90_sha256(bad_hw)
        res_hw = verify_stage_b_milestone90_master_gate(bad_hw)
        self.assertFalse(res_hw.valid)
        self.assertFalse(res_hw.safety_redlines_ok)

        # Tamper counter + recompute SHA-256 -> still fails closed!
        bad_cnt = copy.deepcopy(self.report_primary.to_dict())
        bad_cnt["gate24_offline_verified"] = 20
        bad_cnt["milestone90_sha256"] = compute_milestone90_sha256(bad_cnt)
        res_cnt = verify_stage_b_milestone90_master_gate(bad_cnt)
        self.assertFalse(res_cnt.valid)
        self.assertFalse(res_cnt.all_pillars_milestone_ready)

        # Non-mapping payload
        self.assertFalse(verify_stage_b_milestone90_master_gate(["bad"]).valid)

    def test_06_mode_and_o_rdonly_enforced_for_round16(self) -> None:
        expected_mode = "CLEAN_ROOM_SYNTHETIC" if self.use_clean_room else "LOCAL_DONOR_O_RDONLY"
        self.assertEqual(self.report_primary.verification_mode, expected_mode)

        open_flags = []
        orig_open = os.open

        def _spy_open(path: object, flags: int, *args: object, **kwargs: object) -> int:
            open_flags.append((str(path), flags))
            return orig_open(path, flags, *args, **kwargs)  # type: ignore[arg-type]

        with mock.patch("os.open", side_effect=_spy_open):
            _load_round16_summary(repo_root=DEFAULT_REPO_ROOT, use_clean_room=self.use_clean_room)
        if not self.use_clean_room:
            self.assertTrue(open_flags)
            self.assertTrue(all((f & os.O_ACCMODE) == os.O_RDONLY for _, f in open_flags))

    # ------------------------------------------------------------------
    # 2. Positive Verification of Pillars P1 .. P6
    # ------------------------------------------------------------------

    def test_07_pillar_sequence_p1_to_p6_complete(self) -> None:
        r = self.report_primary
        self.assertEqual(tuple(p.pillar_id for p in r.pillars), PILLAR_IDS)
        self.assertTrue(all(p.passed and p.status == STATUS_MILESTONE_READY for p in r.pillars))

    def test_08_p1_24gate_g21_xlr_g22_gimbal_g23_dewpoint_tec_g24_pmic_5v(self) -> None:
        p1 = self.report_primary.pillars[0]
        self.assertEqual(p1.pillar_id, "P1")
        self.assertEqual(p1.pillar_name, "SAFETY_24GATE_MASTER_PREFLIGHT")
        ev = p1.evidence
        self.assertEqual(ev["offline_verified_gates"], 21)
        self.assertFalse(ev["offline_ready_for_hardware_attach"])
        self.assertEqual(ev["simulated_verified_gates"], 24)
        self.assertFalse(ev["simulated_ready_for_hardware_attach"])
        self.assertTrue(ev["g21_passed"])
        self.assertTrue(ev["g22_passed"])
        self.assertTrue(ev["g23_passed"])
        self.assertTrue(ev["g23_tec_condensation_safe"])
        self.assertTrue(ev["g23_internal_fan_dewpoint_immune"])
        self.assertTrue(ev["g24_passed"])
        self.assertEqual(ev["g24_pmic_5v_budget_ma"], 900)
        self.assertLessEqual(ev["g24_total_pmic_5v_ma"], 900)
        self.assertTrue(ev["g24_usbc_cable_droop_safe"])
        self.assertTrue(ev["g24_cage_cable_strain_safe"])
        self.assertEqual(ev["g19_ibis_park_opcode"], "0x0400")
        self.assertTrue(ev["g20_rsv_salvage_ok"])

    def test_09_p2_otp_rpmb_extcsd_gf256_tier0_and_sd_escape(self) -> None:
        p2 = self.report_primary.pillars[1]
        self.assertEqual(p2.pillar_id, "P2")
        self.assertEqual(p2.pillar_name, "OTP_RPMB_ANTIROLLBACK_TIER0_GF256_SD_ESCAPE")
        ar = p2.evidence["antirollback"]
        self.assertEqual(ar["otp_fuse_touches"], 0)
        self.assertEqual(ar["rpmb_counter_increments"], 0)
        self.assertEqual(ar["gold_pair_tier"], "TIER_A_GOLD_VERIFIED")
        self.assertTrue(ar["gold_pair_compatible"])
        self.assertEqual(ar["ext_csd_boot_perm_wp_blocked"], "BLOCKED_PERMANENT_EMMC_WP_FUSE_TRAP")
        self.assertEqual(ar["ext_csd_user_perm_wp_blocked"], "BLOCKED_PERMANENT_EMMC_WP_FUSE_TRAP")
        t0 = p2.evidence["tier0_gf256_and_sd_escape"]
        self.assertTrue(t0["gf256_2_erasures_healed"])
        self.assertTrue(t0["gf256_silent_bitrot_healed"])
        self.assertTrue(t0["gf256_3_losses_rejected"])
        self.assertTrue(t0["anti_transplant_cross_body_blocked"])
        self.assertTrue(t0["init2_all_passed"])
        self.assertTrue(t0["fat12_clean_and_swap_ok"])
        self.assertTrue(t0["fat16_clean_and_swap_ok"])
        self.assertEqual(t0["emmc_write_bytes"], 0)

    def test_10_p3_16_firmware_lab_auditors_incl_phase80_and_phase85(self) -> None:
        p3 = self.report_primary.pillars[2]
        self.assertEqual(p3.pillar_id, "P3")
        self.assertEqual(p3.pillar_name, "SIXTEEN_FIRMWARE_LAB_AUDITORS")
        ev = p3.evidence
        self.assertEqual(ev["auditor_count"], 16)
        self.assertEqual(ev["passed_auditor_count"], 16)
        for key in FIRMWARE_LAB_16_AUDITOR_KEYS:
            self.assertTrue(ev["auditor_statuses"][key], f"Auditor {key} failed")
        self.assertTrue(ev["phase80_falsecolor_lpcm_tc_ub_ok"])
        self.assertEqual(ev["phase80_int24_wrap_around_count"], 0)
        self.assertEqual(ev["phase80_bus_contention_count"], 0)
        self.assertTrue(ev["phase85_playback_shotmark_ae_ok"])
        self.assertEqual(ev["phase85_p4_nd_motor_fault_attempts"], 0)
        self.assertFalse(ev["phase85_internal_emmc_format_possible"])
        self.assertEqual(ev["calibration_mutation_bytes"], 0)

    def test_11_p4_13_stage_vm_coemulation_incl_stage12_and_stage13(self) -> None:
        p4 = self.report_primary.pillars[3]
        self.assertEqual(p4.pillar_id, "P4")
        self.assertEqual(p4.pillar_name, "THIRTEEN_STAGE_VM_COEMULATION")
        ev = p4.evidence
        self.assertEqual(ev["stage_count"], 13)
        self.assertEqual(ev["passed_stage_count"], 13)
        for skey in VM_COEMULATION_13_STAGE_KEYS:
            self.assertTrue(ev["stage_statuses"][skey], f"Stage {skey} failed")
        self.assertEqual(ev["cp_mutation_bytes"], 0)
        self.assertEqual(ev["wbi_mutation_bytes"], 0)
        self.assertEqual(ev["bk4_persistent_nvram_writes"], 0)
        self.assertEqual(ev["stage12_uart_boot_contention_events"], 0)
        self.assertTrue(ev["stage13_internal_emmc_format_blocked"])
        self.assertEqual(ev["stage13_p1_emmc_mutations"], 0)
        self.assertEqual(ev["stage13_p4_nd_motor_faults"], 0)
        self.assertTrue(ev["stage13_c2pa_license_untouched"])

    def test_12_p5_round14_and_round16_multitab_5tabs_10pairs_real_kernel(self) -> None:
        p5 = self.report_primary.pillars[4]
        self.assertEqual(p5.pillar_id, "P5")
        self.assertEqual(p5.pillar_name, "ROUND16_MULTITAB_AND_4LANG_KERNEL_CLOSURE")
        ev = p5.evidence
        self.assertEqual(ev["round14_positive_pairs"], 18)
        self.assertEqual(ev["round14_nop_count"], 0)
        self.assertIn("4.9.337-scel+", ev["round16_kernel_version"])
        self.assertEqual(ev["round16_tabs_verified"], 5)
        self.assertEqual(tuple(ev["round16_tab_sids"]), ROUND16_MULTITAB_SIDS)
        self.assertEqual(ev["round16_pairwise_deltas_verified"], 10)
        self.assertEqual(ev["round16_runs_verified"], 4)
        self.assertEqual(tuple(ev["round16_run_ids"]), ROUND16_RUN_IDS)
        self.assertEqual(ev["round16_nop_count"], 0)
        self.assertEqual(ev["round16_crashes"], 0)
        self.assertTrue(ev["round16_stage_b_sha256_verified"])
        for pk in ROUND16_5TAB_PAIR_KEYS:
            self.assertGreater(ev["round16_5tab_pairwise_deltas"][pk], 0)
        for pk in ROUND16_TCMEDIA_PAIR_KEYS:
            self.assertGreater(ev["round16_tcmedia_tchinese_deltas"][pk], 0)
        for pk in ROUND16_MONITORING_PAIR_KEYS:
            self.assertGreater(ev["round16_monitoring_japanese_deltas"][pk], 0)

    def test_13_p5_clean_room_fallback_when_round16_missing(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            empty_root = Path(td)
            p5_syn, meta_syn = _evaluate_pillar_5(
                repo_root=empty_root,
                use_clean_room=True,
                faults=Milestone90FaultInjection(),
            )
            self.assertTrue(p5_syn.passed)
            self.assertEqual(p5_syn.evidence["round16_source"], "CLEAN_ROOM_SYNTHETIC")
            self.assertEqual(meta_syn["round16_tabs_verified"], 5)
            self.assertEqual(meta_syn["round16_pairwise_deltas_verified"], 10)
            with self.assertRaises(FileNotFoundError):
                _load_round16_summary(repo_root=empty_root, use_clean_room=False)

    def test_14_p6_dossier_v3_capstone_and_h0_vs_h2_16surface_immutability(self) -> None:
        p6 = self.report_primary.pillars[5]
        self.assertEqual(p6.pillar_id, "P6")
        self.assertEqual(p6.pillar_name, "DOSSIER_V3_CAPSTONE_AND_H0_VS_H2_IMMUTABILITY")
        ev = p6.evidence
        self.assertEqual(ev["dossier_v3_schema_anchor"], "stage_b_release_dossier_v3")
        self.assertEqual(ev["capstone_22gate_schema_anchor"], "stage_b_capstone_22gate_v1")
        self.assertEqual(ev["capstone_22gate_domain_count"], 7)
        self.assertEqual(ev["audited_item_count"], 16)
        self.assertEqual(ev["matched_item_count"], 16)
        self.assertEqual(ev["drifted_surface_count"], 0)
        self.assertTrue(ev["c2pa_rq_lic_intact"])
        self.assertTrue(ev["spacc_cnflasha_untouched"])
        self.assertEqual(self.report_primary.h0_surface_count, 16)

    def test_15_bilingual_markdown_render_contains_all_6_pillars_and_redlines(self) -> None:
        md = render_milestone90_markdown(self.report_primary)
        self.assertIn("stage_b_milestone90_master_gate_v1", md)
        self.assertIn("MILESTONE_90_SIMULATION_READY", md)
        self.assertIn("21/24", md)
        self.assertIn("16/16", md)
        self.assertIn("13/13", md)
        self.assertIn("0x2f..0x33", md)
        self.assertIn(self.report_primary.milestone90_sha256, md)
        for pid in PILLAR_IDS:
            self.assertIn(f"`{pid}`", md)

    # ------------------------------------------------------------------
    # 3. Per-Pillar Fault Injection (Fail-Closed Negative Drills)
    # ------------------------------------------------------------------

    def test_16_p1_fault_g23_tropical_tec_condensation_fails_closed(self) -> None:
        raw_1 = _worker_pillar_1(
            (
                str(DEFAULT_REPO_ROOT),
                True,
                {
                    "p1_dewpoint_kwargs": {
                        "ambient_temp_c": 31.0,
                        "relative_humidity_pct": 80.0,
                        "cooling_method": "external_peltier_tec",
                        "tec_cold_plate_c": 11.0,
                    }
                },
            )
        )
        p1 = _evaluate_pillar_1(raw_1)
        self.assertFalse(p1.passed)
        self.assertEqual(p1.status, STATUS_FAIL_CLOSED)
        self.assertFalse(p1.evidence["g23_passed"])
        self.assertFalse(p1.evidence["g23_tec_condensation_safe"])
        self.assertTrue(any("G23" in e for e in p1.errors))

    def test_17_p1_fault_g24_pmic_5v_overcurrent_fails_closed(self) -> None:
        raw_1 = _worker_pillar_1(
            (
                str(DEFAULT_REPO_ROOT),
                True,
                {
                    "p1_pmic_usbc_kwargs": {
                        "mishoe_5v_ma": 500.0,
                        "usbc_host_mode_vbus_source": True,
                        "usbc_vbus_5v_ma": 500.0,
                        "external_powered_usbc_pd_hub": False,
                        "cage_cable_clamp_installed": True,
                        "cable_ir_drop_v": 0.12,
                        "usbc_cable_length_m": 0.45,
                        "usbc_cable_emarked": True,
                    }
                },
            )
        )
        p1 = _evaluate_pillar_1(raw_1)
        self.assertFalse(p1.passed)
        self.assertFalse(p1.evidence["g24_passed"])
        self.assertGreater(p1.evidence["g24_total_pmic_5v_ma"], 900.0)
        self.assertTrue(any("G24" in e for e in p1.errors))

    def test_18_p1_fault_g24_unclamped_cable_and_ir_drop_fails_closed(self) -> None:
        raw_1 = _worker_pillar_1(
            (
                str(DEFAULT_REPO_ROOT),
                True,
                {
                    "p1_pmic_usbc_kwargs": {
                        "mishoe_5v_ma": 350.0,
                        "usbc_host_mode_vbus_source": True,
                        "usbc_vbus_5v_ma": 400.0,
                        "external_powered_usbc_pd_hub": True,
                        "usbc_cable_attached": True,
                        "cage_cable_clamp_installed": False,
                        "cable_ir_drop_v": 0.90,
                        "usbc_cable_length_m": 3.0,
                        "usbc_cable_emarked": False,
                    }
                },
            )
        )
        p1 = _evaluate_pillar_1(raw_1)
        self.assertFalse(p1.passed)
        self.assertFalse(p1.evidence["g24_passed"])
        self.assertFalse(p1.evidence["g24_cage_cable_strain_safe"])
        self.assertFalse(p1.evidence["g24_usbc_cable_droop_safe"])

    def test_19_p1_fault_g21_xlr_48v_and_g22_gimbal_fails_closed(self) -> None:
        raw_xlr = _worker_pillar_1(
            (
                str(DEFAULT_REPO_ROOT),
                True,
                {
                    "p1_xlr_kwargs": {
                        "channel_id": "INPUT1",
                        "input_mode": "MIC+48V",
                        "source_type": "PASSIVE_RIBBON",
                        "device_label": "Coles 4038",
                        "cloudlifter_or_transformer_isolated": False,
                    }
                },
            )
        )
        p1_xlr = _evaluate_pillar_1(raw_xlr)
        self.assertFalse(p1_xlr.passed)
        self.assertFalse(p1_xlr.evidence["g21_passed"])

        raw_gimbal = _worker_pillar_1(
            (
                str(DEFAULT_REPO_ROOT),
                True,
                {"p1_gimbal_kwargs": {"usb_c_crsdk_active": True, "multiport_rss_active": True}},
            )
        )
        p1_gim = _evaluate_pillar_1(raw_gimbal)
        self.assertFalse(p1_gim.passed)
        self.assertFalse(p1_gim.evidence["g22_passed"])

    def test_20_p1_fault_persistent_write_request_fails_closed(self) -> None:
        raw_1 = _worker_pillar_1(
            (str(DEFAULT_REPO_ROOT), True, {"p1_request_persistent_writes": True})
        )
        p1 = _evaluate_pillar_1(raw_1)
        self.assertFalse(p1.passed)
        self.assertFalse(p1.evidence["persistent_emmc_writes_authorized"])
        self.assertFalse(p1.evidence["persistent_write_release"])

    def test_21_p2_fault_otp_downgrade_and_cross_sku_fails_closed(self) -> None:
        raw_ar = _worker_domain_2(
            (True, {"d2_otp_downgrade_version": "v6.00", "d2_inject_cross_sku_target": "ILME-FX30"})
        )
        p2, _ = _evaluate_pillar_2(
            raw_ar,
            _make_clean_p2_tier0_raw(),
            Milestone90FaultInjection(
                p2_otp_downgrade_version="v6.00",
                p2_inject_cross_sku_target="ILME-FX30",
            ),
        )
        self.assertFalse(p2.passed)
        self.assertTrue(any("downgrade" in e.lower() for e in p2.errors))
        self.assertTrue(any("cross-sku" in e.lower() for e in p2.errors))

    def test_22_p2_fault_ext_csd_perm_wp_fuse_trap_fails_closed(self) -> None:
        raw_ar = _worker_domain_2((True, {"d2_inject_ext_csd_perm_wp": True}))
        p2, _ = _evaluate_pillar_2(
            raw_ar,
            _make_clean_p2_tier0_raw(),
            Milestone90FaultInjection(p2_inject_ext_csd_perm_wp=True),
        )
        self.assertFalse(p2.passed)
        self.assertTrue(any("EXT_CSD" in e for e in p2.errors))

    def test_23_p2_fault_otp_rpmb_nonzero_override_fails_closed(self) -> None:
        p2, meta_2 = _evaluate_pillar_2(
            _make_clean_p2_antirollback_raw(),
            _make_clean_p2_tier0_raw(),
            Milestone90FaultInjection(
                p2_otp_fuse_touches_override=1,
                p2_rpmb_increments_override=1,
            ),
        )
        self.assertFalse(p2.passed)
        self.assertEqual(meta_2["otp_fuse_touches"], 1)
        self.assertEqual(meta_2["rpmb_counter_increments"], 1)

    def test_24_p2_fault_gf256_3loss_quorum_and_cross_body_cnflasha_fails_closed(self) -> None:
        raw_t0 = _worker_pillar_b((True, {"pillar_b_inject_cross_body_cnflasha_transplant": True}))
        p2, _ = _evaluate_pillar_2(
            _make_clean_p2_antirollback_raw(),
            raw_t0,
            Milestone90FaultInjection(
                p2_inject_cross_body_cnflasha_transplant=True,
                p2_inject_gf256_quorum_loss=True,
            ),
        )
        self.assertFalse(p2.passed)
        self.assertTrue(any("GF(256)" in e for e in p2.errors))

    def test_25_p2_fault_init2_escape_failure_fails_closed(self) -> None:
        p2, _ = _evaluate_pillar_2(
            _make_clean_p2_antirollback_raw(),
            _make_clean_p2_tier0_raw(),
            Milestone90FaultInjection(p2_inject_init2_escape_fault=True),
        )
        self.assertFalse(p2.passed)
        self.assertTrue(any("init2" in e.lower() for e in p2.errors))

    def test_26_p3_fault_phase80_int24_wrap_and_bus_contention_fails_closed(self) -> None:
        p3, _ = _evaluate_pillar_3(
            _make_clean_p3_auditors(),
            Milestone90FaultInjection(
                p3_int24_wrap_around_count=1,
                p3_bus_contention_count=2,
            ),
        )
        self.assertFalse(p3.passed)
        self.assertTrue(any("int24_wrap_around_count" in e for e in p3.errors))
        self.assertTrue(any("bus_contention_count" in e for e in p3.errors))

    def test_27_p3_fault_phase85_nd_motor_and_emmc_p1_format_attempt_fails_closed(self) -> None:
        p3, _ = _evaluate_pillar_3(
            _make_clean_p3_auditors(),
            Milestone90FaultInjection(
                p3_p4_nd_motor_fault_attempts=1,
                p3_inject_internal_emmc_format_attempt=True,
            ),
        )
        self.assertFalse(p3.passed)
        self.assertTrue(any("p4_nd_motor_fault_attempts" in e for e in p3.errors))
        self.assertTrue(any("eMMC p1 format attempt" in e for e in p3.errors))

    def test_28_p3_fault_calibration_mutation_and_bk4_nvram_fails_closed(self) -> None:
        p3, _ = _evaluate_pillar_3(
            _make_clean_p3_auditors(),
            Milestone90FaultInjection(
                p3_calibration_mutation_bytes=4,
                p3_bk4_persistent_nvram_writes=1,
                p3_inject_legacy_sq_big6_block=True,
            ),
        )
        self.assertFalse(p3.passed)
        self.assertTrue(any("calibration_mutation_bytes" in e for e in p3.errors))
        self.assertTrue(any("bk4_persistent_nvram_writes" in e for e in p3.errors))

    def test_29_p4_fault_stage13_p1_format_attempt_and_nd_motor_fails_closed(self) -> None:
        p4, _ = _evaluate_pillar_4(
            _make_clean_p4_vm_raw(),
            Milestone90FaultInjection(
                p4_stage13_p1_emmc_format_attempt=True,
                p4_stage13_p4_nd_motor_faults=1,
            ),
        )
        self.assertFalse(p4.passed)
        self.assertTrue(any("Stage 13 p1 format attempt" in e for e in p4.errors))
        self.assertTrue(any("p4_nd_motor_faults" in e for e in p4.errors))

    def test_30_p4_fault_cp_mutation_and_stage12_uart_contention_fails_closed(self) -> None:
        p4, _ = _evaluate_pillar_4(
            _make_clean_p4_vm_raw(),
            Milestone90FaultInjection(
                p4_cp_mutation_bytes=16,
                p4_bk4_persistent_nvram_writes=2,
                p4_stage12_uart_contention_events=1,
            ),
        )
        self.assertFalse(p4.passed)
        self.assertTrue(any("cp_mutation_bytes" in e for e in p4.errors))
        self.assertTrue(any("uart_cont" in e for e in p4.errors))

    def test_31_p4_fault_stage10_relay_drop_and_stage11_nop_fails_closed(self) -> None:
        p4, _ = _evaluate_pillar_4(
            _make_clean_p4_vm_raw(),
            Milestone90FaultInjection(
                p4_stage10_dropped_frames=1,
                p4_stage11_nop_count=1,
                p4_stage11_null_gpio_derefs=1,
            ),
        )
        self.assertFalse(p4.passed)
        self.assertTrue(any("Stage 10 Dual-Slot Relay" in e for e in p4.errors))
        self.assertTrue(any("Stage 11" in e for e in p4.errors))

    def test_32_p5_fault_round16_zero_tab_pair_and_zero_tcmedia_pair_fails_closed(self) -> None:
        p5, _ = _evaluate_pillar_5(
            repo_root=DEFAULT_REPO_ROOT,
            use_clean_room=True,
            faults=Milestone90FaultInjection(
                p5_round16_zero_tab_pair=ROUND16_5TAB_PAIR_KEYS[-1],
                p5_round16_zero_tcmedia_pair=ROUND16_TCMEDIA_PAIR_KEYS[0],
                p5_round16_zero_monitoring_pair=ROUND16_MONITORING_PAIR_KEYS[0],
            ),
        )
        self.assertFalse(p5.passed)
        self.assertEqual(p5.evidence["round16_pairwise_deltas_verified"], 9)
        self.assertTrue(any("Status Check 5-tab pair" in e for e in p5.errors))
        self.assertTrue(any("TC/Media TChinese" in e for e in p5.errors))
        self.assertTrue(any("Monitoring Japanese" in e for e in p5.errors))

    def test_33_p5_fault_round16_nop_crash_and_manifest_count_fails_closed(self) -> None:
        p5, _ = _evaluate_pillar_5(
            repo_root=DEFAULT_REPO_ROOT,
            use_clean_room=True,
            faults=Milestone90FaultInjection(
                p5_round14_nop_count=1,
                p5_round16_nop_count=1,
                p5_round16_crashes=1,
                p5_round16_manifest_count_override=12,
            ),
        )
        self.assertFalse(p5.passed)
        self.assertTrue(any("nop_count" in e for e in p5.errors))
        self.assertTrue(any("crashes" in e for e in p5.errors))
        self.assertTrue(any("manifest count" in e for e in p5.errors))

    def test_34_p6_fault_h0_vs_h2_surface_drift_and_tamper_fails_closed(self) -> None:
        raw_6 = _worker_pillar_f(
            (str(DEFAULT_REPO_ROOT), str(DEFAULT_REPO_ROOT), True, "p2_backup_bin")
        )
        p6, _ = _evaluate_pillar_6(
            raw_6,
            Milestone90FaultInjection(
                p6_drift_surface="p2_backup_bin",
                p6_tamper_negative_control=True,
            ),
        )
        self.assertFalse(p6.passed)
        self.assertEqual(p6.evidence["drifted_surface_count"], 1)

    # ------------------------------------------------------------------
    # 4. CLI Entry Point Tests
    # ------------------------------------------------------------------

    def test_35_cli_verify_milestone_90_json_and_markdown_out(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            out_json = Path(td) / "milestone90.json"
            out_md = Path(td) / "milestone90.md"
            buf = io.StringIO()
            with mock.patch(
                "fx6_closure.stage_b_milestone90_master_gate.build_stage_b_milestone90_master_gate_report",
                return_value=self.report_primary,
            ), mock.patch("sys.stdout", buf):
                rc = fx6_cli_main(
                    [
                        "verify-milestone-90",
                        "--clean-room",
                        "--json",
                        "--output",
                        str(out_json),
                        "--markdown-out",
                        str(out_md),
                    ]
                )
            self.assertEqual(rc, 0)
            self.assertTrue(out_json.is_file())
            self.assertTrue(out_md.is_file())
            payload = json.loads(buf.getvalue())
            self.assertEqual(payload["schema_version"], "stage_b_milestone90_master_gate_v1")
            self.assertEqual(payload["milestone90_sha256"], self.report_primary.milestone90_sha256)
            self.assertIn("MILESTONE_90_SIMULATION_READY", out_md.read_text(encoding="utf-8"))

    def test_36_cli_verify_milestone_90_exits_1_on_fail_closed_gate(self) -> None:
        bad_report = copy.deepcopy(self.report_primary.to_dict())
        bad_report["all_pillars_milestone_ready"] = False
        bad_report["status"] = STATUS_FAIL_CLOSED
        bad_report["milestone90_sha256"] = compute_milestone90_sha256(bad_report)

        class _FakeBadReport:
            def __init__(self, d: dict) -> None:
                self._d = d
                self.all_pillars_milestone_ready = False
                self.schema_version = d["schema_version"]
                self.verification_mode = d["verification_mode"]
                self.passed_pillar_count = 5
                self.pillar_count = 6
                self.gate24_offline_verified = 21
                self.gate24_simulated_verified = 24
                self.otp_fuse_touches = 0
                self.rpmb_counter_increments = 0
                self.firmware_lab_auditors_passed = 16
                self.firmware_lab_auditor_count = 16
                self.vm_coemulation_stages_passed = 13
                self.vm_coemulation_stage_count = 13
                self.round14_positive_pairs = 18
                self.round16_tabs_verified = 5
                self.round16_pairwise_deltas_verified = 10
                self.round16_runs_verified = 4
                self.drifted_surface_count = 0
                self.h0_surface_count = 16
                self.hardware_live_attachment_authorized = False
                self.persistent_emmc_writes_authorized = False
                self.milestone90_sha256 = d["milestone90_sha256"]

            def to_dict(self) -> dict:
                return self._d

            def to_deterministic_json(self, indent: int = 2) -> str:
                return json.dumps(self._d, indent=indent, sort_keys=True) + "\n"

        buf = io.StringIO()
        with mock.patch(
            "fx6_closure.stage_b_milestone90_master_gate.build_stage_b_milestone90_master_gate_report",
            return_value=_FakeBadReport(bad_report),
        ), mock.patch("sys.stdout", buf):
            rc = fx6_cli_main(["verify-milestone-90", "--clean-room"])
        self.assertEqual(rc, 1)
        self.assertIn("status=FAILED", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
