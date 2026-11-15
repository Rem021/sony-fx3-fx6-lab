"""Phase 155 (Pillar 20 / 20/20 Milestone) Dual-Mode Fast Unit Tests (48 tests, <1s):

- Group 0 (01..08): Hard-locked safety redlines, __init__ exports, O_RDONLY donor inspection, clean-room parity & p1:/boot/kemco.txt validation
- Group A (09..23): Passive 1.8V RX-only 460800 8N1 6-stage parser & deterministic recovery-action triage (8 scenarios + edge cases)
- Group B (24..33): 1.8V Logic-Level & Multi-USB VMC-BNCM1 Contention Firewall (6 scenarios + boundary checks)
- Group C (34..42): Last-Resort Off-Chip Hardware ISP (1.8V VCCQ eMMC + 1.8V SPI-NOR) Emergency Verification Checklist (6 scenarios + EXT_CSD/CID guards)
- Group D (43..48): Suite determinism, `verify-uart-460800-isp-triage` CLI & `verify-all-recovery --with-phase155` (>= 20/20 pillars)
"""

from __future__ import annotations

from contextlib import redirect_stdout
from hashlib import sha256
import io
import json
import os
from pathlib import Path
import shutil
import sys
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
ROOT = HERE.parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import fx3_recovery
from fx3_recovery import __main__ as fx3_cli
from fx3_recovery.files import resolve_donor_path
from fx3_recovery.realhw_uart_460800_post_triage_and_isp_guard import (
    ACTION_CREATE_STOP_STAGEB_FLAG,
    ACTION_DISCONNECT_ADAPTER_CHECK_1V8,
    ACTION_EJECT_SD_47US_BYPASS,
    ACTION_HOLD_MENU_SHUTTER_POWER,
    ACTION_NONE_HEALTHY,
    ACTION_P1_LINE1_MODE_CLEAR,
    ACTION_TIER0_VAULT_RESTORE,
    ALLOW_BOOT_PARTITION_TARGETING,
    ALLOW_DESTRUCTIVE_FASTBOOT,
    BLOCKED_ACTIVE_TX_BYTES_ATTEMPTED,
    BLOCKED_CROSS_CAMERA_CID_VAULT_MISMATCH,
    BLOCKED_EXT_CSD_162_OTP_OR_179_177_GUARD,
    BLOCKED_ISP_1V8_RAIL_OVERVOLTAGE,
    BLOCKED_ISP_BUS_CONTENTION_SOC_ACTIVE,
    BLOCKED_ISP_FLYWIRE_TOO_LONG,
    BLOCKED_MULTI_USB_BUS_CONTENTION,
    BLOCKED_OVERVOLTAGE_1V8_PAD_HAZARD,
    BLOCKED_P1_KEMCO_MISSING_460800_CONSOLE,
    BLOCKED_PERSISTENT_ISP_WRITE_LOCKED,
    BLOCKED_PHYSICAL_TX_LINE_CONNECTED,
    BLOCKED_UNDERVOLTAGE_1V8_TAP,
    BLOCKED_UNSUPPORTED_460800_8N1_FRAMING,
    BLOCKED_VMC_BNCM1_LTC_CONTENTION,
    ERR_UNKNOWN_OR_EMPTY_UART_LOG,
    ISP_MAX_FLYWIRE_CM,
    ISP_SPI_NOR_NOMINAL_V,
    ISP_VCCQ_NOMINAL_V,
    OTP_FUSE_TOUCHES,
    OTP_FUSE_WRITES,
    P155_DONOR_FX3_CPAPP_B_RELPATH,
    P155_DONOR_FX3_INIT_RELPATH,
    P155_DONOR_FX3_KEMCO_RELPATH,
    P155_DONOR_FX3_LIBSENCORE_RELPATH,
    P155_DONOR_FX3_TOMCO_RELPATH,
    P155_PILLAR_A_SCENARIO_IDS,
    P155_PILLAR_B_SCENARIO_IDS,
    P155_PILLAR_C_SCENARIO_IDS,
    P155_PINNED_FX3_CPAPP_B_BYTES,
    P155_PINNED_FX3_CPAPP_B_HDR4K_SHA256,
    P155_PINNED_FX3_INIT_BYTES,
    P155_PINNED_FX3_INIT_SHA256,
    P155_PINNED_FX3_KEMCO_BYTES,
    P155_PINNED_FX3_KEMCO_SHA256,
    P155_PINNED_FX3_LIBSENCORE_BYTES,
    P155_PINNED_FX3_LIBSENCORE_SHA256,
    P155_PINNED_FX3_TOMCO_BYTES,
    P155_PINNED_FX3_TOMCO_SHA256,
    P155_STATUS_VERIFIED_PILLAR_A,
    P155_STATUS_VERIFIED_PILLAR_B,
    P155_STATUS_VERIFIED_PILLAR_C,
    P155_STATUS_VERIFIED_SUITE,
    PASSIVE_TX_BYTES_EMITTED,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHASE155_SCHEMA,
    PHASE155_VERSION,
    PHYSICAL_DEVICE_WRITES,
    RAW_FIRMWARE_BYTES_LEAKED,
    READ_ONLY_DONOR_ACCESS,
    SPI_NOR_WRITE_AUTHORIZED,
    UART_1V8_MAX_SAFE_V,
    UART_1V8_MIN_SAFE_V,
    UART_1V8_NOMINAL_V,
    UART_460800_BAUD,
    UART_460800_BOOT_STAGES,
    UART_460800_CONSOLE_ARG,
    UART_460800_FRAMING,
    UART_OVERVOLTAGE_3V3_V,
    UART_OVERVOLTAGE_5V0_V,
    Uart460800ElectricalConfig,
    VALID_460800_RECOVERY_ACTIONS,
    audit_1v8_uart_and_multi_usb_firewall,
    build_default_8_triage_scenarios,
    build_synthetic_isp_checklist_spec,
    build_synthetic_isp_ext_csd,
    build_synthetic_p1_diagnostic_kemco_profile,
    inspect_uart_460800_and_isp_donors_readonly,
    parse_ttyama0_460800_boot_stages,
    run_pillar_a_triage_8_scenario_suite,
    run_pillar_b_firewall_6_scenario_suite,
    run_pillar_c_isp_6_scenario_suite,
    run_realhw_uart_460800_post_triage_and_isp_suite,
    triage_ttyama0_460800_boot_log,
    validate_p1_diagnostic_kemco_profile,
    verify_last_resort_isp_checklist,
)


