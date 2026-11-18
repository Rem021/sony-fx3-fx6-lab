"""Phase 303 (Wave-56, 132/132 Safety Gates Milestone!) Dual-Mode Unit Tests (86 tests) for
`fx3_safety.realhw_dial_customize_mydial_fn_liveview_lut_embed_and_132gate_guard`:

- Gate `G131` (`GATE_G131_DIAL_CUSTOMIZE_5ITEM_3DIAL_MYDIAL_12X2_FN_SPLIT_GUARD`):
  - `MENU -> (Setup) -> [Dial Customize]` exact 5 active items (`Custom Key/Dial Set.`,
    `My Dial Settings`, `Av/Tv Rotate`, `Function Ring(Lens)`, `Lock Operation Parts`),
    ALL `Initialize`-only (surviving `[Camera Settings Reset]`), rejecting legacy
    Ver. 1.xx `Dial Setup` / `Dial/Wheel Setup` / `Dial / Wheel Lock` and
    `VAL_setting_function_ring_FUNCTION_RING_INVALID`.
  - Physical 3-dial hardware enforcement (`Front Dial`, single `Rear Dial`,
    `Control Wheel`) rejecting dormant 4-dial Alpha `Rear Dial L` / `Rear Dial R`
    (`_f 0x6a5c/0x680d`, `BKID_APP_mydial_rear_dial_{left,right}_setting_list0..2`,
    `DIALCUSTOMIZE_DIAL_SETUP_LEFT_SHUTTER_RIGHT_F_NO`) fail-closed (`EOPNOTSUPP=95`).
  - `[My Dial Settings]` `1..3` shared NVRAM banks with Still/Movie per-mode recall
    (`Hold` / `Toggle` / `1->2->3` skipping all-`Not set` banks and temporarily unlocking
    `[Lock Operation Parts]` while active) + `[Fn Menu Settings]` strict 12 Still + 12 Movie
    slot split (blocking `Fn` invocation when all 12 slots of active mode are `Not set`),
    contrasted with `ILME-FX6` (`Multi Function Dial`, `Grip Dial`, `Handle Dial`,
    `IRIS Dial`, `ND Dial`, `Status Screens`, `Direct Menu`).
- Gate `G132` (`GATE_G132_LIVEVIEW_3ITEM_BRIGHT_GRID_HDMI_LUT_EMBED_PPLUT_VAULT_GUARD`):
  - Still-only `[Live View Display Set.]` (`_f 0x6429`) exact 3 sub-items
    (`Live View Display` forced `Setting Effect OFF` when `[Bright Monitoring]` is active,
    `Exposure Effect`, and resettable `Frame Rate Low Limit`), `[Grid Line Display]` /
    `[Grid Line Type]` (`Rule of 3rds Grid`, `Square Grid`, `Diag. + Square Grid`,
    `Initialize`-only) isolated from HDMI clean feed (`HDMI Info. Display = Off`,
    RAW HDMI, `Off(HDMI Only)`), rejecting dormant `FX6` custom PNG grids & markers.
  - `[Manage User LUTs]` (`User1..16`, `17pt`/`33pt` `.cube`, SD/SDXC `/Private/Sony/PRO/LUT`,
    CFexpress `/Sony/PRO/LUT`, read-only `O_RDONLY`), `[Select LUT]` (`709(800%)` / reset
    to `s709`), `[Embed LUT File]` under `[Log Shooting Setting]` (NOT `[Color/Tone]`,
    locked `Off` on `SD/SDHC`, embeds metadata inside container preserving `S-Log3` pixels),
    vs Picture Profile `PPLUT1..4` (irreversible pixel bake & dual reset).
  - Fail-closed `Slot-1` Tier-0 Vault Firewall (`EROFS=30` / `EBUSY=16`,
    `slot1_data_sector_writes == 0`, `slot1_avf_info_mutated == False`).
- Unified `132`-Gate Milestone Master Preflight (`evaluate_132gate_preflight` /
  `verify-132-gates`): `129/132` offline and `132/132` under `--simulate-bench-dry-run`
  with all hardware write/attach redlines hard-locked `False`.
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
from fx3_safety.realhw_touch_shooting_disp_evf_ael_flash_interval_pb_and_130gate_guard import (
    Master130GateReport,
    STATUS_BLOCKED_G130_PLAYBACK_EDIT_DORMANT_OR_SLOT1_VAULT_VIOLATION,
)
from fx3_safety.realhw_dial_customize_mydial_fn_liveview_lut_embed_and_132gate_guard import (
    ALLOWED_AV_TV_ROTATE_MODES_G131,
    ALLOWED_CARD_TYPES_G132,
    ALLOWED_CUBE_GRID_POINTS_G132,
    ALLOWED_EXPOSURE_EFFECT_MODES_G132,
    ALLOWED_FRAME_RATE_LOW_LIMIT_MODES_G132,
    ALLOWED_FUNCTION_RING_MODES_G131,
    ALLOWED_GRID_LINE_TYPES_G132,
    ALLOWED_LIVE_VIEW_DISPLAY_MODES_G132,
    ALLOWED_LOCK_OPERATION_PARTS_MODES_G131,
    ALLOWED_MY_DIAL_RECALL_MODES_G131,
    ALLOWED_USER_LUT_SLOTS_G132,
    AV_TV_ROTATE_DEFAULT_G131,
    AV_TV_ROTATE_NORMAL_G131,
    AV_TV_ROTATE_REVERSE_G131,
    CARD_TYPE_CFEXPRESS_A_G132,
    CARD_TYPE_SDXC_G132,
    CARD_TYPE_SD_SDHC_G132,
    CROSS_MODEL_FLASH_AUTHORIZED,
    DEFAULT_REPO_ROOT,
    DIAL_CUSTOMIZE_5_ITEMS_G131,
    DIAL_CUSTOMIZE_MENU_PATH_G131,
    DONOR_CHECK_CI_MAX_SECONDS_PHASE303,
    DONOR_CHECK_MAX_SECONDS_PHASE303,
    DORMANT_4DIAL_REAR_LR_TRAPS_G131,
    DORMANT_FUNCTION_RING_INVALID_G131,
    EBUSY_ERRNO_G132,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    EMBED_LUT_DEFAULT_G132,
    EMBED_LUT_FILE_MENU_PATH_G132,
    EMBED_LUT_FILE_WRONG_PATH_G132,
    EMBED_LUT_OFF_G132,
    EMBED_LUT_ON_G132,
    ENV_CLEAN_ROOM_TEST_PHASE303,
    ENV_FORCE_CLEAN_ROOM,
    EOPNOTSUPP_ERRNO_G131,
    EOPNOTSUPP_NAME_G131,
    EROFS_ERRNO_G132,
    EXPOSURE_EFFECT_DEFAULT_G132,
    EXPOSURE_EFFECT_SET_AND_FLASH_G132,
    EXPOSURE_EFFECT_SET_ONLY_G132,
    FN_MENU_MOVIE_SLOTS_G131,
    FN_MENU_SETTINGS_MENU_PATH_G131,
    FN_MENU_STILL_SLOTS_G131,
    FRAME_RATE_LOW_LIMIT_DEFAULT_G132,
    FRAME_RATE_LOW_LIMIT_OFF_G132,
    FRAME_RATE_LOW_LIMIT_ON_G132,
    FUNCTION_RING_APSC_S35_FF_G131,
    FUNCTION_RING_DEFAULT_G131,
    FUNCTION_RING_POWER_FOCUS_G131,
    FX3_DEFAULT_FW_VERSION_PHASE303,
    FX3_HELP_GUIDE_CODE_PHASE303,
    FX3_MODEL_ID_PHASE303,
    FX3_MODEL_NAME_PHASE303,
    FX3_PHYSICAL_3_DIALS_G131,
    FX3_PHYSICAL_DIAL_FRONT_G131,
    FX3_PHYSICAL_DIAL_REAR_G131,
    FX3_PHYSICAL_DIAL_WHEEL_G131,
    FX6_APPFW_PRM_USER_LUT_BUFFER_SLOTS_G132,
    FX6_DEFAULT_FW_VERSION_PHASE303,
    FX6_DIAL_CONTROLS_G131,
    FX6_DORMANT_CUSTOM_PNG_GRID_SYMBOLS_G132,
    FX6_MARKER_SAFETY_ZONES_G132,
    FX6_MODEL_NAME_PHASE303,
    FX6_STATUS_AND_DIRECT_MENU_SURFACES_G131,
    FX6_USER_LUT_ACTIVE_UI_CAP_G132,
    G131,
    G131_GATE_CODE,
    G131_GATE_ID,
    G132,
    G132_GATE_CODE,
    G132_GATE_ID,
    GRID_LINE_DISPLAY_DEFAULT_G132,
    GRID_LINE_DISPLAY_OFF_G132,
    GRID_LINE_DISPLAY_ON_G132,
    GRID_LINE_TYPE_DEFAULT_G132,
    GRID_LINE_TYPE_DIAG_SQUARE_G132,
    GRID_LINE_TYPE_RULE_OF_3RDS_G132,
    GRID_LINE_TYPE_SQUARE_G132,
    HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    HDMI_INFO_DISPLAY_DEFAULT_G132,
    HDMI_INFO_DISPLAY_OFF_G132,
    HDMI_INFO_DISPLAY_ON_G132,
    HUMAN_HARDWARE_ATTACH_TOKEN,
    LEGACY_DIAL_SETUP_MENU_NAME_G131,
    LEGACY_DIAL_WHEEL_LOCK_NAME_G131,
    LEGACY_DIAL_WHEEL_SETUP_NAME_G131,
    LIVE_VIEW_DISPLAY_DEFAULT_G132,
    LIVE_VIEW_DISPLAY_SET_3_SUBITEMS_G132,
    LIVE_VIEW_DISPLAY_SET_MENU_PATH_G132,
    LIVE_VIEW_SETTING_EFFECT_OFF_G132,
    LIVE_VIEW_SETTING_EFFECT_ON_G132,
    LOCK_OPERATION_PARTS_ALL_G131,
    LOCK_OPERATION_PARTS_DEFAULT_G131,
    LOCK_OPERATION_PARTS_DIAL_WHEEL_G131,
    LOCK_OPERATION_PARTS_MULTI_SELECTOR_G131,
    LOCK_OPERATION_PARTS_OFF_G131,
    LUT_FOLDER_CFEXPRESS_G132,
    LUT_FOLDER_SD_SDXC_G132,
    LUT_OP_DELETE_ALL_USER_LUTS_G132,
    LUT_OP_IMPORT_USER_LUT_G132,
    LUT_OP_MAKE_CUBE_FOLDER_G132,
    LUT_OP_RECORD_EMBED_LUT_G132,
    LUT_OP_RECORD_PPLUT_G132,
    LUT_OP_WRITE_CUBE_OR_SIDECAR_G132,
    MANAGE_USER_LUTS_MENU_PATH_G132,
    MEDIA_SLOT_1_PHASE303,
    MEDIA_SLOT_2_PHASE303,
    MY_DIAL_RECALL_CYCLE_G131,
    MY_DIAL_RECALL_DEFAULT_G131,
    MY_DIAL_RECALL_HOLD_G131,
    MY_DIAL_RECALL_NONE_G131,
    MY_DIAL_RECALL_TOGGLE_G131,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED,
    PHYSICAL_USB_PACKETS_EMITTED,
    PINNED_FX3_APPFW_SLICES_PHASE303,
    PINNED_FX3_APPFW_SLICES_SHA256_PHASE303,
    PINNED_FX6_APPFW_SLICES_PHASE303,
    PINNED_FX6_APPFW_SLICES_SHA256_PHASE303,
    PINNED_PHASE303_DONOR_SPECS,
    PPLUT_SLOTS_G132,
    RAW_FIRMWARE_BYTES_LEAKED,
    REALHW_DIAL_CUSTOMIZE_MYDIAL_FN_LIVEVIEW_LUT_EMBED_132GATE_SCHEMA,
    RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE303,
    RESET_ACTION_INITIALIZE_PHASE303,
    RESET_ACTION_NONE_PHASE303,
    RESET_ACTION_RESET_NETWORK_SET_PHASE303,
    SELECT_LUT_709_800_G132,
    SELECT_LUT_DEFAULT_G132,
    SELECT_LUT_S709_G132,
    SELECT_LUT_SLOG3_G132,
    SHOOT_MODE_MOVIE_PHASE303,
    SHOOT_MODE_SQ_PHASE303,
    SHOOT_MODE_STILL_PHASE303,
    SPI_NOR_WRITE_AUTHORIZED,
    STATUS_BLOCKED_G131_4DIAL_REAR_LR_OR_LEGACY_TRAP_VIOLATION,
    STATUS_BLOCKED_G131_DIAL_CUSTOMIZE_5ITEM_OR_RESET_VIOLATION,
    STATUS_BLOCKED_G131_FX6_DIAL_OR_DIRECT_MENU_CROSSWIRE_VIOLATION,
    STATUS_BLOCKED_G131_MYDIAL_OR_FN_12X2_SPLIT_VIOLATION,
    STATUS_BLOCKED_G131_TELEMETRY_INVALID,
    STATUS_BLOCKED_G132_GRID_CLEAN_HDMI_OR_FX6_PNG_VIOLATION,
    STATUS_BLOCKED_G132_LIVEVIEW_3ITEM_BRIGHT_OR_RESET_VIOLATION,
    STATUS_BLOCKED_G132_LUT_PATH_SDHC_OR_PPLUT_RESET_VIOLATION,
    STATUS_BLOCKED_G132_SLOT1_TIER0_VAULT_WRITE_FIREWALL_VIOLATION,
    STATUS_BLOCKED_G132_TELEMETRY_INVALID,
    STATUS_BLOCKED_PERSISTENT_EMMC_WRITE,
    STATUS_BLOCKED_PHASE303_DONOR_INTEGRITY,
    STATUS_VERIFIED_G131,
    STATUS_VERIFIED_G132,
    STATUS_VERIFIED_SAFE,
    USB_PACKETS_TRANSMITTED,
    audit_phase303_donor_contracts,
    compute_dial_customize_mydial_fn_matrix,
    compute_liveview_grid_lut_embed_matrix,
    evaluate_132_master_safety_gates,
    evaluate_132gate_preflight,
    evaluate_g131_dial_customize_mydial_fn_guard,
    evaluate_g132_liveview_grid_lut_embed_guard,
    main as module_main,
    resolve_fx3_dial_customize_mydial_fn_state,
    resolve_fx3_liveview_grid_lut_embed_state,
    run_132_gate_preflight,
    verify_dial_customize_mydial_fn_guard,
    verify_liveview_grid_lut_embed_guard,
)


def _make_stub_master130(
    *, dry_run: bool = False, all_g13_130_ok: bool = True
) -> Master130GateReport:
    gates = []
    for i in range(1, 131):
        gid = f"G{i:02d}"
        is_tier0_offline = gid in ("G10", "G11", "G12") and not dry_run
        passed = (not is_tier0_offline) and (all_g13_130_ok or i <= 12)
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
    g13_128 = 116 if all_g13_130_ok else 0
    g129_130 = 2 if all_g13_130_ok else 0
    total = g01_12 + g13_128 + g129_130
    return Master130GateReport(
        schema="stub_130",
        version="2026.11.17",
        evaluated_utc="2026-11-17T00:00:00Z",
        verification_mode="CLEAN_ROOM_SYNTHETIC",
        clean_room_forced=True,
        dry_run_rehearsal_only=dry_run,
        overall_ready_for_hardware_attach=False,
        hardware_live_attachment_authorized=False,
        offline_127_gates_verified=all_g13_130_ok,
        all_130_gates_verified=(dry_run and all_g13_130_ok),
        g13_to_g130_all_passed=all_g13_130_ok,
        g129_to_g130_all_passed=all_g13_130_ok,
        h0_h1_trial_entry_allowed=all_g13_130_ok,
        status=(
            "VERIFIED_ALL_130_GATES_DRY_RUN_SIMULATED_BACKUP"
            if dry_run
            else "VERIFIED_127_OF_130_AWAITING_PHYSICAL_TIER0"
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
            "g13_to_g128_verified": g13_128,
            "g129_to_g130_verified": g129_130,
            "verified_gates": total,
        },
        gates=tuple(gates),
        master_128_report={},
        g129_result={},
        g130_result={},
        errors=(),
        warnings=(),
    )


class TestPhase303DonorAuditAndRedlines(unittest.TestCase):
    def test_01_package_exports_and_schema(self) -> None:
        self.assertEqual(G131, "G131")
        self.assertEqual(G131_GATE_ID, "G131")
        self.assertEqual(G132, "G132")
        self.assertEqual(G132_GATE_ID, "G132")
        self.assertTrue(hasattr(fx3_safety, "evaluate_132gate_preflight"))
        self.assertTrue(hasattr(fx3_safety, "verify_dial_customize_mydial_fn_guard"))
        self.assertTrue(hasattr(fx3_safety, "verify_liveview_grid_lut_embed_guard"))
        self.assertEqual(
            REALHW_DIAL_CUSTOMIZE_MYDIAL_FN_LIVEVIEW_LUT_EMBED_132GATE_SCHEMA,
            "realhw_dial_customize_mydial_fn_liveview_lut_embed_and_132gate_guard_v1",
        )

    def test_02_immutable_redlines_locked(self) -> None:
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

    def test_03_pinned_donor_specs_and_slices(self) -> None:
        self.assertEqual(len(PINNED_PHASE303_DONOR_SPECS), 11)
        self.assertEqual(len(PINNED_FX3_APPFW_SLICES_PHASE303), 55)
        self.assertEqual(len(PINNED_FX6_APPFW_SLICES_PHASE303), 14)
        self.assertEqual(len(PINNED_FX3_APPFW_SLICES_SHA256_PHASE303), 64)
        self.assertEqual(len(PINNED_FX6_APPFW_SLICES_SHA256_PHASE303), 64)

    def test_04_clean_room_forced_audit_succeeds(self) -> None:
        res = audit_phase303_donor_contracts(force_clean_room=True)
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_VERIFIED_SAFE)
        self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(res.files_inspected, 0)
        self.assertEqual(res.raw_firmware_bytes_leaked, 0)
        self.assertTrue(res.fx3_contracts_verified)
        self.assertTrue(res.fx6_contracts_verified)
        self.assertTrue(res.four_lang_resid16_parity_verified)

    def test_05_env_clean_room_flags_respected(self) -> None:
        for env_key in (ENV_FORCE_CLEAN_ROOM, ENV_CLEAN_ROOM_TEST_PHASE303):
            with mock.patch.dict(os.environ, {env_key: "1"}):
                res = audit_phase303_donor_contracts()
                self.assertTrue(res.valid)
                self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_06_explicit_missing_work_root_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.dict(
                os.environ,
                {ENV_FORCE_CLEAN_ROOM: "0", ENV_CLEAN_ROOM_TEST_PHASE303: "0"},
            ):
                res = audit_phase303_donor_contracts(
                    work_root=Path(tmp), force_clean_room=False
                )
                self.assertFalse(res.valid)
                self.assertEqual(res.status, STATUS_BLOCKED_PHASE303_DONOR_INTEGRITY)
                self.assertGreater(len(res.missing_markers), 0)

    def test_07_absent_default_donor_falls_back_to_clean_room(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fake_paths = mock.Mock(work_root=Path(tmp))
            with mock.patch(
                "fx3_safety.realhw_dial_customize_mydial_fn_liveview_lut_embed_and_132gate_guard.resolve_donor_thermal_power_paths",
                return_value=fake_paths,
            ):
                with mock.patch.dict(
                    os.environ,
                    {ENV_FORCE_CLEAN_ROOM: "0", ENV_CLEAN_ROOM_TEST_PHASE303: "0"},
                ):
                    res = audit_phase303_donor_contracts(force_clean_room=False)
                    self.assertTrue(res.valid)
                    self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")
                    self.assertIn("CLEAN_ROOM_SYNTHETIC", res.warnings[0])

    def test_08_donor_audit_respects_local_or_clean_mode_and_budget(self) -> None:
        res = audit_phase303_donor_contracts()
        self.assertTrue(res.valid)
        self.assertEqual(res.raw_firmware_bytes_leaked, 0)
        budget = (
            DONOR_CHECK_CI_MAX_SECONDS_PHASE303
            if os.environ.get("GITHUB_ACTIONS", "").strip().lower() == "true"
            else DONOR_CHECK_MAX_SECONDS_PHASE303
        )
        self.assertLessEqual(res.elapsed_seconds, budget)

    def test_09_donor_specs_override_detects_tamper(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "fake.uxc"
            p.write_bytes(b"TAMPERED")
            override = {
                "fx3_string_english_f_uxc": (
                    "FX3",
                    "fake.uxc",
                    999,
                    "0" * 64,
                    (b"Custom Key/Dial Set.",),
                    "tampered",
                )
            }
            with mock.patch.dict(
                os.environ,
                {ENV_FORCE_CLEAN_ROOM: "0", ENV_CLEAN_ROOM_TEST_PHASE303: "0"},
            ):
                res = audit_phase303_donor_contracts(
                    work_root=Path(tmp),
                    force_clean_room=False,
                    donor_specs_override=override,
                )
                self.assertFalse(res.valid)
                self.assertEqual(res.status, STATUS_BLOCKED_PHASE303_DONOR_INTEGRITY)
                self.assertFalse(res.fx3_contracts_verified)
                self.assertFalse(res.four_lang_resid16_parity_verified)

    def test_10_frozen_dataclasses_immutable(self) -> None:
        res1 = verify_dial_customize_mydial_fn_guard()
        res2 = verify_liveview_grid_lut_embed_guard()
        with self.assertRaises(dataclasses.FrozenInstanceError):
            res1.valid = False  # type: ignore[misc]
        with self.assertRaises(dataclasses.FrozenInstanceError):
            res2.valid = False  # type: ignore[misc]

    def test_11_g131_and_g132_evaluator_results_clean_room(self) -> None:
        v1, r1 = evaluate_g131_dial_customize_mydial_fn_guard(force_clean_room=True)
        v2, r2 = evaluate_g132_liveview_grid_lut_embed_guard(force_clean_room=True)
        self.assertTrue(v1.passed)
        self.assertTrue(r1.valid)
        self.assertEqual(v1.gate_id, "G131")
        self.assertEqual(v1.gate_code, G131_GATE_CODE)
        self.assertTrue(v2.passed)
        self.assertTrue(r2.valid)
        self.assertEqual(v2.gate_id, "G132")
        self.assertEqual(v2.gate_code, G132_GATE_CODE)

    def test_12_g131_and_g132_donor_failure_propagates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.dict(
                os.environ,
                {ENV_FORCE_CLEAN_ROOM: "0", ENV_CLEAN_ROOM_TEST_PHASE303: "0"},
            ):
                v1, r1 = evaluate_g131_dial_customize_mydial_fn_guard(
                    work_root=Path(tmp), force_clean_room=False
                )
                v2, r2 = evaluate_g132_liveview_grid_lut_embed_guard(
                    work_root=Path(tmp), force_clean_room=False
                )
                self.assertFalse(v1.passed)
                self.assertFalse(r1.valid)
                self.assertEqual(r1.status, STATUS_BLOCKED_PHASE303_DONOR_INTEGRITY)
                self.assertFalse(v2.passed)
                self.assertFalse(r2.valid)
                self.assertEqual(r2.status, STATUS_BLOCKED_PHASE303_DONOR_INTEGRITY)


class TestG131DialCustomizeMyDialFnGuard(unittest.TestCase):
    def test_13_default_fx3_dial_customize_5_items_valid(self) -> None:
        res = verify_dial_customize_mydial_fn_guard()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_VERIFIED_G131)
        self.assertEqual(res.dial_customize_menu_path, DIAL_CUSTOMIZE_MENU_PATH_G131)
        self.assertEqual(
            res.dial_customize_5_items,
            (
                "Custom Key/Dial Set.",
                "My Dial Settings",
                "Av/Tv Rotate",
                "Function Ring(Lens)",
                "Lock Operation Parts",
            ),
        )
        self.assertEqual(res.effective_av_tv_rotate, AV_TV_ROTATE_DEFAULT_G131)
        self.assertEqual(res.effective_function_ring, FUNCTION_RING_DEFAULT_G131)
        self.assertEqual(res.effective_lock_operation_parts, LOCK_OPERATION_PARTS_DEFAULT_G131)

    def test_14_all_5_dial_customize_items_survive_cam_reset(self) -> None:
        res = verify_dial_customize_mydial_fn_guard(
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE303,
            requested_av_tv_rotate=AV_TV_ROTATE_REVERSE_G131,
            requested_function_ring=FUNCTION_RING_APSC_S35_FF_G131,
            requested_lock_operation_parts=LOCK_OPERATION_PARTS_ALL_G131,
            requested_my_dial_recall_mode=MY_DIAL_RECALL_TOGGLE_G131,
            requested_my_dial_bank=3,
        )
        self.assertTrue(res.valid)
        self.assertTrue(res.dial_customize_survived_cam_reset)
        self.assertTrue(res.fn_menu_survived_cam_reset)
        self.assertEqual(res.effective_av_tv_rotate, AV_TV_ROTATE_REVERSE_G131)
        self.assertEqual(res.effective_function_ring, FUNCTION_RING_APSC_S35_FF_G131)
        self.assertEqual(res.effective_lock_operation_parts, LOCK_OPERATION_PARTS_ALL_G131)
        self.assertEqual(res.effective_my_dial_recall_mode, MY_DIAL_RECALL_TOGGLE_G131)
        self.assertEqual(res.effective_my_dial_bank, 3)

    def test_15_initialize_resets_dial_customize_and_mydial(self) -> None:
        res = verify_dial_customize_mydial_fn_guard(
            reset_action=RESET_ACTION_INITIALIZE_PHASE303,
            requested_av_tv_rotate=AV_TV_ROTATE_REVERSE_G131,
            requested_function_ring=FUNCTION_RING_APSC_S35_FF_G131,
            requested_lock_operation_parts=LOCK_OPERATION_PARTS_DIAL_WHEEL_G131,
            requested_my_dial_recall_mode=MY_DIAL_RECALL_HOLD_G131,
            requested_my_dial_bank=1,
        )
        self.assertTrue(res.valid)
        self.assertFalse(res.dial_customize_survived_cam_reset)
        self.assertFalse(res.fn_menu_survived_cam_reset)
        self.assertEqual(res.effective_av_tv_rotate, AV_TV_ROTATE_DEFAULT_G131)
        self.assertEqual(res.effective_function_ring, FUNCTION_RING_DEFAULT_G131)
        self.assertEqual(res.effective_lock_operation_parts, LOCK_OPERATION_PARTS_DEFAULT_G131)
        self.assertEqual(res.effective_my_dial_recall_mode, MY_DIAL_RECALL_DEFAULT_G131)
        self.assertIsNone(res.effective_my_dial_bank)

    def test_16_reset_network_set_preserves_dial_customize_and_mydial(self) -> None:
        res = verify_dial_customize_mydial_fn_guard(
            reset_action=RESET_ACTION_RESET_NETWORK_SET_PHASE303,
            requested_av_tv_rotate=AV_TV_ROTATE_REVERSE_G131,
            requested_lock_operation_parts=LOCK_OPERATION_PARTS_MULTI_SELECTOR_G131,
        )
        self.assertTrue(res.valid)
        self.assertTrue(res.dial_customize_survived_cam_reset)
        self.assertEqual(res.effective_av_tv_rotate, AV_TV_ROTATE_REVERSE_G131)
        self.assertEqual(res.effective_lock_operation_parts, LOCK_OPERATION_PARTS_MULTI_SELECTOR_G131)

    def test_17_claiming_dial_customize_resets_on_cam_reset_rejected(self) -> None:
        res = verify_dial_customize_mydial_fn_guard(
            claimed_dial_customize_resets_on_cam_reset=True,
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            res.status, STATUS_BLOCKED_G131_DIAL_CUSTOMIZE_5ITEM_OR_RESET_VIOLATION
        )

    def test_18_wrong_item_count_or_missing_item_rejected(self) -> None:
        res = verify_dial_customize_mydial_fn_guard(
            requested_dial_customize_items=("Custom Key/Dial Set.", "Av/Tv Rotate"),
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            res.status, STATUS_BLOCKED_G131_DIAL_CUSTOMIZE_5ITEM_OR_RESET_VIOLATION
        )

    def test_19_legacy_dial_setup_dial_wheel_setup_lock_rejected_eopnotsupp(self) -> None:
        for legacy in (
            LEGACY_DIAL_SETUP_MENU_NAME_G131,
            LEGACY_DIAL_WHEEL_SETUP_NAME_G131,
            LEGACY_DIAL_WHEEL_LOCK_NAME_G131,
        ):
            res = verify_dial_customize_mydial_fn_guard(
                requested_dial_customize_items=(
                    legacy,
                    "My Dial Settings",
                    "Av/Tv Rotate",
                    "Function Ring(Lens)",
                    "Lock Operation Parts",
                ),
            )
            self.assertFalse(res.valid)
            self.assertEqual(
                res.status, STATUS_BLOCKED_G131_4DIAL_REAR_LR_OR_LEGACY_TRAP_VIOLATION
            )

    def test_20_av_tv_rotate_normal_and_reverse_valid(self) -> None:
        self.assertEqual(ALLOWED_AV_TV_ROTATE_MODES_G131, ("Normal", "Reverse"))
        for mode in ALLOWED_AV_TV_ROTATE_MODES_G131:
            res = verify_dial_customize_mydial_fn_guard(requested_av_tv_rotate=mode)
            self.assertTrue(res.valid)
            self.assertEqual(res.effective_av_tv_rotate, mode)

    def test_21_function_ring_power_focus_and_apsc_s35_ff_valid(self) -> None:
        self.assertEqual(
            ALLOWED_FUNCTION_RING_MODES_G131,
            ("Power Focus", "APS-C/Super 35 mm / Full Frame"),
        )
        for mode in ALLOWED_FUNCTION_RING_MODES_G131:
            res = verify_dial_customize_mydial_fn_guard(requested_function_ring=mode)
            self.assertTrue(res.valid)
            self.assertEqual(res.effective_function_ring, mode)

    def test_22_function_ring_invalid_sentinel_rejected(self) -> None:
        for bad in (DORMANT_FUNCTION_RING_INVALID_G131, "INVALID"):
            res = verify_dial_customize_mydial_fn_guard(requested_function_ring=bad)
            self.assertFalse(res.valid)
            self.assertEqual(
                res.status, STATUS_BLOCKED_G131_DIAL_CUSTOMIZE_5ITEM_OR_RESET_VIOLATION
            )

    def test_23_lock_operation_parts_4_modes_valid(self) -> None:
        self.assertEqual(
            ALLOWED_LOCK_OPERATION_PARTS_MODES_G131,
            ("Off", "Multi-Selector Only", "Dial + Wheel", "All"),
        )
        for mode in ALLOWED_LOCK_OPERATION_PARTS_MODES_G131:
            res = verify_dial_customize_mydial_fn_guard(
                requested_lock_operation_parts=mode
            )
            self.assertTrue(res.valid)
            self.assertEqual(res.effective_lock_operation_parts, mode)

    def test_24_physical_3_dials_front_rear_control_wheel_valid(self) -> None:
        self.assertEqual(
            FX3_PHYSICAL_3_DIALS_G131, ("Front Dial", "Rear Dial", "Control Wheel")
        )
        for dial in FX3_PHYSICAL_3_DIALS_G131:
            res = verify_dial_customize_mydial_fn_guard(requested_physical_dial=dial)
            self.assertTrue(res.valid)
            self.assertEqual(res.requested_physical_dial, dial)
            self.assertTrue(res.dormant_4dial_rear_lr_blocked)
            self.assertIsNone(res.block_errno)

    def test_25_dormant_4dial_rear_dial_left_right_rejected_eopnotsupp_95(self) -> None:
        for trap in ("Rear Dial L", "Rear Dial R", "Rear Dial Left", "Rear Dial Right"):
            res = verify_dial_customize_mydial_fn_guard(requested_physical_dial=trap)
            self.assertFalse(res.valid)
            self.assertEqual(
                res.status, STATUS_BLOCKED_G131_4DIAL_REAR_LR_OR_LEGACY_TRAP_VIOLATION
            )
            self.assertEqual(res.block_errno, EOPNOTSUPP_ERRNO_G131)
            self.assertEqual(res.block_errno_name, EOPNOTSUPP_NAME_G131)

    def test_26_dormant_4dial_bkid_symbols_rejected_eopnotsupp_95(self) -> None:
        for sym in DORMANT_4DIAL_REAR_LR_TRAPS_G131:
            res = verify_dial_customize_mydial_fn_guard(
                requested_dormant_dial_symbol=sym
            )
            self.assertFalse(res.valid)
            self.assertEqual(
                res.status, STATUS_BLOCKED_G131_4DIAL_REAR_LR_OR_LEGACY_TRAP_VIOLATION
            )
            self.assertEqual(res.block_errno, 95)

    def test_27_claimed_4_dials_or_legacy_flags_rejected_eopnotsupp_95(self) -> None:
        for kw in (
            {"claimed_fx3_has_4_dials": True},
            {"claimed_legacy_dial_setup_active": True},
            {"claimed_legacy_dial_wheel_lock_active": True},
            {"requested_dial_customize_legacy_item": "BKID_APP_setting_dial_setup"},
        ):
            res = verify_dial_customize_mydial_fn_guard(**kw)  # type: ignore[arg-type]
            self.assertFalse(res.valid)
            self.assertEqual(res.block_errno, EOPNOTSUPP_ERRNO_G131)

    def test_28_my_dial_1_to_3_hold_and_toggle_recall_valid(self) -> None:
        for recall in (MY_DIAL_RECALL_HOLD_G131, MY_DIAL_RECALL_TOGGLE_G131):
            for sm in (SHOOT_MODE_STILL_PHASE303, SHOOT_MODE_MOVIE_PHASE303):
                res = verify_dial_customize_mydial_fn_guard(
                    shoot_mode=sm,
                    requested_my_dial_recall_mode=recall,
                    requested_my_dial_bank=3,
                    my_dial_bank_1_configured=True,
                    my_dial_bank_2_configured=False,
                    my_dial_bank_3_configured=True,
                )
                self.assertTrue(res.valid)
                self.assertTrue(res.my_dial_nvram_shared_across_modes)
                self.assertTrue(res.my_dial_recall_per_mode_custom_key_split)
                self.assertEqual(res.effective_my_dial_recall_mode, recall)
                self.assertEqual(res.effective_my_dial_bank, 3)

    def test_29_my_dial_1_2_3_cycle_skips_empty_all_not_set_banks(self) -> None:
        res = verify_dial_customize_mydial_fn_guard(
            requested_my_dial_recall_mode=MY_DIAL_RECALL_CYCLE_G131,
            requested_my_dial_bank=2,
            my_dial_bank_1_configured=True,
            my_dial_bank_2_configured=False,
            my_dial_bank_3_configured=True,
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.my_dial_cycle_order, (1, 3))
        self.assertEqual(res.my_dial_skipped_empty_banks, (2,))
        self.assertEqual(res.effective_my_dial_bank, 1)

    def test_30_my_dial_temp_unlock_override_when_locked_dial_wheel_or_all(self) -> None:
        for lock_mode in (LOCK_OPERATION_PARTS_DIAL_WHEEL_G131, LOCK_OPERATION_PARTS_ALL_G131):
            res = verify_dial_customize_mydial_fn_guard(
                requested_lock_operation_parts=lock_mode,
                requested_my_dial_recall_mode=MY_DIAL_RECALL_HOLD_G131,
                requested_my_dial_bank=1,
            )
            self.assertTrue(res.valid)
            self.assertTrue(res.my_dial_temp_unlock_override_active)

    def test_31_my_dial_temp_unlock_inactive_when_only_multiselector_or_empty(self) -> None:
        r_ms = verify_dial_customize_mydial_fn_guard(
            requested_lock_operation_parts=LOCK_OPERATION_PARTS_MULTI_SELECTOR_G131,
            requested_my_dial_recall_mode=MY_DIAL_RECALL_HOLD_G131,
            requested_my_dial_bank=1,
        )
        r_empty = verify_dial_customize_mydial_fn_guard(
            requested_lock_operation_parts=LOCK_OPERATION_PARTS_ALL_G131,
            requested_my_dial_recall_mode=MY_DIAL_RECALL_HOLD_G131,
            requested_my_dial_bank=2,
            my_dial_bank_2_configured=False,
        )
        self.assertFalse(r_ms.my_dial_temp_unlock_override_active)
        self.assertFalse(r_empty.my_dial_temp_unlock_override_active)
        self.assertIsNone(r_empty.effective_my_dial_bank)

    def test_32_my_dial_cycle_including_empty_or_blocked_by_lock_rejected(self) -> None:
        for kw in (
            {"claimed_cycle_includes_empty_mydial_bank": True},
            {"claimed_lock_blocks_recalled_mydial": True},
            {"claimed_mydial_resets_on_cam_reset": True},
            {"claimed_fn_menu_resets_on_cam_reset": True},
        ):
            res = verify_dial_customize_mydial_fn_guard(**kw)  # type: ignore[arg-type]
            self.assertFalse(res.valid)
            self.assertEqual(
                res.status, STATUS_BLOCKED_G131_MYDIAL_OR_FN_12X2_SPLIT_VIOLATION
            )

    def test_33_fn_menu_strict_12_still_and_12_movie_split(self) -> None:
        r_still = verify_dial_customize_mydial_fn_guard(shoot_mode=SHOOT_MODE_STILL_PHASE303)
        r_movie = verify_dial_customize_mydial_fn_guard(shoot_mode=SHOOT_MODE_MOVIE_PHASE303)
        r_sq = verify_dial_customize_mydial_fn_guard(shoot_mode=SHOOT_MODE_SQ_PHASE303)
        self.assertEqual(r_still.fn_menu_menu_path, FN_MENU_SETTINGS_MENU_PATH_G131)
        self.assertEqual(r_still.fn_menu_still_slots, FN_MENU_STILL_SLOTS_G131)
        self.assertEqual(r_still.fn_menu_movie_slots, FN_MENU_MOVIE_SLOTS_G131)
        self.assertEqual(r_still.fn_menu_active_mode_pool, "still_12")
        self.assertEqual(r_movie.fn_menu_active_mode_pool, "movie_12")
        self.assertEqual(r_sq.fn_menu_active_mode_pool, "movie_12")

        for bad_kw in (
            {"fn_menu_still_slots": 16},
            {"fn_menu_movie_slots": 8},
            {"claimed_fn_menu_shared_single_pool": True},
        ):
            bad = verify_dial_customize_mydial_fn_guard(**bad_kw)  # type: ignore[arg-type]
            self.assertFalse(bad.valid)
            self.assertEqual(
                bad.status, STATUS_BLOCKED_G131_MYDIAL_OR_FN_12X2_SPLIT_VIOLATION
            )

    def test_34_fn_invocation_blocked_when_active_mode_all_12_not_set(self) -> None:
        res = verify_dial_customize_mydial_fn_guard(
            shoot_mode=SHOOT_MODE_MOVIE_PHASE303,
            fn_movie_all_not_set=True,
            fn_invoke_requested=True,
        )
        self.assertFalse(res.valid)
        self.assertTrue(res.fn_invocation_blocked_all_not_set)
        self.assertEqual(
            res.status, STATUS_BLOCKED_G131_MYDIAL_OR_FN_12X2_SPLIT_VIOLATION
        )

    def test_35_fn_all_not_set_still_vs_movie_independent_isolation(self) -> None:
        res = verify_dial_customize_mydial_fn_guard(
            shoot_mode=SHOOT_MODE_STILL_PHASE303,
            fn_still_all_not_set=False,
            fn_movie_all_not_set=True,
            fn_invoke_requested=True,
        )
        self.assertTrue(res.valid)
        self.assertFalse(res.fn_invocation_blocked_all_not_set)

    def test_36_fx6_dial_controls_status_screens_direct_menu_crosswire_rejected(self) -> None:
        self.assertEqual(
            FX6_DIAL_CONTROLS_G131,
            ("Multi Function Dial", "Grip Dial", "Handle Dial", "IRIS Dial", "ND Dial"),
        )
        self.assertEqual(
            FX6_STATUS_AND_DIRECT_MENU_SURFACES_G131,
            ("Status Screens", "Direct Menu"),
        )
        for kw in (
            {"claimed_fx6_has_mydial_or_fn_menu": True},
            {"claimed_fx3_has_multi_function_dial_or_direct_menu": True},
            {"claimed_fx3_has_grip_or_handle_dial": True},
            {"target_model": FX6_MODEL_NAME_PHASE303, "av_tv_rotate_use_requested": True},
            {"target_model": FX6_MODEL_NAME_PHASE303, "lock_operation_parts_use_requested": True},
            {"target_model": FX6_MODEL_NAME_PHASE303, "my_dial_use_requested": True},
            {"target_model": FX6_MODEL_NAME_PHASE303, "fn_menu_use_requested": True},
        ):
            res = verify_dial_customize_mydial_fn_guard(**kw)  # type: ignore[arg-type]
            self.assertFalse(res.valid)
            self.assertEqual(
                res.status,
                STATUS_BLOCKED_G131_FX6_DIAL_OR_DIRECT_MENU_CROSSWIRE_VIOLATION,
            )

    def test_37_g131_768_state_matrix_holds(self) -> None:
        m = compute_dial_customize_mydial_fn_matrix()
        self.assertEqual(m["states_checked"], 768)
        self.assertTrue(m["all_invariants_hold"])
        self.assertEqual(m["cam_reset_survived_count"], 192)
        self.assertEqual(m["initialize_reset_count"], 192)
        self.assertGreater(m["temp_unlock_active_count"], 0)

    def test_38_g131_invalid_telemetry_and_persistent_emmc_write_blocked(self) -> None:
        bad1 = verify_dial_customize_mydial_fn_guard(shoot_mode="Timelapse")
        bad2 = verify_dial_customize_mydial_fn_guard(requested_my_dial_bank=4)
        bad3 = verify_dial_customize_mydial_fn_guard(requested_physical_dial="Grip Dial")
        for b in (bad1, bad2, bad3):
            self.assertFalse(b.valid)
            self.assertEqual(b.status, STATUS_BLOCKED_G131_TELEMETRY_INVALID)

        v, r = evaluate_g131_dial_customize_mydial_fn_guard(
            force_clean_room=True,
            request_persistent_emmc_writes=True,
        )
        self.assertFalse(v.passed)
        self.assertFalse(r.valid)
        self.assertEqual(r.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)


class TestG132LiveViewGridLutEmbedGuard(unittest.TestCase):
    def test_39_default_liveview_display_set_3_subitems_still_valid(self) -> None:
        res = verify_liveview_grid_lut_embed_guard()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_VERIFIED_G132)
        self.assertEqual(
            res.live_view_display_set_menu_path, LIVE_VIEW_DISPLAY_SET_MENU_PATH_G132
        )
        self.assertEqual(
            res.live_view_display_set_3_subitems,
            ("Live View Display", "Exposure Effect", "Frame Rate Low Limit"),
        )
        self.assertTrue(res.live_view_display_set_still_only)
        self.assertEqual(res.effective_live_view_display, LIVE_VIEW_SETTING_EFFECT_ON_G132)
        self.assertEqual(res.effective_exposure_effect, EXPOSURE_EFFECT_SET_AND_FLASH_G132)
        self.assertEqual(res.effective_frame_rate_low_limit, FRAME_RATE_LOW_LIMIT_OFF_G132)

    def test_40_liveview_display_set_wrong_path_or_subitems_rejected(self) -> None:
        for kw in (
            {"live_view_display_set_menu_path": "MENU -> (Setup) -> [Display Option]"},
            {"requested_live_view_subitems": ("Live View Display", "Exposure Effect")},
        ):
            res = verify_liveview_grid_lut_embed_guard(**kw)  # type: ignore[arg-type]
            self.assertFalse(res.valid)
            self.assertEqual(
                res.status,
                STATUS_BLOCKED_G132_LIVEVIEW_3ITEM_BRIGHT_OR_RESET_VIOLATION,
            )

    def test_41_liveview_display_set_still_only_blocks_movie_and_sq(self) -> None:
        for sm in (SHOOT_MODE_MOVIE_PHASE303, SHOOT_MODE_SQ_PHASE303):
            res = verify_liveview_grid_lut_embed_guard(
                shoot_mode=sm,
                live_view_display_set_use_requested=True,
            )
            self.assertFalse(res.valid)
            self.assertEqual(
                res.status,
                STATUS_BLOCKED_G132_LIVEVIEW_3ITEM_BRIGHT_OR_RESET_VIOLATION,
            )

    def test_42_bright_monitoring_forces_setting_effect_off(self) -> None:
        res = verify_liveview_grid_lut_embed_guard(
            requested_live_view_display=LIVE_VIEW_SETTING_EFFECT_ON_G132,
            bright_monitoring_active=True,
        )
        self.assertTrue(res.valid)
        self.assertTrue(res.bright_monitoring_active)
        self.assertEqual(
            res.effective_live_view_display, LIVE_VIEW_SETTING_EFFECT_OFF_G132
        )

    def test_43_claiming_setting_effect_on_with_bright_monitoring_rejected(self) -> None:
        res = verify_liveview_grid_lut_embed_guard(
            bright_monitoring_active=True,
            claimed_setting_effect_on_with_bright_monitoring=True,
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            res.status,
            STATUS_BLOCKED_G132_LIVEVIEW_3ITEM_BRIGHT_OR_RESET_VIOLATION,
        )

    def test_44_exposure_effect_modes_and_init_only_persistence(self) -> None:
        self.assertEqual(
            ALLOWED_EXPOSURE_EFFECT_MODES_G132,
            ("Exposure Set. & flash", "Exposure Setting Only"),
        )
        for mode in ALLOWED_EXPOSURE_EFFECT_MODES_G132:
            res = verify_liveview_grid_lut_embed_guard(
                requested_exposure_effect=mode,
                requested_live_view_display=LIVE_VIEW_SETTING_EFFECT_OFF_G132,
                reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE303,
            )
            self.assertTrue(res.valid)
            self.assertTrue(res.live_view_and_exposure_effect_survived_cam_reset)
            self.assertEqual(res.effective_exposure_effect, mode)
            self.assertEqual(
                res.effective_live_view_display, LIVE_VIEW_SETTING_EFFECT_OFF_G132
            )

    def test_45_frame_rate_low_limit_resets_on_cam_reset_only(self) -> None:
        res = verify_liveview_grid_lut_embed_guard(
            requested_frame_rate_low_limit=FRAME_RATE_LOW_LIMIT_ON_G132,
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE303,
        )
        self.assertTrue(res.valid)
        self.assertTrue(res.frame_rate_low_limit_reset_on_cam_reset)
        self.assertEqual(
            res.effective_frame_rate_low_limit, FRAME_RATE_LOW_LIMIT_OFF_G132
        )

        for bad_kw in (
            {"claimed_frame_rate_low_limit_ignores_cam_reset": True},
            {"claimed_live_view_or_exposure_effect_resets_on_cam_reset": True},
        ):
            bad = verify_liveview_grid_lut_embed_guard(**bad_kw)  # type: ignore[arg-type]
            self.assertFalse(bad.valid)
            self.assertEqual(
                bad.status,
                STATUS_BLOCKED_G132_LIVEVIEW_3ITEM_BRIGHT_OR_RESET_VIOLATION,
            )

    def test_46_grid_line_display_and_3_types_survive_cam_reset(self) -> None:
        self.assertEqual(
            ALLOWED_GRID_LINE_TYPES_G132,
            ("Rule of 3rds Grid", "Square Grid", "Diag. + Square Grid"),
        )
        for gt in ALLOWED_GRID_LINE_TYPES_G132:
            res = verify_liveview_grid_lut_embed_guard(
                requested_grid_line_display=GRID_LINE_DISPLAY_ON_G132,
                requested_grid_line_type=gt,
                reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE303,
            )
            self.assertTrue(res.valid)
            self.assertTrue(res.grid_line_survived_cam_reset)
            self.assertEqual(res.effective_grid_line_display, GRID_LINE_DISPLAY_ON_G132)
            self.assertEqual(res.effective_grid_line_type, gt)

    def test_47_grid_line_isolated_from_hdmi_clean_feed_when_hdmi_info_off(self) -> None:
        res = verify_liveview_grid_lut_embed_guard(
            requested_grid_line_display=GRID_LINE_DISPLAY_ON_G132,
            requested_grid_line_type=GRID_LINE_TYPE_DIAG_SQUARE_G132,
            requested_hdmi_info_display=HDMI_INFO_DISPLAY_OFF_G132,
        )
        self.assertTrue(res.valid)
        self.assertTrue(res.grid_line_isolated_from_hdmi_clean_feed)
        self.assertTrue(res.hdmi_clean_feed_preserved)

        r_on = verify_liveview_grid_lut_embed_guard(
            requested_grid_line_display=GRID_LINE_DISPLAY_ON_G132,
            requested_hdmi_info_display=HDMI_INFO_DISPLAY_ON_G132,
        )
        self.assertTrue(r_on.valid)
        self.assertFalse(r_on.grid_line_isolated_from_hdmi_clean_feed)

    def test_48_raw_hdmi_and_hdmi_only_off_force_clean_feed_isolation(self) -> None:
        for kw in (
            {"raw_hdmi_output_active": True},
            {"hdmi_only_off_mode_active": True},
        ):
            res = verify_liveview_grid_lut_embed_guard(
                requested_grid_line_display=GRID_LINE_DISPLAY_ON_G132,
                requested_hdmi_info_display=HDMI_INFO_DISPLAY_ON_G132,
                **kw,
            )
            self.assertTrue(res.valid)
            self.assertEqual(res.effective_hdmi_info_display, HDMI_INFO_DISPLAY_OFF_G132)
            self.assertTrue(res.grid_line_isolated_from_hdmi_clean_feed)
            self.assertTrue(res.hdmi_clean_feed_preserved)

    def test_49_claiming_grid_burned_into_clean_hdmi_or_cam_reset_rejected(self) -> None:
        for kw in (
            {"claimed_grid_line_burned_into_clean_hdmi": True},
            {"claimed_grid_line_resets_on_cam_reset": True},
        ):
            res = verify_liveview_grid_lut_embed_guard(**kw)  # type: ignore[arg-type]
            self.assertFalse(res.valid)
            self.assertEqual(
                res.status, STATUS_BLOCKED_G132_GRID_CLEAN_HDMI_OR_FX6_PNG_VIOLATION
            )

    def test_50_dormant_fx6_custom_png_grids_and_marker_safety_zones_rejected(self) -> None:
        self.assertEqual(FX6_MARKER_SAFETY_ZONES_G132, ("80%", "90%", "92.5%", "95%"))
        for sym in FX6_DORMANT_CUSTOM_PNG_GRID_SYMBOLS_G132:
            res = verify_liveview_grid_lut_embed_guard(
                requested_dormant_grid_symbol=sym
            )
            self.assertFalse(res.valid)
            self.assertEqual(
                res.status, STATUS_BLOCKED_G132_GRID_CLEAN_HDMI_OR_FX6_PNG_VIOLATION
            )
        for kw in (
            {"fx6_custom_png_grid_requested": True},
            {"claimed_fx3_supports_custom_aspect_or_safety_92_5_95": True},
            {"target_model": FX6_MODEL_NAME_PHASE303, "fx3_grid_line_type_use_requested": True},
        ):
            res = verify_liveview_grid_lut_embed_guard(**kw)  # type: ignore[arg-type]
            self.assertFalse(res.valid)
            self.assertEqual(
                res.status, STATUS_BLOCKED_G132_GRID_CLEAN_HDMI_OR_FX6_PNG_VIOLATION
            )

    def test_51_manage_user_luts_user1_to_16_17pt_33pt_cube_valid(self) -> None:
        self.assertEqual(len(ALLOWED_USER_LUT_SLOTS_G132), 16)
        self.assertEqual(ALLOWED_CUBE_GRID_POINTS_G132, (17, 33))
        for pts in ALLOWED_CUBE_GRID_POINTS_G132:
            for slot_name in ("User1", "User8", "User16"):
                res = verify_liveview_grid_lut_embed_guard(
                    requested_cube_grid_points=pts,
                    requested_cube_filename="FX3_CustomLook_33.cube",
                    requested_select_lut=slot_name,
                    requested_lut_or_rec_op=LUT_OP_IMPORT_USER_LUT_G132,
                    requested_target_slot=MEDIA_SLOT_1_PHASE303,
                )
                self.assertTrue(res.valid)
                self.assertEqual(res.manage_user_luts_menu_path, MANAGE_USER_LUTS_MENU_PATH_G132)
                self.assertEqual(res.effective_select_lut, slot_name)
                self.assertTrue(res.lut_import_read_only_safe)
                self.assertEqual(res.slot1_data_sector_writes, 0)

    def test_52_user_luts_card_folder_sd_sdxc_vs_cfexpress_validated(self) -> None:
        r_sdxc = verify_liveview_grid_lut_embed_guard(
            card_type=CARD_TYPE_SDXC_G132,
            requested_lut_folder_path=LUT_FOLDER_SD_SDXC_G132,
        )
        r_cfa = verify_liveview_grid_lut_embed_guard(
            card_type=CARD_TYPE_CFEXPRESS_A_G132,
            requested_lut_folder_path=LUT_FOLDER_CFEXPRESS_G132,
        )
        self.assertTrue(r_sdxc.valid)
        self.assertEqual(r_sdxc.expected_lut_folder_path, "/Private/Sony/PRO/LUT")
        self.assertTrue(r_cfa.valid)
        self.assertEqual(r_cfa.expected_lut_folder_path, "/Sony/PRO/LUT")

        mismatch = verify_liveview_grid_lut_embed_guard(
            card_type=CARD_TYPE_CFEXPRESS_A_G132,
            requested_lut_folder_path=LUT_FOLDER_SD_SDXC_G132,
        )
        self.assertFalse(mismatch.valid)
        self.assertEqual(
            mismatch.status, STATUS_BLOCKED_G132_LUT_PATH_SDHC_OR_PPLUT_RESET_VIOLATION
        )

    def test_53_unsupported_cube_grid_points_or_bad_filename_rejected(self) -> None:
        for bad_kw in (
            {"requested_cube_grid_points": 65},
            {"requested_cube_filename": "bad.3dl"},
            {"requested_cube_filename": ("A" * 60) + ".cube"},
            {"requested_cube_filename": "非ASCII.cube"},
        ):
            res = verify_liveview_grid_lut_embed_guard(**bad_kw)  # type: ignore[arg-type]
            self.assertFalse(res.valid)
            self.assertEqual(
                res.status, STATUS_BLOCKED_G132_LUT_PATH_SDHC_OR_PPLUT_RESET_VIOLATION
            )

    def test_54_select_lut_slog3_s709_709_800_user_slots_and_cam_reset(self) -> None:
        for preset in (SELECT_LUT_SLOG3_G132, SELECT_LUT_S709_G132, SELECT_LUT_709_800_G132, "User12"):
            res = verify_liveview_grid_lut_embed_guard(requested_select_lut=preset)
            self.assertTrue(res.valid)
            self.assertEqual(res.effective_select_lut, preset)

        rst = verify_liveview_grid_lut_embed_guard(
            requested_select_lut="User12",
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE303,
        )
        self.assertTrue(rst.valid)
        self.assertTrue(rst.select_lut_reset_on_cam_reset)
        self.assertTrue(rst.user_luts_survived_cam_reset)
        self.assertEqual(rst.effective_select_lut, SELECT_LUT_DEFAULT_G132)

    def test_55_embed_lut_file_path_under_log_shooting_not_color_tone(self) -> None:
        ok = verify_liveview_grid_lut_embed_guard(
            embed_lut_file_menu_path=EMBED_LUT_FILE_MENU_PATH_G132,
        )
        self.assertTrue(ok.valid)
        for bad_kw in (
            {"embed_lut_file_menu_path": EMBED_LUT_FILE_WRONG_PATH_G132},
            {"claimed_embed_lut_under_color_tone": True},
        ):
            bad = verify_liveview_grid_lut_embed_guard(**bad_kw)  # type: ignore[arg-type]
            self.assertFalse(bad.valid)
            self.assertEqual(
                bad.status, STATUS_BLOCKED_G132_LUT_PATH_SDHC_OR_PPLUT_RESET_VIOLATION
            )

    def test_56_embed_lut_file_hardware_locked_off_on_sd_sdhc(self) -> None:
        res = verify_liveview_grid_lut_embed_guard(
            card_type=CARD_TYPE_SD_SDHC_G132,
            requested_embed_lut_file=EMBED_LUT_ON_G132,
            embed_lut_recording_requested=False,
        )
        self.assertTrue(res.valid)
        self.assertTrue(res.embed_lut_locked_off_by_sdhc)
        self.assertEqual(res.effective_embed_lut_file, EMBED_LUT_OFF_G132)

    def test_57_embed_lut_recording_on_sd_sdhc_when_on_rejected(self) -> None:
        for bad_kw in (
            {"claimed_embed_lut_allowed_on_sdhc": True},
            {
                "card_type": CARD_TYPE_SD_SDHC_G132,
                "requested_embed_lut_file": EMBED_LUT_ON_G132,
                "embed_lut_recording_requested": True,
            },
        ):
            bad = verify_liveview_grid_lut_embed_guard(**bad_kw)  # type: ignore[arg-type]
            self.assertFalse(bad.valid)
            self.assertEqual(
                bad.status, STATUS_BLOCKED_G132_LUT_PATH_SDHC_OR_PPLUT_RESET_VIOLATION
            )

    def test_58_embed_lut_container_metadata_preserves_slog3_no_sidecar(self) -> None:
        res = verify_liveview_grid_lut_embed_guard(
            card_type=CARD_TYPE_CFEXPRESS_A_G132,
            requested_embed_lut_file=EMBED_LUT_ON_G132,
        )
        self.assertTrue(res.valid)
        self.assertTrue(res.embed_lut_preserves_slog3_pixels)
        self.assertFalse(res.embed_lut_creates_external_sidecar)
        self.assertTrue(res.embed_lut_metadata_embedded_in_container)

        for bad_kw in (
            {"claimed_embed_lut_creates_sidecar": True},
            {"claimed_embed_lut_bakes_pixels": True},
        ):
            bad = verify_liveview_grid_lut_embed_guard(**bad_kw)  # type: ignore[arg-type]
            self.assertFalse(bad.valid)
            self.assertEqual(
                bad.status, STATUS_BLOCKED_G132_LUT_PATH_SDHC_OR_PPLUT_RESET_VIOLATION
            )

    def test_59_pplut1_to_4_irreversible_bake_and_dual_reset_contract(self) -> None:
        self.assertEqual(PPLUT_SLOTS_G132, ("PPLUT1", "PPLUT2", "PPLUT3", "PPLUT4"))
        for rst in (
            RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE303,
            RESET_ACTION_INITIALIZE_PHASE303,
        ):
            res = verify_liveview_grid_lut_embed_guard(reset_action=rst)
            self.assertTrue(res.valid)
            self.assertTrue(res.pplut_bakes_pixels_irreversibly)
            self.assertTrue(res.pplut_reset_on_cam_reset_and_initialize)

        bad = verify_liveview_grid_lut_embed_guard(
            claimed_pplut_preserves_slog3_or_survives_reset=True
        )
        self.assertFalse(bad.valid)
        self.assertEqual(
            bad.status, STATUS_BLOCKED_G132_LUT_PATH_SDHC_OR_PPLUT_RESET_VIOLATION
        )

    def test_60_fx6_16_ui_cap_vs_50_appfw_buffer_and_sdi_hdmi_split_enforced(self) -> None:
        ok = verify_liveview_grid_lut_embed_guard()
        self.assertEqual(ok.fx6_user_lut_ui_cap, 16)
        self.assertEqual(ok.fx6_appfw_buffer_slots, 50)
        self.assertEqual(FX6_USER_LUT_ACTIVE_UI_CAP_G132, 16)
        self.assertEqual(FX6_APPFW_PRM_USER_LUT_BUFFER_SLOTS_G132, 50)
        for bad_kw in (
            {"claimed_fx6_exposes_50_user_luts_in_ui": True},
            {"claimed_fx3_has_independent_sdi_hdmi_lut_switches": True},
        ):
            bad = verify_liveview_grid_lut_embed_guard(**bad_kw)  # type: ignore[arg-type]
            self.assertFalse(bad.valid)
            self.assertEqual(
                bad.status, STATUS_BLOCKED_G132_LUT_PATH_SDHC_OR_PPLUT_RESET_VIOLATION
            )

    def test_61_slot1_import_user_lut_read_only_safe_zero_writes(self) -> None:
        res = verify_liveview_grid_lut_embed_guard(
            requested_lut_or_rec_op=LUT_OP_IMPORT_USER_LUT_G132,
            requested_target_slot=MEDIA_SLOT_1_PHASE303,
            slot_1_contains_tier0_vault=True,
            slot_1_write_protected=True,
        )
        self.assertTrue(res.valid)
        self.assertTrue(res.lut_import_read_only_safe)
        self.assertFalse(res.slot1_vault_firewall_blocked)
        self.assertEqual(res.slot1_data_sector_writes, 0)
        self.assertFalse(res.slot1_avf_info_mutated)

    def test_62_slot1_tier0_vault_blocks_write_ops_ebusy_16(self) -> None:
        for op in (
            LUT_OP_MAKE_CUBE_FOLDER_G132,
            LUT_OP_WRITE_CUBE_OR_SIDECAR_G132,
            LUT_OP_RECORD_EMBED_LUT_G132,
            LUT_OP_RECORD_PPLUT_G132,
        ):
            res = verify_liveview_grid_lut_embed_guard(
                requested_lut_or_rec_op=op,
                requested_target_slot=MEDIA_SLOT_1_PHASE303,
                slot_1_contains_tier0_vault=True,
                slot_1_write_protected=False,
            )
            self.assertFalse(res.valid)
            self.assertEqual(
                res.status,
                STATUS_BLOCKED_G132_SLOT1_TIER0_VAULT_WRITE_FIREWALL_VIOLATION,
            )
            self.assertTrue(res.slot1_vault_firewall_blocked)
            self.assertEqual(res.block_errno, "EBUSY")
            self.assertEqual(res.block_errno_code, EBUSY_ERRNO_G132)
            self.assertEqual(res.slot1_data_sector_writes, 0)
            self.assertFalse(res.slot1_avf_info_mutated)

    def test_63_slot1_write_protect_blocks_write_ops_erofs_30(self) -> None:
        for op in (LUT_OP_RECORD_EMBED_LUT_G132, LUT_OP_RECORD_PPLUT_G132):
            res = verify_liveview_grid_lut_embed_guard(
                requested_lut_or_rec_op=op,
                requested_target_slot=MEDIA_SLOT_1_PHASE303,
                slot_1_contains_tier0_vault=False,
                slot_1_write_protected=True,
            )
            self.assertFalse(res.valid)
            self.assertEqual(res.block_errno, "EROFS")
            self.assertEqual(res.block_errno_code, EROFS_ERRNO_G132)
            self.assertEqual(res.slot1_data_sector_writes, 0)

    def test_64_slot2_write_ops_allowed_with_zero_slot1_writes(self) -> None:
        for op in (
            LUT_OP_MAKE_CUBE_FOLDER_G132,
            LUT_OP_RECORD_EMBED_LUT_G132,
            LUT_OP_RECORD_PPLUT_G132,
        ):
            res = verify_liveview_grid_lut_embed_guard(
                requested_lut_or_rec_op=op,
                requested_target_slot=MEDIA_SLOT_2_PHASE303,
                slot_1_contains_tier0_vault=True,
                slot_1_write_protected=True,
            )
            self.assertTrue(res.valid)
            self.assertFalse(res.slot1_vault_firewall_blocked)
            self.assertEqual(res.slot1_data_sector_writes, 0)
            self.assertFalse(res.slot1_avf_info_mutated)

    def test_65_slot1_write_allowed_only_if_vault_absent_and_unlocked(self) -> None:
        res = verify_liveview_grid_lut_embed_guard(
            requested_lut_or_rec_op=LUT_OP_RECORD_EMBED_LUT_G132,
            requested_target_slot=MEDIA_SLOT_1_PHASE303,
            slot_1_contains_tier0_vault=False,
            slot_1_write_protected=False,
        )
        self.assertTrue(res.valid)
        self.assertFalse(res.slot1_vault_firewall_blocked)

    def test_66_g132_864_state_matrix_holds(self) -> None:
        m = compute_liveview_grid_lut_embed_matrix()
        self.assertEqual(m["states_checked"], 864)
        self.assertTrue(m["all_invariants_hold"])
        self.assertEqual(m["bright_override_count"], 432)
        self.assertEqual(m["sdhc_embed_locked_count"], 288)
        self.assertEqual(m["clean_hdmi_isolated_count"], 432)
        self.assertEqual(m["cam_reset_fr_low_count"], 288)

    def test_67_g132_invalid_telemetry_and_persistent_emmc_write_blocked(self) -> None:
        bad1 = verify_liveview_grid_lut_embed_guard(
            requested_select_lut="User17"
        )
        bad2 = verify_liveview_grid_lut_embed_guard(
            requested_lut_or_rec_op="UnknownOp"
        )
        bad3 = verify_liveview_grid_lut_embed_guard(
            requested_grid_line_type="DiagonalOnly"
        )
        for b in (bad1, bad2, bad3):
            self.assertFalse(b.valid)
            self.assertEqual(b.status, STATUS_BLOCKED_G132_TELEMETRY_INVALID)

        bad_bool_cube = verify_liveview_grid_lut_embed_guard(
            requested_cube_grid_points=True  # type: ignore[arg-type]
        )
        self.assertFalse(bad_bool_cube.valid)
        self.assertEqual(
            bad_bool_cube.status,
            STATUS_BLOCKED_G132_LUT_PATH_SDHC_OR_PPLUT_RESET_VIOLATION,
        )

        v, r = evaluate_g132_liveview_grid_lut_embed_guard(
            force_clean_room=True,
            request_persistent_emmc_writes=True,
        )
        self.assertFalse(v.passed)
        self.assertFalse(r.valid)
        self.assertEqual(r.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)


class TestUnified132GateEngineAndCli(unittest.TestCase):
    def test_68_stub_132gate_offline_129_of_132(self) -> None:
        rep = evaluate_132gate_preflight(
            force_clean_room=True,
            master_130_override=_make_stub_master130(dry_run=False),
        )
        self.assertEqual(rep.summary["total_gates"], 132)
        self.assertEqual(rep.summary["verified_gates"], 129)
        self.assertEqual(rep.summary["blocked_or_pending_gates"], 3)
        self.assertTrue(rep.offline_129_gates_verified)
        self.assertFalse(rep.all_132_gates_verified)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.cross_model_flash_authorized)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)
        self.assertEqual(rep.status, "VERIFIED_129_OF_132_AWAITING_PHYSICAL_TIER0")
        self.assertEqual(len(rep.gates), 132)

    def test_69_stub_132gate_dry_run_132_of_132(self) -> None:
        rep = evaluate_132_master_safety_gates(
            force_clean_room=True,
            simulate_bench_dry_run=True,
            master_130_override=_make_stub_master130(dry_run=True),
        )
        self.assertEqual(rep.summary["verified_gates"], 132)
        self.assertTrue(rep.all_132_gates_verified)
        self.assertTrue(rep.dry_run_rehearsal_only)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertEqual(rep.status, "VERIFIED_ALL_132_GATES_DRY_RUN_SIMULATED_BACKUP")

    def test_70_g131_failure_propagates_to_132gate_report(self) -> None:
        rep = evaluate_132gate_preflight(
            force_clean_room=True,
            master_130_override=_make_stub_master130(dry_run=True),
            dial_customize_mydial_fn_kwargs={"requested_physical_dial": "Rear Dial L"},
        )
        self.assertFalse(rep.g131_to_g132_all_passed)
        self.assertFalse(rep.all_132_gates_verified)
        self.assertEqual(
            rep.status, STATUS_BLOCKED_G131_4DIAL_REAR_LR_OR_LEGACY_TRAP_VIOLATION
        )

    def test_71_g132_failure_propagates_to_132gate_report(self) -> None:
        rep = evaluate_132gate_preflight(
            force_clean_room=True,
            master_130_override=_make_stub_master130(dry_run=True),
            liveview_grid_lut_embed_kwargs={
                "requested_lut_or_rec_op": LUT_OP_RECORD_EMBED_LUT_G132,
                "requested_target_slot": MEDIA_SLOT_1_PHASE303,
                "slot_1_contains_tier0_vault": True,
            },
        )
        self.assertFalse(rep.g131_to_g132_all_passed)
        self.assertFalse(rep.all_132_gates_verified)
        self.assertEqual(
            rep.status,
            STATUS_BLOCKED_G132_SLOT1_TIER0_VAULT_WRITE_FIREWALL_VIOLATION,
        )

    def test_72_g130_failure_propagates_to_132gate_report(self) -> None:
        stub130 = _make_stub_master130(dry_run=True, all_g13_130_ok=False)
        bad130 = dataclasses.replace(
            stub130,
            status=STATUS_BLOCKED_G130_PLAYBACK_EDIT_DORMANT_OR_SLOT1_VAULT_VIOLATION,
        )
        rep = evaluate_132gate_preflight(
            force_clean_room=True,
            master_130_override=bad130,
        )
        self.assertFalse(rep.g13_to_g132_all_passed)
        self.assertFalse(rep.all_132_gates_verified)
        self.assertEqual(
            rep.status,
            STATUS_BLOCKED_G130_PLAYBACK_EDIT_DORMANT_OR_SLOT1_VAULT_VIOLATION,
        )

    def test_73_persistent_emmc_write_blocks_132gate_report(self) -> None:
        rep = run_132_gate_preflight(
            force_clean_room=True,
            request_persistent_emmc_writes=True,
            master_130_override=_make_stub_master130(dry_run=True),
        )
        self.assertEqual(rep.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        self.assertFalse(rep.all_132_gates_verified)

    def test_74_real_chained_132gate_offline_and_dry_run(self) -> None:
        off = evaluate_132gate_preflight(DEFAULT_REPO_ROOT)
        self.assertGreaterEqual(off.summary["verified_gates"], 129)
        self.assertEqual(off.summary["verified_gates"], 129)
        self.assertTrue(off.offline_129_gates_verified)
        self.assertFalse(off.overall_ready_for_hardware_attach)
        self.assertEqual(off.raw_firmware_bytes_leaked, 0)

        dry = evaluate_132gate_preflight(
            DEFAULT_REPO_ROOT, simulate_bench_dry_run=True
        )
        self.assertGreaterEqual(dry.summary["verified_gates"], 132)
        self.assertEqual(dry.summary["verified_gates"], 132)
        self.assertTrue(dry.all_132_gates_verified)
        self.assertFalse(dry.overall_ready_for_hardware_attach)
        self.assertFalse(dry.persistent_emmc_writes_authorized)
        self.assertFalse(dry.cross_model_flash_authorized)

    def test_75_real_chained_132gate_clean_room_forced_offline_and_dry_run(self) -> None:
        off = evaluate_132gate_preflight(DEFAULT_REPO_ROOT, force_clean_room=True)
        self.assertEqual(off.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(off.summary["verified_gates"], 129)
        self.assertTrue(off.offline_129_gates_verified)

        dry = evaluate_132gate_preflight(
            DEFAULT_REPO_ROOT, force_clean_room=True, simulate_bench_dry_run=True
        )
        self.assertEqual(dry.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(dry.summary["verified_gates"], 132)
        self.assertTrue(dry.all_132_gates_verified)

    def test_76_cli_help_python314_percent_escaping(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            with self.assertRaises(SystemExit) as ctx:
                cli_main(["--help"])
        self.assertEqual(ctx.exception.code, 0)
        out = buf.getvalue()
        self.assertIn("verify-dial-customize-mydial-fn-guard", out)
        self.assertIn("verify-liveview-grid-lut-embed-guard", out)
        self.assertIn("verify-132-gates", out)

    def test_77_cli_g131_g132_summary_json_and_text(self) -> None:
        for cmd in (
            "verify-dial-customize-mydial-fn-guard",
            "verify-liveview-grid-lut-embed-guard",
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

    def test_78_cli_verify_132_gates_subprocess_uses_sys_executable(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONPATH"] = str(DEFAULT_REPO_ROOT / "outputs" / "fx3-safety")
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "fx3_safety",
                "verify-132-gates",
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
            payload["status"], "VERIFIED_ALL_132_GATES_DRY_RUN_SIMULATED_BACKUP"
        )
        self.assertEqual(payload["summary"]["verified_gates"], 132)
        self.assertEqual(payload["g131_status"], STATUS_VERIFIED_G131)
        self.assertEqual(payload["g132_status"], STATUS_VERIFIED_G132)

    def test_79_cli_verify_132_gates_clean_room_subprocess_uses_sys_executable(self) -> None:
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
                "verify-132-gates",
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
            payload["status"], "VERIFIED_129_OF_132_AWAITING_PHYSICAL_TIER0"
        )
        self.assertEqual(payload["summary"]["verified_gates"], 129)

    def test_80_cli_verify_132_gates_offline_text_mode(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cli_main(["verify-132-gates", "--clean-room"])
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("VERIFIED_129_OF_132_AWAITING_PHYSICAL_TIER0", out)
        self.assertIn("verified=129/132", out)
        self.assertIn("overall_ready_for_hardware_attach=False", out)

    def test_81_cli_aliases_work_cleanly(self) -> None:
        for alias in (
            "verify-g131-dial-customize-mydial-fn",
            "verify-g132-liveview-grid-lut-embed",
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = cli_main([alias, "--clean-room", "--summary", "--json"])
            self.assertEqual(rc, 0)
            self.assertTrue(json.loads(buf.getvalue())["valid"])

    def test_82_module_direct_main_entrypoint(self) -> None:
        for gate_flag in ("g131", "g132", "132"):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = module_main(
                    ["--gate", gate_flag, "--clean-room", "--summary", "--json"]
                )
            self.assertEqual(rc, 0)
            data = json.loads(buf.getvalue())
            self.assertEqual(
                data["status"] if gate_flag != "132" else data["g131_status"],
                STATUS_VERIFIED_G131
                if gate_flag in ("g131", "132")
                else STATUS_VERIFIED_G132,
            )

    def test_83_g131_normalization_aliases_and_resolvers(self) -> None:
        s = resolve_fx3_dial_customize_mydial_fn_state(
            shoot_mode="S&Q Motion",
            requested_av_tv_rotate="reverse",
            requested_function_ring="APS-C S35 FF",
            requested_lock_operation_parts="dial+wheel",
            requested_my_dial_recall_mode="during hold",
            requested_physical_dial="control wheel",
        )
        self.assertTrue(s["valid"])
        self.assertEqual(s["shoot_mode"], SHOOT_MODE_SQ_PHASE303)
        self.assertEqual(s["effective_av_tv_rotate"], AV_TV_ROTATE_REVERSE_G131)
        self.assertEqual(s["effective_function_ring"], FUNCTION_RING_APSC_S35_FF_G131)
        self.assertEqual(
            s["effective_lock_operation_parts"], LOCK_OPERATION_PARTS_DIAL_WHEEL_G131
        )
        self.assertEqual(s["effective_my_dial_recall_mode"], MY_DIAL_RECALL_HOLD_G131)
        self.assertEqual(s["requested_physical_dial"], FX3_PHYSICAL_DIAL_WHEEL_G131)

    def test_84_g132_normalization_aliases_and_resolvers(self) -> None:
        s = resolve_fx3_liveview_grid_lut_embed_state(
            requested_live_view_display="effect_off",
            requested_exposure_effect="ambient only",
            requested_frame_rate_low_limit="on",
            requested_grid_line_display="on",
            requested_grid_line_type="diag+square",
            requested_hdmi_info_display="off",
            card_type="cfa",
            requested_select_lut="r709",
            requested_embed_lut_file="off",
            requested_target_slot="slot b",
        )
        self.assertTrue(s["valid"])
        self.assertEqual(s["effective_live_view_display"], LIVE_VIEW_SETTING_EFFECT_OFF_G132)
        self.assertEqual(s["effective_exposure_effect"], EXPOSURE_EFFECT_SET_ONLY_G132)
        self.assertEqual(s["effective_frame_rate_low_limit"], FRAME_RATE_LOW_LIMIT_ON_G132)
        self.assertEqual(s["effective_grid_line_display"], GRID_LINE_DISPLAY_ON_G132)
        self.assertEqual(s["effective_grid_line_type"], GRID_LINE_TYPE_DIAG_SQUARE_G132)
        self.assertEqual(s["effective_hdmi_info_display"], HDMI_INFO_DISPLAY_OFF_G132)
        self.assertEqual(s["card_type"], CARD_TYPE_CFEXPRESS_A_G132)
        self.assertEqual(s["effective_select_lut"], SELECT_LUT_709_800_G132)
        self.assertEqual(s["effective_embed_lut_file"], EMBED_LUT_OFF_G132)
        self.assertEqual(s["requested_target_slot"], MEDIA_SLOT_2_PHASE303)

    def test_85_g131_and_g132_bool_body_id_rejected(self) -> None:
        r1 = verify_dial_customize_mydial_fn_guard(
            body_model_id=True,  # type: ignore[arg-type]
        )
        r2 = verify_liveview_grid_lut_embed_guard(
            body_model_id=False,  # type: ignore[arg-type]
        )
        self.assertFalse(r1.valid)
        self.assertEqual(r1.status, STATUS_BLOCKED_G131_TELEMETRY_INVALID)
        self.assertFalse(r2.valid)
        self.assertEqual(r2.status, STATUS_BLOCKED_G132_TELEMETRY_INVALID)

    def test_86_g131_mydial_invalid_bank_and_delete_all_user_luts_safe(self) -> None:
        bad_bank = verify_dial_customize_mydial_fn_guard(
            requested_my_dial_bank=True,  # type: ignore[arg-type]
        )
        self.assertFalse(bad_bank.valid)
        self.assertEqual(bad_bank.status, STATUS_BLOCKED_G131_TELEMETRY_INVALID)

        safe_del = verify_liveview_grid_lut_embed_guard(
            requested_lut_or_rec_op=LUT_OP_DELETE_ALL_USER_LUTS_G132,
            requested_target_slot=MEDIA_SLOT_1_PHASE303,
            slot_1_contains_tier0_vault=True,
        )
        self.assertTrue(safe_del.valid)
        self.assertFalse(safe_del.slot1_vault_firewall_blocked)
        self.assertEqual(safe_del.slot1_data_sector_writes, 0)


if __name__ == "__main__":
    unittest.main()
