#!/usr/bin/env python3
"""Unit tests for Phase 315 (Stage 65 — 65/65 Milestone):
Real-Hardware `ILME-FX3 Ver. 7.02` vs `ILME-FX6 Ver. 6.01` Wave-55:
4-Item `[Touch Operation]` & Dormant `Touch Shutter` / `Touch AE` / `Touch Panel/Pad` /
`Footer Icon Touch` Guard,
4-Mode `[DISP (Screen Disp) Set]` & Zero-EVF `Select Finder/Monitor` Blackout-Trap Guard
vs `FX6` Detachable `Viewfinder`,
Still-Only `[AEL w/ Shutter]` / `[Exp.comp.set]` / `[Wireless Flash]` / `[External Flash Set.]`,
and 9-Speed `[Play Speed for Interval]` (`1..9` default `5`) + Dormant `[Beauty Effect]` /
`[Trimming]` & `[Photo Capture]` `Slot-1` Tier-0 Vault Firewall HIL Co-Emulator
(88 dual-mode tests).
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import contextlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time
import unittest
import unittest.mock

FX3_VM_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = FX3_VM_DIR.parents[1]
if str(FX3_VM_DIR) not in sys.path:
    sys.path.insert(0, str(FX3_VM_DIR))

import fx3_vm_coemulation_suite as suite  # noqa: E402
import realhw_touch_shooting_disp_zero_evf_interval_pb_coemulator as p315  # noqa: E402

IS_CI = os.environ.get("GITHUB_ACTIONS", "").lower() == "true"


def _fast_suite_kwargs(**overrides: object) -> dict:
    """Fast config skipping unrelated optional stages 4..64 for quick Stage 65 isolation tests."""
    base = dict(
        force_clean_room=True,
        include_phase41_dtb_mhlx=False,
        include_phase45_imx510_xavc=False,
        include_phase53_hil_fault_harness=False,
        include_phase58_qmp_introspection=False,
        include_phase63_hdmi_raw_uvc=False,
        include_phase67_tc_lens_paint=False,
        include_phase71_dualslot_ups_salvage=False,
        include_phase78_touchaf_ciz_assignable=False,
        include_phase82_camset_lpcm_tcub=False,
        include_phase87_playback_shotmark_dewpoint=False,
        include_phase91_gyroflow_rtmd_anamorphic=False,
        include_phase96_interval_cache_ftp_fan=False,
        include_phase99_lut3d_subzero_sdi=False,
        include_phase103_emi_exfat_endurance=False,
        include_phase107_c2pa_shading_mcfleet_ovp=False,
        include_phase112_hdr_hlg_fiz_gimbal=False,
        include_phase117_proresraw_breathing_mishoe_hil=False,
        include_phase121_uvc_srt_crsdk_usbpd_hil=False,
        include_phase127_mxf_ptpv2_tally_monsoon_hil=False,
        include_phase132_vp_ledwall_freed_artnet_hil=False,
        include_phase141_realhw_preflash_dualboot_hil=False,
        include_phase145_realhw_mpr_dmm_rec=False,
        include_phase150_realhw_body_peripheral_hil=False,
        include_phase157_realhw_imx510_network_usb_hil=False,
        include_phase162_realhw_cfexpress_ufu_5tier_hil=False,
        include_phase167_realhw_cxd90058_sabin_seal_hil=False,
        include_phase172_realhw_c2pa_tc_gyro_prebench_hil=False,
        include_phase178_realhw_ssboot_wbi2_powerloss_slot1_ufu_hil=False,
        include_phase182_realhw_emount_info3d_breathing_hdmi_4264_raw_hil=False,
        include_phase188_realhw_fx3a_firewall_and_xlrh1_4ch_mishoe_hil=False,
        include_phase194_realhw_nouvc_dcc1_lut_path_cineei_hil=False,
        include_phase200_realhw_fan_pwm_shutter_angle_lut_split_hil=False,
        include_phase202_realhw_big6_noend_camset_slot1_vmcbncm1_hil=False,
        include_phase207_realhw_desqueeze_165x_focusmap_simult_shocklesswb_hil=False,
        include_phase213_realhw_hdmi_log1080_proxy_vault_focusmag_brightmon_hil=False,
        include_phase217_realhw_filesettings_shotmark_tcregen_reclamp_hil=False,
        include_phase222_realhw_pixelmap_ntscpal_gammaassist_displaylut_hil=False,
        include_phase226_realhw_steadyshot_active_ciz_4locks_powersave_autotemp_hil=False,
        include_phase232_realhw_sq_fixedvar_zebra_peaking_fullformat_hil=False,
        include_phase236_realhw_silent_autopixelmap_marker_flexexp_hil=False,
        include_stage44=False,
        include_stage45=False,
        include_stage46=False,
        include_stage47=False,
        include_stage48=False,
        include_stage49=False,
        include_stage50=False,
        include_stage51=False,
        include_stage52=False,
        include_stage53=False,
        include_stage54=False,
        include_stage55=False,
        include_stage56=False,
        include_stage57=False,
        include_stage58=False,
        include_stage59=False,
        include_stage60=False,
        include_stage61=False,
        include_stage62=False,
        include_stage63=False,
        include_stage64=False,
    )
    base.update(overrides)
    return base


_FAST_CLI_FLAGS = [
    "--clean-room",
    "--skip-phase41",
    "--skip-phase45",
    "--skip-phase53",
    "--skip-phase58",
    "--skip-phase63",
    "--skip-phase67",
    "--skip-phase71",
    "--skip-phase78",
    "--skip-phase82",
    "--skip-phase87",
    "--skip-phase91",
    "--skip-phase96",
    "--skip-phase99",
    "--skip-phase103",
    "--skip-phase107",
    "--skip-phase112",
    "--skip-phase117",
    "--skip-phase121",
    "--skip-phase127",
    "--skip-phase132",
    "--skip-phase141",
    "--skip-phase145",
    "--skip-phase150",
    "--skip-phase157",
    "--skip-phase162",
    "--skip-phase167",
    "--skip-phase172",
    "--skip-phase178",
    "--skip-phase182",
    "--skip-phase188",
    "--skip-phase194",
    "--skip-phase200",
    "--skip-phase202",
    "--skip-phase207",
    "--skip-phase213",
    "--skip-phase217",
    "--skip-phase222",
    "--skip-phase226",
    "--skip-phase232",
    "--skip-phase236",
    "--skip-stage44",
    "--skip-stage45",
    "--skip-stage46",
    "--skip-stage47",
    "--skip-stage48",
    "--skip-stage49",
    "--skip-stage50",
    "--skip-stage51",
    "--skip-stage52",
    "--skip-stage53",
    "--skip-stage54",
    "--skip-stage55",
    "--skip-stage56",
    "--skip-stage57",
    "--skip-stage58",
    "--skip-stage59",
    "--skip-stage60",
    "--skip-stage61",
    "--skip-stage62",
    "--skip-stage63",
    "--skip-stage64",
]


class TestPhase315DonorInspection(unittest.TestCase):
    """Dual-mode 17-donor O_RDONLY & CLEAN_ROOM_SYNTHETIC verification (tests 01..12)."""

    def test_01_schema_and_milestone_constants(self) -> None:
        self.assertEqual(
            p315.SCHEMA_ID,
            "realhw_touch_shooting_disp_zero_evf_interval_pb_coemulator_v1",
        )
        self.assertEqual(p315.PHASE_NUMBER, 315)
        self.assertEqual(p315.STAGE_INDEX, 65)
        self.assertEqual(p315.STAGE_TOTAL, 65)
        self.assertEqual(p315.MILESTONE_LABEL, "65/65")
        self.assertTrue(p315.IS_65TH_STAGE_MILESTONE)
        self.assertEqual(p315.DONOR_ACCESS_MODE, "O_RDONLY")
        self.assertEqual(p315.BOUNDED_WINDOW_MAX_BYTES, 4096)
        self.assertEqual(len(p315.DONOR_RELPATHS), 17)

    def test_02_donor_audit_current_mode_17_donors(self) -> None:
        audit = p315.inspect_phase315_donors()
        self.assertTrue(audit.all_contracts_verified)
        self.assertEqual(audit.donor_files_inspected, 17)
        self.assertEqual(audit.access_mode, "O_RDONLY")
        self.assertIn(
            audit.source_mode,
            (p315.SOURCE_MODE_LOCAL_DONOR, p315.SOURCE_MODE_CLEAN_ROOM),
        )
        self.assertEqual(len(audit.entries), 17)
        self.assertTrue(all(e.passed for e in audit.entries))
        max_ms = 17000.0 if IS_CI else 2000.0
        self.assertLess(audit.inspection_elapsed_ms, max_ms)

    def test_03_force_clean_room_both_env_vars(self) -> None:
        for env_key in (p315.ENV_CLEAN_ROOM_TEST, p315.ENV_FORCE_CLEAN_ROOM):
            audit = p315.inspect_phase315_donors(env={env_key: "1"})
            self.assertEqual(audit.source_mode, p315.SOURCE_MODE_CLEAN_ROOM)
            self.assertEqual(audit.donor_files_inspected, 17)
            self.assertTrue(audit.all_contracts_verified)
            self.assertFalse(any(e.read_only_checked for e in audit.entries))

    def test_04_missing_donor_dir_falls_back_clean_room(self) -> None:
        audit = p315.inspect_phase315_donors(
            env={p315.ENV_MAC_WORK_ROOT: "/nonexistent/fx3/__phase315_missing__"}
        )
        self.assertEqual(audit.source_mode, p315.SOURCE_MODE_CLEAN_ROOM)
        self.assertEqual(audit.donor_files_inspected, 17)
        self.assertTrue(audit.all_contracts_verified)

    def test_05_compact_donor_byte_lengths_sha256_and_tokens(self) -> None:
        audit = p315.inspect_phase315_donors()
        by_key = {e.donor_key: e for e in audit.entries}
        self.assertEqual(len(p315.EXPECTED_COMPACT_DONOR_SHA256), 14)
        for key, expected_sha in p315.EXPECTED_COMPACT_DONOR_SHA256.items():
            entry = by_key[key]
            self.assertEqual(entry.byte_length, p315.EXPECTED_DONOR_BYTES[key], key)
            self.assertEqual(entry.sha256_or_head4k, expected_sha, key)
            self.assertGreaterEqual(len(entry.tokens_verified), 4, key)
            self.assertTrue(entry.passed, key)

    def test_06_large_donor_bounded_windows_verified(self) -> None:
        audit = p315.inspect_phase315_donors()
        by_key = {e.donor_key: e for e in audit.entries}
        for key in ("fx3_appfw", "fx3_bk4", "fx6_appfw"):
            entry = by_key[key]
            self.assertEqual(entry.byte_length, p315.EXPECTED_DONOR_BYTES[key], key)
            self.assertEqual(
                entry.sha256_or_head4k,
                p315.EXPECTED_LARGE_HEAD4K_SHA256[key],
                key,
            )
            self.assertTrue(entry.passed, key)

    def test_07_bounded_read_rejects_oversized_window(self) -> None:
        with tempfile.NamedTemporaryFile() as tmp:
            tmp.write(b"ABCDEFGH")
            tmp.flush()
            self.assertEqual(p315._read_bounded_window_ro(Path(tmp.name), 0, 4), b"ABCD")
            with self.assertRaises(ValueError):
                p315._read_bounded_window_ro(Path(tmp.name), 0, 4097)

    def test_08_compact_reader_rejects_oversized_file(self) -> None:
        with tempfile.NamedTemporaryFile() as tmp:
            tmp.truncate(2 * 1024 * 1024 + 1)
            with self.assertRaises(ValueError):
                p315._read_compact_donor_ro(Path(tmp.name), 123)

    def test_09_donor_audit_cache_consistency_and_speed(self) -> None:
        a1 = p315.inspect_phase315_donors()
        a2 = p315.inspect_phase315_donors()
        self.assertEqual(a1.source_mode, a2.source_mode)
        self.assertEqual(a1.donor_files_inspected, a2.donor_files_inspected)
        self.assertEqual(a1.entries, a2.entries)

    def test_10_donor_audit_is_pure_o_rdonly_and_zero_writes(self) -> None:
        self.assertEqual(p315.DONOR_ACCESS_MODE, "O_RDONLY")
        self.assertEqual(p315.PHYSICAL_DEVICE_WRITES, 0)
        self.assertEqual(p315.RAW_FIRMWARE_BYTES_LEAKED, 0)

    def test_11_g_uxc_and_fx6_donors_covered_with_localized_tokens(self) -> None:
        self.assertIn("fx3_string_en_g", p315.COMPACT_DONOR_TOKENS)
        self.assertIn("fx3_string_sc_g", p315.COMPACT_DONOR_TOKENS)
        self.assertIn("fx3_string_tc_g", p315.COMPACT_DONOR_TOKENS)
        self.assertIn("fx3_string_ja_g", p315.COMPACT_DONOR_TOKENS)
        self.assertIn("fx6_string_en", p315.COMPACT_DONOR_TOKENS)
        self.assertIn("fx6_string_en_2", p315.COMPACT_DONOR_TOKENS)

    def test_12_clean_room_audit_deterministic_across_repeated_calls(self) -> None:
        a1 = p315.inspect_phase315_donors(force_clean_room=True)
        a2 = p315.inspect_phase315_donors(force_clean_room=True)
        self.assertEqual(a1, a2)


class TestSubModel65ATouchOperationAndDormantGuard(unittest.TestCase):
    """65A: 4-Item [Touch Operation] vs Dormant Alpha Touch Symbols & FX6 (tests 13..28)."""

    def test_13_fx3_setup_exposes_exact_4_items(self) -> None:
        r = p315.simulate_touch_operation_and_dormant_guard_hil()
        self.assertTrue(r.admitted)
        self.assertEqual(r.errno_code, 0)
        self.assertEqual(r.exposed_item_count, 4)
        self.assertEqual(
            r.exposed_setup_items,
            ("Touch Operation", "Touch Sensitivity", "Touch Func. in Shooting", "Swipe Up"),
        )

    def test_14_fx3_defaults_match_wave55_truth(self) -> None:
        r = p315.simulate_touch_operation_and_dormant_guard_hil()
        self.assertEqual(r.effective_touch_operation, p315.TOUCH_OP_ON)
        self.assertEqual(r.effective_touch_sensitivity, p315.TOUCH_SENS_STANDARD)
        self.assertEqual(r.effective_touch_func_in_shooting, p315.TOUCH_SHOOT_TRACKING)
        self.assertEqual(r.effective_swipe_up, p315.SWIPE_UP_OPEN_FN_MENU)
        self.assertTrue(r.shooting_touch_active)
        self.assertTrue(r.playback_touch_active)
        self.assertTrue(r.swipe_up_active)

    def test_15_fx3_touch_sensitivity_standard_or_sensitive_and_rejects_responsive(self) -> None:
        for sens in (p315.TOUCH_SENS_STANDARD, p315.TOUCH_SENS_SENSITIVE):
            r = p315.simulate_touch_operation_and_dormant_guard_hil(touch_sensitivity=sens)
            self.assertTrue(r.admitted)
            self.assertEqual(r.effective_touch_sensitivity, sens)

        for bad in p315.INVALID_TOUCH_SENSITIVITY_SYNONYMS:
            r_bad = p315.simulate_touch_operation_and_dormant_guard_hil(touch_sensitivity=bad)
            self.assertFalse(r_bad.admitted, bad)
            self.assertEqual(r_bad.errno_code, p315.EINVAL_ERRNO, bad)

    def test_16_fx3_touch_func_in_shooting_consistent_across_still_movie_sq(self) -> None:
        for domain in p315.VALID_SHOOTING_DOMAINS:
            for func in p315.VALID_FX3_TOUCH_SHOOT_FUNCS:
                r = p315.simulate_touch_operation_and_dormant_guard_hil(
                    shooting_domain=domain,
                    touch_func_in_shooting=func,
                )
                self.assertTrue(r.admitted, (domain, func))
                self.assertEqual(r.effective_touch_func_in_shooting, func)

    def test_17_fx3_playback_only_disables_shooting_touch_and_swipe_up(self) -> None:
        r = p315.simulate_touch_operation_and_dormant_guard_hil(
            touch_operation=p315.TOUCH_OP_PLAYBACK_ONLY,
            swipe_up=p315.SWIPE_UP_OPEN_FN_MENU,
        )
        self.assertTrue(r.admitted)
        self.assertTrue(r.playback_touch_active)
        self.assertFalse(r.shooting_touch_active)
        self.assertFalse(r.swipe_up_active)
        self.assertFalse(r.screen_fn_icon_touch_supported)
        self.assertFalse(r.stby_rec_touch_supported)
        self.assertFalse(r.long_press_fn_menu_supported)

    def test_18_fx3_touch_operation_off_disables_all_touch_and_swipe_up(self) -> None:
        r = p315.simulate_touch_operation_and_dormant_guard_hil(
            touch_operation=p315.TOUCH_OP_OFF,
            swipe_up=p315.SWIPE_UP_OPEN_FN_MENU,
        )
        self.assertTrue(r.admitted)
        self.assertFalse(r.playback_touch_active)
        self.assertFalse(r.shooting_touch_active)
        self.assertFalse(r.swipe_up_active)

    def test_19_swipe_up_off_disables_swipe_while_keeping_shooting_touch(self) -> None:
        r = p315.simulate_touch_operation_and_dormant_guard_hil(
            touch_operation=p315.TOUCH_OP_ON,
            swipe_up=p315.SWIPE_UP_OFF,
        )
        self.assertTrue(r.admitted)
        self.assertTrue(r.shooting_touch_active)
        self.assertFalse(r.swipe_up_active)
        self.assertTrue(r.screen_fn_icon_touch_supported)
        self.assertTrue(r.stby_rec_touch_supported)
        self.assertTrue(r.long_press_fn_menu_supported)

    def test_20_all_4_touch_items_survive_camera_settings_reset(self) -> None:
        r = p315.simulate_touch_operation_and_dormant_guard_hil(
            touch_operation=p315.TOUCH_OP_PLAYBACK_ONLY,
            touch_sensitivity=p315.TOUCH_SENS_SENSITIVE,
            touch_func_in_shooting=p315.TOUCH_SHOOT_FOCUS,
            swipe_up=p315.SWIPE_UP_OFF,
            camera_settings_reset_applied=True,
        )
        self.assertTrue(r.admitted)
        self.assertTrue(r.all_4_survived_cam_reset)
        self.assertTrue(r.reset_via_initialize_only)
        self.assertEqual(r.effective_touch_operation, p315.TOUCH_OP_PLAYBACK_ONLY)
        self.assertEqual(r.effective_touch_sensitivity, p315.TOUCH_SENS_SENSITIVE)
        self.assertEqual(r.effective_touch_func_in_shooting, p315.TOUCH_SHOOT_FOCUS)
        self.assertEqual(r.effective_swipe_up, p315.SWIPE_UP_OFF)

    def test_21_initialize_resets_all_4_touch_items_to_defaults(self) -> None:
        r = p315.simulate_touch_operation_and_dormant_guard_hil(
            touch_operation=p315.TOUCH_OP_OFF,
            touch_sensitivity=p315.TOUCH_SENS_SENSITIVE,
            touch_func_in_shooting=p315.TOUCH_SHOOT_OFF,
            swipe_up=p315.SWIPE_UP_OFF,
            initialize_applied=True,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.effective_touch_operation, p315.TOUCH_OP_ON)
        self.assertEqual(r.effective_touch_sensitivity, p315.TOUCH_SENS_STANDARD)
        self.assertEqual(r.effective_touch_func_in_shooting, p315.TOUCH_SHOOT_TRACKING)
        self.assertEqual(r.effective_swipe_up, p315.SWIPE_UP_OPEN_FN_MENU)

    def test_22_dormant_touch_shutter_and_touch_ae_rejected_eopnotsupp(self) -> None:
        for sym in ("Touch Shutter", "Touch AE", "Touch Focus+AE", "Touch AE Cancel"):
            r = p315.simulate_touch_operation_and_dormant_guard_hil(
                requested_dormant_touch_symbol=sym
            )
            self.assertFalse(r.admitted, sym)
            self.assertEqual(r.errno_code, p315.EOPNOTSUPP_ERRNO, sym)
            self.assertTrue(r.dormant_touch_symbol_blocked, sym)

    def test_23_dormant_touch_panel_pad_zero_evf_rejected_eopnotsupp(self) -> None:
        for sym in (
            "Touch Panel/Pad",
            "Touch Pad Only",
            "Touch Panel+Pad",
            "Touch Pad Settings",
            "Touch Pad (vertical)",
        ):
            r = p315.simulate_touch_operation_and_dormant_guard_hil(
                requested_dormant_touch_symbol=sym
            )
            self.assertFalse(r.admitted, sym)
            self.assertEqual(r.errno_code, p315.EOPNOTSUPP_ERRNO, sym)
            self.assertTrue(r.dormant_touch_symbol_blocked, sym)

    def test_24_dormant_footer_icon_touch_and_swipe_lr_rejected_eopnotsupp(self) -> None:
        for sym in ("Footer Icon Touch", "Swipe Left", "Swipe Right"):
            r = p315.simulate_touch_operation_and_dormant_guard_hil(
                requested_dormant_touch_symbol=sym
            )
            self.assertFalse(r.admitted, sym)
            self.assertEqual(r.errno_code, p315.EOPNOTSUPP_ERRNO, sym)
            self.assertTrue(r.dormant_touch_symbol_blocked, sym)

    def test_25_fx6_technical_touch_operation_and_mf_spot_or_tracking(self) -> None:
        for mf_fn in p315.VALID_FX6_TOUCH_MF_FUNCS:
            r = p315.simulate_touch_operation_and_dormant_guard_hil(
                body_profile=p315.BODY_MODEL_FX6,
                focus_mode=p315.FOCUS_MODE_MF,
                touch_operation=p315.TOUCH_OP_ON,
                fx6_touch_func_in_mf=mf_fn,
            )
            self.assertTrue(r.admitted, mf_fn)
            self.assertEqual(r.exposed_item_count, 2)
            self.assertEqual(r.effective_touch_func_in_shooting, mf_fn)
            self.assertEqual(r.effective_touch_sensitivity, "N/A")
            self.assertEqual(r.effective_swipe_up, "N/A")

    def test_26_fx6_af_uses_realtime_tracking_when_touch_on(self) -> None:
        r = p315.simulate_touch_operation_and_dormant_guard_hil(
            body_profile=p315.BODY_MODEL_FX6,
            focus_mode=p315.FOCUS_MODE_AFC,
            touch_operation=p315.TOUCH_OP_ON,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.effective_touch_func_in_shooting, "Realtime Tracking AF")
        self.assertTrue(r.shooting_touch_active)

    def test_27_fx6_rejects_fx3_playback_only_sensitivity_and_swipe_up(self) -> None:
        for kw in (
            {"touch_operation": p315.TOUCH_OP_PLAYBACK_ONLY},
            {"touch_sensitivity": p315.TOUCH_SENS_SENSITIVE},
            {"swipe_up": p315.SWIPE_UP_OFF},
        ):
            r = p315.simulate_touch_operation_and_dormant_guard_hil(
                body_profile=p315.BODY_MODEL_FX6, **kw
            )
            self.assertFalse(r.admitted, str(kw))
            self.assertEqual(r.errno_code, p315.EOPNOTSUPP_ERRNO, str(kw))

    def test_28_invalid_65a_arguments_rejected_einval(self) -> None:
        self.assertEqual(
            p315.simulate_touch_operation_and_dormant_guard_hil(
                body_profile="ILME-FX9"
            ).errno_code,
            p315.EINVAL_ERRNO,
        )
        self.assertEqual(
            p315.simulate_touch_operation_and_dormant_guard_hil(
                shooting_domain="TimeLapse"
            ).errno_code,
            p315.EINVAL_ERRNO,
        )
        self.assertEqual(
            p315.simulate_touch_operation_and_dormant_guard_hil(
                touch_operation="Always"
            ).errno_code,
            p315.EINVAL_ERRNO,
        )
        self.assertEqual(
            p315.simulate_touch_operation_and_dormant_guard_hil(
                body_profile=p315.BODY_MODEL_FX6,
                fx6_touch_func_in_mf="Touch Shutter",
            ).errno_code,
            p315.EINVAL_ERRNO,
        )


class TestSubModel65BDispScreenSetAndZeroEvfGuard(unittest.TestCase):
    """65B: [DISP (Screen Disp) Set] & Zero-EVF Blackout-Trap Guard vs FX6 Viewfinder (tests 29..43)."""

    def test_29_fx3_lives_under_operation_customize_4_shoot_3_play_pages(self) -> None:
        r = p315.simulate_disp_screen_set_and_zero_evf_guard_hil()
        self.assertTrue(r.admitted)
        self.assertEqual(r.errno_code, 0)
        self.assertIn("Operation Customize", r.parent_menu_path)
        self.assertEqual(r.exposed_shoot_page_count, 4)
        self.assertEqual(
            r.checked_shoot_pages,
            ("Display All Info.", "No Disp. Info.", "Histogram", "Level"),
        )
        self.assertEqual(r.exposed_play_page_count, 3)
        self.assertEqual(
            r.playback_cycle_pages,
            ("Display Info.", "Histogram", "No Disp. Info."),
        )

    def test_30_wrong_display_option_parent_rejected_eopnotsupp(self) -> None:
        r = p315.simulate_disp_screen_set_and_zero_evf_guard_hil(
            parent_menu=p315.DISP_PARENT_DISPLAY_OPTION_WRONG
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p315.EOPNOTSUPP_ERRNO)
        self.assertIn("OPERATION_CUSTOMIZE", r.reason_code)

    def test_31_shoot_pages_require_at_least_1_checked_einval(self) -> None:
        r_zero = p315.simulate_disp_screen_set_and_zero_evf_guard_hil(checked_shoot_pages=())
        self.assertFalse(r_zero.admitted)
        self.assertEqual(r_zero.errno_code, p315.EINVAL_ERRNO)

        r_one = p315.simulate_disp_screen_set_and_zero_evf_guard_hil(
            checked_shoot_pages=(p315.DISP_SHOOT_ALL_INFO,)
        )
        self.assertTrue(r_one.admitted)
        self.assertEqual(r_one.exposed_shoot_page_count, 1)

    def test_32_zero_evf_fx3_hardware_truth_locked(self) -> None:
        r = p315.simulate_disp_screen_set_and_zero_evf_guard_hil()
        self.assertFalse(r.fx3_has_builtin_evf)
        self.assertFalse(r.fx3_has_eye_sensor)
        self.assertFalse(r.fx3_has_finder_monitor_button)
        self.assertFalse(r.lcd_monitor_blacked_out)
        self.assertTrue(r.blackout_trap_prevented)

    def test_33_zero_evf_finder_monitor_blackout_traps_blocked_enodev(self) -> None:
        for sym in p315.DORMANT_ZERO_EVF_HARDWARE_TRAP_SYMBOLS:
            r = p315.simulate_disp_screen_set_and_zero_evf_guard_hil(
                request_finder_monitor_symbol=sym
            )
            self.assertFalse(r.admitted, sym)
            self.assertEqual(r.errno_code, p315.ENODEV_ERRNO, sym)
            self.assertTrue(r.blackout_trap_prevented, sym)
            self.assertFalse(r.lcd_monitor_blacked_out, sym)

    def test_34_dormant_for_viewfinder_graphic_display_monitor_off_rejected(self) -> None:
        for pg in p315.DORMANT_DISP_SCREEN_PAGES:
            r = p315.simulate_disp_screen_set_and_zero_evf_guard_hil(
                requested_dormant_disp_page=pg
            )
            self.assertFalse(r.admitted, pg)
            self.assertEqual(r.errno_code, p315.EOPNOTSUPP_ERRNO, pg)
            self.assertTrue(r.blackout_trap_prevented, pg)
            self.assertFalse(r.lcd_monitor_blacked_out, pg)

        r_chk = p315.simulate_disp_screen_set_and_zero_evf_guard_hil(
            checked_shoot_pages=(p315.DISP_SHOOT_ALL_INFO, "For viewfinder")
        )
        self.assertFalse(r_chk.admitted)
        self.assertEqual(r_chk.errno_code, p315.EOPNOTSUPP_ERRNO)

    def test_35_disp_shoot_subset_deduplicates_and_rejects_unknown(self) -> None:
        r_dup = p315.simulate_disp_screen_set_and_zero_evf_guard_hil(
            checked_shoot_pages=(p315.DISP_SHOOT_HISTOGRAM, p315.DISP_SHOOT_HISTOGRAM, p315.DISP_SHOOT_LEVEL)
        )
        self.assertTrue(r_dup.admitted)
        self.assertEqual(r_dup.checked_shoot_pages, (p315.DISP_SHOOT_HISTOGRAM, p315.DISP_SHOOT_LEVEL))

        r_unk = p315.simulate_disp_screen_set_and_zero_evf_guard_hil(
            checked_shoot_pages=("Custom Grid Bogus",)
        )
        self.assertFalse(r_unk.admitted)
        self.assertEqual(r_unk.errno_code, p315.EINVAL_ERRNO)

    def test_36_playback_3_disp_pages_cannot_be_altered_eopnotsupp(self) -> None:
        r = p315.simulate_disp_screen_set_and_zero_evf_guard_hil(
            requested_playback_pages=(p315.DISP_PLAY_INFO,)
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p315.EOPNOTSUPP_ERRNO)

    def test_37_disp_survives_camera_settings_reset_and_resets_via_initialize(self) -> None:
        r_csr = p315.simulate_disp_screen_set_and_zero_evf_guard_hil(
            checked_shoot_pages=(p315.DISP_SHOOT_NO_INFO, p315.DISP_SHOOT_LEVEL),
            camera_settings_reset_applied=True,
        )
        self.assertTrue(r_csr.admitted)
        self.assertTrue(r_csr.survived_cam_reset)
        self.assertEqual(r_csr.checked_shoot_pages, (p315.DISP_SHOOT_NO_INFO, p315.DISP_SHOOT_LEVEL))

        r_init = p315.simulate_disp_screen_set_and_zero_evf_guard_hil(
            checked_shoot_pages=(p315.DISP_SHOOT_NO_INFO,),
            initialize_applied=True,
        )
        self.assertTrue(r_init.admitted)
        self.assertEqual(r_init.checked_shoot_pages, p315.FX3_ACTIVE_4_DISP_SHOOT_PAGES)

    def test_38_fx3_disp_consistent_across_still_movie_sq(self) -> None:
        for dom in p315.VALID_SHOOTING_DOMAINS:
            r = p315.simulate_disp_screen_set_and_zero_evf_guard_hil(shooting_domain=dom)
            self.assertTrue(r.admitted, dom)
            self.assertEqual(r.exposed_shoot_page_count, 4, dom)

    def test_39_fx6_detachable_viewfinder_and_viewfinder_hood_supported(self) -> None:
        r = p315.simulate_disp_screen_set_and_zero_evf_guard_hil(
            body_profile=p315.BODY_MODEL_FX6,
            fx6_viewfinder_attached=True,
            fx6_viewfinder_hood_attached=True,
            fx6_terminology="Viewfinder",
            fx6_info_disp_mode=p315.FX6_INFO_DISP_HOME_PRIORITY,
            fx6_vf_mirror_flip=True,
        )
        self.assertTrue(r.admitted)
        self.assertFalse(r.fx6_has_builtin_evf)
        self.assertFalse(r.fx6_uses_loupe_terminology)
        self.assertTrue(r.fx6_detachable_viewfinder_attached)
        self.assertTrue(r.fx6_vf_mirror_flipped)

    def test_40_fx6_rejects_nonexistent_loupe_terminology_einval(self) -> None:
        for term in ("Loupe", "loupe", "LOUPE"):
            r = p315.simulate_disp_screen_set_and_zero_evf_guard_hil(
                body_profile=p315.BODY_MODEL_FX6,
                fx6_terminology=term,
            )
            self.assertFalse(r.admitted, term)
            self.assertEqual(r.errno_code, p315.EINVAL_ERRNO, term)
            self.assertFalse(r.fx6_uses_loupe_terminology)

    def test_41_fx6_info_disp_mode_operation_home_vs_direct_priority(self) -> None:
        for mode in p315.VALID_FX6_INFO_DISP_MODES:
            r = p315.simulate_disp_screen_set_and_zero_evf_guard_hil(
                body_profile=p315.BODY_MODEL_FX6,
                fx6_info_disp_mode=mode,
            )
            self.assertTrue(r.admitted, mode)
            self.assertEqual(r.fx6_info_disp_mode, mode)

        r_bad = p315.simulate_disp_screen_set_and_zero_evf_guard_hil(
            body_profile=p315.BODY_MODEL_FX6,
            fx6_info_disp_mode="All Off Priority",
        )
        self.assertFalse(r_bad.admitted)
        self.assertEqual(r_bad.errno_code, p315.EINVAL_ERRNO)

    def test_42_fx6_display_on_off_toggles_monitoring_output(self) -> None:
        r_on = p315.simulate_disp_screen_set_and_zero_evf_guard_hil(
            body_profile=p315.BODY_MODEL_FX6, fx6_display_on_off=True
        )
        r_off = p315.simulate_disp_screen_set_and_zero_evf_guard_hil(
            body_profile=p315.BODY_MODEL_FX6, fx6_display_on_off=False
        )
        self.assertEqual(r_on.checked_shoot_pages, ("Display On",))
        self.assertEqual(r_off.checked_shoot_pages, ("Display Off",))

    def test_43_invalid_65b_profile_and_domain_rejected_einval(self) -> None:
        self.assertEqual(
            p315.simulate_disp_screen_set_and_zero_evf_guard_hil(body_profile="A7S3").errno_code,
            p315.EINVAL_ERRNO,
        )
        self.assertEqual(
            p315.simulate_disp_screen_set_and_zero_evf_guard_hil(shooting_domain="PANO").errno_code,
            p315.EINVAL_ERRNO,
        )


class TestSubModel65CStillAelAndFlashSubmenuVsFx6(unittest.TestCase):
    """65C: Still-Only [AEL w/ Shutter], [Exp.comp.set], [Wireless Flash], [External Flash Set.] vs FX6 (tests 44..56)."""

    def test_44_all_4_items_rejected_in_movie_and_sq_with_ebusy(self) -> None:
        for dom in (p315.DOMAIN_MOVIE, p315.DOMAIN_SQ):
            r = p315.simulate_still_ael_w_shutter_and_flash_submenu_hil(shooting_domain=dom)
            self.assertFalse(r.admitted, dom)
            self.assertEqual(r.errno_code, p315.EBUSY_ERRNO, dom)

    def test_45_ael_w_shutter_auto_logic_for_afs_afa_afc(self) -> None:
        r_afs = p315.simulate_still_ael_w_shutter_and_flash_submenu_hil(
            focus_mode=p315.FOCUS_MODE_AFS, ael_w_shutter=p315.AEL_W_SHUTTER_AUTO
        )
        self.assertTrue(r_afs.ael_locked_on_half_shutter)
        self.assertFalse(r_afs.continuous_burst_remetering)

        r_afa_still = p315.simulate_still_ael_w_shutter_and_flash_submenu_hil(
            focus_mode=p315.FOCUS_MODE_AFA,
            subject_moving_in_afa=False,
            ael_w_shutter=p315.AEL_W_SHUTTER_AUTO,
        )
        self.assertTrue(r_afa_still.ael_locked_on_half_shutter)

        r_afa_mov = p315.simulate_still_ael_w_shutter_and_flash_submenu_hil(
            focus_mode=p315.FOCUS_MODE_AFA,
            subject_moving_in_afa=True,
            ael_w_shutter=p315.AEL_W_SHUTTER_AUTO,
        )
        self.assertFalse(r_afa_mov.ael_locked_on_half_shutter)
        self.assertTrue(r_afa_mov.continuous_burst_remetering)

        r_afc = p315.simulate_still_ael_w_shutter_and_flash_submenu_hil(
            focus_mode=p315.FOCUS_MODE_AFC, ael_w_shutter=p315.AEL_W_SHUTTER_AUTO
        )
        self.assertFalse(r_afc.ael_locked_on_half_shutter)
        self.assertTrue(r_afc.continuous_burst_remetering)

    def test_46_ael_w_shutter_on_and_off_explicit_modes(self) -> None:
        r_on = p315.simulate_still_ael_w_shutter_and_flash_submenu_hil(
            focus_mode=p315.FOCUS_MODE_AFC, ael_w_shutter=p315.AEL_W_SHUTTER_ON
        )
        self.assertTrue(r_on.ael_locked_on_half_shutter)
        self.assertFalse(r_on.continuous_burst_remetering)

        r_off = p315.simulate_still_ael_w_shutter_and_flash_submenu_hil(
            focus_mode=p315.FOCUS_MODE_AFS, ael_w_shutter=p315.AEL_W_SHUTTER_OFF
        )
        self.assertFalse(r_off.ael_locked_on_half_shutter)
        self.assertTrue(r_off.continuous_burst_remetering)

    def test_47_ael_toggle_overrides_half_shutter_setting(self) -> None:
        r = p315.simulate_still_ael_w_shutter_and_flash_submenu_hil(
            focus_mode=p315.FOCUS_MODE_AFC,
            ael_w_shutter=p315.AEL_W_SHUTTER_OFF,
            ael_toggle_active=True,
        )
        self.assertTrue(r.admitted)
        self.assertTrue(r.ael_locked_on_half_shutter)
        self.assertTrue(r.ael_toggle_overrode_half_shutter)
        self.assertFalse(r.continuous_burst_remetering)

    def test_48_exp_comp_set_ambient_and_flash_vs_ambient_only(self) -> None:
        r_both = p315.simulate_still_ael_w_shutter_and_flash_submenu_hil(
            exp_comp_set=p315.EXP_COMP_SET_AMBIENT_FLASH, exposure_comp_ev=-1.0
        )
        self.assertTrue(r_both.flash_output_shifted_with_ev_comp)

        r_amb = p315.simulate_still_ael_w_shutter_and_flash_submenu_hil(
            exp_comp_set=p315.EXP_COMP_SET_AMBIENT_ONLY, exposure_comp_ev=-1.0
        )
        self.assertFalse(r_amb.flash_output_shifted_with_ev_comp)

    def test_49_exp_comp_set_wrong_parent_menu_rejected_eopnotsupp(self) -> None:
        r = p315.simulate_still_ael_w_shutter_and_flash_submenu_hil(
            request_exp_comp_set_under_wrong_menu=True
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p315.EOPNOTSUPP_ERRNO)

    def test_50_wireless_flash_on_enables_test_flash(self) -> None:
        r_on = p315.simulate_still_ael_w_shutter_and_flash_submenu_hil(
            wireless_flash=p315.WIRELESS_FLASH_ON
        )
        self.assertTrue(r_on.admitted)
        self.assertTrue(r_on.wireless_test_flash_available)

        r_off = p315.simulate_still_ael_w_shutter_and_flash_submenu_hil(
            wireless_flash=p315.WIRELESS_FLASH_OFF
        )
        self.assertFalse(r_off.wireless_test_flash_available)

    def test_51_reset_split_only_wireless_flash_resets_on_camera_settings_reset(self) -> None:
        r = p315.simulate_still_ael_w_shutter_and_flash_submenu_hil(
            ael_w_shutter=p315.AEL_W_SHUTTER_ON,
            exp_comp_set=p315.EXP_COMP_SET_AMBIENT_ONLY,
            wireless_flash=p315.WIRELESS_FLASH_ON,
            camera_settings_reset_applied=True,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.effective_ael_w_shutter, p315.AEL_W_SHUTTER_ON)
        self.assertEqual(r.effective_exp_comp_set, p315.EXP_COMP_SET_AMBIENT_ONLY)
        self.assertEqual(r.effective_wireless_flash, p315.WIRELESS_FLASH_OFF)
        self.assertTrue(r.ael_survived_cam_reset)
        self.assertTrue(r.exp_comp_set_survived_cam_reset)
        self.assertTrue(r.wireless_flash_reset_by_cam_reset)
        self.assertTrue(r.ext_flash_survived_cam_reset)

    def test_52_initialize_resets_all_4_still_ael_and_flash_items(self) -> None:
        r = p315.simulate_still_ael_w_shutter_and_flash_submenu_hil(
            ael_w_shutter=p315.AEL_W_SHUTTER_OFF,
            exp_comp_set=p315.EXP_COMP_SET_AMBIENT_ONLY,
            wireless_flash=p315.WIRELESS_FLASH_ON,
            initialize_applied=True,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.effective_ael_w_shutter, p315.AEL_W_SHUTTER_AUTO)
        self.assertEqual(r.effective_exp_comp_set, p315.EXP_COMP_SET_AMBIENT_FLASH)
        self.assertEqual(r.effective_wireless_flash, p315.WIRELESS_FLASH_OFF)

    def test_53_external_flash_set_direct_mi_shoe_vs_sync_cord_einval(self) -> None:
        r_mi = p315.simulate_still_ael_w_shutter_and_flash_submenu_hil(
            flash_mount_type=p315.FLASH_MOUNT_MI_SHOE,
            access_external_flash_menu=True,
        )
        self.assertTrue(r_mi.admitted)
        self.assertTrue(r_mi.external_flash_menu_accessible)

        r_cord = p315.simulate_still_ael_w_shutter_and_flash_submenu_hil(
            flash_mount_type=p315.FLASH_MOUNT_SYNC_CORD,
            access_external_flash_menu=True,
        )
        self.assertFalse(r_cord.admitted)
        self.assertEqual(r_cord.errno_code, p315.EINVAL_ERRNO)

        r_none = p315.simulate_still_ael_w_shutter_and_flash_submenu_hil(
            flash_mount_type=p315.FLASH_MOUNT_NONE,
            access_external_flash_menu=True,
        )
        self.assertFalse(r_none.admitted)
        self.assertEqual(r_none.errno_code, p315.ENODEV_ERRNO)

    def test_54_external_flash_cannot_pair_or_reset_from_camera_menu_eopnotsupp(self) -> None:
        r = p315.simulate_still_ael_w_shutter_and_flash_submenu_hil(
            flash_mount_type=p315.FLASH_MOUNT_MI_SHOE,
            request_menu_flash_pair_or_reset=True,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p315.EOPNOTSUPP_ERRNO)

    def test_55_fx6_zero_flash_stack_enoent_and_flash_band_reduce_only(self) -> None:
        r_eno = p315.simulate_still_ael_w_shutter_and_flash_submenu_hil(
            body_profile=p315.BODY_MODEL_FX6,
            wireless_flash=p315.WIRELESS_FLASH_ON,
        )
        self.assertFalse(r_eno.admitted)
        self.assertEqual(r_eno.errno_code, p315.ENOENT_ERRNO)

        r_fbr = p315.simulate_still_ael_w_shutter_and_flash_submenu_hil(
            body_profile=p315.BODY_MODEL_FX6,
            fx6_request_flash_band_reduce=True,
        )
        self.assertTrue(r_fbr.admitted)
        self.assertTrue(r_fbr.fx6_flash_band_reduce_only)

    def test_56_invalid_65c_arguments_rejected_einval(self) -> None:
        self.assertEqual(
            p315.simulate_still_ael_w_shutter_and_flash_submenu_hil(
                ael_w_shutter="Slow"
            ).errno_code,
            p315.EINVAL_ERRNO,
        )
        self.assertEqual(
            p315.simulate_still_ael_w_shutter_and_flash_submenu_hil(
                exp_comp_set="Flash only"
            ).errno_code,
            p315.EINVAL_ERRNO,
        )


class TestSubModel65DIntervalPlaySpeedAndSlot1VaultFirewall(unittest.TestCase):
    """65D: 9-Speed [Play Speed for Interval] (1..9 default 5) & Dormant [Beauty Effect]/[Trimming] + Slot-1 Firewall (tests 57..70)."""

    def test_57_viewing_menu_not_playback_option_for_cont_play_interval(self) -> None:
        r_ok = p315.simulate_interval_playback_edit_and_vault_firewall_hil(
            viewing_parent_menu="Viewing"
        )
        self.assertTrue(r_ok.admitted)

        r_bad = p315.simulate_interval_playback_edit_and_vault_firewall_hil(
            viewing_parent_menu="Playback Option"
        )
        self.assertFalse(r_bad.admitted)
        self.assertEqual(r_bad.errno_code, p315.EOPNOTSUPP_ERRNO)

    def test_58_exact_9_interval_speeds_1_through_9_default_5(self) -> None:
        self.assertEqual(p315.INTERVAL_PLAY_SPEED_DEFAULT, 5)
        self.assertEqual(p315.VALID_INTERVAL_PLAY_SPEEDS, (1, 2, 3, 4, 5, 6, 7, 8, 9))
        for spd in p315.VALID_INTERVAL_PLAY_SPEEDS:
            r = p315.simulate_interval_playback_edit_and_vault_firewall_hil(
                operation=p315.PB_OP_VIEW_INTERVAL,
                select_playback_media=p315.SLOT_1,
                play_speed_for_interval=spd,
            )
            self.assertTrue(r.admitted, spd)
            self.assertEqual(r.effective_play_speed_for_interval, spd)
            self.assertEqual(r.slot1_data_sector_writes, 0)
            self.assertFalse(r.slot1_avf_info_mutated)

    def test_59_out_of_range_interval_speeds_0_and_10_rejected_einval(self) -> None:
        for bad_spd in (-1, 0, 10, 16, True):
            r = p315.simulate_interval_playback_edit_and_vault_firewall_hil(
                play_speed_for_interval=bad_spd  # type: ignore[arg-type]
            )
            self.assertFalse(r.admitted, str(bad_spd))
            self.assertEqual(r.errno_code, p315.EINVAL_ERRNO, str(bad_spd))

    def test_60_dial_step_delta_adjusts_and_clamps_within_1_to_9(self) -> None:
        r_up = p315.simulate_interval_playback_edit_and_vault_firewall_hil(
            play_speed_for_interval=8, dial_step_delta=3
        )
        self.assertTrue(r_up.admitted)
        self.assertEqual(r_up.effective_play_speed_for_interval, 9)
        self.assertTrue(r_up.dial_speed_adjusted)

        r_dn = p315.simulate_interval_playback_edit_and_vault_firewall_hil(
            play_speed_for_interval=2, dial_step_delta=-4
        )
        self.assertTrue(r_dn.admitted)
        self.assertEqual(r_dn.effective_play_speed_for_interval, 1)
        self.assertTrue(r_dn.dial_speed_adjusted)

    def test_61_interval_speed_survives_cam_reset_and_resets_only_via_initialize(self) -> None:
        r_csr = p315.simulate_interval_playback_edit_and_vault_firewall_hil(
            play_speed_for_interval=9,
            photo_capture_file_type=p315.PB_JPEG_HEIF_422,
            camera_settings_reset_applied=True,
        )
        self.assertTrue(r_csr.admitted)
        self.assertEqual(r_csr.effective_play_speed_for_interval, 9)
        self.assertEqual(r_csr.effective_photo_capture_file_type, p315.PB_JPEG_HEIF_422)
        self.assertTrue(r_csr.interval_survived_cam_reset)

        r_init = p315.simulate_interval_playback_edit_and_vault_firewall_hil(
            play_speed_for_interval=9,
            photo_capture_file_type=p315.PB_JPEG_HEIF_422,
            initialize_applied=True,
        )
        self.assertTrue(r_init.admitted)
        self.assertEqual(r_init.effective_play_speed_for_interval, 5)
        self.assertEqual(r_init.effective_photo_capture_file_type, p315.PB_JPEG_HEIF_JPEG)

    def test_62_no_in_camera_interval_to_movie_synthesis_eopnotsupp(self) -> None:
        r = p315.simulate_interval_playback_edit_and_vault_firewall_hil(
            operation=p315.PB_OP_SYNTHESIZE_INTERVAL_MOVIE
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p315.EOPNOTSUPP_ERRNO)
        self.assertTrue(r.dormant_trap_blocked)

    def test_63_critical_slot1_tier0_vault_firewall_blocks_rotate_and_photo_capture_erofs(self) -> None:
        for op in (
            p315.PB_OP_ROTATE,
            p315.PB_OP_PHOTO_CAPTURE,
            p315.PB_OP_BEAUTY_EFFECT,
            p315.PB_OP_TRIMMING,
        ):
            r = p315.simulate_interval_playback_edit_and_vault_firewall_hil(
                operation=op,
                select_playback_media=p315.SLOT_1,
                slot1_is_tier0_vault=True,
            )
            self.assertFalse(r.admitted, op)
            self.assertEqual(r.errno_code, p315.EROFS_ERRNO, op)
            self.assertTrue(r.tier0_vault_firewall_triggered, op)
            self.assertEqual(r.slot1_data_sector_writes, 0, op)
            self.assertFalse(r.slot1_avf_info_mutated, op)
            self.assertEqual(r.slot1_vault_pb_edit_mutation_bytes, 0, op)

    def test_64_reverse_copy_slot2_to_slot1_tier0_vault_blocked_erofs(self) -> None:
        r = p315.simulate_interval_playback_edit_and_vault_firewall_hil(
            operation=p315.PB_OP_COPY,
            select_playback_media=p315.SLOT_2,
            slot1_is_tier0_vault=True,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p315.EROFS_ERRNO)
        self.assertTrue(r.tier0_vault_firewall_triggered)
        self.assertEqual(r.slot1_data_sector_writes, 0)

    def test_65_dormant_beauty_effect_and_trimming_on_slot2_rejected_eopnotsupp(self) -> None:
        for op in (p315.PB_OP_BEAUTY_EFFECT, p315.PB_OP_TRIMMING):
            r = p315.simulate_interval_playback_edit_and_vault_firewall_hil(
                operation=op,
                select_playback_media=p315.SLOT_2,
                slot1_is_tier0_vault=True,
            )
            self.assertFalse(r.admitted, op)
            self.assertEqual(r.errno_code, p315.EOPNOTSUPP_ERRNO, op)
            self.assertTrue(r.dormant_trap_blocked, op)

    def test_66_virtual_slot2_rotate_270deg_non_destructive(self) -> None:
        r = p315.simulate_interval_playback_edit_and_vault_firewall_hil(
            operation=p315.PB_OP_ROTATE,
            select_playback_media=p315.SLOT_2,
            slot1_is_tier0_vault=True,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.virtual_slot2_rotated_deg, 270)
        self.assertEqual(r.slot1_data_sector_writes, 0)
        self.assertEqual(r.physical_device_writes, 0)

    def test_67_virtual_slot2_photo_capture_all_3_file_types(self) -> None:
        expected_ext = {
            p315.PB_JPEG_HEIF_JPEG: ".JPG",
            p315.PB_JPEG_HEIF_420: ".HIF",
            p315.PB_JPEG_HEIF_422: ".HIF",
        }
        for ftype, ext in expected_ext.items():
            r = p315.simulate_interval_playback_edit_and_vault_firewall_hil(
                operation=p315.PB_OP_PHOTO_CAPTURE,
                select_playback_media=p315.SLOT_2,
                photo_capture_file_type=ftype,
            )
            self.assertTrue(r.admitted, ftype)
            self.assertEqual(r.effective_photo_capture_file_type, ftype)
            self.assertTrue(r.virtual_slot2_captured_file.endswith(ext), ftype)
            self.assertEqual(r.slot1_data_sector_writes, 0)
            self.assertEqual(r.physical_device_writes, 0)

    def test_68_active_playback_edit_items_exact_4_items(self) -> None:
        r = p315.simulate_interval_playback_edit_and_vault_firewall_hil()
        self.assertEqual(
            r.playback_edit_items_exposed,
            ("Rotate", "Photo Capture", "JPEG/HEIF Switch", "Copy"),
        )

    def test_69_fx6_rejects_interval_pb_photo_capture_beauty_trimming_eopnotsupp(self) -> None:
        for op in (p315.PB_OP_VIEW_INTERVAL, p315.PB_OP_PHOTO_CAPTURE, p315.PB_OP_ROTATE):
            r = p315.simulate_interval_playback_edit_and_vault_firewall_hil(
                body_profile=p315.BODY_MODEL_FX6, operation=op
            )
            self.assertFalse(r.admitted, op)
            self.assertEqual(r.errno_code, p315.EOPNOTSUPP_ERRNO, op)

    def test_70_invalid_65d_arguments_rejected_einval(self) -> None:
        self.assertEqual(
            p315.simulate_interval_playback_edit_and_vault_firewall_hil(
                operation="BOGUS_OP"
            ).errno_code,
            p315.EINVAL_ERRNO,
        )
        self.assertEqual(
            p315.simulate_interval_playback_edit_and_vault_firewall_hil(
                select_playback_media="Slot 9"
            ).errno_code,
            p315.EINVAL_ERRNO,
        )
        self.assertEqual(
            p315.simulate_interval_playback_edit_and_vault_firewall_hil(
                photo_capture_file_type="RAW"
            ).errno_code,
            p315.EINVAL_ERRNO,
        )


class TestRedlinesCLIAndSuiteStage65Integration(unittest.TestCase):
    """Hard safety redlines, standalone CLI, and 65/65 Milestone Suite orchestration (tests 71..88)."""

    def test_71_full_phase315_report_65_65_milestone(self) -> None:
        rep = p315.run_phase315_touch_shooting_disp_zero_evf_interval_pb_coemulation()
        self.assertTrue(rep["all_checks_passed"])
        self.assertTrue(rep["is_65th_stage_milestone"])
        self.assertEqual(rep["milestone"], "65/65")
        self.assertEqual(rep["stage_index"], 65)
        self.assertEqual(rep["stage_total"], 65)
        self.assertEqual(rep["phase_number"], 315)

    def test_72_clean_room_report_deterministic_digest_both_env_vars(self) -> None:
        r1 = p315.run_phase315_touch_shooting_disp_zero_evf_interval_pb_coemulation(
            force_clean_room=True
        )
        r2 = p315.run_phase315_touch_shooting_disp_zero_evf_interval_pb_coemulation(
            env={p315.ENV_FORCE_CLEAN_ROOM: "1"}
        )
        r3 = p315.run_phase315_touch_shooting_disp_zero_evf_interval_pb_coemulation(
            env={p315.ENV_CLEAN_ROOM_TEST: "1"}
        )
        self.assertEqual(r1["source_mode"], p315.SOURCE_MODE_CLEAN_ROOM)
        self.assertEqual(r2["source_mode"], p315.SOURCE_MODE_CLEAN_ROOM)
        self.assertEqual(r3["source_mode"], p315.SOURCE_MODE_CLEAN_ROOM)
        self.assertEqual(r1["redlines"], r2["redlines"])
        self.assertEqual(r2["redlines"], r3["redlines"])
        self.assertEqual(r1["audit_digest_sha256"], r2["audit_digest_sha256"])
        self.assertEqual(r2["audit_digest_sha256"], r3["audit_digest_sha256"])

    def test_73_all_hardware_write_and_wave55_redlines_locked(self) -> None:
        rep = p315.run_phase315_touch_shooting_disp_zero_evf_interval_pb_coemulation(
            force_clean_room=True
        )
        red = rep["redlines"]
        self.assertTrue(red["p8_cp_mutation_forbidden"])
        self.assertTrue(red["cnflasha_userspace_write_blocked"])
        for false_key in (
            "persistent_emmc_writes_authorized",
            "hardware_live_attachment_authorized",
            "overall_ready_for_hardware_attach",
            "isp_write_authorized",
            "spi_nor_write_authorized",
            "el3_payload_transmit_authorized",
            "fx3_has_builtin_evf",
            "fx3_has_eye_sensor",
            "fx3_has_finder_monitor_button",
            "fx6_has_builtin_evf",
            "fx6_uses_loupe_terminology",
            "fx6_has_still_flash_stack",
            "slot1_avf_info_mutated",
        ):
            self.assertFalse(red[false_key], false_key)
        for zero_key in (
            "nop_count",
            "guest_code_modification_bytes",
            "cp_mutation_bytes",
            "wbi_mutation_bytes",
            "calibration_mutation_bytes",
            "cnflasha_mutation_bytes",
            "nvram_persistent_writes",
            "bk4_persistent_nvram_writes",
            "physical_device_writes",
            "emmc_nflasha_write_count",
            "emmc_mutation_bytes",
            "emmc_corruptions",
            "spi_nor_mutation_bytes",
            "otp_fuse_touches",
            "rpmb_counter_increments",
            "physical_usb_packets_emitted",
            "passive_tx_bytes_emitted",
            "dormant_touch_shutter_ae_pad_footer_exposed_events",
            "zero_evf_finder_monitor_blackout_trap_events",
            "still_only_ael_flash_movie_sq_bypass_events",
            "sync_cord_external_flash_bypass_events",
            "interval_play_speed_out_of_1_9_range_events",
            "dormant_beauty_effect_or_trimming_exposed_events",
            "slot1_data_sector_writes",
            "slot1_vault_pb_edit_mutation_bytes",
            "rsv_orphan_count",
            "wf12_00342260_hits",
            "appfw_crashes",
            "null_gpio_derefs",
            "mailbox_stalls",
            "stock_cp_fault_count",
            "raw_firmware_bytes_leaked",
        ):
            self.assertEqual(red[zero_key], 0, zero_key)

    def test_74_standalone_cli_help_uses_sys_executable_and_percent_escaping(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                str(FX3_VM_DIR / "realhw_touch_shooting_disp_zero_evf_interval_pb_coemulator.py"),
                "--help",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("100%", proc.stdout)
        self.assertIn("65/65", proc.stdout)

    def test_75_standalone_cli_summary_and_json_modes(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = p315.main(["--self-test", "--clean-room", "--summary"])
        self.assertEqual(rc, 0)
        self.assertIn("[PASS] Phase 315 Stage 65 (65/65 Milestone)", buf.getvalue())

        buf_json = io.StringIO()
        with contextlib.redirect_stdout(buf_json):
            rc2 = p315.main(["--self-test", "--clean-room", "--json"])
        self.assertEqual(rc2, 0)
        parsed = json.loads(buf_json.getvalue())
        self.assertEqual(parsed["milestone"], "65/65")
        self.assertTrue(parsed["is_65th_stage_milestone"])
        self.assertTrue(parsed["all_checks_passed"])

    def test_76_no_raw_firmware_bytes_leaked_in_json_output(self) -> None:
        rep = p315.run_phase315_touch_shooting_disp_zero_evf_interval_pb_coemulation()
        dumped = json.dumps(rep)
        self.assertNotIn("\\x7fELF", dumped)
        self.assertEqual(rep["redlines"]["raw_firmware_bytes_leaked"], 0)

    def test_77_no_hardcoded_usr_bin_python3_in_stage65_files(self) -> None:
        mod_src = (
            FX3_VM_DIR / "realhw_touch_shooting_disp_zero_evf_interval_pb_coemulator.py"
        ).read_text(encoding="utf-8")
        tst_src = Path(__file__).read_text(encoding="utf-8")
        forbidden = "/usr/bin/" + "python3"
        self.assertNotIn(forbidden, mod_src)
        self.assertNotIn(forbidden, tst_src)

    def test_78_suite_default_config_enables_stage65(self) -> None:
        cfg = suite.CoEmulationConfig()
        self.assertTrue(cfg.include_phase315_realhw_touch_shooting_disp_zero_evf_interval_pb_hil)
        self.assertTrue(cfg.include_stage65)
        self.assertTrue(cfg.stage65_realhw_touch_shooting_disp_zero_evf_interval_pb_hil)

    def test_79_suite_full_run_contains_at_least_65_stages_and_milestone_65_65(self) -> None:
        t0 = time.monotonic()
        rep = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig())
        elapsed = time.monotonic() - t0
        self.assertTrue(rep["all_checks_passed"])
        stage_keys = [k for k in rep if re.match(r"^stage\d+_", k)]
        self.assertGreaterEqual(len(stage_keys), 65)
        s65 = rep["stage65_realhw_touch_shooting_disp_zero_evf_interval_pb_hil"]
        self.assertTrue(s65["all_checks_passed"])
        self.assertTrue(s65["is_65th_stage_milestone"])
        self.assertEqual(s65["milestone"], "65/65")
        self.assertEqual(s65["phase_number"], 315)
        max_elapsed = 30.0 if IS_CI else 15.0
        self.assertLess(elapsed, max_elapsed)

    def test_80_suite_fast_isolated_stage65_only_pass(self) -> None:
        cfg = suite.CoEmulationConfig(**_fast_suite_kwargs())
        rep = suite.run_fx3_vm_coemulation_suite(cfg)
        self.assertTrue(rep["all_checks_passed"])
        self.assertIsNone(rep.get("stage64_realhw_switch_vh_af_stdadj_tcub_copy_slot_hil"))
        self.assertIsNotNone(rep.get("stage65_realhw_touch_shooting_disp_zero_evf_interval_pb_hil"))

    def test_81_suite_skip_flags_disable_stage65(self) -> None:
        for flag in ("--skip-stage65", "--no-include-stage65", "--skip-phase315"):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = suite.main([*_FAST_CLI_FLAGS, flag, "--json"])
            self.assertEqual(rc, 0)
            data = json.loads(buf.getvalue())
            self.assertNotIn("stage65_realhw_touch_shooting_disp_zero_evf_interval_pb_hil", data)
            self.assertFalse(data["config"]["include_stage65"])

    def test_82_suite_cli_help_includes_stage65_and_100pct(self) -> None:
        proc_help = subprocess.run(
            [sys.executable, "-B", str(FX3_VM_DIR / "fx3_vm_coemulation_suite.py"), "--help"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc_help.returncode, 0, proc_help.stderr)
        self.assertIn("--include-stage65", proc_help.stdout)
        self.assertIn("--skip-phase315", proc_help.stdout)
        self.assertIn("65/65 Milestone", proc_help.stdout)
        self.assertIn("100%", proc_help.stdout)

    def test_83_suite_cli_summary_includes_stage65_milestone_m65_and_redlines(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = suite.main([*_FAST_CLI_FLAGS, "--include-stage65", "--summary"])
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn(
            "realhw_touch_shooting_disp_zero_evf_interval_pb_hil=CLEAN_ROOM_SYNTHETIC("
            "m65=65/65,tch_byp=0,evf_trap=0,fx3_evf=0,ael_byp=0,ivl_byp=0,s1_wr=0,emmc_wr=0)",
            out,
        )

    def test_84_suite_subprocess_uses_sys_executable_with_clean_room(self) -> None:
        env = dict(os.environ)
        env["FX3_FX6_FORCE_CLEAN_ROOM"] = "1"
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                str(FX3_VM_DIR / "fx3_vm_coemulation_suite.py"),
                *_FAST_CLI_FLAGS,
                "--summary",
            ],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("[PASS]", proc.stdout)
        self.assertIn("evf_trap=0", proc.stdout)
        self.assertIn("s1_wr=0", proc.stdout)

    def test_85_stage65_payload_keys_present_and_complete(self) -> None:
        rep = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig(**_fast_suite_kwargs()))
        s65 = rep["stage65_realhw_touch_shooting_disp_zero_evf_interval_pb_hil"]
        for key in (
            "pillar_a_touch_operation_4item_and_dormant_guard_hil",
            "pillar_b_disp_screen_disp_set_and_zero_evf_blackout_guard_hil",
            "pillar_c_still_ael_w_shutter_and_flash_submenu_vs_fx6_hil",
            "pillar_d_interval_play_speed_and_slot1_vault_edit_firewall_hil",
            "phase315_audit_digest_sha256",
            "donor_audit",
        ):
            self.assertIn(key, s65)

    def test_86_stage65_config_serialization_in_suite_report(self) -> None:
        rep = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig(**_fast_suite_kwargs()))
        cfg = rep["config"]
        self.assertTrue(cfg["include_phase315_realhw_touch_shooting_disp_zero_evf_interval_pb_hil"])
        self.assertTrue(cfg["include_stage65"])
        self.assertTrue(cfg["stage65_realhw_touch_shooting_disp_zero_evf_interval_pb_hil"])

    def test_87_suite_tamper_zero_evf_or_slot1_vault_detected_by_suite(self) -> None:
        with unittest.mock.patch.object(p315, "FX3_HAS_BUILTIN_EVF", True):
            rep1 = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig(**_fast_suite_kwargs()))
            self.assertFalse(rep1["all_checks_passed"])

        with unittest.mock.patch.object(p315, "SLOT1_AVF_INFO_MUTATED", True):
            rep2 = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig(**_fast_suite_kwargs()))
            self.assertFalse(rep2["all_checks_passed"])

    def test_88_dual_mode_suite_clean_room_and_stage65_probe_4_pillars(self) -> None:
        r_clean = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig(force_clean_room=True))
        self.assertTrue(r_clean["all_checks_passed"])
        clean_stages = [k for k in r_clean if re.match(r"^stage\d+_", k)]
        self.assertGreaterEqual(len(clean_stages), 65)

        probe = r_clean["stage65_realhw_touch_shooting_disp_zero_evf_interval_pb_hil"][
            "pillar_d_interval_play_speed_and_slot1_vault_edit_firewall_hil"
        ]["stage65_milestone_probe"]
        self.assertEqual(probe["stage_index"], 65)
        self.assertEqual(probe["stage_total"], 65)
        self.assertEqual(probe["milestone"], "65/65")
        self.assertTrue(probe["is_65th_stage_milestone"])
        self.assertEqual(len(probe["wave55_pillars"]), 4)


if __name__ == "__main__":
    unittest.main()
