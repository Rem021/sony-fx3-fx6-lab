"""Phase 83 unit tests for Stage-B Capstone 22-Gate + OTP/RPMB + 11-Stage VM + Round 15 Verifier."""

from __future__ import annotations

import copy
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
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
from fx6_closure.stage_b_capstone_22gate_verifier import (  # noqa: E402
    CALIBRATION_MUTATION_BYTES,
    CAPSTONE_22GATE_SCHEMA_VERSION,
    CP_MUTATION_BYTES,
    DEFAULT_REPO_ROOT,
    DOMAIN_IDS,
    FIRMWARE_LAB_14_AUDITOR_KEYS,
    HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    HARDWARE_LIVE_ATTACHMENT_REQUIREMENTS,
    OTP_FUSE_TOUCHES,
    P8_CP_MUTATION_FORBIDDEN,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHASE_83_VERSION,
    ROUND15_CATEGORY_PAIR_KEYS,
    ROUND15_MULTITAB_SIDS,
    ROUND15_RUN_IDS,
    ROUND15_STEPPING_PAIR_KEYS,
    RPMB_COUNTER_INCREMENTS,
    STAGE_B_CAPSTONE_22GATE_SCHEMA,
    STATUS_FAIL_CLOSED,
    STATUS_SIMULATION_READY,
    USB_OR_CAMERA_OPERATIONS,
    VM_COEMULATION_11_STAGE_KEYS,
    WBI_MUTATION_BYTES,
    WBI_P5_WRITE_AND_HIBERNATION_FORBIDDEN,
    CapstoneDomainResult,
    StageBCapstone22GateFaultInjection,
    StageBCapstone22GateReport,
    _evaluate_domain_1,
    _evaluate_domain_2,
    _evaluate_domain_3,
    _evaluate_domain_4,
    _evaluate_domain_5,
    _evaluate_domain_6,
    _evaluate_domain_7,
    _load_round15_summary,
    _worker_domain_1,
    _worker_domain_2,
    build_stage_b_capstone_22gate_report,
    compute_capstone_22gate_sha256,
    render_capstone_22gate_markdown,
    verify_stage_b_capstone_22gate,
)
from fx6_closure.stage_b_post_trial_auditor import (  # noqa: E402
    ANOMALY_BK4_PERSISTENT_NVRAM_LEAK,
    ANOMALY_C2PA_OR_CALIBRATION_DRIFT,
    ANOMALY_CP_BYTE_MUTATION,
    ANOMALY_SECTOR0_TAMPER,
    ANOMALY_WBI2_HEADER_DRIFT,
    STAGE_B_FORENSIC_PROBE_DEFAULTS,
    build_persistent_stock_bk4_bytes,
    populate_stage_b_capture_bundle_fixture,
    verify_stage_b_post_trial_zero_persistence,
)
from fx6_closure.stage_b_release_dossier_v3 import _worker_pillar_b  # noqa: E402

_RAW_BYTES_REPR_REGEX = r"(?<![0-9A-Za-z_/.-])b['\"]"


def _hardlink_clone_dir(src: Path, dst: Path) -> Path:
    shutil.copytree(src, dst, copy_function=os.link)
    return dst


def _make_clean_d3_raw() -> dict:
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


