"""Phase 310 (310th Phase Milestone, Wave-58, 136/136 Safety Gates) Dual-Mode Unit Tests (86 tests) for
`fx3_safety.realhw_bright_mon_shotmark_usblan_bulb_dormant_and_136gate_guard`:

- Gate `G135` (`GATE_G135_BRIGHT_MONITORING_FOCUS_MAG_MONITOR_BRIGHTNESS_VS_FX6_AND_SHOTMARK_CLIPFLAG_DIVIDER_SLOT1_VAULT_GUARD`):
  - `[Bright Monitoring]` (`_f.uxc 0x701f`) is custom-key-only on `ILME-FX3 Ver. 7.02`
    (not a shooting menu toggle, zero multi-step gain control), forces `[Live View Display] =
    Setting Effect OFF`, auto-cancels on power-off / leaving `P-A-S-M` / leaving `MF`, and
    explicitly permits `Ver. 7.00+/7.02` `[Focus Magnifier]` & `[Auto Magnifier in MF]`
    coexistence.
  - `[Monitor Brightness]` (`.uxc 0xe44b`) exposes ONLY `Manual` (`-2..+2`, default `0`) and
    `Sunny Weather` (`_f 0x6fd4`, `Initialize`-only, rejecting dormant `AUTO`/`BRIGHT`/`NORMAL`,
    zero 4K thermal LCD dimming lock) vs `ILME-FX6` `Monitoring > VF Setting > Brightness`
    (`1..15`) and `Shooting > Auto Exposure > Mode > Backlight` (AE mode, NOT LCD backlight).
  - Rejects dormant FX3 in-camera `[Divide]` / `[Extract]` and dormant FTP `15/30/60s`
    Shot-Mark Cut (`_f.uxc 0x7005/0x6e38/0x6c2a -> EOPNOTSUPP=95`), plus FX6 dormant
    `Shot Mark 0..9` / `Essence Mark`, while enforcing fail-closed `EROFS=30` / `EBUSY=16`
    blocking whenever `[Add/Delete Shot Mark1/2]`, Ver. 7.00+ `[Clip Flag]` (`OK`/`NG`/`KEEP`),
    `[Photo Capture]`, `[Create Divider Frame]` (`_f.uxc 0x747a`), or Playback `[Edit]`
    attempts to mutate `M4ROOT/CLIP/*M01.XML`, `DCIM/`, or `AVF_INFO` on a `Slot-1` Tier-0
    recovery vault across `384` matrix states.
- Gate `G136` (`GATE_G136_ZERO_BT_TCLINK_VS_VMC_BNCM1_FX6_BNC_WIFI_WPA3_USBLAN_ZERORF_AND_DORMANT_BULB_TIMER_AUTOHDR_GUARD`):
  - Rejects Bluetooth `[Timecode Link]` / `UltraSync BLUE` on FX3 `Ver. 7.02` (`0` `tc_link`
    symbols -> `EOPNOTSUPP=95`); FX3 supports ONLY wired `Multi/Micro USB` `VMC-BNCM1` LTC input
    (`Time Code Make=Preset` + `Time Code Run=Free Run` -> `EXT-LK`) + HDMI `TC Out` vs FX6
    physical `TC IN/OUT` BNC switch & zero-BT hardware.
  - Validates FX3 `Ver. 7.00+` `WPA2-PSK`/`WPA3-SAE` + `Access Authen. Settings=On` (rejecting
    removed legacy `WEP`/`WPA-PSK`/`IPsec`), `WW728473` (`2.4/5GHz`) vs `WW558244` (`2.4GHz`-only)
    SKU truth, `USB-LAN` kernel stack (`cdc_ncm.ko`, `r8152.ko`, `asix.ko`, `ax88179_178a.ko` +
    `Ver. 7.00+` `[USB-LAN Cnct. Launch]` `_f.uxc 0x7d2a`; mutual exclusion with `Multi/Micro USB`
    & `Wi-Fi`), and mandatory `[Airplane Mode] = On` zero-RF lock (surviving BOTH `Reset Network
    Set.` & `Initialize` while permitting authorized air-gapped wired `eth0`).
  - Rejects dormant `[Bulb Timer]` (`BKID_APP_setting_bulb_timer` / `_f.uxc 0x630f -> EOPNOTSUPP=95`)
    and dormant `[Auto HDR]` (`.uxc 0xe49d -> EOPNOTSUPP=95`), while enforcing Still `[BULB]`
    mechanical-shutter-only rule (blocked/clamped to `30"` under `Electronic Shutter`,
    `Cont. Shooting`, `Cont. Bracket`, `Self-timer(Cont)`, and `Interval Shooting`) and active
    `DRO` / `DRO Bracket` locks under `Picture Profile != Off` or `HLG Still Image = On` across
    `384` matrix states.
- Unified `136`-Gate Milestone Master Preflight (`evaluate_136gate_preflight` / `verify-136-gates`):
  - `133/136` offline and `136/136` under `--simulate-bench-dry-run` with all hardware
    write/attach redlines hard-locked `False`.
"""

from __future__ import annotations

import contextlib
import dataclasses
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

import fx3_safety
from fx3_safety.__main__ import main as cli_main
from fx3_safety.realhw_steadyshot_selftimer_zebra_streaming_and_134gate_guard import (
    Master134GateReport,
    STATUS_BLOCKED_G134_SLOT1_TIER0_VAULT_WRITE_FIREWALL_VIOLATION,
)
from fx3_safety.realhw_bright_mon_shotmark_usblan_bulb_dormant_and_136gate_guard import (
    ACTIVE_PB_EDIT_ITEMS_G135,
    ALLOWED_CARD_OPS_G135,
    ALLOWED_CLIP_FLAG_VALUES_G135,
    ALLOWED_DRO_BRACKET_MODES_G136,
    ALLOWED_DRO_MODES_G136,
    ALLOWED_FX3_SKUS_G136,
    ALLOWED_IMAGE_JUMP_SETTINGS_G135,
    ALLOWED_MONITOR_BRIGHTNESS_MODES_G135,
    ALLOWED_PASM_MODES_G135,
    ALLOWED_SHUTTER_TYPES_G136,
    ALLOWED_STILL_DRIVE_MODES_G136,
    ALLOWED_WIFI_BANDS_G136,
    ALLOWED_WIFI_SECURITIES_G136,
    BRIGHT_MONITORING_F_UXC_RESID16_G135,
    BRIGHT_MONITORING_KEY_PATH_G135,
    CARD_OP_ADD_DELETE_SHOT_MARK_1_G135,
    CARD_OP_ADD_DELETE_SHOT_MARK_2_G135,
    CARD_OP_ADD_SHOT_MARK_1_G135,
    CARD_OP_ADD_SHOT_MARK_2_G135,
    CARD_OP_CREATE_DIVIDER_FRAME_G135,
    CARD_OP_JUMP_READONLY_G135,
    CARD_OP_NONE_G135,
    CARD_OP_PB_EDIT_G135,
    CARD_OP_PHOTO_CAPTURE_G135,
    CARD_OP_SET_CLIP_FLAG_G135,
    CREATE_DIVIDER_FRAME_F_UXC_RESID16_G135,
    CREATE_DIVIDER_FRAME_G_UXC_RESID16_G135,
    CROSS_MODEL_FLASH_AUTHORIZED,
    DEFAULT_REPO_ROOT,
    DONOR_CHECK_CI_MAX_SECONDS_PHASE310,
    DONOR_CHECK_MAX_SECONDS_PHASE310,
    DORMANT_AUTO_HDR_TRAPS_G136,
    DORMANT_BULB_TIMER_TRAPS_G136,
    DORMANT_MONITOR_BRIGHTNESS_MODES_G135,
    DORMANT_SHOTMARK_DIVIDE_TRAPS_G135,
    DORMANT_TC_LINK_TRAPS_G136,
    DRO_AUTO_G136,
    DRO_OFF_G136,
    EBUSY_ERRNO_PHASE310,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    ENV_CLEAN_ROOM_TEST_PHASE310,
    ENV_FORCE_CLEAN_ROOM,
    EOPNOTSUPP_ERRNO_PHASE310,
    EROFS_ERRNO_PHASE310,
    EXPOSURE_MODE_A_G135,
    EXPOSURE_MODE_INTELLIGENT_AUTO_G135,
    EXPOSURE_MODE_M_G135,
    EXPOSURE_MODE_P_G135,
    EXPOSURE_MODE_S_G135,
    FOCUS_MODE_AF_C_G135,
    FOCUS_MODE_AF_S_G135,
    FOCUS_MODE_DMF_G135,
    FOCUS_MODE_MF_G135,
    FX3_DEFAULT_FW_VERSION_PHASE310,
    FX3_HELP_GUIDE_CODE_PHASE310,
    FX3_MODEL_ID_PHASE310,
    FX3_MODEL_NAME_PHASE310,
    FX3_SKU_WW558244_G136,
    FX3_SKU_WW728473_G136,
    FX3_WIRED_TC_CABLE_G136,
    FX6_AE_BACKLIGHT_SYMBOL_G135,
    FX6_DORMANT_BACKLIGHT_SYMBOLS_G135,
    FX6_MODEL_NAME_PHASE310,
    FX6_VF_BRIGHTNESS_DEFAULT_G135,
    FX6_VF_BRIGHTNESS_MAX_G135,
    FX6_VF_BRIGHTNESS_MIN_G135,
    FX6_VF_SETTING_MENU_PATH_G135,
    G135,
    G135_GATE_CODE,
    G135_GATE_ID,
    G136,
    G136_GATE_CODE,
    G136_GATE_ID,
    HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    HUMAN_HARDWARE_ATTACH_TOKEN,
    LIVE_VIEW_DISPLAY_EFFECT_OFF_G135,
    LIVE_VIEW_DISPLAY_EFFECT_ON_G135,
    MEDIA_SLOT_1_PHASE310,
    MEDIA_SLOT_2_PHASE310,
    MONITOR_BRIGHTNESS_MANUAL_G135,
    MONITOR_BRIGHTNESS_MENU_PATH_G135,
    MONITOR_BRIGHTNESS_SUNNY_WEATHER_G135,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED,
    PHYSICAL_USB_PACKETS_EMITTED,
    PINNED_FX3_APPFW_SLICES_PHASE310,
    PINNED_FX6_APPFW_SLICES_PHASE310,
    PINNED_PHASE310_DONOR_SPECS,
    RAW_FIRMWARE_BYTES_LEAKED,
    REALHW_BRIGHT_MON_SHOTMARK_USBLAN_BULB_DORMANT_136GATE_SCHEMA,
    REMOVED_LEGACY_WIFI_SECURITIES_G136,
    RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE310,
    RESET_ACTION_INITIALIZE_PHASE310,
    RESET_ACTION_NONE_PHASE310,
    RESET_ACTION_RESET_NETWORK_SET_PHASE310,
    SHOOT_MODE_MOVIE_PHASE310,
    SHOOT_MODE_SQ_PHASE310,
    SHOOT_MODE_STILL_PHASE310,
    SHUTTER_TYPE_AUTO_G136,
    SHUTTER_TYPE_ELECTRONIC_G136,
    SHUTTER_TYPE_MECHANICAL_G136,
    SPI_NOR_WRITE_AUTHORIZED,
    STATUS_BLOCKED_G135_BRIGHT_MONITORING_CUSTOM_KEY_OR_MAG_VIOLATION,
    STATUS_BLOCKED_G135_DORMANT_DIVIDE_EXTRACT_OR_FTP_CUT_VIOLATION,
    STATUS_BLOCKED_G135_MONITOR_BRIGHTNESS_OR_FX6_BACKLIGHT_VIOLATION,
    STATUS_BLOCKED_G135_SLOT1_TIER0_VAULT_WRITE_FIREWALL_VIOLATION,
    STATUS_BLOCKED_G135_TELEMETRY_INVALID,
    STATUS_BLOCKED_G136_AIRPLANE_ZERO_RF_FIREWALL_VIOLATION,
    STATUS_BLOCKED_G136_DORMANT_BT_TCLINK_OR_FX6_TC_VIOLATION,
    STATUS_BLOCKED_G136_DORMANT_BULB_TIMER_OR_AUTO_HDR_VIOLATION,
    STATUS_BLOCKED_G136_STILL_BULB_MECHANICAL_OR_DRO_LOCK_VIOLATION,
    STATUS_BLOCKED_G136_TELEMETRY_INVALID,
    STATUS_BLOCKED_G136_WIFI_WPA_LEGACY_SKU_OR_USBLAN_EXCLUSION_VIOLATION,
    STATUS_BLOCKED_PERSISTENT_EMMC_WRITE,
    STATUS_BLOCKED_PHASE310_DONOR_INTEGRITY,
    STATUS_VERIFIED_G135,
    STATUS_VERIFIED_G136,
    STATUS_VERIFIED_SAFE,
    STILL_DRIVE_CONT_BRACKET_G136,
    STILL_DRIVE_CONT_SHOOTING_G136,
    STILL_DRIVE_DRO_BRACKET_G136,
    STILL_DRIVE_SELF_TIMER_CONT_G136,
    STILL_DRIVE_SELF_TIMER_SINGLE_G136,
    STILL_DRIVE_SINGLE_BRACKET_G136,
    STILL_DRIVE_SINGLE_G136,
    USB_LAN_CNCT_LAUNCH_F_UXC_RESID16_G136,
    USB_LAN_KERNEL_MODULES_G136,
    USB_PACKETS_TRANSMITTED,
    WIFI_BAND_2_4GHZ_G136,
    WIFI_BAND_5GHZ_G136,
    WIFI_SEC_WPA2_PSK_G136,
    WIFI_SEC_WPA3_SAE_G136,
    audit_phase310_donor_contracts,
    compute_bright_mon_shotmark_vault_matrix,
    compute_tc_link_wifi_usblan_bulb_dormant_matrix,
    evaluate_136_master_safety_gates,
    evaluate_136gate_preflight,
    evaluate_g135_bright_mon_shotmark_vault_guard,
    evaluate_g136_tc_link_wifi_usblan_bulb_dormant_guard,
    main as module_main,
    resolve_fx3_bright_mon_shotmark_vault_state,
    resolve_fx3_tc_link_wifi_usblan_bulb_dormant_state,
    run_136_gate_preflight,
    verify_bright_mon_shotmark_vault_guard,
    verify_tc_link_wifi_usblan_bulb_dormant_guard,
)


