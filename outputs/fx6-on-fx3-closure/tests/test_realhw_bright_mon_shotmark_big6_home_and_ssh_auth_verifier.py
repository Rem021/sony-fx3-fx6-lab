"""Dual-mode unit tests (90 cases) for Phase 316 (`preflight-bright-monitoring-shot-mark-big6-home-and-ssh-auth`):
13th Real-Hardware Physical Bench Readiness Verifier across Waves 58-59 check groups (`A..D`).

Runs deterministically across `LOCAL_DONOR_O_RDONLY`, `FX3_CLEAN_ROOM_TEST=1`, and
`FX3_FX6_FORCE_CLEAN_ROOM=1` modes with zero `.pyc` emission, zero persistent writes,
and cross-platform CI (`sys.executable` + `15.0s` timing headroom).
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import copy
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import unittest
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[3]
for _rel in (
    "outputs/fx6-on-fx3-closure",
    "outputs/fx3-safety",
    "outputs/fx3-recovery-adapter",
    "outputs/fx3-firmware-lab",
    "outputs/fx3-vm",
):
    _cand = str(REPO_ROOT / _rel)
    if _cand not in sys.path:
        sys.path.insert(0, _cand)

import fx6_closure  # noqa: E402
from fx6_closure.__main__ import main as fx6_cli_main  # noqa: E402
from fx6_closure.realhw_card_insert_readiness_verifier import (  # noqa: E402
    GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT,
    GO_NO_GO_DRY_RUN_SIMULATED_READY,
)
from fx6_closure.realhw_sd_stageb_bundle_and_uninstaller import (  # noqa: E402
    DEFAULT_TARGET_BODY_SERIAL,
    DEFAULT_TARGET_EMMC_CID,
)
from fx6_closure.realhw_bright_mon_shotmark_big6_home_and_ssh_auth_verifier import (  # noqa: E402
    P316_BIG6_SIX_TILES,
    P316_BRIGHT_MONITORING_RESID16_HEX,
    P316_BULB_BASE_RESID16_HEX,
    P316_CHECK_GROUP_A_ID,
    P316_CHECK_GROUP_B_ID,
    P316_CHECK_GROUP_C_ID,
    P316_CHECK_GROUP_D_ID,
    P316_CREATE_DIVIDER_FRAME_RESID16_HEX,
    P316_DORMANT_AUTO_FRAMING_RESIDS,
    P316_DORMANT_AUTO_HDR_RESID16_HEX,
    P316_DORMANT_BULB_TIMER_RESID16_HEX,
    P316_DORMANT_FTP_CUT_RESIDS,
    P316_DORMANT_HTTP_AUTH_PROTOCOLS,
    P316_DORMANT_LCD_BRIGHTNESS_MODES,
    P316_ERRNO_EBUSY,
    P316_ERRNO_EINVAL,
    P316_ERRNO_EOPNOTSUPP,
    P316_ERRNO_EROFS,
    P316_FRAMING_SETTINGS_RESID16_HEX,
    P316_FRAMING_SUPPORT_ENUM,
    P316_FX3_VALID_4_FAN_MODES,
    P316_FX6_VALID_3_FAN_MODES,
    P316_GA_ERR_BRIGHT_MONITORING_CUSTOM_KEY_PASM_MF_OR_MAG_COEXIST,
    P316_GA_ERR_BULB_MECH_STILL_DRO_OR_DORMANT_BULB_TIMER_AUTO_HDR,
    P316_GA_ERR_DORMANT_DIVIDE_EXTRACT_FTPCUT_OR_SLOT1_VAULT_WRITE,
    P316_GA_ERR_MODEL_OR_FW_FLOOR,
    P316_GA_ERR_MONITOR_BRIGHTNESS_SUNNY_OR_FX6_BACKLIGHT_CONFUSION,
    P316_GB_ERR_DORMANT_BT_TC_LINK_OR_VMC_BNCM1_EXT_LK_PREREQ,
    P316_GB_ERR_USBLAN_MUTUAL_EXCLUSION_OR_KMOD_MISMATCH,
    P316_GB_ERR_WIFI_SKU_OR_REMOVED_WEP_WPA_IPSEC,
    P316_GB_ERR_ZERO_RF_AIRPLANE_MODE_FIREWALL,
    P316_GC_ERR_BIG6_HOME_FIXED_VAR_OR_ZERO_E_ND_VIOLATION,
    P316_GC_ERR_INTERVAL_7PARAM_9999_OR_SLOT1_VAULT_FIREWALL,
    P316_GC_ERR_MANUAL_FRAMING_LOCK_OR_DORMANT_AI_AUTO_FRAMING,
    P316_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION,
    P316_GD_ERR_H0_H3_IMMUTABILITY_DRIFT,
    P316_GD_ERR_SSH_ACCESS_AUTHEN_OR_DORMANT_HTTPS_HTTP_AUTH,
    P316_GD_ERR_TC_REGEN_HDMI_REC_CTRL_OR_4CH_AUDIO,
    P316_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID,
    P316_GD_ERR_ZERO_FAN_CONTROL_MAX_OR_THERMAL_GUARD,
    P316_GO_NO_GO_BLOCKED_BRIGHT_MON_SHOTMARK_BIG6_SSH_AUTH_FAILURE,
    P316_GO_NO_GO_BRIGHT_MON_SHOTMARK_BIG6_SSH_AUTH_VERIFIED,
    P316_HOME_KEY_RESIDS,
    P316_HOME_LOWER_LEFT_RESID16_HEX,
    P316_IMPORT_ROOT_CERT_RESID16_HEX,
    P316_INDOOR_5GHZ_RESID16_HEX,
    P316_INTERVAL_MAX_FILES_RAW_JH,
    P316_INTERVAL_MAX_SHOTS,
    P316_INTERVAL_SHOOT_7_PARAMS,
    P316_INTERVAL_SHOOT_FUNC_RESID16_HEX,
    P316_JPEG_HEIF_SWITCH_RESID16_HEX,
    P316_MODE_SETTINGS_RESID16_HEX,
    P316_MONITOR_BRIGHTNESS_BASE_RESID16_HEX,
    P316_OVERALL_READY_OFFLINE_AWAITING_BENCH_RECEIPTS,
    P316_PHOTO_CAPTURE_RESID16_HEX,
    P316_REMOVED_LEGACY_WIFI_PROTOCOLS,
    P316_SCHEMA,
    P316_SHOT_MARK_PB_RESIDS,
    P316_SHOT_MARK_REC_RESIDS,
    P316_SONY_HELP_GUIDE_ID,
    P316_SSHD_HOSTKEY_FINGERPRINT_RESID16_HEX,
    P316_SUNNY_WEATHER_BASE_RESID16_HEX,
    P316_SWIPE_DOWN_RESID16_HEX,
    P316_USB_LAN_CNCT_LAUNCH_RESID16_HEX,
    P316_USB_LAN_KERNEL_MODULES,
    P316_VALID_CLIP_FLAGS,
    P316_VALID_DRO_BRACKET_MODES,
    P316_VERSION,
    P316_VMC_BNCM1_ACCESSORY_CODE,
    P316_VMC_BNCM1_PART_NUMBER,
    PHASE316_E_ND_ACTUATOR_TX_COUNT,
    PHASE316_PASSIVE_TX_BYTES_EMITTED,
    PHASE316_RAW_FIRMWARE_BYTES_LEAKED,
    PHASE316_SLOT1_DATA_SECTOR_WRITES,
    PHASE316_USB_PACKETS_TRANSMITTED,
    PHASE316_WIRELESS_RF_PACKETS_EMITTED,
    PHASE_316_CHECK_GROUP_IDS,
    PHASE_316_SCHEMA,
    PHASE_316_VERSION,
    RealHwBrightMonShotMarkBig6HomeAndSshAuthReport,
    _canonical_sha256_dict,
    build_simulated_phase316_tier0_receipts,
    evaluate_p316_check_group_a_bright_monitoring_lcd_shotmark,
    evaluate_p316_check_group_b_zero_bt_tclink_wifi_usblan_airplane,
    evaluate_p316_check_group_c_big6_home_manual_nd_framing_interval,
    evaluate_p316_check_group_d_tc_regen_hdmi_rec_ssh_auth_zero_fan_tier0,
    evaluate_realhw_bright_mon_shotmark_big6_home_and_ssh_auth_preflight,
    inspect_phase316_donors_bounded,
    render_phase316_markdown,
    run_bright_mon_shotmark_big6_home_and_ssh_auth_preflight,
    verify_phase316_report,
)


def _timing_budget(base_sec: float) -> float:
    if os.environ.get("GITHUB_ACTIONS") == "true":
        return base_sec + 15.0
    return base_sec


def _pythonpath_env(extra: dict[str, str] | None = None) -> dict[str, str]:
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPATH"] = os.pathsep.join(
        str(REPO_ROOT / rel)
        for rel in (
            "outputs/fx6-on-fx3-closure",
            "outputs/fx3-safety",
            "outputs/fx3-recovery-adapter",
            "outputs/fx3-firmware-lab",
            "outputs/fx3-vm",
        )
    )
    if extra:
        env.update(extra)
    return env


def _run_cli_subprocess(
    args: list[str], *, extra_env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-B",
            "-m",
            "fx6_closure",
            "preflight-bright-monitoring-shot-mark-big6-home-and-ssh-auth",
            *args,
        ],
        cwd=str(REPO_ROOT),
        env=_pythonpath_env(extra_env),
        capture_output=True,
        text=True,
        timeout=_timing_budget(20.0),
        check=False,
    )


class TestPhase316BrightMonShotMarkBig6HomeAndSshAuthVerifier(unittest.TestCase):
    """90 dual-mode unit tests covering Phase 316 Waves 58-59 physical bench verifier."""

    # ------------------------------------------------------------------
    # 01-08: Exports, Constants & Bounded Donor Inspection
    # ------------------------------------------------------------------

    def test_01_package_all_exports_and_non_duplicate_contract(self) -> None:
        self.assertEqual(len(fx6_closure.__all__), len(set(fx6_closure.__all__)))
        for sym in (
            "PHASE_316_SCHEMA",
            "P316_SCHEMA",
            "P316_SONY_HELP_GUIDE_ID",
            "P316_BIG6_SIX_TILES",
            "P316_INTERVAL_SHOOT_7_PARAMS",
            "P316_USB_LAN_KERNEL_MODULES",
            "P316_FX3_VALID_4_FAN_MODES",
            "P316_FX6_VALID_3_FAN_MODES",
            "evaluate_p316_check_group_a_bright_monitoring_lcd_shotmark",
            "evaluate_p316_check_group_b_zero_bt_tclink_wifi_usblan_airplane",
            "evaluate_p316_check_group_c_big6_home_manual_nd_framing_interval",
            "evaluate_p316_check_group_d_tc_regen_hdmi_rec_ssh_auth_zero_fan_tier0",
            "evaluate_realhw_bright_mon_shotmark_big6_home_and_ssh_auth_preflight",
            "run_bright_mon_shotmark_big6_home_and_ssh_auth_preflight",
            "verify_phase316_report",
            "render_phase316_markdown",
        ):
            self.assertIn(sym, fx6_closure.__all__)
            self.assertTrue(hasattr(fx6_closure, sym))

    def test_02_module_constants_and_redline_zeroes(self) -> None:
        self.assertEqual(
            PHASE_316_SCHEMA, "realhw_preflight13_bright_mon_shotmark_big6_ssh_v1"
        )
        self.assertEqual(P316_SCHEMA, PHASE_316_SCHEMA)
        self.assertEqual(PHASE_316_VERSION, "316.0.0")
        self.assertEqual(P316_VERSION, "316.0.0")
        self.assertEqual(P316_SONY_HELP_GUIDE_ID, "ilc/2210")
        self.assertEqual(PHASE316_RAW_FIRMWARE_BYTES_LEAKED, 0)
        self.assertEqual(PHASE316_PASSIVE_TX_BYTES_EMITTED, 0)
        self.assertEqual(PHASE316_USB_PACKETS_TRANSMITTED, 0)
        self.assertEqual(PHASE316_WIRELESS_RF_PACKETS_EMITTED, 0)
        self.assertEqual(PHASE316_SLOT1_DATA_SECTOR_WRITES, 0)
        self.assertEqual(PHASE316_E_ND_ACTUATOR_TX_COUNT, 0)
        self.assertEqual(P316_ERRNO_EBUSY, 16)
        self.assertEqual(P316_ERRNO_EINVAL, 22)
        self.assertEqual(P316_ERRNO_EROFS, 30)
        self.assertEqual(P316_ERRNO_EOPNOTSUPP, 95)

    def test_03_check_group_ids_exact_four(self) -> None:
        self.assertEqual(len(PHASE_316_CHECK_GROUP_IDS), 4)
        self.assertEqual(
            PHASE_316_CHECK_GROUP_IDS,
            (
                P316_CHECK_GROUP_A_ID,
                P316_CHECK_GROUP_B_ID,
                P316_CHECK_GROUP_C_ID,
                P316_CHECK_GROUP_D_ID,
            ),
        )

    def test_04_donor_inspection_synthetic_clean_room_fast(self) -> None:
        t0 = time.perf_counter()
        res = inspect_phase316_donors_bounded(synthetic_clean_room=True)
        dt = time.perf_counter() - t0
        self.assertTrue(res.passed)
        self.assertEqual(res.verification_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(res.within_150ms_budget)
        self.assertEqual(res.raw_firmware_bytes_leaked, 0)
        self.assertTrue(res.appfw_is_aarch64_elf)
        self.assertTrue(res.upm_ko_is_aarch64_elf)
        self.assertEqual(res.errors, ())
        self.assertLessEqual(dt, _timing_budget(1.0))

    def test_05_donor_inspection_respects_clean_room_env_vars(self) -> None:
        with mock.patch.dict(os.environ, {"FX3_CLEAN_ROOM_TEST": "1"}, clear=False):
            r1 = inspect_phase316_donors_bounded()
            self.assertEqual(r1.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertTrue(r1.passed)
        with mock.patch.dict(os.environ, {"FX3_FX6_FORCE_CLEAN_ROOM": "1"}, clear=False):
            r2 = inspect_phase316_donors_bounded()
            self.assertEqual(r2.verification_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertTrue(r2.passed)

    def test_06_donor_inspection_missing_donors_fail_closed_when_forced_local(self) -> None:
        res = inspect_phase316_donors_bounded(
            fx6_lib_dir=Path("/nonexistent/fx6_lib"),
            fx3_modules_dir=Path("/nonexistent/fx3_mod"),
            force_clean_room=False,
        )
        self.assertFalse(res.passed)
        self.assertEqual(res.verification_mode, "LOCAL_DONOR_O_RDONLY")
        self.assertTrue(any("missing" in e.lower() for e in res.errors))

    def test_07_donor_inspection_local_or_clean_room_under_budget(self) -> None:
        t0 = time.perf_counter()
        res = inspect_phase316_donors_bounded()
        dt = time.perf_counter() - t0
        self.assertTrue(res.passed, res.errors)
        self.assertIn(res.verification_mode, ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"))
        self.assertTrue(res.within_150ms_budget)
        self.assertLessEqual(dt, _timing_budget(1.5))

    def test_08_run_alias_points_to_evaluate_function(self) -> None:
        self.assertIs(
            run_bright_mon_shotmark_big6_home_and_ssh_auth_preflight,
            evaluate_realhw_bright_mon_shotmark_big6_home_and_ssh_auth_preflight,
        )

    # ------------------------------------------------------------------
    # 09-30: Check Group A — Wave 58 §§1,2,4
    # ------------------------------------------------------------------

    def test_09_ga_defaults_pass(self) -> None:
        ga = evaluate_p316_check_group_a_bright_monitoring_lcd_shotmark()
        self.assertTrue(ga.passed, ga.errors)
        self.assertEqual(ga.check_group_id, P316_CHECK_GROUP_A_ID)
        self.assertTrue(ga.slot1_vault_firewall_enforced)
        self.assertEqual(ga.slot1_data_sector_writes, 0)
        self.assertFalse(ga.fx3_bulb_timer_present)
        self.assertFalse(ga.fx3_auto_hdr_present)
        self.assertFalse(ga.fx3_in_camera_divide_extract_present)

    def test_10_ga_rejects_wrong_model_id_fw_floor_and_help_guide(self) -> None:
        ga = evaluate_p316_check_group_a_bright_monitoring_lcd_shotmark(
            body_model_id=0x91030001,
            body_fw="1.01",
            sony_help_guide_id="ilc/9999",
        )
        self.assertFalse(ga.passed)
        self.assertGreaterEqual(
            sum(1 for e in ga.errors if P316_GA_ERR_MODEL_OR_FW_FLOOR in e), 2
        )
        self.assertFalse(
            evaluate_p316_check_group_a_bright_monitoring_lcd_shotmark(
                body_fw="1.01"
            ).passed
        )
        self.assertFalse(
            evaluate_p316_check_group_a_bright_monitoring_lcd_shotmark(
                body_fw="invalid"
            ).passed
        )

    def test_11_ga_rejects_invalid_reset_shoot_exposure_focus_enums(self) -> None:
        ga = evaluate_p316_check_group_a_bright_monitoring_lcd_shotmark(
            reset_action="FACTORY_WIPE",
            shoot_mode="CINEMA_RAW",
            exposure_mode="AUTO_PLUS",
            focus_mode="LASER_AF",
        )
        self.assertFalse(ga.passed)
        self.assertGreaterEqual(len(ga.errors), 4)

    def test_12_ga_bright_monitoring_valid_pasm_mf_and_setting_effect_off(self) -> None:
        self.assertEqual(P316_BRIGHT_MONITORING_RESID16_HEX, "0x701f")
        for exp in ("PROGRAM_AUTO", "APERTURE_PRIORITY", "SHUTTER_PRIORITY", "MANUAL_EXPOSURE"):
            ga = evaluate_p316_check_group_a_bright_monitoring_lcd_shotmark(
                exposure_mode=exp,
                focus_mode="MF",
                bright_monitoring_active=True,
                live_view_display="SETTING_EFFECT_OFF",
            )
            self.assertTrue(ga.passed, ga.errors)
            self.assertTrue(ga.bright_monitoring_active)
            self.assertEqual(ga.live_view_display, "SETTING_EFFECT_OFF")

    def test_13_ga_bright_monitoring_rejects_shoot_menu_and_power_cycle_claims(self) -> None:
        ga = evaluate_p316_check_group_a_bright_monitoring_lcd_shotmark(
            bright_monitoring_in_shoot_menu_claimed=True,
            claimed_bright_monitoring_persists_after_power_cycle=True,
            expect_bright_monitoring_blocks_focus_magnifier=True,
        )
        self.assertFalse(ga.passed)
        self.assertGreaterEqual(
            sum(
                1
                for e in ga.errors
                if P316_GA_ERR_BRIGHT_MONITORING_CUSTOM_KEY_PASM_MF_OR_MAG_COEXIST in e
            ),
            3,
        )

    def test_14_ga_bright_monitoring_rejects_non_pasm_af_or_setting_effect_on(self) -> None:
        for kwargs in (
            {
                "exposure_mode": "INTELLIGENT_AUTO",
                "focus_mode": "MF",
                "bright_monitoring_active": True,
                "live_view_display": "SETTING_EFFECT_OFF",
            },
            {
                "exposure_mode": "MANUAL_EXPOSURE",
                "focus_mode": "AF_C",
                "bright_monitoring_active": True,
                "live_view_display": "SETTING_EFFECT_OFF",
            },
            {
                "exposure_mode": "MANUAL_EXPOSURE",
                "focus_mode": "MF",
                "bright_monitoring_active": True,
                "live_view_display": "SETTING_EFFECT_ON",
            },
            {
                "bright_monitoring_active": False,
                "expect_setting_effect_on_during_bright_monitoring": True,
            },
        ):
            ga = evaluate_p316_check_group_a_bright_monitoring_lcd_shotmark(**kwargs)
            self.assertFalse(ga.passed)
            self.assertTrue(
                any(
                    P316_GA_ERR_BRIGHT_MONITORING_CUSTOM_KEY_PASM_MF_OR_MAG_COEXIST in e
                    for e in ga.errors
                )
            )

    def test_15_ga_monitor_brightness_manual_and_sunny_weather_pass(self) -> None:
        self.assertEqual(P316_MONITOR_BRIGHTNESS_BASE_RESID16_HEX, "0xe44b")
        self.assertEqual(P316_SUNNY_WEATHER_BASE_RESID16_HEX, "0xe1da")
        for lvl in (-2, -1, 0, 1, 2):
            ga = evaluate_p316_check_group_a_bright_monitoring_lcd_shotmark(
                monitor_brightness_mode="MANUAL",
                monitor_brightness_level=lvl,
            )
            self.assertTrue(ga.passed, ga.errors)
        ga_sun = evaluate_p316_check_group_a_bright_monitoring_lcd_shotmark(
            monitor_brightness_mode="SUNNY_WEATHER",
            monitor_brightness_level=0,
        )
        self.assertTrue(ga_sun.passed, ga_sun.errors)

    def test_16_ga_monitor_brightness_rejects_dormant_auto_bright_normal_and_bounds(self) -> None:
        self.assertEqual(P316_DORMANT_LCD_BRIGHTNESS_MODES, ("AUTO", "BRIGHT", "NORMAL"))
        for bad_mode in P316_DORMANT_LCD_BRIGHTNESS_MODES:
            ga = evaluate_p316_check_group_a_bright_monitoring_lcd_shotmark(
                monitor_brightness_mode=bad_mode
            )
            self.assertFalse(ga.passed)
            self.assertFalse(ga.dormant_lcd_brightness_rejected)
        ga_req = evaluate_p316_check_group_a_bright_monitoring_lcd_shotmark(
            dormant_lcd_brightness_mode_requested=True,
            monitor_brightness_level=3,
        )
        self.assertFalse(ga_req.passed)
        self.assertGreaterEqual(
            sum(
                1
                for e in ga_req.errors
                if P316_GA_ERR_MONITOR_BRIGHTNESS_SUNNY_OR_FX6_BACKLIGHT_CONFUSION in e
            ),
            2,
        )

    def test_17_ga_monitor_brightness_initialize_only_and_fx6_disambiguation(self) -> None:
        ga_reset_ok = evaluate_p316_check_group_a_bright_monitoring_lcd_shotmark(
            reset_action="CAMERA_SETTINGS_RESET",
            claimed_monitor_brightness_wiped_by_camera_reset=False,
        )
        self.assertTrue(ga_reset_ok.passed)
        ga_bad = evaluate_p316_check_group_a_bright_monitoring_lcd_shotmark(
            reset_action="CAMERA_SETTINGS_RESET",
            claimed_monitor_brightness_wiped_by_camera_reset=True,
            fx6_backlight_is_lcd_brightness_claimed=True,
            fx6_vf_brightness_1_15_in_fx3_claimed=True,
        )
        self.assertFalse(ga_bad.passed)
        self.assertGreaterEqual(len(ga_bad.errors), 2)

    def test_18_ga_rejects_dormant_divide_extract_and_ftp_cut(self) -> None:
        self.assertEqual(len(P316_DORMANT_FTP_CUT_RESIDS), 4)
        self.assertEqual(len(P316_SHOT_MARK_REC_RESIDS), 2)
        self.assertEqual(len(P316_SHOT_MARK_PB_RESIDS), 2)
        for kwargs in (
            {"dormant_divide_or_extract_requested": True},
            {"dormant_ftp_cut_15_30_60s_requested": True},
        ):
            ga = evaluate_p316_check_group_a_bright_monitoring_lcd_shotmark(**kwargs)
            self.assertFalse(ga.passed)
            self.assertFalse(ga.dormant_divide_extract_ftp_cut_rejected)
            self.assertTrue(
                any(
                    P316_GA_ERR_DORMANT_DIVIDE_EXTRACT_FTPCUT_OR_SLOT1_VAULT_WRITE in e
                    for e in ga.errors
                )
            )

    def test_19_ga_clip_flags_valid_and_invalid(self) -> None:
        self.assertEqual(P316_VALID_CLIP_FLAGS, ("NONE", "OK", "NG", "KEEP"))
        for cf in P316_VALID_CLIP_FLAGS:
            ga = evaluate_p316_check_group_a_bright_monitoring_lcd_shotmark(
                clip_flag=cf, clip_flag_write_requested=True, clip_flag_slot=2
            )
            self.assertTrue(ga.passed, ga.errors)
        ga_bad = evaluate_p316_check_group_a_bright_monitoring_lcd_shotmark(clip_flag="ESSENTIAL")
        self.assertFalse(ga_bad.passed)

    def test_20_ga_slot1_vault_blocks_shotmark_clipflag_photo_divider_edit_erofs30(self) -> None:
        self.assertEqual(P316_PHOTO_CAPTURE_RESID16_HEX, "0x6856")
        self.assertEqual(P316_JPEG_HEIF_SWITCH_RESID16_HEX, "0x7175")
        self.assertEqual(P316_CREATE_DIVIDER_FRAME_RESID16_HEX, "0x747a")
        for kwargs in (
            {"shot_mark_write_requested": True, "shot_mark_slot": 1},
            {"clip_flag": "OK", "clip_flag_write_requested": True, "clip_flag_slot": 1},
            {"photo_capture_requested": True, "photo_capture_slot": 1},
            {"create_divider_frame_requested": True, "divider_frame_slot": 1},
            {"edit_write_requested": True, "edit_write_slot": 1},
        ):
            ga = evaluate_p316_check_group_a_bright_monitoring_lcd_shotmark(
                slot1_contains_tier0_dump=True,
                slot1_wp_locked=True,
                **kwargs,
            )
            self.assertFalse(ga.passed)
            self.assertFalse(ga.slot1_vault_firewall_enforced)
            self.assertEqual(ga.slot1_data_sector_writes, 0)
            self.assertTrue(any("EROFS=30" in e for e in ga.errors))

    def test_21_ga_slot2_write_paths_allowed_when_slot1_vault_untouched(self) -> None:
        ga = evaluate_p316_check_group_a_bright_monitoring_lcd_shotmark(
            shot_mark_write_requested=True,
            shot_mark_slot=2,
            clip_flag="KEEP",
            clip_flag_write_requested=True,
            clip_flag_slot=2,
            photo_capture_requested=True,
            photo_capture_slot=2,
            create_divider_frame_requested=True,
            divider_frame_slot=2,
            edit_write_requested=True,
            edit_write_slot=2,
        )
        self.assertTrue(ga.passed, ga.errors)
        self.assertTrue(ga.slot1_vault_firewall_enforced)
        self.assertEqual(ga.slot1_data_sector_writes, 0)

    def test_22_ga_bulb_valid_mechanical_still_single_m_mode(self) -> None:
        self.assertEqual(P316_BULB_BASE_RESID16_HEX, "0xe916")
        ga = evaluate_p316_check_group_a_bright_monitoring_lcd_shotmark(
            shoot_mode="PHOTO",
            exposure_mode="MANUAL_EXPOSURE",
            bulb_enabled=True,
            shutter_type="MECHANICAL_SHUTTER",
            still_drive_mode="SINGLE_SHOOTING",
            anti_flicker_shoot="OFF",
        )
        self.assertTrue(ga.passed, ga.errors)
        self.assertTrue(ga.bulb_enabled)

    def test_23_ga_bulb_rejects_movie_non_m_electronic_cont_interval_antiflicker(self) -> None:
        for kwargs in (
            {"shoot_mode": "MOVIE", "exposure_mode": "MANUAL_EXPOSURE", "bulb_enabled": True},
            {"shoot_mode": "PHOTO", "exposure_mode": "APERTURE_PRIORITY", "bulb_enabled": True},
            {
                "shoot_mode": "PHOTO",
                "exposure_mode": "MANUAL_EXPOSURE",
                "bulb_enabled": True,
                "shutter_type": "ELECTRONIC_SHUTTER",
            },
            {
                "shoot_mode": "PHOTO",
                "exposure_mode": "MANUAL_EXPOSURE",
                "bulb_enabled": True,
                "still_drive_mode": "CONT_HI_PLUS",
            },
            {
                "shoot_mode": "PHOTO",
                "exposure_mode": "MANUAL_EXPOSURE",
                "bulb_enabled": True,
                "still_drive_mode": "INTERVAL",
            },
            {
                "shoot_mode": "PHOTO",
                "exposure_mode": "MANUAL_EXPOSURE",
                "bulb_enabled": True,
                "anti_flicker_shoot": "ON",
            },
            {"expect_bulb_in_electronic_or_cont_or_interval": True},
        ):
            ga = evaluate_p316_check_group_a_bright_monitoring_lcd_shotmark(**kwargs)
            self.assertFalse(ga.passed)
            self.assertTrue(
                any(
                    P316_GA_ERR_BULB_MECH_STILL_DRO_OR_DORMANT_BULB_TIMER_AUTO_HDR in e
                    for e in ga.errors
                )
            )

    def test_24_ga_dro_and_dro_bracket_pass_when_pp_log_hlg_off(self) -> None:
        for dro in ("AUTO", "LV1", "LV3", "LV5"):
            ga = evaluate_p316_check_group_a_bright_monitoring_lcd_shotmark(
                shoot_mode="PHOTO",
                dro_mode=dro,
                picture_profile="OFF",
                log_shooting_mode="OFF",
                hlg_still_image="OFF",
            )
            self.assertTrue(ga.passed, ga.errors)
        for brk in P316_VALID_DRO_BRACKET_MODES:
            if brk == "OFF":
                continue
            ga_brk = evaluate_p316_check_group_a_bright_monitoring_lcd_shotmark(
                shoot_mode="PHOTO",
                dro_bracket_mode=brk,
                picture_profile="OFF",
                log_shooting_mode="OFF",
                hlg_still_image="OFF",
            )
            self.assertTrue(ga_brk.passed, ga_brk.errors)

    def test_25_ga_dro_locked_out_by_pp_log_or_hlg_still(self) -> None:
        for kwargs in (
            {"dro_mode": "AUTO", "picture_profile": "PP11", "log_shooting_mode": "OFF"},
            {"dro_mode": "LV2", "picture_profile": "OFF", "log_shooting_mode": "CINE_EI"},
            {
                "dro_bracket_mode": "DRO_BRK_HI_3",
                "picture_profile": "OFF",
                "log_shooting_mode": "OFF",
                "hlg_still_image": "ON",
            },
            {"expect_dro_active_with_pp_or_hlg": True},
        ):
            ga = evaluate_p316_check_group_a_bright_monitoring_lcd_shotmark(**kwargs)
            self.assertFalse(ga.passed)
            self.assertTrue(
                any(
                    P316_GA_ERR_BULB_MECH_STILL_DRO_OR_DORMANT_BULB_TIMER_AUTO_HDR in e
                    for e in ga.errors
                )
            )

    def test_26_ga_rejects_dormant_bulb_timer_and_auto_hdr_eopnotsupp95(self) -> None:
        self.assertEqual(P316_DORMANT_BULB_TIMER_RESID16_HEX, "0x630f")
        self.assertEqual(P316_DORMANT_AUTO_HDR_RESID16_HEX, "0xe49d")
        ga = evaluate_p316_check_group_a_bright_monitoring_lcd_shotmark(
            dormant_bulb_timer_requested=True,
            dormant_auto_hdr_requested=True,
        )
        self.assertFalse(ga.passed)
        self.assertFalse(ga.fx3_bulb_timer_present)
        self.assertFalse(ga.fx3_auto_hdr_present)
        self.assertTrue(any("0x630f" in e and "EOPNOTSUPP=95" in e for e in ga.errors))
        self.assertTrue(any("0xe49d" in e and "EOPNOTSUPP=95" in e for e in ga.errors))
        self.assertGreaterEqual(len(ga.errors), 2)

    def test_27_ga_invalid_clip_shutter_drive_dro_enums_rejected(self) -> None:
        ga = evaluate_p316_check_group_a_bright_monitoring_lcd_shotmark(
            shutter_type="GLOBAL_SHUTTER",
            still_drive_mode="ULTRA_BURST",
            anti_flicker_shoot="MAYBE",
            dro_mode="LV9",
            dro_bracket_mode="HDR_BRK",
            hlg_still_image="AUTO",
        )
        self.assertFalse(ga.passed)
        self.assertGreaterEqual(len(ga.errors), 6)

    def test_28_ga_bulb_allows_self_timer_single_and_rejects_self_timer_cont_or_bracket(self) -> None:
        ga_ok = evaluate_p316_check_group_a_bright_monitoring_lcd_shotmark(
            shoot_mode="PHOTO",
            exposure_mode="MANUAL_EXPOSURE",
            bulb_enabled=True,
            shutter_type="MECHANICAL_SHUTTER",
            still_drive_mode="SELF_TIMER_SINGLE",
        )
        self.assertTrue(ga_ok.passed, ga_ok.errors)
        for bad_drive in ("SELF_TIMER_CONT", "BRACKET"):
            ga_bad = evaluate_p316_check_group_a_bright_monitoring_lcd_shotmark(
                shoot_mode="PHOTO",
                exposure_mode="MANUAL_EXPOSURE",
                bulb_enabled=True,
                shutter_type="MECHANICAL_SHUTTER",
                still_drive_mode=bad_drive,
            )
            self.assertFalse(ga_bad.passed)

    def test_29_ga_monitor_brightness_invalid_level_above_and_below(self) -> None:
        for bad_lvl in (-5, -3, 3, 10):
            ga = evaluate_p316_check_group_a_bright_monitoring_lcd_shotmark(
                monitor_brightness_level=bad_lvl
            )
            self.assertFalse(ga.passed)

    def test_30_ga_invariants_preserved_even_when_all_slot1_flags_spammed(self) -> None:
        ga = evaluate_p316_check_group_a_bright_monitoring_lcd_shotmark(
            shot_mark_write_requested=True,
            shot_mark_slot=1,
            clip_flag_write_requested=True,
            clip_flag_slot=1,
            photo_capture_requested=True,
            photo_capture_slot=1,
            create_divider_frame_requested=True,
            divider_frame_slot=1,
            edit_write_requested=True,
            edit_write_slot=1,
        )
        self.assertFalse(ga.passed)
        self.assertEqual(ga.slot1_data_sector_writes, 0)
        self.assertFalse(ga.fx3_bulb_timer_present)
        self.assertFalse(ga.fx3_auto_hdr_present)
        self.assertFalse(ga.fx3_in_camera_divide_extract_present)

    # ------------------------------------------------------------------
    # 31-46: Check Group B — Wave 58 §3
    # ------------------------------------------------------------------

    def test_31_gb_defaults_pass_zero_rf(self) -> None:
        gb = evaluate_p316_check_group_b_zero_bt_tclink_wifi_usblan_airplane()
        self.assertTrue(gb.passed, gb.errors)
        self.assertEqual(gb.check_group_id, P316_CHECK_GROUP_B_ID)
        self.assertFalse(gb.fx3_bt_tc_link_present)
        self.assertTrue(gb.dormant_bt_tc_link_rejected)
        self.assertTrue(gb.dormant_legacy_wifi_sec_rejected)
        self.assertTrue(gb.zero_rf_airplane_firewall_enforced)
        self.assertEqual(gb.wireless_rf_packets_emitted, 0)
        self.assertFalse(gb.rf_nvs_p12_p13_writes_authorized)

    def test_32_gb_rejects_dormant_bt_timecode_link_and_fx6_bnc_claims(self) -> None:
        for kwargs in (
            {"dormant_bt_tc_link_requested": True},
            {"fx3_bt_tc_link_present_claimed": True},
            {"fx6_bt_tc_link_claimed": True},
            {"fx3_builtin_bnc_tc_in_out_switch_claimed": True},
        ):
            gb = evaluate_p316_check_group_b_zero_bt_tclink_wifi_usblan_airplane(**kwargs)
            self.assertFalse(gb.passed)
            self.assertFalse(gb.fx3_bt_tc_link_present)
            self.assertTrue(
                any(
                    P316_GB_ERR_DORMANT_BT_TC_LINK_OR_VMC_BNCM1_EXT_LK_PREREQ in e
                    for e in gb.errors
                )
            )

    def test_33_gb_vmc_bncm1_wired_ext_lk_requires_preset_and_free_run(self) -> None:
        self.assertEqual(P316_VMC_BNCM1_PART_NUMBER, "VMC-BNCM1")
        self.assertEqual(P316_VMC_BNCM1_ACCESSORY_CODE, "A-5051-506-A")
        gb_ok = evaluate_p316_check_group_b_zero_bt_tclink_wifi_usblan_airplane(
            vmc_bncm1_ext_lk_active=True,
            tc_make="PRESET",
            tc_run="FREE_RUN",
        )
        self.assertTrue(gb_ok.passed, gb_ok.errors)
        self.assertTrue(gb_ok.vmc_bncm1_ext_lk_active)

        for bad_make, bad_run in (("REGENERATE", "FREE_RUN"), ("PRESET", "REC_RUN")):
            gb_bad = evaluate_p316_check_group_b_zero_bt_tclink_wifi_usblan_airplane(
                vmc_bncm1_ext_lk_active=True,
                tc_make=bad_make,
                tc_run=bad_run,
            )
            self.assertFalse(gb_bad.passed)

    def test_34_gb_dual_sku_wifi_ww728473_5ghz_allowed_and_ww558244_5ghz_blocked(self) -> None:
        self.assertEqual(P316_INDOOR_5GHZ_RESID16_HEX, "0x6953")
        gb_dual = evaluate_p316_check_group_b_zero_bt_tclink_wifi_usblan_airplane(
            wifi_sku="WW728473",
            wifi_band_5ghz_requested=True,
        )
        self.assertTrue(gb_dual.passed, gb_dual.errors)

        gb_24_only = evaluate_p316_check_group_b_zero_bt_tclink_wifi_usblan_airplane(
            wifi_sku="WW558244",
            wifi_band_5ghz_requested=True,
        )
        self.assertFalse(gb_24_only.passed)
        self.assertTrue(
            any(P316_GB_ERR_WIFI_SKU_OR_REMOVED_WEP_WPA_IPSEC in e for e in gb_24_only.errors)
        )

    def test_35_gb_rejects_outdoor_5ghz_w52(self) -> None:
        gb = evaluate_p316_check_group_b_zero_bt_tclink_wifi_usblan_airplane(
            wifi_sku="WW728473",
            wifi_band_5ghz_requested=True,
            outdoor_5ghz_w52_requested=True,
        )
        self.assertFalse(gb.passed)
        self.assertTrue(any("0x6953" in e for e in gb.errors))

    def test_36_gb_rejects_removed_wep_wpa_psk_and_ipsec_eopnotsupp95(self) -> None:
        self.assertEqual(P316_REMOVED_LEGACY_WIFI_PROTOCOLS, ("WEP", "WPA_PSK", "IPSEC"))
        for proto in P316_REMOVED_LEGACY_WIFI_PROTOCOLS:
            gb = evaluate_p316_check_group_b_zero_bt_tclink_wifi_usblan_airplane(
                wifi_security_protocol=proto
            )
            self.assertFalse(gb.passed)
            self.assertFalse(gb.dormant_legacy_wifi_sec_rejected)
        gb_flag = evaluate_p316_check_group_b_zero_bt_tclink_wifi_usblan_airplane(
            dormant_legacy_wifi_sec_requested=True
        )
        self.assertFalse(gb_flag.passed)
        self.assertFalse(gb_flag.dormant_legacy_wifi_sec_rejected)

    def test_37_gb_usb_lan_cdc_ncm_wired_with_airplane_on_passes(self) -> None:
        self.assertEqual(P316_USB_LAN_CNCT_LAUNCH_RESID16_HEX, "0x7d2a")
        self.assertEqual(len(P316_USB_LAN_KERNEL_MODULES), 8)
        gb = evaluate_p316_check_group_b_zero_bt_tclink_wifi_usblan_airplane(
            usb_lan_cnct_launch="ON",
            network_transport="USB_LAN",
            airplane_mode="ON",
            wifi_enabled=False,
            multi_micro_usb_device_attached=False,
            vmc_bncm1_ext_lk_active=False,
        )
        self.assertTrue(gb.passed, gb.errors)
        self.assertEqual(gb.usb_lan_kernel_module_count, 8)
        self.assertTrue(gb.zero_rf_airplane_firewall_enforced)

    def test_38_gb_usb_lan_rejects_missing_kmods(self) -> None:
        gb = evaluate_p316_check_group_b_zero_bt_tclink_wifi_usblan_airplane(
            exposed_usb_lan_kmods=("cdc_ether.ko", "usbnet.ko")
        )
        self.assertFalse(gb.passed)
        self.assertTrue(
            any(P316_GB_ERR_USBLAN_MUTUAL_EXCLUSION_OR_KMOD_MISMATCH in e for e in gb.errors)
        )

    def test_39_gb_usb_lan_mutually_exclusive_with_multi_micro_usb_vmc_and_wifi(self) -> None:
        for kwargs in (
            {"network_transport": "USB_LAN", "multi_micro_usb_device_attached": True},
            {"network_transport": "USB_LAN", "vmc_bncm1_ext_lk_active": True},
            {"network_transport": "USB_LAN", "wifi_enabled": True},
        ):
            gb = evaluate_p316_check_group_b_zero_bt_tclink_wifi_usblan_airplane(**kwargs)
            self.assertFalse(gb.passed)
            self.assertTrue(
                any(
                    P316_GB_ERR_USBLAN_MUTUAL_EXCLUSION_OR_KMOD_MISMATCH in e
                    for e in gb.errors
                )
            )

    def test_40_gb_zero_rf_blocks_airplane_off_wifi_bt_and_rf_packets(self) -> None:
        for kwargs in (
            {"airplane_mode": "OFF"},
            {"network_transport": "WIRELESS_RF"},
            {"wifi_enabled": True},
            {"bluetooth_enabled": True},
            {"wireless_rf_packets_emitted": 1},
            {"rf_nvs_p12_p13_writes_requested": True},
        ):
            gb = evaluate_p316_check_group_b_zero_bt_tclink_wifi_usblan_airplane(**kwargs)
            self.assertFalse(gb.passed)
            self.assertFalse(gb.zero_rf_airplane_firewall_enforced)
            self.assertEqual(gb.wireless_rf_packets_emitted, 0)
            self.assertFalse(gb.rf_nvs_p12_p13_writes_authorized)
            self.assertTrue(
                any(P316_GB_ERR_ZERO_RF_AIRPLANE_MODE_FIREWALL in e for e in gb.errors)
            )

    def test_41_gb_airplane_mode_persists_across_reset_network_set_and_initialize(self) -> None:
        for action in ("RESET_NETWORK_SET", "INITIALIZE"):
            gb_ok = evaluate_p316_check_group_b_zero_bt_tclink_wifi_usblan_airplane(
                reset_action=action, claimed_airplane_wiped_by_reset=False
            )
            self.assertTrue(gb_ok.passed, gb_ok.errors)
            gb_bad = evaluate_p316_check_group_b_zero_bt_tclink_wifi_usblan_airplane(
                reset_action=action, claimed_airplane_wiped_by_reset=True
            )
            self.assertFalse(gb_bad.passed)

    def test_42_gb_invalid_wifi_usb_airplane_enums_fail_closed(self) -> None:
        gb = evaluate_p316_check_group_b_zero_bt_tclink_wifi_usblan_airplane(
            wifi_sku="WW999999",
            wifi_security_protocol="TKIP_BOGUS",
            usb_lan_cnct_launch="AUTO",
            network_transport="CELLULAR_5G",
            airplane_mode="HALF",
        )
        self.assertFalse(gb.passed)
        self.assertGreaterEqual(len(gb.errors), 5)

    def test_43_gb_ww558244_24ghz_config_without_5ghz_request_passes_when_airplane_on(self) -> None:
        gb = evaluate_p316_check_group_b_zero_bt_tclink_wifi_usblan_airplane(
            wifi_sku="WW558244",
            wifi_band_5ghz_requested=False,
            wifi_security_protocol="WPA2_PSK",
            airplane_mode="ON",
        )
        self.assertTrue(gb.passed, gb.errors)

    def test_44_gb_vmc_bncm1_and_usb_lan_off_passes_coexistence_free(self) -> None:
        gb = evaluate_p316_check_group_b_zero_bt_tclink_wifi_usblan_airplane(
            vmc_bncm1_ext_lk_active=True,
            network_transport="NONE",
            multi_micro_usb_device_attached=True,
        )
        self.assertTrue(gb.passed, gb.errors)

    def test_45_gb_zero_rf_invariants_remain_locked_on_multi_fault(self) -> None:
        gb = evaluate_p316_check_group_b_zero_bt_tclink_wifi_usblan_airplane(
            airplane_mode="OFF",
            wifi_enabled=True,
            bluetooth_enabled=True,
            wireless_rf_packets_emitted=99,
            rf_nvs_p12_p13_writes_requested=True,
        )
        self.assertEqual(gb.wireless_rf_packets_emitted, 0)
        self.assertFalse(gb.rf_nvs_p12_p13_writes_authorized)
        self.assertFalse(gb.fx3_bt_tc_link_present)

    def test_46_gb_none_wifi_sku_passes_with_none_security(self) -> None:
        gb = evaluate_p316_check_group_b_zero_bt_tclink_wifi_usblan_airplane(
            wifi_sku="NONE", wifi_security_protocol="NONE"
        )
        self.assertTrue(gb.passed, gb.errors)

    # ------------------------------------------------------------------
    # 47-64: Check Group C — Wave 59 §§1-2
    # ------------------------------------------------------------------

    def test_47_gc_defaults_and_active_big6_home_fixed_var_pass(self) -> None:
        self.assertEqual(P316_MODE_SETTINGS_RESID16_HEX, "0x7d0d")
        self.assertEqual(P316_HOME_KEY_RESIDS, ("0x7cad", "0x7cb1"))
        self.assertEqual(P316_SWIPE_DOWN_RESID16_HEX, "0x7cdd")
        self.assertEqual(P316_HOME_LOWER_LEFT_RESID16_HEX, "0x7ce3")
        self.assertEqual(len(P316_BIG6_SIX_TILES), 6)

        for trig in ("CUSTOM_KEY_HOME", "SWIPE_DOWN"):
            for ll in ("APERTURE", "ND_FILTER"):
                gc = evaluate_p316_check_group_c_big6_home_manual_nd_framing_interval(
                    shoot_mode="MOVIE",
                    mode_settings="FIXED_VARIABLE",
                    big6_home_screen_active=True,
                    home_trigger_method=trig,
                    home_lower_left_mode=ll,
                )
                self.assertTrue(gc.passed, gc.errors)
                self.assertEqual(gc.big6_tile_count, 6)
                self.assertFalse(gc.fx3_physical_e_nd_present)
                self.assertEqual(gc.e_nd_actuator_tx_count, 0)

    def test_48_gc_big6_home_rejects_legacy_mode_photo_or_wrong_tile_count(self) -> None:
        for kwargs in (
            {"mode_settings": "LEGACY", "big6_home_screen_active": True},
            {"shoot_mode": "PHOTO", "big6_home_screen_active": True},
            {"exposed_big6_tiles": P316_BIG6_SIX_TILES[:5]},
            {"claimed_menu_fn_do_not_exit_home": True},
            {"expect_big6_displays_pp_during_log": True},
            {"expect_big6_displays_variable_iso_in_cine_ei": True},
        ):
            gc = evaluate_p316_check_group_c_big6_home_manual_nd_framing_interval(**kwargs)
            self.assertFalse(gc.passed)
            self.assertTrue(
                any(
                    P316_GC_ERR_BIG6_HOME_FIXED_VAR_OR_ZERO_E_ND_VIOLATION in e
                    for e in gc.errors
                )
            )

    def test_49_gc_critical_zero_physical_e_nd_actuator_firewall(self) -> None:
        for kwargs in (
            {"fx3_physical_e_nd_claimed": True},
            {"e_nd_actuator_tx_count": 1},
        ):
            gc = evaluate_p316_check_group_c_big6_home_manual_nd_framing_interval(**kwargs)
            self.assertFalse(gc.passed)
            self.assertFalse(gc.fx3_physical_e_nd_present)
            self.assertEqual(gc.e_nd_actuator_tx_count, 0)
            self.assertTrue(any("ZERO physical built-in e-ND" in e for e in gc.errors))

    def test_50_gc_manual_framing_settings_independent_rec_vs_hdmi_pass(self) -> None:
        self.assertEqual(P316_FRAMING_SETTINGS_RESID16_HEX, "0x7d18")
        self.assertEqual(P316_FRAMING_SUPPORT_ENUM, "TYPE_EFRAMING_SUPPORT_TYPE_MANUAL_ONLY")
        for rec_area, hdmi_area in (("FULL", "CROP"), ("CROP", "FULL"), ("CROP", "CROP")):
            gc = evaluate_p316_check_group_c_big6_home_manual_nd_framing_interval(
                framing_enabled="ON",
                framing_rec_stream_area=rec_area,
                framing_hdmi_area=hdmi_area,
                apsc_s35_on=False,
                rec_fps=59.94,
                sq_fps=60.0,
            )
            self.assertTrue(gc.passed, gc.errors)

    def test_51_gc_manual_framing_locked_by_apsc_100p_120p_or_active_rec(self) -> None:
        for kwargs in (
            {"framing_enabled": "ON", "apsc_s35_on": True},
            {"framing_enabled": "ON", "rec_fps": 119.88},
            {"framing_enabled": "ON", "rec_fps": 100.0},
            {"framing_enabled": "ON", "sq_fps": 120.0},
            {"framing_enabled": "ON", "active_rec_or_stream_during_framing_toggle": True},
        ):
            gc = evaluate_p316_check_group_c_big6_home_manual_nd_framing_interval(**kwargs)
            self.assertFalse(gc.passed)
            self.assertTrue(
                any(
                    P316_GC_ERR_MANUAL_FRAMING_LOCK_OR_DORMANT_AI_AUTO_FRAMING in e
                    for e in gc.errors
                )
            )

    def test_52_gc_rejects_dormant_ai_auto_framing_eopnotsupp95(self) -> None:
        self.assertEqual(len(P316_DORMANT_AUTO_FRAMING_RESIDS), 5)
        for kwargs in (
            {"dormant_auto_framing_requested": True},
            {"fx3_auto_framing_present_claimed": True},
        ):
            gc = evaluate_p316_check_group_c_big6_home_manual_nd_framing_interval(**kwargs)
            self.assertFalse(gc.passed)
            self.assertFalse(gc.fx3_auto_framing_present)
            self.assertFalse(gc.dormant_auto_framing_rejected)
            self.assertTrue(any("AUTO_FRAMING_AFR" in e for e in gc.errors))

    def test_53_gc_interval_shoot_func_7_params_up_to_9999_slot2_passes(self) -> None:
        self.assertEqual(P316_INTERVAL_SHOOT_FUNC_RESID16_HEX, "0x7027")
        self.assertEqual(len(P316_INTERVAL_SHOOT_7_PARAMS), 7)
        self.assertEqual(P316_INTERVAL_MAX_SHOTS, 9999)
        self.assertEqual(P316_INTERVAL_MAX_FILES_RAW_JH, 19998)
        gc = evaluate_p316_check_group_c_big6_home_manual_nd_framing_interval(
            shoot_mode="PHOTO",
            exposure_mode="MANUAL_EXPOSURE",
            interval_shooting_active=True,
            interval_start_sec=5999,
            interval_sec=60,
            interval_num_shots=9999,
            interval_ae_tracking="LOW",
            interval_shutter_type="MECHANICAL",
            interval_shoot_priority="ON",
            interval_target_slot=2,
        )
        self.assertTrue(gc.passed, gc.errors)
        self.assertEqual(gc.interval_param_count, 7)
        self.assertEqual(gc.interval_num_shots, 9999)
        self.assertTrue(gc.slot1_interval_vault_firewall_enforced)

    def test_54_gc_critical_slot1_tier0_vault_blocks_interval_shoot_slot1_erofs30(self) -> None:
        gc = evaluate_p316_check_group_c_big6_home_manual_nd_framing_interval(
            shoot_mode="PHOTO",
            exposure_mode="MANUAL_EXPOSURE",
            interval_shooting_active=True,
            interval_num_shots=9999,
            interval_target_slot=1,
            slot1_contains_tier0_dump=True,
            slot1_wp_locked=True,
        )
        self.assertFalse(gc.passed)
        self.assertFalse(gc.slot1_interval_vault_firewall_enforced)
        self.assertEqual(gc.slot1_data_sector_writes, 0)
        self.assertTrue(any("EROFS=30" in e and "19,998" in e for e in gc.errors))

    def test_55_gc_interval_rejects_movie_iauto_bulb_reset_survival_or_fx6_mxf(self) -> None:
        for kwargs in (
            {"shoot_mode": "MOVIE", "interval_shooting_active": True},
            {"shoot_mode": "PHOTO", "exposure_mode": "INTELLIGENT_AUTO", "interval_shooting_active": True},
            {"shoot_mode": "PHOTO", "bulb_enabled": True, "interval_shooting_active": True},
            {
                "reset_action": "CAMERA_SETTINGS_RESET",
                "claimed_interval_7params_survive_camera_reset": True,
            },
            {"fx3_interval_outputs_single_mxf_claimed": True},
        ):
            gc = evaluate_p316_check_group_c_big6_home_manual_nd_framing_interval(**kwargs)
            self.assertFalse(gc.passed)
            self.assertTrue(
                any(
                    P316_GC_ERR_INTERVAL_7PARAM_9999_OR_SLOT1_VAULT_FIREWALL in e
                    for e in gc.errors
                )
            )

    def test_56_gc_interval_rejects_out_of_range_bounds_and_param_count(self) -> None:
        gc = evaluate_p316_check_group_c_big6_home_manual_nd_framing_interval(
            exposed_interval_params=P316_INTERVAL_SHOOT_7_PARAMS[:6],
            interval_start_sec=6000,
            interval_sec=61,
            interval_num_shots=10000,
            interval_ae_tracking="ULTRA",
            interval_shutter_type="LEAF",
            interval_shoot_priority="MAYBE",
        )
        self.assertFalse(gc.passed)
        self.assertGreaterEqual(len(gc.errors), 7)

    def test_57_gc_big6_sq_mode_passes(self) -> None:
        gc = evaluate_p316_check_group_c_big6_home_manual_nd_framing_interval(
            shoot_mode="S_AND_Q",
            mode_settings="FIXED_VARIABLE",
            big6_home_screen_active=True,
            home_trigger_method="CUSTOM_KEY_HOME",
        )
        self.assertTrue(gc.passed, gc.errors)

    def test_58_gc_invalid_big6_and_framing_enums_rejected(self) -> None:
        gc = evaluate_p316_check_group_c_big6_home_manual_nd_framing_interval(
            mode_settings="CUSTOM",
            home_trigger_method="SHAKE",
            home_lower_left_mode="ISO",
            framing_enabled="AUTO",
            framing_rec_stream_area="ULTRA_WIDE",
            framing_hdmi_area="PAN",
        )
        self.assertFalse(gc.passed)
        self.assertGreaterEqual(len(gc.errors), 5)

    def test_59_gc_interval_camera_settings_reset_resets_7params_passes_when_accurate(self) -> None:
        gc = evaluate_p316_check_group_c_big6_home_manual_nd_framing_interval(
            reset_action="CAMERA_SETTINGS_RESET",
            claimed_interval_7params_survive_camera_reset=False,
        )
        self.assertTrue(gc.passed, gc.errors)

    def test_60_gc_invariants_locked_even_on_multi_fault(self) -> None:
        gc = evaluate_p316_check_group_c_big6_home_manual_nd_framing_interval(
            fx3_physical_e_nd_claimed=True,
            e_nd_actuator_tx_count=17,
            dormant_auto_framing_requested=True,
            interval_shooting_active=True,
            interval_target_slot=1,
        )
        self.assertFalse(gc.fx3_physical_e_nd_present)
        self.assertEqual(gc.e_nd_actuator_tx_count, 0)
        self.assertFalse(gc.fx3_auto_framing_present)
        self.assertEqual(gc.slot1_data_sector_writes, 0)

    def test_61_gc_big6_displays_pp_during_log_off_still_rejected(self) -> None:
        gc = evaluate_p316_check_group_c_big6_home_manual_nd_framing_interval(
            log_shooting_mode="OFF",
            expect_big6_displays_pp_during_log=True,
        )
        self.assertFalse(gc.passed)

    def test_62_gc_interval_zero_shots_and_zero_interval_rejected(self) -> None:
        for kwargs in (
            {"interval_start_sec": 0},
            {"interval_sec": 0},
            {"interval_num_shots": 0},
        ):
            gc = evaluate_p316_check_group_c_big6_home_manual_nd_framing_interval(**kwargs)
            self.assertFalse(gc.passed)

    def test_63_gc_framing_off_with_apsc_and_120p_passes(self) -> None:
        gc = evaluate_p316_check_group_c_big6_home_manual_nd_framing_interval(
            framing_enabled="OFF",
            apsc_s35_on=True,
            rec_fps=119.88,
            sq_fps=120.0,
        )
        self.assertTrue(gc.passed, gc.errors)

    def test_64_gc_interval_slot1_without_dump_or_wp_passes(self) -> None:
        gc = evaluate_p316_check_group_c_big6_home_manual_nd_framing_interval(
            shoot_mode="PHOTO",
            interval_shooting_active=True,
            interval_target_slot=1,
            slot1_contains_tier0_dump=False,
            slot1_wp_locked=False,
        )
        self.assertTrue(gc.passed, gc.errors)

    # ------------------------------------------------------------------
    # 65-82: Check Group D — Wave 59 §§3-4, Tier-0, Tamper & Markdown
    # ------------------------------------------------------------------

    def test_65_gd_tc_regenerate_forces_rec_run_and_slot1_simult_and_rejects_clock_claim(self) -> None:
        gd_ok, _ = evaluate_p316_check_group_d_tc_regen_hdmi_rec_ssh_auth_zero_fan_tier0(
            tc_make="REGENERATE",
            tc_run="REC_RUN",
            simult_recording=True,
            tc_regen_source_slot=1,
            simulate_bench_dry_run=True,
        )
        self.assertTrue(gd_ok.passed, gd_ok.errors)

        for kwargs in (
            {"tc_make": "REGENERATE", "tc_run": "FREE_RUN"},
            {"tc_make": "REGENERATE", "tc_run": "REC_RUN", "simult_recording": True, "tc_regen_source_slot": 2},
            {"tc_make": "REGENERATE", "tc_run": "REC_RUN", "vmc_bncm1_ext_lk_active": True},
            {"reset_action": "CAMERA_SETTINGS_RESET", "claimed_tc_make_run_wiped_by_camera_reset": True},
            {"fx3_has_clock_tc_mode_claimed": True},
        ):
            gd_bad, _ = evaluate_p316_check_group_d_tc_regen_hdmi_rec_ssh_auth_zero_fan_tier0(**kwargs)
            self.assertFalse(gd_bad.passed)
            self.assertTrue(
                any(P316_GD_ERR_TC_REGEN_HDMI_REC_CTRL_OR_4CH_AUDIO in e for e in gd_bad.errors)
            )

    def test_66_gd_hdmi_rec_control_gated_on_tc_output_and_works_in_hdmi_only(self) -> None:
        for rec_media_mode in ("ON", "OFF_HDMI_ONLY"):
            gd_ok, _ = evaluate_p316_check_group_d_tc_regen_hdmi_rec_ssh_auth_zero_fan_tier0(
                hdmi_tc_output="ON",
                hdmi_rec_control="ON",
                rec_media_dur_hdmi_output=rec_media_mode,
                hdmi_4ch_audio_output="CH3_CH4",
                simulate_bench_dry_run=True,
            )
            self.assertTrue(gd_ok.passed, gd_ok.errors)

        for kwargs in (
            {"hdmi_tc_output": "OFF", "hdmi_rec_control": "ON"},
            {"hdmi_tc_output": "ON", "hdmi_rec_control": "ON", "rec_media_dur_hdmi_output": "OFF"},
            {"hdmi_tc_output": "ON", "hdmi_rec_control": "ON", "shoot_mode": "S_AND_Q"},
            {"hdmi_tc_output": "ON", "hdmi_rec_control": "ON", "streaming_active": True},
        ):
            gd_bad, _ = evaluate_p316_check_group_d_tc_regen_hdmi_rec_ssh_auth_zero_fan_tier0(**kwargs)
            self.assertFalse(gd_bad.passed)

    def test_67_gd_ssh_access_authen_and_rejects_dormant_https_digest_basic(self) -> None:
        self.assertEqual(P316_SSHD_HOSTKEY_FINGERPRINT_RESID16_HEX, "0x610b")
        self.assertEqual(P316_IMPORT_ROOT_CERT_RESID16_HEX, "0x7940")
        self.assertEqual(P316_DORMANT_HTTP_AUTH_PROTOCOLS, ("HTTPS", "HTTP_DIGEST", "BASIC_AUTH"))

        gd_ok, _ = evaluate_p316_check_group_d_tc_regen_hdmi_rec_ssh_auth_zero_fan_tier0(
            access_authen="ON",
            access_authen_protocol="SSH",
            reset_action="CAMERA_SETTINGS_RESET",
            claimed_access_authen_wiped_by_camera_reset=False,
            simulate_bench_dry_run=True,
        )
        self.assertTrue(gd_ok.passed, gd_ok.errors)

        for proto in P316_DORMANT_HTTP_AUTH_PROTOCOLS:
            gd_bad, _ = evaluate_p316_check_group_d_tc_regen_hdmi_rec_ssh_auth_zero_fan_tier0(
                access_authen_protocol=proto
            )
            self.assertFalse(gd_bad.passed)
            self.assertFalse(gd_bad.dormant_http_auth_rejected)
            self.assertTrue(
                any(
                    P316_GD_ERR_SSH_ACCESS_AUTHEN_OR_DORMANT_HTTPS_HTTP_AUTH in e
                    for e in gd_bad.errors
                )
            )

    def test_68_gd_rejects_root_cert_inbound_auth_and_camset_wipe_claims(self) -> None:
        gd, _ = evaluate_p316_check_group_d_tc_regen_hdmi_rec_ssh_auth_zero_fan_tier0(
            dormant_http_https_camera_auth_claimed=True,
            reset_action="CAMERA_SETTINGS_RESET",
            claimed_access_authen_wiped_by_camera_reset=True,
            expect_root_cert_authenticates_inbound_http_server=True,
        )
        self.assertFalse(gd.passed)
        self.assertGreaterEqual(
            sum(
                1
                for e in gd.errors
                if P316_GD_ERR_SSH_ACCESS_AUTHEN_OR_DORMANT_HTTPS_HTTP_AUTH in e
            ),
            3,
        )

    def test_69_gd_thermal_fan_myth_bust_valid_modes_fx3_4_and_fx6_3(self) -> None:
        self.assertEqual(
            P316_FX3_VALID_4_FAN_MODES, ("AUTO", "MINIMUM", "OFF_IN_REC", "ALWAYS_OFF")
        )
        self.assertEqual(P316_FX6_VALID_3_FAN_MODES, ("AUTO", "MINIMUM", "OFF_IN_REC"))
        for mode in P316_FX3_VALID_4_FAN_MODES:
            gd, _ = evaluate_p316_check_group_d_tc_regen_hdmi_rec_ssh_auth_zero_fan_tier0(
                fx3_fan_control=mode, simulate_bench_dry_run=True
            )
            self.assertTrue(gd.passed, gd.errors)
        for mode in P316_FX6_VALID_3_FAN_MODES:
            gd, _ = evaluate_p316_check_group_d_tc_regen_hdmi_rec_ssh_auth_zero_fan_tier0(
                fx6_fan_control=mode, simulate_bench_dry_run=True
            )
            self.assertTrue(gd.passed, gd.errors)

    def test_70_gd_thermal_fan_myth_bust_rejects_max_and_fx6_always_off(self) -> None:
        for kwargs in (
            {"fx3_fan_control": "MAX"},
            {"fx6_fan_control": "MAX"},
            {"dormant_fan_control_max_requested": True},
            {"fx6_fan_control": "ALWAYS_OFF"},
            {"auto_power_off_temp": "HIGH", "handheld_bare_skin_unacknowledged": True},
            {"reset_action": "CAMERA_SETTINGS_RESET", "claimed_fan_or_autotemp_wiped_by_camera_reset": True},
        ):
            gd, _ = evaluate_p316_check_group_d_tc_regen_hdmi_rec_ssh_auth_zero_fan_tier0(**kwargs)
            self.assertFalse(gd.passed)
            self.assertFalse(gd.fx3_fan_control_max_present)
            self.assertFalse(gd.fx6_fan_control_max_present)
            self.assertTrue(
                any(
                    P316_GD_ERR_ZERO_FAN_CONTROL_MAX_OR_THERMAL_GUARD in e
                    for e in gd.errors
                )
            )

    def test_71_gd_redlines_and_h0_h3_drift_fail_closed(self) -> None:
        for kwargs, err_code in (
            ({"simulated_passive_tx_bytes": 1}, P316_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION),
            ({"claim_hardware_live_attach_authorized": True}, P316_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION),
            ({"claim_persistent_emmc_writes_authorized": True}, P316_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION),
            ({"claim_cross_model_flash_authorized": True}, P316_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION),
            ({"simulated_h0_h3_drifted_surfaces": 2}, P316_GD_ERR_H0_H3_IMMUTABILITY_DRIFT),
        ):
            gd, _ = evaluate_p316_check_group_d_tc_regen_hdmi_rec_ssh_auth_zero_fan_tier0(**kwargs)
            self.assertFalse(gd.passed)
            self.assertFalse(gd.overall_ready_for_hardware_attach)
            self.assertFalse(gd.persistent_emmc_writes_authorized)
            self.assertFalse(gd.cross_model_flash_authorized)
            self.assertTrue(any(err_code in e for e in gd.errors))

    def test_72_orchestrator_offline_awaiting_bench_receipts_and_verified(self) -> None:
        rep = evaluate_realhw_bright_mon_shotmark_big6_home_and_ssh_auth_preflight(
            synthetic_clean_room=True
        )
        self.assertIsInstance(rep, RealHwBrightMonShotMarkBig6HomeAndSshAuthReport)
        self.assertEqual(rep.overall_status, P316_OVERALL_READY_OFFLINE_AWAITING_BENCH_RECEIPTS)
        self.assertEqual(rep.go_no_go, GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT)
        self.assertTrue(rep.all_4_check_groups_passed)
        self.assertEqual(rep.check_groups_passed, 4)
        self.assertFalse(rep.tier0_receipt_verified)
        self.assertEqual(rep.h0_h3_surface_count, 16)
        self.assertEqual(rep.h0_equals_h3_count, 16)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        self.assertFalse(rep.cross_model_flash_authorized)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)
        vr = verify_phase316_report(rep.to_dict())
        self.assertTrue(vr.valid, vr.errors)

    def test_73_orchestrator_simulate_bench_dry_run_and_alias(self) -> None:
        for flag_kwargs in (
            {"simulate_bench_dry_run": True},
            {"simulate_ready_bench": True},
        ):
            rep = evaluate_realhw_bright_mon_shotmark_big6_home_and_ssh_auth_preflight(
                synthetic_clean_room=True,
                **flag_kwargs,
            )
            self.assertEqual(rep.overall_status, GO_NO_GO_DRY_RUN_SIMULATED_READY)
            self.assertEqual(rep.go_no_go, GO_NO_GO_DRY_RUN_SIMULATED_READY)
            self.assertTrue(rep.simulate_bench_dry_run)
            self.assertTrue(rep.tier0_receipt_verified)
            self.assertTrue(
                rep.check_group_d_tc_regen_hdmi_rec_ssh_auth_zero_fan_tier0.distinct_physical_media_verified
            )
            self.assertFalse(rep.overall_ready_for_hardware_attach)
            vr = verify_phase316_report(rep.to_dict())
            self.assertTrue(vr.valid, vr.errors)

    def test_74_orchestrator_valid_dual_device_528b_fx3rcpt1_receipts(self) -> None:
        rcpt_a, rcpt_b, h0 = build_simulated_phase316_tier0_receipts()
        self.assertEqual(len(rcpt_a), 528)
        rep = evaluate_realhw_bright_mon_shotmark_big6_home_and_ssh_auth_preflight(
            synthetic_clean_room=True,
            receipt_a_bytes=rcpt_a,
            receipt_b_bytes=rcpt_b,
            st_dev_a_override=1001,
            st_dev_b_override=2002,
            body_serial=DEFAULT_TARGET_BODY_SERIAL,
            emmc_cid=DEFAULT_TARGET_EMMC_CID,
            h0_baselines_a=h0,
            h0_baselines_b=h0,
        )
        self.assertEqual(rep.go_no_go, P316_GO_NO_GO_BRIGHT_MON_SHOTMARK_BIG6_SSH_AUTH_VERIFIED)
        self.assertEqual(
            rep.overall_status, P316_GO_NO_GO_BRIGHT_MON_SHOTMARK_BIG6_SSH_AUTH_VERIFIED
        )
        self.assertTrue(rep.tier0_receipt_verified)
        self.assertFalse(rep.overall_ready_for_hardware_attach)
        vr = verify_phase316_report(rep.to_dict())
        self.assertTrue(vr.valid, vr.errors)

    def test_75_gd_rejects_same_st_dev_corrupt_len_or_missing_copy_b(self) -> None:
        rcpt_a, rcpt_b, h0 = build_simulated_phase316_tier0_receipts()
        gd_same_dev, errs_dev = evaluate_p316_check_group_d_tc_regen_hdmi_rec_ssh_auth_zero_fan_tier0(
            receipt_a_bytes=rcpt_a,
            receipt_b_bytes=rcpt_b,
            st_dev_a_override=777,
            st_dev_b_override=777,
            body_serial=DEFAULT_TARGET_BODY_SERIAL,
            emmc_cid=DEFAULT_TARGET_EMMC_CID,
            h0_baselines_a=h0,
            h0_baselines_b=h0,
        )
        self.assertFalse(gd_same_dev.tier0_receipt_verified)
        self.assertFalse(gd_same_dev.distinct_physical_media_verified)
        self.assertTrue(any("st_dev_a == st_dev_b" in e for e in errs_dev))

        gd_one, errs_one = evaluate_p316_check_group_d_tc_regen_hdmi_rec_ssh_auth_zero_fan_tier0(
            receipt_a_bytes=rcpt_a
        )
        self.assertFalse(gd_one.tier0_receipt_verified)
        self.assertTrue(any("Copy A and Copy B" in e for e in errs_one))

        gd_corrupt, errs_bad = evaluate_p316_check_group_d_tc_regen_hdmi_rec_ssh_auth_zero_fan_tier0(
            receipt_a_bytes=b"BAD" * 10,
            receipt_b_bytes=b"BAD" * 10,
        )
        self.assertFalse(gd_corrupt.tier0_receipt_verified)
        self.assertTrue(any("size/byte mismatch" in e for e in errs_bad))

    def test_76_gd_rejects_trivial_serial_cid_or_mismatched_h0_baselines(self) -> None:
        rcpt_a, rcpt_b, h0 = build_simulated_phase316_tier0_receipts()
        bad_h0 = dict(h0)
        first_key = next(iter(bad_h0))
        bad_h0[first_key] = "0" * 64
        gd, errs = evaluate_p316_check_group_d_tc_regen_hdmi_rec_ssh_auth_zero_fan_tier0(
            receipt_a_bytes=rcpt_a,
            receipt_b_bytes=rcpt_b,
            st_dev_a_override=1,
            st_dev_b_override=2,
            body_serial="0000000",
            emmc_cid="0" * 32,
            h0_baselines_a=h0,
            h0_baselines_b=bad_h0,
        )
        self.assertFalse(gd.tier0_receipt_verified)
        self.assertTrue(any("invalid body_serial" in e for e in errs))
        self.assertTrue(any("invalid emmc_cid" in e for e in errs))
        self.assertTrue(any(P316_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID in e for e in errs))

    def test_77_verify_phase316_report_catches_tampered_locks_counters_and_sha(self) -> None:
        rep = evaluate_realhw_bright_mon_shotmark_big6_home_and_ssh_auth_preflight(
            synthetic_clean_room=True, simulate_bench_dry_run=True
        )
        base = rep.to_dict()
        self.assertTrue(verify_phase316_report(base).valid)

        for field, bad_val in (
            ("overall_ready_for_hardware_attach", True),
            ("cross_model_flash_authorized", True),
            ("fx3_bt_tc_link_present", True),
            ("fx3_auto_framing_present", True),
            ("fx3_physical_e_nd_present", True),
            ("fx3_fan_control_max_present", True),
            ("fx6_fan_control_max_present", True),
            ("e_nd_actuator_tx_count", 1),
            ("wireless_rf_packets_emitted", 1),
            ("slot1_data_sector_writes", 1),
            ("raw_firmware_bytes_leaked", 1),
            ("go_no_go", P316_GO_NO_GO_BRIGHT_MON_SHOTMARK_BIG6_SSH_AUTH_VERIFIED),
            ("report_sha256", "a" * 64),
        ):
            tampered = copy.deepcopy(base)
            tampered[field] = bad_val
            vr = verify_phase316_report(tampered)
            self.assertFalse(vr.valid, f"Expected tamper rejection for {field}={bad_val!r}")

    def test_78_canonical_sha256_ignores_donor_elapsed_seconds(self) -> None:
        rep = evaluate_realhw_bright_mon_shotmark_big6_home_and_ssh_auth_preflight(
            synthetic_clean_room=True, simulate_bench_dry_run=True
        )
        d1 = rep.to_dict()
        d2 = copy.deepcopy(d1)
        d2["donor_inspection"]["elapsed_seconds"] = 999.123
        self.assertEqual(_canonical_sha256_dict(d1), _canonical_sha256_dict(d2))

    def test_79_render_markdown_deterministic_and_contains_sections(self) -> None:
        rep = evaluate_realhw_bright_mon_shotmark_big6_home_and_ssh_auth_preflight(
            synthetic_clean_room=True, simulate_bench_dry_run=True
        )
        md1 = render_phase316_markdown(rep)
        md2 = render_phase316_markdown(rep)
        self.assertEqual(md1, md2)
        self.assertIn(PHASE_316_SCHEMA, md1)
        self.assertIn(P316_CHECK_GROUP_A_ID, md1)
        self.assertIn(P316_CHECK_GROUP_B_ID, md1)
        self.assertIn(P316_CHECK_GROUP_C_ID, md1)
        self.assertIn(P316_CHECK_GROUP_D_ID, md1)
        self.assertIn("16/16", md1)

    def test_80_group_failure_sets_blocked_verdict_and_remediations(self) -> None:
        rep = evaluate_realhw_bright_mon_shotmark_big6_home_and_ssh_auth_preflight(
            synthetic_clean_room=True,
            simulate_bench_dry_run=True,
            dormant_auto_framing_requested=True,
            fx3_fan_control="MAX",
        )
        self.assertEqual(
            rep.go_no_go, P316_GO_NO_GO_BLOCKED_BRIGHT_MON_SHOTMARK_BIG6_SSH_AUTH_FAILURE
        )
        self.assertFalse(rep.all_4_check_groups_passed)
        self.assertEqual(rep.check_groups_passed, 2)
        self.assertGreaterEqual(len(rep.remediation_actions), 2)
        self.assertTrue(verify_phase316_report(rep.to_dict()).valid)

    def test_81_determinism_same_inputs_identical_sha256(self) -> None:
        r1 = evaluate_realhw_bright_mon_shotmark_big6_home_and_ssh_auth_preflight(
            synthetic_clean_room=True,
            simulate_bench_dry_run=True,
            big6_home_screen_active=True,
            home_trigger_method="CUSTOM_KEY_HOME",
            home_lower_left_mode="ND_FILTER",
        )
        r2 = evaluate_realhw_bright_mon_shotmark_big6_home_and_ssh_auth_preflight(
            synthetic_clean_room=True,
            simulate_bench_dry_run=True,
            big6_home_screen_active=True,
            home_trigger_method="CUSTOM_KEY_HOME",
            home_lower_left_mode="ND_FILTER",
        )
        self.assertEqual(r1.report_sha256, r2.report_sha256)

    def test_82_gd_invalid_tc_hdmi_auth_fan_enums_fail_closed(self) -> None:
        gd, _ = evaluate_p316_check_group_d_tc_regen_hdmi_rec_ssh_auth_zero_fan_tier0(
            tc_make="NTP",
            tc_run="JAM",
            hdmi_tc_output="MAYBE",
            hdmi_rec_control="AUTO",
            rec_media_dur_hdmi_output="SDI_ONLY",
            hdmi_4ch_audio_output="CH5_CH6",
            access_authen="AUTO",
            access_authen_protocol="TELNET",
            fx3_fan_control="TURBO",
            fx6_fan_control="TURBO",
            auto_power_off_temp="EXTREME",
        )
        self.assertFalse(gd.passed)
        self.assertGreaterEqual(len(gd.errors), 11)

    # ------------------------------------------------------------------
    # 83-90: Direct CLI & Isolated Subprocess Dual-Mode Verification
    # ------------------------------------------------------------------

    def test_83_cli_help_succeeds_zero_errors(self) -> None:
        proc = _run_cli_subprocess(["--help"])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("preflight-bright-monitoring-shot-mark-big6-home-and-ssh-auth", proc.stdout)

    def test_84_cli_clean_room_offline_awaiting_receipt_exits_2(self) -> None:
        stdout = io.StringIO()
        with mock.patch("sys.stdout", stdout):
            rc = fx6_cli_main(
                [
                    "preflight-bright-monitoring-shot-mark-big6-home-and-ssh-auth",
                    "--force-clean-room",
                    "--json",
                ]
            )
        self.assertEqual(rc, 2)
        data = json.loads(stdout.getvalue())
        self.assertEqual(data["verification_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(data["go_no_go"], GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT)
        self.assertEqual(data["overall_status"], P316_OVERALL_READY_OFFLINE_AWAITING_BENCH_RECEIPTS)
        self.assertTrue(verify_phase316_report(data).valid)

    def test_85_cli_clean_room_simulate_bench_dry_run_json_exits_0(self) -> None:
        stdout = io.StringIO()
        with mock.patch("sys.stdout", stdout):
            rc = fx6_cli_main(
                [
                    "preflight-bright-monitoring-shot-mark-big6-home-and-ssh-auth",
                    "--force-clean-room",
                    "--simulate-bench-dry-run",
                    "--json",
                ]
            )
        self.assertEqual(rc, 0)
        data = json.loads(stdout.getvalue())
        self.assertEqual(data["schema_version"], PHASE_316_SCHEMA)
        self.assertEqual(data["go_no_go"], GO_NO_GO_DRY_RUN_SIMULATED_READY)
        self.assertEqual(data["check_groups_passed"], 4)
        self.assertEqual(data["h0_equals_h3_count"], 16)
        self.assertTrue(verify_phase316_report(data).valid)

    def test_86_cli_summary_writes_json_and_markdown_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            json_out = td_path / "p316.json"
            md_out = td_path / "p316.md"
            stdout = io.StringIO()
            with mock.patch("sys.stdout", stdout):
                rc = fx6_cli_main(
                    [
                        "preflight-bright-monitoring-shot-mark-big6-home-and-ssh-auth",
                        "--force-clean-room",
                        "--simulate-bench-dry-run",
                        "--summary",
                        "--output",
                        str(json_out),
                        "--markdown-out",
                        str(md_out),
                    ]
                )
            self.assertEqual(rc, 0)
            self.assertIn("OVERALL=DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH", stdout.getvalue())
            self.assertTrue(json_out.is_file())
            self.assertTrue(md_out.is_file())
            parsed = json.loads(json_out.read_text(encoding="utf-8"))
            self.assertTrue(verify_phase316_report(parsed).valid)
            self.assertIn(PHASE_316_SCHEMA, md_out.read_text(encoding="utf-8"))

    def test_87_cli_negative_dormant_and_slot1_flags_exit_2(self) -> None:
        for extra_flags in (
            ["--dormant-bt-tc-link-requested"],
            ["--dormant-auto-framing-requested"],
            ["--fx3-physical-e-nd-claimed"],
            ["--dormant-fan-control-max-requested"],
            ["--dormant-http-https-camera-auth-claimed"],
            ["--shot-mark-write-requested", "--shot-mark-slot", "1"],
            ["--interval-shooting-active", "--shoot-mode", "PHOTO", "--interval-target-slot", "1"],
            ["--airplane-mode", "OFF"],
        ):
            stdout = io.StringIO()
            with mock.patch("sys.stdout", stdout):
                rc = fx6_cli_main(
                    [
                        "preflight-bright-monitoring-shot-mark-big6-home-and-ssh-auth",
                        "--force-clean-room",
                        "--simulate-bench-dry-run",
                        "--json",
                        *extra_flags,
                    ]
                )
            self.assertEqual(rc, 2, f"Expected exit 2 for {extra_flags}")
            data = json.loads(stdout.getvalue())
            self.assertEqual(
                data["go_no_go"],
                P316_GO_NO_GO_BLOCKED_BRIGHT_MON_SHOTMARK_BIG6_SSH_AUTH_FAILURE,
            )
            self.assertTrue(verify_phase316_report(data).valid)

    def test_88_cli_subprocess_forced_clean_room_mode(self) -> None:
        proc = _run_cli_subprocess(
            ["--simulate-bench-dry-run", "--json"],
            extra_env={"FX3_FX6_FORCE_CLEAN_ROOM": "1"},
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        data = json.loads(proc.stdout)
        self.assertEqual(data["verification_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(data["go_no_go"], GO_NO_GO_DRY_RUN_SIMULATED_READY)
        self.assertTrue(verify_phase316_report(data).valid)

    def test_89_cli_subprocess_current_env_mode_with_receipt_files_same_dev_fails_closed(self) -> None:
        rcpt_a, rcpt_b, _ = build_simulated_phase316_tier0_receipts()
        with tempfile.TemporaryDirectory() as td:
            p_a = Path(td) / "FX3RCPT1_a.bin"
            p_b = Path(td) / "FX3RCPT1_b.bin"
            p_a.write_bytes(rcpt_a)
            p_b.write_bytes(rcpt_b)
            proc = _run_cli_subprocess(
                [
                    "--receipt-a",
                    str(p_a),
                    "--receipt-b",
                    str(p_b),
                    "--body-serial",
                    DEFAULT_TARGET_BODY_SERIAL,
                    "--emmc-cid",
                    DEFAULT_TARGET_EMMC_CID,
                    "--json",
                ]
            )
            self.assertEqual(proc.returncode, 2)
            data = json.loads(proc.stdout)
            self.assertEqual(
                data["go_no_go"],
                P316_GO_NO_GO_BLOCKED_BRIGHT_MON_SHOTMARK_BIG6_SSH_AUTH_FAILURE,
            )
            self.assertTrue(any("st_dev_a == st_dev_b" in e for e in data["errors"]))

    def test_90_end_to_end_runtime_budget(self) -> None:
        t0 = time.perf_counter()
        rep = evaluate_realhw_bright_mon_shotmark_big6_home_and_ssh_auth_preflight(
            simulate_bench_dry_run=True
        )
        dt = time.perf_counter() - t0
        self.assertLessEqual(dt, _timing_budget(1.5))
        self.assertEqual(rep.go_no_go, GO_NO_GO_DRY_RUN_SIMULATED_READY)
        self.assertEqual(rep.check_groups_passed, 4)
        self.assertTrue(verify_phase316_report(rep.to_dict()).valid)


if __name__ == "__main__":
    unittest.main()
