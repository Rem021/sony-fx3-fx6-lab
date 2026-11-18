"""Dual-mode fast unit tests (>= 88) for Phase 326 Pillar 58 & 58/58 Recovery Master:
Wave-56 [Dial Customize] 5-Item Tree vs Dormant Symbols, 3-Dial Topology + My Dial 1..3
Lock-Override, [Fn Menu Settings] 12+12 Split, [Live View Display Set.] 3-Item Reset Split,
[Grid Line] Clean-HDMI Isolation, [Manage User LUTs] / [Embed LUT File] vs PPLUT1..4 Baking,
ILME-FX6 Boundaries & Slot-1 Tier-0 Vault EROFS=30 Firewall.
"""

from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import fx3_recovery
from fx3_recovery import __main__ as cli_main
from fx3_recovery import realhw_58pillar_dial_customize_mydial_fn12x2_liveview_lut_embed_vault_verifier as p326
from fx3_recovery import (
    ALLOW_BOOT_PARTITION_TARGETING,
    ALLOW_DESTRUCTIVE_FASTBOOT,
    ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS,
    ALLOW_PERSISTENT_JIRITSU_WRITES,
    CROSS_MODEL_FLASH_AUTHORIZED,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    ISP_WRITE_AUTHORIZED,
    LIVE_USB_IOKIT_TRANSMIT_ENABLED,
    MASTER_58_PILLAR_COUNT,
    MASTER_58_PILLAR_IDS,
    MASTER_58_PILLAR_SPECS,
    OTP_FUSE_TOUCHES,
    OTP_FUSE_WRITES,
    OVERALL_READY_FOR_HARDWARE_ATTACH,
    P326_AV_TV_ROTATE_DEFAULT,
    P326_AV_TV_ROTATE_F_RESID16,
    P326_AV_TV_ROTATE_NORMAL_F_RESID16,
    P326_AV_TV_ROTATE_REVERSE_F_RESID16,
    P326_BKID_AV_TV_ROTATE,
    P326_BKID_DEVICE_LOCK,
    P326_BKID_DORMANT_DIAL_SETUP,
    P326_BKID_EMBED_LUT_FILE,
    P326_BKID_FLASH_EXPOSURE_EFFECT,
    P326_BKID_FUNCTION_RING,
    P326_BKID_FX6_FLEXIBLE_ISO_EMBED_LUT_FILE,
    P326_BKID_GRID_LINE_DISPLAY,
    P326_BKID_GRID_LINE_TYPE,
    P326_BKID_HDMI_INFO_DISPLAY,
    P326_BKID_LIVE_VIEW_DISPLAY,
    P326_BKID_SELECT_LUT,
    P326_BLOCKED_3DIAL_TOPOLOGY_OR_MYDIAL_OVERRIDE_DRIFT,
    P326_BLOCKED_DIAL_CUSTOMIZE_5ITEM_OR_RESET_DRIFT,
    P326_BLOCKED_FN_12X2_OR_FX6_DIAL_SPOOF,
    P326_BLOCKED_GRID_LINE_OR_HDMI_CLEAN_FEED_LEAK,
    P326_BLOCKED_INVALID_PILLAR58A_SPEC,
    P326_BLOCKED_INVALID_PILLAR58B_SPEC,
    P326_BLOCKED_LIVE_VIEW_RESET_SPLIT_OR_STILL_GATE,
    P326_BLOCKED_LUT_PATH_EMBED_VS_PPLUT_OR_FX6_SPOOF,
    P326_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
    P326_BLOCKED_SAFETY_POLICY_VIOLATION,
    P326_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL,
    P326_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
    P326_COLOR_TONE_G_RESID16,
    P326_CONTROL_WHEEL_BASE_RESID16,
    P326_CUSTOM_KEY_DIAL_SET_F_RESID16_A,
    P326_CUSTOM_KEY_DIAL_SET_F_RESID16_B,
    P326_DIAL_CUSTOMIZE_5_ITEMS,
    P326_DIAL_CUSTOMIZE_G_RESID16,
    P326_DONOR_INSPECT_CI_BUDGET_SECONDS,
    P326_DORMANT_DIAL_LOCK_F_RESID16,
    P326_DORMANT_DIAL_WHEEL_LOCK_BASE_RESID16,
    P326_DORMANT_DIAL_WHEEL_SETUP_F_RESID16,
    P326_DORMANT_REAR_DIAL_L_F_RESID16,
    P326_DORMANT_REAR_DIAL_R_F_RESID16,
    P326_DORMANT_WHEEL_LOCK_F_RESID16,
    P326_EINVAL_ERRNO,
    P326_EMBED_LUT_FILE_DEFAULT,
    P326_EMBED_LUT_FILE_F_RESID16,
    P326_EMBED_LUT_SDHC_LOCK_G_RESID16,
    P326_EMBED_LUT_VALID_PATH,
    P326_EMBED_LUT_WRONG_PATH,
    P326_EOPNOTSUPP_ERRNO,
    P326_EROFS_ERRNO,
    P326_EXPOSURE_EFFECT_DEFAULT,
    P326_EXPOSURE_EFFECT_F_RESID16,
    P326_FAST_CLI_BUDGET_SECONDS,
    P326_FN_ALL_NOT_SET_INVALID_F_RESID16,
    P326_FN_MENU_SETTINGS_G_RESID16,
    P326_FN_NOT_SET_BASE_RESID16,
    P326_FRAME_RATE_LOW_LIMIT_F_RESID16,
    P326_FRONT_DIAL_BASE_RESID16,
    P326_FUNCTION_RING_DEFAULT,
    P326_FUNCTION_RING_F_RESID16,
    P326_FX3_DIAL_CUSTOMIZE_ITEM_COUNT,
    P326_FX3_FN_MENU_MOVIE_SLOTS,
    P326_FX3_FN_MENU_STILL_SLOTS,
    P326_FX3_FW_VERSION,
    P326_FX3_GRID_LINE_TYPE_COUNT,
    P326_FX3_HELPGUIDE_ID,
    P326_FX3_LIVE_VIEW_DISPLAY_SET_ITEM_COUNT,
    P326_FX3_LUT_CFEXPRESS_DIR,
    P326_FX3_LUT_SD_DIR,
    P326_FX3_MODEL_ID,
    P326_FX3_MODEL_NAME,
    P326_FX3_MY_DIAL_BANK_COUNT,
    P326_FX3_PHYSICAL_DIAL_COUNT,
    P326_FX3_PPLUT_SLOT_COUNT,
    P326_FX3_PRODUCT_CODENAME,
    P326_FX3_USER_LUT_SLOT_COUNT,
    P326_FX6_DIAL_CONTROLS,
    P326_FX6_DONOR_FW_VERSION,
    P326_FX6_DONOR_MODEL_NAME,
    P326_FX6_DORMANT_USER_LUT_BUFFER_CAP,
    P326_FX6_LUT_CFEXPRESS_DIR,
    P326_FX6_LUT_SD_DIR,
    P326_FX6_USER_LUT_UI_CAP,
    P326_GRID_LINE_TYPE_DEFAULT,
    P326_HDMI_INFO_DISPLAY_F_RESID16,
    P326_LIVE_VIEW_DISPLAY_DEFAULT,
    P326_LIVE_VIEW_DISPLAY_F_RESID16,
    P326_LIVE_VIEW_DISPLAY_SET_F_RESID16,
    P326_LIVE_VIEW_DISPLAY_SET_PATH,
    P326_LOCK_OPERATION_PARTS_DEFAULT,
    P326_LOCK_OPERATION_PARTS_F_RESID16,
    P326_MANAGE_USER_LUTS_F_RESID16,
    P326_MY_DIAL_CYCLE_123_F_RESID16,
    P326_MY_DIAL_HOLD_F_RESID16,
    P326_MY_DIAL_SETTINGS_F_RESID16,
    P326_MY_DIAL_TOGGLE_F_RESID16,
    P326_PHYSICAL_3_DIALS,
    P326_PICTURE_PROFILE_PPLUT_F_RESID16,
    P326_PILLAR_58A_SCENARIO_IDS,
    P326_PILLAR_58B_SCENARIO_IDS,
    P326_REAR_DIAL_BASE_RESID16,
    P326_SELECT_LUT_DEFAULT,
    P326_SELECT_LUT_F_RESID16,
    P326_SELECT_LUT_SLOG3_FALLBACK_F_RESID16,
    P326_SHOOTING_DISPLAY_G_RESID16,
    P326_SLOT1_FORMAT_HARD_LOCKED,
    P326_SLOT1_VAULT_EROFS_EOPNOTSUPP_ENFORCED,
    P326_STATUS_FAIL_58OF58_AGGREGATOR,
    P326_STATUS_FAIL_PILLAR58_SUITE,
    P326_STATUS_REJECTED_PILLAR_58A,
    P326_STATUS_REJECTED_PILLAR_58B,
    P326_STATUS_VERIFIED_58OF58_AGGREGATOR,
    P326_STATUS_VERIFIED_PILLAR58_SUITE,
    P326_STATUS_VERIFIED_PILLAR_58A,
    P326_STATUS_VERIFIED_PILLAR_58B,
    PASSIVE_TX_BYTES_EMITTED,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHASE326_MASTER_SCHEMA,
    PHASE326_PHASE_NUMBER,
    PHASE326_SCHEMA,
    PHASE326_VERSION,
    PHYSICAL_DEVICE_WRITES,
    PHYSICAL_USB_PACKETS_EMITTED,
    RAW_FIRMWARE_BYTES_LEAKED,
    READ_ONLY_DONOR_ACCESS,
    RPMB_COUNTER_INCREMENTS,
    SPI_NOR_WRITE_AUTHORIZED,
    build_default_safe_dial_customize_mydial_fn12x2_vault_spec,
    build_default_safe_liveview_grid_lut_embed_pplut_vault_spec,
    compute_expected_dial_customize_mydial_fn12x2_state,
    compute_expected_liveview_grid_lut_embed_state,
    evaluate_58pillar_recovery_master,
    evaluate_dial_customize_mydial_fn12x2_vault,
    evaluate_liveview_grid_lut_embed_pplut_vault,
    evaluate_realhw_57pillar_recovery_master,
    evaluate_realhw_58pillar_recovery_master,
    inspect_phase326_donors_readonly,
    run_pillar58_standalone_suite,
    run_pillar58a_dial_customize_mydial_fn12x2_6_scenario_suite,
    run_pillar58b_liveview_lut_embed_pplut_6_scenario_suite,
    verify_58pillar_recovery_suite,
    verify_dial_customize_mydial_fn12x2_liveview_lut_embed_and_vault,
    verify_dial_customize_mydial_fn12x2_liveview_lut_embed_vault,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


def _donor_appfw_present() -> bool:
    if p326.is_forced_clean_room() or os.environ.get(
        p326.P326_ENV_CLEAN_ROOM_TEST, ""
    ).strip().lower() in ("1", "true", "yes"):
        return False
    p = p326._resolve_phase326_donor_path(p326.P326_DONOR_FX3_APPFW_702_RELPATH)
    return p is not None and p.is_file()


def _clean_env(extra: dict[str, str] | None = None) -> dict[str, str]:
    env = os.environ.copy()
    env.pop("FX3_CLEAN_ROOM_TEST", None)
    env.pop("FX3_FX6_FORCE_CLEAN_ROOM", None)
    py_path = os.pathsep.join(
        [
            str(REPO_ROOT / "outputs/fx3-safety"),
            str(REPO_ROOT / "outputs/fx3-recovery-adapter"),
            str(REPO_ROOT / "outputs/fx3-firmware-lab"),
        ]
    )
    env["PYTHONPATH"] = py_path
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    if extra:
        env.update(extra)
    return env


class TestPhase326SafetyDonorsAndExports(unittest.TestCase):
    """Safety redlines, Wave-56 17-donor inspection, work_root=None CI guard & package exports."""

    def test_01_hard_locked_module_safety_invariants(self) -> None:
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        self.assertFalse(ISP_WRITE_AUTHORIZED)
        self.assertFalse(PERSISTENT_WRITE_RELEASE)
        self.assertFalse(ALLOW_BOOT_PARTITION_TARGETING)
        self.assertFalse(ALLOW_DESTRUCTIVE_FASTBOOT)
        self.assertFalse(ALLOW_PERSISTENT_JIRITSU_WRITES)
        self.assertFalse(ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS)
        self.assertFalse(LIVE_USB_IOKIT_TRANSMIT_ENABLED)
        self.assertFalse(HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        self.assertFalse(OVERALL_READY_FOR_HARDWARE_ATTACH)
        self.assertFalse(CROSS_MODEL_FLASH_AUTHORIZED)
        self.assertTrue(READ_ONLY_DONOR_ACCESS)
        self.assertTrue(P326_SLOT1_FORMAT_HARD_LOCKED)
        self.assertTrue(P326_SLOT1_VAULT_EROFS_EOPNOTSUPP_ENFORCED)
        self.assertEqual(OTP_FUSE_TOUCHES, 0)
        self.assertEqual(OTP_FUSE_WRITES, 0)
        self.assertEqual(RPMB_COUNTER_INCREMENTS, 0)
        self.assertEqual(PASSIVE_TX_BYTES_EMITTED, 0)
        self.assertEqual(PHYSICAL_USB_PACKETS_EMITTED, 0)
        self.assertEqual(PHYSICAL_DEVICE_WRITES, 0)
        self.assertEqual(RAW_FIRMWARE_BYTES_LEAKED, 0)

    def test_02_schema_version_and_camera_identity_constants(self) -> None:
        self.assertEqual(PHASE326_PHASE_NUMBER, 326)
        self.assertEqual(PHASE326_VERSION, "1.0.0")
        self.assertEqual(
            PHASE326_SCHEMA,
            "realhw_58pillar_dial_customize_mydial_fn12x2_liveview_lut_embed_vault_verifier_v1",
        )
        self.assertEqual(PHASE326_MASTER_SCHEMA, "realhw_58pillar_recovery_master_v1")
        self.assertEqual(P326_FX3_MODEL_NAME, "ILME-FX3")
        self.assertEqual(P326_FX3_MODEL_ID, 0x91030080)
        self.assertEqual(P326_FX3_PRODUCT_CODENAME, "PRODUCT_MODEL_ALCIN_UUD")
        self.assertEqual(P326_FX3_HELPGUIDE_ID, "ilc/2210")
        self.assertEqual(P326_FX3_FW_VERSION, "7.02")
        self.assertEqual(P326_EINVAL_ERRNO, 22)
        self.assertEqual(P326_EROFS_ERRNO, 30)
        self.assertEqual(P326_EOPNOTSUPP_ERRNO, 95)

    def test_03_empirical_wave56_topology_and_resid16_constants(self) -> None:
        self.assertEqual(P326_FX3_DIAL_CUSTOMIZE_ITEM_COUNT, 5)
        self.assertEqual(len(P326_DIAL_CUSTOMIZE_5_ITEMS), 5)
        self.assertEqual(P326_FX3_PHYSICAL_DIAL_COUNT, 3)
        self.assertEqual(P326_PHYSICAL_3_DIALS, ("Front Dial", "Rear Dial", "Control Wheel"))
        self.assertEqual(P326_FX3_MY_DIAL_BANK_COUNT, 3)
        self.assertEqual(P326_FX3_FN_MENU_STILL_SLOTS, 12)
        self.assertEqual(P326_FX3_FN_MENU_MOVIE_SLOTS, 12)
        self.assertEqual(P326_FX3_LIVE_VIEW_DISPLAY_SET_ITEM_COUNT, 3)
        self.assertEqual(P326_FX3_GRID_LINE_TYPE_COUNT, 3)
        self.assertEqual(P326_FX3_USER_LUT_SLOT_COUNT, 16)
        self.assertEqual(P326_FX3_PPLUT_SLOT_COUNT, 4)
        self.assertEqual(P326_FX6_USER_LUT_UI_CAP, 16)
        self.assertEqual(P326_FX6_DORMANT_USER_LUT_BUFFER_CAP, 50)
        self.assertEqual(P326_DIAL_CUSTOMIZE_G_RESID16, 0x62ED)
        self.assertEqual(P326_CUSTOM_KEY_DIAL_SET_F_RESID16_A, 0x6290)
        self.assertEqual(P326_CUSTOM_KEY_DIAL_SET_F_RESID16_B, 0x73A0)
        self.assertEqual(P326_MY_DIAL_SETTINGS_F_RESID16, 0x6538)
        self.assertEqual(P326_AV_TV_ROTATE_F_RESID16, 0x72E3)
        self.assertEqual(P326_AV_TV_ROTATE_NORMAL_F_RESID16, 0x688F)
        self.assertEqual(P326_AV_TV_ROTATE_REVERSE_F_RESID16, 0x6175)
        self.assertEqual(P326_FUNCTION_RING_F_RESID16, 0x715E)
        self.assertEqual(P326_LOCK_OPERATION_PARTS_F_RESID16, 0x6904)
        self.assertEqual(P326_DORMANT_DIAL_WHEEL_LOCK_BASE_RESID16, 0xE352)
        self.assertEqual(P326_DORMANT_DIAL_LOCK_F_RESID16, 0x737B)
        self.assertEqual(P326_DORMANT_WHEEL_LOCK_F_RESID16, 0x7ACD)
        self.assertEqual(P326_DORMANT_DIAL_WHEEL_SETUP_F_RESID16, 0x6A89)
        self.assertEqual(P326_DORMANT_REAR_DIAL_L_F_RESID16, 0x6A5C)
        self.assertEqual(P326_DORMANT_REAR_DIAL_R_F_RESID16, 0x680D)
        self.assertEqual(P326_FRONT_DIAL_BASE_RESID16, 0xE4DA)
        self.assertEqual(P326_REAR_DIAL_BASE_RESID16, 0xE4DB)
        self.assertEqual(P326_CONTROL_WHEEL_BASE_RESID16, 0xE353)
        self.assertEqual(P326_MY_DIAL_HOLD_F_RESID16, 0x66FE)
        self.assertEqual(P326_MY_DIAL_TOGGLE_F_RESID16, 0x6BC0)
        self.assertEqual(P326_MY_DIAL_CYCLE_123_F_RESID16, 0x7987)
        self.assertEqual(P326_FN_MENU_SETTINGS_G_RESID16, 0x614B)
        self.assertEqual(P326_FN_NOT_SET_BASE_RESID16, 0xE0AC)
        self.assertEqual(P326_FN_ALL_NOT_SET_INVALID_F_RESID16, 0x6220)
        self.assertEqual(P326_SHOOTING_DISPLAY_G_RESID16, 0x615E)
        self.assertEqual(P326_LIVE_VIEW_DISPLAY_SET_F_RESID16, 0x6429)
        self.assertEqual(P326_LIVE_VIEW_DISPLAY_F_RESID16, 0x7227)
        self.assertEqual(P326_EXPOSURE_EFFECT_F_RESID16, 0x6552)
        self.assertEqual(P326_FRAME_RATE_LOW_LIMIT_F_RESID16, 0x700E)
        self.assertEqual(P326_HDMI_INFO_DISPLAY_F_RESID16, 0x6E7C)
        self.assertEqual(P326_COLOR_TONE_G_RESID16, 0x61FA)
        self.assertEqual(P326_MANAGE_USER_LUTS_F_RESID16, 0x71AF)
        self.assertEqual(P326_SELECT_LUT_F_RESID16, 0x643E)
        self.assertEqual(P326_SELECT_LUT_SLOG3_FALLBACK_F_RESID16, 0x77CA)
        self.assertEqual(P326_EMBED_LUT_FILE_F_RESID16, 0x680F)
        self.assertEqual(P326_EMBED_LUT_SDHC_LOCK_G_RESID16, 0x61A0)
        self.assertEqual(P326_PICTURE_PROFILE_PPLUT_F_RESID16, 0x6095)

    def test_04_empirical_wave56_bkid_and_lut_path_constants(self) -> None:
        self.assertEqual(P326_BKID_AV_TV_ROTATE, "BKID_APP_setting_av_tv_rotate")
        self.assertEqual(P326_BKID_FUNCTION_RING, "BKID_APP_setting_function_ring")
        self.assertEqual(P326_BKID_DEVICE_LOCK, "BKID_APP_setting_device_lock")
        self.assertEqual(P326_BKID_DORMANT_DIAL_SETUP, "BKID_APP_setting_dial_setup")
        self.assertEqual(P326_BKID_LIVE_VIEW_DISPLAY, "BKID_APP_setting_live_view_display")
        self.assertEqual(P326_BKID_FLASH_EXPOSURE_EFFECT, "BKID_APP_setting_flash_exposure_effect")
        self.assertEqual(P326_BKID_GRID_LINE_DISPLAY, "BKID_APP_setting_grid_line_display")
        self.assertEqual(P326_BKID_GRID_LINE_TYPE, "BKID_APP_setting_grid_line_type")
        self.assertEqual(P326_BKID_HDMI_INFO_DISPLAY, "BKID_APP_setting_hdmi_info_display")
        self.assertEqual(P326_BKID_SELECT_LUT, "BKID_APP_setting_select_lut")
        self.assertEqual(P326_BKID_EMBED_LUT_FILE, "BKID_APP_setting_embed_lut_file")
        self.assertEqual(
            P326_BKID_FX6_FLEXIBLE_ISO_EMBED_LUT_FILE,
            "BKID_APP_SETTING_FLEXIBLE_ISO_EMBED_LUT_FILE",
        )
        self.assertEqual(P326_FX3_LUT_SD_DIR, "/Private/Sony/PRO/LUT")
        self.assertEqual(P326_FX3_LUT_CFEXPRESS_DIR, "/Sony/PRO/LUT")
        self.assertEqual(P326_FX6_LUT_SD_DIR, "/PRIVATE/SONY/PRO/LUT/")
        self.assertEqual(P326_FX6_LUT_CFEXPRESS_DIR, "/SONY/PRO/LUT/")
        self.assertEqual(P326_SELECT_LUT_DEFAULT, "s709")
        self.assertEqual(P326_EMBED_LUT_FILE_DEFAULT, "On")

    def test_05_init_exports_and_non_overlapping_master_58_registry(self) -> None:
        self.assertEqual(MASTER_58_PILLAR_COUNT, 58)
        self.assertEqual(len(MASTER_58_PILLAR_SPECS), 58)
        self.assertEqual(len(MASTER_58_PILLAR_IDS), 58)
        self.assertEqual(len(set(MASTER_58_PILLAR_IDS)), 58)
        self.assertEqual(
            MASTER_58_PILLAR_IDS[-1],
            "pillar_58_dial_customize_mydial_fn12x2_liveview_lut_embed_vault",
        )
        self.assertIn("evaluate_realhw_58pillar_recovery_master", fx3_recovery.__all__)
        self.assertIn("evaluate_58pillar_recovery_master", fx3_recovery.__all__)
        self.assertIn("verify_58pillar_recovery_suite", fx3_recovery.__all__)
        self.assertIn("run_pillar58_standalone_suite", fx3_recovery.__all__)
        self.assertIn("MASTER_58_PILLAR_IDS", fx3_recovery.__all__)

    def test_06_safety_invariant_tamper_rejected_in_58a_and_58b(self) -> None:
        with mock.patch.object(p326, "PERSISTENT_EMMC_WRITES_AUTHORIZED", True):
            rep_a = evaluate_dial_customize_mydial_fn12x2_vault(
                build_default_safe_dial_customize_mydial_fn12x2_vault_spec()
            )
            rep_b = evaluate_liveview_grid_lut_embed_pplut_vault(
                build_default_safe_liveview_grid_lut_embed_pplut_vault_spec()
            )
        self.assertFalse(rep_a.passed)
        self.assertEqual(rep_a.block_code, P326_BLOCKED_SAFETY_POLICY_VIOLATION)
        self.assertFalse(rep_b.passed)
        self.assertEqual(rep_b.block_code, P326_BLOCKED_SAFETY_POLICY_VIOLATION)

    def test_07_invalid_58a_and_58b_spec_parameters_fail_closed(self) -> None:
        bad_a = evaluate_dial_customize_mydial_fn12x2_vault(
            build_default_safe_dial_customize_mydial_fn12x2_vault_spec(
                camera_model="ILCE-7M4",
                requested_vault_slot=9,
            )
        )
        bad_b = evaluate_liveview_grid_lut_embed_pplut_vault(
            build_default_safe_liveview_grid_lut_embed_pplut_vault_spec(
                shooting_domain="TimeLapse",
                requested_vault_slot=9,
            )
        )
        self.assertFalse(bad_a.passed)
        self.assertEqual(bad_a.block_code, P326_BLOCKED_INVALID_PILLAR58A_SPEC)
        self.assertFalse(bad_b.passed)
        self.assertEqual(bad_b.block_code, P326_BLOCKED_INVALID_PILLAR58B_SPEC)

    def test_08_donor_snapshot_bounded_readonly_and_17_artifacts(self) -> None:
        snap = inspect_phase326_donors_readonly()
        self.assertTrue(snap.all_donors_present)
        self.assertEqual(snap.donor_files_inspected, 17)
        self.assertEqual(len(snap.artifacts), 17)
        self.assertTrue(snap.under_0_20s_budget)
        self.assertLess(snap.elapsed_seconds, P326_DONOR_INSPECT_CI_BUDGET_SECONDS)
        self.assertEqual(snap.raw_firmware_bytes_leaked, 0)

    def test_09_donor_pinned_hashes_when_local_donors_present(self) -> None:
        snap = inspect_phase326_donors_readonly()
        if _donor_appfw_present():
            self.assertEqual(snap.verification_mode, "LOCAL_DONOR_O_RDONLY")
            self.assertTrue(all(a.matches_pinned for a in snap.artifacts))
            appfw = next(a for a in snap.artifacts if a.artifact_id == "fx3_appfw_702_so")
            self.assertEqual(appfw.header_bytes_read, 4096)
            self.assertEqual(appfw.digest_kind, "HEADER4K_SHA256")
        else:
            self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_10_donor_clean_room_fallback_under_env_and_flag(self) -> None:
        snap_flag = inspect_phase326_donors_readonly(force_clean_room=True)
        self.assertEqual(snap_flag.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(snap_flag.all_donors_present)
        self.assertEqual(snap_flag.raw_firmware_bytes_leaked, 0)
        with mock.patch.dict(os.environ, {"FX3_CLEAN_ROOM_TEST": "1"}):
            snap_env = inspect_phase326_donors_readonly()
        self.assertEqual(snap_env.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(snap_env.all_donors_present)
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            snap_fcr = inspect_phase326_donors_readonly()
        self.assertEqual(snap_fcr.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(snap_fcr.all_donors_present)

    def test_11_work_root_none_and_empty_iter_work_roots_guard_no_typeerror(self) -> None:
        # Must not raise TypeError: unsupported operand type(s) for /: 'NoneType' and 'str'
        resolved = p326._resolve_phase326_donor_path(
            p326.P326_DONOR_FX3_APPFW_702_RELPATH,
            work_roots=(None,),
        )
        self.assertIsNone(resolved)
        with mock.patch.object(p326, "_iter_work_roots", return_value=()):
            snap_empty = inspect_phase326_donors_readonly()
        self.assertEqual(snap_empty.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(snap_empty.all_donors_present)
        self.assertEqual(snap_empty.donor_files_inspected, 17)
        with mock.patch.object(p326, "_iter_work_roots", return_value=(None,)):
            snap_none = inspect_phase326_donors_readonly()
        self.assertEqual(snap_none.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(snap_none.all_donors_present)
        with mock.patch.object(p326, "_iter_work_roots", return_value=(None,)):
            suite_none = run_pillar58_standalone_suite()
        self.assertTrue(suite_none.all_passed)
        self.assertEqual(suite_none.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_12_donor_open_uses_strict_o_rdonly_nofollow_nonblock(self) -> None:
        if not _donor_appfw_present():
            self.skipTest("local donors absent in clean-room CI")
        seen_flags: list[int] = []
        real_open = os.open

        def spy_open(path: str, flags: int, *args: object, **kwargs: object) -> int:
            seen_flags.append(flags)
            return real_open(path, flags, *args, **kwargs)  # type: ignore[arg-type]

        with mock.patch("fx3_recovery.realhw_58pillar_dial_customize_mydial_fn12x2_liveview_lut_embed_vault_verifier.os.open", side_effect=spy_open):
            snap = inspect_phase326_donors_readonly()
        self.assertTrue(snap.all_donors_present)
        self.assertEqual(len(seen_flags), 17)
        expected_flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
        for fl in seen_flags:
            self.assertEqual(fl & os.O_ACCMODE, os.O_RDONLY)
            self.assertEqual(fl, expected_flags)

    def test_13_donor_checks_detect_bad_elf_uxc_bk4_headers(self) -> None:
        self.assertFalse(p326._check_elf64_aarch64(b"NOTELF" + b"\x00" * 64, "X")[0])
        self.assertFalse(p326._check_uxc7_pack(b"uxc\x06" + b"\x00" * 32, "X")[0])
        self.assertFalse(p326._check_bk4_backup(b"\x00" * 32, "X")[0])


class TestPillar58ADialCustomizeMyDialFn12x2(unittest.TestCase):
    """Pillar 58A: [Dial Customize] 5 items, 3-dial topology, My Dial 1..3, Fn 12+12, FX6 & Vault."""

    def test_14_default_safe_spec_58a_passes(self) -> None:
        rep = evaluate_dial_customize_mydial_fn12x2_vault(
            build_default_safe_dial_customize_mydial_fn12x2_vault_spec()
        )
        self.assertTrue(rep.passed)
        self.assertEqual(rep.status, P326_STATUS_VERIFIED_PILLAR_58A)
        self.assertIsNone(rep.block_code)
        self.assertTrue(rep.dial_customize_5item_init_only_and_lock_verified)
        self.assertTrue(rep.three_dial_topology_and_mydial_override_verified)
        self.assertTrue(rep.fn_12x2_split_and_fx6_dial_boundary_verified)
        self.assertTrue(rep.slot1_vault_firewall_and_h0_h3_verified)

    def test_15_camera_settings_reset_does_not_reset_all_5_dial_customize_items(self) -> None:
        spec = build_default_safe_dial_customize_mydial_fn12x2_vault_spec(
            av_tv_rotate="Reverse",
            function_ring_lens="APS-C/Super 35 mm / Full Frame",
            lock_operation_parts="Multi-Selector Only",
            reset_action="Camera Settings Reset",
            post_av_tv_rotate="Reverse",
            post_function_ring_lens="APS-C/Super 35 mm / Full Frame",
            post_lock_operation_parts="Multi-Selector Only",
        )
        rep = evaluate_dial_customize_mydial_fn12x2_vault(spec)
        self.assertTrue(rep.passed)

    def test_16_camera_settings_reset_wiping_av_tv_rotate_rejected(self) -> None:
        spec = build_default_safe_dial_customize_mydial_fn12x2_vault_spec(
            av_tv_rotate="Reverse",
            reset_action="Camera Settings Reset",
            post_av_tv_rotate="Normal",
        )
        rep = evaluate_dial_customize_mydial_fn12x2_vault(spec)
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P326_BLOCKED_DIAL_CUSTOMIZE_5ITEM_OR_RESET_DRIFT)

    def test_17_camera_settings_reset_wiping_function_ring_rejected(self) -> None:
        spec = build_default_safe_dial_customize_mydial_fn12x2_vault_spec(
            function_ring_lens="APS-C/Super 35 mm / Full Frame",
            reset_action="Camera Settings Reset",
            post_function_ring_lens="Power Focus",
        )
        rep = evaluate_dial_customize_mydial_fn12x2_vault(spec)
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P326_BLOCKED_DIAL_CUSTOMIZE_5ITEM_OR_RESET_DRIFT)

    def test_18_camera_settings_reset_wiping_lock_operation_parts_rejected(self) -> None:
        spec = build_default_safe_dial_customize_mydial_fn12x2_vault_spec(
            lock_operation_parts="All",
            reset_action="Camera Settings Reset",
            post_lock_operation_parts="Off",
        )
        rep = evaluate_dial_customize_mydial_fn12x2_vault(spec)
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P326_BLOCKED_DIAL_CUSTOMIZE_5ITEM_OR_RESET_DRIFT)

    def test_19_initialize_resets_all_dial_customize_items_to_defaults(self) -> None:
        spec = build_default_safe_dial_customize_mydial_fn12x2_vault_spec(
            av_tv_rotate="Reverse",
            function_ring_lens="APS-C/Super 35 mm / Full Frame",
            lock_operation_parts="All",
            reset_action="Initialize",
            post_av_tv_rotate=P326_AV_TV_ROTATE_DEFAULT,
            post_function_ring_lens=P326_FUNCTION_RING_DEFAULT,
            post_lock_operation_parts=P326_LOCK_OPERATION_PARTS_DEFAULT,
        )
        rep = evaluate_dial_customize_mydial_fn12x2_vault(spec)
        self.assertTrue(rep.passed)

    def test_20_dial_customize_item_list_replacing_custom_key_with_dial_setup_rejected(self) -> None:
        spec = build_default_safe_dial_customize_mydial_fn12x2_vault_spec(
            dial_customize_items=(
                "Dial Setup",
                "My Dial Settings",
                "Av/Tv Rotate",
                "Function Ring(Lens)",
                "Dial / Wheel Lock",
            ),
        )
        rep = evaluate_dial_customize_mydial_fn12x2_vault(spec)
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P326_BLOCKED_DIAL_CUSTOMIZE_5ITEM_OR_RESET_DRIFT)

    def test_21_function_ring_invalid_enum_rejected_with_eopnotsupp95(self) -> None:
        spec = build_default_safe_dial_customize_mydial_fn12x2_vault_spec(
            function_ring_lens="INVALID",
            post_function_ring_lens="INVALID",
            reported_dormant_dial_errno=None,
        )
        rep = evaluate_dial_customize_mydial_fn12x2_vault(spec)
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P326_BLOCKED_DIAL_CUSTOMIZE_5ITEM_OR_RESET_DRIFT)

    def test_22_lock_operation_parts_all_four_modes_and_shortcuts(self) -> None:
        for mode in ("Off", "Multi-Selector Only", "Dial + Wheel", "All"):
            spec = build_default_safe_dial_customize_mydial_fn12x2_vault_spec(
                lock_operation_parts=mode,
                post_lock_operation_parts=mode,
                my_dial_recall_mode="None",
                reported_active_my_dial_bank=None,
                reported_dials_temporarily_unlocked=False,
            )
            rep = evaluate_dial_customize_mydial_fn12x2_vault(spec)
            self.assertTrue(rep.passed, mode)
        missing_5s = evaluate_dial_customize_mydial_fn12x2_vault(
            build_default_safe_dial_customize_mydial_fn12x2_vault_spec(
                menu_plus_fn_5s_full_lock_supported=False,
            )
        )
        self.assertFalse(missing_5s.passed)

    def test_23_dormant_rear_dial_lr_and_dial_setup_rejected(self) -> None:
        for dormant in ("Rear Dial L", "Rear Dial R", "Dial Setup", "Dial/Wheel Setup", "Dial / Wheel Lock"):
            bad = evaluate_dial_customize_mydial_fn12x2_vault(
                build_default_safe_dial_customize_mydial_fn12x2_vault_spec(
                    requested_dormant_dial_symbols=(dormant,),
                    reported_dormant_dial_errno=None,
                )
            )
            self.assertFalse(bad.passed, dormant)
            self.assertEqual(bad.block_code, P326_BLOCKED_DIAL_CUSTOMIZE_5ITEM_OR_RESET_DRIFT)

    def test_24_physical_dials_including_rear_dial_lr_rejected(self) -> None:
        spec = build_default_safe_dial_customize_mydial_fn12x2_vault_spec(
            physical_dials_present=("Front Dial", "Rear Dial L", "Rear Dial R", "Control Wheel"),
            reported_dormant_dial_errno=P326_EOPNOTSUPP_ERRNO,
        )
        rep = evaluate_dial_customize_mydial_fn12x2_vault(spec)
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P326_BLOCKED_3DIAL_TOPOLOGY_OR_MYDIAL_OVERRIDE_DRIFT)

    def test_25_mydial_123_cycle_skips_empty_bank2_to_bank3(self) -> None:
        st = compute_expected_dial_customize_mydial_fn12x2_state(
            camera_model=P326_FX3_MODEL_NAME,
            shooting_domain="Movie",
            dial_customize_items=P326_DIAL_CUSTOMIZE_5_ITEMS,
            av_tv_rotate="Normal",
            function_ring_lens="Power Focus",
            lock_operation_parts="Dial + Wheel",
            physical_dials_present=P326_PHYSICAL_3_DIALS,
            requested_dormant_dial_symbols=(),
            my_dial_1_configured=True,
            my_dial_2_configured=False,
            my_dial_3_configured=True,
            my_dial_recall_mode="1->2->3",
            my_dial_cycle_step=2,
            fn_still_slot_count=12,
            fn_movie_slot_count=12,
            fn_all_not_set_pressed=False,
            reset_action="None",
        )
        self.assertEqual(st["active_my_dial_bank"], 3)
        self.assertTrue(st["dials_temporarily_unlocked_by_mydial"])

    def test_26_mydial_hold_and_toggle_override_lock_operation_parts(self) -> None:
        for recall in ("Hold", "Toggle"):
            spec = build_default_safe_dial_customize_mydial_fn12x2_vault_spec(
                lock_operation_parts="All",
                post_lock_operation_parts="All",
                my_dial_recall_mode=recall,
                my_dial_cycle_step=1,
                reported_active_my_dial_bank=1,
                reported_dials_temporarily_unlocked=True,
            )
            rep = evaluate_dial_customize_mydial_fn12x2_vault(spec)
            self.assertTrue(rep.passed, recall)
        # Failing to unlock when Dial + Wheel is locked must be rejected
        bad = evaluate_dial_customize_mydial_fn12x2_vault(
            build_default_safe_dial_customize_mydial_fn12x2_vault_spec(
                lock_operation_parts="Dial + Wheel",
                post_lock_operation_parts="Dial + Wheel",
                my_dial_recall_mode="Hold",
                my_dial_cycle_step=1,
                reported_active_my_dial_bank=1,
                reported_dials_temporarily_unlocked=False,
            )
        )
        self.assertFalse(bad.passed)
        self.assertEqual(bad.block_code, P326_BLOCKED_3DIAL_TOPOLOGY_OR_MYDIAL_OVERRIDE_DRIFT)

    def test_27_mydial_all_empty_banks_yield_none(self) -> None:
        spec = build_default_safe_dial_customize_mydial_fn12x2_vault_spec(
            my_dial_1_configured=False,
            my_dial_2_configured=False,
            my_dial_3_configured=False,
            my_dial_recall_mode="1->2->3",
            reported_active_my_dial_bank=None,
            reported_dials_temporarily_unlocked=False,
        )
        rep = evaluate_dial_customize_mydial_fn12x2_vault(spec)
        self.assertTrue(rep.passed)

    def test_28_fn_menu_12x2_all_not_set_triggers_invalid_prompt(self) -> None:
        ok = evaluate_dial_customize_mydial_fn12x2_vault(
            build_default_safe_dial_customize_mydial_fn12x2_vault_spec(
                fn_still_slot_count=12,
                fn_movie_slot_count=12,
                fn_all_not_set_pressed=True,
                reported_fn_invalid_prompt_errno=P326_EINVAL_ERRNO,
            )
        )
        self.assertTrue(ok.passed)
        bad_counts = evaluate_dial_customize_mydial_fn12x2_vault(
            build_default_safe_dial_customize_mydial_fn12x2_vault_spec(
                fn_still_slot_count=11,
                fn_movie_slot_count=13,
            )
        )
        self.assertFalse(bad_counts.passed)
        self.assertEqual(bad_counts.block_code, P326_BLOCKED_FN_12X2_OR_FX6_DIAL_SPOOF)

    def test_29_fx6_clean_control_boundary_passes_and_spoof_rejected(self) -> None:
        fx6_ok = evaluate_dial_customize_mydial_fn12x2_vault(
            build_default_safe_dial_customize_mydial_fn12x2_vault_spec(
                camera_model=P326_FX6_DONOR_MODEL_NAME,
                fw_version=P326_FX6_DONOR_FW_VERSION,
                shooting_domain="Movie",
                fx6_dial_controls=P326_FX6_DIAL_CONTROLS,
                fx6_exposes_av_tv_mydial_or_fn_menu=False,
                fx6_uses_physical_hold_switch=True,
            )
        )
        self.assertTrue(fx6_ok.passed)
        fx6_bad = evaluate_dial_customize_mydial_fn12x2_vault(
            build_default_safe_dial_customize_mydial_fn12x2_vault_spec(
                camera_model=P326_FX6_DONOR_MODEL_NAME,
                fw_version=P326_FX6_DONOR_FW_VERSION,
                fx6_exposes_av_tv_mydial_or_fn_menu=True,
            )
        )
        self.assertFalse(fx6_bad.passed)
        self.assertEqual(fx6_bad.block_code, P326_BLOCKED_FN_12X2_OR_FX6_DIAL_SPOOF)

    def test_30_pillar58a_slot1_vault_overlay_and_h0_h3_guards(self) -> None:
        bad_vault = evaluate_dial_customize_mydial_fn12x2_vault(
            build_default_safe_dial_customize_mydial_fn12x2_vault_spec(
                requested_vault_slot=1,
                requested_vault_action="FORMAT_QUICK",
            )
        )
        self.assertFalse(bad_vault.passed)
        self.assertEqual(bad_vault.block_code, P326_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL)

        bad_overlay = evaluate_dial_customize_mydial_fn12x2_vault(
            build_default_safe_dial_customize_mydial_fn12x2_vault_spec(overlay_dir="/setting/58a")
        )
        self.assertFalse(bad_overlay.passed)
        self.assertEqual(bad_overlay.block_code, P326_BLOCKED_PERSISTENT_OVERLAY_ESCAPE)

        bad_h3 = evaluate_dial_customize_mydial_fn12x2_vault(
            build_default_safe_dial_customize_mydial_fn12x2_vault_spec(backup_bin_h3_sha256="f" * 64)
        )
        self.assertFalse(bad_h3.passed)
        self.assertEqual(bad_h3.block_code, P326_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT)

    def test_31_pillar58a_6_scenario_suite_passes_all_6(self) -> None:
        res = run_pillar58a_dial_customize_mydial_fn12x2_6_scenario_suite()
        self.assertTrue(res.passed)
        self.assertEqual(res.status, P326_STATUS_VERIFIED_PILLAR_58A)
        self.assertEqual(res.scenarios_passed, 6)
        self.assertEqual(res.scenarios_total, 6)
        self.assertEqual(tuple(s.scenario_id for s in res.scenarios), P326_PILLAR_58A_SCENARIO_IDS)
        self.assertEqual(sum(1 for s in res.scenarios if s.expected_allowed), 2)
        self.assertEqual(sum(1 for s in res.scenarios if not s.expected_allowed), 4)


class TestPillar58BLiveViewGridLutEmbedPplutVault(unittest.TestCase):
    """Pillar 58B: Live View Reset Split, Grid HDMI Isolation, Embed LUT vs PPLUT1..4 & Slot-1 Vault."""

    def test_32_default_safe_spec_58b_passes(self) -> None:
        rep = evaluate_liveview_grid_lut_embed_pplut_vault(
            build_default_safe_liveview_grid_lut_embed_pplut_vault_spec()
        )
        self.assertTrue(rep.passed)
        self.assertEqual(rep.status, P326_STATUS_VERIFIED_PILLAR_58B)
        self.assertIsNone(rep.block_code)
        self.assertTrue(rep.live_view_3item_reset_split_and_bright_mon_verified)
        self.assertTrue(rep.grid_line_and_hdmi_clean_feed_isolation_verified)
        self.assertTrue(rep.lut_paths_embed_metadata_vs_pplut_bake_and_fx6_verified)
        self.assertTrue(rep.slot1_vault_firewall_and_h0_h3_verified)

    def test_33_live_view_display_set_still_only_gate_rejects_movie_and_sq(self) -> None:
        for dom in ("Movie", "S&Q"):
            ok_gated = evaluate_liveview_grid_lut_embed_pplut_vault(
                build_default_safe_liveview_grid_lut_embed_pplut_vault_spec(
                    shooting_domain=dom,
                    reported_live_view_gate_errno=P326_EOPNOTSUPP_ERRNO,
                )
            )
            self.assertTrue(ok_gated.passed, dom)
            bad_ungated = evaluate_liveview_grid_lut_embed_pplut_vault(
                build_default_safe_liveview_grid_lut_embed_pplut_vault_spec(
                    shooting_domain=dom,
                    reported_live_view_gate_errno=None,
                )
            )
            self.assertFalse(bad_ungated.passed, dom)
            self.assertEqual(bad_ungated.block_code, P326_BLOCKED_LIVE_VIEW_RESET_SPLIT_OR_STILL_GATE)

    def test_34_live_view_3item_asymmetric_camera_settings_reset_split(self) -> None:
        # Frame Rate Low Limit is ONLY resettable item among the 3!
        ok_split = evaluate_liveview_grid_lut_embed_pplut_vault(
            build_default_safe_liveview_grid_lut_embed_pplut_vault_spec(
                shooting_domain="Still",
                live_view_display="Setting Effect OFF",
                reported_live_view_display="Setting Effect OFF",
                exposure_effect="Exposure Setting Only",
                frame_rate_low_limit="On",
                reset_action="Camera Settings Reset",
                post_live_view_display="Setting Effect OFF",
                post_exposure_effect="Exposure Setting Only",
                post_frame_rate_low_limit="Off",
                post_pplut_reset=True,
            )
        )
        self.assertTrue(ok_split.passed)

        bad_wipe = evaluate_liveview_grid_lut_embed_pplut_vault(
            build_default_safe_liveview_grid_lut_embed_pplut_vault_spec(
                shooting_domain="Still",
                live_view_display="Setting Effect OFF",
                reported_live_view_display="Setting Effect OFF",
                exposure_effect="Exposure Setting Only",
                frame_rate_low_limit="On",
                reset_action="Camera Settings Reset",
                post_live_view_display="Setting Effect ON",
                post_exposure_effect="Exposure Set. & flash",
                post_frame_rate_low_limit="On",
                post_pplut_reset=True,
            )
        )
        self.assertFalse(bad_wipe.passed)
        self.assertEqual(bad_wipe.block_code, P326_BLOCKED_LIVE_VIEW_RESET_SPLIT_OR_STILL_GATE)

    def test_35_bright_monitoring_forces_live_view_setting_effect_off(self) -> None:
        ok = evaluate_liveview_grid_lut_embed_pplut_vault(
            build_default_safe_liveview_grid_lut_embed_pplut_vault_spec(
                live_view_display="Setting Effect ON",
                bright_monitoring_active=True,
                reported_live_view_display="Setting Effect OFF",
                post_live_view_display="Setting Effect OFF",
            )
        )
        self.assertTrue(ok.passed)
        bad = evaluate_liveview_grid_lut_embed_pplut_vault(
            build_default_safe_liveview_grid_lut_embed_pplut_vault_spec(
                live_view_display="Setting Effect ON",
                bright_monitoring_active=True,
                reported_live_view_display="Setting Effect ON",
                post_live_view_display="Setting Effect ON",
            )
        )
        self.assertFalse(bad.passed)
        self.assertEqual(bad.block_code, P326_BLOCKED_LIVE_VIEW_RESET_SPLIT_OR_STILL_GATE)

    def test_36_grid_line_types_init_only_and_hdmi_clean_feed_isolation(self) -> None:
        for gtype in ("Rule of 3rds Grid", "Square Grid", "Diag. + Square Grid"):
            spec = build_default_safe_liveview_grid_lut_embed_pplut_vault_spec(
                grid_line_display="On",
                grid_line_type=gtype,
                reset_action="Camera Settings Reset",
                post_grid_line_display="On",
                post_grid_line_type=gtype,
                post_pplut_reset=True,
                hdmi_info_display="Off",
                raw_output_or_hdmi_only=True,
                reported_clean_hdmi_osd_isolated_to_lcd=True,
                reported_hdmi_clean_feed_grid_leaked=False,
            )
            self.assertTrue(evaluate_liveview_grid_lut_embed_pplut_vault(spec).passed, gtype)

        leak = evaluate_liveview_grid_lut_embed_pplut_vault(
            build_default_safe_liveview_grid_lut_embed_pplut_vault_spec(
                grid_line_display="On",
                hdmi_info_display="Off",
                reported_clean_hdmi_osd_isolated_to_lcd=True,
                reported_hdmi_clean_feed_grid_leaked=True,
            )
        )
        self.assertFalse(leak.passed)
        self.assertEqual(leak.block_code, P326_BLOCKED_GRID_LINE_OR_HDMI_CLEAN_FEED_LEAK)

    def test_37_fx6_dormant_custom_png_grid_spoof_rejected(self) -> None:
        bad = evaluate_liveview_grid_lut_embed_pplut_vault(
            build_default_safe_liveview_grid_lut_embed_pplut_vault_spec(
                fx6_uses_marker_guide_frame=False,
                fx6_exposes_dormant_custom_png_grid=True,
            )
        )
        self.assertFalse(bad.passed)
        self.assertEqual(bad.block_code, P326_BLOCKED_GRID_LINE_OR_HDMI_CLEAN_FEED_LEAK)

    def test_38_lut_card_dirs_17_and_33pt_cube_and_unset_slot_fallback(self) -> None:
        for media, cdir, pts in (
            ("SDXC", "/Private/Sony/PRO/LUT", 17),
            ("CFexpress Type A", "/Sony/PRO/LUT", 33),
        ):
            ok = evaluate_liveview_grid_lut_embed_pplut_vault(
                build_default_safe_liveview_grid_lut_embed_pplut_vault_spec(
                    card_media_type=media,
                    lut_card_dir=cdir,
                    lut_cube_points=pts,
                )
            )
            self.assertTrue(ok.passed, media)

        # Unpopulated User16 falls back to S-Log3 monitoring
        fallback_ok = evaluate_liveview_grid_lut_embed_pplut_vault(
            build_default_safe_liveview_grid_lut_embed_pplut_vault_spec(
                select_lut="User16",
                user_lut_slot_populated=False,
                reported_monitored_lut="S-Log3",
                post_select_lut="User16",
            )
        )
        self.assertTrue(fallback_ok.passed)

        bad_pts = evaluate_liveview_grid_lut_embed_pplut_vault(
            build_default_safe_liveview_grid_lut_embed_pplut_vault_spec(lut_cube_points=65)
        )
        self.assertFalse(bad_pts.passed)
        self.assertEqual(bad_pts.block_code, P326_BLOCKED_LUT_PATH_EMBED_VS_PPLUT_OR_FX6_SPOOF)

    def test_39_embed_lut_file_path_sdhc_lock_and_metadata_embed_no_sidecar(self) -> None:
        wrong_path = evaluate_liveview_grid_lut_embed_pplut_vault(
            build_default_safe_liveview_grid_lut_embed_pplut_vault_spec(
                embed_lut_menu_path=P326_EMBED_LUT_WRONG_PATH,
            )
        )
        self.assertFalse(wrong_path.passed)
        self.assertEqual(wrong_path.block_code, P326_BLOCKED_LUT_PATH_EMBED_VS_PPLUT_OR_FX6_SPOOF)

        # SDHC locks Embed LUT File to Off
        sdhc_locked_ok = evaluate_liveview_grid_lut_embed_pplut_vault(
            build_default_safe_liveview_grid_lut_embed_pplut_vault_spec(
                card_media_type="SDHC",
                lut_card_dir=P326_FX3_LUT_SD_DIR,
                embed_lut_file="On",
                reported_embed_lut_file="Off",
                post_embed_lut_file="On",
            )
        )
        self.assertTrue(sdhc_locked_ok.passed)

        sdhc_bypass_bad = evaluate_liveview_grid_lut_embed_pplut_vault(
            build_default_safe_liveview_grid_lut_embed_pplut_vault_spec(
                card_media_type="SDHC",
                lut_card_dir=P326_FX3_LUT_SD_DIR,
                embed_lut_file="On",
                reported_embed_lut_file="On",
            )
        )
        self.assertFalse(sdhc_bypass_bad.passed)
        self.assertEqual(sdhc_bypass_bad.block_code, P326_BLOCKED_LUT_PATH_EMBED_VS_PPLUT_OR_FX6_SPOOF)

        # Sidecar generation or baked pixels in embed mode rejected
        sidecar_bad = evaluate_liveview_grid_lut_embed_pplut_vault(
            build_default_safe_liveview_grid_lut_embed_pplut_vault_spec(
                lut_workflow_mode="LOG_SHOOTING_EMBED",
                reported_external_cube_sidecar_generated=True,
            )
        )
        self.assertFalse(sidecar_bad.passed)

    def test_40_select_lut_embed_lut_and_pplut1_4_reset_and_bake_semantics(self) -> None:
        ok_reset = evaluate_liveview_grid_lut_embed_pplut_vault(
            build_default_safe_liveview_grid_lut_embed_pplut_vault_spec(
                select_lut="709(800%)",
                reported_monitored_lut="709(800%)",
                embed_lut_file="Off",
                reported_embed_lut_file="Off",
                lut_workflow_mode="PPLUT_BAKE",
                pplut_slot="PPLUT3",
                reported_slog3_pixels_preserved=False,
                reset_action="Camera Settings Reset",
                post_select_lut="s709",
                post_embed_lut_file="On",
                post_pplut_reset=True,
            )
        )
        self.assertTrue(ok_reset.passed)

        bad_pplut_no_reset = evaluate_liveview_grid_lut_embed_pplut_vault(
            build_default_safe_liveview_grid_lut_embed_pplut_vault_spec(
                lut_workflow_mode="PPLUT_BAKE",
                pplut_slot="PPLUT1",
                reported_slog3_pixels_preserved=False,
                reset_action="Camera Settings Reset",
                post_pplut_reset=False,
            )
        )
        self.assertFalse(bad_pplut_no_reset.passed)
        self.assertEqual(
            bad_pplut_no_reset.block_code, P326_BLOCKED_LUT_PATH_EMBED_VS_PPLUT_OR_FX6_SPOOF
        )

    def test_41_slot1_readonly_import_allowed_while_any_write_or_folder_create_erofs30(self) -> None:
        ro_import = evaluate_liveview_grid_lut_embed_pplut_vault(
            build_default_safe_liveview_grid_lut_embed_pplut_vault_spec(
                requested_vault_slot=1,
                requested_vault_action="IMPORT_USER_LUT_CUBE",
                make_cube_folder_on_slot1=False,
                reported_vault_action_allowed=True,
                vault_firewall_errno=None,
                slot1_data_sector_writes=0,
            )
        )
        self.assertTrue(ro_import.passed)

        for action in (
            "EMBED_LUT_RECORD",
            "PPLUT_RECORD",
            "MAKE_CUBE_FOLDER",
            "EXPORT_OR_WRITE_LUT",
            "DELETE_ALL_CARD",
            "FORMAT_QUICK",
            "FORMAT_FULL",
        ):
            blocked_ok = evaluate_liveview_grid_lut_embed_pplut_vault(
                build_default_safe_liveview_grid_lut_embed_pplut_vault_spec(
                    requested_vault_slot=1,
                    requested_vault_action=action,
                    reported_vault_action_allowed=False,
                    vault_firewall_errno="EROFS",
                )
            )
            self.assertTrue(blocked_ok.passed, action)

            bypass_bad = evaluate_liveview_grid_lut_embed_pplut_vault(
                build_default_safe_liveview_grid_lut_embed_pplut_vault_spec(
                    requested_vault_slot=1,
                    requested_vault_action=action,
                    reported_vault_action_allowed=True,
                    vault_firewall_errno=None,
                )
            )
            self.assertFalse(bypass_bad.passed, action)
            self.assertEqual(bypass_bad.block_code, P326_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL)

    def test_42_slot1_make_cube_folder_during_import_rejected_erofs30(self) -> None:
        bad = evaluate_liveview_grid_lut_embed_pplut_vault(
            build_default_safe_liveview_grid_lut_embed_pplut_vault_spec(
                requested_vault_slot=1,
                requested_vault_action="IMPORT_USER_LUT_CUBE",
                make_cube_folder_on_slot1=True,
                reported_vault_action_allowed=True,
                vault_firewall_errno=None,
            )
        )
        self.assertFalse(bad.passed)
        self.assertEqual(bad.block_code, P326_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL)

    def test_43_fx6_16_lut_cap_vs_50_buffer_spoof_rejected(self) -> None:
        bad_cap = evaluate_liveview_grid_lut_embed_pplut_vault(
            build_default_safe_liveview_grid_lut_embed_pplut_vault_spec(
                fx6_user_lut_ui_cap=50,
                fx6_exposes_50_lut_slots=True,
            )
        )
        self.assertFalse(bad_cap.passed)
        self.assertEqual(bad_cap.block_code, P326_BLOCKED_LUT_PATH_EMBED_VS_PPLUT_OR_FX6_SPOOF)

    def test_44_pillar58b_6_scenario_suite_passes_all_6(self) -> None:
        res = run_pillar58b_liveview_lut_embed_pplut_6_scenario_suite()
        self.assertTrue(res.passed)
        self.assertEqual(res.status, P326_STATUS_VERIFIED_PILLAR_58B)
        self.assertEqual(res.scenarios_passed, 6)
        self.assertEqual(res.scenarios_total, 6)
        self.assertEqual(tuple(s.scenario_id for s in res.scenarios), P326_PILLAR_58B_SCENARIO_IDS)
        self.assertEqual(sum(1 for s in res.scenarios if s.expected_allowed), 2)
        self.assertEqual(sum(1 for s in res.scenarios if not s.expected_allowed), 4)


class TestPillar58CombinedAndMaster58Aggregator(unittest.TestCase):
    """Combined single-shot verifier, standalone suite, 58/58 master & backward compat."""

    def test_45_combined_verifier_and_symmetry_alias_both_modes(self) -> None:
        for forced in (True, None):
            r1 = verify_dial_customize_mydial_fn12x2_liveview_lut_embed_and_vault(
                force_clean_room=forced
            )
            r2 = verify_dial_customize_mydial_fn12x2_liveview_lut_embed_vault(
                force_clean_room=forced
            )
            self.assertTrue(r1.all_passed)
            self.assertTrue(r2.all_passed)
            self.assertEqual(r1.status, P326_STATUS_VERIFIED_PILLAR58_SUITE)
            self.assertEqual(r1.raw_firmware_bytes_leaked, 0)

    def test_46_standalone_suite_sha256_deterministic(self) -> None:
        a = run_pillar58_standalone_suite(force_clean_room=True)
        b = run_pillar58_standalone_suite(force_clean_room=True)
        self.assertTrue(a.all_passed)
        self.assertEqual(a.suite_sha256, b.suite_sha256)
        self.assertEqual(len(a.suite_sha256), 64)

    def test_47_master_58pillar_aggregates_57pillar_plus_pillar58(self) -> None:
        m57 = evaluate_realhw_57pillar_recovery_master(force_clean_room=True)
        m58 = evaluate_realhw_58pillar_recovery_master(force_clean_room=True)
        self.assertTrue(m57.all_passed)
        self.assertTrue(m58.all_passed)
        self.assertEqual(m58.schema_version, "realhw_58pillar_recovery_master_v1")
        self.assertEqual(m58.status, P326_STATUS_VERIFIED_58OF58_AGGREGATOR)
        self.assertEqual(m58.pillar_count, 58)
        self.assertEqual(m58.pillars_passed, 58)
        self.assertEqual(len(m58.pillars), 58)
        self.assertEqual(
            m58.pillars[-1].pillar_id,
            "pillar_58_dial_customize_mydial_fn12x2_liveview_lut_embed_vault",
        )
        self.assertEqual(
            [p.pillar_id for p in m58.pillars[:57]],
            [p.pillar_id for p in m57.pillars],
        )

    def test_48_master_58_aliases_consistent(self) -> None:
        r1 = evaluate_realhw_58pillar_recovery_master(force_clean_room=True)
        r2 = evaluate_58pillar_recovery_master(force_clean_room=True)
        r3 = verify_58pillar_recovery_suite(force_clean_room=True)
        self.assertEqual(r1.master_58pillar_sha256, r2.master_58pillar_sha256)
        self.assertEqual(r1.master_58pillar_sha256, r3.master_58pillar_sha256)
        self.assertEqual(r1.pillars_passed, r2.pillars_passed)

    def test_49_master_58_latency_budgets_met_in_both_modes(self) -> None:
        for forced in (True, None):
            rep = evaluate_realhw_58pillar_recovery_master(force_clean_room=forced)
            self.assertTrue(rep.under_1_5s_fast_cli_budget, f"elapsed={rep.elapsed_seconds}")
            self.assertLess(rep.elapsed_seconds, P326_FAST_CLI_BUDGET_SECONDS)
            self.assertTrue(rep.under_2_5s_fast_cli_budget)
            self.assertTrue(rep.nominal_under_4_0s)
            self.assertTrue(rep.under_6s_budget)

    def test_50_master_58_zero_risk_and_wave56_counters(self) -> None:
        rep = evaluate_realhw_58pillar_recovery_master(force_clean_room=True)
        self.assertEqual(rep.dial_customize_dormant_trap_or_reset_drift_events, 0)
        self.assertEqual(rep.rear_dial_lr_or_mydial_override_drift_events, 0)
        self.assertEqual(rep.fn_menu_12x2_or_fx6_dial_spoof_events, 0)
        self.assertEqual(rep.live_view_display_reset_split_or_mode_drift_events, 0)
        self.assertEqual(rep.grid_line_or_hdmi_clean_feed_leak_events, 0)
        self.assertEqual(rep.lut_path_embed_sidecar_or_slot1_vault_bypass_events, 0)
        self.assertEqual(rep.slot1_data_sector_writes, 0)
        self.assertEqual(rep.slot1_lut_mutation_bytes, 0)
        self.assertFalse(rep.slot1_avf_info_mutated)
        self.assertEqual(rep.slot1_vault_mutation_bytes, 0)
        self.assertTrue(rep.slot1_format_hard_locked)
        self.assertTrue(rep.slot1_vault_erofs_eopnotsupp_enforced)
        self.assertEqual(rep.fx3_dial_customize_item_count, 5)
        self.assertEqual(rep.fx3_physical_dial_count, 3)
        self.assertEqual(rep.fx3_my_dial_bank_count, 3)
        self.assertEqual(rep.fx3_fn_menu_still_slots, 12)
        self.assertEqual(rep.fx3_fn_menu_movie_slots, 12)
        self.assertEqual(rep.fx3_live_view_display_set_item_count, 3)
        self.assertEqual(rep.fx3_grid_line_type_count, 3)
        self.assertEqual(rep.fx3_user_lut_slot_count, 16)
        self.assertEqual(rep.fx3_pplut_slot_count, 4)
        self.assertEqual(rep.fx6_user_lut_ui_cap, 16)
        self.assertFalse(rep.fx6_has_av_tv_rotate)
        self.assertFalse(rep.fx6_has_my_dial)
        self.assertFalse(rep.fx6_has_fn_menu)
        self.assertTrue(rep.fx6_has_multi_channel_lut_switches)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.cross_model_flash_authorized)
        self.assertFalse(rep.hardware_live_attachment_authorized)
        self.assertTrue(rep.cnflasha_userspace_write_blocked)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_51_master_58_fault_injection_p58_fails_deterministically(self) -> None:
        rep = evaluate_realhw_58pillar_recovery_master(
            force_clean_room=True,
            fault_inject_pillar="pillar_58_dial_customize_mydial_fn12x2_liveview_lut_embed_vault",
        )
        self.assertFalse(rep.all_passed)
        self.assertEqual(rep.status, P326_STATUS_FAIL_58OF58_AGGREGATOR)
        self.assertEqual(rep.pillars_passed, 57)
        self.assertIn(
            "pillar_58_dial_customize_mydial_fn12x2_liveview_lut_embed_vault",
            rep.failed_pillars,
        )

    def test_52_master_58_fault_injection_p1_and_unknown_pillar(self) -> None:
        rep = evaluate_realhw_58pillar_recovery_master(
            force_clean_room=True,
            fault_inject_pillar=MASTER_58_PILLAR_IDS[0],
        )
        self.assertFalse(rep.all_passed)
        self.assertLess(rep.pillars_passed, 58)
        self.assertIn(MASTER_58_PILLAR_IDS[0], rep.failed_pillars)
        with self.assertRaises(ValueError):
            evaluate_realhw_58pillar_recovery_master(
                force_clean_room=True,
                fault_inject_pillar="P999_UNKNOWN",
            )

    def test_53_master_58_safety_tamper_fails(self) -> None:
        with mock.patch.object(p326, "RAW_FIRMWARE_BYTES_LEAKED", 64):
            with self.assertRaises(ValueError):
                evaluate_realhw_58pillar_recovery_master(force_clean_room=True)

    def test_54_master_58_json_serialization_no_nan(self) -> None:
        rep = evaluate_realhw_58pillar_recovery_master(force_clean_room=True)
        encoded = json.dumps(rep.to_dict(), allow_nan=False, sort_keys=True)
        decoded = json.loads(encoded)
        self.assertEqual(decoded["pillar_count"], 58)
        self.assertEqual(decoded["pillars_passed"], 58)

    def test_55_cli_inprocess_pillar58_standalone_json(self) -> None:
        buf = io.StringIO()
        with mock.patch.object(
            sys,
            "argv",
            [
                "fx3_recovery",
                "verify-pillar58-dial-customize-mydial-fn12x2-liveview-lut-embed-vault",
                "--force-clean-room",
                "--json",
            ],
        ), redirect_stdout(buf):
            rc = cli_main.main()
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())
        self.assertTrue(payload["all_passed"])
        self.assertEqual(payload["verification_mode"], "CLEAN_ROOM_SYNTHETIC")

    def test_56_cli_inprocess_verify_58pillar_recovery_json_and_out_file(self) -> None:
        work_tests = REPO_ROOT / "work" / "_tests"
        work_tests.mkdir(parents=True, exist_ok=True)
        out_dir = Path(tempfile.mkdtemp(prefix="p326_m58_", dir=str(work_tests)))
        shutil.rmtree(out_dir)
        try:
            buf = io.StringIO()
            with mock.patch.object(
                sys,
                "argv",
                [
                    "fx3_recovery",
                    "verify-58pillar-recovery",
                    "--force-clean-room",
                    "--json",
                    "--out",
                    str(out_dir),
                ],
            ), redirect_stdout(buf):
                rc = cli_main.main()
            self.assertEqual(rc, 0, buf.getvalue())
            payload = json.loads(buf.getvalue())
            self.assertTrue(payload["all_passed"])
            self.assertEqual(payload["pillars_passed"], 58)
            report_file = out_dir / "58pillar-recovery-master-report.json"
            self.assertTrue(report_file.exists())
            file_payload = json.loads(report_file.read_text(encoding="utf-8"))
            self.assertEqual(
                file_payload["master_58pillar_sha256"], payload["master_58pillar_sha256"]
            )
        finally:
            shutil.rmtree(out_dir, ignore_errors=True)

    def test_57_cli_inprocess_pillar58_out_file(self) -> None:
        work_tests = REPO_ROOT / "work" / "_tests"
        work_tests.mkdir(parents=True, exist_ok=True)
        out_dir = Path(tempfile.mkdtemp(prefix="p326_p58_", dir=str(work_tests)))
        shutil.rmtree(out_dir)
        try:
            buf = io.StringIO()
            with mock.patch.object(
                sys,
                "argv",
                [
                    "fx3_recovery",
                    "verify-pillar58-dial-customize-mydial-fn12x2-liveview-lut-embed-vault",
                    "--force-clean-room",
                    "--out",
                    str(out_dir),
                ],
            ), redirect_stdout(buf):
                rc = cli_main.main()
            self.assertEqual(rc, 0, buf.getvalue())
            self.assertIn(f"status={P326_STATUS_VERIFIED_PILLAR58_SUITE}", buf.getvalue())
            report_file = (
                out_dir / "pillar58-dial-customize-mydial-fn12x2-liveview-lut-embed-vault-report.json"
            )
            self.assertTrue(report_file.exists())
        finally:
            shutil.rmtree(out_dir, ignore_errors=True)

    def test_58_cli_inprocess_human_readable_summary_exits_zero(self) -> None:
        buf = io.StringIO()
        with mock.patch.object(
            sys,
            "argv",
            ["fx3_recovery", "verify-58pillar-recovery", "--force-clean-room"],
        ), redirect_stdout(buf):
            rc = cli_main.main()
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("status=VERIFIED_58OF58_PILLAR_RECOVERY_MASTER", out)
        self.assertIn("pillars=58/58", out)
        self.assertIn("raw_firmware_bytes_leaked=0", out)

    def test_59_cli_subprocess_help_uses_sys_executable(self) -> None:
        proc = subprocess.run(
            [sys.executable, "-B", "-m", "fx3_recovery", "--help"],
            cwd=str(REPO_ROOT),
            env=_clean_env(),
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("verify-58pillar-recovery", proc.stdout)
        self.assertIn(
            "verify-pillar58-dial-customize-mydial-fn12x2-liveview-lut-embed-vault",
            proc.stdout,
        )

    def test_60_cli_subprocess_verify_58pillar_recovery_clean_room_json(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "fx3_recovery",
                "verify-58pillar-recovery",
                "--force-clean-room",
                "--json",
            ],
            cwd=str(REPO_ROOT),
            env=_clean_env(),
            capture_output=True,
            text=True,
            timeout=25,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertTrue(payload["all_passed"])
        self.assertEqual(payload["pillars_passed"], 58)
        self.assertEqual(payload["verification_mode"], "CLEAN_ROOM_SYNTHETIC")

    def test_61_cli_subprocess_pillar58_fx3_clean_room_test_env_json(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "fx3_recovery",
                "verify-pillar58-dial-customize-mydial-fn12x2-liveview-lut-embed-vault",
                "--json",
            ],
            cwd=str(REPO_ROOT),
            env=_clean_env({"FX3_CLEAN_ROOM_TEST": "1"}),
            capture_output=True,
            text=True,
            timeout=25,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertTrue(payload["all_passed"])
        self.assertEqual(payload["verification_mode"], "CLEAN_ROOM_SYNTHETIC")

    def test_62_cli_subprocess_fx3_fx6_force_clean_room_env_58pillar(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "fx3_recovery",
                "verify-58pillar-recovery",
                "--json",
            ],
            cwd=str(REPO_ROOT),
            env=_clean_env({"FX3_FX6_FORCE_CLEAN_ROOM": "1"}),
            capture_output=True,
            text=True,
            timeout=25,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertTrue(payload["all_passed"])
        self.assertEqual(payload["pillars_passed"], 58)
        self.assertEqual(payload["verification_mode"], "CLEAN_ROOM_SYNTHETIC")

    def test_63_cli_subprocess_default_mode_exits_zero(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "fx3_recovery",
                "verify-58pillar-recovery",
                "--json",
            ],
            cwd=str(REPO_ROOT),
            env=_clean_env(),
            capture_output=True,
            text=True,
            timeout=25,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertTrue(payload["all_passed"])
        self.assertGreaterEqual(payload["pillar_count"], 58)
        self.assertGreaterEqual(payload["pillars_passed"], 58)
        self.assertEqual(payload["raw_firmware_bytes_leaked"], 0)

    def test_64_backward_compatibility_57_56_and_22_pillar_clis(self) -> None:
        for cmd, flag, expected_pillars in (
            ("verify-57pillar-recovery", "--force-clean-room", 57),
            ("verify-56pillar-recovery", "--force-clean-room", 56),
            ("verify-22pillar-recovery", "--clean-room", 22),
        ):
            proc = subprocess.run(
                [sys.executable, "-B", "-m", "fx3_recovery", cmd, flag, "--json"],
                cwd=str(REPO_ROOT),
                env=_clean_env(),
                capture_output=True,
                text=True,
                timeout=25,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, f"{cmd}: {proc.stderr}")
            payload = json.loads(proc.stdout)
            self.assertTrue(payload["all_passed"], cmd)
            self.assertEqual(payload["pillars_passed"], expected_pillars, cmd)

    def test_65_milestone311_auto_discovery_selects_58_of_58(self) -> None:
        sys.path.insert(0, str(REPO_ROOT / "outputs/fx6-on-fx3-closure"))
        try:
            from fx6_closure import realhw_milestone311_master_gate as m311
        finally:
            if str(REPO_ROOT / "outputs/fx6-on-fx3-closure") in sys.path:
                sys.path.remove(str(REPO_ROOT / "outputs/fx6-on-fx3-closure"))
        count, fn, ids = m311._discover_highest_recovery_master()
        self.assertGreaterEqual(count, 58)
        self.assertTrue(callable(fn))
        self.assertGreaterEqual(len(ids), 58)

    def test_66_state_helper_dial_customize_initialize_resets_defaults(self) -> None:
        st = compute_expected_dial_customize_mydial_fn12x2_state(
            camera_model=P326_FX3_MODEL_NAME,
            shooting_domain="Still",
            dial_customize_items=P326_DIAL_CUSTOMIZE_5_ITEMS,
            av_tv_rotate="Reverse",
            function_ring_lens="APS-C/Super 35 mm / Full Frame",
            lock_operation_parts="All",
            physical_dials_present=P326_PHYSICAL_3_DIALS,
            requested_dormant_dial_symbols=(),
            my_dial_1_configured=True,
            my_dial_2_configured=True,
            my_dial_3_configured=True,
            my_dial_recall_mode="Hold",
            my_dial_cycle_step=2,
            fn_still_slot_count=12,
            fn_movie_slot_count=12,
            fn_all_not_set_pressed=False,
            reset_action="Initialize",
        )
        self.assertEqual(st["post_av_tv_rotate"], "Normal")
        self.assertEqual(st["post_function_ring_lens"], "Power Focus")
        self.assertEqual(st["post_lock_operation_parts"], "Off")
        self.assertFalse(st["dials_temporarily_unlocked_by_mydial"])

    def test_67_state_helper_liveview_initialize_resets_all_items(self) -> None:
        st = compute_expected_liveview_grid_lut_embed_state(
            camera_model=P326_FX3_MODEL_NAME,
            shooting_domain="Still",
            live_view_display="Setting Effect OFF",
            bright_monitoring_active=False,
            exposure_effect="Exposure Setting Only",
            frame_rate_low_limit="On",
            grid_line_display="On",
            grid_line_type="Square Grid",
            hdmi_info_display="On",
            raw_output_or_hdmi_only=False,
            card_media_type="SDXC",
            user_lut_slot_populated=True,
            select_lut="User5",
            embed_lut_file="Off",
            pplut_slot="PPLUT2",
            lut_workflow_mode="VIEW_LUT_ONLY",
            requested_vault_slot=1,
            slot1_holds_tier0_vault=True,
            requested_vault_action="READ_ONLY_AUDIT",
            make_cube_folder_on_slot1=False,
            reset_action="Initialize",
        )
        self.assertEqual(st["post_live_view_display"], "Setting Effect ON")
        self.assertEqual(st["post_exposure_effect"], "Exposure Set. & flash")
        self.assertEqual(st["post_frame_rate_low_limit"], "Off")
        self.assertEqual(st["post_grid_line_display"], "Off")
        self.assertEqual(st["post_grid_line_type"], "Rule of 3rds Grid")
        self.assertEqual(st["post_select_lut"], "s709")
        self.assertEqual(st["post_embed_lut_file"], "On")
        self.assertTrue(st["post_pplut_reset"])

    def test_68_hdmi_info_display_on_without_raw_does_not_isolate_clean_feed(self) -> None:
        ok_on = evaluate_liveview_grid_lut_embed_pplut_vault(
            build_default_safe_liveview_grid_lut_embed_pplut_vault_spec(
                grid_line_display="On",
                post_grid_line_display="On",
                hdmi_info_display="On",
                raw_output_or_hdmi_only=False,
                reported_clean_hdmi_osd_isolated_to_lcd=False,
                reported_hdmi_clean_feed_grid_leaked=False,
            )
        )
        self.assertTrue(ok_on.passed)
        # RAW output forces HDMI Info Display = Off -> must isolate
        raw_leak = evaluate_liveview_grid_lut_embed_pplut_vault(
            build_default_safe_liveview_grid_lut_embed_pplut_vault_spec(
                grid_line_display="On",
                hdmi_info_display="On",
                raw_output_or_hdmi_only=True,
                reported_clean_hdmi_osd_isolated_to_lcd=False,
                reported_hdmi_clean_feed_grid_leaked=True,
            )
        )
        self.assertFalse(raw_leak.passed)
        self.assertEqual(raw_leak.block_code, P326_BLOCKED_GRID_LINE_OR_HDMI_CLEAN_FEED_LEAK)

    def test_69_sd_media_also_hardware_locks_embed_lut_file_off(self) -> None:
        ok = evaluate_liveview_grid_lut_embed_pplut_vault(
            build_default_safe_liveview_grid_lut_embed_pplut_vault_spec(
                card_media_type="SD",
                lut_card_dir=P326_FX3_LUT_SD_DIR,
                embed_lut_file="On",
                reported_embed_lut_file="Off",
            )
        )
        self.assertTrue(ok.passed)

    def test_70_pplut1_to_4_all_bake_and_do_not_preserve_slog3_pixels(self) -> None:
        for pplut in ("PPLUT1", "PPLUT2", "PPLUT3", "PPLUT4"):
            ok = evaluate_liveview_grid_lut_embed_pplut_vault(
                build_default_safe_liveview_grid_lut_embed_pplut_vault_spec(
                    lut_workflow_mode="PPLUT_BAKE",
                    pplut_slot=pplut,
                    reported_slog3_pixels_preserved=False,
                )
            )
            self.assertTrue(ok.passed, pplut)
            bad = evaluate_liveview_grid_lut_embed_pplut_vault(
                build_default_safe_liveview_grid_lut_embed_pplut_vault_spec(
                    lut_workflow_mode="PPLUT_BAKE",
                    pplut_slot=pplut,
                    reported_slog3_pixels_preserved=True,
                )
            )
            self.assertFalse(bad.passed, pplut)

    def test_71_slot2_writable_media_allows_embed_and_pplut_record(self) -> None:
        for action in ("EMBED_LUT_RECORD", "PPLUT_RECORD", "EXPORT_OR_WRITE_LUT"):
            ok = evaluate_liveview_grid_lut_embed_pplut_vault(
                build_default_safe_liveview_grid_lut_embed_pplut_vault_spec(
                    requested_vault_slot=2,
                    requested_vault_action=action,
                    reported_vault_action_allowed=True,
                    vault_firewall_errno=None,
                )
            )
            self.assertTrue(ok.passed, action)

    def test_72_pillar58b_slot1_non_zero_bytes_or_avf_info_mutated_rejected(self) -> None:
        bad_bytes = evaluate_liveview_grid_lut_embed_pplut_vault(
            build_default_safe_liveview_grid_lut_embed_pplut_vault_spec(
                slot1_lut_mutation_bytes=512,
                slot1_vault_mutation_bytes=512,
                slot1_avf_info_mutated=True,
            )
        )
        self.assertFalse(bad_bytes.passed)
        self.assertEqual(bad_bytes.block_code, P326_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL)

    def test_73_pillar58b_persistent_overlay_and_h0_h3_drift_rejected(self) -> None:
        bad_ov = evaluate_liveview_grid_lut_embed_pplut_vault(
            build_default_safe_liveview_grid_lut_embed_pplut_vault_spec(
                overlay_dir="/dev/cnflasha15"
            )
        )
        self.assertFalse(bad_ov.passed)
        self.assertEqual(bad_ov.block_code, P326_BLOCKED_PERSISTENT_OVERLAY_ESCAPE)

        bad_h3 = evaluate_liveview_grid_lut_embed_pplut_vault(
            build_default_safe_liveview_grid_lut_embed_pplut_vault_spec(
                tier0_surfaces_h0_h3_matched=14
            )
        )
        self.assertFalse(bad_h3.passed)
        self.assertEqual(bad_h3.block_code, P326_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT)

    def test_74_fx6_lut_paths_and_16_slot_cap_passes_cleanly(self) -> None:
        ok = evaluate_liveview_grid_lut_embed_pplut_vault(
            build_default_safe_liveview_grid_lut_embed_pplut_vault_spec(
                camera_model=P326_FX6_DONOR_MODEL_NAME,
                fw_version=P326_FX6_DONOR_FW_VERSION,
                shooting_domain="Movie",
                card_media_type="SDXC",
                lut_card_dir=P326_FX6_LUT_SD_DIR,
                fx6_user_lut_ui_cap=16,
                fx6_exposes_50_lut_slots=False,
                fx6_supports_multi_channel_lut_switches=True,
            )
        )
        self.assertTrue(ok.passed)

    def test_75_fx6_cfexpress_lut_path_uppercase_verified(self) -> None:
        ok = evaluate_liveview_grid_lut_embed_pplut_vault(
            build_default_safe_liveview_grid_lut_embed_pplut_vault_spec(
                camera_model=P326_FX6_DONOR_MODEL_NAME,
                fw_version=P326_FX6_DONOR_FW_VERSION,
                shooting_domain="Movie",
                card_media_type="CFexpress Type A",
                lut_card_dir=P326_FX6_LUT_CFEXPRESS_DIR,
            )
        )
        self.assertTrue(ok.passed)

    def test_76_fn_menu_still_movie_domains_accept_12x2(self) -> None:
        for dom in ("Still", "Movie", "S&Q"):
            ok = evaluate_dial_customize_mydial_fn12x2_vault(
                build_default_safe_dial_customize_mydial_fn12x2_vault_spec(
                    shooting_domain=dom,
                    fn_still_slot_count=12,
                    fn_movie_slot_count=12,
                )
            )
            self.assertTrue(ok.passed, dom)

    def test_77_mydial_step_past_all_configured_banks_returns_none(self) -> None:
        st = compute_expected_dial_customize_mydial_fn12x2_state(
            camera_model=P326_FX3_MODEL_NAME,
            shooting_domain="Movie",
            dial_customize_items=P326_DIAL_CUSTOMIZE_5_ITEMS,
            av_tv_rotate="Normal",
            function_ring_lens="Power Focus",
            lock_operation_parts="Dial + Wheel",
            physical_dials_present=P326_PHYSICAL_3_DIALS,
            requested_dormant_dial_symbols=(),
            my_dial_1_configured=True,
            my_dial_2_configured=False,
            my_dial_3_configured=False,
            my_dial_recall_mode="1->2->3",
            my_dial_cycle_step=2,
            fn_still_slot_count=12,
            fn_movie_slot_count=12,
            fn_all_not_set_pressed=False,
            reset_action="None",
        )
        self.assertIsNone(st["active_my_dial_bank"])
        self.assertFalse(st["dials_temporarily_unlocked_by_mydial"])

    def test_78_long_press_fn_missing_fails_58a(self) -> None:
        bad = evaluate_dial_customize_mydial_fn12x2_vault(
            build_default_safe_dial_customize_mydial_fn12x2_vault_spec(
                long_press_fn_toggles_lock=False
            )
        )
        self.assertFalse(bad.passed)
        self.assertEqual(bad.block_code, P326_BLOCKED_DIAL_CUSTOMIZE_5ITEM_OR_RESET_DRIFT)

    def test_79_missing_multi_channel_lut_switches_fails_58b(self) -> None:
        bad = evaluate_liveview_grid_lut_embed_pplut_vault(
            build_default_safe_liveview_grid_lut_embed_pplut_vault_spec(
                fx6_supports_multi_channel_lut_switches=False
            )
        )
        self.assertFalse(bad.passed)
        self.assertEqual(bad.block_code, P326_BLOCKED_LUT_PATH_EMBED_VS_PPLUT_OR_FX6_SPOOF)

    def test_80_wrong_live_view_menu_path_fails_58b(self) -> None:
        bad = evaluate_liveview_grid_lut_embed_pplut_vault(
            build_default_safe_liveview_grid_lut_embed_pplut_vault_spec(
                live_view_menu_path=("Setup", "Display Option", "Live View Display Set.")
            )
        )
        self.assertFalse(bad.passed)
        self.assertEqual(bad.block_code, P326_BLOCKED_LIVE_VIEW_RESET_SPLIT_OR_STILL_GATE)

    def test_81_wrong_lut_dir_for_sdxc_vs_cfexpress_fails_58b(self) -> None:
        bad = evaluate_liveview_grid_lut_embed_pplut_vault(
            build_default_safe_liveview_grid_lut_embed_pplut_vault_spec(
                card_media_type="SDXC",
                lut_card_dir="/Sony/PRO/LUT",
            )
        )
        self.assertFalse(bad.passed)
        self.assertEqual(bad.block_code, P326_BLOCKED_LUT_PATH_EMBED_VS_PPLUT_OR_FX6_SPOOF)

    def test_82_fx6_without_physical_hold_switch_fails_58a(self) -> None:
        bad = evaluate_dial_customize_mydial_fn12x2_vault(
            build_default_safe_dial_customize_mydial_fn12x2_vault_spec(
                camera_model=P326_FX6_DONOR_MODEL_NAME,
                fw_version=P326_FX6_DONOR_FW_VERSION,
                fx6_uses_physical_hold_switch=False,
            )
        )
        self.assertFalse(bad.passed)
        self.assertEqual(bad.block_code, P326_BLOCKED_FN_12X2_OR_FX6_DIAL_SPOOF)

    def test_83_select_lut_s709_vs_709_800pct_all_16_user_slots_accepted(self) -> None:
        for slot in ("S-Log3", "s709", "709(800%)", "User1", "User8", "User16"):
            ok = evaluate_liveview_grid_lut_embed_pplut_vault(
                build_default_safe_liveview_grid_lut_embed_pplut_vault_spec(
                    select_lut=slot,
                    user_lut_slot_populated=True,
                    reported_monitored_lut=slot,
                    post_select_lut=slot,
                )
            )
            self.assertTrue(ok.passed, slot)

    def test_84_negative_drift_counters_non_zero_fail_58a_and_58b(self) -> None:
        b1 = evaluate_dial_customize_mydial_fn12x2_vault(
            build_default_safe_dial_customize_mydial_fn12x2_vault_spec(
                rear_dial_lr_or_mydial_override_drift_events=1
            )
        )
        self.assertFalse(b1.passed)
        self.assertEqual(b1.block_code, P326_BLOCKED_3DIAL_TOPOLOGY_OR_MYDIAL_OVERRIDE_DRIFT)

        b2 = evaluate_liveview_grid_lut_embed_pplut_vault(
            build_default_safe_liveview_grid_lut_embed_pplut_vault_spec(
                grid_line_or_hdmi_clean_feed_leak_events=1
            )
        )
        self.assertFalse(b2.passed)
        self.assertEqual(b2.block_code, P326_BLOCKED_GRID_LINE_OR_HDMI_CLEAN_FEED_LEAK)

    def test_85_combined_verifier_detects_missing_donor_budget_failure(self) -> None:
        bad_snap = p326.Phase326DonorSnapshot(
            verification_mode="LOCAL_DONOR_O_RDONLY",
            all_donors_present=False,
            donor_files_inspected=0,
            elapsed_seconds=0.99,
            under_0_20s_budget=False,
            budget_seconds_applied=0.20,
            raw_firmware_bytes_leaked=0,
            artifacts=(),
        )
        with mock.patch.object(p326, "inspect_phase326_donors_readonly", return_value=bad_snap):
            rep = verify_dial_customize_mydial_fn12x2_liveview_lut_embed_and_vault()
        self.assertFalse(rep.all_passed)
        self.assertEqual(rep.status, P326_STATUS_FAIL_PILLAR58_SUITE)

    def test_86_standalone_suite_propagates_donor_failure(self) -> None:
        bad_snap = p326.Phase326DonorSnapshot(
            verification_mode="LOCAL_DONOR_O_RDONLY",
            all_donors_present=False,
            donor_files_inspected=0,
            elapsed_seconds=0.99,
            under_0_20s_budget=False,
            budget_seconds_applied=0.20,
            raw_firmware_bytes_leaked=0,
            artifacts=(),
        )
        with mock.patch.object(p326, "inspect_phase326_donors_readonly", return_value=bad_snap):
            rep = run_pillar58_standalone_suite()
        self.assertFalse(rep.all_passed)

    def test_87_master_58_nonzero_safety_or_mutation_counter_fails(self) -> None:
        bad_suite = run_pillar58_standalone_suite(force_clean_room=True)
        tampered = p326.Pillar58StandaloneReport(
            **{
                **bad_suite.__dict__,
                "slot1_data_sector_writes": 1,
                "slot1_vault_mutation_bytes": 512,
            }
        )
        with mock.patch.object(p326, "run_pillar58_standalone_suite", return_value=tampered):
            rep = evaluate_realhw_58pillar_recovery_master(force_clean_room=True)
        self.assertFalse(rep.all_passed)
        self.assertEqual(rep.status, P326_STATUS_FAIL_58OF58_AGGREGATOR)

    def test_88_cli_inprocess_default_mode_human_and_json_report_all_58(self) -> None:
        buf = io.StringIO()
        with mock.patch.object(
            sys,
            "argv",
            ["fx3_recovery", "verify-58pillar-recovery", "--json"],
        ), redirect_stdout(buf):
            rc = cli_main.main()
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())
        self.assertTrue(payload["all_passed"])
        self.assertEqual(payload["pillar_count"], 58)
        self.assertEqual(payload["pillars_passed"], 58)
        self.assertEqual(payload["raw_firmware_bytes_leaked"], 0)

    def test_89_fx3_fw_supported_versions_tuple_accepted_and_legacy_rejected(self) -> None:
        for fw in ("7.02", "7.01", "7.00", "6.02", "6.00"):
            rep = evaluate_dial_customize_mydial_fn12x2_vault(
                build_default_safe_dial_customize_mydial_fn12x2_vault_spec(fw_version=fw)
            )
            self.assertTrue(rep.passed, fw)
        bad_fw = evaluate_dial_customize_mydial_fn12x2_vault(
            build_default_safe_dial_customize_mydial_fn12x2_vault_spec(fw_version="1.00")
        )
        self.assertFalse(bad_fw.passed)
        self.assertEqual(bad_fw.block_code, P326_BLOCKED_INVALID_PILLAR58A_SPEC)

    def test_90_all_17_pinned_donors_present_in_synthetic_snapshot(self) -> None:
        snap = inspect_phase326_donors_readonly(force_clean_room=True)
        ids = {a.artifact_id for a in snap.artifacts}
        self.assertEqual(len(ids), 17)
        self.assertIn("fx3_appfw_702_so", ids)
        self.assertIn("fx6_appfw_601_so", ids)
        self.assertIn("fx3_backup_bin", ids)
        self.assertIn("fx6_uxc_en_2", ids)
        self.assertTrue(all(a.read_mode == "CLEAN_ROOM_SYNTHETIC" for a in snap.artifacts))


if __name__ == "__main__":
    unittest.main()
