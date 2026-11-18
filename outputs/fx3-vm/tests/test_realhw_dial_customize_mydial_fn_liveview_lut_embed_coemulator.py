#!/usr/bin/env python3
"""Unit tests for Phase 318 (Stage 66 — 66/66 Milestone):
Real-Hardware `ILME-FX3 Ver. 7.02` vs `ILME-FX6 Ver. 6.01` Wave-56:
5-Item `[Dial Customize]` (`Initialize`-Only) & Ver. 2.00+ Menu Evolution vs `FX6` Hardware Dials,
3-Physical-Dial Topology (`Rear Dial L/R` Ban), `My Dial 1..3` Lock-Override &
`12 Still + 12 Movie` `[Fn Menu Settings]`,
3-Item `[Live View Display Set.]` (Still-Only) & `[Grid Line]` Clean-HDMI Isolation,
and `[Manage User LUTs]` (`User1..16`) vs `[Embed LUT File]` (`Log Shooting Setting` SD/SDHC Lock)
vs `PPLUT1..4` Pixel-Baking + `Slot-1` Tier-0 Vault Firewall HIL Co-Emulator
(90 dual-mode tests).
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
import realhw_dial_customize_mydial_fn_liveview_lut_embed_coemulator as p318  # noqa: E402

IS_CI = os.environ.get("GITHUB_ACTIONS", "").lower() == "true"


def _fast_suite_kwargs(**overrides: object) -> dict:
    """Fast config skipping unrelated optional stages 4..65 for quick Stage 66 isolation tests."""
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
        include_stage65=False,
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
    "--skip-stage65",
]


class TestPhase318DonorInspection(unittest.TestCase):
    """Dual-mode 17-donor O_RDONLY & CLEAN_ROOM_SYNTHETIC verification (tests 01..12)."""

    def test_01_schema_and_milestone_constants(self) -> None:
        self.assertEqual(
            p318.SCHEMA_ID,
            "realhw_dial_customize_mydial_fn_liveview_lut_embed_coemulator_v1",
        )
        self.assertEqual(p318.PHASE_NUMBER, 318)
        self.assertEqual(p318.STAGE_INDEX, 66)
        self.assertEqual(p318.STAGE_TOTAL, 66)
        self.assertEqual(p318.MILESTONE_LABEL, "66/66")
        self.assertTrue(p318.IS_66TH_STAGE_MILESTONE)
        self.assertEqual(p318.DONOR_ACCESS_MODE, "O_RDONLY")
        self.assertEqual(p318.BOUNDED_WINDOW_MAX_BYTES, 4096)
        self.assertEqual(len(p318.DONOR_RELPATHS), 17)

    def test_02_donor_audit_current_mode_17_donors(self) -> None:
        audit = p318.inspect_phase318_donors()
        self.assertTrue(audit.all_contracts_verified)
        self.assertEqual(audit.donor_files_inspected, 17)
        self.assertEqual(audit.access_mode, "O_RDONLY")
        self.assertIn(
            audit.source_mode,
            (p318.SOURCE_MODE_LOCAL_DONOR, p318.SOURCE_MODE_CLEAN_ROOM),
        )
        for entry in audit.entries:
            self.assertEqual(
                entry.read_only_checked,
                audit.source_mode == p318.SOURCE_MODE_LOCAL_DONOR,
                entry.donor_key,
            )
            self.assertTrue(entry.passed, entry.donor_key)

    def test_03_clean_room_via_fx3_fx6_force_clean_room_env(self) -> None:
        audit = p318.inspect_phase318_donors(env={p318.ENV_FORCE_CLEAN_ROOM: "1"})
        self.assertEqual(audit.source_mode, p318.SOURCE_MODE_CLEAN_ROOM)
        self.assertTrue(audit.all_contracts_verified)
        self.assertEqual(audit.donor_files_inspected, 17)
        self.assertEqual(audit.inspection_elapsed_ms, 0.0)

    def test_04_clean_room_via_fx3_clean_room_test_env(self) -> None:
        audit = p318.inspect_phase318_donors(env={p318.ENV_CLEAN_ROOM_TEST: "1"})
        self.assertEqual(audit.source_mode, p318.SOURCE_MODE_CLEAN_ROOM)
        self.assertTrue(audit.all_contracts_verified)
        self.assertEqual(audit.donor_files_inspected, 17)
        self.assertEqual(audit.inspection_elapsed_ms, 0.0)

    def test_05_clean_room_parity_between_both_env_vars(self) -> None:
        a1 = p318.inspect_phase318_donors(env={p318.ENV_FORCE_CLEAN_ROOM: "1"})
        a2 = p318.inspect_phase318_donors(env={p318.ENV_CLEAN_ROOM_TEST: "1"})
        self.assertEqual(a1, a2)

    def test_06_clean_room_fallback_when_mac_root_missing(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            audit = p318.inspect_phase318_donors(
                env={p318.ENV_MAC_ROOT: str(Path(td) / "nonexistent_mac")}
            )
            self.assertEqual(audit.source_mode, p318.SOURCE_MODE_CLEAN_ROOM)
            self.assertTrue(audit.all_contracts_verified)
            self.assertEqual(audit.donor_files_inspected, 17)

    def test_07_bounded_4096_windows_strict_bound(self) -> None:
        for donor_key, windows in p318.LARGE_DONOR_WINDOWS.items():
            self.assertGreaterEqual(len(windows), 2, donor_key)
            for _off, name, needle in windows:
                self.assertLessEqual(len(needle), 4096, f"{donor_key}:{name}")

    def test_08_all_17_expected_byte_sizes_and_hashes_present(self) -> None:
        self.assertEqual(set(p318.DONOR_RELPATHS), set(p318.EXPECTED_DONOR_BYTES))
        self.assertEqual(
            set(p318.EXPECTED_COMPACT_DONOR_SHA256)
            | set(p318.EXPECTED_LARGE_HEAD4K_SHA256),
            set(p318.DONOR_RELPATHS),
        )

    def test_09_fx3_uxc_f_and_g_tokens_verified_across_4_languages(self) -> None:
        audit = p318.inspect_phase318_donors()
        by_key = {e.donor_key: e for e in audit.entries}
        self.assertIn("Custom Key/Dial Set.", by_key["fx3_string_en_f"].tokens_verified)
        self.assertIn("自定义键设置", by_key["fx3_string_sc_f"].tokens_verified)
        self.assertIn("自訂鍵/轉盤設定", by_key["fx3_string_tc_f"].tokens_verified)
        self.assertIn("ｶｽﾀﾑｷｰ/ﾀﾞｲﾔﾙ設定", by_key["fx3_string_ja_f"].tokens_verified)
        self.assertIn("Dial Customize", by_key["fx3_string_en_g"].tokens_verified)
        self.assertIn("转盘自定义", by_key["fx3_string_sc_g"].tokens_verified)
        self.assertIn("轉盤客製化", by_key["fx3_string_tc_g"].tokens_verified)
        self.assertIn("ﾀﾞｲﾔﾙｶｽﾀﾏｲｽﾞ", by_key["fx3_string_ja_g"].tokens_verified)

    def test_10_fx3_base_uxc_3dial_tokens_verified_4_languages(self) -> None:
        audit = p318.inspect_phase318_donors()
        by_key = {e.donor_key: e for e in audit.entries}
        self.assertIn("Control Wheel", by_key["fx3_string_en"].tokens_verified)
        self.assertIn("控制拨轮", by_key["fx3_string_sc"].tokens_verified)
        self.assertIn("控制滾輪", by_key["fx3_string_tc"].tokens_verified)
        self.assertIn("コントロールホイール", by_key["fx3_string_ja"].tokens_verified)

    def test_11_fx3_appfw_and_bk4_tokens_verified(self) -> None:
        audit = p318.inspect_phase318_donors()
        by_key = {e.donor_key: e for e in audit.entries}
        fx3_tokens = by_key["fx3_appfw"].tokens_verified
        for tok in (
            "ELF64",
            "DORMANT_DIAL_LEFT_SHUTTER",
            "SD_PRO_LUT_PATH",
            "CF_PRO_LUT_PATH",
            "FUNC_RING_INVALID",
            "MYDIAL_RECALL_STATE_1_HOLD",
            "BKID_EMBED_LUT_FILE",
            "BKID_GRID_LINE_DISP",
            "BKID_LIVE_VIEW_DISP",
            "BKID_FN_STILL0",
            "BKID_FN_MOVIE0",
            "DORMANT_MYDIAL_REAR_L",
            "DORMANT_MYDIAL_REAR_R",
            "BKID_PPLUT1_LINK",
            "EMBEDDED_LUT_PB",
        ):
            self.assertIn(tok, fx3_tokens)
        self.assertEqual(by_key["fx3_bk4"].tokens_verified, ("BK4", "ILME_FX3"))

    def test_12_fx6_donors_verified(self) -> None:
        audit = p318.inspect_phase318_donors()
        by_key = {e.donor_key: e for e in audit.entries}
        self.assertIn("Multi Function Dial", by_key["fx6_string_en"].tokens_verified)
        self.assertIn("ND Dial", by_key["fx6_string_en_2"].tokens_verified)
        self.assertIn("BKID_FX6_MFD", by_key["fx6_appfw"].tokens_verified)
        self.assertIn("DORMANT_CUSTOM_GRID_0", by_key["fx6_appfw"].tokens_verified)


class TestSubModel66ADialCustomize5ItemAndFx6Dials(unittest.TestCase):
    """66A: Exact 5-item [Dial Customize] (Initialize-Only) & Ver. 2.00+ Evolution vs FX6 (tests 13..25)."""

    def test_13_exact_5_dial_customize_items_exposed(self) -> None:
        r = p318.simulate_dial_customize_5item_and_fx6_dials_hil()
        self.assertTrue(r.admitted)
        self.assertEqual(r.exposed_item_count, 5)
        self.assertEqual(
            r.exposed_dial_customize_items,
            (
                "Custom Key/Dial Set.",
                "My Dial Settings",
                "Av/Tv Rotate",
                "Function Ring(Lens)",
                "Lock Operation Parts",
            ),
        )

    def test_14_ver1_dormant_dial_setup_symbols_rejected_eopnotsupp(self) -> None:
        for sym in p318.DORMANT_DIAL_SETUP_SYMBOLS:
            r = p318.simulate_dial_customize_5item_and_fx6_dials_hil(
                requested_dormant_dial_symbol=sym
            )
            self.assertFalse(r.admitted, sym)
            self.assertEqual(r.errno_code, p318.EOPNOTSUPP_ERRNO, sym)
            self.assertTrue(r.dormant_dial_setup_blocked, sym)

    def test_15_av_tv_rotate_normal_and_reverse_only_affect_av_tv_dials(self) -> None:
        r_rev = p318.simulate_dial_customize_5item_and_fx6_dials_hil(
            av_tv_rotate=p318.AV_TV_ROTATE_REVERSE,
            dial_mapped_to_av_or_tv=True,
        )
        self.assertTrue(r_rev.admitted)
        self.assertEqual(r_rev.effective_av_tv_rotate, p318.AV_TV_ROTATE_REVERSE)
        self.assertTrue(r_rev.av_tv_rotate_affects_dial)

        r_iso = p318.simulate_dial_customize_5item_and_fx6_dials_hil(
            av_tv_rotate=p318.AV_TV_ROTATE_REVERSE,
            dial_mapped_to_av_or_tv=False,
        )
        self.assertTrue(r_iso.admitted)
        self.assertFalse(r_iso.av_tv_rotate_affects_dial)

    def test_16_function_ring_valid_modes_and_lens_switch_coupling(self) -> None:
        r_pf = p318.simulate_dial_customize_5item_and_fx6_dials_hil(
            function_ring_mode=p318.FUNC_RING_POWER_FOCUS,
            lens_switch_on_function=True,
        )
        self.assertTrue(r_pf.admitted)
        self.assertEqual(r_pf.effective_function_ring_mode, p318.FUNC_RING_POWER_FOCUS)
        self.assertTrue(r_pf.lens_function_switch_required)

        r_apsc = p318.simulate_dial_customize_5item_and_fx6_dials_hil(
            function_ring_mode=p318.FUNC_RING_APSC_S35_FF,
            lens_switch_on_function=False,
        )
        self.assertTrue(r_apsc.admitted)
        self.assertEqual(r_apsc.effective_function_ring_mode, p318.FUNC_RING_APSC_S35_FF)

    def test_17_function_ring_invalid_rejected_einval(self) -> None:
        r = p318.simulate_dial_customize_5item_and_fx6_dials_hil(
            function_ring_mode="FUNCTION_RING_INVALID"
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p318.EINVAL_ERRNO)
        self.assertEqual(r.reason_code, "INVALID_FUNCTION_RING_MODE")

    def test_18_lock_operation_parts_all_4_modes(self) -> None:
        self.assertEqual(
            p318.VALID_FX3_LOCK_OP_PARTS_MODES,
            ("Off", "Multi-Selector Only", "Dial + Wheel", "All"),
        )
        for mode in p318.VALID_FX3_LOCK_OP_PARTS_MODES:
            r = p318.simulate_dial_customize_5item_and_fx6_dials_hil(
                lock_operation_parts=mode,
                fn_long_press_toggled=True,
            )
            self.assertTrue(r.admitted, mode)
            self.assertEqual(r.effective_lock_operation_parts, mode, mode)
            if mode == p318.LOCK_OP_OFF:
                self.assertFalse(r.fn_long_press_locked, mode)
            else:
                self.assertTrue(r.fn_long_press_locked, mode)

    def test_19_menu_plus_fn_5s_chord_locks_operation_parts(self) -> None:
        r = p318.simulate_dial_customize_5item_and_fx6_dials_hil(
            lock_operation_parts=p318.LOCK_OP_ALL,
            menu_fn_5s_chord_pressed=True,
        )
        self.assertTrue(r.admitted)
        self.assertTrue(r.menu_fn_5s_chord_locked)

        r_off = p318.simulate_dial_customize_5item_and_fx6_dials_hil(
            lock_operation_parts=p318.LOCK_OP_OFF,
            menu_fn_5s_chord_pressed=True,
        )
        self.assertTrue(r_off.admitted)
        self.assertFalse(r_off.menu_fn_5s_chord_locked)

    def test_20_all_5_dial_customize_items_survive_camera_settings_reset(self) -> None:
        r = p318.simulate_dial_customize_5item_and_fx6_dials_hil(
            av_tv_rotate=p318.AV_TV_ROTATE_REVERSE,
            function_ring_mode=p318.FUNC_RING_APSC_S35_FF,
            lock_operation_parts=p318.LOCK_OP_DIAL_WHEEL,
            fn_long_press_toggled=True,
            menu_fn_5s_chord_pressed=True,
            camera_settings_reset_applied=True,
        )
        self.assertTrue(r.admitted)
        self.assertTrue(r.all_5_survived_cam_reset)
        self.assertTrue(r.reset_via_initialize_only)
        self.assertEqual(r.effective_av_tv_rotate, p318.AV_TV_ROTATE_REVERSE)
        self.assertEqual(r.effective_function_ring_mode, p318.FUNC_RING_APSC_S35_FF)
        self.assertEqual(r.effective_lock_operation_parts, p318.LOCK_OP_DIAL_WHEEL)
        self.assertTrue(r.fn_long_press_locked)

    def test_21_initialize_resets_all_5_dial_customize_items_to_factory_defaults(self) -> None:
        r = p318.simulate_dial_customize_5item_and_fx6_dials_hil(
            av_tv_rotate=p318.AV_TV_ROTATE_REVERSE,
            function_ring_mode=p318.FUNC_RING_APSC_S35_FF,
            lock_operation_parts=p318.LOCK_OP_ALL,
            fn_long_press_toggled=True,
            menu_fn_5s_chord_pressed=True,
            initialize_applied=True,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.effective_av_tv_rotate, p318.AV_TV_ROTATE_NORMAL)
        self.assertEqual(r.effective_function_ring_mode, p318.FUNC_RING_POWER_FOCUS)
        self.assertEqual(r.effective_lock_operation_parts, p318.LOCK_OP_OFF)
        self.assertFalse(r.fn_long_press_locked)
        self.assertFalse(r.menu_fn_5s_chord_locked)

    def test_22_fx6_hardware_5_dials_and_mfd_options(self) -> None:
        self.assertEqual(
            p318.FX6_HARDWARE_DIALS,
            ("Multi Function Dial", "Grip Dial", "Handle Dial", "IRIS Dial", "ND Dial"),
        )
        for mfd_fn in p318.VALID_FX6_MFD_DEFAULT_FUNCTIONS:
            r = p318.simulate_dial_customize_5item_and_fx6_dials_hil(
                body_profile=p318.BODY_MODEL_FX6,
                fx6_mfd_default_function=mfd_fn,
                fx6_physical_hold_switch=True,
            )
            self.assertTrue(r.admitted, mfd_fn)
            self.assertEqual(r.fx6_mfd_default_function, mfd_fn, mfd_fn)
            self.assertTrue(r.fx6_physical_hold_switch_engaged)
            self.assertEqual(r.exposed_item_count, 0)

    def test_23_fx6_rejects_fx3_av_tv_rotate_reverse_and_fn_long_press_eopnotsupp(self) -> None:
        r_av = p318.simulate_dial_customize_5item_and_fx6_dials_hil(
            body_profile=p318.BODY_MODEL_FX6,
            av_tv_rotate=p318.AV_TV_ROTATE_REVERSE,
        )
        self.assertFalse(r_av.admitted)
        self.assertEqual(r_av.errno_code, p318.EOPNOTSUPP_ERRNO)

        r_fn = p318.simulate_dial_customize_5item_and_fx6_dials_hil(
            body_profile=p318.BODY_MODEL_FX6,
            fn_long_press_toggled=True,
        )
        self.assertFalse(r_fn.admitted)
        self.assertEqual(r_fn.errno_code, p318.EOPNOTSUPP_ERRNO)

    def test_24_fx3_rejects_fx6_physical_hold_switch_and_mfd_assign_eopnotsupp(self) -> None:
        r_hold = p318.simulate_dial_customize_5item_and_fx6_dials_hil(
            fx6_physical_hold_switch=True
        )
        self.assertFalse(r_hold.admitted)
        self.assertEqual(r_hold.errno_code, p318.EOPNOTSUPP_ERRNO)

        r_mfd = p318.simulate_dial_customize_5item_and_fx6_dials_hil(
            fx6_mfd_default_function="ISO"
        )
        self.assertFalse(r_mfd.admitted)
        self.assertEqual(r_mfd.errno_code, p318.EOPNOTSUPP_ERRNO)

    def test_25_invalid_66a_arguments_rejected_einval(self) -> None:
        self.assertEqual(
            p318.simulate_dial_customize_5item_and_fx6_dials_hil(
                body_profile="ILME-FX9"
            ).errno_code,
            p318.EINVAL_ERRNO,
        )
        self.assertEqual(
            p318.simulate_dial_customize_5item_and_fx6_dials_hil(
                av_tv_rotate="Diagonal"
            ).errno_code,
            p318.EINVAL_ERRNO,
        )
        self.assertEqual(
            p318.simulate_dial_customize_5item_and_fx6_dials_hil(
                lock_operation_parts="Touch Only"
            ).errno_code,
            p318.EINVAL_ERRNO,
        )
        self.assertEqual(
            p318.simulate_dial_customize_5item_and_fx6_dials_hil(
                body_profile=p318.BODY_MODEL_FX6,
                fx6_mfd_default_function="ShutterAngleInvalid",
            ).errno_code,
            p318.EINVAL_ERRNO,
        )


class TestSubModel66B3DialMyDialAndFn12x2(unittest.TestCase):
    """66B: 3-Physical-Dial Topology (Rear Dial L/R Ban), My Dial 1..3 Lock-Override & 12+12 Fn Menu (tests 26..40)."""

    def test_26_fx3_has_exact_3_physical_dials(self) -> None:
        self.assertEqual(p318.FX3_PHYSICAL_DIAL_COUNT, 3)
        self.assertEqual(
            p318.FX3_PHYSICAL_3_DIALS,
            ("Front Dial", "Rear Dial", "Control Wheel"),
        )
        for dial in p318.FX3_PHYSICAL_3_DIALS:
            r = p318.simulate_3dial_mydial_lock_override_and_fn_12x2_hil(
                requested_dial_symbol=dial
            )
            self.assertTrue(r.admitted, dial)
            self.assertEqual(r.physical_dial_count, 3, dial)
            self.assertFalse(r.rear_dial_lr_rejected, dial)

    def test_27_dormant_4dial_rear_dial_l_and_r_banned_eopnotsupp(self) -> None:
        for sym in p318.DORMANT_4DIAL_REAR_LR_SYMBOLS:
            r = p318.simulate_3dial_mydial_lock_override_and_fn_12x2_hil(
                requested_dial_symbol=sym
            )
            self.assertFalse(r.admitted, sym)
            self.assertEqual(r.errno_code, p318.EOPNOTSUPP_ERRNO, sym)
            self.assertTrue(r.rear_dial_lr_rejected, sym)
            self.assertEqual(r.physical_dial_count, 3, sym)

    def test_28_mydial_bank_map_rejects_rear_dial_l_r_inside_banks_eopnotsupp(self) -> None:
        r = p318.simulate_3dial_mydial_lock_override_and_fn_12x2_hil(
            mydial_banks={
                1: {"Rear Dial L": "ISO", "Rear Dial R": "WB"},
                2: {},
                3: {},
            }
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p318.EOPNOTSUPP_ERRNO)
        self.assertTrue(r.rear_dial_lr_rejected)

    def test_29_mydial_3_banks_shared_while_custom_keys_split_still_movie(self) -> None:
        r = p318.simulate_3dial_mydial_lock_override_and_fn_12x2_hil(
            shooting_domain=p318.DOMAIN_STILL,
            still_custom_key_binding="Hold My Dial 1",
            movie_custom_key_binding="My Dial 1->2->3",
        )
        self.assertTrue(r.admitted)
        self.assertTrue(r.mydial_banks_shared_across_modes)
        self.assertEqual(r.still_custom_key_binding, "Hold My Dial 1")
        self.assertEqual(r.movie_custom_key_binding, "My Dial 1->2->3")

    def test_30_mydial_123_cycle_auto_skips_all_not_set_bank_2(self) -> None:
        r = p318.simulate_3dial_mydial_lock_override_and_fn_12x2_hil(
            recall_action=p318.MYDIAL_RECALL_CYCLE_123,
            current_recalled_bank=1,
            mydial_banks={
                1: {"Front Dial": "ISO", "Rear Dial": "--", "Control Wheel": "--"},
                2: {"Front Dial": "--", "Rear Dial": "--", "Control Wheel": "--"},
                3: {"Front Dial": "Drive Mode", "Rear Dial": "--", "Control Wheel": "--"},
            },
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.recalled_mydial_bank, 3)
        self.assertEqual(r.skipped_empty_banks, (2,))

    def test_31_mydial_123_cycle_when_all_3_banks_empty_returns_none(self) -> None:
        r = p318.simulate_3dial_mydial_lock_override_and_fn_12x2_hil(
            recall_action=p318.MYDIAL_RECALL_CYCLE_123,
            current_recalled_bank=None,
            mydial_banks={
                1: {"Front Dial": "--", "Rear Dial": "--", "Control Wheel": "--"},
                2: {"Front Dial": "--", "Rear Dial": "--", "Control Wheel": "--"},
                3: {"Front Dial": "--", "Rear Dial": "--", "Control Wheel": "--"},
            },
        )
        self.assertTrue(r.admitted)
        self.assertIsNone(r.recalled_mydial_bank)
        self.assertEqual(r.skipped_empty_banks, (1, 2, 3))

    def test_32_mydial_recall_temporarily_unlocks_lock_operation_parts(self) -> None:
        for lock_mode in (p318.LOCK_OP_DIAL_WHEEL, p318.LOCK_OP_ALL):
            r = p318.simulate_3dial_mydial_lock_override_and_fn_12x2_hil(
                recall_action=p318.MYDIAL_RECALL_CYCLE_123,
                current_recalled_bank=None,
                lock_operation_parts=lock_mode,
                lock_engaged_before_recall=True,
            )
            self.assertTrue(r.admitted, lock_mode)
            self.assertEqual(r.recalled_mydial_bank, 1, lock_mode)
            self.assertTrue(r.dial_wheel_locked_before_recall, lock_mode)
            self.assertTrue(r.dial_wheel_temporarily_unlocked_during_mydial, lock_mode)
            self.assertFalse(r.lock_restored_after_mydial_exit, lock_mode)

    def test_33_mydial_exit_restores_lock_operation_parts_state(self) -> None:
        r = p318.simulate_3dial_mydial_lock_override_and_fn_12x2_hil(
            recall_action=p318.MYDIAL_RECALL_TOGGLE,
            current_recalled_bank=3,
            mydial_exit_triggered=True,
            lock_operation_parts=p318.LOCK_OP_ALL,
            lock_engaged_before_recall=True,
        )
        self.assertTrue(r.admitted)
        self.assertIsNone(r.recalled_mydial_bank)
        self.assertFalse(r.dial_wheel_temporarily_unlocked_during_mydial)
        self.assertTrue(r.lock_restored_after_mydial_exit)

    def test_34_fn_menu_12_still_all_not_set_blocks_invocation_einval(self) -> None:
        r = p318.simulate_3dial_mydial_lock_override_and_fn_12x2_hil(
            shooting_domain=p318.DOMAIN_STILL,
            still_fn_slots=[p318.FN_NOT_SET] * 12,
            movie_fn_slots=["Picture Profile", "ISO"] + [p318.FN_NOT_SET] * 10,
            invoke_fn_menu=True,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p318.EINVAL_ERRNO)
        self.assertFalse(r.fn_menu_invocable)
        self.assertFalse(r.cross_domain_fn_leak)

    def test_35_fn_menu_12_movie_invocable_while_12_still_not_set(self) -> None:
        r = p318.simulate_3dial_mydial_lock_override_and_fn_12x2_hil(
            shooting_domain=p318.DOMAIN_MOVIE,
            still_fn_slots=[p318.FN_NOT_SET] * 12,
            movie_fn_slots=["Picture Profile", "White Balance"] + [p318.FN_NOT_SET] * 10,
            invoke_fn_menu=True,
        )
        self.assertTrue(r.admitted)
        self.assertTrue(r.fn_menu_invocable)
        self.assertEqual(r.still_fn_slot_count, 12)
        self.assertEqual(r.movie_fn_slot_count, 12)
        self.assertEqual(r.active_domain_fn_assigned_count, 2)
        self.assertFalse(r.cross_domain_fn_leak)

    def test_36_fn_menu_and_mydial_survive_camera_settings_reset(self) -> None:
        r = p318.simulate_3dial_mydial_lock_override_and_fn_12x2_hil(
            shooting_domain=p318.DOMAIN_STILL,
            still_fn_slots=["Focus Mode", "ISO"] + [p318.FN_NOT_SET] * 10,
            invoke_fn_menu=True,
            camera_settings_reset_applied=True,
        )
        self.assertTrue(r.admitted)
        self.assertTrue(r.survived_cam_reset)
        self.assertTrue(r.reset_via_initialize_only)
        self.assertEqual(r.active_domain_fn_assigned_count, 2)
        self.assertTrue(r.fn_menu_invocable)

    def test_37_initialize_clears_mydial_banks_and_12x2_fn_slots(self) -> None:
        r = p318.simulate_3dial_mydial_lock_override_and_fn_12x2_hil(
            shooting_domain=p318.DOMAIN_STILL,
            current_recalled_bank=1,
            still_fn_slots=["Focus Mode", "ISO"] + [p318.FN_NOT_SET] * 10,
            invoke_fn_menu=False,
            initialize_applied=True,
        )
        self.assertTrue(r.admitted)
        self.assertIsNone(r.recalled_mydial_bank)
        self.assertEqual(r.active_domain_fn_assigned_count, 0)
        self.assertFalse(r.fn_menu_invocable)

    def test_38_fx6_status_screens_and_direct_menu_priority_vs_fx3(self) -> None:
        for prio in p318.FX6_DIRECT_MENU_PRIORITIES:
            r = p318.simulate_3dial_mydial_lock_override_and_fn_12x2_hil(
                body_profile=p318.BODY_MODEL_FX6,
                fx6_direct_menu_priority=prio,
            )
            self.assertTrue(r.admitted, prio)
            self.assertTrue(r.fx6_status_and_direct_menu_only)
            self.assertEqual(r.fx6_direct_menu_priority, prio)
            self.assertEqual(r.physical_dial_count, 5)

    def test_39_fx6_rejects_fx3_mydial_recall_and_fn12_invoke_eopnotsupp(self) -> None:
        r1 = p318.simulate_3dial_mydial_lock_override_and_fn_12x2_hil(
            body_profile=p318.BODY_MODEL_FX6,
            current_recalled_bank=1,
        )
        self.assertFalse(r1.admitted)
        self.assertEqual(r1.errno_code, p318.EOPNOTSUPP_ERRNO)

        r2 = p318.simulate_3dial_mydial_lock_override_and_fn_12x2_hil(
            body_profile=p318.BODY_MODEL_FX6,
            invoke_fn_menu=True,
        )
        self.assertFalse(r2.admitted)
        self.assertEqual(r2.errno_code, p318.EOPNOTSUPP_ERRNO)

    def test_40_invalid_66b_fn_slot_length_and_arguments_einval(self) -> None:
        r_len = p318.simulate_3dial_mydial_lock_override_and_fn_12x2_hil(
            still_fn_slots=["ISO"] * 10
        )
        self.assertFalse(r_len.admitted)
        self.assertEqual(r_len.errno_code, p318.EINVAL_ERRNO)

        r_act = p318.simulate_3dial_mydial_lock_override_and_fn_12x2_hil(
            recall_action="TripleTap"
        )
        self.assertFalse(r_act.admitted)
        self.assertEqual(r_act.errno_code, p318.EINVAL_ERRNO)

        r_fx6 = p318.simulate_3dial_mydial_lock_override_and_fn_12x2_hil(
            body_profile=p318.BODY_MODEL_FX6,
            fx6_direct_menu_priority="BogusPriority",
        )
        self.assertFalse(r_fx6.admitted)
        self.assertEqual(r_fx6.errno_code, p318.EINVAL_ERRNO)


class TestSubModel66CLiveViewDisplaySetAndGridLine(unittest.TestCase):
    """66C: Exact 3-item [Live View Display Set.] (Still-Only) & [Grid Line] Clean-HDMI Isolation (tests 41..55)."""

    def test_41_exact_3_live_view_display_set_items_exposed_in_still(self) -> None:
        r = p318.simulate_live_view_disp_and_grid_line_clean_hdmi_hil(
            shooting_domain=p318.DOMAIN_STILL
        )
        self.assertTrue(r.admitted)
        self.assertEqual(
            r.exposed_live_view_3_items,
            ("Live View Display", "Exposure Effect", "Frame Rate Low Limit"),
        )
        self.assertEqual(r.effective_live_view_display, p318.LIVE_VIEW_SETTING_EFFECT_ON)
        self.assertEqual(r.effective_exposure_effect, p318.EXP_EFFECT_SET_AND_FLASH)
        self.assertEqual(r.effective_frame_rate_low_limit, p318.FRAME_RATE_LOW_LIMIT_OFF)

    def test_42_live_view_display_set_blocked_in_movie_and_sq_ebusy(self) -> None:
        for dom in (p318.DOMAIN_MOVIE, p318.DOMAIN_SQ):
            r = p318.simulate_live_view_disp_and_grid_line_clean_hdmi_hil(
                shooting_domain=dom,
                access_live_view_display_set=True,
            )
            self.assertFalse(r.admitted, dom)
            self.assertEqual(r.errno_code, p318.EBUSY_ERRNO, dom)
            self.assertEqual(r.exposed_live_view_3_items, (), dom)

    def test_43_bright_monitoring_forces_setting_effect_off_even_from_on(self) -> None:
        r = p318.simulate_live_view_disp_and_grid_line_clean_hdmi_hil(
            shooting_domain=p318.DOMAIN_STILL,
            live_view_display=p318.LIVE_VIEW_SETTING_EFFECT_ON,
            bright_monitoring_active=True,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.effective_live_view_display, p318.LIVE_VIEW_SETTING_EFFECT_OFF)
        self.assertTrue(r.bright_monitoring_forced_off)
        self.assertTrue(r.view_off_indicator_shown)

    def test_44_exposure_effect_two_modes(self) -> None:
        for mode in p318.VALID_EXPOSURE_EFFECT_MODES:
            r = p318.simulate_live_view_disp_and_grid_line_clean_hdmi_hil(
                shooting_domain=p318.DOMAIN_STILL,
                exposure_effect=mode,
            )
            self.assertTrue(r.admitted, mode)
            self.assertEqual(r.effective_exposure_effect, mode, mode)

    def test_45_live_view_reset_split_camera_settings_reset_only_resets_frame_rate_low_limit(
        self,
    ) -> None:
        r = p318.simulate_live_view_disp_and_grid_line_clean_hdmi_hil(
            shooting_domain=p318.DOMAIN_STILL,
            live_view_display=p318.LIVE_VIEW_SETTING_EFFECT_OFF,
            exposure_effect=p318.EXP_EFFECT_EXPOSURE_ONLY,
            frame_rate_low_limit=p318.FRAME_RATE_LOW_LIMIT_ON,
            grid_line_display=p318.GRID_LINE_ON,
            grid_line_type=p318.GRID_TYPE_DIAG_SQUARE,
            camera_settings_reset_applied=True,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.effective_live_view_display, p318.LIVE_VIEW_SETTING_EFFECT_OFF)
        self.assertEqual(r.effective_exposure_effect, p318.EXP_EFFECT_EXPOSURE_ONLY)
        self.assertEqual(r.effective_frame_rate_low_limit, p318.FRAME_RATE_LOW_LIMIT_OFF)
        self.assertEqual(r.effective_grid_line_display, p318.GRID_LINE_ON)
        self.assertEqual(r.effective_grid_line_type, p318.GRID_TYPE_DIAG_SQUARE)
        self.assertTrue(r.live_view_and_exp_effect_survived_cam_reset)
        self.assertTrue(r.frame_rate_low_limit_reset_by_cam_reset)
        self.assertTrue(r.grid_line_survived_cam_reset)

    def test_46_initialize_resets_all_live_view_and_grid_line_items(self) -> None:
        r = p318.simulate_live_view_disp_and_grid_line_clean_hdmi_hil(
            shooting_domain=p318.DOMAIN_STILL,
            live_view_display=p318.LIVE_VIEW_SETTING_EFFECT_OFF,
            exposure_effect=p318.EXP_EFFECT_EXPOSURE_ONLY,
            frame_rate_low_limit=p318.FRAME_RATE_LOW_LIMIT_ON,
            grid_line_display=p318.GRID_LINE_ON,
            grid_line_type=p318.GRID_TYPE_SQUARE,
            initialize_applied=True,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.effective_live_view_display, p318.LIVE_VIEW_SETTING_EFFECT_ON)
        self.assertEqual(r.effective_exposure_effect, p318.EXP_EFFECT_SET_AND_FLASH)
        self.assertEqual(r.effective_frame_rate_low_limit, p318.FRAME_RATE_LOW_LIMIT_OFF)
        self.assertEqual(r.effective_grid_line_display, p318.GRID_LINE_OFF)
        self.assertEqual(r.effective_grid_line_type, p318.GRID_TYPE_RULE_OF_3RDS)

    def test_47_all_3_grid_line_types_supported_across_still_movie_sq(self) -> None:
        self.assertEqual(
            p318.VALID_GRID_LINE_TYPES,
            ("Rule of 3rds Grid", "Square Grid", "Diag. + Square Grid"),
        )
        for dom in p318.VALID_SHOOTING_DOMAINS:
            for gtype in p318.VALID_GRID_LINE_TYPES:
                r = p318.simulate_live_view_disp_and_grid_line_clean_hdmi_hil(
                    shooting_domain=dom,
                    access_live_view_display_set=False,
                    grid_line_display=p318.GRID_LINE_ON,
                    grid_line_type=gtype,
                    hdmi_info_display=p318.HDMI_INFO_OFF,
                )
                self.assertTrue(r.admitted, (dom, gtype))
                self.assertEqual(r.effective_grid_line_type, gtype, (dom, gtype))
                self.assertTrue(r.local_lcd_grid_rendered, (dom, gtype))
                self.assertEqual(r.hdmi_clean_feed_grid_leaked_pixels, 0, (dom, gtype))

    def test_48_grid_line_clean_hdmi_zero_bleed_when_hdmi_info_off(self) -> None:
        r = p318.simulate_live_view_disp_and_grid_line_clean_hdmi_hil(
            shooting_domain=p318.DOMAIN_MOVIE,
            access_live_view_display_set=False,
            grid_line_display=p318.GRID_LINE_ON,
            grid_line_type=p318.GRID_TYPE_DIAG_SQUARE,
            hdmi_info_display=p318.HDMI_INFO_OFF,
        )
        self.assertTrue(r.admitted)
        self.assertTrue(r.local_lcd_grid_rendered)
        self.assertFalse(r.local_lcd_blanked_by_hdmi_info_on)
        self.assertEqual(r.hdmi_clean_feed_grid_leaked_pixels, 0)

    def test_49_hdmi_info_on_blanks_local_lcd_without_recording_bleed(self) -> None:
        r = p318.simulate_live_view_disp_and_grid_line_clean_hdmi_hil(
            shooting_domain=p318.DOMAIN_MOVIE,
            access_live_view_display_set=False,
            grid_line_display=p318.GRID_LINE_ON,
            hdmi_info_display=p318.HDMI_INFO_ON,
        )
        self.assertTrue(r.admitted)
        self.assertFalse(r.local_lcd_grid_rendered)
        self.assertTrue(r.local_lcd_blanked_by_hdmi_info_on)
        self.assertEqual(r.hdmi_clean_feed_grid_leaked_pixels, 0)

    def test_50_fx6_marker_and_guide_frame_no_hdmi_raw_bleed(self) -> None:
        r = p318.simulate_live_view_disp_and_grid_line_clean_hdmi_hil(
            body_profile=p318.BODY_MODEL_FX6,
            fx6_guide_frame_on=True,
            hdmi_raw_or_hdmi_only_active=True,
        )
        self.assertTrue(r.admitted)
        self.assertTrue(r.fx6_uses_marker_and_guide_frame)
        self.assertEqual(r.hdmi_clean_feed_grid_leaked_pixels, 0)

    def test_51_dormant_custom_grid_line0_3_rejected_eopnotsupp(self) -> None:
        for idx in range(4):
            sym = f"BKID_APP_IS_EXIST_CUSTOM_GRID_LINE{idx}"
            r = p318.simulate_live_view_disp_and_grid_line_clean_hdmi_hil(
                body_profile=p318.BODY_MODEL_FX3,
                access_live_view_display_set=False,
                requested_dormant_custom_grid=sym,
            )
            self.assertFalse(r.admitted, sym)
            self.assertEqual(r.errno_code, p318.EOPNOTSUPP_ERRNO, sym)
            self.assertTrue(r.dormant_custom_grid_blocked, sym)

    def test_52_fx6_rejects_still_only_live_view_display_set_eopnotsupp(self) -> None:
        r = p318.simulate_live_view_disp_and_grid_line_clean_hdmi_hil(
            body_profile=p318.BODY_MODEL_FX6,
            live_view_display=p318.LIVE_VIEW_SETTING_EFFECT_OFF,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p318.EOPNOTSUPP_ERRNO)

    def test_53_fx6_rejects_fx3_grid_line_display_menu_eopnotsupp(self) -> None:
        r = p318.simulate_live_view_disp_and_grid_line_clean_hdmi_hil(
            body_profile=p318.BODY_MODEL_FX6,
            grid_line_display=p318.GRID_LINE_ON,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p318.EOPNOTSUPP_ERRNO)

    def test_54_grid_line_type_unchanged_without_display_still_clean_hdmi_zero(self) -> None:
        r = p318.simulate_live_view_disp_and_grid_line_clean_hdmi_hil(
            shooting_domain=p318.DOMAIN_MOVIE,
            access_live_view_display_set=False,
            grid_line_display=p318.GRID_LINE_OFF,
            grid_line_type=p318.GRID_TYPE_SQUARE,
            hdmi_info_display=p318.HDMI_INFO_OFF,
        )
        self.assertTrue(r.admitted)
        self.assertFalse(r.local_lcd_grid_rendered)
        self.assertEqual(r.hdmi_clean_feed_grid_leaked_pixels, 0)

    def test_55_invalid_66c_arguments_rejected_einval(self) -> None:
        for kwargs in (
            {"shooting_domain": "TimeLapseRaw"},
            {"live_view_display": "HDR Preview"},
            {"exposure_effect": "Strobe Only"},
            {"frame_rate_low_limit": "Auto"},
            {"grid_line_display": "Always"},
            {"grid_line_type": "Golden Ratio"},
            {"hdmi_info_display": "Auto"},
        ):
            r = p318.simulate_live_view_disp_and_grid_line_clean_hdmi_hil(**kwargs)
            self.assertFalse(r.admitted, str(kwargs))
            self.assertEqual(r.errno_code, p318.EINVAL_ERRNO, str(kwargs))


class TestSubModel66DManageUserLutsEmbedVsPplutAndSlot1Vault(unittest.TestCase):
    """66D: [Manage User LUTs] User1..16, [Embed LUT File] SD/SDHC Lock vs PPLUT1..4 & Slot-1 Vault (tests 56..72)."""

    def test_56_manage_user_luts_supports_user1_through_16_with_17_and_33_pt_cube(self) -> None:
        for pts in (17, 33):
            for slot_idx in (1, 8, 16):
                r = p318.simulate_user_lut_embed_vs_pplut_and_slot1_vault_hil(
                    operation=p318.LUT_OP_IMPORT,
                    card_slot=p318.SLOT_2,
                    card_media_type=p318.MEDIA_SDXC,
                    cube_grid_points=pts,
                    requested_user_slot_index=slot_idx,
                )
                self.assertTrue(r.admitted, (pts, slot_idx))
                self.assertTrue(r.user_slot_imported, (pts, slot_idx))
                self.assertEqual(r.cube_grid_points, pts)

    def test_57_user_slot_17_beyond_fx3_16_limit_rejected_eopnotsupp(self) -> None:
        for body in (p318.BODY_MODEL_FX3, p318.BODY_MODEL_FX6):
            r = p318.simulate_user_lut_embed_vs_pplut_and_slot1_vault_hil(
                body_profile=body,
                requested_user_slot_index=17,
            )
            self.assertFalse(r.admitted, body)
            self.assertEqual(r.errno_code, p318.EOPNOTSUPP_ERRNO, body)

    def test_58_sd_vs_cfexpress_card_lut_directory_paths(self) -> None:
        r_sd = p318.simulate_user_lut_embed_vs_pplut_and_slot1_vault_hil(
            card_media_type=p318.MEDIA_SDXC
        )
        self.assertTrue(r_sd.admitted)
        self.assertEqual(r_sd.expected_card_lut_dir, "/Private/Sony/PRO/LUT")

        r_cf = p318.simulate_user_lut_embed_vs_pplut_and_slot1_vault_hil(
            card_media_type=p318.MEDIA_CFEXPRESS_A
        )
        self.assertTrue(r_cf.admitted)
        self.assertEqual(r_cf.expected_card_lut_dir, "/Sony/PRO/LUT")

    def test_59_slot1_tier0_vault_allows_readonly_import_with_zero_writes(self) -> None:
        r = p318.simulate_user_lut_embed_vs_pplut_and_slot1_vault_hil(
            operation=p318.LUT_OP_IMPORT,
            card_slot=p318.SLOT_1,
            slot1_is_tier0_vault=True,
            card_media_type=p318.MEDIA_SDXC,
            requested_user_slot_index=5,
        )
        self.assertTrue(r.admitted)
        self.assertTrue(r.user_slot_imported)
        self.assertFalse(r.tier0_vault_firewall_triggered)
        self.assertEqual(r.slot1_data_sector_writes, 0)
        self.assertFalse(r.slot1_avf_info_mutated)
        self.assertEqual(r.slot1_vault_lut_mutation_bytes, 0)

    def test_60_critical_slot1_tier0_vault_firewall_blocks_all_write_ops_erofs(self) -> None:
        for op in (
            p318.LUT_OP_MAKE_CUBE_FOLDER,
            p318.LUT_OP_RECORD_EMBED_LUT,
            p318.LUT_OP_RECORD_PPLUT_BAKED,
            p318.LUT_OP_WRITE_LUT_CONFIG,
        ):
            r = p318.simulate_user_lut_embed_vs_pplut_and_slot1_vault_hil(
                operation=op,
                card_slot=p318.SLOT_1,
                slot1_is_tier0_vault=True,
                card_media_type=p318.MEDIA_CFEXPRESS_A,
            )
            self.assertFalse(r.admitted, op)
            self.assertEqual(r.errno_code, p318.EROFS_ERRNO, op)
            self.assertTrue(r.tier0_vault_firewall_triggered, op)
            self.assertEqual(r.slot1_data_sector_writes, 0, op)
            self.assertFalse(r.slot1_avf_info_mutated, op)
            self.assertEqual(r.slot1_vault_lut_mutation_bytes, 0, op)

    def test_61_embed_lut_file_embeds_container_metadata_no_sidecar_no_pixel_bake(self) -> None:
        r = p318.simulate_user_lut_embed_vs_pplut_and_slot1_vault_hil(
            operation=p318.LUT_OP_RECORD_EMBED_LUT,
            card_slot=p318.SLOT_2,
            card_media_type=p318.MEDIA_CFEXPRESS_A,
            select_lut="User1",
            imported_user_slots=(1,),
            log_shooting_mode=p318.LOG_SHOOTING_FLEXIBLE_ISO,
            requested_embed_lut_file=p318.EMBED_LUT_ON,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.effective_embed_lut_file, p318.EMBED_LUT_ON)
        self.assertTrue(r.is_embedded_lut_in_pb_file)
        self.assertFalse(r.pixels_baked_irreversibly)
        self.assertEqual(r.sidecar_cube_files_written, 0)

    def test_62_embed_lut_file_hard_locked_off_on_sd_and_sdhc_eopnotsupp(self) -> None:
        for med in (p318.MEDIA_SD, p318.MEDIA_SDHC):
            r_on = p318.simulate_user_lut_embed_vs_pplut_and_slot1_vault_hil(
                operation=p318.LUT_OP_RECORD_EMBED_LUT,
                card_slot=p318.SLOT_2,
                card_media_type=med,
                log_shooting_mode=p318.LOG_SHOOTING_CINE_EI,
                requested_embed_lut_file=p318.EMBED_LUT_ON,
            )
            self.assertFalse(r_on.admitted, med)
            self.assertEqual(r_on.errno_code, p318.EOPNOTSUPP_ERRNO, med)
            self.assertTrue(r_on.embed_lut_sd_sdhc_hard_locked_off, med)
            self.assertEqual(r_on.effective_embed_lut_file, p318.EMBED_LUT_OFF, med)
            self.assertFalse(r_on.is_embedded_lut_in_pb_file, med)

            r_off = p318.simulate_user_lut_embed_vs_pplut_and_slot1_vault_hil(
                operation=p318.LUT_OP_RECORD_EMBED_LUT,
                card_slot=p318.SLOT_2,
                card_media_type=med,
                log_shooting_mode=p318.LOG_SHOOTING_CINE_EI,
                requested_embed_lut_file=p318.EMBED_LUT_OFF,
            )
            self.assertTrue(r_off.admitted, med)
            self.assertEqual(r_off.effective_embed_lut_file, p318.EMBED_LUT_OFF, med)
            self.assertTrue(r_off.embed_lut_sd_sdhc_hard_locked_off, med)

    def test_63_embed_lut_requires_log_shooting_on_eopnotsupp_when_off(self) -> None:
        r = p318.simulate_user_lut_embed_vs_pplut_and_slot1_vault_hil(
            operation=p318.LUT_OP_RECORD_EMBED_LUT,
            card_slot=p318.SLOT_2,
            card_media_type=p318.MEDIA_CFEXPRESS_A,
            log_shooting_mode=p318.LOG_SHOOTING_OFF,
            requested_embed_lut_file=p318.EMBED_LUT_ON,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p318.EOPNOTSUPP_ERRNO)

    def test_64_embed_lut_wrong_menu_parent_color_tone_rejected_eopnotsupp(self) -> None:
        r = p318.simulate_user_lut_embed_vs_pplut_and_slot1_vault_hil(
            operation=p318.LUT_OP_RECORD_EMBED_LUT,
            card_slot=p318.SLOT_2,
            embed_lut_wrong_menu_parent=True,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p318.EOPNOTSUPP_ERRNO)

    def test_65_pplut1_to_4_irreversibly_bakes_pixels_without_container_metadata(self) -> None:
        for pp in p318.VALID_PPLUT_PROFILES:
            r = p318.simulate_user_lut_embed_vs_pplut_and_slot1_vault_hil(
                operation=p318.LUT_OP_RECORD_PPLUT_BAKED,
                card_slot=p318.SLOT_2,
                card_media_type=p318.MEDIA_SDXC,
                log_shooting_mode=p318.LOG_SHOOTING_OFF,
                picture_profile=pp,
            )
            self.assertTrue(r.admitted, pp)
            self.assertEqual(r.picture_profile, pp)
            self.assertTrue(r.pixels_baked_irreversibly, pp)
            self.assertFalse(r.is_embedded_lut_in_pb_file, pp)

    def test_66_pplut_cannot_run_while_log_shooting_active_eopnotsupp(self) -> None:
        r = p318.simulate_user_lut_embed_vs_pplut_and_slot1_vault_hil(
            operation=p318.LUT_OP_RECORD_PPLUT_BAKED,
            card_slot=p318.SLOT_2,
            log_shooting_mode=p318.LOG_SHOOTING_CINE_EI,
            picture_profile="PPLUT1",
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p318.EOPNOTSUPP_ERRNO)

    def test_67_select_lut_unimported_user_slot_falls_back_to_slog3(self) -> None:
        r = p318.simulate_user_lut_embed_vs_pplut_and_slot1_vault_hil(
            operation=p318.LUT_OP_WRITE_LUT_CONFIG,
            card_slot=p318.SLOT_2,
            select_lut="User9",
            imported_user_slots=(1,),
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.effective_select_lut, p318.SELECT_LUT_SLOG3)
        self.assertTrue(r.select_lut_fallback_slog3)

    def test_68_lut_reset_split_cam_reset_vs_initialize(self) -> None:
        r_csr = p318.simulate_user_lut_embed_vs_pplut_and_slot1_vault_hil(
            operation=p318.LUT_OP_IMPORT,
            card_slot=p318.SLOT_2,
            log_shooting_mode=p318.LOG_SHOOTING_OFF,
            select_lut="User1",
            imported_user_slots=(1,),
            requested_embed_lut_file=p318.EMBED_LUT_OFF,
            picture_profile="PPLUT3",
            camera_settings_reset_applied=True,
        )
        self.assertTrue(r_csr.admitted)
        self.assertTrue(r_csr.manage_user_luts_survived_cam_reset)
        self.assertEqual(r_csr.effective_select_lut, p318.SELECT_LUT_S709)
        self.assertEqual(r_csr.effective_embed_lut_file, p318.EMBED_LUT_ON)
        self.assertIsNone(r_csr.picture_profile)

        r_init = p318.simulate_user_lut_embed_vs_pplut_and_slot1_vault_hil(
            operation=p318.LUT_OP_IMPORT,
            card_slot=p318.SLOT_2,
            log_shooting_mode=p318.LOG_SHOOTING_OFF,
            select_lut="User1",
            imported_user_slots=(1,),
            picture_profile="PPLUT4",
            initialize_applied=True,
        )
        self.assertTrue(r_init.admitted)
        self.assertFalse(r_init.user_slot_imported)
        self.assertEqual(r_init.effective_select_lut, p318.SELECT_LUT_S709)
        self.assertEqual(r_init.effective_embed_lut_file, p318.EMBED_LUT_ON)
        self.assertIsNone(r_init.picture_profile)

    def test_69_cube_filename_validation_bad_extension_or_points_einval(self) -> None:
        r_ext = p318.simulate_user_lut_embed_vs_pplut_and_slot1_vault_hil(
            operation=p318.LUT_OP_IMPORT,
            card_slot=p318.SLOT_2,
            cube_filename="bad_lut.3dl",
        )
        self.assertFalse(r_ext.admitted)
        self.assertEqual(r_ext.errno_code, p318.EINVAL_ERRNO)

        r_pts = p318.simulate_user_lut_embed_vs_pplut_and_slot1_vault_hil(
            operation=p318.LUT_OP_IMPORT,
            card_slot=p318.SLOT_2,
            cube_grid_points=65,
        )
        self.assertFalse(r_pts.admitted)
        self.assertEqual(r_pts.errno_code, p318.EINVAL_ERRNO)

    def test_70_fx6_exclamation_prefixed_lut_rejected_einval_while_multichannel_ok(self) -> None:
        r_bang = p318.simulate_user_lut_embed_vs_pplut_and_slot1_vault_hil(
            body_profile=p318.BODY_MODEL_FX6,
            operation=p318.LUT_OP_IMPORT,
            card_slot=p318.SLOT_2,
            fx6_exclamation_prefixed_lut=True,
        )
        self.assertFalse(r_bang.admitted)
        self.assertEqual(r_bang.errno_code, p318.EINVAL_ERRNO)

        r_fx6 = p318.simulate_user_lut_embed_vs_pplut_and_slot1_vault_hil(
            body_profile=p318.BODY_MODEL_FX6,
            operation=p318.LUT_OP_RECORD_EMBED_LUT,
            card_slot=p318.SLOT_2,
            card_media_type=p318.MEDIA_CFEXPRESS_A,
        )
        self.assertTrue(r_fx6.admitted)
        self.assertTrue(r_fx6.fx6_multichannel_lut_switches_supported)

    def test_71_slot2_make_cube_folder_virtual_non_physical_ok(self) -> None:
        r = p318.simulate_user_lut_embed_vs_pplut_and_slot1_vault_hil(
            operation=p318.LUT_OP_MAKE_CUBE_FOLDER,
            card_slot=p318.SLOT_2,
            card_media_type=p318.MEDIA_SDXC,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.slot1_data_sector_writes, 0)
        self.assertEqual(r.physical_device_writes, 0)

    def test_72_invalid_66d_arguments_rejected_einval(self) -> None:
        for kwargs in (
            {"operation": "BOGUS_LUT_OP"},
            {"card_slot": "Slot 3"},
            {"card_media_type": "XQD"},
            {"log_shooting_mode": "Cine EI Quick+Raw"},
            {"requested_embed_lut_file": "Auto"},
            {"select_lut": "User99"},
            {"operation": p318.LUT_OP_RECORD_PPLUT_BAKED, "picture_profile": "PP12"},
        ):
            r = p318.simulate_user_lut_embed_vs_pplut_and_slot1_vault_hil(**kwargs)
            self.assertFalse(r.admitted, str(kwargs))
            self.assertEqual(r.errno_code, p318.EINVAL_ERRNO, str(kwargs))


class TestRedlinesCLIAndSuiteStage66Integration(unittest.TestCase):
    """Hard safety redlines, standalone CLI, and 66/66 Milestone Suite orchestration (tests 73..90)."""

    def test_73_full_phase318_report_66_66_milestone(self) -> None:
        rep = p318.run_phase318_dial_customize_mydial_fn_liveview_lut_embed_coemulation()
        self.assertTrue(rep["all_checks_passed"])
        self.assertTrue(rep["is_66th_stage_milestone"])
        self.assertEqual(rep["milestone"], "66/66")
        self.assertEqual(rep["stage_index"], 66)
        self.assertEqual(rep["stage_total"], 66)
        self.assertEqual(rep["phase_number"], 318)

    def test_74_clean_room_report_deterministic_digest_both_env_vars(self) -> None:
        r1 = p318.run_phase318_dial_customize_mydial_fn_liveview_lut_embed_coemulation(
            force_clean_room=True
        )
        r2 = p318.run_phase318_dial_customize_mydial_fn_liveview_lut_embed_coemulation(
            env={p318.ENV_FORCE_CLEAN_ROOM: "1"}
        )
        r3 = p318.run_phase318_dial_customize_mydial_fn_liveview_lut_embed_coemulation(
            env={p318.ENV_CLEAN_ROOM_TEST: "1"}
        )
        self.assertEqual(r1["source_mode"], p318.SOURCE_MODE_CLEAN_ROOM)
        self.assertEqual(r2["source_mode"], p318.SOURCE_MODE_CLEAN_ROOM)
        self.assertEqual(r3["source_mode"], p318.SOURCE_MODE_CLEAN_ROOM)
        self.assertEqual(r1["redlines"], r2["redlines"])
        self.assertEqual(r2["redlines"], r3["redlines"])
        self.assertEqual(r1["audit_digest_sha256"], r2["audit_digest_sha256"])
        self.assertEqual(r2["audit_digest_sha256"], r3["audit_digest_sha256"])

    def test_75_all_hardware_write_and_wave56_redlines_locked(self) -> None:
        rep = p318.run_phase318_dial_customize_mydial_fn_liveview_lut_embed_coemulation(
            force_clean_room=True
        )
        red = rep["redlines"]
        self.assertTrue(red["p8_cp_mutation_forbidden"])
        self.assertTrue(red["cnflasha_userspace_write_blocked"])
        self.assertEqual(red["fx3_physical_dial_count"], 3)
        for false_key in (
            "persistent_emmc_writes_authorized",
            "hardware_live_attachment_authorized",
            "overall_ready_for_hardware_attach",
            "isp_write_authorized",
            "spi_nor_write_authorized",
            "el3_payload_transmit_authorized",
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
            "dormant_dial_setup_or_rear_dial_lr_exposed_events",
            "mydial_lock_override_failures",
            "fn_menu_still_movie_12x2_leak_events",
            "live_view_movie_sq_bypass_events",
            "grid_line_hdmi_clean_feed_leaked_pixels",
            "embed_lut_sd_sdhc_lock_bypass_events",
            "pplut_non_reset_or_metadata_confusion_events",
            "slot1_data_sector_writes",
            "slot1_vault_lut_mutation_bytes",
            "rsv_orphan_count",
            "wf12_00342260_hits",
            "appfw_crashes",
            "null_gpio_derefs",
            "mailbox_stalls",
            "stock_cp_fault_count",
            "raw_firmware_bytes_leaked",
        ):
            self.assertEqual(red[zero_key], 0, zero_key)

    def test_76_standalone_cli_help_uses_sys_executable_and_percent_escaping(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                str(FX3_VM_DIR / "realhw_dial_customize_mydial_fn_liveview_lut_embed_coemulator.py"),
                "--help",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("100%", proc.stdout)
        self.assertIn("66/66", proc.stdout)

    def test_77_standalone_cli_summary_and_json_modes(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = p318.main(["--self-test", "--clean-room", "--summary"])
        self.assertEqual(rc, 0)
        self.assertIn("[PASS] Phase 318 Stage 66 (66/66 Milestone)", buf.getvalue())

        buf_json = io.StringIO()
        with contextlib.redirect_stdout(buf_json):
            rc2 = p318.main(["--self-test", "--clean-room", "--json"])
        self.assertEqual(rc2, 0)
        parsed = json.loads(buf_json.getvalue())
        self.assertEqual(parsed["milestone"], "66/66")
        self.assertTrue(parsed["is_66th_stage_milestone"])
        self.assertTrue(parsed["all_checks_passed"])

    def test_78_no_raw_firmware_bytes_leaked_in_json_output(self) -> None:
        rep = p318.run_phase318_dial_customize_mydial_fn_liveview_lut_embed_coemulation()
        dumped = json.dumps(rep)
        self.assertNotIn("\\x7fELF", dumped)
        self.assertEqual(rep["redlines"]["raw_firmware_bytes_leaked"], 0)

    def test_79_no_hardcoded_usr_bin_python3_in_stage66_files(self) -> None:
        mod_src = (
            FX3_VM_DIR / "realhw_dial_customize_mydial_fn_liveview_lut_embed_coemulator.py"
        ).read_text(encoding="utf-8")
        tst_src = Path(__file__).read_text(encoding="utf-8")
        forbidden = "/usr/bin/" + "python3"
        self.assertNotIn(forbidden, mod_src)
        self.assertNotIn(forbidden, tst_src)

    def test_80_suite_default_config_enables_stage66(self) -> None:
        cfg = suite.CoEmulationConfig()
        self.assertTrue(cfg.include_phase318_realhw_dial_customize_mydial_fn_liveview_lut_embed_hil)
        self.assertTrue(cfg.include_stage66)
        self.assertTrue(cfg.stage66_realhw_dial_customize_mydial_fn_liveview_lut_embed_hil)

    def test_81_suite_full_run_contains_at_least_66_stages_and_milestone_66_66(self) -> None:
        t0 = time.monotonic()
        rep = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig())
        elapsed = time.monotonic() - t0
        self.assertTrue(rep["all_checks_passed"])
        stage_keys = [k for k in rep if re.match(r"^stage\d+_", k)]
        self.assertGreaterEqual(len(stage_keys), 66)
        s66 = rep["stage66_realhw_dial_customize_mydial_fn_liveview_lut_embed_hil"]
        self.assertTrue(s66["all_checks_passed"])
        self.assertTrue(s66["is_66th_stage_milestone"])
        self.assertEqual(s66["milestone"], "66/66")
        self.assertEqual(s66["phase_number"], 318)
        max_elapsed = 30.0 if IS_CI else 15.0
        self.assertLess(elapsed, max_elapsed)

    def test_82_suite_fast_isolated_stage66_only_pass(self) -> None:
        cfg = suite.CoEmulationConfig(**_fast_suite_kwargs())
        rep = suite.run_fx3_vm_coemulation_suite(cfg)
        self.assertTrue(rep["all_checks_passed"])
        self.assertIsNone(rep.get("stage65_realhw_touch_shooting_disp_zero_evf_interval_pb_hil"))
        self.assertIsNotNone(rep.get("stage66_realhw_dial_customize_mydial_fn_liveview_lut_embed_hil"))

    def test_83_suite_skip_flags_disable_stage66(self) -> None:
        for flag in ("--skip-stage66", "--no-include-stage66", "--skip-phase318"):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = suite.main([*_FAST_CLI_FLAGS, flag, "--json"])
            self.assertEqual(rc, 0)
            data = json.loads(buf.getvalue())
            self.assertNotIn("stage66_realhw_dial_customize_mydial_fn_liveview_lut_embed_hil", data)
            self.assertFalse(data["config"]["include_stage66"])

    def test_84_suite_cli_help_includes_stage66_and_100pct(self) -> None:
        proc_help = subprocess.run(
            [sys.executable, "-B", str(FX3_VM_DIR / "fx3_vm_coemulation_suite.py"), "--help"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc_help.returncode, 0, proc_help.stderr)
        self.assertIn("--include-stage66", proc_help.stdout)
        self.assertIn("--skip-phase318", proc_help.stdout)
        self.assertIn("66/66 Milestone", proc_help.stdout)
        self.assertIn("100%", proc_help.stdout)

    def test_85_suite_cli_summary_includes_stage66_milestone_m66_and_redlines(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = suite.main([*_FAST_CLI_FLAGS, "--include-stage66", "--summary"])
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn(
            "realhw_dial_customize_mydial_fn_liveview_lut_embed_hil=CLEAN_ROOM_SYNTHETIC("
            "m66=66/66,dials=3,dl_byp=0,fn_leak=0,lv_byp=0,hdmi_px=0,emb_byp=0,s1_wr=0,emmc_wr=0)",
            out,
        )

    def test_86_suite_subprocess_uses_sys_executable_with_clean_room(self) -> None:
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
        self.assertIn("dials=3", proc.stdout)
        self.assertIn("hdmi_px=0", proc.stdout)
        self.assertIn("s1_wr=0", proc.stdout)

    def test_87_stage66_payload_keys_present_and_complete(self) -> None:
        rep = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig(**_fast_suite_kwargs()))
        s66 = rep["stage66_realhw_dial_customize_mydial_fn_liveview_lut_embed_hil"]
        for key in (
            "pillar_a_dial_customize_5item_and_fx6_dials_hil",
            "pillar_b_3dial_mydial_lock_override_and_fn_12x2_hil",
            "pillar_c_live_view_3item_and_grid_line_clean_hdmi_hil",
            "pillar_d_user_lut_embed_vs_pplut_and_slot1_vault_hil",
            "phase318_audit_digest_sha256",
            "donor_audit",
        ):
            self.assertIn(key, s66)

    def test_88_stage66_config_serialization_in_suite_report(self) -> None:
        rep = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig(**_fast_suite_kwargs()))
        cfg = rep["config"]
        self.assertTrue(cfg["include_phase318_realhw_dial_customize_mydial_fn_liveview_lut_embed_hil"])
        self.assertTrue(cfg["include_stage66"])
        self.assertTrue(cfg["stage66_realhw_dial_customize_mydial_fn_liveview_lut_embed_hil"])

    def test_89_suite_tamper_3dial_count_hdmi_leak_or_slot1_vault_detected_by_suite(self) -> None:
        with unittest.mock.patch.object(p318, "FX3_PHYSICAL_DIAL_COUNT", 4):
            rep1 = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig(**_fast_suite_kwargs()))
            self.assertFalse(rep1["all_checks_passed"])

        with unittest.mock.patch.object(p318, "GRID_LINE_HDMI_CLEAN_FEED_LEAKED_PIXELS", 1):
            rep2 = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig(**_fast_suite_kwargs()))
            self.assertFalse(rep2["all_checks_passed"])

        with unittest.mock.patch.object(p318, "SLOT1_AVF_INFO_MUTATED", True):
            rep3 = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig(**_fast_suite_kwargs()))
            self.assertFalse(rep3["all_checks_passed"])

    def test_90_dual_mode_suite_clean_room_and_stage66_probe_4_pillars(self) -> None:
        r_clean = suite.run_fx3_vm_coemulation_suite(suite.CoEmulationConfig(force_clean_room=True))
        self.assertTrue(r_clean["all_checks_passed"])
        clean_stages = [k for k in r_clean if re.match(r"^stage\d+_", k)]
        self.assertGreaterEqual(len(clean_stages), 66)

        probe = r_clean["stage66_realhw_dial_customize_mydial_fn_liveview_lut_embed_hil"][
            "pillar_d_user_lut_embed_vs_pplut_and_slot1_vault_hil"
        ]["stage66_milestone_probe"]
        self.assertEqual(probe["stage_index"], 66)
        self.assertEqual(probe["stage_total"], 66)
        self.assertEqual(probe["milestone"], "66/66")
        self.assertTrue(probe["is_66th_stage_milestone"])
        self.assertEqual(probe["fx3_physical_dial_count"], 3)
        self.assertEqual(len(probe["wave56_pillars"]), 4)


if __name__ == "__main__":
    unittest.main()
