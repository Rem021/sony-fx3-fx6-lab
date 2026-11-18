"""Phase 296 — Dual-mode unit tests for Pillar 52
(`[Focus Area]` 14-area hierarchy: 7 universal Still+Movie vs 7 Still-only `Tracking:`,
`[Focus Area Limit]` `>= 2`, `[Switch V/H AF Area]`, `[Focus Area Color]`,
`[Circ. of Focus Point]`, `[AF Area Registration]` `Lock Operation Parts = Off` coupling
& `Initialize`-only survival, body `W/T` `[Zoom Lever Speed]` / `[Custom Key Z. Speed]`
/ `[Remote Zoom Speed]` vs handle-less `XLR-H1` myth-bust & FX6 Smart Handle `0..99`
`Zoom Position Display` contrast; `[ISO Range Limit]` & Still-only `[ISO AUTO Min. SS]`
vs `Cine EI` Base ISO `800/12800` lockout; `[Flash Mode]` `1/250 s` Mechanical-Shutter
Still gate vs `[Video Light Mode]` `PMIC 5V <= 900 mA` rail guard; and `Slot-1`
`EROFS`/`EBUSY` Vault Firewall) and unified `52/52` recovery master
(`verify-52pillar-recovery` / `verify-pillar52-focus-area-zoom-iso-flash-vault`).
"""

from __future__ import annotations

