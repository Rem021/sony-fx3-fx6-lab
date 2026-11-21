"""Comprehensive 4-mode test suite for Phase 373 (`160/160` Hardware Safety Gates, Wave-70 Milestone):
Gate G159 (`Shooting -> [Focus] -> [Peaking Display]` Clean-HDMI Isolation / `Focus Magnifier`
Compatibility / Anti-Camera-Reset / Dormant In-Body `[Focus Map]` vs FX6 `Monitoring > Peaking`
`B&W` & Zero `Peaking Type/Freq`, plus Ver. 2.00..7.02 `[Audio Level Display]` Removal / Exact
5-Item `Shooting -> [Audio Recording]` / Built-In-Only `[Wind Noise Reduct.]` No `Auto` / 3-Tier
Audio Preemption vs FX6 Physical Dials, Menu `CH1..CH4 Wind Filter` & 6-Step `Limiter Mode`),
Gate G160 (`Setup -> [USB] -> [USB Power Supply]` Type-C Only, `9V/3A` PD vs `5V/1.5A`, Mandatory
Charged `NP-FZ100` / Zero Hot-Swap, ON-No-Charge vs OFF-Charge `10-30C`, `DC-C1` `>=65W/5A` vs
FX6 `19.5V` EIAJ `DC IN` & Hot-Replug Reboot Hazard, plus `[NTSC/PAL Selector]` `J1/CE/E33/U2`
SKU Locks, Ver. 7.02 Pure-XAVC Reboot Without Mandatory Format, Cross-Standard Playback Isolation,
and Tier-0 `Slot 1` `EROFS=30` Firewall for `AVF_INFO` Create/Update/Recover/Format vs FX6
`Project > Rec Format > Frequency` & `Thumbnail` Filter),
and Unified `160`-Gate Master Safety Preflight (`G01..G160`).
"""

from __future__ import annotations

import ast
from contextlib import redirect_stdout
import hashlib
from io import StringIO
import json
import os
from pathlib import Path
import subprocess
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
from fx3_safety.realhw_peaking_audio_wind_usbpd_ntscpal_and_160gate_guard import (  # noqa: E402
    AUDIO_LEVEL_DISPLAY_MENU_REMOVED_VER2_PLUS_G159,
    AUDIO_OUT_TIMING_DEFAULT_G159,
    AUDIO_RECORDING_DEFAULT_G159,
    AUDIO_RECORDING_MENU_PATH_G159,
    AUDIO_REC_LEVEL_DEFAULT_G159,
    AUDIO_REC_LEVEL_ELF_TYPO_G159,
    AUDIO_REC_LEVEL_MAX_G159,
    AUDIO_REC_LEVEL_MIN_G159,
    CHARGE_TEMP_MAX_C_G160,
    CHARGE_TEMP_MIN_C_G160,
    CROSS_STANDARD_PLAYBACK_ALLOWED_G160,
    DC_C1_MIN_CABLE_AMPS_G160,
    DC_C1_MIN_PD_WATTS_G160,
    DC_C1_MONITOR_BRIGHTNESS_LOCKED_MAX_G160,
    DONOR_CHECK_MAX_SECONDS_PHASE373,
    EBUSY_ERRNO_PHASE373,
    EINVAL_ERRNO_PHASE373,
    ENV_CLEAN_ROOM_TEST_PHASE373,
    EOPNOTSUPP_ERRNO_PHASE373,
    EROFS_ERRNO_PHASE373,
    EXACT_3_FX3_PEAKING_ITEMS_G159,
    EXACT_3_FX6_PEAKING_ITEMS_G159,
    EXACT_5_FX3_AUDIO_RECORDING_ITEMS_G159,
    EXACT_6_FX6_LIMITER_MODES_G159,
    EXACT_6_FX6_SYSTEM_FREQUENCIES_G160,
    FX3_AUDIO_5ITEMS_RESETTABLE_BY_CAMSET_RESET_G159,
    FX3_AUDIO_LIMITER_PERMANENT_NON_DISABLEABLE_G159,
    FX3_AUDIO_PREEMPTION_TIERS_G159,
    FX3_BATTERY_HOT_SWAP_SUPPORTED_G160,
    FX3_BATTERY_LESS_USB_BOOT_SUPPORTED_G160,
    FX3_CHARGES_WHILE_CAMERA_ON_G160,
    FX3_DEFAULT_FW_VERSION_PHASE373,
    FX3_HDMI_PEAKING_LEAKED_PIXELS_G159,
    FX3_HELP_GUIDE_CODE_PHASE373,
    FX3_INBODY_FOCUS_MAP_EXPOSED_G159,
    FX3_MODEL_ID_PHASE373,
    FX3_MODEL_NAME_PHASE373,
    FX3_PEAKING_COMPATIBLE_WITH_FOCUS_MAGNIFIER_G159,
    FX3_PEAKING_EMITTED_OVER_HDMI_G159,
    FX3_PEAKING_RESETTABLE_BY_CAMSET_RESET_G159,
    FX3_WIND_NOISE_AUTO_EXPOSED_G159,
    FX6_BATTERY_LESS_BOOT_SUPPORTED_G160,
    FX6_DC_IN_NOMINAL_V_G160,
    FX6_DC_UNPLUG_TO_BPU_SEAMLESS_G160,
    FX6_HANDLE_HW_LOW_CUT_SWITCH_PRESENT_G159,
    FX6_PEAKING_FREQ_ELF_HITS_G159,
    FX6_PEAKING_MENU_PATH_G159,
    FX6_PEAKING_TYPE_ELF_HITS_G159,
    FX6_SYSTEM_FREQUENCY_MENU_PATH_G160,
    FX6_THUMBNAIL_FILTERS_BY_CURRENT_FREQ_G160,
    FX6_USBC_BODY_POWER_SUPPORTED_G160,
    FX6_WIND_FILTER_CHANNELS_G159,
    G159,
    G160,
    MEDIA_SLOT_1_PHASE373,
    MEDIA_SLOT_2_PHASE373,
    MEDIA_SLOT_NONE_PHASE373,
    Master160GateReport,
    NTSC_PAL_SELECTOR_MENU_PATH_G160,
    NTSC_PAL_SKU_DEFAULTS_G160,
    NTSC_PAL_SKU_GATE_FN_G160,
    PEAKING_COLOR_DEFAULT_G159,
    PEAKING_DISPLAY_DEFAULT_G159,
    PEAKING_DISPLAY_MENU_PATH_G159,
    PEAKING_LEVEL_DEFAULT_G159,
    PINNED_FX3_APPFW_SLICES_PHASE373,
    PINNED_FX6_APPFW_SLICES_PHASE373,
    PINNED_PHASE373_DONOR_SPECS,
    REALHW_160GATE_PREFLIGHT_SCHEMA,
    RECOVER_DB_MIN_SOC_PCT_G160,
    RECOVER_DB_MIN_VOLTAGE_MV_G160,
    RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE373,
    RESET_ACTION_INITIALIZE_PHASE373,
    RESET_ACTION_NONE_PHASE373,
    RUNNING_ON_NTSC_BANNER_G160,
    RUNNING_ON_PAL_BANNER_G160,
    SHOE_AUDIO_DEFAULT_G159,
    SHOOT_MODE_MOVIE_PHASE373,
    SHOOT_MODE_SQ_PHASE373,
    SHOOT_MODE_STILL_PHASE373,
    STATUS_BLOCKED_G159_DORMANT_FOCUSMAP_FX6_TYPEFREQ_AUDIOMETER_OR_WINDAUTO_EOPNOTSUPP,
    STATUS_BLOCKED_G159_PEAKING_HDMI_RESET_OR_AUDIO_PREEMPTION_WIND_VIOLATION,
    STATUS_BLOCKED_G159_TELEMETRY_INVALID,
    STATUS_BLOCKED_G160_FX6_DC_IN_HOT_REPLUG_RECORDING_EBUSY,
    STATUS_BLOCKED_G160_MICROUSB_NO_FZ100_J1_LOCK_OR_CROSS_STD_EOPNOTSUPP,
    STATUS_BLOCKED_G160_SLOT1_AVFINFO_OR_FORMAT_VAULT_EROFS,
    STATUS_BLOCKED_G160_TELEMETRY_INVALID,
    STATUS_BLOCKED_G160_USBPD_CHARGE_DCC1_OR_NTSCPAL_CONSTRAINT_VIOLATION,
    STATUS_BLOCKED_PERSISTENT_EMMC_WRITE,
    STATUS_BLOCKED_PHASE373_DONOR_INTEGRITY,
    STATUS_VERIFIED_G159,
    STATUS_VERIFIED_G160,
    USB_PD_RECOMMENDED_SHOOT_WATTS_G160,
    USB_POWER_SUPPLY_DEFAULT_G160,
    USB_POWER_SUPPLY_MENU_PATH_G160,
    USB_POWER_SUPPLY_RESETTABLE_BY_CAMSET_RESET_G160,
    VER7_XAVC_SWITCH_REQUIRES_FORMAT_G160,
    VER7_XAVC_SWITCH_REQUIRES_REBOOT_G160,
    WIND_NOISE_REDUCT_DEFAULT_G159,
    audit_phase373_donor_contracts,
    compute_peaking_audio_wind_matrix,
    compute_usbpd_ntscpal_avfinfo_matrix,
    evaluate_160_master_safety_gates,
    evaluate_160gate_preflight,
    evaluate_g159_peaking_audio_wind_guard,
    evaluate_g160_usbpd_ntscpal_avfinfo_guard,
    main as guard_module_main,
    resolve_fx3_peaking_audio_wind_state,
    resolve_fx3_usbpd_ntscpal_avfinfo_state,
    run_160_gate_preflight,
    strip_elapsed_seconds_recursive_phase373,
    verify_peaking_audio_wind_guard,
    verify_peaking_audio_wind_guard_with_audit,
    verify_real_hardware_160gate_readiness,
    verify_usbpd_ntscpal_avfinfo_guard,
    verify_usbpd_ntscpal_avfinfo_guard_with_audit,
)


def _mock_paths_work_root_none(**_kwargs):
    return mock.MagicMock(work_root=None)


