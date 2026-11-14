"""Phase 35 Stage-B (P1..P12+Fan) 10-Scenario Lifecycle, Serial Watchdog & H0->H1->H2 Zero-Drift Tests."""

from __future__ import annotations

import copy
import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from dataclasses import replace
from pathlib import Path
from unittest import mock

sys.dont_write_bytecode = True

import fx6_closure
from fx3_safety.runtime_antibrick_guards import (
    V_LD_SO_PRELOAD,
    V_NFLASHA10_FULL,
    audit_ld_so_preload_and_overlay,
    audit_nflasha10_vfat_budget,
)
from fx3_safety.serial_fault_detector_v2 import (
    DISPOSITION_ALLOWED_DEGRADED,
    DISPOSITION_FAIL_CLOSED_ABORT,
    DISPOSITION_PASS,
    audit_serial_boot_telemetry,
)
from fx6_closure import (
    FX6_APPFW_STAGE_B_SHA256,
    FX6_WLAN_RSRC_P12_SHA256,
    STAGE_B_AIRPLANE_SHADOW_KEYS,
    STAGE_B_FORWARD_STEP_IDS,
    STAGE_B_LIFECYCLE_SCHEMA,
    STAGE_B_LIFECYCLE_VERSION,
    STAGE_B_LIFO_UNWIND_STEP_IDS,
    STAGE_B_ORCHESTRATOR_CPIO_REL_PATH,
    STAGE_B_SCENARIO_IDS,
    StageBLifecycleReport,
    StageBOverlayBundle,
    build_stage_b_ram_overlay_package,
    generate_stage_b_boot_orchestrator_script,
    run_stage_b_lifecycle_drill,
)
from fx6_closure.__main__ import main as fx6_cli_main
from fx6_closure.backup_mount_tolerance_verifier import (
    DEFAULT_FX3_SEED_BK4_PATH,
    RamShadowBk4Bundle,
    build_canonical_fa0080_normal_boot_table,
    synthesize_ram_shadow_bk4,
)
from fx6_closure.hardware_readiness_packet import _is_forced_clean_room
from fx6_closure.stage_a_post_trial_auditor import (
    _populate_deterministic_hw_emmc_and_capture,
    verify_post_trial_zero_mutation,
)
from fx6_closure.stage_b_lifecycle_verifier import (
    _reset_sandbox_boot_state,
    _stage_sandbox_environment,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


class TestPhase35StageBLifecycle(unittest.TestCase):
    report: StageBLifecycleReport
    overlay: StageBOverlayBundle
    ram_bk4: RamShadowBk4Bundle
    use_clean_room: bool
    _shared_tmp: tempfile.TemporaryDirectory[str]
    _hw_dir: Path
    _h0_dir: Path
    _h2_dir: Path
    _sb_root: Path
    _orch_script: Path
    _stage_dir: Path
    _sb_env: dict[str, str]

    @classmethod
    def setUpClass(cls) -> None:
        cls.use_clean_room = _is_forced_clean_room()
        cls.report = run_stage_b_lifecycle_drill(repo_root=REPO_ROOT)
        cls.overlay = build_stage_b_ram_overlay_package()
        fa_tbl = build_canonical_fa0080_normal_boot_table(
            donor_seed_bk4_path=None if cls.use_clean_room else DEFAULT_FX3_SEED_BK4_PATH
        )
        cls.ram_bk4 = synthesize_ram_shadow_bk4(fa0080_table=fa_tbl)

        cls._shared_tmp = tempfile.TemporaryDirectory(prefix="fx6_p35_shared_")
        root = Path(cls._shared_tmp.name)
        cls._hw_dir = root / "hw"
        cls._h0_dir = root / "h0"
        cls._h2_dir = root / "h2"
        cls._sb_root = root / "sb"
        _populate_deterministic_hw_emmc_and_capture(
            cls._hw_dir,
            cls._h0_dir,
            body_serial="3018492",
            emmc_cid="15010038474d453452019c4a7b8e5f91",
            fa0080_table=fa_tbl,
            initialize_hw=True,
        )
        _populate_deterministic_hw_emmc_and_capture(
            cls._hw_dir,
            cls._h2_dir,
            body_serial="3018492",
            emmc_cid="15010038474d453452019c4a7b8e5f91",
            fa0080_table=fa_tbl,
            initialize_hw=False,
        )
        cls._orch_script, cls._stage_dir, cls._sb_env = _stage_sandbox_environment(
            cls._sb_root,
            root / "mb",
            cls._hw_dir,
            cls.overlay,
            cls.ram_bk4.bk4_bytes,
            cls.ram_bk4.sha256,
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls._shared_tmp.cleanup()

    def _scenario(self, scenario_id: str):
        by_id = {s.scenario_id: s for s in self.report.scenarios}
        self.assertIn(scenario_id, by_id)
        return by_id[scenario_id]

    def test_01_exports_and_hard_locked_redlines(self) -> None:
        expected_exports = {
            "STAGE_B_LIFECYCLE_SCHEMA",
            "STAGE_B_LIFECYCLE_VERSION",
            "STAGE_B_SCENARIO_IDS",
            "STAGE_B_FORWARD_STEP_IDS",
            "STAGE_B_LIFO_UNWIND_STEP_IDS",
            "STAGE_B_AIRPLANE_SHADOW_KEYS",
            "STAGE_B_ORCHESTRATOR_CPIO_REL_PATH",
            "StageBOverlayBundle",
            "StageBScenarioResult",
            "StageBLifecycleReport",
            "build_stage_b_ram_overlay_package",
            "generate_stage_b_boot_orchestrator_script",
            "run_stage_b_lifecycle_drill",
        }
        self.assertTrue(expected_exports.issubset(set(fx6_closure.__all__)))
        self.assertEqual(STAGE_B_LIFECYCLE_SCHEMA, "stage_b_lifecycle_verifier_v1")
        self.assertEqual(STAGE_B_LIFECYCLE_VERSION, "35.0.0")
        self.assertFalse(self.report.persistent_emmc_writes_authorized)
        self.assertFalse(self.report.persistent_write_release)
        self.assertTrue(self.report.p8_cp_mutation_forbidden)
        self.assertTrue(self.report.wbi_p5_write_and_hibernation_forbidden)
        self.assertEqual(self.report.usb_or_camera_operations, 0)

    def test_02_orchestrator_script_contract_and_posix_syntax(self) -> None:
        s1 = generate_stage_b_boot_orchestrator_script()
        s2 = generate_stage_b_boot_orchestrator_script()
        self.assertEqual(s1, s2)
        for token in (
            "#!/bin/sh",
            STAGE_B_ORCHESTRATOR_CPIO_REL_PATH,
            "mod_arm_once",
            "FX6_STAGE_A_CLEAR_BEFORE_EXEC",
            "STAGE_B_WBI_HIBERNATION_FORBIDDEN=1",
            "WDT_SET_STOP",
            "09_bind_ro_libWlanResource_so",
            "10_bind_ro_appFw_so",
            "11_bind_ro_ram_shadow_bk4",
            "12_activate_p11_uipc_cp_shim",
        ):
            self.assertIn(token, s1)
        proc = subprocess.run(
            ["/bin/sh", "-n"],
            input=s1,
            text=True,
            capture_output=True,
            timeout=5,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)

    def test_03_overlay_package_odonly_donor_reads_cpio_and_determinism(self) -> None:
        opened_flags: list[tuple[str, int]] = []
        real_open = os.open

        def spy_open(path, flags, *args, **kwargs):
            opened_flags.append((str(path), flags))
            return real_open(path, flags, *args, **kwargs)

        with mock.patch("os.open", side_effect=spy_open):
            bundle = build_stage_b_ram_overlay_package()

        write_mask = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND
        for p, fl in opened_flags:
            self.assertEqual(fl & write_mask, 0, msg=f"Non-O_RDONLY open on {p}: {fl:#x}")

        self.assertTrue(bundle.cpio_audit.valid)
        self.assertTrue(bundle.rollback_all_matched)
        self.assertGreaterEqual(bundle.staged_digest_count, 11)
        self.assertIn("lib/appFw.so", bundle.staged_blobs)
        self.assertIn("lib/libWlanResource.so", bundle.staged_blobs)
        self.assertIn("contracts/p11_uipc_cp_shim.json", bundle.staged_blobs)
        self.assertIn("contracts/bk4_airplane_shadow.json", bundle.staged_blobs)
        self.assertEqual(self.overlay.cpio_sha256, bundle.cpio_sha256)
        self.assertEqual(self.overlay.stage_b_appfw_sha256, bundle.stage_b_appfw_sha256)
        self.assertEqual(self.overlay.stage_b_wlan_rsrc_sha256, bundle.stage_b_wlan_rsrc_sha256)
        self.assertEqual(self.overlay.ram_shadow_bk4_sha256, bundle.ram_shadow_bk4_sha256)
        self.assertEqual(self.overlay.p11_uipc_shim_sha256, bundle.p11_uipc_shim_sha256)

    def test_04_overlay_manifest_redline_fields(self) -> None:
        m = self.overlay.overlay_manifest
        self.assertEqual(m["persistent_flash_writes"], 0)
        self.assertFalse(m["persistent_emmc_writes_authorized"])
        self.assertFalse(m["persistent_write_release"])
        self.assertTrue(m["wbi_p5_write_and_hibernation_forbidden"])
        self.assertEqual(m["wbi_mutation_bytes"], 0)
        self.assertTrue(m["p8_cp_mutation_forbidden"])
        self.assertEqual(m["cp_mutation_bytes"], 0)
        self.assertEqual(m["bk4_airplane_shadow_keys"], STAGE_B_AIRPLANE_SHADOW_KEYS)

    def test_05_report_top_level_stage_b_closure_and_zero_emmc_drift(self) -> None:
        self.assertTrue(self.report.all_checks_passed, msg=self.report.errors)
        self.assertEqual(self.report.scenario_count, 10)
        self.assertEqual(self.report.passed_scenario_count, 10)
        self.assertTrue(self.report.temp_dir_cleaned)
        self.assertTrue(self.report.h0_preflight_passed)
        self.assertTrue(self.report.h0_bundle_valid)
        self.assertTrue(self.report.p10_keymap_verified)
        self.assertTrue(self.report.p11_uipc_shim_verified)
        self.assertTrue(self.report.p12_wireless_guard_verified)
        self.assertTrue(self.report.bk4_airplane_shadow_verified)
        self.assertTrue(self.report.h2_zero_drift_verified)
        self.assertEqual(self.report.h2_audited_item_count, 13)
        self.assertEqual(self.report.h2_persistent_bytes_mutated, 0)
        self.assertEqual(len(self.report.h2_receipt_sha256), 64)
        self.assertEqual(len(self.report.report_sha256), 64)

    def test_06_donor_sha256_pins_and_verification_mode(self) -> None:
        if self.use_clean_room:
            self.assertEqual(self.report.verification_mode, "CLEAN_ROOM_SYNTHETIC_VERIFIED")
            self.assertEqual(len(self.report.stage_b_appfw_sha256), 64)
            self.assertEqual(len(self.report.stage_b_wlan_rsrc_sha256), 64)
        else:
            self.assertEqual(
                self.report.verification_mode, "LOCAL_DONOR_AND_POSIX_SANDBOX_VERIFIED"
            )
            self.assertEqual(self.report.stage_b_appfw_sha256, FX6_APPFW_STAGE_B_SHA256)
            self.assertEqual(self.report.stage_b_wlan_rsrc_sha256, FX6_WLAN_RSRC_P12_SHA256)

    def test_07_scenario_order_matches_canonical_10_matrix(self) -> None:
        ids = tuple(s.scenario_id for s in self.report.scenarios)
        self.assertEqual(ids, STAGE_B_SCENARIO_IDS)
        self.assertEqual(len(STAGE_B_FORWARD_STEP_IDS), 12)
        self.assertEqual(STAGE_B_LIFO_UNWIND_STEP_IDS, tuple(reversed(STAGE_B_FORWARD_STEP_IDS)))

    def test_08_s01_nominal_stage_b_boot_and_clean_powercycle(self) -> None:
        s01 = self._scenario("S01_NOMINAL_STAGE_B_BOOT_AND_CLEAN_POWERCYCLE")
        self.assertTrue(s01.passed, msg=s01.errors)
        self.assertEqual(s01.serial_disposition, DISPOSITION_PASS)
        self.assertTrue(s01.watchdog_passed)
        self.assertTrue(s01.clear_before_exec_ok)
        self.assertTrue(s01.verify_before_mount_ok)
        self.assertTrue(s01.lifo_teardown_ok)
        self.assertTrue(s01.zero_emmc_writes)
        self.assertTrue(s01.zero_wbi_writes)
        self.assertTrue(s01.zero_cp_writes)
        self.assertTrue(s01.zero_nvram_writes)
        self.assertEqual(s01.persistent_bytes_mutated, 0)
        self.assertEqual(s01.details["forward_step_count"], 12)
        self.assertEqual(s01.details["unwind_step_count"], 12)
        self.assertEqual(s01.details["audited_h2_items"], 13)
        self.assertTrue(s01.details["h2_u5_sticky_boot_clean"])
        self.assertEqual(s01.details["cold_reboot_branch"], "STOCK_FX3")

    def test_09_s02_stage_b_appfw_p10_sha_tamper_abort(self) -> None:
        s02 = self._scenario("S02_STAGE_B_APPFW_P10_SHA_TAMPER_ABORT")
        self.assertTrue(s02.passed, msg=s02.errors)
        self.assertEqual(s02.serial_disposition, DISPOSITION_FAIL_CLOSED_ABORT)
        self.assertEqual(s02.diag_code, "ERR_VERIFY_SHA256_MISMATCH:lib/appFw.so")
        self.assertTrue(s02.clear_before_exec_ok)
        self.assertTrue(s02.verify_before_mount_ok)
        self.assertEqual(s02.details["mounts_executed"], 0)
        self.assertTrue(s02.details["stock_boot_invoked"])

    def test_10_s03_stage_b_p12_libwlan_sha_tamper_abort(self) -> None:
        s03 = self._scenario("S03_STAGE_B_P12_LIBWLAN_SHA_TAMPER_ABORT")
        self.assertTrue(s03.passed, msg=s03.errors)
        self.assertEqual(s03.serial_disposition, DISPOSITION_FAIL_CLOSED_ABORT)
        self.assertEqual(s03.diag_code, "ERR_VERIFY_SHA256_MISMATCH:lib/libWlanResource.so")
        self.assertTrue(s03.clear_before_exec_ok)
        self.assertTrue(s03.verify_before_mount_ok)
        self.assertEqual(s03.details["mounts_executed"], 0)
        self.assertTrue(s03.details["zero_0x70d4_hang"])

    def test_11_s04_wf12_hardware_malfunction_00342260_survival(self) -> None:
        s04 = self._scenario("S04_WF12_HARDWARE_MALFUNCTION_00342260_SURVIVAL")
        self.assertTrue(s04.passed, msg=s04.errors)
        self.assertEqual(s04.serial_disposition, DISPOSITION_ALLOWED_DEGRADED)
        self.assertTrue(s04.watchdog_passed)
        self.assertTrue(s04.zero_nvram_writes)
        self.assertEqual(s04.details["p12_patched_rc"], 0)
        self.assertEqual(s04.details["bootloops"], 0)

    def test_12_s05_bt_bsa_uart_absent_survival(self) -> None:
        s05 = self._scenario("S05_BT_BSA_UART_ABSENT_SURVIVAL")
        self.assertTrue(s05.passed, msg=s05.errors)
        self.assertEqual(s05.serial_disposition, DISPOSITION_ALLOWED_DEGRADED)
        self.assertEqual(s05.diag_code, "BT_BSA_0xBB9_AIRPLANE_SHADOW_OK")
        self.assertEqual(
            s05.details["airplane_shadow_keys"],
            {"0x019e0012": "00", "0x0051000f": "00", "0x01a20002": "00"},
        )

    def test_13_s06_detached_smart_handle_xlr_h1_active(self) -> None:
        s06 = self._scenario("S06_DETACHED_SMART_HANDLE_XLR_H1_ACTIVE")
        self.assertTrue(s06.passed, msg=s06.errors)
        self.assertEqual(s06.serial_disposition, DISPOSITION_ALLOWED_DEGRADED)
        self.assertEqual(s06.diag_code, "P11_0x91DB059B_XLR_H1_PRESERVED")
        self.assertTrue(s06.details["xlr_h1_preserved"])
        self.assertEqual(s06.details["hotshoe_vma"], "0x5d90")

    def test_14_s07_ld_so_preload_injection_blocked(self) -> None:
        s07 = self._scenario("S07_LD_SO_PRELOAD_INJECTION_BLOCKED")
        self.assertTrue(s07.passed, msg=s07.errors)
        self.assertEqual(s07.serial_disposition, DISPOSITION_FAIL_CLOSED_ABORT)
        self.assertEqual(s07.diag_code, V_LD_SO_PRELOAD)

    def test_15_s08_nflasha10_0x10000009_headroom_guard(self) -> None:
        s08 = self._scenario("S08_NFLASHA10_0x10000009_HEADROOM_GUARD")
        self.assertTrue(s08.passed, msg=s08.errors)
        self.assertEqual(s08.serial_disposition, DISPOSITION_FAIL_CLOSED_ABORT)
        self.assertEqual(s08.diag_code, V_NFLASHA10_FULL)

    def test_16_s09_timer_ip_watchdog_timeout_auto_revert(self) -> None:
        s09 = self._scenario("S09_TIMER_IP_WATCHDOG_TIMEOUT_AUTO_REVERT")
        self.assertTrue(s09.passed, msg=s09.errors)
        self.assertEqual(s09.serial_disposition, DISPOSITION_FAIL_CLOSED_ABORT)
        self.assertFalse(s09.watchdog_passed)
        self.assertTrue(s09.clear_before_exec_ok)
        self.assertEqual(s09.details["soft_guard_sec"], 90.0)
        self.assertEqual(s09.details["timer_ip_ceiling_sec"], 220.0)
        self.assertTrue(s09.details["post_revert_h2_matched"])
        self.assertEqual(s09.persistent_bytes_mutated, 0)

    def test_17_s10_post_trial_drift_detection(self) -> None:
        s10 = self._scenario("S10_POST_TRIAL_DRIFT_DETECTION")
        self.assertTrue(s10.passed, msg=s10.errors)
        self.assertEqual(s10.status, "POST_TRIAL_DRIFT_DETECTED")
        self.assertEqual(s10.drifted_items, ("p12_cert", "p5_wbi_header"))
        self.assertEqual(s10.details["p12_cert_drift_bytes"], 1)
        self.assertEqual(s10.details["p5_wbi_drift_bytes"], 1)

    def test_18_unarmed_stock_passthrough_reentry_and_bis_guards_direct(self) -> None:
        # (a) Unarmed passthrough
        _reset_sandbox_boot_state(self._sb_root, armed=False)
        p1 = subprocess.run(
            ["/bin/sh", str(self._orch_script)],
            env=self._sb_env,
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertEqual(p1.returncode, 0)
        st1 = (self._sb_root / "tmp" / "stage_b_orchestrator_state.env").read_text(encoding="utf-8")
        self.assertIn("BOOT_BRANCH=STOCK_FX3", st1)

        # (b) Re-entry lock blocks double mount
        (self._sb_root / "tmp" / "stage_b_orchestrator.lock").write_text("", encoding="utf-8")
        p2 = subprocess.run(
            ["/bin/sh", str(self._orch_script)],
            env=self._sb_env,
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertEqual(p2.returncode, 0)
        st2 = (self._sb_root / "tmp" / "stage_b_orchestrator_state.env").read_text(encoding="utf-8")
        self.assertIn("BOOT_BRANCH=REENTRY_BLOCKED", st2)
        self.assertIn("DOUBLE_MOUNT_PREVENTED=1", st2)

        # (c) BIS mode rejected cleanly
        bootmode_p = self._sb_root / "proc" / "udm" / "upm_bootmode"
        try:
            _reset_sandbox_boot_state(self._sb_root, armed=True)
            bootmode_p.write_text("BIS\n", encoding="utf-8")
            p3 = subprocess.run(
                ["/bin/sh", str(self._orch_script)],
                env=self._sb_env,
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertEqual(p3.returncode, 0)
            st3 = (self._sb_root / "tmp" / "stage_b_orchestrator_state.env").read_text(encoding="utf-8")
            self.assertIn("ERR_WBI_BIS_MODE_FORBIDDEN", st3)
        finally:
            bootmode_p.write_text("NORMAL\n", encoding="utf-8")

    def test_19_sandbox_direct_p10_and_p12_tamper_rejection(self) -> None:
        appfw_p = self._stage_dir / "lib" / "appFw.so"
        orig_appfw = appfw_p.read_bytes()
        try:
            mut = bytearray(orig_appfw)
            mut[0] ^= 0x01
            appfw_p.write_bytes(bytes(mut))
            _reset_sandbox_boot_state(self._sb_root, armed=True)
            subprocess.run(
                ["/bin/sh", str(self._orch_script)],
                env=self._sb_env,
                capture_output=True,
                text=True,
                check=True,
            )
            st = (self._sb_root / "tmp" / "stage_b_orchestrator_state.env").read_text(encoding="utf-8")
            self.assertIn("DIAG_CODE=ERR_VERIFY_SHA256_MISMATCH:lib/appFw.so", st)
        finally:
            appfw_p.write_bytes(orig_appfw)

        wlan_p = self._stage_dir / "lib" / "libWlanResource.so"
        orig_wlan = wlan_p.read_bytes()
        try:
            mut_w = bytearray(orig_wlan)
            mut_w[0] ^= 0x01
            wlan_p.write_bytes(bytes(mut_w))
            _reset_sandbox_boot_state(self._sb_root, armed=True)
            subprocess.run(
                ["/bin/sh", str(self._orch_script)],
                env=self._sb_env,
                capture_output=True,
                text=True,
                check=True,
            )
            st_w = (self._sb_root / "tmp" / "stage_b_orchestrator_state.env").read_text(encoding="utf-8")
            self.assertIn("DIAG_CODE=ERR_VERIFY_SHA256_MISMATCH:lib/libWlanResource.so", st_w)
        finally:
            wlan_p.write_bytes(orig_wlan)

    def test_20_direct_post_trial_zero_mutation_and_drift_fail_closed(self) -> None:
        clean_rcpt = verify_post_trial_zero_mutation(self._h0_dir, self._h2_dir)
        self.assertTrue(clean_rcpt.all_checks_passed)
        self.assertEqual(clean_rcpt.persistent_bytes_mutated, 0)

        manifest_p = self._h2_dir / "backup-manifest.json"
        base_m_text = manifest_p.read_text(encoding="utf-8")
        base_m = json.loads(base_m_text)
        p12_p = self._h2_dir / "p12_cert.bin"
        orig_p12 = p12_p.read_bytes()
        try:
            mut = bytearray(orig_p12)
            mut[-1] ^= 0x01
            p12_p.write_bytes(bytes(mut))
            m2 = copy.deepcopy(base_m)
            sha = hashlib.sha256(bytes(mut)).hexdigest()
            m2["items"]["p12_cert"]["pass1_sha256"] = sha
            m2["items"]["p12_cert"]["pass2_sha256"] = sha
            manifest_p.write_text(json.dumps(m2, indent=2) + "\n", encoding="utf-8")
            drift_rcpt = verify_post_trial_zero_mutation(self._h0_dir, self._h2_dir)
            self.assertFalse(drift_rcpt.all_checks_passed)
            self.assertEqual(drift_rcpt.persistent_bytes_mutated, 1)
            self.assertEqual(drift_rcpt.drifted_items, ("p12_cert",))
        finally:
            p12_p.write_bytes(orig_p12)
            manifest_p.write_text(base_m_text, encoding="utf-8")

    def test_21_bk4_airplane_shadow_defaults_and_keys(self) -> None:
        self.assertEqual(
            STAGE_B_AIRPLANE_SHADOW_KEYS,
            {"0x019e0012": "00", "0x0051000f": "00", "0x01a20002": "00"},
        )
        self.assertEqual(self.report.bk4_airplane_shadow_keys, STAGE_B_AIRPLANE_SHADOW_KEYS)
        self.assertEqual(self.ram_bk4.target_backing, "RAM_TMPFS_SHADOW_ONLY")
        self.assertFalse(self.ram_bk4.flash_write_allowed)
        self.assertEqual(self.ram_bk4.active_byte8_selector, 0)
        self.assertGreater(self.ram_bk4.expected_checksum32, 0)
        self.assertEqual(self.ram_bk4.sha256, self.overlay.ram_shadow_bk4_sha256)

    def test_22_serial_fault_detector_v2_stage_b_dispositions(self) -> None:
        nominal = (
            "[    1.200000] FX6_STAGE_A_CLEAR_BEFORE_EXEC token_unlinked=1\n"
            "[    2.100000] WDT_SET_STOP source=stage_b_orchestrator\n"
            "[    2.700000] FX6_STAGE_A_VERIFY_RC=0\n"
            "[    7.100000] FX6_STAGE_B_BRIDGE stage=B p10_keymap=1 p11_uipc_shim=1 p12_wlan_guard=1\n"
        )
        res_pass = audit_serial_boot_telemetry(
            serial_text=nominal,
            native_faithful_mode=True,
            require_wdt_budget_proof=True,
        )
        self.assertTrue(res_pass.passed)
        self.assertEqual(res_pass.disposition, DISPOSITION_PASS)

        wdt_fail = (
            "[    1.200000] FX6_STAGE_A_CLEAR_BEFORE_EXEC token_unlinked=1\n"
            "[   95.000000] TIMER-IP stall\n"
        )
        res_abort = audit_serial_boot_telemetry(
            serial_text=wdt_fail,
            native_faithful_mode=True,
            require_wdt_budget_proof=True,
        )
        self.assertFalse(res_abort.passed)
        self.assertEqual(res_abort.disposition, DISPOSITION_FAIL_CLOSED_ABORT)

    def test_23_runtime_antibrick_guards_positive_and_negative(self) -> None:
        ok_preload = audit_ld_so_preload_and_overlay(
            script_text=(
                "rm -f /tmp/mod_arm_once\n"
                "sync\n"
                "mount --bind -o ro /tmp/fx6_stage_b/lib/appFw.so /usr/lib/appFw.so\n"
            ),
            target_paths=("/usr/lib/appFw.so",),
        )
        self.assertTrue(ok_preload.valid, msg=ok_preload.errors)

        bad_preload = audit_ld_so_preload_and_overlay(
            script_text="echo /tmp/x.so > /etc/ld.so.preload\n",
            target_paths=("/etc/ld.so.preload",),
        )
        self.assertFalse(bad_preload.valid)
        self.assertIn(V_LD_SO_PRELOAD, bad_preload.violation_codes)

        ok_vfat = audit_nflasha10_vfat_budget(
            current_used_bytes=2_000_000,
            planned_writes=({"path": "/setting/ram_only_note.txt", "bytes": 1024},),
        )
        self.assertTrue(ok_vfat.valid)

        bad_vfat = audit_nflasha10_vfat_budget(
            current_used_bytes=11_000_000,
            planned_writes=({"path": "/setting/oversize.bin", "bytes": 1_500_000},),
        )
        self.assertFalse(bad_vfat.valid)
        self.assertIn(V_NFLASHA10_FULL, bad_vfat.violation_codes)

    def test_24_deterministic_json_output_and_no_raw_bytes(self) -> None:
        rendered = self.report.to_deterministic_json(indent=2)
        parsed = json.loads(rendered)
        self.assertEqual(parsed["schema"], STAGE_B_LIFECYCLE_SCHEMA)
        self.assertEqual(parsed["scenario_count"], 10)
        self.assertEqual(parsed["passed_scenario_count"], 10)
        self.assertNotIn("b'", rendered)
        self.assertNotRegex(rendered, r'(?<![0-9A-Za-z_/.-])b[\'"]')

    def test_25_cli_run_stage_b_lifecycle_drill_dispatch_and_help(self) -> None:
        with tempfile.TemporaryDirectory(prefix="fx6_p35_cli_") as td:
            out_path = Path(td) / "stage_b_lifecycle.json"
            buf = io.StringIO()
            with mock.patch(
                "fx6_closure.stage_b_lifecycle_verifier.run_stage_b_lifecycle_drill",
                return_value=self.report,
            ) as mocked_fn, redirect_stdout(buf):
                rc = fx6_cli_main(
                    ["run-stage-b-lifecycle-drill", "--clean-room", "--output", str(out_path)]
                )
            self.assertEqual(rc, 0)
            mocked_fn.assert_called_once()
            self.assertTrue(mocked_fn.call_args.kwargs["synthetic_clean_room"])
            self.assertTrue(out_path.is_file())
            self.assertEqual(
                json.loads(out_path.read_text(encoding="utf-8"))["report_sha256"],
                self.report.report_sha256,
            )

            failed_report = replace(self.report, all_checks_passed=False)
            buf_fail = io.StringIO()
            with mock.patch(
                "fx6_closure.stage_b_lifecycle_verifier.run_stage_b_lifecycle_drill",
                return_value=failed_report,
            ), redirect_stdout(buf_fail):
                rc_fail = fx6_cli_main(["run-stage-b-lifecycle-drill"])
            self.assertEqual(rc_fail, 1)

        help_buf = io.StringIO()
        with redirect_stdout(help_buf), self.assertRaises(SystemExit) as ctx:
            fx6_cli_main(["run-stage-b-lifecycle-drill", "--help"])
        self.assertEqual(ctx.exception.code, 0)
        self.assertIn("--clean-room", help_buf.getvalue())
        self.assertIn("--output", help_buf.getvalue())


if __name__ == "__main__":
    unittest.main()
