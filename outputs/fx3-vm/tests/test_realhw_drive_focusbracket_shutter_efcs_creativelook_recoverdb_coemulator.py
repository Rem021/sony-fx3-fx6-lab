#!/usr/bin/env python3
"""Unit tests for Phase 346 (Stage 76 — 76/76 Full-Board VM Co-Emulation Stages!):
Real-Hardware `ILME-FX3 Ver. 7.02` vs `ILME-FX6 Ver. 6.01` Wave-66:
- 76A: `Shooting -> [Drive Mode]` (`Single Shooting`, `Cont. Shooting` `Hi+` ~10 fps /
  `Hi` 8 / `Mid` 6 / `Lo` 3, `> F11` 1st-frame AF lock, `Uncompressed RAW`/Flash burst
  drop, `Self-timer(Single)` 10/5/2s, `Self-timer(Cont)` 6 options vs dormant 10-img,
  `Cont./Single Bracket` 0.3..1.0 EV x 3/5/9 vs 2.0/3.0 EV x 3/5, `WB bracket`,
  `DRO Bracket` blocked under HLG, `[Bracket Settings]`, `[Interval Shoot Func.]`),
  all `Can be reset` & Movie/S&Q disabled, plus **100%% Dormant `[Focus Bracket]`
  (`DRIVE_MODE_FOCUS_BRACKET`) Myth-Busting** (`EOPNOTSUPP=95` on FX3 & 0 Still
  Drive Mode on FX6),
- 76B: `[Shutter Type]` 2-Option Zero-`Auto` (`Mechanical Shutter` / `Electronic Shutter`,
  reject dormant `Auto` `EOPNOTSUPP=95`), Electronic Shutter / Silent Mode 5-feature
  lockouts (`Flash`, `[Long Exposure NR]`, `[e-Front Curtain Shut.]`, `BULB`,
  `[Anti-flicker Shoot.]`), single **`1/250 s` Flash X-Sync across BOTH FF & APS-C**
  (no `1/320 s`), **Reset-Immune `[e-Front Curtain Shut.]` (`curtaion` ELF typo)**
  with bokeh clipping & Minolta shading advisories, `[Long Exposure NR]` (`>= 1 s`
  dark-frame subtraction, Cont. lock, `iAuto` On-lock), & `[High ISO NR]`
  (`Normal`/`Low`/`Off`, dormant `High` rejected, disabled on pure `RAW`, zero `.ARW`
  mutation) vs `ILME-FX6 Ver. 6.01` `Noise Suppression` & `APR > Execute`,
- 76C: `[Creative Look]` (`10` presets + `6` Custom slots, separate Still/Movie,
  `Can be reset`, exact **8** param bounds `-9..+9` vs **`0..9`** (`Fade`,
  `Sharpness`, `Clarity`) vs `1..5` (`Sharpness Range`), `BW`/`SE` locking
  `Saturation`, Movie/`S&Q` locking `Sharpness Range`, `iAuto`/`PP`/`Log`/`HLG`
  forcing `[-]` lock), plus **100%% Dormant `[Soft Skin Effect]` Myth-Busting**
  on BOTH `ILME-FX3` AND `ILME-FX6` (`EOPNOTSUPP=95`) vs FX6 `Base Look`,
- 76D: `Playback -> [Delete]` / `[Protect]` / `[Recover Image DB]` (`AVF_INFO`
  rewrite, FTP transfer status cleared, Reset & Initialize immune, `<20%%` battery
  gate) vs read-only `[Display Media Info.]` (`40,000`-still cap, `NOT_DISPLAYNG`
  typo, `0` writes), coupled main+`*S03.MP4` Proxy atomic Delete/Protect,
  Playback config Reset-immunity, fail-closed **Tier-0 `Slot 1` `EROFS=30` Firewall**,
  and `ILME-FX6` `Lock/Unlock Clip` + `Restore Media(A)/(B)` (`ng_write_protected`)
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
import realhw_drive_focusbracket_shutter_efcs_creativelook_recoverdb_coemulator as p346  # noqa: E402

IS_CI = os.environ.get("GITHUB_ACTIONS", "").lower() == "true"


def _fast_suite_kwargs(**overrides: object) -> dict:
    """Fast config skipping unrelated optional stages 4..75 for Stage 76 isolation tests."""
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
]


class TestRealHwStage76DriveFocusBracketShutterEfcsCreativeLookRecoverDb(unittest.TestCase):
    # ------------------------------------------------------------------
    # Donor Audit, Bounded O_RDONLY & 4-Mode Fallback Tests (Tests 01..14)
    # ------------------------------------------------------------------

    def test_01_milestone_constants_76_of_76(self) -> None:
        self.assertEqual(p346.PHASE_NUMBER, 346)
        self.assertEqual(p346.STAGE_INDEX, 76)
        self.assertEqual(p346.STAGE_TOTAL, 76)
        self.assertEqual(p346.MILESTONE_LABEL, "76/76")
        self.assertTrue(p346.IS_76TH_STAGE_MILESTONE)
        self.assertEqual(len(p346.DONOR_RELPATHS), 11)
        self.assertEqual(len(p346.EXPECTED_DONOR_BYTES), 11)
        self.assertEqual(len(p346.EXPECTED_COMPACT_DONOR_SHA256), 8)
        self.assertEqual(len(p346.EXPECTED_LARGE_HEAD4K_SHA256), 3)
        self.assertEqual(len(p346.LARGE_DONOR_WINDOWS), 3)

    def test_02_hard_safety_and_wave66_redlines_locked(self) -> None:
        self.assertTrue(p346.P8_CP_MUTATION_FORBIDDEN)
        self.assertTrue(p346.CNFLASHA_USERSPACE_WRITE_BLOCKED)
        self.assertFalse(p346.PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(p346.EMMC_WRITES_AUTHORIZED)
        self.assertFalse(p346.CROSS_MODEL_FLASH_AUTHORIZED)
        self.assertFalse(p346.HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        self.assertFalse(p346.OVERALL_READY_FOR_HARDWARE_ATTACH)
        self.assertFalse(p346.ISP_WRITE_AUTHORIZED)
        self.assertFalse(p346.SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(p346.EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        self.assertFalse(p346.SLOT1_AVF_INFO_MUTATED)
        self.assertEqual(p346.SLOT1_DATA_SECTOR_WRITES, 0)
        self.assertEqual(p346.EMMC_NFLASHA_WRITE_COUNT, 0)
        self.assertEqual(p346.RAW_FIRMWARE_BYTES_LEAKED, 0)
        self.assertEqual(p346.STILL_CONT_HI_PLUS_MAX_FPS, 10)
        self.assertEqual(p346.STILL_CONT_HI_MAX_FPS, 8)
        self.assertEqual(p346.STILL_CONT_MID_MAX_FPS, 6)
        self.assertEqual(p346.STILL_CONT_LO_MAX_FPS, 3)
        self.assertEqual(p346.SELF_TIMER_CONT_OPTIONS_COUNT, 6)
        self.assertEqual(p346.DORMANT_FOCUS_BRACKET_EXPOSED_EVENTS, 0)
        self.assertEqual(p346.FX6_STILL_DRIVE_MODE_EXPOSED_EVENTS, 0)
        self.assertEqual(p346.SHUTTER_TYPE_ACTIVE_OPTIONS_COUNT, 2)
        self.assertEqual(p346.DORMANT_SHUTTER_TYPE_AUTO_EXPOSED_EVENTS, 0)
        self.assertEqual(p346.FLASH_X_SYNC_MAX_SPEED_DENOM, 250)
        self.assertEqual(p346.APSC_1_320_XSYNC_SPOOF_EVENTS, 0)
        self.assertTrue(p346.E_FRONT_CURTAIN_TYPO_MATCHED)
        self.assertEqual(p346.CREATIVE_LOOK_PRESETS_COUNT, 10)
        self.assertEqual(p346.CREATIVE_LOOK_CUSTOM_SLOTS_COUNT, 6)
        self.assertEqual(p346.CREATIVE_LOOK_PARAM_COUNT, 8)
        self.assertEqual(p346.CREATIVE_LOOK_CLARITY_FADE_SHARPNESS_MAX, 9)
        self.assertEqual(p346.FX3_SOFT_SKIN_EFFECT_EXPOSED_EVENTS, 0)
        self.assertEqual(p346.FX6_SOFT_SKIN_EFFECT_EXPOSED_EVENTS, 0)
        self.assertEqual(p346.DISPLAY_MEDIA_INFO_STILL_CAP, 40_000)
        self.assertTrue(p346.NOT_DISPLAYNG_TYPO_MATCHED)

    def test_03_clean_room_test_mode_both_env_vars(self) -> None:
        self.assertFalse(p346.clean_room_test_mode(env={}))
        self.assertTrue(p346.clean_room_test_mode(env={p346.ENV_FORCE_CLEAN_ROOM: "1"}))
        self.assertTrue(p346.clean_room_test_mode(env={p346.ENV_CLEAN_ROOM_TEST: "1"}))
        self.assertTrue(p346.clean_room_test_mode(force_clean_room=True, env={}))
        self.assertFalse(
            p346.clean_room_test_mode(
                force_clean_room=False,
                env={p346.ENV_FORCE_CLEAN_ROOM: "1", p346.ENV_CLEAN_ROOM_TEST: "1"},
            )
        )

    def test_04_resolve_mac_work_root_and_donor_availability_none_fallback(self) -> None:
        self.assertIsNone(
            p346.resolve_mac_work_root(
                env={p346.ENV_MAC_WORK_ROOT: p346.CLEAN_ROOM_SENTINEL_DIRNAME}
            )
        )
        self.assertIsNone(
            p346.resolve_mac_work_root(
                env={p346.ENV_MAC_ROOT: p346.CLEAN_ROOM_SENTINEL_DIRNAME}
            )
        )
        self.assertFalse(
            p346._local_donors_available(
                env={p346.ENV_MAC_WORK_ROOT: p346.CLEAN_ROOM_SENTINEL_DIRNAME}
            )
        )
        with tempfile.TemporaryDirectory() as td:
            with unittest.mock.patch.object(p346, "DEFAULT_REPO_ROOT", Path(td)):
                with unittest.mock.patch.object(p346, "LEGACY_MAC_ROOT", Path(td) / "none"):
                    self.assertIsNone(p346.resolve_mac_work_root(env={}))
                    self.assertFalse(p346._local_donors_available(env={}))
                    rep = p346.run_phase346_drive_focusbracket_shutter_efcs_creativelook_recoverdb_coemulation(
                        env={}
                    )
                    self.assertTrue(rep["all_checks_passed"])
                    self.assertEqual(rep["source_mode"], p346.SOURCE_MODE_CLEAN_ROOM)
                    self.assertEqual(rep["redlines"]["raw_firmware_bytes_leaked"], 0)

    def test_05_clean_room_donor_audit_all_11_contracts(self) -> None:
        for env_key in (p346.ENV_FORCE_CLEAN_ROOM, p346.ENV_CLEAN_ROOM_TEST):
            audit = p346.inspect_phase346_wave66_donors(env={env_key: "1"})
            self.assertEqual(audit.source_mode, p346.SOURCE_MODE_CLEAN_ROOM)
            self.assertEqual(audit.donor_access_mode, p346.DONOR_ACCESS_MODE)
            self.assertEqual(audit.bounded_window_max_bytes, 4096)
            self.assertEqual(audit.donors_checked, 11)
            self.assertEqual(audit.donors_verified, 11)
            self.assertTrue(audit.all_contracts_verified)
            self.assertEqual(audit.raw_firmware_bytes_leaked, 0)

    def test_06_local_donor_o_rdonly_cold_audit_under_250ms(self) -> None:
        if not p346._local_donors_available():
            self.skipTest("Local Mac/work donors unavailable in clean-room environment")
        t0 = time.perf_counter()
        audit = p346.inspect_phase346_wave66_donors(force_clean_room=False)
        elapsed_s = time.perf_counter() - t0
        self.assertEqual(audit.source_mode, p346.SOURCE_MODE_LOCAL_DONOR)
        self.assertEqual(audit.donors_checked, 11)
        self.assertEqual(audit.donors_verified, 11)
        self.assertTrue(audit.all_contracts_verified)
        self.assertEqual(audit.raw_firmware_bytes_leaked, 0)
        self.assertLess(elapsed_s, 0.25)

    def test_07_compact_donor_tokens_across_en_sc_tc_ja_saveload_fx6(self) -> None:
        self.assertEqual(p346.EXPECTED_DONOR_BYTES["fx3_string_en_f"], 373_820)
        self.assertEqual(p346.EXPECTED_DONOR_BYTES["fx3_string_en"], 165_740)
        self.assertEqual(p346.EXPECTED_DONOR_BYTES["fx3_saveload"], 18_760)
        self.assertEqual(p346.EXPECTED_DONOR_BYTES["fx6_string_en"], 118_208)
        self.assertEqual(p346.EXPECTED_DONOR_BYTES["fx6_string_en_2"], 118_676)
        for tok in (
            b"Drive Mode",
            b"Focus Bracket",
            b"Cont. Shooting",
            b"Shutter Type",
            b"e-Front Curtain Shut.",
            b"Long Exposure NR",
            b"High ISO NR",
            b"Creative Look",
            b"Sharpness Range",
            b"Clarity",
            b"Soft Skin Effect",
            b"Delete pressing twice",
            b"Recover Image DB",
            b"Display Media Info.",
        ):
            self.assertIn(tok, p346.COMPACT_DONOR_TOKENS["fx3_string_en_f"])
        self.assertIn(b"Delete confirm.", p346.COMPACT_DONOR_TOKENS["fx3_string_en"])
        self.assertIn(b"Base Look", p346.COMPACT_DONOR_TOKENS["fx6_string_en"])
        self.assertIn(b"Noise Suppression", p346.COMPACT_DONOR_TOKENS["fx6_string_en_2"])

    def test_08_large_donor_elf_and_bk4_tokens_and_typos(self) -> None:
        fx3_elf_tokens = [tok for _, _, tok in p346.LARGE_DONOR_WINDOWS["fx3_appfw"]]
        for expected in (
            b"DRIVE_MODE_1_IMAGE_SHOOTING",
            b"DRIVE_MODE_FOCUS_BRACKET",
            b"DRIVE_MODE_CONT_SHOOTING",
            b"BKID_APP_setting_focus_bracket_order",
            b"BKID_APP_setting_still_shutter_type",
            b"STILL_SHUTTER_TYPE_ANTI_DISTORTION_SHUTTER_AUTO",
            b"BKID_APP_setting_front_curtaion_shutter",
            b"BKID_APP_setting_still_long_exposure_nr",
            b"BKID_APP_setting_still_high_iso_nr",
            b"BKID_APP_creative_look_option_look0",
            b"BKID_APP_setting_soft_skin_effect",
            b"BKID_APP_setting_delete_confirm",
            b"BKID_APP_setting_delete_by_delete_twice",
            b"SYSTEM_MODE_OPTION_RECOVER_DB",
            b"NOT_DISPLAYNG",
        ):
            self.assertIn(expected, fx3_elf_tokens)
        fx6_elf_tokens = [tok for _, _, tok in p346.LARGE_DONOR_WINDOWS["fx6_appfw"]]
        self.assertIn(b"sequence_start_focus_bracket", fx6_elf_tokens)
        self.assertIn(b"soft_skin_effect", fx6_elf_tokens)
        self.assertIn(b"ng_write_protected", fx6_elf_tokens)

    def test_09_bounded_pread_window_strictly_4096_cap_and_o_rdonly(self) -> None:
        self.assertEqual(p346.BOUNDED_WINDOW_MAX_BYTES, 4096)
        self.assertEqual(p346.DONOR_ACCESS_MODE, "O_RDONLY")
        with tempfile.NamedTemporaryFile(delete=False) as tf:
            tf.write(b"X" * 8192)
            p = Path(tf.name)
        try:
            with self.assertRaises(p346.Stage76Phase346Error):
                p346._read_bounded_window_o_rdonly(p, 0, 4097)
            with self.assertRaises(p346.Stage76Phase346Error):
                p346._read_bounded_window_o_rdonly(p, 0, 0)
            chunk = p346._read_bounded_window_o_rdonly(p, 0, 4096)
            self.assertEqual(len(chunk), 4096)
        finally:
            p.unlink()

    def test_10_clean_room_synthetic_mode_makes_zero_file_opens(self) -> None:
        with unittest.mock.patch("os.open", side_effect=AssertionError("os.open forbidden")):
            audit = p346.inspect_phase346_wave66_donors(force_clean_room=True)
            self.assertTrue(audit.all_contracts_verified)
            self.assertEqual(audit.source_mode, p346.SOURCE_MODE_CLEAN_ROOM)
            for art in audit.artifacts.values():
                self.assertEqual(art.source_mode, p346.SOURCE_MODE_CLEAN_ROOM)
                self.assertTrue(art.all_tokens_matched)
                self.assertEqual(art.raw_firmware_bytes_leaked, 0)

    def test_11_audit_json_contains_zero_raw_firmware_bytes(self) -> None:
        rep = p346.run_phase346_drive_focusbracket_shutter_efcs_creativelook_recoverdb_coemulation(
            force_clean_room=True
        )
        serialized = json.dumps(rep)
        self.assertNotIn("\\x7fELF", serialized)
        self.assertNotIn("BK4\\u0000", serialized)
        self.assertEqual(rep["redlines"]["raw_firmware_bytes_leaked"], 0)

    def test_12_four_mode_work_root_override_env_variants(self) -> None:
        with unittest.mock.patch.object(p346, "resolve_mac_work_root", return_value=None):
            r_none = p346.run_phase346_drive_focusbracket_shutter_efcs_creativelook_recoverdb_coemulation(
                env={}
            )
        r_force = p346.run_phase346_drive_focusbracket_shutter_efcs_creativelook_recoverdb_coemulation(
            env={p346.ENV_FORCE_CLEAN_ROOM: "1"}
        )
        r_test = p346.run_phase346_drive_focusbracket_shutter_efcs_creativelook_recoverdb_coemulation(
            env={p346.ENV_CLEAN_ROOM_TEST: "1"}
        )
        self.assertEqual(r_none["audit_digest_sha256"], r_force["audit_digest_sha256"])
        self.assertEqual(r_force["audit_digest_sha256"], r_test["audit_digest_sha256"])

    def test_13_deterministic_digest_excludes_wall_clock(self) -> None:
        r1 = p346.run_phase346_drive_focusbracket_shutter_efcs_creativelook_recoverdb_coemulation(
            force_clean_room=True
        )
        r2 = p346.run_phase346_drive_focusbracket_shutter_efcs_creativelook_recoverdb_coemulation(
            force_clean_room=True
        )
        self.assertEqual(r1["audit_digest_sha256"], r2["audit_digest_sha256"])
        self.assertNotIn("elapsed_seconds", r1)

    def test_14_local_donor_tokens_verified_if_present(self) -> None:
        if not p346._local_donors_available():
            self.skipTest("Local Mac/work donors unavailable in clean-room environment")
        audit = p346.inspect_phase346_wave66_donors(force_clean_room=False)
        for key, art in audit.artifacts.items():
            self.assertTrue(art.size_matched, key)
            self.assertTrue(art.expected_sha256_matched, key)
            self.assertTrue(art.all_tokens_matched, key)
            self.assertEqual(art.raw_firmware_bytes_leaked, 0, key)

    # ------------------------------------------------------------------
    # Sub-Model 76A: Still [Drive Mode] 10 fps / Bracket / Dormant Focus Bracket (Tests 15..36)
    # ------------------------------------------------------------------

    def test_15_76a_single_shooting_default(self) -> None:
        r = p346.simulate_drive_mode_cont_bracket_and_dormant_focus_bracket_hil()
        self.assertTrue(r.admitted)
        self.assertEqual(r.errno_code, 0)
        self.assertEqual(r.effective_drive_mode, "Single Shooting")
        self.assertFalse(r.focus_bracket_exposed)
        self.assertTrue(r.drive_mode_resettable)

    def test_16_76a_cont_shooting_hi_plus_10fps_non_realtime_lv(self) -> None:
        r = p346.simulate_drive_mode_cont_bracket_and_dormant_focus_bracket_hil(
            drive_mode="Cont. Shooting",
            cont_speed="Hi+",
            aperture_f_stop=2.8,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.nominal_max_fps, 10)
        self.assertEqual(r.effective_fps_cap, 10.0)
        self.assertFalse(r.live_view_realtime)
        self.assertFalse(r.af_locked_on_first_frame)
        self.assertFalse(r.burst_rate_reduced)

    def test_17_76a_cont_shooting_hi_mid_lo_fps_and_realtime_lv(self) -> None:
        for spd, fps in (("Hi", 8), ("Mid", 6), ("Lo", 3)):
            r = p346.simulate_drive_mode_cont_bracket_and_dormant_focus_bracket_hil(
                drive_mode="Cont. Shooting",
                cont_speed=spd,
            )
            self.assertTrue(r.admitted, spd)
            self.assertEqual(r.nominal_max_fps, fps, spd)
            self.assertEqual(r.effective_fps_cap, float(fps), spd)
            self.assertTrue(r.live_view_realtime, spd)

    def test_18_76a_aperture_gt_f11_locks_af_first_frame_in_hi_plus_hi_mid(self) -> None:
        for spd in ("Hi+", "Hi", "Mid"):
            r = p346.simulate_drive_mode_cont_bracket_and_dormant_focus_bracket_hil(
                drive_mode="Cont. Shooting",
                cont_speed=spd,
                aperture_f_stop=16.0,
            )
            self.assertTrue(r.admitted, spd)
            self.assertTrue(r.af_locked_on_first_frame, spd)

    def test_19_76a_aperture_gt_f11_lo_does_not_lock_af_first_frame(self) -> None:
        r = p346.simulate_drive_mode_cont_bracket_and_dormant_focus_bracket_hil(
            drive_mode="Cont. Shooting",
            cont_speed="Lo",
            aperture_f_stop=16.0,
        )
        self.assertTrue(r.admitted)
        self.assertFalse(r.af_locked_on_first_frame)

    def test_20_76a_uncompressed_raw_and_flash_reduce_burst_rate(self) -> None:
        r_raw = p346.simulate_drive_mode_cont_bracket_and_dormant_focus_bracket_hil(
            drive_mode="Cont. Shooting",
            cont_speed="Hi+",
            raw_file_type="Uncompressed",
        )
        self.assertTrue(r_raw.admitted)
        self.assertTrue(r_raw.burst_rate_reduced)
        self.assertLess(r_raw.effective_fps_cap, 10.0)

        r_flash = p346.simulate_drive_mode_cont_bracket_and_dormant_focus_bracket_hil(
            drive_mode="Cont. Shooting",
            cont_speed="Hi+",
            external_flash_attached=True,
        )
        self.assertTrue(r_flash.admitted)
        self.assertTrue(r_flash.burst_rate_reduced)
        self.assertLessEqual(r_flash.effective_fps_cap, 5.0)

    def test_21_76a_self_timer_single_10_5_2_sec(self) -> None:
        for sec in (10, 5, 2):
            r = p346.simulate_drive_mode_cont_bracket_and_dormant_focus_bracket_hil(
                drive_mode="Self-timer(Single)",
                self_timer_single_sec=sec,
            )
            self.assertTrue(r.admitted)
            self.assertEqual(r.effective_self_timer_single_sec, sec)

    def test_22_76a_self_timer_cont_6_active_options(self) -> None:
        count = 0
        for sec in (10, 5, 2):
            for shots in (3, 5):
                r = p346.simulate_drive_mode_cont_bracket_and_dormant_focus_bracket_hil(
                    drive_mode="Self-timer(Cont)",
                    self_timer_cont_sec=sec,
                    self_timer_cont_shots=shots,
                )
                self.assertTrue(r.admitted)
                self.assertEqual(r.effective_self_timer_cont_sec, sec)
                self.assertEqual(r.effective_self_timer_cont_shots, shots)
                self.assertEqual(r.self_timer_cont_options_count, 6)
                count += 1
        self.assertEqual(count, 6)

    def test_23_76a_self_timer_cont_dormant_10_img_rejected_95(self) -> None:
        r = p346.simulate_drive_mode_cont_bracket_and_dormant_focus_bracket_hil(
            drive_mode="Self-timer(Cont)",
            self_timer_cont_sec=10,
            self_timer_cont_shots=10,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, 95)

    def test_24_76a_cont_and_single_bracket_fine_ev_allows_3_5_9_shots(self) -> None:
        for mode in ("Cont. Bracket", "Single Bracket"):
            for ev in (0.3, 0.5, 0.7, 1.0):
                for shots in (3, 5, 9):
                    r = p346.simulate_drive_mode_cont_bracket_and_dormant_focus_bracket_hil(
                        drive_mode=mode,
                        bracket_ev_step=ev,
                        bracket_shots=shots,
                    )
                    self.assertTrue(r.admitted, (mode, ev, shots))
                    self.assertEqual(r.effective_bracket_ev_step, ev)
                    self.assertEqual(r.effective_bracket_shots, shots)

    def test_25_76a_bracket_2_0_and_3_0_ev_allow_3_or_5_reject_9_einval(self) -> None:
        for ev in (2.0, 3.0):
            for shots in (3, 5):
                r_ok = p346.simulate_drive_mode_cont_bracket_and_dormant_focus_bracket_hil(
                    drive_mode="Cont. Bracket",
                    bracket_ev_step=ev,
                    bracket_shots=shots,
                )
                self.assertTrue(r_ok.admitted)
            r_bad = p346.simulate_drive_mode_cont_bracket_and_dormant_focus_bracket_hil(
                drive_mode="Single Bracket",
                bracket_ev_step=ev,
                bracket_shots=9,
            )
            self.assertFalse(r_bad.admitted)
            self.assertEqual(r_bad.errno_code, 22)

    def test_26_76a_iauto_disables_exposure_brackets(self) -> None:
        for mode in ("Cont. Bracket", "Single Bracket"):
            r = p346.simulate_drive_mode_cont_bracket_and_dormant_focus_bracket_hil(
                exposure_mode="iAuto",
                drive_mode=mode,
            )
            self.assertFalse(r.admitted)
            self.assertEqual(r.errno_code, 95)

    def test_27_76a_wb_bracket_lo_hi_3_shots(self) -> None:
        for lvl in ("Lo", "Hi"):
            r = p346.simulate_drive_mode_cont_bracket_and_dormant_focus_bracket_hil(
                drive_mode="WB bracket",
                wb_bracket_level=lvl,
            )
            self.assertTrue(r.admitted)
            self.assertEqual(r.effective_wb_bracket_level, lvl)
            self.assertEqual(r.effective_bracket_shots, 3)

    def test_28_76a_dro_bracket_ok_without_hlg_blocked_under_hlg_on(self) -> None:
        r_ok = p346.simulate_drive_mode_cont_bracket_and_dormant_focus_bracket_hil(
            drive_mode="DRO Bracket",
            dro_bracket_level="Hi",
            hlg_still_image="Off",
        )
        self.assertTrue(r_ok.admitted)
        self.assertEqual(r_ok.effective_dro_bracket_level, "Hi")
        self.assertFalse(r_ok.dro_bracket_blocked_by_hlg)

        r_blk = p346.simulate_drive_mode_cont_bracket_and_dormant_focus_bracket_hil(
            drive_mode="DRO Bracket",
            dro_bracket_level="Lo",
            hlg_still_image="On",
        )
        self.assertFalse(r_blk.admitted)
        self.assertEqual(r_blk.errno_code, 95)
        self.assertTrue(r_blk.dro_bracket_blocked_by_hlg)

    def test_29_76a_bracket_settings_and_interval_shoot_func(self) -> None:
        r = p346.simulate_drive_mode_cont_bracket_and_dormant_focus_bracket_hil(
            drive_mode="Single Shooting",
            bracket_selftimer="2 Sec",
            bracket_order="-->0->+",
            interval_shoot_enabled=True,
            shutter_type_in_interval="Electronic Shutter",
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.effective_bracket_selftimer, "2 Sec")
        self.assertEqual(r.effective_bracket_order, "-->0->+")
        self.assertTrue(r.interval_shoot_enabled)
        self.assertEqual(r.effective_shutter_type_in_interval, "Electronic Shutter")
        self.assertTrue(r.interval_outputs_still_sequence_only)

    def test_30_76a_camera_settings_reset_restores_all_drive_mode_settings(self) -> None:
        r = p346.simulate_drive_mode_cont_bracket_and_dormant_focus_bracket_hil(
            drive_mode="Cont. Shooting",
            cont_speed="Hi+",
            bracket_selftimer="5 Sec",
            bracket_order="-->0->+",
            interval_shoot_enabled=True,
            shutter_type_in_interval="Mechanical Shutter",
            camera_settings_reset_applied=True,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.effective_drive_mode, "Single Shooting")
        self.assertEqual(r.effective_bracket_selftimer, "Off")
        self.assertEqual(r.effective_bracket_order, "0->-->+")
        self.assertEqual(r.effective_shutter_type_in_interval, "Electronic Shutter")
        self.assertFalse(r.interval_shoot_enabled)

    def test_31_76a_movie_and_sq_modes_disable_still_drive_mode(self) -> None:
        for sm in ("Movie", "S&Q"):
            r = p346.simulate_drive_mode_cont_bracket_and_dormant_focus_bracket_hil(
                shoot_mode=sm,
                drive_mode="Cont. Shooting",
            )
            self.assertFalse(r.admitted)
            self.assertEqual(r.errno_code, 95)
            self.assertEqual(r.effective_drive_mode, "Disabled")

    def test_32_76a_dormant_focus_bracket_myth_busted_eopnotsupp_95(self) -> None:
        r = p346.simulate_drive_mode_cont_bracket_and_dormant_focus_bracket_hil(
            drive_mode="Focus Bracket",
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, 95)
        self.assertFalse(r.focus_bracket_exposed)
        self.assertEqual(r.effective_drive_mode, "Single Shooting")
        with self.assertRaises(p346.Stage76Phase346Error):
            p346.simulate_drive_mode_cont_bracket_and_dormant_focus_bracket_hil(
                drive_mode="DRIVE_MODE_FOCUS_BRACKET"
            )

    def test_33_76a_fx6_pure_cinema_zero_still_drive_mode_and_zero_focus_bracket(self) -> None:
        for dm in ("Single Shooting", "Cont. Shooting", "Focus Bracket"):
            r = p346.simulate_drive_mode_cont_bracket_and_dormant_focus_bracket_hil(
                body_profile="ILME-FX6",
                fw_version="6.01",
                drive_mode=dm,
            )
            self.assertFalse(r.admitted)
            self.assertEqual(r.errno_code, 95)
            self.assertFalse(r.fx6_still_drive_mode_supported)
            self.assertFalse(r.focus_bracket_exposed)

    def test_34_76a_interval_shutter_type_supports_mech_or_elec(self) -> None:
        r = p346.simulate_drive_mode_cont_bracket_and_dormant_focus_bracket_hil(
            interval_shoot_enabled=True,
            shutter_type_in_interval="Mechanical Shutter",
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.effective_shutter_type_in_interval, "Mechanical Shutter")

    def test_35_76a_hi_plus_with_raw_uncompressed_and_f11_boundary(self) -> None:
        r_f11 = p346.simulate_drive_mode_cont_bracket_and_dormant_focus_bracket_hil(
            drive_mode="Cont. Shooting",
            cont_speed="Hi+",
            aperture_f_stop=11.0,
        )
        self.assertFalse(r_f11.af_locked_on_first_frame)
        r_f13 = p346.simulate_drive_mode_cont_bracket_and_dormant_focus_bracket_hil(
            drive_mode="Cont. Shooting",
            cont_speed="Hi+",
            aperture_f_stop=13.0,
        )
        self.assertTrue(r_f13.af_locked_on_first_frame)

    def test_36_76a_invalid_inputs_raise_stage76_error(self) -> None:
        for bad in (
            dict(body_profile="FX30"),
            dict(fw_version="9.00"),
            dict(shoot_mode="Timelapse"),
            dict(drive_mode="Pixel Shift"),
            dict(cont_speed="Ultra"),
            dict(aperture_f_stop=0.0),
            dict(raw_file_type="Lossless"),
            dict(self_timer_single_sec=1),
            dict(self_timer_cont_sec=3),
            dict(self_timer_cont_shots=7),
            dict(bracket_ev_step=1.5),
            dict(bracket_shots=7),
            dict(wb_bracket_level="Mid"),
            dict(dro_bracket_level="Mid"),
            dict(hlg_still_image="Auto"),
            dict(bracket_selftimer="20 Sec"),
            dict(bracket_order="-->+->0"),
            dict(shutter_type_in_interval="Auto"),
        ):
            with self.assertRaises(p346.Stage76Phase346Error, msg=str(bad)):
                p346.simulate_drive_mode_cont_bracket_and_dormant_focus_bracket_hil(**bad)

    # ------------------------------------------------------------------
    # Sub-Model 76B: [Shutter Type] 2-Opt Zero-Auto, 1/250 X-Sync, EFCS & NR (Tests 37..56)
    # ------------------------------------------------------------------

    def test_37_76b_shutter_type_2_options_default_mechanical(self) -> None:
        r = p346.simulate_shutter_type_xsync_efcs_long_exp_high_iso_nr_hil()
        self.assertTrue(r.admitted)
        self.assertEqual(r.effective_shutter_type, "Mechanical Shutter")
        self.assertFalse(r.shutter_type_auto_exposed)
        self.assertTrue(r.shutter_type_resettable)
        self.assertEqual(r.flash_xsync_max_denom, 250)

    def test_38_76b_shutter_type_dormant_auto_rejected_95(self) -> None:
        r = p346.simulate_shutter_type_xsync_efcs_long_exp_high_iso_nr_hil(
            shutter_type="Auto",
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, 95)
        self.assertFalse(r.shutter_type_auto_exposed)
        self.assertEqual(r.effective_shutter_type, "Mechanical Shutter")

    def test_39_76b_electronic_shutter_locks_all_5_features(self) -> None:
        r_ok = p346.simulate_shutter_type_xsync_efcs_long_exp_high_iso_nr_hil(
            shutter_type="Electronic Shutter",
        )
        self.assertTrue(r_ok.admitted)
        self.assertTrue(r_ok.eshutter_or_silent_5locks_engaged)
        self.assertEqual(len(r_ok.locked_features), 5)
        self.assertEqual(r_ok.effective_efcs, "Locked")
        self.assertEqual(r_ok.effective_long_exposure_nr, "Locked")

        for req in (
            dict(flash_requested=True),
            dict(bulb_requested=True),
            dict(anti_flicker_requested=True),
            dict(efcs_active_use_requested=True),
            dict(long_exposure_nr_requested="On"),
        ):
            r_blk = p346.simulate_shutter_type_xsync_efcs_long_exp_high_iso_nr_hil(
                shutter_type="Electronic Shutter",
                **req,
            )
            self.assertFalse(r_blk.admitted, str(req))
            self.assertEqual(r_blk.errno_code, 95, str(req))

    def test_40_76b_silent_mode_on_locks_all_5_features(self) -> None:
        r = p346.simulate_shutter_type_xsync_efcs_long_exp_high_iso_nr_hil(
            shutter_type="Mechanical Shutter",
            silent_mode="On",
            flash_requested=True,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, 95)
        self.assertTrue(r.eshutter_or_silent_5locks_engaged)
        self.assertEqual(len(r.locked_features), 5)

    def test_41_76b_flash_xsync_1_250_across_both_ff_and_apsc(self) -> None:
        for crop in ("Full-Frame", "APS-C/S35"):
            r = p346.simulate_shutter_type_xsync_efcs_long_exp_high_iso_nr_hil(
                sensor_crop=crop,
                flash_requested=True,
                requested_flash_xsync_denom=250,
            )
            self.assertTrue(r.admitted, crop)
            self.assertEqual(r.flash_xsync_max_denom, 250)

    def test_42_76b_flash_xsync_1_320_rejected_95_on_both_ff_and_apsc(self) -> None:
        for crop in ("Full-Frame", "APS-C/S35"):
            r = p346.simulate_shutter_type_xsync_efcs_long_exp_high_iso_nr_hil(
                sensor_crop=crop,
                flash_requested=True,
                requested_flash_xsync_denom=320,
            )
            self.assertFalse(r.admitted, crop)
            self.assertEqual(r.errno_code, 95)

    def test_43_76b_efcs_curtaion_typo_reset_immune_restored_only_on_init(self) -> None:
        r_reset = p346.simulate_shutter_type_xsync_efcs_long_exp_high_iso_nr_hil(
            shutter_type="Electronic Shutter",
            efcs_setting="Off",
            long_exposure_nr_requested="Off",
            high_iso_nr_requested="Off",
            camera_settings_reset_applied=True,
        )
        self.assertTrue(r_reset.admitted)
        self.assertEqual(r_reset.effective_shutter_type, "Mechanical Shutter")
        self.assertEqual(r_reset.effective_efcs, "Off")
        self.assertEqual(r_reset.efcs_elf_symbol, "BKID_APP_setting_front_curtaion_shutter")
        self.assertFalse(r_reset.efcs_resettable)
        self.assertEqual(r_reset.effective_long_exposure_nr, "On")
        self.assertEqual(r_reset.effective_high_iso_nr, "Normal")

        r_init = p346.simulate_shutter_type_xsync_efcs_long_exp_high_iso_nr_hil(
            efcs_setting="Off",
            initialize_applied=True,
        )
        self.assertTrue(r_init.admitted)
        self.assertEqual(r_init.effective_efcs, "On")

    def test_44_76b_efcs_bokeh_clipping_and_minolta_adapter_shading_advisories(self) -> None:
        r = p346.simulate_shutter_type_xsync_efcs_long_exp_high_iso_nr_hil(
            efcs_setting="On",
            aperture_f_stop=1.4,
            shutter_seconds=1.0 / 4000.0,
            adapter_or_third_party_lens=True,
        )
        self.assertTrue(r.admitted)
        self.assertTrue(r.bokeh_clipping_advisory)
        self.assertTrue(r.minolta_adapter_shading_advisory)

        r_off = p346.simulate_shutter_type_xsync_efcs_long_exp_high_iso_nr_hil(
            efcs_setting="Off",
            aperture_f_stop=1.4,
            shutter_seconds=1.0 / 4000.0,
            adapter_or_third_party_lens=True,
        )
        self.assertFalse(r_off.bokeh_clipping_advisory)
        self.assertFalse(r_off.minolta_adapter_shading_advisory)

    def test_45_76b_non_hss_high_ss_flash_banding_advisory(self) -> None:
        r = p346.simulate_shutter_type_xsync_efcs_long_exp_high_iso_nr_hil(
            flash_requested=True,
            requested_flash_xsync_denom=250,
            third_party_non_hss_trigger=True,
            shutter_seconds=1.0 / 8000.0,
        )
        self.assertTrue(r.admitted)
        self.assertTrue(r.high_ss_non_hss_banding_advisory)

    def test_46_76b_long_exposure_nr_triggers_dark_frame_at_ge_1s(self) -> None:
        r_1s = p346.simulate_shutter_type_xsync_efcs_long_exp_high_iso_nr_hil(
            long_exposure_nr_requested="On",
            shutter_seconds=1.0,
        )
        self.assertTrue(r_1s.admitted)
        self.assertTrue(r_1s.dark_frame_subtraction_triggered)

        r_fast = p346.simulate_shutter_type_xsync_efcs_long_exp_high_iso_nr_hil(
            long_exposure_nr_requested="On",
            shutter_seconds=0.5,
        )
        self.assertTrue(r_fast.admitted)
        self.assertFalse(r_fast.dark_frame_subtraction_triggered)

        r_off = p346.simulate_shutter_type_xsync_efcs_long_exp_high_iso_nr_hil(
            long_exposure_nr_requested="Off",
            shutter_seconds=5.0,
        )
        self.assertFalse(r_off.dark_frame_subtraction_triggered)

    def test_47_76b_long_exposure_nr_locked_in_cont_and_cont_bracket(self) -> None:
        for dm in ("Cont. Shooting", "Cont. Bracket"):
            r = p346.simulate_shutter_type_xsync_efcs_long_exp_high_iso_nr_hil(
                drive_mode=dm,
                long_exposure_nr_requested="On",
            )
            self.assertFalse(r.admitted, dm)
            self.assertEqual(r.errno_code, 95)

    def test_48_76b_long_exposure_nr_forced_on_in_iauto(self) -> None:
        r = p346.simulate_shutter_type_xsync_efcs_long_exp_high_iso_nr_hil(
            exposure_mode="iAuto",
            long_exposure_nr_requested="Off",
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, 95)

    def test_49_76b_high_iso_nr_normal_low_off_and_dormant_high_rejected(self) -> None:
        for lvl in ("Normal", "Low", "Off"):
            r = p346.simulate_shutter_type_xsync_efcs_long_exp_high_iso_nr_hil(
                file_format="JPEG",
                high_iso_nr_requested=lvl,
            )
            self.assertTrue(r.admitted, lvl)
            self.assertEqual(r.effective_high_iso_nr, lvl)
            self.assertFalse(r.arw_raw_data_mutated)

        r_high = p346.simulate_shutter_type_xsync_efcs_long_exp_high_iso_nr_hil(
            file_format="JPEG",
            high_iso_nr_requested="High",
        )
        self.assertFalse(r_high.admitted)
        self.assertEqual(r_high.errno_code, 95)

    def test_50_76b_high_iso_nr_disabled_on_pure_raw_and_never_mutates_arw(self) -> None:
        r_blk = p346.simulate_shutter_type_xsync_efcs_long_exp_high_iso_nr_hil(
            file_format="RAW",
            high_iso_nr_requested="Low",
        )
        self.assertFalse(r_blk.admitted)
        self.assertEqual(r_blk.errno_code, 95)
        self.assertTrue(r_blk.high_iso_nr_disabled_on_pure_raw)
        self.assertFalse(r_blk.arw_raw_data_mutated)

        r_rj = p346.simulate_shutter_type_xsync_efcs_long_exp_high_iso_nr_hil(
            file_format="RAW & JPEG",
            high_iso_nr_requested="Low",
        )
        self.assertTrue(r_rj.admitted)
        self.assertFalse(r_rj.arw_raw_data_mutated)

    def test_51_76b_high_iso_nr_fixed_normal_in_iauto(self) -> None:
        for lvl in ("Low", "Off"):
            r = p346.simulate_shutter_type_xsync_efcs_long_exp_high_iso_nr_hil(
                exposure_mode="iAuto",
                high_iso_nr_requested=lvl,
            )
            self.assertFalse(r.admitted)
            self.assertEqual(r.errno_code, 95)

    def test_52_76b_fx6_shutterless_noise_suppression_and_apr_lens_cap_gate(self) -> None:
        for lvl in ("Off", "Low", "Mid", "High"):
            r = p346.simulate_shutter_type_xsync_efcs_long_exp_high_iso_nr_hil(
                body_profile="ILME-FX6",
                fw_version="6.01",
                fx6_noise_suppression=lvl,
            )
            self.assertTrue(r.admitted, lvl)
            self.assertEqual(r.fx6_noise_suppression, lvl)

        r_apr_uncovered = p346.simulate_shutter_type_xsync_efcs_long_exp_high_iso_nr_hil(
            body_profile="ILME-FX6",
            fw_version="6.01",
            fx6_apr_execute=True,
            apr_lens_cap_covered=False,
        )
        self.assertFalse(r_apr_uncovered.admitted)
        self.assertEqual(r_apr_uncovered.errno_code, 22)

        r_apr_covered = p346.simulate_shutter_type_xsync_efcs_long_exp_high_iso_nr_hil(
            body_profile="ILME-FX6",
            fw_version="6.01",
            fx6_apr_execute=True,
            apr_lens_cap_covered=True,
        )
        self.assertTrue(r_apr_covered.admitted)
        self.assertTrue(r_apr_covered.fx6_apr_executed)

    def test_53_76b_fx6_rejects_mech_shutter_flash_efcs_and_long_exp_nr(self) -> None:
        for kw in (
            dict(shutter_type="Electronic Shutter"),
            dict(flash_requested=True),
            dict(bulb_requested=True),
            dict(anti_flicker_requested=True),
            dict(efcs_active_use_requested=True),
            dict(long_exposure_nr_requested="On"),
        ):
            r = p346.simulate_shutter_type_xsync_efcs_long_exp_high_iso_nr_hil(
                body_profile="ILME-FX6",
                fw_version="6.01",
                **kw,
            )
            self.assertFalse(r.admitted, str(kw))
            self.assertEqual(r.errno_code, 95)

    def test_54_76b_heif_raw_also_protects_arw_while_enabling_heif_nr(self) -> None:
        r = p346.simulate_shutter_type_xsync_efcs_long_exp_high_iso_nr_hil(
            file_format="RAW & HEIF",
            high_iso_nr_requested="Off",
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.effective_high_iso_nr, "Off")
        self.assertFalse(r.arw_raw_data_mutated)

    def test_55_76b_efcs_disabled_still_keeps_reset_immunity_verified(self) -> None:
        r = p346.simulate_shutter_type_xsync_efcs_long_exp_high_iso_nr_hil(
            efcs_setting="Off",
            camera_settings_reset_applied=True,
        )
        self.assertEqual(r.effective_efcs, "Off")
        self.assertFalse(r.efcs_resettable)

    def test_56_76b_invalid_inputs_raise_stage76_error(self) -> None:
        for bad in (
            dict(body_profile="FX30"),
            dict(fw_version="8.00"),
            dict(shoot_mode="Timelapse"),
            dict(sensor_crop="Micro43"),
            dict(shutter_type="Global"),
            dict(silent_mode="Auto"),
            dict(drive_mode="Focus Bracket"),
            dict(efcs_setting="Auto"),
            dict(shutter_seconds=0.0),
            dict(aperture_f_stop=0.0),
            dict(requested_flash_xsync_denom=0),
            dict(long_exposure_nr_requested="Auto"),
            dict(file_format="TIFF"),
            dict(high_iso_nr_requested="Ultra"),
            dict(fx6_exposure_mode="iAuto"),
            dict(fx6_noise_suppression="Extreme"),
        ):
            with self.assertRaises(p346.Stage76Phase346Error, msg=str(bad)):
                p346.simulate_shutter_type_xsync_efcs_long_exp_high_iso_nr_hil(**bad)

    # ------------------------------------------------------------------
    # Sub-Model 76C: [Creative Look] 10+6, 8 Params `0..9`, PP/Log & Soft Skin (Tests 57..74)
    # ------------------------------------------------------------------

    def test_57_76c_creative_look_10_presets_and_6_custom_slots(self) -> None:
        self.assertEqual(len(p346.CREATIVE_LOOK_PRESETS), 10)
        self.assertEqual(len(p346.CREATIVE_LOOK_CUSTOM_SLOTS), 6)
        for look in (*p346.CREATIVE_LOOK_PRESETS, *p346.CREATIVE_LOOK_CUSTOM_SLOTS):
            r = p346.simulate_creative_look_params_pp_log_override_and_soft_skin_dormancy_hil(
                creative_look=look,
            )
            self.assertTrue(r.admitted, look)
            self.assertEqual(r.effective_creative_look, look)
            self.assertEqual(r.presets_count, 10)
            self.assertEqual(r.custom_slots_count, 6)
            self.assertEqual(r.param_count, 8)
            self.assertTrue(r.look_slots_separate_still_movie)
            self.assertTrue(r.creative_look_resettable)

    def test_58_76c_8_param_exact_bounds_with_0_to_9_for_fade_sharpness_clarity(self) -> None:
        r_max = p346.simulate_creative_look_params_pp_log_override_and_soft_skin_dormancy_hil(
            creative_look="Custom Look 1",
            contrast=9,
            highlights=-9,
            shadows=9,
            fade=9,
            saturation=-9,
            sharpness=9,
            sharpness_range=5,
            clarity=9,
        )
        self.assertTrue(r_max.admitted)
        self.assertEqual(r_max.effective_params["fade"], 9)
        self.assertEqual(r_max.effective_params["sharpness"], 9)
        self.assertEqual(r_max.effective_params["clarity"], 9)
        self.assertEqual(r_max.effective_params["sharpness_range"], 5)

        r_min = p346.simulate_creative_look_params_pp_log_override_and_soft_skin_dormancy_hil(
            creative_look="Custom Look 6",
            fade=0,
            sharpness=0,
            sharpness_range=1,
            clarity=0,
        )
        self.assertTrue(r_min.admitted)

    def test_59_76c_fade_sharpness_clarity_reject_negative_values_einval_22(self) -> None:
        for key in ("fade", "sharpness", "clarity"):
            r_neg = p346.simulate_creative_look_params_pp_log_override_and_soft_skin_dormancy_hil(
                creative_look="ST",
                **{key: -1},
            )
            self.assertFalse(r_neg.admitted, key)
            self.assertEqual(r_neg.errno_code, 22, key)
            r_hi = p346.simulate_creative_look_params_pp_log_override_and_soft_skin_dormancy_hil(
                creative_look="ST",
                **{key: 10},
            )
            self.assertFalse(r_hi.admitted, key)
            self.assertEqual(r_hi.errno_code, 22, key)

    def test_60_76c_sharpness_range_enforces_1_to_5_bounds_einval_22(self) -> None:
        for bad_val in (0, 6):
            r = p346.simulate_creative_look_params_pp_log_override_and_soft_skin_dormancy_hil(
                creative_look="VV",
                sharpness_range=bad_val,
            )
            self.assertFalse(r.admitted)
            self.assertEqual(r.errno_code, 22)

    def test_61_76c_signed_params_enforce_minus9_to_plus9_einval_22(self) -> None:
        for key in ("contrast", "highlights", "shadows", "saturation"):
            for bad_val in (-10, 10):
                r = p346.simulate_creative_look_params_pp_log_override_and_soft_skin_dormancy_hil(
                    creative_look="FL",
                    **{key: bad_val},
                )
                self.assertFalse(r.admitted, (key, bad_val))
                self.assertEqual(r.errno_code, 22)

    def test_62_76c_bw_and_se_lock_saturation(self) -> None:
        for look in ("BW", "SE"):
            r_ok = p346.simulate_creative_look_params_pp_log_override_and_soft_skin_dormancy_hil(
                creative_look=look,
            )
            self.assertTrue(r_ok.admitted)
            self.assertTrue(r_ok.saturation_locked_bw_se)
            self.assertIsNone(r_ok.effective_params["saturation"])

            r_blk = p346.simulate_creative_look_params_pp_log_override_and_soft_skin_dormancy_hil(
                creative_look=look,
                saturation=3,
            )
            self.assertFalse(r_blk.admitted)
            self.assertEqual(r_blk.errno_code, 95)

    def test_63_76c_movie_and_sq_lock_sharpness_range(self) -> None:
        for sm in ("Movie", "S&Q"):
            r_ok = p346.simulate_creative_look_params_pp_log_override_and_soft_skin_dormancy_hil(
                shoot_mode=sm,
                creative_look="FL",
            )
            self.assertTrue(r_ok.admitted)
            self.assertTrue(r_ok.sharpness_range_locked_movie_sq)
            self.assertIsNone(r_ok.effective_params["sharpness_range"])

            r_blk = p346.simulate_creative_look_params_pp_log_override_and_soft_skin_dormancy_hil(
                shoot_mode=sm,
                creative_look="FL",
                sharpness_range=4,
            )
            self.assertFalse(r_blk.admitted)
            self.assertEqual(r_blk.errno_code, 95)

    def test_64_76c_iauto_pp11_log_and_hlg_still_override_creative_look_to_dash(self) -> None:
        for kw in (
            dict(exposure_mode="iAuto"),
            dict(picture_profile="PP11"),
            dict(log_shooting="Flexible ISO"),
            dict(log_shooting="Cine EI"),
            dict(log_shooting="Cine EI Quick"),
            dict(hlg_still_image="On"),
        ):
            r_dash = p346.simulate_creative_look_params_pp_log_override_and_soft_skin_dormancy_hil(
                creative_look="ST",
                **kw,
            )
            self.assertTrue(r_dash.admitted, str(kw))
            self.assertEqual(r_dash.effective_creative_look, "[-]")
            self.assertTrue(r_dash.creative_look_locked_dash)

            r_override_blk = p346.simulate_creative_look_params_pp_log_override_and_soft_skin_dormancy_hil(
                creative_look="VV2",
                **kw,
            )
            self.assertFalse(r_override_blk.admitted, str(kw))
            self.assertEqual(r_override_blk.errno_code, 95)

    def test_65_76c_camera_settings_reset_restores_creative_look_to_st_defaults(self) -> None:
        r = p346.simulate_creative_look_params_pp_log_override_and_soft_skin_dormancy_hil(
            creative_look="Custom Look 3",
            contrast=7,
            clarity=8,
            sharpness_range=5,
            camera_settings_reset_applied=True,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.effective_creative_look, "ST")
        self.assertEqual(r.effective_params["contrast"], 0)
        self.assertEqual(r.effective_params["clarity"], 0)
        self.assertEqual(r.effective_params["sharpness_range"], 3)

    def test_66_76c_dormant_soft_skin_effect_rejected_on_both_fx3_and_fx6(self) -> None:
        for body, fw in (("ILME-FX3", "7.02"), ("ILME-FX6", "6.01")):
            for lvl in ("Off", "Low", "Mid", "High"):
                r = p346.simulate_creative_look_params_pp_log_override_and_soft_skin_dormancy_hil(
                    body_profile=body,
                    fw_version=fw,
                    soft_skin_effect_requested=lvl,
                )
                self.assertFalse(r.admitted, (body, lvl))
                self.assertEqual(r.errno_code, 95)
                self.assertFalse(r.soft_skin_effect_exposed)

    def test_67_76c_fx6_uses_paint_look_base_look_and_rejects_creative_look(self) -> None:
        for bl in ("S-Cinetone", "s709", "HLG Live", "HLG Natural"):
            r_ok = p346.simulate_creative_look_params_pp_log_override_and_soft_skin_dormancy_hil(
                body_profile="ILME-FX6",
                fw_version="6.01",
                fx6_base_look=bl,
            )
            self.assertTrue(r_ok.admitted, bl)
            self.assertEqual(r_ok.fx6_base_look, bl)
            self.assertTrue(r_ok.fx6_paint_pipeline_active)
            self.assertEqual(r_ok.presets_count, 0)

        r_blk = p346.simulate_creative_look_params_pp_log_override_and_soft_skin_dormancy_hil(
            body_profile="ILME-FX6",
            fw_version="6.01",
            creative_look="VV",
        )
        self.assertFalse(r_blk.admitted)
        self.assertEqual(r_blk.errno_code, 95)

    def test_68_76c_creative_look_defaults_in_still_mode(self) -> None:
        r = p346.simulate_creative_look_params_pp_log_override_and_soft_skin_dormancy_hil()
        self.assertTrue(r.admitted)
        self.assertEqual(
            r.effective_params,
            {
                "contrast": 0,
                "highlights": 0,
                "shadows": 0,
                "fade": 0,
                "saturation": 0,
                "sharpness": 0,
                "sharpness_range": 3,
                "clarity": 0,
            },
        )

    def test_69_76c_vv2_fl_in_sh_presets_available_in_movie_and_still(self) -> None:
        for look in ("VV2", "FL", "IN", "SH"):
            for sm in ("Still", "Movie"):
                r = p346.simulate_creative_look_params_pp_log_override_and_soft_skin_dormancy_hil(
                    shoot_mode=sm,
                    creative_look=look,
                )
                self.assertTrue(r.admitted, (look, sm))
                self.assertEqual(r.effective_creative_look, look)

    def test_70_76c_pp1_also_locks_creative_look_to_dash(self) -> None:
        r = p346.simulate_creative_look_params_pp_log_override_and_soft_skin_dormancy_hil(
            creative_look="PT",
            picture_profile="PP1",
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, 95)
        self.assertEqual(r.effective_creative_look, "[-]")

    def test_71_76c_param_override_precedence_respects_soft_skin_first(self) -> None:
        r = p346.simulate_creative_look_params_pp_log_override_and_soft_skin_dormancy_hil(
            picture_profile="PP11",
            soft_skin_effect_requested="Mid",
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, 95)
        self.assertFalse(r.soft_skin_effect_exposed)

    def test_72_76c_custom_look_6_allows_clarity_and_fade_within_0_to_9(self) -> None:
        r = p346.simulate_creative_look_params_pp_log_override_and_soft_skin_dormancy_hil(
            creative_look="Custom Look 6",
            fade=5,
            clarity=4,
            sharpness=6,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.effective_params["fade"], 5)
        self.assertEqual(r.effective_params["clarity"], 4)
        self.assertEqual(r.effective_params["sharpness"], 6)

    def test_73_76c_pp_off_and_log_off_allows_creative_look_in_sq(self) -> None:
        r = p346.simulate_creative_look_params_pp_log_override_and_soft_skin_dormancy_hil(
            shoot_mode="S&Q",
            creative_look="NT",
            contrast=-3,
            clarity=2,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.effective_creative_look, "NT")
        self.assertTrue(r.sharpness_range_locked_movie_sq)

    def test_74_76c_invalid_inputs_raise_stage76_error(self) -> None:
        for bad in (
            dict(body_profile="FX30"),
            dict(fw_version="9.00"),
            dict(shoot_mode="Timelapse"),
            dict(creative_look="Custom Look 7"),
            dict(picture_profile="PP12"),
            dict(log_shooting="S-Log3"),
            dict(hlg_still_image="Auto"),
            dict(soft_skin_effect_requested="Max"),
            dict(fx6_base_look="Cinematic"),
            dict(fade=True),
        ):
            with self.assertRaises(p346.Stage76Phase346Error, msg=str(bad)):
                p346.simulate_creative_look_params_pp_log_override_and_soft_skin_dormancy_hil(**bad)

    # ------------------------------------------------------------------
    # Sub-Model 76D: Playback [Delete]/[Protect]/[Recover Image DB] & Slot 1 EROFS=30 (Tests 75..88)
    # ------------------------------------------------------------------

    def test_75_76d_delete_all_6_scopes_on_slot2_skips_protected_and_couples_proxy(self) -> None:
        self.assertEqual(len(p346.VALID_DELETE_SCOPES), 6)
        for scope in p346.VALID_DELETE_SCOPES:
            r = p346.simulate_delete_protect_recover_db_and_slot1_erofs_firewall_hil(
                operation="delete",
                target_slot="Slot 2",
                delete_scope=scope,
                protected_count=2,
                unprotected_count=5,
                has_coupled_proxy=True,
            )
            self.assertTrue(r.admitted, scope)
            self.assertEqual(r.protected_files_skipped, 2)
            self.assertEqual(r.deleted_main_files, 5)
            self.assertEqual(r.deleted_proxy_files, 5)
            self.assertTrue(r.proxy_coupled_atomically)
            self.assertEqual(r.slot1_data_sector_writes, 0)

    def test_76_76d_delete_confirm_and_pressing_twice_reset_immune_and_hazard_flag(self) -> None:
        r_reset = p346.simulate_delete_protect_recover_db_and_slot1_erofs_firewall_hil(
            operation="configure_playback",
            delete_confirm='"Delete" first',
            delete_pressing_twice="On",
            camera_settings_reset_applied=True,
        )
        self.assertTrue(r_reset.admitted)
        self.assertEqual(r_reset.effective_delete_confirm, '"Delete" first')
        self.assertEqual(r_reset.effective_delete_pressing_twice, "On")
        self.assertTrue(r_reset.instant_unconfirmed_delete_hazard)
        self.assertFalse(r_reset.playback_config_resettable)

        r_init = p346.simulate_delete_protect_recover_db_and_slot1_erofs_firewall_hil(
            operation="configure_playback",
            delete_confirm='"Delete" first',
            delete_pressing_twice="On",
            initialize_applied=True,
        )
        self.assertTrue(r_init.admitted)
        self.assertEqual(r_init.effective_delete_confirm, '"Cancel" first')
        self.assertEqual(r_init.effective_delete_pressing_twice, "Off")
        self.assertFalse(r_init.instant_unconfirmed_delete_hazard)

    def test_77_76d_protect_coupled_proxy_and_copy_does_not_copy_protect(self) -> None:
        self.assertEqual(len(p346.VALID_PROTECT_SCOPES), 8)
        r_prot = p346.simulate_delete_protect_recover_db_and_slot1_erofs_firewall_hil(
            operation="protect",
            target_slot="Slot 2",
            protect_scope="All in this Folder",
            has_coupled_proxy=True,
        )
        self.assertTrue(r_prot.admitted)
        self.assertTrue(r_prot.proxy_coupled_atomically)
        self.assertFalse(r_prot.copy_preserves_protect)

    def test_78_76d_recover_image_db_slot2_rewrites_avf_info_clears_ftp_and_immune_to_reset_init(self) -> None:
        r = p346.simulate_delete_protect_recover_db_and_slot1_erofs_firewall_hil(
            operation="recover_image_db",
            target_slot="Slot 2",
            battery_percent=50,
            camera_settings_reset_applied=True,
            initialize_applied=True,
        )
        self.assertTrue(r.admitted)
        self.assertTrue(r.avf_info_rewritten)
        self.assertTrue(r.ftp_transfer_status_cleared)
        self.assertTrue(r.media_files_preserved)
        self.assertTrue(r.recover_db_unaffected_by_reset_and_init)
        self.assertEqual(r.slot1_data_sector_writes, 0)
        self.assertFalse(r.slot1_avf_info_mutated)

    def test_79_76d_recover_image_db_battery_below_20pct_blocked_eperm(self) -> None:
        r = p346.simulate_delete_protect_recover_db_and_slot1_erofs_firewall_hil(
            operation="recover_image_db",
            target_slot="Slot 2",
            battery_percent=19,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, 1)
        self.assertFalse(r.avf_info_rewritten)
        self.assertFalse(r.ftp_transfer_status_cleared)

    def test_80_76d_display_media_info_40000_cap_and_zero_writes_on_slot1(self) -> None:
        r_cap = p346.simulate_delete_protect_recover_db_and_slot1_erofs_firewall_hil(
            operation="display_media_info",
            target_slot="Slot 1",
            raw_remaining_stills=62_500,
        )
        self.assertTrue(r_cap.admitted)
        self.assertEqual(r_cap.displayed_remaining_stills, 40_000)
        self.assertTrue(r_cap.still_cap_40000_applied)
        self.assertEqual(r_cap.slot1_data_sector_writes, 0)
        self.assertFalse(r_cap.slot1_avf_info_mutated)

        r_under = p346.simulate_delete_protect_recover_db_and_slot1_erofs_firewall_hil(
            operation="display_media_info",
            target_slot="Slot 1",
            raw_remaining_stills=12_345,
        )
        self.assertTrue(r_under.admitted)
        self.assertEqual(r_under.displayed_remaining_stills, 12_345)
        self.assertFalse(r_under.still_cap_40000_applied)

    def test_81_76d_tier0_slot1_erofs_30_blocks_delete_protect_and_recover_db(self) -> None:
        for op in ("delete", "protect", "recover_image_db"):
            r = p346.simulate_delete_protect_recover_db_and_slot1_erofs_firewall_hil(
                operation=op,
                target_slot="Slot 1",
                battery_percent=90,
            )
            self.assertFalse(r.admitted, op)
            self.assertEqual(r.errno_code, 30, op)
            self.assertTrue(r.slot1_erofs_triggered, op)
            self.assertEqual(r.slot1_data_sector_writes, 0, op)
            self.assertFalse(r.slot1_avf_info_mutated, op)
            self.assertEqual(r.deleted_main_files, 0, op)
            self.assertEqual(r.deleted_proxy_files, 0, op)
            self.assertFalse(r.avf_info_rewritten, op)

    def test_82_76d_fx6_lock_clip_delete_clip_and_restore_media_write_protected_erofs(self) -> None:
        for fx6_op in ("Lock/Unlock Clip", "Delete Clip", "Restore Media(A)", "Restore Media(B)"):
            r_blk = p346.simulate_delete_protect_recover_db_and_slot1_erofs_firewall_hil(
                body_profile="ILME-FX6",
                fw_version="6.01",
                target_slot="Slot 2",
                fx6_operation=fx6_op,
                fx6_media_write_protected=True,
            )
            self.assertFalse(r_blk.admitted, fx6_op)
            self.assertEqual(r_blk.errno_code, 30)
            self.assertEqual(r_blk.fx6_error_token, "ng_write_protected")
            self.assertFalse(r_blk.avf_info_rewritten)

            r_s1 = p346.simulate_delete_protect_recover_db_and_slot1_erofs_firewall_hil(
                body_profile="ILME-FX6",
                fw_version="6.01",
                target_slot="Slot 1",
                fx6_operation=fx6_op,
            )
            self.assertFalse(r_s1.admitted, fx6_op)
            self.assertEqual(r_s1.errno_code, 30)
            self.assertEqual(r_s1.slot1_data_sector_writes, 0)

    def test_83_76d_fx6_restore_media_b_on_slot2_succeeds_when_unprotected(self) -> None:
        r = p346.simulate_delete_protect_recover_db_and_slot1_erofs_firewall_hil(
            body_profile="ILME-FX6",
            fw_version="6.01",
            target_slot="Slot 2",
            fx6_operation="Restore Media(B)",
            fx6_media_write_protected=False,
        )
        self.assertTrue(r.admitted)
        self.assertTrue(r.avf_info_rewritten)
        self.assertEqual(r.slot1_data_sector_writes, 0)

    def test_84_76d_fx6_media_status_read_only_even_on_slot1(self) -> None:
        r = p346.simulate_delete_protect_recover_db_and_slot1_erofs_firewall_hil(
            body_profile="ILME-FX6",
            fw_version="6.01",
            target_slot="Slot 1",
            fx6_operation="Media Status",
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.slot1_data_sector_writes, 0)

    def test_85_76d_delete_without_coupled_proxy_sets_proxy_deleted_0(self) -> None:
        r = p346.simulate_delete_protect_recover_db_and_slot1_erofs_firewall_hil(
            operation="delete",
            target_slot="Slot 2",
            unprotected_count=3,
            has_coupled_proxy=False,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.deleted_main_files, 3)
        self.assertEqual(r.deleted_proxy_files, 0)

    def test_86_76d_recover_db_battery_exactly_20_percent_succeeds(self) -> None:
        r = p346.simulate_delete_protect_recover_db_and_slot1_erofs_firewall_hil(
            operation="recover_image_db",
            target_slot="Slot 2",
            battery_percent=20,
        )
        self.assertTrue(r.admitted)
        self.assertTrue(r.avf_info_rewritten)

    def test_87_76d_recover_db_fails_closed_even_under_low_battery_on_slot1(self) -> None:
        r = p346.simulate_delete_protect_recover_db_and_slot1_erofs_firewall_hil(
            operation="recover_image_db",
            target_slot="Slot 1",
            battery_percent=100,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, 30)
        self.assertEqual(r.slot1_data_sector_writes, 0)

    def test_88_76d_invalid_inputs_raise_stage76_error(self) -> None:
        for bad in (
            dict(body_profile="FX30"),
            dict(fw_version="9.00"),
            dict(operation="format"),
            dict(target_slot="Slot 3"),
            dict(delete_scope="Everything"),
            dict(protect_scope="Everything"),
            dict(delete_confirm="Never"),
            dict(delete_pressing_twice="Auto"),
            dict(protected_count=-1),
            dict(unprotected_count=-1),
            dict(battery_percent=101),
            dict(raw_remaining_stills=-1),
            dict(fx6_operation="Format"),
        ):
            with self.assertRaises(p346.Stage76Phase346Error, msg=str(bad)):
                p346.simulate_delete_protect_recover_db_and_slot1_erofs_firewall_hil(**bad)

    # ------------------------------------------------------------------
    # Milestone, Determinism, CLI & Suite Stage 76 Wiring (Tests 89..96)
    # ------------------------------------------------------------------

    def test_89_milestone_probe_exact_fields(self) -> None:
        probe = p346._build_stage76_milestone_probe()
        self.assertEqual(probe["phase_number"], 346)
        self.assertEqual(probe["stage_index"], 76)
        self.assertEqual(probe["stage_total"], 76)
        self.assertEqual(probe["milestone"], "76/76")
        self.assertTrue(probe["is_76th_stage_milestone"])
        self.assertEqual(probe["wave"], "Wave-66")
        self.assertEqual(probe["fx3_target_version"], "Ver. 7.02")
        self.assertEqual(probe["fx6_comparison_version"], "Ver. 6.01")

    def test_90_pillar_results_all_passed_in_clean_room(self) -> None:
        rep = p346.run_phase346_drive_focusbracket_shutter_efcs_creativelook_recoverdb_coemulation(
            force_clean_room=True
        )
        for pillar_key in (
            "pillar_a_drive_mode_cont_bracket_focus_bracket_hil",
            "pillar_b_shutter_type_xsync_efcs_long_exp_high_iso_nr_hil",
            "pillar_c_creative_look_params_pp_log_soft_skin_hil",
            "pillar_d_delete_protect_recover_db_slot1_erofs_hil",
        ):
            self.assertTrue(rep[pillar_key]["passed"], pillar_key)

    def test_91_stage76_wrapper_and_suite_fast_determinism(self) -> None:
        s76 = suite.run_stage76_realhw_drive_focusbracket_shutter_efcs_creativelook_recoverdb_hil(
            suite.CoEmulationConfig(force_clean_room=True)
        )
        self.assertEqual(
            s76["stage"],
            "stage76_realhw_drive_focusbracket_shutter_efcs_creativelook_recoverdb_hil",
        )
        self.assertEqual(s76["schema"], p346.SCHEMA_ID)
        self.assertEqual(s76["phase_number"], 346)
        self.assertEqual(s76["milestone"], "76/76")
        self.assertTrue(s76["is_76th_stage_milestone"])
        self.assertTrue(s76["all_checks_passed"])
        self.assertEqual(len(s76["phase346_audit_digest_sha256"]), 64)

        cfg = suite.CoEmulationConfig(**_fast_suite_kwargs())
        r1 = suite.run_fx3_vm_coemulation_suite(cfg)
        r2 = suite.run_fx3_vm_coemulation_suite(cfg)
        self.assertTrue(r1["all_checks_passed"])
        self.assertEqual(r1["audit_digest_sha256"], r2["audit_digest_sha256"])

    def test_92_standalone_and_suite_cli_help_percent_escaping_and_flags(self) -> None:
        proc1 = subprocess.run(
            [
                sys.executable,
                "-B",
                str(
                    FX3_VM_DIR
                    / "realhw_drive_focusbracket_shutter_efcs_creativelook_recoverdb_coemulator.py"
                ),
                "--help",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc1.returncode, 0, proc1.stderr)
        self.assertIn("100%", proc1.stdout)
        self.assertIn("76/76", proc1.stdout)

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
        self.assertIn("76/76 Full-Board Stages", proc2.stdout)
        self.assertIn("--include-stage76", proc2.stdout)
        self.assertIn("--skip-stage76", proc2.stdout)
        self.assertIn("--no-include-stage76", proc2.stdout)
        self.assertIn("--skip-phase346", proc2.stdout)

    def test_93_standalone_cli_summary_json_and_no_hardcoded_python_path(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = p346.main(["--self-test", "--clean-room", "--summary"])
        self.assertEqual(rc, 0)
        self.assertIn("[PASS] Phase 346 Stage 76 (76/76 Stages)", buf.getvalue())

        buf_json = io.StringIO()
        with contextlib.redirect_stdout(buf_json):
            rc2 = p346.main(["--self-test", "--clean-room", "--json"])
        self.assertEqual(rc2, 0)
        parsed = json.loads(buf_json.getvalue())
        self.assertEqual(parsed["milestone"], "76/76")
        self.assertTrue(parsed["is_76th_stage_milestone"])
        self.assertTrue(parsed["all_checks_passed"])
        self.assertNotIn("\\x7fELF", buf_json.getvalue())

        mod_src = (
            FX3_VM_DIR
            / "realhw_drive_focusbracket_shutter_efcs_creativelook_recoverdb_coemulator.py"
        ).read_text(encoding="utf-8")
        tst_src = Path(__file__).read_text(encoding="utf-8")
        forbidden = "/" + "usr/bin/" + "python3"
        self.assertNotIn(forbidden, mod_src)
        self.assertNotIn(forbidden, tst_src)

    def test_94_suite_default_config_enables_stage76_and_full_run_has_76_stages(self) -> None:
        cfg = suite.CoEmulationConfig()
        self.assertTrue(
            cfg.include_phase346_realhw_drive_focusbracket_shutter_efcs_creativelook_recoverdb_hil
        )
        self.assertTrue(cfg.include_stage76)
        self.assertTrue(
            cfg.stage76_realhw_drive_focusbracket_shutter_efcs_creativelook_recoverdb_hil
        )

        t0 = time.monotonic()
        rep = suite.run_fx3_vm_coemulation_suite(cfg)
        elapsed = time.monotonic() - t0
        self.assertTrue(rep["all_checks_passed"])
        stage_keys = [k for k in rep if re.match(r"^stage\d+_", k)]
        self.assertGreaterEqual(len(stage_keys), 76)
        s76 = rep["stage76_realhw_drive_focusbracket_shutter_efcs_creativelook_recoverdb_hil"]
        self.assertTrue(s76["all_checks_passed"])
        self.assertTrue(s76["is_76th_stage_milestone"])
        self.assertEqual(s76["milestone"], "76/76")
        self.assertEqual(s76["phase_number"], 346)
        max_elapsed = 30.0 if IS_CI else 15.0
        self.assertLess(elapsed, max_elapsed)

    def test_95_suite_skip_flags_summary_cli_and_tamper_detection(self) -> None:
        for flag in ("--skip-stage76", "--no-include-stage76", "--skip-phase346"):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = suite.main([*_FAST_CLI_FLAGS, flag, "--json"])
            self.assertEqual(rc, 0)
            data = json.loads(buf.getvalue())
            self.assertNotIn(
                "stage76_realhw_drive_focusbracket_shutter_efcs_creativelook_recoverdb_hil",
                data,
            )
            self.assertFalse(data["config"]["include_stage76"])

        buf_sum = io.StringIO()
        with contextlib.redirect_stdout(buf_sum):
            rc_sum = suite.main([*_FAST_CLI_FLAGS, "--include-stage76", "--summary"])
        self.assertEqual(rc_sum, 0)
        self.assertIn(
            "realhw_drive_focusbracket_shutter_efcs_creativelook_recoverdb_hil=CLEAN_ROOM_SYNTHETIC("
            "m76=76/76,fps=10,fbrk=0,shut=2,xsync=1/250,cl=10+6,sse=0/0,s1_wr=0,emmc_wr=0)",
            buf_sum.getvalue(),
        )

        for attr, val in (
            ("IS_76TH_STAGE_MILESTONE", False),
            ("STILL_CONT_HI_PLUS_MAX_FPS", 12),
            ("DORMANT_FOCUS_BRACKET_EXPOSED_EVENTS", 1),
            ("FX6_STILL_DRIVE_MODE_EXPOSED_EVENTS", 1),
            ("SHUTTER_TYPE_ACTIVE_OPTIONS_COUNT", 3),
            ("DORMANT_SHUTTER_TYPE_AUTO_EXPOSED_EVENTS", 1),
            ("FLASH_X_SYNC_MAX_SPEED_DENOM", 320),
            ("E_FRONT_CURTAIN_TYPO_MATCHED", False),
            ("E_FRONT_CURTAIN_RESET_WIPE_EVENTS", 1),
            ("CREATIVE_LOOK_CLARITY_FADE_SHARPNESS_MAX", 10),
            ("FX3_SOFT_SKIN_EFFECT_EXPOSED_EVENTS", 1),
            ("FX6_SOFT_SKIN_EFFECT_EXPOSED_EVENTS", 1),
            ("RECOVER_DB_SLOT1_EROFS_BYPASS_EVENTS", 1),
            ("DELETE_OR_PROTECT_SLOT1_EROFS_BYPASS_EVENTS", 1),
            ("SLOT1_DATA_SECTOR_WRITES", 1),
            ("SLOT1_AVF_INFO_MUTATED", True),
            ("RAW_FIRMWARE_BYTES_LEAKED", 4),
            ("CP_MUTATION_BYTES", 4),
        ):
            with unittest.mock.patch.object(p346, attr, val):
                rep = suite.run_fx3_vm_coemulation_suite(
                    suite.CoEmulationConfig(**_fast_suite_kwargs())
                )
                self.assertFalse(rep["all_checks_passed"], attr)

    def test_96_all_zero_and_boolean_redlines_verified_across_4_modes(self) -> None:
        clean_rep = p346.run_phase346_drive_focusbracket_shutter_efcs_creativelook_recoverdb_coemulation(
            force_clean_room=True
        )
        red = clean_rep["redlines"]
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
            "dormant_focus_bracket_exposed_events",
            "fx6_still_drive_mode_exposed_events",
            "dro_bracket_hlg_bypass_events",
            "dormant_shutter_type_auto_exposed_events",
            "apsc_1_320_xsync_spoof_events",
            "e_front_curtain_reset_wipe_events",
            "eshutter_5lock_bypass_events",
            "dormant_high_iso_nr_high_exposed_events",
            "high_iso_nr_arw_mutation_events",
            "creative_look_pp_log_hlg_override_bypass_events",
            "fx3_soft_skin_effect_exposed_events",
            "fx6_soft_skin_effect_exposed_events",
            "playback_config_reset_wipe_events",
            "recover_db_reset_or_init_wipe_events",
            "recover_db_slot1_erofs_bypass_events",
            "delete_or_protect_slot1_erofs_bypass_events",
            "proxy_decoupled_orphan_events",
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
            "e_front_curtain_typo_matched",
            "not_displayng_typo_matched",
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

        env_rep = p346.run_phase346_drive_focusbracket_shutter_efcs_creativelook_recoverdb_coemulation(
            env={p346.ENV_FORCE_CLEAN_ROOM: "1"}
        )
        cr_test_rep = p346.run_phase346_drive_focusbracket_shutter_efcs_creativelook_recoverdb_coemulation(
            env={p346.ENV_CLEAN_ROOM_TEST: "1"}
        )
        with unittest.mock.patch.object(p346, "resolve_mac_work_root", return_value=None):
            none_rep = p346.run_phase346_drive_focusbracket_shutter_efcs_creativelook_recoverdb_coemulation(
                env={}
            )
        for r in (env_rep, cr_test_rep, none_rep):
            self.assertTrue(r["all_checks_passed"])
            self.assertEqual(r["source_mode"], p346.SOURCE_MODE_CLEAN_ROOM)
            self.assertEqual(r["audit_digest_sha256"], clean_rep["audit_digest_sha256"])


if __name__ == "__main__":
    unittest.main()