def _make_stub_master134(
    *, dry_run: bool = False, all_g13_134_ok: bool = True
) -> Master134GateReport:
    gates = []
    for i in range(1, 135):
        gid = f"G{i:02d}"
        is_tier0_offline = gid in ("G10", "G11", "G12") and not dry_run
        passed = (not is_tier0_offline) and (all_g13_134_ok or i <= 12)
        gates.append(
            {
                "gate_id": gid,
                "gate_code": f"STUB_{gid}",
                "status": "STATUS_VERIFIED_SAFE" if passed else "PENDING_PHYSICAL_TIER0",
                "passed": passed,
                "evidence": "stub",
                "violation_codes": [],
            }
        )
    g01_12 = 12 if dry_run else 9
    g13_132 = 120 if all_g13_134_ok else 0
    g133_134 = 2 if all_g13_134_ok else 0
    total = g01_12 + g13_132 + g133_134
    return Master134GateReport(
        schema="stub_134",
        version="2026.11.17",
        evaluated_utc="2026-11-17T00:00:00Z",
        verification_mode="CLEAN_ROOM_SYNTHETIC",
        clean_room_forced=True,
        dry_run_rehearsal_only=dry_run,
        overall_ready_for_hardware_attach=False,
        hardware_live_attachment_authorized=False,
        offline_131_gates_verified=all_g13_134_ok,
        all_134_gates_verified=(dry_run and all_g13_134_ok),
        g13_to_g134_all_passed=all_g13_134_ok,
        g133_to_g134_all_passed=all_g13_134_ok,
        h0_h1_trial_entry_allowed=all_g13_134_ok,
        status=(
            "VERIFIED_ALL_134_GATES_DRY_RUN_SIMULATED_BACKUP"
            if dry_run
            else "VERIFIED_131_OF_134_AWAITING_PHYSICAL_TIER0"
        ),
        agent_auto_flash_blocked=True,
        human_hardware_attach_token=False,
        el3_payload_transmit_authorized=False,
        spi_nor_write_authorized=False,
        persistent_emmc_writes_authorized=False,
        persistent_write_release=False,
        physical_flash_auto_exec_authorized=False,
        cross_model_flash_authorized=False,
        usb_packets_transmitted=0,
        physical_usb_packets_emitted=0,
        raw_firmware_bytes_leaked=0,
        technical_gates_passed=total,
        summary={
            "g01_to_g12_verified": g01_12,
            "g13_to_g132_verified": g13_132,
            "g133_to_g134_verified": g133_134,
            "verified_gates": total,
        },
        gates=tuple(gates),
        master_132_report={},
        g133_result={},
        g134_result={},
        errors=(),
        warnings=(),
    )


