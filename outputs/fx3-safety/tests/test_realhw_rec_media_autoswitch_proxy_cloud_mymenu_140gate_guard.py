"""Phase 317 (Task H378, Wave-60, 140/140 Safety Gates Grand Milestone!)
Dual-Mode Unit Tests (92 tests) for
`fx3_safety.realhw_rec_media_autoswitch_proxy_cloud_mymenu_and_140gate_guard`:

- Gate `G139` (`REALHW_REC_MEDIA_AUTO_SWITCH_OVERFLOW_VPG400_AND_PROXY_SUB_VAULT_GUARD`):
  - Dormant `[Prioritize Rec. Media]` (`_f 0x719e`, `0` hits in `FX3 appFw.so`) -> `EOPNOTSUPP=95`.
  - Split `Initialize`-only `[Recording Media]` (Still: `Slot 1` / `Slot 2` / `Simult. Recording` /
    `Sort Recording`; Movie: `Slot 1` / `Slot 2` / `Simult. Recording`, rejecting Movie `Sort
    Recording` with `EINVAL=22`; `Simult. Recording` strictly requiring matching `exFAT`/`FAT32`
    filesystems across both slots) + `[Auto Switch Media]` (`_f 0x6dd9`, `BKID_APP_setting_relay_rec`,
    survives `[Camera Settings Reset]`).
  - CRITICAL `Slot-2 -> Slot-1` Overflow Trap: `Slot 2` + `Auto Switch Media = On` + filling or
    ejecting `Slot 2` triggers `EROFS=30` on `Slot-1` Tier-0 Vault (`slot1_data_sector_writes == 0`,
    `slot1_avf_info_mutated == False`, `slot1_sub_dir_mutated == False`).
  - Card speed gates (`XAVC HS/S 4K` `V60`/`VPG200`, `<=200M` `U3/V30`, `<=60M` `Class 10`,
    `SDHC <=32GB` 4GB split, `XAVC S-I 4K / DCI 4K 600M` `V90`/`VPG200`, `S&Q XAVC S-I 4K 1200M`
    & `240fps` HD mandatory `CFexpress Type A VPG200/VPG400` `.uxc 0xe228`/`0xe224`, `CFexpress Type B`
    rejected `ENODEV=19`).
  - `[Proxy Settings]` (`_f 0x6e3f`, resettable): `XAVC S HD` (`1280x720 6M 8bit`) vs `XAVC HS HD`
    (`1920x1080 9M/16M 10bit`), dormant `16M 8bit` / `9M_420_8BIT` rejected, blocked at
    `119.88p/100p` & `S&Q 120/100fps` (NOT blocked on `XAVC S-I DCI 4K <=59.94p`), writes
    `M4ROOT/SUB/*S03.MP4` (protected on `Slot-1` Vault under `Simult. Recording` or coupled
    Delete/Protect `EROFS=30`) vs FX6 `Simul Rec` / `Chunk Proxy` exclusions.
- Gate `G140` (`REALHW_CREATORS_CLOUD_CNCT_WHILE_POWER_OFF_ZERO_RF_AND_MYMENU_42SLOT_GUARD`):
  - `[Creators' Cloud]` (`Cloud Connection *` / `Cloud Information *` survive even `[Initialize]`,
    requiring explicit sign-out; `CLOUD_CONNECTION_ON_FTP_OFF`) + `C3 Portal` + Ver. 7.00+
    `Clip Flag` (`OK`/`NG`/`KEEP`).
  - CRITICAL Zero-RF Hazard (`[Cnct. while Power OFF]` `_f 0x6ab3`, survives `[Camera Settings Reset]`,
    `_g 0x6476` SC/TC defect tracked): BLE (`UIBIZ_KEY_BLUETOOTH_LOWENERGY_POWER`) stays energized at
    physical power switch `OFF`; Zero-RF bench mode MUST enforce BOTH `[Airplane Mode] = On` AND
    `[Cnct. while Power OFF] = Off` (`rf_packets_transmitted == 0`), vs Bluetooth-less `FX6`.
  - Exact 42-slot `[My Menu]` (`6 x 7 = 42`, `group{1..6}_list{0..6}`, rejecting `>= 42` &
    `(Playback)` tab item registration `EINVAL=22`, rejecting `30`/`36` slot myths, surviving
    `[Camera Settings Reset]`) vs FX6 20-item `User Menu`, `User Menu Only`, rental `User Menu with Lock`
    (`0000..9999` PIN, `Multi-Function Dial + MENU`, excluded from `All File`, rejected on FX3
    `EOPNOTSUPP=95`), and `Slot-1` `CAMSET*.DAT` export blocked `EROFS=30`.
- Unified `140`-Gate Milestone Master Preflight (`evaluate_140gate_preflight` / `verify-140-gates`):
  - `schema_version == "realhw_140gate_preflight_v1"`, `137/140` offline (`VERIFIED_137_OF_140_AWAITING_PHYSICAL_TIER0`),
    `140/140` with `--simulate-bench-dry-run` (`VERIFIED_ALL_140_GATES_DRY_RUN_SIMULATED_BACKUP`),
    all hardware attach & persistent write redlines locked `False` and `raw_firmware_bytes_leaked == 0`,
    and forward-compatible dynamic auto-discovery check (`assertGreaterEqual(highest[0], 140)`).
"""

from __future__ import annotations

import contextlib
import dataclasses
import io
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import time
import unittest
from unittest import mock

import fx3_safety
from fx3_safety.__main__ import main as cli_main
from fx3_safety.realhw_big6_home_framing_interval_tc_ssh_fan_and_138gate_guard import (
    Master138GateReport,
)
from fx3_safety.realhw_rec_media_autoswitch_proxy_cloud_mymenu_and_140gate_guard import (
    ALLOWED_C3_PORTAL_PROFILES_G140,
    ALLOWED_CARD_TYPES_G139,
    ALLOWED_CLIP_FLAGS_G140,
    ALLOWED_MENU_TABS_G140,
    ALLOWED_MOVIE_FILE_FORMATS_G139,
    ALLOWED_MOVIE_RECORDING_MEDIA_G139,
    ALLOWED_POWER_SWITCH_STATES_G140,
    ALLOWED_PROXY_FILE_FORMATS_G139,
    ALLOWED_PROXY_RECORD_SETTINGS_G139,
    ALLOWED_REC_FRAME_RATES_G139,
    ALLOWED_RESET_ACTIONS_PHASE317,
    ALLOWED_SHOOT_MODES_PHASE317,
    ALLOWED_SLOT_FILESYSTEMS_G139,
    ALLOWED_SQ_FRAME_RATES_G139,
    ALLOWED_STILL_RECORDING_MEDIA_G139,
    ALWAYS_CONNECTED_F_UXC_RESID16_G140,
    AUTO_SWITCH_MEDIA_F_UXC_RESID16_G139,
    CARD_CFEXPRESS_TYPE_A_VPG200_G139,
    CARD_CFEXPRESS_TYPE_A_VPG400_G139,
    CARD_CFEXPRESS_TYPE_B_UNSUPPORTED_G139,
    CARD_SDHC_LE32GB_G139,
    CARD_SDXC_CLASS10_G139,
    CARD_SDXC_U3_V30_G139,
    CARD_SDXC_V60_G139,
    CARD_SDXC_V90_G139,
    CARD_SPEED_RANK_G139,
    CFEXPRESS_VPG200_BASE_UXC_RESID16_G139,
    CFEXPRESS_VPG400_BASE_UXC_RESID16_G139,
    CNCT_WHILE_POWER_OFF_F_UXC_RESID16_G140,
    CREATORS_CLOUD_G_UXC_RESID16_G140,
    CROSS_MODEL_FLASH_AUTHORIZED,
    DEFAULT_REPO_ROOT,
    DISPLAY_FROM_MY_MENU_F_UXC_RESID16_G140,
    DONOR_CHECK_CI_MAX_SECONDS_PHASE317,
    DONOR_CHECK_MAX_SECONDS_PHASE317,
    DORMANT_PRIORITIZE_REC_MEDIA_TRAPS_G139,
    DORMANT_PROXY_SETTINGS_G139,
    EBUSY_ERRNO_PHASE317,
    EINVAL_ERRNO_PHASE317,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    ENODEV_ERRNO_PHASE317,
    ENV_CLEAN_ROOM_TEST_PHASE317,
    ENV_FORCE_CLEAN_ROOM,
    EOPNOTSUPP_ERRNO_PHASE317,
    EROFS_ERRNO_PHASE317,
    FX3_DEFAULT_FW_VERSION_PHASE317,
    FX3_HELP_GUIDE_CODE_PHASE317,
    FX3_MODEL_ID_PHASE317,
    FX3_MODEL_NAME_PHASE317,
    FX3_MYMENU_EXACT_SLOTS_G140,
    FX3_MYMENU_FORBIDDEN_TABS_G140,
    FX3_MYMENU_GROUP_MAX_G140,
    FX3_MYMENU_GROUP_MIN_G140,
    FX3_MYMENU_LIST_MAX_G140,
    FX3_MYMENU_LIST_MIN_G140,
    FX6_DEFAULT_FW_VERSION_PHASE317,
    FX6_MODEL_NAME_PHASE317,
    FX6_PRODUCT_CODE_PHASE317,
    FX6_PROXY_CHUNK_DURATIONS_G139,
    FX6_PROXY_SUB_PATH_G139,
    FX6_RENTAL_LOCK_CHORD_G140,
    FX6_USER_MENU_MAX_ITEMS_G140,
    G139,
    G139_GATE_CODE,
    G139_GATE_ID,
    G140,
    G140_GATE_CODE,
    G140_GATE_ID,
    HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    HUMAN_HARDWARE_ATTACH_TOKEN,
    MOVIE_FORMAT_XAVC_HS_4K_G139,
    MOVIE_FORMAT_XAVC_S_4K_G139,
    MOVIE_FORMAT_XAVC_S_HD_G139,
    MOVIE_FORMAT_XAVC_S_I_4K_G139,
    MOVIE_FORMAT_XAVC_S_I_DCI_4K_G139,
    MOVIE_FORMAT_XAVC_S_I_HD_G139,
    MYMENU_OPS_G140,
    MY_MENU_G_UXC_RESID16_G140,
    Master140GateReport,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED,
    PHYSICAL_USB_PACKETS_EMITTED,
    PINNED_FX3_APPFW_SLICES_PHASE317,
    PINNED_FX3_APPFW_SLICES_SHA256_PHASE317,
    PINNED_FX6_APPFW_SLICES_PHASE317,
    PINNED_FX6_APPFW_SLICES_SHA256_PHASE317,
    PINNED_PHASE317_DONOR_SPECS,
    PROXY_BLOCKED_REC_FRAME_RATES_G139,
    PROXY_BLOCKED_SQ_FRAME_RATES_G139,
    PROXY_FORMAT_XAVC_HS_HD_G139,
    PROXY_FORMAT_XAVC_S_HD_G139,
    PROXY_SETTINGS_F_UXC_RESID16_G139,
    PROXY_SETTING_16M_10BIT_G139,
    PROXY_SETTING_6M_8BIT_G139,
    PROXY_SETTING_9M_10BIT_G139,
    PROXY_SUB_PATH_CFEXPRESS_G139,
    PROXY_SUB_PATH_SDXC_G139,
    RAW_FIRMWARE_BYTES_LEAKED,
    REALHW_140GATE_PREFLIGHT_SCHEMA,
    REALHW_CREATORS_CLOUD_CNCT_WHILE_POWER_OFF_ZERO_RF_AND_MYMENU_42SLOT_GUARD,
    REALHW_REC_MEDIA_AUTOSWITCH_PROXY_CLOUD_MYMENU_140GATE_SCHEMA,
    REALHW_REC_MEDIA_AUTOSWITCH_PROXY_CLOUD_MYMENU_140GATE_VERSION,
    REALHW_REC_MEDIA_AUTO_SWITCH_OVERFLOW_VPG400_AND_PROXY_SUB_VAULT_GUARD,
    REC_MEDIA_SIMULT_G139,
    REC_MEDIA_SLOT_1_G139,
    REC_MEDIA_SLOT_2_G139,
    REC_MEDIA_SORT_G139,
    RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE317,
    RESET_ACTION_INITIALIZE_PHASE317,
    RESET_ACTION_NONE_PHASE317,
    RESET_ACTION_RESET_NETWORK_SET_PHASE317,
    SHOOT_MODE_MOVIE_PHASE317,
    SHOOT_MODE_SQ_PHASE317,
    SHOOT_MODE_STILL_PHASE317,
    SLOT_FS_EXFAT_G139,
    SLOT_FS_FAT32_G139,
    SPI_NOR_WRITE_AUTHORIZED,
    STATUS_BLOCKED_G139_CARD_SPEED_OR_TYPEB_VIOLATION,
    STATUS_BLOCKED_G139_PROXY_FORMAT_EXCLUSION_OR_FX6_CROSSWIRE_VIOLATION,
    STATUS_BLOCKED_G139_REC_MEDIA_SPLIT_FS_OR_DORMANT_PRIORITIZE_VIOLATION,
    STATUS_BLOCKED_G139_SLOT2_TO_SLOT1_OVERFLOW_OR_VAULT_VIOLATION,
    STATUS_BLOCKED_G139_TELEMETRY_INVALID,
    STATUS_BLOCKED_G140_CLOUD_PERSISTENCE_OR_FTP_EXCLUSION_VIOLATION,
    STATUS_BLOCKED_G140_CNCT_WHILE_POWER_OFF_ZERO_RF_VIOLATION,
    STATUS_BLOCKED_G140_FX6_USER_MENU_LOCK_OR_SLOT1_CAMSET_VIOLATION,
    STATUS_BLOCKED_G140_MYMENU_42SLOT_OR_PLAYBACK_TAB_VIOLATION,
    STATUS_BLOCKED_G140_TELEMETRY_INVALID,
    STATUS_BLOCKED_PERSISTENT_EMMC_WRITE,
    STATUS_BLOCKED_PHASE317_DONOR_INTEGRITY,
    STATUS_VERIFIED_G139,
    STATUS_VERIFIED_G140,
    STATUS_VERIFIED_SAFE,
    USB_PACKETS_TRANSMITTED,
    audit_phase317_donor_contracts,
    compute_creators_cloud_zerorf_mymenu_matrix,
    compute_rec_media_autoswitch_proxy_matrix,
    evaluate_140_master_safety_gates,
    evaluate_140gate_preflight,
    evaluate_g139_rec_media_autoswitch_proxy_vault_guard,
    evaluate_g140_creators_cloud_zerorf_mymenu42_guard,
    main as guard_cli_main,
    resolve_fx3_creators_cloud_zerorf_mymenu_state,
    resolve_fx3_rec_media_autoswitch_proxy_state,
    run_140_gate_preflight,
    verify_creators_cloud_zerorf_mymenu42_guard,
    verify_rec_media_autoswitch_proxy_vault_guard,
)


