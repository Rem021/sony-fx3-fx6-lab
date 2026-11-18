"""Phase 294 (Wave-53) Dual-Mode Unit Tests (86 tests) for
`fx3_safety.realhw_lens_comp_af_illuminator_aperture_drive_folder_rating_and_126gate_guard`:

- Gate `G125` (`GATE_G125_LENS_COMP_AF_ASSIST_AND_FRONT_AF_ILLUMINATOR_GUARD`):
  - `[Lens Compensation]` (`Shading Comp.`, `Chromatic Aberration Comp.`, `Distortion Comp.`)
    strictly `Auto/Off` (`Auto: Low` / `LENS_COMP_SHADING_AUTO_LOW` `_f 0x6c9c` dormant enum
    rejected fail-closed), surviving `[Camera Settings Reset]` (`Breathing Comp.` resets).
  - E-mount forced-`Auto` distortion lock (`SELP1650`, `FE 28-70mm`), Movie `SteadyShot = Active`
    forced-`Auto` distortion lock, unchipped manual lens lockout, HDMI RAW breathing block, and
    `ILME-FX6 Ver. 6.01` `Technical > Lens` (`All File`, locking `Breathing Compensation = Off`
    when `Distortion = Off`, `S&Q = On`, or `Codec` includes `RAW`).
  - Movie/`S&Q`-only `[AF Transition Speed]` (`1..7`, default `5`), `[AF Subj. Shift Sensitivity]`
    (`1..5`, default `5`, internal `5_RESPONSICE`), `[AF Assist]` (`On/Off`, strictly Movie `AF-C` /
    `MOVIE_AUTO`, incompatible with `SELP1650`/`SEL18200LE`).
  - Empirical `[AF Illuminator]` Front LED Hardware Reality Split: `ILME-FX3` DOES possess a
    built-in front `AF illuminator/Self-timer lamp` LED (`Front side #8`, `0.3..3.0 m`) + MI-Shoe
    external flash AF illuminator in Still mode (`Auto/Off`, locked out in `Movie`/`S&Q`/`AF-C`/
    moving `AF-A`/`Focus Magnifier`/`Mount Adaptor`), whereas `ILME-FX6` completely lacks any
    built-in AF illuminator LED or menu (`N5model36setting_still_image_af_illuminator_tE` dormant).
- Gate `G126` (`GATE_G126_APERTURE_DRIVE_FOCUS_FRAME_AND_SLOT1_FOLDER_RATING_GUARD`):
  - Still-only `[Aperture Drive in AF]` (`Focus Priority/Standard/Silent Priority` + Silent Mode
    `Standard/Silent Priority` sub-key), Still-only `[AF w/ Shutter]` (`On/Off`), Still-only
    `[Pre-AF]` (`Off/On`, `LENS_PRE_AF_SUPPORT`), all-mode `[Circ. of Focus Point]` (orthogonal wrap
    ONLY — NO diagonal wrap), `[Focus Area Color]` (`White/Red`; `ilc/2210` vs legacy `Focus Frame
    Color`): all 5 survive `Camera Settings Reset` (reset ONLY via `[Initialize]`) and are absent
    on `ILME-FX6` (which uses cinema `Iris`).
  - `[File/Folder Settings]` (`Standard Form` `100MSDCF..999MSDCF` vs `Date Form` `100_MMDD`
    locking `[Select REC Folder]`, `[Set File Name]` rules, `4,000`-image per-folder ceiling, dual-slot
    sync rules), and fail-closed `EROFS`/`EOPNOTSUPP` `Slot-1` Tier-0 recovery vault firewall blocking
    `[Create New Folder]`, `[Forced File Number Reset]`, Playback `[Rating]` (`★1..★5`), Still
    custom-key `[Add Rating]`, and `[Rating Set(Custom Key)]` (`slot1_metadata_sector_writes == 0`,
    `slot1_avf_info_mutated == False`).
- Unified `126`-Gate Master Safety Preflight (`evaluate_126gate_preflight` / `verify-126-gates`):
  - `123/126` offline (`VERIFIED_123_OF_126_AWAITING_PHYSICAL_TIER0`) and `126/126` under
    `--simulate-bench-dry-run` (`VERIFIED_ALL_126_GATES_DRY_RUN_SIMULATED_BACKUP`) with all redlines
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
from fx3_safety.realhw_sensor_cleaning_ev_comp_focus_mode_playback_rotate_and_124gate_guard import (
    Master124GateReport,
    evaluate_124gate_preflight,
)
from fx3_safety.realhw_lens_comp_af_illuminator_aperture_drive_folder_rating_and_126gate_guard import (
    AF_ASSIST_FACTORY_DEFAULT_G125,
    AF_ASSIST_F_UXC_RESID16_G125,
    AF_ASSIST_INCOMPATIBLE_LENSES_G125,
    AF_ILLUMINATOR_AUTO_G125,
    AF_ILLUMINATOR_FACTORY_DEFAULT_G125,
    AF_ILLUMINATOR_F_UXC_RESID16_G125,
    AF_ILLUMINATOR_OFF_G125,
    AF_ILLUMINATOR_UXC_RESID16_G125,
    AF_SUBJ_SHIFT_SENS_5_FIRMWARE_SYMBOL_G125,
    AF_SUBJ_SHIFT_SENS_FACTORY_DEFAULT_G125,
    AF_SUBJ_SHIFT_SENS_FN_F_UXC_RESID16_G125,
    AF_SUBJ_SHIFT_SENS_F_UXC_RESID16_G125,
    AF_SUBJ_SHIFT_SENS_MAX_G125,
    AF_SUBJ_SHIFT_SENS_MIN_G125,
    AF_TRANSITION_SPEED_FACTORY_DEFAULT_G125,
    AF_TRANSITION_SPEED_F_UXC_RESID16_G125,
    AF_TRANSITION_SPEED_MAX_G125,
    AF_TRANSITION_SPEED_MIN_G125,
    AF_W_SHUTTER_FACTORY_DEFAULT_G126,
    AF_W_SHUTTER_F_UXC_RESID16_G126,
    ALLOWED_APERTURE_DRIVE_MODES_G126,
    ALLOWED_CIRC_FOCUS_POINT_MODES_G126,
    ALLOWED_FOCUS_AREA_COLORS_G126,
    ALLOWED_FOLDER_NAME_FORMS_G126,
    ALLOWED_LENS_COMP_OPTIONS_G125,
    APERTURE_DRIVE_FACTORY_DEFAULT_G126,
    APERTURE_DRIVE_FOCUS_PRIORITY_G126,
    APERTURE_DRIVE_IN_AF_F_UXC_RESID16_G126,
    APERTURE_DRIVE_SILENT_PRIORITY_G126,
    APERTURE_DRIVE_STANDARD_G126,
    BREATHING_COMP_FACTORY_DEFAULT_G125,
    BREATHING_COMP_F_UXC_RESID16_G125,
    CA_COMP_FACTORY_DEFAULT_G125,
    CA_COMP_F_UXC_RESID16_G125,
    CIRC_FOCUS_POINT_CIRCULATE_G126,
    CIRC_FOCUS_POINT_DEFAULT_G126,
    CIRC_FOCUS_POINT_DOES_NOT_G126,
    CIRC_FOCUS_POINT_F_UXC_RESID16_G126,
    CROSS_MODEL_FLASH_AUTHORIZED,
    DEFAULT_REPO_ROOT,
    DISTORTION_COMP_FACTORY_DEFAULT_G125,
    DISTORTION_COMP_F_UXC_RESID16_G125,
    DONOR_CHECK_CI_MAX_SECONDS_PHASE294,
    DONOR_CHECK_MAX_SECONDS_PHASE294,
    DORMANT_SHADING_AUTO_LOW_MODES_G125,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    ENV_CLEAN_ROOM_TEST_PHASE294,
    ENV_FORCE_CLEAN_ROOM,
    FILE_NUMBER_RESET_G126,
    FILE_NUMBER_SERIES_G126,
    FOCUS_AREA_COLOR_DEFAULT_G126,
    FOCUS_AREA_COLOR_F_UXC_RESID16_G126,
    FOCUS_AREA_COLOR_RED_G126,
    FOCUS_AREA_COLOR_WHITE_G126,
    FOCUS_FRAME_COLOR_LEGACY_F_UXC_RESID16_G126,
    FOLDER_IMAGE_CAPACITY_LIMIT_G126,
    FOLDER_NAME_DATE_FORM_G126,
    FOLDER_NAME_FACTORY_DEFAULT_G126,
    FOLDER_NAME_STANDARD_FORM_G126,
    FX3_DEFAULT_FW_VERSION_PHASE294,
    FX3_FRONT_AF_ILLUMINATOR_PART_NUM_G125,
    FX3_FRONT_AF_ILLUMINATOR_RANGE_M_G125,
    FX3_HELP_GUIDE_CODE_PHASE294,
    FX3_MODEL_ID_PHASE294,
    FX3_MODEL_NAME_PHASE294,
    FX6_DEFAULT_FW_VERSION_PHASE294,
    FX6_IRIS_CONTROL_MODES_G126,
    FX6_LENS_COMP_MENU_PATH_G125,
    FX6_LENS_COMP_PROFILE_SCOPE_G125,
    FX6_MODEL_NAME_PHASE294,
    G125,
    G125_GATE_CODE,
    G125_GATE_ID,
    G126,
    G126_GATE_CODE,
    G126_GATE_ID,
    HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    HUMAN_HARDWARE_ATTACH_TOKEN,
    LENS_COMP_AUTO_G125,
    LENS_COMP_F_UXC_RESID16_G125,
    LENS_COMP_OFF_G125,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED,
    PHYSICAL_USB_PACKETS_EMITTED,
    PINNED_FX3_APPFW_SLICES_PHASE294,
    PINNED_FX3_APPFW_SLICES_SHA256_PHASE294,
    PINNED_FX6_APPFW_SLICES_PHASE294,
    PINNED_FX6_APPFW_SLICES_SHA256_PHASE294,
    PINNED_PHASE294_DONOR_SPECS,
    PRE_AF_FACTORY_DEFAULT_G126,
    PRE_AF_F_UXC_RESID16_G126,
    RAW_FIRMWARE_BYTES_LEAKED,
    REALHW_LENS_COMP_AF_ILLUMINATOR_APERTURE_DRIVE_FOLDER_RATING_126GATE_SCHEMA,
    RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE294,
    RESET_ACTION_INITIALIZE_PHASE294,
    RESET_ACTION_NONE_PHASE294,
    SET_FILE_NAME_DEFAULT_PREFIX_G126,
    SHADING_AUTO_LOW_DORMANT_F_UXC_RESID16_G125,
    SHADING_COMP_FACTORY_DEFAULT_G125,
    SHADING_COMP_F_UXC_RESID16_G125,
    SHOOT_MODE_A_PHASE294,
    SHOOT_MODE_INTELLIGENT_AUTO_PHASE294,
    SHOOT_MODE_MOVIE_PHASE294,
    SHOOT_MODE_M_PHASE294,
    SHOOT_MODE_P_PHASE294,
    SHOOT_MODE_SQ_PHASE294,
    SPI_NOR_WRITE_AUTHORIZED,
    STATUS_BLOCKED_G125_AF_ILLUMINATOR_LED_REALITY_OR_LOCKOUT_VIOLATION,
    STATUS_BLOCKED_G125_DORMANT_AUTO_LOW_OR_RESET_PERSISTENCE_VIOLATION,
    STATUS_BLOCKED_G125_EMOUNT_OR_ACTIVE_SS_DISTORTION_LOCK_VIOLATION,
    STATUS_BLOCKED_G125_FX6_TECHNICAL_LENS_RAW_SQ_BREATHING_VIOLATION,
    STATUS_BLOCKED_G125_MOVIE_AF_TRANSITION_SHIFT_OR_ASSIST_VIOLATION,
    STATUS_BLOCKED_G125_TELEMETRY_INVALID,
    STATUS_BLOCKED_G126_APERTURE_DRIVE_OR_PRE_AF_SHUTTER_MODE_VIOLATION,
    STATUS_BLOCKED_G126_CIRC_DIAGONAL_OR_INITIALIZE_RESET_SPOOF_VIOLATION,
    STATUS_BLOCKED_G126_FOLDER_NAMING_CAPACITY_OR_DUAL_SLOT_VIOLATION,
    STATUS_BLOCKED_G126_FX6_IRIS_VS_FX3_STILL_AF_CROSSWIRE_VIOLATION,
    STATUS_BLOCKED_G126_SLOT1_VAULT_FOLDER_OR_RATING_WRITE_VIOLATION,
    STATUS_BLOCKED_G126_TELEMETRY_INVALID,
    STATUS_BLOCKED_PERSISTENT_EMMC_WRITE,
    STATUS_BLOCKED_PHASE294_DONOR_INTEGRITY,
    STATUS_VERIFIED_G125,
    STATUS_VERIFIED_G126,
    STATUS_VERIFIED_SAFE,
    USB_PACKETS_TRANSMITTED,
    audit_phase294_donor_contracts,
    compute_aperture_drive_and_folder_rating_matrix,
    compute_lens_comp_and_af_illuminator_matrix,
    evaluate_126_master_safety_gates,
    evaluate_126gate_preflight,
    evaluate_g125_lens_comp_and_af_illuminator_guard,
    evaluate_g126_aperture_drive_and_folder_rating_guard,
    main as module_main,
    resolve_fx3_aperture_drive_and_folder_rating_state,
    resolve_fx3_lens_comp_and_af_illuminator_state,
    run_126_gate_preflight,
    verify_aperture_drive_and_folder_rating_guard,
    verify_lens_comp_and_af_illuminator_guard,
)


def _make_stub_master124(
    *, dry_run: bool = False, all_g13_124_ok: bool = True
) -> Master124GateReport:
    gates = []
    for i in range(1, 125):
        gid = f"G{i:02d}"
        is_tier0_offline = gid in ("G10", "G11", "G12") and not dry_run
        passed = (not is_tier0_offline) and (all_g13_124_ok or i <= 12)
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
    g13_122 = 110 if all_g13_124_ok else 0
    g123_124 = 2 if all_g13_124_ok else 0
    total = g01_12 + g13_122 + g123_124
    return Master124GateReport(
        schema="stub_124",
        version="2026.11.17",
        evaluated_utc="2026-11-17T00:00:00Z",
        verification_mode="CLEAN_ROOM_SYNTHETIC",
        clean_room_forced=True,
        dry_run_rehearsal_only=dry_run,
        overall_ready_for_hardware_attach=False,
        hardware_live_attachment_authorized=False,
        offline_121_gates_verified=all_g13_124_ok,
        all_124_gates_verified=(dry_run and all_g13_124_ok),
        g13_to_g124_all_passed=all_g13_124_ok,
        g123_to_g124_all_passed=all_g13_124_ok,
        h0_h1_trial_entry_allowed=all_g13_124_ok,
        status=(
            "VERIFIED_ALL_124_GATES_DRY_RUN_SIMULATED_BACKUP"
            if dry_run
            else "VERIFIED_121_OF_124_AWAITING_PHYSICAL_TIER0"
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
            "g13_to_g122_verified": g13_122,
            "g123_to_g124_verified": g123_124,
            "verified_gates": total,
        },
        gates=tuple(gates),
        master_122_report={},
        g123_result={},
        g124_result={},
        errors=(),
        warnings=(),
    )


class TestPhase294DonorAuditAndRedlines(unittest.TestCase):
    def test_01_package_exports_and_schema(self) -> None:
        self.assertEqual(G125, "G125")
        self.assertEqual(G125_GATE_ID, "G125")
        self.assertEqual(G126, "G126")
        self.assertEqual(G126_GATE_ID, "G126")
        self.assertTrue(hasattr(fx3_safety, "evaluate_126gate_preflight"))
        self.assertTrue(hasattr(fx3_safety, "verify_lens_comp_and_af_illuminator_guard"))
        self.assertTrue(hasattr(fx3_safety, "verify_aperture_drive_and_folder_rating_guard"))
        self.assertEqual(
            REALHW_LENS_COMP_AF_ILLUMINATOR_APERTURE_DRIVE_FOLDER_RATING_126GATE_SCHEMA,
            "realhw_lens_comp_af_illuminator_aperture_drive_folder_rating_and_126gate_guard_v1",
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

    def test_03_pinned_donor_specs_have_12_artifacts(self) -> None:
        self.assertEqual(len(PINNED_PHASE294_DONOR_SPECS), 12)
        self.assertEqual(len(PINNED_FX3_APPFW_SLICES_PHASE294), 32)
        self.assertEqual(len(PINNED_FX6_APPFW_SLICES_PHASE294), 12)
        self.assertEqual(len(PINNED_FX3_APPFW_SLICES_SHA256_PHASE294), 64)
        self.assertEqual(len(PINNED_FX6_APPFW_SLICES_SHA256_PHASE294), 64)

    def test_04_donor_audit_clean_room_synthetic_deterministic(self) -> None:
        audit = audit_phase294_donor_contracts(repo_root=DEFAULT_REPO_ROOT, force_clean_room=True)
        self.assertTrue(audit.valid)
        self.assertEqual(audit.status, STATUS_VERIFIED_SAFE)
        self.assertEqual(audit.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(audit.files_inspected, 0)
        self.assertEqual(audit.raw_firmware_bytes_leaked, 0)
        self.assertTrue(audit.fx3_contracts_verified)
        self.assertTrue(audit.fx6_contracts_verified)
        self.assertTrue(audit.four_lang_resid16_parity_verified)

    def test_05_donor_audit_env_fx3_clean_room_test(self) -> None:
        with mock.patch.dict(os.environ, {ENV_CLEAN_ROOM_TEST_PHASE294: "1"}, clear=False):
            audit = audit_phase294_donor_contracts(repo_root=DEFAULT_REPO_ROOT)
            self.assertTrue(audit.valid)
            self.assertEqual(audit.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_06_donor_audit_env_fx3_fx6_force_clean_room(self) -> None:
        with mock.patch.dict(os.environ, {ENV_FORCE_CLEAN_ROOM: "1"}, clear=False):
            audit = audit_phase294_donor_contracts(repo_root=DEFAULT_REPO_ROOT)
            self.assertTrue(audit.valid)
            self.assertEqual(audit.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_07_donor_audit_local_or_clean_fallback_within_budget(self) -> None:
        audit = audit_phase294_donor_contracts(repo_root=DEFAULT_REPO_ROOT)
        self.assertTrue(audit.valid)
        self.assertEqual(audit.raw_firmware_bytes_leaked, 0)
        budget = (
            DONOR_CHECK_CI_MAX_SECONDS_PHASE294
            if os.environ.get("GITHUB_ACTIONS") == "true"
            else DONOR_CHECK_MAX_SECONDS_PHASE294
        )
        self.assertLessEqual(audit.elapsed_seconds, max(budget, 0.25))
        if audit.verification_mode == "LOCAL_DONOR_O_RDONLY":
            self.assertEqual(audit.files_inspected, 12)
            self.assertTrue(audit.fx3_contracts_verified)
            self.assertTrue(audit.fx6_contracts_verified)
            self.assertTrue(audit.four_lang_resid16_parity_verified)

    def test_08_explicit_missing_work_root_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            with mock.patch.dict(
                os.environ,
                {ENV_CLEAN_ROOM_TEST_PHASE294: "0", ENV_FORCE_CLEAN_ROOM: "0"},
                clear=False,
            ):
                audit = audit_phase294_donor_contracts(
                    work_root=Path(tmpdir), force_clean_room=False
                )
                self.assertFalse(audit.valid)
                self.assertEqual(audit.status, STATUS_BLOCKED_PHASE294_DONOR_INTEGRITY)
                self.assertEqual(len(audit.missing_markers), 12)

    def test_09_github_actions_budget_headroom_15s(self) -> None:
        with mock.patch.dict(os.environ, {"GITHUB_ACTIONS": "true"}, clear=False):
            audit = audit_phase294_donor_contracts(force_clean_room=True)
            self.assertTrue(audit.within_budget_200ms)
            self.assertEqual(DONOR_CHECK_CI_MAX_SECONDS_PHASE294, 15.0)

    def test_10_persistent_write_request_blocked_in_g125_and_g126(self) -> None:
        v125, r125 = evaluate_g125_lens_comp_and_af_illuminator_guard(
            force_clean_room=True, request_persistent_emmc_writes=True
        )
        self.assertFalse(v125.passed)
        self.assertIn(STATUS_BLOCKED_PERSISTENT_EMMC_WRITE, r125.violation_codes)
        v126, r126 = evaluate_g126_aperture_drive_and_folder_rating_guard(
            force_clean_room=True, request_persistent_emmc_writes=True
        )
        self.assertFalse(v126.passed)
        self.assertIn(STATUS_BLOCKED_PERSISTENT_EMMC_WRITE, r126.violation_codes)


class TestPhase294GateG125LensCompAfAssistAndIlluminator(unittest.TestCase):
    def test_11_g125_default_nominal_passes(self) -> None:
        res = verify_lens_comp_and_af_illuminator_guard()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_VERIFIED_G125)
        self.assertEqual(res.effective_shading_comp, SHADING_COMP_FACTORY_DEFAULT_G125)
        self.assertEqual(res.effective_ca_comp, CA_COMP_FACTORY_DEFAULT_G125)
        self.assertEqual(res.effective_distortion_comp, DISTORTION_COMP_FACTORY_DEFAULT_G125)
        self.assertEqual(res.effective_breathing_comp, BREATHING_COMP_FACTORY_DEFAULT_G125)
        self.assertEqual(res.af_transition_speed, 5)
        self.assertEqual(res.af_subj_shift_sens, 5)
        self.assertTrue(res.fx3_has_built_in_af_illuminator_led)
        self.assertFalse(res.fx6_has_built_in_af_illuminator_led)

    def test_12_g125_384_matrix_invariants_hold(self) -> None:
        m = compute_lens_comp_and_af_illuminator_matrix()
        self.assertEqual(m["states_checked"], 384)
        self.assertTrue(m["all_invariants_hold"])
        self.assertGreater(m["forced_auto_dist_count"], 0)
        self.assertGreater(m["illum_blocked_count"], 0)
        self.assertGreater(m["assist_active_count"], 0)
        self.assertGreater(m["lens_comp_persisted_count"], 0)

    def test_13_g125_uxc_and_firmware_constants_match_wave53(self) -> None:
        self.assertEqual(LENS_COMP_F_UXC_RESID16_G125, 0x75C8)
        self.assertEqual(SHADING_COMP_F_UXC_RESID16_G125, 0x64E1)
        self.assertEqual(SHADING_AUTO_LOW_DORMANT_F_UXC_RESID16_G125, 0x6C9C)
        self.assertEqual(CA_COMP_F_UXC_RESID16_G125, 0x68CD)
        self.assertEqual(DISTORTION_COMP_F_UXC_RESID16_G125, 0x6200)
        self.assertEqual(BREATHING_COMP_F_UXC_RESID16_G125, 0x73EA)
        self.assertEqual(AF_TRANSITION_SPEED_F_UXC_RESID16_G125, 0x6E9D)
        self.assertEqual(AF_SUBJ_SHIFT_SENS_F_UXC_RESID16_G125, 0x79D6)
        self.assertEqual(AF_SUBJ_SHIFT_SENS_FN_F_UXC_RESID16_G125, 0x64DE)
        self.assertEqual(AF_ASSIST_F_UXC_RESID16_G125, 0x64A9)
        self.assertEqual(AF_ILLUMINATOR_UXC_RESID16_G125, 0xE07F)
        self.assertEqual(AF_ILLUMINATOR_F_UXC_RESID16_G125, 0x69C0)
        self.assertEqual(AF_SUBJ_SHIFT_SENS_5_FIRMWARE_SYMBOL_G125, "MOVIE_AF_SUBJ_SHIFT_SENS_5_RESPONSICE")

    def test_14_g125_allowed_lens_comp_only_auto_off(self) -> None:
        self.assertEqual(ALLOWED_LENS_COMP_OPTIONS_G125, ("Auto", "Off"))
        for dormant in DORMANT_SHADING_AUTO_LOW_MODES_G125:
            res = verify_lens_comp_and_af_illuminator_guard(requested_shading_comp=dormant)
            self.assertFalse(res.valid)
            self.assertEqual(
                res.status,
                STATUS_BLOCKED_G125_DORMANT_AUTO_LOW_OR_RESET_PERSISTENCE_VIOLATION,
            )

    def test_15_g125_dormant_auto_low_rejected_in_ca_and_distortion_too(self) -> None:
        res_ca = verify_lens_comp_and_af_illuminator_guard(requested_ca_comp="Auto: Low")
        self.assertFalse(res_ca.valid)
        self.assertEqual(
            res_ca.status,
            STATUS_BLOCKED_G125_DORMANT_AUTO_LOW_OR_RESET_PERSISTENCE_VIOLATION,
        )
        res_dist = verify_lens_comp_and_af_illuminator_guard(requested_distortion_comp="Low")
        self.assertFalse(res_dist.valid)
        self.assertEqual(
            res_dist.status,
            STATUS_BLOCKED_G125_DORMANT_AUTO_LOW_OR_RESET_PERSISTENCE_VIOLATION,
        )

    def test_16_g125_lens_comp_survives_cam_settings_reset_breathing_resets(self) -> None:
        eff = resolve_fx3_lens_comp_and_af_illuminator_state(
            shoot_mode=SHOOT_MODE_MOVIE_PHASE294,
            requested_shading_comp=LENS_COMP_OFF_G125,
            requested_ca_comp=LENS_COMP_OFF_G125,
            requested_distortion_comp=LENS_COMP_AUTO_G125,
            requested_breathing_comp="On",
            requested_af_transition_speed=2,
            requested_af_subj_shift_sens=2,
            requested_af_assist="On",
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE294,
        )
        self.assertEqual(eff["effective_shading_comp"], LENS_COMP_OFF_G125)
        self.assertEqual(eff["effective_ca_comp"], LENS_COMP_OFF_G125)
        self.assertEqual(eff["effective_distortion_comp"], LENS_COMP_AUTO_G125)
        self.assertTrue(eff["lens_comp_survived_cam_reset"])
        self.assertEqual(eff["effective_breathing_comp"], "Off")
        self.assertTrue(eff["breathing_comp_reset_on_cam_reset"])
        self.assertEqual(eff["af_transition_speed"], 5)
        self.assertEqual(eff["af_subj_shift_sens"], 5)
        self.assertEqual(eff["af_assist_setting"], "Off")

    def test_17_g125_initialize_resets_lens_comp_to_factory_defaults(self) -> None:
        eff = resolve_fx3_lens_comp_and_af_illuminator_state(
            requested_shading_comp=LENS_COMP_OFF_G125,
            requested_ca_comp=LENS_COMP_OFF_G125,
            requested_distortion_comp=LENS_COMP_AUTO_G125,
            reset_action=RESET_ACTION_INITIALIZE_PHASE294,
        )
        self.assertEqual(eff["effective_shading_comp"], "Auto")
        self.assertEqual(eff["effective_ca_comp"], "Auto")
        self.assertEqual(eff["effective_distortion_comp"], "Off")
        self.assertFalse(eff["lens_comp_survived_cam_reset"])

    def test_18_g125_claimed_lens_comp_resets_on_cam_reset_blocked(self) -> None:
        res = verify_lens_comp_and_af_illuminator_guard(
            claimed_lens_comp_resets_on_cam_settings_reset=True
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            res.status,
            STATUS_BLOCKED_G125_DORMANT_AUTO_LOW_OR_RESET_PERSISTENCE_VIOLATION,
        )

    def test_19_g125_emount_selp1650_and_fe2870_force_distortion_auto(self) -> None:
        for lens in ("SELP1650", "FE 28-70mm F3.5-5.6 OSS"):
            eff = resolve_fx3_lens_comp_and_af_illuminator_state(
                lens_model=lens, requested_distortion_comp="Off"
            )
            self.assertTrue(eff["distortion_forced_auto_by_lens"])
            self.assertEqual(eff["effective_distortion_comp"], "Auto")
            res = verify_lens_comp_and_af_illuminator_guard(
                lens_model=lens,
                requested_distortion_comp="Off",
                distortion_off_override_requested=True,
            )
            self.assertFalse(res.valid)
            self.assertEqual(
                res.status,
                STATUS_BLOCKED_G125_EMOUNT_OR_ACTIVE_SS_DISTORTION_LOCK_VIOLATION,
            )

    def test_20_g125_emount_forced_auto_allowed_when_requested_auto(self) -> None:
        res = verify_lens_comp_and_af_illuminator_guard(
            lens_model="SELP1650", requested_distortion_comp="Auto"
        )
        self.assertTrue(res.valid)
        self.assertTrue(res.distortion_forced_auto_by_lens)

    def test_21_g125_steadyshot_active_forces_distortion_auto_in_movie(self) -> None:
        res_bad = verify_lens_comp_and_af_illuminator_guard(
            shoot_mode=SHOOT_MODE_MOVIE_PHASE294,
            steadyshot_active=True,
            requested_distortion_comp="Off",
            distortion_off_override_requested=True,
        )
        self.assertFalse(res_bad.valid)
        self.assertEqual(
            res_bad.status,
            STATUS_BLOCKED_G125_EMOUNT_OR_ACTIVE_SS_DISTORTION_LOCK_VIOLATION,
        )
        res_ok = verify_lens_comp_and_af_illuminator_guard(
            shoot_mode=SHOOT_MODE_MOVIE_PHASE294,
            steadyshot_active=True,
            requested_distortion_comp="Auto",
        )
        self.assertTrue(res_ok.valid)

    def test_22_g125_unchipped_manual_lens_locks_lens_comp_adjustment(self) -> None:
        res = verify_lens_comp_and_af_illuminator_guard(
            lens_model="Manual 50mm F1.2",
            lens_electronic_contacts=False,
            lens_comp_adjust_requested=True,
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            res.status,
            STATUS_BLOCKED_G125_EMOUNT_OR_ACTIVE_SS_DISTORTION_LOCK_VIOLATION,
        )

    def test_23_g125_breathing_comp_movie_only_and_hdmi_raw_block(self) -> None:
        res_still = verify_lens_comp_and_af_illuminator_guard(
            shoot_mode=SHOOT_MODE_M_PHASE294, requested_breathing_comp="On"
        )
        self.assertFalse(res_still.valid)
        self.assertEqual(
            res_still.status,
            STATUS_BLOCKED_G125_EMOUNT_OR_ACTIVE_SS_DISTORTION_LOCK_VIOLATION,
        )
        res_raw = verify_lens_comp_and_af_illuminator_guard(
            shoot_mode=SHOOT_MODE_MOVIE_PHASE294,
            requested_breathing_comp="On",
            hdmi_raw_output_active=True,
        )
        self.assertFalse(res_raw.valid)
        self.assertEqual(
            res_raw.status,
            STATUS_BLOCKED_G125_EMOUNT_OR_ACTIVE_SS_DISTORTION_LOCK_VIOLATION,
        )

    def test_24_g125_fx6_technical_lens_all_file_path_required(self) -> None:
        res_bad_path = verify_lens_comp_and_af_illuminator_guard(
            target_model=FX6_MODEL_NAME_PHASE294,
            fx6_menu_path="Project/Paint/Lens -> Lens -> Compensate",
        )
        self.assertFalse(res_bad_path.valid)
        self.assertEqual(
            res_bad_path.status,
            STATUS_BLOCKED_G125_FX6_TECHNICAL_LENS_RAW_SQ_BREATHING_VIOLATION,
        )
        res_bad_scope = verify_lens_comp_and_af_illuminator_guard(
            target_model=FX6_MODEL_NAME_PHASE294,
            fx6_menu_path=FX6_LENS_COMP_MENU_PATH_G125,
            fx6_profile_scope="Scene File",
        )
        self.assertFalse(res_bad_scope.valid)
        self.assertEqual(
            res_bad_scope.status,
            STATUS_BLOCKED_G125_FX6_TECHNICAL_LENS_RAW_SQ_BREATHING_VIOLATION,
        )

    def test_25_g125_fx6_breathing_locked_off_by_distortion_off_sq_or_raw(self) -> None:
        for kw in (
            {"requested_distortion_comp": "Off"},
            {"requested_distortion_comp": "Auto", "fx6_sq_on": True},
            {"requested_distortion_comp": "Auto", "fx6_codec": "XAVC-I RAW 4K"},
        ):
            res = verify_lens_comp_and_af_illuminator_guard(
                target_model=FX6_MODEL_NAME_PHASE294,
                fx6_menu_path=FX6_LENS_COMP_MENU_PATH_G125,
                fx6_profile_scope=FX6_LENS_COMP_PROFILE_SCOPE_G125,
                fx6_breathing_requested="Auto",
                **kw,
            )
            self.assertFalse(res.valid)
            self.assertEqual(
                res.status,
                STATUS_BLOCKED_G125_FX6_TECHNICAL_LENS_RAW_SQ_BREATHING_VIOLATION,
            )

    def test_26_g125_fx6_breathing_allowed_when_dist_auto_no_sq_no_raw(self) -> None:
        res = verify_lens_comp_and_af_illuminator_guard(
            target_model=FX6_MODEL_NAME_PHASE294,
            fx6_menu_path=FX6_LENS_COMP_MENU_PATH_G125,
            fx6_profile_scope=FX6_LENS_COMP_PROFILE_SCOPE_G125,
            requested_distortion_comp="Auto",
            fx6_sq_on=False,
            fx6_codec="XAVC-I",
            fx6_breathing_requested="Auto",
        )
        self.assertTrue(res.valid)
        self.assertFalse(res.fx6_breathing_locked_off)

    def test_27_g125_af_transition_speed_1_to_7_bounds(self) -> None:
        self.assertEqual((AF_TRANSITION_SPEED_MIN_G125, AF_TRANSITION_SPEED_MAX_G125), (1, 7))
        for bad in (0, 8, -1):
            res = verify_lens_comp_and_af_illuminator_guard(requested_af_transition_speed=bad)
            self.assertFalse(res.valid)
            self.assertEqual(
                res.status,
                STATUS_BLOCKED_G125_MOVIE_AF_TRANSITION_SHIFT_OR_ASSIST_VIOLATION,
            )
        for good in range(1, 8):
            res = verify_lens_comp_and_af_illuminator_guard(requested_af_transition_speed=good)
            self.assertTrue(res.valid)

    def test_28_g125_af_subj_shift_sens_1_to_5_bounds_and_still_lockout(self) -> None:
        self.assertEqual((AF_SUBJ_SHIFT_SENS_MIN_G125, AF_SUBJ_SHIFT_SENS_MAX_G125), (1, 5))
        for bad in (0, 6):
            res = verify_lens_comp_and_af_illuminator_guard(requested_af_subj_shift_sens=bad)
            self.assertFalse(res.valid)
            self.assertEqual(
                res.status,
                STATUS_BLOCKED_G125_MOVIE_AF_TRANSITION_SHIFT_OR_ASSIST_VIOLATION,
            )
        res_still = verify_lens_comp_and_af_illuminator_guard(
            shoot_mode=SHOOT_MODE_A_PHASE294, af_transition_adjust_requested=True
        )
        self.assertFalse(res_still.valid)
        self.assertEqual(
            res_still.status,
            STATUS_BLOCKED_G125_MOVIE_AF_TRANSITION_SHIFT_OR_ASSIST_VIOLATION,
        )

    def test_29_g125_af_assist_gated_strictly_to_movie_afc(self) -> None:
        res_ok = verify_lens_comp_and_af_illuminator_guard(
            shoot_mode=SHOOT_MODE_MOVIE_PHASE294,
            focus_mode="MOVIE_AUTO",
            requested_af_assist="On",
            af_assist_activate_requested=True,
        )
        self.assertTrue(res_ok.valid)
        self.assertTrue(res_ok.af_assist_active)
        res_still = verify_lens_comp_and_af_illuminator_guard(
            shoot_mode=SHOOT_MODE_M_PHASE294,
            focus_mode="AF-C",
            requested_af_assist="On",
        )
        self.assertFalse(res_still.valid)
        res_mf = verify_lens_comp_and_af_illuminator_guard(
            shoot_mode=SHOOT_MODE_MOVIE_PHASE294,
            focus_mode="MF",
            requested_af_assist="On",
        )
        self.assertFalse(res_mf.valid)
        self.assertEqual(
            res_mf.status,
            STATUS_BLOCKED_G125_MOVIE_AF_TRANSITION_SHIFT_OR_ASSIST_VIOLATION,
        )

    def test_30_g125_af_assist_incompatible_with_selp1650_and_sel18200le(self) -> None:
        self.assertEqual(AF_ASSIST_INCOMPATIBLE_LENSES_G125, ("SELP1650", "SEL18200LE"))
        for lens in AF_ASSIST_INCOMPATIBLE_LENSES_G125:
            res = verify_lens_comp_and_af_illuminator_guard(
                shoot_mode=SHOOT_MODE_MOVIE_PHASE294,
                focus_mode="AF-C",
                lens_model=lens,
                requested_distortion_comp=LENS_COMP_AUTO_G125,
                requested_af_assist="On",
                af_assist_activate_requested=True,
            )
            self.assertFalse(res.valid)
            self.assertEqual(
                res.status,
                STATUS_BLOCKED_G125_MOVIE_AF_TRANSITION_SHIFT_OR_ASSIST_VIOLATION,
            )

    def test_31_g125_fx3_built_in_front_led_and_mi_shoe_reality_enforced(self) -> None:
        self.assertEqual(FX3_FRONT_AF_ILLUMINATOR_PART_NUM_G125, "Front side #8 (TP1000886886)")
        self.assertEqual(FX3_FRONT_AF_ILLUMINATOR_RANGE_M_G125, (0.3, 3.0))
        res_ok = verify_lens_comp_and_af_illuminator_guard(
            shoot_mode=SHOOT_MODE_P_PHASE294,
            focus_mode="AF-S",
            requested_af_illuminator=AF_ILLUMINATOR_AUTO_G125,
            af_illuminator_fire_requested=True,
            mi_shoe_flash_illuminator_attached=True,
        )
        self.assertTrue(res_ok.valid)
        self.assertTrue(res_ok.af_illuminator_active)
        self.assertTrue(res_ok.mi_shoe_flash_illuminator_active)
        self.assertTrue(res_ok.fx3_has_built_in_af_illuminator_led)

        res_spoof = verify_lens_comp_and_af_illuminator_guard(
            claimed_fx3_lacks_built_in_af_illuminator_led=True
        )
        self.assertFalse(res_spoof.valid)
        self.assertEqual(
            res_spoof.status,
            STATUS_BLOCKED_G125_AF_ILLUMINATOR_LED_REALITY_OR_LOCKOUT_VIOLATION,
        )

    def test_32_g125_af_illuminator_lockouts_movie_sq_afc_moving_afa_magnifier_adaptor(self) -> None:
        lockout_cases = [
            {"shoot_mode": SHOOT_MODE_MOVIE_PHASE294, "focus_mode": "AF-S"},
            {"shoot_mode": SHOOT_MODE_SQ_PHASE294, "focus_mode": "AF-S"},
            {"shoot_mode": SHOOT_MODE_M_PHASE294, "focus_mode": "AF-C"},
            {"shoot_mode": SHOOT_MODE_M_PHASE294, "focus_mode": "AF-A", "subject_moving_in_af_a": True},
            {"shoot_mode": SHOOT_MODE_M_PHASE294, "focus_mode": "AF-S", "focus_magnifier_active": True},
            {"shoot_mode": SHOOT_MODE_M_PHASE294, "focus_mode": "AF-S", "mount_adaptor_attached": True},
        ]
        for kw in lockout_cases:
            res = verify_lens_comp_and_af_illuminator_guard(
                requested_af_illuminator=AF_ILLUMINATOR_AUTO_G125,
                af_illuminator_fire_requested=True,
                **kw,
            )
            self.assertFalse(res.valid)
            self.assertEqual(
                res.status,
                STATUS_BLOCKED_G125_AF_ILLUMINATOR_LED_REALITY_OR_LOCKOUT_VIOLATION,
            )

    def test_33_g125_fx6_zero_built_in_af_illuminator_led_fail_closed(self) -> None:
        res_claim = verify_lens_comp_and_af_illuminator_guard(
            claimed_fx6_has_built_in_af_illuminator_led=True
        )
        self.assertFalse(res_claim.valid)
        self.assertEqual(
            res_claim.status,
            STATUS_BLOCKED_G125_AF_ILLUMINATOR_LED_REALITY_OR_LOCKOUT_VIOLATION,
        )
        res_fire = verify_lens_comp_and_af_illuminator_guard(
            target_model=FX6_MODEL_NAME_PHASE294,
            shoot_mode=SHOOT_MODE_P_PHASE294,
            focus_mode="AF-S",
            af_illuminator_fire_requested=True,
        )
        self.assertFalse(res_fire.valid)
        self.assertEqual(
            res_fire.status,
            STATUS_BLOCKED_G125_AF_ILLUMINATOR_LED_REALITY_OR_LOCKOUT_VIOLATION,
        )

    def test_34_g125_invalid_telemetry_and_booleans_blocked(self) -> None:
        for kw in (
            {"body_model_name": "ILCE-7M4"},
            {"body_model_id": 0x1234},
            {"help_guide_code": "ilc/2110"},
            {"requested_af_transition_speed": True},
            {"requested_af_subj_shift_sens": False},
            {"shoot_mode": "INVALID_MODE"},
        ):
            res = verify_lens_comp_and_af_illuminator_guard(**kw)
            self.assertFalse(res.valid)
            self.assertIn(STATUS_BLOCKED_G125_TELEMETRY_INVALID, res.violation_codes)

    def test_35_evaluate_g125_wrapper_clean_room(self) -> None:
        verdict, res = evaluate_g125_lens_comp_and_af_illuminator_guard(force_clean_room=True)
        self.assertTrue(verdict.passed)
        self.assertEqual(verdict.gate_id, G125_GATE_ID)
        self.assertEqual(verdict.gate_code, G125_GATE_CODE)
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_VERIFIED_G125)
        self.assertEqual(res.raw_firmware_bytes_leaked, 0)


class TestPhase294GateG126ApertureDriveFocusFrameFolderRating(unittest.TestCase):
    def test_36_g126_default_nominal_passes(self) -> None:
        res = verify_aperture_drive_and_folder_rating_guard()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_VERIFIED_G126)
        self.assertEqual(res.effective_aperture_drive_in_af, APERTURE_DRIVE_STANDARD_G126)
        self.assertEqual(res.effective_af_w_shutter, "On")
        self.assertEqual(res.effective_pre_af, "Off")
        self.assertEqual(res.effective_circ_of_focus_point, CIRC_FOCUS_POINT_DOES_NOT_G126)
        self.assertEqual(res.effective_focus_area_color, FOCUS_AREA_COLOR_WHITE_G126)
        self.assertEqual(res.effective_folder_name_form, FOLDER_NAME_STANDARD_FORM_G126)
        self.assertEqual(res.effective_file_number_mode, FILE_NUMBER_SERIES_G126)
        self.assertEqual(res.set_file_name_prefix, SET_FILE_NAME_DEFAULT_PREFIX_G126)
        self.assertEqual(res.slot1_metadata_sector_writes, 0)
        self.assertFalse(res.slot1_avf_info_mutated)

    def test_37_g126_384_matrix_invariants_hold(self) -> None:
        m = compute_aperture_drive_and_folder_rating_matrix()
        self.assertEqual(m["states_checked"], 384)
        self.assertTrue(m["all_invariants_hold"])
        self.assertGreater(m["survived_cam_reset_count"], 0)
        self.assertGreater(m["date_form_select_disabled"], 0)
        self.assertEqual(m["slot1_vault_mutations_blocked"], 192)

    def test_38_g126_uxc_constants_and_legacy_focus_frame_mapping(self) -> None:
        self.assertEqual(APERTURE_DRIVE_IN_AF_F_UXC_RESID16_G126, 0x7879)
        self.assertEqual(AF_W_SHUTTER_F_UXC_RESID16_G126, 0x771D)
        self.assertEqual(PRE_AF_F_UXC_RESID16_G126, 0x76D8)
        self.assertEqual(CIRC_FOCUS_POINT_F_UXC_RESID16_G126, 0x74F6)
        self.assertEqual(FOCUS_AREA_COLOR_F_UXC_RESID16_G126, 0x74AD)
        self.assertEqual(FOCUS_FRAME_COLOR_LEGACY_F_UXC_RESID16_G126, 0x7087)

    def test_39_g126_aperture_drive_3_modes_and_silent_detail_2_modes(self) -> None:
        self.assertEqual(
            ALLOWED_APERTURE_DRIVE_MODES_G126,
            ("Focus Priority", "Standard", "Silent Priority"),
        )
        for mode in ALLOWED_APERTURE_DRIVE_MODES_G126:
            res = verify_aperture_drive_and_folder_rating_guard(
                requested_aperture_drive_in_af=mode
            )
            self.assertTrue(res.valid)
            self.assertEqual(res.effective_aperture_drive_in_af, mode)
        res_bad_silent = verify_aperture_drive_and_folder_rating_guard(
            silent_mode_active=True,
            requested_silent_detail_aperture_drive=APERTURE_DRIVE_FOCUS_PRIORITY_G126,
        )
        self.assertFalse(res_bad_silent.valid)
        self.assertEqual(
            res_bad_silent.status,
            STATUS_BLOCKED_G126_APERTURE_DRIVE_OR_PRE_AF_SHUTTER_MODE_VIOLATION,
        )

    def test_40_g126_still_only_lockout_for_aperture_drive_af_w_shutter_and_pre_af(self) -> None:
        for sm in (SHOOT_MODE_MOVIE_PHASE294, SHOOT_MODE_SQ_PHASE294):
            r1 = verify_aperture_drive_and_folder_rating_guard(
                shoot_mode=sm, still_aperture_adjust_requested=True
            )
            self.assertFalse(r1.valid)
            self.assertEqual(
                r1.status,
                STATUS_BLOCKED_G126_APERTURE_DRIVE_OR_PRE_AF_SHUTTER_MODE_VIOLATION,
            )
            r2 = verify_aperture_drive_and_folder_rating_guard(
                shoot_mode=sm, af_w_shutter_still_use_requested=True
            )
            self.assertFalse(r2.valid)
            r3 = verify_aperture_drive_and_folder_rating_guard(
                shoot_mode=sm, requested_pre_af="On", pre_af_activate_requested=True
            )
            self.assertFalse(r3.valid)

    def test_41_g126_pre_af_requires_lens_pre_af_support_bit(self) -> None:
        res_ok = verify_aperture_drive_and_folder_rating_guard(
            shoot_mode=SHOOT_MODE_A_PHASE294,
            lens_pre_af_supported=True,
            requested_pre_af="On",
            pre_af_activate_requested=True,
        )
        self.assertTrue(res_ok.valid)
        self.assertEqual(res_ok.effective_pre_af, "On")
        res_bad = verify_aperture_drive_and_folder_rating_guard(
            shoot_mode=SHOOT_MODE_A_PHASE294,
            lens_pre_af_supported=False,
            requested_pre_af="On",
            pre_af_activate_requested=True,
        )
        self.assertFalse(res_bad.valid)
        self.assertEqual(
            res_bad.status,
            STATUS_BLOCKED_G126_APERTURE_DRIVE_OR_PRE_AF_SHUTTER_MODE_VIOLATION,
        )

    def test_42_g126_circ_of_focus_point_orthogonal_only_no_diagonal(self) -> None:
        self.assertEqual(
            ALLOWED_CIRC_FOCUS_POINT_MODES_G126,
            ("Does Not Circulate", "Circulate"),
        )
        res_ok = verify_aperture_drive_and_folder_rating_guard(
            shoot_mode=SHOOT_MODE_MOVIE_PHASE294,
            requested_circ_of_focus_point=CIRC_FOCUS_POINT_CIRCULATE_G126,
        )
        self.assertTrue(res_ok.valid)
        self.assertTrue(res_ok.orthogonal_wrap_only)
        res_diag = verify_aperture_drive_and_folder_rating_guard(
            claimed_diagonal_focus_point_wrap=True
        )
        self.assertFalse(res_diag.valid)
        self.assertEqual(
            res_diag.status,
            STATUS_BLOCKED_G126_CIRC_DIAGONAL_OR_INITIALIZE_RESET_SPOOF_VIOLATION,
        )

    def test_43_g126_focus_area_color_white_red_and_initialize_only_reset(self) -> None:
        self.assertEqual(ALLOWED_FOCUS_AREA_COLORS_G126, ("White", "Red"))
        eff_cam_reset = resolve_fx3_aperture_drive_and_folder_rating_state(
            requested_aperture_drive_in_af=APERTURE_DRIVE_SILENT_PRIORITY_G126,
            requested_af_w_shutter="Off",
            requested_pre_af="On",
            requested_circ_of_focus_point=CIRC_FOCUS_POINT_CIRCULATE_G126,
            requested_focus_area_color=FOCUS_AREA_COLOR_RED_G126,
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE294,
        )
        self.assertTrue(eff_cam_reset["focus_frame_5_settings_survived_cam_reset"])
        self.assertEqual(
            eff_cam_reset["effective_aperture_drive_in_af"],
            APERTURE_DRIVE_SILENT_PRIORITY_G126,
        )
        self.assertEqual(eff_cam_reset["effective_af_w_shutter"], "Off")
        self.assertEqual(eff_cam_reset["effective_pre_af"], "On")
        self.assertEqual(
            eff_cam_reset["effective_circ_of_focus_point"],
            CIRC_FOCUS_POINT_CIRCULATE_G126,
        )
        self.assertEqual(eff_cam_reset["effective_focus_area_color"], FOCUS_AREA_COLOR_RED_G126)

        eff_init = resolve_fx3_aperture_drive_and_folder_rating_state(
            requested_aperture_drive_in_af=APERTURE_DRIVE_SILENT_PRIORITY_G126,
            requested_af_w_shutter="Off",
            requested_pre_af="On",
            requested_circ_of_focus_point=CIRC_FOCUS_POINT_CIRCULATE_G126,
            requested_focus_area_color=FOCUS_AREA_COLOR_RED_G126,
            reset_action=RESET_ACTION_INITIALIZE_PHASE294,
        )
        self.assertFalse(eff_init["focus_frame_5_settings_survived_cam_reset"])
        self.assertEqual(eff_init["effective_aperture_drive_in_af"], APERTURE_DRIVE_STANDARD_G126)
        self.assertEqual(eff_init["effective_af_w_shutter"], "On")
        self.assertEqual(eff_init["effective_pre_af"], "Off")
        self.assertEqual(
            eff_init["effective_circ_of_focus_point"],
            CIRC_FOCUS_POINT_DOES_NOT_G126,
        )
        self.assertEqual(eff_init["effective_focus_area_color"], FOCUS_AREA_COLOR_WHITE_G126)

    def test_44_g126_claimed_cam_settings_reset_clears_5_settings_rejected(self) -> None:
        res = verify_aperture_drive_and_folder_rating_guard(
            claimed_5_settings_reset_by_cam_settings_reset=True
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            res.status,
            STATUS_BLOCKED_G126_CIRC_DIAGONAL_OR_INITIALIZE_RESET_SPOOF_VIOLATION,
        )

    def test_45_g126_fx6_iris_architecture_and_unwired_close_iris_warning_rejected(self) -> None:
        self.assertEqual(
            FX6_IRIS_CONTROL_MODES_G126,
            ("Auto Iris", "Manual", "Push Auto Iris", "Iris Override"),
        )
        r1 = verify_aperture_drive_and_folder_rating_guard(
            claimed_fx6_has_aperture_drive_or_circ_or_white_red_color=True
        )
        self.assertFalse(r1.valid)
        self.assertEqual(
            r1.status,
            STATUS_BLOCKED_G126_FX6_IRIS_VS_FX3_STILL_AF_CROSSWIRE_VIOLATION,
        )
        r2 = verify_aperture_drive_and_folder_rating_guard(
            claimed_fx6_close_iris_warning_wired=True
        )
        self.assertFalse(r2.valid)
        self.assertEqual(
            r2.status,
            STATUS_BLOCKED_G126_FX6_IRIS_VS_FX3_STILL_AF_CROSSWIRE_VIOLATION,
        )

    def test_46_g126_date_form_disables_select_rec_folder(self) -> None:
        self.assertEqual(ALLOWED_FOLDER_NAME_FORMS_G126, ("Standard Form", "Date Form"))
        res = verify_aperture_drive_and_folder_rating_guard(
            requested_folder_name_form=FOLDER_NAME_DATE_FORM_G126,
            select_rec_folder_requested=True,
        )
        self.assertFalse(res.valid)
        self.assertFalse(res.select_rec_folder_enabled)
        self.assertEqual(
            res.status,
            STATUS_BLOCKED_G126_FOLDER_NAMING_CAPACITY_OR_DUAL_SLOT_VIOLATION,
        )

    def test_47_g126_set_file_name_3char_and_leading_underscore_block(self) -> None:
        for bad in ("_SC", "DS", "DSCX", "ds1", "A-1"):
            res = verify_aperture_drive_and_folder_rating_guard(set_file_name_prefix=bad)
            self.assertFalse(res.valid)
            self.assertEqual(
                res.status,
                STATUS_BLOCKED_G126_FOLDER_NAMING_CAPACITY_OR_DUAL_SLOT_VIOLATION,
            )
        for good in ("DSC", "FX3", "A_9"):
            res = verify_aperture_drive_and_folder_rating_guard(set_file_name_prefix=good)
            self.assertTrue(res.valid)

    def test_48_g126_4000_image_folder_ceiling_enforced(self) -> None:
        self.assertEqual(FOLDER_IMAGE_CAPACITY_LIMIT_G126, 4000)
        res_max = verify_aperture_drive_and_folder_rating_guard(
            slot1_folder_image_count=4000,
            still_capture_into_current_folder_requested=True,
        )
        self.assertFalse(res_max.valid)
        self.assertTrue(res_max.folder_at_4000_limit)
        self.assertEqual(
            res_max.status,
            STATUS_BLOCKED_G126_FOLDER_NAMING_CAPACITY_OR_DUAL_SLOT_VIOLATION,
        )

    def test_49_g126_dual_slot_select_rec_folder_requires_common_folder(self) -> None:
        res_bad = verify_aperture_drive_and_folder_rating_guard(
            dual_slot_simultaneous_rec=True,
            select_rec_folder_requested=True,
            slot1_slot2_common_folder_exists=False,
        )
        self.assertFalse(res_bad.valid)
        self.assertEqual(
            res_bad.status,
            STATUS_BLOCKED_G126_FOLDER_NAMING_CAPACITY_OR_DUAL_SLOT_VIOLATION,
        )

    def test_50_g126_slot1_vault_blocks_create_new_folder_erofs_eopnotsupp(self) -> None:
        for wp, expected_err in ((True, "EROFS"), (False, "EOPNOTSUPP")):
            res = verify_aperture_drive_and_folder_rating_guard(
                target_media_slot="Slot 1",
                slot_1_write_protected=wp,
                slot_1_contains_tier0_vault=True,
                create_new_folder_requested=True,
            )
            self.assertFalse(res.valid)
            self.assertTrue(res.folder_mutation_blocked)
            self.assertEqual(res.block_errno, expected_err)
            self.assertEqual(res.slot1_metadata_sector_writes, 0)
            self.assertFalse(res.slot1_avf_info_mutated)
            self.assertEqual(
                res.status,
                STATUS_BLOCKED_G126_SLOT1_VAULT_FOLDER_OR_RATING_WRITE_VIOLATION,
            )

    def test_51_g126_slot1_vault_blocks_forced_file_number_reset(self) -> None:
        res = verify_aperture_drive_and_folder_rating_guard(
            target_media_slot="Slot 1",
            slot_1_contains_tier0_vault=True,
            forced_file_number_reset_requested=True,
        )
        self.assertFalse(res.valid)
        self.assertTrue(res.folder_mutation_blocked)
        self.assertEqual(res.block_errno, "EOPNOTSUPP")
        self.assertEqual(
            res.status,
            STATUS_BLOCKED_G126_SLOT1_VAULT_FOLDER_OR_RATING_WRITE_VIOLATION,
        )

    def test_52_g126_dual_slot_simultaneous_create_folder_blocked_by_slot1_vault(self) -> None:
        res = verify_aperture_drive_and_folder_rating_guard(
            target_media_slot="Slot 2",
            dual_slot_simultaneous_rec=True,
            slot_1_contains_tier0_vault=True,
            create_new_folder_requested=True,
        )
        self.assertFalse(res.valid)
        self.assertTrue(res.folder_mutation_blocked)

    def test_53_g126_slot1_vault_blocks_playback_rating_and_add_rating(self) -> None:
        for stars in range(1, 6):
            res = verify_aperture_drive_and_folder_rating_guard(
                target_media_slot="Slot 1",
                slot_1_write_protected=True,
                slot_1_contains_tier0_vault=True,
                rating_requested=True,
                rating_stars=stars,
            )
            self.assertFalse(res.valid)
            self.assertTrue(res.rating_operation_blocked)
            self.assertEqual(res.block_errno, "EROFS")
            self.assertEqual(res.slot1_metadata_sector_writes, 0)
            self.assertFalse(res.slot1_avf_info_mutated)
            self.assertEqual(
                res.status,
                STATUS_BLOCKED_G126_SLOT1_VAULT_FOLDER_OR_RATING_WRITE_VIOLATION,
            )

    def test_54_g126_slot2_non_vault_allows_folder_create_and_rating(self) -> None:
        res = verify_aperture_drive_and_folder_rating_guard(
            target_media_slot="Slot 2",
            slot_1_contains_tier0_vault=True,
            dual_slot_simultaneous_rec=False,
            create_new_folder_requested=True,
            rating_requested=True,
            rating_stars=5,
        )
        self.assertTrue(res.valid)
        self.assertFalse(res.folder_mutation_blocked)
        self.assertFalse(res.rating_operation_blocked)
        self.assertIsNone(res.block_errno)

    def test_55_g126_add_rating_blocked_in_movie_or_already_rated_or_bg_transfer(self) -> None:
        r_mov = verify_aperture_drive_and_folder_rating_guard(
            shoot_mode=SHOOT_MODE_MOVIE_PHASE294,
            target_media_slot="Slot 2",
            rating_add_on_shooting_screen_requested=True,
            rating_stars=3,
        )
        self.assertFalse(r_mov.valid)
        r_dup = verify_aperture_drive_and_folder_rating_guard(
            shoot_mode=SHOOT_MODE_M_PHASE294,
            target_media_slot="Slot 2",
            rating_add_on_shooting_screen_requested=True,
            rating_stars=4,
            rating_existing_stars=2,
        )
        self.assertFalse(r_dup.valid)
        r_bg = verify_aperture_drive_and_folder_rating_guard(
            target_media_slot="Slot 2",
            rating_requested=True,
            rating_stars=2,
            background_transfer_active=True,
        )
        self.assertFalse(r_bg.valid)
        r_ram = verify_aperture_drive_and_folder_rating_guard(
            claimed_rating_is_ram_only_non_card_write=True
        )
        self.assertFalse(r_ram.valid)
        self.assertEqual(
            r_ram.status,
            STATUS_BLOCKED_G126_SLOT1_VAULT_FOLDER_OR_RATING_WRITE_VIOLATION,
        )

    def test_56_g126_fx6_uses_clip_flag_not_consumer_rating(self) -> None:
        res = verify_aperture_drive_and_folder_rating_guard(
            target_model=FX6_MODEL_NAME_PHASE294,
            target_media_slot="Slot 2",
            rating_requested=True,
            rating_stars=4,
        )
        self.assertFalse(res.valid)
        self.assertEqual(
            res.status,
            STATUS_BLOCKED_G126_SLOT1_VAULT_FOLDER_OR_RATING_WRITE_VIOLATION,
        )

    def test_57_g126_invalid_telemetry_rejected(self) -> None:
        for kw in (
            {"rating_stars": 6},
            {"rating_stars": 0},
            {"rating_stars": True},
            {"slot1_folder_image_count": -1},
            {"slot1_folder_image_count": False},
            {"fx6_clip_flag": "INVALID"},
            {"target_media_slot": "Slot 9"},
        ):
            res = verify_aperture_drive_and_folder_rating_guard(**kw)
            self.assertFalse(res.valid)
            self.assertIn(STATUS_BLOCKED_G126_TELEMETRY_INVALID, res.violation_codes)

    def test_58_evaluate_g126_wrapper_clean_room(self) -> None:
        verdict, res = evaluate_g126_aperture_drive_and_folder_rating_guard(force_clean_room=True)
        self.assertTrue(verdict.passed)
        self.assertEqual(verdict.gate_id, G126_GATE_ID)
        self.assertEqual(verdict.gate_code, G126_GATE_CODE)
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_VERIFIED_G126)


class TestPhase294Unified126GatePreflightEngine(unittest.TestCase):
    def test_59_aliases_resolve_to_same_function(self) -> None:
        self.assertIs(evaluate_126_master_safety_gates, evaluate_126gate_preflight)
        self.assertIs(run_126_gate_preflight, evaluate_126gate_preflight)

    def test_60_offline_123_of_126_preflight_stubbed_m124(self) -> None:
        stub = _make_stub_master124(dry_run=False)
        report = evaluate_126gate_preflight(
            repo_root=DEFAULT_REPO_ROOT,
            force_clean_room=True,
            master_124_override=stub,
        )
        self.assertEqual(report.status, "VERIFIED_123_OF_126_AWAITING_PHYSICAL_TIER0")
        self.assertTrue(report.offline_123_gates_verified)
        self.assertFalse(report.all_126_gates_verified)
        self.assertTrue(report.g13_to_g126_all_passed)
        self.assertTrue(report.g125_to_g126_all_passed)
        self.assertEqual(report.summary["verified_gates"], 123)
        self.assertEqual(report.summary["total_gates"], 126)
        self.assertEqual(report.summary["blocked_or_pending_gates"], 3)
        self.assertEqual(len(report.gates), 126)
        self.assertFalse(report.overall_ready_for_hardware_attach)
        self.assertFalse(report.persistent_emmc_writes_authorized)
        self.assertFalse(report.cross_model_flash_authorized)
        self.assertEqual(report.raw_firmware_bytes_leaked, 0)

    def test_61_dry_run_126_of_126_preflight_stubbed_m124(self) -> None:
        stub = _make_stub_master124(dry_run=True)
        report = evaluate_126gate_preflight(
            repo_root=DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            master_124_override=stub,
        )
        self.assertEqual(report.status, "VERIFIED_ALL_126_GATES_DRY_RUN_SIMULATED_BACKUP")
        self.assertTrue(report.offline_123_gates_verified)
        self.assertTrue(report.all_126_gates_verified)
        self.assertTrue(report.dry_run_rehearsal_only)
        self.assertEqual(report.summary["verified_gates"], 126)
        self.assertEqual(report.summary["blocked_or_pending_gates"], 0)
        self.assertFalse(report.overall_ready_for_hardware_attach)
        self.assertFalse(report.hardware_live_attachment_authorized)
        self.assertEqual(report.usb_packets_transmitted, 0)

    def test_62_real_evaluate_126gate_preflight_offline_and_dry_run_clean_room(self) -> None:
        rep_off = evaluate_126gate_preflight(
            repo_root=DEFAULT_REPO_ROOT, force_clean_room=True
        )
        self.assertTrue(rep_off.offline_123_gates_verified)
        self.assertEqual(rep_off.summary["verified_gates"], 123)
        self.assertFalse(rep_off.overall_ready_for_hardware_attach)

        rep_dry = evaluate_126gate_preflight(
            repo_root=DEFAULT_REPO_ROOT, force_clean_room=True, simulate_bench_dry_run=True
        )
        self.assertTrue(rep_dry.all_126_gates_verified)
        self.assertEqual(rep_dry.summary["verified_gates"], 126)
        self.assertFalse(rep_dry.overall_ready_for_hardware_attach)
        self.assertFalse(rep_dry.cross_model_flash_authorized)
        self.assertEqual(rep_dry.raw_firmware_bytes_leaked, 0)

    def test_63_g125_failure_propagates_to_126gate_report(self) -> None:
        stub = _make_stub_master124(dry_run=True)
        rep = evaluate_126gate_preflight(
            repo_root=DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            master_124_override=stub,
            lens_comp_af_illuminator_kwargs={"requested_shading_comp": "Auto: Low"},
        )
        self.assertEqual(
            rep.status,
            STATUS_BLOCKED_G125_DORMANT_AUTO_LOW_OR_RESET_PERSISTENCE_VIOLATION,
        )
        self.assertFalse(rep.g125_to_g126_all_passed)
        self.assertFalse(rep.all_126_gates_verified)

    def test_64_g126_failure_propagates_to_126gate_report(self) -> None:
        stub = _make_stub_master124(dry_run=True)
        rep = evaluate_126gate_preflight(
            repo_root=DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            master_124_override=stub,
            aperture_drive_folder_rating_kwargs={
                "target_media_slot": "Slot 1",
                "slot_1_contains_tier0_vault": True,
                "rating_requested": True,
                "rating_stars": 5,
            },
        )
        self.assertEqual(
            rep.status,
            STATUS_BLOCKED_G126_SLOT1_VAULT_FOLDER_OR_RATING_WRITE_VIOLATION,
        )
        self.assertFalse(rep.g125_to_g126_all_passed)
        self.assertFalse(rep.all_126_gates_verified)

    def test_65_request_persistent_writes_blocks_126gate_preflight(self) -> None:
        stub = _make_stub_master124(dry_run=True)
        rep = evaluate_126gate_preflight(
            repo_root=DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            master_124_override=stub,
            request_persistent_emmc_writes=True,
        )
        self.assertEqual(rep.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        self.assertFalse(rep.offline_123_gates_verified)
        self.assertFalse(rep.all_126_gates_verified)

    def test_66_backward_compatibility_124gate_preflight_still_passes(self) -> None:
        m124 = evaluate_124gate_preflight(
            repo_root=DEFAULT_REPO_ROOT, force_clean_room=True, simulate_bench_dry_run=True
        )
        self.assertTrue(m124.all_124_gates_verified)
        self.assertEqual(m124.summary["verified_gates"], 124)

    def test_67_report_json_serializable_and_dataclass(self) -> None:
        stub = _make_stub_master124(dry_run=False)
        rep = evaluate_126gate_preflight(
            repo_root=DEFAULT_REPO_ROOT, force_clean_room=True, master_124_override=stub
        )
        self.assertTrue(dataclasses.is_dataclass(rep))
        encoded = json.dumps(rep.to_dict(), ensure_ascii=False)
        decoded = json.loads(encoded)
        self.assertEqual(decoded["summary"]["total_gates"], 126)
        self.assertEqual(decoded["gates"][-2]["gate_id"], "G125")
        self.assertEqual(decoded["gates"][-1]["gate_id"], "G126")


class TestPhase294CliAndCrossPlatformCiHygiene(unittest.TestCase):
    def _run_cli(self, argv: list[str]) -> tuple[int, str]:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cli_main(argv)
        return rc, buf.getvalue()

    def test_68_cli_verify_g125_summary_json(self) -> None:
        rc, out = self._run_cli(
            ["verify-lens-comp-and-af-illuminator-guard", "--clean-room", "--summary", "--json"]
        )
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["gate"], "G125")
        self.assertEqual(data["status"], STATUS_VERIFIED_G125)
        self.assertTrue(data["fx3_has_built_in_af_illuminator_led"])
        self.assertFalse(data["fx6_has_built_in_af_illuminator_led"])

    def test_69_cli_verify_g125_alias_text(self) -> None:
        rc, out = self._run_cli(["verify-g125-lens-comp-af-illuminator", "--clean-room"])
        self.assertEqual(rc, 0)
        self.assertIn("gate=G125", out)
        self.assertIn("fx3_led=True", out)
        self.assertIn("fx6_led=False", out)

    def test_70_cli_verify_g126_summary_json(self) -> None:
        rc, out = self._run_cli(
            ["verify-aperture-drive-and-folder-rating-guard", "--clean-room", "--summary", "--json"]
        )
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["gate"], "G126")
        self.assertEqual(data["status"], STATUS_VERIFIED_G126)
        self.assertTrue(data["slot_1_contains_tier0_vault"])
        self.assertEqual(data["slot1_metadata_sector_writes"], 0)

    def test_71_cli_verify_g126_alias_text(self) -> None:
        rc, out = self._run_cli(["verify-g126-aperture-drive-folder-rating", "--clean-room"])
        self.assertEqual(rc, 0)
        self.assertIn("gate=G126", out)
        self.assertIn("slot1_vault=True", out)
        self.assertIn("s1_writes=0", out)

    def test_72_cli_verify_126_gates_offline_text_and_json(self) -> None:
        rc, out = self._run_cli(["verify-126-gates", "--clean-room"])
        self.assertEqual(rc, 0)
        self.assertIn("verified=123/126", out)
        self.assertIn("overall_ready_for_hardware_attach=False", out)
        rc2, out2 = self._run_cli(["verify-126-gates", "--clean-room", "--summary", "--json"])
        self.assertEqual(rc2, 0)
        data = json.loads(out2)
        self.assertEqual(data["summary"]["verified_gates"], 123)
        self.assertEqual(data["g125_status"], STATUS_VERIFIED_G125)
        self.assertEqual(data["g126_status"], STATUS_VERIFIED_G126)

    def test_73_cli_verify_126_gates_dry_run_text_and_json(self) -> None:
        rc, out = self._run_cli(["verify-126-gates", "--clean-room", "--simulate-bench-dry-run"])
        self.assertEqual(rc, 0)
        self.assertIn("verified=126/126", out)
        self.assertIn("all_126_gates_verified=True", out)
        self.assertIn("cross_model_flash_authorized=False", out)
        rc2, out2 = self._run_cli(
            ["verify-126-gates", "--clean-room", "--simulate-bench-dry-run", "--summary", "--json"]
        )
        self.assertEqual(rc2, 0)
        data = json.loads(out2)
        self.assertEqual(data["status"], "VERIFIED_ALL_126_GATES_DRY_RUN_SIMULATED_BACKUP")
        self.assertEqual(data["summary"]["verified_gates"], 126)

    def test_74_module_standalone_main_entrypoint(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = module_main(["--clean-room", "--simulate-bench-dry-run", "--summary", "--json"])
        self.assertEqual(rc, 0)
        data = json.loads(buf.getvalue())
        self.assertEqual(data["summary"]["verified_gates"], 126)

    def test_75_argparse_help_python314_safe_across_all_phase294_cmds(self) -> None:
        for cmd in (
            "verify-lens-comp-and-af-illuminator-guard",
            "verify-aperture-drive-and-folder-rating-guard",
            "verify-126-gates",
        ):
            with self.assertRaises(SystemExit) as ctx:
                cli_main([cmd, "--help"])
            self.assertEqual(ctx.exception.code, 0)
        with self.assertRaises(SystemExit) as ctx2:
            module_main(["--help"])
        self.assertEqual(ctx2.exception.code, 0)

    def test_76_subprocess_uses_sys_executable_not_hardcoded_usr_bin_python3(self) -> None:
        mod_src = (
            DEFAULT_REPO_ROOT
            / "outputs/fx3-safety/fx3_safety"
            / "realhw_lens_comp_af_illuminator_aperture_drive_folder_rating_and_126gate_guard.py"
        ).read_text(encoding="utf-8")
        test_src = Path(__file__).read_text(encoding="utf-8")
        forbidden_py = "/usr/bin/" + "python3"
        self.assertNotIn(forbidden_py, mod_src)
        self.assertNotIn(forbidden_py, test_src)

    def test_77_subprocess_cli_verify_126_gates_clean_room(self) -> None:
        timeout_s = 15.0 if os.environ.get("GITHUB_ACTIONS") == "true" else 10.0
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONPATH"] = str(DEFAULT_REPO_ROOT / "outputs/fx3-safety")
        proc = subprocess.run(
            [sys.executable, "-B", "-m", "fx3_safety", "verify-126-gates", "--clean-room", "--simulate-bench-dry-run", "--summary", "--json"],
            cwd=str(DEFAULT_REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        data = json.loads(proc.stdout)
        self.assertEqual(data["summary"]["verified_gates"], 126)

    def test_78_no_init_shadowing_of_phase286_288_290_symbols(self) -> None:
        self.assertNotEqual(
            fx3_safety.G125_GATE_ID,
            fx3_safety.G123_GATE_ID,
        )
        self.assertNotEqual(
            fx3_safety.G126_GATE_ID,
            fx3_safety.G124_GATE_ID,
        )
        self.assertTrue(fx3_safety.G119_GATE_ID.startswith("G119"))
        self.assertTrue(fx3_safety.G121_GATE_ID.startswith("G121"))
        self.assertTrue(fx3_safety.G123_GATE_ID.startswith("G123"))
        self.assertTrue(fx3_safety.G124_GATE_ID.startswith("G124"))
        self.assertEqual(fx3_safety.G125_GATE_ID, "G125")
        self.assertEqual(fx3_safety.G126_GATE_ID, "G126")
        self.assertFalse(fx3_safety.CROSS_MODEL_FLASH_AUTHORIZED)

    def test_79_resolve_g125_with_default_args_smoke(self) -> None:
        st = resolve_fx3_lens_comp_and_af_illuminator_state()
        self.assertEqual(st["effective_shading_comp"], "Auto")
        self.assertEqual(st["effective_ca_comp"], "Auto")
        self.assertEqual(st["effective_distortion_comp"], "Off")

    def test_80_resolve_g126_with_default_args_smoke(self) -> None:
        st = resolve_fx3_aperture_drive_and_folder_rating_state()
        self.assertEqual(st["effective_aperture_drive_in_af"], "Standard")
        self.assertEqual(st["effective_focus_area_color"], "White")
        self.assertTrue(st["select_rec_folder_enabled"])

    def test_81_g126_slot1_write_protect_plus_dual_slot_rating_blocked(self) -> None:
        res = verify_aperture_drive_and_folder_rating_guard(
            target_media_slot="Slot 1+2",
            slot_1_write_protected=True,
            slot_1_contains_tier0_vault=False,
            rating_requested=True,
            rating_stars=1,
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.block_errno, "EROFS")
        self.assertTrue(res.rating_operation_blocked)

    def test_82_g125_af_illuminator_off_disables_active_trigger_in_still(self) -> None:
        eff = resolve_fx3_lens_comp_and_af_illuminator_state(
            shoot_mode=SHOOT_MODE_M_PHASE294,
            focus_mode="AF-S",
            requested_af_illuminator=AF_ILLUMINATOR_OFF_G125,
            mi_shoe_flash_illuminator_attached=True,
        )
        self.assertFalse(eff["af_illuminator_active"])
        self.assertFalse(eff["mi_shoe_flash_illuminator_active"])

    def test_83_g125_af_a_stationary_subject_still_allows_af_illuminator(self) -> None:
        eff = resolve_fx3_lens_comp_and_af_illuminator_state(
            shoot_mode=SHOOT_MODE_P_PHASE294,
            focus_mode="AF-A",
            subject_moving_in_af_a=False,
            requested_af_illuminator=AF_ILLUMINATOR_AUTO_G125,
        )
        self.assertTrue(eff["af_illuminator_active"])

    def test_84_g126_file_number_series_and_reset_modes(self) -> None:
        r_ser = verify_aperture_drive_and_folder_rating_guard(
            requested_file_number_mode=FILE_NUMBER_SERIES_G126
        )
        self.assertTrue(r_ser.valid)
        r_rst = verify_aperture_drive_and_folder_rating_guard(
            requested_file_number_mode=FILE_NUMBER_RESET_G126
        )
        self.assertTrue(r_rst.valid)
        self.assertEqual(r_rst.effective_file_number_mode, FILE_NUMBER_RESET_G126)

    def test_85_g126_dual_slot_select_rec_folder_allowed_when_common_exists_on_standard_form(self) -> None:
        res = verify_aperture_drive_and_folder_rating_guard(
            requested_folder_name_form=FOLDER_NAME_STANDARD_FORM_G126,
            dual_slot_simultaneous_rec=True,
            select_rec_folder_requested=True,
            slot1_slot2_common_folder_exists=True,
        )
        self.assertTrue(res.valid)
        self.assertTrue(res.select_rec_folder_enabled)

    def test_86_cli_verify_126_gates_offline_vs_dryrun_consistency(self) -> None:
        with mock.patch.dict(os.environ, {ENV_CLEAN_ROOM_TEST_PHASE294: "1"}, clear=False):
            rc_off, out_off = self._run_cli(["verify-126-gates", "--json", "--summary"])
            rc_dry, out_dry = self._run_cli(
                ["verify-126-gates", "--simulate-bench-dry-run", "--json", "--summary"]
            )
            self.assertEqual(rc_off, 0)
            self.assertEqual(rc_dry, 0)
            d_off = json.loads(out_off)
            d_dry = json.loads(out_dry)
            self.assertEqual(d_off["summary"]["verified_gates"], 123)
            self.assertEqual(d_dry["summary"]["verified_gates"], 126)
            self.assertFalse(d_dry["summary"]["overall_ready_for_hardware_attach"])


if __name__ == "__main__":
    unittest.main()
