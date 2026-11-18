"""Phase 280 (280th Milestone, Task H321, 116/116 Safety Gates, Wave-48) Dual-Mode
Unit Tests (78 tests, < 5.0s runtime) for
`fx3_safety.realhw_pp_scinetone_creativelook_dro_wb_metering_and_116gate_guard`:

- Gate `G115` (`GATE_G115_PICTURE_PROFILE_SCINETONE_CREATIVE_LOOK_DRO_AND_LOG_SHOOTING_GUARD`):
  - Out-of-box `ILME-FX3 Ver. 7.02` (`ilc/2210`) `[Picture Profile]` (`_f.uxc` `0x6830`)
    defaults to `PP11` (`S-Cinetone`, `0x67ab`/`0x6e61`) for BOTH Movie AND Still unless
    decoupled via `[Different Set for Still/Mv]` (`0x62ee`); whenever `[Picture Profile] != Off`,
    `[Creative Look]` (`0x6823`: 10 presets `ST..SE` + `CREATIVE_BOX_1..6`, 8 params) is locked
    to `'-'` and `[D-Range Optimizer]` (`0xe89c`: `Auto` / `Lv1..Lv5`) is locked to `Off`.
  - `[Log Shooting]` (`Flexible ISO`, `Cine EI Quick`, `Cine EI`, `0x6020`) hard-locks
    `[Picture Profile]` -> `Off`, `[Creative Look]` -> `'-'`, `[D-Range Optimizer]` -> `Off`,
    and movie `[Gamma Display Assist]` -> `Off` (`STATUS_BLOCKED_G115_LOG_SHOOTING_DOUBLE_PP_CORRUPTION_VIOLATION`).
  - `PPLUT1..4` are Movie-only and clamp internal-recording HDMI output to `1080p`
    (`STATUS_BLOCKED_G115_PPLUT_STILL_OR_HDMI_CLAMP_VIOLATION`).
  - Reset trap guard: `[Camera Settings Reset]` and `[Initialize]` restore active PP selector
    to `PP11`, yet customized internal parameters inside `PP1..PP11` and
    `[Different Set for Still/Mv]` check marks SURVIVE BOTH unless `[PPx] -> [Reset]` is
    explicitly invoked (`STATUS_BLOCKED_G115_PP_INTERNAL_PARAM_UNRESET_TRAP`) across 512
    exhaustive matrix states vs `FX6 Ver. 6.01` (`Base Look` `Custom` default `S-Cinetone`).
- Gate `G116` (`GATE_G116_WHITE_BALANCE_CINE_EI_CUSTOM_SETUP_AND_METERING_MODE_GUARD`):
  - `[White Balance]` (`0xe5d4`): `Auto` default (`Priority Set in AWB`: `Standard`/`Ambience`/
    `White` `0x67a7`), fixed presets, `C.Temp./Filter` (`2500K..9900K` in `100K` steps = 75 steps
    + `A7..B7`/`G7..M7` `[-7..+7]`), `Custom 1..3` (`0xe79d..0xe79c`), Still `[Shutter AWB Lock]`
    (`Off` default `0x66db`, NOT resettable by `Camera Settings Reset`), Movie `[Shockless WB]`
    (`1 (Fast)` default `0x62fe`).
  - `Cine EI` / `Cine EI Quick`: `[Auto]` and `[Underwater Auto]` blocked
    (`STATUS_BLOCKED_G116_CINE_EI_AWB_VIOLATION`); `[Custom Setup]` under `[Log Shooting] != Off`
    or `S-Log3`/`PPLUT1..4` blocked (`STATUS_BLOCKED_G116_LOG_CUSTOM_WB_CAPTURE_TRAP`);
    `Custom 1..3` survives `[Camera Settings Reset]` and CANNOT be saved to `CAMSET`
    (`STATUS_BLOCKED_G116_WB_OR_METERING_RESET_CAMSET_BOUNDARY_VIOLATION`).
  - `[Metering Mode]` (`0xe5cf`): all **6** modes (`Multi`, `Center`, `Spot: Standard`,
    `Spot: Large`, `Entire Screen Avg.`, `Highlight`), `[Face Priority in Multi Metering]`
    (`On` default `0x69c7` — hard-locked `Off` when `[De-Squeeze Display] != Off`),
    `[Spot Metering Point]` (`Center`/`Focus Point Link` `0x625c` — locked `Center` on
    `Wide`/`Zone`/`Center Fix`), Still `[AEL w/ Shutter]` (`Auto` default `0x669d`, survives
    `Camera Settings Reset`), and `Cine EI` Base ISO (`800`/`12800`) `M.M.` passive monitoring
    invariance across 288 matrix states vs `FX6 Ver. 6.01` (`Memory A`/`B`/`ATW`).
- Unified `116`-Gate Master Safety Preflight (`evaluate_116gate_preflight` / `verify-116-gates`):
  `113/116` offline (`VERIFIED_113_OF_116_AWAITING_PHYSICAL_TIER0`) and `116/116` in
  `--simulate-bench-dry-run` (`VERIFIED_ALL_116_GATES_DRY_RUN_SIMULATED_BACKUP`) with all
  hardware write/live-attach redlines hard-locked `False`.
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
    AEL_W_SHUTTER_AUTO_G116,
    AEL_W_SHUTTER_DEFAULT_G116,
    AEL_W_SHUTTER_MENU_PATH_G116,
    AEL_W_SHUTTER_OFF_G116,
    AEL_W_SHUTTER_ON_G116,
    ALLOWED_AEL_W_SHUTTER_MODES_G116,
    ALLOWED_CREATIVE_LOOKS_G115,
    ALLOWED_DESQUEEZE_MODES_G116,
    ALLOWED_DRO_MODES_G115,
    ALLOWED_FOCUS_AREAS_G116,
    ALLOWED_HDMI_OUT_RESOLUTIONS_G115,
    ALLOWED_LOG_SHOOTING_MODES_G115,
    ALLOWED_PICTURE_PROFILES_G115,
    ALLOWED_PRIORITY_AWB_MODES_G116,
    ALLOWED_RESET_ACTIONS_PHASE280,
    ALLOWED_SHOCKLESS_WB_MODES_G116,
    ALLOWED_SHOOT_MODES_PHASE280,
    ALLOWED_SHUTTER_AWB_LOCK_MODES_G116,
    ALLOWED_SPOT_METERING_POINTS_G116,
    ALLOWED_WHITE_BALANCE_MODES_G116,
    CINE_EI_BASE_ISOS_G116,
    CREATIVE_LOOK_10_PRESETS_G115,
    CREATIVE_LOOK_8_PARAMS_G115,
    CREATIVE_LOOK_CUSTOM_SLOTS_G115,
    CREATIVE_LOOK_FACTORY_DEFAULT_G115,
    CREATIVE_LOOK_LOCKED_VALUE_G115,
    CREATIVE_LOOK_MENU_PATH_G115,
    CREATIVE_LOOK_UXC_RESID16_G115,
    DEFAULT_REPO_ROOT,
    DIFFERENT_SET_PP_DEFAULT_CHECKED_G115,
    DIFFERENT_SET_RESID16_G115,
    DIFFERENT_SET_STILL_MV_MENU_PATH_G115,
    DONOR_CHECK_CI_MAX_SECONDS_PHASE280,
    DONOR_CHECK_MAX_SECONDS_PHASE280,
    DRO_AUTO_G115,
    DRO_FACTORY_DEFAULT_G115,
    DRO_MENU_PATH_G115,
    DRO_OFF_G115,
    DRO_UXC_RESID16_G115,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    ENV_CLEAN_ROOM_TEST_PHASE280,
    FACE_PRIORITY_MULTI_DEFAULT_G116,
    FACE_PRIORITY_MULTI_METERING_MENU_PATH_G116,
    FACE_PRIORITY_MULTI_OFF_G116,
    FACE_PRIORITY_MULTI_ON_G116,
    FACE_PRIORITY_MULTI_RESID16_G116,
    FX3_DEFAULT_FW_VERSION_PHASE280,
    FX3_EXACT_6_METERING_MODES_G116,
    FX3_HELP_GUIDE_CODE_PHASE280,
    FX3_MODEL_ID,
    FX3_MODEL_NAME,
    FX6_BASE_LOOK_CUSTOM_DEFAULT_G115,
    FX6_DEFAULT_FW_VERSION_PHASE280,
    FX6_MODEL_NAME_PHASE280,
    FX6_PRESET_CINE_EI_KELVINS_G116,
    FX6_PRESET_CUSTOM_KELVINS_G116,
    G115,
    G115_GATE_CODE,
    G115_GATE_ID,
    G116,
    G116_GATE_CODE,
    G116_GATE_ID,
    GATE_G115_PICTURE_PROFILE_SCINETONE_CREATIVE_LOOK_DRO_AND_LOG_SHOOTING_GUARD,
    GATE_G116_WHITE_BALANCE_CINE_EI_CUSTOM_SETUP_AND_METERING_MODE_GUARD,
    HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    HDMI_RES_1080P_G115,
    HDMI_RES_2160P_G115,
    HDMI_RES_AUTO_G115,
    HUMAN_HARDWARE_ATTACH_TOKEN,
    LOG_SHOOTING_CINE_EI_G115,
    LOG_SHOOTING_CINE_EI_QUICK_G115,
    LOG_SHOOTING_FLEXIBLE_ISO_G115,
    LOG_SHOOTING_MENU_PATH_G115,
    LOG_SHOOTING_OFF_G115,
    LOG_SHOOTING_UXC_RESID16_G115,
    METERING_MODE_CENTER_G116,
    METERING_MODE_ENTIRE_SCREEN_AVG_G116,
    METERING_MODE_FACTORY_DEFAULT_G116,
    METERING_MODE_HIGHLIGHT_G116,
    METERING_MODE_MENU_PATH_G116,
    METERING_MODE_MULTI_G116,
    METERING_MODE_SPOT_LARGE_G116,
    METERING_MODE_SPOT_STANDARD_G116,
    METERING_MODE_UXC_RESID16_G116,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED,
    PHYSICAL_USB_PACKETS_EMITTED,
    PICTURE_PROFILE_DEFAULT_CURVES_G115,
    PICTURE_PROFILE_MENU_PATH_G115,
    PICTURE_PROFILE_PP11_RESID16_G115,
    PICTURE_PROFILE_UXC_RESID16_G115,
    PINNED_FX3_APPFW_SLICES_PHASE280,
    PINNED_FX3_APPFW_SLICES_SHA256_PHASE280,
    PINNED_FX6_APPFW_SLICES_PHASE280,
    PINNED_FX6_APPFW_SLICES_SHA256_PHASE280,
    PINNED_PHASE280_DONOR_SPECS,
    PPLUT_PICTURE_PROFILES_G115,
    PP_1_TO_11_G115,
    PP_FACTORY_DEFAULT_G115,
    PP_OFF_G115,
    PRIORITY_AWB_AMBIENCE_G116,
    PRIORITY_AWB_FACTORY_DEFAULT_G116,
    PRIORITY_AWB_RESID16_G116,
    PRIORITY_AWB_STANDARD_G116,
    PRIORITY_AWB_WHITE_G116,
    PRIORITY_SET_IN_AWB_MENU_PATH_G116,
    RAW_FIRMWARE_BYTES_LEAKED,
    REALHW_PP_SCINETONE_CREATIVELOOK_DRO_WB_METERING_116GATE_SCHEMA,
    REALHW_PP_SCINETONE_CREATIVELOOK_DRO_WB_METERING_116GATE_VERSION,
    RESET_ACTION_CAMERA_SETTINGS_RESET,
    RESET_ACTION_INITIALIZE,
    RESET_ACTION_NONE,
    RESET_ACTION_PP_SLOT_RESET_PHASE280,
    RESET_ACTION_RESET_NETWORK_SET_PHASE280,
    SCINETONE_RESID16_G115,
    SHOCKLESS_WB_1_FAST_G116,
    SHOCKLESS_WB_3_SLOW_G116,
    SHOCKLESS_WB_FACTORY_DEFAULT_G116,
    SHOCKLESS_WB_MENU_PATH_G116,
    SHOCKLESS_WB_OFF_G116,
    SHOOT_MODE_INTELLIGENT_AUTO_PHASE280,
    SHOOT_MODE_MOVIE_PHASE280,
    SHOOT_MODE_SQ_PHASE280,
    SHOOT_MODE_STILL_PHASE280,
    SHUTTER_AWB_LOCK_CONT_SHOOTING_G116,
    SHUTTER_AWB_LOCK_FACTORY_DEFAULT_G116,
    SHUTTER_AWB_LOCK_HALF_PRESS_G116,
    SHUTTER_AWB_LOCK_MENU_PATH_G116,
    SHUTTER_AWB_LOCK_OFF_G116,
    SLOG3_PICTURE_PROFILES_G115,
    SPI_NOR_WRITE_AUTHORIZED,
    SPOT_METERING_CENTER_LOCKED_FOCUS_AREAS_G116,
    SPOT_METERING_LINKABLE_FOCUS_AREAS_G116,
    SPOT_METERING_POINT_CENTER_G116,
    SPOT_METERING_POINT_DEFAULT_G116,
    SPOT_METERING_POINT_FOCUS_LINK_G116,
    SPOT_METERING_POINT_MENU_PATH_G116,
    STATUS_BLOCKED_G115_LOG_SHOOTING_DOUBLE_PP_CORRUPTION_VIOLATION,
    STATUS_BLOCKED_G115_PPLUT_STILL_OR_HDMI_CLAMP_VIOLATION,
    STATUS_BLOCKED_G115_PP_CREATIVELOOK_DRO_MUTUAL_EXCLUSION_VIOLATION,
    STATUS_BLOCKED_G115_PP_INTERNAL_PARAM_UNRESET_TRAP,
    STATUS_BLOCKED_G115_TELEMETRY_INVALID,
    STATUS_BLOCKED_G116_CINE_EI_AWB_VIOLATION,
    STATUS_BLOCKED_G116_LOG_CUSTOM_WB_CAPTURE_TRAP,
    STATUS_BLOCKED_G116_METERING_OR_CINE_EI_BASE_ISO_VIOLATION,
    STATUS_BLOCKED_G116_TELEMETRY_INVALID,
    STATUS_BLOCKED_G116_WB_OR_METERING_RESET_CAMSET_BOUNDARY_VIOLATION,
    STATUS_BLOCKED_PHASE280_DONOR_INTEGRITY,
    STATUS_VERIFIED_G115,
    STATUS_VERIFIED_G116,
    USB_PACKETS_TRANSMITTED,
    WB_AUTO_G116,
    WB_CTEMP_FILTER_G116,
    WB_CTEMP_MAX_K_G116,
    WB_CTEMP_MIN_K_G116,
    WB_CTEMP_STEP_K_G116,
    WB_CTEMP_TOTAL_STEPS_G116,
    WB_CUSTOM_1_G116,
    WB_CUSTOM_2_G116,
    WB_CUSTOM_3_G116,
    WB_FACTORY_DEFAULT_G116,
    WB_FINE_TRIM_MAX_G116,
    WB_FINE_TRIM_MIN_G116,
    WB_FLASH_G116,
    WB_UNDERWATER_AUTO_G116,
    WHITE_BALANCE_MENU_PATH_G116,
    WHITE_BALANCE_UXC_RESID16_G116,
    Master116GateReport,
    Phase280DonorAuditResult,
    _default_donor_budget_seconds_phase280,
    _is_forced_clean_room,
    audit_phase280_donor_contracts,
    compute_pp_scinetone_creativelook_dro_matrix,
    compute_wb_cineei_and_metering_matrix,
    evaluate_116_master_safety_gates,
    evaluate_116gate_preflight,
    evaluate_g115_pp_scinetone_creativelook_dro_guard,
    evaluate_g116_wb_cineei_and_metering_guard,
    main as module_main,
    resolve_fx3_pp_scinetone_creativelook_dro_state,
    resolve_fx3_wb_cineei_and_metering_state,
    run_116_gate_preflight,
    verify_pp_scinetone_creativelook_dro_guard,
    verify_wb_cineei_and_metering_guard,
)
from fx3_safety.realhw_usb_mode_hdmi_info_protect_network_reset_and_114gate_guard import (
    Master114GateReport,
    evaluate_114gate_preflight,
)


def _subprocess_timeout_seconds() -> float:
    return (
        15.0
        if os.environ.get("GITHUB_ACTIONS", "").strip().lower() == "true"
        else 10.0
    )


def _make_clean_114_override(
    dry_run_simulated: bool,
    *,
    verification_mode: str = "CLEAN_ROOM_SYNTHETIC",
) -> Master114GateReport:
    gates_114 = []
    for idx in range(1, 115):
        gid = f"G{idx:02d}"
        if idx in (10, 11, 12) and not dry_run_simulated:
            passed = False
            status = "PENDING_PHYSICAL_TIER0"
        else:
            passed = True
            status = "VERIFIED_SAFE"
        gates_114.append(
            {
                "gate_id": gid,
                "gate_code": gid,
                "status": status,
                "passed": passed,
                "evidence": f"synthetic_{gid}",
                "violation_codes": [],
            }
        )
    g01_to_g12_verified = 12 if dry_run_simulated else 9
    verified_total = g01_to_g12_verified + 102
    summary = {
        "total_gates": 114,
        "verified_gates": verified_total,
        "technical_gates_passed": verified_total,
        "blocked_or_pending_gates": 114 - verified_total,
        "g01_to_g12_verified": g01_to_g12_verified,
        "g13_to_g112_verified": 100,
        "g113_to_g114_verified": 2,
        "g13_to_g114_all_passed": True,
        "g113_to_g114_all_passed": True,
        "offline_111_gates_verified": True,
        "all_114_gates_verified": bool(dry_run_simulated),
        "dry_run_rehearsal_only": bool(dry_run_simulated),
        "overall_ready_for_hardware_attach": False,
        "hardware_live_attachment_authorized": False,
        "h0_h1_trial_entry_allowed": True,
        "agent_auto_flash_blocked": True,
        "human_hardware_attach_token": False,
        "physical_flash_auto_exec_authorized": False,
        "el3_payload_transmit_authorized": False,
        "spi_nor_write_authorized": False,
        "persistent_emmc_writes_authorized": False,
        "persistent_write_release": False,
        "usb_packets_transmitted": 0,
        "physical_usb_packets_emitted": 0,
        "raw_firmware_bytes_leaked": 0,
    }
    return Master114GateReport(
        schema="realhw_usb_mode_hdmi_info_protect_network_reset_and_114gate_guard_v1",
        version="1.0.0",
        evaluated_utc="2026-11-17T00:00:00+00:00",
        verification_mode=verification_mode,
        clean_room_forced=(verification_mode == "CLEAN_ROOM_SYNTHETIC"),
        dry_run_rehearsal_only=bool(dry_run_simulated),
        overall_ready_for_hardware_attach=False,
        hardware_live_attachment_authorized=False,
        offline_111_gates_verified=True,
        all_114_gates_verified=bool(dry_run_simulated),
        g13_to_g114_all_passed=True,
        g113_to_g114_all_passed=True,
        h0_h1_trial_entry_allowed=True,
        status=(
            "VERIFIED_ALL_114_GATES_DRY_RUN_SIMULATED_BACKUP"
            if dry_run_simulated
            else "VERIFIED_111_OF_114_AWAITING_PHYSICAL_TIER0"
        ),
        agent_auto_flash_blocked=True,
        human_hardware_attach_token=False,
        el3_payload_transmit_authorized=False,
        spi_nor_write_authorized=False,
        persistent_emmc_writes_authorized=False,
        persistent_write_release=False,
        physical_flash_auto_exec_authorized=False,
        usb_packets_transmitted=0,
        physical_usb_packets_emitted=0,
        raw_firmware_bytes_leaked=0,
        technical_gates_passed=verified_total,
        summary=summary,
        gates=tuple(gates_114),
        master_112_report={"status": "SYNTHETIC"},
        g113_result={"status": "VERIFIED_G113"},
        g114_result={"status": "VERIFIED_G114"},
        errors=(),
        warnings=(),
    )


class Phase280PpScinetoneCreativeLookDroWbMetering116GateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.active_audit = audit_phase280_donor_contracts(repo_root=DEFAULT_REPO_ROOT)
        cls.clean_audit = audit_phase280_donor_contracts(
            repo_root=DEFAULT_REPO_ROOT,
            force_clean_room=True,
        )
        cls.clean_offline_114 = _make_clean_114_override(False)
        cls.clean_dryrun_114 = _make_clean_114_override(True)

    # ------------------------------------------------------------------
    # 01..10: Exports, Redlines & Dual-Mode O_RDONLY / Clean-Room Audit
    # ------------------------------------------------------------------

    def test_01_public_exports_and_schema_metadata(self) -> None:
        self.assertEqual(
            REALHW_PP_SCINETONE_CREATIVELOOK_DRO_WB_METERING_116GATE_SCHEMA,
            "realhw_pp_scinetone_creativelook_dro_wb_metering_and_116gate_guard_v1",
        )
        self.assertEqual(
            REALHW_PP_SCINETONE_CREATIVELOOK_DRO_WB_METERING_116GATE_VERSION,
            "1.0.0",
        )
        for sym in (
            "G115_GATE_ID",
            "G116_GATE_ID",
            "audit_phase280_donor_contracts",
            "verify_pp_scinetone_creativelook_dro_guard",
            "verify_wb_cineei_and_metering_guard",
            "evaluate_g115_pp_scinetone_creativelook_dro_guard",
            "evaluate_g116_wb_cineei_and_metering_guard",
            "evaluate_116gate_preflight",
            "evaluate_116_master_safety_gates",
            "run_116_gate_preflight",
            "Master116GateReport",
        ):
            self.assertIn(sym, fx3_safety.__all__)
            self.assertTrue(hasattr(fx3_safety, sym))

    def test_02_hard_locked_safety_redlines_always_false_and_zero(self) -> None:
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

    def test_03_gate_constants_and_ci_budget_constants(self) -> None:
        self.assertEqual(G115, G115_GATE_ID)
        self.assertEqual(G116, G116_GATE_ID)
        self.assertEqual(
            GATE_G115_PICTURE_PROFILE_SCINETONE_CREATIVE_LOOK_DRO_AND_LOG_SHOOTING_GUARD,
            G115_GATE_CODE,
        )
        self.assertEqual(
            GATE_G116_WHITE_BALANCE_CINE_EI_CUSTOM_SETUP_AND_METERING_MODE_GUARD,
            G116_GATE_CODE,
        )
        self.assertEqual(DONOR_CHECK_MAX_SECONDS_PHASE280, 0.20)
        self.assertEqual(DONOR_CHECK_CI_MAX_SECONDS_PHASE280, 1.00)
        with mock.patch.dict(os.environ, {"GITHUB_ACTIONS": "true"}):
            self.assertEqual(_default_donor_budget_seconds_phase280(), 1.00)
        with mock.patch.dict(os.environ, {"GITHUB_ACTIONS": ""}):
            self.assertEqual(_default_donor_budget_seconds_phase280(), 0.20)

    def test_04_active_donor_audit_is_valid_fast_and_zero_leak(self) -> None:
        audit = self.active_audit
        self.assertTrue(audit.valid, msg=audit.errors)
        self.assertTrue(audit.within_budget_200ms)
        self.assertEqual(audit.raw_firmware_bytes_leaked, 0)
        self.assertTrue(audit.fx3_contracts_verified)
        self.assertTrue(audit.fx6_contracts_verified)
        self.assertTrue(audit.four_lang_resid16_parity_verified)
        self.assertIn(
            audit.verification_mode,
            ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"),
        )
        if audit.verification_mode == "LOCAL_DONOR_O_RDONLY":
            self.assertEqual(audit.files_inspected, len(PINNED_PHASE280_DONOR_SPECS))
            self.assertEqual(
                audit.sha256_by_artifact["fx3_appfw_so"],
                PINNED_FX3_APPFW_SLICES_SHA256_PHASE280,
            )
            self.assertEqual(
                audit.sha256_by_artifact["fx6_appfw_so"],
                PINNED_FX6_APPFW_SLICES_SHA256_PHASE280,
            )

    def test_05_forced_clean_room_audit_deterministic_and_fast(self) -> None:
        self.assertTrue(self.clean_audit.valid)
        self.assertEqual(self.clean_audit.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(self.clean_audit.access_mode, "SYNTHETIC_CLEAN_ROOM")
        self.assertEqual(self.clean_audit.files_inspected, 0)
        self.assertTrue(self.clean_audit.within_budget_200ms)
        self.assertEqual(self.clean_audit.raw_firmware_bytes_leaked, 0)
        self.assertEqual(
            len(self.clean_audit.checked_markers),
            len(PINNED_PHASE280_DONOR_SPECS),
        )

    def test_06_env_vars_force_clean_room_mode(self) -> None:
        for key in (ENV_CLEAN_ROOM_TEST_PHASE280, "FX3_FX6_FORCE_CLEAN_ROOM"):
            with mock.patch.dict(os.environ, {key: "1"}):
                self.assertTrue(_is_forced_clean_room())
                audit = audit_phase280_donor_contracts(repo_root=DEFAULT_REPO_ROOT)
                self.assertEqual(audit.verification_mode, "CLEAN_ROOM_SYNTHETIC")
                self.assertTrue(audit.valid)

    def test_07_missing_donor_root_gracefully_falls_back_to_clean_room(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            audit = audit_phase280_donor_contracts(
                work_root=Path(tmpdir) / "nonexistent",
                force_clean_room=False,
            )
            self.assertTrue(audit.valid)
            self.assertEqual(audit.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertEqual(audit.raw_firmware_bytes_leaked, 0)

    def test_08_tampered_donor_file_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            work_root = Path(tmpdir)
            for key, (
                _body,
                rel_path,
                exp_size,
                _sha,
                _markers,
                _label,
            ) in PINNED_PHASE280_DONOR_SPECS.items():
                fp = work_root / rel_path
                fp.parent.mkdir(parents=True, exist_ok=True)
                if key == "fx3_appfw_so":
                    fp.write_bytes(b"\x00" * 64)
                else:
                    fp.write_bytes(b"\x00" * min(exp_size, 128))
            audit = audit_phase280_donor_contracts(
                work_root=work_root,
                force_clean_room=False,
            )
            self.assertFalse(audit.valid)
            self.assertEqual(audit.status, STATUS_BLOCKED_PHASE280_DONOR_INTEGRITY)
            self.assertGreater(len(audit.missing_markers), 0)
            self.assertEqual(audit.raw_firmware_bytes_leaked, 0)

    def test_09_budget_exceeded_marks_donor_audit_invalid(self) -> None:
        res = audit_phase280_donor_contracts(
            force_clean_room=True,
            max_budget_seconds=-1.0,
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_PHASE280_DONOR_INTEGRITY)
        self.assertFalse(res.within_budget_200ms)

    def test_10_pinned_slice_specs_unique_and_non_overlapping_metadata(self) -> None:
        self.assertEqual(len(PINNED_FX3_APPFW_SLICES_PHASE280), 22)
        self.assertEqual(len(PINNED_FX6_APPFW_SLICES_PHASE280), 6)
        self.assertEqual(len(PINNED_PHASE280_DONOR_SPECS), 11)
        fx3_tokens = [tok for _off, tok in PINNED_FX3_APPFW_SLICES_PHASE280]
        self.assertEqual(len(set(fx3_tokens)), len(fx3_tokens))
        self.assertIn(b"BKID_APP_setting_picture_profile", fx3_tokens)
        self.assertIn(b"BKID_APP_setting_white_balance", fx3_tokens)
        self.assertIn(b"BKID_APP_setting_metering_mode", fx3_tokens)

    # ------------------------------------------------------------------
    # 11..32: Gate G115 — [Picture Profile] PP11, [Creative Look], [DRO], [Log]
    # ------------------------------------------------------------------

    def test_11_g115_default_out_of_box_fx3_pp11_passes(self) -> None:
        res = verify_pp_scinetone_creativelook_dro_guard()
        self.assertTrue(res.valid, msg=res.errors)
        self.assertEqual(res.status, STATUS_VERIFIED_G115)
        self.assertEqual(res.fx3_oob_picture_profile_default, "PP11")
        self.assertEqual(res.effective_picture_profile, "PP11")
        self.assertEqual(res.effective_picture_profile_still, "PP11")
        self.assertEqual(res.effective_creative_look, "-")
        self.assertEqual(res.effective_dro, "Off")
        self.assertTrue(res.creative_look_and_dro_locked)
        self.assertFalse(res.different_set_pp_checked)
        self.assertEqual(res.matrix_states_checked, 512)

    def test_12_g115_menu_paths_resid16_and_creative_look_10_presets(self) -> None:
        self.assertEqual(
            PICTURE_PROFILE_MENU_PATH_G115,
            "MENU -> Exposure/Color -> [Color/Tone] -> [Picture Profile]",
        )
        self.assertEqual(
            DIFFERENT_SET_STILL_MV_MENU_PATH_G115,
            "MENU -> Setup -> [Operation Customize] -> [Different Set for Still/Mv]",
        )
        self.assertEqual(
            CREATIVE_LOOK_MENU_PATH_G115,
            "MENU -> Exposure/Color -> [Color/Tone] -> [Creative Look]",
        )
        self.assertEqual(
            DRO_MENU_PATH_G115,
            "MENU -> Exposure/Color -> [Exposure Comp.] -> [D-Range Optimizer]",
        )
        self.assertEqual(
            LOG_SHOOTING_MENU_PATH_G115,
            "MENU -> Shooting -> [Image Quality/Rec] -> [Log Shooting Setting]",
        )
        self.assertEqual(PICTURE_PROFILE_UXC_RESID16_G115, 0x6830)
        self.assertEqual(PICTURE_PROFILE_PP11_RESID16_G115, 0x67AB)
        self.assertEqual(SCINETONE_RESID16_G115, 0x6E61)
        self.assertEqual(DIFFERENT_SET_RESID16_G115, 0x62EE)
        self.assertEqual(CREATIVE_LOOK_UXC_RESID16_G115, 0x6823)
        self.assertEqual(DRO_UXC_RESID16_G115, 0xE89C)
        self.assertEqual(LOG_SHOOTING_UXC_RESID16_G115, 0x6020)
        self.assertEqual(
            CREATIVE_LOOK_10_PRESETS_G115,
            ("ST", "PT", "NT", "VV", "VV2", "FL", "IN", "SH", "BW", "SE"),
        )
        self.assertEqual(len(CREATIVE_LOOK_CUSTOM_SLOTS_G115), 6)
        self.assertEqual(len(CREATIVE_LOOK_8_PARAMS_G115), 8)
        self.assertEqual(len(PP_1_TO_11_G115), 11)
        self.assertEqual(len(PPLUT_PICTURE_PROFILES_G115), 4)
        self.assertEqual(len(ALLOWED_PICTURE_PROFILES_G115), 16)
        self.assertEqual(len(ALLOWED_DRO_MODES_G115), 7)

    def test_13_g115_matrix_512_states_all_invariants_hold(self) -> None:
        m = compute_pp_scinetone_creativelook_dro_matrix()
        self.assertTrue(m["all_invariants_hold"], msg=m)
        self.assertEqual(m["states_checked"], 512)
        self.assertEqual(m["double_pp_lockouts"], 384)
        self.assertEqual(m["pp_mutual_exclusions"], 112)
        self.assertEqual(m["internal_param_unreset_traps"], 384)
        self.assertEqual(m["pplut_hdmi_clamps"], 16)

    def test_14_g115_different_set_still_mv_coupled_vs_decoupled(self) -> None:
        coupled = resolve_fx3_pp_scinetone_creativelook_dro_state(
            shoot_mode=SHOOT_MODE_STILL_PHASE280,
            requested_picture_profile="PP11",
            requested_picture_profile_still="Off",
            different_set_picture_profile_checked=False,
        )
        self.assertEqual(coupled["effective_picture_profile"], "PP11")
        self.assertEqual(coupled["effective_creative_look"], "-")
        self.assertEqual(coupled["effective_dro"], "Off")

        decoupled = resolve_fx3_pp_scinetone_creativelook_dro_state(
            shoot_mode=SHOOT_MODE_STILL_PHASE280,
            requested_picture_profile="PP11",
            requested_picture_profile_still="Off",
            different_set_picture_profile_checked=True,
            requested_creative_look="VV",
            requested_dro="Lv3",
        )
        self.assertEqual(decoupled["effective_picture_profile"], "Off")
        self.assertEqual(decoupled["effective_creative_look"], "VV")
        self.assertEqual(decoupled["effective_dro"], "Lv3")
        self.assertFalse(decoupled["creative_look_and_dro_locked"])

    def test_15_g115_pp_off_unlocks_all_10_creative_looks_and_custom_boxes(self) -> None:
        for look in CREATIVE_LOOK_10_PRESETS_G115 + CREATIVE_LOOK_CUSTOM_SLOTS_G115:
            res = verify_pp_scinetone_creativelook_dro_guard(
                requested_picture_profile=PP_OFF_G115,
                requested_creative_look=look,
                requested_dro="Lv2",
            )
            self.assertTrue(res.valid, msg=f"look={look} err={res.errors}")
            self.assertEqual(res.effective_creative_look, look)
            self.assertEqual(res.effective_dro, "Lv2")
            self.assertFalse(res.creative_look_and_dro_locked)

    def test_16_g115_hlg_still_locks_dro_to_off_even_with_pp_off(self) -> None:
        res_ok = verify_pp_scinetone_creativelook_dro_guard(
            shoot_mode=SHOOT_MODE_STILL_PHASE280,
            requested_picture_profile=PP_OFF_G115,
            hlg_still_image=True,
            claimed_dro="Off",
        )
        self.assertTrue(res_ok.valid)
        self.assertEqual(res_ok.effective_dro, "Off")

        res_bad = verify_pp_scinetone_creativelook_dro_guard(
            shoot_mode=SHOOT_MODE_STILL_PHASE280,
            requested_picture_profile=PP_OFF_G115,
            hlg_still_image=True,
            claimed_dro="Auto",
        )
        self.assertFalse(res_bad.valid)
        self.assertIn(
            STATUS_BLOCKED_G115_PP_CREATIVELOOK_DRO_MUTUAL_EXCLUSION_VIOLATION,
            res_bad.violation_codes,
        )

    def test_17_g115_blocks_wrong_oob_default_claim(self) -> None:
        for bad_default in ("Off", "PP8", "PPLUT1"):
            res = verify_pp_scinetone_creativelook_dro_guard(
                claimed_fx3_oob_picture_profile_default=bad_default,
            )
            self.assertFalse(res.valid)
            self.assertEqual(
                res.status,
                STATUS_BLOCKED_G115_PP_CREATIVELOOK_DRO_MUTUAL_EXCLUSION_VIOLATION,
            )

    def test_18_g115_blocks_active_creative_look_or_dro_when_pp_is_on(self) -> None:
        r1 = verify_pp_scinetone_creativelook_dro_guard(
            requested_picture_profile="PP11",
            claimed_creative_look="ST",
        )
        self.assertFalse(r1.valid)
        self.assertIn(
            STATUS_BLOCKED_G115_PP_CREATIVELOOK_DRO_MUTUAL_EXCLUSION_VIOLATION,
            r1.violation_codes,
        )

        r2 = verify_pp_scinetone_creativelook_dro_guard(
            requested_picture_profile="PP11",
            claimed_dro="Auto",
        )
        self.assertFalse(r2.valid)
        self.assertIn(
            STATUS_BLOCKED_G115_PP_CREATIVELOOK_DRO_MUTUAL_EXCLUSION_VIOLATION,
            r2.violation_codes,
        )

        r3 = verify_pp_scinetone_creativelook_dro_guard(
            claimed_creative_look_active_with_pp_on=True,
            claimed_dro_active_with_pp_on=True,
        )
        self.assertFalse(r3.valid)
        self.assertEqual(
            r3.status,
            STATUS_BLOCKED_G115_PP_CREATIVELOOK_DRO_MUTUAL_EXCLUSION_VIOLATION,
        )

    def test_19_g115_log_shooting_all_three_modes_hard_lock_pp_cl_dro(self) -> None:
        for log_mode in (
            LOG_SHOOTING_FLEXIBLE_ISO_G115,
            LOG_SHOOTING_CINE_EI_QUICK_G115,
            LOG_SHOOTING_CINE_EI_G115,
        ):
            res = verify_pp_scinetone_creativelook_dro_guard(
                log_shooting=log_mode,
                requested_picture_profile="PP11",
                requested_creative_look="ST",
                requested_dro="Auto",
            )
            self.assertTrue(res.valid, msg=res.errors)
            self.assertEqual(res.effective_picture_profile, "Off")
            self.assertEqual(res.effective_creative_look, "-")
            self.assertEqual(res.effective_dro, "Off")
            self.assertEqual(res.effective_gamma_display_assist, "Off")
            self.assertTrue(res.double_log_or_baked_look_blocked)

    def test_20_g115_log_shooting_blocks_double_pp_or_gamma_assist_claims(self) -> None:
        for kwargs in (
            {"claimed_picture_profile": "PP8"},
            {"claimed_creative_look": "ST"},
            {"claimed_dro": "Auto"},
            {"claimed_pp_active_with_log_on": True},
            {"claimed_gamma_display_assist_movie_on": True},
        ):
            res = verify_pp_scinetone_creativelook_dro_guard(
                log_shooting=LOG_SHOOTING_CINE_EI_G115,
                **kwargs,
            )
            self.assertFalse(res.valid, msg=kwargs)
            self.assertIn(
                STATUS_BLOCKED_G115_LOG_SHOOTING_DOUBLE_PP_CORRUPTION_VIOLATION,
                res.violation_codes,
            )

    def test_21_g115_pplut1_to_4_movie_allowed_with_1080p_hdmi_clamp(self) -> None:
        for lut in PPLUT_PICTURE_PROFILES_G115:
            res = verify_pp_scinetone_creativelook_dro_guard(
                shoot_mode=SHOOT_MODE_MOVIE_PHASE280,
                requested_picture_profile=lut,
                internal_recording_active=True,
                requested_hdmi_output_resolution=HDMI_RES_2160P_G115,
                claimed_hdmi_output_resolution=HDMI_RES_1080P_G115,
            )
            self.assertTrue(res.valid, msg=res.errors)
            self.assertTrue(res.pplut_hdmi_1080p_clamped)
            self.assertEqual(res.effective_hdmi_output_resolution, HDMI_RES_1080P_G115)

    def test_22_g115_pplut_blocks_still_mode_and_unclamped_4k_hdmi_claim(self) -> None:
        r_still = verify_pp_scinetone_creativelook_dro_guard(
            shoot_mode=SHOOT_MODE_STILL_PHASE280,
            requested_picture_profile="PPLUT1",
        )
        self.assertFalse(r_still.valid)
        self.assertEqual(
            r_still.status,
            STATUS_BLOCKED_G115_PPLUT_STILL_OR_HDMI_CLAMP_VIOLATION,
        )

        r_claim_still = verify_pp_scinetone_creativelook_dro_guard(
            claimed_pplut_still_supported=True,
        )
        self.assertFalse(r_claim_still.valid)
        self.assertIn(
            STATUS_BLOCKED_G115_PPLUT_STILL_OR_HDMI_CLAMP_VIOLATION,
            r_claim_still.violation_codes,
        )

        r_4k = verify_pp_scinetone_creativelook_dro_guard(
            shoot_mode=SHOOT_MODE_MOVIE_PHASE280,
            requested_picture_profile="PPLUT2",
            internal_recording_active=True,
            claimed_hdmi_output_resolution=HDMI_RES_2160P_G115,
        )
        self.assertFalse(r_4k.valid)
        self.assertIn(
            STATUS_BLOCKED_G115_PPLUT_STILL_OR_HDMI_CLAMP_VIOLATION,
            r_4k.violation_codes,
        )

    def test_23_g115_reset_trap_customized_pp_survives_camera_reset_and_initialize(self) -> None:
        for r_act in (RESET_ACTION_CAMERA_SETTINGS_RESET, RESET_ACTION_INITIALIZE):
            res = verify_pp_scinetone_creativelook_dro_guard(
                reset_action=r_act,
                pp_internal_params_customized=True,
                pp_explicit_slot_reset_invoked=False,
            )
            self.assertFalse(res.valid)
            self.assertEqual(
                res.status,
                STATUS_BLOCKED_G115_PP_INTERNAL_PARAM_UNRESET_TRAP,
            )
            self.assertFalse(res.pp_internal_params_cleared)
            self.assertEqual(res.effective_picture_profile, "PP11")

    def test_24_g115_explicit_ppx_reset_clears_internal_param_trap(self) -> None:
        res = verify_pp_scinetone_creativelook_dro_guard(
            reset_action=RESET_ACTION_PP_SLOT_RESET_PHASE280,
            pp_internal_params_customized=True,
            pp_explicit_slot_reset_invoked=True,
        )
        self.assertTrue(res.valid, msg=res.errors)
        self.assertTrue(res.pp_internal_params_cleared)

    def test_25_g115_blocks_false_reset_cleanliness_claims(self) -> None:
        for flag in (
            "claimed_camera_reset_clears_pp_internal_params",
            "claimed_initialize_clears_pp_internal_params",
            "claimed_reset_clears_diff_set_check",
            "claimed_pp_slots_clean_after_reset",
        ):
            res = verify_pp_scinetone_creativelook_dro_guard(**{flag: True})
            self.assertFalse(res.valid, msg=flag)
            self.assertEqual(
                res.status,
                STATUS_BLOCKED_G115_PP_INTERNAL_PARAM_UNRESET_TRAP,
            )

    def test_26_g115_fx3_vs_fx6_base_look_and_pp_curve_mappings(self) -> None:
        self.assertEqual(FX6_BASE_LOOK_CUSTOM_DEFAULT_G115, "S-Cinetone")
        self.assertEqual(
            PICTURE_PROFILE_DEFAULT_CURVES_G115["PP11"],
            ("S-Cinetone", "S-Cinetone"),
        )
        self.assertEqual(
            PICTURE_PROFILE_DEFAULT_CURVES_G115["PP8"],
            ("S-Log3", "S-Gamut3.Cine"),
        )
        self.assertEqual(
            PICTURE_PROFILE_DEFAULT_CURVES_G115["PP10"],
            ("HLG2", "BT.2020"),
        )

    def test_27_g115_intelligent_auto_locks_pp_off_and_dro_auto(self) -> None:
        st = resolve_fx3_pp_scinetone_creativelook_dro_state(
            shoot_mode=SHOOT_MODE_INTELLIGENT_AUTO_PHASE280,
            requested_picture_profile="PP11",
            requested_dro="Lv5",
        )
        self.assertEqual(st["effective_picture_profile"], "Off")
        self.assertEqual(st["effective_creative_look"], "-")
        self.assertEqual(st["effective_dro"], "Auto")

    def test_28_g115_different_set_survives_reset_while_active_selector_resets_pp11(self) -> None:
        st = resolve_fx3_pp_scinetone_creativelook_dro_state(
            shoot_mode=SHOOT_MODE_STILL_PHASE280,
            requested_picture_profile="Off",
            requested_picture_profile_still="PP8",
            different_set_picture_profile_checked=True,
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
        )
        self.assertTrue(st["effective_diff_set"])
        self.assertEqual(st["effective_picture_profile"], "PP11")
        self.assertEqual(st["effective_picture_profile_still"], "PP11")

    def test_29_g115_invalid_telemetry_rejected(self) -> None:
        for bad_kwargs in (
            {"body_model_name": "ILME-FX6"},
            {"body_model_id": 0x12345678},
            {"body_model_id": True},
            {"help_guide_code": "ilc/9999"},
            {"shoot_mode": "UNKNOWN"},
            {"requested_picture_profile": "PP99"},
            {"requested_creative_look": "INVALID"},
            {"requested_dro": "Lv99"},
            {"reset_action": "MAGIC_WIPE"},
        ):
            res = verify_pp_scinetone_creativelook_dro_guard(**bad_kwargs)
            self.assertFalse(res.valid, msg=bad_kwargs)
            self.assertEqual(res.status, STATUS_BLOCKED_G115_TELEMETRY_INVALID)

    def test_30_g115_sq_mode_allows_pp11_and_pplut_without_still_block(self) -> None:
        res = verify_pp_scinetone_creativelook_dro_guard(
            shoot_mode=SHOOT_MODE_SQ_PHASE280,
            requested_picture_profile="PPLUT4",
            internal_recording_active=False,
            requested_hdmi_output_resolution=HDMI_RES_2160P_G115,
        )
        self.assertTrue(res.valid, msg=res.errors)
        self.assertFalse(res.pplut_hdmi_1080p_clamped)
        self.assertEqual(res.effective_hdmi_output_resolution, HDMI_RES_2160P_G115)

    def test_31_g115_case_insensitive_enum_normalization(self) -> None:
        res = verify_pp_scinetone_creativelook_dro_guard(
            shoot_mode="movie",
            log_shooting="off",
            requested_picture_profile="[off]",
            requested_creative_look="vv2",
            requested_dro="lv4",
        )
        self.assertTrue(res.valid, msg=res.errors)
        self.assertEqual(res.effective_picture_profile, "Off")
        self.assertEqual(res.effective_creative_look, "VV2")
        self.assertEqual(res.effective_dro, "Lv4")

    def test_32_g115_evaluator_verdict_and_persistent_write_block(self) -> None:
        v_ok, r_ok = evaluate_g115_pp_scinetone_creativelook_dro_guard(
            donor_audit=self.clean_audit,
        )
        self.assertTrue(v_ok.passed)
        self.assertEqual(v_ok.gate_id, G115_GATE_ID)
        self.assertEqual(r_ok.status, STATUS_VERIFIED_G115)
        self.assertFalse(r_ok.persistent_emmc_writes_authorized)

        v_bad, r_bad = evaluate_g115_pp_scinetone_creativelook_dro_guard(
            donor_audit=self.clean_audit,
            request_persistent_emmc_writes=True,
        )
        self.assertFalse(v_bad.passed)
        self.assertFalse(r_bad.valid)
        self.assertFalse(r_bad.persistent_emmc_writes_authorized)

    # ------------------------------------------------------------------
    # 33..56: Gate G116 — [White Balance] & [Metering Mode]
    # ------------------------------------------------------------------

    def test_33_g116_default_wb_auto_and_metering_multi_passes(self) -> None:
        res = verify_wb_cineei_and_metering_guard()
        self.assertTrue(res.valid, msg=res.errors)
        self.assertEqual(res.status, STATUS_VERIFIED_G116)
        self.assertEqual(res.effective_white_balance, "Auto")
        self.assertEqual(res.effective_priority_set_in_awb, "Standard")
        self.assertEqual(res.effective_shutter_awb_lock, "Off")
        self.assertEqual(res.effective_shockless_wb, "1 (Fast)")
        self.assertEqual(res.effective_metering_mode, "Multi")
        self.assertEqual(res.effective_face_priority_in_multi, "On")
        self.assertEqual(res.effective_spot_metering_point, "Center")
        self.assertEqual(res.effective_ael_w_shutter, "Auto")
        self.assertEqual(res.matrix_states_checked, 288)

    def test_34_g116_menu_paths_resid16_and_exact_6_metering_modes(self) -> None:
        self.assertEqual(
            WHITE_BALANCE_MENU_PATH_G116,
            "MENU -> Exposure/Color -> [White Balance] -> [White Balance]",
        )
        self.assertEqual(
            PRIORITY_SET_IN_AWB_MENU_PATH_G116,
            "MENU -> Exposure/Color -> [White Balance] -> [Priority Set in AWB]",
        )
        self.assertEqual(
            SHUTTER_AWB_LOCK_MENU_PATH_G116,
            "MENU -> Exposure/Color -> [White Balance] -> [Shutter AWB Lock]",
        )
        self.assertEqual(
            SHOCKLESS_WB_MENU_PATH_G116,
            "MENU -> Exposure/Color -> [White Balance] -> [Shockless WB]",
        )
        self.assertEqual(
            METERING_MODE_MENU_PATH_G116,
            "MENU -> Exposure/Color -> [Metering] -> [Metering Mode]",
        )
        self.assertEqual(
            FACE_PRIORITY_MULTI_METERING_MENU_PATH_G116,
            "MENU -> Exposure/Color -> [Metering] -> [Face Priority in Multi Metering]",
        )
        self.assertEqual(
            SPOT_METERING_POINT_MENU_PATH_G116,
            "MENU -> Exposure/Color -> [Metering] -> [Spot Metering Point]",
        )
        self.assertEqual(
            AEL_W_SHUTTER_MENU_PATH_G116,
            "MENU -> Exposure/Color -> [Metering] -> [AEL w/ Shutter]",
        )
        self.assertEqual(WHITE_BALANCE_UXC_RESID16_G116, 0xE5D4)
        self.assertEqual(PRIORITY_AWB_RESID16_G116, 0x67A7)
        self.assertEqual(METERING_MODE_UXC_RESID16_G116, 0xE5CF)
        self.assertEqual(FACE_PRIORITY_MULTI_RESID16_G116, 0x69C7)
        self.assertEqual(
            FX3_EXACT_6_METERING_MODES_G116,
            (
                "Multi",
                "Center",
                "Spot: Standard",
                "Spot: Large",
                "Entire Screen Avg.",
                "Highlight",
            ),
        )
        self.assertEqual(len(FX3_EXACT_6_METERING_MODES_G116), 6)

    def test_35_g116_matrix_288_states_all_invariants_hold(self) -> None:
        m = compute_wb_cineei_and_metering_matrix()
        self.assertTrue(m["all_invariants_hold"], msg=m)
        self.assertEqual(m["states_checked"], 288)
        self.assertEqual(m["cine_ei_awb_blocks"], 48)
        self.assertEqual(m["custom_setup_traps"], 108)
        self.assertEqual(m["desqueeze_face_locks"], 144)
        self.assertEqual(m["spot_center_locks"], 144)
        self.assertEqual(m["cine_ei_passive_mm_states"], 144)

    def test_36_g116_color_temp_2500k_to_9900k_100k_step_and_ab_gm_trim(self) -> None:
        steps = list(range(WB_CTEMP_MIN_K_G116, WB_CTEMP_MAX_K_G116 + 1, WB_CTEMP_STEP_K_G116))
        self.assertEqual(len(steps), WB_CTEMP_TOTAL_STEPS_G116)
        self.assertEqual(steps[0], 2500)
        self.assertEqual(steps[-1], 9900)

        for k in (2500, 3200, 4300, 5500, 5600, 6500, 9900):
            res = verify_wb_cineei_and_metering_guard(
                requested_white_balance=WB_CTEMP_FILTER_G116,
                color_temp_k=k,
                wb_ab_trim=WB_FINE_TRIM_MAX_G116,
                wb_gm_trim=WB_FINE_TRIM_MIN_G116,
            )
            self.assertTrue(res.valid, msg=res.errors)

        for bad_k in (2400, 5550, 10000):
            res = verify_wb_cineei_and_metering_guard(
                requested_white_balance=WB_CTEMP_FILTER_G116,
                color_temp_k=bad_k,
            )
            self.assertFalse(res.valid)
            self.assertEqual(res.status, STATUS_BLOCKED_G116_TELEMETRY_INVALID)

        for bad_trim in (-8, 8):
            res = verify_wb_cineei_and_metering_guard(
                requested_white_balance=WB_CTEMP_FILTER_G116,
                wb_ab_trim=bad_trim,
            )
            self.assertFalse(res.valid)
            self.assertEqual(res.status, STATUS_BLOCKED_G116_TELEMETRY_INVALID)

    def test_37_g116_priority_awb_shutter_awb_lock_and_shockless_wb_options(self) -> None:
        for prio in (
            PRIORITY_AWB_STANDARD_G116,
            PRIORITY_AWB_AMBIENCE_G116,
            PRIORITY_AWB_WHITE_G116,
        ):
            r = verify_wb_cineei_and_metering_guard(priority_set_in_awb=prio)
            self.assertTrue(r.valid, msg=r.errors)
            self.assertEqual(r.effective_priority_set_in_awb, prio)

        for lock_mode in ALLOWED_SHUTTER_AWB_LOCK_MODES_G116:
            r = verify_wb_cineei_and_metering_guard(
                shoot_mode=SHOOT_MODE_STILL_PHASE280,
                shutter_awb_lock=lock_mode,
            )
            self.assertTrue(r.valid, msg=r.errors)
            self.assertEqual(r.effective_shutter_awb_lock, lock_mode)

        for swb in ALLOWED_SHOCKLESS_WB_MODES_G116:
            r = verify_wb_cineei_and_metering_guard(shockless_wb=swb)
            self.assertTrue(r.valid, msg=r.errors)
            self.assertEqual(r.effective_shockless_wb, swb)

    def test_38_g116_flash_wb_allowed_in_still_and_blocked_in_movie(self) -> None:
        r_still = verify_wb_cineei_and_metering_guard(
            shoot_mode=SHOOT_MODE_STILL_PHASE280,
            requested_white_balance=WB_FLASH_G116,
        )
        self.assertTrue(r_still.valid)

        r_movie = verify_wb_cineei_and_metering_guard(
            shoot_mode=SHOOT_MODE_MOVIE_PHASE280,
            requested_white_balance=WB_FLASH_G116,
        )
        self.assertFalse(r_movie.valid)
        self.assertEqual(r_movie.status, STATUS_BLOCKED_G116_TELEMETRY_INVALID)

    def test_39_g116_cine_ei_and_cine_ei_quick_block_awb_and_underwater_auto(self) -> None:
        for log_mode in (LOG_SHOOTING_CINE_EI_G115, LOG_SHOOTING_CINE_EI_QUICK_G115):
            for awb_mode in (WB_AUTO_G116, WB_UNDERWATER_AUTO_G116):
                r = verify_wb_cineei_and_metering_guard(
                    log_shooting=log_mode,
                    requested_white_balance=awb_mode,
                )
                self.assertFalse(r.valid)
                self.assertEqual(r.status, STATUS_BLOCKED_G116_CINE_EI_AWB_VIOLATION)
                self.assertTrue(r.cine_ei_awb_blocked)

            r_manual = verify_wb_cineei_and_metering_guard(
                log_shooting=log_mode,
                requested_white_balance=WB_CTEMP_FILTER_G116,
                color_temp_k=5500,
                cine_ei_base_iso=800,
            )
            self.assertTrue(r_manual.valid, msg=r_manual.errors)
            self.assertFalse(r_manual.cine_ei_awb_blocked)

    def test_40_g116_flexible_iso_still_permits_auto_wb_unlike_cine_ei(self) -> None:
        r = verify_wb_cineei_and_metering_guard(
            log_shooting=LOG_SHOOTING_FLEXIBLE_ISO_G115,
            requested_white_balance=WB_AUTO_G116,
        )
        self.assertTrue(r.valid, msg=r.errors)
        self.assertFalse(r.cine_ei_awb_blocked)

    def test_41_g116_custom_setup_trap_under_log_shooting_slog3_and_pplut(self) -> None:
        for log_mode in (
            LOG_SHOOTING_FLEXIBLE_ISO_G115,
            LOG_SHOOTING_CINE_EI_QUICK_G115,
            LOG_SHOOTING_CINE_EI_G115,
        ):
            r = verify_wb_cineei_and_metering_guard(
                log_shooting=log_mode,
                requested_white_balance=WB_CUSTOM_1_G116,
                custom_wb_setup_executed=True,
            )
            self.assertFalse(r.valid)
            self.assertIn(STATUS_BLOCKED_G116_LOG_CUSTOM_WB_CAPTURE_TRAP, r.violation_codes)
            self.assertTrue(r.custom_wb_capture_blocked)

        for pp_trap in ("PP8", "PP9", "PPLUT1", "PPLUT4"):
            r_pp = verify_wb_cineei_and_metering_guard(
                log_shooting=LOG_SHOOTING_OFF_G115,
                picture_profile=pp_trap,
                requested_white_balance=WB_CUSTOM_2_G116,
                custom_wb_setup_executed=True,
            )
            self.assertFalse(r_pp.valid)
            self.assertEqual(r_pp.status, STATUS_BLOCKED_G116_LOG_CUSTOM_WB_CAPTURE_TRAP)

        r_gamma = verify_wb_cineei_and_metering_guard(
            log_shooting=LOG_SHOOTING_OFF_G115,
            picture_profile="PP1",
            picture_profile_gamma="S-Log3",
            requested_white_balance=WB_CUSTOM_3_G116,
            custom_wb_setup_executed=True,
        )
        self.assertFalse(r_gamma.valid)
        self.assertEqual(r_gamma.status, STATUS_BLOCKED_G116_LOG_CUSTOM_WB_CAPTURE_TRAP)

    def test_42_g116_custom_setup_succeeds_under_pp11_or_pp_off_when_log_off(self) -> None:
        for pp in ("PP11", "Off"):
            r = verify_wb_cineei_and_metering_guard(
                log_shooting=LOG_SHOOTING_OFF_G115,
                picture_profile=pp,
                requested_white_balance=WB_CUSTOM_1_G116,
                custom_wb_setup_executed=True,
            )
            self.assertTrue(r.valid, msg=r.errors)
            self.assertFalse(r.custom_wb_capture_blocked)

    def test_43_g116_custom_wb_and_still_locks_reset_and_camset_boundary(self) -> None:
        st_rst = resolve_fx3_wb_cineei_and_metering_state(
            shoot_mode=SHOOT_MODE_STILL_PHASE280,
            shutter_awb_lock=SHUTTER_AWB_LOCK_HALF_PRESS_G116,
            ael_w_shutter=AEL_W_SHUTTER_ON_G116,
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET,
        )
        self.assertTrue(st_rst["custom_wb_slots_memorized_after_reset"])
        self.assertEqual(st_rst["effective_shutter_awb_lock"], SHUTTER_AWB_LOCK_HALF_PRESS_G116)
        self.assertEqual(st_rst["effective_ael_w_shutter"], AEL_W_SHUTTER_ON_G116)
        self.assertEqual(st_rst["effective_white_balance"], "Auto")
        self.assertEqual(st_rst["effective_priority_set_in_awb"], "Standard")
        self.assertEqual(st_rst["effective_shockless_wb"], "1 (Fast)")
        self.assertEqual(st_rst["effective_metering_mode"], "Multi")

        st_init = resolve_fx3_wb_cineei_and_metering_state(
            shoot_mode=SHOOT_MODE_STILL_PHASE280,
            shutter_awb_lock=SHUTTER_AWB_LOCK_HALF_PRESS_G116,
            ael_w_shutter=AEL_W_SHUTTER_ON_G116,
            reset_action=RESET_ACTION_INITIALIZE,
        )
        self.assertFalse(st_init["custom_wb_slots_memorized_after_reset"])
        self.assertEqual(st_init["effective_shutter_awb_lock"], "Off")
        self.assertEqual(st_init["effective_ael_w_shutter"], "Auto")

    def test_44_g116_blocks_false_camset_and_reset_claims(self) -> None:
        for flag in (
            "claimed_custom_wb_saved_to_camset",
            "claimed_camera_reset_wipes_custom_wb_slots",
            "claimed_camera_reset_resets_shutter_awb_lock",
            "claimed_camera_reset_resets_ael_w_shutter",
        ):
            r = verify_wb_cineei_and_metering_guard(**{flag: True})
            self.assertFalse(r.valid, msg=flag)
            self.assertEqual(
                r.status,
                STATUS_BLOCKED_G116_WB_OR_METERING_RESET_CAMSET_BOUNDARY_VIOLATION,
            )

    def test_45_g116_all_6_metering_modes_accepted(self) -> None:
        for m_mode in FX3_EXACT_6_METERING_MODES_G116:
            r = verify_wb_cineei_and_metering_guard(requested_metering_mode=m_mode)
            self.assertTrue(r.valid, msg=f"m_mode={m_mode} err={r.errors}")
            self.assertEqual(r.effective_metering_mode, m_mode)

    def test_46_g116_desqueeze_hard_locks_face_priority_in_multi_metering_off(self) -> None:
        for desq in ALLOWED_DESQUEEZE_MODES_G116:
            if desq == "Off":
                continue
            r_ok = verify_wb_cineei_and_metering_guard(
                desqueeze_display=desq,
                face_priority_in_multi=FACE_PRIORITY_MULTI_ON_G116,
                claimed_effective_face_priority_in_multi=FACE_PRIORITY_MULTI_OFF_G116,
            )
            self.assertTrue(r_ok.valid, msg=r_ok.errors)
            self.assertEqual(r_ok.effective_face_priority_in_multi, "Off")

            r_bad = verify_wb_cineei_and_metering_guard(
                desqueeze_display=desq,
                face_priority_in_multi=FACE_PRIORITY_MULTI_ON_G116,
                claimed_effective_face_priority_in_multi=FACE_PRIORITY_MULTI_ON_G116,
            )
            self.assertFalse(r_bad.valid)
            self.assertEqual(
                r_bad.status,
                STATUS_BLOCKED_G116_METERING_OR_CINE_EI_BASE_ISO_VIOLATION,
            )

    def test_47_g116_spot_metering_point_locked_center_on_wide_zone_center_fix(self) -> None:
        for area in SPOT_METERING_CENTER_LOCKED_FOCUS_AREAS_G116:
            r_ok = verify_wb_cineei_and_metering_guard(
                requested_metering_mode=METERING_MODE_SPOT_STANDARD_G116,
                focus_area=area,
                spot_metering_point=SPOT_METERING_POINT_FOCUS_LINK_G116,
                claimed_effective_spot_metering_point=SPOT_METERING_POINT_CENTER_G116,
            )
            self.assertTrue(r_ok.valid, msg=r_ok.errors)
            self.assertEqual(r_ok.effective_spot_metering_point, "Center")

            r_bad = verify_wb_cineei_and_metering_guard(
                requested_metering_mode=METERING_MODE_SPOT_LARGE_G116,
                focus_area=area,
                spot_metering_point=SPOT_METERING_POINT_FOCUS_LINK_G116,
                claimed_effective_spot_metering_point=SPOT_METERING_POINT_FOCUS_LINK_G116,
            )
            self.assertFalse(r_bad.valid)
            self.assertEqual(
                r_bad.status,
                STATUS_BLOCKED_G116_METERING_OR_CINE_EI_BASE_ISO_VIOLATION,
            )

        for link_area in SPOT_METERING_LINKABLE_FOCUS_AREAS_G116:
            r_link = verify_wb_cineei_and_metering_guard(
                requested_metering_mode=METERING_MODE_SPOT_STANDARD_G116,
                focus_area=link_area,
                spot_metering_point=SPOT_METERING_POINT_FOCUS_LINK_G116,
                claimed_effective_spot_metering_point=SPOT_METERING_POINT_FOCUS_LINK_G116,
            )
            self.assertTrue(r_link.valid, msg=r_link.errors)
            self.assertEqual(r_link.effective_spot_metering_point, "Focus Point Link")

    def test_48_g116_iauto_and_non_optical_zoom_force_multi_metering(self) -> None:
        r_ok = verify_wb_cineei_and_metering_guard(
            shoot_mode=SHOOT_MODE_STILL_PHASE280,
            requested_metering_mode=METERING_MODE_HIGHLIGHT_G116,
            non_optical_zoom_active=True,
            claimed_effective_metering_mode=METERING_MODE_MULTI_G116,
        )
        self.assertTrue(r_ok.valid)
        self.assertEqual(r_ok.effective_metering_mode, "Multi")

        r_bad = verify_wb_cineei_and_metering_guard(
            shoot_mode=SHOOT_MODE_INTELLIGENT_AUTO_PHASE280,
            requested_metering_mode=METERING_MODE_CENTER_G116,
            claimed_effective_metering_mode=METERING_MODE_CENTER_G116,
        )
        self.assertFalse(r_bad.valid)
        self.assertEqual(
            r_bad.status,
            STATUS_BLOCKED_G116_METERING_OR_CINE_EI_BASE_ISO_VIOLATION,
        )

    def test_49_g116_cine_ei_base_iso_800_12800_and_passive_mm_invariance(self) -> None:
        for base_iso in CINE_EI_BASE_ISOS_G116:
            r = verify_wb_cineei_and_metering_guard(
                log_shooting=LOG_SHOOTING_CINE_EI_G115,
                requested_white_balance=WB_CTEMP_FILTER_G116,
                color_temp_k=5500,
                requested_metering_mode=METERING_MODE_SPOT_STANDARD_G116,
                cine_ei_base_iso=base_iso,
            )
            self.assertTrue(r.valid, msg=r.errors)
            self.assertTrue(r.cine_ei_recording_iso_locked)
            self.assertTrue(r.metering_drives_mm_monitoring_only)

        r_bad_iso = verify_wb_cineei_and_metering_guard(
            log_shooting=LOG_SHOOTING_CINE_EI_G115,
            requested_white_balance=WB_CTEMP_FILTER_G116,
            cine_ei_base_iso=3200,
        )
        self.assertFalse(r_bad_iso.valid)
        self.assertEqual(
            r_bad_iso.status,
            STATUS_BLOCKED_G116_METERING_OR_CINE_EI_BASE_ISO_VIOLATION,
        )

        r_gain_mutate = verify_wb_cineei_and_metering_guard(
            log_shooting=LOG_SHOOTING_CINE_EI_QUICK_G115,
            requested_white_balance=WB_CUSTOM_1_G116,
            cine_ei_base_iso=800,
            claimed_metering_alters_cine_ei_recording_iso=True,
        )
        self.assertFalse(r_gain_mutate.valid)
        self.assertEqual(
            r_gain_mutate.status,
            STATUS_BLOCKED_G116_METERING_OR_CINE_EI_BASE_ISO_VIOLATION,
        )

    def test_50_g116_exposure_std_adjust_range_guard(self) -> None:
        r_ok = verify_wb_cineei_and_metering_guard(exposure_std_adjust_ev=1.0)
        self.assertTrue(r_ok.valid)
        r_ok2 = verify_wb_cineei_and_metering_guard(exposure_std_adjust_ev=-1.0)
        self.assertTrue(r_ok2.valid)
        r_bad = verify_wb_cineei_and_metering_guard(exposure_std_adjust_ev=1.5)
        self.assertFalse(r_bad.valid)
        self.assertEqual(r_bad.status, STATUS_BLOCKED_G116_TELEMETRY_INVALID)

    def test_51_g116_fx3_vs_fx6_kelvin_presets(self) -> None:
        self.assertEqual(FX6_PRESET_CUSTOM_KELVINS_G116, (3200, 4300, 5600, 6300))
        self.assertEqual(FX6_PRESET_CINE_EI_KELVINS_G116, (3200, 4300, 5500))
        r = verify_wb_cineei_and_metering_guard()
        self.assertEqual(r.fx6_preset_custom_kelvins, (3200, 4300, 5600, 6300))
        self.assertEqual(r.fx6_preset_cine_ei_kelvins, (3200, 4300, 5500))

    def test_52_g116_ael_w_shutter_all_modes_valid(self) -> None:
        for mode in ALLOWED_AEL_W_SHUTTER_MODES_G116:
            r = verify_wb_cineei_and_metering_guard(
                shoot_mode=SHOOT_MODE_STILL_PHASE280,
                ael_w_shutter=mode,
            )
            self.assertTrue(r.valid, msg=r.errors)
            self.assertEqual(r.effective_ael_w_shutter, mode)

    def test_53_g116_invalid_telemetry_rejected(self) -> None:
        for bad_kwargs in (
            {"body_model_name": "ILME-FX6"},
            {"body_model_id": 0x1234},
            {"help_guide_code": "ilc/0000"},
            {"requested_white_balance": "TungstenX"},
            {"requested_metering_mode": "Evaluative"},
            {"desqueeze_display": "4.0x"},
            {"focus_area": "ZoneX"},
            {"ael_w_shutter": "Always"},
            {"priority_set_in_awb": "Warm"},
        ):
            res = verify_wb_cineei_and_metering_guard(**bad_kwargs)
            self.assertFalse(res.valid, msg=bad_kwargs)
            self.assertEqual(res.status, STATUS_BLOCKED_G116_TELEMETRY_INVALID)

    def test_54_g116_claimed_cine_ei_awb_allowed_triggers_violation(self) -> None:
        res = verify_wb_cineei_and_metering_guard(
            log_shooting=LOG_SHOOTING_OFF_G115,
            claimed_cine_ei_awb_allowed=True,
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_G116_CINE_EI_AWB_VIOLATION)

    def test_55_g116_evaluator_verdict_and_persistent_write_block(self) -> None:
        v_ok, r_ok = evaluate_g116_wb_cineei_and_metering_guard(
            donor_audit=self.clean_audit,
        )
        self.assertTrue(v_ok.passed)
        self.assertEqual(v_ok.gate_id, G116_GATE_ID)
        self.assertEqual(r_ok.status, STATUS_VERIFIED_G116)
        self.assertFalse(r_ok.persistent_emmc_writes_authorized)

        v_bad, r_bad = evaluate_g116_wb_cineei_and_metering_guard(
            donor_audit=self.clean_audit,
            request_persistent_emmc_writes=True,
        )
        self.assertFalse(v_bad.passed)
        self.assertFalse(r_bad.valid)
        self.assertFalse(r_bad.persistent_emmc_writes_authorized)

    def test_56_g115_and_g116_to_dict_json_serializable(self) -> None:
        _, r115 = evaluate_g115_pp_scinetone_creativelook_dro_guard(
            donor_audit=self.clean_audit
        )
        _, r116 = evaluate_g116_wb_cineei_and_metering_guard(
            donor_audit=self.clean_audit
        )
        j115 = json.loads(json.dumps(r115.to_dict(), ensure_ascii=False))
        j116 = json.loads(json.dumps(r116.to_dict(), ensure_ascii=False))
        self.assertEqual(j115["status"], STATUS_VERIFIED_G115)
        self.assertEqual(j116["status"], STATUS_VERIFIED_G116)
        self.assertEqual(j115["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(j116["raw_firmware_bytes_leaked"], 0)

    # ------------------------------------------------------------------
    # 57..68: Unified 116-Gate Master Safety Preflight Engine
    # ------------------------------------------------------------------

    def test_57_unified_116_gates_offline_113_of_116(self) -> None:
        rep = evaluate_116gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=False,
            master_114_override=self.clean_offline_114,
        )
        self.assertEqual(rep.summary["total_gates"], 116)
        self.assertEqual(rep.summary["verified_gates"], 113)
        self.assertEqual(rep.summary["blocked_or_pending_gates"], 3)
        self.assertTrue(rep.offline_113_gates_verified)
        self.assertFalse(rep.all_116_gates_verified)
        self.assertTrue(rep.g115_to_g116_all_passed)
        self.assertTrue(rep.g13_to_g116_all_passed)
        self.assertEqual(rep.status, "VERIFIED_113_OF_116_AWAITING_PHYSICAL_TIER0")
        self.assertEqual(len(rep.gates), 116)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.hardware_live_attachment_authorized)
        self.assertFalse(rep.el3_payload_transmit_authorized)
        self.assertFalse(rep.spi_nor_write_authorized)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertEqual(rep.usb_packets_transmitted, 0)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_58_unified_116_gates_dry_run_simulated_116_of_116(self) -> None:
        rep = evaluate_116gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            master_114_override=self.clean_dryrun_114,
        )
        self.assertEqual(rep.summary["total_gates"], 116)
        self.assertEqual(rep.summary["verified_gates"], 116)
        self.assertEqual(rep.summary["blocked_or_pending_gates"], 0)
        self.assertTrue(rep.offline_113_gates_verified)
        self.assertTrue(rep.all_116_gates_verified)
        self.assertTrue(rep.g115_to_g116_all_passed)
        self.assertTrue(rep.dry_run_rehearsal_only)
        self.assertEqual(rep.status, "VERIFIED_ALL_116_GATES_DRY_RUN_SIMULATED_BACKUP")
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertEqual(rep.usb_packets_transmitted, 0)

    def test_59_unified_116_gates_real_unmocked_delegation(self) -> None:
        rep = evaluate_116gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
        )
        self.assertTrue(rep.all_116_gates_verified)
        self.assertEqual(rep.summary["verified_gates"], 116)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertEqual(rep.gates[-2]["gate_id"], G115_GATE_ID)
        self.assertEqual(rep.gates[-1]["gate_id"], G116_GATE_ID)

    def test_60_unified_116_gates_g115_failure_blocks_report(self) -> None:
        rep = evaluate_116gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            master_114_override=self.clean_dryrun_114,
            pp_creativelook_dro_kwargs={
                "log_shooting": LOG_SHOOTING_CINE_EI_G115,
                "claimed_picture_profile": "PP8",
            },
        )
        self.assertFalse(rep.g115_to_g116_all_passed)
        self.assertFalse(rep.all_116_gates_verified)
        self.assertEqual(
            rep.status,
            STATUS_BLOCKED_G115_LOG_SHOOTING_DOUBLE_PP_CORRUPTION_VIOLATION,
        )
        self.assertEqual(rep.summary["verified_gates"], 115)

    def test_61_unified_116_gates_g116_failure_blocks_report(self) -> None:
        rep = evaluate_116gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            master_114_override=self.clean_dryrun_114,
            wb_metering_kwargs={
                "log_shooting": LOG_SHOOTING_CINE_EI_G115,
                "requested_white_balance": WB_AUTO_G116,
            },
        )
        self.assertFalse(rep.g115_to_g116_all_passed)
        self.assertFalse(rep.all_116_gates_verified)
        self.assertEqual(rep.status, STATUS_BLOCKED_G116_CINE_EI_AWB_VIOLATION)
        self.assertEqual(rep.summary["verified_gates"], 115)

    def test_62_unified_116_gates_upstream_114_failure_blocks_report(self) -> None:
        bad_114 = dataclasses.replace(
            self.clean_dryrun_114,
            g13_to_g114_all_passed=False,
            g113_to_g114_all_passed=False,
            all_114_gates_verified=False,
            status="BLOCKED_UPSTREAM_G114_FAILURE",
        )
        rep = evaluate_116gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            master_114_override=bad_114,
        )
        self.assertFalse(rep.g13_to_g116_all_passed)
        self.assertFalse(rep.all_116_gates_verified)
        self.assertEqual(rep.status, "BLOCKED_UPSTREAM_G114_FAILURE")

    def test_63_unified_116_gates_blocks_persistent_write_escalation(self) -> None:
        rep = evaluate_116gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            request_persistent_emmc_writes=True,
            master_114_override=self.clean_dryrun_114,
        )
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.all_116_gates_verified)
        self.assertFalse(rep.hardware_live_attachment_authorized)
        self.assertFalse(rep.el3_payload_transmit_authorized)
        self.assertFalse(rep.spi_nor_write_authorized)
        self.assertFalse(rep.persistent_emmc_writes_authorized)

    def test_64_unified_116_gates_g01_g09_missing_fails_closed(self) -> None:
        bad_gates = list(self.clean_offline_114.gates)
        bad_gates[0] = {**bad_gates[0], "passed": False}
        bad_summary = dict(self.clean_offline_114.summary)
        bad_summary["g01_to_g12_verified"] = 8
        bad_summary["verified_gates"] = 110
        bad_114 = dataclasses.replace(
            self.clean_offline_114,
            gates=tuple(bad_gates),
            summary=bad_summary,
            offline_111_gates_verified=False,
        )
        rep = evaluate_116gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=False,
            master_114_override=bad_114,
        )
        self.assertFalse(rep.offline_113_gates_verified)
        self.assertEqual(rep.status, "BLOCKED_BY_CORE_G01_G09_REFERENCE_MISSING")

    def test_65_unified_116_gates_report_json_serializable(self) -> None:
        rep = evaluate_116gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            master_114_override=self.clean_dryrun_114,
        )
        raw = json.dumps(rep.to_dict(), ensure_ascii=False)
        decoded = json.loads(raw)
        self.assertEqual(decoded["summary"]["verified_gates"], 116)
        self.assertEqual(decoded["g115_result"]["status"], STATUS_VERIFIED_G115)
        self.assertEqual(decoded["g116_result"]["status"], STATUS_VERIFIED_G116)
        self.assertEqual(decoded["raw_firmware_bytes_leaked"], 0)

    def test_66_aliases_evaluate_116_master_and_run_116_gate_preflight(self) -> None:
        rep1 = run_116_gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=False,
            master_114_override=self.clean_offline_114,
        )
        rep2 = evaluate_116_master_safety_gates(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            master_114_override=self.clean_dryrun_114,
        )
        self.assertEqual(rep1.summary["verified_gates"], 113)
        self.assertEqual(rep2.summary["verified_gates"], 116)

    def test_67_phase280_reset_actions_and_fw_metadata_exact(self) -> None:
        self.assertEqual(
            ALLOWED_RESET_ACTIONS_PHASE280,
            (
                RESET_ACTION_NONE,
                RESET_ACTION_CAMERA_SETTINGS_RESET,
                RESET_ACTION_RESET_NETWORK_SET_PHASE280,
                RESET_ACTION_INITIALIZE,
                RESET_ACTION_PP_SLOT_RESET_PHASE280,
            ),
        )
        self.assertEqual(
            ALLOWED_SHOOT_MODES_PHASE280,
            (
                SHOOT_MODE_MOVIE_PHASE280,
                SHOOT_MODE_STILL_PHASE280,
                SHOOT_MODE_SQ_PHASE280,
                SHOOT_MODE_INTELLIGENT_AUTO_PHASE280,
            ),
        )
        self.assertEqual(FX3_DEFAULT_FW_VERSION_PHASE280, "7.02")
        self.assertEqual(FX6_DEFAULT_FW_VERSION_PHASE280, "6.01")
        self.assertEqual(FX3_HELP_GUIDE_CODE_PHASE280, "ilc/2210")
        self.assertEqual(FX3_MODEL_NAME, "ILME-FX3")
        self.assertEqual(FX6_MODEL_NAME_PHASE280, "ILME-FX6")
        self.assertEqual(FX3_MODEL_ID, 0x91030080)

    def test_68_phase280_master_116_report_type_and_verification_mode(self) -> None:
        rep = evaluate_116gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=None,
            dry_run_simulated=False,
            master_114_override=self.clean_offline_114,
        )
        self.assertIsInstance(rep, Master116GateReport)
        if self.active_audit.verification_mode == "LOCAL_DONOR_O_RDONLY":
            self.assertEqual(rep.verification_mode, "LOCAL_DONOR_O_RDONLY")
        else:
            self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    # ------------------------------------------------------------------
    # 69..78: CLI Entrypoints, Standalone Main, Subprocess Portability & Parity
    # ------------------------------------------------------------------

    def test_69_cli_verify_pp_scinetone_creativelook_dro_guard_text_and_json(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cli_main(["verify-pp-scinetone-creativelook-dro-guard", "--force-clean-room"])
        self.assertEqual(rc, 0)
        self.assertIn("gate=G115_", buf.getvalue())
        self.assertIn("pp=PP11", buf.getvalue())
        self.assertIn("cl=-", buf.getvalue())

        jbuf = io.StringIO()
        with contextlib.redirect_stdout(jbuf):
            rc_j = cli_main(
                [
                    "verify-g115-pp-scinetone-creativelook-dro",
                    "--force-clean-room",
                    "--json",
                ]
            )
        self.assertEqual(rc_j, 0)
        data = json.loads(jbuf.getvalue())
        self.assertTrue(data["valid"])
        self.assertEqual(data["status"], STATUS_VERIFIED_G115)

    def test_70_cli_verify_wb_cineei_and_metering_guard_text_and_json(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cli_main(["verify-wb-cineei-and-metering-guard", "--force-clean-room"])
        self.assertEqual(rc, 0)
        self.assertIn("gate=G116_", buf.getvalue())
        self.assertIn("wb=Auto", buf.getvalue())
        self.assertIn("metering=Multi", buf.getvalue())

        jbuf = io.StringIO()
        with contextlib.redirect_stdout(jbuf):
            rc_j = cli_main(
                ["verify-g116-wb-cineei-metering", "--force-clean-room", "--json"]
            )
        self.assertEqual(rc_j, 0)
        data = json.loads(jbuf.getvalue())
        self.assertTrue(data["valid"])
        self.assertEqual(data["status"], STATUS_VERIFIED_G116)

    def test_71_cli_verify_116_gates_offline_text_and_json(self) -> None:
        offline_116 = evaluate_116gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=False,
            master_114_override=self.clean_offline_114,
        )
        with mock.patch(
            "fx3_safety.__main__.evaluate_116gate_preflight",
            return_value=offline_116,
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = cli_main(["verify-116-gates", "--force-clean-room"])
            self.assertEqual(rc, 0)
            self.assertIn("verified=113/116", buf.getvalue())
            self.assertIn("overall_ready_for_hardware_attach=False", buf.getvalue())

            jbuf = io.StringIO()
            with contextlib.redirect_stdout(jbuf):
                rc_j = cli_main(["verify-116-gates", "--force-clean-room", "--json"])
            self.assertEqual(rc_j, 0)
            parsed = json.loads(jbuf.getvalue())
            self.assertEqual(parsed["summary"]["verified_gates"], 113)
            self.assertTrue(parsed["offline_113_gates_verified"])

    def test_72_cli_verify_116_gates_dry_run_text_and_json(self) -> None:
        dryrun_116 = evaluate_116gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            master_114_override=self.clean_dryrun_114,
        )
        with mock.patch(
            "fx3_safety.__main__.evaluate_116gate_preflight",
            return_value=dryrun_116,
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = cli_main(
                    ["verify-116-gates", "--force-clean-room", "--simulate-bench-dry-run"]
                )
            self.assertEqual(rc, 0)
            self.assertIn("verified=116/116", buf.getvalue())

            jbuf = io.StringIO()
            with contextlib.redirect_stdout(jbuf):
                rc_j = cli_main(
                    [
                        "verify-116-gates",
                        "--force-clean-room",
                        "--simulate-bench-dry-run",
                        "--json",
                    ]
                )
            self.assertEqual(rc_j, 0)
            parsed = json.loads(jbuf.getvalue())
            self.assertTrue(parsed["all_116_gates_verified"])
            self.assertEqual(parsed["summary"]["verified_gates"], 116)

    def test_73_standalone_module_main_offline_and_dry_run(self) -> None:
        offline_116 = evaluate_116gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=False,
            master_114_override=self.clean_offline_114,
        )
        dryrun_116 = evaluate_116gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            master_114_override=self.clean_dryrun_114,
        )
        with mock.patch(
            "fx3_safety.realhw_pp_scinetone_creativelook_dro_wb_metering_and_116gate_guard.evaluate_116gate_preflight",
            return_value=offline_116,
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = module_main(["--force-clean-room"])
            self.assertEqual(rc, 0)
            self.assertIn("verified=113/116", buf.getvalue())

        with mock.patch(
            "fx3_safety.realhw_pp_scinetone_creativelook_dro_wb_metering_and_116gate_guard.evaluate_116gate_preflight",
            return_value=dryrun_116,
        ):
            jbuf = io.StringIO()
            with contextlib.redirect_stdout(jbuf):
                rc_j = module_main(
                    ["--force-clean-room", "--simulate-bench-dry-run", "--json"]
                )
            self.assertEqual(rc_j, 0)
            self.assertTrue(json.loads(jbuf.getvalue())["all_116_gates_verified"])

    def test_74_subprocess_cli_verify_g115_g116_uses_sys_executable(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONPATH"] = str(DEFAULT_REPO_ROOT / "outputs" / "fx3-safety")
        for cmd, expected_status in (
            ("verify-pp-scinetone-creativelook-dro-guard", STATUS_VERIFIED_G115),
            ("verify-wb-cineei-and-metering-guard", STATUS_VERIFIED_G116),
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

    def test_75_subprocess_cli_verify_116_gates_uses_sys_executable(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONPATH"] = str(DEFAULT_REPO_ROOT / "outputs" / "fx3-safety")
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "fx3_safety",
                "verify-116-gates",
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
        self.assertTrue(payload["all_116_gates_verified"])
        self.assertEqual(payload["summary"]["verified_gates"], 116)
        self.assertEqual(payload["raw_firmware_bytes_leaked"], 0)

    def test_76_fx3_clean_room_test_and_force_clean_room_env_in_master_116(self) -> None:
        for env_key in (ENV_CLEAN_ROOM_TEST_PHASE280, "FX3_FX6_FORCE_CLEAN_ROOM"):
            with mock.patch.dict(os.environ, {env_key: "1"}):
                self.assertTrue(_is_forced_clean_room())
                rep = evaluate_116gate_preflight(
                    master_114_override=self.clean_offline_114,
                )
                self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
                self.assertTrue(rep.clean_room_forced)

    def test_77_argparse_help_and_upstream_verify_114_gates_parity(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONPATH"] = str(DEFAULT_REPO_ROOT / "outputs" / "fx3-safety")
        for subcmd in (
            "verify-pp-scinetone-creativelook-dro-guard",
            "verify-wb-cineei-and-metering-guard",
            "verify-116-gates",
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
            "fx3_safety.__main__.evaluate_114gate_preflight",
            return_value=self.clean_offline_114,
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = cli_main(["verify-114-gates", "--force-clean-room"])
        self.assertEqual(rc, 0)
        self.assertIn("verified=111/114", buf.getvalue())

    def test_78_standalone_script_help_exits_zero_python314_percent_safe(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONPATH"] = str(DEFAULT_REPO_ROOT / "outputs" / "fx3-safety")
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "fx3_safety.realhw_pp_scinetone_creativelook_dro_wb_metering_and_116gate_guard",
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
        self.assertIn("phase 280", proc.stdout.lower())
        self.assertIn("116-gate", proc.stdout.lower())


if __name__ == "__main__":
    unittest.main()
