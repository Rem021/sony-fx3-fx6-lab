"""Phase 347 (Task H432, Wave-65, 150/150 Safety Gates Milestone):
Four-Mode Unit Tests (98 tests) for
`fx3_safety.realhw_zoom_ciz_autoslow_iso_arw_rawcomp_usblun_uvc_and_150gate_guard`:

- Gate `G149` (`ZOOM_CIZ_DIGITAL_8STEP_SPEED_RESET_SPLIT_AND_AUTOSLOW_DUAL_BASE_ISO_GUARD`):
  - `Shooting -> [Zoom]` + `Setup -> [Zoom Ring Rotate]` Reset split (`[Zoom Range]`
    & `[Zoom Ring Rotate]` Reset-immune; `[Zoom Lever Speed]` `1st=3`/`2nd=8 Fast`,
    `[Custom Key Z. Speed]` `1..8` def `3`, `[Remote Zoom Speed]` `Variable`/`Fixed 3`
    Resettable), Movie `1.5x` 4K / `2.0x` HD CIZ / `4.0x` Digital & Still 3:2 FF/APS-C
    scales (`8.0x` Still `S`), pre-entry & active lockouts, vs `FX6` zero Digital Zoom
    + `Handle Zoom`.
  - Movie-only `[Auto Slow Shutter]` (`7` lock conditions), Reset-immune `[ISO Range
    Limit]` (manual ISO only), Still-only `[ISO AUTO Min. SS]` (`P/A + ISO AUTO`,
    `1/250 s` flash override, `0` FX6 exposure), and Dual Base ISO (`[Base ISO]`
    `800/12800` visible ONLY in `Cine EI`/`Cine EI Quick`, `20x` per-Gamma switching).
- Gate `G150` (`STILL_ARW_DORMANT_LOSSLESS_HLG_PHOTO_AND_USB_LUN_SINGLE_SLOT1_NPFZ100_UVC_FIREWALL`):
  - Still `[RAW File Type]` strictly `Compressed`/`Uncompressed` (`14-bit .ARW`) vs
    100% dormant `Lossless Comp (L/M/S)` (`EOPNOTSUPP=95`), `[HLG Still Image]`
    (`STILL_HLD_PHOTO_{OFF,ON}`, `HEIF` + `P/A/S/M`, `BT.2100`, ISO floor `100/125`),
    `[Sort Recording]` + `[Auto Switch Media]` `Slot-1` `EROFS=30`.
  - `[USB Connection Mode]` 4 Reset-immune modes, **`[USB LUN Setting] = Single`
    (`_f 0x776d`) exposes ONLY `Slot 1` (does NOT hide `Slot 1`!)** + `MTP`
    targets `Slot 1` + macOS `Spotlight`/`fseventsd`/`fsck_exfat` MSC firewall.
  - `[USB Power Supply]` (`On` def, Type-C only, `NP-FZ100` PD boot gate vs `DC-C1`
    `>=65W PD` + `5A e-Marked` vs `FX6` `19.5V DC IN`), plus Dual `FX3`/`FX6`
    native `UVC` myth-busting (`EOPNOTSUPP=95`) & `[Movie Rec During Streaming]`.
- Unified `150`-Gate Master Preflight (`evaluate_150gate_preflight` / `verify-150-gates`):
  `147/150` offline, `150/150` `--simulate-bench-dry-run`, backward-compatible across
  `verify-58-gates` .. `verify-148-gates`, auto-discovered by `milestone324` & `311`.
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

import fx3_safety
from fx3_safety.__main__ import main as cli_main
from fx3_safety.realhw_breathing_camid_copyright_powersave_ntscpal_and_148gate_guard import (
    evaluate_148gate_preflight,
)
from fx3_safety.realhw_hdmi_raw_desqueeze_reclamp_varshutter_apsc_and_146gate_guard import (
    evaluate_146gate_preflight,
)
from fx3_safety.realhw_shoe_audio_4ch_subject_recog_silent_bodydata_and_144gate_guard import (
    evaluate_144gate_preflight,
)
from fx3_safety.realhw_zoom_ciz_autoslow_iso_arw_rawcomp_usblun_uvc_and_150gate_guard import (
    ALLOWED_EXPOSURE_MODES_G149,
    ALLOWED_GAMMA_CURVES_G149,
    ALLOWED_JH_SWITCH_MODES_G150,
    ALLOWED_RAW_FILE_TYPES_G150,
    ALLOWED_USB_LUN_SETTINGS_G150,
    ALLOWED_ZOOM_RANGES_G149,
    AUTO_SLOW_SHUTTER_DEFAULT_G149,
    AUTO_SLOW_SHUTTER_F_RESID16_G149,
    AUTO_SLOW_SHUTTER_RESETTABLE_BY_CAMSET_RESET_G149,
    BASE_ISO_DEFAULT_G149,
    BASE_ISO_F_RESID16_G149,
    BASE_ISO_HIGH_G149,
    BASE_ISO_LOW_G149,
    CROSS_MODEL_FLASH_AUTHORIZED,
    CUSTOM_KEY_ZOOM_SPEED_DEFAULT_G149,
    CUSTOM_KEY_ZOOM_SPEED_RESETTABLE_BY_CAMSET_RESET_G149,
    DONOR_CHECK_CI_MAX_SECONDS_PHASE347,
    DONOR_CHECK_MAX_SECONDS_PHASE347,
    DORMANT_LIVE_STREAM_USB_F_RESID16_G150,
    DORMANT_LOSSLESS_COMP_F_RESID16S_G150,
    DORMANT_RAW_FILE_TYPES_G150,
    DORMANT_USB_STREAMING_G_RESID16_G150,
    DORMANT_USB_STREAMING_MODE_NAMES_G150,
    DUAL_BASE_ISO_GAMMA_MAP_G149,
    EINVAL_ERRNO_PHASE347,
    EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
    EMMC_WRITES_AUTHORIZED,
    ENV_CLEAN_ROOM_TEST_PHASE347,
    ENV_FORCE_CLEAN_ROOM,
    EOPNOTSUPP_ERRNO_PHASE347,
    EROFS_ERRNO_PHASE347,
    EXACT_4_USB_CONNECTION_MODES_G150,
    EXPOSURE_MODE_A_G149,
    EXPOSURE_MODE_FLEXIBLE_G149,
    EXPOSURE_MODE_IAUTO_G149,
    EXPOSURE_MODE_M_G149,
    EXPOSURE_MODE_P_G149,
    EXPOSURE_MODE_S_G149,
    FX3_DEFAULT_FW_VERSION_PHASE347,
    FX3_HELP_GUIDE_CODE_PHASE347,
    FX3_MODEL_ID_PHASE347,
    FX3_MODEL_NAME_PHASE347,
    G149,
    G149_GATE_CODE,
    G150,
    G150_GATE_CODE,
    HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
    HDMI_REC_MEDIA_OFF_HDMI_ONLY_G150,
    HDMI_REC_MEDIA_ON_G150,
    HLG_STILL_COLOR_SPACE_G150,
    HLG_STILL_IMAGE_ELF_TYPO_SYMBOLS_G150,
    HLG_STILL_IMAGE_F_RESID16_G150,
    HLG_STILL_ISO_FLOOR_G150,
    HUMAN_HARDWARE_ATTACH_TOKEN,
    ISO_AUTO_MIN_SS_DEFAULT_G149,
    ISO_AUTO_MIN_SS_FLASH_OVERRIDE_G149,
    ISO_AUTO_MIN_SS_F_RESID16_G149,
    ISO_RANGE_LIMIT_F_RESID16_G149,
    ISO_RANGE_LIMIT_RESETTABLE_BY_CAMSET_RESET_G149,
    JH_SWITCH_HEIF_420_G150,
    JH_SWITCH_HEIF_422_G150,
    JH_SWITCH_JPEG_G150,
    LOG_SHOOTING_CINE_EI_G149,
    LOG_SHOOTING_CINE_EI_QUICK_G149,
    LOG_SHOOTING_FLEXIBLE_ISO_G149,
    LOG_SHOOTING_OFF_G149,
    MACOS_MSC_POLLUTION_DAEMONS_G150,
    MEDIA_SLOT_1_PHASE347,
    MEDIA_SLOT_2_PHASE347,
    MOVIE_CIZ_4K_SCALE_G149,
    MOVIE_CIZ_HD_SCALE_G149,
    MOVIE_DIGITAL_ZOOM_SCALE_G149,
    MOVIE_REC_DURING_STREAMING_DEFAULT_G150,
    MOVIE_REC_DURING_STREAMING_F_RESID16_G150,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED,
    PHYSICAL_USB_PACKETS_EMITTED,
    PINNED_PHASE347_DONOR_SPECS,
    RAW_FILE_TYPE_COMPRESSED_G150,
    RAW_FILE_TYPE_F_RESID16_G150,
    RAW_FILE_TYPE_UNCOMPRESSED_G150,
    RAW_FIRMWARE_BYTES_LEAKED,
    REALHW_150GATE_PREFLIGHT_SCHEMA,
    REC_MEDIA_DUR_HDMI_OUTPUT_F_RESID16_G150,
    REC_MEDIA_SIMULT_G150,
    REC_MEDIA_SLOT1_G150,
    REC_MEDIA_SLOT2_G150,
    REC_MEDIA_SORT_G150,
    REMOTE_ZOOM_FIXED_SPEED_DEFAULT_G149,
    REMOTE_ZOOM_SPEED_RESETTABLE_BY_CAMSET_RESET_G149,
    REMOTE_ZOOM_SPEED_TYPE_FIXED_G149,
    REMOTE_ZOOM_SPEED_TYPE_VARIABLE_G149,
    RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE347,
    RESET_ACTION_INITIALIZE_PHASE347,
    RESET_ACTION_NONE_PHASE347,
    SHOOT_MODE_MOVIE_PHASE347,
    SHOOT_MODE_SQ_PHASE347,
    SHOOT_MODE_STILL_PHASE347,
    SHUTTER_MODE_ANGLE_G149,
    SHUTTER_MODE_SPEED_G149,
    SORT_RECORDING_F_RESID16_G150,
    SPI_NOR_WRITE_AUTHORIZED,
    STATUS_BLOCKED_G149_AUTOSLOW_ISO_MINSS_OR_DUAL_BASE_ISO_VIOLATION,
    STATUS_BLOCKED_G149_FX6_DIGITAL_ZOOM_OR_MIN_SS_EOPNOTSUPP,
    STATUS_BLOCKED_G149_TELEMETRY_INVALID,
    STATUS_BLOCKED_G149_ZOOM_RESET_SPLIT_OR_LOCKOUT_VIOLATION,
    STATUS_BLOCKED_G150_DORMANT_LOSSLESS_RAW_OR_UVC_STREAMING_EOPNOTSUPP,
    STATUS_BLOCKED_G150_HLG_STILL_USB_LUN_OR_NPFZ100_PD_VIOLATION,
    STATUS_BLOCKED_G150_SLOT1_SORT_USB_MSC_STREAM_VAULT_EROFS,
    STATUS_BLOCKED_G150_TELEMETRY_INVALID,
    STATUS_BLOCKED_PHASE347_DONOR_INTEGRITY,
    STATUS_BLOCKED_PERSISTENT_EMMC_WRITE,
    STATUS_VERIFIED_G149,
    STATUS_VERIFIED_G150,
    STATUS_VERIFIED_SAFE,
    STILL_FMT_HEIF_G150,
    STILL_FMT_JPEG_G150,
    STILL_FMT_RAW_G150,
    STILL_FMT_RAW_HEIF_G150,
    STILL_FMT_RAW_JPEG_G150,
    USB_CONN_MSC_G150,
    USB_CONN_MTP_G150,
    USB_CONN_REMOTE_SHOOTING_G150,
    USB_CONN_SEL_WHEN_CONNECT_G150,
    USB_LUN_MULTI_G150,
    USB_LUN_SETTING_F_RESID16_G150,
    USB_LUN_SINGLE_F_RESID16_G150,
    USB_LUN_SINGLE_G150,
    USB_PACKETS_TRANSMITTED,
    USB_POWER_PORT_MULTI_MICRO_G150,
    USB_POWER_PORT_TYPE_C_G150,
    USB_POWER_SUPPLY_F_RESID16_G150,
    USB_SETUP_RESETTABLE_BY_CAMSET_RESET_G150,
    ZOOM_LEVER_1ST_DEFAULT_G149,
    ZOOM_LEVER_2ND_DEFAULT_G149,
    ZOOM_LEVER_SPEED_RESETTABLE_BY_CAMSET_RESET_G149,
    ZOOM_RANGE_CIZ_G149,
    ZOOM_RANGE_DEFAULT_G149,
    ZOOM_RANGE_DIGITAL_G149,
    ZOOM_RANGE_F_RESID16_G149,
    ZOOM_RANGE_OPTICAL_ONLY_G149,
    ZOOM_RANGE_RESETTABLE_BY_CAMSET_RESET_G149,
    ZOOM_RING_ROTATE_DEFAULT_G149,
    ZOOM_RING_ROTATE_F_RESID16_G149,
    ZOOM_RING_ROTATE_RESETTABLE_BY_CAMSET_RESET_G149,
    ZOOM_RING_ROTATE_RIGHT_LEFT_G149,
    audit_phase347_donor_contracts,
    compute_still_arw_hlg_usblun_uvc_matrix,
    compute_zoom_ciz_autoslow_baseiso_matrix,
    evaluate_150_master_safety_gates,
    evaluate_150gate_preflight,
    evaluate_g149_zoom_ciz_digital_8step_speed_reset_split_and_autoslow_dual_base_iso_guard,
    evaluate_g150_still_arw_dormant_lossless_hlg_photo_and_usb_lun_single_slot1_npfz100_uvc_firewall,
    resolve_fx3_still_arw_hlg_usblun_uvc_state,
    resolve_fx3_zoom_ciz_autoslow_baseiso_state,
    run_150_gate_preflight,
    strip_elapsed_seconds_recursive_phase347,
    verify_still_arw_hlg_usblun_uvc_guard,
    verify_zoom_ciz_autoslow_iso_baseiso_guard,
)
from fx3_safety.thermal_pwm_and_power_guard import (
    DEFAULT_REPO_ROOT,
    DonorThermalPowerPaths,
    resolve_donor_thermal_power_paths,
)


def _donor_exists() -> bool:
    wr = resolve_donor_thermal_power_paths(repo_root=DEFAULT_REPO_ROOT).work_root
    if wr is None:
        return False
    return all((wr / spec[1]).is_file() for spec in PINNED_PHASE347_DONOR_SPECS.values())


def _fake_donorless_paths(*_args: object, **_kwargs: object) -> DonorThermalPowerPaths:
    base = DEFAULT_REPO_ROOT / "__clean_room_no_donor__"
    return DonorThermalPowerPaths(
        work_root=None,
        fx3_lib_dir=base / "fx3_lib",
        fx3_appfw_path=base / "fx3_appfw",
        fx3_cp_path=base / "fx3_cp",
        fx3_bk4_path=base / "fx3_bk4",
        fx6_lib_dir=base / "fx6_lib",
        fx6_bk4_path=base / "fx6_bk4",
        fx6_cp_path=base / "fx6_cp",
    )


class TestPhase347Milestone150SafetyGates(unittest.TestCase):
    # -----------------------------------------------------------------------
    # 01..10: Four-Mode Donor Integrity & Timing / Leak Audit
    # -----------------------------------------------------------------------

    def test_01_donor_audit_normal_local_or_ci_fallback(self) -> None:
        env_clean = {
            k: v
            for k, v in os.environ.items()
            if k not in (ENV_FORCE_CLEAN_ROOM, ENV_CLEAN_ROOM_TEST_PHASE347)
        }
        with mock.patch.dict(os.environ, env_clean, clear=True):
            audit = audit_phase347_donor_contracts(repo_root=DEFAULT_REPO_ROOT)
            self.assertTrue(audit.valid)
            self.assertEqual(audit.status, STATUS_VERIFIED_SAFE)
            self.assertEqual(audit.raw_firmware_bytes_leaked, 0)
            self.assertTrue(audit.within_budget_200ms)
            self.assertLessEqual(audit.elapsed_seconds, DONOR_CHECK_MAX_SECONDS_PHASE347)
            if _donor_exists():
                self.assertEqual(audit.verification_mode, "LOCAL_DONOR_O_RDONLY")
                self.assertEqual(audit.access_mode, "STRICT_OS_O_RDONLY_PREAD")
                self.assertEqual(audit.files_inspected, len(PINNED_PHASE347_DONOR_SPECS))
            else:
                self.assertEqual(audit.verification_mode, "CLEAN_ROOM_SYNTHETIC")
                self.assertEqual(audit.files_inspected, 0)

    def test_02_donor_audit_env_fx3_clean_room_test(self) -> None:
        with mock.patch.dict(os.environ, {ENV_CLEAN_ROOM_TEST_PHASE347: "1"}):
            audit = audit_phase347_donor_contracts(repo_root=DEFAULT_REPO_ROOT)
            self.assertTrue(audit.valid)
            self.assertEqual(audit.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertEqual(audit.access_mode, "SYNTHETIC_NO_DONOR_DISK_IO")
            self.assertEqual(audit.files_inspected, 0)
            self.assertEqual(audit.raw_firmware_bytes_leaked, 0)
            self.assertLessEqual(audit.elapsed_seconds, DONOR_CHECK_CI_MAX_SECONDS_PHASE347)

    def test_03_donor_audit_env_fx3_fx6_force_clean_room(self) -> None:
        with mock.patch.dict(os.environ, {ENV_FORCE_CLEAN_ROOM: "1"}):
            audit = audit_phase347_donor_contracts(repo_root=DEFAULT_REPO_ROOT)
            self.assertTrue(audit.valid)
            self.assertEqual(audit.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertEqual(audit.files_inspected, 0)
            self.assertEqual(audit.raw_firmware_bytes_leaked, 0)

    def test_04_donor_audit_mocked_donorless_work_root_none(self) -> None:
        env_clean = {
            k: v
            for k, v in os.environ.items()
            if k not in (ENV_FORCE_CLEAN_ROOM, ENV_CLEAN_ROOM_TEST_PHASE347)
        }
        with mock.patch.dict(os.environ, env_clean, clear=True):
            with mock.patch(
                "fx3_safety.realhw_zoom_ciz_autoslow_iso_arw_rawcomp_usblun_uvc_and_150gate_guard.resolve_donor_thermal_power_paths",
                side_effect=_fake_donorless_paths,
            ):
                audit = audit_phase347_donor_contracts(repo_root=DEFAULT_REPO_ROOT)
                self.assertTrue(audit.valid)
                self.assertEqual(audit.verification_mode, "CLEAN_ROOM_SYNTHETIC")
                self.assertEqual(audit.access_mode, "SYNTHETIC_ABSENT_DONOR_FALLBACK")
                self.assertEqual(audit.files_inspected, 0)
                self.assertEqual(audit.raw_firmware_bytes_leaked, 0)

    def test_05_donor_audit_fail_closed_on_missing_override(self) -> None:
        env_clean = {
            k: v
            for k, v in os.environ.items()
            if k not in (ENV_FORCE_CLEAN_ROOM, ENV_CLEAN_ROOM_TEST_PHASE347)
        }
        with mock.patch.dict(os.environ, env_clean, clear=True):
            bad = {
                "missing_slice": (
                    "FX3",
                    "nonexistent/wave65/missing.bin",
                    123,
                    "0" * 64,
                    (b"XYZ",),
                    "Missing test binary",
                )
            }
            audit = audit_phase347_donor_contracts(
                repo_root=DEFAULT_REPO_ROOT,
                work_root=DEFAULT_REPO_ROOT,
                donor_specs_override=bad,
            )
            self.assertFalse(audit.valid)
            self.assertEqual(audit.status, STATUS_BLOCKED_PHASE347_DONOR_INTEGRITY)

    def test_06_donor_audit_contains_kmod_and_4lang_uxc_specs(self) -> None:
        for key in (
            "fx3_appfw_so",
            "fx3_bk4_bin",
            "fx3_usbg_storage_ko",
            "fx3_usbg_stillimage_ko",
            "fx3_usb_f_uvc_ko",
            "fx3_g_webcam_ko",
            "fx3_string_english_f_uxc",
            "fx3_string_simplifiedchinese_f_uxc",
            "fx3_string_traditionalchinese_f_uxc",
            "fx3_string_japanese_f_uxc",
            "fx6_appfw_so",
            "fx6_usbg_storage_ko",
            "fx6_usb_f_uvc_ko",
            "fx6_string_english_uxc",
            "fx6_string_english_2_uxc",
        ):
            self.assertIn(key, PINNED_PHASE347_DONOR_SPECS)

    def test_07_uxc_resid16_constants_pinned(self) -> None:
        self.assertEqual(ZOOM_RANGE_F_RESID16_G149, 0x7164)
        self.assertEqual(ZOOM_RING_ROTATE_F_RESID16_G149, 0x6BE7)
        self.assertEqual(AUTO_SLOW_SHUTTER_F_RESID16_G149, 0x76EE)
        self.assertEqual(ISO_RANGE_LIMIT_F_RESID16_G149, 0x69CB)
        self.assertEqual(ISO_AUTO_MIN_SS_F_RESID16_G149, 0x778B)
        self.assertEqual(BASE_ISO_F_RESID16_G149, 0x78CE)
        self.assertEqual(RAW_FILE_TYPE_F_RESID16_G150, 0x6FF2)
        self.assertEqual(DORMANT_LOSSLESS_COMP_F_RESID16S_G150, (0x6B56, 0x7897, 0x6BFD, 0x7894))
        self.assertEqual(HLG_STILL_IMAGE_F_RESID16_G150, 0x76C8)
        self.assertEqual(SORT_RECORDING_F_RESID16_G150, 0x7916)
        self.assertEqual(USB_LUN_SETTING_F_RESID16_G150, 0x6B19)
        self.assertEqual(USB_LUN_SINGLE_F_RESID16_G150, 0x776D)
        self.assertEqual(USB_POWER_SUPPLY_F_RESID16_G150, 0x721E)
        self.assertEqual(DORMANT_LIVE_STREAM_USB_F_RESID16_G150, 0x6216)
        self.assertEqual(DORMANT_USB_STREAMING_G_RESID16_G150, 0x63F7)
        self.assertEqual(MOVIE_REC_DURING_STREAMING_F_RESID16_G150, 0x79D5)
        self.assertEqual(REC_MEDIA_DUR_HDMI_OUTPUT_F_RESID16_G150, 0x6144)

    def test_08_redline_constants_hard_locked(self) -> None:
        self.assertFalse(EMMC_WRITES_AUTHORIZED)
        self.assertFalse(PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(CROSS_MODEL_FLASH_AUTHORIZED)
        self.assertFalse(HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        self.assertFalse(EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        self.assertFalse(SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(PERSISTENT_WRITE_RELEASE)
        self.assertFalse(PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED)
        self.assertFalse(HUMAN_HARDWARE_ATTACH_TOKEN)
        self.assertEqual(USB_PACKETS_TRANSMITTED, 0)
        self.assertEqual(PHYSICAL_USB_PACKETS_EMITTED, 0)
        self.assertEqual(RAW_FIRMWARE_BYTES_LEAKED, 0)

    def test_09_g149_evaluate_clean_room_vs_local(self) -> None:
        v_cr, r_cr = evaluate_g149_zoom_ciz_digital_8step_speed_reset_split_and_autoslow_dual_base_iso_guard(
            repo_root=DEFAULT_REPO_ROOT, force_clean_room=True
        )
        self.assertTrue(v_cr.passed)
        self.assertTrue(r_cr.valid)
        self.assertEqual(r_cr.verification_mode, "CLEAN_ROOM_SYNTHETIC")

        v_loc, r_loc = evaluate_g149_zoom_ciz_digital_8step_speed_reset_split_and_autoslow_dual_base_iso_guard(
            repo_root=DEFAULT_REPO_ROOT, force_clean_room=False
        )
        self.assertTrue(v_loc.passed)
        self.assertTrue(r_loc.valid)

    def test_10_g150_evaluate_clean_room_vs_local(self) -> None:
        v_cr, r_cr = evaluate_g150_still_arw_dormant_lossless_hlg_photo_and_usb_lun_single_slot1_npfz100_uvc_firewall(
            repo_root=DEFAULT_REPO_ROOT, force_clean_room=True
        )
        self.assertTrue(v_cr.passed)
        self.assertTrue(r_cr.valid)
        self.assertEqual(r_cr.verification_mode, "CLEAN_ROOM_SYNTHETIC")

        v_loc, r_loc = evaluate_g150_still_arw_dormant_lossless_hlg_photo_and_usb_lun_single_slot1_npfz100_uvc_firewall(
            repo_root=DEFAULT_REPO_ROOT, force_clean_room=False
        )
        self.assertTrue(v_loc.passed)
        self.assertTrue(r_loc.valid)

    # -----------------------------------------------------------------------
    # 11..35: Gate G149 — Zoom/CIZ/Digital/8-Step Reset Split + Auto Slow / ISO
    # -----------------------------------------------------------------------

    def test_11_g149_defaults_and_reset_split_constants(self) -> None:
        res = verify_zoom_ciz_autoslow_iso_baseiso_guard()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_VERIFIED_G149)
        self.assertEqual(res.effective_zoom_range, "Optical zoom only")
        self.assertEqual(res.effective_zoom_ring_rotate, "Left(W)/Right(T)")
        self.assertEqual(res.effective_zoom_lever_1st_speed, 3)
        self.assertEqual(res.effective_zoom_lever_2nd_speed, 8)
        self.assertEqual(res.effective_custom_key_zoom_speed, 3)
        self.assertEqual(res.effective_remote_zoom_speed_type, "Variable")
        self.assertEqual(res.effective_remote_zoom_fixed_speed, 3)
        self.assertFalse(res.zoom_range_and_ring_resettable_by_camset_reset)
        self.assertTrue(res.zoom_speeds_resettable_by_camset_reset)
        self.assertFalse(ZOOM_RANGE_RESETTABLE_BY_CAMSET_RESET_G149)
        self.assertFalse(ZOOM_RING_ROTATE_RESETTABLE_BY_CAMSET_RESET_G149)
        self.assertTrue(ZOOM_LEVER_SPEED_RESETTABLE_BY_CAMSET_RESET_G149)
        self.assertTrue(CUSTOM_KEY_ZOOM_SPEED_RESETTABLE_BY_CAMSET_RESET_G149)
        self.assertTrue(REMOTE_ZOOM_SPEED_RESETTABLE_BY_CAMSET_RESET_G149)

    def test_12_g149_camset_reset_preserves_zoom_range_and_ring_but_resets_speeds(self) -> None:
        st = resolve_fx3_zoom_ciz_autoslow_baseiso_state(
            zoom_range=ZOOM_RANGE_CIZ_G149,
            zoom_ring_rotate=ZOOM_RING_ROTATE_RIGHT_LEFT_G149,
            zoom_lever_1st_speed=7,
            zoom_lever_2nd_speed=2,
            custom_key_zoom_speed=6,
            remote_zoom_speed_type=REMOTE_ZOOM_SPEED_TYPE_FIXED_G149,
            remote_zoom_fixed_speed=8,
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE347,
        )
        self.assertEqual(st["effective_zoom_range"], ZOOM_RANGE_CIZ_G149)
        self.assertEqual(st["effective_zoom_ring_rotate"], ZOOM_RING_ROTATE_RIGHT_LEFT_G149)
        self.assertEqual(st["effective_zoom_lever_1st_speed"], ZOOM_LEVER_1ST_DEFAULT_G149)
        self.assertEqual(st["effective_zoom_lever_2nd_speed"], ZOOM_LEVER_2ND_DEFAULT_G149)
        self.assertEqual(st["effective_custom_key_zoom_speed"], CUSTOM_KEY_ZOOM_SPEED_DEFAULT_G149)
        self.assertEqual(st["effective_remote_zoom_speed_type"], REMOTE_ZOOM_SPEED_TYPE_VARIABLE_G149)
        self.assertEqual(st["effective_remote_zoom_fixed_speed"], REMOTE_ZOOM_FIXED_SPEED_DEFAULT_G149)

    def test_13_g149_initialize_resets_everything_including_zoom_range_and_ring(self) -> None:
        st = resolve_fx3_zoom_ciz_autoslow_baseiso_state(
            zoom_range=ZOOM_RANGE_DIGITAL_G149,
            zoom_ring_rotate=ZOOM_RING_ROTATE_RIGHT_LEFT_G149,
            zoom_lever_1st_speed=5,
            reset_action=RESET_ACTION_INITIALIZE_PHASE347,
        )
        self.assertEqual(st["effective_zoom_range"], ZOOM_RANGE_OPTICAL_ONLY_G149)
        self.assertEqual(st["effective_zoom_ring_rotate"], ZOOM_RING_ROTATE_DEFAULT_G149)
        self.assertEqual(st["effective_zoom_lever_1st_speed"], ZOOM_LEVER_1ST_DEFAULT_G149)

    def test_14_g149_rejects_claiming_camset_reset_clears_zoom_range_or_ring(self) -> None:
        res = verify_zoom_ciz_autoslow_iso_baseiso_guard(
            claimed_camset_reset_clears_zoom_range_or_ring=True
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.block_errno, EINVAL_ERRNO_PHASE347)
        self.assertEqual(res.status, STATUS_BLOCKED_G149_ZOOM_RESET_SPLIT_OR_LOCKOUT_VIOLATION)

    def test_15_g149_rejects_claiming_camset_reset_preserves_zoom_speeds(self) -> None:
        res = verify_zoom_ciz_autoslow_iso_baseiso_guard(
            claimed_camset_reset_preserves_zoom_speeds=True
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.block_errno, EINVAL_ERRNO_PHASE347)
        self.assertEqual(res.status, STATUS_BLOCKED_G149_ZOOM_RESET_SPLIT_OR_LOCKOUT_VIOLATION)

    def test_16_g149_movie_scales_4k_hd_ciz_and_digital(self) -> None:
        st_4k = resolve_fx3_zoom_ciz_autoslow_baseiso_state(
            shoot_mode=SHOOT_MODE_MOVIE_PHASE347, zoom_range=ZOOM_RANGE_CIZ_G149, movie_is_4k=True
        )
        self.assertEqual(st_4k["effective_max_zoom_scale"], MOVIE_CIZ_4K_SCALE_G149)
        st_hd = resolve_fx3_zoom_ciz_autoslow_baseiso_state(
            shoot_mode=SHOOT_MODE_MOVIE_PHASE347, zoom_range=ZOOM_RANGE_CIZ_G149, movie_is_4k=False
        )
        self.assertEqual(st_hd["effective_max_zoom_scale"], MOVIE_CIZ_HD_SCALE_G149)
        st_dig = resolve_fx3_zoom_ciz_autoslow_baseiso_state(
            shoot_mode=SHOOT_MODE_MOVIE_PHASE347, zoom_range=ZOOM_RANGE_DIGITAL_G149
        )
        self.assertEqual(st_dig["effective_max_zoom_scale"], MOVIE_DIGITAL_ZOOM_SCALE_G149)

    def test_17_g149_still_ff_and_apsc_scales(self) -> None:
        st_ff_s = resolve_fx3_zoom_ciz_autoslow_baseiso_state(
            shoot_mode=SHOOT_MODE_STILL_PHASE347,
            zoom_range=ZOOM_RANGE_DIGITAL_G149,
            still_file_format=STILL_FMT_JPEG_G150,
            still_image_size="S",
            apsc_s35_active=False,
        )
        self.assertEqual(st_ff_s["effective_max_zoom_scale"], 8.0)
        st_apsc_m = resolve_fx3_zoom_ciz_autoslow_baseiso_state(
            shoot_mode=SHOOT_MODE_STILL_PHASE347,
            zoom_range=ZOOM_RANGE_CIZ_G149,
            still_file_format=STILL_FMT_JPEG_G150,
            still_image_size="M",
            apsc_s35_active=True,
        )
        self.assertEqual(st_apsc_m["effective_max_zoom_scale"], 2.6)

    def test_18_g149_pre_entry_lockouts_raw_120p_sq100_hdmi_raw(self) -> None:
        for kw in (
            {"shoot_mode": SHOOT_MODE_STILL_PHASE347, "still_file_format": STILL_FMT_RAW_G150},
            {"shoot_mode": SHOOT_MODE_STILL_PHASE347, "still_file_format": STILL_FMT_RAW_JPEG_G150},
            {"shoot_mode": SHOOT_MODE_MOVIE_PHASE347, "movie_fps": 119.88},
            {"shoot_mode": SHOOT_MODE_SQ_PHASE347, "sq_fps": 100.0},
            {"shoot_mode": SHOOT_MODE_MOVIE_PHASE347, "hdmi_raw_output_on": True},
        ):
            res = verify_zoom_ciz_autoslow_iso_baseiso_guard(
                zoom_range=ZOOM_RANGE_CIZ_G149,
                claimed_non_optical_zoom_during_lockout_allowed=True,
                **kw,
            )
            self.assertFalse(res.valid)
            self.assertTrue(res.non_optical_zoom_pre_entry_locked)
            self.assertEqual(res.effective_zoom_range, ZOOM_RANGE_OPTICAL_ONLY_G149)

    def test_19_g149_active_lockouts_focus_area_metering_face_tracking(self) -> None:
        res_ok = verify_zoom_ciz_autoslow_iso_baseiso_guard(
            zoom_range=ZOOM_RANGE_CIZ_G149,
        )
        self.assertTrue(res_ok.valid)
        self.assertEqual(len(res_ok.non_optical_zoom_active_lockouts), 5)

        res_bad = verify_zoom_ciz_autoslow_iso_baseiso_guard(
            zoom_range=ZOOM_RANGE_DIGITAL_G149,
            claimed_focus_area_or_spot_metering_or_tracking_active_in_ciz=True,
        )
        self.assertFalse(res_bad.valid)
        self.assertEqual(res_bad.status, STATUS_BLOCKED_G149_ZOOM_RESET_SPLIT_OR_LOCKOUT_VIOLATION)

    def test_20_g149_smart_zoom_blocked_in_movie(self) -> None:
        res = verify_zoom_ciz_autoslow_iso_baseiso_guard(
            shoot_mode=SHOOT_MODE_MOVIE_PHASE347,
            claimed_smart_zoom_in_movie_allowed=True,
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.block_errno, EINVAL_ERRNO_PHASE347)

    def test_21_g149_fx6_digital_zoom_and_handle_zoom_eopnotsupp(self) -> None:
        r1 = verify_zoom_ciz_autoslow_iso_baseiso_guard(fx6_digital_zoom_requested=True)
        self.assertFalse(r1.valid)
        self.assertEqual(r1.block_errno, EOPNOTSUPP_ERRNO_PHASE347)
        self.assertEqual(r1.status, STATUS_BLOCKED_G149_FX6_DIGITAL_ZOOM_OR_MIN_SS_EOPNOTSUPP)
        self.assertTrue(r1.fx6_cross_model_spoof_rejected)

        r2 = verify_zoom_ciz_autoslow_iso_baseiso_guard(fx6_handle_zoom_or_min_ss_spoof_requested=True)
        self.assertFalse(r2.valid)
        self.assertEqual(r2.block_errno, EOPNOTSUPP_ERRNO_PHASE347)

    def test_22_g149_auto_slow_shutter_default_movie_only_and_resettable(self) -> None:
        self.assertEqual(AUTO_SLOW_SHUTTER_DEFAULT_G149, "On")
        self.assertTrue(AUTO_SLOW_SHUTTER_RESETTABLE_BY_CAMSET_RESET_G149)
        st = resolve_fx3_zoom_ciz_autoslow_baseiso_state(
            shoot_mode=SHOOT_MODE_MOVIE_PHASE347,
            auto_slow_shutter="Off",
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE347,
        )
        self.assertEqual(st["effective_auto_slow_shutter"], "On")

    def test_23_g149_auto_slow_shutter_7_lock_conditions(self) -> None:
        lock_cases = [
            {"shoot_mode": SHOOT_MODE_STILL_PHASE347},
            {"shoot_mode": SHOOT_MODE_SQ_PHASE347},
            {"exposure_mode": EXPOSURE_MODE_S_G149},
            {"exposure_mode": EXPOSURE_MODE_M_G149},
            {"iso_auto_selected": False},
            {"exposure_mode": EXPOSURE_MODE_FLEXIBLE_G149, "flexible_exp_shutter_manual": True},
            {"log_shooting_mode": LOG_SHOOTING_CINE_EI_G149},
            {"log_shooting_mode": LOG_SHOOTING_CINE_EI_QUICK_G149},
            {"shutter_mode": SHUTTER_MODE_ANGLE_G149},
        ]
        for kw in lock_cases:
            res = verify_zoom_ciz_autoslow_iso_baseiso_guard(
                claimed_auto_slow_shutter_active_under_lock=True,
                **kw,
            )
            self.assertFalse(res.valid)
            self.assertTrue(res.auto_slow_shutter_locked_disabled)
            self.assertEqual(
                res.status,
                STATUS_BLOCKED_G149_AUTOSLOW_ISO_MINSS_OR_DUAL_BASE_ISO_VIOLATION,
            )

    def test_24_g149_iso_range_limit_reset_immune_and_manual_iso_only(self) -> None:
        self.assertFalse(ISO_RANGE_LIMIT_RESETTABLE_BY_CAMSET_RESET_G149)
        r1 = verify_zoom_ciz_autoslow_iso_baseiso_guard(
            claimed_camset_reset_clears_iso_range_limit=True
        )
        self.assertFalse(r1.valid)
        r2 = verify_zoom_ciz_autoslow_iso_baseiso_guard(
            claimed_iso_range_limit_caps_iso_auto=True
        )
        self.assertFalse(r2.valid)

    def test_25_g149_iso_auto_min_ss_still_p_a_iso_auto_only_and_flash_override(self) -> None:
        st_ok = resolve_fx3_zoom_ciz_autoslow_baseiso_state(
            shoot_mode=SHOOT_MODE_STILL_PHASE347,
            exposure_mode=EXPOSURE_MODE_A_G149,
            iso_auto_selected=True,
            iso_auto_min_ss="SLOWER",
            flash_firing=True,
        )
        self.assertTrue(st_ok["iso_auto_min_ss_available"])
        self.assertEqual(st_ok["effective_iso_auto_min_ss"], "SLOWER")
        self.assertEqual(st_ok["effective_flash_iso_auto_min_ss"], ISO_AUTO_MIN_SS_FLASH_OVERRIDE_G149)

        for kw in (
            {"shoot_mode": SHOOT_MODE_MOVIE_PHASE347},
            {"shoot_mode": SHOOT_MODE_SQ_PHASE347},
            {"shoot_mode": SHOOT_MODE_STILL_PHASE347, "exposure_mode": EXPOSURE_MODE_M_G149},
            {"shoot_mode": SHOOT_MODE_STILL_PHASE347, "exposure_mode": EXPOSURE_MODE_P_G149, "iso_auto_selected": False},
        ):
            st_no = resolve_fx3_zoom_ciz_autoslow_baseiso_state(**kw)
            self.assertFalse(st_no["iso_auto_min_ss_available"])

    def test_26_g149_rejects_min_ss_in_movie_sq_or_flash_override_bypass(self) -> None:
        r1 = verify_zoom_ciz_autoslow_iso_baseiso_guard(
            shoot_mode=SHOOT_MODE_MOVIE_PHASE347,
            claimed_iso_auto_min_ss_active_in_movie_or_sq=True,
        )
        self.assertFalse(r1.valid)
        r2 = verify_zoom_ciz_autoslow_iso_baseiso_guard(
            shoot_mode=SHOOT_MODE_STILL_PHASE347,
            exposure_mode=EXPOSURE_MODE_P_G149,
            iso_auto_selected=True,
            flash_firing=True,
            claimed_flash_ignores_1_250_override=True,
        )
        self.assertFalse(r2.valid)

    def test_27_g149_dual_base_iso_cine_ei_only_visibility(self) -> None:
        for mode in (LOG_SHOOTING_CINE_EI_G149, LOG_SHOOTING_CINE_EI_QUICK_G149):
            res = verify_zoom_ciz_autoslow_iso_baseiso_guard(
                log_shooting_mode=mode,
                base_iso_cine_ei=BASE_ISO_HIGH_G149,
            )
            self.assertTrue(res.valid)
            self.assertTrue(res.base_iso_menu_visible)
            self.assertEqual(res.effective_low_base_iso, BASE_ISO_LOW_G149)
            self.assertEqual(res.effective_high_base_iso, BASE_ISO_HIGH_G149)

        for non_ei in (LOG_SHOOTING_OFF_G149, LOG_SHOOTING_FLEXIBLE_ISO_G149):
            res_bad = verify_zoom_ciz_autoslow_iso_baseiso_guard(
                log_shooting_mode=non_ei,
                claimed_base_iso_menu_visible_outside_cine_ei=True,
            )
            self.assertFalse(res_bad.valid)
            self.assertFalse(res_bad.base_iso_menu_visible)

    def test_28_g149_dual_base_iso_20x_per_gamma_switching(self) -> None:
        expected = {
            "S-Log3": (640, 12800),
            "S-Log2": (640, 12800),
            "S-Cinetone": (100, 2000),
            "HLG": (100, 2000),
            "HLG3": (100, 2000),
            "Cine4": (100, 2000),
            "HLG1": (50, 1000),
            "Cine2": (50, 1000),
            "Cine1": (64, 1280),
            "PP Off": (80, 1600),
            "HLG2": (80, 1600),
            "Cine3": (80, 1600),
        }
        for g_name, (low_i, high_i) in expected.items():
            res = verify_zoom_ciz_autoslow_iso_baseiso_guard(
                log_shooting_mode=LOG_SHOOTING_OFF_G149,
                gamma_curve=g_name,
            )
            self.assertTrue(res.valid)
            self.assertEqual((res.effective_low_base_iso, res.effective_high_base_iso), (low_i, high_i))
            self.assertEqual(high_i, low_i * 20)

    def test_29_g149_matrix_combinatorics(self) -> None:
        m = compute_zoom_ciz_autoslow_baseiso_matrix()
        self.assertEqual(m["total_matrix_states"], 288)
        self.assertGreater(m["reset_preserved_zoom_range_count"], 0)
        self.assertGreater(m["reset_restored_lever_speed_count"], 0)
        self.assertGreater(m["pre_entry_locked_count"], 0)
        self.assertGreater(m["active_lockouts_count"], 0)
        self.assertGreater(m["auto_slow_locked_count"], 0)
        self.assertGreater(m["min_ss_available_count"], 0)
        self.assertGreater(m["cine_ei_base_iso_visible_count"], 0)

    def test_30_g149_rejects_bool_speed_and_invalid_body_identity(self) -> None:
        r_bool = verify_zoom_ciz_autoslow_iso_baseiso_guard(
            zoom_lever_1st_speed=True,  # type: ignore[arg-type]
        )
        self.assertFalse(r_bool.valid)
        self.assertEqual(r_bool.status, STATUS_BLOCKED_G149_TELEMETRY_INVALID)

        r_out = verify_zoom_ciz_autoslow_iso_baseiso_guard(zoom_lever_2nd_speed=9)
        self.assertFalse(r_out.valid)
        self.assertEqual(r_out.status, STATUS_BLOCKED_G149_TELEMETRY_INVALID)

        r_model = verify_zoom_ciz_autoslow_iso_baseiso_guard(body_model_name="ILME-FX6")
        self.assertFalse(r_model.valid)
        self.assertEqual(r_model.status, STATUS_BLOCKED_G149_TELEMETRY_INVALID)

    def test_31_g149_rejects_invalid_enums(self) -> None:
        for kw in (
            {"shoot_mode": "Timelapse"},
            {"zoom_range": "HyperZoom"},
            {"zoom_ring_rotate": "Invert"},
            {"remote_zoom_speed_type": "Dynamic"},
            {"auto_slow_shutter": "Maybe"},
            {"exposure_mode": "AutoPlus"},
            {"log_shooting_mode": "SLogOnly"},
            {"shutter_mode": "Degrees"},
            {"base_iso_cine_ei": 400},
            {"gamma_curve": "V-Log"},
            {"reset_action": "FactoryWipe"},
        ):
            r = verify_zoom_ciz_autoslow_iso_baseiso_guard(**kw)  # type: ignore[arg-type]
            self.assertFalse(r.valid)
            self.assertEqual(r.status, STATUS_BLOCKED_G149_TELEMETRY_INVALID)

    def test_32_g149_remote_zoom_speed_reset_behavior(self) -> None:
        st = resolve_fx3_zoom_ciz_autoslow_baseiso_state(
            remote_zoom_speed_type=REMOTE_ZOOM_SPEED_TYPE_FIXED_G149,
            remote_zoom_fixed_speed=7,
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE347,
        )
        self.assertEqual(st["effective_remote_zoom_speed_type"], REMOTE_ZOOM_SPEED_TYPE_VARIABLE_G149)
        self.assertEqual(st["effective_remote_zoom_fixed_speed"], 3)

    def test_33_g149_flexible_iso_hides_base_iso_menu_and_uses_640_12800(self) -> None:
        res = verify_zoom_ciz_autoslow_iso_baseiso_guard(
            log_shooting_mode=LOG_SHOOTING_FLEXIBLE_ISO_G149,
            gamma_curve="S-Log3",
        )
        self.assertTrue(res.valid)
        self.assertFalse(res.base_iso_menu_visible)
        self.assertEqual(res.effective_low_base_iso, 640)
        self.assertEqual(res.effective_high_base_iso, 12800)

    def test_34_g149_all_allowed_constants_consistent(self) -> None:
        self.assertEqual(len(ALLOWED_ZOOM_RANGES_G149), 3)
        self.assertEqual(len(ALLOWED_EXPOSURE_MODES_G149), 6)
        self.assertGreaterEqual(len(ALLOWED_GAMMA_CURVES_G149), 15)
        self.assertEqual(len(DUAL_BASE_ISO_GAMMA_MAP_G149), len(ALLOWED_GAMMA_CURVES_G149))

    def test_35_g149_result_to_dict_serializable(self) -> None:
        res = verify_zoom_ciz_autoslow_iso_baseiso_guard()
        d = res.to_dict()
        self.assertEqual(json.loads(json.dumps(d))["status"], STATUS_VERIFIED_G149)

    # -----------------------------------------------------------------------
    # 36..62: Gate G150 — Still ARW Dormant Lossless, HLG Photo, Sort Rec,
    #                     USB LUN Single Trap, NP-FZ100 PD & Dual UVC
    # -----------------------------------------------------------------------

    def test_36_g150_defaults_safe_and_verified(self) -> None:
        res = verify_still_arw_hlg_usblun_uvc_guard()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_VERIFIED_G150)
        self.assertEqual(res.effective_raw_file_type, RAW_FILE_TYPE_COMPRESSED_G150)
        self.assertEqual(res.effective_jh_switch, JH_SWITCH_JPEG_G150)
        self.assertEqual(res.effective_still_file_format, STILL_FMT_JPEG_G150)
        self.assertEqual(res.effective_hlg_still_image, "Off")
        self.assertEqual(res.effective_usb_connection_mode, USB_CONN_SEL_WHEN_CONNECT_G150)
        self.assertEqual(res.effective_usb_lun_setting, USB_LUN_MULTI_G150)
        self.assertEqual(res.effective_usb_power_supply, "On")
        self.assertEqual(res.effective_movie_rec_during_streaming, "Disable")
        self.assertEqual(res.effective_hdmi_rec_media_mode, HDMI_REC_MEDIA_OFF_HDMI_ONLY_G150)
        self.assertEqual(res.slot1_data_sector_writes, 0)

    def test_37_g150_uncompressed_arw_allowed_and_resettable(self) -> None:
        res = verify_still_arw_hlg_usblun_uvc_guard(
            raw_file_type=RAW_FILE_TYPE_UNCOMPRESSED_G150,
            still_file_format=STILL_FMT_RAW_G150,
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.effective_raw_file_type, RAW_FILE_TYPE_UNCOMPRESSED_G150)

        st_rst = resolve_fx3_still_arw_hlg_usblun_uvc_state(
            raw_file_type=RAW_FILE_TYPE_UNCOMPRESSED_G150,
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE347,
        )
        self.assertEqual(st_rst["effective_raw_file_type"], RAW_FILE_TYPE_COMPRESSED_G150)

    def test_38_g150_dormant_lossless_comp_raw_rejected_eopnotsupp(self) -> None:
        for dormant in DORMANT_RAW_FILE_TYPES_G150:
            res = verify_still_arw_hlg_usblun_uvc_guard(raw_file_type=dormant)
            self.assertFalse(res.valid)
            self.assertTrue(res.dormant_lossless_raw_rejected)
            self.assertEqual(res.block_errno, EOPNOTSUPP_ERRNO_PHASE347)
            self.assertEqual(
                res.status,
                STATUS_BLOCKED_G150_DORMANT_LOSSLESS_RAW_OR_UVC_STREAMING_EOPNOTSUPP,
            )

        res_req = verify_still_arw_hlg_usblun_uvc_guard(
            requested_dormant_lossless_raw="Lossless Comp (L)"
        )
        self.assertFalse(res_req.valid)
        self.assertEqual(res_req.block_errno, EOPNOTSUPP_ERRNO_PHASE347)

    def test_39_g150_hlg_still_image_valid_bt2100_and_iso100_floor(self) -> None:
        self.assertEqual(
            HLG_STILL_IMAGE_ELF_TYPO_SYMBOLS_G150,
            ("STILL_HLD_PHOTO_OFF", "STILL_HLD_PHOTO_ON"),
        )
        for jh in (JH_SWITCH_HEIF_420_G150, JH_SWITCH_HEIF_422_G150):
            res = verify_still_arw_hlg_usblun_uvc_guard(
                jh_switch=jh,
                still_file_format=STILL_FMT_HEIF_G150,
                exposure_mode=EXPOSURE_MODE_M_G149,
                hlg_still_image="On",
            )
            self.assertTrue(res.valid)
            self.assertTrue(res.hlg_still_preconditions_met)
            self.assertEqual(res.effective_hlg_still_image, "On")
            self.assertEqual(res.effective_color_space, HLG_STILL_COLOR_SPACE_G150)
            self.assertGreaterEqual(res.effective_normal_iso_floor, HLG_STILL_ISO_FLOOR_G150)

    def test_40_g150_hlg_still_blocked_with_raw_jpeg_iauto_or_dro_bracket(self) -> None:
        for kw in (
            {"jh_switch": JH_SWITCH_JPEG_G150, "still_file_format": STILL_FMT_JPEG_G150},
            {"jh_switch": JH_SWITCH_HEIF_422_G150, "still_file_format": STILL_FMT_RAW_HEIF_G150},
            {"jh_switch": JH_SWITCH_HEIF_422_G150, "still_file_format": STILL_FMT_HEIF_G150, "exposure_mode": EXPOSURE_MODE_IAUTO_G149},
            {"jh_switch": JH_SWITCH_HEIF_422_G150, "still_file_format": STILL_FMT_HEIF_G150, "dro_bracket_or_iso_override": True},
        ):
            res = verify_still_arw_hlg_usblun_uvc_guard(
                hlg_still_image="On",
                claimed_hlg_still_allowed_with_raw_or_jpeg=True,
                **kw,
            )
            self.assertFalse(res.valid)
            self.assertFalse(res.hlg_still_preconditions_met)
            self.assertEqual(res.effective_hlg_still_image, "Off")
            self.assertEqual(res.block_errno, EINVAL_ERRNO_PHASE347)

    def test_41_g150_hlg_still_rejects_claiming_srgb_or_pp_stays_active(self) -> None:
        res = verify_still_arw_hlg_usblun_uvc_guard(
            jh_switch=JH_SWITCH_HEIF_420_G150,
            still_file_format=STILL_FMT_HEIF_G150,
            exposure_mode=EXPOSURE_MODE_P_G149,
            hlg_still_image="On",
            claimed_hlg_still_keeps_pp_or_creativelook_or_srgb=True,
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_G150_HLG_STILL_USB_LUN_OR_NPFZ100_PD_VIOLATION)

    def test_42_g150_sort_recording_auto_switch_spillover_slot1_erofs(self) -> None:
        res_warn_ok = verify_still_arw_hlg_usblun_uvc_guard(
            rec_media_mode=REC_MEDIA_SORT_G150,
            auto_switch_media="On",
            target_media_slot=MEDIA_SLOT_2_PHASE347,
        )
        self.assertTrue(res_warn_ok.valid)
        self.assertTrue(res_warn_ok.sort_recording_auto_switch_spillover_risk)

        res_erofs = verify_still_arw_hlg_usblun_uvc_guard(
            rec_media_mode=REC_MEDIA_SORT_G150,
            auto_switch_media="On",
            target_media_slot=MEDIA_SLOT_1_PHASE347,
            sort_or_still_write_requested=True,
        )
        self.assertFalse(res_erofs.valid)
        self.assertTrue(res_erofs.slot1_tier0_vault_firewall_blocked)
        self.assertEqual(res_erofs.block_errno, EROFS_ERRNO_PHASE347)
        self.assertEqual(res_erofs.slot1_data_sector_writes, 0)
        self.assertEqual(res_erofs.status, STATUS_BLOCKED_G150_SLOT1_SORT_USB_MSC_STREAM_VAULT_EROFS)

    def test_43_g150_usb_connection_exact_4_modes_and_reset_immune(self) -> None:
        self.assertEqual(
            EXACT_4_USB_CONNECTION_MODES_G150,
            ("Sel. When Connect", "MassStorage(MSC)", "MTP", "Remote Shooting"),
        )
        self.assertFalse(USB_SETUP_RESETTABLE_BY_CAMSET_RESET_G150)
        for mode in EXACT_4_USB_CONNECTION_MODES_G150:
            st = resolve_fx3_still_arw_hlg_usblun_uvc_state(
                usb_connection_mode=mode,
                usb_lun_setting=USB_LUN_SINGLE_G150,
                usb_power_supply="Off",
                reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE347,
            )
            self.assertEqual(st["effective_usb_connection_mode"], mode)
            self.assertEqual(st["effective_usb_lun_setting"], USB_LUN_SINGLE_G150)
            self.assertEqual(st["effective_usb_power_supply"], "Off")

    def test_44_g150_usb_lun_single_trap_exposes_slot1_only(self) -> None:
        res_ok = verify_still_arw_hlg_usblun_uvc_guard(
            usb_lun_setting=USB_LUN_SINGLE_G150,
            target_media_slot=MEDIA_SLOT_2_PHASE347,
        )
        self.assertTrue(res_ok.valid)
        self.assertTrue(res_ok.usb_lun_single_exposes_slot1_only)
        self.assertTrue(res_ok.host_msc_contamination_firewall_active)

        res_trap = verify_still_arw_hlg_usblun_uvc_guard(
            usb_lun_setting=USB_LUN_SINGLE_G150,
            claimed_usb_lun_single_hides_slot1=True,
        )
        self.assertFalse(res_trap.valid)
        self.assertEqual(res_trap.block_errno, EINVAL_ERRNO_PHASE347)
        self.assertEqual(res_trap.status, STATUS_BLOCKED_G150_HLG_STILL_USB_LUN_OR_NPFZ100_PD_VIOLATION)

    def test_45_g150_host_msc_slot1_attach_blocked_erofs_macos_spotlight_shield(self) -> None:
        self.assertIn("mds_Spotlight", MACOS_MSC_POLLUTION_DAEMONS_G150)
        self.assertIn("fseventsd", MACOS_MSC_POLLUTION_DAEMONS_G150)
        self.assertIn("fsck_exfat", MACOS_MSC_POLLUTION_DAEMONS_G150)
        for lun in ALLOWED_USB_LUN_SETTINGS_G150:
            res = verify_still_arw_hlg_usblun_uvc_guard(
                usb_connection_mode=USB_CONN_MSC_G150,
                usb_lun_setting=lun,
                host_msc_slot1_attach_requested=True,
                target_media_slot=MEDIA_SLOT_1_PHASE347,
            )
            self.assertFalse(res.valid)
            self.assertTrue(res.slot1_tier0_vault_firewall_blocked)
            self.assertEqual(res.block_errno, EROFS_ERRNO_PHASE347)
            self.assertEqual(res.slot1_data_sector_writes, 0)

    def test_46_g150_usb_setup_reset_immunity_rejects_camset_reset_claim(self) -> None:
        res = verify_still_arw_hlg_usblun_uvc_guard(
            claimed_camset_reset_clears_usb_settings=True
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.block_errno, EINVAL_ERRNO_PHASE347)

    def test_47_g150_np_fz100_pd_boot_gate_vs_dc_c1(self) -> None:
        res_bat = verify_still_arw_hlg_usblun_uvc_guard(
            np_fz100_battery_inserted=True, np_fz100_charge_pct=25
        )
        self.assertTrue(res_bat.valid)
        self.assertTrue(res_bat.np_fz100_pd_boot_gate_satisfied)

        res_dcc1 = verify_still_arw_hlg_usblun_uvc_guard(
            np_fz100_battery_inserted=False,
            np_fz100_charge_pct=0,
            dc_c1_65w_5a_coupler_active=True,
        )
        self.assertTrue(res_dcc1.valid)
        self.assertTrue(res_dcc1.np_fz100_pd_boot_gate_satisfied)

        for kw in (
            {"np_fz100_battery_inserted": False, "np_fz100_charge_pct": 0},
            {"np_fz100_battery_inserted": True, "np_fz100_charge_pct": 0},
            {"claimed_usb_pd_boots_without_battery_or_dcc1": True},
        ):
            res_fail = verify_still_arw_hlg_usblun_uvc_guard(**kw)
            self.assertFalse(res_fail.valid)
            self.assertEqual(res_fail.block_errno, EINVAL_ERRNO_PHASE347)

    def test_48_g150_usb_power_type_c_only_rejects_multi_micro_usb(self) -> None:
        r1 = verify_still_arw_hlg_usblun_uvc_guard(usb_port_type=USB_POWER_PORT_MULTI_MICRO_G150)
        self.assertFalse(r1.valid)
        self.assertEqual(r1.block_errno, EINVAL_ERRNO_PHASE347)

        r2 = verify_still_arw_hlg_usblun_uvc_guard(claimed_multi_micro_usb_supplies_power=True)
        self.assertFalse(r2.valid)
        self.assertEqual(r2.block_errno, EINVAL_ERRNO_PHASE347)

    def test_49_g150_dual_fx3_fx6_uvc_myth_busting_eopnotsupp(self) -> None:
        for mode_tok in DORMANT_USB_STREAMING_MODE_NAMES_G150:
            res = verify_still_arw_hlg_usblun_uvc_guard(usb_connection_mode=mode_tok)
            self.assertFalse(res.valid)
            self.assertTrue(res.dormant_native_uvc_streaming_rejected)
            self.assertEqual(res.block_errno, EOPNOTSUPP_ERRNO_PHASE347)
            self.assertEqual(
                res.status,
                STATUS_BLOCKED_G150_DORMANT_LOSSLESS_RAW_OR_UVC_STREAMING_EOPNOTSUPP,
            )

        r_fx3 = verify_still_arw_hlg_usblun_uvc_guard(requested_native_uvc_usb_streaming_fx3=True)
        self.assertFalse(r_fx3.valid)
        self.assertEqual(r_fx3.block_errno, EOPNOTSUPP_ERRNO_PHASE347)

        r_fx6 = verify_still_arw_hlg_usblun_uvc_guard(requested_native_uvc_usb_streaming_fx6=True)
        self.assertFalse(r_fx6.valid)
        self.assertEqual(r_fx6.block_errno, EOPNOTSUPP_ERRNO_PHASE347)

    def test_50_g150_movie_rec_during_streaming_and_hdmi_rec_slot1_erofs(self) -> None:
        r_net = verify_still_arw_hlg_usblun_uvc_guard(
            movie_rec_during_streaming="Enable",
            target_media_slot=MEDIA_SLOT_1_PHASE347,
        )
        self.assertFalse(r_net.valid)
        self.assertEqual(r_net.block_errno, EROFS_ERRNO_PHASE347)
        self.assertEqual(r_net.slot1_data_sector_writes, 0)

        r_hdmi = verify_still_arw_hlg_usblun_uvc_guard(
            hdmi_rec_media_mode=HDMI_REC_MEDIA_ON_G150,
            target_media_slot=MEDIA_SLOT_1_PHASE347,
        )
        self.assertFalse(r_hdmi.valid)
        self.assertEqual(r_hdmi.block_errno, EROFS_ERRNO_PHASE347)
        self.assertEqual(r_hdmi.slot1_data_sector_writes, 0)

        r_s2 = verify_still_arw_hlg_usblun_uvc_guard(
            movie_rec_during_streaming="Enable",
            hdmi_rec_media_mode=HDMI_REC_MEDIA_ON_G150,
            target_media_slot=MEDIA_SLOT_2_PHASE347,
        )
        self.assertTrue(r_s2.valid)

    def test_51_g150_fx6_still_arw_hlg_spoof_rejected_eopnotsupp(self) -> None:
        res = verify_still_arw_hlg_usblun_uvc_guard(
            fx6_still_arw_or_hlg_photo_spoof_requested=True
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.block_errno, EOPNOTSUPP_ERRNO_PHASE347)
        self.assertEqual(
            res.status,
            STATUS_BLOCKED_G150_DORMANT_LOSSLESS_RAW_OR_UVC_STREAMING_EOPNOTSUPP,
        )

    def test_52_g150_matrix_combinatorics(self) -> None:
        m = compute_still_arw_hlg_usblun_uvc_matrix()
        self.assertEqual(m["total_matrix_states"], 384)
        self.assertGreater(m["hlg_active_bt2100_count"], 0)
        self.assertGreater(m["sort_spillover_count"], 0)
        self.assertGreater(m["usb_lun_single_slot1_count"], 0)
        self.assertGreater(m["camset_preserved_usb_lun_count"], 0)
        self.assertGreater(m["np_fz100_boot_blocked_count"], 0)

    def test_53_g150_initialize_resets_usb_and_rec_media(self) -> None:
        st = resolve_fx3_still_arw_hlg_usblun_uvc_state(
            usb_connection_mode=USB_CONN_REMOTE_SHOOTING_G150,
            usb_lun_setting=USB_LUN_SINGLE_G150,
            usb_power_supply="Off",
            rec_media_mode=REC_MEDIA_SORT_G150,
            movie_rec_during_streaming="Enable",
            reset_action=RESET_ACTION_INITIALIZE_PHASE347,
        )
        self.assertEqual(st["effective_usb_connection_mode"], USB_CONN_SEL_WHEN_CONNECT_G150)
        self.assertEqual(st["effective_usb_lun_setting"], USB_LUN_MULTI_G150)
        self.assertEqual(st["effective_usb_power_supply"], "On")
        self.assertEqual(st["effective_rec_media_mode"], REC_MEDIA_SLOT1_G150)
        self.assertEqual(st["effective_movie_rec_during_streaming"], "Disable")

    def test_54_g150_rejects_invalid_telemetry_and_bool_int(self) -> None:
        for kw in (
            {"raw_file_type": "mRAW"},
            {"jh_switch": "AVIF"},
            {"still_file_format": "DNG"},
            {"exposure_mode": "Scene"},
            {"hlg_still_image": "Auto"},
            {"rec_media_mode": "Slot 3"},
            {"auto_switch_media": "Yes"},
            {"target_media_slot": True},
            {"target_media_slot": 3},
            {"usb_connection_mode": "TetherPro"},
            {"usb_lun_setting": "Triple"},
            {"usb_power_supply": "Fast"},
            {"usb_port_type": "Lightning"},
            {"np_fz100_charge_pct": True},
            {"np_fz100_charge_pct": 105},
            {"movie_rec_during_streaming": "Maybe"},
            {"hdmi_rec_media_mode": "Mirror"},
            {"reset_action": "SoftReset"},
        ):
            r = verify_still_arw_hlg_usblun_uvc_guard(**kw)  # type: ignore[arg-type]
            self.assertFalse(r.valid)
            self.assertEqual(r.status, STATUS_BLOCKED_G150_TELEMETRY_INVALID)

    def test_55_g150_body_identity_validation(self) -> None:
        for kw in (
            {"body_model_name": "ILME-FX30"},
            {"body_model_id": 0x0503},
            {"help_guide_code": "ilc/2220"},
            {"firmware_version": "not_a_float"},
        ):
            r = verify_still_arw_hlg_usblun_uvc_guard(**kw)  # type: ignore[arg-type]
            self.assertFalse(r.valid)
            self.assertEqual(r.status, STATUS_BLOCKED_G150_TELEMETRY_INVALID)

    def test_56_g150_mtp_mode_allowed_offline_when_not_slot1_write(self) -> None:
        r = verify_still_arw_hlg_usblun_uvc_guard(
            usb_connection_mode=USB_CONN_MTP_G150,
            target_media_slot=MEDIA_SLOT_2_PHASE347,
        )
        self.assertTrue(r.valid)
        self.assertEqual(r.effective_usb_connection_mode, USB_CONN_MTP_G150)

    def test_57_g150_simult_recording_to_slot1_blocked_when_write_requested(self) -> None:
        r = verify_still_arw_hlg_usblun_uvc_guard(
            rec_media_mode=REC_MEDIA_SIMULT_G150,
            target_media_slot=MEDIA_SLOT_1_PHASE347,
            sort_or_still_write_requested=True,
        )
        self.assertFalse(r.valid)
        self.assertEqual(r.block_errno, EROFS_ERRNO_PHASE347)
        self.assertEqual(r.slot1_data_sector_writes, 0)

    def test_58_g150_allow_lists_consistent(self) -> None:
        self.assertEqual(ALLOWED_RAW_FILE_TYPES_G150, ("Compressed", "Uncompressed"))
        self.assertEqual(len(ALLOWED_JH_SWITCH_MODES_G150), 3)
        self.assertEqual(len(ALLOWED_USB_LUN_SETTINGS_G150), 2)
        self.assertEqual(len(DORMANT_RAW_FILE_TYPES_G150), 8)

    def test_59_g150_type_c_power_supply_off_valid_when_battery_ok(self) -> None:
        r = verify_still_arw_hlg_usblun_uvc_guard(
            usb_power_supply="Off",
            usb_port_type=USB_POWER_PORT_TYPE_C_G150,
            np_fz100_battery_inserted=True,
            np_fz100_charge_pct=50,
        )
        self.assertTrue(r.valid)
        self.assertEqual(r.effective_usb_power_supply, "Off")

    def test_60_g150_result_to_dict_serializable(self) -> None:
        res = verify_still_arw_hlg_usblun_uvc_guard()
        d = res.to_dict()
        self.assertEqual(json.loads(json.dumps(d))["status"], STATUS_VERIFIED_G150)

    def test_61_g150_fx3_fw_constants_verified(self) -> None:
        self.assertEqual(FX3_MODEL_NAME_PHASE347, "ILME-FX3")
        self.assertEqual(FX3_MODEL_ID_PHASE347, 0x0502)
        self.assertEqual(FX3_HELP_GUIDE_CODE_PHASE347, "ilc/2210")
        self.assertEqual(FX3_DEFAULT_FW_VERSION_PHASE347, "7.02")

    def test_62_g150_slot2_direct_still_write_allowed_offline(self) -> None:
        r = verify_still_arw_hlg_usblun_uvc_guard(
            rec_media_mode=REC_MEDIA_SLOT2_G150,
            target_media_slot=MEDIA_SLOT_2_PHASE347,
            sort_or_still_write_requested=True,
        )
        self.assertTrue(r.valid)
        self.assertFalse(r.slot1_tier0_vault_firewall_blocked)

    # -----------------------------------------------------------------------
    # 63..86: Unified 150-Gate Preflight, 4 Modes, Redlines & Compat
    # -----------------------------------------------------------------------

    def test_63_150gate_preflight_normal_offline_147_of_150(self) -> None:
        env_clean = {
            k: v
            for k, v in os.environ.items()
            if k not in (ENV_FORCE_CLEAN_ROOM, ENV_CLEAN_ROOM_TEST_PHASE347)
        }
        with mock.patch.dict(os.environ, env_clean, clear=True):
            rep = evaluate_150gate_preflight(DEFAULT_REPO_ROOT)
            self.assertEqual(rep.schema, REALHW_150GATE_PREFLIGHT_SCHEMA)
            self.assertEqual(rep.summary["total_gates"], 150)
            self.assertEqual(rep.summary["verified_gates"], 147)
            self.assertEqual(rep.summary["blocked_or_pending_gates"], 3)
            self.assertTrue(rep.offline_147_gates_verified)
            self.assertFalse(rep.all_150_gates_verified)
            self.assertTrue(rep.g149_to_g150_all_passed)
            self.assertTrue(rep.g13_to_g150_all_passed)
            self.assertEqual(rep.status, "VERIFIED_147_OF_150_AWAITING_PHYSICAL_TIER0")
            self.assertEqual(len(rep.gates), 150)
            self.assertFalse(rep.overall_ready_for_hardware_attach)
            self.assertFalse(rep.hardware_live_attachment_authorized)
            self.assertFalse(rep.cross_model_flash_authorized)
            self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_64_150gate_preflight_simulated_dry_run_150_of_150(self) -> None:
        rep = evaluate_150gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            simulate_bench_dry_run=True,
        )
        self.assertEqual(rep.summary["total_gates"], 150)
        self.assertEqual(rep.summary["verified_gates"], 150)
        self.assertEqual(rep.summary["blocked_or_pending_gates"], 0)
        self.assertTrue(rep.offline_147_gates_verified)
        self.assertTrue(rep.all_150_gates_verified)
        self.assertTrue(rep.dry_run_rehearsal_only)
        self.assertEqual(rep.status, "VERIFIED_ALL_150_GATES_DRY_RUN_SIMULATED_BACKUP")
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.hardware_live_attachment_authorized)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.cross_model_flash_authorized)
        self.assertEqual(rep.usb_packets_transmitted, 0)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_65_150gate_preflight_env_clean_room_test_mode(self) -> None:
        with mock.patch.dict(os.environ, {ENV_CLEAN_ROOM_TEST_PHASE347: "1"}):
            rep = evaluate_150gate_preflight(DEFAULT_REPO_ROOT, dry_run_simulated=True)
            self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertEqual(rep.summary["verified_gates"], 150)
            self.assertTrue(rep.all_150_gates_verified)

    def test_66_150gate_preflight_env_force_clean_room_mode(self) -> None:
        with mock.patch.dict(os.environ, {ENV_FORCE_CLEAN_ROOM: "1"}):
            rep_off = evaluate_150gate_preflight(DEFAULT_REPO_ROOT)
            self.assertEqual(rep_off.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertEqual(rep_off.summary["verified_gates"], 147)
            rep_sim = evaluate_150gate_preflight(DEFAULT_REPO_ROOT, dry_run_simulated=True)
            self.assertEqual(rep_sim.summary["verified_gates"], 150)

    def test_67_150gate_preflight_mocked_donorless_work_root_none(self) -> None:
        env_clean = {
            k: v
            for k, v in os.environ.items()
            if k not in (ENV_FORCE_CLEAN_ROOM, ENV_CLEAN_ROOM_TEST_PHASE347)
        }
        with mock.patch.dict(os.environ, env_clean, clear=True):
            with mock.patch(
                "fx3_safety.realhw_zoom_ciz_autoslow_iso_arw_rawcomp_usblun_uvc_and_150gate_guard.resolve_donor_thermal_power_paths",
                side_effect=_fake_donorless_paths,
            ):
                rep = evaluate_150gate_preflight(DEFAULT_REPO_ROOT, dry_run_simulated=True)
                self.assertEqual(rep.summary["verified_gates"], 150)
                self.assertTrue(rep.all_150_gates_verified)
                self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_68_150gate_preflight_blocks_persistent_emmc_writes(self) -> None:
        rep = evaluate_150gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            request_persistent_emmc_writes=True,
        )
        self.assertEqual(rep.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        self.assertFalse(rep.offline_147_gates_verified)
        self.assertFalse(rep.all_150_gates_verified)
        self.assertFalse(rep.h0_h1_trial_entry_allowed)
        self.assertFalse(rep.persistent_emmc_writes_authorized)

    def test_69_150gate_preflight_fails_closed_on_g149_fault(self) -> None:
        rep = evaluate_150gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            zoom_ciz_autoslow_baseiso_kwargs={"fx6_digital_zoom_requested": True},
        )
        self.assertFalse(rep.g149_to_g150_all_passed)
        self.assertFalse(rep.all_150_gates_verified)
        self.assertEqual(rep.summary["verified_gates"], 149)
        self.assertEqual(rep.status, STATUS_BLOCKED_G149_FX6_DIGITAL_ZOOM_OR_MIN_SS_EOPNOTSUPP)

    def test_70_150gate_preflight_fails_closed_on_g150_fault(self) -> None:
        rep = evaluate_150gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            still_arw_hlg_usblun_uvc_kwargs={
                "host_msc_slot1_attach_requested": True,
                "target_media_slot": MEDIA_SLOT_1_PHASE347,
            },
        )
        self.assertFalse(rep.g149_to_g150_all_passed)
        self.assertFalse(rep.all_150_gates_verified)
        self.assertEqual(rep.summary["verified_gates"], 149)
        self.assertEqual(rep.status, STATUS_BLOCKED_G150_SLOT1_SORT_USB_MSC_STREAM_VAULT_EROFS)

    def test_71_150gate_preflight_propagates_upstream_fault_kwargs(self) -> None:
        rep = evaluate_150gate_preflight(
            DEFAULT_REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            breathing_camid_reel_kwargs={"requested_write_operation": True, "target_media_slot": 1},
        )
        self.assertFalse(rep.all_150_gates_verified)
        self.assertFalse(rep.g13_to_g150_all_passed)

    def test_72_150gate_alias_entrypoints_parity(self) -> None:
        r1 = evaluate_150_master_safety_gates(
            DEFAULT_REPO_ROOT, force_clean_room=True, dry_run_simulated=True
        )
        r2 = run_150_gate_preflight(
            DEFAULT_REPO_ROOT, force_clean_room=True, dry_run_simulated_backup=True
        )
        self.assertEqual(r1.summary["verified_gates"], 150)
        self.assertEqual(r2.summary["verified_gates"], 150)
        self.assertEqual(r1.status, r2.status)

    def test_73_150gate_summary_contract_keys_present(self) -> None:
        rep = evaluate_150gate_preflight(
            DEFAULT_REPO_ROOT, force_clean_room=True, dry_run_simulated=True
        )
        for key in (
            "total_gates",
            "verified_gates",
            "technical_gates_passed",
            "blocked_or_pending_gates",
            "g01_to_g12_verified",
            "g13_to_g148_verified",
            "g149_to_g150_verified",
            "g13_to_g150_all_passed",
            "g149_to_g150_all_passed",
            "offline_147_gates_verified",
            "all_150_gates_verified",
            "dry_run_rehearsal_only",
            "overall_ready_for_hardware_attach",
            "hardware_live_attachment_authorized",
            "agent_auto_flash_blocked",
            "persistent_emmc_writes_authorized",
            "cross_model_flash_authorized",
            "usb_packets_transmitted",
            "raw_firmware_bytes_leaked",
        ):
            self.assertIn(key, rep.summary)

    def test_74_strip_elapsed_seconds_recursive_digest_stability(self) -> None:
        _, g1 = evaluate_g149_zoom_ciz_digital_8step_speed_reset_split_and_autoslow_dual_base_iso_guard(
            repo_root=DEFAULT_REPO_ROOT, force_clean_room=True
        )
        _, g2 = evaluate_g149_zoom_ciz_digital_8step_speed_reset_split_and_autoslow_dual_base_iso_guard(
            repo_root=DEFAULT_REPO_ROOT, force_clean_room=True
        )
        d1 = json.dumps(strip_elapsed_seconds_recursive_phase347(g1.to_dict()), sort_keys=True)
        d2 = json.dumps(strip_elapsed_seconds_recursive_phase347(g2.to_dict()), sort_keys=True)
        self.assertEqual(hashlib.sha256(d1.encode()).hexdigest(), hashlib.sha256(d2.encode()).hexdigest())
        self.assertNotIn("elapsed_seconds", d1)

    def test_75_backward_compatibility_148_146_144_gates(self) -> None:
        r148 = evaluate_148gate_preflight(
            DEFAULT_REPO_ROOT, force_clean_room=True, dry_run_simulated=True
        )
        r146 = evaluate_146gate_preflight(
            DEFAULT_REPO_ROOT, force_clean_room=True, dry_run_simulated=True
        )
        r144 = evaluate_144gate_preflight(
            DEFAULT_REPO_ROOT, force_clean_room=True, dry_run_simulated=True
        )
        self.assertEqual(r148.summary["verified_gates"], 148)
        self.assertEqual(r146.summary["verified_gates"], 146)
        self.assertEqual(r144.summary["verified_gates"], 144)

    def test_76_gate_ids_g01_through_g150_ordered(self) -> None:
        rep = evaluate_150gate_preflight(
            DEFAULT_REPO_ROOT, force_clean_room=True, dry_run_simulated=True
        )
        ids = [g["gate_id"] for g in rep.gates]
        self.assertEqual(len(ids), 150)
        self.assertEqual(ids[-2], G149)
        self.assertEqual(ids[-1], G150)
        self.assertEqual(rep.gates[-2]["gate_code"], G149_GATE_CODE)
        self.assertEqual(rep.gates[-1]["gate_code"], G150_GATE_CODE)

    def test_77_nested_master_148_and_g149_g150_dicts_present(self) -> None:
        rep = evaluate_150gate_preflight(
            DEFAULT_REPO_ROOT, force_clean_room=True, dry_run_simulated=True
        )
        self.assertEqual(rep.master_148_report["summary"]["total_gates"], 148)
        self.assertEqual(rep.g149_result["gate_id"], G149)
        self.assertEqual(rep.g150_result["gate_id"], G150)

    def test_78_h0_h1_trial_entry_allowed_even_offline_147_of_150(self) -> None:
        rep = evaluate_150gate_preflight(
            DEFAULT_REPO_ROOT, force_clean_room=True, dry_run_simulated=False
        )
        self.assertTrue(rep.offline_147_gates_verified)
        self.assertTrue(rep.h0_h1_trial_entry_allowed)
        self.assertFalse(rep.overall_ready_for_hardware_attach)

    def test_79_json_roundtrip_master150_report(self) -> None:
        rep = evaluate_150gate_preflight(
            DEFAULT_REPO_ROOT, force_clean_room=True, dry_run_simulated=True
        )
        dumped = json.dumps(rep.to_dict(), ensure_ascii=False)
        parsed = json.loads(dumped)
        self.assertEqual(parsed["summary"]["total_gates"], 150)
        self.assertEqual(parsed["summary"]["verified_gates"], 150)

    def test_80_dry_run_rehearsal_false_when_not_simulated(self) -> None:
        rep = evaluate_150gate_preflight(
            DEFAULT_REPO_ROOT, force_clean_room=True, dry_run_simulated=False
        )
        self.assertFalse(rep.dry_run_rehearsal_only)
        self.assertFalse(rep.all_150_gates_verified)

    def test_81_g149_audit_wrapper_propagates_errors(self) -> None:
        v, r = evaluate_g149_zoom_ciz_digital_8step_speed_reset_split_and_autoslow_dual_base_iso_guard(
            repo_root=DEFAULT_REPO_ROOT,
            force_clean_room=True,
            claimed_camset_reset_clears_zoom_range_or_ring=True,
        )
        self.assertFalse(v.passed)
        self.assertFalse(r.valid)
        self.assertGreater(len(r.errors), 0)

    def test_82_g150_audit_wrapper_propagates_errors(self) -> None:
        v, r = evaluate_g150_still_arw_dormant_lossless_hlg_photo_and_usb_lun_single_slot1_npfz100_uvc_firewall(
            repo_root=DEFAULT_REPO_ROOT,
            force_clean_room=True,
            raw_file_type="Lossless Comp (S)",
        )
        self.assertFalse(v.passed)
        self.assertFalse(r.valid)
        self.assertGreater(len(r.errors), 0)

    def test_83_g149_reset_network_set_does_not_reset_zoom_or_exposure(self) -> None:
        st = resolve_fx3_zoom_ciz_autoslow_baseiso_state(
            zoom_range=ZOOM_RANGE_CIZ_G149,
            zoom_lever_1st_speed=7,
            auto_slow_shutter="Off",
            reset_action="Reset Network Set.",
        )
        self.assertEqual(st["effective_zoom_range"], ZOOM_RANGE_CIZ_G149)
        self.assertEqual(st["effective_zoom_lever_1st_speed"], 7)
        self.assertEqual(st["effective_auto_slow_shutter"], "Off")

    def test_84_g150_reset_network_set_preserves_still_and_usb(self) -> None:
        st = resolve_fx3_still_arw_hlg_usblun_uvc_state(
            raw_file_type=RAW_FILE_TYPE_UNCOMPRESSED_G150,
            usb_lun_setting=USB_LUN_SINGLE_G150,
            reset_action="Reset Network Set.",
        )
        self.assertEqual(st["effective_raw_file_type"], RAW_FILE_TYPE_UNCOMPRESSED_G150)
        self.assertEqual(st["effective_usb_lun_setting"], USB_LUN_SINGLE_G150)

    def test_85_g149_cine_ei_ei_defaults_800_12800_and_reset(self) -> None:
        st = resolve_fx3_zoom_ciz_autoslow_baseiso_state(
            log_shooting_mode=LOG_SHOOTING_CINE_EI_G149,
            base_iso_cine_ei=BASE_ISO_HIGH_G149,
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE347,
        )
        self.assertEqual(st["effective_cine_ei_base_iso"], BASE_ISO_DEFAULT_G149)
        self.assertEqual(st["effective_low_base_iso"], BASE_ISO_LOW_G149)
        self.assertEqual(st["effective_high_base_iso"], BASE_ISO_HIGH_G149)

    def test_86_g150_hlg_still_resets_to_off_on_camset_reset(self) -> None:
        st = resolve_fx3_still_arw_hlg_usblun_uvc_state(
            jh_switch=JH_SWITCH_HEIF_422_G150,
            still_file_format=STILL_FMT_HEIF_G150,
            exposure_mode=EXPOSURE_MODE_M_G149,
            hlg_still_image="On",
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE347,
        )
        self.assertEqual(st["effective_hlg_still_image"], "Off")
        self.assertEqual(st["effective_jh_switch"], JH_SWITCH_JPEG_G150)

    # -----------------------------------------------------------------------
    # 87..98: CLI, Package Exports & Milestone324/311 Auto-Discovery
    # -----------------------------------------------------------------------

    def test_87_cli_help_percent_escaping_clean(self) -> None:
        buf = io.StringIO()
        with self.assertRaises(SystemExit) as ctx:
            with contextlib.redirect_stdout(buf):
                cli_main(["--help"])
        self.assertEqual(ctx.exception.code, 0)
        self.assertIn("verify-150-gates", buf.getvalue())
        self.assertIn("verify-zoom-ciz-autoslow-baseiso-guard", buf.getvalue())
        self.assertIn("verify-still-arw-hlg-usblun-uvc-guard", buf.getvalue())

    def test_88_cli_verify_150_gates_offline_text_and_json(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cli_main(["verify-150-gates", "--clean-room"])
        self.assertEqual(rc, 0)
        self.assertIn("verified=147/150", buf.getvalue())
        self.assertIn("VERIFIED_147_OF_150_AWAITING_PHYSICAL_TIER0", buf.getvalue())

        jbuf = io.StringIO()
        with contextlib.redirect_stdout(jbuf):
            rc2 = cli_main(["verify-150-gates", "--clean-room", "--json", "--summary"])
        self.assertEqual(rc2, 0)
        payload = json.loads(jbuf.getvalue())
        self.assertEqual(payload["summary"]["verified_gates"], 147)

    def test_89_cli_verify_150_gates_simulated_dry_run(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cli_main(
                ["verify-150-gates", "--clean-room", "--simulate-bench-dry-run", "--json", "--summary"]
            )
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["summary"]["verified_gates"], 150)
        self.assertTrue(payload["summary"]["all_150_gates_verified"])
        self.assertFalse(payload["summary"]["overall_ready_for_hardware_attach"])

    def test_90_cli_verify_g149_and_aliases(self) -> None:
        for cmd in (
            "verify-zoom-ciz-autoslow-baseiso-guard",
            "verify-g149-zoom-ciz-autoslow-baseiso",
            "verify-g149",
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = cli_main([cmd, "--clean-room", "--json", "--summary"])
            self.assertEqual(rc, 0)
            payload = json.loads(buf.getvalue())
            self.assertEqual(payload["gate"], G149)
            self.assertTrue(payload["valid"])

    def test_91_cli_verify_g150_and_aliases(self) -> None:
        for cmd in (
            "verify-still-arw-hlg-usblun-uvc-guard",
            "verify-g150-still-arw-hlg-usblun-uvc",
            "verify-g150",
        ):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = cli_main([cmd, "--clean-room", "--json", "--summary"])
            self.assertEqual(rc, 0)
            payload = json.loads(buf.getvalue())
            self.assertEqual(payload["gate"], G150)
            self.assertTrue(payload["valid"])

    def test_92_cli_module_subcommand_help_works(self) -> None:
        from fx3_safety.realhw_zoom_ciz_autoslow_iso_arw_rawcomp_usblun_uvc_and_150gate_guard import (
            main as mod_main,
        )

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = mod_main(["--clean-room", "--simulate-bench-dry-run", "--json", "--summary"])
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(buf.getvalue())["summary"]["verified_gates"], 150)

    def test_93_fx3_safety_package_exports_and_all(self) -> None:
        for sym in (
            "evaluate_150gate_preflight",
            "evaluate_150_master_safety_gates",
            "run_150_gate_preflight",
            "evaluate_g149_zoom_ciz_digital_8step_speed_reset_split_and_autoslow_dual_base_iso_guard",
            "evaluate_g150_still_arw_dormant_lossless_hlg_photo_and_usb_lun_single_slot1_npfz100_uvc_firewall",
            "Master150GateReport",
        ):
            self.assertTrue(hasattr(fx3_safety, sym), f"Missing export {sym}")
            self.assertIn(sym, fx3_safety.__all__)

    def test_94_fx3_safety_discovers_gate_150_preflight(self) -> None:
        nums = sorted(
            int(name[9:-14])
            for name in dir(fx3_safety)
            if name.startswith("evaluate_") and name.endswith("gate_preflight") and name[9:-14].isdigit()
        )
        self.assertIn(150, nums)
        self.assertGreaterEqual(max(nums), 150)

    def test_95_milestone_324_master_gate_auto_discovers_150_gates(self) -> None:
        extra_paths = [
            str(DEFAULT_REPO_ROOT / "outputs" / p)
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
                repo_root=DEFAULT_REPO_ROOT, force_clean_room=True
            )
            self.assertGreaterEqual(rep.gate142_total_gates, 150)
            self.assertGreaterEqual(rep.gate142_offline_verified, 147)
            self.assertEqual(rep.gate142_offline_verified, rep.gate142_total_gates - 3)
            self.assertGreaterEqual(rep.gate142_simulated_verified, 150)
            self.assertEqual(rep.gate142_simulated_verified, rep.gate142_total_gates)
            self.assertTrue(rep.gate142_all_verified)

    def test_96_milestone_311_master_gate_auto_discovers_150_gates(self) -> None:
        extra_paths = [
            str(DEFAULT_REPO_ROOT / "outputs" / p)
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
                repo_root=DEFAULT_REPO_ROOT, force_clean_room=True
            )
            self.assertGreaterEqual(rep.gate134_total_gates, 150)
            self.assertGreaterEqual(rep.gate134_offline_verified, 147)
            self.assertEqual(rep.gate134_offline_verified, rep.gate134_total_gates - 3)
            self.assertGreaterEqual(rep.gate134_simulated_verified, 150)
            self.assertEqual(rep.gate134_simulated_verified, rep.gate134_total_gates)
            self.assertTrue(rep.gate134_all_verified)

    def test_97_cli_verify_150_gates_clean_room_text_mode(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = cli_main(["verify-150-gates", "--clean-room", "--simulate-bench-dry-run"])
        self.assertEqual(rc, 0)
        self.assertIn("verified=150/150", buf.getvalue())
        self.assertIn("all_150_gates_verified=True", buf.getvalue())

    def test_98_cli_verify_g149_g150_text_mode(self) -> None:
        b1 = io.StringIO()
        with contextlib.redirect_stdout(b1):
            rc1 = cli_main(["verify-g149", "--clean-room"])
        self.assertEqual(rc1, 0)
        self.assertIn("gate=G149", b1.getvalue())

        b2 = io.StringIO()
        with contextlib.redirect_stdout(b2):
            rc2 = cli_main(["verify-g150", "--clean-room"])
        self.assertEqual(rc2, 0)
        self.assertIn("gate=G150", b2.getvalue())


if __name__ == "__main__":
    unittest.main()