def _donors_available_here() -> bool:
    from fx3_safety.thermal_pwm_and_power_guard import resolve_donor_thermal_power_paths

    work_root = resolve_donor_thermal_power_paths(repo_root=DEFAULT_REPO_ROOT).work_root
    for spec in PINNED_PHASE317_DONOR_SPECS.values():
        if not (work_root / spec[1]).exists():
            return False
    return True


def _build_stub_138_report(
    *, dry_run: bool = False, all_g13_138_ok: bool = True
) -> Master138GateReport:
    gates = []
    for idx in range(1, 139):
        is_tier0 = idx in (10, 11, 12)
        passed = bool(
            idx <= 9
            or (is_tier0 and dry_run)
            or (idx >= 13 and all_g13_138_ok)
        )
        gates.append(
            {
                "gate_id": f"G{idx:02d}",
                "gate_code": f"STUB_G{idx:02d}",
                "status": "STATUS_VERIFIED_SAFE" if passed else "AWAITING_PHYSICAL_TIER0",
                "passed": passed,
                "evidence": "stub",
                "violation_codes": [] if passed else ["AWAITING_PHYSICAL_TIER0"],
            }
        )
    g01_12 = 12 if dry_run else 9
    g13_136 = 124 if all_g13_138_ok else 0
    g137_138 = 2 if all_g13_138_ok else 0
    total = g01_12 + g13_136 + g137_138
    return Master138GateReport(
        schema="realhw_138gate_preflight_v1",
        version="2026.11.17",
        evaluated_utc="2026-11-17T00:00:00Z",
        verification_mode="CLEAN_ROOM_SYNTHETIC",
        clean_room_forced=True,
        dry_run_rehearsal_only=dry_run,
        overall_ready_for_hardware_attach=False,
        hardware_live_attachment_authorized=False,
        offline_135_gates_verified=all_g13_138_ok,
        all_138_gates_verified=(dry_run and all_g13_138_ok),
        g13_to_g138_all_passed=all_g13_138_ok,
        g137_to_g138_all_passed=all_g13_138_ok,
        h0_h1_trial_entry_allowed=all_g13_138_ok,
        status=(
            "VERIFIED_ALL_138_GATES_DRY_RUN_SIMULATED_BACKUP"
            if dry_run
            else "VERIFIED_135_OF_138_AWAITING_PHYSICAL_TIER0"
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
            "g13_to_g136_verified": g13_136,
            "g137_to_g138_verified": g137_138,
            "verified_gates": total,
        },
        gates=tuple(gates),
        master_136_report={},
        g137_result={},
        g138_result={},
        errors=(),
        warnings=(),
    )


