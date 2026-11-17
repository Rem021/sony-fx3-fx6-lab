"""Phase 283 (Task H326, 118/118 Safety Gates, Wave-49) Dual-Mode Unit Tests
(78 tests, < 5.0s runtime) for
`fx3_safety.realhw_raw_heif_colorspace_shuttertype_nr_drive_and_118gate_guard`:

- Gate `G117` (`GATE_G117_RAW_HEIF_HLG_STILL_AND_COLORSPACE_ADOBERGB_PREFIX_GUARD`):
  - `[RAW File Type]` (`BKID_APP_setting_still_raw_file_type`, `_f.uxc` `0x6ff2`):
    stock `ILME-FX3` (`12MP IMX510`, `Ver. 7.02`, `ilc/2210`) exposes ONLY
    `Compressed` (default) and `Uncompressed` 14-bit `.ARW`; rejects spoofed
    dormant `Lossless Comp` (`0x6b56` / `RAW_FILE_TYPE_LOSSLESS`,
    `STATUS_BLOCKED_G117_FX3_DORMANT_LOSSLESS_RAW_SPOOF_VIOLATION`); contrasts
    still-less `ILME-FX6` (`Ver. 6.01`, `PRODUCT_MODEL_CHAPLIN`,
    `fx6_still_pipeline_supported == False`, `fx6_mechanical_shutter == False`).
  - `[JPEG/HEIF Switch]` (`JPEG` default, `HEIF(4:2:0)`, `HEIF(4:2:2)`, `0x742a`)
    & `[HLG Still Image]` (`Off` default, `0x76c8`): `[HLG Still Image] = [On]`
    requires `HEIF` + `File Format = HEIF` only + `P/A/S/M`, locks out
    `Picture Profile`, `Creative Look`, `D-Range Optimizer`, and `DRO Bracket`,
    and overrides `[Color Space]` to `BT.2100/BT.2020`
    (`STATUS_BLOCKED_G117_HLG_STILL_PREREQ_OR_LOCKOUT_VIOLATION`).
  - `[Color Space]` (`MENU -> Shooting -> [Image Quality/Rec] -> [Color Space]`,
    `0x68b7`): `sRGB` (`0xe07d` default -> `DSC00001`) vs `AdobeRGB` (`0xe07e` ->
    DCF 2.0 `_DSC0001` automatic leading `_`), `[Set File Name]` (`0x6993`)
    forbids manual leading `_` and survives `[Camera Settings Reset]`, and
    `HEIF` ignores `sRGB`/`AdobeRGB` selection
    (`STATUS_BLOCKED_G117_COLORSPACE_ADOBERGB_PREFIX_VIOLATION`) across 648
    matrix states.
- Gate `G118` (`GATE_G118_SHUTTER_TYPE_FLASH_SYNC_ELECTRONIC_5LOCK_NR_AND_DRIVE_GUARD`):
  - `[Shutter Type]` (`BKID_APP_setting_still_shutter_type`, `_f.uxc` `0x7aa9`):
    stock `ILME-FX3` exposes ONLY `Mechanical Shutter` (default) and
    `Electronic Shutter` (`P/A/S/M` only; forced `Electronic Shutter` when
    `[Silent Mode] = [On]` `0x7a53`); rejects any spoofed `Auto` shutter type
    (`STATUS_BLOCKED_G118_FX3_SHUTTER_TYPE_AUTO_SPOOF_VIOLATION`); enforces
    `[e-Front Curtain Shut.]` (`0x64c6`, `On` default) survival across
    `[Camera Settings Reset]`.
  - Strictly `1/250 s` mechanical flash sync ceiling (`0x759b`, no `1/320 s`
    APS-C sync) and 5-function Electronic Shutter / Silent Mode lockout
    (`Flash shooting`, `Long Exposure NR`, `e-Front Curtain Shut.`, `BULB`,
    `Anti-flicker Shoot.`,
    `STATUS_BLOCKED_G118_ELECTRONIC_SHUTTER_5LOCK_OR_SYNC_VIOLATION`).
  - `[Long Exposure NR]` (`On` default `0x6cd7`, `>= 1 s` dark frame, blocked in
    `Cont. Shooting`/`Cont. Bracket`/`Electronic Shutter`), `[High ISO NR]`
    (`Normal` default `0x650b`, unavailable for `RAW`-only and never alters
    `.ARW` raw data), and `[Drive Mode]` (`8` modes, `Cont. Shooting: Hi+`
    `10 fps` `0x68d1` speed drop on `Uncompressed` RAW or Flash, `Hi+/Hi/Mid`
    AF lock to 1st frame at `> F11`, and `DRO Bracket` lockout under
    `HLG Still Image = On`,
    `STATUS_BLOCKED_G118_NR_OR_DRIVE_CONT_BOUNDARY_VIOLATION`) across 384
    matrix states.
- Unified `118`-Gate Master Safety Preflight (`evaluate_118gate_preflight` /
  `verify-118-gates`): `115/118` offline (`VERIFIED_115_OF_118_AWAITING_PHYSICAL_TIER0`)
  and `118/118` in `--simulate-bench-dry-run`
  (`VERIFIED_ALL_118_GATES_DRY_RUN_SIMULATED_BACKUP`) with all hardware
  write/live-attach redlines hard-locked `False`.
"""

from __future__ import annotations

