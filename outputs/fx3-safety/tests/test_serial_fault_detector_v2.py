"""Clean-room unit tests for Phase 32 Serial & Kernel Telemetry Fault Detector v2."""

from __future__ import annotations

import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent.parent
REPO_ROOT = HERE.parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import fx3_safety
from fx3_safety.serial_fault_detector_v2 import (
    DISPOSITION_ALLOWED_DEGRADED,
    DISPOSITION_FAIL_CLOSED_ABORT,
    DISPOSITION_PASS,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    SERIAL_FAULT_DETECTOR_V2_SCHEMA,
    STAGE_A_SOFT_GUARD_BUDGET_SEC,
    TIMER_IP_HW_WDT_CEILING_SEC,
    StreamingSerialFaultDetectorV2,
    audit_round10_summary_telemetry,
    audit_serial_boot_telemetry,
    main as cli_main,
    verify_watchdog_budget,
)


class SerialFaultDetectorV2Tests(unittest.TestCase):
    def test_01_safety_redlines_and_package_exports(self) -> None:
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(PERSISTENT_WRITE_RELEASE)
        self.assertEqual(STAGE_A_SOFT_GUARD_BUDGET_SEC, 90.0)
        self.assertEqual(TIMER_IP_HW_WDT_CEILING_SEC, 220.0)
        for name in (
            "StreamingSerialFaultDetectorV2",
            "audit_serial_boot_telemetry",
            "audit_round10_summary_telemetry",
            "verify_watchdog_budget",
            "DISPOSITION_PASS",
            "DISPOSITION_ALLOWED_DEGRADED",
            "DISPOSITION_FAIL_CLOSED_ABORT",
        ):
            self.assertIn(name, fx3_safety.__all__)
            self.assertTrue(hasattr(fx3_safety, name))

    def test_02_clean_boot_passes_with_wdt_and_clear_before_exec(self) -> None:
        log = (
            "[    0.000000] Linux version 4.9.337-scel+ (gcc version 6.4.0)\n"
            "[   10.250000] rm -f /tmp/mod_arm_once && busybox sync\n"
            "[   11.500000] TIMER-IP: WDT_SET_STOP\n"
            "[   12.000000] FX6_STAGE_A_VERIFY_RC=0\n"
            "[   14.800000] FX6_PATCH_PLAN appFw_base=0x7f91ee8000 nop_count=0 round=10\n"
            "[   45.000000] FX6_MILESTONE_PRESENTER_READY\n"
        )
        rep = audit_serial_boot_telemetry(
            serial_text=log,
            require_wdt_budget_proof=True,
            require_complete_line_termination=True,
        )
        self.assertTrue(rep.passed, rep.errors)
        self.assertEqual(rep.disposition, DISPOSITION_PASS)
        self.assertFalse(rep.abort_required)
        self.assertEqual(rep.fatal_fault_count, 0)
        self.assertEqual(rep.degraded_event_count, 0)
        self.assertTrue(rep.watchdog_budget.passed)
        self.assertAlmostEqual(rep.watchdog_budget.wdt_stop_sec or 0.0, 11.5)
        self.assertAlmostEqual(rep.watchdog_budget.clear_before_exec_sec or 0.0, 10.25)

    def test_03_category1_kernel_panics_oops_and_unhandled_faults(self) -> None:
        samples = (
            ("[   12.100000] Unable to handle kernel paging request at virtual address 00000008\n", "KERNEL_UNABLE_TO_HANDLE"),
            ("[   14.200000] Internal error: Oops: 96000005 [#1] PREEMPT SMP\n", "KERNEL_INTERNAL_ERROR_OOPS"),
            ("[   18.300000] Kernel panic - not syncing: Attempted to kill init!\n", "KERNEL_PANIC"),
            ("[   19.400000] SError Interrupt on CPU0, code 0xbf000002\n", "KERNEL_SERROR_INTERRUPT"),
            ("[   20.500000] BUG: kernel NULL pointer dereference at 00000010\n", "KERNEL_BUG_MARKER"),
        )
        for line, expected_code in samples:
            rep = audit_serial_boot_telemetry(serial_text=line)
            self.assertFalse(rep.passed)
            self.assertEqual(rep.disposition, DISPOSITION_FAIL_CLOSED_ABORT)
            self.assertTrue(rep.abort_required)
            codes = {f.code for f in rep.findings}
            self.assertIn(expected_code, codes)
            self.assertTrue(any(pb.brick_level.startswith("LEVEL_2_") for pb in rep.brick_recovery_playbooks))

    def test_04_category1_sony_zztgkill_zzstack_zzexcstack_signals_and_assert(self) -> None:
        log = (
            "[   22.100000] ZZTGKILL: pid=412 comm=appFw sig=6\n"
            "[   22.105000] ZZSTACK: lr=0x7f92001000 sp=0x7fe0001200\n"
            "[   22.110000] ZZEXCSTACK: elr=0x7f92001040 esr=0x92000047\n"
            "[   22.120000] Unhandled signal 11 (SIGSEGV) in im.elf\n"
            "assert at PresenterBase.cpp:418\n"
        )
        rep = audit_serial_boot_telemetry(serial_text=log)
        self.assertFalse(rep.passed)
        self.assertEqual(rep.disposition, DISPOSITION_FAIL_CLOSED_ABORT)
        codes = {f.code for f in rep.findings}
        self.assertEqual(
            codes,
            {
                "SONY_ZZTGKILL",
                "SONY_ZZSTACK",
                "SONY_ZZEXCSTACK",
                "USERLAND_SIGSEGV_SIGABRT",
                "SERIAL_ASSERT_FAILURE",
            },
        )
        levels = {pb.brick_level for pb in rep.brick_recovery_playbooks}
        self.assertIn("LEVEL_1_USERLAND_APPFW_SOFT_BRICK", levels)

    def test_05_category2_linker_missso_missdev_imopen_modload(self) -> None:
        log = (
            "[    4.100000] MISSSO: /usr/lib/libInfraMissing.so ENOENT\n"
            "[    4.200000] MISSDEV: /dev/ldec open failed (-2)\n"
            "[    4.300000] IMOPEN: /etc/missing_cfg.bin rc=-2\n"
            "[    4.400000] MODLOAD: /usr/kmod/upm.ko err=-8 (ENOEXEC)\n"
            "im.elf: error while loading shared libraries: libfoo.so: cannot open shared object file\n"
        )
        rep = audit_serial_boot_telemetry(serial_text=log)
        self.assertFalse(rep.passed)
        codes = {f.code for f in rep.findings}
        self.assertEqual(
            codes,
            {
                "SONY_MISSSO",
                "SONY_MISSDEV",
                "SONY_IMOPEN_FAULT",
                "SONY_MODLOAD_FAULT",
                "SHARED_LIB_LOAD_ERROR",
            },
        )

    def test_06_category2_ld_so_preload_dynamic_busybox_deadlock_crosslinks_brick_classifier(self) -> None:
        log = (
            "[    2.400000] ERROR: ld.so: object '/tmp/bad.so' from /etc/ld.so.preload cannot be preloaded\n"
            "[    2.405000] busybox: error while loading shared libraries: /tmp/bad.so\n"
        )
        rep = audit_serial_boot_telemetry(serial_text=log)
        self.assertFalse(rep.passed)
        self.assertEqual(rep.disposition, DISPOSITION_FAIL_CLOSED_ABORT)
        codes = {f.code for f in rep.findings}
        self.assertIn("LD_SO_PRELOAD_BUSYBOX_DEADLOCK", codes)
        levels = {pb.brick_level for pb in rep.brick_recovery_playbooks}
        self.assertIn("LEVEL_2_LD_SO_PRELOAD_BUSYBOX_DEADLOCK", levels)

    def test_07_category2_benign_imopen_modload_ok_not_false_positived(self) -> None:
        log = (
            "[    3.100000] IMOPEN path=/usr/share/app/image_00_169.uxc status=OK\n"
            "[    3.200000] MODLOAD module=/usr/kmod/upm.ko rc=0 module_loaded=1\n"
        )
        rep = audit_serial_boot_telemetry(serial_text=log)
        self.assertTrue(rep.passed, rep.errors)
        self.assertEqual(rep.disposition, DISPOSITION_PASS)

    def test_08_category3_zzfutex_zzcomplete_and_hung_task_blocked(self) -> None:
        log = (
            "[   65.000000] ZZFUTEX: pid=501 comm=AppMain addr=0x7f880010\n"
            "[   66.000000] ZZCOMPLETE: task=SeqQueueNetwork wait_for_completion\n"
            "[  125.000000] INFO: task im.elf:412 blocked for more than 120 seconds.\n"
        )
        rep = audit_serial_boot_telemetry(serial_text=log)
        self.assertFalse(rep.passed)
        codes = {f.code for f in rep.findings}
        self.assertIn("SONY_ZZFUTEX_HANG", codes)
        self.assertIn("SONY_ZZCOMPLETE_HANG", codes)
        self.assertIn("KERNEL_HUNG_TASK_BLOCKED", codes)

    def test_09_category3_wlan_resource_0x70d4_hang_vs_patched_ok(self) -> None:
        hang_log = "[   18.000000] WlanResourceMainThread stuck in handleFatalError 0x70d4 usleep(1000000)\n"
        rep_hang = audit_serial_boot_telemetry(serial_text=hang_log)
        self.assertFalse(rep_hang.passed)
        self.assertIn("WLAN_RESOURCE_0x70D4_HANG", {f.code for f in rep_hang.findings})
        self.assertIn(
            "LEVEL_4_WF12_OR_CP_SUBCOMPONENT_6L9S_FAULT",
            {pb.brick_level for pb in rep_hang.brick_recovery_playbooks},
        )

        ok_log = "[   18.000000] P12_wlan_resource_handleFatalError_nonblocking site=0x70d4 status=OK\n"
        rep_ok = audit_serial_boot_telemetry(serial_text=ok_log)
        self.assertTrue(rep_ok.passed, rep_ok.errors)

    def test_10_category3_uipc_unshimmed_timeout_vs_shimmed_p11_ack(self) -> None:
        bad_uipc = (
            "[   25.000000] UIPC unshimmed timeout waiting for queue 0x92d2091c\n"
            "[   26.000000] osal_wai_sem ETIMEDOUT dest=0x91db059b\n"
        )
        rep_bad = audit_serial_boot_telemetry(serial_text=bad_uipc)
        self.assertFalse(rep_bad.passed)
        self.assertEqual(sum(1 for f in rep_bad.findings if f.code == "UIPC_UNSHIMMED_TIMEOUT"), 2)

        good_uipc = (
            "[   25.000000] FX6_P11_HANDLE_ACK count=1 dest=0x91db059b cb_qid=0x8000610e "
            "req_cmd=0x81000001 evt_cmd=0x88000002 free_rc=0 snd_rc=0 xlr_h1_preserved=1\n"
        )
        rep_good = audit_serial_boot_telemetry(serial_text=good_uipc)
        self.assertTrue(rep_good.passed, rep_good.errors)
        self.assertEqual(rep_good.disposition, DISPOSITION_ALLOWED_DEGRADED)
        self.assertEqual(rep_good.degraded_events[0].code, "P11_DETACHED_GRIP_ACK_0x91DB059B")

    def test_11_category4_watchdog_budget_passes_strictly_before_90s_and_220s(self) -> None:
        wdt = verify_watchdog_budget(
            wdt_stop_sec=41.2,
            clear_before_exec_sec=9.5,
            overlay_exec_sec=10.1,
            max_observed_sec=185.0,
            require_wdt_stop_proof=True,
            require_clear_before_exec_proof=True,
        )
        self.assertTrue(wdt.passed, wdt.errors)
        self.assertEqual(wdt.status, "VERIFIED_WITHIN_BUDGET")

    def test_12_category4_blocks_90s_soft_guard_and_220s_timer_ip_ceiling(self) -> None:
        late_soft = (
            "[   10.000000] rm -f /tmp/mod_arm_once && busybox sync\n"
            "[   90.000000] WDT_SET_STOP\n"
        )
        rep_soft = audit_serial_boot_telemetry(serial_text=late_soft, require_wdt_budget_proof=True)
        self.assertFalse(rep_soft.passed)
        self.assertIn("STAGE_A_90S_SOFT_GUARD_EXCEEDED", {f.code for f in rep_soft.findings})

        late_hw = (
            "[   10.000000] rm -f /tmp/mod_arm_once && busybox sync\n"
            "[  220.500000] TIMER-IP: WDT_SET_STOP\n"
        )
        rep_hw = audit_serial_boot_telemetry(serial_text=late_hw, require_wdt_budget_proof=True)
        self.assertFalse(rep_hw.passed)
        codes_hw = {f.code for f in rep_hw.findings}
        self.assertIn("TIMER_IP_220S_CEILING_EXCEEDED", codes_hw)
        self.assertIn("STAGE_A_90S_SOFT_GUARD_EXCEEDED", codes_hw)

    def test_13_category4_blocks_missing_clear_before_exec_and_commented_bypass_and_order(self) -> None:
        commented_only = (
            "[   10.000000] # rm -f /tmp/mod_arm_once\n"
            "[   11.000000] TIMER-IP: WDT_SET_STOP\n"
            "[   95.000000] FX6_MILESTONE_ALIVE\n"
        )
        rep_commented = audit_serial_boot_telemetry(serial_text=commented_only)
        self.assertFalse(rep_commented.passed)
        self.assertIn("STAGE_A_90S_MISSING_CLEAR_BEFORE_EXEC", {f.code for f in rep_commented.findings})

        wrong_order = (
            "[   11.000000] TIMER-IP: WDT_SET_STOP\n"
            "[   12.000000] busybox mount --bind /tmp/appFw.so /usr/lib/appFw.so\n"
            "[   13.000000] rm -f /tmp/mod_arm_once && busybox sync\n"
        )
        rep_order = audit_serial_boot_telemetry(serial_text=wrong_order, require_wdt_budget_proof=True)
        self.assertFalse(rep_order.passed)
        self.assertIn("CLEAR_BEFORE_EXEC_ORDER_VIOLATION", {f.code for f in rep_order.findings})

    def test_14_category4_blocks_220s_without_wdt_stop_and_timer_ip_bark(self) -> None:
        no_stop_220 = (
            "[   10.000000] rm -f /tmp/mod_arm_once && busybox sync\n"
            "[  221.000000] FX6_MILESTONE_STILL_RUNNING\n"
        )
        rep_220 = audit_serial_boot_telemetry(serial_text=no_stop_220)
        self.assertFalse(rep_220.passed)
        codes = {f.code for f in rep_220.findings}
        self.assertIn("TIMER_IP_220S_MISSING_WDT_SET_STOP", codes)
        self.assertIn("STAGE_A_90S_MISSING_WDT_SET_STOP", codes)

        bark_log = "[   40.000000] TIMER-IP timeout: hardware watchdog reset triggered\n"
        rep_bark = audit_serial_boot_telemetry(serial_text=bark_log)
        self.assertFalse(rep_bark.passed)
        self.assertIn("TIMER_IP_WDT_FAULT_TRIGGERED", {f.code for f in rep_bark.findings})

    def test_15_category5_degraded_safe_events_return_allowed_degraded(self) -> None:
        log = (
            "[   10.000000] rm -f /tmp/mod_arm_once && busybox sync\n"
            "[   11.000000] TIMER-IP: WDT_SET_STOP\n"
            "[   15.000000] WF12_DEGRADED_RADIO_OFF Notice 00342260: The Wi-Fi/Bluetooth unit has malfunctioned.\n"
            "[   16.000000] BT_DEGRADED_DISABLED wrapper_bt_interface_enable rc=0xbb9\n"
            "[   17.000000] FX6_P11_HANDLE_ACK count=1 dest=0x91db059b cb_qid=0x8000610e req_cmd=0x81000001 evt_cmd=0x88000002 free_rc=0 snd_rc=0 xlr_h1_preserved=1\n"
            "[   18.000000] FX6_STAGE_B_R10_RTC0 path=/dev/rtc0 open_ok=0 errno=2\n"
            "[   19.000000] P4_ND_CLEAR: P4_appfw_set_nd_filter_mode_clear\n"
        )
        rep = audit_serial_boot_telemetry(serial_text=log, require_wdt_budget_proof=True)
        self.assertTrue(rep.passed, rep.errors)
        self.assertEqual(rep.disposition, DISPOSITION_ALLOWED_DEGRADED)
        self.assertFalse(rep.abort_required)
        self.assertEqual(rep.fatal_fault_count, 0)
        deg_codes = {d.code for d in rep.degraded_events}
        self.assertEqual(
            deg_codes,
            {
                "WF12_DEGRADED_RADIO_OFF",
                "BT_DEGRADED_DISABLED_0xBB9",
                "P11_DETACHED_GRIP_ACK_0x91DB059B",
                "P11_RTC0_DEGRADED_PROBE",
                "P4_ND_CLEAR",
            },
        )

    def test_16_category5_fatal_system_error_overrides_degraded_and_links_6l9s(self) -> None:
        log = (
            "[   15.000000] BT_DEGRADED_DISABLED err=0xbb9\n"
            '[   18.000000] MODEL_WIFI_FATAL_ERROR_OCCURRED: "System Error" Wi-Fi unit reboot loop\n'
        )
        rep = audit_serial_boot_telemetry(serial_text=log)
        self.assertFalse(rep.passed)
        self.assertEqual(rep.disposition, DISPOSITION_FAIL_CLOSED_ABORT)
        self.assertTrue(rep.abort_required)
        self.assertEqual(rep.degraded_event_count, 1)
        self.assertIn("SYSTEM_ERROR_ABORT", {f.code for f in rep.findings})
        self.assertIn(
            "LEVEL_4_WF12_OR_CP_SUBCOMPONENT_6L9S_FAULT",
            {pb.brick_level for pb in rep.brick_recovery_playbooks},
        )

    def test_17_category5_0x10000009_vfat_full_aborts_and_links_brick_classifier(self) -> None:
        log = "[   20.000000] setting write failed err=0x10000009 on nflasha10\n"
        rep = audit_serial_boot_telemetry(serial_text=log)
        self.assertFalse(rep.passed)
        self.assertEqual(rep.disposition, DISPOSITION_FAIL_CLOSED_ABORT)
        self.assertIn("NFLASHA10_VFAT_FULL_0x10000009", {f.code for f in rep.findings})
        self.assertIn(
            "LEVEL_2_NFLASHA10_VFAT_EXHAUSTION_0x10000009",
            {pb.brick_level for pb in rep.brick_recovery_playbooks},
        )

    def test_18_category5_verify_before_mount_sha_mismatch_aborts(self) -> None:
        log = (
            "FX6_STAGE_A_VERIFY_ITEM path=/usr/lib/appFw.so bytes=50520424 "
            "expected=e2bc2619845e9614 actual=deadbeefcafebabe status=FAIL\n"
            "FX6_STAGE_A_VERIFY_RC=1\n"
        )
        rep = audit_serial_boot_telemetry(serial_text=log)
        self.assertFalse(rep.passed)
        codes = {f.code for f in rep.findings}
        self.assertIn("VERIFY_BEFORE_MOUNT_SHA_MISMATCH", codes)
        self.assertIn("VERIFY_BEFORE_MOUNT_RC_NONZERO", codes)
        self.assertIn(
            "LEVEL_0_TRANSIENT_OR_ONESHOT_OVERLAY",
            {pb.brick_level for pb in rep.brick_recovery_playbooks},
        )

    def test_19_category5_native_faithful_nop_count_nonzero_aborts(self) -> None:
        log = "FX6_STAGE_B_BRIDGE round=10 faithful=1 nop_count=3 p10_keymap=1\n"
        rep_faithful = audit_serial_boot_telemetry(serial_text=log, native_faithful_mode=True)
        self.assertFalse(rep_faithful.passed)
        self.assertIn("NATIVE_FAITHFUL_NOP_COUNT_NONZERO", {f.code for f in rep_faithful.findings})

        # Also verify structured telemetry nop_count > 0 fails closed
        bad_run = {
            "run_id": "r10-bad-nop",
            "kernel_version": "Linux version 4.9.337-scel+",
            "wall_elapsed_sec": 55.0,
            "nop_count": 1,
            "crashes": 0,
            "faithful_invariants": {"FX6_NATIVE_FAITHFUL": 1, "subst_color": 0},
        }
        rep_tel = audit_serial_boot_telemetry(telemetry_summary=bad_run)
        self.assertFalse(rep_tel.passed)
        self.assertIn("NATIVE_FAITHFUL_NOP_COUNT_NONZERO", {f.code for f in rep_tel.findings})

    def test_20_streaming_chunk_boundaries_and_immediate_abort(self) -> None:
        det = StreamingSerialFaultDetectorV2(source_label="uart0")
        c1 = b"[    1.000000] Linux version 4.9.337-scel+\n[   10.000000] P4_ND_"
        c2 = b"CLEAR\n[   12.000000] Kernel panic"
        c3 = b" - not syncing: Fatal exception\n"

        f1 = det.feed_chunk(c1)
        self.assertEqual(f1, [])
        self.assertFalse(det.should_abort_now())

        f2 = det.feed_chunk(c2)
        self.assertEqual([f.code for f in f2], ["P4_ND_CLEAR"])
        self.assertFalse(det.should_abort_now())

        f3 = det.feed_chunk(c3)
        self.assertEqual([f.code for f in f3], ["KERNEL_PANIC"])
        self.assertTrue(det.should_abort_now())

        rep = det.finalize()
        self.assertFalse(rep.passed)
        self.assertEqual(rep.disposition, DISPOSITION_FAIL_CLOSED_ABORT)
        self.assertEqual(rep.lines_scanned, 3)
        self.assertEqual(rep.degraded_event_count, 1)
        self.assertEqual(rep.fatal_fault_count, 1)

    def test_21_empty_truncated_and_o_rdonly_serial_path_fail_closed(self) -> None:
        rep_empty = audit_serial_boot_telemetry(serial_text="")
        self.assertFalse(rep_empty.passed)
        self.assertIn("EMPTY_TELEMETRY_INPUT", {f.code for f in rep_empty.findings})

        rep_trunc = audit_serial_boot_telemetry(
            serial_text="[    1.000000] Linux version 4.9.337-scel+",
            require_complete_line_termination=True,
        )
        self.assertFalse(rep_trunc.passed)
        self.assertIn("INCOMPLETE_TRUNCATED_CAPTURE", {f.code for f in rep_trunc.findings})

        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "boot.serial"
            p.write_text("[    1.000000] FX6_STAGE_A_VERIFY_RC=0\n", encoding="utf-8")
            rep_file = audit_serial_boot_telemetry(serial_path=p)
            self.assertTrue(rep_file.passed, rep_file.errors)

            missing = Path(tmp) / "does_not_exist.serial"
            rep_missing = audit_serial_boot_telemetry(serial_path=missing)
            self.assertFalse(rep_missing.passed)
            self.assertIn("SERIAL_PATH_UNREADABLE", {f.code for f in rep_missing.findings})

    def test_22_round10_committed_summary_json_and_clean_room_fallback(self) -> None:
        summary_file = REPO_ROOT / "reports/2026-11-14-round10-fx6-on-fx3-full-icon-presenter/summary.json"
        if summary_file.is_file():
            rep_real = audit_round10_summary_telemetry(repo_root=REPO_ROOT, force_clean_room=False)
            self.assertTrue(rep_real.all_passed, rep_real.errors)
            self.assertEqual(rep_real.telemetry_source, "committed_round10_summary_json")
            self.assertEqual(rep_real.overall_disposition, DISPOSITION_ALLOWED_DEGRADED)
            self.assertEqual(rep_real.runs_audited, 4)
            for run_key, r in rep_real.run_reports.items():
                self.assertTrue(r["passed"], run_key)
                self.assertEqual(r["fatal_fault_count"], 0, run_key)
                self.assertGreaterEqual(r["degraded_event_count"], 1, run_key)

        with patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            rep_clean = audit_round10_summary_telemetry(repo_root=REPO_ROOT)
            self.assertTrue(rep_clean.all_passed, rep_clean.errors)
            self.assertEqual(rep_clean.telemetry_source, "clean_room_synthetic")
            self.assertEqual(rep_clean.overall_disposition, DISPOSITION_ALLOWED_DEGRADED)
            self.assertEqual(rep_clean.runs_audited, 4)

    def test_23_round10_mutation_detects_icon_blitter_and_unshimmed_rtc_regression(self) -> None:
        bad_run = {
            "run_id": "r10-mutated",
            "kernel_version": "Linux version 4.9.337-scel+",
            "wall_elapsed_sec": 62.0,
            "nop_count": 0,
            "crashes": 0,
            "faithful_invariants": {"FX6_NATIVE_FAITHFUL": 1, "subst_color": 0, "subst_image": 0},
            "r10_telemetry": {
                "icon_blitter": {"subst_color": 0, "subst_image": 2},
                "p11_uipc": {"rtc_0x92d2091c": 3, "handle_0x91db059b": 1},
            },
        }
        rep = audit_serial_boot_telemetry(telemetry_summary=bad_run)
        self.assertFalse(rep.passed)
        codes = {f.code for f in rep.findings}
        self.assertIn("NATIVE_FAITHFUL_INVARIANT_BREACH", codes)
        self.assertIn("UIPC_UNSHIMMED_TIMEOUT", codes)

    def test_24_cli_json_serializable_and_exit_codes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ok_log = Path(tmp) / "ok.serial"
            ok_log.write_text(
                "[    8.000000] rm -f /tmp/mod_arm_once && busybox sync\n"
                "[   12.000000] TIMER-IP: WDT_SET_STOP\n"
                "[   15.000000] WF12_DEGRADED_RADIO_OFF\n",
                encoding="utf-8",
            )
            buf_ok = io.StringIO()
            with contextlib.redirect_stdout(buf_ok):
                rc_ok = cli_main(["--serial", str(ok_log), "--require-wdt-proof"])
            self.assertEqual(rc_ok, 0)
            payload_ok = json.loads(buf_ok.getvalue())
            self.assertEqual(payload_ok["schema"], SERIAL_FAULT_DETECTOR_V2_SCHEMA)
            self.assertEqual(payload_ok["disposition"], DISPOSITION_ALLOWED_DEGRADED)
            self.assertFalse(payload_ok["persistent_write_release"])

            bad_log = Path(tmp) / "bad.serial"
            bad_log.write_text("[   15.000000] ZZFUTEX: deadlocked\n", encoding="utf-8")
            buf_bad = io.StringIO()
            with contextlib.redirect_stdout(buf_bad):
                rc_bad = cli_main(["--serial", str(bad_log)])
            self.assertEqual(rc_bad, 1)
            payload_bad = json.loads(buf_bad.getvalue())
            self.assertEqual(payload_bad["disposition"], DISPOSITION_FAIL_CLOSED_ABORT)


if __name__ == "__main__":
    unittest.main()