class TestPackageExportsAndDonorAuditPhase317(unittest.TestCase):
    def test_01_package_exports_phase317_symbols_and_all(self) -> None:
        self.assertIs(fx3_safety.evaluate_140gate_preflight, evaluate_140gate_preflight)
        self.assertIs(
            fx3_safety.evaluate_g139_rec_media_autoswitch_proxy_vault_guard,
            evaluate_g139_rec_media_autoswitch_proxy_vault_guard,
        )
        self.assertIs(
            fx3_safety.evaluate_g140_creators_cloud_zerorf_mymenu42_guard,
            evaluate_g140_creators_cloud_zerorf_mymenu42_guard,
        )
        self.assertEqual(fx3_safety.G139, "G139")
        self.assertEqual(fx3_safety.G140, "G140")
        self.assertIn("evaluate_140gate_preflight", fx3_safety.__all__)
        self.assertIn("evaluate_140_master_safety_gates", fx3_safety.__all__)
        self.assertIn("run_140_gate_preflight", fx3_safety.__all__)
        self.assertIn("Master140GateReport", fx3_safety.__all__)
        self.assertIn(
            "evaluate_g139_rec_media_autoswitch_proxy_vault_guard", fx3_safety.__all__
        )
        self.assertIn(
            "evaluate_g140_creators_cloud_zerorf_mymenu42_guard", fx3_safety.__all__
        )
        self.assertIn(
            "realhw_rec_media_autoswitch_proxy_cloud_mymenu_and_140gate_guard",
            fx3_safety.__all__,
        )

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

    def test_03_schema_and_gate_constants(self) -> None:
        self.assertEqual(REALHW_140GATE_PREFLIGHT_SCHEMA, "realhw_140gate_preflight_v1")
        self.assertEqual(
            REALHW_REC_MEDIA_AUTOSWITCH_PROXY_CLOUD_MYMENU_140GATE_SCHEMA,
            "realhw_140gate_preflight_v1",
        )
        self.assertEqual(REALHW_REC_MEDIA_AUTOSWITCH_PROXY_CLOUD_MYMENU_140GATE_VERSION, "2026.11.17")
        self.assertEqual(G139_GATE_ID, "G139")
        self.assertEqual(G140_GATE_ID, "G140")
        self.assertEqual(
            G139_GATE_CODE,
            REALHW_REC_MEDIA_AUTO_SWITCH_OVERFLOW_VPG400_AND_PROXY_SUB_VAULT_GUARD,
        )
        self.assertEqual(
            G140_GATE_CODE,
            REALHW_CREATORS_CLOUD_CNCT_WHILE_POWER_OFF_ZERO_RF_AND_MYMENU_42SLOT_GUARD,
        )

    def test_04_donor_audit_clean_room_forced_succeeds_fast_zero_leaks(self) -> None:
        audit = audit_phase317_donor_contracts(force_clean_room=True)
        self.assertTrue(audit.valid)
        self.assertEqual(audit.status, STATUS_VERIFIED_SAFE)
        self.assertEqual(audit.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(audit.raw_firmware_bytes_leaked, 0)
        self.assertTrue(audit.fx3_contracts_verified)
        self.assertTrue(audit.fx6_contracts_verified)
        self.assertTrue(audit.four_lang_resid16_parity_verified)
        self.assertTrue(audit.zero_forbidden_myths_verified)

    def test_05_donor_audit_env_force_and_test_clean_room_modes(self) -> None:
        for env_key in (ENV_FORCE_CLEAN_ROOM, ENV_CLEAN_ROOM_TEST_PHASE317):
            with mock.patch.dict(os.environ, {env_key: "1"}):
                audit = audit_phase317_donor_contracts()
                self.assertTrue(audit.valid)
                self.assertEqual(audit.verification_mode, "CLEAN_ROOM_SYNTHETIC")
                self.assertEqual(audit.raw_firmware_bytes_leaked, 0)

    def test_06_donor_audit_missing_donors_falls_back_clean_room(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            with mock.patch.dict(
                os.environ,
                {ENV_FORCE_CLEAN_ROOM: "", ENV_CLEAN_ROOM_TEST_PHASE317: ""},
            ):
                audit = audit_phase317_donor_contracts(work_root=Path(td))
                self.assertTrue(audit.valid)
                self.assertEqual(audit.verification_mode, "CLEAN_ROOM_SYNTHETIC")
                self.assertGreaterEqual(len(audit.warnings), 1)
                self.assertEqual(audit.raw_firmware_bytes_leaked, 0)

    def test_07_donor_audit_corrupted_sha_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            dummy = root / "bad.bin"
            dummy.write_bytes(b"corrupted-payload")
            specs = {
                "fx3_bad": ("FX3", "bad.bin", len(b"corrupted-payload"), "0" * 64, (b"corrupted",), "bad"),
            }
            with mock.patch.dict(
                os.environ,
                {ENV_FORCE_CLEAN_ROOM: "", ENV_CLEAN_ROOM_TEST_PHASE317: ""},
            ):
                audit = audit_phase317_donor_contracts(
                    work_root=root,
                    force_clean_room=False,
                    donor_specs_override=specs,
                )
            self.assertFalse(audit.valid)
            self.assertEqual(audit.status, STATUS_BLOCKED_PHASE317_DONOR_INTEGRITY)
            self.assertIn("fx3_bad:sha256_mismatch", audit.missing_markers)

    def test_08_donor_audit_size_and_token_mismatch_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            blob = b"partial-file"
            (root / "bad.bin").write_bytes(blob)
            import hashlib

            sha = hashlib.sha256(blob).hexdigest()
            specs = {
                "fx3_bad": ("FX3", "bad.bin", 9999, sha, (b"NONEXISTENT_TOKEN",), "bad"),
            }
            with mock.patch.dict(
                os.environ,
                {ENV_FORCE_CLEAN_ROOM: "", ENV_CLEAN_ROOM_TEST_PHASE317: ""},
            ):
                audit = audit_phase317_donor_contracts(
                    work_root=root,
                    force_clean_room=False,
                    donor_specs_override=specs,
                )
            self.assertFalse(audit.valid)
            self.assertIn("fx3_bad:size_mismatch", audit.missing_markers)
            self.assertIn("fx3_bad:token_missing", audit.missing_markers)

    def test_09_donor_audit_live_o_rdonly_when_present_under_budget(self) -> None:
        if os.environ.get(ENV_FORCE_CLEAN_ROOM) or os.environ.get(ENV_CLEAN_ROOM_TEST_PHASE317):
            self.skipTest("Clean-room env var forces synthetic audit")
        if not _donors_available_here():
            self.skipTest("Donor binaries absent in CI/clean-room host")
        audit = audit_phase317_donor_contracts(force_clean_room=False)
        self.assertTrue(audit.valid, msg=f"errors={audit.errors}")
        self.assertEqual(audit.verification_mode, "LOCAL_DONOR_O_RDONLY")
        self.assertEqual(audit.access_mode, "POSIX_O_RDONLY_AND_PREAD_ZERO_MUTATION")
        self.assertEqual(audit.files_inspected, len(PINNED_PHASE317_DONOR_SPECS))
        self.assertLessEqual(audit.elapsed_seconds, DONOR_CHECK_CI_MAX_SECONDS_PHASE317)
        self.assertLessEqual(audit.elapsed_seconds, DONOR_CHECK_MAX_SECONDS_PHASE317)
        self.assertTrue(audit.within_budget_200ms)
        self.assertEqual(audit.raw_firmware_bytes_leaked, 0)

    def test_10_pinned_appfw_slices_and_hashes_immutable_shape(self) -> None:
        self.assertEqual(len(PINNED_FX3_APPFW_SLICES_PHASE317), 24)
        self.assertEqual(len(PINNED_FX6_APPFW_SLICES_PHASE317), 7)
        self.assertEqual(len(PINNED_FX3_APPFW_SLICES_SHA256_PHASE317), 64)
        self.assertEqual(len(PINNED_FX6_APPFW_SLICES_SHA256_PHASE317), 64)
        self.assertEqual(len(PINNED_PHASE317_DONOR_SPECS), 11)
        self.assertEqual(DONOR_CHECK_MAX_SECONDS_PHASE317, 0.20)


class TestGateG139RecMediaAutoSwitchVpg400AndProxySubVault(unittest.TestCase):
    def test_11_g139_default_safe_slot2_bench_passes(self) -> None:
        res = verify_rec_media_autoswitch_proxy_vault_guard()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_VERIFIED_G139)
        self.assertEqual(res.effective_recording_media, REC_MEDIA_SLOT_2_G139)
        self.assertEqual(res.effective_auto_switch_media, "Off")
        self.assertEqual(res.slot1_data_sector_writes, 0)
        self.assertFalse(res.slot1_avf_info_mutated)
        self.assertFalse(res.slot1_sub_dir_mutated)
        self.assertEqual(res.matrix_states_checked, 256)

    def test_12_g139_uxc_resid16_anchors_exact(self) -> None:
        self.assertEqual(AUTO_SWITCH_MEDIA_F_UXC_RESID16_G139, 0x6DD9)
        self.assertEqual(PROXY_SETTINGS_F_UXC_RESID16_G139, 0x6E3F)
        self.assertEqual(CFEXPRESS_VPG200_BASE_UXC_RESID16_G139, 0xE228)
        self.assertEqual(CFEXPRESS_VPG400_BASE_UXC_RESID16_G139, 0xE224)

    def test_13_g139_dormant_prioritize_rec_media_traps_rejected_eopnotsupp(self) -> None:
        for trap in DORMANT_PRIORITIZE_REC_MEDIA_TRAPS_G139:
            res = verify_rec_media_autoswitch_proxy_vault_guard(
                requested_dormant_prioritize_token=trap,
            )
            self.assertFalse(res.valid)
            self.assertTrue(res.dormant_prioritize_rec_media_blocked)
            self.assertIn(
                STATUS_BLOCKED_G139_REC_MEDIA_SPLIT_FS_OR_DORMANT_PRIORITIZE_VIOLATION,
                res.violation_codes,
            )
            self.assertEqual(res.block_errno, EOPNOTSUPP_ERRNO_PHASE317)

    def test_14_g139_still_vs_movie_split_recording_media_and_sort_rejection(self) -> None:
        self.assertEqual(
            ALLOWED_STILL_RECORDING_MEDIA_G139,
            (REC_MEDIA_SLOT_1_G139, REC_MEDIA_SLOT_2_G139, REC_MEDIA_SIMULT_G139, REC_MEDIA_SORT_G139),
        )
        self.assertEqual(
            ALLOWED_MOVIE_RECORDING_MEDIA_G139,
            (REC_MEDIA_SLOT_1_G139, REC_MEDIA_SLOT_2_G139, REC_MEDIA_SIMULT_G139),
        )
        still_sort = verify_rec_media_autoswitch_proxy_vault_guard(
            shoot_mode=SHOOT_MODE_STILL_PHASE317,
            requested_recording_media=REC_MEDIA_SORT_G139,
            slot_1_contains_tier0_vault=False,
            slot_1_read_only_state=False,
        )
        self.assertTrue(still_sort.valid)
        self.assertFalse(still_sort.movie_sort_recording_rejected)

        movie_sort = verify_rec_media_autoswitch_proxy_vault_guard(
            shoot_mode=SHOOT_MODE_MOVIE_PHASE317,
            requested_recording_media=REC_MEDIA_SORT_G139,
        )
        self.assertFalse(movie_sort.valid)
        self.assertTrue(movie_sort.movie_sort_recording_rejected)
        self.assertEqual(movie_sort.block_errno, EINVAL_ERRNO_PHASE317)

    def test_15_g139_sq_mode_also_rejects_sort_recording(self) -> None:
        sq_sort = verify_rec_media_autoswitch_proxy_vault_guard(
            shoot_mode=SHOOT_MODE_SQ_PHASE317,
            requested_recording_media=REC_MEDIA_SORT_G139,
        )
        self.assertFalse(sq_sort.valid)
        self.assertTrue(sq_sort.movie_sort_recording_rejected)
        self.assertEqual(sq_sort.block_errno, EINVAL_ERRNO_PHASE317)

    def test_16_g139_simult_recording_requires_matching_exfat_or_fat32_filesystems(self) -> None:
        for fs in (SLOT_FS_EXFAT_G139, SLOT_FS_FAT32_G139):
            ok = verify_rec_media_autoswitch_proxy_vault_guard(
                requested_recording_media=REC_MEDIA_SIMULT_G139,
                slot1_fs=fs,
                slot2_fs=fs,
                slot_1_contains_tier0_vault=False,
                slot_1_read_only_state=False,
            )
            self.assertTrue(ok.valid)
            self.assertTrue(ok.simult_filesystem_parity_ok)

        bad = verify_rec_media_autoswitch_proxy_vault_guard(
            requested_recording_media=REC_MEDIA_SIMULT_G139,
            slot1_fs=SLOT_FS_EXFAT_G139,
            slot2_fs=SLOT_FS_FAT32_G139,
            slot_1_contains_tier0_vault=False,
            slot_1_read_only_state=False,
        )
        self.assertFalse(bad.valid)
        self.assertFalse(bad.simult_filesystem_parity_ok)
        self.assertEqual(bad.block_errno, EINVAL_ERRNO_PHASE317)

    def test_17_g139_auto_switch_survives_camera_settings_reset_and_still_blocks_vault(self) -> None:
        res = verify_rec_media_autoswitch_proxy_vault_guard(
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE317,
            requested_recording_media=REC_MEDIA_SLOT_2_G139,
            requested_auto_switch_media="On",
            slot2_full_or_ejected=True,
            slot_1_contains_tier0_vault=True,
        )
        self.assertFalse(res.valid)
        self.assertTrue(res.auto_switch_survived_cam_reset)
        self.assertEqual(res.effective_auto_switch_media, "On")
        self.assertTrue(res.slot2_to_slot1_overflow_triggered)
        self.assertTrue(res.slot1_vault_firewall_blocked)
        self.assertEqual(res.block_errno, EROFS_ERRNO_PHASE317)
        self.assertEqual(res.slot1_data_sector_writes, 0)

    def test_18_g139_initialize_resets_recording_media_and_auto_switch_to_slot1_off(self) -> None:
        res = verify_rec_media_autoswitch_proxy_vault_guard(
            reset_action=RESET_ACTION_INITIALIZE_PHASE317,
            requested_recording_media=REC_MEDIA_SLOT_2_G139,
            requested_auto_switch_media="On",
            slot_1_contains_tier0_vault=True,
            slot_1_read_only_state=True,
        )
        self.assertEqual(res.effective_recording_media, REC_MEDIA_SLOT_1_G139)
        self.assertEqual(res.effective_auto_switch_media, "Off")
        # With recording_execute_requested=False & proxy Off, inspect is safe
        self.assertTrue(res.valid)
        self.assertEqual(res.slot1_data_sector_writes, 0)

    def test_19_g139_critical_slot2_to_slot1_overflow_trap_enforces_erofs(self) -> None:
        res = verify_rec_media_autoswitch_proxy_vault_guard(
            requested_recording_media=REC_MEDIA_SLOT_2_G139,
            requested_auto_switch_media="On",
            slot2_full_or_ejected=True,
            slot_1_contains_tier0_vault=True,
            slot_1_read_only_state=True,
            recording_execute_requested=True,
        )
        self.assertFalse(res.valid)
        self.assertIn(
            STATUS_BLOCKED_G139_SLOT2_TO_SLOT1_OVERFLOW_OR_VAULT_VIOLATION,
            res.violation_codes,
        )
        self.assertEqual(res.block_errno, EROFS_ERRNO_PHASE317)
        self.assertEqual(res.slot1_data_sector_writes, 0)
        self.assertFalse(res.slot1_avf_info_mutated)
        self.assertFalse(res.slot1_sub_dir_mutated)

    def test_20_g139_auto_switch_on_near_tier0_vault_blocks_even_before_slot2_full(self) -> None:
        res = verify_rec_media_autoswitch_proxy_vault_guard(
            requested_recording_media=REC_MEDIA_SLOT_2_G139,
            requested_auto_switch_media="On",
            slot2_full_or_ejected=False,
            slot_1_contains_tier0_vault=True,
        )
        self.assertFalse(res.valid)
        self.assertTrue(res.slot1_vault_firewall_blocked)
        self.assertEqual(res.block_errno, EROFS_ERRNO_PHASE317)

    def test_21_g139_bypass_slot1_vault_firewall_fails_closed(self) -> None:
        res = verify_rec_media_autoswitch_proxy_vault_guard(
            requested_recording_media=REC_MEDIA_SLOT_2_G139,
            requested_auto_switch_media="Off",
            slot_1_contains_tier0_vault=True,
            bypass_slot1_vault_firewall=True,
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.block_errno, EROFS_ERRNO_PHASE317)
        self.assertEqual(res.slot1_data_sector_writes, 0)

    def test_22_g139_slot1_or_simult_recording_execute_against_vault_blocked_erofs(self) -> None:
        for media in (REC_MEDIA_SLOT_1_G139, REC_MEDIA_SIMULT_G139):
            res = verify_rec_media_autoswitch_proxy_vault_guard(
                requested_recording_media=media,
                slot_1_contains_tier0_vault=True,
                recording_execute_requested=True,
            )
            self.assertFalse(res.valid)
            self.assertTrue(res.slot1_vault_firewall_blocked)
            self.assertEqual(res.block_errno, EROFS_ERRNO_PHASE317)
            self.assertEqual(res.slot1_data_sector_writes, 0)

    def test_23_g139_coupled_delete_or_protect_on_simult_or_slot1_blocked_erofs(self) -> None:
        res = verify_rec_media_autoswitch_proxy_vault_guard(
            requested_recording_media=REC_MEDIA_SIMULT_G139,
            slot_1_contains_tier0_vault=True,
            coupled_delete_or_protect_requested=True,
        )
        self.assertFalse(res.valid)
        self.assertTrue(res.slot1_vault_firewall_blocked)
        self.assertEqual(res.block_errno, EROFS_ERRNO_PHASE317)

    def test_24_g139_cfexpress_type_b_rejected_enodev(self) -> None:
        res = verify_rec_media_autoswitch_proxy_vault_guard(
            media_card_type=CARD_CFEXPRESS_TYPE_B_UNSUPPORTED_G139,
        )
        self.assertFalse(res.valid)
        self.assertTrue(res.cfexpress_type_b_rejected)
        self.assertFalse(res.card_speed_sufficient)
        self.assertIn(
            STATUS_BLOCKED_G139_CARD_SPEED_OR_TYPEB_VIOLATION, res.violation_codes
        )
        self.assertEqual(res.block_errno, ENODEV_ERRNO_PHASE317)

    def test_25_g139_xavc_hs_s_4k_280m_requires_v60_plus(self) -> None:
        too_slow = verify_rec_media_autoswitch_proxy_vault_guard(
            movie_file_format=MOVIE_FORMAT_XAVC_S_4K_G139,
            bitrate_mbps=280,
            media_card_type=CARD_SDXC_U3_V30_G139,
        )
        self.assertFalse(too_slow.valid)
        self.assertFalse(too_slow.card_speed_sufficient)
        self.assertEqual(too_slow.block_errno, EINVAL_ERRNO_PHASE317)

        ok = verify_rec_media_autoswitch_proxy_vault_guard(
            movie_file_format=MOVIE_FORMAT_XAVC_S_4K_G139,
            bitrate_mbps=280,
            media_card_type=CARD_SDXC_V60_G139,
        )
        self.assertTrue(ok.valid)
        self.assertTrue(ok.card_speed_sufficient)

    def test_26_g139_xavc_s_4k_200m_allows_v30_and_sdhc_flags_4gb_split(self) -> None:
        v30_ok = verify_rec_media_autoswitch_proxy_vault_guard(
            movie_file_format=MOVIE_FORMAT_XAVC_S_4K_G139,
            bitrate_mbps=140,
            media_card_type=CARD_SDXC_U3_V30_G139,
        )
        self.assertTrue(v30_ok.valid)

        sdhc_hd = verify_rec_media_autoswitch_proxy_vault_guard(
            movie_file_format=MOVIE_FORMAT_XAVC_S_HD_G139,
            bitrate_mbps=50,
            media_card_type=CARD_SDHC_LE32GB_G139,
        )
        self.assertTrue(sdhc_hd.valid)
        self.assertTrue(sdhc_hd.sdhc_4gb_split_active)

    def test_27_g139_xavc_si_4k_and_dci_4k_600m_require_v90_plus(self) -> None:
        for fmt in (MOVIE_FORMAT_XAVC_S_I_4K_G139, MOVIE_FORMAT_XAVC_S_I_DCI_4K_G139):
            bad = verify_rec_media_autoswitch_proxy_vault_guard(
                movie_file_format=fmt,
                bitrate_mbps=600,
                media_card_type=CARD_SDXC_V60_G139,
            )
            self.assertFalse(bad.valid)
            ok = verify_rec_media_autoswitch_proxy_vault_guard(
                movie_file_format=fmt,
                bitrate_mbps=600,
                media_card_type=CARD_SDXC_V90_G139,
            )
            self.assertTrue(ok.valid)

    def test_28_g139_sq_xavc_si_4k_1200m_requires_cfexpress_vpg200_vpg400(self) -> None:
        sdxc_v90 = verify_rec_media_autoswitch_proxy_vault_guard(
            shoot_mode=SHOOT_MODE_SQ_PHASE317,
            movie_file_format=MOVIE_FORMAT_XAVC_S_I_4K_G139,
            sq_frame_rate="60fps",
            bitrate_mbps=1200,
            media_card_type=CARD_SDXC_V90_G139,
        )
        self.assertFalse(sdxc_v90.valid)
        self.assertTrue(sdxc_v90.vpg200_uxc_0xe228_required)
        self.assertTrue(sdxc_v90.vpg400_uxc_0xe224_threshold_triggered)

        vpg200 = verify_rec_media_autoswitch_proxy_vault_guard(
            shoot_mode=SHOOT_MODE_SQ_PHASE317,
            movie_file_format=MOVIE_FORMAT_XAVC_S_I_4K_G139,
            sq_frame_rate="60fps",
            bitrate_mbps=1200,
            media_card_type=CARD_CFEXPRESS_TYPE_A_VPG200_G139,
        )
        self.assertTrue(vpg200.valid)
        self.assertEqual(vpg200.proxy_sub_dir_path, PROXY_SUB_PATH_CFEXPRESS_G139)

    def test_29_g139_sq_xavc_si_4k_1200m_with_proxy_on_requires_vpg400(self) -> None:
        vpg200_proxy = verify_rec_media_autoswitch_proxy_vault_guard(
            shoot_mode=SHOOT_MODE_SQ_PHASE317,
            movie_file_format=MOVIE_FORMAT_XAVC_S_I_4K_G139,
            sq_frame_rate="60fps",
            bitrate_mbps=1200,
            media_card_type=CARD_CFEXPRESS_TYPE_A_VPG200_G139,
            requested_proxy_recording="On",
        )
        self.assertFalse(vpg200_proxy.valid)
        self.assertTrue(vpg200_proxy.vpg400_uxc_0xe224_threshold_triggered)

        vpg400_proxy = verify_rec_media_autoswitch_proxy_vault_guard(
            shoot_mode=SHOOT_MODE_SQ_PHASE317,
            movie_file_format=MOVIE_FORMAT_XAVC_S_I_4K_G139,
            sq_frame_rate="60fps",
            bitrate_mbps=1200,
            media_card_type=CARD_CFEXPRESS_TYPE_A_VPG400_G139,
            requested_proxy_recording="On",
        )
        self.assertTrue(vpg400_proxy.valid)
        self.assertEqual(vpg400_proxy.effective_proxy_recording, "On")

    def test_30_g139_sq_xavc_si_hd_240fps_requires_cfexpress_type_a(self) -> None:
        v90_bad = verify_rec_media_autoswitch_proxy_vault_guard(
            shoot_mode=SHOOT_MODE_SQ_PHASE317,
            movie_file_format=MOVIE_FORMAT_XAVC_S_I_HD_G139,
            sq_frame_rate="240fps",
            bitrate_mbps=890,
            media_card_type=CARD_SDXC_V90_G139,
        )
        self.assertFalse(v90_bad.valid)
        self.assertTrue(v90_bad.vpg200_uxc_0xe228_required)

        cfe_ok = verify_rec_media_autoswitch_proxy_vault_guard(
            shoot_mode=SHOOT_MODE_SQ_PHASE317,
            movie_file_format=MOVIE_FORMAT_XAVC_S_I_HD_G139,
            sq_frame_rate="240fps",
            bitrate_mbps=890,
            media_card_type=CARD_CFEXPRESS_TYPE_A_VPG200_G139,
        )
        self.assertTrue(cfe_ok.valid)

    def test_31_g139_proxy_xavc_s_hd_vs_xavc_hs_hd_specs_and_sub_paths(self) -> None:
        s_hd = verify_rec_media_autoswitch_proxy_vault_guard(
            requested_proxy_recording="On",
            proxy_file_format=PROXY_FORMAT_XAVC_S_HD_G139,
            proxy_record_setting=PROXY_SETTING_6M_8BIT_G139,
            media_card_type=CARD_SDXC_V90_G139,
        )
        self.assertTrue(s_hd.valid)
        self.assertEqual(s_hd.proxy_resolution, "1280x720")
        self.assertEqual(s_hd.proxy_codec, "AVC/H.264")
        self.assertEqual(s_hd.proxy_bitrate_mbps, 6)
        self.assertEqual(s_hd.proxy_bit_depth, 8)
        self.assertEqual(s_hd.proxy_sub_dir_path, PROXY_SUB_PATH_SDXC_G139)

        hs_16 = verify_rec_media_autoswitch_proxy_vault_guard(
            requested_proxy_recording="On",
            proxy_file_format=PROXY_FORMAT_XAVC_HS_HD_G139,
            proxy_record_setting=PROXY_SETTING_16M_10BIT_G139,
            media_card_type=CARD_CFEXPRESS_TYPE_A_VPG400_G139,
        )
        self.assertTrue(hs_16.valid)
        self.assertEqual(hs_16.proxy_resolution, "1920x1080")
        self.assertEqual(hs_16.proxy_codec, "HEVC/H.265")
        self.assertEqual(hs_16.proxy_bitrate_mbps, 16)
        self.assertEqual(hs_16.proxy_bit_depth, 10)
        self.assertEqual(hs_16.proxy_sub_dir_path, PROXY_SUB_PATH_CFEXPRESS_G139)

    def test_32_g139_proxy_resets_on_camera_settings_reset(self) -> None:
        res = verify_rec_media_autoswitch_proxy_vault_guard(
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE317,
            requested_proxy_recording="On",
            proxy_file_format=PROXY_FORMAT_XAVC_HS_HD_G139,
            proxy_record_setting=PROXY_SETTING_16M_10BIT_G139,
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.effective_proxy_recording, "Off")
        self.assertEqual(res.proxy_file_format, PROXY_FORMAT_XAVC_S_HD_G139)
        self.assertEqual(res.proxy_record_setting, PROXY_SETTING_6M_8BIT_G139)

    def test_33_g139_dormant_proxy_settings_and_invalid_format_combos_rejected(self) -> None:
        for trap in DORMANT_PROXY_SETTINGS_G139:
            res = verify_rec_media_autoswitch_proxy_vault_guard(
                requested_proxy_recording="On",
                proxy_file_format=PROXY_FORMAT_XAVC_HS_HD_G139,
                proxy_record_setting=trap,
            )
            self.assertFalse(res.valid)
            self.assertEqual(res.block_errno, EOPNOTSUPP_ERRNO_PHASE317)

        bad_combo = verify_rec_media_autoswitch_proxy_vault_guard(
            requested_proxy_recording="On",
            proxy_file_format=PROXY_FORMAT_XAVC_S_HD_G139,
            proxy_record_setting=PROXY_SETTING_16M_10BIT_G139,
        )
        self.assertFalse(bad_combo.valid)
        self.assertEqual(bad_combo.block_errno, EINVAL_ERRNO_PHASE317)

    def test_34_g139_proxy_blocked_at_119_88p_100p_and_sq_120fps_100fps(self) -> None:
        for fr in PROXY_BLOCKED_REC_FRAME_RATES_G139:
            auto_off = verify_rec_media_autoswitch_proxy_vault_guard(
                rec_frame_rate=fr,
                requested_proxy_recording="On",
                force_proxy_under_100p_120p=False,
            )
            self.assertTrue(auto_off.valid)
            self.assertTrue(auto_off.proxy_blocked_by_frame_rate)
            self.assertEqual(auto_off.effective_proxy_recording, "Off")

            forced_bad = verify_rec_media_autoswitch_proxy_vault_guard(
                rec_frame_rate=fr,
                requested_proxy_recording="On",
                force_proxy_under_100p_120p=True,
            )
            self.assertFalse(forced_bad.valid)
            self.assertEqual(forced_bad.block_errno, EINVAL_ERRNO_PHASE317)

        for sq_fr in PROXY_BLOCKED_SQ_FRAME_RATES_G139:
            forced_sq = verify_rec_media_autoswitch_proxy_vault_guard(
                shoot_mode=SHOOT_MODE_SQ_PHASE317,
                sq_frame_rate=sq_fr,
                requested_proxy_recording="On",
                force_proxy_under_100p_120p=True,
            )
            self.assertFalse(forced_sq.valid)

    def test_35_g139_proxy_not_blocked_on_xavc_si_dci_4k_up_to_59_94p(self) -> None:
        dci_ok = verify_rec_media_autoswitch_proxy_vault_guard(
            movie_file_format=MOVIE_FORMAT_XAVC_S_I_DCI_4K_G139,
            rec_frame_rate="59.94p",
            bitrate_mbps=600,
            media_card_type=CARD_CFEXPRESS_TYPE_A_VPG400_G139,
            requested_proxy_recording="On",
            proxy_file_format=PROXY_FORMAT_XAVC_HS_HD_G139,
            proxy_record_setting=PROXY_SETTING_9M_10BIT_G139,
        )
        self.assertTrue(dci_ok.valid)
        self.assertFalse(dci_ok.proxy_blocked_by_frame_rate)
        self.assertEqual(dci_ok.effective_proxy_recording, "On")
        self.assertTrue(dci_ok.proxy_allowed_on_dci_4k_up_to_59_94p)

        myth = verify_rec_media_autoswitch_proxy_vault_guard(
            movie_file_format=MOVIE_FORMAT_XAVC_S_I_DCI_4K_G139,
            rec_frame_rate="59.94p",
            claimed_dci_4k_blocks_proxy=True,
        )
        self.assertFalse(myth.valid)

    def test_36_g139_proxy_in_camera_playback_and_fx3_chunk_proxy_xdroot_rejected(self) -> None:
        pb = verify_rec_media_autoswitch_proxy_vault_guard(
            claimed_proxy_in_camera_playback=True,
        )
        self.assertFalse(pb.valid)
        self.assertFalse(pb.proxy_in_camera_playback_permitted)

        chunk_on_fx3 = verify_rec_media_autoswitch_proxy_vault_guard(
            claimed_fx3_supports_chunk_proxy_or_xdroot=True,
        )
        self.assertFalse(chunk_on_fx3.valid)
        self.assertEqual(chunk_on_fx3.block_errno, EOPNOTSUPP_ERRNO_PHASE317)

    def test_37_g139_fx6_simul_rec_and_chunk_proxy_exclusions_enforced(self) -> None:
        self.assertEqual(FX6_PROXY_SUB_PATH_G139, "/XDROOT/Sub")
        self.assertEqual(FX6_PROXY_CHUNK_DURATIONS_G139, ("30s", "1min", "2min"))

        bad_simul = verify_rec_media_autoswitch_proxy_vault_guard(
            target_model=FX6_MODEL_NAME_PHASE317,
            fx6_simul_rec_enabled=True,
            fx6_proxy_rec_enabled=True,
        )
        self.assertFalse(bad_simul.valid)
        self.assertFalse(bad_simul.fx6_simul_rec_proxy_exclusion_ok)

        bad_chunk_relay = verify_rec_media_autoswitch_proxy_vault_guard(
            target_model=FX6_MODEL_NAME_PHASE317,
            fx6_chunk_proxy_enabled=True,
            fx6_relay_rec_enabled=True,
        )
        self.assertFalse(bad_chunk_relay.valid)

        ok_fx6 = verify_rec_media_autoswitch_proxy_vault_guard(
            target_model=FX6_MODEL_NAME_PHASE317,
            fx6_simul_rec_enabled=True,
            fx6_proxy_rec_enabled=False,
            fx6_chunk_proxy_enabled=False,
        )
        self.assertTrue(ok_fx6.valid)

    def test_38_g139_matrix_256_states_zero_slot1_writes(self) -> None:
        m = compute_rec_media_autoswitch_proxy_matrix()
        self.assertEqual(m["states_checked"], 256)
        self.assertGreater(m["slot1_vault_blocked_count"], 0)
        self.assertGreater(m["overflow_trap_count"], 0)
        self.assertGreater(m["proxy_fr_blocked_count"], 0)
        self.assertGreater(m["vpg_cfe_required_count"], 0)

    def test_39_g139_invalid_enums_and_identity_fail_closed(self) -> None:
        for bad_kw in (
            {"body_model_name": "ILCE-7SM3"},
            {"body_model_id": 0xDEADBEEF},
            {"help_guide_code": "ilc/9999"},
            {"firmware_version": "1.00-invalid"},
            {"target_model": "ILME-FX9"},
            {"reset_action": "FactoryBoom"},
            {"shoot_mode": "Timelapse"},
            {"requested_recording_media": "Slot 3"},
            {"requested_auto_switch_media": "Maybe"},
            {"requested_proxy_recording": "Auto"},
            {"slot1_fs": "NTFS"},
            {"slot2_fs": "APFS"},
            {"media_card_type": "MemoryStick"},
            {"movie_file_format": "ProResRAW"},
            {"rec_frame_rate": "48p"},
            {"sq_frame_rate": "1000fps"},
            {"bitrate_mbps": 0},
            {"proxy_file_format": "MJPEG"},
            {"proxy_record_setting": "999M"},
        ):
            r = verify_rec_media_autoswitch_proxy_vault_guard(**bad_kw)
            self.assertFalse(r.valid, msg=f"bad_kw={bad_kw}")
            self.assertIn(STATUS_BLOCKED_G139_TELEMETRY_INVALID, r.violation_codes)

    def test_40_g139_evaluate_persistent_emmc_write_blocked_and_resolver_dict(self) -> None:
        v, r = evaluate_g139_rec_media_autoswitch_proxy_vault_guard(
            force_clean_room=True,
            request_persistent_emmc_writes=True,
        )
        self.assertFalse(v.passed)
        self.assertFalse(r.valid)
        self.assertIn(STATUS_BLOCKED_PERSISTENT_EMMC_WRITE, r.violation_codes)
        self.assertFalse(r.persistent_emmc_writes_authorized)

        d = resolve_fx3_rec_media_autoswitch_proxy_state()
        self.assertTrue(d["valid"])
        self.assertEqual(d["slot1_data_sector_writes"], 0)


class TestGateG140CreatorsCloudZeroRfAndMyMenu42(unittest.TestCase):
    def test_41_g140_default_zero_rf_and_42slot_passes(self) -> None:
        res = verify_creators_cloud_zerorf_mymenu42_guard()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_VERIFIED_G140)
        self.assertTrue(res.zero_rf_enforced)
        self.assertEqual(res.rf_packets_transmitted, 0)
        self.assertFalse(res.ble_power_off_energized)
        self.assertEqual(res.mymenu_exact_slots, 42)
        self.assertEqual(res.fx6_user_menu_max_items, 20)
        self.assertEqual(res.matrix_states_checked, 256)

    def test_42_g140_uxc_resid16_anchors_exact(self) -> None:
        self.assertEqual(CREATORS_CLOUD_G_UXC_RESID16_G140, 0x62B5)
        self.assertEqual(CNCT_WHILE_POWER_OFF_F_UXC_RESID16_G140, 0x6AB3)
        self.assertEqual(ALWAYS_CONNECTED_F_UXC_RESID16_G140, 0x6833)
        self.assertEqual(MY_MENU_G_UXC_RESID16_G140, 0x6232)
        self.assertEqual(DISPLAY_FROM_MY_MENU_F_UXC_RESID16_G140, 0x64F6)

    def test_43_g140_creators_cloud_survives_initialize_unless_explicit_signout(self) -> None:
        survived = verify_creators_cloud_zerorf_mymenu42_guard(
            reset_action=RESET_ACTION_INITIALIZE_PHASE317,
            requested_cloud_connection="On",
            cloud_account_signout_requested=False,
        )
        self.assertTrue(survived.valid)
        self.assertTrue(survived.cloud_survived_initialize)
        self.assertEqual(survived.effective_cloud_connection, "On")

        false_assumption = verify_creators_cloud_zerorf_mymenu42_guard(
            reset_action=RESET_ACTION_INITIALIZE_PHASE317,
            requested_cloud_connection="On",
            cloud_account_signout_requested=False,
            assume_initialize_wipes_cloud_account=True,
        )
        self.assertFalse(false_assumption.valid)
        self.assertIn(
            STATUS_BLOCKED_G140_CLOUD_PERSISTENCE_OR_FTP_EXCLUSION_VIOLATION,
            false_assumption.violation_codes,
        )

        signed_out = verify_creators_cloud_zerorf_mymenu42_guard(
            reset_action=RESET_ACTION_INITIALIZE_PHASE317,
            requested_cloud_connection="On",
            cloud_account_signout_requested=True,
            assume_initialize_wipes_cloud_account=True,
        )
        self.assertTrue(signed_out.valid)
        self.assertFalse(signed_out.cloud_survived_initialize)
        self.assertEqual(signed_out.effective_cloud_connection, "Off")

    def test_44_g140_cloud_connection_on_ftp_off_mutual_exclusion(self) -> None:
        conflict = verify_creators_cloud_zerorf_mymenu42_guard(
            requested_cloud_connection="On",
            ftp_transfer_enabled=True,
        )
        self.assertFalse(conflict.valid)
        self.assertFalse(conflict.cloud_ftp_mutual_exclusion_ok)
        self.assertIn(
            STATUS_BLOCKED_G140_CLOUD_PERSISTENCE_OR_FTP_EXCLUSION_VIOLATION,
            conflict.violation_codes,
        )

    def test_45_g140_c3_portal_profiles_and_clip_flag_filters_verified(self) -> None:
        self.assertEqual(
            ALLOWED_C3_PORTAL_PROFILES_G140, ("None", "Cloud(Private)", "Cloud(Share)")
        )
        self.assertEqual(ALLOWED_CLIP_FLAGS_G140, ("NONE", "OK", "NG", "KEEP"))
        for c3 in ALLOWED_C3_PORTAL_PROFILES_G140:
            for flag in ALLOWED_CLIP_FLAGS_G140:
                res = verify_creators_cloud_zerorf_mymenu42_guard(
                    c3_portal_profile=c3,
                    clip_flag_filter=flag,
                )
                self.assertTrue(res.valid)
                self.assertEqual(res.c3_portal_profile, c3)
                self.assertEqual(res.clip_flag_filter, flag)

    def test_46_g140_cnct_while_power_off_ble_energized_at_switch_off_violates_zero_rf(self) -> None:
        hazard = verify_creators_cloud_zerorf_mymenu42_guard(
            physical_power_switch="OFF",
            requested_airplane_mode="Off",
            requested_cnct_while_power_off="On",
            requested_bluetooth_function="On",
            bluetooth_paired=True,
            zero_rf_bench_mode=True,
        )
        self.assertFalse(hazard.valid)
        self.assertTrue(hazard.ble_power_off_energized)
        self.assertFalse(hazard.zero_rf_enforced)
        self.assertGreater(hazard.rf_packets_transmitted, 0)
        self.assertIn(
            STATUS_BLOCKED_G140_CNCT_WHILE_POWER_OFF_ZERO_RF_VIOLATION,
            hazard.violation_codes,
        )

    def test_47_g140_airplane_alone_without_cnct_power_off_still_fails_if_cnct_on_checked_or_ble_active(self) -> None:
        # Both Airplane=On AND Cnct. while Power OFF=Off must be explicitly set
        partial = verify_creators_cloud_zerorf_mymenu42_guard(
            physical_power_switch="OFF",
            requested_airplane_mode="On",
            requested_cnct_while_power_off="On",
            bluetooth_paired=True,
            zero_rf_bench_mode=True,
        )
        self.assertFalse(partial.valid)
        self.assertFalse(partial.zero_rf_enforced)

    def test_48_g140_cnct_while_power_off_survives_cam_reset_and_clears_on_net_reset(self) -> None:
        cam_rst = verify_creators_cloud_zerorf_mymenu42_guard(
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE317,
            requested_airplane_mode="Off",
            requested_cnct_while_power_off="On",
            bluetooth_paired=True,
            zero_rf_bench_mode=True,
        )
        self.assertFalse(cam_rst.valid)
        self.assertTrue(cam_rst.cnct_while_power_off_survived_cam_reset)
        self.assertEqual(cam_rst.effective_cnct_while_power_off, "On")
        self.assertTrue(cam_rst.ble_power_off_energized)

        net_rst = verify_creators_cloud_zerorf_mymenu42_guard(
            reset_action=RESET_ACTION_RESET_NETWORK_SET_PHASE317,
            requested_airplane_mode="On",
            requested_cnct_while_power_off="On",
            bluetooth_paired=True,
            zero_rf_bench_mode=True,
        )
        self.assertTrue(net_rst.valid)
        self.assertEqual(net_rst.effective_cnct_while_power_off, "Off")
        self.assertFalse(net_rst.ble_power_off_energized)
        self.assertEqual(net_rst.rf_packets_transmitted, 0)

    def test_49_g140_fx6_bluetooth_absent_rejects_claimed_ble_power_off_eopnotsupp(self) -> None:
        bad = verify_creators_cloud_zerorf_mymenu42_guard(
            target_model=FX6_MODEL_NAME_PHASE317,
            claimed_fx6_has_bluetooth_cnct_power_off=True,
        )
        self.assertFalse(bad.valid)
        self.assertTrue(bad.fx6_bluetooth_absent)
        self.assertEqual(bad.block_errno, EOPNOTSUPP_ERRNO_PHASE317)

    def test_50_g140_sc_tc_localization_defect_flag_tracked(self) -> None:
        res = verify_creators_cloud_zerorf_mymenu42_guard()
        self.assertTrue(res.cnct_while_power_off_g_0x6476_sc_tc_defect_known)

    def test_51_g140_fx3_mymenu_exact_42_slots_6x7_and_rejects_30_36_myths(self) -> None:
        self.assertEqual(FX3_MYMENU_GROUP_MIN_G140, 1)
        self.assertEqual(FX3_MYMENU_GROUP_MAX_G140, 6)
        self.assertEqual(FX3_MYMENU_LIST_MIN_G140, 0)
        self.assertEqual(FX3_MYMENU_LIST_MAX_G140, 6)
        self.assertEqual(FX3_MYMENU_EXACT_SLOTS_G140, 42)

        for grp in range(1, 7):
            for lst in range(0, 7):
                r = verify_creators_cloud_zerorf_mymenu42_guard(
                    mymenu_group=grp,
                    mymenu_list=lst,
                )
                self.assertTrue(r.valid)
                self.assertEqual(r.mymenu_slot_index, (grp - 1) * 7 + lst)

        for myth_cap in (30, 36):
            bad = verify_creators_cloud_zerorf_mymenu42_guard(
                claimed_fx3_mymenu_capacity=myth_cap,
            )
            self.assertFalse(bad.valid)
            self.assertEqual(bad.block_errno, EINVAL_ERRNO_PHASE317)

    def test_52_g140_fx3_mymenu_out_of_range_slot_ge_42_rejected_einval(self) -> None:
        for kw in (
            {"mymenu_slot_index": 42},
            {"mymenu_slot_index": -1},
            {"mymenu_group": 0, "mymenu_list": 0},
            {"mymenu_group": 7, "mymenu_list": 0},
            {"mymenu_group": 1, "mymenu_list": 7},
        ):
            r = verify_creators_cloud_zerorf_mymenu42_guard(**kw)
            self.assertFalse(r.valid, msg=f"kw={kw}")
            self.assertIn(
                STATUS_BLOCKED_G140_MYMENU_42SLOT_OR_PLAYBACK_TAB_VIOLATION,
                r.violation_codes,
            )
            self.assertEqual(r.block_errno, EINVAL_ERRNO_PHASE317)

    def test_53_g140_fx3_mymenu_playback_tab_registration_rejected_einval(self) -> None:
        bad = verify_creators_cloud_zerorf_mymenu42_guard(
            mymenu_op="Add Item",
            mymenu_item_tab="Playback",
        )
        self.assertFalse(bad.valid)
        self.assertTrue(bad.playback_tab_registration_rejected)
        self.assertEqual(bad.block_errno, EINVAL_ERRNO_PHASE317)

        for tab in ALLOWED_MENU_TABS_G140:
            if tab in FX3_MYMENU_FORBIDDEN_TABS_G140:
                continue
            ok = verify_creators_cloud_zerorf_mymenu42_guard(
                mymenu_op="Add Item",
                mymenu_item_tab=tab,
            )
            self.assertTrue(ok.valid, msg=f"tab={tab}")

    def test_54_g140_mymenu_ops_persistence_cam_reset_vs_initialize_delete_all(self) -> None:
        self.assertEqual(
            MYMENU_OPS_G140,
            (
                "None",
                "Add Item",
                "Sort Item",
                "Delete Item",
                "Delete Page",
                "Delete All",
                "Display From My Menu",
            ),
        )
        cam_rst = verify_creators_cloud_zerorf_mymenu42_guard(
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE317,
            mymenu_op="Display From My Menu",
            requested_display_from_mymenu="On",
        )
        self.assertTrue(cam_rst.valid)
        self.assertTrue(cam_rst.mymenu_survived_cam_reset)
        self.assertEqual(cam_rst.effective_display_from_mymenu, "On")

        for clearing_kw in (
            {"reset_action": RESET_ACTION_INITIALIZE_PHASE317, "mymenu_op": "Add Item"},
            {"reset_action": RESET_ACTION_NONE_PHASE317, "mymenu_op": "Delete All"},
        ):
            cleared = verify_creators_cloud_zerorf_mymenu42_guard(
                requested_display_from_mymenu="On",
                **clearing_kw,
            )
            self.assertTrue(cleared.valid)
            self.assertEqual(cleared.effective_display_from_mymenu, "Off")

    def test_55_g140_camset_export_to_slot1_vault_blocked_erofs(self) -> None:
        slot1_bad = verify_creators_cloud_zerorf_mymenu42_guard(
            camset_export_requested=True,
            camset_slot=REC_MEDIA_SLOT_1_G139,
            slot_1_contains_tier0_vault=True,
        )
        self.assertFalse(slot1_bad.valid)
        self.assertTrue(slot1_bad.slot1_camset_vault_blocked)
        self.assertEqual(slot1_bad.block_errno, EROFS_ERRNO_PHASE317)
        self.assertEqual(slot1_bad.slot1_data_sector_writes, 0)

        slot2_ok = verify_creators_cloud_zerorf_mymenu42_guard(
            camset_export_requested=True,
            camset_slot=REC_MEDIA_SLOT_2_G139,
            slot_1_contains_tier0_vault=True,
        )
        self.assertTrue(slot2_ok.valid)
        self.assertFalse(slot2_ok.slot1_camset_vault_blocked)

    def test_56_g140_fx6_20_item_user_menu_and_rental_lock_vs_fx3_eopnotsupp(self) -> None:
        self.assertEqual(FX6_USER_MENU_MAX_ITEMS_G140, 20)
        self.assertEqual(FX6_RENTAL_LOCK_CHORD_G140, "Multi-Function Dial + MENU")

        fx6_ok = verify_creators_cloud_zerorf_mymenu42_guard(
            target_model=FX6_MODEL_NAME_PHASE317,
            fx6_user_menu_only=True,
            fx6_user_menu_with_lock=True,
            fx6_user_menu_lock_pin="4321",
            fx6_user_menu_item_count=20,
        )
        self.assertTrue(fx6_ok.valid)
        self.assertTrue(fx6_ok.fx6_user_menu_lock_excluded_from_all_file)

        fx3_rejected = verify_creators_cloud_zerorf_mymenu42_guard(
            target_model=FX3_MODEL_NAME_PHASE317,
            fx6_user_menu_with_lock=True,
        )
        self.assertFalse(fx3_rejected.valid)
        self.assertTrue(fx3_rejected.fx6_rental_lock_rejected_on_fx3)
        self.assertEqual(fx3_rejected.block_errno, EOPNOTSUPP_ERRNO_PHASE317)

    def test_57_g140_fx6_bad_pin_over_20_items_or_all_file_leak_rejected(self) -> None:
        for bad_kw in (
            {"target_model": FX6_MODEL_NAME_PHASE317, "fx6_user_menu_lock_pin": "123"},
            {"target_model": FX6_MODEL_NAME_PHASE317, "fx6_user_menu_lock_pin": "ABCD"},
            {"target_model": FX6_MODEL_NAME_PHASE317, "fx6_user_menu_item_count": 21},
            {
                "target_model": FX6_MODEL_NAME_PHASE317,
                "claimed_fx6_user_menu_lock_exports_to_all_file": True,
            },
        ):
            r = verify_creators_cloud_zerorf_mymenu42_guard(**bad_kw)
            self.assertFalse(r.valid, msg=f"bad_kw={bad_kw}")
            self.assertEqual(r.block_errno, EINVAL_ERRNO_PHASE317)

    def test_58_g140_matrix_256_states_verified(self) -> None:
        m = compute_creators_cloud_zerorf_mymenu_matrix()
        self.assertEqual(m["states_checked"], 256)
        self.assertGreater(m["cloud_survived_init_count"], 0)
        self.assertGreater(m["ble_power_off_hazard_count"], 0)
        self.assertGreater(m["zero_rf_clean_count"], 0)
        self.assertGreater(m["slot1_camset_vault_blocked_count"], 0)

    def test_59_g140_invalid_enums_and_identity_fail_closed(self) -> None:
        for bad_kw in (
            {"body_model_name": "ILCE-7M4"},
            {"body_model_id": 0x11223344},
            {"help_guide_code": "ilc/0000"},
            {"firmware_version": "bad"},
            {"target_model": "FX9"},
            {"reset_action": "WipeAll"},
            {"requested_cloud_connection": "Maybe"},
            {"requested_airplane_mode": "Maybe"},
            {"requested_cnct_while_power_off": "Maybe"},
            {"requested_bluetooth_function": "Maybe"},
            {"requested_display_from_mymenu": "Maybe"},
            {"camset_slot": REC_MEDIA_SIMULT_G139},
            {"physical_power_switch": "SLEEP"},
            {"c3_portal_profile": "PublicBucket"},
            {"clip_flag_filter": "STAR"},
            {"mymenu_op": "Destroy"},
            {"mymenu_item_tab": "Secret"},
        ):
            r = verify_creators_cloud_zerorf_mymenu42_guard(**bad_kw)
            self.assertFalse(r.valid, msg=f"bad_kw={bad_kw}")
            self.assertIn(STATUS_BLOCKED_G140_TELEMETRY_INVALID, r.violation_codes)

    def test_60_g140_evaluate_persistent_emmc_write_blocked_and_resolver_dict(self) -> None:
        v, r = evaluate_g140_creators_cloud_zerorf_mymenu42_guard(
            force_clean_room=True,
            request_persistent_emmc_writes=True,
        )
        self.assertFalse(v.passed)
        self.assertFalse(r.valid)
        self.assertIn(STATUS_BLOCKED_PERSISTENT_EMMC_WRITE, r.violation_codes)
        self.assertFalse(r.persistent_emmc_writes_authorized)

        d = resolve_fx3_creators_cloud_zerorf_mymenu_state()
        self.assertTrue(d["valid"])
        self.assertEqual(d["rf_packets_transmitted"], 0)


