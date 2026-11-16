"""Phase 110 unit tests for Stage-B Milestone Phase 110 Century+10 6-Pillar Master Gate."""

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
from fx6_closure.stage_b_milestone110_master_gate import (  # noqa: E402
    CALIBRATION_MUTATION_BYTES,
    CP_MUTATION_BYTES,
    DEFAULT_REPO_ROOT,
    FIRMWARE_LAB_20_AUDITOR_KEYS,
    HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    HARDWARE_LIVE_ATTACHMENT_REQUIREMENTS,
    MILESTONE110_SCHEMA_VERSION,
    OTP_FUSE_TOUCHES,
    P8_CP_MUTATION_FORBIDDEN,
    PASSIVE_TX_BYTES_EMITTED,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHASE_110_VERSION,
    PILLAR_IDS,
    RECOVERY_10_PILLAR_IDS,
    ROUND17_MULTITAB_SIDS,
    ROUND17_RUN_IDS,
    ROUND19_11CAT_NAMES,
    ROUND19_11CAT_PAIR_KEYS,
    ROUND19_RUN_IDS,
    RPMB_COUNTER_INCREMENTS,
    STAGE_B_MILESTONE110_SCHEMA,
    STATUS_FAIL_CLOSED,
    STATUS_MILESTONE_READY,
    USB_OR_CAMERA_OPERATIONS,
    VM_COEMULATION_18_STAGE_KEYS,
    WBI_MUTATION_BYTES,
    WBI_P5_WRITE_AND_HIBERNATION_FORBIDDEN,
    Milestone110FaultInjection,
    Milestone110PillarResult,
    StageBMilestone110MasterGateReport,
    _evaluate_pillar_1,
    _evaluate_pillar_2,
    _evaluate_pillar_3,
    _evaluate_pillar_4,
    _evaluate_pillar_5,
    _evaluate_pillar_6,
    _load_round17_summary,
    _load_round19_summary,
    _worker_domain_2,
    _worker_pillar_1,
    build_stage_b_milestone110_master_gate_report,
    compute_milestone110_sha256,
    render_milestone110_markdown,
    verify_stage_b_milestone110_master_gate,
)
from fx6_closure.stage_b_release_dossier_v3 import (  # noqa: E402
    _worker_pillar_b,
    _worker_pillar_f,
)

_RAW_BYTES_REPR_REGEX = r"(?<![0-9A-Za-z_/.-])b['\"]"


def _make_clean_p2_master_raw() -> dict:
    return {
        "schema": "fx3-recovery-master-suite-v1",
        "verification_mode": "CLEAN_ROOM_SYNTHETIC",
        "all_passed": True,
        "status": "RECOVERY_MASTER_7PILLAR_VERIFIED_SAFE",
        "pillar_count": 7,
        "pillars_passed": 7,
        "pillar_statuses": {k: True for k in RECOVERY_10_PILLAR_IDS[:7]},
        "uart_scenarios_total": 10,
        "uart_scenarios_passed": 10,
        "uart_all_passed": True,
        "passive_tx_bytes_emitted": 0,
        "physical_device_writes": 0,
        "persistent_emmc_writes_authorized": False,
        "persistent_write_release": False,
        "allow_boot_partition_targeting": False,
        "allow_destructive_fastboot": False,
        "recovery_master_sha256": "1" * 64,
        "errors": [],
    }


def _make_clean_p2_p8_p10_raw() -> dict:
    return {
        "p8_gpt_rpmb": {
            "schema": "fx3-gpt-rpmb-and-rescue-bundle-v1",
            "all_passed": True,
            "status": "VERIFIED_GPT_RPMB_RESCUE_SAFE",
            "gpt_heal_backup_ok": True,
            "gpt_heal_primary_ok": True,
            "rpmb_authenticated_write_passed": True,
            "sd_rescue_ok": True,
            "stage_b_zero_rpmb_ok": True,
            "otp_fuse_touches": 0,
            "rpmb_writes_emitted": 0,
            "passive_tx_bytes_emitted": 0,
            "physical_device_writes": 0,
            "persistent_emmc_writes_authorized": False,
            "suite_sha256": "2" * 64,
            "errors": [],
        },
        "p9_ramdisk_emmc_health": {
            "schema": "fx3-ramdisk-overlay-and-emmc-health-v1",
            "all_passed": True,
            "status": "VERIFIED_RAMDISK_OVERLAY_EMMC_HEALTH_SAFE",
            "stage_b_containment_ready": True,
            "cpio_reject_traversal_passed": True,
            "cpio_reject_setuid_passed": True,
            "emmc_reject_pre_eol_urgent_passed": True,
            "emmc_reject_lifetime_gt80_passed": True,
            "mount_reject_rw_mmcblk_passed": True,
            "otp_fuse_touches": 0,
            "passive_tx_bytes_emitted": 0,
            "physical_device_writes": 0,
            "persistent_emmc_writes_authorized": False,
            "suite_sha256": "3" * 64,
            "errors": [],
        },
        "p10_fdt_bootargs_kernel": {
            "schema": "fx3-fdt-bootargs-and-kernel-v1",
            "all_passed": True,
            "status": "VERIFIED_FDT_BOOTARGS_AND_KERNEL_SAFE",
            "stage_b_boot_gate_ready": True,
            "bootargs_reject_rw_emmc_passed": True,
            "bootargs_reject_nowatchdog_passed": True,
            "kernel_reject_fx6_transplant_passed": True,
            "otp_fuse_touches": 0,
            "passive_tx_bytes_emitted": 0,
            "physical_device_writes": 0,
            "persistent_emmc_writes_authorized": False,
            "suite_sha256": "4" * 64,
            "errors": [],
        },
    }


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
        for k in FIRMWARE_LAB_20_AUDITOR_KEYS[:14]
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
        "report_sha256": "1" * 64,
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
        "report_sha256": "2" * 64,
    }
    aud["metadata_gyro_catalyst_and_anamorphic_audit"] = {
        "schema": "fx3-metadata-gyro-catalyst-and-anamorphic-v1",
        "all_checks_passed": True,
        "imu_calibration_mutation_bytes": 0,
        "cp_mutation_bytes": 0,
        "persistent_emmc_writes_authorized": False,
        "report_sha256": "3" * 64,
    }
    aud["interval_cache_and_ftp_audit"] = {
        "schema": "fx3-interval-cache-and-ftp-v1",
        "all_checks_passed": True,
        "calibration_mutation_bytes": 0,
        "emmc_mutation_bytes": 0,
        "persistent_emmc_writes_authorized": False,
        "report_sha256": "4" * 64,
    }
    aud["lut3d_cube_tetrahedral_and_sdi_hdmi_audit"] = {
        "schema": "fx3-lut3d-cube-tetrahedral-and-sdi-hdmi-v1",
        "all_checks_passed": True,
        "calibration_mutation_bytes": 0,
        "emmc_mutation_bytes": 0,
        "persistent_emmc_writes_authorized": False,
        "report_sha256": "5" * 64,
    }
    aud["c2pa_lens_shading_and_mc_fleet_audit"] = {
        "schema": "fx3-c2pa-lens-shading-and-mc-fleet-v1",
        "all_checks_passed": True,
        "pillar_4_factory_shading_immutability": {
            "passed": True,
            "calibration_mutation_bytes": 0,
            "emmc_mutation_bytes": 0,
            "bit_exact_preservation_verified": True,
            "persistent_emmc_writes_authorized": False,
        },
        "report_sha256": "6" * 64,
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
    for sk in VM_COEMULATION_18_STAGE_KEYS:
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
        "phase82_audit_digest_sha256": "c" * 64,
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
        "phase87_audit_digest_sha256": "d" * 64,
    }
    vm["stage14_phase91_gyroflow_rtmd_anamorphic"] = {
        "all_checks_passed": True,
        "nop_count": 0,
        "cp_mutation_bytes": 0,
        "stock_cp_fault_count": 0,
        "phase91_audit_digest_sha256": "e" * 64,
    }
    vm["stage15_phase96_interval_cache_ftp_fan"] = {
        "all_checks_passed": True,
        "nop_count": 0,
        "wf12_00342260_hits": 0,
        "emmc_partition_mutations": 0,
        "phase96_audit_digest_sha256": "f" * 64,
    }
    vm["stage16_phase99_lut3d_subzero_sdi"] = {
        "all_checks_passed": True,
        "nop_count": 0,
        "lithium_plating_events": 0,
        "sdi_transceiver_faults": 0,
        "dropped_rec_triggers": 0,
        "phase99_audit_digest_sha256": "0" * 64,
    }
    vm["stage17_phase103_emi_exfat_endurance"] = {
        "all_checks_passed": True,
        "nop_count": 0,
        "emmc_sector_writes": 0,
        "emmc_wear_level_increments": 0,
        "cxd90057_gpio_damage_events": 0,
        "phase103_audit_digest_sha256": "1" * 64,
    }
    vm["stage18_phase107_c2pa_shading_mcfleet_ovp"] = {
        "all_checks_passed": True,
        "nop_count": 0,
        "cnflasha_mutation_bytes": 0,
        "private_key_reads": 0,
        "private_key_exports": 0,
        "wf12_00342260_hits": 0,
        "cxd90057_pmic_damage_events": 0,
        "emount_flange_damage_events": 0,
        "persistent_emmc_writes_authorized": False,
        "phase107_audit_digest_sha256": "2" * 64,
    }
    return vm


