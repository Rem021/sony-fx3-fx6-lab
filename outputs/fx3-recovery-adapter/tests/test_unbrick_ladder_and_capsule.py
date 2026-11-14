"""Dual-mode unit tests for Phase 47 Tier-0..Tier-4 Unbrick Escalation Ladder & `p1` VFAT Capsule Verifier.

Passes in BOTH:
- Local Donor `O_RDONLY` mode (verifies real FX3 `2.05/nflasha1` via `os.O_RDONLY`)
- `FX3_FX6_FORCE_CLEAN_ROOM=1` mode (deterministic synthetic fixtures)
Designed for `<1s` total execution time with zero binary/bytecode residue.
"""

from __future__ import annotations

from contextlib import redirect_stdout
from hashlib import sha256
import io
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import time
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import fx3_recovery
from fx3_recovery import __main__ as fx3_cli
from fx3_recovery.fat import FatP1
from fx3_recovery.files import ROOT, is_forced_clean_room, resolve_donor_path
from fx3_recovery.unbrick_ladder_and_capsule_verifier import (
    ALLOW_BOOT_PARTITION_TARGETING,
    ALLOW_DESTRUCTIVE_FASTBOOT,
    ALLOW_PERSISTENT_JIRITSU_WRITES,
    CAPSULE_SCHEMA,
    DONOR_P1_205_RELPATH,
    EMMC_WRITE_BYTES,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    REQUIRED_FSYNC_ORDER,
    SCENARIO_IDS,
    THERMAL_ABORT_TEMP_C,
    UNBRICK_LADDER_SCHEMA,
    USBPD_BROWNOUT_MIN_MV,
    WBI_MUTATION_BYTES,
    RecoveryTier,
    ScenarioSpec,
    audit_capsule_fsync_order,
    audit_recovery_pillars_dual_mode,
    build_p1_vfat_rollback_capsule,
    default_12_scenarios,
    evaluate_unbrick_scenario,
    run_12_scenario_escalation_matrix,
    run_unbrick_ladder_and_capsule_suite,
    verify_p1_vfat_capsule,
)


def _patch_fat_entry_both_mirrors(data: bytearray, fat_type: str, cluster: int, val: int) -> None:
    u16 = lambda at: struct.unpack_from("<H", data, at)[0]
    reserved = u16(14)
    fat_sectors = u16(22)
    fat1_off = reserved * 512
    fat2_off = fat1_off + fat_sectors * 512
    for base in (fat1_off, fat2_off):
        if fat_type == "FAT12":
            at = base + cluster + cluster // 2
            cur = struct.unpack_from("<H", data, at)[0]
            if cluster & 1:
                cur = (cur & 0x000F) | ((val & 0xFFF) << 4)
            else:
                cur = (cur & 0xF000) | (val & 0xFFF)
            struct.pack_into("<H", data, at, cur)
        else:
            struct.pack_into("<H", data, base + cluster * 2, val & 0xFFFF)