class TestUnified140GatePreflightAndCli(unittest.TestCase):
    def test_61_preflight_140_offline_137_of_140_and_redlines(self) -> None:
        rep = evaluate_140gate_preflight(force_clean_room=True)
        self.assertEqual(rep.schema, "realhw_140gate_preflight_v1")
        self.assertEqual(rep.schema_version, "realhw_140gate_preflight_v1")
        self.assertEqual(rep.status, "VERIFIED_137_OF_140_AWAITING_PHYSICAL_TIER0")
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(rep.offline_137_gates_verified)
        self.assertFalse(rep.all_140_gates_verified)
        self.assertTrue(rep.g13_to_g140_all_passed)
        self.assertTrue(rep.g139_to_g140_all_passed)
        self.assertEqual(rep.summary["total_gates"], 140)
        self.assertEqual(rep.summary["verified_gates"], 137)
        self.assertEqual(rep.summary["blocked_or_pending_gates"], 3)
        self.assertEqual(rep.summary["g01_to_g12_verified"], 9)
        self.assertEqual(rep.summary["g13_to_g138_verified"], 126)
        self.assertEqual(rep.summary["g139_to_g140_verified"], 2)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.hardware_live_attachment_authorized)
        self.assertFalse(rep.cross_model_flash_authorized)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertEqual(rep.usb_packets_transmitted, 0)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_62_preflight_140_dry_run_all_140_of_140_verified(self) -> None:
        rep = evaluate_140gate_preflight(force_clean_room=True, simulate_bench_dry_run=True)
        self.assertEqual(rep.status, "VERIFIED_ALL_140_GATES_DRY_RUN_SIMULATED_BACKUP")
        self.assertTrue(rep.dry_run_rehearsal_only)
        self.assertTrue(rep.offline_137_gates_verified)
        self.assertTrue(rep.all_140_gates_verified)
        self.assertEqual(rep.summary["verified_gates"], 140)
        self.assertEqual(rep.summary["blocked_or_pending_gates"], 0)
        self.assertEqual(rep.summary["g01_to_g12_verified"], 12)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.hardware_live_attachment_authorized)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_63_preflight_140_aliases_identical(self) -> None:
        r1 = evaluate_140_master_safety_gates(force_clean_room=True, dry_run_simulated=True)
        r2 = run_140_gate_preflight(force_clean_room=True, dry_run_simulated_backup=True)
        self.assertEqual(r1.schema_version, REALHW_140GATE_PREFLIGHT_SCHEMA)
        self.assertEqual(r2.schema_version, REALHW_140GATE_PREFLIGHT_SCHEMA)
        self.assertTrue(r1.all_140_gates_verified)
        self.assertTrue(r2.all_140_gates_verified)

    def test_64_preflight_140_gate_ids_g01_through_g140_ordered(self) -> None:
        stub = _build_stub_138_report(dry_run=False, all_g13_138_ok=True)
        rep = evaluate_140gate_preflight(
            force_clean_room=True,
            master_138_override=stub,
        )
        gate_ids = [g["gate_id"] for g in rep.gates]
        self.assertEqual(len(gate_ids), 140)
        for idx in range(1, 141):
            self.assertTrue(
                gate_ids[idx - 1].startswith(f"G{idx:02d}"),
                msg=f"Gate at index {idx - 1} was {gate_ids[idx - 1]}",
            )
        self.assertEqual(gate_ids[-2:], ["G139", "G140"])

    def test_65_preflight_140_persistent_emmc_write_request_blocks(self) -> None:
        stub = _build_stub_138_report(dry_run=True, all_g13_138_ok=True)
        rep = evaluate_140gate_preflight(
            force_clean_room=True,
            simulate_bench_dry_run=True,
            request_persistent_emmc_writes=True,
            master_138_override=stub,
        )
        self.assertEqual(rep.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        self.assertFalse(rep.offline_137_gates_verified)
        self.assertFalse(rep.all_140_gates_verified)
        self.assertFalse(rep.h0_h1_trial_entry_allowed)

    def test_66_preflight_140_g139_fault_propagates_and_blocks(self) -> None:
        stub = _build_stub_138_report(dry_run=False, all_g13_138_ok=True)
        rep = evaluate_140gate_preflight(
            force_clean_room=True,
            master_138_override=stub,
            rec_media_autoswitch_proxy_kwargs={
                "requested_recording_media": REC_MEDIA_SLOT_2_G139,
                "requested_auto_switch_media": "On",
                "slot2_full_or_ejected": True,
                "slot_1_contains_tier0_vault": True,
            },
        )
        self.assertEqual(
            rep.status, STATUS_BLOCKED_G139_SLOT2_TO_SLOT1_OVERFLOW_OR_VAULT_VIOLATION
        )
        self.assertFalse(rep.g139_to_g140_all_passed)
        self.assertFalse(rep.offline_137_gates_verified)
        self.assertEqual(rep.summary["verified_gates"], 136)

    def test_67_preflight_140_g140_fault_propagates_and_blocks(self) -> None:
        stub = _build_stub_138_report(dry_run=False, all_g13_138_ok=True)
        rep = evaluate_140gate_preflight(
            force_clean_room=True,
            master_138_override=stub,
            creators_cloud_mymenu_kwargs={
                "requested_airplane_mode": "Off",
                "requested_cnct_while_power_off": "On",
                "bluetooth_paired": True,
                "zero_rf_bench_mode": True,
            },
        )
        self.assertEqual(
            rep.status, STATUS_BLOCKED_G140_CNCT_WHILE_POWER_OFF_ZERO_RF_VIOLATION
        )
        self.assertFalse(rep.g139_to_g140_all_passed)
        self.assertFalse(rep.offline_137_gates_verified)
        self.assertEqual(rep.summary["verified_gates"], 136)

    def test_68_preflight_140_m138_fault_propagates(self) -> None:
        bad_stub = _build_stub_138_report(dry_run=False, all_g13_138_ok=False)
        bad_stub = dataclasses.replace(
            bad_stub, status="BLOCKED_BY_MOCK_M138"
        )
        rep = evaluate_140gate_preflight(
            force_clean_room=True,
            master_138_override=bad_stub,
        )
        self.assertEqual(rep.status, "BLOCKED_BY_MOCK_M138")
        self.assertFalse(rep.g13_to_g140_all_passed)
        self.assertFalse(rep.offline_137_gates_verified)

    def test_69_forward_compatible_dynamic_auto_discovery_includes_140(self) -> None:
        eval_re = re.compile(r"^evaluate_(\d+)gate_preflight$")
        candidates = []
        for name in dir(fx3_safety):
            m = eval_re.match(name)
            if m:
                candidates.append((int(m.group(1)), name))
        candidates.sort()
        self.assertIn((140, "evaluate_140gate_preflight"), candidates)
        highest = candidates[-1]
        self.assertGreaterEqual(highest[0], 140)

    def test_70_milestone311_compatible_schema_and_preflight_summary(self) -> None:
        rep = evaluate_140gate_preflight(force_clean_room=True)
        self.assertEqual(rep.schema, "realhw_140gate_preflight_v1")
        self.assertEqual(rep.schema_version, "realhw_140gate_preflight_v1")
        self.assertEqual(rep.summary["total_gates"], 140)
        self.assertEqual(rep.summary["verified_gates"], 137)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)
        self.assertEqual(rep.usb_packets_transmitted, 0)

    def test_71_cli_verify_140_gates_plain_text_and_json_summary(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cli_main(["verify-140-gates", "--clean-room"])
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("verified=137/140", out)
        self.assertIn("raw_firmware_bytes_leaked=0", out)
        self.assertIn("overall_ready_for_hardware_attach=False", out)

        buf_json = io.StringIO()
        with contextlib.redirect_stdout(buf_json):
            rc_json = cli_main(
                ["verify-140-gates", "--clean-room", "--simulate-bench-dry-run", "--summary", "--json"]
            )
        self.assertEqual(rc_json, 0)
        payload = json.loads(buf_json.getvalue())
        self.assertEqual(payload["schema_version"], "realhw_140gate_preflight_v1")
        self.assertEqual(payload["summary"]["verified_gates"], 140)
        self.assertEqual(payload["g139_status"], STATUS_VERIFIED_G139)
        self.assertEqual(payload["g140_status"], STATUS_VERIFIED_G140)

    def test_72_cli_verify_140_gates_full_json_payload(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cli_main(
                ["verify-140-gates", "--clean-room", "--simulate-bench-dry-run", "--json"]
            )
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["schema"], REALHW_140GATE_PREFLIGHT_SCHEMA)
        self.assertEqual(payload["schema_version"], REALHW_140GATE_PREFLIGHT_SCHEMA)
        self.assertEqual(len(payload["gates"]), 140)
        self.assertEqual(payload["raw_firmware_bytes_leaked"], 0)
        self.assertFalse(payload["overall_ready_for_hardware_attach"])

    def test_73_cli_g139_and_g140_subcommands_plain_and_json(self) -> None:
        for cmd in (
            "verify-rec-media-autoswitch-proxy-vault-guard",
            "verify-g139-rec-media-autoswitch-proxy",
            "verify-creators-cloud-zerorf-mymenu42-guard",
            "verify-g140-creators-cloud-zerorf-mymenu",
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = cli_main([cmd, "--clean-room"])
            self.assertEqual(rc, 0)
            self.assertIn("valid=True", buf.getvalue())

            buf_j = io.StringIO()
            with contextlib.redirect_stdout(buf_j):
                rc_j = cli_main([cmd, "--clean-room", "--summary", "--json"])
            self.assertEqual(rc_j, 0)
            p = json.loads(buf_j.getvalue())
            self.assertTrue(p["valid"])
            self.assertEqual(p["raw_firmware_bytes_leaked"], 0)

    def test_74_standalone_guard_cli_main_all_modes(self) -> None:
        for argv in (
            ["--clean-room", "--gate", "g139", "--json", "--summary"],
            ["--clean-room", "--gate", "g140", "--json", "--summary"],
            ["--clean-room", "--gate", "140", "--simulate-bench-dry-run", "--json", "--summary"],
            ["--clean-room", "--gate", "140"],
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = guard_cli_main(argv)
            self.assertEqual(rc, 0)
            self.assertTrue(buf.getvalue().strip())

    def test_75_cli_help_percent_safety_no_value_error(self) -> None:
        for argv in (
            ["verify-rec-media-autoswitch-proxy-vault-guard", "--help"],
            ["verify-creators-cloud-zerorf-mymenu42-guard", "--help"],
            ["verify-140-gates", "--help"],
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                with self.assertRaises(SystemExit) as cm:
                    cli_main(argv)
            self.assertEqual(cm.exception.code, 0)
            self.assertTrue(len(buf.getvalue()) > 20)

        buf_g = io.StringIO()
        with contextlib.redirect_stdout(buf_g):
            with self.assertRaises(SystemExit) as cm:
                guard_cli_main(["--help"])
        self.assertEqual(cm.exception.code, 0)

    def test_76_g139_and_g140_donor_mode_consistent_with_clean_room(self) -> None:
        if os.environ.get(ENV_FORCE_CLEAN_ROOM) or os.environ.get(ENV_CLEAN_ROOM_TEST_PHASE317):
            self.skipTest("Forced clean-room active")
        if not _donors_available_here():
            self.skipTest("Donor binaries absent")
        rep_donor = evaluate_140gate_preflight(force_clean_room=False)
        rep_clean = evaluate_140gate_preflight(force_clean_room=True)
        self.assertEqual(rep_donor.verification_mode, "LOCAL_DONOR_O_RDONLY")
        self.assertEqual(rep_clean.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(
            rep_donor.summary["verified_gates"], rep_clean.summary["verified_gates"]
        )
        self.assertEqual(rep_donor.raw_firmware_bytes_leaked, 0)

    def test_77_g139_xavc_hs_4k_card_speed_tiers_complete(self) -> None:
        c10_ok = verify_rec_media_autoswitch_proxy_vault_guard(
            movie_file_format=MOVIE_FORMAT_XAVC_HS_4K_G139,
            bitrate_mbps=50,
            media_card_type=CARD_SDXC_CLASS10_G139,
        )
        self.assertTrue(c10_ok.valid)

        v30_bad_150m_is_ok = verify_rec_media_autoswitch_proxy_vault_guard(
            movie_file_format=MOVIE_FORMAT_XAVC_HS_4K_G139,
            bitrate_mbps=150,
            media_card_type=CARD_SDXC_U3_V30_G139,
        )
        self.assertTrue(v30_bad_150m_is_ok.valid)

        c10_bad_150m = verify_rec_media_autoswitch_proxy_vault_guard(
            movie_file_format=MOVIE_FORMAT_XAVC_HS_4K_G139,
            bitrate_mbps=150,
            media_card_type=CARD_SDXC_CLASS10_G139,
        )
        self.assertFalse(c10_bad_150m.valid)

    def test_78_g139_sq_high_fps_hs_4k_requires_v90_plus(self) -> None:
        v60_bad = verify_rec_media_autoswitch_proxy_vault_guard(
            shoot_mode=SHOOT_MODE_SQ_PHASE317,
            movie_file_format=MOVIE_FORMAT_XAVC_HS_4K_G139,
            sq_frame_rate="120fps",
            bitrate_mbps=280,
            media_card_type=CARD_SDXC_V60_G139,
        )
        self.assertFalse(v60_bad.valid)

        v90_ok = verify_rec_media_autoswitch_proxy_vault_guard(
            shoot_mode=SHOOT_MODE_SQ_PHASE317,
            movie_file_format=MOVIE_FORMAT_XAVC_HS_4K_G139,
            sq_frame_rate="120fps",
            bitrate_mbps=280,
            media_card_type=CARD_SDXC_V90_G139,
        )
        self.assertTrue(v90_ok.valid)

    def test_79_g139_card_speed_rank_monotonicity(self) -> None:
        self.assertLess(
            CARD_SPEED_RANK_G139[CARD_SDXC_CLASS10_G139],
            CARD_SPEED_RANK_G139[CARD_SDXC_U3_V30_G139],
        )
        self.assertLess(
            CARD_SPEED_RANK_G139[CARD_SDXC_U3_V30_G139],
            CARD_SPEED_RANK_G139[CARD_SDXC_V60_G139],
        )
        self.assertLess(
            CARD_SPEED_RANK_G139[CARD_SDXC_V60_G139],
            CARD_SPEED_RANK_G139[CARD_SDXC_V90_G139],
        )
        self.assertLess(
            CARD_SPEED_RANK_G139[CARD_SDXC_V90_G139],
            CARD_SPEED_RANK_G139[CARD_CFEXPRESS_TYPE_A_VPG200_G139],
        )
        self.assertLess(
            CARD_SPEED_RANK_G139[CARD_CFEXPRESS_TYPE_A_VPG200_G139],
            CARD_SPEED_RANK_G139[CARD_CFEXPRESS_TYPE_A_VPG400_G139],
        )

    def test_80_g139_proxy_xavc_hs_hd_9m_10bit_valid(self) -> None:
        res = verify_rec_media_autoswitch_proxy_vault_guard(
            requested_proxy_recording="On",
            proxy_file_format=PROXY_FORMAT_XAVC_HS_HD_G139,
            proxy_record_setting=PROXY_SETTING_9M_10BIT_G139,
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.proxy_bitrate_mbps, 9)
        self.assertEqual(res.proxy_bit_depth, 10)
        self.assertEqual(res.proxy_codec, "HEVC/H.265")

    def test_81_g139_movie_xavc_si_600m_with_proxy_on_requires_cfexpress_type_a(self) -> None:
        v90_bad = verify_rec_media_autoswitch_proxy_vault_guard(
            shoot_mode=SHOOT_MODE_MOVIE_PHASE317,
            movie_file_format=MOVIE_FORMAT_XAVC_S_I_4K_G139,
            rec_frame_rate="59.94p",
            bitrate_mbps=600,
            media_card_type=CARD_SDXC_V90_G139,
            requested_proxy_recording="On",
        )
        self.assertFalse(v90_bad.valid)
        self.assertTrue(v90_bad.vpg200_uxc_0xe228_required)
        self.assertTrue(v90_bad.vpg400_uxc_0xe224_threshold_triggered)

        vpg200_ok = verify_rec_media_autoswitch_proxy_vault_guard(
            shoot_mode=SHOOT_MODE_MOVIE_PHASE317,
            movie_file_format=MOVIE_FORMAT_XAVC_S_I_4K_G139,
            rec_frame_rate="59.94p",
            bitrate_mbps=600,
            media_card_type=CARD_CFEXPRESS_TYPE_A_VPG200_G139,
            requested_proxy_recording="On",
        )
        self.assertTrue(vpg200_ok.valid)

    def test_82_g139_network_reset_preserves_rec_media_and_auto_switch(self) -> None:
        res = verify_rec_media_autoswitch_proxy_vault_guard(
            reset_action=RESET_ACTION_RESET_NETWORK_SET_PHASE317,
            requested_recording_media=REC_MEDIA_SLOT_2_G139,
            requested_auto_switch_media="Off",
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.effective_recording_media, REC_MEDIA_SLOT_2_G139)
        self.assertEqual(res.effective_auto_switch_media, "Off")

    def test_83_g140_cloud_survives_camera_settings_reset_and_net_reset(self) -> None:
        for rst in (
            RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE317,
            RESET_ACTION_RESET_NETWORK_SET_PHASE317,
        ):
            r = verify_creators_cloud_zerorf_mymenu42_guard(
                reset_action=rst,
                requested_cloud_connection="On",
            )
            self.assertTrue(r.valid)
            self.assertEqual(r.effective_cloud_connection, "On")
            self.assertEqual(
                r.cloud_survived_cam_reset,
                rst == RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE317,
            )

    def test_84_g140_unpaired_bluetooth_does_not_energize_ble_on_power_off(self) -> None:
        res = verify_creators_cloud_zerorf_mymenu42_guard(
            physical_power_switch="OFF",
            requested_airplane_mode="On",
            requested_cnct_while_power_off="On",
            bluetooth_paired=False,
            zero_rf_bench_mode=True,
        )
        self.assertTrue(res.valid)
        self.assertFalse(res.ble_power_off_energized)
        self.assertEqual(res.effective_cnct_while_power_off, "Off")
        self.assertEqual(res.rf_packets_transmitted, 0)

    def test_85_g140_zero_rf_bench_mode_disabled_still_tracks_ble_packets(self) -> None:
        res = verify_creators_cloud_zerorf_mymenu42_guard(
            physical_power_switch="OFF",
            requested_airplane_mode="Off",
            requested_cnct_while_power_off="On",
            requested_bluetooth_function="On",
            bluetooth_paired=True,
            zero_rf_bench_mode=False,
        )
        self.assertTrue(res.valid)
        self.assertTrue(res.ble_power_off_energized)
        self.assertFalse(res.zero_rf_enforced)
        self.assertGreater(res.rf_packets_transmitted, 0)

    def test_86_g140_non_bool_int_guard_rejects_booleans_for_mymenu_indices(self) -> None:
        for bad_val in (True, False, "1"):
            r = verify_creators_cloud_zerorf_mymenu42_guard(
                mymenu_group=bad_val,  # type: ignore[arg-type]
            )
            self.assertFalse(r.valid)

    def test_87_shared_model_identity_and_errno_constants(self) -> None:
        self.assertEqual(FX3_MODEL_NAME_PHASE317, "ILME-FX3")
        self.assertEqual(FX3_MODEL_ID_PHASE317, 0x39383232)
        self.assertEqual(FX3_HELP_GUIDE_CODE_PHASE317, "ilc/2210")
        self.assertEqual(FX3_DEFAULT_FW_VERSION_PHASE317, "7.02")
        self.assertEqual(FX6_MODEL_NAME_PHASE317, "ILME-FX6")
        self.assertEqual(FX6_PRODUCT_CODE_PHASE317, "PRODUCT_MODEL_CHAPLIN")
        self.assertEqual(FX6_DEFAULT_FW_VERSION_PHASE317, "6.01")
        self.assertEqual(EROFS_ERRNO_PHASE317, 30)
        self.assertEqual(EOPNOTSUPP_ERRNO_PHASE317, 95)
        self.assertEqual(EINVAL_ERRNO_PHASE317, 22)
        self.assertEqual(EBUSY_ERRNO_PHASE317, 16)
        self.assertEqual(ENODEV_ERRNO_PHASE317, 19)

    def test_88_g139_and_g140_allowed_enum_tuples_nonempty(self) -> None:
        self.assertEqual(
            ALLOWED_SHOOT_MODES_PHASE317,
            (SHOOT_MODE_STILL_PHASE317, SHOOT_MODE_MOVIE_PHASE317, SHOOT_MODE_SQ_PHASE317),
        )
        self.assertEqual(
            ALLOWED_RESET_ACTIONS_PHASE317,
            (
                RESET_ACTION_NONE_PHASE317,
                RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE317,
                RESET_ACTION_RESET_NETWORK_SET_PHASE317,
                RESET_ACTION_INITIALIZE_PHASE317,
            ),
        )
        self.assertEqual(len(ALLOWED_CARD_TYPES_G139), 7)
        self.assertEqual(len(ALLOWED_MOVIE_FILE_FORMATS_G139), 6)
        self.assertEqual(len(ALLOWED_PROXY_FILE_FORMATS_G139), 2)
        self.assertEqual(len(ALLOWED_PROXY_RECORD_SETTINGS_G139), 3)
        self.assertEqual(len(ALLOWED_REC_FRAME_RATES_G139), 8)
        self.assertEqual(len(ALLOWED_SQ_FRAME_RATES_G139), 14)
        self.assertEqual(len(ALLOWED_SLOT_FILESYSTEMS_G139), 2)
        self.assertEqual(ALLOWED_POWER_SWITCH_STATES_G140, ("ON", "OFF"))

    def test_89_g139_result_to_dict_serializes_json_cleanly(self) -> None:
        v, r = evaluate_g139_rec_media_autoswitch_proxy_vault_guard(force_clean_room=True)
        d = r.to_dict()
        encoded = json.dumps(d)
        self.assertIn("rec_media_autoswitch_proxy_vault_guard", encoded)
        self.assertEqual(v.gate_id, G139)

    def test_90_g140_result_to_dict_serializes_json_cleanly(self) -> None:
        v, r = evaluate_g140_creators_cloud_zerorf_mymenu42_guard(force_clean_room=True)
        d = r.to_dict()
        encoded = json.dumps(d)
        self.assertIn("creators_cloud_zerorf_mymenu42_guard", encoded)
        self.assertEqual(v.gate_id, G140)

    def test_91_master_140_report_nested_g_valid_and_zero_tx(self) -> None:
        rep = evaluate_140gate_preflight(force_clean_room=True)
        d = rep.to_dict()
        self.assertTrue(d["g139_result"]["valid"])
        self.assertTrue(d["g140_result"]["valid"])
        self.assertEqual(d["usb_packets_transmitted"], 0)
        self.assertEqual(d["raw_firmware_bytes_leaked"], 0)

    def test_92_preflight_140_real_full_evaluation_under_budget(self) -> None:
        t0 = time.perf_counter()
        rep = evaluate_140gate_preflight(force_clean_room=True, simulate_bench_dry_run=False)
        dt = time.perf_counter() - t0
        self.assertTrue(rep.offline_137_gates_verified)
        self.assertEqual(rep.summary["verified_gates"], 137)
        self.assertLess(dt, 10.0)


if __name__ == "__main__":
    unittest.main()
