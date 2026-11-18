"""Phase 313 (313th Phase Milestone, Wave-59, 138/138 Safety Gates) Dual-Mode Unit Tests (88 tests) for
`fx3_safety.realhw_big6_home_framing_interval_tc_ssh_fan_and_138gate_guard`:

- Gate `G137` (`GATE_G137_BIG6_HOME_ND_META_MANUAL_FRAMING_VS_AUTO_FRAMING_AND_INTERVAL_SHOOT_9999_SLOT1_VAULT_GUARD`):
  - Ver. 7.00+/7.02 `[BIG6]` (Home) screen requires `[Mode Settings] == Fixed/Variable`
    (`_f.uxc 0x7d0d`, `BKID_APP_setting_fps_fixed_variable_select`), enters via custom key
    `[HOME]` or `[Swipe Down]` (`26view_tp_button_01_for_big6`), maps exact 6 dynamic tiles
    (`FPS`, `ISO` vs `Base ISO+EI` via `update_big6_item_iso_ei`, `Shutter Speed/Angle`,
    `Aperture` vs manual `ND Filter` metadata via `Home Lower Left` `_f.uxc 0x7ce3` — zero
    physical `e-ND` actuator on FX3 vs real `e-ND` `1/4..1/128` on FX6!), `Picture Profile`
    vs `Select LUT`, `White Balance`, and never outputs to HDMI (`hdmi_big6_output_blocked=True`).
  - Validates active manual `[Framing Settings]` (`_f.uxc 0x7d18`: `Framing = Off/On`,
    `Recording / Streaming = Full/Crop`, `HDMI = Crop/Full`; disables `APS-C S35`; locks out
    during `>= 100p` HFR, active recording, or streaming) while rejecting dormant AI
    `[Auto Framing]` (`_f.uxc 0x6be6` / `0x79bc` -> `EOPNOTSUPP=95`; FX3 `appFw.so` hard-locks
    `TYPE_EFRAMING_SUPPORT_TYPE_MANUAL_ONLY` with `0` `AUTO_FRAMING_AFR` / `PTZAUTOFRAMING` hits).
  - CRITICAL VAULT FIREWALL: Still `[Interval Shoot Func.]` (`_f.uxc 0x7027`: 7 `Initialize`-only
    resettable parameters, up to `9,999` RAW/JPEG/HEIF still shots = up to `19,998` `DCIM` files
    + `AVF_INFO` rewrites; exits `BULB` to `30"`, disabled in `iAuto`) contrasted with FX6
    single-MXF `Project > Interval Rec` -> fail-closed `EROFS=30` / `EBUSY=16`
    (`slot1_data_sector_writes == 0`) whenever `Slot 1` holds a Tier-0 recovery vault!
- Gate `G138` (`GATE_G138_TC_MAKE_REGEN_HDMI_REC_CTRL_SSH_ACCESS_AUTHEN_AND_FAN_4MODE_3MODE_ZERO_MAX_GUARD`):
  - `[Time Code Make]` (`_f.uxc 0x6b79`: `Preset` / `Regenerate`, `Initialize`-only; rejecting
    FX6-only `Clock` mode on FX3 -> `EOPNOTSUPP=95`) forces `Rec Run` whenever `Regenerate`
    is selected (reading TC from `Slot 1` during `Simult. Recording`), whereas `VMC-BNCM1 EXT-LK`
    requires `Preset` + `Free Run`; HDMI `[REC Control]` requires `Movie` + `[Time Code Output] == On`
    (works in both `Rec. Media = On` and `Off(HDMI Only)`, restricted in `S&Q` / streaming) +
    `[4ch Audio Output]` (`CH1/CH2` vs `CH3/CH4`) vs FX6 `SDI/HDMI Remote I/F` & `Parallel Rec`.
  - Ver. 7.00+ `[Access Authen. Settings]` (`On` by default, survives `Camera Settings Reset`,
    resets to `On` via `Reset Network Set.` / `Initialize`) uses `SSH` (`MSGID_SSHD_START_CMD`,
    `sshd_start`, `SSH Host Key Fingerprint` `_g.uxc 0x610b`) + `PTP-IP` — rejecting non-existent
    `HTTP_DIGEST` / `BASIC_AUTH` / inbound `HTTPS` server auth myths (`EOPNOTSUPP=95`; `[Import Root
    Certificate]` `_f.uxc 0x7940` is outbound `FTPS`/`RTMPS`/`Cloud` client TLS only, with `Slot-1`
    protected via `EROFS=30`).
  - Busts the Fan Control `Max` myth across BOTH cameras: FX3 `[Fan Control]` exposes exact `4`
    modes (`Auto` / `Minimum` / `Off in Rec` / `Always Off`, `Initialize`-only) + `[Auto Power OFF Temp.]`
    (`Standard` / `High`), whereas FX6 `Technical > Fan Control` exposes exact `3` modes (`Auto` /
    `Minimum` / `Off in Rec`, keeping `Always Off` dormant -> `EOPNOTSUPP=95`) — rejecting
    non-existent `FAN_CONTROL_MAX` (`0` hits in both FX3 & FX6 `appFw.so` -> `EOPNOTSUPP=95`)!
- Unified `138`-Gate Milestone Master Preflight (`evaluate_138gate_preflight` / `verify-138-gates`):
  - `135/138` offline and `138/138` under `--simulate-bench-dry-run`, with all hardware
    write/attach redlines hard-locked `False` and `raw_firmware_bytes_leaked == 0`.
"""

from __future__ import annotations

import contextlib
import dataclasses
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

import fx3_safety
from fx3_safety.__main__ import main as cli_main
from fx3_safety.realhw_bright_mon_shotmark_usblan_bulb_dormant_and_136gate_guard import (
    Master136GateReport,
)
from fx3_safety.realhw_big6_home_framing_interval_tc_ssh_fan_and_138gate_guard import (
    ACCESS_AUTHEN_F_UXC_RESID16_G138,
    ALLOWED_4CH_AUDIO_OUTPUT_G138,
    ALLOWED_ACCESS_AUTHEN_TRANSPORTS_G138,
    ALLOWED_AE_TRACKING_SENSITIVITIES_G137,
    ALLOWED_AUTO_PWR_OFF_TEMP_MODES_G138,
    ALLOWED_BIG6_ENTRY_TRIGGERS_G137,
    ALLOWED_EXPOSURE_MODES_G137,
    ALLOWED_FRAMING_HDMI_MODES_G137,
    ALLOWED_FRAMING_REC_STREAM_MODES_G137,
    ALLOWED_FX3_TC_MAKE_MODES_G138,
    ALLOWED_FX6_SDI_HDMI_REC_CTRL_MODES_G138,
    ALLOWED_FX6_TC_MAKE_MODES_G138,
    ALLOWED_HOME_LOWER_LEFT_MODES_G137,
    ALLOWED_INTERVAL_SHUTTER_TYPES_G137,
    ALLOWED_INTERVAL_STILL_FORMATS_G137,
    ALLOWED_LOG_SHOOTING_MODES_G137,
    ALLOWED_MODE_SETTINGS_G137,
    ALLOWED_PASM_MODES_G137,
    ALLOWED_REC_MEDIA_DUR_HDMI_G138,
    ALLOWED_RECORDING_MEDIA_MODES_PHASE313,
    ALLOWED_RESET_ACTIONS_PHASE313,
    ALLOWED_SHOOT_MODES_PHASE313,
    ALLOWED_SHUTTER_MODES_G137,
    ALLOWED_TC_RUN_MODES_G138,
    AUDIO_4CH_CH1_CH2_G138,
    AUDIO_4CH_CH3_CH4_G138,
    AUTO_PWR_OFF_TEMP_HIGH_G138,
    AUTO_PWR_OFF_TEMP_STANDARD_G138,
    BIG6_ENTRY_HOME_KEY_G137,
    BIG6_ENTRY_NONE_G137,
    BIG6_ENTRY_SWIPE_DOWN_G137,
    BIG6_HOME_CUSTOM_KEY_F_UXC_RESID16_G137,
    BIG6_HOME_LOWER_LEFT_F_UXC_RESID16_G137,
    BIG6_MODE_SETTINGS_F_UXC_RESID16_G137,
    BIG6_SWIPE_DOWN_F_UXC_RESID16_G137,
    CROSS_MODEL_FLASH_AUTHORIZED,
    DEFAULT_REPO_ROOT,
    DONOR_CHECK_CI_MAX_SECONDS_PHASE313,
    DONOR_CHECK_MAX_SECONDS_PHASE313,
    DORMANT_AUTO_FRAMING_TRAPS_G137,
    EBUSY_ERRNO_PHASE313,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    ENV_CLEAN_ROOM_TEST_PHASE313,
    ENV_FORCE_CLEAN_ROOM,
    EOPNOTSUPP_ERRNO_PHASE313,
    EROFS_ERRNO_PHASE313,
    EXPOSURE_MODE_A_G137,
    EXPOSURE_MODE_INTELLIGENT_AUTO_G137,
    EXPOSURE_MODE_M_G137,
    EXPOSURE_MODE_P_G137,
    EXPOSURE_MODE_S_G137,
    FAN_CONTROL_ALWAYS_OFF_G138,
    FAN_CONTROL_AUTO_G138,
    FAN_CONTROL_MINIMUM_G138,
    FAN_CONTROL_OFF_IN_REC_G138,
    FORBIDDEN_FAN_MAX_TOKENS_G138,
    FORBIDDEN_HTTP_AUTH_MYTHS_G138,
    FRAMING_HDMI_CROP_G137,
    FRAMING_HDMI_FULL_G137,
    FRAMING_REC_STREAM_CROP_G137,
    FRAMING_REC_STREAM_FULL_G137,
    FRAMING_SETTINGS_F_UXC_RESID16_G137,
    FX3_BIG6_EXACT_6_TILES_LABELS_G137,
    FX3_DEFAULT_FW_VERSION_PHASE313,
    FX3_EXACT_4_FAN_MODES_G138,
    FX3_HELP_GUIDE_CODE_PHASE313,
    FX3_MODEL_ID_PHASE313,
    FX3_MODEL_NAME_PHASE313,
    FX6_DEFAULT_FW_VERSION_PHASE313,
    FX6_END_ND_OPTIONS_G137,
    FX6_EXACT_3_FAN_MODES_G138,
    FX6_MODEL_NAME_PHASE313,
    FX6_PARALLEL_REC_G138,
    FX6_PRODUCT_CODE_PHASE313,
    FX6_SDI_HDMI_REC_CTRL_OFF_G138,
    FX6_SDI_HDMI_REMOTE_IF_G138,
    G137,
    G137_GATE_CODE,
    G137_GATE_ID,
    G138,
    G138_GATE_CODE,
    G138_GATE_ID,
    HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    HDMI_4CH_AUDIO_OUTPUT_F_UXC_RESID16_G138,
    HDMI_REC_CONTROL_F_UXC_RESID16_G138,
    HDMI_REC_MEDIA_OFF_HDMI_ONLY_G138,
    HDMI_REC_MEDIA_ON_G138,
    HDMI_TC_OUTPUT_F_UXC_RESID16_G138,
    HOME_LOWER_LEFT_APERTURE_G137,
    HOME_LOWER_LEFT_ND_FILTER_G137,
    HUMAN_HARDWARE_ATTACH_TOKEN,
    IMPORT_ROOT_CERT_F_UXC_RESID16_G138,
    INTERVAL_MAX_DCIM_FILES_G137,
    INTERVAL_PERIOD_DEFAULT_SEC_G137,
    INTERVAL_PERIOD_MAX_SEC_G137,
    INTERVAL_PERIOD_MIN_SEC_G137,
    INTERVAL_SHOOT_7_PARAMS_G137,
    INTERVAL_SHOOT_F_UXC_RESID16_G137,
    INTERVAL_SHOTS_DEFAULT_G137,
    INTERVAL_SHOTS_MAX_G137,
    INTERVAL_SHOTS_MIN_G137,
    INTERVAL_SHUTTER_ELECTRONIC_G137,
    INTERVAL_SHUTTER_MECHANICAL_G137,
    INTERVAL_START_TIME_DEFAULT_SEC_G137,
    INTERVAL_START_TIME_MAX_SEC_G137,
    INTERVAL_START_TIME_MIN_SEC_G137,
    INTERVAL_STILL_FORMAT_HEIF_G137,
    INTERVAL_STILL_FORMAT_JPEG_G137,
    INTERVAL_STILL_FORMAT_RAW_G137,
    INTERVAL_STILL_FORMAT_RAW_HEIF_G137,
    INTERVAL_STILL_FORMAT_RAW_JPEG_G137,
    LOG_SHOOTING_CINE_EI_G137,
    LOG_SHOOTING_CINE_EI_QUICK_G137,
    LOG_SHOOTING_FLEXIBLE_ISO_G137,
    LOG_SHOOTING_OFF_G137,
    MEDIA_SIMULT_RECORDING_PHASE313,
    MEDIA_SLOT_1_PHASE313,
    MEDIA_SLOT_2_PHASE313,
    MODE_SETTINGS_FIXED_FPS_G137,
    MODE_SETTINGS_FIXED_VARIABLE_G137,
    Master138GateReport,
    OUTBOUND_CLIENT_TLS_TYPES_G138,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED,
    PHYSICAL_USB_PACKETS_EMITTED,
    PINNED_FX3_APPFW_SLICES_PHASE313,
    PINNED_FX3_APPFW_SLICES_SHA256_PHASE313,
    PINNED_FX6_APPFW_SLICES_PHASE313,
    PINNED_FX6_APPFW_SLICES_SHA256_PHASE313,
    PINNED_PHASE313_DONOR_SPECS,
    RAW_FIRMWARE_BYTES_LEAKED,
    REALHW_BIG6_HOME_FRAMING_INTERVAL_TC_SSH_FAN_138GATE_SCHEMA,
    REALHW_BIG6_HOME_FRAMING_INTERVAL_TC_SSH_FAN_138GATE_VERSION,
    RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE313,
    RESET_ACTION_INITIALIZE_PHASE313,
    RESET_ACTION_NONE_PHASE313,
    RESET_ACTION_RESET_NETWORK_SET_PHASE313,
    SHOOT_MODE_MOVIE_PHASE313,
    SHOOT_MODE_SQ_PHASE313,
    SHOOT_MODE_STILL_PHASE313,
    SHUTTER_MODE_ANGLE_G137,
    SHUTTER_MODE_SPEED_G137,
    SPI_NOR_WRITE_AUTHORIZED,
    SSH_HOST_KEY_G_UXC_RESID16_G138,
    STATUS_BLOCKED_G137_BIG6_PREREQ_HDMI_OR_END_ACTUATOR_VIOLATION,
    STATUS_BLOCKED_G137_DORMANT_AUTO_FRAMING_OR_LOCK_VIOLATION,
    STATUS_BLOCKED_G137_INTERVAL_SHOOT_PARAM_OR_FX6_CROSSWIRE_VIOLATION,
    STATUS_BLOCKED_G137_SLOT1_INTERVAL_9999_VAULT_FIREWALL_VIOLATION,
    STATUS_BLOCKED_G137_TELEMETRY_INVALID,
    STATUS_BLOCKED_G138_FAN_MAX_MYTH_OR_FX6_ALWAYS_OFF_VIOLATION,
    STATUS_BLOCKED_G138_SSH_ACCESS_AUTHEN_HTTPS_MYTH_OR_CERT_VIOLATION,
    STATUS_BLOCKED_G138_TC_MAKE_CLOCK_REGEN_OR_HDMI_REC_CTRL_VIOLATION,
    STATUS_BLOCKED_G138_TELEMETRY_INVALID,
    STATUS_BLOCKED_PERSISTENT_EMMC_WRITE,
    STATUS_BLOCKED_PHASE313_DONOR_INTEGRITY,
    STATUS_VERIFIED_G137,
    STATUS_VERIFIED_G138,
    TC_MAKE_F_UXC_RESID16_G138,
    TC_MAKE_FX6_CLOCK_G138,
    TC_MAKE_PRESET_G138,
    TC_MAKE_REGENERATE_G138,
    TC_RUN_F_UXC_RESID16_G138,
    TC_RUN_FREE_RUN_G138,
    TC_RUN_REC_RUN_G138,
    USB_PACKETS_TRANSMITTED,
    audit_phase313_donor_contracts,
    compute_big6_home_framing_interval_matrix,
    compute_tc_make_ssh_authen_fan_matrix,
    evaluate_138_master_safety_gates,
    evaluate_138gate_preflight,
    evaluate_g137_big6_home_framing_interval_vault_guard,
    evaluate_g138_tc_make_hdmi_rec_ssh_authen_fan_guard,
    resolve_fx3_big6_home_framing_interval_state,
    resolve_fx3_tc_make_ssh_authen_fan_state,
    run_138_gate_preflight,
    verify_big6_home_framing_interval_vault_guard,
    verify_tc_make_hdmi_rec_ssh_authen_fan_guard,
)


