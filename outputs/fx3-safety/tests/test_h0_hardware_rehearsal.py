"""Comprehensive unit & fault-injection tests for Phase 28 H0 Hardware Rehearsal Engine.

All tests are clean-room compatible (passing in both Local Donor mode and
`FX3_FX6_FORCE_CLEAN_ROOM=1`) and execute in < 2 seconds.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fx3_safety.h0_hardware_rehearsal import (
    H0_REHEARSAL_SCHEMA,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    H0RehearsalConfig,
    main as h0_cli_main,
    run_h0_hardware_rehearsal,
    run_stage1_multiport_harness_rehearsal,
    run_stage2_macos_usb_transport_rehearsal,
    run_stage3_runtime_antibrick_rehearsal,
    run_stage4_brick_classifier_matrix_rehearsal,
    run_stage5_p1_autolocator_rehearsal,
)
from fx3_safety.preflight import TIER0_REQUIRED_BACKUPS


REPO_ROOT = Path(__file__).resolve().parents[3]


class H0HardwareRehearsalTests(unittest.TestCase):
    def test_01_hard_locked_module_safety_flags(self) -> None:
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(PERSISTENT_WRITE_RELEASE)

    def test_02_full_6_stage_h0_rehearsal_green_baseline(self) -> None:
        rep = run_h0_hardware_rehearsal(repo_root=REPO_ROOT)
        self.assertEqual(rep.schema, H0_REHEARSAL_SCHEMA)
        self.assertTrue(rep.all_passed, rep.errors)
        self.assertTrue(rep.ready_for_physical_h0_capture)
        self.assertEqual(rep.status, "H0_REHEARSAL_READY_READONLY")
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.persistent_write_release)
        self.assertEqual(len(rep.stages), 6)
        self.assertTrue(all(s.passed for s in rep.stages))
        self.assertEqual(rep.blocked_stages, ())
        self.assertEqual(rep.gates_summary["verified_gates"], 12)
        self.assertTrue(rep.gates_summary["all_12_gates_verified"])
        self.assertFalse(rep.gates_report["persistent_write_release"])

    def test_03_full_6_stage_h0_rehearsal_with_unicorn_and_decoupled_mode(self) -> None:
        rep_uc = run_h0_hardware_rehearsal(repo_root=REPO_ROOT, run_unicorn_verification=True)
        self.assertTrue(rep_uc.all_passed, rep_uc.errors)
        self.assertFalse(rep_uc.persistent_write_release)

        rep_dec = run_h0_hardware_rehearsal(repo_root=REPO_ROOT, force_decoupled_adapter=True)
        self.assertTrue(rep_dec.all_passed, rep_dec.errors)
        self.assertEqual(rep_dec.adapter_mode, "decoupled")
        self.assertFalse(rep_dec.persistent_write_release)

    def test_04_stage1_blocks_standard_raspberry_pi_pico_gp29_hazard(self) -> None:
        rep = run_h0_hardware_rehearsal(repo_root=REPO_ROOT, board="raspberry_pi_pico")
        self.assertFalse(rep.all_passed)
        self.assertFalse(rep.ready_for_physical_h0_capture)
        self.assertFalse(rep.persistent_write_release)
        self.assertEqual(rep.status, "BLOCKED_BY_MULTIPORT_TIER3_HARNESS_REDLINE")
        self.assertIn("S1_multiport_tier3_harness", rep.blocked_stages)
        g12 = [g for g in rep.gates_report["gates"] if g["gate_id"] == "G12_persistent_flash_write_authorization"][0]
        self.assertEqual(g12["status"], "BLOCKED_BY_MULTIPORT_TIER3_HARNESS_REDLINE")

    def test_05_stage1_blocks_missing_open_drain_flag_or_push_pull_drive(self) -> None:
        s1_no_flag = run_stage1_multiport_harness_rehearsal(
            H0RehearsalConfig(compile_flags=())
        )
        self.assertFalse(s1_no_flag.passed)
        self.assertEqual(s1_no_flag.status, "BLOCKED_BY_MULTIPORT_TIER3_HARNESS_REDLINE")

        s1_pp = run_stage1_multiport_harness_rehearsal(
            H0RehearsalConfig(gpio_drive_mode="push_pull", open_drain=False, io_voltage_v=3.3)
        )
        self.assertFalse(s1_pp.passed)
        self.assertEqual(s1_pp.status, "BLOCKED_BY_MULTIPORT_TIER3_HARNESS_REDLINE")

    def test_06_stage1_blocks_wdt_trap_bootrom_read_and_destructive_fastboot(self) -> None:
        s1_wdt = run_stage1_multiport_harness_rehearsal(
            H0RehearsalConfig(uart_probe_address=0xFFFFC000, uart_probe_size=64)
        )
        self.assertFalse(s1_wdt.passed)

        s1_fb = run_stage1_multiport_harness_rehearsal(
            H0RehearsalConfig(
                fastboot_commands=("getvar:version", "flash:p15"),
                caller_force_emmc_auth=True,
                caller_force_destructive_fastboot=True,
            )
        )
        self.assertFalse(s1_fb.passed)
        self.assertFalse(s1_fb.persistent_emmc_writes_authorized)

    def test_07_stage2_blocks_insufficient_macos26_quiescence(self) -> None:
        rep = run_h0_hardware_rehearsal(
            repo_root=REPO_ROOT,
            driver_quiescent=False,
            quiescence_waited_ms=100,
        )
        self.assertFalse(rep.all_passed)
        self.assertEqual(rep.status, "BLOCKED_MSC_DRIVER_ACTIVE")
        self.assertIn("S2_macos_usb_transport_guard", rep.blocked_stages)
        self.assertFalse(rep.persistent_write_release)

    def test_08_stage2_blocks_exclusive_access_0xe00002be_exhaustion(self) -> None:
        s2 = run_stage2_macos_usb_transport_rehearsal(
            H0RehearsalConfig(claim_return_codes=(0xE00002BE, 0xE00002BE, 0xE00002BE, 0xE00002BE))
        )
        self.assertFalse(s2.passed)
        self.assertEqual(s2.status, "FAILED_CLOSED_EXCLUSIVE_ACCESS")
        self.assertEqual(s2.details["backoff_schedule_ms"], [50, 100, 200, 400])

    def test_09_stage2_blocks_usb_stall_without_retransmission(self) -> None:
        s2 = run_stage2_macos_usb_transport_rehearsal(
            H0RehearsalConfig(vendor_control_stall=True)
        )
        self.assertFalse(s2.passed)
        self.assertEqual(s2.status, "STALL_ABORTED_NO_RETRANSMIT")
        self.assertEqual(s2.details["retransmit_count"], 0)

    def test_10_stage2_blocks_senser_v2_rsa_ilce7m5_fail_closed(self) -> None:
        s2 = run_stage2_macos_usb_transport_rehearsal(
            H0RehearsalConfig(
                senser_version=2,
                senser_auth_scheme="rsa_signature",
                senser_challenge_rounds=1,
                senser_model_name="ILCE-7M5",
                senser_rsa_modulus_bits=2048,
            )
        )
        self.assertFalse(s2.passed)
        self.assertEqual(s2.status, "BLOCKED_SENSER_V2_RSA_UNSUPPORTED")
        self.assertTrue(s2.details["fail_closed"])

    def test_11_stage2_blocks_destructive_jiritsu_and_path_traversal(self) -> None:
        s2_fmt = run_stage2_macos_usb_transport_rehearsal(
            H0RehearsalConfig(jiritsu_commands=((0x40, 0x1001, 0x4003, None),))
        )
        self.assertFalse(s2_fmt.passed)
        self.assertEqual(s2_fmt.status, "BLOCKED_DESTRUCTIVE_JIRITSU_FORMAT")

        s2_trav = run_stage2_macos_usb_transport_rehearsal(
            H0RehearsalConfig(
                jiritsu_commands=((0x40, 0x1001, 0x400F, "/tmp/jiritsu/../../etc/ld.so.preload"),)
            )
        )
        self.assertFalse(s2_trav.passed)
        self.assertEqual(s2_trav.status, "BLOCKED_PATH_TRAVERSAL_OR_PERSISTENT_WRITE")

    def test_12_stage2_decoupled_adapter_also_blocks_stall_and_senser_v2(self) -> None:
        s2_stall = run_stage2_macos_usb_transport_rehearsal(
            H0RehearsalConfig(force_decoupled_adapter=True, vendor_control_stall=True)
        )
        self.assertFalse(s2_stall.passed)
        self.assertEqual(s2_stall.adapter_mode, "decoupled")
        self.assertEqual(s2_stall.status, "STALL_ABORTED_NO_RETRANSMIT")
        self.assertEqual(s2_stall.details["retransmit_count"], 0)

        s2_v2 = run_stage2_macos_usb_transport_rehearsal(
            H0RehearsalConfig(
                force_decoupled_adapter=True,
                senser_version=2,
                senser_auth_scheme="rsa_signature",
                senser_model_name="ILCE-7M5",
                senser_rsa_modulus_bits=2048,
            )
        )
        self.assertFalse(s2_v2.passed)
        self.assertEqual(s2_v2.status, "BLOCKED_SENSER_V2_RSA_UNSUPPORTED")

    def test_13_stage3_blocks_ld_so_preload_and_missing_clear_before_exec(self) -> None:
        rep_preload = run_h0_hardware_rehearsal(
            repo_root=REPO_ROOT,
            runtime_script_text='echo "/tmp/evil.so" > /etc/ld.so.preload\n',
        )
        self.assertFalse(rep_preload.all_passed)
        self.assertIn("S3_runtime_antibrick_guards", rep_preload.blocked_stages)
        g12 = [g for g in rep_preload.gates_report["gates"] if g["gate_id"] == "G12_persistent_flash_write_authorization"][0]
        self.assertEqual(g12["status"], "BLOCKED_BY_RUNTIME_ANTIBRICK_REDLINE")

        s3_no_clear = run_stage3_runtime_antibrick_rehearsal(
            H0RehearsalConfig(runtime_script_text="busybox mount --bind /tmp/a /usr/lib/appFw.so\n")
        )
        self.assertFalse(s3_no_clear.passed)
        self.assertIn("LD_SO_PRELOAD_DYNAMIC_BUSYBOX_DEADLOCK", s3_no_clear.details["violation_codes"])

    def test_14_stage3_blocks_busybox_dd_truncation_hazard(self) -> None:
        s3_dd = run_stage3_runtime_antibrick_rehearsal(
            H0RehearsalConfig(
                runtime_script_text="dd if=/tmp/fx6_stage_a/Backup.bin of=/setting/Backup.bin bs=4096\n"
            )
        )
        self.assertFalse(s3_dd.passed)
        self.assertIn("BUSYBOX_DD_TRUNCATION_HAZARD", s3_dd.details["violation_codes"])

    def test_15_stage3_blocks_nflasha10_0x10000009_vfat_exhaustion(self) -> None:
        s3_vfat = run_stage3_runtime_antibrick_rehearsal(
            H0RehearsalConfig(
                nflasha10_used_bytes=11 * 1024 * 1024,
                nflasha10_planned_writes=({"path": "/setting/big.bin", "bytes": 512 * 1024},),
            )
        )
        self.assertFalse(s3_vfat.passed)
        self.assertIn("NFLASHA10_12MIB_VFAT_EXHAUSTION_0x10000009", s3_vfat.details["violation_codes"])

    def test_16_stage3_blocks_camset_bk4_product_model_mutation(self) -> None:
        s3_cam = run_stage3_runtime_antibrick_rehearsal(
            H0RehearsalConfig(
                camset_diff_entries=(
                    {"key": "PRODUCT_MODEL", "bk_id": 0x00010000, "old_value": 4, "new_value": 3},
                )
            )
        )
        self.assertFalse(s3_cam.passed)
        self.assertIn("CAMSET_BK4_PRODUCT_MODEL_MUTATION_BLOCK", s3_cam.details["violation_codes"])

    def test_17_stage3_blocks_pmca_5step_readback_mismatch(self) -> None:
        bad_manifest = {
            "drop_exit_guard_ok": True,
            "tmpfs_staging_ok": True,
            "expected_sha256": "a" * 64,
            "readback_sha256": "b" * 64,
            "rollback_history": ({"slot_id": "slot-1", "sha256": "a" * 64, "bytes": 4096},),
        }
        s3_pmca = run_stage3_runtime_antibrick_rehearsal(
            H0RehearsalConfig(pmca_5step_manifest=bad_manifest)
        )
        self.assertFalse(s3_pmca.passed)
        self.assertIn("PMCA_5STEP_WRITE_GUARD_VIOLATION", s3_pmca.details["violation_codes"])

    def test_18_stage4_brick_classifier_full_6_symptom_matrix_and_wf12_isolation(self) -> None:
        s4_ok = run_stage4_brick_classifier_matrix_rehearsal(H0RehearsalConfig())
        self.assertTrue(s4_ok.passed, s4_ok.errors)
        self.assertEqual(s4_ok.details["symptom_count"], 6)
        self.assertTrue(all(row["passed"] for row in s4_ok.details["matrix"].values()))

        rep_wf12_fail = run_h0_hardware_rehearsal(
            repo_root=REPO_ROOT,
            wireless_fault_isolation_ok=False,
        )
        self.assertFalse(rep_wf12_fail.all_passed)
        self.assertIn("S4_brick_classifier_matrix", rep_wf12_fail.blocked_stages)
        g12 = [g for g in rep_wf12_fail.gates_report["gates"] if g["gate_id"] == "G12_persistent_flash_write_authorization"][0]
        self.assertEqual(g12["status"], "BLOCKED_BY_WIRELESS_FAULT_ISOLATION_REDLINE")

    def test_19_stage5_p1_autolocator_tracks_shifted_v702_and_rollback_sha256(self) -> None:
        s5 = run_stage5_p1_autolocator_rehearsal(
            H0RehearsalConfig(shift_sd=0x240, shift_uc=0x380, vma_bias=0x90000)
        )
        self.assertTrue(s5.passed, s5.errors)
        self.assertTrue(s5.details["byte_length_invariant"])
        self.assertTrue(s5.details["rollback_verified"])
        self.assertTrue(s5.details["squashfs_readback_ok"])
        self.assertEqual(s5.details["pass1_rollback_sha256"], s5.details["pass2_rollback_sha256"])
        self.assertFalse(s5.persistent_emmc_writes_authorized)

    def test_20_stage5_blocks_corrupt_prologue_and_ambiguous_multi_match(self) -> None:
        rep_corrupt = run_h0_hardware_rehearsal(repo_root=REPO_ROOT, corrupt_prologue=True)
        self.assertFalse(rep_corrupt.all_passed)
        self.assertIn("S5_v702_p1_autolocator_rollback", rep_corrupt.blocked_stages)
        g12 = [g for g in rep_corrupt.gates_report["gates"] if g["gate_id"] == "G12_persistent_flash_write_authorization"][0]
        self.assertEqual(g12["status"], "BLOCKED_BY_P1_RECOVERY_BRIDGE_REDLINE")

        s5_amb = run_stage5_p1_autolocator_rehearsal(
            H0RehearsalConfig(duplicate_pattern_ambiguous=True)
        )
        self.assertFalse(s5_amb.passed)
        self.assertEqual(s5_amb.status, "BLOCKED_STAGE5_P1_AUTOLOCATOR")

        s5_dec_bad = run_stage5_p1_autolocator_rehearsal(
            H0RehearsalConfig(force_decoupled_adapter=True, corrupt_prologue=True)
        )
        self.assertFalse(s5_dec_bad.passed)
        self.assertEqual(s5_dec_bad.adapter_mode, "decoupled")

    def test_21_stage6_blocks_invalid_tier0_manifest_or_syscall_trace(self) -> None:
        bad_manifest = {"camera_body_tag": "short", "items": {}}
        rep_man = run_h0_hardware_rehearsal(repo_root=REPO_ROOT, tier0_manifest_override=bad_manifest)
        self.assertFalse(rep_man.all_passed)
        self.assertIn("S6_preflight_12_gate_audit", rep_man.blocked_stages)
        self.assertFalse(rep_man.persistent_write_release)

        bad_trace = [{"nr": 56, "dirfd": -100, "path": "/dev/nflasha", "flags": 0x2, "ret": 3}]
        rep_tr = run_h0_hardware_rehearsal(repo_root=REPO_ROOT, worker_syscall_trace_override=bad_trace)
        self.assertFalse(rep_tr.all_passed)
        self.assertIn("S6_preflight_12_gate_audit", rep_tr.blocked_stages)
        self.assertFalse(rep_tr.persistent_write_release)

    def test_22_stage6_blocks_gate12_redlines_with_persistent_write_release_false(self) -> None:
        for kw, expected in (
            ({"backup_mount_tolerance_ok": False}, "BLOCKED_BY_BACKUP_OR_MOUNT_TOLERANCE_REDLINE"),
            ({"cp_rtos_ok": False}, "BLOCKED_BY_CP_RTOS_REDLINE"),
            ({"uipc_cp_shim_ok": False}, "BLOCKED_BY_UIPC_CP_SHIM_REDLINE"),
        ):
            rep = run_h0_hardware_rehearsal(repo_root=REPO_ROOT, **kw)
            self.assertFalse(rep.all_passed)
            self.assertFalse(rep.persistent_write_release)
            g12 = [g for g in rep.gates_report["gates"] if g["gate_id"] == "G12_persistent_flash_write_authorization"][0]
            self.assertEqual(g12["status"], expected)

    def test_23_report_is_json_serializable_and_cli_succeeds(self) -> None:
        rep = run_h0_hardware_rehearsal(repo_root=REPO_ROOT)
        encoded = json.dumps(rep.to_dict())
        decoded = json.loads(encoded)
        self.assertEqual(decoded["schema"], H0_REHEARSAL_SCHEMA)
        self.assertFalse(decoded["persistent_write_release"])

        with tempfile.TemporaryDirectory() as tmp:
            out_path = Path(tmp) / "h0_rehearsal.json"
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = h0_cli_main(["--repo-root", str(REPO_ROOT), "--out", str(out_path)])
            self.assertEqual(rc, 0)
            stdout_payload = json.loads(buf.getvalue())
            self.assertEqual(stdout_payload["schema"], H0_REHEARSAL_SCHEMA)
            cli_payload = json.loads(out_path.read_text(encoding="utf-8"))
            self.assertTrue(cli_payload["all_passed"])
            self.assertFalse(cli_payload["persistent_write_release"])

    def test_24_clean_room_mode_compatibility(self) -> None:
        with patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            rep = run_h0_hardware_rehearsal(repo_root=REPO_ROOT)
            self.assertTrue(rep.all_passed, rep.errors)
            self.assertFalse(rep.persistent_write_release)
            self.assertEqual(len(TIER0_REQUIRED_BACKUPS), 11)


if __name__ == "__main__":
    unittest.main()
