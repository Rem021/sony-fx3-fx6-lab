"""Phase 320 — Dual-mode unit tests for Recovery Pillar 57 & Unified 57/57 Recovery Master.

Covers:
1. Safety Redlines, Bounded O_RDONLY 17 Donors, CI `work_root is None` Safety & Package Exports.
2. Sub-Pillar 57A:
   - Wave-55 `MENU -> (Setup) -> [Touch Operation]` (`_g 0x6345`, `base 0xe8e3`) exact **4 active
     items**, ALL 4 `Initialize`-only (`resists Camera Settings Reset` & `Reset Network Set.`):
     `[Touch Operation]` (`On`/`On: Playback Only` `0x6cde`/`Off`), `[Touch Sensitivity]` (`Standard`/
     `Sensitive` `0x7205`, NOT `Responsive`), `[Touch Func. in Shooting]` (`Touch Focus`/`Touch Tracking`/
     `Off`, identical across Still/Movie/`S&Q`), and `[Swipe Up]` (`Open the Fn Menu`/`Off`, active only
     when `Touch Operation == On`).
   - Dormant Alpha traps fail-closed with `EOPNOTSUPP=95`: `Touch Shutter` (`0x6a80`), `Touch AE`
     (`0x702a`), `Touch Panel/Pad` (`0x76ec`), `Touch Pad Settings`, `Footer Icon Touch` (`0x70da`),
     `Swipe Left`/`Swipe Right` (`0x6b06`/`0x6c19`).
   - `[Operation Customize] -> [DISP (Screen Disp) Set]` (`_g 0x61c4 -> 0x61da`, NOT `Display Option`,
     `Initialize`-only): exact 4 shoot pages (`Display All Info.`, `No Disp. Info.`, `Histogram`, `Level`)
     and 3 playback pages (`Display Info.`, `Histogram`, `No Disp. Info.`).
   - **Zero-EVF Blackout Guard**: `ILME-FX3` has zero built-in EVF, zero eye sensor, zero `FINDER/MONITOR`
     button; fail-closed `EOPNOTSUPP=95` on `Select Finder/Monitor`, `For viewfinder`, `Graphic Display`,
     `Monitor Off`, vs `ILME-FX6` (`Technical > Touch Operation`, `Touch Function in MF`, detachable
     3.5" LCD `Viewfinder` + `Viewfinder Hood`, never `Loupe`).
3. Sub-Pillar 57B:
   - Still-only (`Movie`/`S&Q` -> `EOPNOTSUPP=95`) `[AEL w/ Shutter]` (`0x669d`, `Auto`/`On`/`Off`,
     `Initialize`-only, `[AEL toggle]` override) & `[Flash]` submenu asymmetric reset split:
     `[Exp.comp.set]` (`Ambient&flash`/`Ambient only`, `Initialize`-only), `[External Flash Set.]`
     (`Initialize`-only, direct MI-Shoe required vs wired sync cord/menu reset `EOPNOTSUPP=95` & FX6
     rolling-shutter `Flash Band Reduce`), and **`[Wireless Flash]` (`Off`/`On`) as the ONLY item among
     the 4 resettable by `[Camera Settings Reset]`**.
   - `MENU -> (Playback) -> [Viewing]` (`_g 0x6033`, NOT `Playback Option`): `[Cont. Play for Interval]`
     & `[Play Speed for Interval]` exact `1..9` speed steps (default `5`, `Initialize`-only, read-only,
     no in-camera movie synthesis).
   - `MENU -> (Playback) -> [Edit]` (`_g 0x6418`): `[Rotate]`, `[Photo Capture]` (`JPEG`/`HEIF(4:2:0)`/
     `HEIF(4:2:2)`), `[Copy]` allowed on `Slot 2` (`[Select Playback Media]` defaults to `Slot 1`),
     ANY write/mutate targeting `Slot 1` fails closed with `EROFS=30` (`slot1_data_sector_writes == 0`),
     and dormant `[Beauty Effect]` / `[Trimming]` fail closed with `EOPNOTSUPP=95` (`EROFS=30` if `Slot 1`).
4. Unified `57/57` Recovery Master (`evaluate_realhw_57pillar_recovery_master` / CLI `< 1.5s`).
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
from fx3_recovery import (
    realhw_57pillar_touch_disp_zero_evf_flash_interval_pb_vault_verifier as p320,
)
from fx3_recovery.realhw_56pillar_switch_vh_af_stdadj_tcub_copy_vault_verifier import (
    evaluate_realhw_56pillar_recovery_master,
)
from fx3_recovery.realhw_57pillar_touch_disp_zero_evf_flash_interval_pb_vault_verifier import (
    ALLOW_BOOT_PARTITION_TARGETING,
    ALLOW_DESTRUCTIVE_FASTBOOT,
    ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS,
    ALLOW_PERSISTENT_JIRITSU_WRITES,
    CROSS_MODEL_FLASH_AUTHORIZED,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    ISP_WRITE_AUTHORIZED,
    LIVE_USB_IOKIT_TRANSMIT_ENABLED,
    MASTER_57_PILLAR_COUNT,
    MASTER_57_PILLAR_IDS,
    MASTER_57_PILLAR_SPECS,
    OTP_FUSE_TOUCHES,
    OTP_FUSE_WRITES,
    OVERALL_READY_FOR_HARDWARE_ATTACH,
    P320_AEL_W_SHUTTER_BKID,
    P320_AEL_W_SHUTTER_DEFAULT,
    P320_AEL_W_SHUTTER_F_RESID16,
    P320_AEL_W_SHUTTER_MODES,
    P320_BLOCKED_DISP_SET_4SHOOT_3PB_OR_PATH_DRIFT,
    P320_BLOCKED_EXT_FLASH_MISHOE_OR_FX6_SPOOF,
    P320_BLOCKED_FX6_TOUCH_OR_EVF_SPOOF,
    P320_BLOCKED_INTERVAL_PB_9SCALE_OR_PATH_DRIFT,
    P320_BLOCKED_INVALID_PILLAR57A_SPEC,
    P320_BLOCKED_INVALID_PILLAR57B_SPEC,
    P320_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
    P320_BLOCKED_PLAYBACK_EDIT_DORMANT_OR_SLOT1_VAULT_FIREWALL,
    P320_BLOCKED_SAFETY_POLICY_VIOLATION,
    P320_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL,
    P320_BLOCKED_STILL_AEL_OR_FLASH_RESET_SPLIT_DRIFT,
    P320_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
    P320_BLOCKED_TOUCH_4ITEM_DORMANT_OR_RESET_DRIFT,
    P320_BLOCKED_ZERO_EVF_BLACKOUT_GUARD_BREACH,
    P320_CONTINUOUS_PLAYBACK_BKID,
    P320_CONT_PB_LEGACY_F_RESID16,
    P320_CONT_PLAY_INTERVAL_F_RESID16,
    P320_DISP_PLAY_3_PAGES,
    P320_DISP_SET_G_RESID16,
    P320_DISP_SET_MENU_PATH,
    P320_DISP_SET_WRONG_PATH,
    P320_DISP_SHOOT_4_PAGES,
    P320_DISP_SHOOT_RESID16_MAP,
    P320_DONOR_INSPECT_BUDGET_SECONDS,
    P320_DONOR_INSPECT_CI_BUDGET_SECONDS,
    P320_DORMANT_BEAUTY_EFFECT_F_RESID16,
    P320_DORMANT_EVF_OR_DISP_TRAPS,
    P320_DORMANT_EVF_TRAP_RESID16_MAP,
    P320_DORMANT_PLAYBACK_EDIT_TRAPS,
    P320_DORMANT_TOUCH_TRAPS,
    P320_DORMANT_TOUCH_TRAP_RESID16_MAP,
    P320_EOPNOTSUPP_ERRNO,
    P320_EROFS_ERRNO,
    P320_EXP_COMP_SET_BKID,
    P320_EXP_COMP_SET_DEFAULT,
    P320_EXP_COMP_SET_F_RESID16,
    P320_EXP_COMP_SET_F_RESID16_MAP,
    P320_EXP_COMP_SET_MODES,
    P320_EXT_FLASH_CUST_F_RESID16,
    P320_EXT_FLASH_FIRING_F_RESID16,
    P320_EXT_FLASH_SET_F_RESID16,
    P320_EXT_FLASH_SUBMENUS,
    P320_FAST_CLI_BUDGET_SECONDS,
    P320_FX3_DISP_PLAY_PAGE_COUNT,
    P320_FX3_DISP_SHOOT_PAGE_COUNT,
    P320_FX3_FW_VERSION,
    P320_FX3_HAS_BUILTIN_EVF,
    P320_FX3_HAS_EYE_SENSOR,
    P320_FX3_HAS_FINDER_MONITOR_BUTTON,
    P320_FX3_HELPGUIDE_ID,
    P320_FX3_INTERVAL_PB_SPEED_DEFAULT,
    P320_FX3_INTERVAL_PB_SPEED_MAX,
    P320_FX3_INTERVAL_PB_SPEED_MIN,
    P320_FX3_MODEL_ID,
    P320_FX3_MODEL_NAME,
    P320_FX3_PRODUCT_CODENAME,
    P320_FX3_TOUCH_ACTIVE_ITEM_COUNT,
    P320_FX6_BUILTIN_EVF_ENUM,
    P320_FX6_DETACHABLE_LCD_TERMS,
    P320_FX6_FLASH_BAND_REDUCE_2_RESID16,
    P320_FX6_FORBIDDEN_LOUPE_TERM,
    P320_FX6_HAS_BUILTIN_EVF,
    P320_FX6_HAS_DETACHABLE_LCD_VIEWFINDER,
    P320_FX6_HAS_INTERVAL_PB,
    P320_FX6_HAS_PLAYBACK_EDIT_MENU,
    P320_FX6_HAS_STILL_TTL_FLASH,
    P320_FX6_TOUCH_MF_MODES,
    P320_FX6_TOUCH_OPERATION_MODES,
    P320_INTERVAL_PB_MENU_PATH,
    P320_INTERVAL_PB_SPEED_DEFAULT,
    P320_INTERVAL_PB_SPEED_SCALE_9,
    P320_INTERVAL_PB_WRONG_PATH,
    P320_PB_SPEED_LEGACY_F_RESID16,
    P320_PHOTO_CAPTURE_FILE_DEFAULT,
    P320_PHOTO_CAPTURE_FILE_TYPES,
    P320_PINNED_FX3_APPFW_702_BYTES,
    P320_PINNED_FX3_APPFW_702_HDR4K_SHA256,
    P320_PINNED_FX3_BACKUP_BIN_BYTES,
    P320_PINNED_FX3_BACKUP_BIN_SHA256,
    P320_PINNED_FX3_UXC_EN_F_BYTES,
    P320_PINNED_FX3_UXC_EN_F_SHA256,
    P320_PINNED_FX6_APPFW_601_BYTES,
    P320_PINNED_FX6_APPFW_601_HDR4K_SHA256,
    P320_PLAYBACK_EDIT_ACTIVE_4_ITEMS,
    P320_PLAYBACK_EDIT_G_RESID16,
    P320_PLAYBACK_EDIT_RESID16_MAP,
    P320_PLAYBACK_VIEWING_G_RESID16,
    P320_PLAY_SPEED_INTERVAL_F_RESID16,
    P320_SAFE_SECONDARY_SLOT,
    P320_SELECT_PLAYBACK_MEDIA_DEFAULT_SLOT,
    P320_SLOT1_FORMAT_HARD_LOCKED,
    P320_SLOT1_VAULT_EROFS_EOPNOTSUPP_ENFORCED,
    P320_SLOT1_VAULT_SLOT,
    P320_STATUS_FAIL_57OF57_AGGREGATOR,
    P320_STATUS_VERIFIED_57OF57_AGGREGATOR,
    P320_STATUS_VERIFIED_PILLAR57_SUITE,
    P320_STATUS_VERIFIED_PILLAR_57A,
    P320_STATUS_VERIFIED_PILLAR_57B,
    P320_SWIPE_UP_BKID,
    P320_SWIPE_UP_DEFAULT,
    P320_SWIPE_UP_FN_MENU_F_RESID16,
    P320_SWIPE_UP_F_RESID16,
    P320_TIER0_SURFACE_COUNT,
    P320_TOUCH_FUNC_RESID16_MAP,
    P320_TOUCH_FUNC_SHOOTING_BKID,
    P320_TOUCH_FUNC_SHOOTING_DEFAULT,
    P320_TOUCH_FUNC_SHOOTING_F_RESID16,
    P320_TOUCH_OPERATION_4_ITEMS,
    P320_TOUCH_OPERATION_BASE_RESID16,
    P320_TOUCH_OPERATION_BKID,
    P320_TOUCH_OPERATION_DEFAULT,
    P320_TOUCH_OPERATION_G_RESID16,
    P320_TOUCH_OP_PLAYBACK_ONLY_F_RESID16,
    P320_TOUCH_SENSITIVITY_BKID,
    P320_TOUCH_SENSITIVITY_DEFAULT,
    P320_TOUCH_SENSITIVITY_DORMANT_OR_WRONG,
    P320_TOUCH_SENSITIVITY_F_RESID16,
    P320_TOUCH_SENSITIVITY_SENSITIVE_F_RESID16,
    P320_WIRELESS_FLASH_BKID,
    P320_WIRELESS_FLASH_DEFAULT,
    P320_WIRELESS_FLASH_F_RESID16,
    PASSIVE_TX_BYTES_EMITTED,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHASE320_MASTER_SCHEMA,
    PHASE320_PHASE_NUMBER,
    PHASE320_SCHEMA,
    PHASE320_VERSION,
    PHYSICAL_DEVICE_WRITES,
    PHYSICAL_USB_PACKETS_EMITTED,
    RAW_FIRMWARE_BYTES_LEAKED,
    READ_ONLY_DONOR_ACCESS,
    RPMB_COUNTER_INCREMENTS,
    SPI_NOR_WRITE_AUTHORIZED,
    build_default_safe_still_ael_flash_interval_pb_edit_vault_spec,
    build_default_safe_touch_disp_zero_evf_vault_spec,
    compute_expected_still_ael_flash_interval_pb_edit_vault_state,
    compute_expected_touch_disp_zero_evf_state,
    evaluate_57pillar_recovery_master,
    evaluate_realhw_57pillar_recovery_master,
    evaluate_still_ael_flash_interval_pb_edit_vault,
    evaluate_touch_disp_zero_evf_vault,
    inspect_phase320_donors_readonly,
    run_pillar57_standalone_suite,
    run_pillar57a_touch_disp_zero_evf_6_scenario_suite,
    run_pillar57b_still_ael_flash_interval_pb_edit_6_scenario_suite,
    verify_57pillar_recovery_suite,
    verify_touch_disp_zero_evf_flash_interval_pb_and_vault,
    verify_touch_disp_zero_evf_flash_interval_pb_vault,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


def _donor_appfw_present() -> bool:
    if p320.is_forced_clean_room() or os.environ.get(
        p320.P320_ENV_CLEAN_ROOM_TEST, ""
    ).strip().lower() in ("1", "true", "yes"):
        return False
    p = p320.resolve_donor_path(p320.P320_DONOR_FX3_APPFW_702_RELPATH, require_file=True)
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


class TestPhase320SafetyDonorsAndExports(unittest.TestCase):
    """Safety redlines, Wave-55 17-donor inspection & package exports."""

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
        self.assertTrue(P320_SLOT1_FORMAT_HARD_LOCKED)
        self.assertTrue(P320_SLOT1_VAULT_EROFS_EOPNOTSUPP_ENFORCED)
        self.assertEqual(OTP_FUSE_TOUCHES, 0)
        self.assertEqual(OTP_FUSE_WRITES, 0)
        self.assertEqual(RPMB_COUNTER_INCREMENTS, 0)
        self.assertEqual(PASSIVE_TX_BYTES_EMITTED, 0)
        self.assertEqual(PHYSICAL_USB_PACKETS_EMITTED, 0)
        self.assertEqual(PHYSICAL_DEVICE_WRITES, 0)
        self.assertEqual(RAW_FIRMWARE_BYTES_LEAKED, 0)

    def test_02_schema_version_and_camera_identity_constants(self) -> None:
        self.assertEqual(PHASE320_PHASE_NUMBER, 320)
        self.assertEqual(PHASE320_VERSION, "1.0.0")
        self.assertEqual(
            PHASE320_SCHEMA,
            "realhw_57pillar_touch_disp_zero_evf_flash_interval_pb_vault_verifier_v1",
        )
        self.assertEqual(PHASE320_MASTER_SCHEMA, "realhw_57pillar_recovery_master_v1")
        self.assertEqual(P320_FX3_MODEL_NAME, "ILME-FX3")
        self.assertEqual(P320_FX3_MODEL_ID, 0x91030080)
        self.assertEqual(P320_FX3_PRODUCT_CODENAME, "PRODUCT_MODEL_ALCIN_UUD")
        self.assertEqual(P320_FX3_HELPGUIDE_ID, "ilc/2210")
        self.assertEqual(P320_FX3_FW_VERSION, "7.02")
        self.assertEqual(P320_EOPNOTSUPP_ERRNO, 95)
        self.assertEqual(P320_EROFS_ERRNO, 30)
        self.assertFalse(P320_FX3_HAS_BUILTIN_EVF)
        self.assertFalse(P320_FX3_HAS_EYE_SENSOR)
        self.assertFalse(P320_FX3_HAS_FINDER_MONITOR_BUTTON)
        self.assertFalse(P320_FX6_HAS_BUILTIN_EVF)
        self.assertTrue(P320_FX6_HAS_DETACHABLE_LCD_VIEWFINDER)
        self.assertFalse(P320_FX6_HAS_STILL_TTL_FLASH)
        self.assertFalse(P320_FX6_HAS_INTERVAL_PB)
        self.assertFalse(P320_FX6_HAS_PLAYBACK_EDIT_MENU)

    def test_03_empirical_uxc_resid16_and_bkid_constants(self) -> None:
        self.assertEqual(P320_FX3_TOUCH_ACTIVE_ITEM_COUNT, 4)
        self.assertEqual(len(P320_TOUCH_OPERATION_4_ITEMS), 4)
        self.assertEqual(P320_TOUCH_OPERATION_G_RESID16, 0x6345)
        self.assertEqual(P320_TOUCH_OPERATION_BASE_RESID16, 0xE8E3)
        self.assertEqual(P320_TOUCH_OP_PLAYBACK_ONLY_F_RESID16, 0x6CDE)
        self.assertEqual(P320_TOUCH_SENSITIVITY_F_RESID16, 0x739F)
        self.assertEqual(P320_TOUCH_SENSITIVITY_SENSITIVE_F_RESID16, 0x7205)
        self.assertEqual(P320_TOUCH_FUNC_SHOOTING_F_RESID16, 0x7575)
        self.assertEqual(P320_SWIPE_UP_F_RESID16, 0x7518)
        self.assertEqual(P320_SWIPE_UP_FN_MENU_F_RESID16, 0x7281)
        self.assertEqual(P320_TOUCH_OPERATION_BKID, "BKID_APP_setting_touch_operation")
        self.assertEqual(P320_TOUCH_SENSITIVITY_BKID, "BKID_APP_setting_touch_sensitivity")
        self.assertEqual(P320_TOUCH_FUNC_SHOOTING_BKID, "BKID_APP_setting_shooting_touch_function")
        self.assertEqual(P320_SWIPE_UP_BKID, "BKID_APP_setting_swipe_up")
        self.assertEqual(P320_DISP_SET_G_RESID16, 0x61DA)
        self.assertEqual(P320_AEL_W_SHUTTER_F_RESID16, 0x669D)
        self.assertEqual(P320_EXP_COMP_SET_F_RESID16, 0x73C2)
        self.assertEqual(P320_WIRELESS_FLASH_F_RESID16, 0x6201)
        self.assertEqual(P320_EXT_FLASH_SET_F_RESID16, 0x6771)
        self.assertEqual(P320_EXT_FLASH_FIRING_F_RESID16, 0x671D)
        self.assertEqual(P320_EXT_FLASH_CUST_F_RESID16, 0x705F)
        self.assertEqual(P320_PLAYBACK_VIEWING_G_RESID16, 0x6033)
        self.assertEqual(P320_CONT_PLAY_INTERVAL_F_RESID16, 0x78FA)
        self.assertEqual(P320_PLAY_SPEED_INTERVAL_F_RESID16, 0x639E)
        self.assertEqual(P320_PLAYBACK_EDIT_G_RESID16, 0x6418)
        self.assertEqual(P320_DORMANT_BEAUTY_EFFECT_F_RESID16, 0x7849)
        self.assertEqual(P320_FX6_FLASH_BAND_REDUCE_2_RESID16, 0x4215)

    def test_04_init_exports_and_non_overlapping_master_57_registry(self) -> None:
        self.assertEqual(MASTER_57_PILLAR_COUNT, 57)
        self.assertEqual(len(MASTER_57_PILLAR_SPECS), 57)
        self.assertEqual(len(MASTER_57_PILLAR_IDS), 57)
        self.assertEqual(len(set(MASTER_57_PILLAR_IDS)), 57)
        self.assertEqual(
            MASTER_57_PILLAR_IDS[-1],
            "pillar_57_touch_disp_zero_evf_flash_interval_pb_vault",
        )
        self.assertIn("evaluate_realhw_57pillar_recovery_master", fx3_recovery.__all__)
        self.assertIn("evaluate_57pillar_recovery_master", fx3_recovery.__all__)
        self.assertIn("verify_57pillar_recovery_suite", fx3_recovery.__all__)
        self.assertIn("run_pillar57_standalone_suite", fx3_recovery.__all__)
        self.assertIn("MASTER_57_PILLAR_IDS", fx3_recovery.__all__)

    def test_05_safety_invariant_tamper_rejected_in_57a_and_57b(self) -> None:
        with mock.patch.object(p320, "PERSISTENT_EMMC_WRITES_AUTHORIZED", True):
            rep_a = evaluate_touch_disp_zero_evf_vault(
                build_default_safe_touch_disp_zero_evf_vault_spec()
            )
            rep_b = evaluate_still_ael_flash_interval_pb_edit_vault(
                build_default_safe_still_ael_flash_interval_pb_edit_vault_spec()
            )
        self.assertFalse(rep_a.passed)
        self.assertEqual(rep_a.block_code, P320_BLOCKED_SAFETY_POLICY_VIOLATION)
        self.assertFalse(rep_b.passed)
        self.assertEqual(rep_b.block_code, P320_BLOCKED_SAFETY_POLICY_VIOLATION)

    def test_06_invalid_57a_and_57b_spec_parameters_fail_closed(self) -> None:
        bad_a = evaluate_touch_disp_zero_evf_vault(
            build_default_safe_touch_disp_zero_evf_vault_spec(
                camera_model="ILCE-7M4",
                requested_vault_slot=9,
            )
        )
        bad_b = evaluate_still_ael_flash_interval_pb_edit_vault(
            build_default_safe_still_ael_flash_interval_pb_edit_vault_spec(
                shooting_domain="TimeLapse",
                target_write_slot=9,
            )
        )
        self.assertFalse(bad_a.passed)
        self.assertEqual(bad_a.block_code, P320_BLOCKED_INVALID_PILLAR57A_SPEC)
        self.assertFalse(bad_b.passed)
        self.assertEqual(bad_b.block_code, P320_BLOCKED_INVALID_PILLAR57B_SPEC)

    def test_07_donor_snapshot_bounded_readonly_and_17_artifacts(self) -> None:
        snap = inspect_phase320_donors_readonly()
        self.assertTrue(snap.all_donors_present)
        self.assertEqual(snap.donor_files_inspected, 17)
        self.assertEqual(len(snap.artifacts), 17)
        self.assertTrue(snap.under_0_20s_budget)
        self.assertLess(snap.elapsed_seconds, P320_DONOR_INSPECT_CI_BUDGET_SECONDS)
        self.assertEqual(snap.raw_firmware_bytes_leaked, 0)

    def test_08_donor_pinned_hashes_when_local_donors_present(self) -> None:
        snap = inspect_phase320_donors_readonly()
        if (
            _donor_appfw_present()
            and os.environ.get(p320.P320_ENV_CLEAN_ROOM_TEST, "") != "1"
            and os.environ.get("FX3_FX6_FORCE_CLEAN_ROOM", "") != "1"
        ):
            self.assertEqual(snap.verification_mode, "LOCAL_DONOR_O_RDONLY")
        by_id = {a.artifact_id: a for a in snap.artifacts}
        self.assertEqual(by_id["fx3_appfw_702_so"].total_bytes, P320_PINNED_FX3_APPFW_702_BYTES)
        self.assertEqual(
            by_id["fx3_appfw_702_so"].digest_sha256, P320_PINNED_FX3_APPFW_702_HDR4K_SHA256
        )
        self.assertEqual(by_id["fx6_appfw_601_so"].total_bytes, P320_PINNED_FX6_APPFW_601_BYTES)
        self.assertEqual(
            by_id["fx6_appfw_601_so"].digest_sha256, P320_PINNED_FX6_APPFW_601_HDR4K_SHA256
        )
        self.assertEqual(by_id["fx3_backup_bin"].total_bytes, P320_PINNED_FX3_BACKUP_BIN_BYTES)
        self.assertEqual(by_id["fx3_backup_bin"].digest_sha256, P320_PINNED_FX3_BACKUP_BIN_SHA256)
        self.assertEqual(by_id["fx3_uxc_en_f"].total_bytes, P320_PINNED_FX3_UXC_EN_F_BYTES)
        self.assertEqual(by_id["fx3_uxc_en_f"].digest_sha256, P320_PINNED_FX3_UXC_EN_F_SHA256)
        self.assertTrue(all(a.matches_pinned for a in snap.artifacts))
        if snap.verification_mode == "LOCAL_DONOR_O_RDONLY":
            self.assertEqual(by_id["fx3_appfw_702_so"].header_bytes_read, 4096)
            self.assertEqual(by_id["fx6_appfw_601_so"].header_bytes_read, 4096)

    def test_09_donor_inspection_force_clean_room_and_missing_work_root_none_guard(self) -> None:
        snap_forced = inspect_phase320_donors_readonly(force_clean_room=True)
        self.assertEqual(snap_forced.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(snap_forced.all_donors_present)
        self.assertEqual(snap_forced.donor_files_inspected, 17)
        with mock.patch.object(p320, "resolve_donor_path", return_value=None):
            snap_missing = inspect_phase320_donors_readonly(force_clean_room=False)
        self.assertEqual(snap_missing.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(snap_missing.all_donors_present)
        self.assertEqual(snap_missing.donor_files_inspected, 17)

    def test_10_env_clean_room_test_and_fx3_fx6_force_clean_room_honored(self) -> None:
        with mock.patch.dict(os.environ, {p320.P320_ENV_CLEAN_ROOM_TEST: "1"}, clear=False):
            snap = inspect_phase320_donors_readonly(force_clean_room=None)
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}, clear=False):
            snap2 = inspect_phase320_donors_readonly(force_clean_room=None)
        self.assertEqual(snap2.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_11_dual_mode_parity_standalone_suite(self) -> None:
        rep_cr = run_pillar57_standalone_suite(force_clean_room=True)
        rep_def = run_pillar57_standalone_suite()
        self.assertTrue(rep_cr.all_passed)
        self.assertTrue(rep_def.all_passed)
        self.assertEqual(rep_cr.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        if _donor_appfw_present():
            self.assertEqual(rep_def.verification_mode, "LOCAL_DONOR_O_RDONLY")
        self.assertEqual(
            [s.passed for s in rep_cr.pillar_57a_touch_disp_zero_evf_vault.scenarios],
            [s.passed for s in rep_def.pillar_57a_touch_disp_zero_evf_vault.scenarios],
        )
        self.assertEqual(
            [
                s.passed
                for s in rep_cr.pillar_57b_still_ael_flash_interval_pb_edit_vault.scenarios
            ],
            [
                s.passed
                for s in rep_def.pillar_57b_still_ael_flash_interval_pb_edit_vault.scenarios
            ],
        )

    def test_12_dual_mode_parity_master_57_verdicts(self) -> None:
        m_cr = evaluate_realhw_57pillar_recovery_master(force_clean_room=True)
        m_def = evaluate_realhw_57pillar_recovery_master()
        self.assertTrue(m_cr.all_passed)
        self.assertTrue(m_def.all_passed)
        self.assertEqual(m_cr.pillars_passed, 57)
        self.assertEqual(m_cr.pillar_count, 57)
        self.assertEqual(m_def.pillars_passed, 57)
        if _donor_appfw_present():
            self.assertEqual(m_def.verification_mode, "LOCAL_DONOR_O_RDONLY")
        self.assertEqual(
            [p.pillar_id for p in m_cr.pillars],
            [p.pillar_id for p in m_def.pillars],
        )


class TestPhase320SubPillar57ATouchDispZeroEvf(unittest.TestCase):
    """Wave-55 Touch Operation 4-item tree, DISP 4-shoot/3-PB & Zero-EVF Blackout Guard."""

    def test_13_touch_operation_4_items_and_defaults(self) -> None:
        self.assertEqual(
            P320_TOUCH_OPERATION_4_ITEMS,
            (
                "Touch Operation",
                "Touch Sensitivity",
                "Touch Func. in Shooting",
                "Swipe Up",
            ),
        )
        self.assertEqual(P320_TOUCH_OPERATION_DEFAULT, "On")
        self.assertEqual(P320_TOUCH_SENSITIVITY_DEFAULT, "Standard")
        self.assertEqual(P320_TOUCH_FUNC_SHOOTING_DEFAULT, "Touch Tracking")
        self.assertEqual(P320_SWIPE_UP_DEFAULT, "Open the Fn Menu")
        rep = evaluate_touch_disp_zero_evf_vault(
            build_default_safe_touch_disp_zero_evf_vault_spec()
        )
        self.assertTrue(rep.passed)
        self.assertEqual(rep.status, P320_STATUS_VERIFIED_PILLAR_57A)

    def test_14_touch_func_in_shooting_unified_across_still_movie_sq(self) -> None:
        for domain in ("Still", "Movie", "S&Q"):
            for func in ("Touch Focus", "Touch Tracking", "Off"):
                rep = evaluate_touch_disp_zero_evf_vault(
                    build_default_safe_touch_disp_zero_evf_vault_spec(
                        shooting_domain=domain,
                        touch_func_in_shooting=func,
                        post_touch_func_in_shooting=func,
                    )
                )
                self.assertTrue(rep.passed, f"failed for {domain}/{func}: {rep.errors}")
        self.assertEqual(
            P320_TOUCH_FUNC_RESID16_MAP,
            {
                "Touch Focus": (0x6E79, 0x7427),
                "Touch Tracking": (0x68F4, 0x69EE),
            },
        )

    def test_15_touch_operation_playback_only_and_off_deactivate_swipe_up(self) -> None:
        for mode in ("On: Playback Only", "Off"):
            rep = evaluate_touch_disp_zero_evf_vault(
                build_default_safe_touch_disp_zero_evf_vault_spec(
                    touch_operation=mode,
                    swipe_up="Open the Fn Menu",
                    reported_swipe_up_active=False,
                    post_touch_operation=mode,
                    post_swipe_up="Open the Fn Menu",
                )
            )
            self.assertTrue(rep.passed, f"{mode} failed: {rep.errors}")
            bad = evaluate_touch_disp_zero_evf_vault(
                build_default_safe_touch_disp_zero_evf_vault_spec(
                    touch_operation=mode,
                    reported_swipe_up_active=True,
                    post_touch_operation=mode,
                )
            )
            self.assertFalse(bad.passed)
            self.assertEqual(bad.block_code, P320_BLOCKED_TOUCH_4ITEM_DORMANT_OR_RESET_DRIFT)

    def test_16_touch_sensitivity_sensitive_accepted_responsive_rejected(self) -> None:
        ok = evaluate_touch_disp_zero_evf_vault(
            build_default_safe_touch_disp_zero_evf_vault_spec(
                touch_sensitivity="Sensitive",
                post_touch_sensitivity="Sensitive",
            )
        )
        self.assertTrue(ok.passed)
        bad = evaluate_touch_disp_zero_evf_vault(
            build_default_safe_touch_disp_zero_evf_vault_spec(
                touch_sensitivity=P320_TOUCH_SENSITIVITY_DORMANT_OR_WRONG,
                post_touch_sensitivity=P320_TOUCH_SENSITIVITY_DORMANT_OR_WRONG,
            )
        )
        self.assertFalse(bad.passed)
        self.assertEqual(bad.block_code, P320_BLOCKED_TOUCH_4ITEM_DORMANT_OR_RESET_DRIFT)

    def test_17_all_4_touch_items_survive_camera_settings_reset_and_network_reset(self) -> None:
        for reset_kind in ("Camera Settings Reset", "Reset Network Set."):
            rep = evaluate_touch_disp_zero_evf_vault(
                build_default_safe_touch_disp_zero_evf_vault_spec(
                    touch_operation="On: Playback Only",
                    touch_sensitivity="Sensitive",
                    touch_func_in_shooting="Touch Focus",
                    swipe_up="Off",
                    reported_swipe_up_active=False,
                    reset_action=reset_kind,
                    post_touch_operation="On: Playback Only",
                    post_touch_sensitivity="Sensitive",
                    post_touch_func_in_shooting="Touch Focus",
                    post_swipe_up="Off",
                )
            )
            self.assertTrue(rep.passed, f"{reset_kind} failed: {rep.errors}")

    def test_18_all_4_touch_items_reset_only_on_initialize(self) -> None:
        rep = evaluate_touch_disp_zero_evf_vault(
            build_default_safe_touch_disp_zero_evf_vault_spec(
                touch_operation="Off",
                touch_sensitivity="Sensitive",
                touch_func_in_shooting="Off",
                swipe_up="Off",
                reset_action="Initialize",
                reported_swipe_up_active=True,
                post_touch_operation=P320_TOUCH_OPERATION_DEFAULT,
                post_touch_sensitivity=P320_TOUCH_SENSITIVITY_DEFAULT,
                post_touch_func_in_shooting=P320_TOUCH_FUNC_SHOOTING_DEFAULT,
                post_swipe_up=P320_SWIPE_UP_DEFAULT,
            )
        )
        self.assertTrue(rep.passed)

    def test_19_touch_reset_drift_spoofing_camera_reset_wipe_rejected(self) -> None:
        bad = evaluate_touch_disp_zero_evf_vault(
            build_default_safe_touch_disp_zero_evf_vault_spec(
                touch_sensitivity="Sensitive",
                reset_action="Camera Settings Reset",
                post_touch_sensitivity="Standard",
            )
        )
        self.assertFalse(bad.passed)
        self.assertEqual(bad.block_code, P320_BLOCKED_TOUCH_4ITEM_DORMANT_OR_RESET_DRIFT)

    def test_20_all_7_dormant_alpha_touch_traps_enforce_eopnotsupp95(self) -> None:
        self.assertEqual(len(P320_DORMANT_TOUCH_TRAPS), 15)
        for trap in P320_DORMANT_TOUCH_TRAPS:
            rep = evaluate_touch_disp_zero_evf_vault(
                build_default_safe_touch_disp_zero_evf_vault_spec(
                    requested_dormant_touch_symbols=(trap,),
                    reported_dormant_touch_errno=P320_EOPNOTSUPP_ERRNO,
                )
            )
            self.assertTrue(rep.passed, f"rejected trap {trap} should pass with EOPNOTSUPP=95")
        self.assertEqual(P320_DORMANT_TOUCH_TRAP_RESID16_MAP["Touch Shutter"], 0x6A80)
        self.assertEqual(P320_DORMANT_TOUCH_TRAP_RESID16_MAP["Touch AE"], 0x702A)
        self.assertEqual(P320_DORMANT_TOUCH_TRAP_RESID16_MAP["Touch Panel/Pad"], 0x76EC)
        self.assertEqual(P320_DORMANT_TOUCH_TRAP_RESID16_MAP["Footer Icon Touch"], 0x70DA)

    def test_21_dormant_touch_trap_bypass_without_eopnotsupp95_rejected(self) -> None:
        bad = evaluate_touch_disp_zero_evf_vault(
            build_default_safe_touch_disp_zero_evf_vault_spec(
                requested_dormant_touch_symbols=("Touch Shutter", "Touch AE"),
                reported_dormant_touch_errno=None,
            )
        )
        self.assertFalse(bad.passed)
        self.assertEqual(bad.block_code, P320_BLOCKED_TOUCH_4ITEM_DORMANT_OR_RESET_DRIFT)

    def test_22_disp_set_exact_4_shoot_3_pb_pages_and_menu_path(self) -> None:
        self.assertEqual(P320_DISP_SET_MENU_PATH, ("Setup", "Operation Customize", "DISP (Screen Disp) Set"))
        self.assertEqual(P320_FX3_DISP_SHOOT_PAGE_COUNT, 4)
        self.assertEqual(P320_FX3_DISP_PLAY_PAGE_COUNT, 3)
        self.assertEqual(
            P320_DISP_SHOOT_4_PAGES,
            ("Display All Info.", "No Disp. Info.", "Histogram", "Level"),
        )
        self.assertEqual(
            P320_DISP_PLAY_3_PAGES,
            ("Display Info.", "Histogram", "No Disp. Info."),
        )
        self.assertEqual(P320_DISP_SHOOT_RESID16_MAP["Display All Info."], 0xEA0E)
        self.assertEqual(P320_DISP_SHOOT_RESID16_MAP["No Disp. Info."], 0xE9F9)
        self.assertEqual(P320_DISP_SHOOT_RESID16_MAP["Histogram"], 0xE07B)
        self.assertEqual(P320_DISP_SHOOT_RESID16_MAP["Level"], 0xE8BC)

    def test_23_disp_set_wrong_display_option_path_or_page_count_rejected(self) -> None:
        bad_path = evaluate_touch_disp_zero_evf_vault(
            build_default_safe_touch_disp_zero_evf_vault_spec(
                disp_set_menu_path=P320_DISP_SET_WRONG_PATH,
            )
        )
        bad_pages = evaluate_touch_disp_zero_evf_vault(
            build_default_safe_touch_disp_zero_evf_vault_spec(
                disp_shoot_pages_enabled=("Display All Info.", "Histogram"),
            )
        )
        self.assertFalse(bad_path.passed)
        self.assertEqual(bad_path.block_code, P320_BLOCKED_DISP_SET_4SHOOT_3PB_OR_PATH_DRIFT)
        self.assertFalse(bad_pages.passed)
        self.assertEqual(bad_pages.block_code, P320_BLOCKED_DISP_SET_4SHOOT_3PB_OR_PATH_DRIFT)

    def test_24_disp_set_initialize_only_survives_camera_reset(self) -> None:
        st = compute_expected_touch_disp_zero_evf_state(
            camera_model=P320_FX3_MODEL_NAME,
            shooting_domain="Movie",
            touch_operation="Off",
            touch_sensitivity="Sensitive",
            touch_func_in_shooting="Off",
            swipe_up="Off",
            requested_dormant_touch_symbols=(),
            disp_shoot_pages_enabled=("Display All Info.", "No Disp. Info.", "Histogram", "Level"),
            disp_play_pages_enabled=("Display Info.", "Histogram", "No Disp. Info."),
            requested_dormant_evf_symbols=(),
            reset_action="Camera Settings Reset",
        )
        self.assertEqual(st["post_disp_shoot_pages"], P320_DISP_SHOOT_4_PAGES)
        self.assertEqual(st["post_disp_play_pages"], P320_DISP_PLAY_3_PAGES)
        self.assertEqual(st["post_touch_operation"], "Off")

    def test_25_zero_evf_blackout_guard_enforces_eopnotsupp95_on_dormant_evf_traps(self) -> None:
        self.assertEqual(len(P320_DORMANT_EVF_OR_DISP_TRAPS), 12)
        for evf_trap in P320_DORMANT_EVF_OR_DISP_TRAPS:
            rep = evaluate_touch_disp_zero_evf_vault(
                build_default_safe_touch_disp_zero_evf_vault_spec(
                    requested_dormant_evf_symbols=(evf_trap,),
                    reported_dormant_evf_errno=P320_EOPNOTSUPP_ERRNO,
                    evf_scanout_blocked=True,
                    lcd_panel_scanout_preserved=True,
                )
            )
            self.assertTrue(rep.passed, f"EVF trap {evf_trap} should pass when EOPNOTSUPP=95")
        self.assertEqual(P320_DORMANT_EVF_TRAP_RESID16_MAP["Select Finder/Monitor"], 0x74F9)
        self.assertEqual(P320_DORMANT_EVF_TRAP_RESID16_MAP["Graphic Display"], 0xE07A)

    def test_26_zero_evf_blackout_guard_rejects_builtin_evf_eye_sensor_or_finder_route(self) -> None:
        for field in (
            {"fx3_has_builtin_evf": True},
            {"fx3_has_eye_sensor": True},
            {"fx3_has_finder_monitor_button": True},
            {"evf_scanout_blocked": False},
            {"lcd_panel_scanout_preserved": False},
            {"requested_dormant_evf_symbols": ("Monitor Off",), "reported_dormant_evf_errno": None},
        ):
            bad = evaluate_touch_disp_zero_evf_vault(
                build_default_safe_touch_disp_zero_evf_vault_spec(**field)
            )
            self.assertFalse(bad.passed, f"should reject {field}")
            self.assertEqual(bad.block_code, P320_BLOCKED_ZERO_EVF_BLACKOUT_GUARD_BREACH)

    def test_27_fx6_touch_operation_mf_only_and_detachable_lcd_viewfinder_contrast(self) -> None:
        self.assertEqual(
            P320_FX6_BUILTIN_EVF_ENUM,
            "VAL_FEATURE_MANAGER_builtin_evf_TYPE_BUILTIN_EVF_NOT_EXIST",
        )
        self.assertIn("Viewfinder", P320_FX6_DETACHABLE_LCD_TERMS)
        self.assertIn("Viewfinder Hood", P320_FX6_DETACHABLE_LCD_TERMS)
        self.assertEqual(P320_FX6_FORBIDDEN_LOUPE_TERM, "Loupe")
        self.assertEqual(P320_FX6_TOUCH_OPERATION_MODES, ("On", "Off"))
        self.assertEqual(P320_FX6_TOUCH_MF_MODES, ("Spot Focus", "Tracking AF"))
        ok_fx6 = evaluate_touch_disp_zero_evf_vault(
            build_default_safe_touch_disp_zero_evf_vault_spec(
                camera_model="ILME-FX6",
                fw_version="6.01",
                shooting_domain="Movie",
                touch_operation="On",
                touch_sensitivity="Standard",
                touch_func_in_shooting="Spot Focus",
                swipe_up="Off",
                reported_swipe_up_active=False,
                post_touch_operation="On",
                post_touch_sensitivity="N/A_FX6",
                post_touch_func_in_shooting="Spot Focus",
                post_swipe_up="N/A_FX6",
                disp_shoot_pages_enabled=(),
                disp_play_pages_enabled=(),
                post_disp_shoot_pages_enabled=(),
                post_disp_play_pages_enabled=(),
            )
        )
        self.assertTrue(ok_fx6.passed, ok_fx6.errors)

    def test_28_fx6_touch_sensitivity_or_loupe_spoof_rejected(self) -> None:
        bad = evaluate_touch_disp_zero_evf_vault(
            build_default_safe_touch_disp_zero_evf_vault_spec(
                camera_model="ILME-FX6",
                fw_version="6.01",
                shooting_domain="Movie",
                touch_operation="On",
                touch_func_in_shooting="Tracking AF",
                reported_swipe_up_active=False,
                post_touch_sensitivity="N/A_FX6",
                post_touch_func_in_shooting="Tracking AF",
                post_swipe_up="N/A_FX6",
                fx6_exposes_touch_sensitivity_or_swipe_up=True,
                fx6_uses_loupe_term=True,
            )
        )
        self.assertFalse(bad.passed)
        self.assertEqual(bad.block_code, P320_BLOCKED_FX6_TOUCH_OR_EVF_SPOOF)

    def test_29_57a_slot1_vault_format_and_edit_actions_blocked(self) -> None:
        for act in ("ROTATE", "PHOTO_CAPTURE", "COPY_TO_TARGET", "FORMAT_QUICK", "FORMAT_FULL"):
            bad = evaluate_touch_disp_zero_evf_vault(
                build_default_safe_touch_disp_zero_evf_vault_spec(
                    requested_vault_slot=1,
                    requested_vault_action=act,
                )
            )
            self.assertFalse(bad.passed)
            self.assertEqual(bad.block_code, P320_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL)

    def test_30_57a_persistent_overlay_escape_and_h0_h3_drift_blocked(self) -> None:
        bad_ov = evaluate_touch_disp_zero_evf_vault(
            build_default_safe_touch_disp_zero_evf_vault_spec(overlay_dir="/setting/touch")
        )
        bad_h3 = evaluate_touch_disp_zero_evf_vault(
            build_default_safe_touch_disp_zero_evf_vault_spec(
                backup_bin_h3_sha256="f" * 64,
                tier0_surfaces_h0_h3_matched=15,
            )
        )
        self.assertFalse(bad_ov.passed)
        self.assertEqual(bad_ov.block_code, P320_BLOCKED_PERSISTENT_OVERLAY_ESCAPE)
        self.assertFalse(bad_h3.passed)
        self.assertEqual(bad_h3.block_code, P320_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT)

    def test_31_pillar_57a_6_scenario_suite_passes(self) -> None:
        res = run_pillar57a_touch_disp_zero_evf_6_scenario_suite()
        self.assertTrue(res.passed)
        self.assertEqual(res.scenarios_passed, 6)
        self.assertEqual(res.scenarios_total, 6)
        self.assertEqual(res.status, P320_STATUS_VERIFIED_PILLAR_57A)
        self.assertTrue(all(s.passed for s in res.scenarios))

    def test_32_57a_negative_counters_nonzero_rejected(self) -> None:
        c1 = evaluate_touch_disp_zero_evf_vault(
            build_default_safe_touch_disp_zero_evf_vault_spec(
                touch_op_dormant_trap_or_reset_drift_events=1
            )
        )
        c2 = evaluate_touch_disp_zero_evf_vault(
            build_default_safe_touch_disp_zero_evf_vault_spec(
                disp_set_or_zero_evf_blackout_events=1
            )
        )
        c3 = evaluate_touch_disp_zero_evf_vault(
            build_default_safe_touch_disp_zero_evf_vault_spec(fx6_touch_or_evf_spoof_events=1)
        )
        self.assertFalse(c1.passed)
        self.assertFalse(c2.passed)
        self.assertFalse(c3.passed)
        self.assertEqual(c1.block_code, P320_BLOCKED_TOUCH_4ITEM_DORMANT_OR_RESET_DRIFT)
        self.assertEqual(c2.block_code, P320_BLOCKED_DISP_SET_4SHOOT_3PB_OR_PATH_DRIFT)
        self.assertEqual(c3.block_code, P320_BLOCKED_FX6_TOUCH_OR_EVF_SPOOF)

    def test_33_57a_matrix_states_and_zero_writes(self) -> None:
        rep = evaluate_touch_disp_zero_evf_vault(
            build_default_safe_touch_disp_zero_evf_vault_spec()
        )
        self.assertEqual(rep.matrix_states_checked, 18)
        self.assertEqual(rep.physical_device_writes, 0)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertEqual(len(rep.digest_sha256), 64)
        self.assertIsInstance(json.dumps(rep.to_dict()), str)

    def test_34_57a_touch_operation_on_playback_only_still_allows_valid_disp(self) -> None:
        rep = evaluate_touch_disp_zero_evf_vault(
            build_default_safe_touch_disp_zero_evf_vault_spec(
                shooting_domain="Still",
                touch_operation="On: Playback Only",
                swipe_up="Open the Fn Menu",
                reported_swipe_up_active=False,
                post_touch_operation="On: Playback Only",
                post_swipe_up="Open the Fn Menu",
            )
        )
        self.assertTrue(rep.passed)
        self.assertTrue(rep.disp_set_4shoot_3pb_and_path_verified)
        self.assertTrue(rep.zero_evf_blackout_guard_verified)


class TestPhase320SubPillar57BStillAelFlashIntervalPbEditVault(unittest.TestCase):
    """Still-only AEL/Flash reset split, 9-speed Interval PB & Edit Slot-1 EROFS=30 Vault."""

    def test_35_still_only_ael_w_shutter_auto_on_off_and_ael_toggle_override(self) -> None:
        self.assertEqual(P320_AEL_W_SHUTTER_MODES, ("Auto", "On", "Off"))
        self.assertEqual(P320_AEL_W_SHUTTER_DEFAULT, "Auto")
        self.assertEqual(P320_AEL_W_SHUTTER_BKID, "BKID_APP_setting_still_image_ael_w_shutter")
        for mode, expect_lock in (("Auto", True), ("On", True), ("Off", False)):
            rep = evaluate_still_ael_flash_interval_pb_edit_vault(
                build_default_safe_still_ael_flash_interval_pb_edit_vault_spec(
                    ael_w_shutter=mode,
                    post_ael_w_shutter=mode,
                    ael_toggle_key_active=False,
                    reported_half_press_ael_locked=expect_lock,
                )
            )
            self.assertTrue(rep.passed, f"AEL={mode} failed: {rep.errors}")
        # [AEL toggle] custom key overrides half-press AEL lock even when AEL w/ Shutter == On
        override = evaluate_still_ael_flash_interval_pb_edit_vault(
            build_default_safe_still_ael_flash_interval_pb_edit_vault_spec(
                ael_w_shutter="On",
                post_ael_w_shutter="On",
                ael_toggle_key_active=True,
                reported_half_press_ael_locked=False,
            )
        )
        self.assertTrue(override.passed)

    def test_36_still_only_ael_and_flash_gate_reject_movie_and_sq_with_eopnotsupp95(self) -> None:
        for dom in ("Movie", "S&Q"):
            ok = evaluate_still_ael_flash_interval_pb_edit_vault(
                build_default_safe_still_ael_flash_interval_pb_edit_vault_spec(
                    shooting_domain=dom,
                    reported_still_flash_errno=P320_EOPNOTSUPP_ERRNO,
                    reported_ext_flash_errno=P320_EOPNOTSUPP_ERRNO,
                    reported_half_press_ael_locked=False,
                )
            )
            self.assertTrue(ok.passed, f"domain {dom} gate failed: {ok.errors}")
            bad = evaluate_still_ael_flash_interval_pb_edit_vault(
                build_default_safe_still_ael_flash_interval_pb_edit_vault_spec(
                    shooting_domain=dom,
                    reported_still_flash_errno=None,
                    reported_half_press_ael_locked=False,
                )
            )
            self.assertFalse(bad.passed)
            self.assertEqual(bad.block_code, P320_BLOCKED_STILL_AEL_OR_FLASH_RESET_SPLIT_DRIFT)

    def test_37_asymmetric_camera_settings_reset_only_wireless_flash_resets(self) -> None:
        self.assertEqual(P320_EXP_COMP_SET_MODES, ("Ambient&flash", "Ambient only"))
        self.assertEqual(P320_EXP_COMP_SET_DEFAULT, "Ambient&flash")
        self.assertEqual(P320_EXP_COMP_SET_BKID, "BKID_APP_setting_exp_comp_set")
        self.assertEqual(
            P320_EXP_COMP_SET_F_RESID16_MAP,
            {"Ambient&flash": 0x6EFE, "Ambient only": 0x7617},
        )
        self.assertEqual(P320_WIRELESS_FLASH_BKID, "BKID_APP_setting_wireless_flash")
        self.assertEqual(P320_WIRELESS_FLASH_DEFAULT, "Off")
        # Camera Settings Reset resets ONLY Wireless Flash -> Off; AEL w/ Shutter & Exp.comp.set persist!
        ok_split = evaluate_still_ael_flash_interval_pb_edit_vault(
            build_default_safe_still_ael_flash_interval_pb_edit_vault_spec(
                ael_w_shutter="On",
                exp_comp_set="Ambient only",
                wireless_flash="On",
                reset_action="Camera Settings Reset",
                post_ael_w_shutter="On",
                post_exp_comp_set="Ambient only",
                post_wireless_flash="Off",
            )
        )
        self.assertTrue(ok_split.passed)
        # Spoofing Wireless Flash surviving Camera Settings Reset -> rejected
        bad_wf = evaluate_still_ael_flash_interval_pb_edit_vault(
            build_default_safe_still_ael_flash_interval_pb_edit_vault_spec(
                wireless_flash="On",
                reset_action="Camera Settings Reset",
                post_wireless_flash="On",
            )
        )
        # Spoofing AEL w/ Shutter wiping on Camera Settings Reset -> rejected
        bad_ael = evaluate_still_ael_flash_interval_pb_edit_vault(
            build_default_safe_still_ael_flash_interval_pb_edit_vault_spec(
                ael_w_shutter="On",
                reset_action="Camera Settings Reset",
                post_ael_w_shutter="Auto",
            )
        )
        self.assertFalse(bad_wf.passed)
        self.assertFalse(bad_ael.passed)
        self.assertEqual(bad_wf.block_code, P320_BLOCKED_STILL_AEL_OR_FLASH_RESET_SPLIT_DRIFT)
        self.assertEqual(bad_ael.block_code, P320_BLOCKED_STILL_AEL_OR_FLASH_RESET_SPLIT_DRIFT)

    def test_38_initialize_resets_all_4_still_ael_flash_and_interval_pb_items(self) -> None:
        ok = evaluate_still_ael_flash_interval_pb_edit_vault(
            build_default_safe_still_ael_flash_interval_pb_edit_vault_spec(
                ael_w_shutter="Off",
                exp_comp_set="Ambient only",
                wireless_flash="On",
                cont_play_for_interval="On",
                play_speed_for_interval=9,
                photo_capture_file_type="HEIF(4:2:2)",
                reset_action="Initialize",
                post_ael_w_shutter=P320_AEL_W_SHUTTER_DEFAULT,
                post_exp_comp_set=P320_EXP_COMP_SET_DEFAULT,
                post_wireless_flash=P320_WIRELESS_FLASH_DEFAULT,
                post_cont_play_for_interval="Off",
                post_play_speed_for_interval=P320_INTERVAL_PB_SPEED_DEFAULT,
                post_photo_capture_file_type=P320_PHOTO_CAPTURE_FILE_DEFAULT,
                reported_half_press_ael_locked=True,
            )
        )
        self.assertTrue(ok.passed)

    def test_39_external_flash_set_direct_mishoe_vs_sync_cord_and_menu_reset(self) -> None:
        self.assertEqual(
            P320_EXT_FLASH_SUBMENUS, ("Ext. Flash Firing Set.", "Ext. Flash Cust. Set.")
        )
        # Sync cord off-camera or camera-menu reset properly gated with EOPNOTSUPP=95 -> passes
        for kw in (
            {"ext_flash_direct_mishoe": False},
            {"ext_flash_sync_cord_requested": True},
            {"ext_flash_camera_menu_reset_requested": True},
        ):
            ok = evaluate_still_ael_flash_interval_pb_edit_vault(
                build_default_safe_still_ael_flash_interval_pb_edit_vault_spec(
                    reported_ext_flash_errno=P320_EOPNOTSUPP_ERRNO,
                    **kw,
                )
            )
            bad = evaluate_still_ael_flash_interval_pb_edit_vault(
                build_default_safe_still_ael_flash_interval_pb_edit_vault_spec(
                    reported_ext_flash_errno=None,
                    **kw,
                )
            )
            self.assertTrue(ok.passed)
            self.assertFalse(bad.passed)
            self.assertEqual(bad.block_code, P320_BLOCKED_EXT_FLASH_MISHOE_OR_FX6_SPOOF)

    def test_40_fx6_zero_ttl_flash_and_rolling_shutter_flash_band_reduce_contrast(self) -> None:
        ok_fx6 = evaluate_still_ael_flash_interval_pb_edit_vault(
            build_default_safe_still_ael_flash_interval_pb_edit_vault_spec(
                camera_model="ILME-FX6",
                fw_version="6.01",
                shooting_domain="Movie",
                reported_still_flash_errno=P320_EOPNOTSUPP_ERRNO,
                reported_ext_flash_errno=P320_EOPNOTSUPP_ERRNO,
                reported_half_press_ael_locked=False,
                post_ael_w_shutter="N/A_FX6",
                post_exp_comp_set="N/A_FX6",
                post_wireless_flash="N/A_FX6",
                post_cont_play_for_interval="N/A_FX6",
                post_play_speed_for_interval=0,
                post_photo_capture_file_type="N/A_FX6",
                reported_vault_action_allowed=False,
            )
        )
        bad_fx6 = evaluate_still_ael_flash_interval_pb_edit_vault(
            build_default_safe_still_ael_flash_interval_pb_edit_vault_spec(
                fx6_exposes_still_ttl_flash_or_ael=True,
                fx6_flash_band_reduce_is_rolling_shutter_comp=False,
            )
        )
        self.assertTrue(ok_fx6.passed, ok_fx6.errors)
        self.assertFalse(bad_fx6.passed)
        self.assertEqual(bad_fx6.block_code, P320_BLOCKED_EXT_FLASH_MISHOE_OR_FX6_SPOOF)

    def test_41_interval_pb_exact_9_speed_steps_default_5_under_playback_viewing(self) -> None:
        self.assertEqual(P320_INTERVAL_PB_MENU_PATH, ("Playback", "Viewing"))
        self.assertEqual(P320_INTERVAL_PB_WRONG_PATH, ("Playback", "Playback Option"))
        self.assertEqual(P320_FX3_INTERVAL_PB_SPEED_MIN, 1)
        self.assertEqual(P320_FX3_INTERVAL_PB_SPEED_MAX, 9)
        self.assertEqual(P320_INTERVAL_PB_SPEED_DEFAULT, 5)
        self.assertEqual(P320_INTERVAL_PB_SPEED_SCALE_9, tuple(range(1, 10)))
        self.assertEqual(P320_CONTINUOUS_PLAYBACK_BKID, "BKID_APP_setting_continuous_playback")
        self.assertEqual(P320_CONT_PB_LEGACY_F_RESID16, 0x72E6)
        self.assertEqual(P320_PB_SPEED_LEGACY_F_RESID16, 0x72BD)
        for spd in range(1, 10):
            rep = evaluate_still_ael_flash_interval_pb_edit_vault(
                build_default_safe_still_ael_flash_interval_pb_edit_vault_spec(
                    cont_play_for_interval="On",
                    play_speed_for_interval=spd,
                    post_cont_play_for_interval="On",
                    post_play_speed_for_interval=spd,
                    reset_action="Camera Settings Reset",
                )
            )
            self.assertTrue(rep.passed, f"speed={spd} failed: {rep.errors}")

    def test_42_interval_pb_rejects_5_scale_synthesis_wrong_path_and_oob_speed(self) -> None:
        for kw in (
            {"interval_pb_menu_path": P320_INTERVAL_PB_WRONG_PATH},
            {"play_speed_scale_max": 5},
            {"play_speed_for_interval": 10, "post_play_speed_for_interval": 10},
            {"play_speed_for_interval": 0, "post_play_speed_for_interval": 0},
            {"in_camera_timelapse_movie_synthesis_supported": True},
            {"interval_pb_read_only_safe": False},
        ):
            bad = evaluate_still_ael_flash_interval_pb_edit_vault(
                build_default_safe_still_ael_flash_interval_pb_edit_vault_spec(**kw)
            )
            self.assertFalse(bad.passed, f"should reject {kw}")
            self.assertEqual(bad.block_code, P320_BLOCKED_INTERVAL_PB_9SCALE_OR_PATH_DRIFT)

    def test_43_playback_edit_active_4_items_and_photo_capture_heif_types(self) -> None:
        self.assertEqual(
            P320_PLAYBACK_EDIT_ACTIVE_4_ITEMS,
            ("Rotate", "Photo Capture", "JPEG/HEIF Switch", "Copy"),
        )
        self.assertEqual(P320_PLAYBACK_EDIT_RESID16_MAP["Rotate"], 0xE5AE)
        self.assertEqual(P320_PLAYBACK_EDIT_RESID16_MAP["Photo Capture"], 0x6856)
        self.assertEqual(P320_PLAYBACK_EDIT_RESID16_MAP["JPEG/HEIF Switch"], 0x6938)
        self.assertEqual(P320_PLAYBACK_EDIT_RESID16_MAP["Copy"], 0x79FC)
        self.assertEqual(P320_PHOTO_CAPTURE_FILE_TYPES, ("JPEG", "HEIF(4:2:0)", "HEIF(4:2:2)"))
        for ftype in P320_PHOTO_CAPTURE_FILE_TYPES:
            for act in ("ROTATE", "PHOTO_CAPTURE", "COPY_TO_TARGET"):
                rep = evaluate_still_ael_flash_interval_pb_edit_vault(
                    build_default_safe_still_ael_flash_interval_pb_edit_vault_spec(
                        select_playback_media_slot=1,
                        target_write_slot=P320_SAFE_SECONDARY_SLOT,
                        photo_capture_file_type=ftype,
                        post_photo_capture_file_type=ftype,
                        requested_vault_action=act,
                        reported_vault_action_allowed=True,
                        vault_firewall_errno=None,
                    )
                )
                self.assertTrue(rep.passed, f"Slot 2 {act}/{ftype} failed: {rep.errors}")

    def test_44_critical_slot1_vault_erofs30_firewall_blocks_rotate_photocap_copy(self) -> None:
        self.assertEqual(P320_SELECT_PLAYBACK_MEDIA_DEFAULT_SLOT, 1)
        self.assertEqual(P320_SLOT1_VAULT_SLOT, 1)
        for act in ("ROTATE", "PHOTO_CAPTURE", "COPY_TO_TARGET", "FORMAT_QUICK", "FORMAT_FULL"):
            # Correctly refused with EROFS=30 and 0 writes -> passes
            ok = evaluate_still_ael_flash_interval_pb_edit_vault(
                build_default_safe_still_ael_flash_interval_pb_edit_vault_spec(
                    select_playback_media_slot=1,
                    target_write_slot=1,
                    requested_vault_action=act,
                    reported_vault_action_allowed=False,
                    vault_firewall_errno="EROFS",
                )
            )
            self.assertTrue(ok.passed, f"Slot 1 EROFS=30 check failed for {act}: {ok.errors}")
            # Bypassed or nonzero writes -> rejected!
            bad = evaluate_still_ael_flash_interval_pb_edit_vault(
                build_default_safe_still_ael_flash_interval_pb_edit_vault_spec(
                    select_playback_media_slot=1,
                    target_write_slot=1,
                    requested_vault_action=act,
                    reported_vault_action_allowed=True,
                    vault_firewall_errno=None,
                    slot1_data_sector_writes=4096,
                    slot1_avf_info_mutated=True,
                )
            )
            self.assertFalse(bad.passed)
            self.assertEqual(
                bad.block_code, P320_BLOCKED_PLAYBACK_EDIT_DORMANT_OR_SLOT1_VAULT_FIREWALL
            )

    def test_45_dormant_beauty_effect_and_trimming_enforced_eopnotsupp95_and_erofs30_on_slot1(
        self,
    ) -> None:
        self.assertEqual(
            P320_DORMANT_PLAYBACK_EDIT_TRAPS,
            (
                "Beauty Effect",
                "Trimming",
                "API_START_BEAUTYEFFECT_DETECTION",
                "sequence_edit_trimming_start",
            ),
        )
        for trap in ("BEAUTY_EFFECT", "TRIMMING"):
            # On Slot 2: EOPNOTSUPP=95
            ok_s2 = evaluate_still_ael_flash_interval_pb_edit_vault(
                build_default_safe_still_ael_flash_interval_pb_edit_vault_spec(
                    target_write_slot=2,
                    requested_vault_action=trap,
                    reported_vault_action_allowed=False,
                    vault_firewall_errno="EOPNOTSUPP",
                )
            )
            # On Slot 1: stacked EROFS=30
            ok_s1 = evaluate_still_ael_flash_interval_pb_edit_vault(
                build_default_safe_still_ael_flash_interval_pb_edit_vault_spec(
                    target_write_slot=1,
                    requested_vault_action=trap,
                    reported_vault_action_allowed=False,
                    vault_firewall_errno="EROFS",
                )
            )
            bad = evaluate_still_ael_flash_interval_pb_edit_vault(
                build_default_safe_still_ael_flash_interval_pb_edit_vault_spec(
                    target_write_slot=1,
                    requested_vault_action=trap,
                    reported_vault_action_allowed=True,
                    vault_firewall_errno=None,
                )
            )
            self.assertTrue(ok_s2.passed, ok_s2.errors)
            self.assertTrue(ok_s1.passed, ok_s1.errors)
            self.assertFalse(bad.passed)
            self.assertEqual(
                bad.block_code, P320_BLOCKED_PLAYBACK_EDIT_DORMANT_OR_SLOT1_VAULT_FIREWALL
            )

    def test_46_57b_persistent_overlay_escape_and_h0_h3_drift_blocked(self) -> None:
        bad_ov = evaluate_still_ael_flash_interval_pb_edit_vault(
            build_default_safe_still_ael_flash_interval_pb_edit_vault_spec(
                overlay_dir="/pnflasha/overlay"
            )
        )
        bad_h3 = evaluate_still_ael_flash_interval_pb_edit_vault(
            build_default_safe_still_ael_flash_interval_pb_edit_vault_spec(
                backup_bin_h3_sha256="1" * 64,
                tier0_surfaces_h0_h3_matched=14,
            )
        )
        self.assertFalse(bad_ov.passed)
        self.assertEqual(bad_ov.block_code, P320_BLOCKED_PERSISTENT_OVERLAY_ESCAPE)
        self.assertFalse(bad_h3.passed)
        self.assertEqual(bad_h3.block_code, P320_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT)

    def test_47_pillar_57b_6_scenario_suite_passes(self) -> None:
        res = run_pillar57b_still_ael_flash_interval_pb_edit_6_scenario_suite()
        self.assertTrue(res.passed)
        self.assertEqual(res.scenarios_passed, 6)
        self.assertEqual(res.scenarios_total, 6)
        self.assertEqual(res.status, P320_STATUS_VERIFIED_PILLAR_57B)
        self.assertTrue(all(s.passed for s in res.scenarios))

    def test_48_57b_negative_counters_nonzero_rejected(self) -> None:
        c1 = evaluate_still_ael_flash_interval_pb_edit_vault(
            build_default_safe_still_ael_flash_interval_pb_edit_vault_spec(
                still_ael_flash_reset_split_or_mishoe_drift_events=1
            )
        )
        c2 = evaluate_still_ael_flash_interval_pb_edit_vault(
            build_default_safe_still_ael_flash_interval_pb_edit_vault_spec(
                interval_pb_9scale_or_path_drift_events=1
            )
        )
        c3 = evaluate_still_ael_flash_interval_pb_edit_vault(
            build_default_safe_still_ael_flash_interval_pb_edit_vault_spec(
                playback_edit_dormant_or_slot1_vault_bypass_events=1
            )
        )
        self.assertFalse(c1.passed)
        self.assertFalse(c2.passed)
        self.assertFalse(c3.passed)
        self.assertEqual(c1.block_code, P320_BLOCKED_STILL_AEL_OR_FLASH_RESET_SPLIT_DRIFT)
        self.assertEqual(c2.block_code, P320_BLOCKED_INTERVAL_PB_9SCALE_OR_PATH_DRIFT)
        self.assertEqual(
            c3.block_code, P320_BLOCKED_PLAYBACK_EDIT_DORMANT_OR_SLOT1_VAULT_FIREWALL
        )

    def test_49_57b_matrix_states_and_zero_writes(self) -> None:
        rep = evaluate_still_ael_flash_interval_pb_edit_vault(
            build_default_safe_still_ael_flash_interval_pb_edit_vault_spec()
        )
        self.assertEqual(rep.matrix_states_checked, 18)
        self.assertEqual(rep.slot1_data_sector_writes, 0)
        self.assertEqual(rep.slot1_edit_avf_info_mutation_bytes, 0)
        self.assertFalse(rep.slot1_avf_info_mutated)
        self.assertEqual(rep.physical_device_writes, 0)
        self.assertEqual(len(rep.digest_sha256), 64)
        self.assertIsInstance(json.dumps(rep.to_dict()), str)

    def test_50_57b_photo_capture_file_type_survives_camera_reset(self) -> None:
        st = compute_expected_still_ael_flash_interval_pb_edit_vault_state(
            camera_model=P320_FX3_MODEL_NAME,
            shooting_domain="Still",
            ael_w_shutter="Off",
            ael_toggle_key_active=False,
            exp_comp_set="Ambient only",
            wireless_flash="On",
            ext_flash_direct_mishoe=True,
            ext_flash_sync_cord_requested=False,
            ext_flash_camera_menu_reset_requested=False,
            cont_play_for_interval="On",
            play_speed_for_interval=7,
            photo_capture_file_type="HEIF(4:2:2)",
            select_playback_media_slot=1,
            target_write_slot=2,
            slot1_holds_tier0_vault=True,
            requested_vault_action="PHOTO_CAPTURE",
            reset_action="Camera Settings Reset",
        )
        self.assertEqual(st["post_photo_capture_file_type"], "HEIF(4:2:2)")
        self.assertEqual(st["post_wireless_flash"], "Off")
        self.assertEqual(st["post_ael_w_shutter"], "Off")
        self.assertEqual(st["post_exp_comp_set"], "Ambient only")
        self.assertEqual(st["post_play_speed_for_interval"], 7)
        self.assertTrue(st["action_allowed"])
        self.assertIsNone(st["firewall_errno"])

    def test_51_57b_slot1_avf_info_mutated_flag_rejected(self) -> None:
        bad = evaluate_still_ael_flash_interval_pb_edit_vault(
            build_default_safe_still_ael_flash_interval_pb_edit_vault_spec(
                slot1_avf_info_mutated=True,
                slot1_edit_avf_info_mutation_bytes=512,
            )
        )
        self.assertFalse(bad.passed)
        self.assertEqual(
            bad.block_code, P320_BLOCKED_PLAYBACK_EDIT_DORMANT_OR_SLOT1_VAULT_FIREWALL
        )

    def test_52_57b_stage_b_volatile_overlay_accepts_run_and_tmp(self) -> None:
        for ov in ("/tmp/fx3_stageb_p320", "/run/fx3_stageb_p320"):
            rep = evaluate_still_ael_flash_interval_pb_edit_vault(
                build_default_safe_still_ael_flash_interval_pb_edit_vault_spec(overlay_dir=ov)
            )
            self.assertTrue(rep.passed, f"overlay {ov} failed: {rep.errors}")

    def test_53_57b_network_reset_preserves_ael_flash_and_interval_pb(self) -> None:
        rep = evaluate_still_ael_flash_interval_pb_edit_vault(
            build_default_safe_still_ael_flash_interval_pb_edit_vault_spec(
                ael_w_shutter="Off",
                exp_comp_set="Ambient only",
                wireless_flash="On",
                cont_play_for_interval="On",
                play_speed_for_interval=3,
                reset_action="Reset Network Set.",
                post_ael_w_shutter="Off",
                post_exp_comp_set="Ambient only",
                post_wireless_flash="On",
                post_cont_play_for_interval="On",
                post_play_speed_for_interval=3,
                reported_half_press_ael_locked=False,
            )
        )
        self.assertTrue(rep.passed, rep.errors)

    def test_54_57b_photo_capture_legacy_jpeg_heif_switch_resid16_constants(self) -> None:
        self.assertEqual(P320_PLAYBACK_EDIT_G_RESID16, 0x6418)
        self.assertEqual(P320_EXT_FLASH_SET_F_RESID16, 0x6771)
        self.assertEqual(P320_EXT_FLASH_FIRING_F_RESID16, 0x671D)
        self.assertEqual(P320_EXT_FLASH_CUST_F_RESID16, 0x705F)
        self.assertEqual(P320_CONT_PLAY_INTERVAL_F_RESID16, 0x78FA)
        self.assertEqual(P320_PLAY_SPEED_INTERVAL_F_RESID16, 0x639E)

    def test_55_57a_touch_func_resid16_and_swipe_up_resid16_constants(self) -> None:
        self.assertEqual(P320_SWIPE_UP_MODES := p320.P320_SWIPE_UP_MODES, ("Open the Fn Menu", "Off"))
        self.assertEqual(P320_TOUCH_FUNC_SHOOTING_F_RESID16, 0x7575)
        self.assertEqual(P320_SWIPE_UP_F_RESID16, 0x7518)
        self.assertEqual(P320_SWIPE_UP_FN_MENU_F_RESID16, 0x7281)

    def test_56_57b_slot2_rotate_and_copy_allowed_when_playback_media_is_slot1(self) -> None:
        for act in ("ROTATE", "COPY_TO_TARGET"):
            rep = evaluate_still_ael_flash_interval_pb_edit_vault(
                build_default_safe_still_ael_flash_interval_pb_edit_vault_spec(
                    select_playback_media_slot=1,
                    target_write_slot=2,
                    requested_vault_action=act,
                    reported_vault_action_allowed=True,
                    vault_firewall_errno=None,
                )
            )
            self.assertTrue(rep.passed, rep.errors)

    def test_57_57b_slot1_write_mutation_rejected_even_if_select_playback_media_is_slot2(self) -> None:
        bad = evaluate_still_ael_flash_interval_pb_edit_vault(
            build_default_safe_still_ael_flash_interval_pb_edit_vault_spec(
                select_playback_media_slot=2,
                target_write_slot=1,
                requested_vault_action="ROTATE",
                reported_vault_action_allowed=True,
                vault_firewall_errno=None,
            )
        )
        self.assertFalse(bad.passed)
        self.assertEqual(
            bad.block_code, P320_BLOCKED_PLAYBACK_EDIT_DORMANT_OR_SLOT1_VAULT_FIREWALL
        )

    def test_58_57b_wireless_flash_reset_drift_in_camera_reset_rejected(self) -> None:
        bad = evaluate_still_ael_flash_interval_pb_edit_vault(
            build_default_safe_still_ael_flash_interval_pb_edit_vault_spec(
                wireless_flash="On",
                exp_comp_set="Ambient only",
                reset_action="Camera Settings Reset",
                post_wireless_flash="Off",
                post_exp_comp_set="Ambient&flash",  # Exp.comp.set must NOT reset on Camera Settings Reset!
            )
        )
        self.assertFalse(bad.passed)
        self.assertEqual(bad.block_code, P320_BLOCKED_STILL_AEL_OR_FLASH_RESET_SPLIT_DRIFT)

    def test_59_57a_touch_operation_on_enables_swipe_up_in_still_movie_sq(self) -> None:
        for dom in ("Still", "Movie", "S&Q"):
            st = compute_expected_touch_disp_zero_evf_state(
                camera_model=P320_FX3_MODEL_NAME,
                shooting_domain=dom,
                touch_operation="On",
                touch_sensitivity="Standard",
                touch_func_in_shooting="Touch Tracking",
                swipe_up="Open the Fn Menu",
                requested_dormant_touch_symbols=(),
                disp_shoot_pages_enabled=P320_DISP_SHOOT_4_PAGES,
                disp_play_pages_enabled=P320_DISP_PLAY_3_PAGES,
                requested_dormant_evf_symbols=(),
                reset_action="None",
            )
            self.assertTrue(st["swipe_up_active"])

    def test_60_57b_interval_pb_survives_camera_reset_even_with_max_speed_9(self) -> None:
        rep = evaluate_still_ael_flash_interval_pb_edit_vault(
            build_default_safe_still_ael_flash_interval_pb_edit_vault_spec(
                cont_play_for_interval="On",
                play_speed_for_interval=9,
                reset_action="Camera Settings Reset",
                post_cont_play_for_interval="On",
                post_play_speed_for_interval=9,
            )
        )
        self.assertTrue(rep.passed)

    def test_61_57a_fx3_supported_fw_versions_include_200_through_702(self) -> None:
        for ver in ("2.00", "3.00", "6.00", "6.02", "7.00", "7.02"):
            rep = evaluate_touch_disp_zero_evf_vault(
                build_default_safe_touch_disp_zero_evf_vault_spec(fw_version=ver)
            )
            self.assertTrue(rep.passed, f"fw={ver} failed: {rep.errors}")

    def test_62_57b_fx3_supported_fw_versions_include_200_through_702(self) -> None:
        for ver in ("2.00", "3.00", "6.00", "6.02", "7.00", "7.02"):
            rep = evaluate_still_ael_flash_interval_pb_edit_vault(
                build_default_safe_still_ael_flash_interval_pb_edit_vault_spec(fw_version=ver)
            )
            self.assertTrue(rep.passed, f"fw={ver} failed: {rep.errors}")

    def test_63_57a_slot2_read_only_audit_allowed(self) -> None:
        rep = evaluate_touch_disp_zero_evf_vault(
            build_default_safe_touch_disp_zero_evf_vault_spec(
                requested_vault_slot=2,
                requested_vault_action="READ_ONLY_AUDIT",
            )
        )
        self.assertTrue(rep.passed)

    def test_64_57b_slot1_vault_erofs_ebusy_codes_defined(self) -> None:
        self.assertEqual(P320_EROFS_ERRNO, 30)
        self.assertEqual(p320.P320_VAULT_FIREWALL_ERRNO_CODES["EROFS"], 30)
        self.assertEqual(p320.P320_VAULT_FIREWALL_ERRNO_CODES["EOPNOTSUPP"], 95)
        self.assertEqual(p320.P320_VAULT_FIREWALL_ERRNO_CODES["EBUSY"], 16)

    def test_65_57a_swipe_left_right_rejected_with_eopnotsupp95(self) -> None:
        ok = evaluate_touch_disp_zero_evf_vault(
            build_default_safe_touch_disp_zero_evf_vault_spec(
                requested_dormant_touch_symbols=("Swipe Left", "Swipe Right"),
                reported_dormant_touch_errno=P320_EOPNOTSUPP_ERRNO,
            )
        )
        self.assertTrue(ok.passed)

    def test_66_57b_half_press_ael_lock_mismatch_rejected(self) -> None:
        bad = evaluate_still_ael_flash_interval_pb_edit_vault(
            build_default_safe_still_ael_flash_interval_pb_edit_vault_spec(
                ael_w_shutter="On",
                ael_toggle_key_active=True,
                reported_half_press_ael_locked=True,  # toggle must override half-press AEL lock!
            )
        )
        self.assertFalse(bad.passed)
        self.assertEqual(bad.block_code, P320_BLOCKED_STILL_AEL_OR_FLASH_RESET_SPLIT_DRIFT)

    def test_67_57a_for_viewfinder_and_graphic_display_dormant_traps(self) -> None:
        self.assertEqual(P320_DORMANT_EVF_TRAP_RESID16_MAP["For viewfinder"], 0x62D3)
        self.assertEqual(P320_DORMANT_EVF_TRAP_RESID16_MAP["DISP Button:Finder"], 0x6B57)
        ok = evaluate_touch_disp_zero_evf_vault(
            build_default_safe_touch_disp_zero_evf_vault_spec(
                requested_dormant_evf_symbols=("For viewfinder", "Graphic Display"),
                reported_dormant_evf_errno=P320_EOPNOTSUPP_ERRNO,
            )
        )
        self.assertTrue(ok.passed)

    def test_68_57b_playback_edit_copy_on_slot1_even_when_denied_fails_if_writes_nonzero(self) -> None:
        bad = evaluate_still_ael_flash_interval_pb_edit_vault(
            build_default_safe_still_ael_flash_interval_pb_edit_vault_spec(
                target_write_slot=1,
                requested_vault_action="COPY_TO_TARGET",
                reported_vault_action_allowed=False,
                vault_firewall_errno="EROFS",
                slot1_data_sector_writes=512,
            )
        )
        self.assertFalse(bad.passed)
        self.assertEqual(
            bad.block_code, P320_BLOCKED_PLAYBACK_EDIT_DORMANT_OR_SLOT1_VAULT_FIREWALL
        )


class TestPhase320StandaloneMasterAndCli(unittest.TestCase):
    """Combined single-shot verifier, 57/57 recovery master, CLI & discovery."""

    def test_69_single_shot_combined_verifiers_both_modes(self) -> None:
        for forced in (True, None):
            r1 = verify_touch_disp_zero_evf_flash_interval_pb_and_vault(force_clean_room=forced)
            r2 = verify_touch_disp_zero_evf_flash_interval_pb_vault(force_clean_room=forced)
            self.assertTrue(r1.all_passed)
            self.assertTrue(r2.all_passed)
            self.assertEqual(r1.status, P320_STATUS_VERIFIED_PILLAR57_SUITE)
            self.assertEqual(r1.raw_firmware_bytes_leaked, 0)

    def test_70_standalone_suite_sha256_deterministic_per_mode(self) -> None:
        a = run_pillar57_standalone_suite(force_clean_room=True)
        b = run_pillar57_standalone_suite(force_clean_room=True)
        self.assertTrue(a.all_passed)
        self.assertEqual(a.suite_sha256, b.suite_sha256)
        self.assertEqual(len(a.suite_sha256), 64)

    def test_71_master_57pillar_aggregates_56pillar_plus_pillar57(self) -> None:
        m56 = evaluate_realhw_56pillar_recovery_master(force_clean_room=True)
        m57 = evaluate_realhw_57pillar_recovery_master(force_clean_room=True)
        self.assertTrue(m56.all_passed)
        self.assertTrue(m57.all_passed)
        self.assertEqual(m57.schema_version, "realhw_57pillar_recovery_master_v1")
        self.assertEqual(m57.status, P320_STATUS_VERIFIED_57OF57_AGGREGATOR)
        self.assertEqual(m57.pillar_count, 57)
        self.assertEqual(m57.pillars_passed, 57)
        self.assertEqual(len(m57.pillars), 57)
        self.assertEqual(
            m57.pillars[-1].pillar_id,
            "pillar_57_touch_disp_zero_evf_flash_interval_pb_vault",
        )
        self.assertEqual(
            [p.pillar_id for p in m57.pillars[:56]],
            [p.pillar_id for p in m56.pillars],
        )

    def test_72_master_57_aliases_consistent(self) -> None:
        r1 = evaluate_realhw_57pillar_recovery_master(force_clean_room=True)
        r2 = evaluate_57pillar_recovery_master(force_clean_room=True)
        r3 = verify_57pillar_recovery_suite(force_clean_room=True)
        self.assertEqual(r1.master_57pillar_sha256, r2.master_57pillar_sha256)
        self.assertEqual(r1.master_57pillar_sha256, r3.master_57pillar_sha256)
        self.assertEqual(r1.pillars_passed, r2.pillars_passed)

    def test_73_master_57_latency_budgets_met_in_both_modes(self) -> None:
        for forced in (True, None):
            rep = evaluate_realhw_57pillar_recovery_master(force_clean_room=forced)
            self.assertTrue(rep.under_1_5s_fast_cli_budget, f"elapsed={rep.elapsed_seconds}")
            self.assertLess(rep.elapsed_seconds, P320_FAST_CLI_BUDGET_SECONDS)
            self.assertTrue(rep.under_2_5s_fast_cli_budget)
            self.assertTrue(rep.nominal_under_4_0s)
            self.assertTrue(rep.under_6s_budget)

    def test_74_master_57_zero_risk_and_wave55_counters(self) -> None:
        rep = evaluate_realhw_57pillar_recovery_master(force_clean_room=True)
        self.assertEqual(rep.touch_op_dormant_trap_or_reset_drift_events, 0)
        self.assertEqual(rep.disp_set_or_zero_evf_blackout_events, 0)
        self.assertEqual(rep.fx6_touch_or_evf_spoof_events, 0)
        self.assertEqual(rep.still_ael_flash_reset_split_or_mishoe_drift_events, 0)
        self.assertEqual(rep.interval_pb_9scale_or_path_drift_events, 0)
        self.assertEqual(rep.playback_edit_dormant_or_slot1_vault_bypass_events, 0)
        self.assertEqual(rep.slot1_data_sector_writes, 0)
        self.assertEqual(rep.slot1_edit_avf_info_mutation_bytes, 0)
        self.assertFalse(rep.slot1_avf_info_mutated)
        self.assertEqual(rep.slot1_vault_mutation_bytes, 0)
        self.assertTrue(rep.slot1_format_hard_locked)
        self.assertTrue(rep.slot1_vault_erofs_eopnotsupp_enforced)
        self.assertFalse(rep.fx3_has_eye_sensor)
        self.assertFalse(rep.fx3_has_finder_monitor_button)
        self.assertEqual(rep.fx3_touch_active_item_count, 4)
        self.assertEqual(rep.fx3_disp_shoot_page_count, 4)
        self.assertEqual(rep.fx3_disp_play_page_count, 3)
        self.assertEqual(rep.fx3_interval_pb_speed_min, 1)
        self.assertEqual(rep.fx3_interval_pb_speed_max, 9)
        self.assertEqual(rep.fx3_interval_pb_speed_default, 5)
        self.assertTrue(rep.fx6_has_detachable_lcd_viewfinder)
        self.assertFalse(rep.fx6_has_still_ttl_flash)
        self.assertFalse(rep.fx6_has_interval_pb)
        self.assertFalse(rep.fx6_has_playback_edit_menu)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.cross_model_flash_authorized)
        self.assertFalse(rep.hardware_live_attachment_authorized)
        self.assertTrue(rep.cnflasha_userspace_write_blocked)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_75_master_57_fault_injection_p57_fails_deterministically(self) -> None:
        rep = evaluate_realhw_57pillar_recovery_master(
            force_clean_room=True,
            fault_inject_pillar="pillar_57_touch_disp_zero_evf_flash_interval_pb_vault",
        )
        self.assertFalse(rep.all_passed)
        self.assertEqual(rep.status, P320_STATUS_FAIL_57OF57_AGGREGATOR)
        self.assertEqual(rep.pillars_passed, 56)
        self.assertIn("pillar_57_touch_disp_zero_evf_flash_interval_pb_vault", rep.failed_pillars)

    def test_76_master_57_fault_injection_p1_and_unknown_pillar(self) -> None:
        rep = evaluate_realhw_57pillar_recovery_master(
            force_clean_room=True,
            fault_inject_pillar=MASTER_57_PILLAR_IDS[0],
        )
        self.assertFalse(rep.all_passed)
        self.assertLess(rep.pillars_passed, 57)
        self.assertIn(MASTER_57_PILLAR_IDS[0], rep.failed_pillars)
        with self.assertRaises(ValueError):
            evaluate_realhw_57pillar_recovery_master(
                force_clean_room=True,
                fault_inject_pillar="P999_UNKNOWN",
            )

    def test_77_master_57_safety_tamper_fails(self) -> None:
        with mock.patch.object(p320, "RAW_FIRMWARE_BYTES_LEAKED", 64):
            with self.assertRaises(ValueError):
                evaluate_realhw_57pillar_recovery_master(force_clean_room=True)

    def test_78_master_57_json_serialization_no_nan(self) -> None:
        rep = evaluate_realhw_57pillar_recovery_master(force_clean_room=True)
        encoded = json.dumps(rep.to_dict(), allow_nan=False, sort_keys=True)
        decoded = json.loads(encoded)
        self.assertEqual(decoded["pillar_count"], 57)
        self.assertEqual(decoded["pillars_passed"], 57)

    def test_79_cli_inprocess_pillar57_standalone_json(self) -> None:
        buf = io.StringIO()
        with mock.patch.object(
            sys,
            "argv",
            [
                "fx3_recovery",
                "verify-pillar57-touch-disp-zero-evf-flash-interval-pb-vault",
                "--force-clean-room",
                "--json",
            ],
        ), redirect_stdout(buf):
            rc = cli_main.main()
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())
        self.assertTrue(payload["all_passed"])
        self.assertEqual(payload["verification_mode"], "CLEAN_ROOM_SYNTHETIC")

    def test_80_cli_inprocess_verify_57pillar_recovery_json_and_out_file(self) -> None:
        work_tests = REPO_ROOT / "work" / "_tests"
        work_tests.mkdir(parents=True, exist_ok=True)
        out_dir = Path(tempfile.mkdtemp(prefix="p320_m57_", dir=str(work_tests)))
        shutil.rmtree(out_dir)
        try:
            buf = io.StringIO()
            with mock.patch.object(
                sys,
                "argv",
                [
                    "fx3_recovery",
                    "verify-57pillar-recovery",
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
            self.assertEqual(payload["pillars_passed"], 57)
            report_file = out_dir / "57pillar-recovery-master-report.json"
            self.assertTrue(report_file.exists())
            file_payload = json.loads(report_file.read_text(encoding="utf-8"))
            self.assertEqual(file_payload["master_57pillar_sha256"], payload["master_57pillar_sha256"])
        finally:
            shutil.rmtree(out_dir, ignore_errors=True)

    def test_81_cli_inprocess_pillar57_out_file(self) -> None:
        work_tests = REPO_ROOT / "work" / "_tests"
        work_tests.mkdir(parents=True, exist_ok=True)
        out_dir = Path(tempfile.mkdtemp(prefix="p320_p57_", dir=str(work_tests)))
        shutil.rmtree(out_dir)
        try:
            buf = io.StringIO()
            with mock.patch.object(
                sys,
                "argv",
                [
                    "fx3_recovery",
                    "verify-pillar57-touch-disp-zero-evf-flash-interval-pb-vault",
                    "--force-clean-room",
                    "--out",
                    str(out_dir),
                ],
            ), redirect_stdout(buf):
                rc = cli_main.main()
            self.assertEqual(rc, 0, buf.getvalue())
            self.assertIn("status=VERIFIED_PILLAR57_TOUCH_DISP_ZERO_EVF_FLASH_INTERVAL_PB_VAULT", buf.getvalue())
            report_file = out_dir / "pillar57-touch-disp-zero-evf-flash-interval-pb-vault-report.json"
            self.assertTrue(report_file.exists())
        finally:
            shutil.rmtree(out_dir, ignore_errors=True)

    def test_82_cli_inprocess_human_readable_summary_exits_zero(self) -> None:
        buf = io.StringIO()
        with mock.patch.object(
            sys,
            "argv",
            ["fx3_recovery", "verify-57pillar-recovery", "--force-clean-room"],
        ), redirect_stdout(buf):
            rc = cli_main.main()
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("status=VERIFIED_57OF57_PILLAR_RECOVERY_MASTER", out)
        self.assertIn("pillars=57/57", out)
        self.assertIn("raw_firmware_bytes_leaked=0", out)

    def test_83_cli_subprocess_help_uses_sys_executable(self) -> None:
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
        self.assertIn("verify-57pillar-recovery", proc.stdout)
        self.assertIn("verify-pillar57-touch-disp-zero-evf-flash-interval-pb-vault", proc.stdout)

    def test_84_cli_subprocess_verify_57pillar_recovery_clean_room_json(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "fx3_recovery",
                "verify-57pillar-recovery",
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
        self.assertEqual(payload["pillars_passed"], 57)
        self.assertEqual(payload["verification_mode"], "CLEAN_ROOM_SYNTHETIC")

    def test_85_cli_subprocess_pillar57_fx3_clean_room_test_env_json(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "fx3_recovery",
                "verify-pillar57-touch-disp-zero-evf-flash-interval-pb-vault",
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

    def test_86_cli_subprocess_fx3_fx6_force_clean_room_env_57pillar(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "fx3_recovery",
                "verify-57pillar-recovery",
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
        self.assertEqual(payload["pillars_passed"], 57)
        self.assertEqual(payload["verification_mode"], "CLEAN_ROOM_SYNTHETIC")

    def test_87_cli_subprocess_default_mode_exits_zero(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "fx3_recovery",
                "verify-57pillar-recovery",
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
        self.assertGreaterEqual(payload["pillar_count"], 57)
        self.assertGreaterEqual(payload["pillars_passed"], 57)
        self.assertEqual(payload["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(payload["slot1_data_sector_writes"], 0)

    def test_88_cli_subprocess_pillar57_default_mode_exits_zero(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "fx3_recovery",
                "verify-pillar57-touch-disp-zero-evf-flash-interval-pb-vault",
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
        self.assertEqual(payload["raw_firmware_bytes_leaked"], 0)

    def test_89_cli_subprocess_pillar57_help_succeeds(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "fx3_recovery",
                "verify-pillar57-touch-disp-zero-evf-flash-interval-pb-vault",
                "--help",
            ],
            cwd=str(REPO_ROOT),
            env=_clean_env(),
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("--force-clean-room", proc.stdout)

    def test_90_forward_compatible_discovery_in_fx3_recovery(self) -> None:
        discovered = [
            int(name[len("evaluate_realhw_") : -len("pillar_recovery_master")])
            for name in dir(fx3_recovery)
            if name.startswith("evaluate_realhw_") and name.endswith("pillar_recovery_master")
        ]
        self.assertGreaterEqual(max(discovered), 57)
        self.assertIn(57, discovered)
        self.assertGreaterEqual(len(fx3_recovery.MASTER_57_PILLAR_IDS), 57)


if __name__ == "__main__":
    unittest.main()