def _full_6stage_healthy_log() -> str:
    return (
        "[0.001] STAGE_0_BOOTROM_SPI_NOR_IPL: CXD90057 BootROM IPL OK\n"
        "[0.045] STAGE_1_BLOADER_BL31_ATF: BLoader + BL31 ATF handoff [TOMCO]\n"
        "[0.210] STAGE_2_LINUX_4_9_337_SCEL_KERNEL: Linux version 4.9.337-scel+ console=ttyAMA0,460800n8\n"
        "[0.650] STAGE_3_SPACC_CNFLASHA15_EXT2_USR: spacc cnflasha15 ext2 /usr mounted ro\n"
        "[0.810] STAGE_4_IM_ELF_SD_ESCAPE_WRAPPER: im.elf /sbin/init2 47us check clear\n"
        "[1.420] STAGE_5_STAGEB_APPFW_BIG6_READY: appFw.so BIG6_READY\n"
    )


class TestPhase155Uart460800AndIspGuard(unittest.TestCase):
    # ------------------------------------------------------------------
    # Group 0: Safety Redlines, Exports, O_RDONLY Donors & kemco Profile
    # ------------------------------------------------------------------

    def test_01_hard_locked_safety_constants(self) -> None:
        self.assertEqual(PASSIVE_TX_BYTES_EMITTED, 0)
        self.assertEqual(PHYSICAL_DEVICE_WRITES, 0)
        self.assertEqual(OTP_FUSE_TOUCHES, 0)
        self.assertEqual(OTP_FUSE_WRITES, 0)
        self.assertEqual(RAW_FIRMWARE_BYTES_LEAKED, 0)
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(PERSISTENT_WRITE_RELEASE)
        self.assertFalse(ALLOW_BOOT_PARTITION_TARGETING)
        self.assertFalse(ALLOW_DESTRUCTIVE_FASTBOOT)
        self.assertTrue(READ_ONLY_DONOR_ACCESS)

    def test_02_package_exports_phase155_symbols_and_no_shadowing(self) -> None:
        required_exports = (
            "PHASE155_SCHEMA",
            "P155_STATUS_VERIFIED_SUITE",
            "P155_STATUS_VERIFIED_PILLAR_A",
            "P155_STATUS_VERIFIED_PILLAR_B",
            "P155_STATUS_VERIFIED_PILLAR_C",
            "UART_460800_BOOT_STAGES",
            "VALID_460800_RECOVERY_ACTIONS",
            "audit_1v8_uart_and_multi_usb_firewall",
            "inspect_uart_460800_and_isp_donors_readonly",
            "parse_ttyama0_460800_boot_stages",
            "triage_ttyama0_460800_boot_log",
            "verify_last_resort_isp_checklist",
            "run_pillar_a_triage_8_scenario_suite",
            "run_pillar_b_firewall_6_scenario_suite",
            "run_pillar_c_isp_6_scenario_suite",
            "run_realhw_uart_460800_post_triage_and_isp_suite",
        )
        for sym in required_exports:
            self.assertTrue(hasattr(fx3_recovery, sym), f"missing export: {sym}")
            self.assertIn(sym, fx3_recovery.__all__)
        # Ensure earlier Phase 151 exports were not clobbered
        self.assertTrue(hasattr(fx3_recovery, "run_realhw_pnflasha_cnflasha_mtdro_tier0_vault_suite"))
        self.assertEqual(fx3_recovery.PHASE151_SCHEMA, "fx3-realhw-pnflasha-cnflasha-mtdro-tier0-vault-v1")

    def test_03_clean_room_donor_snapshot_leaks_zero_raw_bytes(self) -> None:
        snap = inspect_uart_460800_and_isp_donors_readonly(force_clean_room=True)
        self.assertTrue(snap.all_passed)
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(snap.access_mode, "SYNTHETIC_METADATA_ONLY")
        self.assertEqual(snap.donor_files_inspected, 0)
        self.assertEqual(snap.raw_firmware_bytes_leaked, 0)
        self.assertEqual(len(snap.artifacts), 5)
        self.assertEqual(snap.stock_kemco_uart_cfg, 1)
        self.assertEqual(snap.stock_kemco_console, "ttynull0")
        self.assertEqual(snap.tomco_uart_baudrate, UART_460800_BAUD)
        self.assertEqual(snap.tomco_console_enable, "N")
        self.assertTrue(snap.p1_diagnostic_kemco_valid)
        dumped = json.dumps(snap.to_dict(), sort_keys=True)
        self.assertNotIn("raw_bytes", dumped)
        self.assertNotIn("hexdump", dumped)

    def test_04_env_force_clean_room_overrides_default_mode(self) -> None:
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            snap = inspect_uart_460800_and_isp_donors_readonly(force_clean_room=None)
        self.assertTrue(snap.all_passed)
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(snap.donor_files_inspected, 0)

    def test_05_local_donor_rdonly_mode_or_clean_fallback(self) -> None:
        kemco_p = resolve_donor_path(P155_DONOR_FX3_KEMCO_RELPATH, require_file=True)
        snap = inspect_uart_460800_and_isp_donors_readonly(force_clean_room=False)
        self.assertTrue(snap.all_passed, f"donor errors: {snap.errors}")
        self.assertEqual(snap.raw_firmware_bytes_leaked, 0)
        if kemco_p is not None and kemco_p.is_file():
            self.assertEqual(snap.verification_mode, "LOCAL_DONOR_RDONLY")
            self.assertEqual(snap.access_mode, "O_RDONLY_NOFOLLOW_NONBLOCK")
            self.assertEqual(snap.donor_files_inspected, 5)
            by_id = {a.artifact_id: a for a in snap.artifacts}
            self.assertEqual(by_id["fx3_kemco_txt"].byte_length, P155_PINNED_FX3_KEMCO_BYTES)
            self.assertEqual(by_id["fx3_kemco_txt"].sha256_digest, P155_PINNED_FX3_KEMCO_SHA256)
            self.assertEqual(by_id["fx3_tomco_txt"].byte_length, P155_PINNED_FX3_TOMCO_BYTES)
            self.assertEqual(by_id["fx3_tomco_txt"].sha256_digest, P155_PINNED_FX3_TOMCO_SHA256)
            self.assertEqual(by_id["fx3_sbin_init"].byte_length, P155_PINNED_FX3_INIT_BYTES)
            self.assertEqual(by_id["fx3_sbin_init"].sha256_digest, P155_PINNED_FX3_INIT_SHA256)
            self.assertEqual(by_id["fx3_libsencore_so"].byte_length, P155_PINNED_FX3_LIBSENCORE_BYTES)
            self.assertEqual(by_id["fx3_libsencore_so"].sha256_digest, P155_PINNED_FX3_LIBSENCORE_SHA256)
            self.assertEqual(by_id["fx3_cpapp_b_bin"].byte_length, P155_PINNED_FX3_CPAPP_B_BYTES)
            self.assertEqual(by_id["fx3_cpapp_b_bin"].header_4k_sha256, P155_PINNED_FX3_CPAPP_B_HDR4K_SHA256)
        else:
            self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertEqual(snap.donor_files_inspected, 0)

    def test_06_local_donor_falls_back_when_donor_missing(self) -> None:
        with mock.patch(
            "fx3_recovery.realhw_uart_460800_post_triage_and_isp_guard.resolve_donor_path",
            return_value=None,
        ):
            snap = inspect_uart_460800_and_isp_donors_readonly(force_clean_room=False)
        self.assertTrue(snap.all_passed)
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(snap.donor_files_inspected, 0)

    def test_07_pinned_donor_relpaths_are_well_formed(self) -> None:
        rels = (
            P155_DONOR_FX3_KEMCO_RELPATH,
            P155_DONOR_FX3_TOMCO_RELPATH,
            P155_DONOR_FX3_INIT_RELPATH,
            P155_DONOR_FX3_LIBSENCORE_RELPATH,
            P155_DONOR_FX3_CPAPP_B_RELPATH,
        )
        for rel in rels:
            self.assertTrue(rel.startswith("sony-firmware-20261024/"))
            self.assertNotIn("..", rel)

    def test_08_validate_p1_diagnostic_kemco_profile_accepts_fx3_blocks_fx6_and_ttynull(self) -> None:
        good = build_synthetic_p1_diagnostic_kemco_profile()
        ok, errs = validate_p1_diagnostic_kemco_profile(good)
        self.assertTrue(ok, f"unexpected errs: {errs}")
        self.assertIn(UART_460800_CONSOLE_ARG, good)

        bad_fx6 = "cfg.uart=9\nconsole=ttynull0\n"
        ok6, errs6 = validate_p1_diagnostic_kemco_profile(bad_fx6)
        self.assertFalse(ok6)
        joined6 = " ".join(errs6)
        self.assertIn(BLOCKED_P1_KEMCO_MISSING_460800_CONSOLE, joined6)
        self.assertIn("forbidden_fx6_cfg_uart_9", joined6)
        self.assertIn("ttynull_silences_console", joined6)

    # ------------------------------------------------------------------
    # Group A: Passive 1.8V RX-Only 460800 8N1 6-Stage Triage Engine
    # ------------------------------------------------------------------

    def test_09_boot_stages_and_valid_actions_exact_contract(self) -> None:
        self.assertEqual(
            UART_460800_BOOT_STAGES,
            (
                "STAGE_0_BOOTROM_SPI_NOR_IPL",
                "STAGE_1_BLOADER_BL31_ATF",
                "STAGE_2_LINUX_4_9_337_SCEL_KERNEL",
                "STAGE_3_SPACC_CNFLASHA15_EXT2_USR",
                "STAGE_4_IM_ELF_SD_ESCAPE_WRAPPER",
                "STAGE_5_STAGEB_APPFW_BIG6_READY",
            ),
        )
        self.assertEqual(
            VALID_460800_RECOVERY_ACTIONS,
            (
                ACTION_EJECT_SD_47US_BYPASS,
                ACTION_CREATE_STOP_STAGEB_FLAG,
                ACTION_HOLD_MENU_SHUTTER_POWER,
                ACTION_P1_LINE1_MODE_CLEAR,
                ACTION_TIER0_VAULT_RESTORE,
            ),
        )

    def test_10_parse_full_6_stage_log_monotonic_and_transitions(self) -> None:
        trace = parse_ttyama0_460800_boot_stages(_full_6stage_healthy_log())
        self.assertEqual(trace.stages_observed, UART_460800_BOOT_STAGES)
        self.assertEqual(trace.highest_stage_reached, "STAGE_5_STAGEB_APPFW_BIG6_READY")
        self.assertEqual(trace.highest_stage_index, 5)
        self.assertEqual(len(trace.stage_transitions), 5)
        self.assertTrue(trace.valid_monotonic_progression)
        self.assertEqual(trace.framing_noise_ratio, 0.0)

    def test_11_parse_explicit_stage_tag_precedes_keyword_fallback(self) -> None:
        # "spi-nor" appears inside STAGE_1 line; explicit STAGE_1 marker must win over STAGE_0 keyword
        log_text = (
            "[0.001] STAGE_0_BOOTROM_SPI_NOR_IPL: CXD90057 IPL\n"
            "[0.050] STAGE_1_BLOADER_BL31_ATF: BLoader spi-nor crc check ok\n"
        )
        trace = parse_ttyama0_460800_boot_stages(log_text)
        self.assertEqual(
            trace.stages_observed,
            ("STAGE_0_BOOTROM_SPI_NOR_IPL", "STAGE_1_BLOADER_BL31_ATF"),
        )
        self.assertTrue(trace.valid_monotonic_progression)

    def test_12_parse_keyword_only_log_without_explicit_stage_prefixes(self) -> None:
        log_text = (
            "CXD90057 BootROM IPL OK\n"
            "BLoader [TOMCO] handoff to ATF BL31\n"
            "Linux version 4.9.337-scel+ console=ttyAMA0,460800n8\n"
            "crypt-emmc spacc cnflasha15 /usr mounted\n"
            "im.elf /sbin/init2 47us check\n"
            "appFw.so BIG6_READY\n"
        )
        trace = parse_ttyama0_460800_boot_stages(log_text)
        self.assertEqual(trace.stages_observed, UART_460800_BOOT_STAGES)
        self.assertTrue(trace.valid_monotonic_progression)

    def test_13_parse_detects_non_monotonic_regression_without_wdt_and_allows_wdt_reset(self) -> None:
        out_of_order = (
            "STAGE_2_LINUX_4_9_337_SCEL_KERNEL: kernel up\n"
            "STAGE_0_BOOTROM_SPI_NOR_IPL: unexpected reset\n"
        )
        t_bad = parse_ttyama0_460800_boot_stages(out_of_order)
        self.assertFalse(t_bad.valid_monotonic_progression)

        with_wdt = (
            "STAGE_2_LINUX_4_9_337_SCEL_KERNEL: kernel up\n"
            "watchdog reset triggered\n"
            "STAGE_0_BOOTROM_SPI_NOR_IPL: reboot\n"
        )
        t_wdt = parse_ttyama0_460800_boot_stages(with_wdt)
        self.assertTrue(t_wdt.valid_monotonic_progression)

    def test_14_triage_healthy_stage5_returns_none_healthy(self) -> None:
        res = triage_ttyama0_460800_boot_log(_full_6stage_healthy_log())
        self.assertTrue(res.passed)
        self.assertTrue(res.classified)
        self.assertTrue(res.safe_to_operate)
        self.assertFalse(res.fault_detected)
        self.assertEqual(res.recovery_action, ACTION_NONE_HEALTHY)
        self.assertEqual(res.highest_stage_reached, "STAGE_5_STAGEB_APPFW_BIG6_READY")
        self.assertEqual(res.passive_tx_bytes_emitted, 0)
        self.assertFalse(res.persistent_emmc_writes_authorized)
        self.assertFalse(res.spi_nor_write_authorized)

    def test_15_triage_maps_stage4_sd_overlay_manifest_to_eject_sd_47us_bypass(self) -> None:
        log_text = (
            "STAGE_0_BOOTROM_SPI_NOR_IPL: ok\n"
            "STAGE_1_BLOADER_BL31_ATF: ok\n"
            "STAGE_2_LINUX_4_9_337_SCEL_KERNEL: ttyAMA0 460800\n"
            "STAGE_3_SPACC_CNFLASHA15_EXT2_USR: ok\n"
            "STAGE_4_IM_ELF_SD_ESCAPE_WRAPPER: im.elf manifest_sha256_mismatch\n"
        )
        res = triage_ttyama0_460800_boot_log(log_text)
        self.assertTrue(res.passed)
        self.assertTrue(res.fault_detected)
        self.assertEqual(res.recovery_action, ACTION_EJECT_SD_47US_BYPASS)
        self.assertEqual(res.recovery_tier, "TIER_0_EJECT_SD_47US")

    def test_16_triage_maps_appfw_crash_loop_to_create_stop_stageb_flag(self) -> None:
        log_text = _full_6stage_healthy_log() + "STAGE_5_STAGEB_APPFW_BIG6_READY: appFw.so segfault crash loop\n"
        res = triage_ttyama0_460800_boot_log(log_text)
        self.assertTrue(res.passed)
        self.assertTrue(res.fault_detected)
        self.assertEqual(res.recovery_action, ACTION_CREATE_STOP_STAGEB_FLAG)
        self.assertEqual(res.recovery_tier, "TIER_0_SD_FLAG")

    def test_17_triage_maps_init2_early_stall_to_hold_menu_shutter_power(self) -> None:
        log_text = (
            "STAGE_0_BOOTROM_SPI_NOR_IPL: ok\n"
            "STAGE_1_BLOADER_BL31_ATF: ok\n"
            "STAGE_2_LINUX_4_9_337_SCEL_KERNEL: ttyAMA0 460800\n"
            "STAGE_3_SPACC_CNFLASHA15_EXT2_USR: ok\n"
            "STAGE_4_IM_ELF_SD_ESCAPE_WRAPPER: /sbin/init2 init2_early_stall\n"
        )
        res = triage_ttyama0_460800_boot_log(log_text)
        self.assertTrue(res.passed)
        self.assertEqual(res.recovery_action, ACTION_HOLD_MENU_SHUTTER_POWER)
        self.assertEqual(res.recovery_tier, "TIER_0_HARDWARE_KEY_CHORD")

    def test_18_triage_maps_p1_line1_latch_to_p1_line1_mode_clear(self) -> None:
        log_text = (
            "STAGE_0_BOOTROM_SPI_NOR_IPL: ok\n"
            "STAGE_1_BLOADER_BL31_ATF: ok\n"
            "STAGE_2_LINUX_4_9_337_SCEL_KERNEL: ttyAMA0 460800\n"
            "STAGE_3_SPACC_CNFLASHA15_EXT2_USR: p1_line1_mode_latch mode=1 sticky\n"
        )
        res = triage_ttyama0_460800_boot_log(log_text)
        self.assertTrue(res.passed)
        self.assertEqual(res.recovery_action, ACTION_P1_LINE1_MODE_CLEAR)
        self.assertEqual(res.recovery_tier, "TIER_1_P1_MODE_CLEAR")

    def test_19_triage_maps_stage0_to_3_erofs_spacc_or_spi_nor_to_tier0_vault_restore(self) -> None:
        log_erofs = (
            "STAGE_0_BOOTROM_SPI_NOR_IPL: ok\n"
            "STAGE_1_BLOADER_BL31_ATF: ok\n"
            "STAGE_2_LINUX_4_9_337_SCEL_KERNEL: ok\n"
            "STAGE_3_SPACC_CNFLASHA15_EXT2_USR: EXT2-fs error EROFS Kernel panic\n"
        )
        res3 = triage_ttyama0_460800_boot_log(log_erofs)
        self.assertTrue(res3.passed)
        self.assertEqual(res3.recovery_action, ACTION_TIER0_VAULT_RESTORE)

        log_s0 = "STAGE_0_BOOTROM_SPI_NOR_IPL: CXD90057 BootROM bootrom_usb_fallback error\n"
        res0 = triage_ttyama0_460800_boot_log(log_s0)
        self.assertTrue(res0.passed)
        self.assertEqual(res0.recovery_action, ACTION_TIER0_VAULT_RESTORE)

    def test_20_triage_fail_closed_on_empty_garbled_or_incomplete_log(self) -> None:
        res_empty = triage_ttyama0_460800_boot_log("   \n")
        self.assertFalse(res_empty.passed)
        self.assertFalse(res_empty.classified)
        self.assertEqual(res_empty.fault_category, ERR_UNKNOWN_OR_EMPTY_UART_LOG)
        self.assertEqual(res_empty.recovery_action, ACTION_DISCONNECT_ADAPTER_CHECK_1V8)

        res_garble = triage_ttyama0_460800_boot_log("\ufffd\ufffd\ufffd\x00\x02STAGE_2")
        self.assertFalse(res_garble.passed)
        self.assertFalse(res_garble.classified)
        self.assertEqual(res_garble.recovery_action, ACTION_DISCONNECT_ADAPTER_CHECK_1V8)

        res_inc = triage_ttyama0_460800_boot_log("STAGE_2_LINUX_4_9_337_SCEL_KERNEL: ttyAMA0 460800 ok\n")
        self.assertFalse(res_inc.passed)
        self.assertFalse(res_inc.classified)
        self.assertEqual(res_inc.recovery_action, ACTION_TIER0_VAULT_RESTORE)

    def test_21_triage_aborts_immediately_when_electrical_firewall_fails(self) -> None:
        bad_cfg = Uart460800ElectricalConfig(io_voltage_v=UART_OVERVOLTAGE_3V3_V)
        res = triage_ttyama0_460800_boot_log(_full_6stage_healthy_log(), electrical_cfg=bad_cfg)
        self.assertFalse(res.passed)
        self.assertFalse(res.safe_to_operate)
        self.assertEqual(res.recovery_action, ACTION_DISCONNECT_ADAPTER_CHECK_1V8)
        self.assertEqual(res.fault_category, BLOCKED_OVERVOLTAGE_1V8_PAD_HAZARD)
        self.assertIn(BLOCKED_OVERVOLTAGE_1V8_PAD_HAZARD, res.firewall_decision.blocked_codes)
        self.assertEqual(res.passive_tx_bytes_emitted, 0)

    def test_22_default_8_scenarios_cover_all_five_recovery_actions(self) -> None:
        scenarios = build_default_8_triage_scenarios()
        self.assertEqual(len(scenarios), 8)
        actions = {s[1] for s in scenarios}
        for act in VALID_460800_RECOVERY_ACTIONS:
            self.assertIn(act, actions)

    def test_23_pillar_a_triage_8_scenario_suite_passes(self) -> None:
        pa = run_pillar_a_triage_8_scenario_suite()
        self.assertTrue(pa.passed, f"Pillar A failed: {pa}")
        self.assertEqual(pa.status, P155_STATUS_VERIFIED_PILLAR_A)
        self.assertEqual(pa.scenarios_passed, 8)
        self.assertEqual(pa.scenarios_total, 8)
        self.assertEqual(tuple(s.scenario_id for s in pa.scenarios), P155_PILLAR_A_SCENARIO_IDS)
        self.assertEqual(pa.passive_tx_bytes_emitted, 0)
        self.assertFalse(pa.persistent_emmc_writes_authorized)

    # ------------------------------------------------------------------
    # Group B: 1.8V Logic-Level & Multi-USB VMC-BNCM1 Contention Firewall
    # ------------------------------------------------------------------

    def test_24_firewall_accepts_strict_1v8_rx_only_460800_8n1(self) -> None:
        dec = audit_1v8_uart_and_multi_usb_firewall(Uart460800ElectricalConfig())
        self.assertTrue(dec.safe, f"unexpected firewall block: {dec}")
        self.assertEqual(dec.status, "VERIFIED_1V8_RX_ONLY_460800_FIREWALL")
        self.assertEqual(dec.blocked_codes, ())
        self.assertEqual(dec.passive_tx_bytes_emitted, 0)
        self.assertEqual(dec.recommended_action, ACTION_NONE_HEALTHY)

    def test_25_firewall_voltage_boundaries_1v65_to_1v98(self) -> None:
        self.assertTrue(audit_1v8_uart_and_multi_usb_firewall(Uart460800ElectricalConfig(io_voltage_v=UART_1V8_MIN_SAFE_V)).safe)
        self.assertTrue(audit_1v8_uart_and_multi_usb_firewall(Uart460800ElectricalConfig(io_voltage_v=UART_1V8_MAX_SAFE_V)).safe)
        self.assertEqual(UART_1V8_NOMINAL_V, 1.80)

        under = audit_1v8_uart_and_multi_usb_firewall(Uart460800ElectricalConfig(io_voltage_v=1.50))
        self.assertFalse(under.safe)
        self.assertIn(BLOCKED_UNDERVOLTAGE_1V8_TAP, under.blocked_codes)

    def test_26_firewall_hard_blocks_3v3_and_5v0_uart_adapters(self) -> None:
        d33 = audit_1v8_uart_and_multi_usb_firewall(Uart460800ElectricalConfig(io_voltage_v=UART_OVERVOLTAGE_3V3_V))
        self.assertFalse(d33.safe)
        self.assertIn(BLOCKED_OVERVOLTAGE_1V8_PAD_HAZARD, d33.blocked_codes)
        self.assertEqual(d33.recommended_action, ACTION_DISCONNECT_ADAPTER_CHECK_1V8)

        d50 = audit_1v8_uart_and_multi_usb_firewall(Uart460800ElectricalConfig(io_voltage_v=UART_OVERVOLTAGE_5V0_V))
        self.assertFalse(d50.safe)
        self.assertIn(BLOCKED_OVERVOLTAGE_1V8_PAD_HAZARD, d50.blocked_codes)

    def test_27_firewall_enforces_physical_tx_disconnected_and_zero_tx_bytes(self) -> None:
        d_pin = audit_1v8_uart_and_multi_usb_firewall(Uart460800ElectricalConfig(tx_line_connected=True))
        self.assertFalse(d_pin.safe)
        self.assertIn(BLOCKED_PHYSICAL_TX_LINE_CONNECTED, d_pin.blocked_codes)
        self.assertEqual(d_pin.passive_tx_bytes_emitted, 0)

        d_bytes = audit_1v8_uart_and_multi_usb_firewall(
            Uart460800ElectricalConfig(tx_line_connected=False, tx_bytes_attempted=0),
            active_tx_payload=b"reboot\n",
        )
        self.assertFalse(d_bytes.safe)
        self.assertIn(BLOCKED_ACTIVE_TX_BYTES_ATTEMPTED, d_bytes.blocked_codes)
        self.assertEqual(d_bytes.tx_bytes_attempted, 7)
        self.assertEqual(d_bytes.passive_tx_bytes_emitted, 0)

    def test_28_firewall_blocks_vmc_bncm1_680k_ltc_and_lanc_100k_contention(self) -> None:
        d_ltc = audit_1v8_uart_and_multi_usb_firewall(
            Uart460800ElectricalConfig(vmc_bncm1_ltc_attached=True, pin6_id_resistor_ohm=680_000.0)
        )
        self.assertFalse(d_ltc.safe)
        self.assertIn(BLOCKED_VMC_BNCM1_LTC_CONTENTION, d_ltc.blocked_codes)

        # Even if boolean flag is False, detecting 680k or 100k resistor still blocks!
        d_res_ltc = audit_1v8_uart_and_multi_usb_firewall(Uart460800ElectricalConfig(pin6_id_resistor_ohm=680_000.0))
        self.assertFalse(d_res_ltc.safe)
        self.assertIn(BLOCKED_VMC_BNCM1_LTC_CONTENTION, d_res_ltc.blocked_codes)

        d_lanc = audit_1v8_uart_and_multi_usb_firewall(Uart460800ElectricalConfig(pin6_id_resistor_ohm=100_000.0))
        self.assertFalse(d_lanc.safe)
        self.assertIn(BLOCKED_VMC_BNCM1_LTC_CONTENTION, d_lanc.blocked_codes)

    def test_29_firewall_blocks_multi_usb_concurrent_bus_contention(self) -> None:
        for competing in ("MSC_054C_0DA1", "SERVICE_054C_0336", "USB_C_DUAL_HOST"):
            dec = audit_1v8_uart_and_multi_usb_firewall(
                Uart460800ElectricalConfig(multi_usb_ports_active=("ttyAMA0_RX_1V8", competing))
            )
            self.assertFalse(dec.safe, f"expected block for {competing}")
            self.assertIn(BLOCKED_MULTI_USB_BUS_CONTENTION, dec.blocked_codes)

    def test_30_firewall_blocks_wrong_baud_or_framing(self) -> None:
        d_baud = audit_1v8_uart_and_multi_usb_firewall(Uart460800ElectricalConfig(baud_rate=115200))
        self.assertFalse(d_baud.safe)
        self.assertIn(BLOCKED_UNSUPPORTED_460800_8N1_FRAMING, d_baud.blocked_codes)

        d_frm = audit_1v8_uart_and_multi_usb_firewall(Uart460800ElectricalConfig(framing="7E1"))
        self.assertFalse(d_frm.safe)
        self.assertIn(BLOCKED_UNSUPPORTED_460800_8N1_FRAMING, d_frm.blocked_codes)
        self.assertEqual(UART_460800_FRAMING, "8N1")

    def test_31_firewall_reports_multiple_simultaneous_violations(self) -> None:
        dec = audit_1v8_uart_and_multi_usb_firewall(
            Uart460800ElectricalConfig(
                io_voltage_v=5.0,
                tx_line_connected=True,
                vmc_bncm1_ltc_attached=True,
                multi_usb_ports_active=("ttyAMA0_RX_1V8", "MSC_054C_0DA1"),
                baud_rate=9600,
            ),
            active_tx_payload=b"x",
        )
        self.assertFalse(dec.safe)
        self.assertEqual(len(dec.blocked_codes), 6)
        self.assertEqual(dec.passive_tx_bytes_emitted, 0)

    def test_32_firewall_to_dict_json_safe(self) -> None:
        dec = audit_1v8_uart_and_multi_usb_firewall(Uart460800ElectricalConfig())
        encoded = json.dumps(dec.to_dict(), sort_keys=True, allow_nan=False)
        self.assertIn("VERIFIED_1V8_RX_ONLY_460800_FIREWALL", encoded)

    def test_33_pillar_b_firewall_6_scenario_suite_passes(self) -> None:
        pb = run_pillar_b_firewall_6_scenario_suite()
        self.assertTrue(pb.passed, f"Pillar B failed: {pb}")
        self.assertEqual(pb.status, P155_STATUS_VERIFIED_PILLAR_B)
        self.assertEqual(pb.scenarios_passed, 6)
        self.assertEqual(pb.scenarios_total, 6)
        self.assertEqual(tuple(s.scenario_id for s in pb.scenarios), P155_PILLAR_B_SCENARIO_IDS)
        self.assertEqual(pb.passive_tx_bytes_emitted, 0)

    # ------------------------------------------------------------------
    # Group C: Last-Resort Off-Chip Hardware ISP (1.8V VCCQ + SPI-NOR)
    # ------------------------------------------------------------------

    def test_34_isp_checklist_happy_path_readonly_bench_verified(self) -> None:
        spec = build_synthetic_isp_checklist_spec()
        rep = verify_last_resort_isp_checklist(spec)
        self.assertTrue(rep.passed, f"ISP happy path failed: {rep}")
        self.assertTrue(rep.theoretical_bench_repair_eligible)
        self.assertTrue(rep.electrical_isolation_ok)
        self.assertTrue(rep.cid_vault_paired)
        self.assertTrue(rep.pnflasha_two_pass_verified)
        self.assertTrue(rep.mtd0ro_two_pass_verified)
        self.assertEqual(rep.partition_access, 0)
        self.assertIn(rep.boot_partition_enable, (1, 2))
        self.assertEqual(rep.otp_fuse_touches, 0)
        self.assertEqual(rep.physical_device_writes, 0)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.spi_nor_write_authorized)
        self.assertFalse(rep.persistent_write_release)
        self.assertEqual(ISP_VCCQ_NOMINAL_V, 1.80)
        self.assertEqual(ISP_SPI_NOR_NOMINAL_V, 1.80)

    def test_35_isp_checklist_blocks_3v3_or_5v0_vccq_and_spinor_overvoltage(self) -> None:
        r1 = verify_last_resort_isp_checklist(build_synthetic_isp_checklist_spec(vccq_voltage_v=3.30))
        self.assertFalse(r1.passed)
        self.assertIn(BLOCKED_ISP_1V8_RAIL_OVERVOLTAGE, r1.blocked_codes)

        r2 = verify_last_resort_isp_checklist(build_synthetic_isp_checklist_spec(spi_nor_voltage_v=5.00))
        self.assertFalse(r2.passed)
        self.assertIn(BLOCKED_ISP_1V8_RAIL_OVERVOLTAGE, r2.blocked_codes)

    def test_36_isp_checklist_blocks_active_soc_or_attached_battery_usb(self) -> None:
        r_rst = verify_last_resort_isp_checklist(build_synthetic_isp_checklist_spec(soc_reset_held_low=False))
        self.assertFalse(r_rst.passed)
        self.assertFalse(r_rst.electrical_isolation_ok)
        self.assertIn(BLOCKED_ISP_BUS_CONTENTION_SOC_ACTIVE, r_rst.blocked_codes)

        r_pwr = verify_last_resort_isp_checklist(
            build_synthetic_isp_checklist_spec(main_battery_and_usb_disconnected=False)
        )
        self.assertFalse(r_pwr.passed)
        self.assertIn(BLOCKED_ISP_BUS_CONTENTION_SOC_ACTIVE, r_pwr.blocked_codes)

    def test_37_isp_checklist_blocks_flywire_exceeding_10cm(self) -> None:
        self.assertEqual(ISP_MAX_FLYWIRE_CM, 10.0)
        r_ok = verify_last_resort_isp_checklist(build_synthetic_isp_checklist_spec(flywire_length_cm=10.0))
        self.assertTrue(r_ok.passed)

        r_long = verify_last_resort_isp_checklist(build_synthetic_isp_checklist_spec(flywire_length_cm=15.0))
        self.assertFalse(r_long.passed)
        self.assertIn(BLOCKED_ISP_FLYWIRE_TOO_LONG, r_long.blocked_codes)

    def test_38_isp_checklist_blocks_ext_csd_179_177_corruption(self) -> None:
        # PARTITION_ACCESS non-zero (RPMB/BOOT0 leaked) & BOOT_PARTITION_ENABLE=7 (UDA)
        r_179 = verify_last_resort_isp_checklist(build_synthetic_isp_checklist_spec(part_config=0x79))
        self.assertFalse(r_179.passed)
        self.assertIn(BLOCKED_EXT_CSD_162_OTP_OR_179_177_GUARD, r_179.blocked_codes)

        # EXT_CSD[177] reserved bits set
        r_177 = verify_last_resort_isp_checklist(build_synthetic_isp_checklist_spec(boot_bus_conditions=0xC0))
        self.assertFalse(r_177.passed)
        self.assertIn(BLOCKED_EXT_CSD_162_OTP_OR_179_177_GUARD, r_177.blocked_codes)

        # Truncated EXT_CSD
        spec = build_synthetic_isp_checklist_spec()
        r_short = verify_last_resort_isp_checklist(type(spec)(**{**spec.__dict__, "ext_csd_bytes": b"\x00" * 64}))
        self.assertFalse(r_short.passed)
        self.assertIn(BLOCKED_EXT_CSD_162_OTP_OR_179_177_GUARD, r_short.blocked_codes)

    def test_39_isp_checklist_blocks_ext_csd_162_otp_write_and_reserved_values(self) -> None:
        r_otp = verify_last_resort_isp_checklist(build_synthetic_isp_checklist_spec(otp_162_write_requested=True))
        self.assertFalse(r_otp.passed)
        self.assertIn(BLOCKED_EXT_CSD_162_OTP_OR_179_177_GUARD, r_otp.blocked_codes)

        r_res = verify_last_resort_isp_checklist(build_synthetic_isp_checklist_spec(rst_n_function=0x03))
        self.assertFalse(r_res.passed)
        self.assertIn(BLOCKED_EXT_CSD_162_OTP_OR_179_177_GUARD, r_res.blocked_codes)
        self.assertEqual(len(build_synthetic_isp_ext_csd()), 512)

    def test_40_isp_checklist_blocks_cross_camera_cid_or_pnflasha_mtd0ro_mismatch(self) -> None:
        r_cid = verify_last_resort_isp_checklist(build_synthetic_isp_checklist_spec(cross_camera_cid_mismatch=True))
        self.assertFalse(r_cid.passed)
        self.assertFalse(r_cid.cid_vault_paired)
        self.assertIn(BLOCKED_CROSS_CAMERA_CID_VAULT_MISMATCH, r_cid.blocked_codes)

        spec = build_synthetic_isp_checklist_spec()
        r_mtd = verify_last_resort_isp_checklist(
            type(spec)(**{**spec.__dict__, "mtd0ro_readback_sha256": sha256(b"corrupt").hexdigest()})
        )
        self.assertFalse(r_mtd.passed)
        self.assertFalse(r_mtd.mtd0ro_two_pass_verified)
        self.assertIn(BLOCKED_CROSS_CAMERA_CID_VAULT_MISMATCH, r_mtd.blocked_codes)

    def test_41_isp_checklist_hard_blocks_persistent_write_authorization_requests(self) -> None:
        r_w = verify_last_resort_isp_checklist(
            build_synthetic_isp_checklist_spec(request_persistent_emmc_writes=True, request_spi_nor_write=True)
        )
        self.assertFalse(r_w.passed)
        self.assertFalse(r_w.theoretical_bench_repair_eligible)
        self.assertIn(BLOCKED_PERSISTENT_ISP_WRITE_LOCKED, r_w.blocked_codes)
        self.assertFalse(r_w.persistent_emmc_writes_authorized)
        self.assertFalse(r_w.spi_nor_write_authorized)

    def test_42_pillar_c_isp_6_scenario_suite_passes(self) -> None:
        pc = run_pillar_c_isp_6_scenario_suite()
        self.assertTrue(pc.passed, f"Pillar C failed: {pc}")
        self.assertEqual(pc.status, P155_STATUS_VERIFIED_PILLAR_C)
        self.assertEqual(pc.scenarios_passed, 6)
        self.assertEqual(pc.scenarios_total, 6)
        self.assertEqual(tuple(s.scenario_id for s in pc.scenarios), P155_PILLAR_C_SCENARIO_IDS)
        self.assertFalse(pc.persistent_emmc_writes_authorized)
        self.assertFalse(pc.spi_nor_write_authorized)

    # ------------------------------------------------------------------
    # Group D: Suite Determinism, CLI & 20/20 Pillar Milestone
    # ------------------------------------------------------------------

    def test_43_suite_determinism_in_clean_room_and_local_donor_modes(self) -> None:
        r1 = run_realhw_uart_460800_post_triage_and_isp_suite(force_clean_room=True)
        r2 = run_realhw_uart_460800_post_triage_and_isp_suite(force_clean_room=True)
        self.assertTrue(r1.all_passed)
        self.assertEqual(r1.schema, PHASE155_SCHEMA)
        self.assertEqual(r1.version, PHASE155_VERSION)
        self.assertEqual(r1.status, P155_STATUS_VERIFIED_SUITE)
        self.assertEqual(r1.suite_sha256, r2.suite_sha256)
        self.assertEqual(r1.passive_tx_bytes_emitted, 0)
        self.assertEqual(r1.physical_device_writes, 0)
        self.assertEqual(r1.otp_fuse_touches, 0)
        self.assertFalse(r1.persistent_emmc_writes_authorized)
        self.assertFalse(r1.spi_nor_write_authorized)
        json.dumps(r1.to_dict(), sort_keys=True, allow_nan=False)

        r_loc = run_realhw_uart_460800_post_triage_and_isp_suite(force_clean_room=False)
        self.assertTrue(r_loc.all_passed)
        self.assertEqual(r_loc.pillar_a_triage_8_scenarios.scenarios_passed, 8)
        self.assertEqual(r_loc.pillar_b_firewall_6_scenarios.scenarios_passed, 6)
        self.assertEqual(r_loc.pillar_c_isp_6_scenarios.scenarios_passed, 6)

    def test_44_cli_verify_uart_460800_isp_triage_json_and_out(self) -> None:
        buf = io.StringIO()
        with (
            mock.patch.object(sys, "argv", ["fx3_recovery", "verify-uart-460800-isp-triage", "--clean-room", "--json"]),
            redirect_stdout(buf),
        ):
            rc = fx3_cli.main()
        self.assertEqual(rc, 0)
        parsed = json.loads(buf.getvalue())
        self.assertTrue(parsed["all_passed"])
        self.assertEqual(parsed["verification_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(parsed["pillar_a_triage_8_scenarios"]["scenarios_passed"], 8)
        self.assertEqual(parsed["pillar_b_firewall_6_scenarios"]["scenarios_passed"], 6)
        self.assertEqual(parsed["pillar_c_isp_6_scenarios"]["scenarios_passed"], 6)
        self.assertEqual(parsed["passive_tx_bytes_emitted"], 0)
        self.assertEqual(parsed["physical_device_writes"], 0)
        self.assertEqual(parsed["otp_fuse_touches"], 0)
        self.assertFalse(parsed["spi_nor_write_authorized"])
        self.assertFalse(parsed["persistent_emmc_writes_authorized"])

        scratch_root = ROOT / "work" / "_tests" / "phase155_cli_out"
        if scratch_root.exists():
            shutil.rmtree(scratch_root)
        scratch_root.parent.mkdir(parents=True, exist_ok=True)
        try:
            buf_out = io.StringIO()
            with (
                mock.patch.object(
                    sys,
                    "argv",
                    [
                        "fx3_recovery",
                        "verify-uart-460800-isp-triage",
                        "--clean-room",
                        "--json",
                        "--out",
                        str(scratch_root),
                    ],
                ),
                redirect_stdout(buf_out),
            ):
                rc_out = fx3_cli.main()
            self.assertEqual(rc_out, 0)
            rep_file = scratch_root / "uart-460800-isp-triage-report.json"
            self.assertTrue(rep_file.is_file())
            written = json.loads(rep_file.read_text(encoding="utf-8"))
            self.assertEqual(written["schema"], PHASE155_SCHEMA)
        finally:
            if scratch_root.exists():
                shutil.rmtree(scratch_root)

    def test_45_cli_verify_uart_460800_isp_triage_text_and_nonzero_on_failure(self) -> None:
        buf_txt = io.StringIO()
        with (
            mock.patch.object(sys, "argv", ["fx3_recovery", "verify-uart-460800-isp-triage", "--clean-room"]),
            redirect_stdout(buf_txt),
        ):
            rc_txt = fx3_cli.main()
        self.assertEqual(rc_txt, 0)
        txt = buf_txt.getvalue()
        self.assertIn(f"status={P155_STATUS_VERIFIED_SUITE}", txt)
        self.assertIn("pillar_a_triage=8/8", txt)
        self.assertIn("pillar_b_firewall=6/6", txt)
        self.assertIn("pillar_c_isp=6/6", txt)
        self.assertIn("passive_tx_bytes_emitted=0", txt)
        self.assertIn("physical_device_writes=0", txt)
        self.assertIn("spi_nor_write_authorized=False", txt)
        self.assertIn("persistent_emmc_writes_authorized=False", txt)

        rep = run_realhw_uart_460800_post_triage_and_isp_suite(force_clean_room=True)
        failing = type(rep)(**{**rep.__dict__, "all_passed": False, "status": "REJECTED_FOR_TEST"})
        buf_fail = io.StringIO()
        with (
            mock.patch.object(fx3_cli, "run_realhw_uart_460800_post_triage_and_isp_suite", return_value=failing),
            mock.patch.object(sys, "argv", ["fx3_recovery", "verify-uart-460800-isp-triage", "--clean-room", "--json"]),
            redirect_stdout(buf_fail),
        ):
            rc_fail = fx3_cli.main()
        self.assertEqual(rc_fail, 2)
        self.assertFalse(json.loads(buf_fail.getvalue())["all_passed"])

    def test_46_cli_verify_all_recovery_with_phase155_reaches_20_of_20_pillars(self) -> None:
        argv_20 = [
            "fx3_recovery",
            "verify-all-recovery",
            "--clean-room",
            "--with-phase94",
            "--with-phase101",
            "--with-phase106",
            "--with-phase113",
            "--with-phase119",
            "--with-phase124",
            "--with-phase126",
            "--with-phase134",
            "--with-phase138",
            "--with-phase139",
            "--with-phase144",
            "--with-phase151",
            "--with-phase155",
            "--json",
        ]
        buf = io.StringIO()
        with mock.patch.object(sys, "argv", argv_20), redirect_stdout(buf):
            rc = fx3_cli.main()
        self.assertEqual(rc, 0)
        parsed = json.loads(buf.getvalue())
        self.assertTrue(parsed["all_passed"])
        self.assertGreaterEqual(parsed["pillar_count"], 20)
        self.assertGreaterEqual(parsed["pillars_passed"], 20)
        self.assertEqual(parsed["pillars_passed"], parsed["pillar_count"])
        self.assertIn("phase155_pillar20_uart_460800_isp_triage", parsed)

        buf_txt = io.StringIO()
        with mock.patch.object(sys, "argv", argv_20[:-1]), redirect_stdout(buf_txt):
            rc_txt = fx3_cli.main()
        self.assertEqual(rc_txt, 0)
        self.assertIn("pillars=20/20", buf_txt.getvalue())

    def test_47_cli_verify_all_recovery_preserves_7_and_19_pillar_backward_compatibility(self) -> None:
        buf7 = io.StringIO()
        with (
            mock.patch.object(sys, "argv", ["fx3_recovery", "verify-all-recovery", "--clean-room", "--json"]),
            redirect_stdout(buf7),
        ):
            rc7 = fx3_cli.main()
        self.assertEqual(rc7, 0)
        p7 = json.loads(buf7.getvalue())
        self.assertEqual(p7["pillar_count"], 7)
        self.assertEqual(p7["pillars_passed"], 7)
        self.assertNotIn("phase155_pillar20_uart_460800_isp_triage", p7)

        buf19 = io.StringIO()
        with (
            mock.patch.object(
                sys,
                "argv",
                [
                    "fx3_recovery",
                    "verify-all-recovery",
                    "--clean-room",
                    "--with-phase94",
                    "--with-phase101",
                    "--with-phase106",
                    "--with-phase113",
                    "--with-phase119",
                    "--with-phase124",
                    "--with-phase126",
                    "--with-phase134",
                    "--with-phase138",
                    "--with-phase139",
                    "--with-phase144",
                    "--with-phase151",
                    "--json",
                ],
            ),
            redirect_stdout(buf19),
        ):
            rc19 = fx3_cli.main()
        self.assertEqual(rc19, 0)
        p19 = json.loads(buf19.getvalue())
        self.assertEqual(p19["pillar_count"], 19)
        self.assertEqual(p19["pillars_passed"], 19)
        self.assertNotIn("phase155_pillar20_uart_460800_isp_triage", p19)

    def test_48_verify_all_recovery_phase155_failure_propagates_nonzero_rc(self) -> None:
        rep = run_realhw_uart_460800_post_triage_and_isp_suite(force_clean_room=True)
        failing = type(rep)(**{**rep.__dict__, "all_passed": False, "status": "REJECTED_FOR_TEST"})
        buf = io.StringIO()
        with (
            mock.patch.object(fx3_cli, "run_realhw_uart_460800_post_triage_and_isp_suite", return_value=failing),
            mock.patch.object(
                sys,
                "argv",
                ["fx3_recovery", "verify-all-recovery", "--clean-room", "--with-phase155", "--json"],
            ),
            redirect_stdout(buf),
        ):
            rc = fx3_cli.main()
        self.assertEqual(rc, 2)
        parsed = json.loads(buf.getvalue())
        self.assertFalse(parsed["all_passed"])
        self.assertEqual(parsed["pillar_count"], 8)
        self.assertEqual(parsed["pillars_passed"], 7)


if __name__ == "__main__":
    unittest.main()
