"""Phase 68 unit tests for Stage-B R0..R6 Closed-Loop Hardware Rehearsal Orchestrator."""

from __future__ import annotations

import copy
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
    "outputs/fx3-vm",
    "outputs/fx6-on-fx3-closure",
):
    _cand = str(REPO_ROOT / _rel)
    if _cand not in sys.path:
        sys.path.insert(0, _cand)

import fx6_closure  # noqa: E402
from fx6_closure.__main__ import main as fx6_cli_main  # noqa: E402
from fx6_closure.hardware_readiness_packet import verify_real_tier0_capture_bundle  # noqa: E402
from fx6_closure.stage_b_post_trial_auditor import (  # noqa: E402
    ANOMALY_BK4_PERSISTENT_NVRAM_LEAK,
    ANOMALY_C2PA_OR_CALIBRATION_DRIFT,
    ANOMALY_CP_BYTE_MUTATION,
    ANOMALY_SECTOR0_TAMPER,
    ANOMALY_WBI2_HEADER_DRIFT,
    CLASS_CLEAN_ZERO_PERSISTENCE,
    STAGE_B_FORENSIC_PROBE_DEFAULTS,
    verify_stage_b_post_trial_zero_persistence,
)
from fx6_closure.stage_b_ram_overlay_packager import (  # noqa: E402
    STAGE_B_BK_LANG_SPECS,
    audit_stage_b_bk4_shadow,
)
from fx6_closure.stage_b_rehearsal_orchestrator import (  # noqa: E402
    CALIBRATION_MUTATION_BYTES,
    CP_MUTATION_BYTES,
    DEFAULT_FX3_MODULES_DIR,
    DEFAULT_FX6_DONOR_LIB_DIR,
    DEFAULT_REPO_ROOT,
    HARDWARE_LIVE_ATTACHMENT_REQUIREMENTS,
    P8_CP_MUTATION_FORBIDDEN,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHASE_68_VERSION,
    REHEARSAL_STAGE_IDS,
    ROUND13_4LANG_PAIRS,
    SCHEMA_VERSION,
    STAGE_B_REHEARSAL_SCHEMA,
    STATUS_FAIL_CLOSED,
    STATUS_REHEARSAL_PASSED,
    USB_OR_CAMERA_OPERATIONS,
    WBI_MUTATION_BYTES,
    WBI_P5_WRITE_AND_HIBERNATION_FORBIDDEN,
    StageBClosedLoopRehearsalReport,
    StageBRehearsalFaultInjection,
    _run_stage_r0,
    _run_stage_r1,
    _run_stage_r2,
    _run_stage_r3,
    _run_stage_r4,
    _run_stage_r5,
    _run_stage_r6,
    build_persistent_stock_bk4_bytes,
    compute_rehearsal_digest_sha256,
    render_stage_b_rehearsal_markdown,
    run_stage_b_closed_loop_rehearsal,
    verify_stage_b_rehearsal_certificate,
)


def _hardlink_clone_dir(src: Path, dst: Path) -> Path:
    shutil.copytree(src, dst, copy_function=os.link)
    return dst


