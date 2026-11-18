"""Phase 319 (Task H381, Wave-61, 142/142 Safety Gates):
Dual-Mode Unit Tests (92 tests) for
`fx3_safety.realhw_ftp_ftpes_customwb_af_focusmap_marker_and_142gate_guard`:

- Gate `G141` (`REALHW_FTP_FTPES_9SLOT_ZERO_SFTP_AVF_VAULT_AND_CUSTOMWB_CINEEI_GUARD`):
  - Exact 9 FTP server slots (`Server 1..9`, `BKID_APP_ftp_server_settings_*0..8`, reset via
    `[Reset Network Set.]` / `[Initialize]`), `FTP`/`FTPES` (Explicit TLS) Passive Mode ONLY —
    zero `SFTP` (`EOPNOTSUPP=95`), zero Implicit FTPS `990` (`EOPNOTSUPP=95`), zero Active Mode
    (`EOPNOTSUPP=95`), dormant `[Transfer JPEG Size]`/`[Transfer HEIF Size]` (`0x6aed`/`0x63dd`,
    `EOPNOTSUPP=95`), `Specify Directory` <= 128 chars, vs FX6 (`3` UI / `16` ELF slots,
    `certification.pem` on `Slot B`, `Chunk` Proxy mutually exclusive with `Simul/Relay Rec`).
  - `Slot-1` `AVF_INFO` mutation (`save_ftp_transfer_list_to_media` / `.uxc 0x0a13`) blocked
    `EROFS=30` (`slot1_data_sector_writes == 0`, `cacert.pem` `<= 1 MB` strictly `O_RDONLY`),
    plus Zero-RF `USB-LAN` bypass lock (`Airplane=On` + `FTP=Off` + `USB-LAN=Disconnected`).
  - White Balance (`2500K..9900K`, `Custom 1..3` `A-B` `+-7` `0.5` / `G-M` `+-7` `0.25` excluded
    from `CAMSET*.DAT` & wiped ONLY by `[Initialize]`), `Custom WB Error` `0x0220` under
    `Log != Off` / `S-Log3` / `PPLUT1..4`, `Cine EI` / `Cine EI Quick` Auto lockout, Still
    `[Shutter AWB Lock]` vs resettable Movie `[Shockless WB]` (`Off/1..3`) & `[Priority Set in
    AWB]`, vs FX6 `WHT BAL` (`PRST/A/B`), `Memory A..H`, `ATW` locked in `Cine EI`.
- Gate `G142` (`REALHW_MOVIE_AF_1TO7_1TO5_EXTERNAL_FOCUSMAP_AND_15ASPECT_MARKER_PEAKING_GUARD`):
  - Empirical disambiguation: BOTH `FX3` and `FX6` use `1..7` for `[AF Transition Speed]`
    (FX3 default `5`) and `1..5` for `[AF Subj. Shift Sensitivity]` (FX3 default `5`; `6`/`7`
    rejected `EINVAL=22` on BOTH models!), plus resettable `[AF Assist]` incompatible with
    `SELP1650`/`SEL18200LE`.
  - `[Focus Map]` myth-bust: `ILME-FX3` has ZERO on-body `[Focus Map]` menu (`EOPNOTSUPP=95`),
    only external *Monitor & Control* (`Ver. >= 6.00`, valid at `100p`/`119.88p`, blocked at
    `>= 150fps`, Playback, Auto Framing, USB wired remote, UVC, `HDMI RAW`, Focus Magnifier,
    Digital Extender, non-PDAF/MF/LA-EA/no lens), vs FX6 native on-body `[Focus Map]` (`< 6fps`
    blocked).
  - Exact 15 active `[Aspect Marker]` ratios + `Off` = 16 states, `[Center Marker]`,
    `[Safety Zone]` (`Off/80%/90%` vs FX6 `92.5%/95%`), `[Guideframe]`, Focus Magnifier auto-hide,
    `[Peaking Display]` (`High/Mid/Low`, 4 FX3 colors vs FX6 `B&W`), `Initialize`-only wipe and
    NEVER output on HDMI, vs FX6 `User Box` & `Aspect Mask` (`0..15`).
- Unified `142`-Gate Master Safety Preflight (`evaluate_142gate_preflight` / `verify-142-gates`):
  - `schema_version == "realhw_142gate_preflight_v1"`, `139/142` offline, `142/142` dry-run,
    all hardware attach & persistent write redlines locked `False` (`raw_firmware_bytes_leaked == 0`),
    donorless `work_root=None` clean-room fallback without `TypeError`, and forward-compatible
    dynamic discovery (`(142, "evaluate_142gate_preflight") in candidates` & `highest[0] >= 142`).
"""

from __future__ import annotations

import contextlib
import dataclasses
import hashlib
import io
import json
import os
from pathlib import Path
import re
import tempfile
import unittest
from unittest import mock

import fx3_safety
from fx3_safety.__main__ import main as cli_main
from fx3_safety.realhw_ftp_ftpes_customwb_af_focusmap_marker_and_142gate_guard import (
    AF_ASSIST_F_UXC_RESID16_G142,
    AF_ASSIST_INCOMPATIBLE_LENSES_G142,
    AF_SUBJ_SHIFT_SENS_DEFAULT_G142,
    AF_SUBJ_SHIFT_SENS_F_UXC_RESID16_G142,
    AF_SUBJ_SHIFT_SENS_MAX_G142,
    AF_SUBJ_SHIFT_SENS_MIN_G142,
    AF_TRANSITION_SPEED_DEFAULT_G142,
    AF_TRANSITION_SPEED_F_UXC_RESID16_G142,
    AF_TRANSITION_SPEED_MAX_G142,
    AF_TRANSITION_SPEED_MIN_G142,
    ALLOWED_ASPECT_MARKER_STATES_FX3_G142,
    ALLOWED_FTP_CLIP_FLAGS_G141,
    ALLOWED_FTP_DIR_HIERARCHIES_G141,
    ALLOWED_FTP_MOVIE_TARGETS_G141,
    ALLOWED_FTP_RAW_JH_TARGETS_G141,
    ALLOWED_FTP_ROOT_CERT_ERR_BEHAVIORS_G141,
    ALLOWED_FTP_TRANSFER_MODES_G141,
    ALLOWED_FX3_FTP_PROTOCOLS_G141,
    ALLOWED_FX3_PEAKING_COLORS_G142,
    ALLOWED_FX3_SAFETY_ZONES_G142,
    ALLOWED_FX3_WB_MODES_G141,
    ALLOWED_FX6_ASPECT_SAFETY_AREAS_G142,
    ALLOWED_FX6_PEAKING_COLORS_G142,
    ALLOWED_FX6_WB_MEMORY_BANKS_G141,
    ALLOWED_FX6_WHT_BAL_SWITCH_G141,
    ALLOWED_LOG_SHOOTING_MODES_PHASE319,
    ALLOWED_PEAKING_LEVELS_G142,
    ALLOWED_PRIORITY_SET_AWB_G141,
    ALLOWED_RESET_ACTIONS_PHASE319,
    ALLOWED_SHOCKLESS_WB_G141,
    ALLOWED_SHOOT_MODES_PHASE319,
    ALLOWED_SHUTTER_AWB_LOCK_G141,
    ALLOWED_USBLAN_STATES_G141,
    ASPECT_MARKER_F_UXC_RESID16_G142,
    CENTER_MARKER_F_UXC_RESID16_G142,
    CINE_EI_LOCKED_WB_MODES_G141,
    CROSS_MODEL_FLASH_AUTHORIZED,
    CUSTOM_WB_ERROR_0X0220_PP_GAMMAS_G141,
    DEFAULT_REPO_ROOT,
    DONOR_CHECK_CI_MAX_SECONDS_PHASE319,
    DONOR_CHECK_MAX_SECONDS_PHASE319,
    DORMANT_FTP_IMAGE_SIZE_TRAPS_G141,
    EBUSY_ERRNO_PHASE319,
    EINVAL_ERRNO_PHASE319,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    ENODEV_ERRNO_PHASE319,
    ENV_CLEAN_ROOM_TEST_PHASE319,
    ENV_FORCE_CLEAN_ROOM,
    EOPNOTSUPP_ERRNO_PHASE319,
    EROFS_ERRNO_PHASE319,
    EXACT_15_ACTIVE_ASPECT_RATIOS_FX3_G142,
    FOCUS_MAP_HIGH_FPS_BLOCK_THRESHOLD_G142,
    FOCUS_MAP_MIN_FX3_FW_G142,
    FOCUS_MAP_SHARED_F_UXC_RESID16_G142,
    FTP_AVF_DB_RESET_WARNING_BASE_UXC_RESID16_G141,
    FTP_DIR_HIERARCHY_SAME_AS_CAMERA_G141,
    FTP_DIR_HIERARCHY_STANDARD_G141,
    FTP_FTPES_CONNECT_F_UXC_RESID16_G141,
    FTP_FUNCTION_F_UXC_RESID16_G141,
    FTP_MODE_ACTIVE_G141,
    FTP_MODE_PASSIVE_G141,
    FTP_PROTOCOL_FTPES_G141,
    FTP_PROTOCOL_FTP_G141,
    FTP_PROTOCOL_IMPLICIT_FTPS_FORBIDDEN_G141,
    FTP_PROTOCOL_SFTP_FORBIDDEN_G141,
    FTP_SECURE_PROTOCOL_F_UXC_RESID16_G141,
    FTP_SERVER1_F_UXC_RESID16_G141,
    FTP_SERVER8_F_UXC_RESID16_G141,
    FTP_SERVER9_F_UXC_RESID16_G141,
    FTP_SLOT1_MUTEX_BASE_UXC_RESID16_G141,
    FTP_TRANSFER_HEIF_SIZE_DORMANT_F_UXC_RESID16_G141,
    FTP_TRANSFER_JPEG_SIZE_DORMANT_F_UXC_RESID16_G141,
    FX3_DEFAULT_FW_VERSION_PHASE319,
    FX3_FTP_CACERT_FILENAME_G141,
    FX3_FTP_CACERT_MAX_BYTES_G141,
    FX3_FTP_EXACT_SERVER_SLOTS_G141,
    FX3_FTP_SERVER_SLOT_MAX_G141,
    FX3_FTP_SERVER_SLOT_MIN_G141,
    FX3_FTP_SPECIFY_DIRECTORY_MAX_LEN_G141,
    FX3_HELP_GUIDE_CODE_PHASE319,
    FX3_MODEL_ID_PHASE319,
    FX3_MODEL_NAME_PHASE319,
    FX6_ASPECT_MASK_DEFAULT_G142,
    FX6_ASPECT_MASK_MAX_G142,
    FX6_ASPECT_MASK_MIN_G142,
    FX6_DEFAULT_FW_VERSION_PHASE319,
    FX6_FTP_CERT_FILENAME_G141,
    FX6_FTP_CERT_SLOT_G141,
    FX6_FTP_ELF_SERVER_SLOTS_MAX_G141,
    FX6_FTP_UI_SERVER_SLOTS_G141,
    FX6_MODEL_NAME_PHASE319,
    FX6_PRODUCT_CODE_PHASE319,
    FX6_USER_BOX_HEIGHT_MAX_G142,
    FX6_USER_BOX_HEIGHT_MIN_G142,
    FX6_USER_BOX_H_POS_MAX_G142,
    FX6_USER_BOX_H_POS_MIN_G142,
    FX6_USER_BOX_V_POS_MAX_G142,
    FX6_USER_BOX_V_POS_MIN_G142,
    FX6_USER_BOX_WIDTH_MAX_G142,
    FX6_USER_BOX_WIDTH_MIN_G142,
    G141,
    G141_GATE_CODE,
    G141_GATE_ID,
    G142,
    G142_GATE_CODE,
    G142_GATE_ID,
    GUIDEFRAME_F_UXC_RESID16_G142,
    HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    HUMAN_HARDWARE_ATTACH_TOKEN,
    LOG_SHOOTING_CINE_EI_PHASE319,
    LOG_SHOOTING_CINE_EI_QUICK_PHASE319,
    LOG_SHOOTING_FLEXIBLE_ISO_PHASE319,
    LOG_SHOOTING_OFF_PHASE319,
    MARKER_DISPLAY_F_UXC_RESID16_G142,
    Master142GateReport,
    PEAKING_COLOR_BASE_UXC_RESID16_G142,
    PEAKING_DISPLAY_F_UXC_RESID16_G142,
    PEAKING_LEVEL_BASE_UXC_RESID16_G142,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED,
    PHYSICAL_USB_PACKETS_EMITTED,
    PINNED_FX3_APPFW_SLICES_PHASE319,
    PINNED_FX3_APPFW_SLICES_SHA256_PHASE319,
    PINNED_FX6_APPFW_SLICES_PHASE319,
    PINNED_FX6_APPFW_SLICES_SHA256_PHASE319,
    PINNED_PHASE319_DONOR_SPECS,
    RAW_FIRMWARE_BYTES_LEAKED,
    REALHW_142GATE_PREFLIGHT_SCHEMA,
    REALHW_FTP_FTPES_9SLOT_ZERO_SFTP_AVF_VAULT_AND_CUSTOMWB_CINEEI_GUARD,
    REALHW_FTP_FTPES_CUSTOMWB_AF_FOCUSMAP_MARKER_142GATE_SCHEMA,
    REALHW_FTP_FTPES_CUSTOMWB_AF_FOCUSMAP_MARKER_142GATE_VERSION,
    REALHW_MOVIE_AF_1TO7_1TO5_EXTERNAL_FOCUSMAP_AND_15ASPECT_MARKER_PEAKING_GUARD,
    RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE319,
    RESET_ACTION_INITIALIZE_PHASE319,
    RESET_ACTION_NONE_PHASE319,
    RESET_ACTION_RESET_NETWORK_SET_PHASE319,
    SAFETY_ZONE_F_UXC_RESID16_G142,
    SHOOT_MODE_MOVIE_PHASE319,
    SHOOT_MODE_SQ_PHASE319,
    SHOOT_MODE_STILL_PHASE319,
    SPI_NOR_WRITE_AUTHORIZED,
    STATUS_BLOCKED_G141_CUSTOMWB_LOG_ERR_0X0220_OR_CINEEI_VIOLATION,
    STATUS_BLOCKED_G141_FTP_9SLOT_PROTOCOL_OR_DORMANT_VIOLATION,
    STATUS_BLOCKED_G141_SLOT1_AVF_INFO_VAULT_OR_CACERT_VIOLATION,
    STATUS_BLOCKED_G141_TELEMETRY_INVALID,
    STATUS_BLOCKED_G141_USBLAN_ZERO_RF_BYPASS_VIOLATION,
    STATUS_BLOCKED_G142_FOCUSMAP_ONBODY_OR_EXCLUSION_VIOLATION,
    STATUS_BLOCKED_G142_MARKER_15ASPECT_PEAKING_OR_HDMI_VIOLATION,
    STATUS_BLOCKED_G142_MOVIE_AF_1TO7_1TO5_OR_ASSIST_VIOLATION,
    STATUS_BLOCKED_G142_TELEMETRY_INVALID,
    STATUS_BLOCKED_PERSISTENT_EMMC_WRITE,
    STATUS_BLOCKED_PHASE319_DONOR_INTEGRITY,
    STATUS_VERIFIED_G141,
    STATUS_VERIFIED_G142,
    STATUS_VERIFIED_SAFE,
    USB_PACKETS_TRANSMITTED,
    WB_AB_AXIS_MAX_G141,
    WB_AB_AXIS_MIN_G141,
    WB_AB_STEP_G141,
    WB_COLOR_TEMP_MAX_K_G141,
    WB_COLOR_TEMP_MIN_K_G141,
    WB_COLOR_TEMP_STEP_K_G141,
    WB_CUSTOM_ERROR_BASE_UXC_RESID16_G141,
    WB_CUSTOM_ERROR_F_UXC_RESID16_G141,
    WB_GM_AXIS_MAX_G141,
    WB_GM_AXIS_MIN_G141,
    WB_GM_STEP_G141,
    WB_PRIORITY_SET_IN_AWB_F_UXC_RESID16_G141,
    WB_SHOCKLESS_WB_F_UXC_RESID16_G141,
    WB_SHUTTER_AWB_LOCK_F_UXC_RESID16_G141,
    WB_WHITE_BALANCE_F_UXC_RESID16_G141,
    audit_phase319_donor_contracts,
    compute_ftp_ftpes_customwb_matrix,
    compute_movie_af_focusmap_marker_peaking_matrix,
    evaluate_142_master_safety_gates,
    evaluate_142gate_preflight,
    evaluate_g141_ftp_ftpes_avf_vault_and_customwb_cineei_guard,
    evaluate_g142_movie_af_focusmap_marker_peaking_guard,
    main as guard_cli_main,
    resolve_fx3_ftp_ftpes_customwb_state,
    resolve_fx3_movie_af_focusmap_marker_peaking_state,
    run_142_gate_preflight,
    verify_ftp_ftpes_avf_vault_and_customwb_cineei_guard,
    verify_movie_af_focusmap_marker_peaking_guard,
)
from fx3_safety.realhw_rec_media_autoswitch_proxy_cloud_mymenu_and_140gate_guard import (
    Master140GateReport,
)
from fx3_safety.thermal_pwm_and_power_guard import DonorThermalPowerPaths


