"""Phase 314 — Dual-mode unit tests for Recovery Pillar 56 & Unified 56/56 Recovery Master.

Covers:
1. Sub-Pillar 56A:
   - Still `AF-C`-only `[Switch V/H AF Area]` (`_f.uxc 0x73ae`, `Off` / `AF Point Only` `0x615a` /
     `AF Point + AF Area` `0x69e8`): `0_DEGREES`/`90_DEGREES`/`270_DEGREES` vs vertical pitch
     `INVALID`, all 8 lockout conditions (`EBUSY=16`), remembered coords clear on option change,
     and reset on `[Camera Settings Reset]`.
   - `[Focus Area Limit]` (`_f.uxc 0x6de2`): exact 14 `BKID_APP_focus_area_limit_*` checkboxes
     (7 non-tracking + 7 Still-only `Tracking:*`), `>= 2` floor (`.uxc 0xea28 -> EINVAL=22`),
     Movie/`S&Q` `Tracking:` exclusion, and dormant BIONZ XR symbols `flexible_spot_{xl,xs}` /
     `custom_{1..3}` rejected with `EOPNOTSUPP=95`.
   - `Initialize`-only `[Focus Area Color]` (`_f.uxc 0x74ad`, `White` `.uxc 0xe883` / `Red`
     `.uxc 0xe8c6`) contrasted with zero-switch `ILME-FX6` (no `Switch V/H AF Area`, no `Focus
     Area Limit`, orange moving AF frame + `Focus Area Ind.(AF-S)` `0x2236`).
2. Sub-Pillar 56B:
   - `[Exposure Std. Adjust]` (`_f.uxc 0x6114`, `.uxc 0xe567`): all **5** metering modes (`Multi`
     `0x6d79`, `Center` `0x6da8`, `Spot` `0x7a8a`, `Entire Screen Avg.` `0x6f15`, `Highlight`
     `0x7600`) across 13 `1/6 EV` steps (`-1..+1 EV`), EXIF isolation (`[Exposure Comp.]`
     unchanged), `M.M.` baseline shift, mid-bracket shot count reset, and `Initialize`-only reset
     vs `[Bracket Settings]` (`Camera Settings Reset` resettable) & dormant FX6 (`ENOENT=2`).
   - All 6 `MENU -> Shooting -> [TC/UB]` items + `Setup -> Display Option -> [TC/UB Disp. Setting]`
     (`Counter`/`TC`/`U-Bit`, movie-playback-only toggle `.uxc 0xe728`) surviving `[Camera Settings
     Reset]` (`Initialize`-only); `[Time Code Format]` (`DF`/`NDF`) NTSC-only, forced `NDF` (`[-]`)
     at `23.98p`/`24.00p`, hidden in `PAL`; contrasted with FX6 physical BNC `TC IN/OUT` (`EXT-LK`).
   - CRITICAL Fail-Closed Reverse `Slot-2 -> Slot-1` `[Copy]` (`FUNC_copy_content`) Tier-0 Vault
     Firewall (`EROFS=30` / `EBUSY=16`, `slot1_data_sector_writes == 0`,
     `slot1_copy_avf_info_mutation_bytes == 0`) vs safe `Slot-1 -> Slot-2` copy (clears group &
     `Protect` on destination) + `[Slide Show]` (`Repeat: Off`, `Interval: 1/3/5/10/30 Sec` default
     `3 Sec`, `[Power Save Start Time]` bypass) & dormant FX6 `Copy Clip`.
3. Unified `56/56` Recovery Master (`evaluate_realhw_56pillar_recovery_master` / CLI).
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
    realhw_56pillar_switch_vh_af_stdadj_tcub_copy_vault_verifier as p314,
)
from fx3_recovery.realhw_55pillar_lens_comp_af_illuminator_folder_rating_vault_verifier import (
    evaluate_realhw_55pillar_recovery_master,
)
from fx3_recovery.realhw_56pillar_switch_vh_af_stdadj_tcub_copy_vault_verifier import (
    ALLOW_BOOT_PARTITION_TARGETING,
    ALLOW_DESTRUCTIVE_FASTBOOT,
    ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS,
    ALLOW_PERSISTENT_JIRITSU_WRITES,
    CROSS_MODEL_FLASH_AUTHORIZED,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    ISP_WRITE_AUTHORIZED,
    LIVE_USB_IOKIT_TRANSMIT_ENABLED,
    MASTER_56_PILLAR_COUNT,
    MASTER_56_PILLAR_IDS,
    MASTER_56_PILLAR_SPECS,
    OTP_FUSE_TOUCHES,
    OTP_FUSE_WRITES,
    OVERALL_READY_FOR_HARDWARE_ATTACH,
    P314_BLOCKED_EXP_STD_ADJ_5MODE_OR_BRACKET_DRIFT,
    P314_BLOCKED_FOCUS_AREA_COLOR_OR_FX6_SPOOF,
    P314_BLOCKED_FOCUS_AREA_LIMIT_LT2_OR_DORMANT_SYMBOL,
    P314_BLOCKED_INVALID_PILLAR56A_SPEC,
    P314_BLOCKED_INVALID_PILLAR56B_SPEC,
    P314_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
    P314_BLOCKED_REVERSE_COPY_SLOT2_TO_SLOT1_VAULT_FIREWALL,
    P314_BLOCKED_SAFETY_POLICY_VIOLATION,
    P314_BLOCKED_SLIDESHOW_POWER_SAVE_OR_FX6_COPY_CLIP_SPOOF,
    P314_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL,
    P314_BLOCKED_SWITCH_VH_AF_LOCKOUT_OR_COORDS_DRIFT,
    P314_BLOCKED_TCUB_INIT_RESET_OR_FORMAT_LOCK_DRIFT,
    P314_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
    P314_BRACKET_ORDER_DEFAULT,
    P314_BRACKET_ORDER_MODES,
    P314_BRACKET_SELFTIMER_DEFAULT,
    P314_BRACKET_SELFTIMER_MODES,
    P314_COPY_FAIL_RESID16,
    P314_COPY_FUNC_SYMBOL,
    P314_COPY_F_RESID16,
    P314_DONOR_INSPECT_BUDGET_SECONDS,
    P314_DONOR_INSPECT_CI_BUDGET_SECONDS,
    P314_EBUSY_ERRNO,
    P314_EINVAL_ERRNO,
    P314_ENOENT_ERRNO,
    P314_ENV_CLEAN_ROOM_TEST,
    P314_EOPNOTSUPP_ERRNO,
    P314_EROFS_ERRNO,
    P314_EXP_STD_ADJ_5_METERING_MODES,
    P314_EXP_STD_ADJ_F_RESID16,
    P314_EXP_STD_ADJ_MODE_BKID_MAP,
    P314_EXP_STD_ADJ_MODE_F_RESID16_MAP,
    P314_EXP_STD_ADJ_PID_SYMBOL,
    P314_EXP_STD_ADJ_STEPS_SIXTHS,
    P314_EXP_STD_ADJ_WARN_RESID16,
    P314_FAST_CLI_BUDGET_SECONDS,
    P314_FOCUS_AREA_COLOR_DEFAULT,
    P314_FOCUS_AREA_COLOR_F_RESID16,
    P314_FOCUS_AREA_COLOR_RESID16_MAP,
    P314_FOCUS_AREA_LIMIT_14_AREAS,
    P314_FOCUS_AREA_LIMIT_BKID_MAP,
    P314_FOCUS_AREA_LIMIT_DORMANT_5,
    P314_FOCUS_AREA_LIMIT_F_RESID16,
    P314_FOCUS_AREA_LIMIT_LT2_RESID16,
    P314_FOCUS_AREA_LIMIT_NON_TRACKING_7,
    P314_FOCUS_AREA_LIMIT_TRACKING_7,
    P314_FORCED_NDF_FRAME_RATES,
    P314_FX3_EXP_STD_ADJ_METERING_MODE_COUNT,
    P314_FX3_FOCUS_AREA_LIMIT_COUNT,
    P314_FX3_FOCUS_AREA_LIMIT_MIN_ENABLED,
    P314_FX3_FW_VERSION,
    P314_FX3_HAS_PHYSICAL_BNC_TC_PORT,
    P314_FX3_HAS_SWITCH_VH_AF_AREA,
    P314_FX3_HELPGUIDE_ID,
    P314_FX3_MODEL_ID,
    P314_FX3_MODEL_NAME,
    P314_FX6_DONOR_FW_VERSION,
    P314_FX6_DONOR_MODEL_NAME,
    P314_FX6_DORMANT_COPY_CLIP_2_RESID16,
    P314_FX6_FOCUS_AREA_IND_AFS_RESID16,
    P314_FX6_FOCUS_AREA_MARKER_2_RESID16,
    P314_FX6_HAS_PHYSICAL_BNC_TC_PORT,
    P314_FX6_TC_FORMAT_2_RESID16,
    P314_PINNED_FX3_APPFW_702_BYTES,
    P314_PINNED_FX3_APPFW_702_HDR4K_SHA256,
    P314_PINNED_FX3_BACKUP_BIN_BYTES,
    P314_PINNED_FX3_BACKUP_BIN_SHA256,
    P314_PINNED_FX3_UXC_EN_F_BYTES,
    P314_PINNED_FX3_UXC_EN_F_SHA256,
    P314_PINNED_FX6_APPFW_601_BYTES,
    P314_PINNED_FX6_APPFW_601_HDR4K_SHA256,
    P314_PINNED_FX6_UXC_EN_2_BYTES,
    P314_PINNED_FX6_UXC_EN_2_SHA256,
    P314_PINNED_FX6_UXC_EN_BYTES,
    P314_PINNED_FX6_UXC_EN_SHA256,
    P314_SELECT_PLAYBACK_MEDIA_DEFAULT_SLOT,
    P314_SLIDESHOW_INTERVALS,
    P314_SLIDESHOW_INTERVAL_DEFAULT,
    P314_SLIDESHOW_REPEAT_DEFAULT,
    P314_SLIDESHOW_RESID16,
    P314_SLIDESHOW_VALID_VIEW_MODES,
    P314_STAGE_B_VOLATILE_OVERLAY_DIR,
    P314_STATUS_VERIFIED_56OF56_AGGREGATOR,
    P314_STATUS_VERIFIED_PILLAR56_SUITE,
    P314_STATUS_VERIFIED_PILLAR_56A,
    P314_STATUS_VERIFIED_PILLAR_56B,
    P314_SWITCH_VH_AF_BKID,
    P314_SWITCH_VH_AF_DEFAULT,
    P314_SWITCH_VH_AF_F_RESID16,
    P314_SWITCH_VH_AF_LOCKOUT_CONDITIONS,
    P314_SWITCH_VH_AF_RESID16_MAP,
    P314_TCUB_DISP_DEFAULT,
    P314_TCUB_DISP_F_RESID16,
    P314_TCUB_PLAYBACK_STILL_BLOCK_RESID16,
    P314_TC_FORMAT_DEFAULT,
    P314_TC_FORMAT_F_RESID16,
    P314_TC_MAKE_DEFAULT,
    P314_TC_PRESET_DEFAULT,
    P314_TC_RUN_DEFAULT,
    P314_UB_PRESET_DEFAULT,
    P314_UB_TIME_REC_DEFAULT,
    P314_VAULT_FIREWALL_ERRNO_CODES,
    PASSIVE_TX_BYTES_EMITTED,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHASE314_MASTER_SCHEMA,
    PHASE314_PHASE_NUMBER,
    PHASE314_SCHEMA,
    PHASE314_VERSION,
    PHYSICAL_DEVICE_WRITES,
    PHYSICAL_USB_PACKETS_EMITTED,
    RAW_FIRMWARE_BYTES_LEAKED,
    READ_ONLY_DONOR_ACCESS,
    RPMB_COUNTER_INCREMENTS,
    SPI_NOR_WRITE_AUTHORIZED,
    build_default_safe_exposure_std_tcub_reverse_copy_vault_spec,
    build_default_safe_switch_vh_af_focus_limit_color_vault_spec,
    compute_expected_exposure_std_adj_and_bracket_state,
    compute_expected_focus_area_limit_and_color_state,
    compute_expected_playback_copy_and_slideshow_vault_state,
    compute_expected_switch_vh_af_state,
    compute_expected_tcub_and_disp_state,
    evaluate_56pillar_recovery_master,
    evaluate_exposure_std_tcub_reverse_copy_vault,
    evaluate_realhw_56pillar_recovery_master,
    evaluate_switch_vh_af_focus_limit_color_vault,
    inspect_phase314_donors_readonly,
    run_pillar56_standalone_suite,
    run_pillar56a_switch_vh_af_focus_limit_color_6_scenario_suite,
    run_pillar56b_exposure_std_tcub_reverse_copy_6_scenario_suite,
    verify_56pillar_recovery_suite,
    verify_switch_vh_af_stdadj_tcub_copy_and_vault,
    verify_switch_vh_af_stdadj_tcub_copy_vault,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
ADAPTER_ROOT = Path(__file__).resolve().parents[1]


def _ci_headroom() -> float:
    return 15.0 if os.environ.get("GITHUB_ACTIONS", "").strip().lower() == "true" else 0.0


def _clean_env(**extra: str) -> dict[str, str]:
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    existing_pp = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = (
        f"{ADAPTER_ROOT}{os.pathsep}{existing_pp}" if existing_pp else str(ADAPTER_ROOT)
    )
    env.update(extra)
    return env


class TestPhase314SafetyDonorsAndExports(unittest.TestCase):
    """Tests 01-12: Safety locks, package exports, donor inspection, and empirical constants."""

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
        self.assertTrue(p314.CNFLASHA_USERSPACE_WRITE_BLOCKED)
        self.assertEqual(OTP_FUSE_TOUCHES, 0)
        self.assertEqual(OTP_FUSE_WRITES, 0)
        self.assertEqual(RPMB_COUNTER_INCREMENTS, 0)
        self.assertEqual(PASSIVE_TX_BYTES_EMITTED, 0)
        self.assertEqual(PHYSICAL_USB_PACKETS_EMITTED, 0)
        self.assertEqual(PHYSICAL_DEVICE_WRITES, 0)
        self.assertEqual(RAW_FIRMWARE_BYTES_LEAKED, 0)

    def test_02_schema_version_and_camera_identity_constants(self) -> None:
        self.assertEqual(
            PHASE314_SCHEMA,
            "realhw_56pillar_switch_vh_af_stdadj_tcub_copy_vault_verifier_v1",
        )
        self.assertEqual(PHASE314_MASTER_SCHEMA, "realhw_56pillar_recovery_master_v1")
        self.assertEqual(PHASE314_VERSION, "1.0.0")
        self.assertEqual(PHASE314_PHASE_NUMBER, 314)
        self.assertEqual(P314_FX3_MODEL_NAME, "ILME-FX3")
        self.assertEqual(P314_FX3_MODEL_ID, 0x91030080)
        self.assertEqual(P314_FX3_FW_VERSION, "7.02")
        self.assertEqual(P314_FX3_HELPGUIDE_ID, "ilc/2210")
        self.assertEqual(P314_FX6_DONOR_MODEL_NAME, "ILME-FX6")
        self.assertEqual(P314_FX6_DONOR_FW_VERSION, "6.01")
        self.assertTrue(P314_FX3_HAS_SWITCH_VH_AF_AREA)
        self.assertEqual(P314_FX3_FOCUS_AREA_LIMIT_COUNT, 14)
        self.assertEqual(P314_FX3_FOCUS_AREA_LIMIT_MIN_ENABLED, 2)
        self.assertEqual(P314_FX3_EXP_STD_ADJ_METERING_MODE_COUNT, 5)
        self.assertFalse(P314_FX3_HAS_PHYSICAL_BNC_TC_PORT)
        self.assertTrue(P314_FX6_HAS_PHYSICAL_BNC_TC_PORT)

    def test_03_empirical_uxc_resid16_and_bkid_constants(self) -> None:
        self.assertEqual(P314_SWITCH_VH_AF_F_RESID16, 0x73AE)
        self.assertEqual(P314_SWITCH_VH_AF_RESID16_MAP["AF Point Only"], 0x615A)
        self.assertEqual(P314_SWITCH_VH_AF_RESID16_MAP["AF Point + AF Area"], 0x69E8)
        self.assertEqual(P314_SWITCH_VH_AF_BKID, "BKID_APP_setting_vertical_horizontal_focus_area_switch")
        self.assertEqual(P314_FOCUS_AREA_LIMIT_F_RESID16, 0x6DE2)
        self.assertEqual(P314_FOCUS_AREA_LIMIT_LT2_RESID16, 0xEA28)
        self.assertEqual(P314_FOCUS_AREA_COLOR_F_RESID16, 0x74AD)
        self.assertEqual(P314_FOCUS_AREA_COLOR_RESID16_MAP["White"], 0xE883)
        self.assertEqual(P314_FOCUS_AREA_COLOR_RESID16_MAP["Red"], 0xE8C6)
        self.assertEqual(P314_FX6_FOCUS_AREA_IND_AFS_RESID16, 0x2236)
        self.assertEqual(P314_FX6_FOCUS_AREA_MARKER_2_RESID16, 0x4D6B)
        self.assertEqual(P314_EXP_STD_ADJ_F_RESID16, 0x6114)
        self.assertEqual(P314_EXP_STD_ADJ_WARN_RESID16, 0xE567)
        self.assertEqual(P314_TCUB_DISP_F_RESID16, 0x6B0C)
        self.assertEqual(P314_TCUB_PLAYBACK_STILL_BLOCK_RESID16, 0xE728)
        self.assertEqual(P314_TC_FORMAT_F_RESID16, 0x6E3D)
        self.assertEqual(P314_COPY_F_RESID16, 0x79FC)
        self.assertEqual(P314_COPY_FAIL_RESID16, (0xE366, 0xE6DB))
        self.assertEqual(P314_SLIDESHOW_RESID16, 0xE2CC)
        self.assertEqual(P314_FX6_DORMANT_COPY_CLIP_2_RESID16, 0x4136)
        self.assertEqual(P314_FX6_TC_FORMAT_2_RESID16, 0x456D)

    def test_04_init_exports_and_non_overlapping_master_56_registry(self) -> None:
        self.assertIs(
            fx3_recovery.evaluate_realhw_56pillar_recovery_master,
            evaluate_realhw_56pillar_recovery_master,
        )
        self.assertIs(
            fx3_recovery.evaluate_56pillar_recovery_master,
            evaluate_56pillar_recovery_master,
        )
        self.assertIs(fx3_recovery.verify_56pillar_recovery_suite, verify_56pillar_recovery_suite)
        self.assertIs(fx3_recovery.run_pillar56_standalone_suite, run_pillar56_standalone_suite)
        self.assertIs(fx3_recovery.CROSS_MODEL_FLASH_AUTHORIZED, CROSS_MODEL_FLASH_AUTHORIZED)
        for sym in p314.__all__:
            self.assertEqual(fx3_recovery.__all__.count(sym), 1, sym)
        self.assertEqual(MASTER_56_PILLAR_COUNT, 56)
        self.assertEqual(len(MASTER_56_PILLAR_SPECS), 56)
        self.assertEqual(len(MASTER_56_PILLAR_IDS), 56)
        self.assertEqual(len(set(MASTER_56_PILLAR_IDS)), 56)
        self.assertEqual(MASTER_56_PILLAR_SPECS[55][0], 56)
        self.assertEqual(
            MASTER_56_PILLAR_SPECS[55][1],
            "pillar_56_switch_vh_af_stdadj_tcub_copy_vault",
        )

    def test_05_safety_invariant_tamper_rejected_in_56a_and_56b(self) -> None:
        with mock.patch.object(p314, "CROSS_MODEL_FLASH_AUTHORIZED", True):
            rep_a = evaluate_switch_vh_af_focus_limit_color_vault(
                build_default_safe_switch_vh_af_focus_limit_color_vault_spec()
            )
            self.assertFalse(rep_a.passed)
            self.assertEqual(rep_a.block_code, P314_BLOCKED_SAFETY_POLICY_VIOLATION)

            rep_b = evaluate_exposure_std_tcub_reverse_copy_vault(
                build_default_safe_exposure_std_tcub_reverse_copy_vault_spec()
            )
            self.assertFalse(rep_b.passed)
            self.assertEqual(rep_b.block_code, P314_BLOCKED_SAFETY_POLICY_VIOLATION)

    def test_06_invalid_56a_and_56b_spec_parameters_fail_closed(self) -> None:
        rep_a = evaluate_switch_vh_af_focus_limit_color_vault(
            build_default_safe_switch_vh_af_focus_limit_color_vault_spec(
                camera_model="ILCE-7M4"
            )
        )
        self.assertFalse(rep_a.passed)
        self.assertEqual(rep_a.block_code, P314_BLOCKED_INVALID_PILLAR56A_SPEC)

        rep_b = evaluate_exposure_std_tcub_reverse_copy_vault(
            build_default_safe_exposure_std_tcub_reverse_copy_vault_spec(
                exp_std_metering_mode="UnknownMeter"
            )
        )
        self.assertFalse(rep_b.passed)
        self.assertEqual(rep_b.block_code, P314_BLOCKED_INVALID_PILLAR56B_SPEC)

        rep_b2 = evaluate_exposure_std_tcub_reverse_copy_vault(
            build_default_safe_exposure_std_tcub_reverse_copy_vault_spec(
                ub_preset="ZZ ZZ ZZ ZZ"
            )
        )
        self.assertFalse(rep_b2.passed)
        self.assertEqual(rep_b2.block_code, P314_BLOCKED_INVALID_PILLAR56B_SPEC)

    def test_07_donor_snapshot_bounded_readonly_and_17_artifacts(self) -> None:
        snap = inspect_phase314_donors_readonly()
        self.assertIn(snap.verification_mode, ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"))
        self.assertTrue(snap.all_donors_present)
        self.assertEqual(snap.donor_files_inspected, 17)
        self.assertEqual(len(snap.artifacts), 17)
        self.assertEqual(snap.raw_firmware_bytes_leaked, 0)
        self.assertLess(snap.elapsed_seconds, max(P314_DONOR_INSPECT_BUDGET_SECONDS, P314_DONOR_INSPECT_CI_BUDGET_SECONDS) + _ci_headroom())
        self.assertTrue(all(a.present and a.matches_pinned for a in snap.artifacts))

    def test_08_donor_pinned_hashes_when_local_donors_present(self) -> None:
        snap = inspect_phase314_donors_readonly()
        by_id = {a.artifact_id: a for a in snap.artifacts}
        self.assertEqual(by_id["fx3_appfw_702_so"].total_bytes, P314_PINNED_FX3_APPFW_702_BYTES)
        self.assertEqual(by_id["fx3_appfw_702_so"].digest_sha256, P314_PINNED_FX3_APPFW_702_HDR4K_SHA256)
        self.assertEqual(by_id["fx3_backup_bin"].total_bytes, P314_PINNED_FX3_BACKUP_BIN_BYTES)
        self.assertEqual(by_id["fx3_backup_bin"].digest_sha256, P314_PINNED_FX3_BACKUP_BIN_SHA256)
        self.assertEqual(by_id["fx3_uxc_en_f"].total_bytes, P314_PINNED_FX3_UXC_EN_F_BYTES)
        self.assertEqual(by_id["fx3_uxc_en_f"].digest_sha256, P314_PINNED_FX3_UXC_EN_F_SHA256)
        self.assertEqual(by_id["fx6_appfw_601_so"].total_bytes, P314_PINNED_FX6_APPFW_601_BYTES)
        self.assertEqual(by_id["fx6_appfw_601_so"].digest_sha256, P314_PINNED_FX6_APPFW_601_HDR4K_SHA256)
        self.assertEqual(by_id["fx6_uxc_en"].total_bytes, P314_PINNED_FX6_UXC_EN_BYTES)
        self.assertEqual(by_id["fx6_uxc_en"].digest_sha256, P314_PINNED_FX6_UXC_EN_SHA256)
        self.assertEqual(by_id["fx6_uxc_en_2"].total_bytes, P314_PINNED_FX6_UXC_EN_2_BYTES)
        self.assertEqual(by_id["fx6_uxc_en_2"].digest_sha256, P314_PINNED_FX6_UXC_EN_2_SHA256)
        if snap.verification_mode == "LOCAL_DONOR_O_RDONLY":
            self.assertLess(snap.elapsed_seconds, 0.25 + _ci_headroom())
            self.assertEqual(by_id["fx3_appfw_702_so"].header_bytes_read, 4096)
            self.assertEqual(by_id["fx6_appfw_601_so"].header_bytes_read, 4096)

    def test_09_donor_inspection_force_clean_room_and_missing_fallback(self) -> None:
        snap_forced = inspect_phase314_donors_readonly(force_clean_room=True)
        self.assertEqual(snap_forced.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(snap_forced.donor_files_inspected, 17)
        self.assertTrue(snap_forced.all_donors_present)

        with mock.patch.object(p314, "resolve_donor_path", return_value=None):
            snap_missing = inspect_phase314_donors_readonly(force_clean_room=False)
        self.assertEqual(snap_missing.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(snap_missing.all_donors_present)
        self.assertEqual(snap_missing.donor_files_inspected, 17)

    def test_10_env_clean_room_test_and_fx3_fx6_force_clean_room_honored(self) -> None:
        with mock.patch.dict(os.environ, {P314_ENV_CLEAN_ROOM_TEST: "1"}):
            snap = inspect_phase314_donors_readonly()
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")

        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            rep = run_pillar56_standalone_suite()
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(rep.all_passed)

    def test_11_dual_mode_parity_standalone_suite(self) -> None:
        rep_cr = run_pillar56_standalone_suite(force_clean_room=True)
        rep_def = run_pillar56_standalone_suite()
        self.assertTrue(rep_cr.all_passed)
        self.assertTrue(rep_def.all_passed)
        self.assertEqual(
            [(o.scenario_id, o.actual_allowed, o.block_code, o.passed) for o in rep_cr.pillar_56a_switch_vh_af_focus_limit_color_vault.scenarios],
            [(o.scenario_id, o.actual_allowed, o.block_code, o.passed) for o in rep_def.pillar_56a_switch_vh_af_focus_limit_color_vault.scenarios],
        )
        self.assertEqual(
            [(o.scenario_id, o.actual_allowed, o.block_code, o.passed) for o in rep_cr.pillar_56b_exposure_std_tcub_reverse_copy_vault.scenarios],
            [(o.scenario_id, o.actual_allowed, o.block_code, o.passed) for o in rep_def.pillar_56b_exposure_std_tcub_reverse_copy_vault.scenarios],
        )

    def test_12_dual_mode_parity_master_56_verdicts(self) -> None:
        m_cr = evaluate_realhw_56pillar_recovery_master(force_clean_room=True)
        m_def = evaluate_realhw_56pillar_recovery_master()
        self.assertTrue(m_cr.all_passed)
        self.assertTrue(m_def.all_passed)
        self.assertEqual(m_cr.pillar_count, m_def.pillar_count)
        self.assertEqual(m_cr.pillars_passed, m_def.pillars_passed)
        self.assertEqual(
            [(p.pillar_number, p.pillar_id, p.passed) for p in m_cr.pillars],
            [(p.pillar_number, p.pillar_id, p.passed) for p in m_def.pillars],
        )


class TestPhase314SubPillar56ASwitchVhAfFocusLimitColor(unittest.TestCase):
    """Tests 13-36: Sub-Pillar 56A — Switch V/H AF Area, 14-area Limit, Focus Area Color, FX6, Vault."""

    def test_13_switch_vh_af_default_off_and_3_valid_orientations_still_afc(self) -> None:
        self.assertEqual(P314_SWITCH_VH_AF_DEFAULT, "Off")
        for orient in ("0_DEGREES", "90_DEGREES", "270_DEGREES"):
            for mode in ("AF Point Only", "AF Point + AF Area"):
                st = compute_expected_switch_vh_af_state(
                    camera_model=P314_FX3_MODEL_NAME,
                    shooting_domain="Still",
                    focus_mode="AF-C",
                    configured_switch_vh_af=mode,
                    previous_switch_vh_af=mode,
                    orientation=orient,
                    intelligent_auto_active=False,
                    digital_zoom_active=False,
                    af_active_in_progress=False,
                    continuous_burst_active=False,
                    self_timer_countdown_active=False,
                    focus_magnifier_active=False,
                    reset_action="None",
                )
                self.assertTrue(st["switch_triggered"], (orient, mode))
                self.assertIsNone(st["switch_errno"])
                self.assertFalse(st["orientation_coords_cleared"])
                self.assertEqual(st["post_switch_vh_af"], mode)

    def test_14_switch_vh_af_invalid_vertical_pitch_never_switches(self) -> None:
        st = compute_expected_switch_vh_af_state(
            camera_model=P314_FX3_MODEL_NAME,
            shooting_domain="Still",
            focus_mode="AF-C",
            configured_switch_vh_af="AF Point + AF Area",
            previous_switch_vh_af="AF Point + AF Area",
            orientation="INVALID",
            intelligent_auto_active=False,
            digital_zoom_active=False,
            af_active_in_progress=False,
            continuous_burst_active=False,
            self_timer_countdown_active=False,
            focus_magnifier_active=False,
            reset_action="None",
        )
        self.assertFalse(st["switch_triggered"])
        self.assertIsNone(st["switch_errno"])
        rep = evaluate_switch_vh_af_focus_limit_color_vault(
            build_default_safe_switch_vh_af_focus_limit_color_vault_spec(
                orientation="INVALID",
                reported_switch_triggered=False,
            )
        )
        self.assertTrue(rep.passed)

    def test_15_switch_vh_af_all_8_lockout_conditions_enforce_ebusy16(self) -> None:
        self.assertEqual(len(P314_SWITCH_VH_AF_LOCKOUT_CONDITIONS), 8)
        lockout_cases = [
            {"shooting_domain": "Movie", "reported_movie_tracking_excluded": True},
            {"shooting_domain": "S&Q", "reported_movie_tracking_excluded": True},
            {"focus_mode": "AF-S"},
            {"focus_mode": "AF-A"},
            {"focus_mode": "DMF"},
            {"focus_mode": "MF"},
            {"intelligent_auto_active": True},
            {"digital_zoom_active": True},
            {"af_active_in_progress": True},
            {"continuous_burst_active": True},
            {"self_timer_countdown_active": True},
            {"focus_magnifier_active": True},
        ]
        for overrides in lockout_cases:
            spec = build_default_safe_switch_vh_af_focus_limit_color_vault_spec(
                reported_switch_triggered=False,
                reported_switch_errno=P314_EBUSY_ERRNO,
                **overrides,
            )
            rep = evaluate_switch_vh_af_focus_limit_color_vault(spec)
            self.assertTrue(rep.passed, f"Expected pass with EBUSY=16 lockout for {overrides}: {rep.errors}")

    def test_16_switch_vh_af_lockout_bypass_rejected(self) -> None:
        spec = build_default_safe_switch_vh_af_focus_limit_color_vault_spec(
            focus_magnifier_active=True,
            reported_switch_triggered=True,
            reported_switch_errno=None,
        )
        rep = evaluate_switch_vh_af_focus_limit_color_vault(spec)
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P314_BLOCKED_SWITCH_VH_AF_LOCKOUT_OR_COORDS_DRIFT)

    def test_17_switch_vh_af_mode_change_clears_remembered_coords(self) -> None:
        spec = build_default_safe_switch_vh_af_focus_limit_color_vault_spec(
            previous_switch_vh_af="AF Point Only",
            configured_switch_vh_af="AF Point + AF Area",
            reported_orientation_coords_cleared=True,
        )
        rep = evaluate_switch_vh_af_focus_limit_color_vault(spec)
        self.assertTrue(rep.passed)

        spec_bad = build_default_safe_switch_vh_af_focus_limit_color_vault_spec(
            previous_switch_vh_af="AF Point Only",
            configured_switch_vh_af="AF Point + AF Area",
            reported_orientation_coords_cleared=False,
        )
        rep_bad = evaluate_switch_vh_af_focus_limit_color_vault(spec_bad)
        self.assertFalse(rep_bad.passed)
        self.assertEqual(rep_bad.block_code, P314_BLOCKED_SWITCH_VH_AF_LOCKOUT_OR_COORDS_DRIFT)

    def test_18_switch_vh_af_and_focus_limit_reset_on_camera_settings_reset(self) -> None:
        spec = build_default_safe_switch_vh_af_focus_limit_color_vault_spec(
            configured_switch_vh_af="AF Point + AF Area",
            previous_switch_vh_af="AF Point + AF Area",
            requested_enabled_areas=("Wide", "Zone", "Spot: S"),
            reset_action="Camera Settings Reset",
            reported_switch_triggered=True,
            reported_orientation_coords_cleared=True,
            post_switch_vh_af="Off",
            post_enabled_areas=P314_FOCUS_AREA_LIMIT_14_AREAS,
            configured_focus_area_color="Red",
            post_focus_area_color="Red",
        )
        rep = evaluate_switch_vh_af_focus_limit_color_vault(spec)
        self.assertTrue(rep.passed, rep.errors)

    def test_19_switch_vh_af_reset_drift_rejected(self) -> None:
        spec = build_default_safe_switch_vh_af_focus_limit_color_vault_spec(
            reset_action="Camera Settings Reset",
            reported_orientation_coords_cleared=True,
            post_switch_vh_af="AF Point + AF Area",
            post_enabled_areas=P314_FOCUS_AREA_LIMIT_14_AREAS,
        )
        rep = evaluate_switch_vh_af_focus_limit_color_vault(spec)
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P314_BLOCKED_SWITCH_VH_AF_LOCKOUT_OR_COORDS_DRIFT)

    def test_20_focus_area_limit_exact_14_bkid_checkboxes(self) -> None:
        self.assertEqual(len(P314_FOCUS_AREA_LIMIT_NON_TRACKING_7), 7)
        self.assertEqual(len(P314_FOCUS_AREA_LIMIT_TRACKING_7), 7)
        self.assertEqual(len(P314_FOCUS_AREA_LIMIT_14_AREAS), 14)
        self.assertEqual(set(P314_FOCUS_AREA_LIMIT_BKID_MAP.keys()), set(P314_FOCUS_AREA_LIMIT_14_AREAS))
        for area, bkid in P314_FOCUS_AREA_LIMIT_BKID_MAP.items():
            self.assertTrue(bkid.startswith("BKID_APP_focus_area_limit_"), (area, bkid))

    def test_21_focus_area_limit_enforces_ge_2_floor_einval22(self) -> None:
        for few in (("Wide",), ()):
            rep = evaluate_switch_vh_af_focus_limit_color_vault(
                build_default_safe_switch_vh_af_focus_limit_color_vault_spec(
                    requested_enabled_areas=few,
                    post_enabled_areas=few,
                    reported_limit_lt2_errno=P314_EINVAL_ERRNO,
                )
            )
            self.assertTrue(rep.passed, (few, rep.errors))

        rep_bad = evaluate_switch_vh_af_focus_limit_color_vault(
            build_default_safe_switch_vh_af_focus_limit_color_vault_spec(
                requested_enabled_areas=("Wide",),
                post_enabled_areas=("Wide",),
                reported_limit_lt2_errno=None,
            )
        )
        self.assertFalse(rep_bad.passed)
        self.assertEqual(rep_bad.block_code, P314_BLOCKED_FOCUS_AREA_LIMIT_LT2_OR_DORMANT_SYMBOL)

    def test_22_focus_area_limit_rejects_5_dormant_bionz_xr_symbols_eopnotsupp95(self) -> None:
        self.assertEqual(
            P314_FOCUS_AREA_LIMIT_DORMANT_5,
            (
                "flexible_spot_xl",
                "flexible_spot_xs",
                "custom_1",
                "custom_2",
                "custom_3",
            ),
        )
        for dormant_sym in P314_FOCUS_AREA_LIMIT_DORMANT_5:
            rep = evaluate_switch_vh_af_focus_limit_color_vault(
                build_default_safe_switch_vh_af_focus_limit_color_vault_spec(
                    requested_dormant_areas=(dormant_sym,),
                    reported_dormant_errno=P314_EOPNOTSUPP_ERRNO,
                )
            )
            self.assertTrue(rep.passed, (dormant_sym, rep.errors))

            rep_bad = evaluate_switch_vh_af_focus_limit_color_vault(
                build_default_safe_switch_vh_af_focus_limit_color_vault_spec(
                    requested_dormant_areas=(dormant_sym,),
                    reported_dormant_errno=None,
                )
            )
            self.assertFalse(rep_bad.passed)
            self.assertEqual(rep_bad.block_code, P314_BLOCKED_FOCUS_AREA_LIMIT_LT2_OR_DORMANT_SYMBOL)

    def test_23_focus_area_limit_movie_sq_excludes_tracking7(self) -> None:
        fl = compute_expected_focus_area_limit_and_color_state(
            camera_model=P314_FX3_MODEL_NAME,
            shooting_domain="Movie",
            requested_enabled_areas=P314_FOCUS_AREA_LIMIT_14_AREAS,
            requested_dormant_areas=(),
            configured_focus_area_color="White",
            reset_action="None",
        )
        self.assertEqual(fl["effective_areas"], P314_FOCUS_AREA_LIMIT_NON_TRACKING_7)

        rep_bad = evaluate_switch_vh_af_focus_limit_color_vault(
            build_default_safe_switch_vh_af_focus_limit_color_vault_spec(
                shooting_domain="Movie",
                reported_switch_triggered=False,
                reported_switch_errno=P314_EBUSY_ERRNO,
                reported_movie_tracking_excluded=False,
            )
        )
        self.assertFalse(rep_bad.passed)
        self.assertEqual(rep_bad.block_code, P314_BLOCKED_FOCUS_AREA_LIMIT_LT2_OR_DORMANT_SYMBOL)

    def test_24_focus_area_color_survives_camera_reset_needs_initialize(self) -> None:
        self.assertEqual(P314_FOCUS_AREA_COLOR_DEFAULT, "White")
        rep_cam_reset = evaluate_switch_vh_af_focus_limit_color_vault(
            build_default_safe_switch_vh_af_focus_limit_color_vault_spec(
                configured_focus_area_color="Red",
                post_focus_area_color="Red",
                reset_action="Camera Settings Reset",
                reported_orientation_coords_cleared=True,
                post_switch_vh_af="Off",
            )
        )
        self.assertTrue(rep_cam_reset.passed, rep_cam_reset.errors)

        rep_net_reset = evaluate_switch_vh_af_focus_limit_color_vault(
            build_default_safe_switch_vh_af_focus_limit_color_vault_spec(
                configured_focus_area_color="Red",
                post_focus_area_color="Red",
                reset_action="Reset Network Set.",
            )
        )
        self.assertTrue(rep_net_reset.passed, rep_net_reset.errors)

        rep_init = evaluate_switch_vh_af_focus_limit_color_vault(
            build_default_safe_switch_vh_af_focus_limit_color_vault_spec(
                configured_focus_area_color="Red",
                post_focus_area_color="White",
                reset_action="Initialize",
                reported_orientation_coords_cleared=True,
                post_switch_vh_af="Off",
            )
        )
        self.assertTrue(rep_init.passed, rep_init.errors)

    def test_25_focus_area_color_reset_spoof_rejected(self) -> None:
        rep = evaluate_switch_vh_af_focus_limit_color_vault(
            build_default_safe_switch_vh_af_focus_limit_color_vault_spec(
                configured_focus_area_color="Red",
                post_focus_area_color="White",
                reset_action="Camera Settings Reset",
                reported_orientation_coords_cleared=True,
                post_switch_vh_af="Off",
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P314_BLOCKED_FOCUS_AREA_COLOR_OR_FX6_SPOOF)

    def test_26_fx6_zero_switch_zero_limit_orange_moving_contrast(self) -> None:
        rep_ok = evaluate_switch_vh_af_focus_limit_color_vault(
            build_default_safe_switch_vh_af_focus_limit_color_vault_spec(
                camera_model=P314_FX6_DONOR_MODEL_NAME,
                fw_version=P314_FX6_DONOR_FW_VERSION,
                shooting_domain="Movie",
                reported_switch_triggered=False,
                reported_switch_errno=P314_EOPNOTSUPP_ERRNO,
                post_switch_vh_af="Off",
                requested_enabled_areas=(),
                post_enabled_areas=(),
                reported_dormant_errno=None,
                post_focus_area_color="OrangeMoving",
                fx6_exposes_switch_vh_af_or_limit=False,
                fx6_exposes_white_red_color_toggle=False,
            )
        )
        self.assertTrue(rep_ok.passed, rep_ok.errors)

        rep_spoof = evaluate_switch_vh_af_focus_limit_color_vault(
            build_default_safe_switch_vh_af_focus_limit_color_vault_spec(
                camera_model=P314_FX6_DONOR_MODEL_NAME,
                fw_version=P314_FX6_DONOR_FW_VERSION,
                shooting_domain="Movie",
                reported_switch_triggered=False,
                reported_switch_errno=P314_EOPNOTSUPP_ERRNO,
                post_switch_vh_af="Off",
                requested_enabled_areas=(),
                post_enabled_areas=(),
                reported_dormant_errno=None,
                post_focus_area_color="OrangeMoving",
                fx6_exposes_switch_vh_af_or_limit=True,
            )
        )
        self.assertFalse(rep_spoof.passed)
        self.assertEqual(rep_spoof.block_code, P314_BLOCKED_FOCUS_AREA_COLOR_OR_FX6_SPOOF)

    def test_27_56a_slot1_vault_format_and_copy_action_blocked(self) -> None:
        for action in ("COPY_PLAYBACK_MEDIA", "FORMAT_QUICK", "FORMAT_FULL"):
            rep = evaluate_switch_vh_af_focus_limit_color_vault(
                build_default_safe_switch_vh_af_focus_limit_color_vault_spec(
                    requested_vault_slot=1,
                    requested_vault_action=action,
                )
            )
            self.assertFalse(rep.passed, action)
            self.assertEqual(rep.block_code, P314_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL)

    def test_28_56a_persistent_overlay_escape_blocked(self) -> None:
        for bad_dir in ("/dev/cnflasha", "/mnt/pnflasha/overlay", "/setting/overlay"):
            rep = evaluate_switch_vh_af_focus_limit_color_vault(
                build_default_safe_switch_vh_af_focus_limit_color_vault_spec(overlay_dir=bad_dir)
            )
            self.assertFalse(rep.passed, bad_dir)
            self.assertEqual(rep.block_code, P314_BLOCKED_PERSISTENT_OVERLAY_ESCAPE)

    def test_29_56a_backup_bin_h0_h3_drift_blocked(self) -> None:
        rep = evaluate_switch_vh_af_focus_limit_color_vault(
            build_default_safe_switch_vh_af_focus_limit_color_vault_spec(
                backup_bin_h3_sha256="0" * 64,
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P314_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT)

    def test_30_pillar_56a_6_scenario_suite_passes(self) -> None:
        res = run_pillar56a_switch_vh_af_focus_limit_color_6_scenario_suite()
        self.assertTrue(res.passed)
        self.assertEqual(res.status, P314_STATUS_VERIFIED_PILLAR_56A)
        self.assertEqual(res.scenarios_passed, 6)
        self.assertEqual(res.scenarios_total, 6)
        self.assertTrue(all(o.passed for o in res.scenarios))

    def test_31_56a_matrix_states_and_zero_writes(self) -> None:
        rep = evaluate_switch_vh_af_focus_limit_color_vault(
            build_default_safe_switch_vh_af_focus_limit_color_vault_spec()
        )
        self.assertTrue(rep.passed)
        self.assertEqual(rep.matrix_states_checked, 18)
        self.assertEqual(rep.physical_device_writes, 0)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertEqual(rep.slot1_vault_mutation_bytes, 0)

    def test_32_56a_still_afc_switch_with_all_14_areas_allowed(self) -> None:
        rep = evaluate_switch_vh_af_focus_limit_color_vault(
            build_default_safe_switch_vh_af_focus_limit_color_vault_spec(
                orientation="270_DEGREES",
                configured_switch_vh_af="AF Point Only",
                previous_switch_vh_af="AF Point Only",
                post_switch_vh_af="AF Point Only",
                configured_focus_area_color="Red",
                post_focus_area_color="Red",
            )
        )
        self.assertTrue(rep.passed, rep.errors)

    def test_33_56a_minimum_2_enabled_areas_boundary_allowed(self) -> None:
        two_areas = ("Wide", "Spot: M")
        rep = evaluate_switch_vh_af_focus_limit_color_vault(
            build_default_safe_switch_vh_af_focus_limit_color_vault_spec(
                requested_enabled_areas=two_areas,
                post_enabled_areas=two_areas,
            )
        )
        self.assertTrue(rep.passed, rep.errors)

    def test_34_56a_negative_counter_nonzero_fails(self) -> None:
        rep = evaluate_switch_vh_af_focus_limit_color_vault(
            build_default_safe_switch_vh_af_focus_limit_color_vault_spec(
                focus_limit_lt2_or_dormant_symbol_events=1,
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P314_BLOCKED_FOCUS_AREA_LIMIT_LT2_OR_DORMANT_SYMBOL)

    def test_35_56a_switch_vh_af_off_does_not_raise_ebusy_in_movie(self) -> None:
        rep = evaluate_switch_vh_af_focus_limit_color_vault(
            build_default_safe_switch_vh_af_focus_limit_color_vault_spec(
                shooting_domain="Movie",
                configured_switch_vh_af="Off",
                previous_switch_vh_af="Off",
                post_switch_vh_af="Off",
                reported_switch_triggered=False,
                reported_switch_errno=None,
                reported_movie_tracking_excluded=True,
            )
        )
        self.assertTrue(rep.passed, rep.errors)

    def test_36_56a_report_to_dict_serializable(self) -> None:
        rep = evaluate_switch_vh_af_focus_limit_color_vault(
            build_default_safe_switch_vh_af_focus_limit_color_vault_spec()
        )
        raw = json.dumps(rep.to_dict(), sort_keys=True, allow_nan=False)
        self.assertIn(P314_STATUS_VERIFIED_PILLAR_56A, raw)


class TestPhase314SubPillar56BExpStdAdjTcubReverseCopySlideShow(unittest.TestCase):
    """Tests 37-68: Sub-Pillar 56B — 5-mode Exposure Std. Adj., Bracket, 7-item TC/UB, Reverse Copy Firewall, Slide Show."""

    def test_37_exposure_std_adj_all_5_metering_modes_verified(self) -> None:
        self.assertEqual(
            P314_EXP_STD_ADJ_5_METERING_MODES,
            ("Multi", "Center", "Spot", "Entire Screen Avg.", "Highlight"),
        )
        self.assertEqual(set(P314_EXP_STD_ADJ_MODE_BKID_MAP.keys()), set(P314_EXP_STD_ADJ_5_METERING_MODES))
        self.assertEqual(set(P314_EXP_STD_ADJ_MODE_F_RESID16_MAP.keys()), set(P314_EXP_STD_ADJ_5_METERING_MODES))
        for mode in P314_EXP_STD_ADJ_5_METERING_MODES:
            rep = evaluate_exposure_std_tcub_reverse_copy_vault(
                build_default_safe_exposure_std_tcub_reverse_copy_vault_spec(
                    exp_std_metering_mode=mode,
                    configured_exp_std_adj_sixths=2,
                    post_exp_std_adj_sixths=2,
                    reported_mm_baseline_shifted_sixths=2,
                )
            )
            self.assertTrue(rep.passed, (mode, rep.errors))

    def test_38_exposure_std_adj_all_13_one_sixth_ev_steps_supported(self) -> None:
        self.assertEqual(P314_EXP_STD_ADJ_STEPS_SIXTHS, tuple(range(-6, 7)))
        self.assertEqual(len(P314_EXP_STD_ADJ_STEPS_SIXTHS), 13)
        for step in P314_EXP_STD_ADJ_STEPS_SIXTHS:
            rep = evaluate_exposure_std_tcub_reverse_copy_vault(
                build_default_safe_exposure_std_tcub_reverse_copy_vault_spec(
                    exp_std_metering_mode="Highlight",
                    configured_exp_std_adj_sixths=step,
                    post_exp_std_adj_sixths=step,
                    reported_mm_baseline_shifted_sixths=step,
                )
            )
            self.assertTrue(rep.passed, (step, rep.errors))

    def test_39_exposure_std_adj_4mode_conflation_rejected(self) -> None:
        rep = evaluate_exposure_std_tcub_reverse_copy_vault(
            build_default_safe_exposure_std_tcub_reverse_copy_vault_spec(
                exp_std_metering_mode="Highlight",
                exp_std_supported_modes_count=4,
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P314_BLOCKED_EXP_STD_ADJ_5MODE_OR_BRACKET_DRIFT)

    def test_40_exposure_std_adj_exif_isolation_does_not_mutate_exposure_comp(self) -> None:
        rep_ok = evaluate_exposure_std_tcub_reverse_copy_vault(
            build_default_safe_exposure_std_tcub_reverse_copy_vault_spec(
                exp_std_metering_mode="Entire Screen Avg.",
                configured_exp_std_adj_sixths=-4,
                post_exp_std_adj_sixths=-4,
                reported_mm_baseline_shifted_sixths=-4,
                base_exposure_comp_tenths=7,
                reported_post_exposure_comp_tenths=7,
                reported_exif_std_adj_isolated=True,
            )
        )
        self.assertTrue(rep_ok.passed, rep_ok.errors)

        rep_bad = evaluate_exposure_std_tcub_reverse_copy_vault(
            build_default_safe_exposure_std_tcub_reverse_copy_vault_spec(
                configured_exp_std_adj_sixths=-4,
                post_exp_std_adj_sixths=-4,
                reported_mm_baseline_shifted_sixths=-4,
                base_exposure_comp_tenths=7,
                reported_post_exposure_comp_tenths=0,
            )
        )
        self.assertFalse(rep_bad.passed)
        self.assertEqual(rep_bad.block_code, P314_BLOCKED_EXP_STD_ADJ_5MODE_OR_BRACKET_DRIFT)

    def test_41_exposure_std_adj_mid_bracket_resets_shot_counter(self) -> None:
        rep_ok = evaluate_exposure_std_tcub_reverse_copy_vault(
            build_default_safe_exposure_std_tcub_reverse_copy_vault_spec(
                configured_exp_std_adj_sixths=3,
                post_exp_std_adj_sixths=3,
                reported_mm_baseline_shifted_sixths=3,
                adjusted_mid_bracket=True,
                reported_bracket_shot_counter_reset=True,
            )
        )
        self.assertTrue(rep_ok.passed, rep_ok.errors)

        rep_bad = evaluate_exposure_std_tcub_reverse_copy_vault(
            build_default_safe_exposure_std_tcub_reverse_copy_vault_spec(
                configured_exp_std_adj_sixths=3,
                post_exp_std_adj_sixths=3,
                reported_mm_baseline_shifted_sixths=3,
                adjusted_mid_bracket=True,
                reported_bracket_shot_counter_reset=False,
            )
        )
        self.assertFalse(rep_bad.passed)
        self.assertEqual(rep_bad.block_code, P314_BLOCKED_EXP_STD_ADJ_5MODE_OR_BRACKET_DRIFT)

    def test_42_exposure_std_adj_survives_camera_reset_bracket_resets(self) -> None:
        rep_cam = evaluate_exposure_std_tcub_reverse_copy_vault(
            build_default_safe_exposure_std_tcub_reverse_copy_vault_spec(
                configured_exp_std_adj_sixths=5,
                post_exp_std_adj_sixths=5,
                reported_mm_baseline_shifted_sixths=5,
                configured_bracket_selftimer="5 Sec",
                configured_bracket_order="-->0->+",
                reset_action="Camera Settings Reset",
                post_bracket_selftimer="Off",
                post_bracket_order="0->-->+",
            )
        )
        self.assertTrue(rep_cam.passed, rep_cam.errors)

        rep_init = evaluate_exposure_std_tcub_reverse_copy_vault(
            build_default_safe_exposure_std_tcub_reverse_copy_vault_spec(
                configured_exp_std_adj_sixths=5,
                post_exp_std_adj_sixths=0,
                reported_mm_baseline_shifted_sixths=5,
                configured_bracket_selftimer="10 Sec",
                configured_bracket_order="-->0->+",
                reset_action="Initialize",
                post_bracket_selftimer="Off",
                post_bracket_order="0->-->+",
            )
        )
        self.assertTrue(rep_init.passed, rep_init.errors)

    def test_43_exposure_std_adj_warn_prompt_required(self) -> None:
        rep = evaluate_exposure_std_tcub_reverse_copy_vault(
            build_default_safe_exposure_std_tcub_reverse_copy_vault_spec(
                configured_exp_std_adj_sixths=1,
                post_exp_std_adj_sixths=1,
                reported_mm_baseline_shifted_sixths=1,
                exp_std_warn_prompt_acknowledged=False,
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P314_BLOCKED_EXP_STD_ADJ_5MODE_OR_BRACKET_DRIFT)

    def test_44_bracket_settings_unicode_order_and_selftimer_modes(self) -> None:
        self.assertEqual(P314_BRACKET_SELFTIMER_MODES, ("Off", "2 Sec", "5 Sec", "10 Sec"))
        self.assertEqual(P314_BRACKET_ORDER_MODES, ("0->-->+", "-->0->+"))
        for st_mode in P314_BRACKET_SELFTIMER_MODES:
            for ord_mode in P314_BRACKET_ORDER_MODES:
                rep = evaluate_exposure_std_tcub_reverse_copy_vault(
                    build_default_safe_exposure_std_tcub_reverse_copy_vault_spec(
                        configured_bracket_selftimer=st_mode,
                        post_bracket_selftimer=st_mode,
                        configured_bracket_order=ord_mode,
                        post_bracket_order=ord_mode,
                    )
                )
                self.assertTrue(rep.passed, (st_mode, ord_mode, rep.errors))

    def test_45_fx6_dormant_bracket_and_missing_exposure_std_enoent2(self) -> None:
        rep_ok = evaluate_exposure_std_tcub_reverse_copy_vault(
            build_default_safe_exposure_std_tcub_reverse_copy_vault_spec(
                camera_model=P314_FX6_DONOR_MODEL_NAME,
                fw_version=P314_FX6_DONOR_FW_VERSION,
                fx6_exp_std_errno=P314_ENOENT_ERRNO,
                fx6_bracket_errno=P314_ENOENT_ERRNO,
            )
        )
        self.assertTrue(rep_ok.passed, rep_ok.errors)

        rep_bad = evaluate_exposure_std_tcub_reverse_copy_vault(
            build_default_safe_exposure_std_tcub_reverse_copy_vault_spec(
                camera_model=P314_FX6_DONOR_MODEL_NAME,
                fw_version=P314_FX6_DONOR_FW_VERSION,
                fx6_exp_std_errno=None,
                fx6_bracket_errno=P314_ENOENT_ERRNO,
            )
        )
        self.assertFalse(rep_bad.passed)
        self.assertEqual(rep_bad.block_code, P314_BLOCKED_EXP_STD_ADJ_5MODE_OR_BRACKET_DRIFT)

    def test_46_tcub_all_7_items_survive_camera_settings_reset(self) -> None:
        rep = evaluate_exposure_std_tcub_reverse_copy_vault(
            build_default_safe_exposure_std_tcub_reverse_copy_vault_spec(
                tc_preset="01:23:45.12",
                ub_preset="AB CD EF 01",
                tc_format="NDF",
                tc_run="Free Run",
                tc_make="Regenerate",
                ub_time_rec="On",
                tc_ub_disp_setting="U-Bit",
                reset_action="Camera Settings Reset",
                post_tc_preset="01:23:45.12",
                post_ub_preset="AB CD EF 01",
                post_tc_format="NDF",
                post_tc_run="Free Run",
                post_tc_make="Regenerate",
                post_ub_time_rec="On",
                post_tc_ub_disp_setting="U-Bit",
            )
        )
        self.assertTrue(rep.passed, rep.errors)

    def test_47_tcub_all_7_items_reset_only_on_initialize(self) -> None:
        rep = evaluate_exposure_std_tcub_reverse_copy_vault(
            build_default_safe_exposure_std_tcub_reverse_copy_vault_spec(
                tc_preset="01:23:45.12",
                ub_preset="AB CD EF 01",
                tc_format="NDF",
                tc_run="Free Run",
                tc_make="Regenerate",
                ub_time_rec="On",
                tc_ub_disp_setting="Counter",
                reset_action="Initialize",
                post_tc_preset=P314_TC_PRESET_DEFAULT,
                post_ub_preset=P314_UB_PRESET_DEFAULT,
                post_tc_format=P314_TC_FORMAT_DEFAULT,
                post_tc_run=P314_TC_RUN_DEFAULT,
                post_tc_make=P314_TC_MAKE_DEFAULT,
                post_ub_time_rec=P314_UB_TIME_REC_DEFAULT,
                post_tc_ub_disp_setting=P314_TCUB_DISP_DEFAULT,
            )
        )
        self.assertTrue(rep.passed, rep.errors)

        rep_bad = evaluate_exposure_std_tcub_reverse_copy_vault(
            build_default_safe_exposure_std_tcub_reverse_copy_vault_spec(
                tc_preset="01:23:45.12",
                reset_action="Camera Settings Reset",
                post_tc_preset=P314_TC_PRESET_DEFAULT,
            )
        )
        self.assertFalse(rep_bad.passed)
        self.assertEqual(rep_bad.block_code, P314_BLOCKED_TCUB_INIT_RESET_OR_FORMAT_LOCK_DRIFT)

    def test_48_tc_format_ntsc_2398p_and_24p_forced_ndf(self) -> None:
        self.assertEqual(P314_FORCED_NDF_FRAME_RATES, ("23.98p", "24.00p"))
        for fps in P314_FORCED_NDF_FRAME_RATES:
            rep = evaluate_exposure_std_tcub_reverse_copy_vault(
                build_default_safe_exposure_std_tcub_reverse_copy_vault_spec(
                    tv_system="NTSC",
                    frame_rate=fps,
                    tc_format="DF",
                    reported_tc_format_visible=True,
                    reported_tc_format_locked_ndf=True,
                    post_tc_format="NDF",
                )
            )
            self.assertTrue(rep.passed, (fps, rep.errors))

            rep_spoof = evaluate_exposure_std_tcub_reverse_copy_vault(
                build_default_safe_exposure_std_tcub_reverse_copy_vault_spec(
                    tv_system="NTSC",
                    frame_rate=fps,
                    tc_format="DF",
                    reported_tc_format_visible=True,
                    reported_tc_format_locked_ndf=False,
                    post_tc_format="DF",
                )
            )
            self.assertFalse(rep_spoof.passed)
            self.assertEqual(rep_spoof.block_code, P314_BLOCKED_TCUB_INIT_RESET_OR_FORMAT_LOCK_DRIFT)

    def test_49_tc_format_hidden_in_pal_mode(self) -> None:
        rep_ok = evaluate_exposure_std_tcub_reverse_copy_vault(
            build_default_safe_exposure_std_tcub_reverse_copy_vault_spec(
                tv_system="PAL",
                frame_rate="25.00p",
                reported_tc_format_visible=False,
                reported_tc_format_locked_ndf=False,
                post_tc_format="N/A_PAL_HIDDEN",
            )
        )
        self.assertTrue(rep_ok.passed, rep_ok.errors)

        rep_bad = evaluate_exposure_std_tcub_reverse_copy_vault(
            build_default_safe_exposure_std_tcub_reverse_copy_vault_spec(
                tv_system="PAL",
                frame_rate="25.00p",
                reported_tc_format_visible=True,
                post_tc_format="N/A_PAL_HIDDEN",
            )
        )
        self.assertFalse(rep_bad.passed)
        self.assertEqual(rep_bad.block_code, P314_BLOCKED_TCUB_INIT_RESET_OR_FORMAT_LOCK_DRIFT)

    def test_50_tcub_disp_setting_playback_toggle_movie_only(self) -> None:
        rep_still_blocked = evaluate_exposure_std_tcub_reverse_copy_vault(
            build_default_safe_exposure_std_tcub_reverse_copy_vault_spec(
                playback_media_kind="Still",
                reported_playback_disp_toggle_allowed=False,
            )
        )
        self.assertTrue(rep_still_blocked.passed, rep_still_blocked.errors)

        rep_still_spoof = evaluate_exposure_std_tcub_reverse_copy_vault(
            build_default_safe_exposure_std_tcub_reverse_copy_vault_spec(
                playback_media_kind="Still",
                reported_playback_disp_toggle_allowed=True,
            )
        )
        self.assertFalse(rep_still_spoof.passed)
        self.assertEqual(rep_still_spoof.block_code, P314_BLOCKED_TCUB_INIT_RESET_OR_FORMAT_LOCK_DRIFT)

    def test_51_fx6_physical_bnc_tc_port_boundary(self) -> None:
        rep_bad_fx3 = evaluate_exposure_std_tcub_reverse_copy_vault(
            build_default_safe_exposure_std_tcub_reverse_copy_vault_spec(
                fx3_has_physical_bnc_tc_port=True,
            )
        )
        self.assertFalse(rep_bad_fx3.passed)
        self.assertEqual(rep_bad_fx3.block_code, P314_BLOCKED_TCUB_INIT_RESET_OR_FORMAT_LOCK_DRIFT)

        rep_bad_fx6 = evaluate_exposure_std_tcub_reverse_copy_vault(
            build_default_safe_exposure_std_tcub_reverse_copy_vault_spec(
                fx6_has_physical_bnc_tc_port=False,
            )
        )
        self.assertFalse(rep_bad_fx6.passed)
        self.assertEqual(rep_bad_fx6.block_code, P314_BLOCKED_TCUB_INIT_RESET_OR_FORMAT_LOCK_DRIFT)

    def test_52_critical_reverse_copy_slot2_to_slot1_tier0_vault_fails_closed_ebusy_and_erofs(self) -> None:
        for ro_or_busy, expected_errno in ((True, "EBUSY"), (False, "EROFS")):
            st = compute_expected_playback_copy_and_slideshow_vault_state(
                camera_model=P314_FX3_MODEL_NAME,
                select_playback_media_slot=2,
                slot1_holds_tier0_vault=True,
                slot1_read_only_or_busy=ro_or_busy,
                battery_ok_for_copy=True,
                target_slot_speed_class_ok=True,
                slideshow_view_mode="Date View",
                slideshow_repeat="Off",
                slideshow_interval="3 Sec",
                slideshow_active=False,
                requested_vault_action="COPY_PLAYBACK_MEDIA",
                reset_action="None",
            )
            self.assertTrue(st["reverse_to_slot1"])
            self.assertFalse(st["action_allowed"])
            self.assertEqual(st["firewall_errno"], expected_errno)
            self.assertEqual(st["firewall_errno_num"], P314_VAULT_FIREWALL_ERRNO_CODES[expected_errno])

            rep = evaluate_exposure_std_tcub_reverse_copy_vault(
                build_default_safe_exposure_std_tcub_reverse_copy_vault_spec(
                    select_playback_media_slot=2,
                    post_select_playback_media=2,
                    slot1_holds_tier0_vault=True,
                    slot1_read_only_or_busy=ro_or_busy,
                    requested_vault_action="COPY_PLAYBACK_MEDIA",
                    reported_vault_action_allowed=False,
                    vault_firewall_errno=expected_errno,
                    slot1_data_sector_writes=0,
                    slot1_copy_avf_info_mutation_bytes=0,
                    slot1_vault_mutation_bytes=0,
                )
            )
            self.assertFalse(rep.passed, (expected_errno, rep.errors))
            self.assertEqual(rep.block_code, P314_BLOCKED_REVERSE_COPY_SLOT2_TO_SLOT1_VAULT_FIREWALL)
            self.assertEqual(rep.slot1_data_sector_writes, 0)
            self.assertEqual(rep.slot1_copy_avf_info_mutation_bytes, 0)

    def test_53_critical_reverse_copy_bypass_or_slot1_write_blocked(self) -> None:
        rep = evaluate_exposure_std_tcub_reverse_copy_vault(
            build_default_safe_exposure_std_tcub_reverse_copy_vault_spec(
                select_playback_media_slot=2,
                post_select_playback_media=2,
                slot1_holds_tier0_vault=True,
                requested_vault_action="COPY_PLAYBACK_MEDIA",
                reported_vault_action_allowed=True,
                vault_firewall_errno=None,
                reported_dest_group_and_protect_cleared=True,
                slot1_data_sector_writes=4096,
                slot1_copy_avf_info_mutation_bytes=512,
                slot1_vault_mutation_bytes=4608,
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P314_BLOCKED_REVERSE_COPY_SLOT2_TO_SLOT1_VAULT_FIREWALL)

    def test_54_forward_copy_slot1_to_slot2_allowed_clears_group_and_protect(self) -> None:
        rep = evaluate_exposure_std_tcub_reverse_copy_vault(
            build_default_safe_exposure_std_tcub_reverse_copy_vault_spec(
                select_playback_media_slot=1,
                post_select_playback_media=1,
                slot1_holds_tier0_vault=True,
                battery_ok_for_copy=True,
                target_slot_speed_class_ok=True,
                requested_vault_action="COPY_PLAYBACK_MEDIA",
                reported_vault_action_allowed=True,
                vault_firewall_errno=None,
                reported_dest_group_and_protect_cleared=True,
                slot1_data_sector_writes=0,
                slot1_copy_avf_info_mutation_bytes=0,
            )
        )
        self.assertTrue(rep.passed, rep.errors)

    def test_55_copy_low_battery_or_slow_dest_card_rejected_einval22(self) -> None:
        for overrides in (
            {"battery_ok_for_copy": False},
            {"target_slot_speed_class_ok": False},
        ):
            rep = evaluate_exposure_std_tcub_reverse_copy_vault(
                build_default_safe_exposure_std_tcub_reverse_copy_vault_spec(
                    select_playback_media_slot=1,
                    requested_vault_action="COPY_PLAYBACK_MEDIA",
                    reported_vault_action_allowed=False,
                    vault_firewall_errno="EINVAL",
                    **overrides,
                )
            )
            self.assertTrue(rep.passed, (overrides, rep.errors))

    def test_56_select_playback_media_survives_camera_reset_needs_initialize(self) -> None:
        rep_cam = evaluate_exposure_std_tcub_reverse_copy_vault(
            build_default_safe_exposure_std_tcub_reverse_copy_vault_spec(
                select_playback_media_slot=2,
                post_select_playback_media=2,
                reset_action="Camera Settings Reset",
            )
        )
        self.assertTrue(rep_cam.passed, rep_cam.errors)

        rep_init = evaluate_exposure_std_tcub_reverse_copy_vault(
            build_default_safe_exposure_std_tcub_reverse_copy_vault_spec(
                select_playback_media_slot=2,
                post_select_playback_media=1,
                reset_action="Initialize",
            )
        )
        self.assertTrue(rep_init.passed, rep_init.errors)

    def test_57_56b_format_quick_and_full_on_slot1_blocked_erofs(self) -> None:
        for fmt in ("FORMAT_QUICK", "FORMAT_FULL"):
            st = compute_expected_playback_copy_and_slideshow_vault_state(
                camera_model=P314_FX3_MODEL_NAME,
                select_playback_media_slot=1,
                slot1_holds_tier0_vault=True,
                slot1_read_only_or_busy=True,
                battery_ok_for_copy=True,
                target_slot_speed_class_ok=True,
                slideshow_view_mode="Date View",
                slideshow_repeat="Off",
                slideshow_interval="3 Sec",
                slideshow_active=False,
                requested_vault_action=fmt,
                reset_action="None",
            )
            self.assertFalse(st["action_allowed"])
            self.assertEqual(st["firewall_errno"], "EROFS")
            self.assertEqual(st["firewall_errno_num"], P314_EROFS_ERRNO)

            rep = evaluate_exposure_std_tcub_reverse_copy_vault(
                build_default_safe_exposure_std_tcub_reverse_copy_vault_spec(
                    requested_vault_action=fmt,
                    reported_vault_action_allowed=False,
                    vault_firewall_errno="EROFS",
                )
            )
            self.assertFalse(rep.passed, (fmt, rep.errors))
            self.assertEqual(rep.block_code, P314_BLOCKED_REVERSE_COPY_SLOT2_TO_SLOT1_VAULT_FIREWALL)

    def test_58_slideshow_defaults_intervals_and_initialize_only(self) -> None:
        self.assertEqual(P314_SLIDESHOW_REPEAT_DEFAULT, "Off")
        self.assertEqual(P314_SLIDESHOW_INTERVAL_DEFAULT, "3 Sec")
        self.assertEqual(P314_SLIDESHOW_INTERVALS, ("1 Sec", "3 Sec", "5 Sec", "10 Sec", "30 Sec"))
        self.assertEqual(P314_SLIDESHOW_VALID_VIEW_MODES, ("Date View", "Folder View(Still)"))
        rep_cam = evaluate_exposure_std_tcub_reverse_copy_vault(
            build_default_safe_exposure_std_tcub_reverse_copy_vault_spec(
                slideshow_view_mode="Folder View(Still)",
                slideshow_repeat="On",
                slideshow_interval="10 Sec",
                slideshow_active=True,
                reported_power_save_bypassed=True,
                reset_action="Camera Settings Reset",
                post_slideshow_repeat="On",
                post_slideshow_interval="10 Sec",
            )
        )
        self.assertTrue(rep_cam.passed, rep_cam.errors)

        rep_init = evaluate_exposure_std_tcub_reverse_copy_vault(
            build_default_safe_exposure_std_tcub_reverse_copy_vault_spec(
                slideshow_repeat="On",
                slideshow_interval="30 Sec",
                reset_action="Initialize",
                post_slideshow_repeat="Off",
                post_slideshow_interval="3 Sec",
            )
        )
        self.assertTrue(rep_init.passed, rep_init.errors)

    def test_59_slideshow_invalid_in_movie_view_or_missing_power_save_bypass(self) -> None:
        rep_bad_bypass = evaluate_exposure_std_tcub_reverse_copy_vault(
            build_default_safe_exposure_std_tcub_reverse_copy_vault_spec(
                slideshow_view_mode="Date View",
                slideshow_active=True,
                reported_power_save_bypassed=False,
            )
        )
        self.assertFalse(rep_bad_bypass.passed)
        self.assertEqual(rep_bad_bypass.block_code, P314_BLOCKED_SLIDESHOW_POWER_SAVE_OR_FX6_COPY_CLIP_SPOOF)

        rep_movie_view = evaluate_exposure_std_tcub_reverse_copy_vault(
            build_default_safe_exposure_std_tcub_reverse_copy_vault_spec(
                slideshow_view_mode="Movie View",
                slideshow_active=False,
                requested_vault_action="SLIDESHOW_PLAYBACK",
                reported_vault_action_allowed=False,
                vault_firewall_errno="EINVAL",
            )
        )
        self.assertTrue(rep_movie_view.passed, rep_movie_view.errors)

    def test_60_fx6_dormant_copy_clip_rejected(self) -> None:
        rep = evaluate_exposure_std_tcub_reverse_copy_vault(
            build_default_safe_exposure_std_tcub_reverse_copy_vault_spec(
                camera_model=P314_FX6_DONOR_MODEL_NAME,
                fw_version=P314_FX6_DONOR_FW_VERSION,
                fx6_exp_std_errno=P314_ENOENT_ERRNO,
                fx6_bracket_errno=P314_ENOENT_ERRNO,
                fx6_copy_clip_active=True,
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P314_BLOCKED_SLIDESHOW_POWER_SAVE_OR_FX6_COPY_CLIP_SPOOF)

    def test_61_56b_persistent_overlay_and_h0_h3_guards(self) -> None:
        rep_ov = evaluate_exposure_std_tcub_reverse_copy_vault(
            build_default_safe_exposure_std_tcub_reverse_copy_vault_spec(overlay_dir="/emmc/stage_b")
        )
        self.assertFalse(rep_ov.passed)
        self.assertEqual(rep_ov.block_code, P314_BLOCKED_PERSISTENT_OVERLAY_ESCAPE)

        rep_h3 = evaluate_exposure_std_tcub_reverse_copy_vault(
            build_default_safe_exposure_std_tcub_reverse_copy_vault_spec(tier0_surfaces_h0_h3_matched=15)
        )
        self.assertFalse(rep_h3.passed)
        self.assertEqual(rep_h3.block_code, P314_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT)

    def test_62_pillar_56b_6_scenario_suite_passes(self) -> None:
        res = run_pillar56b_exposure_std_tcub_reverse_copy_6_scenario_suite()
        self.assertTrue(res.passed)
        self.assertEqual(res.status, P314_STATUS_VERIFIED_PILLAR_56B)
        self.assertEqual(res.scenarios_passed, 6)
        self.assertEqual(res.scenarios_total, 6)
        self.assertTrue(all(o.passed for o in res.scenarios))

    def test_63_56b_matrix_states_and_zero_writes(self) -> None:
        rep = evaluate_exposure_std_tcub_reverse_copy_vault(
            build_default_safe_exposure_std_tcub_reverse_copy_vault_spec()
        )
        self.assertTrue(rep.passed)
        self.assertEqual(rep.matrix_states_checked, 18)
        self.assertEqual(rep.physical_device_writes, 0)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertEqual(rep.slot1_data_sector_writes, 0)
        self.assertEqual(rep.slot1_copy_avf_info_mutation_bytes, 0)

    def test_64_56b_copy_func_and_pid_symbol_names(self) -> None:
        self.assertEqual(P314_COPY_FUNC_SYMBOL, "FUNC_copy_content")
        self.assertEqual(P314_EXP_STD_ADJ_PID_SYMBOL, "PID_SET_STANDARD_EXPOSURE_SETTING")

    def test_65_56b_negative_tcub_counter_nonzero_fails(self) -> None:
        rep = evaluate_exposure_std_tcub_reverse_copy_vault(
            build_default_safe_exposure_std_tcub_reverse_copy_vault_spec(
                tcub_reset_wipe_or_format_lock_violations=1
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P314_BLOCKED_TCUB_INIT_RESET_OR_FORMAT_LOCK_DRIFT)

    def test_66_56b_negative_bracket_counter_nonzero_fails(self) -> None:
        rep = evaluate_exposure_std_tcub_reverse_copy_vault(
            build_default_safe_exposure_std_tcub_reverse_copy_vault_spec(
                bracket_settings_reset_or_fx6_spoof_events=1
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P314_BLOCKED_EXP_STD_ADJ_5MODE_OR_BRACKET_DRIFT)

    def test_67_56b_stage_b_volatile_overlay_accepts_run_and_tmp(self) -> None:
        for path_ok in (P314_STAGE_B_VOLATILE_OVERLAY_DIR, "/run/fx3-stageb"):
            rep = evaluate_exposure_std_tcub_reverse_copy_vault(
                build_default_safe_exposure_std_tcub_reverse_copy_vault_spec(overlay_dir=path_ok)
            )
            self.assertTrue(rep.passed, (path_ok, rep.errors))

    def test_68_56b_report_to_dict_serializable(self) -> None:
        rep = evaluate_exposure_std_tcub_reverse_copy_vault(
            build_default_safe_exposure_std_tcub_reverse_copy_vault_spec()
        )
        raw = json.dumps(rep.to_dict(), sort_keys=True, allow_nan=False)
        self.assertIn(P314_STATUS_VERIFIED_PILLAR_56B, raw)


class TestPhase314StandaloneMasterAndCli(unittest.TestCase):
    """Tests 69-88: Combined verifier, 56/56 Master Aggregator, fault injection, and dual-mode CLI."""

    def test_69_single_shot_combined_verifiers_both_modes(self) -> None:
        r1 = verify_switch_vh_af_stdadj_tcub_copy_vault(force_clean_room=True)
        r2 = verify_switch_vh_af_stdadj_tcub_copy_and_vault()
        self.assertTrue(r1.all_passed)
        self.assertTrue(r2.all_passed)
        self.assertEqual(r1.status, P314_STATUS_VERIFIED_PILLAR56_SUITE)
        self.assertEqual(r1.raw_firmware_bytes_leaked, 0)
        self.assertEqual(r2.slot1_data_sector_writes, 0)

    def test_70_standalone_suite_sha256_deterministic_per_mode(self) -> None:
        s1 = run_pillar56_standalone_suite(force_clean_room=True)
        s2 = run_pillar56_standalone_suite(force_clean_room=True)
        self.assertTrue(s1.all_passed)
        self.assertEqual(s1.suite_sha256, s2.suite_sha256)
        self.assertEqual(s1.pillar_56a_switch_vh_af_focus_limit_color_vault.scenarios_passed, 6)
        self.assertEqual(s1.pillar_56b_exposure_std_tcub_reverse_copy_vault.scenarios_passed, 6)

    def test_71_master_56pillar_aggregates_55pillar_plus_pillar56(self) -> None:
        m55 = evaluate_realhw_55pillar_recovery_master(force_clean_room=True)
        m56 = evaluate_realhw_56pillar_recovery_master(force_clean_room=True)
        self.assertEqual(m56.schema_version, PHASE314_MASTER_SCHEMA)
        self.assertEqual(m56.status, P314_STATUS_VERIFIED_56OF56_AGGREGATOR)
        self.assertTrue(m56.all_passed)
        self.assertGreaterEqual(m56.pillar_count, 56)
        self.assertGreaterEqual(m56.pillars_passed, 56)
        self.assertEqual(m56.pillar_count, m55.pillar_count + 1)
        ids = [p.pillar_id for p in m56.pillars]
        for pid in [p.pillar_id for p in m55.pillars]:
            self.assertIn(pid, ids)
        self.assertIn("pillar_56_switch_vh_af_stdadj_tcub_copy_vault", ids)

    def test_72_master_56_aliases_consistent(self) -> None:
        m1 = evaluate_56pillar_recovery_master(force_clean_room=True)
        m2 = verify_56pillar_recovery_suite(force_clean_room=True)
        self.assertTrue(m1.all_passed)
        self.assertTrue(m2.all_passed)
        self.assertEqual(m1.master_56pillar_sha256, m2.master_56pillar_sha256)
        self.assertEqual(m1.schema_version, "realhw_56pillar_recovery_master_v1")

    def test_73_master_56_latency_budgets_met_in_both_modes(self) -> None:
        for forced in (True, False):
            m = evaluate_realhw_56pillar_recovery_master(force_clean_room=True if forced else None)
            self.assertTrue(m.all_passed)
            self.assertLess(m.elapsed_seconds, P314_FAST_CLI_BUDGET_SECONDS + _ci_headroom())
            self.assertTrue(m.under_6s_budget or _ci_headroom() > 0)

    def test_74_master_56_zero_risk_and_wave54_counters(self) -> None:
        m = evaluate_realhw_56pillar_recovery_master(force_clean_room=True)
        self.assertEqual(m.switch_vh_af_lockout_or_coords_drift_events, 0)
        self.assertEqual(m.focus_limit_lt2_or_dormant_symbol_events, 0)
        self.assertEqual(m.focus_area_color_or_fx6_spoof_events, 0)
        self.assertEqual(m.exp_std_adj_mode_conflation_or_reset_drift_events, 0)
        self.assertEqual(m.bracket_settings_reset_or_fx6_spoof_events, 0)
        self.assertEqual(m.tcub_reset_wipe_or_format_lock_violations, 0)
        self.assertEqual(m.reverse_copy_slot2_to_slot1_bypass_events, 0)
        self.assertEqual(m.slideshow_power_save_or_fx6_copy_clip_spoof_events, 0)
        self.assertEqual(m.slot1_data_sector_writes, 0)
        self.assertEqual(m.slot1_copy_avf_info_mutation_bytes, 0)
        self.assertEqual(m.slot1_vault_mutation_bytes, 0)
        self.assertTrue(m.slot1_format_hard_locked)
        self.assertTrue(m.slot1_vault_erofs_ebusy_enforced)
        self.assertEqual(m.raw_firmware_bytes_leaked, 0)
        self.assertFalse(m.overall_ready_for_hardware_attach)
        self.assertFalse(m.cross_model_flash_authorized)
        self.assertFalse(m.hardware_live_attachment_authorized)

    def test_75_master_56_fault_injection_pillar56_fails_deterministically(self) -> None:
        m = evaluate_realhw_56pillar_recovery_master(
            force_clean_room=True,
            fault_inject_pillar="pillar_56_switch_vh_af_stdadj_tcub_copy_vault",
        )
        self.assertFalse(m.all_passed)
        self.assertEqual(m.pillars_passed, m.pillar_count - 1)
        self.assertIn("pillar_56_switch_vh_af_stdadj_tcub_copy_vault", m.failed_pillars)

    def test_76_master_56_fault_injection_pillar1_and_unknown_pillar(self) -> None:
        m = evaluate_realhw_56pillar_recovery_master(
            force_clean_room=True,
            fault_inject_pillar=MASTER_56_PILLAR_IDS[0],
        )
        self.assertFalse(m.all_passed)
        self.assertIn(MASTER_56_PILLAR_IDS[0], m.failed_pillars)

        with self.assertRaises(ValueError):
            evaluate_realhw_56pillar_recovery_master(
                force_clean_room=True,
                fault_inject_pillar="nonexistent_pillar_999",
            )

    def test_77_master_56_safety_tamper_fails(self) -> None:
        with mock.patch.object(p314, "HARDWARE_LIVE_ATTACHMENT_AUTHORIZED", True):
            with self.assertRaises(ValueError):
                evaluate_realhw_56pillar_recovery_master(force_clean_room=True)

    def test_78_master_56_json_serialization_no_nan(self) -> None:
        m = evaluate_realhw_56pillar_recovery_master(force_clean_room=True)
        raw = json.dumps(m.to_dict(), sort_keys=True, allow_nan=False)
        parsed = json.loads(raw)
        self.assertEqual(parsed["schema_version"], "realhw_56pillar_recovery_master_v1")
        self.assertGreaterEqual(parsed["pillar_count"], 56)

    def test_79_cli_inprocess_pillar56_standalone_json(self) -> None:
        buf = io.StringIO()
        with mock.patch.object(
            sys,
            "argv",
            [
                "fx3_recovery",
                "verify-pillar56-switch-vh-af-stdadj-tcub-copy-vault",
                "--force-clean-room",
                "--json",
            ],
        ):
            with redirect_stdout(buf):
                rc = cli_main.main()
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())
        self.assertTrue(payload["all_passed"])
        self.assertEqual(payload["verification_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(payload["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(payload["slot1_data_sector_writes"], 0)

    def test_80_cli_inprocess_verify_56pillar_recovery_json_and_out_file(self) -> None:
        work_tests = REPO_ROOT / "work" / "_tests"
        work_tests.mkdir(parents=True, exist_ok=True)
        out_dir = Path(tempfile.mkdtemp(prefix="p314_m56_", dir=str(work_tests)))
        shutil.rmtree(out_dir)
        try:
            buf = io.StringIO()
            with mock.patch.object(
                sys,
                "argv",
                [
                    "fx3_recovery",
                    "verify-56pillar-recovery",
                    "--force-clean-room",
                    "--json",
                    "--out",
                    str(out_dir),
                ],
            ):
                with redirect_stdout(buf):
                    rc = cli_main.main()
            self.assertEqual(rc, 0, buf.getvalue())
            payload = json.loads(buf.getvalue())
            report_file = out_dir / "56pillar-recovery-master-report.json"
            self.assertTrue(report_file.is_file())
            file_payload = json.loads(report_file.read_text(encoding="utf-8"))
            self.assertEqual(payload, file_payload)
            self.assertTrue(payload["all_passed"])
            self.assertGreaterEqual(payload["pillar_count"], 56)
            self.assertGreaterEqual(payload["pillars_passed"], 56)
            self.assertEqual(payload["schema_version"], "realhw_56pillar_recovery_master_v1")
        finally:
            shutil.rmtree(out_dir, ignore_errors=True)

    def test_81_cli_inprocess_pillar56_out_file(self) -> None:
        work_tests = REPO_ROOT / "work" / "_tests"
        work_tests.mkdir(parents=True, exist_ok=True)
        out_dir = Path(tempfile.mkdtemp(prefix="p314_p56_", dir=str(work_tests)))
        shutil.rmtree(out_dir)
        try:
            buf = io.StringIO()
            with mock.patch.object(
                sys,
                "argv",
                [
                    "fx3_recovery",
                    "verify-pillar56-switch-vh-af-stdadj-tcub-copy-vault",
                    "--force-clean-room",
                    "--json",
                    "--out",
                    str(out_dir),
                ],
            ):
                with redirect_stdout(buf):
                    rc = cli_main.main()
            self.assertEqual(rc, 0, buf.getvalue())
            report_file = out_dir / "pillar56-switch-vh-af-stdadj-tcub-copy-vault-report.json"
            self.assertTrue(report_file.is_file())
        finally:
            shutil.rmtree(out_dir, ignore_errors=True)

    def test_82_cli_inprocess_human_readable_summary_exits_zero(self) -> None:
        buf56 = io.StringIO()
        with mock.patch.object(
            sys,
            "argv",
            [
                "fx3_recovery",
                "verify-pillar56-switch-vh-af-stdadj-tcub-copy-vault",
                "--force-clean-room",
            ],
        ):
            with redirect_stdout(buf56):
                rc56 = cli_main.main()
        self.assertEqual(rc56, 0)
        self.assertIn("pillar_56a=6/6 pillar_56b=6/6", buf56.getvalue())

        bufm = io.StringIO()
        with mock.patch.object(
            sys,
            "argv",
            ["fx3_recovery", "verify-56pillar-recovery", "--force-clean-room"],
        ):
            with redirect_stdout(bufm):
                rcm = cli_main.main()
        self.assertEqual(rcm, 0)
        self.assertIn("pillars=56/56", bufm.getvalue())

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
        self.assertIn("verify-pillar56-switch-vh-af-stdadj-tcub-copy-vault", proc.stdout)
        self.assertIn("verify-56pillar-recovery", proc.stdout)

    def test_84_cli_subprocess_verify_56pillar_recovery_clean_room_json(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "fx3_recovery",
                "verify-56pillar-recovery",
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
        self.assertGreaterEqual(payload["pillar_count"], 56)
        self.assertGreaterEqual(payload["pillars_passed"], 56)
        self.assertEqual(payload["verification_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertLess(payload["elapsed_seconds"], P314_FAST_CLI_BUDGET_SECONDS + _ci_headroom())
        self.assertFalse(payload["overall_ready_for_hardware_attach"])
        self.assertFalse(payload["cross_model_flash_authorized"])
        self.assertEqual(payload["raw_firmware_bytes_leaked"], 0)

    def test_85_cli_subprocess_pillar56_fx3_clean_room_test_env_json(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "fx3_recovery",
                "verify-pillar56-switch-vh-af-stdadj-tcub-copy-vault",
                "--json",
            ],
            cwd=str(REPO_ROOT),
            env=_clean_env(**{P314_ENV_CLEAN_ROOM_TEST: "1"}),
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertTrue(payload["all_passed"])
        self.assertEqual(payload["verification_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(payload["donor_snapshot"]["donor_files_inspected"], 17)
        self.assertEqual(payload["slot1_data_sector_writes"], 0)
        self.assertEqual(payload["slot1_copy_avf_info_mutation_bytes"], 0)

    def test_86_cli_subprocess_fx3_fx6_force_clean_room_env_56pillar(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "fx3_recovery",
                "verify-56pillar-recovery",
                "--json",
            ],
            cwd=str(REPO_ROOT),
            env=_clean_env(FX3_FX6_FORCE_CLEAN_ROOM="1"),
            capture_output=True,
            text=True,
            timeout=25,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertTrue(payload["all_passed"])
        self.assertGreaterEqual(payload["pillar_count"], 56)
        self.assertEqual(payload["verification_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(payload["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(payload["slot1_data_sector_writes"], 0)

    def test_87_cli_subprocess_default_mode_exits_zero(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "fx3_recovery",
                "verify-56pillar-recovery",
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
        self.assertGreaterEqual(payload["pillar_count"], 56)
        self.assertGreaterEqual(payload["pillars_passed"], 56)
        self.assertEqual(payload["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(payload["slot1_data_sector_writes"], 0)

    def test_88_forward_compatible_discovery_in_fx3_recovery(self) -> None:
        discovered = [
            int(name[len("evaluate_realhw_") : -len("pillar_recovery_master")])
            for name in dir(fx3_recovery)
            if name.startswith("evaluate_realhw_") and name.endswith("pillar_recovery_master")
        ]
        self.assertGreaterEqual(max(discovered), 56)
        self.assertIn(56, discovered)
        self.assertGreaterEqual(len(fx3_recovery.MASTER_56_PILLAR_IDS), 56)


if __name__ == "__main__":
    unittest.main()