import contextlib
import dataclasses
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import fx3_safety
from fx3_safety.__main__ import main as cli_main
from fx3_safety.realhw_pp_scinetone_creativelook_dro_wb_metering_and_116gate_guard import (
    Master116GateReport,
    evaluate_116gate_preflight,
)
from fx3_safety.realhw_raw_heif_colorspace_shuttertype_nr_drive_and_118gate_guard import (
    ADOBERGB_DEFAULT_PREFIX_G117,
    ADOBERGB_DSC_HINT_UXC_RESID16_G117,
    ALLOWED_COLOR_SPACES_G117,
    ALLOWED_CONT_SPEEDS_G118,
    ALLOWED_FILE_FORMATS_G117,
    ALLOWED_HIGH_ISO_NR_MODES_G118,
    ALLOWED_JH_SWITCH_MODES_G117,
    ALLOWED_RESET_ACTIONS_PHASE283,
    ALLOWED_SHOOT_MODES_PHASE283,
    ALLOWED_STILL_QUALITIES_G117,
    ALLOWED_STILL_SIZES_G117,
    APSC_FLASH_SYNC_SPOOF_DENOM_G118,
    COLOR_SPACE_ADOBERGB_G117,
    COLOR_SPACE_ADOBERGB_UXC_RESID16_G117,
    COLOR_SPACE_BT2100_BT2020_G117,
    COLOR_SPACE_FACTORY_DEFAULT_G117,
    COLOR_SPACE_MENU_PATH_G117,
    COLOR_SPACE_SRGB_G117,
    COLOR_SPACE_SRGB_UXC_RESID16_G117,
    COLOR_SPACE_UXC_RESID16_G117,
    CONT_AF_FIRST_FRAME_LOCK_SPEEDS_G118,
    CONT_AF_LOCK_APERTURE_THRESHOLD_G118,
    CONT_SHOOTING_HI_PLUS_UXC_RESID16_G118,
    CONT_SPEED_HI_G118,
    CONT_SPEED_HI_PLUS_G118,
    CONT_SPEED_LO_G118,
    CONT_SPEED_MAX_FPS_G118,
    CONT_SPEED_MID_G118,
    DEFAULT_REPO_ROOT,
    DONOR_CHECK_CI_MAX_SECONDS_PHASE283,
    DONOR_CHECK_MAX_SECONDS_PHASE283,
    DORMANT_LOSSLESS_COMP_UXC_RESID16_G117,
    DRIVE_CONT_BRACKET_G118,
    DRIVE_CONT_G118,
    DRIVE_DRO_BRACKET_G118,
    DRIVE_MODE_FACTORY_DEFAULT_G118,
    DRIVE_MODE_MENU_PATH_G118,
    DRIVE_MODE_UXC_RESID16_G118,
    DRIVE_SELF_TIMER_CONT_G118,
    DRIVE_SELF_TIMER_SINGLE_G118,
    DRIVE_SINGLE_BRACKET_G118,
    DRIVE_SINGLE_G118,
    DRIVE_WB_BRACKET_G118,
    E_FRONT_CURTAIN_DEFAULT_G118,
    E_FRONT_CURTAIN_MENU_PATH_G118,
    E_FRONT_CURTAIN_UXC_RESID16_G118,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    ELECTRONIC_SHUTTER_5LOCKED_FUNCTIONS_G118,
    ENV_CLEAN_ROOM_TEST_PHASE283,
    FILE_FORMAT_FACTORY_DEFAULT_G117,
    FILE_FORMAT_HEIF_G117,
    FILE_FORMAT_JPEG_G117,
    FILE_FORMAT_RAW_G117,
    FILE_FORMAT_RAW_HEIF_G117,
    FILE_FORMAT_RAW_JPEG_G117,
    FX3_DEFAULT_FW_VERSION_PHASE283,
    FX3_EXACT_2_RAW_FILE_TYPES_G117,
    FX3_EXACT_2_SHUTTER_TYPES_G118,
    FX3_EXACT_8_DRIVE_MODES_G118,
    FX3_FLASH_SYNC_CEILING_DENOM_G118,
    FX3_FLASH_SYNC_CEILING_LABEL_G118,
    FX3_FLASH_SYNC_CEILING_SECONDS_G118,
    FX3_HELP_GUIDE_CODE_PHASE283,
    FX3_MODEL_ID,
    FX3_MODEL_NAME,
    FX6_DEFAULT_FW_VERSION_PHASE283,
    FX6_MODEL_NAME_PHASE283,
    G117,
    G117_GATE_CODE,
    G117_GATE_ID,
    G118,
    G118_GATE_CODE,
    G118_GATE_ID,
    GATE_G117_RAW_HEIF_HLG_STILL_AND_COLORSPACE_ADOBERGB_PREFIX_GUARD,
    GATE_G118_SHUTTER_TYPE_FLASH_SYNC_ELECTRONIC_5LOCK_NR_AND_DRIVE_GUARD,
    HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    HEIF_BIT_DEPTH_FX3_G117,
    HIGH_ISO_NR_FACTORY_DEFAULT_G118,
    HIGH_ISO_NR_LOW_G118,
    HIGH_ISO_NR_MENU_PATH_G118,
    HIGH_ISO_NR_NORMAL_G118,
    HIGH_ISO_NR_OFF_G118,
    HLG_STILL_IMAGE_MENU_PATH_G117,
    HLG_STILL_IMAGE_UXC_RESID16_G117,
    HLG_STILL_LOCKED_OUT_FUNCTIONS_G117,
    HUMAN_HARDWARE_ATTACH_TOKEN,
    IMAGE_QUALITY_SETTINGS_MENU_PATH_G117,
    JH_SWITCH_FACTORY_DEFAULT_G117,
    JH_SWITCH_HEIF_420_G117,
    JH_SWITCH_HEIF_422_G117,
    JH_SWITCH_JPEG_G117,
    JPEG_HEIF_SWITCH_MENU_PATH_G117,
    LONG_EXP_NR_DEFAULT_G118,
    LONG_EXP_NR_THRESHOLD_SECONDS_G118,
    LONG_EXPOSURE_NR_MENU_PATH_G118,
    Master118GateReport,
    PASM_SHOOT_MODES_PHASE283,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED,
    PHYSICAL_USB_PACKETS_EMITTED,
    PINNED_FX3_APPFW_SLICES_PHASE283,
    PINNED_FX3_APPFW_SLICES_SHA256_PHASE283,
    PINNED_FX6_APPFW_SLICES_PHASE283,
    PINNED_FX6_APPFW_SLICES_SHA256_PHASE283,
    PINNED_PHASE283_DONOR_SPECS,
    Phase283DonorAuditResult,
    RAW_BIT_DEPTH_FX3_G117,
    RAW_FIRMWARE_BYTES_LEAKED,
    RAW_FILE_TYPE_UXC_RESID16_G117,
    RAW_TYPE_COMPRESSED_G117,
    RAW_TYPE_DORMANT_LOSSLESS_COMP_G117,
    RAW_TYPE_FACTORY_DEFAULT_G117,
    RAW_TYPE_UNCOMPRESSED_G117,
    REALHW_RAW_HEIF_COLORSPACE_SHUTTERTYPE_NR_DRIVE_118GATE_SCHEMA,
    REALHW_RAW_HEIF_COLORSPACE_SHUTTERTYPE_NR_DRIVE_118GATE_VERSION,
    RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE283,
    RESET_ACTION_INITIALIZE_PHASE283,
    RESET_ACTION_NONE_PHASE283,
    RESET_ACTION_RESET_NETWORK_SET_PHASE283,
    SET_FILE_NAME_DEFAULT_PREFIX_G117,
    SET_FILE_NAME_MENU_PATH_G117,
    SET_FILE_NAME_PREFIX_LENGTH_G117,
    SET_FILE_NAME_UXC_RESID16_G117,
    SHOOT_MODE_A_PHASE283,
    SHOOT_MODE_INTELLIGENT_AUTO_PHASE283,
    SHOOT_MODE_M_PHASE283,
    SHOOT_MODE_P_PHASE283,
    SHOOT_MODE_S_PHASE283,
    SHUTTER_TYPE_ELECTRONIC_G118,
    SHUTTER_TYPE_FACTORY_DEFAULT_G118,
    SHUTTER_TYPE_INTERVAL_DEFAULT_G118,
    SHUTTER_TYPE_MECHANICAL_G118,
    SHUTTER_TYPE_MENU_PATH_G118,
    SHUTTER_TYPE_SIBLING_AUTO_TRAP_G118,
    SHUTTER_TYPE_UXC_RESID16_G118,
    SILENT_MODE_DEFAULT_G118,
    SILENT_MODE_MENU_PATH_G118,
    SPI_NOR_WRITE_AUTHORIZED,
    STATUS_BLOCKED_G117_COLORSPACE_ADOBERGB_PREFIX_VIOLATION,
    STATUS_BLOCKED_G117_FX3_DORMANT_LOSSLESS_RAW_SPOOF_VIOLATION,
    STATUS_BLOCKED_G117_HLG_STILL_PREREQ_OR_LOCKOUT_VIOLATION,
    STATUS_BLOCKED_G117_TELEMETRY_INVALID,
    STATUS_BLOCKED_G118_ELECTRONIC_SHUTTER_5LOCK_OR_SYNC_VIOLATION,
    STATUS_BLOCKED_G118_FX3_SHUTTER_TYPE_AUTO_SPOOF_VIOLATION,
    STATUS_BLOCKED_G118_NR_OR_DRIVE_CONT_BOUNDARY_VIOLATION,
    STATUS_BLOCKED_G118_TELEMETRY_INVALID,
    STATUS_BLOCKED_PHASE283_DONOR_INTEGRITY,
    STATUS_VERIFIED_G117,
    STATUS_VERIFIED_G118,
    STILL_QUALITY_EXTRA_FINE_G117,
    STILL_QUALITY_FACTORY_DEFAULT_G117,
    STILL_QUALITY_FINE_G117,
    STILL_QUALITY_STANDARD_G117,
    STILL_SIZE_L_G117,
    USB_PACKETS_TRANSMITTED,
    _default_donor_budget_seconds_phase283,
    _is_forced_clean_room,
    audit_phase283_donor_contracts,
    compute_raw_heif_hlg_colorspace_matrix,
    compute_shutter_type_nr_drive_matrix,
    evaluate_118_master_safety_gates,
    evaluate_118gate_preflight,
    evaluate_g117_raw_heif_colorspace_guard,
    evaluate_g118_shutter_type_nr_drive_guard,
    main as module_main,
    resolve_fx3_raw_heif_hlg_colorspace_state,
    resolve_fx3_shutter_type_nr_drive_state,
    run_118_gate_preflight,
    verify_raw_heif_colorspace_guard,
    verify_shutter_type_nr_drive_guard,
)


def _subprocess_timeout_seconds() -> float:
    return (
        15.0
        if os.environ.get("GITHUB_ACTIONS", "").strip().lower() == "true"
        else 10.0
    )