class TestPhase110MilestoneMasterGate(unittest.TestCase):
    report_primary: StageBMilestone110MasterGateReport
    build_elapsed_s: float
    use_clean_room: bool

    @classmethod
    def setUpClass(cls) -> None:
        cls.use_clean_room = _is_forced_clean_room()
        t0 = time.monotonic()
        cls.report_primary = build_stage_b_milestone110_master_gate_report(
            synthetic_clean_room=True if cls.use_clean_room else None
        )
        cls.build_elapsed_s = time.monotonic() - t0

    # ------------------------------------------------------------------
    # 1. Contract, Performance (< 2.5s), Redlines & Tamper Evidence
    # ------------------------------------------------------------------

    def test_01_public_exports_and_schema_constants(self) -> None:
        self.assertEqual(STAGE_B_MILESTONE110_SCHEMA, "stage_b_milestone110_master_gate_v1")
        self.assertEqual(MILESTONE110_SCHEMA_VERSION, "stage_b_milestone110_master_gate_v1")
        self.assertEqual(PHASE_110_VERSION, "110.0.0")
        self.assertEqual(PILLAR_IDS, ("P1", "P2", "P3", "P4", "P5", "P6"))
        self.assertEqual(len(RECOVERY_10_PILLAR_IDS), 10)
        self.assertEqual(len(FIRMWARE_LAB_20_AUDITOR_KEYS), 20)
        self.assertEqual(len(VM_COEMULATION_18_STAGE_KEYS), 18)
        self.assertEqual(len(ROUND17_MULTITAB_SIDS), 10)
        self.assertEqual(len(ROUND19_11CAT_NAMES), 11)
        self.assertEqual(len(ROUND19_11CAT_PAIR_KEYS), 55)
        for sym in (
            "STAGE_B_MILESTONE110_SCHEMA",
            "MILESTONE110_SCHEMA_VERSION",
            "MILESTONE110_PILLAR_IDS",
            "MILESTONE110_PILLAR_SPECS",
            "RECOVERY_10_PILLAR_IDS",
            "FIRMWARE_LAB_20_AUDITOR_KEYS",
            "VM_COEMULATION_18_STAGE_KEYS",
            "ROUND17_MULTITAB_SIDS",
            "ROUND19_11CAT_NAMES",
            "ROUND19_11CAT_PAIR_KEYS",
            "STATUS_MILESTONE110_READY",
            "Milestone110FaultInjection",
            "Milestone110PillarResult",
            "StageBMilestone110MasterGateReport",
            "StageBMilestone110VerifyResult",
            "build_stage_b_milestone110_master_gate_report",
            "compute_milestone110_sha256",
            "render_milestone110_markdown",
            "verify_stage_b_milestone110_master_gate",
        ):
            self.assertTrue(hasattr(fx6_closure, sym), f"Missing package export: {sym}")

    def test_02_milestone110_builds_under_2500ms_and_is_ready(self) -> None:
        budget_s = 15.0 if os.environ.get("GITHUB_ACTIONS") == "true" else 2.5
        self.assertLess(
            self.build_elapsed_s,
            budget_s,
            f"Milestone 110 gate build took {self.build_elapsed_s:.3f}s >= {budget_s}s",
        )
        r = self.report_primary
        self.assertEqual(r.schema_version, "stage_b_milestone110_master_gate_v1")
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
        self.assertEqual(PASSIVE_TX_BYTES_EMITTED, 0)
        self.assertEqual(r.cp_mutation_bytes, 0)
        self.assertEqual(r.wbi_mutation_bytes, 0)
        self.assertEqual(r.calibration_mutation_bytes, 0)
        self.assertEqual(r.usb_or_camera_operations, 0)
        self.assertEqual(r.otp_fuse_touches, 0)
        self.assertEqual(r.rpmb_counter_increments, 0)
        self.assertEqual(r.passive_tx_bytes_emitted, 0)
        self.assertTrue(r.temp_dir_cleaned)

    def test_04_deterministic_sha256_and_zero_raw_bytes_repr(self) -> None:
        r1 = self.report_primary
        r2_dict = copy.deepcopy(r1.to_dict())
        recomputed = compute_milestone110_sha256(r2_dict)
        self.assertRegex(r1.milestone110_sha256, r"^[0-9a-f]{64}$")
        self.assertEqual(r1.milestone110_sha256, recomputed)

        rendered = r1.to_deterministic_json(indent=2)
        self.assertNotRegex(rendered, _RAW_BYTES_REPR_REGEX)
        parsed = json.loads(rendered)
        self.assertEqual(parsed["milestone110_sha256"], r1.milestone110_sha256)

    def test_05_tamper_evident_verifier_accepts_valid_and_rejects_mutations(self) -> None:
        vr = verify_stage_b_milestone110_master_gate(self.report_primary)
        self.assertTrue(vr.valid)
        self.assertTrue(vr.schema_ok)
        self.assertTrue(vr.digest_matched)
        self.assertTrue(vr.safety_redlines_ok)
        self.assertTrue(vr.all_6_pillars_ok)
        self.assertTrue(vr.all_pillars_milestone_ready)
        self.assertEqual(vr.errors, ())

        # Tamper digest
        bad_digest = copy.deepcopy(self.report_primary.to_dict())
        bad_digest["milestone110_sha256"] = "0" * 64
        self.assertFalse(verify_stage_b_milestone110_master_gate(bad_digest).valid)

        # Tamper schema
        bad_schema = copy.deepcopy(self.report_primary.to_dict())
        bad_schema["schema_version"] = "wrong_schema"
        self.assertFalse(verify_stage_b_milestone110_master_gate(bad_schema).valid)

        # Tamper hard-locked safety flag + recompute SHA-256 -> still fails closed
        for flag, val in (
            ("persistent_emmc_writes_authorized", True),
            ("passive_tx_bytes_emitted", 1),
            ("otp_fuse_touches", 1),
        ):
            bad_hw = copy.deepcopy(self.report_primary.to_dict())
            bad_hw[flag] = val
            bad_hw["milestone110_sha256"] = compute_milestone110_sha256(bad_hw)
            res_hw = verify_stage_b_milestone110_master_gate(bad_hw)
            self.assertFalse(res_hw.valid)
            self.assertFalse(res_hw.safety_redlines_ok)

        # Tamper threshold counters + recompute SHA-256 -> still fails closed
        for cnt_key, cnt_val in (
            ("gate32_offline_verified", 28),
            ("recovery_pillar_count", 9),
            ("firmware_lab_auditor_count", 19),
            ("vm_coemulation_stage_count", 17),
            ("round17_pairwise_deltas_verified", 44),
            ("round19_pairwise_deltas_verified", 54),
        ):
            bad_cnt = copy.deepcopy(self.report_primary.to_dict())
            bad_cnt[cnt_key] = cnt_val
            bad_cnt["milestone110_sha256"] = compute_milestone110_sha256(bad_cnt)
            res_cnt = verify_stage_b_milestone110_master_gate(bad_cnt)
            self.assertFalse(res_cnt.valid, f"Tampered {cnt_key}={cnt_val} unexpectedly accepted")
            self.assertFalse(res_cnt.all_pillars_milestone_ready)

        # Non-mapping payload
        self.assertFalse(verify_stage_b_milestone110_master_gate(["bad"]).valid)

    def test_06_mode_and_o_rdonly_enforced_for_round17_and_round19(self) -> None:
        expected_mode = "CLEAN_ROOM_SYNTHETIC" if self.use_clean_room else "LOCAL_DONOR_O_RDONLY"
        self.assertEqual(self.report_primary.verification_mode, expected_mode)

        open_flags = []
        orig_open = os.open

        def _spy_open(path: object, flags: int, *args: object, **kwargs: object) -> int:
            open_flags.append((str(path), flags))
            return orig_open(path, flags, *args, **kwargs)  # type: ignore[arg-type]

        with mock.patch("os.open", side_effect=_spy_open):
            _load_round17_summary(repo_root=DEFAULT_REPO_ROOT, use_clean_room=self.use_clean_room)
            _load_round19_summary(repo_root=DEFAULT_REPO_ROOT, use_clean_room=self.use_clean_room)
        if not self.use_clean_room:
            self.assertGreaterEqual(len(open_flags), 2)
            self.assertTrue(all((f & os.O_ACCMODE) == os.O_RDONLY for _, f in open_flags))

    # ------------------------------------------------------------------
    # 2. Positive Verification of Pillars P1 .. P6
    # ------------------------------------------------------------------

    def test_07_pillar_sequence_p1_to_p6_complete(self) -> None:
        r = self.report_primary
        self.assertEqual(tuple(p.pillar_id for p in r.pillars), PILLAR_IDS)
        self.assertTrue(all(p.passed and p.status == STATUS_MILESTONE_READY for p in r.pillars))

    def test_08_p1_32gate_g25_to_g30_g31_cantilever_and_g32_dummy_battery(self) -> None:
        p1 = self.report_primary.pillars[0]
        self.assertEqual(p1.pillar_id, "P1")
        self.assertEqual(p1.pillar_name, "SAFETY_32GATE_MASTER_PREFLIGHT")
        ev = p1.evidence
        self.assertGreaterEqual(ev["total_gates"], 32)
        self.assertGreaterEqual(ev["offline_verified_gates"], 29)
        self.assertFalse(ev["offline_ready_for_hardware_attach"])
        self.assertGreaterEqual(ev["simulated_verified_gates"], 32)
        self.assertFalse(ev["simulated_ready_for_hardware_attach"])
        self.assertTrue(ev["g25_to_g30_passed"])
        self.assertTrue(ev["g31_passed"])
        self.assertTrue(ev["g31_cantilever_flange_safe"])
        self.assertTrue(ev["g31_pl_adapter_backfocus_safe"])
        self.assertTrue(ev["g31_mattebox_barrel_safe"])
        self.assertTrue(ev["g32_passed"])
        self.assertTrue(ev["g32_dummy_battery_voltage_safe"])
        self.assertTrue(ev["g32_dtap_polarity_safe"])
        self.assertTrue(ev["g32_infolithium_auth_safe"])
        self.assertFalse(ev["persistent_emmc_writes_authorized"])
        self.assertFalse(ev["persistent_write_release"])

    def test_09_p2_10pillar_recovery_uart_gpt_rpmb_cpio_fdt(self) -> None:
        p2 = self.report_primary.pillars[1]
        self.assertEqual(p2.pillar_id, "P2")
        self.assertEqual(p2.pillar_name, "TEN_PILLAR_RECOVERY_MASTER_SUITE")
        ev = p2.evidence
        self.assertGreaterEqual(ev["recovery_pillar_count"], 10)
        self.assertEqual(ev["recovery_pillars_passed"], ev["recovery_pillar_count"])
        for pid in RECOVERY_10_PILLAR_IDS:
            self.assertTrue(ev["pillar_statuses"][pid], f"Recovery pillar {pid} failed")
        self.assertEqual(ev["uart_scenarios_total"], 10)
        self.assertEqual(ev["uart_scenarios_passed"], 10)
        self.assertEqual(ev["otp_fuse_touches"], 0)
        self.assertEqual(ev["rpmb_counter_increments"], 0)
        self.assertEqual(ev["passive_tx_bytes_emitted"], 0)
        self.assertEqual(ev["physical_device_writes"], 0)
        self.assertEqual(ev["gold_pair_tier"], "TIER_A_GOLD_VERIFIED")
        self.assertTrue(ev["gf256_2_erasures_healed"])
        self.assertTrue(ev["p8_gpt_rpmb_ok"])
        self.assertTrue(ev["p9_ramdisk_emmc_health_ok"])
        self.assertTrue(ev["p10_fdt_bootargs_kernel_ok"])

    def test_10_p3_ge20_firmware_lab_auditors_incl_17_to_20(self) -> None:
        p3 = self.report_primary.pillars[2]
        self.assertEqual(p3.pillar_id, "P3")
        self.assertEqual(p3.pillar_name, "TWENTY_PLUS_FIRMWARE_LAB_AUDITORS")
        ev = p3.evidence
        self.assertGreaterEqual(ev["auditor_count"], 20)
        self.assertGreaterEqual(ev["passed_auditor_count"], 20)
        self.assertEqual(ev["passed_auditor_count"], ev["auditor_count"])
        for key in FIRMWARE_LAB_20_AUDITOR_KEYS:
            self.assertTrue(ev["auditor_statuses"][key], f"Auditor {key} failed")
        self.assertTrue(ev["phase89_gyroflow_anamorphic_ok"])
        self.assertTrue(ev["phase93_interval_cache_ftp_ok"])
        self.assertTrue(ev["phase98_lut3d_sdi_hdmi_ok"])
        self.assertTrue(ev["phase105_c2pa_shading_mc_ok"])
        self.assertEqual(ev["calibration_mutation_bytes"], 0)

    def test_11_p3_forward_compatible_with_phase111_extra_auditor(self) -> None:
        aud = _make_clean_p3_auditors()
        aud["phase111_extra_future_audit"] = {"all_checks_passed": True, "report_sha256": "9" * 64}
        p3_ok, meta_ok = _evaluate_pillar_3(aud, Milestone110FaultInjection())
        self.assertTrue(p3_ok.passed)
        self.assertEqual(meta_ok["auditor_count"], 21)
        self.assertEqual(meta_ok["passed_count"], 21)

        aud["phase111_extra_future_audit"] = {"all_checks_passed": False, "report_sha256": "9" * 64}
        p3_bad, _ = _evaluate_pillar_3(aud, Milestone110FaultInjection())
        self.assertFalse(p3_bad.passed)
        self.assertTrue(any("phase111_extra_future_audit" in e for e in p3_bad.errors))

    def test_12_p4_ge18_stage_vm_coemulation_incl_stages_14_to_18(self) -> None:
        p4 = self.report_primary.pillars[3]
        self.assertEqual(p4.pillar_id, "P4")
        self.assertEqual(p4.pillar_name, "EIGHTEEN_PLUS_STAGE_VM_COEMULATION")
        ev = p4.evidence
        self.assertGreaterEqual(ev["stage_count"], 18)
        self.assertGreaterEqual(ev["passed_stage_count"], 18)
        self.assertEqual(ev["passed_stage_count"], ev["stage_count"])
        for skey in VM_COEMULATION_18_STAGE_KEYS:
            self.assertTrue(ev["stage_statuses"][skey], f"Stage {skey} failed")
        self.assertEqual(ev["cp_mutation_bytes"], 0)
        self.assertEqual(ev["wbi_mutation_bytes"], 0)
        self.assertEqual(ev["bk4_persistent_nvram_writes"], 0)
        self.assertEqual(ev["stage15_wf12_00342260_hits"], 0)
        self.assertEqual(ev["stage16_lithium_plating_events"], 0)
        self.assertEqual(ev["stage17_emmc_sector_writes"], 0)
        self.assertEqual(ev["stage18_cnflasha_mutation_bytes"], 0)
        self.assertEqual(ev["stage18_private_key_exports"], 0)

    def test_13_p4_forward_compatible_with_stage19_extra_stage(self) -> None:
        vm = _make_clean_p4_vm_raw()
        vm["stage19_phase111_future_harness"] = {"all_checks_passed": True}
        p4_ok, meta_ok = _evaluate_pillar_4(vm, Milestone110FaultInjection())
        self.assertTrue(p4_ok.passed)
        self.assertEqual(meta_ok["stage_count"], 19)
        self.assertEqual(meta_ok["passed_count"], 19)

        vm["stage19_phase111_future_harness"] = {"all_checks_passed": False}
        p4_bad, _ = _evaluate_pillar_4(vm, Milestone110FaultInjection())
        self.assertFalse(p4_bad.passed)
        self.assertTrue(any("stage19_phase111_future_harness" in e for e in p4_bad.errors))

    def test_14_p5_round14_round17_45pairs_and_round19_55pairs_real_kernel(self) -> None:
        p5 = self.report_primary.pillars[4]
        self.assertEqual(p5.pillar_id, "P5")
        self.assertEqual(p5.pillar_name, "REAL_KERNEL_R14_R17_R19_COMPLETE_UI_CLOSURES")
        ev = p5.evidence
        self.assertEqual(ev["round14_positive_pairs"], 18)
        self.assertIn("4.9.337-scel+", ev["round17_kernel_version"])
        self.assertEqual(ev["round17_tabs_verified"], 10)
        self.assertEqual(tuple(ev["round17_tab_sids"]), ROUND17_MULTITAB_SIDS)
        self.assertEqual(ev["round17_pairwise_deltas_verified"], 45)
        self.assertTrue(ev["round17_wraparound_verified"])
        self.assertEqual(ev["round17_runs_verified"], len(ROUND17_RUN_IDS))
        self.assertEqual(ev["round17_wf12_immune"], 1)

        self.assertIn("4.9.337-scel+", ev["round19_kernel_version"])
        self.assertEqual(ev["round19_categories_verified"], 11)
        self.assertEqual(tuple(ev["round19_category_names"]), ROUND19_11CAT_NAMES)
        self.assertEqual(ev["round19_pairwise_deltas_verified"], 55)
        self.assertTrue(ev["round19_wraparound_verified"])
        self.assertGreater(ev["round19_tchinese_vs_schinese_pixels"], 0)
        self.assertEqual(ev["round19_runs_verified"], len(ROUND19_RUN_IDS))
        self.assertEqual(ev["round19_wf12_immune"], 1)
        self.assertEqual(ev["real_kernel_nop_count"], 0)
        self.assertEqual(ev["real_kernel_crashes"], 0)

    def test_15_p5_clean_room_fallback_when_round17_and_round19_missing(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            empty_root = Path(td)
            p5_syn, meta_syn = _evaluate_pillar_5(
                repo_root=empty_root,
                use_clean_room=True,
                faults=Milestone110FaultInjection(),
            )
            self.assertTrue(p5_syn.passed)
            self.assertEqual(p5_syn.evidence["round17_source"], "CLEAN_ROOM_SYNTHETIC")
            self.assertEqual(p5_syn.evidence["round19_source"], "CLEAN_ROOM_SYNTHETIC")
            self.assertEqual(meta_syn["round17_tabs_verified"], 10)
            self.assertEqual(meta_syn["round17_pairwise_deltas_verified"], 45)
            self.assertEqual(meta_syn["round19_categories_verified"], 11)
            self.assertEqual(meta_syn["round19_pairwise_deltas_verified"], 55)
            with self.assertRaises(FileNotFoundError):
                _load_round17_summary(repo_root=empty_root, use_clean_room=False)
            with self.assertRaises(FileNotFoundError):
                _load_round19_summary(repo_root=empty_root, use_clean_room=False)

    def test_16_p6_dossier_v3_capstone22_m90_and_h0_vs_h2_immutability(self) -> None:
        p6 = self.report_primary.pillars[5]
        self.assertEqual(p6.pillar_id, "P6")
        self.assertEqual(p6.pillar_name, "POST_TRIAL_H0_VS_H2_IMMUTABILITY_AND_HARDWARE_LOCK_PROOF")
        ev = p6.evidence
        self.assertEqual(ev["dossier_v3_schema_anchor"], "stage_b_release_dossier_v3")
        self.assertEqual(ev["capstone_22gate_schema_anchor"], "stage_b_capstone_22gate_v1")
        self.assertEqual(ev["milestone90_schema_anchor"], "stage_b_milestone90_master_gate_v1")
        self.assertEqual(ev["audited_item_count"], 16)
        self.assertEqual(ev["matched_item_count"], 16)
        self.assertEqual(ev["drifted_surface_count"], 0)
        self.assertTrue(ev["c2pa_rq_lic_intact"])
        self.assertTrue(ev["spacc_cnflasha_untouched"])
        self.assertFalse(ev["persistent_emmc_writes_authorized"])
        self.assertEqual(ev["otp_fuse_touches"], 0)
        self.assertEqual(ev["passive_tx_bytes_emitted"], 0)

    def test_17_bilingual_markdown_render_contains_all_6_pillars_and_redlines(self) -> None:
        md = render_milestone110_markdown(self.report_primary)
        self.assertIn("stage_b_milestone110_master_gate_v1", md)
        self.assertIn("MILESTONE_110_SIMULATION_READY", md)
        self.assertIn("29/32", md)
        self.assertIn("32/32", md)
        self.assertIn("10/10", md)
        self.assertIn("45/45", md)
        self.assertIn("55/55", md)
        self.assertIn("20/20", md)
        self.assertIn("18/18", md)
        self.assertIn(self.report_primary.milestone110_sha256, md)
        for pid in PILLAR_IDS:
            self.assertIn(f"`{pid}`", md)

    # ------------------------------------------------------------------
    # 3. Per-Pillar Fault Injection (Fail-Closed Negative Drills)
    # ------------------------------------------------------------------

    def test_18_p1_fault_g31_heavy_pl_cantilever_without_lws_fails_closed(self) -> None:
        raw_1 = _worker_pillar_1(
            (
                str(DEFAULT_REPO_ROOT),
                True,
                {
                    "p1_pl_cantilever_kwargs": {
                        "lens_plus_mattebox_kg": 2.4,
                        "l_cg_mm": 130.0,
                        "lws_15mm_y_support_engaged": False,
                        "pl_to_e_adapter_used": True,
                        "adapter_foot_bolted_to_cage": False,
                        "clamp_on_mattebox": True,
                        "lens_front_rotates_or_telescopes": True,
                    }
                },
            )
        )
        p1 = _evaluate_pillar_1(raw_1)
        self.assertFalse(p1.passed)
        self.assertEqual(p1.status, STATUS_FAIL_CLOSED)
        self.assertFalse(p1.evidence["g31_passed"])
        self.assertFalse(p1.evidence["g31_cantilever_flange_safe"])
        self.assertFalse(p1.evidence["g31_pl_adapter_backfocus_safe"])
        self.assertFalse(p1.evidence["g31_mattebox_barrel_safe"])

    def test_19_p1_fault_g32_vmount_dummy_battery_ovp_blowout_fails_closed(self) -> None:
        raw_1 = _worker_pillar_1(
            (
                str(DEFAULT_REPO_ROOT),
                True,
                {
                    "p1_dummy_battery_kwargs": {
                        "dummy_battery_installed": True,
                        "measured_open_circuit_v": 14.8,
                        "v_mount_nominal_v": 14.8,
                        "buck_regulator_ovp_crowbar_verified": False,
                        "dtap_source_used": True,
                        "reverse_polarity_diode_or_smart_dtap": False,
                        "infolithium_thermistor_ntc_valid": False,
                    }
                },
            )
        )
        p1 = _evaluate_pillar_1(raw_1)
        self.assertFalse(p1.passed)
        self.assertEqual(p1.status, STATUS_FAIL_CLOSED)
        self.assertFalse(p1.evidence["g32_passed"])
        self.assertFalse(p1.evidence["g32_dummy_battery_voltage_safe"])
        self.assertFalse(p1.evidence["g32_dtap_polarity_safe"])
        self.assertFalse(p1.evidence["g32_infolithium_auth_safe"])

    def test_20_p1_fault_g26_tripod_and_g30_longform_and_persistent_write_fail_closed(self) -> None:
        raw_heat = _worker_pillar_1(
            (
                str(DEFAULT_REPO_ROOT),
                True,
                {"p1_tripod_housing_kwargs": {"screw_thread_length_mm": 8.5, "applied_torque_nm": 5.0}},
            )
        )
        p1_heat = _evaluate_pillar_1(raw_heat)
        self.assertFalse(p1_heat.passed)
        self.assertFalse(p1_heat.evidence["g25_to_g30_passed"])

        raw_persist = _worker_pillar_1(
            (str(DEFAULT_REPO_ROOT), True, {"p1_request_persistent_writes": True})
        )
        p1_persist = _evaluate_pillar_1(raw_persist)
        self.assertFalse(p1_persist.passed)
        self.assertFalse(p1_persist.evidence["persistent_emmc_writes_authorized"])
        self.assertFalse(p1_persist.evidence["persistent_write_release"])

    def test_21_p2_fault_otp_downgrade_cross_sku_and_ext_csd_perm_wp_fail_closed(self) -> None:
        raw_ar = _worker_domain_2(
            (
                True,
                {
                    "d2_otp_downgrade_version": "v6.00",
                    "d2_inject_cross_sku_target": "ILME-FX30",
                    "d2_inject_ext_csd_perm_wp": True,
                },
            )
        )
        p2, _ = _evaluate_pillar_2(
            _make_clean_p2_master_raw(),
            _make_clean_p2_p8_p10_raw(),
            raw_ar,
            _make_clean_p2_tier0_raw(),
            Milestone110FaultInjection(
                p2_otp_downgrade_version="v6.00",
                p2_inject_cross_sku_target="ILME-FX30",
                p2_inject_ext_csd_perm_wp=True,
            ),
        )
        self.assertFalse(p2.passed)
        self.assertTrue(any("downgrade" in e.lower() for e in p2.errors))
        self.assertTrue(any("cross-sku" in e.lower() for e in p2.errors))
        self.assertTrue(any("EXT_CSD" in e for e in p2.errors))

    def test_22_p2_fault_nonzero_otp_rpmb_and_passive_tx_fail_closed(self) -> None:
        p2, meta_2 = _evaluate_pillar_2(
            _make_clean_p2_master_raw(),
            _make_clean_p2_p8_p10_raw(),
            _make_clean_p2_antirollback_raw(),
            _make_clean_p2_tier0_raw(),
            Milestone110FaultInjection(
                p2_otp_fuse_touches_override=1,
                p2_rpmb_increments_override=1,
                p2_passive_tx_bytes_override=16,
            ),
        )
        self.assertFalse(p2.passed)
        self.assertEqual(meta_2["otp_fuse_touches"], 1)
        self.assertEqual(meta_2["rpmb_counter_increments"], 1)
        self.assertEqual(meta_2["passive_tx_bytes_emitted"], 16)

    def test_23_p2_fault_gf256_quorum_loss_cross_body_and_init2_escape_fail_closed(self) -> None:
        raw_t0 = _worker_pillar_b((True, {"pillar_b_inject_cross_body_cnflasha_transplant": True}))
        p2, _ = _evaluate_pillar_2(
            _make_clean_p2_master_raw(),
            _make_clean_p2_p8_p10_raw(),
            _make_clean_p2_antirollback_raw(),
            raw_t0,
            Milestone110FaultInjection(
                p2_inject_cross_body_cnflasha_transplant=True,
                p2_inject_gf256_quorum_loss=True,
                p2_inject_init2_escape_fault=True,
            ),
        )
        self.assertFalse(p2.passed)
        self.assertTrue(any("GF(256)" in e for e in p2.errors))
        self.assertTrue(any("init2" in e.lower() for e in p2.errors))

    def test_24_p2_fault_p8_gpt_rpmb_p9_cpio_emmc_and_p10_fdt_kernel_fail_closed(self) -> None:
        p2, meta_2 = _evaluate_pillar_2(
            _make_clean_p2_master_raw(),
            _make_clean_p2_p8_p10_raw(),
            _make_clean_p2_antirollback_raw(),
            _make_clean_p2_tier0_raw(),
            Milestone110FaultInjection(
                p2_inject_gpt_both_corrupted=True,
                p2_inject_rpmb_replay_fault=True,
                p2_inject_cpio_or_emmc_fault=True,
                p2_inject_fdt_or_kernel_fault=True,
            ),
        )
        self.assertFalse(p2.passed)
        self.assertEqual(meta_2["recovery_pillars_passed"], 7)
        self.assertFalse(p2.evidence["p8_gpt_rpmb_ok"])
        self.assertFalse(p2.evidence["p9_ramdisk_emmc_health_ok"])
        self.assertFalse(p2.evidence["p10_fdt_bootargs_kernel_ok"])

    def test_25_p2_fault_uart_s0_s6_under_10_scenarios_fails_closed(self) -> None:
        bad_master = _make_clean_p2_master_raw()
        bad_master["uart_scenarios_passed"] = 9
        bad_master["uart_all_passed"] = False
        p2, _ = _evaluate_pillar_2(
            bad_master,
            _make_clean_p2_p8_p10_raw(),
            _make_clean_p2_antirollback_raw(),
            _make_clean_p2_tier0_raw(),
            Milestone110FaultInjection(),
        )
        self.assertFalse(p2.passed)
        self.assertTrue(any("UART S0..S6" in e for e in p2.errors))

    def test_26_p3_fault_auditors_17_18_20_mutations_fail_closed(self) -> None:
        p3, meta_3 = _evaluate_pillar_3(
            _make_clean_p3_auditors(),
            Milestone110FaultInjection(
                p3_imu_calibration_mutation_bytes=12,
                p3_emmc_mutation_bytes=64,
                p3_c2pa_shading_mutation_bytes=32,
            ),
        )
        self.assertFalse(p3.passed)
        self.assertGreater(meta_3["calibration_mutation_bytes"], 0)
        self.assertTrue(any("#17" in e for e in p3.errors))
        self.assertTrue(any("#18" in e for e in p3.errors))
        self.assertTrue(any("#20" in e for e in p3.errors))

    def test_27_p3_fault_phase80_int24_phase85_nd_motor_and_emmc_format_fail_closed(self) -> None:
        p3, _ = _evaluate_pillar_3(
            _make_clean_p3_auditors(),
            Milestone110FaultInjection(
                p3_int24_wrap_around_count=1,
                p3_bus_contention_count=2,
                p3_p4_nd_motor_fault_attempts=1,
                p3_inject_internal_emmc_format_attempt=True,
                p3_calibration_mutation_bytes=4,
                p3_bk4_persistent_nvram_writes=1,
            ),
        )
        self.assertFalse(p3.passed)
        self.assertTrue(any("int24_wrap_around_count" in e for e in p3.errors))
        self.assertTrue(any("eMMC p1 format attempt" in e for e in p3.errors))
        self.assertTrue(any("calibration_mutation_bytes" in e for e in p3.errors))

    def test_28_p4_fault_stage15_wf12_stage16_lithium_stage17_emmc_fail_closed(self) -> None:
        p4, _ = _evaluate_pillar_4(
            _make_clean_p4_vm_raw(),
            Milestone110FaultInjection(
                p4_stage15_wf12_hits=1,
                p4_stage16_lithium_plating_events=2,
                p4_stage17_emmc_sector_writes=4,
            ),
        )
        self.assertFalse(p4.passed)
        self.assertEqual(p4.evidence["stage15_wf12_00342260_hits"], 1)
        self.assertEqual(p4.evidence["stage16_lithium_plating_events"], 2)
        self.assertEqual(p4.evidence["stage17_emmc_sector_writes"], 4)
        self.assertTrue(any("Stage 15" in e for e in p4.errors))
        self.assertTrue(any("Stage 16" in e for e in p4.errors))
        self.assertTrue(any("Stage 17" in e for e in p4.errors))

    def test_29_p4_fault_stage18_cnflasha_and_private_key_export_fail_closed(self) -> None:
        p4, _ = _evaluate_pillar_4(
            _make_clean_p4_vm_raw(),
            Milestone110FaultInjection(
                p4_stage18_cnflasha_mutation_bytes=128,
                p4_stage18_private_key_exports=1,
                p4_cp_mutation_bytes=16,
                p4_bk4_persistent_nvram_writes=1,
            ),
        )
        self.assertFalse(p4.passed)
        self.assertEqual(p4.evidence["stage18_cnflasha_mutation_bytes"], 128)
        self.assertEqual(p4.evidence["stage18_private_key_exports"], 1)
        self.assertTrue(any("Stage 18" in e for e in p4.errors))
        self.assertTrue(any("cp_mutation_bytes" in e for e in p4.errors))

    def test_30_p5_fault_round17_zero_pair_and_failed_wraparound_fail_closed(self) -> None:
        p5, meta_5 = _evaluate_pillar_5(
            repo_root=DEFAULT_REPO_ROOT,
            use_clean_room=True,
            faults=Milestone110FaultInjection(
                p5_round17_zero_tab_pair="tab9_vs_tab10",
                p5_round17_zero_wraparound=True,
            ),
        )
        self.assertFalse(p5.passed)
        self.assertEqual(meta_5["round17_pairwise_deltas_verified"], 44)
        self.assertFalse(p5.evidence["round17_wraparound_verified"])
        self.assertTrue(any("10-tab Status Check pair tab9_vs_tab10" in e for e in p5.errors))
        self.assertTrue(any("wrap-around" in e for e in p5.errors))

    def test_31_p5_fault_round19_zero_cat_pair_zero_tchinese_and_wf12_fail_closed(self) -> None:
        p5, meta_5 = _evaluate_pillar_5(
            repo_root=DEFAULT_REPO_ROOT,
            use_clean_room=True,
            faults=Milestone110FaultInjection(
                p5_round19_zero_cat_pair=ROUND19_11CAT_PAIR_KEYS[-1],
                p5_round19_zero_wraparound=True,
                p5_round19_zero_tchinese_delta=True,
                p5_round19_wf12_immune_override=0,
            ),
        )
        self.assertFalse(p5.passed)
        self.assertEqual(meta_5["round19_pairwise_deltas_verified"], 54)
        self.assertFalse(p5.evidence["round19_wraparound_verified"])
        self.assertEqual(p5.evidence["round19_tchinese_vs_schinese_pixels"], 0)
        self.assertEqual(p5.evidence["round19_wf12_immune"], 0)
        self.assertTrue(any("Full-Menu pair" in e for e in p5.errors))
        self.assertTrue(any("ZH-TW vs ZH-CN" in e for e in p5.errors))
        self.assertTrue(any("WF-12" in e for e in p5.errors))

    def test_32_p5_fault_round14_round17_round19_nops_crashes_manifest_fail_closed(self) -> None:
        p5, _ = _evaluate_pillar_5(
            repo_root=DEFAULT_REPO_ROOT,
            use_clean_room=True,
            faults=Milestone110FaultInjection(
                p5_round14_nop_count=1,
                p5_round14_zero_pair=True,
                p5_round17_nop_count=1,
                p5_round17_crashes=1,
                p5_round17_manifest_count_override=12,
                p5_round19_nop_count=1,
                p5_round19_crashes=1,
                p5_round19_manifest_count_override=12,
            ),
        )
        self.assertFalse(p5.passed)
        self.assertGreater(p5.evidence["real_kernel_nop_count"], 0)
        self.assertGreater(p5.evidence["real_kernel_crashes"], 0)
        self.assertTrue(any("manifest count" in e for e in p5.errors))

    def test_33_p6_fault_h0_vs_h2_surface_drift_and_tamper_fail_closed(self) -> None:
        raw_6 = _worker_pillar_f(
            (str(DEFAULT_REPO_ROOT), str(DEFAULT_REPO_ROOT), True, "p2_backup_bin")
        )
        p6, _ = _evaluate_pillar_6(
            raw_6,
            Milestone110FaultInjection(
                p6_drift_surface="p2_backup_bin",
                p6_tamper_negative_control=True,
            ),
            p1_meta={
                "persistent_emmc_writes_authorized": False,
                "simulated_ready_for_hardware_attach": False,
            },
            p2_meta={
                "otp_fuse_touches": 0,
                "rpmb_counter_increments": 0,
                "passive_tx_bytes_emitted": 0,
            },
            p3_meta={"calibration_mutation_bytes": 0},
            p4_meta={"cp_mutation_bytes": 0, "bk4_persistent_nvram_writes": 0},
        )
        self.assertFalse(p6.passed)
        self.assertEqual(p6.evidence["drifted_surface_count"], 1)

    def test_34_p6_fault_cross_pillar_hardware_lock_breach_fails_closed(self) -> None:
        raw_6 = _worker_pillar_f((str(DEFAULT_REPO_ROOT), str(DEFAULT_REPO_ROOT), True, None))
        p6, _ = _evaluate_pillar_6(
            raw_6,
            Milestone110FaultInjection(),
            p1_meta={
                "persistent_emmc_writes_authorized": True,
                "simulated_ready_for_hardware_attach": True,
            },
            p2_meta={
                "otp_fuse_touches": 1,
                "rpmb_counter_increments": 1,
                "passive_tx_bytes_emitted": 4,
            },
            p3_meta={"calibration_mutation_bytes": 8},
            p4_meta={"cp_mutation_bytes": 16, "bk4_persistent_nvram_writes": 1},
        )
        self.assertFalse(p6.passed)
        self.assertTrue(any("P1 hardware-lock invariant breached" in e for e in p6.errors))
        self.assertTrue(any("P2 zero-touch" in e for e in p6.errors))
        self.assertTrue(any("P3 calibration" in e for e in p6.errors))
        self.assertTrue(any("P4 CP/BK4" in e for e in p6.errors))

    # ------------------------------------------------------------------
    # 4. CLI Entry Point & Negative Verifier Tests
    # ------------------------------------------------------------------

    def test_35_cli_verify_milestone_110_json_markdown_and_verify_json(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            out_json = Path(td) / "milestone110.json"
            out_md = Path(td) / "milestone110.md"
            buf = io.StringIO()
            with mock.patch(
                "fx6_closure.stage_b_milestone110_master_gate.build_stage_b_milestone110_master_gate_report",
                return_value=self.report_primary,
            ), mock.patch("sys.stdout", buf):
                rc = fx6_cli_main(
                    [
                        "verify-milestone-110",
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
            self.assertEqual(payload["schema_version"], "stage_b_milestone110_master_gate_v1")
            self.assertEqual(payload["milestone110_sha256"], self.report_primary.milestone110_sha256)
            self.assertIn("MILESTONE_110_SIMULATION_READY", out_md.read_text(encoding="utf-8"))

            # Verify valid JSON via fail-closed verifier
            written_payload = json.loads(out_json.read_text(encoding="utf-8"))
            v_ok = verify_stage_b_milestone110_master_gate(written_payload)
            self.assertTrue(v_ok.valid)

            # Tamper payload -> verifier fails closed
            bad_payload = copy.deepcopy(written_payload)
            bad_payload["round19_pairwise_deltas_verified"] = 54
            bad_payload["milestone110_sha256"] = compute_milestone110_sha256(bad_payload)
            v_bad = verify_stage_b_milestone110_master_gate(bad_payload)
            self.assertFalse(v_bad.valid)
            self.assertFalse(v_bad.all_pillars_milestone_ready)

    def test_36_cli_verify_milestone_110_exits_1_on_fail_closed_gate(self) -> None:
        bad_report = copy.deepcopy(self.report_primary.to_dict())
        bad_report["all_pillars_milestone_ready"] = False
        bad_report["status"] = STATUS_FAIL_CLOSED
        bad_report["milestone110_sha256"] = compute_milestone110_sha256(bad_report)

        class _FakeBadReport:
            def __init__(self, d: dict) -> None:
                self._d = d
                self.all_pillars_milestone_ready = False
                self.schema_version = d["schema_version"]
                self.verification_mode = d["verification_mode"]
                self.passed_pillar_count = 5
                self.pillar_count = 6
                self.gate32_offline_verified = 29
                self.gate32_simulated_verified = 32
                self.recovery_pillars_passed = 10
                self.recovery_pillar_count = 10
                self.otp_fuse_touches = 0
                self.rpmb_counter_increments = 0
                self.passive_tx_bytes_emitted = 0
                self.firmware_lab_auditors_passed = 20
                self.firmware_lab_auditor_count = 20
                self.vm_coemulation_stages_passed = 18
                self.vm_coemulation_stage_count = 18
                self.round14_positive_pairs = 18
                self.round17_tabs_verified = 10
                self.round17_pairwise_deltas_verified = 45
                self.round17_runs_verified = 7
                self.round19_categories_verified = 11
                self.round19_pairwise_deltas_verified = 55
                self.round19_runs_verified = 5
                self.drifted_surface_count = 0
                self.h0_surface_count = 16
                self.hardware_live_attachment_authorized = False
                self.persistent_emmc_writes_authorized = False
                self.milestone110_sha256 = d["milestone110_sha256"]

            def to_dict(self) -> dict:
                return self._d

            def to_deterministic_json(self, indent: int = 2) -> str:
                return json.dumps(self._d, indent=indent, sort_keys=True) + "\n"

        buf = io.StringIO()
        with mock.patch(
            "fx6_closure.stage_b_milestone110_master_gate.build_stage_b_milestone110_master_gate_report",
            return_value=_FakeBadReport(bad_report),
        ), mock.patch("sys.stdout", buf):
            rc = fx6_cli_main(["verify-milestone-110", "--clean-room"])
        self.assertEqual(rc, 1)
        self.assertIn("status=FAILED", buf.getvalue())

    def test_37_pillar_result_dataclass_to_dict_and_no_raw_bytes(self) -> None:
        for p in self.report_primary.pillars:
            self.assertIsInstance(p, Milestone110PillarResult)
            pd = p.to_dict()
            self.assertEqual(pd["pillar_id"], p.pillar_id)
            serialized = json.dumps(pd, sort_keys=True)
            self.assertNotRegex(serialized, _RAW_BYTES_REPR_REGEX)

    def test_38_verify_rejects_broken_pillar_order_or_missing_pillar(self) -> None:
        bad = copy.deepcopy(self.report_primary.to_dict())
        bad["pillars"] = list(bad["pillars"][:5])
        bad["milestone110_sha256"] = compute_milestone110_sha256(bad)
        res = verify_stage_b_milestone110_master_gate(bad)
        self.assertFalse(res.valid)
        self.assertFalse(res.all_6_pillars_ok)

    def test_39_verify_rejects_c2pa_or_cnflasha_breach(self) -> None:
        for key in ("c2pa_rq_lic_intact", "spacc_cnflasha_untouched"):
            bad = copy.deepcopy(self.report_primary.to_dict())
            bad[key] = False
            bad["milestone110_sha256"] = compute_milestone110_sha256(bad)
            res = verify_stage_b_milestone110_master_gate(bad)
            self.assertFalse(res.valid, f"Tampered {key}=False unexpectedly accepted")
            self.assertFalse(res.all_pillars_milestone_ready)

    def test_40_round19_11cat_pair_keys_cover_all_unique_pairs(self) -> None:
        self.assertEqual(len(ROUND19_11CAT_PAIR_KEYS), 55)
        self.assertEqual(len(set(ROUND19_11CAT_PAIR_KEYS)), 55)
        self.assertEqual(ROUND19_11CAT_PAIR_KEYS[0], "user_vs_shooting")
        self.assertEqual(ROUND19_11CAT_PAIR_KEYS[-1], "network_vs_maintenance")


if __name__ == "__main__":
    unittest.main()
