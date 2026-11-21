"""Phase 370 (Pillar 68 & 68/68 Milestone) unit tests:
Wave-66 `ILME-FX3 Ver. 7.02` vs `ILME-FX6 Ver. 6.01` empirical telemetry across 4 sub-pillars:
- Pillar 68A (Still `[Drive Mode]` 10fps `Hi+` non-live-view / `Hi` 8 / `Mid` 6 / `Lo` 3, `> F11`
  first-frame AF lock, rate drop on Uncompressed RAW or Flash, 6-combo `Self-timer(Cont)` vs dormant
  `10SEC_10IMAGES` rejection, `Cont./Single Bracket`, `WB bracket`, `DRO Bracket` HLG lockout, Still
  `[Interval Shoot Func.]` with `Electronic Shutter` default, and Dormant `[Focus Bracket]` rejection on
  both FX3 & FX6 `EOPNOTSUPP=95`; strictly 2-option `[Shutter Type]` `Mechanical Shutter` def /
  `Electronic Shutter` with NO `Auto` option, 5-feature lockout under Electronic/Silent, strictly `1/250 s`
  X-Sync ceiling, Reset-resistant `[e-Front Curtain Shut.]` (`BKID_APP_setting_front_curtaion_shutter`),
  `>= 1 s` `[Long Exposure NR]`, and 3-level `[High ISO NR]` never altering `.ARW` vs FX6 `Noise Suppression`
  & `APR`).
- Pillar 68B (`[Creative Look]` 10 presets `ST..SE` + `Custom Look 1..6` + 8 asymmetric parameters
  `-9..+9` / `0..9` `Fade/Sharpness/Clarity` / `1..5` `Sharpness Range/fineness`, `BW/SE` Saturation lock,
  Movie/S&Q `Sharpness Range` lock, `PP != Off` / `Log != Off` / `HLG Still = On` / `iAuto` forced `[-]`
  override, and Dormant `[Soft Skin Effect]` rejection on both FX3 & FX6 vs FX6 `Base Look`; Playback
  `[Delete]` scopes + coupled Proxy + Protected skip, Reset-resistant `[Delete confirm.]` &
  `[Delete pressing twice]`, `[Protect]` coupled Proxy & `[Copy]` non-preserve, Reset/Init-resistant
  `[Recover Image DB]` (`AVF_INFO` + FTP wipe + battery gate) vs `[Display Media Info.]` `40,000` still cap,
  fail-closed Tier-0 `Slot 1 EROFS=30` vault firewall & FX6 `Restore Media(A)` guard).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any
import unittest
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[3]
ADAPTER_ROOT = Path(__file__).resolve().parents[1]
if str(ADAPTER_ROOT) not in sys.path:
    sys.path.insert(0, str(ADAPTER_ROOT))

import fx3_recovery as fr  # noqa: E402
from fx3_recovery import (  # noqa: E402
    ALLOW_BOOT_PARTITION_TARGETING,
    ALLOW_DESTRUCTIVE_FASTBOOT,
    ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS,
    ALLOW_PERSISTENT_JIRITSU_WRITES,
    BODYDATA_PLACEMENT_OR_FLASH_AUTHORIZED,
    CNFLASHA_USERSPACE_WRITE_BLOCKED,
    CROSS_MODEL_FLASH_AUTHORIZED,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    ISP_WRITE_AUTHORIZED,
    LIVE_USB_IOKIT_TRANSMIT_ENABLED,
    MASTER_68_PILLAR_COUNT,
    MASTER_68_PILLAR_IDS,
    MASTER_68_PILLAR_SPECS,
    OTP_FUSE_TOUCHES,
    OTP_FUSE_WRITES,
    OVERALL_READY_FOR_HARDWARE_ATTACH,
    P370_AIRPLANE_MODE_FORCED_ON,
    P370_BKID_EFCS_SONY_TYPO,
    P370_BLOCKED_CREATIVE_LOOK_8PARAM_OVERRIDE_OR_SOFTSKIN,
    P370_BLOCKED_DELETE_PROTECT_OR_RECOVERDB_DRIFT,
    P370_BLOCKED_DRIVE_MODE_OR_DORMANT_FOCUS_BRACKET,
    P370_BLOCKED_INVALID_PILLAR68A_SPEC,
    P370_BLOCKED_INVALID_PILLAR68B_SPEC,
    P370_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
    P370_BLOCKED_SHUTTER_2OPT_XSYNC_EFCS_OR_NR_DRIFT,
    P370_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL,
    P370_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
    P370_BODYDATA_PLACEMENT_OR_FLASH_AUTHORIZED,
    P370_CONCURRENT_CEILING_SECONDS,
    P370_CROSS_MODEL_FLASH_AUTHORIZED,
    P370_DONOR_FX3_APPFW_702_RELPATH,
    P370_DONOR_FX3_BACKUP_BIN_RELPATH,
    P370_DONOR_FX3_UXC_EN_RELPATH,
    P370_DONOR_FX6_APPFW_601_RELPATH,
    P370_DONOR_FX6_UXC_EN_2_RELPATH,
    P370_DONOR_FX6_UXC_EN_RELPATH,
    P370_DONOR_INSPECT_BUDGET_SECONDS,
    P370_EBUSY_ERRNO,
    P370_EINVAL_ERRNO,
    P370_EMMC_WRITES_AUTHORIZED,
    P370_ENV_CLEAN_ROOM_TEST,
    P370_EOPNOTSUPP_ERRNO,
    P370_FAST_CLI_BUDGET_SECONDS,
    P370_FX3_ACTIVE_DRIVE_MODES,
    P370_FX3_ACTIVE_SHUTTER_TYPES,
    P370_FX3_CONT_SHOOT_SPEEDS_FPS,
    P370_FX3_CREATIVE_LOOK_ALL_SLOTS,
    P370_FX3_CREATIVE_LOOK_CUSTOM_SLOTS,
    P370_FX3_CREATIVE_LOOK_DEFAULT,
    P370_FX3_CREATIVE_LOOK_PARAM_BOUNDS,
    P370_FX3_CREATIVE_LOOK_PRESETS,
    P370_FX3_CREATIVE_LOOK_RESETTABLE,
    P370_FX3_DELETE_CONFIRM_DEFAULT,
    P370_FX3_DELETE_CONFIRM_RESETTABLE,
    P370_FX3_DELETE_TWICE_RESETTABLE,
    P370_FX3_DISPLAY_MEDIA_INFO_STILL_CAP,
    P370_FX3_DRIVE_MODE_DEFAULT,
    P370_FX3_DRIVE_MODE_RESETTABLE,
    P370_FX3_EFCS_DEFAULT,
    P370_FX3_EFCS_RESETTABLE,
    P370_FX3_ELECTRONIC_OR_SILENT_LOCKED_FEATURES,
    P370_FX3_EXP_BRACKET_STEPS_COUNTS,
    P370_FX3_FLASH_XSYNC_CEILING_RECIPROCAL,
    P370_FX3_FW_VERSION,
    P370_FX3_HAS_DORMANT_FOCUS_BRACKET_EXPOSED,
    P370_FX3_HAS_DORMANT_SOFT_SKIN_EXPOSED,
    P370_FX3_HAS_SHUTTER_TYPE_AUTO_EXPOSED,
    P370_FX3_HELPGUIDE_ID,
    P370_FX3_HIGH_ISO_NR_ACTIVE_LEVELS,
    P370_FX3_HIGH_ISO_NR_DEFAULT,
    P370_FX3_HIGH_ISO_NR_DORMANT_LEVELS,
    P370_FX3_INTERVAL_SHUTTER_DEFAULT,
    P370_FX3_LONG_EXP_NR_DEFAULT,
    P370_FX3_MODEL_ID,
    P370_FX3_MODEL_NAME,
    P370_FX3_SELF_TIMER_CONT_ACTIVE_OPTIONS,
    P370_FX3_SELF_TIMER_CONT_DORMANT_OPTIONS,
    P370_FX3_SELF_TIMER_SINGLE_OPTIONS,
    P370_FX3_SHUTTER_TYPE_DEFAULT,
    P370_FX6_DONOR_FW_VERSION,
    P370_FX6_DONOR_MODEL_NAME,
    P370_FX6_HAS_CREATIVE_LOOK,
    P370_FX6_HAS_EFCS,
    P370_FX6_HAS_FOCUS_BRACKET,
    P370_FX6_HAS_LONG_EXP_NR,
    P370_FX6_HAS_MECHANICAL_SHUTTER,
    P370_FX6_HAS_SOFT_SKIN_EFFECT,
    P370_FX6_HAS_STILL_DRIVE_MODE,
    P370_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    P370_OVERALL_READY_FOR_HARDWARE_ATTACH,
    P370_PILLAR_68A_SCENARIO_IDS,
    P370_PILLAR_68B_SCENARIO_IDS,
    P370_PINNED_FX3_BACKUP_BIN_SHA256,
    P370_SLOT1_VAULT_EROFS_EBUSY_ENFORCED,
    P370_SLOT1_VAULT_EROFS_EOPNOTSUPP_ENFORCED,
    P370_STATUS_FAIL_68OF68_AGGREGATOR,
    P370_STATUS_VERIFIED_68OF68_AGGREGATOR,
    P370_STATUS_VERIFIED_PILLAR68_SUITE,
    P370_STATUS_VERIFIED_PILLAR_68A,
    P370_STATUS_VERIFIED_PILLAR_68B,
    P370_WRITE_MUTATING_VAULT_ACTIONS,
    PASSIVE_TX_BYTES_EMITTED,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHASE370_MASTER_SCHEMA,
    PHASE370_PHASE_NUMBER,
    PHASE370_SCHEMA,
    PHASE370_VERSION,
    PHYSICAL_DEVICE_WRITES,
    PHYSICAL_USB_PACKETS_EMITTED,
    RAW_FIRMWARE_BYTES_LEAKED,
    READ_ONLY_DONOR_ACCESS,
    RPMB_COUNTER_INCREMENTS,
    SPI_NOR_WRITE_AUTHORIZED,
    build_default_safe_creativelook_softskin_recoverdb_vault_spec,
    build_default_safe_drive_focusbracket_shutter_efcs_nr_vault_spec,
    compute_expected_creativelook_softskin_recoverdb_state,
    compute_expected_drive_focusbracket_shutter_efcs_nr_state,
    evaluate_68pillar_recovery_master,
    evaluate_creativelook_softskin_recoverdb_vault,
    evaluate_drive_focusbracket_shutter_efcs_nr_vault,
    evaluate_realhw_68pillar_recovery_master,
    inspect_phase370_donors_readonly,
    run_pillar68_standalone_suite,
    run_pillar68a_drive_focusbracket_shutter_efcs_nr_vault_6_scenario_suite,
    run_pillar68b_creativelook_softskin_recoverdb_vault_6_scenario_suite,
    verify_68pillar_recovery,
    verify_68pillar_recovery_master,
    verify_68pillar_recovery_suite,
    verify_all_68_recovery_pillars,
    verify_drive_focusbracket_shutter_efcs_creativelook_recoverdb_and_vault,
    verify_drive_focusbracket_shutter_efcs_creativelook_recoverdb_vault,
)

CI_RELAXED_CLEAN_ROOM_BUDGET_S = 5.0


def _wave66_donors_present() -> bool:
    roots = list(fr.files.iter_donor_work_roots())
    required = (
        P370_DONOR_FX3_APPFW_702_RELPATH,
        P370_DONOR_FX3_BACKUP_BIN_RELPATH,
        P370_DONOR_FX3_UXC_EN_RELPATH,
        P370_DONOR_FX6_APPFW_601_RELPATH,
        P370_DONOR_FX6_UXC_EN_RELPATH,
        P370_DONOR_FX6_UXC_EN_2_RELPATH,
    )
    for rel in required:
        rel_n = rel[5:] if rel.startswith("work/") else rel
        if not any(
            r is not None and ((r / rel_n).exists() or (r.parent / rel).exists())
            for r in roots
        ):
            return False
    return True


def _strip_elapsed_seconds(obj: Any) -> Any:
    """Recursively strip non-deterministic `elapsed_seconds` keys prior to digest checks."""
    if isinstance(obj, dict):
        return {
            k: _strip_elapsed_seconds(v)
            for k, v in obj.items()
            if k != "elapsed_seconds"
        }
    if isinstance(obj, list):
        return [_strip_elapsed_seconds(v) for v in obj]
    if isinstance(obj, tuple):
        return tuple(_strip_elapsed_seconds(v) for v in obj)
    return obj


def _compute_68a_from_spec(spec: fr.DriveModeFocusBracketShutterEfcsNrVaultSpec) -> dict[str, object]:
    return compute_expected_drive_focusbracket_shutter_efcs_nr_state(
        camera_model=spec.camera_model,
        fw_version=spec.fw_version,
        shooting_domain=spec.shooting_domain,
        exposure_mode=spec.exposure_mode,
        still_file_format=spec.still_file_format,
        raw_file_type=spec.raw_file_type,
        hlg_still_image=spec.hlg_still_image,
        flash_active=spec.flash_active,
        aperture_f_number=spec.aperture_f_number,
        drive_mode=spec.drive_mode,
        cont_shoot_speed=spec.cont_shoot_speed,
        self_timer_single_sec=spec.self_timer_single_sec,
        self_timer_cont_option=spec.self_timer_cont_option,
        bracket_step_ev=spec.bracket_step_ev,
        bracket_img_count=spec.bracket_img_count,
        wb_bracket_mode=spec.wb_bracket_mode,
        dro_bracket_mode=spec.dro_bracket_mode,
        bracket_selftimer=spec.bracket_selftimer,
        bracket_order=spec.bracket_order,
        interval_shoot_active=spec.interval_shoot_active,
        interval_output_is_movie=spec.interval_output_is_movie,
        shutter_type_in_interval=spec.shutter_type_in_interval,
        focus_bracket_requested=spec.focus_bracket_requested,
        shutter_type=spec.shutter_type,
        silent_mode=spec.silent_mode,
        requested_flash_sync_reciprocal=spec.requested_flash_sync_reciprocal,
        efcs_enabled=spec.efcs_enabled,
        bulb_requested=spec.bulb_requested,
        anti_flicker_shoot_requested=spec.anti_flicker_shoot_requested,
        shutter_speed_seconds=spec.shutter_speed_seconds,
        long_exposure_nr=spec.long_exposure_nr,
        high_iso_nr=spec.high_iso_nr,
        fx6_noise_suppression=spec.fx6_noise_suppression,
        fx6_apr_lens_cap_covered=spec.fx6_apr_lens_cap_covered,
        reset_action=spec.reset_action,
        requested_vault_slot=spec.requested_vault_slot,
        slot1_holds_tier0_vault=spec.slot1_holds_tier0_vault,
        requested_vault_action=spec.requested_vault_action,
    )


def _compute_68b_from_spec(spec: fr.CreativeLookSoftSkinDeleteProtectRecoverDbVaultSpec) -> dict[str, object]:
    return compute_expected_creativelook_softskin_recoverdb_state(
        camera_model=spec.camera_model,
        fw_version=spec.fw_version,
        shooting_domain=spec.shooting_domain,
        exposure_mode=spec.exposure_mode,
        picture_profile=spec.picture_profile,
        log_shooting_mode=spec.log_shooting_mode,
        hlg_still_image=spec.hlg_still_image,
        creative_look=spec.creative_look,
        cl_contrast=spec.cl_contrast,
        cl_highlights=spec.cl_highlights,
        cl_shadows=spec.cl_shadows,
        cl_fade=spec.cl_fade,
        cl_saturation=spec.cl_saturation,
        cl_sharpness=spec.cl_sharpness,
        cl_sharpness_range=spec.cl_sharpness_range,
        cl_clarity=spec.cl_clarity,
        attempt_edit_saturation_on_bw_se=spec.attempt_edit_saturation_on_bw_se,
        attempt_edit_sharpness_range_in_movie=spec.attempt_edit_sharpness_range_in_movie,
        soft_skin_effect_requested=spec.soft_skin_effect_requested,
        fx6_base_look_mode=spec.fx6_base_look_mode,
        selected_playback_slot=spec.selected_playback_slot,
        delete_scope=spec.delete_scope,
        delete_item_protected=spec.delete_item_protected,
        delete_has_coupled_proxy=spec.delete_has_coupled_proxy,
        delete_confirm_mode=spec.delete_confirm_mode,
        delete_pressing_twice=spec.delete_pressing_twice,
        protect_scope=spec.protect_scope,
        protect_has_coupled_proxy=spec.protect_has_coupled_proxy,
        copy_preserves_protect=spec.copy_preserves_protect,
        recover_image_db_requested=spec.recover_image_db_requested,
        battery_sufficient_for_recover_db=spec.battery_sufficient_for_recover_db,
        display_media_info_still_cap=spec.display_media_info_still_cap,
        reset_action=spec.reset_action,
        requested_vault_slot=spec.requested_vault_slot,
        slot1_holds_tier0_vault=spec.slot1_holds_tier0_vault,
        requested_vault_action=spec.requested_vault_action,
    )


class Phase370Pillar68VerifierTests(unittest.TestCase):
    """Core unit tests for Phase 370 (Pillar 68A + 68B + 68/68 Master)."""

    def test_001_safety_redlines_and_pinned_metadata(self) -> None:
        self.assertEqual(
            PHASE370_SCHEMA,
            "realhw_68pillar_drive_focusbracket_shutter_efcs_creativelook_recoverdb_vault_verifier_v1",
        )
        self.assertEqual(PHASE370_MASTER_SCHEMA, "realhw_68pillar_recovery_master_v1")
        self.assertEqual(PHASE370_VERSION, "1.0.0")
        self.assertEqual(PHASE370_PHASE_NUMBER, 370)
        self.assertEqual(MASTER_68_PILLAR_COUNT, 68)
        self.assertEqual(len(MASTER_68_PILLAR_SPECS), 68)
        self.assertEqual(len(MASTER_68_PILLAR_IDS), 68)
        self.assertEqual(P370_FAST_CLI_BUDGET_SECONDS, 1.50)
        self.assertEqual(P370_CONCURRENT_CEILING_SECONDS, 6.00)
        self.assertEqual(P370_DONOR_INSPECT_BUDGET_SECONDS, 2.0)

        self.assertTrue(CNFLASHA_USERSPACE_WRITE_BLOCKED)
        self.assertTrue(READ_ONLY_DONOR_ACCESS)
        self.assertTrue(P370_SLOT1_VAULT_EROFS_EOPNOTSUPP_ENFORCED)
        self.assertTrue(P370_SLOT1_VAULT_EROFS_EBUSY_ENFORCED)
        self.assertTrue(P370_AIRPLANE_MODE_FORCED_ON)

        for flag in (
            PERSISTENT_EMMC_WRITES_AUTHORIZED,
            SPI_NOR_WRITE_AUTHORIZED,
            EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
            ISP_WRITE_AUTHORIZED,
            PERSISTENT_WRITE_RELEASE,
            ALLOW_BOOT_PARTITION_TARGETING,
            ALLOW_DESTRUCTIVE_FASTBOOT,
            ALLOW_PERSISTENT_JIRITSU_WRITES,
            ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS,
            LIVE_USB_IOKIT_TRANSMIT_ENABLED,
            HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
            OVERALL_READY_FOR_HARDWARE_ATTACH,
            CROSS_MODEL_FLASH_AUTHORIZED,
            BODYDATA_PLACEMENT_OR_FLASH_AUTHORIZED,
            P370_EMMC_WRITES_AUTHORIZED,
            P370_CROSS_MODEL_FLASH_AUTHORIZED,
            P370_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
            P370_OVERALL_READY_FOR_HARDWARE_ATTACH,
            P370_BODYDATA_PLACEMENT_OR_FLASH_AUTHORIZED,
        ):
            self.assertFalse(flag)

        for zero_cnt in (
            OTP_FUSE_TOUCHES,
            OTP_FUSE_WRITES,
            RPMB_COUNTER_INCREMENTS,
            PASSIVE_TX_BYTES_EMITTED,
            PHYSICAL_USB_PACKETS_EMITTED,
            PHYSICAL_DEVICE_WRITES,
            RAW_FIRMWARE_BYTES_LEAKED,
        ):
            self.assertEqual(zero_cnt, 0)

    def test_002_non_shadowing_package_exports_and_aliases(self) -> None:
        self.assertTrue(hasattr(fr, "verify_66pillar_recovery_suite"))
        self.assertTrue(hasattr(fr, "verify_67pillar_recovery_suite"))
        self.assertTrue(hasattr(fr, "verify_68pillar_recovery_suite"))
        self.assertTrue(hasattr(fr, "verify_68pillar_recovery_master"))
        self.assertTrue(callable(verify_68pillar_recovery))
        self.assertTrue(callable(verify_68pillar_recovery_master))
        self.assertTrue(callable(verify_all_68_recovery_pillars))
        self.assertTrue(callable(evaluate_68pillar_recovery_master))
        self.assertIs(
            fr.realhw_68pillar_drive_focusbracket_shutter_efcs_creativelook_recoverdb_vault_verifier,
            sys.modules[
                "fx3_recovery.realhw_68pillar_drive_focusbracket_shutter_efcs_creativelook_recoverdb_vault_verifier"
            ],
        )

    def test_003_fx3_fx6_wave66_capability_booleans_and_constants(self) -> None:
        self.assertEqual(P370_FX3_MODEL_NAME, "ILME-FX3")
        self.assertEqual(P370_FX3_MODEL_ID, 0x91030080)
        self.assertEqual(P370_FX3_HELPGUIDE_ID, "ilc/2210")
        self.assertEqual(P370_FX3_FW_VERSION, "7.02")
        self.assertEqual(P370_FX6_DONOR_MODEL_NAME, "ILME-FX6")
        self.assertEqual(P370_FX6_DONOR_FW_VERSION, "6.01")

        self.assertEqual(len(P370_FX3_ACTIVE_DRIVE_MODES), 9)
        self.assertEqual(P370_FX3_CONT_SHOOT_SPEEDS_FPS, {"Hi+": 10.0, "Hi": 8.0, "Mid": 6.0, "Lo": 3.0})
        self.assertEqual(len(P370_FX3_SELF_TIMER_CONT_ACTIVE_OPTIONS), 6)
        self.assertEqual(P370_FX3_ACTIVE_SHUTTER_TYPES, ("Mechanical Shutter", "Electronic Shutter"))
        self.assertEqual(P370_FX3_FLASH_XSYNC_CEILING_RECIPROCAL, 250)
        self.assertEqual(P370_BKID_EFCS_SONY_TYPO, "BKID_APP_setting_front_curtaion_shutter")
        self.assertEqual(P370_FX3_HIGH_ISO_NR_ACTIVE_LEVELS, ("Normal", "Low", "Off"))
        self.assertEqual(len(P370_FX3_CREATIVE_LOOK_PRESETS), 10)
        self.assertEqual(len(P370_FX3_CREATIVE_LOOK_CUSTOM_SLOTS), 6)
        self.assertEqual(len(P370_FX3_CREATIVE_LOOK_ALL_SLOTS), 16)
        self.assertEqual(len(P370_FX3_CREATIVE_LOOK_PARAM_BOUNDS), 8)
        self.assertEqual(P370_FX3_DISPLAY_MEDIA_INFO_STILL_CAP, 40_000)

        self.assertFalse(P370_FX3_HAS_DORMANT_FOCUS_BRACKET_EXPOSED)
        self.assertFalse(P370_FX3_HAS_SHUTTER_TYPE_AUTO_EXPOSED)
        self.assertFalse(P370_FX3_HAS_DORMANT_SOFT_SKIN_EXPOSED)
        self.assertFalse(P370_FX6_HAS_STILL_DRIVE_MODE)
        self.assertFalse(P370_FX6_HAS_FOCUS_BRACKET)
        self.assertFalse(P370_FX6_HAS_MECHANICAL_SHUTTER)
        self.assertFalse(P370_FX6_HAS_EFCS)
        self.assertFalse(P370_FX6_HAS_LONG_EXP_NR)
        self.assertFalse(P370_FX6_HAS_CREATIVE_LOOK)
        self.assertFalse(P370_FX6_HAS_SOFT_SKIN_EFFECT)

        self.assertTrue(P370_FX3_DRIVE_MODE_RESETTABLE)
        self.assertFalse(P370_FX3_EFCS_RESETTABLE)
        self.assertTrue(P370_FX3_CREATIVE_LOOK_RESETTABLE)
        self.assertFalse(P370_FX3_DELETE_CONFIRM_RESETTABLE)
        self.assertFalse(P370_FX3_DELETE_TWICE_RESETTABLE)

    def test_004_donor_inspect_clean_room_and_local_o_rdonly(self) -> None:
        snap_clean = inspect_phase370_donors_readonly(force_clean_room=True)
        self.assertEqual(snap_clean.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(snap_clean.donor_files_inspected, 17)
        self.assertTrue(snap_clean.all_donors_present)
        self.assertEqual(snap_clean.raw_firmware_bytes_leaked, 0)
        self.assertTrue(snap_clean.under_2_0s_budget)

        snap_auto = inspect_phase370_donors_readonly()
        self.assertEqual(snap_auto.donor_files_inspected, 17)
        self.assertTrue(snap_auto.all_donors_present)
        self.assertEqual(snap_auto.raw_firmware_bytes_leaked, 0)
        if _wave66_donors_present() and not (
            os.environ.get(P370_ENV_CLEAN_ROOM_TEST) == "1"
            or os.environ.get("FX3_FX6_FORCE_CLEAN_ROOM") == "1"
        ):
            self.assertEqual(snap_auto.verification_mode, "LOCAL_DONOR_O_RDONLY")

    def test_005_donor_inspect_env_clean_room_and_donorless_work_root_none(self) -> None:
        with patch.dict(os.environ, {P370_ENV_CLEAN_ROOM_TEST: "1"}):
            snap = inspect_phase370_donors_readonly()
            self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertEqual(snap.donor_files_inspected, 17)
            self.assertTrue(snap.all_donors_present)

        with patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            snap2 = inspect_phase370_donors_readonly()
            self.assertEqual(snap2.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertEqual(snap2.donor_files_inspected, 17)

        with patch.object(fr.files, "iter_donor_work_roots", return_value=(None,)):
            snap_none = inspect_phase370_donors_readonly(force_clean_room=False)
            self.assertEqual(snap_none.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertEqual(snap_none.donor_files_inspected, 17)
            self.assertTrue(snap_none.all_donors_present)

            m_none = verify_68pillar_recovery_suite()
            self.assertTrue(m_none.all_passed)
            self.assertEqual(m_none.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertEqual(m_none.pillars_passed, m_none.pillar_count)

    def test_006_donor_inspect_bad_marker_rejection_helpers(self) -> None:
        mod = fr.realhw_68pillar_drive_focusbracket_shutter_efcs_creativelook_recoverdb_vault_verifier
        ok_elf, msg_elf = mod._check_elf64_aarch64(b"NOT_ELF", "X")
        self.assertFalse(ok_elf)
        self.assertIn("NOT_ELF", msg_elf)

        ok_uxc, msg_uxc = mod._check_uxc7_pack(b"BAD_UXC0000000000", "X")
        self.assertFalse(ok_uxc)
        self.assertIn("BAD_UXC7_MAGIC", msg_uxc)

        ok_bk4, msg_bk4 = mod._check_bk4_backup(b"BAD_BK4" + b"\x00" * 32, "X")
        self.assertFalse(ok_bk4)
        self.assertIn("BAD_BK4_MAGIC", msg_bk4)

    def test_007_default_safe_specs_evaluate_and_verify_combined(self) -> None:
        rep_a = evaluate_drive_focusbracket_shutter_efcs_nr_vault(
            build_default_safe_drive_focusbracket_shutter_efcs_nr_vault_spec()
        )
        self.assertTrue(rep_a.passed)
        self.assertEqual(rep_a.status, P370_STATUS_VERIFIED_PILLAR_68A)
        self.assertIsNone(rep_a.block_code)

        rep_b = evaluate_creativelook_softskin_recoverdb_vault(
            build_default_safe_creativelook_softskin_recoverdb_vault_spec()
        )
        self.assertTrue(rep_b.passed)
        self.assertEqual(rep_b.status, P370_STATUS_VERIFIED_PILLAR_68B)
        self.assertIsNone(rep_b.block_code)

        comb = verify_drive_focusbracket_shutter_efcs_creativelook_recoverdb_and_vault(
            force_clean_room=True
        )
        self.assertTrue(comb.all_passed)
        self.assertEqual(comb.status, P370_STATUS_VERIFIED_PILLAR68_SUITE)
        self.assertEqual(comb.raw_firmware_bytes_leaked, 0)
        self.assertEqual(comb.slot1_sector_writes, 0)

        comb2 = verify_drive_focusbracket_shutter_efcs_creativelook_recoverdb_vault(
            force_clean_room=True
        )
        self.assertTrue(comb2.all_passed)
        self.assertEqual(
            _strip_elapsed_seconds(comb.to_dict()),
            _strip_elapsed_seconds(comb2.to_dict()),
        )

    def test_008_pillar68a_cont_shoot_hi_plus_10fps_f11_lock_and_rate_drop(self) -> None:
        # Hi+ 10fps, > F11 locks AF to first frame, Uncompressed RAW reduces rate, non-live-view
        spec = build_default_safe_drive_focusbracket_shutter_efcs_nr_vault_spec(
            still_file_format="RAW & JPEG",
            raw_file_type="Uncompressed",
            aperture_f_number=16.0,
            drive_mode="Cont. Shooting",
            cont_shoot_speed="Hi+",
            reported_effective_drive_mode="Cont. Shooting",
            reported_nominal_cont_fps=10.0,
            reported_drive_rate_reduced=True,
            reported_live_view_realtime_refresh=False,
            reported_focus_locked_first_frame=True,
            long_exposure_nr="Off",
            reported_effective_long_exp_nr="Off",
            reset_action="None",
            post_drive_mode="Cont. Shooting",
            post_long_exposure_nr="Off",
        )
        self.assertTrue(evaluate_drive_focusbracket_shutter_efcs_nr_vault(spec).passed)

        # Spoof claiming Hi+ has live-view real-time refresh or F16 doesn't lock AF -> BLOCKED
        spoof = build_default_safe_drive_focusbracket_shutter_efcs_nr_vault_spec(
            aperture_f_number=16.0,
            drive_mode="Cont. Shooting",
            cont_shoot_speed="Hi+",
            reported_effective_drive_mode="Cont. Shooting",
            reported_nominal_cont_fps=10.0,
            reported_live_view_realtime_refresh=True,
            reported_focus_locked_first_frame=False,
            long_exposure_nr="Off",
            reported_effective_long_exp_nr="Off",
            reset_action="None",
            post_drive_mode="Cont. Shooting",
            post_long_exposure_nr="Off",
        )
        rep = evaluate_drive_focusbracket_shutter_efcs_nr_vault(spoof)
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P370_BLOCKED_DRIVE_MODE_OR_DORMANT_FOCUS_BRACKET)

    def test_009_pillar68a_dormant_focus_bracket_rejected_fx3_and_fx6(self) -> None:
        for model, fw in (
            (P370_FX3_MODEL_NAME, P370_FX3_FW_VERSION),
            (P370_FX6_DONOR_MODEL_NAME, P370_FX6_DONOR_FW_VERSION),
        ):
            spec = build_default_safe_drive_focusbracket_shutter_efcs_nr_vault_spec(
                camera_model=model,
                fw_version=fw,
                drive_mode="Focus Bracket",
                focus_bracket_requested=True,
            )
            st = _compute_68a_from_spec(spec)
            self.assertEqual(st["focus_bracket_errno"], P370_EOPNOTSUPP_ERRNO)
            self.assertEqual(st["drive_mode_errno"], P370_EOPNOTSUPP_ERRNO)
            rep = evaluate_drive_focusbracket_shutter_efcs_nr_vault(spec)
            self.assertFalse(rep.passed)
            self.assertEqual(rep.block_code, P370_BLOCKED_DRIVE_MODE_OR_DORMANT_FOCUS_BRACKET)

    def test_010_pillar68a_movie_sq_lock_self_timer_cont_and_dro_hlg(self) -> None:
        # Movie/S&Q locks Still Drive Mode
        spec_mv = build_default_safe_drive_focusbracket_shutter_efcs_nr_vault_spec(
            shooting_domain="Movie",
            drive_mode="Cont. Shooting",
        )
        self.assertEqual(_compute_68a_from_spec(spec_mv)["drive_mode_errno"], P370_EOPNOTSUPP_ERRNO)
        self.assertFalse(evaluate_drive_focusbracket_shutter_efcs_nr_vault(spec_mv).passed)

        # DRO Bracket disabled under HLG Still Image = On
        spec_dro = build_default_safe_drive_focusbracket_shutter_efcs_nr_vault_spec(
            hlg_still_image="On",
            drive_mode="DRO Bracket",
        )
        self.assertEqual(_compute_68a_from_spec(spec_dro)["drive_mode_errno"], P370_EOPNOTSUPP_ERRNO)
        self.assertFalse(evaluate_drive_focusbracket_shutter_efcs_nr_vault(spec_dro).passed)

        # Cont. Bracket / Single Bracket disabled in iAuto
        spec_iauto = build_default_safe_drive_focusbracket_shutter_efcs_nr_vault_spec(
            exposure_mode="iAuto",
            drive_mode="Cont. Bracket",
            long_exposure_nr="On",
        )
        self.assertEqual(_compute_68a_from_spec(spec_iauto)["drive_mode_errno"], P370_EOPNOTSUPP_ERRNO)
        self.assertFalse(evaluate_drive_focusbracket_shutter_efcs_nr_vault(spec_iauto).passed)

        # Interval Shoot outputting movie instead of still sequence rejected
        spec_int = build_default_safe_drive_focusbracket_shutter_efcs_nr_vault_spec(
            drive_mode="Interval Shoot Func.",
            interval_shoot_active=True,
            interval_output_is_movie=True,
        )
        self.assertEqual(_compute_68a_from_spec(spec_int)["drive_mode_errno"], P370_EOPNOTSUPP_ERRNO)
        self.assertFalse(evaluate_drive_focusbracket_shutter_efcs_nr_vault(spec_int).passed)

    def test_011_pillar68a_shutter_type_2opt_reject_auto_and_electronic_5lockout(self) -> None:
        # Reject dormant Auto / ANTI_DISTORTION_SHUTTER_AUTO
        for dormant_st in ("Auto", "ANTI_DISTORTION_SHUTTER_AUTO"):
            spec_bad = build_default_safe_drive_focusbracket_shutter_efcs_nr_vault_spec(
                shutter_type=dormant_st,
            )
            self.assertEqual(_compute_68a_from_spec(spec_bad)["shutter_errno"], P370_EOPNOTSUPP_ERRNO)
            rep = evaluate_drive_focusbracket_shutter_efcs_nr_vault(spec_bad)
            self.assertFalse(rep.passed)
            self.assertEqual(rep.block_code, P370_BLOCKED_SHUTTER_2OPT_XSYNC_EFCS_OR_NR_DRIFT)

        # Electronic Shutter or Silent Mode = On hard-locks 5 features
        spec_elec = build_default_safe_drive_focusbracket_shutter_efcs_nr_vault_spec(
            shutter_type="Electronic Shutter",
            efcs_enabled="Off",
            long_exposure_nr="Off",
            reported_effective_shutter_type="Electronic Shutter",
            reported_electronic_or_silent_active=True,
            reported_locked_features_under_electronic=P370_FX3_ELECTRONIC_OR_SILENT_LOCKED_FEATURES,
            reported_effective_efcs="Off",
            reported_effective_long_exp_nr="Off",
            reset_action="None",
            post_shutter_type="Electronic Shutter",
            post_efcs="Off",
            post_long_exposure_nr="Off",
        )
        self.assertTrue(evaluate_drive_focusbracket_shutter_efcs_nr_vault(spec_elec).passed)

        for lock_kw in (
            {"flash_active": True},
            {"bulb_requested": True},
            {"anti_flicker_shoot_requested": True},
        ):
            spec_bypass = build_default_safe_drive_focusbracket_shutter_efcs_nr_vault_spec(
                shutter_type="Electronic Shutter",
                efcs_enabled="Off",
                long_exposure_nr="Off",
                **lock_kw,
            )
            self.assertEqual(_compute_68a_from_spec(spec_bypass)["shutter_errno"], P370_EOPNOTSUPP_ERRNO)
            self.assertFalse(evaluate_drive_focusbracket_shutter_efcs_nr_vault(spec_bypass).passed)

    def test_012_pillar68a_xsync_1_250_ceiling_efcs_reset_resist_and_nr(self) -> None:
        # 1/250 allowed; 1/320 rejected
        spec_320 = build_default_safe_drive_focusbracket_shutter_efcs_nr_vault_spec(
            requested_flash_sync_reciprocal=320,
        )
        self.assertEqual(_compute_68a_from_spec(spec_320)["xsync_errno"], P370_EOPNOTSUPP_ERRNO)
        self.assertFalse(evaluate_drive_focusbracket_shutter_efcs_nr_vault(spec_320).passed)

        # EFCS Off resists Camera Settings Reset, only Initialize restores On
        spec_efcs_reset = build_default_safe_drive_focusbracket_shutter_efcs_nr_vault_spec(
            efcs_enabled="Off",
            reported_effective_efcs="Off",
            reset_action="Camera Settings Reset",
            post_efcs="Off",
        )
        self.assertTrue(evaluate_drive_focusbracket_shutter_efcs_nr_vault(spec_efcs_reset).passed)

        spec_efcs_bad_wipe = build_default_safe_drive_focusbracket_shutter_efcs_nr_vault_spec(
            efcs_enabled="Off",
            reported_effective_efcs="Off",
            reset_action="Camera Settings Reset",
            post_efcs="On",  # Wrong! EFCS resists Camera Settings Reset
        )
        self.assertFalse(evaluate_drive_focusbracket_shutter_efcs_nr_vault(spec_efcs_bad_wipe).passed)

        # Long Exposure NR triggers at >= 1.0 s (and skips at 0.5 s)
        spec_lenr_1s = build_default_safe_drive_focusbracket_shutter_efcs_nr_vault_spec(
            shutter_speed_seconds=2.0,
            long_exposure_nr="On",
            reported_effective_long_exp_nr="On",
            reported_long_exp_nr_subtraction_active=True,
        )
        self.assertTrue(evaluate_drive_focusbracket_shutter_efcs_nr_vault(spec_lenr_1s).passed)

        # High ISO NR dormant HIGH rejected & never alters .ARW RAW
        spec_high_bad = build_default_safe_drive_focusbracket_shutter_efcs_nr_vault_spec(
            high_iso_nr="HIGH",
        )
        self.assertEqual(_compute_68a_from_spec(spec_high_bad)["nr_errno"], P370_EOPNOTSUPP_ERRNO)
        self.assertFalse(evaluate_drive_focusbracket_shutter_efcs_nr_vault(spec_high_bad).passed)

        spec_arw_mut = build_default_safe_drive_focusbracket_shutter_efcs_nr_vault_spec(
            reported_arw_raw_untouched=False,
        )
        self.assertFalse(evaluate_drive_focusbracket_shutter_efcs_nr_vault(spec_arw_mut).passed)

    def test_013_pillar68b_creative_look_custom_and_asymmetric_bounds(self) -> None:
        # Custom Look 6 with asymmetric extremes (Fade/Sharpness/Clarity at 9, Sharpness Range at 5)
        spec_ok = build_default_safe_creativelook_softskin_recoverdb_vault_spec(
            creative_look="Custom Look 6",
            cl_contrast=-9,
            cl_highlights=9,
            cl_shadows=-9,
            cl_fade=9,
            cl_saturation=-9,
            cl_sharpness=9,
            cl_sharpness_range=5,
            cl_clarity=9,
            reported_effective_creative_look="Custom Look 6",
            reset_action="Camera Settings Reset",
            post_creative_look="ST",
        )
        self.assertTrue(evaluate_creativelook_softskin_recoverdb_vault(spec_ok).passed)

        # Negative Clarity (-1) must fail (Clarity is 0..9!)
        spec_bad_clarity = build_default_safe_creativelook_softskin_recoverdb_vault_spec(
            cl_clarity=-1,
        )
        self.assertEqual(_compute_68b_from_spec(spec_bad_clarity)["creative_look_errno"], P370_EINVAL_ERRNO)
        rep = evaluate_creativelook_softskin_recoverdb_vault(spec_bad_clarity)
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P370_BLOCKED_CREATIVE_LOOK_8PARAM_OVERRIDE_OR_SOFTSKIN)

    def test_014_pillar68b_bw_se_sat_lock_movie_range_lock_and_pp_log_hlg_iauto(self) -> None:
        # BW & SE lock Saturation
        for preset in ("BW", "SE"):
            spec_sat = build_default_safe_creativelook_softskin_recoverdb_vault_spec(
                creative_look=preset,
                reported_effective_creative_look=preset,
                reported_saturation_locked=True,
                reset_action="None",
                post_creative_look=preset,
            )
            self.assertTrue(evaluate_creativelook_softskin_recoverdb_vault(spec_sat).passed)

            spec_sat_edit = build_default_safe_creativelook_softskin_recoverdb_vault_spec(
                creative_look=preset,
                attempt_edit_saturation_on_bw_se=True,
            )
            self.assertEqual(_compute_68b_from_spec(spec_sat_edit)["creative_look_errno"], P370_EOPNOTSUPP_ERRNO)
            self.assertFalse(evaluate_creativelook_softskin_recoverdb_vault(spec_sat_edit).passed)

        # Movie / S&Q locks Sharpness Range
        spec_mv_sr = build_default_safe_creativelook_softskin_recoverdb_vault_spec(
            shooting_domain="Movie",
            attempt_edit_sharpness_range_in_movie=True,
        )
        self.assertEqual(_compute_68b_from_spec(spec_mv_sr)["creative_look_errno"], P370_EOPNOTSUPP_ERRNO)
        self.assertFalse(evaluate_creativelook_softskin_recoverdb_vault(spec_mv_sr).passed)

        # PP != Off, Log != Off, HLG Still = On, iAuto all force [-]
        for ov_kw in (
            {"picture_profile": "PP11"},
            {"log_shooting_mode": "Cine EI"},
            {"hlg_still_image": "On"},
            {"exposure_mode": "iAuto"},
        ):
            spec_ov = build_default_safe_creativelook_softskin_recoverdb_vault_spec(
                creative_look="VV2",
                **ov_kw,
            )
            st = _compute_68b_from_spec(spec_ov)
            self.assertTrue(st["creative_look_forced_disabled"])
            self.assertEqual(st["effective_creative_look"], "[-]")
            self.assertEqual(st["creative_look_errno"], P370_EOPNOTSUPP_ERRNO)

    def test_015_pillar68b_dormant_soft_skin_rejected_on_fx3_and_fx6(self) -> None:
        for model, fw, cl in (
            (P370_FX3_MODEL_NAME, P370_FX3_FW_VERSION, "ST"),
            (P370_FX6_DONOR_MODEL_NAME, P370_FX6_DONOR_FW_VERSION, "None"),
        ):
            spec = build_default_safe_creativelook_softskin_recoverdb_vault_spec(
                camera_model=model,
                fw_version=fw,
                creative_look=cl,
                soft_skin_effect_requested=True,
            )
            st = _compute_68b_from_spec(spec)
            self.assertEqual(st["soft_skin_errno"], P370_EOPNOTSUPP_ERRNO)
            rep = evaluate_creativelook_softskin_recoverdb_vault(spec)
            self.assertFalse(rep.passed)
            self.assertEqual(rep.block_code, P370_BLOCKED_CREATIVE_LOOK_8PARAM_OVERRIDE_OR_SOFTSKIN)

    def test_016_pillar68b_playback_delete_protect_recover_db_and_display_media_info(self) -> None:
        # Delete on Slot 2 with coupled Proxy & Delete confirm = "Delete" first + pressing twice = On (quick-delete hazard, resists Reset)
        spec_del = build_default_safe_creativelook_softskin_recoverdb_vault_spec(
            selected_playback_slot=2,
            delete_scope="All in this Folder",
            delete_has_coupled_proxy=True,
            delete_confirm_mode='"Delete" first',
            delete_pressing_twice="On",
            reported_delete_coupled_proxy=True,
            reported_quick_delete_hazard=True,
            reset_action="Camera Settings Reset",
            post_delete_confirm_mode='"Delete" first',
            post_delete_pressing_twice="On",
            requested_vault_slot=2,
        )
        self.assertTrue(evaluate_creativelook_softskin_recoverdb_vault(spec_del).passed)

        # Initialize resets Delete confirm & Delete pressing twice, while Recover Image DB persists!
        spec_init = build_default_safe_creativelook_softskin_recoverdb_vault_spec(
            selected_playback_slot=2,
            delete_confirm_mode='"Delete" first',
            delete_pressing_twice="On",
            recover_image_db_requested=True,
            battery_sufficient_for_recover_db=True,
            reported_quick_delete_hazard=True,
            reported_recover_db_avf_info_rebuilt=True,
            reported_recover_db_ftp_history_wiped=True,
            reset_action="Initialize",
            post_delete_confirm_mode='"Cancel" first',
            post_delete_pressing_twice="Off",
            post_image_db_recovered_persisted=True,
            requested_vault_slot=2,
        )
        self.assertTrue(evaluate_creativelook_softskin_recoverdb_vault(spec_init).passed)

        # Low battery blocks Recover Image DB (EBUSY=16)
        spec_low_bat = build_default_safe_creativelook_softskin_recoverdb_vault_spec(
            recover_image_db_requested=True,
            battery_sufficient_for_recover_db=False,
        )
        self.assertEqual(_compute_68b_from_spec(spec_low_bat)["playback_action_errno"], P370_EBUSY_ERRNO)
        self.assertFalse(evaluate_creativelook_softskin_recoverdb_vault(spec_low_bat).passed)

        # Copy never preserves Protect; Display Media Info still cap <= 40,000
        spec_copy = build_default_safe_creativelook_softskin_recoverdb_vault_spec(
            copy_preserves_protect=True,
        )
        self.assertFalse(evaluate_creativelook_softskin_recoverdb_vault(spec_copy).passed)

        spec_cap = build_default_safe_creativelook_softskin_recoverdb_vault_spec(
            display_media_info_still_cap=40_001,
        )
        self.assertFalse(_compute_68b_from_spec(spec_cap)["media_info_still_cap_ok"])
        self.assertFalse(evaluate_creativelook_softskin_recoverdb_vault(spec_cap).passed)

    def test_017_slot1_vault_erofs_firewall_overlay_escape_and_h0_h3(self) -> None:
        # Both 68A and 68B must reject overlay escapes & Backup.bin H0!=H3 drift
        spec_a_ov = build_default_safe_drive_focusbracket_shutter_efcs_nr_vault_spec(
            overlay_dir="/setting/bad68a",
        )
        rep_a_ov = evaluate_drive_focusbracket_shutter_efcs_nr_vault(spec_a_ov)
        self.assertFalse(rep_a_ov.passed)
        self.assertEqual(rep_a_ov.block_code, P370_BLOCKED_PERSISTENT_OVERLAY_ESCAPE)

        spec_b_ov = build_default_safe_creativelook_softskin_recoverdb_vault_spec(
            overlay_dir="/mnt/emmc/bad68b",
        )
        rep_b_ov = evaluate_creativelook_softskin_recoverdb_vault(spec_b_ov)
        self.assertFalse(rep_b_ov.passed)
        self.assertEqual(rep_b_ov.block_code, P370_BLOCKED_PERSISTENT_OVERLAY_ESCAPE)

        spec_h0_h3 = build_default_safe_creativelook_softskin_recoverdb_vault_spec(
            backup_bin_h3_sha256="f" * 64,
            tier0_surfaces_h0_h3_matched=15,
        )
        rep_h0_h3 = evaluate_creativelook_softskin_recoverdb_vault(spec_h0_h3)
        self.assertFalse(rep_h0_h3.passed)
        self.assertEqual(rep_h0_h3.block_code, P370_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT)

    def test_018_invalid_specs_return_expected_block_codes(self) -> None:
        sa = build_default_safe_drive_focusbracket_shutter_efcs_nr_vault_spec(
            shooting_domain="InvalidDomain",
        )
        ra = evaluate_drive_focusbracket_shutter_efcs_nr_vault(sa)
        self.assertFalse(ra.passed)
        self.assertEqual(ra.block_code, P370_BLOCKED_INVALID_PILLAR68A_SPEC)

        sb = build_default_safe_creativelook_softskin_recoverdb_vault_spec(
            shooting_domain="InvalidDomain",
        )
        rb = evaluate_creativelook_softskin_recoverdb_vault(sb)
        self.assertFalse(rb.passed)
        self.assertEqual(rb.block_code, P370_BLOCKED_INVALID_PILLAR68B_SPEC)

    def test_019_6_scenario_suites_68a_and_68b(self) -> None:
        res_a = run_pillar68a_drive_focusbracket_shutter_efcs_nr_vault_6_scenario_suite()
        self.assertTrue(res_a.passed)
        self.assertEqual(res_a.status, P370_STATUS_VERIFIED_PILLAR_68A)
        self.assertEqual(res_a.scenarios_passed, 6)
        self.assertEqual(res_a.scenarios_total, 6)
        self.assertEqual(tuple(s.scenario_id for s in res_a.scenarios), P370_PILLAR_68A_SCENARIO_IDS)
        self.assertEqual(sum(1 for s in res_a.scenarios if s.expected_allowed), 2)
        self.assertEqual(sum(1 for s in res_a.scenarios if not s.expected_allowed), 4)

        res_b = run_pillar68b_creativelook_softskin_recoverdb_vault_6_scenario_suite()
        self.assertTrue(res_b.passed)
        self.assertEqual(res_b.status, P370_STATUS_VERIFIED_PILLAR_68B)
        self.assertEqual(res_b.scenarios_passed, 6)
        self.assertEqual(res_b.scenarios_total, 6)
        self.assertEqual(tuple(s.scenario_id for s in res_b.scenarios), P370_PILLAR_68B_SCENARIO_IDS)
        self.assertEqual(sum(1 for s in res_b.scenarios if s.expected_allowed), 2)
        self.assertEqual(sum(1 for s in res_b.scenarios if not s.expected_allowed), 4)

    def test_020_standalone_suite_normal_clean_room_and_deterministic_sha(self) -> None:
        r1 = run_pillar68_standalone_suite(force_clean_room=True)
        r2 = run_pillar68_standalone_suite(force_clean_room=True)
        self.assertTrue(r1.all_passed)
        self.assertEqual(r1.status, P370_STATUS_VERIFIED_PILLAR68_SUITE)
        self.assertEqual(r1.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(r1.suite_sha256, r2.suite_sha256)
        self.assertEqual(_strip_elapsed_seconds(r1.to_dict()), _strip_elapsed_seconds(r2.to_dict()))
        self.assertEqual(r1.raw_firmware_bytes_leaked, 0)
        self.assertEqual(r1.slot1_sector_writes, 0)
        self.assertEqual(r1.cnflasha_writes, 0)
        self.assertEqual(r1.rf_packets_transmitted, 0)

        r_auto = run_pillar68_standalone_suite()
        self.assertTrue(r_auto.all_passed)
        self.assertEqual(r_auto.donor_snapshot.donor_files_inspected, 17)
        self.assertLessEqual(r_auto.elapsed_seconds, CI_RELAXED_CLEAN_ROOM_BUDGET_S)

    def test_021_master_68pillar_normal_and_clean_room_and_sha_determinism(self) -> None:
        m_clean1 = verify_68pillar_recovery_master(force_clean_room=True)
        m_clean2 = evaluate_realhw_68pillar_recovery_master(force_clean_room=True)
        self.assertTrue(m_clean1.all_passed)
        self.assertEqual(m_clean1.status, P370_STATUS_VERIFIED_68OF68_AGGREGATOR)
        self.assertEqual(m_clean1.pillar_count, 68)
        self.assertEqual(m_clean1.pillars_passed, 68)
        self.assertGreaterEqual(m_clean1.pillar_count, 68)
        self.assertEqual(m_clean1.failed_pillars, ())
        self.assertEqual(m_clean1.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(m_clean1.master_68pillar_sha256, m_clean2.master_68pillar_sha256)
        self.assertEqual(
            _strip_elapsed_seconds(m_clean1.to_dict()),
            _strip_elapsed_seconds(m_clean2.to_dict()),
        )
        self.assertLessEqual(m_clean1.elapsed_seconds, CI_RELAXED_CLEAN_ROOM_BUDGET_S)
        self.assertEqual(m_clean1.raw_firmware_bytes_leaked, 0)
        self.assertFalse(m_clean1.emmc_writes_authorized)
        self.assertFalse(m_clean1.fx3_has_dormant_focus_bracket_exposed)
        self.assertFalse(m_clean1.fx3_has_shutter_type_auto_exposed)
        self.assertFalse(m_clean1.fx3_has_dormant_soft_skin_exposed)
        self.assertFalse(m_clean1.fx6_has_still_drive_mode)
        self.assertFalse(m_clean1.fx3_efcs_resettable)
        self.assertTrue(m_clean1.fx3_creative_look_resettable)

        m_auto = verify_68pillar_recovery()
        self.assertTrue(m_auto.all_passed)
        self.assertEqual(m_auto.pillars_passed, 68)
        self.assertEqual(m_auto.pillar_count, 68)
        self.assertLessEqual(m_auto.elapsed_seconds, CI_RELAXED_CLEAN_ROOM_BUDGET_S)

    def test_022_master_68pillar_fault_injection_and_unknown_pillar_rejection(self) -> None:
        m_fault = evaluate_realhw_68pillar_recovery_master(
            force_clean_room=True,
            fault_inject_pillar=MASTER_68_PILLAR_IDS[-1],
        )
        self.assertFalse(m_fault.all_passed)
        self.assertEqual(m_fault.status, P370_STATUS_FAIL_68OF68_AGGREGATOR)
        self.assertEqual(m_fault.pillars_passed, 67)
        self.assertEqual(m_fault.failed_pillars, (MASTER_68_PILLAR_IDS[-1],))

        with self.assertRaises(ValueError):
            evaluate_realhw_68pillar_recovery_master(
                force_clean_room=True,
                fault_inject_pillar="nonexistent_pillar_999",
            )

    def test_023_cli_help_json_and_out_normal_and_clean_room(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONPATH"] = f"{ADAPTER_ROOT}:{REPO_ROOT / 'outputs' / 'fx3-safety'}"

        for cmd in (
            "verify-pillar68-drive-focusbracket-shutter-efcs-creativelook-recoverdb-vault",
            "verify-pillar68-recovery",
            "verify-68pillar-recovery",
        ):
            help_proc = subprocess.run(
                [sys.executable, "-B", "-m", "fx3_recovery", cmd, "--help"],
                cwd=str(REPO_ROOT),
                env=env,
                capture_output=True,
                text=True,
                timeout=45,
            )
            self.assertEqual(help_proc.returncode, 0, f"{cmd} --help: {help_proc.stderr}")
            self.assertIn(cmd, help_proc.stdout)

        work_tests = REPO_ROOT / "work" / "_tests"
        work_tests.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=work_tests, prefix="p370_cli_test_") as tmpd:
            out_dir = Path(tmpd) / "master_out"
            proc_master = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    "-m",
                    "fx3_recovery",
                    "verify-68pillar-recovery",
                    "--force-clean-room",
                    "--json",
                    "--out",
                    str(out_dir),
                ],
                cwd=str(REPO_ROOT),
                env=env,
                capture_output=True,
                text=True,
                timeout=45,
            )
            self.assertEqual(proc_master.returncode, 0, proc_master.stdout or proc_master.stderr)
            payload = json.loads(proc_master.stdout)
            self.assertTrue(payload["all_passed"])
            self.assertEqual(payload["pillars_passed"], 68)
            self.assertGreaterEqual(payload["pillar_count"], 68)
            self.assertEqual(payload["raw_firmware_bytes_leaked"], 0)
            self.assertLessEqual(payload["elapsed_seconds"], CI_RELAXED_CLEAN_ROOM_BUDGET_S)
            report_file = out_dir / "68pillar-recovery-master-report.json"
            self.assertTrue(report_file.is_file())

            out_p68 = Path(tmpd) / "p68_out"
            proc_p68 = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    "-m",
                    "fx3_recovery",
                    "verify-pillar68-recovery",
                    "--json",
                    "--out",
                    str(out_p68),
                ],
                cwd=str(REPO_ROOT),
                env=env,
                capture_output=True,
                text=True,
                timeout=45,
            )
            self.assertEqual(proc_p68.returncode, 0, proc_p68.stdout or proc_p68.stderr)
            p68_payload = json.loads(proc_p68.stdout)
            self.assertTrue(p68_payload["all_passed"])
            self.assertEqual(p68_payload["raw_firmware_bytes_leaked"], 0)
            self.assertTrue(
                (out_p68 / "pillar68-drive-focusbracket-shutter-efcs-creativelook-recoverdb-vault-report.json").is_file()
            )


# ---------------------------------------------------------------------------
# Parameterized Coverage Matrices (~150+ Total Tests with Core Tests)
# ---------------------------------------------------------------------------


def _make_drive_mode_test(mode: str, expect_ok: bool, extra: dict[str, Any]):
    def _test(self: unittest.TestCase) -> None:
        kwargs: dict[str, Any] = {
            "drive_mode": mode,
            "reported_effective_drive_mode": mode if expect_ok else "Single Shooting",
            "reset_action": "Camera Settings Reset",
            "post_drive_mode": "Single Shooting",
        }
        kwargs.update(extra)
        if mode == "Interval Shoot Func.":
            kwargs["interval_shoot_active"] = True
        spec = build_default_safe_drive_focusbracket_shutter_efcs_nr_vault_spec(**kwargs)
        st = _compute_68a_from_spec(spec)
        if expect_ok:
            self.assertIsNone(st["drive_mode_errno"])
            self.assertTrue(evaluate_drive_focusbracket_shutter_efcs_nr_vault(spec).passed)
        else:
            self.assertEqual(st["drive_mode_errno"], P370_EOPNOTSUPP_ERRNO)
            self.assertFalse(evaluate_drive_focusbracket_shutter_efcs_nr_vault(spec).passed)
    return _test


def _make_cont_speed_test(speed: str, fps: float, fnum: float, live_rt: bool, af_lock: bool):
    def _test(self: unittest.TestCase) -> None:
        spec = build_default_safe_drive_focusbracket_shutter_efcs_nr_vault_spec(
            drive_mode="Cont. Shooting",
            cont_shoot_speed=speed,
            aperture_f_number=fnum,
            long_exposure_nr="Off",
            reported_effective_drive_mode="Cont. Shooting",
            reported_nominal_cont_fps=fps,
            reported_live_view_realtime_refresh=live_rt,
            reported_focus_locked_first_frame=af_lock,
            reported_effective_long_exp_nr="Off",
            reset_action="None",
            post_drive_mode="Cont. Shooting",
            post_long_exposure_nr="Off",
        )
        self.assertTrue(evaluate_drive_focusbracket_shutter_efcs_nr_vault(spec).passed)
    return _test


def _make_self_timer_cont_test(option: str, expect_ok: bool):
    def _test(self: unittest.TestCase) -> None:
        spec = build_default_safe_drive_focusbracket_shutter_efcs_nr_vault_spec(
            drive_mode="Self-timer(Cont)",
            self_timer_cont_option=option,
            reported_effective_drive_mode="Self-timer(Cont)" if expect_ok else "Single Shooting",
        )
        st = _compute_68a_from_spec(spec)
        if expect_ok:
            self.assertIsNone(st["drive_mode_errno"])
            self.assertTrue(evaluate_drive_focusbracket_shutter_efcs_nr_vault(spec).passed)
        else:
            self.assertEqual(st["drive_mode_errno"], P370_EOPNOTSUPP_ERRNO)
            self.assertFalse(evaluate_drive_focusbracket_shutter_efcs_nr_vault(spec).passed)
    return _test


def _make_exp_bracket_combo_test(step: float, count: int, expect_ok: bool):
    def _test(self: unittest.TestCase) -> None:
        spec = build_default_safe_drive_focusbracket_shutter_efcs_nr_vault_spec(
            drive_mode="Cont. Bracket",
            bracket_step_ev=step,
            bracket_img_count=count,
            long_exposure_nr="Off",
            reported_effective_drive_mode="Cont. Bracket" if expect_ok else "Single Shooting",
            reported_effective_long_exp_nr="Off",
        )
        st = _compute_68a_from_spec(spec)
        if expect_ok:
            self.assertIsNone(st["drive_mode_errno"])
            self.assertTrue(evaluate_drive_focusbracket_shutter_efcs_nr_vault(spec).passed)
        else:
            self.assertEqual(st["drive_mode_errno"], P370_EOPNOTSUPP_ERRNO)
            self.assertFalse(evaluate_drive_focusbracket_shutter_efcs_nr_vault(spec).passed)
    return _test


def _make_shutter_xsync_nr_test(
    shutter_t: str,
    silent: str,
    xsync_rec: int,
    lenr: str,
    hisor: str,
    shutter_s: float,
    expect_ok: bool,
):
    def _test(self: unittest.TestCase) -> None:
        elec = (shutter_t == "Electronic Shutter") or (silent == "On")
        spec = build_default_safe_drive_focusbracket_shutter_efcs_nr_vault_spec(
            shutter_type=shutter_t,
            silent_mode=silent,
            requested_flash_sync_reciprocal=xsync_rec,
            efcs_enabled="Off" if elec else "On",
            shutter_speed_seconds=shutter_s,
            long_exposure_nr=lenr,
            high_iso_nr=hisor,
            reported_effective_shutter_type=shutter_t if shutter_t in P370_FX3_ACTIVE_SHUTTER_TYPES else "Mechanical Shutter",
            reported_electronic_or_silent_active=elec,
            reported_locked_features_under_electronic=P370_FX3_ELECTRONIC_OR_SILENT_LOCKED_FEATURES if elec else (),
            reported_effective_efcs="Off" if elec else "On",
            reported_effective_long_exp_nr=lenr,
            reported_long_exp_nr_subtraction_active=(lenr == "On" and not elec and shutter_s >= 1.0),
            reported_effective_high_iso_nr=hisor if hisor in P370_FX3_HIGH_ISO_NR_ACTIVE_LEVELS else "Normal",
            reset_action="None",
            post_shutter_type=shutter_t if shutter_t in P370_FX3_ACTIVE_SHUTTER_TYPES else "Mechanical Shutter",
            post_efcs="Off" if elec else "On",
            post_long_exposure_nr=lenr,
            post_high_iso_nr=hisor if hisor in P370_FX3_HIGH_ISO_NR_ACTIVE_LEVELS else "Normal",
        )
        self.assertEqual(evaluate_drive_focusbracket_shutter_efcs_nr_vault(spec).passed, expect_ok)
    return _test


def _make_creative_look_slot_test(slot: str):
    def _test(self: unittest.TestCase) -> None:
        sat_locked = slot in ("BW", "SE")
        spec = build_default_safe_creativelook_softskin_recoverdb_vault_spec(
            creative_look=slot,
            reported_effective_creative_look=slot,
            reported_saturation_locked=sat_locked,
            reset_action="Camera Settings Reset",
            post_creative_look="ST",
        )
        self.assertTrue(evaluate_creativelook_softskin_recoverdb_vault(spec).passed)
    return _test


def _make_creative_look_param_bound_test(field: str, val: int, expect_ok: bool):
    def _test(self: unittest.TestCase) -> None:
        spec = build_default_safe_creativelook_softskin_recoverdb_vault_spec(**{field: val})
        st = _compute_68b_from_spec(spec)
        if expect_ok:
            self.assertIsNone(st["creative_look_errno"])
            self.assertTrue(evaluate_creativelook_softskin_recoverdb_vault(spec).passed)
        else:
            self.assertEqual(st["creative_look_errno"], P370_EINVAL_ERRNO)
            self.assertFalse(evaluate_creativelook_softskin_recoverdb_vault(spec).passed)
    return _test


def _make_playback_delete_protect_test(
    del_scope: str,
    prot_scope: str,
    protected_item: bool,
    coupled_proxy: bool,
):
    def _test(self: unittest.TestCase) -> None:
        spec = build_default_safe_creativelook_softskin_recoverdb_vault_spec(
            selected_playback_slot=2,
            delete_scope=del_scope,
            delete_item_protected=protected_item,
            delete_has_coupled_proxy=coupled_proxy if del_scope != "None" else False,
            protect_scope=prot_scope,
            protect_has_coupled_proxy=coupled_proxy if prot_scope != "None" else False,
            reported_delete_coupled_proxy=bool(del_scope != "None" and coupled_proxy and not protected_item),
            reported_delete_protected_skipped=bool(del_scope != "None" and protected_item),
            reported_protect_coupled_proxy=bool(prot_scope != "None" and coupled_proxy),
            requested_vault_slot=2,
        )
        self.assertTrue(evaluate_creativelook_softskin_recoverdb_vault(spec).passed)
    return _test


def _make_slot1_write_block_test(action: str, errno_str: str):
    def _test(self: unittest.TestCase) -> None:
        expect_pass = errno_str == "EROFS"
        sa = build_default_safe_drive_focusbracket_shutter_efcs_nr_vault_spec(
            requested_vault_slot=1,
            requested_vault_action=action,
            reported_vault_action_allowed=False,
            vault_firewall_errno=errno_str,
        )
        self.assertEqual(evaluate_drive_focusbracket_shutter_efcs_nr_vault(sa).passed, expect_pass)

        sb = build_default_safe_creativelook_softskin_recoverdb_vault_spec(
            requested_vault_slot=1,
            requested_vault_action=action,
            reported_vault_action_allowed=False,
            vault_firewall_errno=errno_str,
        )
        self.assertEqual(evaluate_creativelook_softskin_recoverdb_vault(sb).passed, expect_pass)
    return _test


def _make_reset_action_matrix_test(reset_action: str):
    def _test(self: unittest.TestCase) -> None:
        init = reset_action == "Initialize"
        keep = reset_action == "None"
        sa = build_default_safe_drive_focusbracket_shutter_efcs_nr_vault_spec(
            drive_mode="WB bracket",
            reported_effective_drive_mode="WB bracket",
            shutter_type="Mechanical Shutter",
            efcs_enabled="Off",
            long_exposure_nr="Off",
            high_iso_nr="Low",
            reported_effective_efcs="Off",
            reported_effective_long_exp_nr="Off",
            reported_effective_high_iso_nr="Low",
            shutter_type_in_interval="Mechanical Shutter",
            reset_action=reset_action,
            post_drive_mode="WB bracket" if keep else P370_FX3_DRIVE_MODE_DEFAULT,
            post_shutter_type="Mechanical Shutter",
            post_shutter_type_in_interval="Mechanical Shutter" if keep else P370_FX3_INTERVAL_SHUTTER_DEFAULT,
            post_efcs=P370_FX3_EFCS_DEFAULT if init else "Off",
            post_long_exposure_nr="Off" if keep else P370_FX3_LONG_EXP_NR_DEFAULT,
            post_high_iso_nr="Low" if keep else P370_FX3_HIGH_ISO_NR_DEFAULT,
        )
        self.assertTrue(evaluate_drive_focusbracket_shutter_efcs_nr_vault(sa).passed)

        sb = build_default_safe_creativelook_softskin_recoverdb_vault_spec(
            creative_look="FL",
            reported_effective_creative_look="FL",
            delete_confirm_mode='"Delete" first',
            delete_pressing_twice="On",
            reported_quick_delete_hazard=True,
            recover_image_db_requested=True,
            reported_recover_db_avf_info_rebuilt=True,
            reported_recover_db_ftp_history_wiped=True,
            reset_action=reset_action,
            post_creative_look="FL" if keep else P370_FX3_CREATIVE_LOOK_DEFAULT,
            post_delete_confirm_mode=P370_FX3_DELETE_CONFIRM_DEFAULT if init else '"Delete" first',
            post_delete_pressing_twice="Off" if init else "On",
            post_image_db_recovered_persisted=True,
        )
        self.assertTrue(evaluate_creativelook_softskin_recoverdb_vault(sb).passed)
    return _test


def _make_donor_presence_test(idx: int):
    def _test(self: unittest.TestCase) -> None:
        snap = inspect_phase370_donors_readonly(force_clean_room=True)
        art = snap.artifacts[idx]
        self.assertTrue(art.matches_pinned)
        self.assertTrue(art.present)
        self.assertEqual(len(art.digest_sha256), 64)
    return _test


def _make_master_pillar_id_test(idx: int):
    def _test(self: unittest.TestCase) -> None:
        m = verify_all_68_recovery_pillars(force_clean_room=True)
        pillar = m.pillars[idx]
        self.assertTrue(pillar.passed)
        self.assertEqual(pillar.pillar_id, MASTER_68_PILLAR_IDS[idx])
    return _test


def _make_fault_inject_pillar_test(idx: int):
    def _test(self: unittest.TestCase) -> None:
        pid = MASTER_68_PILLAR_IDS[idx]
        m = evaluate_realhw_68pillar_recovery_master(
            force_clean_room=True,
            fault_inject_pillar=pid,
        )
        self.assertFalse(m.all_passed)
        self.assertEqual(m.pillars_passed, 67)
        self.assertEqual(m.failed_pillars, (pid,))
    return _test


def _install_parameterized_tests() -> None:
    idx = 24

    # 1. All 9 active Drive Modes + Dormant Focus Bracket + invalid (11 tests)
    for dm in P370_FX3_ACTIVE_DRIVE_MODES:
        clean = dm.lower().replace(" ", "_").replace("(", "_").replace(")", "").replace(".", "")
        extra: dict[str, Any] = {}
        if dm == "Cont. Shooting":
            extra = {
                "long_exposure_nr": "Off",
                "reported_nominal_cont_fps": 10.0,
                "reported_live_view_realtime_refresh": False,
                "reported_effective_long_exp_nr": "Off",
                "post_long_exposure_nr": "On",
            }
        elif dm == "Cont. Bracket":
            extra = {
                "long_exposure_nr": "Off",
                "reported_effective_long_exp_nr": "Off",
                "post_long_exposure_nr": "On",
            }
        setattr(
            Phase370Pillar68VerifierTests,
            f"test_{idx:03d}_drive_mode_active_{clean}",
            _make_drive_mode_test(dm, True, extra),
        )
        idx += 1
    for bad_dm in ("Focus Bracket", "Motion Shot"):
        clean = bad_dm.lower().replace(" ", "_")
        setattr(
            Phase370Pillar68VerifierTests,
            f"test_{idx:03d}_drive_mode_reject_{clean}",
            _make_drive_mode_test(bad_dm, False, {}),
        )
        idx += 1

    # 2. Cont. Shooting Speeds & >F11 AF lock matrix (8 tests)
    for spd, fps in P370_FX3_CONT_SHOOT_SPEEDS_FPS.items():
        for fnum, exp_lock in ((4.0, False), (16.0, spd in ("Hi+", "Hi", "Mid"))):
            clean_spd = spd.lower().replace("+", "_plus")
            setattr(
                Phase370Pillar68VerifierTests,
                f"test_{idx:03d}_cont_{clean_spd}_f{int(fnum)}",
                _make_cont_speed_test(spd, fps, fnum, spd != "Hi+", exp_lock),
            )
            idx += 1

    # 3. Self-timer(Cont) 6 active + 3 dormant combos (9 tests)
    for opt in P370_FX3_SELF_TIMER_CONT_ACTIVE_OPTIONS:
        clean = opt.lower().replace(" ", "_").replace(".", "")
        setattr(
            Phase370Pillar68VerifierTests,
            f"test_{idx:03d}_selftimer_cont_active_{clean}",
            _make_self_timer_cont_test(opt, True),
        )
        idx += 1
    for bad_opt in P370_FX3_SELF_TIMER_CONT_DORMANT_OPTIONS:
        clean = bad_opt.lower().replace(" ", "_").replace(".", "")
        setattr(
            Phase370Pillar68VerifierTests,
            f"test_{idx:03d}_selftimer_cont_reject_{clean}",
            _make_self_timer_cont_test(bad_opt, False),
        )
        idx += 1

    # 4. Exposure Bracket Step x Count valid & invalid matrix (18 tests)
    for step, counts in P370_FX3_EXP_BRACKET_STEPS_COUNTS.items():
        for cnt in counts:
            setattr(
                Phase370Pillar68VerifierTests,
                f"test_{idx:03d}_bracket_ev_{str(step).replace('.', '_')}_x{cnt}",
                _make_exp_bracket_combo_test(step, cnt, True),
            )
            idx += 1
    for bad_step, bad_cnt in ((2.0, 9), (3.0, 9)):
        setattr(
            Phase370Pillar68VerifierTests,
            f"test_{idx:03d}_bracket_reject_ev_{str(bad_step).replace('.', '_')}_x{bad_cnt}",
            _make_exp_bracket_combo_test(bad_step, bad_cnt, False),
        )
        idx += 1

    # 5. Shutter Type / X-Sync / Long Exp NR / High ISO NR matrix (10 tests)
    shutter_cases = (
        ("mech_250_lenr1s_norm", "Mechanical Shutter", "Off", 250, "On", "Normal", 1.0, True),
        ("mech_250_lenr_off_low", "Mechanical Shutter", "Off", 250, "Off", "Low", 0.5, True),
        ("mech_250_highiso_off", "Mechanical Shutter", "Off", 250, "On", "Off", 0.25, True),
        ("elec_silent_off_lenr_off", "Electronic Shutter", "Off", 250, "Off", "Normal", 0.5, True),
        ("mech_silent_on_lenr_off", "Mechanical Shutter", "On", 250, "Off", "Normal", 0.5, True),
        ("reject_shutter_auto", "Auto", "Off", 250, "On", "Normal", 0.5, False),
        ("reject_dormant_anti_dist_auto", "ANTI_DISTORTION_SHUTTER_AUTO", "Off", 250, "On", "Normal", 0.5, False),
        ("reject_xsync_320", "Mechanical Shutter", "Off", 320, "On", "Normal", 0.003125, False),
        ("reject_highiso_dormant_high", "Mechanical Shutter", "Off", 250, "On", "HIGH", 0.5, False),
        ("reject_lenr_on_under_elec", "Electronic Shutter", "Off", 250, "On", "Normal", 2.0, False),
    )
    for label, st_t, sil, xrec, lenr, hnr, sh_s, eok in shutter_cases:
        setattr(
            Phase370Pillar68VerifierTests,
            f"test_{idx:03d}_shutter_nr_{label}",
            _make_shutter_xsync_nr_test(st_t, sil, xrec, lenr, hnr, sh_s, eok),
        )
        idx += 1

    # 6. All 16 Creative Look Slots (10 Presets + 6 Custom) (16 tests)
    for slot in P370_FX3_CREATIVE_LOOK_ALL_SLOTS:
        clean = slot.lower().replace(" ", "_")
        setattr(
            Phase370Pillar68VerifierTests,
            f"test_{idx:03d}_creative_look_slot_{clean}",
            _make_creative_look_slot_test(slot),
        )
        idx += 1

    # 7. All 8 Creative Look Asymmetric Parameters (min, max, underflow, overflow = 32 tests)
    field_map = {
        "contrast": "cl_contrast",
        "highlights": "cl_highlights",
        "shadows": "cl_shadows",
        "fade": "cl_fade",
        "saturation": "cl_saturation",
        "sharpness": "cl_sharpness",
        "sharpness_range": "cl_sharpness_range",
        "clarity": "cl_clarity",
    }
    for pkey, (lo, hi) in P370_FX3_CREATIVE_LOOK_PARAM_BOUNDS.items():
        fname = field_map[pkey]
        for tag, val, eok in (
            ("min", lo, True),
            ("max", hi, True),
            ("under", lo - 1, False),
            ("over", hi + 1, False),
        ):
            setattr(
                Phase370Pillar68VerifierTests,
                f"test_{idx:03d}_cl_param_{pkey}_{tag}",
                _make_creative_look_param_bound_test(fname, val, eok),
            )
            idx += 1

    # 8. Playback Delete & Protect scopes + proxy coupling (9 tests)
    pb_cases = (
        ("del_folder_proxy", "All in this Folder", "None", False, True),
        ("del_date_protected_skip", "All with this date", "None", True, True),
        ("del_other_than_this", "All Other Than This Img.", "None", False, False),
        ("del_group_proxy", "All Images in This Group", "None", False, True),
        ("del_multiple", "Multiple Img.", "None", False, False),
        ("prot_folder_proxy", "None", "All in this Folder", False, True),
        ("prot_cancel_date", "None", "Cancel All with this date", False, False),
        ("prot_group_proxy", "None", "All Images in This Group", False, True),
        ("prot_multiple", "None", "Multiple Img.", False, False),
    )
    for label, ds, ps, prt, cpx in pb_cases:
        setattr(
            Phase370Pillar68VerifierTests,
            f"test_{idx:03d}_playback_{label}",
            _make_playback_delete_protect_test(ds, ps, prt, cpx),
        )
        idx += 1

    # 9. Slot-1 Write Firewall actions x errno pairs (5 actions x 3 errnos = 15 tests)
    for action in sorted(P370_WRITE_MUTATING_VAULT_ACTIONS):
        for err_str in ("EROFS", "EOPNOTSUPP", "EBUSY"):
            setattr(
                Phase370Pillar68VerifierTests,
                f"test_{idx:03d}_slot1_block_{action.lower()}_{err_str.lower()}",
                _make_slot1_write_block_test(action, err_str),
            )
            idx += 1

    # 10. Reset Action Matrices (3 tests)
    for r_act in ("None", "Camera Settings Reset", "Initialize"):
        clean = r_act.lower().replace(" ", "_")
        setattr(
            Phase370Pillar68VerifierTests,
            f"test_{idx:03d}_reset_matrix_{clean}",
            _make_reset_action_matrix_test(r_act),
        )
        idx += 1

    # 11. Individual Donor Checks (17 Wave-66 donors)
    for d_i in range(17):
        setattr(
            Phase370Pillar68VerifierTests,
            f"test_{idx:03d}_donor_artifact_{d_i:02d}",
            _make_donor_presence_test(d_i),
        )
        idx += 1

    # 12. Key & final pillars across MASTER_68_PILLAR_IDS (16 tests)
    for p_i in (*range(0, 65, 5), 65, 66, 67):
        setattr(
            Phase370Pillar68VerifierTests,
            f"test_{idx:03d}_master_pillar_{p_i+1:02d}",
            _make_master_pillar_id_test(p_i),
        )
        idx += 1

    # 13. Fault injection across 5 key pillars incl. 66, 67 & 68 (5 tests)
    for p_i in (0, 21, 65, 66, 67):
        setattr(
            Phase370Pillar68VerifierTests,
            f"test_{idx:03d}_fault_inject_pillar_{p_i+1:02d}",
            _make_fault_inject_pillar_test(p_i),
        )
        idx += 1


_install_parameterized_tests()


if __name__ == "__main__":
    unittest.main()