def _donors_available_here() -> bool:
    from fx3_safety.thermal_pwm_and_power_guard import resolve_donor_thermal_power_paths

    work_root = resolve_donor_thermal_power_paths(repo_root=DEFAULT_REPO_ROOT).work_root
    if work_root is None:
        return False
    for spec in PINNED_PHASE319_DONOR_SPECS.values():
        if not (work_root / spec[1]).exists():
            return False
    return True


def _build_stub_140_report(
    *, dry_run: bool = False, all_g13_140_ok: bool = True
) -> Master140GateReport:
    gates = []
    for idx in range(1, 141):
        is_tier0 = idx in (10, 11, 12)
        passed = bool(
            idx <= 9
            or (is_tier0 and dry_run)
            or (idx >= 13 and all_g13_140_ok)
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
    g13_138 = 126 if all_g13_140_ok else 0
    g139_140 = 2 if all_g13_140_ok else 0
    total = g01_12 + g13_138 + g139_140
    return Master140GateReport(
        schema="realhw_140gate_preflight_v1",
        schema_version="realhw_140gate_preflight_v1",
        version="2026.11.17",
        evaluated_utc="2026-11-17T00:00:00Z",
        verification_mode="CLEAN_ROOM_SYNTHETIC",
        clean_room_forced=True,
        dry_run_rehearsal_only=dry_run,
        overall_ready_for_hardware_attach=False,
        hardware_live_attachment_authorized=False,
        offline_137_gates_verified=all_g13_140_ok,
        all_140_gates_verified=(dry_run and all_g13_140_ok),
        g13_to_g140_all_passed=all_g13_140_ok,
        g139_to_g140_all_passed=all_g13_140_ok,
        h0_h1_trial_entry_allowed=all_g13_140_ok,
        status=(
            "VERIFIED_ALL_140_GATES_DRY_RUN_SIMULATED_BACKUP"
            if dry_run
            else "VERIFIED_137_OF_140_AWAITING_PHYSICAL_TIER0"
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
            "g13_to_g138_verified": g13_138,
            "g139_to_g140_verified": g139_140,
            "verified_gates": total,
        },
        gates=tuple(gates),
        master_138_report={},
        g139_result={},
        g140_result={},
        errors=(),
        warnings=(),
    )


class TestPackageExportsAndDonorAuditPhase319(unittest.TestCase):
    def test_01_package_exports_phase319_symbols_and_all(self) -> None:
        self.assertIs(fx3_safety.evaluate_142gate_preflight, evaluate_142gate_preflight)
        self.assertIs(
            fx3_safety.evaluate_g141_ftp_ftpes_avf_vault_and_customwb_cineei_guard,
            evaluate_g141_ftp_ftpes_avf_vault_and_customwb_cineei_guard,
        )
        self.assertIs(
            fx3_safety.evaluate_g142_movie_af_focusmap_marker_peaking_guard,
            evaluate_g142_movie_af_focusmap_marker_peaking_guard,
        )
        self.assertEqual(fx3_safety.G141, "G141")
        self.assertEqual(fx3_safety.G142, "G142")
        self.assertIn("evaluate_142gate_preflight", fx3_safety.__all__)
        self.assertIn("evaluate_142_master_safety_gates", fx3_safety.__all__)
        self.assertIn("run_142_gate_preflight", fx3_safety.__all__)
        self.assertIn("Master142GateReport", fx3_safety.__all__)
        self.assertIn(
            "evaluate_g141_ftp_ftpes_avf_vault_and_customwb_cineei_guard",
            fx3_safety.__all__,
        )
        self.assertIn(
            "evaluate_g142_movie_af_focusmap_marker_peaking_guard",
            fx3_safety.__all__,
        )
        self.assertIn(
            "realhw_ftp_ftpes_customwb_af_focusmap_marker_and_142gate_guard",
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
        self.assertEqual(REALHW_142GATE_PREFLIGHT_SCHEMA, "realhw_142gate_preflight_v1")
        self.assertEqual(
            REALHW_FTP_FTPES_CUSTOMWB_AF_FOCUSMAP_MARKER_142GATE_SCHEMA,
            "realhw_142gate_preflight_v1",
        )
        self.assertEqual(
            REALHW_FTP_FTPES_CUSTOMWB_AF_FOCUSMAP_MARKER_142GATE_VERSION,
            "2026.11.17",
        )
        self.assertEqual(G141_GATE_ID, "G141")
        self.assertEqual(G142_GATE_ID, "G142")
        self.assertEqual(
            G141_GATE_CODE,
            REALHW_FTP_FTPES_9SLOT_ZERO_SFTP_AVF_VAULT_AND_CUSTOMWB_CINEEI_GUARD,
        )
        self.assertEqual(
            G142_GATE_CODE,
            REALHW_MOVIE_AF_1TO7_1TO5_EXTERNAL_FOCUSMAP_AND_15ASPECT_MARKER_PEAKING_GUARD,
        )

    def test_04_donor_audit_clean_room_forced_succeeds_fast_zero_leaks(self) -> None:
        audit = audit_phase319_donor_contracts(force_clean_room=True)
        self.assertTrue(audit.valid)
        self.assertEqual(audit.status, STATUS_VERIFIED_SAFE)
        self.assertEqual(audit.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(audit.raw_firmware_bytes_leaked, 0)
        self.assertTrue(audit.fx3_contracts_verified)
        self.assertTrue(audit.fx6_contracts_verified)
        self.assertTrue(audit.four_lang_resid16_parity_verified)
        self.assertTrue(audit.zero_forbidden_myths_verified)

    def test_05_donor_audit_env_force_and_test_clean_room_modes(self) -> None:
        for env_key in (ENV_FORCE_CLEAN_ROOM, ENV_CLEAN_ROOM_TEST_PHASE319):
            with mock.patch.dict(os.environ, {env_key: "1"}):
                audit = audit_phase319_donor_contracts()
                self.assertTrue(audit.valid)
                self.assertEqual(audit.verification_mode, "CLEAN_ROOM_SYNTHETIC")
                self.assertEqual(audit.raw_firmware_bytes_leaked, 0)

    def test_06_donor_audit_missing_donors_falls_back_clean_room(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            with mock.patch.dict(
                os.environ,
                {ENV_FORCE_CLEAN_ROOM: "", ENV_CLEAN_ROOM_TEST_PHASE319: ""},
            ):
                audit = audit_phase319_donor_contracts(work_root=Path(td))
                self.assertTrue(audit.valid)
                self.assertEqual(audit.verification_mode, "CLEAN_ROOM_SYNTHETIC")
                self.assertGreaterEqual(len(audit.warnings), 1)
                self.assertEqual(audit.raw_firmware_bytes_leaked, 0)

    def test_07_donorless_work_root_none_falls_back_clean_room_no_typeerror(self) -> None:
        fake_paths = DonorThermalPowerPaths(
            work_root=None,
            fx3_lib_dir=None,
            fx3_appfw_path=None,
            fx3_cp_path=None,
            fx3_bk4_path=None,
            fx6_lib_dir=None,
            fx6_bk4_path=None,
            fx6_cp_path=None,
        )
        with mock.patch.dict(
            os.environ,
            {ENV_FORCE_CLEAN_ROOM: "", ENV_CLEAN_ROOM_TEST_PHASE319: ""},
        ):
            with mock.patch(
                "fx3_safety.thermal_pwm_and_power_guard.resolve_donor_thermal_power_paths",
                return_value=fake_paths,
            ), mock.patch(
                "fx3_safety.realhw_ftp_ftpes_customwb_af_focusmap_marker_and_142gate_guard.resolve_donor_thermal_power_paths",
                return_value=fake_paths,
            ):
                self.assertFalse(_donors_available_here())
                audit = audit_phase319_donor_contracts(
                    repo_root=Path("/tmp/nonexistent-donorless-repo"),
                    force_clean_room=False,
                )
                self.assertTrue(audit.valid)
                self.assertEqual(audit.verification_mode, "CLEAN_ROOM_SYNTHETIC")
                self.assertEqual(audit.access_mode, "CLEAN_ROOM_FALLBACK_MISSING_DONORS")
                self.assertGreaterEqual(len(audit.warnings), 1)
                self.assertEqual(audit.raw_firmware_bytes_leaked, 0)

    def test_08_donor_audit_corrupted_sha_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            dummy = root / "bad.bin"
            dummy.write_bytes(b"corrupted-payload")
            specs = {
                "fx3_bad": (
                    "FX3",
                    "bad.bin",
                    len(b"corrupted-payload"),
                    "0" * 64,
                    (b"corrupted",),
                    "bad",
                ),
            }
            with mock.patch.dict(
                os.environ,
                {ENV_FORCE_CLEAN_ROOM: "", ENV_CLEAN_ROOM_TEST_PHASE319: ""},
            ):
                audit = audit_phase319_donor_contracts(
                    work_root=root,
                    force_clean_room=False,
                    donor_specs_override=specs,
                )
            self.assertFalse(audit.valid)
            self.assertEqual(audit.status, STATUS_BLOCKED_PHASE319_DONOR_INTEGRITY)
            self.assertIn("fx3_bad:sha256_mismatch", audit.missing_markers)

    def test_09_donor_audit_size_and_token_mismatch_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            blob = b"partial-file"
            (root / "bad.bin").write_bytes(blob)
            sha = hashlib.sha256(blob).hexdigest()
            specs = {
                "fx3_bad": ("FX3", "bad.bin", 9999, sha, (b"NONEXISTENT_TOKEN",), "bad"),
            }
            with mock.patch.dict(
                os.environ,
                {ENV_FORCE_CLEAN_ROOM: "", ENV_CLEAN_ROOM_TEST_PHASE319: ""},
            ):
                audit = audit_phase319_donor_contracts(
                    work_root=root,
                    force_clean_room=False,
                    donor_specs_override=specs,
                )
            self.assertFalse(audit.valid)
            self.assertIn("fx3_bad:size_mismatch", audit.missing_markers)
            self.assertIn("fx3_bad:token_missing", audit.missing_markers)

    def test_10_donor_audit_live_o_rdonly_when_present_under_budget(self) -> None:
        if os.environ.get(ENV_FORCE_CLEAN_ROOM) or os.environ.get(
            ENV_CLEAN_ROOM_TEST_PHASE319
        ):
            self.skipTest("Clean-room env var forces synthetic audit")
        if not _donors_available_here():
            self.skipTest("Donor binaries absent in CI/clean-room host")
        audit = audit_phase319_donor_contracts(force_clean_room=False)
        self.assertTrue(audit.valid, msg=f"errors={audit.errors}")
        self.assertEqual(audit.verification_mode, "LOCAL_DONOR_O_RDONLY")
        self.assertEqual(audit.access_mode, "POSIX_O_RDONLY_AND_PREAD_ZERO_MUTATION")
        self.assertEqual(audit.files_inspected, len(PINNED_PHASE319_DONOR_SPECS))
        self.assertLessEqual(audit.elapsed_seconds, DONOR_CHECK_CI_MAX_SECONDS_PHASE319)
        self.assertLessEqual(audit.elapsed_seconds, DONOR_CHECK_MAX_SECONDS_PHASE319)
        self.assertTrue(audit.within_budget_200ms)
        self.assertEqual(audit.raw_firmware_bytes_leaked, 0)

    def test_11_pinned_appfw_slices_and_hashes_immutable_shape(self) -> None:
        self.assertEqual(len(PINNED_FX3_APPFW_SLICES_PHASE319), 30)
        self.assertEqual(len(PINNED_FX6_APPFW_SLICES_PHASE319), 16)
        self.assertEqual(len(PINNED_FX3_APPFW_SLICES_SHA256_PHASE319), 64)
        self.assertEqual(len(PINNED_FX6_APPFW_SLICES_SHA256_PHASE319), 64)
        self.assertEqual(len(PINNED_PHASE319_DONOR_SPECS), 11)
        self.assertEqual(DONOR_CHECK_MAX_SECONDS_PHASE319, 0.20)
        self.assertEqual(DONOR_CHECK_CI_MAX_SECONDS_PHASE319, 15.0)

    def test_12_donorless_work_root_none_with_override_fails_closed(self) -> None:
        fake_paths = DonorThermalPowerPaths(
            work_root=None,
            fx3_lib_dir=None,
            fx3_appfw_path=None,
            fx3_cp_path=None,
            fx3_bk4_path=None,
            fx6_lib_dir=None,
            fx6_bk4_path=None,
            fx6_cp_path=None,
        )
        specs = {"fx3_bad": ("FX3", "missing.bin", 10, "0" * 64, (b"x",), "bad")}
        with mock.patch.dict(
            os.environ,
            {ENV_FORCE_CLEAN_ROOM: "", ENV_CLEAN_ROOM_TEST_PHASE319: ""},
        ), mock.patch(
            "fx3_safety.realhw_ftp_ftpes_customwb_af_focusmap_marker_and_142gate_guard.resolve_donor_thermal_power_paths",
            return_value=fake_paths,
        ):
            audit = audit_phase319_donor_contracts(
                repo_root=Path("/tmp/nonexistent-donorless-repo"),
                force_clean_room=False,
                donor_specs_override=specs,
            )
            self.assertFalse(audit.valid)
            self.assertEqual(audit.status, STATUS_BLOCKED_PHASE319_DONOR_INTEGRITY)
            self.assertIn("fx3_bad:file_missing", audit.missing_markers)


class TestGateG141FtpFtpes9SlotZeroSftpAvfVaultAndCustomWbCineEi(unittest.TestCase):
    def test_13_g141_default_safe_zerorf_bench_passes(self) -> None:
        res = verify_ftp_ftpes_avf_vault_and_customwb_cineei_guard()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_VERIFIED_G141)
        self.assertEqual(res.effective_ftp_function, "Off")
        self.assertEqual(res.effective_airplane_mode, "On")
        self.assertEqual(res.effective_usblan_tethering, "Disconnected")
        self.assertTrue(res.zero_rf_and_usblan_isolated)
        self.assertEqual(res.rf_packets_transmitted, 0)
        self.assertEqual(res.wired_usblan_ftp_packets, 0)
        self.assertEqual(res.slot1_data_sector_writes, 0)
        self.assertFalse(res.slot1_avf_info_mutated)
        self.assertEqual(res.matrix_states_checked, 256)

    def test_14_g141_uxc_resid16_anchors_exact(self) -> None:
        self.assertEqual(FTP_FUNCTION_F_UXC_RESID16_G141, 0x6317)
        self.assertEqual(FTP_SERVER1_F_UXC_RESID16_G141, 0x6305)
        self.assertEqual(FTP_SERVER8_F_UXC_RESID16_G141, 0x72F4)
        self.assertEqual(FTP_SERVER9_F_UXC_RESID16_G141, 0x630D)
        self.assertEqual(FTP_SECURE_PROTOCOL_F_UXC_RESID16_G141, 0x60DD)
        self.assertEqual(FTP_FTPES_CONNECT_F_UXC_RESID16_G141, 0x6553)
        self.assertEqual(FTP_TRANSFER_JPEG_SIZE_DORMANT_F_UXC_RESID16_G141, 0x6AED)
        self.assertEqual(FTP_TRANSFER_HEIF_SIZE_DORMANT_F_UXC_RESID16_G141, 0x63DD)
        self.assertEqual(FTP_AVF_DB_RESET_WARNING_BASE_UXC_RESID16_G141, 0x0A13)
        self.assertEqual(FTP_SLOT1_MUTEX_BASE_UXC_RESID16_G141, 0x09B7)
        self.assertEqual(WB_WHITE_BALANCE_F_UXC_RESID16_G141, 0x73EE)
        self.assertEqual(WB_PRIORITY_SET_IN_AWB_F_UXC_RESID16_G141, 0x67A7)
        self.assertEqual(WB_SHUTTER_AWB_LOCK_F_UXC_RESID16_G141, 0x66DB)
        self.assertEqual(WB_SHOCKLESS_WB_F_UXC_RESID16_G141, 0x62FE)
        self.assertEqual(WB_CUSTOM_ERROR_F_UXC_RESID16_G141, 0x63AC)
        self.assertEqual(WB_CUSTOM_ERROR_BASE_UXC_RESID16_G141, 0x0220)

    def test_15_g141_exact_9_ftp_server_slots_supported_and_bounds_enforced(self) -> None:
        self.assertEqual(FX3_FTP_EXACT_SERVER_SLOTS_G141, 9)
        self.assertEqual(FX3_FTP_SERVER_SLOT_MIN_G141, 1)
        self.assertEqual(FX3_FTP_SERVER_SLOT_MAX_G141, 9)
        for slot in range(1, 10):
            res = verify_ftp_ftpes_avf_vault_and_customwb_cineei_guard(
                zero_rf_bench_mode=False,
                requested_airplane_mode="Off",
                requested_ftp_function="On",
                ftp_server_slot=slot,
                ftp_protocol=FTP_PROTOCOL_FTPES_G141,
            )
            self.assertTrue(res.valid, msg=f"slot={slot} failed: {res.violation_codes}")
            self.assertEqual(res.ftp_server_slot, slot)

        for bad_slot in (0, 10, 16):
            bad = verify_ftp_ftpes_avf_vault_and_customwb_cineei_guard(
                zero_rf_bench_mode=False,
                requested_airplane_mode="Off",
                requested_ftp_function="On",
                ftp_server_slot=bad_slot,
            )
            self.assertFalse(bad.valid)
            self.assertEqual(bad.block_errno, EINVAL_ERRNO_PHASE319)

    def test_16_g141_zero_sftp_and_zero_implicit_ftps_990_rejected_eopnotsupp(self) -> None:
        self.assertEqual(
            ALLOWED_FX3_FTP_PROTOCOLS_G141,
            (FTP_PROTOCOL_FTP_G141, FTP_PROTOCOL_FTPES_G141),
        )
        for proto, port in (
            (FTP_PROTOCOL_SFTP_FORBIDDEN_G141, 22),
            (FTP_PROTOCOL_IMPLICIT_FTPS_FORBIDDEN_G141, 990),
            (FTP_PROTOCOL_FTPES_G141, 990),
        ):
            res = verify_ftp_ftpes_avf_vault_and_customwb_cineei_guard(
                zero_rf_bench_mode=False,
                requested_airplane_mode="Off",
                requested_ftp_function="On",
                ftp_protocol=proto,
                ftp_port=port,
            )
            self.assertFalse(res.valid)
            self.assertTrue(res.dormant_sftp_or_implicit_ftps_rejected)
            self.assertIn(
                STATUS_BLOCKED_G141_FTP_9SLOT_PROTOCOL_OR_DORMANT_VIOLATION,
                res.violation_codes,
            )
            self.assertEqual(res.block_errno, EOPNOTSUPP_ERRNO_PHASE319)

    def test_17_g141_fx3_passive_only_rejects_active_mode_eopnotsupp(self) -> None:
        bad = verify_ftp_ftpes_avf_vault_and_customwb_cineei_guard(
            zero_rf_bench_mode=False,
            requested_airplane_mode="Off",
            requested_ftp_function="On",
            ftp_transfer_mode=FTP_MODE_ACTIVE_G141,
        )
        self.assertFalse(bad.valid)
        self.assertTrue(bad.fx3_active_mode_rejected)
        self.assertEqual(bad.block_errno, EOPNOTSUPP_ERRNO_PHASE319)

        fx6_ok = verify_ftp_ftpes_avf_vault_and_customwb_cineei_guard(
            target_model=FX6_MODEL_NAME_PHASE319,
            zero_rf_bench_mode=False,
            requested_airplane_mode="Off",
            requested_ftp_function="On",
            ftp_transfer_mode=FTP_MODE_ACTIVE_G141,
            ftp_server_slot=1,
            fx6_ui_server_slots_claimed=FX6_FTP_UI_SERVER_SLOTS_G141,
        )
        self.assertTrue(fx6_ok.valid)
        self.assertFalse(fx6_ok.fx3_active_mode_rejected)

    def test_18_g141_dormant_transfer_jpeg_heif_size_rejected_eopnotsupp(self) -> None:
        for trap in DORMANT_FTP_IMAGE_SIZE_TRAPS_G141:
            res = verify_ftp_ftpes_avf_vault_and_customwb_cineei_guard(
                dormant_transfer_image_size_token=trap,
            )
            self.assertFalse(res.valid)
            self.assertTrue(res.dormant_transfer_image_size_rejected)
            self.assertEqual(res.block_errno, EOPNOTSUPP_ERRNO_PHASE319)

    def test_19_g141_specify_directory_128_char_limit_and_hierarchies(self) -> None:
        self.assertEqual(FX3_FTP_SPECIFY_DIRECTORY_MAX_LEN_G141, 128)
        for h in ALLOWED_FTP_DIR_HIERARCHIES_G141:
            ok = verify_ftp_ftpes_avf_vault_and_customwb_cineei_guard(
                zero_rf_bench_mode=False,
                requested_airplane_mode="Off",
                requested_ftp_function="On",
                ftp_directory_hierarchy=h,
                ftp_specify_directory="a" * 128,
            )
            self.assertTrue(ok.valid)
            self.assertEqual(ok.ftp_specify_directory_len, 128)

        too_long = verify_ftp_ftpes_avf_vault_and_customwb_cineei_guard(
            zero_rf_bench_mode=False,
            requested_airplane_mode="Off",
            requested_ftp_function="On",
            ftp_specify_directory="a" * 129,
        )
        self.assertFalse(too_long.valid)
        self.assertEqual(too_long.block_errno, EINVAL_ERRNO_PHASE319)

    def test_20_g141_ftp_and_creators_cloud_mutual_exclusion(self) -> None:
        bad = verify_ftp_ftpes_avf_vault_and_customwb_cineei_guard(
            zero_rf_bench_mode=False,
            requested_airplane_mode="Off",
            requested_ftp_function="On",
            requested_cloud_connection="On",
        )
        self.assertFalse(bad.valid)
        self.assertFalse(bad.ftp_cloud_mutual_exclusion_ok)
        self.assertEqual(bad.block_errno, EINVAL_ERRNO_PHASE319)

    def test_21_g141_reset_network_and_initialize_wipe_ftp_while_cam_reset_preserves(self) -> None:
        for rst in (
            RESET_ACTION_RESET_NETWORK_SET_PHASE319,
            RESET_ACTION_INITIALIZE_PHASE319,
        ):
            r = verify_ftp_ftpes_avf_vault_and_customwb_cineei_guard(
                zero_rf_bench_mode=(rst != RESET_ACTION_INITIALIZE_PHASE319),
                reset_action=rst,
                requested_ftp_function="On",
                ftp_server_slot=7,
            )
            self.assertTrue(r.valid)
            self.assertEqual(r.effective_ftp_function, "Off")
            self.assertEqual(r.ftp_server_slot, 1)

        cam_rst = verify_ftp_ftpes_avf_vault_and_customwb_cineei_guard(
            zero_rf_bench_mode=False,
            requested_airplane_mode="Off",
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE319,
            requested_ftp_function="On",
            ftp_server_slot=9,
        )
        self.assertTrue(cam_rst.valid)
        self.assertEqual(cam_rst.effective_ftp_function, "On")
        self.assertEqual(cam_rst.ftp_server_slot, 9)

    def test_22_g141_critical_slot1_avf_info_mutation_enforces_erofs(self) -> None:
        for kw in (
            {
                "slot1_ftp_target_selected": True,
                "requested_ftp_function": "On",
                "zero_rf_bench_mode": False,
                "requested_airplane_mode": "Off",
            },
            {"ftp_transfer_status_write_requested": True},
            {"ftp_avf_db_recover_requested": True},
            {"bypass_slot1_avf_firewall": True},
        ):
            res = verify_ftp_ftpes_avf_vault_and_customwb_cineei_guard(
                slot_1_contains_tier0_vault=True,
                **kw,
            )
            self.assertFalse(res.valid)
            self.assertTrue(res.slot1_avf_info_firewall_blocked)
            self.assertEqual(res.slot1_data_sector_writes, 0)
            self.assertFalse(res.slot1_avf_info_mutated)
            self.assertEqual(res.block_errno, EROFS_ERRNO_PHASE319)
            self.assertIn(
                STATUS_BLOCKED_G141_SLOT1_AVF_INFO_VAULT_OR_CACERT_VIOLATION,
                res.violation_codes,
            )

    def test_23_g141_cacert_pem_strictly_o_rdonly_and_max_1mb(self) -> None:
        ok = verify_ftp_ftpes_avf_vault_and_customwb_cineei_guard(
            cacert_import_requested=True,
            cacert_filename=FX3_FTP_CACERT_FILENAME_G141,
            cacert_slot="Slot 1",
            cacert_size_bytes=FX3_FTP_CACERT_MAX_BYTES_G141,
            cacert_pem_valid=True,
            cacert_write_mode_requested=False,
        )
        self.assertTrue(ok.valid)
        self.assertTrue(ok.cacert_o_rdonly_valid)
        self.assertEqual(ok.cacert_read_mode, "O_RDONLY")

        bad_wr = verify_ftp_ftpes_avf_vault_and_customwb_cineei_guard(
            cacert_import_requested=True,
            cacert_slot="Slot 1",
            slot_1_contains_tier0_vault=True,
            cacert_write_mode_requested=True,
        )
        self.assertFalse(bad_wr.valid)
        self.assertFalse(bad_wr.cacert_o_rdonly_valid)
        self.assertEqual(bad_wr.block_errno, EROFS_ERRNO_PHASE319)

        for bad_kw in (
            {"cacert_size_bytes": FX3_FTP_CACERT_MAX_BYTES_G141 + 1},
            {"cacert_filename": "wrong.pem"},
            {"cacert_pem_valid": False},
            {"cacert_slot": "Slot 2"},
        ):
            b = verify_ftp_ftpes_avf_vault_and_customwb_cineei_guard(
                cacert_import_requested=True,
                **bad_kw,
            )
            self.assertFalse(b.valid)
            self.assertEqual(b.block_errno, EINVAL_ERRNO_PHASE319)

    def test_24_g141_critical_usblan_zero_rf_bypass_trap(self) -> None:
        # Airplane Mode = On does NOT block wired USB-LAN FTP!
        usblan_leak = verify_ftp_ftpes_avf_vault_and_customwb_cineei_guard(
            zero_rf_bench_mode=True,
            requested_airplane_mode="On",
            requested_ftp_function="Off",
            requested_usblan_tethering="Connected",
        )
        self.assertFalse(usblan_leak.valid)
        self.assertFalse(usblan_leak.zero_rf_and_usblan_isolated)
        self.assertIn(
            STATUS_BLOCKED_G141_USBLAN_ZERO_RF_BYPASS_VIOLATION,
            usblan_leak.violation_codes,
        )
        self.assertEqual(usblan_leak.block_errno, EINVAL_ERRNO_PHASE319)

        # Airplane Mode = Off or FTP = On or Wi-Fi active also blocked under Zero-RF
        for kw in (
            {"requested_airplane_mode": "Off"},
            {"requested_ftp_function": "On"},
            {"wifi_paired_or_ap_active": True},
        ):
            r = verify_ftp_ftpes_avf_vault_and_customwb_cineei_guard(
                zero_rf_bench_mode=True,
                **kw,
            )
            self.assertFalse(r.valid)
            self.assertIn(
                STATUS_BLOCKED_G141_USBLAN_ZERO_RF_BYPASS_VIOLATION,
                r.violation_codes,
            )

    def test_25_g141_fx6_chunk_proxy_certification_pem_and_slot_contrast(self) -> None:
        self.assertEqual(FX6_FTP_UI_SERVER_SLOTS_G141, 3)
        self.assertEqual(FX6_FTP_ELF_SERVER_SLOTS_MAX_G141, 16)
        self.assertEqual(FX6_FTP_CERT_FILENAME_G141, "certification.pem")
        self.assertEqual(FX6_FTP_CERT_SLOT_G141, "Slot B")

        fx3_claim = verify_ftp_ftpes_avf_vault_and_customwb_cineei_guard(
            target_model=FX3_MODEL_NAME_PHASE319,
            claimed_fx3_supports_chunk_proxy_or_certification_pem=True,
        )
        self.assertFalse(fx3_claim.valid)
        self.assertEqual(fx3_claim.block_errno, EOPNOTSUPP_ERRNO_PHASE319)

        fx6_chunk_ok = verify_ftp_ftpes_avf_vault_and_customwb_cineei_guard(
            target_model=FX6_MODEL_NAME_PHASE319,
            zero_rf_bench_mode=False,
            requested_airplane_mode="Off",
            requested_ftp_function="On",
            fx6_chunk_proxy_enabled=True,
            fx6_simul_rec_enabled=False,
            fx6_relay_rec_enabled=False,
        )
        self.assertTrue(fx6_chunk_ok.valid)
        self.assertTrue(fx6_chunk_ok.fx6_chunk_proxy_mutual_exclusion_ok)

        fx6_chunk_simul_bad = verify_ftp_ftpes_avf_vault_and_customwb_cineei_guard(
            target_model=FX6_MODEL_NAME_PHASE319,
            zero_rf_bench_mode=False,
            requested_airplane_mode="Off",
            fx6_chunk_proxy_enabled=True,
            fx6_simul_rec_enabled=True,
        )
        self.assertFalse(fx6_chunk_simul_bad.valid)
        self.assertFalse(fx6_chunk_simul_bad.fx6_chunk_proxy_mutual_exclusion_ok)

    def test_26_g141_fx6_claimed_ui_exposes_sftp_rejected_eopnotsupp(self) -> None:
        bad = verify_ftp_ftpes_avf_vault_and_customwb_cineei_guard(
            target_model=FX6_MODEL_NAME_PHASE319,
            fx6_claimed_ui_exposes_sftp=True,
        )
        self.assertFalse(bad.valid)
        self.assertEqual(bad.block_errno, EOPNOTSUPP_ERRNO_PHASE319)

    def test_27_g141_wb_kelvin_2500_to_9900_step_100_validated(self) -> None:
        for k in (WB_COLOR_TEMP_MIN_K_G141, 5600, WB_COLOR_TEMP_MAX_K_G141):
            ok = verify_ftp_ftpes_avf_vault_and_customwb_cineei_guard(
                requested_white_balance="C.Temp./Filter",
                wb_color_temp_k=k,
            )
            self.assertTrue(ok.valid)
        for bad_k in (2400, 5650, 10000):
            bad = verify_ftp_ftpes_avf_vault_and_customwb_cineei_guard(
                requested_white_balance="C.Temp./Filter",
                wb_color_temp_k=bad_k,
            )
            self.assertFalse(bad.valid)
            self.assertEqual(bad.block_errno, EINVAL_ERRNO_PHASE319)

    def test_28_g141_custom_wb_1_to_3_excluded_from_camset_and_initialize_only_wipe(
        self,
    ) -> None:
        cam_rst = verify_ftp_ftpes_avf_vault_and_customwb_cineei_guard(
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE319,
            requested_white_balance="Custom 1",
            custom_wb_calibrated=True,
        )
        self.assertTrue(cam_rst.valid)
        self.assertTrue(cam_rst.custom_wb_preserved_across_cam_reset)
        self.assertTrue(cam_rst.custom_wb_excluded_from_camset)
        self.assertEqual(cam_rst.effective_white_balance, "Auto")

        assume_wipe = verify_ftp_ftpes_avf_vault_and_customwb_cineei_guard(
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE319,
            requested_white_balance="Custom 2",
            assume_cam_reset_wipes_custom_wb_slots=True,
        )
        self.assertFalse(assume_wipe.valid)
        self.assertEqual(assume_wipe.block_errno, EINVAL_ERRNO_PHASE319)

        camset_claim = verify_ftp_ftpes_avf_vault_and_customwb_cineei_guard(
            claimed_custom_wb_exports_in_camset=True,
        )
        self.assertFalse(camset_claim.valid)

        init_rst = verify_ftp_ftpes_avf_vault_and_customwb_cineei_guard(
            zero_rf_bench_mode=False,
            reset_action=RESET_ACTION_INITIALIZE_PHASE319,
            requested_white_balance="Custom 3",
            custom_wb_calibrated=True,
        )
        self.assertTrue(init_rst.valid)
        self.assertFalse(init_rst.custom_wb_preserved_across_cam_reset)
        self.assertEqual(init_rst.effective_white_balance, "Auto")

    def test_29_g141_custom_wb_error_0x0220_under_log_or_slog3_pplut(self) -> None:
        for kw in (
            {"log_shooting": LOG_SHOOTING_FLEXIBLE_ISO_PHASE319},
            {"log_shooting": LOG_SHOOTING_CINE_EI_PHASE319},
            {"picture_profile_gamma": "S-Log3"},
            {"picture_profile_gamma": "PPLUT1"},
            {"picture_profile_gamma": "PPLUT4"},
        ):
            r = verify_ftp_ftpes_avf_vault_and_customwb_cineei_guard(
                custom_wb_setup_requested=True,
                requested_white_balance="Custom 1",
                **kw,
            )
            self.assertFalse(r.valid)
            self.assertTrue(r.custom_wb_error_0x0220_triggered)
            self.assertIn(
                STATUS_BLOCKED_G141_CUSTOMWB_LOG_ERR_0X0220_OR_CINEEI_VIOLATION,
                r.violation_codes,
            )
            self.assertEqual(r.block_errno, EINVAL_ERRNO_PHASE319)

    def test_30_g141_cine_ei_locks_out_auto_and_underwater_auto_wb(self) -> None:
        for log_mode in (
            LOG_SHOOTING_CINE_EI_PHASE319,
            LOG_SHOOTING_CINE_EI_QUICK_PHASE319,
        ):
            for auto_wb in CINE_EI_LOCKED_WB_MODES_G141:
                bad = verify_ftp_ftpes_avf_vault_and_customwb_cineei_guard(
                    log_shooting=log_mode,
                    requested_white_balance=auto_wb,
                )
                self.assertFalse(bad.valid)
                self.assertTrue(bad.cine_ei_auto_wb_locked_out)
                self.assertEqual(bad.block_errno, EINVAL_ERRNO_PHASE319)

            daylight_ok = verify_ftp_ftpes_avf_vault_and_customwb_cineei_guard(
                log_shooting=log_mode,
                requested_white_balance="Daylight",
            )
            self.assertTrue(daylight_ok.valid)
            self.assertTrue(daylight_ok.cine_ei_auto_wb_locked_out)

    def test_31_g141_still_shutter_awb_lock_vs_shockless_wb_and_priority_awb(
        self,
    ) -> None:
        still_ok = verify_ftp_ftpes_avf_vault_and_customwb_cineei_guard(
            shoot_mode=SHOOT_MODE_STILL_PHASE319,
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE319,
            requested_shutter_awb_lock="Shut. Halfway",
        )
        self.assertTrue(still_ok.valid)
        self.assertTrue(still_ok.shutter_awb_lock_survived_cam_reset)
        self.assertEqual(still_ok.effective_shutter_awb_lock, "Shut. Halfway")

        still_init = verify_ftp_ftpes_avf_vault_and_customwb_cineei_guard(
            zero_rf_bench_mode=False,
            shoot_mode=SHOOT_MODE_STILL_PHASE319,
            reset_action=RESET_ACTION_INITIALIZE_PHASE319,
            requested_shutter_awb_lock="Cont. Shooting",
        )
        self.assertTrue(still_init.valid)
        self.assertEqual(still_init.effective_shutter_awb_lock, "Off")

        movie_bad = verify_ftp_ftpes_avf_vault_and_customwb_cineei_guard(
            shoot_mode=SHOOT_MODE_MOVIE_PHASE319,
            movie_shutter_awb_lock_claimed=True,
        )
        self.assertFalse(movie_bad.valid)
        self.assertEqual(movie_bad.block_errno, EINVAL_ERRNO_PHASE319)

        shock_rst = verify_ftp_ftpes_avf_vault_and_customwb_cineei_guard(
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE319,
            requested_shockless_wb="3",
            requested_priority_set_in_awb="Ambience",
        )
        self.assertTrue(shock_rst.valid)
        self.assertEqual(shock_rst.effective_shockless_wb, "1")
        self.assertEqual(shock_rst.effective_priority_set_in_awb, "Standard")

    def test_32_g141_fx6_atw_locked_in_cine_ei_and_memory_a_to_h(self) -> None:
        self.assertEqual(ALLOWED_FX6_WHT_BAL_SWITCH_G141, ("PRST", "A", "B"))
        self.assertEqual(len(ALLOWED_FX6_WB_MEMORY_BANKS_G141), 8)
        fx6_atw_ok = verify_ftp_ftpes_avf_vault_and_customwb_cineei_guard(
            target_model=FX6_MODEL_NAME_PHASE319,
            log_shooting=LOG_SHOOTING_OFF_PHASE319,
            requested_white_balance="Daylight",
            fx6_wht_bal_switch="A",
            fx6_wb_memory_bank="Memory H",
            fx6_atw_enabled=True,
            fx6_atw_speed=5,
        )
        self.assertTrue(fx6_atw_ok.valid)

        fx6_atw_cine_ei_bad = verify_ftp_ftpes_avf_vault_and_customwb_cineei_guard(
            target_model=FX6_MODEL_NAME_PHASE319,
            log_shooting=LOG_SHOOTING_CINE_EI_PHASE319,
            requested_white_balance="Daylight",
            fx6_atw_enabled=True,
        )
        self.assertFalse(fx6_atw_cine_ei_bad.valid)
        self.assertTrue(fx6_atw_cine_ei_bad.fx6_atw_cine_ei_locked_out)
        self.assertEqual(fx6_atw_cine_ei_bad.block_errno, EINVAL_ERRNO_PHASE319)

    def test_33_g141_compute_256_state_matrix_invariant(self) -> None:
        mat = compute_ftp_ftpes_customwb_matrix()
        self.assertEqual(mat["states_checked"], 256)
        self.assertGreater(mat["sftp_rejected_count"], 0)
        self.assertGreater(mat["slot1_avf_blocked_count"], 0)
        self.assertGreater(mat["usblan_bypass_blocked_count"], 0)
        self.assertGreater(mat["customwb_0x0220_count"], 0)

    def test_34_g141_request_persistent_emmc_writes_blocked_erofs(self) -> None:
        r = verify_ftp_ftpes_avf_vault_and_customwb_cineei_guard(
            request_persistent_emmc_writes=True,
        )
        self.assertFalse(r.valid)
        self.assertIn(STATUS_BLOCKED_PERSISTENT_EMMC_WRITE, r.violation_codes)
        self.assertEqual(r.block_errno, EROFS_ERRNO_PHASE319)

    def test_35_g141_wb_ab_gm_grid_steps_and_boundaries(self) -> None:
        ok = verify_ftp_ftpes_avf_vault_and_customwb_cineei_guard(
            wb_ab_shift=WB_AB_AXIS_MIN_G141,
            wb_gm_shift=WB_GM_AXIS_MAX_G141 - WB_GM_STEP_G141,
        )
        self.assertTrue(ok.valid)

        for kw in (
            {"wb_ab_shift": 0.25},  # A-B is 0.5 step, not 0.25
            {"wb_ab_shift": WB_AB_AXIS_MAX_G141 + 0.5},
            {"wb_gm_shift": 0.1},  # G-M is 0.25 step
            {"wb_gm_shift": WB_GM_AXIS_MIN_G141 - 0.25},
        ):
            bad = verify_ftp_ftpes_avf_vault_and_customwb_cineei_guard(**kw)
            self.assertFalse(bad.valid)
            self.assertEqual(bad.block_errno, EINVAL_ERRNO_PHASE319)

    def test_36_g141_allowed_wb_and_ftp_enums_complete(self) -> None:
        self.assertEqual(len(ALLOWED_FX3_WB_MODES_G141), 14)
        self.assertEqual(ALLOWED_FTP_TRANSFER_MODES_G141, ("Passive", "Active"))
        self.assertEqual(ALLOWED_USBLAN_STATES_G141, ("Disconnected", "Connected"))
        self.assertEqual(ALLOWED_PRIORITY_SET_AWB_G141, ("Standard", "Ambience", "White"))
        self.assertEqual(
            ALLOWED_SHUTTER_AWB_LOCK_G141, ("Off", "Shut. Halfway", "Cont. Shooting")
        )
        self.assertEqual(ALLOWED_SHOCKLESS_WB_G141, ("Off", "1", "2", "3"))
        self.assertEqual(
            CUSTOM_WB_ERROR_0X0220_PP_GAMMAS_G141,
            ("S-Log3", "PPLUT1", "PPLUT2", "PPLUT3", "PPLUT4"),
        )

    def test_37_g141_zero_rf_disabled_tracks_packets_when_ftp_or_usblan_active(
        self,
    ) -> None:
        r_wifi = verify_ftp_ftpes_avf_vault_and_customwb_cineei_guard(
            zero_rf_bench_mode=False,
            requested_airplane_mode="Off",
            requested_ftp_function="On",
            requested_usblan_tethering="Disconnected",
        )
        self.assertTrue(r_wifi.valid)
        self.assertGreater(r_wifi.rf_packets_transmitted, 0)
        self.assertEqual(r_wifi.wired_usblan_ftp_packets, 0)

        r_lan = verify_ftp_ftpes_avf_vault_and_customwb_cineei_guard(
            zero_rf_bench_mode=False,
            requested_airplane_mode="On",
            requested_ftp_function="On",
            requested_usblan_tethering="Connected",
        )
        self.assertTrue(r_lan.valid)
        self.assertEqual(r_lan.rf_packets_transmitted, 0)
        self.assertGreater(r_lan.wired_usblan_ftp_packets, 0)

    def test_38_g141_fx3_ftp_function_with_slot1_non_vault_safe(self) -> None:
        r = verify_ftp_ftpes_avf_vault_and_customwb_cineei_guard(
            zero_rf_bench_mode=False,
            requested_airplane_mode="Off",
            requested_ftp_function="On",
            slot_1_contains_tier0_vault=False,
            slot1_ftp_target_selected=True,
            ftp_transfer_status_write_requested=True,
        )
        self.assertTrue(r.valid)
        self.assertFalse(r.slot1_avf_info_firewall_blocked)

    def test_39_g141_fx6_invalid_atw_speed_rejected(self) -> None:
        for bad_spd in (0, 6):
            r = verify_ftp_ftpes_avf_vault_and_customwb_cineei_guard(
                target_model=FX6_MODEL_NAME_PHASE319,
                fx6_atw_speed=bad_spd,
            )
            self.assertFalse(r.valid)
            self.assertEqual(r.block_errno, EINVAL_ERRNO_PHASE319)

    def test_40_g141_fx6_ui_slots_exceeding_3_rejected(self) -> None:
        r = verify_ftp_ftpes_avf_vault_and_customwb_cineei_guard(
            target_model=FX6_MODEL_NAME_PHASE319,
            fx6_ui_server_slots_claimed=9,
        )
        self.assertFalse(r.valid)
        self.assertEqual(r.block_errno, EINVAL_ERRNO_PHASE319)

    def test_41_g141_fx6_ftp_slot_up_to_16_elf_bound_checked(self) -> None:
        ok = verify_ftp_ftpes_avf_vault_and_customwb_cineei_guard(
            target_model=FX6_MODEL_NAME_PHASE319,
            zero_rf_bench_mode=False,
            requested_airplane_mode="Off",
            requested_ftp_function="On",
            ftp_server_slot=16,
            fx6_ui_server_slots_claimed=FX6_FTP_UI_SERVER_SLOTS_G141,
        )
        self.assertTrue(ok.valid)
        bad = verify_ftp_ftpes_avf_vault_and_customwb_cineei_guard(
            target_model=FX6_MODEL_NAME_PHASE319,
            ftp_server_slot=17,
        )
        self.assertFalse(bad.valid)


class TestGateG142MovieAfFocusMapAnd15AspectMarkerPeaking(unittest.TestCase):
    def test_42_g142_default_safe_state_passes(self) -> None:
        res = verify_movie_af_focusmap_marker_peaking_guard()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_VERIFIED_G142)
        self.assertEqual(res.effective_af_transition_speed, AF_TRANSITION_SPEED_DEFAULT_G142)
        self.assertEqual(
            res.effective_af_subj_shift_sensitivity, AF_SUBJ_SHIFT_SENS_DEFAULT_G142
        )
        self.assertFalse(res.fx3_onbody_focus_map_menu_present)
        self.assertFalse(res.focus_map_hdmi_burnin)
        self.assertFalse(res.marker_hdmi_output)
        self.assertFalse(res.peaking_hdmi_output)
        self.assertTrue(res.exact_15_active_aspect_ratios_verified)
        self.assertEqual(res.matrix_states_checked, 512)

    def test_43_g142_uxc_resid16_anchors_exact(self) -> None:
        self.assertEqual(AF_TRANSITION_SPEED_F_UXC_RESID16_G142, 0x6E9D)
        self.assertEqual(AF_SUBJ_SHIFT_SENS_F_UXC_RESID16_G142, 0x79D6)
        self.assertEqual(AF_ASSIST_F_UXC_RESID16_G142, 0x64A9)
        self.assertEqual(FOCUS_MAP_SHARED_F_UXC_RESID16_G142, 0x61F9)
        self.assertEqual(MARKER_DISPLAY_F_UXC_RESID16_G142, 0x6803)
        self.assertEqual(CENTER_MARKER_F_UXC_RESID16_G142, 0x6707)
        self.assertEqual(ASPECT_MARKER_F_UXC_RESID16_G142, 0x66AC)
        self.assertEqual(SAFETY_ZONE_F_UXC_RESID16_G142, 0x6F50)
        self.assertEqual(GUIDEFRAME_F_UXC_RESID16_G142, 0x62F9)
        self.assertEqual(PEAKING_DISPLAY_F_UXC_RESID16_G142, 0x6FE5)
        self.assertEqual(PEAKING_LEVEL_BASE_UXC_RESID16_G142, 0x014C)
        self.assertEqual(PEAKING_COLOR_BASE_UXC_RESID16_G142, 0x014D)

    def test_44_g142_both_fx3_and_fx6_enforce_1_to_7_speed_and_1_to_5_subj_shift(
        self,
    ) -> None:
        self.assertEqual(AF_TRANSITION_SPEED_MIN_G142, 1)
        self.assertEqual(AF_TRANSITION_SPEED_MAX_G142, 7)
        self.assertEqual(AF_SUBJ_SHIFT_SENS_MIN_G142, 1)
        self.assertEqual(AF_SUBJ_SHIFT_SENS_MAX_G142, 5)

        for mdl in (FX3_MODEL_NAME_PHASE319, FX6_MODEL_NAME_PHASE319):
            for spd in range(1, 8):
                for sens in range(1, 6):
                    ok = verify_movie_af_focusmap_marker_peaking_guard(
                        target_model=mdl,
                        requested_af_transition_speed=spd,
                        requested_af_subj_shift_sensitivity=sens,
                    )
                    self.assertTrue(ok.valid)
                    self.assertFalse(ok.af_subj_shift_6_or_7_rejected)

            for bad_sens in (0, 6, 7):
                bad = verify_movie_af_focusmap_marker_peaking_guard(
                    target_model=mdl,
                    requested_af_subj_shift_sensitivity=bad_sens,
                )
                self.assertFalse(bad.valid)
                if bad_sens in (6, 7):
                    self.assertTrue(bad.af_subj_shift_6_or_7_rejected)
                self.assertEqual(bad.block_errno, EINVAL_ERRNO_PHASE319)

            for bad_spd in (0, 8):
                bad_s = verify_movie_af_focusmap_marker_peaking_guard(
                    target_model=mdl,
                    requested_af_transition_speed=bad_spd,
                )
                self.assertFalse(bad_s.valid)

        claimed = verify_movie_af_focusmap_marker_peaking_guard(
            target_model=FX6_MODEL_NAME_PHASE319,
            claimed_fx6_af_subj_shift_sens_is_1_to_7=True,
        )
        self.assertFalse(claimed.valid)
        self.assertTrue(claimed.af_subj_shift_6_or_7_rejected)

    def test_45_g142_af_reset_behavior_and_incompatible_lenses(self) -> None:
        self.assertEqual(AF_ASSIST_INCOMPATIBLE_LENSES_G142, ("SELP1650", "SEL18200LE"))
        rst = verify_movie_af_focusmap_marker_peaking_guard(
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE319,
            requested_af_transition_speed=1,
            requested_af_subj_shift_sensitivity=1,
            requested_af_assist="On",
        )
        self.assertTrue(rst.valid)
        self.assertEqual(rst.effective_af_transition_speed, 5)
        self.assertEqual(rst.effective_af_subj_shift_sensitivity, 5)
        self.assertEqual(rst.effective_af_assist, "Off")

        for lens in AF_ASSIST_INCOMPATIBLE_LENSES_G142:
            bad = verify_movie_af_focusmap_marker_peaking_guard(
                requested_af_assist="On",
                lens_model=lens,
            )
            self.assertFalse(bad.valid)
            self.assertTrue(bad.af_assist_incompatible_lens_rejected)
            self.assertIn(
                STATUS_BLOCKED_G142_MOVIE_AF_1TO7_1TO5_OR_ASSIST_VIOLATION,
                bad.violation_codes,
            )
            self.assertEqual(bad.block_errno, EINVAL_ERRNO_PHASE319)

    def test_46_g142_critical_fx3_zero_onbody_focus_map_rejected_eopnotsupp(self) -> None:
        for kw in (
            {"requested_fx3_onbody_focus_map": True},
            {"claimed_fx3_ver2_onbody_focus_map": True},
        ):
            r = verify_movie_af_focusmap_marker_peaking_guard(
                target_model=FX3_MODEL_NAME_PHASE319,
                **kw,
            )
            self.assertFalse(r.valid)
            self.assertFalse(r.fx3_onbody_focus_map_menu_present)
            self.assertTrue(r.fx3_onbody_focus_map_rejected)
            self.assertIn(
                STATUS_BLOCKED_G142_FOCUSMAP_ONBODY_OR_EXCLUSION_VIOLATION,
                r.violation_codes,
            )
            self.assertEqual(r.block_errno, EOPNOTSUPP_ERRNO_PHASE319)

    def test_47_g142_external_monitor_control_focus_map_allowed_at_100p_119_88p(
        self,
    ) -> None:
        for fps in (23.98, 29.97, 59.94, 100.0, 119.88):
            ok = verify_movie_af_focusmap_marker_peaking_guard(
                target_model=FX3_MODEL_NAME_PHASE319,
                firmware_version="7.02",
                frame_rate_fps=fps,
                external_focus_map_requested=True,
            )
            self.assertTrue(ok.valid, msg=f"fps={fps} failed: {ok.violation_codes}")
            self.assertTrue(ok.external_monitor_control_focus_map_active)
            self.assertFalse(ok.focus_map_blocked_by_fps_or_exclusion)

        myth = verify_movie_af_focusmap_marker_peaking_guard(
            target_model=FX3_MODEL_NAME_PHASE319,
            frame_rate_fps=119.88,
            external_focus_map_requested=True,
            claimed_100p_or_119_88p_blocks_fx3_focus_map=True,
        )
        self.assertFalse(myth.valid)
        self.assertEqual(myth.block_errno, EINVAL_ERRNO_PHASE319)

    def test_48_g142_external_focus_map_exclusions_blocked_einval(self) -> None:
        self.assertEqual(FOCUS_MAP_HIGH_FPS_BLOCK_THRESHOLD_G142, 150)
        exclusions = (
            {"frame_rate_fps": 150.0},
            {"frame_rate_fps": 240.0},
            {"in_playback_mode": True},
            {"auto_framing_enabled": True},
            {"usb_wired_remote_connected": True},
            {"uvc_streaming_active": True},
            {"hdmi_raw_output_active": True},
            {"focus_magnifier_active": True},
            {"digital_extender_active": True},
            {"is_pdaf_lens": False},
            {"mount_adapter_attached": True},
            {"lens_attached": False},
            {"shoot_mode": SHOOT_MODE_STILL_PHASE319},
            {"claimed_focus_map_burns_into_hdmi_or_rec": True},
        )
        for kw in exclusions:
            r = verify_movie_af_focusmap_marker_peaking_guard(
                external_focus_map_requested=True,
                **kw,
            )
            self.assertFalse(r.valid, msg=f"exclusion {kw} should fail")
            self.assertFalse(r.external_monitor_control_focus_map_active)
            self.assertTrue(r.focus_map_blocked_by_fps_or_exclusion)
            self.assertEqual(r.block_errno, EINVAL_ERRNO_PHASE319)

    def test_49_g142_fx6_native_onbody_focus_map_and_low_fps_block(self) -> None:
        ok = verify_movie_af_focusmap_marker_peaking_guard(
            target_model=FX6_MODEL_NAME_PHASE319,
            frame_rate_fps=23.98,
            fx6_onbody_focus_map_requested=True,
        )
        self.assertTrue(ok.valid)

        low_fps_bad = verify_movie_af_focusmap_marker_peaking_guard(
            target_model=FX6_MODEL_NAME_PHASE319,
            frame_rate_fps=5.0,
            fx6_onbody_focus_map_requested=True,
        )
        self.assertFalse(low_fps_bad.valid)
        self.assertTrue(low_fps_bad.focus_map_blocked_by_fps_or_exclusion)
        self.assertEqual(low_fps_bad.block_errno, EINVAL_ERRNO_PHASE319)

    def test_50_g142_exact_15_active_aspect_ratios_plus_off_equal_16_states(self) -> None:
        self.assertEqual(len(EXACT_15_ACTIVE_ASPECT_RATIOS_FX3_G142), 15)
        self.assertEqual(len(ALLOWED_ASPECT_MARKER_STATES_FX3_G142), 16)
        for ratio in ALLOWED_ASPECT_MARKER_STATES_FX3_G142:
            r = verify_movie_af_focusmap_marker_peaking_guard(
                requested_marker_display="On",
                requested_aspect_marker=ratio,
            )
            self.assertTrue(r.valid, msg=f"ratio={ratio} failed")
            self.assertEqual(r.effective_aspect_marker, ratio)

        b_240 = verify_movie_af_focusmap_marker_peaking_guard(
            requested_marker_display="On",
            requested_aspect_marker="2.40:1",
        )
        self.assertFalse(b_240.valid)
        self.assertEqual(b_240.block_errno, EOPNOTSUPP_ERRNO_PHASE319)

        for bad_ratio in ("1.33:1", "21:9"):
            b = verify_movie_af_focusmap_marker_peaking_guard(
                requested_marker_display="On",
                requested_aspect_marker=bad_ratio,
            )
            self.assertFalse(b.valid)
            self.assertEqual(b.block_errno, EINVAL_ERRNO_PHASE319)

    def test_51_g142_marker_safety_zone_guideframe_and_focus_magnifier_autohide(
        self,
    ) -> None:
        for sz in ALLOWED_FX3_SAFETY_ZONES_G142:
            ok = verify_movie_af_focusmap_marker_peaking_guard(
                requested_marker_display="On",
                requested_center_marker="On",
                requested_safety_zone=sz,
                requested_guideframe="On",
                focus_magnifier_active=True,
            )
            self.assertTrue(ok.valid)
            self.assertTrue(ok.marker_auto_hidden_under_focus_magnifier)
            self.assertFalse(ok.marker_hdmi_output)

        # FX6 92.5%/95% rejected on FX3
        for fx6_sz in ("92.5%", "95%"):
            bad = verify_movie_af_focusmap_marker_peaking_guard(
                target_model=FX3_MODEL_NAME_PHASE319,
                requested_safety_zone=fx6_sz,
            )
            self.assertFalse(bad.valid)
            self.assertEqual(bad.block_errno, EOPNOTSUPP_ERRNO_PHASE319)

        hdmi_bad = verify_movie_af_focusmap_marker_peaking_guard(
            requested_marker_display="On",
            claimed_marker_outputs_to_hdmi=True,
        )
        self.assertFalse(hdmi_bad.valid)

        mag_bad = verify_movie_af_focusmap_marker_peaking_guard(
            requested_marker_display="On",
            focus_magnifier_active=True,
            claimed_marker_visible_during_focus_magnifier=True,
        )
        self.assertFalse(mag_bad.valid)

    def test_52_g142_peaking_4_colors_fx3_vs_bw_fx6_never_hdmi(self) -> None:
        self.assertEqual(ALLOWED_PEAKING_LEVELS_G142, ("High", "Mid", "Low"))
        self.assertEqual(
            ALLOWED_FX3_PEAKING_COLORS_G142, ("Red", "Yellow", "Blue", "White")
        )
        self.assertEqual(
            ALLOWED_FX6_PEAKING_COLORS_G142, ("B&W", "Red", "Yellow", "Blue")
        )
        for color in ALLOWED_FX3_PEAKING_COLORS_G142:
            ok = verify_movie_af_focusmap_marker_peaking_guard(
                requested_peaking_display="On",
                requested_peaking_color=color,
            )
            self.assertTrue(ok.valid)
            self.assertFalse(ok.peaking_hdmi_output)

        fx3_bw = verify_movie_af_focusmap_marker_peaking_guard(
            target_model=FX3_MODEL_NAME_PHASE319,
            requested_peaking_display="On",
            requested_peaking_color="B&W",
        )
        self.assertFalse(fx3_bw.valid)
        self.assertEqual(fx3_bw.block_errno, EOPNOTSUPP_ERRNO_PHASE319)

        fx6_bw = verify_movie_af_focusmap_marker_peaking_guard(
            target_model=FX6_MODEL_NAME_PHASE319,
            requested_peaking_display="On",
            requested_peaking_color="B&W",
        )
        self.assertTrue(fx6_bw.valid)

        hdmi_pk = verify_movie_af_focusmap_marker_peaking_guard(
            requested_peaking_display="On",
            claimed_peaking_outputs_to_hdmi=True,
        )
        self.assertFalse(hdmi_pk.valid)

    def test_53_g142_marker_and_peaking_survive_cam_reset_and_wipe_on_initialize(
        self,
    ) -> None:
        cam_rst = verify_movie_af_focusmap_marker_peaking_guard(
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE319,
            requested_marker_display="On",
            requested_center_marker="On",
            requested_aspect_marker="2.39:1",
            requested_safety_zone="90%",
            requested_guideframe="On",
            requested_peaking_display="On",
            requested_peaking_level="High",
            requested_peaking_color="Red",
        )
        self.assertTrue(cam_rst.valid)
        self.assertTrue(cam_rst.marker_and_peaking_survived_cam_reset)
        self.assertEqual(cam_rst.effective_marker_display, "On")
        self.assertEqual(cam_rst.effective_aspect_marker, "2.39:1")
        self.assertEqual(cam_rst.effective_peaking_display, "On")
        self.assertEqual(cam_rst.effective_peaking_color, "Red")

        init_rst = verify_movie_af_focusmap_marker_peaking_guard(
            reset_action=RESET_ACTION_INITIALIZE_PHASE319,
            requested_marker_display="On",
            requested_aspect_marker="2.39:1",
            requested_peaking_display="On",
            requested_peaking_level="High",
            requested_peaking_color="Red",
        )
        self.assertTrue(init_rst.valid)
        self.assertFalse(init_rst.marker_and_peaking_survived_cam_reset)
        self.assertEqual(init_rst.effective_marker_display, "Off")
        self.assertEqual(init_rst.effective_aspect_marker, "Off")
        self.assertEqual(init_rst.effective_peaking_display, "Off")
        self.assertEqual(init_rst.effective_peaking_level, "Mid")
        self.assertEqual(init_rst.effective_peaking_color, "White")

    def test_54_g142_fx6_user_box_and_aspect_mask_vs_fx3_eopnotsupp(self) -> None:
        fx6_ok = verify_movie_af_focusmap_marker_peaking_guard(
            target_model=FX6_MODEL_NAME_PHASE319,
            fx6_user_box_enabled=True,
            fx6_user_box_width=FX6_USER_BOX_WIDTH_MAX_G142,
            fx6_user_box_height=FX6_USER_BOX_HEIGHT_MAX_G142,
            fx6_user_box_h_pos=FX6_USER_BOX_H_POS_MIN_G142,
            fx6_user_box_v_pos=FX6_USER_BOX_V_POS_MAX_G142,
            fx6_aspect_mask_level=FX6_ASPECT_MASK_MAX_G142,
        )
        self.assertTrue(fx6_ok.valid)

        for kw in (
            {"fx6_user_box_enabled": True},
            {"claimed_fx3_supports_user_box_or_aspect_mask": True},
        ):
            fx3_bad = verify_movie_af_focusmap_marker_peaking_guard(
                target_model=FX3_MODEL_NAME_PHASE319,
                **kw,
            )
            self.assertFalse(fx3_bad.valid)
            self.assertEqual(fx3_bad.block_errno, EOPNOTSUPP_ERRNO_PHASE319)

    def test_55_g142_compute_512_state_matrix_invariant(self) -> None:
        mat = compute_movie_af_focusmap_marker_peaking_matrix()
        self.assertEqual(mat["states_checked"], 512)
        self.assertGreater(mat["af_range_blocked_count"], 0)
        self.assertGreater(mat["onbody_focusmap_blocked_count"], 0)
        self.assertGreater(mat["external_focusmap_valid_count"], 0)
        self.assertGreater(mat["marker_peaking_reset_survived_count"], 0)

    def test_56_g142_request_persistent_emmc_writes_blocked_erofs(self) -> None:
        r = verify_movie_af_focusmap_marker_peaking_guard(
            request_persistent_emmc_writes=True,
        )
        self.assertFalse(r.valid)
        self.assertIn(STATUS_BLOCKED_PERSISTENT_EMMC_WRITE, r.violation_codes)
        self.assertEqual(r.block_errno, EROFS_ERRNO_PHASE319)

    def test_57_g142_fx6_safety_areas_92_5_and_95_valid_on_fx6(self) -> None:
        self.assertEqual(
            ALLOWED_FX6_ASPECT_SAFETY_AREAS_G142,
            ("Off", "80%", "90%", "92.5%", "95%"),
        )
        for area in ALLOWED_FX6_ASPECT_SAFETY_AREAS_G142:
            r = verify_movie_af_focusmap_marker_peaking_guard(
                target_model=FX6_MODEL_NAME_PHASE319,
                requested_safety_zone=area,
            )
            self.assertTrue(r.valid)

    def test_58_g142_fx6_white_peaking_rejected(self) -> None:
        r = verify_movie_af_focusmap_marker_peaking_guard(
            target_model=FX6_MODEL_NAME_PHASE319,
            requested_peaking_display="On",
            requested_peaking_color="White",
        )
        self.assertFalse(r.valid)
        self.assertEqual(r.block_errno, EOPNOTSUPP_ERRNO_PHASE319)

    def test_59_g142_fx6_onbody_focus_map_blocked_when_in_playback(self) -> None:
        r = verify_movie_af_focusmap_marker_peaking_guard(
            target_model=FX6_MODEL_NAME_PHASE319,
            fx6_onbody_focus_map_requested=True,
            in_playback_mode=True,
        )
        self.assertFalse(r.valid)
        self.assertEqual(r.block_errno, EINVAL_ERRNO_PHASE319)

    def test_60_g142_fx3_focus_map_min_fw_6_00_enforced(self) -> None:
        self.assertEqual(FOCUS_MAP_MIN_FX3_FW_G142, 6.00)
        ok = verify_movie_af_focusmap_marker_peaking_guard(
            firmware_version="6.00",
            external_focus_map_requested=True,
        )
        self.assertTrue(ok.valid)
        bad = verify_movie_af_focusmap_marker_peaking_guard(
            firmware_version="5.00",
            external_focus_map_requested=True,
        )
        self.assertFalse(bad.valid)
        self.assertEqual(bad.block_errno, EOPNOTSUPP_ERRNO_PHASE319)

    def test_61_g142_marker_and_peaking_preserve_across_network_reset(self) -> None:
        r = verify_movie_af_focusmap_marker_peaking_guard(
            reset_action=RESET_ACTION_RESET_NETWORK_SET_PHASE319,
            requested_marker_display="On",
            requested_aspect_marker="1.85:1",
            requested_peaking_display="On",
            requested_peaking_color="Yellow",
        )
        self.assertTrue(r.valid)
        self.assertEqual(r.effective_marker_display, "On")
        self.assertEqual(r.effective_aspect_marker, "1.85:1")
        self.assertEqual(r.effective_peaking_display, "On")
        self.assertEqual(r.effective_peaking_color, "Yellow")

    def test_62_g142_sq_mode_still_enforces_marker_and_af_contracts(self) -> None:
        r = verify_movie_af_focusmap_marker_peaking_guard(
            shoot_mode=SHOOT_MODE_SQ_PHASE319,
            frame_rate_fps=120.0,
            requested_af_transition_speed=7,
            requested_af_subj_shift_sensitivity=5,
            requested_marker_display="On",
            requested_aspect_marker="16:9",
        )
        self.assertTrue(r.valid)

    def test_63_g142_external_focus_map_disabled_does_not_fail_at_240fps(self) -> None:
        r = verify_movie_af_focusmap_marker_peaking_guard(
            frame_rate_fps=240.0,
            external_focus_map_requested=False,
        )
        self.assertTrue(r.valid)
        self.assertFalse(r.external_monitor_control_focus_map_active)

    def test_64_g142_fx6_user_box_bounds_enforced(self) -> None:
        for kw in (
            {"fx6_user_box_width": FX6_USER_BOX_WIDTH_MIN_G142 - 1},
            {"fx6_user_box_width": FX6_USER_BOX_WIDTH_MAX_G142 + 1},
            {"fx6_user_box_height": FX6_USER_BOX_HEIGHT_MIN_G142 - 1},
            {"fx6_user_box_height": FX6_USER_BOX_HEIGHT_MAX_G142 + 1},
            {"fx6_user_box_h_pos": FX6_USER_BOX_H_POS_MIN_G142 - 1},
            {"fx6_user_box_h_pos": FX6_USER_BOX_H_POS_MAX_G142 + 1},
            {"fx6_user_box_v_pos": FX6_USER_BOX_V_POS_MIN_G142 - 1},
            {"fx6_user_box_v_pos": FX6_USER_BOX_V_POS_MAX_G142 + 1},
            {"fx6_aspect_mask_level": FX6_ASPECT_MASK_MIN_G142 - 1},
            {"fx6_aspect_mask_level": FX6_ASPECT_MASK_MAX_G142 + 1},
        ):
            r = verify_movie_af_focusmap_marker_peaking_guard(
                target_model=FX6_MODEL_NAME_PHASE319,
                **kw,
            )
            self.assertFalse(r.valid, msg=f"kw={kw} should fail")
            self.assertEqual(r.block_errno, EINVAL_ERRNO_PHASE319)

    def test_65_g142_peaking_all_levels_valid(self) -> None:
        for lvl in ALLOWED_PEAKING_LEVELS_G142:
            r = verify_movie_af_focusmap_marker_peaking_guard(
                requested_peaking_display="On",
                requested_peaking_level=lvl,
            )
            self.assertTrue(r.valid)
            self.assertEqual(r.effective_peaking_level, lvl)

    def test_66_g142_marker_still_mode_valid_with_aspect_marker(self) -> None:
        r = verify_movie_af_focusmap_marker_peaking_guard(
            shoot_mode=SHOOT_MODE_STILL_PHASE319,
            requested_marker_display="On",
            requested_aspect_marker="1:1",
        )
        self.assertTrue(r.valid)
        self.assertEqual(r.effective_aspect_marker, "1:1")

    def test_67_g142_af_assist_on_with_pdaf_lens_valid(self) -> None:
        r = verify_movie_af_focusmap_marker_peaking_guard(
            requested_af_assist="On",
            lens_model="SEL2470GM2",
        )
        self.assertTrue(r.valid)
        self.assertEqual(r.effective_af_assist, "On")
        self.assertFalse(r.af_assist_incompatible_lens_rejected)

    def test_68_g142_reset_initialize_resets_af_speed_sens_and_assist(self) -> None:
        r = verify_movie_af_focusmap_marker_peaking_guard(
            reset_action=RESET_ACTION_INITIALIZE_PHASE319,
            requested_af_transition_speed=2,
            requested_af_subj_shift_sensitivity=2,
            requested_af_assist="On",
        )
        self.assertTrue(r.valid)
        self.assertEqual(r.effective_af_transition_speed, 5)
        self.assertEqual(r.effective_af_subj_shift_sensitivity, 5)
        self.assertEqual(r.effective_af_assist, "Off")


class TestUnified142GatePreflightAndCliPhase319(unittest.TestCase):
    def test_69_preflight_142_clean_room_offline_139_of_142(self) -> None:
        rep = evaluate_142gate_preflight(force_clean_room=True)
        self.assertIsInstance(rep, Master142GateReport)
        self.assertEqual(rep.schema_version, "realhw_142gate_preflight_v1")
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(rep.offline_139_gates_verified)
        self.assertFalse(rep.all_142_gates_verified)
        self.assertTrue(rep.g13_to_g142_all_passed)
        self.assertTrue(rep.g141_to_g142_all_passed)
        self.assertTrue(rep.h0_h1_trial_entry_allowed)
        self.assertEqual(rep.status, "VERIFIED_139_OF_142_AWAITING_PHYSICAL_TIER0")
        self.assertEqual(len(rep.gates), 142)
        self.assertEqual(rep.summary["total_gates"], 142)
        self.assertEqual(rep.summary["verified_gates"], 139)
        self.assertEqual(rep.summary["g141_to_g142_verified"], 2)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.hardware_live_attachment_authorized)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)
        self.assertEqual(rep.usb_packets_transmitted, 0)

    def test_70_preflight_142_dry_run_simulated_all_142(self) -> None:
        rep = evaluate_142gate_preflight(
            force_clean_room=True, dry_run_simulated=True
        )
        self.assertTrue(rep.all_142_gates_verified)
        self.assertEqual(rep.status, "VERIFIED_ALL_142_GATES_DRY_RUN_SIMULATED_BACKUP")
        self.assertEqual(rep.summary["verified_gates"], 142)
        self.assertEqual(rep.summary["blocked_or_pending_gates"], 0)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.persistent_emmc_writes_authorized)

    def test_71_preflight_142_persistent_write_request_blocks(self) -> None:
        rep = evaluate_142gate_preflight(
            force_clean_room=True,
            request_persistent_emmc_writes=True,
        )
        self.assertEqual(rep.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        self.assertFalse(rep.offline_139_gates_verified)
        self.assertFalse(rep.h0_h1_trial_entry_allowed)

    def test_72_preflight_142_g141_violation_propagates(self) -> None:
        rep = evaluate_142gate_preflight(
            force_clean_room=True,
            master_140_override=_build_stub_140_report(dry_run=False, all_g13_140_ok=True),
            ftp_ftpes_customwb_kwargs={
                "zero_rf_bench_mode": True,
                "requested_airplane_mode": "On",
                "requested_usblan_tethering": "Connected",
            },
        )
        self.assertEqual(rep.status, STATUS_BLOCKED_G141_USBLAN_ZERO_RF_BYPASS_VIOLATION)
        self.assertFalse(rep.g141_to_g142_all_passed)
        self.assertFalse(rep.offline_139_gates_verified)
        self.assertEqual(rep.summary["verified_gates"], 138)

    def test_73_preflight_142_g142_violation_propagates(self) -> None:
        rep = evaluate_142gate_preflight(
            force_clean_room=True,
            master_140_override=_build_stub_140_report(dry_run=False, all_g13_140_ok=True),
            movie_af_focusmap_marker_kwargs={
                "requested_fx3_onbody_focus_map": True,
            },
        )
        self.assertEqual(rep.status, STATUS_BLOCKED_G142_FOCUSMAP_ONBODY_OR_EXCLUSION_VIOLATION)
        self.assertFalse(rep.g141_to_g142_all_passed)
        self.assertFalse(rep.offline_139_gates_verified)
        self.assertEqual(rep.summary["verified_gates"], 138)

    def test_74_preflight_142_m140_fault_propagates(self) -> None:
        bad_stub = _build_stub_140_report(dry_run=False, all_g13_140_ok=False)
        bad_stub = dataclasses.replace(bad_stub, status="BLOCKED_BY_MOCK_M140")
        rep = evaluate_142gate_preflight(
            force_clean_room=True,
            master_140_override=bad_stub,
        )
        self.assertEqual(rep.status, "BLOCKED_BY_MOCK_M140")
        self.assertFalse(rep.g13_to_g142_all_passed)
        self.assertFalse(rep.offline_139_gates_verified)

    def test_75_forward_compatible_dynamic_auto_discovery_includes_142(self) -> None:
        eval_re = re.compile(r"^evaluate_(\d+)gate_preflight$")
        candidates = []
        for name in dir(fx3_safety):
            m = eval_re.match(name)
            if m:
                candidates.append((int(m.group(1)), name))
        candidates.sort()
        self.assertIn((142, "evaluate_142gate_preflight"), candidates)
        highest = candidates[-1]
        self.assertGreaterEqual(highest[0], 142)

    def test_76_aliases_and_schema_version_compatibility(self) -> None:
        r1 = evaluate_142_master_safety_gates(force_clean_room=True)
        r2 = run_142_gate_preflight(force_clean_room=True)
        self.assertEqual(r1.schema, "realhw_142gate_preflight_v1")
        self.assertEqual(r1.schema_version, "realhw_142gate_preflight_v1")
        self.assertEqual(r2.summary["verified_gates"], 139)

    def test_77_cli_verify_142_gates_plain_text_and_json_summary(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cli_main(["verify-142-gates", "--clean-room"])
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("verified=139/142", out)
        self.assertIn("raw_firmware_bytes_leaked=0", out)
        self.assertIn("overall_ready_for_hardware_attach=False", out)

        buf_json = io.StringIO()
        with contextlib.redirect_stdout(buf_json):
            rc_json = cli_main(
                [
                    "verify-142-gates",
                    "--clean-room",
                    "--simulate-bench-dry-run",
                    "--summary",
                    "--json",
                ]
            )
        self.assertEqual(rc_json, 0)
        payload = json.loads(buf_json.getvalue())
        self.assertEqual(payload["schema_version"], "realhw_142gate_preflight_v1")
        self.assertEqual(payload["summary"]["verified_gates"], 142)
        self.assertEqual(payload["g141_status"], STATUS_VERIFIED_G141)
        self.assertEqual(payload["g142_status"], STATUS_VERIFIED_G142)

    def test_78_cli_verify_142_gates_full_json_payload(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cli_main(
                [
                    "verify-142-gates",
                    "--clean-room",
                    "--simulate-bench-dry-run",
                    "--json",
                ]
            )
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["schema"], REALHW_142GATE_PREFLIGHT_SCHEMA)
        self.assertEqual(payload["schema_version"], REALHW_142GATE_PREFLIGHT_SCHEMA)
        self.assertEqual(len(payload["gates"]), 142)
        self.assertEqual(payload["raw_firmware_bytes_leaked"], 0)
        self.assertFalse(payload["overall_ready_for_hardware_attach"])

    def test_79_cli_g141_and_g142_subcommands_plain_and_json(self) -> None:
        for cmd in (
            "verify-ftp-ftpes-avf-vault-customwb-guard",
            "verify-g141-ftp-ftpes-customwb",
            "verify-movie-af-focusmap-marker-peaking-guard",
            "verify-g142-movie-af-focusmap-marker",
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

    def test_80_standalone_guard_cli_main_all_modes(self) -> None:
        for argv in (
            ["--clean-room", "--gate", "g141", "--json", "--summary"],
            ["--clean-room", "--gate", "g142", "--json", "--summary"],
            [
                "--clean-room",
                "--gate",
                "142",
                "--simulate-bench-dry-run",
                "--json",
                "--summary",
            ],
            ["--clean-room", "--gate", "142"],
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = guard_cli_main(argv)
            self.assertEqual(rc, 0)
            self.assertTrue(buf.getvalue().strip())

    def test_81_cli_help_percent_safety_no_value_error(self) -> None:
        for argv in (
            ["verify-ftp-ftpes-avf-vault-customwb-guard", "--help"],
            ["verify-movie-af-focusmap-marker-peaking-guard", "--help"],
            ["verify-142-gates", "--help"],
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

    def test_82_g141_and_g142_donor_mode_consistent_with_clean_room(self) -> None:
        if os.environ.get(ENV_FORCE_CLEAN_ROOM) or os.environ.get(
            ENV_CLEAN_ROOM_TEST_PHASE319
        ):
            self.skipTest("Forced clean-room active")
        if not _donors_available_here():
            self.skipTest("Donor binaries absent")
        rep_donor = evaluate_142gate_preflight(force_clean_room=False)
        rep_clean = evaluate_142gate_preflight(force_clean_room=True)
        self.assertEqual(rep_donor.verification_mode, "LOCAL_DONOR_O_RDONLY")
        self.assertEqual(rep_clean.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(
            rep_donor.summary["verified_gates"], rep_clean.summary["verified_gates"]
        )
        self.assertEqual(rep_donor.raw_firmware_bytes_leaked, 0)

    def test_83_g141_and_g142_verdicts_and_to_dict_json_serializable(self) -> None:
        v1, r1 = evaluate_g141_ftp_ftpes_avf_vault_and_customwb_cineei_guard(
            force_clean_room=True
        )
        v2, r2 = evaluate_g142_movie_af_focusmap_marker_peaking_guard(
            force_clean_room=True
        )
        self.assertEqual(v1.gate_id, G141)
        self.assertEqual(v1.gate_code, G141_GATE_CODE)
        self.assertTrue(v1.passed)
        self.assertEqual(v2.gate_id, G142)
        self.assertEqual(v2.gate_code, G142_GATE_CODE)
        self.assertTrue(v2.passed)
        self.assertIn("ftp_ftpes_customwb_vault_guard", json.dumps(r1.to_dict()))
        self.assertIn("movie_af_focusmap_marker_peaking_guard", json.dumps(r2.to_dict()))

    def test_84_resolvers_return_valid_dict_state(self) -> None:
        s1 = resolve_fx3_ftp_ftpes_customwb_state()
        s2 = resolve_fx3_movie_af_focusmap_marker_peaking_state()
        self.assertTrue(s1["valid"])
        self.assertEqual(s1["effective_ftp_function"], "Off")
        self.assertTrue(s2["valid"])
        self.assertEqual(s2["effective_af_transition_speed"], 5)

    def test_85_non_bool_int_guard_rejects_booleans_for_numeric_fields(self) -> None:
        for bad_val in (True, False, "1"):
            r1 = verify_ftp_ftpes_avf_vault_and_customwb_cineei_guard(
                ftp_server_slot=bad_val,  # type: ignore[arg-type]
            )
            self.assertFalse(r1.valid)
            r2 = verify_movie_af_focusmap_marker_peaking_guard(
                requested_af_transition_speed=bad_val,  # type: ignore[arg-type]
            )
            self.assertFalse(r2.valid)

    def test_86_g141_invalid_body_identity_rejected(self) -> None:
        for kw in (
            {"body_model_name": "OTHER"},
            {"body_model_id": True},
            {"body_model_id": 0x1234},
            {"help_guide_code": "bad"},
            {"firmware_version": "bad"},
        ):
            r = verify_ftp_ftpes_avf_vault_and_customwb_cineei_guard(**kw)
            self.assertFalse(r.valid)
            self.assertIn(STATUS_BLOCKED_G141_TELEMETRY_INVALID, r.violation_codes)

    def test_87_g142_invalid_body_identity_rejected(self) -> None:
        for kw in (
            {"body_model_name": "OTHER"},
            {"body_model_id": True},
            {"body_model_id": 0x1234},
            {"help_guide_code": "bad"},
            {"firmware_version": "bad"},
        ):
            r = verify_movie_af_focusmap_marker_peaking_guard(**kw)
            self.assertFalse(r.valid)
            self.assertIn(STATUS_BLOCKED_G142_TELEMETRY_INVALID, r.violation_codes)

    def test_88_g141_ftp_suboptions_enumerated_and_validated(self) -> None:
        for cert_beh in ALLOWED_FTP_ROOT_CERT_ERR_BEHAVIORS_G141:
            for flag in ALLOWED_FTP_CLIP_FLAGS_G141:
                for raw_t in ALLOWED_FTP_RAW_JH_TARGETS_G141:
                    for mov_t in ALLOWED_FTP_MOVIE_TARGETS_G141:
                        r = verify_ftp_ftpes_avf_vault_and_customwb_cineei_guard(
                            ftp_root_cert_error_behavior=cert_beh,
                            ftp_clip_flag_filter=flag,
                            ftp_raw_jh_target=raw_t,
                            ftp_movie_target=mov_t,
                        )
                        self.assertTrue(r.valid)

        bad_flag = verify_ftp_ftpes_avf_vault_and_customwb_cineei_guard(
            ftp_clip_flag_filter="INVALID_FLAG"
        )
        self.assertFalse(bad_flag.valid)

    def test_89_g141_shared_mode_and_reset_enums_exact(self) -> None:
        self.assertEqual(
            ALLOWED_SHOOT_MODES_PHASE319,
            (SHOOT_MODE_STILL_PHASE319, SHOOT_MODE_MOVIE_PHASE319, SHOOT_MODE_SQ_PHASE319),
        )
        self.assertEqual(
            ALLOWED_RESET_ACTIONS_PHASE319,
            (
                RESET_ACTION_NONE_PHASE319,
                RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE319,
                RESET_ACTION_RESET_NETWORK_SET_PHASE319,
                RESET_ACTION_INITIALIZE_PHASE319,
            ),
        )
        self.assertEqual(
            ALLOWED_LOG_SHOOTING_MODES_PHASE319,
            (
                LOG_SHOOTING_OFF_PHASE319,
                LOG_SHOOTING_FLEXIBLE_ISO_PHASE319,
                LOG_SHOOTING_CINE_EI_PHASE319,
                LOG_SHOOTING_CINE_EI_QUICK_PHASE319,
            ),
        )
        self.assertEqual(EROFS_ERRNO_PHASE319, 30)
        self.assertEqual(EOPNOTSUPP_ERRNO_PHASE319, 95)
        self.assertEqual(EINVAL_ERRNO_PHASE319, 22)
        self.assertEqual(EBUSY_ERRNO_PHASE319, 16)
        self.assertEqual(ENODEV_ERRNO_PHASE319, 19)

    def test_90_g142_marker_and_peaking_preserve_center_and_guideframe_on_cam_reset(
        self,
    ) -> None:
        r = verify_movie_af_focusmap_marker_peaking_guard(
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE319,
            requested_marker_display="On",
            requested_center_marker="On",
            requested_guideframe="On",
        )
        self.assertTrue(r.valid)
        self.assertEqual(r.effective_center_marker, "On")
        self.assertEqual(r.effective_guideframe, "On")

    def test_91_g142_fx3_focus_map_blocked_with_laea_mount_adapter(self) -> None:
        r = verify_movie_af_focusmap_marker_peaking_guard(
            external_focus_map_requested=True,
            mount_adapter_attached=True,
        )
        self.assertFalse(r.valid)
        self.assertTrue(r.focus_map_blocked_by_fps_or_exclusion)
        self.assertEqual(r.block_errno, EINVAL_ERRNO_PHASE319)

    def test_92_preflight_142_donorless_work_root_none_clean_room_fallback(self) -> None:
        fake_paths = DonorThermalPowerPaths(
            work_root=None,
            fx3_lib_dir=None,
            fx3_appfw_path=None,
            fx3_cp_path=None,
            fx3_bk4_path=None,
            fx6_lib_dir=None,
            fx6_bk4_path=None,
            fx6_cp_path=None,
        )
        with mock.patch.dict(
            os.environ,
            {ENV_FORCE_CLEAN_ROOM: "", ENV_CLEAN_ROOM_TEST_PHASE319: ""},
        ), mock.patch(
            "fx3_safety.realhw_ftp_ftpes_customwb_af_focusmap_marker_and_142gate_guard.resolve_donor_thermal_power_paths",
            return_value=fake_paths,
        ):
            rep = evaluate_142gate_preflight(
                DEFAULT_REPO_ROOT,
                force_clean_room=False,
            )
            self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertTrue(rep.offline_139_gates_verified)
            self.assertEqual(rep.summary["verified_gates"], 139)
            self.assertEqual(rep.raw_firmware_bytes_leaked, 0)


if __name__ == "__main__":
    unittest.main()
