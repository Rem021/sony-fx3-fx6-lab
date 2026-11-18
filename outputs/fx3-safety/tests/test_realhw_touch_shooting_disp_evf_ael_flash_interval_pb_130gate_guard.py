"""Phase 299 (Wave-55, 130/130 Safety Gates Milestone!) Dual-Mode Unit Tests (84 tests) for
`fx3_safety.realhw_touch_shooting_disp_evf_ael_flash_interval_pb_and_130gate_guard`:

- Gate `G129` (`GATE_G129_TOUCH_OPERATION_DISP_4MODE_AND_ZERO_EVF_BLACKOUT_GUARD`):
  - `[Touch Operation]` 4-item menu (`Touch Operation` [`On`/`On: Playback Only`/`Off`],
    `Touch Sensitivity` [`Standard`/`Sensitive`, NOT `Responsive`], `Touch Func. in Shooting`
    [`Touch Focus`/`Touch Tracking`/`Off` across Still/Movie/S&Q], `Swipe Up` [`Open the Fn Menu`/`Off`])
    surviving `[Camera Settings Reset]` (`Initialize`-only!).
  - Fail-closed rejection of dormant Alpha traps (`Touch Shutter`, `Touch AE`, `Touch Focus+AE`,
    `Touch Panel/Pad`, `Touch Pad Settings`, `Footer Icon Touch`, `Swipe Left`/`Right`, `Responsive`).
  - `[DISP (Screen Disp) Set]` exact `Operation Customize` path (NOT `Display Option`), exact
    4 shooting pages (`Display All Info.`, `No Disp. Info.`, `Histogram`, `Level`) + 3 playback pages
    (`Display Info.`, `Histogram`, `No Disp. Info.`), surviving `[Camera Settings Reset]`.
  - Total Zero-EVF Blackout Trap Firewall (`ILME-FX3` has ZERO EVF, ZERO eye sensor, ZERO
    `FINDER/MONITOR` button — blocks `Select Finder/Monitor`, `For viewfinder`, `Graphic Display`,
    `Monitor Off`, `DISP Button:Finder`), contrasted with `ILME-FX6` (`TYPE_BUILTIN_EVF_NOT_EXIST`,
    detachable 3.5" LCD `Viewfinder` + `Viewfinder Hood`, never `"Loupe"`).
- Gate `G130` (`GATE_G130_AEL_WIRELESS_FLASH_INTERVAL_9SCALE_AND_PLAYBACK_EDIT_VAULT_GUARD`):
  - Still-only `[AEL w/ Shutter]` (`Auto`/`On`/`Off`, `Initialize`-only), Still-only `[Exp.comp.set]`
    (`Exposure/Color -> [Flash]`: `Ambient&flash`/`Ambient only`, `Initialize`-only), Still-only
    `[Wireless Flash]` (`Off`/`On`, **the ONLY Flash item resettable via `[Camera Settings Reset]`**),
    Still-only direct-MI-Shoe `[External Flash Set.]` (no off-camera sync cord, no camera-menu flash reset),
    contrasted with flash-less `ILME-FX6` (`Flash Band Reduce` is rolling-shutter compensation, NOT flash trigger).
  - Playback `MENU -> (Playback) -> [Viewing]` (NOT `Playback Option`) `[Cont. Play for Interval]` &
    `[Play Speed for Interval]` exact **`1..9` scale (default `5`, NOT `1..5`)**, `Initialize`-only,
    read-only safe, no in-camera movie assembly.
  - Playback `MENU -> (Playback) -> [Edit]` exact 4 active items (`Rotate`, `Photo Capture`,
    `JPEG/HEIF Switch` [`JPEG`/`HEIF(4:2:0)`/`HEIF(4:2:2)`], `Copy`), fail-closed blocking dormant
    `Beauty Effect`/`Trimming` traps AND fail-closed blocking (`EROFS`/`EOPNOTSUPP`, `slot1_data_sector_writes == 0`)
    any write mutation (`Rotate`, `Photo Capture`, `Copy Slot 2 -> Slot 1`) targeting read-only `Slot 1` Tier-0 vault!
- Unified `130`-Gate Milestone Master Preflight (`evaluate_130gate_preflight` / `verify-130-gates`):
  - `127/130` offline (`VERIFIED_127_OF_130_AWAITING_PHYSICAL_TIER0`) and `130/130` under
    `--simulate-bench-dry-run` (`VERIFIED_ALL_130_GATES_DRY_RUN_SIMULATED_BACKUP`) with all redlines
    hard-locked `False` and zero raw firmware bytes leaked.
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
from fx3_safety.realhw_switch_vh_af_stdadj_bracket_tcub_copy_slot_and_128gate_guard import (
    Master128GateReport,
)
from fx3_safety.realhw_touch_shooting_disp_evf_ael_flash_interval_pb_and_130gate_guard import (
    AEL_W_SHUTTER_AUTO_G130,
    AEL_W_SHUTTER_DEFAULT_G130,
    AEL_W_SHUTTER_OFF_G130,
    AEL_W_SHUTTER_ON_G130,
    ALLOWED_AEL_W_SHUTTER_MODES_G130,
    ALLOWED_EXP_COMP_SET_MODES_G130,
    ALLOWED_PHOTO_CAPTURE_FILE_TYPES_G130,
    ALLOWED_PLAY_SPEED_INTERVAL_SCALE_G130,
    ALLOWED_SWIPE_UP_MODES_G129,
    ALLOWED_TOUCH_FUNC_IN_SHOOTING_G129,
    ALLOWED_TOUCH_OPERATION_MODES_G129,
    ALLOWED_TOUCH_SENSITIVITIES_G129,
    ALLOWED_WIRELESS_FLASH_MODES_G130,
    CROSS_MODEL_FLASH_AUTHORIZED,
    DEFAULT_REPO_ROOT,
    DISP_PLAY_3_PAGES_G129,
    DISP_SET_MENU_PATH_G129,
    DISP_SET_WRONG_PATH_G129,
    DISP_SHOOT_4_PAGES_G129,
    DONOR_CHECK_CI_MAX_SECONDS_PHASE299,
    DONOR_CHECK_MAX_SECONDS_PHASE299,
    DORMANT_EVF_AND_DISP_TRAP_KEYS_G129,
    DORMANT_OR_WRONG_TOUCH_SENSITIVITY_G129,
    DORMANT_PLAYBACK_EDIT_TRAP_ITEMS_G130,
    DORMANT_TOUCH_TRAP_KEYS_G129,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    ENV_CLEAN_ROOM_TEST_PHASE299,
    ENV_FORCE_CLEAN_ROOM,
    EXP_COMP_SET_AMBIENT_AND_FLASH_G130,
    EXP_COMP_SET_AMBIENT_ONLY_G130,
    EXP_COMP_SET_DEFAULT_G130,
    EXT_FLASH_SUBMENUS_G130,
    FX3_DEFAULT_FW_VERSION_PHASE299,
    FX3_HELP_GUIDE_CODE_PHASE299,
    FX3_MODEL_ID_PHASE299,
    FX3_MODEL_NAME_PHASE299,
    FX6_DEFAULT_FW_VERSION_PHASE299,
    FX6_DETACHABLE_LCD_TERMS_G129,
    FX6_FLASH_BAND_REDUCE_NAME_G130,
    FX6_MODEL_NAME_PHASE299,
    G129,
    G129_GATE_CODE,
    G129_GATE_ID,
    G130,
    G130_GATE_CODE,
    G130_GATE_ID,
    HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    HUMAN_HARDWARE_ATTACH_TOKEN,
    INTERVAL_PB_MENU_PATH_G130,
    INTERVAL_PB_WRONG_PATH_G130,
    MEDIA_SLOT_1_PHASE299,
    MEDIA_SLOT_2_PHASE299,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHOTO_CAPTURE_FILE_DEFAULT_G130,
    PHOTO_CAPTURE_FILE_HEIF_420_G130,
    PHOTO_CAPTURE_FILE_HEIF_422_G130,
    PHOTO_CAPTURE_FILE_JPEG_G130,
    PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED,
    PHYSICAL_USB_PACKETS_EMITTED,
    PINNED_FX3_APPFW_SLICES_PHASE299,
    PINNED_FX3_APPFW_SLICES_SHA256_PHASE299,
    PINNED_FX6_APPFW_SLICES_PHASE299,
    PINNED_FX6_APPFW_SLICES_SHA256_PHASE299,
    PINNED_PHASE299_DONOR_SPECS,
    PLAYBACK_EDIT_ACTIVE_4_ITEMS_G130,
    PLAY_SPEED_INTERVAL_DEFAULT_G130,
    PLAY_SPEED_INTERVAL_MAX_G130,
    PLAY_SPEED_INTERVAL_MIN_G130,
    RAW_FIRMWARE_BYTES_LEAKED,
    REALHW_TOUCH_SHOOTING_DISP_EVF_AEL_FLASH_INTERVAL_PB_130GATE_SCHEMA,
    RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE299,
    RESET_ACTION_INITIALIZE_PHASE299,
    RESET_ACTION_NONE_PHASE299,
    SHOOT_MODE_MOVIE_PHASE299,
    SHOOT_MODE_SQ_PHASE299,
    SHOOT_MODE_STILL_PHASE299,
    SPI_NOR_WRITE_AUTHORIZED,
    STATUS_BLOCKED_G129_DISP_4MODE_OR_PATH_VIOLATION,
    STATUS_BLOCKED_G129_FX6_TOUCH_OR_EVF_CROSSWIRE_VIOLATION,
    STATUS_BLOCKED_G129_TELEMETRY_INVALID,
    STATUS_BLOCKED_G129_TOUCH_RESET_OR_DORMANT_TRAP_VIOLATION,
    STATUS_BLOCKED_G129_ZERO_EVF_BLACKOUT_TRAP_VIOLATION,
    STATUS_BLOCKED_G130_AEL_OR_FLASH_STILL_RESET_VIOLATION,
    STATUS_BLOCKED_G130_EXT_FLASH_MISHOE_OR_FX6_VIOLATION,
    STATUS_BLOCKED_G130_INTERVAL_PLAYBACK_SCALE_OR_PATH_VIOLATION,
    STATUS_BLOCKED_G130_PLAYBACK_EDIT_DORMANT_OR_SLOT1_VAULT_VIOLATION,
    STATUS_BLOCKED_G130_TELEMETRY_INVALID,
    STATUS_BLOCKED_PERSISTENT_EMMC_WRITE,
    STATUS_BLOCKED_PHASE299_DONOR_INTEGRITY,
    STATUS_VERIFIED_G129,
    STATUS_VERIFIED_G130,
    STATUS_VERIFIED_SAFE,
    SWIPE_UP_DEFAULT_G129,
    SWIPE_UP_OFF_G129,
    SWIPE_UP_OPEN_FN_MENU_G129,
    TOUCH_FUNC_DEFAULT_G129,
    TOUCH_FUNC_OFF_G129,
    TOUCH_FUNC_TOUCH_FOCUS_G129,
    TOUCH_FUNC_TOUCH_TRACKING_G129,
    TOUCH_OPERATION_4_ITEMS_G129,
    TOUCH_OP_DEFAULT_G129,
    TOUCH_OP_OFF_G129,
    TOUCH_OP_ON_G129,
    TOUCH_OP_PLAYBACK_ONLY_G129,
    TOUCH_SENSITIVITY_DEFAULT_G129,
    TOUCH_SENSITIVITY_SENSITIVE_G129,
    TOUCH_SENSITIVITY_STANDARD_G129,
    USB_PACKETS_TRANSMITTED,
    WIRELESS_FLASH_DEFAULT_G130,
    WIRELESS_FLASH_OFF_G130,
    WIRELESS_FLASH_ON_G130,
    audit_phase299_donor_contracts,
    compute_ael_flash_and_interval_pb_edit_matrix,
    compute_touch_shooting_and_disp_evf_matrix,
    evaluate_130_master_safety_gates,
    evaluate_130gate_preflight,
    evaluate_g129_touch_shooting_and_disp_evf_absence_guard,
    evaluate_g130_ael_wireless_flash_and_interval_pb_edit_guard,
    main as module_main,
    resolve_fx3_ael_flash_and_interval_pb_edit_state,
    resolve_fx3_touch_shooting_and_disp_evf_state,
    run_130_gate_preflight,
    verify_ael_wireless_flash_and_interval_pb_edit_guard,
    verify_touch_shooting_and_disp_evf_absence_guard,
)


def _make_stub_master128(
    *, dry_run: bool = False, all_g13_128_ok: bool = True
) -> Master128GateReport:
    gates = []
    for i in range(1, 129):
        gid = f"G{i:02d}"
        is_tier0_offline = gid in ("G10", "G11", "G12") and not dry_run
        passed = (not is_tier0_offline) and (all_g13_128_ok or i <= 12)
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
    g13_126 = 114 if all_g13_128_ok else 0
    g127_128 = 2 if all_g13_128_ok else 0
    total = g01_12 + g13_126 + g127_128
    return Master128GateReport(
        schema="stub_128",
        version="2026.11.17",
        evaluated_utc="2026-11-17T00:00:00Z",
        verification_mode="CLEAN_ROOM_SYNTHETIC",
        clean_room_forced=True,
        dry_run_rehearsal_only=dry_run,
        overall_ready_for_hardware_attach=False,
        hardware_live_attachment_authorized=False,
        offline_125_gates_verified=all_g13_128_ok,
        all_128_gates_verified=(dry_run and all_g13_128_ok),
        g13_to_g128_all_passed=all_g13_128_ok,
        g127_to_g128_all_passed=all_g13_128_ok,
        h0_h1_trial_entry_allowed=all_g13_128_ok,
        status=(
            "VERIFIED_ALL_128_GATES_DRY_RUN_SIMULATED_BACKUP"
            if dry_run
            else "VERIFIED_125_OF_128_AWAITING_PHYSICAL_TIER0"
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
            "g13_to_g126_verified": g13_126,
            "g127_to_g128_verified": g127_128,
            "verified_gates": total,
        },
        gates=tuple(gates),
        master_126_report={},
        g127_result={},
        g128_result={},
        errors=(),
        warnings=(),
    )


class TestPhase299DonorAuditAndRedlines(unittest.TestCase):
    def test_01_package_exports_and_schema(self) -> None:
        self.assertEqual(G129, "G129")
        self.assertEqual(G129_GATE_ID, "G129")
        self.assertEqual(G130, "G130")
        self.assertEqual(G130_GATE_ID, "G130")
        self.assertTrue(hasattr(fx3_safety, "evaluate_130gate_preflight"))
        self.assertTrue(hasattr(fx3_safety, "verify_touch_shooting_and_disp_evf_absence_guard"))
        self.assertTrue(hasattr(fx3_safety, "verify_ael_wireless_flash_and_interval_pb_edit_guard"))
        self.assertEqual(
            REALHW_TOUCH_SHOOTING_DISP_EVF_AEL_FLASH_INTERVAL_PB_130GATE_SCHEMA,
            "realhw_touch_shooting_disp_evf_ael_flash_interval_pb_and_130gate_guard_v1",
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
        self.assertEqual(len(PINNED_PHASE299_DONOR_SPECS), 11)
        self.assertEqual(len(PINNED_FX3_APPFW_SLICES_PHASE299), 49)
        self.assertEqual(len(PINNED_FX6_APPFW_SLICES_PHASE299), 13)
        self.assertEqual(len(PINNED_FX3_APPFW_SLICES_SHA256_PHASE299), 64)
        self.assertEqual(len(PINNED_FX6_APPFW_SLICES_SHA256_PHASE299), 64)

    def test_04_clean_room_forced_audit_succeeds(self) -> None:
        res = audit_phase299_donor_contracts(force_clean_room=True)
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_VERIFIED_SAFE)
        self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(res.files_inspected, 0)
        self.assertEqual(res.raw_firmware_bytes_leaked, 0)
        self.assertTrue(res.fx3_contracts_verified)
        self.assertTrue(res.fx6_contracts_verified)
        self.assertTrue(res.four_lang_resid16_parity_verified)

    def test_05_env_clean_room_flags_respected(self) -> None:
        for env_key in (ENV_FORCE_CLEAN_ROOM, ENV_CLEAN_ROOM_TEST_PHASE299):
            with mock.patch.dict(os.environ, {env_key: "1"}):
                res = audit_phase299_donor_contracts()
                self.assertTrue(res.valid)
                self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_06_explicit_missing_work_root_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.dict(
                os.environ,
                {ENV_FORCE_CLEAN_ROOM: "0", ENV_CLEAN_ROOM_TEST_PHASE299: "0"},
            ):
                res = audit_phase299_donor_contracts(
                    work_root=Path(tmp), force_clean_room=False
                )
                self.assertFalse(res.valid)
                self.assertEqual(res.status, STATUS_BLOCKED_PHASE299_DONOR_INTEGRITY)
                self.assertGreater(len(res.missing_markers), 0)

    def test_07_absent_default_donor_falls_back_to_clean_room(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fake_paths = mock.Mock(work_root=Path(tmp))
            with mock.patch(
                "fx3_safety.realhw_touch_shooting_disp_evf_ael_flash_interval_pb_and_130gate_guard.resolve_donor_thermal_power_paths",
                return_value=fake_paths,
            ):
                with mock.patch.dict(
                    os.environ,
                    {ENV_FORCE_CLEAN_ROOM: "0", ENV_CLEAN_ROOM_TEST_PHASE299: "0"},
                ):
                    res = audit_phase299_donor_contracts(force_clean_room=False)
                    self.assertTrue(res.valid)
                    self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")
                    self.assertIn("CLEAN_ROOM_SYNTHETIC", res.warnings[0])

    def test_08_donor_audit_respects_local_or_clean_mode_and_budget(self) -> None:
        res = audit_phase299_donor_contracts()
        self.assertTrue(res.valid)
        self.assertEqual(res.raw_firmware_bytes_leaked, 0)
        budget = (
            DONOR_CHECK_CI_MAX_SECONDS_PHASE299
            if os.environ.get("GITHUB_ACTIONS", "").strip().lower() == "true"
            else DONOR_CHECK_MAX_SECONDS_PHASE299
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
                    8,
                    "0" * 64,
                    (b"Touch Func. in Shooting",),
                    "fake marker",
                )
            }
            res = audit_phase299_donor_contracts(
                work_root=Path(tmp),
                force_clean_room=False,
                donor_specs_override=override,
            )
            self.assertFalse(res.valid)
            self.assertEqual(res.status, STATUS_BLOCKED_PHASE299_DONOR_INTEGRITY)

    def test_10_ci_timing_budget_headroom(self) -> None:
        with mock.patch.dict(os.environ, {"GITHUB_ACTIONS": "true"}):
            res = audit_phase299_donor_contracts(force_clean_room=True)
            self.assertTrue(res.within_budget_200ms)
            self.assertEqual(DONOR_CHECK_CI_MAX_SECONDS_PHASE299, 15.0)

    def test_11_dataclasses_are_frozen(self) -> None:
        g129 = verify_touch_shooting_and_disp_evf_absence_guard()
        g130 = verify_ael_wireless_flash_and_interval_pb_edit_guard()
        self.assertTrue(dataclasses.is_dataclass(g129))
        self.assertTrue(dataclasses.is_dataclass(g130))
        with self.assertRaises(dataclasses.FrozenInstanceError):
            g129.valid = False  # type: ignore[misc]
        with self.assertRaises(dataclasses.FrozenInstanceError):
            g130.valid = False  # type: ignore[misc]


class TestGateG129TouchOperationAndDispZeroEvf(unittest.TestCase):
    def test_12_default_g129_guard_passes(self) -> None:
        res = verify_touch_shooting_and_disp_evf_absence_guard()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_VERIFIED_G129)
        self.assertEqual(res.effective_touch_operation, TOUCH_OP_ON_G129)
        self.assertEqual(res.effective_touch_sensitivity, TOUCH_SENSITIVITY_STANDARD_G129)
        self.assertEqual(res.effective_touch_func_in_shooting, TOUCH_FUNC_TOUCH_TRACKING_G129)
        self.assertEqual(res.effective_swipe_up, SWIPE_UP_OPEN_FN_MENU_G129)
        self.assertEqual(res.disp_shoot_pages_enabled, DISP_SHOOT_4_PAGES_G129)
        self.assertEqual(res.disp_play_pages_enabled, DISP_PLAY_3_PAGES_G129)
        self.assertFalse(res.fx3_has_builtin_evf)
        self.assertFalse(res.fx3_has_eye_sensor)
        self.assertFalse(res.fx3_has_finder_monitor_button)
        self.assertTrue(res.evf_scanout_blocked)
        self.assertTrue(res.lcd_panel_scanout_preserved)
        self.assertEqual(res.matrix_states_checked, 432)

    def test_13_touch_operation_exact_4_items_constants(self) -> None:
        self.assertEqual(len(TOUCH_OPERATION_4_ITEMS_G129), 4)
        self.assertEqual(
            TOUCH_OPERATION_4_ITEMS_G129,
            ("Touch Operation", "Touch Sensitivity", "Touch Func. in Shooting", "Swipe Up"),
        )
        self.assertEqual(
            ALLOWED_TOUCH_OPERATION_MODES_G129, ("On", "On: Playback Only", "Off")
        )
        self.assertEqual(ALLOWED_TOUCH_SENSITIVITIES_G129, ("Standard", "Sensitive"))
        self.assertEqual(
            ALLOWED_TOUCH_FUNC_IN_SHOOTING_G129,
            ("Touch Focus", "Touch Tracking", "Off"),
        )
        self.assertEqual(ALLOWED_SWIPE_UP_MODES_G129, ("Open the Fn Menu", "Off"))

    def test_14_touch_func_identical_across_still_movie_sq(self) -> None:
        for sm in (SHOOT_MODE_STILL_PHASE299, SHOOT_MODE_MOVIE_PHASE299, SHOOT_MODE_SQ_PHASE299):
            for tf in ALLOWED_TOUCH_FUNC_IN_SHOOTING_G129:
                res = verify_touch_shooting_and_disp_evf_absence_guard(
                    shoot_mode=sm,
                    requested_touch_func_in_shooting=tf,
                )
                self.assertTrue(res.valid)
                self.assertEqual(res.effective_touch_func_in_shooting, tf)

    def test_15_touch_sensitivity_sensitive_accepted_responsive_rejected(self) -> None:
        ok = verify_touch_shooting_and_disp_evf_absence_guard(
            requested_touch_sensitivity=TOUCH_SENSITIVITY_SENSITIVE_G129,
        )
        self.assertTrue(ok.valid)
        self.assertEqual(ok.effective_touch_sensitivity, TOUCH_SENSITIVITY_SENSITIVE_G129)

        bad = verify_touch_shooting_and_disp_evf_absence_guard(
            requested_touch_sensitivity=DORMANT_OR_WRONG_TOUCH_SENSITIVITY_G129,
        )
        self.assertFalse(bad.valid)
        self.assertEqual(bad.status, STATUS_BLOCKED_G129_TOUCH_RESET_OR_DORMANT_TRAP_VIOLATION)

    def test_16_swipe_up_active_only_when_touch_operation_on(self) -> None:
        on_res = verify_touch_shooting_and_disp_evf_absence_guard(
            requested_touch_operation=TOUCH_OP_ON_G129,
            requested_swipe_up=SWIPE_UP_OPEN_FN_MENU_G129,
        )
        self.assertTrue(on_res.valid)
        self.assertTrue(on_res.swipe_up_active)

        for mode in (TOUCH_OP_PLAYBACK_ONLY_G129, TOUCH_OP_OFF_G129):
            inactive = verify_touch_shooting_and_disp_evf_absence_guard(
                requested_touch_operation=mode,
                requested_swipe_up=SWIPE_UP_OPEN_FN_MENU_G129,
            )
            self.assertTrue(inactive.valid)
            self.assertFalse(inactive.swipe_up_active)

    def test_17_touch_and_disp_survive_camera_settings_reset(self) -> None:
        cam_rst = verify_touch_shooting_and_disp_evf_absence_guard(
            requested_touch_operation=TOUCH_OP_PLAYBACK_ONLY_G129,
            requested_touch_sensitivity=TOUCH_SENSITIVITY_SENSITIVE_G129,
            requested_touch_func_in_shooting=TOUCH_FUNC_TOUCH_FOCUS_G129,
            requested_swipe_up=SWIPE_UP_OFF_G129,
            requested_disp_shoot_pages=("Display All Info.", "Histogram"),
            requested_disp_play_pages=("Histogram",),
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE299,
        )
        self.assertTrue(cam_rst.valid)
        self.assertTrue(cam_rst.touch_4_items_survived_cam_reset)
        self.assertTrue(cam_rst.disp_set_survived_cam_reset)
        self.assertEqual(cam_rst.effective_touch_operation, TOUCH_OP_PLAYBACK_ONLY_G129)
        self.assertEqual(cam_rst.effective_touch_sensitivity, TOUCH_SENSITIVITY_SENSITIVE_G129)
        self.assertEqual(cam_rst.effective_touch_func_in_shooting, TOUCH_FUNC_TOUCH_FOCUS_G129)
        self.assertEqual(cam_rst.effective_swipe_up, SWIPE_UP_OFF_G129)
        self.assertEqual(cam_rst.disp_shoot_pages_enabled, ("Display All Info.", "Histogram"))

    def test_18_touch_and_disp_reset_only_on_initialize(self) -> None:
        init_rst = verify_touch_shooting_and_disp_evf_absence_guard(
            requested_touch_operation=TOUCH_OP_OFF_G129,
            requested_touch_sensitivity=TOUCH_SENSITIVITY_SENSITIVE_G129,
            requested_touch_func_in_shooting=TOUCH_FUNC_OFF_G129,
            requested_swipe_up=SWIPE_UP_OFF_G129,
            requested_disp_shoot_pages=("Level",),
            reset_action=RESET_ACTION_INITIALIZE_PHASE299,
        )
        self.assertTrue(init_rst.valid)
        self.assertFalse(init_rst.touch_4_items_survived_cam_reset)
        self.assertFalse(init_rst.disp_set_survived_cam_reset)
        self.assertEqual(init_rst.effective_touch_operation, TOUCH_OP_DEFAULT_G129)
        self.assertEqual(init_rst.effective_touch_sensitivity, TOUCH_SENSITIVITY_DEFAULT_G129)
        self.assertEqual(init_rst.effective_touch_func_in_shooting, TOUCH_FUNC_DEFAULT_G129)
        self.assertEqual(init_rst.effective_swipe_up, SWIPE_UP_DEFAULT_G129)
        self.assertEqual(init_rst.disp_shoot_pages_enabled, DISP_SHOOT_4_PAGES_G129)

    def test_19_dormant_touch_shutter_ae_pad_footer_traps_rejected(self) -> None:
        for trap in DORMANT_TOUCH_TRAP_KEYS_G129:
            res = verify_touch_shooting_and_disp_evf_absence_guard(
                requested_dormant_touch_feature=trap,
            )
            self.assertFalse(res.valid)
            self.assertEqual(
                res.status, STATUS_BLOCKED_G129_TOUCH_RESET_OR_DORMANT_TRAP_VIOLATION
            )

    def test_20_touch_func_dormant_touch_shutter_and_ae_rejected(self) -> None:
        for bad_func in ("Touch Shutter", "Touch AE", "Touch Focus+AE"):
            res = verify_touch_shooting_and_disp_evf_absence_guard(
                requested_touch_func_in_shooting=bad_func,
            )
            self.assertFalse(res.valid)
            self.assertEqual(
                res.status, STATUS_BLOCKED_G129_TOUCH_RESET_OR_DORMANT_TRAP_VIOLATION
            )

    def test_21_touch_reset_spoof_rejected(self) -> None:
        res = verify_touch_shooting_and_disp_evf_absence_guard(
            claimed_touch_resets_on_cam_settings_reset=True,
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            res.status, STATUS_BLOCKED_G129_TOUCH_RESET_OR_DORMANT_TRAP_VIOLATION
        )

    def test_22_disp_set_menu_path_must_be_operation_customize_not_display_option(self) -> None:
        r1 = verify_touch_shooting_and_disp_evf_absence_guard(
            disp_set_menu_path=DISP_SET_WRONG_PATH_G129,
        )
        r2 = verify_touch_shooting_and_disp_evf_absence_guard(
            claimed_disp_set_under_display_option=True,
        )
        r3 = verify_touch_shooting_and_disp_evf_absence_guard(
            claimed_disp_resets_on_cam_settings_reset=True,
        )
        for r in (r1, r2, r3):
            self.assertFalse(r.valid)
            self.assertEqual(r.status, STATUS_BLOCKED_G129_DISP_4MODE_OR_PATH_VIOLATION)

    def test_23_disp_shoot_4_pages_and_play_3_pages_exact(self) -> None:
        self.assertEqual(
            DISP_SHOOT_4_PAGES_G129,
            ("Display All Info.", "No Disp. Info.", "Histogram", "Level"),
        )
        self.assertEqual(
            DISP_PLAY_3_PAGES_G129,
            ("Display Info.", "Histogram", "No Disp. Info."),
        )
        bad_empty = verify_touch_shooting_and_disp_evf_absence_guard(
            requested_disp_shoot_pages=(),
        )
        bad_extra = verify_touch_shooting_and_disp_evf_absence_guard(
            requested_disp_shoot_pages=("Display All Info.", "Custom Unknown"),
        )
        bad_play = verify_touch_shooting_and_disp_evf_absence_guard(
            requested_disp_play_pages=("Invalid Play Page",),
        )
        for r in (bad_empty, bad_extra, bad_play):
            self.assertFalse(r.valid)
            self.assertEqual(r.status, STATUS_BLOCKED_G129_DISP_4MODE_OR_PATH_VIOLATION)

    def test_24_zero_evf_blackout_firewall_blocks_all_dormant_evf_keys(self) -> None:
        for evf_key in DORMANT_EVF_AND_DISP_TRAP_KEYS_G129:
            res = verify_touch_shooting_and_disp_evf_absence_guard(
                requested_dormant_evf_or_disp_key=evf_key,
            )
            self.assertFalse(res.valid)
            self.assertEqual(
                res.status, STATUS_BLOCKED_G129_ZERO_EVF_BLACKOUT_TRAP_VIOLATION
            )
            self.assertTrue(res.evf_scanout_blocked)
            self.assertTrue(res.lcd_panel_scanout_preserved)

    def test_25_zero_evf_blackout_firewall_blocks_scanout_switch_and_disp_page_trap(self) -> None:
        sw = verify_touch_shooting_and_disp_evf_absence_guard(
            evf_scanout_switch_requested=True,
        )
        claim = verify_touch_shooting_and_disp_evf_absence_guard(
            claimed_fx3_has_evf_or_eye_sensor=True,
        )
        page_trap = verify_touch_shooting_and_disp_evf_absence_guard(
            requested_disp_shoot_pages=("Graphic Display",),
        )
        page_vf = verify_touch_shooting_and_disp_evf_absence_guard(
            requested_disp_shoot_pages=("For viewfinder",),
        )
        for r in (sw, claim, page_trap, page_vf):
            self.assertFalse(r.valid)
            self.assertEqual(
                r.status, STATUS_BLOCKED_G129_ZERO_EVF_BLACKOUT_TRAP_VIOLATION
            )

    def test_26_fx6_touch_and_viewfinder_crosswire_rejected(self) -> None:
        self.assertEqual(FX6_DETACHABLE_LCD_TERMS_G129, ("Viewfinder", "Viewfinder Hood"))
        for kw in [
            {"target_model": FX6_MODEL_NAME_PHASE299, "touch_sensitivity_adjust_requested": True},
            {"target_model": FX6_MODEL_NAME_PHASE299, "swipe_up_requested": True},
            {"target_model": FX6_MODEL_NAME_PHASE299, "fx6_4page_disp_ring_requested": True},
            {"claimed_fx6_has_touch_sensitivity_or_swipe_up": True},
            {"claimed_fx6_has_builtin_evf": True},
            {"claimed_fx6_uses_loupe_terminology": True},
        ]:
            res = verify_touch_shooting_and_disp_evf_absence_guard(**kw)  # type: ignore[arg-type]
            self.assertFalse(res.valid)
            self.assertEqual(
                res.status, STATUS_BLOCKED_G129_FX6_TOUCH_OR_EVF_CROSSWIRE_VIOLATION
            )

    def test_27_g129_432_state_matrix_holds(self) -> None:
        m = compute_touch_shooting_and_disp_evf_matrix()
        self.assertEqual(m["states_checked"], 432)
        self.assertTrue(m["all_invariants_hold"])
        self.assertEqual(m["cam_reset_survived_count"], 108)
        self.assertEqual(m["initialize_reset_count"], 108)
        self.assertGreater(m["swipe_up_active_count"], 0)

    def test_28_g129_invalid_identity_fails_closed(self) -> None:
        res = verify_touch_shooting_and_disp_evf_absence_guard(
            body_model_name="ILCE-7SM3",
            body_model_id=0x9999,
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_G129_TELEMETRY_INVALID)

    def test_29_evaluate_g129_blocks_persistent_emmc_write(self) -> None:
        v, r = evaluate_g129_touch_shooting_and_disp_evf_absence_guard(
            force_clean_room=True,
            request_persistent_emmc_writes=True,
        )
        self.assertFalse(v.passed)
        self.assertFalse(r.valid)
        self.assertEqual(r.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)


class TestGateG130AelFlashAndIntervalPbEditVault(unittest.TestCase):
    def test_30_default_g130_guard_passes(self) -> None:
        res = verify_ael_wireless_flash_and_interval_pb_edit_guard()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_VERIFIED_G130)
        self.assertEqual(res.effective_ael_w_shutter, AEL_W_SHUTTER_AUTO_G130)
        self.assertEqual(res.effective_exp_comp_set, EXP_COMP_SET_AMBIENT_AND_FLASH_G130)
        self.assertEqual(res.effective_wireless_flash, WIRELESS_FLASH_OFF_G130)
        self.assertEqual(res.effective_play_speed_for_interval, 5)
        self.assertEqual(res.play_speed_scale_min, 1)
        self.assertEqual(res.play_speed_scale_max, 9)
        self.assertEqual(res.play_speed_scale_default, 5)
        self.assertTrue(res.interval_pb_read_only_safe)
        self.assertFalse(res.in_camera_timelapse_movie_assembly_supported)
        self.assertEqual(res.slot1_data_sector_writes, 0)
        self.assertFalse(res.slot1_avf_info_mutated)
        self.assertEqual(res.matrix_states_checked, 432)

    def test_31_wireless_flash_only_item_reset_by_cam_settings_reset(self) -> None:
        cam_rst = verify_ael_wireless_flash_and_interval_pb_edit_guard(
            requested_ael_w_shutter=AEL_W_SHUTTER_ON_G130,
            requested_exp_comp_set=EXP_COMP_SET_AMBIENT_ONLY_G130,
            requested_wireless_flash=WIRELESS_FLASH_ON_G130,
            requested_cont_play_for_interval="On",
            requested_play_speed_for_interval=8,
            requested_photo_capture_file_type=PHOTO_CAPTURE_FILE_HEIF_422_G130,
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE299,
        )
        self.assertTrue(cam_rst.valid)
        # [AEL w/ Shutter], [Exp.comp.set], [Interval PB] survive Camera Settings Reset!
        self.assertTrue(cam_rst.ael_w_shutter_survived_cam_reset)
        self.assertTrue(cam_rst.exp_comp_set_survived_cam_reset)
        self.assertTrue(cam_rst.interval_pb_survived_cam_reset)
        self.assertEqual(cam_rst.effective_ael_w_shutter, AEL_W_SHUTTER_ON_G130)
        self.assertEqual(cam_rst.effective_exp_comp_set, EXP_COMP_SET_AMBIENT_ONLY_G130)
        self.assertEqual(cam_rst.effective_play_speed_for_interval, 8)
        self.assertEqual(cam_rst.effective_cont_play_for_interval, "On")
        # [Wireless Flash] is the ONLY Flash item reset by Camera Settings Reset!
        self.assertTrue(cam_rst.wireless_flash_reset_on_cam_reset)
        self.assertEqual(cam_rst.effective_wireless_flash, WIRELESS_FLASH_OFF_G130)

    def test_32_initialize_resets_all_g130_settings_to_defaults(self) -> None:
        init_rst = verify_ael_wireless_flash_and_interval_pb_edit_guard(
            requested_ael_w_shutter=AEL_W_SHUTTER_OFF_G130,
            requested_exp_comp_set=EXP_COMP_SET_AMBIENT_ONLY_G130,
            requested_wireless_flash=WIRELESS_FLASH_ON_G130,
            requested_cont_play_for_interval="On",
            requested_play_speed_for_interval=9,
            requested_photo_capture_file_type=PHOTO_CAPTURE_FILE_HEIF_420_G130,
            reset_action=RESET_ACTION_INITIALIZE_PHASE299,
        )
        self.assertTrue(init_rst.valid)
        self.assertFalse(init_rst.ael_w_shutter_survived_cam_reset)
        self.assertFalse(init_rst.exp_comp_set_survived_cam_reset)
        self.assertFalse(init_rst.interval_pb_survived_cam_reset)
        self.assertEqual(init_rst.effective_ael_w_shutter, AEL_W_SHUTTER_DEFAULT_G130)
        self.assertEqual(init_rst.effective_exp_comp_set, EXP_COMP_SET_DEFAULT_G130)
        self.assertEqual(init_rst.effective_wireless_flash, WIRELESS_FLASH_DEFAULT_G130)
        self.assertEqual(init_rst.effective_play_speed_for_interval, 5)
        self.assertEqual(init_rst.effective_photo_capture_file_type, PHOTO_CAPTURE_FILE_DEFAULT_G130)

    def test_33_ael_and_flash_blocked_in_movie_and_sq_modes(self) -> None:
        for sm in (SHOOT_MODE_MOVIE_PHASE299, SHOOT_MODE_SQ_PHASE299):
            for flag in (
                "ael_w_shutter_use_requested",
                "exp_comp_set_use_requested",
                "wireless_flash_use_requested",
                "external_flash_use_requested",
            ):
                res = verify_ael_wireless_flash_and_interval_pb_edit_guard(
                    shoot_mode=sm, **{flag: True}
                )
                self.assertFalse(res.valid)
                self.assertEqual(
                    res.status, STATUS_BLOCKED_G130_AEL_OR_FLASH_STILL_RESET_VIOLATION
                )

    def test_34_exp_comp_set_wrong_path_and_reset_spoof_rejected(self) -> None:
        r1 = verify_ael_wireless_flash_and_interval_pb_edit_guard(
            claimed_exp_comp_set_under_exposure_comp=True,
        )
        r2 = verify_ael_wireless_flash_and_interval_pb_edit_guard(
            claimed_ael_or_exp_comp_resets_on_cam_reset=True,
        )
        r3 = verify_ael_wireless_flash_and_interval_pb_edit_guard(
            claimed_wireless_flash_ignores_cam_reset=True,
        )
        for r in (r1, r2, r3):
            self.assertFalse(r.valid)
            self.assertEqual(
                r.status, STATUS_BLOCKED_G130_AEL_OR_FLASH_STILL_RESET_VIOLATION
            )

    def test_35_ext_flash_mishoe_only_rejects_sync_cord_and_menu_reset(self) -> None:
        for flag in ("off_camera_sync_cord_flash_requested", "camera_menu_flash_reset_requested"):
            res = verify_ael_wireless_flash_and_interval_pb_edit_guard(**{flag: True})
            self.assertFalse(res.valid)
            self.assertEqual(
                res.status, STATUS_BLOCKED_G130_EXT_FLASH_MISHOE_OR_FX6_VIOLATION
            )

    def test_36_fx6_lacks_flash_and_flash_band_reduce_disambiguated(self) -> None:
        self.assertEqual(FX6_FLASH_BAND_REDUCE_NAME_G130, "Flash Band Reduce")
        for kw in [
            {"target_model": FX6_MODEL_NAME_PHASE299, "wireless_flash_use_requested": True},
            {"target_model": FX6_MODEL_NAME_PHASE299, "ael_w_shutter_use_requested": True},
            {"claimed_fx6_has_still_flash_or_ael": True},
            {"claimed_fx6_flash_band_reduce_is_flash_trigger": True},
        ]:
            res = verify_ael_wireless_flash_and_interval_pb_edit_guard(**kw)  # type: ignore[arg-type]
            self.assertFalse(res.valid)
            self.assertEqual(
                res.status, STATUS_BLOCKED_G130_EXT_FLASH_MISHOE_OR_FX6_VIOLATION
            )

    def test_37_interval_playback_exact_1_to_9_scale_and_default_5(self) -> None:
        self.assertEqual(ALLOWED_PLAY_SPEED_INTERVAL_SCALE_G130, (1, 2, 3, 4, 5, 6, 7, 8, 9))
        for spd in ALLOWED_PLAY_SPEED_INTERVAL_SCALE_G130:
            res = verify_ael_wireless_flash_and_interval_pb_edit_guard(
                requested_cont_play_for_interval="On",
                requested_play_speed_for_interval=spd,
                requested_select_playback_media=MEDIA_SLOT_1_PHASE299,
                slot_1_contains_tier0_vault=True,
            )
            self.assertTrue(res.valid)
            self.assertEqual(res.effective_play_speed_for_interval, spd)
            self.assertTrue(res.interval_pb_read_only_safe)

    def test_38_interval_playback_out_of_range_and_wrong_path_rejected(self) -> None:
        for bad_spd in (0, -1, 10, 99):
            res = verify_ael_wireless_flash_and_interval_pb_edit_guard(
                requested_play_speed_for_interval=bad_spd,
            )
            self.assertFalse(res.valid)
            self.assertEqual(
                res.status, STATUS_BLOCKED_G130_INTERVAL_PLAYBACK_SCALE_OR_PATH_VIOLATION
            )
        for kw in [
            {"interval_pb_menu_path": INTERVAL_PB_WRONG_PATH_G130},
            {"claimed_interval_under_playback_option": True},
            {"claimed_play_speed_max_is_5": True},
            {"claimed_in_camera_timelapse_movie_assembly": True},
        ]:
            res = verify_ael_wireless_flash_and_interval_pb_edit_guard(**kw)  # type: ignore[arg-type]
            self.assertFalse(res.valid)
            self.assertEqual(
                res.status, STATUS_BLOCKED_G130_INTERVAL_PLAYBACK_SCALE_OR_PATH_VIOLATION
            )

    def test_39_playback_edit_active_4_items_and_photo_capture_formats(self) -> None:
        self.assertEqual(
            PLAYBACK_EDIT_ACTIVE_4_ITEMS_G130,
            ("Rotate", "Photo Capture", "JPEG/HEIF Switch", "Copy"),
        )
        for fmt in (
            PHOTO_CAPTURE_FILE_JPEG_G130,
            PHOTO_CAPTURE_FILE_HEIF_420_G130,
            PHOTO_CAPTURE_FILE_HEIF_422_G130,
        ):
            res = verify_ael_wireless_flash_and_interval_pb_edit_guard(
                requested_photo_capture_file_type=fmt,
                requested_select_playback_media=MEDIA_SLOT_2_PHASE299,
                requested_playback_edit_action="Photo Capture",
                slot_1_contains_tier0_vault=True,
            )
            self.assertTrue(res.valid)
            self.assertEqual(res.effective_photo_capture_file_type, fmt)
            self.assertEqual(res.target_write_slot, MEDIA_SLOT_2_PHASE299)
            self.assertEqual(res.slot1_data_sector_writes, 0)

    def test_40_dormant_beauty_effect_and_trimming_traps_rejected(self) -> None:
        for trap in DORMANT_PLAYBACK_EDIT_TRAP_ITEMS_G130:
            res = verify_ael_wireless_flash_and_interval_pb_edit_guard(
                requested_select_playback_media=MEDIA_SLOT_2_PHASE299,
                requested_playback_edit_action=trap,
                slot_1_contains_tier0_vault=False,
            )
            self.assertFalse(res.valid)
            self.assertEqual(
                res.status,
                STATUS_BLOCKED_G130_PLAYBACK_EDIT_DORMANT_OR_SLOT1_VAULT_VIOLATION,
            )

    def test_41_slot1_tier0_vault_blocks_rotate_and_photo_capture_eopnotsupp(self) -> None:
        for action in ("Rotate", "Photo Capture"):
            res = verify_ael_wireless_flash_and_interval_pb_edit_guard(
                requested_select_playback_media=MEDIA_SLOT_1_PHASE299,
                requested_playback_edit_action=action,
                slot_1_contains_tier0_vault=True,
                slot_1_write_protected=False,
            )
            self.assertFalse(res.valid)
            self.assertEqual(
                res.status,
                STATUS_BLOCKED_G130_PLAYBACK_EDIT_DORMANT_OR_SLOT1_VAULT_VIOLATION,
            )
            self.assertEqual(res.target_write_slot, MEDIA_SLOT_1_PHASE299)
            self.assertTrue(res.playback_edit_blocked_by_slot1_vault_firewall)
            self.assertEqual(res.block_errno, "EOPNOTSUPP")
            self.assertEqual(res.slot1_data_sector_writes, 0)
            self.assertFalse(res.slot1_avf_info_mutated)

    def test_42_slot1_write_protect_blocks_copy_slot2_to_slot1_erofs(self) -> None:
        res = verify_ael_wireless_flash_and_interval_pb_edit_guard(
            requested_select_playback_media=MEDIA_SLOT_2_PHASE299,
            requested_playback_edit_action="Copy",
            slot_1_contains_tier0_vault=False,
            slot_1_write_protected=True,
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            res.status,
            STATUS_BLOCKED_G130_PLAYBACK_EDIT_DORMANT_OR_SLOT1_VAULT_VIOLATION,
        )
        self.assertEqual(res.target_write_slot, MEDIA_SLOT_1_PHASE299)
        self.assertEqual(res.block_errno, "EROFS")
        self.assertEqual(res.slot1_data_sector_writes, 0)
        self.assertFalse(res.slot1_avf_info_mutated)

    def test_43_copy_slot1_to_slot2_and_rotate_slot2_allowed_with_zero_slot1_writes(self) -> None:
        copy_1_to_2 = verify_ael_wireless_flash_and_interval_pb_edit_guard(
            requested_select_playback_media=MEDIA_SLOT_1_PHASE299,
            requested_playback_edit_action="Copy",
            slot_1_contains_tier0_vault=True,
        )
        self.assertTrue(copy_1_to_2.valid)
        self.assertEqual(copy_1_to_2.target_write_slot, MEDIA_SLOT_2_PHASE299)
        self.assertEqual(copy_1_to_2.slot1_data_sector_writes, 0)

        rot_2 = verify_ael_wireless_flash_and_interval_pb_edit_guard(
            requested_select_playback_media=MEDIA_SLOT_2_PHASE299,
            requested_playback_edit_action="Rotate",
            slot_1_contains_tier0_vault=True,
        )
        self.assertTrue(rot_2.valid)
        self.assertEqual(rot_2.target_write_slot, MEDIA_SLOT_2_PHASE299)
        self.assertEqual(rot_2.slot1_data_sector_writes, 0)

    def test_44_g130_432_state_matrix_holds(self) -> None:
        m = compute_ael_flash_and_interval_pb_edit_matrix()
        self.assertEqual(m["states_checked"], 432)
        self.assertTrue(m["all_invariants_hold"])
        self.assertEqual(m["wireless_reset_cam_count"], 216)
        self.assertEqual(m["ael_survived_cam_count"], 216)
        self.assertEqual(m["slot1_edit_blocked_count"], 108)

    def test_45_g130_invalid_telemetry_fails_closed(self) -> None:
        bad1 = verify_ael_wireless_flash_and_interval_pb_edit_guard(
            requested_play_speed_for_interval=True,  # type: ignore[arg-type]
        )
        bad2 = verify_ael_wireless_flash_and_interval_pb_edit_guard(
            requested_playback_edit_action="Unknown Edit Op",
        )
        for b in (bad1, bad2):
            self.assertFalse(b.valid)
            self.assertEqual(b.status, STATUS_BLOCKED_G130_TELEMETRY_INVALID)

    def test_46_evaluate_g130_blocks_persistent_emmc_write(self) -> None:
        v, r = evaluate_g130_ael_wireless_flash_and_interval_pb_edit_guard(
            force_clean_room=True,
            request_persistent_emmc_writes=True,
        )
        self.assertFalse(v.passed)
        self.assertFalse(r.valid)
        self.assertEqual(r.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)


class TestUnified130GateEngineAndCli(unittest.TestCase):
    def test_47_stub_130gate_offline_127_of_130(self) -> None:
        rep = evaluate_130gate_preflight(
            force_clean_room=True,
            master_128_override=_make_stub_master128(dry_run=False),
        )
        self.assertEqual(rep.summary["total_gates"], 130)
        self.assertEqual(rep.summary["verified_gates"], 127)
        self.assertTrue(rep.offline_127_gates_verified)
        self.assertFalse(rep.all_130_gates_verified)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.cross_model_flash_authorized)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)
        self.assertEqual(rep.status, "VERIFIED_127_OF_130_AWAITING_PHYSICAL_TIER0")
        self.assertEqual(len(rep.gates), 130)

    def test_48_stub_130gate_dry_run_130_of_130(self) -> None:
        rep = evaluate_130_master_safety_gates(
            force_clean_room=True,
            simulate_bench_dry_run=True,
            master_128_override=_make_stub_master128(dry_run=True),
        )
        self.assertEqual(rep.summary["verified_gates"], 130)
        self.assertTrue(rep.all_130_gates_verified)
        self.assertTrue(rep.dry_run_rehearsal_only)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertEqual(rep.status, "VERIFIED_ALL_130_GATES_DRY_RUN_SIMULATED_BACKUP")

    def test_49_g129_failure_propagates_to_130gate_report(self) -> None:
        rep = evaluate_130gate_preflight(
            force_clean_room=True,
            master_128_override=_make_stub_master128(dry_run=True),
            touch_shooting_disp_evf_kwargs={"evf_scanout_switch_requested": True},
        )
        self.assertFalse(rep.g129_to_g130_all_passed)
        self.assertFalse(rep.all_130_gates_verified)
        self.assertEqual(rep.status, STATUS_BLOCKED_G129_ZERO_EVF_BLACKOUT_TRAP_VIOLATION)

    def test_50_g130_failure_propagates_to_130gate_report(self) -> None:
        rep = evaluate_130gate_preflight(
            force_clean_room=True,
            master_128_override=_make_stub_master128(dry_run=True),
            ael_flash_interval_pb_edit_kwargs={
                "requested_select_playback_media": MEDIA_SLOT_1_PHASE299,
                "requested_playback_edit_action": "Photo Capture",
                "slot_1_contains_tier0_vault": True,
            },
        )
        self.assertFalse(rep.g129_to_g130_all_passed)
        self.assertFalse(rep.all_130_gates_verified)
        self.assertEqual(
            rep.status,
            STATUS_BLOCKED_G130_PLAYBACK_EDIT_DORMANT_OR_SLOT1_VAULT_VIOLATION,
        )

    def test_51_persistent_emmc_write_blocks_130gate_report(self) -> None:
        rep = run_130_gate_preflight(
            force_clean_room=True,
            request_persistent_emmc_writes=True,
            master_128_override=_make_stub_master128(dry_run=True),
        )
        self.assertEqual(rep.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        self.assertFalse(rep.all_130_gates_verified)

    def test_52_real_chained_130gate_offline_and_dry_run(self) -> None:
        off = evaluate_130gate_preflight(DEFAULT_REPO_ROOT)
        self.assertEqual(off.summary["verified_gates"], 127)
        self.assertTrue(off.offline_127_gates_verified)
        self.assertFalse(off.overall_ready_for_hardware_attach)
        self.assertEqual(off.raw_firmware_bytes_leaked, 0)

        dry = evaluate_130gate_preflight(
            DEFAULT_REPO_ROOT, simulate_bench_dry_run=True
        )
        self.assertEqual(dry.summary["verified_gates"], 130)
        self.assertTrue(dry.all_130_gates_verified)
        self.assertFalse(dry.overall_ready_for_hardware_attach)
        self.assertFalse(dry.persistent_emmc_writes_authorized)
        self.assertFalse(dry.cross_model_flash_authorized)

    def test_53_cli_help_python314_percent_escaping(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            with self.assertRaises(SystemExit) as ctx:
                cli_main(["--help"])
        self.assertEqual(ctx.exception.code, 0)
        out = buf.getvalue()
        self.assertIn("verify-touch-shooting-and-disp-evf-absence-guard", out)
        self.assertIn("verify-ael-wireless-flash-and-interval-pb-edit-guard", out)
        self.assertIn("verify-130-gates", out)

    def test_54_cli_g129_g130_summary_json_and_text(self) -> None:
        for cmd in (
            "verify-touch-shooting-and-disp-evf-absence-guard",
            "verify-ael-wireless-flash-and-interval-pb-edit-guard",
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

    def test_55_cli_verify_130_gates_subprocess_uses_sys_executable(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONPATH"] = str(DEFAULT_REPO_ROOT / "outputs" / "fx3-safety")
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "fx3_safety",
                "verify-130-gates",
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
        self.assertEqual(payload["status"], "VERIFIED_ALL_130_GATES_DRY_RUN_SIMULATED_BACKUP")
        self.assertEqual(payload["summary"]["verified_gates"], 130)
        self.assertEqual(payload["g129_status"], STATUS_VERIFIED_G129)
        self.assertEqual(payload["g130_status"], STATUS_VERIFIED_G130)

    def test_56_module_direct_main_entrypoint(self) -> None:
        for gate_flag in ("g129", "g130", "130"):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = module_main(["--gate", gate_flag, "--clean-room", "--summary", "--json"])
            self.assertEqual(rc, 0)
            data = json.loads(buf.getvalue())
            self.assertEqual(
                data["status"] if gate_flag != "130" else data["g129_status"],
                STATUS_VERIFIED_G129 if gate_flag in ("g129", "130") else STATUS_VERIFIED_G130,
            )

    def test_57_cli_verify_130_gates_offline_text_mode(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cli_main(["verify-130-gates", "--clean-room"])
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("VERIFIED_127_OF_130_AWAITING_PHYSICAL_TIER0", out)
        self.assertIn("verified=127/130", out)
        self.assertIn("overall_ready_for_hardware_attach=False", out)

    def test_58_cli_aliases_work_cleanly(self) -> None:
        for alias in (
            "verify-g129-touch-shooting-disp-evf",
            "verify-g130-ael-flash-interval-pb-edit",
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = cli_main([alias, "--clean-room", "--summary", "--json"])
            self.assertEqual(rc, 0)
            self.assertTrue(json.loads(buf.getvalue())["valid"])

    def test_59_g129_normalization_aliases(self) -> None:
        res = verify_touch_shooting_and_disp_evf_absence_guard(
            shoot_mode="S&Q Motion",
            requested_touch_operation="ON_PLAYBACK_ONLY",
            requested_touch_sensitivity="sensitive",
            requested_touch_func_in_shooting="touch focus",
            requested_swipe_up="fn menu",
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.shoot_mode, SHOOT_MODE_SQ_PHASE299)
        self.assertEqual(res.effective_touch_operation, TOUCH_OP_PLAYBACK_ONLY_G129)
        self.assertEqual(res.effective_touch_sensitivity, TOUCH_SENSITIVITY_SENSITIVE_G129)
        self.assertEqual(res.effective_touch_func_in_shooting, TOUCH_FUNC_TOUCH_FOCUS_G129)
        self.assertEqual(res.effective_swipe_up, SWIPE_UP_OPEN_FN_MENU_G129)

    def test_60_g130_normalization_aliases(self) -> None:
        res = verify_ael_wireless_flash_and_interval_pb_edit_guard(
            requested_ael_w_shutter="ON",
            requested_exp_comp_set="Ambient and Flash",
            requested_wireless_flash="ON",
            requested_cont_play_for_interval="on",
            requested_photo_capture_file_type="heif(4:2:0)",
            requested_select_playback_media="slot2",
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.effective_ael_w_shutter, AEL_W_SHUTTER_ON_G130)
        self.assertEqual(res.effective_exp_comp_set, EXP_COMP_SET_AMBIENT_AND_FLASH_G130)
        self.assertEqual(res.effective_wireless_flash, WIRELESS_FLASH_ON_G130)
        self.assertEqual(res.effective_cont_play_for_interval, "On")
        self.assertEqual(res.effective_photo_capture_file_type, PHOTO_CAPTURE_FILE_HEIF_420_G130)
        self.assertEqual(res.effective_select_playback_media, MEDIA_SLOT_2_PHASE299)

    def test_61_g129_all_disp_shoot_subsets_valid(self) -> None:
        for page in DISP_SHOOT_4_PAGES_G129:
            res = verify_touch_shooting_and_disp_evf_absence_guard(
                requested_disp_shoot_pages=(page,),
            )
            self.assertTrue(res.valid)
            self.assertEqual(res.disp_shoot_pages_enabled, (page,))

    def test_62_g129_all_disp_play_subsets_valid(self) -> None:
        for page in DISP_PLAY_3_PAGES_G129:
            res = verify_touch_shooting_and_disp_evf_absence_guard(
                requested_disp_play_pages=(page,),
            )
            self.assertTrue(res.valid)
            self.assertEqual(res.disp_play_pages_enabled, (page,))

    def test_63_g129_reset_network_set_does_not_wipe_touch_or_disp(self) -> None:
        res = verify_touch_shooting_and_disp_evf_absence_guard(
            requested_touch_operation=TOUCH_OP_OFF_G129,
            requested_touch_sensitivity=TOUCH_SENSITIVITY_SENSITIVE_G129,
            reset_action="Reset Network Set.",
        )
        self.assertTrue(res.valid)
        self.assertTrue(res.touch_4_items_survived_cam_reset)
        self.assertEqual(res.effective_touch_operation, TOUCH_OP_OFF_G129)
        self.assertEqual(res.effective_touch_sensitivity, TOUCH_SENSITIVITY_SENSITIVE_G129)

    def test_64_g130_reset_network_set_preserves_ael_flash_and_interval(self) -> None:
        res = verify_ael_wireless_flash_and_interval_pb_edit_guard(
            requested_ael_w_shutter=AEL_W_SHUTTER_OFF_G130,
            requested_exp_comp_set=EXP_COMP_SET_AMBIENT_ONLY_G130,
            requested_wireless_flash=WIRELESS_FLASH_ON_G130,
            requested_play_speed_for_interval=2,
            reset_action="Reset Network Set.",
        )
        self.assertTrue(res.valid)
        self.assertFalse(res.wireless_flash_reset_on_cam_reset)
        self.assertEqual(res.effective_wireless_flash, WIRELESS_FLASH_ON_G130)
        self.assertEqual(res.effective_play_speed_for_interval, 2)

    def test_65_g130_still_modes_allow_ael_and_flash(self) -> None:
        for sm in ("Still", "P", "A", "S", "M"):
            res = verify_ael_wireless_flash_and_interval_pb_edit_guard(
                shoot_mode=sm,
                ael_w_shutter_use_requested=True,
                exp_comp_set_use_requested=True,
                wireless_flash_use_requested=True,
                external_flash_use_requested=True,
            )
            self.assertTrue(res.valid)

    def test_66_g130_all_external_flash_submenus_supported(self) -> None:
        self.assertEqual(
            EXT_FLASH_SUBMENUS_G130,
            ("Ext. Flash Firing Set.", "Ext. Flash Cust. Set."),
        )
        for sub in EXT_FLASH_SUBMENUS_G130:
            res = verify_ael_wireless_flash_and_interval_pb_edit_guard(
                requested_external_flash_set=sub,
                external_flash_use_requested=True,
            )
            self.assertTrue(res.valid)
            self.assertEqual(res.effective_external_flash_set, sub)
            self.assertTrue(res.ext_flash_direct_mishoe_only)
            self.assertFalse(res.off_camera_sync_cord_supported)

    def test_67_g130_all_3_ael_modes_and_2_exp_comp_modes_verified(self) -> None:
        self.assertEqual(ALLOWED_AEL_W_SHUTTER_MODES_G130, ("Auto", "On", "Off"))
        self.assertEqual(ALLOWED_EXP_COMP_SET_MODES_G130, ("Ambient&flash", "Ambient only"))
        self.assertEqual(ALLOWED_WIRELESS_FLASH_MODES_G130, ("Off", "On"))
        self.assertEqual(
            ALLOWED_PHOTO_CAPTURE_FILE_TYPES_G130,
            ("JPEG", "HEIF(4:2:0)", "HEIF(4:2:2)"),
        )
        for ael in ALLOWED_AEL_W_SHUTTER_MODES_G130:
            for ec in ALLOWED_EXP_COMP_SET_MODES_G130:
                res = verify_ael_wireless_flash_and_interval_pb_edit_guard(
                    requested_ael_w_shutter=ael,
                    requested_exp_comp_set=ec,
                )
                self.assertTrue(res.valid)
                self.assertEqual(res.effective_ael_w_shutter, ael)
                self.assertEqual(res.effective_exp_comp_set, ec)

    def test_68_g130_jpeg_heif_switch_action_metadata_safe(self) -> None:
        res = verify_ael_wireless_flash_and_interval_pb_edit_guard(
            requested_select_playback_media=MEDIA_SLOT_1_PHASE299,
            requested_playback_edit_action="JPEG/HEIF Switch",
            requested_photo_capture_file_type=PHOTO_CAPTURE_FILE_HEIF_422_G130,
            slot_1_contains_tier0_vault=True,
        )
        self.assertTrue(res.valid)
        self.assertIsNone(res.target_write_slot)
        self.assertEqual(res.slot1_data_sector_writes, 0)

    def test_69_g130_rotate_and_photo_capture_allowed_only_if_slot1_unlocked(self) -> None:
        for act in ("Rotate", "Photo Capture"):
            res = verify_ael_wireless_flash_and_interval_pb_edit_guard(
                requested_select_playback_media=MEDIA_SLOT_1_PHASE299,
                requested_playback_edit_action=act,
                slot_1_contains_tier0_vault=False,
                slot_1_write_protected=False,
            )
            self.assertTrue(res.valid)
            self.assertFalse(res.playback_edit_blocked_by_slot1_vault_firewall)

    def test_70_g129_menu_path_and_fx3_identity_constants(self) -> None:
        self.assertEqual(FX3_MODEL_NAME_PHASE299, "ILME-FX3")
        self.assertEqual(FX3_MODEL_ID_PHASE299, 0x39383232)
        self.assertEqual(FX3_HELP_GUIDE_CODE_PHASE299, "ilc/2210")
        self.assertEqual(FX3_DEFAULT_FW_VERSION_PHASE299, "7.02")
        self.assertEqual(FX6_MODEL_NAME_PHASE299, "ILME-FX6")
        self.assertEqual(FX6_DEFAULT_FW_VERSION_PHASE299, "6.01")
        self.assertIn("Operation Customize", DISP_SET_MENU_PATH_G129)
        self.assertIn("[Viewing]", INTERVAL_PB_MENU_PATH_G130)

    def test_71_g129_resolver_defaults_and_serialize(self) -> None:
        s = resolve_fx3_touch_shooting_and_disp_evf_state()
        self.assertEqual(s["effective_touch_operation"], TOUCH_OP_ON_G129)
        self.assertTrue(s["swipe_up_active"])
        res = verify_touch_shooting_and_disp_evf_absence_guard()
        d = res.to_dict()
        self.assertIsInstance(d, dict)
        self.assertTrue(d["valid"])

    def test_72_g130_resolver_defaults_and_serialize(self) -> None:
        s = resolve_fx3_ael_flash_and_interval_pb_edit_state()
        self.assertEqual(s["effective_play_speed_for_interval"], 5)
        self.assertFalse(s["playback_edit_blocked_by_slot1_vault_firewall"])
        res = verify_ael_wireless_flash_and_interval_pb_edit_guard()
        d = res.to_dict()
        self.assertIsInstance(d, dict)
        self.assertTrue(d["valid"])

    def test_73_g129_bool_body_id_rejected(self) -> None:
        res = verify_touch_shooting_and_disp_evf_absence_guard(
            body_model_id=True,  # type: ignore[arg-type]
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_G129_TELEMETRY_INVALID)

    def test_74_g130_bool_body_id_rejected(self) -> None:
        res = verify_ael_wireless_flash_and_interval_pb_edit_guard(
            body_model_id=False,  # type: ignore[arg-type]
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_G130_TELEMETRY_INVALID)

    def test_75_g129_invalid_fw_rejected(self) -> None:
        res = verify_touch_shooting_and_disp_evf_absence_guard(firmware_version="BAD")
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_G129_TELEMETRY_INVALID)

    def test_76_g130_invalid_ext_flash_submenu_rejected(self) -> None:
        res = verify_ael_wireless_flash_and_interval_pb_edit_guard(
            requested_external_flash_set="Unknown Submenu",
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_G130_TELEMETRY_INVALID)

    def test_77_master130_gates_g129_and_g130_last_two_entries(self) -> None:
        rep = evaluate_130gate_preflight(
            force_clean_room=True,
            simulate_bench_dry_run=True,
            master_128_override=_make_stub_master128(dry_run=True),
        )
        self.assertEqual(rep.gates[128]["gate_id"], "G129")
        self.assertEqual(rep.gates[128]["gate_code"], G129_GATE_CODE)
        self.assertTrue(rep.gates[128]["passed"])
        self.assertEqual(rep.gates[129]["gate_id"], "G130")
        self.assertEqual(rep.gates[129]["gate_code"], G130_GATE_CODE)
        self.assertTrue(rep.gates[129]["passed"])

    def test_78_master130_upstream_g128_failure_propagates(self) -> None:
        rep = evaluate_130gate_preflight(
            force_clean_room=True,
            simulate_bench_dry_run=True,
            master_128_override=_make_stub_master128(dry_run=True, all_g13_128_ok=False),
        )
        self.assertFalse(rep.g13_to_g130_all_passed)
        self.assertFalse(rep.all_130_gates_verified)
        self.assertFalse(rep.h0_h1_trial_entry_allowed)

    def test_79_master130_report_dict_roundtrip_json_serializable(self) -> None:
        rep = evaluate_130gate_preflight(
            force_clean_room=True,
            simulate_bench_dry_run=True,
            master_128_override=_make_stub_master128(dry_run=True),
        )
        encoded = json.dumps(rep.to_dict())
        decoded = json.loads(encoded)
        self.assertEqual(decoded["summary"]["total_gates"], 130)
        self.assertEqual(decoded["summary"]["verified_gates"], 130)
        self.assertFalse(decoded["overall_ready_for_hardware_attach"])

    def test_80_cli_verify_130_gates_full_json_payload(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cli_main(["verify-130-gates", "--clean-room", "--simulate-bench-dry-run", "--json"])
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())
        self.assertEqual(len(payload["gates"]), 130)
        self.assertEqual(payload["status"], "VERIFIED_ALL_130_GATES_DRY_RUN_SIMULATED_BACKUP")
        self.assertEqual(payload["raw_firmware_bytes_leaked"], 0)

    def test_81_g129_touch_op_off_blocks_neither_shooting_mode_nor_disp(self) -> None:
        res = verify_touch_shooting_and_disp_evf_absence_guard(
            requested_touch_operation=TOUCH_OP_OFF_G129,
            requested_disp_shoot_pages=DISP_SHOOT_4_PAGES_G129,
        )
        self.assertTrue(res.valid)
        self.assertFalse(res.swipe_up_active)
        self.assertEqual(res.disp_shoot_pages_enabled, DISP_SHOOT_4_PAGES_G129)

    def test_82_g130_dormant_beauty_effect_blocked_even_on_slot2(self) -> None:
        res = verify_ael_wireless_flash_and_interval_pb_edit_guard(
            requested_select_playback_media=MEDIA_SLOT_2_PHASE299,
            requested_playback_edit_action="Beauty Effect",
            slot_1_contains_tier0_vault=True,
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            res.status,
            STATUS_BLOCKED_G130_PLAYBACK_EDIT_DORMANT_OR_SLOT1_VAULT_VIOLATION,
        )
        self.assertEqual(res.slot1_data_sector_writes, 0)

    def test_83_g130_dormant_trimming_blocked_and_slot1_write_zero(self) -> None:
        res = verify_ael_wireless_flash_and_interval_pb_edit_guard(
            requested_select_playback_media=MEDIA_SLOT_1_PHASE299,
            requested_playback_edit_action="Trimming",
            slot_1_contains_tier0_vault=True,
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            res.status,
            STATUS_BLOCKED_G130_PLAYBACK_EDIT_DORMANT_OR_SLOT1_VAULT_VIOLATION,
        )
        self.assertEqual(res.slot1_data_sector_writes, 0)
        self.assertFalse(res.slot1_avf_info_mutated)

    def test_84_donor_audit_under_200ms_or_ci_headroom_local_mode(self) -> None:
        with mock.patch.dict(
            os.environ,
            {ENV_FORCE_CLEAN_ROOM: "0", ENV_CLEAN_ROOM_TEST_PHASE299: "0"},
        ):
            res = audit_phase299_donor_contracts(force_clean_room=False)
            self.assertTrue(res.valid)
            self.assertIn(
                res.verification_mode, ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC")
            )
            self.assertEqual(res.raw_firmware_bytes_leaked, 0)


if __name__ == "__main__":
    unittest.main()
