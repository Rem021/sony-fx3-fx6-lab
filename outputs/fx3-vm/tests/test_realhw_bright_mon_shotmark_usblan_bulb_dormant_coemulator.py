#!/usr/bin/env python3
"""Unit tests for Phase 325 (Stage 68 — 68/68 Milestone):
Real-Hardware `ILME-FX3 Ver. 7.02` vs `ILME-FX6 Ver. 6.01` Wave-58:
Custom-Key-Only `[Bright Monitoring]` (`Ver. 7.00+` Focus Magnifier Coexistence) &
`[Monitor Brightness]` (`Manual -2..+2` / `Sunny Weather`, `Initialize`-Only) vs `ILME-FX6`
`VF Brightness 1..15` & AE `Backlight`,
`[Shot Mark 1/2]` & `[Clip Flag]` (`OK/NG/KEEP`) vs Zero `[Divide]` / `[Extract]` / `FTP Cut` &
`Slot-1` Tier-0 `EROFS=30` / `EBUSY=16` Vault Firewall,
Zero Bluetooth `[Timecode Link]` vs Wired `VMC-BNCM1` (`EXT-LK`), `WPA2/WPA3`-Only Wi-Fi
(`WW728473` 2.4/5GHz vs `WW558244` 2.4GHz), `Bluetooth 5.0` (`15/2/1`), & `USB-LAN` Mutual Exclusion
+ `[Airplane Mode]=On` Surviving Both Resets, and
Still `[BULB]` Mechanical-Shutter Constraint & `[DRO]` / `[DRO Bracket]` vs Dormant
`[Bulb Timer]` & Dormant `[Auto HDR]` HIL
(92 dual-mode tests).
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
import realhw_bright_mon_shotmark_usblan_bulb_dormant_coemulator as p325  # noqa: E402

IS_CI = os.environ.get("GITHUB_ACTIONS", "").lower() == "true"


def _fast_suite_kwargs(**overrides: object) -> dict:
    """Fast config skipping unrelated optional stages 4..67 for quick Stage 68 isolation tests."""
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
        include_stage66=False,
        include_stage67=False,
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
    "--skip-stage66",
    "--skip-stage67",
]


class TestRealHwStage68BrightMonShotMarkUsbLanBulbDormant(unittest.TestCase):
    # ------------------------------------------------------------------
    # Donor Audit, Bounded O_RDONLY & Dual-Mode Tests (Tests 1..12)
    # ------------------------------------------------------------------

    def test_01_milestone_constants_68_of_68(self) -> None:
        self.assertEqual(p325.PHASE_NUMBER, 325)
        self.assertEqual(p325.STAGE_INDEX, 68)
        self.assertEqual(p325.STAGE_TOTAL, 68)
        self.assertEqual(p325.MILESTONE_LABEL, "68/68")
        self.assertTrue(p325.IS_68TH_STAGE_MILESTONE)
        self.assertEqual(len(p325.DONOR_RELPATHS), 28)
        self.assertEqual(len(p325.EXPECTED_DONOR_BYTES), 28)
        self.assertEqual(len(p325.EXPECTED_COMPACT_DONOR_SHA256), 25)
        self.assertEqual(len(p325.EXPECTED_LARGE_HEAD4K_SHA256), 3)

    def test_02_donor_audit_matches_active_mode(self) -> None:
        rep = p325.inspect_phase325_donors()
        self.assertTrue(rep.all_contracts_verified)
        self.assertEqual(rep.donor_files_inspected, 28)
        self.assertEqual(rep.compact_donors_verified, 25)
        self.assertEqual(rep.large_donors_verified, 3)
        self.assertEqual(rep.access_mode, "O_RDONLY")
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)
        if p325.clean_room_test_mode() or p325.resolve_mac_work_root() is None:
            self.assertEqual(rep.source_mode, "CLEAN_ROOM_SYNTHETIC")
        else:
            self.assertEqual(rep.source_mode, "LOCAL_DONOR_O_RDONLY")

    def test_03_clean_room_test_env_triggers_synthetic_mode(self) -> None:
        rep = p325.inspect_phase325_donors(env={"FX3_CLEAN_ROOM_TEST": "1"})
        self.assertEqual(rep.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(rep.all_contracts_verified)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_04_force_clean_room_env_triggers_synthetic_mode(self) -> None:
        rep = p325.inspect_phase325_donors(env={"FX3_FX6_FORCE_CLEAN_ROOM": "1"})
        self.assertEqual(rep.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(rep.all_contracts_verified)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_05_force_clean_room_kwarg_overrides_local_donors(self) -> None:
        rep = p325.inspect_phase325_donors(force_clean_room=True)
        self.assertEqual(rep.source_mode, "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(rep.all_contracts_verified)

    def test_06_donorless_work_root_none_falls_back_cleanly(self) -> None:
        with unittest.mock.patch.object(p325, "resolve_mac_work_root", return_value=None):
            rep = p325.inspect_phase325_donors(force_clean_room=False)
            self.assertEqual(rep.source_mode, "CLEAN_ROOM_SYNTHETIC")
            self.assertTrue(rep.all_contracts_verified)
            self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_07_sentinel_dirname_disables_donor_lookup(self) -> None:
        root = p325.resolve_mac_work_root(
            force_clean_room=False,
            env={"FX3_FX6_MAC_WORK_ROOT": f"/tmp/{p325.CLEAN_ROOM_SENTINEL_DIRNAME}"},
        )
        self.assertIsNone(root)

    def test_08_bounded_window_rejects_illegal_offset_or_oversize(self) -> None:
        with tempfile.NamedTemporaryFile() as tmp:
            tmp.write(b"ABCD" * 32)
            tmp.flush()
            with self.assertRaises(p325.Stage68Phase325Error):
                p325._read_window_readonly_bytes(Path(tmp.name), -1, 16)
            with self.assertRaises(p325.Stage68Phase325Error):
                p325._read_window_readonly_bytes(Path(tmp.name), 0, 0)
            with self.assertRaises(p325.Stage68Phase325Error):
                p325._read_window_readonly_bytes(
                    Path(tmp.name), 0, p325.BOUNDED_WINDOW_MAX_BYTES + 1
                )

    def test_09_bounded_window_reads_exact_slice_o_rdonly(self) -> None:
        with tempfile.NamedTemporaryFile() as tmp:
            tmp.write(b"0123456789ABCDEF")
            tmp.flush()
            self.assertEqual(p325._read_window_readonly_bytes(Path(tmp.name), 4, 6), b"456789")
            self.assertEqual(p325._read_window_readonly_bytes(Path(tmp.name), 999, 8), b"")

    def test_10_coemulation_payload_top_level_and_zero_leak(self) -> None:
        rep = p325.run_phase325_bright_mon_shotmark_usblan_bulb_dormant_coemulation(
            force_clean_room=True
        )
        self.assertTrue(rep["all_checks_passed"])
        self.assertTrue(rep["is_68th_stage_milestone"])
        self.assertEqual(rep["milestone"], "68/68")
        self.assertEqual(rep["phase_number"], 325)
        self.assertEqual(rep["stage_index"], 68)
        self.assertEqual(rep["stage_total"], 68)
        self.assertEqual(rep["redlines"]["raw_firmware_bytes_leaked"], 0)
        dumped = json.dumps(rep)
        self.assertNotIn("\\x7fELF", dumped)

    def test_11_audit_digest_deterministic_in_clean_room(self) -> None:
        r1 = p325.run_phase325_bright_mon_shotmark_usblan_bulb_dormant_coemulation(
            force_clean_room=True
        )
        r2 = p325.run_phase325_bright_mon_shotmark_usblan_bulb_dormant_coemulation(
            force_clean_room=True
        )
        self.assertEqual(r1["audit_digest_sha256"], r2["audit_digest_sha256"])

    def test_12_clean_room_vs_local_donor_parity(self) -> None:
        r_clean = p325.run_phase325_bright_mon_shotmark_usblan_bulb_dormant_coemulation(
            force_clean_room=True
        )
        r_default = p325.run_phase325_bright_mon_shotmark_usblan_bulb_dormant_coemulation()
        self.assertEqual(r_clean["all_checks_passed"], r_default["all_checks_passed"])
        self.assertEqual(r_clean["redlines"], r_default["redlines"])

    # ------------------------------------------------------------------
    # Sub-Model 68A — Bright Monitoring & Monitor Brightness vs FX6 (Tests 13..28)
    # ------------------------------------------------------------------

    def test_13_bright_monitoring_custom_key_only_forces_setting_effect_off(self) -> None:
        for mode in p325.FX3_PASM_MODES:
            r = p325.simulate_bright_monitoring_and_monitor_brightness_hil(
                firmware_version=p325.FW_VER_702,
                exposure_mode=mode,
                focus_mode="MF",
                trigger_source="Custom Key/Dial Set.",
                bright_monitoring_requested=True,
                live_view_setting_effect_requested="Setting Effect ON",
            )
            self.assertTrue(r.admitted, mode)
            self.assertTrue(r.bright_monitoring_active)
            self.assertFalse(r.shooting_menu_toggle_exposed)
            self.assertEqual(r.live_view_setting_effect, "Setting Effect OFF")
            self.assertFalse(r.hdmi_clean_feed_altered)

    def test_14_bright_monitoring_shooting_menu_rejected_eopnotsupp(self) -> None:
        r = p325.simulate_bright_monitoring_and_monitor_brightness_hil(
            trigger_source="Shooting Menu",
            bright_monitoring_requested=True,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p325.EOPNOTSUPP_ERRNO)
        self.assertFalse(r.bright_monitoring_active)
        self.assertFalse(r.shooting_menu_toggle_exposed)
        self.assertEqual(r.auto_canceled_reason, "CustomKeyOnly")

    def test_15_bright_monitoring_ver700_702_allows_focus_magnifier_coexistence(self) -> None:
        for fw in (p325.FW_VER_700, p325.FW_VER_702):
            for mag, auto_mag in ((True, False), (False, True), (True, True)):
                r = p325.simulate_bright_monitoring_and_monitor_brightness_hil(
                    firmware_version=fw,
                    exposure_mode="M",
                    focus_mode="MF",
                    trigger_source="Custom Key/Dial Set.",
                    bright_monitoring_requested=True,
                    focus_magnifier_active=mag,
                    auto_magnifier_in_mf_active=auto_mag,
                )
                self.assertTrue(r.admitted, (fw, mag, auto_mag))
                self.assertTrue(r.bright_monitoring_active)
                self.assertTrue(r.magnifier_coexistence_allowed)

    def test_16_bright_monitoring_pre_ver700_blocks_focus_magnifier(self) -> None:
        r = p325.simulate_bright_monitoring_and_monitor_brightness_hil(
            firmware_version=p325.FW_VER_601,
            exposure_mode="M",
            focus_mode="MF",
            bright_monitoring_requested=True,
            focus_magnifier_active=True,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p325.EOPNOTSUPP_ERRNO)
        self.assertFalse(r.magnifier_coexistence_allowed)
        self.assertEqual(r.auto_canceled_reason, "LegacyPre700_Magnifier_MutualExclusion")

    def test_17_bright_monitoring_auto_cancels_on_power_off(self) -> None:
        r = p325.simulate_bright_monitoring_and_monitor_brightness_hil(
            bright_monitoring_requested=True,
            power_off_applied=True,
        )
        self.assertTrue(r.admitted)
        self.assertFalse(r.bright_monitoring_active)
        self.assertEqual(r.auto_canceled_reason, "AutoCanceled:PowerOff")

    def test_18_bright_monitoring_auto_cancels_leaving_pasm(self) -> None:
        for exp in p325.FX3_NON_PASM_MODES:
            r = p325.simulate_bright_monitoring_and_monitor_brightness_hil(
                bright_monitoring_requested=True,
                exposure_mode=exp,
            )
            self.assertTrue(r.admitted, exp)
            self.assertFalse(r.bright_monitoring_active)
            self.assertEqual(r.auto_canceled_reason, "AutoCanceled:Left_PASM")

    def test_19_bright_monitoring_auto_cancels_leaving_mf_for_af(self) -> None:
        for af in ("AF-S", "AF-C", "DMF", "AF-A"):
            r = p325.simulate_bright_monitoring_and_monitor_brightness_hil(
                bright_monitoring_requested=True,
                focus_mode=af,
            )
            self.assertTrue(r.admitted, af)
            self.assertFalse(r.bright_monitoring_active)
            self.assertEqual(r.auto_canceled_reason, "AutoCanceled:Left_MF_For_AF")

    def test_20_fx3_4k_recording_has_no_thermal_brightness_clamp(self) -> None:
        r = p325.simulate_bright_monitoring_and_monitor_brightness_hil(
            shoot_mode=p325.SHOOT_MODE_MOVIE,
            recording_4k_active=True,
            monitor_brightness_mode="Sunny Weather",
        )
        self.assertTrue(r.admitted)
        self.assertFalse(r.fx3_4k_thermal_brightness_clamp)
        self.assertTrue(r.sunny_weather_power_warning)

    def test_21_monitor_brightness_manual_range_minus2_to_plus2(self) -> None:
        for lvl in (-2, -1, 0, 1, 2):
            r = p325.simulate_bright_monitoring_and_monitor_brightness_hil(
                monitor_brightness_mode="Manual",
                monitor_brightness_manual_level=lvl,
            )
            self.assertTrue(r.admitted, lvl)
            self.assertEqual(r.monitor_brightness_manual_level, lvl)
        for bad in (-3, 3):
            r_bad = p325.simulate_bright_monitoring_and_monitor_brightness_hil(
                monitor_brightness_mode="Manual",
                monitor_brightness_manual_level=bad,
            )
            self.assertFalse(r_bad.admitted, bad)
            self.assertEqual(r_bad.errno_code, p325.EINVAL_ERRNO)

    def test_22_monitor_brightness_dormant_auto_rejected_eopnotsupp(self) -> None:
        for mode in p325.DORMANT_MONITOR_BRIGHTNESS_MODES:
            r = p325.simulate_bright_monitoring_and_monitor_brightness_hil(
                monitor_brightness_mode=mode,
            )
            self.assertFalse(r.admitted, mode)
            self.assertEqual(r.errno_code, p325.EOPNOTSUPP_ERRNO)
            self.assertTrue(r.dormant_lcd_brightness_auto_rejected)

    def test_23_monitor_brightness_survives_reset_but_resets_on_initialize(self) -> None:
        r_reset = p325.simulate_bright_monitoring_and_monitor_brightness_hil(
            monitor_brightness_mode="Sunny Weather",
            monitor_brightness_manual_level=2,
            camera_settings_reset_applied=True,
        )
        self.assertTrue(r_reset.admitted)
        self.assertEqual(r_reset.monitor_brightness_mode, "Sunny Weather")
        self.assertEqual(r_reset.monitor_brightness_manual_level, 2)
        self.assertTrue(r_reset.camera_settings_reset_preserved_brightness)

        r_init = p325.simulate_bright_monitoring_and_monitor_brightness_hil(
            monitor_brightness_mode="Sunny Weather",
            monitor_brightness_manual_level=2,
            initialize_applied=True,
        )
        self.assertTrue(r_init.admitted)
        self.assertEqual(r_init.monitor_brightness_mode, "Manual")
        self.assertEqual(r_init.monitor_brightness_manual_level, 0)
        self.assertTrue(r_init.initialize_resets_brightness)

    def test_24_fx6_vf_brightness_1_to_15_and_color_bw(self) -> None:
        for lvl, cm in ((1, "Color"), (8, "Color"), (15, "B&W")):
            r = p325.simulate_bright_monitoring_and_monitor_brightness_hil(
                body_profile=p325.BODY_MODEL_FX6,
                fx6_vf_brightness_level=lvl,
                fx6_vf_color_mode=cm,
            )
            self.assertTrue(r.admitted)
            self.assertEqual(r.fx6_vf_brightness_level, lvl)
            self.assertEqual(r.fx6_vf_color_mode, cm)

    def test_25_fx6_vf_brightness_out_of_range_rejected_einval(self) -> None:
        for bad in (0, 16):
            r = p325.simulate_bright_monitoring_and_monitor_brightness_hil(
                body_profile=p325.BODY_MODEL_FX6,
                fx6_vf_brightness_level=bad,
            )
            self.assertFalse(r.admitted)
            self.assertEqual(r.errno_code, p325.EINVAL_ERRNO)

    def test_26_fx6_ae_backlight_vs_dormant_lcd_vf_backlight_nightshot(self) -> None:
        r_ae = p325.simulate_bright_monitoring_and_monitor_brightness_hil(
            body_profile=p325.BODY_MODEL_FX6,
            fx6_ae_mode="Backlight",
        )
        self.assertTrue(r_ae.admitted)
        self.assertTrue(r_ae.is_ae_backlight_compensation)

        for feat in ("LCD Backlight", "VF Backlight", "NIGHTSHOT_MODE", "NIGHTSHOT_SETTING"):
            r_dorm = p325.simulate_bright_monitoring_and_monitor_brightness_hil(
                body_profile=p325.BODY_MODEL_FX6,
                fx6_dormant_feature_requested=feat,
            )
            self.assertFalse(r_dorm.admitted, feat)
            self.assertEqual(r_dorm.errno_code, p325.EOPNOTSUPP_ERRNO)
            self.assertTrue(r_dorm.dormant_fx6_backlight_or_nightshot_rejected)

    def test_27_fx6_rejects_bright_monitoring_eopnotsupp(self) -> None:
        r = p325.simulate_bright_monitoring_and_monitor_brightness_hil(
            body_profile=p325.BODY_MODEL_FX6,
            bright_monitoring_requested=True,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p325.EOPNOTSUPP_ERRNO)
        self.assertEqual(r.auto_canceled_reason, "FX6_uses_Cine_EI_dual_native_ISO_800_12800")

    def test_28_invalid_68a_arguments_raise(self) -> None:
        with self.assertRaises(p325.Stage68Phase325Error):
            p325.simulate_bright_monitoring_and_monitor_brightness_hil(body_profile="FX30")
        with self.assertRaises(p325.Stage68Phase325Error):
            p325.simulate_bright_monitoring_and_monitor_brightness_hil(trigger_source="Fn")

    # ------------------------------------------------------------------
    # Sub-Model 68B — Shot Mark 1/2, Clip Flag, Zero Divide/Extract & Slot-1 Vault (Tests 29..46)
    # ------------------------------------------------------------------

    def test_29_fx3_recording_add_shot_mark1_and_2_on_slot2(self) -> None:
        for op in ("Add Shot Mark1", "Add Shot Mark2"):
            r = p325.simulate_shot_mark_clip_flag_edit_and_slot1_vault_hil(
                operation=op,
                target_slot=p325.SLOT_2,
                is_recording=True,
            )
            self.assertTrue(r.admitted, op)
            self.assertTrue(r.m4root_xml_sidecar_rewritten)
            self.assertFalse(r.dcim_still_written)
            self.assertEqual(r.slot1_data_sector_writes, 0)

    def test_30_fx3_add_shot_mark_during_playback_rejected_einval(self) -> None:
        for op in ("Add Shot Mark1", "Add Shot Mark2"):
            r = p325.simulate_shot_mark_clip_flag_edit_and_slot1_vault_hil(
                operation=op,
                target_slot=p325.SLOT_2,
                is_recording=False,
            )
            self.assertFalse(r.admitted)
            self.assertEqual(r.errno_code, p325.EINVAL_ERRNO)

    def test_31_fx3_playback_add_delete_shot_mark1_and_2_on_slot2(self) -> None:
        for op in ("Add/Delete Shot Mark1", "Add/Delete Shot Mark2"):
            r = p325.simulate_shot_mark_clip_flag_edit_and_slot1_vault_hil(
                operation=op,
                target_slot=p325.SLOT_2,
                is_recording=False,
            )
            self.assertTrue(r.admitted, op)
            self.assertTrue(r.m4root_xml_sidecar_rewritten)

    def test_32_fx3_playback_shot_mark_or_photo_capture_during_rec_ebusy(self) -> None:
        for op in ("Add/Delete Shot Mark1", "Add/Delete Shot Mark2", "Photo Capture"):
            r = p325.simulate_shot_mark_clip_flag_edit_and_slot1_vault_hil(
                operation=op,
                target_slot=p325.SLOT_2,
                is_recording=True,
            )
            self.assertFalse(r.admitted, op)
            self.assertEqual(r.errno_code, p325.EBUSY_ERRNO)

    def test_33_fx3_all_12_image_jump_settings_admitted(self) -> None:
        for jmp in p325.FX3_IMAGE_JUMP_SETTINGS:
            r = p325.simulate_shot_mark_clip_flag_edit_and_slot1_vault_hil(
                operation="Image Jump",
                target_slot=p325.SLOT_1,
                is_recording=False,
                image_jump_setting=jmp,
            )
            self.assertTrue(r.admitted, jmp)
            self.assertEqual(r.image_jump_setting, jmp)
            self.assertEqual(r.slot1_data_sector_writes, 0)

    def test_34_fx3_clip_flag_ok_ng_keep_off_on_slot2(self) -> None:
        for flag in p325.FX3_CLIP_FLAGS:
            r = p325.simulate_shot_mark_clip_flag_edit_and_slot1_vault_hil(
                operation="Clip Flag Edit",
                target_slot=p325.SLOT_2,
                is_recording=False,
                clip_flag=flag,
            )
            self.assertTrue(r.admitted, flag)
            self.assertEqual(r.clip_flag, flag)
            self.assertTrue(r.m4root_xml_sidecar_rewritten)

    def test_35_fx3_photo_capture_jpeg_heif420_heif422_on_slot2(self) -> None:
        for ft in p325.FX3_PHOTO_CAPTURE_FILE_TYPES:
            r = p325.simulate_shot_mark_clip_flag_edit_and_slot1_vault_hil(
                operation="Photo Capture",
                target_slot=p325.SLOT_2,
                is_recording=False,
                photo_capture_file_type=ft,
            )
            self.assertTrue(r.admitted, ft)
            self.assertTrue(r.dcim_still_written)
            self.assertFalse(r.m4root_xml_sidecar_rewritten)

    def test_36_fx3_create_divider_frame_on_slot2(self) -> None:
        r = p325.simulate_shot_mark_clip_flag_edit_and_slot1_vault_hil(
            operation="Create Divider Frame",
            target_slot=p325.SLOT_2,
            is_recording=False,
        )
        self.assertTrue(r.admitted)
        self.assertTrue(r.dcim_still_written)
        self.assertEqual(r.slot1_data_sector_writes, 0)

    def test_37_fx3_dormant_divide_extract_ftp_cut_rejected_eopnotsupp(self) -> None:
        for op in p325.DORMANT_DIVIDE_EXTRACT_CUT_OPS:
            r = p325.simulate_shot_mark_clip_flag_edit_and_slot1_vault_hil(
                operation=op,
                target_slot=p325.SLOT_2,
                is_recording=False,
            )
            self.assertFalse(r.admitted, op)
            self.assertEqual(r.errno_code, p325.EOPNOTSUPP_ERRNO)
            self.assertTrue(r.dormant_divide_extract_cut_rejected)

    def test_38_slot1_tier0_vault_blocks_all_write_ops_erofs(self) -> None:
        for op in p325.FX3_WRITE_CARD_OPS:
            r = p325.simulate_shot_mark_clip_flag_edit_and_slot1_vault_hil(
                operation=op,
                target_slot=p325.SLOT_1,
                is_recording=(op in ("Add Shot Mark1", "Add Shot Mark2")),
            )
            self.assertFalse(r.admitted, op)
            self.assertEqual(r.errno_code, p325.EROFS_ERRNO)
            self.assertTrue(r.tier0_vault_firewall_triggered)
            self.assertEqual(r.slot1_data_sector_writes, 0)
            self.assertFalse(r.slot1_avf_info_mutated)
            self.assertEqual(r.slot1_vault_shotmark_edit_mutation_bytes, 0)

    def test_39_slot1_tier0_vault_returns_ebusy_when_busy(self) -> None:
        r = p325.simulate_shot_mark_clip_flag_edit_and_slot1_vault_hil(
            operation="Add/Delete Shot Mark1",
            target_slot=p325.SLOT_1,
            is_recording=False,
            slot1_vault_busy=True,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p325.EBUSY_ERRNO)
        self.assertTrue(r.tier0_vault_firewall_triggered)
        self.assertEqual(r.slot1_data_sector_writes, 0)
        self.assertFalse(r.slot1_avf_info_mutated)

    def test_40_slot1_readonly_playback_and_ftp_filter_pull_allowed(self) -> None:
        for op in ("ReadOnly_Playback", "FTP_Filter_Pull"):
            r = p325.simulate_shot_mark_clip_flag_edit_and_slot1_vault_hil(
                operation=op,
                target_slot=p325.SLOT_1,
                is_recording=False,
            )
            self.assertTrue(r.admitted, op)
            self.assertEqual(r.slot1_data_sector_writes, 0)
            self.assertFalse(r.slot1_avf_info_mutated)

    def test_41_fx6_thumbnail_clip_flag_active_on_slot2(self) -> None:
        r = p325.simulate_shot_mark_clip_flag_edit_and_slot1_vault_hil(
            body_profile=p325.BODY_MODEL_FX6,
            operation="Clip Flag Edit",
            target_slot=p325.SLOT_2,
            clip_flag="NG",
        )
        self.assertTrue(r.admitted)
        self.assertTrue(r.m4root_xml_sidecar_rewritten)

    def test_42_fx6_dormant_shot_mark_0_to_9_and_essence_mark_rejected(self) -> None:
        for op in (
            "Shot Mark 0..9",
            "Essence Mark",
            "Add Shot Mark1",
            "Add/Delete Shot Mark2",
            "Create Divider Frame",
        ):
            r = p325.simulate_shot_mark_clip_flag_edit_and_slot1_vault_hil(
                body_profile=p325.BODY_MODEL_FX6,
                operation=op,
                target_slot=p325.SLOT_2,
            )
            self.assertFalse(r.admitted, op)
            self.assertEqual(r.errno_code, p325.EOPNOTSUPP_ERRNO)
            self.assertTrue(r.dormant_fx6_shotmark_essence_rejected)

    def test_43_fx6_dormant_divide_extract_rejected_eopnotsupp(self) -> None:
        for op in ("Divide", "Divide Clip", "Extract"):
            r = p325.simulate_shot_mark_clip_flag_edit_and_slot1_vault_hil(
                body_profile=p325.BODY_MODEL_FX6,
                operation=op,
                target_slot=p325.SLOT_2,
            )
            self.assertFalse(r.admitted, op)
            self.assertEqual(r.errno_code, p325.EOPNOTSUPP_ERRNO)
            self.assertTrue(r.dormant_divide_extract_cut_rejected)

    def test_44_fx6_slot1_clip_flag_blocked_by_vault_firewall(self) -> None:
        r = p325.simulate_shot_mark_clip_flag_edit_and_slot1_vault_hil(
            body_profile=p325.BODY_MODEL_FX6,
            operation="Clip Flag Edit",
            target_slot=p325.SLOT_1,
            clip_flag="KEEP",
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p325.EROFS_ERRNO)
        self.assertTrue(r.tier0_vault_firewall_triggered)
        self.assertEqual(r.slot1_data_sector_writes, 0)

    def test_45_fx3_copy_and_rotate_slot1_blocked_erofs(self) -> None:
        for op in ("Copy", "Rotate"):
            r = p325.simulate_shot_mark_clip_flag_edit_and_slot1_vault_hil(
                operation=op,
                target_slot=p325.SLOT_1,
                is_recording=False,
            )
            self.assertFalse(r.admitted, op)
            self.assertEqual(r.errno_code, p325.EROFS_ERRNO)

    def test_46_invalid_68b_arguments_raise(self) -> None:
        with self.assertRaises(p325.Stage68Phase325Error):
            p325.simulate_shot_mark_clip_flag_edit_and_slot1_vault_hil(target_slot=3)
        with self.assertRaises(p325.Stage68Phase325Error):
            p325.simulate_shot_mark_clip_flag_edit_and_slot1_vault_hil(clip_flag="BAD")
        with self.assertRaises(p325.Stage68Phase325Error):
            p325.simulate_shot_mark_clip_flag_edit_and_slot1_vault_hil(
                photo_capture_file_type="RAW"
            )
        with self.assertRaises(p325.Stage68Phase325Error):
            p325.simulate_shot_mark_clip_flag_edit_and_slot1_vault_hil(operation="UnknownOp")

    # ------------------------------------------------------------------
    # Sub-Model 68C — Zero BT Timecode Link vs VMC-BNCM1, WPA2/WPA3, USB-LAN (Tests 47..68)
    # ------------------------------------------------------------------

    def test_47_bt_timecode_link_and_ultrasync_blue_rejected_eopnotsupp(self) -> None:
        for src in ("Timecode Link", "Bluetooth Timecode Link", "UltraSync BLUE"):
            r = p325.simulate_timecode_wifi_bt_usblan_and_airplane_hil(tc_source=src)
            self.assertFalse(r.admitted, src)
            self.assertEqual(r.errno_code, p325.EOPNOTSUPP_ERRNO)
            self.assertTrue(r.dormant_bt_timecode_link_rejected)
            self.assertEqual(r.rf_packets_transmitted, 0)

    def test_48_removed_wep_wpa_psk_ipsec_rejected_eopnotsupp(self) -> None:
        for sec in p325.REMOVED_WIFI_SECURITY:
            r = p325.simulate_timecode_wifi_bt_usblan_and_airplane_hil(
                wifi_security=sec,
                zero_rf_bench_firewall=False,
                airplane_mode="Off",
            )
            self.assertFalse(r.admitted, sec)
            self.assertEqual(r.errno_code, p325.EOPNOTSUPP_ERRNO)
            self.assertTrue(r.removed_wep_wpa_ipsec_rejected)

    def test_49_vmc_bncm1_ext_lk_admitted_with_preset_free_run(self) -> None:
        r = p325.simulate_timecode_wifi_bt_usblan_and_airplane_hil(
            tc_source="VMC-BNCM1",
            tc_make="Preset",
            tc_run="Free Run",
        )
        self.assertTrue(r.admitted)
        self.assertTrue(r.ext_lk_locked)
        self.assertEqual(r.hdmi_tc_output_default, "Off")
        self.assertTrue(r.multi_micro_usb_active)
        self.assertEqual(r.rf_packets_transmitted, 0)

    def test_50_vmc_bncm1_requires_preset_and_free_run(self) -> None:
        for make, run in (("Regenerate", "Free Run"), ("Preset", "Rec Run")):
            r = p325.simulate_timecode_wifi_bt_usblan_and_airplane_hil(
                tc_source="VMC-BNCM1",
                tc_make=make,
                tc_run=run,
            )
            self.assertFalse(r.admitted, (make, run))
            self.assertEqual(r.errno_code, p325.EINVAL_ERRNO)
            self.assertFalse(r.ext_lk_locked)

    def test_51_wifi_sku_ww728473_supports_24_and_5ghz_indoor_only(self) -> None:
        for band in ("2.4GHz", "5GHz"):
            for sec in p325.FX3_SUPPORTED_WIFI_SECURITY:
                r = p325.simulate_timecode_wifi_bt_usblan_and_airplane_hil(
                    wifi_sku=p325.WIFI_SKU_WW728473,
                    wifi_band=band,
                    wifi_security=sec,
                    airplane_mode="Off",
                    zero_rf_bench_firewall=False,
                )
                self.assertTrue(r.admitted, (band, sec))
                self.assertTrue(r.wifi_5ghz_indoor_only)
                self.assertTrue(r.wifi_available)

    def test_52_wifi_sku_ww558244_rejects_5ghz_eopnotsupp(self) -> None:
        r_5 = p325.simulate_timecode_wifi_bt_usblan_and_airplane_hil(
            wifi_sku=p325.WIFI_SKU_WW558244,
            wifi_band="5GHz",
            airplane_mode="Off",
            zero_rf_bench_firewall=False,
        )
        self.assertFalse(r_5.admitted)
        self.assertEqual(r_5.errno_code, p325.EOPNOTSUPP_ERRNO)

        r_24 = p325.simulate_timecode_wifi_bt_usblan_and_airplane_hil(
            wifi_sku=p325.WIFI_SKU_WW558244,
            wifi_band="2.4GHz",
            airplane_mode="Off",
            zero_rf_bench_firewall=False,
        )
        self.assertTrue(r_24.admitted)

    def test_53_bt_50_capacity_bounds_15_paired_2_concurrent_1_remote(self) -> None:
        r_ok = p325.simulate_timecode_wifi_bt_usblan_and_airplane_hil(
            bt_paired_devices=15,
            bt_concurrent_connections=2,
            bt_remote_count=1,
            airplane_mode="Off",
            zero_rf_bench_firewall=False,
        )
        self.assertTrue(r_ok.admitted)

        for kw in (
            {"bt_paired_devices": 16},
            {"bt_concurrent_connections": 3},
            {"bt_remote_count": 2},
        ):
            r_bad = p325.simulate_timecode_wifi_bt_usblan_and_airplane_hil(
                airplane_mode="Off",
                zero_rf_bench_firewall=False,
                **kw,
            )
            self.assertFalse(r_bad.admitted, kw)
            self.assertEqual(r_bad.errno_code, p325.EINVAL_ERRNO)

    def test_54_usblan_kernel_modules_and_connect_launch_default_off(self) -> None:
        for mod in ("cdc_ncm.ko", "r8152.ko", "ax88179_178a.ko", "asix.ko"):
            self.assertIn(mod, p325.FX3_USBLAN_KERNEL_MODULES)
        r = p325.simulate_timecode_wifi_bt_usblan_and_airplane_hil(
            usb_lan_requested=True,
            airplane_mode="On",
        )
        self.assertTrue(r.admitted)
        self.assertTrue(r.usb_lan_active)
        self.assertEqual(r.usb_lan_connect_launch, "Off")
        self.assertFalse(r.wifi_available)

    def test_55_usblan_blocks_concurrent_multi_micro_usb_and_vmcbncm1(self) -> None:
        for kw in (
            {"multi_micro_usb_active": True},
            {"tc_source": "VMC-BNCM1"},
        ):
            r = p325.simulate_timecode_wifi_bt_usblan_and_airplane_hil(
                usb_lan_requested=True,
                **kw,
            )
            self.assertFalse(r.admitted, kw)
            self.assertEqual(r.errno_code, p325.EBUSY_ERRNO)
            self.assertTrue(r.usblan_mutual_exclusion_triggered)

    def test_56_usblan_disables_concurrent_wifi_ebusy(self) -> None:
        r = p325.simulate_timecode_wifi_bt_usblan_and_airplane_hil(
            usb_lan_requested=True,
            wifi_requested=True,
            airplane_mode="Off",
            zero_rf_bench_firewall=False,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p325.EBUSY_ERRNO)
        self.assertTrue(r.usblan_mutual_exclusion_triggered)
        self.assertFalse(r.wifi_available)

    def test_57_airplane_mode_on_survives_reset_network_set_and_initialize(self) -> None:
        r = p325.simulate_timecode_wifi_bt_usblan_and_airplane_hil(
            usb_lan_requested=True,
            airplane_mode="On",
            reset_network_set_applied=True,
            initialize_applied=True,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.airplane_mode, "On")
        self.assertFalse(r.wifi_available)
        self.assertEqual(r.rf_packets_transmitted, 0)
        self.assertEqual(r.rf_nvs_mutation_bytes, 0)

    def test_58_zero_rf_bench_firewall_blocks_rf_emissions_eperm(self) -> None:
        for kw in (
            {"airplane_mode": "Off"},
            {"wifi_requested": True},
            {"bluetooth_requested": True},
        ):
            r = p325.simulate_timecode_wifi_bt_usblan_and_airplane_hil(
                zero_rf_bench_firewall=True,
                **kw,
            )
            self.assertFalse(r.admitted, kw)
            self.assertEqual(r.errno_code, p325.EPERM_ERRNO)
            self.assertEqual(r.rf_packets_transmitted, 0)

    def test_59_fx6_physical_bnc_tc_in_locks_ext_lk(self) -> None:
        r = p325.simulate_timecode_wifi_bt_usblan_and_airplane_hil(
            body_profile=p325.BODY_MODEL_FX6,
            tc_source="Physical BNC TC IN",
            tc_make="Preset",
            tc_run="Free Run",
        )
        self.assertTrue(r.admitted)
        self.assertTrue(r.ext_lk_locked)
        self.assertTrue(r.fx6_physical_bnc_tc_switch)

    def test_60_fx6_dormant_usb_timecode_and_no_bluetooth_hardware(self) -> None:
        for src in ("USB Timecode", "VMC-BNCM1"):
            r = p325.simulate_timecode_wifi_bt_usblan_and_airplane_hil(
                body_profile=p325.BODY_MODEL_FX6,
                tc_source=src,
            )
            self.assertFalse(r.admitted, src)
            self.assertEqual(r.errno_code, p325.EOPNOTSUPP_ERRNO)

        r_bt = p325.simulate_timecode_wifi_bt_usblan_and_airplane_hil(
            body_profile=p325.BODY_MODEL_FX6,
            bluetooth_requested=True,
        )
        self.assertFalse(r_bt.admitted)
        self.assertEqual(r_bt.errno_code, p325.EOPNOTSUPP_ERRNO)

    def test_61_usblan_connect_launch_on_allowed_over_usb_c(self) -> None:
        r = p325.simulate_timecode_wifi_bt_usblan_and_airplane_hil(
            usb_lan_requested=True,
            usb_lan_connect_launch="On",
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.usb_lan_connect_launch, "On")

    def test_62_fx3_internal_tc_free_run_without_ext_lk(self) -> None:
        r = p325.simulate_timecode_wifi_bt_usblan_and_airplane_hil(
            tc_source="Internal",
            tc_make="Preset",
            tc_run="Free Run",
        )
        self.assertTrue(r.admitted)
        self.assertFalse(r.ext_lk_locked)

    def test_63_fx6_physical_bnc_without_preset_free_run_not_ext_lk(self) -> None:
        r = p325.simulate_timecode_wifi_bt_usblan_and_airplane_hil(
            body_profile=p325.BODY_MODEL_FX6,
            tc_source="Physical BNC TC IN",
            tc_make="Regenerate",
            tc_run="Rec Run",
        )
        self.assertTrue(r.admitted)
        self.assertFalse(r.ext_lk_locked)

    def test_64_wifi_available_false_when_airplane_on_even_without_usblan(self) -> None:
        r = p325.simulate_timecode_wifi_bt_usblan_and_airplane_hil(
            airplane_mode="On",
            usb_lan_requested=False,
        )
        self.assertTrue(r.admitted)
        self.assertFalse(r.wifi_available)

    def test_65_invalid_wifi_security_raises(self) -> None:
        with self.assertRaises(p325.Stage68Phase325Error):
            p325.simulate_timecode_wifi_bt_usblan_and_airplane_hil(wifi_security="OPEN_NONE")

    def test_66_invalid_68c_arguments_raise(self) -> None:
        with self.assertRaises(p325.Stage68Phase325Error):
            p325.simulate_timecode_wifi_bt_usblan_and_airplane_hil(wifi_sku="WW000000")
        with self.assertRaises(p325.Stage68Phase325Error):
            p325.simulate_timecode_wifi_bt_usblan_and_airplane_hil(wifi_band="6GHz")
        with self.assertRaises(p325.Stage68Phase325Error):
            p325.simulate_timecode_wifi_bt_usblan_and_airplane_hil(usb_lan_connect_launch="Auto")
        with self.assertRaises(p325.Stage68Phase325Error):
            p325.simulate_timecode_wifi_bt_usblan_and_airplane_hil(airplane_mode="Partial")

    def test_67_fx3_paired_zero_bluetooth_off_under_zero_rf(self) -> None:
        r = p325.simulate_timecode_wifi_bt_usblan_and_airplane_hil(
            airplane_mode="On",
            bluetooth_requested=False,
        )
        self.assertTrue(r.admitted)
        self.assertFalse(r.bluetooth_enabled)

    def test_68_fx3_vmc_bncm1_disables_concurrent_usblan_first(self) -> None:
        r = p325.simulate_timecode_wifi_bt_usblan_and_airplane_hil(
            tc_source="VMC-BNCM1",
            usb_lan_requested=True,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p325.EBUSY_ERRNO)
        self.assertFalse(r.usb_lan_active)

    # ------------------------------------------------------------------
    # Sub-Model 68D — Still BULB, DRO / DRO Bracket vs Dormant Bulb Timer & Auto HDR (Tests 69..84)
    # ------------------------------------------------------------------

    def test_69_dormant_bulb_timer_rejected_eopnotsupp(self) -> None:
        r = p325.simulate_bulb_dro_and_dormant_timer_hdr_hil(bulb_timer_requested=True)
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p325.EOPNOTSUPP_ERRNO)
        self.assertTrue(r.dormant_bulb_timer_rejected)

    def test_70_dormant_auto_hdr_rejected_eopnotsupp(self) -> None:
        r = p325.simulate_bulb_dro_and_dormant_timer_hdr_hil(auto_hdr_requested=True)
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p325.EOPNOTSUPP_ERRNO)
        self.assertTrue(r.dormant_auto_hdr_rejected)

    def test_71_still_bulb_requires_manual_mechanical_shutter_single_or_self_single(self) -> None:
        for drv in ("Single Shooting", "Self-timer(Single)"):
            for ctrl in p325.EXTENDED_BULB_CONTROLLERS:
                r = p325.simulate_bulb_dro_and_dormant_timer_hdr_hil(
                    shoot_mode=p325.SHOOT_MODE_STILL,
                    exposure_mode="M",
                    shutter_type="Mechanical Shutter",
                    drive_mode=drv,
                    bulb_requested=True,
                    long_exposure_nr="On",
                    extended_bulb_controller=ctrl,
                )
                self.assertTrue(r.admitted, (drv, ctrl))
                self.assertEqual(r.effective_shutter_speed, "BULB")
                self.assertFalse(r.anti_flicker_allowed)
                self.assertTrue(r.long_exposure_nr_dark_frame)
                self.assertEqual(r.extended_bulb_controller, ctrl)

    def test_72_still_bulb_falls_back_to_30s_under_electronic_shutter(self) -> None:
        r = p325.simulate_bulb_dro_and_dormant_timer_hdr_hil(
            shoot_mode=p325.SHOOT_MODE_STILL,
            exposure_mode="M",
            shutter_type="Electronic Shutter",
            drive_mode="Single Shooting",
            bulb_requested=True,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p325.EOPNOTSUPP_ERRNO)
        self.assertTrue(r.bulb_fallback_to_30s)
        self.assertEqual(r.effective_shutter_speed, '30"')

    def test_73_still_bulb_falls_back_to_30s_under_blocked_drive_modes(self) -> None:
        for drv in p325.BULB_BLOCKED_DRIVE_MODES:
            r = p325.simulate_bulb_dro_and_dormant_timer_hdr_hil(
                shoot_mode=p325.SHOOT_MODE_STILL,
                exposure_mode="M",
                shutter_type="Mechanical Shutter",
                drive_mode=drv,
                bulb_requested=True,
            )
            self.assertFalse(r.admitted, drv)
            self.assertEqual(r.errno_code, p325.EOPNOTSUPP_ERRNO)
            self.assertTrue(r.bulb_fallback_to_30s)
            self.assertEqual(r.effective_shutter_speed, '30"')

    def test_74_still_bulb_blocked_outside_manual_exposure(self) -> None:
        for exp in ("P", "A", "S", "Intelligent Auto"):
            r = p325.simulate_bulb_dro_and_dormant_timer_hdr_hil(
                shoot_mode=p325.SHOOT_MODE_STILL,
                exposure_mode=exp,
                shutter_type="Mechanical Shutter",
                bulb_requested=True,
            )
            self.assertFalse(r.admitted, exp)
            self.assertEqual(r.errno_code, p325.EOPNOTSUPP_ERRNO)
            self.assertTrue(r.bulb_fallback_to_30s)

    def test_75_bulb_rejected_in_movie_and_sq(self) -> None:
        for sm in (p325.SHOOT_MODE_MOVIE, p325.SHOOT_MODE_SQ):
            r = p325.simulate_bulb_dro_and_dormant_timer_hdr_hil(
                shoot_mode=sm,
                exposure_mode="M",
                bulb_requested=True,
            )
            self.assertFalse(r.admitted, sm)
            self.assertEqual(r.errno_code, p325.EOPNOTSUPP_ERRNO)

    def test_76_long_exposure_nr_off_disables_dark_frame_for_bulb(self) -> None:
        r = p325.simulate_bulb_dro_and_dormant_timer_hdr_hil(
            bulb_requested=True,
            long_exposure_nr="Off",
        )
        self.assertTrue(r.admitted)
        self.assertFalse(r.long_exposure_nr_dark_frame)

    def test_77_all_dro_modes_and_dro_bracket_modes_valid(self) -> None:
        for dro in p325.FX3_DRO_MODES:
            for brk in p325.FX3_DRO_BRACKET_MODES:
                r = p325.simulate_bulb_dro_and_dormant_timer_hdr_hil(
                    dro_mode=dro,
                    dro_bracket_mode=brk,
                    picture_profile="Off",
                    hlg_still_image="Off",
                )
                self.assertTrue(r.admitted, (dro, brk))
                self.assertEqual(r.effective_dro_mode, dro)
                self.assertEqual(r.dro_bracket_mode, brk)

    def test_78_dro_forced_off_when_picture_profile_active(self) -> None:
        for pp in ("PP1", "PP10", "PP11"):
            r = p325.simulate_bulb_dro_and_dormant_timer_hdr_hil(
                picture_profile=pp,
                dro_mode="Lv5",
            )
            self.assertTrue(r.admitted, pp)
            self.assertTrue(r.dro_forced_off_by_pp)
            self.assertEqual(r.effective_dro_mode, "Off")

    def test_79_dro_forced_off_and_dro_bracket_rejected_when_hlg_still_on(self) -> None:
        r_ok = p325.simulate_bulb_dro_and_dormant_timer_hdr_hil(
            hlg_still_image="On",
            dro_mode="Lv4",
            dro_bracket_mode="Off",
        )
        self.assertTrue(r_ok.admitted)
        self.assertTrue(r_ok.dro_disabled_by_hlg)
        self.assertEqual(r_ok.effective_dro_mode, "Off")

        r_blk = p325.simulate_bulb_dro_and_dormant_timer_hdr_hil(
            hlg_still_image="On",
            dro_mode="Lv4",
            dro_bracket_mode="DRO Bracket: Hi",
        )
        self.assertFalse(r_blk.admitted)
        self.assertEqual(r_blk.errno_code, p325.EOPNOTSUPP_ERRNO)
        self.assertTrue(r_blk.dro_disabled_by_hlg)

    def test_80_dro_bracket_rejected_when_picture_profile_active(self) -> None:
        r = p325.simulate_bulb_dro_and_dormant_timer_hdr_hil(
            picture_profile="PP8",
            dro_bracket_mode="DRO Bracket: Lo",
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p325.EOPNOTSUPP_ERRNO)
        self.assertTrue(r.dro_forced_off_by_pp)

    def test_81_camera_settings_reset_restores_dro_auto_and_bracket_off(self) -> None:
        r = p325.simulate_bulb_dro_and_dormant_timer_hdr_hil(
            dro_mode="Lv5",
            dro_bracket_mode="DRO Bracket: Hi",
            camera_settings_reset_applied=True,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.effective_dro_mode, "Auto")
        self.assertEqual(r.dro_bracket_mode, "Off")

    def test_82_fx6_lacks_still_bulb_and_dro_rejected_eopnotsupp(self) -> None:
        r = p325.simulate_bulb_dro_and_dormant_timer_hdr_hil(
            body_profile=p325.BODY_MODEL_FX6,
            bulb_requested=True,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p325.EOPNOTSUPP_ERRNO)
        self.assertEqual(r.effective_dro_mode, "N/A")

    def test_83_invalid_68d_arguments_raise(self) -> None:
        with self.assertRaises(p325.Stage68Phase325Error):
            p325.simulate_bulb_dro_and_dormant_timer_hdr_hil(shutter_type="Leaf Shutter")
        with self.assertRaises(p325.Stage68Phase325Error):
            p325.simulate_bulb_dro_and_dormant_timer_hdr_hil(dro_mode="Lv6")
        with self.assertRaises(p325.Stage68Phase325Error):
            p325.simulate_bulb_dro_and_dormant_timer_hdr_hil(picture_profile="PP99")
        with self.assertRaises(p325.Stage68Phase325Error):
            p325.simulate_bulb_dro_and_dormant_timer_hdr_hil(hlg_still_image="Maybe")

    def test_84_redline_zero_fault_counters_in_payload(self) -> None:
        rep = p325.run_phase325_bright_mon_shotmark_usblan_bulb_dormant_coemulation(
            force_clean_room=True
        )
        red = rep["redlines"]
        self.assertFalse(red["bright_mon_shooting_menu_exposed"])
        self.assertFalse(red["slot1_avf_info_mutated"])
        self.assertFalse(red["persistent_emmc_writes_authorized"])
        self.assertFalse(red["hardware_live_attachment_authorized"])
        self.assertFalse(red["overall_ready_for_hardware_attach"])
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
            "dormant_lcd_brightness_auto_exposed_events",
            "dormant_divide_extract_or_ftp_cut_exposed_events",
            "dormant_bt_timecode_link_exposed_events",
            "removed_wep_wpa_ipsec_exposed_events",
            "usblan_wifi_or_multi_usb_coexist_violations",
            "dormant_bulb_timer_or_auto_hdr_exposed_events",
            "bulb_non_mech_or_cont_bypass_events",
            "post_reset_airplane_off_rf_leak_events",
            "rf_packets_transmitted",
            "rf_nvs_mutation_bytes",
            "slot1_data_sector_writes",
            "slot1_vault_shotmark_edit_mutation_bytes",
            "rsv_orphan_count",
            "wf12_00342260_hits",
            "appfw_crashes",
            "raw_firmware_bytes_leaked",
        ):
            self.assertEqual(red[zero_key], 0, zero_key)

    # ------------------------------------------------------------------
    # Standalone CLI, No Hardcoded Paths & Suite Stage 68 Wiring (Tests 85..92)
    # ------------------------------------------------------------------

    def test_85_standalone_cli_help_uses_sys_executable_and_percent_escaping(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                str(FX3_VM_DIR / "realhw_bright_mon_shotmark_usblan_bulb_dormant_coemulator.py"),
                "--help",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("100%", proc.stdout)
        self.assertIn("68/68", proc.stdout)

    def test_86_suite_cli_help_percent_escaping_works(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                str(FX3_VM_DIR / "fx3_vm_coemulation_suite.py"),
                "--help",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("68/68 Milestone", proc.stdout)
        self.assertIn("--include-stage68", proc.stdout)
        self.assertIn("--skip-stage68", proc.stdout)
        self.assertIn("--skip-phase325", proc.stdout)

    def test_87_standalone_cli_summary_and_json_modes(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = p325.main(["--self-test", "--clean-room", "--summary"])
        self.assertEqual(rc, 0)
        self.assertIn("[PASS] Phase 325 Stage 68 (68/68 Milestone)", buf.getvalue())

        buf_json = io.StringIO()
        with contextlib.redirect_stdout(buf_json):
            rc2 = p325.main(["--self-test", "--clean-room", "--json"])
        self.assertEqual(rc2, 0)
        parsed = json.loads(buf_json.getvalue())
        self.assertEqual(parsed["milestone"], "68/68")
        self.assertTrue(parsed["is_68th_stage_milestone"])
        self.assertTrue(parsed["all_checks_passed"])
        self.assertNotIn("\\x7fELF", buf_json.getvalue())

    def test_88_no_hardcoded_usr_bin_python3_in_stage68_files(self) -> None:
        mod_src = (
            FX3_VM_DIR / "realhw_bright_mon_shotmark_usblan_bulb_dormant_coemulator.py"
        ).read_text(encoding="utf-8")
        tst_src = Path(__file__).read_text(encoding="utf-8")
        forbidden = "/usr/bin/" + "python3"
        self.assertNotIn(forbidden, mod_src)
        self.assertNotIn(forbidden, tst_src)

    def test_89_suite_default_config_enables_stage68_and_full_run_contains_68_stages(self) -> None:
        cfg = suite.CoEmulationConfig()
        self.assertTrue(
            cfg.include_phase325_realhw_bright_mon_shotmark_usblan_bulb_dormant_hil
        )
        self.assertTrue(cfg.include_stage68)
        self.assertTrue(cfg.stage68_realhw_bright_mon_shotmark_usblan_bulb_dormant_hil)

        t0 = time.monotonic()
        rep = suite.run_fx3_vm_coemulation_suite(cfg)
        elapsed = time.monotonic() - t0
        self.assertTrue(rep["all_checks_passed"])
        stage_keys = [k for k in rep if re.match(r"^stage\d+_", k)]
        self.assertGreaterEqual(len(stage_keys), 68)
        s68 = rep["stage68_realhw_bright_mon_shotmark_usblan_bulb_dormant_hil"]
        self.assertTrue(s68["all_checks_passed"])
        self.assertTrue(s68["is_68th_stage_milestone"])
        self.assertEqual(s68["milestone"], "68/68")
        self.assertEqual(s68["phase_number"], 325)
        max_elapsed = 30.0 if IS_CI else 15.0
        self.assertLess(elapsed, max_elapsed)

    def test_90_suite_skip_flags_and_summary_cli_for_stage68(self) -> None:
        for flag in ("--skip-stage68", "--no-include-stage68", "--skip-phase325"):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = suite.main([*_FAST_CLI_FLAGS, flag, "--json"])
            self.assertEqual(rc, 0)
            data = json.loads(buf.getvalue())
            self.assertNotIn(
                "stage68_realhw_bright_mon_shotmark_usblan_bulb_dormant_hil",
                data,
            )
            self.assertFalse(data["config"]["include_stage68"])

        buf_sum = io.StringIO()
        with contextlib.redirect_stdout(buf_sum):
            rc_sum = suite.main([*_FAST_CLI_FLAGS, "--include-stage68", "--summary"])
        self.assertEqual(rc_sum, 0)
        self.assertIn(
            "realhw_bright_mon_shotmark_usblan_bulb_dormant_hil=CLEAN_ROOM_SYNTHETIC("
            "m68=68/68,bm_menu=0,div_byp=0,bt_tc=0,usblan=0,bulb=0,rf_tx=0,s1_wr=0,emmc_wr=0)",
            buf_sum.getvalue(),
        )

    def test_91_suite_tamper_bright_mon_bt_tc_usblan_or_bulb_detected(self) -> None:
        for attr, val in (
            ("BRIGHT_MON_SHOOTING_MENU_EXPOSED", True),
            ("DORMANT_BT_TIMECODE_LINK_EXPOSED_EVENTS", 1),
            ("USBLAN_WIFI_OR_MULTI_USB_COEXIST_VIOLATIONS", 1),
            ("BULB_NON_MECH_OR_CONT_BYPASS_EVENTS", 1),
        ):
            with unittest.mock.patch.object(p325, attr, val):
                rep = suite.run_fx3_vm_coemulation_suite(
                    suite.CoEmulationConfig(**_fast_suite_kwargs())
                )
                self.assertFalse(rep["all_checks_passed"], attr)

    def test_92_suite_tamper_rf_tx_or_slot1_vault_detected(self) -> None:
        for attr, val in (
            ("RF_PACKETS_TRANSMITTED", 1),
            ("SLOT1_AVF_INFO_MUTATED", True),
            ("SLOT1_VAULT_SHOTMARK_EDIT_MUTATION_BYTES", 64),
        ):
            with unittest.mock.patch.object(p325, attr, val):
                rep = suite.run_fx3_vm_coemulation_suite(
                    suite.CoEmulationConfig(**_fast_suite_kwargs())
                )
                self.assertFalse(rep["all_checks_passed"], attr)


if __name__ == "__main__":
    unittest.main()
