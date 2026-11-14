"""Clean-room unit tests for 2026 Runtime Anti-Brick Guards & Brick Classifier v2."""

from __future__ import annotations

from pathlib import Path
import struct
import sys
import unittest

HERE = Path(__file__).resolve().parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from fx3_safety.boot_contracts import BK4_HEADER_SIZE, BK4_MAGIC, BK4_SYNC_MARKER
from fx3_safety.brick_classifier import classify_brick_state
from fx3_safety.runtime_antibrick_guards import (
    FX3_PRODUCT_MODEL_ENUM,
    NFLASHA10_DEFAULT_MIN_HEADROOM_BYTES,
    NFLASHA10_LOCKUP_ERROR_CODE,
    NFLASHA10_PARTITION_BYTES,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    V_BUSYBOX_DD_TRUNC,
    V_CAMSET_PRODUCT_MODEL,
    V_LD_SO_PRELOAD,
    V_NFLASHA10_FULL,
    V_PMCA_5STEP,
    audit_busybox_dd_commands,
    audit_camset_bk4_diff,
    audit_ld_so_preload_and_overlay,
    audit_nflasha10_vfat_budget,
    audit_pmca_5step_write_contract,
    evaluate_runtime_antibrick_guards,
)


def _make_valid_bk4(payload: bytes, *, subs: int = 819, word2c: int = 5) -> bytes:
    buf = bytearray(BK4_HEADER_SIZE + len(payload))
    struct.pack_into("<I", buf, 0x04, BK4_SYNC_MARKER)
    buf[0x08] = 1
    buf[0x0C:0x10] = BK4_MAGIC
    struct.pack_into("<IIIII", buf, 0x10, subs, 42, BK4_HEADER_SIZE, len(payload), 0)
    struct.pack_into("<i", buf, 0x2C, word2c)
    buf[BK4_HEADER_SIZE:] = payload
    csum = (sum(buf[0:0x20]) + sum(buf[0x24:])) & 0xFFFFFFFF
    struct.pack_into("<I", buf, 0x20, csum)
    return bytes(buf)