class TestPhase68StageBClosedLoopRehearsal(unittest.TestCase):
    """34 fast dual-mode tests covering R0..R6 rehearsal, redlines, fault injection & CLI."""

    report_primary: StageBClosedLoopRehearsalReport
    elapsed_primary_s: float
    use_clean_room: bool
    _tmp_ctx: tempfile.TemporaryDirectory
    _h0_base_dir: Path
    _h2_base_dir: Path
    _fa0080_tbl: bytes
    _stock_bk4: bytes

    @classmethod
    def setUpClass(cls) -> None:
        cls.use_clean_room = os.environ.get("FX3_FX6_FORCE_CLEAN_ROOM") == "1"
        t0 = time.monotonic()
        cls.report_primary = run_stage_b_closed_loop_rehearsal()
        cls.elapsed_primary_s = time.monotonic() - t0

        cls._tmp_ctx = tempfile.TemporaryDirectory(prefix="fx6_p68_fixtures_")
        tp = Path(cls._tmp_ctx.name)
        cls._h0_base_dir = tp / "h0_base"
        cls._h2_base_dir = tp / "h2_base"
        _, cls._fa0080_tbl, cls._stock_bk4 = _run_stage_r2(
            h0_dir=cls._h0_base_dir,
            use_clean_room=cls.use_clean_room,
            faults=StageBRehearsalFaultInjection(),
        )
        _run_stage_r5(
            volatile_overlay_dir=tp / "ov_base",
            h2_dir=cls._h2_base_dir,
            fa0080_tbl=cls._fa0080_tbl,
            stock_bk4=cls._stock_bk4,
            faults=StageBRehearsalFaultInjection(),
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp_ctx.cleanup()

    # ------------------------------------------------------------------
    # Exports, Schema, Hard-Locked Redlines & Performance
    # ------------------------------------------------------------------

    def test_01_public_exports_in_init(self) -> None:
        for sym in (
            "STAGE_B_REHEARSAL_SCHEMA",
            "SCHEMA_VERSION",
            "PHASE_68_VERSION",
            "REHEARSAL_STAGE_IDS",
            "StageBRehearsalFaultInjection",
            "StageBRehearsalStageResult",
            "StageBClosedLoopRehearsalReport",
            "StageBRehearsalCertificateVerifyResult",
            "compute_rehearsal_digest_sha256",
            "render_stage_b_rehearsal_markdown",
            "run_stage_b_closed_loop_rehearsal",
            "verify_stage_b_rehearsal_certificate",
        ):
            self.assertIn(sym, fx6_closure.__all__)
            self.assertTrue(hasattr(fx6_closure, sym))

    def test_02_schema_and_hard_locked_zero_write_redlines(self) -> None:
        rep = self.report_primary
        self.assertEqual(STAGE_B_REHEARSAL_SCHEMA, "stage_b_closed_loop_rehearsal_v1")
        self.assertEqual(SCHEMA_VERSION, "stage_b_closed_loop_rehearsal_v1")
        self.assertEqual(rep.schema_version, "stage_b_closed_loop_rehearsal_v1")
        self.assertEqual(rep.phase_version, PHASE_68_VERSION)
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(PERSISTENT_WRITE_RELEASE)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.persistent_write_release)
        self.assertFalse(rep.hardware_live_attachment_authorized)
        self.assertEqual(rep.hardware_live_attachment_requirements, HARDWARE_LIVE_ATTACHMENT_REQUIREMENTS)
        self.assertTrue(P8_CP_MUTATION_FORBIDDEN)
        self.assertTrue(WBI_P5_WRITE_AND_HIBERNATION_FORBIDDEN)
        self.assertTrue(rep.p8_cp_mutation_forbidden)
        self.assertTrue(rep.wbi_p5_write_and_hibernation_forbidden)
        self.assertEqual(CP_MUTATION_BYTES, 0)
        self.assertEqual(WBI_MUTATION_BYTES, 0)
        self.assertEqual(CALIBRATION_MUTATION_BYTES, 0)
        self.assertEqual(USB_OR_CAMERA_OPERATIONS, 0)
        self.assertEqual(rep.cp_mutation_bytes, 0)
        self.assertEqual(rep.wbi_mutation_bytes, 0)
        self.assertEqual(rep.calibration_mutation_bytes, 0)
        self.assertEqual(rep.usb_or_camera_operations, 0)
        self.assertTrue(rep.temp_dir_cleaned)

    def test_03_single_rehearsal_under_4_seconds(self) -> None:
        self.assertLess(self.elapsed_primary_s, 4.0)
        self.assertTrue(self.report_primary.rehearsal_passed)
        self.assertEqual(self.report_primary.status, STATUS_REHEARSAL_PASSED)

    def test_04_deterministic_digest_across_repeated_calls(self) -> None:
        d_first = compute_rehearsal_digest_sha256(self.report_primary.to_dict())
        d_second = compute_rehearsal_digest_sha256(json.loads(self.report_primary.to_deterministic_json()))
        self.assertEqual(self.report_primary.rehearsal_digest_sha256, d_first)
        self.assertEqual(d_first, d_second)
        self.assertEqual(len(d_first), 64)
        # Verify repeated independent invocations of R0, R1, R4, and H0-vs-H2 receipt match identically
        f = StageBRehearsalFaultInjection()
        self.assertEqual(
            _run_stage_r0(use_clean_room=self.use_clean_room, faults=f).to_dict(),
            self.report_primary.stages[0].to_dict(),
        )
        self.assertEqual(
            _run_stage_r1(repo_root=DEFAULT_REPO_ROOT, use_clean_room=self.use_clean_room, faults=f).to_dict(),
            self.report_primary.stages[1].to_dict(),
        )
        r4_again, _ = _run_stage_r4(repo_root=DEFAULT_REPO_ROOT, use_clean_room=self.use_clean_room, faults=f)
        self.assertEqual(r4_again.to_dict(), self.report_primary.stages[4].to_dict())

    def test_05_zero_raw_bytes_repr_in_json(self) -> None:
        rendered = self.report_primary.to_deterministic_json()
        self.assertNotRegex(rendered, r'(?<![0-9A-Za-z_/.-])b[\'"]')

    def test_06_certificate_verifier_passes_nominal_report(self) -> None:
        res = verify_stage_b_rehearsal_certificate(self.report_primary)
        self.assertTrue(res.valid)
        self.assertTrue(res.schema_ok)
        self.assertTrue(res.digest_matched)
        self.assertTrue(res.safety_redlines_ok)
        self.assertTrue(res.all_7_stages_ok)
        self.assertTrue(res.rehearsal_passed)
        self.assertEqual(res.errors, ())

    def test_07_mode_tracks_environment_and_donor_o_rdonly_reads(self) -> None:
        expected_mode = "CLEAN_ROOM_SYNTHETIC" if self.use_clean_room else "LOCAL_DONOR_O_RDONLY"
        self.assertEqual(self.report_primary.verification_mode, expected_mode)
        if not self.use_clean_room:
            from fx6_closure.stage_b_post_trial_auditor import _probe_donor_surfaces_o_rdonly

            open_flags = []
            orig_open = os.open

            def _spy_open(path: object, flags: int, *args: object, **kwargs: object) -> int:
                open_flags.append((str(path), flags))
                return orig_open(path, flags, *args, **kwargs)  # type: ignore[arg-type]

            with mock.patch("os.open", side_effect=_spy_open):
                _probe_donor_surfaces_o_rdonly(use_clean_room=False)
            self.assertTrue(open_flags)
            self.assertTrue(all((f & os.O_ACCMODE) == os.O_RDONLY for _, f in open_flags))

    # ------------------------------------------------------------------
    # R0..R6 Positive Stage Assertions
    # ------------------------------------------------------------------

    def test_08_stage_sequence_r0_to_r6_complete(self) -> None:
        self.assertEqual(self.report_primary.stage_count, 7)
        self.assertEqual(self.report_primary.passed_stage_count, 7)
        self.assertEqual(self.report_primary.failed_stage_ids, ())
        self.assertEqual(tuple(s.stage_id for s in self.report_primary.stages), REHEARSAL_STAGE_IDS)
        self.assertTrue(all(s.passed and s.status == STATUS_REHEARSAL_PASSED for s in self.report_primary.stages))

    def test_09_r0_bench_fixture_selftest_invariants(self) -> None:
        r0 = self.report_primary.stages[0]
        self.assertEqual(r0.stage_id, "R0")
        self.assertEqual(r0.stage_name, "BENCH_FIXTURE_SELFTEST")
        ev = r0.evidence
        self.assertTrue(ev["cmake_open_drain_equals_one"])
        self.assertAlmostEqual(ev["v_idle_tx_v"], 1.8)
        self.assertTrue(ev["open_drain_enforced"])
        self.assertFalse(ev["overvoltage_hazard"])
        self.assertTrue(ev["loopback_48000_bit_exact"])
        self.assertTrue(ev["camera_disconnected_verified"])
        self.assertTrue(ev["ltc_cable_disconnected_verified"])

    def test_10_r1_18gate_and_exfat_media_firewall_invariants(self) -> None:
        r1 = self.report_primary.stages[1]
        self.assertEqual(r1.stage_id, "R1")
        self.assertEqual(r1.stage_name, "SAFETY_18GATE_AND_MEDIA_FIREWALL")
        ev = r1.evidence
        self.assertEqual(ev["gate_count"], 18)
        self.assertTrue(ev["all_18_gates_verified"])
        self.assertTrue(ev["offline_15_gates_verified"])
        self.assertTrue(ev["g17_to_g18_all_passed"])
        self.assertTrue(ev["exfat_lab_card_all_passed"])
        self.assertTrue(ev["exfat_bootchecksum_ok"])
        self.assertTrue(ev["p1_vs_exfat_separated"])
        self.assertTrue(ev["production_xdroot_rejected"])
        self.assertTrue(ev["production_m4root_rsv_rejected"])

    def test_11_r2_h0_16surface_baseline_snapshot(self) -> None:
        r2 = self.report_primary.stages[2]
        self.assertEqual(r2.stage_id, "R2")
        self.assertEqual(r2.stage_name, "H0_BASELINE_SNAPSHOT")
        self.assertEqual(self.report_primary.h0_surface_count, 16)
        surfaces = r2.evidence["surfaces"]
        self.assertEqual(len(surfaces), 16)
        for req in ("sector0", "p1_updater", "p2_backup_bin", "p5_wbi_header", "p8_cp_image", "c2pa_rq_lic", "spacc_cnflasha"):
            self.assertIn(req, surfaces)
            self.assertEqual(len(surfaces[req]["sha256"]), 64)

    def test_12_r3_stage_b_volatile_overlay_and_wf12_immunity(self) -> None:
        r3 = self.report_primary.stages[3]
        self.assertEqual(r3.stage_id, "R3")
        self.assertEqual(r3.stage_name, "STAGE_B_VOLATILE_OVERLAY_MOUNT")
        ev = r3.evidence
        self.assertEqual(ev["lock_table_count"], 13)
        self.assertTrue(ev["tmpfs_within_budget"])
        self.assertLess(ev["volatile_tmpfs_overlay_mib"], 48.0)
        self.assertTrue(ev["wf12_immunity_ok"])
        self.assertEqual(ev["bk4_airplane_keys"], {"0x019e0012": "00", "0x0051000f": "00", "0x01a20002": "00"})
        self.assertEqual(ev["init2_total_emmc_writes"], 0)
        self.assertEqual(ev["init2_sandbox_passed"], ev["init2_sandbox_total"])

    def test_13_r4_live_h1_qmp_hdmi_and_round13_4lang_closure(self) -> None:
        r4 = self.report_primary.stages[4]
        self.assertEqual(r4.stage_id, "R4")
        self.assertEqual(r4.stage_name, "LIVE_H1_COEMULATION_AND_4LANG_UI")
        ev = r4.evidence
        self.assertTrue(ev["qmp_all_checks_passed"])
        self.assertEqual(ev["qmp_nop_count"], 0)
        self.assertTrue(ev["qmp_ctrl_magic_verified"])
        self.assertTrue(ev["hdmi_all_checks_passed"])
        self.assertTrue(ev["edid_256b_valid"])
        self.assertEqual(ev["sdi_transceiver_faults"], 0)
        self.assertIn("4.9.337-scel+", ev["round13_kernel_version"])
        self.assertEqual(ev["round13_status_check_sid"], "0x2f")
        self.assertEqual(ev["round13_menu_3layer_sid"], "0x11")
        self.assertEqual(ev["round13_4lang_positive_pairs"], 6)
        self.assertEqual(self.report_primary.round13_4lang_pairs_verified, 6)
        for pair in ROUND13_4LANG_PAIRS:
            self.assertGreater(ev["round13_big6_pair_deltas"][pair], 0)
            self.assertGreater(ev["round13_menu_pair_deltas"][pair], 0)

    def test_14_r5_cold_power_cycle_wipe(self) -> None:
        r5 = self.report_primary.stages[5]
        self.assertEqual(r5.stage_id, "R5")
        self.assertEqual(r5.stage_name, "COLD_POWER_CYCLE_WIPE")
        ev = r5.evidence
        self.assertEqual(ev["transition"], "H1 -> H2")
        self.assertTrue(ev["volatile_overlay_vanished"])
        self.assertEqual(ev["lingering_mounts"], 0)
        self.assertEqual(ev["tmpfs_residue_files"], 0)
        self.assertEqual(ev["emmc_residual_writes"], 0)
        self.assertFalse(ev["mod_arm_once_present"])
        self.assertTrue(ev["stock_fx3_restored"])

    def test_15_r6_h0_vs_h2_post_trial_forensic_audit(self) -> None:
        r6 = self.report_primary.stages[6]
        self.assertEqual(r6.stage_id, "R6")
        self.assertEqual(r6.stage_name, "H0_VS_H2_POST_TRIAL_FORENSIC_AUDIT")
        ev = r6.evidence
        self.assertEqual(ev["classification"], CLASS_CLEAN_ZERO_PERSISTENCE)
        self.assertEqual(ev["audited_item_count"], 16)
        self.assertEqual(ev["matched_item_count"], 16)
        self.assertEqual(ev["drifted_surface_count"], 0)
        self.assertEqual(self.report_primary.h2_drifted_surface_count, 0)
        self.assertTrue(ev["c2pa_keystore_untouched"])
        self.assertTrue(ev["spacc_cnflasha_untouched"])
        self.assertEqual(ev["calibration_mutation_bytes"], 0)
        self.assertEqual(ev["negative_tamper_scenarios_passed"], 10)
        self.assertEqual(self.report_primary.negative_tamper_drills_passed, 10)

    # ------------------------------------------------------------------
    # Fault Injection Across Every Stage R0..R6 (Fail-Closed)
    # ------------------------------------------------------------------

    def test_16_r0_fault_3v3_overvoltage_and_push_pull_fails_closed(self) -> None:
        res_v = _run_stage_r0(use_clean_room=self.use_clean_room, faults=StageBRehearsalFaultInjection(r0_v_idle_tx_v=3.3))
        self.assertFalse(res_v.passed)
        self.assertEqual(res_v.status, STATUS_FAIL_CLOSED)
        self.assertTrue(res_v.evidence["overvoltage_hazard"])

        res_pp = _run_stage_r0(use_clean_room=self.use_clean_room, faults=StageBRehearsalFaultInjection(r0_open_drain=False))
        self.assertFalse(res_pp.passed)
        self.assertEqual(res_pp.status, STATUS_FAIL_CLOSED)

    def test_17_r0_fault_camera_or_ltc_attached_and_framing_error(self) -> None:
        res_cam = _run_stage_r0(use_clean_room=self.use_clean_room, faults=StageBRehearsalFaultInjection(r0_camera_connected=True))
        self.assertFalse(res_cam.passed)
        res_ltc = _run_stage_r0(use_clean_room=self.use_clean_room, faults=StageBRehearsalFaultInjection(r0_ltc_cable_connected=True))
        self.assertFalse(res_ltc.passed)
        res_frm = _run_stage_r0(use_clean_room=self.use_clean_room, faults=StageBRehearsalFaultInjection(r0_inject_framing_error=True))
        self.assertFalse(res_frm.passed)

    def test_18_r1_fault_client_card_with_rsv_and_xdroot_rejected(self) -> None:
        res_rsv = _run_stage_r1(
            repo_root=DEFAULT_REPO_ROOT,
            use_clean_room=self.use_clean_room,
            faults=StageBRehearsalFaultInjection(r1_slot_a_entries=(("PRIVATE/M4ROOT/CLIP/C0001.RSV", 4096),)),
        )
        self.assertFalse(res_rsv.passed)
        self.assertEqual(res_rsv.status, STATUS_FAIL_CLOSED)
        self.assertFalse(res_rsv.evidence["exfat_lab_card_all_passed"])

        res_xd = _run_stage_r1(
            repo_root=DEFAULT_REPO_ROOT,
            use_clean_room=self.use_clean_room,
            faults=StageBRehearsalFaultInjection(r1_slot_a_entries=(("XDROOT/Clip/A001C001.MXF", 65536),)),
        )
        self.assertFalse(res_xd.passed)
        self.assertEqual(res_xd.status, STATUS_FAIL_CLOSED)

    def test_19_r1_fault_bad_exfat_bootchecksum_and_persistent_write_request(self) -> None:
        from fx3_safety.exfat_media_integrity_guard import build_synthetic_exfat_boot_region

        bad_exfat = bytearray(build_synthetic_exfat_boot_region())
        bad_exfat[11 * 512] ^= 0xFF
        res_chk = _run_stage_r1(
            repo_root=DEFAULT_REPO_ROOT,
            use_clean_room=self.use_clean_room,
            faults=StageBRehearsalFaultInjection(r1_exfat_boot_bytes=bytes(bad_exfat)),
        )
        self.assertFalse(res_chk.passed)
        self.assertFalse(res_chk.evidence["exfat_bootchecksum_ok"])

        res_wr = _run_stage_r1(
            repo_root=DEFAULT_REPO_ROOT,
            use_clean_room=self.use_clean_room,
            faults=StageBRehearsalFaultInjection(r1_request_persistent_writes=True),
        )
        self.assertFalse(res_wr.passed)

    def test_20_r2_fault_wbi2_and_sector0_corruption_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            h0_wbi = _hardlink_clone_dir(self._h0_base_dir, Path(td) / "h0_wbi")
            wbi_p = h0_wbi / "p5_wbi_header.bin"
            raw_wbi = bytearray(wbi_p.read_bytes())
            wbi_p.unlink()
            raw_wbi[0:4] = b"XXXX"
            wbi_p.write_bytes(bytes(raw_wbi))
            audit_wbi = verify_real_tier0_capture_bundle(h0_wbi)
            self.assertFalse(audit_wbi.valid)
            self.assertFalse(audit_wbi.p5_wbi2_header_ok)

            h0_sec = _hardlink_clone_dir(self._h0_base_dir, Path(td) / "h0_sec")
            sec_p = h0_sec / "sector0.bin"
            raw_sec = bytearray(sec_p.read_bytes())
            sec_p.unlink()
            raw_sec[0:4] = b"0000"
            sec_p.write_bytes(bytes(raw_sec))
            audit_sec = verify_real_tier0_capture_bundle(h0_sec)
            self.assertFalse(audit_sec.valid)
            self.assertFalse(audit_sec.sector0_magic_ok)

    def test_21_r3_fault_wf12_airplane_lock_table_and_tmpfs_budget(self) -> None:
        bad_bk4 = build_persistent_stock_bk4_bytes(wireless_enabled=True, bk_lang_byte=STAGE_B_BK_LANG_SPECS["en"].bk_lang_value)
        bad_audit = audit_stage_b_bk4_shadow(bad_bk4, expected_lang="en")
        self.assertFalse(bad_audit["valid"])

        stub_v2 = mock.MagicMock(
            schema="stage_b_ram_overlay_v2",
            lang="en",
            bk_lang_spec=STAGE_B_BK_LANG_SPECS["en"],
            cpio_size_bytes=self.report_primary.stages[3].evidence["cpio_archive_bytes"],
            cpio_entry_count=self.report_primary.stages[3].evidence["cpio_entry_count"],
            cpio_sha256=self.report_primary.stages[3].evidence["cpio_sha256"],
            lock_table_count=13,
            tmpfs_budget_audit=mock.MagicMock(
                within_budget=True,
                volatile_tmpfs_overlay_mib=self.report_primary.stages[3].evidence["volatile_tmpfs_overlay_mib"],
            ),
            stage_b_appfw_sha256=self.report_primary.stages[3].evidence["stage_b_appfw_sha256"],
            stage_b_wlan_rsrc_sha256=self.report_primary.stages[3].evidence["stage_b_wlan_rsrc_sha256"],
            all_checks_passed=True,
            errors=(),
            cpio_deterministic_metadata_ok=True,
            init2_failsafe_audit_valid=True,
            init2_ld_preload_audit_valid=True,
            rollback_all_matched=True,
            persistent_emmc_writes_authorized=False,
            cp_mutation_bytes=0,
            wbi_mutation_bytes=0,
            sandbox_drill=mock.MagicMock(
                passed_count=9,
                scenario_count=9,
                clean_mount_verified=True,
                all_faults_fail_closed=True,
                total_emmc_mutation_bytes=0,
                total_cp_mutation_bytes=0,
                total_wbi_mutation_bytes=0,
            ),
        )
        with tempfile.TemporaryDirectory() as td:
            with mock.patch("fx6_closure.stage_b_rehearsal_orchestrator.verify_stage_b_ram_overlay_v2", return_value=stub_v2):
                r_wf = _run_stage_r3(
                    fx6_lib_dir=DEFAULT_FX6_DONOR_LIB_DIR,
                    fx3_modules_dir=DEFAULT_FX3_MODULES_DIR,
                    lang="en",
                    use_clean_room=self.use_clean_room,
                    volatile_overlay_dir=Path(td) / "v1",
                    faults=StageBRehearsalFaultInjection(r3_violate_wf12_airplane=True),
                )
                self.assertFalse(r_wf.passed)
                self.assertFalse(r_wf.evidence["wf12_immunity_ok"])

                r_lk = _run_stage_r3(
                    fx6_lib_dir=DEFAULT_FX6_DONOR_LIB_DIR,
                    fx3_modules_dir=DEFAULT_FX3_MODULES_DIR,
                    lang="en",
                    use_clean_room=self.use_clean_room,
                    volatile_overlay_dir=Path(td) / "v2",
                    faults=StageBRehearsalFaultInjection(r3_corrupt_lock_table=True),
                )
                self.assertFalse(r_lk.passed)
                self.assertEqual(r_lk.evidence["lock_table_count"], 12)

                r_mem = _run_stage_r3(
                    fx6_lib_dir=DEFAULT_FX6_DONOR_LIB_DIR,
                    fx3_modules_dir=DEFAULT_FX3_MODULES_DIR,
                    lang="en",
                    use_clean_room=self.use_clean_room,
                    volatile_overlay_dir=Path(td) / "v3",
                    faults=StageBRehearsalFaultInjection(r3_exceed_tmpfs_budget=True),
                )
                self.assertFalse(r_mem.passed)
                self.assertFalse(r_mem.evidence["tmpfs_within_budget"])

    def test_22_r4_fault_nop_count_nonzero_fails_closed(self) -> None:
        res_nop, _ = _run_stage_r4(
            repo_root=DEFAULT_REPO_ROOT,
            use_clean_room=self.use_clean_room,
            faults=StageBRehearsalFaultInjection(r4_nop_count=1),
        )
        self.assertFalse(res_nop.passed)
        self.assertEqual(res_nop.status, STATUS_FAIL_CLOSED)
        self.assertEqual(res_nop.evidence["qmp_nop_count"], 1)

    def test_23_r4_fault_corrupt_edid_and_zero_4lang_delta(self) -> None:
        res_edid, _ = _run_stage_r4(
            repo_root=DEFAULT_REPO_ROOT,
            use_clean_room=self.use_clean_room,
            faults=StageBRehearsalFaultInjection(r4_corrupt_edid_checksum=True),
        )
        self.assertFalse(res_edid.passed)
        self.assertFalse(res_edid.evidence["edid_256b_valid"])

        res_lang, pairs = _run_stage_r4(
            repo_root=DEFAULT_REPO_ROOT,
            use_clean_room=self.use_clean_room,
            faults=StageBRehearsalFaultInjection(r4_zero_lang_pair_delta="schinese_vs_tchinese"),
        )
        self.assertFalse(res_lang.passed)
        self.assertEqual(pairs, 5)

    def test_24_r5_fault_lingering_mount_residual_emmc_and_sticky_oneshot(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tp = Path(td)
            ov = tp / "ov"
            (ov / "tmp" / "fx6_overlay").mkdir(parents=True)
            (ov / "tmp" / "fx6_overlay" / "stage_b_overlay_manifest.json").write_text("{}", encoding="utf-8")

            r_mnt = _run_stage_r5(
                volatile_overlay_dir=ov,
                h2_dir=tp / "h2_m",
                fa0080_tbl=self._fa0080_tbl,
                stock_bk4=self._stock_bk4,
                faults=StageBRehearsalFaultInjection(r5_lingering_overlay_mount=True),
            )
            self.assertFalse(r_mnt.passed)
            self.assertEqual(r_mnt.evidence["lingering_mounts"], 1)

            r_wr = _run_stage_r5(
                volatile_overlay_dir=tp / "ov2",
                h2_dir=tp / "h2_w",
                fa0080_tbl=self._fa0080_tbl,
                stock_bk4=self._stock_bk4,
                faults=StageBRehearsalFaultInjection(r5_residual_emmc_writes=4096),
            )
            self.assertFalse(r_wr.passed)
            self.assertEqual(r_wr.evidence["emmc_residual_writes"], 4096)

            r_one = _run_stage_r5(
                volatile_overlay_dir=tp / "ov3",
                h2_dir=tp / "h2_o",
                fa0080_tbl=self._fa0080_tbl,
                stock_bk4=self._stock_bk4,
                faults=StageBRehearsalFaultInjection(r5_sticky_mod_arm_once=True),
            )
            self.assertFalse(r_one.passed)
            self.assertTrue(r_one.evidence["mod_arm_once_present"])

    def _run_r6_drift_surface(self, surface: str) -> object:
        import hashlib

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

    def test_25_r6_fault_bk4_1byte_drift_detected(self) -> None:
        rec = self._run_r6_drift_surface("BK4")
        self.assertFalse(rec.all_checks_passed)
        self.assertIn(ANOMALY_BK4_PERSISTENT_NVRAM_LEAK, rec.anomaly_codes)
        self.assertIn("p2_backup_bin", rec.drifted_items)

    def test_26_r6_fault_c2pa_1byte_drift_detected(self) -> None:
        rec = self._run_r6_drift_surface("C2PA")
        self.assertFalse(rec.all_checks_passed)
        self.assertFalse(rec.c2pa_keystore_untouched)
        self.assertGreater(rec.calibration_mutation_bytes, 0)
        self.assertIn(ANOMALY_C2PA_OR_CALIBRATION_DRIFT, rec.anomaly_codes)

    def test_27_r6_fault_wbi2_1byte_drift_detected(self) -> None:
        rec = self._run_r6_drift_surface("WBI2")
        self.assertFalse(rec.all_checks_passed)
        self.assertGreater(rec.wbi_mutation_bytes, 0)
        self.assertIn(ANOMALY_WBI2_HEADER_DRIFT, rec.anomaly_codes)

    def test_28_r6_fault_cp_and_sector0_1byte_drift_detected(self) -> None:
        rec_cp = self._run_r6_drift_surface("CP")
        self.assertFalse(rec_cp.all_checks_passed)
        self.assertGreater(rec_cp.cp_mutation_bytes, 0)
        self.assertIn(ANOMALY_CP_BYTE_MUTATION, rec_cp.anomaly_codes)

        rec_s0 = self._run_r6_drift_surface("sector0")
        self.assertFalse(rec_s0.all_checks_passed)
        self.assertGreater(rec_s0.sector0_mutation_bytes, 0)
        self.assertIn(ANOMALY_SECTOR0_TAMPER, rec_s0.anomaly_codes)

    def test_29_r6_orchestrator_flips_fail_closed_on_tamper_control(self) -> None:
        fake_rep = mock.MagicMock(
            all_checks_passed=True,
            all_10_scenarios_passed=True,
            passed_scenario_count=10,
            scenario_count=10,
            report_sha256="0" * 64,
        )
        fake_rep.to_dict.return_value = {}
        with (
            mock.patch("fx6_closure.stage_b_rehearsal_orchestrator.run_stage_b_post_trial_forensic_audit", return_value=fake_rep),
            mock.patch("fx6_closure.stage_b_rehearsal_orchestrator.verify_stage_b_post_trial_report", return_value=mock.MagicMock(valid=True)),
        ):
            r6_bad, _ = _run_stage_r6(
                h0_dir=self._h0_base_dir,
                h2_dir=self._h2_base_dir,
                fx6_lib_dir=DEFAULT_FX6_DONOR_LIB_DIR,
                fx3_modules_dir=DEFAULT_FX3_MODULES_DIR,
                use_clean_room=self.use_clean_room,
                faults=StageBRehearsalFaultInjection(r6_tamper_negative_control=True),
            )
        self.assertFalse(r6_bad.passed)
        self.assertEqual(r6_bad.status, STATUS_FAIL_CLOSED)

    # ------------------------------------------------------------------
    # Certificate Tamper Detection & Clean-Room Parity
    # ------------------------------------------------------------------

    def test_30_certificate_verifier_rejects_tampered_digest_and_redlines(self) -> None:
        bad_digest = copy.deepcopy(self.report_primary.to_dict())
        bad_digest["rehearsal_digest_sha256"] = "f" * 64
        res_d = verify_stage_b_rehearsal_certificate(bad_digest)
        self.assertFalse(res_d.valid)
        self.assertFalse(res_d.digest_matched)

        bad_schema = copy.deepcopy(self.report_primary.to_dict())
        bad_schema["schema_version"] = "wrong_schema_v0"
        res_s = verify_stage_b_rehearsal_certificate(bad_schema)
        self.assertFalse(res_s.valid)
        self.assertFalse(res_s.schema_ok)

        for key, val in (
            ("persistent_emmc_writes_authorized", True),
            ("persistent_write_release", True),
            ("hardware_live_attachment_authorized", True),
            ("cp_mutation_bytes", 1),
            ("wbi_mutation_bytes", 1),
            ("calibration_mutation_bytes", 1),
        ):
            tampered = copy.deepcopy(self.report_primary.to_dict())
            tampered[key] = val
            tampered["rehearsal_digest_sha256"] = compute_rehearsal_digest_sha256(tampered)
            res_t = verify_stage_b_rehearsal_certificate(tampered)
            self.assertFalse(res_t.valid)
            self.assertFalse(res_t.safety_redlines_ok)

    def test_31_clean_room_mode_stages_pass_independently(self) -> None:
        f = StageBRehearsalFaultInjection()
        r0 = _run_stage_r0(use_clean_room=True, faults=f)
        r1 = _run_stage_r1(repo_root=DEFAULT_REPO_ROOT, use_clean_room=True, faults=f)
        r4, pairs = _run_stage_r4(repo_root=DEFAULT_REPO_ROOT, use_clean_room=True, faults=f)
        self.assertTrue(r0.passed and r1.passed and r4.passed)
        self.assertEqual(pairs, 6)
        with tempfile.TemporaryDirectory() as td:
            tp = Path(td)
            r2, tbl, bk4 = _run_stage_r2(h0_dir=tp / "h0", use_clean_room=True, faults=f)
            r5 = _run_stage_r5(volatile_overlay_dir=tp / "ov", h2_dir=tp / "h2", fa0080_tbl=tbl, stock_bk4=bk4, faults=f)
            rec = verify_stage_b_post_trial_zero_persistence(tp / "h0", tp / "h2", synthetic_clean_room=True)
            self.assertTrue(r2.passed and r5.passed and rec.all_checks_passed)
            self.assertEqual(rec.matched_item_count, 16)

    def test_32_unsupported_language_and_bad_drift_target_raise(self) -> None:
        with self.assertRaises(ValueError):
            run_stage_b_closed_loop_rehearsal(lang="fr")
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(ValueError):
                _run_stage_r5(
                    volatile_overlay_dir=Path(td) / "ov",
                    h2_dir=Path(td) / "h2",
                    fa0080_tbl=self._fa0080_tbl,
                    stock_bk4=self._stock_bk4,
                    faults=StageBRehearsalFaultInjection(r6_drift_surface="UNKNOWN_SURFACE"),
                )

    def test_33_cli_rehearse_stage_b_closed_loop_outputs_and_exit_codes(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tp = Path(td)
            md_path = tp / "rehearsal.md"
            out_path = tp / "rehearsal.json"
            with mock.patch(
                "fx6_closure.stage_b_rehearsal_orchestrator.run_stage_b_closed_loop_rehearsal",
                return_value=self.report_primary,
            ) as mock_run:
                buf = io.StringIO()
                with mock.patch("sys.stdout", buf):
                    rc = fx6_cli_main(
                        [
                            "rehearse-stage-b-closed-loop",
                            "--clean-room",
                            "--lang",
                            "schinese",
                            "--json",
                            "--markdown-out",
                            str(md_path),
                            "--output",
                            str(out_path),
                        ]
                    )
                self.assertEqual(rc, 0)
                mock_run.assert_called_once()
                _, kwargs = mock_run.call_args
                self.assertTrue(kwargs["synthetic_clean_room"])
                self.assertEqual(kwargs["lang"], "schinese")

                stdout_json = json.loads(buf.getvalue())
                out_json = json.loads(out_path.read_text(encoding="utf-8"))
                md_text = md_path.read_text(encoding="utf-8")
                self.assertEqual(stdout_json, out_json)
                self.assertEqual(stdout_json["schema_version"], STAGE_B_REHEARSAL_SCHEMA)
                self.assertTrue(stdout_json["rehearsal_passed"])
                self.assertFalse(stdout_json["hardware_live_attachment_authorized"])
                self.assertFalse(stdout_json["persistent_emmc_writes_authorized"])
                self.assertIn("Stage-B `R0..R6` Closed-Loop Hardware Rehearsal Certificate", md_text)
                self.assertIn(stdout_json["rehearsal_digest_sha256"], md_text)

                buf_summary = io.StringIO()
                with mock.patch("sys.stdout", buf_summary):
                    rc_sum = fx6_cli_main(["rehearse-stage-b-closed-loop"])
                self.assertEqual(rc_sum, 0)
                self.assertIn("status=OK", buf_summary.getvalue())
                self.assertIn("stages=7/7", buf_summary.getvalue())

        failed_rep = copy.deepcopy(self.report_primary)
        with mock.patch(
            "fx6_closure.stage_b_rehearsal_orchestrator.run_stage_b_closed_loop_rehearsal",
            return_value=StageBClosedLoopRehearsalReport(
                **{
                    **failed_rep.to_dict(),
                    "rehearsal_passed": False,
                    "status": STATUS_FAIL_CLOSED,
                    "passed_stage_count": 6,
                    "failed_stage_ids": ("R0",),
                }
            ),
        ):
            buf = io.StringIO()
            with mock.patch("sys.stdout", buf):
                rc_fail = fx6_cli_main(["rehearse-stage-b-closed-loop"])
            self.assertEqual(rc_fail, 1)
            self.assertIn("status=FAILED", buf.getvalue())

    def test_34_markdown_renderer_contains_all_stage_rows(self) -> None:
        md = render_stage_b_rehearsal_markdown(self.report_primary)
        for sid in REHEARSAL_STAGE_IDS:
            self.assertIn(f"`{sid}`", md)
        self.assertIn("`REHEARSAL_PASSED`", md)
        self.assertIn("`rehearsal_passed=True`", md)


if __name__ == "__main__":
    unittest.main()
