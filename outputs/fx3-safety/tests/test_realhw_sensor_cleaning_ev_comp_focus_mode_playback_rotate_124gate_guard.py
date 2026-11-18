"""Phase 290 (290th Phase Milestone, Wave-52) Dual-Mode Unit Tests (82 tests) for
`fx3_safety.realhw_sensor_cleaning_ev_comp_focus_mode_playback_rotate_and_124gate_guard`:

- Gate `G123` (`GATE_G123_SENSOR_CLEANING_EV_COMP_AND_CINE_EI_GUARD`):
  - `[Sensor Cleaning]` (`_f.uxc` `0x67d6`, legacy `.uxc` `0xe7d7` `Cleaning Mode`,
    `FUNC_set_cleaning_mode`): `NP-FZ100 >= 51%` remaining battery (`>= 3` bars pre-Ver. 2.00;
    `< 51%` rejected fail-closed via `INSUFFICIENT_BATTERY_CLEANING_MODE` / `Power insufficient.`
    `.uxc` `0xe574`), 5-axis IBIS carriage vibrate/center, mandatory physical power-switch
    `OFF` (`_g.uxc` `0x6221`), manual blower only (no compressed air), forbidden during active
    Tier-0 `p3` backup or open mount (`STATUS_BLOCKED_G123_CLEANING_LOW_BATTERY_OR_ACTIVE_MOUNT_VIOLATION`).
  - `ILME-FX6 Ver. 6.01` contrast: zero IBIS, front electronic Variable ND (`1/4..1/128` +
    `CLEAR`) optical assembly, `Technical > APR`, and `CrCommandId_SensorCleaning` (`320`)
    unsupported (`STATUS_BLOCKED_G123_FX6_END_CLEANING_OR_IBIS_SPOOF_VIOLATION`).
  - `[Exposure Comp.]` (`_f.uxc` `0x76de`): Still `-5.0..+5.0 EV` vs Movie/`S&Q`
    `-2.0..+2.0 EV`, `[Exposure step]` (`0.3EV` default / `0.5EV`, survives `Camera Settings Reset`),
    `Exposure Std. Adjust` (`-1..+1 EV` in `1/6 EV` steps), active in `M` ONLY when `ISO = ISO AUTO`
    (locked out in `iAuto` and `M` + fixed ISO), dormant Alpha `[Reset EV Comp.]` omitted from
    dial-less FX3 `ilc/2210`, and **100% locked out under `[Log Shooting] = Cine EI` or
    `Cine EI Quick`** (hard-locks `EXPOSURE_MODE_MOVIE_M` + `Base ISO 800/12800`), across
    `384` matrix states.
- Gate `G124` (`GATE_G124_FOCUS_MODE_AND_PLAYBACK_ROTATE_SLOT1_GUARD`):
  - `[Focus Mode]` Still 5-Mode (`Single-shot AF`, default `Automatic AF`, `Continuous AF`,
    `DMF`, `Manual Focus`; dormant `PF`/`SEMI_MANUAL` blocked) vs Movie/`S&Q` strict 2-Mode
    (`Continuous AF` encoded internally as `MOVIE_AUTO` + `Manual Focus`; `AF-S`/`AF-A`/`DMF`
    rejected in Movie/`S&Q`, `STATUS_BLOCKED_G124_FOCUS_MODE_MOVIE_SPLIT_OR_DORMANT_VIOLATION`).
  - `[AF Assist]` (`_f.uxc` `0x64a9`, strictly Movie `AF-C`/`MOVIE_AUTO`), Still-only
    `[Priority Set in AF-S/AF-C]` (`AF / Release / Balanced Emphasis`, survives
    `Camera Settings Reset`), and Still-only `[AF Illuminator]` (`.uxc` `0xe07f`, locked out
    in Movie/`S&Q`/`AF-C`/Focus Magnifier/Mount Adaptor), vs `FX6` `AF/MF` + `Push AF Mode`.
  - `[Playback]` `[View Mode]` (`Date View`, `Folder View(Still)`, `Movie View`; dormant
    `AVCHD View`/`Folder View(MP4)`/`Mov. View by File Format` blocked), `[Image Index]`
    (`9 Images`, `25 Images`; dormant `12_IMAGES`/`30 Images` `_f.uxc` `0x6e7a` blocked),
    `[Display as Group]` (`Off/On`, group-delete wipes all burst/interval frames),
    `[Display Rotation]` (`Auto/Manual/Off`, `BKID_APP_setting_display_rotatiton`), and
    **`[Rotate]` (`FUNC_rotate_content`) `Slot-1` Read-Only Vault Firewall (`EROFS`/`EBUSY`)**,
    across `384` matrix states.
- Unified `124`-Gate Master Safety Preflight (`evaluate_124gate_preflight` / `verify-124-gates`):
  - `121/124` offline (`VERIFIED_121_OF_124_AWAITING_PHYSICAL_TIER0`) and `124/124` in
    `--simulate-bench-dry-run` (`VERIFIED_ALL_124_GATES_DRY_RUN_SIMULATED_BACKUP`) with all
    hardware write/live-attach/cross-model redlines hard-locked `False`.
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
from fx3_safety.realhw_dci4k_aspect_custom_hold_camset_photo_capture_and_122gate_guard import (
    Master122GateReport,
    evaluate_122gate_preflight,
)
from fx3_safety.realhw_sensor_cleaning_ev_comp_focus_mode_playback_rotate_and_124gate_guard import (
    AF_ASSIST_F_UXC_RESID16_G124,
    AF_A_UXC_RESID16_G124,
    AF_C_UXC_RESID16_G124,
    AF_ILLUMINATOR_AUTO_G124,
    AF_ILLUMINATOR_FACTORY_DEFAULT_G124,
    AF_ILLUMINATOR_OFF_G124,
    AF_ILLUMINATOR_UXC_RESID16_G124,
    AF_PRIORITY_AF_G124,
    AF_PRIORITY_BALANCED_G124,
    AF_PRIORITY_FACTORY_DEFAULT_G124,
    AF_PRIORITY_RELEASE_G124,
    AF_S_UXC_RESID16_G124,
    ALLOWED_AF_ILLUMINATOR_MODES_G124,
    ALLOWED_AF_PRIORITY_MODES_G124,
    ALLOWED_DISPLAY_ROTATION_MODES_G124,
    ALLOWED_EXPOSURE_STEPS_G123,
    ALLOWED_ISO_MODES_G123,
    ALLOWED_LOG_SHOOTING_MODES_G123,
    ALLOWED_RESET_ACTIONS_PHASE290,
    ALLOWED_SHOOT_MODES_PHASE290,
    BALANCED_EMPHASIS_F_UXC_RESID16_G124,
    CINE_EI_BASE_ISOS_G123,
    CINE_EI_EXPOSURE_INDEX_RANGE_BY_BASE_G123,
    CINE_EI_LOCKED_LOG_MODES_G123,
    CLEANING_MODE_LEGACY_UXC_RESID16_G123,
    CROSS_MODEL_FLASH_AUTHORIZED,
    DATE_VIEW_UXC_RESID16_G124,
    DEFAULT_REPO_ROOT,
    DIAL_EV_COMP_UXC_RESID16_G123,
    DISPLAY_AS_GROUP_F_UXC_RESID16_G124,
    DISPLAY_AS_GROUP_MENU_PATH_G124,
    DISPLAY_ROTATION_AUTO_G124,
    DISPLAY_ROTATION_FACTORY_DEFAULT_G124,
    DISPLAY_ROTATION_F_UXC_RESID16_G124,
    DISPLAY_ROTATION_MANUAL_G124,
    DISPLAY_ROTATION_MENU_PATH_G124,
    DISPLAY_ROTATION_OFF_G124,
    DMF_UXC_RESID16_G124,
    DONOR_CHECK_CI_MAX_SECONDS_PHASE290,
    DONOR_CHECK_MAX_SECONDS_PHASE290,
    DORMANT_FOCUS_MODES_G124,
    DORMANT_IMAGE_INDEX_MODES_G124,
    DORMANT_VIEW_MODES_G124,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    ENV_CLEAN_ROOM_TEST_PHASE290,
    EV_COMP_FACTORY_DEFAULT_EV_G123,
    EV_COMP_LIVE_METER_MAX_EV_G123,
    EV_COMP_LIVE_METER_MIN_EV_G123,
    EV_COMP_MOVIE_MAX_EV_G123,
    EV_COMP_MOVIE_MIN_EV_G123,
    EV_COMP_STILL_MAX_EV_G123,
    EV_COMP_STILL_MIN_EV_G123,
    EXPOSURE_COMP_F_UXC_RESID16_G123,
    EXPOSURE_COMP_MENU_PATH_G123,
    EXPOSURE_COMP_UXC_RESID16_G123,
    EXPOSURE_STD_ADJUST_MAX_EV_G123,
    EXPOSURE_STD_ADJUST_MENU_PATH_G123,
    EXPOSURE_STD_ADJUST_MIN_EV_G123,
    EXPOSURE_STD_ADJUST_STEP_DENOM_G123,
    EXPOSURE_STEP_0_3_EV_G123,
    EXPOSURE_STEP_0_5_EV_G123,
    EXPOSURE_STEP_FACTORY_DEFAULT_G123,
    EXPOSURE_STEP_F_UXC_RESID16_G123,
    EXPOSURE_STEP_MENU_PATH_G123,
    FOCUS_MODE_AF_A_G124,
    FOCUS_MODE_AF_C_G124,
    FOCUS_MODE_AF_S_G124,
    FOCUS_MODE_DMF_G124,
    FOCUS_MODE_G_UXC_RESID16_G124,
    FOCUS_MODE_MENU_PATH_G124,
    FOCUS_MODE_MF_G124,
    FOLDER_VIEW_STILL_UXC_RESID16_G124,
    FX3_ACTIVE_2_IMAGE_INDEX_MODES_G124,
    FX3_ACTIVE_3_VIEW_MODES_G124,
    FX3_APPFW_DISPLAY_ROTATION_BKID_G124,
    FX3_DEFAULT_FW_VERSION_PHASE290,
    FX3_HELP_GUIDE_CODE_PHASE290,
    FX3_MODEL_ID_PHASE290,
    FX3_MODEL_NAME_PHASE290,
    FX3_MOVIE_2_FOCUS_MODES_G124,
    FX3_MOVIE_AFC_INTERNAL_ENUM_G124,
    FX3_STILL_5_FOCUS_MODES_G124,
    FX6_CRSDK_SENSOR_CLEANING_CMD_ID_G123,
    FX6_DEFAULT_FW_VERSION_PHASE290,
    FX6_MODEL_NAME_PHASE290,
    FX6_VARIABLE_ND_VALUES_G123,
    FocusModePlaybackRotateGuardResult,
    G123,
    G123SensorCleaningEvCompGuardResult,
    G123_GATE_CODE,
    G123_GATE_ID,
    G124,
    G124FocusModePlaybackRotateGuardResult,
    G124_GATE_CODE,
    G124_GATE_ID,
    GATE_G123_SENSOR_CLEANING_EV_COMP_AND_CINE_EI_GUARD,
    GATE_G124_FOCUS_MODE_AND_PLAYBACK_ROTATE_SLOT1_GUARD,
    HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    HUMAN_HARDWARE_ATTACH_TOKEN,
    IMAGE_INDEX_25_F_UXC_RESID16_G124,
    IMAGE_INDEX_25_G124,
    IMAGE_INDEX_30_DORMANT_F_UXC_RESID16_G124,
    IMAGE_INDEX_9_G124,
    IMAGE_INDEX_9_UXC_RESID16_G124,
    IMAGE_INDEX_FACTORY_DEFAULT_G124,
    IMAGE_INDEX_MENU_PATH_G124,
    IMAGE_INDEX_UXC_RESID16_G124,
    ISO_MODE_AUTO_G123,
    ISO_MODE_FIXED_G123,
    LOG_SHOOTING_CINE_EI_G123,
    LOG_SHOOTING_CINE_EI_QUICK_G123,
    LOG_SHOOTING_FLEXIBLE_ISO_G123,
    LOG_SHOOTING_OFF_G123,
    MF_UXC_RESID16_G124,
    MOVIE_SHOOT_MODES_PHASE290,
    MOVIE_VIEW_F_UXC_RESID16_G124,
    Master124GateReport,
    PASM_SHOOT_MODES_PHASE290,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED,
    PHYSICAL_USB_PACKETS_EMITTED,
    PINNED_FX3_APPFW_SLICES_PHASE290,
    PINNED_FX3_APPFW_SLICES_SHA256_PHASE290,
    PINNED_FX6_APPFW_SLICES_PHASE290,
    PINNED_FX6_APPFW_SLICES_SHA256_PHASE290,
    PINNED_PHASE290_DONOR_SPECS,
    PLAYBACK_MEDIA_SLOT1_DEFAULT_G124,
    POWER_INSUFFICIENT_UXC_RESID16_G123,
    POWER_OFF_AFTER_CLEANING_G_UXC_RESID16_G123,
    PRIORITY_AF_C_F_UXC_RESID16_G124,
    PRIORITY_AF_S_F_UXC_RESID16_G124,
    Phase290DonorAuditResult,
    RAW_FIRMWARE_BYTES_LEAKED,
    REALHW_SENSOR_CLEANING_EV_COMP_FOCUS_MODE_PLAYBACK_ROTATE_124GATE_SCHEMA,
    REALHW_SENSOR_CLEANING_EV_COMP_FOCUS_MODE_PLAYBACK_ROTATE_124GATE_VERSION,
    RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE290,
    RESET_ACTION_INITIALIZE_PHASE290,
    RESET_ACTION_NONE_PHASE290,
    RESET_ACTION_RESET_NETWORK_SET_PHASE290,
    RESET_EV_COMP_F_UXC_RESID16_G123,
    ROTATE_F_UXC_RESID16_G124,
    ROTATE_MENU_PATH_G124,
    ROTATE_STEP_DEGREES_CCW_G124,
    ROTATE_UXC_RESID16_G124,
    SENSOR_CLEANING_F_UXC_RESID16_G123,
    SENSOR_CLEANING_MENU_PATH_G123,
    SENSOR_CLEANING_MIN_BATTERY_PCT_G123,
    SENSOR_CLEANING_PRE_V200_MIN_BARS_G123,
    SHOOT_MODE_A_PHASE290,
    SHOOT_MODE_INTELLIGENT_AUTO_PHASE290,
    SHOOT_MODE_MOVIE_PHASE290,
    SHOOT_MODE_MR_PHASE290,
    SHOOT_MODE_M_PHASE290,
    SHOOT_MODE_P_PHASE290,
    SHOOT_MODE_SQ_PHASE290,
    SHOOT_MODE_STILL_PHASE290,
    SHOOT_MODE_S_PHASE290,
    SPI_NOR_WRITE_AUTHORIZED,
    STATUS_BLOCKED_G123_CINE_EI_EV_COMP_OR_LEGACY_DIAL_SPOOF_VIOLATION,
    STATUS_BLOCKED_G123_CLEANING_LOW_BATTERY_OR_ACTIVE_MOUNT_VIOLATION,
    STATUS_BLOCKED_G123_EV_COMP_RANGE_STEP_OR_MANUAL_ISO_VIOLATION,
    STATUS_BLOCKED_G123_FX6_END_CLEANING_OR_IBIS_SPOOF_VIOLATION,
    STATUS_BLOCKED_G123_TELEMETRY_INVALID,
    STATUS_BLOCKED_G124_AF_PRIORITY_ASSIST_OR_ILLUMINATOR_VIOLATION,
    STATUS_BLOCKED_G124_FOCUS_MODE_MOVIE_SPLIT_OR_DORMANT_VIOLATION,
    STATUS_BLOCKED_G124_PLAYBACK_VIEW_INDEX_OR_GROUP_DORMANT_VIOLATION,
    STATUS_BLOCKED_G124_SLOT1_ROTATE_WRITE_VAULT_VIOLATION,
    STATUS_BLOCKED_G124_TELEMETRY_INVALID,
    STATUS_BLOCKED_PHASE290_DONOR_INTEGRITY,
    STATUS_VERIFIED_G123,
    STATUS_VERIFIED_G124,
    STILL_FOCUS_MODE_FACTORY_DEFAULT_G124,
    STILL_SHOOT_MODES_PHASE290,
    SensorCleaningEvCompGuardResult,
    UNABLE_TO_ROTATE_UXC_RESID16_G124,
    USB_PACKETS_TRANSMITTED,
    VIEW_MODE_DATE_G124,
    VIEW_MODE_FACTORY_DEFAULT_G124,
    VIEW_MODE_FOLDER_STILL_G124,
    VIEW_MODE_MENU_PATH_G124,
    VIEW_MODE_MOVIE_G124,
    VIEW_MODE_UXC_RESID16_G124,
    _default_donor_budget_seconds_phase290,
    _is_forced_clean_room,
    audit_phase290_donor_contracts,
    compute_focus_mode_and_playback_rotate_matrix,
    compute_sensor_cleaning_and_ev_comp_matrix,
    evaluate_124_master_safety_gates,
    evaluate_124gate_preflight,
    evaluate_g123_sensor_cleaning_and_ev_comp_guard,
    evaluate_g124_focus_mode_and_playback_rotate_guard,
    main as module_main,
    resolve_fx3_focus_mode_and_playback_rotate_state,
    resolve_fx3_sensor_cleaning_and_ev_comp_state,
    run_124_gate_preflight,
    verify_focus_mode_and_playback_rotate_guard,
    verify_sensor_cleaning_and_ev_comp_guard,
)


def _subprocess_timeout_seconds() -> float:
    return 15.0 if os.environ.get("GITHUB_ACTIONS", "").strip().lower() == "true" else 10.0


def _build_synthetic_122_report(*, dry_run: bool) -> Master122GateReport:
    return evaluate_122gate_preflight(
        DEFAULT_REPO_ROOT,
        force_clean_room=True,
        dry_run_simulated=dry_run,
    )


class TestPhase290SensorCleaningEvCompFocusModePlaybackRotate124GateGuard(
    unittest.TestCase
):
    clean_offline_122: Master122GateReport
    clean_dryrun_122: Master122GateReport

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.clean_offline_122 = _build_synthetic_122_report(dry_run=False)
        cls.clean_dryrun_122 = _build_synthetic_122_report(dry_run=True)

    # --- 1. Package Exports, Hard Redlines & Dual-Mode Donor Audit (Tests 01-12) ---

    def test_01_package_exports_and_all_integrity(self) -> None:
        self.assertTrue(
            hasattr(
                fx3_safety,
                "realhw_sensor_cleaning_ev_comp_focus_mode_playback_rotate_and_124gate_guard",
            )
        )
        for name in (
            "evaluate_124gate_preflight",
            "evaluate_124_master_safety_gates",
            "run_124_gate_preflight",
            "evaluate_g123_sensor_cleaning_and_ev_comp_guard",
            "evaluate_g124_focus_mode_and_playback_rotate_guard",
            "Master124GateReport",
            "G123",
            "G124",
            "CROSS_MODEL_FLASH_AUTHORIZED",
        ):
            self.assertIn(name, fx3_safety.__all__)
            self.assertTrue(hasattr(fx3_safety, name))
        self.assertIs(evaluate_124_master_safety_gates, evaluate_124gate_preflight)
        self.assertIs(run_124_gate_preflight, evaluate_124gate_preflight)

    def test_02_schema_version_and_redline_constants_locked(self) -> None:
        self.assertEqual(
            REALHW_SENSOR_CLEANING_EV_COMP_FOCUS_MODE_PLAYBACK_ROTATE_124GATE_SCHEMA,
            "realhw_sensor_cleaning_ev_comp_focus_mode_playback_rotate_and_124gate_guard_v1",
        )
        self.assertEqual(
            REALHW_SENSOR_CLEANING_EV_COMP_FOCUS_MODE_PLAYBACK_ROTATE_124GATE_VERSION,
            "1.0.0",
        )
        self.assertFalse(HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        self.assertFalse(HUMAN_HARDWARE_ATTACH_TOKEN)
        self.assertFalse(CROSS_MODEL_FLASH_AUTHORIZED)
        self.assertFalse(EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        self.assertFalse(SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(PERSISTENT_WRITE_RELEASE)
        self.assertFalse(PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED)
        self.assertEqual(USB_PACKETS_TRANSMITTED, 0)
        self.assertEqual(PHYSICAL_USB_PACKETS_EMITTED, 0)
        self.assertEqual(RAW_FIRMWARE_BYTES_LEAKED, 0)

    def test_03_pinned_donor_specs_and_slices_exact(self) -> None:
        self.assertEqual(len(PINNED_PHASE290_DONOR_SPECS), 11)
        self.assertEqual(len(PINNED_FX3_APPFW_SLICES_PHASE290), 23)
        self.assertEqual(len(PINNED_FX6_APPFW_SLICES_PHASE290), 6)
        self.assertEqual(len(PINNED_FX3_APPFW_SLICES_SHA256_PHASE290), 64)
        self.assertEqual(len(PINNED_FX6_APPFW_SLICES_SHA256_PHASE290), 64)
        self.assertLessEqual(DONOR_CHECK_MAX_SECONDS_PHASE290, 0.20)
        self.assertEqual(DONOR_CHECK_CI_MAX_SECONDS_PHASE290, 1.00)

    def test_04_donor_audit_fast_o_rdonly_and_clean_room_fallback(self) -> None:
        res = audit_phase290_donor_contracts()
        self.assertTrue(res.valid, msg=res.errors)
        self.assertIn(
            res.verification_mode, ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC")
        )
        self.assertEqual(res.raw_firmware_bytes_leaked, 0)
        self.assertTrue(res.fx3_contracts_verified)
        self.assertTrue(res.fx6_contracts_verified)
        self.assertTrue(res.four_lang_resid16_parity_verified)
        self.assertLessEqual(res.elapsed_seconds, _default_donor_budget_seconds_phase290())

    def test_05_forced_clean_room_mode_returns_synthetic_zero_files(self) -> None:
        res = audit_phase290_donor_contracts(force_clean_room=True)
        self.assertIsInstance(res, Phase290DonorAuditResult)
        self.assertTrue(res.valid)
        self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(res.files_inspected, 0)
        self.assertEqual(len(res.checked_markers), 11)
        self.assertEqual(res.missing_markers, ())
        self.assertEqual(res.raw_firmware_bytes_leaked, 0)

    def test_06_clean_room_env_flags_supported(self) -> None:
        for env_key in (ENV_CLEAN_ROOM_TEST_PHASE290, "FX3_FX6_FORCE_CLEAN_ROOM"):
            with mock.patch.dict(os.environ, {env_key: "1"}):
                self.assertTrue(_is_forced_clean_room())
                res = audit_phase290_donor_contracts()
                self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")
                self.assertTrue(res.valid)

    def test_07_github_actions_timing_headroom_budget_helper(self) -> None:
        with mock.patch.dict(os.environ, {"GITHUB_ACTIONS": "true"}):
            self.assertEqual(
                _default_donor_budget_seconds_phase290(),
                DONOR_CHECK_CI_MAX_SECONDS_PHASE290,
            )
            self.assertEqual(_subprocess_timeout_seconds(), 15.0)
        with mock.patch.dict(os.environ, {"GITHUB_ACTIONS": ""}):
            self.assertEqual(
                _default_donor_budget_seconds_phase290(),
                DONOR_CHECK_MAX_SECONDS_PHASE290,
            )

    def test_08_missing_explicit_work_root_blocks_with_donor_integrity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.dict(
                os.environ,
                {ENV_CLEAN_ROOM_TEST_PHASE290: "", "FX3_FX6_FORCE_CLEAN_ROOM": ""},
            ):
                res = audit_phase290_donor_contracts(
                    work_root=Path(tmp),
                    force_clean_room=False,
                )
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_PHASE290_DONOR_INTEGRITY)
        self.assertGreater(len(res.missing_markers), 0)

    def test_09_tampered_donor_file_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fake = Path(tmp) / "fake_uxc.bin"
            fake.write_bytes(b"TAMPERED_DONOR_PAYLOAD")
            bad_spec = {
                "fake_key": (
                    "FX3",
                    "fake_uxc.bin",
                    999,
                    "0" * 64,
                    (b"Sensor Cleaning",),
                    "BAD_MARKER",
                )
            }
            with mock.patch.dict(
                os.environ,
                {ENV_CLEAN_ROOM_TEST_PHASE290: "", "FX3_FX6_FORCE_CLEAN_ROOM": ""},
            ):
                res = audit_phase290_donor_contracts(
                    work_root=Path(tmp),
                    force_clean_room=False,
                    donor_specs_override=bad_spec,
                )
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_PHASE290_DONOR_INTEGRITY)
        self.assertIn("BAD_MARKER", res.missing_markers)

    def test_10_valid_custom_donor_override_o_rdonly_audit_succeeds(self) -> None:
        import hashlib

        payload = b"Sensor Cleaning\x00Exposure Comp.\x00Rotate"
        sha = hashlib.sha256(payload).hexdigest()
        with tempfile.TemporaryDirectory() as tmp:
            fp = Path(tmp) / "custom_f.uxc"
            fp.write_bytes(payload)
            spec = {
                "custom_f": (
                    "FX3",
                    "custom_f.uxc",
                    len(payload),
                    sha,
                    (b"Sensor Cleaning", b"Exposure Comp.", b"Rotate"),
                    "CUSTOM_OK",
                )
            }
            with mock.patch.dict(
                os.environ,
                {ENV_CLEAN_ROOM_TEST_PHASE290: "", "FX3_FX6_FORCE_CLEAN_ROOM": ""},
            ):
                res = audit_phase290_donor_contracts(
                    work_root=Path(tmp),
                    force_clean_room=False,
                    donor_specs_override=spec,
                )
        self.assertTrue(res.valid, msg=res.errors)
        self.assertEqual(res.verification_mode, "LOCAL_DONOR_O_RDONLY")
        self.assertEqual(res.files_inspected, 1)
        self.assertEqual(res.checked_markers, ("CUSTOM_OK",))

    def test_11_donor_audit_result_json_roundtrip_zero_leakage(self) -> None:
        res = audit_phase290_donor_contracts(force_clean_room=True)
        dumped = json.dumps(res.to_dict())
        loaded = json.loads(dumped)
        self.assertEqual(loaded["status"], "VERIFIED_SAFE")
        self.assertEqual(loaded["raw_firmware_bytes_leaked"], 0)
        self.assertTrue(loaded["four_lang_resid16_parity_verified"])

    def test_12_default_gate_identities_match_wave52_contracts(self) -> None:
        self.assertEqual(G123, G123_GATE_ID)
        self.assertEqual(G124, G124_GATE_ID)
        self.assertEqual(GATE_G123_SENSOR_CLEANING_EV_COMP_AND_CINE_EI_GUARD, G123_GATE_CODE)
        self.assertEqual(GATE_G124_FOCUS_MODE_AND_PLAYBACK_ROTATE_SLOT1_GUARD, G124_GATE_CODE)

    # --- 2. Gate G123: [Sensor Cleaning] >= 51% / Power-OFF / FX6 e-ND & [Exposure Comp.] / Cine EI (Tests 13-35) ---

    def test_13_g123_uxc_resid16_and_battery_constants_exact(self) -> None:
        self.assertEqual(SENSOR_CLEANING_F_UXC_RESID16_G123, 0x67D6)
        self.assertEqual(CLEANING_MODE_LEGACY_UXC_RESID16_G123, 0xE7D7)
        self.assertEqual(POWER_INSUFFICIENT_UXC_RESID16_G123, 0xE574)
        self.assertEqual(POWER_OFF_AFTER_CLEANING_G_UXC_RESID16_G123, 0x6221)
        self.assertEqual(EXPOSURE_COMP_F_UXC_RESID16_G123, 0x76DE)
        self.assertEqual(EXPOSURE_COMP_UXC_RESID16_G123, 0xE956)
        self.assertEqual(RESET_EV_COMP_F_UXC_RESID16_G123, 0x7853)
        self.assertEqual(EXPOSURE_STEP_F_UXC_RESID16_G123, 0x78C4)
        self.assertEqual(DIAL_EV_COMP_UXC_RESID16_G123, 0xE4D9)
        self.assertEqual(SENSOR_CLEANING_MIN_BATTERY_PCT_G123, 51)
        self.assertEqual(SENSOR_CLEANING_PRE_V200_MIN_BARS_G123, 3)
        self.assertEqual(FX6_CRSDK_SENSOR_CLEANING_CMD_ID_G123, 320)
        self.assertEqual(FX6_VARIABLE_ND_VALUES_G123, ("CLEAR", "1/4..1/128"))

    def test_14_g123_default_state_verified_and_fx6_contrast_locked(self) -> None:
        res = verify_sensor_cleaning_and_ev_comp_guard()
        self.assertIsInstance(res, SensorCleaningEvCompGuardResult)
        self.assertTrue(res.valid, msg=res.errors)
        self.assertEqual(res.status, STATUS_VERIFIED_G123)
        self.assertEqual(res.body_model_name, FX3_MODEL_NAME_PHASE290)
        self.assertEqual(res.body_model_id_hex, "0x91030080")
        self.assertEqual(res.help_guide_code, FX3_HELP_GUIDE_CODE_PHASE290)
        self.assertFalse(res.fx6_has_ibis)
        self.assertTrue(res.fx6_front_end_assembly_present)
        self.assertFalse(res.fx6_sensor_cleaning_supported)
        self.assertEqual(res.fx6_crsdk_sensor_cleaning_id, 320)
        self.assertTrue(res.fx6_exposes_apr)
        self.assertFalse(res.fx3_has_physical_ev_dial)
        self.assertEqual(res.matrix_states_checked, 384)

    def test_15_g123_sensor_cleaning_51pct_threshold_allowed_50pct_blocked(self) -> None:
        ok_51 = verify_sensor_cleaning_and_ev_comp_guard(
            sensor_cleaning_requested=True,
            battery_pct=51,
            power_switch_off_after_cleaning=True,
        )
        self.assertTrue(ok_51.valid, msg=ok_51.errors)
        self.assertTrue(ok_51.sensor_cleaning_allowed)

        ok_100 = verify_sensor_cleaning_and_ev_comp_guard(
            sensor_cleaning_requested=True,
            battery_pct=100,
            power_switch_off_after_cleaning=True,
        )
        self.assertTrue(ok_100.valid, msg=ok_100.errors)

        for low in (50, 25, 0):
            bad = verify_sensor_cleaning_and_ev_comp_guard(
                sensor_cleaning_requested=True,
                battery_pct=low,
                power_switch_off_after_cleaning=True,
            )
            self.assertFalse(bad.valid, msg=low)
            self.assertEqual(
                bad.status,
                STATUS_BLOCKED_G123_CLEANING_LOW_BATTERY_OR_ACTIVE_MOUNT_VIOLATION,
            )
            self.assertFalse(bad.sensor_cleaning_allowed)

    def test_16_g123_sensor_cleaning_pre_v200_3bars_boundary(self) -> None:
        ok_bars = verify_sensor_cleaning_and_ev_comp_guard(
            firmware_version="1.01",
            sensor_cleaning_requested=True,
            battery_bars=3,
            battery_pct=45,
            power_switch_off_after_cleaning=True,
        )
        self.assertTrue(ok_bars.valid, msg=ok_bars.errors)
        self.assertTrue(ok_bars.sensor_cleaning_allowed)

        bad_bars = verify_sensor_cleaning_and_ev_comp_guard(
            firmware_version="1.01",
            sensor_cleaning_requested=True,
            battery_bars=2,
            battery_pct=45,
            power_switch_off_after_cleaning=True,
        )
        self.assertFalse(bad_bars.valid)
        self.assertEqual(
            bad_bars.status,
            STATUS_BLOCKED_G123_CLEANING_LOW_BATTERY_OR_ACTIVE_MOUNT_VIOLATION,
        )

    def test_17_g123_sensor_cleaning_blocks_missing_power_off_backup_mount_rec_air(self) -> None:
        for bad_kw in (
            {"sensor_cleaning_requested": True, "battery_pct": 80, "power_switch_off_after_cleaning": False},
            {"sensor_cleaning_requested": True, "battery_pct": 80, "tier0_p3_backup_active": True},
            {"sensor_cleaning_requested": True, "battery_pct": 80, "open_mount_active": True},
            {"sensor_cleaning_requested": True, "battery_pct": 80, "recording_active": True},
            {"sensor_cleaning_requested": True, "battery_pct": 80, "compressed_air_blower_requested": True},
        ):
            res = verify_sensor_cleaning_and_ev_comp_guard(**bad_kw)
            self.assertFalse(res.valid, msg=bad_kw)
            self.assertEqual(
                res.status,
                STATUS_BLOCKED_G123_CLEANING_LOW_BATTERY_OR_ACTIVE_MOUNT_VIOLATION,
            )

    def test_18_g123_fx6_end_optical_block_and_zero_ibis_rejects_cleaning_crosswire(self) -> None:
        for bad_kw in (
            {"target_model": FX6_MODEL_NAME_PHASE290, "sensor_cleaning_requested": True},
            {"claimed_fx6_has_ibis_sensor_cleaning": True},
            {"claimed_cross_wire_fx3_ibis_clean_to_fx6_end": True},
        ):
            res = verify_sensor_cleaning_and_ev_comp_guard(**bad_kw)
            self.assertFalse(res.valid, msg=bad_kw)
            self.assertEqual(
                res.status,
                STATUS_BLOCKED_G123_FX6_END_CLEANING_OR_IBIS_SPOOF_VIOLATION,
            )

    def test_19_g123_ev_comp_still_5ev_and_movie_sq_2ev_bounds(self) -> None:
        self.assertEqual((EV_COMP_STILL_MIN_EV_G123, EV_COMP_STILL_MAX_EV_G123), (-5.0, 5.0))
        self.assertEqual((EV_COMP_MOVIE_MIN_EV_G123, EV_COMP_MOVIE_MAX_EV_G123), (-2.0, 2.0))
        self.assertEqual((EV_COMP_LIVE_METER_MIN_EV_G123, EV_COMP_LIVE_METER_MAX_EV_G123), (-3.0, 3.0))

        for sm in (SHOOT_MODE_P_PHASE290, SHOOT_MODE_A_PHASE290, SHOOT_MODE_S_PHASE290):
            for ev in (-5.0, -3.0, 0.0, 2.7, 5.0):
                ok = verify_sensor_cleaning_and_ev_comp_guard(
                    shoot_mode=sm,
                    requested_ev_comp=ev,
                )
                self.assertTrue(ok.valid, msg=f"{sm}/{ev}: {ok.errors}")
                self.assertEqual(ok.effective_ev_comp, ev)
            for bad_ev in (-5.3, 5.3):
                bad = verify_sensor_cleaning_and_ev_comp_guard(
                    shoot_mode=sm,
                    requested_ev_comp=bad_ev,
                )
                self.assertFalse(bad.valid, msg=f"{sm}/{bad_ev}")
                self.assertEqual(
                    bad.status,
                    STATUS_BLOCKED_G123_EV_COMP_RANGE_STEP_OR_MANUAL_ISO_VIOLATION,
                )

        for mv_sm in (SHOOT_MODE_MOVIE_PHASE290, SHOOT_MODE_SQ_PHASE290):
            for ev in (-2.0, -0.3, 0.0, 1.5, 2.0):
                ok_mv = verify_sensor_cleaning_and_ev_comp_guard(
                    shoot_mode=mv_sm,
                    log_shooting=LOG_SHOOTING_FLEXIBLE_ISO_G123,
                    requested_ev_comp=ev,
                )
                self.assertTrue(ok_mv.valid, msg=f"{mv_sm}/{ev}: {ok_mv.errors}")
            for bad_mv_ev in (-2.3, 2.3, 5.0):
                bad_mv = verify_sensor_cleaning_and_ev_comp_guard(
                    shoot_mode=mv_sm,
                    log_shooting=LOG_SHOOTING_FLEXIBLE_ISO_G123,
                    requested_ev_comp=bad_mv_ev,
                )
                self.assertFalse(bad_mv.valid, msg=f"{mv_sm}/{bad_mv_ev}")
                self.assertEqual(
                    bad_mv.status,
                    STATUS_BLOCKED_G123_EV_COMP_RANGE_STEP_OR_MANUAL_ISO_VIOLATION,
                )

    def test_20_g123_manual_m_iso_auto_vs_fixed_iso_and_iauto_lockout(self) -> None:
        ok_m_auto = verify_sensor_cleaning_and_ev_comp_guard(
            shoot_mode=SHOOT_MODE_M_PHASE290,
            iso_mode=ISO_MODE_AUTO_G123,
            requested_ev_comp=2.0,
        )
        self.assertTrue(ok_m_auto.valid, msg=ok_m_auto.errors)
        self.assertTrue(ok_m_auto.ev_comp_active)
        self.assertEqual(ok_m_auto.effective_ev_comp, 2.0)

        ok_m_fixed_zero = verify_sensor_cleaning_and_ev_comp_guard(
            shoot_mode=SHOOT_MODE_M_PHASE290,
            iso_mode=ISO_MODE_FIXED_G123,
            requested_ev_comp=0.0,
        )
        self.assertTrue(ok_m_fixed_zero.valid, msg=ok_m_fixed_zero.errors)
        self.assertFalse(ok_m_fixed_zero.ev_comp_active)

        bad_m_fixed = verify_sensor_cleaning_and_ev_comp_guard(
            shoot_mode=SHOOT_MODE_M_PHASE290,
            iso_mode=ISO_MODE_FIXED_G123,
            requested_ev_comp=1.0,
        )
        self.assertFalse(bad_m_fixed.valid)
        self.assertEqual(
            bad_m_fixed.status,
            STATUS_BLOCKED_G123_EV_COMP_RANGE_STEP_OR_MANUAL_ISO_VIOLATION,
        )

        bad_iauto = verify_sensor_cleaning_and_ev_comp_guard(
            shoot_mode=SHOOT_MODE_INTELLIGENT_AUTO_PHASE290,
            ev_comp_apply_requested=True,
        )
        self.assertFalse(bad_iauto.valid)
        self.assertEqual(
            bad_iauto.status,
            STATUS_BLOCKED_G123_EV_COMP_RANGE_STEP_OR_MANUAL_ISO_VIOLATION,
        )

    def test_21_g123_cine_ei_and_cine_ei_quick_total_ev_comp_lockout(self) -> None:
        self.assertEqual(CINE_EI_BASE_ISOS_G123, (800, 12800))
        self.assertEqual(CINE_EI_EXPOSURE_INDEX_RANGE_BY_BASE_G123[800], (200, 3200))
        self.assertEqual(CINE_EI_EXPOSURE_INDEX_RANGE_BY_BASE_G123[12800], (3200, 51200))
        for cine_mode in CINE_EI_LOCKED_LOG_MODES_G123:
            for base_iso in CINE_EI_BASE_ISOS_G123:
                ok = verify_sensor_cleaning_and_ev_comp_guard(
                    shoot_mode=SHOOT_MODE_MOVIE_PHASE290,
                    log_shooting=cine_mode,
                    cine_ei_base_iso=base_iso,
                    requested_ev_comp=0.0,
                )
                self.assertTrue(ok.valid, msg=f"{cine_mode}/{base_iso}: {ok.errors}")
                self.assertTrue(ok.cine_ei_locks_ev_comp)
                self.assertFalse(ok.ev_comp_active)

                bad = verify_sensor_cleaning_and_ev_comp_guard(
                    shoot_mode=SHOOT_MODE_MOVIE_PHASE290,
                    log_shooting=cine_mode,
                    cine_ei_base_iso=base_iso,
                    requested_ev_comp=-0.7,
                )
                self.assertFalse(bad.valid)
                self.assertEqual(
                    bad.status,
                    STATUS_BLOCKED_G123_CINE_EI_EV_COMP_OR_LEGACY_DIAL_SPOOF_VIOLATION,
                )

    def test_22_g123_exposure_step_and_exposure_std_adjust_one_sixth_ev(self) -> None:
        self.assertEqual(ALLOWED_EXPOSURE_STEPS_G123, (EXPOSURE_STEP_0_3_EV_G123, EXPOSURE_STEP_0_5_EV_G123))
        self.assertEqual(EXPOSURE_STEP_FACTORY_DEFAULT_G123, EXPOSURE_STEP_0_3_EV_G123)
        self.assertEqual(EXPOSURE_STD_ADJUST_STEP_DENOM_G123, 6)
        for step in ALLOWED_EXPOSURE_STEPS_G123:
            for num in range(-6, 7):
                std_ev = num / 6.0
                res = verify_sensor_cleaning_and_ev_comp_guard(
                    requested_exposure_step=step,
                    exposure_std_adjust_ev=std_ev,
                )
                self.assertTrue(res.valid, msg=f"{step}/{std_ev}: {res.errors}")
                self.assertEqual(res.effective_exposure_step, step)

        for bad_std in (-1.5, 1.5, 0.25):
            res_bad = verify_sensor_cleaning_and_ev_comp_guard(
                exposure_std_adjust_ev=bad_std,
            )
            self.assertFalse(res_bad.valid, msg=bad_std)
            self.assertEqual(
                res_bad.status,
                STATUS_BLOCKED_G123_EV_COMP_RANGE_STEP_OR_MANUAL_ISO_VIOLATION,
            )

    def test_23_g123_spoof_flags_legacy_dial_cine_ei_shutter_angle_blocked(self) -> None:
        for bad_kw in (
            {"claimed_fx3_has_physical_ev_dial_or_reset_ev_comp": True},
            {"claimed_cine_ei_allows_ev_comp": True},
            {"claimed_exposure_step_changes_shutter_angle": True},
        ):
            res = verify_sensor_cleaning_and_ev_comp_guard(**bad_kw)
            self.assertFalse(res.valid, msg=bad_kw)
            self.assertEqual(
                res.status,
                STATUS_BLOCKED_G123_CINE_EI_EV_COMP_OR_LEGACY_DIAL_SPOOF_VIOLATION,
            )

    def test_24_g123_reset_persistence_ev_comp_resets_step_survives(self) -> None:
        res_cam = verify_sensor_cleaning_and_ev_comp_guard(
            shoot_mode=SHOOT_MODE_P_PHASE290,
            requested_ev_comp=1.7,
            requested_exposure_step=EXPOSURE_STEP_0_5_EV_G123,
            exposure_std_adjust_ev=0.5,
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE290,
        )
        self.assertTrue(res_cam.valid, msg=res_cam.errors)
        self.assertEqual(res_cam.effective_ev_comp, EV_COMP_FACTORY_DEFAULT_EV_G123)
        self.assertTrue(res_cam.ev_comp_reset_on_cam_reset)
        self.assertEqual(res_cam.effective_exposure_step, EXPOSURE_STEP_0_5_EV_G123)
        self.assertTrue(res_cam.exposure_step_survived_cam_reset)

        res_init = verify_sensor_cleaning_and_ev_comp_guard(
            shoot_mode=SHOOT_MODE_P_PHASE290,
            requested_ev_comp=1.7,
            requested_exposure_step=EXPOSURE_STEP_0_5_EV_G123,
            reset_action=RESET_ACTION_INITIALIZE_PHASE290,
        )
        self.assertTrue(res_init.valid)
        self.assertEqual(res_init.effective_ev_comp, 0.0)
        self.assertEqual(res_init.effective_exposure_step, EXPOSURE_STEP_0_3_EV_G123)
        self.assertFalse(res_init.exposure_step_survived_cam_reset)

    def test_25_g123_384_state_matrix_invariants(self) -> None:
        m = compute_sensor_cleaning_and_ev_comp_matrix()
        self.assertEqual(m["states_checked"], 384)
        self.assertEqual(m["cleaning_blocked_low_batt"], 256)
        self.assertEqual(m["cine_ei_ev_locked"], 192)
        self.assertEqual(m["manual_fixed_iso_ev_locked"], 48)
        self.assertEqual(m["step_survived_cam_reset"], 192)
        self.assertTrue(m["all_invariants_hold"])

    def test_26_g123_invalid_telemetry_rejected(self) -> None:
        for bad_kw in (
            {"body_model_name": FX6_MODEL_NAME_PHASE290},
            {"body_model_id": True},
            {"body_model_id": 0x1234},
            {"help_guide_code": "ilc/0000"},
            {"firmware_version": "bad"},
            {"battery_pct": -1},
            {"battery_pct": 101},
            {"battery_pct": True},
            {"battery_bars": 5},
            {"battery_bars": True},
            {"requested_ev_comp": False},
            {"exposure_std_adjust_ev": "0"},
            {"cine_ei_base_iso": 1600},
            {"shoot_mode": "Scene"},
            {"log_shooting": "S-Log2"},
            {"iso_mode": "AUTO_MAGIC"},
            {"requested_exposure_step": "0.1EV"},
            {"reset_action": "BOGUS"},
            {"target_model": "ILCE-7SM3"},
        ):
            res = verify_sensor_cleaning_and_ev_comp_guard(**bad_kw)
            self.assertFalse(res.valid, msg=bad_kw)
            self.assertEqual(res.status, STATUS_BLOCKED_G123_TELEMETRY_INVALID)

    def test_27_g123_evaluator_blocks_persistent_emmc_writes(self) -> None:
        verdict, res = evaluate_g123_sensor_cleaning_and_ev_comp_guard(
            force_clean_room=True,
            request_persistent_emmc_writes=True,
        )
        self.assertFalse(verdict.passed)
        self.assertFalse(res.valid)
        self.assertEqual(verdict.status, "BLOCKED_BY_PERSISTENT_EMMC_WRITE_REDLINE")

    def test_28_g123_menu_paths_and_evidence_tokens(self) -> None:
        self.assertIn("[Sensor Cleaning]", SENSOR_CLEANING_MENU_PATH_G123)
        self.assertIn("[Exposure Comp.]", EXPOSURE_COMP_MENU_PATH_G123)
        self.assertIn("[Exposure step]", EXPOSURE_STEP_MENU_PATH_G123)
        self.assertIn("[Exposure Std. Adjust]", EXPOSURE_STD_ADJUST_MENU_PATH_G123)
        verdict, res = evaluate_g123_sensor_cleaning_and_ev_comp_guard(
            force_clean_room=True
        )
        self.assertTrue(verdict.passed)
        self.assertIn("clean_batt>=51%", verdict.evidence)
        self.assertIn("fx6_ibis=False", verdict.evidence)
        self.assertIn("fx3_dial=False", verdict.evidence)
        self.assertEqual(
            json.loads(json.dumps(res.to_dict()))["status"], STATUS_VERIFIED_G123
        )

    def test_29_g123_normalization_aliases_work(self) -> None:
        res = verify_sensor_cleaning_and_ev_comp_guard(
            shoot_mode="[Movie]",
            log_shooting="flexible iso",
            iso_mode="auto",
            requested_exposure_step="0.5 ev",
            requested_ev_comp=-1.5,
        )
        self.assertTrue(res.valid, msg=res.errors)
        self.assertEqual(res.shoot_mode, SHOOT_MODE_MOVIE_PHASE290)
        self.assertEqual(res.log_shooting, LOG_SHOOTING_FLEXIBLE_ISO_G123)
        self.assertEqual(res.iso_mode, ISO_MODE_AUTO_G123)
        self.assertEqual(res.effective_exposure_step, EXPOSURE_STEP_0_5_EV_G123)

    def test_30_g123_fx6_target_safe_when_sensor_cleaning_not_requested(self) -> None:
        res = verify_sensor_cleaning_and_ev_comp_guard(
            target_model=FX6_MODEL_NAME_PHASE290,
            sensor_cleaning_requested=False,
        )
        self.assertTrue(res.valid, msg=res.errors)

    def test_31_g123_resolve_helper_exact_fields(self) -> None:
        r = resolve_fx3_sensor_cleaning_and_ev_comp_state(
            sensor_cleaning_requested=True,
            battery_pct=49,
            shoot_mode=SHOOT_MODE_M_PHASE290,
            log_shooting=LOG_SHOOTING_CINE_EI_G123,
            requested_ev_comp=1.0,
        )
        self.assertFalse(r["sensor_cleaning_allowed"])
        self.assertTrue(r["cine_ei_locks_ev_comp"])
        self.assertFalse(r["ev_comp_active"])
        self.assertEqual(r["effective_ev_comp"], 0.0)

    def test_32_g123_all_4_log_shooting_modes_enumerated(self) -> None:
        self.assertEqual(len(ALLOWED_LOG_SHOOTING_MODES_G123), 4)
        self.assertEqual(len(ALLOWED_ISO_MODES_G123), 2)
        self.assertIn(LOG_SHOOTING_OFF_G123, ALLOWED_LOG_SHOOTING_MODES_G123)
        self.assertIn(LOG_SHOOTING_CINE_EI_QUICK_G123, ALLOWED_LOG_SHOOTING_MODES_G123)

    def test_33_g123_still_exposure_comp_inactive_in_movie_still_range_blocked(self) -> None:
        res = verify_sensor_cleaning_and_ev_comp_guard(
            shoot_mode=SHOOT_MODE_MOVIE_PHASE290,
            log_shooting=LOG_SHOOTING_OFF_G123,
            requested_ev_comp=3.0,
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            res.status,
            STATUS_BLOCKED_G123_EV_COMP_RANGE_STEP_OR_MANUAL_ISO_VIOLATION,
        )

    def test_34_g123_reset_network_set_preserves_ev_comp_and_step(self) -> None:
        res = verify_sensor_cleaning_and_ev_comp_guard(
            shoot_mode=SHOOT_MODE_P_PHASE290,
            requested_ev_comp=1.3,
            requested_exposure_step=EXPOSURE_STEP_0_5_EV_G123,
            reset_action=RESET_ACTION_RESET_NETWORK_SET_PHASE290,
        )
        self.assertTrue(res.valid, msg=res.errors)
        self.assertEqual(res.effective_ev_comp, 1.3)
        self.assertFalse(res.ev_comp_reset_on_cam_reset)
        self.assertTrue(res.exposure_step_survived_cam_reset)

    def test_35_g123_fx3_vs_fx6_fw_version_fields_recorded(self) -> None:
        res = verify_sensor_cleaning_and_ev_comp_guard()
        self.assertEqual(res.firmware_version, FX3_DEFAULT_FW_VERSION_PHASE290)
        self.assertEqual(res.fx6_comparison_fw_version, FX6_DEFAULT_FW_VERSION_PHASE290)
        self.assertEqual(EXPOSURE_STD_ADJUST_MIN_EV_G123, -1.0)
        self.assertEqual(EXPOSURE_STD_ADJUST_MAX_EV_G123, 1.0)

    # --- 3. Gate G124: [Focus Mode] Still 5 vs Movie 2, AF Submenu & [Playback] Rotate Slot-1 Firewall (Tests 36-58) ---

    def test_36_g124_uxc_resid16_and_bkid_constants_exact(self) -> None:
        self.assertEqual(FOCUS_MODE_G_UXC_RESID16_G124, 0x625E)
        self.assertEqual(AF_S_UXC_RESID16_G124, 0xE56D)
        self.assertEqual(AF_A_UXC_RESID16_G124, 0xE56C)
        self.assertEqual(AF_C_UXC_RESID16_G124, 0xE56E)
        self.assertEqual(DMF_UXC_RESID16_G124, 0xE4AC)
        self.assertEqual(MF_UXC_RESID16_G124, 0xE9E4)
        self.assertEqual(AF_ASSIST_F_UXC_RESID16_G124, 0x64A9)
        self.assertEqual(PRIORITY_AF_S_F_UXC_RESID16_G124, 0x7519)
        self.assertEqual(PRIORITY_AF_C_F_UXC_RESID16_G124, 0x681B)
        self.assertEqual(BALANCED_EMPHASIS_F_UXC_RESID16_G124, 0x6A60)
        self.assertEqual(AF_ILLUMINATOR_UXC_RESID16_G124, 0xE07F)
        self.assertEqual(VIEW_MODE_UXC_RESID16_G124, 0xE3B7)
        self.assertEqual(DATE_VIEW_UXC_RESID16_G124, 0xE3B8)
        self.assertEqual(FOLDER_VIEW_STILL_UXC_RESID16_G124, 0xE3B9)
        self.assertEqual(MOVIE_VIEW_F_UXC_RESID16_G124, 0x7468)
        self.assertEqual(IMAGE_INDEX_UXC_RESID16_G124, 0xE20A)
        self.assertEqual(IMAGE_INDEX_9_UXC_RESID16_G124, 0xE4A3)
        self.assertEqual(IMAGE_INDEX_25_F_UXC_RESID16_G124, 0x7302)
        self.assertEqual(IMAGE_INDEX_30_DORMANT_F_UXC_RESID16_G124, 0x6E7A)
        self.assertEqual(DISPLAY_AS_GROUP_F_UXC_RESID16_G124, 0x6F26)
        self.assertEqual(DISPLAY_ROTATION_F_UXC_RESID16_G124, 0x6AA4)
        self.assertEqual(ROTATE_F_UXC_RESID16_G124, 0x795A)
        self.assertEqual(ROTATE_UXC_RESID16_G124, 0xE5AE)
        self.assertEqual(UNABLE_TO_ROTATE_UXC_RESID16_G124, 0xE922)
        self.assertEqual(
            FX3_APPFW_DISPLAY_ROTATION_BKID_G124, "BKID_APP_setting_display_rotatiton"
        )

    def test_37_g124_default_state_verified(self) -> None:
        res = verify_focus_mode_and_playback_rotate_guard()
        self.assertIsInstance(res, FocusModePlaybackRotateGuardResult)
        self.assertTrue(res.valid, msg=res.errors)
        self.assertEqual(res.status, STATUS_VERIFIED_G124)
        self.assertEqual(res.effective_focus_mode, STILL_FOCUS_MODE_FACTORY_DEFAULT_G124)
        self.assertEqual(res.internal_focus_enum, "AF_A")
        self.assertEqual(res.effective_priority_af_s, AF_PRIORITY_BALANCED_G124)
        self.assertEqual(res.effective_priority_af_c, AF_PRIORITY_BALANCED_G124)
        self.assertEqual(res.effective_af_illuminator, AF_ILLUMINATOR_AUTO_G124)
        self.assertFalse(res.fx6_supports_af_a_dmf_illuminator)
        self.assertEqual(res.effective_view_mode, VIEW_MODE_DATE_G124)
        self.assertEqual(res.effective_image_index, IMAGE_INDEX_9_G124)
        self.assertEqual(res.effective_display_as_group, "Off")
        self.assertEqual(res.effective_display_rotation, DISPLAY_ROTATION_AUTO_G124)
        self.assertEqual(res.playback_media_slot, PLAYBACK_MEDIA_SLOT1_DEFAULT_G124)
        self.assertFalse(res.rotate_blocked)
        self.assertEqual(res.matrix_states_checked, 384)

    def test_38_g124_still_5_focus_modes_accepted_and_aliases_normalized(self) -> None:
        self.assertEqual(len(FX3_STILL_5_FOCUS_MODES_G124), 5)
        for alias, exp in (
            ("AF-S", FOCUS_MODE_AF_S_G124),
            ("AF-A", FOCUS_MODE_AF_A_G124),
            ("AF-C", FOCUS_MODE_AF_C_G124),
            ("DMF", FOCUS_MODE_DMF_G124),
            ("MF", FOCUS_MODE_MF_G124),
        ):
            res = verify_focus_mode_and_playback_rotate_guard(
                shoot_mode=SHOOT_MODE_M_PHASE290,
                requested_focus_mode=alias,
            )
            self.assertTrue(res.valid, msg=f"{alias}: {res.errors}")
            self.assertEqual(res.effective_focus_mode, exp)

    def test_39_g124_movie_sq_strict_2_focus_modes_movie_auto_and_mf(self) -> None:
        self.assertEqual(len(FX3_MOVIE_2_FOCUS_MODES_G124), 2)
        self.assertEqual(FX3_MOVIE_AFC_INTERNAL_ENUM_G124, "MOVIE_AUTO")
        for sm in MOVIE_SHOOT_MODES_PHASE290:
            ok_afc = verify_focus_mode_and_playback_rotate_guard(
                shoot_mode=sm,
                requested_focus_mode=FOCUS_MODE_AF_C_G124,
            )
            self.assertTrue(ok_afc.valid, msg=ok_afc.errors)
            self.assertEqual(ok_afc.internal_focus_enum, "MOVIE_AUTO")

            ok_mf = verify_focus_mode_and_playback_rotate_guard(
                shoot_mode=sm,
                requested_focus_mode=FOCUS_MODE_MF_G124,
            )
            self.assertTrue(ok_mf.valid, msg=ok_mf.errors)
            self.assertEqual(ok_mf.internal_focus_enum, "MF")

            for bad_fm in (FOCUS_MODE_AF_S_G124, FOCUS_MODE_AF_A_G124, FOCUS_MODE_DMF_G124):
                bad = verify_focus_mode_and_playback_rotate_guard(
                    shoot_mode=sm,
                    requested_focus_mode=bad_fm,
                )
                self.assertFalse(bad.valid, msg=f"{sm}/{bad_fm}")
                self.assertEqual(
                    bad.status,
                    STATUS_BLOCKED_G124_FOCUS_MODE_MOVIE_SPLIT_OR_DORMANT_VIOLATION,
                )

    def test_40_g124_dormant_focus_modes_and_movie_fx6_spoofs_blocked(self) -> None:
        for dormant_fm in DORMANT_FOCUS_MODES_G124:
            res = verify_focus_mode_and_playback_rotate_guard(
                requested_focus_mode=dormant_fm
            )
            self.assertFalse(res.valid, msg=dormant_fm)
            self.assertEqual(
                res.status,
                STATUS_BLOCKED_G124_FOCUS_MODE_MOVIE_SPLIT_OR_DORMANT_VIOLATION,
            )
        for bad_kw in (
            {"claimed_movie_supports_af_s_af_a_dmf": True},
            {"claimed_fx6_has_af_a_dmf_or_illuminator": True},
        ):
            res_sp = verify_focus_mode_and_playback_rotate_guard(**bad_kw)
            self.assertFalse(res_sp.valid, msg=bad_kw)
            self.assertEqual(
                res_sp.status,
                STATUS_BLOCKED_G124_FOCUS_MODE_MOVIE_SPLIT_OR_DORMANT_VIOLATION,
            )

    def test_41_g124_af_assist_gated_strictly_to_movie_afc(self) -> None:
        ok = verify_focus_mode_and_playback_rotate_guard(
            shoot_mode=SHOOT_MODE_MOVIE_PHASE290,
            requested_focus_mode=FOCUS_MODE_AF_C_G124,
            af_assist_setting="On",
        )
        self.assertTrue(ok.valid, msg=ok.errors)
        self.assertTrue(ok.af_assist_active)

        for bad_kw in (
            {
                "shoot_mode": SHOOT_MODE_M_PHASE290,
                "requested_focus_mode": FOCUS_MODE_AF_C_G124,
                "af_assist_setting": "On",
            },
            {
                "shoot_mode": SHOOT_MODE_MOVIE_PHASE290,
                "requested_focus_mode": FOCUS_MODE_MF_G124,
                "af_assist_setting": "On",
            },
        ):
            bad = verify_focus_mode_and_playback_rotate_guard(**bad_kw)
            self.assertFalse(bad.valid, msg=bad_kw)
            self.assertEqual(
                bad.status,
                STATUS_BLOCKED_G124_AF_PRIORITY_ASSIST_OR_ILLUMINATOR_VIOLATION,
            )

    def test_42_g124_af_illuminator_still_only_and_lockouts(self) -> None:
        self.assertEqual(
            ALLOWED_AF_ILLUMINATOR_MODES_G124,
            (AF_ILLUMINATOR_AUTO_G124, AF_ILLUMINATOR_OFF_G124),
        )
        for still_fm in (FOCUS_MODE_AF_S_G124, FOCUS_MODE_AF_A_G124, FOCUS_MODE_DMF_G124):
            ok = verify_focus_mode_and_playback_rotate_guard(
                shoot_mode=SHOOT_MODE_P_PHASE290,
                requested_focus_mode=still_fm,
                requested_af_illuminator=AF_ILLUMINATOR_AUTO_G124,
                af_illuminator_fire_requested=True,
            )
            self.assertTrue(ok.valid, msg=f"{still_fm}: {ok.errors}")
            self.assertTrue(ok.af_illuminator_active)

        for bad_kw in (
            {
                "shoot_mode": SHOOT_MODE_MOVIE_PHASE290,
                "requested_focus_mode": FOCUS_MODE_AF_C_G124,
                "af_illuminator_fire_requested": True,
            },
            {
                "shoot_mode": SHOOT_MODE_M_PHASE290,
                "requested_focus_mode": FOCUS_MODE_AF_C_G124,
                "af_illuminator_fire_requested": True,
            },
            {
                "shoot_mode": SHOOT_MODE_M_PHASE290,
                "requested_focus_mode": FOCUS_MODE_AF_S_G124,
                "focus_magnifier_active": True,
                "af_illuminator_fire_requested": True,
            },
            {
                "shoot_mode": SHOOT_MODE_M_PHASE290,
                "requested_focus_mode": FOCUS_MODE_AF_S_G124,
                "mount_adaptor_attached": True,
                "af_illuminator_fire_requested": True,
            },
            {
                "shoot_mode": SHOOT_MODE_M_PHASE290,
                "requested_focus_mode": FOCUS_MODE_AF_S_G124,
                "requested_af_illuminator": AF_ILLUMINATOR_OFF_G124,
                "af_illuminator_fire_requested": True,
            },
        ):
            bad = verify_focus_mode_and_playback_rotate_guard(**bad_kw)
            self.assertFalse(bad.valid, msg=bad_kw)
            self.assertEqual(
                bad.status,
                STATUS_BLOCKED_G124_AF_PRIORITY_ASSIST_OR_ILLUMINATOR_VIOLATION,
            )

    def test_43_g124_priority_set_af_s_af_c_survives_camera_reset(self) -> None:
        self.assertEqual(
            ALLOWED_AF_PRIORITY_MODES_G124,
            (AF_PRIORITY_AF_G124, AF_PRIORITY_RELEASE_G124, AF_PRIORITY_BALANCED_G124),
        )
        res = verify_focus_mode_and_playback_rotate_guard(
            requested_priority_af_s=AF_PRIORITY_AF_G124,
            requested_priority_af_c=AF_PRIORITY_RELEASE_G124,
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE290,
        )
        self.assertTrue(res.valid, msg=res.errors)
        self.assertEqual(res.effective_priority_af_s, AF_PRIORITY_AF_G124)
        self.assertEqual(res.effective_priority_af_c, AF_PRIORITY_RELEASE_G124)
        self.assertTrue(res.af_priority_survived_cam_reset)

        spoof = verify_focus_mode_and_playback_rotate_guard(
            claimed_priority_reset_on_cam_reset=True
        )
        self.assertFalse(spoof.valid)
        self.assertEqual(
            spoof.status,
            STATUS_BLOCKED_G124_AF_PRIORITY_ASSIST_OR_ILLUMINATOR_VIOLATION,
        )

    def test_44_g124_playback_view_mode_3_active_vs_3_dormant(self) -> None:
        self.assertEqual(len(FX3_ACTIVE_3_VIEW_MODES_G124), 3)
        self.assertEqual(len(DORMANT_VIEW_MODES_G124), 3)
        for vm in FX3_ACTIVE_3_VIEW_MODES_G124:
            res = verify_focus_mode_and_playback_rotate_guard(requested_view_mode=vm)
            self.assertTrue(res.valid, msg=f"{vm}: {res.errors}")
            self.assertEqual(res.effective_view_mode, vm)
        for dormant_vm in DORMANT_VIEW_MODES_G124:
            bad = verify_focus_mode_and_playback_rotate_guard(
                requested_view_mode=dormant_vm
            )
            self.assertFalse(bad.valid, msg=dormant_vm)
            self.assertEqual(
                bad.status,
                STATUS_BLOCKED_G124_PLAYBACK_VIEW_INDEX_OR_GROUP_DORMANT_VIOLATION,
            )

    def test_45_g124_playback_image_index_9_25_active_vs_12_30_dormant(self) -> None:
        self.assertEqual(
            FX3_ACTIVE_2_IMAGE_INDEX_MODES_G124,
            (IMAGE_INDEX_9_G124, IMAGE_INDEX_25_G124),
        )
        for idx in FX3_ACTIVE_2_IMAGE_INDEX_MODES_G124:
            res = verify_focus_mode_and_playback_rotate_guard(
                requested_image_index=idx
            )
            self.assertTrue(res.valid, msg=f"{idx}: {res.errors}")
            self.assertEqual(res.effective_image_index, idx)
        for dormant_idx in DORMANT_IMAGE_INDEX_MODES_G124:
            bad = verify_focus_mode_and_playback_rotate_guard(
                requested_image_index=dormant_idx
            )
            self.assertFalse(bad.valid, msg=dormant_idx)
            self.assertEqual(
                bad.status,
                STATUS_BLOCKED_G124_PLAYBACK_VIEW_INDEX_OR_GROUP_DORMANT_VIOLATION,
            )

    def test_46_g124_display_as_group_rotation_and_group_delete_warning(self) -> None:
        self.assertEqual(
            ALLOWED_DISPLAY_ROTATION_MODES_G124,
            (
                DISPLAY_ROTATION_AUTO_G124,
                DISPLAY_ROTATION_MANUAL_G124,
                DISPLAY_ROTATION_OFF_G124,
            ),
        )
        for rot in ALLOWED_DISPLAY_ROTATION_MODES_G124:
            res = verify_focus_mode_and_playback_rotate_guard(
                requested_display_as_group="On",
                requested_display_rotation=rot,
                reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE290,
            )
            self.assertTrue(res.valid, msg=f"{rot}: {res.errors}")
            self.assertEqual(res.effective_display_as_group, "On")
            self.assertEqual(res.effective_display_rotation, rot)
            self.assertTrue(res.playback_settings_survived_cam_reset)

        bad_grp = verify_focus_mode_and_playback_rotate_guard(
            claimed_group_delete_keeps_other_frames=True
        )
        self.assertFalse(bad_grp.valid)
        self.assertEqual(
            bad_grp.status,
            STATUS_BLOCKED_G124_PLAYBACK_VIEW_INDEX_OR_GROUP_DORMANT_VIOLATION,
        )

    def test_47_g124_rotate_slot1_read_only_vault_firewall_erofs_ebusy_einval(self) -> None:
        self.assertEqual(ROTATE_STEP_DEGREES_CCW_G124, 90)
        bad_erofs = verify_focus_mode_and_playback_rotate_guard(
            rotate_requested=True,
            playback_media_slot="Slot 1",
            slot_1_write_protected=True,
        )
        self.assertFalse(bad_erofs.valid)
        self.assertTrue(bad_erofs.rotate_blocked)
        self.assertEqual(bad_erofs.rotate_block_errno, "EROFS")
        self.assertEqual(
            bad_erofs.status, STATUS_BLOCKED_G124_SLOT1_ROTATE_WRITE_VAULT_VIOLATION
        )

        bad_ebusy = verify_focus_mode_and_playback_rotate_guard(
            rotate_requested=True,
            playback_media_slot="Slot 2",
            background_transfer_active=True,
        )
        self.assertFalse(bad_ebusy.valid)
        self.assertTrue(bad_ebusy.rotate_blocked)
        self.assertEqual(bad_ebusy.rotate_block_errno, "EBUSY")
        self.assertEqual(
            bad_ebusy.status, STATUS_BLOCKED_G124_SLOT1_ROTATE_WRITE_VAULT_VIOLATION
        )

        bad_movie = verify_focus_mode_and_playback_rotate_guard(
            rotate_requested=True,
            playback_media_slot="Slot 2",
            playback_media_kind="Movie",
        )
        self.assertFalse(bad_movie.valid)
        self.assertEqual(bad_movie.rotate_block_errno, "EINVAL")
        self.assertEqual(
            bad_movie.status, STATUS_BLOCKED_G124_SLOT1_ROTATE_WRITE_VAULT_VIOLATION
        )

        bad_grp_del = verify_focus_mode_and_playback_rotate_guard(
            group_delete_requested=True,
            playback_media_slot="Slot 1",
            slot_1_contains_tier0_vault=True,
        )
        self.assertFalse(bad_grp_del.valid)
        self.assertEqual(
            bad_grp_del.status, STATUS_BLOCKED_G124_SLOT1_ROTATE_WRITE_VAULT_VIOLATION
        )

        bad_ro_claim = verify_focus_mode_and_playback_rotate_guard(
            claimed_rotate_is_read_only_display_only=True
        )
        self.assertFalse(bad_ro_claim.valid)
        self.assertEqual(
            bad_ro_claim.status, STATUS_BLOCKED_G124_SLOT1_ROTATE_WRITE_VAULT_VIOLATION
        )

    def test_48_g124_rotate_slot2_still_allowed_when_not_busy(self) -> None:
        ok = verify_focus_mode_and_playback_rotate_guard(
            rotate_requested=True,
            playback_media_slot="Slot 2",
            playback_media_kind="Still",
            background_transfer_active=False,
        )
        self.assertTrue(ok.valid, msg=ok.errors)
        self.assertFalse(ok.rotate_blocked)
        self.assertIsNone(ok.rotate_block_errno)

    def test_49_g124_384_state_matrix_invariants(self) -> None:
        m = compute_focus_mode_and_playback_rotate_matrix()
        self.assertEqual(m["states_checked"], 384)
        self.assertEqual(m["movie_afc_internal_movie_auto"], 144)
        self.assertGreater(m["illuminator_locked_states"], 0)
        self.assertEqual(m["priority_survived_cam_reset"], 192)
        self.assertEqual(m["playback_survived_cam_reset"], 192)
        self.assertTrue(m["all_invariants_hold"])

    def test_50_g124_invalid_telemetry_rejected(self) -> None:
        for bad_kw in (
            {"body_model_name": FX6_MODEL_NAME_PHASE290},
            {"body_model_id": False},
            {"help_guide_code": "ilc/9999"},
            {"firmware_version": ""},
            {"shoot_mode": "Scene"},
            {"requested_focus_mode": "HYPER_AF"},
            {"af_assist_setting": "Maybe"},
            {"requested_priority_af_s": "Turbo"},
            {"requested_priority_af_c": "Turbo"},
            {"requested_af_illuminator": "Strobe"},
            {"requested_view_mode": "Carousel"},
            {"requested_image_index": "64 Images"},
            {"requested_display_as_group": "Always"},
            {"requested_display_rotation": "Flip180"},
            {"playback_media_slot": "Slot 9"},
            {"playback_media_kind": "Audio"},
            {"reset_action": "BOGUS"},
        ):
            res = verify_focus_mode_and_playback_rotate_guard(**bad_kw)
            self.assertFalse(res.valid, msg=bad_kw)
            self.assertEqual(res.status, STATUS_BLOCKED_G124_TELEMETRY_INVALID)

    def test_51_g124_evaluator_blocks_persistent_emmc_writes(self) -> None:
        verdict, res = evaluate_g124_focus_mode_and_playback_rotate_guard(
            force_clean_room=True,
            request_persistent_emmc_writes=True,
        )
        self.assertFalse(verdict.passed)
        self.assertFalse(res.valid)
        self.assertEqual(verdict.status, "BLOCKED_BY_PERSISTENT_EMMC_WRITE_REDLINE")

    def test_52_g124_menu_paths_and_evidence_tokens(self) -> None:
        self.assertIn("[Focus Mode]", FOCUS_MODE_MENU_PATH_G124)
        self.assertIn("[View Mode]", VIEW_MODE_MENU_PATH_G124)
        self.assertIn("[Image Index]", IMAGE_INDEX_MENU_PATH_G124)
        self.assertIn("[Display as Group]", DISPLAY_AS_GROUP_MENU_PATH_G124)
        self.assertIn("[Display Rotation]", DISPLAY_ROTATION_MENU_PATH_G124)
        self.assertIn("[Rotate]", ROTATE_MENU_PATH_G124)
        verdict, res = evaluate_g124_focus_mode_and_playback_rotate_guard(
            force_clean_room=True
        )
        self.assertTrue(verdict.passed)
        self.assertIn("still5=5,movie2=2", verdict.evidence)
        self.assertIn("fx6_af=False", verdict.evidence)
        self.assertEqual(
            json.loads(json.dumps(res.to_dict()))["status"], STATUS_VERIFIED_G124
        )

    def test_53_all_9_shoot_modes_handled_across_g123_and_g124(self) -> None:
        self.assertEqual(len(ALLOWED_SHOOT_MODES_PHASE290), 9)
        self.assertEqual(len(STILL_SHOOT_MODES_PHASE290), 6)
        self.assertEqual(len(PASM_SHOOT_MODES_PHASE290), 5)
        self.assertEqual(len(MOVIE_SHOOT_MODES_PHASE290), 2)
        self.assertIn(SHOOT_MODE_STILL_PHASE290, PASM_SHOOT_MODES_PHASE290)
        self.assertIn(SHOOT_MODE_MR_PHASE290, ALLOWED_SHOOT_MODES_PHASE290)
        for sm in ALLOWED_SHOOT_MODES_PHASE290:
            r1 = verify_sensor_cleaning_and_ev_comp_guard(shoot_mode=sm)
            self.assertTrue(r1.valid, msg=f"G123 {sm}: {r1.errors}")
            fm = (
                FOCUS_MODE_AF_C_G124
                if sm in MOVIE_SHOOT_MODES_PHASE290
                else STILL_FOCUS_MODE_FACTORY_DEFAULT_G124
            )
            r2 = verify_focus_mode_and_playback_rotate_guard(
                shoot_mode=sm, requested_focus_mode=fm
            )
            self.assertTrue(r2.valid, msg=f"G124 {sm}: {r2.errors}")

    def test_54_all_4_reset_actions_accepted_in_g123_and_g124(self) -> None:
        self.assertEqual(len(ALLOWED_RESET_ACTIONS_PHASE290), 4)
        for r_act in ALLOWED_RESET_ACTIONS_PHASE290:
            r1 = verify_sensor_cleaning_and_ev_comp_guard(reset_action=r_act)
            self.assertTrue(r1.valid, msg=r_act)
            r2 = verify_focus_mode_and_playback_rotate_guard(reset_action=r_act)
            self.assertTrue(r2.valid, msg=r_act)

    def test_55_g124_initialize_resets_priority_illuminator_and_playback_settings(self) -> None:
        res = verify_focus_mode_and_playback_rotate_guard(
            requested_focus_mode=FOCUS_MODE_MF_G124,
            requested_priority_af_s=AF_PRIORITY_AF_G124,
            requested_priority_af_c=AF_PRIORITY_RELEASE_G124,
            requested_af_illuminator=AF_ILLUMINATOR_OFF_G124,
            requested_view_mode=VIEW_MODE_MOVIE_G124,
            requested_image_index=IMAGE_INDEX_25_G124,
            requested_display_as_group="On",
            requested_display_rotation=DISPLAY_ROTATION_OFF_G124,
            reset_action=RESET_ACTION_INITIALIZE_PHASE290,
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.effective_focus_mode, STILL_FOCUS_MODE_FACTORY_DEFAULT_G124)
        self.assertEqual(res.effective_priority_af_s, AF_PRIORITY_BALANCED_G124)
        self.assertEqual(res.effective_priority_af_c, AF_PRIORITY_BALANCED_G124)
        self.assertEqual(res.effective_af_illuminator, AF_ILLUMINATOR_AUTO_G124)
        self.assertEqual(res.effective_view_mode, VIEW_MODE_DATE_G124)
        self.assertEqual(res.effective_image_index, IMAGE_INDEX_9_G124)
        self.assertEqual(res.effective_display_as_group, "Off")
        self.assertEqual(res.effective_display_rotation, DISPLAY_ROTATION_AUTO_G124)
        self.assertFalse(res.af_priority_survived_cam_reset)
        self.assertFalse(res.playback_settings_survived_cam_reset)

    def test_56_g124_movie_focus_mode_alias_movie_auto_normalized(self) -> None:
        res = verify_focus_mode_and_playback_rotate_guard(
            shoot_mode=SHOOT_MODE_MOVIE_PHASE290,
            requested_focus_mode="MOVIE_AUTO",
            af_assist_setting="On",
        )
        self.assertTrue(res.valid, msg=res.errors)
        self.assertEqual(res.effective_focus_mode, FOCUS_MODE_AF_C_G124)
        self.assertEqual(res.internal_focus_enum, "MOVIE_AUTO")
        self.assertTrue(res.af_assist_active)

    def test_57_g124_resolve_helper_exact_fields(self) -> None:
        r = resolve_fx3_focus_mode_and_playback_rotate_state(
            shoot_mode=SHOOT_MODE_SQ_PHASE290,
            requested_focus_mode=FOCUS_MODE_AF_S_G124,
            rotate_requested=True,
            playback_media_slot="Slot 1",
            slot_1_write_protected=True,
        )
        self.assertEqual(r["effective_focus_mode"], FOCUS_MODE_AF_C_G124)
        self.assertEqual(r["internal_focus_enum"], "MOVIE_AUTO")
        self.assertTrue(r["rotate_blocked"])
        self.assertEqual(r["rotate_block_errno"], "EROFS")

    def test_58_g124_body_model_hex_and_view_aliases_normalized(self) -> None:
        res = verify_focus_mode_and_playback_rotate_guard(
            requested_view_mode="[Folder View(Still)]",
            requested_image_index="[25 Images]",
            requested_display_rotation="manual",
        )
        self.assertTrue(res.valid, msg=res.errors)
        self.assertEqual(res.body_model_id_hex, "0x91030080")
        self.assertEqual(res.effective_view_mode, VIEW_MODE_FOLDER_STILL_G124)
        self.assertEqual(res.effective_image_index, IMAGE_INDEX_25_G124)
        self.assertEqual(res.effective_display_rotation, DISPLAY_ROTATION_MANUAL_G124)

    # --- 4. Unified 124-Gate Preflight (`evaluate_124gate_preflight`, Tests 59-71) ---

    def test_59_master_124_offline_mode_121_of_124_with_mocked_upstream(self) -> None:
        rep = evaluate_124gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=False,
            master_122_override=self.clean_offline_122,
        )
        self.assertIsInstance(rep, Master124GateReport)
        self.assertEqual(rep.status, "VERIFIED_121_OF_124_AWAITING_PHYSICAL_TIER0")
        self.assertEqual(rep.summary["total_gates"], 124)
        self.assertEqual(rep.summary["verified_gates"], 121)
        self.assertEqual(rep.summary["blocked_or_pending_gates"], 3)
        self.assertEqual(rep.summary["g01_to_g12_verified"], 9)
        self.assertEqual(rep.summary["g13_to_g122_verified"], 110)
        self.assertEqual(rep.summary["g123_to_g124_verified"], 2)
        self.assertTrue(rep.offline_121_gates_verified)
        self.assertFalse(rep.all_124_gates_verified)
        self.assertTrue(rep.g13_to_g124_all_passed)
        self.assertTrue(rep.g123_to_g124_all_passed)
        self.assertTrue(rep.h0_h1_trial_entry_allowed)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.cross_model_flash_authorized)
        self.assertEqual(len(rep.gates), 124)

    def test_60_master_124_dry_run_mode_124_of_124_and_redlines_locked(self) -> None:
        rep = evaluate_124gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            master_122_override=self.clean_dryrun_122,
        )
        self.assertEqual(rep.status, "VERIFIED_ALL_124_GATES_DRY_RUN_SIMULATED_BACKUP")
        self.assertTrue(rep.all_124_gates_verified)
        self.assertTrue(rep.dry_run_rehearsal_only)
        self.assertEqual(rep.summary["verified_gates"], 124)
        self.assertEqual(rep.summary["blocked_or_pending_gates"], 0)
        self.assertEqual(rep.summary["g01_to_g12_verified"], 12)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.hardware_live_attachment_authorized)
        self.assertFalse(rep.el3_payload_transmit_authorized)
        self.assertFalse(rep.spi_nor_write_authorized)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.cross_model_flash_authorized)
        self.assertEqual(rep.usb_packets_transmitted, 0)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_61_master_124_dry_run_flag_aliases(self) -> None:
        rep1 = evaluate_124gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            simulate_bench_dry_run=True,
            master_122_override=self.clean_dryrun_122,
        )
        self.assertTrue(rep1.all_124_gates_verified)
        self.assertTrue(rep1.dry_run_rehearsal_only)

        rep2 = evaluate_124gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated_backup=True,
            master_122_override=self.clean_dryrun_122,
        )
        self.assertTrue(rep2.all_124_gates_verified)
        self.assertTrue(rep2.dry_run_rehearsal_only)

    def test_62_master_124_propagates_g123_and_g124_failures(self) -> None:
        rep123 = evaluate_124gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            sensor_cleaning_ev_comp_kwargs={
                "sensor_cleaning_requested": True,
                "battery_pct": 40,
            },
            master_122_override=self.clean_dryrun_122,
        )
        self.assertEqual(
            rep123.status,
            STATUS_BLOCKED_G123_CLEANING_LOW_BATTERY_OR_ACTIVE_MOUNT_VIOLATION,
        )
        self.assertFalse(rep123.g123_to_g124_all_passed)
        self.assertFalse(rep123.all_124_gates_verified)

        rep124 = evaluate_124gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            focus_mode_playback_rotate_kwargs={
                "rotate_requested": True,
                "playback_media_slot": "Slot 1",
                "slot_1_write_protected": True,
            },
            master_122_override=self.clean_dryrun_122,
        )
        self.assertEqual(
            rep124.status,
            STATUS_BLOCKED_G124_SLOT1_ROTATE_WRITE_VAULT_VIOLATION,
        )
        self.assertFalse(rep124.g123_to_g124_all_passed)
        self.assertFalse(rep124.all_124_gates_verified)

    def test_63_master_124_propagates_upstream_g122_failure(self) -> None:
        broken_122 = dataclasses.replace(
            self.clean_dryrun_122,
            g13_to_g122_all_passed=False,
            status="BLOCKED_G122_PHOTO_CAPTURE_DCI4K_OR_SLOT1_WRITE_VIOLATION",
        )
        rep = evaluate_124gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            master_122_override=broken_122,
        )
        self.assertEqual(
            rep.status, "BLOCKED_G122_PHOTO_CAPTURE_DCI4K_OR_SLOT1_WRITE_VIOLATION"
        )
        self.assertFalse(rep.g13_to_g124_all_passed)
        self.assertFalse(rep.all_124_gates_verified)

    def test_64_master_124_blocks_persistent_emmc_write_request(self) -> None:
        rep = evaluate_124gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            request_persistent_emmc_writes=True,
            master_122_override=self.clean_dryrun_122,
        )
        self.assertEqual(rep.status, "BLOCKED_BY_PERSISTENT_EMMC_WRITE_REDLINE")
        self.assertFalse(rep.all_124_gates_verified)
        self.assertFalse(rep.h0_h1_trial_entry_allowed)

    def test_65_master_124_gate_sequence_g121_to_g124_exact(self) -> None:
        rep = evaluate_124gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            master_122_override=self.clean_dryrun_122,
        )
        self.assertEqual(rep.gates[-1]["gate_id"], G124_GATE_ID)
        self.assertEqual(rep.gates[-2]["gate_id"], G123_GATE_ID)
        self.assertEqual(
            rep.gates[-3]["gate_id"],
            "G122_recall_custom_hold_camset_card_path_photo_capture_and_enlarge_guard",
        )
        self.assertEqual(
            rep.gates[-4]["gate_id"],
            "G121_dci4k_uhd_longgop_hdmi_raw_and_still_aspect_ratio_guard",
        )

    def test_66_master_124_to_dict_is_json_serializable(self) -> None:
        rep = evaluate_124gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=False,
            master_122_override=self.clean_offline_122,
        )
        loaded = json.loads(json.dumps(rep.to_dict()))
        self.assertEqual(loaded["summary"]["total_gates"], 124)
        self.assertEqual(loaded["summary"]["verified_gates"], 121)
        self.assertEqual(loaded["summary"]["g123_to_g124_verified"], 2)
        self.assertFalse(loaded["cross_model_flash_authorized"])

    def test_67_master_124_full_live_stack_without_override(self) -> None:
        rep_off = evaluate_124gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=False,
        )
        self.assertTrue(rep_off.offline_121_gates_verified)
        self.assertEqual(rep_off.summary["verified_gates"], 121)
        self.assertEqual(rep_off.status, "VERIFIED_121_OF_124_AWAITING_PHYSICAL_TIER0")

        rep_dry = evaluate_124gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
        )
        self.assertTrue(rep_dry.all_124_gates_verified)
        self.assertEqual(rep_dry.summary["verified_gates"], 124)
        self.assertEqual(
            rep_dry.status, "VERIFIED_ALL_124_GATES_DRY_RUN_SIMULATED_BACKUP"
        )

    def test_68_fx3_clean_room_test_and_force_clean_room_env_in_master_124(self) -> None:
        for env_key in (ENV_CLEAN_ROOM_TEST_PHASE290, "FX3_FX6_FORCE_CLEAN_ROOM"):
            with mock.patch.dict(os.environ, {env_key: "1"}):
                self.assertTrue(_is_forced_clean_room())
                rep = evaluate_124gate_preflight(
                    master_122_override=self.clean_offline_122,
                )
                self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
                self.assertTrue(rep.clean_room_forced)

    def test_69_master_124_blocks_core_g01_g09_missing(self) -> None:
        broken_gates = list(self.clean_offline_122.gates)
        broken_gates[0] = dict(broken_gates[0], passed=False)
        broken_122 = dataclasses.replace(
            self.clean_offline_122, gates=tuple(broken_gates)
        )
        rep = evaluate_124gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=False,
            master_122_override=broken_122,
        )
        self.assertEqual(rep.status, "BLOCKED_BY_CORE_G01_G09_REFERENCE_MISSING")
        self.assertFalse(rep.offline_121_gates_verified)

    def test_70_master_124_embeds_master_122_g123_and_g124_dicts(self) -> None:
        rep = evaluate_124gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=False,
            master_122_override=self.clean_offline_122,
        )
        self.assertEqual(rep.master_122_report["summary"]["total_gates"], 122)
        self.assertEqual(rep.g123_result["status"], STATUS_VERIFIED_G123)
        self.assertEqual(rep.g124_result["status"], STATUS_VERIFIED_G124)

    def test_71_master_124_local_donor_o_rdonly_mode_if_donors_present(self) -> None:
        audit = audit_phase290_donor_contracts(force_clean_room=False)
        if audit.verification_mode == "LOCAL_DONOR_O_RDONLY":
            rep = evaluate_124gate_preflight(
                DEFAULT_REPO_ROOT,
                force_clean_room=False,
                dry_run_simulated=False,
            )
            self.assertEqual(rep.verification_mode, "LOCAL_DONOR_O_RDONLY")
            self.assertTrue(rep.offline_121_gates_verified)
            self.assertEqual(rep.summary["verified_gates"], 121)
        else:
            self.assertEqual(audit.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    # --- 5. CLI & Cross-Platform CI Portability Tests (Tests 72-82) ---

    def test_72_cli_verify_g123_text_summary_and_json(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cli_main(["verify-sensor-cleaning-and-ev-comp-guard", "--clean-room"])
        self.assertEqual(rc, 0)
        self.assertIn("gate=G123_", buf.getvalue())
        self.assertIn("fx6_ibis=False", buf.getvalue())
        self.assertIn("fx3_dial=False", buf.getvalue())

        jbuf = io.StringIO()
        with contextlib.redirect_stdout(jbuf):
            rc_j = cli_main(
                ["verify-g123-sensor-cleaning-ev-comp", "--clean-room", "--summary", "--json"]
            )
        self.assertEqual(rc_j, 0)
        data = json.loads(jbuf.getvalue())
        self.assertTrue(data["valid"])
        self.assertEqual(data["status"], STATUS_VERIFIED_G123)
        self.assertEqual(data["raw_firmware_bytes_leaked"], 0)

    def test_73_cli_verify_g124_text_summary_and_json(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cli_main(
                ["verify-focus-mode-and-playback-rotate-guard", "--clean-room"]
            )
        self.assertEqual(rc, 0)
        self.assertIn("gate=G124_", buf.getvalue())
        self.assertIn("fx6_af=False", buf.getvalue())
        self.assertIn("slot1_wp=True", buf.getvalue())

        jbuf = io.StringIO()
        with contextlib.redirect_stdout(jbuf):
            rc_j = cli_main(
                [
                    "verify-g124-focus-mode-playback-rotate",
                    "--clean-room",
                    "--summary",
                    "--json",
                ]
            )
        self.assertEqual(rc_j, 0)
        data = json.loads(jbuf.getvalue())
        self.assertTrue(data["valid"])
        self.assertEqual(data["status"], STATUS_VERIFIED_G124)

    def test_74_cli_verify_124_gates_offline_text_and_json(self) -> None:
        offline_124 = evaluate_124gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=False,
            master_122_override=self.clean_offline_122,
        )
        with mock.patch(
            "fx3_safety.__main__.evaluate_124gate_preflight",
            return_value=offline_124,
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = cli_main(["verify-124-gates", "--clean-room"])
            self.assertEqual(rc, 0)
            self.assertIn("verified=121/124", buf.getvalue())
            self.assertIn("overall_ready_for_hardware_attach=False", buf.getvalue())
            self.assertIn("cross_model_flash_authorized=False", buf.getvalue())

            jbuf = io.StringIO()
            with contextlib.redirect_stdout(jbuf):
                rc_j = cli_main(["verify-124-gates", "--clean-room", "--summary", "--json"])
            self.assertEqual(rc_j, 0)
            parsed = json.loads(jbuf.getvalue())
            self.assertEqual(parsed["summary"]["verified_gates"], 121)
            self.assertTrue(parsed["summary"]["offline_121_gates_verified"])

    def test_75_cli_verify_124_gates_dry_run_text_and_json(self) -> None:
        dryrun_124 = evaluate_124gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            master_122_override=self.clean_dryrun_122,
        )
        with mock.patch(
            "fx3_safety.__main__.evaluate_124gate_preflight",
            return_value=dryrun_124,
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = cli_main(
                    ["verify-124-gates", "--clean-room", "--simulate-bench-dry-run"]
                )
            self.assertEqual(rc, 0)
            self.assertIn("verified=124/124", buf.getvalue())

            jbuf = io.StringIO()
            with contextlib.redirect_stdout(jbuf):
                rc_j = cli_main(
                    [
                        "verify-124-gates",
                        "--clean-room",
                        "--simulate-bench-dry-run",
                        "--json",
                    ]
                )
            self.assertEqual(rc_j, 0)
            parsed = json.loads(jbuf.getvalue())
            self.assertTrue(parsed["all_124_gates_verified"])
            self.assertEqual(parsed["summary"]["verified_gates"], 124)

    def test_76_standalone_module_main_offline_summary_and_dry_run(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = module_main(["--clean-room"])
        self.assertEqual(rc, 0)
        self.assertIn("verified=121/124", buf.getvalue())

        jbuf = io.StringIO()
        with contextlib.redirect_stdout(jbuf):
            rc_j = module_main(
                ["--clean-room", "--simulate-bench-dry-run", "--summary", "--json"]
            )
        self.assertEqual(rc_j, 0)
        parsed = json.loads(jbuf.getvalue())
        self.assertEqual(parsed["summary"]["verified_gates"], 124)
        self.assertEqual(parsed["g123_status"], STATUS_VERIFIED_G123)
        self.assertEqual(parsed["g124_status"], STATUS_VERIFIED_G124)

    def test_77_subprocess_cli_verify_g123_g124_uses_sys_executable(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONPATH"] = str(DEFAULT_REPO_ROOT / "outputs" / "fx3-safety")
        for cmd, expected_status in (
            ("verify-sensor-cleaning-and-ev-comp-guard", STATUS_VERIFIED_G123),
            ("verify-focus-mode-and-playback-rotate-guard", STATUS_VERIFIED_G124),
        ):
            proc = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    "-m",
                    "fx3_safety",
                    cmd,
                    "--clean-room",
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

    def test_78_subprocess_cli_verify_124_gates_dry_run_uses_sys_executable(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONPATH"] = str(DEFAULT_REPO_ROOT / "outputs" / "fx3-safety")
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "fx3_safety",
                "verify-124-gates",
                "--clean-room",
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
        self.assertTrue(payload["all_124_gates_verified"])
        self.assertEqual(payload["summary"]["verified_gates"], 124)
        self.assertFalse(payload["overall_ready_for_hardware_attach"])
        self.assertFalse(payload["cross_model_flash_authorized"])
        self.assertEqual(payload["raw_firmware_bytes_leaked"], 0)

    def test_79_subprocess_cli_verify_124_gates_offline_uses_sys_executable(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONPATH"] = str(DEFAULT_REPO_ROOT / "outputs" / "fx3-safety")
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "fx3_safety",
                "verify-124-gates",
                "--clean-room",
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
        self.assertTrue(payload["offline_121_gates_verified"])
        self.assertFalse(payload["all_124_gates_verified"])
        self.assertEqual(payload["summary"]["verified_gates"], 121)

    def test_80_argparse_help_escaped_percent_portability_on_python314(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONPATH"] = str(DEFAULT_REPO_ROOT / "outputs" / "fx3-safety")
        for subcmd in (
            "verify-sensor-cleaning-and-ev-comp-guard",
            "verify-g123-sensor-cleaning-ev-comp",
            "verify-focus-mode-and-playback-rotate-guard",
            "verify-g124-focus-mode-playback-rotate",
            "verify-124-gates",
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
            self.assertEqual(proc.returncode, 0, msg=f"{subcmd} --help failed: {proc.stderr}")

        proc_mod = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "fx3_safety.realhw_sensor_cleaning_ev_comp_focus_mode_playback_rotate_and_124gate_guard",
                "--help",
            ],
            cwd=str(DEFAULT_REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=_subprocess_timeout_seconds(),
            check=False,
        )
        self.assertEqual(proc_mod.returncode, 0, msg=proc_mod.stderr)
        self.assertIn("51%", proc_mod.stdout)

    def test_81_no_hardcoded_usr_bin_python3_or_bare_percent_in_phase290_files(self) -> None:
        test_src = Path(__file__).read_text(encoding="utf-8")
        # Check line-by-line so string literals in this assertion do not false-positive
        forbidden = "/usr/bin/" + "python3"
        self.assertNotIn(forbidden, test_src)
        guard_path = (
            DEFAULT_REPO_ROOT
            / "outputs"
            / "fx3-safety"
            / "fx3_safety"
            / "realhw_sensor_cleaning_ev_comp_focus_mode_playback_rotate_and_124gate_guard.py"
        )
        self.assertNotIn(forbidden, guard_path.read_text(encoding="utf-8"))

    def test_82_offline_verify_124_gates_with_fx3_clean_room_test_env_var(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONPATH"] = str(DEFAULT_REPO_ROOT / "outputs" / "fx3-safety")
        env[ENV_CLEAN_ROOM_TEST_PHASE290] = "1"
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "fx3_safety",
                "verify-124-gates",
                "--summary",
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
        self.assertEqual(payload["verification_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(payload["summary"]["verified_gates"], 121)


if __name__ == "__main__":
    unittest.main()