def _donors_available_here() -> bool:
    from fx3_safety.thermal_pwm_and_power_guard import resolve_donor_thermal_power_paths

    work_root = resolve_donor_thermal_power_paths(repo_root=DEFAULT_REPO_ROOT).work_root
    if work_root is None:
        return False
    for spec in PINNED_PHASE313_DONOR_SPECS.values():
        if not (work_root / spec[1]).exists():
            return False
    return True


def _build_stub_136_report(
    *, dry_run: bool = False, all_g13_136_ok: bool = True
) -> Master136GateReport:
    gates = []
    for idx in range(1, 137):
        is_tier0 = idx in (10, 11, 12)
        passed = True if (idx <= 9 or (is_tier0 and dry_run) or (idx >= 13 and all_g13_136_ok)) else False
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
    g13_134 = 122 if all_g13_136_ok else 0
    g135_136 = 2 if all_g13_136_ok else 0
    total = g01_12 + g13_134 + g135_136
    return Master136GateReport(
        schema="stub_136",
        version="2026.11.17",
        evaluated_utc="2026-11-17T00:00:00Z",
        verification_mode="CLEAN_ROOM_SYNTHETIC",
        clean_room_forced=True,
        dry_run_rehearsal_only=dry_run,
        overall_ready_for_hardware_attach=False,
        hardware_live_attachment_authorized=False,
        offline_133_gates_verified=all_g13_136_ok,
        all_136_gates_verified=(dry_run and all_g13_136_ok),
        g13_to_g136_all_passed=all_g13_136_ok,
        g135_to_g136_all_passed=all_g13_136_ok,
        h0_h1_trial_entry_allowed=all_g13_136_ok,
        status=(
            "VERIFIED_ALL_136_GATES_DRY_RUN_SIMULATED_BACKUP"
            if dry_run
            else "VERIFIED_133_OF_136_AWAITING_PHYSICAL_TIER0"
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
            "g13_to_g134_verified": g13_134,
            "g135_to_g136_verified": g135_136,
            "verified_gates": total,
        },
        gates=tuple(gates),
        master_134_report={},
        g135_result={},
        g136_result={},
        errors=(),
        warnings=(),
    )


