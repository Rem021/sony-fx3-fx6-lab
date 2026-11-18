#!/usr/bin/env python3
"""Unit tests for Phase 335 (Stage 72 — 72/72 VM HIL Stages Milestone!):
Real-Hardware `ILME-FX3 Ver. 7.02` vs `ILME-FX6 Ver. 6.01` Wave-62:
- 72A: `[Audio Recording]` (5 active items, resettable `On[def]/Off` disabled in S&Q,
  32-step `[Audio Rec Level]` `0..31` def `26` + Delete-key reset + always-on Limiter,
  `[Shoe Audio Set.]` `48kHz/24bit 4ch` / `24bit 2ch` / `16bit 2ch[def]`, internal-mic-only
  `[Wind Noise Reduct.]`, `[Audio Out Timing]` `Live[def]/Lip Sync` under
  `Shooting -> Audio Recording`, removed standalone `Audio Level Display`, `Setup ->
  Sound Option -> [4ch Audio Monitoring]` 5 pairs + HDMI `[4ch Audio Output]`, `3.5mm`
  plug MI-shoe override, `HANDLE AUDIO=OFF` fallback, `ANALOG` 16-bit 2ch lock,
  Proxy `MPEG-4 AAC-LC 2ch 128 kbps` & `>=100p` cutoff vs FX6 native 4ch 24-bit LPCM +
  `CH1..CH4` pots + 6-step `Limiter Mode` + dormant `32bit float`),
- 72B: `[Face/Eye AF]` (Wave-42 Errata: `ILME-FX3 Ver. 7.02` `[Face/Eye Subject]`
  exposes ONLY `Human[def]` & `Animal`, dormant `Bird`/`Animal/Bird`/`Insect`/
  `Car/Train`/`Airplane` `EOPNOTSUPP=95` & `0` `BKID_APP_*` airplane hits, Still-only
  `Animal` + `TYPE_ANIMAL_EYE_AF_IN_MOVIE_NOT_SUPPORT`, resettable `[Right/Left Eye Select]`
  & `[Face/Eye Frame Disp.]` `Off[def]` Clean-HDMI 0-leak, `[Regist. Faces Priority]`
  grayed on `Animal`, Initialize-only 8-slot `[Face Memory]` excluded from `CAMSET*.DAT`
  vs FX6 `Human`-only + session `Saved Tracking Face`),
- 72C: `[Silent Mode Settings]` (`[Silent Mode]` `Off[def]/On` Electronic Shutter +
  `Audio signals = Off` + 5 hard lockouts while `AF Illuminator` stays active,
  2-item `[Target Function Settings]` `[Aperture Drive in AF]` & `[Auto Pixel Mapping]`
  rejecting extra items, `Auto Pixel Mapping=Off` blocking power-off mechanical shutter
  & `cnflasha` bad-pixel write, dormant `[Shutter When Pwr OFF]` `_f 0x709f`
  `EOPNOTSUPP=95` vs FX6 shutterless), and
- 72D: `[Version]` & `BODYDATA.DAT` Firewall (`Body Ver. 7.02` / `Lens` / `Mount Adaptor`,
  Ver. 6.00+ update dot silenced under `Airplane Mode = On`, `Slot 1` root vs `Slot 2`,
  `NP-FZ100 >= 51%` 3 bars, mandatory `Ver. 2.04/2.05` stepping-stone before `Ver. 7.02`
  with 5-long/6-short LED fault code, cross-model rejection, FX6 `Slot B` + mandatory
  `AC Adaptor`, and 100% NO-GO / BLOCKED `EROFS=30` / `EPERM=1` firewall) HIL
(96 four-mode tests).
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
import realhw_shoe_audio_4ch_subject_recog_silent_target_version_coemulator as p335  # noqa: E402

IS_CI = os.environ.get("GITHUB_ACTIONS", "").lower() == "true"


def _fast_suite_kwargs(**overrides: object) -> dict:
    """Fast config skipping unrelated optional stages 4..71 for quick Stage 72 isolation tests."""
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
]


class TestRealHwStage72ShoeAudioSubjectRecogSilentTargetVersion(unittest.TestCase):
    # ------------------------------------------------------------------
    # Donor Audit, Bounded O_RDONLY & Dual-Mode Tests (Tests 1..14)
    # ------------------------------------------------------------------

    def test_01_milestone_constants_72_of_72(self) -> None:
        self.assertEqual(p335.PHASE_NUMBER, 335)
        self.assertEqual(p335.STAGE_INDEX, 72)
        self.assertEqual(p335.STAGE_TOTAL, 72)
        self.assertEqual(p335.MILESTONE_LABEL, "72/72")
        self.assertTrue(p335.IS_72ND_STAGE_MILESTONE)
        self.assertEqual(
            p335.STAGE_NAME,
            "stage72_realhw_shoe_audio_4ch_subject_recog_silent_target_version_hil",
        )
        self.assertEqual(len(p335.DONOR_RELPATHS), 21)
        self.assertEqual(len(p335.EXPECTED_DONOR_BYTES), 21)
        self.assertEqual(len(p335.EXPECTED_COMPACT_DONOR_SHA256), 18)
        self.assertEqual(len(p335.EXPECTED_LARGE_HEAD4K_SHA256), 3)

    def test_02_hard_safety_redlines_locked(self) -> None:
        self.assertTrue(p335.P8_CP_MUTATION_FORBIDDEN)
        self.assertTrue(p335.CNFLASHA_USERSPACE_WRITE_BLOCKED)
        self.assertTrue(p335.BODYDATA_FLASH_EXECUTION_BLOCKED)
        self.assertFalse(p335.PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(p335.EMMC_WRITES_AUTHORIZED)
        self.assertFalse(p335.CROSS_MODEL_FLASH_AUTHORIZED)
        self.assertFalse(p335.HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        self.assertFalse(p335.OVERALL_READY_FOR_HARDWARE_ATTACH)
        self.assertFalse(p335.ISP_WRITE_AUTHORIZED)
        self.assertFalse(p335.SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(p335.EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        self.assertFalse(p335.SLOT1_AVF_INFO_MUTATED)
        self.assertFalse(p335.FX3_HAS_SHUTTER_WHEN_PWR_OFF)
        self.assertFalse(p335.FX6_HAS_MECHANICAL_SHUTTER)
        self.assertEqual(p335.FX3_ACTIVE_AUDIO_RECORDING_MENU_ITEMS, 5)
        self.assertEqual(p335.AUDIO_REC_LEVEL_STEPS, 32)
        self.assertEqual(p335.FOUR_CH_MONITORING_PAIRS_COUNT, 5)
        self.assertEqual(p335.FX3_EXPOSED_FACE_EYE_SUBJECTS_COUNT, 2)
        self.assertEqual(p335.FX3_FACE_MEMORY_MAX_SLOTS, 8)
        self.assertEqual(p335.FX3_SILENT_MODE_HARD_LOCKED_FEATURES_COUNT, 5)
        self.assertEqual(p335.FX3_TARGET_FUNCTION_SETTINGS_ITEM_COUNT, 2)
        self.assertEqual(p335.BODYDATA_MIN_BATTERY_PCT, 51)
        self.assertEqual(p335.SLOT1_DATA_SECTOR_WRITES, 0)
        self.assertEqual(p335.EMMC_NFLASHA_WRITE_COUNT, 0)
        self.assertEqual(p335.RAW_FIRMWARE_BYTES_LEAKED, 0)

    def test_03_clean_room_test_mode_both_env_vars(self) -> None:
        self.assertFalse(p335.clean_room_test_mode(env={}))
        self.assertTrue(p335.clean_room_test_mode(env={p335.ENV_FORCE_CLEAN_ROOM: "1"}))
        self.assertTrue(p335.clean_room_test_mode(env={p335.ENV_CLEAN_ROOM_TEST: "1"}))
        self.assertTrue(p335.clean_room_test_mode(force_clean_room=True, env={}))
        self.assertFalse(
            p335.clean_room_test_mode(
                force_clean_room=False,
                env={p335.ENV_FORCE_CLEAN_ROOM: "1", p335.ENV_CLEAN_ROOM_TEST: "1"},
            )
        )

    def test_04_resolve_mac_work_root_and_donor_paths_none_fallback(self) -> None:
        self.assertIsNone(p335.resolve_phase335_donor_paths(None))
        self.assertIsNone(
            p335.resolve_mac_work_root(
                env={p335.ENV_MAC_WORK_ROOT: p335.CLEAN_ROOM_SENTINEL_DIRNAME}
            )
        )
        self.assertIsNone(
            p335.resolve_mac_work_root(
                env={p335.ENV_MAC_ROOT: p335.CLEAN_ROOM_SENTINEL_DIRNAME}
            )
        )
        with tempfile.TemporaryDirectory() as td:
            with unittest.mock.patch.object(p335, "DEFAULT_REPO_ROOT", Path(td)):
                with unittest.mock.patch.object(p335, "LEGACY_MAC_ROOT", Path(td) / "none"):
                    self.assertIsNone(p335.resolve_mac_work_root(env={}))
                    self.assertIsNone(p335.resolve_phase335_donor_paths(None, env={}))
                    rep = p335.run_phase335_shoe_audio_4ch_subject_recog_silent_target_version_coemulation(
                        env={}
                    )
                    self.assertTrue(rep["all_checks_passed"])
                    self.assertEqual(rep["source_mode"], p335.SOURCE_MODE_CLEAN_ROOM)
                    self.assertEqual(rep["redlines"]["raw_firmware_bytes_leaked"], 0)

    def test_05_clean_room_donor_audit_all_21_contracts(self) -> None:
        for env_key in (p335.ENV_FORCE_CLEAN_ROOM, p335.ENV_CLEAN_ROOM_TEST):
            audit = p335.inspect_phase335_donors(env={env_key: "1"})
            self.assertEqual(audit.source_mode, p335.SOURCE_MODE_CLEAN_ROOM)
            self.assertEqual(audit.access_mode, p335.DONOR_ACCESS_MODE)
            self.assertEqual(audit.donor_files_inspected, 21)
            self.assertEqual(audit.compact_donors_verified, 18)
            self.assertEqual(audit.large_donors_verified, 3)
            self.assertTrue(audit.all_contracts_verified)
            self.assertEqual(audit.raw_firmware_bytes_leaked, 0)

    def test_06_local_donor_o_rdonly_cold_audit_under_200ms(self) -> None:
        if p335.resolve_mac_work_root() is None:
            self.skipTest("Local Mac/work donors unavailable in clean-room environment")
        p335._DONOR_AUDIT_CACHE.clear()
        t0 = time.perf_counter()
        audit = p335.inspect_phase335_donors(force_clean_room=False)
        elapsed_s = time.perf_counter() - t0
        self.assertEqual(audit.source_mode, p335.SOURCE_MODE_LOCAL_DONOR)
        self.assertEqual(audit.donor_files_inspected, 21)
        self.assertEqual(audit.compact_donors_verified, 18)
        self.assertEqual(audit.large_donors_verified, 3)
        self.assertTrue(audit.all_contracts_verified)
        self.assertEqual(audit.raw_firmware_bytes_leaked, 0)
        self.assertLess(elapsed_s, 0.20)

    def test_07_compact_donor_tokens_verified(self) -> None:
        self.assertEqual(p335.EXPECTED_DONOR_BYTES["fx3_205_libsdfileupdater"], 60_584)
        self.assertEqual(p335.EXPECTED_DONOR_BYTES["fx6_lib_hotshoe"], 47_808)
        self.assertIn(b"Shoe Audio Set.", p335.COMPACT_DONOR_TOKENS["fx3_string_en_f"])
        self.assertIn(b"Audio Out Timing", p335.COMPACT_DONOR_TOKENS["fx3_string_en_f"])
        self.assertIn(b"4ch Audio Monitoring", p335.COMPACT_DONOR_TOKENS["fx3_string_en_f"])
        self.assertIn(b"Face/Eye Subject", p335.COMPACT_DONOR_TOKENS["fx3_string_en_f"])
        self.assertIn(b"Target Function Settings", p335.COMPACT_DONOR_TOKENS["fx3_string_en_f"])
        self.assertIn(b"Shutter When Pwr OFF", p335.COMPACT_DONOR_TOKENS["fx3_string_en_f"])
        self.assertIn(b"Auto Pixel Restore", p335.COMPACT_DONOR_TOKENS["fx6_string_en"])
        self.assertIn(b"Version Up", p335.COMPACT_DONOR_TOKENS["fx6_string_en_2"])

    def test_08_bounded_window_reader_rejects_oversized_or_negative_reads(self) -> None:
        with tempfile.NamedTemporaryFile() as tf:
            tf.write(b"ABCDEFGH")
            tf.flush()
            self.assertEqual(p335._read_window_readonly_bytes(Path(tf.name), 2, 4), b"CDEF")
            with self.assertRaises(p335.Stage72Phase335Error):
                p335._read_window_readonly_bytes(Path(tf.name), 0, 4097)
            with self.assertRaises(p335.Stage72Phase335Error):
                p335._read_window_readonly_bytes(Path(tf.name), 0, 0)
            with self.assertRaises(p335.Stage72Phase335Error):
                p335._read_window_readonly_bytes(Path(tf.name), -1, 16)

    def test_09_donor_audit_detects_tampered_expected_digest(self) -> None:
        if p335.resolve_mac_work_root() is None:
            self.skipTest("Local Mac/work donors unavailable in clean-room environment")
        p335._DONOR_AUDIT_CACHE.clear()
        try:
            bad_digests = dict(p335.EXPECTED_COMPACT_DONOR_SHA256)
            bad_digests["fx3_lib_airplane"] = "0" * 64
            with unittest.mock.patch.object(
                p335, "EXPECTED_COMPACT_DONOR_SHA256", bad_digests
            ):
                audit = p335.inspect_phase335_donors(force_clean_room=False)
                self.assertFalse(audit.all_contracts_verified)
                self.assertIn(
                    "digest_or_size_mismatch:fx3_lib_airplane", audit.verification_notes
                )
        finally:
            p335._DONOR_AUDIT_CACHE.clear()

    def test_10_json_output_contains_zero_raw_firmware_bytes(self) -> None:
        rep = p335.run_phase335_shoe_audio_4ch_subject_recog_silent_target_version_coemulation(
            force_clean_room=True
        )
        txt = json.dumps(rep)
        self.assertNotIn("\\x7fELF", txt)
        self.assertNotIn("BK4\\x00", txt)
        self.assertEqual(rep["redlines"]["raw_firmware_bytes_leaked"], 0)

    def test_11_full_phase335_payload_passes_clean_room(self) -> None:
        rep = p335.run_phase335_shoe_audio_4ch_subject_recog_silent_target_version_coemulation(
            force_clean_room=True
        )
        self.assertEqual(rep["schema"], p335.SCHEMA_ID)
        self.assertEqual(rep["milestone"], "72/72")
        self.assertTrue(rep["is_72nd_stage_milestone"])
        self.assertTrue(rep["all_checks_passed"])
        self.assertEqual(len(rep["audit_digest_sha256"]), 64)

    def test_12_full_phase335_payload_passes_local_donor_mode(self) -> None:
        if p335.resolve_mac_work_root() is None:
            self.skipTest("Local Mac/work donors unavailable in clean-room environment")
        rep = p335.run_phase335_shoe_audio_4ch_subject_recog_silent_target_version_coemulation(
            force_clean_room=False
        )
        self.assertEqual(rep["source_mode"], p335.SOURCE_MODE_LOCAL_DONOR)
        self.assertTrue(rep["all_checks_passed"])
        self.assertEqual(rep["donor_audit"]["donor_files_inspected"], 21)

    def test_13_fx3_large_windows_contain_wave62_symbols(self) -> None:
        labels = {lbl for _, lbl, _ in p335.LARGE_DONOR_WINDOWS["fx3_appfw"]}
        for expected in (
            "AUDIO_REC_LVL_0",
            "AUDIO_REC_LVL_31",
            "EXT_MIC_48K_24B_4CH",
            "AUDIO_OUT_TIMING_LIVE",
            "AUDIO_OUT_TIMING_LIP",
            "BKID_AUDIO_OUT_TIMING",
            "BKID_AUDIO_LVL_DISP",
            "PRM_FACE_MEM_NUM",
            "SUBJ_DET_BIRD",
            "SUBJ_DET_INSECT",
            "SUBJ_DET_CAR_TRAIN",
            "SUBJ_DET_PLANE",
            "ANIMAL_MOVIE_NOT_SUP",
            "BKID_SILENT_MODE",
            "BKID_APERTURE_DRIVE",
            "BKID_AUTO_PIXEL_MAP",
            "BKID_IMAGE_SENSOR_BARRIER",
            "EVT_ANTI_DUST",
        ):
            self.assertIn(expected, labels)

    def test_14_fx6_large_windows_contain_wave62_symbols(self) -> None:
        labels = {lbl for _, lbl, _ in p335.LARGE_DONOR_WINDOWS["fx6_appfw"]}
        for expected in (
            "FX6_BKID_AUDIO_OUT_TIMING",
            "FX6_AUDIO_TIMING_LIVE",
            "FX6_AUDIO_TIMING_LIP",
            "FX6_IMAGE_SENSOR_BARRIER",
        ):
            self.assertIn(expected, labels)

    # ------------------------------------------------------------------
    # Sub-Model 72A — Shoe Audio 4ch 24-bit, XLR-H1 vs 3.5mm & Audio Out Timing (Tests 15..36)
    # ------------------------------------------------------------------

    def test_15_fx3_audio_recording_has_exact_5_active_menu_items(self) -> None:
        self.assertEqual(len(p335.FX3_ACTIVE_AUDIO_RECORDING_ITEMS), 5)
        self.assertEqual(
            p335.FX3_ACTIVE_AUDIO_RECORDING_ITEMS,
            (
                "Audio Recording",
                "Audio Rec Level",
                "Shoe Audio Set.",
                "Wind Noise Reduct.",
                "Audio Out Timing",
            ),
        )

    def test_16_fx3_xlrh1_digital_48khz_24bit_4ch_across_all_main_codecs(self) -> None:
        for vfmt in p335.VALID_VIDEO_FORMATS_4CH_CAPABLE:
            res = p335.simulate_shoe_audio_4ch_xlrh1_override_and_timing_hil(
                mi_shoe_device="XLR-H1",
                xlrh1_handle_audio="ON",
                xlrh1_digital_analog_switch="DIGITAL",
                xlrh1_input_select="IN1·IN2",
                shoe_audio_set="48kHz/24bit 4ch",
                video_format=vfmt,
            )
            self.assertTrue(res.admitted, vfmt)
            self.assertEqual(res.effective_audio_channels, 4, vfmt)
            self.assertEqual(res.effective_bit_depth, 24, vfmt)
            self.assertTrue(res.disp_audio_meter_auto_4ch_expanded, vfmt)
            self.assertEqual(
                res.channel_routing_map,
                {
                    "CH1": "INPUT1",
                    "CH2": "INPUT2",
                    "CH3": "INPUT3_3.5MM_L",
                    "CH4": "INPUT3_3.5MM_R",
                },
            )

    def test_17_fx3_xlrh1_in1_mirrors_input1_to_ch1_ch2_while_ch3_ch4_keep_input3(self) -> None:
        res = p335.simulate_shoe_audio_4ch_xlrh1_override_and_timing_hil(
            mi_shoe_device="XLR-H1",
            xlrh1_handle_audio="ON",
            xlrh1_digital_analog_switch="DIGITAL",
            xlrh1_input_select="IN1",
            shoe_audio_set="48kHz/24bit 4ch",
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.channel_routing_map["CH1"], "INPUT1")
        self.assertEqual(res.channel_routing_map["CH2"], "INPUT1")
        self.assertEqual(res.channel_routing_map["CH3"], "INPUT3_3.5MM_L")
        self.assertEqual(res.channel_routing_map["CH4"], "INPUT3_3.5MM_R")

    def test_18_fx3_35mm_mic_plug_overrides_xlrh1_and_grays_out_shoe_audio_set(self) -> None:
        blocked = p335.simulate_shoe_audio_4ch_xlrh1_override_and_timing_hil(
            mi_shoe_device="XLR-H1",
            xlrh1_handle_audio="ON",
            mic_35mm_plugged=True,
            shoe_audio_set="48kHz/24bit 4ch",
        )
        self.assertFalse(blocked.admitted)
        self.assertEqual(blocked.errno_code, p335.EOPNOTSUPP_ERRNO)
        self.assertEqual(blocked.effective_active_input, "3.5mm_MIC_2CH")
        self.assertTrue(blocked.shoe_audio_set_grayed_out)

        ok_2ch = p335.simulate_shoe_audio_4ch_xlrh1_override_and_timing_hil(
            mi_shoe_device="XLR-H1",
            mic_35mm_plugged=True,
            shoe_audio_set="48kHz/16bit 2ch",
        )
        self.assertTrue(ok_2ch.admitted)
        self.assertEqual(ok_2ch.effective_audio_channels, 2)
        self.assertTrue(ok_2ch.shoe_audio_set_grayed_out)
        self.assertFalse(ok_2ch.disp_audio_meter_auto_4ch_expanded)

    def test_19_fx3_xlrh1_handle_audio_off_falls_back_to_internal_stereo_mic(self) -> None:
        blocked = p335.simulate_shoe_audio_4ch_xlrh1_override_and_timing_hil(
            mi_shoe_device="XLR-H1",
            xlrh1_handle_audio="OFF",
            shoe_audio_set="48kHz/24bit 4ch",
        )
        self.assertFalse(blocked.admitted)
        self.assertEqual(blocked.errno_code, p335.EOPNOTSUPP_ERRNO)
        self.assertEqual(blocked.effective_active_input, "INTERNAL_STEREO_2CH")

        fallback = p335.simulate_shoe_audio_4ch_xlrh1_override_and_timing_hil(
            mi_shoe_device="XLR-H1",
            xlrh1_handle_audio="OFF",
            shoe_audio_set="48kHz/16bit 2ch",
            wind_noise_reduct="On",
        )
        self.assertTrue(fallback.admitted)
        self.assertEqual(fallback.effective_active_input, "INTERNAL_STEREO_2CH")
        self.assertEqual(fallback.effective_audio_channels, 2)
        self.assertTrue(fallback.wind_noise_reduct_effective_on_active_mic)

    def test_20_fx3_xlrh1_analog_switch_and_legacy_shoe_restrict_to_16bit_2ch(self) -> None:
        for dev, sw in (("XLR-H1", "ANALOG"), ("Legacy_Analog_2ch", "DIGITAL")):
            for mode in ("48kHz/24bit 4ch", "48kHz/24bit 2ch"):
                rej = p335.simulate_shoe_audio_4ch_xlrh1_override_and_timing_hil(
                    mi_shoe_device=dev,
                    xlrh1_digital_analog_switch=sw,
                    shoe_audio_set=mode,
                )
                self.assertFalse(rej.admitted, (dev, sw, mode))
                self.assertEqual(rej.errno_code, p335.EOPNOTSUPP_ERRNO)
                self.assertTrue(rej.shoe_audio_set_grayed_out)

            ok = p335.simulate_shoe_audio_4ch_xlrh1_override_and_timing_hil(
                mi_shoe_device=dev,
                xlrh1_digital_analog_switch=sw,
                shoe_audio_set="48kHz/16bit 2ch",
            )
            self.assertTrue(ok.admitted, (dev, sw))
            self.assertEqual(ok.effective_bit_depth, 16)
            self.assertEqual(ok.effective_audio_channels, 2)

    def test_21_fx3_ecm_b1m_supports_24bit_2ch_but_rejects_4ch(self) -> None:
        ok = p335.simulate_shoe_audio_4ch_xlrh1_override_and_timing_hil(
            mi_shoe_device="ECM-B1M",
            shoe_audio_set="48kHz/24bit 2ch",
        )
        self.assertTrue(ok.admitted)
        self.assertEqual(ok.effective_bit_depth, 24)
        self.assertEqual(ok.effective_audio_channels, 2)

        rej = p335.simulate_shoe_audio_4ch_xlrh1_override_and_timing_hil(
            mi_shoe_device="ECM-B1M",
            shoe_audio_set="48kHz/24bit 4ch",
        )
        self.assertFalse(rej.admitted)
        self.assertEqual(rej.errno_code, p335.EOPNOTSUPP_ERRNO)

    def test_22_fx3_audio_rec_level_0_to_31_default_26_and_delete_key_reset(self) -> None:
        for lvl in (0, 15, 26, 31):
            ok = p335.simulate_shoe_audio_4ch_xlrh1_override_and_timing_hil(
                audio_rec_level=lvl
            )
            self.assertTrue(ok.admitted, lvl)
            self.assertEqual(ok.effective_audio_rec_level, lvl)
            self.assertTrue(ok.internal_limiter_always_on)

        for bad_lvl in (-1, 32):
            bad = p335.simulate_shoe_audio_4ch_xlrh1_override_and_timing_hil(
                audio_rec_level=bad_lvl
            )
            self.assertFalse(bad.admitted, bad_lvl)
            self.assertEqual(bad.errno_code, p335.EINVAL_ERRNO)

        rst = p335.simulate_shoe_audio_4ch_xlrh1_override_and_timing_hil(
            audio_rec_level=5,
            delete_key_reset=True,
        )
        self.assertTrue(rst.admitted)
        self.assertEqual(rst.effective_audio_rec_level, 26)

    def test_23_fx3_internal_limiter_cannot_be_disabled_eopnotsupp(self) -> None:
        rej = p335.simulate_shoe_audio_4ch_xlrh1_override_and_timing_hil(
            disable_internal_limiter_requested=True
        )
        self.assertFalse(rej.admitted)
        self.assertEqual(rej.errno_code, p335.EOPNOTSUPP_ERRNO)
        self.assertTrue(rej.internal_limiter_always_on)

    def test_24_fx3_wind_noise_reduct_effective_only_on_internal_mic(self) -> None:
        internal_on = p335.simulate_shoe_audio_4ch_xlrh1_override_and_timing_hil(
            mi_shoe_device="None",
            wind_noise_reduct="On",
        )
        self.assertTrue(internal_on.admitted)
        self.assertTrue(internal_on.wind_noise_reduct_effective_on_active_mic)

        jack_on = p335.simulate_shoe_audio_4ch_xlrh1_override_and_timing_hil(
            mic_35mm_plugged=True,
            wind_noise_reduct="On",
        )
        self.assertTrue(jack_on.admitted)
        self.assertFalse(jack_on.wind_noise_reduct_effective_on_active_mic)

        xlr_on = p335.simulate_shoe_audio_4ch_xlrh1_override_and_timing_hil(
            mi_shoe_device="XLR-H1",
            xlrh1_handle_audio="ON",
            shoe_audio_set="48kHz/24bit 4ch",
            wind_noise_reduct="On",
        )
        self.assertTrue(xlr_on.admitted)
        self.assertFalse(xlr_on.wind_noise_reduct_effective_on_active_mic)

    def test_25_fx3_audio_out_timing_lives_under_shooting_audio_not_setup_sound(self) -> None:
        for mode in ("Live", "Lip Sync"):
            ok = p335.simulate_shoe_audio_4ch_xlrh1_override_and_timing_hil(
                menu_path_requested="Shooting -> Audio Recording",
                audio_out_timing=mode,
            )
            self.assertTrue(ok.admitted, mode)
            self.assertEqual(ok.effective_audio_out_timing, mode)

        misrouted = p335.simulate_shoe_audio_4ch_xlrh1_override_and_timing_hil(
            menu_path_requested="Setup -> Sound Option",
            audio_out_timing="Lip Sync",
        )
        self.assertFalse(misrouted.admitted)
        self.assertEqual(misrouted.errno_code, p335.EINVAL_ERRNO)

    def test_26_fx3_standalone_audio_level_display_removed_ver2_to_ver702(self) -> None:
        rej = p335.simulate_shoe_audio_4ch_xlrh1_override_and_timing_hil(
            standalone_audio_level_display_requested=True
        )
        self.assertFalse(rej.admitted)
        self.assertEqual(rej.errno_code, p335.EOPNOTSUPP_ERRNO)
        self.assertFalse(rej.standalone_audio_level_display_exposed)

    def test_27_fx3_proxy_always_aac_lc_2ch_128kbps_and_disabled_at_100p_plus(self) -> None:
        proxy_ok = p335.simulate_shoe_audio_4ch_xlrh1_override_and_timing_hil(
            mi_shoe_device="XLR-H1",
            shoe_audio_set="48kHz/24bit 4ch",
            proxy_recording="On",
            fps=59.94,
        )
        self.assertTrue(proxy_ok.admitted)
        self.assertTrue(proxy_ok.effective_proxy_enabled)
        self.assertEqual(proxy_ok.proxy_audio_codec, "MPEG-4 AAC-LC 2ch 128 kbps")
        self.assertEqual(proxy_ok.proxy_audio_channels, 2)

        for high_fps in (100.0, 119.88, 120.0):
            cutoff = p335.simulate_shoe_audio_4ch_xlrh1_override_and_timing_hil(
                proxy_recording="On",
                fps=high_fps,
            )
            self.assertTrue(cutoff.admitted, high_fps)
            self.assertFalse(cutoff.effective_proxy_enabled, high_fps)
            self.assertEqual(cutoff.proxy_audio_channels, 0, high_fps)

        lpcm_rej = p335.simulate_shoe_audio_4ch_xlrh1_override_and_timing_hil(
            proxy_recording="On",
            proxy_4ch_lpcm_requested=True,
        )
        self.assertFalse(lpcm_rej.admitted)
        self.assertEqual(lpcm_rej.errno_code, p335.EOPNOTSUPP_ERRNO)

    def test_28_fx3_sq_mode_disables_audio_recording_and_4ch_timing(self) -> None:
        sq_rej = p335.simulate_shoe_audio_4ch_xlrh1_override_and_timing_hil(
            shoot_mode=p335.SHOOT_MODE_SQ,
            audio_recording="On",
            shoe_audio_set="48kHz/24bit 4ch",
            mi_shoe_device="XLR-H1",
        )
        self.assertFalse(sq_rej.admitted)
        self.assertEqual(sq_rej.errno_code, p335.EOPNOTSUPP_ERRNO)

        sq_off = p335.simulate_shoe_audio_4ch_xlrh1_override_and_timing_hil(
            shoot_mode=p335.SHOOT_MODE_SQ,
            audio_recording="Off",
        )
        self.assertTrue(sq_off.admitted)
        self.assertEqual(sq_off.effective_audio_recording, "Off")
        self.assertEqual(sq_off.effective_audio_channels, 0)

    def test_29_fx3_4ch_audio_monitoring_5_pairs_and_hdmi_4ch_output(self) -> None:
        self.assertEqual(len(p335.VALID_4CH_MONITORING_PAIRS), 5)
        for pair in p335.VALID_4CH_MONITORING_PAIRS:
            for hdmi_out in p335.VALID_HDMI_4CH_OUTPUT_MODES:
                res = p335.simulate_shoe_audio_4ch_xlrh1_override_and_timing_hil(
                    mi_shoe_device="XLR-H1",
                    shoe_audio_set="48kHz/24bit 4ch",
                    four_ch_audio_monitoring=pair,
                    hdmi_4ch_audio_output=hdmi_out,
                )
                self.assertTrue(res.admitted)
                self.assertEqual(res.effective_4ch_audio_monitoring, pair)
                self.assertEqual(res.effective_hdmi_4ch_audio_output, hdmi_out)

    def test_30_fx3_audio_settings_reset_by_camera_settings_reset(self) -> None:
        res = p335.simulate_shoe_audio_4ch_xlrh1_override_and_timing_hil(
            audio_recording="Off",
            audio_rec_level=10,
            shoe_audio_set="48kHz/24bit 4ch",
            wind_noise_reduct="On",
            audio_out_timing="Lip Sync",
            four_ch_audio_monitoring="CH3/CH4",
            hdmi_4ch_audio_output="CH3/CH4",
            camera_settings_reset_applied=True,
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.effective_audio_recording, "On")
        self.assertEqual(res.effective_audio_rec_level, 26)
        self.assertEqual(res.effective_shoe_audio_set, "48kHz/16bit 2ch")
        self.assertEqual(res.effective_wind_noise_reduct, "Off")
        self.assertEqual(res.effective_audio_out_timing, "Live")
        self.assertEqual(res.effective_4ch_audio_monitoring, "CH1/CH2")
        self.assertEqual(res.effective_hdmi_4ch_audio_output, "CH1/CH2")

    def test_31_fx6_native_4ch_24bit_lpcm_6step_limiter_and_dormant_32bit_float(self) -> None:
        self.assertEqual(len(p335.FX6_LIMITER_MODES), 6)
        for lim in p335.FX6_LIMITER_MODES:
            fx6_ok = p335.simulate_shoe_audio_4ch_xlrh1_override_and_timing_hil(
                body_profile=p335.BODY_MODEL_FX6,
                fx6_limiter_mode=lim,
                audio_out_timing="Lip Sync",
            )
            self.assertTrue(fx6_ok.admitted, lim)
            self.assertTrue(fx6_ok.fx6_native_4ch_lpcm)
            self.assertEqual(fx6_ok.effective_audio_channels, 4)
            self.assertEqual(fx6_ok.effective_bit_depth, 24)
            self.assertFalse(fx6_ok.internal_limiter_always_on)

        float_rej = p335.simulate_shoe_audio_4ch_xlrh1_override_and_timing_hil(
            body_profile=p335.BODY_MODEL_FX6,
            fx6_32bit_float_requested=True,
        )
        self.assertFalse(float_rej.admitted)
        self.assertEqual(float_rej.errno_code, p335.EOPNOTSUPP_ERRNO)

    def test_32_72a_invalid_inputs_raise_stage72_error(self) -> None:
        for bad_kwargs in (
            dict(body_profile="ILME-FX30"),
            dict(menu_path_requested="Network -> Audio"),
            dict(shoe_audio_set="96kHz/32bit 4ch"),
            dict(audio_out_timing="Auto"),
            dict(four_ch_audio_monitoring="CH1/CH3"),
            dict(hdmi_4ch_audio_output="MIX_ALL"),
            dict(fx6_limiter_mode="-20dB"),
            dict(xlrh1_input_select="IN3"),
        ):
            with self.assertRaises(p335.Stage72Phase335Error, msg=str(bad_kwargs)):
                p335.simulate_shoe_audio_4ch_xlrh1_override_and_timing_hil(**bad_kwargs)

    # ------------------------------------------------------------------
    # Sub-Model 72B — Face/Eye Subject Myth-Busting & 8-Slot Face Memory (Tests 33..52)
    # ------------------------------------------------------------------

    def test_33_fx3_exposed_subjects_are_strictly_human_and_animal_only(self) -> None:
        self.assertEqual(p335.FX3_EXPOSED_SUBJECT_TYPES, ("Human", "Animal"))
        self.assertEqual(
            p335.DORMANT_SHARED_ELF_SUBJECT_TYPES,
            ("Bird", "Animal/Bird", "Insect", "Car/Train", "Airplane"),
        )

    def test_34_fx3_rejects_dormant_bird_insect_car_airplane_eopnotsupp(self) -> None:
        for mode in (p335.SHOOT_MODE_STILL, p335.SHOOT_MODE_MOVIE, p335.SHOOT_MODE_SQ):
            for subj in p335.DORMANT_SHARED_ELF_SUBJECT_TYPES:
                res = p335.simulate_face_eye_subject_recog_and_face_memory_hil(
                    shoot_mode=mode,
                    face_eye_subject=subj,
                )
                self.assertFalse(res.admitted, (mode, subj))
                self.assertEqual(res.errno_code, p335.EOPNOTSUPP_ERRNO)
                self.assertTrue(res.dormant_subject_blocked)
                self.assertEqual(res.bkid_airplane_hits, 0)

    def test_35_fx3_animal_eye_af_works_in_still_mode_and_grays_regist_faces_priority(self) -> None:
        still_animal = p335.simulate_face_eye_subject_recog_and_face_memory_hil(
            shoot_mode=p335.SHOOT_MODE_STILL,
            face_eye_subject="Animal",
            right_left_eye_select="Left Eye",
        )
        self.assertTrue(still_animal.admitted)
        self.assertEqual(still_animal.effective_face_eye_subject, "Animal")
        self.assertTrue(still_animal.eye_detection_active)
        self.assertFalse(still_animal.face_detection_active)
        self.assertTrue(still_animal.regist_faces_priority_grayed_out)
        self.assertEqual(still_animal.effective_right_left_eye_select, "Left Eye")

    def test_36_fx3_animal_eye_af_blocked_in_movie_and_sq_modes(self) -> None:
        for bad_mode in (p335.SHOOT_MODE_MOVIE, p335.SHOOT_MODE_SQ):
            res = p335.simulate_face_eye_subject_recog_and_face_memory_hil(
                shoot_mode=bad_mode,
                face_eye_subject="Animal",
            )
            self.assertFalse(res.admitted, bad_mode)
            self.assertEqual(res.errno_code, p335.EOPNOTSUPP_ERRNO)
            self.assertTrue(res.animal_eye_af_in_movie_not_support)
            self.assertFalse(res.eye_detection_active)

    def test_37_fx3_human_subject_admitted_in_still_movie_and_sq(self) -> None:
        for mode in p335.VALID_SHOOT_MODES:
            res = p335.simulate_face_eye_subject_recog_and_face_memory_hil(
                shoot_mode=mode,
                face_eye_subject="Human",
                right_left_eye_select="Right Eye",
            )
            self.assertTrue(res.admitted, mode)
            self.assertTrue(res.eye_detection_active)
            self.assertTrue(res.face_detection_active)
            self.assertFalse(res.regist_faces_priority_grayed_out)

    def test_38_fx3_intelligent_auto_locks_face_eye_prior_in_af_on(self) -> None:
        iauto = p335.simulate_face_eye_subject_recog_and_face_memory_hil(
            exposure_mode="Intelligent Auto",
            face_eye_prior_in_af="Off",
        )
        self.assertTrue(iauto.admitted)
        self.assertEqual(iauto.effective_face_eye_prior_in_af, "On")

    def test_39_fx3_face_eye_frame_disp_clean_hdmi_zero_leak(self) -> None:
        res = p335.simulate_face_eye_subject_recog_and_face_memory_hil(
            face_eye_frame_disp="On"
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.effective_face_eye_frame_disp, "On")
        self.assertEqual(res.hdmi_clean_feed_frame_leaked_pixels, 0)

    def test_40_fx3_face_memory_8_slots_survives_camera_reset_and_excluded_from_camset(self) -> None:
        ok8 = p335.simulate_face_eye_subject_recog_and_face_memory_hil(
            face_memory_count=7,
            face_memory_op="New Registration",
            camset_export_requested=True,
            camera_settings_reset_applied=True,
            face_eye_subject="Animal",
            shoot_mode=p335.SHOOT_MODE_STILL,
            face_eye_frame_disp="On",
            right_left_eye_select="Right Eye",
            regist_faces_priority="Off",
        )
        self.assertTrue(ok8.admitted)
        self.assertEqual(ok8.effective_face_memory_count, 8)
        self.assertTrue(ok8.face_memory_survives_camera_reset)
        self.assertFalse(ok8.face_memory_exported_in_camset)
        # Other 5 items reset
        self.assertEqual(ok8.effective_face_eye_subject, "Human")
        self.assertEqual(ok8.effective_face_eye_frame_disp, "Off")
        self.assertEqual(ok8.effective_right_left_eye_select, "Auto")
        self.assertEqual(ok8.effective_regist_faces_priority, "On")

    def test_41_fx3_face_memory_slot_9_overflow_rejected_einval_and_initialize_wipes(self) -> None:
        ovf = p335.simulate_face_eye_subject_recog_and_face_memory_hil(
            face_memory_count=8,
            face_memory_op="New Registration",
        )
        self.assertFalse(ovf.admitted)
        self.assertEqual(ovf.errno_code, p335.EINVAL_ERRNO)

        init_wipe = p335.simulate_face_eye_subject_recog_and_face_memory_hil(
            face_memory_count=8,
            initialize_applied=True,
        )
        self.assertTrue(init_wipe.admitted)
        self.assertEqual(init_wipe.effective_face_memory_count, 0)

        del_all = p335.simulate_face_eye_subject_recog_and_face_memory_hil(
            face_memory_count=5,
            face_memory_op="Delete All",
        )
        self.assertTrue(del_all.admitted)
        self.assertEqual(del_all.effective_face_memory_count, 0)

    def test_42_fx6_human_only_and_saved_tracking_face_session_lifecycle(self) -> None:
        fx6_ok = p335.simulate_face_eye_subject_recog_and_face_memory_hil(
            body_profile=p335.BODY_MODEL_FX6,
            face_eye_subject="Human",
            fx6_face_eye_mode="Face/Eye Only AF",
            fx6_saved_tracking_face_active=True,
        )
        self.assertTrue(fx6_ok.admitted)
        self.assertTrue(fx6_ok.fx6_saved_tracking_face_active)
        self.assertEqual(fx6_ok.face_memory_max_slots, 0)

        fx6_push = p335.simulate_face_eye_subject_recog_and_face_memory_hil(
            body_profile=p335.BODY_MODEL_FX6,
            face_eye_subject="Human",
            fx6_saved_tracking_face_active=True,
            fx6_tracking_stopped_or_push_af=True,
        )
        self.assertTrue(fx6_push.admitted)
        self.assertFalse(fx6_push.fx6_saved_tracking_face_active)

        for subj in ("Animal", "Bird", "Airplane"):
            rej = p335.simulate_face_eye_subject_recog_and_face_memory_hil(
                body_profile=p335.BODY_MODEL_FX6,
                face_eye_subject=subj,
            )
            self.assertFalse(rej.admitted, subj)
            self.assertEqual(rej.errno_code, p335.EOPNOTSUPP_ERRNO)

        mem_rej = p335.simulate_face_eye_subject_recog_and_face_memory_hil(
            body_profile=p335.BODY_MODEL_FX6,
            face_memory_op="New Registration",
        )
        self.assertFalse(mem_rej.admitted)
        self.assertEqual(mem_rej.errno_code, p335.EOPNOTSUPP_ERRNO)

    def test_43_72b_invalid_inputs_raise_stage72_error(self) -> None:
        for bad_kwargs in (
            dict(face_eye_subject="Dog"),
            dict(right_left_eye_select="Both Eyes"),
            dict(face_memory_op="Export"),
            dict(fx6_face_eye_mode="Animal AF"),
        ):
            with self.assertRaises(p335.Stage72Phase335Error, msg=str(bad_kwargs)):
                p335.simulate_face_eye_subject_recog_and_face_memory_hil(**bad_kwargs)

    # ------------------------------------------------------------------
    # Sub-Model 72C — Silent Mode, 2-Item Target Function Settings & Shutter-When-Pwr-OFF (Tests 44..60)
    # ------------------------------------------------------------------

    def test_44_fx3_silent_mode_on_forces_electronic_shutter_and_mutes_audio_signals(self) -> None:
        res = p335.simulate_silent_mode_target_settings_and_shutter_pwr_off_hil(
            silent_mode="On",
            aperture_drive_in_af="Silent Priority",
            auto_pixel_mapping="Off",
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.effective_silent_mode, "On")
        self.assertEqual(res.effective_shutter_type, "Electronic Shutter")
        self.assertEqual(res.effective_interval_shutter_type, "Electronic Shutter")
        self.assertEqual(res.effective_audio_signals, "Off")
        self.assertEqual(res.target_function_item_count, 2)
        self.assertFalse(res.shutter_when_pwr_off_exposed)
        self.assertTrue(res.image_sensor_barrier_dormant)

    def test_45_fx3_silent_mode_locks_exact_5_features_eopnotsupp(self) -> None:
        self.assertEqual(len(p335.FX3_SILENT_MODE_5_LOCKOUTS), 5)
        for feat in p335.FX3_SILENT_MODE_5_LOCKOUTS:
            rej = p335.simulate_silent_mode_target_settings_and_shutter_pwr_off_hil(
                silent_mode="On",
                requested_feature_while_silent=feat,
            )
            self.assertFalse(rej.admitted, feat)
            self.assertEqual(rej.errno_code, p335.EOPNOTSUPP_ERRNO)
            self.assertEqual(len(rej.locked_out_features), 5)

    def test_46_fx3_silent_mode_does_not_auto_disable_af_illuminator(self) -> None:
        res = p335.simulate_silent_mode_target_settings_and_shutter_pwr_off_hil(
            silent_mode="On",
            requested_feature_while_silent="AF Illuminator",
        )
        self.assertTrue(res.admitted)
        self.assertFalse(res.af_illuminator_auto_disabled)

    def test_47_fx3_target_function_settings_has_only_2_items_and_rejects_extra(self) -> None:
        self.assertEqual(
            p335.FX3_TARGET_FUNCTION_ITEMS,
            ("Aperture Drive in AF", "Auto Pixel Mapping"),
        )
        for extra in ("AF Illuminator", "Image Sensor Barrier", "Shutter When Pwr OFF", "Beep"):
            rej = p335.simulate_silent_mode_target_settings_and_shutter_pwr_off_hil(
                extra_target_item_requested=extra
            )
            self.assertFalse(rej.admitted, extra)
            self.assertEqual(rej.errno_code, p335.EOPNOTSUPP_ERRNO)

    def test_48_fx3_aperture_drive_in_af_still_only_vs_movie(self) -> None:
        for mode in p335.VALID_APERTURE_DRIVE_IN_AF_MODES:
            still_res = p335.simulate_silent_mode_target_settings_and_shutter_pwr_off_hil(
                shoot_mode=p335.SHOOT_MODE_STILL,
                silent_mode="On",
                aperture_drive_in_af=mode,
            )
            self.assertTrue(still_res.admitted, mode)
            self.assertTrue(still_res.aperture_drive_still_af_only_applies)

            movie_res = p335.simulate_silent_mode_target_settings_and_shutter_pwr_off_hil(
                shoot_mode=p335.SHOOT_MODE_MOVIE,
                silent_mode="On",
                aperture_drive_in_af=mode,
            )
            self.assertTrue(movie_res.admitted, mode)
            self.assertFalse(movie_res.aperture_drive_still_af_only_applies)

    def test_49_fx3_auto_pixel_mapping_off_blocks_poweroff_shutter_and_cnflasha_write(self) -> None:
        res = p335.simulate_silent_mode_target_settings_and_shutter_pwr_off_hil(
            silent_mode="On",
            auto_pixel_mapping="Off",
            power_off_sequence_triggered=True,
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.poweroff_mech_shutter_actuations, 0)
        self.assertEqual(res.cnflasha_bad_pixel_writes, 0)

    def test_50_fx3_shutter_when_pwr_off_strictly_dormant_eopnotsupp(self) -> None:
        for body in p335.VALID_BODY_MODELS:
            rej = p335.simulate_silent_mode_target_settings_and_shutter_pwr_off_hil(
                body_profile=body,
                shutter_when_pwr_off_requested=True,
            )
            self.assertFalse(rej.admitted, body)
            self.assertEqual(rej.errno_code, p335.EOPNOTSUPP_ERRNO)
            self.assertFalse(rej.shutter_when_pwr_off_exposed)
            self.assertTrue(rej.image_sensor_barrier_dormant)

    def test_51_fx3_silent_mode_items_reset_by_camera_settings_reset(self) -> None:
        res = p335.simulate_silent_mode_target_settings_and_shutter_pwr_off_hil(
            silent_mode="On",
            aperture_drive_in_af="Silent Priority",
            auto_pixel_mapping="Not Target",
            camera_settings_reset_applied=True,
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.effective_silent_mode, "Off")
        self.assertEqual(res.effective_aperture_drive_in_af, "Standard")
        self.assertEqual(res.effective_auto_pixel_mapping, "Off")

    def test_52_fx6_shutterless_rejects_silent_mode_submenu_eopnotsupp(self) -> None:
        fx6_base = p335.simulate_silent_mode_target_settings_and_shutter_pwr_off_hil(
            body_profile=p335.BODY_MODEL_FX6,
            silent_mode="Off",
        )
        self.assertTrue(fx6_base.admitted)
        self.assertFalse(fx6_base.fx6_has_mechanical_shutter)
        self.assertEqual(fx6_base.effective_shutter_type, "Electronic Shutter")
        self.assertEqual(fx6_base.target_function_item_count, 0)

        fx6_silent = p335.simulate_silent_mode_target_settings_and_shutter_pwr_off_hil(
            body_profile=p335.BODY_MODEL_FX6,
            silent_mode="On",
        )
        self.assertFalse(fx6_silent.admitted)
        self.assertEqual(fx6_silent.errno_code, p335.EOPNOTSUPP_ERRNO)

    def test_53_72c_invalid_inputs_raise_stage72_error(self) -> None:
        for bad_kwargs in (
            dict(aperture_drive_in_af="Turbo"),
            dict(auto_pixel_mapping="On"),
            dict(requested_feature_while_silent="High Frame Rate"),
        ):
            with self.assertRaises(p335.Stage72Phase335Error, msg=str(bad_kwargs)):
                p335.simulate_silent_mode_target_settings_and_shutter_pwr_off_hil(**bad_kwargs)

    # ------------------------------------------------------------------
    # Sub-Model 72D — Version Audit & BODYDATA.DAT Slot-1 / Ver. 2.04-2.05 NO-GO Firewall (Tests 54..78)
    # ------------------------------------------------------------------

    def test_54_fx3_version_readonly_audit_and_airplane_mode_silences_update_dot(self) -> None:
        bench = p335.simulate_version_audit_and_bodydata_nogo_firewall_hil(
            current_fw_version=p335.FW_VER_702,
            airplane_mode="On",
            network_latest_fw_available=True,
            lens_attached=True,
            lens_fw_version="04",
            mount_adaptor_attached=True,
            mount_adaptor_fw_version="02",
        )
        self.assertTrue(bench.admitted)
        self.assertEqual(bench.errno_code, 0)
        self.assertFalse(bench.update_badge_shown)
        self.assertEqual(bench.lens_version_displayed, "Ver.04")
        self.assertEqual(bench.mount_adaptor_version_displayed, "Ver.02")
        self.assertFalse(bench.firewall_blocked)
        self.assertEqual(bench.slot1_data_sector_writes, 0)

        online = p335.simulate_version_audit_and_bodydata_nogo_firewall_hil(
            current_fw_version=p335.FW_VER_700,
            airplane_mode="Off",
            network_latest_fw_available=True,
        )
        self.assertTrue(online.admitted)
        self.assertTrue(online.update_badge_shown)

    def test_55_fx3_pre_204_requires_stepping_stone_204_or_205_with_5long_6short_led_code(self) -> None:
        for old_fw in (p335.FW_VER_100, p335.FW_VER_200, p335.FW_VER_202):
            rej = p335.simulate_version_audit_and_bodydata_nogo_firewall_hil(
                current_fw_version=old_fw,
                target_update_version=p335.FW_VER_702,
                media_slot="Slot 1",
                battery_pct=90,
                execute_software_update_requested=True,
            )
            self.assertFalse(rej.admitted, old_fw)
            self.assertEqual(rej.errno_code, p335.EINVAL_ERRNO)
            self.assertTrue(rej.stepping_stone_required)
            self.assertEqual(rej.led_long_blinks, 5)
            self.assertEqual(rej.led_short_blinks, 6)
            self.assertTrue(rej.firewall_blocked)
            self.assertEqual(rej.slot1_data_sector_writes, 0)

    def test_56_fx3_ver_204_and_205_satisfy_stepping_stone_check_but_hit_tier0_nogo_firewall(self) -> None:
        for bridge_fw in (p335.FW_VER_204, p335.FW_VER_205):
            stage_rej = p335.simulate_version_audit_and_bodydata_nogo_firewall_hil(
                current_fw_version=bridge_fw,
                target_update_version=p335.FW_VER_702,
                media_slot="Slot 1",
                battery_pct=85,
                stage_bodydata_to_card_requested=True,
            )
            self.assertFalse(stage_rej.admitted, bridge_fw)
            self.assertEqual(stage_rej.errno_code, p335.EROFS_ERRNO)
            self.assertFalse(stage_rej.stepping_stone_required)
            self.assertTrue(stage_rej.firewall_blocked)
            self.assertEqual(stage_rej.slot1_data_sector_writes, 0)

            exec_rej = p335.simulate_version_audit_and_bodydata_nogo_firewall_hil(
                current_fw_version=bridge_fw,
                target_update_version=p335.FW_VER_702,
                media_slot="Slot 1",
                battery_pct=85,
                execute_software_update_requested=True,
            )
            self.assertFalse(exec_rej.admitted, bridge_fw)
            self.assertEqual(exec_rej.errno_code, p335.EPERM_ERRNO)
            self.assertFalse(exec_rej.emmc_writes_authorized)
            self.assertEqual(exec_rej.emmc_nflasha_write_count, 0)
            self.assertEqual(exec_rej.bodydata_flash_execution_events, 0)

    def test_57_fx3_rejects_slot2_and_renamed_bodydata_dat_einval(self) -> None:
        slot2 = p335.simulate_version_audit_and_bodydata_nogo_firewall_hil(
            current_fw_version=p335.FW_VER_205,
            target_update_version=p335.FW_VER_702,
            media_slot="Slot 2",
            battery_pct=90,
            execute_software_update_requested=True,
        )
        self.assertFalse(slot2.admitted)
        self.assertEqual(slot2.errno_code, p335.EINVAL_ERRNO)
        self.assertEqual(slot2.required_slot, "Slot 1")

        for bad_name in ("BODYDATA(1).DAT", "BODYDATA-3.DAT", "bodydata.dat"):
            renamed = p335.simulate_version_audit_and_bodydata_nogo_firewall_hil(
                current_fw_version=p335.FW_VER_205,
                update_filename=bad_name,
                media_slot="Slot 1",
                battery_pct=90,
                execute_software_update_requested=True,
            )
            self.assertFalse(renamed.admitted, bad_name)
            self.assertEqual(renamed.errno_code, p335.EINVAL_ERRNO)

    def test_58_fx3_rejects_battery_below_51_pct_eperm(self) -> None:
        for pct in (0, 25, 50):
            low = p335.simulate_version_audit_and_bodydata_nogo_firewall_hil(
                current_fw_version=p335.FW_VER_205,
                media_slot="Slot 1",
                battery_pct=pct,
                execute_software_update_requested=True,
            )
            self.assertFalse(low.admitted, pct)
            self.assertEqual(low.errno_code, p335.EPERM_ERRNO)
            self.assertTrue(low.firewall_blocked)

    def test_59_cross_model_fx3_to_fx6_and_fx6_to_fx3_strictly_blocked_eperm(self) -> None:
        for body, file_model in (
            (p335.BODY_MODEL_FX3, p335.BODY_MODEL_FX6),
            (p335.BODY_MODEL_FX6, p335.BODY_MODEL_FX3),
        ):
            rej = p335.simulate_version_audit_and_bodydata_nogo_firewall_hil(
                body_profile=body,
                target_body_model_file=file_model,
                execute_software_update_requested=True,
            )
            self.assertFalse(rej.admitted, (body, file_model))
            self.assertEqual(rej.errno_code, p335.EPERM_ERRNO)
            self.assertTrue(rej.cross_model_rejected)
            self.assertFalse(rej.cross_model_flash_authorized)
            self.assertTrue(rej.firewall_blocked)

    def test_60_fx6_requires_slot_b_ac_adaptor_and_detached_peripherals_before_nogo_firewall(self) -> None:
        slot_a = p335.simulate_version_audit_and_bodydata_nogo_firewall_hil(
            body_profile=p335.BODY_MODEL_FX6,
            current_fw_version=p335.FW_VER_601,
            target_update_version=p335.FW_VER_602,
            target_body_model_file=p335.BODY_MODEL_FX6,
            media_slot="Slot A",
            ac_adaptor_connected=True,
            execute_software_update_requested=True,
        )
        self.assertFalse(slot_a.admitted)
        self.assertEqual(slot_a.errno_code, p335.EINVAL_ERRNO)
        self.assertEqual(slot_a.required_slot, "Slot B")

        no_ac = p335.simulate_version_audit_and_bodydata_nogo_firewall_hil(
            body_profile=p335.BODY_MODEL_FX6,
            current_fw_version=p335.FW_VER_601,
            target_update_version=p335.FW_VER_602,
            target_body_model_file=p335.BODY_MODEL_FX6,
            media_slot="Slot B",
            ac_adaptor_connected=False,
            execute_software_update_requested=True,
        )
        self.assertFalse(no_ac.admitted)
        self.assertEqual(no_ac.errno_code, p335.EPERM_ERRNO)
        self.assertIn("AC Adaptor", no_ac.error_message)

        periph = p335.simulate_version_audit_and_bodydata_nogo_firewall_hil(
            body_profile=p335.BODY_MODEL_FX6,
            current_fw_version=p335.FW_VER_601,
            target_update_version=p335.FW_VER_602,
            target_body_model_file=p335.BODY_MODEL_FX6,
            media_slot="Slot B",
            ac_adaptor_connected=True,
            peripherals_attached=True,
            execute_software_update_requested=True,
        )
        self.assertFalse(periph.admitted)
        self.assertEqual(periph.errno_code, p335.EPERM_ERRNO)

        full_ready_blocked = p335.simulate_version_audit_and_bodydata_nogo_firewall_hil(
            body_profile=p335.BODY_MODEL_FX6,
            current_fw_version=p335.FW_VER_601,
            target_update_version=p335.FW_VER_602,
            target_body_model_file=p335.BODY_MODEL_FX6,
            media_slot="Slot B",
            ac_adaptor_connected=True,
            peripherals_attached=False,
            execute_software_update_requested=True,
        )
        self.assertFalse(full_ready_blocked.admitted)
        self.assertEqual(full_ready_blocked.errno_code, p335.EPERM_ERRNO)
        self.assertTrue(full_ready_blocked.firewall_blocked)

    def test_61_72d_invalid_inputs_raise_stage72_error(self) -> None:
        for bad_kwargs in (
            dict(body_profile="FX9"),
            dict(current_fw_version="9.99"),
            dict(target_update_version="9.99"),
            dict(target_body_model_file="ILCE-7SM3"),
            dict(media_slot="Slot 3"),
            dict(airplane_mode="Auto"),
        ):
            with self.assertRaises(p335.Stage72Phase335Error, msg=str(bad_kwargs)):
                p335.simulate_version_audit_and_bodydata_nogo_firewall_hil(**bad_kwargs)

    # ------------------------------------------------------------------
    # Additional Contract & Boundary Cross-Checks (Tests 62..80)
    # ------------------------------------------------------------------

    def test_62_fx3_audio_recording_off_mutes_effective_channels_even_with_xlrh1(self) -> None:
        res = p335.simulate_shoe_audio_4ch_xlrh1_override_and_timing_hil(
            mi_shoe_device="XLR-H1",
            shoe_audio_set="48kHz/24bit 4ch",
            audio_recording="Off",
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.effective_audio_channels, 0)
        self.assertFalse(res.disp_audio_meter_auto_4ch_expanded)

    def test_63_fx3_shoe_audio_24bit_2ch_and_16bit_2ch_on_xlrh1(self) -> None:
        for mode, expected_bits in (("48kHz/24bit 2ch", 24), ("48kHz/16bit 2ch", 16)):
            res = p335.simulate_shoe_audio_4ch_xlrh1_override_and_timing_hil(
                mi_shoe_device="XLR-H1",
                xlrh1_handle_audio="ON",
                xlrh1_digital_analog_switch="DIGITAL",
                shoe_audio_set=mode,
            )
            self.assertTrue(res.admitted, mode)
            self.assertEqual(res.effective_audio_channels, 2)
            self.assertEqual(res.effective_bit_depth, expected_bits)

    def test_64_fx3_initialize_resets_audio_and_silent_mode_to_defaults(self) -> None:
        aud = p335.simulate_shoe_audio_4ch_xlrh1_override_and_timing_hil(
            audio_recording="Off",
            audio_rec_level=3,
            shoe_audio_set="48kHz/24bit 4ch",
            audio_out_timing="Lip Sync",
            initialize_applied=True,
        )
        self.assertTrue(aud.admitted)
        self.assertEqual(aud.effective_audio_rec_level, 26)
        self.assertEqual(aud.effective_shoe_audio_set, "48kHz/16bit 2ch")
        self.assertEqual(aud.effective_audio_out_timing, "Live")

        sil = p335.simulate_silent_mode_target_settings_and_shutter_pwr_off_hil(
            silent_mode="On",
            aperture_drive_in_af="Not Target",
            auto_pixel_mapping="Not Target",
            initialize_applied=True,
        )
        self.assertTrue(sil.admitted)
        self.assertEqual(sil.effective_silent_mode, "Off")
        self.assertEqual(sil.effective_aperture_drive_in_af, "Standard")
        self.assertEqual(sil.effective_auto_pixel_mapping, "Off")

    def test_65_fx3_face_memory_delete_decrements_and_never_underflows(self) -> None:
        dec = p335.simulate_face_eye_subject_recog_and_face_memory_hil(
            face_memory_count=3,
            face_memory_op="Delete",
        )
        self.assertTrue(dec.admitted)
        self.assertEqual(dec.effective_face_memory_count, 2)

        zero_del = p335.simulate_face_eye_subject_recog_and_face_memory_hil(
            face_memory_count=0,
            face_memory_op="Delete",
        )
        self.assertTrue(zero_del.admitted)
        self.assertEqual(zero_del.effective_face_memory_count, 0)

    def test_66_fx3_face_memory_order_exchanging_preserves_count(self) -> None:
        ex = p335.simulate_face_eye_subject_recog_and_face_memory_hil(
            face_memory_count=4,
            face_memory_op="Order Exchanging",
        )
        self.assertTrue(ex.admitted)
        self.assertEqual(ex.effective_face_memory_count, 4)

    def test_67_fx3_face_eye_prior_in_af_off_disables_eye_and_face_detection(self) -> None:
        off_res = p335.simulate_face_eye_subject_recog_and_face_memory_hil(
            face_eye_prior_in_af="Off",
            face_eye_subject="Human",
        )
        self.assertTrue(off_res.admitted)
        self.assertFalse(off_res.eye_detection_active)
        self.assertFalse(off_res.face_detection_active)

    def test_68_fx3_silent_mode_off_allows_flash_bulb_and_antiflicker(self) -> None:
        for feat in p335.FX3_SILENT_MODE_5_LOCKOUTS:
            res = p335.simulate_silent_mode_target_settings_and_shutter_pwr_off_hil(
                silent_mode="Off",
                requested_feature_while_silent=feat,
            )
            self.assertTrue(res.admitted, feat)
            self.assertEqual(res.effective_shutter_type, "Mechanical Shutter")
            self.assertEqual(res.effective_audio_signals, "On")
            self.assertEqual(res.locked_out_features, ())

    def test_69_fx3_version_audit_without_lens_or_mount_adaptor_omits_strings(self) -> None:
        res = p335.simulate_version_audit_and_bodydata_nogo_firewall_hil(
            lens_attached=False,
            mount_adaptor_attached=False,
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.lens_version_displayed, "")
        self.assertEqual(res.mount_adaptor_version_displayed, "")

    def test_70_fx3_tc_ub_reset_flag_on_bodydata_update(self) -> None:
        fx3 = p335.simulate_version_audit_and_bodydata_nogo_firewall_hil(
            body_profile=p335.BODY_MODEL_FX3
        )
        fx6 = p335.simulate_version_audit_and_bodydata_nogo_firewall_hil(
            body_profile=p335.BODY_MODEL_FX6
        )
        self.assertTrue(fx3.tc_ub_reset_on_update)
        self.assertFalse(fx6.tc_ub_reset_on_update)

    def test_71_milestone_probe_exact_fields(self) -> None:
        probe = p335._build_stage72_milestone_probe()
        self.assertEqual(probe["phase_number"], 335)
        self.assertEqual(probe["stage_index"], 72)
        self.assertEqual(probe["stage_total"], 72)
        self.assertEqual(probe["milestone"], "72/72")
        self.assertTrue(probe["is_72nd_stage_milestone"])
        self.assertEqual(probe["wave"], "Wave-62")
        self.assertEqual(probe["fx3_target_version"], "Ver. 7.02")
        self.assertEqual(probe["fx6_comparison_version"], "Ver. 6.01")

    def test_72_pillar_results_all_passed_in_clean_room(self) -> None:
        rep = p335.run_phase335_shoe_audio_4ch_subject_recog_silent_target_version_coemulation(
            force_clean_room=True
        )
        for pillar_key in (
            "pillar_a_shoe_audio_4ch_xlrh1_override_and_timing_hil",
            "pillar_b_face_eye_subject_recog_and_face_memory_hil",
            "pillar_c_silent_mode_target_settings_and_shutter_pwr_off_hil",
            "pillar_d_version_audit_and_bodydata_nogo_firewall_hil",
        ):
            self.assertTrue(rep[pillar_key]["passed"], pillar_key)

    def test_73_deterministic_digest_identical_across_repeated_clean_room_runs(self) -> None:
        rep1 = p335.run_phase335_shoe_audio_4ch_subject_recog_silent_target_version_coemulation(
            force_clean_room=True
        )
        rep2 = p335.run_phase335_shoe_audio_4ch_subject_recog_silent_target_version_coemulation(
            force_clean_room=True
        )
        self.assertEqual(rep1["audit_digest_sha256"], rep2["audit_digest_sha256"])

    def test_74_deterministic_suite_digest_identical_across_repeated_fast_runs(self) -> None:
        cfg = suite.CoEmulationConfig(**_fast_suite_kwargs())
        r1 = suite.run_fx3_vm_coemulation_suite(cfg)
        r2 = suite.run_fx3_vm_coemulation_suite(cfg)
        self.assertEqual(r1["audit_digest_sha256"], r2["audit_digest_sha256"])

    def test_75_fx3_battery_exactly_51_pct_passes_battery_gate_and_hits_firewall(self) -> None:
        at51 = p335.simulate_version_audit_and_bodydata_nogo_firewall_hil(
            current_fw_version=p335.FW_VER_205,
            target_update_version=p335.FW_VER_702,
            media_slot="Slot 1",
            battery_pct=51,
            execute_software_update_requested=True,
        )
        self.assertFalse(at51.admitted)
        self.assertEqual(at51.errno_code, p335.EPERM_ERRNO)
        self.assertIn("Tier-0 NO-GO", at51.error_message)

    def test_76_fx3_ver_202_staging_to_slot1_also_catches_stepping_stone_before_nogo(self) -> None:
        st = p335.simulate_version_audit_and_bodydata_nogo_firewall_hil(
            current_fw_version=p335.FW_VER_202,
            target_update_version=p335.FW_VER_702,
            media_slot="Slot 1",
            battery_pct=90,
            stage_bodydata_to_card_requested=True,
        )
        self.assertFalse(st.admitted)
        self.assertEqual(st.errno_code, p335.EINVAL_ERRNO)
        self.assertEqual(st.led_long_blinks, 5)
        self.assertEqual(st.led_short_blinks, 6)

    def test_77_fx3_ver_600_and_601_and_702_network_badge_behavior(self) -> None:
        for fw in (p335.FW_VER_600, p335.FW_VER_601, p335.FW_VER_702):
            off = p335.simulate_version_audit_and_bodydata_nogo_firewall_hil(
                current_fw_version=fw,
                airplane_mode="Off",
                network_latest_fw_available=True,
            )
            self.assertTrue(off.update_badge_shown, fw)
            on = p335.simulate_version_audit_and_bodydata_nogo_firewall_hil(
                current_fw_version=fw,
                airplane_mode="On",
                network_latest_fw_available=True,
            )
            self.assertFalse(on.update_badge_shown, fw)

    def test_78_fx3_ver_100_to_204_stepping_stone_allowed_by_version_check_then_blocked_by_nogo(self) -> None:
        bridge = p335.simulate_version_audit_and_bodydata_nogo_firewall_hil(
            current_fw_version=p335.FW_VER_100,
            target_update_version=p335.FW_VER_204,
            media_slot="Slot 1",
            battery_pct=80,
            execute_software_update_requested=True,
        )
        self.assertFalse(bridge.admitted)
        self.assertFalse(bridge.stepping_stone_required)
        self.assertEqual(bridge.errno_code, p335.EPERM_ERRNO)
        self.assertIn("Tier-0 NO-GO", bridge.error_message)

    def test_79_fx3_proxy_on_at_99_99_fps_still_aac_lc_2ch(self) -> None:
        res = p335.simulate_shoe_audio_4ch_xlrh1_override_and_timing_hil(
            proxy_recording="On",
            fps=50.0,
            mi_shoe_device="XLR-H1",
            shoe_audio_set="48kHz/24bit 4ch",
        )
        self.assertTrue(res.admitted)
        self.assertTrue(res.effective_proxy_enabled)
        self.assertEqual(res.proxy_audio_channels, 2)
        self.assertEqual(res.proxy_audio_codec, "MPEG-4 AAC-LC 2ch 128 kbps")

    def test_80_stage72_wrapper_output_schema_matches_suite_contract(self) -> None:
        s72 = suite.run_stage72_realhw_shoe_audio_4ch_subject_recog_silent_target_version_hil(
            suite.CoEmulationConfig(force_clean_room=True)
        )
        self.assertEqual(s72["stage"], p335.STAGE_NAME)
        self.assertEqual(s72["schema"], p335.SCHEMA_ID)
        self.assertEqual(s72["phase_number"], 335)
        self.assertEqual(s72["milestone"], "72/72")
        self.assertTrue(s72["is_72nd_stage_milestone"])
        self.assertTrue(s72["all_checks_passed"])
        self.assertEqual(len(s72["phase335_audit_digest_sha256"]), 64)

    # ------------------------------------------------------------------
    # Standalone CLI, No Hardcoded Paths & Suite Stage 72 Wiring (Tests 81..96)
    # ------------------------------------------------------------------

    def test_81_standalone_cli_help_uses_sys_executable_and_percent_escaping(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                str(
                    FX3_VM_DIR
                    / "realhw_shoe_audio_4ch_subject_recog_silent_target_version_coemulator.py"
                ),
                "--help",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("100%", proc.stdout)
        self.assertIn("51%", proc.stdout)
        self.assertIn("72/72", proc.stdout)

    def test_82_suite_cli_help_percent_escaping_and_stage72_flags(self) -> None:
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
        self.assertIn("72/72 Milestone", proc.stdout)
        self.assertIn("--include-stage72", proc.stdout)
        self.assertIn("--skip-stage72", proc.stdout)
        self.assertIn("--no-include-stage72", proc.stdout)
        self.assertIn("--skip-phase335", proc.stdout)

    def test_83_standalone_cli_summary_and_json_modes(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = p335.main(["--self-test", "--clean-room", "--summary"])
        self.assertEqual(rc, 0)
        self.assertIn("[PASS] Phase 335 Stage 72 (72/72 Milestone)", buf.getvalue())

        buf_json = io.StringIO()
        with contextlib.redirect_stdout(buf_json):
            rc2 = p335.main(["--self-test", "--clean-room", "--json"])
        self.assertEqual(rc2, 0)
        parsed = json.loads(buf_json.getvalue())
        self.assertEqual(parsed["milestone"], "72/72")
        self.assertTrue(parsed["is_72nd_stage_milestone"])
        self.assertTrue(parsed["all_checks_passed"])
        self.assertNotIn("\\x7fELF", buf_json.getvalue())

    def test_84_no_hardcoded_usr_bin_python3_in_stage72_files(self) -> None:
        mod_src = (
            FX3_VM_DIR
            / "realhw_shoe_audio_4ch_subject_recog_silent_target_version_coemulator.py"
        ).read_text(encoding="utf-8")
        tst_src = Path(__file__).read_text(encoding="utf-8")
        forbidden = "/usr/bin/" + "python3"
        self.assertNotIn(forbidden, mod_src)
        self.assertNotIn(forbidden, tst_src)

    def test_85_suite_default_config_enables_stage72_and_full_run_contains_72_stages(self) -> None:
        cfg = suite.CoEmulationConfig()
        self.assertTrue(
            cfg.include_phase335_realhw_shoe_audio_4ch_subject_recog_silent_target_version_hil
        )
        self.assertTrue(cfg.include_stage72)
        self.assertTrue(
            cfg.stage72_realhw_shoe_audio_4ch_subject_recog_silent_target_version_hil
        )

        t0 = time.monotonic()
        rep = suite.run_fx3_vm_coemulation_suite(cfg)
        elapsed = time.monotonic() - t0
        self.assertTrue(rep["all_checks_passed"])
        stage_keys = [k for k in rep if re.match(r"^stage\d+_", k)]
        self.assertGreaterEqual(len(stage_keys), 72)
        s72 = rep["stage72_realhw_shoe_audio_4ch_subject_recog_silent_target_version_hil"]
        self.assertTrue(s72["all_checks_passed"])
        self.assertTrue(s72["is_72nd_stage_milestone"])
        self.assertEqual(s72["milestone"], "72/72")
        self.assertEqual(s72["phase_number"], 335)
        max_elapsed = 30.0 if IS_CI else 15.0
        self.assertLess(elapsed, max_elapsed)

    def test_86_suite_skip_flags_and_summary_cli_for_stage72(self) -> None:
        for flag in ("--skip-stage72", "--no-include-stage72", "--skip-phase335"):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = suite.main([*_FAST_CLI_FLAGS, flag, "--json"])
            self.assertEqual(rc, 0)
            data = json.loads(buf.getvalue())
            self.assertNotIn(
                "stage72_realhw_shoe_audio_4ch_subject_recog_silent_target_version_hil",
                data,
            )
            self.assertFalse(data["config"]["include_stage72"])

        buf_sum = io.StringIO()
        with contextlib.redirect_stdout(buf_sum):
            rc_sum = suite.main([*_FAST_CLI_FLAGS, "--include-stage72", "--summary"])
        self.assertEqual(rc_sum, 0)
        self.assertIn(
            "realhw_shoe_audio_4ch_subject_recog_silent_target_version_hil=CLEAN_ROOM_SYNTHETIC("
            "m72=72/72,aud=5,subj=2,fmem=8,slck=5,tgt=2,sh_off=0,bd_blk=1,s1_wr=0,emmc_wr=0)",
            buf_sum.getvalue(),
        )

    def test_87_suite_tamper_72a_audio_redlines_detected(self) -> None:
        for attr, val in (
            ("FX3_ACTIVE_AUDIO_RECORDING_MENU_ITEMS", 6),
            ("AUDIO_REC_LEVEL_STEPS", 31),
            ("FOUR_CH_MONITORING_PAIRS_COUNT", 4),
            ("JACK_35MM_SHOE_OVERRIDE_VIOLATIONS", 1),
            ("EXTERNAL_MIC_WIND_REDUCTION_LEAK_EVENTS", 1),
            ("PROXY_4CH_AUDIO_BYPASS_EVENTS", 1),
            ("STANDALONE_AUDIO_LEVEL_DISPLAY_SPOOF_EVENTS", 1),
            ("AUDIO_OUT_TIMING_SETUP_MISROUTE_EVENTS", 1),
        ):
            with unittest.mock.patch.object(p335, attr, val):
                rep = suite.run_fx3_vm_coemulation_suite(
                    suite.CoEmulationConfig(**_fast_suite_kwargs())
                )
                self.assertFalse(rep["all_checks_passed"], attr)

    def test_88_suite_tamper_72b_subject_recog_or_face_memory_detected(self) -> None:
        for attr, val in (
            ("FX3_EXPOSED_FACE_EYE_SUBJECTS_COUNT", 3),
            ("FX3_FACE_MEMORY_MAX_SLOTS", 9),
            ("DORMANT_BIRD_INSECT_CAR_AIRPLANE_EXPOSED_EVENTS", 1),
            ("ANIMAL_EYE_AF_IN_MOVIE_BYPASS_EVENTS", 1),
            ("FACE_EYE_FRAME_HDMI_LEAKED_PIXELS", 1),
            ("FACE_MEMORY_CAMSET_LEAK_EVENTS", 1),
            ("FACE_MEMORY_CAMERA_RESET_WIPE_EVENTS", 1),
        ):
            with unittest.mock.patch.object(p335, attr, val):
                rep = suite.run_fx3_vm_coemulation_suite(
                    suite.CoEmulationConfig(**_fast_suite_kwargs())
                )
                self.assertFalse(rep["all_checks_passed"], attr)

    def test_89_suite_tamper_72c_silent_mode_target_or_shutter_pwr_off_detected(self) -> None:
        for attr, val in (
            ("FX3_SILENT_MODE_HARD_LOCKED_FEATURES_COUNT", 4),
            ("FX3_TARGET_FUNCTION_SETTINGS_ITEM_COUNT", 3),
            ("FX3_HAS_SHUTTER_WHEN_PWR_OFF", True),
            ("FX6_HAS_MECHANICAL_SHUTTER", True),
            ("SILENT_MODE_5LOCK_BYPASS_EVENTS", 1),
            ("TARGET_FUNCTION_EXTRA_ITEM_SPOOF_EVENTS", 1),
            ("SHUTTER_WHEN_PWR_OFF_EXPOSED_EVENTS", 1),
            ("POWEROFF_PIXEL_MAPPING_SHUTTER_ACTUATIONS", 1),
        ):
            with unittest.mock.patch.object(p335, attr, val):
                rep = suite.run_fx3_vm_coemulation_suite(
                    suite.CoEmulationConfig(**_fast_suite_kwargs())
                )
                self.assertFalse(rep["all_checks_passed"], attr)

    def test_90_suite_tamper_72d_version_or_bodydata_firewall_detected(self) -> None:
        for attr, val in (
            ("AIRPLANE_MODE_VERSION_DOT_LEAK_EVENTS", 1),
            ("BODYDATA_STEPPING_STONE_BYPASS_EVENTS", 1),
            ("BODYDATA_SLOT2_OR_FX6_SLOTA_BYPASS_EVENTS", 1),
            ("BODYDATA_FLASH_EXECUTION_EVENTS", 1),
            ("CROSS_MODEL_FLASH_ATTEMPT_ADMITTED_EVENTS", 1),
            ("BODYDATA_FLASH_EXECUTION_BLOCKED", False),
            ("EMMC_WRITES_AUTHORIZED", True),
            ("CROSS_MODEL_FLASH_AUTHORIZED", True),
        ):
            with unittest.mock.patch.object(p335, attr, val):
                rep = suite.run_fx3_vm_coemulation_suite(
                    suite.CoEmulationConfig(**_fast_suite_kwargs())
                )
                self.assertFalse(rep["all_checks_passed"], attr)

    def test_91_suite_tamper_hard_write_and_rf_redlines_detected(self) -> None:
        for attr, val in (
            ("PERSISTENT_EMMC_WRITES_AUTHORIZED", True),
            ("HARDWARE_LIVE_ATTACHMENT_AUTHORIZED", True),
            ("PHYSICAL_DEVICE_WRITES", 1),
            ("EMMC_NFLASHA_WRITE_COUNT", 1),
            ("SLOT1_DATA_SECTOR_WRITES", 1),
            ("SLOT1_AVF_INFO_MUTATED", True),
            ("RF_PACKETS_TRANSMITTED", 1),
            ("RF_NVS_MUTATION_BYTES", 16),
            ("RAW_FIRMWARE_BYTES_LEAKED", 4),
        ):
            with unittest.mock.patch.object(p335, attr, val):
                rep = suite.run_fx3_vm_coemulation_suite(
                    suite.CoEmulationConfig(**_fast_suite_kwargs())
                )
                self.assertFalse(rep["all_checks_passed"], attr)

    def test_92_suite_tamper_runtime_fault_redlines_detected(self) -> None:
        for attr, val in (
            ("NOP_COUNT", 1),
            ("GUEST_CODE_MODIFICATION_BYTES", 4),
            ("CP_MUTATION_BYTES", 4),
            ("WBI_MUTATION_BYTES", 4),
            ("CALIBRATION_MUTATION_BYTES", 4),
            ("CNFLASHA_MUTATION_BYTES", 4),
            ("CNFLASHA_USERSPACE_WRITE_BLOCKED", False),
            ("RSV_ORPHAN_COUNT", 1),
            ("WF12_00342260_HITS", 1),
            ("APPFW_CRASHES", 1),
        ):
            with unittest.mock.patch.object(p335, attr, val):
                rep = suite.run_fx3_vm_coemulation_suite(
                    suite.CoEmulationConfig(**_fast_suite_kwargs())
                )
                self.assertFalse(rep["all_checks_passed"], attr)

    def test_93_stage72_all_redline_zero_keys_verified(self) -> None:
        rep = p335.run_phase335_shoe_audio_4ch_subject_recog_silent_target_version_coemulation(
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
            "jack_35mm_shoe_override_violations",
            "external_mic_wind_reduction_leak_events",
            "proxy_4ch_audio_bypass_events",
            "standalone_audio_level_display_spoof_events",
            "audio_out_timing_setup_misroute_events",
            "dormant_bird_insect_car_airplane_exposed_events",
            "animal_eye_af_in_movie_bypass_events",
            "face_eye_frame_hdmi_leaked_pixels",
            "face_memory_camset_leak_events",
            "face_memory_camera_reset_wipe_events",
            "silent_mode_5lock_bypass_events",
            "target_function_extra_item_spoof_events",
            "shutter_when_pwr_off_exposed_events",
            "poweroff_pixel_mapping_shutter_actuations",
            "airplane_mode_version_dot_leak_events",
            "bodydata_stepping_stone_bypass_events",
            "bodydata_slot2_or_fx6_slota_bypass_events",
            "bodydata_flash_execution_events",
            "cross_model_flash_attempt_admitted_events",
            "rsv_orphan_count",
            "wf12_00342260_hits",
            "appfw_crashes",
            "null_gpio_derefs",
            "mailbox_stalls",
            "stock_cp_fault_count",
            "raw_firmware_bytes_leaked",
        ):
            self.assertEqual(red[zero_key], 0, zero_key)

    def test_94_stage72_all_false_and_true_boolean_redlines_verified(self) -> None:
        rep = p335.run_phase335_shoe_audio_4ch_subject_recog_silent_target_version_coemulation(
            force_clean_room=True
        )
        red = rep["redlines"]
        for true_key in (
            "p8_cp_mutation_forbidden",
            "cnflasha_userspace_write_blocked",
            "bodydata_flash_execution_blocked",
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
            "fx3_has_shutter_when_pwr_off",
            "fx6_has_mechanical_shutter",
        ):
            self.assertFalse(red[false_key], false_key)

    def test_95_suite_tamper_milestone_flag_detected(self) -> None:
        with unittest.mock.patch.object(p335, "IS_72ND_STAGE_MILESTONE", False):
            # Tampering module constant alone still keeps _build_stage72_milestone_probe check active
            rep = suite.run_fx3_vm_coemulation_suite(
                suite.CoEmulationConfig(**_fast_suite_kwargs())
            )
            self.assertFalse(rep["all_checks_passed"])

    def test_96_clean_room_mocked_empty_env_and_local_env_parity(self) -> None:
        clean_rep = p335.run_phase335_shoe_audio_4ch_subject_recog_silent_target_version_coemulation(
            force_clean_room=True
        )
        env_rep = p335.run_phase335_shoe_audio_4ch_subject_recog_silent_target_version_coemulation(
            env={p335.ENV_FORCE_CLEAN_ROOM: "1"}
        )
        self.assertEqual(
            clean_rep["audit_digest_sha256"],
            env_rep["audit_digest_sha256"],
        )


if __name__ == "__main__":
    unittest.main()
