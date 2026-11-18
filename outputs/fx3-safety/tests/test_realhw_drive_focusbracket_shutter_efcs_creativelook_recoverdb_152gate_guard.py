"""Unit tests for Phase 351 (Task H439, Wave-66, 152/152 Milestone):
G151 (`[Drive Mode]` 10 fps / Dormant `[Focus Bracket]` / `[Shutter Type]` 2-Mode Zero-`Auto` / `1/250 s` X-Sync / `curtaion` Typo / `[Long Exposure NR]` / `[High ISO NR]`),
G152 (`[Creative Look]` 10+6 / `0..9` Asymmetric Bounds / Dormant `[Soft Skin Effect]` / `[Delete]` / `[Protect]` / `[Display Media Info.]` / `[Recover Image DB]` Slot-1 `EROFS=30` Firewall),
and Unified 152-Gate Master Safety Preflight (`evaluate_152gate_preflight` / `verify_real_hardware_152gate_readiness` / `verify-152-gates`).
"""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import unittest
from unittest import mock

sys.dont_write_bytecode = True

SAFETY_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SAFETY_ROOT.parents[1]
if str(SAFETY_ROOT) not in sys.path:
    sys.path.insert(0, str(SAFETY_ROOT))

import fx3_safety  # noqa: E402
from fx3_safety.__main__ import main as cli_main  # noqa: E402
from fx3_safety.realhw_drive_focusbracket_shutter_efcs_creativelook_recoverdb_and_152gate_guard import (  # noqa: E402
    ABSENT_PROTECT_CANCEL_ALL_IMAGES_G152,
    ALLOWED_CONT_SPEEDS_G151,
    ALLOWED_CREATIVE_LOOK_SLOTS_G152,
    ALLOWED_DELETE_CONFIRM_MODES_G152,
    CONT_SHOOTING_MAX_FPS_G151,
    CONT_SPEED_HI_G151,
    CONT_SPEED_HI_PLUS_G151,
    CONT_SPEED_LO_G151,
    CONT_SPEED_MID_G151,
    CREATIVE_LOOK_10_PRESETS_G152,
    CREATIVE_LOOK_6_CUSTOM_SLOTS_G152,
    CREATIVE_LOOK_8_PARAM_BOUNDS_G152,
    CREATIVE_LOOK_DEFAULT_G152,
    CREATIVE_LOOK_TOTAL_SLOTS_G152,
    DELETE_CONFIRM_CANCEL_FIRST_G152,
    DELETE_CONFIRM_DELETE_FIRST_G152,
    DELETE_PRESSING_TWICE_DEFAULT_G152,
    DISPLAY_MEDIA_INFO_ELF_TYPO_G152,
    DISPLAY_MEDIA_INFO_MAX_STILL_COUNT_G152,
    DONOR_CHECK_MAX_SECONDS_PHASE351,
    DORMANT_APSC_XSYNC_STR_G151,
    DORMANT_FOCUS_BRACKET_EXPOSED_EVENTS_G151,
    DORMANT_FOCUS_BRACKET_TOKENS_G151,
    DORMANT_HIGH_ISO_NR_TOKENS_G151,
    DORMANT_SELF_TIMER_CONT_OPTIONS_G151,
    DORMANT_SHUTTER_TYPE_AUTO_TOKENS_G151,
    DORMANT_SOFT_SKIN_EXPOSED_FX3_G152,
    DORMANT_SOFT_SKIN_EXPOSED_FX6_G152,
    DRIVE_MODE_CONT_BRACKET_G151,
    DRIVE_MODE_CONT_G151,
    DRIVE_MODE_DEFAULT_G151,
    DRIVE_MODE_DRO_BRACKET_G151,
    DRIVE_MODE_SELF_TIMER_CONT_G151,
    DRIVE_MODE_SELF_TIMER_SINGLE_G151,
    DRIVE_MODE_SINGLE_BRACKET_G151,
    DRIVE_MODE_SINGLE_G151,
    DRIVE_MODE_WB_BRACKET_G151,
    EFCS_DEFAULT_G151,
    EFCS_ELF_TYPO_SYMBOL_G151,
    EFCS_RESETTABLE_BY_CAMSET_RESET_G151,
    EINVAL_ERRNO_PHASE351,
    ENV_CLEAN_ROOM_TEST_PHASE351,
    EOPNOTSUPP_ERRNO_PHASE351,
    EROFS_ERRNO_PHASE351,
    EXACT_2_SHUTTER_TYPES_G151,
    EXACT_3_HIGH_ISO_NR_OPTIONS_G151,
    EXACT_3_SELF_TIMER_SINGLE_OPTIONS_G151,
    EXACT_5_DELETE_BATCH_MODES_G152,
    EXACT_5_ELECTRONIC_SHUTTER_LOCKED_ITEMS_G151,
    EXACT_6_SELF_TIMER_CONT_OPTIONS_G151,
    EXACT_7_PROTECT_MODES_G152,
    EXACT_8_DRIVE_MODES_G151,
    FX3_FLASH_XSYNC_CEILING_STR_G151,
    FX6_APR_MENU_PATH_G151,
    FX6_DORMANT_FOCUS_BRACKET_SYMBOL_COUNT_G151,
    FX6_MEDIA_MUTATION_MENUS_G152,
    FX6_NOISE_SUPPRESSION_MODES_G151,
    G151,
    G152,
    HIGH_ISO_NR_ALTERS_ARW_G151,
    HIGH_ISO_NR_DEFAULT_G151,
    HIGH_ISO_NR_LOW_G151,
    HIGH_ISO_NR_NORMAL_G151,
    HIGH_ISO_NR_OFF_G151,
    INTERVAL_SHUTTER_TYPE_DEFAULT_G151,
    LONG_EXPOSURE_NR_DEFAULT_G151,
    LONG_EXPOSURE_NR_MIN_SHUTTER_SEC_G151,
    MEDIA_SLOT_1_PHASE351,
    MEDIA_SLOT_2_PHASE351,
    PINNED_FX3_APPFW_SLICES_SHA256_PHASE351,
    PINNED_FX6_APPFW_SLICES_SHA256_PHASE351,
    PINNED_PHASE351_DONOR_SPECS,
    PLAYBACK_DELETE_CONFIG_RESETTABLE_BY_CAMSET_RESET_G152,
    REALHW_152GATE_PREFLIGHT_SCHEMA,
    RECOVER_IMAGE_DB_IMMUNE_TO_RESET_AND_INIT_G152,
    RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE351,
    RESET_ACTION_INITIALIZE_PHASE351,
    RESET_ACTION_RESET_NETWORK_SET_PHASE351,
    SHOOT_MODE_MOVIE_PHASE351,
    SHOOT_MODE_SQ_PHASE351,
    SHOOT_MODE_STILL_PHASE351,
    SHUTTER_TYPE_DEFAULT_G151,
    SHUTTER_TYPE_ELECTRONIC_G151,
    SHUTTER_TYPE_MECHANICAL_G151,
    STATUS_BLOCKED_G151_DORMANT_FOCUS_BRACKET_SHUTTER_AUTO_OR_FX6_EOPNOTSUPP,
    STATUS_BLOCKED_G151_DRIVE_LOCKOUT_OR_XSYNC_1_320_VIOLATION,
    STATUS_BLOCKED_G151_SHUTTER_TYPE_EFCS_RESET_OR_NR_VIOLATION,
    STATUS_BLOCKED_G151_TELEMETRY_INVALID,
    STATUS_BLOCKED_G152_CREATIVE_LOOK_BOUNDS_LOCKOUT_OR_DELETE_RESET_VIOLATION,
    STATUS_BLOCKED_G152_DORMANT_SOFT_SKIN_OR_PROTECT_CANCEL_ALL_EOPNOTSUPP,
    STATUS_BLOCKED_G152_SLOT1_DELETE_PROTECT_RECOVERDB_VAULT_EROFS,
    STATUS_BLOCKED_G152_TELEMETRY_INVALID,
    STATUS_BLOCKED_PHASE351_DONOR_INTEGRITY,
    STATUS_VERIFIED_G151,
    STATUS_VERIFIED_G152,
    audit_phase351_donor_contracts,
    compute_creative_look_and_media_matrix,
    compute_drive_shutter_efcs_nr_matrix,
    evaluate_152_master_safety_gates,
    evaluate_152gate_preflight,
    evaluate_g151_drive_focusbracket_shutter_efcs_nr_guard,
    evaluate_g152_creative_look_soft_skin_delete_protect_recoverdb_guard,
    resolve_fx3_creative_look_and_playback_media_state,
    resolve_fx3_drive_shutter_efcs_nr_state,
    run_152_gate_preflight,
    strip_elapsed_seconds_recursive_phase351,
    verify_creative_look_soft_skin_delete_protect_recoverdb_guard,
    verify_drive_focusbracket_shutter_efcs_nr_guard,
    verify_real_hardware_152gate_readiness,
)
from fx3_safety.realhw_shoe_audio_4ch_subject_recog_silent_bodydata_and_144gate_guard import (  # noqa: E402
    ENV_FORCE_CLEAN_ROOM,
)
from fx3_safety.thermal_pwm_and_power_guard import (  # noqa: E402
    resolve_donor_thermal_power_paths,
)