class UnbrickLadderAndCapsuleTests(unittest.TestCase):
    def setUp(self) -> None:
        self._sandbox = (
            ROOT / "outputs" / "fx3-recovery-adapter" / f".tmp-ladder-test-{os.getpid()}-{time.time_ns()}"
        )

    def tearDown(self) -> None:
        shutil.rmtree(self._sandbox, ignore_errors=True)

    def test_01_safety_constants_and_package_exports(self) -> None:
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(ALLOW_BOOT_PARTITION_TARGETING)
        self.assertFalse(ALLOW_DESTRUCTIVE_FASTBOOT)
        self.assertFalse(ALLOW_PERSISTENT_JIRITSU_WRITES)
        self.assertEqual(WBI_MUTATION_BYTES, 0)
        self.assertEqual(EMMC_WRITE_BYTES, 0)
        self.assertEqual(fx3_recovery.UNBRICK_LADDER_SCHEMA, UNBRICK_LADDER_SCHEMA)
        self.assertIn("run_unbrick_ladder_and_capsule_suite", fx3_recovery.__all__)
        self.assertIn("verify_p1_vfat_capsule", fx3_recovery.__all__)
        self.assertIn("build_p1_vfat_rollback_capsule", fx3_recovery.__all__)

    def test_02_default_12_scenarios_catalogue_and_order(self) -> None:
        specs = default_12_scenarios()
        self.assertEqual(len(specs), 12)
        self.assertEqual(tuple(s.scenario_id for s in specs), SCENARIO_IDS)
        self.assertEqual([s.scenario_number for s in specs], list(range(1, 13)))

    def test_03_s01_clean_stage_ab_power_cycle_reboot_tier0(self) -> None:
        res = evaluate_unbrick_scenario(default_12_scenarios()[0])
        self.assertTrue(res.passed)
        self.assertEqual(res.selected_tier, RecoveryTier.TIER_0)
        self.assertEqual(res.minimal_privilege_tier, RecoveryTier.TIER_0)
        self.assertTrue(res.stock_fx3_boot_restored)
        self.assertEqual(res.emmc_write_bytes, 0)
        self.assertEqual(res.wbi_mutation_bytes, 0)
        self.assertFalse(res.persistent_emmc_writes_authorized)

    def test_04_s02_p1_vfat_boot_counter_oneshot_latch(self) -> None:
        res = evaluate_unbrick_scenario(default_12_scenarios()[1])
        self.assertTrue(res.passed)
        self.assertEqual(res.selected_tier, RecoveryTier.TIER_0)
        self.assertTrue(res.details["oneshot_latch_tripped"])
        self.assertFalse(res.details["sd_removal_required"])
        self.assertTrue(res.stock_fx3_boot_restored)

    def test_05_s03_wf12_00342260_patched_prevention_and_unpatched_cold_cycle(self) -> None:
        patched = evaluate_unbrick_scenario(default_12_scenarios()[2])
        self.assertTrue(patched.passed)
        self.assertTrue(patched.details["prevented_on_patched_trial"])
        self.assertEqual(patched.details["notice_code"], "00342260")

        unpatched_cold = evaluate_unbrick_scenario(
            ScenarioSpec(
                3,
                "S03_WF12_00342260_WIRELESS_HANG",
                "Unpatched WF-12 cold power cycle",
                {
                    "notice_code": "00342260",
                    "led_symptom": "6L+9S",
                    "p12_0x70d4_patched": False,
                    "bk4_airplane_shadow": False,
                    "unpatched_trial_cold_power_cycle_s": 60,
                },
            )
        )
        self.assertTrue(unpatched_cold.passed)
        self.assertTrue(unpatched_cold.details["cleared_on_unpatched_cold_power_cycle"])

        unpatched_insufficient = evaluate_unbrick_scenario(
            ScenarioSpec(
                3,
                "S03_WF12_00342260_WIRELESS_HANG",
                "Insufficient cold power cycle",
                {
                    "notice_code": "00342260",
                    "led_symptom": "6L+9S",
                    "p12_0x70d4_patched": False,
                    "bk4_airplane_shadow": False,
                    "unpatched_trial_cold_power_cycle_s": 5,
                },
            )
        )
        self.assertFalse(unpatched_insufficient.passed)

    def test_06_s04_0x100d_early_init_appfw_abort_tier0_skip(self) -> None:
        res = evaluate_unbrick_scenario(default_12_scenarios()[3])
        self.assertTrue(res.passed)
        self.assertEqual(res.selected_tier, RecoveryTier.TIER_0)
        self.assertTrue(res.details["oneshot_hook_skipped"])
        self.assertTrue(res.stock_fx3_boot_restored)
        self.assertEqual(res.emmc_write_bytes, 0)

    def test_07_s05_macos26_iousbhost_0xe00002be_stall_and_h0_retry(self) -> None:
        res = evaluate_unbrick_scenario(default_12_scenarios()[4])
        self.assertTrue(res.passed)
        self.assertEqual(res.selected_tier, RecoveryTier.TIER_1)
        self.assertEqual(res.details["active_backend"], "IOUSBHost")
        self.assertEqual(res.details["stall_retransmit_count"], 0)
        self.assertEqual(res.details["service_vid_pid"], "054C:0336")
        self.assertGreaterEqual(res.details["exclusive_access_retries"], 1)

    def test_08_s06_shifted_vma_v702_p1_autolocator_rejects_v200_offsets(self) -> None:
        res = evaluate_unbrick_scenario(default_12_scenarios()[5])
        self.assertTrue(res.passed)
        self.assertEqual(res.selected_tier, RecoveryTier.TIER_2)
        self.assertTrue(res.details["hardcoded_v200_rejected_fail_closed"])
        self.assertTrue(res.details["corrupted_prologue_rejected_fail_closed"])
        self.assertTrue(res.details["rollback_byte_exact"])
        self.assertEqual(len(res.details["located_offsets"]), 4)

    def test_09_s07_corrupted_truncated_h0_emmc_stuck_bus_blocks_h1(self) -> None:
        res = evaluate_unbrick_scenario(default_12_scenarios()[6])
        self.assertTrue(res.passed)
        self.assertEqual(res.selected_tier, RecoveryTier.TIER_4)
        self.assertEqual(res.disposition, "BLOCKED_FAIL_CLOSED")
        self.assertTrue(res.h1_entry_blocked)
        self.assertTrue(res.details["healthy_p1_passed"])

    def test_10_s08_vmc_bncm1_ltc_cable_blocks_tier3_until_unplugged(self) -> None:
        res = evaluate_unbrick_scenario(default_12_scenarios()[7])
        self.assertTrue(res.passed)
        self.assertEqual(res.selected_tier, RecoveryTier.TIER_3)
        self.assertTrue(res.details["blocked_while_ltc_plugged"])
        self.assertEqual(res.details["unplugged_1v8_status"], "VERIFIED_TIER3_OPEN_DRAIN_FIXTURE")
        self.assertTrue(res.details["unplugged_3v3_open_drain_ok"])
        self.assertTrue(res.details["push_pull_rejected"])

    def test_11_s09_destructive_fastboot_commands_blocked_fail_closed(self) -> None:
        res = evaluate_unbrick_scenario(default_12_scenarios()[8])
        self.assertTrue(res.passed)
        self.assertEqual(res.selected_tier, RecoveryTier.TIER_3)
        self.assertEqual(res.disposition, "BLOCKED_FAIL_CLOSED")
        self.assertTrue(res.details["boot_chain_firewall_blocked"])
        self.assertEqual(len(res.details["blocked_commands"]), 5)
        self.assertEqual(len(res.details["permitted_readonly_commands"]), 3)
        self.assertFalse(res.persistent_emmc_writes_authorized)

    def test_12_s10_ld_so_preload_dynamic_busybox_rejected_prepackaging(self) -> None:
        res = evaluate_unbrick_scenario(default_12_scenarios()[9])
        self.assertTrue(res.passed)
        self.assertEqual(res.selected_tier, RecoveryTier.TIER_2)
        self.assertTrue(res.details["deadlock_rejected"])
        self.assertEqual(res.details["scoped_appfw_launcher_status"], "SCOPED_APPFW_LD_PRELOAD_OK")
        self.assertEqual(res.details["static_binary_status"], "STATIC_BINARY_OK")

    def test_13_s11_cross_body_fx6_wbi2_injection_rejected_zero_wbi_mutation(self) -> None:
        res = evaluate_unbrick_scenario(default_12_scenarios()[10])
        self.assertTrue(res.passed)
        self.assertEqual(res.selected_tier, RecoveryTier.TIER_2)
        self.assertEqual(res.disposition, "BLOCKED_FAIL_CLOSED")
        self.assertTrue(res.h1_entry_blocked)
        self.assertEqual(res.wbi_mutation_bytes, 0)
        self.assertEqual(res.emmc_write_bytes, 0)

    def test_14_s12_thermal_90c_and_usbpd_780v_brownout_graceful_abort(self) -> None:
        both = evaluate_unbrick_scenario(default_12_scenarios()[11])
        self.assertTrue(both.passed)
        self.assertEqual(both.disposition, "ABORTED_GRACEFUL")
        self.assertEqual(both.emmc_write_bytes, 0)
        self.assertTrue(both.h1_entry_blocked)

        thermal_only = evaluate_unbrick_scenario(
            ScenarioSpec(
                12,
                "S12_THERMAL_OR_USBPD_BROWNOUT_ABORT",
                "Thermal >= 90C only",
                {"temp_c": THERMAL_ABORT_TEMP_C, "vbus_mv": 9000},
            )
        )
        self.assertTrue(thermal_only.passed)
        self.assertTrue(thermal_only.details["thermal_triggered"])
        self.assertFalse(thermal_only.details["brownout_triggered"])

        brownout_only = evaluate_unbrick_scenario(
            ScenarioSpec(
                12,
                "S12_THERMAL_OR_USBPD_BROWNOUT_ABORT",
                "USB-PD < 7.80V only",
                {"temp_c": 45.0, "vbus_mv": USBPD_BROWNOUT_MIN_MV - 50},
            )
        )
        self.assertTrue(brownout_only.passed)
        self.assertFalse(brownout_only.details["thermal_triggered"])
        self.assertTrue(brownout_only.details["brownout_triggered"])

    def test_15_p1_vfat_fat12_capsule_83_lfn_fsync_and_two_pass_sha256(self) -> None:
        cap_bytes, meta = build_p1_vfat_rollback_capsule(fat_type="FAT12", boot_attempts=1)
        ver = verify_p1_vfat_capsule(cap_bytes, expected_sha256=meta["capsule_sha256"])
        self.assertTrue(ver.valid, ver.errors)
        self.assertEqual(ver.schema, CAPSULE_SCHEMA)
        self.assertEqual(ver.fat_type, "FAT12")
        self.assertTrue(ver.fat_mirrors_equal)
        self.assertTrue(ver.entries_83_and_lfn_valid)
        self.assertTrue(ver.two_pass_sha256_match)
        self.assertEqual(ver.fsync_order, REQUIRED_FSYNC_ORDER)
        self.assertTrue(ver.fsync_order_valid)
        self.assertTrue(ver.oneshot_latch_tripped)
        self.assertFalse(ver.persistent_emmc_writes_authorized)
        # Compatible with FatP1 parser
        fat = FatP1(cap_bytes)
        self.assertIn("/capsule/failsafe-hook-capsule.cfg", fat.files)

    def test_16_p1_vfat_fat16_capsule_4100_clusters_83_lfn_and_sha256(self) -> None:
        cap_bytes, meta = build_p1_vfat_rollback_capsule(fat_type="FAT16", boot_attempts=2, max_boot_attempts=1)
        ver = verify_p1_vfat_capsule(cap_bytes, expected_sha256=meta["capsule_sha256"])
        self.assertTrue(ver.valid, ver.errors)
        self.assertEqual(ver.fat_type, "FAT16")
        self.assertEqual(ver.cluster_count, 4100)
        self.assertTrue(ver.entries_83_and_lfn_valid)
        self.assertTrue(ver.two_pass_sha256_match)
        self.assertTrue(ver.oneshot_latch_tripped)
        self.assertTrue(any(e.lfn_name == "capsule-manifest.json" for e in ver.entries))

    def test_17_capsule_verifier_rejects_fat_mirror_mismatch(self) -> None:
        cap_bytes, _ = build_p1_vfat_rollback_capsule(fat_type="FAT12", boot_attempts=1)
        mut = bytearray(cap_bytes)
        # Flip one byte in FAT2 (sector 33)
        mut[33 * 512 + 10] ^= 0xFF
        ver = verify_p1_vfat_capsule(bytes(mut))
        self.assertFalse(ver.valid)
        self.assertFalse(ver.fat_mirrors_equal)

    def test_18_capsule_verifier_rejects_bad_lfn_checksum(self) -> None:
        cap_bytes, _ = build_p1_vfat_rollback_capsule(fat_type="FAT12", boot_attempts=1)
        mut = bytearray(cap_bytes)
        # Root dir starts at sector 65; find first LFN entry (attr == 0x0F) and corrupt checksum byte +13
        root_off = 65 * 512
        for off in range(root_off, root_off + 512 * 32, 32):
            if mut[off + 11] == 0x0F:
                mut[off + 13] ^= 0x01
                break
        ver = verify_p1_vfat_capsule(bytes(mut))
        self.assertFalse(ver.valid)

    def test_19_capsule_verifier_rejects_invalid_83_filename_characters(self) -> None:
        cap_bytes, _ = build_p1_vfat_rollback_capsule(fat_type="FAT12", boot_attempts=1, include_lfn=False)
        mut = bytearray(cap_bytes)
        root_off = 65 * 512
        # Corrupt BOOT entry name with illegal lowercase/control byte
        mut[root_off + 0] = ord(" ")
        ver = verify_p1_vfat_capsule(bytes(mut))
        self.assertFalse(ver.valid)

    def test_20_capsule_verifier_rejects_cyclic_fat_cluster_chain(self) -> None:
        cap_bytes, _ = build_p1_vfat_rollback_capsule(fat_type="FAT16", boot_attempts=1)
        mut = bytearray(cap_bytes)
        # Cluster 2 is /BOOT directory; point cluster 2 back to cluster 2
        _patch_fat_entry_both_mirrors(mut, "FAT16", 2, 2)
        ver = verify_p1_vfat_capsule(bytes(mut))
        self.assertFalse(ver.valid)

    def test_21_capsule_verifier_rejects_cross_linked_clusters(self) -> None:
        cap_bytes, _ = build_p1_vfat_rollback_capsule(fat_type="FAT12", boot_attempts=1, include_lfn=False)
        mut = bytearray(cap_bytes)
        # Root entry 0 is BOOT (cluster 2), entry 1 is CAPSULE (cluster 3); cross-link entry 1 to cluster 2
        root_off = 65 * 512
        struct.pack_into("<H", mut, root_off + 32 + 26, 2)
        ver = verify_p1_vfat_capsule(bytes(mut))
        self.assertFalse(ver.valid)

    def test_22_capsule_verifier_rejects_fsync_out_of_order(self) -> None:
        cap_bytes, meta = build_p1_vfat_rollback_capsule(fat_type="FAT12", boot_attempts=1)
        bad_order = (
            "stage_tmp_write",
            "atomic_replace",  # fsync skipped before rename!
            "fsync_tmp_file",
            "verify_pass1_sha256_o_rdonly",
            "fsync_parent_dir",
            "verify_pass2_sha256_o_rdonly",
        )
        ok, _ = audit_capsule_fsync_order(bad_order)
        self.assertFalse(ok)
        ver = verify_p1_vfat_capsule(
            cap_bytes,
            expected_sha256=meta["capsule_sha256"],
            fsync_order_override=bad_order,
        )
        self.assertFalse(ver.valid)
        self.assertFalse(ver.fsync_order_valid)

    def test_23_capsule_verifier_rejects_external_sha256_mismatch(self) -> None:
        cap_bytes, _ = build_p1_vfat_rollback_capsule(fat_type="FAT12", boot_attempts=1)
        ver = verify_p1_vfat_capsule(cap_bytes, expected_sha256="0" * 64)
        self.assertFalse(ver.valid)

    def test_24_capsule_verifier_rejects_manifest_tamper_emmc_auth_true(self) -> None:
        cap_bytes, _ = build_p1_vfat_rollback_capsule(fat_type="FAT12", boot_attempts=1)
        target = b'"persistent_emmc_writes_authorized": false'
        replacement = b'"persistent_emmc_writes_authorized": true '
        idx = cap_bytes.find(target)
        self.assertGreater(idx, 0)
        mut = bytearray(cap_bytes)
        mut[idx : idx + len(target)] = replacement
        ver = verify_p1_vfat_capsule(bytes(mut))
        self.assertFalse(ver.valid)

    def test_25_dual_mode_pillar_audit_local_or_clean_room_o_rdonly(self) -> None:
        cr_audit = audit_recovery_pillars_dual_mode(force_clean_room=True)
        self.assertTrue(cr_audit.passed, cr_audit.errors)
        self.assertEqual(cr_audit.mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(cr_audit.two_pass_stable)
        self.assertEqual(len(cr_audit.autolocator_sites), 4)
        self.assertFalse(cr_audit.persistent_emmc_writes_authorized)

        auto_audit = audit_recovery_pillars_dual_mode()
        self.assertTrue(auto_audit.passed, auto_audit.errors)
        donor_p1 = resolve_donor_path(DONOR_P1_205_RELPATH)
        if not is_forced_clean_room() and donor_p1.is_file():
            self.assertEqual(auto_audit.mode, "LOCAL_DONOR_O_RDONLY")
        else:
            self.assertEqual(auto_audit.mode, "CLEAN_ROOM_SYNTHETIC")

    def test_26_full_suite_report_serializable_and_deterministic(self) -> None:
        r1 = run_unbrick_ladder_and_capsule_suite(force_clean_room=True)
        r2 = run_unbrick_ladder_and_capsule_suite(force_clean_room=True)
        self.assertTrue(r1.all_passed, r1.errors)
        self.assertEqual(r1.scenarios_passed, 12)
        d1 = r1.to_dict()
        d2 = r2.to_dict()
        self.assertEqual(d1, d2)
        encoded = json.dumps(d1, sort_keys=True)
        self.assertIn("VERIFIED_ALL_12_SCENARIOS_AND_CAPSULES", encoded)

    def test_27_unknown_scenario_id_fails_closed(self) -> None:
        with self.assertRaises(ValueError):
            evaluate_unbrick_scenario(ScenarioSpec(99, "S99_UNKNOWN_FAILURE", "unknown"))

    def test_28_cli_verify_unbrick_ladder_clean_room_json_and_summary(self) -> None:
        self._sandbox.parent.mkdir(parents=True, exist_ok=True)
        out_dir = self._sandbox
        # Summary mode (in-process for speed)
        buf_sum = io.StringIO()
        with mock.patch.object(sys, "argv", ["fx3_recovery", "verify-unbrick-ladder", "--clean-room"]):
            with redirect_stdout(buf_sum):
                rc = fx3_cli.main()
        self.assertEqual(rc, 0)
        self.assertIn("scenarios_passed=12/12", buf_sum.getvalue())
        self.assertIn("persistent_emmc_writes_authorized=False", buf_sum.getvalue())

        # JSON + --out mode (real subprocess)
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONPATH"] = str(ROOT / "outputs" / "fx3-recovery-adapter")
        proc = subprocess.run(
            [
                "/usr/bin/python3",
                "-B",
                "-m",
                "fx3_recovery",
                "verify-unbrick-ladder",
                "--clean-room",
                "--json",
                "--out",
                str(out_dir),
            ],
            cwd=str(ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertTrue(payload["all_passed"])
        self.assertEqual(payload["scenarios_passed"], 12)
        self.assertFalse(payload["persistent_emmc_writes_authorized"])
        self.assertTrue((out_dir / "unbrick-ladder-report.json").is_file())

    def test_29_cli_no_raw_bytes_repr_in_output(self) -> None:
        buf = io.StringIO()
        with mock.patch.object(sys, "argv", ["fx3_recovery", "verify-unbrick-ladder", "--clean-room", "--json"]):
            with redirect_stdout(buf):
                rc = fx3_cli.main()
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertNotIn("b'\\x", out)
        self.assertNotIn('b"\\x', out)

    def test_30_total_suite_runtime_under_budget(self) -> None:
        t0 = time.monotonic()
        rep = run_unbrick_ladder_and_capsule_suite()
        elapsed = time.monotonic() - t0
        self.assertTrue(rep.all_passed, rep.errors)
        self.assertLess(elapsed, 0.5)
        self.assertEqual(len(run_12_scenario_escalation_matrix()), 12)


if __name__ == "__main__":
    unittest.main()
