#!/usr/bin/env python3
"""Unit tests for Phase 337 (Stage 73 — 73/73 VM HIL Stages Milestone!):
Real-Hardware `ILME-FX3 Ver. 7.02` vs `ILME-FX6 Ver. 6.01` Wave-63:
- 73A: `[HDMI Output Settings]` (8 active items, Reset-immune, `Rec. Media dur
  HDMI Output = On` default vs `Off(HDMI Only)`, `Output Resolution` 1080p
  reclamp under `Log != Off`/`PPLUT1..4` when `Rec. Media=On`, `4K Output
  Set.(HDMI Only)` 10-bit & dormant `24.00p 8bit`, `24.00p` forced reboot,
  `RAW Output` `4264x2408` 16-bit requiring Movie + `Log != Off` + `S-Log3`
  lock + `Active` IBIS disabled + `HDMI Info. Display` forced `Off`, Ver. 2.00+
  removal of standalone `Color Gamut for RAW Output`
  `BKID_APP_setting_color_gamut_for_raw_out`, `REC Control` requiring `Time
  Code Output = On`, `4ch Audio Output` `CH1/CH2` vs `CH3/CH4`), `Slot 1` Tier-0
  `EROFS=30` when `Rec. Media dur HDMI Output = On` vs zero card writes when
  `Off(HDMI Only)`, vs `FX6` `12G-SDI RAW` (`4096x2160`/`3840x2160 "C"`, HDMI
  `<=1080p`) / `RAW(HDMI)` (`4240x2392`, no `24Hz`) & `SDI/HDMI Remote I/F` vs
  `Parallel Rec`,
- 73B: `[De-Squeeze Display]` (Reset-immune: `Off`/`1.3x`/`1.5x`/`1.6x` [actual
  `1.65x` `VAL_DE_SQUEEZE_DISP_1_65X`]/`2.0x`, `0` hits for `1.8x`), 4 forced
  lockouts (`Focus Mode=Manual Focus`, `Focus Area=Wide`, `SteadyShot=Off`,
  `Face Priority in Multi Metering=Off`), 6 non-desqueezed bypass states
  (`Still` `MOVIE` button, `Remote Shooting`, `Photo Capture`, `Log=Off`,
  `RAW Output=On` HDMI, `Off(HDMI Only)` HDMI), coexistence with `Focus
  Magnifier` / `Bright Monitoring`, vs `FX6` `Ratio (HDMI/VF)`
  (`Off`/`1.3x`/`1.5x`/`2.0x`, never `1.6x`, never SDI),
- 73C: `[REC Lamp]` (myth-busting `[Tally Light]`: 3 physical LEDs with
  rear+top `REC` button hardware-coupled -> `All On`/`Only Front Off`/`All Off`,
  independent of `Silent Mode`, Reset-immune), `[Emphasized REC Display]`
  (Resettable, Clean-HDMI 0-leak), `[Remain Shoot Display]` (active Still burst
  indicator, Reset-immune), and Still `[Auto Review]` (`Off`/`2/5/10 Sec`,
  disabled in Interval Shoot, Reset-immune) vs `FX6` independent
  `Front/Rear Tally` + `G/Y Tally`, and
- 73D: Still mechanical `[Anti-flicker Shoot.]` (Resettable, 100/120 Hz,
  disabled under electronic shutter/`Silent Mode=On`/`BULB`/Movie/S&Q) vs
  **100% dormant `[Var. Shutter]`** (`BKID_APP_setting_high_res_ss` / `_f 0x6831`)
  vs `FX6` `ECS` (`23.99..8000 Hz`), plus `[APS-C S35 Shooting]` (`Resettable: Not
  available` — Wave 42 errata fix!, total 4K/DCI 4K/HDMI-4K/RAW lockout leaving
  `HD 1920x1080` up to `120p` blocking S&Q `200/240fps`, Still `L: 12M`
  downgraded to `M: 5.1M` `2768x1848` 3:2 / `4.3M` 16:9) HIL
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
import realhw_hdmi_raw_desqueeze_reclamp_varshutter_apsc_coemulator as p337  # noqa: E402

IS_CI = os.environ.get("GITHUB_ACTIONS", "").lower() == "true"


def _fast_suite_kwargs(**overrides: object) -> dict:
    """Fast config skipping unrelated optional stages 4..72 for quick Stage 73 isolation tests."""
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
]


class TestRealHwStage73HdmiRawDesqueezeRecLampVarShutterApsc(unittest.TestCase):
    # ------------------------------------------------------------------
    # Donor Audit, Bounded O_RDONLY & 4-Mode Fallback Tests (Tests 1..14)
    # ------------------------------------------------------------------

    def test_01_milestone_constants_73_of_73(self) -> None:
        self.assertEqual(p337.PHASE_NUMBER, 337)
        self.assertEqual(p337.STAGE_INDEX, 73)
        self.assertEqual(p337.STAGE_TOTAL, 73)
        self.assertEqual(p337.MILESTONE_LABEL, "73/73")
        self.assertTrue(p337.IS_73RD_STAGE_MILESTONE)
        self.assertEqual(len(p337.DONOR_RELPATHS), 17)
        self.assertEqual(len(p337.EXPECTED_DONOR_BYTES), 17)
        self.assertEqual(len(p337.EXPECTED_COMPACT_DONOR_SHA256), 14)
        self.assertEqual(len(p337.EXPECTED_LARGE_HEAD4K_SHA256), 3)
        self.assertEqual(len(p337.LARGE_DONOR_WINDOWS), 3)

    def test_02_hard_safety_redlines_locked(self) -> None:
        self.assertTrue(p337.P8_CP_MUTATION_FORBIDDEN)
        self.assertTrue(p337.CNFLASHA_USERSPACE_WRITE_BLOCKED)
        self.assertFalse(p337.PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(p337.EMMC_WRITES_AUTHORIZED)
        self.assertFalse(p337.CROSS_MODEL_FLASH_AUTHORIZED)
        self.assertFalse(p337.HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        self.assertFalse(p337.OVERALL_READY_FOR_HARDWARE_ATTACH)
        self.assertFalse(p337.ISP_WRITE_AUTHORIZED)
        self.assertFalse(p337.SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(p337.EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        self.assertFalse(p337.SLOT1_AVF_INFO_MUTATED)
        self.assertEqual(p337.FX3_ACTIVE_HDMI_OUTPUT_SETTINGS_ITEMS, 8)
        self.assertTrue(p337.HDMI_COLOR_GAMUT_FOR_RAW_OUT_REMOVED_V2)
        self.assertEqual(p337.HDMI_RAW_WIDTH, 4264)
        self.assertEqual(p337.HDMI_RAW_HEIGHT, 2408)
        self.assertEqual(p337.HDMI_RAW_BIT_DEPTH, 16)
        self.assertEqual(p337.FX3_DESQUEEZE_ACTIVE_OPTIONS_COUNT, 5)
        self.assertEqual(p337.FX3_DESQUEEZE_1_6X_ACTUAL_FACTOR, 1.65)
        self.assertEqual(p337.FX3_DESQUEEZE_FORCED_LOCKOUT_COUNT, 4)
        self.assertEqual(p337.FX3_REC_LAMP_PHYSICAL_LED_COUNT, 3)
        self.assertEqual(p337.FX3_REC_LAMP_ACTIVE_STATES_COUNT, 3)
        self.assertEqual(p337.FX3_STILL_APSC_32_EFFECTIVE_MP, 5.1)
        self.assertEqual(p337.SLOT1_DATA_SECTOR_WRITES, 0)
        self.assertEqual(p337.EMMC_NFLASHA_WRITE_COUNT, 0)
        self.assertEqual(p337.RAW_FIRMWARE_BYTES_LEAKED, 0)

    def test_03_clean_room_test_mode_both_env_vars(self) -> None:
        self.assertFalse(p337.clean_room_test_mode(env={}))
        self.assertTrue(p337.clean_room_test_mode(env={p337.ENV_FORCE_CLEAN_ROOM: "1"}))
        self.assertTrue(p337.clean_room_test_mode(env={p337.ENV_CLEAN_ROOM_TEST: "1"}))
        self.assertTrue(p337.clean_room_test_mode(force_clean_room=True, env={}))
        self.assertFalse(
            p337.clean_room_test_mode(
                force_clean_room=False,
                env={p337.ENV_FORCE_CLEAN_ROOM: "1", p337.ENV_CLEAN_ROOM_TEST: "1"},
            )
        )

    def test_04_resolve_mac_work_root_and_donor_paths_none_fallback(self) -> None:
        self.assertIsNone(p337.resolve_phase337_donor_paths(None))
        self.assertIsNone(
            p337.resolve_mac_work_root(
                env={p337.ENV_MAC_WORK_ROOT: p337.CLEAN_ROOM_SENTINEL_DIRNAME}
            )
        )
        self.assertIsNone(
            p337.resolve_mac_work_root(
                env={p337.ENV_MAC_ROOT: p337.CLEAN_ROOM_SENTINEL_DIRNAME}
            )
        )
        with tempfile.TemporaryDirectory() as td:
            with unittest.mock.patch.object(p337, "DEFAULT_REPO_ROOT", Path(td)):
                with unittest.mock.patch.object(p337, "LEGACY_MAC_ROOT", Path(td) / "none"):
                    self.assertIsNone(p337.resolve_mac_work_root(env={}))
                    self.assertIsNone(p337.resolve_phase337_donor_paths(None, env={}))
                    rep = p337.run_phase337_hdmi_raw_desqueeze_reclamp_varshutter_apsc_coemulation(
                        env={}
                    )
                    self.assertTrue(rep["all_checks_passed"])
                    self.assertEqual(rep["source_mode"], p337.SOURCE_MODE_CLEAN_ROOM)
                    self.assertEqual(rep["redlines"]["raw_firmware_bytes_leaked"], 0)

    def test_05_clean_room_donor_audit_all_17_contracts(self) -> None:
        for env_key in (p337.ENV_FORCE_CLEAN_ROOM, p337.ENV_CLEAN_ROOM_TEST):
            audit = p337.inspect_phase337_donors(env={env_key: "1"})
            self.assertEqual(audit.source_mode, p337.SOURCE_MODE_CLEAN_ROOM)
            self.assertEqual(audit.access_mode, p337.DONOR_ACCESS_MODE)
            self.assertEqual(audit.donor_files_inspected, 17)
            self.assertEqual(audit.compact_donors_verified, 14)
            self.assertEqual(audit.large_donors_verified, 3)
            self.assertTrue(audit.negative_1_8x_verified_absent)
            self.assertTrue(audit.all_contracts_verified)
            self.assertEqual(audit.raw_firmware_bytes_leaked, 0)

    def test_06_local_donor_o_rdonly_cold_audit_under_200ms(self) -> None:
        if p337.resolve_mac_work_root() is None:
            self.skipTest("Local Mac/work donors unavailable in clean-room environment")
        p337._DONOR_AUDIT_CACHE.clear()
        t0 = time.perf_counter()
        audit = p337.inspect_phase337_donors(force_clean_room=False)
        elapsed_s = time.perf_counter() - t0
        self.assertEqual(audit.source_mode, p337.SOURCE_MODE_LOCAL_DONOR)
        self.assertEqual(audit.donor_files_inspected, 17)
        self.assertEqual(audit.compact_donors_verified, 14)
        self.assertEqual(audit.large_donors_verified, 3)
        self.assertTrue(audit.negative_1_8x_verified_absent)
        self.assertTrue(audit.all_contracts_verified)
        self.assertEqual(audit.raw_firmware_bytes_leaked, 0)
        self.assertLess(elapsed_s, 0.20)

    def test_07_compact_donor_tokens_and_1_8x_absence(self) -> None:
        self.assertEqual(p337.EXPECTED_DONOR_BYTES["fx3_string_en_f"], 373_820)
        self.assertEqual(p337.EXPECTED_DONOR_BYTES["fx6_string_en"], 118_208)
        self.assertIn(b"HDMI Output Settings", p337.COMPACT_DONOR_TOKENS["fx3_string_en_f"])
        self.assertIn(b"1.65x compression", p337.COMPACT_DONOR_TOKENS["fx3_string_en_f"])
        self.assertIn(b"REC Lamp", p337.COMPACT_DONOR_TOKENS["fx3_string_en_f"])
        self.assertIn(b"Remain Shoot Display", p337.COMPACT_DONOR_TOKENS["fx3_string_en_f"])
        self.assertIn(b"Anti-flicker Shoot.", p337.COMPACT_DONOR_TOKENS["fx3_string_en_f"])
        self.assertIn(b"APS-C/Super 35mm", p337.COMPACT_DONOR_TOKENS["fx3_string_en_f"])
        self.assertIn(b"RAW(HDMI)", p337.COMPACT_DONOR_TOKENS["fx6_string_en"])
        self.assertIn(b"SDI/HDMI Remote I/F", p337.COMPACT_DONOR_TOKENS["fx6_string_en_2"])
        for key, toks in p337.COMPACT_DONOR_TOKENS.items():
            for t in toks:
                self.assertNotIn(b"1.8x", t, key)

    def test_08_bounded_window_reader_rejects_oversized_or_negative_reads(self) -> None:
        with tempfile.NamedTemporaryFile() as tf:
            tf.write(b"ABCDEFGH")
            tf.flush()
            self.assertEqual(p337._read_window_readonly_bytes(Path(tf.name), 2, 4), b"CDEF")
            with self.assertRaises(p337.Stage73Phase337Error):
                p337._read_window_readonly_bytes(Path(tf.name), 0, 4097)
            with self.assertRaises(p337.Stage73Phase337Error):
                p337._read_window_readonly_bytes(Path(tf.name), 0, 0)
            with self.assertRaises(p337.Stage73Phase337Error):
                p337._read_window_readonly_bytes(Path(tf.name), -1, 16)

    def test_09_donor_audit_detects_tampered_expected_digest(self) -> None:
        if p337.resolve_mac_work_root() is None:
            self.skipTest("Local Mac/work donors unavailable in clean-room environment")
        p337._DONOR_AUDIT_CACHE.clear()
        try:
            bad_digests = dict(p337.EXPECTED_COMPACT_DONOR_SHA256)
            bad_digests["fx3_string_en_f"] = "0" * 64
            with unittest.mock.patch.object(
                p337, "EXPECTED_COMPACT_DONOR_SHA256", bad_digests
            ):
                audit = p337.inspect_phase337_donors(force_clean_room=False)
                self.assertFalse(audit.all_contracts_verified)
                self.assertIn(
                    "digest_or_size_mismatch:fx3_string_en_f", audit.verification_notes
                )
        finally:
            p337._DONOR_AUDIT_CACHE.clear()

    def test_10_json_output_contains_zero_raw_firmware_bytes(self) -> None:
        rep = p337.run_phase337_hdmi_raw_desqueeze_reclamp_varshutter_apsc_coemulation(
            force_clean_room=True
        )
        txt = json.dumps(rep)
        self.assertNotIn("\\x7fELF", txt)
        self.assertNotIn("BK4\\x00", txt)
        self.assertEqual(rep["redlines"]["raw_firmware_bytes_leaked"], 0)

    def test_11_full_phase337_payload_passes_clean_room(self) -> None:
        rep = p337.run_phase337_hdmi_raw_desqueeze_reclamp_varshutter_apsc_coemulation(
            force_clean_room=True
        )
        self.assertEqual(rep["schema"], p337.SCHEMA_ID)
        self.assertEqual(rep["milestone"], "73/73")
        self.assertTrue(rep["is_73rd_stage_milestone"])
        self.assertTrue(rep["all_checks_passed"])
        self.assertEqual(len(rep["audit_digest_sha256"]), 64)

    def test_12_full_phase337_payload_passes_local_donor_mode(self) -> None:
        if p337.resolve_mac_work_root() is None:
            self.skipTest("Local Mac/work donors unavailable in clean-room environment")
        rep = p337.run_phase337_hdmi_raw_desqueeze_reclamp_varshutter_apsc_coemulation(
            force_clean_room=False
        )
        self.assertEqual(rep["source_mode"], p337.SOURCE_MODE_LOCAL_DONOR)
        self.assertTrue(rep["all_checks_passed"])
        self.assertEqual(rep["donor_audit"]["donor_files_inspected"], 17)

    def test_13_fx3_large_windows_contain_wave63_symbols(self) -> None:
        labels = {lbl for _, lbl, _ in p337.LARGE_DONOR_WINDOWS["fx3_appfw"]}
        for expected in (
            "BKID_HDMI_RES",
            "BKID_REC_MEDIA_HDMI",
            "BKID_HDMI_4K_SET",
            "BKID_RAW_OUT",
            "BKID_RAW_OUT_FPS",
            "BKID_COLOR_GAMUT_RAW",
            "BKID_HDMI_TC",
            "BKID_REC_CTRL",
            "BKID_4CH_OUT",
            "BKID_REC_LAMP",
            "RAW_REC_MEDIA_ON_SLOT1",
            "BKID_DE_SQUEEZE",
            "BKID_AUTO_REVIEW",
            "VAL_DE_SQUEEZE_1_65X",
            "REC_LAMP_ONLY_FRONT_OFF",
            "REC_LAMP_LIGHT_UP_ONLY_ONE",
            "BKID_EMPH_REC",
            "BKID_ANTI_FLICKER",
            "BKID_HIGH_RES_SS",
            "REMAIN_SHOOT_DISP",
            "BKID_SUPER_35MM",
        ):
            self.assertIn(expected, labels)

    def test_14_fx6_and_bk4_large_windows_verified(self) -> None:
        fx6_labels = {lbl for _, lbl, _ in p337.LARGE_DONOR_WINDOWS["fx6_appfw"]}
        for expected in (
            "FX6_DESQUEEZE_HDMI",
            "FX6_DESQUEEZE_LCD",
            "FX6_ECS_FREQ",
            "FX6_BKID_ECS_FREQ",
            "FX6_FRONT_TALLY",
            "FX6_REAR_TALLY",
            "FX6_IMAGER_SCANMODE",
        ):
            self.assertIn(expected, fx6_labels)
        bk4_labels = {lbl for _, lbl, _ in p337.LARGE_DONOR_WINDOWS["fx3_bk4"]}
        self.assertEqual(bk4_labels, {"BK4", "CX95900", "ILME_FX3"})

    # ------------------------------------------------------------------
    # Sub-Model 73A: [HDMI Output Settings], 4264x2408 RAW & Slot-1 (15..30)
    # ------------------------------------------------------------------

    def test_15_73a_8_active_items_and_reset_immunity_vs_initialize(self) -> None:
        self.assertEqual(p337.FX3_ACTIVE_HDMI_OUTPUT_ITEMS_COUNT, 8)
        self.assertEqual(p337.FX3_ACTIVE_HDMI_OUTPUT_SETTINGS_ITEMS, 8)
        res_reset = p337.simulate_hdmi_output_raw_4264_reclamp_and_slot1_hil(
            rec_media_dur_hdmi="Off(HDMI Only)",
            output_resolution="1080i",
            four_k_hdmi_only_set="23.98p 10bit",
            previous_four_k_hdmi_only_set="23.98p 10bit",
            raw_output="On",
            raw_output_fps="23.98p",
            log_shooting="Cine EI",
            time_code_output="On",
            rec_control="On",
            four_ch_audio_output="CH3/CH4",
            camera_settings_reset_applied=True,
        )
        self.assertTrue(res_reset.admitted)
        self.assertFalse(res_reset.resettable_via_camera_settings_reset)
        self.assertEqual(res_reset.effective_rec_media_dur_hdmi, "Off(HDMI Only)")
        self.assertTrue(res_reset.raw_output_active)
        self.assertEqual(res_reset.effective_rec_control, "On")
        self.assertEqual(res_reset.effective_4ch_audio_output, "CH3/CH4")

        res_init = p337.simulate_hdmi_output_raw_4264_reclamp_and_slot1_hil(
            rec_media_dur_hdmi="Off(HDMI Only)",
            raw_output="On",
            log_shooting="Cine EI",
            time_code_output="On",
            rec_control="On",
            four_ch_audio_output="CH3/CH4",
            initialize_applied=True,
        )
        self.assertTrue(res_init.admitted)
        self.assertEqual(res_init.effective_rec_media_dur_hdmi, "On")
        self.assertFalse(res_init.raw_output_active)
        self.assertEqual(res_init.effective_rec_control, "Off")
        self.assertEqual(res_init.effective_4ch_audio_output, "CH1/CH2")

    def test_16_73a_log_and_pplut_reclamp_hdmi_to_1080p_when_rec_media_on(self) -> None:
        for log_mode in ("Flexible ISO", "Cine EI", "Cine EI Quick"):
            r = p337.simulate_hdmi_output_raw_4264_reclamp_and_slot1_hil(
                rec_media_dur_hdmi="On",
                output_resolution="2160p",
                log_shooting=log_mode,
            )
            self.assertTrue(r.admitted, log_mode)
            self.assertTrue(r.hdmi_clamped_1080p, log_mode)
            self.assertEqual(r.effective_output_resolution, "1080p", log_mode)

        for pplut in ("PPLUT1", "PPLUT2", "PPLUT3", "PPLUT4"):
            r = p337.simulate_hdmi_output_raw_4264_reclamp_and_slot1_hil(
                rec_media_dur_hdmi="On",
                output_resolution="Auto",
                picture_profile=pplut,
            )
            self.assertTrue(r.admitted, pplut)
            self.assertTrue(r.hdmi_clamped_1080p, pplut)
            self.assertEqual(r.effective_output_resolution, "1080p", pplut)

    def test_17_73a_hdmi_only_10bit_modes_and_24_00p_forced_reboot(self) -> None:
        for mode in p337.VALID_4K_HDMI_ONLY_MODES_10BIT:
            r = p337.simulate_hdmi_output_raw_4264_reclamp_and_slot1_hil(
                rec_media_dur_hdmi="Off(HDMI Only)",
                four_k_hdmi_only_set=mode,
                previous_four_k_hdmi_only_set=mode,
            )
            self.assertTrue(r.admitted, mode)
            self.assertFalse(r.forced_reboot_on_24_00p, mode)
            self.assertEqual(r.effective_output_resolution, mode)
            self.assertEqual(r.hdmi_only_card_writes, 0)

        enter_24 = p337.simulate_hdmi_output_raw_4264_reclamp_and_slot1_hil(
            rec_media_dur_hdmi="Off(HDMI Only)",
            four_k_hdmi_only_set="24.00p 10bit",
            previous_four_k_hdmi_only_set="59.94p 10bit",
        )
        self.assertTrue(enter_24.admitted)
        self.assertTrue(enter_24.forced_reboot_on_24_00p)

        exit_24 = p337.simulate_hdmi_output_raw_4264_reclamp_and_slot1_hil(
            rec_media_dur_hdmi="Off(HDMI Only)",
            four_k_hdmi_only_set="23.98p 10bit",
            previous_four_k_hdmi_only_set="24.00p 10bit",
        )
        self.assertTrue(exit_24.admitted)
        self.assertTrue(exit_24.forced_reboot_on_24_00p)

    def test_18_73a_dormant_24_00p_8bit_rejected_eopnotsupp(self) -> None:
        rej = p337.simulate_hdmi_output_raw_4264_reclamp_and_slot1_hil(
            rec_media_dur_hdmi="Off(HDMI Only)",
            four_k_hdmi_only_set="24.00p 8bit",
        )
        self.assertFalse(rej.admitted)
        self.assertEqual(rej.errno_code, p337.EOPNOTSUPP_ERRNO)

    def test_19_73a_raw_4264x2408_16bit_locks_slog3_ibis_and_hdmi_info_off(self) -> None:
        res = p337.simulate_hdmi_output_raw_4264_reclamp_and_slot1_hil(
            shoot_mode=p337.SHOOT_MODE_MOVIE,
            rec_media_dur_hdmi="Off(HDMI Only)",
            raw_output="On",
            raw_output_fps="59.94p",
            log_shooting="Flexible ISO",
            ibis_mode="Active",
            hdmi_info_display="On",
            rec_triggered=True,
        )
        self.assertTrue(res.admitted)
        self.assertTrue(res.raw_output_active)
        self.assertEqual(res.hdmi_raw_resolution, "4264x2408")
        self.assertEqual(res.hdmi_raw_bit_depth, 16)
        self.assertEqual(res.effective_gamma_locked, "S-Log3")
        self.assertTrue(res.active_ibis_disabled)
        self.assertEqual(res.effective_ibis_mode, "Standard")
        self.assertEqual(res.effective_hdmi_info_display, "Off")
        self.assertFalse(res.internal_xavc_write_attempted)
        self.assertFalse(res.internal_proxy_write_attempted)
        self.assertFalse(res.inbody_raw_written)
        self.assertEqual(res.slot1_data_sector_writes, 0)

    def test_20_73a_raw_requires_movie_log_and_compatible_device(self) -> None:
        non_movie = p337.simulate_hdmi_output_raw_4264_reclamp_and_slot1_hil(
            shoot_mode=p337.SHOOT_MODE_STILL,
            raw_output="On",
            log_shooting="Cine EI",
        )
        self.assertFalse(non_movie.admitted)
        self.assertEqual(non_movie.errno_code, p337.EOPNOTSUPP_ERRNO)

        no_log = p337.simulate_hdmi_output_raw_4264_reclamp_and_slot1_hil(
            shoot_mode=p337.SHOOT_MODE_MOVIE,
            raw_output="On",
            log_shooting="Off",
        )
        self.assertFalse(no_log.admitted)
        self.assertEqual(no_log.errno_code, p337.EINVAL_ERRNO)

        no_dev = p337.simulate_hdmi_output_raw_4264_reclamp_and_slot1_hil(
            shoot_mode=p337.SHOOT_MODE_MOVIE,
            raw_output="On",
            log_shooting="Cine EI",
            raw_compatible_device_connected=False,
        )
        self.assertFalse(no_dev.admitted)
        self.assertEqual(no_dev.errno_code, p337.EINVAL_ERRNO)

    def test_21_73a_ver2_plus_removed_color_gamut_for_raw_output(self) -> None:
        for fw in (p337.FW_VER_200, p337.FW_VER_300, p337.FW_VER_700, p337.FW_VER_702):
            rej = p337.simulate_hdmi_output_raw_4264_reclamp_and_slot1_hil(
                fw_version=fw,
                color_gamut_for_raw_out_requested=True,
            )
            self.assertFalse(rej.admitted, fw)
            self.assertEqual(rej.errno_code, p337.EOPNOTSUPP_ERRNO)
            self.assertFalse(rej.color_gamut_for_raw_out_exposed)
            self.assertTrue(rej.color_gamut_managed_via_log)

    def test_22_73a_rec_control_requires_time_code_output_on(self) -> None:
        rej = p337.simulate_hdmi_output_raw_4264_reclamp_and_slot1_hil(
            time_code_output="Off",
            rec_control="On",
        )
        self.assertFalse(rej.admitted)
        self.assertEqual(rej.errno_code, p337.EINVAL_ERRNO)

        ok = p337.simulate_hdmi_output_raw_4264_reclamp_and_slot1_hil(
            time_code_output="On",
            rec_control="On",
        )
        self.assertTrue(ok.admitted)
        self.assertEqual(ok.effective_time_code_output, "On")
        self.assertEqual(ok.effective_rec_control, "On")

    def test_23_73a_rec_media_on_with_raw_triggers_slot1_erofs_30(self) -> None:
        for slot in ("Slot 1", "Simult. Recording"):
            blocked = p337.simulate_hdmi_output_raw_4264_reclamp_and_slot1_hil(
                rec_media_dur_hdmi="On",
                raw_output="On",
                log_shooting="Cine EI",
                recording_media_slot=slot,
                rec_triggered=True,
            )
            self.assertFalse(blocked.admitted, slot)
            self.assertEqual(blocked.errno_code, p337.EROFS_ERRNO)
            self.assertTrue(blocked.slot1_erofs_triggered)
            self.assertTrue(blocked.internal_xavc_write_attempted)
            self.assertTrue(blocked.internal_proxy_write_attempted)
            self.assertFalse(blocked.inbody_raw_written)
            self.assertEqual(blocked.slot1_data_sector_writes, 0)

        slot2_only = p337.simulate_hdmi_output_raw_4264_reclamp_and_slot1_hil(
            rec_media_dur_hdmi="On",
            raw_output="On",
            log_shooting="Cine EI",
            recording_media_slot="Slot 2",
            rec_triggered=True,
        )
        self.assertTrue(slot2_only.admitted)
        self.assertFalse(slot2_only.slot1_erofs_triggered)
        self.assertTrue(slot2_only.internal_xavc_write_attempted)
        self.assertEqual(slot2_only.slot1_data_sector_writes, 0)

    def test_24_73a_sq_locks_off_hdmi_only_raw_and_tc_output(self) -> None:
        r_hdmi = p337.simulate_hdmi_output_raw_4264_reclamp_and_slot1_hil(
            shoot_mode=p337.SHOOT_MODE_SQ,
            rec_media_dur_hdmi="Off(HDMI Only)",
        )
        self.assertFalse(r_hdmi.admitted)
        self.assertEqual(r_hdmi.errno_code, p337.EOPNOTSUPP_ERRNO)

        r_raw = p337.simulate_hdmi_output_raw_4264_reclamp_and_slot1_hil(
            shoot_mode=p337.SHOOT_MODE_SQ,
            raw_output="On",
            log_shooting="Cine EI",
        )
        self.assertFalse(r_raw.admitted)
        self.assertEqual(r_raw.errno_code, p337.EOPNOTSUPP_ERRNO)

        r_tc = p337.simulate_hdmi_output_raw_4264_reclamp_and_slot1_hil(
            shoot_mode=p337.SHOOT_MODE_SQ,
            time_code_output="On",
        )
        self.assertFalse(r_tc.admitted)
        self.assertEqual(r_tc.errno_code, p337.EOPNOTSUPP_ERRNO)

    def test_25_73a_hdmi_info_display_on_blanks_inbody_lcd(self) -> None:
        res = p337.simulate_hdmi_output_raw_4264_reclamp_and_slot1_hil(
            rec_media_dur_hdmi="On",
            raw_output="Off",
            hdmi_info_display="On",
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.effective_hdmi_info_display, "On")
        self.assertTrue(res.inbody_lcd_forced_off)

    def test_26_73a_4ch_audio_output_ch1_ch2_vs_ch3_ch4(self) -> None:
        for pair in p337.VALID_HDMI_4CH_AUDIO_OUTPUT:
            r = p337.simulate_hdmi_output_raw_4264_reclamp_and_slot1_hil(
                four_ch_audio_output=pair
            )
            self.assertTrue(r.admitted, pair)
            self.assertEqual(r.effective_4ch_audio_output, pair)

    def test_27_73a_fx6_12g_sdi_raw_clamps_hdmi_to_1080p_and_4ch_sdi_lpcm(self) -> None:
        for mode, exp_raw_res in (
            ("12G-SDI RAW (4096x2160)", "4096x2160"),
            ("12G-SDI RAW (3840x2160 C)", "3840x2160_C"),
        ):
            r = p337.simulate_hdmi_output_raw_4264_reclamp_and_slot1_hil(
                body_profile=p337.BODY_MODEL_FX6,
                fx6_raw_mode=mode,
                fx6_sdi_hdmi_rec_ctrl="Parallel Rec",
                fx6_card_inserted=True,
            )
            self.assertTrue(r.admitted, mode)
            self.assertTrue(r.hdmi_clamped_1080p)
            self.assertEqual(r.effective_output_resolution, "1080p")
            self.assertEqual(r.hdmi_raw_resolution, exp_raw_res)
            self.assertTrue(r.fx6_sdi_4ch_lpcm)
            self.assertEqual(r.effective_4ch_audio_output, "4ch_SDI_24bit_LPCM")

    def test_28_73a_fx6_raw_hdmi_4240x2392_blocks_24_00hz(self) -> None:
        rej = p337.simulate_hdmi_output_raw_4264_reclamp_and_slot1_hil(
            body_profile=p337.BODY_MODEL_FX6,
            fx6_raw_mode="RAW(HDMI) (4240x2392)",
            fx6_raw_hdmi_fps="24.00p",
        )
        self.assertFalse(rej.admitted)
        self.assertEqual(rej.errno_code, p337.EOPNOTSUPP_ERRNO)

        ok = p337.simulate_hdmi_output_raw_4264_reclamp_and_slot1_hil(
            body_profile=p337.BODY_MODEL_FX6,
            fx6_raw_mode="RAW(HDMI) (4240x2392)",
            fx6_raw_hdmi_fps="23.98p",
        )
        self.assertTrue(ok.admitted)
        self.assertEqual(ok.hdmi_raw_resolution, "4240x2392")

    def test_29_73a_fx6_sdi_hdmi_remote_if_cardless_vs_parallel_rec_card_required(self) -> None:
        remote_cardless = p337.simulate_hdmi_output_raw_4264_reclamp_and_slot1_hil(
            body_profile=p337.BODY_MODEL_FX6,
            fx6_raw_mode="RAW(HDMI) (4240x2392)",
            fx6_raw_hdmi_fps="59.94p",
            fx6_sdi_hdmi_rec_ctrl="SDI/HDMI Remote I/F",
            fx6_card_inserted=False,
        )
        self.assertTrue(remote_cardless.admitted)

        parallel_no_card = p337.simulate_hdmi_output_raw_4264_reclamp_and_slot1_hil(
            body_profile=p337.BODY_MODEL_FX6,
            fx6_raw_mode="12G-SDI RAW (4096x2160)",
            fx6_sdi_hdmi_rec_ctrl="Parallel Rec",
            fx6_card_inserted=False,
        )
        self.assertFalse(parallel_no_card.admitted)
        self.assertEqual(parallel_no_card.errno_code, p337.EINVAL_ERRNO)

    def test_30_73a_invalid_inputs_raise_stage73_error(self) -> None:
        for bad_kwargs in (
            dict(body_profile="FX9"),
            dict(fw_version="9.99"),
            dict(shoot_mode="Timelapse"),
            dict(rec_media_dur_hdmi="Always"),
            dict(output_resolution="4320p"),
            dict(four_k_hdmi_only_set="120p 10bit"),
            dict(raw_output="Auto"),
            dict(raw_output_fps="119.88p"),
            dict(log_shooting="S-Log2"),
            dict(ibis_mode="Dynamic"),
            dict(hdmi_info_display="Auto"),
            dict(time_code_output="Auto"),
            dict(rec_control="Auto"),
            dict(four_ch_audio_output="CH1/CH3"),
            dict(recording_media_slot="Slot 3"),
            dict(fx6_raw_mode="X-OCN"),
            dict(fx6_sdi_hdmi_rec_ctrl="Dual"),
        ):
            with self.assertRaises(p337.Stage73Phase337Error, msg=str(bad_kwargs)):
                p337.simulate_hdmi_output_raw_4264_reclamp_and_slot1_hil(**bad_kwargs)

    # ------------------------------------------------------------------
    # Sub-Model 73B: [De-Squeeze Display], 4 Lockouts & 6 Bypasses (31..44)
    # ------------------------------------------------------------------

    def test_31_73b_desqueeze_reset_immunity_vs_initialize(self) -> None:
        res_reset = p337.simulate_desqueeze_display_4locks_and_bypass_hil(
            desqueeze_mode="1.5x",
            camera_settings_reset_applied=True,
        )
        self.assertTrue(res_reset.admitted)
        self.assertFalse(res_reset.resettable_via_camera_settings_reset)
        self.assertEqual(res_reset.effective_desqueeze, "1.5x")
        self.assertEqual(res_reset.actual_horizontal_factor, 1.5)

        res_init = p337.simulate_desqueeze_display_4locks_and_bypass_hil(
            desqueeze_mode="1.5x",
            initialize_applied=True,
        )
        self.assertTrue(res_init.admitted)
        self.assertEqual(res_init.effective_desqueeze, "Off")
        self.assertEqual(res_init.actual_horizontal_factor, 1.0)

    def test_32_73b_1_6x_executes_exact_1_65x_factor_and_version_history(self) -> None:
        for mode, factor in (("Off", 1.0), ("1.3x", 1.3), ("1.5x", 1.5), ("1.6x", 1.65), ("2.0x", 2.0)):
            r = p337.simulate_desqueeze_display_4locks_and_bypass_hil(
                fw_version=p337.FW_VER_702,
                desqueeze_mode=mode,
            )
            self.assertTrue(r.admitted, mode)
            self.assertEqual(r.actual_horizontal_factor, factor, mode)
            self.assertFalse(r.inbody_recorded_stream_desqueezed)

        # Ver. 3.00 introduced Off/1.3x/2.0x; Ver. 7.00+ activated 1.5x/1.6x
        for v3_ok in ("Off", "1.3x", "2.0x"):
            r3 = p337.simulate_desqueeze_display_4locks_and_bypass_hil(
                fw_version=p337.FW_VER_300,
                desqueeze_mode=v3_ok,
            )
            self.assertTrue(r3.admitted, v3_ok)
        for v7_only in ("1.5x", "1.6x"):
            r3_no = p337.simulate_desqueeze_display_4locks_and_bypass_hil(
                fw_version=p337.FW_VER_300,
                desqueeze_mode=v7_only,
            )
            self.assertFalse(r3_no.admitted, v7_only)
            self.assertEqual(r3_no.errno_code, p337.EOPNOTSUPP_ERRNO)

    def test_33_73b_1_8x_strictly_absent_and_rejected_fx3_and_fx6(self) -> None:
        for body in p337.VALID_BODY_MODELS:
            rej = p337.simulate_desqueeze_display_4locks_and_bypass_hil(
                body_profile=body,
                desqueeze_mode="1.8x",
            )
            self.assertFalse(rej.admitted, body)
            self.assertEqual(rej.errno_code, p337.EOPNOTSUPP_ERRNO)

    def test_34_73b_still_mode_rejects_active_desqueeze_but_allows_off(self) -> None:
        rej = p337.simulate_desqueeze_display_4locks_and_bypass_hil(
            shoot_mode=p337.SHOOT_MODE_STILL,
            desqueeze_mode="1.3x",
            still_movie_button_rec=False,
        )
        self.assertFalse(rej.admitted)
        self.assertEqual(rej.errno_code, p337.EOPNOTSUPP_ERRNO)

        off_still = p337.simulate_desqueeze_display_4locks_and_bypass_hil(
            shoot_mode=p337.SHOOT_MODE_STILL,
            desqueeze_mode="Off",
        )
        self.assertTrue(off_still.admitted)

    def test_35_73b_4_forced_lockouts_enforced(self) -> None:
        for override in (
            dict(requested_focus_mode="AF-C"),
            dict(requested_focus_mode="DMF"),
            dict(requested_focus_area="Zone"),
            dict(requested_focus_area="Spot"),
            dict(requested_steadyshot="Standard"),
            dict(requested_steadyshot="Active"),
            dict(requested_face_priority_metering="On"),
        ):
            rej = p337.simulate_desqueeze_display_4locks_and_bypass_hil(
                desqueeze_mode="1.6x",
                **override,
            )
            self.assertFalse(rej.admitted, str(override))
            self.assertEqual(rej.errno_code, p337.EOPNOTSUPP_ERRNO)
            self.assertEqual(rej.effective_focus_mode, "Manual Focus")
            self.assertEqual(rej.effective_focus_area, "Wide")
            self.assertEqual(rej.effective_steadyshot, "Off")
            self.assertEqual(rej.effective_face_priority_metering, "Off")

    def test_36_73b_bypass_still_movie_button_recording(self) -> None:
        r = p337.simulate_desqueeze_display_4locks_and_bypass_hil(
            shoot_mode=p337.SHOOT_MODE_STILL,
            desqueeze_mode="1.5x",
            still_movie_button_rec=True,
        )
        self.assertTrue(r.admitted)
        self.assertFalse(r.lcd_desqueezed)
        self.assertFalse(r.hdmi_desqueezed)
        self.assertIn("Still MOVIE button", r.bypass_reason)

    def test_37_73b_bypass_remote_shooting(self) -> None:
        r = p337.simulate_desqueeze_display_4locks_and_bypass_hil(
            desqueeze_mode="1.5x",
            remote_shooting=True,
        )
        self.assertTrue(r.admitted)
        self.assertFalse(r.lcd_desqueezed)
        self.assertFalse(r.hdmi_desqueezed)
        self.assertIn("Remote Shooting", r.bypass_reason)

    def test_38_73b_bypass_photo_capture(self) -> None:
        r = p337.simulate_desqueeze_display_4locks_and_bypass_hil(
            desqueeze_mode="2.0x",
            photo_capture=True,
        )
        self.assertTrue(r.admitted)
        self.assertFalse(r.lcd_desqueezed)
        self.assertFalse(r.hdmi_desqueezed)
        self.assertIn("Photo Capture", r.bypass_reason)

    def test_39_73b_bypass_log_shooting_off(self) -> None:
        r = p337.simulate_desqueeze_display_4locks_and_bypass_hil(
            desqueeze_mode="1.6x",
            log_shooting="Off",
        )
        self.assertTrue(r.admitted)
        self.assertFalse(r.lcd_desqueezed)
        self.assertFalse(r.hdmi_desqueezed)
        self.assertIn("Log Shooting=Off", r.bypass_reason)

    def test_40_73b_bypass_hdmi_raw_and_hdmi_only_leave_lcd_desqueezed_only(self) -> None:
        r_raw = p337.simulate_desqueeze_display_4locks_and_bypass_hil(
            desqueeze_mode="1.6x",
            raw_output="On",
        )
        self.assertTrue(r_raw.admitted)
        self.assertTrue(r_raw.lcd_desqueezed)
        self.assertFalse(r_raw.hdmi_desqueezed)
        self.assertIn("RAW Output=On (HDMI)", r_raw.bypass_reason)

        r_hdmi_only = p337.simulate_desqueeze_display_4locks_and_bypass_hil(
            desqueeze_mode="1.5x",
            rec_media_dur_hdmi="Off(HDMI Only)",
        )
        self.assertTrue(r_hdmi_only.admitted)
        self.assertTrue(r_hdmi_only.lcd_desqueezed)
        self.assertFalse(r_hdmi_only.hdmi_desqueezed)
        self.assertIn("Off(HDMI Only)", r_hdmi_only.bypass_reason)

    def test_41_73b_coexists_with_focus_magnifier_and_bright_monitoring(self) -> None:
        r = p337.simulate_desqueeze_display_4locks_and_bypass_hil(
            shoot_mode=p337.SHOOT_MODE_SQ,
            desqueeze_mode="2.0x",
            focus_magnifier_active=True,
            bright_monitoring_active=True,
        )
        self.assertTrue(r.admitted)
        self.assertTrue(r.lcd_desqueezed)
        self.assertTrue(r.hdmi_desqueezed)
        self.assertTrue(r.coexists_with_focus_magnifier)
        self.assertTrue(r.coexists_with_bright_monitoring)

    def test_42_73b_inbody_recorded_stream_never_desqueezed(self) -> None:
        for mode in p337.FX3_DESQUEEZE_ACTIVE_MODES:
            r = p337.simulate_desqueeze_display_4locks_and_bypass_hil(desqueeze_mode=mode)
            self.assertFalse(r.inbody_recorded_stream_desqueezed, mode)

    def test_43_73b_fx6_ratio_hdmi_vf_excludes_1_6x_never_sdi_disables_af_spot(self) -> None:
        for ok_mode in p337.FX6_DESQUEEZE_ACTIVE_MODES:
            r = p337.simulate_desqueeze_display_4locks_and_bypass_hil(
                body_profile=p337.BODY_MODEL_FX6,
                desqueeze_mode=ok_mode,
            )
            self.assertTrue(r.admitted, ok_mode)
            self.assertFalse(r.sdi_desqueezed)
            if ok_mode != "Off":
                self.assertTrue(r.lcd_desqueezed)
                self.assertTrue(r.hdmi_desqueezed)

        r_raw_hdmi = p337.simulate_desqueeze_display_4locks_and_bypass_hil(
            body_profile=p337.BODY_MODEL_FX6,
            desqueeze_mode="1.5x",
            fx6_sd_or_raw_hdmi=True,
        )
        self.assertTrue(r_raw_hdmi.admitted)
        self.assertTrue(r_raw_hdmi.lcd_desqueezed)
        self.assertFalse(r_raw_hdmi.hdmi_desqueezed)
        self.assertFalse(r_raw_hdmi.sdi_desqueezed)

        rej_16 = p337.simulate_desqueeze_display_4locks_and_bypass_hil(
            body_profile=p337.BODY_MODEL_FX6,
            desqueeze_mode="1.6x",
        )
        self.assertFalse(rej_16.admitted)
        self.assertEqual(rej_16.errno_code, p337.EOPNOTSUPP_ERRNO)

        rej_af = p337.simulate_desqueeze_display_4locks_and_bypass_hil(
            body_profile=p337.BODY_MODEL_FX6,
            desqueeze_mode="1.3x",
            requested_focus_mode="AF-C",
        )
        self.assertFalse(rej_af.admitted)
        self.assertEqual(rej_af.errno_code, p337.EOPNOTSUPP_ERRNO)

        rej_spot = p337.simulate_desqueeze_display_4locks_and_bypass_hil(
            body_profile=p337.BODY_MODEL_FX6,
            desqueeze_mode="1.3x",
            requested_focus_area="Spot",
        )
        self.assertFalse(rej_spot.admitted)
        self.assertEqual(rej_spot.errno_code, p337.EOPNOTSUPP_ERRNO)

    def test_44_73b_invalid_inputs_raise_stage73_error(self) -> None:
        for bad_kwargs in (
            dict(body_profile="FX30"),
            dict(fw_version="8.00"),
            dict(shoot_mode="Custom"),
            dict(desqueeze_mode="1.4x"),
            dict(requested_focus_mode="AF-A"),
            dict(requested_focus_area="Expand"),
            dict(requested_steadyshot="Dynamic"),
            dict(requested_face_priority_metering="Auto"),
        ):
            with self.assertRaises(p337.Stage73Phase337Error, msg=str(bad_kwargs)):
                p337.simulate_desqueeze_display_4locks_and_bypass_hil(**bad_kwargs)

    # ------------------------------------------------------------------
    # Sub-Model 73C: REC Lamp 3-LED, Emphasized REC, Remain Shoot, Auto Review (45..58)
    # ------------------------------------------------------------------

    def test_45_73c_myth_tally_light_menu_strictly_rejected_eopnotsupp(self) -> None:
        rej = p337.simulate_rec_lamp_emph_rec_remain_shoot_auto_review_hil(
            tally_light_menu_requested=True
        )
        self.assertFalse(rej.admitted)
        self.assertEqual(rej.errno_code, p337.EOPNOTSUPP_ERRNO)
        self.assertIn("[REC Lamp]", rej.reason)

    def test_46_73c_rec_lamp_3_physical_leds_and_rear_top_coupling(self) -> None:
        all_on = p337.simulate_rec_lamp_emph_rec_remain_shoot_auto_review_hil(
            rec_lamp_mode="All On",
            recording_active=True,
        )
        self.assertTrue(all_on.admitted)
        self.assertTrue(all_on.front_tally_led_on)
        self.assertTrue(all_on.rear_tally_led_on)
        self.assertTrue(all_on.top_rec_button_ring_led_on)
        self.assertTrue(all_on.rear_top_rec_hardware_coupled)

        front_off = p337.simulate_rec_lamp_emph_rec_remain_shoot_auto_review_hil(
            rec_lamp_mode="Only Front Off",
            recording_active=True,
        )
        self.assertTrue(front_off.admitted)
        self.assertFalse(front_off.front_tally_led_on)
        self.assertTrue(front_off.rear_tally_led_on)
        self.assertTrue(front_off.top_rec_button_ring_led_on)

        all_off = p337.simulate_rec_lamp_emph_rec_remain_shoot_auto_review_hil(
            rec_lamp_mode="All Off",
            recording_active=True,
        )
        self.assertTrue(all_off.admitted)
        self.assertFalse(all_off.front_tally_led_on)
        self.assertFalse(all_off.rear_tally_led_on)
        self.assertFalse(all_off.top_rec_button_ring_led_on)

    def test_47_73c_dormant_only_rear_on_rejected_eopnotsupp(self) -> None:
        rej = p337.simulate_rec_lamp_emph_rec_remain_shoot_auto_review_hil(
            rec_lamp_mode="Only Rear On"
        )
        self.assertFalse(rej.admitted)
        self.assertEqual(rej.errno_code, p337.EOPNOTSUPP_ERRNO)
        self.assertIn("REC_LAMP_LIGHT_UP_ONLY_ONE", rej.reason)

    def test_48_73c_silent_mode_leaves_rec_lamp_untouched(self) -> None:
        res = p337.simulate_rec_lamp_emph_rec_remain_shoot_auto_review_hil(
            rec_lamp_mode="All On",
            silent_mode="On",
            recording_active=True,
        )
        self.assertTrue(res.admitted)
        self.assertTrue(res.silent_mode_leaves_rec_lamp_untouched)
        self.assertTrue(res.front_tally_led_on)
        self.assertTrue(res.rear_tally_led_on)
        self.assertTrue(res.top_rec_button_ring_led_on)

    def test_49_73c_reset_vs_initialize_across_rec_lamp_emph_remain_and_review(self) -> None:
        # After Reset: REC Lamp, Remain Shoot, Auto Review persist; Emphasized REC resets -> On
        after_reset = p337.simulate_rec_lamp_emph_rec_remain_shoot_auto_review_hil(
            shoot_mode=p337.SHOOT_MODE_STILL,
            recording_active=False,
            rec_lamp_mode="All Off",
            emphasized_rec_display="Off",
            remain_shoot_display="Always Display",
            auto_review="10 Sec",
            camera_settings_reset_applied=True,
        )
        self.assertTrue(after_reset.admitted)
        self.assertEqual(after_reset.effective_rec_lamp_mode, "All Off")
        self.assertFalse(after_reset.rec_lamp_resettable)
        self.assertEqual(after_reset.effective_emphasized_rec_display, "On")
        self.assertTrue(after_reset.emphasized_rec_resettable)
        self.assertEqual(after_reset.effective_remain_shoot_display, "Always Display")
        self.assertFalse(after_reset.remain_shoot_resettable)
        self.assertEqual(after_reset.effective_auto_review, "10 Sec")
        self.assertFalse(after_reset.auto_review_resettable)

        # After Initialize: all reset to defaults
        after_init = p337.simulate_rec_lamp_emph_rec_remain_shoot_auto_review_hil(
            shoot_mode=p337.SHOOT_MODE_STILL,
            recording_active=False,
            rec_lamp_mode="All Off",
            emphasized_rec_display="Off",
            remain_shoot_display="Always Display",
            auto_review="10 Sec",
            initialize_applied=True,
        )
        self.assertTrue(after_init.admitted)
        self.assertEqual(after_init.effective_rec_lamp_mode, "All On")
        self.assertEqual(after_init.effective_emphasized_rec_display, "On")
        self.assertEqual(after_init.effective_remain_shoot_display, "Not Displayed")
        self.assertEqual(after_init.effective_auto_review, "Off")

    def test_50_73c_emphasized_rec_hdmi_clean_feed_gating(self) -> None:
        clean = p337.simulate_rec_lamp_emph_rec_remain_shoot_auto_review_hil(
            emphasized_rec_display="On",
            hdmi_info_display="Off",
            recording_active=True,
        )
        self.assertTrue(clean.lcd_emph_rec_rendered)
        self.assertFalse(clean.hdmi_emph_rec_rendered)
        self.assertEqual(clean.hdmi_emph_rec_leaked_pixels, 0)

        with_osd = p337.simulate_rec_lamp_emph_rec_remain_shoot_auto_review_hil(
            emphasized_rec_display="On",
            hdmi_info_display="On",
            raw_output="Off",
            rec_media_dur_hdmi="On",
            recording_active=True,
        )
        self.assertTrue(with_osd.lcd_emph_rec_rendered)
        self.assertTrue(with_osd.hdmi_emph_rec_rendered)

        raw_clean = p337.simulate_rec_lamp_emph_rec_remain_shoot_auto_review_hil(
            emphasized_rec_display="On",
            hdmi_info_display="On",
            raw_output="On",
            recording_active=True,
        )
        self.assertFalse(raw_clean.hdmi_emph_rec_rendered)

    def test_51_73c_remain_shoot_display_active_all_3_options(self) -> None:
        for opt in p337.VALID_REMAIN_SHOOT_DISPLAY_MODES:
            r = p337.simulate_rec_lamp_emph_rec_remain_shoot_auto_review_hil(
                shoot_mode=p337.SHOOT_MODE_STILL,
                remain_shoot_display=opt,
            )
            self.assertTrue(r.admitted, opt)
            self.assertTrue(r.remain_shoot_active_on_fx3)
            self.assertEqual(r.effective_remain_shoot_display, opt)

    def test_52_73c_still_auto_review_options_and_magnify_support(self) -> None:
        for opt in p337.VALID_AUTO_REVIEW_MODES:
            r = p337.simulate_rec_lamp_emph_rec_remain_shoot_auto_review_hil(
                shoot_mode=p337.SHOOT_MODE_STILL,
                auto_review=opt,
            )
            self.assertTrue(r.admitted, opt)
            self.assertEqual(r.effective_auto_review, opt)
            self.assertTrue(r.auto_review_magnify_supported)

    def test_53_73c_auto_review_disabled_in_interval_shoot(self) -> None:
        rej = p337.simulate_rec_lamp_emph_rec_remain_shoot_auto_review_hil(
            shoot_mode=p337.SHOOT_MODE_STILL,
            auto_review="5 Sec",
            interval_shoot=True,
        )
        self.assertFalse(rej.admitted)
        self.assertEqual(rej.errno_code, p337.EOPNOTSUPP_ERRNO)
        self.assertFalse(rej.auto_review_magnify_supported)

        off_ok = p337.simulate_rec_lamp_emph_rec_remain_shoot_auto_review_hil(
            shoot_mode=p337.SHOOT_MODE_STILL,
            auto_review="Off",
            interval_shoot=True,
        )
        self.assertTrue(off_ok.admitted)

    def test_54_73c_movie_and_sq_auto_review_inactive(self) -> None:
        for m in (p337.SHOOT_MODE_MOVIE, p337.SHOOT_MODE_SQ):
            r = p337.simulate_rec_lamp_emph_rec_remain_shoot_auto_review_hil(
                shoot_mode=m,
                auto_review="2 Sec",
            )
            self.assertTrue(r.admitted, m)
            self.assertEqual(r.effective_auto_review, "Off")
            self.assertFalse(r.auto_review_magnify_supported)

    def test_55_73c_standby_keeps_rec_lamp_and_emph_rec_off(self) -> None:
        r = p337.simulate_rec_lamp_emph_rec_remain_shoot_auto_review_hil(
            recording_active=False,
            rec_lamp_mode="All On",
            emphasized_rec_display="On",
        )
        self.assertTrue(r.admitted)
        self.assertFalse(r.front_tally_led_on)
        self.assertFalse(r.rear_tally_led_on)
        self.assertFalse(r.top_rec_button_ring_led_on)
        self.assertFalse(r.lcd_emph_rec_rendered)

    def test_56_73c_fx6_independent_front_rear_and_green_yellow_tally(self) -> None:
        fx6 = p337.simulate_rec_lamp_emph_rec_remain_shoot_auto_review_hil(
            body_profile=p337.BODY_MODEL_FX6,
            recording_active=True,
            fx6_front_tally="Off",
            fx6_rear_tally="On",
            fx6_g_tally="On",
            fx6_y_tally="Off",
        )
        self.assertTrue(fx6.admitted)
        self.assertTrue(fx6.fx6_independent_front_rear_tally)
        self.assertTrue(fx6.fx6_green_yellow_tally_supported)
        self.assertFalse(fx6.front_tally_led_on)
        self.assertTrue(fx6.rear_tally_led_on)
        self.assertFalse(fx6.rear_top_rec_hardware_coupled)

    def test_57_73c_fx3_has_no_independent_front_rear_or_g_y_tally(self) -> None:
        fx3 = p337.simulate_rec_lamp_emph_rec_remain_shoot_auto_review_hil()
        self.assertFalse(fx3.fx6_independent_front_rear_tally)
        self.assertFalse(fx3.fx6_green_yellow_tally_supported)

    def test_58_73c_invalid_inputs_raise_stage73_error(self) -> None:
        for bad_kwargs in (
            dict(body_profile="FX1"),
            dict(shoot_mode="Panorama"),
            dict(rec_lamp_mode="Only Top On"),
            dict(silent_mode="Auto"),
            dict(emphasized_rec_display="Blink"),
            dict(remain_shoot_display="HalfPress"),
            dict(auto_review="1 Sec"),
        ):
            with self.assertRaises(p337.Stage73Phase337Error, msg=str(bad_kwargs)):
                p337.simulate_rec_lamp_emph_rec_remain_shoot_auto_review_hil(**bad_kwargs)

    # ------------------------------------------------------------------
    # Sub-Model 73D: Anti-flicker, Dormant Var. Shutter / FX6 ECS, APS-C S35 (59..74)
    # ------------------------------------------------------------------

    def test_59_73d_dormant_var_shutter_strictly_rejected_eopnotsupp(self) -> None:
        for mode in p337.VALID_SHOOT_MODES:
            rej = p337.simulate_antiflicker_dormant_varshutter_and_apsc_4k_lockout_hil(
                shoot_mode=mode,
                var_shutter_requested=True,
            )
            self.assertFalse(rej.admitted, mode)
            self.assertEqual(rej.errno_code, p337.EOPNOTSUPP_ERRNO)
            self.assertFalse(rej.var_shutter_exposed)
            self.assertIn("high_res_ss", rej.reason)

    def test_60_73d_antiflicker_still_mechanical_on_and_resettable(self) -> None:
        ok = p337.simulate_antiflicker_dormant_varshutter_and_apsc_4k_lockout_hil(
            shoot_mode=p337.SHOOT_MODE_STILL,
            antiflicker_shoot="On",
            shutter_type="Mechanical",
            silent_mode="Off",
            bulb_active=False,
        )
        self.assertTrue(ok.admitted)
        self.assertEqual(ok.effective_antiflicker_shoot, "On")
        self.assertTrue(ok.antiflicker_resettable)
        self.assertEqual(ok.antiflicker_supported_hz, (100, 120))

        reset = p337.simulate_antiflicker_dormant_varshutter_and_apsc_4k_lockout_hil(
            shoot_mode=p337.SHOOT_MODE_STILL,
            antiflicker_shoot="On",
            camera_settings_reset_applied=True,
        )
        self.assertTrue(reset.admitted)
        self.assertEqual(reset.effective_antiflicker_shoot, "Off")

    def test_61_73d_antiflicker_blocked_in_eshutter_silent_bulb_movie_sq(self) -> None:
        for kwargs in (
            dict(shoot_mode=p337.SHOOT_MODE_STILL, antiflicker_shoot="On", shutter_type="Electronic"),
            dict(shoot_mode=p337.SHOOT_MODE_STILL, antiflicker_shoot="On", silent_mode="On"),
            dict(shoot_mode=p337.SHOOT_MODE_STILL, antiflicker_shoot="On", bulb_active=True),
            dict(shoot_mode=p337.SHOOT_MODE_MOVIE, antiflicker_shoot="On"),
            dict(shoot_mode=p337.SHOOT_MODE_SQ, antiflicker_shoot="On"),
        ):
            rej = p337.simulate_antiflicker_dormant_varshutter_and_apsc_4k_lockout_hil(**kwargs)
            self.assertFalse(rej.admitted, str(kwargs))
            self.assertEqual(rej.errno_code, p337.EOPNOTSUPP_ERRNO)

    def test_62_73d_fx6_ecs_range_defaults_and_out_of_range_einval(self) -> None:
        for fps_key, exp_hz in p337.FX6_ECS_DEFAULT_HZ_BY_FPS.items():
            ok = p337.simulate_antiflicker_dormant_varshutter_and_apsc_4k_lockout_hil(
                body_profile=p337.BODY_MODEL_FX6,
                fx6_shutter_mode="ECS",
                fx6_project_fps=fps_key,
            )
            self.assertTrue(ok.admitted, fps_key)
            self.assertEqual(ok.fx6_ecs_frequency_hz, exp_hz)

        custom_hi = p337.simulate_antiflicker_dormant_varshutter_and_apsc_4k_lockout_hil(
            body_profile=p337.BODY_MODEL_FX6,
            fx6_shutter_mode="ECS",
            fx6_ecs_frequency_hz=8000.0,
        )
        self.assertTrue(custom_hi.admitted)

        for bad_hz in (23.98, 8000.01):
            rej = p337.simulate_antiflicker_dormant_varshutter_and_apsc_4k_lockout_hil(
                body_profile=p337.BODY_MODEL_FX6,
                fx6_shutter_mode="ECS",
                fx6_ecs_frequency_hz=bad_hz,
            )
            self.assertFalse(rej.admitted, bad_hz)
            self.assertEqual(rej.errno_code, p337.EINVAL_ERRNO)

    def test_63_73d_wave42_errata_fix_apsc_s35_survives_reset_resets_only_on_initialize(self) -> None:
        after_reset = p337.simulate_antiflicker_dormant_varshutter_and_apsc_4k_lockout_hil(
            shoot_mode=p337.SHOOT_MODE_MOVIE,
            apsc_s35_mode="On",
            video_format="XAVC S HD",
            camera_settings_reset_applied=True,
        )
        self.assertTrue(after_reset.admitted)
        self.assertFalse(after_reset.apsc_s35_resettable)
        self.assertEqual(after_reset.effective_apsc_s35_mode, "On")
        self.assertTrue(after_reset.apsc_s35_crop_active)

        after_init = p337.simulate_antiflicker_dormant_varshutter_and_apsc_4k_lockout_hil(
            shoot_mode=p337.SHOOT_MODE_MOVIE,
            apsc_s35_mode="On",
            video_format="XAVC S HD",
            initialize_applied=True,
        )
        self.assertTrue(after_init.admitted)
        self.assertEqual(after_init.effective_apsc_s35_mode, "Auto")
        self.assertFalse(after_init.apsc_s35_crop_active)

    def test_64_73d_apsc_s35_locks_out_all_5_4k_video_formats(self) -> None:
        for fmt in p337.FX3_4K_VIDEO_FORMATS:
            mode = p337.SHOOT_MODE_SQ if fmt == "S&Q 4K" else p337.SHOOT_MODE_MOVIE
            rej = p337.simulate_antiflicker_dormant_varshutter_and_apsc_4k_lockout_hil(
                shoot_mode=mode,
                apsc_s35_mode="On",
                video_format=fmt,
            )
            self.assertFalse(rej.admitted, fmt)
            self.assertEqual(rej.errno_code, p337.EOPNOTSUPP_ERRNO)
            self.assertEqual(rej.max_video_resolution, "1920x1080")

    def test_65_73d_apsc_s35_auto_with_s35_lens_also_locks_out_4k(self) -> None:
        rej = p337.simulate_antiflicker_dormant_varshutter_and_apsc_4k_lockout_hil(
            shoot_mode=p337.SHOOT_MODE_MOVIE,
            apsc_s35_mode="Auto",
            s35_lens_mounted=True,
            video_format="XAVC S 4K",
        )
        self.assertFalse(rej.admitted)
        self.assertEqual(rej.errno_code, p337.EOPNOTSUPP_ERRNO)
        self.assertTrue(rej.apsc_s35_crop_active)

    def test_66_73d_apsc_s35_locks_hdmi_4k_raw_auto_framing_and_sq_200_240fps(self) -> None:
        for kwargs in (
            dict(shoot_mode=p337.SHOOT_MODE_MOVIE, apsc_s35_mode="On", video_format="XAVC S HD", four_k_hdmi_only_requested=True),
            dict(shoot_mode=p337.SHOOT_MODE_MOVIE, apsc_s35_mode="On", video_format="XAVC S HD", raw_output="On"),
            dict(shoot_mode=p337.SHOOT_MODE_MOVIE, apsc_s35_mode="On", video_format="XAVC S HD", auto_framing=True),
            dict(shoot_mode=p337.SHOOT_MODE_SQ, apsc_s35_mode="On", video_format="XAVC S-I HD", fps=200.0),
            dict(shoot_mode=p337.SHOOT_MODE_SQ, apsc_s35_mode="On", video_format="XAVC S-I HD", fps=240.0),
        ):
            rej = p337.simulate_antiflicker_dormant_varshutter_and_apsc_4k_lockout_hil(**kwargs)
            self.assertFalse(rej.admitted, str(kwargs))
            self.assertEqual(rej.errno_code, p337.EOPNOTSUPP_ERRNO)

    def test_67_73d_apsc_s35_allows_hd_1920x1080_up_to_120p(self) -> None:
        for fmt in p337.FX3_HD_VIDEO_FORMATS:
            for fps_val in (23.98, 59.94, 100.0, 119.88):
                ok = p337.simulate_antiflicker_dormant_varshutter_and_apsc_4k_lockout_hil(
                    shoot_mode=p337.SHOOT_MODE_MOVIE,
                    apsc_s35_mode="On",
                    video_format=fmt,
                    fps=fps_val,
                )
                self.assertTrue(ok.admitted, (fmt, fps_val))
                self.assertEqual(ok.max_video_resolution, "1920x1080")
                self.assertEqual(ok.max_regular_fps, 120)

    def test_68_73d_still_apsc_downgrades_l_12m_to_m_5_1m_and_all_aspect_ratios(self) -> None:
        for ratio, (exp_lbl, exp_dims, exp_mp) in p337.APSC_STILL_M_PIXEL_MAP.items():
            ok = p337.simulate_antiflicker_dormant_varshutter_and_apsc_4k_lockout_hil(
                shoot_mode=p337.SHOOT_MODE_STILL,
                apsc_s35_mode="On",
                still_aspect_ratio=ratio,
                still_image_size_requested="L",
                allow_auto_still_downgrade=True,
            )
            self.assertTrue(ok.admitted, ratio)
            self.assertTrue(ok.downgraded_from_L_to_M)
            self.assertEqual(ok.effective_still_image_size_label, exp_lbl)
            self.assertEqual(ok.effective_still_dimensions, exp_dims)
            self.assertEqual(ok.effective_still_megapixels, exp_mp)

            strict_rej = p337.simulate_antiflicker_dormant_varshutter_and_apsc_4k_lockout_hil(
                shoot_mode=p337.SHOOT_MODE_STILL,
                apsc_s35_mode="On",
                still_aspect_ratio=ratio,
                still_image_size_requested="L",
                allow_auto_still_downgrade=False,
            )
            self.assertFalse(strict_rej.admitted, ratio)
            self.assertEqual(strict_rej.errno_code, p337.EOPNOTSUPP_ERRNO)
            self.assertEqual(strict_rej.effective_still_image_size_label, exp_lbl)

    def test_69_73d_still_fullframe_retains_l_12m_4240x2832(self) -> None:
        ff = p337.simulate_antiflicker_dormant_varshutter_and_apsc_4k_lockout_hil(
            shoot_mode=p337.SHOOT_MODE_STILL,
            apsc_s35_mode="Off",
            still_aspect_ratio="3:2",
            still_image_size_requested="L",
        )
        self.assertTrue(ff.admitted)
        self.assertFalse(ff.downgraded_from_L_to_M)
        self.assertEqual(ff.effective_still_image_size_label, "L: 12M")
        self.assertEqual(ff.effective_still_dimensions, "4240x2832")
        self.assertEqual(ff.effective_still_megapixels, 12.1)

    def test_70_73d_fx6_imager_scan_mode_s35_locks_1080p_and_blocks_4k_raw(self) -> None:
        s35_hd = p337.simulate_antiflicker_dormant_varshutter_and_apsc_4k_lockout_hil(
            body_profile=p337.BODY_MODEL_FX6,
            fx6_imager_scan_mode="S35",
            video_format="XAVC S-I HD",
        )
        self.assertTrue(s35_hd.admitted)
        self.assertEqual(s35_hd.max_video_resolution, "1920x1080")
        self.assertEqual(s35_hd.fx6_ciz_max_4k_ratio, 1.5)

        s35_4k = p337.simulate_antiflicker_dormant_varshutter_and_apsc_4k_lockout_hil(
            body_profile=p337.BODY_MODEL_FX6,
            fx6_imager_scan_mode="S35",
            video_format="XAVC S-I 4K",
        )
        self.assertFalse(s35_4k.admitted)
        self.assertEqual(s35_4k.errno_code, p337.EOPNOTSUPP_ERRNO)

        s35_raw = p337.simulate_antiflicker_dormant_varshutter_and_apsc_4k_lockout_hil(
            body_profile=p337.BODY_MODEL_FX6,
            fx6_imager_scan_mode="S35",
            video_format="XAVC S-I HD",
            raw_output="On",
        )
        self.assertFalse(s35_raw.admitted)
        self.assertEqual(s35_raw.errno_code, p337.EOPNOTSUPP_ERRNO)

    def test_71_73d_still_apsc_s_size_yields_2_0m(self) -> None:
        s_sz = p337.simulate_antiflicker_dormant_varshutter_and_apsc_4k_lockout_hil(
            shoot_mode=p337.SHOOT_MODE_STILL,
            apsc_s35_mode="On",
            still_image_size_requested="S",
        )
        self.assertTrue(s_sz.admitted)
        self.assertEqual(s_sz.effective_still_image_size_label, "S: 2.0M")
        self.assertEqual(s_sz.effective_still_dimensions, "1744x1160")

    def test_72_73d_apsc_off_permits_4k_and_dci_4k_and_raw(self) -> None:
        for fmt in p337.FX3_4K_VIDEO_FORMATS:
            mode = p337.SHOOT_MODE_SQ if fmt == "S&Q 4K" else p337.SHOOT_MODE_MOVIE
            ok = p337.simulate_antiflicker_dormant_varshutter_and_apsc_4k_lockout_hil(
                shoot_mode=mode,
                apsc_s35_mode="Off",
                video_format=fmt,
            )
            self.assertTrue(ok.admitted, fmt)
            self.assertEqual(ok.max_video_resolution, "4096x2160")

    def test_73_73d_fx6_shutter_speed_and_angle_modes_admitted(self) -> None:
        for sm in ("Speed", "Angle"):
            r = p337.simulate_antiflicker_dormant_varshutter_and_apsc_4k_lockout_hil(
                body_profile=p337.BODY_MODEL_FX6,
                fx6_shutter_mode=sm,
            )
            self.assertTrue(r.admitted, sm)
            self.assertEqual(r.fx6_shutter_mode, sm)

    def test_74_73d_invalid_inputs_raise_stage73_error(self) -> None:
        for bad_kwargs in (
            dict(body_profile="FX2"),
            dict(shoot_mode="Burst"),
            dict(antiflicker_shoot="Auto"),
            dict(shutter_type="Global"),
            dict(silent_mode="Always"),
            dict(apsc_s35_mode="Manual"),
            dict(video_format="X-OCN 8K"),
            dict(raw_output="Auto"),
            dict(still_aspect_ratio="21:9"),
            dict(still_image_size_requested="XL"),
            dict(fx6_imager_scan_mode="S16"),
            dict(fx6_shutter_mode="VarShutter"),
            dict(fx6_project_fps="120p"),
        ):
            with self.assertRaises(p337.Stage73Phase337Error, msg=str(bad_kwargs)):
                p337.simulate_antiflicker_dormant_varshutter_and_apsc_4k_lockout_hil(**bad_kwargs)

    # ------------------------------------------------------------------
    # Milestone, Determinism, CLI & Suite Stage 73 Wiring (Tests 75..96)
    # ------------------------------------------------------------------

    def test_75_milestone_probe_exact_fields(self) -> None:
        probe = p337._build_stage73_milestone_probe()
        self.assertEqual(probe["phase_number"], 337)
        self.assertEqual(probe["stage_index"], 73)
        self.assertEqual(probe["stage_total"], 73)
        self.assertEqual(probe["milestone"], "73/73")
        self.assertTrue(probe["is_73rd_stage_milestone"])
        self.assertEqual(probe["wave"], "Wave-63")
        self.assertEqual(probe["fx3_target_version"], "Ver. 7.02")
        self.assertEqual(probe["fx6_comparison_version"], "Ver. 6.01")

    def test_76_pillar_results_all_passed_in_clean_room(self) -> None:
        rep = p337.run_phase337_hdmi_raw_desqueeze_reclamp_varshutter_apsc_coemulation(
            force_clean_room=True
        )
        for pillar_key in (
            "pillar_a_hdmi_raw_4264_reclamp_and_slot1_hil",
            "pillar_b_desqueeze_165x_4locks_and_6bypasses_hil",
            "pillar_c_rec_lamp_emph_rec_remain_shoot_auto_review_hil",
            "pillar_d_antiflicker_dormant_varshutter_ecs_and_apsc_s35_hil",
        ):
            self.assertTrue(rep[pillar_key]["passed"], pillar_key)

    def test_77_deterministic_digest_identical_across_repeated_clean_room_runs(self) -> None:
        rep1 = p337.run_phase337_hdmi_raw_desqueeze_reclamp_varshutter_apsc_coemulation(
            force_clean_room=True
        )
        rep2 = p337.run_phase337_hdmi_raw_desqueeze_reclamp_varshutter_apsc_coemulation(
            force_clean_room=True
        )
        self.assertEqual(rep1["audit_digest_sha256"], rep2["audit_digest_sha256"])

    def test_78_deterministic_suite_digest_identical_across_repeated_fast_runs(self) -> None:
        cfg = suite.CoEmulationConfig(**_fast_suite_kwargs())
        r1 = suite.run_fx3_vm_coemulation_suite(cfg)
        r2 = suite.run_fx3_vm_coemulation_suite(cfg)
        self.assertEqual(r1["audit_digest_sha256"], r2["audit_digest_sha256"])

    def test_79_stage73_wrapper_output_schema_matches_suite_contract(self) -> None:
        s73 = suite.run_stage73_realhw_hdmi_raw_desqueeze_reclamp_varshutter_apsc_hil(
            suite.CoEmulationConfig(force_clean_room=True)
        )
        self.assertEqual(
            s73["stage"],
            "stage73_realhw_hdmi_raw_desqueeze_reclamp_varshutter_apsc_hil",
        )
        self.assertEqual(s73["schema"], p337.SCHEMA_ID)
        self.assertEqual(s73["phase_number"], 337)
        self.assertEqual(s73["milestone"], "73/73")
        self.assertTrue(s73["is_73rd_stage_milestone"])
        self.assertTrue(s73["all_checks_passed"])
        self.assertEqual(len(s73["phase337_audit_digest_sha256"]), 64)

    def test_80_standalone_cli_help_uses_sys_executable_and_percent_escaping(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                str(
                    FX3_VM_DIR
                    / "realhw_hdmi_raw_desqueeze_reclamp_varshutter_apsc_coemulator.py"
                ),
                "--help",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("100%", proc.stdout)
        self.assertIn("73/73", proc.stdout)

    def test_81_suite_cli_help_percent_escaping_and_stage73_flags(self) -> None:
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
        self.assertIn("73/73 Milestone", proc.stdout)
        self.assertIn("--include-stage73", proc.stdout)
        self.assertIn("--skip-stage73", proc.stdout)
        self.assertIn("--no-include-stage73", proc.stdout)
        self.assertIn("--skip-phase337", proc.stdout)

    def test_82_standalone_cli_summary_and_json_modes(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = p337.main(["--self-test", "--clean-room", "--summary"])
        self.assertEqual(rc, 0)
        self.assertIn("[PASS] Phase 337 Stage 73 (73/73 Milestone)", buf.getvalue())

        buf_json = io.StringIO()
        with contextlib.redirect_stdout(buf_json):
            rc2 = p337.main(["--self-test", "--clean-room", "--json"])
        self.assertEqual(rc2, 0)
        parsed = json.loads(buf_json.getvalue())
        self.assertEqual(parsed["milestone"], "73/73")
        self.assertTrue(parsed["is_73rd_stage_milestone"])
        self.assertTrue(parsed["all_checks_passed"])
        self.assertNotIn("\\x7fELF", buf_json.getvalue())

    def test_83_no_hardcoded_usr_bin_python3_in_stage73_files(self) -> None:
        mod_src = (
            FX3_VM_DIR
            / "realhw_hdmi_raw_desqueeze_reclamp_varshutter_apsc_coemulator.py"
        ).read_text(encoding="utf-8")
        tst_src = Path(__file__).read_text(encoding="utf-8")
        forbidden = "/usr/bin/" + "python3"
        self.assertNotIn(forbidden, mod_src)
        self.assertNotIn(forbidden, tst_src)

    def test_84_suite_default_config_enables_stage73_and_full_run_contains_73_stages(self) -> None:
        cfg = suite.CoEmulationConfig()
        self.assertTrue(
            cfg.include_phase337_realhw_hdmi_raw_desqueeze_reclamp_varshutter_apsc_hil
        )
        self.assertTrue(cfg.include_stage73)
        self.assertTrue(
            cfg.stage73_realhw_hdmi_raw_desqueeze_reclamp_varshutter_apsc_hil
        )

        t0 = time.monotonic()
        rep = suite.run_fx3_vm_coemulation_suite(cfg)
        elapsed = time.monotonic() - t0
        self.assertTrue(rep["all_checks_passed"])
        stage_keys = [k for k in rep if re.match(r"^stage\d+_", k)]
        self.assertGreaterEqual(len(stage_keys), 73)
        s73 = rep["stage73_realhw_hdmi_raw_desqueeze_reclamp_varshutter_apsc_hil"]
        self.assertTrue(s73["all_checks_passed"])
        self.assertTrue(s73["is_73rd_stage_milestone"])
        self.assertEqual(s73["milestone"], "73/73")
        self.assertEqual(s73["phase_number"], 337)
        max_elapsed = 30.0 if IS_CI else 15.0
        self.assertLess(elapsed, max_elapsed)

    def test_85_suite_skip_flags_and_summary_cli_for_stage73(self) -> None:
        for flag in ("--skip-stage73", "--no-include-stage73", "--skip-phase337"):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = suite.main([*_FAST_CLI_FLAGS, flag, "--json"])
            self.assertEqual(rc, 0)
            data = json.loads(buf.getvalue())
            self.assertNotIn(
                "stage73_realhw_hdmi_raw_desqueeze_reclamp_varshutter_apsc_hil",
                data,
            )
            self.assertFalse(data["config"]["include_stage73"])

        buf_sum = io.StringIO()
        with contextlib.redirect_stdout(buf_sum):
            rc_sum = suite.main([*_FAST_CLI_FLAGS, "--include-stage73", "--summary"])
        self.assertEqual(rc_sum, 0)
        self.assertIn(
            "realhw_hdmi_raw_desqueeze_reclamp_varshutter_apsc_hil=CLEAN_ROOM_SYNTHETIC("
            "m73=73/73,hdmi=8,raw=4264x2408@16b,desq=5(1.65x),lamp=3/3,varsh=0,apsc_mp=5.1,"
            "s1_wr=0,emmc_wr=0)",
            buf_sum.getvalue(),
        )

    def test_86_suite_tamper_73a_hdmi_raw_redlines_detected(self) -> None:
        for attr, val in (
            ("FX3_ACTIVE_HDMI_OUTPUT_SETTINGS_ITEMS", 9),
            ("HDMI_COLOR_GAMUT_FOR_RAW_OUT_REMOVED_V2", False),
            ("HDMI_RAW_WIDTH", 4240),
            ("HDMI_RAW_HEIGHT", 2392),
            ("HDMI_RAW_BIT_DEPTH", 12),
            ("DORMANT_COLOR_GAMUT_RAW_OUT_EXPOSED_EVENTS", 1),
            ("HDMI_ONLY_CARD_WRITE_LEAK_EVENTS", 1),
            ("REC_MEDIA_ON_SLOT1_EROFS_BYPASS_EVENTS", 1),
            ("REC_CONTROL_WITHOUT_TC_BYPASS_EVENTS", 1),
        ):
            with unittest.mock.patch.object(p337, attr, val):
                rep = suite.run_fx3_vm_coemulation_suite(
                    suite.CoEmulationConfig(**_fast_suite_kwargs())
                )
                self.assertFalse(rep["all_checks_passed"], attr)

    def test_87_suite_tamper_73b_desqueeze_redlines_detected(self) -> None:
        for attr, val in (
            ("FX3_DESQUEEZE_ACTIVE_OPTIONS_COUNT", 6),
            ("FX3_DESQUEEZE_1_6X_ACTUAL_FACTOR", 1.6),
            ("DESQUEEZE_1_8X_EXPOSED_EVENTS", 1),
            ("FX3_DESQUEEZE_FORCED_LOCKOUT_COUNT", 3),
            ("DESQUEEZE_4LOCK_BYPASS_EVENTS", 1),
            ("DESQUEEZE_INBODY_STREAM_MUTATION_EVENTS", 1),
            ("FX6_SDI_DESQUEEZE_LEAK_EVENTS", 1),
        ):
            with unittest.mock.patch.object(p337, attr, val):
                rep = suite.run_fx3_vm_coemulation_suite(
                    suite.CoEmulationConfig(**_fast_suite_kwargs())
                )
                self.assertFalse(rep["all_checks_passed"], attr)

    def test_88_suite_tamper_73c_rec_lamp_emph_rec_redlines_detected(self) -> None:
        for attr, val in (
            ("FX3_REC_LAMP_PHYSICAL_LED_COUNT", 2),
            ("FX3_REC_LAMP_ACTIVE_STATES_COUNT", 4),
            ("DORMANT_TALLY_LIGHT_MENU_EXPOSED_EVENTS", 1),
            ("DORMANT_REC_LAMP_SINGLE_REAR_EXPOSED_EVENTS", 1),
            ("SILENT_MODE_REC_LAMP_AUTO_OFF_VIOLATIONS", 1),
            ("EMPH_REC_CLEAN_HDMI_LEAKED_PIXELS", 1),
        ):
            with unittest.mock.patch.object(p337, attr, val):
                rep = suite.run_fx3_vm_coemulation_suite(
                    suite.CoEmulationConfig(**_fast_suite_kwargs())
                )
                self.assertFalse(rep["all_checks_passed"], attr)

    def test_89_suite_tamper_73d_var_shutter_antiflicker_apsc_redlines_detected(self) -> None:
        for attr, val in (
            ("DORMANT_VAR_SHUTTER_EXPOSED_EVENTS", 1),
            ("ANTIFLICKER_SILENT_OR_ESHUTTER_BYPASS_EVENTS", 1),
            ("APSC_S35_CAMERA_RESET_WIPE_EVENTS", 1),
            ("APSC_S35_4K_OR_DCI4K_BYPASS_EVENTS", 1),
            ("STILL_APSC_L_12M_BYPASS_EVENTS", 1),
            ("FX3_STILL_APSC_32_EFFECTIVE_MP", 4.2),
        ):
            with unittest.mock.patch.object(p337, attr, val):
                rep = suite.run_fx3_vm_coemulation_suite(
                    suite.CoEmulationConfig(**_fast_suite_kwargs())
                )
                self.assertFalse(rep["all_checks_passed"], attr)

    def test_90_suite_tamper_hard_write_and_rf_redlines_detected(self) -> None:
        for attr, val in (
            ("PERSISTENT_EMMC_WRITES_AUTHORIZED", True),
            ("EMMC_WRITES_AUTHORIZED", True),
            ("CROSS_MODEL_FLASH_AUTHORIZED", True),
            ("HARDWARE_LIVE_ATTACHMENT_AUTHORIZED", True),
            ("PHYSICAL_DEVICE_WRITES", 1),
            ("EMMC_NFLASHA_WRITE_COUNT", 1),
            ("SLOT1_DATA_SECTOR_WRITES", 1),
            ("SLOT1_AVF_INFO_MUTATED", True),
            ("RF_PACKETS_TRANSMITTED", 1),
            ("RF_NVS_MUTATION_BYTES", 16),
            ("RAW_FIRMWARE_BYTES_LEAKED", 4),
        ):
            with unittest.mock.patch.object(p337, attr, val):
                rep = suite.run_fx3_vm_coemulation_suite(
                    suite.CoEmulationConfig(**_fast_suite_kwargs())
                )
                self.assertFalse(rep["all_checks_passed"], attr)

    def test_91_suite_tamper_runtime_fault_redlines_detected(self) -> None:
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
            ("NULL_GPIO_DEREFS", 1),
            ("MAILBOX_STALLS", 1),
            ("STOCK_CP_FAULT_COUNT", 1),
        ):
            with unittest.mock.patch.object(p337, attr, val):
                rep = suite.run_fx3_vm_coemulation_suite(
                    suite.CoEmulationConfig(**_fast_suite_kwargs())
                )
                self.assertFalse(rep["all_checks_passed"], attr)

    def test_92_stage73_all_redline_zero_keys_verified(self) -> None:
        rep = p337.run_phase337_hdmi_raw_desqueeze_reclamp_varshutter_apsc_coemulation(
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
            "dormant_color_gamut_raw_out_exposed_events",
            "hdmi_only_card_write_leak_events",
            "rec_media_on_slot1_erofs_bypass_events",
            "rec_control_without_tc_bypass_events",
            "desqueeze_1_8x_exposed_events",
            "desqueeze_4lock_bypass_events",
            "desqueeze_inbody_stream_mutation_events",
            "fx6_sdi_desqueeze_leak_events",
            "dormant_tally_light_menu_exposed_events",
            "dormant_rec_lamp_single_rear_exposed_events",
            "silent_mode_rec_lamp_auto_off_violations",
            "emph_rec_clean_hdmi_leaked_pixels",
            "dormant_var_shutter_exposed_events",
            "antiflicker_silent_or_eshutter_bypass_events",
            "apsc_s35_camera_reset_wipe_events",
            "apsc_s35_4k_or_dci4k_bypass_events",
            "still_apsc_l_12m_bypass_events",
            "rsv_orphan_count",
            "wf12_00342260_hits",
            "appfw_crashes",
            "null_gpio_derefs",
            "mailbox_stalls",
            "stock_cp_fault_count",
            "raw_firmware_bytes_leaked",
        ):
            self.assertEqual(red[zero_key], 0, zero_key)

    def test_93_stage73_all_false_and_true_boolean_redlines_verified(self) -> None:
        rep = p337.run_phase337_hdmi_raw_desqueeze_reclamp_varshutter_apsc_coemulation(
            force_clean_room=True
        )
        red = rep["redlines"]
        for true_key in (
            "p8_cp_mutation_forbidden",
            "cnflasha_userspace_write_blocked",
            "hdmi_color_gamut_for_raw_out_removed_v2",
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

    def test_94_suite_tamper_milestone_flag_detected(self) -> None:
        with unittest.mock.patch.object(p337, "IS_73RD_STAGE_MILESTONE", False):
            rep = suite.run_fx3_vm_coemulation_suite(
                suite.CoEmulationConfig(**_fast_suite_kwargs())
            )
            self.assertFalse(rep["all_checks_passed"])

    def test_95_clean_room_mocked_empty_env_and_local_env_parity(self) -> None:
        clean_rep = p337.run_phase337_hdmi_raw_desqueeze_reclamp_varshutter_apsc_coemulation(
            force_clean_room=True
        )
        env_rep = p337.run_phase337_hdmi_raw_desqueeze_reclamp_varshutter_apsc_coemulation(
            env={p337.ENV_FORCE_CLEAN_ROOM: "1"}
        )
        self.assertEqual(
            clean_rep["audit_digest_sha256"],
            env_rep["audit_digest_sha256"],
        )

    def test_96_all_four_env_modes_pass_cleanly_including_work_root_none(self) -> None:
        with unittest.mock.patch.object(p337, "resolve_mac_work_root", return_value=None):
            none_rep = p337.run_phase337_hdmi_raw_desqueeze_reclamp_varshutter_apsc_coemulation(
                env={}
            )
        self.assertTrue(none_rep["all_checks_passed"])
        self.assertEqual(none_rep["source_mode"], p337.SOURCE_MODE_CLEAN_ROOM)
        self.assertEqual(none_rep["redlines"]["raw_firmware_bytes_leaked"], 0)

        cr_test_rep = p337.run_phase337_hdmi_raw_desqueeze_reclamp_varshutter_apsc_coemulation(
            env={p337.ENV_CLEAN_ROOM_TEST: "1"}
        )
        self.assertTrue(cr_test_rep["all_checks_passed"])
        self.assertEqual(cr_test_rep["audit_digest_sha256"], none_rep["audit_digest_sha256"])


if __name__ == "__main__":
    unittest.main()
