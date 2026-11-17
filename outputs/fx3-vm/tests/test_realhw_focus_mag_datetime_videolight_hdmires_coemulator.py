#!/usr/bin/env python3
"""Unit tests for Phase 278 (Stage 55, 55/55):
Real-Hardware `ILME-FX3` (`0x91030080`, `ilc/2210`, `Ver. 7.02`) Wave-45
`[Focus Assistant]` (`Focus Magnifier`, `Auto Magnifier in MF`, `Initial Focus Mag.` `x1.0`,
`AF in Focus Mag.`) & `[Peaking Display]` / `[AF Illuminator]` (Still-Only),
`[Area/Date/Time Setting]` (`Setup > Area/Date`) & Zero-RF Creators' App Isolation, and
`[Video Light Mode]` (`Power Link` Default & MI-Shoe `5V <= 900 mA` Rail Budget) &
`[HDMI Resolution]` (`Auto` Default & Log `1080p` Override) HIL Co-Emulator (72 dual-mode tests).
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
import time
import unittest
import unittest.mock

FX3_VM_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = FX3_VM_DIR.parents[1]
if str(FX3_VM_DIR) not in sys.path:
    sys.path.insert(0, str(FX3_VM_DIR))

import fx3_vm_coemulation_suite as suite  # noqa: E402
import realhw_focus_mag_datetime_videolight_hdmires_coemulator as p278  # noqa: E402

IS_CI = os.environ.get("GITHUB_ACTIONS", "").lower() == "true"


def _fast_suite_kwargs(**overrides: object) -> dict:
    """Fast config skipping heavy unrelated stages for <50ms flag/override tests."""
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
]


class TestPhase278FocusMagDatetimeVideoLightHdmiResCoEmulator(unittest.TestCase):
    clean_audit: dict = {}
    default_audit: dict = {}
    clean_suite: dict = {}
    clean_suite_elapsed: float = 0.0
    default_suite: dict = {}
    default_suite_elapsed: float = 0.0

    @classmethod
    def setUpClass(cls) -> None:
        cls.clean_audit = p278.run_phase278_realhw_focus_mag_datetime_videolight_hdmires_hil(
            force_clean_room=True
        )
        cls.default_audit = p278.run_phase278_realhw_focus_mag_datetime_videolight_hdmires_hil()

        forced = p278.is_forced_clean_room()
        t0 = time.monotonic()
        cls.default_suite = suite.run_fx3_vm_coemulation_suite(
            suite.CoEmulationConfig(force_clean_room=True if forced else None)
        )
        cls.default_suite_elapsed = time.monotonic() - t0

        if forced:
            cls.clean_suite = cls.default_suite
            cls.clean_suite_elapsed = cls.default_suite_elapsed
        else:
            t1 = time.monotonic()
            cls.clean_suite = suite.run_fx3_vm_coemulation_suite(
                suite.CoEmulationConfig(**_fast_suite_kwargs(force_clean_room=True))
            )
            cls.clean_suite_elapsed = time.monotonic() - t1

    # ------------------------------------------------------------------
    # Group 1: Schema, Stage 55 (55/55) & O_RDONLY 18-Donor Verification (14 tests)
    # ------------------------------------------------------------------
    def test_01_schema_version_phase278_stage55_and_redline_constants(self) -> None:
        self.assertEqual(
            p278.SCHEMA_ID,
            "realhw_focus_mag_datetime_videolight_hdmires_coemulator_v1",
        )
        self.assertEqual(p278.PHASE_278_SCHEMA, p278.SCHEMA_ID)
        self.assertEqual(p278.PHASE_278_VERSION, "278.0.0")
        self.assertEqual(p278.PHASE_NUMBER, 278)
        self.assertEqual(p278.STAGE_INDEX, 55)
        self.assertEqual(p278.STAGE_TOTAL, 55)
        self.assertEqual(p278.MILESTONE_LABEL, "55/55")
        self.assertEqual(
            p278.STAGE_NAME,
            "stage55_realhw_focus_mag_datetime_videolight_hdmires_hil",
        )
        self.assertEqual(p278.FX3_MODEL_ID, 0x91030080)
        self.assertEqual(p278.FX6_MODEL_ID, 0x91020080)
        self.assertEqual(p278.FX3_HELP_GUIDE_ID, "ilc/2210")
        self.assertTrue(p278.CNFLASHA_USERSPACE_WRITE_BLOCKED)
        self.assertFalse(p278.PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(p278.HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        self.assertFalse(p278.OVERALL_READY_FOR_HARDWARE_ATTACH)

    def test_02_clean_room_audit_deterministic_sha256_digest(self) -> None:
        self.assertTrue(self.clean_audit["all_checks_passed"])
        self.assertEqual(self.clean_audit["source_mode"], p278.SOURCE_MODE_CLEAN_ROOM)
        again = p278.run_phase278_realhw_focus_mag_datetime_videolight_hdmires_hil(
            force_clean_room=True
        )
        self.assertEqual(
            self.clean_audit["audit_digest_sha256"],
            again["audit_digest_sha256"],
        )

    def test_03_both_clean_room_env_vars_force_clean_room(self) -> None:
        self.assertTrue(p278.is_forced_clean_room({p278.ENV_CLEAN_ROOM_TEST: "1"}))
        self.assertTrue(p278.is_forced_clean_room({p278.ENV_FORCE_CLEAN_ROOM: "1"}))
        self.assertTrue(p278.is_forced_clean_room({p278.ENV_CLEAN_ROOM_TEST: "true"}))
        self.assertFalse(p278.is_forced_clean_room({}))
        rep = p278.run_phase278_realhw_focus_mag_datetime_videolight_hdmires_hil(
            env={p278.ENV_CLEAN_ROOM_TEST: "1"}
        )
        self.assertEqual(rep["source_mode"], p278.SOURCE_MODE_CLEAN_ROOM)
        self.assertTrue(rep["all_checks_passed"])

    def test_04_donor_audit_18_artifacts_and_zero_raw_leakage(self) -> None:
        for rep in (self.clean_audit, self.default_audit):
            da = rep["donor_audit"]
            self.assertEqual(da["access_mode"], "O_RDONLY")
            self.assertEqual(da["donor_files_inspected"], 18)
            self.assertEqual(da["raw_firmware_bytes_leaked"], 0)
            self.assertTrue(da["focus_assistant_and_peaking_proven"])
            self.assertTrue(da["area_datetime_and_zero_rf_proven"])
            self.assertTrue(da["video_light_and_hdmi_res_proven"])
            self.assertTrue(da["all_contracts_verified"])
            self.assertEqual(list(da["errors"]), [])

    def test_05_compact_donors_exact_sizes_and_sha256(self) -> None:
        da = self.default_audit["donor_audit"]
        compact_keys = tuple(p278.EXPECTED_COMPACT_DONOR_SHA256.keys())
        self.assertEqual(len(compact_keys), 10)
        for key in compact_keys:
            item = da[key]
            self.assertEqual(item["file_bytes"], p278.EXPECTED_DONOR_BYTES[key], msg=key)
            self.assertEqual(len(item["sha256"]), 64, msg=key)
            self.assertTrue(item["sha256_verified"], msg=key)
            if da["source_mode"] == p278.SOURCE_MODE_LOCAL_DONOR:
                self.assertEqual(
                    item["sha256"],
                    p278.EXPECTED_COMPACT_DONOR_SHA256[key],
                    msg=key,
                )
            if key in ("fx3_string_en_f", "fx6_string_en"):
                self.assertTrue(item["uxd_container_ok"], msg=key)
            else:
                self.assertTrue(item["elf64_le_ok"], msg=key)

    def test_06_large_donors_bounded_4k_windows_and_head_sha256(self) -> None:
        da = self.default_audit["donor_audit"]
        large_keys = tuple(p278.EXPECTED_LARGE_HEAD4K_SHA256.keys())
        self.assertEqual(len(large_keys), 8)
        for key in large_keys:
            item = da[key]
            self.assertTrue(item["bounded_windows_only"], msg=key)
            self.assertEqual(item["file_bytes"], p278.EXPECTED_DONOR_BYTES[key], msg=key)
            self.assertEqual(len(item["head_sha256"]), 64, msg=key)
            self.assertTrue(item["head_sha256_verified"], msg=key)
            if da["source_mode"] == p278.SOURCE_MODE_LOCAL_DONOR:
                self.assertEqual(
                    item["head_sha256"],
                    p278.EXPECTED_LARGE_HEAD4K_SHA256[key],
                    msg=key,
                )
            self.assertGreater(item["bytes_read_total"], 0, msg=key)
            self.assertTrue(all(v == 1 for v in item["window_hits"].values()), msg=key)

    def test_07_fx3_string_en_f_proves_wave45_markers_and_rejects_absent(self) -> None:
        da = self.default_audit["donor_audit"]
        fx3_str = da["fx3_string_en_f"]
        for tok in (
            "Auto Magnifier in MF",
            "Focus Magnif. Time",
            "Initial Focus Mag.",
            "AF in Focus Mag.",
            "No Limit",
            "x1.0",
            "x4.0",
            "Peaking Display",
            "Peaking Level",
            "Peaking Color",
            "AF Illuminator",
            "Area/Date/Time Setting",
            "Location Info. Link",
            "Auto Time Correction",
            "Auto Area Adjustment",
            "Airplane Mode",
            "Video Light Mode",
            "Power Link",
            "REC Link",
            "HDMI Resolution",
            "2160p",
            "1080p",
            "Off(HDMI Only)",
            "Camera Settings Reset",
            "Initialize",
        ):
            self.assertEqual(fx3_str["marker_hits"][tok], 1, msg=tok)
        for absent in ("Date/Time Setup", "Autoframing Settings", "Built-In ND", "ECS"):
            self.assertEqual(fx3_str["absent_marker_hits"][absent], 0, msg=absent)

    def test_08_fx6_string_en_distinguishes_ilme_fx6_vocabulary(self) -> None:
        da = self.default_audit["donor_audit"]
        fx6_str = da["fx6_string_en"]
        for tok in ("Focus Magnifier", "Peaking Level", "Date/Time", "RAW Output", "1080i"):
            self.assertEqual(fx6_str["marker_hits"][tok], 1, msg=tok)
        for absent in (
            "Auto Magnifier in MF",
            "Area/Date/Time Setting",
            "Video Light Mode",
            "HDMI Resolution",
            "AF Illuminator",
        ):
            self.assertEqual(fx6_str["absent_marker_hits"][absent], 0, msg=absent)

    def test_09_donor_inspection_cached_fast_lt_0_2s_and_clean_room_fallback(self) -> None:
        t0 = time.monotonic()
        da = p278.inspect_phase278_donors()
        elapsed = time.monotonic() - t0
        self.assertLess(elapsed, 0.2 if not IS_CI else 2.0)
        self.assertTrue(da.all_contracts_verified)

        missing_root = REPO_ROOT / "work" / "__nonexistent_donor_tree_phase278__"
        with unittest.mock.patch.object(p278, "_iter_work_roots", return_value=(missing_root,)):
            fb = p278.inspect_phase278_donors(env={})
        self.assertEqual(fb.source_mode, p278.SOURCE_MODE_CLEAN_ROOM)
        self.assertTrue(fb.all_contracts_verified)

    def test_10_os_open_called_strictly_with_o_rdonly_when_local_donors_present(self) -> None:
        if p278.is_forced_clean_room():
            self.assertEqual(
                self.default_audit["source_mode"], p278.SOURCE_MODE_CLEAN_ROOM
            )
            return
        real_open = os.open
        seen_flags = []

        def _spy_open(path, flags, *args, **kwargs):
            seen_flags.append(flags)
            return real_open(path, flags, *args, **kwargs)

        p278._DONOR_AUDIT_CACHE.clear()
        with unittest.mock.patch("os.open", side_effect=_spy_open):
            da = p278.inspect_phase278_donors()
        self.assertTrue(da.all_contracts_verified)
        if da.source_mode == p278.SOURCE_MODE_LOCAL_DONOR:
            self.assertGreater(len(seen_flags), 0)
            for fl in seen_flags:
                self.assertEqual(fl & os.O_ACCMODE, os.O_RDONLY)

    def test_11_compact_donor_paths_and_bounded_window_bounds(self) -> None:
        for key, wins in p278.LARGE_DONOR_WINDOWS.items():
            fsize = p278.EXPECTED_DONOR_BYTES[key]
            for offset, label, token in wins:
                self.assertGreaterEqual(offset, 0, msg=f"{key}:{label}")
                self.assertLess(offset + len(token), fsize, msg=f"{key}:{label}")
                self.assertLessEqual(len(token), p278.BOUNDED_WINDOW_MAX_BYTES)

    def test_12_clean_room_synthetic_mode_has_identical_pillar_outcomes(self) -> None:
        for key in (
            "pillar_a_focus_assistant_and_peaking_hil",
            "pillar_b_area_datetime_and_zero_rf_hil",
            "pillar_c_d_video_light_hdmi_res_and_redlines",
        ):
            self.assertEqual(
                self.clean_audit[key],
                self.default_audit[key],
                msg=key,
            )

    def test_13_resolve_donor_paths_respects_clean_room_sentinel(self) -> None:
        paths = p278.resolve_phase278_donor_paths(env={p278.ENV_CLEAN_ROOM_TEST: "1"})
        self.assertEqual(len(paths), 18)
        for p in paths.values():
            self.assertIn(p278.CLEAN_ROOM_SENTINEL_DIRNAME, str(p))

    def test_14_fx3_compact_tokens_include_buspower_adjmedia_airplane_saveload(self) -> None:
        da = self.clean_audit["donor_audit"]
        self.assertEqual(da["fx3_buspower"]["marker_hits"]["BusPower_Init"], 1)
        self.assertEqual(da["fx3_adj_media"]["marker_hits"]["AVBB_SCN_START_HDMI"], 1)
        self.assertEqual(da["fx3_airplane"]["marker_hits"]["AirplaneModeTraceRecord"], 1)
        self.assertEqual(da["fx3_saveload"]["marker_hits"]["SaveLoadSettingsIf"], 1)
        self.assertEqual(da["fx3_media_cfg"]["marker_hits"]["InfraMediaConfig"], 1)
        self.assertEqual(da["fx3_media_common"]["marker_hits"]["clock_gettime"], 1)
        self.assertEqual(da["fx3_bt_core"]["marker_hits"]["InfraBTCore_"], 1)
        self.assertEqual(da["fx3_wlan_common"]["marker_hits"]["WlanControlCommon"], 1)

    # ------------------------------------------------------------------
    # Group 2: Sub-Model 55A — [Focus Assistant], [Peaking] & [AF Illuminator] (18 tests)
    # ------------------------------------------------------------------
    def test_15_focus_assistant_and_peaking_factory_defaults(self) -> None:
        res = p278.simulate_focus_assistant_and_peaking_hil()
        self.assertTrue(res.admitted)
        self.assertEqual(res.errno_code, 0)
        self.assertEqual(res.focus_assistant_menu_path, p278.FOCUS_ASSISTANT_MENU_PATH)
        self.assertEqual(res.peaking_menu_path, p278.PEAKING_DISPLAY_MENU_PATH)
        self.assertEqual(res.af_illuminator_menu_path, p278.AF_ILLUMINATOR_MENU_PATH)
        self.assertEqual(res.effective_auto_magnifier_in_mf, p278.TOGGLE_ON)
        self.assertEqual(res.focus_magnifier_default_key, "Custom Button 5")
        self.assertEqual(res.peaking_display_select_default_key, "Control Wheel Right")
        self.assertEqual(res.effective_focus_mag_time, "No Limit")
        self.assertEqual(res.effective_still_initial_focus_mag, "x1.0")
        self.assertEqual(res.effective_movie_initial_focus_mag, "x1.0")
        self.assertEqual(res.effective_af_in_focus_mag, p278.TOGGLE_ON)
        self.assertEqual(res.effective_peaking_display, p278.TOGGLE_OFF)
        self.assertEqual(res.effective_peaking_level, "Mid")
        self.assertEqual(res.effective_peaking_color, "White")
        self.assertEqual(res.effective_af_illuminator, "Auto")

    def test_16_reject_legacy_mf_assist_title_spoofing_eopnotsupp(self) -> None:
        res = p278.simulate_focus_assistant_and_peaking_hil(
            menu_item_title=p278.LEGACY_MF_ASSIST_TITLE
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p278.EOPNOTSUPP_ERRNO)
        self.assertEqual(res.reason_code, "LEGACY_MF_ASSIST_TITLE_SPOOF_REJECTED")
        self.assertEqual(res.legacy_mf_assist_spoof_events, 0)

    def test_17_invalid_focus_assistant_title_or_enum_einval(self) -> None:
        bad_title = p278.simulate_focus_assistant_and_peaking_hil(
            menu_item_title="Unknown Mag Title"
        )
        self.assertFalse(bad_title.admitted)
        self.assertEqual(bad_title.errno_code, p278.EINVAL_ERRNO)

        for kwargs in (
            {"configured_focus_mag_time": "10 Sec"},
            {"configured_still_initial_focus_mag": "x2.0"},
            {"configured_movie_initial_focus_mag": "x8.0"},
            {"configured_peaking_level": "Ultra"},
            {"configured_peaking_color": "Green"},
            {"configured_af_illuminator": "Always"},
        ):
            r = p278.simulate_focus_assistant_and_peaking_hil(**kwargs)
            self.assertFalse(r.admitted, msg=str(kwargs))
            self.assertEqual(r.errno_code, p278.EINVAL_ERRNO, msg=str(kwargs))

    def test_18_auto_magnifier_in_mf_focus_ring_triggers_in_mf_and_dmf_only(self) -> None:
        for fm in (p278.FOCUS_MODE_MF, p278.FOCUS_MODE_DMF):
            r = p278.simulate_focus_assistant_and_peaking_hil(
                focus_mode=fm,
                focus_ring_turned=True,
                configured_auto_magnifier_in_mf=p278.TOGGLE_ON,
                configured_movie_initial_focus_mag=p278.INITIAL_FOCUS_MAG_X4_0,
            )
            self.assertTrue(r.focus_magnifier_triggered, msg=fm)
            self.assertEqual(r.focus_magnifier_active_scale, "x4.0", msg=fm)

        r_off = p278.simulate_focus_assistant_and_peaking_hil(
            focus_mode=p278.FOCUS_MODE_MF,
            focus_ring_turned=True,
            configured_auto_magnifier_in_mf=p278.TOGGLE_OFF,
        )
        self.assertFalse(r_off.focus_magnifier_triggered)

        r_afc = p278.simulate_focus_assistant_and_peaking_hil(
            focus_mode=p278.FOCUS_MODE_AF_C,
            focus_ring_turned=True,
            configured_auto_magnifier_in_mf=p278.TOGGLE_ON,
        )
        self.assertFalse(r_afc.focus_magnifier_triggered)

    def test_19_custom_button_5_and_mf_lcd_double_tap_touch_gate(self) -> None:
        c5 = p278.simulate_focus_assistant_and_peaking_hil(
            focus_mode=p278.FOCUS_MODE_MF,
            custom_button_5_pressed=True,
            touch_operation=p278.TOGGLE_OFF,
            configured_movie_initial_focus_mag=p278.INITIAL_FOCUS_MAG_X4_0,
        )
        self.assertTrue(c5.focus_magnifier_triggered)
        self.assertEqual(c5.focus_magnifier_active_scale, "x4.0")

        dt_on = p278.simulate_focus_assistant_and_peaking_hil(
            focus_mode=p278.FOCUS_MODE_MF,
            touch_operation=p278.TOGGLE_ON,
            double_tap_lcd=True,
        )
        self.assertTrue(dt_on.focus_magnifier_triggered)

        dt_off = p278.simulate_focus_assistant_and_peaking_hil(
            focus_mode=p278.FOCUS_MODE_MF,
            touch_operation=p278.TOGGLE_OFF,
            double_tap_lcd=True,
        )
        self.assertFalse(dt_off.focus_magnifier_triggered)

    def test_20_separate_still_and_movie_initial_focus_mag_registers(self) -> None:
        still_res = p278.simulate_focus_assistant_and_peaking_hil(
            shooting_domain=p278.SHOOTING_DOMAIN_STILL,
            custom_button_5_pressed=True,
            configured_still_initial_focus_mag=p278.INITIAL_FOCUS_MAG_X4_0,
            configured_movie_initial_focus_mag=p278.INITIAL_FOCUS_MAG_X1_0,
        )
        movie_res = p278.simulate_focus_assistant_and_peaking_hil(
            shooting_domain=p278.SHOOTING_DOMAIN_MOVIE,
            custom_button_5_pressed=True,
            configured_still_initial_focus_mag=p278.INITIAL_FOCUS_MAG_X4_0,
            configured_movie_initial_focus_mag=p278.INITIAL_FOCUS_MAG_X1_0,
        )
        sq_res = p278.simulate_focus_assistant_and_peaking_hil(
            shooting_domain=p278.SHOOTING_DOMAIN_SQ,
            custom_button_5_pressed=True,
            configured_still_initial_focus_mag=p278.INITIAL_FOCUS_MAG_X4_0,
            configured_movie_initial_focus_mag=p278.INITIAL_FOCUS_MAG_X1_0,
        )
        self.assertEqual(still_res.focus_magnifier_active_scale, "x4.0")
        self.assertEqual(movie_res.focus_magnifier_active_scale, "x1.0")
        self.assertEqual(sq_res.focus_magnifier_active_scale, "x1.0")

    def test_21_focus_magnif_time_all_three_options_supported(self) -> None:
        for mag_time in p278.VALID_FOCUS_MAG_TIMES:
            res = p278.simulate_focus_assistant_and_peaking_hil(
                configured_focus_mag_time=mag_time
            )
            self.assertTrue(res.admitted, msg=mag_time)
            self.assertEqual(res.effective_focus_mag_time, mag_time)

    def test_22_still_af_in_focus_mag_on_refocus_vs_off_cancels(self) -> None:
        on_res = p278.simulate_focus_assistant_and_peaking_hil(
            shooting_domain=p278.SHOOTING_DOMAIN_STILL,
            focus_mode=p278.FOCUS_MODE_DMF,
            focus_ring_turned=True,
            half_press_shutter=True,
            configured_af_in_focus_mag=p278.TOGGLE_ON,
        )
        self.assertTrue(on_res.focus_magnifier_triggered)
        self.assertTrue(on_res.af_in_focus_mag_refocus_active)

        off_res = p278.simulate_focus_assistant_and_peaking_hil(
            shooting_domain=p278.SHOOTING_DOMAIN_STILL,
            focus_mode=p278.FOCUS_MODE_DMF,
            focus_ring_turned=True,
            half_press_shutter=True,
            configured_af_in_focus_mag=p278.TOGGLE_OFF,
        )
        self.assertFalse(off_res.focus_magnifier_triggered)
        self.assertFalse(off_res.af_in_focus_mag_refocus_active)

    def test_23_hdmi_raw_output_locks_out_focus_magnifier_and_blocks_bypass(self) -> None:
        locked = p278.simulate_focus_assistant_and_peaking_hil(
            custom_button_5_pressed=True,
            hdmi_raw_output=p278.TOGGLE_ON,
            monitor_sink=p278.MONITOR_SINK_EXTERNAL_HDMI,
        )
        self.assertTrue(locked.admitted)
        self.assertTrue(locked.focus_mag_locked_by_hdmi_raw)
        self.assertFalse(locked.focus_magnifier_triggered)

        bypass = p278.simulate_focus_assistant_and_peaking_hil(
            hdmi_raw_output=p278.TOGGLE_ON,
            force_focus_mag_during_hdmi_raw=True,
        )
        self.assertFalse(bypass.admitted)
        self.assertEqual(bypass.errno_code, p278.EOPNOTSUPP_ERRNO)
        self.assertTrue(bypass.focus_mag_locked_by_hdmi_raw)

    def test_24_peaking_display_all_levels_and_colors_lcd_only_clean_hdmi(self) -> None:
        for lvl in p278.VALID_PEAKING_LEVELS:
            for col in p278.VALID_PEAKING_COLORS:
                lcd = p278.simulate_focus_assistant_and_peaking_hil(
                    configured_peaking_display=p278.TOGGLE_ON,
                    configured_peaking_level=lvl,
                    configured_peaking_color=col,
                    monitor_sink=p278.MONITOR_SINK_LCD_LIVE_VIEW,
                )
                self.assertTrue(lcd.lcd_peaking_rendered)
                self.assertFalse(lcd.external_hdmi_mag_or_peaking_baked)
                self.assertEqual(lcd.effective_peaking_level, lvl)
                self.assertEqual(lcd.effective_peaking_color, col)

                hdmi = p278.simulate_focus_assistant_and_peaking_hil(
                    configured_peaking_display=p278.TOGGLE_ON,
                    configured_peaking_level=lvl,
                    configured_peaking_color=col,
                    monitor_sink=p278.MONITOR_SINK_EXTERNAL_HDMI,
                )
                self.assertFalse(hdmi.lcd_peaking_rendered)
                self.assertFalse(hdmi.external_hdmi_mag_or_peaking_baked)
                self.assertEqual(hdmi.hdmi_clean_feed_mag_or_peaking_leaked_pixels, 0)

    def test_25_forced_hdmi_mag_or_peaking_bake_blocked_eopnotsupp(self) -> None:
        res = p278.simulate_focus_assistant_and_peaking_hil(
            configured_peaking_display=p278.TOGGLE_ON,
            monitor_sink=p278.MONITOR_SINK_EXTERNAL_HDMI,
            force_bake_mag_or_peaking_to_hdmi=True,
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p278.EOPNOTSUPP_ERRNO)
        self.assertEqual(res.hdmi_clean_feed_mag_or_peaking_leaked_pixels, 0)

    def test_26_af_illuminator_still_only_fires_in_af_s_af_a_dmf_low_light(self) -> None:
        for fm in (p278.FOCUS_MODE_AF_S, p278.FOCUS_MODE_AF_A, p278.FOCUS_MODE_DMF):
            res = p278.simulate_focus_assistant_and_peaking_hil(
                shooting_domain=p278.SHOOTING_DOMAIN_STILL,
                focus_mode=fm,
                low_light_scene=True,
                configured_af_illuminator=p278.AF_ILLUMINATOR_AUTO,
            )
            self.assertTrue(res.af_illuminator_fired, msg=fm)

        still_afc = p278.simulate_focus_assistant_and_peaking_hil(
            shooting_domain=p278.SHOOTING_DOMAIN_STILL,
            focus_mode=p278.FOCUS_MODE_AF_C,
            low_light_scene=True,
            configured_af_illuminator=p278.AF_ILLUMINATOR_AUTO,
        )
        self.assertFalse(still_afc.af_illuminator_fired)

        still_off = p278.simulate_focus_assistant_and_peaking_hil(
            shooting_domain=p278.SHOOTING_DOMAIN_STILL,
            focus_mode=p278.FOCUS_MODE_AF_S,
            low_light_scene=True,
            configured_af_illuminator=p278.AF_ILLUMINATOR_OFF,
        )
        self.assertFalse(still_off.af_illuminator_fired)

    def test_27_af_illuminator_never_fires_in_movie_or_sq_and_blocks_override(self) -> None:
        for dom in (p278.SHOOTING_DOMAIN_MOVIE, p278.SHOOTING_DOMAIN_SQ):
            sup = p278.simulate_focus_assistant_and_peaking_hil(
                shooting_domain=dom,
                focus_mode=p278.FOCUS_MODE_AF_S,
                low_light_scene=True,
                configured_af_illuminator=p278.AF_ILLUMINATOR_AUTO,
            )
            self.assertTrue(sup.admitted, msg=dom)
            self.assertFalse(sup.af_illuminator_fired, msg=dom)
            self.assertEqual(sup.af_illuminator_movie_or_sq_fire_events, 0)

            blk = p278.simulate_focus_assistant_and_peaking_hil(
                shooting_domain=dom,
                low_light_scene=True,
                force_fire_af_illuminator_in_movie_or_sq=True,
            )
            self.assertFalse(blk.admitted, msg=dom)
            self.assertEqual(blk.errno_code, p278.EOPNOTSUPP_ERRNO, msg=dom)
            self.assertEqual(blk.af_illuminator_movie_or_sq_fire_events, 0)

    def test_28_focus_and_peaking_reset_by_camera_settings_reset_and_initialize(self) -> None:
        for act in (p278.RESET_ACTION_CAMERA_SETTINGS_RESET, p278.RESET_ACTION_INITIALIZE):
            r = p278.simulate_focus_assistant_and_peaking_hil(
                configured_auto_magnifier_in_mf=p278.TOGGLE_OFF,
                configured_focus_mag_time=p278.FOCUS_MAG_TIME_5S,
                configured_still_initial_focus_mag=p278.INITIAL_FOCUS_MAG_X4_0,
                configured_movie_initial_focus_mag=p278.INITIAL_FOCUS_MAG_X4_0,
                configured_af_in_focus_mag=p278.TOGGLE_OFF,
                configured_peaking_display=p278.TOGGLE_ON,
                configured_peaking_level=p278.PEAKING_LEVEL_HIGH,
                configured_peaking_color=p278.PEAKING_COLOR_BLUE,
                configured_af_illuminator=p278.AF_ILLUMINATOR_OFF,
                reset_action=act,
            )
            self.assertTrue(r.focus_items_reset_to_factory, msg=act)
            self.assertFalse(r.focus_items_survived_reset, msg=act)
            self.assertEqual(r.effective_auto_magnifier_in_mf, p278.TOGGLE_ON)
            self.assertEqual(r.effective_focus_mag_time, p278.FOCUS_MAG_TIME_NO_LIMIT)
            self.assertEqual(r.effective_still_initial_focus_mag, "x1.0")
            self.assertEqual(r.effective_movie_initial_focus_mag, "x1.0")
            self.assertEqual(r.effective_af_in_focus_mag, p278.TOGGLE_ON)
            self.assertEqual(r.effective_peaking_display, p278.TOGGLE_OFF)
            self.assertEqual(r.effective_peaking_level, p278.PEAKING_LEVEL_MID)
            self.assertEqual(r.effective_peaking_color, p278.PEAKING_COLOR_WHITE)
            self.assertEqual(r.effective_af_illuminator, p278.AF_ILLUMINATOR_AUTO)

    def test_29_focus_and_peaking_survive_reset_network_set(self) -> None:
        r = p278.simulate_focus_assistant_and_peaking_hil(
            configured_auto_magnifier_in_mf=p278.TOGGLE_OFF,
            configured_focus_mag_time=p278.FOCUS_MAG_TIME_2S,
            configured_still_initial_focus_mag=p278.INITIAL_FOCUS_MAG_X4_0,
            configured_movie_initial_focus_mag=p278.INITIAL_FOCUS_MAG_X4_0,
            configured_af_in_focus_mag=p278.TOGGLE_OFF,
            configured_peaking_display=p278.TOGGLE_ON,
            configured_peaking_level=p278.PEAKING_LEVEL_LOW,
            configured_peaking_color=p278.PEAKING_COLOR_YELLOW,
            configured_af_illuminator=p278.AF_ILLUMINATOR_OFF,
            reset_action=p278.RESET_ACTION_RESET_NETWORK_SET,
        )
        self.assertTrue(r.focus_items_survived_reset)
        self.assertFalse(r.focus_items_reset_to_factory)
        self.assertEqual(r.effective_auto_magnifier_in_mf, p278.TOGGLE_OFF)
        self.assertEqual(r.effective_focus_mag_time, p278.FOCUS_MAG_TIME_2S)
        self.assertEqual(r.effective_peaking_level, p278.PEAKING_LEVEL_LOW)
        self.assertEqual(r.effective_peaking_color, p278.PEAKING_COLOR_YELLOW)
        self.assertEqual(r.effective_af_illuminator, p278.AF_ILLUMINATOR_OFF)

    def test_30_hdmi_info_display_on_vs_off_clean_exit(self) -> None:
        r_clean = p278.simulate_focus_assistant_and_peaking_hil(
            configured_peaking_display=p278.TOGGLE_ON,
            hdmi_info_display=p278.TOGGLE_OFF,
            monitor_sink=p278.MONITOR_SINK_EXTERNAL_HDMI,
        )
        self.assertFalse(r_clean.lcd_peaking_rendered)
        self.assertFalse(r_clean.external_hdmi_mag_or_peaking_baked)
        self.assertEqual(r_clean.hdmi_clean_feed_mag_or_peaking_leaked_pixels, 0)

    def test_31_invalid_toggle_domain_or_reset_einval(self) -> None:
        for kwargs in (
            {"shooting_domain": "CINE_UNKNOWN"},
            {"focus_mode": "MF_INVALID"},
            {"touch_operation": "Auto"},
            {"monitor_sink": "EVF_INTERNAL"},
            {"reset_action": "FACTORY_NUKE"},
        ):
            r = p278.simulate_focus_assistant_and_peaking_hil(**kwargs)
            self.assertFalse(r.admitted, msg=str(kwargs))
            self.assertEqual(r.errno_code, p278.EINVAL_ERRNO, msg=str(kwargs))

    def test_32_pillar_a_summary_passed_and_zero_writes(self) -> None:
        pa = self.clean_audit["pillar_a_focus_assistant_and_peaking_hil"]
        self.assertTrue(pa["passed"])
        self.assertEqual(pa["exact_auto_magnifier_title"], "Auto Magnifier in MF")
        self.assertEqual(pa["focus_magnifier_default_key"], "Custom Button 5")
        self.assertEqual(pa["factory_defaults_ok"]["physical_device_writes"], 0)
        self.assertEqual(pa["factory_defaults_ok"]["bk4_persistent_nvram_writes"], 0)

    # ------------------------------------------------------------------
    # Group 3: Sub-Model 55B — [Area/Date/Time Setting] & Zero-RF Isolation (14 tests)
    # ------------------------------------------------------------------
    def test_33_area_datetime_initial_unconfigured_state(self) -> None:
        res = p278.simulate_area_datetime_and_zero_rf_hil()
        self.assertTrue(res.admitted)
        self.assertEqual(res.menu_path, p278.AREA_DATETIME_MENU_PATH)
        self.assertEqual(res.menu_item_title, p278.AREA_DATETIME_OFFICIAL_TITLE)
        self.assertEqual(res.effective_area_setting, p278.AREA_UNCONFIGURED)
        self.assertEqual(res.effective_daylight_savings, p278.TOGGLE_OFF)
        self.assertEqual(res.effective_date_format, p278.DATE_FORMAT_YYYY_MM_DD)
        self.assertTrue(res.rtc_reprompt_required)
        self.assertTrue(res.creators_app_sync_blocked_by_airplane_mode)
        self.assertEqual(res.passive_tx_bytes_emitted, 0)

    def test_34_reject_legacy_date_time_setup_spoofing_eopnotsupp(self) -> None:
        res = p278.simulate_area_datetime_and_zero_rf_hil(
            menu_item_title=p278.LEGACY_DATE_TIME_SETUP_TITLE
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p278.EOPNOTSUPP_ERRNO)
        self.assertEqual(res.reason_code, "LEGACY_DATE_TIME_SETUP_TITLE_SPOOF_REJECTED")
        self.assertEqual(res.legacy_date_time_setup_spoof_events, 0)

    def test_35_invalid_area_datetime_parameters_rejected_einval(self) -> None:
        for kwargs in (
            {"menu_item_title": "Clock Setup"},
            {"bench_stage": "H9"},
            {"configured_area_setting": "Mars Base"},
            {"configured_daylight_savings": "Auto"},
            {"configured_date_format": "YYYY/MM/DD"},
            {"configured_date_time": "2026-11-17"},
        ):
            r = p278.simulate_area_datetime_and_zero_rf_hil(**kwargs)
            self.assertFalse(r.admitted, msg=str(kwargs))
            self.assertEqual(r.errno_code, p278.EINVAL_ERRNO, msg=str(kwargs))

    def test_36_area_datetime_survives_camera_settings_reset_under_setup(self) -> None:
        res = p278.simulate_area_datetime_and_zero_rf_hil(
            configured_area_setting="Los Angeles",
            configured_daylight_savings=p278.TOGGLE_ON,
            configured_date_time="2026-11-17 15:45:12",
            configured_date_format=p278.DATE_FORMAT_MM_DD_YYYY,
            reset_action=p278.RESET_ACTION_CAMERA_SETTINGS_RESET,
        )
        self.assertTrue(res.admitted)
        self.assertTrue(res.area_datetime_survived_camera_reset)
        self.assertFalse(res.area_datetime_cleared_by_initialize)
        self.assertFalse(res.rtc_reprompt_required)
        self.assertEqual(res.effective_area_setting, "Los Angeles")
        self.assertEqual(res.effective_daylight_savings, p278.TOGGLE_ON)
        self.assertEqual(res.effective_date_time, "2026-11-17 15:45:12")
        self.assertEqual(res.effective_date_format, p278.DATE_FORMAT_MM_DD_YYYY)

    def test_37_area_datetime_survives_reset_network_set(self) -> None:
        res = p278.simulate_area_datetime_and_zero_rf_hil(
            airplane_mode=p278.TOGGLE_OFF,
            configured_area_setting="Tokyo",
            configured_daylight_savings=p278.TOGGLE_OFF,
            configured_date_time="2026-11-17 08:00:00",
            configured_date_format=p278.DATE_FORMAT_DD_MM_YYYY,
            configured_location_info_link=p278.TOGGLE_ON,
            configured_auto_time_correction=p278.TOGGLE_ON,
            reset_action=p278.RESET_ACTION_RESET_NETWORK_SET,
        )
        self.assertTrue(res.area_datetime_survived_camera_reset)
        self.assertEqual(res.effective_area_setting, "Tokyo")
        self.assertEqual(res.effective_date_time, "2026-11-17 08:00:00")
        self.assertEqual(res.effective_date_format, p278.DATE_FORMAT_DD_MM_YYYY)
        # Reset Network Set. still clears Network Location Info. Link
        self.assertEqual(res.effective_location_info_link, p278.TOGGLE_OFF)
        self.assertEqual(res.effective_auto_time_correction, p278.TOGGLE_OFF)

    def test_38_initialize_clears_area_datetime_and_triggers_reprompt(self) -> None:
        res = p278.simulate_area_datetime_and_zero_rf_hil(
            configured_area_setting="London",
            configured_daylight_savings=p278.TOGGLE_ON,
            configured_date_time="2026-11-17 12:00:00",
            configured_date_format=p278.DATE_FORMAT_DD_MM_YYYY,
            reset_action=p278.RESET_ACTION_INITIALIZE,
        )
        self.assertTrue(res.admitted)
        self.assertTrue(res.area_datetime_cleared_by_initialize)
        self.assertTrue(res.rtc_reprompt_required)
        self.assertEqual(res.effective_area_setting, p278.AREA_UNCONFIGURED)
        self.assertEqual(res.effective_daylight_savings, p278.TOGGLE_OFF)
        self.assertEqual(res.effective_date_format, p278.DATE_FORMAT_YYYY_MM_DD)

    def test_39_rtc_backup_battery_depletion_clears_and_reprompts(self) -> None:
        res = p278.simulate_area_datetime_and_zero_rf_hil(
            configured_area_setting="New York",
            configured_daylight_savings=p278.TOGGLE_ON,
            configured_date_time="2026-11-17 12:00:00",
            rtc_backup_battery_depleted=True,
        )
        self.assertTrue(res.admitted)
        self.assertTrue(res.rtc_backup_battery_depleted)
        self.assertTrue(res.rtc_reprompt_required)
        self.assertEqual(res.effective_area_setting, p278.AREA_UNCONFIGURED)
        self.assertEqual(res.effective_date_time, "2020-01-01 00:00:00")

    def test_40_all_3_date_formats_and_valid_areas_accepted(self) -> None:
        for fmt in p278.VALID_DATE_FORMATS:
            for area in ("UTC", "Tokyo", "Los Angeles", "Berlin"):
                r = p278.simulate_area_datetime_and_zero_rf_hil(
                    configured_area_setting=area,
                    configured_date_format=fmt,
                )
                self.assertTrue(r.admitted, msg=f"{area}:{fmt}")
                self.assertEqual(r.effective_area_setting, area)
                self.assertEqual(r.effective_date_format, fmt)
                self.assertFalse(r.rtc_reprompt_required)

    def test_41_zero_rf_airplane_mode_blocks_creators_app_across_h0_to_h3(self) -> None:
        for stage in p278.VALID_BENCH_STAGES:
            r = p278.simulate_area_datetime_and_zero_rf_hil(
                bench_stage=stage,
                airplane_mode=p278.TOGGLE_ON,
                configured_area_setting="UTC",
                configured_location_info_link=p278.TOGGLE_ON,
                configured_auto_time_correction=p278.TOGGLE_ON,
                configured_auto_area_adjustment=p278.TOGGLE_ON,
            )
            self.assertTrue(r.admitted, msg=stage)
            self.assertTrue(r.creators_app_sync_blocked_by_airplane_mode, msg=stage)
            self.assertEqual(r.effective_location_info_link, p278.TOGGLE_OFF, msg=stage)
            self.assertEqual(r.effective_auto_time_correction, p278.TOGGLE_OFF, msg=stage)
            self.assertEqual(r.effective_auto_area_adjustment, p278.TOGGLE_OFF, msg=stage)
            self.assertEqual(r.passive_tx_bytes_emitted, 0, msg=stage)
            self.assertEqual(r.creators_app_rtc_sync_jump_events, 0, msg=stage)
            self.assertTrue(r.h0_h3_rtc_monotonic_preserved, msg=stage)

    def test_42_forced_creators_app_sync_in_airplane_mode_blocked_eacces(self) -> None:
        r = p278.simulate_area_datetime_and_zero_rf_hil(
            airplane_mode=p278.TOGGLE_ON,
            configured_location_info_link=p278.TOGGLE_ON,
            configured_auto_time_correction=p278.TOGGLE_ON,
            force_creators_app_sync_during_airplane=True,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p278.EACCES_ERRNO)
        self.assertTrue(r.creators_app_sync_blocked_by_airplane_mode)
        self.assertEqual(r.passive_tx_bytes_emitted, 0)

    def test_43_forced_h0_h3_forensic_rtc_jump_blocked_eopnotsupp(self) -> None:
        r = p278.simulate_area_datetime_and_zero_rf_hil(
            bench_stage=p278.BENCH_STAGE_H2,
            airplane_mode=p278.TOGGLE_OFF,
            force_rtc_jump_during_h0_h3=True,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p278.EOPNOTSUPP_ERRNO)
        self.assertEqual(r.creators_app_rtc_sync_jump_events, 0)

    def test_44_auto_time_correction_requires_location_info_link_on(self) -> None:
        r_link_off = p278.simulate_area_datetime_and_zero_rf_hil(
            airplane_mode=p278.TOGGLE_OFF,
            configured_location_info_link=p278.TOGGLE_OFF,
            configured_auto_time_correction=p278.TOGGLE_ON,
            configured_auto_area_adjustment=p278.TOGGLE_ON,
        )
        self.assertEqual(r_link_off.effective_auto_time_correction, p278.TOGGLE_OFF)
        self.assertEqual(r_link_off.effective_auto_area_adjustment, p278.TOGGLE_OFF)

        r_link_on = p278.simulate_area_datetime_and_zero_rf_hil(
            airplane_mode=p278.TOGGLE_OFF,
            configured_location_info_link=p278.TOGGLE_ON,
            configured_auto_time_correction=p278.TOGGLE_ON,
            configured_auto_area_adjustment=p278.TOGGLE_ON,
        )
        self.assertEqual(r_link_on.effective_location_info_link, p278.TOGGLE_ON)
        self.assertEqual(r_link_on.effective_auto_time_correction, p278.TOGGLE_ON)
        self.assertEqual(r_link_on.effective_auto_area_adjustment, p278.TOGGLE_ON)

    def test_45_zero_rf_h0_h3_matrix_has_all_4_stages(self) -> None:
        pb = self.clean_audit["pillar_b_area_datetime_and_zero_rf_hil"]
        self.assertEqual(set(pb["zero_rf_h0_h3_isolation_matrix"].keys()), {"H0", "H1", "H2", "H3"})

    def test_46_pillar_b_summary_passed_and_zero_writes(self) -> None:
        pb = self.clean_audit["pillar_b_area_datetime_and_zero_rf_hil"]
        self.assertTrue(pb["passed"])
        self.assertEqual(pb["exact_official_title"], "Area/Date/Time Setting")
        self.assertEqual(pb["initial_unconfigured_ok"]["physical_device_writes"], 0)
        self.assertEqual(pb["initial_unconfigured_ok"]["bk4_persistent_nvram_writes"], 0)

    # ------------------------------------------------------------------
    # Group 4: Sub-Model 55C — [Video Light Mode] & [HDMI Resolution] (16 tests)
    # ------------------------------------------------------------------
    def test_47_video_light_and_hdmi_resolution_factory_defaults(self) -> None:
        res = p278.simulate_video_light_and_hdmi_res_hil()
        self.assertTrue(res.admitted)
        self.assertEqual(res.video_light_menu_path, p278.VIDEO_LIGHT_MODE_MENU_PATH)
        self.assertEqual(res.hdmi_res_menu_path, p278.HDMI_RESOLUTION_MENU_PATH)
        self.assertEqual(res.effective_video_light_mode, p278.VIDEO_LIGHT_POWER_LINK)
        self.assertEqual(res.effective_hdmi_menu_setting, p278.HDMI_RES_AUTO)
        self.assertEqual(res.effective_hdmi_resolution, p278.HDMI_RES_2160P)
        self.assertTrue(res.video_light_active)
        self.assertFalse(res.hdmi_log_1080p_downshift_active)

    def test_48_video_light_power_link_turns_on_in_power_on_stby_rec_and_off_power_off(self) -> None:
        for state in (
            p278.CAMERA_STATE_POWER_ON,
            p278.CAMERA_STATE_STBY,
            p278.CAMERA_STATE_REC,
        ):
            r = p278.simulate_video_light_and_hdmi_res_hil(
                configured_video_light_mode=p278.VIDEO_LIGHT_POWER_LINK,
                camera_state=state,
            )
            self.assertTrue(r.video_light_active, msg=state)

        r_off = p278.simulate_video_light_and_hdmi_res_hil(
            configured_video_light_mode=p278.VIDEO_LIGHT_POWER_LINK,
            camera_state=p278.CAMERA_STATE_POWER_OFF,
        )
        self.assertFalse(r_off.video_light_active)

    def test_49_video_light_rec_link_and_rec_link_stby_state_machines(self) -> None:
        r_rec_stby = p278.simulate_video_light_and_hdmi_res_hil(
            configured_video_light_mode=p278.VIDEO_LIGHT_REC_LINK,
            camera_state=p278.CAMERA_STATE_STBY,
        )
        self.assertFalse(r_rec_stby.video_light_active)

        r_rec_rec = p278.simulate_video_light_and_hdmi_res_hil(
            configured_video_light_mode=p278.VIDEO_LIGHT_REC_LINK,
            camera_state=p278.CAMERA_STATE_REC,
        )
        self.assertTrue(r_rec_rec.video_light_active)

        r_rs_pon = p278.simulate_video_light_and_hdmi_res_hil(
            configured_video_light_mode=p278.VIDEO_LIGHT_REC_LINK_STBY,
            camera_state=p278.CAMERA_STATE_POWER_ON,
        )
        r_rs_stby = p278.simulate_video_light_and_hdmi_res_hil(
            configured_video_light_mode=p278.VIDEO_LIGHT_REC_LINK_STBY,
            camera_state=p278.CAMERA_STATE_STBY,
        )
        self.assertFalse(r_rs_pon.video_light_active)
        self.assertTrue(r_rs_stby.video_light_active)

    def test_50_video_light_auto_mode_responds_to_low_light_only(self) -> None:
        bright = p278.simulate_video_light_and_hdmi_res_hil(
            configured_video_light_mode=p278.VIDEO_LIGHT_AUTO,
            camera_state=p278.CAMERA_STATE_REC,
            low_light_scene=False,
        )
        dark = p278.simulate_video_light_and_hdmi_res_hil(
            configured_video_light_mode=p278.VIDEO_LIGHT_AUTO,
            camera_state=p278.CAMERA_STATE_REC,
            low_light_scene=True,
        )
        self.assertFalse(bright.video_light_active)
        self.assertTrue(dark.video_light_active)

    def test_51_mishoe_5v_900ma_rail_budget_admitted_up_to_900ma_and_locked_above(self) -> None:
        ok_900 = p278.simulate_video_light_and_hdmi_res_hil(
            mishoe_video_light_attached=True,
            mishoe_load_ma=900,
        )
        self.assertTrue(ok_900.admitted)
        self.assertFalse(ok_900.mishoe_rail_overcurrent_tripped)
        self.assertEqual(ok_900.mishoe_rail_voltage_mv, 5000)

        oc_901 = p278.simulate_video_light_and_hdmi_res_hil(
            mishoe_video_light_attached=True,
            mishoe_load_ma=901,
        )
        self.assertFalse(oc_901.admitted)
        self.assertEqual(oc_901.errno_code, p278.EACCES_ERRNO)
        self.assertTrue(oc_901.mishoe_rail_overcurrent_tripped)
        self.assertEqual(oc_901.reason_code, "MISHOE_5V_900MA_RAIL_OVERCURRENT_LOCKOUT")
        self.assertEqual(oc_901.mishoe_5v_900ma_overcurrent_events, 0)

    def test_52_mishoe_unattached_ignores_light_activation_and_load(self) -> None:
        res = p278.simulate_video_light_and_hdmi_res_hil(
            mishoe_video_light_attached=False,
            mishoe_load_ma=0,
        )
        self.assertTrue(res.admitted)
        self.assertFalse(res.video_light_active)
        self.assertEqual(res.mishoe_load_ma, 0)

    def test_53_hdmi_resolution_all_4_options_and_edid_auto_negotiation(self) -> None:
        for sink_max in (p278.HDMI_RES_2160P, p278.HDMI_RES_1080P, p278.HDMI_RES_1080I):
            r_auto = p278.simulate_video_light_and_hdmi_res_hil(
                configured_hdmi_resolution=p278.HDMI_RES_AUTO,
                edid_sink_max_resolution=sink_max,
            )
            self.assertEqual(r_auto.effective_hdmi_menu_setting, p278.HDMI_RES_AUTO)
            self.assertEqual(r_auto.effective_hdmi_resolution, sink_max)

        for explicit in (p278.HDMI_RES_2160P, p278.HDMI_RES_1080P, p278.HDMI_RES_1080I):
            r_exp = p278.simulate_video_light_and_hdmi_res_hil(
                configured_hdmi_resolution=explicit,
                edid_sink_max_resolution=p278.HDMI_RES_2160P,
            )
            self.assertEqual(r_exp.effective_hdmi_menu_setting, explicit)
            self.assertEqual(r_exp.effective_hdmi_resolution, explicit)

    def test_54_log_shooting_internal_recording_forces_1080p_downshift(self) -> None:
        for log_mode in (
            p278.LOG_SHOOTING_CINE_EI,
            p278.LOG_SHOOTING_CINE_EI_QUICK,
            p278.LOG_SHOOTING_FLEXIBLE_ISO,
        ):
            r = p278.simulate_video_light_and_hdmi_res_hil(
                log_shooting=log_mode,
                internal_recording_active=True,
                rec_media_dur_hdmi_output=p278.REC_MEDIA_DUR_HDMI_ON,
                configured_hdmi_resolution=p278.HDMI_RES_2160P,
            )
            self.assertTrue(r.admitted, msg=log_mode)
            self.assertTrue(r.hdmi_log_1080p_downshift_active, msg=log_mode)
            self.assertEqual(r.effective_hdmi_resolution, p278.HDMI_RES_1080P, msg=log_mode)

    def test_55_rec_media_dur_hdmi_off_hdmi_only_preserves_2160p_in_log(self) -> None:
        for log_mode in (
            p278.LOG_SHOOTING_CINE_EI,
            p278.LOG_SHOOTING_CINE_EI_QUICK,
            p278.LOG_SHOOTING_FLEXIBLE_ISO,
        ):
            r = p278.simulate_video_light_and_hdmi_res_hil(
                log_shooting=log_mode,
                internal_recording_active=True,
                rec_media_dur_hdmi_output=p278.REC_MEDIA_DUR_HDMI_OFF_HDMI_ONLY,
                configured_hdmi_resolution=p278.HDMI_RES_2160P,
            )
            self.assertTrue(r.admitted, msg=log_mode)
            self.assertFalse(r.hdmi_log_1080p_downshift_active, msg=log_mode)
            self.assertEqual(r.effective_hdmi_resolution, p278.HDMI_RES_2160P, msg=log_mode)

    def test_56_log_shooting_standby_without_internal_recording_preserves_2160p(self) -> None:
        r = p278.simulate_video_light_and_hdmi_res_hil(
            camera_state=p278.CAMERA_STATE_STBY,
            log_shooting=p278.LOG_SHOOTING_CINE_EI,
            internal_recording_active=False,
            rec_media_dur_hdmi_output=p278.REC_MEDIA_DUR_HDMI_ON,
            configured_hdmi_resolution=p278.HDMI_RES_2160P,
        )
        self.assertTrue(r.admitted)
        self.assertFalse(r.hdmi_log_1080p_downshift_active)
        self.assertEqual(r.effective_hdmi_resolution, p278.HDMI_RES_2160P)

    def test_57_forced_bypass_of_log_1080p_downshift_blocked_eopnotsupp(self) -> None:
        r = p278.simulate_video_light_and_hdmi_res_hil(
            log_shooting=p278.LOG_SHOOTING_FLEXIBLE_ISO,
            internal_recording_active=True,
            rec_media_dur_hdmi_output=p278.REC_MEDIA_DUR_HDMI_ON,
            configured_hdmi_resolution=p278.HDMI_RES_2160P,
            force_bypass_log_1080p_downshift=True,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p278.EOPNOTSUPP_ERRNO)
        self.assertEqual(r.hdmi_log_1080p_downshift_bypass_events, 0)

    def test_58_video_light_and_hdmi_res_survive_camera_settings_reset(self) -> None:
        for act in (p278.RESET_ACTION_CAMERA_SETTINGS_RESET, p278.RESET_ACTION_RESET_NETWORK_SET):
            r = p278.simulate_video_light_and_hdmi_res_hil(
                configured_video_light_mode=p278.VIDEO_LIGHT_REC_LINK_STBY,
                configured_hdmi_resolution=p278.HDMI_RES_1080I,
                reset_action=act,
            )
            self.assertTrue(r.admitted, msg=act)
            self.assertTrue(r.setup_items_survived_camera_reset, msg=act)
            self.assertFalse(r.setup_items_restored_by_initialize, msg=act)
            self.assertEqual(r.effective_video_light_mode, p278.VIDEO_LIGHT_REC_LINK_STBY)
            self.assertEqual(r.effective_hdmi_menu_setting, p278.HDMI_RES_1080I)
            self.assertEqual(r.effective_hdmi_resolution, p278.HDMI_RES_1080I)

    def test_59_initialize_restores_video_light_power_link_and_hdmi_auto(self) -> None:
        r = p278.simulate_video_light_and_hdmi_res_hil(
            configured_video_light_mode=p278.VIDEO_LIGHT_AUTO,
            configured_hdmi_resolution=p278.HDMI_RES_1080I,
            edid_sink_max_resolution=p278.HDMI_RES_2160P,
            reset_action=p278.RESET_ACTION_INITIALIZE,
        )
        self.assertTrue(r.admitted)
        self.assertTrue(r.setup_items_restored_by_initialize)
        self.assertFalse(r.setup_items_survived_camera_reset)
        self.assertEqual(r.effective_video_light_mode, p278.VIDEO_LIGHT_POWER_LINK)
        self.assertEqual(r.effective_hdmi_menu_setting, p278.HDMI_RES_AUTO)
        self.assertEqual(r.effective_hdmi_resolution, p278.HDMI_RES_2160P)

    def test_60_invalid_video_light_or_hdmi_parameter_rejected_einval(self) -> None:
        for kwargs in (
            {"camera_state": "SLEEP"},
            {"mishoe_load_ma": -1},
            {"log_shooting": "S-Log2"},
            {"rec_media_dur_hdmi_output": "HDMI_ONLY_OLD"},
            {"edid_sink_max_resolution": "Auto"},
            {"configured_video_light_mode": "Strobe"},
            {"configured_hdmi_resolution": "480p"},
        ):
            r = p278.simulate_video_light_and_hdmi_res_hil(**kwargs)
            self.assertFalse(r.admitted, msg=str(kwargs))
            self.assertEqual(r.errno_code, p278.EINVAL_ERRNO, msg=str(kwargs))

    def test_61_video_light_4mode_matrix_covers_all_4_modes(self) -> None:
        pcd = self.clean_audit["pillar_c_d_video_light_hdmi_res_and_redlines"]
        self.assertEqual(
            set(pcd["video_light_4mode_matrix"].keys()),
            {"Power Link", "REC Link", "REC Link & STBY", "Auto"},
        )

    def test_62_pillar_cd_passed_flag_and_zero_writes(self) -> None:
        pcd = self.clean_audit["pillar_c_d_video_light_hdmi_res_and_redlines"]
        self.assertTrue(pcd["passed"])
        self.assertEqual(pcd["mishoe_5v_rail_limit_ma"], 900)

    # ------------------------------------------------------------------
    # Group 5: 16 Redline Probes, Stage 55 (55/55) Suite & Subprocess Hygiene (10 tests)
    # ------------------------------------------------------------------
    def test_63_all_16_redline_probes_fail_closed_and_unknown_probe_einval(self) -> None:
        self.assertEqual(len(p278.ALL_16_REDLINE_PROBE_FIELDS), 16)
        base = p278.probe_phase278_redline_guard()
        self.assertTrue(base.valid)
        self.assertEqual(base.errno_code, 0)
        for field in p278.ALL_16_REDLINE_PROBE_FIELDS:
            blocked = p278.probe_phase278_redline_guard(**{field: True})
            self.assertFalse(blocked.valid, msg=field)
            self.assertGreater(blocked.errno_code, 0, msg=field)
            self.assertEqual(blocked.physical_device_writes, 0)
            self.assertEqual(blocked.emmc_corruptions, 0)
            self.assertEqual(blocked.raw_firmware_bytes_leaked, 0)
        bad = p278.probe_phase278_redline_guard(unknown_probe_xyz=True)
        self.assertFalse(bad.valid)
        self.assertEqual(bad.errno_code, p278.EINVAL_ERRNO)

    def test_64_standalone_cli_self_test_summary_and_json_via_sys_executable(self) -> None:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env[p278.ENV_CLEAN_ROOM_TEST] = "1"
        script = str(FX3_VM_DIR / "realhw_focus_mag_datetime_videolight_hdmires_coemulator.py")

        proc_sum = subprocess.run(
            [sys.executable, "-B", script, "--self-test", "--summary"],
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertIn("[PASS] Phase 278 Stage 55 (55/55)", proc_sum.stdout)
        self.assertIn("mode=CLEAN_ROOM_SYNTHETIC", proc_sum.stdout)

        proc_json = subprocess.run(
            [sys.executable, "-B", script, "--self-test", "--json"],
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        data = json.loads(proc_json.stdout)
        self.assertTrue(data["all_checks_passed"])
        self.assertEqual(data["milestone"], "55/55")
        self.assertEqual(data["phase_number"], 278)

    def test_65_suite_stage55_55_of_55_auto_discovered_and_all_stages_pass(self) -> None:
        for rep in (self.default_suite, self.clean_suite):
            self.assertTrue(rep["all_checks_passed"])
            s55 = rep["stage55_realhw_focus_mag_datetime_videolight_hdmires_hil"]
            self.assertTrue(s55["all_checks_passed"])
            self.assertEqual(s55["phase_number"], 278)
            self.assertEqual(s55["milestone"], "55/55")
            stage_keys = [
                k for k in rep if re.match(r"^stage\d+_", k) and isinstance(rep[k], dict)
            ]
            if rep is self.default_suite:
                self.assertGreaterEqual(len(stage_keys), 55)

    def test_66_suite_default_and_clean_room_runtime_within_budget(self) -> None:
        max_default_s = 15.0 if IS_CI else 5.0
        max_clean_s = 10.0 if IS_CI else 3.0
        self.assertLess(self.default_suite_elapsed, max_default_s)
        self.assertLess(self.clean_suite_elapsed, max_clean_s)

    def test_67_suite_deterministic_digest_in_clean_room_mode(self) -> None:
        rep_a = suite.run_fx3_vm_coemulation_suite(
            suite.CoEmulationConfig(**_fast_suite_kwargs(force_clean_room=True))
        )
        rep_b = suite.run_fx3_vm_coemulation_suite(
            suite.CoEmulationConfig(**_fast_suite_kwargs(force_clean_room=True))
        )
        self.assertEqual(rep_a["audit_digest_sha256"], rep_b["audit_digest_sha256"])

    def test_68_suite_stage55_config_defaults_and_skip_overrides(self) -> None:
        default_cfg = suite.CoEmulationConfig()
        self.assertTrue(default_cfg.stage55_realhw_focus_mag_datetime_videolight_hdmires_hil)
        self.assertTrue(default_cfg.include_stage55)
        self.assertTrue(
            default_cfg.include_phase278_realhw_focus_mag_datetime_videolight_hdmires_hil
        )

        for override in (
            {"stage55_realhw_focus_mag_datetime_videolight_hdmires_hil": False},
            {"include_stage55": False},
            {"include_phase278_realhw_focus_mag_datetime_videolight_hdmires_hil": False},
        ):
            rep = suite.run_fx3_vm_coemulation_suite(
                suite.CoEmulationConfig(**_fast_suite_kwargs(**override))
            )
            self.assertTrue(rep["all_checks_passed"])
            self.assertNotIn(
                "stage55_realhw_focus_mag_datetime_videolight_hdmires_hil", rep
            )
            self.assertFalse(rep["config"]["include_stage55"])
            self.assertFalse(
                rep["config"]["stage55_realhw_focus_mag_datetime_videolight_hdmires_hil"]
            )

    def test_69_fx3_vm_coemulation_suite_include_stage55_cli_summary(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = suite.main(_FAST_CLI_FLAGS + ["--include-stage55", "--summary"])
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("[PASS] Phase 33 FX3-VM Co-Emulation", out)
        self.assertIn(
            "realhw_focus_mag_datetime_videolight_hdmires_hil=CLEAN_ROOM_SYNTHETIC",
            out,
        )

    def test_70_fx3_vm_coemulation_suite_cli_skip_phase278_and_skip_stage55(self) -> None:
        for skip_flag in ("--skip-phase278", "--skip-stage55", "--no-include-stage55"):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = suite.main(_FAST_CLI_FLAGS + [skip_flag, "--json"])
            self.assertEqual(rc, 0)
            parsed = json.loads(buf.getvalue())
            self.assertTrue(parsed["all_checks_passed"])
            self.assertNotIn(
                "stage55_realhw_focus_mag_datetime_videolight_hdmires_hil", parsed
            )

    def test_71_all_safety_and_byof_redlines_locked_across_stage55_and_suite(self) -> None:
        for rep in (self.clean_audit, self.default_audit):
            red = rep["redlines"]
            self.assertFalse(red["persistent_emmc_writes_authorized"])
            self.assertFalse(red["hardware_live_attachment_authorized"])
            self.assertFalse(red["overall_ready_for_hardware_attach"])
            self.assertFalse(red["isp_write_authorized"])
            self.assertFalse(red["spi_nor_write_authorized"])
            self.assertFalse(red["el3_payload_transmit_authorized"])
            self.assertTrue(red["cnflasha_userspace_write_blocked"])
            self.assertEqual(red["legacy_mf_assist_spoof_events"], 0)
            self.assertEqual(red["hdmi_clean_feed_mag_or_peaking_leaked_pixels"], 0)
            self.assertEqual(red["af_illuminator_movie_or_sq_fire_events"], 0)
            self.assertEqual(red["legacy_date_time_setup_spoof_events"], 0)
            self.assertEqual(red["passive_tx_bytes_emitted"], 0)
            self.assertEqual(red["creators_app_rtc_sync_jump_events"], 0)
            self.assertEqual(red["mishoe_5v_900ma_overcurrent_events"], 0)
            self.assertEqual(red["hdmi_log_1080p_downshift_bypass_events"], 0)
            self.assertEqual(red["physical_device_writes"], 0)
            self.assertEqual(red["emmc_corruptions"], 0)
            self.assertEqual(red["nop_count"], 0)
            self.assertEqual(red["guest_code_modification_bytes"], 0)
            self.assertEqual(red["raw_firmware_bytes_leaked"], 0)

    def test_72_no_pyc_bytecode_files_emitted_under_fx3_vm(self) -> None:
        pyc_files = list(FX3_VM_DIR.rglob("*.pyc"))
        self.assertEqual(pyc_files, [])


if __name__ == "__main__":
    unittest.main()