class TestPackageExportsAndDonorAuditPhase310(unittest.TestCase):
    def test_01_package_exports_phase310_symbols(self) -> None:
        self.assertIs(fx3_safety.evaluate_136gate_preflight, evaluate_136gate_preflight)
        self.assertIs(
            fx3_safety.evaluate_g135_bright_mon_shotmark_vault_guard,
            evaluate_g135_bright_mon_shotmark_vault_guard,
        )
        self.assertIs(
            fx3_safety.evaluate_g136_tc_link_wifi_usblan_bulb_dormant_guard,
            evaluate_g136_tc_link_wifi_usblan_bulb_dormant_guard,
        )
        self.assertEqual(fx3_safety.G135, "G135")
        self.assertEqual(fx3_safety.G136, "G136")
        self.assertIn("evaluate_136gate_preflight", fx3_safety.__all__)
        self.assertIn("evaluate_g135_bright_mon_shotmark_vault_guard", fx3_safety.__all__)
        self.assertIn("evaluate_g136_tc_link_wifi_usblan_bulb_dormant_guard", fx3_safety.__all__)

    def test_02_immutable_redlines_hard_locked_false_and_zero(self) -> None:
        self.assertFalse(EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        self.assertFalse(SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(PERSISTENT_WRITE_RELEASE)
        self.assertFalse(PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED)
        self.assertFalse(HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        self.assertFalse(HUMAN_HARDWARE_ATTACH_TOKEN)
        self.assertFalse(CROSS_MODEL_FLASH_AUTHORIZED)
        self.assertEqual(USB_PACKETS_TRANSMITTED, 0)
        self.assertEqual(PHYSICAL_USB_PACKETS_EMITTED, 0)
        self.assertEqual(RAW_FIRMWARE_BYTES_LEAKED, 0)

    def test_03_frozen_dataclasses_and_schema_constants(self) -> None:
        self.assertEqual(
            REALHW_BRIGHT_MON_SHOTMARK_USBLAN_BULB_DORMANT_136GATE_SCHEMA,
            "realhw_bright_mon_shotmark_usblan_bulb_dormant_and_136gate_guard_v1",
        )
        res = verify_bright_mon_shotmark_vault_guard()
        with self.assertRaises(dataclasses.FrozenInstanceError):
            res.valid = False  # type: ignore[misc]
        res2 = verify_tc_link_wifi_usblan_bulb_dormant_guard()
        with self.assertRaises(dataclasses.FrozenInstanceError):
            res2.valid = False  # type: ignore[misc]

    def test_04_donor_audit_clean_room_forced_under_budget(self) -> None:
        t0 = time.perf_counter()
        audit = audit_phase310_donor_contracts(force_clean_room=True)
        dt = time.perf_counter() - t0
        self.assertTrue(audit.valid)
        self.assertEqual(audit.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(audit.access_mode, "SYNTHETIC_NO_DONOR_TOUCH")
        self.assertEqual(audit.files_inspected, 0)
        self.assertEqual(audit.raw_firmware_bytes_leaked, 0)
        self.assertTrue(audit.fx3_contracts_verified)
        self.assertTrue(audit.fx6_contracts_verified)
        self.assertTrue(audit.four_lang_resid16_parity_verified)
        self.assertTrue(audit.usblan_kmod_stack_verified)
        budget = (
            DONOR_CHECK_CI_MAX_SECONDS_PHASE310 + 15.0
            if os.environ.get("GITHUB_ACTIONS") == "true"
            else DONOR_CHECK_MAX_SECONDS_PHASE310
        )
        self.assertLessEqual(dt, budget)

    def test_05_donor_audit_env_fx3_clean_room_test_1(self) -> None:
        with mock.patch.dict(os.environ, {ENV_CLEAN_ROOM_TEST_PHASE310: "1"}):
            audit = audit_phase310_donor_contracts()
            self.assertTrue(audit.valid)
            self.assertEqual(audit.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_06_donor_audit_env_fx3_fx6_force_clean_room_1(self) -> None:
        with mock.patch.dict(os.environ, {ENV_FORCE_CLEAN_ROOM: "1"}):
            audit = audit_phase310_donor_contracts()
            self.assertTrue(audit.valid)
            self.assertEqual(audit.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_07_donor_audit_absent_donor_fallback_clean_room(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            fake_paths = mock.Mock()
            fake_paths.work_root = Path(td)
            with mock.patch(
                "fx3_safety.realhw_bright_mon_shotmark_usblan_bulb_dormant_and_136gate_guard.resolve_donor_thermal_power_paths",
                return_value=fake_paths,
            ):
                audit = audit_phase310_donor_contracts(
                    repo_root=Path(td),
                    force_clean_room=False,
                )
            self.assertTrue(audit.valid)
            self.assertEqual(audit.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertEqual(audit.access_mode, "SYNTHETIC_ABSENT_DONOR_FALLBACK")

    def test_08_donor_audit_real_o_rdonly_or_clean_room_dual_mode(self) -> None:
        t0 = time.perf_counter()
        audit = audit_phase310_donor_contracts(repo_root=DEFAULT_REPO_ROOT)
        dt = time.perf_counter() - t0
        self.assertTrue(audit.valid)
        self.assertEqual(audit.raw_firmware_bytes_leaked, 0)
        self.assertTrue(audit.fx3_contracts_verified)
        self.assertTrue(audit.fx6_contracts_verified)
        self.assertTrue(audit.four_lang_resid16_parity_verified)
        self.assertTrue(audit.usblan_kmod_stack_verified)
        budget = (
            DONOR_CHECK_CI_MAX_SECONDS_PHASE310 + 15.0
            if os.environ.get("GITHUB_ACTIONS") == "true"
            else 5.0
        )
        self.assertLessEqual(dt, budget)
        if audit.verification_mode == "LOCAL_DONOR_O_RDONLY":
            self.assertEqual(audit.files_inspected, 18)
            self.assertEqual(len(audit.checked_markers), 18)
            self.assertEqual(len(PINNED_FX3_APPFW_SLICES_PHASE310), 27)
            self.assertEqual(len(PINNED_FX6_APPFW_SLICES_PHASE310), 13)

    def test_09_donor_audit_detects_missing_or_tampered_file_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            fake_root = Path(td)
            sample = fake_root / "fake.uxc"
            sample.write_bytes(b"TAMPERED_CONTENT")
            bad_specs = {
                "fx3_fake": (
                    "FX3",
                    "fake.uxc",
                    999,
                    "0" * 64,
                    (b"EXPECTED_TOKEN",),
                    "Tamper test",
                )
            }
            audit = audit_phase310_donor_contracts(
                work_root=fake_root,
                force_clean_room=False,
                donor_specs_override=bad_specs,
            )
            self.assertFalse(audit.valid)
            self.assertEqual(audit.status, STATUS_BLOCKED_PHASE310_DONOR_INTEGRITY)
            self.assertGreaterEqual(len(audit.missing_markers), 3)

    def test_10_donor_specs_contain_all_18_wave58_artifacts(self) -> None:
        expected_keys = {
            "fx3_appfw_so",
            "fx3_string_english_f_uxc",
            "fx3_string_simplifiedchinese_f_uxc",
            "fx3_string_traditionalchinese_f_uxc",
            "fx3_string_japanese_f_uxc",
            "fx3_string_english_uxc",
            "fx3_string_english_g_uxc",
            "fx3_bk4_bin",
            "fx3_cdc_ncm_ko",
            "fx3_r8152_ko",
            "fx3_asix_ko",
            "fx3_ax88179_ko",
            "fx3_lib_wired_lan",
            "fx3_lib_wlan",
            "fx3_lib_airplane",
            "fx6_appfw_so",
            "fx6_string_english_uxc",
            "fx6_string_english_2_uxc",
        }
        self.assertEqual(set(PINNED_PHASE310_DONOR_SPECS.keys()), expected_keys)


class TestGateG135BrightMonitoringMonitorBrightnessShotMarkVaultGuard(unittest.TestCase):
    def test_11_g135_default_nominal_fx3_passes(self) -> None:
        res = verify_bright_mon_shotmark_vault_guard()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_VERIFIED_G135)
        self.assertEqual(res.bright_monitoring_key_path, BRIGHT_MONITORING_KEY_PATH_G135)
        self.assertTrue(res.bright_monitoring_custom_key_only)
        self.assertFalse(res.effective_bright_monitoring_active)
        self.assertEqual(res.monitor_brightness_menu_path, MONITOR_BRIGHTNESS_MENU_PATH_G135)
        self.assertEqual(res.effective_monitor_brightness_mode, MONITOR_BRIGHTNESS_MANUAL_G135)
        self.assertEqual(res.effective_monitor_brightness_level, 0)
        self.assertEqual(res.fx6_vf_setting_menu_path, FX6_VF_SETTING_MENU_PATH_G135)
        self.assertEqual(res.fx6_vf_brightness, FX6_VF_BRIGHTNESS_DEFAULT_G135)
        self.assertTrue(res.fx6_ae_backlight_is_ae_only)
        self.assertEqual(res.active_pb_edit_items, ACTIVE_PB_EDIT_ITEMS_G135)

    def test_12_g135_bright_monitoring_active_in_pasm_mf_forces_setting_effect_off(self) -> None:
        for exp in ALLOWED_PASM_MODES_G135:
            res = verify_bright_mon_shotmark_vault_guard(
                shoot_mode=SHOOT_MODE_STILL_PHASE310,
                exposure_mode=exp,
                focus_mode=FOCUS_MODE_MF_G135,
                requested_bright_monitoring_active=True,
                requested_live_view_display=LIVE_VIEW_DISPLAY_EFFECT_ON_G135,
            )
            self.assertTrue(res.valid)
            self.assertTrue(res.effective_bright_monitoring_active)
            self.assertFalse(res.bright_monitoring_auto_cancelled)
            self.assertEqual(res.effective_live_view_display, LIVE_VIEW_DISPLAY_EFFECT_OFF_G135)

    def test_13_g135_bright_monitoring_movie_sq_pasm_mf_also_supported(self) -> None:
        for sm in (SHOOT_MODE_MOVIE_PHASE310, SHOOT_MODE_SQ_PHASE310):
            res = verify_bright_mon_shotmark_vault_guard(
                shoot_mode=sm,
                exposure_mode=EXPOSURE_MODE_M_G135,
                focus_mode=FOCUS_MODE_MF_G135,
                requested_bright_monitoring_active=True,
            )
            self.assertTrue(res.valid)
            self.assertTrue(res.effective_bright_monitoring_active)
            self.assertEqual(res.effective_live_view_display, LIVE_VIEW_DISPLAY_EFFECT_OFF_G135)

    def test_14_g135_bright_monitoring_rejects_menu_toggle_and_multistep_gain(self) -> None:
        bad_menu = verify_bright_mon_shotmark_vault_guard(
            bright_monitoring_menu_toggle_claimed=True,
        )
        self.assertFalse(bad_menu.valid)
        self.assertEqual(bad_menu.block_errno, EOPNOTSUPP_ERRNO_PHASE310)
        self.assertIn(
            STATUS_BLOCKED_G135_BRIGHT_MONITORING_CUSTOM_KEY_OR_MAG_VIOLATION,
            bad_menu.violation_codes,
        )

        bad_gain = verify_bright_mon_shotmark_vault_guard(
            bright_monitoring_multi_step_gain_claimed=True,
        )
        self.assertFalse(bad_gain.valid)
        self.assertEqual(bad_gain.block_errno, EOPNOTSUPP_ERRNO_PHASE310)
        self.assertIn(
            STATUS_BLOCKED_G135_BRIGHT_MONITORING_CUSTOM_KEY_OR_MAG_VIOLATION,
            bad_gain.violation_codes,
        )

    def test_15_g135_bright_monitoring_auto_cancels_on_power_off_auto_or_af(self) -> None:
        res_pwr = verify_bright_mon_shotmark_vault_guard(
            power_off=True,
            requested_bright_monitoring_active=True,
        )
        self.assertTrue(res_pwr.valid)
        self.assertFalse(res_pwr.effective_bright_monitoring_active)
        self.assertTrue(res_pwr.bright_monitoring_auto_cancelled)
        self.assertIn("power_off", res_pwr.bright_monitoring_auto_cancel_reasons)

        res_iauto = verify_bright_mon_shotmark_vault_guard(
            exposure_mode=EXPOSURE_MODE_INTELLIGENT_AUTO_G135,
            focus_mode=FOCUS_MODE_MF_G135,
            requested_bright_monitoring_active=True,
        )
        self.assertTrue(res_iauto.valid)
        self.assertFalse(res_iauto.effective_bright_monitoring_active)
        self.assertTrue(res_iauto.bright_monitoring_auto_cancelled)
        self.assertTrue(any("left P/A/S/M" in r for r in res_iauto.bright_monitoring_auto_cancel_reasons))

        for af in (FOCUS_MODE_AF_S_G135, FOCUS_MODE_AF_C_G135, FOCUS_MODE_DMF_G135):
            res_af = verify_bright_mon_shotmark_vault_guard(
                exposure_mode=EXPOSURE_MODE_M_G135,
                focus_mode=af,
                requested_bright_monitoring_active=True,
            )
            self.assertTrue(res_af.valid)
            self.assertFalse(res_af.effective_bright_monitoring_active)
            self.assertTrue(res_af.bright_monitoring_auto_cancelled)
            self.assertTrue(any("left MF" in r for r in res_af.bright_monitoring_auto_cancel_reasons))

        bad_persist = verify_bright_mon_shotmark_vault_guard(
            power_off=True,
            requested_bright_monitoring_active=True,
            claimed_bright_mon_persists_across_power_or_af_or_auto=True,
        )
        self.assertFalse(bad_persist.valid)
        self.assertIn(
            STATUS_BLOCKED_G135_BRIGHT_MONITORING_CUSTOM_KEY_OR_MAG_VIOLATION,
            bad_persist.violation_codes,
        )

    def test_16_g135_v700_focus_magnifier_and_auto_magnifier_coexist_with_bright_monitoring(self) -> None:
        res = verify_bright_mon_shotmark_vault_guard(
            exposure_mode=EXPOSURE_MODE_M_G135,
            focus_mode=FOCUS_MODE_MF_G135,
            requested_bright_monitoring_active=True,
            focus_magnifier_active=True,
            auto_magnifier_in_mf=True,
        )
        self.assertTrue(res.valid)
        self.assertTrue(res.effective_bright_monitoring_active)
        self.assertTrue(res.focus_magnifier_coexists_with_bright_monitoring)

        bad_v7_conflict = verify_bright_mon_shotmark_vault_guard(
            requested_bright_monitoring_active=True,
            focus_magnifier_active=True,
            claimed_focus_magnifier_blocked_in_v7=True,
        )
        self.assertFalse(bad_v7_conflict.valid)
        self.assertIn(
            STATUS_BLOCKED_G135_BRIGHT_MONITORING_CUSTOM_KEY_OR_MAG_VIOLATION,
            bad_v7_conflict.violation_codes,
        )

    def test_17_g135_monitor_brightness_manual_minus2_to_plus2_and_sunny_weather(self) -> None:
        for lvl in range(-2, 3):
            res = verify_bright_mon_shotmark_vault_guard(
                requested_monitor_brightness_mode=MONITOR_BRIGHTNESS_MANUAL_G135,
                requested_monitor_brightness_level=lvl,
            )
            self.assertTrue(res.valid)
            self.assertEqual(res.effective_monitor_brightness_mode, MONITOR_BRIGHTNESS_MANUAL_G135)
            self.assertEqual(res.effective_monitor_brightness_level, lvl)

        sunny = verify_bright_mon_shotmark_vault_guard(
            requested_monitor_brightness_mode=MONITOR_BRIGHTNESS_SUNNY_WEATHER_G135,
        )
        self.assertTrue(sunny.valid)
        self.assertEqual(sunny.effective_monitor_brightness_mode, MONITOR_BRIGHTNESS_SUNNY_WEATHER_G135)

        for bad_val in (3, -3):
            bad_lvl = verify_bright_mon_shotmark_vault_guard(
                requested_monitor_brightness_mode=MONITOR_BRIGHTNESS_MANUAL_G135,
                requested_monitor_brightness_level=bad_val,
            )
            self.assertFalse(bad_lvl.valid)
            self.assertIn(
                STATUS_BLOCKED_G135_MONITOR_BRIGHTNESS_OR_FX6_BACKLIGHT_VIOLATION,
                bad_lvl.violation_codes,
            )

    def test_18_g135_monitor_brightness_rejects_dormant_auto_bright_normal(self) -> None:
        for dormant in DORMANT_MONITOR_BRIGHTNESS_MODES_G135:
            bad = verify_bright_mon_shotmark_vault_guard(
                requested_monitor_brightness_mode=dormant,
            )
            self.assertFalse(bad.valid)
            self.assertEqual(bad.block_errno, EOPNOTSUPP_ERRNO_PHASE310)
            self.assertIn(
                STATUS_BLOCKED_G135_MONITOR_BRIGHTNESS_OR_FX6_BACKLIGHT_VIOLATION,
                bad.violation_codes,
            )

    def test_19_g135_monitor_brightness_initialize_only_and_no_4k_lcd_dimming_lock(self) -> None:
        cam_rst = verify_bright_mon_shotmark_vault_guard(
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE310,
            requested_monitor_brightness_mode=MONITOR_BRIGHTNESS_SUNNY_WEATHER_G135,
        )
        self.assertTrue(cam_rst.valid)
        self.assertTrue(cam_rst.monitor_brightness_survived_cam_reset)
        self.assertEqual(
            cam_rst.effective_monitor_brightness_mode,
            MONITOR_BRIGHTNESS_SUNNY_WEATHER_G135,
        )

        init_rst = verify_bright_mon_shotmark_vault_guard(
            reset_action=RESET_ACTION_INITIALIZE_PHASE310,
            requested_monitor_brightness_mode=MONITOR_BRIGHTNESS_SUNNY_WEATHER_G135,
        )
        self.assertTrue(init_rst.valid)
        self.assertEqual(init_rst.effective_monitor_brightness_mode, MONITOR_BRIGHTNESS_MANUAL_G135)
        self.assertEqual(init_rst.effective_monitor_brightness_level, 0)

        bad_cam_rst = verify_bright_mon_shotmark_vault_guard(
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE310,
            claimed_monitor_brightness_resets_on_cam_reset=True,
        )
        self.assertFalse(bad_cam_rst.valid)
        self.assertIn(
            STATUS_BLOCKED_G135_MONITOR_BRIGHTNESS_OR_FX6_BACKLIGHT_VIOLATION,
            bad_cam_rst.violation_codes,
        )

        bad_dim = verify_bright_mon_shotmark_vault_guard(
            claimed_fx3_4k_thermal_lcd_dimming_lock=True,
        )
        self.assertFalse(bad_dim.valid)
        self.assertIn(
            STATUS_BLOCKED_G135_MONITOR_BRIGHTNESS_OR_FX6_BACKLIGHT_VIOLATION,
            bad_dim.violation_codes,
        )

    def test_20_g135_fx6_vf_setting_1_15_and_ae_backlight_vs_dormant_lcd_backlight(self) -> None:
        ok = verify_bright_mon_shotmark_vault_guard(
            fx6_vf_brightness=FX6_VF_BRIGHTNESS_MAX_G135,
            fx6_vf_color_mode="B&W",
        )
        self.assertTrue(ok.valid)
        self.assertEqual(ok.fx6_vf_brightness, 15)
        self.assertEqual(ok.fx6_vf_color_mode, "B&W")

        for bad_kw in (
            {"fx6_vf_brightness": 0},
            {"fx6_vf_brightness": 16},
            {"claimed_fx6_ae_backlight_is_lcd_backlight": True},
            {"claimed_fx6_lcd_vf_backlight_or_nightshot_active": True},
        ):
            bad = verify_bright_mon_shotmark_vault_guard(**bad_kw)  # type: ignore[arg-type]
            self.assertFalse(bad.valid)
            self.assertIn(
                STATUS_BLOCKED_G135_MONITOR_BRIGHTNESS_OR_FX6_BACKLIGHT_VIOLATION,
                bad.violation_codes,
            )

        self.assertEqual(FX6_AE_BACKLIGHT_SYMBOL_G135, "VAL_setting_auto_exposure_mode_MODE_BACKLIGHT")
        self.assertIn("NIGHTSHOT_ON", FX6_DORMANT_BACKLIGHT_SYMBOLS_G135)

    def test_21_g135_rejects_dormant_fx3_divide_extract_ftp_cut_and_fx6_shot_mark0_9(self) -> None:
        bad_flag = verify_bright_mon_shotmark_vault_guard(
            dormant_divide_extract_or_ftp_cut_requested=True,
        )
        self.assertFalse(bad_flag.valid)
        self.assertTrue(bad_flag.dormant_divide_extract_or_ftp_cut_blocked)
        self.assertEqual(bad_flag.block_errno, EOPNOTSUPP_ERRNO_PHASE310)
        self.assertIn(
            STATUS_BLOCKED_G135_DORMANT_DIVIDE_EXTRACT_OR_FTP_CUT_VIOLATION,
            bad_flag.violation_codes,
        )

        for trap in DORMANT_SHOTMARK_DIVIDE_TRAPS_G135:
            bad_sym = verify_bright_mon_shotmark_vault_guard(
                requested_dormant_shotmark_symbol=trap,
            )
            self.assertFalse(bad_sym.valid)
            self.assertEqual(bad_sym.block_errno, EOPNOTSUPP_ERRNO_PHASE310)

        bad_fx6 = verify_bright_mon_shotmark_vault_guard(
            claimed_fx6_has_divide_or_shot_mark0_9=True,
        )
        self.assertFalse(bad_fx6.valid)
        self.assertIn(
            STATUS_BLOCKED_G135_DORMANT_DIVIDE_EXTRACT_OR_FTP_CUT_VIOLATION,
            bad_fx6.violation_codes,
        )

    def test_22_g135_slot1_tier0_vault_blocks_all_mutating_card_ops_erofs_30(self) -> None:
        mutating_ops = (
            CARD_OP_ADD_SHOT_MARK_1_G135,
            CARD_OP_ADD_SHOT_MARK_2_G135,
            CARD_OP_ADD_DELETE_SHOT_MARK_1_G135,
            CARD_OP_ADD_DELETE_SHOT_MARK_2_G135,
            CARD_OP_SET_CLIP_FLAG_G135,
            CARD_OP_PHOTO_CAPTURE_G135,
            CARD_OP_CREATE_DIVIDER_FRAME_G135,
            CARD_OP_PB_EDIT_G135,
        )
        for op in mutating_ops:
            bad = verify_bright_mon_shotmark_vault_guard(
                requested_card_op=op,
                requested_clip_flag="OK" if op == CARD_OP_SET_CLIP_FLAG_G135 else "Off",
                requested_target_slot=MEDIA_SLOT_1_PHASE310,
                slot_1_contains_tier0_vault=True,
            )
            self.assertFalse(bad.valid, msg=f"op={op} should fail on Slot-1 vault")
            self.assertTrue(bad.slot1_vault_firewall_blocked)
            self.assertEqual(bad.block_errno, EROFS_ERRNO_PHASE310)
            self.assertEqual(bad.block_errno_name, "EROFS")
            self.assertEqual(bad.slot1_data_sector_writes, 0)
            self.assertFalse(bad.slot1_m4root_xml_mutated)
            self.assertFalse(bad.slot1_dcim_mutated)
            self.assertFalse(bad.slot1_avf_info_mutated)
            self.assertIn(
                STATUS_BLOCKED_G135_SLOT1_TIER0_VAULT_WRITE_FIREWALL_VIOLATION,
                bad.violation_codes,
            )

    def test_23_g135_slot1_write_protected_blocks_with_ebusy_16(self) -> None:
        bad = verify_bright_mon_shotmark_vault_guard(
            requested_card_op=CARD_OP_CREATE_DIVIDER_FRAME_G135,
            requested_target_slot=MEDIA_SLOT_1_PHASE310,
            slot_1_contains_tier0_vault=False,
            slot_1_write_protected=True,
        )
        self.assertFalse(bad.valid)
        self.assertTrue(bad.slot1_vault_firewall_blocked)
        self.assertEqual(bad.block_errno, EBUSY_ERRNO_PHASE310)
        self.assertEqual(bad.block_errno_name, "EBUSY")
        self.assertEqual(bad.slot1_data_sector_writes, 0)

    def test_24_g135_readonly_jump_on_slot1_and_mutating_ops_on_slot2_allowed(self) -> None:
        ro = verify_bright_mon_shotmark_vault_guard(
            requested_card_op=CARD_OP_JUMP_READONLY_G135,
            requested_image_jump_setting="Shot Mark1 Only",
            requested_target_slot=MEDIA_SLOT_1_PHASE310,
            slot_1_contains_tier0_vault=True,
            slot_1_write_protected=True,
        )
        self.assertTrue(ro.valid)
        self.assertFalse(ro.slot1_vault_firewall_blocked)
        self.assertEqual(ro.slot1_data_sector_writes, 0)

        for op in (
            CARD_OP_ADD_DELETE_SHOT_MARK_1_G135,
            CARD_OP_SET_CLIP_FLAG_G135,
            CARD_OP_PHOTO_CAPTURE_G135,
            CARD_OP_CREATE_DIVIDER_FRAME_G135,
            CARD_OP_PB_EDIT_G135,
        ):
            ok = verify_bright_mon_shotmark_vault_guard(
                requested_card_op=op,
                requested_clip_flag="KEEP" if op == CARD_OP_SET_CLIP_FLAG_G135 else "Off",
                requested_photo_capture_file_type="HEIF 4:2:0",
                requested_target_slot=MEDIA_SLOT_2_PHASE310,
                slot_1_contains_tier0_vault=True,
                slot_1_write_protected=True,
            )
            self.assertTrue(ok.valid, msg=f"op={op} on Slot-2 should pass")
            self.assertFalse(ok.slot1_vault_firewall_blocked)
            self.assertEqual(ok.slot1_data_sector_writes, 0)

    def test_25_g135_slot1_write_allowed_only_when_vault_absent_and_unlocked(self) -> None:
        ok = verify_bright_mon_shotmark_vault_guard(
            requested_card_op=CARD_OP_ADD_SHOT_MARK_2_G135,
            requested_target_slot=MEDIA_SLOT_1_PHASE310,
            slot_1_contains_tier0_vault=False,
            slot_1_write_protected=False,
        )
        self.assertTrue(ok.valid)
        self.assertFalse(ok.slot1_vault_firewall_blocked)

    def test_26_g135_384_state_matrix_holds(self) -> None:
        m = compute_bright_mon_shotmark_vault_matrix()
        self.assertEqual(m["states_checked"], 384)
        self.assertTrue(m["all_invariants_hold"])
        self.assertEqual(m["bm_active_effect_off_count"], 48)
        self.assertEqual(m["bm_autocancel_count"], 336)
        self.assertEqual(m["cam_reset_mon_persisted_count"], 192)
        self.assertEqual(m["slot1_vault_blocked_count"], 160)

    def test_27_g135_normalization_aliases_and_resolver(self) -> None:
        s = resolve_fx3_bright_mon_shotmark_vault_state(
            shoot_mode="S&Q",
            exposure_mode="m",
            focus_mode="mf",
            requested_bright_monitoring_active=True,
            requested_monitor_brightness_mode="sunny weather",
            requested_card_op=CARD_OP_SET_CLIP_FLAG_G135,
            requested_clip_flag="keep",
            requested_image_jump_setting="No Shot Mark",
            requested_photo_capture_file_type="HEIF 4:2:0",
            requested_target_slot="slot b",
            reset_action="cam_reset",
            requested_live_view_display="off",
        )
        self.assertTrue(s["valid"])
        self.assertTrue(s["effective_bright_monitoring_active"])
        self.assertEqual(s["effective_live_view_display"], LIVE_VIEW_DISPLAY_EFFECT_OFF_G135)
        self.assertEqual(s["effective_monitor_brightness_mode"], MONITOR_BRIGHTNESS_SUNNY_WEATHER_G135)
        self.assertEqual(s["requested_card_op"], CARD_OP_SET_CLIP_FLAG_G135)
        self.assertEqual(s["requested_clip_flag"], "KEEP")
        self.assertEqual(s["requested_target_slot"], MEDIA_SLOT_2_PHASE310)

    def test_28_g135_invalid_telemetry_and_bool_body_id_rejected(self) -> None:
        for bad_kw in (
            {"body_model_id": False},
            {"body_model_name": "FX9"},
            {"requested_live_view_display": "AlwaysOff"},
            {"requested_card_op": "EraseFormatCard"},
            {"requested_clip_flag": "STAR5"},
            {"requested_image_jump_setting": "Jump100"},
            {"requested_photo_capture_file_type": "DNG"},
            {"requested_target_slot": "Slot 3"},
        ):
            bad = verify_bright_mon_shotmark_vault_guard(**bad_kw)  # type: ignore[arg-type]
            self.assertFalse(bad.valid)
            self.assertEqual(bad.status, STATUS_BLOCKED_G135_TELEMETRY_INVALID)

    def test_29_g135_evaluate_with_persistent_emmc_write_blocked(self) -> None:
        verdict, res = evaluate_g135_bright_mon_shotmark_vault_guard(
            force_clean_room=True,
            request_persistent_emmc_writes=True,
        )
        self.assertFalse(verdict.passed)
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        self.assertFalse(res.persistent_emmc_writes_authorized)

    def test_30_g135_gate_constants_and_uxc_resid16_pinned(self) -> None:
        self.assertEqual(G135, "G135")
        self.assertEqual(G135_GATE_ID, "G135")
        self.assertEqual(BRIGHT_MONITORING_F_UXC_RESID16_G135, 0x701F)
        self.assertEqual(CREATE_DIVIDER_FRAME_F_UXC_RESID16_G135, 0x747A)
        self.assertEqual(CREATE_DIVIDER_FRAME_G_UXC_RESID16_G135, 0x6118)
        self.assertEqual(len(ALLOWED_CARD_OPS_G135), 10)
        self.assertEqual(len(ALLOWED_CLIP_FLAG_VALUES_G135), 4)
        self.assertEqual(len(ALLOWED_IMAGE_JUMP_SETTINGS_G135), 6)
        self.assertEqual(len(ALLOWED_MONITOR_BRIGHTNESS_MODES_G135), 2)


class TestGateG136TcLinkWifiUsbLanBulbDormantGuard(unittest.TestCase):
    def test_31_g136_default_nominal_fx3_passes(self) -> None:
        res = verify_tc_link_wifi_usblan_bulb_dormant_guard()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_VERIFIED_G136)
        self.assertEqual(res.fx3_bluetooth_tc_link_symbols, 0)
        self.assertEqual(res.vmc_bncm1_cable, FX3_WIRED_TC_CABLE_G136)
        self.assertFalse(res.fx6_has_bluetooth_hw)
        self.assertTrue(res.fx6_has_physical_tc_in_out_bnc)
        self.assertEqual(res.usb_lan_kernel_modules, USB_LAN_KERNEL_MODULES_G136)
        self.assertEqual(res.effective_airplane_mode, "On")
        self.assertEqual(res.wireless_packets_emitted, 0)
        self.assertFalse(res.rf_nvs_p12_p13_writes_permitted)

    def test_32_g136_rejects_bt_timecode_link_and_ultrasync_blue_eopnotsupp_95(self) -> None:
        bad = verify_tc_link_wifi_usblan_bulb_dormant_guard(tc_link_requested=True)
        self.assertFalse(bad.valid)
        self.assertTrue(bad.dormant_tc_link_blocked)
        self.assertEqual(bad.block_errno, EOPNOTSUPP_ERRNO_PHASE310)
        self.assertIn(
            STATUS_BLOCKED_G136_DORMANT_BT_TCLINK_OR_FX6_TC_VIOLATION,
            bad.violation_codes,
        )

        for trap in DORMANT_TC_LINK_TRAPS_G136:
            bad_sym = verify_tc_link_wifi_usblan_bulb_dormant_guard(
                requested_dormant_tc_symbol=trap,
            )
            self.assertFalse(bad_sym.valid)
            self.assertEqual(bad_sym.block_errno, EOPNOTSUPP_ERRNO_PHASE310)

        bad_fx6 = verify_tc_link_wifi_usblan_bulb_dormant_guard(
            claimed_fx6_has_bluetooth_hw_or_usb_tc_in=True,
        )
        self.assertFalse(bad_fx6.valid)
        self.assertIn(
            STATUS_BLOCKED_G136_DORMANT_BT_TCLINK_OR_FX6_TC_VIOLATION,
            bad_fx6.violation_codes,
        )

    def test_33_g136_wired_vmc_bncm1_ext_lk_and_hdmi_tc_out_rules(self) -> None:
        ok = verify_tc_link_wifi_usblan_bulb_dormant_guard(
            shoot_mode=SHOOT_MODE_MOVIE_PHASE310,
            vmc_bncm1_ext_ltc_requested=True,
            tc_make="Preset",
            tc_run="Free Run",
            hdmi_tc_output="On",
        )
        self.assertTrue(ok.valid)
        self.assertEqual(ok.ext_tc_lock_status, "EXT-LK")
        self.assertEqual(ok.hdmi_tc_output, "On")

        for bad_kw in (
            {"shoot_mode": SHOOT_MODE_SQ_PHASE310, "vmc_bncm1_ext_ltc_requested": True},
            {"shoot_mode": SHOOT_MODE_MOVIE_PHASE310, "vmc_bncm1_ext_ltc_requested": True, "tc_make": "Regenerate"},
            {"shoot_mode": SHOOT_MODE_MOVIE_PHASE310, "vmc_bncm1_ext_ltc_requested": True, "tc_run": "Rec Run"},
            {"shoot_mode": SHOOT_MODE_SQ_PHASE310, "hdmi_tc_output": "On"},
        ):
            bad = verify_tc_link_wifi_usblan_bulb_dormant_guard(**bad_kw)  # type: ignore[arg-type]
            self.assertFalse(bad.valid)
            self.assertIn(
                STATUS_BLOCKED_G136_DORMANT_BT_TCLINK_OR_FX6_TC_VIOLATION,
                bad.violation_codes,
            )

    def test_34_g136_wifi_wpa2_wpa3_accepted_vs_legacy_wep_wpa1_ipsec_rejected(self) -> None:
        for sec in (WIFI_SEC_WPA2_PSK_G136, WIFI_SEC_WPA3_SAE_G136):
            ok = verify_tc_link_wifi_usblan_bulb_dormant_guard(
                wifi_requested=True,
                requested_wifi_security=sec,
                access_authen_settings="On",
                requested_airplane_mode="Off",
                bench_zero_rf_required=False,
            )
            self.assertTrue(ok.valid)
            self.assertTrue(ok.wifi_active)

        for legacy in REMOVED_LEGACY_WIFI_SECURITIES_G136:
            bad = verify_tc_link_wifi_usblan_bulb_dormant_guard(
                wifi_requested=True,
                requested_wifi_security=legacy,
                requested_airplane_mode="Off",
                bench_zero_rf_required=False,
            )
            self.assertFalse(bad.valid)
            self.assertEqual(bad.block_errno, EOPNOTSUPP_ERRNO_PHASE310)
            self.assertIn(
                STATUS_BLOCKED_G136_WIFI_WPA_LEGACY_SKU_OR_USBLAN_EXCLUSION_VIOLATION,
                bad.violation_codes,
            )

    def test_35_g136_wifi_sku_ww728473_dual_band_vs_ww558244_24ghz_only(self) -> None:
        ok_dual = verify_tc_link_wifi_usblan_bulb_dormant_guard(
            fx3_sku_code=FX3_SKU_WW728473_G136,
            wifi_requested=True,
            requested_wifi_band=WIFI_BAND_5GHZ_G136,
            requested_airplane_mode="Off",
            bench_zero_rf_required=False,
        )
        self.assertTrue(ok_dual.valid)

        ok_24 = verify_tc_link_wifi_usblan_bulb_dormant_guard(
            fx3_sku_code=FX3_SKU_WW558244_G136,
            wifi_requested=True,
            requested_wifi_band=WIFI_BAND_2_4GHZ_G136,
            requested_airplane_mode="Off",
            bench_zero_rf_required=False,
        )
        self.assertTrue(ok_24.valid)

        bad_5g = verify_tc_link_wifi_usblan_bulb_dormant_guard(
            fx3_sku_code=FX3_SKU_WW558244_G136,
            wifi_requested=True,
            requested_wifi_band=WIFI_BAND_5GHZ_G136,
            requested_airplane_mode="Off",
            bench_zero_rf_required=False,
        )
        self.assertFalse(bad_5g.valid)
        self.assertEqual(bad_5g.block_errno, EOPNOTSUPP_ERRNO_PHASE310)
        self.assertIn(
            STATUS_BLOCKED_G136_WIFI_WPA_LEGACY_SKU_OR_USBLAN_EXCLUSION_VIOLATION,
            bad_5g.violation_codes,
        )

    def test_36_g136_usblan_mutual_exclusion_with_multi_micro_usb_and_wifi(self) -> None:
        bad_multi = verify_tc_link_wifi_usblan_bulb_dormant_guard(
            usb_lan_requested=True,
            multi_micro_usb_active=True,
        )
        self.assertFalse(bad_multi.valid)
        self.assertTrue(bad_multi.usb_bus_mutual_exclusion_blocked)
        self.assertEqual(bad_multi.block_errno, EBUSY_ERRNO_PHASE310)
        self.assertIn(
            STATUS_BLOCKED_G136_WIFI_WPA_LEGACY_SKU_OR_USBLAN_EXCLUSION_VIOLATION,
            bad_multi.violation_codes,
        )

        bad_vmc = verify_tc_link_wifi_usblan_bulb_dormant_guard(
            shoot_mode=SHOOT_MODE_MOVIE_PHASE310,
            usb_lan_requested=True,
            vmc_bncm1_ext_ltc_requested=True,
        )
        self.assertFalse(bad_vmc.valid)
        self.assertTrue(bad_vmc.usb_bus_mutual_exclusion_blocked)

        bad_wifi = verify_tc_link_wifi_usblan_bulb_dormant_guard(
            usb_lan_requested=True,
            wifi_requested=True,
            requested_airplane_mode="Off",
            bench_zero_rf_required=False,
        )
        self.assertFalse(bad_wifi.valid)
        self.assertTrue(bad_wifi.usb_bus_mutual_exclusion_blocked)

    def test_37_g136_airplane_mode_zero_rf_permits_authorized_usblan_eth0(self) -> None:
        ok = verify_tc_link_wifi_usblan_bulb_dormant_guard(
            requested_airplane_mode="On",
            bench_zero_rf_required=True,
            usb_lan_requested=True,
            usb_lan_authorized=True,
            requested_usb_lan_cnct_launch="On",
        )
        self.assertTrue(ok.valid)
        self.assertTrue(ok.usb_lan_active)
        self.assertTrue(ok.wired_eth0_permitted_under_airplane)
        self.assertEqual(ok.wireless_packets_emitted, 0)
        self.assertFalse(ok.airplane_zero_rf_firewall_blocked)

        bad_unauth = verify_tc_link_wifi_usblan_bulb_dormant_guard(
            requested_airplane_mode="On",
            usb_lan_requested=True,
            usb_lan_authorized=False,
        )
        self.assertFalse(bad_unauth.valid)
        self.assertIn(
            STATUS_BLOCKED_G136_AIRPLANE_ZERO_RF_FIREWALL_VIOLATION,
            bad_unauth.violation_codes,
        )

    def test_38_g136_airplane_mode_zero_rf_blocks_wifi_bt_rfnvs_and_survives_resets(self) -> None:
        for bad_kw in (
            {"requested_airplane_mode": "Off", "bench_zero_rf_required": True},
            {"requested_airplane_mode": "On", "wifi_requested": True},
            {"requested_airplane_mode": "On", "bt_requested": True},
            {"requested_airplane_mode": "On", "rf_nvs_write_requested": True},
            {"claimed_airplane_resets_on_net_reset_or_init": True},
        ):
            bad = verify_tc_link_wifi_usblan_bulb_dormant_guard(**bad_kw)  # type: ignore[arg-type]
            self.assertFalse(bad.valid)
            self.assertTrue(bad.airplane_zero_rf_firewall_blocked)
            self.assertEqual(bad.wireless_packets_emitted, 0)
            self.assertFalse(bad.rf_nvs_p12_p13_writes_permitted)
            self.assertEqual(bad.rf_nvs_mutation_bytes, 0)
            self.assertIn(
                STATUS_BLOCKED_G136_AIRPLANE_ZERO_RF_FIREWALL_VIOLATION,
                bad.violation_codes,
            )

        for rst in (
            RESET_ACTION_RESET_NETWORK_SET_PHASE310,
            RESET_ACTION_INITIALIZE_PHASE310,
        ):
            ok_rst = verify_tc_link_wifi_usblan_bulb_dormant_guard(
                reset_action=rst,
                requested_airplane_mode="On",
            )
            self.assertTrue(ok_rst.valid)
            self.assertEqual(ok_rst.effective_airplane_mode, "On")
            self.assertTrue(ok_rst.airplane_survived_network_reset_and_init)

    def test_39_g136_usb_lan_cnct_launch_blocked_under_reset_network_or_init(self) -> None:
        for rst in (
            RESET_ACTION_RESET_NETWORK_SET_PHASE310,
            RESET_ACTION_INITIALIZE_PHASE310,
        ):
            ok = verify_tc_link_wifi_usblan_bulb_dormant_guard(
                reset_action=rst,
                requested_usb_lan_cnct_launch="On",
            )
            self.assertTrue(ok.valid)
            self.assertEqual(ok.effective_usb_lan_cnct_launch, "Off")

    def test_40_g136_rejects_dormant_bulb_timer_and_auto_hdr_eopnotsupp_95(self) -> None:
        bad_bt = verify_tc_link_wifi_usblan_bulb_dormant_guard(bulb_timer_requested=True)
        self.assertFalse(bad_bt.valid)
        self.assertTrue(bad_bt.dormant_bulb_timer_blocked)
        self.assertEqual(bad_bt.block_errno, EOPNOTSUPP_ERRNO_PHASE310)
        self.assertIn(
            STATUS_BLOCKED_G136_DORMANT_BULB_TIMER_OR_AUTO_HDR_VIOLATION,
            bad_bt.violation_codes,
        )

        for trap in DORMANT_BULB_TIMER_TRAPS_G136:
            bad = verify_tc_link_wifi_usblan_bulb_dormant_guard(
                requested_dormant_bulb_symbol=trap,
            )
            self.assertFalse(bad.valid)
            self.assertEqual(bad.block_errno, EOPNOTSUPP_ERRNO_PHASE310)

        bad_hdr = verify_tc_link_wifi_usblan_bulb_dormant_guard(auto_hdr_requested=True)
        self.assertFalse(bad_hdr.valid)
        self.assertTrue(bad_hdr.dormant_auto_hdr_blocked)
        self.assertEqual(bad_hdr.block_errno, EOPNOTSUPP_ERRNO_PHASE310)
        self.assertIn(
            STATUS_BLOCKED_G136_DORMANT_BULB_TIMER_OR_AUTO_HDR_VIOLATION,
            bad_hdr.violation_codes,
        )

        for trap in DORMANT_AUTO_HDR_TRAPS_G136:
            bad = verify_tc_link_wifi_usblan_bulb_dormant_guard(
                requested_dormant_hdr_symbol=trap,
            )
            self.assertFalse(bad.valid)
            self.assertEqual(bad.block_errno, EOPNOTSUPP_ERRNO_PHASE310)

    def test_41_g136_still_bulb_mechanical_single_passes_and_disables_antiflicker(self) -> None:
        for shutter in (SHUTTER_TYPE_MECHANICAL_G136, SHUTTER_TYPE_AUTO_G136):
            for drive in (STILL_DRIVE_SINGLE_G136, STILL_DRIVE_SELF_TIMER_SINGLE_G136):
                ok = verify_tc_link_wifi_usblan_bulb_dormant_guard(
                    shoot_mode=SHOOT_MODE_STILL_PHASE310,
                    requested_shutter_type=shutter,
                    requested_drive_mode=drive,
                    requested_bulb_mode=True,
                )
                self.assertTrue(ok.valid)
                self.assertTrue(ok.effective_bulb_active)
                self.assertFalse(ok.bulb_locked_out_clamped_to_30s)
                self.assertTrue(ok.anti_flicker_shoot_disabled)

    def test_42_g136_still_bulb_blocked_clamped_to_30s_under_all_lockout_conditions(self) -> None:
        lockout_cases = (
            {"requested_shutter_type": SHUTTER_TYPE_ELECTRONIC_G136},
            {"requested_drive_mode": STILL_DRIVE_CONT_SHOOTING_G136},
            {"requested_drive_mode": STILL_DRIVE_CONT_BRACKET_G136},
            {"requested_drive_mode": STILL_DRIVE_SELF_TIMER_CONT_G136},
            {"interval_shooting_on": True},
        )
        for kw in lockout_cases:
            clamped = verify_tc_link_wifi_usblan_bulb_dormant_guard(
                shoot_mode=SHOOT_MODE_STILL_PHASE310,
                requested_bulb_mode=True,
                **kw,  # type: ignore[arg-type]
            )
            self.assertTrue(clamped.valid)
            self.assertFalse(clamped.effective_bulb_active)
            self.assertTrue(clamped.bulb_locked_out_clamped_to_30s)

            forced = verify_tc_link_wifi_usblan_bulb_dormant_guard(
                shoot_mode=SHOOT_MODE_STILL_PHASE310,
                requested_bulb_mode=True,
                force_bulb_under_lockout=True,
                **kw,  # type: ignore[arg-type]
            )
            self.assertFalse(forced.valid)
            self.assertIn(
                STATUS_BLOCKED_G136_STILL_BULB_MECHANICAL_OR_DRO_LOCK_VIOLATION,
                forced.violation_codes,
            )

    def test_43_g136_bulb_blocked_in_movie_sq_and_fx6(self) -> None:
        for sm in (SHOOT_MODE_MOVIE_PHASE310, SHOOT_MODE_SQ_PHASE310):
            clamped = verify_tc_link_wifi_usblan_bulb_dormant_guard(
                shoot_mode=sm,
                requested_bulb_mode=True,
            )
            self.assertTrue(clamped.valid)
            self.assertTrue(clamped.bulb_locked_out_clamped_to_30s)
            self.assertIn("non_still_shoot_mode", clamped.bulb_lockout_reasons)

        bad_fx6 = verify_tc_link_wifi_usblan_bulb_dormant_guard(
            claimed_fx6_supports_still_bulb_or_dro=True,
        )
        self.assertFalse(bad_fx6.valid)
        self.assertIn(
            STATUS_BLOCKED_G136_STILL_BULB_MECHANICAL_OR_DRO_LOCK_VIOLATION,
            bad_fx6.violation_codes,
        )

    def test_44_g136_dro_and_dro_bracket_locked_off_under_picture_profile_or_hlg(self) -> None:
        for kw in ({"picture_profile_on": True}, {"hlg_still_image_on": True}):
            ok = verify_tc_link_wifi_usblan_bulb_dormant_guard(
                requested_dro_mode="Lv5",
                requested_dro_bracket="DRO Bracket: Hi",
                **kw,  # type: ignore[arg-type]
            )
            self.assertTrue(ok.valid)
            self.assertTrue(ok.dro_locked_off)
            self.assertEqual(ok.effective_dro_mode, DRO_OFF_G136)
            self.assertEqual(ok.effective_dro_bracket, "Off")

            bad = verify_tc_link_wifi_usblan_bulb_dormant_guard(
                requested_dro_mode="Lv5",
                force_dro_when_pp_or_hlg=True,
                **kw,  # type: ignore[arg-type]
            )
            self.assertFalse(bad.valid)
            self.assertIn(
                STATUS_BLOCKED_G136_STILL_BULB_MECHANICAL_OR_DRO_LOCK_VIOLATION,
                bad.violation_codes,
            )

    def test_45_g136_dro_reset_by_camera_settings_reset_all_levels_valid(self) -> None:
        for lvl in ALLOWED_DRO_MODES_G136:
            ok = verify_tc_link_wifi_usblan_bulb_dormant_guard(
                requested_dro_mode=lvl,
            )
            self.assertTrue(ok.valid)
            self.assertEqual(ok.effective_dro_mode, lvl)

        for brk in ALLOWED_DRO_BRACKET_MODES_G136:
            ok = verify_tc_link_wifi_usblan_bulb_dormant_guard(
                requested_dro_bracket=brk,
            )
            self.assertTrue(ok.valid)
            self.assertEqual(ok.effective_dro_bracket, brk)

        rst = verify_tc_link_wifi_usblan_bulb_dormant_guard(
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE310,
            requested_dro_mode="Lv4",
        )
        self.assertTrue(rst.valid)
        self.assertEqual(rst.effective_dro_mode, DRO_AUTO_G136)
        self.assertTrue(rst.dro_reset_by_cam_reset)

    def test_46_g136_768_state_matrix_holds(self) -> None:
        m = compute_tc_link_wifi_usblan_bulb_dormant_matrix()
        self.assertEqual(m["states_checked"], 768)
        self.assertTrue(m["all_invariants_hold"])
        self.assertEqual(m["zero_rf_blocked_count"], 576)
        self.assertEqual(m["usb_conflict_blocked_count"], 288)
        self.assertEqual(m["bulb_clamped_count"], 640)
        self.assertEqual(m["dro_locked_count"], 384)

    def test_47_g136_normalization_aliases_and_resolver(self) -> None:
        s = resolve_fx3_tc_link_wifi_usblan_bulb_dormant_state(
            shoot_mode="Movie",
            vmc_bncm1_ext_ltc_requested=True,
            tc_make="Preset",
            tc_run="Free Run",
            hdmi_tc_output="on",
            fx3_sku_code="WW728473",
            requested_wifi_band=WIFI_BAND_5GHZ_G136,
            requested_wifi_security=WIFI_SEC_WPA3_SAE_G136,
            requested_airplane_mode="on",
            requested_shutter_type="mechanical",
            requested_drive_mode="single",
            requested_bulb_mode=False,
            requested_dro_mode="lv3",
            requested_dro_bracket="DRO Bracket: Lo",
            reset_action="network_reset",
        )
        self.assertTrue(s["valid"])
        self.assertEqual(s["ext_tc_lock_status"], "EXT-LK")
        self.assertEqual(s["requested_wifi_band"], WIFI_BAND_5GHZ_G136)
        self.assertEqual(s["requested_wifi_security"], WIFI_SEC_WPA3_SAE_G136)
        self.assertEqual(s["effective_dro_mode"], "Lv3")
        self.assertEqual(s["effective_dro_bracket"], "DRO Bracket: Lo")

    def test_48_g136_invalid_telemetry_and_bool_body_id_rejected(self) -> None:
        for bad_kw in (
            {"body_model_id": False},
            {"body_model_name": "FX9"},
            {"fx3_sku_code": "WW999999"},
            {"requested_wifi_band": "6GHz"},
            {"requested_wifi_security": "TLS-SRP"},
            {"requested_shutter_type": "LeafShutter"},
            {"requested_drive_mode": "QuadShoot"},
            {"requested_dro_mode": "Lv9"},
            {"requested_dro_bracket": "DRO Bracket: Ultra"},
            {"tc_make": "External"},
            {"tc_run": "Pause"},
        ):
            bad = verify_tc_link_wifi_usblan_bulb_dormant_guard(**bad_kw)  # type: ignore[arg-type]
            self.assertFalse(bad.valid)
            self.assertEqual(bad.status, STATUS_BLOCKED_G136_TELEMETRY_INVALID)

    def test_49_g136_evaluate_with_persistent_emmc_write_blocked(self) -> None:
        verdict, res = evaluate_g136_tc_link_wifi_usblan_bulb_dormant_guard(
            force_clean_room=True,
            request_persistent_emmc_writes=True,
        )
        self.assertFalse(verdict.passed)
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        self.assertFalse(res.persistent_emmc_writes_authorized)

    def test_50_g136_gate_constants_and_kernel_modules_pinned(self) -> None:
        self.assertEqual(G136, "G136")
        self.assertEqual(G136_GATE_ID, "G136")
        self.assertEqual(USB_LAN_CNCT_LAUNCH_F_UXC_RESID16_G136, 0x7D2A)
        self.assertEqual(
            USB_LAN_KERNEL_MODULES_G136,
            (
                "cdc_ncm.ko",
                "cdc_ether.ko",
                "r8152.ko",
                "asix.ko",
                "ax88179_178a.ko",
                "usbnet.ko",
                "ipheth.ko",
                "rndis_host.ko",
            ),
        )
        self.assertEqual(len(ALLOWED_FX3_SKUS_G136), 2)
        self.assertEqual(len(ALLOWED_WIFI_BANDS_G136), 2)
        self.assertEqual(len(ALLOWED_WIFI_SECURITIES_G136), 2)
        self.assertEqual(len(ALLOWED_SHUTTER_TYPES_G136), 3)
        self.assertEqual(len(ALLOWED_STILL_DRIVE_MODES_G136), 7)


class TestUnified136GateEngineAndCli(unittest.TestCase):
    def test_51_stub_136gate_offline_133_of_136(self) -> None:
        rep = evaluate_136gate_preflight(
            force_clean_room=True,
            master_134_override=_make_stub_master134(dry_run=False),
        )
        self.assertEqual(rep.summary["total_gates"], 136)
        self.assertEqual(rep.summary["verified_gates"], 133)
        self.assertEqual(rep.summary["blocked_or_pending_gates"], 3)
        self.assertTrue(rep.offline_133_gates_verified)
        self.assertFalse(rep.all_136_gates_verified)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.cross_model_flash_authorized)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)
        self.assertEqual(rep.status, "VERIFIED_133_OF_136_AWAITING_PHYSICAL_TIER0")
        self.assertEqual(len(rep.gates), 136)

    def test_52_stub_136gate_dry_run_136_of_136(self) -> None:
        rep = evaluate_136_master_safety_gates(
            force_clean_room=True,
            simulate_bench_dry_run=True,
            master_134_override=_make_stub_master134(dry_run=True),
        )
        self.assertEqual(rep.summary["verified_gates"], 136)
        self.assertTrue(rep.all_136_gates_verified)
        self.assertTrue(rep.dry_run_rehearsal_only)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertEqual(rep.status, "VERIFIED_ALL_136_GATES_DRY_RUN_SIMULATED_BACKUP")

    def test_53_g135_failure_propagates_to_136gate_report(self) -> None:
        rep = evaluate_136gate_preflight(
            force_clean_room=True,
            master_134_override=_make_stub_master134(dry_run=True),
            bright_mon_shotmark_kwargs={
                "requested_card_op": CARD_OP_ADD_SHOT_MARK_1_G135,
                "requested_target_slot": MEDIA_SLOT_1_PHASE310,
                "slot_1_contains_tier0_vault": True,
            },
        )
        self.assertFalse(rep.g135_to_g136_all_passed)
        self.assertFalse(rep.all_136_gates_verified)
        self.assertEqual(
            rep.status,
            STATUS_BLOCKED_G135_SLOT1_TIER0_VAULT_WRITE_FIREWALL_VIOLATION,
        )

    def test_54_g136_failure_propagates_to_136gate_report(self) -> None:
        rep = evaluate_136gate_preflight(
            force_clean_room=True,
            master_134_override=_make_stub_master134(dry_run=True),
            tc_link_wifi_usblan_bulb_kwargs={"tc_link_requested": True},
        )
        self.assertFalse(rep.g135_to_g136_all_passed)
        self.assertFalse(rep.all_136_gates_verified)
        self.assertEqual(
            rep.status,
            STATUS_BLOCKED_G136_DORMANT_BT_TCLINK_OR_FX6_TC_VIOLATION,
        )

    def test_55_g134_failure_propagates_to_136gate_report(self) -> None:
        stub134 = _make_stub_master134(dry_run=True, all_g13_134_ok=False)
        bad134 = dataclasses.replace(
            stub134,
            status=STATUS_BLOCKED_G134_SLOT1_TIER0_VAULT_WRITE_FIREWALL_VIOLATION,
        )
        rep = evaluate_136gate_preflight(
            force_clean_room=True,
            master_134_override=bad134,
        )
        self.assertFalse(rep.g13_to_g136_all_passed)
        self.assertFalse(rep.all_136_gates_verified)
        self.assertEqual(
            rep.status,
            STATUS_BLOCKED_G134_SLOT1_TIER0_VAULT_WRITE_FIREWALL_VIOLATION,
        )

    def test_56_persistent_emmc_write_blocks_136gate_report(self) -> None:
        rep = run_136_gate_preflight(
            force_clean_room=True,
            request_persistent_emmc_writes=True,
            master_134_override=_make_stub_master134(dry_run=True),
        )
        self.assertEqual(rep.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        self.assertFalse(rep.all_136_gates_verified)

    def test_57_real_chained_136gate_offline_and_dry_run(self) -> None:
        off = evaluate_136gate_preflight(DEFAULT_REPO_ROOT)
        self.assertGreaterEqual(off.summary["verified_gates"], 133)
        self.assertEqual(off.summary["verified_gates"], 133)
        self.assertTrue(off.offline_133_gates_verified)
        self.assertFalse(off.overall_ready_for_hardware_attach)
        self.assertEqual(off.raw_firmware_bytes_leaked, 0)

        dry = evaluate_136gate_preflight(
            DEFAULT_REPO_ROOT, simulate_bench_dry_run=True
        )
        self.assertGreaterEqual(dry.summary["verified_gates"], 136)
        self.assertEqual(dry.summary["verified_gates"], 136)
        self.assertTrue(dry.all_136_gates_verified)
        self.assertFalse(dry.overall_ready_for_hardware_attach)
        self.assertFalse(dry.persistent_emmc_writes_authorized)
        self.assertFalse(dry.cross_model_flash_authorized)

    def test_58_real_chained_136gate_clean_room_forced_offline_and_dry_run(self) -> None:
        off = evaluate_136gate_preflight(DEFAULT_REPO_ROOT, force_clean_room=True)
        self.assertEqual(off.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(off.summary["verified_gates"], 133)
        self.assertTrue(off.offline_133_gates_verified)

        dry = evaluate_136gate_preflight(
            DEFAULT_REPO_ROOT, force_clean_room=True, simulate_bench_dry_run=True
        )
        self.assertEqual(dry.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(dry.summary["verified_gates"], 136)
        self.assertTrue(dry.all_136_gates_verified)

    def test_59_cli_help_python314_percent_escaping(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            with self.assertRaises(SystemExit) as ctx:
                cli_main(["--help"])
        self.assertEqual(ctx.exception.code, 0)
        out = buf.getvalue()
        self.assertIn("verify-bright-mon-shotmark-vault-guard", out)
        self.assertIn("verify-tc-link-wifi-usblan-bulb-dormant-guard", out)
        self.assertIn("verify-136-gates", out)

    def test_60_cli_g135_g136_summary_json_and_text(self) -> None:
        for cmd in (
            "verify-bright-mon-shotmark-vault-guard",
            "verify-tc-link-wifi-usblan-bulb-dormant-guard",
        ):
            buf_j = io.StringIO()
            with contextlib.redirect_stdout(buf_j):
                rc = cli_main([cmd, "--clean-room", "--summary", "--json"])
            self.assertEqual(rc, 0)
            data = json.loads(buf_j.getvalue())
            self.assertTrue(data["valid"])
            self.assertEqual(data["raw_firmware_bytes_leaked"], 0)

            buf_t = io.StringIO()
            with contextlib.redirect_stdout(buf_t):
                rc2 = cli_main([cmd, "--clean-room"])
            self.assertEqual(rc2, 0)
            self.assertIn("valid=True", buf_t.getvalue())

    def test_61_cli_verify_136_gates_subprocess_uses_sys_executable(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONPATH"] = str(DEFAULT_REPO_ROOT / "outputs" / "fx3-safety")
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "fx3_safety",
                "verify-136-gates",
                "--simulate-bench-dry-run",
                "--summary",
                "--json",
            ],
            cwd=str(DEFAULT_REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(
            payload["status"], "VERIFIED_ALL_136_GATES_DRY_RUN_SIMULATED_BACKUP"
        )
        self.assertEqual(payload["summary"]["verified_gates"], 136)
        self.assertEqual(payload["g135_status"], STATUS_VERIFIED_G135)
        self.assertEqual(payload["g136_status"], STATUS_VERIFIED_G136)

    def test_62_cli_verify_136_gates_clean_room_subprocess_uses_sys_executable(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONPATH"] = str(DEFAULT_REPO_ROOT / "outputs" / "fx3-safety")
        env["FX3_FX6_FORCE_CLEAN_ROOM"] = "1"
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "fx3_safety",
                "verify-136-gates",
                "--summary",
                "--json",
            ],
            cwd=str(DEFAULT_REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["verification_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(
            payload["status"], "VERIFIED_133_OF_136_AWAITING_PHYSICAL_TIER0"
        )
        self.assertEqual(payload["summary"]["verified_gates"], 133)

    def test_63_cli_verify_136_gates_offline_text_mode(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cli_main(["verify-136-gates", "--clean-room"])
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("VERIFIED_133_OF_136_AWAITING_PHYSICAL_TIER0", out)
        self.assertIn("verified=133/136", out)
        self.assertIn("overall_ready_for_hardware_attach=False", out)

    def test_64_cli_aliases_work_cleanly(self) -> None:
        for alias in (
            "verify-g135-bright-mon-shotmark-vault",
            "verify-g136-tc-link-wifi-usblan-bulb-dormant",
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = cli_main([alias, "--clean-room", "--summary", "--json"])
            self.assertEqual(rc, 0)
            self.assertTrue(json.loads(buf.getvalue())["valid"])

    def test_65_module_direct_main_entrypoint(self) -> None:
        for gate_flag in ("g135", "g136", "136"):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = module_main(
                    ["--gate", gate_flag, "--clean-room", "--summary", "--json"]
                )
            self.assertEqual(rc, 0)
            data = json.loads(buf.getvalue())
            self.assertEqual(
                data["status"] if gate_flag != "136" else data["g135_status"],
                STATUS_VERIFIED_G135
                if gate_flag in ("g135", "136")
                else STATUS_VERIFIED_G136,
            )

    def test_66_module_main_text_output_g135_g136_136(self) -> None:
        for flag in ("g135", "g136", "136"):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = module_main(["--gate", flag, "--clean-room"])
            self.assertEqual(rc, 0)
            self.assertIn("STATUS_VERIFIED" if flag != "136" else "133/136", buf.getvalue())

    def test_67_cli_full_json_payload_contains_136_gates_and_redlines(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cli_main(
                ["verify-136-gates", "--clean-room", "--simulate-bench-dry-run", "--json"]
            )
        self.assertEqual(rc, 0)
        data = json.loads(buf.getvalue())
        self.assertEqual(len(data["gates"]), 136)
        self.assertEqual(data["gates"][-2]["gate_id"], G135_GATE_ID)
        self.assertEqual(data["gates"][-2]["gate_code"], G135_GATE_CODE)
        self.assertEqual(data["gates"][-1]["gate_id"], G136_GATE_ID)
        self.assertEqual(data["gates"][-1]["gate_code"], G136_GATE_CODE)
        self.assertFalse(data["hardware_live_attachment_authorized"])
        self.assertFalse(data["persistent_emmc_writes_authorized"])
        self.assertEqual(data["raw_firmware_bytes_leaked"], 0)

    def test_68_h0_h1_trial_entry_blocked_if_persistent_emmc_or_g135_fails(self) -> None:
        rep_bad_g135 = evaluate_136gate_preflight(
            force_clean_room=True,
            master_134_override=_make_stub_master134(dry_run=False),
            bright_mon_shotmark_kwargs={"bright_monitoring_menu_toggle_claimed": True},
        )
        self.assertFalse(rep_bad_g135.h0_h1_trial_entry_allowed)
        self.assertEqual(
            rep_bad_g135.status,
            STATUS_BLOCKED_G135_BRIGHT_MONITORING_CUSTOM_KEY_OR_MAG_VIOLATION,
        )

        rep_emmc = evaluate_136gate_preflight(
            force_clean_room=True,
            master_134_override=_make_stub_master134(dry_run=False),
            request_persistent_emmc_writes=True,
        )
        self.assertFalse(rep_emmc.h0_h1_trial_entry_allowed)

    def test_69_fx3_clean_room_test_env_propagates_to_136_gates_subprocess(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONPATH"] = str(DEFAULT_REPO_ROOT / "outputs" / "fx3-safety")
        env[ENV_CLEAN_ROOM_TEST_PHASE310] = "1"
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "fx3_safety",
                "verify-g135-bright-mon-shotmark-vault",
                "--summary",
                "--json",
            ],
            cwd=str(DEFAULT_REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["verification_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(payload["valid"])

    def test_70_fx3_identity_constants_phase310_match_fx3_v702(self) -> None:
        self.assertEqual(FX3_MODEL_NAME_PHASE310, "ILME-FX3")
        self.assertEqual(FX3_MODEL_ID_PHASE310, 0x39383232)
        self.assertEqual(FX3_HELP_GUIDE_CODE_PHASE310, "ilc/2210")
        self.assertEqual(FX3_DEFAULT_FW_VERSION_PHASE310, "7.02")
        self.assertEqual(FX6_MODEL_NAME_PHASE310, "ILME-FX6")

    def test_71_g135_multiple_simultaneous_violations_collect_all_codes(self) -> None:
        bad = verify_bright_mon_shotmark_vault_guard(
            bright_monitoring_menu_toggle_claimed=True,
            requested_monitor_brightness_mode="AUTO",
            dormant_divide_extract_or_ftp_cut_requested=True,
            requested_card_op=CARD_OP_CREATE_DIVIDER_FRAME_G135,
            requested_target_slot=MEDIA_SLOT_1_PHASE310,
            slot_1_contains_tier0_vault=True,
        )
        self.assertFalse(bad.valid)
        self.assertEqual(len(bad.violation_codes), 4)
        self.assertIn(
            STATUS_BLOCKED_G135_BRIGHT_MONITORING_CUSTOM_KEY_OR_MAG_VIOLATION,
            bad.violation_codes,
        )
        self.assertIn(
            STATUS_BLOCKED_G135_MONITOR_BRIGHTNESS_OR_FX6_BACKLIGHT_VIOLATION,
            bad.violation_codes,
        )
        self.assertIn(
            STATUS_BLOCKED_G135_DORMANT_DIVIDE_EXTRACT_OR_FTP_CUT_VIOLATION,
            bad.violation_codes,
        )
        self.assertIn(
            STATUS_BLOCKED_G135_SLOT1_TIER0_VAULT_WRITE_FIREWALL_VIOLATION,
            bad.violation_codes,
        )

    def test_72_g136_multiple_simultaneous_violations_collect_all_codes(self) -> None:
        bad = verify_tc_link_wifi_usblan_bulb_dormant_guard(
            tc_link_requested=True,
            requested_wifi_security="WEP",
            wifi_requested=True,
            requested_airplane_mode="On",
            bulb_timer_requested=True,
            requested_shutter_type=SHUTTER_TYPE_ELECTRONIC_G136,
            requested_bulb_mode=True,
            force_bulb_under_lockout=True,
        )
        self.assertFalse(bad.valid)
        self.assertEqual(len(bad.violation_codes), 5)
        self.assertIn(
            STATUS_BLOCKED_G136_DORMANT_BT_TCLINK_OR_FX6_TC_VIOLATION,
            bad.violation_codes,
        )
        self.assertIn(
            STATUS_BLOCKED_G136_WIFI_WPA_LEGACY_SKU_OR_USBLAN_EXCLUSION_VIOLATION,
            bad.violation_codes,
        )
        self.assertIn(
            STATUS_BLOCKED_G136_AIRPLANE_ZERO_RF_FIREWALL_VIOLATION,
            bad.violation_codes,
        )
        self.assertIn(
            STATUS_BLOCKED_G136_DORMANT_BULB_TIMER_OR_AUTO_HDR_VIOLATION,
            bad.violation_codes,
        )
        self.assertIn(
            STATUS_BLOCKED_G136_STILL_BULB_MECHANICAL_OR_DRO_LOCK_VIOLATION,
            bad.violation_codes,
        )

    def test_73_g135_bright_monitoring_combined_3_auto_cancel_reasons(self) -> None:
        res = verify_bright_mon_shotmark_vault_guard(
            power_off=True,
            exposure_mode=EXPOSURE_MODE_INTELLIGENT_AUTO_G135,
            focus_mode=FOCUS_MODE_AF_C_G135,
            requested_bright_monitoring_active=True,
        )
        self.assertTrue(res.valid)
        self.assertFalse(res.effective_bright_monitoring_active)
        self.assertEqual(len(res.bright_monitoring_auto_cancel_reasons), 3)

    def test_74_g135_focus_magnifier_without_bright_monitoring_preserves_live_view_on(self) -> None:
        res = verify_bright_mon_shotmark_vault_guard(
            focus_mode=FOCUS_MODE_MF_G135,
            focus_magnifier_active=True,
            requested_bright_monitoring_active=False,
            requested_live_view_display=LIVE_VIEW_DISPLAY_EFFECT_ON_G135,
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.effective_live_view_display, LIVE_VIEW_DISPLAY_EFFECT_ON_G135)

    def test_75_g135_fx6_vf_brightness_boundary_1_and_15_valid(self) -> None:
        for b in (FX6_VF_BRIGHTNESS_MIN_G135, FX6_VF_BRIGHTNESS_MAX_G135):
            ok = verify_bright_mon_shotmark_vault_guard(fx6_vf_brightness=b)
            self.assertTrue(ok.valid)
            self.assertEqual(ok.fx6_vf_brightness, b)

    def test_76_g136_access_authen_off_with_wpa2_or_wpa3_rejected(self) -> None:
        bad = verify_tc_link_wifi_usblan_bulb_dormant_guard(
            wifi_requested=True,
            requested_wifi_security=WIFI_SEC_WPA3_SAE_G136,
            access_authen_settings="Off",
            requested_airplane_mode="Off",
            bench_zero_rf_required=False,
        )
        self.assertFalse(bad.valid)
        self.assertIn(
            STATUS_BLOCKED_G136_WIFI_WPA_LEGACY_SKU_OR_USBLAN_EXCLUSION_VIOLATION,
            bad.violation_codes,
        )

    def test_77_g136_single_bracket_and_dro_bracket_allowed_with_mechanical_bulb_off_wait(self) -> None:
        ok = verify_tc_link_wifi_usblan_bulb_dormant_guard(
            shoot_mode=SHOOT_MODE_STILL_PHASE310,
            requested_shutter_type=SHUTTER_TYPE_MECHANICAL_G136,
            requested_drive_mode=STILL_DRIVE_SINGLE_BRACKET_G136,
            requested_bulb_mode=True,
        )
        self.assertTrue(ok.valid)
        self.assertTrue(ok.effective_bulb_active)

    def test_78_g136_dro_bracket_forced_off_under_picture_profile_and_hlg(self) -> None:
        bad = verify_tc_link_wifi_usblan_bulb_dormant_guard(
            requested_dro_mode=DRO_OFF_G136,
            requested_dro_bracket="DRO Bracket: Hi",
            picture_profile_on=True,
            force_dro_when_pp_or_hlg=True,
        )
        self.assertFalse(bad.valid)
        self.assertIn(
            STATUS_BLOCKED_G136_STILL_BULB_MECHANICAL_OR_DRO_LOCK_VIOLATION,
            bad.violation_codes,
        )

    def test_79_g136_long_exposure_nr_preserved_and_anti_flicker_only_disabled_on_bulb(self) -> None:
        non_bulb = verify_tc_link_wifi_usblan_bulb_dormant_guard(
            requested_bulb_mode=False,
            long_exposure_nr="Off",
        )
        self.assertTrue(non_bulb.valid)
        self.assertFalse(non_bulb.anti_flicker_shoot_disabled)
        self.assertEqual(non_bulb.long_exposure_nr, "Off")

    def test_80_g136_offline_report_to_dict_json_roundtrip(self) -> None:
        rep = evaluate_136gate_preflight(
            force_clean_room=True,
            master_134_override=_make_stub_master134(dry_run=False),
        )
        blob = json.dumps(rep.to_dict(), ensure_ascii=False)
        decoded = json.loads(blob)
        self.assertEqual(decoded["summary"]["total_gates"], 136)
        self.assertEqual(decoded["summary"]["verified_gates"], 133)
        self.assertEqual(decoded["g135_result"]["status"], STATUS_VERIFIED_G135)
        self.assertEqual(decoded["g136_result"]["status"], STATUS_VERIFIED_G136)

    def test_81_g135_all_pasm_and_mf_combinations_activate_bright_monitoring(self) -> None:
        for exp in (
            EXPOSURE_MODE_P_G135,
            EXPOSURE_MODE_A_G135,
            EXPOSURE_MODE_S_G135,
            EXPOSURE_MODE_M_G135,
        ):
            res = verify_bright_mon_shotmark_vault_guard(
                exposure_mode=exp,
                focus_mode=FOCUS_MODE_MF_G135,
                requested_bright_monitoring_active=True,
            )
            self.assertTrue(res.valid)
            self.assertTrue(res.effective_bright_monitoring_active)

    def test_82_g135_camera_settings_reset_and_initialize_preserve_or_reset_monitor_brightness(self) -> None:
        res_cam = verify_bright_mon_shotmark_vault_guard(
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE310,
            requested_monitor_brightness_mode=MONITOR_BRIGHTNESS_MANUAL_G135,
            requested_monitor_brightness_level=2,
        )
        self.assertTrue(res_cam.valid)
        self.assertEqual(res_cam.effective_monitor_brightness_level, 2)

        res_init = verify_bright_mon_shotmark_vault_guard(
            reset_action=RESET_ACTION_INITIALIZE_PHASE310,
            requested_monitor_brightness_mode=MONITOR_BRIGHTNESS_MANUAL_G135,
            requested_monitor_brightness_level=2,
        )
        self.assertTrue(res_init.valid)
        self.assertEqual(res_init.effective_monitor_brightness_level, 0)

    def test_83_g136_wifi_24ghz_only_sku_ww558244_with_wpa2_psk_valid(self) -> None:
        ok = verify_tc_link_wifi_usblan_bulb_dormant_guard(
            fx3_sku_code=FX3_SKU_WW558244_G136,
            wifi_requested=True,
            requested_wifi_band=WIFI_BAND_2_4GHZ_G136,
            requested_wifi_security=WIFI_SEC_WPA2_PSK_G136,
            access_authen_settings="On",
            requested_airplane_mode="Off",
            bench_zero_rf_required=False,
        )
        self.assertTrue(ok.valid)
        self.assertTrue(ok.wifi_active)

    def test_84_g136_ext_lk_released_without_preset_and_free_run(self) -> None:
        ok_int = verify_tc_link_wifi_usblan_bulb_dormant_guard(
            shoot_mode=SHOOT_MODE_MOVIE_PHASE310,
            vmc_bncm1_ext_ltc_requested=False,
        )
        self.assertTrue(ok_int.valid)
        self.assertEqual(ok_int.ext_tc_lock_status, "INT")

    def test_85_milestone295_dynamic_auto_discovery_reaches_136_gates(self) -> None:
        import re

        candidates = []
        for name in fx3_safety.__all__:
            m = re.match(r"^evaluate_(\d+)gate_preflight$", name)
            if m:
                candidates.append((int(m.group(1)), name))
        highest = max(candidates)
        self.assertGreaterEqual(highest[0], 136)
        self.assertEqual(highest[1], "evaluate_136gate_preflight")

    def test_86_cli_verify_136_gates_json_default_donor_mode(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cli_main(["verify-136-gates", "--summary", "--json"])
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["status"], "VERIFIED_133_OF_136_AWAITING_PHYSICAL_TIER0")
        self.assertGreaterEqual(payload["summary"]["verified_gates"], 133)
        self.assertEqual(payload["summary"]["raw_firmware_bytes_leaked"], 0)


if __name__ == "__main__":
    unittest.main()
