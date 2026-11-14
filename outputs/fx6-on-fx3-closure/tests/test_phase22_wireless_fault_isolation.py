"""Unit & Unicorn AArch64 fault-injection tests for Phase 22 (P12) Wireless Fault Isolation Verifier."""

from __future__ import annotations

import contextlib
import io
import json
import os
import sys
import time
import unittest
from pathlib import Path
from typing import Dict

sys.dont_write_bytecode = True

from fx6_closure.wireless_fault_isolation_verifier import (  # noqa: E402
    APPFW_SYSINIT_QUEUE_ID,
    APPLICATION_SYSTEM_INIT_BUDGET_MS,
    BT_BSA_HAL_INIT_ERR_CODE,
    CP_MUTATION_BYTES,
    KMOD_MUTATION_COUNT,
    NVRAM_PERSISTENT_WRITES,
    P8_CP_MUTATION_FORBIDDEN,
    P12_WLAN_FATAL_GUARD_SPEC,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHASE_22_SCHEMA,
    PHASE_22_VERSION,
    REQUIRED_FX3_APPFW_WIRELESS_MARKERS,
    REQUIRED_FX6_APPFW_WIRELESS_MARKERS,
    REQUIRED_FX6_BT_MARKERS,
    REQUIRED_FX6_WLAN_RSRC_MARKERS,
    SONY_NOTICE_00342260_ID,
    SONY_NOTICE_00342260_UPDATED,
    WBI_MUTATION_BYTES,
    Phase22WirelessFaultIsolationReport,
    WirelessFaultIsolationStateMachine,
    audit_donor_wireless_surfaces,
    build_clean_room_phase22_fixtures,
    main,
    resolve_phase22_donor_paths,
    run_phase22_wireless_fault_isolation_verification,
    verify_airplane_ram_shadow_bk4_and_scenario_5,
    verify_p3_remote_board_synergy,
    verify_p12_wlan_fatal_guard,
)


def _donors_available() -> bool:
    if os.environ.get("FX3_FX6_FORCE_CLEAN_ROOM") == "1":
        return False
    paths = resolve_phase22_donor_paths()
    return paths is not None and all(p.is_file() for p in paths.values())