class RuntimeAntibrickGuardTests(unittest.TestCase):
    def test_01_safety_constant_hard_locked(self) -> None:
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertEqual(FX3_PRODUCT_MODEL_ENUM, 4)

    def test_02_ld_so_preload_target_path_and_script_blocked(self) -> None:
        r_path = audit_ld_so_preload_and_overlay(target_paths=["/etc/ld.so.preload"])
        self.assertFalse(r_path.valid)
        self.assertIn(V_LD_SO_PRELOAD, r_path.violation_codes)

        r_script = audit_ld_so_preload_and_overlay(
            script_text="echo /tmp/mod.so > /etc/ld.so.preload\n"
        )
        self.assertFalse(r_script.valid)
        self.assertIn(V_LD_SO_PRELOAD, r_script.violation_codes)

    def test_03_jiritsu_set_file_path_traversal_into_etc_blocked(self) -> None:
        r_trav = audit_ld_so_preload_and_overlay(
            jiritsu_set_file_paths=["/tmp/jiritsu/../../etc/ld.so.preload"]
        )
        self.assertFalse(r_trav.valid)
        self.assertIn(V_LD_SO_PRELOAD, r_trav.violation_codes)

        r_ok = audit_ld_so_preload_and_overlay(
            jiritsu_set_file_paths=["/tmp/jiritsu/libJit.so"]
        )
        self.assertTrue(r_ok.valid)

    def test_04_ram_only_ld_library_path_and_mount_bind_requires_clear_before_exec(self) -> None:
        good = (
            'rm -f "/tmp/mod_arm_once"\n'
            "busybox sync\n"
            "LD_LIBRARY_PATH=/tmp/ram_libs /usr/bin/app\n"
        )
        self.assertTrue(audit_ld_so_preload_and_overlay(script_text=good).valid)

        missing_clear = "LD_LIBRARY_PATH=/tmp/ram_libs /usr/bin/app\n"
        r_missing = audit_ld_so_preload_and_overlay(script_text=missing_clear)
        self.assertFalse(r_missing.valid)
        self.assertIn(V_LD_SO_PRELOAD, r_missing.violation_codes)

        wrong_order = (
            "busybox mount --bind /tmp/appFw.so /usr/lib/appFw.so\n"
            "rm -f /tmp/mod_arm_once\n"
            "busybox sync\n"
        )
        r_order = audit_ld_so_preload_and_overlay(script_text=wrong_order)
        self.assertFalse(r_order.valid)
        self.assertIn(V_LD_SO_PRELOAD, r_order.violation_codes)

    def test_05_commented_clear_before_exec_does_not_bypass(self) -> None:
        commented = (
            "# rm -f /tmp/mod_arm_once\n"
            "# busybox sync\n"
            "busybox mount --bind /tmp/appFw.so /usr/lib/appFw.so\n"
        )
        res = audit_ld_so_preload_and_overlay(script_text=commented)
        self.assertFalse(res.valid)
        self.assertIn(V_LD_SO_PRELOAD, res.violation_codes)

    def test_06_busybox_dd_without_notrunc_blocked(self) -> None:
        res = audit_busybox_dd_commands("busybox dd if=/tmp/patch.bin of=/mnt/sd/existing.img bs=512 seek=1\n")
        self.assertFalse(res.valid)
        self.assertIn(V_BUSYBOX_DD_TRUNC, res.violation_codes)

    def test_07_busybox_dd_with_unverified_notrunc_on_sony_busybox_blocked(self) -> None:
        cmd = "dd if=/tmp/patch.bin of=/mnt/sd/existing.img bs=512 seek=1 conv=notrunc\n"
        res_unverified = audit_busybox_dd_commands(cmd, busybox_notrunc_verified=False)
        self.assertFalse(res_unverified.valid)
        self.assertIn(V_BUSYBOX_DD_TRUNC, res_unverified.violation_codes)

        res_verified = audit_busybox_dd_commands(cmd, busybox_notrunc_verified=True)
        self.assertTrue(res_verified.valid)

    def test_08_busybox_dd_onto_persistent_partition_or_dev_always_blocked(self) -> None:
        for cmd in (
            "dd if=/tmp/x of=/dev/nflasha15 bs=4096 conv=notrunc\n",
            "busybox dd if=/tmp/x of=/setting/Backup.bin conv=notrunc\n",
            "dd if=/tmp/x of=/boot/initrd.img conv=notrunc\n",
        ):
            res = audit_busybox_dd_commands(cmd, busybox_notrunc_verified=True)
            self.assertFalse(res.valid)
            self.assertIn(V_BUSYBOX_DD_TRUNC, res.violation_codes)

    def test_09_busybox_dd_into_tmpfs_staging_allowed(self) -> None:
        res = audit_busybox_dd_commands("busybox dd if=/dev/nflasha1 of=/tmp/stage/p1.bin bs=65536\n")
        self.assertTrue(res.valid)

    def test_10_shell_truncation_redirection_onto_persistent_paths_blocked(self) -> None:
        res = audit_busybox_dd_commands("cat /tmp/new.so > /usr/lib/appFw.so\n")
        self.assertFalse(res.valid)
        self.assertIn(V_BUSYBOX_DD_TRUNC, res.violation_codes)

    def test_11_pmca_5step_write_contract_valid_5slot_manifest(self) -> None:
        h = "a" * 64
        slots = [{"slot_id": f"slot-{i}", "sha256": f"{i}" * 64, "bytes": 1024 + i} for i in range(1, 6)]
        res = audit_pmca_5step_write_contract(
            drop_exit_guard_ok=True,
            tmpfs_staging_ok=True,
            expected_sha256=h,
            readback_sha256=h,
            rollback_history=slots,
            script_text="busybox dd if=/dev/nflasha1 of=/tmp/stage.bin bs=65536\n",
        )
        self.assertTrue(res.valid, res.errors)
        self.assertEqual(res.details["rollback_slots"], 5)
        self.assertFalse(res.details["persistent_emmc_writes_authorized"])

    def test_12_pmca_5step_write_contract_rejects_missing_drop_guard_or_bad_readback(self) -> None:
        slots = [{"slot_id": "slot-1", "sha256": "b" * 64, "bytes": 512}]
        no_drop = audit_pmca_5step_write_contract(
            drop_exit_guard_ok=False,
            tmpfs_staging_ok=True,
            expected_sha256="a" * 64,
            readback_sha256="a" * 64,
            rollback_history=slots,
        )
        self.assertFalse(no_drop.valid)
        self.assertIn(V_PMCA_5STEP, no_drop.violation_codes)

        bad_rb = audit_pmca_5step_write_contract(
            drop_exit_guard_ok=True,
            tmpfs_staging_ok=True,
            expected_sha256="a" * 64,
            readback_sha256="c" * 64,
            rollback_history=slots,
        )
        self.assertFalse(bad_rb.valid)
        self.assertIn(V_PMCA_5STEP, bad_rb.violation_codes)

    def test_13_pmca_5step_write_contract_rejects_bad_rollback_manifest_slots(self) -> None:
        h = "a" * 64
        too_many = [{"slot_id": f"s{i}", "sha256": h, "bytes": 512} for i in range(6)]
        res_6 = audit_pmca_5step_write_contract(
            drop_exit_guard_ok=True,
            tmpfs_staging_ok=True,
            expected_sha256=h,
            readback_sha256=h,
            rollback_history=too_many,
        )
        self.assertFalse(res_6.valid)
        self.assertIn(V_PMCA_5STEP, res_6.violation_codes)

        empty = audit_pmca_5step_write_contract(
            drop_exit_guard_ok=True,
            tmpfs_staging_ok=True,
            expected_sha256=h,
            readback_sha256=h,
            rollback_history=[],
        )
        self.assertFalse(empty.valid)
        self.assertIn(V_PMCA_5STEP, empty.violation_codes)

    def test_14_nflasha10_12mib_vfat_headroom_within_budget_passes(self) -> None:
        res = audit_nflasha10_vfat_budget(
            current_used_bytes=6 * 1024 * 1024,
            planned_writes=[
                {"path": "/setting/updater/mode", "bytes": 0},
                {"path": "/setting/updater/mode6", "bytes": 0},
                {"path": "/tmp/mod_log.txt", "bytes": 16 * 1024},
            ],
        )
        self.assertTrue(res.valid, res.errors)
        self.assertEqual(res.details["partition_bytes"], NFLASHA10_PARTITION_BYTES)
        self.assertGreaterEqual(res.details["projected_free_bytes"], NFLASHA10_DEFAULT_MIN_HEADROOM_BYTES)

    def test_15_nflasha10_12mib_vfat_exhaustion_0x10000009_blocked(self) -> None:
        res = audit_nflasha10_vfat_budget(
            current_used_bytes=10 * 1024 * 1024,
            planned_writes=[{"path": "/tmp/huge_dump.bin", "bytes": 512 * 1024}],
        )
        self.assertFalse(res.valid)
        self.assertIn(V_NFLASHA10_FULL, res.violation_codes)
        self.assertEqual(res.details["error_code"], hex(NFLASHA10_LOCKUP_ERROR_CODE))

    def test_16_nflasha10_cluster_rounding_and_hard_floor_1mib_enforced(self) -> None:
        # 1-byte write rounds up to 4096-byte VFAT cluster, pushing free below 2 MiB reserve
        res_round = audit_nflasha10_vfat_budget(
            current_used_bytes=10 * 1024 * 1024,
            planned_writes=[{"path": "/setting/flag.dat", "bytes": 1}],
        )
        self.assertFalse(res_round.valid)
        self.assertEqual(res_round.details["planned_cluster_bytes"], 4096)

        res_floor = audit_nflasha10_vfat_budget(
            current_used_bytes=1024,
            min_headroom_bytes=512 * 1024,
        )
        self.assertFalse(res_floor.valid)
        self.assertIn(V_NFLASHA10_FULL, res_floor.violation_codes)

    def test_17_camset_bk4_safe_user_settings_allowed(self) -> None:
        res = audit_camset_bk4_diff(
            diff_entries=[
                {"key": "DE_SQUEEZE", "bk_id": "0x02cf1bf2", "old_value": 0, "new_value": 1},
                {"key": "SELECT_LUT", "bk_id": 0x02CF1453, "old_value": 0, "new_value": 2},
                {"key": "SHUTTER_MODE", "bk_id": 0x02CF1702, "old_value": 0, "new_value": 1},
                {"key": "NTSC_PAL_POPUP", "bk_id": 0x02CF0004, "old_value": 1, "new_value": 0},
            ]
        )
        self.assertTrue(res.valid, res.errors)
        self.assertEqual(len(res.details["allowed_keys"]), 4)
        self.assertEqual(res.details["blocked_keys"], [])

    def test_18_camset_bk4_product_model_alcin_uud_enum4_tampering_blocked(self) -> None:
        for bad_entry in (
            {"key": "PRODUCT_MODEL", "old_value": 4, "new_value": 3},
            {"key": "FEATURE_MANAGER_MODEL_ALCIN_UUD", "old_value": "ALCIN_UUD", "new_value": "LAX"},
            {"key": "BKID_PRODUCT_MODEL", "bk_id": 0x02CF0001, "old_value": "0x91030080", "new_value": "0x91030090"},
            {"key": "CALIB_PSD.BIN", "old_value": "a", "new_value": "b"},
        ):
            res = audit_camset_bk4_diff(diff_entries=[bad_entry])
            self.assertFalse(res.valid, f"Expected block for {bad_entry}")
            self.assertIn(V_CAMSET_PRODUCT_MODEL, res.violation_codes)

    def test_19_binary_bk4_diff_allows_safe_user_offset_blocks_protected_model_offset(self) -> None:
        p0 = bytearray(b"\x00" * 128)
        p0[16] = 4  # simulated protected PRODUCT_MODEL enum ALCIN_UUD=4
        p0[64] = 0  # simulated user De-Squeeze flag
        before = _make_valid_bk4(bytes(p0))

        # Safe user setting change at BK4_HEADER_SIZE + 64 with valid checksum
        p1 = bytearray(p0)
        p1[64] = 1
        after_safe = _make_valid_bk4(bytes(p1))
        ok = audit_camset_bk4_diff(
            before_bk4=before,
            after_bk4=after_safe,
            protected_byte_offsets=[BK4_HEADER_SIZE + 16],
            allowed_user_byte_offsets=[BK4_HEADER_SIZE + 64],
        )
        self.assertTrue(ok.valid, ok.errors)

        # Protected PRODUCT_MODEL offset mutation blocked even with valid checksum
        p2 = bytearray(p0)
        p2[16] = 0  # attempting to change ALCIN_UUD(4) -> LS(0)
        after_bad = _make_valid_bk4(bytes(p2))
        bad = audit_camset_bk4_diff(
            before_bk4=before,
            after_bk4=after_bad,
            protected_byte_offsets=[BK4_HEADER_SIZE + 16],
        )
        self.assertFalse(bad.valid)
        self.assertIn(V_CAMSET_PRODUCT_MODEL, bad.violation_codes)

        # Bad checksum rejected
        corrupt = bytearray(after_safe)
        corrupt[-1] ^= 0xFF
        bad_csum = audit_camset_bk4_diff(before_bk4=before, after_bk4=bytes(corrupt))
        self.assertFalse(bad_csum.valid)

    def test_20_unified_runtime_antibrick_evaluator_combines_all_vectors(self) -> None:
        h = "d" * 64
        slots = [{"slot_id": f"s{i}", "sha256": h, "bytes": 4096} for i in range(1, 6)]
        safe_hook = "rm -f /tmp/mod_arm_once\nbusybox sync\nbusybox mount --bind /log/mod/appFw.so /usr/lib/appFw.so\n"
        ok = evaluate_runtime_antibrick_guards(
            script_text=safe_hook,
            jiritsu_set_file_paths=["/tmp/jiritsu/libJit.so"],
            nflasha10_used_bytes=4 * 1024 * 1024,
            nflasha10_planned_writes=[{"path": "/setting/updater/mode", "bytes": 0}],
            camset_diff_entries=[{"key": "DE_SQUEEZE", "bk_id": 0x02CF1BF2, "old_value": 0, "new_value": 1}],
            pmca_5step_manifest={
                "drop_exit_guard_ok": True,
                "tmpfs_staging_ok": True,
                "expected_sha256": h,
                "readback_sha256": h,
                "rollback_history": slots,
            },
        )
        self.assertTrue(ok.valid, ok.errors)
        self.assertEqual(ok.status, "VERIFIED_SAFE")
        self.assertFalse(ok.details["persistent_emmc_writes_authorized"])

        multi_fail = evaluate_runtime_antibrick_guards(
            script_text="dd if=/tmp/a of=/setting/Backup.bin\necho x > /etc/ld.so.preload\n",
            nflasha10_used_bytes=11 * 1024 * 1024,
            nflasha10_planned_writes=[{"path": "/tmp/blob.bin", "bytes": 512 * 1024}],
            camset_diff_entries=[{"key": "PRODUCT_MODEL", "old_value": 4, "new_value": 3}],
        )
        self.assertFalse(multi_fail.valid)
        self.assertEqual(
            set(multi_fail.violation_codes),
            {V_LD_SO_PRELOAD, V_BUSYBOX_DD_TRUNC, V_NFLASHA10_FULL, V_CAMSET_PRODUCT_MODEL},
        )

    def test_21_brick_classifier_13S_0x100D_uart_framing_playbook(self) -> None:
        for d in (
            classify_brick_state(led_symptom="red_13S"),
            classify_brick_state(diagnostic_code=0x100D),
        ):
            self.assertEqual(d.level, "LEVEL_3_MULTIPORT_BOOTROM_UART_FRAMING_ERROR_0x100D")
            self.assertFalse(d.software_usb_or_sd_recoverable)
            self.assertTrue(d.disassembly_free_uart_bootrom_recoverable)
            self.assertFalse(d.hardware_programmer_required)
            joined = " ".join(d.primary_recovery_steps + [d.root_cause_summary])
            self.assertIn("RP2040-Zero", joined)
            self.assertIn("-DOPEN_DRAIN", joined)
            self.assertIn("48,000", joined)

    def test_22_brick_classifier_6L_9S_wf12_sony_00342260_playbook(self) -> None:
        d = classify_brick_state(led_symptom="red_6L+9S")
        self.assertEqual(d.level, "LEVEL_4_WF12_OR_CP_SUBCOMPONENT_6L9S_FAULT")
        self.assertEqual(d.severity, "CRITICAL_HARDWARE")
        self.assertTrue(d.disassembly_free_uart_bootrom_recoverable)
        joined = " ".join(d.primary_recovery_steps + d.fallback_recovery_steps + [d.root_cause_summary])
        self.assertIn("WF-12", joined)
        self.assertIn("00342260", joined)
        self.assertIn("RP2040-Zero", joined)
        self.assertIn("-DOPEN_DRAIN", joined)

        # Backward compatibility: red_6L with spi_nor remains LEVEL_4_SPOF_HARDWARE_BRICK
        d_legacy = classify_brick_state(led_symptom="red_6L", corrupted_regions=["spi_nor"])
        self.assertEqual(d_legacy.level, "LEVEL_4_SPOF_HARDWARE_BRICK")
        self.assertTrue(d_legacy.hardware_programmer_required)

    def test_23_brick_classifier_0x10000009_nflasha10_vfat_exhaustion_playbook(self) -> None:
        for d in (
            classify_brick_state(error_code=0x10000009, usb_vid_pid="054C:0336"),
            classify_brick_state(corrupted_regions=["nflasha10_full"]),
        ):
            self.assertEqual(d.level, "LEVEL_2_NFLASHA10_VFAT_EXHAUSTION_0x10000009")
            self.assertTrue(d.disassembly_free_uart_bootrom_recoverable)
            self.assertFalse(d.hardware_programmer_required)
            joined = " ".join(d.primary_recovery_steps + [d.root_cause_summary])
            self.assertIn("12 MiB", joined)
            self.assertIn("nflasha10", joined)
            self.assertIn("RP2040-Zero", joined)

    def test_24_brick_classifier_ld_so_preload_deadlock_and_backward_compat(self) -> None:
        d_new = classify_brick_state(ld_so_preload_deadlock=True)
        self.assertEqual(d_new.level, "LEVEL_2_LD_SO_PRELOAD_BUSYBOX_DEADLOCK")
        self.assertFalse(d_new.software_usb_or_sd_recoverable)
        self.assertTrue(d_new.disassembly_free_uart_bootrom_recoverable)
        self.assertFalse(d_new.hardware_programmer_required)
        joined = " ".join(d_new.primary_recovery_steps + d_new.critical_warnings + [d_new.root_cause_summary])
        self.assertIn("/bin/busybox", joined)
        self.assertIn("LD_LIBRARY_PATH", joined)
        self.assertIn("RP2040-Zero", joined)
        self.assertIn("-DOPEN_DRAIN", joined)

        # Preserve exact legacy contract when p3_system + p10_preload are passed together
        d_legacy = classify_brick_state(corrupted_regions=["p3_system", "p10_preload"], updater_mode_armed=False)
        self.assertEqual(d_legacy.level, "LEVEL_2_UNARMED_P2_P3_P7_BOOT_HANG")
        self.assertFalse(d_legacy.software_usb_or_sd_recoverable)
        self.assertTrue(d_legacy.disassembly_free_uart_bootrom_recoverable)
        self.assertFalse(d_legacy.hardware_programmer_required)


if __name__ == "__main__":
    unittest.main()
