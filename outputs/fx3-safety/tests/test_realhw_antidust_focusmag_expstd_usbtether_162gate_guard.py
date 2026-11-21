"""Comprehensive 4-mode test suite for Phase 378 (`162/162` Hardware Safety Gates, Wave-71):
Gate G161 (Dormant `[Anti-Dust Function]` / `[Shutter When Pwr OFF]` `ALCIN_UUD` Open-Shutter
Mechanical Safety & Active `[Sensor Cleaning]` `NP-FZ100 >= 51%` + Physical Power-Off Prompt
vs `ILME-FX6` Sealed `e-ND` + `Technical > APR`, plus `[Focus Magnifier]` Full-Pipeline:
5 Reset-Resistant Items, 12.1MP Ratios FF/APS-C/Movie, Dormant High-MP Alpha Ratio Rejection,
Still-Only `[AF in Focus Mag.]` & `[Auto Magnifier in MF]`, Movie `REC` Continuity, Clean-HDMI
& Internal-Recording Zero-Crop Isolation, Coexistence vs Suppression vs FX6 `VF/HDMI` Target),
Gate G162 (`[Exposure Std. Adjust]` 5-Mode `+-1.0 EV` `1/6-EV` Reset-Resistant Hidden Bias,
`M.M.` / Spot AEL Shift Without EXIF `ExposureBiasValue` Mutation, Mid-Bracket Count Reset vs
FX6 `+-3.0` `0.25`-Step 25-Step `AE Level` & Per-LUT `AE Level Offset`, plus Wired Smartphone
USB Tethering `CDC-NCM`/`RNDIS`/`ipheth` Zero-RF `Airplane Mode = On` Bypass, Dual-Port Mutex,
*Monitor & Control* USB Limitations, FX3 Stripped `CUsbGadgetIAP` vs FX6 Active `usbg_iap.ko`,
and Tier-0 `Slot 1` `MSC`/`MTP` `EROFS=30` Firewall),
and Unified `162`-Gate Master Safety Preflight (`G01..G162`).
"""

from __future__ import annotations

import ast
from contextlib import redirect_stdout
import hashlib
from io import StringIO
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.dont_write_bytecode = True

SAFETY_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SAFETY_ROOT.parents[1]
if str(SAFETY_ROOT) not in sys.path:
    sys.path.insert(0, str(SAFETY_ROOT))

import fx3_safety  # noqa: E402
from fx3_safety import __main__ as safety_cli  # noqa: E402
from fx3_safety.realhw_antidust_focusmag_expstd_usbtether_and_162gate_guard import (  # noqa: E402
    AF_IN_FOCUS_MAG_DEFAULT_G161,
    ALLOWED_EXPOSURE_CONTROL_MODES_G162,
    ALLOWED_FOCUS_MAG_TIMES_G161,
    ALLOWED_FX3_USB_CONNECTION_MODES_G162,
    ALLOWED_FX6_AE_MODES_G162,
    ALLOWED_FX6_FOCUS_MAG_TARGETS_G161,
    ALLOWED_USB_LUN_SETTINGS_G162,
    ALLOWED_USB_TETHERING_DRIVERS_G162,
    AUTO_MAG_IN_MF_DEFAULT_G161,
    DONOR_CHECK_MAX_SECONDS_PHASE378,
    DORMANT_ANTIDUST_FUNCTION_F_RESID16_G161,
    DORMANT_ANTIDUST_SYMBOLS_G161,
    DORMANT_HIGH_MP_ALPHA_MAG_RATIOS_G161,
    DORMANT_SHUTTER_WHEN_PWR_OFF_F_RESID16_G161,
    DORMANT_USB_STREAMING_MODE_G162,
    EBUSY_ERRNO_PHASE378,
    EINVAL_ERRNO_PHASE378,
    ENV_CLEAN_ROOM_TEST_PHASE378,
    EOPNOTSUPP_ERRNO_PHASE378,
    EROFS_ERRNO_PHASE378,
    EXACT_5_FX3_FOCUS_ASSISTANT_ITEMS_G161,
    EXACT_5_METERING_MODES_G162,
    EXPOSURE_STD_ADJUST_MENU_PATH_G162,
    EXPOSURE_STD_ADJUST_RESETTABLE_BY_CAMSET_RESET_G162,
    EXPOSURE_STD_ALTERS_EXIF_BIAS_VALUE_G162,
    EXPOSURE_STD_MAX_SIXTHS_G162,
    EXPOSURE_STD_MIN_SIXTHS_G162,
    EXPOSURE_STD_STEP_COUNT_G162,
    FOCUS_ASSISTANT_MENU_PATH_G161,
    FOCUS_MAG_TIME_DEFAULT_G161,
    FX3_AF_IN_FOCUS_MAG_STILL_ONLY_G161,
    FX3_AUTO_MAG_IN_MF_STILL_ONLY_G161,
    FX3_DEFAULT_FW_VERSION_PHASE378,
    FX3_DORMANT_ANTIDUST_EXPOSED_G161,
    FX3_DORMANT_SHUTTER_WHEN_PWR_OFF_EXPOSED_G161,
    FX3_FOCUS_ASSISTANT_5ITEMS_RESETTABLE_VER2_PLUS_G161,
    FX3_FOCUS_MAG_CLEAN_HDMI_CROP_PIXELS_G161,
    FX3_FOCUS_MAG_COEXISTING_FEATURES_G161,
    FX3_FOCUS_MAG_INTERNAL_REC_CROP_PIXELS_G161,
    FX3_FOCUS_MAG_REC_CONTINUITY_SUPPORTED_G161,
    FX3_FOCUS_MAG_SUPPRESSED_FEATURES_G161,
    FX3_HELP_GUIDE_CODE_PHASE378,
    FX3_MC_USB_FOCUS_MAP_SUPPORTED_G162,
    FX3_MC_USB_LUT_IMPORT_SUPPORTED_G162,
    FX3_MC_USB_TIMECODE_SUPPORTED_G162,
    FX3_MODEL_ID_PHASE378,
    FX3_MODEL_NAME_PHASE378,
    FX3_MOVIE_SQ_MAG_RATIOS_G161,
    FX3_POWER_OFF_SHUTTER_STATE_G161,
    FX3_STILL_APSC_MAG_RATIOS_G161,
    FX3_STILL_FF_MAG_RATIOS_G161,
    FX3_USBG_IAP_CLASS_HITS_G162,
    FX3_USB_MSC_ELF_TYPO_G162,
    FX3_USB_TETHERING_RF_TX_PACKETS_AIRPLANE_G162,
    FX3_USB_TETHERING_ZERO_RF_AIRPLANE_ALLOWED_G162,
    FX6_AE_LEVEL_MAX_G162,
    FX6_AE_LEVEL_MIN_G162,
    FX6_AE_LEVEL_STEP_COUNT_G162,
    FX6_AE_LEVEL_STEP_G162,
    FX6_END_RANGE_LABEL_G161,
    FX6_FOCAL_PLANE_MECHANICAL_SHUTTER_PRESENT_G161,
    FX6_HDMI_MAG_RATIOS_G161,
    FX6_PER_LUT_AE_LEVEL_OFFSET_SUPPORTED_G162,
    FX6_SHUTTER_WHEN_PWR_OFF_ELF_HITS_G161,
    FX6_USBG_IAP_CLASS_ACTIVE_G162,
    FX6_USER_IBIS_SENSOR_CLEANING_SUPPORTED_G161,
    FX6_VF_MAG_RATIOS_G161,
    G161,
    G162,
    MEDIA_SLOT_1_PHASE378,
    MEDIA_SLOT_2_PHASE378,
    MEDIA_SLOT_NONE_PHASE378,
    Master162GateReport,
    PINNED_FX3_APPFW_SLICES_PHASE378,
    PINNED_FX6_APPFW_SLICES_PHASE378,
    PINNED_PHASE378_DONOR_SPECS,
    REALHW_162GATE_PREFLIGHT_SCHEMA,
    RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE378,
    RESET_ACTION_INITIALIZE_PHASE378,
    RESET_ACTION_NONE_PHASE378,
    SENSOR_CLEANING_F_RESID16_G161,
    SENSOR_CLEANING_MENU_PATH_G161,
    SENSOR_CLEANING_MIN_SOC_PCT_G161,
    SHOOT_MODE_MOVIE_PHASE378,
    SHOOT_MODE_SQ_PHASE378,
    SHOOT_MODE_STILL_PHASE378,
    STATUS_BLOCKED_G161_CLEANING51_REC_HDMI_CROP_OR_SUPPRESSION_VIOLATION,
    STATUS_BLOCKED_G161_DORMANT_ANTIDUST_HIGHMP_RATIO_STILLONLY_OR_FX6_EOPNOTSUPP,
    STATUS_BLOCKED_G161_TELEMETRY_INVALID,
    STATUS_BLOCKED_G162_DORMANT_NOUVC_IAP2_MC_OR_STEP18_EOPNOTSUPP,
    STATUS_BLOCKED_G162_DUAL_USB_PORT_OR_FX6_LAN_MUTEX_EBUSY,
    STATUS_BLOCKED_G162_EXPSTD_EXIF_RESET_OR_ZERORF_AIRPLANE_VIOLATION,
    STATUS_BLOCKED_G162_SLOT1_MSC_MTP_WRITABLE_EROFS,
    STATUS_BLOCKED_G162_TELEMETRY_INVALID,
    STATUS_BLOCKED_PERSISTENT_EMMC_WRITE,
    STATUS_BLOCKED_PHASE378_DONOR_INTEGRITY,
    STATUS_VERIFIED_G161,
    STATUS_VERIFIED_G162,
    USB_CONNECTION_MODE_MENU_PATH_G162,
    USB_LAN_TETHERING_MENU_PATH_G162,
    audit_phase378_donor_contracts,
    compute_antidust_focusmag_matrix,
    compute_expstd_usbtether_matrix,
    evaluate_162_master_safety_gates,
    evaluate_162gate_preflight,
    evaluate_g161_antidust_focusmag_guard,
    evaluate_g162_expstd_usbtether_guard,
    main as guard_module_main,
    resolve_fx3_antidust_focusmag_state,
    resolve_fx3_expstd_usbtether_state,
    run_162_gate_preflight,
    strip_elapsed_seconds_recursive_phase378,
    verify_antidust_focusmag_guard,
    verify_antidust_focusmag_guard_with_audit,
    verify_expstd_usbtether_guard,
    verify_expstd_usbtether_guard_with_audit,
    verify_real_hardware_162gate_readiness,
)