def _make_clean_d4_auditors() -> dict:
    aud = {
        k: {"all_checks_passed": True, "report_sha256": "c" * 64}
        for k in FIRMWARE_LAB_14_AUDITOR_KEYS
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
    return aud


def _make_clean_d5_raw() -> dict:
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
    for sk in VM_COEMULATION_11_STAGE_KEYS:
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
    return vm


class TestPhase83StageBCapstone22GateVerifier(unittest.TestCase):
    """36 fast (< 3.5s total) dual-mode tests covering D1..D7, fault injection, CLI & BYOF sync."""

    report_primary: StageBCapstone22GateReport
    elapsed_primary_s: float
    use_clean_room: bool
    _tmp_ctx: tempfile.TemporaryDirectory
    _h0_base_dir: Path
    _h2_base_dir: Path

    @classmethod
    def setUpClass(cls) -> None:
        cls.use_clean_room = os.environ.get("FX3_FX6_FORCE_CLEAN_ROOM") == "1"
        t0 = time.monotonic()
        cls.report_primary = build_stage_b_capstone_22gate_report()
        cls.elapsed_primary_s = time.monotonic() - t0

        cls._tmp_ctx = tempfile.TemporaryDirectory(prefix="fx6_p83_h0_h2_")
        tp = Path(cls._tmp_ctx.name)
        cls._h0_base_dir = tp / "h0_base"
        cls._h2_base_dir = tp / "h2_base"
        fa0080_tbl = (
            bytes(range(256))
            if cls.use_clean_room
            else hashlib.sha256(b"fx3-0xfa0080-bank0-bank1-donor-table").digest() * 8
        )
        stock_bk4 = build_persistent_stock_bk4_bytes()
        populate_stage_b_capture_bundle_fixture(
            cls._h0_base_dir,
            fa0080_table=fa0080_tbl,
            bk4_bytes=stock_bk4,
        )
        populate_stage_b_capture_bundle_fixture(
            cls._h2_base_dir,
            fa0080_table=fa0080_tbl,
            bk4_bytes=stock_bk4,
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp_ctx.cleanup()

    # ------------------------------------------------------------------
    # 1. Public Exports, Schema, Hard-Locked Redlines & Runtime Budget
    # ------------------------------------------------------------------

    def test_01_public_exports_in_init(self) -> None:
        for sym in (
            "STAGE_B_CAPSTONE_22GATE_SCHEMA",
            "CAPSTONE_22GATE_SCHEMA_VERSION",
            "PHASE_83_VERSION",
            "DOMAIN_IDS",
            "DOMAIN_SPECS",
            "FIRMWARE_LAB_14_AUDITOR_KEYS",
            "VM_COEMULATION_11_STAGE_KEYS",
            "ROUND15_SUMMARY_RELPATH",
            "ROUND15_RUN_IDS",
            "ROUND15_RUN_SPECS",
            "ROUND15_MULTITAB_SIDS",
            "OTP_FUSE_TOUCHES",
            "RPMB_COUNTER_INCREMENTS",
            "CapstoneDomainResult",
            "StageBCapstone22GateFaultInjection",
            "StageBCapstone22GateReport",
            "StageBCapstone22GateVerifyResult",
            "build_stage_b_capstone_22gate_report",
            "compute_capstone_22gate_sha256",
            "render_capstone_22gate_markdown",
            "verify_stage_b_capstone_22gate",
        ):
            self.assertIn(sym, fx6_closure.__all__)
            self.assertTrue(hasattr(fx6_closure, sym))

    def test_02_schema_and_hard_locked_zero_write_redlines(self) -> None:
        r = self.report_primary
        self.assertEqual(STAGE_B_CAPSTONE_22GATE_SCHEMA, "stage_b_capstone_22gate_v1")
        self.assertEqual(CAPSTONE_22GATE_SCHEMA_VERSION, "stage_b_capstone_22gate_v1")
        self.assertEqual(r.schema_version, "stage_b_capstone_22gate_v1")
        self.assertEqual(r.phase_version, PHASE_83_VERSION)
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(PERSISTENT_WRITE_RELEASE)
        self.assertFalse(HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        self.assertFalse(r.persistent_emmc_writes_authorized)
        self.assertFalse(r.persistent_write_release)
        self.assertFalse(r.hardware_live_attachment_authorized)
        self.assertEqual(r.hardware_live_attachment_requirements, HARDWARE_LIVE_ATTACHMENT_REQUIREMENTS)
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
        self.assertTrue(r.o_rdonly_enforced)
        self.assertTrue(r.temp_dir_cleaned)

    def test_03_single_capstone_build_under_3_5_seconds(self) -> None:
        self.assertLess(self.elapsed_primary_s, 15.0 if os.environ.get("GITHUB_ACTIONS") == "true" else 3.5)
        self.assertTrue(self.report_primary.all_domains_capstone_ready)
        self.assertEqual(self.report_primary.status, STATUS_SIMULATION_READY)

    def test_04_deterministic_capstone_sha256_repeatability(self) -> None:
        d1 = compute_capstone_22gate_sha256(self.report_primary.to_dict())
        d2 = compute_capstone_22gate_sha256(json.loads(self.report_primary.to_deterministic_json()))
        self.assertEqual(self.report_primary.capstone_sha256, d1)
        self.assertEqual(d1, d2)
        self.assertEqual(len(d1), 64)

        raw_d1_again = _worker_domain_1((str(DEFAULT_REPO_ROOT), self.use_clean_room, {}))
        d1_again = _evaluate_domain_1(raw_d1_again)
        self.assertEqual(d1_again.to_dict(), self.report_primary.domains[0].to_dict())

        d6_again, _ = _evaluate_domain_6(
            repo_root=DEFAULT_REPO_ROOT,
            use_clean_room=self.use_clean_room,
            faults=StageBCapstone22GateFaultInjection(),
        )
        self.assertEqual(d6_again.to_dict(), self.report_primary.domains[5].to_dict())

    def test_05_zero_raw_bytes_repr_in_json(self) -> None:
        rendered = self.report_primary.to_deterministic_json()
        self.assertNotRegex(rendered, _RAW_BYTES_REPR_REGEX)

    def test_06_verifier_passes_nominal_capstone_report(self) -> None:
        vr = verify_stage_b_capstone_22gate(self.report_primary)
        self.assertTrue(vr.valid)
        self.assertTrue(vr.schema_ok)
        self.assertTrue(vr.digest_matched)
        self.assertTrue(vr.safety_redlines_ok)
        self.assertTrue(vr.all_7_domains_ok)
        self.assertTrue(vr.all_domains_capstone_ready)
        self.assertEqual(vr.errors, ())

    def test_07_mode_and_o_rdonly_enforced_for_round15_and_round14(self) -> None:
        expected_mode = "CLEAN_ROOM_SYNTHETIC" if self.use_clean_room else "LOCAL_DONOR_O_RDONLY"
        self.assertEqual(self.report_primary.verification_mode, expected_mode)

        open_flags = []
        orig_open = os.open

        def _spy_open(path: object, flags: int, *args: object, **kwargs: object) -> int:
            open_flags.append((str(path), flags))
            return orig_open(path, flags, *args, **kwargs)  # type: ignore[arg-type]

        with mock.patch("os.open", side_effect=_spy_open):
            _load_round15_summary(repo_root=DEFAULT_REPO_ROOT, use_clean_room=self.use_clean_room)
        self.assertTrue(open_flags)
        self.assertTrue(all((f & os.O_ACCMODE) == os.O_RDONLY for _, f in open_flags))

    # ------------------------------------------------------------------
    # 2. Positive Verification of Domains D1 .. D7
    # ------------------------------------------------------------------

    def test_08_domain_sequence_d1_to_d7_complete(self) -> None:
        r = self.report_primary
        self.assertEqual(r.domain_count, 7)
        self.assertEqual(r.passed_domain_count, 7)
        self.assertEqual(r.failed_domain_ids, ())
        self.assertEqual(tuple(d.domain_id for d in r.domains), DOMAIN_IDS)
        self.assertTrue(all(d.passed and d.status == STATUS_SIMULATION_READY for d in r.domains))

    def test_09_d1_22gate_g21_xlr_48v_and_g22_gimbal_invariants(self) -> None:
        d1 = self.report_primary.domains[0]
        self.assertEqual(d1.domain_id, "D1")
        self.assertEqual(d1.domain_name, "SAFETY_22GATE_MASTER_PREFLIGHT")
        ev = d1.evidence
        self.assertEqual(ev["offline_verified_gates"], 19)
        self.assertFalse(ev["offline_ready_for_hardware_attach"])
        self.assertEqual(ev["simulated_verified_gates"], 22)
        self.assertFalse(ev["simulated_ready_for_hardware_attach"])
        self.assertTrue(ev["g21_passed"])
        self.assertTrue(ev["g21_hot_plug_discharge_safe"])
        self.assertEqual(ev["g21_channel_count"], 3)
        self.assertTrue(ev["g22_passed"])
        self.assertTrue(ev["g22_single_control_bus_arbitrated"])
        self.assertTrue(ev["g22_follow_focus_shear_safe"])
        self.assertTrue(ev["g22_laser_cmos_safe"])
        self.assertTrue(ev["g22_shutter_curtain_safe"])
        self.assertTrue(ev["g22_shutter_blade_parked_open"])
        self.assertTrue(ev["g22_ibis_gimbal_drift_safe"])
        self.assertLess(ev["g19_crowbar_ms"], 2.0)
        self.assertEqual(ev["g19_ibis_park_opcode"], "0x0400")
        self.assertEqual(ev["g20_lost_frames_on_switchover"], 0)
        self.assertTrue(ev["g20_rsv_salvage_ok"])

    def test_10_d2_otp_rpmb_antirollback_and_ext_csd_firewall_invariants(self) -> None:
        d2 = self.report_primary.domains[1]
        self.assertEqual(d2.domain_id, "D2")
        self.assertEqual(d2.domain_name, "OTP_RPMB_ANTIROLLBACK_AND_EXTCSD_FIREWALL")
        ev = d2.evidence
        self.assertEqual(ev["otp_fuse_touches"], 0)
        self.assertEqual(ev["rpmb_counter_increments"], 0)
        self.assertEqual(ev["gold_pair_tier"], "TIER_A_GOLD_VERIFIED")
        self.assertTrue(ev["gold_pair_compatible"])
        self.assertTrue(ev["ext_csd_clean_safe"])
        self.assertEqual(ev["ext_csd_boot_perm_wp_blocked"], "BLOCKED_PERMANENT_EMMC_WP_FUSE_TRAP")
        self.assertEqual(ev["ext_csd_user_perm_wp_blocked"], "BLOCKED_PERMANENT_EMMC_WP_FUSE_TRAP")
        self.assertEqual(ev["mmc_perm_wp_cmd_blocked"], "BLOCKED_PERMANENT_EMMC_WP_FUSE_TRAP")
        self.assertEqual(ev["physical_device_writes"], 0)
        self.assertFalse(ev["persistent_emmc_writes_authorized"])

    def test_11_d3_tier0_gf256_healer_and_sd_sentinel_escape_invariants(self) -> None:
        d3 = self.report_primary.domains[2]
        self.assertEqual(d3.domain_id, "D3")
        self.assertEqual(d3.domain_name, "TIER0_GF256_HEALER_AND_SD_SENTINEL_ESCAPE")
        ev = d3.evidence
        self.assertTrue(ev["tier0_all_passed"])
        self.assertTrue(ev["gf256_1_erasure_healed"])
        self.assertTrue(ev["gf256_2_erasures_healed"])
        self.assertTrue(ev["gf256_silent_bitrot_healed"])
        self.assertTrue(ev["gf256_3_losses_rejected"])
        self.assertTrue(ev["anti_transplant_same_body_allowed"])
        self.assertTrue(ev["anti_transplant_cross_body_blocked"])
        self.assertTrue(ev["init2_all_passed"])
        self.assertEqual(ev["escape_drills_passed"], ev["escape_drill_count"])
        self.assertEqual(ev["watchdog_scenarios_passed"], ev["watchdog_scenario_count"])
        self.assertTrue(ev["fat12_clean_and_swap_ok"])
        self.assertTrue(ev["fat16_clean_and_swap_ok"])
        self.assertEqual(ev["emmc_write_bytes"], 0)

    def test_12_d4_14_firmware_lab_auditors_and_phase75_big6_ciz_invariants(self) -> None:
        d4 = self.report_primary.domains[3]
        self.assertEqual(d4.domain_id, "D4")
        self.assertEqual(d4.domain_name, "FOURTEEN_FIRMWARE_LAB_AUDITORS")
        ev = d4.evidence
        self.assertEqual(ev["auditor_count"], 14)
        self.assertEqual(ev["passed_auditor_count"], 14)
        for key in FIRMWARE_LAB_14_AUDITOR_KEYS:
            self.assertTrue(ev["auditor_statuses"][key], f"Auditor {key} failed")
        self.assertEqual(ev["phase65_calibration_mutation_bytes"], 0)
        self.assertTrue(ev["phase65_white_point_preserved"])
        self.assertEqual(ev["phase70_internal_emmc_clip_writes"], 0)
        self.assertTrue(ev["phase70_c2pa_rq_lic_preserved"])
        self.assertTrue(ev["phase70_nrtm_v220_sidecar_ok"])
        self.assertTrue(ev["phase75_assignable_catalog_ok"])
        self.assertTrue(ev["phase75_zoom_ciz_matrix_ok"])
        self.assertTrue(ev["phase75_touch_af_desqueeze_ok"])
        self.assertTrue(ev["phase75_big6_fn_shadow_ok"])
        self.assertEqual(ev["phase75_bk4_persistent_nvram_writes"], 0)
        self.assertEqual(ev["phase75_null_gpio_faults"], 0)

    def test_13_d5_11_stage_vm_coemulation_and_stage11_touchaf_invariants(self) -> None:
        d5 = self.report_primary.domains[4]
        self.assertEqual(d5.domain_id, "D5")
        self.assertEqual(d5.domain_name, "ELEVEN_STAGE_VM_COEMULATION")
        ev = d5.evidence
        self.assertEqual(ev["stage_count"], 11)
        self.assertEqual(ev["passed_stage_count"], 11)
        for skey in VM_COEMULATION_11_STAGE_KEYS:
            self.assertTrue(ev["stage_statuses"][skey], f"Stage {skey} failed")
        self.assertEqual(ev["cp_mutation_bytes"], 0)
        self.assertEqual(ev["wbi_mutation_bytes"], 0)
        self.assertEqual(ev["stage10_relay_dropped_frames"], 0)
        self.assertGreater(ev["stage10_rsv_salvageable_frames"], 0)
        self.assertEqual(ev["stage10_rsv_salvageable_frames"], ev["stage10_rsv_committed_frames"])
        self.assertEqual(ev["stage11_nop_count"], 0)
        self.assertEqual(ev["stage11_bk4_persistent_nvram_writes"], 0)
        self.assertEqual(ev["stage11_null_gpio_derefs"], 0)
        self.assertEqual(ev["stage11_mailbox_stalls"], 0)

    def test_14_d6_round14_and_round15_multitab_real_kernel_invariants(self) -> None:
        d6 = self.report_primary.domains[5]
        self.assertEqual(d6.domain_id, "D6")
        self.assertEqual(d6.domain_name, "ROUND15_MULTITAB_REAL_KERNEL_CLOSURE")
        ev = d6.evidence
        self.assertEqual(ev["round14_positive_pairs"], 18)
        self.assertEqual(ev["round14_nop_count"], 0)
        self.assertIn("4.9.337-scel+", ev["round15_kernel_version"])
        self.assertEqual(ev["round15_tabs_verified"], 3)
        self.assertEqual(tuple(ev["round15_tab_sids"]), ROUND15_MULTITAB_SIDS)
        self.assertEqual(ev["round15_runs_verified"], 4)
        self.assertEqual(tuple(ev["round15_run_ids"]), ROUND15_RUN_IDS)
        self.assertEqual(ev["round15_nop_count"], 0)
        self.assertEqual(ev["round15_crashes"], 0)
        self.assertTrue(ev["round15_stage_b_sha256_verified"])
        for pk in ROUND15_STEPPING_PAIR_KEYS:
            self.assertGreater(ev["round15_tab_stepping_deltas"][pk], 0)
        for pk in ROUND15_CATEGORY_PAIR_KEYS:
            self.assertGreater(ev["round15_monitoring_category_deltas"][pk], 0)

    def test_15_d6_clean_room_fallback_when_round15_missing(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            empty_root = Path(td)
            d6_syn, meta_syn = _evaluate_domain_6(
                repo_root=empty_root,
                use_clean_room=True,
                faults=StageBCapstone22GateFaultInjection(),
            )
            self.assertTrue(d6_syn.passed)
            self.assertEqual(d6_syn.evidence["round15_source"], "CLEAN_ROOM_SYNTHETIC")
            self.assertEqual(meta_syn["round15_tabs_verified"], 3)
            self.assertEqual(meta_syn["round15_runs_verified"], 4)
            with self.assertRaises(FileNotFoundError):
                _load_round15_summary(repo_root=empty_root, use_clean_room=False)

    def test_16_d7_dossier_v3_and_h0_vs_h2_16surface_invariants(self) -> None:
        d7 = self.report_primary.domains[6]
        self.assertEqual(d7.domain_id, "D7")
        self.assertEqual(d7.domain_name, "DOSSIER_V3_AND_H0_VS_H2_FORENSIC_IMMUTABILITY")
        ev = d7.evidence
        self.assertEqual(ev["dossier_v3_schema_anchor"], "stage_b_release_dossier_v3")
        self.assertEqual(ev["dossier_v3_pillar_count"], 6)
        self.assertEqual(ev["audited_item_count"], 16)
        self.assertEqual(ev["matched_item_count"], 16)
        self.assertEqual(ev["drifted_surface_count"], 0)
        self.assertEqual(ev["persistent_bytes_mutated"], 0)
        self.assertTrue(ev["c2pa_rq_lic_intact"])
        self.assertTrue(ev["spacc_cnflasha_untouched"])
        self.assertEqual(ev["forensic_scenarios_passed"], 10)
        self.assertEqual(ev["forensic_scenario_count"], 10)

    # ------------------------------------------------------------------
    # 3. Per-Domain Fail-Closed Fault Injection (D1 .. D7)
    # ------------------------------------------------------------------

    def test_17_fault_d1_g21_passive_ribbon_48v_burnout_fails_closed(self) -> None:
        raw_fault = _worker_domain_1(
            (
                str(DEFAULT_REPO_ROOT),
                self.use_clean_room,
                {
                    "d1_xlr_kwargs": {
                        "channel_id": "INPUT1",
                        "input_mode": "MIC+48V",
                        "source_type": "PASSIVE_RIBBON",
                        "device_label": "Coles 4038",
                        "cloudlifter_or_transformer_isolated": False,
                    }
                },
            )
        )
        d1 = _evaluate_domain_1(raw_fault)
        self.assertFalse(d1.passed)
        self.assertEqual(d1.status, STATUS_FAIL_CLOSED)
        self.assertFalse(d1.evidence["g21_passed"])
        self.assertIn("PHANTOM_48V", d1.evidence["g21_status"])

    def test_18_fault_d1_g21_hotplug_transient_unramped_fails_closed(self) -> None:
        raw_fault = _worker_domain_1(
            (
                str(DEFAULT_REPO_ROOT),
                self.use_clean_room,
                {
                    "d1_xlr_kwargs": {
                        "channel_id": "INPUT1",
                        "input_mode": "MIC+48V",
                        "source_type": "CONDENSER_BALANCED",
                        "hot_plug_event": True,
                        "adc_mute_ramped": False,
                        "phantom_48v_boost_energized": True,
                        "residual_phantom_voltage_v": 12.0,
                    }
                },
            )
        )
        d1 = _evaluate_domain_1(raw_fault)
        self.assertFalse(d1.passed)
        self.assertFalse(d1.evidence["g21_passed"])
        self.assertFalse(d1.evidence["g21_hot_plug_discharge_safe"])

    def test_19_fault_d1_g22_dual_bus_and_follow_focus_shear_fail_closed(self) -> None:
        raw_bus = _worker_domain_1(
            (
                str(DEFAULT_REPO_ROOT),
                self.use_clean_room,
                {"d1_gimbal_kwargs": {"usb_c_crsdk_active": True, "multiport_rss_active": True}},
            )
        )
        d1_bus = _evaluate_domain_1(raw_bus)
        self.assertFalse(d1_bus.passed)
        self.assertFalse(d1_bus.evidence["g22_single_control_bus_arbitrated"])

        raw_shear = _worker_domain_1(
            (
                str(DEFAULT_REPO_ROOT),
                self.use_clean_room,
                {
                    "d1_gimbal_kwargs": {
                        "soft_ab_stops_calibrated": False,
                        "infinite_spin_uncalibrated": True,
                        "motor_torque_nm": 0.65,
                        "lens_support_rod_clamp_installed": False,
                    }
                },
            )
        )
        d1_shear = _evaluate_domain_1(raw_shear)
        self.assertFalse(d1_shear.passed)
        self.assertFalse(d1_shear.evidence["g22_follow_focus_shear_safe"])

    def test_20_fault_d1_g22_laser_cmos_and_shutter_park_and_persist_write_fail_closed(self) -> None:
        raw_laser = _worker_domain_1(
            (
                str(DEFAULT_REPO_ROOT),
                self.use_clean_room,
                {
                    "d1_gimbal_kwargs": {
                        "venue_laser_present": True,
                        "laser_class": "CLASS_4",
                        "optical_laser_cut_filter_installed": False,
                    }
                },
            )
        )
        d1_laser = _evaluate_domain_1(raw_laser)
        self.assertFalse(d1_laser.passed)
        self.assertFalse(d1_laser.evidence["g22_laser_cmos_safe"])

        raw_shutter = _worker_domain_1(
            (
                str(DEFAULT_REPO_ROOT),
                self.use_clean_room,
                {"d1_gimbal_kwargs": {"shutter_when_power_off": "ON"}},
            )
        )
        d1_shutter = _evaluate_domain_1(raw_shutter)
        self.assertFalse(d1_shutter.passed)
        self.assertFalse(d1_shutter.evidence["g22_shutter_curtain_safe"])

        raw_wr = _worker_domain_1(
            (str(DEFAULT_REPO_ROOT), self.use_clean_room, {"d1_request_persistent_writes": True})
        )
        d1_wr = _evaluate_domain_1(raw_wr)
        self.assertFalse(d1_wr.passed)

    def test_21_fault_d2_otp_downgrade_v205_v600_fails_closed(self) -> None:
        raw_d2 = _worker_domain_2((self.use_clean_room, {"d2_otp_downgrade_version": "v2.05"}))
        d2, _ = _evaluate_domain_2(
            raw_d2, StageBCapstone22GateFaultInjection(d2_otp_downgrade_version="v2.05")
        )
        self.assertFalse(d2.passed)
        self.assertEqual(d2.status, STATUS_FAIL_CLOSED)
        self.assertTrue(any("BLOCKED_ANTIROLLBACK_EPOCH_DOWNGRADE" in e for e in d2.errors))

    def test_22_fault_d2_cross_sku_wbi2_and_ext_csd_perm_wp_fail_closed(self) -> None:
        raw_sku = _worker_domain_2((self.use_clean_room, {"d2_inject_cross_sku_target": "wbi2"}))
        d2_sku, _ = _evaluate_domain_2(
            raw_sku, StageBCapstone22GateFaultInjection(d2_inject_cross_sku_target="wbi2")
        )
        self.assertFalse(d2_sku.passed)
        self.assertTrue(any("BLOCKED_CROSS_SKU_BOOTCHAIN_BRICK" in e for e in d2_sku.errors))

        raw_wp = _worker_domain_2((self.use_clean_room, {"d2_inject_ext_csd_perm_wp": True}))
        d2_wp, _ = _evaluate_domain_2(
            raw_wp, StageBCapstone22GateFaultInjection(d2_inject_ext_csd_perm_wp=True)
        )
        self.assertFalse(d2_wp.passed)
        self.assertTrue(any("BLOCKED_PERMANENT_EMMC_WP_FUSE_TRAP" in e for e in d2_wp.errors))

    def test_23_fault_d2_nonzero_otp_or_rpmb_counter_overrides_fail_closed(self) -> None:
        raw_clean = _worker_domain_2((self.use_clean_room, {}))
        d2_otp, meta_otp = _evaluate_domain_2(
            raw_clean, StageBCapstone22GateFaultInjection(d2_otp_fuse_touches_override=1)
        )
        self.assertFalse(d2_otp.passed)
        self.assertEqual(meta_otp["otp_fuse_touches"], 1)

        d2_rpmb, meta_rpmb = _evaluate_domain_2(
            raw_clean, StageBCapstone22GateFaultInjection(d2_rpmb_increments_override=1)
        )
        self.assertFalse(d2_rpmb.passed)
        self.assertEqual(meta_rpmb["rpmb_counter_increments"], 1)

    def test_24_fault_d3_cross_body_cnflasha_gf256_quorum_loss_init2_fail_closed(self) -> None:
        raw_b = _worker_pillar_b(
            (self.use_clean_room, {"pillar_b_inject_cross_body_cnflasha_transplant": True})
        )
        d3_trans = _evaluate_domain_3(
            raw_b,
            StageBCapstone22GateFaultInjection(d3_inject_cross_body_cnflasha_transplant=True),
        )
        self.assertFalse(d3_trans.passed)
        self.assertEqual(d3_trans.status, STATUS_FAIL_CLOSED)
        self.assertTrue(any("cnflasha" in e for e in d3_trans.errors))

        base_d3 = _make_clean_d3_raw()
        d3_gf = _evaluate_domain_3(
            base_d3, StageBCapstone22GateFaultInjection(d3_inject_gf256_quorum_loss=True)
        )
        self.assertFalse(d3_gf.passed)

        d3_i2 = _evaluate_domain_3(
            base_d3, StageBCapstone22GateFaultInjection(d3_inject_init2_escape_fault=True)
        )
        self.assertFalse(d3_i2.passed)

    def test_25_fault_d4_legacy_sq_big6_block_and_persistent_nvram_writes_fail_closed(self) -> None:
        aud = _make_clean_d4_auditors()
        d4_clean, _ = _evaluate_domain_4(aud, StageBCapstone22GateFaultInjection())
        self.assertTrue(d4_clean.passed)

        d4_sq, _ = _evaluate_domain_4(
            aud, StageBCapstone22GateFaultInjection(d4_inject_legacy_sq_big6_block=True)
        )
        self.assertFalse(d4_sq.passed)
        self.assertTrue(any("Big6 S&Q" in e for e in d4_sq.errors))

        d4_nv, meta_nv = _evaluate_domain_4(
            aud, StageBCapstone22GateFaultInjection(d4_bk4_persistent_nvram_writes=1)
        )
        self.assertFalse(d4_nv.passed)
        self.assertEqual(meta_nv["bk4_persistent_nvram_writes"], 1)

        d4_sp, _ = _evaluate_domain_4(
            aud, StageBCapstone22GateFaultInjection(d4_inject_persistent_nvram_shadow_path=True)
        )
        self.assertFalse(d4_sp.passed)
        self.assertTrue(any("persistent NVRAM shadow" in e for e in d4_sp.errors))

    def test_26_fault_d4_wb_whitepoint_cal_mutation_and_nrtm_fail_closed(self) -> None:
        aud = _make_clean_d4_auditors()
        d4_wp, _ = _evaluate_domain_4(
            aud, StageBCapstone22GateFaultInjection(d4_corrupt_wb_whitepoint=True)
        )
        self.assertFalse(d4_wp.passed)
        self.assertFalse(d4_wp.evidence["phase65_white_point_preserved"])

        d4_cal, meta_cal = _evaluate_domain_4(
            aud, StageBCapstone22GateFaultInjection(d4_calibration_mutation_bytes=4)
        )
        self.assertFalse(d4_cal.passed)
        self.assertEqual(meta_cal["calibration_mutation_bytes"], 4)

        d4_nrtm, _ = _evaluate_domain_4(
            aud, StageBCapstone22GateFaultInjection(d4_corrupt_nrtm_sidecar=True)
        )
        self.assertFalse(d4_nrtm.passed)
        self.assertFalse(d4_nrtm.evidence["phase70_nrtm_v220_sidecar_ok"])

    def test_27_fault_d5_stage11_nop_null_gpio_stage10_drop_cp_mut_fail_closed(self) -> None:
        vm = _make_clean_d5_raw()
        d5_s11_nop, _ = _evaluate_domain_5(
            vm, StageBCapstone22GateFaultInjection(d5_stage11_nop_count=1)
        )
        self.assertFalse(d5_s11_nop.passed)
        self.assertEqual(d5_s11_nop.evidence["stage11_nop_count"], 1)

        d5_s11_gpio, _ = _evaluate_domain_5(
            vm, StageBCapstone22GateFaultInjection(d5_stage11_null_gpio_derefs=1)
        )
        self.assertFalse(d5_s11_gpio.passed)
        self.assertEqual(d5_s11_gpio.evidence["stage11_null_gpio_derefs"], 1)

        d5_drop, _ = _evaluate_domain_5(
            vm, StageBCapstone22GateFaultInjection(d5_stage10_dropped_frames=1)
        )
        self.assertFalse(d5_drop.passed)
        self.assertEqual(d5_drop.evidence["stage10_relay_dropped_frames"], 1)

        d5_cp, meta_cp = _evaluate_domain_5(
            vm, StageBCapstone22GateFaultInjection(d5_cp_mutation_bytes=2)
        )
        self.assertFalse(d5_cp.passed)
        self.assertEqual(meta_cp["cp_mutation_bytes"], 2)

    def test_28_fault_d6_round15_crash_and_nop_count_fail_closed(self) -> None:
        d6_crash, meta_c = _evaluate_domain_6(
            repo_root=DEFAULT_REPO_ROOT,
            use_clean_room=self.use_clean_room,
            faults=StageBCapstone22GateFaultInjection(d6_round15_crashes=1),
        )
        self.assertFalse(d6_crash.passed)
        self.assertEqual(d6_crash.status, STATUS_FAIL_CLOSED)
        self.assertEqual(meta_c["round15_crashes"], 1)

        d6_nop, meta_n = _evaluate_domain_6(
            repo_root=DEFAULT_REPO_ROOT,
            use_clean_room=self.use_clean_room,
            faults=StageBCapstone22GateFaultInjection(d6_round15_nop_count=1),
        )
        self.assertFalse(d6_nop.passed)
        self.assertEqual(meta_n["round15_nop_count"], 1)

    def test_29_fault_d6_round15_zero_tab_pair_and_category_pair_fail_closed(self) -> None:
        d6_tab, _ = _evaluate_domain_6(
            repo_root=DEFAULT_REPO_ROOT,
            use_clean_room=self.use_clean_room,
            faults=StageBCapstone22GateFaultInjection(d6_round15_zero_tab_pair="tab1_vs_tab2"),
        )
        self.assertFalse(d6_tab.passed)
        self.assertEqual(d6_tab.evidence["round15_tab_stepping_deltas"]["tab1_vs_tab2"], 0)

        d6_cat, _ = _evaluate_domain_6(
            repo_root=DEFAULT_REPO_ROOT,
            use_clean_room=self.use_clean_room,
            faults=StageBCapstone22GateFaultInjection(
                d6_round15_zero_category_pair="monitoring_vs_shooting_r11d"
            ),
        )
        self.assertFalse(d6_cat.passed)
        self.assertEqual(
            d6_cat.evidence["round15_monitoring_category_deltas"]["monitoring_vs_shooting_r11d"],
            0,
        )

    def test_30_fault_d6_round15_manifest_count_and_round14_zero_pair_fail_closed(self) -> None:
        d6_mc, _ = _evaluate_domain_6(
            repo_root=DEFAULT_REPO_ROOT,
            use_clean_room=self.use_clean_room,
            faults=StageBCapstone22GateFaultInjection(d6_round15_manifest_count_override=12),
        )
        self.assertFalse(d6_mc.passed)

        d6_r14, meta_r14 = _evaluate_domain_6(
            repo_root=DEFAULT_REPO_ROOT,
            use_clean_room=self.use_clean_room,
            faults=StageBCapstone22GateFaultInjection(d6_round14_zero_pair=True),
        )
        self.assertFalse(d6_r14.passed)
        self.assertEqual(meta_r14["round14_positive_pairs"], 17)

    def _run_h0_h2_1byte_drift(self, surface: str) -> object:
        with tempfile.TemporaryDirectory() as td:
            h2 = _hardlink_clone_dir(self._h2_base_dir, Path(td) / "h2")
            mf_path = h2 / "backup-manifest.json"
            mf = json.loads(mf_path.read_text(encoding="utf-8"))
            mf_path.unlink()

            mapping = {
                "BK4": ("items", "p2_backup_bin", "p2_backup_bin.bin", -64),
                "C2PA": ("stage_b_forensic_probes", "c2pa_rq_lic", STAGE_B_FORENSIC_PROBE_DEFAULTS["c2pa_rq_lic"], 0x50),
                "WBI2": ("redline_headers", "p5_wbi_header", "p5_wbi_header.bin", 200),
                "CP": ("stage_b_forensic_probes", "p8_cp_image", STAGE_B_FORENSIC_PROBE_DEFAULTS["p8_cp_image"], 0x120),
                "sector0": ("items", "sector0", "sector0.bin", 400),
            }
            sec, key, fname, offset = mapping[surface]
            fpath = h2 / fname
            mut = bytearray(fpath.read_bytes())
            fpath.unlink()
            mut[offset] ^= 0x01
            fpath.write_bytes(bytes(mut))
            sha = hashlib.sha256(bytes(mut)).hexdigest()
            mf[sec][key]["pass1_sha256"] = sha
            mf[sec][key]["pass2_sha256"] = sha
            mf_path.write_text(json.dumps(mf, indent=2) + "\n", encoding="utf-8")

            return verify_stage_b_post_trial_zero_persistence(
                self._h0_base_dir,
                h2,
                synthetic_clean_room=self.use_clean_room,
            )

    def test_31_fault_d7_h0_vs_h2_1byte_drift_bk4_c2pa_wbi2_cp_sector0_fail_closed(self) -> None:
        self.assertIn(ANOMALY_BK4_PERSISTENT_NVRAM_LEAK, self._run_h0_h2_1byte_drift("BK4").anomaly_codes)
        rec_c2pa = self._run_h0_h2_1byte_drift("C2PA")
        self.assertFalse(rec_c2pa.c2pa_keystore_untouched)
        self.assertIn(ANOMALY_C2PA_OR_CALIBRATION_DRIFT, rec_c2pa.anomaly_codes)
        self.assertIn(ANOMALY_WBI2_HEADER_DRIFT, self._run_h0_h2_1byte_drift("WBI2").anomaly_codes)
        self.assertIn(ANOMALY_CP_BYTE_MUTATION, self._run_h0_h2_1byte_drift("CP").anomaly_codes)
        self.assertIn(ANOMALY_SECTOR0_TAMPER, self._run_h0_h2_1byte_drift("sector0").anomaly_codes)

        base_7 = dict(self.report_primary.domains[6].evidence)
        raw_7_drift = {
            "receipt_schema": base_7["receipt_schema"],
            "classification": "DRIFT_DETECTED",
            "anomaly_codes": [ANOMALY_BK4_PERSISTENT_NVRAM_LEAK],
            "all_checks_passed": False,
            "zero_persistence_verified": False,
            "audited_item_count": 16,
            "matched_item_count": 15,
            "drifted_surface_count": 1,
            "drifted_items": ["p2_backup_bin"],
            "persistent_bytes_mutated": 1,
            "wbi_mutation_bytes": 0,
            "cp_mutation_bytes": 0,
            "calibration_mutation_bytes": 0,
            "sector0_mutation_bytes": 0,
            "c2pa_keystore_untouched": True,
            "spacc_cnflasha_untouched": True,
            "exfat_media_clean": True,
            "peak_soc_c": 46.5,
            "receipt_sha256": base_7["receipt_sha256"],
            "receipt_errors": ["p2_backup_bin 1-byte drift"],
            "audit_all_checks_passed": True,
            "audit_all_10_scenarios_passed": True,
            "audit_scenario_count": 10,
            "audit_passed_scenario_count": 10,
            "audit_verify_valid": True,
            "audit_report_sha256": base_7["audit_report_sha256"],
            "o_rdonly_probe_count": base_7["o_rdonly_probe_count"],
            "temp_dir_cleaned": True,
        }
        d7_bad, meta_7_bad = _evaluate_domain_7(raw_7_drift, StageBCapstone22GateFaultInjection())
        self.assertFalse(d7_bad.passed)
        self.assertEqual(meta_7_bad["drifted_surface_count"], 1)

    def test_32_end_to_end_capstone_builder_rolls_up_single_domain_failure(self) -> None:
        bad_d6 = CapstoneDomainResult(
            domain_id="D6",
            domain_name="ROUND15_MULTITAB_REAL_KERNEL_CLOSURE",
            passed=False,
            status=STATUS_FAIL_CLOSED,
            summary="Injected Round 15 crash=1",
            evidence={},
            errors=("d6_r15: Round 15 real-kernel crashes=1 != 0",),
        )
        with mock.patch(
            "fx6_closure.stage_b_capstone_22gate_verifier._collect_parallel_capstone_results",
            return_value=(
                {"offline_verified_gates": 19, "sim_verified_gates": 22},
                {},
                {},
                {},
                {},
                {},
            ),
        ), mock.patch(
            "fx6_closure.stage_b_capstone_22gate_verifier._evaluate_domain_1",
            return_value=self.report_primary.domains[0],
        ), mock.patch(
            "fx6_closure.stage_b_capstone_22gate_verifier._evaluate_domain_2",
            return_value=(
                self.report_primary.domains[1],
                {"otp_fuse_touches": 0, "rpmb_counter_increments": 0},
            ),
        ), mock.patch(
            "fx6_closure.stage_b_capstone_22gate_verifier._evaluate_domain_3",
            return_value=self.report_primary.domains[2],
        ), mock.patch(
            "fx6_closure.stage_b_capstone_22gate_verifier._evaluate_domain_4",
            return_value=(
                self.report_primary.domains[3],
                {
                    "auditor_count": 14,
                    "passed_count": 14,
                    "calibration_mutation_bytes": 0,
                    "bk4_persistent_nvram_writes": 0,
                },
            ),
        ), mock.patch(
            "fx6_closure.stage_b_capstone_22gate_verifier._evaluate_domain_5",
            return_value=(
                self.report_primary.domains[4],
                {"stage_count": 11, "passed_count": 11, "cp_mutation_bytes": 0},
            ),
        ), mock.patch(
            "fx6_closure.stage_b_capstone_22gate_verifier._evaluate_domain_6",
            return_value=(
                bad_d6,
                {
                    "round14_positive_pairs": 18,
                    "round15_tabs_verified": 3,
                    "round15_runs_verified": 4,
                    "round15_nop_count": 0,
                    "round15_crashes": 1,
                },
            ),
        ), mock.patch(
            "fx6_closure.stage_b_capstone_22gate_verifier._evaluate_domain_7",
            return_value=(
                self.report_primary.domains[6],
                {
                    "h0_surface_count": 16,
                    "drifted_surface_count": 0,
                    "c2pa_rq_lic_intact": True,
                    "spacc_cnflasha_untouched": True,
                    "wbi_mutation_bytes": 0,
                    "cp_mutation_bytes": 0,
                    "calibration_mutation_bytes": 0,
                    "temp_dir_cleaned": True,
                },
            ),
        ):
            failed_rep = build_stage_b_capstone_22gate_report(synthetic_clean_room=True)

        self.assertFalse(failed_rep.all_domains_capstone_ready)
        self.assertEqual(failed_rep.status, STATUS_FAIL_CLOSED)
        self.assertEqual(failed_rep.passed_domain_count, 6)
        self.assertEqual(failed_rep.failed_domain_ids, ("D6",))
        self.assertFalse(verify_stage_b_capstone_22gate(failed_rep).valid)

    # ------------------------------------------------------------------
    # 4. Tamper-Evident Verifier, Bilingual Markdown, CLI & BYOF
    # ------------------------------------------------------------------

    def test_33_verifier_rejects_tampered_digest_schema_redlines_and_raw_bytes(self) -> None:
        bad_digest = copy.deepcopy(self.report_primary.to_dict())
        bad_digest["capstone_sha256"] = "0" * 64
        self.assertFalse(verify_stage_b_capstone_22gate(bad_digest).digest_matched)

        bad_schema = copy.deepcopy(self.report_primary.to_dict())
        bad_schema["schema_version"] = "wrong_schema"
        self.assertFalse(verify_stage_b_capstone_22gate(bad_schema).schema_ok)

        self.assertFalse(verify_stage_b_capstone_22gate("not-a-dict").valid)

        for key, bad_val in (
            ("persistent_emmc_writes_authorized", True),
            ("persistent_write_release", True),
            ("hardware_live_attachment_authorized", True),
            ("cp_mutation_bytes", 1),
            ("wbi_mutation_bytes", 1),
            ("calibration_mutation_bytes", 1),
            ("otp_fuse_touches", 1),
            ("rpmb_counter_increments", 1),
            ("o_rdonly_enforced", False),
        ):
            tampered = copy.deepcopy(self.report_primary.to_dict())
            tampered[key] = bad_val
            tampered["capstone_sha256"] = compute_capstone_22gate_sha256(tampered)
            res_t = verify_stage_b_capstone_22gate(tampered)
            self.assertFalse(res_t.valid)
            self.assertFalse(res_t.safety_redlines_ok)

        tampered_raw = copy.deepcopy(self.report_primary.to_dict())
        tampered_raw["domains"][0]["summary"] = "leaked b'deadbeef'"
        tampered_raw["capstone_sha256"] = compute_capstone_22gate_sha256(tampered_raw)
        self.assertFalse(verify_stage_b_capstone_22gate(tampered_raw).valid)

    def test_34_render_capstone_22gate_markdown_bilingual_content(self) -> None:
        md = render_capstone_22gate_markdown(self.report_primary)
        self.assertIn("Stage-B 终局 22-Gate 与防回滚闭环验证报告", md)
        self.assertIn("Stage-B Capstone 22-Gate & Anti-Rollback Verification Report", md)
        self.assertIn("hardware_live_attachment_authorized=False", md)
        self.assertIn("persistent_emmc_writes_authorized=False", md)
        self.assertIn("otp_fuse_touches=0", md)
        self.assertIn("rpmb_counter_increments=0", md)
        self.assertIn(self.report_primary.capstone_sha256, md)
        for did in DOMAIN_IDS:
            self.assertIn(did, md)

    def test_35_cli_verify_stage_b_capstone_json_markdown_and_nonzero_exit(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tp = Path(td)
            md_path = tp / "capstone_22gate.md"
            out_path = tp / "capstone_22gate.json"
            with mock.patch(
                "fx6_closure.stage_b_capstone_22gate_verifier.build_stage_b_capstone_22gate_report",
                return_value=self.report_primary,
            ) as mock_build:
                buf = io.StringIO()
                with mock.patch("sys.stdout", buf):
                    rc = fx6_cli_main(
                        [
                            "verify-stage-b-capstone",
                            "--clean-room",
                            "--json",
                            "--markdown-out",
                            str(md_path),
                            "--output",
                            str(out_path),
                        ]
                    )
                self.assertEqual(rc, 0)
                mock_build.assert_called_once()
                self.assertTrue(mock_build.call_args[1]["synthetic_clean_room"])

                stdout_json = json.loads(buf.getvalue())
                out_json = json.loads(out_path.read_text(encoding="utf-8"))
                self.assertEqual(stdout_json, out_json)
                self.assertEqual(stdout_json["schema_version"], STAGE_B_CAPSTONE_22GATE_SCHEMA)
                self.assertTrue(stdout_json["all_domains_capstone_ready"])
                self.assertFalse(stdout_json["hardware_live_attachment_authorized"])
                self.assertFalse(stdout_json["persistent_emmc_writes_authorized"])
                md_text = md_path.read_text(encoding="utf-8")
                self.assertIn(stdout_json["capstone_sha256"], md_text)

        buf_ok = io.StringIO()
        with mock.patch(
            "fx6_closure.stage_b_capstone_22gate_verifier.build_stage_b_capstone_22gate_report",
            return_value=self.report_primary,
        ), mock.patch("sys.stdout", buf_ok):
            rc_ok = fx6_cli_main(["verify-stage-b-capstone"])
        self.assertEqual(rc_ok, 0)
        self.assertIn("status=OK", buf_ok.getvalue())
        self.assertIn("domains=7/7", buf_ok.getvalue())

        bad_dict = copy.deepcopy(self.report_primary.to_dict())
        bad_dict["all_domains_capstone_ready"] = False
        bad_dict["status"] = STATUS_FAIL_CLOSED
        bad_dict["capstone_sha256"] = compute_capstone_22gate_sha256(bad_dict)
        bad_obj = mock.MagicMock(
            all_domains_capstone_ready=False,
            schema_version=STAGE_B_CAPSTONE_22GATE_SCHEMA,
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            passed_domain_count=6,
            domain_count=7,
            gate22_offline_verified=19,
            gate22_simulated_verified=22,
            otp_fuse_touches=0,
            rpmb_counter_increments=0,
            firmware_lab_auditors_passed=14,
            firmware_lab_auditor_count=14,
            vm_coemulation_stages_passed=11,
            vm_coemulation_stage_count=11,
            round14_positive_pairs=18,
            round15_tabs_verified=3,
            round15_runs_verified=4,
            drifted_surface_count=0,
            h0_surface_count=16,
            hardware_live_attachment_authorized=False,
            persistent_emmc_writes_authorized=False,
            capstone_sha256=bad_dict["capstone_sha256"],
        )
        bad_obj.to_dict.return_value = bad_dict
        bad_obj.to_deterministic_json.return_value = json.dumps(bad_dict)

        buf_fail = io.StringIO()
        with mock.patch(
            "fx6_closure.stage_b_capstone_22gate_verifier.build_stage_b_capstone_22gate_report",
            return_value=bad_obj,
        ), mock.patch("sys.stdout", buf_fail):
            rc_fail = fx6_cli_main(["verify-stage-b-capstone", "--json"])
        self.assertEqual(rc_fail, 1)

    def test_36_verify_byof_manifest_compatibility_check(self) -> None:
        scripts_dir = str((DEFAULT_REPO_ROOT / "scripts").resolve())
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)
        import verify_byof_manifest  # noqa: E402

        byof_doc = DEFAULT_REPO_ROOT / "docs" / "BYOF-REPRODUCTION.md"
        text = byof_doc.read_text(encoding="utf-8")
        rows, parse_errors = verify_byof_manifest.parse_byof_markdown(text)
        self.assertEqual(parse_errors, ())
        self.assertGreaterEqual(len(rows), 194)
        self.assertIn("verify-stage-b-capstone", text)
        self.assertIn("2.6", text)
        self.assertIn("8768", text)
        # Ensure zero `\bstage\d+` regex violations as enforced by verify_byof_manifest.py
        import re as _re
        self.assertIsNone(_re.search(r"\bstage\d+[A-Za-z0-9_-]*", text, _re.IGNORECASE))


if __name__ == "__main__":
    unittest.main()
