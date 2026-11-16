"""Phase 76 unit tests for Unified Stage-B Release Dossier v3 (`stage_b_release_dossier_v3`)."""

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
from fx6_closure.stage_b_release_dossier_v3 import (  # noqa: E402
    CALIBRATION_MUTATION_BYTES,
    CP_MUTATION_BYTES,
    DEFAULT_FX3_MODULES_DIR,
    DEFAULT_FX6_DONOR_LIB_DIR,
    DEFAULT_REPO_ROOT,
    DOSSIER_V3_SCHEMA_VERSION,
    FIRMWARE_LAB_13_AUDITOR_KEYS,
    HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    HARDWARE_LIVE_ATTACHMENT_REQUIREMENTS,
    P8_CP_MUTATION_FORBIDDEN,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHASE_76_VERSION,
    PILLAR_IDS,
    ROUND14_4LANG_PAIRS,
    ROUND14_RUN_IDS,
    STAGE_B_RELEASE_DOSSIER_V3_SCHEMA,
    STATUS_FAIL_CLOSED,
    STATUS_SIMULATION_READY,
    USB_OR_CAMERA_OPERATIONS,
    VM_COEMULATION_10_STAGE_KEYS,
    WBI_MUTATION_BYTES,
    WBI_P5_WRITE_AND_HIBERNATION_FORBIDDEN,
    DossierV3PillarResult,
    StageBReleaseDossierV3FaultInjection,
    StageBReleaseDossierV3Report,
    _evaluate_pillar_a,
    _evaluate_pillar_b,
    _evaluate_pillar_c,
    _evaluate_pillar_d,
    _evaluate_pillar_e,
    _evaluate_pillar_f,
    _load_round14_summary,
    _worker_pillar_a,
    _worker_pillar_b,
    build_stage_b_release_dossier_v3,
    compute_dossier_v3_sha256,
    render_dossier_v3_markdown,
    verify_stage_b_release_dossier_v3,
)


def _hardlink_clone_dir(src: Path, dst: Path) -> Path:
    shutil.copytree(src, dst, copy_function=os.link)
    return dst


