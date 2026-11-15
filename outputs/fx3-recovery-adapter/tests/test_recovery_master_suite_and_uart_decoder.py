"""Dual-mode unit tests for Phase 86 Passive 1.8V RX-Only UART Boot-Stage Decoder & Unified Master Self-Audit.

Passes in BOTH:
- Local Donor `O_RDONLY` mode (verifies all 7 `fx3_recovery` pillars against real local donor files)
- `FX3_FX6_FORCE_CLEAN_ROOM=1` mode (deterministic clean-room synthetic fixtures)
Designed for `< 0.6s` total execution time with zero binary/bytecode residue.
"""

from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import shutil
import sys
import time
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import fx3_recovery
from fx3_recovery import __main__ as fx3_cli
from fx3_recovery import recovery_master_suite_and_uart_decoder as mod
from fx3_recovery.files import ROOT, is_forced_clean_room
from fx3_recovery.recovery_master_suite_and_uart_decoder import (
    ALLOW_BOOT_PARTITION_TARGETING,
    ALLOW_DESTRUCTIVE_FASTBOOT,
    BOOT_STAGES,
    OUTCOME_BLOCKED_ACTIVE_TX_INJECTION,
    OUTCOME_BLOCKED_LTC_CONFLICT,
    OUTCOME_BLOCKED_UNDERVOLTAGE_TAP,
    OUTCOME_BLOCKED_UNSAFE_TX_LINE,
    OUTCOME_BLOCKED_UNSUPPORTED_BAUD,
    OUTCOME_CLEAN_HASH_FAILOPEN_STOCK_BOOT,
    OUTCOME_CLEAN_SD_SENTINEL_STOCK_ESCAPE,
    OUTCOME_CRITICAL_DO_NOT_DOWNGRADE_BOOTCHAIN,
    OUTCOME_DISCONNECT_CABLE_CHECK_1V8_OPEN_DRAIN,
    OUTCOME_HEALTHY_STAGE_B_LIVE,
    OUTCOME_NEVER_CROSS_FLASH_FX6_WBI2,
    OUTCOME_NO_EMMC_FLASH_NEEDED,
    OUTCOME_TIER0_COLD_REBOOT_WIPES_TMPFS,
    OUTCOME_TIER0_CRASH_BREAKER_RECOVERED,
    OUTCOME_TIER1_SD_SENTINEL_OR_P1_83_ROLLBACK,
    OUTCOME_UNKNOWN_OR_INCOMPLETE_BOOT_LOG,
    PASSIVE_TX_BYTES_EMITTED,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHYSICAL_DEVICE_WRITES,
    PILLAR_IDS,
    READ_ONLY_DONOR_ACCESS,
    RECOVERY_MASTER_SUITE_SCHEMA,
    STAGE_INDEX_MAP,
    STATUS_FAIL_RECOVERY_MASTER_SUITE,
    STATUS_VERIFIED_PASSIVE_RX_TAP,
    STATUS_VERIFIED_RECOVERY_MASTER_SUITE,
    STATUS_VERIFIED_UART_DECODER_SUITE,
    TEN_OUTCOME_CODES,
    UART_BOOTROM_BAUD,
    UART_CONSOLE_BAUD,
    UART_SCENARIO_IDS,
    PassiveTapConfig,
    RecoveryMasterSuiteReport,
    audit_passive_rx_tap_safety,
    build_default_10_uart_scenarios,
    decode_uart_boot_log,
    parse_cxd90057_boot_stages,
    run_recovery_master_suite,
    run_uart_boot_decoder_10_scenario_suite,
)


