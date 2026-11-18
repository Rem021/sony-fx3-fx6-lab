"""Phase 286 (Task H330, 120/120 Safety Gates Milestone!, Wave-50) Dual-Mode Unit
Tests (80 tests, < 5.0s runtime) for
`fx3_safety.realhw_focus_area_zoom_lever_iso_minss_flash_and_120gate_guard`:

- Gate `G119` (`GATE_G119_FOCUS_AREA_14OPT_AF_REG_XLRH1_NO_ZOOM_LEVER_AND_ZOOM_SPEED_GUARD`):
  - Complete `14`-option `[Focus Area]` hierarchy (`BKID_APP_setting_autofocus_area_contrast_detect_af`,
    `_f.uxc` `0xe0ad`): `7` shared Still+Movie areas (`Wide` default, `Zone`, `Center Fix`,
    `Spot: S`, `Spot: M`, `Spot: L`, `Expand Spot`) + `7` Still-only (`AF-C`) `Tracking:`
    areas (`Tracking: Wide`, `Tracking: Zone`, `Tracking: Center Fix`, `Tracking: Spot S/M/L`,
    `Tracking: Expand Spot`), blocking Movie/`S&Q` menu `Tracking:` selection
    (`STATUS_BLOCKED_G119_MOVIE_TRACKING_FOCUS_AREA_VIOLATION` — Movie uses `Touch Tracking`).
  - `[Focus Area Limit]` `>= 2` (`0x6de2`/`0xe227`), `[Focus Area Color]` (`White`/`Red` `0x6af1`,
    non-resettable by `Camera Settings Reset`), `[Circ. of Focus Point]` (`0x74f6`), `[Switch V/H AF Area]`,
    and Still-only `[AF Area Registration]` (`0x6b65`, locks `[Lock Operation Parts]` to `Off` and
    survives `Camera Settings Reset`, `STATUS_BLOCKED_G119_FOCUS_AREA_LIMIT_OR_AF_REG_VIOLATION`).
  - `XLR-H1` vs `FX6` Smart Handle hardware truth: `ILME-FX3` `XLR-H1` has NO zoom lever,
    NO record button, and NO `ZOOM HOLD` switch (`STATUS_BLOCKED_G119_XLRH1_FAKE_HANDLE_ZOOM_SPOOF_VIOLATION`),
    vs body `W/T` `[Zoom Lever Speed]` (`1st=3`, `2nd=8`, `1..8` `STBY`/`REC`, `0x6304`),
    `[Custom Key Z. Speed]` (`1..8` default `3`, `0x78e8`), `[Remote Zoom Speed]` (`Variable`/`Fixed` `1..8`, `0x7128`),
    and non-resettable `[Zoom Range]` (`Optical zoom only` / `ClearImage Zoom` / `Digital Zoom`
    locked out in `RAW` or `119.88p`/`100p`, `0x7164`), vs `FX6` `0..99` `Zoom Position Display` (`0x22ce`),
    across `384` matrix states.
- Gate `G120` (`GATE_G120_ISO_RANGE_MINSS_CINE_EI_AND_STILL_MECHANICAL_FLASH_SYNC_GUARD`):
  - `[ISO Range Limit]` (`0x72f8`, `50..409600`, survives `Camera Settings Reset`) &
    `[ISO AUTO Min. SS]` (`0x778b`, `Slower..Faster` or `1/8000..30"`, Still `P`/`A` + `ISO AUTO` ONLY),
    with `Cine EI` / `Cine EI Quick` pinning sensor sensitivity strictly to Base `ISO 800` / `ISO 12800`
    (`STATUS_BLOCKED_G120_ISO_MINSS_MOVIE_OR_CINE_EI_VIOLATION`).
  - `[Flash Mode]` (`.uxc` `0xe5ce`: `Autoflash`, `Fill-flash`, `Slow Sync.`, `Rear Sync.`, `Flash Off`),
    `[Flash Comp.]` (`-3.0..+3.0 EV` `0xe5d3`), non-resettable `[Exp.comp.set]` (`Ambient&flash`/`Ambient only` `0xe11a`),
    `[Wireless Flash]` (`0x6201`), `[Red Eye Reduction]` (`0x7ac9`), `[External Flash Set.]` (`0x6771`):
    strictly Still-only (`VAL_HAITA_*_EXPOSURE_MODE_STILL`) AND Mechanical-Shutter-only (`<= 1/250 s` sync,
    hard-disabled in Movie/`S&Q`, `Electronic Shutter`, or `Silent Mode = On`; `< 250 V` positive-polarity
    MI-Shoe overvoltage guard, `STATUS_BLOCKED_G120_FLASH_MOVIE_ESHUTTER_OR_HV_SHOE_VIOLATION`),
    contrasted with `[Video Light Mode]` (`0x6211`) across Still/Movie/`S&Q` and `FX6` `Flash Band Reduce` (`0x4215`),
    across `384` matrix states.
- Unified `120`-Gate Milestone Master Safety Preflight (`evaluate_120gate_preflight` / `verify-120-gates`):
  - `117/120` offline (`VERIFIED_117_OF_120_AWAITING_PHYSICAL_TIER0`) and `120/120` in `--simulate-bench-dry-run`
    (`VERIFIED_ALL_120_GATES_DRY_RUN_SIMULATED_BACKUP`) with all hardware write/live-attach redlines hard-locked `False`.
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
import unittest
from unittest import mock

import fx3_safety
from fx3_safety.__main__ import main as cli_main
from fx3_safety.realhw_raw_heif_colorspace_shuttertype_nr_drive_and_118gate_guard import (
    Master118GateReport,
    evaluate_118gate_preflight,
)
from fx3_safety.realhw_focus_area_zoom_lever_iso_minss_flash_and_120gate_guard import (
    AF_AREA_REG_MENU_PATH_G119,
    AF_AREA_REG_UXC_RESID16_G119,
    AF_FOCUS_MODE_AF_A_G119,
    AF_FOCUS_MODE_AF_C_G119,
    AF_FOCUS_MODE_AF_S_G119,
    AF_FOCUS_MODE_DMF_G119,
    AF_FOCUS_MODE_MF_G119,
    ALLOWED_CIRC_FOCUS_POINT_MODES_G119,
    ALLOWED_EXP_COMP_SET_MODES_G120,
    ALLOWED_FOCUS_AREA_COLORS_G119,
    ALLOWED_FOCUS_MODES_G119,
    ALLOWED_LOG_SHOOTING_MODES_G120,
    ALLOWED_REMOTE_ZOOM_SPEED_TYPES_G119,
    ALLOWED_RESET_ACTIONS_PHASE286,
    ALLOWED_SHOOT_MODES_PHASE286,
    ALLOWED_SWITCH_VH_MODES_G119,
    ALLOWED_ZOOM_RANGES_G119,
    CINE_EI_BASE_ISOS_G120,
    CINE_EI_LOCKED_LOG_MODES_G120,
    CIRCULATING_FOCUS_AREAS_G119,
    CIRC_CIRCULATE_G119,
    CIRC_DOES_NOT_CIRCULATE_G119,
    CIRC_FOCUS_POINT_DEFAULT_G119,
    CUSTOM_KEY_Z_SPEED_DEFAULT_G119,
    DEFAULT_REPO_ROOT,
    DONOR_CHECK_CI_MAX_SECONDS_PHASE286,
    DONOR_CHECK_MAX_SECONDS_PHASE286,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    ENV_CLEAN_ROOM_TEST_PHASE286,
    EXP_COMP_SET_AMBIENT_AND_FLASH_G120,
    EXP_COMP_SET_AMBIENT_ONLY_G120,
    EXP_COMP_SET_FACTORY_DEFAULT_G120,
    EXP_COMP_SET_UXC_RESID16_G120,
    FLASH_COMP_MAX_EV_G120,
    FLASH_COMP_MIN_EV_G120,
    FLASH_MODE_AUTOFLASH_G120,
    FLASH_MODE_FACTORY_DEFAULT_G120,
    FLASH_MODE_FILL_FLASH_G120,
    FLASH_MODE_FLASH_OFF_G120,
    FLASH_MODE_MENU_PATH_G120,
    FLASH_MODE_REAR_SYNC_G120,
    FLASH_MODE_SLOW_SYNC_G120,
    FLASH_MODE_UXC_RESID16_G120,
    FOCUS_AREA_CENTER_FIX_G119,
    FOCUS_AREA_COLOR_FACTORY_DEFAULT_G119,
    FOCUS_AREA_COLOR_RED_G119,
    FOCUS_AREA_COLOR_WHITE_G119,
    FOCUS_AREA_EXPAND_SPOT_G119,
    FOCUS_AREA_FACTORY_DEFAULT_G119,
    FOCUS_AREA_MENU_PATH_G119,
    FOCUS_AREA_SPOT_L_G119,
    FOCUS_AREA_SPOT_M_G119,
    FOCUS_AREA_SPOT_S_G119,
    FOCUS_AREA_TRACKING_CENTER_FIX_G119,
    FOCUS_AREA_TRACKING_EXPAND_SPOT_G119,
    FOCUS_AREA_TRACKING_SPOT_L_G119,
    FOCUS_AREA_TRACKING_SPOT_M_G119,
    FOCUS_AREA_TRACKING_SPOT_S_G119,
    FOCUS_AREA_TRACKING_WIDE_G119,
    FOCUS_AREA_TRACKING_ZONE_G119,
    FOCUS_AREA_UXC_RESID16_G119,
    FOCUS_AREA_WIDE_G119,
    FOCUS_AREA_ZONE_G119,
    FX3_DEFAULT_FW_VERSION_PHASE286,
    FX3_EXACT_14_FOCUS_AREAS_G119,
    FX3_EXACT_4_VIDEO_LIGHT_MODES_G120,
    FX3_EXACT_5_FLASH_MODES_G120,
    FX3_FLASH_SYNC_CEILING_DENOM_G120,
    FX3_FLASH_SYNC_CEILING_SECONDS_G120,
    FX3_HELP_GUIDE_CODE_PHASE286,
    FX3_MI_SHOE_MAX_SAFE_SYNC_VOLTAGE_V_G120,
    FX3_MODEL_ID,
    FX3_MODEL_NAME,
    FX3_SHARED_7_FOCUS_AREAS_G119,
    FX3_STILL_ONLY_7_TRACKING_FOCUS_AREAS_G119,
    FX3_XLR_H1_HAS_REC_BUTTON_G119,
    FX3_XLR_H1_HAS_ZOOM_HOLD_SWITCH_G119,
    FX3_XLR_H1_HAS_ZOOM_LEVER_G119,
    FX6_DEFAULT_FW_VERSION_PHASE286,
    FX6_EXACT_3_FOCUS_AREAS_G119,
    FX6_FLASH_BAND_REDUCE_UXC_RESID16_G120,
    FX6_HANDLE_HOLD_MODES_G119,
    FX6_HANDLE_ZOOM_MODES_G119,
    FX6_MODEL_NAME_PHASE286,
    FX6_ZOOM_POSITION_DISPLAY_RANGE_G119,
    FX6_ZOOM_POSITION_DISPLAY_UXC_RESID16_G119,
    G119,
    G119_GATE_CODE,
    G119_GATE_ID,
    G120,
    G120_GATE_CODE,
    G120_GATE_ID,
    GATE_G119_FOCUS_AREA_14OPT_AF_REG_XLRH1_NO_ZOOM_LEVER_AND_ZOOM_SPEED_GUARD,
    GATE_G120_ISO_RANGE_MINSS_CINE_EI_AND_STILL_MECHANICAL_FLASH_SYNC_GUARD,
    HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    HUMAN_HARDWARE_ATTACH_TOKEN,
    ISO_AUTO_MIN_SS_FACTORY_DEFAULT_G120,
    ISO_AUTO_MIN_SS_FASTER_G120,
    ISO_AUTO_MIN_SS_FAST_G120,
    ISO_AUTO_MIN_SS_MANUAL_SHUTTER_TOKENS_G120,
    ISO_AUTO_MIN_SS_MENU_PATH_G120,
    ISO_AUTO_MIN_SS_RELATIVE_PRESETS_G120,
    ISO_AUTO_MIN_SS_SLOWER_G120,
    ISO_AUTO_MIN_SS_SLOW_G120,
    ISO_AUTO_MIN_SS_STANDARD_G120,
    ISO_AUTO_MIN_SS_UXC_RESID16_G120,
    ISO_DEFAULT_STILL_MAX_G120,
    ISO_DEFAULT_STILL_MIN_G120,
    ISO_HARDWARE_MAX_G120,
    ISO_HARDWARE_MIN_G120,
    ISO_RANGE_LIMIT_MENU_PATH_G120,
    ISO_RANGE_LIMIT_UXC_RESID16_G120,
    LOG_SHOOTING_CINE_EI_G120,
    LOG_SHOOTING_CINE_EI_QUICK_G120,
    LOG_SHOOTING_FLEXIBLE_ISO_G120,
    LOG_SHOOTING_OFF_G120,
    MIN_FOCUS_AREA_LIMIT_COUNT_G119,
    MOVIE_TRACKING_MECHANISM_G119,
    Master120GateReport,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED,
    PHYSICAL_USB_PACKETS_EMITTED,
    PINNED_FX3_APPFW_SLICES_PHASE286,
    PINNED_FX3_APPFW_SLICES_SHA256_PHASE286,
    PINNED_FX6_APPFW_SLICES_PHASE286,
    PINNED_FX6_APPFW_SLICES_SHA256_PHASE286,
    PINNED_PHASE286_DONOR_SPECS,
    Phase286DonorAuditResult,
    RAW_FIRMWARE_BYTES_LEAKED,
    REALHW_FOCUS_AREA_ZOOM_LEVER_ISO_MINSS_FLASH_120GATE_SCHEMA,
    REALHW_FOCUS_AREA_ZOOM_LEVER_ISO_MINSS_FLASH_120GATE_VERSION,
    REMOTE_ZOOM_FIXED_SPEED_DEFAULT_G119,
    REMOTE_ZOOM_SPEED_TYPE_FIXED_G119,
    REMOTE_ZOOM_SPEED_TYPE_VARIABLE_G119,
    RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE286,
    RESET_ACTION_INITIALIZE_PHASE286,
    RESET_ACTION_NONE_PHASE286,
    RESET_ACTION_RESET_NETWORK_SET_PHASE286,
    SHOOT_MODE_A_PHASE286,
    SHOOT_MODE_INTELLIGENT_AUTO_PHASE286,
    SHOOT_MODE_MOVIE_PHASE286,
    SHOOT_MODE_M_PHASE286,
    SHOOT_MODE_P_PHASE286,
    SHOOT_MODE_SQ_PHASE286,
    SHOOT_MODE_STILL_PASM_PHASE286,
    SHOOT_MODE_S_PHASE286,
    SHUTTER_TYPE_ELECTRONIC_G120,
    SHUTTER_TYPE_MECHANICAL_G120,
    SPI_NOR_WRITE_AUTHORIZED,
    STATUS_BLOCKED_G119_FOCUS_AREA_LIMIT_OR_AF_REG_VIOLATION,
    STATUS_BLOCKED_G119_MOVIE_TRACKING_FOCUS_AREA_VIOLATION,
    STATUS_BLOCKED_G119_TELEMETRY_INVALID,
    STATUS_BLOCKED_G119_XLRH1_FAKE_HANDLE_ZOOM_SPOOF_VIOLATION,
    STATUS_BLOCKED_G119_ZOOM_RANGE_OR_SPEED_BOUNDARY_VIOLATION,
    STATUS_BLOCKED_G120_FLASH_MOVIE_ESHUTTER_OR_HV_SHOE_VIOLATION,
    STATUS_BLOCKED_G120_ISO_MINSS_MOVIE_OR_CINE_EI_VIOLATION,
    STATUS_BLOCKED_G120_ISO_RANGE_OR_RESET_PERSISTENCE_VIOLATION,
    STATUS_BLOCKED_G120_TELEMETRY_INVALID,
    STATUS_BLOCKED_G120_VIDEO_LIGHT_OR_FLASH_COMP_VIOLATION,
    STATUS_BLOCKED_PHASE286_DONOR_INTEGRITY,
    STATUS_VERIFIED_G119,
    STATUS_VERIFIED_G120,
    SWITCH_VH_AF_POINT_ONLY_G119,
    SWITCH_VH_AF_POINT_PLUS_AREA_G119,
    SWITCH_VH_OFF_G119,
    USB_PACKETS_TRANSMITTED,
    VIDEO_LIGHT_AUTO_G120,
    VIDEO_LIGHT_FACTORY_DEFAULT_G120,
    VIDEO_LIGHT_MODE_UXC_RESID16_G120,
    VIDEO_LIGHT_POWER_LINK_G120,
    VIDEO_LIGHT_REC_LINK_G120,
    VIDEO_LIGHT_REC_LINK_STBY_G120,
    ZOOM_LEVER_1ST_DEFAULT_G119,
    ZOOM_LEVER_2ND_DEFAULT_G119,
    ZOOM_RANGE_CLEAR_IMAGE_G119,
    ZOOM_RANGE_DIGITAL_G119,
    ZOOM_RANGE_FACTORY_DEFAULT_G119,
    ZOOM_RANGE_OPTICAL_ONLY_G119,
    ZOOM_SPEED_MAX_G119,
    ZOOM_SPEED_MIN_G119,
    _default_donor_budget_seconds_phase286,
    _is_forced_clean_room,
    audit_phase286_donor_contracts,
    compute_focus_area_and_zoom_lever_matrix,
    compute_iso_minss_and_flash_matrix,
    evaluate_120_master_safety_gates,
    evaluate_120gate_preflight,
    evaluate_g119_focus_area_and_zoom_lever_guard,
    evaluate_g120_iso_minss_and_flash_guard,
    main as module_main,
    resolve_fx3_focus_area_and_zoom_lever_state,
    resolve_fx3_iso_minss_and_flash_state,
    run_120_gate_preflight,
    verify_focus_area_and_zoom_lever_guard,
    verify_iso_minss_and_flash_guard,
)


def _subprocess_timeout_seconds() -> float:
    return 15.0 if os.environ.get("GITHUB_ACTIONS") == "true" else 10.0


class TestPhase286FocusAreaZoomIsoFlash120GateGuard(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.clean_offline_118: Master118GateReport = evaluate_118gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=False,
        )
        cls.clean_dryrun_118: Master118GateReport = evaluate_118gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
        )

    # --- 1. Redlines, Schema & Public Exports (Tests 01-05) ---

    def test_01_hard_locked_redlines_and_schema(self) -> None:
        self.assertEqual(
            REALHW_FOCUS_AREA_ZOOM_LEVER_ISO_MINSS_FLASH_120GATE_SCHEMA,
            "realhw_focus_area_zoom_lever_iso_minss_flash_and_120gate_guard_v1",
        )
        self.assertEqual(REALHW_FOCUS_AREA_ZOOM_LEVER_ISO_MINSS_FLASH_120GATE_VERSION, "1.0.0")
        self.assertFalse(EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        self.assertFalse(SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(PERSISTENT_WRITE_RELEASE)
        self.assertFalse(PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED)
        self.assertFalse(HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        self.assertFalse(HUMAN_HARDWARE_ATTACH_TOKEN)
        self.assertEqual(USB_PACKETS_TRANSMITTED, 0)
        self.assertEqual(PHYSICAL_USB_PACKETS_EMITTED, 0)
        self.assertEqual(RAW_FIRMWARE_BYTES_LEAKED, 0)

    def test_02_gate_aliases_and_package_exports(self) -> None:
        self.assertEqual(G119, G119_GATE_ID)
        self.assertEqual(G120, G120_GATE_ID)
        self.assertEqual(
            GATE_G119_FOCUS_AREA_14OPT_AF_REG_XLRH1_NO_ZOOM_LEVER_AND_ZOOM_SPEED_GUARD,
            G119_GATE_CODE,
        )
        self.assertEqual(
            GATE_G120_ISO_RANGE_MINSS_CINE_EI_AND_STILL_MECHANICAL_FLASH_SYNC_GUARD,
            G120_GATE_CODE,
        )
        self.assertIs(evaluate_120_master_safety_gates, evaluate_120gate_preflight)
        self.assertIs(run_120_gate_preflight, evaluate_120gate_preflight)
        for name in (
            "evaluate_120gate_preflight",
            "evaluate_120_master_safety_gates",
            "run_120_gate_preflight",
            "evaluate_g119_focus_area_and_zoom_lever_guard",
            "evaluate_g120_iso_minss_and_flash_guard",
            "verify_focus_area_and_zoom_lever_guard",
            "verify_iso_minss_and_flash_guard",
            "audit_phase286_donor_contracts",
            "Master120GateReport",
            "G119_GATE_ID",
            "G120_GATE_ID",
            "realhw_focus_area_zoom_lever_iso_minss_flash_and_120gate_guard",
        ):
            self.assertIn(name, fx3_safety.__all__)
            self.assertTrue(hasattr(fx3_safety, name), msg=name)

    def test_03_pinned_donor_specs_and_slices_integrity(self) -> None:
        self.assertEqual(len(PINNED_PHASE286_DONOR_SPECS), 11)
        self.assertEqual(len(PINNED_FX3_APPFW_SLICES_PHASE286), 27)
        self.assertEqual(len(PINNED_FX6_APPFW_SLICES_PHASE286), 9)
        self.assertEqual(len(PINNED_FX3_APPFW_SLICES_SHA256_PHASE286), 64)
        self.assertEqual(len(PINNED_FX6_APPFW_SLICES_SHA256_PHASE286), 64)
        self.assertEqual(FX3_DEFAULT_FW_VERSION_PHASE286, "7.02")
        self.assertEqual(FX6_DEFAULT_FW_VERSION_PHASE286, "6.01")
        self.assertEqual(FX3_HELP_GUIDE_CODE_PHASE286, "ilc/2210")

    def test_04_donor_audit_synthetic_clean_room_fast_and_zero_leak(self) -> None:
        res = audit_phase286_donor_contracts(force_clean_room=True)
        self.assertIsInstance(res, Phase286DonorAuditResult)
        self.assertTrue(res.valid)
        self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(res.access_mode, "SYNTHETIC_CLEAN_ROOM")
        self.assertEqual(res.files_inspected, 0)
        self.assertEqual(res.raw_firmware_bytes_leaked, 0)
        self.assertTrue(res.within_budget_200ms)
        self.assertTrue(res.fx3_contracts_verified)
        self.assertTrue(res.fx6_contracts_verified)
        self.assertTrue(res.four_lang_resid16_parity_verified)
        self.assertEqual(len(res.checked_markers), 11)
        self.assertEqual(res.missing_markers, ())

    def test_05_donor_audit_dual_mode_o_rdonly_or_clean_room_fallback(self) -> None:
        res = audit_phase286_donor_contracts(repo_root=DEFAULT_REPO_ROOT)
        self.assertTrue(res.valid, msg=res.errors)
        self.assertIn(res.verification_mode, ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"))
        self.assertTrue(res.within_budget_200ms)
        self.assertEqual(res.raw_firmware_bytes_leaked, 0)
        if res.verification_mode == "LOCAL_DONOR_O_RDONLY":
            self.assertEqual(res.access_mode, "OS_OPEN_O_RDONLY")
            self.assertEqual(res.files_inspected, 11)
            self.assertEqual(
                res.sha256_by_artifact["fx3_appfw_so"],
                PINNED_FX3_APPFW_SLICES_SHA256_PHASE286,
            )
            self.assertEqual(
                res.sha256_by_artifact["fx6_appfw_so"],
                PINNED_FX6_APPFW_SLICES_SHA256_PHASE286,
            )

    def test_06_donor_audit_nonexistent_work_root_falls_back_cleanly(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            res = audit_phase286_donor_contracts(work_root=Path(td))
            self.assertTrue(res.valid)
            self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertEqual(res.raw_firmware_bytes_leaked, 0)

    def test_07_donor_audit_tampered_file_blocks_integrity(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            work_root = Path(td)
            for _body, rel_path, *_rest in PINNED_PHASE286_DONOR_SPECS.values():
                fp = work_root / rel_path
                fp.parent.mkdir(parents=True, exist_ok=True)
                fp.write_bytes(b"TAMPERED_DONOR_STUB")
            res = audit_phase286_donor_contracts(work_root=work_root, force_clean_room=False)
            self.assertFalse(res.valid)
            self.assertEqual(res.status, STATUS_BLOCKED_PHASE286_DONOR_INTEGRITY)
            self.assertEqual(len(res.missing_markers), 11)

    def test_08_donor_budget_ci_headroom_check(self) -> None:
        with mock.patch.dict(os.environ, {"GITHUB_ACTIONS": "true"}):
            self.assertEqual(_default_donor_budget_seconds_phase286(), DONOR_CHECK_CI_MAX_SECONDS_PHASE286)
        with mock.patch.dict(os.environ, {"GITHUB_ACTIONS": "false"}):
            self.assertEqual(_default_donor_budget_seconds_phase286(), DONOR_CHECK_MAX_SECONDS_PHASE286)
        res = audit_phase286_donor_contracts(force_clean_room=True, max_budget_seconds=-1.0)
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_PHASE286_DONOR_INTEGRITY)

    # --- 2. Gate G119: 14-Option [Focus Area], AF Area Reg, XLR-H1 & Zoom Speeds (Tests 09-33) ---

    def test_09_g119_exact_14_focus_areas_and_uxc_ids(self) -> None:
        self.assertEqual(len(FX3_EXACT_14_FOCUS_AREAS_G119), 14)
        self.assertEqual(len(FX3_SHARED_7_FOCUS_AREAS_G119), 7)
        self.assertEqual(len(FX3_STILL_ONLY_7_TRACKING_FOCUS_AREAS_G119), 7)
        self.assertEqual(
            FX3_EXACT_14_FOCUS_AREAS_G119,
            FX3_SHARED_7_FOCUS_AREAS_G119 + FX3_STILL_ONLY_7_TRACKING_FOCUS_AREAS_G119,
        )
        self.assertEqual(FOCUS_AREA_FACTORY_DEFAULT_G119, FOCUS_AREA_WIDE_G119)
        self.assertEqual(FOCUS_AREA_UXC_RESID16_G119, 0xE0AD)
        self.assertEqual(AF_AREA_REG_UXC_RESID16_G119, 0x6B65)
        self.assertEqual(MOVIE_TRACKING_MECHANISM_G119, "Touch Tracking")
        self.assertEqual(FX6_EXACT_3_FOCUS_AREAS_G119, ("Wide", "Zone", "Flexible Spot"))

    def test_10_g119_default_fx3_state_verified(self) -> None:
        res = verify_focus_area_and_zoom_lever_guard()
        self.assertTrue(res.valid, msg=res.errors)
        self.assertEqual(res.status, STATUS_VERIFIED_G119)
        self.assertEqual(res.effective_focus_area, FOCUS_AREA_WIDE_G119)
        self.assertEqual(res.focus_area_limit_enabled_count, 14)
        self.assertFalse(res.xlr_h1_has_zoom_lever)
        self.assertFalse(res.xlr_h1_has_rec_button)
        self.assertFalse(res.xlr_h1_has_zoom_hold_switch)
        self.assertEqual(res.zoom_lever_1st_speed_stby, ZOOM_LEVER_1ST_DEFAULT_G119)
        self.assertEqual(res.zoom_lever_2nd_speed_stby, ZOOM_LEVER_2ND_DEFAULT_G119)
        self.assertEqual(res.fx6_zoom_position_display_range, (0, 99))
        self.assertEqual(res.matrix_states_checked, 384)

    def test_11_g119_all_7_shared_focus_areas_allowed_in_movie_and_sq(self) -> None:
        for sm in (SHOOT_MODE_MOVIE_PHASE286, SHOOT_MODE_SQ_PHASE286):
            for fa in FX3_SHARED_7_FOCUS_AREAS_G119:
                res = verify_focus_area_and_zoom_lever_guard(
                    shoot_mode=sm,
                    requested_focus_area=fa,
                )
                self.assertTrue(res.valid, msg=f"{sm}/{fa}: {res.errors}")
                self.assertEqual(res.effective_focus_area, fa)

    def test_12_g119_all_7_tracking_focus_areas_allowed_in_still_afc_only(self) -> None:
        for fa in FX3_STILL_ONLY_7_TRACKING_FOCUS_AREAS_G119:
            res = verify_focus_area_and_zoom_lever_guard(
                shoot_mode=SHOOT_MODE_M_PHASE286,
                focus_mode=AF_FOCUS_MODE_AF_C_G119,
                requested_focus_area=fa,
            )
            self.assertTrue(res.valid, msg=f"{fa}: {res.errors}")
            self.assertEqual(res.effective_focus_area, fa)

    def test_13_g119_movie_and_sq_block_all_7_tracking_focus_areas(self) -> None:
        for sm in (SHOOT_MODE_MOVIE_PHASE286, SHOOT_MODE_SQ_PHASE286):
            for fa in FX3_STILL_ONLY_7_TRACKING_FOCUS_AREAS_G119:
                res = verify_focus_area_and_zoom_lever_guard(
                    shoot_mode=sm,
                    focus_mode=AF_FOCUS_MODE_AF_C_G119,
                    requested_focus_area=fa,
                )
                self.assertFalse(res.valid, msg=f"{sm}/{fa}")
                self.assertEqual(res.status, STATUS_BLOCKED_G119_MOVIE_TRACKING_FOCUS_AREA_VIOLATION)
                self.assertEqual(res.effective_focus_area, FOCUS_AREA_WIDE_G119)

    def test_14_g119_still_tracking_requires_afc_and_blocks_non_afc(self) -> None:
        for fm in (
            AF_FOCUS_MODE_AF_S_G119,
            AF_FOCUS_MODE_AF_A_G119,
            AF_FOCUS_MODE_DMF_G119,
            AF_FOCUS_MODE_MF_G119,
        ):
            res = verify_focus_area_and_zoom_lever_guard(
                shoot_mode=SHOOT_MODE_P_PHASE286,
                focus_mode=fm,
                requested_focus_area=FOCUS_AREA_TRACKING_SPOT_M_G119,
            )
            self.assertFalse(res.valid, msg=fm)
            self.assertEqual(res.status, STATUS_BLOCKED_G119_MOVIE_TRACKING_FOCUS_AREA_VIOLATION)

    def test_15_g119_spoofed_movie_tracking_or_fx3_focus_area_catalog_blocked(self) -> None:
        res1 = verify_focus_area_and_zoom_lever_guard(claimed_movie_tracking_menu_available=True)
        self.assertFalse(res1.valid)
        self.assertEqual(res1.status, STATUS_BLOCKED_G119_MOVIE_TRACKING_FOCUS_AREA_VIOLATION)

        res2 = verify_focus_area_and_zoom_lever_guard(claimed_fx6_has_tracking_focus_areas=True)
        self.assertFalse(res2.valid)
        self.assertEqual(res2.status, STATUS_BLOCKED_G119_MOVIE_TRACKING_FOCUS_AREA_VIOLATION)

        res3 = verify_focus_area_and_zoom_lever_guard(
            claimed_fx3_focus_areas=FX3_SHARED_7_FOCUS_AREAS_G119
        )
        self.assertFalse(res3.valid)
        self.assertEqual(res3.status, STATUS_BLOCKED_G119_MOVIE_TRACKING_FOCUS_AREA_VIOLATION)

    def test_16_g119_focus_area_limit_enforces_min_2_areas(self) -> None:
        res_ok = verify_focus_area_and_zoom_lever_guard(
            focus_area_limit_enabled_count=MIN_FOCUS_AREA_LIMIT_COUNT_G119
        )
        self.assertTrue(res_ok.valid)

        for bad_cnt in (0, 1, 15):
            res_bad = verify_focus_area_and_zoom_lever_guard(
                focus_area_limit_enabled_count=bad_cnt
            )
            self.assertFalse(res_bad.valid, msg=bad_cnt)
            self.assertEqual(res_bad.status, STATUS_BLOCKED_G119_FOCUS_AREA_LIMIT_OR_AF_REG_VIOLATION)

    def test_17_g119_focus_area_color_and_af_reg_survive_cam_reset_but_init_clears(self) -> None:
        res_cam = verify_focus_area_and_zoom_lever_guard(
            requested_focus_area_color=FOCUS_AREA_COLOR_RED_G119,
            requested_af_area_registration="On",
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE286,
        )
        self.assertTrue(res_cam.valid, msg=res_cam.errors)
        self.assertEqual(res_cam.focus_area_color, FOCUS_AREA_COLOR_RED_G119)
        self.assertTrue(res_cam.focus_area_color_survived_cam_reset)
        self.assertEqual(res_cam.effective_af_area_registration, "On")
        self.assertTrue(res_cam.af_area_reg_survived_cam_reset)
        self.assertTrue(res_cam.lock_operation_parts_forced_off)

        res_init = verify_focus_area_and_zoom_lever_guard(
            requested_focus_area_color=FOCUS_AREA_COLOR_RED_G119,
            requested_af_area_registration="On",
            reset_action=RESET_ACTION_INITIALIZE_PHASE286,
        )
        self.assertTrue(res_init.valid)
        self.assertEqual(res_init.focus_area_color, FOCUS_AREA_COLOR_WHITE_G119)
        self.assertEqual(res_init.effective_af_area_registration, "Off")
        self.assertFalse(res_init.lock_operation_parts_forced_off)

    def test_18_g119_af_area_registration_still_only_and_reset_spoof_blocked(self) -> None:
        res_mv = verify_focus_area_and_zoom_lever_guard(
            shoot_mode=SHOOT_MODE_MOVIE_PHASE286,
            requested_af_area_registration="On",
        )
        self.assertFalse(res_mv.valid)
        self.assertEqual(res_mv.status, STATUS_BLOCKED_G119_FOCUS_AREA_LIMIT_OR_AF_REG_VIOLATION)

        for kw in (
            {"claimed_camera_reset_resets_focus_area_color": True},
            {"claimed_camera_reset_resets_af_area_reg": True},
            {"claimed_af_area_reg_allows_lock_op_parts_on": True},
        ):
            res_sp = verify_focus_area_and_zoom_lever_guard(**kw)
            self.assertFalse(res_sp.valid, msg=kw)
            self.assertEqual(res_sp.status, STATUS_BLOCKED_G119_FOCUS_AREA_LIMIT_OR_AF_REG_VIOLATION)

    def test_19_g119_circ_of_focus_point_and_switch_vh_modes(self) -> None:
        for circ in ALLOWED_CIRC_FOCUS_POINT_MODES_G119:
            for vh in ALLOWED_SWITCH_VH_MODES_G119:
                res = verify_focus_area_and_zoom_lever_guard(
                    shoot_mode=SHOOT_MODE_M_PHASE286,
                    requested_circ_of_focus_point=circ,
                    requested_switch_vh_af_area=vh,
                )
                self.assertTrue(res.valid, msg=f"{circ}/{vh}")
                self.assertEqual(res.circ_of_focus_point, circ)
                self.assertEqual(res.switch_vh_af_area, vh)

        r_dig = resolve_fx3_focus_area_and_zoom_lever_state(
            shoot_mode=SHOOT_MODE_M_PHASE286,
            requested_zoom_range=ZOOM_RANGE_DIGITAL_G119,
            requested_switch_vh_af_area=SWITCH_VH_AF_POINT_PLUS_AREA_G119,
        )
        self.assertEqual(r_dig["switch_vh_af_area"], SWITCH_VH_OFF_G119)
        self.assertEqual(len(CIRCULATING_FOCUS_AREAS_G119), 10)

    def test_20_g119_xlr_h1_no_zoom_lever_myth_bust_blocks_spoof(self) -> None:
        self.assertFalse(FX3_XLR_H1_HAS_ZOOM_LEVER_G119)
        self.assertFalse(FX3_XLR_H1_HAS_REC_BUTTON_G119)
        self.assertFalse(FX3_XLR_H1_HAS_ZOOM_HOLD_SWITCH_G119)
        self.assertEqual(FX6_HANDLE_ZOOM_MODES_G119, ("Off", "Low", "High", "Variable"))
        self.assertEqual(FX6_HANDLE_HOLD_MODES_G119, ("Normal", "Rec Button Only"))
        self.assertEqual(FX6_ZOOM_POSITION_DISPLAY_UXC_RESID16_G119, 0x22CE)

        for kw in (
            {"claimed_xlr_h1_has_zoom_lever": True},
            {"claimed_xlr_h1_has_rec_button": True},
            {"claimed_xlr_h1_has_zoom_hold_switch": True},
            {"claimed_fx6_0_99_is_zoom_speed": True},
        ):
            res = verify_focus_area_and_zoom_lever_guard(**kw)
            self.assertFalse(res.valid, msg=kw)
            self.assertEqual(res.status, STATUS_BLOCKED_G119_XLRH1_FAKE_HANDLE_ZOOM_SPOOF_VIOLATION)

    def test_21_g119_zoom_speeds_valid_1_to_8_and_out_of_range_blocked(self) -> None:
        res_ok = verify_focus_area_and_zoom_lever_guard(
            zoom_lever_1st_speed_stby=ZOOM_SPEED_MIN_G119,
            zoom_lever_1st_speed_rec=4,
            zoom_lever_2nd_speed_stby=ZOOM_SPEED_MAX_G119,
            zoom_lever_2nd_speed_rec=7,
            custom_key_z_speed_stby=2,
            custom_key_z_speed_rec=6,
            remote_zoom_speed_type=REMOTE_ZOOM_SPEED_TYPE_FIXED_G119,
            remote_zoom_fixed_speed_stby=5,
            remote_zoom_fixed_speed_rec=8,
        )
        self.assertTrue(res_ok.valid, msg=res_ok.errors)
        self.assertEqual(res_ok.remote_zoom_speed_type, REMOTE_ZOOM_SPEED_TYPE_FIXED_G119)

        for field, bad_val in (
            ("zoom_lever_1st_speed_stby", 0),
            ("zoom_lever_1st_speed_rec", 9),
            ("zoom_lever_2nd_speed_stby", 99),
            ("zoom_lever_2nd_speed_rec", -1),
            ("custom_key_z_speed_stby", 0),
            ("custom_key_z_speed_rec", 9),
            ("remote_zoom_fixed_speed_stby", 0),
            ("remote_zoom_fixed_speed_rec", 99),
        ):
            res_bad = verify_focus_area_and_zoom_lever_guard(**{field: bad_val})
            self.assertFalse(res_bad.valid, msg=f"{field}={bad_val}")
            self.assertEqual(res_bad.status, STATUS_BLOCKED_G119_ZOOM_RANGE_OR_SPEED_BOUNDARY_VIOLATION)

    def test_22_g119_zoom_range_raw_120p_lockout_and_cam_reset_survival(self) -> None:
        for zr in (ZOOM_RANGE_CLEAR_IMAGE_G119, ZOOM_RANGE_DIGITAL_G119):
            res_ok = verify_focus_area_and_zoom_lever_guard(
                requested_zoom_range=zr,
                reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE286,
            )
            self.assertTrue(res_ok.valid, msg=res_ok.errors)
            self.assertEqual(res_ok.effective_zoom_range, zr)
            self.assertTrue(res_ok.zoom_range_survived_cam_reset)

            res_raw = verify_focus_area_and_zoom_lever_guard(
                requested_zoom_range=zr,
                raw_recording=True,
            )
            self.assertFalse(res_raw.valid)
            self.assertEqual(res_raw.status, STATUS_BLOCKED_G119_ZOOM_RANGE_OR_SPEED_BOUNDARY_VIOLATION)
            self.assertEqual(res_raw.effective_zoom_range, ZOOM_RANGE_OPTICAL_ONLY_G119)

            res_120 = verify_focus_area_and_zoom_lever_guard(
                requested_zoom_range=zr,
                high_fps_120p_100p=True,
            )
            self.assertFalse(res_120.valid)
            self.assertEqual(res_120.status, STATUS_BLOCKED_G119_ZOOM_RANGE_OR_SPEED_BOUNDARY_VIOLATION)

        res_spoof = verify_focus_area_and_zoom_lever_guard(
            claimed_camera_reset_resets_zoom_range=True
        )
        self.assertFalse(res_spoof.valid)
        self.assertEqual(res_spoof.status, STATUS_BLOCKED_G119_ZOOM_RANGE_OR_SPEED_BOUNDARY_VIOLATION)

    def test_23_g119_384_state_matrix_invariants(self) -> None:
        m = compute_focus_area_and_zoom_lever_matrix()
        self.assertEqual(m["states_checked"], 384)
        self.assertEqual(m["movie_tracking_locked_states"], 96)
        self.assertEqual(m["af_reg_lock_op_parts_off_states"], 32)
        self.assertEqual(m["ciz_locked_in_raw_120p_states"], 96)
        self.assertEqual(m["non_resettable_survived_cam_reset_states"], 128)
        self.assertTrue(m["all_invariants_hold"])

    def test_24_g119_invalid_telemetry_bool_int_and_model_rejected(self) -> None:
        for bad_kw in (
            {"body_model_name": FX6_MODEL_NAME_PHASE286},
            {"body_model_id": True},
            {"body_model_id": 0x12345678},
            {"help_guide_code": "ilc/9999"},
            {"shoot_mode": "Panorama"},
            {"focus_mode": "AF-Z"},
            {"requested_focus_area": "Tracking: Invalid"},
            {"focus_area_limit_enabled_count": True},
            {"zoom_lever_1st_speed_stby": False},
            {"reset_action": "BOGUS"},
        ):
            res = verify_focus_area_and_zoom_lever_guard(**bad_kw)
            self.assertFalse(res.valid, msg=bad_kw)
            self.assertEqual(res.status, STATUS_BLOCKED_G119_TELEMETRY_INVALID)

    def test_25_g119_evaluator_blocks_persistent_emmc_writes(self) -> None:
        verdict, res = evaluate_g119_focus_area_and_zoom_lever_guard(
            force_clean_room=True,
            request_persistent_emmc_writes=True,
        )
        self.assertFalse(verdict.passed)
        self.assertFalse(res.valid)
        self.assertEqual(verdict.status, "BLOCKED_BY_PERSISTENT_EMMC_WRITE_REDLINE")

    # --- 3. Gate G120: [ISO Range Limit], [ISO AUTO Min. SS], Cine EI & Flash Sync (Tests 26-50) ---

    def test_26_g120_uxc_ids_and_factory_defaults(self) -> None:
        self.assertEqual(ISO_RANGE_LIMIT_UXC_RESID16_G120, 0x72F8)
        self.assertEqual(ISO_AUTO_MIN_SS_UXC_RESID16_G120, 0x778B)
        self.assertEqual(FLASH_MODE_UXC_RESID16_G120, 0xE5CE)
        self.assertEqual(EXP_COMP_SET_UXC_RESID16_G120, 0xE11A)
        self.assertEqual(VIDEO_LIGHT_MODE_UXC_RESID16_G120, 0x6211)
        self.assertEqual(FX6_FLASH_BAND_REDUCE_UXC_RESID16_G120, 0x4215)
        self.assertEqual(len(FX3_EXACT_5_FLASH_MODES_G120), 5)
        self.assertEqual(len(FX3_EXACT_4_VIDEO_LIGHT_MODES_G120), 4)
        self.assertEqual(CINE_EI_BASE_ISOS_G120, (800, 12800))
        self.assertEqual(FX3_FLASH_SYNC_CEILING_DENOM_G120, 250)
        self.assertAlmostEqual(FX3_FLASH_SYNC_CEILING_SECONDS_G120, 1.0 / 250.0)
        self.assertEqual(FX3_MI_SHOE_MAX_SAFE_SYNC_VOLTAGE_V_G120, 250.0)

    def test_27_g120_default_state_verified(self) -> None:
        res = verify_iso_minss_and_flash_guard()
        self.assertTrue(res.valid, msg=res.errors)
        self.assertEqual(res.status, STATUS_VERIFIED_G120)
        self.assertEqual(res.effective_iso_range_min, ISO_DEFAULT_STILL_MIN_G120)
        self.assertEqual(res.effective_iso_range_max, ISO_DEFAULT_STILL_MAX_G120)
        self.assertFalse(res.cine_ei_base_iso_pinned)
        self.assertTrue(res.flash_available)
        self.assertEqual(res.effective_flash_mode, FLASH_MODE_FACTORY_DEFAULT_G120)
        self.assertEqual(res.effective_exp_comp_set, EXP_COMP_SET_FACTORY_DEFAULT_G120)
        self.assertEqual(res.effective_video_light_mode, VIDEO_LIGHT_FACTORY_DEFAULT_G120)
        self.assertFalse(res.fx6_still_flash_supported)
        self.assertTrue(res.fx6_flash_band_reduce_supported)
        self.assertEqual(res.matrix_states_checked, 384)

    def test_28_g120_iso_auto_min_ss_active_strictly_in_still_p_and_a(self) -> None:
        for sm in (SHOOT_MODE_P_PHASE286, SHOOT_MODE_A_PHASE286):
            for preset in ISO_AUTO_MIN_SS_RELATIVE_PRESETS_G120 + ("1/250", "1/1000", '1"'):
                res = verify_iso_minss_and_flash_guard(
                    shoot_mode=sm,
                    iso_mode="ISO AUTO",
                    requested_iso_auto_min_ss=preset,
                )
                self.assertTrue(res.valid, msg=f"{sm}/{preset}: {res.errors}")
                self.assertTrue(res.iso_auto_min_ss_active)
                self.assertEqual(res.effective_iso_auto_min_ss, preset)

        for sm in (SHOOT_MODE_S_PHASE286, SHOOT_MODE_M_PHASE286, SHOOT_MODE_MOVIE_PHASE286):
            r = resolve_fx3_iso_minss_and_flash_state(
                shoot_mode=sm,
                iso_mode="ISO AUTO",
                requested_iso_auto_min_ss=ISO_AUTO_MIN_SS_FAST_G120,
            )
            self.assertFalse(r["iso_auto_min_ss_active"], msg=sm)

    def test_29_g120_iso_auto_min_ss_blocked_in_movie_sq_and_cine_ei(self) -> None:
        for sm in (SHOOT_MODE_MOVIE_PHASE286, SHOOT_MODE_SQ_PHASE286):
            res = verify_iso_minss_and_flash_guard(
                shoot_mode=sm,
                iso_mode="ISO AUTO",
                requested_iso_auto_min_ss=ISO_AUTO_MIN_SS_FASTER_G120,
            )
            self.assertFalse(res.valid, msg=sm)
            self.assertEqual(res.status, STATUS_BLOCKED_G120_ISO_MINSS_MOVIE_OR_CINE_EI_VIOLATION)

        res_cei = verify_iso_minss_and_flash_guard(
            shoot_mode=SHOOT_MODE_M_PHASE286,
            log_shooting=LOG_SHOOTING_CINE_EI_G120,
            requested_iso_value=800,
            requested_iso_auto_min_ss=ISO_AUTO_MIN_SS_SLOW_G120,
        )
        self.assertFalse(res_cei.valid)
        self.assertEqual(res_cei.status, STATUS_BLOCKED_G120_ISO_MINSS_MOVIE_OR_CINE_EI_VIOLATION)

    def test_30_g120_cine_ei_pins_base_iso_800_and_12800_and_blocks_others(self) -> None:
        for log_m in CINE_EI_LOCKED_LOG_MODES_G120:
            for base_iso in CINE_EI_BASE_ISOS_G120:
                res_ok = verify_iso_minss_and_flash_guard(
                    shoot_mode=SHOOT_MODE_MOVIE_PHASE286,
                    log_shooting=log_m,
                    requested_iso_value=base_iso,
                )
                self.assertTrue(res_ok.valid, msg=f"{log_m}/{base_iso}: {res_ok.errors}")
                self.assertTrue(res_ok.cine_ei_base_iso_pinned)
                self.assertEqual(res_ok.effective_base_iso, base_iso)

            for bad_iso in (100, 640, 1600, 3200, 25600):
                res_bad = verify_iso_minss_and_flash_guard(
                    shoot_mode=SHOOT_MODE_MOVIE_PHASE286,
                    log_shooting=log_m,
                    requested_iso_value=bad_iso,
                )
                self.assertFalse(res_bad.valid, msg=f"{log_m}/{bad_iso}")
                self.assertEqual(
                    res_bad.status,
                    STATUS_BLOCKED_G120_ISO_MINSS_MOVIE_OR_CINE_EI_VIOLATION,
                )

    def test_31_g120_iso_range_limit_and_exp_comp_set_survive_cam_reset(self) -> None:
        res_cam = verify_iso_minss_and_flash_guard(
            requested_iso_range_min=200,
            requested_iso_range_max=12800,
            requested_iso_value=1600,
            requested_iso_auto_min_ss=ISO_AUTO_MIN_SS_FAST_G120,
            requested_exp_comp_set=EXP_COMP_SET_AMBIENT_ONLY_G120,
            flash_comp_ev=1.0,
            requested_flash_mode=FLASH_MODE_FILL_FLASH_G120,
            requested_video_light_mode=VIDEO_LIGHT_REC_LINK_G120,
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE286,
        )
        self.assertTrue(res_cam.valid, msg=res_cam.errors)
        self.assertEqual(res_cam.effective_iso_range_min, 200)
        self.assertEqual(res_cam.effective_iso_range_max, 12800)
        self.assertTrue(res_cam.iso_range_limit_survived_cam_reset)
        self.assertEqual(res_cam.effective_exp_comp_set, EXP_COMP_SET_AMBIENT_ONLY_G120)
        self.assertTrue(res_cam.exp_comp_set_survived_cam_reset)
        self.assertEqual(res_cam.effective_iso_auto_min_ss, ISO_AUTO_MIN_SS_STANDARD_G120)
        self.assertEqual(res_cam.effective_flash_mode, FLASH_MODE_AUTOFLASH_G120)
        self.assertEqual(res_cam.flash_comp_ev, 0.0)
        self.assertEqual(res_cam.effective_video_light_mode, VIDEO_LIGHT_POWER_LINK_G120)

    def test_32_g120_initialize_resets_iso_range_limit_and_exp_comp_set(self) -> None:
        res_init = verify_iso_minss_and_flash_guard(
            requested_iso_range_min=400,
            requested_iso_range_max=6400,
            requested_iso_value=800,
            requested_exp_comp_set=EXP_COMP_SET_AMBIENT_ONLY_G120,
            reset_action=RESET_ACTION_INITIALIZE_PHASE286,
        )
        self.assertTrue(res_init.valid)
        self.assertEqual(res_init.effective_iso_range_min, ISO_DEFAULT_STILL_MIN_G120)
        self.assertEqual(res_init.effective_iso_range_max, ISO_DEFAULT_STILL_MAX_G120)
        self.assertEqual(res_init.effective_exp_comp_set, EXP_COMP_SET_AMBIENT_AND_FLASH_G120)

    def test_33_g120_iso_range_bounds_manual_violation_and_spoofs_blocked(self) -> None:
        for bad_kw in (
            {"requested_iso_range_min": 25, "requested_iso_range_max": 12800},
            {"requested_iso_range_min": 100, "requested_iso_range_max": 819200},
            {"requested_iso_range_min": 6400, "requested_iso_range_max": 800},
            {"requested_iso_range_min": 200, "requested_iso_range_max": 3200, "requested_iso_value": 6400},
            {"claimed_camera_reset_resets_iso_range_limit": True},
            {"claimed_camera_reset_resets_exp_comp_set": True},
        ):
            res = verify_iso_minss_and_flash_guard(**bad_kw)
            self.assertFalse(res.valid, msg=bad_kw)
            self.assertEqual(res.status, STATUS_BLOCKED_G120_ISO_RANGE_OR_RESET_PERSISTENCE_VIOLATION)

    def test_34_g120_all_5_flash_modes_allowed_in_still_mechanical_shutter(self) -> None:
        for fm in FX3_EXACT_5_FLASH_MODES_G120:
            res = verify_iso_minss_and_flash_guard(
                shoot_mode=SHOOT_MODE_M_PHASE286,
                shutter_type=SHUTTER_TYPE_MECHANICAL_G120,
                silent_mode="Off",
                flash_requested=(fm != FLASH_MODE_FLASH_OFF_G120),
                requested_flash_mode=fm,
                shutter_speed_seconds=1.0 / 250.0,
            )
            self.assertTrue(res.valid, msg=f"{fm}: {res.errors}")
            self.assertEqual(res.effective_flash_mode, fm)

    def test_35_g120_flash_blocked_in_movie_sq_eshutter_and_silent_mode(self) -> None:
        for bad_kw in (
            {"shoot_mode": SHOOT_MODE_MOVIE_PHASE286, "flash_requested": True, "requested_flash_mode": FLASH_MODE_FILL_FLASH_G120},
            {"shoot_mode": SHOOT_MODE_SQ_PHASE286, "flash_requested": True, "requested_flash_mode": FLASH_MODE_AUTOFLASH_G120},
            {"shoot_mode": SHOOT_MODE_M_PHASE286, "shutter_type": SHUTTER_TYPE_ELECTRONIC_G120, "flash_requested": True, "requested_flash_mode": FLASH_MODE_FILL_FLASH_G120},
            {"shoot_mode": SHOOT_MODE_M_PHASE286, "silent_mode": "On", "flash_requested": True, "requested_flash_mode": FLASH_MODE_REAR_SYNC_G120},
            {"claimed_flash_allowed_in_movie_or_sq": True},
            {"claimed_flash_allowed_with_electronic_shutter": True},
            {"claimed_flash_allowed_with_silent_mode_on": True},
            {"claimed_fx6_has_still_flash_stack": True},
        ):
            res = verify_iso_minss_and_flash_guard(**bad_kw)
            self.assertFalse(res.valid, msg=bad_kw)
            self.assertEqual(res.status, STATUS_BLOCKED_G120_FLASH_MOVIE_ESHUTTER_OR_HV_SHOE_VIOLATION)

    def test_36_g120_flash_sync_1_250_ceiling_and_hss_override(self) -> None:
        res_fast = verify_iso_minss_and_flash_guard(
            flash_requested=True,
            requested_flash_mode=FLASH_MODE_FILL_FLASH_G120,
            shutter_speed_seconds=1.0 / 320.0,
            hss_external_flash=False,
        )
        self.assertFalse(res_fast.valid)
        self.assertEqual(res_fast.status, STATUS_BLOCKED_G120_FLASH_MOVIE_ESHUTTER_OR_HV_SHOE_VIOLATION)

        res_hss = verify_iso_minss_and_flash_guard(
            flash_requested=True,
            requested_flash_mode=FLASH_MODE_FILL_FLASH_G120,
            shutter_speed_seconds=1.0 / 1000.0,
            hss_external_flash=True,
        )
        self.assertTrue(res_hss.valid, msg=res_hss.errors)

    def test_37_g120_mi_shoe_250v_and_negative_polarity_guard(self) -> None:
        res_ok = verify_iso_minss_and_flash_guard(
            mi_shoe_trigger_voltage_v=249.9,
            mi_shoe_positive_polarity=True,
        )
        self.assertTrue(res_ok.valid)

        for bad_v, bad_pol in ((250.0, True), (320.0, True), (5.0, False)):
            res_bad = verify_iso_minss_and_flash_guard(
                mi_shoe_trigger_voltage_v=bad_v,
                mi_shoe_positive_polarity=bad_pol,
            )
            self.assertFalse(res_bad.valid, msg=f"v={bad_v}, pol={bad_pol}")
            self.assertEqual(res_bad.status, STATUS_BLOCKED_G120_FLASH_MOVIE_ESHUTTER_OR_HV_SHOE_VIOLATION)

    def test_38_g120_flash_comp_bounds_and_video_light_across_all_modes(self) -> None:
        for ev in (FLASH_COMP_MIN_EV_G120, 0.0, FLASH_COMP_MAX_EV_G120):
            res_ok = verify_iso_minss_and_flash_guard(flash_comp_ev=ev)
            self.assertTrue(res_ok.valid, msg=ev)

        for bad_ev in (-3.3, 3.3):
            res_bad = verify_iso_minss_and_flash_guard(flash_comp_ev=bad_ev)
            self.assertFalse(res_bad.valid, msg=bad_ev)
            self.assertEqual(res_bad.status, STATUS_BLOCKED_G120_VIDEO_LIGHT_OR_FLASH_COMP_VIOLATION)

        for sm in (SHOOT_MODE_M_PHASE286, SHOOT_MODE_MOVIE_PHASE286, SHOOT_MODE_SQ_PHASE286):
            for vl in FX3_EXACT_4_VIDEO_LIGHT_MODES_G120:
                res_vl = verify_iso_minss_and_flash_guard(
                    shoot_mode=sm,
                    requested_video_light_mode=vl,
                )
                self.assertTrue(res_vl.valid, msg=f"{sm}/{vl}: {res_vl.errors}")
                self.assertTrue(res_vl.video_light_active_across_still_movie_sq)
                self.assertEqual(res_vl.effective_video_light_mode, vl)

        res_blk = verify_iso_minss_and_flash_guard(claimed_video_light_blocked_in_movie=True)
        self.assertFalse(res_blk.valid)
        self.assertEqual(res_blk.status, STATUS_BLOCKED_G120_VIDEO_LIGHT_OR_FLASH_COMP_VIOLATION)

    def test_39_g120_384_state_matrix_invariants(self) -> None:
        m = compute_iso_minss_and_flash_matrix()
        self.assertEqual(m["states_checked"], 384)
        self.assertEqual(m["iso_auto_min_ss_active_states"], 48)
        self.assertEqual(m["cine_ei_base_iso_pinned_states"], 192)
        self.assertEqual(m["flash_available_states"], 72)
        self.assertEqual(m["non_resettable_survived_cam_reset_states"], 128)
        self.assertTrue(m["all_invariants_hold"])

    def test_40_g120_invalid_telemetry_and_persistent_write_blocked(self) -> None:
        for bad_kw in (
            {"body_model_name": FX6_MODEL_NAME_PHASE286},
            {"body_model_id": False},
            {"shoot_mode": "InvalidMode"},
            {"log_shooting": "S-Log2"},
            {"requested_iso_auto_min_ss": "InvalidMinSS"},
            {"shutter_type": "Auto"},
            {"requested_flash_mode": "Strobe"},
            {"requested_iso_value": 0},
            {"mi_shoe_trigger_voltage_v": -1.0},
            {"shutter_speed_seconds": 0.0},
        ):
            res = verify_iso_minss_and_flash_guard(**bad_kw)
            self.assertFalse(res.valid, msg=bad_kw)
            self.assertEqual(res.status, STATUS_BLOCKED_G120_TELEMETRY_INVALID)

        verdict, gres = evaluate_g120_iso_minss_and_flash_guard(
            force_clean_room=True,
            request_persistent_emmc_writes=True,
        )
        self.assertFalse(verdict.passed)
        self.assertFalse(gres.valid)
        self.assertEqual(verdict.status, "BLOCKED_BY_PERSISTENT_EMMC_WRITE_REDLINE")

    # --- 4. Unified 120-Gate Preflight (`evaluate_120gate_preflight`, Tests 41-55) ---

    def test_41_master_120_offline_mode_117_of_120_with_mocked_upstream(self) -> None:
        rep = evaluate_120gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=False,
            master_118_override=self.clean_offline_118,
        )
        self.assertIsInstance(rep, Master120GateReport)
        self.assertEqual(rep.status, "VERIFIED_117_OF_120_AWAITING_PHYSICAL_TIER0")
        self.assertEqual(rep.summary["total_gates"], 120)
        self.assertEqual(rep.summary["verified_gates"], 117)
        self.assertEqual(rep.summary["blocked_or_pending_gates"], 3)
        self.assertEqual(rep.summary["g01_to_g12_verified"], 9)
        self.assertEqual(rep.summary["g13_to_g118_verified"], 106)
        self.assertEqual(rep.summary["g119_to_g120_verified"], 2)
        self.assertTrue(rep.offline_117_gates_verified)
        self.assertFalse(rep.all_120_gates_verified)
        self.assertTrue(rep.g13_to_g120_all_passed)
        self.assertTrue(rep.g119_to_g120_all_passed)
        self.assertTrue(rep.h0_h1_trial_entry_allowed)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertEqual(len(rep.gates), 120)

    def test_42_master_120_dry_run_mode_120_of_120_and_redlines_locked(self) -> None:
        rep = evaluate_120gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            master_118_override=self.clean_dryrun_118,
        )
        self.assertEqual(rep.status, "VERIFIED_ALL_120_GATES_DRY_RUN_SIMULATED_BACKUP")
        self.assertTrue(rep.all_120_gates_verified)
        self.assertTrue(rep.dry_run_rehearsal_only)
        self.assertEqual(rep.summary["verified_gates"], 120)
        self.assertEqual(rep.summary["blocked_or_pending_gates"], 0)
        self.assertEqual(rep.summary["g01_to_g12_verified"], 12)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.hardware_live_attachment_authorized)
        self.assertFalse(rep.el3_payload_transmit_authorized)
        self.assertFalse(rep.spi_nor_write_authorized)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertEqual(rep.usb_packets_transmitted, 0)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_43_master_120_simulate_bench_dry_run_flag_alias(self) -> None:
        rep = evaluate_120gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            simulate_bench_dry_run=True,
            master_118_override=self.clean_dryrun_118,
        )
        self.assertTrue(rep.all_120_gates_verified)
        self.assertTrue(rep.dry_run_rehearsal_only)

    def test_44_master_120_propagates_g119_and_g120_failures(self) -> None:
        rep119 = evaluate_120gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            focus_area_zoom_kwargs={"claimed_xlr_h1_has_zoom_lever": True},
            master_118_override=self.clean_dryrun_118,
        )
        self.assertEqual(rep119.status, STATUS_BLOCKED_G119_XLRH1_FAKE_HANDLE_ZOOM_SPOOF_VIOLATION)
        self.assertFalse(rep119.g119_to_g120_all_passed)
        self.assertFalse(rep119.all_120_gates_verified)

        rep120 = evaluate_120gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            iso_minss_flash_kwargs={"mi_shoe_trigger_voltage_v": 300.0},
            master_118_override=self.clean_dryrun_118,
        )
        self.assertEqual(rep120.status, STATUS_BLOCKED_G120_FLASH_MOVIE_ESHUTTER_OR_HV_SHOE_VIOLATION)
        self.assertFalse(rep120.g119_to_g120_all_passed)
        self.assertFalse(rep120.all_120_gates_verified)

    def test_45_master_120_propagates_upstream_g118_failure(self) -> None:
        broken_118 = dataclasses.replace(
            self.clean_dryrun_118,
            g13_to_g118_all_passed=False,
            status="BLOCKED_G118_FX3_SHUTTER_TYPE_AUTO_SPOOF_VIOLATION",
        )
        rep = evaluate_120gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            master_118_override=broken_118,
        )
        self.assertEqual(rep.status, "BLOCKED_G118_FX3_SHUTTER_TYPE_AUTO_SPOOF_VIOLATION")
        self.assertFalse(rep.g13_to_g120_all_passed)
        self.assertFalse(rep.all_120_gates_verified)

    def test_46_master_120_blocks_persistent_emmc_write_request(self) -> None:
        rep = evaluate_120gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            request_persistent_emmc_writes=True,
            master_118_override=self.clean_dryrun_118,
        )
        self.assertEqual(rep.status, "BLOCKED_BY_PERSISTENT_EMMC_WRITE_REDLINE")
        self.assertFalse(rep.all_120_gates_verified)
        self.assertFalse(rep.h0_h1_trial_entry_allowed)

    def test_47_master_120_gate_sequence_g117_g118_g119_g120_exact(self) -> None:
        rep = evaluate_120gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            master_118_override=self.clean_dryrun_118,
        )
        self.assertEqual(rep.gates[-1]["gate_id"], G120_GATE_ID)
        self.assertEqual(rep.gates[-2]["gate_id"], G119_GATE_ID)
        self.assertEqual(
            rep.gates[-3]["gate_id"],
            "G118_shutter_type_flash_sync_electronic_5lock_nr_and_drive_guard",
        )
        self.assertEqual(
            rep.gates[-4]["gate_id"],
            "G117_raw_heif_hlg_still_and_colorspace_adobergb_prefix_guard",
        )

    def test_48_master_120_to_dict_is_json_serializable(self) -> None:
        rep = evaluate_120gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=False,
            master_118_override=self.clean_offline_118,
        )
        loaded = json.loads(json.dumps(rep.to_dict()))
        self.assertEqual(loaded["summary"]["total_gates"], 120)
        self.assertEqual(loaded["summary"]["verified_gates"], 117)
        self.assertEqual(loaded["summary"]["g119_to_g120_verified"], 2)

    def test_49_master_120_full_live_stack_without_override(self) -> None:
        rep_off = evaluate_120gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=False,
        )
        self.assertTrue(rep_off.offline_117_gates_verified)
        self.assertEqual(rep_off.summary["verified_gates"], 117)
        self.assertEqual(rep_off.status, "VERIFIED_117_OF_120_AWAITING_PHYSICAL_TIER0")

        rep_dry = evaluate_120gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
        )
        self.assertTrue(rep_dry.all_120_gates_verified)
        self.assertEqual(rep_dry.summary["verified_gates"], 120)
        self.assertEqual(rep_dry.status, "VERIFIED_ALL_120_GATES_DRY_RUN_SIMULATED_BACKUP")

    def test_50_fx3_clean_room_test_and_force_clean_room_env_in_master_120(self) -> None:
        for env_key in (ENV_CLEAN_ROOM_TEST_PHASE286, "FX3_FX6_FORCE_CLEAN_ROOM"):
            with mock.patch.dict(os.environ, {env_key: "1"}):
                self.assertTrue(_is_forced_clean_room())
                rep = evaluate_120gate_preflight(
                    master_118_override=self.clean_offline_118,
                )
                self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
                self.assertTrue(rep.clean_room_forced)

    # --- 5. Exhaustive Domain & Edge-Case Coverage (Tests 51-68) ---

    def test_51_all_g119_and_g120_reset_actions_accepted(self) -> None:
        for r_act in ALLOWED_RESET_ACTIONS_PHASE286:
            r1 = verify_focus_area_and_zoom_lever_guard(reset_action=r_act)
            self.assertTrue(r1.valid, msg=r_act)
            self.assertEqual(r1.reset_action, r_act)
            r2 = verify_iso_minss_and_flash_guard(reset_action=r_act)
            self.assertTrue(r2.valid, msg=r_act)
            self.assertEqual(r2.reset_action, r_act)

    def test_52_all_8_shoot_modes_handled_without_telemetry_error(self) -> None:
        self.assertEqual(len(ALLOWED_SHOOT_MODES_PHASE286), 8)
        for sm in ALLOWED_SHOOT_MODES_PHASE286:
            r1 = verify_focus_area_and_zoom_lever_guard(shoot_mode=sm)
            self.assertTrue(r1.valid, msg=sm)
            r2 = verify_iso_minss_and_flash_guard(shoot_mode=sm)
            self.assertTrue(r2.valid, msg=sm)

    def test_53_g119_intelligent_auto_forces_wide_focus_area(self) -> None:
        r = resolve_fx3_focus_area_and_zoom_lever_state(
            shoot_mode=SHOOT_MODE_INTELLIGENT_AUTO_PHASE286,
            requested_focus_area=FOCUS_AREA_SPOT_L_G119,
        )
        self.assertEqual(r["effective_focus_area"], FOCUS_AREA_WIDE_G119)

    def test_54_g119_switch_vh_reset_behavior_and_movie_lockout(self) -> None:
        r_mv = resolve_fx3_focus_area_and_zoom_lever_state(
            shoot_mode=SHOOT_MODE_MOVIE_PHASE286,
            requested_switch_vh_af_area=SWITCH_VH_AF_POINT_ONLY_G119,
        )
        self.assertEqual(r_mv["switch_vh_af_area"], SWITCH_VH_OFF_G119)

        r_rst = resolve_fx3_focus_area_and_zoom_lever_state(
            shoot_mode=SHOOT_MODE_M_PHASE286,
            requested_switch_vh_af_area=SWITCH_VH_AF_POINT_PLUS_AREA_G119,
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE286,
        )
        self.assertEqual(r_rst["switch_vh_af_area"], SWITCH_VH_OFF_G119)

    def test_55_g119_zoom_lever_and_remote_speeds_reset_on_cam_reset(self) -> None:
        r = resolve_fx3_focus_area_and_zoom_lever_state(
            zoom_lever_1st_speed_stby=7,
            zoom_lever_2nd_speed_stby=2,
            custom_key_z_speed_stby=8,
            remote_zoom_speed_type=REMOTE_ZOOM_SPEED_TYPE_FIXED_G119,
            remote_zoom_fixed_speed_stby=6,
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE286,
        )
        self.assertEqual(r["zoom_lever_1st_speed_stby"], ZOOM_LEVER_1ST_DEFAULT_G119)
        self.assertEqual(r["zoom_lever_2nd_speed_stby"], ZOOM_LEVER_2ND_DEFAULT_G119)
        self.assertEqual(r["custom_key_z_speed_stby"], CUSTOM_KEY_Z_SPEED_DEFAULT_G119)
        self.assertEqual(r["remote_zoom_speed_type"], REMOTE_ZOOM_SPEED_TYPE_VARIABLE_G119)
        self.assertEqual(r["remote_zoom_fixed_speed_stby"], REMOTE_ZOOM_FIXED_SPEED_DEFAULT_G119)

    def test_56_g119_network_reset_preserves_focus_and_zoom_settings(self) -> None:
        res = verify_focus_area_and_zoom_lever_guard(
            requested_focus_area=FOCUS_AREA_ZONE_G119,
            requested_focus_area_color=FOCUS_AREA_COLOR_RED_G119,
            requested_zoom_range=ZOOM_RANGE_CLEAR_IMAGE_G119,
            reset_action=RESET_ACTION_RESET_NETWORK_SET_PHASE286,
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.effective_focus_area, FOCUS_AREA_ZONE_G119)
        self.assertEqual(res.focus_area_color, FOCUS_AREA_COLOR_RED_G119)
        self.assertEqual(res.effective_zoom_range, ZOOM_RANGE_CLEAR_IMAGE_G119)

    def test_57_g119_enum_tuples_exact_cardinalities(self) -> None:
        self.assertEqual(len(ALLOWED_FOCUS_MODES_G119), 5)
        self.assertEqual(len(ALLOWED_FOCUS_AREA_COLORS_G119), 2)
        self.assertEqual(len(ALLOWED_CIRC_FOCUS_POINT_MODES_G119), 2)
        self.assertEqual(len(ALLOWED_SWITCH_VH_MODES_G119), 3)
        self.assertEqual(len(ALLOWED_ZOOM_RANGES_G119), 3)
        self.assertEqual(len(ALLOWED_REMOTE_ZOOM_SPEED_TYPES_G119), 2)

    def test_58_g120_iso_range_limit_accepts_full_50_to_409600_hardware_span(self) -> None:
        res = verify_iso_minss_and_flash_guard(
            requested_iso_range_min=ISO_HARDWARE_MIN_G120,
            requested_iso_range_max=ISO_HARDWARE_MAX_G120,
            requested_iso_value=409600,
        )
        self.assertTrue(res.valid, msg=res.errors)
        self.assertEqual(res.effective_iso_range_min, 50)
        self.assertEqual(res.effective_iso_range_max, 409600)

    def test_59_g120_flexible_iso_is_not_base_iso_pinned(self) -> None:
        res = verify_iso_minss_and_flash_guard(
            shoot_mode=SHOOT_MODE_MOVIE_PHASE286,
            log_shooting=LOG_SHOOTING_FLEXIBLE_ISO_G120,
            requested_iso_value=1600,
        )
        self.assertTrue(res.valid, msg=res.errors)
        self.assertFalse(res.cine_ei_base_iso_pinned)
        self.assertIsNone(res.effective_base_iso)

    def test_60_g120_all_manual_min_ss_shutter_tokens_valid_in_still_a(self) -> None:
        for tok in ISO_AUTO_MIN_SS_MANUAL_SHUTTER_TOKENS_G120:
            res = verify_iso_minss_and_flash_guard(
                shoot_mode=SHOOT_MODE_A_PHASE286,
                iso_mode="ISO AUTO",
                requested_iso_auto_min_ss=tok,
            )
            self.assertTrue(res.valid, msg=tok)
            self.assertEqual(res.effective_iso_auto_min_ss, tok)
            self.assertTrue(res.iso_auto_min_ss_active)

    def test_61_g120_wireless_flash_and_red_eye_reset_on_cam_reset(self) -> None:
        r = resolve_fx3_iso_minss_and_flash_state(
            wireless_flash="On",
            red_eye_reduction="On",
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE286,
        )
        self.assertEqual(r["wireless_flash"], "Off")
        self.assertEqual(r["red_eye_reduction"], "Off")

    def test_62_g120_network_reset_preserves_iso_range_and_flash(self) -> None:
        res = verify_iso_minss_and_flash_guard(
            requested_iso_range_min=160,
            requested_iso_range_max=25600,
            requested_iso_value=800,
            requested_flash_mode=FLASH_MODE_SLOW_SYNC_G120,
            requested_exp_comp_set=EXP_COMP_SET_AMBIENT_ONLY_G120,
            reset_action=RESET_ACTION_RESET_NETWORK_SET_PHASE286,
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.effective_iso_range_min, 160)
        self.assertEqual(res.effective_flash_mode, FLASH_MODE_SLOW_SYNC_G120)
        self.assertEqual(res.effective_exp_comp_set, EXP_COMP_SET_AMBIENT_ONLY_G120)

    def test_63_g120_enum_tuples_and_menu_paths(self) -> None:
        self.assertEqual(len(ALLOWED_LOG_SHOOTING_MODES_G120), 4)
        self.assertEqual(len(ALLOWED_EXP_COMP_SET_MODES_G120), 2)
        self.assertIn("[Focus Area]", FOCUS_AREA_MENU_PATH_G119)
        self.assertIn("[AF Area Registration]", AF_AREA_REG_MENU_PATH_G119)
        self.assertIn("[ISO Range Limit]", ISO_RANGE_LIMIT_MENU_PATH_G120)
        self.assertIn("[ISO AUTO Min. SS]", ISO_AUTO_MIN_SS_MENU_PATH_G120)
        self.assertIn("[Flash Mode]", FLASH_MODE_MENU_PATH_G120)

    def test_64_g119_all_7_tracking_aliases_with_colons_normalized(self) -> None:
        for short, colon in (
            (FOCUS_AREA_TRACKING_SPOT_S_G119, "Tracking: Spot: S"),
            (FOCUS_AREA_TRACKING_SPOT_M_G119, "Tracking: Spot: M"),
            (FOCUS_AREA_TRACKING_SPOT_L_G119, "Tracking: Spot: L"),
        ):
            res = verify_focus_area_and_zoom_lever_guard(
                shoot_mode=SHOOT_MODE_M_PHASE286,
                focus_mode=AF_FOCUS_MODE_AF_C_G119,
                requested_focus_area=colon,
            )
            self.assertTrue(res.valid, msg=colon)
            self.assertEqual(res.effective_focus_area, short)

    def test_65_g119_to_dict_serializable(self) -> None:
        verdict, res = evaluate_g119_focus_area_and_zoom_lever_guard(force_clean_room=True)
        self.assertTrue(verdict.passed)
        loaded = json.loads(json.dumps(res.to_dict()))
        self.assertEqual(loaded["status"], STATUS_VERIFIED_G119)

    def test_66_g120_to_dict_serializable(self) -> None:
        verdict, res = evaluate_g120_iso_minss_and_flash_guard(force_clean_room=True)
        self.assertTrue(verdict.passed)
        loaded = json.loads(json.dumps(res.to_dict()))
        self.assertEqual(loaded["status"], STATUS_VERIFIED_G120)

    def test_67_g119_evidence_string_contains_key_tokens(self) -> None:
        verdict, _res = evaluate_g119_focus_area_and_zoom_lever_guard(force_clean_room=True)
        self.assertIn("14opt=14", verdict.evidence)
        self.assertIn("trk_still_only=7", verdict.evidence)
        self.assertIn("xlr_h1_zoom_lever=False", verdict.evidence)

    def test_68_g120_evidence_string_contains_key_tokens(self) -> None:
        verdict, _res = evaluate_g120_iso_minss_and_flash_guard(force_clean_room=True)
        self.assertIn("iso_range=(80..102400)", verdict.evidence)
        self.assertIn("sync<=1/250", verdict.evidence)
        self.assertIn("fx6_flash=False", verdict.evidence)

    # --- 6. CLI & Cross-Platform CI Portability Tests (Tests 69-80) ---

    def test_69_cli_verify_g119_text_and_json(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cli_main(["verify-focus-area-and-zoom-lever-guard", "--force-clean-room"])
        self.assertEqual(rc, 0)
        self.assertIn("gate=G119_", buf.getvalue())
        self.assertIn("14opt=14", buf.getvalue())
        self.assertIn("xlr_h1_zoom_lever=False", buf.getvalue())

        jbuf = io.StringIO()
        with contextlib.redirect_stdout(jbuf):
            rc_j = cli_main(
                ["verify-g119-focus-area-zoom-lever", "--force-clean-room", "--json"]
            )
        self.assertEqual(rc_j, 0)
        data = json.loads(jbuf.getvalue())
        self.assertTrue(data["valid"])
        self.assertEqual(data["status"], STATUS_VERIFIED_G119)

    def test_70_cli_verify_g120_text_and_json(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cli_main(["verify-iso-minss-and-flash-guard", "--force-clean-room"])
        self.assertEqual(rc, 0)
        self.assertIn("gate=G120_", buf.getvalue())
        self.assertIn("sync<=1/250", buf.getvalue())
        self.assertIn("fx6_still_flash=False", buf.getvalue())

        jbuf = io.StringIO()
        with contextlib.redirect_stdout(jbuf):
            rc_j = cli_main(
                ["verify-g120-iso-minss-flash", "--force-clean-room", "--json"]
            )
        self.assertEqual(rc_j, 0)
        data = json.loads(jbuf.getvalue())
        self.assertTrue(data["valid"])
        self.assertEqual(data["status"], STATUS_VERIFIED_G120)

    def test_71_cli_verify_120_gates_offline_text_and_json(self) -> None:
        offline_120 = evaluate_120gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=False,
            master_118_override=self.clean_offline_118,
        )
        with mock.patch(
            "fx3_safety.__main__.evaluate_120gate_preflight",
            return_value=offline_120,
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = cli_main(["verify-120-gates", "--force-clean-room"])
            self.assertEqual(rc, 0)
            self.assertIn("verified=117/120", buf.getvalue())
            self.assertIn("overall_ready_for_hardware_attach=False", buf.getvalue())

            jbuf = io.StringIO()
            with contextlib.redirect_stdout(jbuf):
                rc_j = cli_main(["verify-120-gates", "--force-clean-room", "--json"])
            self.assertEqual(rc_j, 0)
            parsed = json.loads(jbuf.getvalue())
            self.assertEqual(parsed["summary"]["verified_gates"], 117)
            self.assertTrue(parsed["offline_117_gates_verified"])

    def test_72_cli_verify_120_gates_dry_run_text_and_json(self) -> None:
        dryrun_120 = evaluate_120gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            master_118_override=self.clean_dryrun_118,
        )
        with mock.patch(
            "fx3_safety.__main__.evaluate_120gate_preflight",
            return_value=dryrun_120,
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = cli_main(
                    ["verify-120-gates", "--force-clean-room", "--simulate-bench-dry-run"]
                )
            self.assertEqual(rc, 0)
            self.assertIn("verified=120/120", buf.getvalue())

            jbuf = io.StringIO()
            with contextlib.redirect_stdout(jbuf):
                rc_j = cli_main(
                    [
                        "verify-120-gates",
                        "--force-clean-room",
                        "--simulate-bench-dry-run",
                        "--json",
                    ]
                )
            self.assertEqual(rc_j, 0)
            parsed = json.loads(jbuf.getvalue())
            self.assertTrue(parsed["all_120_gates_verified"])
            self.assertEqual(parsed["summary"]["verified_gates"], 120)

    def test_73_standalone_module_main_offline_and_dry_run(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = module_main(["--force-clean-room"])
        self.assertEqual(rc, 0)
        self.assertIn("verified=117/120", buf.getvalue())

        jbuf = io.StringIO()
        with contextlib.redirect_stdout(jbuf):
            rc_j = module_main(
                ["--force-clean-room", "--simulate-bench-dry-run", "--json"]
            )
        self.assertEqual(rc_j, 0)
        self.assertTrue(json.loads(jbuf.getvalue())["all_120_gates_verified"])

    def test_74_subprocess_cli_verify_g119_g120_uses_sys_executable(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONPATH"] = str(DEFAULT_REPO_ROOT / "outputs" / "fx3-safety")
        for cmd, expected_status in (
            ("verify-focus-area-and-zoom-lever-guard", STATUS_VERIFIED_G119),
            ("verify-iso-minss-and-flash-guard", STATUS_VERIFIED_G120),
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

    def test_75_subprocess_cli_verify_120_gates_uses_sys_executable(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONPATH"] = str(DEFAULT_REPO_ROOT / "outputs" / "fx3-safety")
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "fx3_safety",
                "verify-120-gates",
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
        self.assertTrue(payload["all_120_gates_verified"])
        self.assertEqual(payload["summary"]["verified_gates"], 120)
        self.assertEqual(payload["raw_firmware_bytes_leaked"], 0)

    def test_76_subprocess_cli_verify_120_gates_offline_uses_sys_executable(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONPATH"] = str(DEFAULT_REPO_ROOT / "outputs" / "fx3-safety")
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "fx3_safety",
                "verify-120-gates",
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
        self.assertTrue(payload["offline_117_gates_verified"])
        self.assertFalse(payload["all_120_gates_verified"])
        self.assertEqual(payload["summary"]["verified_gates"], 117)

    def test_77_argparse_help_and_upstream_verify_118_gates_parity(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONPATH"] = str(DEFAULT_REPO_ROOT / "outputs" / "fx3-safety")
        for subcmd in (
            "verify-focus-area-and-zoom-lever-guard",
            "verify-iso-minss-and-flash-guard",
            "verify-120-gates",
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
            "fx3_safety.__main__.evaluate_118gate_preflight",
            return_value=self.clean_offline_118,
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = cli_main(["verify-118-gates", "--force-clean-room"])
        self.assertEqual(rc, 0)
        self.assertIn("verified=115/118", buf.getvalue())

    def test_78_standalone_script_help_exits_zero_python314_percent_safe(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONPATH"] = str(DEFAULT_REPO_ROOT / "outputs" / "fx3-safety")
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "fx3_safety.realhw_focus_area_zoom_lever_iso_minss_flash_and_120gate_guard",
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
        self.assertIn("phase 286", proc.stdout.lower())
        self.assertIn("120-gate", proc.stdout.lower())

    def test_79_g119_circulate_only_applies_to_10_expected_areas(self) -> None:
        self.assertEqual(
            CIRCULATING_FOCUS_AREAS_G119,
            (
                FOCUS_AREA_ZONE_G119,
                FOCUS_AREA_SPOT_S_G119,
                FOCUS_AREA_SPOT_M_G119,
                FOCUS_AREA_SPOT_L_G119,
                FOCUS_AREA_EXPAND_SPOT_G119,
                FOCUS_AREA_TRACKING_ZONE_G119,
                FOCUS_AREA_TRACKING_SPOT_S_G119,
                FOCUS_AREA_TRACKING_SPOT_M_G119,
                FOCUS_AREA_TRACKING_SPOT_L_G119,
                FOCUS_AREA_TRACKING_EXPAND_SPOT_G119,
            ),
        )
        res = verify_focus_area_and_zoom_lever_guard(
            requested_circ_of_focus_point=CIRC_CIRCULATE_G119,
            requested_focus_area=FOCUS_AREA_SPOT_S_G119,
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.circ_of_focus_point, CIRC_CIRCULATE_G119)

    def test_80_g120_std_alias_for_iso_auto_min_ss_standard_normalized(self) -> None:
        res = verify_iso_minss_and_flash_guard(
            shoot_mode=SHOOT_MODE_P_PHASE286,
            iso_mode="ISO AUTO",
            requested_iso_auto_min_ss="STD",
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.effective_iso_auto_min_ss, ISO_AUTO_MIN_SS_STANDARD_G120)
        self.assertTrue(res.iso_auto_min_ss_active)


if __name__ == "__main__":
    unittest.main()