def _mock_paths_work_root_none(**_kwargs):
    return mock.MagicMock(work_root=None)


class TestPhase378HardwareSafety162Gates(unittest.TestCase):
    # ------------------------------------------------------------------
    # Donor Integrity & 4-Mode Checks (01..12)
    # ------------------------------------------------------------------

    def test_01_donor_specs_pin_24_artifacts_and_fast_budget(self) -> None:
        self.assertEqual(len(PINNED_PHASE378_DONOR_SPECS), 24)
        self.assertEqual(len(PINNED_FX3_APPFW_SLICES_PHASE378), 31)
        self.assertEqual(len(PINNED_FX6_APPFW_SLICES_PHASE378), 14)
        audit = audit_phase378_donor_contracts(repo_root=REPO_ROOT)
        self.assertTrue(audit.valid)
        self.assertTrue(audit.within_budget_200ms)
        self.assertLessEqual(audit.elapsed_seconds, DONOR_CHECK_MAX_SECONDS_PHASE378)
        self.assertEqual(audit.raw_firmware_bytes_leaked, 0)

    def test_02_donor_audit_normal_mode_matches_expected(self) -> None:
        with mock.patch.dict(
            os.environ,
            {"FX3_FX6_FORCE_CLEAN_ROOM": "", ENV_CLEAN_ROOM_TEST_PHASE378: ""},
            clear=False,
        ):
            audit = audit_phase378_donor_contracts(repo_root=REPO_ROOT)
        self.assertTrue(audit.valid)
        self.assertTrue(audit.tethering_kmods_verified)
        self.assertTrue(audit.zero_fx3_iap2_gadget_verified)
        self.assertEqual(audit.raw_firmware_bytes_leaked, 0)
        self.assertIn(
            audit.verification_mode,
            ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"),
        )
        if audit.verification_mode == "LOCAL_DONOR_O_RDONLY":
            self.assertEqual(audit.files_inspected, 24)
            self.assertEqual(audit.access_mode, "STRICT_OS_O_RDONLY_PREAD")

    def test_03_donor_audit_fx3_clean_room_test_env_mode(self) -> None:
        with mock.patch.dict(
            os.environ,
            {ENV_CLEAN_ROOM_TEST_PHASE378: "1", "FX3_FX6_FORCE_CLEAN_ROOM": ""},
            clear=False,
        ):
            audit = audit_phase378_donor_contracts(repo_root=REPO_ROOT)
        self.assertTrue(audit.valid)
        self.assertEqual(audit.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(audit.access_mode, "SYNTHETIC_NO_DONOR_DISK_IO")
        self.assertEqual(audit.files_inspected, 0)
        self.assertEqual(audit.raw_firmware_bytes_leaked, 0)

    def test_04_donor_audit_force_clean_room_env_mode(self) -> None:
        with mock.patch.dict(
            os.environ,
            {"FX3_FX6_FORCE_CLEAN_ROOM": "1", ENV_CLEAN_ROOM_TEST_PHASE378: ""},
            clear=False,
        ):
            audit = audit_phase378_donor_contracts(repo_root=REPO_ROOT)
        self.assertTrue(audit.valid)
        self.assertEqual(audit.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(audit.files_inspected, 0)

    def test_05_donor_audit_mocked_work_root_none_fallback(self) -> None:
        with mock.patch(
            "fx3_safety.realhw_antidust_focusmag_expstd_usbtether_and_162gate_guard.resolve_donor_thermal_power_paths",
            side_effect=_mock_paths_work_root_none,
        ):
            with mock.patch.dict(
                os.environ,
                {"FX3_FX6_FORCE_CLEAN_ROOM": "", ENV_CLEAN_ROOM_TEST_PHASE378: ""},
                clear=False,
            ):
                audit = audit_phase378_donor_contracts(repo_root=REPO_ROOT)
        self.assertTrue(audit.valid)
        self.assertEqual(audit.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(audit.access_mode, "SYNTHETIC_ABSENT_DONOR_FALLBACK")
        self.assertEqual(audit.raw_firmware_bytes_leaked, 0)

    def test_06_donor_audit_absent_temp_work_root_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            audit = audit_phase378_donor_contracts(
                repo_root=REPO_ROOT,
                work_root=Path(tmpdir),
                force_clean_room=False,
            )
        self.assertTrue(audit.valid)
        self.assertEqual(audit.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(audit.access_mode, "SYNTHETIC_ABSENT_DONOR_FALLBACK")

    def test_07_donor_audit_override_detects_missing_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            bad_spec = {
                "tiny": ("FX3", "missing.bin", 4, "0" * 64, (b"ABCD",), "missing file")
            }
            audit = audit_phase378_donor_contracts(
                work_root=Path(tmpdir),
                force_clean_room=False,
                donor_specs_override=bad_spec,
            )
        self.assertFalse(audit.valid)
        self.assertEqual(audit.status, STATUS_BLOCKED_PHASE378_DONOR_INTEGRITY)

    def test_08_donor_audit_override_detects_size_and_sha_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir) / "sample.bin"
            p.write_bytes(b"ABCD1234")
            bad_spec = {
                "sample": (
                    "FX3",
                    "sample.bin",
                    99,
                    "f" * 64,
                    (b"ABCD", b"MISSING_TOK"),
                    "tampered",
                )
            }
            audit = audit_phase378_donor_contracts(
                work_root=Path(tmpdir),
                force_clean_room=False,
                donor_specs_override=bad_spec,
            )
        self.assertFalse(audit.valid)
        self.assertEqual(audit.status, STATUS_BLOCKED_PHASE378_DONOR_INTEGRITY)
        self.assertTrue(any("size_mismatch" in e for e in audit.errors))
        self.assertTrue(any("sha256_mismatch" in e for e in audit.errors))
        self.assertTrue(any("token_missing" in e for e in audit.errors))

    def test_09_donor_audit_override_valid_synthetic_file_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            payload = b"\x7fELF_WAVE71_TETHER_OK"
            p = Path(tmpdir) / "ok.bin"
            p.write_bytes(payload)
            sha = hashlib.sha256(payload).hexdigest()
            spec = {
                "ok": (
                    "FX3",
                    "ok.bin",
                    len(payload),
                    sha,
                    (b"\x7fELF", b"WAVE71"),
                    "ok synthetic",
                )
            }
            audit = audit_phase378_donor_contracts(
                work_root=Path(tmpdir),
                force_clean_room=False,
                donor_specs_override=spec,
            )
        self.assertTrue(audit.valid)
        self.assertEqual(audit.files_inspected, 1)
        self.assertEqual(audit.file_digests["ok"], sha)

    def test_10_donor_audit_clean_room_digest_deterministic(self) -> None:
        a1 = strip_elapsed_seconds_recursive_phase378(
            audit_phase378_donor_contracts(force_clean_room=True).to_dict()
        )
        a2 = strip_elapsed_seconds_recursive_phase378(
            audit_phase378_donor_contracts(force_clean_room=True).to_dict()
        )
        self.assertEqual(a1, a2)

    def test_11_source_module_strictly_o_rdonly_and_no_write_syscalls(self) -> None:
        src_path = (
            SAFETY_ROOT
            / "fx3_safety"
            / "realhw_antidust_focusmag_expstd_usbtether_and_162gate_guard.py"
        )
        text = src_path.read_text(encoding="utf-8")
        tree = ast.parse(text)
        self.assertIsNotNone(tree)
        self.assertIn("os.O_RDONLY", text)
        self.assertNotIn("os.O_RDWR", text)
        self.assertNotIn("os.O_CREAT", text)
        self.assertNotIn("write_bytes(", text)

    def test_12_pinned_constants_match_empirical_wave71_baseline(self) -> None:
        self.assertEqual(FX3_POWER_OFF_SHUTTER_STATE_G161, "OPEN")
        self.assertFalse(FX3_DORMANT_ANTIDUST_EXPOSED_G161)
        self.assertFalse(FX3_DORMANT_SHUTTER_WHEN_PWR_OFF_EXPOSED_G161)
        self.assertEqual(SENSOR_CLEANING_MIN_SOC_PCT_G161, 51)
        self.assertEqual(len(EXACT_5_FX3_FOCUS_ASSISTANT_ITEMS_G161), 5)
        self.assertFalse(FX3_FOCUS_ASSISTANT_5ITEMS_RESETTABLE_VER2_PLUS_G161)
        self.assertEqual(len(EXACT_5_METERING_MODES_G162), 5)
        self.assertEqual(EXPOSURE_STD_STEP_COUNT_G162, 13)
        self.assertFalse(EXPOSURE_STD_ADJUST_RESETTABLE_BY_CAMSET_RESET_G162)
        self.assertFalse(EXPOSURE_STD_ALTERS_EXIF_BIAS_VALUE_G162)
        self.assertEqual(FX6_AE_LEVEL_MIN_G162, -3.0)
        self.assertEqual(FX6_AE_LEVEL_MAX_G162, 3.0)
        self.assertEqual(FX6_AE_LEVEL_STEP_G162, 0.25)
        self.assertEqual(FX6_AE_LEVEL_STEP_COUNT_G162, 25)
        self.assertEqual(FX3_USBG_IAP_CLASS_HITS_G162, 0)
        self.assertTrue(FX6_USBG_IAP_CLASS_ACTIVE_G162)
        self.assertEqual(FX3_USB_MSC_ELF_TYPO_G162, "USB_CONNECTION_METHOD_MASS_STRAGE")

    # ------------------------------------------------------------------
    # Gate G161: Anti-Dust / Open-Shutter & Sensor Cleaning >=51% (13..30)
    # ------------------------------------------------------------------

    def test_13_g161_default_safe_baseline_passes(self) -> None:
        res = verify_antidust_focusmag_guard()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_VERIFIED_G161)
        self.assertEqual(res.block_errno, 0)
        self.assertEqual(res.effective_power_off_shutter_state, "OPEN")
        self.assertFalse(res.hdmi_output_cropped)
        self.assertFalse(res.internal_recording_cropped)
        self.assertEqual(res.raw_firmware_bytes_leaked, 0)

    def test_14_g161_blocks_dormant_antidust_function_eopnotsupp(self) -> None:
        res = verify_antidust_focusmag_guard(request_dormant_antidust_function=True)
        self.assertFalse(res.valid)
        self.assertEqual(res.block_errno, EOPNOTSUPP_ERRNO_PHASE378)
        self.assertEqual(
            res.status,
            STATUS_BLOCKED_G161_DORMANT_ANTIDUST_HIGHMP_RATIO_STILLONLY_OR_FX6_EOPNOTSUPP,
        )

    def test_15_g161_blocks_dormant_shutter_when_pwr_off_eopnotsupp(self) -> None:
        res = verify_antidust_focusmag_guard(request_dormant_shutter_when_pwr_off=True)
        self.assertFalse(res.valid)
        self.assertEqual(res.block_errno, EOPNOTSUPP_ERRNO_PHASE378)

    def test_16_g161_blocks_close_shutter_on_power_off_eopnotsupp(self) -> None:
        res = verify_antidust_focusmag_guard(close_shutter_on_power_off=True)
        self.assertFalse(res.valid)
        self.assertEqual(res.block_errno, EOPNOTSUPP_ERRNO_PHASE378)

    def test_17_g161_blocks_dormant_sensor_barrier_bkid_pid_eopnotsupp(self) -> None:
        res = verify_antidust_focusmag_guard(
            request_dormant_sensor_barrier_bkid_or_pid=True
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.block_errno, EOPNOTSUPP_ERRNO_PHASE378)

    def test_18_g161_sensor_cleaning_allows_exact_51pct_threshold(self) -> None:
        res = verify_antidust_focusmag_guard(
            sensor_cleaning_requested=True,
            np_fz100_inserted=True,
            np_fz100_soc_pct=51,
            skip_physical_power_off_prompt=False,
        )
        self.assertTrue(res.valid)
        self.assertTrue(res.sensor_cleaning_allowed)
        self.assertEqual(res.effective_power_off_shutter_state, "OPEN")

    def test_19_g161_sensor_cleaning_blocks_50pct_below_threshold(self) -> None:
        res = verify_antidust_focusmag_guard(
            sensor_cleaning_requested=True,
            np_fz100_inserted=True,
            np_fz100_soc_pct=50,
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.block_errno, EINVAL_ERRNO_PHASE378)
        self.assertEqual(
            res.status,
            STATUS_BLOCKED_G161_CLEANING51_REC_HDMI_CROP_OR_SUPPRESSION_VIOLATION,
        )
        self.assertFalse(res.sensor_cleaning_allowed)

    def test_20_g161_sensor_cleaning_blocks_missing_battery(self) -> None:
        res = verify_antidust_focusmag_guard(
            sensor_cleaning_requested=True,
            np_fz100_inserted=False,
            np_fz100_soc_pct=100,
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.block_errno, EINVAL_ERRNO_PHASE378)

    def test_21_g161_sensor_cleaning_blocks_skip_physical_power_off_prompt(self) -> None:
        res = verify_antidust_focusmag_guard(
            sensor_cleaning_requested=True,
            np_fz100_soc_pct=80,
            skip_physical_power_off_prompt=True,
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.block_errno, EINVAL_ERRNO_PHASE378)

    def test_22_g161_blocks_fx6_user_ibis_sensor_cleaning_eopnotsupp(self) -> None:
        res = verify_antidust_focusmag_guard(
            request_fx6_user_ibis_sensor_cleaning=True
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.block_errno, EOPNOTSUPP_ERRNO_PHASE378)

    def test_23_g161_blocks_fx6_mechanical_shutter_curtain_eopnotsupp(self) -> None:
        res = verify_antidust_focusmag_guard(
            request_fx6_mechanical_shutter_curtain=True
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.block_errno, EOPNOTSUPP_ERRNO_PHASE378)
        self.assertFalse(res.fx6_focal_plane_mechanical_shutter_present)
        self.assertEqual(res.fx6_end_range_label, FX6_END_RANGE_LABEL_G161)

    def test_24_g161_fx3_still_ff_ratios_x1_0_x2_1_x4_1_valid(self) -> None:
        for init_r in ("x1.0", "x2.1"):
            for act_r in FX3_STILL_FF_MAG_RATIOS_G161:
                res = verify_antidust_focusmag_guard(
                    shoot_mode=SHOOT_MODE_STILL_PHASE378,
                    sensor_crop_mode="FF",
                    initial_focus_mag_ratio=init_r,
                    active_focus_mag_ratio=act_r,
                    movie_rec_active=False,
                )
                self.assertTrue(res.valid, f"Failed for {init_r}->{act_r}: {res.errors}")

    def test_25_g161_fx3_still_apsc_ratios_x1_0_x1_5_x3_0_valid(self) -> None:
        for init_r in ("x1.0", "x1.5"):
            for act_r in FX3_STILL_APSC_MAG_RATIOS_G161:
                res = verify_antidust_focusmag_guard(
                    shoot_mode=SHOOT_MODE_STILL_PHASE378,
                    sensor_crop_mode="APS-C",
                    initial_focus_mag_ratio=init_r,
                    active_focus_mag_ratio=act_r,
                    movie_rec_active=False,
                )
                self.assertTrue(res.valid, f"Failed for {init_r}->{act_r}: {res.errors}")

    def test_26_g161_fx3_movie_and_sq_ratios_x1_0_x4_0_valid(self) -> None:
        for sm in (SHOOT_MODE_MOVIE_PHASE378, SHOOT_MODE_SQ_PHASE378):
            for init_r in ("x1.0", "x4.0"):
                for act_r in FX3_MOVIE_SQ_MAG_RATIOS_G161:
                    res = verify_antidust_focusmag_guard(
                        shoot_mode=sm,
                        initial_focus_mag_ratio=init_r,
                        active_focus_mag_ratio=act_r,
                    )
                    self.assertTrue(res.valid, f"Failed for {sm} {init_r}->{act_r}")

    def test_27_g161_rejects_all_10_dormant_high_mp_alpha_ratios_eopnotsupp(self) -> None:
        self.assertEqual(len(DORMANT_HIGH_MP_ALPHA_MAG_RATIOS_G161), 10)
        for bad_ratio in DORMANT_HIGH_MP_ALPHA_MAG_RATIOS_G161:
            res_act = verify_antidust_focusmag_guard(active_focus_mag_ratio=bad_ratio)
            self.assertFalse(res_act.valid, bad_ratio)
            self.assertEqual(res_act.block_errno, EOPNOTSUPP_ERRNO_PHASE378)
            res_init = verify_antidust_focusmag_guard(initial_focus_mag_ratio=bad_ratio)
            self.assertFalse(res_init.valid, bad_ratio)
            self.assertEqual(res_init.block_errno, EOPNOTSUPP_ERRNO_PHASE378)

    def test_28_g161_rejects_cross_mode_mismatched_active_ratios(self) -> None:
        res_mv = verify_antidust_focusmag_guard(
            shoot_mode=SHOOT_MODE_MOVIE_PHASE378,
            active_focus_mag_ratio="x2.1",
        )
        self.assertFalse(res_mv.valid)
        self.assertEqual(res_mv.block_errno, EINVAL_ERRNO_PHASE378)

        res_apsc = verify_antidust_focusmag_guard(
            shoot_mode=SHOOT_MODE_STILL_PHASE378,
            sensor_crop_mode="APS-C",
            active_focus_mag_ratio="x4.1",
            movie_rec_active=False,
        )
        self.assertFalse(res_apsc.valid)
        self.assertEqual(res_apsc.block_errno, EINVAL_ERRNO_PHASE378)

    def test_29_g161_all_3_focus_mag_times_valid(self) -> None:
        for t in ALLOWED_FOCUS_MAG_TIMES_G161:
            res = verify_antidust_focusmag_guard(focus_mag_time=t)
            self.assertTrue(res.valid)
            self.assertEqual(res.effective_focus_mag_time, t)

    def test_30_g161_rejects_invalid_focus_mag_time_telemetry(self) -> None:
        res = verify_antidust_focusmag_guard(focus_mag_time="10 Sec")
        self.assertFalse(res.valid)
        self.assertEqual(res.status, STATUS_BLOCKED_G161_TELEMETRY_INVALID)

    # ------------------------------------------------------------------
    # Gate G161: Focus Magnifier Still-Only, REC, Clean-HDMI & FX6 (31..48)
    # ------------------------------------------------------------------

    def test_31_g161_af_in_focus_mag_allowed_in_still_afs(self) -> None:
        res = verify_antidust_focusmag_guard(
            shoot_mode=SHOOT_MODE_STILL_PHASE378,
            active_focus_mag_ratio="x2.1",
            movie_rec_active=False,
            invoke_af_in_focus_mag=True,
            still_af_mode="AF-S",
        )
        self.assertTrue(res.valid)
        self.assertTrue(res.af_in_focus_mag_usable_in_mode)

    def test_32_g161_af_in_focus_mag_blocked_in_movie_and_sq_eopnotsupp(self) -> None:
        for sm in (SHOOT_MODE_MOVIE_PHASE378, SHOOT_MODE_SQ_PHASE378):
            res = verify_antidust_focusmag_guard(
                shoot_mode=sm,
                invoke_af_in_focus_mag=True,
            )
            self.assertFalse(res.valid)
            self.assertEqual(res.block_errno, EOPNOTSUPP_ERRNO_PHASE378)

    def test_33_g161_auto_mag_in_mf_blocked_in_movie_and_sq_eopnotsupp(self) -> None:
        for sm in (SHOOT_MODE_MOVIE_PHASE378, SHOOT_MODE_SQ_PHASE378):
            res = verify_antidust_focusmag_guard(
                shoot_mode=sm,
                invoke_auto_mag_in_mf=True,
            )
            self.assertFalse(res.valid)
            self.assertEqual(res.block_errno, EOPNOTSUPP_ERRNO_PHASE378)

    def test_34_g161_af_in_focus_mag_blocked_in_still_afc_cont_or_adapter(self) -> None:
        r1 = verify_antidust_focusmag_guard(
            shoot_mode=SHOOT_MODE_STILL_PHASE378,
            active_focus_mag_ratio="x2.1",
            movie_rec_active=False,
            invoke_af_in_focus_mag=True,
            still_af_mode="AF-C",
        )
        r2 = verify_antidust_focusmag_guard(
            shoot_mode=SHOOT_MODE_STILL_PHASE378,
            active_focus_mag_ratio="x2.1",
            movie_rec_active=False,
            invoke_af_in_focus_mag=True,
            still_cont_shooting_active=True,
        )
        r3 = verify_antidust_focusmag_guard(
            shoot_mode=SHOOT_MODE_STILL_PHASE378,
            active_focus_mag_ratio="x2.1",
            movie_rec_active=False,
            invoke_auto_mag_in_mf=True,
            mount_adapter_attached=True,
        )
        for r in (r1, r2, r3):
            self.assertFalse(r.valid)
            self.assertEqual(r.block_errno, EINVAL_ERRNO_PHASE378)

    def test_35_g161_blocks_claim_rec_cancels_focus_mag(self) -> None:
        res = verify_antidust_focusmag_guard(
            movie_rec_active=True,
            claim_rec_cancels_focus_mag=True,
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.block_errno, EINVAL_ERRNO_PHASE378)

    def test_36_g161_blocks_clean_hdmi_crop_and_internal_rec_crop(self) -> None:
        r1 = verify_antidust_focusmag_guard(
            hdmi_info_display="Off",
            claim_clean_hdmi_cropped=True,
        )
        r2 = verify_antidust_focusmag_guard(
            claim_internal_recording_cropped=True,
        )
        self.assertFalse(r1.valid)
        self.assertFalse(r2.valid)
        self.assertEqual(r1.clean_hdmi_crop_pixels, 0)
        self.assertEqual(r2.internal_rec_crop_pixels, 0)

    def test_37_g161_coexistence_with_peaking_bright_mon_ver7_and_desqueeze(self) -> None:
        res = verify_antidust_focusmag_guard(
            firmware_version="7.02",
            focus_magnifier_active=True,
            peaking_active=True,
            bright_monitoring_active=True,
            desqueeze_active=True,
        )
        self.assertTrue(res.valid)
        self.assertTrue(res.peaking_coexists)
        self.assertTrue(res.bright_monitoring_coexists)
        self.assertTrue(res.desqueeze_coexists)

    def test_38_g161_bright_mon_focus_mag_coexistence_blocked_below_ver7(self) -> None:
        res = verify_antidust_focusmag_guard(
            firmware_version="6.02",
            focus_magnifier_active=True,
            bright_monitoring_active=True,
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.block_errno, EINVAL_ERRNO_PHASE378)

    def test_39_g161_blocks_suppressed_features_active_during_focus_mag(self) -> None:
        for kw in (
            {"claim_marker_display_visible_during_mag": True},
            {"claim_switch_vh_af_active_during_mag": True},
            {"claim_af_illuminator_active_during_mag": True},
        ):
            res = verify_antidust_focusmag_guard(focus_magnifier_active=True, **kw)
            self.assertFalse(res.valid, str(kw))
            self.assertEqual(res.block_errno, EINVAL_ERRNO_PHASE378)
            self.assertEqual(
                res.suppressed_features_while_active,
                FX3_FOCUS_MAG_SUPPRESSED_FEATURES_G161,
            )

    def test_40_g161_focus_assistant_5items_resist_camset_reset_but_reset_on_init(self) -> None:
        st_rst = resolve_fx3_antidust_focusmag_state(
            focus_mag_time="2 Sec",
            initial_focus_mag_ratio="x4.0",
            af_in_focus_mag="Off",
            auto_mag_in_mf="Off",
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE378,
        )
        self.assertEqual(st_rst["effective_focus_mag_time"], "2 Sec")
        self.assertEqual(st_rst["effective_initial_focus_mag_ratio"], "x4.0")
        self.assertEqual(st_rst["effective_af_in_focus_mag"], "Off")
        self.assertEqual(st_rst["effective_auto_mag_in_mf"], "Off")

        st_init = resolve_fx3_antidust_focusmag_state(
            focus_mag_time="2 Sec",
            initial_focus_mag_ratio="x4.0",
            af_in_focus_mag="Off",
            auto_mag_in_mf="Off",
            reset_action=RESET_ACTION_INITIALIZE_PHASE378,
        )
        self.assertEqual(st_init["effective_focus_mag_time"], FOCUS_MAG_TIME_DEFAULT_G161)
        self.assertEqual(st_init["effective_initial_focus_mag_ratio"], "x1.0")
        self.assertEqual(st_init["effective_af_in_focus_mag"], AF_IN_FOCUS_MAG_DEFAULT_G161)
        self.assertEqual(st_init["effective_auto_mag_in_mf"], AUTO_MAG_IN_MF_DEFAULT_G161)

    def test_41_g161_blocks_claim_camset_reset_clears_focus_assistant(self) -> None:
        res = verify_antidust_focusmag_guard(
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE378,
            claim_camset_reset_clears_focus_assistant=True,
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.block_errno, EINVAL_ERRNO_PHASE378)

    def test_42_g161_fx6_vf_and_ver6_hdmi_target_ratios_valid(self) -> None:
        for r in FX6_VF_MAG_RATIOS_G161:
            res = verify_antidust_focusmag_guard(
                fx6_focus_mag_target="VF", fx6_focus_mag_ratio=r
            )
            self.assertTrue(res.valid, r)
        for r in FX6_HDMI_MAG_RATIOS_G161:
            res = verify_antidust_focusmag_guard(
                fx6_firmware_version="6.01",
                fx6_focus_mag_target="HDMI",
                fx6_focus_mag_ratio=r,
            )
            self.assertTrue(res.valid, r)

    def test_43_g161_fx6_hdmi_target_blocked_below_ver6_and_dormant_x8_blocked(self) -> None:
        r_old = verify_antidust_focusmag_guard(
            fx6_firmware_version="5.00",
            fx6_focus_mag_target="HDMI",
            fx6_focus_mag_ratio="x2.0",
        )
        self.assertFalse(r_old.valid)
        self.assertEqual(r_old.block_errno, EOPNOTSUPP_ERRNO_PHASE378)

        r_x8 = verify_antidust_focusmag_guard(
            fx6_focus_mag_target="VF", fx6_focus_mag_ratio="x8.0"
        )
        self.assertFalse(r_x8.valid)
        self.assertEqual(r_x8.block_errno, EOPNOTSUPP_ERRNO_PHASE378)

        r_af = verify_antidust_focusmag_guard(request_fx6_af_in_focus_mag=True)
        self.assertFalse(r_af.valid)
        self.assertEqual(r_af.block_errno, EOPNOTSUPP_ERRNO_PHASE378)

    def test_44_g161_fx6_blocks_sdi_or_internal_rec_crop_and_mismatched_target_ratio(self) -> None:
        r_sdi = verify_antidust_focusmag_guard(
            claim_fx6_sdi_or_internal_rec_cropped=True
        )
        self.assertFalse(r_sdi.valid)
        self.assertEqual(r_sdi.block_errno, EINVAL_ERRNO_PHASE378)

        r_mis = verify_antidust_focusmag_guard(
            fx6_focus_mag_target="HDMI", fx6_focus_mag_ratio="x6.0"
        )
        self.assertFalse(r_mis.valid)
        self.assertEqual(r_mis.block_errno, EINVAL_ERRNO_PHASE378)

    def test_45_g161_telemetry_rejects_bad_identity_and_non_bools(self) -> None:
        r1 = verify_antidust_focusmag_guard(body_model_name="ILME-FX6")
        r2 = verify_antidust_focusmag_guard(np_fz100_soc_pct=150)
        r3 = verify_antidust_focusmag_guard(focus_magnifier_active="yes")  # type: ignore[arg-type]
        for r in (r1, r2, r3):
            self.assertFalse(r.valid)
            self.assertEqual(r.status, STATUS_BLOCKED_G161_TELEMETRY_INVALID)

    def test_46_g161_hdmi_info_on_emits_warning_while_keeping_zero_rec_crop(self) -> None:
        res = verify_antidust_focusmag_guard(
            hdmi_info_display="On",
            focus_magnifier_active=True,
        )
        self.assertTrue(res.valid)
        self.assertFalse(res.internal_recording_cropped)
        self.assertTrue(len(res.warnings) >= 1)

    def test_47_g161_384_state_matrix_invariants(self) -> None:
        mat = compute_antidust_focusmag_matrix()
        self.assertEqual(mat["total_states"], 384)
        self.assertTrue(mat["open_shutter_all_verified"])
        self.assertTrue(mat["zero_internal_crop_all_verified"])
        self.assertEqual(mat["zero_clean_hdmi_crop_count"], 192)
        self.assertTrue(mat["rec_continuity_all_verified"])
        self.assertEqual(mat["cleaning_blocked_below51_count"], 192)
        self.assertTrue(mat["still_only_af_all_verified"])
        self.assertEqual(mat["suppressed_active_count"], 192)
        self.assertEqual(mat["camset_reset_immune_count"], 192)

    def test_48_g161_evaluate_with_audit_wrapper_and_alias(self) -> None:
        v1, r1 = evaluate_g161_antidust_focusmag_guard(
            repo_root=REPO_ROOT, force_clean_room=True
        )
        v2, r2 = verify_antidust_focusmag_guard_with_audit(
            repo_root=REPO_ROOT, force_clean_room=True
        )
        self.assertTrue(v1.passed)
        self.assertTrue(r1.valid)
        self.assertEqual(v1.gate_id, G161)
        self.assertEqual(r1.status, r2.status)
        self.assertFalse(r1.persistent_emmc_writes_authorized)
        self.assertFalse(r1.cross_model_flash_authorized)
        self.assertEqual(r1.raw_firmware_bytes_leaked, 0)

    # ------------------------------------------------------------------
    # Gate G162: Exposure Std. Adjust (5 Modes, 13 Steps, Reset-Immune) (49..66)
    # ------------------------------------------------------------------

    def test_49_g162_default_safe_baseline_passes(self) -> None:
        res = verify_expstd_usbtether_guard()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_VERIFIED_G162)
        self.assertEqual(res.block_errno, 0)
        self.assertEqual(res.slot1_writes, 0)
        self.assertEqual(res.usb_tx, 0)
        self.assertFalse(res.cross_model_flash_authorized)
        self.assertFalse(res.live_attach_authorized)
        self.assertEqual(res.rf_tx_packets, 0)
        self.assertTrue(res.zero_rf_tethering_bypass_active)

    def test_50_g162_all_5_metering_modes_and_all_13_sixth_ev_steps_valid(self) -> None:
        for mm in EXACT_5_METERING_MODES_G162:
            for s in range(EXPOSURE_STD_MIN_SIXTHS_G162, EXPOSURE_STD_MAX_SIXTHS_G162 + 1):
                res = verify_expstd_usbtether_guard(
                    metering_mode=mm,
                    exposure_std_sixths=s,
                )
                self.assertTrue(res.valid, f"Failed {mm} {s}/6 EV: {res.errors}")
                self.assertEqual(res.effective_exposure_std_sixths, s)
                self.assertEqual(res.metering_warning_icon_shown, s != 0)
                self.assertFalse(res.alters_exif_exposure_bias_value)
                self.assertEqual(res.exif_exposure_bias_delta_ev, 0.0)

    def test_51_g162_exposure_std_out_of_range_blocked(self) -> None:
        for bad_s in (-7, 7, -12, 12):
            res = verify_expstd_usbtether_guard(exposure_std_sixths=bad_s)
            self.assertFalse(res.valid)
            self.assertEqual(res.block_errno, EINVAL_ERRNO_PHASE378)
            self.assertEqual(
                res.status,
                STATUS_BLOCKED_G162_EXPSTD_EXIF_RESET_OR_ZERORF_AIRPLANE_VIOLATION,
            )

    def test_52_g162_dormant_step_1_8_ev_rejected_eopnotsupp(self) -> None:
        res = verify_expstd_usbtether_guard(request_dormant_step_1_8_ev=True)
        self.assertFalse(res.valid)
        self.assertEqual(res.block_errno, EOPNOTSUPP_ERRNO_PHASE378)
        self.assertEqual(
            res.status,
            STATUS_BLOCKED_G162_DORMANT_NOUVC_IAP2_MC_OR_STEP18_EOPNOTSUPP,
        )

    def test_53_g162_exposure_std_resists_camset_reset_and_zeroes_only_on_init(self) -> None:
        r_rst = verify_expstd_usbtether_guard(
            metering_mode="Spot",
            exposure_std_sixths=-3,
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE378,
        )
        self.assertTrue(r_rst.valid)
        self.assertEqual(r_rst.effective_exposure_std_sixths, -3)
        self.assertEqual(r_rst.mm_zero_point_shifted_ev, -0.5)
        self.assertEqual(r_rst.spot_ael_baseline_shifted_ev, -0.5)
        self.assertTrue(r_rst.metering_warning_icon_shown)

        r_init = verify_expstd_usbtether_guard(
            metering_mode="Spot",
            exposure_std_sixths=-3,
            reset_action=RESET_ACTION_INITIALIZE_PHASE378,
        )
        self.assertTrue(r_init.valid)
        self.assertEqual(r_init.effective_exposure_std_sixths, 0)
        self.assertFalse(r_init.metering_warning_icon_shown)

    def test_54_g162_blocks_claim_camset_reset_zeroes_exp_std(self) -> None:
        res = verify_expstd_usbtether_guard(
            exposure_std_sixths=2,
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE378,
            claim_camset_reset_zeroes_exp_std=True,
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.block_errno, EINVAL_ERRNO_PHASE378)

    def test_55_g162_blocks_claim_exp_std_alters_exif_exposure_bias_value(self) -> None:
        res = verify_expstd_usbtether_guard(
            exposure_std_sixths=3,
            claim_exp_std_alters_exif_bias=True,
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.block_errno, EINVAL_ERRNO_PHASE378)

    def test_56_g162_mid_bracket_alteration_resets_bracket_count(self) -> None:
        r_ok = verify_expstd_usbtether_guard(
            exposure_std_sixths=2,
            altered_mid_bracket=True,
        )
        self.assertTrue(r_ok.valid)
        self.assertTrue(r_ok.bracket_count_reset_triggered)

        r_bad = verify_expstd_usbtether_guard(
            exposure_std_sixths=2,
            altered_mid_bracket=True,
            claim_bracket_count_preserved_on_change=True,
        )
        self.assertFalse(r_bad.valid)
        self.assertEqual(r_bad.block_errno, EINVAL_ERRNO_PHASE378)

    def test_57_g162_cine_ei_vs_flexible_iso_auto_exposure_impact(self) -> None:
        r_ei = verify_expstd_usbtether_guard(
            exposure_std_sixths=3,
            exposure_control_mode="Cine_EI",
        )
        self.assertTrue(r_ei.valid)
        self.assertFalse(r_ei.alters_actual_auto_exposure)
        self.assertEqual(r_ei.mm_zero_point_shifted_ev, 0.5)

        r_flex = verify_expstd_usbtether_guard(
            exposure_std_sixths=3,
            exposure_control_mode="Flexible_ISO_AUTO",
        )
        self.assertTrue(r_flex.valid)
        self.assertTrue(r_flex.alters_actual_auto_exposure)

    def test_58_g162_fx6_ae_level_25_steps_pm3_0_debunks_pm2_0_myth(self) -> None:
        for idx in range(-12, 13):
            ev = idx * 0.25
            res = verify_expstd_usbtether_guard(fx6_ae_level_ev=ev)
            self.assertTrue(res.valid, f"FX6 AE Level {ev} failed: {res.errors}")
            self.assertEqual(res.fx6_ae_level_step_count, 25)
            self.assertTrue(res.fx6_per_lut_ae_level_offset_supported)

        r_myth = verify_expstd_usbtether_guard(claim_fx6_ae_level_capped_at_2ev=True)
        self.assertFalse(r_myth.valid)
        self.assertEqual(r_myth.block_errno, EINVAL_ERRNO_PHASE378)

    def test_59_g162_fx6_ae_level_rejects_out_of_range_or_bad_step(self) -> None:
        r1 = verify_expstd_usbtether_guard(fx6_ae_level_ev=3.25)
        r2 = verify_expstd_usbtether_guard(fx6_ae_level_ev=-3.25)
        r3 = verify_expstd_usbtether_guard(fx6_ae_level_ev=0.10)
        for r in (r1, r2, r3):
            self.assertFalse(r.valid)
            self.assertEqual(r.block_errno, EINVAL_ERRNO_PHASE378)

    def test_60_g162_fx6_ae_modes_and_speed_bounds(self) -> None:
        for mode in ALLOWED_FX6_AE_MODES_G162:
            res = verify_expstd_usbtether_guard(fx6_ae_mode=mode, fx6_ae_speed=-99)
            self.assertTrue(res.valid)
        r_bad = verify_expstd_usbtether_guard(fx6_ae_speed=100)
        self.assertFalse(r_bad.valid)
        self.assertEqual(r_bad.status, STATUS_BLOCKED_G162_TELEMETRY_INVALID)

    # ------------------------------------------------------------------
    # Gate G162: USB Tethering, Zero-RF Airplane, M&C, iAP2 & Slot 1 EROFS (61..84)
    # ------------------------------------------------------------------

    def test_61_g162_all_4_usb_tethering_drivers_and_zero_rf_workloads_valid(self) -> None:
        for drv in ALLOWED_USB_TETHERING_DRIVERS_G162:
            for wl in ("rtmp", "rtmps", "srt", "ftp", "ftpes", "sftp"):
                res = verify_expstd_usbtether_guard(
                    usb_tethering_active=True,
                    usb_tethering_driver=drv,
                    tethering_workload=wl,
                    airplane_mode="On",
                )
                self.assertTrue(res.valid, f"{drv}/{wl}: {res.errors}")
                self.assertTrue(res.zero_rf_tethering_bypass_active)
                self.assertEqual(res.rf_tx_packets, 0)
                self.assertFalse(res.wifi_bt_radio_enabled)

    def test_62_g162_blocks_airplane_mode_off_rf_leak_on_bench(self) -> None:
        res = verify_expstd_usbtether_guard(airplane_mode="Off")
        self.assertFalse(res.valid)
        self.assertEqual(res.block_errno, EINVAL_ERRNO_PHASE378)
        self.assertTrue(res.wifi_bt_radio_enabled)

    def test_63_g162_reset_network_set_requires_airplane_mode_rearm(self) -> None:
        r_unarmed = verify_expstd_usbtether_guard(
            reset_network_set_executed=True,
            airplane_mode_rearmed_after_net_reset=False,
        )
        self.assertFalse(r_unarmed.valid)
        self.assertEqual(r_unarmed.block_errno, EINVAL_ERRNO_PHASE378)

        r_rearmed = verify_expstd_usbtether_guard(
            reset_network_set_executed=True,
            airplane_mode_rearmed_after_net_reset=True,
        )
        self.assertTrue(r_rearmed.valid)
        self.assertEqual(r_rearmed.rf_tx_packets, 0)

    def test_64_g162_usb_lan_cnct_launch_ver7_valid_but_blocked_below_ver7(self) -> None:
        r_ok = verify_expstd_usbtether_guard(
            firmware_version="7.02", usb_lan_cnct_launch="On"
        )
        self.assertTrue(r_ok.valid)

        r_old = verify_expstd_usbtether_guard(
            firmware_version="6.02", usb_lan_cnct_launch="On"
        )
        self.assertFalse(r_old.valid)
        self.assertEqual(r_old.block_errno, EOPNOTSUPP_ERRNO_PHASE378)

    def test_65_g162_blocks_dormant_nouvc_usb_streaming_eopnotsupp(self) -> None:
        res = verify_expstd_usbtether_guard(
            usb_connection_mode=DORMANT_USB_STREAMING_MODE_G162
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.block_errno, EOPNOTSUPP_ERRNO_PHASE378)

    def test_66_g162_blocks_creators_app_usb_live_streaming_eopnotsupp(self) -> None:
        res = verify_expstd_usbtether_guard(
            tethering_workload="creators_app_usb_streaming"
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.block_errno, EOPNOTSUPP_ERRNO_PHASE378)

    def test_67_g162_blocks_dual_usb_ports_simultaneous_ebusy(self) -> None:
        res = verify_expstd_usbtether_guard(dual_usb_ports_simultaneous=True)
        self.assertFalse(res.valid)
        self.assertEqual(res.block_errno, EBUSY_ERRNO_PHASE378)
        self.assertEqual(
            res.status, STATUS_BLOCKED_G162_DUAL_USB_PORT_OR_FX6_LAN_MUTEX_EBUSY
        )

    def test_68_g162_blocks_fx6_wired_lan_or_pc_usb_mutex_ebusy(self) -> None:
        res = verify_expstd_usbtether_guard(fx6_wired_lan_or_pc_usb_simultaneous=True)
        self.assertFalse(res.valid)
        self.assertEqual(res.block_errno, EBUSY_ERRNO_PHASE378)

    def test_69_g162_blocks_fx3_stripped_cusbgadgetiap_eopnotsupp(self) -> None:
        res = verify_expstd_usbtether_guard(request_fx3_iap2_gadget=True)
        self.assertFalse(res.valid)
        self.assertEqual(res.block_errno, EOPNOTSUPP_ERRNO_PHASE378)
        self.assertEqual(res.fx3_usbg_iap_class_hits, 0)
        self.assertTrue(res.fx6_usbg_iap_class_active)

    def test_70_g162_blocks_monitor_and_control_usb_tc_focusmap_lut_eopnotsupp(self) -> None:
        for kw in (
            {"request_mc_usb_timecode": True},
            {"request_mc_usb_focus_map": True},
            {"request_mc_usb_lut_import": True},
        ):
            res = verify_expstd_usbtether_guard(
                tethering_workload="monitor_and_control_usb", **kw
            )
            self.assertFalse(res.valid, str(kw))
            self.assertEqual(res.block_errno, EOPNOTSUPP_ERRNO_PHASE378)

    def test_71_g162_monitor_and_control_usb_basic_remote_shooting_allowed(self) -> None:
        res = verify_expstd_usbtether_guard(
            usb_connection_mode="Remote Shooting",
            tethering_workload="monitor_and_control_usb",
        )
        self.assertTrue(res.valid)
        self.assertFalse(res.mc_usb_timecode_supported)
        self.assertFalse(res.mc_usb_focus_map_supported)
        self.assertFalse(res.mc_usb_lut_import_supported)

    def test_72_g162_blocks_fx6_usb_hub_attached_eopnotsupp(self) -> None:
        res = verify_expstd_usbtether_guard(fx6_usb_hub_attached=True)
        self.assertFalse(res.valid)
        self.assertEqual(res.block_errno, EOPNOTSUPP_ERRNO_PHASE378)

    def test_73_g162_slot1_mtp_writable_blocked_erofs30(self) -> None:
        res = verify_expstd_usbtether_guard(
            usb_connection_mode="MTP",
            target_media_slot=MEDIA_SLOT_1_PHASE378,
            host_storage_access_mode="host_writable",
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.block_errno, EROFS_ERRNO_PHASE378)
        self.assertEqual(res.status, STATUS_BLOCKED_G162_SLOT1_MSC_MTP_WRITABLE_EROFS)
        self.assertEqual(res.slot1_writes, 0)
        self.assertEqual(res.usb_tx, 0)

    def test_74_g162_slot1_msc_multi_lun_writable_blocked_erofs30(self) -> None:
        res = verify_expstd_usbtether_guard(
            usb_connection_mode="MassStorage(MSC)",
            usb_lun_setting="Multi",
            host_storage_access_mode="host_writable",
            usbgmsc_readonly_enforced=False,
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.block_errno, EROFS_ERRNO_PHASE378)
        self.assertEqual(res.slot1_writes, 0)

    def test_75_g162_slot1_msc_single_lun_writable_blocked_erofs30(self) -> None:
        res = verify_expstd_usbtether_guard(
            usb_connection_mode="MassStorage(MSC)",
            usb_lun_setting="Single",
            host_storage_access_mode="host_writable",
            usbgmsc_readonly_enforced=False,
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.block_errno, EROFS_ERRNO_PHASE378)
        self.assertEqual(res.slot1_writes, 0)

    def test_76_g162_slot1_msc_readonly_guarded_allowed_zero_writes(self) -> None:
        res = verify_expstd_usbtether_guard(
            usb_connection_mode="MassStorage(MSC)",
            usb_lun_setting="Single",
            target_media_slot=MEDIA_SLOT_NONE_PHASE378,
            host_storage_access_mode="read_only_guarded",
            usbgmsc_readonly_enforced=True,
        )
        self.assertTrue(res.valid)
        self.assertFalse(res.slot1_exposed_writable)
        self.assertEqual(res.slot1_writes, 0)

    def test_77_g162_slot1_direct_host_writable_blocked_erofs30(self) -> None:
        res = verify_expstd_usbtether_guard(
            usb_connection_mode="Sel. When Connect",
            target_media_slot=MEDIA_SLOT_1_PHASE378,
            host_storage_access_mode="host_writable",
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.block_errno, EROFS_ERRNO_PHASE378)

    def test_78_g162_slot2_non_tier0_target_does_not_trigger_slot1_erofs(self) -> None:
        res = verify_expstd_usbtether_guard(
            usb_connection_mode="Remote Shooting",
            target_media_slot=MEDIA_SLOT_2_PHASE378,
            host_storage_access_mode="none",
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.slot1_writes, 0)

    def test_79_g162_erofs_takes_priority_over_ebusy_and_eopnotsupp(self) -> None:
        res = verify_expstd_usbtether_guard(
            usb_connection_mode="MassStorage(MSC)",
            host_storage_access_mode="host_writable",
            dual_usb_ports_simultaneous=True,
            request_fx3_iap2_gadget=True,
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.block_errno, EROFS_ERRNO_PHASE378)

    def test_80_g162_telemetry_rejects_invalid_enums_and_types(self) -> None:
        r1 = verify_expstd_usbtether_guard(metering_mode="Matrix")
        r2 = verify_expstd_usbtether_guard(usb_tethering_driver="usb_bad")
        r3 = verify_expstd_usbtether_guard(target_media_slot=9)
        r4 = verify_expstd_usbtether_guard(exposure_std_sixths=True)  # type: ignore[arg-type]
        for r in (r1, r2, r3, r4):
            self.assertFalse(r.valid)
            self.assertEqual(r.status, STATUS_BLOCKED_G162_TELEMETRY_INVALID)

    def test_81_g162_480_state_matrix_invariants(self) -> None:
        mat = compute_expstd_usbtether_matrix()
        self.assertEqual(mat["total_states"], 480)
        self.assertTrue(mat["zero_exif_delta_all_verified"])
        self.assertEqual(mat["camset_reset_survived_count"], 120)
        self.assertEqual(mat["initialize_zeroed_count"], 160)
        self.assertEqual(mat["slot1_msc_mtp_writable_detected"], 240)
        self.assertTrue(mat["zero_rf_tether_all_verified"])

    def test_82_g162_evaluate_with_audit_wrapper_and_alias(self) -> None:
        v1, r1 = evaluate_g162_expstd_usbtether_guard(
            repo_root=REPO_ROOT, force_clean_room=True
        )
        v2, r2 = verify_expstd_usbtether_guard_with_audit(
            repo_root=REPO_ROOT, force_clean_room=True
        )
        self.assertTrue(v1.passed)
        self.assertTrue(r1.valid)
        self.assertEqual(v1.gate_id, G162)
        self.assertEqual(r1.status, r2.status)
        self.assertFalse(r1.persistent_emmc_writes_authorized)
        self.assertFalse(r1.cross_model_flash_authorized)
        self.assertFalse(r1.hardware_live_attachment_authorized)

    def test_83_g162_resolve_state_handles_all_exposure_control_modes(self) -> None:
        for mode in ALLOWED_EXPOSURE_CONTROL_MODES_G162:
            st = resolve_fx3_expstd_usbtether_state(
                exposure_std_sixths=-2, exposure_control_mode=mode
            )
            expected_ae = mode in ("P_A_S", "M_ISO_AUTO", "Flexible_ISO_AUTO")
            self.assertEqual(st["alters_actual_auto_exposure"], expected_ae, mode)

    def test_84_g162_non_zero_exp_std_emits_operator_trap_warning(self) -> None:
        res = verify_expstd_usbtether_guard(exposure_std_sixths=-1)
        self.assertTrue(res.valid)
        self.assertTrue(any("Camera Settings Reset" in w for w in res.warnings))

    # ------------------------------------------------------------------
    # Unified 162-Gate Master Preflight, 4-Mode & Redline Tests (85..100)
    # ------------------------------------------------------------------

    def test_85_master_162gate_offline_nogo_159_of_162_clean_room(self) -> None:
        rep = evaluate_162gate_preflight(REPO_ROOT, force_clean_room=True)
        self.assertIsInstance(rep, Master162GateReport)
        self.assertEqual(rep.schema_version, REALHW_162GATE_PREFLIGHT_SCHEMA)
        self.assertEqual(rep.status, "VERIFIED_159_OF_162_AWAITING_PHYSICAL_TIER0")
        self.assertEqual(rep.summary["total_gates"], 162)
        self.assertEqual(rep.summary["verified_gates"], 159)
        self.assertEqual(rep.summary["blocked_or_pending_gates"], 3)
        self.assertEqual(len(rep.gates), 162)
        self.assertTrue(rep.offline_159_gates_verified)
        self.assertFalse(rep.all_162_gates_verified)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.hardware_live_attachment_authorized)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.cross_model_flash_authorized)
        self.assertEqual(rep.usb_packets_transmitted, 0)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_86_master_162gate_simulated_dry_run_162_of_162_clean_room(self) -> None:
        rep = evaluate_162gate_preflight(
            REPO_ROOT, force_clean_room=True, dry_run_simulated=True
        )
        self.assertEqual(rep.status, "VERIFIED_ALL_162_GATES_DRY_RUN_SIMULATED_BACKUP")
        self.assertEqual(rep.summary["verified_gates"], 162)
        self.assertTrue(rep.all_162_gates_verified)
        self.assertTrue(rep.dry_run_rehearsal_only)
        self.assertTrue(rep.g161_to_g162_all_passed)
        self.assertTrue(rep.g13_to_g162_all_passed)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.hardware_live_attachment_authorized)
        self.assertFalse(rep.cross_model_flash_authorized)
        self.assertEqual(rep.usb_packets_transmitted, 0)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_87_master_162gate_normal_mode_local_donor_or_fallback(self) -> None:
        with mock.patch.dict(
            os.environ,
            {"FX3_FX6_FORCE_CLEAN_ROOM": "", ENV_CLEAN_ROOM_TEST_PHASE378: ""},
            clear=False,
        ):
            rep = evaluate_162gate_preflight(REPO_ROOT)
        self.assertEqual(rep.summary["verified_gates"], 159)
        self.assertTrue(rep.offline_159_gates_verified)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_88_master_162gate_fx3_clean_room_test_env_mode(self) -> None:
        with mock.patch.dict(
            os.environ,
            {ENV_CLEAN_ROOM_TEST_PHASE378: "1", "FX3_FX6_FORCE_CLEAN_ROOM": ""},
            clear=False,
        ):
            rep = evaluate_162gate_preflight(REPO_ROOT)
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(rep.summary["verified_gates"], 159)

    def test_89_master_162gate_work_root_none_donorless_fallback(self) -> None:
        with mock.patch(
            "fx3_safety.realhw_antidust_focusmag_expstd_usbtether_and_162gate_guard.resolve_donor_thermal_power_paths",
            side_effect=_mock_paths_work_root_none,
        ):
            with mock.patch.dict(
                os.environ,
                {"FX3_FX6_FORCE_CLEAN_ROOM": "", ENV_CLEAN_ROOM_TEST_PHASE378: ""},
                clear=False,
            ):
                rep = evaluate_162gate_preflight(REPO_ROOT)
        self.assertEqual(rep.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(rep.summary["verified_gates"], 159)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_90_master_162gate_aliases_return_equivalent_reports(self) -> None:
        base_m160 = fx3_safety.evaluate_160gate_preflight(
            REPO_ROOT, force_clean_room=True
        )
        r1 = evaluate_162_master_safety_gates(
            REPO_ROOT, force_clean_room=True, master_160_override=base_m160
        )
        r2 = run_162_gate_preflight(
            REPO_ROOT, force_clean_room=True, master_160_override=base_m160
        )
        r3 = verify_real_hardware_162gate_readiness(
            REPO_ROOT, force_clean_room=True, master_160_override=base_m160
        )
        self.assertEqual(r1.status, r2.status)
        self.assertEqual(r2.status, r3.status)
        self.assertEqual(r3.summary["total_gates"], 162)

    def test_91_master_162gate_blocks_g161_failure_propagation(self) -> None:
        base_m160 = fx3_safety.evaluate_160gate_preflight(
            REPO_ROOT, force_clean_room=True
        )
        rep = evaluate_162gate_preflight(
            REPO_ROOT,
            force_clean_room=True,
            master_160_override=base_m160,
            antidust_focusmag_kwargs={"request_dormant_shutter_when_pwr_off": True},
        )
        self.assertFalse(rep.g161_to_g162_all_passed)
        self.assertFalse(rep.offline_159_gates_verified)
        self.assertEqual(
            rep.status,
            STATUS_BLOCKED_G161_DORMANT_ANTIDUST_HIGHMP_RATIO_STILLONLY_OR_FX6_EOPNOTSUPP,
        )
        self.assertEqual(rep.summary["verified_gates"], 158)

    def test_92_master_162gate_blocks_g162_slot1_erofs_propagation(self) -> None:
        base_m160 = fx3_safety.evaluate_160gate_preflight(
            REPO_ROOT, force_clean_room=True
        )
        rep = evaluate_162gate_preflight(
            REPO_ROOT,
            force_clean_room=True,
            master_160_override=base_m160,
            expstd_usbtether_kwargs={
                "usb_connection_mode": "MTP",
                "target_media_slot": MEDIA_SLOT_1_PHASE378,
                "host_storage_access_mode": "host_writable",
            },
        )
        self.assertFalse(rep.g161_to_g162_all_passed)
        self.assertFalse(rep.offline_159_gates_verified)
        self.assertEqual(rep.status, STATUS_BLOCKED_G162_SLOT1_MSC_MTP_WRITABLE_EROFS)
        self.assertEqual(rep.summary["verified_gates"], 158)

    def test_93_master_162gate_blocks_persistent_emmc_write_request(self) -> None:
        base_m160 = fx3_safety.evaluate_160gate_preflight(
            REPO_ROOT, force_clean_room=True
        )
        rep = evaluate_162gate_preflight(
            REPO_ROOT,
            force_clean_room=True,
            master_160_override=base_m160,
            request_persistent_emmc_writes=True,
        )
        self.assertEqual(rep.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        self.assertFalse(rep.offline_159_gates_verified)
        self.assertFalse(rep.all_162_gates_verified)
        self.assertFalse(rep.h0_h1_trial_entry_allowed)
        self.assertFalse(rep.persistent_emmc_writes_authorized)

    def test_94_master_162gate_gate_ids_contiguous_g01_to_g162(self) -> None:
        base_m160 = fx3_safety.evaluate_160gate_preflight(
            REPO_ROOT, force_clean_room=True
        )
        rep = evaluate_162gate_preflight(
            REPO_ROOT, force_clean_room=True, master_160_override=base_m160
        )
        ids = [g["gate_id"] for g in rep.gates]
        self.assertEqual(len(ids), 162)
        self.assertEqual(ids[-2], G161)
        self.assertEqual(ids[-1], G162)
        self.assertEqual(len(set(ids)), 162)

    def test_95_master_162gate_simulate_bench_dry_run_kwarg_alias(self) -> None:
        base_m160_sim = fx3_safety.evaluate_160gate_preflight(
            REPO_ROOT, force_clean_room=True, dry_run_simulated=True
        )
        rep = evaluate_162gate_preflight(
            REPO_ROOT,
            force_clean_room=True,
            simulate_bench_dry_run=True,
            master_160_override=base_m160_sim,
        )
        self.assertTrue(rep.all_162_gates_verified)
        self.assertTrue(rep.dry_run_rehearsal_only)
        self.assertEqual(rep.summary["verified_gates"], 162)

    def test_96_master_162gate_json_serializable_no_raw_bytes(self) -> None:
        base_m160 = fx3_safety.evaluate_160gate_preflight(
            REPO_ROOT, force_clean_room=True
        )
        rep = evaluate_162gate_preflight(
            REPO_ROOT, force_clean_room=True, master_160_override=base_m160
        )
        encoded = json.dumps(rep.to_dict(), ensure_ascii=False)
        parsed = json.loads(encoded)
        self.assertEqual(parsed["summary"]["total_gates"], 162)
        self.assertEqual(parsed["raw_firmware_bytes_leaked"], 0)

    def test_97_package_exports_include_162gate_entrypoints(self) -> None:
        for sym in (
            "G161",
            "G162",
            "Master162GateReport",
            "evaluate_162gate_preflight",
            "evaluate_162_master_safety_gates",
            "run_162_gate_preflight",
            "verify_real_hardware_162gate_readiness",
            "evaluate_g161_antidust_focusmag_guard",
            "evaluate_g162_expstd_usbtether_guard",
            "verify_antidust_focusmag_guard",
            "verify_expstd_usbtether_guard",
            "audit_phase378_donor_contracts",
        ):
            self.assertTrue(hasattr(fx3_safety, sym), f"Missing export: {sym}")
            self.assertIn(sym, fx3_safety.__all__, f"Missing in __all__: {sym}")

    def test_98_module_cli_g161_and_g162_summary_and_json(self) -> None:
        for gate_arg in ("g161", "g162"):
            buf = StringIO()
            with redirect_stdout(buf):
                rc = guard_module_main(
                    ["--gate", gate_arg, "--force-clean-room", "--summary", "--json"]
                )
            self.assertEqual(rc, 0)
            payload = json.loads(buf.getvalue())
            self.assertTrue(payload["valid"])
            self.assertEqual(payload["raw_firmware_bytes_leaked"], 0)

    def test_99_module_cli_162_text_and_json_dry_run(self) -> None:
        buf = StringIO()
        with redirect_stdout(buf):
            rc = guard_module_main(
                [
                    "--gate",
                    "162",
                    "--force-clean-room",
                    "--simulate-bench-dry-run",
                    "--summary",
                    "--json",
                ]
            )
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["summary"]["verified_gates"], 162)
        self.assertEqual(
            payload["status"], "VERIFIED_ALL_162_GATES_DRY_RUN_SIMULATED_BACKUP"
        )

    def test_100_safety_cli_verify_g161_and_aliases(self) -> None:
        for subcmd in (
            "verify-antidust-focusmag-guard",
            "verify-g161-antidust-focusmag",
            "verify-g161",
        ):
            buf = StringIO()
            with redirect_stdout(buf):
                rc = safety_cli.main([subcmd, "--force-clean-room", "--summary", "--json"])
            self.assertEqual(rc, 0, subcmd)
            data = json.loads(buf.getvalue())
            self.assertEqual(data["gate"], G161)
            self.assertTrue(data["valid"])
            self.assertEqual(data["effective_power_off_shutter_state"], "OPEN")

    def test_101_safety_cli_verify_g162_and_aliases(self) -> None:
        for subcmd in (
            "verify-expstd-usbtether-guard",
            "verify-g162-expstd-usbtether",
            "verify-g162",
        ):
            buf = StringIO()
            with redirect_stdout(buf):
                rc = safety_cli.main([subcmd, "--force-clean-room", "--summary", "--json"])
            self.assertEqual(rc, 0, subcmd)
            data = json.loads(buf.getvalue())
            self.assertEqual(data["gate"], G162)
            self.assertTrue(data["valid"])
            self.assertEqual(data["rf_tx_packets"], 0)
            self.assertEqual(data["slot1_writes"], 0)

    def test_102_safety_cli_verify_162_gates_offline_text_and_json(self) -> None:
        buf_txt = StringIO()
        with redirect_stdout(buf_txt):
            rc = safety_cli.main(["verify-162-gates", "--force-clean-room"])
        self.assertEqual(rc, 0)
        out = buf_txt.getvalue()
        self.assertIn("verified=159/162", out)
        self.assertIn("overall_ready_for_hardware_attach=False", out)
        self.assertIn("raw_firmware_bytes_leaked=0", out)

        buf_json = StringIO()
        with redirect_stdout(buf_json):
            rc2 = safety_cli.main(
                ["verify-162-gates", "--force-clean-room", "--summary", "--json"]
            )
        self.assertEqual(rc2, 0)
        payload = json.loads(buf_json.getvalue())
        self.assertEqual(payload["summary"]["verified_gates"], 159)
        self.assertEqual(payload["g161_status"], STATUS_VERIFIED_G161)
        self.assertEqual(payload["g162_status"], STATUS_VERIFIED_G162)

    def test_103_safety_cli_verify_162_gates_dry_run_162_of_162(self) -> None:
        buf = StringIO()
        with redirect_stdout(buf):
            rc = safety_cli.main(
                [
                    "verify-162-gates",
                    "--force-clean-room",
                    "--simulate-bench-dry-run",
                    "--summary",
                    "--json",
                ]
            )
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["summary"]["verified_gates"], 162)
        self.assertTrue(payload["summary"]["all_162_gates_verified"])
        self.assertFalse(payload["summary"]["overall_ready_for_hardware_attach"])
        self.assertFalse(payload["summary"]["cross_model_flash_authorized"])
        self.assertEqual(payload["summary"]["usb_packets_transmitted"], 0)

    def test_104_readme_documents_phase378_162_gates_and_cli(self) -> None:
        readme_text = (SAFETY_ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("Phase 378", readme_text)
        self.assertIn("verify-162-gates", readme_text)
        self.assertIn("G161", readme_text)
        self.assertIn("G162", readme_text)
        self.assertIn("162/162", readme_text)

    def test_105_uxc_resid16_anchors_and_menu_paths_match_wave71(self) -> None:
        self.assertEqual(DORMANT_ANTIDUST_FUNCTION_F_RESID16_G161, 0x7495)
        self.assertEqual(DORMANT_SHUTTER_WHEN_PWR_OFF_F_RESID16_G161, 0x709F)
        self.assertEqual(SENSOR_CLEANING_F_RESID16_G161, 0x67D6)
        self.assertEqual(
            SENSOR_CLEANING_MENU_PATH_G161,
            "Setup -> [Setup Option] -> [Sensor Cleaning]",
        )
        self.assertEqual(
            FOCUS_ASSISTANT_MENU_PATH_G161,
            "Shooting -> [Focus] -> [Focus Assistant]",
        )
        self.assertEqual(
            EXPOSURE_STD_ADJUST_MENU_PATH_G162,
            "Exposure/Color -> [Exposure Comp.] -> [Exposure Std. Adjust]",
        )
        self.assertEqual(
            USB_CONNECTION_MODE_MENU_PATH_G162,
            "Setup -> [USB] -> [USB Connection Mode]",
        )
        self.assertEqual(
            USB_LAN_TETHERING_MENU_PATH_G162, "Network -> [USB-LAN/Tethering]"
        )

    def test_106_fx3_vs_fx6_contrast_invariants_locked(self) -> None:
        self.assertEqual(FX6_SHUTTER_WHEN_PWR_OFF_ELF_HITS_G161, 0)
        self.assertFalse(FX6_FOCAL_PLANE_MECHANICAL_SHUTTER_PRESENT_G161)
        self.assertFalse(FX6_USER_IBIS_SENSOR_CLEANING_SUPPORTED_G161)
        self.assertTrue(FX3_AF_IN_FOCUS_MAG_STILL_ONLY_G161)
        self.assertTrue(FX3_AUTO_MAG_IN_MF_STILL_ONLY_G161)
        self.assertTrue(FX3_FOCUS_MAG_REC_CONTINUITY_SUPPORTED_G161)
        self.assertEqual(FX3_FOCUS_MAG_CLEAN_HDMI_CROP_PIXELS_G161, 0)
        self.assertEqual(FX3_FOCUS_MAG_INTERNAL_REC_CROP_PIXELS_G161, 0)
        self.assertEqual(len(DORMANT_ANTIDUST_SYMBOLS_G161), 7)
        self.assertEqual(len(FX3_FOCUS_MAG_COEXISTING_FEATURES_G161), 3)
        self.assertEqual(len(FX3_FOCUS_MAG_SUPPRESSED_FEATURES_G161), 3)
        self.assertEqual(len(ALLOWED_FX3_USB_CONNECTION_MODES_G162), 4)
        self.assertEqual(len(ALLOWED_USB_LUN_SETTINGS_G162), 2)
        self.assertTrue(FX3_USB_TETHERING_ZERO_RF_AIRPLANE_ALLOWED_G162)
        self.assertEqual(FX3_USB_TETHERING_RF_TX_PACKETS_AIRPLANE_G162, 0)
        self.assertFalse(FX3_MC_USB_TIMECODE_SUPPORTED_G162)
        self.assertFalse(FX3_MC_USB_FOCUS_MAP_SUPPORTED_G162)
        self.assertFalse(FX3_MC_USB_LUT_IMPORT_SUPPORTED_G162)

    def test_107_safety_cli_text_output_for_g161_and_g162(self) -> None:
        buf1 = StringIO()
        with redirect_stdout(buf1):
            rc1 = safety_cli.main(["verify-g161", "--force-clean-room"])
        self.assertEqual(rc1, 0)
        self.assertIn("gate=G161", buf1.getvalue())
        self.assertIn("shutter_pwroff=OPEN", buf1.getvalue())

        buf2 = StringIO()
        with redirect_stdout(buf2):
            rc2 = safety_cli.main(["verify-g162", "--force-clean-room"])
        self.assertEqual(rc2, 0)
        self.assertIn("gate=G162", buf2.getvalue())
        self.assertIn("rf_tx=0", buf2.getvalue())
        self.assertIn("s1_writes=0", buf2.getvalue())

    def test_108_no_pyc_artifacts_created_during_suite(self) -> None:
        pycache_dirs = list((SAFETY_ROOT / "fx3_safety").rglob("__pycache__")) + list(
            (SAFETY_ROOT / "tests").rglob("__pycache__")
        )
        pyc_files = [
            p
            for d in pycache_dirs
            for p in d.rglob("*.pyc")
            if "162gate" in p.name
        ]
        self.assertEqual(pyc_files, [])

    def test_109_cli_main_help_formatting_no_percent_error(self) -> None:
        for argv in (
            ["--help"],
            ["verify-g161", "--help"],
            ["verify-g162", "--help"],
            ["verify-162-gates", "--help"],
        ):
            buf = StringIO()
            with redirect_stdout(buf):
                with self.assertRaises(SystemExit) as cm:
                    safety_cli.main(argv)
            self.assertEqual(cm.exception.code, 0, argv)
            self.assertTrue(len(buf.getvalue()) > 20)


if __name__ == "__main__":
    unittest.main()