from contextlib import redirect_stdout
from dataclasses import replace
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
    realhw_52pillar_focus_area_zoom_lever_iso_minss_flash_vault_verifier as p296,
)
from fx3_recovery.realhw_51pillar_raw_heif_colorspace_shuttertype_nr_drive_vault_verifier import (
    evaluate_realhw_51pillar_recovery_master,
)
from fx3_recovery.realhw_52pillar_focus_area_zoom_lever_iso_minss_flash_vault_verifier import (
    ALLOW_BOOT_PARTITION_TARGETING,
    ALLOW_DESTRUCTIVE_FASTBOOT,
    ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS,
    ALLOW_PERSISTENT_JIRITSU_WRITES,
    CNFLASHA_USERSPACE_WRITE_BLOCKED,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    ISP_WRITE_AUTHORIZED,
    LIVE_USB_IOKIT_TRANSMIT_ENABLED,
    MASTER_52_PILLAR_COUNT,
    MASTER_52_PILLAR_IDS,
    MASTER_52_PILLAR_SPECS,
    OTP_FUSE_TOUCHES,
    OTP_FUSE_WRITES,
    OVERALL_READY_FOR_HARDWARE_ATTACH,
    P296_AF_AREA_REG_BKID,
    P296_AF_AREA_REG_DEFAULT,
    P296_AF_AREA_REG_LOCK_OR_RESET_DRIFT_EVENTS,
    P296_BLOCKED_AF_AREA_REG_LOCK_OR_RESET_DRIFT,
    P296_BLOCKED_FLASH_STILL_MECH_GATE_VIOLATION,
    P296_BLOCKED_INVALID_PILLAR52A_SPEC,
    P296_BLOCKED_INVALID_PILLAR52B_SPEC,
    P296_BLOCKED_ISO_MINSS_OR_CINE_EI_LOCK_DRIFT,
    P296_BLOCKED_MOVIE_TRACKING_AREA_OR_LIMIT_VIOLATION,
    P296_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
    P296_BLOCKED_SAFETY_POLICY_VIOLATION,
    P296_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL,
    P296_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
    P296_BLOCKED_VIDEO_LIGHT_PMIC_900MA_OVERCURRENT,
    P296_BLOCKED_XLRH1_ZOOM_MYTH_OR_FX6_HANDLE_CONFLATION,
    P296_CINE_EI_BASE_ISOS,
    P296_CIRC_ELIGIBLE_FOCUS_AREAS,
    P296_CIRC_FOCUS_POINT_BKID,
    P296_CIRC_FOCUS_POINT_DEFAULT,
    P296_CUSTOM_KEY_ZOOM_SPEED_DEFAULT,
    P296_DONOR_INSPECT_BUDGET_SECONDS,
    P296_ENV_CLEAN_ROOM_TEST,
    P296_FAST_CLI_BUDGET_SECONDS,
    P296_FLASH_5_MODES,
    P296_FLASH_MODE_BKID,
    P296_FLASH_MODE_DEFAULT,
    P296_FLASH_STILL_MECH_GATE_VIOLATIONS,
    P296_FOCUS_AREA_14_AREAS,
    P296_FOCUS_AREA_7_STILL_TRACKING,
    P296_FOCUS_AREA_7_UNIVERSAL,
    P296_FOCUS_AREA_BKID,
    P296_FOCUS_AREA_COLOR_DEFAULT,
    P296_FOCUS_AREA_DEFAULT,
    P296_FOCUS_AREA_LIMIT_MIN_AREAS,
    P296_FX3_FW_VERSION,
    P296_FX3_HELPGUIDE_ID,
    P296_FX3_MAX_FLASH_SYNC_DENOM,
    P296_FX3_MODEL_ID,
    P296_FX3_MODEL_NAME,
    P296_FX3_SENSOR_FAMILY,
    P296_FX6_0_99_IS_ZOOM_POSITION_DISPLAY,
    P296_FX6_FOCUS_AREAS,
    P296_FX6_HAS_ISO_AUTO_MIN_SS,
    P296_FX6_MECHANICAL_SHUTTER_PRESENT,
    P296_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    P296_ISO_AUTO_MIN_SS_BKID,
    P296_ISO_AUTO_MIN_SS_DEFAULT,
    P296_ISO_AUTO_MIN_SS_OPTIONS,
    P296_ISO_AUTO_MIN_SS_RELATIVE,
    P296_ISO_MINSS_OR_CINE_EI_LOCK_DRIFT_EVENTS,
    P296_ISO_RANGE_LIMIT_BKID,
    P296_MISHOE_PMIC_5V_MAX_MA,
    P296_MISHOE_PMIC_5V_OVERCURRENT_EVENTS,
    P296_MOVIE_TRACKING_AREA_OR_LIMIT_VIOLATIONS,
    P296_OVERALL_READY_FOR_HARDWARE_ATTACH,
    P296_PINNED_FX3_APPFW_702_BYTES,
    P296_PINNED_FX3_APPFW_702_HDR4K_SHA256,
    P296_PINNED_FX3_BACKUP_BIN_BYTES,
    P296_PINNED_FX3_BACKUP_BIN_SHA256,
    P296_PINNED_FX3_UXC_EN_F_BYTES,
    P296_PINNED_FX3_UXC_EN_F_SHA256,
    P296_PINNED_FX6_APPFW_601_BYTES,
    P296_PINNED_FX6_APPFW_601_HDR4K_SHA256,
    P296_REMOTE_ZOOM_FIXED_SPEED_DEFAULT,
    P296_REMOTE_ZOOM_SPEED_TYPE_DEFAULT,
    P296_SLOT1_FORMAT_HARD_LOCKED,
    P296_SLOT1_VAULT_EROFS_EBUSY_ENFORCED,
    P296_STATUS_FAIL_52OF52_AGGREGATOR,
    P296_STATUS_FAIL_PILLAR52_SUITE,
    P296_STATUS_VERIFIED_52OF52_AGGREGATOR,
    P296_STATUS_VERIFIED_PILLAR52_SUITE,
    P296_STATUS_VERIFIED_PILLAR_52A,
    P296_STATUS_VERIFIED_PILLAR_52B,
    P296_SWITCH_VH_AF_DEFAULT,
    P296_VIDEO_LIGHT_4_MODES,
    P296_VIDEO_LIGHT_MODE_BKID,
    P296_VIDEO_LIGHT_MODE_DEFAULT,
    P296_XLRH1_HAS_REC_BUTTON,
    P296_XLRH1_HAS_ZOOM_HOLD_SWITCH,
    P296_XLRH1_HAS_ZOOM_LEVER,
    P296_XLRH1_ZOOM_OR_HOLD_SPOOF_EVENTS,
    P296_ZOOM_LEVER_1ST_SPEED_DEFAULT,
    P296_ZOOM_LEVER_2ND_SPEED_DEFAULT,
    P296_ZOOM_RANGE_DEFAULT,
    PASSIVE_TX_BYTES_EMITTED,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHASE296_PHASE_NUMBER,
    PHASE296_SCHEMA,
    PHASE296_VERSION,
    PHYSICAL_DEVICE_WRITES,
    PHYSICAL_USB_PACKETS_EMITTED,
    RAW_FIRMWARE_BYTES_LEAKED,
    READ_ONLY_DONOR_ACCESS,
    RPMB_COUNTER_INCREMENTS,
    SPI_NOR_WRITE_AUTHORIZED,
    build_default_safe_focus_area_zoom_xlrh1_vault_spec,
    build_default_safe_iso_minss_flash_videolight_vault_spec,
    compute_expected_flash_and_video_light_state,
    compute_expected_focus_area_and_af_reg_state,
    compute_expected_iso_range_minss_and_cine_ei_state,
    compute_expected_zoom_speed_and_reset_state,
    evaluate_52pillar_recovery_master,
    evaluate_focus_area_zoom_xlrh1_vault,
    evaluate_iso_minss_flash_videolight_vault,
    evaluate_realhw_52pillar_recovery_master,
    inspect_phase296_donors_readonly,
    run_pillar52_standalone_suite,
    run_pillar52a_focus_area_zoom_xlrh1_6_scenario_suite,
    run_pillar52b_iso_minss_flash_videolight_6_scenario_suite,
    verify_52pillar_recovery_suite,
    verify_focus_area_zoom_lever_iso_minss_flash_and_vault,
    verify_focus_area_zoom_lever_iso_minss_flash_vault,
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _is_ci() -> bool:
    return os.environ.get("GITHUB_ACTIONS") == "true"


def _clean_room_forced_by_env() -> bool:
    return (
        os.environ.get(P296_ENV_CLEAN_ROOM_TEST) == "1"
        or os.environ.get("FX3_FX6_FORCE_CLEAN_ROOM") == "1"
    )


class TestPhase296Pillar52And52PillarRecoveryMaster(unittest.TestCase):
    # ------------------------------------------------------------------
    # 1. Safety Invariants & Firmware Reality Constants (1..6)
    # ------------------------------------------------------------------

    def test_01_safety_constants_hard_locked(self) -> None:
        self.assertTrue(CNFLASHA_USERSPACE_WRITE_BLOCKED)
        self.assertTrue(READ_ONLY_DONOR_ACCESS)
        self.assertTrue(P296_SLOT1_FORMAT_HARD_LOCKED)
        self.assertTrue(P296_SLOT1_VAULT_EROFS_EBUSY_ENFORCED)
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(PERSISTENT_WRITE_RELEASE)
        self.assertFalse(SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        self.assertFalse(ISP_WRITE_AUTHORIZED)
        self.assertFalse(LIVE_USB_IOKIT_TRANSMIT_ENABLED)
        self.assertFalse(HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        self.assertFalse(OVERALL_READY_FOR_HARDWARE_ATTACH)
        self.assertFalse(P296_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        self.assertFalse(P296_OVERALL_READY_FOR_HARDWARE_ATTACH)
        self.assertFalse(ALLOW_BOOT_PARTITION_TARGETING)
        self.assertFalse(ALLOW_DESTRUCTIVE_FASTBOOT)
        self.assertFalse(ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS)
        self.assertFalse(ALLOW_PERSISTENT_JIRITSU_WRITES)
        self.assertEqual(OTP_FUSE_TOUCHES, 0)
        self.assertEqual(OTP_FUSE_WRITES, 0)
        self.assertEqual(RPMB_COUNTER_INCREMENTS, 0)
        self.assertEqual(PASSIVE_TX_BYTES_EMITTED, 0)
        self.assertEqual(PHYSICAL_USB_PACKETS_EMITTED, 0)
        self.assertEqual(PHYSICAL_DEVICE_WRITES, 0)
        self.assertEqual(RAW_FIRMWARE_BYTES_LEAKED, 0)

    def test_02_camera_baseline_and_phase_metadata(self) -> None:
        self.assertEqual(PHASE296_PHASE_NUMBER, 296)
        self.assertEqual(PHASE296_VERSION, "1.0.0")
        self.assertIn("52pillar", PHASE296_SCHEMA)
        self.assertEqual(P296_FX3_MODEL_NAME, "ILME-FX3")
        self.assertEqual(P296_FX3_MODEL_ID, 0x91030080)
        self.assertEqual(P296_FX3_HELPGUIDE_ID, "ilc/2210")
        self.assertEqual(P296_FX3_FW_VERSION, "7.02")
        self.assertEqual(P296_FX3_SENSOR_FAMILY, "12 MP IMX510")

    def test_03_focus_area_14_and_xlrh1_myth_bust_constants(self) -> None:
        self.assertEqual(len(P296_FOCUS_AREA_7_UNIVERSAL), 7)
        self.assertEqual(len(P296_FOCUS_AREA_7_STILL_TRACKING), 7)
        self.assertEqual(len(P296_FOCUS_AREA_14_AREAS), 14)
        self.assertEqual(P296_FOCUS_AREA_DEFAULT, "Wide")
        self.assertEqual(P296_FOCUS_AREA_LIMIT_MIN_AREAS, 2)
        self.assertEqual(P296_SWITCH_VH_AF_DEFAULT, "Off")
        self.assertEqual(P296_FOCUS_AREA_COLOR_DEFAULT, "White")
        self.assertEqual(P296_CIRC_FOCUS_POINT_DEFAULT, "Does Not Circulate")
        self.assertEqual(P296_AF_AREA_REG_DEFAULT, "Off")
        self.assertEqual(P296_FX6_FOCUS_AREAS, ("Wide", "Zone", "Flexible Spot"))
        self.assertFalse(P296_XLRH1_HAS_ZOOM_LEVER)
        self.assertFalse(P296_XLRH1_HAS_REC_BUTTON)
        self.assertFalse(P296_XLRH1_HAS_ZOOM_HOLD_SWITCH)
        self.assertTrue(P296_FX6_0_99_IS_ZOOM_POSITION_DISPLAY)
        self.assertEqual(P296_ZOOM_RANGE_DEFAULT, "Optical zoom only")
        self.assertEqual(P296_ZOOM_LEVER_1ST_SPEED_DEFAULT, 3)
        self.assertEqual(P296_ZOOM_LEVER_2ND_SPEED_DEFAULT, 8)
        self.assertEqual(P296_CUSTOM_KEY_ZOOM_SPEED_DEFAULT, 3)
        self.assertEqual(P296_REMOTE_ZOOM_SPEED_TYPE_DEFAULT, "Variable")
        self.assertEqual(P296_REMOTE_ZOOM_FIXED_SPEED_DEFAULT, 3)

    def test_04_iso_minss_flash_videolight_constants(self) -> None:
        self.assertEqual(
            P296_ISO_AUTO_MIN_SS_RELATIVE,
            ("Slower", "Slow", "Standard", "Fast", "Faster"),
        )
        self.assertEqual(P296_ISO_AUTO_MIN_SS_DEFAULT, "Standard")
        self.assertEqual(P296_CINE_EI_BASE_ISOS, (800, 12800))
        self.assertFalse(P296_FX6_HAS_ISO_AUTO_MIN_SS)
        self.assertEqual(
            P296_FLASH_5_MODES,
            ("Flash Off", "Autoflash", "Fill-flash", "Slow Sync.", "Rear Sync."),
        )
        self.assertEqual(P296_FLASH_MODE_DEFAULT, "Fill-flash")
        self.assertEqual(P296_FX3_MAX_FLASH_SYNC_DENOM, 250)
        self.assertFalse(P296_FX6_MECHANICAL_SHUTTER_PRESENT)
        self.assertEqual(
            P296_VIDEO_LIGHT_4_MODES,
            ("Power Link", "REC Link", "REC Link&STBY", "Auto"),
        )
        self.assertEqual(P296_VIDEO_LIGHT_MODE_DEFAULT, "Power Link")
        self.assertEqual(P296_MISHOE_PMIC_5V_MAX_MA, 900)
        self.assertEqual(P296_FOCUS_AREA_BKID, "BKID_APP_setting_autofocus_area_contrast_detect_af")
        self.assertEqual(P296_AF_AREA_REG_BKID, "BKID_APP_setting_register_the_af_frame")
        self.assertEqual(P296_CIRC_FOCUS_POINT_BKID, "BKID_APP_setting_circulate_of_focus_point")
        self.assertEqual(P296_ISO_RANGE_LIMIT_BKID, "BKID_APP_setting_iso_range_limit_min")
        self.assertEqual(P296_ISO_AUTO_MIN_SS_BKID, "BKID_APP_setting_iso_auto_min_s_s")
        self.assertEqual(P296_FLASH_MODE_BKID, "BKID_APP_setting_flash_mode")
        self.assertEqual(P296_VIDEO_LIGHT_MODE_BKID, "BKID_APP_setting_video_light_set")

    def test_05_master_52_pillar_specs_integrity(self) -> None:
        self.assertGreaterEqual(MASTER_52_PILLAR_COUNT, 52)
        self.assertEqual(len(MASTER_52_PILLAR_SPECS), MASTER_52_PILLAR_COUNT)
        self.assertEqual(MASTER_52_PILLAR_SPECS[51][0], 52)
        self.assertEqual(
            MASTER_52_PILLAR_SPECS[51][1],
            "pillar_52_focus_area_zoom_lever_iso_minss_flash_vault",
        )
        self.assertIn("pillar_52_focus_area_zoom_lever_iso_minss_flash_vault", MASTER_52_PILLAR_IDS)

    def test_06_exports_present_in_package_init_without_missing(self) -> None:
        for name in (
            "MASTER_52_PILLAR_COUNT",
            "MASTER_52_PILLAR_SPECS",
            "FocusAreaZoomLeverXlrH1VaultSpec",
            "IsoRangeMinssFlashVideolightVaultSpec",
            "Master52PillarRecoveryReport",
            "evaluate_focus_area_zoom_xlrh1_vault",
            "evaluate_iso_minss_flash_videolight_vault",
            "verify_focus_area_zoom_lever_iso_minss_flash_and_vault",
            "verify_focus_area_zoom_lever_iso_minss_flash_vault",
            "run_pillar52_standalone_suite",
            "evaluate_realhw_52pillar_recovery_master",
            "evaluate_52pillar_recovery_master",
            "verify_52pillar_recovery_suite",
        ):
            self.assertTrue(hasattr(fx3_recovery, name), f"Missing export: {name}")
            self.assertIn(name, fx3_recovery.__all__)

    # ------------------------------------------------------------------
    # 2. Bounded O_RDONLY Donor Inspection & Clean-Room Fallback (7..14)
    # ------------------------------------------------------------------

    def test_07_inspect_donors_default_mode_and_17_artifacts(self) -> None:
        snap = inspect_phase296_donors_readonly()
        self.assertTrue(snap.all_donors_present)
        self.assertEqual(snap.donor_files_inspected, 17)
        self.assertEqual(snap.raw_firmware_bytes_leaked, 0)
        budget = 0.50 if _is_ci() else P296_DONOR_INSPECT_BUDGET_SECONDS
        self.assertTrue(snap.under_0_20s_budget, f"elapsed={snap.elapsed_seconds}, budget={budget}")
        if _clean_room_forced_by_env():
            self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        else:
            self.assertIn(snap.verification_mode, ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"))

    def test_08_inspect_donors_forced_clean_room_and_env_var(self) -> None:
        snap = inspect_phase296_donors_readonly(force_clean_room=True)
        self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(snap.donor_files_inspected, 17)
        self.assertTrue(snap.all_donors_present)
        self.assertEqual(snap.raw_firmware_bytes_leaked, 0)
        with mock.patch.dict(os.environ, {P296_ENV_CLEAN_ROOM_TEST: "1"}):
            snap_env = inspect_phase296_donors_readonly()
            self.assertEqual(snap_env.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            snap_env2 = inspect_phase296_donors_readonly()
            self.assertEqual(snap_env2.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_09_inspect_donors_falls_back_when_donors_missing(self) -> None:
        with mock.patch.object(p296, "resolve_donor_path", return_value=None):
            snap = inspect_phase296_donors_readonly(force_clean_room=False)
            self.assertEqual(snap.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertEqual(snap.donor_files_inspected, 17)
            self.assertTrue(snap.all_donors_present)

    def test_10_pinned_donor_digests_match_in_local_or_clean_room(self) -> None:
        snap = inspect_phase296_donors_readonly()
        by_id = {a.artifact_id: a for a in snap.artifacts}
        self.assertEqual(by_id["fx3_appfw_702_so"].total_bytes, P296_PINNED_FX3_APPFW_702_BYTES)
        self.assertEqual(
            by_id["fx3_appfw_702_so"].digest_sha256,
            P296_PINNED_FX3_APPFW_702_HDR4K_SHA256,
        )
        self.assertEqual(by_id["fx6_appfw_601_so"].total_bytes, P296_PINNED_FX6_APPFW_601_BYTES)
        self.assertEqual(
            by_id["fx6_appfw_601_so"].digest_sha256,
            P296_PINNED_FX6_APPFW_601_HDR4K_SHA256,
        )
        self.assertEqual(by_id["fx3_backup_bin"].total_bytes, P296_PINNED_FX3_BACKUP_BIN_BYTES)
        self.assertEqual(by_id["fx3_backup_bin"].digest_sha256, P296_PINNED_FX3_BACKUP_BIN_SHA256)
        self.assertEqual(by_id["fx3_uxc_en_f"].total_bytes, P296_PINNED_FX3_UXC_EN_F_BYTES)
        self.assertEqual(by_id["fx3_uxc_en_f"].digest_sha256, P296_PINNED_FX3_UXC_EN_F_SHA256)
        self.assertTrue(all(a.matches_pinned for a in snap.artifacts))

    def test_11_o_rdonly_bounded_header_never_reads_full_appfw_so(self) -> None:
        snap = inspect_phase296_donors_readonly()
        by_id = {a.artifact_id: a for a in snap.artifacts}
        self.assertEqual(by_id["fx3_appfw_702_so"].header_bytes_read, 4096)
        self.assertEqual(by_id["fx6_appfw_601_so"].header_bytes_read, 4096)
        self.assertEqual(by_id["fx3_appfw_702_so"].digest_kind, "HEADER4K_SHA256")
        self.assertEqual(by_id["fx6_appfw_601_so"].digest_kind, "HEADER4K_SHA256")

    def test_12_safety_invariant_tamper_fails_closed(self) -> None:
        with mock.patch.object(p296, "PERSISTENT_EMMC_WRITES_AUTHORIZED", True):
            rep_a = evaluate_focus_area_zoom_xlrh1_vault(
                build_default_safe_focus_area_zoom_xlrh1_vault_spec()
            )
            self.assertFalse(rep_a.passed)
            self.assertEqual(rep_a.block_code, P296_BLOCKED_SAFETY_POLICY_VIOLATION)
            rep_b = evaluate_iso_minss_flash_videolight_vault(
                build_default_safe_iso_minss_flash_videolight_vault_spec()
            )
            self.assertFalse(rep_b.passed)
            self.assertEqual(rep_b.block_code, P296_BLOCKED_SAFETY_POLICY_VIOLATION)

    def test_13_raw_firmware_leak_tamper_fails_closed(self) -> None:
        with mock.patch.object(p296, "RAW_FIRMWARE_BYTES_LEAKED", 64):
            errs = p296._safety_invariant_errors()
            self.assertTrue(any("RAW_FIRMWARE_BYTES_LEAKED" in e for e in errs))

    def test_14_ci_donor_budget_widens_under_github_actions(self) -> None:
        with mock.patch.dict(os.environ, {"GITHUB_ACTIONS": "true"}):
            self.assertEqual(p296._donor_inspect_budget_seconds(), 0.50)
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("GITHUB_ACTIONS", None)
            self.assertEqual(p296._donor_inspect_budget_seconds(), 0.20)

    # ------------------------------------------------------------------
    # 3. Sub-Pillar 52A — Focus Area, AF Area Reg, Zoom Lever & XLR-H1 (15..36)
    # ------------------------------------------------------------------

    def test_15_default_pillar52a_passes(self) -> None:
        rep = evaluate_focus_area_zoom_xlrh1_vault(
            build_default_safe_focus_area_zoom_xlrh1_vault_spec()
        )
        self.assertTrue(rep.passed, rep.errors)
        self.assertEqual(rep.status, P296_STATUS_VERIFIED_PILLAR_52A)
        self.assertIsNone(rep.block_code)
        self.assertEqual(rep.matrix_states_checked, 14)

    def test_16_all_7_universal_focus_areas_allowed_in_still_and_movie(self) -> None:
        for domain in ("Still", "Movie", "S&Q"):
            for area in P296_FOCUS_AREA_7_UNIVERSAL:
                rep = evaluate_focus_area_zoom_xlrh1_vault(
                    build_default_safe_focus_area_zoom_xlrh1_vault_spec(
                        shooting_domain=domain,
                        configured_focus_area=area,
                        reported_focus_area=area,
                        reported_tracking_areas_allowed=(domain == "Still"),
                        reported_touch_tracking_allowed=(domain in ("Movie", "S&Q")),
                    )
                )
                self.assertTrue(rep.passed, f"{domain}/{area}: {rep.errors}")

    def test_17_all_7_tracking_focus_areas_allowed_only_in_still_pasm(self) -> None:
        for area in P296_FOCUS_AREA_7_STILL_TRACKING:
            rep = evaluate_focus_area_zoom_xlrh1_vault(
                build_default_safe_focus_area_zoom_xlrh1_vault_spec(
                    shooting_domain="Still",
                    shooting_mode="M",
                    configured_focus_area=area,
                    reported_focus_area=area,
                    reported_tracking_areas_allowed=True,
                )
            )
            self.assertTrue(rep.passed, f"{area}: {rep.errors}")

    def test_18_tracking_focus_area_blocked_in_movie_and_sq(self) -> None:
        for domain in ("Movie", "S&Q"):
            for area in ("Tracking: Wide", "Tracking: Spot M", "Tracking: Expand Spot"):
                rep = evaluate_focus_area_zoom_xlrh1_vault(
                    build_default_safe_focus_area_zoom_xlrh1_vault_spec(
                        shooting_domain=domain,
                        configured_focus_area=area,
                        reported_focus_area=area,
                        reported_tracking_areas_allowed=True,
                        reported_touch_tracking_allowed=True,
                    )
                )
                self.assertFalse(rep.passed)
                self.assertEqual(
                    rep.block_code, P296_BLOCKED_MOVIE_TRACKING_AREA_OR_LIMIT_VIOLATION
                )

    def test_19_touch_tracking_unavailable_in_mf_or_clear_image_zoom(self) -> None:
        # Movie AF-C + Optical -> Touch Tracking allowed
        res = compute_expected_focus_area_and_af_reg_state(
            shooting_domain="Movie",
            shooting_mode="M",
            focus_mode="AF-C",
            zoom_range="Optical zoom only",
            configured_focus_area="Wide",
            focus_area_limit_enabled_areas=P296_FOCUS_AREA_14_AREAS,
            pre_af_area_reg="Off",
            configured_lock_operation_parts="Off",
            configured_focus_area_color="White",
            reset_action="None",
        )
        self.assertFalse(res[0])  # tracking_areas_allowed False in Movie
        self.assertTrue(res[3])   # touch_tracking_allowed True

        # MF blocks Touch Tracking
        res_mf = compute_expected_focus_area_and_af_reg_state(
            shooting_domain="Movie",
            shooting_mode="M",
            focus_mode="MF",
            zoom_range="Optical zoom only",
            configured_focus_area="Wide",
            focus_area_limit_enabled_areas=P296_FOCUS_AREA_14_AREAS,
            pre_af_area_reg="Off",
            configured_lock_operation_parts="Off",
            configured_focus_area_color="White",
            reset_action="None",
        )
        self.assertFalse(res_mf[3])

        # ClearImage Zoom blocks Touch Tracking
        res_ciz = compute_expected_focus_area_and_af_reg_state(
            shooting_domain="S&Q",
            shooting_mode="M",
            focus_mode="AF-C",
            zoom_range="ClearImage Zoom",
            configured_focus_area="Wide",
            focus_area_limit_enabled_areas=P296_FOCUS_AREA_14_AREAS,
            pre_af_area_reg="Off",
            configured_lock_operation_parts="Off",
            configured_focus_area_color="White",
            reset_action="None",
        )
        self.assertFalse(res_ciz[3])

    def test_20_focus_area_limit_requires_at_least_2_areas(self) -> None:
        rep_ok = evaluate_focus_area_zoom_xlrh1_vault(
            build_default_safe_focus_area_zoom_xlrh1_vault_spec(
                focus_area_limit_enabled_areas=("Wide", "Spot: M"),
            )
        )
        self.assertTrue(rep_ok.passed)

        rep_bad = evaluate_focus_area_zoom_xlrh1_vault(
            build_default_safe_focus_area_zoom_xlrh1_vault_spec(
                focus_area_limit_enabled_areas=("Wide",),
            )
        )
        self.assertFalse(rep_bad.passed)
        self.assertEqual(rep_bad.block_code, P296_BLOCKED_MOVIE_TRACKING_AREA_OR_LIMIT_VIOLATION)

    def test_21_focus_area_limit_rejects_duplicate_or_unknown_areas(self) -> None:
        rep_dup = evaluate_focus_area_zoom_xlrh1_vault(
            build_default_safe_focus_area_zoom_xlrh1_vault_spec(
                focus_area_limit_enabled_areas=("Wide", "Wide"),
            )
        )
        self.assertFalse(rep_dup.passed)
        rep_unk = evaluate_focus_area_zoom_xlrh1_vault(
            build_default_safe_focus_area_zoom_xlrh1_vault_spec(
                focus_area_limit_enabled_areas=("Wide", "Flexible Spot"),
            )
        )
        self.assertFalse(rep_unk.passed)

    def test_22_switch_vh_af_area_still_only_gate(self) -> None:
        rep_still = evaluate_focus_area_zoom_xlrh1_vault(
            build_default_safe_focus_area_zoom_xlrh1_vault_spec(
                shooting_domain="Still",
                switch_vh_af_area="AF Point + AF Area",
            )
        )
        self.assertTrue(rep_still.passed)
        rep_movie = evaluate_focus_area_zoom_xlrh1_vault(
            build_default_safe_focus_area_zoom_xlrh1_vault_spec(
                shooting_domain="Movie",
                reported_tracking_areas_allowed=False,
                reported_touch_tracking_allowed=True,
                switch_vh_af_area="AF Point Only",
            )
        )
        self.assertFalse(rep_movie.passed)

    def test_23_circ_of_focus_point_wraps_hv_on_10_eligible_areas(self) -> None:
        self.assertEqual(len(P296_CIRC_ELIGIBLE_FOCUS_AREAS), 10)
        for area in P296_CIRC_ELIGIBLE_FOCUS_AREAS:
            rep = evaluate_focus_area_zoom_xlrh1_vault(
                build_default_safe_focus_area_zoom_xlrh1_vault_spec(
                    configured_focus_area=area,
                    reported_focus_area=area,
                    circ_of_focus_point="Circulate",
                )
            )
            self.assertTrue(rep.passed, f"{area}: {rep.errors}")

    def test_24_af_area_registration_forces_lock_operation_parts_off(self) -> None:
        rep_ok = evaluate_focus_area_zoom_xlrh1_vault(
            build_default_safe_focus_area_zoom_xlrh1_vault_spec(
                pre_af_area_reg="On",
                post_af_area_reg="On",
                configured_lock_operation_parts="On",
                reported_lock_operation_parts="Off",
            )
        )
        self.assertTrue(rep_ok.passed)

        rep_bad = evaluate_focus_area_zoom_xlrh1_vault(
            build_default_safe_focus_area_zoom_xlrh1_vault_spec(
                pre_af_area_reg="On",
                post_af_area_reg="On",
                configured_lock_operation_parts="On",
                reported_lock_operation_parts="On",
            )
        )
        self.assertFalse(rep_bad.passed)
        self.assertEqual(rep_bad.block_code, P296_BLOCKED_AF_AREA_REG_LOCK_OR_RESET_DRIFT)

    def test_25_af_area_registration_survives_camset_reset_cleared_only_by_initialize_or_del(self) -> None:
        # Camera Settings Reset keeps AF Area Reg On
        rep_keep = evaluate_focus_area_zoom_xlrh1_vault(
            build_default_safe_focus_area_zoom_xlrh1_vault_spec(
                pre_af_area_reg="On",
                post_af_area_reg="On",
                reset_action="Camera Settings Reset",
                configured_focus_area_color="Red",
                post_focus_area_color="Red",
            )
        )
        self.assertTrue(rep_keep.passed)

        # Initialize resets AF Area Reg & Focus Area Color & Zoom Range
        rep_init = evaluate_focus_area_zoom_xlrh1_vault(
            build_default_safe_focus_area_zoom_xlrh1_vault_spec(
                pre_af_area_reg="On",
                post_af_area_reg="Off",
                configured_focus_area_color="Red",
                post_focus_area_color="White",
                zoom_range="ClearImage Zoom",
                post_zoom_range="Optical zoom only",
                reset_action="Initialize",
            )
        )
        self.assertTrue(rep_init.passed)

        # Del. Regist. AF Area resets AF Area Reg to Off
        rep_del = evaluate_focus_area_zoom_xlrh1_vault(
            build_default_safe_focus_area_zoom_xlrh1_vault_spec(
                pre_af_area_reg="On",
                post_af_area_reg="Off",
                del_regist_af_area_invoked=True,
            )
        )
        self.assertTrue(rep_del.passed)

        # Claiming Camera Settings Reset cleared AF Area Reg must be rejected
        rep_wipe_bad = evaluate_focus_area_zoom_xlrh1_vault(
            build_default_safe_focus_area_zoom_xlrh1_vault_spec(
                pre_af_area_reg="On",
                post_af_area_reg="Off",
                reset_action="Camera Settings Reset",
            )
        )
        self.assertFalse(rep_wipe_bad.passed)
        self.assertEqual(rep_wipe_bad.block_code, P296_BLOCKED_AF_AREA_REG_LOCK_OR_RESET_DRIFT)

    def test_26_xlrh1_myth_bust_rejects_zoom_lever_rec_btn_or_zoom_hold_switch(self) -> None:
        for kwargs in (
            {"xlrh1_has_zoom_lever": True},
            {"xlrh1_has_rec_button": True},
            {"xlrh1_has_zoom_hold_switch": True},
            {"xlrh1_zoom_or_hold_spoof_events": 1},
        ):
            rep = evaluate_focus_area_zoom_xlrh1_vault(
                build_default_safe_focus_area_zoom_xlrh1_vault_spec(**kwargs)
            )
            self.assertFalse(rep.passed)
            self.assertEqual(
                rep.block_code, P296_BLOCKED_XLRH1_ZOOM_MYTH_OR_FX6_HANDLE_CONFLATION
            )

    def test_27_fx6_smart_handle_and_0_99_zoom_position_display_contrast(self) -> None:
        rep_bad1 = evaluate_focus_area_zoom_xlrh1_vault(
            build_default_safe_focus_area_zoom_xlrh1_vault_spec(
                fx6_zoom_0_99_is_position_display=False
            )
        )
        self.assertFalse(rep_bad1.passed)
        self.assertEqual(rep_bad1.block_code, P296_BLOCKED_XLRH1_ZOOM_MYTH_OR_FX6_HANDLE_CONFLATION)

        rep_bad2 = evaluate_focus_area_zoom_xlrh1_vault(
            build_default_safe_focus_area_zoom_xlrh1_vault_spec(
                fx6_focus_areas=("Wide", "Zone", "Tracking: Wide")
            )
        )
        self.assertFalse(rep_bad2.passed)
        self.assertEqual(rep_bad2.block_code, P296_BLOCKED_MOVIE_TRACKING_AREA_OR_LIMIT_VIOLATION)

    def test_28_body_zoom_lever_speeds_1st_3_2nd_8_custom_and_remote_variable_fixed(self) -> None:
        rep_var = evaluate_focus_area_zoom_xlrh1_vault(
            build_default_safe_focus_area_zoom_xlrh1_vault_spec(
                pre_zoom_lever_1st_stby=3,
                pre_zoom_lever_2nd_stby=8,
                pre_custom_key_zoom_stby=5,
                post_custom_key_zoom_stby=5,
                pre_remote_zoom_speed_type="Fixed",
                post_remote_zoom_speed_type="Fixed",
                pre_remote_zoom_fixed_stby=6,
                post_remote_zoom_fixed_stby=6,
            )
        )
        self.assertTrue(rep_var.passed)

        # Out-of-range speed 9 rejected fail-closed
        rep_9 = evaluate_focus_area_zoom_xlrh1_vault(
            build_default_safe_focus_area_zoom_xlrh1_vault_spec(pre_zoom_lever_2nd_stby=9)
        )
        self.assertFalse(rep_9.passed)
        self.assertEqual(rep_9.block_code, P296_BLOCKED_INVALID_PILLAR52A_SPEC)

    def test_29_zoom_speeds_reset_on_camset_reset_while_zoom_range_survives(self) -> None:
        res = compute_expected_zoom_speed_and_reset_state(
            zoom_range="ClearImage Zoom",
            file_format="XAVC S 4K",
            frame_rate_fps=24,
            pre_zoom_lever_1st_stby=6,
            pre_zoom_lever_2nd_stby=2,
            pre_custom_key_zoom_stby=7,
            pre_remote_zoom_speed_type="Fixed",
            pre_remote_zoom_fixed_stby=5,
            reset_action="Camera Settings Reset",
        )
        self.assertTrue(res[0])
        self.assertEqual(res[1], "ClearImage Zoom")
        self.assertEqual(res[2], 3)
        self.assertEqual(res[3], 8)
        self.assertEqual(res[4], 3)
        self.assertEqual(res[5], "Variable")
        self.assertEqual(res[6], 3)

    def test_30_ciz_and_digital_zoom_blocked_in_raw_or_120p(self) -> None:
        rep_raw = evaluate_focus_area_zoom_xlrh1_vault(
            build_default_safe_focus_area_zoom_xlrh1_vault_spec(
                zoom_range="ClearImage Zoom",
                post_zoom_range="ClearImage Zoom",
                file_format="RAW",
            )
        )
        self.assertFalse(rep_raw.passed)
        self.assertEqual(rep_raw.block_code, P296_BLOCKED_XLRH1_ZOOM_MYTH_OR_FX6_HANDLE_CONFLATION)

        rep_120 = evaluate_focus_area_zoom_xlrh1_vault(
            build_default_safe_focus_area_zoom_xlrh1_vault_spec(
                zoom_range="Digital Zoom",
                post_zoom_range="Digital Zoom",
                file_format="XAVC S 4K",
                frame_rate_fps=120,
            )
        )
        self.assertFalse(rep_120.passed)

    def test_31_slot1_focus_zoom_camset_write_blocked(self) -> None:
        rep = evaluate_focus_area_zoom_xlrh1_vault(
            build_default_safe_focus_area_zoom_xlrh1_vault_spec(
                target_focus_zoom_slot=1,
                camset_af_zoom_targets_slot1=True,
                requested_vault_action="CAMSET_FOCUS_ZOOM_WRITE",
                slot1_focus_zoom_camset_mutation_bytes=4096,
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P296_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL)

    def test_32_pillar52a_persistent_overlay_escape_rejected(self) -> None:
        rep = evaluate_focus_area_zoom_xlrh1_vault(
            build_default_safe_focus_area_zoom_xlrh1_vault_spec(overlay_dir="/setting/52a")
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P296_BLOCKED_PERSISTENT_OVERLAY_ESCAPE)

    def test_33_pillar52a_backup_bin_h0_h3_drift_rejected(self) -> None:
        rep = evaluate_focus_area_zoom_xlrh1_vault(
            build_default_safe_focus_area_zoom_xlrh1_vault_spec(
                backup_bin_h3_sha256="f" * 64,
                tier0_surfaces_h0_h3_matched=15,
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P296_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT)

    def test_34_pillar52a_invalid_spec_enums_rejected(self) -> None:
        rep = evaluate_focus_area_zoom_xlrh1_vault(
            build_default_safe_focus_area_zoom_xlrh1_vault_spec(camera_model="ILME-FX9")
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P296_BLOCKED_INVALID_PILLAR52A_SPEC)

    def test_35_pillar52a_digest_is_deterministic(self) -> None:
        s = build_default_safe_focus_area_zoom_xlrh1_vault_spec()
        r1 = evaluate_focus_area_zoom_xlrh1_vault(s)
        r2 = evaluate_focus_area_zoom_xlrh1_vault(s)
        self.assertEqual(r1.digest_sha256, r2.digest_sha256)

    def test_36_run_pillar52a_6_scenario_suite_passes(self) -> None:
        suite = run_pillar52a_focus_area_zoom_xlrh1_6_scenario_suite()
        self.assertTrue(suite.passed)
        self.assertEqual(suite.scenarios_passed, 6)
        self.assertEqual(suite.scenarios_total, 6)
        self.assertTrue(suite.scenarios[0].actual_allowed)
        self.assertTrue(suite.scenarios[1].actual_allowed)
        for s in suite.scenarios[2:]:
            self.assertFalse(s.actual_allowed)

    # ------------------------------------------------------------------
    # 4. Sub-Pillar 52B — ISO Range Limit, ISO AUTO Min. SS, Cine EI,
    #    Flash Still Mech Gate, Video Light PMIC 900 mA & Slot-1 Vault (37..58)
    # ------------------------------------------------------------------

    def test_37_default_pillar52b_passes(self) -> None:
        rep = evaluate_iso_minss_flash_videolight_vault(
            build_default_safe_iso_minss_flash_videolight_vault_spec()
        )
        self.assertTrue(rep.passed, rep.errors)
        self.assertEqual(rep.status, P296_STATUS_VERIFIED_PILLAR_52B)
        self.assertIsNone(rep.block_code)
        self.assertEqual(rep.matrix_states_checked, 14)

    def test_38_iso_range_limit_clamps_manual_and_iso_auto(self) -> None:
        # Clamp below min (50 -> 100) and above max (25600 -> 12800)
        res_low = compute_expected_iso_range_minss_and_cine_ei_state(
            shooting_domain="Still",
            shooting_mode="M",
            log_shooting_mode="Off",
            cine_ei_base_iso=800,
            iso_mode="Manual",
            requested_iso=50,
            iso_range_limit_min=100,
            iso_range_limit_max=12800,
            configured_iso_auto_min_ss="Standard",
            reset_action="None",
        )
        self.assertEqual(res_low[3], 100)
        self.assertFalse(res_low[1])  # M + Manual -> ISO AUTO Min. SS inactive

        res_high = compute_expected_iso_range_minss_and_cine_ei_state(
            shooting_domain="Still",
            shooting_mode="M",
            log_shooting_mode="Off",
            cine_ei_base_iso=800,
            iso_mode="ISO AUTO",
            requested_iso=25600,
            iso_range_limit_min=100,
            iso_range_limit_max=12800,
            configured_iso_auto_min_ss="Fast",
            reset_action="None",
        )
        self.assertEqual(res_high[3], 12800)
        self.assertTrue(res_high[1])  # M + ISO AUTO -> ISO AUTO Min. SS active

    def test_39_iso_auto_min_ss_supports_relative_5_and_manual_thresholds_in_still(self) -> None:
        for val in ("Slower", "Slow", "Standard", "Fast", "Faster", "1/8000", "1/250", '30"'):
            self.assertIn(val, P296_ISO_AUTO_MIN_SS_OPTIONS)
            rep = evaluate_iso_minss_flash_videolight_vault(
                build_default_safe_iso_minss_flash_videolight_vault_spec(
                    shooting_domain="Still",
                    shooting_mode="P",
                    iso_mode="ISO AUTO",
                    configured_iso_auto_min_ss=val,
                    post_iso_auto_min_ss=val,
                    reported_iso_auto_min_ss_active=True,
                )
            )
            self.assertTrue(rep.passed, f"{val}: {rep.errors}")

    def test_40_iso_auto_min_ss_locked_out_in_movie_and_sq(self) -> None:
        for domain in ("Movie", "S&Q"):
            rep_ok = evaluate_iso_minss_flash_videolight_vault(
                build_default_safe_iso_minss_flash_videolight_vault_spec(
                    shooting_domain=domain,
                    shooting_mode="M",
                    reported_iso_auto_min_ss_active=False,
                    reported_auto_slow_shutter_allowed=True,
                    reported_flash_allowed=False,
                )
            )
            self.assertTrue(rep_ok.passed, f"{domain}: {rep_ok.errors}")

            rep_bad = evaluate_iso_minss_flash_videolight_vault(
                build_default_safe_iso_minss_flash_videolight_vault_spec(
                    shooting_domain=domain,
                    shooting_mode="P",
                    reported_iso_auto_min_ss_active=True,
                    reported_auto_slow_shutter_allowed=True,
                    reported_flash_allowed=False,
                )
            )
            self.assertFalse(rep_bad.passed)
            self.assertEqual(rep_bad.block_code, P296_BLOCKED_ISO_MINSS_OR_CINE_EI_LOCK_DRIFT)

    def test_41_cine_ei_and_cine_ei_quick_pin_base_iso_800_or_12800_and_lock_all(self) -> None:
        for log_mode in ("Cine EI", "Cine EI Quick"):
            for base_iso in (800, 12800):
                rep_ok = evaluate_iso_minss_flash_videolight_vault(
                    build_default_safe_iso_minss_flash_videolight_vault_spec(
                        shooting_domain="Movie",
                        shooting_mode="M",
                        log_shooting_mode=log_mode,
                        cine_ei_base_iso=base_iso,
                        requested_iso=6400,
                        reported_iso=base_iso,
                        reported_iso_range_limit_active=False,
                        reported_iso_auto_min_ss_active=False,
                        reported_auto_slow_shutter_allowed=False,
                        reported_flash_allowed=False,
                    )
                )
                self.assertTrue(rep_ok.passed, f"{log_mode}/{base_iso}: {rep_ok.errors}")

            rep_bad = evaluate_iso_minss_flash_videolight_vault(
                build_default_safe_iso_minss_flash_videolight_vault_spec(
                    shooting_domain="Movie",
                    shooting_mode="M",
                    log_shooting_mode=log_mode,
                    cine_ei_base_iso=800,
                    requested_iso=3200,
                    reported_iso=3200,
                    reported_iso_range_limit_active=True,
                    reported_iso_auto_min_ss_active=False,
                    reported_auto_slow_shutter_allowed=True,
                    reported_flash_allowed=False,
                )
            )
            self.assertFalse(rep_bad.passed)
            self.assertEqual(rep_bad.block_code, P296_BLOCKED_ISO_MINSS_OR_CINE_EI_LOCK_DRIFT)

    def test_42_flexible_iso_keeps_iso_range_limit_active(self) -> None:
        rep = evaluate_iso_minss_flash_videolight_vault(
            build_default_safe_iso_minss_flash_videolight_vault_spec(
                shooting_domain="Movie",
                shooting_mode="M",
                log_shooting_mode="Flexible ISO",
                requested_iso=25600,
                reported_iso=12800,
                iso_range_limit_min=100,
                iso_range_limit_max=12800,
                reported_iso_range_limit_active=True,
                reported_iso_auto_min_ss_active=False,
                reported_auto_slow_shutter_allowed=True,
                reported_flash_allowed=False,
            )
        )
        self.assertTrue(rep.passed, rep.errors)

    def test_43_fx6_has_zero_iso_auto_min_ss_or_mechanical_shutter(self) -> None:
        rep_minss = evaluate_iso_minss_flash_videolight_vault(
            build_default_safe_iso_minss_flash_videolight_vault_spec(fx6_has_iso_auto_min_ss=True)
        )
        self.assertFalse(rep_minss.passed)
        self.assertEqual(rep_minss.block_code, P296_BLOCKED_ISO_MINSS_OR_CINE_EI_LOCK_DRIFT)

        rep_mech = evaluate_iso_minss_flash_videolight_vault(
            build_default_safe_iso_minss_flash_videolight_vault_spec(
                fx6_mechanical_shutter_present=True
            )
        )
        self.assertFalse(rep_mech.passed)
        self.assertEqual(rep_mech.block_code, P296_BLOCKED_FLASH_STILL_MECH_GATE_VIOLATION)

    def test_44_all_5_flash_modes_supported_in_mechanical_still_with_1_250_sync(self) -> None:
        for mode in P296_FLASH_5_MODES:
            rep = evaluate_iso_minss_flash_videolight_vault(
                build_default_safe_iso_minss_flash_videolight_vault_spec(
                    configured_flash_mode=mode,
                    post_flash_mode=mode,
                    flash_fired=(mode != "Flash Off"),
                    reported_flash_allowed=True,
                )
            )
            self.assertTrue(rep.passed, f"{mode}: {rep.errors}")

    def test_45_flash_strictly_blocked_in_movie_and_sq(self) -> None:
        for domain in ("Movie", "S&Q"):
            rep = evaluate_iso_minss_flash_videolight_vault(
                build_default_safe_iso_minss_flash_videolight_vault_spec(
                    shooting_domain=domain,
                    reported_iso_auto_min_ss_active=False,
                    reported_auto_slow_shutter_allowed=True,
                    reported_flash_allowed=True,
                    flash_fired=True,
                )
            )
            self.assertFalse(rep.passed)
            self.assertEqual(rep.block_code, P296_BLOCKED_FLASH_STILL_MECH_GATE_VIOLATION)

    def test_46_flash_strictly_blocked_in_electronic_shutter_and_silent_mode(self) -> None:
        rep_elec = evaluate_iso_minss_flash_videolight_vault(
            build_default_safe_iso_minss_flash_videolight_vault_spec(
                shutter_type="Electronic Shutter",
                reported_flash_allowed=True,
                flash_fired=True,
            )
        )
        self.assertFalse(rep_elec.passed)
        self.assertEqual(rep_elec.block_code, P296_BLOCKED_FLASH_STILL_MECH_GATE_VIOLATION)

        rep_silent = evaluate_iso_minss_flash_videolight_vault(
            build_default_safe_iso_minss_flash_videolight_vault_spec(
                silent_mode="On",
                silent_mode_target_override_shutter=False,
                reported_flash_allowed=True,
            )
        )
        self.assertFalse(rep_silent.passed)
        self.assertEqual(rep_silent.block_code, P296_BLOCKED_FLASH_STILL_MECH_GATE_VIOLATION)

        # Silent Mode with Target Function override allows mechanical shutter flash
        rep_override = evaluate_iso_minss_flash_videolight_vault(
            build_default_safe_iso_minss_flash_videolight_vault_spec(
                silent_mode="On",
                silent_mode_target_override_shutter=True,
                reported_flash_allowed=True,
                flash_fired=True,
            )
        )
        self.assertTrue(rep_override.passed, rep_override.errors)

    def test_47_flash_sync_ceiling_exceeding_250_rejected(self) -> None:
        rep = evaluate_iso_minss_flash_videolight_vault(
            build_default_safe_iso_minss_flash_videolight_vault_spec(flash_sync_speed_denom=500)
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P296_BLOCKED_FLASH_STILL_MECH_GATE_VIOLATION)

    def test_48_video_light_all_4_modes_span_still_movie_sq_under_900ma(self) -> None:
        for domain in ("Still", "Movie", "S&Q"):
            for vl_mode in P296_VIDEO_LIGHT_4_MODES:
                rep = evaluate_iso_minss_flash_videolight_vault(
                    build_default_safe_iso_minss_flash_videolight_vault_spec(
                        shooting_domain=domain,
                        reported_iso_auto_min_ss_active=(domain == "Still"),
                        reported_auto_slow_shutter_allowed=(domain != "Still"),
                        reported_flash_allowed=(domain == "Still"),
                        configured_video_light_mode=vl_mode,
                        reported_video_light_allowed=True,
                        mishoe_5v_draw_ma=900,
                    )
                )
                self.assertTrue(rep.passed, f"{domain}/{vl_mode}: {rep.errors}")

    def test_49_video_light_pmic_5v_over_900ma_rejected_fail_closed(self) -> None:
        rep = evaluate_iso_minss_flash_videolight_vault(
            build_default_safe_iso_minss_flash_videolight_vault_spec(
                mishoe_5v_draw_ma=901,
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P296_BLOCKED_VIDEO_LIGHT_PMIC_900MA_OVERCURRENT)

    def test_50_non_sony_flash_over_250v_rejected_fail_closed(self) -> None:
        rep = evaluate_iso_minss_flash_videolight_vault(
            build_default_safe_iso_minss_flash_videolight_vault_spec(
                non_sony_flash_trigger_voltage_v=260.0
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P296_BLOCKED_VIDEO_LIGHT_PMIC_900MA_OVERCURRENT)

    def test_51_camset_reset_restores_flash_mode_fill_flash_and_iso_minss_standard(self) -> None:
        rep = evaluate_iso_minss_flash_videolight_vault(
            build_default_safe_iso_minss_flash_videolight_vault_spec(
                configured_flash_mode="Rear Sync.",
                post_flash_mode="Fill-flash",
                configured_iso_auto_min_ss="Faster",
                post_iso_auto_min_ss="Standard",
                reset_action="Camera Settings Reset",
            )
        )
        self.assertTrue(rep.passed, rep.errors)

    def test_52_slot1_flash_videolight_imagedb_mutation_blocked(self) -> None:
        rep = evaluate_iso_minss_flash_videolight_vault(
            build_default_safe_iso_minss_flash_videolight_vault_spec(
                target_capture_slot=1,
                avf_info_imagedb_targets_slot1=True,
                requested_vault_action="STILL_FLASH_CAPTURE_WRITE",
                slot1_flash_videolight_imagedb_bytes=4096,
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P296_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL)

    def test_53_pillar52b_persistent_overlay_escape_rejected(self) -> None:
        rep = evaluate_iso_minss_flash_videolight_vault(
            build_default_safe_iso_minss_flash_videolight_vault_spec(overlay_dir="/dev/cnflasha")
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P296_BLOCKED_PERSISTENT_OVERLAY_ESCAPE)

    def test_54_pillar52b_backup_bin_h0_h3_drift_rejected(self) -> None:
        rep = evaluate_iso_minss_flash_videolight_vault(
            build_default_safe_iso_minss_flash_videolight_vault_spec(
                backup_bin_h3_sha256="a" * 64,
                tier0_surfaces_h0_h3_matched=15,
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P296_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT)

    def test_55_pillar52b_invalid_spec_rejected(self) -> None:
        rep = evaluate_iso_minss_flash_videolight_vault(
            build_default_safe_iso_minss_flash_videolight_vault_spec(
                iso_range_limit_min=6400,
                iso_range_limit_max=1600,
            )
        )
        self.assertFalse(rep.passed)
        self.assertEqual(rep.block_code, P296_BLOCKED_INVALID_PILLAR52B_SPEC)

    def test_56_pillar52b_digest_is_deterministic(self) -> None:
        s = build_default_safe_iso_minss_flash_videolight_vault_spec()
        r1 = evaluate_iso_minss_flash_videolight_vault(s)
        r2 = evaluate_iso_minss_flash_videolight_vault(s)
        self.assertEqual(r1.digest_sha256, r2.digest_sha256)

    def test_57_compute_expected_flash_video_light_helper(self) -> None:
        allowed, post_f, vl_ok, pmic_ok = compute_expected_flash_and_video_light_state(
            camera_model="ILME-FX6",
            shooting_domain="Still",
            shutter_type="Mechanical Shutter",
            silent_mode="Off",
            silent_mode_target_override_shutter=False,
            configured_flash_mode="Fill-flash",
            configured_video_light_mode="Power Link",
            mishoe_5v_draw_ma=500,
            reset_action="None",
        )
        self.assertFalse(allowed)
        self.assertEqual(post_f, "Fill-flash")
        self.assertTrue(vl_ok)
        self.assertTrue(pmic_ok)

    def test_58_run_pillar52b_6_scenario_suite_passes(self) -> None:
        suite = run_pillar52b_iso_minss_flash_videolight_6_scenario_suite()
        self.assertTrue(suite.passed)
        self.assertEqual(suite.scenarios_passed, 6)
        self.assertEqual(suite.scenarios_total, 6)
        self.assertTrue(suite.scenarios[0].actual_allowed)
        self.assertTrue(suite.scenarios[1].actual_allowed)
        for s in suite.scenarios[2:]:
            self.assertFalse(s.actual_allowed)

    # ------------------------------------------------------------------
    # 5. Combined Verifier & Standalone Pillar 52 Suite (59..64)
    # ------------------------------------------------------------------

    def test_59_combined_verifier_passes_and_alias_matches(self) -> None:
        r1 = verify_focus_area_zoom_lever_iso_minss_flash_and_vault(force_clean_room=True)
        r2 = verify_focus_area_zoom_lever_iso_minss_flash_vault(force_clean_room=True)
        self.assertTrue(r1.all_passed)
        self.assertTrue(r2.passed)
        self.assertEqual(r1.status, P296_STATUS_VERIFIED_PILLAR52_SUITE)
        self.assertEqual(r1.slot1_vault_mutation_bytes, 0)
        self.assertEqual(r1.raw_firmware_bytes_leaked, 0)
        self.assertFalse(r1.overall_ready_for_hardware_attach)

    def test_60_combined_verifier_fails_when_52a_fails(self) -> None:
        bad_52a = build_default_safe_focus_area_zoom_xlrh1_vault_spec(xlrh1_has_zoom_lever=True)
        r = verify_focus_area_zoom_lever_iso_minss_flash_and_vault(
            force_clean_room=True, spec_52a=bad_52a
        )
        self.assertFalse(r.all_passed)
        self.assertEqual(r.status, P296_STATUS_FAIL_PILLAR52_SUITE)

    def test_61_combined_verifier_fails_when_52b_fails(self) -> None:
        bad_52b = build_default_safe_iso_minss_flash_videolight_vault_spec(mishoe_5v_draw_ma=1200)
        r = verify_focus_area_zoom_lever_iso_minss_flash_and_vault(
            force_clean_room=True, spec_52b=bad_52b
        )
        self.assertFalse(r.all_passed)
        self.assertEqual(r.status, P296_STATUS_FAIL_PILLAR52_SUITE)

    def test_62_standalone_suite_passes_default_and_clean_room(self) -> None:
        st_def = run_pillar52_standalone_suite()
        self.assertTrue(st_def.all_passed, st_def.errors)
        self.assertEqual(st_def.pillar_52a_focus_area_zoom_xlrh1_vault.scenarios_passed, 6)
        self.assertEqual(st_def.pillar_52b_iso_minss_flash_videolight_vault.scenarios_passed, 6)
        self.assertEqual(st_def.raw_firmware_bytes_leaked, 0)

        st_cr = run_pillar52_standalone_suite(force_clean_room=True)
        self.assertTrue(st_cr.all_passed)
        self.assertEqual(st_cr.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_63_standalone_suite_propagates_52a_and_52b_failures(self) -> None:
        bad_a = replace(run_pillar52a_focus_area_zoom_xlrh1_6_scenario_suite(), passed=False)
        with mock.patch.object(
            p296, "run_pillar52a_focus_area_zoom_xlrh1_6_scenario_suite", return_value=bad_a
        ):
            st = run_pillar52_standalone_suite(force_clean_room=True)
            self.assertFalse(st.all_passed)
            self.assertEqual(st.status, P296_STATUS_FAIL_PILLAR52_SUITE)
            self.assertEqual(st.slot1_focus_zoom_camset_mutation_bytes, 4096)

        bad_b = replace(run_pillar52b_iso_minss_flash_videolight_6_scenario_suite(), passed=False)
        with mock.patch.object(
            p296,
            "run_pillar52b_iso_minss_flash_videolight_6_scenario_suite",
            return_value=bad_b,
        ):
            st2 = run_pillar52_standalone_suite(force_clean_room=True)
            self.assertFalse(st2.all_passed)
            self.assertEqual(st2.slot1_flash_videolight_imagedb_bytes, 4096)

    def test_64_standalone_suite_json_serializable(self) -> None:
        st = run_pillar52_standalone_suite(force_clean_room=True)
        payload = json.dumps(st.to_dict(), sort_keys=True, allow_nan=False)
        parsed = json.loads(payload)
        self.assertEqual(parsed["status"], P296_STATUS_VERIFIED_PILLAR52_SUITE)
        self.assertEqual(parsed["raw_firmware_bytes_leaked"], 0)

    # ------------------------------------------------------------------
    # 6. Unified 52-Pillar Recovery Master Aggregator (65..74)
    # ------------------------------------------------------------------

    def test_65_master_52of52_passes_in_default_mode_under_budget(self) -> None:
        m52 = evaluate_realhw_52pillar_recovery_master()
        self.assertTrue(m52.all_passed, m52.errors)
        self.assertEqual(m52.status, P296_STATUS_VERIFIED_52OF52_AGGREGATOR)
        self.assertGreaterEqual(m52.pillar_count, 52)
        self.assertGreaterEqual(m52.pillars_passed, 52)
        self.assertEqual(m52.failed_pillars, ())
        budget = 15.0 if _is_ci() else P296_FAST_CLI_BUDGET_SECONDS * 2.5
        self.assertLess(m52.elapsed_seconds, budget)
        self.assertEqual(m52.raw_firmware_bytes_leaked, 0)
        self.assertFalse(m52.persistent_emmc_writes_authorized)
        self.assertFalse(m52.overall_ready_for_hardware_attach)
        self.assertFalse(m52.hardware_live_attachment_authorized)

    def test_66_master_52of52_passes_in_clean_room_and_env_forced_modes(self) -> None:
        m_cr = evaluate_realhw_52pillar_recovery_master(force_clean_room=True)
        self.assertTrue(m_cr.all_passed)
        self.assertEqual(m_cr.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertGreaterEqual(m_cr.pillars_passed, 52)

        with mock.patch.dict(os.environ, {P296_ENV_CLEAN_ROOM_TEST: "1"}):
            m_env = evaluate_52pillar_recovery_master()
            self.assertTrue(m_env.all_passed)
            self.assertEqual(m_env.verification_mode, "CLEAN_ROOM_SYNTHETIC")

        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}):
            m_env2 = verify_52pillar_recovery_suite()
            self.assertTrue(m_env2.all_passed)
            self.assertEqual(m_env2.verification_mode, "CLEAN_ROOM_SYNTHETIC")

    def test_67_master_52of52_preserves_51_plus_1_lineage_and_rollup_fields(self) -> None:
        m51 = evaluate_realhw_51pillar_recovery_master(force_clean_room=True)
        m52 = evaluate_realhw_52pillar_recovery_master(force_clean_room=True)
        self.assertEqual(m52.pillar_count, m51.pillar_count + 1)
        self.assertEqual(m52.pillars[-1].pillar_number, 52)
        self.assertEqual(
            m52.pillars[-1].pillar_id,
            "pillar_52_focus_area_zoom_lever_iso_minss_flash_vault",
        )
        self.assertFalse(m52.xlrh1_has_zoom_lever)
        self.assertFalse(m52.xlrh1_has_rec_button)
        self.assertFalse(m52.xlrh1_has_zoom_hold_switch)
        self.assertTrue(m52.fx6_0_99_is_zoom_position_display)
        self.assertFalse(m52.fx6_has_iso_auto_min_ss)
        self.assertFalse(m52.fx6_mechanical_shutter_present)
        self.assertFalse(m52.fx3_ui_exposes_lossless_raw)
        self.assertFalse(m52.fx3_ui_exposes_shutter_type_auto)
        self.assertFalse(m52.fx6_still_pipeline_present)

    def test_68_master_52of52_fault_injection_pillar52(self) -> None:
        m52 = evaluate_realhw_52pillar_recovery_master(
            force_clean_room=True,
            fault_inject_pillar="pillar_52_focus_area_zoom_lever_iso_minss_flash_vault",
        )
        self.assertFalse(m52.all_passed)
        self.assertEqual(m52.status, P296_STATUS_FAIL_52OF52_AGGREGATOR)
        self.assertEqual(m52.pillars_passed, 51)
        self.assertEqual(
            m52.failed_pillars,
            ("pillar_52_focus_area_zoom_lever_iso_minss_flash_vault",),
        )

    def test_69_master_52of52_fault_injection_unknown_pillar_raises(self) -> None:
        with self.assertRaises(ValueError):
            evaluate_realhw_52pillar_recovery_master(
                force_clean_room=True,
                fault_inject_pillar="nonexistent_pillar",
            )

    def test_70_master_52of52_rejects_m51_or_p52_safety_drift(self) -> None:
        m51_bad = replace(
            evaluate_realhw_51pillar_recovery_master(force_clean_room=True),
            raw_firmware_bytes_leaked=32,
        )
        with mock.patch.object(p296, "evaluate_realhw_51pillar_recovery_master", return_value=m51_bad):
            m52 = evaluate_realhw_52pillar_recovery_master(force_clean_room=True)
            self.assertFalse(m52.all_passed)
            self.assertTrue(any("raw_firmware_bytes_leaked" in e for e in m52.errors))

    def test_71_master_52of52_rejects_p52_slot1_vault_drift(self) -> None:
        p52_bad = replace(
            run_pillar52_standalone_suite(force_clean_room=True),
            slot1_vault_mutation_bytes=4096,
        )
        with mock.patch.object(p296, "run_pillar52_standalone_suite", return_value=p52_bad):
            m52 = evaluate_realhw_52pillar_recovery_master(force_clean_room=True)
            self.assertFalse(m52.all_passed)
            self.assertTrue(any("slot1_vault_mutation_bytes" in e for e in m52.errors))

    def test_72_master_52of52_digest_deterministic_in_clean_room(self) -> None:
        r1 = evaluate_realhw_52pillar_recovery_master(force_clean_room=True)
        r2 = evaluate_realhw_52pillar_recovery_master(force_clean_room=True)
        self.assertEqual(r1.master_52pillar_sha256, r2.master_52pillar_sha256)

    def test_73_master_52of52_to_dict_json_roundtrip(self) -> None:
        m52 = evaluate_realhw_52pillar_recovery_master(force_clean_room=True)
        payload = json.dumps(m52.to_dict(), sort_keys=True, allow_nan=False)
        parsed = json.loads(payload)
        self.assertGreaterEqual(parsed["pillar_count"], 52)
        self.assertGreaterEqual(parsed["pillars_passed"], 52)
        self.assertEqual(parsed["status"], P296_STATUS_VERIFIED_52OF52_AGGREGATOR)

    def test_74_backward_compatibility_51pillar_master_still_passes(self) -> None:
        m51 = evaluate_realhw_51pillar_recovery_master(force_clean_room=True)
        self.assertTrue(m51.all_passed)
        self.assertGreaterEqual(m51.pillar_count, 51)
        self.assertGreaterEqual(m51.pillars_passed, 51)

    # ------------------------------------------------------------------
    # 7. CLI Subcommands, --out Output & Subprocess Portability (75..80)
    # ------------------------------------------------------------------

    def test_75_cli_pillar52_json_and_out_in_repo_work_tests(self) -> None:
        work_tests = _repo_root() / "work" / "_tests"
        work_tests.mkdir(parents=True, exist_ok=True)
        out_dir = Path(tempfile.mkdtemp(prefix="p296_p52_", dir=str(work_tests)))
        shutil.rmtree(out_dir)
        try:
            buf = io.StringIO()
            with mock.patch.object(
                sys,
                "argv",
                [
                    "fx3_recovery",
                    "verify-pillar52-focus-area-zoom-iso-flash-vault",
                    "--clean-room",
                    "--json",
                    "--out",
                    str(out_dir),
                ],
            ):
                with redirect_stdout(buf):
                    rc = cli_main.main()
            self.assertEqual(rc, 0)
            payload = json.loads(buf.getvalue())
            self.assertTrue(payload["all_passed"])
            self.assertEqual(payload["status"], P296_STATUS_VERIFIED_PILLAR52_SUITE)
            report_file = out_dir / "pillar52-focus-area-zoom-iso-flash-vault-report.json"
            self.assertTrue(report_file.is_file())
        finally:
            shutil.rmtree(out_dir, ignore_errors=True)

    def test_76_cli_52pillar_recovery_json_and_out_in_repo_work_tests(self) -> None:
        work_tests = _repo_root() / "work" / "_tests"
        work_tests.mkdir(parents=True, exist_ok=True)
        out_dir = Path(tempfile.mkdtemp(prefix="p296_m52_", dir=str(work_tests)))
        shutil.rmtree(out_dir)
        try:
            buf = io.StringIO()
            with mock.patch.object(
                sys,
                "argv",
                [
                    "fx3_recovery",
                    "verify-52pillar-recovery",
                    "--clean-room",
                    "--json",
                    "--out",
                    str(out_dir),
                ],
            ):
                with redirect_stdout(buf):
                    rc = cli_main.main()
            self.assertEqual(rc, 0)
            payload = json.loads(buf.getvalue())
            self.assertTrue(payload["all_passed"])
            self.assertGreaterEqual(payload["pillars_passed"], 52)
            self.assertEqual(payload["status"], P296_STATUS_VERIFIED_52OF52_AGGREGATOR)
            report_file = out_dir / "52pillar-recovery-master-report.json"
            self.assertTrue(report_file.is_file())
        finally:
            shutil.rmtree(out_dir, ignore_errors=True)

    def test_77_cli_human_readable_output_and_subprocess_sys_executable(self) -> None:
        b1 = io.StringIO()
        with mock.patch.object(
            sys,
            "argv",
            ["fx3_recovery", "verify-pillar52-focus-area-zoom-iso-flash-vault", "--clean-room"],
        ):
            with redirect_stdout(b1):
                rc1 = cli_main.main()
        self.assertEqual(rc1, 0)
        self.assertIn("pillar_52a=6/6", b1.getvalue())
        self.assertIn("pillar_52b=6/6", b1.getvalue())

        b2 = io.StringIO()
        with mock.patch.object(
            sys,
            "argv",
            ["fx3_recovery", "verify-52pillar-recovery", "--clean-room"],
        ):
            with redirect_stdout(b2):
                rc2 = cli_main.main()
        self.assertEqual(rc2, 0)
        t2 = b2.getvalue()
        self.assertIn("pillars=", t2)
        self.assertIn("all_passed=True", t2)
        self.assertIn("raw_firmware_bytes_leaked=0", t2)

        adapter_dir = _repo_root() / "outputs" / "fx3-recovery-adapter"
        env_base = dict(os.environ)
        env_base["PYTHONDONTWRITEBYTECODE"] = "1"
        env_base["PYTHONPATH"] = str(adapter_dir)
        for subcmd in (
            "verify-pillar52-focus-area-zoom-iso-flash-vault --clean-room --json",
            "verify-52pillar-recovery --clean-room --json",
        ):
            proc = subprocess.run(
                [sys.executable, "-B", "-m", "fx3_recovery", *subcmd.split()],
                cwd=str(_repo_root()),
                env=env_base,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            parsed = json.loads(proc.stdout)
            self.assertTrue(parsed["all_passed"])

    def test_78_cli_help_portability_for_phase296_subcommands(self) -> None:
        adapter_dir = _repo_root() / "outputs" / "fx3-recovery-adapter"
        env_base = dict(os.environ)
        env_base["PYTHONDONTWRITEBYTECODE"] = "1"
        env_base["PYTHONPATH"] = str(adapter_dir)
        for subcmd in (
            "--help",
            "verify-pillar52-focus-area-zoom-iso-flash-vault --help",
            "verify-52pillar-recovery --help",
        ):
            proc = subprocess.run(
                [sys.executable, "-B", "-m", "fx3_recovery", *subcmd.split()],
                cwd=str(_repo_root()),
                env=env_base,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_79_cli_returns_nonzero_on_pillar52_and_master_failures(self) -> None:
        failed_st = replace(
            run_pillar52_standalone_suite(force_clean_room=True),
            all_passed=False,
            status=P296_STATUS_FAIL_PILLAR52_SUITE,
        )
        with mock.patch.object(cli_main, "run_pillar52_standalone_suite", return_value=failed_st):
            buf = io.StringIO()
            with mock.patch.object(
                sys,
                "argv",
                [
                    "fx3_recovery",
                    "verify-pillar52-focus-area-zoom-iso-flash-vault",
                    "--clean-room",
                    "--json",
                ],
            ):
                with redirect_stdout(buf):
                    rc = cli_main.main()
            self.assertEqual(rc, 2)

        failed_m = replace(
            evaluate_realhw_52pillar_recovery_master(force_clean_room=True),
            all_passed=False,
            status=P296_STATUS_FAIL_52OF52_AGGREGATOR,
        )
        with mock.patch.object(cli_main, "verify_52pillar_recovery_suite", return_value=failed_m):
            buf = io.StringIO()
            with mock.patch.object(
                sys,
                "argv",
                ["fx3_recovery", "verify-52pillar-recovery", "--clean-room", "--json"],
            ):
                with redirect_stdout(buf):
                    rc = cli_main.main()
            self.assertEqual(rc, 2)

    def test_80_no_raw_firmware_bytes_or_usb_tx_anywhere_in_module(self) -> None:
        snap = inspect_phase296_donors_readonly()
        st = run_pillar52_standalone_suite(force_clean_room=True)
        m52 = evaluate_realhw_52pillar_recovery_master(force_clean_room=True)
        self.assertEqual(snap.raw_firmware_bytes_leaked, 0)
        self.assertEqual(st.raw_firmware_bytes_leaked, 0)
        self.assertEqual(m52.raw_firmware_bytes_leaked, 0)
        self.assertEqual(st.passive_tx_bytes_emitted, 0)
        self.assertEqual(m52.passive_tx_bytes_emitted, 0)
        self.assertFalse(m52.overall_ready_for_hardware_attach)
        self.assertFalse(m52.persistent_emmc_writes_authorized)


if __name__ == "__main__":
    unittest.main()