class TestPhase76StageBReleaseDossierV3(unittest.TestCase):
    """32 fast (< 3.5s total) dual-mode tests covering Pillars A..F, fault injection, Markdown & CLI."""

    dossier_primary: StageBReleaseDossierV3Report
    elapsed_primary_s: float
    use_clean_room: bool
    _tmp_ctx: tempfile.TemporaryDirectory
    _h0_base_dir: Path
    _h2_base_dir: Path

    @classmethod
    def setUpClass(cls) -> None:
        cls.use_clean_room = os.environ.get("FX3_FX6_FORCE_CLEAN_ROOM") == "1"
        t0 = time.monotonic()
        cls.dossier_primary = build_stage_b_release_dossier_v3()
        cls.elapsed_primary_s = time.monotonic() - t0

        cls._tmp_ctx = tempfile.TemporaryDirectory(prefix="fx6_p76_h0_h2_")
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
            "STAGE_B_RELEASE_DOSSIER_V3_SCHEMA",
            "DOSSIER_V3_SCHEMA_VERSION",
            "PHASE_76_VERSION",
            "PILLAR_IDS",
            "PILLAR_SPECS",
            "FIRMWARE_LAB_13_AUDITOR_KEYS",
            "VM_COEMULATION_10_STAGE_KEYS",
            "ROUND14_SUMMARY_RELPATH",
            "ROUND14_4LANG_PAIRS",
            "STATUS_SIMULATION_READY",
            "HARDWARE_LIVE_ATTACHMENT_AUTHORIZED",
            "DossierV3PillarResult",
            "StageBReleaseDossierV3FaultInjection",
            "StageBReleaseDossierV3Report",
            "StageBReleaseDossierV3VerifyResult",
            "compute_dossier_v3_sha256",
            "build_stage_b_release_dossier_v3",
            "verify_stage_b_release_dossier_v3",
            "render_dossier_v3_markdown",
        ):
            self.assertIn(sym, fx6_closure.__all__)
            self.assertTrue(hasattr(fx6_closure, sym))

    def test_02_schema_and_hard_locked_zero_write_redlines(self) -> None:
        d = self.dossier_primary
        self.assertEqual(STAGE_B_RELEASE_DOSSIER_V3_SCHEMA, "stage_b_release_dossier_v3")
        self.assertEqual(DOSSIER_V3_SCHEMA_VERSION, "stage_b_release_dossier_v3")
        self.assertEqual(d.schema_version, "stage_b_release_dossier_v3")
        self.assertEqual(d.phase_version, PHASE_76_VERSION)
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(PERSISTENT_WRITE_RELEASE)
        self.assertFalse(HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        self.assertFalse(d.persistent_emmc_writes_authorized)
        self.assertFalse(d.persistent_write_release)
        self.assertFalse(d.hardware_live_attachment_authorized)
        self.assertEqual(d.hardware_live_attachment_requirements, HARDWARE_LIVE_ATTACHMENT_REQUIREMENTS)
        self.assertTrue(P8_CP_MUTATION_FORBIDDEN)
        self.assertTrue(WBI_P5_WRITE_AND_HIBERNATION_FORBIDDEN)
        self.assertTrue(d.p8_cp_mutation_forbidden)
        self.assertTrue(d.wbi_p5_write_and_hibernation_forbidden)
        self.assertEqual(CP_MUTATION_BYTES, 0)
        self.assertEqual(WBI_MUTATION_BYTES, 0)
        self.assertEqual(CALIBRATION_MUTATION_BYTES, 0)
        self.assertEqual(USB_OR_CAMERA_OPERATIONS, 0)
        self.assertEqual(d.cp_mutation_bytes, 0)
        self.assertEqual(d.wbi_mutation_bytes, 0)
        self.assertEqual(d.calibration_mutation_bytes, 0)
        self.assertEqual(d.usb_or_camera_operations, 0)
        self.assertTrue(d.o_rdonly_enforced)
        self.assertTrue(d.temp_dir_cleaned)

    def test_03_single_dossier_build_under_3_5_seconds(self) -> None:
        self.assertLess(self.elapsed_primary_s, 15.0 if os.environ.get("GITHUB_ACTIONS") == "true" else 3.5)
        self.assertTrue(self.dossier_primary.all_pillars_simulation_ready)
        self.assertEqual(self.dossier_primary.status, STATUS_SIMULATION_READY)

    def test_04_deterministic_sha256_repeatability(self) -> None:
        d1 = compute_dossier_v3_sha256(self.dossier_primary.to_dict())
        d2 = compute_dossier_v3_sha256(json.loads(self.dossier_primary.to_deterministic_json()))
        self.assertEqual(self.dossier_primary.dossier_v3_sha256, d1)
        self.assertEqual(d1, d2)
        self.assertEqual(len(d1), 64)

        # Independently re-evaluating Pillar A and Pillar E must yield byte-identical evidence
        raw_a_again = _worker_pillar_a((str(DEFAULT_REPO_ROOT), self.use_clean_room, {}))
        pa_again = _evaluate_pillar_a(raw_a_again)
        self.assertEqual(pa_again.to_dict(), self.dossier_primary.pillars[0].to_dict())

        pe_again, _ = _evaluate_pillar_e(
            repo_root=DEFAULT_REPO_ROOT,
            use_clean_room=self.use_clean_room,
            faults=StageBReleaseDossierV3FaultInjection(),
        )
        self.assertEqual(pe_again.to_dict(), self.dossier_primary.pillars[4].to_dict())

    def test_05_zero_raw_bytes_repr_in_json(self) -> None:
        rendered = self.dossier_primary.to_deterministic_json()
        self.assertNotRegex(rendered, r'(?<![0-9A-Za-z_/.-])b[\'"]')

    def test_06_verifier_passes_nominal_dossier(self) -> None:
        vr = verify_stage_b_release_dossier_v3(self.dossier_primary)
        self.assertTrue(vr.valid)
        self.assertTrue(vr.schema_ok)
        self.assertTrue(vr.digest_matched)
        self.assertTrue(vr.safety_redlines_ok)
        self.assertTrue(vr.all_6_pillars_ok)
        self.assertTrue(vr.all_pillars_simulation_ready)
        self.assertEqual(vr.errors, ())

    def test_07_mode_and_o_rdonly_enforced_for_round14_and_donors(self) -> None:
        expected_mode = "CLEAN_ROOM_SYNTHETIC" if self.use_clean_room else "LOCAL_DONOR_O_RDONLY"
        self.assertEqual(self.dossier_primary.verification_mode, expected_mode)

        open_flags = []
        orig_open = os.open

        def _spy_open(path: object, flags: int, *args: object, **kwargs: object) -> int:
            open_flags.append((str(path), flags))
            return orig_open(path, flags, *args, **kwargs)  # type: ignore[arg-type]

        with mock.patch("os.open", side_effect=_spy_open):
            _load_round14_summary(repo_root=DEFAULT_REPO_ROOT, use_clean_room=self.use_clean_room)
        self.assertTrue(open_flags)
        self.assertTrue(all((f & os.O_ACCMODE) == os.O_RDONLY for _, f in open_flags))

    # ------------------------------------------------------------------
    # 2. Pillar A..F Positive Verification
    # ------------------------------------------------------------------

    def test_08_pillar_sequence_a_to_f_complete(self) -> None:
        d = self.dossier_primary
        self.assertEqual(d.pillar_count, 6)
        self.assertEqual(d.passed_pillar_count, 6)
        self.assertEqual(d.failed_pillar_ids, ())
        self.assertEqual(tuple(p.pillar_id for p in d.pillars), PILLAR_IDS)
        self.assertTrue(all(p.passed and p.status == STATUS_SIMULATION_READY for p in d.pillars))

    def test_09_pillar_a_20gate_g19_g20_invariants(self) -> None:
        pa = self.dossier_primary.pillars[0]
        self.assertEqual(pa.pillar_id, "PILLAR_A")
        self.assertEqual(pa.pillar_name, "PHYSICAL_RIG_AND_20GATE_SAFETY")
        ev = pa.evidence
        self.assertEqual(ev["offline_verified_gates"], 17)
        self.assertFalse(ev["offline_ready_for_hardware_attach"])
        self.assertEqual(ev["simulated_verified_gates"], 20)
        self.assertFalse(ev["simulated_ready_for_hardware_attach"])
        self.assertTrue(ev["g19_rig_groundloop_passed"])
        self.assertFalse(ev["g19_ground_loop_hazard"])
        self.assertTrue(ev["g19_emount_rail_passed"])
        self.assertLess(ev["g19_crowbar_ms"], 2.0)
        self.assertEqual(ev["g19_ibis_park_opcode"], "0x0400")
        self.assertTrue(ev["g20_power_failover_passed"])
        self.assertEqual(ev["g20_lost_frames_on_switchover"], 0)
        self.assertTrue(ev["g20_rsv_salvage_passed"])
        self.assertFalse(ev["persistent_emmc_writes_authorized"])
        self.assertFalse(ev["persistent_write_release"])

    def test_10_pillar_b_gf256_anti_transplant_and_init2_escape_invariants(self) -> None:
        pb = self.dossier_primary.pillars[1]
        self.assertEqual(pb.pillar_id, "PILLAR_B")
        self.assertEqual(pb.pillar_name, "TIER0_GF256_SELFHEAL_AND_INIT2_ESCAPE")
        ev = pb.evidence
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

    def test_11_pillar_c_13_firmware_lab_auditors_and_wb_proxy_invariants(self) -> None:
        pc = self.dossier_primary.pillars[2]
        self.assertEqual(pc.pillar_id, "PILLAR_C")
        self.assertEqual(pc.pillar_name, "FIRMWARE_PARITY_13PLUS_AUDITORS")
        ev = pc.evidence
        self.assertEqual(ev["auditor_count"], 13)
        self.assertEqual(ev["passed_auditor_count"], 13)
        for key in FIRMWARE_LAB_13_AUDITOR_KEYS:
            self.assertTrue(ev["auditor_statuses"][key], f"Auditor {key} did not pass")
        self.assertEqual(ev["phase65_calibration_mutation_bytes"], 0)
        self.assertEqual(ev["phase65_cp_mutation_bytes"], 0)
        self.assertTrue(ev["phase65_white_point_preserved"])
        self.assertEqual(ev["phase70_internal_emmc_clip_writes"], 0)
        self.assertTrue(ev["phase70_c2pa_rq_lic_preserved"])
        self.assertTrue(ev["phase70_clipname_proxy_ok"])
        self.assertTrue(ev["phase70_dual_slot_matrix_ok"])
        self.assertTrue(ev["phase70_nrtm_v220_sidecar_ok"])

    def test_12_pillar_d_10stage_vm_coemulation_invariants(self) -> None:
        pd = self.dossier_primary.pillars[3]
        self.assertEqual(pd.pillar_id, "PILLAR_D")
        self.assertEqual(pd.pillar_name, "TEN_STAGE_HETEROGENEOUS_COEMULATION")
        ev = pd.evidence
        self.assertEqual(ev["stage_count"], 10)
        self.assertEqual(ev["passed_stage_count"], 10)
        for skey in VM_COEMULATION_10_STAGE_KEYS:
            self.assertTrue(ev["stage_statuses"][skey], f"Stage {skey} failed")
        self.assertEqual(ev["cp_mutation_bytes"], 0)
        self.assertEqual(ev["wbi_mutation_bytes"], 0)
        self.assertEqual(ev["stage9_nop_count"], 0)
        self.assertEqual(ev["stage10_dram_elastic_fifo_mib"], 256)
        self.assertEqual(ev["stage10_relay_dropped_frames"], 0)
        self.assertFalse(ev["stage10_relay_main_stalled"])
        self.assertGreater(ev["stage10_rsv_salvageable_frames"], 0)
        self.assertEqual(ev["stage10_rsv_salvageable_frames"], ev["stage10_rsv_committed_frames"])
        self.assertTrue(ev["stage10_c2pa_license_untouched"])

    def test_13_pillar_e_round14_real_kernel_4lang_3surface_invariants(self) -> None:
        pe = self.dossier_primary.pillars[4]
        self.assertEqual(pe.pillar_id, "PILLAR_E")
        self.assertEqual(pe.pillar_name, "FOUR_LANG_THREE_SURFACE_REAL_KERNEL_UI")
        ev = pe.evidence
        self.assertIn("4.9.337-scel+", ev["kernel_version"])
        self.assertEqual(ev["nop_count"], 0)
        self.assertEqual(ev["crashes"], 0)
        self.assertTrue(ev["stage_b_sha256_verified"])
        for rid in ROUND14_RUN_IDS:
            self.assertEqual(ev["stage_b_manifest_counts"][rid], 13)
        self.assertEqual(ev["total_surfaces"], 3)
        self.assertEqual(ev["total_matrix_pairs"], 18)
        self.assertEqual(ev["positive_matrix_pairs"], 18)
        self.assertEqual(ev["surface_positive_counts"], {"big6_home": 6, "full_menu": 6, "status_check": 6})
        for pair in ROUND14_4LANG_PAIRS:
            self.assertGreater(ev["status_check_6pair_deltas"][pair], 0)

    def test_14_pillar_e_clean_room_fallback_when_round14_missing(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            empty_root = Path(td)
            pe_syn, meta_syn = _evaluate_pillar_e(
                repo_root=empty_root,
                use_clean_room=True,
                faults=StageBReleaseDossierV3FaultInjection(),
            )
            self.assertTrue(pe_syn.passed)
            self.assertEqual(pe_syn.evidence["round14_source"], "CLEAN_ROOM_SYNTHETIC")
            self.assertEqual(meta_syn["positive_pairs"], 18)
            with self.assertRaises(FileNotFoundError):
                _load_round14_summary(repo_root=empty_root, use_clean_room=False)

    def test_15_pillar_f_h0_vs_h2_16surface_zero_persistence_invariants(self) -> None:
        pf = self.dossier_primary.pillars[5]
        self.assertEqual(pf.pillar_id, "PILLAR_F")
        self.assertEqual(pf.pillar_name, "CLOSED_LOOP_R0_R6_ZERO_PERSISTENCE_PROOF")
        ev = pf.evidence
        self.assertEqual(ev["audited_item_count"], 16)
        self.assertEqual(ev["matched_item_count"], 16)
        self.assertEqual(ev["drifted_surface_count"], 0)
        self.assertEqual(ev["persistent_bytes_mutated"], 0)
        self.assertTrue(ev["c2pa_rq_lic_intact"])
        self.assertTrue(ev["spacc_cnflasha_untouched"])
        self.assertEqual(ev["wbi_mutation_bytes"], 0)
        self.assertEqual(ev["cp_mutation_bytes"], 0)
        self.assertEqual(ev["calibration_mutation_bytes"], 0)
        self.assertEqual(ev["sector0_mutation_bytes"], 0)
        self.assertEqual(ev["forensic_scenarios_passed"], 10)
        self.assertEqual(ev["forensic_scenario_count"], 10)

    # ------------------------------------------------------------------
    # 3. Per-Pillar Fail-Closed Fault Injection (Pillar A .. Pillar F)
    # ------------------------------------------------------------------

    def test_16_fault_pillar_a_g19_dtap_groundloop_fails_closed(self) -> None:
        raw_fault = _worker_pillar_a(
            (
                str(DEFAULT_REPO_ROOT),
                self.use_clean_room,
                {
                    "pillar_a_rig_kwargs": {
                        "shared_unisolated_dtap": True,
                        "camera_power_mode": "DTAP_DUMMY_BATTERY",
                        "monitor_power_mode": "SAME_DTAP_BATTERY",
                    }
                },
            )
        )
        pa = _evaluate_pillar_a(raw_fault)
        self.assertFalse(pa.passed)
        self.assertEqual(pa.status, STATUS_FAIL_CLOSED)
        self.assertFalse(pa.evidence["g19_rig_groundloop_passed"])
        self.assertTrue(pa.evidence["g19_ground_loop_hazard"])

    def test_17_fault_pillar_a_emount_crowbar_and_persistent_write_fail_closed(self) -> None:
        raw_emount = _worker_pillar_a(
            (
                str(DEFAULT_REPO_ROOT),
                self.use_clean_room,
                {"pillar_a_emount_kwargs": {"v_lens_servo_crowbar_ms": 4.2}},
            )
        )
        pa_emount = _evaluate_pillar_a(raw_emount)
        self.assertFalse(pa_emount.passed)
        self.assertFalse(pa_emount.evidence["g19_emount_rail_passed"])

        raw_wr = _worker_pillar_a(
            (
                str(DEFAULT_REPO_ROOT),
                self.use_clean_room,
                {"pillar_a_request_persistent_writes": True},
            )
        )
        pa_wr = _evaluate_pillar_a(raw_wr)
        self.assertFalse(pa_wr.passed)

    def test_18_fault_pillar_a_g20_ups_frame_drop_fails_closed(self) -> None:
        raw_g20 = _worker_pillar_a(
            (
                str(DEFAULT_REPO_ROOT),
                self.use_clean_room,
                {"pillar_a_power_failover_kwargs": {"lost_frames_on_switchover": 2}},
            )
        )
        pa = _evaluate_pillar_a(raw_g20)
        self.assertFalse(pa.passed)
        self.assertFalse(pa.evidence["g20_power_failover_passed"])

    def test_19_fault_pillar_b_cross_body_cnflasha_transplant_fails_closed(self) -> None:
        raw_b = _worker_pillar_b(
            (self.use_clean_room, {"pillar_b_inject_cross_body_cnflasha_transplant": True})
        )
        pb = _evaluate_pillar_b(
            raw_b,
            StageBReleaseDossierV3FaultInjection(pillar_b_inject_cross_body_cnflasha_transplant=True),
        )
        self.assertFalse(pb.passed)
        self.assertEqual(pb.status, STATUS_FAIL_CLOSED)
        self.assertTrue(pb.evidence["cross_body_transplant_fault_rejected_by_guard"])
        self.assertTrue(any("cnflasha" in e for e in pb.errors))

    def test_20_fault_pillar_b_gf256_quorum_loss_and_init2_escape_fail_closed(self) -> None:
        base_b = {
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
            "escape_drill_count": 10,
            "escape_drills_passed": 10,
            "watchdog_suite_passed": True,
            "watchdog_scenario_count": 7,
            "watchdog_scenarios_passed": 7,
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
        pb_gf = _evaluate_pillar_b(
            base_b,
            StageBReleaseDossierV3FaultInjection(pillar_b_inject_gf256_quorum_loss=True),
        )
        self.assertFalse(pb_gf.passed)

        pb_i2 = _evaluate_pillar_b(
            base_b,
            StageBReleaseDossierV3FaultInjection(pillar_b_inject_init2_escape_fault=True),
        )
        self.assertFalse(pb_i2.passed)

    def test_21_fault_pillar_c_wb_whitepoint_cal_mutation_and_nrtm_fail_closed(self) -> None:
        ok_auditors = {
            k: {"all_checks_passed": True, "report_sha256": "c" * 64}
            for k in FIRMWARE_LAB_13_AUDITOR_KEYS
        }
        ok_auditors["wb_color_matrix_and_look_audit"] = {
            "all_checks_passed": True,
            "calibration_mutation_bytes": 0,
            "cp_mutation_bytes": 0,
            "pillar_d_factory_calibration": {"passed": True},
            "report_sha256": "d" * 64,
        }
        ok_auditors["proxy_clipname_and_sidecar_audit"] = {
            "all_checks_passed": True,
            "internal_emmc_clip_writes": 0,
            "c2pa_rq_lic_preserved": True,
            "pillar_1_clipname_proxy": {"passed": True},
            "pillar_2_dual_slot_matrix": {"passed": True},
            "pillar_3_nrtm_xml_sidecar": {"passed": True},
            "report_sha256": "e" * 64,
        }

        pc_wp, _ = _evaluate_pillar_c(
            ok_auditors,
            StageBReleaseDossierV3FaultInjection(pillar_c_corrupt_wb_whitepoint=True),
        )
        self.assertFalse(pc_wp.passed)
        self.assertFalse(pc_wp.evidence["phase65_white_point_preserved"])

        pc_cal, meta_cal = _evaluate_pillar_c(
            ok_auditors,
            StageBReleaseDossierV3FaultInjection(pillar_c_calibration_mutation_bytes=4),
        )
        self.assertFalse(pc_cal.passed)
        self.assertEqual(meta_cal["calibration_mutation_bytes"], 4)

        pc_nrtm, _ = _evaluate_pillar_c(
            ok_auditors,
            StageBReleaseDossierV3FaultInjection(pillar_c_corrupt_nrtm_sidecar=True),
        )
        self.assertFalse(pc_nrtm.passed)
        self.assertFalse(pc_nrtm.evidence["phase70_nrtm_v220_sidecar_ok"])

    def test_22_fault_pillar_d_stage10_frame_drop_and_cp_mutation_fail_closed(self) -> None:
        base_vm = {
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
        for sk in VM_COEMULATION_10_STAGE_KEYS:
            base_vm[sk] = {"all_checks_passed": True}
        base_vm["stage9_phase67_tc_lens_paint"] = {
            "all_checks_passed": True,
            "nop_count": 0,
            "phase67_audit_digest_sha256": "9" * 64,
        }
        base_vm["stage10_phase71_dualslot_ups_salvage"] = {
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

        pd_drop, _ = _evaluate_pillar_d(
            base_vm,
            StageBReleaseDossierV3FaultInjection(pillar_d_stage10_dropped_frames=1),
        )
        self.assertFalse(pd_drop.passed)
        self.assertEqual(pd_drop.evidence["stage10_relay_dropped_frames"], 1)

        pd_cp, meta_cp = _evaluate_pillar_d(
            base_vm,
            StageBReleaseDossierV3FaultInjection(pillar_d_cp_mutation_bytes=1),
        )
        self.assertFalse(pd_cp.passed)
        self.assertEqual(meta_cp["cp_mutation_bytes"], 1)

        pd_s9, _ = _evaluate_pillar_d(
            base_vm,
            StageBReleaseDossierV3FaultInjection(pillar_d_stage9_nop_count=1),
        )
        self.assertFalse(pd_s9.passed)
        self.assertEqual(pd_s9.evidence["stage9_nop_count"], 1)

    def test_23_fault_pillar_e_round14_nop_count_nonzero_fails_closed(self) -> None:
        pe_nop, meta_nop = _evaluate_pillar_e(
            repo_root=DEFAULT_REPO_ROOT,
            use_clean_room=self.use_clean_room,
            faults=StageBReleaseDossierV3FaultInjection(pillar_e_nop_count=1),
        )
        self.assertFalse(pe_nop.passed)
        self.assertEqual(pe_nop.status, STATUS_FAIL_CLOSED)
        self.assertEqual(meta_nop["nop_count"], 1)

    def test_24_fault_pillar_e_collapsed_4lang_delta_and_manifest_count_fail_closed(self) -> None:
        pe_pair, meta_pair = _evaluate_pillar_e(
            repo_root=DEFAULT_REPO_ROOT,
            use_clean_room=self.use_clean_room,
            faults=StageBReleaseDossierV3FaultInjection(
                pillar_e_zero_pair_surface="status_check",
                pillar_e_zero_pair_name="schinese_vs_tchinese",
            ),
        )
        self.assertFalse(pe_pair.passed)
        self.assertEqual(meta_pair["positive_pairs"], 17)

        pe_mc, _ = _evaluate_pillar_e(
            repo_root=DEFAULT_REPO_ROOT,
            use_clean_room=self.use_clean_room,
            faults=StageBReleaseDossierV3FaultInjection(pillar_e_stage_b_manifest_count_override=12),
        )
        self.assertFalse(pe_mc.passed)

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

    def test_25_fault_pillar_f_h0_vs_h2_bk4_and_c2pa_1byte_drift(self) -> None:
        rec_bk4 = self._run_h0_h2_1byte_drift("BK4")
        self.assertFalse(rec_bk4.all_checks_passed)
        self.assertIn(ANOMALY_BK4_PERSISTENT_NVRAM_LEAK, rec_bk4.anomaly_codes)

        rec_c2pa = self._run_h0_h2_1byte_drift("C2PA")
        self.assertFalse(rec_c2pa.all_checks_passed)
        self.assertFalse(rec_c2pa.c2pa_keystore_untouched)
        self.assertIn(ANOMALY_C2PA_OR_CALIBRATION_DRIFT, rec_c2pa.anomaly_codes)

    def test_26_fault_pillar_f_wbi2_cp_sector0_and_evaluator_fail_closed(self) -> None:
        rec_wbi = self._run_h0_h2_1byte_drift("WBI2")
        self.assertFalse(rec_wbi.all_checks_passed)
        self.assertIn(ANOMALY_WBI2_HEADER_DRIFT, rec_wbi.anomaly_codes)

        rec_cp = self._run_h0_h2_1byte_drift("CP")
        self.assertFalse(rec_cp.all_checks_passed)
        self.assertIn(ANOMALY_CP_BYTE_MUTATION, rec_cp.anomaly_codes)

        rec_sec = self._run_h0_h2_1byte_drift("sector0")
        self.assertFalse(rec_sec.all_checks_passed)
        self.assertIn(ANOMALY_SECTOR0_TAMPER, rec_sec.anomaly_codes)

        base_f = dict(self.dossier_primary.pillars[5].evidence)
        raw_f_drift = {
            "receipt_schema": base_f["receipt_schema"],
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
            "receipt_sha256": base_f["receipt_sha256"],
            "receipt_errors": ["p2_backup_bin 1-byte drift"],
            "audit_all_checks_passed": True,
            "audit_all_10_scenarios_passed": True,
            "audit_scenario_count": 10,
            "audit_passed_scenario_count": 10,
            "audit_verify_valid": True,
            "audit_report_sha256": base_f["audit_report_sha256"],
            "o_rdonly_probe_count": base_f["o_rdonly_probe_count"],
            "temp_dir_cleaned": True,
        }
        pf_bad, meta_f_bad = _evaluate_pillar_f(raw_f_drift, StageBReleaseDossierV3FaultInjection())
        self.assertFalse(pf_bad.passed)
        self.assertEqual(meta_f_bad["drifted_surface_count"], 1)

    def test_27_end_to_end_dossier_builder_rolls_up_any_single_pillar_failure(self) -> None:
        bad_pillar = DossierV3PillarResult(
            pillar_id="PILLAR_E",
            pillar_name="FOUR_LANG_THREE_SURFACE_REAL_KERNEL_UI",
            passed=False,
            status=STATUS_FAIL_CLOSED,
            summary="Injected nop_count=1 fault",
            evidence={},
            errors=("pillar_e: Round 14 real-kernel nop_count=1 != 0",),
        )
        with mock.patch(
            "fx6_closure.stage_b_release_dossier_v3._collect_parallel_donor_results",
            return_value=(
                {
                    "schema": "s",
                    "verification_mode": "CLEAN_ROOM_SYNTHETIC",
                    "offline_verified_gates": 17,
                    "offline_17_gates_verified": True,
                    "offline_all_20_gates_verified": False,
                    "offline_ready_for_hw": False,
                    "sim_verified_gates": 20,
                    "sim_all_20_gates_verified": True,
                    "sim_dry_run_rehearsal_only": True,
                    "sim_ready_for_hw": False,
                    "g19_to_g20_all_passed": True,
                    "g19_passed": True,
                    "g19_rig_groundloop_passed": True,
                    "g19_ground_loop_hazard": False,
                    "g19_emount_rail_passed": True,
                    "g19_crowbar_ms": 1.2,
                    "g19_ibis_park_opcode": 0x0400,
                    "g20_passed": True,
                    "g20_power_failover_passed": True,
                    "g20_lost_frames": 0,
                    "g20_rsv_salvage_ok": True,
                    "persistent_emmc_writes_authorized": False,
                    "persistent_write_release": False,
                    "sim_errors": [],
                    "g19_errors": [],
                    "g20_errors": [],
                },
                {},
                {},
                {},
                {},
            ),
        ), mock.patch(
            "fx6_closure.stage_b_release_dossier_v3._evaluate_pillar_b",
            return_value=self.dossier_primary.pillars[1],
        ), mock.patch(
            "fx6_closure.stage_b_release_dossier_v3._evaluate_pillar_c",
            return_value=(
                self.dossier_primary.pillars[2],
                {"auditor_count": 13, "passed_count": 13, "calibration_mutation_bytes": 0},
            ),
        ), mock.patch(
            "fx6_closure.stage_b_release_dossier_v3._evaluate_pillar_d",
            return_value=(
                self.dossier_primary.pillars[3],
                {"stage_count": 10, "passed_count": 10, "cp_mutation_bytes": 0},
            ),
        ), mock.patch(
            "fx6_closure.stage_b_release_dossier_v3._evaluate_pillar_e",
            return_value=(
                bad_pillar,
                {"surfaces_verified": 3, "positive_pairs": 18, "nop_count": 1},
            ),
        ), mock.patch(
            "fx6_closure.stage_b_release_dossier_v3._evaluate_pillar_f",
            return_value=(
                self.dossier_primary.pillars[5],
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
            failed_dossier = build_stage_b_release_dossier_v3(synthetic_clean_room=True)

        self.assertFalse(failed_dossier.all_pillars_simulation_ready)
        self.assertEqual(failed_dossier.status, STATUS_FAIL_CLOSED)
        self.assertEqual(failed_dossier.passed_pillar_count, 5)
        self.assertEqual(failed_dossier.failed_pillar_ids, ("PILLAR_E",))
        self.assertFalse(verify_stage_b_release_dossier_v3(failed_dossier).valid)

    # ------------------------------------------------------------------
    # 4. Tamper-Evident Verifier, Bilingual Markdown & CLI
    # ------------------------------------------------------------------

    def test_28_verifier_rejects_tampered_digest_schema_and_hardlocked_flags(self) -> None:
        bad_digest = copy.deepcopy(self.dossier_primary.to_dict())
        bad_digest["dossier_v3_sha256"] = "0" * 64
        res_d = verify_stage_b_release_dossier_v3(bad_digest)
        self.assertFalse(res_d.valid)
        self.assertFalse(res_d.digest_matched)

        bad_schema = copy.deepcopy(self.dossier_primary.to_dict())
        bad_schema["schema_version"] = "wrong_schema"
        res_s = verify_stage_b_release_dossier_v3(bad_schema)
        self.assertFalse(res_s.valid)
        self.assertFalse(res_s.schema_ok)

        for key, bad_val in (
            ("persistent_emmc_writes_authorized", True),
            ("persistent_write_release", True),
            ("hardware_live_attachment_authorized", True),
            ("cp_mutation_bytes", 1),
            ("wbi_mutation_bytes", 1),
            ("calibration_mutation_bytes", 1),
            ("o_rdonly_enforced", False),
        ):
            tampered = copy.deepcopy(self.dossier_primary.to_dict())
            tampered[key] = bad_val
            tampered["dossier_v3_sha256"] = compute_dossier_v3_sha256(tampered)
            res_t = verify_stage_b_release_dossier_v3(tampered)
            self.assertFalse(res_t.valid)
            self.assertFalse(res_t.safety_redlines_ok)

    def test_29_verifier_rejects_non_mapping_and_raw_bytes_repr(self) -> None:
        res_bad_type = verify_stage_b_release_dossier_v3("not-a-dict")
        self.assertFalse(res_bad_type.valid)

        tampered = copy.deepcopy(self.dossier_primary.to_dict())
        tampered["pillars"][0]["summary"] = "leaked b'deadbeef'"
        tampered["dossier_v3_sha256"] = compute_dossier_v3_sha256(tampered)
        res_raw = verify_stage_b_release_dossier_v3(tampered)
        self.assertFalse(res_raw.valid)

    def test_30_render_dossier_v3_markdown_bilingual_content(self) -> None:
        md = render_dossier_v3_markdown(self.dossier_primary)
        self.assertIn("Stage-B 统一发布档案 v3", md)
        self.assertIn("Unified Stage-B Release Dossier v3", md)
        self.assertIn("六大支柱验证矩阵", md)
        self.assertIn("6-Pillar Verification Matrix", md)
        self.assertIn("hardware_live_attachment_authorized=False", md)
        self.assertIn("persistent_emmc_writes_authorized=False", md)
        self.assertIn(self.dossier_primary.dossier_v3_sha256, md)
        for pid in PILLAR_IDS:
            self.assertIn(pid, md)

    def test_31_cli_build_stage_b_dossier_v3_json_and_markdown_out(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tp = Path(td)
            md_path = tp / "dossier_v3.md"
            out_path = tp / "dossier_v3.json"
            with mock.patch(
                "fx6_closure.stage_b_release_dossier_v3.build_stage_b_release_dossier_v3",
                return_value=self.dossier_primary,
            ) as mock_build:
                buf = io.StringIO()
                with mock.patch("sys.stdout", buf):
                    rc = fx6_cli_main(
                        [
                            "build-stage-b-dossier-v3",
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
                _, kwargs = mock_build.call_args
                self.assertTrue(kwargs["synthetic_clean_room"])

                stdout_json = json.loads(buf.getvalue())
                out_json = json.loads(out_path.read_text(encoding="utf-8"))
                self.assertEqual(stdout_json, out_json)
                self.assertEqual(stdout_json["schema_version"], STAGE_B_RELEASE_DOSSIER_V3_SCHEMA)
                self.assertTrue(stdout_json["all_pillars_simulation_ready"])
                self.assertFalse(stdout_json["hardware_live_attachment_authorized"])
                self.assertFalse(stdout_json["persistent_emmc_writes_authorized"])
                md_text = md_path.read_text(encoding="utf-8")
                self.assertIn("Unified Stage-B Release Dossier v3", md_text)
                self.assertIn(stdout_json["dossier_v3_sha256"], md_text)

    def test_32_cli_build_stage_b_dossier_v3_summary_and_nonzero_exit_on_failure(self) -> None:
        buf_ok = io.StringIO()
        with mock.patch(
            "fx6_closure.stage_b_release_dossier_v3.build_stage_b_release_dossier_v3",
            return_value=self.dossier_primary,
        ), mock.patch("sys.stdout", buf_ok):
            rc_ok = fx6_cli_main(["build-stage-b-dossier-v3"])
        self.assertEqual(rc_ok, 0)
        self.assertIn("status=OK", buf_ok.getvalue())
        self.assertIn("pillars=6/6", buf_ok.getvalue())

        bad_dict = copy.deepcopy(self.dossier_primary.to_dict())
        bad_dict["all_pillars_simulation_ready"] = False
        bad_dict["status"] = STATUS_FAIL_CLOSED
        bad_dict["dossier_v3_sha256"] = compute_dossier_v3_sha256(bad_dict)
        bad_obj = mock.MagicMock(
            all_pillars_simulation_ready=False,
            schema_version=STAGE_B_RELEASE_DOSSIER_V3_SCHEMA,
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            passed_pillar_count=5,
            pillar_count=6,
            gate20_offline_verified=17,
            gate20_simulated_verified=20,
            firmware_lab_auditors_passed=13,
            firmware_lab_auditor_count=13,
            vm_coemulation_stages_passed=10,
            vm_coemulation_stage_count=10,
            round14_positive_pairs=18,
            drifted_surface_count=0,
            h0_surface_count=16,
            hardware_live_attachment_authorized=False,
            persistent_emmc_writes_authorized=False,
            dossier_v3_sha256=bad_dict["dossier_v3_sha256"],
        )
        bad_obj.to_dict.return_value = bad_dict
        bad_obj.to_deterministic_json.return_value = json.dumps(bad_dict)

        buf_fail = io.StringIO()
        with mock.patch(
            "fx6_closure.stage_b_release_dossier_v3.build_stage_b_release_dossier_v3",
            return_value=bad_obj,
        ), mock.patch("sys.stdout", buf_fail):
            rc_fail = fx6_cli_main(["build-stage-b-dossier-v3", "--json"])
        self.assertEqual(rc_fail, 1)


if __name__ == "__main__":
    unittest.main()
