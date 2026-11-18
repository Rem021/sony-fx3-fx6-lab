#!/usr/bin/env python3
"""Unit tests for Phase 343 (Stage 75 — 75/75 VM HIL Stages Milestone!):
Real-Hardware `ILME-FX3 Ver. 7.02` vs `ILME-FX6 Ver. 6.01` Wave-65:
- 75A: `Shooting -> [Zoom]` & `Setup -> [Zoom Ring Rotate]` — 3-step
  `[Zoom Range]` (`Optical zoom only` / `ClearImage Zoom` 1.5x 4K / 2.0x HD /
  `Digital Zoom` 4.0x, Still 3:2 FF/APS-C scales, Smart Zoom disabled in Movie
  and FF `L`), 8-step Standby/Rec speeds (`Zoom Lever 1st=3/2nd=8`, `Custom Key
  Z. Speed=3`, `Remote Zoom Speed=Variable/3`), Split Reset law (speeds
  Resettable vs `[Zoom Range]` & `[Zoom Ring Rotate]` Reset-immune), pre-entry
  lockouts (Still RAW / 119.88p / S&Q>=100fps / HDMI RAW / Breathing Comp.),
  active non-optical lockouts (`Focus Area` -> Center Priority, `Metering Mode`
  -> `[Multi]`, `Face/Eye Prior. in AF` + `Face Priority in Multi Metering` +
  `Tracking` disabled), vs `ILME-FX6 Ver. 6.01` `Zoom Type` (ZERO Digital
  Zoom) + `Handle Zoom` (`Off/Low=3/High=8/Variable`),
- 75B: `[Auto Slow Shutter]` (Movie-only default On, Resettable, 7-lockout
  matrix incl. Still/S&Q, S, M, fixed manual ISO, Flex Exp Shutter=Manual,
  Cine EI/Quick, Shutter Angle exclusion), `[ISO Range Limit]` (Reset-immune,
  governs Manual ISO only vs `ISO AUTO` right-wheel min/max), Still-only
  `[ISO AUTO Min. SS]` (strictly Still P/A + ISO AUTO, flash sync 1/250 s
  override, presets + 1/8000"..30", 0 hits in FX6 `appFw.so`), & Dual Base ISO
  truth (`[Base ISO]` 800/12800 visible ONLY in Cine EI/Quick, hidden elsewhere
  with per-Gamma 20x dual conversion gain matrix vs FX6 Base Sensitivity + AGC),
- 75C: Still `ARW` (`Compressed`/`Uncompressed` Resettable vs 100% dormant
  `Lossless Comp (L/M/S)` `EOPNOTSUPP=95` on `ALCIN_UUD`), `[JPEG/HEIF Switch]`
  & `[HLG Still Image]` (internal ELF typo `STILL_HLD_PHOTO_{OFF,ON}`, requires
  `Still + HEIF + File Format=HEIF + P/A/S/M`, forces `BT.2100/BT.2020`, ISO
  floor 100/125, disables PP/Creative Look/DRO), `[Sort Recording]` Reset-immune
  + `[Auto Switch Media]` Slot-1 spillover blocked `EROFS=30` vs FX6 zero Still,
- 75D: `[USB Connection Mode]` (4 active modes Reset-immune), **`[USB LUN
  Setting] = Single` exposing ONLY `Slot 1` (does NOT hide `Slot 1`!)** + MTP
  Slot-1 target + `usbg_storage.ko` macOS Spotlight/fseventsd/fsck_exfat hazard
  blocked by Tier-0 `Slot 1` `EROFS=30`, `[USB Power Supply]` `9V/3A` PD requiring
  `NP-FZ100` inserted (battery pull cuts power; battery-less needs `DC-C1` +
  `>=65W PD` + `5A` cable vs FX6 `19.5V DC IN`), Dual FX3+FX6 native `UVC/UAC`
  100% dormancy (`EOPNOTSUPP=95`), & `[Movie Rec During Streaming]` vs
  `[Rec. Media dur HDMI Output]` Slot-1 `EROFS=30` firewall
HIL (96 four-mode tests).
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
import realhw_zoom_ciz_autoslow_iso_arw_rawcomp_usblun_uvc_coemulator as p343  # noqa: E402

IS_CI = os.environ.get("GITHUB_ACTIONS", "").lower() == "true"


def _fast_suite_kwargs(**overrides: object) -> dict:
    """Fast config skipping unrelated optional stages 4..74 for Stage 75 isolation tests."""
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
]


class TestRealHwStage75ZoomCizAutoSlowIsoArwUsbLunUvc(unittest.TestCase):
    # ------------------------------------------------------------------
    # Donor Audit, Bounded O_RDONLY & 4-Mode Fallback Tests (Tests 01..14)
    # ------------------------------------------------------------------

    def test_01_milestone_constants_75_of_75(self) -> None:
        self.assertEqual(p343.PHASE_NUMBER, 343)
        self.assertEqual(p343.STAGE_INDEX, 75)
        self.assertEqual(p343.STAGE_TOTAL, 75)
        self.assertEqual(p343.MILESTONE_LABEL, "75/75")
        self.assertTrue(p343.IS_75TH_STAGE_MILESTONE)
        self.assertEqual(len(p343.DONOR_RELPATHS), 18)
        self.assertEqual(len(p343.EXPECTED_DONOR_BYTES), 18)
        self.assertEqual(len(p343.EXPECTED_COMPACT_DONOR_SHA256), 15)
        self.assertEqual(len(p343.EXPECTED_LARGE_HEAD4K_SHA256), 3)
        self.assertEqual(len(p343.LARGE_DONOR_WINDOWS), 3)

    def test_02_hard_safety_redlines_locked(self) -> None:
        self.assertTrue(p343.P8_CP_MUTATION_FORBIDDEN)
        self.assertTrue(p343.CNFLASHA_USERSPACE_WRITE_BLOCKED)
        self.assertFalse(p343.PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(p343.EMMC_WRITES_AUTHORIZED)
        self.assertFalse(p343.CROSS_MODEL_FLASH_AUTHORIZED)
        self.assertFalse(p343.HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        self.assertFalse(p343.OVERALL_READY_FOR_HARDWARE_ATTACH)
        self.assertFalse(p343.ISP_WRITE_AUTHORIZED)
        self.assertFalse(p343.SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(p343.EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        self.assertFalse(p343.SLOT1_AVF_INFO_MUTATED)
        self.assertEqual(p343.SLOT1_DATA_SECTOR_WRITES, 0)
        self.assertEqual(p343.EMMC_NFLASHA_WRITE_COUNT, 0)
        self.assertEqual(p343.RAW_FIRMWARE_BYTES_LEAKED, 0)
        self.assertEqual(p343.ZOOM_LEVER_1ST_DEFAULT_SPEED, 3)
        self.assertEqual(p343.ZOOM_LEVER_2ND_DEFAULT_SPEED, 8)
        self.assertEqual(p343.CIZ_4K_MAX_MAGNIFICATION, 1.5)
        self.assertEqual(p343.CIZ_HD_MAX_MAGNIFICATION, 2.0)
        self.assertEqual(p343.DIGITAL_ZOOM_MOVIE_MAX_MAGNIFICATION, 4.0)
        self.assertEqual(p343.AUTO_SLOW_SHUTTER_LOCKOUT_CONDITIONS_COUNT, 7)
        self.assertEqual(p343.DUAL_CONVERSION_GAIN_RATIO, 20)
        self.assertEqual(p343.RAW_FILE_TYPE_ACTIVE_OPTIONS_COUNT, 2)
        self.assertTrue(p343.STILL_HLG_PHOTO_TYPO_MATCHED)
        self.assertEqual(p343.USB_CONNECTION_ACTIVE_MODES_COUNT, 4)
        self.assertTrue(p343.USB_LUN_SINGLE_EXPOSES_SLOT1_ONLY)

    def test_03_clean_room_test_mode_both_env_vars(self) -> None:
        self.assertFalse(p343.clean_room_test_mode(env={}))
        self.assertTrue(p343.clean_room_test_mode(env={p343.ENV_FORCE_CLEAN_ROOM: "1"}))
        self.assertTrue(p343.clean_room_test_mode(env={p343.ENV_CLEAN_ROOM_TEST: "1"}))
        self.assertTrue(p343.clean_room_test_mode(force_clean_room=True, env={}))
        self.assertFalse(
            p343.clean_room_test_mode(
                force_clean_room=False,
                env={p343.ENV_FORCE_CLEAN_ROOM: "1", p343.ENV_CLEAN_ROOM_TEST: "1"},
            )
        )

    def test_04_resolve_mac_work_root_and_donor_availability_none_fallback(self) -> None:
        self.assertIsNone(
            p343.resolve_mac_work_root(
                env={p343.ENV_MAC_WORK_ROOT: p343.CLEAN_ROOM_SENTINEL_DIRNAME}
            )
        )
        self.assertIsNone(
            p343.resolve_mac_work_root(
                env={p343.ENV_MAC_ROOT: p343.CLEAN_ROOM_SENTINEL_DIRNAME}
            )
        )
        self.assertFalse(
            p343._local_donors_available(
                env={p343.ENV_MAC_WORK_ROOT: p343.CLEAN_ROOM_SENTINEL_DIRNAME}
            )
        )
        with tempfile.TemporaryDirectory() as td:
            with unittest.mock.patch.object(p343, "DEFAULT_REPO_ROOT", Path(td)):
                with unittest.mock.patch.object(p343, "LEGACY_MAC_ROOT", Path(td) / "none"):
                    self.assertIsNone(p343.resolve_mac_work_root(env={}))
                    self.assertFalse(p343._local_donors_available(env={}))
                    rep = p343.run_phase343_zoom_ciz_autoslow_iso_arw_rawcomp_usblun_uvc_coemulation(
                        env={}
                    )
                    self.assertTrue(rep["all_checks_passed"])
                    self.assertEqual(rep["source_mode"], p343.SOURCE_MODE_CLEAN_ROOM)
                    self.assertEqual(rep["redlines"]["raw_firmware_bytes_leaked"], 0)

    def test_05_clean_room_donor_audit_all_18_contracts(self) -> None:
        for env_key in (p343.ENV_FORCE_CLEAN_ROOM, p343.ENV_CLEAN_ROOM_TEST):
            audit = p343.inspect_phase343_wave65_donors(env={env_key: "1"})
            self.assertEqual(audit.source_mode, p343.SOURCE_MODE_CLEAN_ROOM)
            self.assertEqual(audit.donor_access_mode, p343.DONOR_ACCESS_MODE)
            self.assertEqual(audit.bounded_window_max_bytes, 4096)
            self.assertEqual(audit.donors_checked, 18)
            self.assertEqual(audit.donors_verified, 18)
            self.assertTrue(audit.all_contracts_verified)
            self.assertEqual(audit.raw_firmware_bytes_leaked, 0)

    def test_06_local_donor_o_rdonly_cold_audit_under_250ms(self) -> None:
        if not p343._local_donors_available():
            self.skipTest("Local Mac/work donors unavailable in clean-room environment")
        t0 = time.perf_counter()
        audit = p343.inspect_phase343_wave65_donors(force_clean_room=False)
        elapsed_s = time.perf_counter() - t0
        self.assertEqual(audit.source_mode, p343.SOURCE_MODE_LOCAL_DONOR)
        self.assertEqual(audit.donors_checked, 18)
        self.assertEqual(audit.donors_verified, 18)
        self.assertTrue(audit.all_contracts_verified)
        self.assertEqual(audit.raw_firmware_bytes_leaked, 0)
        self.assertLess(elapsed_s, 0.25)

    def test_07_compact_donor_tokens_across_en_sc_tc_ja_kmods_fx6(self) -> None:
        self.assertEqual(p343.EXPECTED_DONOR_BYTES["fx3_string_en_f"], 373_820)
        self.assertEqual(p343.EXPECTED_DONOR_BYTES["fx3_saveload"], 18_760)
        self.assertEqual(p343.EXPECTED_DONOR_BYTES["fx3_usbg_storage"], 104_288)
        self.assertEqual(p343.EXPECTED_DONOR_BYTES["fx3_usb_f_uvc"], 78_840)
        self.assertEqual(p343.EXPECTED_DONOR_BYTES["fx3_g_webcam"], 13_728)
        self.assertEqual(p343.EXPECTED_DONOR_BYTES["fx6_string_en"], 118_208)
        for tok in (
            b"Zoom Range",
            b"ClearImage Zoom",
            b"Digital Zoom",
            b"Zoom Ring Rotate",
            b"Auto Slow Shutter",
            b"ISO Range Limit",
            b"ISO AUTO Min. SS",
            b"Base ISO",
            b"RAW File Type",
            b"Lossless Comp",
            b"HLG Still Image",
            b"Sort Recording",
            b"USB Connection Mode",
            b"USB LUN Setting",
            b"USB Power Supply",
            b"Movie Rec During Streaming",
        ):
            self.assertIn(tok, p343.COMPACT_DONOR_TOKENS["fx3_string_en_f"])
        self.assertIn(b"Handle Zoom", p343.COMPACT_DONOR_TOKENS["fx6_string_en"])
        self.assertIn(b"Base Sensitivity", p343.COMPACT_DONOR_TOKENS["fx6_string_en"])

    def test_08_bounded_window_reader_rejects_oversized_or_negative_reads(self) -> None:
        with tempfile.NamedTemporaryFile() as tf:
            tf.write(b"ABCDEFGH")
            tf.flush()
            self.assertEqual(
                p343._read_bounded_window_o_rdonly(Path(tf.name), 2, 4), b"CDEF"
            )
            with self.assertRaises(p343.Stage75Phase343Error):
                p343._read_bounded_window_o_rdonly(Path(tf.name), 0, 4097)
            with self.assertRaises(p343.Stage75Phase343Error):
                p343._read_bounded_window_o_rdonly(Path(tf.name), 0, 0)
            with self.assertRaises(p343.Stage75Phase343Error):
                p343._read_bounded_window_o_rdonly(Path(tf.name), -1, 16)

    def test_09_donor_audit_detects_tampered_expected_digest(self) -> None:
        if not p343._local_donors_available():
            self.skipTest("Local Mac/work donors unavailable in clean-room environment")
        bad_digests = dict(p343.EXPECTED_COMPACT_DONOR_SHA256)
        bad_digests["fx3_string_en_f"] = "0" * 64
        with unittest.mock.patch.object(
            p343, "EXPECTED_COMPACT_DONOR_SHA256", bad_digests
        ):
            audit = p343.inspect_phase343_wave65_donors(force_clean_room=False)
            self.assertFalse(audit.all_contracts_verified)
            self.assertEqual(audit.donors_verified, 17)
            self.assertFalse(audit.artifacts["fx3_string_en_f"].expected_sha256_matched)

    def test_10_json_output_contains_zero_raw_firmware_bytes(self) -> None:
        rep = p343.run_phase343_zoom_ciz_autoslow_iso_arw_rawcomp_usblun_uvc_coemulation(
            force_clean_room=True
        )
        txt = json.dumps(rep)
        self.assertNotIn("\\x7fELF", txt)
        self.assertNotIn("BK4\\x00", txt)
        self.assertEqual(rep["redlines"]["raw_firmware_bytes_leaked"], 0)

    def test_11_full_phase343_payload_passes_clean_room(self) -> None:
        rep = p343.run_phase343_zoom_ciz_autoslow_iso_arw_rawcomp_usblun_uvc_coemulation(
            force_clean_room=True
        )
        self.assertEqual(rep["schema"], p343.SCHEMA_ID)
        self.assertEqual(rep["milestone"], "75/75")
        self.assertTrue(rep["is_75th_stage_milestone"])
        self.assertTrue(rep["all_checks_passed"])
        self.assertEqual(len(rep["audit_digest_sha256"]), 64)

    def test_12_full_phase343_payload_passes_local_donor_mode(self) -> None:
        if not p343._local_donors_available():
            self.skipTest("Local Mac/work donors unavailable in clean-room environment")
        rep = p343.run_phase343_zoom_ciz_autoslow_iso_arw_rawcomp_usblun_uvc_coemulation(
            force_clean_room=False
        )
        self.assertEqual(rep["source_mode"], p343.SOURCE_MODE_LOCAL_DONOR)
        self.assertTrue(rep["all_checks_passed"])
        self.assertEqual(rep["donor_audit"]["donors_checked"], 18)
        self.assertEqual(rep["donor_audit"]["donors_verified"], 18)

    def test_13_fx3_large_windows_contain_wave65_symbols_incl_typo_and_dormant(self) -> None:
        labels = {lbl for _, lbl, _ in p343.LARGE_DONOR_WINDOWS["fx3_appfw"]}
        for expected in (
            "BKID_APP_setting_zoom_setting",
            "BKID_APP_setting_1st_zoom_spd_stby",
            "BKID_APP_setting_2nd_zoom_spd_rec",
            "BKID_APP_setting_fixed_zoom_speed_stby",
            "BKID_APP_setting_remote_fixed_zoom_speed_stby",
            "BKID_APP_setting_zoom_direction",
            "BKID_APP_setting_auto_slow_shutter",
            "BKID_APP_setting_iso_range_limit_min_movie",
            "BKID_APP_setting_iso_auto_min_s_s",
            "BKID_APP_setting_base_iso",
            "BKID_APP_setting_still_raw_file_type",
            "RAW_FILE_TYPE_LOSSLESS",
            "BKID_APP_setting_still_hlg_photo",
            "STILL_HLD_PHOTO_OFF",
            "STILL_HLD_PHOTO_ON",
            "VAL_HAITA_model_diff_normal_iso_range_min_in_still_hlg_photo_on",
            "BKID_APP_setting_usb_connection_method",
            "BKID_APP_setting_lun_settings",
            "BKID_APP_setting_usb_supply",
            "USB_CONNECTION_USB_STREAMING",
            "BKID_APP_setting_movie_network_streaming_movie_rec_dur_distribution",
            "BKID_APP_setting_rec_media_during_hdmi_output",
        ):
            self.assertIn(expected, labels)

    def test_14_fx6_large_windows_contain_zoom_base_sensitivity_uvc_dcin(self) -> None:
        labels = {lbl for _, lbl, _ in p343.LARGE_DONOR_WINDOWS["fx6_appfw"]}
        for expected in (
            "VAL_setting_zoom_setting_",
            "CLEAR_IMAGE_ZOOM",
            "BKID_APP_SETTING_BASE_ISO",
            "BKID_APP_SETTING_BASE_SENSITIVITY",
            "BKID_APP_SETTING_AGC_LIMIT",
            "BKID_APP_SETTING_USB_STREAMING_PROCAM",
            "BKID_APP_SETTING_HANDLE_ZOOM",
            "BKID_APP_SETTING_DC_LOW_VOLT",
        ):
            self.assertIn(expected, labels)

    # ------------------------------------------------------------------
    # Sub-Model 75A: Zoom Range, Speeds, Ring Rotate & FX6 (Tests 15..32)
    # ------------------------------------------------------------------

    def test_15_75a_ciz_movie_4k_and_hd_magnification(self) -> None:
        r4k = p343.simulate_zoom_range_speeds_ring_rotate_and_fx6_zoom_hil(
            shoot_mode=p343.SHOOT_MODE_MOVIE,
            movie_resolution="4K",
            zoom_range="ClearImage Zoom",
        )
        self.assertTrue(r4k.admitted)
        self.assertEqual(r4k.effective_max_magnification, 1.5)
        self.assertTrue(r4k.smart_zoom_disabled_in_movie)

        rhd = p343.simulate_zoom_range_speeds_ring_rotate_and_fx6_zoom_hil(
            shoot_mode=p343.SHOOT_MODE_MOVIE,
            movie_resolution="HD",
            zoom_range="ClearImage Zoom",
        )
        self.assertTrue(rhd.admitted)
        self.assertEqual(rhd.effective_max_magnification, 2.0)

    def test_16_75a_digital_zoom_movie_4x_ff_and_apsc(self) -> None:
        for apsc in (False, True):
            r = p343.simulate_zoom_range_speeds_ring_rotate_and_fx6_zoom_hil(
                shoot_mode=p343.SHOOT_MODE_MOVIE,
                apsc_s35_enabled=apsc,
                zoom_range="Digital Zoom",
            )
            self.assertTrue(r.admitted)
            self.assertEqual(r.effective_max_magnification, 4.0)

    def test_17_75a_still_3_2_ff_and_apsc_ciz_digital_magnification_table(self) -> None:
        expected_ciz_ff = {"L": 2.0, "M": 3.1, "S": 4.0}
        expected_dig_ff = {"L": 4.0, "M": 6.1, "S": 8.0}
        for sz, mag in expected_ciz_ff.items():
            r = p343.simulate_zoom_range_speeds_ring_rotate_and_fx6_zoom_hil(
                shoot_mode=p343.SHOOT_MODE_STILL,
                still_file_format="JPEG",
                still_image_size=sz,
                apsc_s35_enabled=False,
                zoom_range="ClearImage Zoom",
            )
            self.assertTrue(r.admitted, sz)
            self.assertEqual(r.effective_max_magnification, mag, sz)
        for sz, mag in expected_dig_ff.items():
            r = p343.simulate_zoom_range_speeds_ring_rotate_and_fx6_zoom_hil(
                shoot_mode=p343.SHOOT_MODE_STILL,
                still_file_format="HEIF",
                still_image_size=sz,
                apsc_s35_enabled=False,
                zoom_range="Digital Zoom",
            )
            self.assertTrue(r.admitted, sz)
            self.assertEqual(r.effective_max_magnification, mag, sz)
        r_apsc_m = p343.simulate_zoom_range_speeds_ring_rotate_and_fx6_zoom_hil(
            shoot_mode=p343.SHOOT_MODE_STILL,
            still_file_format="JPEG",
            still_image_size="M",
            apsc_s35_enabled=True,
            zoom_range="ClearImage Zoom",
        )
        self.assertTrue(r_apsc_m.admitted)
        self.assertEqual(r_apsc_m.effective_max_magnification, 2.6)

    def test_18_75a_smart_zoom_disabled_in_movie_sq_and_still_l_or_raw(self) -> None:
        for mode in (p343.SHOOT_MODE_MOVIE, p343.SHOOT_MODE_SQ):
            rej = p343.simulate_zoom_range_speeds_ring_rotate_and_fx6_zoom_hil(
                shoot_mode=mode,
                zoom_range="Smart Zoom",
            )
            self.assertFalse(rej.admitted, mode)
            self.assertEqual(rej.errno_code, p343.EOPNOTSUPP_ERRNO)

        rej_l = p343.simulate_zoom_range_speeds_ring_rotate_and_fx6_zoom_hil(
            shoot_mode=p343.SHOOT_MODE_STILL,
            still_file_format="JPEG",
            still_image_size="L",
            zoom_range="Smart Zoom",
        )
        self.assertFalse(rej_l.admitted)
        self.assertEqual(rej_l.errno_code, p343.EOPNOTSUPP_ERRNO)

        ok_m = p343.simulate_zoom_range_speeds_ring_rotate_and_fx6_zoom_hil(
            shoot_mode=p343.SHOOT_MODE_STILL,
            still_file_format="JPEG",
            still_image_size="M",
            zoom_range="Smart Zoom",
        )
        self.assertTrue(ok_m.admitted)
        self.assertEqual(ok_m.effective_max_magnification, 1.5)

    def test_19_75a_dual_segment_zoom_lever_and_custom_remote_speeds_1_to_8(self) -> None:
        r = p343.simulate_zoom_range_speeds_ring_rotate_and_fx6_zoom_hil(
            zoom_lever_1st_standby=1,
            zoom_lever_1st_rec=2,
            zoom_lever_2nd_standby=7,
            zoom_lever_2nd_rec=5,
            custom_key_zoom_speed_standby=4,
            custom_key_zoom_speed_rec=6,
            remote_zoom_speed_type="Fixed",
            remote_zoom_fixed_standby=2,
            remote_zoom_fixed_rec=8,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.effective_zoom_lever_1st_standby, 1)
        self.assertEqual(r.effective_zoom_lever_1st_rec, 2)
        self.assertEqual(r.effective_zoom_lever_2nd_standby, 7)
        self.assertEqual(r.effective_zoom_lever_2nd_rec, 5)
        self.assertEqual(r.effective_custom_key_speed_standby, 4)
        self.assertEqual(r.effective_custom_key_speed_rec, 6)
        self.assertEqual(r.effective_remote_speed_type, "Fixed")
        self.assertEqual(r.effective_remote_fixed_speed_standby, 2)
        self.assertEqual(r.effective_remote_fixed_speed_rec, 8)

    def test_20_75a_split_reset_law_speeds_reset_while_range_and_ring_survive(self) -> None:
        r = p343.simulate_zoom_range_speeds_ring_rotate_and_fx6_zoom_hil(
            zoom_range="ClearImage Zoom",
            zoom_ring_rotate="Right(W)/Left(T)",
            zoom_lever_1st_standby=6,
            zoom_lever_1st_rec=2,
            zoom_lever_2nd_standby=5,
            zoom_lever_2nd_rec=4,
            custom_key_zoom_speed_standby=7,
            custom_key_zoom_speed_rec=1,
            remote_zoom_speed_type="Fixed",
            remote_zoom_fixed_standby=6,
            remote_zoom_fixed_rec=8,
            camera_settings_reset_applied=True,
        )
        self.assertTrue(r.admitted)
        self.assertTrue(r.zoom_speeds_resettable)
        self.assertFalse(r.zoom_range_resettable)
        self.assertFalse(r.zoom_ring_rotate_resettable)
        # Speeds reset to factory defaults
        self.assertEqual(r.effective_zoom_lever_1st_standby, 3)
        self.assertEqual(r.effective_zoom_lever_1st_rec, 3)
        self.assertEqual(r.effective_zoom_lever_2nd_standby, 8)
        self.assertEqual(r.effective_zoom_lever_2nd_rec, 8)
        self.assertEqual(r.effective_custom_key_speed_standby, 3)
        self.assertEqual(r.effective_custom_key_speed_rec, 3)
        self.assertEqual(r.effective_remote_speed_type, "Variable")
        self.assertEqual(r.effective_remote_fixed_speed_standby, 3)
        self.assertEqual(r.effective_remote_fixed_speed_rec, 3)
        # Zoom Range and Zoom Ring Rotate survive Reset
        self.assertEqual(r.effective_zoom_range, "ClearImage Zoom")
        self.assertEqual(r.effective_zoom_ring_rotate, "Right(W)/Left(T)")

    def test_21_75a_initialize_restores_reset_immune_zoom_range_and_ring_rotate(self) -> None:
        r = p343.simulate_zoom_range_speeds_ring_rotate_and_fx6_zoom_hil(
            zoom_range="Digital Zoom",
            zoom_ring_rotate="Right(W)/Left(T)",
            initialize_applied=True,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.effective_zoom_range, "Optical zoom only")
        self.assertEqual(r.effective_zoom_ring_rotate, "Left(W)/Right(T)")
        self.assertEqual(r.effective_max_magnification, 1.0)

    def test_22_75a_preentry_lockout_still_raw_formats(self) -> None:
        for fmt in ("RAW", "RAW & JPEG", "RAW & HEIF"):
            for zr in ("ClearImage Zoom", "Digital Zoom"):
                rej = p343.simulate_zoom_range_speeds_ring_rotate_and_fx6_zoom_hil(
                    shoot_mode=p343.SHOOT_MODE_STILL,
                    still_file_format=fmt,
                    zoom_range=zr,
                )
                self.assertFalse(rej.admitted, f"{fmt}+{zr}")
                self.assertEqual(rej.errno_code, p343.EOPNOTSUPP_ERRNO)

    def test_23_75a_preentry_lockout_movie_11988p_and_100p(self) -> None:
        for fps in (100.0, 119.88):
            for zr in ("ClearImage Zoom", "Digital Zoom"):
                rej = p343.simulate_zoom_range_speeds_ring_rotate_and_fx6_zoom_hil(
                    shoot_mode=p343.SHOOT_MODE_MOVIE,
                    fps=fps,
                    zoom_range=zr,
                )
                self.assertFalse(rej.admitted, f"{fps}+{zr}")
                self.assertEqual(rej.errno_code, p343.EOPNOTSUPP_ERRNO)

    def test_24_75a_preentry_lockout_sq_100_120fps_vs_allowed_sq_60fps(self) -> None:
        for fps in (100.0, 120.0):
            rej = p343.simulate_zoom_range_speeds_ring_rotate_and_fx6_zoom_hil(
                shoot_mode=p343.SHOOT_MODE_SQ,
                fps=fps,
                zoom_range="ClearImage Zoom",
            )
            self.assertFalse(rej.admitted)
            self.assertEqual(rej.errno_code, p343.EOPNOTSUPP_ERRNO)

        ok = p343.simulate_zoom_range_speeds_ring_rotate_and_fx6_zoom_hil(
            shoot_mode=p343.SHOOT_MODE_SQ,
            fps=60.0,
            zoom_range="ClearImage Zoom",
        )
        self.assertTrue(ok.admitted)

    def test_25_75a_preentry_lockout_hdmi_raw_and_breathing_comp(self) -> None:
        rej_raw = p343.simulate_zoom_range_speeds_ring_rotate_and_fx6_zoom_hil(
            hdmi_raw_output=True,
            zoom_range="ClearImage Zoom",
        )
        self.assertFalse(rej_raw.admitted)
        self.assertEqual(rej_raw.errno_code, p343.EOPNOTSUPP_ERRNO)

        rej_bc = p343.simulate_zoom_range_speeds_ring_rotate_and_fx6_zoom_hil(
            breathing_comp_enabled=True,
            zoom_range="Digital Zoom",
        )
        self.assertFalse(rej_bc.admitted)
        self.assertEqual(rej_bc.errno_code, p343.EOPNOTSUPP_ERRNO)

    def test_26_75a_active_non_optical_zoom_locks_focus_metering_face_tracking(self) -> None:
        ok = p343.simulate_zoom_range_speeds_ring_rotate_and_fx6_zoom_hil(
            zoom_range="ClearImage Zoom",
        )
        self.assertTrue(ok.admitted)
        self.assertTrue(ok.non_optical_zoom_active)
        self.assertTrue(ok.focus_area_disabled)
        self.assertEqual(ok.effective_focus_area, "Center Priority")
        self.assertTrue(ok.metering_locked_multi)
        self.assertEqual(ok.effective_metering_mode, "Multi")
        self.assertTrue(ok.face_eye_prior_af_disabled)
        self.assertTrue(ok.face_prior_multi_metering_disabled)
        self.assertTrue(ok.tracking_disabled)

    def test_27_75a_active_non_optical_zoom_rejects_bypass_requests(self) -> None:
        for bad_kwargs in (
            dict(zoom_range="ClearImage Zoom", requested_focus_area="Wide"),
            dict(zoom_range="Digital Zoom", requested_metering_mode="Spot"),
            dict(zoom_range="ClearImage Zoom", requested_face_eye_prior_af=True),
            dict(zoom_range="Digital Zoom", requested_face_prior_multi_metering=True),
            dict(zoom_range="ClearImage Zoom", requested_tracking=True),
        ):
            rej = p343.simulate_zoom_range_speeds_ring_rotate_and_fx6_zoom_hil(**bad_kwargs)
            self.assertFalse(rej.admitted, str(bad_kwargs))
            self.assertEqual(rej.errno_code, p343.EOPNOTSUPP_ERRNO)

    def test_28_75a_fx6_zoom_type_zero_digital_zoom_and_zero_smart_zoom(self) -> None:
        for zr in ("Digital Zoom", "Smart Zoom"):
            rej = p343.simulate_zoom_range_speeds_ring_rotate_and_fx6_zoom_hil(
                body_profile=p343.BODY_MODEL_FX6,
                fw_version=p343.FW_VER_601,
                zoom_range=zr,
            )
            self.assertFalse(rej.admitted, zr)
            self.assertEqual(rej.errno_code, p343.EOPNOTSUPP_ERRNO)
            self.assertFalse(rej.fx6_digital_zoom_supported)

    def test_29_75a_fx6_ciz_locked_on_sq_over_60fps_and_raw_codec(self) -> None:
        rej_sq = p343.simulate_zoom_range_speeds_ring_rotate_and_fx6_zoom_hil(
            body_profile=p343.BODY_MODEL_FX6,
            fw_version=p343.FW_VER_601,
            shoot_mode=p343.SHOOT_MODE_SQ,
            fps=120.0,
            zoom_range="ClearImage Zoom",
        )
        self.assertFalse(rej_sq.admitted)
        self.assertEqual(rej_sq.errno_code, p343.EOPNOTSUPP_ERRNO)

        for raw_codec in ("RAW", "RAW & XAVC-I", "RAW(HDMI)", "RAW(HDMI) & XAVC-I"):
            rej_raw = p343.simulate_zoom_range_speeds_ring_rotate_and_fx6_zoom_hil(
                body_profile=p343.BODY_MODEL_FX6,
                fw_version=p343.FW_VER_601,
                fx6_codec=raw_codec,
                zoom_range="ClearImage Zoom",
            )
            self.assertFalse(rej_raw.admitted, raw_codec)
            self.assertEqual(rej_raw.errno_code, p343.EOPNOTSUPP_ERRNO)

    def test_30_75a_fx6_handle_zoom_modes_off_low_high_variable(self) -> None:
        expected = {"Off": None, "Low": 3, "High": 8, "Variable": 8}
        for mode, step in expected.items():
            r = p343.simulate_zoom_range_speeds_ring_rotate_and_fx6_zoom_hil(
                body_profile=p343.BODY_MODEL_FX6,
                fw_version=p343.FW_VER_601,
                zoom_range="ClearImage Zoom",
                fx6_handle_zoom=mode,
            )
            self.assertTrue(r.admitted, mode)
            self.assertEqual(r.fx6_handle_zoom_mode, mode)
            self.assertEqual(r.fx6_handle_zoom_speed_step, step)
            self.assertEqual(r.effective_max_magnification, 1.5)

    def test_31_75a_fx3_optical_allows_wide_spot_and_tracking(self) -> None:
        r = p343.simulate_zoom_range_speeds_ring_rotate_and_fx6_zoom_hil(
            zoom_range="Optical zoom only",
            requested_focus_area="Wide",
            requested_metering_mode="Spot",
            requested_face_eye_prior_af=True,
            requested_tracking=True,
        )
        self.assertTrue(r.admitted)
        self.assertFalse(r.non_optical_zoom_active)
        self.assertEqual(r.effective_focus_area, "Wide")
        self.assertEqual(r.effective_metering_mode, "Spot")
        self.assertFalse(r.tracking_disabled)

    def test_32_75a_invalid_inputs_raise_stage75_error(self) -> None:
        for bad_kwargs in (
            dict(body_profile="FX30"),
            dict(fw_version="9.00"),
            dict(shoot_mode="TimeLapse"),
            dict(still_file_format="DNG"),
            dict(still_image_size="XL"),
            dict(movie_resolution="8K"),
            dict(zoom_range="SuperZoom"),
            dict(remote_zoom_speed_type="Ramp"),
            dict(zoom_ring_rotate="Up/Down"),
            dict(fx6_codec="ProRes"),
            dict(fx6_handle_zoom="Turbo"),
            dict(fps=0.0),
            dict(zoom_lever_1st_standby=0),
            dict(zoom_lever_2nd_rec=9),
            dict(custom_key_zoom_speed_standby=True),
        ):
            with self.assertRaises(p343.Stage75Phase343Error, msg=str(bad_kwargs)):
                p343.simulate_zoom_range_speeds_ring_rotate_and_fx6_zoom_hil(**bad_kwargs)

    # ------------------------------------------------------------------
    # Sub-Model 75B: Auto Slow Shutter, ISO Limit, Min. SS, Dual Base (33..50)
    # ------------------------------------------------------------------

    def test_33_75b_auto_slow_shutter_movie_p_iso_auto_default_on_and_resettable(self) -> None:
        r = p343.simulate_auto_slow_shutter_iso_limit_min_ss_dual_base_hil(
            shoot_mode=p343.SHOOT_MODE_MOVIE,
            exposure_mode="P",
            iso_mode="ISO AUTO",
            auto_slow_shutter_requested="Off",
        )
        self.assertTrue(r.admitted)
        self.assertFalse(r.auto_slow_shutter_locked)
        self.assertEqual(r.effective_auto_slow_shutter, "Off")
        self.assertTrue(r.auto_slow_shutter_resettable)

        r_rst = p343.simulate_auto_slow_shutter_iso_limit_min_ss_dual_base_hil(
            shoot_mode=p343.SHOOT_MODE_MOVIE,
            exposure_mode="P",
            iso_mode="ISO AUTO",
            auto_slow_shutter_requested="Off",
            camera_settings_reset_applied=True,
        )
        self.assertTrue(r_rst.admitted)
        self.assertEqual(r_rst.effective_auto_slow_shutter, "On")

    def test_34_75b_auto_slow_shutter_all_7_lockout_conditions(self) -> None:
        lockout_cases = (
            dict(shoot_mode=p343.SHOOT_MODE_STILL),
            dict(shoot_mode=p343.SHOOT_MODE_SQ),
            dict(shoot_mode=p343.SHOOT_MODE_MOVIE, exposure_mode="S"),
            dict(shoot_mode=p343.SHOOT_MODE_MOVIE, exposure_mode="M"),
            dict(shoot_mode=p343.SHOOT_MODE_MOVIE, iso_mode="Manual"),
            dict(
                shoot_mode=p343.SHOOT_MODE_MOVIE,
                exposure_mode="Flexible Exp. Mode",
                flex_exp_shutter_auto=False,
            ),
            dict(shoot_mode=p343.SHOOT_MODE_MOVIE, log_shooting="Cine EI"),
            dict(shoot_mode=p343.SHOOT_MODE_MOVIE, log_shooting="Cine EI Quick"),
            dict(shoot_mode=p343.SHOOT_MODE_MOVIE, shutter_mode="Angle"),
        )
        for kw in lockout_cases:
            rej = p343.simulate_auto_slow_shutter_iso_limit_min_ss_dual_base_hil(
                auto_slow_shutter_requested="On",
                **kw,
            )
            self.assertFalse(rej.admitted, str(kw))
            self.assertEqual(rej.errno_code, p343.EOPNOTSUPP_ERRNO)
            self.assertTrue(rej.auto_slow_shutter_locked)
            self.assertGreaterEqual(len(rej.auto_slow_shutter_lock_reasons), 1)

    def test_35_75b_auto_slow_shutter_allowed_in_flex_exp_auto_shutter_and_flex_iso(self) -> None:
        r_flex = p343.simulate_auto_slow_shutter_iso_limit_min_ss_dual_base_hil(
            shoot_mode=p343.SHOOT_MODE_MOVIE,
            exposure_mode="Flexible Exp. Mode",
            flex_exp_shutter_auto=True,
            iso_mode="ISO AUTO",
            auto_slow_shutter_requested="On",
        )
        self.assertTrue(r_flex.admitted)
        self.assertFalse(r_flex.auto_slow_shutter_locked)
        self.assertEqual(r_flex.effective_auto_slow_shutter, "On")

        r_fiso = p343.simulate_auto_slow_shutter_iso_limit_min_ss_dual_base_hil(
            shoot_mode=p343.SHOOT_MODE_MOVIE,
            exposure_mode="P",
            log_shooting="Flexible ISO",
            iso_mode="ISO AUTO",
            auto_slow_shutter_requested="On",
        )
        self.assertTrue(r_fiso.admitted)
        self.assertFalse(r_fiso.auto_slow_shutter_locked)

    def test_36_75b_iso_range_limit_reset_immune_and_governs_manual_only(self) -> None:
        r = p343.simulate_auto_slow_shutter_iso_limit_min_ss_dual_base_hil(
            shoot_mode=p343.SHOOT_MODE_MOVIE,
            iso_mode="ISO AUTO",
            iso_range_limit_min=640,
            iso_range_limit_max=25600,
            iso_auto_min_limit=100,
            iso_auto_max_limit=12800,
            camera_settings_reset_applied=True,
        )
        self.assertTrue(r.admitted)
        self.assertFalse(r.iso_range_limit_resettable)
        self.assertTrue(r.iso_range_limit_governs_manual_only)
        # Survives Camera Settings Reset
        self.assertEqual(r.effective_iso_range_limit_min, 640)
        self.assertEqual(r.effective_iso_range_limit_max, 25600)
        # Does NOT leak into ISO AUTO limits
        self.assertEqual(r.effective_iso_auto_min_limit, 100)
        self.assertEqual(r.effective_iso_auto_max_limit, 12800)

        # Manual ISO outside [ISO Range Limit] is rejected EINVAL
        rej_man = p343.simulate_auto_slow_shutter_iso_limit_min_ss_dual_base_hil(
            shoot_mode=p343.SHOOT_MODE_MOVIE,
            iso_mode="Manual",
            manual_iso=320,
            iso_range_limit_min=640,
            iso_range_limit_max=25600,
        )
        self.assertFalse(rej_man.admitted)
        self.assertEqual(rej_man.errno_code, p343.EINVAL_ERRNO)

    def test_37_75b_initialize_restores_iso_range_limit_defaults(self) -> None:
        r = p343.simulate_auto_slow_shutter_iso_limit_min_ss_dual_base_hil(
            iso_range_limit_min=640,
            iso_range_limit_max=25600,
            initialize_applied=True,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.effective_iso_range_limit_min, 80)
        self.assertEqual(r.effective_iso_range_limit_max, 102400)

    def test_38_75b_iso_auto_min_ss_strictly_still_p_or_a_plus_iso_auto_only(self) -> None:
        for exp in ("P", "A"):
            for val in ("SLOWER", "SLOW", "STD", "FAST", "FASTER", "1/250", "1/8000", '30"'):
                r = p343.simulate_auto_slow_shutter_iso_limit_min_ss_dual_base_hil(
                    shoot_mode=p343.SHOOT_MODE_STILL,
                    exposure_mode=exp,
                    iso_mode="ISO AUTO",
                    iso_auto_min_ss_requested=val,
                )
                self.assertTrue(r.admitted, f"{exp}+{val}")
                self.assertTrue(r.iso_auto_min_ss_enabled)
                self.assertEqual(r.effective_iso_auto_min_ss, val)

    def test_39_75b_iso_auto_min_ss_blocked_in_movie_sq_and_still_s_m_or_manual_iso(self) -> None:
        blocked = (
            dict(shoot_mode=p343.SHOOT_MODE_MOVIE, exposure_mode="P", iso_mode="ISO AUTO"),
            dict(shoot_mode=p343.SHOOT_MODE_SQ, exposure_mode="A", iso_mode="ISO AUTO"),
            dict(shoot_mode=p343.SHOOT_MODE_STILL, exposure_mode="S", iso_mode="ISO AUTO"),
            dict(shoot_mode=p343.SHOOT_MODE_STILL, exposure_mode="M", iso_mode="ISO AUTO"),
            dict(shoot_mode=p343.SHOOT_MODE_STILL, exposure_mode="P", iso_mode="Manual"),
        )
        for kw in blocked:
            rej = p343.simulate_auto_slow_shutter_iso_limit_min_ss_dual_base_hil(
                iso_auto_min_ss_requested="1/125",
                **kw,
            )
            self.assertFalse(rej.admitted, str(kw))
            self.assertEqual(rej.errno_code, p343.EOPNOTSUPP_ERRNO)
            self.assertFalse(rej.iso_auto_min_ss_enabled)

    def test_40_75b_iso_auto_min_ss_flash_sync_1_250_override_and_resettable(self) -> None:
        r = p343.simulate_auto_slow_shutter_iso_limit_min_ss_dual_base_hil(
            shoot_mode=p343.SHOOT_MODE_STILL,
            exposure_mode="A",
            iso_mode="ISO AUTO",
            iso_auto_min_ss_requested="1/500",
            external_flash_attached=True,
        )
        self.assertTrue(r.admitted)
        self.assertTrue(r.flash_sync_override_active)
        self.assertEqual(r.flash_sync_override_shutter, "1/250")

        r_rst = p343.simulate_auto_slow_shutter_iso_limit_min_ss_dual_base_hil(
            shoot_mode=p343.SHOOT_MODE_STILL,
            exposure_mode="P",
            iso_mode="ISO AUTO",
            iso_auto_min_ss_requested="FASTER",
            camera_settings_reset_applied=True,
        )
        self.assertTrue(r_rst.admitted)
        self.assertTrue(r_rst.iso_auto_min_ss_resettable)
        self.assertEqual(r_rst.effective_iso_auto_min_ss, "STD")

    def test_41_75b_base_iso_menu_visible_only_in_cine_ei_and_cine_ei_quick(self) -> None:
        for log_mode in ("Cine EI", "Cine EI Quick"):
            r = p343.simulate_auto_slow_shutter_iso_limit_min_ss_dual_base_hil(
                shoot_mode=p343.SHOOT_MODE_MOVIE,
                log_shooting=log_mode,
                base_iso_requested=12800,
            )
            self.assertTrue(r.admitted, log_mode)
            self.assertTrue(r.base_iso_menu_visible)
            self.assertEqual(r.effective_base_iso, 12800)

        for non_ei in ("Off", "Flexible ISO"):
            rej = p343.simulate_auto_slow_shutter_iso_limit_min_ss_dual_base_hil(
                shoot_mode=p343.SHOOT_MODE_MOVIE,
                log_shooting=non_ei,
                base_iso_requested=12800,
            )
            self.assertFalse(rej.admitted, non_ei)
            self.assertEqual(rej.errno_code, p343.EOPNOTSUPP_ERRNO)
            self.assertFalse(rej.base_iso_menu_visible)

    def test_42_75b_per_gamma_20x_dual_base_iso_matrix_all_15_profiles(self) -> None:
        self.assertEqual(len(p343.GAMMA_DUAL_BASE_ISO_MATRIX), 15)
        for gamma, (low_iso, high_iso) in p343.GAMMA_DUAL_BASE_ISO_MATRIX.items():
            self.assertEqual(high_iso, low_iso * 20, gamma)
            r = p343.simulate_auto_slow_shutter_iso_limit_min_ss_dual_base_hil(
                shoot_mode=p343.SHOOT_MODE_MOVIE,
                gamma_profile=gamma,
            )
            self.assertTrue(r.admitted, gamma)
            self.assertEqual(r.dual_base_low_iso, low_iso, gamma)
            self.assertEqual(r.dual_base_high_iso, high_iso, gamma)
            self.assertEqual(r.dual_conversion_gain_ratio, 20, gamma)

    def test_43_75b_key_gamma_tiers_exact_pairs(self) -> None:
        self.assertEqual(p343.GAMMA_DUAL_BASE_ISO_MATRIX["S-Log3"], (640, 12800))
        self.assertEqual(p343.GAMMA_DUAL_BASE_ISO_MATRIX["S-Log2"], (640, 12800))
        self.assertEqual(p343.GAMMA_DUAL_BASE_ISO_MATRIX["ITU709(800%)"], (640, 12800))
        self.assertEqual(p343.GAMMA_DUAL_BASE_ISO_MATRIX["S-Cinetone(PP11)"], (100, 2000))
        self.assertEqual(p343.GAMMA_DUAL_BASE_ISO_MATRIX["HLG"], (100, 2000))
        self.assertEqual(p343.GAMMA_DUAL_BASE_ISO_MATRIX["PP Off"], (80, 1600))
        self.assertEqual(p343.GAMMA_DUAL_BASE_ISO_MATRIX["Cine1"], (64, 1280))
        self.assertEqual(p343.GAMMA_DUAL_BASE_ISO_MATRIX["HLG1"], (50, 1000))
        self.assertEqual(p343.GAMMA_DUAL_BASE_ISO_MATRIX["Cine2"], (50, 1000))

    def test_44_75b_fx6_zero_iso_auto_min_ss_and_custom_base_sensitivity(self) -> None:
        rej = p343.simulate_auto_slow_shutter_iso_limit_min_ss_dual_base_hil(
            body_profile=p343.BODY_MODEL_FX6,
            fw_version=p343.FW_VER_601,
            iso_auto_min_ss_requested="STD",
        )
        self.assertFalse(rej.admitted)
        self.assertEqual(rej.errno_code, p343.EOPNOTSUPP_ERRNO)
        self.assertFalse(rej.fx6_iso_auto_min_ss_supported)

        for sens, exp_iso in (("Low", 800), ("High", 12800)):
            ok = p343.simulate_auto_slow_shutter_iso_limit_min_ss_dual_base_hil(
                body_profile=p343.BODY_MODEL_FX6,
                fw_version=p343.FW_VER_601,
                fx6_base_sensitivity=sens,
                fx6_agc_enabled=True,
            )
            self.assertTrue(ok.admitted, sens)
            self.assertEqual(ok.effective_base_iso, exp_iso)
            self.assertEqual(ok.fx6_base_sensitivity, sens)
            self.assertTrue(ok.fx6_agc_enabled)

    def test_45_75b_cine_ei_base_iso_resets_to_800(self) -> None:
        r = p343.simulate_auto_slow_shutter_iso_limit_min_ss_dual_base_hil(
            shoot_mode=p343.SHOOT_MODE_MOVIE,
            log_shooting="Cine EI",
            base_iso_requested=12800,
            camera_settings_reset_applied=True,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.effective_base_iso, 800)

    def test_46_75b_auto_slow_shutter_none_request_under_lock_reports_disabled(self) -> None:
        r = p343.simulate_auto_slow_shutter_iso_limit_min_ss_dual_base_hil(
            shoot_mode=p343.SHOOT_MODE_MOVIE,
            shutter_mode="Angle",
        )
        self.assertTrue(r.admitted)
        self.assertTrue(r.auto_slow_shutter_locked)
        self.assertEqual(r.effective_auto_slow_shutter, "Disabled")

    def test_47_75b_iso_auto_min_ss_range_boundaries(self) -> None:
        for valid in ("1/2", "1/8000", '0.4"', '30"'):
            self.assertTrue(p343._is_valid_iso_auto_min_ss_value(valid), valid)
        for invalid in ("1/1", "1/16000", '0.1"', '60"', "TURBO"):
            self.assertFalse(p343._is_valid_iso_auto_min_ss_value(invalid), invalid)

    def test_48_75b_manual_iso_within_limit_admitted(self) -> None:
        r = p343.simulate_auto_slow_shutter_iso_limit_min_ss_dual_base_hil(
            shoot_mode=p343.SHOOT_MODE_MOVIE,
            iso_mode="Manual",
            manual_iso=1600,
            iso_range_limit_min=640,
            iso_range_limit_max=12800,
        )
        self.assertTrue(r.admitted)

    def test_49_75b_shutter_angle_exclusion_in_lock_reasons(self) -> None:
        r = p343.simulate_auto_slow_shutter_iso_limit_min_ss_dual_base_hil(
            shoot_mode=p343.SHOOT_MODE_MOVIE,
            shutter_mode="Angle",
        )
        self.assertIn("shutter_mode_angle_exclusion", r.auto_slow_shutter_lock_reasons)

    def test_50_75b_invalid_inputs_raise_stage75_error(self) -> None:
        for bad_kwargs in (
            dict(body_profile="FX30"),
            dict(fw_version="9.00"),
            dict(shoot_mode="Burst"),
            dict(exposure_mode="Scene"),
            dict(shutter_mode="Degrees"),
            dict(log_shooting="S-Log4"),
            dict(gamma_profile="Unknown"),
            dict(iso_mode="AutoDual"),
            dict(auto_slow_shutter_requested="Auto"),
            dict(iso_range_limit_min=0),
            dict(iso_range_limit_min=3200, iso_range_limit_max=800),
            dict(iso_auto_min_limit=3200, iso_auto_max_limit=800),
            dict(iso_auto_min_ss_requested="1/16000"),
            dict(base_iso_requested=3200),
            dict(fx6_base_sensitivity="Medium"),
        ):
            with self.assertRaises(p343.Stage75Phase343Error, msg=str(bad_kwargs)):
                p343.simulate_auto_slow_shutter_iso_limit_min_ss_dual_base_hil(**bad_kwargs)

    # ------------------------------------------------------------------
    # Sub-Model 75C: Still ARW, Dormant Lossless, HLG Still & Sort (51..64)
    # ------------------------------------------------------------------

    def test_51_75c_still_arw_exposes_strictly_compressed_and_uncompressed(self) -> None:
        self.assertEqual(
            p343.ACTIVE_RAW_FILE_TYPES, ("Compressed", "Uncompressed")
        )
        for raw_t in p343.ACTIVE_RAW_FILE_TYPES:
            r = p343.simulate_still_arw_rawcomp_heif_hlg_and_sort_slot1_hil(
                raw_file_type=raw_t,
            )
            self.assertTrue(r.admitted, raw_t)
            self.assertEqual(r.effective_raw_file_type, raw_t)
            self.assertTrue(r.lossless_raw_dormant_alcin_uud)
            self.assertTrue(r.raw_file_type_resettable)

    def test_52_75c_lossless_comp_l_m_s_100pct_dormant_on_alcin_uud(self) -> None:
        for dormant in p343.DORMANT_RAW_FILE_TYPES:
            rej = p343.simulate_still_arw_rawcomp_heif_hlg_and_sort_slot1_hil(
                raw_file_type=dormant,
            )
            self.assertFalse(rej.admitted, dormant)
            self.assertEqual(rej.errno_code, p343.EOPNOTSUPP_ERRNO)
            self.assertTrue(rej.lossless_raw_dormant_alcin_uud)
            self.assertEqual(rej.effective_raw_file_type, "Compressed")

    def test_53_75c_raw_file_type_reset_reverts_uncompressed_to_compressed(self) -> None:
        r = p343.simulate_still_arw_rawcomp_heif_hlg_and_sort_slot1_hil(
            raw_file_type="Uncompressed",
            camera_settings_reset_applied=True,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.effective_raw_file_type, "Compressed")

    def test_54_75c_hlg_still_image_still_hld_photo_typo_and_heif_prerequisites(self) -> None:
        for heif_mode in ("HEIF(4:2:0)", "HEIF(4:2:2)"):
            for exp in ("P", "A", "S", "M"):
                r = p343.simulate_still_arw_rawcomp_heif_hlg_and_sort_slot1_hil(
                    shoot_mode=p343.SHOOT_MODE_STILL,
                    exposure_mode=exp,
                    file_format="HEIF",
                    jpeg_heif_switch=heif_mode,
                    hlg_still_image="On",
                )
                self.assertTrue(r.admitted, f"{heif_mode}+{exp}")
                self.assertEqual(r.effective_hlg_still_image, "On")
                self.assertEqual(r.hlg_still_internal_elf_symbol, "STILL_HLD_PHOTO_ON")
                self.assertEqual(r.hlg_still_color_space, "BT.2100/BT.2020")
                self.assertEqual(r.hlg_still_iso_floor_range, (100, 125))
                self.assertTrue(r.pp_creative_look_dro_disabled)

    def test_55_75c_hlg_still_forced_off_on_jpeg_or_raw_or_raw_heif(self) -> None:
        for bad_kw in (
            dict(file_format="HEIF", jpeg_heif_switch="JPEG", hlg_still_image="On"),
            dict(file_format="RAW", jpeg_heif_switch="HEIF(4:2:0)", hlg_still_image="On"),
            dict(file_format="RAW & HEIF", jpeg_heif_switch="HEIF(4:2:2)", hlg_still_image="On"),
            dict(file_format="RAW & JPEG", jpeg_heif_switch="JPEG", hlg_still_image="On"),
            dict(
                shoot_mode=p343.SHOOT_MODE_MOVIE,
                file_format="HEIF",
                jpeg_heif_switch="HEIF(4:2:0)",
                hlg_still_image="On",
            ),
            dict(
                shoot_mode=p343.SHOOT_MODE_STILL,
                exposure_mode="Auto",
                file_format="HEIF",
                jpeg_heif_switch="HEIF(4:2:0)",
                hlg_still_image="On",
            ),
        ):
            rej = p343.simulate_still_arw_rawcomp_heif_hlg_and_sort_slot1_hil(**bad_kw)
            self.assertFalse(rej.admitted, str(bad_kw))
            self.assertEqual(rej.errno_code, p343.EOPNOTSUPP_ERRNO)
            self.assertEqual(rej.effective_hlg_still_image, "Off")
            self.assertEqual(rej.hlg_still_internal_elf_symbol, "STILL_HLD_PHOTO_OFF")

    def test_56_75c_hlg_still_and_jpeg_heif_switch_reset_behavior(self) -> None:
        r = p343.simulate_still_arw_rawcomp_heif_hlg_and_sort_slot1_hil(
            file_format="HEIF",
            jpeg_heif_switch="HEIF(4:2:2)",
            hlg_still_image="On",
            camera_settings_reset_applied=True,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.effective_jpeg_heif_switch, "JPEG")
        self.assertEqual(r.effective_hlg_still_image, "Off")
        self.assertEqual(r.hlg_still_internal_elf_symbol, "STILL_HLD_PHOTO_OFF")

    def test_57_75c_sort_recording_reset_immune_vs_initialize_wipe(self) -> None:
        r_rst = p343.simulate_still_arw_rawcomp_heif_hlg_and_sort_slot1_hil(
            sort_recording="On",
            camera_settings_reset_applied=True,
        )
        self.assertTrue(r_rst.admitted)
        self.assertFalse(r_rst.sort_recording_resettable)
        self.assertEqual(r_rst.effective_sort_recording, "On")

        r_init = p343.simulate_still_arw_rawcomp_heif_hlg_and_sort_slot1_hil(
            sort_recording="On",
            initialize_applied=True,
        )
        self.assertTrue(r_init.admitted)
        self.assertEqual(r_init.effective_sort_recording, "Off")

    def test_58_75c_sort_recording_autoswitch_spillover_to_slot1_blocked_erofs30(self) -> None:
        rej = p343.simulate_still_arw_rawcomp_heif_hlg_and_sort_slot1_hil(
            sort_recording="On",
            auto_switch_media="On",
            recording_slot="Slot 2",
            slot2_full_spillover_triggered=True,
        )
        self.assertFalse(rej.admitted)
        self.assertEqual(rej.errno_code, p343.EROFS_ERRNO)
        self.assertTrue(rej.slot1_erofs_triggered)
        self.assertEqual(rej.slot1_data_sector_writes, 0)

    def test_59_75c_direct_slot1_still_capture_blocked_erofs30(self) -> None:
        rej = p343.simulate_still_arw_rawcomp_heif_hlg_and_sort_slot1_hil(
            recording_slot="Slot 1",
            capture_triggered=True,
        )
        self.assertFalse(rej.admitted)
        self.assertEqual(rej.errno_code, p343.EROFS_ERRNO)
        self.assertTrue(rej.slot1_erofs_triggered)
        self.assertEqual(rej.slot1_data_sector_writes, 0)

    def test_60_75c_slot2_capture_without_spillover_admitted_zero_slot1_writes(self) -> None:
        r = p343.simulate_still_arw_rawcomp_heif_hlg_and_sort_slot1_hil(
            recording_slot="Slot 2",
            sort_recording="On",
            auto_switch_media="Off",
            capture_triggered=True,
        )
        self.assertTrue(r.admitted)
        self.assertFalse(r.slot1_erofs_triggered)
        self.assertEqual(r.slot1_data_sector_writes, 0)

    def test_61_75c_fx6_pure_cinema_rejects_still_mode_and_has_zero_arw_heif(self) -> None:
        rej = p343.simulate_still_arw_rawcomp_heif_hlg_and_sort_slot1_hil(
            body_profile=p343.BODY_MODEL_FX6,
            fw_version=p343.FW_VER_601,
            shoot_mode=p343.SHOOT_MODE_STILL,
        )
        self.assertFalse(rej.admitted)
        self.assertEqual(rej.errno_code, p343.EOPNOTSUPP_ERRNO)
        self.assertFalse(rej.fx6_has_still_arw_heif)

        ok_mv = p343.simulate_still_arw_rawcomp_heif_hlg_and_sort_slot1_hil(
            body_profile=p343.BODY_MODEL_FX6,
            fw_version=p343.FW_VER_601,
            shoot_mode=p343.SHOOT_MODE_MOVIE,
        )
        self.assertTrue(ok_mv.admitted)
        self.assertFalse(ok_mv.fx6_has_still_arw_heif)

    def test_62_75c_hlg_still_off_leaves_srgb_and_iso_80_100_floor(self) -> None:
        r = p343.simulate_still_arw_rawcomp_heif_hlg_and_sort_slot1_hil(
            file_format="HEIF",
            jpeg_heif_switch="HEIF(4:2:0)",
            hlg_still_image="Off",
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.hlg_still_color_space, "sRGB")
        self.assertEqual(r.hlg_still_iso_floor_range, (80, 100))
        self.assertFalse(r.pp_creative_look_dro_disabled)

    def test_63_75c_slot1_hazard_does_not_leak_writes_even_with_hlg_on(self) -> None:
        rej = p343.simulate_still_arw_rawcomp_heif_hlg_and_sort_slot1_hil(
            file_format="HEIF",
            jpeg_heif_switch="HEIF(4:2:2)",
            hlg_still_image="On",
            recording_slot="Slot 1",
            capture_triggered=True,
        )
        self.assertFalse(rej.admitted)
        self.assertEqual(rej.errno_code, p343.EROFS_ERRNO)
        self.assertEqual(rej.slot1_data_sector_writes, 0)

    def test_64_75c_invalid_inputs_raise_stage75_error(self) -> None:
        for bad_kwargs in (
            dict(body_profile="FX30"),
            dict(fw_version="9.00"),
            dict(shoot_mode=p343.SHOOT_MODE_SQ),
            dict(exposure_mode="Scene"),
            dict(file_format="TIFF"),
            dict(raw_file_type="Lossy"),
            dict(jpeg_heif_switch="AVIF"),
            dict(hlg_still_image="Auto"),
            dict(sort_recording="Auto"),
            dict(auto_switch_media="Auto"),
            dict(recording_slot="Slot 3"),
        ):
            with self.assertRaises(p343.Stage75Phase343Error, msg=str(bad_kwargs)):
                p343.simulate_still_arw_rawcomp_heif_hlg_and_sort_slot1_hil(**bad_kwargs)

    # ------------------------------------------------------------------
    # Sub-Model 75D: USB Mode, LUN=Single Slot-1 Hazard, PD & UVC (65..78)
    # ------------------------------------------------------------------

    def test_65_75d_usb_connection_mode_4_active_modes_reset_immune(self) -> None:
        self.assertEqual(len(p343.ACTIVE_USB_CONNECTION_MODES), 4)
        for mode in p343.ACTIVE_USB_CONNECTION_MODES:
            r = p343.simulate_usb_mode_lun_pd_and_uvc_dormancy_hil(
                usb_connection_mode=mode,
                host_os_msc_lockdown=True,
                camera_settings_reset_applied=True,
            )
            self.assertTrue(r.admitted, mode)
            self.assertFalse(r.usb_settings_resettable)
            self.assertEqual(r.effective_usb_connection_mode, mode)

    def test_66_75d_critical_usb_lun_single_exposes_only_slot1_not_slot2(self) -> None:
        r_single = p343.simulate_usb_mode_lun_pd_and_uvc_dormancy_hil(
            usb_connection_mode="MassStorage(MSC)",
            usb_lun_setting="Single",
            host_os_msc_lockdown=True,
            host_write_attempt_on_slot1=False,
        )
        self.assertTrue(r_single.admitted)
        self.assertTrue(r_single.single_lun_exposes_slot1_only)
        self.assertEqual(r_single.exposed_luns, ("Slot 1",))
        self.assertTrue(r_single.slot1_exposed_hazard_detected)

        r_multi = p343.simulate_usb_mode_lun_pd_and_uvc_dormancy_hil(
            usb_connection_mode="MassStorage(MSC)",
            usb_lun_setting="Multi",
            host_os_msc_lockdown=True,
        )
        self.assertTrue(r_multi.admitted)
        self.assertEqual(r_multi.exposed_luns, ("Slot 1", "Slot 2"))

    def test_67_75d_msc_single_and_mtp_slot1_host_pollution_blocked_erofs30(self) -> None:
        for mode, lun in (
            ("MassStorage(MSC)", "Single"),
            ("MassStorage(MSC)", "Multi"),
            ("MTP", "Single"),
        ):
            rej_unprotected = p343.simulate_usb_mode_lun_pd_and_uvc_dormancy_hil(
                usb_connection_mode=mode,
                usb_lun_setting=lun,
                host_os_msc_lockdown=False,
            )
            self.assertFalse(rej_unprotected.admitted, f"{mode}+{lun}")
            self.assertEqual(rej_unprotected.errno_code, p343.EROFS_ERRNO)
            self.assertTrue(rej_unprotected.slot1_erofs_triggered)
            self.assertEqual(rej_unprotected.slot1_data_sector_writes, 0)

            rej_write = p343.simulate_usb_mode_lun_pd_and_uvc_dormancy_hil(
                usb_connection_mode=mode,
                usb_lun_setting=lun,
                host_os_msc_lockdown=True,
                host_write_attempt_on_slot1=True,
            )
            self.assertFalse(rej_write.admitted, f"{mode}+{lun}+wr")
            self.assertEqual(rej_write.errno_code, p343.EROFS_ERRNO)
            self.assertEqual(rej_write.slot1_data_sector_writes, 0)

    def test_68_75d_usb_settings_reset_immune_vs_initialize_defaults(self) -> None:
        r_rst = p343.simulate_usb_mode_lun_pd_and_uvc_dormancy_hil(
            usb_connection_mode="Remote Shooting",
            usb_lun_setting="Single",
            usb_power_supply="Off",
            camera_settings_reset_applied=True,
        )
        self.assertTrue(r_rst.admitted)
        self.assertEqual(r_rst.effective_usb_connection_mode, "Remote Shooting")
        self.assertEqual(r_rst.effective_usb_lun_setting, "Single")
        self.assertEqual(r_rst.effective_usb_power_supply, "Off")

        r_init = p343.simulate_usb_mode_lun_pd_and_uvc_dormancy_hil(
            usb_connection_mode="Remote Shooting",
            usb_lun_setting="Single",
            usb_power_supply="Off",
            initialize_applied=True,
        )
        self.assertTrue(r_init.admitted)
        self.assertEqual(r_init.effective_usb_connection_mode, "Sel. When Connect")
        self.assertEqual(r_init.effective_usb_lun_setting, "Multi")
        self.assertEqual(r_init.effective_usb_power_supply, "On")

    def test_69_75d_np_fz100_pd_gate_and_live_battery_pull_brownout(self) -> None:
        rej_no_bat = p343.simulate_usb_mode_lun_pd_and_uvc_dormancy_hil(
            np_fz100_inserted=False,
            usb_pd_voltage_v=9.0,
            usb_pd_current_a=3.0,
        )
        self.assertFalse(rej_no_bat.admitted)
        self.assertEqual(rej_no_bat.errno_code, p343.EPERM_ERRNO)
        self.assertTrue(rej_no_bat.power_cut_brownout)
        self.assertFalse(rej_no_bat.np_fz100_pd_gate_satisfied)

        rej_pull = p343.simulate_usb_mode_lun_pd_and_uvc_dormancy_hil(
            np_fz100_inserted=True,
            np_fz100_pulled_live=True,
        )
        self.assertFalse(rej_pull.admitted)
        self.assertEqual(rej_pull.errno_code, p343.EPERM_ERRNO)
        self.assertTrue(rej_pull.power_cut_brownout)

    def test_70_75d_dcc1_coupler_65w_5a_emarker_allows_batteryless_operation(self) -> None:
        ok = p343.simulate_usb_mode_lun_pd_and_uvc_dormancy_hil(
            np_fz100_inserted=False,
            dc_c1_coupler_attached=True,
            dc_c1_pd_watts=65,
            dc_c1_cable_amps=5,
        )
        self.assertTrue(ok.admitted)
        self.assertFalse(ok.power_cut_brownout)
        self.assertTrue(ok.np_fz100_pd_gate_satisfied)

        # Under-rated cable (3A) or adapter (<65W) fails gate
        for w, a in ((45, 5), (65, 3)):
            rej = p343.simulate_usb_mode_lun_pd_and_uvc_dormancy_hil(
                np_fz100_inserted=False,
                dc_c1_coupler_attached=True,
                dc_c1_pd_watts=w,
                dc_c1_cable_amps=a,
            )
            self.assertFalse(rej.admitted, f"{w}W/{a}A")
            self.assertTrue(rej.power_cut_brownout)

    def test_71_75d_fx6_19_5v_dcin_batteryless_boot_and_voltage_envelope(self) -> None:
        ok = p343.simulate_usb_mode_lun_pd_and_uvc_dormancy_hil(
            body_profile=p343.BODY_MODEL_FX6,
            fw_version=p343.FW_VER_601,
            np_fz100_inserted=False,
            fx6_dc_in_voltage_v=19.5,
        )
        self.assertTrue(ok.admitted)
        self.assertTrue(ok.fx6_batteryless_dcin_active)
        self.assertFalse(ok.power_cut_brownout)

        for bad_v in (16.5, 15.5, 22.0):
            rej = p343.simulate_usb_mode_lun_pd_and_uvc_dormancy_hil(
                body_profile=p343.BODY_MODEL_FX6,
                fw_version=p343.FW_VER_601,
                fx6_dc_in_voltage_v=bad_v,
            )
            self.assertFalse(rej.admitted, str(bad_v))
            self.assertEqual(rej.errno_code, p343.EPERM_ERRNO)
            self.assertTrue(rej.power_cut_brownout)

    def test_72_75d_dual_fx3_and_fx6_native_uvc_100pct_dormancy(self) -> None:
        for body, fw in (
            (p343.BODY_MODEL_FX3, p343.FW_VER_702),
            (p343.BODY_MODEL_FX6, p343.FW_VER_601),
        ):
            rej = p343.simulate_usb_mode_lun_pd_and_uvc_dormancy_hil(
                body_profile=body,
                fw_version=fw,
                usb_connection_mode="USB Streaming (UVC)",
            )
            self.assertFalse(rej.admitted, body)
            self.assertEqual(rej.errno_code, p343.EOPNOTSUPP_ERRNO)
            self.assertFalse(rej.native_uvc_exposed)
            self.assertTrue(rej.uvc_kmods_dormant_at_boot)

    def test_73_75d_movie_rec_during_streaming_and_hdmi_rec_slot1_erofs30(self) -> None:
        rej_stream = p343.simulate_usb_mode_lun_pd_and_uvc_dormancy_hil(
            network_streaming_enabled=True,
            movie_rec_during_streaming="Enable",
            recording_slot="Slot 1",
        )
        self.assertFalse(rej_stream.admitted)
        self.assertEqual(rej_stream.errno_code, p343.EROFS_ERRNO)
        self.assertTrue(rej_stream.slot1_erofs_triggered)
        self.assertEqual(rej_stream.slot1_data_sector_writes, 0)

        rej_hdmi = p343.simulate_usb_mode_lun_pd_and_uvc_dormancy_hil(
            hdmi_rec_media_dur_hdmi="On",
            recording_slot="Slot 1",
        )
        self.assertFalse(rej_hdmi.admitted)
        self.assertEqual(rej_hdmi.errno_code, p343.EROFS_ERRNO)
        self.assertEqual(rej_hdmi.slot1_data_sector_writes, 0)

    def test_74_75d_movie_rec_during_streaming_slot2_admitted_and_resettable(self) -> None:
        ok = p343.simulate_usb_mode_lun_pd_and_uvc_dormancy_hil(
            network_streaming_enabled=True,
            movie_rec_during_streaming="Enable",
            hdmi_rec_media_dur_hdmi="On",
            recording_slot="Slot 2",
        )
        self.assertTrue(ok.admitted)
        self.assertTrue(ok.network_streaming_enabled)
        self.assertEqual(ok.effective_movie_rec_during_streaming, "Enable")
        self.assertEqual(ok.effective_hdmi_rec_media_dur_hdmi, "On")

        rst = p343.simulate_usb_mode_lun_pd_and_uvc_dormancy_hil(
            network_streaming_enabled=True,
            movie_rec_during_streaming="Enable",
            hdmi_rec_media_dur_hdmi="On",
            recording_slot="Slot 2",
            camera_settings_reset_applied=True,
        )
        self.assertTrue(rst.admitted)
        self.assertEqual(rst.effective_movie_rec_during_streaming, "Disable")
        self.assertEqual(rst.effective_hdmi_rec_media_dur_hdmi, "Off(HDMI Only)")

    def test_75_75d_remote_shooting_hides_msc_luns(self) -> None:
        r = p343.simulate_usb_mode_lun_pd_and_uvc_dormancy_hil(
            usb_connection_mode="Remote Shooting",
            usb_lun_setting="Single",
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.exposed_luns, ())
        self.assertFalse(r.slot1_exposed_hazard_detected)

    def test_76_75d_pd_voltage_current_insufficient_with_battery_still_runs_on_battery(self) -> None:
        r = p343.simulate_usb_mode_lun_pd_and_uvc_dormancy_hil(
            np_fz100_inserted=True,
            usb_power_supply="On",
            usb_pd_voltage_v=5.0,
            usb_pd_current_a=1.5,
        )
        self.assertTrue(r.admitted)
        self.assertFalse(r.np_fz100_pd_gate_satisfied)

    def test_77_75d_mtp_with_lockdown_and_no_write_attempt_admitted(self) -> None:
        r = p343.simulate_usb_mode_lun_pd_and_uvc_dormancy_hil(
            usb_connection_mode="MTP",
            host_os_msc_lockdown=True,
            host_write_attempt_on_slot1=False,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.exposed_luns, ("Slot 1",))

    def test_78_75d_invalid_inputs_raise_stage75_error(self) -> None:
        for bad_kwargs in (
            dict(body_profile="FX30"),
            dict(fw_version="9.00"),
            dict(usb_connection_mode="PTP"),
            dict(usb_lun_setting="Triple"),
            dict(usb_power_supply="Auto"),
            dict(movie_rec_during_streaming="Force"),
            dict(hdmi_rec_media_dur_hdmi="Auto"),
            dict(recording_slot="Slot 3"),
        ):
            with self.assertRaises(p343.Stage75Phase343Error, msg=str(bad_kwargs)):
                p343.simulate_usb_mode_lun_pd_and_uvc_dormancy_hil(**bad_kwargs)

    # ------------------------------------------------------------------
    # Milestone, Determinism, CLI & Suite Stage 75 Wiring (Tests 79..96)
    # ------------------------------------------------------------------

    def test_79_milestone_probe_exact_fields(self) -> None:
        probe = p343._build_stage75_milestone_probe()
        self.assertEqual(probe["phase_number"], 343)
        self.assertEqual(probe["stage_index"], 75)
        self.assertEqual(probe["stage_total"], 75)
        self.assertEqual(probe["milestone"], "75/75")
        self.assertTrue(probe["is_75th_stage_milestone"])
        self.assertEqual(probe["wave"], "Wave-65")
        self.assertEqual(probe["fx3_target_version"], "Ver. 7.02")
        self.assertEqual(probe["fx6_comparison_version"], "Ver. 6.01")

    def test_80_pillar_results_all_passed_in_clean_room(self) -> None:
        rep = p343.run_phase343_zoom_ciz_autoslow_iso_arw_rawcomp_usblun_uvc_coemulation(
            force_clean_room=True
        )
        for pillar_key in (
            "pillar_a_zoom_range_speeds_ring_rotate_hil",
            "pillar_b_auto_slow_shutter_iso_limit_min_ss_dual_base_hil",
            "pillar_c_still_arw_rawcomp_heif_hlg_sort_slot1_hil",
            "pillar_d_usb_mode_lun_pd_and_uvc_dormancy_hil",
        ):
            self.assertTrue(rep[pillar_key]["passed"], pillar_key)

    def test_81_deterministic_digest_identical_across_repeated_clean_room_runs(self) -> None:
        rep1 = p343.run_phase343_zoom_ciz_autoslow_iso_arw_rawcomp_usblun_uvc_coemulation(
            force_clean_room=True
        )
        rep2 = p343.run_phase343_zoom_ciz_autoslow_iso_arw_rawcomp_usblun_uvc_coemulation(
            force_clean_room=True
        )
        self.assertEqual(rep1["audit_digest_sha256"], rep2["audit_digest_sha256"])

    def test_82_deterministic_suite_digest_identical_across_repeated_fast_runs(self) -> None:
        cfg = suite.CoEmulationConfig(**_fast_suite_kwargs())
        r1 = suite.run_fx3_vm_coemulation_suite(cfg)
        r2 = suite.run_fx3_vm_coemulation_suite(cfg)
        self.assertEqual(r1["audit_digest_sha256"], r2["audit_digest_sha256"])

    def test_83_stage75_wrapper_output_schema_matches_suite_contract(self) -> None:
        s75 = suite.run_stage75_realhw_zoom_ciz_autoslow_iso_arw_rawcomp_usblun_uvc_hil(
            suite.CoEmulationConfig(force_clean_room=True)
        )
        self.assertEqual(
            s75["stage"],
            "stage75_realhw_zoom_ciz_autoslow_iso_arw_rawcomp_usblun_uvc_hil",
        )
        self.assertEqual(s75["schema"], p343.SCHEMA_ID)
        self.assertEqual(s75["phase_number"], 343)
        self.assertEqual(s75["milestone"], "75/75")
        self.assertTrue(s75["is_75th_stage_milestone"])
        self.assertTrue(s75["all_checks_passed"])
        self.assertEqual(len(s75["phase343_audit_digest_sha256"]), 64)

    def test_84_standalone_cli_help_uses_sys_executable_and_percent_escaping(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                str(
                    FX3_VM_DIR
                    / "realhw_zoom_ciz_autoslow_iso_arw_rawcomp_usblun_uvc_coemulator.py"
                ),
                "--help",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("100%", proc.stdout)
        self.assertIn("75/75", proc.stdout)

    def test_85_suite_cli_help_percent_escaping_and_stage75_flags(self) -> None:
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
        self.assertIn("75/75 Milestone", proc.stdout)
        self.assertIn("--include-stage75", proc.stdout)
        self.assertIn("--skip-stage75", proc.stdout)
        self.assertIn("--no-include-stage75", proc.stdout)
        self.assertIn("--skip-phase343", proc.stdout)

    def test_86_standalone_cli_summary_and_json_modes(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = p343.main(["--self-test", "--clean-room", "--summary"])
        self.assertEqual(rc, 0)
        self.assertIn("[PASS] Phase 343 Stage 75 (75/75 Milestone)", buf.getvalue())

        buf_json = io.StringIO()
        with contextlib.redirect_stdout(buf_json):
            rc2 = p343.main(["--self-test", "--clean-room", "--json"])
        self.assertEqual(rc2, 0)
        parsed = json.loads(buf_json.getvalue())
        self.assertEqual(parsed["milestone"], "75/75")
        self.assertTrue(parsed["is_75th_stage_milestone"])
        self.assertTrue(parsed["all_checks_passed"])
        self.assertNotIn("\\x7fELF", buf_json.getvalue())

    def test_87_no_hardcoded_usr_bin_python3_in_stage75_files(self) -> None:
        mod_src = (
            FX3_VM_DIR
            / "realhw_zoom_ciz_autoslow_iso_arw_rawcomp_usblun_uvc_coemulator.py"
        ).read_text(encoding="utf-8")
        tst_src = Path(__file__).read_text(encoding="utf-8")
        forbidden = "/usr/bin/" + "python3"
        self.assertNotIn(forbidden, mod_src)
        self.assertNotIn(forbidden, tst_src)

    def test_88_suite_default_config_enables_stage75_and_full_run_contains_75_stages(self) -> None:
        cfg = suite.CoEmulationConfig()
        self.assertTrue(
            cfg.include_phase343_realhw_zoom_ciz_autoslow_iso_arw_rawcomp_usblun_uvc_hil
        )
        self.assertTrue(cfg.include_stage75)
        self.assertTrue(
            cfg.stage75_realhw_zoom_ciz_autoslow_iso_arw_rawcomp_usblun_uvc_hil
        )

        t0 = time.monotonic()
        rep = suite.run_fx3_vm_coemulation_suite(cfg)
        elapsed = time.monotonic() - t0
        self.assertTrue(rep["all_checks_passed"])
        stage_keys = [k for k in rep if re.match(r"^stage\d+_", k)]
        self.assertGreaterEqual(len(stage_keys), 75)
        s75 = rep["stage75_realhw_zoom_ciz_autoslow_iso_arw_rawcomp_usblun_uvc_hil"]
        self.assertTrue(s75["all_checks_passed"])
        self.assertTrue(s75["is_75th_stage_milestone"])
        self.assertEqual(s75["milestone"], "75/75")
        self.assertEqual(s75["phase_number"], 343)
        max_elapsed = 30.0 if IS_CI else 15.0
        self.assertLess(elapsed, max_elapsed)

    def test_89_suite_skip_flags_and_summary_cli_for_stage75(self) -> None:
        for flag in ("--skip-stage75", "--no-include-stage75", "--skip-phase343"):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = suite.main([*_FAST_CLI_FLAGS, flag, "--json"])
            self.assertEqual(rc, 0)
            data = json.loads(buf.getvalue())
            self.assertNotIn(
                "stage75_realhw_zoom_ciz_autoslow_iso_arw_rawcomp_usblun_uvc_hil",
                data,
            )
            self.assertFalse(data["config"]["include_stage75"])

        buf_sum = io.StringIO()
        with contextlib.redirect_stdout(buf_sum):
            rc_sum = suite.main([*_FAST_CLI_FLAGS, "--include-stage75", "--summary"])
        self.assertEqual(rc_sum, 0)
        self.assertIn(
            "realhw_zoom_ciz_autoslow_iso_arw_rawcomp_usblun_uvc_hil=CLEAN_ROOM_SYNTHETIC("
            "m75=75/75,ciz=1.5/2.0x,ass_lck=7,dcg=20x,raw_opt=2,usb_m=4,uvc=0/0,"
            "s1_wr=0,emmc_wr=0)",
            buf_sum.getvalue(),
        )

    def test_90_suite_tamper_75a_zoom_redlines_detected(self) -> None:
        for attr, val in (
            ("ZOOM_LEVER_1ST_DEFAULT_SPEED", 5),
            ("ZOOM_LEVER_2ND_DEFAULT_SPEED", 3),
            ("ZOOM_CUSTOM_KEY_DEFAULT_SPEED", 8),
            ("ZOOM_REMOTE_DEFAULT_SPEED", 8),
            ("ZOOM_SPEED_MAX_STEPS", 10),
            ("CIZ_4K_MAX_MAGNIFICATION", 2.0),
            ("CIZ_HD_MAX_MAGNIFICATION", 4.0),
            ("DIGITAL_ZOOM_MOVIE_MAX_MAGNIFICATION", 8.0),
            ("ZOOM_RANGE_RESET_IMMUNITY_DRIFT_EVENTS", 1),
            ("ZOOM_RING_ROTATE_RESET_IMMUNITY_DRIFT_EVENTS", 1),
            ("NON_OPTICAL_ZOOM_AF_TRACKING_BYPASS_EVENTS", 1),
            ("FX6_DIGITAL_ZOOM_LEAK_EVENTS", 1),
        ):
            with unittest.mock.patch.object(p343, attr, val):
                rep = suite.run_fx3_vm_coemulation_suite(
                    suite.CoEmulationConfig(**_fast_suite_kwargs())
                )
                self.assertFalse(rep["all_checks_passed"], attr)

    def test_91_suite_tamper_75b_autoslow_iso_redlines_detected(self) -> None:
        for attr, val in (
            ("AUTO_SLOW_SHUTTER_LOCKOUT_CONDITIONS_COUNT", 5),
            ("AUTO_SLOW_SHUTTER_6LOCK_BYPASS_EVENTS", 1),
            ("ISO_RANGE_LIMIT_RESET_IMMUNITY_DRIFT_EVENTS", 1),
            ("ISO_RANGE_LIMIT_LEAKED_TO_AUTO_EVENTS", 1),
            ("ISO_AUTO_MIN_SS_MOVIE_OR_SQ_BYPASS_EVENTS", 1),
            ("DUAL_CONVERSION_GAIN_RATIO", 16),
            ("FX6_ISO_AUTO_MIN_SS_EXPOSED_EVENTS", 1),
        ):
            with unittest.mock.patch.object(p343, attr, val):
                rep = suite.run_fx3_vm_coemulation_suite(
                    suite.CoEmulationConfig(**_fast_suite_kwargs())
                )
                self.assertFalse(rep["all_checks_passed"], attr)

    def test_92_suite_tamper_75c_arw_hlg_sort_redlines_detected(self) -> None:
        for attr, val in (
            ("RAW_FILE_TYPE_ACTIVE_OPTIONS_COUNT", 3),
            ("DORMANT_LOSSLESS_RAW_EXPOSED_EVENTS", 1),
            ("HLG_STILL_PREREQUISITE_BYPASS_EVENTS", 1),
            ("STILL_HLG_PHOTO_TYPO_MATCHED", False),
            ("SORT_RECORDING_SLOT1_EROFS_BYPASS_EVENTS", 1),
            ("FX6_STILL_ARW_OR_HEIF_EXPOSED_EVENTS", 1),
        ):
            with unittest.mock.patch.object(p343, attr, val):
                rep = suite.run_fx3_vm_coemulation_suite(
                    suite.CoEmulationConfig(**_fast_suite_kwargs())
                )
                self.assertFalse(rep["all_checks_passed"], attr)

    def test_93_suite_tamper_75d_usb_lun_pd_uvc_and_tier0_redlines_detected(self) -> None:
        for attr, val in (
            ("USB_CONNECTION_ACTIVE_MODES_COUNT", 5),
            ("USB_LUN_SINGLE_EXPOSES_SLOT1_ONLY", False),
            ("USB_LUN_SLOT1_HOST_POLLUTION_EVENTS", 1),
            ("USB_PD_BATTERYLESS_POWER_BYPASS_EVENTS", 1),
            ("FX3_NATIVE_UVC_EXPOSED_EVENTS", 1),
            ("FX6_NATIVE_UVC_EXPOSED_EVENTS", 1),
            ("STREAMING_MOVIE_REC_SLOT1_EROFS_BYPASS_EVENTS", 1),
            ("PHYSICAL_DEVICE_WRITES", 1),
            ("EMMC_NFLASHA_WRITE_COUNT", 1),
            ("SLOT1_DATA_SECTOR_WRITES", 1),
            ("SLOT1_AVF_INFO_MUTATED", True),
            ("RAW_FIRMWARE_BYTES_LEAKED", 4),
            ("CP_MUTATION_BYTES", 4),
            ("WBI_MUTATION_BYTES", 4),
            ("CNFLASHA_USERSPACE_WRITE_BLOCKED", False),
        ):
            with unittest.mock.patch.object(p343, attr, val):
                rep = suite.run_fx3_vm_coemulation_suite(
                    suite.CoEmulationConfig(**_fast_suite_kwargs())
                )
                self.assertFalse(rep["all_checks_passed"], attr)

    def test_94_stage75_all_zero_and_boolean_redlines_verified(self) -> None:
        rep = p343.run_phase343_zoom_ciz_autoslow_iso_arw_rawcomp_usblun_uvc_coemulation(
            force_clean_room=True
        )
        red = rep["redlines"]
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
            "slot1_data_sector_writes",
            "rf_packets_transmitted",
            "rf_nvs_mutation_bytes",
            "zoom_range_reset_immunity_drift_events",
            "zoom_ring_rotate_reset_immunity_drift_events",
            "non_optical_zoom_af_tracking_bypass_events",
            "fx6_digital_zoom_leak_events",
            "auto_slow_shutter_6lock_bypass_events",
            "iso_range_limit_reset_immunity_drift_events",
            "iso_range_limit_leaked_to_auto_events",
            "iso_auto_min_ss_movie_or_sq_bypass_events",
            "fx6_iso_auto_min_ss_exposed_events",
            "dormant_lossless_raw_exposed_events",
            "hlg_still_prerequisite_bypass_events",
            "sort_recording_slot1_erofs_bypass_events",
            "fx6_still_arw_or_heif_exposed_events",
            "usb_lun_slot1_host_pollution_events",
            "usb_pd_batteryless_power_bypass_events",
            "fx3_native_uvc_exposed_events",
            "fx6_native_uvc_exposed_events",
            "streaming_movie_rec_slot1_erofs_bypass_events",
            "rsv_orphan_count",
            "wf12_00342260_hits",
            "appfw_crashes",
            "null_gpio_derefs",
            "mailbox_stalls",
            "stock_cp_fault_count",
            "raw_firmware_bytes_leaked",
        ):
            self.assertEqual(red[zero_key], 0, zero_key)
        for true_key in (
            "p8_cp_mutation_forbidden",
            "cnflasha_userspace_write_blocked",
            "still_hlg_photo_typo_matched",
            "usb_lun_single_exposes_slot1_only",
        ):
            self.assertTrue(red[true_key], true_key)
        for false_key in (
            "persistent_emmc_writes_authorized",
            "emmc_writes_authorized",
            "cross_model_flash_authorized",
            "hardware_live_attachment_authorized",
            "overall_ready_for_hardware_attach",
            "isp_write_authorized",
            "spi_nor_write_authorized",
            "el3_payload_transmit_authorized",
            "slot1_avf_info_mutated",
        ):
            self.assertFalse(red[false_key], false_key)

    def test_95_suite_tamper_milestone_flag_detected(self) -> None:
        with unittest.mock.patch.object(p343, "IS_75TH_STAGE_MILESTONE", False):
            rep = suite.run_fx3_vm_coemulation_suite(
                suite.CoEmulationConfig(**_fast_suite_kwargs())
            )
            self.assertFalse(rep["all_checks_passed"])

    def test_96_all_four_env_modes_pass_cleanly_including_work_root_none(self) -> None:
        clean_rep = p343.run_phase343_zoom_ciz_autoslow_iso_arw_rawcomp_usblun_uvc_coemulation(
            force_clean_room=True
        )
        env_rep = p343.run_phase343_zoom_ciz_autoslow_iso_arw_rawcomp_usblun_uvc_coemulation(
            env={p343.ENV_FORCE_CLEAN_ROOM: "1"}
        )
        self.assertEqual(
            clean_rep["audit_digest_sha256"],
            env_rep["audit_digest_sha256"],
        )

        with unittest.mock.patch.object(p343, "resolve_mac_work_root", return_value=None):
            none_rep = p343.run_phase343_zoom_ciz_autoslow_iso_arw_rawcomp_usblun_uvc_coemulation(
                env={}
            )
        self.assertTrue(none_rep["all_checks_passed"])
        self.assertEqual(none_rep["source_mode"], p343.SOURCE_MODE_CLEAN_ROOM)
        self.assertEqual(none_rep["redlines"]["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(none_rep["audit_digest_sha256"], clean_rep["audit_digest_sha256"])

        cr_test_rep = p343.run_phase343_zoom_ciz_autoslow_iso_arw_rawcomp_usblun_uvc_coemulation(
            env={p343.ENV_CLEAN_ROOM_TEST: "1"}
        )
        self.assertTrue(cr_test_rep["all_checks_passed"])
        self.assertEqual(cr_test_rep["audit_digest_sha256"], clean_rep["audit_digest_sha256"])


if __name__ == "__main__":
    unittest.main()
