#!/usr/bin/env python3
"""Unit tests for Phase 350 (Stage 77 — 77/77 Full-Board VM Co-Emulation Stages!):
Real-Hardware `ILME-FX3 Ver. 7.02` vs `ILME-FX6 Ver. 6.01` Wave-67:
- 77A: `Setup -> [Setup Option] -> [Auto Pixel Mapping]` (Reset-immune,
  `[Initialize]` -> `On`) & `[Pixel Mapping]` (`FUNC_execute_manual_pixel_mapping`,
  `SYSTEM_MODE_OPTION_MANUAL_PIXEL_MAPPING`, lens-cap `_g 0x63f1`, auto-reboot,
  `INFRA_NOTIFY_BATTERY_CHECK_FOR_PIXEL_MAPPING`), Silent-Mode Target Function
  default `Off` (`Not Target`) firing mechanical shutter sound via
  `vdf_set_shutter_mute_by_pixel_mapping` unless explicitly set `On`, Sony ELF typos
  (`BKID_APP_setting_notification_for_pixel_mappinng`,
  `BKID_APP_pixel_mapping_excuted_status`), dormant `[Pixel Map. Notification]` &
  `[Shutter When Pwr OFF]` vs `ILME-FX6 Ver. 6.01` `Technical > APR > Execute/Cancel`
  (`PIXEL_MAPPING_RESULT_LIGHT_DETECTED` / `INVALID_TEMPERATURE`) & 100%% dormant
  CMOS `ABB` (`auto_black_balance`),
- 77B: `Setup -> [Monitor]` (exact 3 Reset-immune items: `[Monitor Brightness]`
  `Manual -2..+2` / `Sunny Weather` `INFRA_NOTIFY_UPM_LCD_BRIGHTNESS_LIMIT`,
  `[Display Quality]` `Standard`/`High` thermal lock, `[Monitor Flip Direction]`
  `Auto`/`Horizontal Flip`/`180 Degree Flip`/`No Flip`), zero `[Finder/Monitor]`
  group & 4 dormant EVF items (`Finder/Monitor Sel.`, `Viewfinder Bright.`,
  `Viewfinder Color Temp.`, `Finder Frame Rate`) vs `ILME-FX6 Ver. 6.01`
  `Monitoring > VF Setting` (`Brightness 1..15` def `8`, `Color Mode` `Color/B&W`),
  `VF Adjust` / `VF Mode` & physical `MIRROR` (`Off/B/T/ROT`) with 0
  `Backlight/Contrast/Chroma/Color Temp.` submenus,
- 77C: Still `P/A/S/M`-Only `[Recall Custom hold 1-3]` (`11` slots
  `is_checked_recall_custom_hold0..10`, zero independent `White Balance`, excludes
  Self-timer, Reset-immune, `CAMSET*.DAT`, `[AF On]` / `[Eye AF]` / Still `AF-C`
  `[Tracking On]`) vs `ILME-FX6 Ver. 6.01` `Push AF` / `Push AGC` / `Push Auto Iris`
  lockouts & dormant `High/Low Key` (`FX6 ns2 0x4b25`),
- 77D: `Setup -> [External Output]` Reset-immune HDMI Matrix (`[HDMI Resolution]`,
  `[HDMI Output Settings]` `Rec. Media dur HDMI Output` default `On` & forced `On` in
  `S&Q`, `Output Resolution` downscaled to `1080p` under `Log`/`PPLUT1..4`,
  `4K Output Set.(HDMI Only)` `24.00p` reboot + `hdmi_4k_outpute` typo, `RAW Output`,
  `Time Code Output`, `[REC Control]` hard-requiring `Time Code Output = On`,
  `4ch Audio Output`, `[HDMI Info. Display]`, `[CTRL FOR HDMI]` `ctrl_for_hmdi` typo,
  dormant `24p/60p Output` & `4K/2K Output`), Tier-0 `Slot 1` `EROFS=30` Firewall,
  and `ILME-FX6 Ver. 6.01` dual `12G-SDI + HDMI` (`RAW(HDMI)` `4240x2392` forcing
  `SDI` down to `1920x1080P/i`, `SDI/HDMI Remote I/F` vs `Parallel Rec`)
HIL (100 four-mode tests).
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
if str(FX3_VM_DIR) not in sys.path:
    sys.path.insert(0, str(FX3_VM_DIR))

import fx3_vm_coemulation_suite as suite  # noqa: E402
import realhw_pixelmap_apr_monitor_vfadjust_customhold_hdmi_reccontrol_coemulator as p350  # noqa: E402

IS_CI = os.environ.get("GITHUB_ACTIONS", "").lower() == "true"


def _fast_suite_kwargs(**overrides: object) -> dict:
    """Fast config skipping unrelated optional stages 4..76 for Stage 77 isolation tests."""
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
        include_stage68=False,
        include_stage69=False,
        include_stage70=False,
        include_stage71=False,
        include_stage72=False,
        include_stage73=False,
        include_stage74=False,
        include_stage75=False,
        include_stage76=False,
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
    "--skip-stage68",
    "--skip-stage69",
    "--skip-stage70",
    "--skip-stage71",
    "--skip-stage72",
    "--skip-stage73",
    "--skip-stage74",
    "--skip-stage75",
    "--skip-stage76",
]


class TestRealHwStage77PixelMapAprMonitorVfAdjustCustomHoldHdmiRecControl(unittest.TestCase):
    # ------------------------------------------------------------------
    # Donor Audit, Bounded O_RDONLY & 4-Mode Fallback Tests (Tests 01..15)
    # ------------------------------------------------------------------

    def test_01_milestone_constants_77_of_77(self) -> None:
        self.assertEqual(p350.PHASE_NUMBER, 350)
        self.assertEqual(p350.STAGE_INDEX, 77)
        self.assertEqual(p350.STAGE_TOTAL, 77)
        self.assertEqual(p350.MILESTONE_LABEL, "77/77")
        self.assertTrue(p350.IS_77TH_STAGE_MILESTONE)
        self.assertEqual(len(p350.DONOR_RELPATHS), 12)
        self.assertEqual(len(p350.EXPECTED_DONOR_BYTES), 12)
        self.assertEqual(len(p350.EXPECTED_COMPACT_DONOR_SHA256), 9)
        self.assertEqual(len(p350.EXPECTED_LARGE_HEAD4K_SHA256), 3)
        self.assertEqual(len(p350.LARGE_DONOR_WINDOWS), 3)

    def test_02_hard_safety_and_wave67_redlines_locked(self) -> None:
        self.assertTrue(p350.P8_CP_MUTATION_FORBIDDEN)
        self.assertTrue(p350.CNFLASHA_USERSPACE_WRITE_BLOCKED)
        self.assertFalse(p350.PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(p350.EMMC_WRITES_AUTHORIZED)
        self.assertFalse(p350.CROSS_MODEL_FLASH_AUTHORIZED)
        self.assertFalse(p350.HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        self.assertFalse(p350.OVERALL_READY_FOR_HARDWARE_ATTACH)
        self.assertFalse(p350.ISP_WRITE_AUTHORIZED)
        self.assertFalse(p350.SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(p350.EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        self.assertFalse(p350.SLOT1_AVF_INFO_MUTATED)
        self.assertEqual(p350.SLOT1_DATA_SECTOR_WRITES, 0)
        self.assertEqual(p350.EMMC_NFLASHA_WRITE_COUNT, 0)
        self.assertEqual(p350.RAW_FIRMWARE_BYTES_LEAKED, 0)
        self.assertEqual(p350.PIXEL_MAPPING_AUTO_RESET_WIPE_EVENTS, 0)
        self.assertFalse(p350.SILENT_AUTO_PIXEL_MAPPING_DEFAULT_MUTE_SHUTTER)
        self.assertTrue(p350.PIXEL_MAPPINNG_TYPO_MATCHED)
        self.assertTrue(p350.PIXEL_MAPPING_EXCUTED_TYPO_MATCHED)
        self.assertEqual(p350.DORMANT_PIXEL_MAP_NOTIFICATION_EXPOSED_EVENTS, 0)
        self.assertEqual(p350.DORMANT_SHUTTER_WHEN_PWR_OFF_EXPOSED_EVENTS, 0)
        self.assertEqual(p350.FX6_ABB_MENU_EXPOSED_EVENTS, 0)
        self.assertEqual(p350.FX3_MONITOR_GROUP_ACTIVE_ITEMS_COUNT, 3)
        self.assertEqual(p350.DORMANT_FINDER_MONITOR_GROUP_EXPOSED_EVENTS, 0)
        self.assertEqual(p350.DORMANT_EVF_MENUS_EXPOSED_EVENTS, 0)
        self.assertEqual(p350.FX6_VF_BRIGHTNESS_DEFAULT, 8)
        self.assertEqual(p350.RECALL_CUSTOM_HOLD_SLOTS_COUNT, 3)
        self.assertEqual(p350.RECALL_CUSTOM_HOLD_CHECKBOX_PARAMS_COUNT, 11)
        self.assertEqual(p350.RECALL_CUSTOM_HOLD_WHITE_BALANCE_INDEPENDENT_SLOTS, 0)
        self.assertEqual(p350.FX6_RECALL_CUSTOM_HOLD_EXPOSED_EVENTS, 0)
        self.assertEqual(p350.FX6_DORMANT_HIGH_LOW_KEY_EXPOSED_EVENTS, 0)
        self.assertTrue(p350.HDMI_4K_OUTPUTE_TYPO_MATCHED)
        self.assertTrue(p350.CTRL_FOR_HMDI_TYPO_MATCHED)
        self.assertEqual(p350.HDMI_REC_MEDIA_SLOT1_EROFS_BYPASS_EVENTS, 0)

    def test_03_clean_room_test_mode_both_env_vars(self) -> None:
        self.assertFalse(p350.clean_room_test_mode(env={}))
        self.assertTrue(p350.clean_room_test_mode(env={p350.ENV_FORCE_CLEAN_ROOM: "1"}))
        self.assertTrue(p350.clean_room_test_mode(env={p350.ENV_CLEAN_ROOM_TEST: "1"}))
        self.assertTrue(p350.clean_room_test_mode(force_clean_room=True, env={}))
        self.assertFalse(
            p350.clean_room_test_mode(
                force_clean_room=False,
                env={p350.ENV_FORCE_CLEAN_ROOM: "1", p350.ENV_CLEAN_ROOM_TEST: "1"},
            )
        )

    def test_04_resolve_mac_work_root_and_donorless_fallback(self) -> None:
        self.assertIsNone(p350.resolve_mac_work_root(work_root=None, env={}))
        self.assertIsNone(
            p350.resolve_mac_work_root(work_root="/nonexistent/wave67/path", env={})
        )
        self.assertIsNone(
            p350.resolve_mac_work_root(
                env={p350.ENV_MAC_WORK_ROOT: p350.CLEAN_ROOM_SENTINEL_DIRNAME}
            )
        )
        self.assertIsNone(
            p350.resolve_mac_work_root(
                env={p350.ENV_MAC_ROOT: p350.CLEAN_ROOM_SENTINEL_DIRNAME}
            )
        )
        self.assertFalse(
            p350._local_donors_available(
                env={p350.ENV_MAC_WORK_ROOT: p350.CLEAN_ROOM_SENTINEL_DIRNAME}
            )
        )
        with tempfile.TemporaryDirectory() as td:
            with unittest.mock.patch.object(p350, "DEFAULT_REPO_ROOT", Path(td)):
                with unittest.mock.patch.object(p350, "LEGACY_MAC_ROOT", Path(td) / "none"):
                    self.assertIsNone(p350.resolve_mac_work_root(env={}))
                    self.assertFalse(p350._local_donors_available(env={}))
                    rep = p350.run_phase350_pixelmap_apr_monitor_vfadjust_customhold_hdmi_reccontrol_coemulation(
                        env={}
                    )
                    self.assertTrue(rep["all_checks_passed"])
                    self.assertEqual(rep["source_mode"], p350.SOURCE_MODE_CLEAN_ROOM)
                    self.assertEqual(rep["redlines"]["raw_firmware_bytes_leaked"], 0)

    def test_05_clean_room_donor_audit_all_12_contracts(self) -> None:
        for env_key in (p350.ENV_FORCE_CLEAN_ROOM, p350.ENV_CLEAN_ROOM_TEST):
            audit = p350.inspect_phase350_wave67_donors(env={env_key: "1"})
            self.assertEqual(audit.source_mode, p350.SOURCE_MODE_CLEAN_ROOM)
            self.assertEqual(audit.donor_access_mode, p350.DONOR_ACCESS_MODE)
            self.assertEqual(audit.bounded_window_max_bytes, 4096)
            self.assertEqual(audit.donors_checked, 12)
            self.assertEqual(audit.donors_verified, 12)
            self.assertTrue(audit.all_contracts_verified)
            self.assertEqual(audit.raw_firmware_bytes_leaked, 0)

    def test_06_local_donor_o_rdonly_cold_audit_under_250ms(self) -> None:
        if not p350._local_donors_available():
            self.skipTest("Local Mac/work donors unavailable in clean-room environment")
        t0 = time.perf_counter()
        audit = p350.inspect_phase350_wave67_donors(force_clean_room=False)
        elapsed_s = time.perf_counter() - t0
        self.assertEqual(audit.source_mode, p350.SOURCE_MODE_LOCAL_DONOR)
        self.assertEqual(audit.donors_checked, 12)
        self.assertEqual(audit.donors_verified, 12)
        self.assertTrue(audit.all_contracts_verified)
        self.assertEqual(audit.raw_firmware_bytes_leaked, 0)
        self.assertLess(elapsed_s, 0.25)

    def test_07_compact_donor_tokens_across_en_sc_tc_ja_saveload_fx6(self) -> None:
        self.assertEqual(p350.EXPECTED_DONOR_BYTES["fx3_string_en_f"], 373_820)
        self.assertEqual(p350.EXPECTED_DONOR_BYTES["fx3_string_en_g"], 69_600)
        self.assertEqual(p350.EXPECTED_DONOR_BYTES["fx3_saveload"], 18_760)
        self.assertEqual(p350.EXPECTED_DONOR_BYTES["fx6_string_en"], 118_208)
        self.assertEqual(p350.EXPECTED_DONOR_BYTES["fx6_string_en_2"], 118_676)
        for tok in (
            b"Auto Pixel Mapping",
            b"Pixel Mapping",
            b"Not Target",
            b"Pixel Map. Notification",
            b"Sunny Weather",
            b"Display Quality",
            b"Monitor Flip Direction",
            b"Finder/Monitor Sel.",
            b"Viewfinder Bright.",
            b"Recall Custom hold 1",
            b"HDMI Resolution",
            b"Rec. Media dur HDMI Output",
            b"Off(HDMI Only)",
            b"4K Output Set.(HDMI Only)",
            b"Time Code Output",
            b"REC Control",
            b"4ch Audio Output",
            b"24p/60p Output",
        ):
            self.assertIn(tok, p350.COMPACT_DONOR_TOKENS["fx3_string_en_f"])
        self.assertIn(b"CTRL FOR HDMI", p350.COMPACT_DONOR_TOKENS["fx3_string_en"])
        self.assertIn(b"Attach the lens cap", p350.COMPACT_DONOR_TOKENS["fx3_string_en_g"])
        self.assertIn(b"VF Adjust", p350.COMPACT_DONOR_TOKENS["fx6_string_en"])
        self.assertIn(b"VF Setting", p350.COMPACT_DONOR_TOKENS["fx6_string_en_2"])

    def test_08_large_donor_elf_and_bk4_tokens_and_exact_typos(self) -> None:
        fx3_elf_tokens = [tok for _, _, tok in p350.LARGE_DONOR_WINDOWS["fx3_appfw"]]
        for expected in (
            b"FUNC_execute_manual_pixel_mapping",
            b"SYSTEM_MODE_OPTION_MANUAL_PIXEL_MAPPING",
            b"INFRA_NOTIFY_BATTERY_CHECK_FOR_PIXEL_MAPPING",
            b"vdf_set_shutter_mute_by_pixel_mapping",
            b"BKID_APP_setting_notification_for_pixel_mappinng",
            b"BKID_APP_pixel_mapping_excuted_status",
            b"INFRA_NOTIFY_UPM_LCD_BRIGHTNESS_LIMIT",
            b"BKID_APP_setting_finder_monitor",
            b"BKID_APP_setting_viewfinder_bright",
            b"BKID_APP_setting_evf_adjustment",
            b"BKID_APP_setting_finder_framerate",
            b"is_checked_recall_custom_hold0",
            b"is_checked_recall_custom_hold10",
            b"PRM_HAITA_hdmi_4k_outpute_apsc_restriction",
            b"BKID_APP_setting_ctrl_for_hmdi",
        ):
            self.assertIn(expected, fx3_elf_tokens)
        fx6_elf_tokens = [tok for _, _, tok in p350.LARGE_DONOR_WINDOWS["fx6_appfw"]]
        self.assertIn(b"procam_msg_confirm_execute_apr_controller", fx6_elf_tokens)
        self.assertIn(b"PIXEL_MAPPING_RESULT_LIGHT_DETECTED", fx6_elf_tokens)
        self.assertIn(b"PIXEL_MAPPING_RESULT_INVALID_TEMPERATURE", fx6_elf_tokens)
        self.assertIn(b"auto_black_balance", fx6_elf_tokens)
        self.assertIn(b"setting_evf_adjustment_t", fx6_elf_tokens)
        self.assertIn(b"ASSIGNABLE_SWITCH_PUSH_AF_MODE", fx6_elf_tokens)

    def test_09_bounded_pread_window_strictly_4096_cap_and_o_rdonly(self) -> None:
        self.assertEqual(p350.BOUNDED_WINDOW_MAX_BYTES, 4096)
        self.assertEqual(p350.DONOR_ACCESS_MODE, "O_RDONLY")
        with tempfile.NamedTemporaryFile(delete=False) as tf:
            tf.write(b"Z" * 8192)
            p = Path(tf.name)
        try:
            with self.assertRaises(p350.Stage77Phase350Error):
                p350._read_bounded_window_o_rdonly(p, 0, 4097)
            with self.assertRaises(p350.Stage77Phase350Error):
                p350._read_bounded_window_o_rdonly(p, 0, 0)
            chunk = p350._read_bounded_window_o_rdonly(p, 0, 4096)
            self.assertEqual(len(chunk), 4096)
        finally:
            p.unlink()

    def test_10_clean_room_synthetic_mode_makes_zero_file_opens(self) -> None:
        with unittest.mock.patch("os.open", side_effect=AssertionError("os.open forbidden")):
            audit = p350.inspect_phase350_wave67_donors(force_clean_room=True)
            self.assertTrue(audit.all_contracts_verified)
            self.assertEqual(audit.source_mode, p350.SOURCE_MODE_CLEAN_ROOM)
            for art in audit.artifacts.values():
                self.assertEqual(art.source_mode, p350.SOURCE_MODE_CLEAN_ROOM)
                self.assertTrue(art.all_tokens_matched)
                self.assertEqual(art.raw_firmware_bytes_leaked, 0)

    def test_11_audit_json_contains_zero_raw_firmware_bytes(self) -> None:
        rep = p350.run_phase350_pixelmap_apr_monitor_vfadjust_customhold_hdmi_reccontrol_coemulation(
            force_clean_room=True
        )
        dumped = json.dumps(rep)
        self.assertNotIn("\\x7fELF", dumped)
        self.assertNotIn("7f454c46", dumped.lower())
        self.assertEqual(rep["redlines"]["raw_firmware_bytes_leaked"], 0)

    def test_12_deterministic_digest_reproducible_across_runs(self) -> None:
        r1 = p350.run_phase350_pixelmap_apr_monitor_vfadjust_customhold_hdmi_reccontrol_coemulation(
            force_clean_room=True
        )
        r2 = p350.run_phase350_pixelmap_apr_monitor_vfadjust_customhold_hdmi_reccontrol_coemulation(
            force_clean_room=True
        )
        self.assertEqual(r1["audit_digest_sha256"], r2["audit_digest_sha256"])
        self.assertEqual(len(r1["audit_digest_sha256"]), 64)

    def test_13_strip_wall_clock_removes_elapsed_seconds_recursively(self) -> None:
        sample = {
            "a": 1,
            "elapsed_seconds": 0.42,
            "nested": [{"elapsed_seconds": 9.9, "keep": "ok"}],
        }
        stripped = p350._strip_wall_clock(sample)
        self.assertNotIn("elapsed_seconds", stripped)
        self.assertNotIn("elapsed_seconds", stripped["nested"][0])
        self.assertEqual(stripped["nested"][0]["keep"], "ok")

    def test_14_all_4_runner_modes_work_root_variants_pass(self) -> None:
        modes = [
            p350.run_phase350_pixelmap_apr_monitor_vfadjust_customhold_hdmi_reccontrol_coemulation(
                work_root=None
            ),
            p350.run_phase350_pixelmap_apr_monitor_vfadjust_customhold_hdmi_reccontrol_coemulation(
                work_root="/nonexistent/wave67/donor/root"
            ),
            p350.run_phase350_pixelmap_apr_monitor_vfadjust_customhold_hdmi_reccontrol_coemulation(
                env={p350.ENV_CLEAN_ROOM_TEST: "1"}
            ),
            p350.run_phase350_pixelmap_apr_monitor_vfadjust_customhold_hdmi_reccontrol_coemulation(
                env={p350.ENV_FORCE_CLEAN_ROOM: "1"}
            ),
        ]
        for rep in modes:
            self.assertTrue(rep["all_checks_passed"])
            self.assertEqual(rep["source_mode"], p350.SOURCE_MODE_CLEAN_ROOM)
            self.assertEqual(rep["milestone"], "77/77")

    def test_15_donor_local_vs_clean_room_both_pass_when_donors_present(self) -> None:
        if not p350._local_donors_available():
            self.skipTest("Local Mac/work donors unavailable in clean-room environment")
        rep_local = p350.run_phase350_pixelmap_apr_monitor_vfadjust_customhold_hdmi_reccontrol_coemulation(
            force_clean_room=False
        )
        rep_clean = p350.run_phase350_pixelmap_apr_monitor_vfadjust_customhold_hdmi_reccontrol_coemulation(
            force_clean_room=True
        )
        self.assertTrue(rep_local["all_checks_passed"])
        self.assertTrue(rep_clean["all_checks_passed"])
        self.assertEqual(rep_local["source_mode"], p350.SOURCE_MODE_LOCAL_DONOR)
        self.assertEqual(rep_clean["source_mode"], p350.SOURCE_MODE_CLEAN_ROOM)

    # ------------------------------------------------------------------
    # Sub-Model 77A: Pixel Mapping & Auto Pixel Mapping vs FX6 APR & ABB (16..37)
    # ------------------------------------------------------------------

    def test_16_77a_silent_mode_default_still_fires_shutter_during_auto_pixel_mapping(self) -> None:
        r = p350.simulate_pixel_mapping_silent_shutter_and_fx6_apr_abb_hil(
            operation="auto_poweroff",
            auto_pixel_mapping="On",
            silent_mode="On",
            silent_target_auto_pixel_mapping="Off",
        )
        self.assertTrue(r.admitted)
        self.assertTrue(r.auto_poweroff_executed)
        self.assertTrue(r.mechanical_shutter_sound_emitted)
        self.assertEqual(r.effective_silent_target_auto_pixel_mapping, "Off")

    def test_17_77a_silent_mode_target_on_mutes_shutter_during_auto_pixel_mapping(self) -> None:
        r = p350.simulate_pixel_mapping_silent_shutter_and_fx6_apr_abb_hil(
            operation="auto_poweroff",
            auto_pixel_mapping="On",
            silent_mode="On",
            silent_target_auto_pixel_mapping="On",
        )
        self.assertTrue(r.admitted)
        self.assertTrue(r.auto_poweroff_executed)
        self.assertFalse(r.mechanical_shutter_sound_emitted)

    def test_18_77a_camera_settings_reset_immune_auto_pixel_mapping_but_resets_silent_target(self) -> None:
        r = p350.simulate_pixel_mapping_silent_shutter_and_fx6_apr_abb_hil(
            operation="auto_poweroff",
            auto_pixel_mapping="Off",
            silent_mode="On",
            silent_target_auto_pixel_mapping="On",
            camera_settings_reset_applied=True,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.effective_auto_pixel_mapping, "Off")
        self.assertFalse(r.auto_pixel_mapping_resettable)
        self.assertEqual(r.effective_silent_mode, "Off")
        self.assertEqual(r.effective_silent_target_auto_pixel_mapping, "Off")
        self.assertTrue(r.silent_target_resettable)
        self.assertFalse(r.auto_poweroff_executed)
        self.assertTrue(r.manual_every_3_days_advisory)

    def test_19_77a_initialize_restores_auto_pixel_mapping_to_on(self) -> None:
        r = p350.simulate_pixel_mapping_silent_shutter_and_fx6_apr_abb_hil(
            operation="auto_poweroff",
            auto_pixel_mapping="Off",
            silent_mode="On",
            silent_target_auto_pixel_mapping="On",
            initialize_applied=True,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.effective_auto_pixel_mapping, "On")
        self.assertEqual(r.effective_silent_mode, "Off")
        self.assertEqual(r.effective_silent_target_auto_pixel_mapping, "Off")
        self.assertTrue(r.auto_poweroff_executed)
        self.assertTrue(r.mechanical_shutter_sound_emitted)

    def test_20_77a_manual_pixel_mapping_triggers_auto_reboot_when_shielded(self) -> None:
        r = p350.simulate_pixel_mapping_silent_shutter_and_fx6_apr_abb_hil(
            operation="manual_pixel_mapping",
            lens_cap_light_shielded=True,
            battery_sufficient=True,
        )
        self.assertTrue(r.admitted)
        self.assertTrue(r.manual_executed)
        self.assertTrue(r.auto_reboot_triggered)
        self.assertTrue(r.mechanical_shutter_sound_emitted)

    def test_21_77a_manual_pixel_mapping_fails_without_lens_cap_light_shield(self) -> None:
        r = p350.simulate_pixel_mapping_silent_shutter_and_fx6_apr_abb_hil(
            operation="manual_pixel_mapping",
            lens_cap_light_shielded=False,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p350.EINVAL_ERRNO)
        self.assertFalse(r.manual_executed)
        self.assertFalse(r.auto_reboot_triggered)

    def test_22_77a_battery_gate_blocks_manual_and_auto_pixel_mapping(self) -> None:
        for op in ("manual_pixel_mapping", "auto_poweroff"):
            r = p350.simulate_pixel_mapping_silent_shutter_and_fx6_apr_abb_hil(
                operation=op,
                auto_pixel_mapping="On",
                battery_sufficient=False,
            )
            self.assertFalse(r.admitted, op)
            self.assertEqual(r.errno_code, p350.EPERM_ERRNO)
            self.assertIn("INFRA_NOTIFY_BATTERY_CHECK_FOR_PIXEL_MAPPING", r.reason)

    def test_23_77a_battery_low_does_not_fail_when_auto_pixel_mapping_off(self) -> None:
        r = p350.simulate_pixel_mapping_silent_shutter_and_fx6_apr_abb_hil(
            operation="auto_poweroff",
            auto_pixel_mapping="Off",
            battery_sufficient=False,
        )
        self.assertTrue(r.admitted)
        self.assertFalse(r.auto_poweroff_executed)
        self.assertTrue(r.manual_every_3_days_advisory)

    def test_24_77a_exact_sony_firmware_typos_recorded(self) -> None:
        r = p350.simulate_pixel_mapping_silent_shutter_and_fx6_apr_abb_hil(
            operation="auto_poweroff"
        )
        self.assertEqual(
            r.notification_typo_symbol,
            "BKID_APP_setting_notification_for_pixel_mappinng",
        )
        self.assertEqual(
            r.executed_status_typo_symbol,
            "BKID_APP_pixel_mapping_excuted_status",
        )

    def test_25_77a_dormant_pixel_map_notification_and_shutter_when_pwr_off_blocked(self) -> None:
        for op in ("dormant_pixel_map_notification", "dormant_shutter_when_pwr_off"):
            r = p350.simulate_pixel_mapping_silent_shutter_and_fx6_apr_abb_hil(operation=op)
            self.assertFalse(r.admitted, op)
            self.assertEqual(r.errno_code, p350.EOPNOTSUPP_ERRNO)
            self.assertFalse(r.dormant_pixel_map_notification_exposed)
            self.assertFalse(r.dormant_shutter_when_pwr_off_exposed)

    def test_26_77a_fx3_rejects_fx6_apr_and_abb_operations(self) -> None:
        for op in ("fx6_apr_execute", "fx6_apr_cancel", "fx6_abb_menu"):
            r = p350.simulate_pixel_mapping_silent_shutter_and_fx6_apr_abb_hil(
                body_profile=p350.BODY_MODEL_FX3,
                fw_version=p350.FW_VER_702,
                operation=op,
            )
            self.assertFalse(r.admitted)
            self.assertEqual(r.errno_code, p350.EOPNOTSUPP_ERRNO)

    def test_27_77a_fx6_apr_execute_requires_both_lens_cap_and_black_cloth(self) -> None:
        r_ok = p350.simulate_pixel_mapping_silent_shutter_and_fx6_apr_abb_hil(
            body_profile=p350.BODY_MODEL_FX6,
            fw_version=p350.FW_VER_601,
            operation="fx6_apr_execute",
            lens_cap_light_shielded=True,
            black_cloth_shielded=True,
            temperature_valid=True,
        )
        self.assertTrue(r_ok.admitted)
        self.assertTrue(r_ok.fx6_apr_executed)
        self.assertFalse(r_ok.fx6_abb_menu_exposed)
        self.assertEqual(r_ok.fx6_result_code, "PIXEL_MAPPING_RESULT_OK")

        for cap, cloth in ((False, True), (True, False)):
            r_fail = p350.simulate_pixel_mapping_silent_shutter_and_fx6_apr_abb_hil(
                body_profile=p350.BODY_MODEL_FX6,
                fw_version=p350.FW_VER_601,
                operation="fx6_apr_execute",
                lens_cap_light_shielded=cap,
                black_cloth_shielded=cloth,
            )
            self.assertFalse(r_fail.admitted)
            self.assertEqual(r_fail.errno_code, p350.EINVAL_ERRNO)
            self.assertEqual(r_fail.fx6_result_code, "PIXEL_MAPPING_RESULT_LIGHT_DETECTED")

    def test_28_77a_fx6_apr_invalid_temperature_rejected(self) -> None:
        r = p350.simulate_pixel_mapping_silent_shutter_and_fx6_apr_abb_hil(
            body_profile=p350.BODY_MODEL_FX6,
            fw_version=p350.FW_VER_601,
            operation="fx6_apr_execute",
            lens_cap_light_shielded=True,
            black_cloth_shielded=True,
            temperature_valid=False,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p350.EINVAL_ERRNO)
        self.assertEqual(r.fx6_result_code, "PIXEL_MAPPING_RESULT_INVALID_TEMPERATURE")

    def test_29_77a_fx6_apr_cancel_succeeds(self) -> None:
        r = p350.simulate_pixel_mapping_silent_shutter_and_fx6_apr_abb_hil(
            body_profile=p350.BODY_MODEL_FX6,
            fw_version=p350.FW_VER_601,
            operation="fx6_apr_cancel",
        )
        self.assertTrue(r.admitted)
        self.assertFalse(r.fx6_apr_executed)
        self.assertEqual(r.fx6_result_code, "APR_CANCELED")

    def test_30_77a_fx6_cmos_abb_menu_100_percent_dormant(self) -> None:
        r = p350.simulate_pixel_mapping_silent_shutter_and_fx6_apr_abb_hil(
            body_profile=p350.BODY_MODEL_FX6,
            fw_version=p350.FW_VER_601,
            operation="fx6_abb_menu",
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p350.EOPNOTSUPP_ERRNO)
        self.assertFalse(r.fx6_abb_menu_exposed)

    def test_31_77a_fx6_rejects_fx3_auto_and_manual_pixel_mapping(self) -> None:
        for op in ("auto_poweroff", "manual_pixel_mapping"):
            r = p350.simulate_pixel_mapping_silent_shutter_and_fx6_apr_abb_hil(
                body_profile=p350.BODY_MODEL_FX6,
                fw_version=p350.FW_VER_601,
                operation=op,
            )
            self.assertFalse(r.admitted)
            self.assertEqual(r.errno_code, p350.EOPNOTSUPP_ERRNO)

    def test_32_77a_auto_pixel_mapping_on_silent_off_fires_shutter(self) -> None:
        r = p350.simulate_pixel_mapping_silent_shutter_and_fx6_apr_abb_hil(
            operation="auto_poweroff",
            auto_pixel_mapping="On",
            silent_mode="Off",
            silent_target_auto_pixel_mapping="On",
        )
        self.assertTrue(r.admitted)
        self.assertTrue(r.mechanical_shutter_sound_emitted)

    def test_33_77a_reset_with_auto_pixel_mapping_on_preserves_on_and_resets_target(self) -> None:
        r = p350.simulate_pixel_mapping_silent_shutter_and_fx6_apr_abb_hil(
            operation="auto_poweroff",
            auto_pixel_mapping="On",
            silent_mode="On",
            silent_target_auto_pixel_mapping="On",
            camera_settings_reset_applied=True,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.effective_auto_pixel_mapping, "On")
        self.assertEqual(r.effective_silent_target_auto_pixel_mapping, "Off")
        self.assertTrue(r.mechanical_shutter_sound_emitted)

    def test_34_77a_pillar_a_payload_fields_verified(self) -> None:
        rep = p350.run_phase350_pixelmap_apr_monitor_vfadjust_customhold_hdmi_reccontrol_coemulation(
            force_clean_room=True
        )
        pa = rep["pillar_a_pixelmap_silent_shutter_fx6_apr_abb_hil"]
        self.assertTrue(pa["passed"])
        self.assertTrue(pa["silent_default_shutter"]["mechanical_shutter_sound_emitted"])
        self.assertFalse(pa["silent_target_on_muted"]["mechanical_shutter_sound_emitted"])
        self.assertEqual(pa["reset_immune"]["effective_auto_pixel_mapping"], "Off")
        self.assertTrue(pa["manual_reboot"]["auto_reboot_triggered"])
        self.assertTrue(pa["fx6_apr_execute"]["fx6_apr_executed"])

    def test_35_77a_auto_poweroff_battery_sufficient_no_reboot(self) -> None:
        r = p350.simulate_pixel_mapping_silent_shutter_and_fx6_apr_abb_hil(
            operation="auto_poweroff",
            auto_pixel_mapping="On",
            battery_sufficient=True,
        )
        self.assertTrue(r.admitted)
        self.assertTrue(r.auto_poweroff_executed)
        self.assertFalse(r.auto_reboot_triggered)

    def test_36_77a_invalid_inputs_raise_stage77_error(self) -> None:
        for bad in (
            dict(body_profile="FX30"),
            dict(fw_version="1.00"),
            dict(operation="bad_op"),
            dict(auto_pixel_mapping="Maybe"),
            dict(silent_mode="Auto"),
            dict(silent_target_auto_pixel_mapping="Target"),
        ):
            with self.assertRaises(p350.Stage77Phase350Error, msg=str(bad)):
                p350.simulate_pixel_mapping_silent_shutter_and_fx6_apr_abb_hil(**bad)

    def test_37_77a_manual_pixel_mapping_always_emits_shutter_and_reboot(self) -> None:
        r = p350.simulate_pixel_mapping_silent_shutter_and_fx6_apr_abb_hil(
            operation="manual_pixel_mapping",
            silent_mode="On",
            silent_target_auto_pixel_mapping="On",
            lens_cap_light_shielded=True,
        )
        self.assertTrue(r.admitted)
        self.assertTrue(r.manual_executed)
        self.assertTrue(r.auto_reboot_triggered)

    # ------------------------------------------------------------------
    # Sub-Model 77B: Setup -> [Monitor] 3-Item & 4 Dormant EVF vs FX6 VF (38..56)
    # ------------------------------------------------------------------

    def test_38_77b_monitor_group_exact_3_items_and_zero_finder_monitor(self) -> None:
        self.assertEqual(len(p350.FX3_MONITOR_ACTIVE_ITEMS), 3)
        self.assertEqual(len(p350.DORMANT_FX3_EVF_MENUS), 4)
        r = p350.simulate_monitor_3item_dormant_evf_and_fx6_vf_setting_hil(
            monitor_brightness="Manual",
            monitor_brightness_level=2,
            display_quality="High",
            monitor_flip_direction="Horizontal Flip",
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.fx3_group_name, "Setup -> [Monitor]")
        self.assertEqual(r.fx3_active_items_count, 3)
        self.assertFalse(r.finder_monitor_group_exposed)
        self.assertFalse(r.dormant_evf_menus_exposed)
        self.assertFalse(r.bright_monitoring_in_monitor_group)

    def test_39_77b_monitor_settings_reset_immune_and_initialize_restores(self) -> None:
        r_reset = p350.simulate_monitor_3item_dormant_evf_and_fx6_vf_setting_hil(
            monitor_brightness="Sunny Weather",
            display_quality="High",
            monitor_flip_direction="180 Degree Flip",
            camera_settings_reset_applied=True,
        )
        self.assertTrue(r_reset.admitted)
        self.assertFalse(r_reset.monitor_settings_resettable)
        self.assertEqual(r_reset.effective_monitor_brightness, "Sunny Weather")
        self.assertEqual(r_reset.effective_display_quality, "High")
        self.assertEqual(r_reset.effective_monitor_flip_direction, "180 Degree Flip")

        r_init = p350.simulate_monitor_3item_dormant_evf_and_fx6_vf_setting_hil(
            monitor_brightness="Sunny Weather",
            monitor_brightness_level=2,
            display_quality="High",
            monitor_flip_direction="180 Degree Flip",
            initialize_applied=True,
        )
        self.assertTrue(r_init.admitted)
        self.assertEqual(r_init.effective_monitor_brightness, "Manual")
        self.assertEqual(r_init.effective_monitor_brightness_level, 0)
        self.assertEqual(r_init.effective_display_quality, "Standard")
        self.assertEqual(r_init.effective_monitor_flip_direction, "Auto")

    def test_40_77b_monitor_brightness_manual_bounds_minus2_to_plus2(self) -> None:
        for lvl in (-2, -1, 0, 1, 2):
            r = p350.simulate_monitor_3item_dormant_evf_and_fx6_vf_setting_hil(
                monitor_brightness="Manual",
                monitor_brightness_level=lvl,
            )
            self.assertTrue(r.admitted, lvl)
            self.assertEqual(r.effective_monitor_brightness_level, lvl)
        for bad_lvl in (-3, 3):
            r_bad = p350.simulate_monitor_3item_dormant_evf_and_fx6_vf_setting_hil(
                monitor_brightness="Manual",
                monitor_brightness_level=bad_lvl,
            )
            self.assertFalse(r_bad.admitted, bad_lvl)
            self.assertEqual(r_bad.errno_code, p350.EINVAL_ERRNO)

    def test_41_77b_display_quality_thermally_locked_to_standard_on_high_temp(self) -> None:
        r = p350.simulate_monitor_3item_dormant_evf_and_fx6_vf_setting_hil(
            display_quality="High",
            body_temperature_high=True,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p350.EOPNOTSUPP_ERRNO)
        self.assertEqual(r.effective_display_quality, "Standard")
        self.assertTrue(r.display_quality_thermally_locked)

    def test_42_77b_sunny_weather_high_temp_notifies_upm_lcd_limit(self) -> None:
        r = p350.simulate_monitor_3item_dormant_evf_and_fx6_vf_setting_hil(
            monitor_brightness="Sunny Weather",
            display_quality="Standard",
            body_temperature_high=True,
        )
        self.assertTrue(r.admitted)
        self.assertTrue(r.upm_lcd_brightness_limit_notified)
        self.assertTrue(r.display_quality_thermally_locked)

    def test_43_77b_all_4_monitor_flip_directions_admitted(self) -> None:
        for flip in ("Auto", "Horizontal Flip", "180 Degree Flip", "No Flip"):
            r = p350.simulate_monitor_3item_dormant_evf_and_fx6_vf_setting_hil(
                monitor_flip_direction=flip
            )
            self.assertTrue(r.admitted, flip)
            self.assertEqual(r.effective_monitor_flip_direction, flip)

    def test_44_77b_dormant_finder_monitor_and_4_evf_menus_blocked(self) -> None:
        r_grp = p350.simulate_monitor_3item_dormant_evf_and_fx6_vf_setting_hil(
            operation="dormant_finder_monitor_group"
        )
        self.assertFalse(r_grp.admitted)
        self.assertEqual(r_grp.errno_code, p350.EOPNOTSUPP_ERRNO)
        self.assertFalse(r_grp.finder_monitor_group_exposed)

        for evf_item in p350.DORMANT_FX3_EVF_MENUS:
            r_item = p350.simulate_monitor_3item_dormant_evf_and_fx6_vf_setting_hil(
                operation="dormant_evf_item",
                dormant_evf_item=evf_item,
            )
            self.assertFalse(r_item.admitted, evf_item)
            self.assertEqual(r_item.errno_code, p350.EOPNOTSUPP_ERRNO)
            self.assertFalse(r_item.dormant_evf_menus_exposed)

    def test_45_77b_bright_monitoring_stays_in_shooting_display_not_monitor_group(self) -> None:
        r = p350.simulate_monitor_3item_dormant_evf_and_fx6_vf_setting_hil(
            operation="bright_monitoring_check"
        )
        self.assertTrue(r.admitted)
        self.assertFalse(r.bright_monitoring_in_monitor_group)

    def test_46_77b_fx6_vf_setting_brightness_1_to_15_default_8_and_color_bw(self) -> None:
        for color in ("Color", "B&W"):
            r = p350.simulate_monitor_3item_dormant_evf_and_fx6_vf_setting_hil(
                body_profile=p350.BODY_MODEL_FX6,
                fw_version=p350.FW_VER_601,
                operation="fx6_vf_setting",
                fx6_vf_brightness=8,
                fx6_vf_color_mode=color,
                fx6_vf_mirror="B/T",
            )
            self.assertTrue(r.admitted, color)
            self.assertEqual(r.fx6_vf_brightness, 8)
            self.assertEqual(r.fx6_vf_color_mode, color)
            self.assertEqual(r.fx6_vf_mirror, "B/T")
            self.assertFalse(r.fx6_4_vf_submenus_exposed)

    def test_47_77b_fx6_vf_brightness_bounds_1_to_15(self) -> None:
        for good in (1, 15):
            r = p350.simulate_monitor_3item_dormant_evf_and_fx6_vf_setting_hil(
                body_profile=p350.BODY_MODEL_FX6,
                fw_version=p350.FW_VER_601,
                operation="fx6_vf_setting",
                fx6_vf_brightness=good,
            )
            self.assertTrue(r.admitted, good)
        for bad in (0, 16):
            r = p350.simulate_monitor_3item_dormant_evf_and_fx6_vf_setting_hil(
                body_profile=p350.BODY_MODEL_FX6,
                fw_version=p350.FW_VER_601,
                operation="fx6_vf_setting",
                fx6_vf_brightness=bad,
            )
            self.assertFalse(r.admitted, bad)
            self.assertEqual(r.errno_code, p350.EINVAL_ERRNO)

    def test_48_77b_fx6_vf_adjust_requires_vf_connected(self) -> None:
        r_ok = p350.simulate_monitor_3item_dormant_evf_and_fx6_vf_setting_hil(
            body_profile=p350.BODY_MODEL_FX6,
            fw_version=p350.FW_VER_601,
            operation="fx6_vf_adjust",
            fx6_vf_connected=True,
        )
        self.assertTrue(r_ok.admitted)

        r_fail = p350.simulate_monitor_3item_dormant_evf_and_fx6_vf_setting_hil(
            body_profile=p350.BODY_MODEL_FX6,
            fw_version=p350.FW_VER_601,
            operation="fx6_vf_adjust",
            fx6_vf_connected=False,
        )
        self.assertFalse(r_fail.admitted)
        self.assertEqual(r_fail.errno_code, p350.EINVAL_ERRNO)
        self.assertIn("Please connect the viewfinder", r_fail.reason)

    def test_49_77b_fx6_4_dormant_vf_submenus_rejected(self) -> None:
        for sub in p350.FX6_DORMANT_VF_SUBMENUS:
            r = p350.simulate_monitor_3item_dormant_evf_and_fx6_vf_setting_hil(
                body_profile=p350.BODY_MODEL_FX6,
                fw_version=p350.FW_VER_601,
                operation="fx6_dormant_vf_submenu",
                fx6_dormant_submenu=sub,
            )
            self.assertFalse(r.admitted, sub)
            self.assertEqual(r.errno_code, p350.EOPNOTSUPP_ERRNO)
            self.assertFalse(r.fx6_4_vf_submenus_exposed)

    def test_50_77b_fx3_rejects_fx6_vf_operations(self) -> None:
        for op in ("fx6_vf_setting", "fx6_vf_adjust", "fx6_dormant_vf_submenu"):
            r = p350.simulate_monitor_3item_dormant_evf_and_fx6_vf_setting_hil(
                body_profile=p350.BODY_MODEL_FX3,
                operation=op,
            )
            self.assertFalse(r.admitted)
            self.assertEqual(r.errno_code, p350.EOPNOTSUPP_ERRNO)

    def test_51_77b_fx6_rejects_fx3_configure_monitor(self) -> None:
        r = p350.simulate_monitor_3item_dormant_evf_and_fx6_vf_setting_hil(
            body_profile=p350.BODY_MODEL_FX6,
            fw_version=p350.FW_VER_601,
            operation="configure_monitor",
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p350.EOPNOTSUPP_ERRNO)

    def test_52_77b_fx6_mirror_switch_states(self) -> None:
        for mirror in ("Off", "B/T", "ROT"):
            r = p350.simulate_monitor_3item_dormant_evf_and_fx6_vf_setting_hil(
                body_profile=p350.BODY_MODEL_FX6,
                fw_version=p350.FW_VER_601,
                operation="fx6_vf_setting",
                fx6_vf_mirror=mirror,
            )
            self.assertTrue(r.admitted, mirror)
            self.assertEqual(r.fx6_vf_mirror, mirror)

    def test_53_77b_fx3_manual_brightness_with_high_temp_standard_quality_admitted(self) -> None:
        r = p350.simulate_monitor_3item_dormant_evf_and_fx6_vf_setting_hil(
            monitor_brightness="Manual",
            monitor_brightness_level=1,
            display_quality="Standard",
            body_temperature_high=True,
        )
        self.assertTrue(r.admitted)
        self.assertFalse(r.upm_lcd_brightness_limit_notified)
        self.assertTrue(r.display_quality_thermally_locked)

    def test_54_77b_pillar_b_payload_verified(self) -> None:
        rep = p350.run_phase350_pixelmap_apr_monitor_vfadjust_customhold_hdmi_reccontrol_coemulation(
            force_clean_room=True
        )
        pb = rep["pillar_b_monitor_3item_dormant_evf_fx6_vf_hil"]
        self.assertTrue(pb["passed"])
        self.assertEqual(pb["monitor_reset_immune"]["fx3_active_items_count"], 3)
        self.assertEqual(len(pb["dormant_evf_blocks"]), 5)

    def test_55_77b_invalid_inputs_raise_stage77_error(self) -> None:
        for bad in (
            dict(body_profile="FX30"),
            dict(fw_version="2.00"),
            dict(operation="bad"),
            dict(monitor_brightness="Auto"),
            dict(monitor_brightness_level="2"),
            dict(monitor_brightness_level=True),
            dict(display_quality="Ultra"),
            dict(monitor_flip_direction="90"),
            dict(dormant_evf_item="EVF Auto"),
            dict(fx6_vf_brightness="8"),
            dict(fx6_vf_brightness=False),
            dict(fx6_vf_color_mode="Sepia"),
            dict(fx6_vf_mirror="Flip"),
            dict(fx6_dormant_submenu="Sharpness"),
        ):
            with self.assertRaises(p350.Stage77Phase350Error, msg=str(bad)):
                p350.simulate_monitor_3item_dormant_evf_and_fx6_vf_setting_hil(**bad)

    def test_56_77b_initialize_does_not_leak_previous_flip_or_quality(self) -> None:
        r = p350.simulate_monitor_3item_dormant_evf_and_fx6_vf_setting_hil(
            monitor_brightness="Sunny Weather",
            display_quality="High",
            monitor_flip_direction="No Flip",
            initialize_applied=True,
        )
        self.assertEqual(r.effective_monitor_brightness, "Manual")
        self.assertEqual(r.effective_display_quality, "Standard")
        self.assertEqual(r.effective_monitor_flip_direction, "Auto")

    # ------------------------------------------------------------------
    # Sub-Model 77C: Still P/A/S/M Recall Custom Hold 1-3 vs FX6 Push (57..75)
    # ------------------------------------------------------------------

    def test_57_77c_recall_custom_hold_1_to_3_admitted_in_still_pasm(self) -> None:
        self.assertEqual(len(p350.RECALL_CUSTOM_HOLD_11_PARAMS), 11)
        for slot in (1, 2, 3):
            for exp_mode in ("P", "A", "S", "M"):
                r = p350.simulate_still_pasm_recall_custom_hold_and_fx6_push_controls_hil(
                    shoot_mode=p350.SHOOT_MODE_STILL,
                    exposure_mode=exp_mode,
                    operation="recall_custom_hold",
                    hold_slot=slot,
                )
                self.assertTrue(r.admitted, (slot, exp_mode))
                self.assertEqual(r.slots_count, 3)
                self.assertEqual(len(r.effective_checked_params), 11)
                self.assertFalse(r.white_balance_independent_slot_supported)
                self.assertFalse(r.recall_resettable)
                self.assertTrue(r.persisted_in_camset_dat)

    def test_58_77c_recall_custom_hold_rejected_in_movie_sq_and_iauto(self) -> None:
        for mode, exp in (
            (p350.SHOOT_MODE_MOVIE, "M"),
            (p350.SHOOT_MODE_SQ, "M"),
            (p350.SHOOT_MODE_STILL, "iAuto"),
        ):
            r = p350.simulate_still_pasm_recall_custom_hold_and_fx6_push_controls_hil(
                shoot_mode=mode,
                exposure_mode=exp,
                operation="recall_custom_hold",
                hold_slot=1,
            )
            self.assertFalse(r.admitted, (mode, exp))
            self.assertEqual(r.errno_code, p350.EOPNOTSUPP_ERRNO)

    def test_59_77c_zero_independent_white_balance_slot_rejected(self) -> None:
        r1 = p350.simulate_still_pasm_recall_custom_hold_and_fx6_push_controls_hil(
            operation="dormant_recall_white_balance"
        )
        self.assertFalse(r1.admitted)
        self.assertEqual(r1.errno_code, p350.EOPNOTSUPP_ERRNO)
        self.assertFalse(r1.white_balance_independent_slot_supported)

        r2 = p350.simulate_still_pasm_recall_custom_hold_and_fx6_push_controls_hil(
            operation="recall_custom_hold",
            checked_params=("aperture", "white_balance"),
        )
        self.assertFalse(r2.admitted)
        self.assertEqual(r2.errno_code, p350.EOPNOTSUPP_ERRNO)

    def test_60_77c_self_timer_excluded_from_drive_mode_registration(self) -> None:
        r = p350.simulate_still_pasm_recall_custom_hold_and_fx6_push_controls_hil(
            operation="recall_custom_hold",
            include_self_timer_in_drive_mode=True,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p350.EINVAL_ERRNO)
        self.assertFalse(r.self_timer_included_in_recall_drive_mode)

    def test_61_77c_hlg_still_temporarily_disabled_during_iso_or_dro_bracket(self) -> None:
        for brk in ("ISO Bracket", "DRO Bracket"):
            r = p350.simulate_still_pasm_recall_custom_hold_and_fx6_push_controls_hil(
                operation="recall_custom_hold",
                hlg_still_image="On",
                drive_mode_bracket=brk,
            )
            self.assertTrue(r.admitted, brk)
            self.assertTrue(r.hlg_temporarily_disabled)

        r_cont = p350.simulate_still_pasm_recall_custom_hold_and_fx6_push_controls_hil(
            operation="recall_custom_hold",
            hlg_still_image="On",
            drive_mode_bracket="Cont. Shooting",
        )
        self.assertTrue(r_cont.admitted)
        self.assertFalse(r_cont.hlg_temporarily_disabled)

    def test_62_77c_reset_immune_vs_initialize_clears_checked_params(self) -> None:
        r_reset = p350.simulate_still_pasm_recall_custom_hold_and_fx6_push_controls_hil(
            operation="recall_custom_hold",
            checked_params=("aperture", "shutter_speed"),
            camera_settings_reset_applied=True,
        )
        self.assertTrue(r_reset.admitted)
        self.assertEqual(r_reset.effective_checked_params, ("aperture", "shutter_speed"))

        r_init = p350.simulate_still_pasm_recall_custom_hold_and_fx6_push_controls_hil(
            operation="recall_custom_hold",
            checked_params=("aperture", "shutter_speed"),
            initialize_applied=True,
        )
        self.assertTrue(r_init.admitted)
        self.assertEqual(r_init.effective_checked_params, ())

    def test_63_77c_af_on_admitted_across_still_movie_sq(self) -> None:
        for mode in p350.VALID_SHOOT_MODES:
            r = p350.simulate_still_pasm_recall_custom_hold_and_fx6_push_controls_hil(
                shoot_mode=mode,
                operation="af_on",
            )
            self.assertTrue(r.admitted, mode)

    def test_64_77c_eye_af_admitted_in_still_movie_blocked_in_sq(self) -> None:
        for mode in (p350.SHOOT_MODE_STILL, p350.SHOOT_MODE_MOVIE):
            r = p350.simulate_still_pasm_recall_custom_hold_and_fx6_push_controls_hil(
                shoot_mode=mode,
                operation="eye_af",
            )
            self.assertTrue(r.admitted, mode)
        r_sq = p350.simulate_still_pasm_recall_custom_hold_and_fx6_push_controls_hil(
            shoot_mode=p350.SHOOT_MODE_SQ,
            operation="eye_af",
        )
        self.assertFalse(r_sq.admitted)
        self.assertEqual(r_sq.errno_code, p350.EOPNOTSUPP_ERRNO)

    def test_65_77c_tracking_on_requires_still_plus_af_c(self) -> None:
        r_ok = p350.simulate_still_pasm_recall_custom_hold_and_fx6_push_controls_hil(
            shoot_mode=p350.SHOOT_MODE_STILL,
            focus_mode="AF-C",
            operation="tracking_on",
        )
        self.assertTrue(r_ok.admitted)

        for mode, fm in (
            (p350.SHOOT_MODE_MOVIE, "AF-C"),
            (p350.SHOOT_MODE_STILL, "AF-S"),
            (p350.SHOOT_MODE_STILL, "MF"),
        ):
            r_fail = p350.simulate_still_pasm_recall_custom_hold_and_fx6_push_controls_hil(
                shoot_mode=mode,
                focus_mode=fm,
                operation="tracking_on",
            )
            self.assertFalse(r_fail.admitted, (mode, fm))
            self.assertEqual(r_fail.errno_code, p350.EOPNOTSUPP_ERRNO)

    def test_66_77c_fx6_zero_recall_custom_hold_and_dormant_high_low_key(self) -> None:
        r_recall = p350.simulate_still_pasm_recall_custom_hold_and_fx6_push_controls_hil(
            body_profile=p350.BODY_MODEL_FX6,
            fw_version=p350.FW_VER_601,
            operation="recall_custom_hold",
        )
        self.assertFalse(r_recall.admitted)
        self.assertEqual(r_recall.errno_code, p350.EOPNOTSUPP_ERRNO)
        self.assertFalse(r_recall.fx6_recall_custom_hold_supported)

        r_hlk = p350.simulate_still_pasm_recall_custom_hold_and_fx6_push_controls_hil(
            body_profile=p350.BODY_MODEL_FX6,
            fw_version=p350.FW_VER_601,
            operation="fx6_dormant_high_low_key",
        )
        self.assertFalse(r_hlk.admitted)
        self.assertEqual(r_hlk.errno_code, p350.EOPNOTSUPP_ERRNO)
        self.assertFalse(r_hlk.fx6_high_low_key_exposed)

    def test_67_77c_fx6_push_af_lockouts_manual_focus_and_desqueeze(self) -> None:
        r_ok = p350.simulate_still_pasm_recall_custom_hold_and_fx6_push_controls_hil(
            body_profile=p350.BODY_MODEL_FX6,
            fw_version=p350.FW_VER_601,
            operation="fx6_push_af",
            fx6_lens_manual_focus=False,
            fx6_desqueeze="Off(1.0x)",
            fx6_push_af_mode="Single-shot AF(AF-S)",
        )
        self.assertTrue(r_ok.admitted)

        r_mf = p350.simulate_still_pasm_recall_custom_hold_and_fx6_push_controls_hil(
            body_profile=p350.BODY_MODEL_FX6,
            fw_version=p350.FW_VER_601,
            operation="fx6_push_af",
            fx6_lens_manual_focus=True,
        )
        self.assertFalse(r_mf.admitted)
        self.assertEqual(r_mf.errno_code, p350.EOPNOTSUPP_ERRNO)

        for desq in ("1.3x", "2.0x"):
            r_desq = p350.simulate_still_pasm_recall_custom_hold_and_fx6_push_controls_hil(
                body_profile=p350.BODY_MODEL_FX6,
                fw_version=p350.FW_VER_601,
                operation="fx6_push_af",
                fx6_desqueeze=desq,
            )
            self.assertFalse(r_desq.admitted, desq)
            self.assertEqual(r_desq.errno_code, p350.EOPNOTSUPP_ERRNO)

    def test_68_77c_fx6_push_agc_blocked_in_cine_ei_or_bokeh_on(self) -> None:
        for exp in ("Flexible ISO", "Custom"):
            r_ok = p350.simulate_still_pasm_recall_custom_hold_and_fx6_push_controls_hil(
                body_profile=p350.BODY_MODEL_FX6,
                fw_version=p350.FW_VER_601,
                operation="fx6_push_agc",
                fx6_exposure_mode=exp,
                fx6_bokeh_control="Off",
            )
            self.assertTrue(r_ok.admitted, exp)

        for exp, bokeh in (
            ("Cine EI", "Off"),
            ("Cine EI Quick", "Off"),
            ("Custom", "On"),
        ):
            r_blk = p350.simulate_still_pasm_recall_custom_hold_and_fx6_push_controls_hil(
                body_profile=p350.BODY_MODEL_FX6,
                fw_version=p350.FW_VER_601,
                operation="fx6_push_agc",
                fx6_exposure_mode=exp,
                fx6_bokeh_control=bokeh,
            )
            self.assertFalse(r_blk.admitted, (exp, bokeh))
            self.assertEqual(r_blk.errno_code, p350.EOPNOTSUPP_ERRNO)

    def test_69_77c_fx6_push_auto_iris_blocked_on_manual_iris_or_bokeh_on(self) -> None:
        r_ok = p350.simulate_still_pasm_recall_custom_hold_and_fx6_push_controls_hil(
            body_profile=p350.BODY_MODEL_FX6,
            fw_version=p350.FW_VER_601,
            operation="fx6_push_auto_iris",
            fx6_lens_manual_iris=False,
            fx6_bokeh_control="Off",
        )
        self.assertTrue(r_ok.admitted)

        for man_iris, bokeh in ((True, "Off"), (False, "On")):
            r_blk = p350.simulate_still_pasm_recall_custom_hold_and_fx6_push_controls_hil(
                body_profile=p350.BODY_MODEL_FX6,
                fw_version=p350.FW_VER_601,
                operation="fx6_push_auto_iris",
                fx6_lens_manual_iris=man_iris,
                fx6_bokeh_control=bokeh,
            )
            self.assertFalse(r_blk.admitted, (man_iris, bokeh))
            self.assertEqual(r_blk.errno_code, p350.EOPNOTSUPP_ERRNO)

    def test_70_77c_fx3_rejects_fx6_push_operations(self) -> None:
        for op in ("fx6_push_af", "fx6_push_agc", "fx6_push_auto_iris", "fx6_dormant_high_low_key"):
            r = p350.simulate_still_pasm_recall_custom_hold_and_fx6_push_controls_hil(
                body_profile=p350.BODY_MODEL_FX3,
                operation=op,
            )
            self.assertFalse(r.admitted, op)
            self.assertEqual(r.errno_code, p350.EOPNOTSUPP_ERRNO)

    def test_71_77c_invalid_inputs_raise_stage77_error(self) -> None:
        for bad in (
            dict(body_profile="FX30"),
            dict(fw_version="9.00"),
            dict(shoot_mode="Timelapse"),
            dict(exposure_mode="Auto"),
            dict(operation="bad_op"),
            dict(hold_slot=4),
            dict(hlg_still_image="Auto"),
            dict(drive_mode_bracket="Focus"),
            dict(focus_mode="Continuous"),
            dict(fx6_desqueeze="1.5x"),
            dict(fx6_exposure_mode="P"),
            dict(fx6_bokeh_control="Auto"),
            dict(fx6_push_af_mode="MF"),
            dict(checked_params=("nonexistent_slot",)),
        ):
            with self.assertRaises(p350.Stage77Phase350Error, msg=str(bad)):
                p350.simulate_still_pasm_recall_custom_hold_and_fx6_push_controls_hil(**bad)

    def test_72_77c_custom_checked_subset_order_preserved(self) -> None:
        subset = ("shooting_mode", "iso_sensitivity", "focus_area")
        r = p350.simulate_still_pasm_recall_custom_hold_and_fx6_push_controls_hil(
            shoot_mode=p350.SHOOT_MODE_STILL,
            exposure_mode="A",
            checked_params=subset,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.effective_checked_params, subset)

    def test_73_77c_fx6_rejects_still_af_custom_keys(self) -> None:
        for op in ("af_on", "eye_af", "tracking_on", "dormant_recall_white_balance"):
            r = p350.simulate_still_pasm_recall_custom_hold_and_fx6_push_controls_hil(
                body_profile=p350.BODY_MODEL_FX6,
                fw_version=p350.FW_VER_601,
                operation=op,
            )
            self.assertFalse(r.admitted, op)
            self.assertEqual(r.errno_code, p350.EOPNOTSUPP_ERRNO)

    def test_74_77c_pillar_c_payload_verified(self) -> None:
        rep = p350.run_phase350_pixelmap_apr_monitor_vfadjust_customhold_hdmi_reccontrol_coemulation(
            force_clean_room=True
        )
        pc = rep["pillar_c_still_pasm_recall_custom_hold_fx6_push_hil"]
        self.assertTrue(pc["passed"])
        self.assertEqual(len(pc["still_pasm_recall"]["effective_checked_params"]), 11)
        self.assertTrue(pc["fx6_push_af"]["admitted"])

    def test_75_77c_empty_checked_params_tuple_allowed(self) -> None:
        r = p350.simulate_still_pasm_recall_custom_hold_and_fx6_push_controls_hil(
            shoot_mode=p350.SHOOT_MODE_STILL,
            exposure_mode="S",
            checked_params=(),
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.effective_checked_params, ())

    # ------------------------------------------------------------------
    # Sub-Model 77D: External Output HDMI Matrix & Slot-1 EROFS=30 (76..93)
    # ------------------------------------------------------------------

    def test_76_77d_slot1_erofs_30_blocks_rec_control_with_rec_media_on(self) -> None:
        r = p350.simulate_external_output_hdmi_tc_rec_control_and_slot1_erofs_hil(
            operation="rec_control_trigger",
            rec_media_dur_hdmi_output="On",
            time_code_output="On",
            rec_control="On",
            recording_target_slot="Slot 1",
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p350.EROFS_ERRNO)
        self.assertTrue(r.slot1_erofs_triggered)
        self.assertEqual(r.slot1_data_sector_writes, 0)
        self.assertEqual(r.emmc_nflasha_write_count, 0)

    def test_77_77d_safe_hdmi_only_rec_control_succeeds_even_with_slot1_present(self) -> None:
        r = p350.simulate_external_output_hdmi_tc_rec_control_and_slot1_erofs_hil(
            operation="rec_control_trigger",
            rec_media_dur_hdmi_output="Off(HDMI Only)",
            time_code_output="On",
            rec_control="On",
            recording_target_slot="Slot 1",
            hdmi_info_display="On",
        )
        self.assertTrue(r.admitted)
        self.assertFalse(r.slot1_erofs_triggered)
        self.assertEqual(r.effective_hdmi_info_display, "Off")
        self.assertEqual(r.slot1_data_sector_writes, 0)

    def test_78_77d_safe_slot2_rec_control_succeeds_and_downscales_log_to_1080p(self) -> None:
        r = p350.simulate_external_output_hdmi_tc_rec_control_and_slot1_erofs_hil(
            operation="rec_control_trigger",
            rec_media_dur_hdmi_output="On",
            time_code_output="On",
            rec_control="On",
            recording_target_slot="Slot 2",
            log_shooting="Cine EI",
        )
        self.assertTrue(r.admitted)
        self.assertFalse(r.slot1_erofs_triggered)
        self.assertTrue(r.output_downscaled_to_1080)
        self.assertEqual(r.effective_output_resolution, "1080p")

    def test_79_77d_pplut1_to_4_downscales_hdmi_to_1080_when_rec_media_on(self) -> None:
        for pp in ("PPLUT1", "PPLUT2", "PPLUT3", "PPLUT4"):
            r = p350.simulate_external_output_hdmi_tc_rec_control_and_slot1_erofs_hil(
                picture_profile=pp,
                rec_media_dur_hdmi_output="On",
                output_resolution="2160p",
            )
            self.assertTrue(r.admitted, pp)
            self.assertTrue(r.output_downscaled_to_1080, pp)
            self.assertEqual(r.effective_output_resolution, "1080p")

        r_hdmi_only = p350.simulate_external_output_hdmi_tc_rec_control_and_slot1_erofs_hil(
            picture_profile="PPLUT1",
            rec_media_dur_hdmi_output="Off(HDMI Only)",
            output_resolution="2160p",
        )
        self.assertTrue(r_hdmi_only.admitted)
        self.assertFalse(r_hdmi_only.output_downscaled_to_1080)
        self.assertEqual(r_hdmi_only.effective_output_resolution, "2160p")

    def test_80_77d_rec_control_hard_requires_time_code_output_on_and_prereqs(self) -> None:
        for bad_kwargs in (
            dict(time_code_output="Off"),
            dict(compatible_ext_recorder=False),
            dict(hdmi_connected=False),
            dict(usb_streaming_mode="On"),
        ):
            r = p350.simulate_external_output_hdmi_tc_rec_control_and_slot1_erofs_hil(
                operation="rec_control_trigger",
                time_code_output=bad_kwargs.get("time_code_output", "On"),
                rec_control="On",
                compatible_ext_recorder=bad_kwargs.get("compatible_ext_recorder", True),
                hdmi_connected=bad_kwargs.get("hdmi_connected", True),
                usb_streaming_mode=bad_kwargs.get("usb_streaming_mode", "Off"),
                recording_target_slot="Slot 2",
            )
            self.assertFalse(r.admitted, str(bad_kwargs))
            self.assertEqual(r.errno_code, p350.EOPNOTSUPP_ERRNO)
            self.assertEqual(r.effective_rec_control, "Off")

    def test_81_77d_sq_mode_forces_rec_media_on_and_locks_raw_and_tc_off(self) -> None:
        r_hdmi_only = p350.simulate_external_output_hdmi_tc_rec_control_and_slot1_erofs_hil(
            shoot_mode=p350.SHOOT_MODE_SQ,
            rec_media_dur_hdmi_output="Off(HDMI Only)",
        )
        self.assertFalse(r_hdmi_only.admitted)
        self.assertEqual(r_hdmi_only.errno_code, p350.EOPNOTSUPP_ERRNO)
        self.assertEqual(r_hdmi_only.effective_rec_media_dur_hdmi_output, "On")

        r_raw = p350.simulate_external_output_hdmi_tc_rec_control_and_slot1_erofs_hil(
            shoot_mode=p350.SHOOT_MODE_SQ,
            raw_output="On",
        )
        self.assertFalse(r_raw.admitted)
        self.assertEqual(r_raw.errno_code, p350.EOPNOTSUPP_ERRNO)

        r_tc = p350.simulate_external_output_hdmi_tc_rec_control_and_slot1_erofs_hil(
            shoot_mode=p350.SHOOT_MODE_SQ,
            time_code_output="On",
        )
        self.assertFalse(r_tc.admitted)
        self.assertEqual(r_tc.errno_code, p350.EOPNOTSUPP_ERRNO)

    def test_82_77d_4k_24p_transition_triggers_reboot_and_cross_rate_isolation(self) -> None:
        r_enter = p350.simulate_external_output_hdmi_tc_rec_control_and_slot1_erofs_hil(
            operation="change_4k_24p",
            four_k_output_set="24.00p 10bit",
            previous_four_k_output_set="23.98p 10bit",
        )
        self.assertTrue(r_enter.admitted)
        self.assertTrue(r_enter.reboot_required)
        self.assertTrue(r_enter.cross_frame_rate_playback_isolated)

        r_stay = p350.simulate_external_output_hdmi_tc_rec_control_and_slot1_erofs_hil(
            operation="change_4k_24p",
            four_k_output_set="24.00p 10bit",
            previous_four_k_output_set="24.00p 10bit",
        )
        self.assertTrue(r_stay.admitted)
        self.assertFalse(r_stay.reboot_required)

    def test_83_77d_hdmi_info_display_blacks_out_lcd_vs_raw_forces_clean(self) -> None:
        r_info_on = p350.simulate_external_output_hdmi_tc_rec_control_and_slot1_erofs_hil(
            hdmi_connected=True,
            hdmi_info_display="On",
            raw_output="Off",
        )
        self.assertTrue(r_info_on.admitted)
        self.assertTrue(r_info_on.body_lcd_blackout)

        r_raw_on = p350.simulate_external_output_hdmi_tc_rec_control_and_slot1_erofs_hil(
            hdmi_connected=True,
            hdmi_info_display="On",
            raw_output="On",
        )
        self.assertTrue(r_raw_on.admitted)
        self.assertEqual(r_raw_on.effective_hdmi_info_display, "Off")
        self.assertFalse(r_raw_on.body_lcd_blackout)

    def test_84_77d_external_output_reset_immune_and_initialize_restores_defaults(self) -> None:
        r_reset = p350.simulate_external_output_hdmi_tc_rec_control_and_slot1_erofs_hil(
            hdmi_resolution="1080p",
            four_ch_audio_output="CH3/CH4",
            ctrl_for_hdmi="Off",
            camera_settings_reset_applied=True,
        )
        self.assertTrue(r_reset.admitted)
        self.assertFalse(r_reset.external_output_resettable)
        self.assertEqual(r_reset.effective_hdmi_resolution, "1080p")
        self.assertEqual(r_reset.effective_4ch_audio_output, "CH3/CH4")
        self.assertEqual(r_reset.effective_ctrl_for_hdmi, "Off")

        r_init = p350.simulate_external_output_hdmi_tc_rec_control_and_slot1_erofs_hil(
            hdmi_resolution="1080p",
            four_ch_audio_output="CH3/CH4",
            ctrl_for_hdmi="Off",
            initialize_applied=True,
        )
        self.assertTrue(r_init.admitted)
        self.assertEqual(r_init.effective_hdmi_resolution, "Auto")
        self.assertEqual(r_init.effective_4ch_audio_output, "CH1/CH2")
        self.assertEqual(r_init.effective_ctrl_for_hdmi, "On")

    def test_85_77d_typos_and_dormant_24p_60p_and_4k_2k_blocked(self) -> None:
        for op in ("dormant_24p_60p", "dormant_4k_2k"):
            r = p350.simulate_external_output_hdmi_tc_rec_control_and_slot1_erofs_hil(
                operation=op
            )
            self.assertFalse(r.admitted, op)
            self.assertEqual(r.errno_code, p350.EOPNOTSUPP_ERRNO)
            self.assertFalse(r.dormant_24p_60p_exposed)
            self.assertFalse(r.dormant_4k_2k_exposed)
            self.assertEqual(
                r.hdmi_4k_outpute_typo_symbol,
                "PRM_HAITA_hdmi_4k_outpute_apsc_restriction",
            )
            self.assertEqual(r.ctrl_for_hmdi_typo_symbol, "BKID_APP_setting_ctrl_for_hmdi")

    def test_86_77d_fx6_raw_hdmi_forces_sdi_to_1080(self) -> None:
        r = p350.simulate_external_output_hdmi_tc_rec_control_and_slot1_erofs_hil(
            body_profile=p350.BODY_MODEL_FX6,
            fw_version=p350.FW_VER_601,
            operation="fx6_dual_output",
            fx6_codec="RAW(HDMI)",
            fx6_sdi_on=True,
            fx6_hdmi_on=True,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.fx6_hdmi_output, "4240x2392 RAW(HDMI)")
        self.assertEqual(r.fx6_sdi_output, "1920x1080P/i")
        self.assertTrue(r.output_downscaled_to_1080)

    def test_87_77d_fx6_sdi_hdmi_rec_control_requires_hdmi_tc_out_on(self) -> None:
        r_fail = p350.simulate_external_output_hdmi_tc_rec_control_and_slot1_erofs_hil(
            body_profile=p350.BODY_MODEL_FX6,
            fw_version=p350.FW_VER_601,
            operation="fx6_dual_output",
            fx6_hdmi_on=True,
            fx6_sdi_hdmi_rec_control="SDI/HDMI Remote I/F",
            fx6_hdmi_tc_out="Off",
        )
        self.assertFalse(r_fail.admitted)
        self.assertEqual(r_fail.errno_code, p350.EOPNOTSUPP_ERRNO)

        r_ok = p350.simulate_external_output_hdmi_tc_rec_control_and_slot1_erofs_hil(
            body_profile=p350.BODY_MODEL_FX6,
            fw_version=p350.FW_VER_601,
            operation="fx6_dual_output",
            fx6_hdmi_on=True,
            fx6_sdi_hdmi_rec_control="SDI/HDMI Remote I/F",
            fx6_hdmi_tc_out="On",
        )
        self.assertTrue(r_ok.admitted)

    def test_88_77d_fx6_parallel_rec_on_slot1_blocked_by_erofs_30(self) -> None:
        r = p350.simulate_external_output_hdmi_tc_rec_control_and_slot1_erofs_hil(
            body_profile=p350.BODY_MODEL_FX6,
            fw_version=p350.FW_VER_601,
            operation="fx6_dual_output",
            fx6_sdi_hdmi_rec_control="Parallel Rec",
            fx6_hdmi_tc_out="On",
            recording_target_slot="Slot 1",
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p350.EROFS_ERRNO)
        self.assertTrue(r.slot1_erofs_triggered)
        self.assertEqual(r.slot1_data_sector_writes, 0)

    def test_89_77d_fx6_sq_over_60fps_with_sdi_on_downscales_hdmi_to_1080p(self) -> None:
        r = p350.simulate_external_output_hdmi_tc_rec_control_and_slot1_erofs_hil(
            body_profile=p350.BODY_MODEL_FX6,
            fw_version=p350.FW_VER_601,
            operation="fx6_dual_output",
            fx6_sdi_on=True,
            fx6_hdmi_on=True,
            fx6_codec="XAVC-I",
            fx6_sq_fps=120.0,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.fx6_hdmi_output, "1920x1080P")
        self.assertTrue(r.output_downscaled_to_1080)

    def test_90_77d_fx3_rejects_fx6_dual_output_and_fx6_rejects_fx3_ops(self) -> None:
        r1 = p350.simulate_external_output_hdmi_tc_rec_control_and_slot1_erofs_hil(
            body_profile=p350.BODY_MODEL_FX3,
            operation="fx6_dual_output",
        )
        self.assertFalse(r1.admitted)
        self.assertEqual(r1.errno_code, p350.EOPNOTSUPP_ERRNO)

        r2 = p350.simulate_external_output_hdmi_tc_rec_control_and_slot1_erofs_hil(
            body_profile=p350.BODY_MODEL_FX6,
            fw_version=p350.FW_VER_601,
            operation="hdmi_output",
        )
        self.assertFalse(r2.admitted)
        self.assertEqual(r2.errno_code, p350.EOPNOTSUPP_ERRNO)

    def test_91_77d_rec_w_shutter_with_off_hdmi_only_requires_shutter_button(self) -> None:
        r = p350.simulate_external_output_hdmi_tc_rec_control_and_slot1_erofs_hil(
            operation="rec_control_trigger",
            rec_media_dur_hdmi_output="Off(HDMI Only)",
            time_code_output="On",
            rec_control="On",
            rec_w_shutter="On",
            recording_target_slot="Slot 1",
        )
        self.assertTrue(r.admitted)
        self.assertIn("rec_w_shutter=On", r.reason)

    def test_92_77d_4ch_audio_output_ch1_ch2_vs_ch3_ch4(self) -> None:
        for ch in ("CH1/CH2", "CH3/CH4"):
            r = p350.simulate_external_output_hdmi_tc_rec_control_and_slot1_erofs_hil(
                four_ch_audio_output=ch
            )
            self.assertTrue(r.admitted, ch)
            self.assertEqual(r.effective_4ch_audio_output, ch)

    def test_93_77d_invalid_inputs_raise_stage77_error(self) -> None:
        for bad in (
            dict(body_profile="FX30"),
            dict(fw_version="1.00"),
            dict(shoot_mode="Timelapse"),
            dict(operation="bad_op"),
            dict(hdmi_resolution="720p"),
            dict(rec_media_dur_hdmi_output="Never"),
            dict(output_resolution="480p"),
            dict(four_k_output_set="120p"),
            dict(previous_four_k_output_set="120p"),
            dict(raw_output="Auto"),
            dict(time_code_output="Auto"),
            dict(rec_control="Auto"),
            dict(rec_w_shutter="Auto"),
            dict(four_ch_audio_output="CH5/CH6"),
            dict(hdmi_info_display="Auto"),
            dict(ctrl_for_hdmi="Auto"),
            dict(log_shooting="SLog"),
            dict(picture_profile="PP99"),
            dict(recording_target_slot="Slot 3"),
            dict(usb_streaming_mode="Auto"),
            dict(fx6_codec="H264"),
            dict(fx6_sq_fps=0.0),
            dict(fx6_sdi_hdmi_rec_control="Auto"),
            dict(fx6_hdmi_tc_out="Auto"),
        ):
            with self.assertRaises(p350.Stage77Phase350Error, msg=str(bad)):
                p350.simulate_external_output_hdmi_tc_rec_control_and_slot1_erofs_hil(**bad)

    # ------------------------------------------------------------------
    # Milestone, Determinism, CLI & Suite Stage 77 Wiring (Tests 94..100)
    # ------------------------------------------------------------------

    def test_94_milestone_probe_exact_fields(self) -> None:
        probe = p350._build_stage77_milestone_probe()
        self.assertEqual(probe["phase_number"], 350)
        self.assertEqual(probe["stage_index"], 77)
        self.assertEqual(probe["stage_total"], 77)
        self.assertEqual(probe["milestone"], "77/77")
        self.assertTrue(probe["is_77th_stage_milestone"])
        self.assertEqual(probe["wave"], "Wave-67")
        self.assertEqual(probe["fx3_target_version"], "Ver. 7.02")
        self.assertEqual(probe["fx6_comparison_version"], "Ver. 6.01")

    def test_95_pillar_results_all_passed_in_clean_room(self) -> None:
        rep = p350.run_phase350_pixelmap_apr_monitor_vfadjust_customhold_hdmi_reccontrol_coemulation(
            force_clean_room=True
        )
        for pillar_key in (
            "pillar_a_pixelmap_silent_shutter_fx6_apr_abb_hil",
            "pillar_b_monitor_3item_dormant_evf_fx6_vf_hil",
            "pillar_c_still_pasm_recall_custom_hold_fx6_push_hil",
            "pillar_d_external_output_hdmi_tc_rec_ctrl_slot1_erofs_hil",
        ):
            self.assertTrue(rep[pillar_key]["passed"], pillar_key)

    def test_96_stage77_wrapper_and_suite_fast_determinism(self) -> None:
        s77 = suite.run_stage77_realhw_pixelmap_apr_monitor_vfadjust_customhold_hdmi_reccontrol_hil(
            suite.CoEmulationConfig(force_clean_room=True)
        )
        self.assertEqual(
            s77["stage"],
            "stage77_realhw_pixelmap_apr_monitor_vfadjust_customhold_hdmi_reccontrol_hil",
        )
        self.assertEqual(s77["schema"], p350.SCHEMA_ID)
        self.assertEqual(s77["phase_number"], 350)
        self.assertEqual(s77["milestone"], "77/77")
        self.assertTrue(s77["is_77th_stage_milestone"])
        self.assertTrue(s77["all_checks_passed"])
        self.assertEqual(len(s77["phase350_audit_digest_sha256"]), 64)

        cfg = suite.CoEmulationConfig(**_fast_suite_kwargs())
        r1 = suite.run_fx3_vm_coemulation_suite(cfg)
        r2 = suite.run_fx3_vm_coemulation_suite(cfg)
        self.assertTrue(r1["all_checks_passed"])
        self.assertEqual(r1["audit_digest_sha256"], r2["audit_digest_sha256"])

    def test_97_standalone_and_suite_cli_help_percent_escaping_and_flags(self) -> None:
        proc1 = subprocess.run(
            [
                sys.executable,
                "-B",
                str(
                    FX3_VM_DIR
                    / "realhw_pixelmap_apr_monitor_vfadjust_customhold_hdmi_reccontrol_coemulator.py"
                ),
                "--help",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc1.returncode, 0, proc1.stderr)
        self.assertIn("100%", proc1.stdout)
        self.assertIn("77/77", proc1.stdout)

        proc2 = subprocess.run(
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
        self.assertEqual(proc2.returncode, 0, proc2.stderr)
        self.assertIn("77/77 Full-Board Stages", proc2.stdout)
        self.assertIn("--include-stage77", proc2.stdout)
        self.assertIn("--skip-stage77", proc2.stdout)
        self.assertIn("--no-include-stage77", proc2.stdout)
        self.assertIn("--skip-phase350", proc2.stdout)

    def test_98_standalone_cli_summary_json_and_no_hardcoded_python_path(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = p350.main(["--self-test", "--clean-room", "--summary"])
        self.assertEqual(rc, 0)
        self.assertIn("[PASS] Phase 350 Stage 77 (77/77 Stages)", buf.getvalue())

        buf_json = io.StringIO()
        with contextlib.redirect_stdout(buf_json):
            rc2 = p350.main(["--self-test", "--clean-room", "--json"])
        self.assertEqual(rc2, 0)
        parsed = json.loads(buf_json.getvalue())
        self.assertEqual(parsed["milestone"], "77/77")
        self.assertTrue(parsed["is_77th_stage_milestone"])
        self.assertTrue(parsed["all_checks_passed"])
        self.assertNotIn("\\x7fELF", buf_json.getvalue())

        mod_src = (
            FX3_VM_DIR
            / "realhw_pixelmap_apr_monitor_vfadjust_customhold_hdmi_reccontrol_coemulator.py"
        ).read_text(encoding="utf-8")
        tst_src = Path(__file__).read_text(encoding="utf-8")
        forbidden = "/" + "usr/bin/" + "python3"
        self.assertNotIn(forbidden, mod_src)
        self.assertNotIn(forbidden, tst_src)

    def test_99_suite_default_config_enables_stage77_and_full_run_has_at_least_77_stages(self) -> None:
        cfg = suite.CoEmulationConfig()
        self.assertTrue(
            cfg.include_phase350_realhw_pixelmap_apr_monitor_vfadjust_customhold_hdmi_reccontrol_hil
        )
        self.assertTrue(cfg.include_stage77)
        self.assertTrue(
            cfg.stage77_realhw_pixelmap_apr_monitor_vfadjust_customhold_hdmi_reccontrol_hil
        )

        t0 = time.monotonic()
        rep = suite.run_fx3_vm_coemulation_suite(cfg)
        elapsed = time.monotonic() - t0
        self.assertTrue(rep["all_checks_passed"])
        stage_keys = [k for k in rep if re.match(r"^stage\d+_", k)]
        self.assertGreaterEqual(len(stage_keys), 77)
        self.assertIn(
            "stage77_realhw_pixelmap_apr_monitor_vfadjust_customhold_hdmi_reccontrol_hil",
            rep,
        )
        s77 = rep[
            "stage77_realhw_pixelmap_apr_monitor_vfadjust_customhold_hdmi_reccontrol_hil"
        ]
        self.assertTrue(s77["all_checks_passed"])
        self.assertTrue(s77["is_77th_stage_milestone"])
        self.assertEqual(s77["milestone"], "77/77")
        self.assertEqual(s77["phase_number"], 350)
        max_elapsed = 30.0 if IS_CI else 15.0
        self.assertLess(elapsed, max_elapsed)

    def test_100_suite_skip_flags_summary_cli_and_tamper_detection(self) -> None:
        for flag in ("--skip-stage77", "--no-include-stage77", "--skip-phase350"):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = suite.main([*_FAST_CLI_FLAGS, flag, "--json"])
            self.assertEqual(rc, 0)
            data = json.loads(buf.getvalue())
            self.assertNotIn(
                "stage77_realhw_pixelmap_apr_monitor_vfadjust_customhold_hdmi_reccontrol_hil",
                data,
            )
            self.assertFalse(data["config"]["include_stage77"])

        buf_sum = io.StringIO()
        with contextlib.redirect_stdout(buf_sum):
            rc_sum = suite.main([*_FAST_CLI_FLAGS, "--include-stage77", "--summary"])
        self.assertEqual(rc_sum, 0)
        self.assertIn(
            "realhw_pixelmap_apr_monitor_vfadjust_customhold_hdmi_reccontrol_hil=CLEAN_ROOM_SYNTHETIC("
            "m77=77/77,abb=0,mon=3,evf=0,hold=3x11,wb=0,erofs_byp=0,s1_wr=0,emmc_wr=0)",
            buf_sum.getvalue(),
        )

        for attr, val in (
            ("IS_77TH_STAGE_MILESTONE", False),
            ("FX6_ABB_MENU_EXPOSED_EVENTS", 1),
            ("FX3_MONITOR_GROUP_ACTIVE_ITEMS_COUNT", 4),
            ("DORMANT_EVF_MENUS_EXPOSED_EVENTS", 1),
            ("RECALL_CUSTOM_HOLD_CHECKBOX_PARAMS_COUNT", 12),
            ("RECALL_CUSTOM_HOLD_WHITE_BALANCE_INDEPENDENT_SLOTS", 1),
            ("HDMI_REC_MEDIA_SLOT1_EROFS_BYPASS_EVENTS", 1),
            ("SLOT1_DATA_SECTOR_WRITES", 1),
            ("EMMC_NFLASHA_WRITE_COUNT", 1),
            ("RAW_FIRMWARE_BYTES_LEAKED", 1),
        ):
            with unittest.mock.patch.object(p350, attr, val):
                rep = p350.run_phase350_pixelmap_apr_monitor_vfadjust_customhold_hdmi_reccontrol_coemulation(
                    force_clean_room=True
                )
                self.assertFalse(rep["all_checks_passed"], attr)


if __name__ == "__main__":
    unittest.main()
