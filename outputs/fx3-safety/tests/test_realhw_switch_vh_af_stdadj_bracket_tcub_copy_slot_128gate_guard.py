"""Phase 297 (Wave-54, 128/128 Power-of-Two Safety Gates Milestone!) Dual-Mode Unit Tests (86 tests) for
`fx3_safety.realhw_switch_vh_af_stdadj_bracket_tcub_copy_slot_and_128gate_guard`:

- Gate `G127` (`GATE_G127_SWITCH_VH_AF_FOCUS_LIMIT_STD_ADJ_AND_BRACKET_GUARD`):
  - `[Switch V/H AF Area]` (`Off` / `AF Point Only` / `AF Point + AF Area`) operating ONLY in Still
    `AF-C` across `0°/90°/270°` gravity orientations vs `INVALID` vertical pitch up/down and 8
    lockout conditions (`Movie/S&Q`, non-`AF-C`, `Intelligent Auto`, Digital Zoom, active AF,
    burst/continuous shooting, self-timer countdown, `[Focus Magnifier]`); mode change clears
    stored points; resets on `[Camera Settings Reset]`.
  - `[Focus Area Limit]` exact 14 checkboxes vs dormant `Spot: XL/XS` & `Custom 1..3` fail-closed
    rejection, minimum `>= 2` enabled areas (`.uxc 0xea28`), Movie/`S&Q` `Tracking:*` exclusion.
  - `[Exposure Std. Adjust]` ALL 5 metering modes (`Multi`, `Center`, `Spot`, `Entire Screen Avg.`,
    `Highlight`) at `-1..+1 EV` (`1/6 EV`, 13 steps `-6..+6`), independent EXIF / `M.M.` / Spot AEL
    shift, active bracket shot-count reset, and **`[Camera Settings Reset]` survival (`Initialize`-only)**.
  - Still `[Bracket Settings]` (`[Selftimer during Bracket]` `Off/2/5/10 Sec`, `[Bracket order]`
    `0->-->+ / -->0->+`) Still-only enforcement + `ILME-FX6` dormant `bracket_*` exclusion.
- Gate `G128` (`GATE_G128_TCUB_FORMAT_PLAYBACK_COPY_DIRECTION_AND_SLIDESHOW_GUARD`):
  - All 6 `[TC/UB]` items + `[TC/UB Disp. Setting]` (`Counter / TC / U-Bit`) surviving
    `[Camera Settings Reset]` (`Initialize`-only!), playback toggle restricted to Movie playback
    (`.uxc 0xe728`), `[Time Code Format]` NTSC-only (`DF/NDF`), forced `NDF` in `23.98p`/`24.00p`,
    hidden in `PAL`, and `ILME-FX3` no-BNC vs `ILME-FX6` physical BNC `TC IN/OUT` + `EXT-LK`.
  - Playback `[Copy]` directional asymmetry firewall: `[Select Playback Media] = Slot 1` copies
    `Slot 1 -> Slot 2` (stripping `Protect` flags), whereas `[Select Playback Media] = Slot 2`
    reverses write direction onto `Slot 1` (`Slot 2 -> Slot 1`) and is blocked fail-closed
    (`EROFS`/`EBUSY`, `slot1_data_sector_writes == 0`, `slot1_avf_info_mutated == False`) whenever
    `Slot 1` holds the Tier-0 recovery vault or is write-protected! Plus battery gate, destination
    card speed class, `[Slide Show]` (`Date View` / `Folder View(Still)` only) `Power Save Start Time`
    sleep bypass, and dormant `FX6` `Copy Clip` exclusion.
- Unified `128`-Gate Milestone Master Preflight (`evaluate_128gate_preflight` / `verify-128-gates`):
  - `125/128` offline (`VERIFIED_125_OF_128_AWAITING_PHYSICAL_TIER0`) and `128/128` under
    `--simulate-bench-dry-run` (`VERIFIED_ALL_128_GATES_DRY_RUN_SIMULATED_BACKUP`) with all redlines
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
from fx3_safety.realhw_lens_comp_af_illuminator_aperture_drive_folder_rating_and_126gate_guard import (
    Master126GateReport,
)
from fx3_safety.realhw_switch_vh_af_stdadj_bracket_tcub_copy_slot_and_128gate_guard import (
    ALLOWED_BRACKET_ORDERS_G127,
    ALLOWED_BRACKET_SELFTIMER_OPTIONS_G127,
    ALLOWED_DEST_CARD_SPEED_CLASSES_G128,
    ALLOWED_GRAVITY_ORIENTATIONS_G127,
    ALLOWED_PLAYBACK_MEDIA_SLOTS_G128,
    ALLOWED_SLIDE_SHOW_INTERVALS_G128,
    ALLOWED_SLIDE_SHOW_VIEW_MODES_G128,
    ALLOWED_SWITCH_VH_AF_MODES_G127,
    ALLOWED_TCUB_DISP_SETTINGS_G128,
    ALLOWED_TC_FORMATS_G128,
    BRACKET_ORDER_DEFAULT_G127,
    BRACKET_ORDER_MINUS_ZERO_PLUS_G127,
    BRACKET_ORDER_ZERO_MINUS_PLUS_G127,
    BRACKET_SELFTIMER_10SEC_G127,
    BRACKET_SELFTIMER_2SEC_G127,
    BRACKET_SELFTIMER_5SEC_G127,
    BRACKET_SELFTIMER_DEFAULT_G127,
    BRACKET_SELFTIMER_OFF_G127,
    CROSS_MODEL_FLASH_AUTHORIZED,
    DEFAULT_REPO_ROOT,
    DISALLOWED_SLIDE_SHOW_VIEW_MODES_G128,
    DONOR_CHECK_CI_MAX_SECONDS_PHASE297,
    DONOR_CHECK_MAX_SECONDS_PHASE297,
    DORMANT_FOCUS_AREA_LIMIT_OPTIONS_G127,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    ENV_CLEAN_ROOM_TEST_PHASE297,
    ENV_FORCE_CLEAN_ROOM,
    EXPOSURE_STD_ADJ_5_METERING_MODES_G127,
    EXPOSURE_STD_ADJ_STEP_COUNT_G127,
    EXPOSURE_STD_ADJ_VALID_SIXTHS_G127,
    FOCUS_AREA_COLOR_RED_G127,
    FOCUS_AREA_COLOR_WHITE_G127,
    FOCUS_AREA_LIMIT_14_OPTIONS_G127,
    FOCUS_AREA_LIMIT_MIN_ENABLED_G127,
    FOCUS_AREA_LIMIT_TRACKING_OPTIONS_G127,
    FX3_DEFAULT_FW_VERSION_PHASE297,
    FX3_HELP_GUIDE_CODE_PHASE297,
    FX3_MODEL_ID_PHASE297,
    FX3_MODEL_NAME_PHASE297,
    FX6_DEFAULT_FW_VERSION_PHASE297,
    FX6_MODEL_NAME_PHASE297,
    G127,
    G127_GATE_CODE,
    G127_GATE_ID,
    G128,
    G128_GATE_CODE,
    G128_GATE_ID,
    GRAVITY_ORIENTATION_0_DEG_G127,
    GRAVITY_ORIENTATION_270_DEG_G127,
    GRAVITY_ORIENTATION_90_DEG_G127,
    GRAVITY_ORIENTATION_INVALID_G127,
    HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    HUMAN_HARDWARE_ATTACH_TOKEN,
    MEDIA_SLOT_1_G128,
    MEDIA_SLOT_2_G128,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED,
    PHYSICAL_USB_PACKETS_EMITTED,
    PINNED_FX3_APPFW_SLICES_PHASE297,
    PINNED_FX3_APPFW_SLICES_SHA256_PHASE297,
    PINNED_FX6_APPFW_SLICES_PHASE297,
    PINNED_FX6_APPFW_SLICES_SHA256_PHASE297,
    PINNED_PHASE297_DONOR_SPECS,
    RAW_FIRMWARE_BYTES_LEAKED,
    REALHW_SWITCH_VH_AF_STDADJ_BRACKET_TCUB_COPY_SLOT_128GATE_SCHEMA,
    RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE297,
    RESET_ACTION_INITIALIZE_PHASE297,
    RESET_ACTION_NONE_PHASE297,
    SHOOT_MODE_INTELLIGENT_AUTO_PHASE297,
    SHOOT_MODE_MOVIE_PHASE297,
    SHOOT_MODE_M_PHASE297,
    SHOOT_MODE_P_PHASE297,
    SHOOT_MODE_SQ_PHASE297,
    SLIDE_SHOW_INTERVAL_10SEC_G128,
    SLIDE_SHOW_INTERVAL_1SEC_G128,
    SLIDE_SHOW_INTERVAL_30SEC_G128,
    SLIDE_SHOW_INTERVAL_3SEC_G128,
    SLIDE_SHOW_INTERVAL_5SEC_G128,
    SLIDE_SHOW_VIEW_DATE_G128,
    SLIDE_SHOW_VIEW_FOLDER_STILL_G128,
    SPI_NOR_WRITE_AUTHORIZED,
    STATUS_BLOCKED_G127_BRACKET_SETTINGS_OR_FX6_CROSSWIRE_VIOLATION,
    STATUS_BLOCKED_G127_EXPOSURE_STD_ADJ_5MODE_OR_RESET_VIOLATION,
    STATUS_BLOCKED_G127_FOCUS_AREA_LIMIT_DORMANT_OR_MIN2_VIOLATION,
    STATUS_BLOCKED_G127_SWITCH_VH_AF_LOCKOUT_OR_PITCH_INVALID,
    STATUS_BLOCKED_G127_TELEMETRY_INVALID,
    STATUS_BLOCKED_G128_COPY_BATTERY_SPEED_OR_SLIDESHOW_FX6_VIOLATION,
    STATUS_BLOCKED_G128_SLOT2_TO_SLOT1_VAULT_COPY_FIREWALL_VIOLATION,
    STATUS_BLOCKED_G128_TCUB_RESET_PERSISTENCE_OR_PLAYBACK_TOGGLE_VIOLATION,
    STATUS_BLOCKED_G128_TC_FORMAT_PAL_OR_24P_NDF_LOCK_VIOLATION,
    STATUS_BLOCKED_G128_TELEMETRY_INVALID,
    STATUS_BLOCKED_PERSISTENT_EMMC_WRITE,
    STATUS_BLOCKED_PHASE297_DONOR_INTEGRITY,
    STATUS_VERIFIED_G127,
    STATUS_VERIFIED_G128,
    STATUS_VERIFIED_SAFE,
    SWITCH_VH_AF_DEFAULT_G127,
    SWITCH_VH_AF_OFF_G127,
    SWITCH_VH_AF_POINT_AND_AREA_G127,
    SWITCH_VH_AF_POINT_ONLY_G127,
    TCUB_6_ITEMS_G128,
    TCUB_DISP_COUNTER_G128,
    TCUB_DISP_TC_G128,
    TCUB_DISP_UBIT_G128,
    TC_FORMAT_DF_G128,
    TC_FORMAT_NDF_G128,
    TC_MAKE_PRESET_G128,
    TC_MAKE_REGENERATE_G128,
    TC_RUN_FREE_G128,
    TC_RUN_REC_G128,
    TV_SYSTEM_NTSC_G128,
    TV_SYSTEM_PAL_G128,
    USB_PACKETS_TRANSMITTED,
    audit_phase297_donor_contracts,
    compute_switch_vh_af_and_exposure_stdadj_matrix,
    compute_tcub_and_playback_copy_slot_matrix,
    evaluate_128_master_safety_gates,
    evaluate_128gate_preflight,
    evaluate_g127_switch_vh_af_and_exposure_stdadj_guard,
    evaluate_g128_tcub_format_and_playback_copy_slot_guard,
    main as module_main,
    resolve_fx3_switch_vh_af_and_exposure_stdadj_state,
    resolve_fx3_tcub_format_and_playback_copy_slot_state,
    run_128_gate_preflight,
    verify_switch_vh_af_and_exposure_stdadj_guard,
    verify_tcub_format_and_playback_copy_slot_guard,
)


def _make_stub_master126(
    *, dry_run: bool = False, all_g13_126_ok: bool = True
) -> Master126GateReport:
    gates = []
    for i in range(1, 127):
        gid = f"G{i:02d}"
        is_tier0_offline = gid in ("G10", "G11", "G12") and not dry_run
        passed = (not is_tier0_offline) and (all_g13_126_ok or i <= 12)
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
    g13_124 = 112 if all_g13_126_ok else 0
    g125_126 = 2 if all_g13_126_ok else 0
    total = g01_12 + g13_124 + g125_126
    return Master126GateReport(
        schema="stub_126",
        version="2026.11.17",
        evaluated_utc="2026-11-17T00:00:00Z",
        verification_mode="CLEAN_ROOM_SYNTHETIC",
        clean_room_forced=True,
        dry_run_rehearsal_only=dry_run,
        overall_ready_for_hardware_attach=False,
        hardware_live_attachment_authorized=False,
        offline_123_gates_verified=all_g13_126_ok,
        all_126_gates_verified=(dry_run and all_g13_126_ok),
        g13_to_g126_all_passed=all_g13_126_ok,
        g125_to_g126_all_passed=all_g13_126_ok,
        h0_h1_trial_entry_allowed=all_g13_126_ok,
        status=(
            "VERIFIED_ALL_126_GATES_DRY_RUN_SIMULATED_BACKUP"
            if dry_run
            else "VERIFIED_123_OF_126_AWAITING_PHYSICAL_TIER0"
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
            "g13_to_g124_verified": g13_124,
            "g125_to_g126_verified": g125_126,
            "verified_gates": total,
        },
        gates=tuple(gates),
        master_124_report={},
        g125_result={},
        g126_result={},
        errors=(),
        warnings=(),
    )


class TestPhase297DonorAuditAndRedlines(unittest.TestCase):
    def test_01_package_exports_and_schema(self) -> None:
        self.assertEqual(G127, "G127")
        self.assertEqual(G127_GATE_ID, "G127")
        self.assertEqual(G128, "G128")
        self.assertEqual(G128_GATE_ID, "G128")
        self.assertTrue(hasattr(fx3_safety, "evaluate_128gate_preflight"))
        self.assertTrue(hasattr(fx3_safety, "verify_switch_vh_af_and_exposure_stdadj_guard"))
        self.assertTrue(hasattr(fx3_safety, "verify_tcub_format_and_playback_copy_slot_guard"))
        self.assertEqual(
            REALHW_SWITCH_VH_AF_STDADJ_BRACKET_TCUB_COPY_SLOT_128GATE_SCHEMA,
            "realhw_switch_vh_af_stdadj_bracket_tcub_copy_slot_and_128gate_guard_v1",
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
        self.assertEqual(len(PINNED_PHASE297_DONOR_SPECS), 11)
        self.assertEqual(len(PINNED_FX3_APPFW_SLICES_PHASE297), 48)
        self.assertEqual(len(PINNED_FX6_APPFW_SLICES_PHASE297), 14)

    def test_04_clean_room_forced_audit_succeeds(self) -> None:
        res = audit_phase297_donor_contracts(force_clean_room=True)
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_VERIFIED_SAFE)
        self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(res.files_inspected, 0)
        self.assertEqual(res.raw_firmware_bytes_leaked, 0)
        self.assertTrue(res.fx3_contracts_verified)
        self.assertTrue(res.fx6_contracts_verified)
        self.assertTrue(res.four_lang_resid16_parity_verified)

    def test_05_env_clean_room_flags_respected(self) -> None:
        for env_key in (ENV_FORCE_CLEAN_ROOM, ENV_CLEAN_ROOM_TEST_PHASE297):
            with mock.patch.dict(os.environ, {env_key: "1"}):
                res = audit_phase297_donor_contracts()
                self.assertTrue(res.valid)
                self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_06_explicit_missing_work_root_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.dict(
                os.environ,
                {ENV_FORCE_CLEAN_ROOM: "0", ENV_CLEAN_ROOM_TEST_PHASE297: "0"},
            ):
                res = audit_phase297_donor_contracts(
                    work_root=Path(tmp), force_clean_room=False
                )
                self.assertFalse(res.valid)
                self.assertEqual(res.status, STATUS_BLOCKED_PHASE297_DONOR_INTEGRITY)
                self.assertGreater(len(res.missing_markers), 0)

    def test_07_absent_default_donor_falls_back_to_clean_room(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            fake_paths = mock.Mock(work_root=Path(tmp))
            with mock.patch(
                "fx3_safety.realhw_switch_vh_af_stdadj_bracket_tcub_copy_slot_and_128gate_guard.resolve_donor_thermal_power_paths",
                return_value=fake_paths,
            ):
                with mock.patch.dict(
                    os.environ,
                    {ENV_FORCE_CLEAN_ROOM: "0", ENV_CLEAN_ROOM_TEST_PHASE297: "0"},
                ):
                    res = audit_phase297_donor_contracts(force_clean_room=False)
                    self.assertTrue(res.valid)
                    self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")
                    self.assertIn("CLEAN_ROOM_SYNTHETIC", res.warnings[0])

    def test_08_donor_audit_respects_local_or_clean_mode_and_budget(self) -> None:
        res = audit_phase297_donor_contracts()
        self.assertTrue(res.valid)
        self.assertEqual(res.raw_firmware_bytes_leaked, 0)
        budget = (
            DONOR_CHECK_CI_MAX_SECONDS_PHASE297
            if os.environ.get("GITHUB_ACTIONS", "").strip().lower() == "true"
            else DONOR_CHECK_MAX_SECONDS_PHASE297
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
                    (b"Switch V/H AF Area",),
                    "fake marker",
                )
            }
            res = audit_phase297_donor_contracts(
                work_root=Path(tmp),
                force_clean_room=False,
                donor_specs_override=override,
            )
            self.assertFalse(res.valid)
            self.assertEqual(res.status, STATUS_BLOCKED_PHASE297_DONOR_INTEGRITY)

    def test_10_ci_timing_budget_headroom(self) -> None:
        with mock.patch.dict(os.environ, {"GITHUB_ACTIONS": "true"}):
            res = audit_phase297_donor_contracts(force_clean_room=True)
            self.assertTrue(res.within_budget_200ms)
            self.assertEqual(DONOR_CHECK_CI_MAX_SECONDS_PHASE297, 15.0)

    def test_11_dataclasses_are_frozen(self) -> None:
        g127 = verify_switch_vh_af_and_exposure_stdadj_guard()
        g128 = verify_tcub_format_and_playback_copy_slot_guard()
        self.assertTrue(dataclasses.is_dataclass(g127))
        self.assertTrue(dataclasses.is_dataclass(g128))
        with self.assertRaises(dataclasses.FrozenInstanceError):
            g127.valid = False  # type: ignore[misc]
        with self.assertRaises(dataclasses.FrozenInstanceError):
            g128.valid = False  # type: ignore[misc]


class TestGateG127SwitchVhAfFocusLimitStdAdjBracket(unittest.TestCase):
    def test_12_default_still_afc_guard_passes(self) -> None:
        res = verify_switch_vh_af_and_exposure_stdadj_guard()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_VERIFIED_G127)
        self.assertEqual(res.effective_switch_vh_af_area, SWITCH_VH_AF_OFF_G127)
        self.assertEqual(res.enabled_focus_area_limit_count, 14)
        self.assertEqual(res.exposure_std_adjust_metering_mode_count, 5)
        self.assertEqual(res.effective_bracket_selftimer, BRACKET_SELFTIMER_OFF_G127)
        self.assertEqual(res.effective_bracket_order, BRACKET_ORDER_ZERO_MINUS_PLUS_G127)
        self.assertEqual(res.matrix_states_checked, 384)

    def test_13_switch_vh_af_active_in_still_afc_3_orientations(self) -> None:
        for orient in (
            GRAVITY_ORIENTATION_0_DEG_G127,
            GRAVITY_ORIENTATION_90_DEG_G127,
            GRAVITY_ORIENTATION_270_DEG_G127,
        ):
            for mode in (SWITCH_VH_AF_POINT_ONLY_G127, SWITCH_VH_AF_POINT_AND_AREA_G127):
                res = verify_switch_vh_af_and_exposure_stdadj_guard(
                    shoot_mode=SHOOT_MODE_M_PHASE297,
                    focus_mode="AF-C",
                    gravity_orientation=orient,
                    requested_switch_vh_af_area=mode,
                    switch_vh_af_trigger_requested=True,
                )
                self.assertTrue(res.valid)
                self.assertTrue(res.vh_af_orientation_switch_active)
                self.assertEqual(res.vh_af_lockout_reasons, ())

    def test_14_vertical_pitch_invalid_blocks_switch(self) -> None:
        res = verify_switch_vh_af_and_exposure_stdadj_guard(
            shoot_mode=SHOOT_MODE_M_PHASE297,
            focus_mode="AF-C",
            gravity_orientation=GRAVITY_ORIENTATION_INVALID_G127,
            requested_switch_vh_af_area=SWITCH_VH_AF_POINT_AND_AREA_G127,
            switch_vh_af_trigger_requested=True,
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_G127_SWITCH_VH_AF_LOCKOUT_OR_PITCH_INVALID)
        self.assertIn("VERTICAL_PITCH_INVALID", res.vh_af_lockout_reasons)

    def test_15_lockout_movie_and_sq_modes(self) -> None:
        for sm in (SHOOT_MODE_MOVIE_PHASE297, SHOOT_MODE_SQ_PHASE297):
            res = verify_switch_vh_af_and_exposure_stdadj_guard(
                shoot_mode=sm,
                focus_mode="AF-C",
                gravity_orientation=GRAVITY_ORIENTATION_90_DEG_G127,
                requested_switch_vh_af_area=SWITCH_VH_AF_POINT_ONLY_G127,
                switch_vh_af_trigger_requested=True,
            )
            self.assertFalse(res.valid)
            self.assertEqual(res.status, STATUS_BLOCKED_G127_SWITCH_VH_AF_LOCKOUT_OR_PITCH_INVALID)
            self.assertIn("MOVIE_OR_SQ_MODE", res.vh_af_lockout_reasons)

    def test_16_lockout_non_afc_focus_modes(self) -> None:
        for fm in ("AF-S", "AF-A", "DMF", "MF"):
            res = verify_switch_vh_af_and_exposure_stdadj_guard(
                shoot_mode=SHOOT_MODE_P_PHASE297,
                focus_mode=fm,
                gravity_orientation=GRAVITY_ORIENTATION_90_DEG_G127,
                requested_switch_vh_af_area=SWITCH_VH_AF_POINT_ONLY_G127,
                switch_vh_af_trigger_requested=True,
            )
            self.assertFalse(res.valid)
            self.assertIn("FOCUS_MODE_NOT_AF_C", res.vh_af_lockout_reasons)

    def test_17_lockout_iauto_digital_zoom_active_af(self) -> None:
        for kwargs, reason in [
            ({"shoot_mode": SHOOT_MODE_INTELLIGENT_AUTO_PHASE297}, "INTELLIGENT_AUTO"),
            ({"digital_zoom_active": True}, "DIGITAL_ZOOM_ACTIVE"),
            ({"af_in_progress": True}, "AF_ACTIVE"),
        ]:
            res = verify_switch_vh_af_and_exposure_stdadj_guard(
                focus_mode="AF-C",
                gravity_orientation=GRAVITY_ORIENTATION_90_DEG_G127,
                requested_switch_vh_af_area=SWITCH_VH_AF_POINT_ONLY_G127,
                switch_vh_af_trigger_requested=True,
                **kwargs,
            )
            self.assertFalse(res.valid)
            self.assertIn(reason, res.vh_af_lockout_reasons)

    def test_18_lockout_burst_selftimer_focus_magnifier(self) -> None:
        for kwargs, reason in [
            ({"continuous_shooting_active": True}, "CONTINUOUS_SHOOTING"),
            ({"self_timer_countdown_active": True}, "SELF_TIMER_COUNTDOWN"),
            ({"focus_magnifier_active": True}, "FOCUS_MAGNIFIER_ACTIVE"),
        ]:
            res = verify_switch_vh_af_and_exposure_stdadj_guard(
                shoot_mode=SHOOT_MODE_M_PHASE297,
                focus_mode="AF-C",
                gravity_orientation=GRAVITY_ORIENTATION_270_DEG_G127,
                requested_switch_vh_af_area=SWITCH_VH_AF_POINT_AND_AREA_G127,
                switch_vh_af_trigger_requested=True,
                **kwargs,
            )
            self.assertFalse(res.valid)
            self.assertIn(reason, res.vh_af_lockout_reasons)

    def test_19_mode_change_clears_stored_points_and_rejects_persist_claim(self) -> None:
        ok = verify_switch_vh_af_and_exposure_stdadj_guard(
            previous_switch_vh_af_area=SWITCH_VH_AF_POINT_ONLY_G127,
            requested_switch_vh_af_area=SWITCH_VH_AF_POINT_AND_AREA_G127,
        )
        self.assertTrue(ok.valid)
        self.assertTrue(ok.stored_points_cleared_on_mode_change)

        bad = verify_switch_vh_af_and_exposure_stdadj_guard(
            previous_switch_vh_af_area=SWITCH_VH_AF_POINT_ONLY_G127,
            requested_switch_vh_af_area=SWITCH_VH_AF_POINT_AND_AREA_G127,
            claimed_stored_points_persist_across_mode_change=True,
        )
        self.assertFalse(bad.valid)
        self.assertEqual(bad.status, STATUS_BLOCKED_G127_SWITCH_VH_AF_LOCKOUT_OR_PITCH_INVALID)

    def test_20_switch_vh_af_resets_on_cam_settings_reset(self) -> None:
        res = verify_switch_vh_af_and_exposure_stdadj_guard(
            requested_switch_vh_af_area=SWITCH_VH_AF_POINT_AND_AREA_G127,
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE297,
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.effective_switch_vh_af_area, SWITCH_VH_AF_OFF_G127)
        self.assertTrue(res.switch_vh_af_reset_on_cam_reset)

    def test_21_focus_area_limit_exact_14_options(self) -> None:
        self.assertEqual(len(FOCUS_AREA_LIMIT_14_OPTIONS_G127), 14)
        self.assertEqual(len(FOCUS_AREA_LIMIT_TRACKING_OPTIONS_G127), 7)
        res = verify_switch_vh_af_and_exposure_stdadj_guard(
            requested_focus_area_limit_options=("Wide", "Spot: M"),
            focus_area_limit_switch_requested=True,
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.enabled_focus_area_limit_count, 2)

    def test_22_focus_area_limit_dormant_xl_xs_custom_rejected(self) -> None:
        for dormant in DORMANT_FOCUS_AREA_LIMIT_OPTIONS_G127:
            res = verify_switch_vh_af_and_exposure_stdadj_guard(
                requested_focus_area_limit_options=("Wide", "Zone", dormant),
            )
            self.assertFalse(res.valid)
            self.assertEqual(
                res.status, STATUS_BLOCKED_G127_FOCUS_AREA_LIMIT_DORMANT_OR_MIN2_VIOLATION
            )

    def test_23_focus_area_limit_less_than_2_rejected(self) -> None:
        for opts in [("Wide",), ()]:
            res = verify_switch_vh_af_and_exposure_stdadj_guard(
                requested_focus_area_limit_options=opts,
                focus_area_limit_switch_requested=True,
            )
            self.assertFalse(res.valid)
            self.assertEqual(
                res.status, STATUS_BLOCKED_G127_FOCUS_AREA_LIMIT_DORMANT_OR_MIN2_VIOLATION
            )

    def test_24_focus_area_tracking_rejected_in_movie_sq(self) -> None:
        for sm in (SHOOT_MODE_MOVIE_PHASE297, SHOOT_MODE_SQ_PHASE297):
            res = verify_switch_vh_af_and_exposure_stdadj_guard(
                shoot_mode=sm,
                focus_area_tracking_select_requested=True,
            )
            self.assertFalse(res.valid)
            self.assertFalse(res.focus_area_limit_tracking_available)
            self.assertEqual(
                res.status, STATUS_BLOCKED_G127_FOCUS_AREA_LIMIT_DORMANT_OR_MIN2_VIOLATION
            )

    def test_25_exposure_std_adjust_all_5_metering_modes_and_13_steps(self) -> None:
        self.assertEqual(len(EXPOSURE_STD_ADJ_5_METERING_MODES_G127), 5)
        self.assertEqual(len(EXPOSURE_STD_ADJ_VALID_SIXTHS_G127), EXPOSURE_STD_ADJ_STEP_COUNT_G127)
        self.assertEqual(EXPOSURE_STD_ADJ_VALID_SIXTHS_G127, tuple(range(-6, 7)))
        steps = {
            "Multi": -6,
            "Center": -1,
            "Spot": 3,
            "Entire Screen Avg.": 2,
            "Highlight": 6,
        }
        res = verify_switch_vh_af_and_exposure_stdadj_guard(
            requested_exposure_std_adjust_sixths=steps,
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.exposure_std_adjust_sixths_by_mode, steps)
        self.assertAlmostEqual(res.exposure_std_adjust_ev_by_mode["Multi"], -1.0, places=3)
        self.assertAlmostEqual(res.exposure_std_adjust_ev_by_mode["Spot"], 0.5, places=3)
        self.assertAlmostEqual(res.exposure_std_adjust_ev_by_mode["Highlight"], 1.0, places=3)
        self.assertTrue(res.mm_and_spot_ael_shifted)
        self.assertTrue(res.exposure_std_adjust_independent_of_exp_comp)

    def test_26_exposure_std_adjust_out_of_range_and_unknown_mode_rejected(self) -> None:
        for bad in ({"Multi": 7}, {"Spot": -7}, {"Multi": True}, {"UnknownMode": 1}):
            res = verify_switch_vh_af_and_exposure_stdadj_guard(
                requested_exposure_std_adjust_sixths=bad,  # type: ignore[arg-type]
            )
            self.assertFalse(res.valid)
            self.assertEqual(res.status, STATUS_BLOCKED_G127_TELEMETRY_INVALID)

    def test_27_exposure_std_adjust_rejects_4mode_claim(self) -> None:
        res = verify_switch_vh_af_and_exposure_stdadj_guard(
            claimed_only_4_metering_modes=True,
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            res.status, STATUS_BLOCKED_G127_EXPOSURE_STD_ADJ_5MODE_OR_RESET_VIOLATION
        )

    def test_28_exposure_std_adjust_survives_cam_reset_and_wipes_on_initialize(self) -> None:
        steps = {"Multi": 2, "Center": -2, "Spot": 4, "Entire Screen Avg.": -3, "Highlight": 5}
        cam_rst = verify_switch_vh_af_and_exposure_stdadj_guard(
            requested_exposure_std_adjust_sixths=steps,
            requested_focus_area_color=FOCUS_AREA_COLOR_RED_G127,
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE297,
        )
        self.assertTrue(cam_rst.valid)
        self.assertTrue(cam_rst.exposure_std_adjust_survived_cam_reset)
        self.assertEqual(cam_rst.exposure_std_adjust_sixths_by_mode, steps)
        self.assertEqual(cam_rst.effective_focus_area_color, FOCUS_AREA_COLOR_RED_G127)

        init_rst = verify_switch_vh_af_and_exposure_stdadj_guard(
            requested_exposure_std_adjust_sixths=steps,
            requested_focus_area_color=FOCUS_AREA_COLOR_RED_G127,
            reset_action=RESET_ACTION_INITIALIZE_PHASE297,
        )
        self.assertTrue(init_rst.valid)
        self.assertFalse(init_rst.exposure_std_adjust_survived_cam_reset)
        self.assertEqual(
            init_rst.exposure_std_adjust_sixths_by_mode,
            {m: 0 for m in EXPOSURE_STD_ADJ_5_METERING_MODES_G127},
        )
        self.assertEqual(init_rst.effective_focus_area_color, FOCUS_AREA_COLOR_WHITE_G127)

    def test_29_exposure_std_adjust_reset_spoof_and_exp_comp_stack_rejected(self) -> None:
        r1 = verify_switch_vh_af_and_exposure_stdadj_guard(
            claimed_exposure_std_adj_resets_on_cam_settings_reset=True,
        )
        r2 = verify_switch_vh_af_and_exposure_stdadj_guard(
            claimed_exposure_std_adj_stacks_into_exp_comp=True,
        )
        r3 = verify_switch_vh_af_and_exposure_stdadj_guard(
            exposure_std_adjust_changed_mid_bracket=True,
            claimed_bracket_count_continues_after_std_adj_change=True,
        )
        for r in (r1, r2, r3):
            self.assertFalse(r.valid)
            self.assertEqual(
                r.status, STATUS_BLOCKED_G127_EXPOSURE_STD_ADJ_5MODE_OR_RESET_VIOLATION
            )

    def test_30_bracket_settings_still_options_and_reset(self) -> None:
        for timer in ALLOWED_BRACKET_SELFTIMER_OPTIONS_G127:
            for order in ALLOWED_BRACKET_ORDERS_G127:
                res = verify_switch_vh_af_and_exposure_stdadj_guard(
                    shoot_mode=SHOOT_MODE_M_PHASE297,
                    requested_bracket_selftimer=timer,
                    requested_bracket_order=order,
                    bracket_settings_use_requested=True,
                )
                self.assertTrue(res.valid)
                self.assertEqual(res.effective_bracket_selftimer, timer)
                self.assertEqual(res.effective_bracket_order, order)

        rst = verify_switch_vh_af_and_exposure_stdadj_guard(
            requested_bracket_selftimer=BRACKET_SELFTIMER_10SEC_G127,
            requested_bracket_order=BRACKET_ORDER_MINUS_ZERO_PLUS_G127,
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE297,
        )
        self.assertTrue(rst.valid)
        self.assertEqual(rst.effective_bracket_selftimer, BRACKET_SELFTIMER_OFF_G127)
        self.assertEqual(rst.effective_bracket_order, BRACKET_ORDER_ZERO_MINUS_PLUS_G127)

    def test_31_bracket_settings_blocked_in_movie_and_fx6(self) -> None:
        mv = verify_switch_vh_af_and_exposure_stdadj_guard(
            shoot_mode=SHOOT_MODE_MOVIE_PHASE297,
            bracket_settings_use_requested=True,
        )
        self.assertFalse(mv.valid)
        self.assertEqual(mv.status, STATUS_BLOCKED_G127_BRACKET_SETTINGS_OR_FX6_CROSSWIRE_VIOLATION)

        fx6 = verify_switch_vh_af_and_exposure_stdadj_guard(
            target_model=FX6_MODEL_NAME_PHASE297,
            bracket_settings_use_requested=True,
        )
        self.assertFalse(fx6.valid)
        self.assertEqual(fx6.status, STATUS_BLOCKED_G127_BRACKET_SETTINGS_OR_FX6_CROSSWIRE_VIOLATION)

        claim = verify_switch_vh_af_and_exposure_stdadj_guard(
            claimed_fx6_has_vh_switch_limit_std_adj_or_bracket=True,
        )
        self.assertFalse(claim.valid)

    def test_32_g127_384_state_matrix_holds(self) -> None:
        m = compute_switch_vh_af_and_exposure_stdadj_matrix()
        self.assertEqual(m["states_checked"], 384)
        self.assertTrue(m["all_invariants_hold"])
        self.assertGreater(m["vh_active_count"], 0)
        self.assertGreater(m["pitch_invalid_blocked"], 0)
        self.assertGreater(m["std_adj_survived_cam_reset_count"], 0)

    def test_33_g127_invalid_identity_fails_closed(self) -> None:
        res = verify_switch_vh_af_and_exposure_stdadj_guard(
            body_model_name="ILCE-7M4",
            body_model_id=0x1234,
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_G127_TELEMETRY_INVALID)

    def test_34_evaluate_g127_blocks_persistent_emmc_write(self) -> None:
        v, r = evaluate_g127_switch_vh_af_and_exposure_stdadj_guard(
            force_clean_room=True,
            request_persistent_emmc_writes=True,
        )
        self.assertFalse(v.passed)
        self.assertFalse(r.valid)
        self.assertEqual(r.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)


class TestGateG128TcubFormatAndPlaybackCopySlot(unittest.TestCase):
    def test_35_default_g128_guard_passes(self) -> None:
        res = verify_tcub_format_and_playback_copy_slot_guard()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_VERIFIED_G128)
        self.assertEqual(len(TCUB_6_ITEMS_G128), 6)
        self.assertEqual(res.effective_tc_format, TC_FORMAT_DF_G128)
        self.assertEqual(res.effective_tcub_disp_setting, TCUB_DISP_TC_G128)
        self.assertEqual(res.effective_select_playback_media, MEDIA_SLOT_1_G128)
        self.assertEqual(res.copy_direction_label, "Slot 1 -> Slot 2")
        self.assertEqual(res.slot1_data_sector_writes, 0)
        self.assertFalse(res.slot1_avf_info_mutated)
        self.assertEqual(res.matrix_states_checked, 384)

    def test_36_all_6_tcub_items_and_disp_survive_cam_reset(self) -> None:
        cam_rst = verify_tcub_format_and_playback_copy_slot_guard(
            requested_tc_preset="01:23:45.12",
            requested_ub_preset="AB CD EF 01",
            requested_tc_format=TC_FORMAT_NDF_G128,
            requested_tc_run=TC_RUN_FREE_G128,
            requested_tc_make=TC_MAKE_REGENERATE_G128,
            requested_ub_time_rec="On",
            requested_tcub_disp_setting=TCUB_DISP_UBIT_G128,
            requested_slide_show_repeat="On",
            requested_slide_show_interval=SLIDE_SHOW_INTERVAL_10SEC_G128,
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE297,
        )
        self.assertTrue(cam_rst.valid)
        self.assertTrue(cam_rst.tcub_6_items_survived_cam_reset)
        self.assertTrue(cam_rst.tcub_disp_survived_cam_reset)
        self.assertTrue(cam_rst.slide_show_survived_cam_reset)
        self.assertEqual(cam_rst.effective_tc_preset, "01:23:45.12")
        self.assertEqual(cam_rst.effective_ub_preset, "AB CD EF 01")
        self.assertEqual(cam_rst.effective_tc_format, TC_FORMAT_NDF_G128)
        self.assertEqual(cam_rst.effective_tc_run, TC_RUN_FREE_G128)
        self.assertEqual(cam_rst.effective_tc_make, TC_MAKE_REGENERATE_G128)
        self.assertEqual(cam_rst.effective_ub_time_rec, "On")
        self.assertEqual(cam_rst.effective_tcub_disp_setting, TCUB_DISP_UBIT_G128)
        self.assertEqual(cam_rst.effective_slide_show_repeat, "On")
        self.assertEqual(cam_rst.effective_slide_show_interval, SLIDE_SHOW_INTERVAL_10SEC_G128)

    def test_37_tcub_and_slideshow_reset_only_on_initialize(self) -> None:
        init_rst = verify_tcub_format_and_playback_copy_slot_guard(
            requested_tc_preset="01:23:45.12",
            requested_ub_preset="AB CD EF 01",
            requested_tc_format=TC_FORMAT_NDF_G128,
            requested_tc_run=TC_RUN_FREE_G128,
            requested_tc_make=TC_MAKE_REGENERATE_G128,
            requested_ub_time_rec="On",
            requested_tcub_disp_setting=TCUB_DISP_COUNTER_G128,
            requested_slide_show_repeat="On",
            requested_slide_show_interval=SLIDE_SHOW_INTERVAL_30SEC_G128,
            reset_action=RESET_ACTION_INITIALIZE_PHASE297,
        )
        self.assertTrue(init_rst.valid)
        self.assertFalse(init_rst.tcub_6_items_survived_cam_reset)
        self.assertEqual(init_rst.effective_tc_preset, "00:00:00.00")
        self.assertEqual(init_rst.effective_ub_preset, "00 00 00 00")
        self.assertEqual(init_rst.effective_tc_format, TC_FORMAT_DF_G128)
        self.assertEqual(init_rst.effective_tc_run, TC_RUN_REC_G128)
        self.assertEqual(init_rst.effective_tc_make, TC_MAKE_PRESET_G128)
        self.assertEqual(init_rst.effective_ub_time_rec, "Off")
        self.assertEqual(init_rst.effective_tcub_disp_setting, TCUB_DISP_TC_G128)
        self.assertEqual(init_rst.effective_slide_show_repeat, "Off")
        self.assertEqual(init_rst.effective_slide_show_interval, SLIDE_SHOW_INTERVAL_3SEC_G128)

    def test_38_tcub_reset_spoof_rejected(self) -> None:
        res = verify_tcub_format_and_playback_copy_slot_guard(
            claimed_tcub_resets_on_cam_settings_reset=True,
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            res.status,
            STATUS_BLOCKED_G128_TCUB_RESET_PERSISTENCE_OR_PLAYBACK_TOGGLE_VIOLATION,
        )

    def test_39_tcub_disp_playback_toggle_movie_only(self) -> None:
        mv = verify_tcub_format_and_playback_copy_slot_guard(
            playback_active=True,
            playback_media_is_movie=True,
            tcub_disp_toggle_in_playback_requested=True,
        )
        self.assertTrue(mv.valid)
        self.assertTrue(mv.tcub_disp_playback_toggle_allowed)

        still = verify_tcub_format_and_playback_copy_slot_guard(
            playback_active=True,
            playback_media_is_movie=False,
            tcub_disp_toggle_in_playback_requested=True,
        )
        self.assertFalse(still.valid)
        self.assertEqual(
            still.status,
            STATUS_BLOCKED_G128_TCUB_RESET_PERSISTENCE_OR_PLAYBACK_TOGGLE_VIOLATION,
        )

    def test_40_fx3_has_no_bnc_tc_port_vs_fx6(self) -> None:
        ok = verify_tcub_format_and_playback_copy_slot_guard()
        self.assertFalse(ok.fx3_has_bnc_tc_port)
        self.assertTrue(ok.fx6_has_bnc_tc_port)

        bad = verify_tcub_format_and_playback_copy_slot_guard(
            claimed_fx3_has_bnc_tc_port=True,
        )
        self.assertFalse(bad.valid)
        self.assertEqual(
            bad.status,
            STATUS_BLOCKED_G128_TCUB_RESET_PERSISTENCE_OR_PLAYBACK_TOGGLE_VIOLATION,
        )

    def test_41_tc_format_forced_ndf_in_2398p_and_2400p(self) -> None:
        for fr in ("23.98p", "24.00p"):
            res_ndf = verify_tcub_format_and_playback_copy_slot_guard(
                tv_system=TV_SYSTEM_NTSC_G128,
                frame_rate=fr,
                requested_tc_format=TC_FORMAT_NDF_G128,
            )
            self.assertTrue(res_ndf.valid)
            self.assertTrue(res_ndf.tc_format_forced_ndf)
            self.assertEqual(res_ndf.effective_tc_format, TC_FORMAT_NDF_G128)

            res_df_req = verify_tcub_format_and_playback_copy_slot_guard(
                tv_system=TV_SYSTEM_NTSC_G128,
                frame_rate=fr,
                requested_tc_format=TC_FORMAT_DF_G128,
                tc_format_change_requested=True,
            )
            self.assertFalse(res_df_req.valid)
            self.assertEqual(
                res_df_req.status,
                STATUS_BLOCKED_G128_TC_FORMAT_PAL_OR_24P_NDF_LOCK_VIOLATION,
            )

    def test_42_tc_format_hidden_in_pal(self) -> None:
        res_pal = verify_tcub_format_and_playback_copy_slot_guard(
            tv_system=TV_SYSTEM_PAL_G128,
            frame_rate="25p",
        )
        self.assertTrue(res_pal.valid)
        self.assertFalse(res_pal.tc_format_menu_visible)

        res_pal_mut = verify_tcub_format_and_playback_copy_slot_guard(
            tv_system=TV_SYSTEM_PAL_G128,
            frame_rate="25p",
            tc_format_change_requested=True,
        )
        self.assertFalse(res_pal_mut.valid)
        self.assertEqual(
            res_pal_mut.status,
            STATUS_BLOCKED_G128_TC_FORMAT_PAL_OR_24P_NDF_LOCK_VIOLATION,
        )

    def test_43_copy_slot1_to_slot2_is_allowed_read_only_on_slot1(self) -> None:
        res = verify_tcub_format_and_playback_copy_slot_guard(
            requested_select_playback_media=MEDIA_SLOT_1_G128,
            slot_1_contains_tier0_vault=True,
            copy_requested=True,
            copy_includes_movie=True,
            destination_card_speed_class="CFexpress Type A",
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.copy_source_slot, MEDIA_SLOT_1_G128)
        self.assertEqual(res.copy_destination_slot, MEDIA_SLOT_2_G128)
        self.assertEqual(res.copy_direction_label, "Slot 1 -> Slot 2")
        self.assertFalse(res.copy_blocked_by_slot1_vault_firewall)
        self.assertEqual(res.slot1_data_sector_writes, 0)
        self.assertFalse(res.slot1_avf_info_mutated)

    def test_44_copy_slot2_to_slot1_blocked_fail_closed_ebusy_on_tier0_vault(self) -> None:
        res = verify_tcub_format_and_playback_copy_slot_guard(
            requested_select_playback_media=MEDIA_SLOT_2_G128,
            slot_1_contains_tier0_vault=True,
            slot_1_write_protected=False,
            copy_requested=True,
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            res.status,
            STATUS_BLOCKED_G128_SLOT2_TO_SLOT1_VAULT_COPY_FIREWALL_VIOLATION,
        )
        self.assertEqual(res.copy_direction_label, "Slot 2 -> Slot 1")
        self.assertTrue(res.copy_blocked_by_slot1_vault_firewall)
        self.assertEqual(res.block_errno, "EBUSY")
        self.assertEqual(res.slot1_data_sector_writes, 0)
        self.assertFalse(res.slot1_avf_info_mutated)

    def test_45_copy_slot2_to_slot1_blocked_fail_closed_erofs_on_write_protect(self) -> None:
        res = verify_tcub_format_and_playback_copy_slot_guard(
            requested_select_playback_media=MEDIA_SLOT_2_G128,
            slot_1_contains_tier0_vault=False,
            slot_1_write_protected=True,
            copy_requested=True,
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.block_errno, "EROFS")
        self.assertEqual(res.slot1_data_sector_writes, 0)

    def test_46_copy_slot2_to_slot1_allowed_only_when_slot1_not_vault_and_not_ro(self) -> None:
        res = verify_tcub_format_and_playback_copy_slot_guard(
            requested_select_playback_media=MEDIA_SLOT_2_G128,
            slot_1_contains_tier0_vault=False,
            slot_1_write_protected=False,
            copy_requested=True,
        )
        self.assertTrue(res.valid)
        self.assertFalse(res.copy_blocked_by_slot1_vault_firewall)

    def test_47_copy_protect_flag_strip_and_battery_speed_gates(self) -> None:
        prot = verify_tcub_format_and_playback_copy_slot_guard(
            claimed_copy_preserves_protect_flags=True,
        )
        self.assertFalse(prot.valid)
        self.assertEqual(
            prot.status,
            STATUS_BLOCKED_G128_SLOT2_TO_SLOT1_VAULT_COPY_FIREWALL_VIOLATION,
        )

        low_batt = verify_tcub_format_and_playback_copy_slot_guard(
            requested_select_playback_media=MEDIA_SLOT_1_G128,
            copy_requested=True,
            battery_sufficient_for_copy=False,
        )
        self.assertFalse(low_batt.valid)
        self.assertEqual(
            low_batt.status,
            STATUS_BLOCKED_G128_COPY_BATTERY_SPEED_OR_SLIDESHOW_FX6_VIOLATION,
        )

        slow_card = verify_tcub_format_and_playback_copy_slot_guard(
            requested_select_playback_media=MEDIA_SLOT_1_G128,
            copy_requested=True,
            copy_includes_movie=True,
            destination_card_speed_class="SDHC Class4",
        )
        self.assertFalse(slow_card.valid)
        self.assertEqual(
            slow_card.status,
            STATUS_BLOCKED_G128_COPY_BATTERY_SPEED_OR_SLIDESHOW_FX6_VIOLATION,
        )

    def test_48_slideshow_view_modes_intervals_and_sleep_bypass(self) -> None:
        for vm in ALLOWED_SLIDE_SHOW_VIEW_MODES_G128:
            for interval in ALLOWED_SLIDE_SHOW_INTERVALS_G128:
                ok = verify_tcub_format_and_playback_copy_slot_guard(
                    slide_show_start_requested=True,
                    slide_show_view_mode=vm,
                    requested_slide_show_interval=interval,
                    slide_show_active=True,
                )
                self.assertTrue(ok.valid)
                self.assertTrue(ok.power_save_sleep_bypassed_during_slideshow)

        for bad_vm in DISALLOWED_SLIDE_SHOW_VIEW_MODES_G128:
            bad = verify_tcub_format_and_playback_copy_slot_guard(
                slide_show_start_requested=True,
                slide_show_view_mode=bad_vm,
            )
            self.assertFalse(bad.valid)
            self.assertEqual(
                bad.status,
                STATUS_BLOCKED_G128_COPY_BATTERY_SPEED_OR_SLIDESHOW_FX6_VIOLATION,
            )

        sleep_spoof = verify_tcub_format_and_playback_copy_slot_guard(
            claimed_power_save_triggers_during_slideshow=True,
        )
        self.assertFalse(sleep_spoof.valid)

    def test_49_fx6_lacks_slideshow_and_dormant_copy_clip_rejected(self) -> None:
        for kw in [
            {"target_model": FX6_MODEL_NAME_PHASE297, "fx6_copy_clip_requested": True},
            {"target_model": FX6_MODEL_NAME_PHASE297, "slide_show_start_requested": True},
            {"claimed_fx6_has_slideshow_or_copy_clip": True},
        ]:
            res = verify_tcub_format_and_playback_copy_slot_guard(**kw)  # type: ignore[arg-type]
            self.assertFalse(res.valid)
            self.assertEqual(
                res.status,
                STATUS_BLOCKED_G128_COPY_BATTERY_SPEED_OR_SLIDESHOW_FX6_VIOLATION,
            )

    def test_50_g128_384_state_matrix_and_invalid_telemetry(self) -> None:
        m = compute_tcub_and_playback_copy_slot_matrix()
        self.assertEqual(m["states_checked"], 384)
        self.assertTrue(m["all_invariants_hold"])
        self.assertGreater(m["ndf_locked_24p_count"], 0)
        self.assertGreater(m["pal_hidden_count"], 0)
        self.assertGreater(m["slot2_to_slot1_blocked_count"], 0)

        bad = verify_tcub_format_and_playback_copy_slot_guard(
            requested_tc_preset="INVALID",
            requested_ub_preset="ZZ",
        )
        self.assertFalse(bad.valid)
        self.assertEqual(bad.status, STATUS_BLOCKED_G128_TELEMETRY_INVALID)

    def test_51_evaluate_g128_blocks_persistent_emmc_write(self) -> None:
        v, r = evaluate_g128_tcub_format_and_playback_copy_slot_guard(
            force_clean_room=True,
            request_persistent_emmc_writes=True,
        )
        self.assertFalse(v.passed)
        self.assertFalse(r.valid)
        self.assertEqual(r.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)


class TestUnified128GateEngineAndCli(unittest.TestCase):
    def test_52_stub_128gate_offline_125_of_128(self) -> None:
        rep = evaluate_128gate_preflight(
            force_clean_room=True,
            master_126_override=_make_stub_master126(dry_run=False),
        )
        self.assertEqual(rep.summary["total_gates"], 128)
        self.assertEqual(rep.summary["verified_gates"], 125)
        self.assertTrue(rep.offline_125_gates_verified)
        self.assertFalse(rep.all_128_gates_verified)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.cross_model_flash_authorized)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)
        self.assertEqual(rep.status, "VERIFIED_125_OF_128_AWAITING_PHYSICAL_TIER0")
        self.assertEqual(len(rep.gates), 128)

    def test_53_stub_128gate_dry_run_128_of_128(self) -> None:
        rep = evaluate_128_master_safety_gates(
            force_clean_room=True,
            simulate_bench_dry_run=True,
            master_126_override=_make_stub_master126(dry_run=True),
        )
        self.assertEqual(rep.summary["verified_gates"], 128)
        self.assertTrue(rep.all_128_gates_verified)
        self.assertTrue(rep.dry_run_rehearsal_only)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertEqual(rep.status, "VERIFIED_ALL_128_GATES_DRY_RUN_SIMULATED_BACKUP")

    def test_54_g127_failure_propagates_to_128gate_report(self) -> None:
        rep = evaluate_128gate_preflight(
            force_clean_room=True,
            master_126_override=_make_stub_master126(dry_run=True),
            switch_vh_af_exposure_stdadj_kwargs={"claimed_only_4_metering_modes": True},
        )
        self.assertFalse(rep.g127_to_g128_all_passed)
        self.assertFalse(rep.all_128_gates_verified)
        self.assertEqual(
            rep.status, STATUS_BLOCKED_G127_EXPOSURE_STD_ADJ_5MODE_OR_RESET_VIOLATION
        )

    def test_55_g128_failure_propagates_to_128gate_report(self) -> None:
        rep = evaluate_128gate_preflight(
            force_clean_room=True,
            master_126_override=_make_stub_master126(dry_run=True),
            tcub_playback_copy_slot_kwargs={
                "requested_select_playback_media": MEDIA_SLOT_2_G128,
                "slot_1_contains_tier0_vault": True,
                "copy_requested": True,
            },
        )
        self.assertFalse(rep.g127_to_g128_all_passed)
        self.assertFalse(rep.all_128_gates_verified)
        self.assertEqual(
            rep.status,
            STATUS_BLOCKED_G128_SLOT2_TO_SLOT1_VAULT_COPY_FIREWALL_VIOLATION,
        )

    def test_56_persistent_emmc_write_blocks_128gate_report(self) -> None:
        rep = run_128_gate_preflight(
            force_clean_room=True,
            request_persistent_emmc_writes=True,
            master_126_override=_make_stub_master126(dry_run=True),
        )
        self.assertEqual(rep.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        self.assertFalse(rep.all_128_gates_verified)

    def test_57_real_chained_128gate_offline_and_dry_run(self) -> None:
        off = evaluate_128gate_preflight(DEFAULT_REPO_ROOT)
        self.assertEqual(off.summary["verified_gates"], 125)
        self.assertTrue(off.offline_125_gates_verified)
        self.assertFalse(off.overall_ready_for_hardware_attach)
        self.assertEqual(off.raw_firmware_bytes_leaked, 0)

        dry = evaluate_128gate_preflight(
            DEFAULT_REPO_ROOT, simulate_bench_dry_run=True
        )
        self.assertEqual(dry.summary["verified_gates"], 128)
        self.assertTrue(dry.all_128_gates_verified)
        self.assertFalse(dry.overall_ready_for_hardware_attach)
        self.assertFalse(dry.persistent_emmc_writes_authorized)
        self.assertFalse(dry.cross_model_flash_authorized)

    def test_58_cli_help_python314_percent_escaping(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            with self.assertRaises(SystemExit) as ctx:
                cli_main(["--help"])
        self.assertEqual(ctx.exception.code, 0)
        out = buf.getvalue()
        self.assertIn("verify-switch-vh-af-and-exposure-stdadj-guard", out)
        self.assertIn("verify-tcub-format-and-playback-copy-slot-guard", out)
        self.assertIn("verify-128-gates", out)

    def test_59_cli_g127_g128_summary_json_and_text(self) -> None:
        for cmd in (
            "verify-switch-vh-af-and-exposure-stdadj-guard",
            "verify-tcub-format-and-playback-copy-slot-guard",
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

    def test_60_cli_verify_128_gates_subprocess_uses_sys_executable(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONPATH"] = str(DEFAULT_REPO_ROOT / "outputs" / "fx3-safety")
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "fx3_safety",
                "verify-128-gates",
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
        self.assertEqual(payload["status"], "VERIFIED_ALL_128_GATES_DRY_RUN_SIMULATED_BACKUP")
        self.assertEqual(payload["summary"]["verified_gates"], 128)
        self.assertEqual(payload["g127_status"], STATUS_VERIFIED_G127)
        self.assertEqual(payload["g128_status"], STATUS_VERIFIED_G128)

    def test_61_module_direct_main_entrypoint(self) -> None:
        for gate_flag in ("g127", "g128", "128"):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = module_main(["--gate", gate_flag, "--clean-room", "--summary", "--json"])
            self.assertEqual(rc, 0)
            data = json.loads(buf.getvalue())
            self.assertEqual(
                data["status"] if gate_flag != "128" else data["g127_status"],
                STATUS_VERIFIED_G127 if gate_flag in ("g127", "128") else STATUS_VERIFIED_G128,
            )

    def test_62_g127_all_5_metering_mode_names_exact(self) -> None:
        self.assertEqual(
            EXPOSURE_STD_ADJ_5_METERING_MODES_G127,
            ("Multi", "Center", "Spot", "Entire Screen Avg.", "Highlight"),
        )

    def test_63_g127_focus_area_limit_14_names_exact(self) -> None:
        self.assertEqual(len(set(FOCUS_AREA_LIMIT_14_OPTIONS_G127)), 14)
        self.assertIn("Center Fix", FOCUS_AREA_LIMIT_14_OPTIONS_G127)
        self.assertIn("Tracking: Center Fix", FOCUS_AREA_LIMIT_14_OPTIONS_G127)

    def test_64_g127_all_3_switch_vh_af_modes_supported(self) -> None:
        self.assertEqual(
            ALLOWED_SWITCH_VH_AF_MODES_G127,
            ("Off", "AF Point Only", "AF Point + AF Area"),
        )

    def test_65_g127_all_4_gravity_orientations_supported(self) -> None:
        self.assertEqual(
            ALLOWED_GRAVITY_ORIENTATIONS_G127,
            ("0_DEGREES", "90_DEGREES", "270_DEGREES", "INVALID"),
        )

    def test_66_g127_all_13_ev_steps_in_one_sixth_ev_valid(self) -> None:
        for s in range(-6, 7):
            res = verify_switch_vh_af_and_exposure_stdadj_guard(
                requested_exposure_std_adjust_sixths={"Spot": s},
            )
            self.assertTrue(res.valid)
            self.assertEqual(res.exposure_std_adjust_sixths_by_mode["Spot"], s)

    def test_67_g127_focus_area_limit_resets_on_cam_settings_reset(self) -> None:
        res = verify_switch_vh_af_and_exposure_stdadj_guard(
            requested_focus_area_limit_options=("Wide", "Zone"),
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE297,
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.enabled_focus_area_limit_count, 14)
        self.assertTrue(res.focus_area_limit_reset_on_cam_reset)

    def test_68_g127_pasm_modes_all_allow_switch_vh_af(self) -> None:
        for sm in ("P", "A", "S", "M", "Still"):
            res = verify_switch_vh_af_and_exposure_stdadj_guard(
                shoot_mode=sm,
                focus_mode="AF-C",
                gravity_orientation=GRAVITY_ORIENTATION_90_DEG_G127,
                requested_switch_vh_af_area=SWITCH_VH_AF_POINT_ONLY_G127,
                switch_vh_af_trigger_requested=True,
            )
            self.assertTrue(res.valid)
            self.assertTrue(res.vh_af_orientation_switch_active)

    def test_69_g127_bracket_order_arrow_unicode_normalized(self) -> None:
        res = verify_switch_vh_af_and_exposure_stdadj_guard(
            requested_bracket_order="-→0→+",
            requested_bracket_selftimer=BRACKET_SELFTIMER_2SEC_G127,
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.effective_bracket_order, BRACKET_ORDER_MINUS_ZERO_PLUS_G127)
        self.assertEqual(res.effective_bracket_selftimer, BRACKET_SELFTIMER_2SEC_G127)

    def test_70_g127_fx6_lacks_flag_always_true(self) -> None:
        res = verify_switch_vh_af_and_exposure_stdadj_guard()
        self.assertTrue(res.fx6_lacks_vh_switch_limit_std_adj_bracket)

    def test_71_g128_tcub_6_items_constant_complete(self) -> None:
        self.assertEqual(
            TCUB_6_ITEMS_G128,
            (
                "Time Code Preset",
                "User Bit Preset",
                "Time Code Format",
                "Time Code Run",
                "Time Code Make",
                "User Bit Time Rec",
            ),
        )

    def test_72_g128_tcub_disp_settings_all_3_supported(self) -> None:
        self.assertEqual(ALLOWED_TCUB_DISP_SETTINGS_G128, ("Counter", "TC", "U-Bit"))
        for disp in ALLOWED_TCUB_DISP_SETTINGS_G128:
            res = verify_tcub_format_and_playback_copy_slot_guard(
                requested_tcub_disp_setting=disp,
            )
            self.assertTrue(res.valid)
            self.assertEqual(res.effective_tcub_disp_setting, disp)

    def test_73_g128_tc_format_df_allowed_in_ntsc_2997p_5994p(self) -> None:
        for fr in ("29.97p", "59.94p", "119.88p"):
            res = verify_tcub_format_and_playback_copy_slot_guard(
                tv_system=TV_SYSTEM_NTSC_G128,
                frame_rate=fr,
                requested_tc_format=TC_FORMAT_DF_G128,
                tc_format_change_requested=True,
            )
            self.assertTrue(res.valid)
            self.assertFalse(res.tc_format_forced_ndf)
            self.assertEqual(res.effective_tc_format, TC_FORMAT_DF_G128)

    def test_74_g128_allowed_dest_card_speed_classes_for_movie_copy(self) -> None:
        for sc in ALLOWED_DEST_CARD_SPEED_CLASSES_G128:
            res = verify_tcub_format_and_playback_copy_slot_guard(
                requested_select_playback_media=MEDIA_SLOT_1_G128,
                copy_requested=True,
                copy_includes_movie=True,
                destination_card_speed_class=sc,
            )
            self.assertTrue(res.valid)
            self.assertTrue(res.destination_card_speed_ok)

    def test_75_g128_slideshow_intervals_all_5_valid(self) -> None:
        self.assertEqual(
            ALLOWED_SLIDE_SHOW_INTERVALS_G128,
            ("1 Sec", "3 Sec", "5 Sec", "10 Sec", "30 Sec"),
        )
        for interval in (
            SLIDE_SHOW_INTERVAL_1SEC_G128,
            SLIDE_SHOW_INTERVAL_3SEC_G128,
            SLIDE_SHOW_INTERVAL_5SEC_G128,
            SLIDE_SHOW_INTERVAL_10SEC_G128,
            SLIDE_SHOW_INTERVAL_30SEC_G128,
        ):
            res = verify_tcub_format_and_playback_copy_slot_guard(
                requested_slide_show_interval=interval,
            )
            self.assertTrue(res.valid)
            self.assertEqual(res.effective_slide_show_interval, interval)

    def test_76_g128_still_copy_ignores_movie_card_speed_gate(self) -> None:
        res = verify_tcub_format_and_playback_copy_slot_guard(
            requested_select_playback_media=MEDIA_SLOT_1_G128,
            copy_requested=True,
            copy_includes_movie=False,
            destination_card_speed_class="SD Class4",
        )
        self.assertTrue(res.valid)

    def test_77_g128_select_playback_media_choices(self) -> None:
        self.assertEqual(ALLOWED_PLAYBACK_MEDIA_SLOTS_G128, ("Slot 1", "Slot 2"))

    def test_78_g128_tc_formats_choices(self) -> None:
        self.assertEqual(ALLOWED_TC_FORMATS_G128, ("DF", "NDF"))

    def test_79_g128_slideshow_inactive_by_default_no_sleep_bypass(self) -> None:
        res = verify_tcub_format_and_playback_copy_slot_guard(slide_show_active=False)
        self.assertTrue(res.valid)
        self.assertFalse(res.power_save_sleep_bypassed_during_slideshow)

    def test_80_g128_fx6_lacks_slideshow_flag_true(self) -> None:
        res = verify_tcub_format_and_playback_copy_slot_guard()
        self.assertTrue(res.fx6_lacks_slideshow_and_copy_clip)

    def test_81_g127_g128_gate_code_constants(self) -> None:
        self.assertEqual(
            G127_GATE_CODE,
            "GATE_G127_SWITCH_VH_AF_FOCUS_LIMIT_STD_ADJ_AND_BRACKET_GUARD",
        )
        self.assertEqual(
            G128_GATE_CODE,
            "GATE_G128_TCUB_FORMAT_PLAYBACK_COPY_DIRECTION_AND_SLIDESHOW_GUARD",
        )

    def test_82_128gate_report_json_serializable(self) -> None:
        rep = evaluate_128gate_preflight(
            force_clean_room=True,
            simulate_bench_dry_run=True,
            master_126_override=_make_stub_master126(dry_run=True),
        )
        blob = json.dumps(rep.to_dict())
        parsed = json.loads(blob)
        self.assertEqual(parsed["summary"]["total_gates"], 128)
        self.assertEqual(parsed["summary"]["verified_gates"], 128)

    def test_83_128gate_offline_cli_exit_zero_and_status(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cli_main(["verify-128-gates", "--clean-room", "--summary", "--json"])
        self.assertEqual(rc, 0)
        data = json.loads(buf.getvalue())
        self.assertEqual(data["status"], "VERIFIED_125_OF_128_AWAITING_PHYSICAL_TIER0")
        self.assertEqual(data["summary"]["verified_gates"], 125)

    def test_84_128gate_dry_run_cli_text_output_contains_redlines(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cli_main(["verify-128-gates", "--clean-room", "--simulate-bench-dry-run"])
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("verified=128/128", out)
        self.assertIn("overall_ready_for_hardware_attach=False", out)
        self.assertIn("persistent_emmc_writes_authorized=False", out)
        self.assertIn("cross_model_flash_authorized=False", out)
        self.assertIn("raw_firmware_bytes_leaked=0", out)

    def test_85_resolve_state_helpers_return_consistent_dicts(self) -> None:
        s127 = resolve_fx3_switch_vh_af_and_exposure_stdadj_state(
            shoot_mode=SHOOT_MODE_M_PHASE297,
            focus_mode="AF-C",
            gravity_orientation=GRAVITY_ORIENTATION_90_DEG_G127,
            requested_switch_vh_af_area=SWITCH_VH_AF_POINT_AND_AREA_G127,
        )
        self.assertTrue(s127["vh_af_orientation_switch_active"])
        self.assertEqual(s127["enabled_focus_area_limit_count"], 14)

        s128 = resolve_fx3_tcub_format_and_playback_copy_slot_state(
            requested_select_playback_media=MEDIA_SLOT_2_G128,
            slot_1_contains_tier0_vault=True,
            copy_requested=True,
        )
        self.assertEqual(s128["copy_direction_label"], "Slot 2 -> Slot 1")
        self.assertTrue(s128["copy_blocked_by_slot1_vault_firewall"])

    def test_86_g127_and_g128_aliases_accepted_in_cli(self) -> None:
        for alias in (
            "verify-g127-switch-vh-af-exposure-stdadj",
            "verify-g128-tcub-playback-copy-slot",
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = cli_main([alias, "--clean-room", "--summary", "--json"])
            self.assertEqual(rc, 0)
            self.assertTrue(json.loads(buf.getvalue())["valid"])


if __name__ == "__main__":
    unittest.main()