class TestPhase373HardwareSafety160Gates(unittest.TestCase):
    # ------------------------------------------------------------------
    # Donor Integrity & 4-Mode Checks (01..12)
    # ------------------------------------------------------------------

    def test_01_donor_specs_pin_16_artifacts_and_fast_budget(self) -> None:
        self.assertEqual(len(PINNED_PHASE373_DONOR_SPECS), 16)
        self.assertEqual(len(PINNED_FX3_APPFW_SLICES_PHASE373), 30)
        self.assertEqual(len(PINNED_FX6_APPFW_SLICES_PHASE373), 13)
        audit = audit_phase373_donor_contracts(repo_root=REPO_ROOT)
        self.assertTrue(audit.valid)
        self.assertTrue(audit.within_budget_200ms)
        self.assertLessEqual(audit.elapsed_seconds, DONOR_CHECK_MAX_SECONDS_PHASE373)
        self.assertEqual(audit.raw_firmware_bytes_leaked, 0)

    def test_02_donor_audit_normal_mode_matches_expected(self) -> None:
        with mock.patch.dict(
            os.environ,
            {"FX3_FX6_FORCE_CLEAN_ROOM": "", ENV_CLEAN_ROOM_TEST_PHASE373: ""},
            clear=False,
        ):
            audit = audit_phase373_donor_contracts(repo_root=REPO_ROOT)
        self.assertTrue(audit.valid)
        self.assertEqual(audit.raw_firmware_bytes_leaked, 0)
        self.assertIn(
            audit.verification_mode,
            ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"),
        )
        if audit.verification_mode == "LOCAL_DONOR_O_RDONLY":
            self.assertEqual(audit.files_inspected, 16)
            self.assertEqual(audit.access_mode, "STRICT_OS_O_RDONLY_PREAD")

    def test_03_donor_audit_fx3_clean_room_test_env_mode(self) -> None:
        with mock.patch.dict(
            os.environ,
            {ENV_CLEAN_ROOM_TEST_PHASE373: "1", "FX3_FX6_FORCE_CLEAN_ROOM": ""},
            clear=False,
        ):
            audit = audit_phase373_donor_contracts(repo_root=REPO_ROOT)
        self.assertTrue(audit.valid)
        self.assertEqual(audit.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(audit.access_mode, "SYNTHETIC_NO_DONOR_DISK_IO")
        self.assertEqual(audit.files_inspected, 0)
        self.assertEqual(audit.raw_firmware_bytes_leaked, 0)

    def test_04_donor_audit_force_clean_room_env_mode(self) -> None:
        with mock.patch.dict(
            os.environ,
            {"FX3_FX6_FORCE_CLEAN_ROOM": "1", ENV_CLEAN_ROOM_TEST_PHASE373: ""},
            clear=False,
        ):
            audit = audit_phase373_donor_contracts(repo_root=REPO_ROOT)
        self.assertTrue(audit.valid)
        self.assertEqual(audit.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(audit.files_inspected, 0)

    def test_05_donor_audit_mocked_work_root_none_fallback(self) -> None:
        with mock.patch(
            "fx3_safety.realhw_peaking_audio_wind_usbpd_ntscpal_and_160gate_guard.resolve_donor_thermal_power_paths",
            side_effect=_mock_paths_work_root_none,
        ):
            with mock.patch.dict(
                os.environ,
                {"FX3_FX6_FORCE_CLEAN_ROOM": "", ENV_CLEAN_ROOM_TEST_PHASE373: ""},
                clear=False,
            ):
                audit = audit_phase373_donor_contracts(repo_root=REPO_ROOT)
        self.assertTrue(audit.valid)
        self.assertEqual(audit.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(audit.access_mode, "SYNTHETIC_ABSENT_DONOR_FALLBACK")
        self.assertEqual(audit.raw_firmware_bytes_leaked, 0)

    def test_06_donor_audit_absent_temp_work_root_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            audit = audit_phase373_donor_contracts(
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
                "tiny": (
                    "FX3",
                    "missing.bin",
                    16,
                    "0" * 64,
                    (b"NEEDLE",),
                    "test missing",
                )
            }
            audit = audit_phase373_donor_contracts(
                work_root=Path(tmpdir),
                force_clean_room=False,
                donor_specs_override=bad_spec,
            )
        self.assertFalse(audit.valid)
        self.assertEqual(audit.status, STATUS_BLOCKED_PHASE373_DONOR_INTEGRITY)
        self.assertIn("tiny:file_missing", audit.missing_markers)

    def test_08_donor_audit_override_detects_sha256_and_token_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir) / "blob.bin"
            p.write_bytes(b"INVALID_CONTENT")
            bad_spec = {
                "blob": (
                    "FX3",
                    "blob.bin",
                    15,
                    "f" * 64,
                    (b"EXPECTED_TOKEN",),
                    "tampered",
                )
            }
            audit = audit_phase373_donor_contracts(
                work_root=Path(tmpdir),
                force_clean_room=False,
                donor_specs_override=bad_spec,
            )
        self.assertFalse(audit.valid)
        self.assertIn("blob:sha256_mismatch", audit.missing_markers)
        self.assertIn("blob:token_missing_idx_0", audit.missing_markers)

    def test_09_strip_elapsed_seconds_and_ms_recursive_determinism(self) -> None:
        a = {
            "elapsed_seconds": 0.011,
            "elapsed_ms": 11.2,
            "nested": [{"elapsed_seconds": 0.022, "elapsed_ms": 22.1, "val": 1}],
            "tuple_val": ({"elapsed_seconds": 0.033, "elapsed_ms": 33.0, "ok": True},),
        }
        b = {
            "elapsed_seconds": 0.999,
            "elapsed_ms": 999.9,
            "nested": [{"elapsed_seconds": 0.888, "elapsed_ms": 888.8, "val": 1}],
            "tuple_val": ({"elapsed_seconds": 0.777, "elapsed_ms": 777.7, "ok": True},),
        }
        sa = strip_elapsed_seconds_recursive_phase373(a)
        sb = strip_elapsed_seconds_recursive_phase373(b)
        self.assertEqual(sa, sb)
        self.assertNotIn("elapsed_seconds", sa)
        self.assertNotIn("elapsed_ms", sa)
        ha = hashlib.sha256(json.dumps(sa, sort_keys=True).encode()).hexdigest()
        hb = hashlib.sha256(json.dumps(sb, sort_keys=True).encode()).hexdigest()
        self.assertEqual(ha, hb)

    def test_10_clean_room_vs_local_donor_file_digests_match(self) -> None:
        cr = audit_phase373_donor_contracts(repo_root=REPO_ROOT, force_clean_room=True)
        norm = audit_phase373_donor_contracts(repo_root=REPO_ROOT, force_clean_room=False)
        self.assertEqual(cr.file_digests, norm.file_digests)

    def test_11_preflight_160_passes_across_all_4_modes(self) -> None:
        # Mode 1: normal
        r1 = evaluate_160gate_preflight(REPO_ROOT, dry_run_simulated=True)
        # Mode 2: FX3_CLEAN_ROOM_TEST=1
        with mock.patch.dict(os.environ, {ENV_CLEAN_ROOM_TEST_PHASE373: "1"}, clear=False):
            r2 = evaluate_160gate_preflight(REPO_ROOT, dry_run_simulated=True)
        # Mode 3: FX3_FX6_FORCE_CLEAN_ROOM=1
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}, clear=False):
            r3 = evaluate_160gate_preflight(REPO_ROOT, dry_run_simulated=True)
        # Mode 4a: donorless temp work_root
        with tempfile.TemporaryDirectory() as tmpdir:
            r4a = evaluate_160gate_preflight(
                REPO_ROOT,
                work_root=Path(tmpdir),
                dry_run_simulated=True,
            )
        # Mode 4b: mocked work_root=None
        with mock.patch(
            "fx3_safety.realhw_peaking_audio_wind_usbpd_ntscpal_and_160gate_guard.resolve_donor_thermal_power_paths",
            side_effect=_mock_paths_work_root_none,
        ):
            with mock.patch.dict(
                os.environ,
                {"FX3_FX6_FORCE_CLEAN_ROOM": "", ENV_CLEAN_ROOM_TEST_PHASE373: ""},
                clear=False,
            ):
                r4b = evaluate_160gate_preflight(REPO_ROOT, dry_run_simulated=True)
        for rep in (r1, r2, r3, r4a, r4b):
            self.assertIsInstance(rep, Master160GateReport)
            self.assertEqual(rep.summary["total_gates"], 160)
            self.assertEqual(rep.summary["verified_gates"], 160)
            self.assertTrue(rep.all_160_gates_verified)
            self.assertFalse(rep.overall_ready_for_hardware_attach)
            self.assertFalse(rep.hardware_live_attachment_authorized)
            self.assertFalse(rep.persistent_emmc_writes_authorized)
            self.assertFalse(rep.cross_model_flash_authorized)
            self.assertEqual(rep.usb_packets_transmitted, 0)
            self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_12_donor_audit_work_root_none_override_fails_closed(self) -> None:
        bad_spec = {"x": ("FX3", "x.bin", 1, "0" * 64, (b"A",), "override")}
        with mock.patch(
            "fx3_safety.realhw_peaking_audio_wind_usbpd_ntscpal_and_160gate_guard.resolve_donor_thermal_power_paths",
            side_effect=_mock_paths_work_root_none,
        ):
            audit = audit_phase373_donor_contracts(
                force_clean_room=False,
                donor_specs_override=bad_spec,
            )
        self.assertFalse(audit.valid)
        self.assertIn("x:work_root_none", audit.missing_markers)

    # ------------------------------------------------------------------
    # Gate G159: Peaking Display Clean-HDMI & FX6 Zero Type/Freq (13..34)
    # ------------------------------------------------------------------

    def test_13_g159_default_verified_safe(self) -> None:
        res = verify_peaking_audio_wind_guard()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_VERIFIED_G159)
        self.assertEqual(res.block_errno, 0)
        self.assertEqual(res.peaking_display_menu_path, PEAKING_DISPLAY_MENU_PATH_G159)
        self.assertEqual(res.fx6_peaking_menu_path, FX6_PEAKING_MENU_PATH_G159)
        self.assertEqual(res.audio_recording_menu_path, AUDIO_RECORDING_MENU_PATH_G159)
        self.assertEqual(res.fx3_peaking_items_count, 3)
        self.assertEqual(res.fx6_peaking_items_count, 3)
        self.assertEqual(res.fx3_audio_recording_items_count, 5)

    def test_14_g159_exact_3_fx3_peaking_items_and_defaults(self) -> None:
        self.assertEqual(
            EXACT_3_FX3_PEAKING_ITEMS_G159,
            ("Peaking Display", "Peaking Level", "Peaking Color"),
        )
        self.assertEqual(PEAKING_DISPLAY_DEFAULT_G159, "Off")
        self.assertEqual(PEAKING_LEVEL_DEFAULT_G159, "Mid")
        self.assertEqual(PEAKING_COLOR_DEFAULT_G159, "White")
        self.assertFalse(FX3_PEAKING_RESETTABLE_BY_CAMSET_RESET_G159)

    def test_15_g159_peaking_all_3_items_survive_camera_settings_reset(self) -> None:
        st = resolve_fx3_peaking_audio_wind_state(
            peaking_display="On",
            peaking_level="High",
            peaking_color="Red",
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE373,
        )
        self.assertEqual(st["effective_peaking_display"], "On")
        self.assertEqual(st["effective_peaking_level"], "High")
        self.assertEqual(st["effective_peaking_color"], "Red")

    def test_16_g159_peaking_all_3_items_reset_only_by_initialize(self) -> None:
        st = resolve_fx3_peaking_audio_wind_state(
            peaking_display="On",
            peaking_level="Low",
            peaking_color="Blue",
            reset_action=RESET_ACTION_INITIALIZE_PHASE373,
        )
        self.assertEqual(st["effective_peaking_display"], "Off")
        self.assertEqual(st["effective_peaking_level"], "Mid")
        self.assertEqual(st["effective_peaking_color"], "White")

    def test_17_g159_claimed_camset_reset_clears_peaking_blocked_einval(self) -> None:
        res = verify_peaking_audio_wind_guard(claimed_camset_reset_clears_peaking=True)
        self.assertFalse(res.valid)
        self.assertEqual(res.block_errno, EINVAL_ERRNO_PHASE373)
        self.assertEqual(
            res.status,
            STATUS_BLOCKED_G159_PEAKING_HDMI_RESET_OR_AUDIO_PREEMPTION_WIND_VIOLATION,
        )
        self.assertIn("PEAKING_3ITEMS_RESET_IMMUNITY_VIOLATION", res.violation_codes)

    def test_18_g159_peaking_clean_hdmi_never_emitted_with_hdmi_info_on(self) -> None:
        res = verify_peaking_audio_wind_guard(
            peaking_display="On",
            peaking_level="High",
            peaking_color="Yellow",
            hdmi_info_display="On",
            raw_output="Off",
        )
        self.assertTrue(res.valid)
        self.assertFalse(res.peaking_emitted_over_hdmi)
        self.assertEqual(res.hdmi_peaking_leaked_pixels, 0)

    def test_19_g159_peaking_clean_hdmi_never_emitted_with_raw_output_on(self) -> None:
        res = verify_peaking_audio_wind_guard(
            peaking_display="On",
            hdmi_info_display="Off",
            raw_output="On",
        )
        self.assertTrue(res.valid)
        self.assertFalse(res.peaking_emitted_over_hdmi)
        self.assertEqual(res.hdmi_peaking_leaked_pixels, 0)

    def test_20_g159_claimed_peaking_over_hdmi_blocked_einval(self) -> None:
        res = verify_peaking_audio_wind_guard(
            peaking_display="On",
            hdmi_info_display="On",
            claimed_peaking_over_hdmi=True,
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.block_errno, EINVAL_ERRNO_PHASE373)
        self.assertIn("PEAKING_CLEAN_HDMI_ISOLATION_VIOLATION", res.violation_codes)

    def test_21_g159_peaking_compatible_with_focus_magnifier(self) -> None:
        res = verify_peaking_audio_wind_guard(
            peaking_display="On",
            focus_magnifier_active=True,
        )
        self.assertTrue(res.valid)
        self.assertTrue(res.peaking_compatible_with_focus_magnifier)
        self.assertTrue(res.focus_magnifier_active)

    def test_22_g159_claimed_peaking_focus_magnifier_mutex_blocked_einval(self) -> None:
        res = verify_peaking_audio_wind_guard(
            peaking_display="On",
            focus_magnifier_active=True,
            claimed_peaking_focus_magnifier_mutex=True,
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.block_errno, EINVAL_ERRNO_PHASE373)
        self.assertIn("PEAKING_FOCUS_MAGNIFIER_COMPAT_VIOLATION", res.violation_codes)

    def test_23_g159_dormant_inbody_focus_map_rejected_eopnotsupp(self) -> None:
        res = verify_peaking_audio_wind_guard(requested_inbody_focus_map=True)
        self.assertFalse(res.valid)
        self.assertEqual(res.block_errno, EOPNOTSUPP_ERRNO_PHASE373)
        self.assertEqual(
            res.status,
            STATUS_BLOCKED_G159_DORMANT_FOCUSMAP_FX6_TYPEFREQ_AUDIOMETER_OR_WINDAUTO_EOPNOTSUPP,
        )
        self.assertFalse(res.fx3_inbody_focus_map_exposed)
        self.assertIn("FX3_INBODY_FOCUS_MAP_DORMANT_EOPNOTSUPP", res.violation_codes)

    def test_24_g159_wireless_mc_focus_map_allowed_ver6_plus_not_usb_wired(self) -> None:
        ok = verify_peaking_audio_wind_guard(
            firmware_version="7.02",
            wireless_mc_app_connected=True,
        )
        self.assertTrue(ok.valid)
        self.assertTrue(ok.wireless_mc_focus_map_allowed)
        bad_usb = verify_peaking_audio_wind_guard(requested_usb_wired_mc_focus_map=True)
        self.assertFalse(bad_usb.valid)
        self.assertEqual(bad_usb.block_errno, EOPNOTSUPP_ERRNO_PHASE373)
        self.assertIn("FX3_USB_WIRED_MC_FOCUS_MAP_UNSUPPORTED_EOPNOTSUPP", bad_usb.violation_codes)

    def test_25_g159_fx6_monitoring_peaking_3_items_bw_not_white(self) -> None:
        self.assertEqual(EXACT_3_FX6_PEAKING_ITEMS_G159, ("Setting", "Peaking Level", "Color"))
        self.assertEqual(FX6_PEAKING_TYPE_ELF_HITS_G159, 0)
        self.assertEqual(FX6_PEAKING_FREQ_ELF_HITS_G159, 0)
        ok_bw = verify_peaking_audio_wind_guard(fx6_peaking_color="B&W")
        self.assertTrue(ok_bw.valid)
        bad_white = verify_peaking_audio_wind_guard(fx6_peaking_color="White")
        self.assertFalse(bad_white.valid)
        self.assertEqual(bad_white.block_errno, EOPNOTSUPP_ERRNO_PHASE373)
        self.assertIn("FX6_PEAKING_COLOR_BW_NOT_WHITE_EOPNOTSUPP", bad_white.violation_codes)

    def test_26_g159_fx6_dormant_peaking_type_or_freq_rejected_eopnotsupp(self) -> None:
        res = verify_peaking_audio_wind_guard(
            requested_fx6_dormant_peaking_type_or_freq=True
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.block_errno, EOPNOTSUPP_ERRNO_PHASE373)
        self.assertIn("FX6_DORMANT_PEAKING_TYPE_OR_FREQ_ZERO_ELF_EOPNOTSUPP", res.violation_codes)

    def test_27_g159_all_4_fx3_peaking_colors_and_3_levels_valid(self) -> None:
        for lvl in ("High", "Mid", "Low"):
            for col in ("Red", "Yellow", "Blue", "White"):
                r = verify_peaking_audio_wind_guard(
                    peaking_display="On", peaking_level=lvl, peaking_color=col
                )
                self.assertTrue(r.valid, f"Failed for {lvl}/{col}")

    # ------------------------------------------------------------------
    # Gate G159: Ver. 2.00+ Audio 5-Item, Wind Built-In Only & Preemption (28..48)
    # ------------------------------------------------------------------

    def test_28_g159_audio_level_display_menu_removed_ver2_plus_eopnotsupp(self) -> None:
        self.assertTrue(AUDIO_LEVEL_DISPLAY_MENU_REMOVED_VER2_PLUS_G159)
        res = verify_peaking_audio_wind_guard(
            requested_audio_level_display_menu_write=True
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.block_errno, EOPNOTSUPP_ERRNO_PHASE373)
        self.assertIn("FX3_AUDIO_LEVEL_DISPLAY_MENU_REMOVED_VER2_EOPNOTSUPP", res.violation_codes)

    def test_29_g159_exact_5_audio_items_all_resettable_by_camset_reset(self) -> None:
        self.assertEqual(
            EXACT_5_FX3_AUDIO_RECORDING_ITEMS_G159,
            (
                "Audio Recording",
                "Audio Rec Level",
                "Audio Out Timing",
                "Wind Noise Reduct.",
                "Shoe Audio Set.",
            ),
        )
        self.assertTrue(FX3_AUDIO_5ITEMS_RESETTABLE_BY_CAMSET_RESET_G159)
        st = resolve_fx3_peaking_audio_wind_state(
            audio_recording="Off",
            audio_rec_level=12,
            audio_out_timing="Lip Sync",
            wind_noise_reduct="On",
            shoe_audio_format="48kHz/24bit 4ch",
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE373,
        )
        self.assertEqual(st["effective_audio_recording"], AUDIO_RECORDING_DEFAULT_G159)
        self.assertEqual(st["effective_audio_rec_level"], AUDIO_REC_LEVEL_DEFAULT_G159)
        self.assertEqual(st["effective_audio_out_timing"], AUDIO_OUT_TIMING_DEFAULT_G159)
        self.assertEqual(st["effective_wind_noise_reduct"], WIND_NOISE_REDUCT_DEFAULT_G159)
        self.assertEqual(st["effective_shoe_audio_format"], SHOE_AUDIO_DEFAULT_G159)

    def test_30_g159_claimed_audio_5items_reset_immune_blocked_einval(self) -> None:
        res = verify_peaking_audio_wind_guard(claimed_audio_5items_reset_immune=True)
        self.assertFalse(res.valid)
        self.assertEqual(res.block_errno, EINVAL_ERRNO_PHASE373)
        self.assertIn("AUDIO_5ITEMS_RESETTABLE_VIOLATION", res.violation_codes)

    def test_31_g159_audio_rec_level_bounds_0_to_31_and_defult_typo(self) -> None:
        self.assertEqual(AUDIO_REC_LEVEL_MIN_G159, 0)
        self.assertEqual(AUDIO_REC_LEVEL_MAX_G159, 31)
        self.assertEqual(AUDIO_REC_LEVEL_DEFAULT_G159, 26)
        self.assertEqual(AUDIO_REC_LEVEL_ELF_TYPO_G159, "adj_audio_rec_level_defult")
        self.assertTrue(verify_peaking_audio_wind_guard(audio_rec_level=0).valid)
        self.assertTrue(verify_peaking_audio_wind_guard(audio_rec_level=31).valid)
        bad_lo = verify_peaking_audio_wind_guard(audio_rec_level=-1)
        bad_hi = verify_peaking_audio_wind_guard(audio_rec_level=32)
        self.assertFalse(bad_lo.valid)
        self.assertFalse(bad_hi.valid)
        self.assertEqual(bad_lo.status, STATUS_BLOCKED_G159_TELEMETRY_INVALID)
        self.assertEqual(bad_hi.status, STATUS_BLOCKED_G159_TELEMETRY_INVALID)

    def test_32_g159_permanent_audio_limiter_non_disableable_eopnotsupp(self) -> None:
        self.assertTrue(FX3_AUDIO_LIMITER_PERMANENT_NON_DISABLEABLE_G159)
        res = verify_peaking_audio_wind_guard(requested_disable_fx3_audio_limiter=True)
        self.assertFalse(res.valid)
        self.assertEqual(res.block_errno, EOPNOTSUPP_ERRNO_PHASE373)
        self.assertIn("FX3_PERMANENT_AUDIO_LIMITER_NON_DISABLEABLE_EOPNOTSUPP", res.violation_codes)

    def test_33_g159_wind_noise_auto_rejected_eopnotsupp(self) -> None:
        self.assertFalse(FX3_WIND_NOISE_AUTO_EXPOSED_G159)
        r1 = verify_peaking_audio_wind_guard(wind_noise_reduct="Auto")
        r2 = verify_peaking_audio_wind_guard(requested_wind_noise_auto=True)
        for r in (r1, r2):
            self.assertFalse(r.valid)
            self.assertEqual(r.block_errno, EOPNOTSUPP_ERRNO_PHASE373)
            self.assertIn("FX3_WIND_NOISE_AUTO_UNEXPOSED_EOPNOTSUPP", r.violation_codes)

    def test_34_g159_wind_noise_active_only_on_builtin_stereo_mic(self) -> None:
        res = verify_peaking_audio_wind_guard(
            shoot_mode=SHOOT_MODE_MOVIE_PHASE373,
            wind_noise_reduct="On",
            mic_35mm_plugged=False,
            xlr_h1_mode="OFF",
            mi_shoe_other_mic_attached=False,
        )
        self.assertTrue(res.valid)
        self.assertEqual(res.active_audio_input_source, "builtin_stereo_mic")
        self.assertTrue(res.wind_noise_dsp_active)
        self.assertEqual(res.wind_noise_bypassed_reason, "none")

    def test_35_g159_wind_noise_bypassed_on_35mm_xlr_mishoe_and_sq(self) -> None:
        cases = [
            ({"mic_35mm_plugged": True}, "external_3.5mm_mic_preempts"),
            ({"xlr_h1_mode": "DIGITAL"}, "external_xlr_h1_digital_bypass"),
            ({"xlr_h1_mode": "ANALOG"}, "external_xlr_h1_analog_bypass"),
            ({"mi_shoe_other_mic_attached": True}, "external_mi_shoe_mic_bypass"),
            ({"shoot_mode": SHOOT_MODE_SQ_PHASE373}, "sq_0ch_disabled"),
        ]
        for kw, reason in cases:
            r = verify_peaking_audio_wind_guard(wind_noise_reduct="On", **kw)
            self.assertTrue(r.valid)
            self.assertFalse(r.wind_noise_dsp_active)
            self.assertEqual(r.wind_noise_bypassed_reason, reason)

    def test_36_g159_claimed_wind_noise_active_on_external_mic_blocked_einval(self) -> None:
        res = verify_peaking_audio_wind_guard(
            wind_noise_reduct="On",
            xlr_h1_mode="DIGITAL",
            claimed_wind_noise_active_on_external_mic=True,
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.block_errno, EINVAL_ERRNO_PHASE373)
        self.assertIn("WIND_NOISE_BUILTIN_STEREO_MIC_ONLY_VIOLATION", res.violation_codes)

    def test_37_g159_3tier_preemption_35mm_beats_xlr_h1_digital(self) -> None:
        self.assertEqual(
            FX3_AUDIO_PREEMPTION_TIERS_G159,
            ("3.5mm_mic", "mi_shoe_xlr_h1_digital", "builtin_stereo_mic"),
        )
        r = verify_peaking_audio_wind_guard(
            mic_35mm_plugged=True,
            xlr_h1_mode="DIGITAL",
            shoe_audio_format="48kHz/24bit 4ch",
        )
        self.assertTrue(r.valid)
        self.assertEqual(r.active_audio_input_source, "3.5mm_mic")
        self.assertEqual(r.active_audio_channels, 2)
        self.assertFalse(r.shoe_audio_menu_selectable)

    def test_38_g159_claimed_35mm_allows_xlr_4ch_blocked_einval(self) -> None:
        r = verify_peaking_audio_wind_guard(
            mic_35mm_plugged=True,
            xlr_h1_mode="DIGITAL",
            claimed_35mm_allows_xlr_4ch=True,
        )
        self.assertFalse(r.valid)
        self.assertEqual(r.block_errno, EINVAL_ERRNO_PHASE373)
        self.assertIn("AUDIO_35MM_PREEMPTS_XLRH1_4CH_VIOLATION", r.violation_codes)

    def test_39_g159_xlr_h1_digital_4ch_and_analog_downgrade_and_off_fallback(self) -> None:
        r_dig = verify_peaking_audio_wind_guard(
            xlr_h1_mode="DIGITAL", shoe_audio_format="48kHz/24bit 4ch"
        )
        self.assertTrue(r_dig.valid)
        self.assertEqual(r_dig.active_audio_input_source, "mi_shoe_xlr_h1_digital")
        self.assertEqual(r_dig.active_audio_channels, 4)
        self.assertTrue(r_dig.shoe_audio_menu_selectable)

        r_ana = verify_peaking_audio_wind_guard(
            xlr_h1_mode="ANALOG", shoe_audio_format="48kHz/24bit 4ch"
        )
        self.assertTrue(r_ana.valid)
        self.assertEqual(r_ana.active_audio_input_source, "mi_shoe_xlr_h1_analog")
        self.assertEqual(r_ana.active_audio_channels, 2)
        self.assertEqual(r_ana.effective_shoe_audio_format, "48kHz/16bit 2ch")
        self.assertFalse(r_ana.shoe_audio_menu_selectable)

        r_off = verify_peaking_audio_wind_guard(xlr_h1_mode="OFF")
        self.assertEqual(r_off.active_audio_input_source, "builtin_stereo_mic")

    def test_40_g159_fx6_handle_zero_hw_low_cut_switch_eopnotsupp(self) -> None:
        self.assertFalse(FX6_HANDLE_HW_LOW_CUT_SWITCH_PRESENT_G159)
        self.assertEqual(len(FX6_WIND_FILTER_CHANNELS_G159), 4)
        self.assertEqual(len(EXACT_6_FX6_LIMITER_MODES_G159), 6)
        r = verify_peaking_audio_wind_guard(requested_fx6_handle_hw_low_cut_switch=True)
        self.assertFalse(r.valid)
        self.assertEqual(r.block_errno, EOPNOTSUPP_ERRNO_PHASE373)
        self.assertIn("FX6_HANDLE_ZERO_HW_LOW_CUT_SWITCH_EOPNOTSUPP", r.violation_codes)

    def test_41_g159_fx6_6step_limiter_modes_all_valid(self) -> None:
        for mode in EXACT_6_FX6_LIMITER_MODES_G159:
            r = verify_peaking_audio_wind_guard(fx6_limiter_mode=mode)
            self.assertTrue(r.valid, f"FX6 limiter mode {mode} failed")

    def test_42_g159_invalid_telemetry_fields_fail_closed_einval(self) -> None:
        bad_cases = [
            {"body_model_name": "ILME-FX6"},
            {"body_model_id": 0x9999},
            {"help_guide_code": "ilc/2035"},
            {"firmware_version": "not-a-float"},
            {"peaking_display": "Maybe"},
            {"peaking_level": "Ultra"},
            {"peaking_color": "Green"},
            {"audio_out_timing": "Delayed"},
            {"wind_noise_reduct": "SuperHigh"},
            {"shoe_audio_format": "96kHz/32bit 8ch"},
            {"xlr_h1_mode": "PHANTOM_ONLY"},
            {"fx6_limiter_mode": "-24dB"},
            {"fx6_peaking_color": "Purple"},
            {"reset_action": "FactoryWipe"},
        ]
        for kw in bad_cases:
            r = verify_peaking_audio_wind_guard(**kw)
            self.assertFalse(r.valid, f"Should fail for {kw}")
            self.assertEqual(r.block_errno, EINVAL_ERRNO_PHASE373)
            self.assertEqual(r.status, STATUS_BLOCKED_G159_TELEMETRY_INVALID)

    def test_43_g159_exhaustive_384_state_matrix(self) -> None:
        m = compute_peaking_audio_wind_matrix()
        self.assertEqual(m["total_matrix_states"], 384)
        self.assertEqual(m["hdmi_peaking_zero_count"], 384)
        self.assertEqual(m["peaking_reset_preserved_count"], 192)
        self.assertEqual(m["wind_reset_cleared_count"], 96)
        self.assertGreater(m["wind_builtin_only_active_count"], 0)
        self.assertGreater(m["wind_external_or_sq_bypassed_count"], 0)
        self.assertGreater(m["mic_35mm_preempted_xlr_count"], 0)

    def test_44_g159_evaluate_and_alias_wrapper_match(self) -> None:
        v1, r1 = evaluate_g159_peaking_audio_wind_guard(
            repo_root=REPO_ROOT, force_clean_room=True
        )
        v2, r2 = verify_peaking_audio_wind_guard_with_audit(
            repo_root=REPO_ROOT, force_clean_room=True
        )
        self.assertTrue(v1.passed)
        self.assertTrue(v2.passed)
        self.assertEqual(v1.gate_id, G159)
        self.assertEqual(r1.status, STATUS_VERIFIED_G159)
        self.assertEqual(r1.status, r2.status)

    def test_45_g159_sq_mode_forces_0ch_audio(self) -> None:
        r = verify_peaking_audio_wind_guard(
            shoot_mode=SHOOT_MODE_SQ_PHASE373,
            xlr_h1_mode="DIGITAL",
            shoe_audio_format="48kHz/24bit 4ch",
        )
        self.assertTrue(r.valid)
        self.assertEqual(r.active_audio_channels, 0)
        self.assertEqual(r.active_audio_input_source, "none_sq_0ch")
        self.assertFalse(r.shoe_audio_menu_selectable)

    def test_46_g159_audio_recording_off_yields_0ch(self) -> None:
        r = verify_peaking_audio_wind_guard(audio_recording="Off")
        self.assertTrue(r.valid)
        self.assertEqual(r.active_audio_channels, 0)
        self.assertEqual(r.active_audio_input_source, "audio_recording_off")
        self.assertFalse(r.wind_noise_dsp_active)

    # ------------------------------------------------------------------
    # Gate G160: USB Power Supply / Mandatory NP-FZ100 / DC-C1 vs FX6 DC IN (47..68)
    # ------------------------------------------------------------------

    def test_47_g160_default_verified_safe(self) -> None:
        res = verify_usbpd_ntscpal_avfinfo_guard()
        self.assertTrue(res.valid)
        self.assertEqual(res.status, STATUS_VERIFIED_G160)
        self.assertEqual(res.block_errno, 0)
        self.assertEqual(res.usb_power_supply_menu_path, USB_POWER_SUPPLY_MENU_PATH_G160)
        self.assertEqual(res.ntsc_pal_selector_menu_path, NTSC_PAL_SELECTOR_MENU_PATH_G160)
        self.assertEqual(res.fx6_system_frequency_menu_path, FX6_SYSTEM_FREQUENCY_MENU_PATH_G160)
        self.assertEqual(res.usb_pd_watts, USB_PD_RECOMMENDED_SHOOT_WATTS_G160)
        self.assertFalse(res.low_power_drain_warning)
        self.assertFalse(res.charging_active)
        self.assertEqual(res.charge_led_state, "OFF")
        self.assertTrue(res.power_save_bypassed_by_usb_pd)

    def test_48_g160_usb_power_supply_anti_camera_reset_initialize_only(self) -> None:
        self.assertEqual(USB_POWER_SUPPLY_DEFAULT_G160, "On")
        self.assertFalse(USB_POWER_SUPPLY_RESETTABLE_BY_CAMSET_RESET_G160)
        st_rst = resolve_fx3_usbpd_ntscpal_avfinfo_state(
            usb_power_supply="Off",
            reset_action=RESET_ACTION_CAMERA_SETTINGS_RESET_PHASE373,
        )
        self.assertEqual(st_rst["effective_usb_power_supply"], "Off")
        st_init = resolve_fx3_usbpd_ntscpal_avfinfo_state(
            usb_power_supply="Off",
            reset_action=RESET_ACTION_INITIALIZE_PHASE373,
        )
        self.assertEqual(st_init["effective_usb_power_supply"], "On")

    def test_49_g160_claimed_camset_reset_clears_usb_power_blocked_einval(self) -> None:
        res = verify_usbpd_ntscpal_avfinfo_guard(
            claimed_camset_reset_clears_usb_power_supply=True
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.block_errno, EINVAL_ERRNO_PHASE373)
        self.assertIn("USB_POWER_SUPPLY_RESET_IMMUNITY_VIOLATION", res.violation_codes)

    def test_50_g160_multi_micro_usb_power_rejected_eopnotsupp(self) -> None:
        res = verify_usbpd_ntscpal_avfinfo_guard(
            power_source_mode="usb_c_pd",
            usb_port_kind="multi_micro_usb",
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.block_errno, EOPNOTSUPP_ERRNO_PHASE373)
        self.assertEqual(
            res.status,
            STATUS_BLOCKED_G160_MICROUSB_NO_FZ100_J1_LOCK_OR_CROSS_STD_EOPNOTSUPP,
        )
        self.assertIn("FX3_MULTI_MICRO_USB_POWER_REJECTED_EOPNOTSUPP", res.violation_codes)

    def test_51_g160_5v_1_5a_low_power_drain_warning_and_strict_block(self) -> None:
        warn_res = verify_usbpd_ntscpal_avfinfo_guard(
            usb_pd_volts=5.0,
            usb_pd_amps=1.5,
            require_sustained_pd_27w=False,
        )
        self.assertTrue(warn_res.valid)
        self.assertEqual(warn_res.usb_pd_watts, 7.5)
        self.assertTrue(warn_res.low_power_drain_warning)
        self.assertTrue(len(warn_res.warnings) >= 1)

        strict_res = verify_usbpd_ntscpal_avfinfo_guard(
            usb_pd_volts=5.0,
            usb_pd_amps=1.5,
            require_sustained_pd_27w=True,
        )
        self.assertFalse(strict_res.valid)
        self.assertEqual(strict_res.block_errno, EINVAL_ERRNO_PHASE373)
        self.assertIn(
            "FX3_USB_PD_BELOW_9V3A_27W_CONTINUOUS_SHOOT_INSUFFICIENT",
            strict_res.violation_codes,
        )

    def test_52_g160_mandatory_np_fz100_inserted_no_batteryless_usb_boot_eopnotsupp(self) -> None:
        self.assertFalse(FX3_BATTERY_LESS_USB_BOOT_SUPPORTED_G160)
        res = verify_usbpd_ntscpal_avfinfo_guard(
            power_source_mode="usb_c_pd",
            np_fz100_inserted=False,
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.block_errno, EOPNOTSUPP_ERRNO_PHASE373)
        self.assertIn(
            "FX3_MANDATORY_NP_FZ100_INSERTED_NO_BATTERYLESS_USB_BOOT_EOPNOTSUPP",
            res.violation_codes,
        )

    def test_53_g160_zero_soc_np_fz100_blocks_usb_pd_boot_einval(self) -> None:
        res = verify_usbpd_ntscpal_avfinfo_guard(
            power_source_mode="usb_c_pd",
            camera_power_state="ON",
            np_fz100_inserted=True,
            np_fz100_soc_pct=0,
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.block_errno, EINVAL_ERRNO_PHASE373)
        self.assertIn(
            "FX3_USB_PD_REQUIRES_SUFFICIENTLY_CHARGED_NP_FZ100",
            res.violation_codes,
        )

    def test_54_g160_hot_pull_battery_cuts_power_blocked_einval(self) -> None:
        self.assertFalse(FX3_BATTERY_HOT_SWAP_SUPPORTED_G160)
        res = verify_usbpd_ntscpal_avfinfo_guard(
            power_source_mode="usb_c_pd",
            np_fz100_inserted=True,
            hot_pull_battery_requested=True,
        )
        self.assertFalse(res.valid)
        self.assertEqual(res.block_errno, EINVAL_ERRNO_PHASE373)
        self.assertIn(
            "FX3_ZERO_BATTERY_HOT_SWAP_POWER_CUT_HAZARD",
            res.violation_codes,
        )

    def test_55_g160_on_mode_no_charge_vs_off_mode_charge_10_to_30c(self) -> None:
        self.assertFalse(FX3_CHARGES_WHILE_CAMERA_ON_G160)
        self.assertEqual(CHARGE_TEMP_MIN_C_G160, 10.0)
        self.assertEqual(CHARGE_TEMP_MAX_C_G160, 30.0)

        on_res = verify_usbpd_ntscpal_avfinfo_guard(
            camera_power_state="ON", ambient_temp_c=22.0
        )
        self.assertFalse(on_res.charging_active)
        self.assertEqual(on_res.charge_led_state, "OFF")

        off_chg = verify_usbpd_ntscpal_avfinfo_guard(
            camera_power_state="OFF", np_fz100_soc_pct=50, ambient_temp_c=20.0
        )
        self.assertTrue(off_chg.valid)
        self.assertTrue(off_chg.charging_active)
        self.assertEqual(off_chg.charge_led_state, "ON_CHARGING")

        off_full = verify_usbpd_ntscpal_avfinfo_guard(
            camera_power_state="OFF", np_fz100_soc_pct=100, ambient_temp_c=20.0
        )
        self.assertTrue(off_full.valid)
        self.assertFalse(off_full.charging_active)
        self.assertEqual(off_full.charge_led_state, "OFF_FULL")

        off_cold = verify_usbpd_ntscpal_avfinfo_guard(
            camera_power_state="OFF", np_fz100_soc_pct=50, ambient_temp_c=5.0
        )
        self.assertTrue(off_cold.valid)
        self.assertFalse(off_cold.charging_active)
        self.assertEqual(off_cold.charge_led_state, "FAST_BLINK_TEMP_FAULT")

    def test_56_g160_claimed_on_mode_charge_or_out_of_temp_charge_blocked(self) -> None:
        r1 = verify_usbpd_ntscpal_avfinfo_guard(claimed_charges_while_camera_on=True)
        self.assertFalse(r1.valid)
        self.assertEqual(r1.block_errno, EINVAL_ERRNO_PHASE373)
        self.assertIn("FX3_ON_MODE_NO_BATTERY_CHARGE_VIOLATION", r1.violation_codes)

        r2 = verify_usbpd_ntscpal_avfinfo_guard(
            camera_power_state="OFF",
            ambient_temp_c=35.0,
            claimed_charge_outside_10_30c=True,
        )
        self.assertFalse(r2.valid)
        self.assertEqual(r2.block_errno, EINVAL_ERRNO_PHASE373)
        self.assertIn(
            "FX3_OFF_MODE_CHARGE_TEMP_10_30C_WINDOW_VIOLATION", r2.violation_codes
        )

    def test_57_g160_dc_c1_coupler_65w_5a_and_brightness_locked_max(self) -> None:
        self.assertEqual(DC_C1_MIN_PD_WATTS_G160, 65.0)
        self.assertEqual(DC_C1_MIN_CABLE_AMPS_G160, 5.0)
        self.assertTrue(DC_C1_MONITOR_BRIGHTNESS_LOCKED_MAX_G160)

        ok = verify_usbpd_ntscpal_avfinfo_guard(
            power_source_mode="dc_c1_coupler",
            np_fz100_inserted=False,
            dc_c1_pd_watts=65.0,
            dc_c1_cable_amps=5.0,
        )
        self.assertTrue(ok.valid)
        self.assertTrue(ok.monitor_brightness_locked_max)
        self.assertEqual(ok.charge_led_state, "DC_C1_SOLID_OK")

        bad_w = verify_usbpd_ntscpal_avfinfo_guard(
            power_source_mode="dc_c1_coupler",
            np_fz100_inserted=False,
            dc_c1_pd_watts=45.0,
            dc_c1_cable_amps=5.0,
        )
        self.assertFalse(bad_w.valid)
        self.assertEqual(bad_w.block_errno, EINVAL_ERRNO_PHASE373)
        self.assertIn("DC_C1_REQUIRES_65W_PD_AND_5A_CABLE", bad_w.violation_codes)

        bad_a = verify_usbpd_ntscpal_avfinfo_guard(
            power_source_mode="dc_c1_coupler",
            np_fz100_inserted=False,
            dc_c1_pd_watts=100.0,
            dc_c1_cable_amps=3.0,
        )
        self.assertFalse(bad_a.valid)
        self.assertIn("DC_C1_REQUIRES_65W_PD_AND_5A_CABLE", bad_a.violation_codes)

        bad_br = verify_usbpd_ntscpal_avfinfo_guard(
            power_source_mode="dc_c1_coupler",
            np_fz100_inserted=False,
            dc_c1_pd_watts=65.0,
            dc_c1_cable_amps=5.0,
            claimed_dc_c1_brightness_adjustable=True,
        )
        self.assertFalse(bad_br.valid)
        self.assertIn("DC_C1_MONITOR_BRIGHTNESS_LOCKED_MAX_VIOLATION", bad_br.violation_codes)

    def test_58_g160_fx6_19_5v_dc_in_batteryless_boot_and_hot_replug_ebusy(self) -> None:
        self.assertTrue(FX6_BATTERY_LESS_BOOT_SUPPORTED_G160)
        self.assertTrue(FX6_DC_UNPLUG_TO_BPU_SEAMLESS_G160)
        self.assertFalse(FX6_USBC_BODY_POWER_SUPPORTED_G160)
        self.assertEqual(FX6_DC_IN_NOMINAL_V_G160, 19.5)

        ok = verify_usbpd_ntscpal_avfinfo_guard(
            power_source_mode="fx6_dc_in_19_5v",
            np_fz100_inserted=False,
            fx6_dc_in_voltage_v=19.5,
        )
        self.assertTrue(ok.valid)

        bad_v = verify_usbpd_ntscpal_avfinfo_guard(
            power_source_mode="fx6_dc_in_19_5v",
            np_fz100_inserted=False,
            fx6_dc_in_voltage_v=15.0,
        )
        self.assertFalse(bad_v.valid)
        self.assertIn("FX6_DC_IN_VOLTAGE_OUT_OF_SAFE_WINDOW", bad_v.violation_codes)

        busy = verify_usbpd_ntscpal_avfinfo_guard(
            power_source_mode="fx6_dc_in_19_5v",
            fx6_recording_active=True,
            fx6_dc_in_hot_replug_requested=True,
        )
        self.assertFalse(busy.valid)
        self.assertEqual(busy.block_errno, EBUSY_ERRNO_PHASE373)
        self.assertEqual(
            busy.status, STATUS_BLOCKED_G160_FX6_DC_IN_HOT_REPLUG_RECORDING_EBUSY
        )

        no_usbc = verify_usbpd_ntscpal_avfinfo_guard(requested_fx6_usbc_body_power=True)
        self.assertFalse(no_usbc.valid)
        self.assertEqual(no_usbc.block_errno, EOPNOTSUPP_ERRNO_PHASE373)
        self.assertIn("FX6_ZERO_USBC_BODY_POWER_EOPNOTSUPP", no_usbc.violation_codes)

    # ------------------------------------------------------------------
    # Gate G160: NTSC/PAL SKU Locks, Pure-XAVC Reboot & Slot 1 EROFS=30 (59..78)
    # ------------------------------------------------------------------

    def test_59_g160_sku_j1_locked_ntsc_only_eopnotsupp(self) -> None:
        self.assertEqual(NTSC_PAL_SKU_GATE_FN_G160, "lib::backup_get_ntsc_pal_selector_dst")
        self.assertEqual(NTSC_PAL_SKU_DEFAULTS_G160["J1"], "NTSC")
        ok = verify_usbpd_ntscpal_avfinfo_guard(
            sku_region_code="J1", requested_video_standard="NTSC"
        )
        self.assertTrue(ok.valid)
        self.assertEqual(ok.boot_banner_text, "")

        bad = verify_usbpd_ntscpal_avfinfo_guard(
            sku_region_code="J1", requested_video_standard="PAL"
        )
        self.assertFalse(bad.valid)
        self.assertEqual(bad.block_errno, EOPNOTSUPP_ERRNO_PHASE373)
        self.assertIn("FX3_J1_JAPAN_SKU_NTSC_ONLY_LOCKED_EOPNOTSUPP", bad.violation_codes)

    def test_60_g160_sku_ce_e33_pal_default_emits_running_on_ntsc_banner(self) -> None:
        for sku in ("CE", "E33"):
            r_pal = verify_usbpd_ntscpal_avfinfo_guard(
                sku_region_code=sku, requested_video_standard="PAL"
            )
            self.assertTrue(r_pal.valid)
            self.assertEqual(r_pal.boot_banner_text, "")

            r_ntsc = verify_usbpd_ntscpal_avfinfo_guard(
                sku_region_code=sku, requested_video_standard="NTSC"
            )
            self.assertTrue(r_ntsc.valid)
            self.assertEqual(r_ntsc.boot_banner_text, RUNNING_ON_NTSC_BANNER_G160)

    def test_61_g160_sku_u2_ntsc_default_emits_running_on_pal_banner(self) -> None:
        r_ntsc = verify_usbpd_ntscpal_avfinfo_guard(
            sku_region_code="U2", requested_video_standard="NTSC"
        )
        self.assertTrue(r_ntsc.valid)
        self.assertEqual(r_ntsc.boot_banner_text, "")

        r_pal = verify_usbpd_ntscpal_avfinfo_guard(
            sku_region_code="U2", requested_video_standard="PAL"
        )
        self.assertTrue(r_pal.valid)
        self.assertEqual(r_pal.boot_banner_text, RUNNING_ON_PAL_BANNER_G160)

    def test_62_g160_ver7_pure_xavc_reboots_without_mandatory_format(self) -> None:
        self.assertTrue(VER7_XAVC_SWITCH_REQUIRES_REBOOT_G160)
        self.assertFalse(VER7_XAVC_SWITCH_REQUIRES_FORMAT_G160)
        r_fmt = verify_usbpd_ntscpal_avfinfo_guard(
            claimed_ver7_xavc_requires_mandatory_format=True
        )
        self.assertFalse(r_fmt.valid)
        self.assertEqual(r_fmt.block_errno, EINVAL_ERRNO_PHASE373)
        self.assertIn("VER7_XAVC_NTSC_PAL_NO_MANDATORY_FORMAT_VIOLATION", r_fmt.violation_codes)

        r_noreb = verify_usbpd_ntscpal_avfinfo_guard(claimed_ntsc_pal_switch_no_reboot=True)
        self.assertFalse(r_noreb.valid)
        self.assertIn("NTSC_PAL_SWITCH_MANDATORY_REBOOT_VIOLATION", r_noreb.violation_codes)

    def test_63_g160_cross_standard_playback_isolated_eopnotsupp(self) -> None:
        self.assertFalse(CROSS_STANDARD_PLAYBACK_ALLOWED_G160)
        ok_same = verify_usbpd_ntscpal_avfinfo_guard(
            sku_region_code="U2",
            requested_video_standard="NTSC",
            avf_db_operation="playback_check",
            clip_recorded_standard="NTSC",
        )
        self.assertTrue(ok_same.valid)

        bad_cross = verify_usbpd_ntscpal_avfinfo_guard(
            sku_region_code="U2",
            requested_video_standard="PAL",
            avf_db_operation="playback_check",
            clip_recorded_standard="NTSC",
        )
        self.assertFalse(bad_cross.valid)
        self.assertEqual(bad_cross.block_errno, EOPNOTSUPP_ERRNO_PHASE373)
        self.assertIn("FX3_CROSS_STANDARD_PLAYBACK_ISOLATED_EOPNOTSUPP", bad_cross.violation_codes)

        bad_flag = verify_usbpd_ntscpal_avfinfo_guard(requested_cross_standard_playback=True)
        self.assertFalse(bad_flag.valid)
        self.assertEqual(bad_flag.block_errno, EOPNOTSUPP_ERRNO_PHASE373)

    def test_64_g160_slot1_avfinfo_create_update_recover_format_all_erofs_30(self) -> None:
        for op in ("avf_info_create", "avf_info_update", "recover_image_db", "format_card"):
            res = verify_usbpd_ntscpal_avfinfo_guard(
                avf_db_operation=op,
                target_media_slot=MEDIA_SLOT_1_PHASE373,
            )
            self.assertFalse(res.valid, f"Slot 1 {op} must fail closed")
            self.assertEqual(res.block_errno, EROFS_ERRNO_PHASE373)
            self.assertEqual(res.block_errno_name, "EROFS")
            self.assertEqual(res.status, STATUS_BLOCKED_G160_SLOT1_AVFINFO_OR_FORMAT_VAULT_EROFS)
            self.assertTrue(res.slot1_tier0_erofs_blocked)
            self.assertEqual(res.slot1_data_sector_writes, 0)
            self.assertEqual(res.emmc_nflasha_write_count, 0)

    def test_65_g160_slot2_avfinfo_ops_allowed_with_zero_slot1_writes(self) -> None:
        for op in ("avf_info_create", "avf_info_update", "recover_image_db", "format_card"):
            res = verify_usbpd_ntscpal_avfinfo_guard(
                avf_db_operation=op,
                target_media_slot=MEDIA_SLOT_2_PHASE373,
                np_fz100_soc_pct=60,
                battery_voltage_mv=7600,
            )
            self.assertTrue(res.valid, f"Slot 2 {op} should pass")
            self.assertFalse(res.slot1_tier0_erofs_blocked)
            self.assertEqual(res.slot1_data_sector_writes, 0)

    def test_66_g160_recover_image_db_depleted_battery_blocked_einval(self) -> None:
        self.assertEqual(RECOVER_DB_MIN_SOC_PCT_G160, 10)
        self.assertEqual(RECOVER_DB_MIN_VOLTAGE_MV_G160, 6400)
        r_soc = verify_usbpd_ntscpal_avfinfo_guard(
            avf_db_operation="recover_image_db",
            target_media_slot=MEDIA_SLOT_2_PHASE373,
            np_fz100_soc_pct=5,
            battery_voltage_mv=7200,
        )
        self.assertFalse(r_soc.valid)
        self.assertEqual(r_soc.block_errno, EINVAL_ERRNO_PHASE373)
        self.assertIn("RECOVER_IMAGE_DB_DEPLETED_BATTERY_BLOCKED", r_soc.violation_codes)

        r_mv = verify_usbpd_ntscpal_avfinfo_guard(
            avf_db_operation="recover_image_db",
            target_media_slot=MEDIA_SLOT_2_PHASE373,
            np_fz100_soc_pct=20,
            battery_voltage_mv=6200,
        )
        self.assertFalse(r_mv.valid)
        self.assertIn("RECOVER_IMAGE_DB_DEPLETED_BATTERY_BLOCKED", r_mv.violation_codes)

    def test_67_g160_fx6_6_system_frequencies_and_thumbnail_filtering(self) -> None:
        self.assertEqual(
            EXACT_6_FX6_SYSTEM_FREQUENCIES_G160,
            ("59.94", "50", "29.97", "25", "24", "23.98"),
        )
        self.assertTrue(FX6_THUMBNAIL_FILTERS_BY_CURRENT_FREQ_G160)
        for freq in EXACT_6_FX6_SYSTEM_FREQUENCIES_G160:
            r = verify_usbpd_ntscpal_avfinfo_guard(fx6_system_frequency_hz=freq)
            self.assertTrue(r.valid, f"FX6 freq {freq} failed")

        bad_thumb = verify_usbpd_ntscpal_avfinfo_guard(
            claimed_fx6_thumbnail_shows_all_freqs=True
        )
        self.assertFalse(bad_thumb.valid)
        self.assertEqual(bad_thumb.block_errno, EINVAL_ERRNO_PHASE373)
        self.assertIn("FX6_THUMBNAIL_FREQUENCY_FILTER_VIOLATION", bad_thumb.violation_codes)

    def test_68_g160_invalid_telemetry_fields_fail_closed_einval(self) -> None:
        bad_cases = [
            {"usb_power_supply": "Auto"},
            {"usb_port_kind": "lightning"},
            {"power_source_mode": "v_mount_raw"},
            {"camera_power_state": "SLEEP"},
            {"usb_pd_volts": -5.0},
            {"usb_pd_amps": -1.0},
            {"np_fz100_soc_pct": 105},
            {"np_fz100_soc_pct": True},
            {"battery_voltage_mv": -100},
            {"ambient_temp_c": "hot"},
            {"dc_c1_pd_watts": -10.0},
            {"dc_c1_cable_amps": -2.0},
            {"fx6_dc_in_voltage_v": -19.5},
            {"sku_region_code": "JP99"},
            {"requested_video_standard": "SECAM"},
            {"clip_recorded_standard": "SECAM"},
            {"avf_db_operation": "wipe_emmc"},
            {"target_media_slot": 3},
            {"fx6_system_frequency_hz": "120"},
            {"reset_action": "HardReset"},
        ]
        for kw in bad_cases:
            r = verify_usbpd_ntscpal_avfinfo_guard(**kw)
            self.assertFalse(r.valid, f"Should fail for {kw}")
            self.assertEqual(r.block_errno, EINVAL_ERRNO_PHASE373)
            self.assertEqual(r.status, STATUS_BLOCKED_G160_TELEMETRY_INVALID)

    def test_69_g160_exhaustive_384_state_matrix(self) -> None:
        m = compute_usbpd_ntscpal_avfinfo_matrix()
        self.assertEqual(m["total_matrix_states"], 384)
        self.assertEqual(m["on_mode_zero_charge_count"], 192)
        self.assertEqual(m["usb_power_reset_preserved_count"], 192)
        self.assertEqual(m["j1_pal_locked_count"], 64)
        self.assertEqual(m["ce_ntsc_banner_count"], 64)
        self.assertEqual(m["u2_pal_banner_count"], 64)
        self.assertGreater(m["off_mode_temp_fault_count"], 0)
        self.assertGreater(m["low_power_drain_warn_count"], 0)

    def test_70_g160_evaluate_and_alias_wrapper_match(self) -> None:
        v1, r1 = evaluate_g160_usbpd_ntscpal_avfinfo_guard(
            repo_root=REPO_ROOT, force_clean_room=True
        )
        v2, r2 = verify_usbpd_ntscpal_avfinfo_guard_with_audit(
            repo_root=REPO_ROOT, force_clean_room=True
        )
        self.assertTrue(v1.passed)
        self.assertTrue(v2.passed)
        self.assertEqual(v1.gate_id, G160)
        self.assertEqual(r1.status, STATUS_VERIFIED_G160)
        self.assertEqual(r1.status, r2.status)

    def test_71_g160_erofs_precedence_over_eopnotsupp_and_ebusy(self) -> None:
        r = verify_usbpd_ntscpal_avfinfo_guard(
            target_media_slot=MEDIA_SLOT_1_PHASE373,
            avf_db_operation="avf_info_create",
            sku_region_code="J1",
            requested_video_standard="PAL",
            fx6_recording_active=True,
            fx6_dc_in_hot_replug_requested=True,
        )
        self.assertFalse(r.valid)
        self.assertEqual(r.block_errno, EROFS_ERRNO_PHASE373)
        self.assertEqual(r.status, STATUS_BLOCKED_G160_SLOT1_AVFINFO_OR_FORMAT_VAULT_EROFS)

    def test_72_g160_battery_only_mode_valid(self) -> None:
        r = verify_usbpd_ntscpal_avfinfo_guard(
            power_source_mode="battery_only",
            np_fz100_inserted=True,
            np_fz100_soc_pct=75,
        )
        self.assertTrue(r.valid)
        self.assertFalse(r.charging_active)
        self.assertFalse(r.power_save_bypassed_by_usb_pd)
        self.assertFalse(r.monitor_brightness_locked_max)

    def test_73_g160_slot1_playback_check_readonly_allowed_same_standard(self) -> None:
        r = verify_usbpd_ntscpal_avfinfo_guard(
            avf_db_operation="playback_check",
            target_media_slot=MEDIA_SLOT_1_PHASE373,
            sku_region_code="U2",
            requested_video_standard="NTSC",
            clip_recorded_standard="NTSC",
        )
        self.assertTrue(r.valid)
        self.assertFalse(r.slot1_tier0_erofs_blocked)
        self.assertEqual(r.slot1_data_sector_writes, 0)

    def test_74_g160_off_mode_usb_charge_temp_boundary_10c_and_30c_inclusive(self) -> None:
        for t in (10.0, 30.0):
            r = verify_usbpd_ntscpal_avfinfo_guard(
                camera_power_state="OFF",
                np_fz100_soc_pct=50,
                ambient_temp_c=t,
            )
            self.assertTrue(r.valid)
            self.assertTrue(r.charging_active)
            self.assertEqual(r.charge_led_state, "ON_CHARGING")

    def test_75_g160_off_mode_usb_charge_above_30c_fast_blink_fault(self) -> None:
        r = verify_usbpd_ntscpal_avfinfo_guard(
            camera_power_state="OFF",
            np_fz100_soc_pct=50,
            ambient_temp_c=31.0,
        )
        self.assertTrue(r.valid)
        self.assertFalse(r.charging_active)
        self.assertEqual(r.charge_led_state, "FAST_BLINK_TEMP_FAULT")

    # ------------------------------------------------------------------
    # Unified 160-Gate Master Preflight Engine & Safety Locks (76..95)
    # ------------------------------------------------------------------

    def test_76_preflight_160_offline_default_157_of_160(self) -> None:
        rep = evaluate_160gate_preflight(REPO_ROOT, force_clean_room=True)
        self.assertEqual(rep.schema, REALHW_160GATE_PREFLIGHT_SCHEMA)
        self.assertEqual(rep.status, "VERIFIED_157_OF_160_AWAITING_PHYSICAL_TIER0")
        self.assertEqual(rep.summary["total_gates"], 160)
        self.assertEqual(rep.summary["verified_gates"], 157)
        self.assertEqual(rep.summary["blocked_or_pending_gates"], 3)
        self.assertTrue(rep.offline_157_gates_verified)
        self.assertFalse(rep.all_160_gates_verified)
        self.assertTrue(rep.g13_to_g160_all_passed)
        self.assertTrue(rep.g159_to_g160_all_passed)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.hardware_live_attachment_authorized)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.cross_model_flash_authorized)
        self.assertEqual(rep.usb_packets_transmitted, 0)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_77_preflight_160_dry_run_simulated_160_of_160(self) -> None:
        rep = evaluate_160gate_preflight(
            REPO_ROOT, force_clean_room=True, simulate_bench_dry_run=True
        )
        self.assertEqual(
            rep.status, "VERIFIED_ALL_160_GATES_DRY_RUN_SIMULATED_BACKUP"
        )
        self.assertEqual(rep.summary["verified_gates"], 160)
        self.assertEqual(rep.summary["blocked_or_pending_gates"], 0)
        self.assertTrue(rep.all_160_gates_verified)
        self.assertTrue(rep.dry_run_rehearsal_only)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.hardware_live_attachment_authorized)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.cross_model_flash_authorized)
        self.assertEqual(rep.usb_packets_transmitted, 0)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_78_preflight_160_blocks_persistent_emmc_writes_request(self) -> None:
        rep = evaluate_160gate_preflight(
            REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            request_persistent_emmc_writes=True,
        )
        self.assertEqual(rep.status, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        self.assertFalse(rep.offline_157_gates_verified)
        self.assertFalse(rep.all_160_gates_verified)
        self.assertFalse(rep.h0_h1_trial_entry_allowed)
        self.assertEqual(
            rep.g160_result["status"],
            STATUS_BLOCKED_G160_SLOT1_AVFINFO_OR_FORMAT_VAULT_EROFS,
        )

    def test_79_preflight_160_g159_fault_injection_propagates(self) -> None:
        rep = evaluate_160gate_preflight(
            REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            peaking_audio_wind_kwargs={"requested_wind_noise_auto": True},
        )
        self.assertEqual(
            rep.status,
            STATUS_BLOCKED_G159_DORMANT_FOCUSMAP_FX6_TYPEFREQ_AUDIOMETER_OR_WINDAUTO_EOPNOTSUPP,
        )
        self.assertFalse(rep.g159_to_g160_all_passed)
        self.assertFalse(rep.all_160_gates_verified)
        self.assertEqual(rep.summary["verified_gates"], 159)

    def test_80_preflight_160_g160_fault_injection_propagates(self) -> None:
        rep = evaluate_160gate_preflight(
            REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            usbpd_ntscpal_avfinfo_kwargs={
                "target_media_slot": MEDIA_SLOT_1_PHASE373,
                "avf_db_operation": "format_card",
            },
        )
        self.assertEqual(
            rep.status, STATUS_BLOCKED_G160_SLOT1_AVFINFO_OR_FORMAT_VAULT_EROFS
        )
        self.assertFalse(rep.g159_to_g160_all_passed)
        self.assertFalse(rep.all_160_gates_verified)
        self.assertEqual(rep.summary["verified_gates"], 159)

    def test_81_preflight_160_gate_sequence_g01_to_g160_contiguous(self) -> None:
        rep = evaluate_160gate_preflight(
            REPO_ROOT, force_clean_room=True, dry_run_simulated=True
        )
        gate_ids = [g["gate_id"] for g in rep.gates]
        self.assertEqual(len(gate_ids), 160)
        self.assertEqual(gate_ids[-2], G159)
        self.assertEqual(gate_ids[-1], G160)
        self.assertEqual(len(set(gate_ids)), 160)

    def test_82_preflight_160_no_raw_bytes_repr_in_report_dict(self) -> None:
        rep = evaluate_160gate_preflight(
            REPO_ROOT, force_clean_room=True, dry_run_simulated=True
        )
        dumped = json.dumps(rep.to_dict(), ensure_ascii=False)
        self.assertNotIn("b'\\x7fELF", dumped)
        self.assertNotIn('b"\\x7fELF', dumped)

    def test_83_preflight_160_report_has_master_158_and_g159_g160_dicts(self) -> None:
        rep = evaluate_160gate_preflight(REPO_ROOT, force_clean_room=True)
        d = rep.to_dict()
        self.assertIn("master_158_report", d)
        self.assertIn("g159_result", d)
        self.assertIn("g160_result", d)
        self.assertEqual(d["g159_result"]["gate_id"], G159)
        self.assertEqual(d["g160_result"]["gate_id"], G160)

    def test_84_backward_compatibility_158_156_154_152_150_gates(self) -> None:
        r158 = fx3_safety.evaluate_158gate_preflight(REPO_ROOT, force_clean_room=True)
        r156 = fx3_safety.evaluate_156gate_preflight(REPO_ROOT, force_clean_room=True)
        r154 = fx3_safety.evaluate_154gate_preflight(REPO_ROOT, force_clean_room=True)
        r152 = fx3_safety.evaluate_152gate_preflight(REPO_ROOT, force_clean_room=True)
        r150 = fx3_safety.evaluate_150gate_preflight(REPO_ROOT, force_clean_room=True)
        self.assertEqual(r158.summary["verified_gates"], 155)
        self.assertEqual(r156.summary["verified_gates"], 153)
        self.assertEqual(r154.summary["verified_gates"], 151)
        self.assertEqual(r152.summary["verified_gates"], 149)
        self.assertEqual(r150.summary["verified_gates"], 147)

    def test_85_simulate_bench_dry_run_alias_kwargs_and_wrapper_fns(self) -> None:
        r1 = evaluate_160_master_safety_gates(
            REPO_ROOT, force_clean_room=True, simulate_bench_dry_run=True
        )
        r2 = run_160_gate_preflight(
            REPO_ROOT, force_clean_room=True, dry_run_simulated_backup=True
        )
        r3 = verify_real_hardware_160gate_readiness(
            REPO_ROOT, force_clean_room=True, dry_run_simulated=True
        )
        self.assertEqual(r1.summary["verified_gates"], 160)
        self.assertEqual(r2.summary["verified_gates"], 160)
        self.assertEqual(r3.summary["verified_gates"], 160)

    def test_86_forward_compatible_dynamic_discovery_export(self) -> None:
        nums = sorted(
            int(name[9:-14])
            for name in dir(fx3_safety)
            if name.startswith("evaluate_")
            and name.endswith("gate_preflight")
            and name[9:-14].isdigit()
        )
        self.assertIn(160, nums)
        self.assertGreaterEqual(max(nums), 160)

    def test_87_fx3_safety_package_exports_and_all(self) -> None:
        for sym in (
            "evaluate_160gate_preflight",
            "evaluate_160_master_safety_gates",
            "run_160_gate_preflight",
            "verify_real_hardware_160gate_readiness",
            "evaluate_g159_peaking_audio_wind_guard",
            "evaluate_g160_usbpd_ntscpal_avfinfo_guard",
            "Master160GateReport",
            "realhw_peaking_audio_wind_usbpd_ntscpal_and_160gate_guard",
        ):
            self.assertTrue(hasattr(fx3_safety, sym), f"Missing export {sym}")
            self.assertIn(sym, fx3_safety.__all__)

    def test_88_init_py_phase373_exports_zero_ast_shadowing_or_duplicates(self) -> None:
        init_src = (SAFETY_ROOT / "fx3_safety" / "__init__.py").read_text(encoding="utf-8")
        tree = ast.parse(init_src)
        prev_imp = set()
        new_imp = []
        for node in tree.body:
            if isinstance(node, ast.ImportFrom):
                is_new = node.module == "realhw_peaking_audio_wind_usbpd_ntscpal_and_160gate_guard"
                for alias in node.names:
                    name = alias.asname or alias.name
                    if is_new:
                        new_imp.append(name)
                    else:
                        prev_imp.add(name)
        self.assertEqual(len(new_imp), len(set(new_imp)))
        self.assertEqual(set(new_imp) & prev_imp, set())

    def test_89_master_158_override_injection_works(self) -> None:
        m158 = fx3_safety.evaluate_158gate_preflight(
            REPO_ROOT, force_clean_room=True, dry_run_simulated=True
        )
        rep = evaluate_160gate_preflight(
            REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            master_158_override=m158,
        )
        self.assertEqual(rep.summary["verified_gates"], 160)

    def test_90_all_hardlocked_safety_booleans_and_counters_invariant(self) -> None:
        rep = evaluate_160gate_preflight(
            REPO_ROOT, force_clean_room=True, dry_run_simulated=True
        )
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.hardware_live_attachment_authorized)
        self.assertFalse(rep.persistent_emmc_writes_authorized)
        self.assertFalse(rep.emmc_writes_authorized)
        self.assertFalse(rep.persistent_write_release)
        self.assertFalse(rep.cross_model_flash_authorized)
        self.assertFalse(rep.el3_payload_transmit_authorized)
        self.assertFalse(rep.spi_nor_write_authorized)
        self.assertFalse(rep.physical_flash_auto_exec_authorized)
        self.assertFalse(rep.human_hardware_attach_token)
        self.assertEqual(rep.usb_packets_transmitted, 0)
        self.assertEqual(rep.physical_usb_packets_emitted, 0)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_91_h0_h1_trial_entry_allowed_and_auto_flash_blocked(self) -> None:
        rep_off = evaluate_160gate_preflight(REPO_ROOT, force_clean_room=True)
        rep_fail = evaluate_160gate_preflight(
            REPO_ROOT, force_clean_room=True, request_persistent_emmc_writes=True
        )
        self.assertTrue(rep_off.h0_h1_trial_entry_allowed)
        self.assertTrue(rep_off.agent_auto_flash_blocked)
        self.assertFalse(rep_fail.h0_h1_trial_entry_allowed)

    def test_92_canonical_digest_consistency_across_clean_room_modes(self) -> None:
        r_cr = evaluate_160gate_preflight(
            REPO_ROOT, force_clean_room=True, dry_run_simulated=True
        )
        with mock.patch.dict(os.environ, {ENV_CLEAN_ROOM_TEST_PHASE373: "1"}, clear=False):
            r_env = evaluate_160gate_preflight(REPO_ROOT, dry_run_simulated=True)
        s1 = strip_elapsed_seconds_recursive_phase373(
            {
                "g159": r_cr.g159_result,
                "g160": r_cr.g160_result,
            }
        )
        s2 = strip_elapsed_seconds_recursive_phase373(
            {
                "g159": r_env.g159_result,
                "g160": r_env.g160_result,
            }
        )
        d1 = hashlib.sha256(json.dumps(s1, sort_keys=True).encode()).hexdigest()
        d2 = hashlib.sha256(json.dumps(s2, sort_keys=True).encode()).hexdigest()
        self.assertEqual(d1, d2)

    def test_93_g159_g160_negative_bool_invariants_remain_false(self) -> None:
        _, r159 = evaluate_g159_peaking_audio_wind_guard(
            repo_root=REPO_ROOT, force_clean_room=True
        )
        _, r160 = evaluate_g160_usbpd_ntscpal_avfinfo_guard(
            repo_root=REPO_ROOT, force_clean_room=True
        )
        g159_d = r159.peaking_audio_wind_guard
        g160_d = r160.usbpd_ntscpal_avfinfo_guard
        self.assertFalse(g159_d["peaking_resettable_by_camset_reset"])
        self.assertFalse(g159_d["peaking_emitted_over_hdmi"])
        self.assertFalse(g159_d["fx3_inbody_focus_map_exposed"])
        self.assertFalse(g159_d["fx3_wind_noise_auto_exposed"])
        self.assertFalse(g159_d["fx6_handle_hw_low_cut_switch_present"])
        self.assertFalse(g160_d["usb_power_supply_resettable_by_camset_reset"])
        self.assertFalse(g160_d["fx3_battery_less_usb_boot_supported"])
        self.assertFalse(g160_d["fx3_battery_hot_swap_supported"])
        self.assertFalse(g160_d["fx3_charges_while_camera_on"])
        self.assertFalse(g160_d["fx6_usbc_body_power_supported"])
        self.assertFalse(g160_d["ver7_xavc_switch_requires_format"])
        self.assertFalse(g160_d["cross_standard_playback_allowed"])

    def test_94_g159_g160_no_raw_bytes_repr_in_guard_dicts(self) -> None:
        _, r159 = evaluate_g159_peaking_audio_wind_guard(
            repo_root=REPO_ROOT, force_clean_room=True
        )
        _, r160 = evaluate_g160_usbpd_ntscpal_avfinfo_guard(
            repo_root=REPO_ROOT, force_clean_room=True
        )
        for obj in (r159.to_dict(), r160.to_dict()):
            dumped = json.dumps(obj, ensure_ascii=False)
            self.assertNotIn("b'\\x7fELF", dumped)
            self.assertNotIn('b"\\x7fELF', dumped)

    def test_95_extra_upstream_kwargs_forwarding_preserved(self) -> None:
        rep = evaluate_160gate_preflight(
            REPO_ROOT,
            force_clean_room=True,
            dry_run_simulated=True,
            pbmag_varshutter_ecs_kwargs={"requested_dormant_var_shutter": True},
        )
        self.assertFalse(rep.all_160_gates_verified)
        self.assertFalse(rep.g13_to_g160_all_passed)

    # ------------------------------------------------------------------
    # CLI, Subprocess & Help Formatting Tests (96..108)
    # ------------------------------------------------------------------

    def test_96_cli_verify_160_gates_text_offline_and_dry_run(self) -> None:
        buf1 = StringIO()
        with redirect_stdout(buf1):
            rc1 = safety_cli.main(["verify-160-gates", "--clean-room"])
        buf2 = StringIO()
        with redirect_stdout(buf2):
            rc2 = safety_cli.main(
                ["verify-160-gates", "--clean-room", "--simulate-bench-dry-run"]
            )
        self.assertEqual(rc1, 0)
        self.assertEqual(rc2, 0)
        self.assertIn("verified=157/160", buf1.getvalue())
        self.assertIn("verified=160/160", buf2.getvalue())

    def test_97_cli_verify_160_gates_json_and_summary(self) -> None:
        buf = StringIO()
        with redirect_stdout(buf):
            rc = safety_cli.main(
                [
                    "verify-160-gates",
                    "--clean-room",
                    "--simulate-bench-dry-run",
                    "--json",
                    "--summary",
                ]
            )
        self.assertEqual(rc, 0)
        parsed = json.loads(buf.getvalue())
        self.assertEqual(parsed["summary"]["verified_gates"], 160)
        self.assertEqual(parsed["g159_status"], STATUS_VERIFIED_G159)
        self.assertEqual(parsed["g160_status"], STATUS_VERIFIED_G160)

    def test_98_cli_g159_and_g160_aliases_json_summary_and_text(self) -> None:
        for cmd_list in (
            ["verify-peaking-audio-wind-guard", "--clean-room", "--json", "--summary"],
            ["verify-g159-peaking-audio-wind", "--clean-room", "--json", "--summary"],
            ["verify-g159", "--clean-room"],
            ["verify-usbpd-ntscpal-avfinfo-guard", "--clean-room", "--json", "--summary"],
            ["verify-g160-usbpd-ntscpal-avfinfo", "--clean-room", "--json", "--summary"],
            ["verify-g160", "--clean-room"],
        ):
            buf = StringIO()
            with redirect_stdout(buf):
                rc = safety_cli.main(cmd_list)
            self.assertEqual(rc, 0, f"Command failed: {cmd_list}")

    def test_99_module_main_entrypoint_g159_g160_and_160(self) -> None:
        for argv in (
            ["--clean-room", "--gate", "g159", "--json", "--summary"],
            ["--clean-room", "--gate", "g160", "--json", "--summary"],
            ["--clean-room", "--gate", "160", "--simulate-bench-dry-run", "--json", "--summary"],
            ["--clean-room", "--gate", "160"],
        ):
            buf = StringIO()
            with redirect_stdout(buf):
                rc = guard_module_main(argv)
            self.assertEqual(rc, 0, f"Module CLI failed for {argv}")

    def test_100_cli_main_help_formatting_no_percent_typeerror(self) -> None:
        buf = StringIO()
        with self.assertRaises(SystemExit) as ctx:
            with redirect_stdout(buf):
                safety_cli.main(["--help"])
        self.assertEqual(ctx.exception.code, 0)
        help_out = buf.getvalue()
        self.assertIn("verify-160-gates", help_out)
        self.assertIn("verify-g159", help_out)
        self.assertIn("verify-g160", help_out)

    def test_101_subprocess_cli_verify_g159_and_g160_generous_timeout(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONPATH"] = str(SAFETY_ROOT)
        for subcmd in ("verify-g159", "verify-g160"):
            proc = subprocess.run(
                [sys.executable, "-B", "-m", "fx3_safety", subcmd, "--clean-room", "--json", "--summary"],
                cwd=str(REPO_ROOT),
                env=env,
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            data = json.loads(proc.stdout)
            self.assertTrue(data["valid"])
            self.assertEqual(data["raw_firmware_bytes_leaked"], 0)

    def test_102_subprocess_cli_verify_160_gates_offline_and_dry_run(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONPATH"] = str(SAFETY_ROOT)
        p1 = subprocess.run(
            [sys.executable, "-B", "-m", "fx3_safety", "verify-160-gates", "--clean-room", "--json", "--summary"],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        self.assertEqual(p1.returncode, 0, p1.stderr)
        d1 = json.loads(p1.stdout)
        self.assertEqual(d1["summary"]["verified_gates"], 157)
        self.assertEqual(d1["status"], "VERIFIED_157_OF_160_AWAITING_PHYSICAL_TIER0")

        p2 = subprocess.run(
            [
                sys.executable,
                "-B",
                "-m",
                "fx3_safety",
                "verify-160-gates",
                "--clean-room",
                "--simulate-bench-dry-run",
                "--json",
                "--summary",
            ],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        self.assertEqual(p2.returncode, 0, p2.stderr)
        d2 = json.loads(p2.stdout)
        self.assertEqual(d2["summary"]["verified_gates"], 160)
        self.assertEqual(d2["status"], "VERIFIED_ALL_160_GATES_DRY_RUN_SIMULATED_BACKUP")

    def test_103_g159_verdict_evidence_contains_key_tokens(self) -> None:
        v, _ = evaluate_g159_peaking_audio_wind_guard(
            repo_root=REPO_ROOT, force_clean_room=True
        )
        self.assertIn("peaking_hdmi=False", v.evidence)
        self.assertIn("fx6_type_freq_hits=0/0", v.evidence)
        self.assertIn("audio_items=5", v.evidence)
        self.assertIn("wind_auto=False", v.evidence)

    def test_104_g160_verdict_evidence_contains_key_tokens(self) -> None:
        v, _ = evaluate_g160_usbpd_ntscpal_avfinfo_guard(
            repo_root=REPO_ROOT, force_clean_room=True
        )
        self.assertIn("pwr=usb_c_pd", v.evidence)
        self.assertIn("pd_w=27.0W", v.evidence)
        self.assertIn("fz100=True", v.evidence)
        self.assertIn("s1_writes=0", v.evidence)

    def test_105_g159_mi_shoe_other_mic_allows_shoe_audio_and_bypasses_wind(self) -> None:
        r = verify_peaking_audio_wind_guard(
            mi_shoe_other_mic_attached=True,
            wind_noise_reduct="On",
            shoe_audio_format="48kHz/24bit 2ch",
        )
        self.assertTrue(r.valid)
        self.assertEqual(r.active_audio_input_source, "mi_shoe_external_mic")
        self.assertEqual(r.active_audio_channels, 2)
        self.assertTrue(r.shoe_audio_menu_selectable)
        self.assertFalse(r.wind_noise_dsp_active)

    def test_106_g160_usb_power_supply_off_disables_power_save_bypass(self) -> None:
        r = verify_usbpd_ntscpal_avfinfo_guard(
            usb_power_supply="Off",
            power_source_mode="usb_c_pd",
            camera_power_state="ON",
        )
        self.assertTrue(r.valid)
        self.assertFalse(r.power_save_bypassed_by_usb_pd)
        self.assertFalse(r.low_power_drain_warning)

    def test_107_g160_fx6_dc_in_overvoltage_blocked_einval(self) -> None:
        r = verify_usbpd_ntscpal_avfinfo_guard(
            power_source_mode="fx6_dc_in_19_5v",
            np_fz100_inserted=False,
            fx6_dc_in_voltage_v=21.5,
        )
        self.assertFalse(r.valid)
        self.assertEqual(r.block_errno, EINVAL_ERRNO_PHASE373)
        self.assertIn("FX6_DC_IN_VOLTAGE_OUT_OF_SAFE_WINDOW", r.violation_codes)

    def test_108_cli_subparser_help_g159_g160_160_no_format_errors(self) -> None:
        for cmd in ("verify-g159", "verify-g160", "verify-160-gates"):
            buf = StringIO()
            with self.assertRaises(SystemExit) as ctx:
                with redirect_stdout(buf):
                    safety_cli.main([cmd, "--help"])
            self.assertEqual(ctx.exception.code, 0)
            self.assertIn("--force-clean-room", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