class TestPhase22WirelessFaultIsolation(unittest.TestCase):
    """Comprehensive dual-mode tests for Phase 22 WF-12/BT/SeqQueueNetwork/00342260 verifier."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.t_start = time.monotonic()
        cls.active_report: Phase22WirelessFaultIsolationReport = (
            run_phase22_wireless_fault_isolation_verification()
        )
        cls.active_elapsed_s = time.monotonic() - cls.t_start
        cls.clean_report: Phase22WirelessFaultIsolationReport = (
            run_phase22_wireless_fault_isolation_verification(synthetic_mode=True)
        )
        cls.fixtures: Dict[str, bytes] = build_clean_room_phase22_fixtures()

    def test_01_active_mode_passes_all_gates(self) -> None:
        self.assertTrue(self.active_report.passed, msg=f"errors={self.active_report.errors}")
        self.assertEqual(self.active_report.errors, ())
        self.assertEqual(self.active_report.schema, PHASE_22_SCHEMA)
        self.assertEqual(self.active_report.phase_version, PHASE_22_VERSION)
        self.assertEqual(self.active_report.sony_notice_id, SONY_NOTICE_00342260_ID)
        self.assertEqual(self.active_report.sony_notice_updated, SONY_NOTICE_00342260_UPDATED)
        self.assertEqual(self.active_report.application_system_init_budget_ms, APPLICATION_SYSTEM_INIT_BUDGET_MS)

    def test_02_active_mode_matches_environment_expectation(self) -> None:
        if _donors_available():
            self.assertEqual(self.active_report.verification_mode, "LOCAL_DONOR_VERIFIED")
        else:
            self.assertEqual(self.active_report.verification_mode, "CLEAN_ROOM_SYNTHETIC_VERIFIED")

    def test_03_clean_room_env_var_forces_synthetic_mode(self) -> None:
        prev = os.environ.get("FX3_FX6_FORCE_CLEAN_ROOM")
        os.environ["FX3_FX6_FORCE_CLEAN_ROOM"] = "1"
        try:
            forced = run_phase22_wireless_fault_isolation_verification()
            self.assertTrue(forced.passed, msg=f"errors={forced.errors}")
            self.assertEqual(forced.verification_mode, "CLEAN_ROOM_SYNTHETIC_VERIFIED")
            self.assertEqual(forced.report_sha256, self.clean_report.report_sha256)
        finally:
            if prev is None:
                os.environ.pop("FX3_FX6_FORCE_CLEAN_ROOM", None)
            else:
                os.environ["FX3_FX6_FORCE_CLEAN_ROOM"] = prev

    def test_04_strict_redlines_zero_mutations_locked(self) -> None:
        for rep in (self.active_report, self.clean_report):
            self.assertEqual(rep.donor_access_mode, "O_RDONLY")
            self.assertFalse(rep.persistent_emmc_writes_authorized)
            self.assertFalse(rep.persistent_write_release)
            self.assertTrue(rep.p8_cp_mutation_forbidden)
            self.assertEqual(rep.wbi_mutation_bytes, WBI_MUTATION_BYTES)
            self.assertEqual(rep.cp_mutation_bytes, CP_MUTATION_BYTES)
            self.assertEqual(rep.kmod_mutation_count, KMOD_MUTATION_COUNT)
            self.assertEqual(rep.nvram_persistent_writes, NVRAM_PERSISTENT_WRITES)
            self.assertEqual(rep.wbi_mutation_bytes, 0)
            self.assertEqual(rep.cp_mutation_bytes, 0)
            self.assertEqual(rep.kmod_mutation_count, 0)
            self.assertEqual(rep.nvram_persistent_writes, 0)

    def test_05_read_only_os_open_enforced_when_reading_donors(self) -> None:
        orig_open = os.open
        opened_flags: list[int] = []

        def _spy_open(path: object, flags: int, *args: object, **kwargs: object) -> int:
            opened_flags.append(flags)
            self.assertEqual(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC), 0)
            return orig_open(path, flags, *args, **kwargs)  # type: ignore[arg-type]

        if _donors_available():
            os.open = _spy_open  # type: ignore[assignment]
            try:
                rep = run_phase22_wireless_fault_isolation_verification(synthetic_mode=False)
                self.assertTrue(rep.passed)
                self.assertGreaterEqual(len(opened_flags), 12)
            finally:
                os.open = orig_open  # type: ignore[assignment]
        else:
            self.assertEqual(self.clean_report.donor_access_mode, "O_RDONLY")

    def test_06_deterministic_json_and_sha256_repeatability(self) -> None:
        second_clean = run_phase22_wireless_fault_isolation_verification(synthetic_mode=True)
        self.assertEqual(self.clean_report.report_sha256, second_clean.report_sha256)
        self.assertEqual(self.clean_report.to_deterministic_json(), second_clean.to_deterministic_json())
        parsed = json.loads(self.clean_report.to_deterministic_json())
        self.assertEqual(parsed["report_sha256"], self.clean_report.report_sha256)

        second_active = run_phase22_wireless_fault_isolation_verification()
        self.assertEqual(self.active_report.report_sha256, second_active.report_sha256)
        self.assertEqual(self.active_report.to_deterministic_json(), second_active.to_deterministic_json())

    def test_07_clean_room_synthetic_fixtures_integrity(self) -> None:
        expected_keys = {
            "fx6_appfw",
            "fx6_remoteboard",
            "fx6_wlan_rsrc",
            "fx6_wlan_ctrl",
            "fx6_bt",
            "fx6_bt_core",
            "fx6_rsrc_bt",
            "fx6_bt_vendor",
            "fx6_net_init",
            "fx6_start_bt_sh",
            "fx6_bk4",
            "fx3_appfw",
            "fx3_insmod1",
            "fx3_insmod2",
            "fx3_bk4",
        }
        self.assertEqual(set(self.fixtures.keys()), expected_keys)
        for key, blob in self.fixtures.items():
            if key.startswith("fx6_") and key not in ("fx6_start_bt_sh", "fx6_bk4"):
                self.assertEqual(blob[:4], b"\x7fELF", msg=f"{key} missing ELF header")
            elif key == "fx3_appfw":
                self.assertEqual(blob[:4], b"\x7fELF")

    def test_08_donor_surface_audit_markers_and_no_early_wireless_kmod(self) -> None:
        for rep in (self.active_report, self.clean_report):
            audit = rep.donor_surface_audit
            self.assertTrue(audit.all_markers_satisfied)
            self.assertEqual(len(audit.fx6_appfw_markers_present), len(REQUIRED_FX6_APPFW_WIRELESS_MARKERS))
            self.assertEqual(len(audit.fx3_appfw_markers_present), len(REQUIRED_FX3_APPFW_WIRELESS_MARKERS))
            self.assertEqual(len(audit.fx6_wlan_rsrc_markers_present), len(REQUIRED_FX6_WLAN_RSRC_MARKERS))
            self.assertEqual(len(audit.fx6_bt_markers_present), len(REQUIRED_FX6_BT_MARKERS))
            self.assertEqual(audit.fx3_insmod_early_wireless_kmods, ())
            self.assertFalse(audit.fx6_libinfrapericon_present)

    def test_09_donor_surface_audit_detects_early_wireless_kmod_or_missing_marker(self) -> None:
        bad_insmod = dict(self.fixtures)
        bad_insmod["fx3_insmod2"] = bad_insmod["fx3_insmod2"] + b"\ninsmod /usr/kmod/wlan.ko\n"
        audit_bad_kmod = audit_donor_wireless_surfaces(bad_insmod, fx6_libinfrapericon_present=False)
        self.assertEqual(audit_bad_kmod.fx3_insmod_early_wireless_kmods, ("wlan.ko",))
        self.assertFalse(audit_bad_kmod.all_markers_satisfied)

        bad_marker = dict(self.fixtures)
        bad_marker["fx6_appfw"] = bad_marker["fx6_appfw"].replace(
            b"WIFI_DEVICE_ERROR_TYPE_HARDWARE_ERROR", b"WIFI_DEVICE_ERROR_TYPE_REDACTED______"
        )
        audit_bad_str = audit_donor_wireless_surfaces(bad_marker, fx6_libinfrapericon_present=False)
        self.assertFalse(audit_bad_str.all_markers_satisfied)

    def test_10_p3_remote_board_synergy_and_rollback(self) -> None:
        for rep in (self.active_report, self.clean_report):
            p3 = rep.p3_remote_board_synergy
            self.assertEqual(p3.patch_group, "P3")
            self.assertEqual(p3.changed_bytes, 16)
            self.assertTrue(p3.rollback_sha256_matched)
            self.assertTrue(p3.unpatched_hang_proven)
            self.assertEqual(p3.patched_rc, 0)
            self.assertTrue(p3.sp_preserved)
            self.assertNotEqual(p3.before_sha256, p3.after_sha256)

    def test_11_p12_wlan_resource_fatal_guard_and_rollback(self) -> None:
        expected_delta = sum(
            1 for a, b in zip(P12_WLAN_FATAL_GUARD_SPEC.sites[0].original_bytes, P12_WLAN_FATAL_GUARD_SPEC.sites[0].patched_bytes) if a != b
        )
        self.assertEqual(expected_delta, 7)
        for rep in (self.active_report, self.clean_report):
            p12 = rep.p12_wlan_fatal_guard
            self.assertEqual(p12.patch_group, "P12")
            self.assertEqual(p12.changed_bytes, 7)
            self.assertTrue(p12.rollback_sha256_matched)
            self.assertTrue(p12.unpatched_hang_proven)
            self.assertEqual(p12.patched_rc, 0)
            self.assertTrue(p12.sp_preserved)
            self.assertNotEqual(p12.before_sha256, p12.after_sha256)

    def test_12_scenario_1_wf12_sdio_probe_timeout_nonblocking(self) -> None:
        for rep in (self.active_report, self.clean_report):
            s1 = next(s for s in rep.fault_scenarios if s.scenario_id == "WF12_SDIO_PROBE_TIMEOUT")
            self.assertTrue(s1.passed)
            self.assertTrue(s1.unicorn_executed)
            self.assertEqual(s1.observed_return_code, -1)
            self.assertFalse(s1.hang_or_loop_detected)
            self.assertFalse(s1.system_error_abort)
            self.assertEqual(s1.wdt_resets, 0)
            self.assertEqual(s1.degraded_state, "WF12_DEGRADED_RADIO_OFF")
            self.assertTrue(s1.sp_preserved)

    def test_13_scenario_2_bt_bsa_uart_no_response_fallback(self) -> None:
        for rep in (self.active_report, self.clean_report):
            s2 = next(s for s in rep.fault_scenarios if s.scenario_id == "BT_BSA_UART_NO_RESPONSE")
            self.assertTrue(s2.passed)
            self.assertTrue(s2.unicorn_executed)
            self.assertEqual(s2.observed_return_code, BT_BSA_HAL_INIT_ERR_CODE)
            self.assertFalse(s2.hang_or_loop_detected)
            self.assertFalse(s2.system_error_abort)
            self.assertEqual(s2.wdt_resets, 0)
            self.assertEqual(s2.degraded_state, "BT_DEGRADED_DISABLED")
            self.assertTrue(s2.sp_preserved)

    def test_14_scenario_3_notice_00342260_malfunction_dismissible(self) -> None:
        for rep in (self.active_report, self.clean_report):
            s3 = next(s for s in rep.fault_scenarios if s.scenario_id == "NOTICE_00342260_MALFUNCTION_CODE")
            self.assertTrue(s3.passed)
            self.assertTrue(s3.unicorn_executed)
            self.assertEqual(s3.observed_return_code, 1)
            self.assertFalse(s3.system_error_abort)
            self.assertEqual(s3.wdt_resets, 0)
            self.assertTrue(s3.shooting_unaffected)
            self.assertTrue(s3.recording_unaffected)
            self.assertEqual(s3.degraded_state, "NOTICE_00342260_AIRPLANE_LATCHED")
            self.assertTrue(s3.sp_preserved)
            self.assertIn("dismissible_evt_0xbc0=True", s3.details)

    def test_15_scenario_4_seq_queue_network_drain_under_50ms_budget(self) -> None:
        for rep in (self.active_report, self.clean_report):
            s4 = next(s for s in rep.fault_scenarios if s.scenario_id == "SEQ_QUEUE_NETWORK_DRAIN_NONBLOCKING")
            self.assertTrue(s4.passed)
            self.assertTrue(s4.unicorn_executed)
            self.assertEqual(s4.observed_return_code, 0)
            self.assertLess(s4.simulated_elapsed_ms, APPLICATION_SYSTEM_INIT_BUDGET_MS)
            self.assertFalse(s4.hang_or_loop_detected)
            self.assertFalse(s4.system_error_abort)
            self.assertEqual(s4.degraded_state, "SEQ_QUEUE_NETWORK_NONBLOCKING_DRAINED")
            self.assertIn(f"0x{APPFW_SYSINIT_QUEUE_ID:08x}", s4.details)
            self.assertTrue(s4.sp_preserved)

    def test_16_scenario_5_airplane_ram_shadow_bk4_zero_nvram_writes(self) -> None:
        for rep in (self.active_report, self.clean_report):
            bk4 = rep.airplane_ram_shadow_bk4
            self.assertTrue(bk4.valid_bk4_header)
            self.assertTrue(bk4.checksum_ok)
            self.assertTrue(bk4.airplane_mode_shadow_default)
            self.assertEqual(bk4.bkid_0x019e0012_shadow_hex, "00")
            self.assertEqual(bk4.bkid_0x0051000f_shadow_hex, "00")
            self.assertEqual(bk4.bkid_0x01a20002_shadow_hex, "00")
            self.assertEqual(bk4.nvram_persistent_writes, 0)
            self.assertEqual(bk4.wbi_mutation_bytes, 0)
            self.assertEqual(bk4.cp_mutation_bytes, 0)
            self.assertEqual(bk4.kmod_mutation_count, 0)
            self.assertTrue(bk4.unicorn_bt_init_bypassed)
            self.assertTrue(bk4.unicorn_rsrc_bt_bypassed)
            self.assertTrue(bk4.unicorn_stock_unshadowed_probed_hw)

            s5 = next(s for s in rep.fault_scenarios if s.scenario_id == "AIRPLANE_MODE_RAM_SHADOW_DEFAULT")
            self.assertTrue(s5.passed)
            self.assertEqual(s5.nvram_writes, 0)
            self.assertEqual(s5.degraded_state, "AIRPLANE_MODE_RAM_SHADOW_SAFE")
            self.assertTrue(s5.sp_preserved)

    def test_17_negative_corrupt_wireless_guard_fails_report_and_all_scenarios(self) -> None:
        bad_syn = run_phase22_wireless_fault_isolation_verification(
            synthetic_mode=True, corrupt_wireless_guard=True
        )
        self.assertFalse(bad_syn.passed)
        self.assertTrue(bad_syn.corrupt_wireless_guard_injected)
        self.assertGreaterEqual(len(bad_syn.errors), 7)
        self.assertEqual(bad_syn.p3_remote_board_synergy.changed_bytes, 0)
        self.assertEqual(bad_syn.p3_remote_board_synergy.patched_rc, 0xDEAD)
        self.assertEqual(bad_syn.p12_wlan_fatal_guard.changed_bytes, 0)
        self.assertEqual(bad_syn.p12_wlan_fatal_guard.patched_rc, 0xDEAD)
        for sc in bad_syn.fault_scenarios:
            self.assertFalse(sc.passed, msg=f"{sc.scenario_id} should fail under corrupt guard")

        if _donors_available():
            bad_local = run_phase22_wireless_fault_isolation_verification(
                synthetic_mode=False, corrupt_wireless_guard=True
            )
            self.assertFalse(bad_local.passed)
            self.assertGreaterEqual(len(bad_local.errors), 7)

    def test_18_standalone_guard_and_bk4_corruption_helpers(self) -> None:
        p3_bad = verify_p3_remote_board_synergy(
            self.fixtures["fx6_remoteboard"], synthetic_mode=True, corrupt_guard=True
        )
        self.assertEqual(p3_bad.patched_rc, 0xDEAD)
        self.assertEqual(p3_bad.changed_bytes, 0)

        p12_bad = verify_p12_wlan_fatal_guard(
            self.fixtures["fx6_wlan_rsrc"], synthetic_mode=True, corrupt_guard=True
        )
        self.assertEqual(p12_bad.patched_rc, 0xDEAD)
        self.assertEqual(p12_bad.changed_bytes, 0)

        bk4_bad, s5_bad = verify_airplane_ram_shadow_bk4_and_scenario_5(
            self.fixtures["fx3_bk4"],
            self.fixtures["fx6_bt"],
            self.fixtures["fx6_rsrc_bt"],
            corrupt_guard=True,
        )
        self.assertFalse(bk4_bad.airplane_mode_shadow_default)
        self.assertFalse(bk4_bad.unicorn_bt_init_bypassed)
        self.assertFalse(bk4_bad.unicorn_rsrc_bt_bypassed)
        self.assertFalse(s5_bad.passed)
        self.assertEqual(s5_bad.degraded_state, "UNSHADOWED_COLD_PROBE_HAZARD")

    def test_19_state_machine_guarded_vs_unguarded_transitions(self) -> None:
        safe = WirelessFaultIsolationStateMachine(nonblocking_guard_enabled=True, airplane_ram_shadow=True)
        self.assertEqual(safe.radio_state, "AIRPLANE_OFF")
        self.assertEqual(safe.handle_wf12_sdio_probe_timeout(-1, False), "WF12_DEGRADED_RADIO_OFF")
        self.assertEqual(safe.handle_bt_bsa_uart_no_response(BT_BSA_HAL_INIT_ERR_CODE), "BT_DEGRADED_DISABLED")
        self.assertEqual(safe.handle_notice_00342260_malfunction(True, True), "NOTICE_00342260_AIRPLANE_LATCHED")
        self.assertEqual(safe.handle_seq_queue_network_drain(12.5), "SEQ_QUEUE_NETWORK_NONBLOCKING_DRAINED")
        self.assertEqual(safe.wdt_resets, 0)
        self.assertFalse(safe.system_error_abort)
        self.assertTrue(safe.shooting_enabled)
        self.assertTrue(safe.recording_enabled)

        unsafe = WirelessFaultIsolationStateMachine(nonblocking_guard_enabled=False, airplane_ram_shadow=False)
        self.assertEqual(unsafe.radio_state, "RADIO_COLD_PROBE")
        self.assertEqual(unsafe.handle_wf12_sdio_probe_timeout(-1, True), "BOOTLOOP_WDT_RESET")
        self.assertEqual(unsafe.handle_notice_00342260_malfunction(True, False), "SYSTEM_ERROR_BOOTLOOP_5_10S")
        self.assertEqual(unsafe.handle_seq_queue_network_drain(80.0), "SEQ_QUEUE_NETWORK_BLOCKED")
        self.assertTrue(unsafe.system_error_abort)
        self.assertGreaterEqual(unsafe.wdt_resets, 3)
        self.assertFalse(unsafe.shooting_enabled)

    def test_20_scenario_parity_between_active_and_clean_room(self) -> None:
        active_ids = [s.scenario_id for s in self.active_report.fault_scenarios]
        clean_ids = [s.scenario_id for s in self.clean_report.fault_scenarios]
        self.assertEqual(active_ids, clean_ids)
        self.assertEqual(
            active_ids,
            [
                "WF12_SDIO_PROBE_TIMEOUT",
                "BT_BSA_UART_NO_RESPONSE",
                "NOTICE_00342260_MALFUNCTION_CODE",
                "SEQ_QUEUE_NETWORK_DRAIN_NONBLOCKING",
                "AIRPLANE_MODE_RAM_SHADOW_DEFAULT",
            ],
        )
        for s_a, s_c in zip(self.active_report.fault_scenarios, self.clean_report.fault_scenarios):
            self.assertEqual(s_a.degraded_state, s_c.degraded_state)
            self.assertEqual(s_a.observed_return_code, s_c.observed_return_code)

    def test_21_cli_main_json_and_summary_modes(self) -> None:
        out_json = io.StringIO()
        with contextlib.redirect_stdout(out_json):
            rc_json = main(["--clean-room", "--json"])
        self.assertEqual(rc_json, 0)
        payload = json.loads(out_json.getvalue())
        self.assertTrue(payload["passed"])
        self.assertEqual(payload["verification_mode"], "CLEAN_ROOM_SYNTHETIC_VERIFIED")
        self.assertEqual(payload["report_sha256"], self.clean_report.report_sha256)

        out_text = io.StringIO()
        with contextlib.redirect_stdout(out_text):
            rc_text = main(["--clean-room"])
        self.assertEqual(rc_text, 0)
        self.assertIn("PASS (CLEAN_ROOM_SYNTHETIC_VERIFIED)", out_text.getvalue())

    def test_22_runtime_budget_under_3_seconds(self) -> None:
        self.assertLess(self.active_elapsed_s, 3.0)


if __name__ == "__main__":
    unittest.main()
