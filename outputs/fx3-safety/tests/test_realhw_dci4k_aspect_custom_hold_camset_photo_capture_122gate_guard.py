"""Phase 288 (Wave-51) Dual-Mode Unit Tests (80 tests) for
`fx3_safety.realhw_dci4k_aspect_custom_hold_camset_photo_capture_and_122gate_guard`:

- Gate `G121` (`GATE_G121_DCI4K_UHD_LONGGOP_HDMI_RAW_AND_STILL_ASPECT_RATIO_GUARD`):
  - `[XAVC S-I DCI 4K]` (`_f.uxc` `0x7336`/`0x61ce`, `4096x2160` `17:9` All-Intra `4:2:2 10bit`)
    at `23.98p`/`24.00p`/`25p`/`29.97p`/`50p`/`59.94p` (`240M..600M`, `CFexpress VPG200+` or
    `SDXC V90+` at `600M`), S&Q strictly `1..48 fps` (NO `100fps`/`120fps`), and mandatory
    reboot + playback quarantine on `24.00p` (`0x75ce`, `_g.uxc` `0x639b`/`0x63b6`,
    `STATUS_BLOCKED_G121_DCI4K_HFR_OR_UNREBOOTED_24P_VIOLATION`).
  - Long-GOP codecs (`XAVC HS 4K` `0x76df`, `XAVC S 4K` `0x690c`) and `XAVC S-I 4K` (`0x70ba`)
    strictly `3840x2160` (`16:9` UHD) with NO `4096x2160` and NO `24.00p`
    (`STATUS_BLOCKED_G121_LONGGOP_DCI4K_OR_24P_SPOOF_VIOLATION`).
  - Type-A HDMI RAW (`0x6e97`, `4264x2408`, `23.98p..59.94p` incl. `24.00p`) requiring
    `[Log Shooting] != Off`, plus Still `[Aspect Ratio]` (`0x757c`/`.uxc` `0xe680`: `3:2` `12M`
    default, `4:3` `11M`, `16:9` `10M`, `1:1` `8.0M`; `.ARW` full `3:2` pixels; `APS-C S35 = On`
    `L -> M` step-down; vs Still-less `FX6`), across `384` matrix states.
- Gate `G122` (`GATE_G122_RECALL_CUSTOM_HOLD_CAMSET_CARD_PATH_PHOTO_CAPTURE_AND_ENLARGE_GUARD`):
  - `[Reg. Custom Shoot Set]` (`0x7631`, `Recall Custom hold 1..3`, `11` `is_checked_recall_custom_hold0..10`
    checkboxes): Still `P/A/S/M` only, `[HLG Still Image] = Off` on ISO / DRO Bracket, survives
    `[Camera Settings Reset]` (`STATUS_BLOCKED_G122_RECALL_CUSTOM_HOLD_MODE_OR_HLG_VIOLATION`).
  - Empirical card path boundary: `ILME-FX3` `%c:%s/SONY/SETTING/%s/CAMPR%02d%c.DAT` (`M1..M4`) &
    `%c:%s/SONY/SETTING/%s/CAMSET/%s.DAT` (`CAMSET`) rejecting `FX6` `PRIVATE/SONY/PRO/CAMERA` spoofs
    and enforcing `[Format]` wipe protection on `Slot 1` (`STATUS_BLOCKED_G122_FX3_CAMSET_CARD_PATH_SPOOF_VIOLATION`).
  - Playback `[Photo Capture]` (`0x6856`, `JPEG` / `HEIF 4:2:0` / `HEIF 4:2:2`, `8.3M` / `2.1M`):
    hard-blocked on `XAVC S-I DCI 4K` (`_g 0x60ce`) AND hard-blocked on `Slot 1` recovery vault
    (`STATUS_BLOCKED_G122_PHOTO_CAPTURE_DCI4K_OR_SLOT1_WRITE_VIOLATION`), plus Still-only
    `[Enlarge Image]` (`.uxc` `0xe8cb`) & exact `ilc/2210` `[Enlarge Initial Mag.]` (`0x6b6e`) /
    `[Enlarge Initial Position]` (`0x781f`) surviving `[Camera Settings Reset]`, across `384` matrix states.
- Unified `122`-Gate Master Safety Preflight (`evaluate_122gate_preflight` / `verify-122-gates`):
  - `119/122` offline (`VERIFIED_119_OF_122_AWAITING_PHYSICAL_TIER0`) and `122/122` in
    `--simulate-bench-dry-run` (`VERIFIED_ALL_122_GATES_DRY_RUN_SIMULATED_BACKUP`) with all hardware
    write/live-attach redlines hard-locked `False`.
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
from fx3_safety.realhw_focus_area_zoom_lever_iso_minss_flash_and_120gate_guard import (
    Master120GateReport,
    evaluate_120gate_preflight,
)
from fx3_safety.realhw_dci4k_aspect_custom_hold_camset_photo_capture_and_122gate_guard import (
    ALLOWED_4K_FILE_FORMATS_G121,
    ALLOWED_CARD_TIERS_G121,
    ALLOWED_ENLARGE_INITIAL_MAG_G122,
    ALLOWED_ENLARGE_INITIAL_POS_G122,
    ALLOWED_LOG_SHOOTING_MODES_G121,
    ALLOWED_MEMORY_RECALL_MEDIA_SLOTS_G122,
    ALLOWED_PHOTO_CAPTURE_FILE_TYPES_G122,
    ALLOWED_RESET_ACTIONS_PHASE288,
    ALLOWED_SHOOT_MODES_PHASE288,
    ALLOWED_STILL_ASPECT_RATIOS_G121,
    ALLOWED_STILL_IMAGE_SIZES_G121,
    ASPECT_3_2_UXC_RESID16_G121,
    ASPECT_RATIO_1_1_G121,
    ASPECT_RATIO_16_9_G121,
    ASPECT_RATIO_3_2_G121,
    ASPECT_RATIO_4_3_G121,
    ASPECT_RATIO_F_UXC_RESID16_G121,
    ASPECT_RATIO_MENU_PATH_G121,
    ASPECT_RATIO_UXC_RESID16_G121,
    CAMERA_MEMORY_BODY_BANKS_G122,
    CAMERA_MEMORY_CARD_BANKS_G122,
    CAMERA_SET_MEMORY_MENU_PATH_G122,
    CAMERA_SET_MEMORY_UXC_RESID16_G122,
    CARD_TIER_CFEXPRESS_VPG200_G121,
    CARD_TIER_SDXC_V30_G121,
    CARD_TIER_SDXC_V60_G121,
    CARD_TIER_SDXC_V90_G121,
    CustomHoldCamsetPhotoEnlargeGuardResult,
    DCI4K_600M_ALLOWED_CARD_TIERS_G121,
    DCI_4K_ALLOWED_REC_RATES_G121,
    DCI_4K_ALLOWED_SQ_FPS_G121,
    DCI_4K_ASPECT_LABEL_G121,
    DCI_4K_BITRATES_MBPS_G121,
    DCI_4K_DIMENSIONS_G121,
    DCI_4K_FORBIDDEN_HFR_FPS_G121,
    DEFAULT_REPO_ROOT,
    DONOR_CHECK_CI_MAX_SECONDS_PHASE288,
    DONOR_CHECK_MAX_SECONDS_PHASE288,
    Dci4kUhdLongGopHdmiRawAspectGuardResult,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    ENLARGE_IMAGE_MENU_PATH_G122,
    ENLARGE_IMAGE_UXC_RESID16_G122,
    ENLARGE_INITIAL_MAG_DEFAULT_G122,
    ENLARGE_INITIAL_MAG_PREVIOUS_G122,
    ENLARGE_INITIAL_MAG_STANDARD_G122,
    ENLARGE_INITIAL_MAG_UXC_RESID16_G122,
    ENLARGE_INITIAL_POS_CENTER_G122,
    ENLARGE_INITIAL_POS_DEFAULT_G122,
    ENLARGE_INITIAL_POS_FOCUSED_G122,
    ENLARGE_INITIAL_POSITION_UXC_RESID16_G122,
    ENV_CLEAN_ROOM_TEST_PHASE288,
    FILE_FORMAT_FACTORY_DEFAULT_G121,
    FILE_FORMAT_MENU_PATH_G121,
    FILE_FORMAT_XAVC_HS_4K_G121,
    FILE_FORMAT_XAVC_S_4K_G121,
    FILE_FORMAT_XAVC_SI_4K_G121,
    FILE_FORMAT_XAVC_SI_DCI_4K_G121,
    FRAME_RATE_24_00P_UXC_RESID16_G121,
    FX3_ALLOWED_CARD_PATH_PREFIXES_G122,
    FX3_CAMPR_PATH_TEMPLATE_G122,
    FX3_CAMSET_PATH_TEMPLATE_G122,
    FX3_DEFAULT_FW_VERSION_PHASE288,
    FX3_EXACT_11_CUSTOM_HOLD_BOOL_SYMBOLS_G122,
    FX3_EXACT_11_CUSTOM_HOLD_CHECKBOX_KEYS_G122,
    FX3_HELP_GUIDE_CODE_PHASE288,
    FX3_MODEL_ID_PHASE288,
    FX3_MODEL_NAME_PHASE288,
    FX3_RAW_FULL_SENSOR_DIMENSIONS_G121,
    FX6_DEFAULT_FW_VERSION_PHASE288,
    FX6_FORBIDDEN_CARD_PATH_MARKERS_G122,
    FX6_MODEL_NAME_PHASE288,
    G121,
    G121_GATE_CODE,
    G121_GATE_ID,
    G121Dci4kAspectRatioGuardResult,
    G122,
    G122_GATE_CODE,
    G122_GATE_ID,
    G122CustomHoldCamsetPhotoEnlargeGuardResult,
    GATE_G121_DCI4K_UHD_LONGGOP_HDMI_RAW_AND_STILL_ASPECT_RATIO_GUARD,
    GATE_G122_RECALL_CUSTOM_HOLD_CAMSET_CARD_PATH_PHOTO_CAPTURE_AND_ENLARGE_GUARD,
    HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    HDMI_RAW_ALLOWED_RATES_G121,
    HDMI_RAW_ASPECT_LABEL_G121,
    HDMI_RAW_DIMENSIONS_G121,
    HDMI_RAW_OUTPUT_UXC_RESID16_G121,
    HLG_LOCKOUT_RECALL_PARAMS_G122,
    HUMAN_HARDWARE_ATTACH_TOKEN,
    JPEG_HEIF_SWITCH_UXC_RESID16_G122,
    LOG_SHOOTING_CINE_EI_G121,
    LOG_SHOOTING_CINE_EI_QUICK_G121,
    LOG_SHOOTING_FLEXIBLE_ISO_G121,
    LOG_SHOOTING_OFF_G121,
    LONGGOP_4K_FILE_FORMATS_G121,
    MEMORY_RECALL_MEDIA_UXC_RESID16_G122,
    MOVIE_SETTINGS_MENU_PATH_G121,
    MOVIE_SHOOT_MODES_PHASE288,
    Master122GateReport,
    PASM_SHOOT_MODES_PHASE288,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHOTO_CAPTURE_4K_DIMENSIONS_G122,
    PHOTO_CAPTURE_4K_MP_LABEL_G122,
    PHOTO_CAPTURE_DCI4K_LOCKOUT_G_UXC_RESID16_G122,
    PHOTO_CAPTURE_FILE_TYPE_DEFAULT_G122,
    PHOTO_CAPTURE_HD_DIMENSIONS_G122,
    PHOTO_CAPTURE_HD_MP_LABEL_G122,
    PHOTO_CAPTURE_MENU_PATH_G122,
    PHOTO_CAPTURE_TYPE_HEIF_420_G122,
    PHOTO_CAPTURE_TYPE_HEIF_422_G122,
    PHOTO_CAPTURE_TYPE_JPEG_G122,
    PHOTO_CAPTURE_UXC_RESID16_G122,
    PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED,
    PHYSICAL_USB_PACKETS_EMITTED,
    PINNED_FX3_APPFW_SLICES_PHASE288,
    PINNED_FX3_APPFW_SLICES_SHA256_PHASE288,
    PINNED_FX6_APPFW_SLICES_PHASE288,
    PINNED_FX6_APPFW_SLICES_SHA256_PHASE288,
    PINNED_PHASE288_DONOR_SPECS,
    PLAYBACK_24P_QUARANTINE_G_UXC_RESID16_G121,
    Phase288DonorAuditResult,
    RAW_FIRMWARE_BYTES_LEAKED,
    RAW_OUTPUT_MENU_PATH_G121,
    REALHW_DCI4K_ASPECT_CUSTOM_HOLD_CAMSET_PHOTO_CAPTURE_122GATE_SCHEMA,
    REALHW_DCI4K_ASPECT_CUSTOM_HOLD_CAMSET_PHOTO_CAPTURE_122GATE_VERSION,
    REBOOT_24P_G_UXC_RESID16_G121,
    RECALL_CUSTOM_HOLD_1_UXC_RESID16_G122,
    RECALL_CUSTOM_HOLD_2_UXC_RESID16_G122,
    RECALL_CUSTOM_HOLD_3_UXC_RESID16_G122,
    RECALL_CUSTOM_HOLD_SLOTS_G122,
    REG_CUSTOM_SHOOT_SET_MENU_PATH_G122,
    REG_CUSTOM_SHOOT_SET_UXC_RESID16_G122,
    RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE288,
    RESET_ACTION_INITIALIZE_PHASE288,
    RESET_ACTION_NONE_PHASE288,
    RESET_ACTION_RESET_NETWORK_SET_PHASE288,
    SAVE_LOAD_SETTINGS_MENU_PATH_G122,
    SHOOT_MODE_A_PHASE288,
    SHOOT_MODE_INTELLIGENT_AUTO_PHASE288,
    SHOOT_MODE_MOVIE_PHASE288,
    SHOOT_MODE_MR_PHASE288,
    SHOOT_MODE_M_PHASE288,
    SHOOT_MODE_P_PHASE288,
    SHOOT_MODE_SQ_PHASE288,
    SHOOT_MODE_STILL_PASM_PHASE288,
    SHOOT_MODE_S_PHASE288,
    SHUTTER_MODE_UXC_RESID16_G121,
    SPI_NOR_WRITE_AUTHORIZED,
    STATUS_BLOCKED_G121_DCI4K_HFR_OR_UNREBOOTED_24P_VIOLATION,
    STATUS_BLOCKED_G121_HDMI_RAW_LOG_OR_STILL_ASPECT_SPOOF_VIOLATION,
    STATUS_BLOCKED_G121_LONGGOP_DCI4K_OR_24P_SPOOF_VIOLATION,
    STATUS_BLOCKED_G121_TELEMETRY_INVALID,
    STATUS_BLOCKED_G122_ENLARGE_IMAGE_OR_RESET_PERSISTENCE_VIOLATION,
    STATUS_BLOCKED_G122_FX3_CAMSET_CARD_PATH_SPOOF_VIOLATION,
    STATUS_BLOCKED_G122_PHOTO_CAPTURE_DCI4K_OR_SLOT1_WRITE_VIOLATION,
    STATUS_BLOCKED_G122_RECALL_CUSTOM_HOLD_MODE_OR_HLG_VIOLATION,
    STATUS_BLOCKED_G122_TELEMETRY_INVALID,
    STATUS_BLOCKED_PHASE288_DONOR_INTEGRITY,
    STATUS_VERIFIED_G121,
    STATUS_VERIFIED_G122,
    STILL_ASPECT_RATIO_DEFAULT_G121,
    STILL_ASPECT_RESOLUTION_TABLE_G121,
    STILL_IMAGE_SIZE_L_G121,
    STILL_IMAGE_SIZE_M_G121,
    STILL_IMAGE_SIZE_S_G121,
    STILL_SHOOT_MODES_PHASE288,
    UHD_4K_ALLOWED_REC_RATES_G121,
    UHD_4K_ASPECT_LABEL_G121,
    UHD_4K_DIMENSIONS_G121,
    UHD_4K_MAX_SQ_FPS_G121,
    UHD_ONLY_4K_FILE_FORMATS_G121,
    USB_PACKETS_TRANSMITTED,
    XAVC_HS_4K_UXC_RESID16_G121,
    XAVC_S_4K_UXC_RESID16_G121,
    XAVC_SI_4K_UXC_RESID16_G121,
    XAVC_SI_DCI_4K_ALT_UXC_RESID16_G121,
    XAVC_SI_DCI_4K_UXC_RESID16_G121,
    _is_forced_clean_room,
    audit_phase288_donor_contracts,
    compute_custom_hold_camset_photo_and_enlarge_matrix,
    compute_dci4k_hdmi_raw_and_aspect_ratio_matrix,
    evaluate_122_master_safety_gates,
    evaluate_122gate_preflight,
    evaluate_g121_dci4k_and_aspect_ratio_guard,
    evaluate_g122_custom_hold_camset_photo_capture_guard,
    main as module_main,
    resolve_fx3_custom_hold_camset_photo_and_enlarge_state,
    resolve_fx3_dci4k_hdmi_raw_and_aspect_ratio_state,
    run_122_gate_preflight,
    verify_custom_hold_camset_photo_capture_guard,
    verify_dci4k_and_aspect_ratio_guard,
)


def _subprocess_timeout_seconds() -> float:
    return 15.0 if os.environ.get("GITHUB_ACTIONS", "").strip().lower() == "true" else 10.0


def _build_synthetic_120_report(*, dry_run: bool) -> Master120GateReport:
    return evaluate_120gate_preflight(
        DEFAULT_REPO_ROOT,
        force_clean_room=True,
        dry_run_simulated=dry_run,
    )


class TestPhase288Dci4kAspectCustomHoldCamsetPhotoCapture122GateGuard(
    unittest.TestCase
):
    clean_offline_120: Master120GateReport
    clean_dryrun_120: Master120GateReport

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.clean_offline_120 = _build_synthetic_120_report(dry_run=False)
        cls.clean_dryrun_120 = _build_synthetic_120_report(dry_run=True)

    # --- 1. Package Exports, Hard Redlines & Dual-Mode Donor Audit (Tests 01-10) ---

    def test_01_package_exports_and_all_integrity(self) -> None:
        self.assertTrue(
            hasattr(
                fx3_safety,
                "realhw_dci4k_aspect_custom_hold_camset_photo_capture_and_122gate_guard",
            )
        )
        for name in (
            "evaluate_122gate_preflight",
            "evaluate_122_master_safety_gates",
            "run_122_gate_preflight",
            "evaluate_g121_dci4k_and_aspect_ratio_guard",
            "evaluate_g122_custom_hold_camset_photo_capture_guard",
            "Master122GateReport",
            "G121",
            "G122",
        ):
            self.assertIn(name, fx3_safety.__all__)
            self.assertTrue(hasattr(fx3_safety, name))
        self.assertIs(evaluate_122_master_safety_gates, evaluate_122gate_preflight)
        self.assertIs(run_122_gate_preflight, evaluate_122gate_preflight)

    def test_02_schema_version_and_redline_constants_locked(self) -> None:
        self.assertEqual(
            REALHW_DCI4K_ASPECT_CUSTOM_HOLD_CAMSET_PHOTO_CAPTURE_122GATE_SCHEMA,
            "realhw_dci4k_aspect_custom_hold_camset_photo_capture_and_122gate_guard_v1",
        )
        self.assertEqual(
            REALHW_DCI4K_ASPECT_CUSTOM_HOLD_CAMSET_PHOTO_CAPTURE_122GATE_VERSION,
            "1.0.0",
        )
        self.assertFalse(HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        self.assertFalse(HUMAN_HARDWARE_ATTACH_TOKEN)
        self.assertFalse(EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        self.assertFalse(SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(PERSISTENT_WRITE_RELEASE)
        self.assertFalse(PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED)
        self.assertEqual(USB_PACKETS_TRANSMITTED, 0)
        self.assertEqual(PHYSICAL_USB_PACKETS_EMITTED, 0)
        self.assertEqual(RAW_FIRMWARE_BYTES_LEAKED, 0)

    def test_03_pinned_donor_specs_and_slices_exact(self) -> None:
        self.assertEqual(len(PINNED_PHASE288_DONOR_SPECS), 11)
        self.assertEqual(len(PINNED_FX3_APPFW_SLICES_PHASE288), 17)
        self.assertEqual(len(PINNED_FX6_APPFW_SLICES_PHASE288), 9)
        self.assertEqual(len(PINNED_FX3_APPFW_SLICES_SHA256_PHASE288), 64)
        self.assertEqual(len(PINNED_FX6_APPFW_SLICES_SHA256_PHASE288), 64)
        self.assertLessEqual(DONOR_CHECK_MAX_SECONDS_PHASE288, 0.20)
        self.assertEqual(DONOR_CHECK_CI_MAX_SECONDS_PHASE288, 1.00)

    def test_04_donor_audit_fast_o_rdonly_and_clean_room_fallback(self) -> None:
        res = audit_phase288_donor_contracts()
        self.assertTrue(res.valid, msg=res.errors)
        self.assertIn(
            res.verification_mode, ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC")
        )
        self.assertEqual(res.raw_firmware_bytes_leaked, 0)
        self.assertTrue(res.fx3_contracts_verified)
        self.assertTrue(res.fx6_contracts_verified)
        self.assertTrue(res.four_lang_resid16_parity_verified)
        budget = (
            DONOR_CHECK_CI_MAX_SECONDS_PHASE288
            if os.environ.get("GITHUB_ACTIONS", "").strip().lower() == "true"
            else DONOR_CHECK_MAX_SECONDS_PHASE288
        )
        self.assertLessEqual(res.elapsed_seconds, budget)

    def test_05_forced_clean_room_mode_returns_synthetic_zero_files(self) -> None:
        res = audit_phase288_donor_contracts(force_clean_room=True)
        self.assertIsInstance(res, Phase288DonorAuditResult)
        self.assertTrue(res.valid)
        self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(res.files_inspected, 0)
        self.assertEqual(len(res.checked_markers), 11)
        self.assertEqual(res.missing_markers, ())

    def test_06_env_clean_room_flags_respected(self) -> None:
        for env_key in (ENV_CLEAN_ROOM_TEST_PHASE288, "FX3_FX6_FORCE_CLEAN_ROOM"):
            with mock.patch.dict(os.environ, {env_key: "1"}):
                self.assertTrue(_is_forced_clean_room())
                res = audit_phase288_donor_contracts()
                self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")
                self.assertTrue(res.valid)

    def test_07_explicit_missing_work_root_fails_closed(self) -> None:
        with mock.patch.dict(
            os.environ,
            {ENV_CLEAN_ROOM_TEST_PHASE288: "", "FX3_FX6_FORCE_CLEAN_ROOM": ""},
        ):
            with tempfile.TemporaryDirectory() as td:
                res = audit_phase288_donor_contracts(
                    work_root=Path(td),
                    force_clean_room=False,
                )
                self.assertFalse(res.valid)
                self.assertEqual(res.status, STATUS_BLOCKED_PHASE288_DONOR_INTEGRITY)
                self.assertFalse(res.fx3_contracts_verified)
                self.assertEqual(len(res.missing_markers), 11)

    def test_08_corrupted_donor_sha_mismatch_blocked(self) -> None:
        with mock.patch.dict(
            os.environ,
            {ENV_CLEAN_ROOM_TEST_PHASE288: "", "FX3_FX6_FORCE_CLEAN_ROOM": ""},
        ):
            with tempfile.TemporaryDirectory() as td:
                root = Path(td)
                fake_fx3 = root / "fx3_fake.uxc"
                fake_fx3.write_bytes(b"XAVC S-I DCI 4K 24.00p")
                fake_fx6 = root / "fx6_fake.uxc"
                fake_fx6.write_bytes(b"Custom Aspect Ratio")
                override = {
                    "fx3_string_english_f_uxc": (
                        "FX3",
                        "fx3_fake.uxc",
                        len(fake_fx3.read_bytes()),
                        "0" * 64,
                        (b"XAVC S-I DCI 4K",),
                        "FAKE_FX3_MARKER",
                    ),
                    "fx6_string_english_uxc": (
                        "FX6",
                        "fx6_fake.uxc",
                        len(fake_fx6.read_bytes()),
                        "0" * 64,
                        (b"Custom Aspect Ratio",),
                        "FAKE_FX6_MARKER",
                    ),
                }
                res = audit_phase288_donor_contracts(
                    work_root=root,
                    force_clean_room=False,
                    donor_specs_override=override,
                )
                self.assertFalse(res.valid)
                self.assertEqual(res.status, STATUS_BLOCKED_PHASE288_DONOR_INTEGRITY)
                self.assertFalse(res.fx3_contracts_verified)
                self.assertFalse(res.fx6_contracts_verified)

    def test_09_clean_room_fallback_when_default_work_root_missing(self) -> None:
        with mock.patch.dict(
            os.environ,
            {ENV_CLEAN_ROOM_TEST_PHASE288: "", "FX3_FX6_FORCE_CLEAN_ROOM": ""},
        ):
            with tempfile.TemporaryDirectory() as td:
                fake_paths = mock.MagicMock(work_root=Path(td))
                with mock.patch(
                    "fx3_safety.realhw_dci4k_aspect_custom_hold_camset_photo_capture_and_122gate_guard.resolve_donor_thermal_power_paths",
                    return_value=fake_paths,
                ):
                    res = audit_phase288_donor_contracts()
                    self.assertTrue(res.valid)
                    self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")
                    self.assertEqual(
                        res.access_mode,
                        "SYNTHETIC_CLEAN_ROOM_FALLBACK_NO_LOCAL_DONOR",
                    )

    def test_10_gate_identifiers_and_donor_audit_serializable(self) -> None:
        self.assertEqual(G121, G121_GATE_ID)
        self.assertEqual(G122, G122_GATE_ID)
        self.assertEqual(GATE_G121_DCI4K_UHD_LONGGOP_HDMI_RAW_AND_STILL_ASPECT_RATIO_GUARD, G121_GATE_CODE)
        self.assertEqual(
            GATE_G122_RECALL_CUSTOM_HOLD_CAMSET_CARD_PATH_PHOTO_CAPTURE_AND_ENLARGE_GUARD,
            G122_GATE_CODE,
        )
        res = audit_phase288_donor_contracts(force_clean_room=True)
        self.assertEqual(json.loads(json.dumps(res.to_dict()))["raw_firmware_bytes_leaked"], 0)

    # --- 2. Gate G121: XAVC S-I DCI 4K vs Long-GOP UHD, HDMI RAW, Still Aspect Ratio (Tests 11-35) ---

    def test_11_g121_uxc_resid16_and_dimension_constants(self) -> None:
        self.assertEqual(XAVC_SI_DCI_4K_UXC_RESID16_G121, 0x7336)
        self.assertEqual(XAVC_SI_DCI_4K_ALT_UXC_RESID16_G121, 0x61CE)
        self.assertEqual(XAVC_HS_4K_UXC_RESID16_G121, 0x76DF)
        self.assertEqual(XAVC_S_4K_UXC_RESID16_G121, 0x690C)
        self.assertEqual(XAVC_SI_4K_UXC_RESID16_G121, 0x70BA)
        self.assertEqual(FRAME_RATE_24_00P_UXC_RESID16_G121, 0x75CE)
        self.assertEqual(SHUTTER_MODE_UXC_RESID16_G121, 0x7C7C)
        self.assertEqual(HDMI_RAW_OUTPUT_UXC_RESID16_G121, 0x6E97)
        self.assertEqual(REBOOT_24P_G_UXC_RESID16_G121, 0x639B)
        self.assertEqual(PLAYBACK_24P_QUARANTINE_G_UXC_RESID16_G121, 0x63B6)
        self.assertEqual(ASPECT_RATIO_F_UXC_RESID16_G121, 0x757C)
        self.assertEqual(ASPECT_RATIO_UXC_RESID16_G121, 0xE680)
        self.assertEqual(ASPECT_3_2_UXC_RESID16_G121, 0xE4F8)
        self.assertEqual(DCI_4K_DIMENSIONS_G121, (4096, 2160))
        self.assertEqual(UHD_4K_DIMENSIONS_G121, (3840, 2160))
        self.assertEqual(HDMI_RAW_DIMENSIONS_G121, (4264, 2408))

    def test_12_g121_default_state_verified(self) -> None:
        res = verify_dci4k_and_aspect_ratio_guard()
        self.assertIsInstance(res, Dci4kUhdLongGopHdmiRawAspectGuardResult)
        self.assertTrue(res.valid, msg=res.errors)
        self.assertEqual(res.status, STATUS_VERIFIED_G121)
        self.assertEqual(res.effective_file_format, FILE_FORMAT_XAVC_SI_DCI_4K_G121)
        self.assertEqual(res.movie_dimensions, DCI_4K_DIMENSIONS_G121)
        self.assertEqual(res.movie_aspect_label, DCI_4K_ASPECT_LABEL_G121)
        self.assertTrue(res.is_dci_4k_all_intra)
        self.assertEqual(res.effective_still_aspect_ratio, STILL_ASPECT_RATIO_DEFAULT_G121)
        self.assertEqual(res.effective_still_image_size, STILL_IMAGE_SIZE_L_G121)
        self.assertEqual(res.still_aspect_megapixel_label, "12M")
        self.assertTrue(res.arw_retains_full_3_2_pixels)
        self.assertFalse(res.fx6_still_aspect_supported)
        self.assertEqual(res.matrix_states_checked, 384)

    def test_13_g121_xavc_si_dci4k_all_6_frame_rates_and_bitrates(self) -> None:
        self.assertEqual(len(DCI_4K_ALLOWED_REC_RATES_G121), 6)
        for rate, mbps in DCI_4K_BITRATES_MBPS_G121.items():
            res = verify_dci4k_and_aspect_ratio_guard(
                requested_file_format=FILE_FORMAT_XAVC_SI_DCI_4K_G121,
                rec_frame_rate=rate,
                requested_movie_dimensions=DCI_4K_DIMENSIONS_G121,
                card_tier=CARD_TIER_CFEXPRESS_VPG200_G121,
                switched_24_00p_boundary=(rate == "24.00p"),
                reboot_completed_for_24_00p=(rate == "24.00p"),
            )
            self.assertTrue(res.valid, msg=f"{rate}: {res.errors}")
            self.assertEqual(res.bitrate_mbps, mbps)
            self.assertEqual(res.movie_dimensions, (4096, 2160))

    def test_14_g121_dci4k_600m_requires_vpg200_or_v90_card(self) -> None:
        for ok_card in DCI4K_600M_ALLOWED_CARD_TIERS_G121:
            res = verify_dci4k_and_aspect_ratio_guard(
                requested_file_format=FILE_FORMAT_XAVC_SI_DCI_4K_G121,
                rec_frame_rate="59.94p",
                card_tier=ok_card,
            )
            self.assertTrue(res.valid, msg=ok_card)

        for slow_card in (CARD_TIER_SDXC_V60_G121, CARD_TIER_SDXC_V30_G121):
            res_bad = verify_dci4k_and_aspect_ratio_guard(
                requested_file_format=FILE_FORMAT_XAVC_SI_DCI_4K_G121,
                rec_frame_rate="59.94p",
                card_tier=slow_card,
            )
            self.assertFalse(res_bad.valid, msg=slow_card)
            self.assertEqual(
                res_bad.status,
                STATUS_BLOCKED_G121_DCI4K_HFR_OR_UNREBOOTED_24P_VIOLATION,
            )

    def test_15_g121_dci4k_sq_allowed_1_to_48fps_and_blocks_100_120fps(self) -> None:
        self.assertEqual(DCI_4K_ALLOWED_SQ_FPS_G121, (1, 2, 3, 6, 12, 24, 48))
        for fps in DCI_4K_ALLOWED_SQ_FPS_G121:
            res = verify_dci4k_and_aspect_ratio_guard(
                shoot_mode=SHOOT_MODE_SQ_PHASE288,
                requested_file_format=FILE_FORMAT_XAVC_SI_DCI_4K_G121,
                sq_fps=fps,
            )
            self.assertTrue(res.valid, msg=f"fps={fps}: {res.errors}")

        for bad_fps in DCI_4K_FORBIDDEN_HFR_FPS_G121 + (60,):
            res_bad = verify_dci4k_and_aspect_ratio_guard(
                shoot_mode=SHOOT_MODE_SQ_PHASE288,
                requested_file_format=FILE_FORMAT_XAVC_SI_DCI_4K_G121,
                sq_fps=bad_fps,
            )
            self.assertFalse(res_bad.valid, msg=bad_fps)
            self.assertEqual(
                res_bad.status,
                STATUS_BLOCKED_G121_DCI4K_HFR_OR_UNREBOOTED_24P_VIOLATION,
            )

    def test_16_g121_dci4k_blocks_100p_119_88p_and_unrebooted_24_00p(self) -> None:
        for hfr in ("100p", "119.88p"):
            res_hfr = verify_dci4k_and_aspect_ratio_guard(
                requested_file_format=FILE_FORMAT_XAVC_SI_DCI_4K_G121,
                rec_frame_rate=hfr,
            )
            self.assertFalse(res_hfr.valid, msg=hfr)
            self.assertEqual(
                res_hfr.status,
                STATUS_BLOCKED_G121_DCI4K_HFR_OR_UNREBOOTED_24P_VIOLATION,
            )

        res_unreboot = verify_dci4k_and_aspect_ratio_guard(
            requested_file_format=FILE_FORMAT_XAVC_SI_DCI_4K_G121,
            rec_frame_rate="24.00p",
            switched_24_00p_boundary=True,
            reboot_completed_for_24_00p=False,
        )
        self.assertFalse(res_unreboot.valid)
        self.assertEqual(
            res_unreboot.status,
            STATUS_BLOCKED_G121_DCI4K_HFR_OR_UNREBOOTED_24P_VIOLATION,
        )

        res_no_quar = verify_dci4k_and_aspect_ratio_guard(
            playback_24_00p_quarantine_enforced=False
        )
        self.assertFalse(res_no_quar.valid)
        self.assertEqual(
            res_no_quar.status,
            STATUS_BLOCKED_G121_DCI4K_HFR_OR_UNREBOOTED_24P_VIOLATION,
        )

    def test_17_g121_dci4k_hfr_and_24p_spoof_flags_blocked(self) -> None:
        for kw in (
            {"claimed_dci4k_supports_120fps": True},
            {"claimed_24_00p_no_reboot_or_shared_playback": True},
            {"requested_movie_dimensions": UHD_4K_DIMENSIONS_G121},
        ):
            res = verify_dci4k_and_aspect_ratio_guard(**kw)
            self.assertFalse(res.valid, msg=kw)
            self.assertEqual(
                res.status,
                STATUS_BLOCKED_G121_DCI4K_HFR_OR_UNREBOOTED_24P_VIOLATION,
            )

    def test_18_g121_longgop_and_xavc_si_4k_strictly_3840x2160_no_dci4k_no_24_00p(self) -> None:
        for fmt in UHD_ONLY_4K_FILE_FORMATS_G121:
            res_ok = verify_dci4k_and_aspect_ratio_guard(
                requested_file_format=fmt,
                rec_frame_rate="119.88p",
                requested_movie_dimensions=UHD_4K_DIMENSIONS_G121,
                sq_fps=120,
            )
            self.assertTrue(res_ok.valid, msg=f"{fmt}: {res_ok.errors}")
            self.assertEqual(res_ok.movie_dimensions, UHD_4K_DIMENSIONS_G121)
            self.assertEqual(res_ok.movie_aspect_label, UHD_4K_ASPECT_LABEL_G121)
            self.assertFalse(res_ok.is_dci_4k_all_intra)

            res_dci = verify_dci4k_and_aspect_ratio_guard(
                requested_file_format=fmt,
                requested_movie_dimensions=DCI_4K_DIMENSIONS_G121,
            )
            self.assertFalse(res_dci.valid, msg=fmt)
            self.assertEqual(
                res_dci.status, STATUS_BLOCKED_G121_LONGGOP_DCI4K_OR_24P_SPOOF_VIOLATION
            )

            res_24 = verify_dci4k_and_aspect_ratio_guard(
                requested_file_format=fmt,
                rec_frame_rate="24.00p",
            )
            self.assertFalse(res_24.valid, msg=fmt)
            self.assertEqual(
                res_24.status, STATUS_BLOCKED_G121_LONGGOP_DCI4K_OR_24P_SPOOF_VIOLATION
            )

    def test_19_g121_longgop_and_8k_spoof_flags_blocked(self) -> None:
        for kw in (
            {"claimed_longgop_supports_dci4k": True},
            {"claimed_longgop_supports_24_00p": True},
            {"claimed_xavc_si_uhd_supports_dci4k": True},
            {"claimed_xavc_hs_8k_active_on_fx3": True},
        ):
            res = verify_dci4k_and_aspect_ratio_guard(**kw)
            self.assertFalse(res.valid, msg=kw)
            self.assertEqual(
                res.status, STATUS_BLOCKED_G121_LONGGOP_DCI4K_OR_24P_SPOOF_VIOLATION
            )

    def test_20_g121_hdmi_raw_4264x2408_requires_log_shooting_not_off(self) -> None:
        for log_m in (
            LOG_SHOOTING_FLEXIBLE_ISO_G121,
            LOG_SHOOTING_CINE_EI_G121,
            LOG_SHOOTING_CINE_EI_QUICK_G121,
        ):
            for rate in HDMI_RAW_ALLOWED_RATES_G121:
                res = verify_dci4k_and_aspect_ratio_guard(
                    hdmi_raw_output_enabled=True,
                    hdmi_raw_dimensions=HDMI_RAW_DIMENSIONS_G121,
                    hdmi_raw_frame_rate=rate,
                    log_shooting=log_m,
                )
                self.assertTrue(res.valid, msg=f"{log_m}/{rate}: {res.errors}")
                self.assertEqual(res.hdmi_raw_dimensions, (4264, 2408))

        res_off = verify_dci4k_and_aspect_ratio_guard(
            hdmi_raw_output_enabled=True,
            hdmi_raw_dimensions=HDMI_RAW_DIMENSIONS_G121,
            log_shooting=LOG_SHOOTING_OFF_G121,
        )
        self.assertFalse(res_off.valid)
        self.assertEqual(
            res_off.status,
            STATUS_BLOCKED_G121_HDMI_RAW_LOG_OR_STILL_ASPECT_SPOOF_VIOLATION,
        )

    def test_21_g121_hdmi_raw_wrong_dimensions_or_120p_blocked(self) -> None:
        for bad_kw in (
            {
                "hdmi_raw_output_enabled": True,
                "hdmi_raw_dimensions": (4096, 2160),
                "log_shooting": LOG_SHOOTING_CINE_EI_G121,
            },
            {
                "hdmi_raw_output_enabled": True,
                "hdmi_raw_frame_rate": "119.88p",
                "log_shooting": LOG_SHOOTING_CINE_EI_G121,
            },
            {"claimed_hdmi_raw_allowed_with_log_off": True},
        ):
            res = verify_dci4k_and_aspect_ratio_guard(**bad_kw)
            self.assertFalse(res.valid, msg=bad_kw)
            self.assertEqual(
                res.status,
                STATUS_BLOCKED_G121_HDMI_RAW_LOG_OR_STILL_ASPECT_SPOOF_VIOLATION,
            )

    def test_22_g121_still_aspect_ratio_all_12_mp_combinations_verified(self) -> None:
        self.assertEqual(
            ALLOWED_STILL_ASPECT_RATIOS_G121, ("3:2", "4:3", "16:9", "1:1")
        )
        for aspect, size_map in STILL_ASPECT_RESOLUTION_TABLE_G121.items():
            for sz, (exp_mp, exp_dims) in size_map.items():
                res = verify_dci4k_and_aspect_ratio_guard(
                    shoot_mode=SHOOT_MODE_M_PHASE288,
                    requested_still_aspect_ratio=aspect,
                    requested_still_image_size=sz,
                )
                self.assertTrue(res.valid, msg=f"{aspect}/{sz}: {res.errors}")
                self.assertEqual(res.effective_still_aspect_ratio, aspect)
                self.assertEqual(res.effective_still_image_size, sz)
                self.assertEqual(res.still_aspect_megapixel_label, exp_mp)
                self.assertEqual(res.still_jpeg_heif_dimensions, exp_dims)
                self.assertTrue(res.arw_retains_full_3_2_pixels)

    def test_23_g121_apsc_s35_steps_l_down_to_m_and_resets_work(self) -> None:
        for aspect in ALLOWED_STILL_ASPECT_RATIOS_G121:
            res = verify_dci4k_and_aspect_ratio_guard(
                shoot_mode=SHOOT_MODE_A_PHASE288,
                requested_still_aspect_ratio=aspect,
                requested_still_image_size=STILL_IMAGE_SIZE_L_G121,
                apsc_s35_shooting="On",
            )
            self.assertTrue(res.valid)
            self.assertEqual(res.effective_still_image_size, STILL_IMAGE_SIZE_M_G121)

        res_cam_rst = verify_dci4k_and_aspect_ratio_guard(
            requested_still_aspect_ratio=ASPECT_RATIO_1_1_G121,
            requested_still_image_size=STILL_IMAGE_SIZE_S_G121,
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE288,
        )
        self.assertTrue(res_cam_rst.valid)
        self.assertEqual(res_cam_rst.effective_still_aspect_ratio, ASPECT_RATIO_3_2_G121)
        self.assertEqual(res_cam_rst.effective_still_image_size, STILL_IMAGE_SIZE_L_G121)
        self.assertTrue(res_cam_rst.still_aspect_reset_on_cam_reset)

        res_net_rst = verify_dci4k_and_aspect_ratio_guard(
            requested_still_aspect_ratio=ASPECT_RATIO_16_9_G121,
            reset_action=RESET_ACTION_RESET_NETWORK_SET_PHASE288,
        )
        self.assertTrue(res_net_rst.valid)
        self.assertEqual(res_net_rst.effective_still_aspect_ratio, ASPECT_RATIO_16_9_G121)
        self.assertFalse(res_net_rst.still_aspect_reset_on_cam_reset)

    def test_24_g121_aspect_and_fx6_spoof_flags_blocked(self) -> None:
        for kw in (
            {"claimed_arw_crops_raw_sensor_pixels": True},
            {"claimed_apsc_s35_keeps_l_size": True},
            {"claimed_fx6_has_still_aspect_ratio": True},
            {"claimed_camera_reset_preserves_still_aspect": True},
        ):
            res = verify_dci4k_and_aspect_ratio_guard(**kw)
            self.assertFalse(res.valid, msg=kw)
            self.assertEqual(
                res.status,
                STATUS_BLOCKED_G121_HDMI_RAW_LOG_OR_STILL_ASPECT_SPOOF_VIOLATION,
            )

    def test_25_g121_384_state_matrix_invariants(self) -> None:
        m = compute_dci4k_hdmi_raw_and_aspect_ratio_matrix()
        self.assertEqual(m["states_checked"], 384)
        self.assertEqual(m["dci4k_all_intra_states"], 96)
        self.assertEqual(m["longgop_uhd_states"], 192)
        self.assertEqual(m["aspect_reset_to_3_2_states"], 128)
        self.assertEqual(m["apsc_l_to_m_stepdown_states"], 128)
        self.assertTrue(m["all_invariants_hold"])

    def test_26_g121_invalid_telemetry_rejected(self) -> None:
        for bad_kw in (
            {"body_model_name": FX6_MODEL_NAME_PHASE288},
            {"body_model_id": True},
            {"help_guide_code": "ilc/9999"},
            {"requested_file_format": "ProRes 422"},
            {"rec_frame_rate": "48p"},
            {"card_tier": "VHS"},
            {"sq_fps": True},
            {"sq_fps": 0},
            {"log_shooting": "S-Log2"},
            {"requested_still_aspect_ratio": "2:1"},
            {"requested_still_image_size": "XL"},
            {"reset_action": "BOGUS"},
        ):
            res = verify_dci4k_and_aspect_ratio_guard(**bad_kw)
            self.assertFalse(res.valid, msg=bad_kw)
            self.assertEqual(res.status, STATUS_BLOCKED_G121_TELEMETRY_INVALID)

    def test_27_g121_evaluator_blocks_persistent_emmc_writes(self) -> None:
        verdict, res = evaluate_g121_dci4k_and_aspect_ratio_guard(
            force_clean_room=True,
            request_persistent_emmc_writes=True,
        )
        self.assertFalse(verdict.passed)
        self.assertFalse(res.valid)
        self.assertEqual(verdict.status, "BLOCKED_BY_PERSISTENT_EMMC_WRITE_REDLINE")

    def test_28_g121_rate_and_codec_normalization_aliases(self) -> None:
        res = verify_dci4k_and_aspect_ratio_guard(
            requested_file_format="[XAVC S-I DCI 4K]",
            rec_frame_rate="24p",
            switched_24_00p_boundary=True,
            reboot_completed_for_24_00p=True,
            card_tier="VPG200",
        )
        self.assertTrue(res.valid, msg=res.errors)
        self.assertEqual(res.rec_frame_rate, "24.00p")
        self.assertEqual(res.bitrate_mbps, 240)
        self.assertEqual(res.card_tier, CARD_TIER_CFEXPRESS_VPG200_G121)

    def test_29_g121_menu_paths_and_evidence_tokens(self) -> None:
        self.assertIn("[File Format]", FILE_FORMAT_MENU_PATH_G121)
        self.assertIn("[Movie Settings]", MOVIE_SETTINGS_MENU_PATH_G121)
        self.assertIn("[HDMI Output Settings]", RAW_OUTPUT_MENU_PATH_G121)
        self.assertIn("[Aspect Ratio]", ASPECT_RATIO_MENU_PATH_G121)
        verdict, res = evaluate_g121_dci4k_and_aspect_ratio_guard(force_clean_room=True)
        self.assertTrue(verdict.passed)
        self.assertIn("4096x2160@23.98p", verdict.evidence)
        self.assertIn("4264x2408", verdict.evidence)
        self.assertIn("fx6_still_aspect=False", verdict.evidence)
        self.assertEqual(
            json.loads(json.dumps(res.to_dict()))["status"], STATUS_VERIFIED_G121
        )

    def test_30_g121_longgop_all_uhd_rates_valid(self) -> None:
        for fmt in LONGGOP_4K_FILE_FORMATS_G121:
            for rate in UHD_4K_ALLOWED_REC_RATES_G121:
                if fmt == FILE_FORMAT_XAVC_HS_4K_G121 and rate == "29.97p":
                    continue
                res = verify_dci4k_and_aspect_ratio_guard(
                    requested_file_format=fmt,
                    rec_frame_rate=rate,
                    requested_movie_dimensions=UHD_4K_DIMENSIONS_G121,
                )
                self.assertTrue(res.valid, msg=f"{fmt}/{rate}: {res.errors}")

    def test_31_g121_factory_defaults_and_raw_full_sensor_constants(self) -> None:
        self.assertEqual(FILE_FORMAT_FACTORY_DEFAULT_G121, FILE_FORMAT_XAVC_S_4K_G121)
        self.assertEqual(FX3_RAW_FULL_SENSOR_DIMENSIONS_G121, (4240, 2832))
        self.assertEqual(HDMI_RAW_ASPECT_LABEL_G121, "16:9")
        self.assertEqual(UHD_4K_MAX_SQ_FPS_G121, 120)

    def test_32_g121_xavc_si_4k_sq_120fps_allowed_unlike_dci4k(self) -> None:
        res_uhd = verify_dci4k_and_aspect_ratio_guard(
            shoot_mode=SHOOT_MODE_SQ_PHASE288,
            requested_file_format=FILE_FORMAT_XAVC_SI_4K_G121,
            sq_fps=120,
        )
        self.assertTrue(res_uhd.valid, msg=res_uhd.errors)
        res_dci = verify_dci4k_and_aspect_ratio_guard(
            shoot_mode=SHOOT_MODE_SQ_PHASE288,
            requested_file_format=FILE_FORMAT_XAVC_SI_DCI_4K_G121,
            sq_fps=120,
        )
        self.assertFalse(res_dci.valid)

    def test_33_g121_initialize_resets_still_aspect_to_3_2_l(self) -> None:
        res = verify_dci4k_and_aspect_ratio_guard(
            requested_still_aspect_ratio=ASPECT_RATIO_4_3_G121,
            requested_still_image_size=STILL_IMAGE_SIZE_S_G121,
            reset_action=RESET_ACTION_INITIALIZE_PHASE288,
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.effective_still_aspect_ratio, ASPECT_RATIO_3_2_G121)
        self.assertEqual(res.effective_still_image_size, STILL_IMAGE_SIZE_L_G121)

    def test_34_g121_all_4_allowed_4k_formats_and_card_tiers_enumerated(self) -> None:
        self.assertEqual(len(ALLOWED_4K_FILE_FORMATS_G121), 4)
        self.assertEqual(len(ALLOWED_CARD_TIERS_G121), 4)
        self.assertEqual(len(ALLOWED_LOG_SHOOTING_MODES_G121), 4)
        self.assertEqual(len(ALLOWED_STILL_IMAGE_SIZES_G121), 3)

    def test_35_g121_fx3_vs_fx6_fw_version_fields_recorded(self) -> None:
        res = verify_dci4k_and_aspect_ratio_guard()
        self.assertEqual(res.firmware_version, FX3_DEFAULT_FW_VERSION_PHASE288)
        self.assertEqual(res.fx6_comparison_fw_version, FX6_DEFAULT_FW_VERSION_PHASE288)
        self.assertFalse(res.fx6_longgop_has_dci4k)

    # --- 3. Gate G122: [Reg. Custom Shoot Set], [Camera Set. Memory], Paths, Photo Capture & Enlarge (Tests 36-58) ---

    def test_36_g122_uxc_resid16_and_11_checkbox_constants(self) -> None:
        self.assertEqual(REG_CUSTOM_SHOOT_SET_UXC_RESID16_G122, 0x7631)
        self.assertEqual(RECALL_CUSTOM_HOLD_1_UXC_RESID16_G122, 0x60B4)
        self.assertEqual(RECALL_CUSTOM_HOLD_2_UXC_RESID16_G122, 0x7581)
        self.assertEqual(RECALL_CUSTOM_HOLD_3_UXC_RESID16_G122, 0x725B)
        self.assertEqual(CAMERA_SET_MEMORY_UXC_RESID16_G122, 0x75A6)
        self.assertEqual(MEMORY_RECALL_MEDIA_UXC_RESID16_G122, 0x763C)
        self.assertEqual(PHOTO_CAPTURE_UXC_RESID16_G122, 0x6856)
        self.assertEqual(PHOTO_CAPTURE_DCI4K_LOCKOUT_G_UXC_RESID16_G122, 0x60CE)
        self.assertEqual(JPEG_HEIF_SWITCH_UXC_RESID16_G122, 0x6938)
        self.assertEqual(ENLARGE_IMAGE_UXC_RESID16_G122, 0xE8CB)
        self.assertEqual(ENLARGE_INITIAL_MAG_UXC_RESID16_G122, 0x6B6E)
        self.assertEqual(ENLARGE_INITIAL_POSITION_UXC_RESID16_G122, 0x781F)
        self.assertEqual(len(FX3_EXACT_11_CUSTOM_HOLD_CHECKBOX_KEYS_G122), 11)
        self.assertEqual(len(FX3_EXACT_11_CUSTOM_HOLD_BOOL_SYMBOLS_G122), 11)
        self.assertEqual(
            FX3_EXACT_11_CUSTOM_HOLD_BOOL_SYMBOLS_G122[0],
            "is_checked_recall_custom_hold0",
        )
        self.assertEqual(
            FX3_EXACT_11_CUSTOM_HOLD_BOOL_SYMBOLS_G122[-1],
            "is_checked_recall_custom_hold10",
        )

    def test_37_g122_default_state_verified(self) -> None:
        res = verify_custom_hold_camset_photo_capture_guard()
        self.assertIsInstance(res, CustomHoldCamsetPhotoEnlargeGuardResult)
        self.assertTrue(res.valid, msg=res.errors)
        self.assertEqual(res.status, STATUS_VERIFIED_G122)
        self.assertEqual(len(res.exact_11_custom_hold_keys), 11)
        self.assertTrue(res.fx6_pro_camera_path_rejected)
        self.assertTrue(res.format_slot_1_protected)
        self.assertTrue(res.photo_capture_dci4k_locked)
        self.assertTrue(res.photo_capture_slot1_write_blocked)
        self.assertEqual(res.effective_photo_capture_file_type, PHOTO_CAPTURE_TYPE_JPEG_G122)
        self.assertEqual(res.effective_enlarge_initial_mag, ENLARGE_INITIAL_MAG_STANDARD_G122)
        self.assertEqual(res.effective_enlarge_initial_position, ENLARGE_INITIAL_POS_FOCUSED_G122)
        self.assertFalse(res.fx6_photo_capture_supported)
        self.assertFalse(res.fx6_playback_enlarge_supported)
        self.assertEqual(res.matrix_states_checked, 384)

    def test_38_g122_recall_custom_hold_pasm_only_all_11_checkboxes(self) -> None:
        for sm in PASM_SHOOT_MODES_PHASE288:
            for slot in RECALL_CUSTOM_HOLD_SLOTS_G122:
                res = verify_custom_hold_camset_photo_capture_guard(
                    shoot_mode=sm,
                    recall_custom_hold_requested=True,
                    recall_custom_hold_slot=slot,
                    recalled_hold_params=FX3_EXACT_11_CUSTOM_HOLD_CHECKBOX_KEYS_G122,
                    hlg_still_image_on=False,
                )
                self.assertTrue(res.valid, msg=f"{sm}/{slot}: {res.errors}")
                self.assertTrue(res.hlg_still_image_forced_off)

    def test_39_g122_recall_custom_hold_blocked_in_movie_sq_iauto_mr_and_hlg(self) -> None:
        for bad_sm in (
            SHOOT_MODE_MOVIE_PHASE288,
            SHOOT_MODE_SQ_PHASE288,
            SHOOT_MODE_INTELLIGENT_AUTO_PHASE288,
            SHOOT_MODE_MR_PHASE288,
        ):
            res = verify_custom_hold_camset_photo_capture_guard(
                shoot_mode=bad_sm,
                recall_custom_hold_requested=True,
            )
            self.assertFalse(res.valid, msg=bad_sm)
            self.assertEqual(
                res.status, STATUS_BLOCKED_G122_RECALL_CUSTOM_HOLD_MODE_OR_HLG_VIOLATION
            )

        for param in HLG_LOCKOUT_RECALL_PARAMS_G122:
            res_hlg = verify_custom_hold_camset_photo_capture_guard(
                shoot_mode=SHOOT_MODE_M_PHASE288,
                recall_custom_hold_requested=True,
                recalled_hold_params=(param,),
                hlg_still_image_on=True,
            )
            self.assertFalse(res_hlg.valid, msg=param)
            self.assertEqual(
                res_hlg.status,
                STATUS_BLOCKED_G122_RECALL_CUSTOM_HOLD_MODE_OR_HLG_VIOLATION,
            )

        for bad_kw in (
            {"recalled_hold_params": ("self_timer",)},
            {"claimed_recall_custom_hold_includes_self_timer": True},
            {"claimed_camera_reset_wipes_custom_hold_or_camset_1_3": True},
        ):
            res_sp = verify_custom_hold_camset_photo_capture_guard(**bad_kw)
            self.assertFalse(res_sp.valid, msg=bad_kw)
            self.assertEqual(
                res_sp.status,
                STATUS_BLOCKED_G122_RECALL_CUSTOM_HOLD_MODE_OR_HLG_VIOLATION,
            )

    def test_40_g122_fx3_camset_and_campr_paths_accepted_and_fx6_spoof_rejected(self) -> None:
        for good_path in (
            FX3_CAMPR_PATH_TEMPLATE_G122,
            FX3_CAMSET_PATH_TEMPLATE_G122,
            "1:/PRIVATE/SONY/SETTING/FX3/CAMPR01A.DAT",
            "1:/SONY/SETTING/FX3/CAMSET/CAMSET01.DAT",
        ):
            res = verify_custom_hold_camset_photo_capture_guard(
                submitted_card_path=good_path
            )
            self.assertTrue(res.valid, msg=f"{good_path}: {res.errors}")

        for bad_path in (
            "PRIVATE/SONY/PRO/CAMERA/CAMSET01.DAT",
            "1:/PRIVATE/SONY/PRO/CAMERA/USER01.DAT",
            "s/SONY/PRO/CAMERA/",
            "s/SONY/PRO/SCENE/",
            "/DCIM/100MSDCF/DSC00001.JPG",
        ):
            res_bad = verify_custom_hold_camset_photo_capture_guard(
                submitted_card_path=bad_path
            )
            self.assertFalse(res_bad.valid, msg=bad_path)
            self.assertEqual(
                res_bad.status, STATUS_BLOCKED_G122_FX3_CAMSET_CARD_PATH_SPOOF_VIOLATION
            )

    def test_41_g122_save_load_slot1_only_mr_block_and_format_slot1_firewall(self) -> None:
        res_ok = verify_custom_hold_camset_photo_capture_guard(
            shoot_mode=SHOOT_MODE_M_PHASE288,
            save_load_settings_requested=True,
            save_load_target_slot="Slot 1",
            submitted_card_path=FX3_CAMSET_PATH_TEMPLATE_G122,
        )
        self.assertTrue(res_ok.valid, msg=res_ok.errors)

        for bad_kw in (
            {
                "shoot_mode": SHOOT_MODE_MR_PHASE288,
                "save_load_settings_requested": True,
                "save_load_target_slot": "Slot 1",
            },
            {
                "save_load_settings_requested": True,
                "save_load_target_slot": "Slot 2",
            },
            {
                "format_slot_1_requested": True,
                "slot_1_contains_camset_or_m1_m4_vault": True,
            },
            {"claimed_format_preserves_camset_or_m1_m4": True},
        ):
            res_bad = verify_custom_hold_camset_photo_capture_guard(**bad_kw)
            self.assertFalse(res_bad.valid, msg=bad_kw)
            self.assertEqual(
                res_bad.status, STATUS_BLOCKED_G122_FX3_CAMSET_CARD_PATH_SPOOF_VIOLATION
            )

    def test_42_g122_photo_capture_slot2_uhd_and_hd_all_3_file_types_valid(self) -> None:
        for ftype in ALLOWED_PHOTO_CAPTURE_FILE_TYPES_G122:
            for tier, exp_mp, exp_dims in (
                ("4K", PHOTO_CAPTURE_4K_MP_LABEL_G122, PHOTO_CAPTURE_4K_DIMENSIONS_G122),
                ("HD", PHOTO_CAPTURE_HD_MP_LABEL_G122, PHOTO_CAPTURE_HD_DIMENSIONS_G122),
            ):
                res = verify_custom_hold_camset_photo_capture_guard(
                    photo_capture_requested=True,
                    playback_slot="Slot 2",
                    playback_source_file_format=FILE_FORMAT_XAVC_S_4K_G121,
                    playback_source_resolution_tier=tier,
                    requested_photo_capture_file_type=ftype,
                )
                self.assertTrue(res.valid, msg=f"{ftype}/{tier}: {res.errors}")
                self.assertEqual(res.effective_photo_capture_file_type, ftype)
                self.assertEqual(res.photo_capture_output_mp_label, exp_mp)
                self.assertEqual(res.photo_capture_output_dimensions, exp_dims)

    def test_43_g122_photo_capture_blocked_on_dci4k_and_slot1_vault(self) -> None:
        res_dci = verify_custom_hold_camset_photo_capture_guard(
            photo_capture_requested=True,
            playback_slot="Slot 2",
            playback_source_file_format=FILE_FORMAT_XAVC_SI_DCI_4K_G121,
        )
        self.assertFalse(res_dci.valid)
        self.assertEqual(
            res_dci.status,
            STATUS_BLOCKED_G122_PHOTO_CAPTURE_DCI4K_OR_SLOT1_WRITE_VIOLATION,
        )

        res_slot1 = verify_custom_hold_camset_photo_capture_guard(
            photo_capture_requested=True,
            playback_slot="Slot 1",
            playback_source_file_format=FILE_FORMAT_XAVC_S_4K_G121,
        )
        self.assertFalse(res_slot1.valid)
        self.assertEqual(
            res_slot1.status,
            STATUS_BLOCKED_G122_PHOTO_CAPTURE_DCI4K_OR_SLOT1_WRITE_VIOLATION,
        )

        for sp in (
            {"claimed_photo_capture_supported_on_dci4k": True},
            {"claimed_photo_capture_read_only": True},
        ):
            res_sp = verify_custom_hold_camset_photo_capture_guard(**sp)
            self.assertFalse(res_sp.valid, msg=sp)
            self.assertEqual(
                res_sp.status,
                STATUS_BLOCKED_G122_PHOTO_CAPTURE_DCI4K_OR_SLOT1_WRITE_VIOLATION,
            )

    def test_44_g122_enlarge_image_still_only_and_exact_ilc2210_mag_position(self) -> None:
        for mag in ALLOWED_ENLARGE_INITIAL_MAG_G122:
            for pos in ALLOWED_ENLARGE_INITIAL_POS_G122:
                res = verify_custom_hold_camset_photo_capture_guard(
                    enlarge_image_requested=True,
                    playback_media_kind="Still",
                    requested_enlarge_initial_mag=mag,
                    requested_enlarge_initial_position=pos,
                    reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE288,
                )
                self.assertTrue(res.valid, msg=f"{mag}/{pos}: {res.errors}")
                self.assertEqual(res.effective_enlarge_initial_mag, mag)
                self.assertEqual(res.effective_enlarge_initial_position, pos)
                self.assertTrue(res.enlarge_settings_survived_cam_reset)

        res_mv = verify_custom_hold_camset_photo_capture_guard(
            enlarge_image_requested=True,
            playback_media_kind="Movie",
        )
        self.assertFalse(res_mv.valid)
        self.assertEqual(
            res_mv.status,
            STATUS_BLOCKED_G122_ENLARGE_IMAGE_OR_RESET_PERSISTENCE_VIOLATION,
        )

    def test_45_g122_enlarge_spoofs_and_initialize_reset_behavior(self) -> None:
        for bad_kw in (
            {"claimed_enlarge_image_supported_on_movie": True},
            {"claimed_enlarge_initial_mag_init_alias": True},
            {"claimed_camera_reset_wipes_enlarge_or_photo_capture": True},
            {"claimed_fx6_has_photo_capture_or_playback_enlarge": True},
        ):
            res = verify_custom_hold_camset_photo_capture_guard(**bad_kw)
            self.assertFalse(res.valid, msg=bad_kw)
            self.assertEqual(
                res.status,
                STATUS_BLOCKED_G122_ENLARGE_IMAGE_OR_RESET_PERSISTENCE_VIOLATION,
            )

        res_init = verify_custom_hold_camset_photo_capture_guard(
            requested_photo_capture_file_type=PHOTO_CAPTURE_TYPE_HEIF_422_G122,
            requested_enlarge_initial_mag=ENLARGE_INITIAL_MAG_PREVIOUS_G122,
            requested_enlarge_initial_position=ENLARGE_INITIAL_POS_CENTER_G122,
            reset_action=RESET_ACTION_INITIALIZE_PHASE288,
        )
        self.assertTrue(res_init.valid)
        self.assertEqual(
            res_init.effective_photo_capture_file_type,
            PHOTO_CAPTURE_FILE_TYPE_DEFAULT_G122,
        )
        self.assertEqual(
            res_init.effective_enlarge_initial_mag, ENLARGE_INITIAL_MAG_DEFAULT_G122
        )
        self.assertEqual(
            res_init.effective_enlarge_initial_position, ENLARGE_INITIAL_POS_DEFAULT_G122
        )
        self.assertFalse(res_init.enlarge_settings_survived_cam_reset)

    def test_46_g122_384_state_matrix_invariants(self) -> None:
        m = compute_custom_hold_camset_photo_and_enlarge_matrix()
        self.assertEqual(m["states_checked"], 384)
        self.assertEqual(m["hlg_forced_off_states"], 192)
        self.assertEqual(m["cam_reset_survived_states"], 192)
        self.assertEqual(m["init_reset_states"], 192)
        self.assertEqual(m["slot1_protected_states"], 192)
        self.assertTrue(m["all_invariants_hold"])

    def test_47_g122_invalid_telemetry_rejected(self) -> None:
        for bad_kw in (
            {"body_model_name": FX6_MODEL_NAME_PHASE288},
            {"body_model_id": False},
            {"help_guide_code": "ilc/0000"},
            {"shoot_mode": "Scene"},
            {"recall_custom_hold_slot": "Recall Custom hold 9"},
            {"recalled_hold_params": "aperture"},
            {"camset_memory_slot": "M9"},
            {"camset_media_slot": "Slot 9"},
            {"save_load_target_slot": "Slot 3"},
            {"playback_slot": "Slot 0"},
            {"requested_photo_capture_file_type": "TIFF"},
            {"playback_source_resolution_tier": "8K"},
            {"playback_media_kind": "Audio"},
            {"requested_enlarge_initial_mag": "Init."},
            {"requested_enlarge_initial_position": "TopLeft"},
            {"reset_action": "BOGUS"},
        ):
            res = verify_custom_hold_camset_photo_capture_guard(**bad_kw)
            self.assertFalse(res.valid, msg=bad_kw)
            self.assertEqual(res.status, STATUS_BLOCKED_G122_TELEMETRY_INVALID)

    def test_48_g122_evaluator_blocks_persistent_emmc_writes(self) -> None:
        verdict, res = evaluate_g122_custom_hold_camset_photo_capture_guard(
            force_clean_room=True,
            request_persistent_emmc_writes=True,
        )
        self.assertFalse(verdict.passed)
        self.assertFalse(res.valid)
        self.assertEqual(verdict.status, "BLOCKED_BY_PERSISTENT_EMMC_WRITE_REDLINE")

    def test_49_g122_camset_all_body_and_card_banks_plus_media_reset(self) -> None:
        self.assertEqual(CAMERA_MEMORY_BODY_BANKS_G122, ("1", "2", "3"))
        self.assertEqual(CAMERA_MEMORY_CARD_BANKS_G122, ("M1", "M2", "M3", "M4"))
        self.assertEqual(ALLOWED_MEMORY_RECALL_MEDIA_SLOTS_G122, ("Slot 1", "Slot 2"))
        for slot in CAMERA_MEMORY_BODY_BANKS_G122 + CAMERA_MEMORY_CARD_BANKS_G122:
            res = verify_custom_hold_camset_photo_capture_guard(
                camset_memory_slot=slot,
                camset_media_slot="Slot 2",
                reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE288,
            )
            self.assertTrue(res.valid, msg=slot)
            self.assertEqual(res.camset_memory_slot, slot)
            self.assertEqual(res.camset_media_slot, "Slot 1")
            self.assertTrue(res.body_memory_banks_survived_cam_reset)

    def test_50_g122_sd_vs_cfexpress_concrete_sample_paths(self) -> None:
        r_sd = resolve_fx3_custom_hold_camset_photo_and_enlarge_state(
            use_cfexpress_media=False
        )
        self.assertEqual(
            r_sd["concrete_sample_campr_path"], "1:/PRIVATE/SONY/SETTING/FX3/CAMPR01A.DAT"
        )
        self.assertEqual(
            r_sd["concrete_sample_camset_path"],
            "1:/PRIVATE/SONY/SETTING/FX3/CAMSET/CAMSET01.DAT",
        )
        r_cfe = resolve_fx3_custom_hold_camset_photo_and_enlarge_state(
            use_cfexpress_media=True
        )
        self.assertEqual(
            r_cfe["concrete_sample_campr_path"], "1:/SONY/SETTING/FX3/CAMPR01A.DAT"
        )
        self.assertEqual(
            r_cfe["concrete_sample_camset_path"],
            "1:/SONY/SETTING/FX3/CAMSET/CAMSET01.DAT",
        )

    def test_51_g122_menu_paths_and_constants(self) -> None:
        self.assertIn("[Reg. Custom Shoot Set]", REG_CUSTOM_SHOOT_SET_MENU_PATH_G122)
        self.assertIn("[Camera Set. Memory]", CAMERA_SET_MEMORY_MENU_PATH_G122)
        self.assertIn("[Save/Load Settings]", SAVE_LOAD_SETTINGS_MENU_PATH_G122)
        self.assertIn("[Photo Capture]", PHOTO_CAPTURE_MENU_PATH_G122)
        self.assertIn("[Enlarge Image]", ENLARGE_IMAGE_MENU_PATH_G122)
        self.assertEqual(len(FX3_ALLOWED_CARD_PATH_PREFIXES_G122), 2)
        self.assertEqual(len(FX6_FORBIDDEN_CARD_PATH_MARKERS_G122), 5)

    def test_52_g122_evidence_and_json_roundtrip(self) -> None:
        verdict, res = evaluate_g122_custom_hold_camset_photo_capture_guard(
            force_clean_room=True
        )
        self.assertTrue(verdict.passed)
        self.assertIn("hold_keys=11", verdict.evidence)
        self.assertIn("slot1_blk=True", verdict.evidence)
        self.assertIn("fx6_photo=False", verdict.evidence)
        self.assertEqual(
            json.loads(json.dumps(res.to_dict()))["status"], STATUS_VERIFIED_G122
        )

    def test_53_all_9_shoot_modes_handled_across_g121_and_g122_without_telemetry_error(
        self,
    ) -> None:
        self.assertEqual(len(ALLOWED_SHOOT_MODES_PHASE288), 9)
        self.assertEqual(len(STILL_SHOOT_MODES_PHASE288), 6)
        self.assertEqual(len(MOVIE_SHOOT_MODES_PHASE288), 2)
        for sm in ALLOWED_SHOOT_MODES_PHASE288:
            r1 = verify_dci4k_and_aspect_ratio_guard(shoot_mode=sm)
            self.assertTrue(r1.valid, msg=sm)
            r2 = verify_custom_hold_camset_photo_capture_guard(
                shoot_mode=sm, recall_custom_hold_requested=False
            )
            self.assertTrue(r2.valid, msg=sm)

    def test_54_all_4_reset_actions_accepted_in_g121_and_g122(self) -> None:
        self.assertEqual(len(ALLOWED_RESET_ACTIONS_PHASE288), 4)
        for r_act in ALLOWED_RESET_ACTIONS_PHASE288:
            r1 = verify_dci4k_and_aspect_ratio_guard(reset_action=r_act)
            self.assertTrue(r1.valid, msg=r_act)
            r2 = verify_custom_hold_camset_photo_capture_guard(reset_action=r_act)
            self.assertTrue(r2.valid, msg=r_act)

    def test_55_g122_heif_420_and_422_aliases_normalized(self) -> None:
        for raw, exp in (
            ("HEIF(4:2:0)", PHOTO_CAPTURE_TYPE_HEIF_420_G122),
            ("heif 4:2:0", PHOTO_CAPTURE_TYPE_HEIF_420_G122),
            ("HEIF(4:2:2)", PHOTO_CAPTURE_TYPE_HEIF_422_G122),
            ("heif422", PHOTO_CAPTURE_TYPE_HEIF_422_G122),
        ):
            res = verify_custom_hold_camset_photo_capture_guard(
                requested_photo_capture_file_type=raw
            )
            self.assertTrue(res.valid, msg=raw)
            self.assertEqual(res.effective_photo_capture_file_type, exp)

    def test_56_g122_format_slot1_allowed_only_when_not_requested_or_empty(self) -> None:
        res_empty = verify_custom_hold_camset_photo_capture_guard(
            format_slot_1_requested=True,
            slot_1_contains_camset_or_m1_m4_vault=False,
        )
        self.assertTrue(res_empty.valid)

    def test_57_g122_network_reset_preserves_media_slot_and_playback_settings(self) -> None:
        res = verify_custom_hold_camset_photo_capture_guard(
            camset_media_slot="Slot 2",
            requested_photo_capture_file_type=PHOTO_CAPTURE_TYPE_HEIF_420_G122,
            requested_enlarge_initial_mag=ENLARGE_INITIAL_MAG_PREVIOUS_G122,
            requested_enlarge_initial_position=ENLARGE_INITIAL_POS_CENTER_G122,
            reset_action=RESET_ACTION_RESET_NETWORK_SET_PHASE288,
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.camset_media_slot, "Slot 2")
        self.assertEqual(
            res.effective_photo_capture_file_type, PHOTO_CAPTURE_TYPE_HEIF_420_G122
        )
        self.assertEqual(
            res.effective_enlarge_initial_mag, ENLARGE_INITIAL_MAG_PREVIOUS_G122
        )

    def test_58_g122_body_model_hex_string_preserved(self) -> None:
        res = verify_custom_hold_camset_photo_capture_guard()
        self.assertEqual(res.body_model_id_hex, "0x91030080")
        self.assertEqual(res.effective_campr_path_template, FX3_CAMPR_PATH_TEMPLATE_G122)
        self.assertEqual(res.effective_camset_path_template, FX3_CAMSET_PATH_TEMPLATE_G122)

    # --- 4. Unified 122-Gate Preflight (`evaluate_122gate_preflight`, Tests 59-70) ---

    def test_59_master_122_offline_mode_119_of_122_with_mocked_upstream(self) -> None:
        rep = evaluate_122gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=False,
            master_120_override=self.clean_offline_120,
        )
        self.assertIsInstance(rep, Master122GateReport)
        self.assertEqual(rep.status, "VERIFIED_119_OF_122_AWAITING_PHYSICAL_TIER0")
        self.assertEqual(rep.summary["total_gates"], 122)
        self.assertEqual(rep.summary["verified_gates"], 119)
        self.assertEqual(rep.summary["blocked_or_pending_gates"], 3)
        self.assertEqual(rep.summary["g01_to_g12_verified"], 9)
        self.assertEqual(rep.summary["g13_to_g120_verified"], 108)
        self.assertEqual(rep.summary["g121_to_g122_verified"], 2)
        self.assertTrue(rep.offline_119_gates_verified)
        self.assertFalse(rep.all_122_gates_verified)
        self.assertTrue(rep.g13_to_g122_all_passed)
        self.assertTrue(rep.g121_to_g122_all_passed)
        self.assertTrue(rep.h0_h1_trial_entry_allowed)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertEqual(len(rep.gates), 122)

    def test_60_master_122_dry_run_mode_122_of_122_and_redlines_locked(self) -> None:
        rep = evaluate_122gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            master_120_override=self.clean_dryrun_120,
        )
        self.assertEqual(rep.status, "VERIFIED_ALL_122_GATES_DRY_RUN_SIMULATED_BACKUP")
        self.assertTrue(rep.all_122_gates_verified)
        self.assertTrue(rep.dry_run_rehearsal_only)
        self.assertEqual(rep.summary["verified_gates"], 122)
        self.assertEqual(rep.summary["blocked_or_pending_gates"], 0)
        self.assertEqual(rep.summary["g01_to_g12_verified"], 12)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.hardware_live_attachment_authorized)
        self.assertFalse(rep.el3_payload_transmit_authorized)
        self.assertFalse(rep.spi_nor_write_authorized)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertEqual(rep.usb_packets_transmitted, 0)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_61_master_122_simulate_bench_dry_run_flag_alias(self) -> None:
        rep = evaluate_122gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            simulate_bench_dry_run=True,
            master_120_override=self.clean_dryrun_120,
        )
        self.assertTrue(rep.all_122_gates_verified)
        self.assertTrue(rep.dry_run_rehearsal_only)

    def test_62_master_122_propagates_g121_and_g122_failures(self) -> None:
        rep121 = evaluate_122gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            dci4k_aspect_kwargs={"claimed_longgop_supports_dci4k": True},
            master_120_override=self.clean_dryrun_120,
        )
        self.assertEqual(
            rep121.status, STATUS_BLOCKED_G121_LONGGOP_DCI4K_OR_24P_SPOOF_VIOLATION
        )
        self.assertFalse(rep121.g121_to_g122_all_passed)
        self.assertFalse(rep121.all_122_gates_verified)

        rep122 = evaluate_122gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            custom_hold_camset_photo_kwargs={
                "photo_capture_requested": True,
                "playback_slot": "Slot 1",
            },
            master_120_override=self.clean_dryrun_120,
        )
        self.assertEqual(
            rep122.status,
            STATUS_BLOCKED_G122_PHOTO_CAPTURE_DCI4K_OR_SLOT1_WRITE_VIOLATION,
        )
        self.assertFalse(rep122.g121_to_g122_all_passed)
        self.assertFalse(rep122.all_122_gates_verified)

    def test_63_master_122_propagates_upstream_g120_failure(self) -> None:
        broken_120 = dataclasses.replace(
            self.clean_dryrun_120,
            g13_to_g120_all_passed=False,
            status="BLOCKED_G120_FLASH_MOVIE_ESHUTTER_OR_HV_SHOE_VIOLATION",
        )
        rep = evaluate_122gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            master_120_override=broken_120,
        )
        self.assertEqual(
            rep.status, "BLOCKED_G120_FLASH_MOVIE_ESHUTTER_OR_HV_SHOE_VIOLATION"
        )
        self.assertFalse(rep.g13_to_g122_all_passed)
        self.assertFalse(rep.all_122_gates_verified)

    def test_64_master_122_blocks_persistent_emmc_write_request(self) -> None:
        rep = evaluate_122gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            request_persistent_emmc_writes=True,
            master_120_override=self.clean_dryrun_120,
        )
        self.assertEqual(rep.status, "BLOCKED_BY_PERSISTENT_EMMC_WRITE_REDLINE")
        self.assertFalse(rep.all_122_gates_verified)
        self.assertFalse(rep.h0_h1_trial_entry_allowed)

    def test_65_master_122_gate_sequence_g119_to_g122_exact(self) -> None:
        rep = evaluate_122gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            master_120_override=self.clean_dryrun_120,
        )
        self.assertEqual(rep.gates[-1]["gate_id"], G122_GATE_ID)
        self.assertEqual(rep.gates[-2]["gate_id"], G121_GATE_ID)
        self.assertEqual(
            rep.gates[-3]["gate_id"],
            "G120_iso_range_minss_cine_ei_and_still_mechanical_flash_sync_guard",
        )
        self.assertEqual(
            rep.gates[-4]["gate_id"],
            "G119_focus_area_14opt_af_reg_xlrh1_no_zoom_lever_and_zoom_speed_guard",
        )

    def test_66_master_122_to_dict_is_json_serializable(self) -> None:
        rep = evaluate_122gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=False,
            master_120_override=self.clean_offline_120,
        )
        loaded = json.loads(json.dumps(rep.to_dict()))
        self.assertEqual(loaded["summary"]["total_gates"], 122)
        self.assertEqual(loaded["summary"]["verified_gates"], 119)
        self.assertEqual(loaded["summary"]["g121_to_g122_verified"], 2)

    def test_67_master_122_full_live_stack_without_override(self) -> None:
        rep_off = evaluate_122gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=False,
        )
        self.assertTrue(rep_off.offline_119_gates_verified)
        self.assertEqual(rep_off.summary["verified_gates"], 119)
        self.assertEqual(rep_off.status, "VERIFIED_119_OF_122_AWAITING_PHYSICAL_TIER0")

        rep_dry = evaluate_122gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
        )
        self.assertTrue(rep_dry.all_122_gates_verified)
        self.assertEqual(rep_dry.summary["verified_gates"], 122)
        self.assertEqual(
            rep_dry.status, "VERIFIED_ALL_122_GATES_DRY_RUN_SIMULATED_BACKUP"
        )

    def test_68_fx3_clean_room_test_and_force_clean_room_env_in_master_122(self) -> None:
        for env_key in (ENV_CLEAN_ROOM_TEST_PHASE288, "FX3_FX6_FORCE_CLEAN_ROOM"):
            with mock.patch.dict(os.environ, {env_key: "1"}):
                self.assertTrue(_is_forced_clean_room())
                rep = evaluate_122gate_preflight(
                    master_120_override=self.clean_offline_120,
                )
                self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
                self.assertTrue(rep.clean_room_forced)

    def test_69_master_122_blocks_core_g01_g09_missing(self) -> None:
        broken_gates = list(self.clean_offline_120.gates)
        broken_gates[0] = dict(broken_gates[0], passed=False)
        broken_120 = dataclasses.replace(
            self.clean_offline_120, gates=tuple(broken_gates)
        )
        rep = evaluate_122gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=False,
            master_120_override=broken_120,
        )
        self.assertEqual(rep.status, "BLOCKED_BY_CORE_G01_G09_REFERENCE_MISSING")
        self.assertFalse(rep.offline_119_gates_verified)

    def test_70_master_122_embeds_master_120_g121_and_g122_dicts(self) -> None:
        rep = evaluate_122gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=False,
            master_120_override=self.clean_offline_120,
        )
        self.assertEqual(rep.master_120_report["summary"]["total_gates"], 120)
        self.assertEqual(rep.g121_result["status"], STATUS_VERIFIED_G121)
        self.assertEqual(rep.g122_result["status"], STATUS_VERIFIED_G122)

    # --- 5. CLI & Cross-Platform CI Portability Tests (Tests 71-80) ---

    def test_71_cli_verify_g121_text_and_json(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cli_main(["verify-dci4k-and-aspect-ratio-guard", "--force-clean-room"])
        self.assertEqual(rc, 0)
        self.assertIn("gate=G121_", buf.getvalue())
        self.assertIn("4096x2160@23.98p", buf.getvalue())
        self.assertIn("fx6_still_aspect=False", buf.getvalue())

        jbuf = io.StringIO()
        with contextlib.redirect_stdout(jbuf):
            rc_j = cli_main(
                ["verify-g121-dci4k-aspect-ratio", "--force-clean-room", "--json"]
            )
        self.assertEqual(rc_j, 0)
        data = json.loads(jbuf.getvalue())
        self.assertTrue(data["valid"])
        self.assertEqual(data["status"], STATUS_VERIFIED_G121)

    def test_72_cli_verify_g122_text_and_json(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cli_main(
                ["verify-custom-hold-camset-photo-capture-guard", "--force-clean-room"]
            )
        self.assertEqual(rc, 0)
        self.assertIn("gate=G122_", buf.getvalue())
        self.assertIn("hold_keys=11", buf.getvalue())
        self.assertIn("fx6_photo=False", buf.getvalue())

        jbuf = io.StringIO()
        with contextlib.redirect_stdout(jbuf):
            rc_j = cli_main(
                [
                    "verify-g122-custom-hold-camset-photo-capture",
                    "--force-clean-room",
                    "--json",
                ]
            )
        self.assertEqual(rc_j, 0)
        data = json.loads(jbuf.getvalue())
        self.assertTrue(data["valid"])
        self.assertEqual(data["status"], STATUS_VERIFIED_G122)

    def test_73_cli_verify_122_gates_offline_text_and_json(self) -> None:
        offline_122 = evaluate_122gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=False,
            master_120_override=self.clean_offline_120,
        )
        with mock.patch(
            "fx3_safety.__main__.evaluate_122gate_preflight",
            return_value=offline_122,
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = cli_main(["verify-122-gates", "--force-clean-room"])
            self.assertEqual(rc, 0)
            self.assertIn("verified=119/122", buf.getvalue())
            self.assertIn("overall_ready_for_hardware_attach=False", buf.getvalue())

            jbuf = io.StringIO()
            with contextlib.redirect_stdout(jbuf):
                rc_j = cli_main(["verify-122-gates", "--force-clean-room", "--json"])
            self.assertEqual(rc_j, 0)
            parsed = json.loads(jbuf.getvalue())
            self.assertEqual(parsed["summary"]["verified_gates"], 119)
            self.assertTrue(parsed["offline_119_gates_verified"])

    def test_74_cli_verify_122_gates_dry_run_text_and_json(self) -> None:
        dryrun_122 = evaluate_122gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            master_120_override=self.clean_dryrun_120,
        )
        with mock.patch(
            "fx3_safety.__main__.evaluate_122gate_preflight",
            return_value=dryrun_122,
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = cli_main(
                    ["verify-122-gates", "--force-clean-room", "--simulate-bench-dry-run"]
                )
            self.assertEqual(rc, 0)
            self.assertIn("verified=122/122", buf.getvalue())

            jbuf = io.StringIO()
            with contextlib.redirect_stdout(jbuf):
                rc_j = cli_main(
                    [
                        "verify-122-gates",
                        "--force-clean-room",
                        "--simulate-bench-dry-run",
                        "--json",
                    ]
                )
            self.assertEqual(rc_j, 0)
            parsed = json.loads(jbuf.getvalue())
            self.assertTrue(parsed["all_122_gates_verified"])
            self.assertEqual(parsed["summary"]["verified_gates"], 122)

    def test_75_standalone_module_main_offline_and_dry_run(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = module_main(["--force-clean-room"])
        self.assertEqual(rc, 0)
        self.assertIn("verified=119/122", buf.getvalue())

        jbuf = io.StringIO()
        with contextlib.redirect_stdout(jbuf):
            rc_j = module_main(
                ["--force-clean-room", "--simulate-bench-dry-run", "--json"]
            )
        self.assertEqual(rc_j, 0)
        self.assertTrue(json.loads(jbuf.getvalue())["all_122_gates_verified"])

    def test_76_subprocess_cli_verify_g121_g122_uses_sys_executable(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONPATH"] = str(DEFAULT_REPO_ROOT / "outputs" / "fx3-safety")
        for cmd, expected_status in (
            ("verify-dci4k-and-aspect-ratio-guard", STATUS_VERIFIED_G121),
            ("verify-custom-hold-camset-photo-capture-guard", STATUS_VERIFIED_G122),
        ):
            proc = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    "-m",
                    "fx3_safety",
                    cmd,
                    "--force-clean-room",
                    "--json",
                ],
                cwd=str(DEFAULT_REPO_ROOT),
                env=env,
                capture_output=True,
                text=True,
                timeout=_subprocess_timeout_seconds(),
                check=False,
            )
            self.assertEqual(proc.returncode, 0, msg=proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertTrue(payload["valid"])
            self.assertEqual(payload["status"], expected_status)

    def test_77_subprocess_cli_verify_122_gates_dry_run_uses_sys_executable(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONPATH"] = str(DEFAULT_REPO_ROOT / "outputs" / "fx3-safety")
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "fx3_safety",
                "verify-122-gates",
                "--force-clean-room",
                "--simulate-bench-dry-run",
                "--json",
            ],
            cwd=str(DEFAULT_REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=_subprocess_timeout_seconds(),
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertTrue(payload["all_122_gates_verified"])
        self.assertEqual(payload["summary"]["verified_gates"], 122)
        self.assertEqual(payload["raw_firmware_bytes_leaked"], 0)

    def test_78_subprocess_cli_verify_122_gates_offline_uses_sys_executable(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONPATH"] = str(DEFAULT_REPO_ROOT / "outputs" / "fx3-safety")
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "fx3_safety",
                "verify-122-gates",
                "--force-clean-room",
                "--json",
            ],
            cwd=str(DEFAULT_REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=_subprocess_timeout_seconds(),
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertTrue(payload["offline_119_gates_verified"])
        self.assertFalse(payload["all_122_gates_verified"])
        self.assertEqual(payload["summary"]["verified_gates"], 119)

    def test_79_argparse_help_escaped_percent_portability_on_python314(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONPATH"] = str(DEFAULT_REPO_ROOT / "outputs" / "fx3-safety")
        for subcmd in (
            "verify-dci4k-and-aspect-ratio-guard",
            "verify-custom-hold-camset-photo-capture-guard",
            "verify-122-gates",
        ):
            proc = subprocess.run(
                [sys.executable, "-B", "-m", "fx3_safety", subcmd, "--help"],
                cwd=str(DEFAULT_REPO_ROOT),
                env=env,
                capture_output=True,
                text=True,
                timeout=_subprocess_timeout_seconds(),
                check=False,
            )
            self.assertEqual(proc.returncode, 0, msg=f"{subcmd}: {proc.stderr}")

        proc_top = subprocess.run(
            [sys.executable, "-B", "-m", "fx3_safety", "--help"],
            cwd=str(DEFAULT_REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=_subprocess_timeout_seconds(),
            check=False,
        )
        self.assertEqual(proc_top.returncode, 0, msg=proc_top.stderr)

        proc_mod = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "fx3_safety.realhw_dci4k_aspect_custom_hold_camset_photo_capture_and_122gate_guard",
                "--help",
            ],
            cwd=str(DEFAULT_REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=_subprocess_timeout_seconds(),
            check=False,
        )
        self.assertEqual(proc_mod.returncode, 0, msg=proc_mod.stderr)

    def test_80_upstream_verify_120_gates_backward_compatible(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONPATH"] = str(DEFAULT_REPO_ROOT / "outputs" / "fx3-safety")
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "fx3_safety",
                "verify-120-gates",
                "--force-clean-room",
                "--json",
            ],
            cwd=str(DEFAULT_REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=_subprocess_timeout_seconds(),
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertTrue(payload["offline_117_gates_verified"])
        self.assertEqual(payload["summary"]["verified_gates"], 117)


if __name__ == "__main__":
    unittest.main()