class TestPhase283RawHeifColorSpaceShutterNrDrive118GateGuard(unittest.TestCase):
    """78 unit tests validating Phase 283 (G117 + G118 + unified 118-gate preflight)."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.donor_audit = audit_phase283_donor_contracts()
        cls.clean_audit = audit_phase283_donor_contracts(force_clean_room=True)
        cls.clean_offline_116: Master116GateReport = evaluate_116gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=False,
        )
        cls.clean_dryrun_116: Master116GateReport = evaluate_116gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
        )

    # --- 1. Hard-Locked Safety Redlines & Exports (Tests 01-06) ---

    def test_01_hard_locked_hardware_safety_redlines_are_false_and_zero(self) -> None:
        self.assertFalse(HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        self.assertFalse(HUMAN_HARDWARE_ATTACH_TOKEN)
        self.assertFalse(EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        self.assertFalse(SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(PERSISTENT_WRITE_RELEASE)
        self.assertFalse(PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED)
        self.assertEqual(USB_PACKETS_TRANSMITTED, 0)
        self.assertEqual(PHYSICAL_USB_PACKETS_EMITTED, 0)
        self.assertEqual(RAW_FIRMWARE_BYTES_LEAKED, 0)

    def test_02_schema_gate_ids_and_aliases(self) -> None:
        self.assertEqual(
            REALHW_RAW_HEIF_COLORSPACE_SHUTTERTYPE_NR_DRIVE_118GATE_SCHEMA,
            "realhw_raw_heif_colorspace_shuttertype_nr_drive_and_118gate_guard_v1",
        )
        self.assertEqual(REALHW_RAW_HEIF_COLORSPACE_SHUTTERTYPE_NR_DRIVE_118GATE_VERSION, "1.0.0")
        self.assertEqual(G117, G117_GATE_ID)
        self.assertEqual(G118, G118_GATE_ID)
        self.assertEqual(
            GATE_G117_RAW_HEIF_HLG_STILL_AND_COLORSPACE_ADOBERGB_PREFIX_GUARD,
            G117_GATE_CODE,
        )
        self.assertEqual(
            GATE_G118_SHUTTER_TYPE_FLASH_SYNC_ELECTRONIC_5LOCK_NR_AND_DRIVE_GUARD,
            G118_GATE_CODE,
        )
        self.assertIs(evaluate_118_master_safety_gates, evaluate_118gate_preflight)
        self.assertIs(run_118_gate_preflight, evaluate_118gate_preflight)

    def test_03_package_root_exports_all_phase283_symbols(self) -> None:
        expected = [
            "audit_phase283_donor_contracts",
            "compute_raw_heif_hlg_colorspace_matrix",
            "compute_shutter_type_nr_drive_matrix",
            "resolve_fx3_raw_heif_hlg_colorspace_state",
            "resolve_fx3_shutter_type_nr_drive_state",
            "verify_raw_heif_colorspace_guard",
            "verify_shutter_type_nr_drive_guard",
            "evaluate_g117_raw_heif_colorspace_guard",
            "evaluate_g118_shutter_type_nr_drive_guard",
            "evaluate_118gate_preflight",
            "evaluate_118_master_safety_gates",
            "run_118_gate_preflight",
            "Master118GateReport",
            "Phase283DonorAuditResult",
            "RawHeifColorSpaceGuardResult",
            "ShutterTypeNrDriveGuardResult",
            "G117RawHeifColorSpaceGuardResult",
            "G118ShutterTypeNrDriveGuardResult",
        ]
        for name in expected:
            self.assertTrue(hasattr(fx3_safety, name), f"Missing export: {name}")
            self.assertIn(name, fx3_safety.__all__)

    def test_04_model_constants_and_ci_donor_budget_rule(self) -> None:
        self.assertEqual(FX3_MODEL_NAME, "ILME-FX3")
        self.assertEqual(FX3_MODEL_ID, 0x91030080)
        self.assertEqual(FX6_MODEL_NAME_PHASE283, "ILME-FX6")
        self.assertEqual(FX3_DEFAULT_FW_VERSION_PHASE283, "7.02")
        self.assertEqual(FX6_DEFAULT_FW_VERSION_PHASE283, "6.01")
        self.assertEqual(FX3_HELP_GUIDE_CODE_PHASE283, "ilc/2210")
        with mock.patch.dict(os.environ, {"GITHUB_ACTIONS": "true"}):
            self.assertEqual(
                _default_donor_budget_seconds_phase283(),
                DONOR_CHECK_CI_MAX_SECONDS_PHASE283,
            )
        with mock.patch.dict(os.environ, {"GITHUB_ACTIONS": ""}):
            self.assertEqual(
                _default_donor_budget_seconds_phase283(),
                DONOR_CHECK_MAX_SECONDS_PHASE283,
            )

    def test_05_clean_room_env_var_detection(self) -> None:
        for env_key in (ENV_CLEAN_ROOM_TEST_PHASE283, "FX3_FX6_FORCE_CLEAN_ROOM"):
            with mock.patch.dict(os.environ, {env_key: "1"}):
                self.assertTrue(_is_forced_clean_room())
        self.assertTrue(_is_forced_clean_room(True))
        self.assertFalse(_is_forced_clean_room(False))

    def test_06_pinned_appfw_slices_integrity(self) -> None:
        self.assertEqual(len(PINNED_FX3_APPFW_SLICES_PHASE283), 20)
        self.assertEqual(len(PINNED_FX6_APPFW_SLICES_PHASE283), 4)
        self.assertEqual(len(PINNED_PHASE283_DONOR_SPECS), 11)
        fx3_concat = hashlib.sha256(
            b"".join(tok for _off, tok in PINNED_FX3_APPFW_SLICES_PHASE283)
        ).hexdigest()
        fx6_concat = hashlib.sha256(
            b"".join(tok for _off, tok in PINNED_FX6_APPFW_SLICES_PHASE283)
        ).hexdigest()
        self.assertEqual(fx3_concat, PINNED_FX3_APPFW_SLICES_SHA256_PHASE283)
        self.assertEqual(fx6_concat, PINNED_FX6_APPFW_SLICES_SHA256_PHASE283)

    # --- 2. Dual-Mode Donor Contract Audit (Tests 07-12) ---

    def test_07_donor_audit_active_mode_within_budget_zero_leak(self) -> None:
        self.assertTrue(self.donor_audit.valid)
        self.assertIn(
            self.donor_audit.verification_mode,
            ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"),
        )
        self.assertTrue(self.donor_audit.within_budget_200ms)
        self.assertEqual(self.donor_audit.raw_firmware_bytes_leaked, 0)
        self.assertTrue(self.donor_audit.fx3_contracts_verified)
        self.assertTrue(self.donor_audit.fx6_contracts_verified)
        self.assertTrue(self.donor_audit.four_lang_resid16_parity_verified)

    def test_08_forced_clean_room_donor_audit_deterministic(self) -> None:
        self.assertTrue(self.clean_audit.valid)
        self.assertEqual(self.clean_audit.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(self.clean_audit.access_mode, "SYNTHETIC_CLEAN_ROOM")
        self.assertEqual(self.clean_audit.files_inspected, 0)
        self.assertEqual(len(self.clean_audit.checked_markers), 11)
        self.assertEqual(self.clean_audit.missing_markers, ())
        self.assertEqual(self.clean_audit.raw_firmware_bytes_leaked, 0)

    def test_09_donor_audit_missing_directory_falls_back_to_clean_room(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            res = audit_phase283_donor_contracts(work_root=Path(td), force_clean_room=False)
            self.assertTrue(res.valid)
            self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertEqual(res.files_inspected, 0)

    def test_10_donor_audit_tampered_uxc_marker_blocks_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for key, (_body, rel, exp_sz, _sha, markers, _label) in PINNED_PHASE283_DONOR_SPECS.items():
                fp = root / rel
                fp.parent.mkdir(parents=True, exist_ok=True)
                if key in ("fx3_appfw_so", "fx6_appfw_so"):
                    fp.write_bytes(b"\x00" * exp_sz)
                else:
                    fp.write_bytes(b"".join(markers))
            res = audit_phase283_donor_contracts(work_root=root, force_clean_room=False)
            self.assertFalse(res.valid)
            self.assertEqual(res.status, STATUS_BLOCKED_PHASE283_DONOR_INTEGRITY)
            self.assertTrue(len(res.missing_markers) > 0)

    def test_11_donor_audit_budget_exceeded_returns_blocked_status(self) -> None:
        res = audit_phase283_donor_contracts(force_clean_room=True, max_budget_seconds=-1.0)
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_PHASE283_DONOR_INTEGRITY)

    def test_12_donor_audit_local_donor_reads_exact_11_files_when_present(self) -> None:
        if self.donor_audit.verification_mode == "LOCAL_DONOR_O_RDONLY":
            self.assertEqual(self.donor_audit.files_inspected, 11)
            self.assertEqual(self.donor_audit.access_mode, "OS_OPEN_O_RDONLY")
            self.assertLess(self.donor_audit.elapsed_seconds, 0.20)
        else:
            self.assertEqual(self.donor_audit.files_inspected, 0)

    # --- 3. Gate G117 Constants & Resolver Behavior (Tests 13-24) ---

    def test_13_g117_constants_and_uxc_resids(self) -> None:
        self.assertEqual(
            FX3_EXACT_2_RAW_FILE_TYPES_G117,
            (RAW_TYPE_COMPRESSED_G117, RAW_TYPE_UNCOMPRESSED_G117),
        )
        self.assertEqual(RAW_TYPE_FACTORY_DEFAULT_G117, RAW_TYPE_COMPRESSED_G117)
        self.assertEqual(RAW_BIT_DEPTH_FX3_G117, 14)
        self.assertEqual(HEIF_BIT_DEPTH_FX3_G117, 10)
        self.assertEqual(JH_SWITCH_FACTORY_DEFAULT_G117, JH_SWITCH_JPEG_G117)
        self.assertEqual(FILE_FORMAT_FACTORY_DEFAULT_G117, FILE_FORMAT_JPEG_G117)
        self.assertEqual(STILL_QUALITY_FACTORY_DEFAULT_G117, STILL_QUALITY_FINE_G117)
        self.assertEqual(COLOR_SPACE_FACTORY_DEFAULT_G117, COLOR_SPACE_SRGB_G117)
        self.assertEqual(SET_FILE_NAME_DEFAULT_PREFIX_G117, "DSC")
        self.assertEqual(ADOBERGB_DEFAULT_PREFIX_G117, "_DSC")
        self.assertEqual(SET_FILE_NAME_PREFIX_LENGTH_G117, 3)
        self.assertEqual(RAW_FILE_TYPE_UXC_RESID16_G117, 0x6FF2)
        self.assertEqual(DORMANT_LOSSLESS_COMP_UXC_RESID16_G117, 0x6B56)
        self.assertEqual(HLG_STILL_IMAGE_UXC_RESID16_G117, 0x76C8)
        self.assertEqual(COLOR_SPACE_UXC_RESID16_G117, 0x68B7)
        self.assertEqual(COLOR_SPACE_SRGB_UXC_RESID16_G117, 0xE07D)
        self.assertEqual(COLOR_SPACE_ADOBERGB_UXC_RESID16_G117, 0xE07E)
        self.assertEqual(ADOBERGB_DSC_HINT_UXC_RESID16_G117, 0xE895)
        self.assertEqual(SET_FILE_NAME_UXC_RESID16_G117, 0x6993)

    def test_14_g117_menu_paths_match_ilc2210(self) -> None:
        self.assertEqual(
            COLOR_SPACE_MENU_PATH_G117,
            "MENU -> Shooting -> [Image Quality/Rec] -> [Color Space]",
        )
        self.assertIn("JPEG/HEIF Switch", JPEG_HEIF_SWITCH_MENU_PATH_G117)
        self.assertIn("Image Quality Settings", IMAGE_QUALITY_SETTINGS_MENU_PATH_G117)
        self.assertIn("HLG Still Image", HLG_STILL_IMAGE_MENU_PATH_G117)
        self.assertIn("Set File Name", SET_FILE_NAME_MENU_PATH_G117)

    def test_15_g117_default_resolver_is_srgb_dsc00001_compressed_jpeg(self) -> None:
        r = resolve_fx3_raw_heif_hlg_colorspace_state()
        self.assertEqual(r["effective_jpeg_heif_switch"], JH_SWITCH_JPEG_G117)
        self.assertEqual(r["effective_file_format"], FILE_FORMAT_JPEG_G117)
        self.assertEqual(r["effective_raw_file_type"], RAW_TYPE_COMPRESSED_G117)
        self.assertEqual(r["effective_hlg_still_image"], "Off")
        self.assertEqual(r["effective_color_space"], COLOR_SPACE_SRGB_G117)
        self.assertEqual(r["effective_dcf_filename_prefix"], "DSC")
        self.assertEqual(r["example_still_filename"], "DSC00001.JPG")

    def test_16_g117_adobergb_prepends_dcf_leading_underscore_in_jpeg_and_raw_jpeg(self) -> None:
        r_jpg = resolve_fx3_raw_heif_hlg_colorspace_state(
            requested_file_format=FILE_FORMAT_JPEG_G117,
            requested_color_space=COLOR_SPACE_ADOBERGB_G117,
        )
        self.assertEqual(r_jpg["effective_color_space"], COLOR_SPACE_ADOBERGB_G117)
        self.assertEqual(r_jpg["effective_dcf_filename_prefix"], "_DSC")
        self.assertEqual(r_jpg["example_still_filename"], "_DSC0001.JPG")

        r_raw = resolve_fx3_raw_heif_hlg_colorspace_state(
            requested_file_format=FILE_FORMAT_RAW_JPEG_G117,
            requested_color_space=COLOR_SPACE_ADOBERGB_G117,
            requested_file_name_prefix="FX3",
        )
        self.assertEqual(r_raw["effective_dcf_filename_prefix"], "_FX3")
        self.assertEqual(r_raw["example_still_filename"], "_FX30001.ARW")

    def test_17_g117_heif_ignores_srgb_adobergb_when_hlg_off(self) -> None:
        for sw in (JH_SWITCH_HEIF_420_G117, JH_SWITCH_HEIF_422_G117):
            r = resolve_fx3_raw_heif_hlg_colorspace_state(
                requested_jpeg_heif_switch=sw,
                requested_file_format=FILE_FORMAT_HEIF_G117,
                requested_hlg_still_image="Off",
                requested_color_space=COLOR_SPACE_ADOBERGB_G117,
            )
            self.assertTrue(r["heif_ignores_srgb_adobergb"])
            self.assertEqual(r["effective_color_space"], COLOR_SPACE_SRGB_G117)
            self.assertEqual(r["effective_dcf_filename_prefix"], "DSC")
            self.assertEqual(r["example_still_filename"], "DSC00001.HIF")

    def test_18_g117_hlg_still_on_locks_pp_cl_dro_dro_bracket_and_sets_bt2100(self) -> None:
        r = resolve_fx3_raw_heif_hlg_colorspace_state(
            shoot_mode=SHOOT_MODE_M_PHASE283,
            requested_jpeg_heif_switch=JH_SWITCH_HEIF_422_G117,
            requested_file_format=FILE_FORMAT_HEIF_G117,
            requested_hlg_still_image="On",
            requested_color_space=COLOR_SPACE_ADOBERGB_G117,
        )
        self.assertTrue(r["hlg_still_prereq_met"])
        self.assertEqual(r["effective_hlg_still_image"], "On")
        self.assertEqual(r["effective_picture_profile"], "Off")
        self.assertEqual(r["effective_creative_look"], "-")
        self.assertEqual(r["effective_dro"], "Off")
        self.assertFalse(r["dro_bracket_available"])
        self.assertEqual(r["effective_color_space"], COLOR_SPACE_BT2100_BT2020_G117)
        self.assertEqual(
            HLG_STILL_LOCKED_OUT_FUNCTIONS_G117,
            ("Picture Profile", "Creative Look", "D-Range Optimizer", "DRO Bracket"),
        )

    def test_19_g117_hlg_still_prerequisites_enforced(self) -> None:
        r_jpeg = resolve_fx3_raw_heif_hlg_colorspace_state(
            requested_jpeg_heif_switch=JH_SWITCH_JPEG_G117,
            requested_file_format=FILE_FORMAT_JPEG_G117,
            requested_hlg_still_image="On",
        )
        self.assertFalse(r_jpeg["hlg_still_prereq_met"])
        self.assertEqual(r_jpeg["effective_hlg_still_image"], "Off")

        r_raw_heif = resolve_fx3_raw_heif_hlg_colorspace_state(
            requested_jpeg_heif_switch=JH_SWITCH_HEIF_420_G117,
            requested_file_format=FILE_FORMAT_RAW_HEIF_G117,
            requested_hlg_still_image="On",
        )
        self.assertFalse(r_raw_heif["hlg_still_prereq_met"])
        self.assertEqual(r_raw_heif["effective_hlg_still_image"], "Off")

        r_iauto = resolve_fx3_raw_heif_hlg_colorspace_state(
            shoot_mode=SHOOT_MODE_INTELLIGENT_AUTO_PHASE283,
            requested_jpeg_heif_switch=JH_SWITCH_HEIF_420_G117,
            requested_file_format=FILE_FORMAT_HEIF_G117,
            requested_hlg_still_image="On",
        )
        self.assertFalse(r_iauto["hlg_still_prereq_met"])

        r_reg = resolve_fx3_raw_heif_hlg_colorspace_state(
            shoot_mode=SHOOT_MODE_M_PHASE283,
            requested_jpeg_heif_switch=JH_SWITCH_HEIF_420_G117,
            requested_file_format=FILE_FORMAT_HEIF_G117,
            requested_hlg_still_image="On",
            reg_custom_shoot_set_iso_or_dro_bracket=True,
        )
        self.assertFalse(r_reg["hlg_still_prereq_met"])

    def test_20_g117_set_file_name_survives_cam_reset_but_resets_on_initialize(self) -> None:
        r_cam = resolve_fx3_raw_heif_hlg_colorspace_state(
            requested_file_name_prefix="A7S",
            requested_color_space=COLOR_SPACE_ADOBERGB_G117,
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE283,
        )
        self.assertTrue(r_cam["file_name_prefix_survived_cam_reset"])
        self.assertEqual(r_cam["effective_base_file_name_prefix"], "A7S")
        self.assertEqual(r_cam["effective_color_space"], COLOR_SPACE_SRGB_G117)

        r_init = resolve_fx3_raw_heif_hlg_colorspace_state(
            requested_file_name_prefix="A7S",
            reset_action=RESET_ACTION_INITIALIZE_PHASE283,
        )
        self.assertEqual(r_init["effective_base_file_name_prefix"], "DSC")

    def test_21_g117_648_state_matrix_invariants(self) -> None:
        m = compute_raw_heif_hlg_colorspace_matrix()
        self.assertEqual(m["states_checked"], 648)
        self.assertEqual(m["hlg_still_active_states"], 16)
        self.assertEqual(m["hlg_still_bt2100_states"], 16)
        self.assertEqual(m["adobergb_underscore_prefix_states"], 36)
        self.assertEqual(m["heif_ignores_adobergb_states"], 144)
        self.assertEqual(m["file_name_survived_cam_reset_states"], 216)
        self.assertTrue(m["all_invariants_hold"])

    def test_22_g117_guard_passes_valid_pasm_states(self) -> None:
        for sm in PASM_SHOOT_MODES_PHASE283:
            res = verify_raw_heif_colorspace_guard(
                shoot_mode=sm,
                requested_jpeg_heif_switch=JH_SWITCH_HEIF_422_G117,
                requested_file_format=FILE_FORMAT_HEIF_G117,
                requested_hlg_still_image="On",
            )
            self.assertTrue(res.valid, msg=res.errors)
            self.assertEqual(res.status, STATUS_VERIFIED_G117)
            self.assertEqual(res.effective_color_space, COLOR_SPACE_BT2100_BT2020_G117)

    def test_23_g117_guard_blocks_dormant_lossless_raw_and_fx6_still_spoofs(self) -> None:
        r1 = verify_raw_heif_colorspace_guard(
            requested_raw_file_type=RAW_TYPE_DORMANT_LOSSLESS_COMP_G117
        )
        self.assertFalse(r1.valid)
        self.assertEqual(r1.status, STATUS_BLOCKED_G117_FX3_DORMANT_LOSSLESS_RAW_SPOOF_VIOLATION)

        r2 = verify_raw_heif_colorspace_guard(claimed_lossless_comp_exposed=True)
        self.assertFalse(r2.valid)
        self.assertEqual(r2.status, STATUS_BLOCKED_G117_FX3_DORMANT_LOSSLESS_RAW_SPOOF_VIOLATION)

        r3 = verify_raw_heif_colorspace_guard(
            claimed_fx3_raw_file_types=("Compressed", "Uncompressed", "Lossless Comp")
        )
        self.assertFalse(r3.valid)
        self.assertEqual(r3.status, STATUS_BLOCKED_G117_FX3_DORMANT_LOSSLESS_RAW_SPOOF_VIOLATION)

        r4 = verify_raw_heif_colorspace_guard(claimed_fx6_still_pipeline_supported=True)
        self.assertFalse(r4.valid)
        self.assertEqual(r4.status, STATUS_BLOCKED_G117_FX3_DORMANT_LOSSLESS_RAW_SPOOF_VIOLATION)

        r5 = verify_raw_heif_colorspace_guard(claimed_fx6_mechanical_shutter=True)
        self.assertFalse(r5.valid)
        self.assertEqual(r5.status, STATUS_BLOCKED_G117_FX3_DORMANT_LOSSLESS_RAW_SPOOF_VIOLATION)

    def test_24_g117_guard_blocks_hlg_prereq_lockout_and_colorspace_prefix_violations(self) -> None:
        r_hlg_jpeg = verify_raw_heif_colorspace_guard(
            requested_jpeg_heif_switch=JH_SWITCH_JPEG_G117,
            requested_file_format=FILE_FORMAT_JPEG_G117,
            requested_hlg_still_image="On",
        )
        self.assertFalse(r_hlg_jpeg.valid)
        self.assertEqual(r_hlg_jpeg.status, STATUS_BLOCKED_G117_HLG_STILL_PREREQ_OR_LOCKOUT_VIOLATION)

        r_hlg_pp = verify_raw_heif_colorspace_guard(
            claimed_hlg_still_allows_picture_profile=True
        )
        self.assertFalse(r_hlg_pp.valid)
        self.assertEqual(r_hlg_pp.status, STATUS_BLOCKED_G117_HLG_STILL_PREREQ_OR_LOCKOUT_VIOLATION)

        r_hlg_dro_b = verify_raw_heif_colorspace_guard(
            claimed_hlg_still_allows_dro_bracket=True
        )
        self.assertFalse(r_hlg_dro_b.valid)
        self.assertEqual(r_hlg_dro_b.status, STATUS_BLOCKED_G117_HLG_STILL_PREREQ_OR_LOCKOUT_VIOLATION)

        r_lead_us = verify_raw_heif_colorspace_guard(requested_file_name_prefix="_FX")
        self.assertFalse(r_lead_us.valid)
        self.assertEqual(r_lead_us.status, STATUS_BLOCKED_G117_COLORSPACE_ADOBERGB_PREFIX_VIOLATION)

        r_heif_cs = verify_raw_heif_colorspace_guard(
            claimed_heif_honors_color_space_selection=True
        )
        self.assertFalse(r_heif_cs.valid)
        self.assertEqual(r_heif_cs.status, STATUS_BLOCKED_G117_COLORSPACE_ADOBERGB_PREFIX_VIOLATION)

        r_reset_fn = verify_raw_heif_colorspace_guard(
            claimed_camera_reset_resets_file_name_prefix=True
        )
        self.assertFalse(r_reset_fn.valid)
        self.assertEqual(r_reset_fn.status, STATUS_BLOCKED_G117_COLORSPACE_ADOBERGB_PREFIX_VIOLATION)

    # --- 4. Gate G118 Constants & Resolver Behavior (Tests 25-39) ---

    def test_25_g118_constants_and_uxc_resids(self) -> None:
        self.assertEqual(
            FX3_EXACT_2_SHUTTER_TYPES_G118,
            (SHUTTER_TYPE_MECHANICAL_G118, SHUTTER_TYPE_ELECTRONIC_G118),
        )
        self.assertEqual(SHUTTER_TYPE_FACTORY_DEFAULT_G118, SHUTTER_TYPE_MECHANICAL_G118)
        self.assertEqual(SHUTTER_TYPE_INTERVAL_DEFAULT_G118, SHUTTER_TYPE_ELECTRONIC_G118)
        self.assertEqual(E_FRONT_CURTAIN_DEFAULT_G118, "On")
        self.assertEqual(SILENT_MODE_DEFAULT_G118, "Off")
        self.assertEqual(FX3_FLASH_SYNC_CEILING_DENOM_G118, 250)
        self.assertEqual(FX3_FLASH_SYNC_CEILING_LABEL_G118, "1/250 s")
        self.assertEqual(APSC_FLASH_SYNC_SPOOF_DENOM_G118, 320)
        self.assertEqual(len(ELECTRONIC_SHUTTER_5LOCKED_FUNCTIONS_G118), 5)
        self.assertEqual(len(FX3_EXACT_8_DRIVE_MODES_G118), 8)
        self.assertEqual(CONT_SPEED_MAX_FPS_G118[CONT_SPEED_HI_PLUS_G118], 10.0)
        self.assertEqual(CONT_SPEED_MAX_FPS_G118[CONT_SPEED_HI_G118], 8.0)
        self.assertEqual(CONT_SPEED_MAX_FPS_G118[CONT_SPEED_MID_G118], 6.0)
        self.assertEqual(CONT_SPEED_MAX_FPS_G118[CONT_SPEED_LO_G118], 3.0)
        self.assertEqual(SHUTTER_TYPE_UXC_RESID16_G118, 0x7AA9)
        self.assertEqual(E_FRONT_CURTAIN_UXC_RESID16_G118, 0x64C6)
        self.assertEqual(DRIVE_MODE_UXC_RESID16_G118, 0x7228)
        self.assertEqual(CONT_SHOOTING_HI_PLUS_UXC_RESID16_G118, 0x68D1)

    def test_26_g118_menu_paths(self) -> None:
        self.assertIn("[Shutter Type]", SHUTTER_TYPE_MENU_PATH_G118)
        self.assertIn("[e-Front Curtain Shut.]", E_FRONT_CURTAIN_MENU_PATH_G118)
        self.assertIn("[Silent Mode]", SILENT_MODE_MENU_PATH_G118)
        self.assertIn("[Long Exposure NR]", LONG_EXPOSURE_NR_MENU_PATH_G118)
        self.assertIn("[High ISO NR]", HIGH_ISO_NR_MENU_PATH_G118)
        self.assertIn("[Drive Mode]", DRIVE_MODE_MENU_PATH_G118)

    def test_27_g118_silent_mode_forces_electronic_shutter_and_5_lockouts(self) -> None:
        r = resolve_fx3_shutter_type_nr_drive_state(
            requested_shutter_type=SHUTTER_TYPE_MECHANICAL_G118,
            requested_silent_mode="On",
            requested_long_exposure_nr="On",
            requested_e_front_curtain="On",
        )
        self.assertEqual(r["effective_shutter_type"], SHUTTER_TYPE_ELECTRONIC_G118)
        self.assertTrue(r["electronic_shutter_5lock_active"])
        self.assertEqual(r["effective_long_exposure_nr"], "Off")
        self.assertEqual(r["effective_e_front_curtain"], "Unavailable")

    def test_28_g118_e_front_curtain_survives_cam_reset_needs_initialize(self) -> None:
        r_cam = resolve_fx3_shutter_type_nr_drive_state(
            requested_e_front_curtain="Off",
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE283,
        )
        self.assertTrue(r_cam["e_front_curtain_survived_cam_reset"])
        self.assertEqual(r_cam["effective_e_front_curtain"], "Off")

        r_init = resolve_fx3_shutter_type_nr_drive_state(
            requested_e_front_curtain="Off",
            reset_action=RESET_ACTION_INITIALIZE_PHASE283,
        )
        self.assertEqual(r_init["effective_e_front_curtain"], "On")

    def test_29_g118_flash_sync_1_250_ceiling_enforced(self) -> None:
        ok_sync = resolve_fx3_shutter_type_nr_drive_state(
            flash_enabled=True,
            shutter_speed_seconds=FX3_FLASH_SYNC_CEILING_SECONDS_G118,
        )
        self.assertFalse(ok_sync["mechanical_flash_sync_exceeded"])

        bad_sync = resolve_fx3_shutter_type_nr_drive_state(
            flash_enabled=True,
            shutter_speed_seconds=1.0 / 320.0,
        )
        self.assertTrue(bad_sync["mechanical_flash_sync_exceeded"])

    def test_30_g118_long_exp_nr_dark_frame_and_cont_lockouts(self) -> None:
        r_1s = resolve_fx3_shutter_type_nr_drive_state(
            shutter_speed_seconds=LONG_EXP_NR_THRESHOLD_SECONDS_G118,
            requested_long_exposure_nr="On",
            requested_drive_mode=DRIVE_SINGLE_G118,
        )
        self.assertTrue(r_1s["long_exp_nr_dark_frame_active"])
        self.assertEqual(r_1s["long_exp_nr_dark_frame_duration_sec"], 1.0)

        for drv in (DRIVE_CONT_G118, DRIVE_CONT_BRACKET_G118):
            r_blk = resolve_fx3_shutter_type_nr_drive_state(
                shutter_speed_seconds=2.0,
                requested_long_exposure_nr="On",
                requested_drive_mode=drv,
            )
            self.assertEqual(r_blk["effective_long_exposure_nr"], "Off")
            self.assertFalse(r_blk["long_exp_nr_dark_frame_active"])

    def test_31_g118_high_iso_nr_unavailable_in_raw_only_and_iauto_fixed_normal(self) -> None:
        r_raw = resolve_fx3_shutter_type_nr_drive_state(
            file_format=FILE_FORMAT_RAW_G117,
            requested_high_iso_nr=HIGH_ISO_NR_OFF_G118,
        )
        self.assertEqual(r_raw["effective_high_iso_nr"], "Unavailable")

        r_iauto = resolve_fx3_shutter_type_nr_drive_state(
            shoot_mode=SHOOT_MODE_INTELLIGENT_AUTO_PHASE283,
            file_format=FILE_FORMAT_JPEG_G117,
            requested_high_iso_nr=HIGH_ISO_NR_OFF_G118,
        )
        self.assertEqual(r_iauto["effective_high_iso_nr"], HIGH_ISO_NR_NORMAL_G118)

    def test_32_g118_drive_hi_plus_10fps_uncompressed_flash_and_gt_f11_af_lock(self) -> None:
        r_fast = resolve_fx3_shutter_type_nr_drive_state(
            requested_drive_mode=DRIVE_CONT_G118,
            cont_shooting_speed=CONT_SPEED_HI_PLUS_G118,
            file_format=FILE_FORMAT_RAW_G117,
            raw_file_type=RAW_TYPE_COMPRESSED_G117,
            flash_enabled=False,
            aperture_f_number=2.8,
        )
        self.assertTrue(r_fast["hi_plus_sustains_10fps"])
        self.assertFalse(r_fast["monitor_live_view_enabled_in_drive"])
        self.assertFalse(r_fast["af_locked_to_first_frame_gt_f11"])

        r_uncomp = resolve_fx3_shutter_type_nr_drive_state(
            requested_drive_mode=DRIVE_CONT_G118,
            cont_shooting_speed=CONT_SPEED_HI_PLUS_G118,
            file_format=FILE_FORMAT_RAW_G117,
            raw_file_type=RAW_TYPE_UNCOMPRESSED_G117,
        )
        self.assertFalse(r_uncomp["hi_plus_sustains_10fps"])

        r_flash = resolve_fx3_shutter_type_nr_drive_state(
            requested_drive_mode=DRIVE_CONT_G118,
            cont_shooting_speed=CONT_SPEED_HI_PLUS_G118,
            flash_enabled=True,
        )
        self.assertFalse(r_flash["hi_plus_sustains_10fps"])

        r_f16 = resolve_fx3_shutter_type_nr_drive_state(
            requested_drive_mode=DRIVE_CONT_G118,
            cont_shooting_speed=CONT_SPEED_MID_G118,
            aperture_f_number=16.0,
        )
        self.assertTrue(r_f16["af_locked_to_first_frame_gt_f11"])

    def test_33_g118_384_state_matrix_invariants(self) -> None:
        m = compute_shutter_type_nr_drive_matrix()
        self.assertEqual(m["states_checked"], 384)
        self.assertEqual(m["electronic_5lock_states"], 288)
        self.assertEqual(m["long_exp_nr_dark_frame_states"], 24)
        self.assertEqual(m["high_iso_nr_unavailable_states"], 128)
        self.assertEqual(m["hi_plus_10fps_sustained_states"], 64)
        self.assertEqual(m["af_locked_gt_f11_states"], 48)
        self.assertTrue(m["all_invariants_hold"])

    def test_34_g118_guard_blocks_auto_shutter_spoof_and_efront_reset_spoof(self) -> None:
        r1 = verify_shutter_type_nr_drive_guard(
            requested_shutter_type=SHUTTER_TYPE_SIBLING_AUTO_TRAP_G118
        )
        self.assertFalse(r1.valid)
        self.assertEqual(r1.status, STATUS_BLOCKED_G118_FX3_SHUTTER_TYPE_AUTO_SPOOF_VIOLATION)

        r2 = verify_shutter_type_nr_drive_guard(claimed_shutter_type_auto_exposed=True)
        self.assertFalse(r2.valid)
        self.assertEqual(r2.status, STATUS_BLOCKED_G118_FX3_SHUTTER_TYPE_AUTO_SPOOF_VIOLATION)

        r3 = verify_shutter_type_nr_drive_guard(
            claimed_fx3_shutter_types=("Auto", "Mechanical Shutter", "Electronic Shutter")
        )
        self.assertFalse(r3.valid)
        self.assertEqual(r3.status, STATUS_BLOCKED_G118_FX3_SHUTTER_TYPE_AUTO_SPOOF_VIOLATION)

        r4 = verify_shutter_type_nr_drive_guard(
            claimed_camera_reset_resets_e_front_curtain=True
        )
        self.assertFalse(r4.valid)
        self.assertEqual(r4.status, STATUS_BLOCKED_G118_FX3_SHUTTER_TYPE_AUTO_SPOOF_VIOLATION)

    def test_35_g118_guard_blocks_all_5_electronic_lockouts_and_1_320_sync_spoof(self) -> None:
        for flag_name in (
            "claimed_electronic_shutter_allows_flash",
            "claimed_electronic_shutter_allows_long_exp_nr",
            "claimed_electronic_shutter_allows_e_front_curtain",
            "claimed_electronic_shutter_allows_bulb",
            "claimed_electronic_shutter_allows_anti_flicker",
            "claimed_silent_mode_allows_mechanical_shutter",
        ):
            r = verify_shutter_type_nr_drive_guard(**{flag_name: True})
            self.assertFalse(r.valid, msg=flag_name)
            self.assertEqual(
                r.status,
                STATUS_BLOCKED_G118_ELECTRONIC_SHUTTER_5LOCK_OR_SYNC_VIOLATION,
            )

        r_sync = verify_shutter_type_nr_drive_guard(
            claimed_flash_sync_ceiling_denom=APSC_FLASH_SYNC_SPOOF_DENOM_G118
        )
        self.assertFalse(r_sync.valid)
        self.assertEqual(
            r_sync.status,
            STATUS_BLOCKED_G118_ELECTRONIC_SHUTTER_5LOCK_OR_SYNC_VIOLATION,
        )

        r_fast_flash = verify_shutter_type_nr_drive_guard(
            flash_enabled=True,
            shutter_speed_seconds=1.0 / 320.0,
        )
        self.assertFalse(r_fast_flash.valid)
        self.assertEqual(
            r_fast_flash.status,
            STATUS_BLOCKED_G118_ELECTRONIC_SHUTTER_5LOCK_OR_SYNC_VIOLATION,
        )

        r_elec_bulb = verify_shutter_type_nr_drive_guard(
            requested_shutter_type=SHUTTER_TYPE_ELECTRONIC_G118,
            bulb_mode=True,
        )
        self.assertFalse(r_elec_bulb.valid)
        self.assertEqual(
            r_elec_bulb.status,
            STATUS_BLOCKED_G118_ELECTRONIC_SHUTTER_5LOCK_OR_SYNC_VIOLATION,
        )

    def test_36_g118_guard_blocks_nr_and_drive_boundary_violations(self) -> None:
        for flag_name in (
            "claimed_long_exp_nr_active_in_cont_shooting",
            "claimed_long_exp_nr_active_in_cont_bracket",
            "claimed_high_iso_nr_available_in_raw_only",
            "claimed_high_iso_nr_alters_arw_raw",
            "claimed_hi_plus_10fps_sustained_with_uncompressed_raw",
            "claimed_hi_plus_10fps_sustained_with_flash",
            "claimed_af_unlocked_above_f11_in_hi_plus",
            "claimed_dro_bracket_available_in_hlg_still",
        ):
            r = verify_shutter_type_nr_drive_guard(**{flag_name: True})
            self.assertFalse(r.valid, msg=flag_name)
            self.assertEqual(
                r.status,
                STATUS_BLOCKED_G118_NR_OR_DRIVE_CONT_BOUNDARY_VIOLATION,
            )

        r_dro_hlg = verify_shutter_type_nr_drive_guard(
            requested_drive_mode=DRIVE_DRO_BRACKET_G118,
            hlg_still_image="On",
        )
        self.assertFalse(r_dro_hlg.valid)
        self.assertEqual(
            r_dro_hlg.status,
            STATUS_BLOCKED_G118_NR_OR_DRIVE_CONT_BOUNDARY_VIOLATION,
        )

    def test_37_g117_and_g118_telemetry_invalid_for_wrong_body_or_bad_enums(self) -> None:
        r117 = verify_raw_heif_colorspace_guard(body_model_name="ILME-FX6")
        self.assertFalse(r117.valid)
        self.assertEqual(r117.status, STATUS_BLOCKED_G117_TELEMETRY_INVALID)

        r117_bad = verify_raw_heif_colorspace_guard(requested_color_space="ProPhotoRGB")
        self.assertFalse(r117_bad.valid)
        self.assertEqual(r117_bad.status, STATUS_BLOCKED_G117_TELEMETRY_INVALID)

        r118 = verify_shutter_type_nr_drive_guard(body_model_id=0x12345678)
        self.assertFalse(r118.valid)
        self.assertEqual(r118.status, STATUS_BLOCKED_G118_TELEMETRY_INVALID)

        r118_bad = verify_shutter_type_nr_drive_guard(shutter_speed_seconds=-0.5)
        self.assertFalse(r118_bad.valid)
        self.assertEqual(r118_bad.status, STATUS_BLOCKED_G118_TELEMETRY_INVALID)

    def test_38_evaluate_g117_and_g118_wrappers_return_gate_verdicts(self) -> None:
        v117, r117 = evaluate_g117_raw_heif_colorspace_guard(donor_audit=self.clean_audit)
        self.assertTrue(v117.passed)
        self.assertEqual(v117.gate_id, G117_GATE_ID)
        self.assertEqual(v117.status, STATUS_VERIFIED_G117)
        self.assertFalse(r117.persistent_emmc_writes_authorized)
        self.assertEqual(r117.raw_firmware_bytes_leaked, 0)

        v118, r118 = evaluate_g118_shutter_type_nr_drive_guard(donor_audit=self.clean_audit)
        self.assertTrue(v118.passed)
        self.assertEqual(v118.gate_id, G118_GATE_ID)
        self.assertEqual(v118.status, STATUS_VERIFIED_G118)
        self.assertFalse(r118.persistent_emmc_writes_authorized)
        self.assertEqual(r118.raw_firmware_bytes_leaked, 0)

    def test_39_evaluate_g117_g118_block_persistent_emmc_writes(self) -> None:
        v117, r117 = evaluate_g117_raw_heif_colorspace_guard(
            donor_audit=self.clean_audit,
            request_persistent_emmc_writes=True,
        )
        self.assertFalse(v117.passed)
        self.assertEqual(r117.status, "BLOCKED_BY_PERSISTENT_EMMC_WRITE_REDLINE")

        v118, r118 = evaluate_g118_shutter_type_nr_drive_guard(
            donor_audit=self.clean_audit,
            request_persistent_emmc_writes=True,
        )
        self.assertFalse(v118.passed)
        self.assertEqual(r118.status, "BLOCKED_BY_PERSISTENT_EMMC_WRITE_REDLINE")

    # --- 5. Unified 118-Gate Master Preflight (Tests 40-55) ---

    def test_40_master_118_offline_clean_room_reaches_115_of_118(self) -> None:
        rep = evaluate_118gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=False,
            master_116_override=self.clean_offline_116,
        )
        self.assertIsInstance(rep, Master118GateReport)
        self.assertEqual(rep.status, "VERIFIED_115_OF_118_AWAITING_PHYSICAL_TIER0")
        self.assertEqual(rep.summary["total_gates"], 118)
        self.assertEqual(rep.summary["verified_gates"], 115)
        self.assertEqual(rep.summary["blocked_or_pending_gates"], 3)
        self.assertTrue(rep.offline_115_gates_verified)
        self.assertFalse(rep.all_118_gates_verified)
        self.assertTrue(rep.g117_to_g118_all_passed)
        self.assertTrue(rep.g13_to_g118_all_passed)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.hardware_live_attachment_authorized)
        self.assertEqual(len(rep.gates), 118)

    def test_41_master_118_dry_run_clean_room_reaches_118_of_118(self) -> None:
        rep = evaluate_118gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            master_116_override=self.clean_dryrun_116,
        )
        self.assertEqual(rep.status, "VERIFIED_ALL_118_GATES_DRY_RUN_SIMULATED_BACKUP")
        self.assertEqual(rep.summary["verified_gates"], 118)
        self.assertEqual(rep.summary["blocked_or_pending_gates"], 0)
        self.assertTrue(rep.all_118_gates_verified)
        self.assertTrue(rep.dry_run_rehearsal_only)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertEqual(rep.usb_packets_transmitted, 0)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_42_master_118_simulate_bench_dry_run_alias(self) -> None:
        rep = evaluate_118gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            simulate_bench_dry_run=True,
            master_116_override=self.clean_dryrun_116,
        )
        self.assertTrue(rep.all_118_gates_verified)
        self.assertEqual(rep.status, "VERIFIED_ALL_118_GATES_DRY_RUN_SIMULATED_BACKUP")

    def test_43_master_118_blocks_when_g117_fails(self) -> None:
        rep = evaluate_118gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            raw_heif_colorspace_kwargs={"requested_raw_file_type": "Lossless Comp"},
            master_116_override=self.clean_dryrun_116,
        )
        self.assertEqual(rep.status, STATUS_BLOCKED_G117_FX3_DORMANT_LOSSLESS_RAW_SPOOF_VIOLATION)
        self.assertFalse(rep.g117_to_g118_all_passed)
        self.assertFalse(rep.all_118_gates_verified)
        self.assertFalse(rep.h0_h1_trial_entry_allowed)
        self.assertEqual(rep.summary["verified_gates"], 117)

    def test_44_master_118_blocks_when_g118_fails(self) -> None:
        rep = evaluate_118gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            shutter_nr_drive_kwargs={"requested_shutter_type": "Auto"},
            master_116_override=self.clean_dryrun_116,
        )
        self.assertEqual(rep.status, STATUS_BLOCKED_G118_FX3_SHUTTER_TYPE_AUTO_SPOOF_VIOLATION)
        self.assertFalse(rep.g117_to_g118_all_passed)
        self.assertFalse(rep.all_118_gates_verified)
        self.assertEqual(rep.summary["verified_gates"], 117)

    def test_45_master_118_blocks_on_persistent_emmc_write_request(self) -> None:
        rep = evaluate_118gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            request_persistent_emmc_writes=True,
            master_116_override=self.clean_dryrun_116,
        )
        self.assertEqual(rep.status, "BLOCKED_BY_PERSISTENT_EMMC_WRITE_REDLINE")
        self.assertFalse(rep.all_118_gates_verified)
        self.assertFalse(rep.offline_115_gates_verified)
        self.assertFalse(rep.h0_h1_trial_entry_allowed)

    def test_46_master_118_gates_end_with_g117_and_g118_in_exact_order(self) -> None:
        rep = evaluate_118gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=False,
            master_116_override=self.clean_offline_116,
        )
        self.assertEqual(rep.gates[-2]["gate_id"], G117_GATE_ID)
        self.assertEqual(rep.gates[-1]["gate_id"], G118_GATE_ID)
        self.assertEqual(rep.gates[-3]["gate_id"], "G116_white_balance_cine_ei_custom_setup_and_metering_mode_guard")

    def test_47_master_118_to_dict_is_json_serializable(self) -> None:
        rep = evaluate_118gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=False,
            master_116_override=self.clean_offline_116,
        )
        d = rep.to_dict()
        dumped = json.dumps(d)
        loaded = json.loads(dumped)
        self.assertEqual(loaded["summary"]["total_gates"], 118)
        self.assertEqual(loaded["summary"]["g117_to_g118_verified"], 2)

    def test_48_master_118_propagates_upstream_g116_failure(self) -> None:
        broken_116 = dataclasses.replace(
            self.clean_dryrun_116,
            g13_to_g116_all_passed=False,
            status="BLOCKED_G116_CINE_EI_AWB_VIOLATION",
        )
        rep = evaluate_118gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            master_116_override=broken_116,
        )
        self.assertEqual(rep.status, "BLOCKED_G116_CINE_EI_AWB_VIOLATION")
        self.assertFalse(rep.g13_to_g118_all_passed)
        self.assertFalse(rep.all_118_gates_verified)

    def test_49_master_118_all_allowed_enums_populated(self) -> None:
        self.assertEqual(len(ALLOWED_JH_SWITCH_MODES_G117), 3)
        self.assertEqual(len(ALLOWED_FILE_FORMATS_G117), 5)
        self.assertEqual(len(ALLOWED_STILL_QUALITIES_G117), 3)
        self.assertEqual(len(ALLOWED_STILL_SIZES_G117), 3)
        self.assertEqual(len(ALLOWED_COLOR_SPACES_G117), 2)
        self.assertEqual(len(ALLOWED_HIGH_ISO_NR_MODES_G118), 3)
        self.assertEqual(len(ALLOWED_CONT_SPEEDS_G118), 4)
        self.assertEqual(len(ALLOWED_RESET_ACTIONS_PHASE283), 4)
        self.assertEqual(len(ALLOWED_SHOOT_MODES_PHASE283), 8)

    def test_50_g117_all_reset_actions_handled(self) -> None:
        for r_act in ALLOWED_RESET_ACTIONS_PHASE283:
            res = verify_raw_heif_colorspace_guard(reset_action=r_act)
            self.assertTrue(res.valid, msg=r_act)
            self.assertEqual(res.reset_action, r_act)

    def test_51_g118_all_reset_actions_handled(self) -> None:
        for r_act in ALLOWED_RESET_ACTIONS_PHASE283:
            res = verify_shutter_type_nr_drive_guard(reset_action=r_act)
            self.assertTrue(res.valid, msg=r_act)
            self.assertEqual(res.reset_action, r_act)

    def test_52_g118_all_8_drive_modes_and_4_cont_speeds_valid(self) -> None:
        for drv in FX3_EXACT_8_DRIVE_MODES_G118:
            res = verify_shutter_type_nr_drive_guard(requested_drive_mode=drv)
            self.assertTrue(res.valid, msg=drv)
        for spd in ALLOWED_CONT_SPEEDS_G118:
            res = verify_shutter_type_nr_drive_guard(
                requested_drive_mode=DRIVE_CONT_G118,
                cont_shooting_speed=spd,
            )
            self.assertTrue(res.valid, msg=spd)
            self.assertEqual(res.cont_shooting_nominal_max_fps, CONT_SPEED_MAX_FPS_G118[spd])

    def test_53_g117_file_format_auto_alignment_jpeg_vs_heif(self) -> None:
        r1 = resolve_fx3_raw_heif_hlg_colorspace_state(
            requested_jpeg_heif_switch=JH_SWITCH_JPEG_G117,
            requested_file_format=FILE_FORMAT_RAW_HEIF_G117,
        )
        self.assertEqual(r1["effective_file_format"], FILE_FORMAT_RAW_JPEG_G117)

        r2 = resolve_fx3_raw_heif_hlg_colorspace_state(
            requested_jpeg_heif_switch=JH_SWITCH_HEIF_420_G117,
            requested_file_format=FILE_FORMAT_JPEG_G117,
        )
        self.assertEqual(r2["effective_file_format"], FILE_FORMAT_HEIF_G117)

    def test_54_g118_mechanical_anti_flicker_and_bulb_allowed_in_mechanical(self) -> None:
        res = verify_shutter_type_nr_drive_guard(
            requested_shutter_type=SHUTTER_TYPE_MECHANICAL_G118,
            requested_silent_mode="Off",
            bulb_mode=True,
            anti_flicker_shoot=True,
            shutter_speed_seconds=2.0,
        )
        self.assertTrue(res.valid, msg=res.errors)
        self.assertTrue(res.long_exp_nr_dark_frame_active)

    def test_55_g118_silent_mode_on_blocks_flash_bulb_and_antiflicker(self) -> None:
        for kw in (
            {"flash_enabled": True},
            {"bulb_mode": True},
            {"anti_flicker_shoot": True},
        ):
            res = verify_shutter_type_nr_drive_guard(requested_silent_mode="On", **kw)
            self.assertFalse(res.valid)
            self.assertEqual(
                res.status,
                STATUS_BLOCKED_G118_ELECTRONIC_SHUTTER_5LOCK_OR_SYNC_VIOLATION,
            )

    # --- 6. CLI & Cross-Platform CI Portability Tests (Tests 56-78) ---

    def test_56_cli_verify_raw_heif_colorspace_guard_text_and_json(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cli_main(["verify-raw-heif-colorspace-guard", "--force-clean-room"])
        self.assertEqual(rc, 0)
        self.assertIn("gate=G117_", buf.getvalue())
        self.assertIn("raw=Compressed", buf.getvalue())
        self.assertIn("fx6_still=False", buf.getvalue())

        jbuf = io.StringIO()
        with contextlib.redirect_stdout(jbuf):
            rc_j = cli_main(
                ["verify-g117-raw-heif-colorspace", "--force-clean-room", "--json"]
            )
        self.assertEqual(rc_j, 0)
        data = json.loads(jbuf.getvalue())
        self.assertTrue(data["valid"])
        self.assertEqual(data["status"], STATUS_VERIFIED_G117)

    def test_57_cli_verify_shutter_type_nr_drive_guard_text_and_json(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cli_main(["verify-shutter-type-nr-drive-guard", "--force-clean-room"])
        self.assertEqual(rc, 0)
        self.assertIn("gate=G118_", buf.getvalue())
        self.assertIn("shutter=Mechanical Shutter", buf.getvalue())
        self.assertIn("no_auto=True", buf.getvalue())
        self.assertIn("sync=1/250 s", buf.getvalue())

        jbuf = io.StringIO()
        with contextlib.redirect_stdout(jbuf):
            rc_j = cli_main(
                ["verify-g118-shutter-type-nr-drive", "--force-clean-room", "--json"]
            )
        self.assertEqual(rc_j, 0)
        data = json.loads(jbuf.getvalue())
        self.assertTrue(data["valid"])
        self.assertEqual(data["status"], STATUS_VERIFIED_G118)

    def test_58_cli_verify_118_gates_offline_text_and_json(self) -> None:
        offline_118 = evaluate_118gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=False,
            master_116_override=self.clean_offline_116,
        )
        with mock.patch(
            "fx3_safety.__main__.evaluate_118gate_preflight",
            return_value=offline_118,
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = cli_main(["verify-118-gates", "--force-clean-room"])
            self.assertEqual(rc, 0)
            self.assertIn("verified=115/118", buf.getvalue())
            self.assertIn("overall_ready_for_hardware_attach=False", buf.getvalue())

            jbuf = io.StringIO()
            with contextlib.redirect_stdout(jbuf):
                rc_j = cli_main(["verify-118-gates", "--force-clean-room", "--json"])
            self.assertEqual(rc_j, 0)
            parsed = json.loads(jbuf.getvalue())
            self.assertEqual(parsed["summary"]["verified_gates"], 115)
            self.assertTrue(parsed["offline_115_gates_verified"])

    def test_59_cli_verify_118_gates_dry_run_text_and_json(self) -> None:
        dryrun_118 = evaluate_118gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            master_116_override=self.clean_dryrun_116,
        )
        with mock.patch(
            "fx3_safety.__main__.evaluate_118gate_preflight",
            return_value=dryrun_118,
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = cli_main(
                    ["verify-118-gates", "--force-clean-room", "--simulate-bench-dry-run"]
                )
            self.assertEqual(rc, 0)
            self.assertIn("verified=118/118", buf.getvalue())

            jbuf = io.StringIO()
            with contextlib.redirect_stdout(jbuf):
                rc_j = cli_main(
                    [
                        "verify-118-gates",
                        "--force-clean-room",
                        "--simulate-bench-dry-run",
                        "--json",
                    ]
                )
            self.assertEqual(rc_j, 0)
            parsed = json.loads(jbuf.getvalue())
            self.assertTrue(parsed["all_118_gates_verified"])
            self.assertEqual(parsed["summary"]["verified_gates"], 118)

    def test_60_standalone_module_main_offline_and_dry_run(self) -> None:
        offline_118 = evaluate_118gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=False,
            master_116_override=self.clean_offline_116,
        )
        dryrun_118 = evaluate_118gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            master_116_override=self.clean_dryrun_116,
        )
        with mock.patch(
            "fx3_safety.realhw_raw_heif_colorspace_shuttertype_nr_drive_and_118gate_guard.evaluate_118gate_preflight",
            return_value=offline_118,
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = module_main(["--force-clean-room"])
            self.assertEqual(rc, 0)
            self.assertIn("verified=115/118", buf.getvalue())

        with mock.patch(
            "fx3_safety.realhw_raw_heif_colorspace_shuttertype_nr_drive_and_118gate_guard.evaluate_118gate_preflight",
            return_value=dryrun_118,
        ):
            jbuf = io.StringIO()
            with contextlib.redirect_stdout(jbuf):
                rc_j = module_main(
                    ["--force-clean-room", "--simulate-bench-dry-run", "--json"]
                )
            self.assertEqual(rc_j, 0)
            self.assertTrue(json.loads(jbuf.getvalue())["all_118_gates_verified"])

    def test_61_subprocess_cli_verify_g117_g118_uses_sys_executable(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONPATH"] = str(DEFAULT_REPO_ROOT / "outputs" / "fx3-safety")
        for cmd, expected_status in (
            ("verify-raw-heif-colorspace-guard", STATUS_VERIFIED_G117),
            ("verify-shutter-type-nr-drive-guard", STATUS_VERIFIED_G118),
        ):
            proc = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    "-m",
                    "fx3_safety",
                    cmd,
                    "--force-clean-room",
                    "--json",
                ],
                cwd=str(DEFAULT_REPO_ROOT),
                env=env,
                capture_output=True,
                text=True,
                timeout=_subprocess_timeout_seconds(),
                check=False,
            )
            self.assertEqual(proc.returncode, 0, msg=proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertTrue(payload["valid"])
            self.assertEqual(payload["status"], expected_status)

    def test_62_subprocess_cli_verify_118_gates_uses_sys_executable(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONPATH"] = str(DEFAULT_REPO_ROOT / "outputs" / "fx3-safety")
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "fx3_safety",
                "verify-118-gates",
                "--force-clean-room",
                "--simulate-bench-dry-run",
                "--json",
            ],
            cwd=str(DEFAULT_REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=_subprocess_timeout_seconds(),
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertTrue(payload["all_118_gates_verified"])
        self.assertEqual(payload["summary"]["verified_gates"], 118)
        self.assertEqual(payload["raw_firmware_bytes_leaked"], 0)

    def test_63_fx3_clean_room_test_and_force_clean_room_env_in_master_118(self) -> None:
        for env_key in (ENV_CLEAN_ROOM_TEST_PHASE283, "FX3_FX6_FORCE_CLEAN_ROOM"):
            with mock.patch.dict(os.environ, {env_key: "1"}):
                self.assertTrue(_is_forced_clean_room())
                rep = evaluate_118gate_preflight(
                    master_116_override=self.clean_offline_116,
                )
                self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
                self.assertTrue(rep.clean_room_forced)

    def test_64_argparse_help_and_upstream_verify_116_gates_parity(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONPATH"] = str(DEFAULT_REPO_ROOT / "outputs" / "fx3-safety")
        for subcmd in (
            "verify-raw-heif-colorspace-guard",
            "verify-shutter-type-nr-drive-guard",
            "verify-118-gates",
        ):
            proc = subprocess.run(
                [sys.executable, "-B", "-m", "fx3_safety", subcmd, "--help"],
                cwd=str(DEFAULT_REPO_ROOT),
                env=env,
                capture_output=True,
                text=True,
                timeout=_subprocess_timeout_seconds(),
                check=False,
            )
            self.assertEqual(proc.returncode, 0, msg=proc.stderr)

        with mock.patch(
            "fx3_safety.__main__.evaluate_116gate_preflight",
            return_value=self.clean_offline_116,
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = cli_main(["verify-116-gates", "--force-clean-room"])
        self.assertEqual(rc, 0)
        self.assertIn("verified=113/116", buf.getvalue())

    def test_65_standalone_script_help_exits_zero_python314_percent_safe(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONPATH"] = str(DEFAULT_REPO_ROOT / "outputs" / "fx3-safety")
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "fx3_safety.realhw_raw_heif_colorspace_shuttertype_nr_drive_and_118gate_guard",
                "--help",
            ],
            cwd=str(DEFAULT_REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=_subprocess_timeout_seconds(),
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        self.assertIn("phase 283", proc.stdout.lower())
        self.assertIn("118-gate", proc.stdout.lower())

    def test_66_g117_hlg_still_on_in_s_mode_and_a_mode_with_heif_420(self) -> None:
        for sm in (SHOOT_MODE_P_PHASE283, SHOOT_MODE_A_PHASE283, SHOOT_MODE_S_PHASE283):
            res = verify_raw_heif_colorspace_guard(
                shoot_mode=sm,
                requested_jpeg_heif_switch=JH_SWITCH_HEIF_420_G117,
                requested_file_format=FILE_FORMAT_HEIF_G117,
                requested_hlg_still_image="On",
            )
            self.assertTrue(res.valid, msg=res.errors)
            self.assertEqual(res.effective_hlg_still_image, "On")
            self.assertEqual(res.effective_color_space, COLOR_SPACE_BT2100_BT2020_G117)

    def test_67_g117_hlg_still_blocked_when_reg_custom_shoot_overrides(self) -> None:
        res = verify_raw_heif_colorspace_guard(
            shoot_mode=SHOOT_MODE_M_PHASE283,
            requested_jpeg_heif_switch=JH_SWITCH_HEIF_420_G117,
            requested_file_format=FILE_FORMAT_HEIF_G117,
            requested_hlg_still_image="On",
            reg_custom_shoot_set_iso_or_dro_bracket=True,
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_G117_HLG_STILL_PREREQ_OR_LOCKOUT_VIOLATION)

    def test_68_g117_custom_prefix_with_middle_or_trailing_underscore_allowed(self) -> None:
        res = verify_raw_heif_colorspace_guard(
            requested_file_name_prefix="A_1",
            requested_color_space=COLOR_SPACE_SRGB_G117,
        )
        self.assertTrue(res.valid, msg=res.errors)
        self.assertEqual(res.effective_dcf_filename_prefix, "A_1")
        self.assertEqual(res.example_still_filename, "A_100001.JPG")

    def test_69_g117_invalid_prefix_length_or_chars_rejected(self) -> None:
        for bad in ("AB", "ABCD", "ab1", "A-1"):
            res = verify_raw_heif_colorspace_guard(requested_file_name_prefix=bad)
            self.assertFalse(res.valid, msg=bad)
            self.assertEqual(res.status, STATUS_BLOCKED_G117_COLORSPACE_ADOBERGB_PREFIX_VIOLATION)

    def test_70_g117_heif_ignores_adobergb_prefix_spoof_blocked(self) -> None:
        res = verify_raw_heif_colorspace_guard(
            requested_jpeg_heif_switch=JH_SWITCH_HEIF_422_G117,
            requested_file_format=FILE_FORMAT_HEIF_G117,
            requested_color_space=COLOR_SPACE_ADOBERGB_G117,
            claimed_heif_uses_adobergb_prefix=True,
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_G117_COLORSPACE_ADOBERGB_PREFIX_VIOLATION)

    def test_71_g118_cont_lo_does_not_lock_af_above_f11(self) -> None:
        r = resolve_fx3_shutter_type_nr_drive_state(
            requested_drive_mode=DRIVE_CONT_G118,
            cont_shooting_speed=CONT_SPEED_LO_G118,
            aperture_f_number=16.0,
        )
        self.assertFalse(r["af_locked_to_first_frame_gt_f11"])
        self.assertTrue(r["monitor_live_view_enabled_in_drive"])

    def test_72_g118_cont_hi_hi_plus_mid_lock_af_only_strictly_above_f11(self) -> None:
        r_eq = resolve_fx3_shutter_type_nr_drive_state(
            requested_drive_mode=DRIVE_CONT_G118,
            cont_shooting_speed=CONT_SPEED_HI_PLUS_G118,
            aperture_f_number=11.0,
        )
        self.assertFalse(r_eq["af_locked_to_first_frame_gt_f11"])

        for spd in CONT_AF_FIRST_FRAME_LOCK_SPEEDS_G118:
            r_gt = resolve_fx3_shutter_type_nr_drive_state(
                requested_drive_mode=DRIVE_CONT_G118,
                cont_shooting_speed=spd,
                aperture_f_number=11.1,
            )
            self.assertTrue(r_gt["af_locked_to_first_frame_gt_f11"], msg=spd)

    def test_73_g118_all_bracket_modes_except_dro_allowed_under_hlg_still(self) -> None:
        for drv in (
            DRIVE_SELF_TIMER_SINGLE_G118,
            DRIVE_SELF_TIMER_CONT_G118,
            DRIVE_CONT_BRACKET_G118,
            DRIVE_SINGLE_BRACKET_G118,
            DRIVE_WB_BRACKET_G118,
        ):
            res = verify_shutter_type_nr_drive_guard(
                requested_drive_mode=drv,
                hlg_still_image="On",
            )
            self.assertTrue(res.valid, msg=drv)

    def test_74_g118_raw_only_uncompressed_no_flash_drops_below_10fps(self) -> None:
        res = verify_shutter_type_nr_drive_guard(
            requested_drive_mode=DRIVE_CONT_G118,
            cont_shooting_speed=CONT_SPEED_HI_PLUS_G118,
            file_format=FILE_FORMAT_RAW_G117,
            raw_file_type=RAW_TYPE_UNCOMPRESSED_G117,
        )
        self.assertTrue(res.valid)
        self.assertFalse(res.hi_plus_sustains_10fps)
        self.assertEqual(res.effective_high_iso_nr, "Unavailable")

    def test_75_g117_raw_bit_depth_12bit_spoof_rejected(self) -> None:
        res = verify_raw_heif_colorspace_guard(claimed_fx3_raw_bit_depth=12)
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_G117_FX3_DORMANT_LOSSLESS_RAW_SPOOF_VIOLATION)

    def test_76_g117_hlg_color_space_spoof_rejected(self) -> None:
        res = verify_raw_heif_colorspace_guard(
            claimed_hlg_still_color_space="sRGB",
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_G117_HLG_STILL_PREREQ_OR_LOCKOUT_VIOLATION)

    def test_77_master_118_default_clean_room_returns_status_and_summary_keys(self) -> None:
        rep = evaluate_118gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=False,
            master_116_override=self.clean_offline_116,
        )
        for key in (
            "total_gates",
            "verified_gates",
            "g01_to_g12_verified",
            "g13_to_g116_verified",
            "g117_to_g118_verified",
            "g13_to_g118_all_passed",
            "g117_to_g118_all_passed",
            "offline_115_gates_verified",
            "all_118_gates_verified",
            "overall_ready_for_hardware_attach",
            "hardware_live_attachment_authorized",
            "raw_firmware_bytes_leaked",
        ):
            self.assertIn(key, rep.summary)

    def test_78_cli_invalid_g117_g118_result_returns_nonzero(self) -> None:
        bad_verdict, bad_res = evaluate_g117_raw_heif_colorspace_guard(
            donor_audit=self.clean_audit,
            raw_heif_colorspace_kwargs={"requested_raw_file_type": "Lossless Comp"},
        )
        with mock.patch(
            "fx3_safety.__main__.evaluate_g117_raw_heif_colorspace_guard",
            return_value=(bad_verdict, bad_res),
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = cli_main(["verify-raw-heif-colorspace-guard", "--force-clean-room"])
            self.assertEqual(rc, 1)


if __name__ == "__main__":
    unittest.main()