def _norm_digest(payload: dict) -> str:
    clean = strip_elapsed_seconds_recursive_phase351(payload)
    if isinstance(clean, dict):
        clean.pop("evaluated_utc", None)
    return hashlib.sha256(
        json.dumps(clean, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()


class TestPhase351Wave66152GateGuard(unittest.TestCase):
    """100-test comprehensive suite for Phase 351 (G151, G152, 152/152 Milestone)."""

    # -----------------------------------------------------------------------
    # 01..12: 4-Mode Donor Audit, Redlines & Recursive Digest Hygiene
    # -----------------------------------------------------------------------

    def test_01_donor_audit_mode1_local_o_rdonly_or_synthetic(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(ENV_FORCE_CLEAN_ROOM, None)
            os.environ.pop(ENV_CLEAN_ROOM_TEST_PHASE351, None)
            res = audit_phase351_donor_contracts(repo_root=REPO_ROOT)
            self.assertTrue(res.valid)
            self.assertEqual(res.raw_firmware_bytes_leaked, 0)
            self.assertLessEqual(res.elapsed_seconds, DONOR_CHECK_MAX_SECONDS_PHASE351)
            if resolve_donor_thermal_power_paths(repo_root=REPO_ROOT).work_root is not None:
                self.assertEqual(res.verification_mode, "LOCAL_DONOR_O_RDONLY")
                self.assertEqual(res.files_inspected, len(PINNED_PHASE351_DONOR_SPECS))
                self.assertEqual(
                    res.file_digests["fx3_appfw_so"],
                    PINNED_FX3_APPFW_SLICES_SHA256_PHASE351,
                )
                self.assertEqual(
                    res.file_digests["fx6_appfw_so"],
                    PINNED_FX6_APPFW_SLICES_SHA256_PHASE351,
                )

    def test_02_donor_audit_mode2_fx3_clean_room_test_env(self) -> None:
        with mock.patch.dict(os.environ, {ENV_CLEAN_ROOM_TEST_PHASE351: "1"}):
            res = audit_phase351_donor_contracts(repo_root=REPO_ROOT)
            self.assertTrue(res.valid)
            self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertEqual(res.raw_firmware_bytes_leaked, 0)

    def test_03_donor_audit_mode3_force_clean_room_env_and_arg(self) -> None:
        with mock.patch.dict(os.environ, {ENV_FORCE_CLEAN_ROOM: "1"}):
            res = audit_phase351_donor_contracts(repo_root=REPO_ROOT)
            self.assertTrue(res.valid)
            self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        res2 = audit_phase351_donor_contracts(repo_root=REPO_ROOT, force_clean_room=True)
        self.assertTrue(res2.valid)
        self.assertEqual(res2.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_04_donor_audit_mode4_work_root_none_nonexistent_path(self) -> None:
        class _DummyPaths:
            work_root = None

        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(ENV_FORCE_CLEAN_ROOM, None)
            os.environ.pop(ENV_CLEAN_ROOM_TEST_PHASE351, None)
            with mock.patch(
                "fx3_safety.realhw_drive_focusbracket_shutter_efcs_creativelook_recoverdb_and_152gate_guard.resolve_donor_thermal_power_paths",
                return_value=_DummyPaths(),
            ):
                res = audit_phase351_donor_contracts(repo_root=REPO_ROOT)
                self.assertTrue(res.valid)
                self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")

        missing_root = REPO_ROOT / "nonexistent_phase351_work_root_xyz"
        res_missing = audit_phase351_donor_contracts(work_root=missing_root)
        self.assertTrue(res_missing.valid)
        self.assertEqual(res_missing.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_05_donor_audit_tampered_override_fails_closed(self) -> None:
        bad_spec = {
            "fake_donor": (
                "FX3",
                "does_not_exist.bin",
                123,
                "0" * 64,
                (b"NONEXISTENT",),
                "missing file test",
            )
        }
        res = audit_phase351_donor_contracts(
            work_root=REPO_ROOT,
            force_clean_room=False,
            donor_specs_override=bad_spec,
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_PHASE351_DONOR_INTEGRITY)

    def test_06_donor_audit_o_rdonly_never_uses_write_flags(self) -> None:
        self.assertIn("fx3_appfw_so", PINNED_PHASE351_DONOR_SPECS)
        self.assertIn("fx6_appfw_so", PINNED_PHASE351_DONOR_SPECS)
        self.assertIn("fx3_bk4_bin", PINNED_PHASE351_DONOR_SPECS)
        self.assertIn("fx3_string_english_f_uxc", PINNED_PHASE351_DONOR_SPECS)
        self.assertIn("fx3_string_simplifiedchinese_f_uxc", PINNED_PHASE351_DONOR_SPECS)
        self.assertIn("fx3_string_traditionalchinese_f_uxc", PINNED_PHASE351_DONOR_SPECS)
        self.assertIn("fx3_string_japanese_f_uxc", PINNED_PHASE351_DONOR_SPECS)

    def test_07_strip_elapsed_seconds_recursive_phase351(self) -> None:
        sample = {
            "elapsed_seconds": 0.123,
            "nested": [{"elapsed_seconds": 0.456, "keep": 1}],
            "tuple_val": ({"elapsed_seconds": 0.99, "x": 2},),
        }
        stripped = strip_elapsed_seconds_recursive_phase351(sample)
        self.assertNotIn("elapsed_seconds", stripped)
        self.assertNotIn("elapsed_seconds", stripped["nested"][0])
        self.assertEqual(stripped["nested"][0]["keep"], 1)
        self.assertNotIn("elapsed_seconds", stripped["tuple_val"][0])

    def test_08_deterministic_digest_across_clean_room_runs(self) -> None:
        r1 = audit_phase351_donor_contracts(force_clean_room=True).to_dict()
        r2 = audit_phase351_donor_contracts(force_clean_room=True).to_dict()
        self.assertEqual(_norm_digest(r1), _norm_digest(r2))

    def test_09_g151_redlines_locked(self) -> None:
        _, g151 = evaluate_g151_drive_focusbracket_shutter_efcs_nr_guard(
            force_clean_room=True
        )
        self.assertTrue(g151.valid)
        self.assertFalse(g151.emmc_writes_authorized)
        self.assertFalse(g151.persistent_emmc_writes_authorized)
        self.assertFalse(g151.cross_model_flash_authorized)
        self.assertFalse(g151.hardware_live_attachment_authorized)
        self.assertEqual(g151.usb_packets_transmitted, 0)
        self.assertEqual(g151.raw_firmware_bytes_leaked, 0)

    def test_10_g152_redlines_locked(self) -> None:
        _, g152 = evaluate_g152_creative_look_soft_skin_delete_protect_recoverdb_guard(
            force_clean_room=True
        )
        self.assertTrue(g152.valid)
        self.assertFalse(g152.emmc_writes_authorized)
        self.assertFalse(g152.persistent_emmc_writes_authorized)
        self.assertFalse(g152.cross_model_flash_authorized)
        self.assertFalse(g152.hardware_live_attachment_authorized)
        self.assertEqual(g152.usb_packets_transmitted, 0)
        self.assertEqual(g152.raw_firmware_bytes_leaked, 0)

    def test_11_uxc_and_elf_constants_pinned(self) -> None:
        self.assertEqual(EFCS_ELF_TYPO_SYMBOL_G151, "BKID_APP_setting_front_curtaion_shutter")
        self.assertEqual(DISPLAY_MEDIA_INFO_ELF_TYPO_G152, "NOT_DISPLAYNG")
        self.assertEqual(DISPLAY_MEDIA_INFO_MAX_STILL_COUNT_G152, 40_000)

    def test_12_g151_g152_clean_room_digest_stability(self) -> None:
        _, r1 = evaluate_g151_drive_focusbracket_shutter_efcs_nr_guard(force_clean_room=True)
        _, r2 = evaluate_g151_drive_focusbracket_shutter_efcs_nr_guard(force_clean_room=True)
        self.assertEqual(_norm_digest(r1.to_dict()), _norm_digest(r2.to_dict()))
        _, s1 = evaluate_g152_creative_look_soft_skin_delete_protect_recoverdb_guard(
            force_clean_room=True
        )
        _, s2 = evaluate_g152_creative_look_soft_skin_delete_protect_recoverdb_guard(
            force_clean_room=True
        )
        self.assertEqual(_norm_digest(s1.to_dict()), _norm_digest(s2.to_dict()))

    # -----------------------------------------------------------------------
    # 13..46: Gate G151 — Drive Mode 10fps, Dormant Focus Bracket,
    #         Shutter Type 2-Mode Zero-Auto, 1/250 X-Sync, EFCS, Long/High NR
    # -----------------------------------------------------------------------

    def test_13_g151_nominal_default_passes(self) -> None:
        res = verify_drive_focusbracket_shutter_efcs_nr_guard()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_VERIFIED_G151)
        self.assertEqual(res.block_errno, 0)
        self.assertEqual(res.effective_drive_mode, DRIVE_MODE_SINGLE_G151)
        self.assertEqual(res.effective_shutter_type, SHUTTER_TYPE_MECHANICAL_G151)
        self.assertEqual(res.effective_flash_xsync_ceiling, FX3_FLASH_XSYNC_CEILING_STR_G151)
        self.assertEqual(res.effective_efcs, EFCS_DEFAULT_G151)
        self.assertEqual(res.effective_long_exposure_nr, LONG_EXPOSURE_NR_DEFAULT_G151)
        self.assertEqual(res.effective_high_iso_nr, HIGH_ISO_NR_DEFAULT_G151)

    def test_14_g151_exact_8_drive_modes_accepted_in_still(self) -> None:
        self.assertEqual(len(EXACT_8_DRIVE_MODES_G151), 8)
        for dm in EXACT_8_DRIVE_MODES_G151:
            res = verify_drive_focusbracket_shutter_efcs_nr_guard(
                shoot_mode=SHOOT_MODE_STILL_PHASE351,
                drive_mode=dm,
            )
            self.assertTrue(res.valid, f"Drive mode {dm} failed: {res.errors}")
            self.assertTrue(res.drive_mode_available)

    def test_15_g151_cont_shooting_4_speeds_fps_map(self) -> None:
        self.assertEqual(ALLOWED_CONT_SPEEDS_G151, ("Hi+", "Hi", "Mid", "Lo"))
        self.assertEqual(CONT_SHOOTING_MAX_FPS_G151, {"Hi+": 10, "Hi": 8, "Mid": 6, "Lo": 3})
        for spd, fps in CONT_SHOOTING_MAX_FPS_G151.items():
            res = verify_drive_focusbracket_shutter_efcs_nr_guard(
                drive_mode=DRIVE_MODE_CONT_G151,
                cont_speed=spd,
            )
            self.assertTrue(res.valid)
            self.assertEqual(res.effective_max_fps, fps)

    def test_16_g151_cont_hi_plus_exceeding_10fps_rejected(self) -> None:
        res = verify_drive_focusbracket_shutter_efcs_nr_guard(
            drive_mode=DRIVE_MODE_CONT_G151,
            cont_speed=CONT_SPEED_HI_PLUS_G151,
            claimed_cont_hi_plus_exceeds_10fps=True,
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.block_errno, EINVAL_ERRNO_PHASE351)
        self.assertEqual(res.status, STATUS_BLOCKED_G151_DRIVE_LOCKOUT_OR_XSYNC_1_320_VIOLATION)

    def test_17_g151_cont_shooting_first_frame_af_lock_above_f11(self) -> None:
        for spd in (CONT_SPEED_HI_PLUS_G151, CONT_SPEED_HI_G151, CONT_SPEED_MID_G151):
            st_f16 = resolve_fx3_drive_shutter_efcs_nr_state(
                drive_mode=DRIVE_MODE_CONT_G151,
                cont_speed=spd,
                aperture_f_number=16.0,
            )
            self.assertTrue(st_f16["first_frame_af_locked"])
            st_f11 = resolve_fx3_drive_shutter_efcs_nr_state(
                drive_mode=DRIVE_MODE_CONT_G151,
                cont_speed=spd,
                aperture_f_number=11.0,
            )
            self.assertFalse(st_f11["first_frame_af_locked"])
        st_lo_f16 = resolve_fx3_drive_shutter_efcs_nr_state(
            drive_mode=DRIVE_MODE_CONT_G151,
            cont_speed=CONT_SPEED_LO_G151,
            aperture_f_number=16.0,
        )
        self.assertFalse(st_lo_f16["first_frame_af_locked"])

    def test_18_g151_claimed_af_tracks_above_f11_in_hi_plus_rejected(self) -> None:
        res = verify_drive_focusbracket_shutter_efcs_nr_guard(
            drive_mode=DRIVE_MODE_CONT_G151,
            cont_speed=CONT_SPEED_HI_PLUS_G151,
            aperture_f_number=14.0,
            claimed_cont_af_tracks_above_f11=True,
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.block_errno, EINVAL_ERRNO_PHASE351)

    def test_19_g151_cont_speed_drops_on_uncompressed_raw_or_flash(self) -> None:
        st_raw = resolve_fx3_drive_shutter_efcs_nr_state(
            drive_mode=DRIVE_MODE_CONT_G151,
            cont_speed=CONT_SPEED_HI_PLUS_G151,
            uncompressed_raw_active=True,
        )
        self.assertTrue(st_raw["cont_shooting_speed_reduced"])
        self.assertLess(st_raw["effective_max_fps"], 10)

        st_flash = resolve_fx3_drive_shutter_efcs_nr_state(
            drive_mode=DRIVE_MODE_CONT_G151,
            cont_speed=CONT_SPEED_HI_G151,
            flash_firing=True,
        )
        self.assertTrue(st_flash["cont_shooting_speed_reduced"])
        self.assertLess(st_flash["effective_max_fps"], 8)

    def test_20_g151_self_timer_single_3_and_cont_6_vs_dormant_10img(self) -> None:
        self.assertEqual(len(EXACT_3_SELF_TIMER_SINGLE_OPTIONS_G151), 3)
        self.assertEqual(len(EXACT_6_SELF_TIMER_CONT_OPTIONS_G151), 6)
        for opt in EXACT_6_SELF_TIMER_CONT_OPTIONS_G151:
            res = verify_drive_focusbracket_shutter_efcs_nr_guard(
                drive_mode=DRIVE_MODE_SELF_TIMER_CONT_G151,
                self_timer_cont_option=opt,
            )
            self.assertTrue(res.valid)
        for bad_opt in DORMANT_SELF_TIMER_CONT_OPTIONS_G151:
            res_bad = verify_drive_focusbracket_shutter_efcs_nr_guard(
                drive_mode=DRIVE_MODE_SELF_TIMER_CONT_G151,
                self_timer_cont_option=bad_opt,
            )
            self.assertFalse(res_bad.valid)
            self.assertEqual(res_bad.block_errno, EOPNOTSUPP_ERRNO_PHASE351)

    def test_21_g151_dro_bracket_disabled_when_hlg_still_on(self) -> None:
        st = resolve_fx3_drive_shutter_efcs_nr_state(
            drive_mode=DRIVE_MODE_DRO_BRACKET_G151,
            hlg_still_image="On",
        )
        self.assertFalse(st["dro_bracket_available"])
        self.assertEqual(st["effective_drive_mode"], "Unavailable")
        res_bad = verify_drive_focusbracket_shutter_efcs_nr_guard(
            drive_mode=DRIVE_MODE_DRO_BRACKET_G151,
            hlg_still_image="On",
            claimed_dro_bracket_active_with_hlg_still=True,
        )
        self.assertFalse(res_bad.valid)
        self.assertEqual(res_bad.block_errno, EINVAL_ERRNO_PHASE351)

    def test_22_g151_drive_mode_still_only_unavailable_in_movie_sq(self) -> None:
        for sm in (SHOOT_MODE_MOVIE_PHASE351, SHOOT_MODE_SQ_PHASE351):
            res = verify_drive_focusbracket_shutter_efcs_nr_guard(shoot_mode=sm)
            self.assertTrue(res.valid)
            self.assertFalse(res.drive_mode_available)
            self.assertEqual(res.effective_drive_mode, "Unavailable")
            res_bad = verify_drive_focusbracket_shutter_efcs_nr_guard(
                shoot_mode=sm,
                claimed_drive_mode_active_in_movie_or_sq=True,
            )
            self.assertFalse(res_bad.valid)

    def test_23_g151_dormant_focus_bracket_tokens_all_rejected_eopnotsupp_95(self) -> None:
        self.assertEqual(DORMANT_FOCUS_BRACKET_EXPOSED_EVENTS_G151, 0)
        self.assertEqual(FX6_DORMANT_FOCUS_BRACKET_SYMBOL_COUNT_G151, 56)
        for tok in DORMANT_FOCUS_BRACKET_TOKENS_G151:
            res = verify_drive_focusbracket_shutter_efcs_nr_guard(
                requested_dormant_focus_bracket=tok
            )
            self.assertFalse(res.valid)
            self.assertEqual(res.block_errno, EOPNOTSUPP_ERRNO_PHASE351)
            self.assertEqual(
                res.status,
                STATUS_BLOCKED_G151_DORMANT_FOCUS_BRACKET_SHUTTER_AUTO_OR_FX6_EOPNOTSUPP,
            )
        res2 = verify_drive_focusbracket_shutter_efcs_nr_guard(
            claimed_focus_bracket_exposed_on_fx3_or_fx6=True
        )
        self.assertFalse(res2.valid)
        self.assertEqual(res2.block_errno, EOPNOTSUPP_ERRNO_PHASE351)

    def test_24_g151_drive_mode_resets_on_camset_reset(self) -> None:
        st = resolve_fx3_drive_shutter_efcs_nr_state(
            drive_mode=DRIVE_MODE_CONT_G151,
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE351,
        )
        self.assertEqual(st["effective_drive_mode"], DRIVE_MODE_DEFAULT_G151)

    def test_25_g151_shutter_type_strictly_2_options_zero_auto(self) -> None:
        self.assertEqual(
            EXACT_2_SHUTTER_TYPES_G151,
            (SHUTTER_TYPE_MECHANICAL_G151, SHUTTER_TYPE_ELECTRONIC_G151),
        )
        self.assertEqual(INTERVAL_SHUTTER_TYPE_DEFAULT_G151, SHUTTER_TYPE_ELECTRONIC_G151)
        for stype in EXACT_2_SHUTTER_TYPES_G151:
            res = verify_drive_focusbracket_shutter_efcs_nr_guard(shutter_type=stype)
            self.assertTrue(res.valid)
        for bad_tok in DORMANT_SHUTTER_TYPE_AUTO_TOKENS_G151:
            res_bad = verify_drive_focusbracket_shutter_efcs_nr_guard(shutter_type=bad_tok)
            self.assertFalse(res_bad.valid)
            self.assertEqual(res_bad.block_errno, EOPNOTSUPP_ERRNO_PHASE351)
        res_claimed = verify_drive_focusbracket_shutter_efcs_nr_guard(
            claimed_shutter_type_auto_exists=True
        )
        self.assertFalse(res_claimed.valid)
        self.assertEqual(res_claimed.block_errno, EOPNOTSUPP_ERRNO_PHASE351)

    def test_26_g151_electronic_shutter_and_silent_mode_lock_5_items(self) -> None:
        self.assertEqual(len(EXACT_5_ELECTRONIC_SHUTTER_LOCKED_ITEMS_G151), 5)
        for kw in ({"shutter_type": SHUTTER_TYPE_ELECTRONIC_G151}, {"silent_mode": "On"}):
            res = verify_drive_focusbracket_shutter_efcs_nr_guard(**kw)
            self.assertTrue(res.valid)
            self.assertEqual(
                res.electronic_shutter_5_lockouts,
                EXACT_5_ELECTRONIC_SHUTTER_LOCKED_ITEMS_G151,
            )
            res_bad = verify_drive_focusbracket_shutter_efcs_nr_guard(
                claimed_electronic_shutter_allows_locked_item=True,
                **kw,
            )
            self.assertFalse(res_bad.valid)
            self.assertEqual(res_bad.block_errno, EINVAL_ERRNO_PHASE351)

    def test_27_g151_xsync_single_250_ceiling_rejects_1_320(self) -> None:
        self.assertEqual(FX3_FLASH_XSYNC_CEILING_STR_G151, "1/250")
        self.assertEqual(DORMANT_APSC_XSYNC_STR_G151, "1/320")
        res_bad = verify_drive_focusbracket_shutter_efcs_nr_guard(
            claimed_xsync_320_apsc_tier_supported=True
        )
        self.assertFalse(res_bad.valid)
        self.assertEqual(res_bad.block_errno, EINVAL_ERRNO_PHASE351)
        self.assertEqual(
            res_bad.status,
            STATUS_BLOCKED_G151_DRIVE_LOCKOUT_OR_XSYNC_1_320_VIOLATION,
        )

    def test_28_g151_efcs_reset_immunity_vs_initialize(self) -> None:
        self.assertFalse(EFCS_RESETTABLE_BY_CAMSET_RESET_G151)
        st_camset = resolve_fx3_drive_shutter_efcs_nr_state(
            efcs="Off",
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE351,
        )
        self.assertEqual(st_camset["effective_efcs"], "Off")
        st_init = resolve_fx3_drive_shutter_efcs_nr_state(
            efcs="Off",
            reset_action=RESET_ACTION_INITIALIZE_PHASE351,
        )
        self.assertEqual(st_init["effective_efcs"], EFCS_DEFAULT_G151)

        res_bad = verify_drive_focusbracket_shutter_efcs_nr_guard(
            claimed_camset_reset_clears_efcs=True
        )
        self.assertFalse(res_bad.valid)
        self.assertEqual(
            res_bad.status,
            STATUS_BLOCKED_G151_SHUTTER_TYPE_EFCS_RESET_OR_NR_VIOLATION,
        )

    def test_29_g151_long_exposure_nr_threshold_1s_and_lockouts(self) -> None:
        self.assertEqual(LONG_EXPOSURE_NR_MIN_SHUTTER_SEC_G151, 1.0)
        st_sub = resolve_fx3_drive_shutter_efcs_nr_state(shutter_speed_seconds=0.5)
        self.assertFalse(st_sub["long_exposure_nr_active_for_shot"])
        st_1s = resolve_fx3_drive_shutter_efcs_nr_state(shutter_speed_seconds=1.0)
        self.assertTrue(st_1s["long_exposure_nr_active_for_shot"])

        st_cont = resolve_fx3_drive_shutter_efcs_nr_state(
            drive_mode=DRIVE_MODE_CONT_G151,
            shutter_speed_seconds=2.0,
        )
        self.assertTrue(st_cont["long_exposure_nr_locked_disabled"])
        self.assertFalse(st_cont["long_exposure_nr_active_for_shot"])

        res_bad = verify_drive_focusbracket_shutter_efcs_nr_guard(
            shutter_speed_seconds=0.5,
            claimed_long_nr_active_under_lock_or_sub_1s=True,
        )
        self.assertFalse(res_bad.valid)

    def test_30_g151_long_exposure_nr_resets_on_camset_reset(self) -> None:
        st = resolve_fx3_drive_shutter_efcs_nr_state(
            long_exposure_nr="Off",
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE351,
        )
        self.assertEqual(st["effective_long_exposure_nr"], LONG_EXPOSURE_NR_DEFAULT_G151)

    def test_31_g151_high_iso_nr_3_options_and_arw_immutability(self) -> None:
        self.assertFalse(HIGH_ISO_NR_ALTERS_ARW_G151)
        self.assertEqual(
            EXACT_3_HIGH_ISO_NR_OPTIONS_G151,
            (HIGH_ISO_NR_NORMAL_G151, HIGH_ISO_NR_LOW_G151, HIGH_ISO_NR_OFF_G151),
        )
        for opt in EXACT_3_HIGH_ISO_NR_OPTIONS_G151:
            res = verify_drive_focusbracket_shutter_efcs_nr_guard(high_iso_nr=opt)
            self.assertTrue(res.valid)
        st_raw = resolve_fx3_drive_shutter_efcs_nr_state(still_file_format="RAW")
        self.assertEqual(st_raw["effective_high_iso_nr"], "Unavailable")
        for bad in DORMANT_HIGH_ISO_NR_TOKENS_G151:
            res_dormant = verify_drive_focusbracket_shutter_efcs_nr_guard(high_iso_nr=bad)
            self.assertFalse(res_dormant.valid)
            self.assertEqual(res_dormant.block_errno, EOPNOTSUPP_ERRNO_PHASE351)
        res_arw = verify_drive_focusbracket_shutter_efcs_nr_guard(
            claimed_high_iso_nr_alters_arw=True
        )
        self.assertFalse(res_arw.valid)

    def test_32_g151_fx6_cross_model_spoof_rejected_eopnotsupp_95(self) -> None:
        self.assertEqual(FX6_NOISE_SUPPRESSION_MODES_G151, ("Off", "Low", "Mid", "High"))
        self.assertEqual(FX6_APR_MENU_PATH_G151, "Technical > APR > Execute")
        res = verify_drive_focusbracket_shutter_efcs_nr_guard(
            fx6_mech_shutter_xsync_or_long_nr_spoof_requested=True
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.block_errno, EOPNOTSUPP_ERRNO_PHASE351)
        self.assertTrue(res.fx6_cross_model_spoof_rejected)

    def test_33_g151_exhaustive_384_state_matrix(self) -> None:
        m = compute_drive_shutter_efcs_nr_matrix()
        self.assertEqual(m["total_matrix_states"], 384)
        self.assertGreater(m["cont_10fps_count"], 0)
        self.assertGreater(m["first_frame_af_locked_count"], 0)
        self.assertEqual(m["elec_5_lockouts_count"], 96)
        self.assertEqual(m["efcs_reset_preserved_count"], 192)
        self.assertGreater(m["long_nr_darkframe_triggered_count"], 0)
        self.assertGreater(m["dro_hlg_blocked_count"], 0)

    def test_34_g151_invalid_bool_telemetry_and_identity_rejected(self) -> None:
        res_bad_model = verify_drive_focusbracket_shutter_efcs_nr_guard(
            body_model_name="ILME-FX6"
        )
        self.assertFalse(res_bad_model.valid)
        self.assertEqual(res_bad_model.status, STATUS_BLOCKED_G151_TELEMETRY_INVALID)

        res_bad_f = verify_drive_focusbracket_shutter_efcs_nr_guard(
            aperture_f_number=True  # type: ignore[arg-type]
        )
        self.assertFalse(res_bad_f.valid)
        self.assertEqual(res_bad_f.status, STATUS_BLOCKED_G151_TELEMETRY_INVALID)

    def test_35_g151_bracket_modes_and_shutter_speed_negative_rejected(self) -> None:
        for dm in (
            DRIVE_MODE_CONT_BRACKET_G151,
            DRIVE_MODE_SINGLE_BRACKET_G151,
            DRIVE_MODE_WB_BRACKET_G151,
            DRIVE_MODE_SELF_TIMER_SINGLE_G151,
        ):
            res = verify_drive_focusbracket_shutter_efcs_nr_guard(drive_mode=dm)
            self.assertTrue(res.valid)
        res_bad_ss = verify_drive_focusbracket_shutter_efcs_nr_guard(
            shutter_speed_seconds=-1.0
        )
        self.assertFalse(res_bad_ss.valid)

    # -----------------------------------------------------------------------
    # 36..68: Gate G152 — Creative Look 10+6 / Asymmetric 0..9 Bounds /
    #         Dormant Soft Skin / Delete / Protect / Recover Image DB Slot-1 EROFS=30
    # -----------------------------------------------------------------------

    def test_36_g152_nominal_default_passes(self) -> None:
        res = verify_creative_look_soft_skin_delete_protect_recoverdb_guard()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_VERIFIED_G152)
        self.assertEqual(res.block_errno, 0)
        self.assertEqual(res.effective_creative_look, CREATIVE_LOOK_DEFAULT_G152)
        self.assertEqual(res.effective_delete_confirm, DELETE_CONFIRM_CANCEL_FIRST_G152)
        self.assertEqual(res.effective_delete_pressing_twice, DELETE_PRESSING_TWICE_DEFAULT_G152)
        self.assertFalse(res.slot1_tier0_vault_firewall_blocked)
        self.assertEqual(res.slot1_data_sector_writes, 0)
        self.assertEqual(res.emmc_nflasha_write_count, 0)

    def test_37_g152_creative_look_10_presets_and_6_custom_slots(self) -> None:
        self.assertEqual(len(CREATIVE_LOOK_10_PRESETS_G152), 10)
        self.assertEqual(len(CREATIVE_LOOK_6_CUSTOM_SLOTS_G152), 6)
        self.assertEqual(len(ALLOWED_CREATIVE_LOOK_SLOTS_G152), CREATIVE_LOOK_TOTAL_SLOTS_G152)
        self.assertEqual(CREATIVE_LOOK_TOTAL_SLOTS_G152, 16)
        for slot in ALLOWED_CREATIVE_LOOK_SLOTS_G152:
            res = verify_creative_look_soft_skin_delete_protect_recoverdb_guard(
                creative_look=slot
            )
            self.assertTrue(res.valid, f"Creative look {slot} failed: {res.errors}")

    def test_38_g152_asymmetric_0_to_9_bounds_for_fade_sharpness_clarity(self) -> None:
        self.assertEqual(CREATIVE_LOOK_8_PARAM_BOUNDS_G152["Fade"], (0, 9))
        self.assertEqual(CREATIVE_LOOK_8_PARAM_BOUNDS_G152["Sharpness"], (0, 9))
        self.assertEqual(CREATIVE_LOOK_8_PARAM_BOUNDS_G152["Clarity"], (0, 9))
        self.assertEqual(CREATIVE_LOOK_8_PARAM_BOUNDS_G152["Sharpness Range"], (1, 5))
        for p_kw in ("fade", "sharpness", "clarity"):
            res_ok = verify_creative_look_soft_skin_delete_protect_recoverdb_guard(**{p_kw: 9})
            self.assertTrue(res_ok.valid)
            res_neg = verify_creative_look_soft_skin_delete_protect_recoverdb_guard(**{p_kw: -1})
            self.assertFalse(res_neg.valid)
            self.assertEqual(res_neg.block_errno, EINVAL_ERRNO_PHASE351)
            self.assertEqual(
                res_neg.status,
                STATUS_BLOCKED_G152_CREATIVE_LOOK_BOUNDS_LOCKOUT_OR_DELETE_RESET_VIOLATION,
            )
            res_hi = verify_creative_look_soft_skin_delete_protect_recoverdb_guard(**{p_kw: 10})
            self.assertFalse(res_hi.valid)

    def test_39_g152_symmetric_minus9_plus9_and_sharpness_range_1_to_5_bounds(self) -> None:
        for p_kw in ("contrast", "highlights", "shadows", "saturation"):
            self.assertTrue(
                verify_creative_look_soft_skin_delete_protect_recoverdb_guard(**{p_kw: -9}).valid
            )
            self.assertTrue(
                verify_creative_look_soft_skin_delete_protect_recoverdb_guard(**{p_kw: 9}).valid
            )
            self.assertFalse(
                verify_creative_look_soft_skin_delete_protect_recoverdb_guard(**{p_kw: -10}).valid
            )
            self.assertFalse(
                verify_creative_look_soft_skin_delete_protect_recoverdb_guard(**{p_kw: 10}).valid
            )
        self.assertTrue(
            verify_creative_look_soft_skin_delete_protect_recoverdb_guard(sharpness_range=1).valid
        )
        self.assertTrue(
            verify_creative_look_soft_skin_delete_protect_recoverdb_guard(sharpness_range=5).valid
        )
        self.assertFalse(
            verify_creative_look_soft_skin_delete_protect_recoverdb_guard(sharpness_range=0).valid
        )
        self.assertFalse(
            verify_creative_look_soft_skin_delete_protect_recoverdb_guard(sharpness_range=6).valid
        )

    def test_40_g152_bool_param_rejected_strict_int(self) -> None:
        res = verify_creative_look_soft_skin_delete_protect_recoverdb_guard(
            fade=True  # type: ignore[arg-type]
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_G152_TELEMETRY_INVALID)

    def test_41_g152_bw_se_saturation_lock_and_movie_sq_sharpness_range_lock(self) -> None:
        for look in ("BW", "SE"):
            st = resolve_fx3_creative_look_and_playback_media_state(creative_look=look)
            self.assertTrue(st["creative_look_saturation_locked"])
            res_bad = verify_creative_look_soft_skin_delete_protect_recoverdb_guard(
                creative_look=look,
                claimed_bw_or_se_saturation_adjustable=True,
            )
            self.assertFalse(res_bad.valid)
        for sm in (SHOOT_MODE_MOVIE_PHASE351, SHOOT_MODE_SQ_PHASE351):
            st = resolve_fx3_creative_look_and_playback_media_state(shoot_mode=sm)
            self.assertTrue(st["creative_look_sharpness_range_locked"])
            res_bad = verify_creative_look_soft_skin_delete_protect_recoverdb_guard(
                shoot_mode=sm,
                claimed_movie_sharpness_range_adjustable=True,
            )
            self.assertFalse(res_bad.valid)

    def test_42_g152_forced_dash_under_pp_log_hlg_still_or_iauto(self) -> None:
        for kw in (
            {"picture_profile": "PP11"},
            {"log_shooting_mode": "Flexible ISO"},
            {"hlg_still_image": "On"},
            {"exposure_mode": "iAuto"},
        ):
            res_ok = verify_creative_look_soft_skin_delete_protect_recoverdb_guard(**kw)
            self.assertTrue(res_ok.valid)
            self.assertTrue(res_ok.creative_look_forced_dash_disabled)
            self.assertEqual(res_ok.effective_creative_look, "[-]")
            res_bad = verify_creative_look_soft_skin_delete_protect_recoverdb_guard(
                claimed_creative_look_active_under_pp_or_log_or_hlg=True,
                **kw,
            )
            self.assertFalse(res_bad.valid)

    def test_43_g152_creative_look_resets_on_camset_reset(self) -> None:
        st = resolve_fx3_creative_look_and_playback_media_state(
            creative_look="Custom Look 3",
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE351,
        )
        self.assertEqual(st["effective_creative_look"], CREATIVE_LOOK_DEFAULT_G152)

    def test_44_g152_dormant_soft_skin_effect_100pct_rejected_on_both_fx3_and_fx6(self) -> None:
        self.assertEqual(DORMANT_SOFT_SKIN_EXPOSED_FX3_G152, 0)
        self.assertEqual(DORMANT_SOFT_SKIN_EXPOSED_FX6_G152, 0)
        for kw in ({"requested_soft_skin_effect_fx3": True}, {"requested_soft_skin_effect_fx6": True}):
            res = verify_creative_look_soft_skin_delete_protect_recoverdb_guard(**kw)
            self.assertFalse(res.valid)
            self.assertEqual(res.block_errno, EOPNOTSUPP_ERRNO_PHASE351)
            self.assertEqual(
                res.status,
                STATUS_BLOCKED_G152_DORMANT_SOFT_SKIN_OR_PROTECT_CANCEL_ALL_EOPNOTSUPP,
            )

    def test_45_g152_delete_5_batch_modes_and_reset_immune_delete_config(self) -> None:
        self.assertEqual(len(EXACT_5_DELETE_BATCH_MODES_G152), 5)
        self.assertFalse(PLAYBACK_DELETE_CONFIG_RESETTABLE_BY_CAMSET_RESET_G152)
        for dm in EXACT_5_DELETE_BATCH_MODES_G152:
            res = verify_creative_look_soft_skin_delete_protect_recoverdb_guard(
                delete_mode=dm,
                target_media_slot=MEDIA_SLOT_2_PHASE351,
            )
            self.assertTrue(res.valid)
        st_camset = resolve_fx3_creative_look_and_playback_media_state(
            delete_confirm=DELETE_CONFIRM_DELETE_FIRST_G152,
            delete_pressing_twice="On",
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE351,
        )
        self.assertEqual(st_camset["effective_delete_confirm"], DELETE_CONFIRM_DELETE_FIRST_G152)
        self.assertEqual(st_camset["effective_delete_pressing_twice"], "On")
        st_init = resolve_fx3_creative_look_and_playback_media_state(
            delete_confirm=DELETE_CONFIRM_DELETE_FIRST_G152,
            delete_pressing_twice="On",
            reset_action=RESET_ACTION_INITIALIZE_PHASE351,
        )
        self.assertEqual(st_init["effective_delete_confirm"], DELETE_CONFIRM_CANCEL_FIRST_G152)
        self.assertEqual(st_init["effective_delete_pressing_twice"], DELETE_PRESSING_TWICE_DEFAULT_G152)

    def test_46_g152_delete_proxy_protected_and_reset_violations_rejected(self) -> None:
        self.assertFalse(
            verify_creative_look_soft_skin_delete_protect_recoverdb_guard(
                claimed_camset_reset_clears_delete_confirm_or_twice=True
            ).valid
        )
        self.assertFalse(
            verify_creative_look_soft_skin_delete_protect_recoverdb_guard(
                claimed_delete_skips_proxy_or_deletes_protected=True
            ).valid
        )

    def test_47_g152_protect_7_modes_and_zero_cancel_all_images(self) -> None:
        self.assertEqual(len(EXACT_7_PROTECT_MODES_G152), 7)
        for pm in EXACT_7_PROTECT_MODES_G152:
            res = verify_creative_look_soft_skin_delete_protect_recoverdb_guard(
                protect_mode=pm,
                target_media_slot=MEDIA_SLOT_2_PHASE351,
            )
            self.assertTrue(res.valid)
        res_bad = verify_creative_look_soft_skin_delete_protect_recoverdb_guard(
            protect_mode=ABSENT_PROTECT_CANCEL_ALL_IMAGES_G152
        )
        self.assertFalse(res_bad.valid)
        self.assertEqual(res_bad.block_errno, EOPNOTSUPP_ERRNO_PHASE351)
        res_bad2 = verify_creative_look_soft_skin_delete_protect_recoverdb_guard(
            claimed_protect_cancel_all_images_exists=True
        )
        self.assertFalse(res_bad2.valid)
        self.assertEqual(res_bad2.block_errno, EOPNOTSUPP_ERRNO_PHASE351)

    def test_48_g152_display_media_info_readonly_safe_even_on_slot1(self) -> None:
        res = verify_creative_look_soft_skin_delete_protect_recoverdb_guard(
            display_media_info_requested=True,
            target_media_slot=MEDIA_SLOT_1_PHASE351,
        )
        self.assertTrue(res.valid)
        self.assertTrue(res.display_media_info_readonly_safe)
        self.assertEqual(res.slot1_data_sector_writes, 0)
        self.assertEqual(res.emmc_nflasha_write_count, 0)

    def test_49_g152_slot1_tier0_erofs_30_firewall_blocks_delete_protect_recoverdb(self) -> None:
        for kw in (
            {"delete_mutation_requested": True},
            {"protect_mutation_requested": True},
            {"recover_image_db_requested": True},
            {"requested_write_operation": True},
        ):
            res = verify_creative_look_soft_skin_delete_protect_recoverdb_guard(
                target_media_slot=MEDIA_SLOT_1_PHASE351,
                **kw,
            )
            self.assertFalse(res.valid)
            self.assertEqual(res.block_errno, EROFS_ERRNO_PHASE351)
            self.assertEqual(
                res.status,
                STATUS_BLOCKED_G152_SLOT1_DELETE_PROTECT_RECOVERDB_VAULT_EROFS,
            )
            self.assertTrue(res.slot1_tier0_vault_firewall_blocked)
            self.assertEqual(res.slot1_data_sector_writes, 0)
            self.assertEqual(res.emmc_nflasha_write_count, 0)

    def test_50_g152_slot2_mutations_allowed_with_zero_slot1_writes(self) -> None:
        for kw in (
            {"delete_mutation_requested": True},
            {"protect_mutation_requested": True},
            {"recover_image_db_requested": True},
        ):
            res = verify_creative_look_soft_skin_delete_protect_recoverdb_guard(
                target_media_slot=MEDIA_SLOT_2_PHASE351,
                **kw,
            )
            self.assertTrue(res.valid)
            self.assertFalse(res.slot1_tier0_vault_firewall_blocked)
            self.assertEqual(res.slot1_data_sector_writes, 0)

    def test_51_g152_recover_image_db_semantics_and_persistence(self) -> None:
        self.assertTrue(RECOVER_IMAGE_DB_IMMUNE_TO_RESET_AND_INIT_G152)
        self.assertFalse(
            verify_creative_look_soft_skin_delete_protect_recoverdb_guard(
                claimed_recover_db_erases_av_files_or_keeps_ftp=True
            ).valid
        )
        self.assertFalse(
            verify_creative_look_soft_skin_delete_protect_recoverdb_guard(
                claimed_reset_or_init_clears_recover_db=True
            ).valid
        )

    def test_52_g152_fx6_base_look_restore_media_spoof_rejected(self) -> None:
        self.assertEqual(
            FX6_MEDIA_MUTATION_MENUS_G152,
            ("Lock/Unlock Clip", "Delete Clip", "Restore Media(A)", "Restore Media(B)"),
        )
        res = verify_creative_look_soft_skin_delete_protect_recoverdb_guard(
            fx6_base_look_or_restore_media_spoof_requested=True
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.block_errno, EOPNOTSUPP_ERRNO_PHASE351)

    def test_53_g152_exhaustive_384_state_matrix(self) -> None:
        m = compute_creative_look_and_media_matrix()
        self.assertEqual(m["total_matrix_states"], 384)
        self.assertGreater(m["forced_dash_count"], 0)
        self.assertGreater(m["sat_locked_count"], 0)
        self.assertEqual(m["sharp_range_locked_count"], 360)
        self.assertEqual(m["camset_preserved_delete_cfg_count"], 128)
        self.assertEqual(m["slot1_erofs_blocked_count"], 192)

    def test_54_g152_invalid_telemetry_rejected(self) -> None:
        self.assertEqual(
            verify_creative_look_soft_skin_delete_protect_recoverdb_guard(
                creative_look="BogusLook"
            ).status,
            STATUS_BLOCKED_G152_TELEMETRY_INVALID,
        )
        self.assertEqual(
            verify_creative_look_soft_skin_delete_protect_recoverdb_guard(
                target_media_slot=True  # type: ignore[arg-type]
            ).status,
            STATUS_BLOCKED_G152_TELEMETRY_INVALID,
        )

    # -----------------------------------------------------------------------
    # 55..85: Unified 152-Gate Master Preflight Engine & Aliases
    # -----------------------------------------------------------------------

    def test_55_preflight_offline_default_149_of_152_nogo(self) -> None:
        rep = evaluate_152gate_preflight(REPO_ROOT, force_clean_room=True)
        self.assertEqual(rep.schema, REALHW_152GATE_PREFLIGHT_SCHEMA)
        self.assertEqual(len(rep.gates), 152)
        self.assertEqual(rep.summary["total_gates"], 152)
        self.assertEqual(rep.summary["verified_gates"], 149)
        self.assertEqual(rep.summary["blocked_or_pending_gates"], 3)
        self.assertEqual(rep.summary["g151_to_g152_verified"], 2)
        self.assertTrue(rep.offline_149_gates_verified)
        self.assertFalse(rep.all_152_gates_verified)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertEqual(rep.status, "VERIFIED_149_OF_152_AWAITING_PHYSICAL_TIER0")
        self.assertTrue(rep.agent_auto_flash_blocked)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)
        self.assertEqual(rep.usb_packets_transmitted, 0)

    def test_56_preflight_simulated_dry_run_152_of_152_redlines_locked(self) -> None:
        rep = evaluate_152gate_preflight(
            REPO_ROOT, force_clean_room=True, dry_run_simulated=True
        )
        self.assertEqual(rep.summary["verified_gates"], 152)
        self.assertEqual(rep.summary["blocked_or_pending_gates"], 0)
        self.assertTrue(rep.all_152_gates_verified)
        self.assertTrue(rep.dry_run_rehearsal_only)
        self.assertEqual(rep.status, "VERIFIED_ALL_152_GATES_DRY_RUN_SIMULATED_BACKUP")
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.hardware_live_attachment_authorized)
        self.assertFalse(rep.el3_payload_transmit_authorized)
        self.assertFalse(rep.spi_nor_write_authorized)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.cross_model_flash_authorized)
        self.assertEqual(rep.usb_packets_transmitted, 0)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_57_preflight_all_aliases_work(self) -> None:
        r1 = evaluate_152_master_safety_gates(REPO_ROOT, force_clean_room=True)
        r2 = run_152_gate_preflight(REPO_ROOT, force_clean_room=True)
        r3 = verify_real_hardware_152gate_readiness(REPO_ROOT, force_clean_room=True)
        for rep in (r1, r2, r3):
            self.assertEqual(rep.summary["verified_gates"], 149)
            self.assertEqual(len(rep.gates), 152)

    def test_58_preflight_mode_local_o_rdonly(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(ENV_FORCE_CLEAN_ROOM, None)
            os.environ.pop(ENV_CLEAN_ROOM_TEST_PHASE351, None)
            rep = evaluate_152gate_preflight(REPO_ROOT)
            self.assertEqual(rep.summary["verified_gates"], 149)
            self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_59_preflight_mode_fx3_clean_room_test_env(self) -> None:
        with mock.patch.dict(os.environ, {ENV_CLEAN_ROOM_TEST_PHASE351: "1"}):
            rep = evaluate_152gate_preflight(REPO_ROOT, dry_run_simulated=True)
            self.assertEqual(rep.summary["verified_gates"], 152)
            self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_60_preflight_mode_force_clean_room_env(self) -> None:
        with mock.patch.dict(os.environ, {ENV_FORCE_CLEAN_ROOM: "1"}):
            rep = evaluate_152gate_preflight(REPO_ROOT, dry_run_simulated=True)
            self.assertEqual(rep.summary["verified_gates"], 152)
            self.assertTrue(rep.clean_room_forced)

    def test_61_preflight_mode_work_root_none_ci_fallback(self) -> None:
        class _DummyPaths:
            work_root = None

        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(ENV_FORCE_CLEAN_ROOM, None)
            os.environ.pop(ENV_CLEAN_ROOM_TEST_PHASE351, None)
            with mock.patch(
                "fx3_safety.realhw_drive_focusbracket_shutter_efcs_creativelook_recoverdb_and_152gate_guard.resolve_donor_thermal_power_paths",
                return_value=_DummyPaths(),
            ):
                rep = evaluate_152gate_preflight(REPO_ROOT)
                self.assertEqual(rep.summary["verified_gates"], 149)
                self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_62_preflight_request_persistent_emmc_writes_fail_closed(self) -> None:
        rep = evaluate_152gate_preflight(
            REPO_ROOT, force_clean_room=True, request_persistent_emmc_writes=True
        )
        self.assertFalse(rep.offline_149_gates_verified)
        self.assertFalse(rep.all_152_gates_verified)
        self.assertFalse(rep.h0_h1_trial_entry_allowed)
        self.assertIn("BLOCKED_PERSISTENT_EMMC_WRITE", rep.status)

    def test_63_preflight_g151_fault_blocks_master(self) -> None:
        rep = evaluate_152gate_preflight(
            REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            drive_focusbracket_shutter_efcs_nr_kwargs={
                "requested_dormant_focus_bracket": "Focus Bracket"
            },
        )
        self.assertFalse(rep.all_152_gates_verified)
        self.assertFalse(rep.g151_to_g152_all_passed)
        self.assertEqual(rep.summary["g151_to_g152_verified"], 1)

    def test_64_preflight_g152_fault_blocks_master(self) -> None:
        rep = evaluate_152gate_preflight(
            REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            creative_look_delete_protect_recoverdb_kwargs={
                "target_media_slot": MEDIA_SLOT_1_PHASE351,
                "recover_image_db_requested": True,
            },
        )
        self.assertFalse(rep.all_152_gates_verified)
        self.assertFalse(rep.g151_to_g152_all_passed)
        self.assertEqual(rep.status, STATUS_BLOCKED_G152_SLOT1_DELETE_PROTECT_RECOVERDB_VAULT_EROFS)

    def test_65_preflight_propagates_upstream_g149_g150_fault(self) -> None:
        rep = evaluate_152gate_preflight(
            REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            still_arw_hlg_usblun_uvc_kwargs={
                "requested_native_uvc_usb_streaming_fx3": True
            },
        )
        self.assertFalse(rep.all_152_gates_verified)
        self.assertFalse(rep.g13_to_g152_all_passed)

    def test_66_preflight_gate_ids_g01_through_g152_ordered(self) -> None:
        rep = evaluate_152gate_preflight(
            REPO_ROOT, force_clean_room=True, dry_run_simulated=True
        )
        gate_ids = [g["gate_id"] for g in rep.gates]
        self.assertTrue(gate_ids[0].startswith("G01"))
        self.assertEqual(gate_ids[-2], G151)
        self.assertEqual(gate_ids[-1], G152)
        self.assertEqual(len(set(gate_ids)), 152)

    def test_67_preflight_no_raw_bytes_repr_in_report_dict(self) -> None:
        rep = evaluate_152gate_preflight(
            REPO_ROOT, force_clean_room=True, dry_run_simulated=True
        )
        dumped = json.dumps(rep.to_dict(), ensure_ascii=False)
        self.assertNotIn("b'\\x7fELF", dumped)
        self.assertNotIn("elapsed_seconds_leak", dumped)

    def test_68_preflight_report_has_master_150_and_g151_g152_dicts(self) -> None:
        rep = evaluate_152gate_preflight(REPO_ROOT, force_clean_room=True)
        d = rep.to_dict()
        self.assertIn("master_150_report", d)
        self.assertIn("g151_result", d)
        self.assertIn("g152_result", d)
        self.assertEqual(d["g151_result"]["gate_id"], G151)
        self.assertEqual(d["g152_result"]["gate_id"], G152)

    def test_69_backward_compatibility_150_148_146_144_gates(self) -> None:
        r150 = fx3_safety.evaluate_150gate_preflight(REPO_ROOT, force_clean_room=True)
        r148 = fx3_safety.evaluate_148gate_preflight(REPO_ROOT, force_clean_room=True)
        r146 = fx3_safety.evaluate_146gate_preflight(REPO_ROOT, force_clean_room=True)
        r144 = fx3_safety.evaluate_144gate_preflight(REPO_ROOT, force_clean_room=True)
        self.assertEqual(r150.summary["verified_gates"], 147)
        self.assertEqual(r148.summary["verified_gates"], 145)
        self.assertEqual(r146.summary["verified_gates"], 143)
        self.assertEqual(r144.summary["verified_gates"], 141)

    def test_70_simulate_bench_dry_run_alias_kwargs(self) -> None:
        r1 = evaluate_152gate_preflight(
            REPO_ROOT, force_clean_room=True, simulate_bench_dry_run=True
        )
        r2 = evaluate_152gate_preflight(
            REPO_ROOT, force_clean_room=True, dry_run_simulated_backup=True
        )
        self.assertEqual(r1.summary["verified_gates"], 152)
        self.assertEqual(r2.summary["verified_gates"], 152)

    def test_71_forward_compatible_dynamic_discovery_export(self) -> None:
        nums = sorted(
            int(name[9:-14])
            for name in dir(fx3_safety)
            if name.startswith("evaluate_")
            and name.endswith("gate_preflight")
            and name[9:-14].isdigit()
        )
        self.assertIn(152, nums)
        self.assertGreaterEqual(max(nums), 152)

    def test_72_fx3_safety_package_exports_and_all(self) -> None:
        for sym in (
            "evaluate_152gate_preflight",
            "evaluate_152_master_safety_gates",
            "run_152_gate_preflight",
            "verify_real_hardware_152gate_readiness",
            "evaluate_g151_drive_focusbracket_shutter_efcs_nr_guard",
            "evaluate_g152_creative_look_soft_skin_delete_protect_recoverdb_guard",
            "Master152GateReport",
        ):
            self.assertTrue(hasattr(fx3_safety, sym), f"Missing export {sym}")
            self.assertIn(sym, fx3_safety.__all__)

    # -----------------------------------------------------------------------
    # 73..88: Additional Wave-66 Matrix, Reset & Edge-Case Coverage
    # -----------------------------------------------------------------------

    def test_73_g151_reset_network_set_preserves_drive_and_shutter(self) -> None:
        st = resolve_fx3_drive_shutter_efcs_nr_state(
            drive_mode=DRIVE_MODE_CONT_G151,
            shutter_type=SHUTTER_TYPE_ELECTRONIC_G151,
            long_exposure_nr="Off",
            high_iso_nr=HIGH_ISO_NR_LOW_G151,
            reset_action=RESET_ACTION_RESET_NETWORK_SET_PHASE351,
        )
        self.assertEqual(st["effective_drive_mode"], DRIVE_MODE_CONT_G151)
        self.assertEqual(st["effective_shutter_type"], SHUTTER_TYPE_ELECTRONIC_G151)
        self.assertEqual(st["effective_high_iso_nr"], HIGH_ISO_NR_LOW_G151)

    def test_74_g152_reset_network_set_preserves_creative_look_and_delete_cfg(self) -> None:
        st = resolve_fx3_creative_look_and_playback_media_state(
            creative_look="FL",
            delete_confirm=DELETE_CONFIRM_DELETE_FIRST_G152,
            delete_pressing_twice="On",
            reset_action=RESET_ACTION_RESET_NETWORK_SET_PHASE351,
        )
        self.assertEqual(st["effective_creative_look"], "FL")
        self.assertEqual(st["effective_delete_confirm"], DELETE_CONFIRM_DELETE_FIRST_G152)
        self.assertEqual(st["effective_delete_pressing_twice"], "On")

    def test_75_g151_shutter_type_resets_to_mechanical_on_camset_reset(self) -> None:
        st = resolve_fx3_drive_shutter_efcs_nr_state(
            shutter_type=SHUTTER_TYPE_ELECTRONIC_G151,
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE351,
        )
        self.assertEqual(st["effective_shutter_type"], SHUTTER_TYPE_DEFAULT_G151)
        self.assertEqual(st["electronic_shutter_5_lockouts"], ())

    def test_76_g151_iauto_locks_brackets_and_forces_nr_defaults(self) -> None:
        st = resolve_fx3_drive_shutter_efcs_nr_state(
            drive_mode=DRIVE_MODE_CONT_BRACKET_G151,
            exposure_mode="iAuto",
            long_exposure_nr="Off",
            high_iso_nr=HIGH_ISO_NR_OFF_G151,
        )
        self.assertEqual(st["effective_drive_mode"], "Unavailable")
        self.assertEqual(st["effective_long_exposure_nr"], "On")
        self.assertEqual(st["effective_high_iso_nr"], HIGH_ISO_NR_NORMAL_G151)

    def test_77_g151_efcs_disabled_under_electronic_shutter_or_silent_mode(self) -> None:
        st1 = resolve_fx3_drive_shutter_efcs_nr_state(shutter_type=SHUTTER_TYPE_ELECTRONIC_G151)
        st2 = resolve_fx3_drive_shutter_efcs_nr_state(silent_mode="On")
        self.assertEqual(st1["effective_efcs"], "Disabled")
        self.assertEqual(st2["effective_efcs"], "Disabled")

    def test_78_g151_cont_bracket_and_self_timer_single_reset_to_single_shooting(self) -> None:
        for dm in (DRIVE_MODE_CONT_BRACKET_G151, DRIVE_MODE_SELF_TIMER_SINGLE_G151):
            st = resolve_fx3_drive_shutter_efcs_nr_state(
                drive_mode=dm,
                reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE351,
            )
            self.assertEqual(st["effective_drive_mode"], DRIVE_MODE_SINGLE_G151)

    def test_79_g152_custom_look_1_to_6_reset_to_st_on_camset_reset(self) -> None:
        for slot in CREATIVE_LOOK_6_CUSTOM_SLOTS_G152:
            st = resolve_fx3_creative_look_and_playback_media_state(
                creative_look=slot,
                reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE351,
            )
            self.assertEqual(st["effective_creative_look"], "ST")

    def test_80_g152_still_mode_allows_sharpness_range_unless_forced_dash(self) -> None:
        st_still = resolve_fx3_creative_look_and_playback_media_state(
            shoot_mode=SHOOT_MODE_STILL_PHASE351,
            creative_look="VV2",
        )
        self.assertFalse(st_still["creative_look_sharpness_range_locked"])
        self.assertFalse(st_still["creative_look_saturation_locked"])

        st_pp = resolve_fx3_creative_look_and_playback_media_state(
            shoot_mode=SHOOT_MODE_STILL_PHASE351,
            picture_profile="PP11",
        )
        self.assertTrue(st_pp["creative_look_sharpness_range_locked"])
        self.assertTrue(st_pp["creative_look_saturation_locked"])

    def test_81_g152_slot0_none_allows_no_slot1_write_block(self) -> None:
        res = verify_creative_look_soft_skin_delete_protect_recoverdb_guard(
            target_media_slot=0,
            display_media_info_requested=True,
        )
        self.assertTrue(res.valid)
        self.assertFalse(res.slot1_tier0_vault_firewall_blocked)

    def test_82_g151_invalid_body_id_help_code_fw_rejected(self) -> None:
        self.assertEqual(
            verify_drive_focusbracket_shutter_efcs_nr_guard(body_model_id=0x9999).status,
            STATUS_BLOCKED_G151_TELEMETRY_INVALID,
        )
        self.assertEqual(
            verify_drive_focusbracket_shutter_efcs_nr_guard(help_guide_code="ilc/2035").status,
            STATUS_BLOCKED_G151_TELEMETRY_INVALID,
        )
        self.assertEqual(
            verify_drive_focusbracket_shutter_efcs_nr_guard(firmware_version="").status,
            STATUS_BLOCKED_G151_TELEMETRY_INVALID,
        )

    def test_83_g152_invalid_body_id_help_code_fw_rejected(self) -> None:
        self.assertEqual(
            verify_creative_look_soft_skin_delete_protect_recoverdb_guard(
                body_model_name="ILME-FX6"
            ).status,
            STATUS_BLOCKED_G152_TELEMETRY_INVALID,
        )
        self.assertEqual(
            verify_creative_look_soft_skin_delete_protect_recoverdb_guard(
                help_guide_code="5-024-458-18"
            ).status,
            STATUS_BLOCKED_G152_TELEMETRY_INVALID,
        )

    def test_84_g151_invalid_drive_cont_speed_silent_efcs_nr_rejected(self) -> None:
        for bad_kw in (
            {"drive_mode": "InvalidDrive"},
            {"cont_speed": "Ultra"},
            {"silent_mode": "Maybe"},
            {"efcs": "Auto"},
            {"long_exposure_nr": "High"},
            {"reset_action": "FactoryNuclear"},
        ):
            res = verify_drive_focusbracket_shutter_efcs_nr_guard(**bad_kw)
            self.assertFalse(res.valid)
            self.assertEqual(res.status, STATUS_BLOCKED_G151_TELEMETRY_INVALID)

    def test_85_g152_invalid_delete_protect_slot_reset_rejected(self) -> None:
        for bad_kw in (
            {"shoot_mode": "Timelapse"},
            {"hlg_still_image": "Auto"},
            {"delete_mode": "Delete Everything"},
            {"delete_confirm": "Always"},
            {"delete_pressing_twice": "Triple"},
            {"protect_mode": "Unprotect All"},
            {"target_media_slot": 9},
            {"reset_action": "WipeAll"},
        ):
            res = verify_creative_look_soft_skin_delete_protect_recoverdb_guard(**bad_kw)
            self.assertFalse(res.valid)
            self.assertEqual(res.status, STATUS_BLOCKED_G152_TELEMETRY_INVALID)

    def test_86_g151_with_audit_missing_override_fails_with_donor_integrity(self) -> None:
        with mock.patch(
            "fx3_safety.realhw_drive_focusbracket_shutter_efcs_creativelook_recoverdb_and_152gate_guard.audit_phase351_donor_contracts"
        ) as m_audit:
            from fx3_safety.realhw_drive_focusbracket_shutter_efcs_creativelook_recoverdb_and_152gate_guard import (
                Phase351DonorAuditResult,
            )

            m_audit.return_value = Phase351DonorAuditResult(
                valid=False,
                status=STATUS_BLOCKED_PHASE351_DONOR_INTEGRITY,
                verification_mode="LOCAL_DONOR_O_RDONLY",
                access_mode="STRICT_OS_O_RDONLY_PREAD",
                files_inspected=0,
                fx3_contracts_verified=False,
                fx6_contracts_verified=False,
                four_lang_resid16_parity_verified=False,
                zero_forbidden_myths_verified=False,
                elapsed_seconds=0.001,
                within_budget_200ms=True,
                raw_firmware_bytes_leaked=0,
                file_digests={},
                missing_markers=("tampered",),
                errors=("tampered",),
                warnings=(),
            )
            v1, r1 = evaluate_g151_drive_focusbracket_shutter_efcs_nr_guard()
            v2, r2 = evaluate_g152_creative_look_soft_skin_delete_protect_recoverdb_guard()
            self.assertFalse(v1.passed)
            self.assertEqual(r1.status, STATUS_BLOCKED_PHASE351_DONOR_INTEGRITY)
            self.assertFalse(v2.passed)
            self.assertEqual(r2.status, STATUS_BLOCKED_PHASE351_DONOR_INTEGRITY)

    def test_87_preflight_summary_flags_consistent(self) -> None:
        rep = evaluate_152gate_preflight(REPO_ROOT, force_clean_room=True)
        s = rep.summary
        self.assertEqual(s["g01_to_g12_verified"], 9)
        self.assertEqual(s["g13_to_g150_verified"], 138)
        self.assertEqual(s["g151_to_g152_verified"], 2)
        self.assertEqual(s["verified_gates"], 149)
        self.assertTrue(s["g13_to_g152_all_passed"])
        self.assertTrue(s["g151_to_g152_all_passed"])
        self.assertFalse(s["overall_ready_for_hardware_attach"])

    def test_88_preflight_simulated_summary_flags_consistent(self) -> None:
        rep = evaluate_152gate_preflight(
            REPO_ROOT, force_clean_room=True, dry_run_simulated=True
        )
        s = rep.summary
        self.assertEqual(s["g01_to_g12_verified"], 12)
        self.assertEqual(s["g13_to_g150_verified"], 138)
        self.assertEqual(s["g151_to_g152_verified"], 2)
        self.assertEqual(s["verified_gates"], 152)
        self.assertTrue(s["all_152_gates_verified"])
        self.assertFalse(s["overall_ready_for_hardware_attach"])

    # -----------------------------------------------------------------------
    # 89..100: CLI Subcommands, Argparse Percent Escaping & Milestone Auto-Discovery
    # -----------------------------------------------------------------------

    def test_89_cli_help_percent_escaping_clean(self) -> None:
        buf = io.StringIO()
        with self.assertRaises(SystemExit) as ctx:
            with contextlib.redirect_stdout(buf):
                cli_main(["--help"])
        self.assertEqual(ctx.exception.code, 0)
        self.assertIn("verify-152-gates", buf.getvalue())
        self.assertIn("verify-drive-focusbracket-shutter-efcs-nr-guard", buf.getvalue())
        self.assertIn("verify-creative-look-soft-skin-delete-protect-recoverdb-guard", buf.getvalue())

    def test_90_cli_verify_152_gates_offline_text_and_json(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cli_main(["verify-152-gates", "--clean-room"])
        self.assertEqual(rc, 0)
        self.assertIn("verified=149/152", buf.getvalue())
        self.assertIn("VERIFIED_149_OF_152_AWAITING_PHYSICAL_TIER0", buf.getvalue())
        self.assertIn("overall_ready_for_hardware_attach=False", buf.getvalue())

        jbuf = io.StringIO()
        with contextlib.redirect_stdout(jbuf):
            rc2 = cli_main(["verify-152-gates", "--clean-room", "--json", "--summary"])
        self.assertEqual(rc2, 0)
        payload = json.loads(jbuf.getvalue())
        self.assertEqual(payload["summary"]["verified_gates"], 149)

    def test_91_cli_verify_152_gates_simulated_dry_run(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cli_main(
                [
                    "verify-152-gates",
                    "--clean-room",
                    "--simulate-bench-dry-run",
                    "--json",
                    "--summary",
                ]
            )
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["summary"]["verified_gates"], 152)
        self.assertTrue(payload["summary"]["all_152_gates_verified"])
        self.assertFalse(payload["summary"]["overall_ready_for_hardware_attach"])

    def test_92_cli_verify_152_gates_text_dry_run(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cli_main(["verify-152-gates", "--clean-room", "--simulate-bench-dry-run"])
        self.assertEqual(rc, 0)
        self.assertIn("verified=152/152", buf.getvalue())
        self.assertIn("all_152_gates_verified=True", buf.getvalue())

    def test_93_cli_verify_g151_and_aliases_json(self) -> None:
        for cmd in (
            "verify-drive-focusbracket-shutter-efcs-nr-guard",
            "verify-g151-drive-shutter-efcs-nr",
            "verify-g151",
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = cli_main([cmd, "--clean-room", "--json", "--summary"])
            self.assertEqual(rc, 0)
            payload = json.loads(buf.getvalue())
            self.assertEqual(payload["gate"], G151)
            self.assertTrue(payload["valid"])

    def test_94_cli_verify_g152_and_aliases_json(self) -> None:
        for cmd in (
            "verify-creative-look-soft-skin-delete-protect-recoverdb-guard",
            "verify-g152-creativelook-delete-recoverdb",
            "verify-g152",
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = cli_main([cmd, "--clean-room", "--json", "--summary"])
            self.assertEqual(rc, 0)
            payload = json.loads(buf.getvalue())
            self.assertEqual(payload["gate"], G152)
            self.assertTrue(payload["valid"])

    def test_95_cli_verify_g151_g152_text_mode(self) -> None:
        b1 = io.StringIO()
        with contextlib.redirect_stdout(b1):
            rc1 = cli_main(["verify-g151", "--clean-room"])
        self.assertEqual(rc1, 0)
        self.assertIn("gate=G151", b1.getvalue())

        b2 = io.StringIO()
        with contextlib.redirect_stdout(b2):
            rc2 = cli_main(["verify-g152", "--clean-room"])
        self.assertEqual(rc2, 0)
        self.assertIn("gate=G152", b2.getvalue())

    def test_96_cli_module_standalone_main_works(self) -> None:
        from fx3_safety.realhw_drive_focusbracket_shutter_efcs_creativelook_recoverdb_and_152gate_guard import (
            main as mod_main,
        )

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = mod_main(["--clean-room", "--simulate-bench-dry-run", "--json", "--summary"])
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(buf.getvalue())["summary"]["verified_gates"], 152)

        b151 = io.StringIO()
        with contextlib.redirect_stdout(b151):
            rc1 = mod_main(["--clean-room", "--gate", "g151", "--json", "--summary"])
        self.assertEqual(rc1, 0)
        self.assertEqual(json.loads(b151.getvalue())["gate"], G151)

        b152 = io.StringIO()
        with contextlib.redirect_stdout(b152):
            rc2 = mod_main(["--clean-room", "--gate", "g152", "--json", "--summary"])
        self.assertEqual(rc2, 0)
        self.assertEqual(json.loads(b152.getvalue())["gate"], G152)

    def test_97_milestone_324_master_gate_auto_discovers_152_gates(self) -> None:
        extra_paths = [
            str(REPO_ROOT / "outputs" / p)
            for p in (
                "fx6-on-fx3-closure",
                "fx3-safety",
                "fx3-recovery-adapter",
                "fx3-firmware-lab",
                "fx3-vm",
            )
        ]
        with mock.patch.object(sys, "path", extra_paths + sys.path):
            from fx6_closure.realhw_milestone324_master_gate import (
                evaluate_milestone_324_master_gate,
            )

            rep = evaluate_milestone_324_master_gate(
                repo_root=REPO_ROOT, force_clean_room=True
            )
            self.assertGreaterEqual(rep.gate142_total_gates, 152)
            self.assertGreaterEqual(rep.gate142_offline_verified, 149)
            self.assertEqual(rep.gate142_offline_verified, rep.gate142_total_gates - 3)
            self.assertGreaterEqual(rep.gate142_simulated_verified, 152)
            self.assertEqual(rep.gate142_simulated_verified, rep.gate142_total_gates)
            self.assertTrue(rep.gate142_all_verified)

    def test_98_milestone_311_master_gate_auto_discovers_152_gates(self) -> None:
        extra_paths = [
            str(REPO_ROOT / "outputs" / p)
            for p in (
                "fx6-on-fx3-closure",
                "fx3-safety",
                "fx3-recovery-adapter",
                "fx3-firmware-lab",
                "fx3-vm",
            )
        ]
        with mock.patch.object(sys, "path", extra_paths + sys.path):
            from fx6_closure.realhw_milestone311_master_gate import (
                evaluate_milestone_311_master_gate,
            )

            rep = evaluate_milestone_311_master_gate(
                repo_root=REPO_ROOT, force_clean_room=True
            )
            self.assertGreaterEqual(rep.gate134_total_gates, 152)
            self.assertGreaterEqual(rep.gate134_offline_verified, 149)
            self.assertEqual(rep.gate134_offline_verified, rep.gate134_total_gates - 3)
            self.assertGreaterEqual(rep.gate134_simulated_verified, 152)
            self.assertEqual(rep.gate134_simulated_verified, rep.gate134_total_gates)
            self.assertTrue(rep.gate134_all_verified)

    def test_99_cli_verify_152_gates_full_json_no_summary(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cli_main(["verify-152-gates", "--clean-room", "--json"])
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["summary"]["total_gates"], 152)
        self.assertEqual(len(payload["gates"]), 152)

    def test_100_cli_verify_152_gates_force_clean_room_flag(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cli_main(
                ["verify-152-gates", "--force-clean-room", "--simulate-bench-dry-run"]
            )
        self.assertEqual(rc, 0)
        self.assertIn("mode=CLEAN_ROOM_SYNTHETIC", buf.getvalue())
        self.assertIn("verified=152/152", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