class TestPackageExportsAndDonorAuditPhase313(unittest.TestCase):
    def test_01_package_exports_phase313_symbols_and_all(self) -> None:
        self.assertIs(fx3_safety.evaluate_138gate_preflight, evaluate_138gate_preflight)
        self.assertIs(
            fx3_safety.evaluate_g137_big6_home_framing_interval_vault_guard,
            evaluate_g137_big6_home_framing_interval_vault_guard,
        )
        self.assertIs(
            fx3_safety.evaluate_g138_tc_make_hdmi_rec_ssh_authen_fan_guard,
            evaluate_g138_tc_make_hdmi_rec_ssh_authen_fan_guard,
        )
        self.assertEqual(fx3_safety.G137, "G137")
        self.assertEqual(fx3_safety.G138, "G138")
        self.assertIn("evaluate_138gate_preflight", fx3_safety.__all__)
        self.assertIn(
            "evaluate_g137_big6_home_framing_interval_vault_guard", fx3_safety.__all__
        )
        self.assertIn(
            "evaluate_g138_tc_make_hdmi_rec_ssh_authen_fan_guard", fx3_safety.__all__
        )
        self.assertIn("Master138GateReport", fx3_safety.__all__)
        self.assertIn("evaluate_138_master_safety_gates", fx3_safety.__all__)
        self.assertIn("run_138_gate_preflight", fx3_safety.__all__)

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
            REALHW_BIG6_HOME_FRAMING_INTERVAL_TC_SSH_FAN_138GATE_SCHEMA,
            "realhw_big6_home_framing_interval_tc_ssh_fan_and_138gate_guard_v1",
        )
        self.assertTrue(REALHW_BIG6_HOME_FRAMING_INTERVAL_TC_SSH_FAN_138GATE_VERSION)
        r1 = verify_big6_home_framing_interval_vault_guard()
        with self.assertRaises(dataclasses.FrozenInstanceError):
            r1.valid = False  # type: ignore[misc]
        r2 = verify_tc_make_hdmi_rec_ssh_authen_fan_guard()
        with self.assertRaises(dataclasses.FrozenInstanceError):
            r2.valid = False  # type: ignore[misc]
        aud = audit_phase313_donor_contracts(force_clean_room=True)
        with self.assertRaises(dataclasses.FrozenInstanceError):
            aud.valid = False  # type: ignore[misc]

    def test_04_donor_audit_clean_room_forced_under_budget(self) -> None:
        t0 = time.perf_counter()
        audit = audit_phase313_donor_contracts(force_clean_room=True)
        dt = time.perf_counter() - t0
        self.assertTrue(audit.valid)
        self.assertEqual(audit.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(audit.access_mode, "SYNTHETIC_NO_DONOR_TOUCH")
        self.assertEqual(audit.files_inspected, 0)
        self.assertEqual(audit.raw_firmware_bytes_leaked, 0)
        self.assertTrue(audit.fx3_contracts_verified)
        self.assertTrue(audit.fx6_contracts_verified)
        self.assertTrue(audit.four_lang_resid16_parity_verified)
        budget = (
            DONOR_CHECK_CI_MAX_SECONDS_PHASE313 + 15.0
            if os.environ.get("GITHUB_ACTIONS") == "true"
            else DONOR_CHECK_MAX_SECONDS_PHASE313
        )
        self.assertLessEqual(dt, budget)

    def test_05_donor_audit_env_fx3_clean_room_test_1(self) -> None:
        with mock.patch.dict(os.environ, {ENV_CLEAN_ROOM_TEST_PHASE313: "1"}):
            audit = audit_phase313_donor_contracts()
            self.assertTrue(audit.valid)
            self.assertEqual(audit.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_06_donor_audit_env_fx3_fx6_force_clean_room_1(self) -> None:
        with mock.patch.dict(os.environ, {ENV_FORCE_CLEAN_ROOM: "1"}):
            audit = audit_phase313_donor_contracts()
            self.assertTrue(audit.valid)
            self.assertEqual(audit.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_07_donor_audit_real_o_rdonly_when_present_or_clean_room_when_absent(self) -> None:
        audit = audit_phase313_donor_contracts()
        self.assertTrue(audit.valid)
        self.assertEqual(audit.raw_firmware_bytes_leaked, 0)
        budget = (
            DONOR_CHECK_CI_MAX_SECONDS_PHASE313 + 15.0
            if os.environ.get("GITHUB_ACTIONS") == "true"
            else DONOR_CHECK_MAX_SECONDS_PHASE313
        )
        self.assertLessEqual(audit.elapsed_seconds, budget)
        if _donors_available_here() and os.environ.get(ENV_FORCE_CLEAN_ROOM) != "1" and os.environ.get(ENV_CLEAN_ROOM_TEST_PHASE313) != "1":
            self.assertEqual(audit.verification_mode, "LOCAL_DONOR_O_RDONLY")
            self.assertEqual(audit.access_mode, "POSIX_O_RDONLY_AND_PREAD_ZERO_MUTATION")
            self.assertEqual(audit.files_inspected, len(PINNED_PHASE313_DONOR_SPECS))
            self.assertEqual(audit.sha256_by_artifact["fx3_appfw_so"], PINNED_FX3_APPFW_SLICES_SHA256_PHASE313)
            self.assertEqual(audit.sha256_by_artifact["fx6_appfw_so"], PINNED_FX6_APPFW_SLICES_SHA256_PHASE313)
            self.assertTrue(audit.four_lang_resid16_parity_verified)
        else:
            self.assertEqual(audit.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_08_donor_audit_absent_root_falls_back_clean_room_without_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.dict(os.environ, {}, clear=False):
                os.environ.pop(ENV_FORCE_CLEAN_ROOM, None)
                os.environ.pop(ENV_CLEAN_ROOM_TEST_PHASE313, None)
                audit = audit_phase313_donor_contracts(work_root=Path(tmp))
                self.assertTrue(audit.valid)
                self.assertEqual(audit.verification_mode, "CLEAN_ROOM_SYNTHETIC")
                self.assertEqual(audit.raw_firmware_bytes_leaked, 0)

    def test_09_donor_audit_tampered_donor_file_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for spec in PINNED_PHASE313_DONOR_SPECS.values():
                p = root / spec[1]
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(b"\x00" * 64)
            with mock.patch.dict(os.environ, {}, clear=False):
                os.environ.pop(ENV_FORCE_CLEAN_ROOM, None)
                os.environ.pop(ENV_CLEAN_ROOM_TEST_PHASE313, None)
                audit = audit_phase313_donor_contracts(work_root=root)
                self.assertFalse(audit.valid)
                self.assertEqual(audit.status, STATUS_BLOCKED_PHASE313_DONOR_INTEGRITY)
                self.assertEqual(audit.raw_firmware_bytes_leaked, 0)

    def test_10_pinned_donor_slices_counts_and_fx3_absence_proofs(self) -> None:
        self.assertEqual(len(PINNED_FX3_APPFW_SLICES_PHASE313), 25)
        self.assertEqual(len(PINNED_FX6_APPFW_SLICES_PHASE313), 12)
        self.assertEqual(len(PINNED_PHASE313_DONOR_SPECS), 11)
        fx3_tokens = {tok.decode("ascii", errors="ignore") for _, tok in PINNED_FX3_APPFW_SLICES_PHASE313}
        self.assertIn("BKID_APP_setting_fps_fixed_variable_select", fx3_tokens)
        self.assertIn("TYPE_EFRAMING_SUPPORT_TYPE_MANUAL_ONLY", fx3_tokens)
        self.assertIn("MSGID_SSHD_START_CMD", fx3_tokens)
        self.assertIn("FAN_CONTROL_ALWAYS_OFF", fx3_tokens)
        self.assertNotIn("VAL_setting_tc_make_TC_MAKE_CLOCK", fx3_tokens)
        self.assertNotIn("FAN_CONTROL_MAX", fx3_tokens)

    def test_11_gate_constants_and_4lang_uxc_ids(self) -> None:
        self.assertEqual(G137_GATE_ID, G137)
        self.assertEqual(G138_GATE_ID, G138)
        self.assertIn("G137_BIG6_HOME_ND_META_MANUAL_FRAMING", G137_GATE_CODE)
        self.assertIn("G138_TC_MAKE_REGEN_HDMI_REC_CTRL", G138_GATE_CODE)
        self.assertEqual(BIG6_MODE_SETTINGS_F_UXC_RESID16_G137, 0x7D0D)
        self.assertEqual(BIG6_HOME_LOWER_LEFT_F_UXC_RESID16_G137, 0x7CE3)
        self.assertEqual(FRAMING_SETTINGS_F_UXC_RESID16_G137, 0x7D18)
        self.assertEqual(INTERVAL_SHOOT_F_UXC_RESID16_G137, 0x7027)
        self.assertEqual(TC_MAKE_F_UXC_RESID16_G138, 0x6B79)
        self.assertEqual(ACCESS_AUTHEN_F_UXC_RESID16_G138, 0x7ADA)
        self.assertEqual(IMPORT_ROOT_CERT_F_UXC_RESID16_G138, 0x7940)
        self.assertEqual(SSH_HOST_KEY_G_UXC_RESID16_G138, 0x610B)


class TestGateG137Big6HomeManualFramingAndIntervalVault(unittest.TestCase):
    def test_12_g137_baseline_clean_defaults_pass(self) -> None:
        v, r = evaluate_g137_big6_home_framing_interval_vault_guard(force_clean_room=True)
        self.assertTrue(v.passed)
        self.assertTrue(r.valid)
        self.assertEqual(r.status, STATUS_VERIFIED_G137)
        self.assertEqual(r.raw_firmware_bytes_leaked, 0)
        self.assertFalse(r.persistent_emmc_writes_authorized)
        self.assertEqual(r.big6_home_framing_interval_vault_guard["matrix_states_checked"], 256)

    def test_13_g137_big6_requires_mode_settings_fixed_variable(self) -> None:
        ok = verify_big6_home_framing_interval_vault_guard(
            requested_mode_settings=MODE_SETTINGS_FIXED_VARIABLE_G137,
            big6_entry_trigger=BIG6_ENTRY_HOME_KEY_G137,
        )
        self.assertTrue(ok.valid)
        self.assertTrue(ok.big6_screen_active)
        self.assertEqual(ok.big6_exact_6_tiles, FX3_BIG6_EXACT_6_TILES_LABELS_G137)

        inactive = verify_big6_home_framing_interval_vault_guard(
            requested_mode_settings=MODE_SETTINGS_FIXED_FPS_G137,
            big6_entry_trigger=BIG6_ENTRY_HOME_KEY_G137,
        )
        self.assertTrue(inactive.valid)
        self.assertFalse(inactive.big6_screen_active)

        blocked = verify_big6_home_framing_interval_vault_guard(
            requested_mode_settings=MODE_SETTINGS_FIXED_FPS_G137,
            big6_entry_trigger=BIG6_ENTRY_HOME_KEY_G137,
            force_big6_without_fixed_variable=True,
        )
        self.assertFalse(blocked.valid)
        self.assertIn(
            STATUS_BLOCKED_G137_BIG6_PREREQ_HDMI_OR_END_ACTUATOR_VIOLATION,
            blocked.violation_codes,
        )

    def test_14_g137_big6_swipe_down_entry_and_touch_cursor_tiles(self) -> None:
        ok = verify_big6_home_framing_interval_vault_guard(
            requested_mode_settings=MODE_SETTINGS_FIXED_VARIABLE_G137,
            big6_entry_trigger=BIG6_ENTRY_SWIPE_DOWN_G137,
            touch_operation_enabled=True,
            big6_cursor_active=True,
        )
        self.assertTrue(ok.valid)
        self.assertTrue(ok.big6_screen_active)
        self.assertTrue(ok.big6_cursor_active)
        self.assertEqual(len(ok.big6_exact_6_tiles), 6)
        self.assertEqual(BIG6_SWIPE_DOWN_F_UXC_RESID16_G137, 0x7CDD)
        self.assertEqual(BIG6_HOME_CUSTOM_KEY_F_UXC_RESID16_G137, 0x7CAD)

        swipe_blocked = verify_big6_home_framing_interval_vault_guard(
            requested_mode_settings=MODE_SETTINGS_FIXED_VARIABLE_G137,
            big6_entry_trigger=BIG6_ENTRY_SWIPE_DOWN_G137,
            touch_operation_enabled=False,
        )
        self.assertFalse(swipe_blocked.valid)
        self.assertFalse(swipe_blocked.big6_screen_active)

    def test_15_g137_big6_dynamic_tile_iso_vs_ei_and_pp_vs_lut(self) -> None:
        std_log_off = verify_big6_home_framing_interval_vault_guard(
            log_shooting_mode=LOG_SHOOTING_OFF_G137,
        )
        self.assertTrue(std_log_off.valid)
        self.assertEqual(std_log_off.big6_iso_or_ei_tile_label, "ISO")
        self.assertEqual(std_log_off.big6_pp_or_lut_tile_label, "Picture Profile")

        cine_ei = verify_big6_home_framing_interval_vault_guard(
            log_shooting_mode=LOG_SHOOTING_CINE_EI_G137,
        )
        self.assertTrue(cine_ei.valid)
        self.assertEqual(cine_ei.big6_iso_or_ei_tile_label, "Base ISO + EI")
        self.assertEqual(cine_ei.big6_pp_or_lut_tile_label, "Select LUT")

        cine_ei_quick = verify_big6_home_framing_interval_vault_guard(
            log_shooting_mode=LOG_SHOOTING_CINE_EI_QUICK_G137,
        )
        self.assertEqual(cine_ei_quick.big6_iso_or_ei_tile_label, "Base ISO + EI")
        self.assertEqual(cine_ei_quick.big6_pp_or_lut_tile_label, "Select LUT")

        flex_iso = verify_big6_home_framing_interval_vault_guard(
            log_shooting_mode=LOG_SHOOTING_FLEXIBLE_ISO_G137,
        )
        self.assertEqual(flex_iso.big6_iso_or_ei_tile_label, "ISO")
        self.assertEqual(flex_iso.big6_pp_or_lut_tile_label, "Select LUT")

    def test_16_g137_big6_never_outputs_to_hdmi(self) -> None:
        blocked = verify_big6_home_framing_interval_vault_guard(
            requested_mode_settings=MODE_SETTINGS_FIXED_VARIABLE_G137,
            big6_entry_trigger=BIG6_ENTRY_HOME_KEY_G137,
            big6_hdmi_output_claimed=True,
        )
        self.assertFalse(blocked.valid)
        self.assertTrue(blocked.big6_hdmi_output_active)
        self.assertEqual(blocked.block_errno, EOPNOTSUPP_ERRNO_PHASE313)
        self.assertIn(
            STATUS_BLOCKED_G137_BIG6_PREREQ_HDMI_OR_END_ACTUATOR_VIOLATION,
            blocked.violation_codes,
        )

    def test_17_g137_home_lower_left_nd_metadata_only_vs_fx6_end(self) -> None:
        meta_ok = verify_big6_home_framing_interval_vault_guard(
            requested_home_lower_left=HOME_LOWER_LEFT_ND_FILTER_G137,
            target_model=FX3_MODEL_NAME_PHASE313,
        )
        self.assertTrue(meta_ok.valid)
        self.assertEqual(meta_ok.effective_home_lower_left, HOME_LOWER_LEFT_ND_FILTER_G137)
        self.assertFalse(meta_ok.fx3_physical_end_actuator_present)
        self.assertEqual(meta_ok.fx6_physical_end_options, FX6_END_ND_OPTIONS_G137)
        self.assertIn("1/4..1/128", FX6_END_ND_OPTIONS_G137)

        blocked_hw = verify_big6_home_framing_interval_vault_guard(
            claimed_fx3_physical_end_actuator=True,
        )
        self.assertFalse(blocked_hw.valid)
        self.assertEqual(blocked_hw.block_errno, EOPNOTSUPP_ERRNO_PHASE313)
        self.assertIn(
            STATUS_BLOCKED_G137_BIG6_PREREQ_HDMI_OR_END_ACTUATOR_VIOLATION,
            blocked_hw.violation_codes,
        )

    def test_18_g137_home_lower_left_preserves_net_reset_and_resets_cam_and_init(self) -> None:
        net_reset = verify_big6_home_framing_interval_vault_guard(
            requested_home_lower_left=HOME_LOWER_LEFT_ND_FILTER_G137,
            reset_action=RESET_ACTION_RESET_NETWORK_SET_PHASE313,
        )
        self.assertTrue(net_reset.valid)
        self.assertEqual(net_reset.effective_home_lower_left, HOME_LOWER_LEFT_ND_FILTER_G137)

        for rst in (
            RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE313,
            RESET_ACTION_INITIALIZE_PHASE313,
        ):
            reset_res = verify_big6_home_framing_interval_vault_guard(
                requested_home_lower_left=HOME_LOWER_LEFT_ND_FILTER_G137,
                reset_action=rst,
            )
            self.assertTrue(reset_res.valid)
            self.assertEqual(reset_res.effective_home_lower_left, HOME_LOWER_LEFT_APERTURE_G137)

    def test_19_g137_manual_framing_settings_valid_crop_full(self) -> None:
        for rec_mode in ALLOWED_FRAMING_REC_STREAM_MODES_G137:
            for hdmi_mode in ALLOWED_FRAMING_HDMI_MODES_G137:
                res = verify_big6_home_framing_interval_vault_guard(
                    requested_framing_on=True,
                    framing_rec_stream_mode=rec_mode,
                    framing_hdmi_mode=hdmi_mode,
                    fps=24,
                )
                self.assertTrue(res.valid)
                self.assertTrue(res.effective_framing_on)
                self.assertTrue(res.apsc_s35_disabled_by_framing)
                self.assertEqual(res.fx3_framing_support_lock, "TYPE_EFRAMING_SUPPORT_TYPE_MANUAL_ONLY")

    def test_20_g137_framing_lockout_100p_hfr_rec_streaming(self) -> None:
        hfr = verify_big6_home_framing_interval_vault_guard(
            requested_framing_on=True,
            fps=120,
        )
        self.assertTrue(hfr.valid)
        self.assertTrue(hfr.framing_locked_out)
        self.assertIn("high_frame_rate_ge_100p", hfr.framing_lockout_reasons)

        rec = verify_big6_home_framing_interval_vault_guard(
            requested_framing_on=True,
            active_recording=True,
        )
        self.assertTrue(rec.framing_locked_out)
        self.assertIn("active_recording", rec.framing_lockout_reasons)

        stream = verify_big6_home_framing_interval_vault_guard(
            requested_framing_on=True,
            streaming_active=True,
        )
        self.assertTrue(stream.framing_locked_out)
        self.assertIn("streaming_active", stream.framing_lockout_reasons)

    def test_21_g137_framing_fails_when_forcing_apsc_or_bypassing_lockout(self) -> None:
        bad_apsc = verify_big6_home_framing_interval_vault_guard(
            requested_framing_on=True,
            claimed_apsc_s35_concurrent_with_framing=True,
        )
        self.assertFalse(bad_apsc.valid)
        self.assertIn(
            STATUS_BLOCKED_G137_DORMANT_AUTO_FRAMING_OR_LOCK_VIOLATION,
            bad_apsc.violation_codes,
        )

        bad_120p = verify_big6_home_framing_interval_vault_guard(
            requested_framing_on=True,
            fps=120,
            force_framing_under_lockout=True,
        )
        self.assertFalse(bad_120p.valid)
        self.assertIn(
            STATUS_BLOCKED_G137_DORMANT_AUTO_FRAMING_OR_LOCK_VIOLATION,
            bad_120p.violation_codes,
        )

    def test_22_g137_dormant_ai_auto_framing_rejected_eopnotsupp(self) -> None:
        for trap in DORMANT_AUTO_FRAMING_TRAPS_G137:
            res = verify_big6_home_framing_interval_vault_guard(
                requested_dormant_auto_framing_symbol=trap,
            )
            self.assertFalse(res.valid)
            self.assertTrue(res.dormant_auto_framing_blocked)
            self.assertEqual(res.block_errno, EOPNOTSUPP_ERRNO_PHASE313)
            self.assertIn(
                STATUS_BLOCKED_G137_DORMANT_AUTO_FRAMING_OR_LOCK_VIOLATION,
                res.violation_codes,
            )

    def test_23_g137_interval_shoot_slot2_unprotected_passes_with_params(self) -> None:
        res = verify_big6_home_framing_interval_vault_guard(
            shoot_mode=SHOOT_MODE_STILL_PHASE313,
            exposure_mode=EXPOSURE_MODE_M_G137,
            requested_interval_shooting="On",
            requested_target_slot=MEDIA_SLOT_2_PHASE313,
            slot_1_contains_tier0_vault=True,
            interval_start_time_sec=INTERVAL_START_TIME_DEFAULT_SEC_G137,
            interval_period_sec=INTERVAL_PERIOD_DEFAULT_SEC_G137,
            interval_shot_count=INTERVAL_SHOTS_MAX_G137,
            interval_ae_tracking_sensitivity="Mid",
            interval_shutter_type=INTERVAL_SHUTTER_ELECTRONIC_G137,
            interval_priority="Off",
            interval_still_format=INTERVAL_STILL_FORMAT_RAW_JPEG_G137,
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.effective_interval_shooting, "On")
        self.assertEqual(res.interval_max_dcim_files, INTERVAL_MAX_DCIM_FILES_G137)
        self.assertEqual(res.slot1_data_sector_writes, 0)
        self.assertFalse(res.slot1_dcim_mutated)
        self.assertFalse(res.slot1_avf_info_mutated)

    def test_24_g137_slot1_interval_9999_vault_firewall_blocks_erofs(self) -> None:
        blocked = verify_big6_home_framing_interval_vault_guard(
            shoot_mode=SHOOT_MODE_STILL_PHASE313,
            requested_interval_shooting="On",
            requested_target_slot=MEDIA_SLOT_1_PHASE313,
            slot_1_contains_tier0_vault=True,
            slot_1_write_protected=False,
            interval_shot_count=INTERVAL_SHOTS_MAX_G137,
            interval_still_format=INTERVAL_STILL_FORMAT_RAW_JPEG_G137,
        )
        self.assertFalse(blocked.valid)
        self.assertTrue(blocked.slot1_vault_firewall_blocked)
        self.assertEqual(blocked.block_errno, EROFS_ERRNO_PHASE313)
        self.assertEqual(blocked.block_errno_name, "EROFS")
        self.assertEqual(blocked.slot1_data_sector_writes, 0)
        self.assertFalse(blocked.slot1_dcim_mutated)
        self.assertFalse(blocked.slot1_avf_info_mutated)
        self.assertIn(
            STATUS_BLOCKED_G137_SLOT1_INTERVAL_9999_VAULT_FIREWALL_VIOLATION,
            blocked.violation_codes,
        )

    def test_25_g137_slot1_interval_simult_rec_and_wp_switch_ebusy(self) -> None:
        simult = verify_big6_home_framing_interval_vault_guard(
            shoot_mode=SHOOT_MODE_STILL_PHASE313,
            requested_interval_shooting="On",
            requested_target_slot=MEDIA_SIMULT_RECORDING_PHASE313,
            slot_1_contains_tier0_vault=True,
            slot_1_write_protected=False,
        )
        self.assertFalse(simult.valid)
        self.assertEqual(simult.block_errno, EROFS_ERRNO_PHASE313)
        self.assertEqual(simult.slot1_data_sector_writes, 0)

        wp = verify_big6_home_framing_interval_vault_guard(
            shoot_mode=SHOOT_MODE_STILL_PHASE313,
            requested_interval_shooting="On",
            requested_target_slot=MEDIA_SLOT_1_PHASE313,
            slot_1_contains_tier0_vault=False,
            slot_1_write_protected=True,
        )
        self.assertFalse(wp.valid)
        self.assertEqual(wp.block_errno, EBUSY_ERRNO_PHASE313)
        self.assertEqual(wp.block_errno_name, "EBUSY")
        self.assertEqual(wp.slot1_data_sector_writes, 0)

    def test_26_g137_interval_exits_bulb_to_30s_and_disabled_in_iauto(self) -> None:
        bulb_ok = verify_big6_home_framing_interval_vault_guard(
            shoot_mode=SHOOT_MODE_STILL_PHASE313,
            requested_interval_shooting="On",
            requested_target_slot=MEDIA_SLOT_2_PHASE313,
            exposure_mode=EXPOSURE_MODE_M_G137,
            interval_bulb_requested_concurrently=True,
        )
        self.assertTrue(bulb_ok.valid)
        self.assertTrue(bulb_ok.interval_bulb_exited_to_30s)

        iauto_ok = verify_big6_home_framing_interval_vault_guard(
            shoot_mode=SHOOT_MODE_STILL_PHASE313,
            requested_interval_shooting="On",
            requested_target_slot=MEDIA_SLOT_2_PHASE313,
            exposure_mode=EXPOSURE_MODE_INTELLIGENT_AUTO_G137,
        )
        self.assertTrue(iauto_ok.valid)
        self.assertTrue(iauto_ok.interval_disabled_in_iauto)

        iauto_bad = verify_big6_home_framing_interval_vault_guard(
            shoot_mode=SHOOT_MODE_STILL_PHASE313,
            requested_interval_shooting="On",
            requested_target_slot=MEDIA_SLOT_2_PHASE313,
            exposure_mode=EXPOSURE_MODE_INTELLIGENT_AUTO_G137,
            force_interval_in_iauto_or_non_still=True,
        )
        self.assertFalse(iauto_bad.valid)
        self.assertIn(
            STATUS_BLOCKED_G137_INTERVAL_SHOOT_PARAM_OR_FX6_CROSSWIRE_VIOLATION,
            iauto_bad.violation_codes,
        )

    def test_27_g137_interval_bounds_and_cam_initialize_reset_of_7_params(self) -> None:
        self.assertEqual(len(INTERVAL_SHOOT_7_PARAMS_G137), 7)
        bad_shots = verify_big6_home_framing_interval_vault_guard(
            interval_shot_count=10000,
        )
        self.assertFalse(bad_shots.valid)
        bad_start = verify_big6_home_framing_interval_vault_guard(
            interval_start_time_sec=6000,
        )
        self.assertFalse(bad_start.valid)
        bad_period = verify_big6_home_framing_interval_vault_guard(
            interval_period_sec=0,
        )
        self.assertFalse(bad_period.valid)

        init = verify_big6_home_framing_interval_vault_guard(
            shoot_mode=SHOOT_MODE_STILL_PHASE313,
            requested_interval_shooting="On",
            requested_target_slot=MEDIA_SLOT_2_PHASE313,
            reset_action=RESET_ACTION_INITIALIZE_PHASE313,
            interval_start_time_sec=10,
            interval_period_sec=15,
            interval_shot_count=500,
            interval_ae_tracking_sensitivity="Low",
            interval_shutter_type=INTERVAL_SHUTTER_MECHANICAL_G137,
            interval_priority="On",
        )
        self.assertTrue(init.valid)
        self.assertEqual(init.effective_interval_shooting, "Off")
        self.assertEqual(init.interval_start_time_sec, INTERVAL_START_TIME_DEFAULT_SEC_G137)
        self.assertEqual(init.interval_period_sec, INTERVAL_PERIOD_DEFAULT_SEC_G137)
        self.assertEqual(init.interval_shot_count, INTERVAL_SHOTS_DEFAULT_G137)
        self.assertEqual(init.interval_ae_tracking_sensitivity, "Mid")
        self.assertEqual(init.interval_shutter_type, INTERVAL_SHUTTER_ELECTRONIC_G137)
        self.assertEqual(init.interval_priority, "Off")

    def test_28_g137_fx6_single_mxf_interval_rec_vs_fx3_stills_crosswire_rejected(self) -> None:
        bad_cross = verify_big6_home_framing_interval_vault_guard(
            claimed_fx3_interval_outputs_single_mxf_or_fx6_9999=True,
        )
        self.assertFalse(bad_cross.valid)
        self.assertEqual(bad_cross.block_errno, EOPNOTSUPP_ERRNO_PHASE313)
        self.assertIn(
            STATUS_BLOCKED_G137_INTERVAL_SHOOT_PARAM_OR_FX6_CROSSWIRE_VIOLATION,
            bad_cross.violation_codes,
        )

    def test_29_g137_256_state_matrix_and_telemetry_validation(self) -> None:
        mat = compute_big6_home_framing_interval_matrix()
        self.assertEqual(mat["states_checked"], 256)
        self.assertEqual(mat["big6_active_count"], 64)
        self.assertEqual(mat["nd_metadata_only_count"], 128)
        self.assertEqual(mat["framing_apsc_disabled_count"], 128)
        self.assertEqual(mat["slot1_firewall_blocked_count"], 32)

        bad_model = verify_big6_home_framing_interval_vault_guard(body_model_name="ILCE-7M4")
        self.assertFalse(bad_model.valid)
        self.assertIn(STATUS_BLOCKED_G137_TELEMETRY_INVALID, bad_model.violation_codes)

        bad_fw = verify_big6_home_framing_interval_vault_guard(firmware_version="invalid")
        self.assertFalse(bad_fw.valid)

        bad_mode = verify_big6_home_framing_interval_vault_guard(requested_mode_settings="BOGUS")
        self.assertFalse(bad_mode.valid)

        bad_shoot = verify_big6_home_framing_interval_vault_guard(shoot_mode="BOGUS")
        self.assertFalse(bad_shoot.valid)

        bad_fmt = verify_big6_home_framing_interval_vault_guard(interval_still_format="BMP")
        self.assertFalse(bad_fmt.valid)

        res_dict = resolve_fx3_big6_home_framing_interval_state()
        self.assertTrue(res_dict["valid"])
        self.assertEqual(res_dict["status"], STATUS_VERIFIED_G137)


class TestGateG138TcMakeHdmiRecSshAuthenAndFanControl(unittest.TestCase):
    def test_30_g138_baseline_clean_defaults_pass(self) -> None:
        v, r = evaluate_g138_tc_make_hdmi_rec_ssh_authen_fan_guard(force_clean_room=True)
        self.assertTrue(v.passed)
        self.assertTrue(r.valid)
        self.assertEqual(r.status, STATUS_VERIFIED_G138)
        self.assertEqual(r.raw_firmware_bytes_leaked, 0)
        self.assertFalse(r.persistent_emmc_writes_authorized)
        self.assertEqual(r.tc_make_hdmi_rec_ssh_authen_fan_guard["matrix_states_checked"], 256)

    def test_31_g138_tc_make_regenerate_forces_rec_run_reading_slot1(self) -> None:
        ok = verify_tc_make_hdmi_rec_ssh_authen_fan_guard(
            recording_media_mode=MEDIA_SIMULT_RECORDING_PHASE313,
            requested_tc_make=TC_MAKE_REGENERATE_G138,
            requested_tc_run=TC_RUN_FREE_RUN_G138,
        )
        self.assertTrue(ok.valid)
        self.assertEqual(ok.effective_tc_make, TC_MAKE_REGENERATE_G138)
        self.assertEqual(ok.effective_tc_run, TC_RUN_REC_RUN_G138)
        self.assertTrue(ok.tc_regenerate_forced_rec_run)
        self.assertEqual(ok.tc_regenerate_source_slot, MEDIA_SLOT_1_PHASE313)

        slot2_ok = verify_tc_make_hdmi_rec_ssh_authen_fan_guard(
            recording_media_mode=MEDIA_SLOT_2_PHASE313,
            requested_tc_make=TC_MAKE_REGENERATE_G138,
        )
        self.assertEqual(slot2_ok.tc_regenerate_source_slot, MEDIA_SLOT_2_PHASE313)

        bad_force = verify_tc_make_hdmi_rec_ssh_authen_fan_guard(
            requested_tc_make=TC_MAKE_REGENERATE_G138,
            requested_tc_run=TC_RUN_FREE_RUN_G138,
            force_free_run_under_regenerate=True,
        )
        self.assertFalse(bad_force.valid)
        self.assertIn(
            STATUS_BLOCKED_G138_TC_MAKE_CLOCK_REGEN_OR_HDMI_REC_CTRL_VIOLATION,
            bad_force.violation_codes,
        )

    def test_32_g138_tc_make_clock_rejected_on_fx3_allowed_on_fx6_spec(self) -> None:
        bad_fx3_clock = verify_tc_make_hdmi_rec_ssh_authen_fan_guard(
            target_model=FX3_MODEL_NAME_PHASE313,
            requested_tc_make=TC_MAKE_FX6_CLOCK_G138,
        )
        self.assertFalse(bad_fx3_clock.valid)
        self.assertEqual(bad_fx3_clock.block_errno, EOPNOTSUPP_ERRNO_PHASE313)
        self.assertIn(
            STATUS_BLOCKED_G138_TC_MAKE_CLOCK_REGEN_OR_HDMI_REC_CTRL_VIOLATION,
            bad_fx3_clock.violation_codes,
        )
        self.assertEqual(ALLOWED_FX3_TC_MAKE_MODES_G138, (TC_MAKE_PRESET_G138, TC_MAKE_REGENERATE_G138))
        self.assertIn(TC_MAKE_FX6_CLOCK_G138, ALLOWED_FX6_TC_MAKE_MODES_G138)

    def test_33_g138_vmc_bncm1_ext_lk_requires_preset_and_free_run(self) -> None:
        ext_ok = verify_tc_make_hdmi_rec_ssh_authen_fan_guard(
            shoot_mode=SHOOT_MODE_MOVIE_PHASE313,
            requested_tc_make=TC_MAKE_PRESET_G138,
            requested_tc_run=TC_RUN_FREE_RUN_G138,
            vmc_bncm1_ext_ltc_requested=True,
        )
        self.assertTrue(ext_ok.valid)
        self.assertEqual(ext_ok.ext_tc_lock_status, "EXT-LK")

        ext_regen = verify_tc_make_hdmi_rec_ssh_authen_fan_guard(
            shoot_mode=SHOOT_MODE_MOVIE_PHASE313,
            requested_tc_make=TC_MAKE_REGENERATE_G138,
            vmc_bncm1_ext_ltc_requested=True,
        )
        self.assertTrue(ext_regen.valid)
        self.assertEqual(ext_regen.ext_tc_lock_status, "INT")

        ext_forced_bad = verify_tc_make_hdmi_rec_ssh_authen_fan_guard(
            shoot_mode=SHOOT_MODE_MOVIE_PHASE313,
            requested_tc_make=TC_MAKE_REGENERATE_G138,
            vmc_bncm1_ext_ltc_requested=True,
            force_ext_lk_without_preset_freerun=True,
        )
        self.assertFalse(ext_forced_bad.valid)
        self.assertIn(
            STATUS_BLOCKED_G138_TC_MAKE_CLOCK_REGEN_OR_HDMI_REC_CTRL_VIOLATION,
            ext_forced_bad.violation_codes,
        )

    def test_34_g138_hdmi_rec_control_cardless_and_restrictions(self) -> None:
        cardless_ok = verify_tc_make_hdmi_rec_ssh_authen_fan_guard(
            shoot_mode=SHOOT_MODE_MOVIE_PHASE313,
            hdmi_tc_output="On",
            requested_hdmi_rec_control="On",
            rec_media_dur_hdmi_output=HDMI_REC_MEDIA_OFF_HDMI_ONLY_G138,
            hdmi_raw_output_on=True,
        )
        self.assertTrue(cardless_ok.valid)
        self.assertEqual(cardless_ok.effective_hdmi_rec_control, "On")
        self.assertTrue(cardless_ok.cardless_hdmi_rec_ctrl_permitted)

        tc_off = verify_tc_make_hdmi_rec_ssh_authen_fan_guard(
            shoot_mode=SHOOT_MODE_MOVIE_PHASE313,
            hdmi_tc_output="Off",
            requested_hdmi_rec_control="On",
        )
        self.assertTrue(tc_off.valid)
        self.assertEqual(tc_off.effective_hdmi_rec_control, "Off")
        self.assertIn("hdmi_tc_output_off", tc_off.hdmi_rec_ctrl_restricted_reasons)

        sq_bad = verify_tc_make_hdmi_rec_ssh_authen_fan_guard(
            shoot_mode=SHOOT_MODE_SQ_PHASE313,
            hdmi_tc_output="On",
            requested_hdmi_rec_control="On",
            force_hdmi_rec_ctrl_when_restricted=True,
        )
        self.assertFalse(sq_bad.valid)

        stream_bad = verify_tc_make_hdmi_rec_ssh_authen_fan_guard(
            shoot_mode=SHOOT_MODE_MOVIE_PHASE313,
            hdmi_tc_output="On",
            requested_hdmi_rec_control="On",
            streaming_active=True,
            force_hdmi_rec_ctrl_when_restricted=True,
        )
        self.assertFalse(stream_bad.valid)

        usb_stream_bad = verify_tc_make_hdmi_rec_ssh_authen_fan_guard(
            shoot_mode=SHOOT_MODE_MOVIE_PHASE313,
            hdmi_tc_output="On",
            requested_hdmi_rec_control="On",
            usb_streaming_active=True,
            force_hdmi_rec_ctrl_when_restricted=True,
        )
        self.assertFalse(usb_stream_bad.valid)

    def test_35_g138_4ch_audio_and_fx6_sdi_remote_if_contrast(self) -> None:
        self.assertEqual(ALLOWED_4CH_AUDIO_OUTPUT_G138, (AUDIO_4CH_CH1_CH2_G138, AUDIO_4CH_CH3_CH4_G138))
        ch34 = verify_tc_make_hdmi_rec_ssh_authen_fan_guard(
            audio_4ch_output_channels=AUDIO_4CH_CH3_CH4_G138,
            fx6_sdi_hdmi_rec_ctrl_mode=FX6_SDI_HDMI_REMOTE_IF_G138,
        )
        self.assertTrue(ch34.valid)
        self.assertEqual(ch34.audio_4ch_output_channels, AUDIO_4CH_CH3_CH4_G138)
        self.assertEqual(ch34.fx6_sdi_hdmi_rec_ctrl_mode, FX6_SDI_HDMI_REMOTE_IF_G138)
        self.assertTrue(ch34.fx6_parallel_rec_follows_slot_a)

        bad_sdi = verify_tc_make_hdmi_rec_ssh_authen_fan_guard(
            claimed_fx3_has_sdi_remote_if_or_bnc_tc_switch=True,
        )
        self.assertFalse(bad_sdi.valid)
        self.assertEqual(bad_sdi.block_errno, EOPNOTSUPP_ERRNO_PHASE313)

    def test_36_g138_ssh_access_authen_persistence_and_resets(self) -> None:
        cam_rst = verify_tc_make_hdmi_rec_ssh_authen_fan_guard(
            requested_access_authen_settings="Off",
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE313,
        )
        self.assertTrue(cam_rst.valid)
        self.assertEqual(cam_rst.effective_access_authen_settings, "Off")
        self.assertFalse(cam_rst.sshd_control_active)
        self.assertTrue(cam_rst.access_authen_survived_cam_reset)

        net_rst = verify_tc_make_hdmi_rec_ssh_authen_fan_guard(
            requested_access_authen_settings="Off",
            reset_action=RESET_ACTION_RESET_NETWORK_SET_PHASE313,
        )
        self.assertTrue(net_rst.valid)
        self.assertEqual(net_rst.effective_access_authen_settings, "On")
        self.assertTrue(net_rst.sshd_control_active)
        self.assertTrue(net_rst.access_authen_reset_by_net_or_init)
        self.assertEqual(net_rst.access_authen_transports, ALLOWED_ACCESS_AUTHEN_TRANSPORTS_G138)

        init_rst = verify_tc_make_hdmi_rec_ssh_authen_fan_guard(
            requested_access_authen_settings="Off",
            reset_action=RESET_ACTION_INITIALIZE_PHASE313,
        )
        self.assertTrue(init_rst.valid)
        self.assertEqual(init_rst.effective_access_authen_settings, "On")
        self.assertTrue(init_rst.sshd_control_active)

    def test_37_g138_zero_http_digest_https_server_myths_and_root_cert_slot1(self) -> None:
        for myth in FORBIDDEN_HTTP_AUTH_MYTHS_G138:
            bad = verify_tc_make_hdmi_rec_ssh_authen_fan_guard(
                requested_http_auth_protocol=myth,
            )
            self.assertFalse(bad.valid)
            self.assertTrue(bad.http_digest_or_https_server_blocked)
            self.assertEqual(bad.block_errno, EOPNOTSUPP_ERRNO_PHASE313)
            self.assertIn(
                STATUS_BLOCKED_G138_SSH_ACCESS_AUTHEN_HTTPS_MYTH_OR_CERT_VIOLATION,
                bad.violation_codes,
            )

        bad_inbound = verify_tc_make_hdmi_rec_ssh_authen_fan_guard(
            claimed_root_cert_is_inbound_https_server=True,
        )
        self.assertFalse(bad_inbound.valid)
        self.assertEqual(bad_inbound.block_errno, EOPNOTSUPP_ERRNO_PHASE313)

        slot2_cert = verify_tc_make_hdmi_rec_ssh_authen_fan_guard(
            import_root_cert_requested=True,
            import_root_cert_type="FTPS",
            import_root_cert_slot=MEDIA_SLOT_2_PHASE313,
            slot_1_contains_tier0_vault=True,
        )
        self.assertTrue(slot2_cert.valid)
        self.assertTrue(slot2_cert.import_root_cert_outbound_client_tls_only)

        slot1_cert_blocked = verify_tc_make_hdmi_rec_ssh_authen_fan_guard(
            import_root_cert_requested=True,
            import_root_cert_type="RTMPS",
            import_root_cert_slot=MEDIA_SLOT_1_PHASE313,
            slot_1_contains_tier0_vault=True,
        )
        self.assertFalse(slot1_cert_blocked.valid)
        self.assertTrue(slot1_cert_blocked.slot1_vault_cert_blocked)
        self.assertEqual(slot1_cert_blocked.block_errno, EROFS_ERRNO_PHASE313)
        self.assertEqual(slot1_cert_blocked.slot1_data_sector_writes, 0)

    def test_38_g138_fan_control_4mode_fx3_vs_3mode_fx6_zero_max_truth(self) -> None:
        self.assertEqual(len(FX3_EXACT_4_FAN_MODES_G138), 4)
        self.assertEqual(len(FX6_EXACT_3_FAN_MODES_G138), 3)
        for mode in FX3_EXACT_4_FAN_MODES_G138:
            ok = verify_tc_make_hdmi_rec_ssh_authen_fan_guard(
                target_model=FX3_MODEL_NAME_PHASE313,
                requested_fan_control=mode,
            )
            self.assertTrue(ok.valid)
            self.assertEqual(ok.effective_fan_control, mode)
            self.assertEqual(ok.fx3_exact_fan_modes_count, 4)
            self.assertEqual(ok.fx6_exact_fan_modes_count, 3)

        for myth in FORBIDDEN_FAN_MAX_TOKENS_G138:
            for cam in (FX3_MODEL_NAME_PHASE313, FX6_MODEL_NAME_PHASE313):
                bad = verify_tc_make_hdmi_rec_ssh_authen_fan_guard(
                    target_model=cam,
                    requested_fan_control=myth,
                )
                self.assertFalse(bad.valid)
                self.assertTrue(bad.fan_max_myth_blocked)
                self.assertEqual(bad.block_errno, EOPNOTSUPP_ERRNO_PHASE313)
                self.assertIn(
                    STATUS_BLOCKED_G138_FAN_MAX_MYTH_OR_FX6_ALWAYS_OFF_VIOLATION,
                    bad.violation_codes,
                )

        bad_fx6_always_off = verify_tc_make_hdmi_rec_ssh_authen_fan_guard(
            target_model=FX6_MODEL_NAME_PHASE313,
            requested_fan_control=FAN_CONTROL_ALWAYS_OFF_G138,
        )
        self.assertFalse(bad_fx6_always_off.valid)
        self.assertTrue(bad_fx6_always_off.fx6_always_off_dormant_blocked)
        self.assertEqual(bad_fx6_always_off.block_errno, EOPNOTSUPP_ERRNO_PHASE313)

    def test_39_g138_fan_off_in_rec_temp_override_and_initialize_reset(self) -> None:
        ovr = verify_tc_make_hdmi_rec_ssh_authen_fan_guard(
            requested_fan_control=FAN_CONTROL_OFF_IN_REC_G138,
            requested_auto_pwr_off_temp=AUTO_PWR_OFF_TEMP_HIGH_G138,
            internal_temp_exceeded_threshold=True,
        )
        self.assertTrue(ovr.valid)
        self.assertTrue(ovr.fan_off_in_rec_temp_override_active)
        self.assertTrue(ovr.low_temp_burn_tripod_warning)

        init_rst = verify_tc_make_hdmi_rec_ssh_authen_fan_guard(
            requested_tc_make=TC_MAKE_REGENERATE_G138,
            requested_hdmi_rec_control="On",
            requested_fan_control=FAN_CONTROL_MINIMUM_G138,
            requested_auto_pwr_off_temp=AUTO_PWR_OFF_TEMP_HIGH_G138,
            reset_action=RESET_ACTION_INITIALIZE_PHASE313,
        )
        self.assertTrue(init_rst.valid)
        self.assertEqual(init_rst.effective_tc_make, TC_MAKE_PRESET_G138)
        self.assertEqual(init_rst.effective_hdmi_rec_control, "Off")
        self.assertEqual(init_rst.effective_fan_control, FAN_CONTROL_AUTO_G138)
        self.assertEqual(init_rst.effective_auto_pwr_off_temp, AUTO_PWR_OFF_TEMP_STANDARD_G138)

    def test_40_g138_256_state_matrix_and_telemetry_validation(self) -> None:
        mat = compute_tc_make_ssh_authen_fan_matrix()
        self.assertEqual(mat["states_checked"], 256)
        self.assertEqual(mat["tc_regen_forced_rec_count"], 128)
        self.assertEqual(mat["cardless_hdmi_rec_ctrl_count"], 64)
        self.assertEqual(mat["sshd_active_count"], 128)
        self.assertEqual(mat["fan_temp_override_count"], 32)

        bad_id = verify_tc_make_hdmi_rec_ssh_authen_fan_guard(body_model_id=True)  # type: ignore[arg-type]
        self.assertFalse(bad_id.valid)
        self.assertIn(STATUS_BLOCKED_G138_TELEMETRY_INVALID, bad_id.violation_codes)

        bad_target = verify_tc_make_hdmi_rec_ssh_authen_fan_guard(target_model="ILCE-1")
        self.assertFalse(bad_target.valid)

        bad_fan = verify_tc_make_hdmi_rec_ssh_authen_fan_guard(requested_fan_control="TURBO")
        self.assertFalse(bad_fan.valid)

        bad_cert = verify_tc_make_hdmi_rec_ssh_authen_fan_guard(import_root_cert_type="HTTPS_INBOUND")
        self.assertFalse(bad_cert.valid)

        res_dict = resolve_fx3_tc_make_ssh_authen_fan_state()
        self.assertTrue(res_dict["valid"])
        self.assertEqual(res_dict["status"], STATUS_VERIFIED_G138)


class TestUnified138GateMasterPreflightAndCLIs(unittest.TestCase):
    def test_41_master_138_offline_clean_room_reaches_135_of_138(self) -> None:
        rep = evaluate_138gate_preflight(force_clean_room=True)
        self.assertIsInstance(rep, Master138GateReport)
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(rep.status, "VERIFIED_135_OF_138_AWAITING_PHYSICAL_TIER0")
        self.assertEqual(rep.summary["total_gates"], 138)
        self.assertEqual(rep.summary["verified_gates"], 135)
        self.assertEqual(rep.summary["blocked_or_pending_gates"], 3)
        self.assertTrue(rep.offline_135_gates_verified)
        self.assertFalse(rep.all_138_gates_verified)
        self.assertTrue(rep.g137_to_g138_all_passed)
        self.assertTrue(rep.g13_to_g138_all_passed)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.hardware_live_attachment_authorized)
        self.assertTrue(rep.agent_auto_flash_blocked)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)
        self.assertEqual(len(rep.gates), 138)

    def test_42_master_138_simulated_dry_run_reaches_138_of_138(self) -> None:
        rep = evaluate_138gate_preflight(
            force_clean_room=True,
            simulate_bench_dry_run=True,
        )
        self.assertEqual(rep.status, "VERIFIED_ALL_138_GATES_DRY_RUN_SIMULATED_BACKUP")
        self.assertEqual(rep.summary["verified_gates"], 138)
        self.assertEqual(rep.summary["blocked_or_pending_gates"], 0)
        self.assertTrue(rep.all_138_gates_verified)
        self.assertTrue(rep.dry_run_rehearsal_only)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.hardware_live_attachment_authorized)
        self.assertFalse(rep.cross_model_flash_authorized)
        self.assertEqual(rep.usb_packets_transmitted, 0)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_43_master_138_donor_default_mode_consistent(self) -> None:
        rep = evaluate_138gate_preflight()
        self.assertEqual(rep.summary["total_gates"], 138)
        self.assertEqual(rep.summary["verified_gates"], 135)
        self.assertTrue(rep.offline_135_gates_verified)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_44_master_138_aliases_and_serialization(self) -> None:
        r1 = evaluate_138_master_safety_gates(force_clean_room=True, dry_run_simulated=True)
        r2 = run_138_gate_preflight(force_clean_room=True, dry_run_simulated_backup=True)
        self.assertTrue(r1.all_138_gates_verified)
        self.assertTrue(r2.all_138_gates_verified)
        d = r1.to_dict()
        self.assertEqual(d["summary"]["verified_gates"], 138)
        self.assertEqual(d["g137_result"]["status"], STATUS_VERIFIED_G137)
        self.assertEqual(d["g138_result"]["status"], STATUS_VERIFIED_G138)

    def test_45_master_138_blocks_persistent_emmc_writes(self) -> None:
        stub = _build_stub_136_report()
        rep = evaluate_138gate_preflight(
            force_clean_room=True,
            request_persistent_emmc_writes=True,
            master_136_override=stub,
        )
        self.assertEqual(rep.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        self.assertFalse(rep.offline_135_gates_verified)
        self.assertFalse(rep.h0_h1_trial_entry_allowed)
        self.assertFalse(rep.overall_ready_for_hardware_attach)

    def test_46_master_138_propagates_g137_failure(self) -> None:
        stub = _build_stub_136_report()
        rep = evaluate_138gate_preflight(
            force_clean_room=True,
            master_136_override=stub,
            big6_home_framing_interval_kwargs={
                "shoot_mode": SHOOT_MODE_STILL_PHASE313,
                "requested_interval_shooting": "On",
                "requested_target_slot": MEDIA_SLOT_1_PHASE313,
                "slot_1_contains_tier0_vault": True,
            },
        )
        self.assertEqual(rep.status, STATUS_BLOCKED_G137_SLOT1_INTERVAL_9999_VAULT_FIREWALL_VIOLATION)
        self.assertFalse(rep.g137_to_g138_all_passed)
        self.assertFalse(rep.offline_135_gates_verified)

    def test_47_master_138_propagates_g138_failure(self) -> None:
        stub = _build_stub_136_report()
        rep = evaluate_138gate_preflight(
            force_clean_room=True,
            master_136_override=stub,
            tc_make_ssh_fan_kwargs={"requested_fan_control": "MAX"},
        )
        self.assertEqual(rep.status, STATUS_BLOCKED_G138_FAN_MAX_MYTH_OR_FX6_ALWAYS_OFF_VIOLATION)
        self.assertFalse(rep.g137_to_g138_all_passed)
        self.assertFalse(rep.offline_135_gates_verified)

    def test_48_master_138_propagates_upstream_m136_failure(self) -> None:
        bad_stub = _build_stub_136_report(all_g13_136_ok=False)
        rep = evaluate_138gate_preflight(
            force_clean_room=True,
            master_136_override=bad_stub,
        )
        self.assertFalse(rep.g13_to_g138_all_passed)
        self.assertFalse(rep.offline_135_gates_verified)

    def test_49_milestone295_dynamic_auto_discovery_reaches_at_least_138_gates(self) -> None:
        candidates = []
        for name in fx3_safety.__all__:
            m = re.match(r"^evaluate_(\d+)gate_preflight$", name)
            if m:
                candidates.append((int(m.group(1)), name))
        highest = max(candidates)
        self.assertGreaterEqual(highest[0], 138)
        self.assertIn((138, "evaluate_138gate_preflight"), candidates)

    def test_50_cli_verify_138_gates_json_summary_clean_room_and_dry_run(self) -> None:
        buf1 = io.StringIO()
        with contextlib.redirect_stdout(buf1):
            rc1 = cli_main(["verify-138-gates", "--clean-room", "--summary", "--json"])
        self.assertEqual(rc1, 0)
        p1 = json.loads(buf1.getvalue())
        self.assertEqual(p1["status"], "VERIFIED_135_OF_138_AWAITING_PHYSICAL_TIER0")
        self.assertEqual(p1["summary"]["verified_gates"], 135)
        self.assertEqual(p1["g137_status"], STATUS_VERIFIED_G137)
        self.assertEqual(p1["g138_status"], STATUS_VERIFIED_G138)

        buf2 = io.StringIO()
        with contextlib.redirect_stdout(buf2):
            rc2 = cli_main(
                ["verify-138-gates", "--clean-room", "--simulate-bench-dry-run", "--summary", "--json"]
            )
        self.assertEqual(rc2, 0)
        p2 = json.loads(buf2.getvalue())
        self.assertEqual(p2["status"], "VERIFIED_ALL_138_GATES_DRY_RUN_SIMULATED_BACKUP")
        self.assertEqual(p2["summary"]["verified_gates"], 138)
        self.assertEqual(p2["summary"]["raw_firmware_bytes_leaked"], 0)

    def test_51_cli_g137_and_g138_subcommands_and_aliases(self) -> None:
        for cmd in (
            "verify-big6-home-framing-interval-vault-guard",
            "verify-g137-big6-home-framing-interval",
            "verify-tc-make-hdmi-rec-ssh-authen-fan-guard",
            "verify-g138-tc-make-hdmi-rec-ssh-fan",
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = cli_main([cmd, "--clean-room", "--summary", "--json"])
            self.assertEqual(rc, 0)
            payload = json.loads(buf.getvalue())
            self.assertTrue(payload["valid"])
            self.assertEqual(payload["raw_firmware_bytes_leaked"], 0)

    def test_52_cli_text_outputs_and_module_main(self) -> None:
        from fx3_safety.realhw_big6_home_framing_interval_tc_ssh_fan_and_138gate_guard import (
            main as mod_main,
        )

        for argv in (
            ["--clean-room", "--gate", "g137", "--summary", "--json"],
            ["--clean-room", "--gate", "g138", "--summary", "--json"],
            ["--clean-room", "--gate", "138", "--simulate-bench-dry-run", "--summary", "--json"],
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = mod_main(argv)
            self.assertEqual(rc, 0)
            self.assertTrue(json.loads(buf.getvalue()))

    def test_53_subprocess_help_python314_percent_safe(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONPATH"] = str(DEFAULT_REPO_ROOT / "outputs" / "fx3-safety")
        for subcmd in (
            "--help",
            "verify-big6-home-framing-interval-vault-guard --help",
            "verify-tc-make-hdmi-rec-ssh-authen-fan-guard --help",
            "verify-138-gates --help",
        ):
            proc = subprocess.run(
                [sys.executable, "-B", "-m", "fx3_safety", *subcmd.split()],
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, msg=proc.stderr)

    def test_54_subprocess_cli_verify_138_gates_both_modes(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONPATH"] = str(DEFAULT_REPO_ROOT / "outputs" / "fx3-safety")
        env["FX3_FX6_FORCE_CLEAN_ROOM"] = "1"
        p1 = subprocess.run(
            [sys.executable, "-B", "-m", "fx3_safety", "verify-138-gates", "--summary", "--json"],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(p1.returncode, 0, msg=p1.stderr)
        j1 = json.loads(p1.stdout)
        self.assertEqual(j1["summary"]["verified_gates"], 135)

        p2 = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "fx3_safety",
                "verify-138-gates",
                "--simulate-bench-dry-run",
                "--summary",
                "--json",
            ],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(p2.returncode, 0, msg=p2.stderr)
        j2 = json.loads(p2.stdout)
        self.assertEqual(j2["summary"]["verified_gates"], 138)


# Additional fine-grained matrix, enum, edge-case, and negative-path unit tests (55..88)
class TestWave59FineGrainedEdgeCasesPhase313(unittest.TestCase):
    def test_55_g137_all_mode_settings_enum_check(self) -> None:
        self.assertEqual(
            ALLOWED_MODE_SETTINGS_G137,
            (MODE_SETTINGS_FIXED_VARIABLE_G137, MODE_SETTINGS_FIXED_FPS_G137),
        )

    def test_56_g137_all_pasm_and_exposure_modes(self) -> None:
        self.assertEqual(
            ALLOWED_PASM_MODES_G137,
            (EXPOSURE_MODE_P_G137, EXPOSURE_MODE_A_G137, EXPOSURE_MODE_S_G137, EXPOSURE_MODE_M_G137),
        )
        self.assertIn(EXPOSURE_MODE_INTELLIGENT_AUTO_G137, ALLOWED_EXPOSURE_MODES_G137)

    def test_57_g137_shutter_speed_vs_angle_modes(self) -> None:
        for sm in ALLOWED_SHUTTER_MODES_G137:
            res = verify_big6_home_framing_interval_vault_guard(shutter_mode=sm)
            self.assertTrue(res.valid)
            self.assertEqual(res.shutter_mode, sm)

    def test_58_g137_all_log_shooting_modes_supported(self) -> None:
        self.assertEqual(len(ALLOWED_LOG_SHOOTING_MODES_G137), 4)
        for lm in ALLOWED_LOG_SHOOTING_MODES_G137:
            res = verify_big6_home_framing_interval_vault_guard(log_shooting_mode=lm)
            self.assertTrue(res.valid)
            self.assertEqual(res.log_shooting_mode, lm)

    def test_59_g137_all_big6_entry_triggers(self) -> None:
        self.assertEqual(
            ALLOWED_BIG6_ENTRY_TRIGGERS_G137,
            (BIG6_ENTRY_NONE_G137, BIG6_ENTRY_HOME_KEY_G137, BIG6_ENTRY_SWIPE_DOWN_G137),
        )

    def test_60_g137_home_lower_left_modes_tuple(self) -> None:
        self.assertEqual(
            ALLOWED_HOME_LOWER_LEFT_MODES_G137,
            (HOME_LOWER_LEFT_APERTURE_G137, HOME_LOWER_LEFT_ND_FILTER_G137),
        )

    def test_61_g137_framing_rec_stream_and_hdmi_enums(self) -> None:
        self.assertEqual(
            ALLOWED_FRAMING_REC_STREAM_MODES_G137,
            (FRAMING_REC_STREAM_FULL_G137, FRAMING_REC_STREAM_CROP_G137),
        )
        self.assertEqual(
            ALLOWED_FRAMING_HDMI_MODES_G137,
            (FRAMING_HDMI_CROP_G137, FRAMING_HDMI_FULL_G137),
        )

    def test_62_g137_interval_ae_tracking_and_shutter_and_still_formats(self) -> None:
        self.assertEqual(ALLOWED_AE_TRACKING_SENSITIVITIES_G137, ("High", "Mid", "Low"))
        self.assertEqual(
            ALLOWED_INTERVAL_SHUTTER_TYPES_G137,
            (INTERVAL_SHUTTER_ELECTRONIC_G137, INTERVAL_SHUTTER_MECHANICAL_G137),
        )
        self.assertEqual(
            ALLOWED_INTERVAL_STILL_FORMATS_G137,
            (
                INTERVAL_STILL_FORMAT_RAW_G137,
                INTERVAL_STILL_FORMAT_JPEG_G137,
                INTERVAL_STILL_FORMAT_HEIF_G137,
                INTERVAL_STILL_FORMAT_RAW_JPEG_G137,
                INTERVAL_STILL_FORMAT_RAW_HEIF_G137,
            ),
        )

    def test_63_g137_interval_9999_dcim_file_count_doubles_for_raw_plus_jpeg_heif(self) -> None:
        raw_only = verify_big6_home_framing_interval_vault_guard(
            shoot_mode=SHOOT_MODE_STILL_PHASE313,
            requested_interval_shooting="On",
            requested_target_slot=MEDIA_SLOT_2_PHASE313,
            interval_shot_count=INTERVAL_SHOTS_MAX_G137,
            interval_still_format=INTERVAL_STILL_FORMAT_RAW_G137,
        )
        self.assertTrue(raw_only.valid)
        self.assertEqual(raw_only.interval_max_dcim_files, 9999)

        raw_heif = verify_big6_home_framing_interval_vault_guard(
            shoot_mode=SHOOT_MODE_STILL_PHASE313,
            requested_interval_shooting="On",
            requested_target_slot=MEDIA_SLOT_2_PHASE313,
            interval_shot_count=INTERVAL_SHOTS_MAX_G137,
            interval_still_format=INTERVAL_STILL_FORMAT_RAW_HEIF_G137,
        )
        self.assertTrue(raw_heif.valid)
        self.assertEqual(raw_heif.interval_max_dcim_files, 19998)

    def test_64_g137_framing_survives_net_reset_and_resets_on_cam_and_init(self) -> None:
        net_rst = verify_big6_home_framing_interval_vault_guard(
            requested_framing_on=True,
            reset_action=RESET_ACTION_RESET_NETWORK_SET_PHASE313,
        )
        self.assertTrue(net_rst.valid)
        self.assertTrue(net_rst.effective_framing_on)

        for rst in (
            RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE313,
            RESET_ACTION_INITIALIZE_PHASE313,
        ):
            cleared = verify_big6_home_framing_interval_vault_guard(
                requested_framing_on=True,
                reset_action=rst,
            )
            self.assertTrue(cleared.valid)
            self.assertFalse(cleared.effective_framing_on)

    def test_65_g137_big6_mode_settings_preserves_net_reset_and_resets_on_cam_and_init(self) -> None:
        net_rst = verify_big6_home_framing_interval_vault_guard(
            requested_mode_settings=MODE_SETTINGS_FIXED_VARIABLE_G137,
            shutter_mode=SHUTTER_MODE_ANGLE_G137,
            reset_action=RESET_ACTION_RESET_NETWORK_SET_PHASE313,
        )
        self.assertEqual(net_rst.effective_mode_settings, MODE_SETTINGS_FIXED_VARIABLE_G137)

        for rst in (
            RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE313,
            RESET_ACTION_INITIALIZE_PHASE313,
        ):
            cleared = verify_big6_home_framing_interval_vault_guard(
                requested_mode_settings=MODE_SETTINGS_FIXED_VARIABLE_G137,
                shutter_mode=SHUTTER_MODE_ANGLE_G137,
                reset_action=rst,
            )
            self.assertEqual(cleared.effective_mode_settings, MODE_SETTINGS_FIXED_FPS_G137)

    def test_66_g137_interval_limits_min_max_constants(self) -> None:
        self.assertEqual(INTERVAL_START_TIME_MIN_SEC_G137, 1)
        self.assertEqual(INTERVAL_START_TIME_MAX_SEC_G137, 5999)
        self.assertEqual(INTERVAL_PERIOD_MIN_SEC_G137, 1)
        self.assertEqual(INTERVAL_PERIOD_MAX_SEC_G137, 60)
        self.assertEqual(INTERVAL_SHOTS_MIN_G137, 1)
        self.assertEqual(INTERVAL_SHOTS_MAX_G137, 9999)

    def test_67_g137_non_int_fps_and_interval_bounds_rejected(self) -> None:
        bad_fps = verify_big6_home_framing_interval_vault_guard(fps=True)  # type: ignore[arg-type]
        self.assertFalse(bad_fps.valid)
        bad_start = verify_big6_home_framing_interval_vault_guard(interval_start_time_sec=False)  # type: ignore[arg-type]
        self.assertFalse(bad_start.valid)

    def test_68_g137_invalid_target_slot_or_reset_action_rejected(self) -> None:
        bad_slot = verify_big6_home_framing_interval_vault_guard(requested_target_slot="SLOT99")
        self.assertFalse(bad_slot.valid)
        bad_rst = verify_big6_home_framing_interval_vault_guard(reset_action="NUKE")
        self.assertFalse(bad_rst.valid)

    def test_69_g137_evaluate_blocks_persistent_emmc_write_flag(self) -> None:
        v, r = evaluate_g137_big6_home_framing_interval_vault_guard(
            force_clean_room=True,
            request_persistent_emmc_writes=True,
        )
        self.assertFalse(v.passed)
        self.assertFalse(r.valid)
        self.assertIn(STATUS_BLOCKED_PERSISTENT_EMMC_WRITE, r.violation_codes)

    def test_70_g138_evaluate_blocks_persistent_emmc_write_flag(self) -> None:
        v, r = evaluate_g138_tc_make_hdmi_rec_ssh_authen_fan_guard(
            force_clean_room=True,
            request_persistent_emmc_writes=True,
        )
        self.assertFalse(v.passed)
        self.assertFalse(r.valid)
        self.assertIn(STATUS_BLOCKED_PERSISTENT_EMMC_WRITE, r.violation_codes)

    def test_71_g138_tc_make_f_uxc_and_tc_run_f_uxc_ids(self) -> None:
        self.assertEqual(TC_MAKE_F_UXC_RESID16_G138, 0x6B79)
        self.assertEqual(TC_RUN_F_UXC_RESID16_G138, 0x7313)
        self.assertEqual(HDMI_REC_CONTROL_F_UXC_RESID16_G138, 0x76E1)
        self.assertEqual(HDMI_TC_OUTPUT_F_UXC_RESID16_G138, 0x72AF)
        self.assertEqual(HDMI_4CH_AUDIO_OUTPUT_F_UXC_RESID16_G138, 0x6AA0)

    def test_72_g138_allowed_tc_run_rec_media_and_fx6_modes(self) -> None:
        self.assertEqual(ALLOWED_TC_RUN_MODES_G138, (TC_RUN_REC_RUN_G138, TC_RUN_FREE_RUN_G138))
        self.assertEqual(
            ALLOWED_REC_MEDIA_DUR_HDMI_G138,
            (HDMI_REC_MEDIA_ON_G138, HDMI_REC_MEDIA_OFF_HDMI_ONLY_G138),
        )
        self.assertEqual(
            ALLOWED_FX6_SDI_HDMI_REC_CTRL_MODES_G138,
            (FX6_SDI_HDMI_REC_CTRL_OFF_G138, FX6_SDI_HDMI_REMOTE_IF_G138, FX6_PARALLEL_REC_G138),
        )

    def test_73_g138_fx6_parallel_rec_mode_validated(self) -> None:
        res = verify_tc_make_hdmi_rec_ssh_authen_fan_guard(
            target_model=FX6_MODEL_NAME_PHASE313,
            fx6_sdi_hdmi_rec_ctrl_mode=FX6_PARALLEL_REC_G138,
            requested_fan_control=FAN_CONTROL_MINIMUM_G138,
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.fx6_sdi_hdmi_rec_ctrl_mode, FX6_PARALLEL_REC_G138)
        self.assertTrue(res.fx6_parallel_rec_follows_slot_a)

    def test_74_g138_outbound_client_tls_types_only(self) -> None:
        self.assertEqual(OUTBOUND_CLIENT_TLS_TYPES_G138, ("Cloud", "FTPS", "RTMPS"))
        for cert_type in OUTBOUND_CLIENT_TLS_TYPES_G138:
            res = verify_tc_make_hdmi_rec_ssh_authen_fan_guard(
                import_root_cert_requested=True,
                import_root_cert_type=cert_type,
                import_root_cert_slot=MEDIA_SLOT_2_PHASE313,
            )
            self.assertTrue(res.valid)
            self.assertTrue(res.import_root_cert_outbound_client_tls_only)

    def test_75_g138_ssh_and_ptpip_only_in_access_authen_transports(self) -> None:
        self.assertEqual(ALLOWED_ACCESS_AUTHEN_TRANSPORTS_G138, ("SSH", "PTP-IP"))
        self.assertNotIn("HTTPS", ALLOWED_ACCESS_AUTHEN_TRANSPORTS_G138)
        self.assertNotIn("HTTP_DIGEST", ALLOWED_ACCESS_AUTHEN_TRANSPORTS_G138)

    def test_76_g138_fx6_3_fan_modes_valid_and_always_off_blocked(self) -> None:
        self.assertEqual(
            FX6_EXACT_3_FAN_MODES_G138,
            (FAN_CONTROL_AUTO_G138, FAN_CONTROL_MINIMUM_G138, FAN_CONTROL_OFF_IN_REC_G138),
        )
        for m in FX6_EXACT_3_FAN_MODES_G138:
            res = verify_tc_make_hdmi_rec_ssh_authen_fan_guard(
                target_model=FX6_MODEL_NAME_PHASE313,
                requested_fan_control=m,
            )
            self.assertTrue(res.valid)
        bad = verify_tc_make_hdmi_rec_ssh_authen_fan_guard(
            target_model=FX6_MODEL_NAME_PHASE313,
            requested_fan_control=FAN_CONTROL_ALWAYS_OFF_G138,
        )
        self.assertFalse(bad.valid)
        self.assertTrue(bad.fx6_always_off_dormant_blocked)

    def test_77_g138_auto_power_off_temp_standard_vs_high(self) -> None:
        self.assertEqual(
            ALLOWED_AUTO_PWR_OFF_TEMP_MODES_G138,
            (AUTO_PWR_OFF_TEMP_STANDARD_G138, AUTO_PWR_OFF_TEMP_HIGH_G138),
        )
        std = verify_tc_make_hdmi_rec_ssh_authen_fan_guard(
            requested_auto_pwr_off_temp=AUTO_PWR_OFF_TEMP_STANDARD_G138,
        )
        self.assertTrue(std.valid)
        self.assertFalse(std.low_temp_burn_tripod_warning)

        hi = verify_tc_make_hdmi_rec_ssh_authen_fan_guard(
            requested_auto_pwr_off_temp=AUTO_PWR_OFF_TEMP_HIGH_G138,
        )
        self.assertTrue(hi.valid)
        self.assertTrue(hi.low_temp_burn_tripod_warning)

    def test_78_g138_invalid_enum_inputs_all_fail_closed(self) -> None:
        self.assertFalse(
            verify_tc_make_hdmi_rec_ssh_authen_fan_guard(requested_tc_make="NTP").valid
        )
        self.assertFalse(
            verify_tc_make_hdmi_rec_ssh_authen_fan_guard(requested_tc_run="JAM").valid
        )
        self.assertFalse(
            verify_tc_make_hdmi_rec_ssh_authen_fan_guard(audio_4ch_output_channels="CH5/CH6").valid
        )
        self.assertFalse(
            verify_tc_make_hdmi_rec_ssh_authen_fan_guard(rec_media_dur_hdmi_output="MAYBE").valid
        )
        self.assertFalse(
            verify_tc_make_hdmi_rec_ssh_authen_fan_guard(fx6_sdi_hdmi_rec_ctrl_mode="SDI_ONLY").valid
        )
        self.assertFalse(
            verify_tc_make_hdmi_rec_ssh_authen_fan_guard(requested_auto_pwr_off_temp="EXTREME").valid
        )
        self.assertFalse(
            verify_tc_make_hdmi_rec_ssh_authen_fan_guard(import_root_cert_slot=MEDIA_SIMULT_RECORDING_PHASE313).valid
        )

    def test_79_shared_model_and_fw_identity_constants(self) -> None:
        self.assertEqual(FX3_MODEL_NAME_PHASE313, "ILME-FX3")
        self.assertEqual(FX3_MODEL_ID_PHASE313, 0x39383232)
        self.assertEqual(FX3_HELP_GUIDE_CODE_PHASE313, "ilc/2210")
        self.assertEqual(FX3_DEFAULT_FW_VERSION_PHASE313, "7.02")
        self.assertEqual(FX6_MODEL_NAME_PHASE313, "ILME-FX6")
        self.assertEqual(FX6_PRODUCT_CODE_PHASE313, "PRODUCT_MODEL_CHAPLIN")
        self.assertEqual(FX6_DEFAULT_FW_VERSION_PHASE313, "6.01")

    def test_80_shared_mode_and_reset_tuples(self) -> None:
        self.assertEqual(
            ALLOWED_SHOOT_MODES_PHASE313,
            (SHOOT_MODE_STILL_PHASE313, SHOOT_MODE_MOVIE_PHASE313, SHOOT_MODE_SQ_PHASE313),
        )
        self.assertEqual(
            ALLOWED_RECORDING_MEDIA_MODES_PHASE313,
            (MEDIA_SLOT_1_PHASE313, MEDIA_SLOT_2_PHASE313, MEDIA_SIMULT_RECORDING_PHASE313),
        )
        self.assertEqual(
            ALLOWED_RESET_ACTIONS_PHASE313,
            (
                RESET_ACTION_NONE_PHASE313,
                RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE313,
                RESET_ACTION_RESET_NETWORK_SET_PHASE313,
                RESET_ACTION_INITIALIZE_PHASE313,
            ),
        )

    def test_81_g137_all_7_interval_params_preserve_on_net_reset_and_reset_on_cam_and_init(self) -> None:
        net_rst = verify_big6_home_framing_interval_vault_guard(
            shoot_mode=SHOOT_MODE_STILL_PHASE313,
            requested_interval_shooting="On",
            requested_target_slot=MEDIA_SLOT_2_PHASE313,
            reset_action=RESET_ACTION_RESET_NETWORK_SET_PHASE313,
            interval_shot_count=250,
        )
        self.assertTrue(net_rst.valid)
        self.assertEqual(net_rst.effective_interval_shooting, "On")
        self.assertEqual(net_rst.interval_shot_count, 250)

        for rst in (
            RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE313,
            RESET_ACTION_INITIALIZE_PHASE313,
        ):
            cleared = verify_big6_home_framing_interval_vault_guard(
                shoot_mode=SHOOT_MODE_STILL_PHASE313,
                requested_interval_shooting="On",
                requested_target_slot=MEDIA_SLOT_2_PHASE313,
                reset_action=rst,
                interval_shot_count=250,
            )
            self.assertTrue(cleared.valid)
            self.assertEqual(cleared.effective_interval_shooting, "Off")
            self.assertEqual(cleared.interval_shot_count, 30)

    def test_82_g138_tc_make_and_fan_control_preserve_on_cam_and_net_resets(self) -> None:
        for rst in (
            RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE313,
            RESET_ACTION_RESET_NETWORK_SET_PHASE313,
        ):
            res = verify_tc_make_hdmi_rec_ssh_authen_fan_guard(
                requested_tc_make=TC_MAKE_REGENERATE_G138,
                requested_fan_control=FAN_CONTROL_ALWAYS_OFF_G138,
                reset_action=rst,
            )
            self.assertTrue(res.valid)
            self.assertEqual(res.effective_tc_make, TC_MAKE_REGENERATE_G138)
            self.assertEqual(res.effective_fan_control, FAN_CONTROL_ALWAYS_OFF_G138)

    def test_83_g138_still_mode_restricts_hdmi_rec_control(self) -> None:
        st = verify_tc_make_hdmi_rec_ssh_authen_fan_guard(
            shoot_mode=SHOOT_MODE_STILL_PHASE313,
            hdmi_tc_output="On",
            requested_hdmi_rec_control="On",
        )
        self.assertTrue(st.valid)
        self.assertEqual(st.effective_hdmi_rec_control, "Off")
        self.assertIn("shoot_mode_Still", st.hdmi_rec_ctrl_restricted_reasons)

    def test_84_g138_hdmi_rec_control_in_movie_with_tc_out_on_passes(self) -> None:
        mv = verify_tc_make_hdmi_rec_ssh_authen_fan_guard(
            shoot_mode=SHOOT_MODE_MOVIE_PHASE313,
            hdmi_tc_output="On",
            requested_hdmi_rec_control="On",
            rec_media_dur_hdmi_output=HDMI_REC_MEDIA_ON_G138,
        )
        self.assertTrue(mv.valid)
        self.assertEqual(mv.effective_hdmi_rec_control, "On")
        self.assertFalse(mv.cardless_hdmi_rec_ctrl_permitted)

    def test_85_master_138_gate_ids_g01_through_g138_complete_and_ordered(self) -> None:
        rep = evaluate_138gate_preflight(force_clean_room=True)
        gate_ids = [g["gate_id"] for g in rep.gates]
        self.assertEqual(len(gate_ids), 138)
        for idx in range(1, 139):
            self.assertTrue(
                gate_ids[idx - 1].startswith(f"G{idx:02d}"),
                msg=f"Gate at index {idx - 1} was {gate_ids[idx - 1]}",
            )
        self.assertEqual(gate_ids[-2:], ["G137", "G138"])

    def test_86_cli_verify_138_gates_plain_text_mode(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cli_main(["verify-138-gates", "--clean-room"])
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("verified=135/138", out)
        self.assertIn("raw_firmware_bytes_leaked=0", out)
        self.assertIn("overall_ready_for_hardware_attach=False", out)

    def test_87_cli_g137_and_g138_plain_text_mode(self) -> None:
        for cmd in (
            "verify-big6-home-framing-interval-vault-guard",
            "verify-tc-make-hdmi-rec-ssh-authen-fan-guard",
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = cli_main([cmd, "--clean-room"])
            self.assertEqual(rc, 0)
            self.assertIn("valid=True", buf.getvalue())

    def test_88_cli_verify_138_gates_json_full_report_zero_leaks(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cli_main(["verify-138-gates", "--clean-room", "--simulate-bench-dry-run", "--json"])
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["schema"], REALHW_BIG6_HOME_FRAMING_INTERVAL_TC_SSH_FAN_138GATE_SCHEMA)
        self.assertEqual(len(payload["gates"]), 138)
        self.assertEqual(payload["raw_firmware_bytes_leaked"], 0)
        self.assertFalse(payload["overall_ready_for_hardware_attach"])


if __name__ == "__main__":
    unittest.main()