class RecoveryMasterSuiteAndUartDecoderTests(unittest.TestCase):
    master_report: RecoveryMasterSuiteReport

    @classmethod
    def setUpClass(cls) -> None:
        cls.master_report = run_recovery_master_suite()

    def setUp(self) -> None:
        self._sandbox = (
            ROOT / "outputs" / "fx3-recovery-adapter" / f".tmp-phase86-test-{os.getpid()}-{time.time_ns()}"
        )

    def tearDown(self) -> None:
        shutil.rmtree(self._sandbox, ignore_errors=True)

    def test_01_safety_constants_and_package_exports(self) -> None:
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(PERSISTENT_WRITE_RELEASE)
        self.assertFalse(ALLOW_BOOT_PARTITION_TARGETING)
        self.assertFalse(ALLOW_DESTRUCTIVE_FASTBOOT)
        self.assertTrue(READ_ONLY_DONOR_ACCESS)
        self.assertEqual(PHYSICAL_DEVICE_WRITES, 0)
        self.assertEqual(PASSIVE_TX_BYTES_EMITTED, 0)
        self.assertEqual(len(PILLAR_IDS), 7)
        self.assertEqual(len(TEN_OUTCOME_CODES), 10)
        self.assertEqual(len(UART_SCENARIO_IDS), 10)
        self.assertEqual(fx3_recovery.RECOVERY_MASTER_SUITE_SCHEMA, RECOVERY_MASTER_SUITE_SCHEMA)
        for symbol in (
            "audit_passive_rx_tap_safety",
            "parse_cxd90057_boot_stages",
            "decode_uart_boot_log",
            "build_default_10_uart_scenarios",
            "run_uart_boot_decoder_10_scenario_suite",
            "run_recovery_master_suite",
            "PassiveTapConfig",
            "RecoveryMasterSuiteReport",
        ):
            self.assertIn(symbol, fx3_recovery.__all__)

    def test_02_boot_stages_s0_to_s6_order_and_indices(self) -> None:
        expected = (
            "S0_BOOTROM_ENTRY",
            "S1_NBL_OPTEE_TRUSTZONE",
            "S2_UBOOT_BOOT_AB",
            "S3_LINUX_4_9_337_SCEL",
            "S4_INIT2_SENTINEL_CHECK",
            "S5_STAGE_B_TMPFS_MOUNT",
            "S6_ICX1295_BIG6_READY",
        )
        self.assertEqual(BOOT_STAGES, expected)
        for i, stage in enumerate(expected):
            self.assertEqual(STAGE_INDEX_MAP[stage], i)

    def test_03_passive_rx_tap_allows_rx_only_and_open_drain_1v8_idle(self) -> None:
        for baud in (UART_CONSOLE_BAUD, UART_BOOTROM_BAUD):
            rx_only = audit_passive_rx_tap_safety(
                PassiveTapConfig(tx_line_connected=False, open_drain_tx_idle_1v8=False, io_voltage_v=1.80, baud_rate=baud)
            )
            self.assertTrue(rx_only.safe)
            self.assertEqual(rx_only.status, STATUS_VERIFIED_PASSIVE_RX_TAP)
            self.assertEqual(rx_only.passive_tx_bytes_emitted, 0)
            self.assertFalse(rx_only.bootrom_uart_boot_trigger_risk)

            od_idle = audit_passive_rx_tap_safety(
                PassiveTapConfig(tx_line_connected=True, open_drain_tx_idle_1v8=True, io_voltage_v=1.80, baud_rate=baud)
            )
            self.assertTrue(od_idle.safe)
            self.assertEqual(od_idle.passive_tx_bytes_emitted, 0)

    def test_04_passive_rx_tap_rejects_active_tx_injection_fail_closed(self) -> None:
        res_attempt = audit_passive_rx_tap_safety(
            PassiveTapConfig(tx_line_connected=True, open_drain_tx_idle_1v8=True, tx_bytes_attempted=2)
        )
        self.assertFalse(res_attempt.safe)
        self.assertEqual(res_attempt.status, OUTCOME_BLOCKED_ACTIVE_TX_INJECTION)
        self.assertEqual(res_attempt.passive_tx_bytes_emitted, 0)
        self.assertTrue(res_attempt.bootrom_uart_boot_trigger_risk)

        res_payload = audit_passive_rx_tap_safety(
            PassiveTapConfig(tx_line_connected=False, open_drain_tx_idle_1v8=True),
            active_tx_payload=b"UB\x00\x01",
        )
        self.assertFalse(res_payload.safe)
        self.assertEqual(res_payload.status, OUTCOME_BLOCKED_ACTIVE_TX_INJECTION)
        self.assertEqual(res_payload.passive_tx_bytes_emitted, 0)
        self.assertEqual(res_payload.tx_bytes_attempted, 4)

    def test_05_passive_rx_tap_rejects_unsafe_push_pull_tx_line(self) -> None:
        res = audit_passive_rx_tap_safety(
            PassiveTapConfig(tx_line_connected=True, open_drain_tx_idle_1v8=False, io_voltage_v=1.80)
        )
        self.assertFalse(res.safe)
        self.assertEqual(res.status, OUTCOME_BLOCKED_UNSAFE_TX_LINE)
        self.assertEqual(res.passive_tx_bytes_emitted, 0)
        self.assertTrue(res.bootrom_uart_boot_trigger_risk)

    def test_06_passive_rx_tap_rejects_3v3_overvoltage_and_undervoltage(self) -> None:
        ov = audit_passive_rx_tap_safety(PassiveTapConfig(io_voltage_v=3.30))
        self.assertFalse(ov.safe)
        self.assertEqual(ov.status, OUTCOME_DISCONNECT_CABLE_CHECK_1V8_OPEN_DRAIN)
        self.assertEqual(ov.recommended_action, OUTCOME_DISCONNECT_CABLE_CHECK_1V8_OPEN_DRAIN)

        uv = audit_passive_rx_tap_safety(PassiveTapConfig(io_voltage_v=1.20))
        self.assertFalse(uv.safe)
        self.assertEqual(uv.status, OUTCOME_BLOCKED_UNDERVOLTAGE_TAP)

    def test_07_passive_rx_tap_rejects_ltc_cable_and_unsupported_baud(self) -> None:
        ltc = audit_passive_rx_tap_safety(PassiveTapConfig(ltc_cable_connected=True))
        self.assertFalse(ltc.safe)
        self.assertEqual(ltc.status, OUTCOME_BLOCKED_LTC_CONFLICT)

        bad_baud = audit_passive_rx_tap_safety(PassiveTapConfig(baud_rate=9600))
        self.assertFalse(bad_baud.safe)
        self.assertEqual(bad_baud.status, OUTCOME_BLOCKED_UNSUPPORTED_BAUD)

    def test_08_parse_cxd90057_boot_stages_full_s0_to_s6_transitions(self) -> None:
        s0_to_s6 = build_default_10_uart_scenarios()[0].log_text
        trace = parse_cxd90057_boot_stages(s0_to_s6)
        self.assertEqual(trace.stages_observed, BOOT_STAGES)
        self.assertEqual(trace.highest_stage_reached, "S6_ICX1295_BIG6_READY")
        self.assertEqual(trace.highest_stage_index, 6)
        self.assertTrue(trace.valid_monotonic_progression)
        self.assertEqual(
            trace.stage_transitions,
            (
                "S0_BOOTROM_ENTRY->S1_NBL_OPTEE_TRUSTZONE",
                "S1_NBL_OPTEE_TRUSTZONE->S2_UBOOT_BOOT_AB",
                "S2_UBOOT_BOOT_AB->S3_LINUX_4_9_337_SCEL",
                "S3_LINUX_4_9_337_SCEL->S4_INIT2_SENTINEL_CHECK",
                "S4_INIT2_SENTINEL_CHECK->S5_STAGE_B_TMPFS_MOUNT",
                "S5_STAGE_B_TMPFS_MOUNT->S6_ICX1295_BIG6_READY",
            ),
        )

    def test_09_parse_cxd90057_detects_non_monotonic_regression_without_wdt(self) -> None:
        out_of_order = (
            "S0_BOOTROM_ENTRY: CXD90057 BootROM\n"
            "S4_INIT2_SENTINEL_CHECK: /sbin/init2\n"
            "S1_NBL_OPTEE_TRUSTZONE: OP-TEE unexpected jump\n"
        )
        trace = parse_cxd90057_boot_stages(out_of_order)
        self.assertFalse(trace.wdt_reset_observed)
        self.assertFalse(trace.valid_monotonic_progression)

    def test_10_parse_cxd90057_allows_wdt_reset_cycle_back_to_s0(self) -> None:
        wdt_reboot_log = (
            "S0_BOOTROM_ENTRY: CXD90057 BootROM\n"
            "S1_NBL_OPTEE_TRUSTZONE: OP-TEE\n"
            "S2_UBOOT_BOOT_AB: U-Boot\n"
            "S3_LINUX_4_9_337_SCEL: Linux version 4.9.337-scel+\n"
            "S4_INIT2_SENTINEL_CHECK: /sbin/init2\n"
            "S5_STAGE_B_TMPFS_MOUNT: mount -t tmpfs /tmp/fx6_stage_b\n"
            "CXD90057 WDT reset triggered -> cold reset to stock\n"
            "S0_BOOTROM_ENTRY: CXD90057 BootROM\n"
            "S1_NBL_OPTEE_TRUSTZONE: OP-TEE\n"
            "S2_UBOOT_BOOT_AB: U-Boot\n"
            "S3_LINUX_4_9_337_SCEL: Linux version 4.9.337-scel+\n"
            "S4_INIT2_SENTINEL_CHECK: exec /sbin/init2.stock\n"
        )
        trace = parse_cxd90057_boot_stages(wdt_reboot_log)
        self.assertTrue(trace.wdt_reset_observed)
        self.assertTrue(trace.stock_fallback_observed)
        self.assertTrue(trace.valid_monotonic_progression)

    def test_11_decode_u01_healthy_stage_b_live(self) -> None:
        spec = build_default_10_uart_scenarios()[0]
        res = decode_uart_boot_log(spec.log_text, tap=spec.tap, scenario_id=spec.scenario_id)
        self.assertTrue(res.passed)
        self.assertTrue(res.triage_classified)
        self.assertTrue(res.safe_to_operate)
        self.assertFalse(res.fault_detected)
        self.assertEqual(res.outcome_code, OUTCOME_HEALTHY_STAGE_B_LIVE)
        self.assertEqual(res.highest_stage_reached, "S6_ICX1295_BIG6_READY")
        self.assertEqual(res.recovery_tier, "NONE")
        self.assertEqual(res.passive_tx_bytes_emitted, 0)
        self.assertEqual(res.emmc_write_bytes, 0)
        self.assertFalse(res.persistent_emmc_writes_authorized)

    def test_12_decode_u02_sd_sentinel_stock_escape(self) -> None:
        spec = build_default_10_uart_scenarios()[1]
        res = decode_uart_boot_log(spec.log_text, tap=spec.tap, scenario_id=spec.scenario_id)
        self.assertTrue(res.passed)
        self.assertEqual(res.outcome_code, OUTCOME_CLEAN_SD_SENTINEL_STOCK_ESCAPE)
        self.assertEqual(res.highest_stage_reached, "S4_INIT2_SENTINEL_CHECK")
        self.assertEqual(res.recovery_tier, "TIER_0")

        alt = decode_uart_boot_log("S4_INIT2_SENTINEL_CHECK: found DISABLE_STAGE_B.TXT -> stock FX3")
        self.assertEqual(alt.outcome_code, OUTCOME_CLEAN_SD_SENTINEL_STOCK_ESCAPE)

    def test_13_decode_u03_cpio_sha256_mismatch_failopen(self) -> None:
        spec = build_default_10_uart_scenarios()[2]
        res = decode_uart_boot_log(spec.log_text, tap=spec.tap, scenario_id=spec.scenario_id)
        self.assertTrue(res.passed)
        self.assertEqual(res.outcome_code, OUTCOME_CLEAN_HASH_FAILOPEN_STOCK_BOOT)
        self.assertEqual(res.highest_stage_reached, "S4_INIT2_SENTINEL_CHECK")
        self.assertEqual(res.recovery_tier, "TIER_0")

    def test_14_decode_u04_icx1295_wf12_00342260_assert(self) -> None:
        spec = build_default_10_uart_scenarios()[3]
        res = decode_uart_boot_log(spec.log_text, tap=spec.tap, scenario_id=spec.scenario_id)
        self.assertTrue(res.passed)
        self.assertTrue(res.fault_detected)
        self.assertEqual(res.outcome_code, OUTCOME_NO_EMMC_FLASH_NEEDED)
        self.assertIn("P12", res.recovery_action)
        self.assertIn("COLD_REBOOT", res.recovery_action)
        self.assertEqual(res.recovery_tier, "TIER_0")

    def test_15_decode_u05_procam_3x_15s_crash_breaker(self) -> None:
        spec = build_default_10_uart_scenarios()[4]
        res = decode_uart_boot_log(spec.log_text, tap=spec.tap, scenario_id=spec.scenario_id)
        self.assertTrue(res.passed)
        self.assertEqual(res.outcome_code, OUTCOME_TIER0_CRASH_BREAKER_RECOVERED)
        self.assertEqual(res.recovery_tier, "TIER_0")
        self.assertEqual(res.passive_tx_bytes_emitted, 0)

    def test_16_decode_u06_kernel_paging_oops_wdt_wipes_tmpfs(self) -> None:
        spec = build_default_10_uart_scenarios()[5]
        res = decode_uart_boot_log(spec.log_text, tap=spec.tap, scenario_id=spec.scenario_id)
        self.assertTrue(res.passed)
        self.assertEqual(res.outcome_code, OUTCOME_TIER0_COLD_REBOOT_WIPES_TMPFS)
        self.assertEqual(res.recovery_tier, "TIER_0")

    def test_17_decode_u07_wbi2_hibernate_mismatch(self) -> None:
        spec = build_default_10_uart_scenarios()[6]
        res = decode_uart_boot_log(spec.log_text, tap=spec.tap, scenario_id=spec.scenario_id)
        self.assertTrue(res.passed)
        self.assertEqual(res.outcome_code, OUTCOME_NEVER_CROSS_FLASH_FX6_WBI2)
        self.assertEqual(res.recovery_tier, "TIER_0")
        self.assertTrue(any("cold boot" in step.lower() for step in res.prescribed_steps))

    def test_18_decode_u08_p1_init2_sh_syntax_or_hang(self) -> None:
        spec = build_default_10_uart_scenarios()[7]
        res = decode_uart_boot_log(spec.log_text, tap=spec.tap, scenario_id=spec.scenario_id)
        self.assertTrue(res.passed)
        self.assertEqual(res.outcome_code, OUTCOME_TIER1_SD_SENTINEL_OR_P1_83_ROLLBACK)
        self.assertEqual(res.recovery_tier, "TIER_1")
        self.assertIn("FX3_SAFE_STOCK_FLG", res.recovery_action)
        self.assertIn("83_POINTER_ROLLBACK", res.recovery_action)

    def test_19_decode_u09_otp_rpmb_antirollback_rejection(self) -> None:
        spec = build_default_10_uart_scenarios()[8]
        res = decode_uart_boot_log(spec.log_text, tap=spec.tap, scenario_id=spec.scenario_id)
        self.assertTrue(res.passed)
        self.assertTrue(res.critical_hazard)
        self.assertEqual(res.outcome_code, OUTCOME_CRITICAL_DO_NOT_DOWNGRADE_BOOTCHAIN)
        self.assertEqual(res.highest_stage_reached, "S1_NBL_OPTEE_TRUSTZONE")
        self.assertEqual(res.recovery_tier, "TIER_4")

    def test_20_decode_u10_3v3_overvoltage_and_raw_bytes_framing_noise_burst(self) -> None:
        spec = build_default_10_uart_scenarios()[9]
        res = decode_uart_boot_log(spec.log_text, tap=spec.tap, scenario_id=spec.scenario_id)
        self.assertTrue(res.triage_classified)
        self.assertFalse(res.safe_to_operate)
        self.assertTrue(res.critical_hazard)
        self.assertEqual(res.outcome_code, OUTCOME_DISCONNECT_CABLE_CHECK_1V8_OPEN_DRAIN)

        raw_garbage = b"\xff\xfe\x80\x81\x9f\x00\x01\xff" * 16
        raw_res = decode_uart_boot_log(raw_garbage, scenario_id="RAW_FRAMING_BURST")
        self.assertTrue(raw_res.triage_classified)
        self.assertFalse(raw_res.safe_to_operate)
        self.assertTrue(raw_res.critical_hazard)
        self.assertGreaterEqual(raw_res.framing_noise_ratio, 0.25)
        self.assertEqual(raw_res.outcome_code, OUTCOME_DISCONNECT_CABLE_CHECK_1V8_OPEN_DRAIN)

    def test_21_decode_rejects_active_tx_injection_even_on_valid_log(self) -> None:
        valid_log = build_default_10_uart_scenarios()[0].log_text
        res = decode_uart_boot_log(
            valid_log,
            tap=PassiveTapConfig(tx_line_connected=True, open_drain_tx_idle_1v8=True, tx_bytes_attempted=1),
            active_tx_payload=b"UB",
        )
        self.assertFalse(res.passed)
        self.assertFalse(res.safe_to_operate)
        self.assertEqual(res.outcome_code, OUTCOME_BLOCKED_ACTIVE_TX_INJECTION)
        self.assertEqual(res.passive_tx_bytes_emitted, 0)

    def test_22_decode_unknown_or_incomplete_log_fails_closed(self) -> None:
        for log in ("", "S0_BOOTROM_ENTRY: CXD90057 BootROM\nS1_NBL_OPTEE_TRUSTZONE: OP-TEE\n"):
            res = decode_uart_boot_log(log)
            self.assertFalse(res.passed)
            self.assertFalse(res.triage_classified)
            self.assertEqual(res.outcome_code, OUTCOME_UNKNOWN_OR_INCOMPLETE_BOOT_LOG)
            self.assertEqual(res.emmc_write_bytes, 0)

    def test_23_decode_rejects_invalid_input_types(self) -> None:
        with self.assertRaises(TypeError):
            decode_uart_boot_log(12345)  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            audit_passive_rx_tap_safety(active_tx_payload="not-bytes")  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            audit_passive_rx_tap_safety(PassiveTapConfig(tx_bytes_attempted=-1))

    def test_24_uart_10_scenario_suite_passes_all_10_and_probes(self) -> None:
        suite = run_uart_boot_decoder_10_scenario_suite()
        self.assertTrue(suite.passed)
        self.assertEqual(suite.status, STATUS_VERIFIED_UART_DECODER_SUITE)
        self.assertEqual(suite.scenarios_total, 10)
        self.assertEqual(suite.scenarios_passed, 10)
        self.assertTrue(suite.active_tx_rejection_verified)
        self.assertTrue(suite.unsafe_tx_line_rejection_verified)
        self.assertTrue(suite.overvoltage_3v3_tap_rejection_verified)
        self.assertEqual(suite.passive_tx_bytes_emitted, 0)
        self.assertEqual(suite.physical_device_writes, 0)
        self.assertFalse(suite.persistent_emmc_writes_authorized)
        self.assertFalse(suite.persistent_write_release)

    def test_25_master_suite_executes_all_7_pillars_under_1s(self) -> None:
        rep = self.master_report
        self.assertTrue(rep.all_passed)
        self.assertEqual(rep.status, STATUS_VERIFIED_RECOVERY_MASTER_SUITE)
        self.assertEqual(rep.pillar_count, 7)
        self.assertEqual(rep.pillars_passed, 7)
        self.assertEqual(rep.failed_pillars, ())
        self.assertEqual(rep.errors, ())
        self.assertLess(rep.elapsed_seconds, 1.0)
        self.assertEqual(tuple(p.pillar_id for p in rep.pillars), PILLAR_IDS)
        self.assertEqual(len(rep.recovery_master_sha256), 64)

    def test_26_master_suite_pillar_1_macos_usb_and_pillar_2_rp2040_invariants(self) -> None:
        p1 = self.master_report.pillars[0]
        self.assertEqual(p1.pillar_id, "macos_usb_transport_guard")
        self.assertTrue(p1.passed)
        self.assertEqual(p1.summary_metrics["claim_backend"], "IOUSBHost")
        self.assertTrue(p1.summary_metrics["senser_v2_fail_closed"])
        self.assertFalse(p1.summary_metrics["allow_persistent_jiritsu_writes"])

        p2 = self.master_report.pillars[1]
        self.assertEqual(p2.pillar_id, "rp2040_multiport_fixture_selftest")
        self.assertTrue(p2.passed)
        self.assertFalse(p2.summary_metrics["camera_connected"])
        self.assertTrue(p2.summary_metrics["loopback_48000_exact"])
        self.assertTrue(p2.summary_metrics["loopback_115200_exact"])

    def test_27_master_suite_pillar_3_init2_and_pillar_4_tier0_backup_invariants(self) -> None:
        p3 = self.master_report.pillars[2]
        self.assertEqual(p3.pillar_id, "init2_escape_and_watchdog_simulator")
        self.assertTrue(p3.passed)
        self.assertEqual(p3.summary_metrics["escape_drills_passed"], 7)
        self.assertEqual(p3.summary_metrics["escape_drills_total"], 7)
        self.assertEqual(p3.summary_metrics["wdt_scenarios_passed"], 5)
        self.assertEqual(p3.summary_metrics["wdt_scenarios_total"], 5)
        self.assertEqual(p3.summary_metrics["physical_writes"], 0)

        p4 = self.master_report.pillars[3]
        self.assertEqual(p4.pillar_id, "tier0_backup_parity_and_manifest_guard")
        self.assertTrue(p4.passed)
        self.assertEqual(p4.summary_metrics["partition_count"], 11)
        self.assertTrue(p4.summary_metrics["heal_1_bitrot_exact"])
        self.assertTrue(p4.summary_metrics["cross_body_blocked"])

    def test_28_master_suite_pillar_5_antirollback_and_pillar_6_unbrick_ladder_invariants(self) -> None:
        p5 = self.master_report.pillars[4]
        self.assertEqual(p5.pillar_id, "firmware_updata_and_antirollback_guard")
        self.assertTrue(p5.passed)
        self.assertEqual(p5.summary_metrics["otp_fuse_touches"], 0)
        self.assertEqual(p5.summary_metrics["rpmb_counter_increments"], 0)
        self.assertTrue(p5.summary_metrics["ext_csd_perm_wp_blocked"])

        p6 = self.master_report.pillars[5]
        self.assertEqual(p6.pillar_id, "unbrick_ladder_and_capsule_verifier")
        self.assertTrue(p6.passed)
        self.assertEqual(p6.summary_metrics["scenarios_passed"], 12)
        self.assertEqual(p6.summary_metrics["scenario_count"], 12)
        self.assertEqual(p6.summary_metrics["wbi_mutation_bytes"], 0)
        self.assertEqual(p6.summary_metrics["emmc_write_bytes"], 0)

    def test_29_master_suite_pillar_7_uart_and_hard_locked_safety_flags(self) -> None:
        rep = self.master_report
        p7 = rep.pillars[6]
        self.assertEqual(p7.pillar_id, "passive_uart_boot_stage_decoder")
        self.assertTrue(p7.passed)
        self.assertEqual(p7.summary_metrics["scenarios_passed"], 10)
        self.assertEqual(p7.summary_metrics["scenarios_total"], 10)
        self.assertEqual(p7.summary_metrics["passive_tx_bytes_emitted"], 0)
        self.assertEqual(rep.passive_tx_bytes_emitted, 0)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.persistent_write_release)
        self.assertFalse(rep.allow_boot_partition_targeting)
        self.assertFalse(rep.allow_destructive_fastboot)
        self.assertFalse(rep.allow_persistent_jiritsu_writes)
        self.assertFalse(rep.allow_destructive_jiritsu_commands)
        self.assertEqual(rep.physical_device_writes, 0)

    def test_30_master_suite_fault_injection_fail_closed(self) -> None:
        with self.assertRaises(ValueError):
            run_recovery_master_suite(fault_inject_pillar="nonexistent_pillar")

        with (
            mock.patch.object(mod, "_run_pillar_3_init2_escape", return_value=self.master_report.pillars[2]),
            mock.patch.object(mod, "_run_pillar_4_tier0_backup", return_value=self.master_report.pillars[3]),
            mock.patch.object(mod, "_run_pillar_6_unbrick_ladder", return_value=self.master_report.pillars[5]),
        ):
            failed = run_recovery_master_suite(
                force_clean_room=True,
                fault_inject_pillar="rp2040_multiport_fixture_selftest",
            )
        self.assertFalse(failed.all_passed)
        self.assertEqual(failed.status, STATUS_FAIL_RECOVERY_MASTER_SUITE)
        self.assertEqual(failed.pillars_passed, 6)
        self.assertEqual(failed.failed_pillars, ("rp2040_multiport_fixture_selftest",))
        self.assertFalse(failed.persistent_emmc_writes_authorized)
        self.assertFalse(failed.persistent_write_release)
        self.assertNotEqual(failed.recovery_master_sha256, self.master_report.recovery_master_sha256)

    def test_31_master_suite_mocked_safety_violation_fails_closed(self) -> None:
        bad_p2 = mock.MagicMock(
            all_passed=True,
            status="VERIFIED_BENCH_FIXTURE",
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            board="waveshare_rp2040_zero",
            camera_connected=True,
            donor_p1_sha256="0" * 64,
            pio_dividers=(),
            loopback_48000=mock.MagicMock(bit_exact_match=True),
            loopback_115200=mock.MagicMock(bit_exact_match=True),
            glitch_rejection_verified=True,
            framing_error_rejection_verified=True,
            persistent_emmc_writes_authorized=False,
            errors=(),
        )
        with (
            mock.patch.object(mod, "run_rp2040_multiport_fixture_selftest", return_value=bad_p2),
            mock.patch.object(mod, "_run_pillar_3_init2_escape", return_value=self.master_report.pillars[2]),
            mock.patch.object(mod, "_run_pillar_4_tier0_backup", return_value=self.master_report.pillars[3]),
            mock.patch.object(mod, "_run_pillar_6_unbrick_ladder", return_value=self.master_report.pillars[5]),
        ):
            failed = run_recovery_master_suite(force_clean_room=True)
        self.assertFalse(failed.all_passed)
        self.assertIn("rp2040_multiport_fixture_selftest", failed.failed_pillars)

    def test_32_master_suite_determinism_and_dual_mode_parity(self) -> None:
        rep = self.master_report
        expected_mode = "CLEAN_ROOM_SYNTHETIC" if is_forced_clean_room() else rep.verification_mode
        self.assertIn(expected_mode, ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"))

        # Re-run real pillars 1, 2, 5, 7 + master hash aggregation while reusing deterministic 3, 4, 6 summaries
        with (
            mock.patch.object(mod, "_run_pillar_3_init2_escape", return_value=rep.pillars[2]),
            mock.patch.object(mod, "_run_pillar_4_tier0_backup", return_value=rep.pillars[3]),
            mock.patch.object(mod, "_run_pillar_6_unbrick_ladder", return_value=rep.pillars[5]),
        ):
            rerun_same_mode = run_recovery_master_suite()
        self.assertTrue(rerun_same_mode.all_passed)
        self.assertEqual(rerun_same_mode.verification_mode, rep.verification_mode)
        self.assertEqual(rerun_same_mode.recovery_master_sha256, rep.recovery_master_sha256)
        self.assertEqual(rerun_same_mode.uart_decoder_suite.scenarios_passed, 10)
        self.assertEqual(rerun_same_mode.passive_tx_bytes_emitted, 0)

        # Verify Clean-Room mode produces CLEAN_ROOM_SYNTHETIC with all 7 pillars passing
        with (
            mock.patch.object(mod, "_run_pillar_3_init2_escape", return_value=mod.PillarAuditSummary(**{**rep.pillars[2].__dict__, "verification_mode": "CLEAN_ROOM_SYNTHETIC"})),
            mock.patch.object(mod, "_run_pillar_4_tier0_backup", return_value=mod.PillarAuditSummary(**{**rep.pillars[3].__dict__, "verification_mode": "CLEAN_ROOM_SYNTHETIC"})),
            mock.patch.object(mod, "_run_pillar_6_unbrick_ladder", return_value=mod.PillarAuditSummary(**{**rep.pillars[5].__dict__, "verification_mode": "CLEAN_ROOM_SYNTHETIC"})),
        ):
            clean_rep = run_recovery_master_suite(force_clean_room=True)
        self.assertTrue(clean_rep.all_passed)
        self.assertEqual(clean_rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(clean_rep.pillar_count, rep.pillar_count)
        self.assertEqual(clean_rep.pillars_passed, rep.pillars_passed)
        self.assertEqual(clean_rep.uart_decoder_suite.scenarios_passed, rep.uart_decoder_suite.scenarios_passed)
        self.assertEqual(clean_rep.passive_tx_bytes_emitted, 0)

    def test_33_cli_verify_all_recovery_json_text_out_and_fail_exit_code(self) -> None:
        out_dir = self._sandbox / "cli_master_out"
        self._sandbox.mkdir(parents=True, exist_ok=True)

        with mock.patch("fx3_recovery.__main__.run_recovery_master_suite", return_value=self.master_report):
            buf_json = io.StringIO()
            with mock.patch.object(sys, "argv", ["fx3_recovery", "verify-all-recovery", "--clean-room", "--json", "--out", str(out_dir)]), redirect_stdout(buf_json):
                rc = fx3_cli.main()
            self.assertEqual(rc, 0)
            rendered = buf_json.getvalue()
            self.assertNotRegex(rendered, r'(?<![0-9A-Za-z_/.-])b[\'"]')
            parsed = json.loads(rendered)
            self.assertEqual(parsed["schema"], RECOVERY_MASTER_SUITE_SCHEMA)
            self.assertEqual(parsed["pillars_passed"], 7)
            self.assertTrue((out_dir / "recovery-master-report.json").is_file())

            buf_text = io.StringIO()
            with mock.patch.object(sys, "argv", ["fx3_recovery", "verify-all-recovery"]), redirect_stdout(buf_text):
                rc_txt = fx3_cli.main()
            self.assertEqual(rc_txt, 0)
            self.assertIn("status=VERIFIED_RECOVERY_MASTER_SUITE", buf_text.getvalue())
            self.assertIn("pillars=7/7", buf_text.getvalue())

        failing_rep = RecoveryMasterSuiteReport(
            **{
                **self.master_report.__dict__,
                "all_passed": False,
                "status": STATUS_FAIL_RECOVERY_MASTER_SUITE,
                "pillars_passed": 6,
                "failed_pillars": ("rp2040_multiport_fixture_selftest",),
            }
        )
        with mock.patch("fx3_recovery.__main__.run_recovery_master_suite", return_value=failing_rep):
            buf_fail = io.StringIO()
            with mock.patch.object(sys, "argv", ["fx3_recovery", "verify-all-recovery", "--json"]), redirect_stdout(buf_fail):
                rc_fail = fx3_cli.main()
            self.assertEqual(rc_fail, 2)

    def test_34_json_serialization_no_raw_bytes_repr_and_no_nan(self) -> None:
        rendered = json.dumps(self.master_report.to_dict(), ensure_ascii=False, sort_keys=True, allow_nan=False)
        self.assertNotRegex(rendered, r'(?<![0-9A-Za-z_/.-])b[\'"]')
        decoded = json.loads(rendered)
        self.assertEqual(decoded["recovery_master_sha256"], self.master_report.recovery_master_sha256)
        self.assertFalse(decoded["persistent_emmc_writes_authorized"])
        self.assertFalse(decoded["persistent_write_release"])
        self.assertEqual(decoded["passive_tx_bytes_emitted"], 0)


if __name__ == "__main__":
    unittest.main()
