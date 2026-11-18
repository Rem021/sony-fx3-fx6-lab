#!/usr/bin/env python3
"""Unit tests for Phase 339 (Stage 74 — 74/74 VM HIL Stages Milestone!):
Real-Hardware `ILME-FX3 Ver. 7.02` vs `ILME-FX6 Ver. 6.01` Wave-64:
- 74A: `[Breathing Comp.]` (`Ver. 3.00+`, `Off` default / `On`, **Resettable**
  unlike Reset-immune `Shading`/`Chromatic`/`Distortion Comp.`), disabled in
  Still, Movie `119.88p/100p`, `S&Q >= 100/120fps` (active `<100/120fps` on FX3
  vs disabled across ALL `S&Q` on FX6!), HDMI `RAW Output`, TC
  `SEL14TC`/`SEL20TC`, `SEL100F28GM` macro `0.57m-1.0m`, third-party lenses,
  Digital Zoom & Auto Framing, and Catalyst Prepare-only (`Distortion Comp.=
  Auto` required; free `Catalyst Browse` unsupported) vs `FX6` `Technical >
  Lens > Breathing Compensation` (`Auto`/`Off`, `Distortion=Off`, ALL S&Q/RAW
  locked),
- 74B: Movie `[File Settings]` (**Reset-immune**, `PRIVATE/M4ROOT/CLIP/*.MP4`):
  `File Number` (`Series`/`Reset` + `Series Counter Reset` `max+1`), `File Name
  Format` (`Standard`, `Cam ID + Reel#` `YYMMDD` + `C999 -> D001` filename
  position rollover without mutating menu setting + `Camera ID` change
  resetting `Reel#` whereas `File Number = Reset` preserves `Reel#`, `Title`
  `37`-char max default `"C"`, `Date+Title`/`Title+Date` `YYYYMMDD`), `SDHC`
  (`FAT32 <=32GB`) forced `Standard` + `4 GB` split + no `Simult. Recording`
  with `exFAT`, and `Slot 1` Tier-0 `EROFS=30` vs `FX6` `TC/Media > Clip Name
  Format` (`4..46` char `nnn_` prefix, `/XDROOT/Clip/*.MXF`),
- 74C: `[Copyright Info]` (`46`-char `Set Photographer`/`Set Copyright`,
  `Write Copyright Info` `Off` default, Still-only EXIF) & `[Write Serial
  Number]` (`BKID_APP_setting_write_serial_number_still_movie` active across
  Still + Movie!) — **ALL 5 items Reset-immune (`Not available`, Round-57
  errata fix!)**, `[Copyright Info]` excluded from `CAMSET*.DAT` whereas `[Write
  Serial Number]` toggle is NOT excluded, zero PII/serial leaked, `Slot 1`
  `EROFS=30` vs `FX6` lens serial tracking (`0..5`), and
- 74D: `Setup -> [Power Setting Option]` (`Power Save Start Time` 6 active steps
  `Off/30/5[default]/2/1 Min/10 Sec` vs 5 dormant steps + 9 official
  auto-bypass conditions, `Auto Power OFF Temp.` `Standard`/`High` tripod
  warning, **100% dormant `[Power Save by Monitor]`**
  `BKID_APP_setting_monitor_power_linkage`) + `[NTSC/PAL Selector]`
  (Reset-immune, auto-reboot, `Running on NTSC./PAL.`, `PAL` disables `23.98p`
  & `DF`, dual-generation UXC format prompt trap -> Tier-0 `Slot 1` `EROFS=30`
  firewall blocking SD-Erase/TRIM) vs `FX6` `Project > Rec Format > Frequency`
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
import realhw_breathing_camid_copyright_powersave_ntsc_pal_coemulator as p339  # noqa: E402

IS_CI = os.environ.get("GITHUB_ACTIONS", "").lower() == "true"


def _fast_suite_kwargs(**overrides: object) -> dict:
    """Fast config skipping unrelated optional stages 4..73 for Stage 74 isolation tests."""
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
]


class TestRealHwStage74BreathingCamidCopyrightPowerSaveNtscPal(unittest.TestCase):
    # ------------------------------------------------------------------
    # Donor Audit, Bounded O_RDONLY & 4-Mode Fallback Tests (Tests 01..14)
    # ------------------------------------------------------------------

    def test_01_milestone_constants_74_of_74(self) -> None:
        self.assertEqual(p339.PHASE_NUMBER, 339)
        self.assertEqual(p339.STAGE_INDEX, 74)
        self.assertEqual(p339.STAGE_TOTAL, 74)
        self.assertEqual(p339.MILESTONE_LABEL, "74/74")
        self.assertTrue(p339.IS_74TH_STAGE_MILESTONE)
        self.assertEqual(len(p339.DONOR_RELPATHS), 18)
        self.assertEqual(len(p339.EXPECTED_DONOR_BYTES), 18)
        self.assertEqual(len(p339.EXPECTED_COMPACT_DONOR_SHA256), 15)
        self.assertEqual(len(p339.EXPECTED_LARGE_HEAD4K_SHA256), 3)
        self.assertEqual(len(p339.LARGE_DONOR_WINDOWS), 3)

    def test_02_hard_safety_redlines_locked(self) -> None:
        self.assertTrue(p339.P8_CP_MUTATION_FORBIDDEN)
        self.assertTrue(p339.CNFLASHA_USERSPACE_WRITE_BLOCKED)
        self.assertFalse(p339.PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(p339.EMMC_WRITES_AUTHORIZED)
        self.assertFalse(p339.CROSS_MODEL_FLASH_AUTHORIZED)
        self.assertFalse(p339.HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        self.assertFalse(p339.OVERALL_READY_FOR_HARDWARE_ATTACH)
        self.assertFalse(p339.ISP_WRITE_AUTHORIZED)
        self.assertFalse(p339.SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(p339.EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        self.assertFalse(p339.SLOT1_AVF_INFO_MUTATED)
        self.assertEqual(p339.BREATHING_COMP_HFR_THRESHOLD_FPS, 100.0)
        self.assertFalse(p339.CATALYST_BROWSE_BREATHING_SUPPORTED)
        self.assertEqual(p339.MOVIE_FILE_TITLE_MAX_CHARS, 37)
        self.assertEqual(p339.SDHC_FORCED_SPLIT_GB, 4)
        self.assertEqual(p339.FX6_CLIP_TITLE_PREFIX_MIN_CHARS, 4)
        self.assertEqual(p339.FX6_CLIP_TITLE_PREFIX_MAX_CHARS, 46)
        self.assertEqual(p339.COPYRIGHT_MAX_CHARS, 46)
        self.assertEqual(p339.POWER_SAVE_ACTIVE_STEPS_COUNT, 6)
        self.assertEqual(p339.POWER_SAVE_BYPASS_CONDITIONS_COUNT, 9)
        self.assertEqual(p339.SLOT1_DATA_SECTOR_WRITES, 0)
        self.assertEqual(p339.EMMC_NFLASHA_WRITE_COUNT, 0)
        self.assertEqual(p339.RAW_FIRMWARE_BYTES_LEAKED, 0)

    def test_03_clean_room_test_mode_both_env_vars(self) -> None:
        self.assertFalse(p339.clean_room_test_mode(env={}))
        self.assertTrue(p339.clean_room_test_mode(env={p339.ENV_FORCE_CLEAN_ROOM: "1"}))
        self.assertTrue(p339.clean_room_test_mode(env={p339.ENV_CLEAN_ROOM_TEST: "1"}))
        self.assertTrue(p339.clean_room_test_mode(force_clean_room=True, env={}))
        self.assertFalse(
            p339.clean_room_test_mode(
                force_clean_room=False,
                env={p339.ENV_FORCE_CLEAN_ROOM: "1", p339.ENV_CLEAN_ROOM_TEST: "1"},
            )
        )

    def test_04_resolve_mac_work_root_and_donor_paths_none_fallback(self) -> None:
        self.assertIsNone(p339.resolve_phase339_donor_paths(None))
        self.assertIsNone(
            p339.resolve_mac_work_root(
                env={p339.ENV_MAC_WORK_ROOT: p339.CLEAN_ROOM_SENTINEL_DIRNAME}
            )
        )
        self.assertIsNone(
            p339.resolve_mac_work_root(
                env={p339.ENV_MAC_ROOT: p339.CLEAN_ROOM_SENTINEL_DIRNAME}
            )
        )
        with tempfile.TemporaryDirectory() as td:
            with unittest.mock.patch.object(p339, "DEFAULT_REPO_ROOT", Path(td)):
                with unittest.mock.patch.object(p339, "LEGACY_MAC_ROOT", Path(td) / "none"):
                    self.assertIsNone(p339.resolve_mac_work_root(env={}))
                    self.assertIsNone(p339.resolve_phase339_donor_paths(None, env={}))
                    rep = p339.run_phase339_breathing_camid_copyright_powersave_ntsc_pal_coemulation(
                        env={}
                    )
                    self.assertTrue(rep["all_checks_passed"])
                    self.assertEqual(rep["source_mode"], p339.SOURCE_MODE_CLEAN_ROOM)
                    self.assertEqual(rep["redlines"]["raw_firmware_bytes_leaked"], 0)

    def test_05_clean_room_donor_audit_all_18_contracts(self) -> None:
        for env_key in (p339.ENV_FORCE_CLEAN_ROOM, p339.ENV_CLEAN_ROOM_TEST):
            audit = p339.inspect_phase339_donors(env={env_key: "1"})
            self.assertEqual(audit.source_mode, p339.SOURCE_MODE_CLEAN_ROOM)
            self.assertEqual(audit.access_mode, p339.DONOR_ACCESS_MODE)
            self.assertEqual(audit.donor_files_inspected, 18)
            self.assertEqual(audit.compact_donors_verified, 15)
            self.assertEqual(audit.large_donors_verified, 3)
            self.assertTrue(audit.all_contracts_verified)
            self.assertEqual(audit.raw_firmware_bytes_leaked, 0)

    def test_06_local_donor_o_rdonly_cold_audit_under_200ms(self) -> None:
        if p339.resolve_mac_work_root() is None:
            self.skipTest("Local Mac/work donors unavailable in clean-room environment")
        p339._DONOR_AUDIT_CACHE.clear()
        t0 = time.perf_counter()
        audit = p339.inspect_phase339_donors(force_clean_room=False)
        elapsed_s = time.perf_counter() - t0
        self.assertEqual(audit.source_mode, p339.SOURCE_MODE_LOCAL_DONOR)
        self.assertEqual(audit.donor_files_inspected, 18)
        self.assertEqual(audit.compact_donors_verified, 15)
        self.assertEqual(audit.large_donors_verified, 3)
        self.assertTrue(audit.all_contracts_verified)
        self.assertEqual(audit.raw_firmware_bytes_leaked, 0)
        self.assertLess(elapsed_s, 0.20)

    def test_07_compact_donor_tokens_across_15_files_en_sc_tc_ja_fx6(self) -> None:
        self.assertEqual(p339.EXPECTED_DONOR_BYTES["fx3_string_en_f"], 373_820)
        self.assertEqual(p339.EXPECTED_DONOR_BYTES["fx3_saveload"], 18_760)
        self.assertEqual(p339.EXPECTED_DONOR_BYTES["fx6_string_en"], 118_208)
        self.assertIn(b"Breathing Comp.", p339.COMPACT_DONOR_TOKENS["fx3_string_en_f"])
        self.assertIn(b"Cam ID + Reel#", p339.COMPACT_DONOR_TOKENS["fx3_string_en_f"])
        self.assertIn(b"Copyright Info", p339.COMPACT_DONOR_TOKENS["fx3_string_en_f"])
        self.assertIn(b"Write Serial Number", p339.COMPACT_DONOR_TOKENS["fx3_string_en_f"])
        self.assertIn(b"Power Save Start Time", p339.COMPACT_DONOR_TOKENS["fx3_string_en_f"])
        self.assertIn(b"Auto Power OFF Temp.", p339.COMPACT_DONOR_TOKENS["fx3_string_en_f"])
        self.assertIn(b"Power Save by Monitor", p339.COMPACT_DONOR_TOKENS["fx3_string_en_f"])
        self.assertIn(b"NTSC/PAL Selector", p339.COMPACT_DONOR_TOKENS["fx3_string_en_f"])
        self.assertIn(b"Running on NTSC.", p339.COMPACT_DONOR_TOKENS["fx3_string_en"])
        self.assertIn(b"Running on PAL.", p339.COMPACT_DONOR_TOKENS["fx3_string_en"])
        self.assertIn(b"Breathing Compensation", p339.COMPACT_DONOR_TOKENS["fx6_string_en"])
        self.assertIn(b"Clip Name Format", p339.COMPACT_DONOR_TOKENS["fx6_string_en"])
        self.assertIn(b"Frequency", p339.COMPACT_DONOR_TOKENS["fx6_string_en"])

    def test_08_bounded_window_reader_rejects_oversized_or_negative_reads(self) -> None:
        with tempfile.NamedTemporaryFile() as tf:
            tf.write(b"ABCDEFGH")
            tf.flush()
            self.assertEqual(p339._read_window_readonly_bytes(Path(tf.name), 2, 4), b"CDEF")
            with self.assertRaises(p339.Stage74Phase339Error):
                p339._read_window_readonly_bytes(Path(tf.name), 0, 4097)
            with self.assertRaises(p339.Stage74Phase339Error):
                p339._read_window_readonly_bytes(Path(tf.name), 0, 0)
            with self.assertRaises(p339.Stage74Phase339Error):
                p339._read_window_readonly_bytes(Path(tf.name), -1, 16)

    def test_09_donor_audit_detects_tampered_expected_digest(self) -> None:
        if p339.resolve_mac_work_root() is None:
            self.skipTest("Local Mac/work donors unavailable in clean-room environment")
        p339._DONOR_AUDIT_CACHE.clear()
        try:
            bad_digests = dict(p339.EXPECTED_COMPACT_DONOR_SHA256)
            bad_digests["fx3_string_en_f"] = "0" * 64
            with unittest.mock.patch.object(
                p339, "EXPECTED_COMPACT_DONOR_SHA256", bad_digests
            ):
                audit = p339.inspect_phase339_donors(force_clean_room=False)
                self.assertFalse(audit.all_contracts_verified)
                self.assertIn(
                    "digest_or_size_mismatch:fx3_string_en_f", audit.verification_notes
                )
        finally:
            p339._DONOR_AUDIT_CACHE.clear()

    def test_10_json_output_contains_zero_raw_firmware_bytes(self) -> None:
        rep = p339.run_phase339_breathing_camid_copyright_powersave_ntsc_pal_coemulation(
            force_clean_room=True
        )
        txt = json.dumps(rep)
        self.assertNotIn("\\x7fELF", txt)
        self.assertNotIn("BK4\\x00", txt)
        self.assertEqual(rep["redlines"]["raw_firmware_bytes_leaked"], 0)

    def test_11_full_phase339_payload_passes_clean_room(self) -> None:
        rep = p339.run_phase339_breathing_camid_copyright_powersave_ntsc_pal_coemulation(
            force_clean_room=True
        )
        self.assertEqual(rep["schema"], p339.SCHEMA_ID)
        self.assertEqual(rep["milestone"], "74/74")
        self.assertTrue(rep["is_74th_stage_milestone"])
        self.assertTrue(rep["all_checks_passed"])
        self.assertEqual(len(rep["audit_digest_sha256"]), 64)

    def test_12_full_phase339_payload_passes_local_donor_mode(self) -> None:
        if p339.resolve_mac_work_root() is None:
            self.skipTest("Local Mac/work donors unavailable in clean-room environment")
        rep = p339.run_phase339_breathing_camid_copyright_powersave_ntsc_pal_coemulation(
            force_clean_room=False
        )
        self.assertEqual(rep["source_mode"], p339.SOURCE_MODE_LOCAL_DONOR)
        self.assertTrue(rep["all_checks_passed"])
        self.assertEqual(rep["donor_audit"]["donor_files_inspected"], 18)

    def test_13_fx3_large_windows_contain_wave64_symbols(self) -> None:
        labels = {lbl for _, lbl, _ in p339.LARGE_DONOR_WINDOWS["fx3_appfw"]}
        for expected in (
            "PID_SET_BREATHING_CORRECTION",
            "PRM_HAITA_setting_lens_comp_breathing_exposure_mode",
            "BKID_APP_setting_lens_comp_breathing",
            "BKID_APP_setting_lens_comp_distortion",
            "BKID_APP_setting_xavc_s_file_name_camid_camera_id",
            "BKID_APP_update_required_xavcs_file_name_reel_number",
            "BKID_APP_setting_write_serial_number_still_movie",
            "BKID_APP_setting_still_write_serial_number",
            "BKID_APP_setting_still_write_copyright_infomation",
            "BKID_APP_setting_start_power_saving",
            "BKID_APP_setting_auto_pwr_off_temp",
            "BKID_APP_setting_monitor_power_linkage",
            "BKID_APP_setting_ntsc_pal_selector",
        ):
            self.assertIn(expected, labels)

    def test_14_fx6_and_bk4_large_windows_verified(self) -> None:
        fx6_labels = {lbl for _, lbl, _ in p339.LARGE_DONOR_WINDOWS["fx6_appfw"]}
        for expected in (
            "BKID_APP_SETTING_LENS_COMP_BREATHING",
            "BKID_APP_CAMID_CURRENT_CAMERA_ID0",
            "BKID_APP_CAMID_CURRENT_REEL_NUMBER0",
            "BKID_APP_CURRENT_LENS_SERIAL_NUMBER",
            "BKID_APP_PRESET_LENS_SERIAL_NUMBER0",
            "BKID_APP_SETTING_FREQUENCY_REC_FORMAT",
            "DIADEM_PRO",
        ):
            self.assertIn(expected, fx6_labels)
        bk4_labels = {lbl for _, lbl, _ in p339.LARGE_DONOR_WINDOWS["fx3_bk4"]}
        self.assertEqual(bk4_labels, {"BK4_HEADER", "ILME-FX3"})

    # ------------------------------------------------------------------
    # Sub-Model 74A: [Breathing Comp.] Lockouts, Reset & Catalyst (15..30)
    # ------------------------------------------------------------------

    def test_15_74a_requires_ver_300_plus_on_fx3(self) -> None:
        rej = p339.simulate_breathing_comp_lockouts_and_catalyst_hil(
            fw_version=p339.FW_VER_200,
            breathing_comp="On",
        )
        self.assertFalse(rej.admitted)
        self.assertEqual(rej.errno_code, p339.EOPNOTSUPP_ERRNO)

        ok3 = p339.simulate_breathing_comp_lockouts_and_catalyst_hil(
            fw_version=p339.FW_VER_300,
            breathing_comp="On",
        )
        self.assertTrue(ok3.admitted)
        self.assertEqual(ok3.effective_breathing_comp, "On")

    def test_16_74a_resettable_asymmetry_against_reset_immune_siblings(self) -> None:
        r = p339.simulate_breathing_comp_lockouts_and_catalyst_hil(
            breathing_comp="On",
            camera_settings_reset_applied=True,
        )
        self.assertTrue(r.admitted)
        self.assertTrue(r.breathing_resettable_via_camera_settings_reset)
        self.assertFalse(r.sibling_lens_comp_resettable)
        self.assertEqual(r.effective_breathing_comp, "Off")

    def test_17_74a_initialize_also_restores_breathing_comp_default_off(self) -> None:
        r = p339.simulate_breathing_comp_lockouts_and_catalyst_hil(
            breathing_comp="On",
            initialize_applied=True,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.effective_breathing_comp, "Off")

    def test_18_74a_movie_below_100p_and_sq_below_100fps_active_on_fx3(self) -> None:
        for mode, fps_val in (
            (p339.SHOOT_MODE_MOVIE, 23.98),
            (p339.SHOOT_MODE_MOVIE, 59.94),
            (p339.SHOOT_MODE_SQ, 1.0),
            (p339.SHOOT_MODE_SQ, 60.0),
        ):
            r = p339.simulate_breathing_comp_lockouts_and_catalyst_hil(
                shoot_mode=mode,
                fps=fps_val,
                breathing_comp="On",
            )
            self.assertTrue(r.admitted, (mode, fps_val))
            self.assertEqual(r.effective_breathing_comp, "On")

    def test_19_74a_disabled_in_still_mode_and_fx3_rejects_auto_option(self) -> None:
        rej_still = p339.simulate_breathing_comp_lockouts_and_catalyst_hil(
            shoot_mode=p339.SHOOT_MODE_STILL,
            breathing_comp="On",
        )
        self.assertFalse(rej_still.admitted)
        self.assertEqual(rej_still.errno_code, p339.EOPNOTSUPP_ERRNO)

        with self.assertRaises(p339.Stage74Phase339Error):
            p339.simulate_breathing_comp_lockouts_and_catalyst_hil(
                shoot_mode=p339.SHOOT_MODE_MOVIE,
                breathing_comp="Auto",
            )

    def test_20_74a_disabled_at_100p_11988p_and_sq_100_120_240fps(self) -> None:
        for mode, fps_val in (
            (p339.SHOOT_MODE_MOVIE, 100.0),
            (p339.SHOOT_MODE_MOVIE, 119.88),
            (p339.SHOOT_MODE_SQ, 100.0),
            (p339.SHOOT_MODE_SQ, 120.0),
            (p339.SHOOT_MODE_SQ, 200.0),
            (p339.SHOOT_MODE_SQ, 240.0),
        ):
            rej = p339.simulate_breathing_comp_lockouts_and_catalyst_hil(
                shoot_mode=mode,
                fps=fps_val,
                breathing_comp="On",
            )
            self.assertFalse(rej.admitted, (mode, fps_val))
            self.assertEqual(rej.errno_code, p339.EOPNOTSUPP_ERRNO)

    def test_21_74a_disabled_when_hdmi_raw_output_on(self) -> None:
        rej = p339.simulate_breathing_comp_lockouts_and_catalyst_hil(
            hdmi_raw_output="On",
            breathing_comp="On",
        )
        self.assertFalse(rej.admitted)
        self.assertEqual(rej.errno_code, p339.EOPNOTSUPP_ERRNO)

    def test_22_74a_disabled_with_teleconverters_sel14tc_sel20tc(self) -> None:
        for tc in ("SEL14TC", "SEL20TC"):
            rej = p339.simulate_breathing_comp_lockouts_and_catalyst_hil(
                teleconverter=tc,
                breathing_comp="On",
            )
            self.assertFalse(rej.admitted, tc)
            self.assertEqual(rej.errno_code, p339.EOPNOTSUPP_ERRNO)

    def test_23_74a_sel100f28gm_macro_range_057_100_lockout(self) -> None:
        ok_far = p339.simulate_breathing_comp_lockouts_and_catalyst_hil(
            lens_id="SEL100F28GM",
            sel100_macro_range_057_100=False,
            breathing_comp="On",
        )
        self.assertTrue(ok_far.admitted)

        rej_macro = p339.simulate_breathing_comp_lockouts_and_catalyst_hil(
            lens_id="SEL100F28GM",
            sel100_macro_range_057_100=True,
            breathing_comp="On",
        )
        self.assertFalse(rej_macro.admitted)
        self.assertEqual(rej_macro.errno_code, p339.EOPNOTSUPP_ERRNO)

    def test_24_74a_third_party_or_incompatible_lens_lockout(self) -> None:
        rej_3p = p339.simulate_breathing_comp_lockouts_and_catalyst_hil(
            third_party_or_manual_lens=True,
            breathing_comp="On",
        )
        self.assertFalse(rej_3p.admitted)
        self.assertEqual(rej_3p.errno_code, p339.EOPNOTSUPP_ERRNO)

        rej_unlisted = p339.simulate_breathing_comp_lockouts_and_catalyst_hil(
            lens_id="UNKNOWN_LENS",
            breathing_comp="On",
        )
        self.assertFalse(rej_unlisted.admitted)
        self.assertEqual(rej_unlisted.errno_code, p339.EOPNOTSUPP_ERRNO)

    def test_25_74a_ciz_compatible_vs_digital_zoom_and_auto_framing_lockout(self) -> None:
        ciz_ok = p339.simulate_breathing_comp_lockouts_and_catalyst_hil(
            breathing_comp="On",
            clear_image_zoom_ratio=1.5,
        )
        self.assertTrue(ciz_ok.admitted)
        self.assertTrue(ciz_ok.fov_narrowed_with_ciz_pipeline)

        rej_dz = p339.simulate_breathing_comp_lockouts_and_catalyst_hil(
            breathing_comp="On",
            digital_zoom_active=True,
        )
        self.assertFalse(rej_dz.admitted)
        self.assertEqual(rej_dz.errno_code, p339.EOPNOTSUPP_ERRNO)

        rej_af = p339.simulate_breathing_comp_lockouts_and_catalyst_hil(
            breathing_comp="On",
            auto_framing_active=True,
        )
        self.assertFalse(rej_af.admitted)
        self.assertEqual(rej_af.errno_code, p339.EOPNOTSUPP_ERRNO)

    def test_26_74a_catalyst_prepare_requires_off_and_distortion_auto(self) -> None:
        prep_ok = p339.simulate_breathing_comp_lockouts_and_catalyst_hil(
            breathing_comp="Off",
            distortion_comp="Auto",
            catalyst_client="Catalyst Prepare",
        )
        self.assertTrue(prep_ok.admitted)
        self.assertTrue(prep_ok.catalyst_post_comp_supported)

        prep_pl_ok = p339.simulate_breathing_comp_lockouts_and_catalyst_hil(
            breathing_comp="Off",
            distortion_comp="Auto",
            catalyst_client="Catalyst Prepare Plugin",
        )
        self.assertTrue(prep_pl_ok.admitted)
        self.assertTrue(prep_pl_ok.catalyst_post_comp_supported)

        rej_dist_off = p339.simulate_breathing_comp_lockouts_and_catalyst_hil(
            breathing_comp="Off",
            distortion_comp="Off",
            catalyst_client="Catalyst Prepare",
        )
        self.assertFalse(rej_dist_off.admitted)
        self.assertEqual(rej_dist_off.errno_code, p339.EOPNOTSUPP_ERRNO)

        rej_inbody_on = p339.simulate_breathing_comp_lockouts_and_catalyst_hil(
            breathing_comp="On",
            distortion_comp="Auto",
            catalyst_client="Catalyst Prepare",
        )
        self.assertFalse(rej_inbody_on.admitted)
        self.assertEqual(rej_inbody_on.errno_code, p339.EINVAL_ERRNO)

    def test_27_74a_free_catalyst_browse_unsupported(self) -> None:
        rej_browse = p339.simulate_breathing_comp_lockouts_and_catalyst_hil(
            breathing_comp="Off",
            distortion_comp="Auto",
            catalyst_client="Catalyst Browse",
        )
        self.assertFalse(rej_browse.admitted)
        self.assertEqual(rej_browse.errno_code, p339.EOPNOTSUPP_ERRNO)
        self.assertFalse(rej_browse.catalyst_post_comp_supported)

    def test_28_74a_fx6_auto_off_allows_movie_requires_distortion_auto(self) -> None:
        fx6_ok = p339.simulate_breathing_comp_lockouts_and_catalyst_hil(
            body_profile=p339.BODY_MODEL_FX6,
            fw_version=p339.FW_VER_601,
            shoot_mode=p339.SHOOT_MODE_MOVIE,
            fps=59.94,
            breathing_comp="Auto",
            distortion_comp="Auto",
        )
        self.assertTrue(fx6_ok.admitted)
        self.assertEqual(fx6_ok.effective_breathing_comp, "Auto")
        self.assertTrue(fx6_ok.fx6_all_sq_locked_off)

        fx6_dist_off = p339.simulate_breathing_comp_lockouts_and_catalyst_hil(
            body_profile=p339.BODY_MODEL_FX6,
            fw_version=p339.FW_VER_601,
            breathing_comp="Auto",
            distortion_comp="Off",
        )
        self.assertFalse(fx6_dist_off.admitted)
        self.assertEqual(fx6_dist_off.errno_code, p339.EOPNOTSUPP_ERRNO)

    def test_29_74a_fx6_locks_all_sq_rates_and_raw_codecs(self) -> None:
        for sq_fps in (1.0, 24.0, 60.0, 120.0):
            rej_sq = p339.simulate_breathing_comp_lockouts_and_catalyst_hil(
                body_profile=p339.BODY_MODEL_FX6,
                shoot_mode=p339.SHOOT_MODE_SQ,
                fps=sq_fps,
                breathing_comp="Auto",
            )
            self.assertFalse(rej_sq.admitted, sq_fps)
            self.assertEqual(rej_sq.errno_code, p339.EOPNOTSUPP_ERRNO)

        for codec in ("RAW", "RAW & XAVC-I"):
            rej_raw = p339.simulate_breathing_comp_lockouts_and_catalyst_hil(
                body_profile=p339.BODY_MODEL_FX6,
                breathing_comp="Auto",
                fx6_codec=codec,
            )
            self.assertFalse(rej_raw.admitted, codec)
            self.assertEqual(rej_raw.errno_code, p339.EOPNOTSUPP_ERRNO)

    def test_30_74a_invalid_inputs_raise_stage74_error(self) -> None:
        for bad_kwargs in (
            dict(body_profile="FX30"),
            dict(fw_version="9.99"),
            dict(shoot_mode="Timelapse"),
            dict(fps=0.0),
            dict(breathing_comp="High"),
            dict(distortion_comp="Manual"),
            dict(teleconverter="SEL25TC"),
            dict(hdmi_raw_output="Auto"),
            dict(clear_image_zoom_ratio=0.5),
            dict(catalyst_client="Resolve"),
            dict(fx6_codec="ProRes"),
            dict(body_profile=p339.BODY_MODEL_FX6, breathing_comp="On"),
        ):
            with self.assertRaises(p339.Stage74Phase339Error, msg=str(bad_kwargs)):
                p339.simulate_breathing_comp_lockouts_and_catalyst_hil(**bad_kwargs)

    # ------------------------------------------------------------------
    # Sub-Model 74B: Movie [File Settings], Cam ID+Reel#, SDHC & Slot-1 (31..46)
    # ------------------------------------------------------------------

    def test_31_74b_file_settings_reset_immune_vs_initialize(self) -> None:
        after_reset = p339.simulate_movie_file_settings_camid_reel_sdhc_slot1_hil(
            file_number_mode="Reset",
            file_name_format="Cam ID + Reel#",
            camera_id="B",
            previous_camera_id="B",
            reel_number=17,
            camera_position="L",
            title="STUDIO",
            camera_settings_reset_applied=True,
        )
        self.assertTrue(after_reset.admitted)
        self.assertFalse(after_reset.file_settings_resettable)
        self.assertEqual(after_reset.effective_file_number_mode, "Reset")
        self.assertEqual(after_reset.effective_file_name_format, "Cam ID + Reel#")
        self.assertEqual(after_reset.effective_camera_id, "B")
        self.assertEqual(after_reset.effective_reel_number, 17)
        self.assertEqual(after_reset.menu_camera_position_preserved, "L")
        self.assertEqual(after_reset.effective_title, "STUDIO")

        after_init = p339.simulate_movie_file_settings_camid_reel_sdhc_slot1_hil(
            file_number_mode="Reset",
            file_name_format="Cam ID + Reel#",
            camera_id="B",
            previous_camera_id="B",
            reel_number=17,
            camera_position="L",
            title="STUDIO",
            initialize_applied=True,
        )
        self.assertTrue(after_init.admitted)
        self.assertEqual(after_init.effective_file_number_mode, "Series")
        self.assertEqual(after_init.effective_file_name_format, "Standard")
        self.assertEqual(after_init.effective_camera_id, "A")
        self.assertEqual(after_init.effective_reel_number, 1)
        self.assertEqual(after_init.menu_camera_position_preserved, "C")
        self.assertEqual(after_init.effective_title, "C")

    def test_32_74b_series_counter_reset_uses_existing_max_plus_one(self) -> None:
        r = p339.simulate_movie_file_settings_camid_reel_sdhc_slot1_hil(
            file_number_mode="Series",
            series_counter_reset_applied=True,
            existing_dir_max_clip_number=28,
            next_clip_number=950,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.effective_clip_number, 29)
        self.assertEqual(r.emitted_clip_path, "PRIVATE/M4ROOT/CLIP/C0029.MP4")

    def test_33_74b_camid_reel_yymmdd_6_digits_and_c999_to_d001_rollover(self) -> None:
        r = p339.simulate_movie_file_settings_camid_reel_sdhc_slot1_hil(
            file_name_format="Cam ID + Reel#",
            camera_id="A",
            previous_camera_id="A",
            reel_number=3,
            camera_position="C",
            next_clip_number=1000,
            yymmdd="261117",
            rand2="XZ",
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.menu_camera_position_preserved, "C")
        self.assertEqual(r.emitted_filename_position_char, "D")
        self.assertEqual(r.effective_clip_number, 1)
        self.assertEqual(r.emitted_date_digits, 6)
        self.assertEqual(r.emitted_clip_path, "PRIVATE/M4ROOT/CLIP/A003D001_261117XZ.MP4")

    def test_34_74b_camera_id_change_resets_reel_number_to_001(self) -> None:
        r = p339.simulate_movie_file_settings_camid_reel_sdhc_slot1_hil(
            file_name_format="Cam ID + Reel#",
            camera_id="B",
            previous_camera_id="A",
            reel_number=55,
            yymmdd="261117",
            rand2="AB",
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.effective_reel_number, 1)
        self.assertEqual(r.emitted_clip_path, "PRIVATE/M4ROOT/CLIP/B001C001_261117AB.MP4")

    def test_35_74b_file_number_reset_preserves_reel_number(self) -> None:
        r = p339.simulate_movie_file_settings_camid_reel_sdhc_slot1_hil(
            file_number_mode="Reset",
            file_name_format="Cam ID + Reel#",
            camera_id="A",
            previous_camera_id="A",
            reel_number=42,
            next_clip_number=1,
            yymmdd="261117",
            rand2="CD",
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.effective_reel_number, 42)
        self.assertEqual(r.effective_clip_number, 1)
        self.assertEqual(r.emitted_clip_path, "PRIVATE/M4ROOT/CLIP/A042C001_261117CD.MP4")

    def test_36_74b_title_37char_max_and_default_c_on_standard_dir(self) -> None:
        t37 = "A" * 37
        r = p339.simulate_movie_file_settings_camid_reel_sdhc_slot1_hil(
            file_name_format="Title",
            title=t37,
            next_clip_number=7,
            rand2="XY",
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.title_char_len, 37)
        self.assertEqual(r.emitted_date_digits, 0)
        self.assertEqual(r.emitted_clip_path, f"PRIVATE/M4ROOT/CLIP/{t37}0007.MP4")

        rej38 = p339.simulate_movie_file_settings_camid_reel_sdhc_slot1_hil(
            file_name_format="Title",
            title="A" * 38,
        )
        self.assertFalse(rej38.admitted)
        self.assertEqual(rej38.errno_code, p339.EINVAL_ERRNO)

        rej_empty = p339.simulate_movie_file_settings_camid_reel_sdhc_slot1_hil(
            file_name_format="Title",
            title="",
        )
        self.assertFalse(rej_empty.admitted)
        self.assertEqual(rej_empty.errno_code, p339.EINVAL_ERRNO)

    def test_37_74b_date_plus_title_and_title_plus_date_use_yyyymmdd_8_digits(self) -> None:
        dt = p339.simulate_movie_file_settings_camid_reel_sdhc_slot1_hil(
            file_name_format="Date + Title",
            title="SCENE1",
            yyyymmdd="20261117",
            next_clip_number=12,
        )
        self.assertTrue(dt.admitted)
        self.assertEqual(dt.emitted_date_digits, 8)
        self.assertEqual(dt.emitted_clip_path, "PRIVATE/M4ROOT/CLIP/20261117_SCENE10012.MP4")

        td = p339.simulate_movie_file_settings_camid_reel_sdhc_slot1_hil(
            file_name_format="Title + Date",
            title="SCENE1",
            yyyymmdd="20261117",
            next_clip_number=12,
        )
        self.assertTrue(td.admitted)
        self.assertEqual(td.emitted_date_digits, 8)
        self.assertEqual(td.emitted_clip_path, "PRIVATE/M4ROOT/CLIP/SCENE1_20261117_0012.MP4")

    def test_38_74b_title_charset_rejects_disallowed_symbols(self) -> None:
        for bad_title in ("BAD/NAME", "A*B", "TEST?1", "FOO<BAR>"):
            rej = p339.simulate_movie_file_settings_camid_reel_sdhc_slot1_hil(
                file_name_format="Title",
                title=bad_title,
            )
            self.assertFalse(rej.admitted, bad_title)
            self.assertEqual(rej.errno_code, p339.EINVAL_ERRNO)

    def test_39_74b_sdhc_fat32_4gb_split_and_forced_standard_format(self) -> None:
        sdhc_ok = p339.simulate_movie_file_settings_camid_reel_sdhc_slot1_hil(
            card_type_slot2="SDHC",
            recording_slot="Slot 2",
            file_name_format="Standard",
            next_clip_number=5,
        )
        self.assertTrue(sdhc_ok.admitted)
        self.assertTrue(sdhc_ok.sdhc_4gb_split_active)
        self.assertEqual(sdhc_ok.split_chunk_limit_gb, 4)
        self.assertEqual(sdhc_ok.emitted_clip_path, "PRIVATE/M4ROOT/CLIP/C0005.MP4")

        for non_std in ("Cam ID + Reel#", "Title", "Date + Title", "Title + Date"):
            rej = p339.simulate_movie_file_settings_camid_reel_sdhc_slot1_hil(
                card_type_slot2="SDHC",
                recording_slot="Slot 2",
                file_name_format=non_std,
            )
            self.assertFalse(rej.admitted, non_std)
            self.assertEqual(rej.errno_code, p339.EOPNOTSUPP_ERRNO)

    def test_40_74b_sdhc_and_exfat_simultaneous_recording_blocked_einval(self) -> None:
        rej = p339.simulate_movie_file_settings_camid_reel_sdhc_slot1_hil(
            card_type_slot1="SDXC",
            card_type_slot2="SDHC",
            recording_slot="Simult. Recording",
            file_name_format="Standard",
        )
        self.assertFalse(rej.admitted)
        self.assertEqual(rej.errno_code, p339.EINVAL_ERRNO)

    def test_41_74b_slot1_tier0_erofs30_firewall_vs_slot2_admitted(self) -> None:
        rej_s1 = p339.simulate_movie_file_settings_camid_reel_sdhc_slot1_hil(
            recording_slot="Slot 1",
            file_name_format="Cam ID + Reel#",
            rec_triggered=True,
        )
        self.assertFalse(rej_s1.admitted)
        self.assertEqual(rej_s1.errno_code, p339.EROFS_ERRNO)
        self.assertTrue(rej_s1.slot1_erofs_triggered)
        self.assertEqual(rej_s1.slot1_data_sector_writes, 0)

        rej_sim = p339.simulate_movie_file_settings_camid_reel_sdhc_slot1_hil(
            recording_slot="Simult. Recording",
            file_name_format="Standard",
            rec_triggered=True,
        )
        self.assertFalse(rej_sim.admitted)
        self.assertEqual(rej_sim.errno_code, p339.EROFS_ERRNO)
        self.assertTrue(rej_sim.slot1_erofs_triggered)

        ok_s2 = p339.simulate_movie_file_settings_camid_reel_sdhc_slot1_hil(
            recording_slot="Slot 2",
            file_name_format="Cam ID + Reel#",
            rec_triggered=True,
        )
        self.assertTrue(ok_s2.admitted)
        self.assertFalse(ok_s2.slot1_erofs_triggered)

    def test_42_74b_fx6_clip_name_format_title_prefix_4_to_46_and_xdroot_mxf(self) -> None:
        fx6_cf = p339.simulate_movie_file_settings_camid_reel_sdhc_slot1_hil(
            body_profile=p339.BODY_MODEL_FX6,
            fw_version=p339.FW_VER_601,
            card_type_slot1="CFexpress Type A",
            recording_slot="Slot 1",
            file_name_format="Title",
            fx6_title_prefix="A" * 46,
            next_clip_number=3,
        )
        self.assertTrue(fx6_cf.admitted)
        self.assertEqual(fx6_cf.emitted_clip_path, f"/XDROOT/Clip/{'A' * 46}0003.MXF")
        self.assertTrue(fx6_cf.fx6_card_inherits_camid_reel)

        fx6_sd = p339.simulate_movie_file_settings_camid_reel_sdhc_slot1_hil(
            body_profile=p339.BODY_MODEL_FX6,
            fw_version=p339.FW_VER_601,
            card_type_slot2="SDXC",
            recording_slot="Slot 2",
            file_name_format="Title",
            fx6_title_prefix="001_",
            next_clip_number=1,
        )
        self.assertTrue(fx6_sd.admitted)
        self.assertEqual(fx6_sd.emitted_clip_path, "/PRIVATE/XDROOT/Clip/001_0001.MXF")

    def test_43_74b_fx6_camid_reel_naming_and_invalid_prefix_lengths(self) -> None:
        fx6_camid = p339.simulate_movie_file_settings_camid_reel_sdhc_slot1_hil(
            body_profile=p339.BODY_MODEL_FX6,
            fw_version=p339.FW_VER_601,
            file_name_format="Cam ID + Reel#",
            camera_id="C",
            previous_camera_id="C",
            reel_number=12,
            camera_position="R",
            next_clip_number=9,
            yymmdd="261117",
            rand2="ZZ",
        )
        self.assertTrue(fx6_camid.admitted)
        self.assertEqual(fx6_camid.emitted_clip_path, "/XDROOT/Clip/C012R009.MXF")

        for bad_pfx in ("12_", "A" * 47):
            rej = p339.simulate_movie_file_settings_camid_reel_sdhc_slot1_hil(
                body_profile=p339.BODY_MODEL_FX6,
                file_name_format="Title",
                fx6_title_prefix=bad_pfx,
            )
            self.assertFalse(rej.admitted, bad_pfx)
            self.assertEqual(rej.errno_code, p339.EINVAL_ERRNO)

    def test_44_74b_fx6_rejects_consumer_standard_and_date_title_formats(self) -> None:
        for bad_fmt in ("Standard", "Date + Title", "Title + Date"):
            rej = p339.simulate_movie_file_settings_camid_reel_sdhc_slot1_hil(
                body_profile=p339.BODY_MODEL_FX6,
                file_name_format=bad_fmt,
            )
            self.assertFalse(rej.admitted, bad_fmt)
            self.assertEqual(rej.errno_code, p339.EOPNOTSUPP_ERRNO)

    def test_45_74b_standard_vs_title_directory_and_position_preservation(self) -> None:
        r_std = p339.simulate_movie_file_settings_camid_reel_sdhc_slot1_hil(
            file_name_format="Standard",
            camera_position="L",
            next_clip_number=42,
        )
        self.assertTrue(r_std.admitted)
        self.assertEqual(r_std.emitted_clip_path, "PRIVATE/M4ROOT/CLIP/C0042.MP4")
        self.assertEqual(r_std.menu_camera_position_preserved, "L")

    def test_46_74b_invalid_inputs_raise_stage74_error(self) -> None:
        for bad_kwargs in (
            dict(body_profile="FX30"),
            dict(fw_version="8.00"),
            dict(card_type_slot1="MemoryStick"),
            dict(card_type_slot2="UHS-0"),
            dict(recording_slot="Slot 3"),
            dict(file_number_mode="Random"),
            dict(file_name_format="UUID"),
            dict(camera_id="AB"),
            dict(previous_camera_id="1"),
            dict(reel_number=0),
            dict(reel_number=1000),
            dict(camera_position="D"),
            dict(existing_dir_max_clip_number=-1),
            dict(next_clip_number=0),
            dict(yymmdd="20261117"),
            dict(yyyymmdd="261117"),
            dict(rand2="A!"),
        ):
            with self.assertRaises(p339.Stage74Phase339Error, msg=str(bad_kwargs)):
                p339.simulate_movie_file_settings_camid_reel_sdhc_slot1_hil(**bad_kwargs)

    # ------------------------------------------------------------------
    # Sub-Model 74C: [Copyright Info] 46ch, [Write Serial], CAMSET (47..60)
    # ------------------------------------------------------------------

    def test_47_74c_round57_errata_fix_all_5_items_reset_immune(self) -> None:
        r = p339.simulate_copyright_46ch_serial_camset_isolation_hil(
            shoot_mode=p339.SHOOT_MODE_STILL,
            write_copyright_info="On",
            photographer_name="P" * 46,
            copyright_name="C" * 46,
            write_serial_number="On",
            camera_settings_reset_applied=True,
        )
        self.assertTrue(r.admitted)
        self.assertTrue(r.all_5_items_reset_immune)
        self.assertEqual(r.effective_write_copyright_info, "On")
        self.assertEqual(r.effective_photographer_name, "P" * 46)
        self.assertEqual(r.effective_copyright_name, "C" * 46)
        self.assertEqual(r.effective_write_serial_number, "On")

    def test_48_74c_initialize_wipes_all_5_items_to_factory_defaults(self) -> None:
        r = p339.simulate_copyright_46ch_serial_camset_isolation_hil(
            write_copyright_info="On",
            photographer_name="JaneDoe",
            copyright_name="ACME",
            write_serial_number="On",
            initialize_applied=True,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.effective_write_copyright_info, "Off")
        self.assertEqual(r.effective_photographer_name, "")
        self.assertEqual(r.effective_copyright_name, "")
        self.assertEqual(r.effective_write_serial_number, "Off")

    def test_49_74c_write_serial_number_active_across_still_and_movie(self) -> None:
        still = p339.simulate_copyright_46ch_serial_camset_isolation_hil(
            shoot_mode=p339.SHOOT_MODE_STILL,
            write_serial_number="On",
            write_copyright_info="On",
            capture_or_record_triggered=True,
        )
        self.assertTrue(still.admitted)
        self.assertTrue(still.write_serial_active_in_still)
        self.assertTrue(still.write_serial_active_in_movie)
        self.assertTrue(still.still_exif_copyright_written)
        self.assertFalse(still.movie_exif_copyright_written)

        movie = p339.simulate_copyright_46ch_serial_camset_isolation_hil(
            shoot_mode=p339.SHOOT_MODE_MOVIE,
            write_serial_number="On",
            write_copyright_info="On",
            capture_or_record_triggered=True,
        )
        self.assertTrue(movie.admitted)
        self.assertTrue(movie.write_serial_active_in_still)
        self.assertTrue(movie.write_serial_active_in_movie)
        self.assertFalse(movie.still_exif_copyright_written)
        self.assertFalse(movie.movie_exif_copyright_written)

    def test_50_74c_photographer_and_copyright_46ch_ascii_bounds_enforced(self) -> None:
        for field in ("photographer_name", "copyright_name"):
            ok46 = p339.simulate_copyright_46ch_serial_camset_isolation_hil(**{field: "A" * 46})
            self.assertTrue(ok46.admitted, field)

            rej47 = p339.simulate_copyright_46ch_serial_camset_isolation_hil(**{field: "A" * 47})
            self.assertFalse(rej47.admitted, field)
            self.assertEqual(rej47.errno_code, p339.EINVAL_ERRNO)

            rej_nonascii = p339.simulate_copyright_46ch_serial_camset_isolation_hil(
                **{field: "版权"}
            )
            self.assertFalse(rej_nonascii.admitted, field)
            self.assertEqual(rej_nonascii.errno_code, p339.EINVAL_ERRNO)

    def test_51_74c_camset_excludes_copyright_info_but_preserves_serial_toggle_no_pii(self) -> None:
        r = p339.simulate_copyright_46ch_serial_camset_isolation_hil(
            write_copyright_info="On",
            photographer_name="SecretPhotographer",
            copyright_name="SecretStudio",
            write_serial_number="On",
            camset_export_requested=True,
            camset_target_slot="Slot 2",
        )
        self.assertTrue(r.admitted)
        self.assertTrue(r.copyright_excluded_from_camset)
        self.assertTrue(r.write_serial_toggle_in_camset)
        self.assertFalse(r.camset_contains_copyright_pii)
        self.assertFalse(r.camset_contains_body_serial_string)
        self.assertEqual(r.photographer_copyright_pii_leaked_bytes, 0)
        self.assertEqual(r.body_serial_number_leaked_bytes, 0)

    def test_52_74c_camset_excluded_groups_include_copyright_info_only(self) -> None:
        self.assertIn("Copyright Info", p339.CAMSET_EXCLUDED_GROUPS)
        self.assertNotIn("Write Serial Number", p339.CAMSET_EXCLUDED_GROUPS)

    def test_53_74c_slot1_erofs30_on_capture_and_camset_export(self) -> None:
        rej_cap = p339.simulate_copyright_46ch_serial_camset_isolation_hil(
            recording_slot="Slot 1",
            capture_or_record_triggered=True,
        )
        self.assertFalse(rej_cap.admitted)
        self.assertEqual(rej_cap.errno_code, p339.EROFS_ERRNO)
        self.assertTrue(rej_cap.slot1_erofs_triggered)
        self.assertEqual(rej_cap.slot1_data_sector_writes, 0)

        rej_camset = p339.simulate_copyright_46ch_serial_camset_isolation_hil(
            camset_export_requested=True,
            camset_target_slot="Slot 1",
        )
        self.assertFalse(rej_camset.admitted)
        self.assertEqual(rej_camset.errno_code, p339.EROFS_ERRNO)
        self.assertTrue(rej_camset.slot1_erofs_triggered)

    def test_54_74c_simultaneous_recording_blocked_by_slot1_erofs(self) -> None:
        rej = p339.simulate_copyright_46ch_serial_camset_isolation_hil(
            recording_slot="Simult. Recording",
            capture_or_record_triggered=True,
        )
        self.assertFalse(rej.admitted)
        self.assertEqual(rej.errno_code, p339.EROFS_ERRNO)
        self.assertTrue(rej.slot1_erofs_triggered)

    def test_55_74c_zero_pii_leaked_when_write_copyright_off_or_on(self) -> None:
        for state in ("Off", "On"):
            r = p339.simulate_copyright_46ch_serial_camset_isolation_hil(
                write_copyright_info=state,
                photographer_name="Anon",
                copyright_name="Corp",
                write_serial_number="On",
            )
            self.assertTrue(r.admitted, state)
            self.assertEqual(r.photographer_copyright_pii_leaked_bytes, 0)
            self.assertEqual(r.body_serial_number_leaked_bytes, 0)

    def test_56_74c_fx6_tracks_6_lens_serial_slots_without_consumer_copyright_menu(self) -> None:
        fx6 = p339.simulate_copyright_46ch_serial_camset_isolation_hil(
            body_profile=p339.BODY_MODEL_FX6,
            fw_version=p339.FW_VER_601,
        )
        self.assertTrue(fx6.admitted)
        self.assertFalse(fx6.fx6_has_consumer_copyright_menu)
        self.assertEqual(fx6.fx6_lens_serial_slots, 6)

        fx6_rej = p339.simulate_copyright_46ch_serial_camset_isolation_hil(
            body_profile=p339.BODY_MODEL_FX6,
            write_copyright_info="On",
            photographer_name="Jane",
        )
        self.assertFalse(fx6_rej.admitted)
        self.assertEqual(fx6_rej.errno_code, p339.EOPNOTSUPP_ERRNO)

    def test_57_74c_write_serial_number_toggle_persists_across_sq_mode_too(self) -> None:
        r = p339.simulate_copyright_46ch_serial_camset_isolation_hil(
            shoot_mode=p339.SHOOT_MODE_SQ,
            write_serial_number="On",
            camera_settings_reset_applied=True,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.effective_write_serial_number, "On")
        self.assertFalse(r.still_exif_copyright_written)

    def test_58_74c_capture_on_slot2_succeeds_without_erofs(self) -> None:
        r = p339.simulate_copyright_46ch_serial_camset_isolation_hil(
            recording_slot="Slot 2",
            capture_or_record_triggered=True,
            write_copyright_info="On",
            photographer_name="Operator1",
            copyright_name="Studio1",
        )
        self.assertTrue(r.admitted)
        self.assertFalse(r.slot1_erofs_triggered)
        self.assertTrue(r.still_exif_copyright_written)

    def test_59_74c_empty_names_allowed_and_zero_leak(self) -> None:
        r = p339.simulate_copyright_46ch_serial_camset_isolation_hil(
            write_copyright_info="Off",
            photographer_name="",
            copyright_name="",
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.photographer_copyright_pii_leaked_bytes, 0)

    def test_60_74c_invalid_inputs_raise_stage74_error(self) -> None:
        for bad_kwargs in (
            dict(body_profile="FX1"),
            dict(fw_version="9.00"),
            dict(shoot_mode="Burst"),
            dict(write_copyright_info="Auto"),
            dict(write_serial_number="Always"),
            dict(recording_slot="Slot 9"),
            dict(camset_target_slot="Simult. Recording"),
        ):
            with self.assertRaises(p339.Stage74Phase339Error, msg=str(bad_kwargs)):
                p339.simulate_copyright_46ch_serial_camset_isolation_hil(**bad_kwargs)

    # ------------------------------------------------------------------
    # Sub-Model 74D: Power Setting, Dormant Monitor & NTSC/PAL (61..76)
    # ------------------------------------------------------------------

    def test_61_74d_power_save_6_active_steps_and_5_min_default(self) -> None:
        self.assertEqual(
            p339.FX3_POWER_SAVE_ACTIVE_STEPS,
            ("Off", "30 Min", "5 Min", "2 Min", "1 Min", "10 Sec"),
        )
        for step in p339.FX3_POWER_SAVE_ACTIVE_STEPS:
            r = p339.simulate_power_setting_9cond_dormant_monitor_ntsc_pal_hil(
                power_save_start_time=step,
            )
            self.assertTrue(r.admitted, step)
            self.assertEqual(r.effective_power_save_start_time, step)
            self.assertEqual(r.auto_sleep_armed, step != "Off")

    def test_62_74d_dormant_power_save_steps_rejected_eopnotsupp(self) -> None:
        self.assertEqual(
            p339.DORMANT_POWER_SAVE_STEPS,
            ("20 Sec", "30 Sec", "60 Min", "240 Min", "No Limit"),
        )
        for step in p339.DORMANT_POWER_SAVE_STEPS:
            rej = p339.simulate_power_setting_9cond_dormant_monitor_ntsc_pal_hil(
                power_save_start_time=step,
            )
            self.assertFalse(rej.admitted, step)
            self.assertEqual(rej.errno_code, p339.EOPNOTSUPP_ERRNO)

    def test_63_74d_all_9_official_auto_bypass_conditions_disarm_sleep(self) -> None:
        cond_kwargs = (
            ("usb_power_supplied", dict(usb_power_supplied=True)),
            ("slideshow_playing", dict(slideshow_playing=True)),
            ("ftp_transfer_active", dict(ftp_transfer_active=True)),
            ("recording_movies", dict(recording_movies=True)),
            ("connected_to_pc", dict(connected_to_pc=True)),
            ("connected_to_tv_hdmi", dict(connected_to_tv_hdmi=True)),
            ("ir_remote_ctrl_on", dict(ir_remote_ctrl_on=True)),
            ("bluetooth_rmt_ctrl_on", dict(bluetooth_rmt_ctrl_on=True)),
            (
                "streaming_or_creators_cloud_upload",
                dict(streaming_or_creators_cloud_upload=True),
            ),
        )
        self.assertEqual(len(cond_kwargs), 9)
        for name, kw in cond_kwargs:
            r = p339.simulate_power_setting_9cond_dormant_monitor_ntsc_pal_hil(
                power_save_start_time="10 Sec",
                **kw,
            )
            self.assertTrue(r.admitted, name)
            self.assertFalse(r.auto_sleep_armed, name)
            self.assertEqual(r.power_save_bypass_reasons, (name,))

    def test_64_74d_dormant_power_save_by_monitor_100pct_rejected_on_fx3_and_fx6(self) -> None:
        for body in (p339.BODY_MODEL_FX3, p339.BODY_MODEL_FX6):
            rej = p339.simulate_power_setting_9cond_dormant_monitor_ntsc_pal_hil(
                body_profile=body,
                power_save_by_monitor_requested=True,
            )
            self.assertFalse(rej.admitted, body)
            self.assertEqual(rej.errno_code, p339.EOPNOTSUPP_ERRNO)
            self.assertFalse(rej.power_save_by_monitor_exposed)

    def test_65_74d_auto_power_off_temp_high_emits_tripod_warning(self) -> None:
        std = p339.simulate_power_setting_9cond_dormant_monitor_ntsc_pal_hil(
            auto_pwr_off_temp="Standard",
        )
        self.assertTrue(std.admitted)
        self.assertFalse(std.tripod_only_warning_emitted)

        hi = p339.simulate_power_setting_9cond_dormant_monitor_ntsc_pal_hil(
            auto_pwr_off_temp="High",
        )
        self.assertTrue(hi.admitted)
        self.assertTrue(hi.tripod_only_warning_emitted)

    def test_66_74d_setup_items_reset_immune_vs_initialize(self) -> None:
        after_reset = p339.simulate_power_setting_9cond_dormant_monitor_ntsc_pal_hil(
            power_save_start_time="10 Sec",
            auto_pwr_off_temp="High",
            tv_system="PAL",
            previous_tv_system="PAL",
            factory_default_tv_system="NTSC",
            requested_fps=50.0,
            requested_tc_format="NDF",
            camera_settings_reset_applied=True,
        )
        self.assertTrue(after_reset.admitted)
        self.assertFalse(after_reset.power_setting_resettable)
        self.assertFalse(after_reset.ntsc_pal_resettable)
        self.assertEqual(after_reset.effective_power_save_start_time, "10 Sec")
        self.assertEqual(after_reset.effective_auto_pwr_off_temp, "High")
        self.assertEqual(after_reset.effective_tv_system, "PAL")

        after_init = p339.simulate_power_setting_9cond_dormant_monitor_ntsc_pal_hil(
            power_save_start_time="10 Sec",
            auto_pwr_off_temp="High",
            tv_system="PAL",
            previous_tv_system="PAL",
            factory_default_tv_system="NTSC",
            requested_fps=50.0,
            requested_tc_format="NDF",
            initialize_applied=True,
        )
        self.assertTrue(after_init.admitted)
        self.assertEqual(after_init.effective_power_save_start_time, "5 Min")
        self.assertEqual(after_init.effective_auto_pwr_off_temp, "Standard")
        self.assertEqual(after_init.effective_tv_system, "NTSC")

    def test_67_74d_ntsc_pal_switch_triggers_auto_reboot_and_running_on_banner(self) -> None:
        to_pal = p339.simulate_power_setting_9cond_dormant_monitor_ntsc_pal_hil(
            tv_system="PAL",
            previous_tv_system="NTSC",
            factory_default_tv_system="NTSC",
            requested_fps=50.0,
            requested_tc_format="NDF",
        )
        self.assertTrue(to_pal.admitted)
        self.assertTrue(to_pal.auto_reboot_triggered)
        self.assertEqual(to_pal.boot_banner_text, "Running on PAL.")

        to_ntsc_on_pal_body = p339.simulate_power_setting_9cond_dormant_monitor_ntsc_pal_hil(
            tv_system="NTSC",
            previous_tv_system="PAL",
            factory_default_tv_system="PAL",
            requested_fps=59.94,
            requested_tc_format="DF",
        )
        self.assertTrue(to_ntsc_on_pal_body.admitted)
        self.assertTrue(to_ntsc_on_pal_body.auto_reboot_triggered)
        self.assertEqual(to_ntsc_on_pal_body.boot_banner_text, "Running on NTSC.")

        default_no_banner = p339.simulate_power_setting_9cond_dormant_monitor_ntsc_pal_hil(
            tv_system="NTSC",
            previous_tv_system="NTSC",
            factory_default_tv_system="NTSC",
        )
        self.assertFalse(default_no_banner.auto_reboot_triggered)
        self.assertEqual(default_no_banner.boot_banner_text, "")

    def test_68_74d_pal_disables_2398p_and_df_timecode_eopnotsupp(self) -> None:
        rej_2398 = p339.simulate_power_setting_9cond_dormant_monitor_ntsc_pal_hil(
            tv_system="PAL",
            requested_fps=23.98,
            requested_tc_format="NDF",
        )
        self.assertFalse(rej_2398.admitted)
        self.assertEqual(rej_2398.errno_code, p339.EOPNOTSUPP_ERRNO)
        self.assertFalse(rej_2398.fps_2398p_allowed)

        rej_df = p339.simulate_power_setting_9cond_dormant_monitor_ntsc_pal_hil(
            tv_system="PAL",
            requested_fps=25.0,
            requested_tc_format="DF",
        )
        self.assertFalse(rej_df.admitted)
        self.assertEqual(rej_df.errno_code, p339.EOPNOTSUPP_ERRNO)
        self.assertEqual(rej_df.effective_tc_format, "NDF")

    def test_69_74d_cross_system_playback_blocked(self) -> None:
        for cur_sys, clip_sys in (("PAL", "NTSC"), ("NTSC", "PAL")):
            rej = p339.simulate_power_setting_9cond_dormant_monitor_ntsc_pal_hil(
                tv_system=cur_sys,
                requested_fps=50.0 if cur_sys == "PAL" else 59.94,
                playback_clip_tv_system=clip_sys,
            )
            self.assertFalse(rej.admitted, (cur_sys, clip_sys))
            self.assertEqual(rej.errno_code, p339.EOPNOTSUPP_ERRNO)
            self.assertTrue(rej.cross_system_playback_blocked)

    def test_70_74d_slot1_erofs30_blocks_uxc_format_and_sd_erase_trim_trap(self) -> None:
        rej = p339.simulate_power_setting_9cond_dormant_monitor_ntsc_pal_hil(
            tv_system="PAL",
            previous_tv_system="NTSC",
            requested_fps=50.0,
            slot1_format_or_erase_requested=True,
        )
        self.assertFalse(rej.admitted)
        self.assertEqual(rej.errno_code, p339.EROFS_ERRNO)
        self.assertTrue(rej.legacy_format_prompt_trapped)
        self.assertTrue(rej.slot1_erofs_triggered)
        self.assertEqual(rej.slot1_data_sector_writes, 0)

    def test_71_74d_ntsc_allows_2398p_and_df_timecode(self) -> None:
        ok = p339.simulate_power_setting_9cond_dormant_monitor_ntsc_pal_hil(
            tv_system="NTSC",
            requested_fps=23.98,
            requested_tc_format="DF",
        )
        self.assertTrue(ok.admitted)
        self.assertTrue(ok.fps_2398p_allowed)
        self.assertEqual(ok.effective_tc_format, "DF")

    def test_72_74d_fx6_project_rec_format_frequency_no_format_trap(self) -> None:
        for freq in p339.FX6_FREQUENCY_OPTIONS:
            r = p339.simulate_power_setting_9cond_dormant_monitor_ntsc_pal_hil(
                body_profile=p339.BODY_MODEL_FX6,
                fw_version=p339.FW_VER_601,
                fx6_project_frequency=freq,
                fx6_previous_frequency="59.94",
            )
            self.assertTrue(r.admitted, freq)
            self.assertFalse(r.legacy_format_prompt_trapped)
            self.assertEqual(r.auto_reboot_triggered, freq != "59.94")
            self.assertEqual(r.fps_2398p_allowed, freq == "23.98")

    def test_73_74d_same_system_playback_admitted(self) -> None:
        r = p339.simulate_power_setting_9cond_dormant_monitor_ntsc_pal_hil(
            tv_system="PAL",
            requested_fps=25.0,
            playback_clip_tv_system="PAL",
        )
        self.assertTrue(r.admitted)
        self.assertFalse(r.cross_system_playback_blocked)

    def test_74_74d_fx3_power_save_steps_constant_count_verified(self) -> None:
        self.assertEqual(len(p339.FX3_POWER_SAVE_ACTIVE_STEPS), 6)
        self.assertEqual(len(p339.POWER_SAVE_9_BYPASS_CONDITIONS), 9)

    def test_75_74d_ntsc_pal_with_offline_sleep_and_9cond_combined(self) -> None:
        r = p339.simulate_power_setting_9cond_dormant_monitor_ntsc_pal_hil(
            power_save_start_time="1 Min",
            usb_power_supplied=True,
            recording_movies=True,
            tv_system="PAL",
            requested_fps=50.0,
        )
        self.assertTrue(r.admitted)
        self.assertFalse(r.auto_sleep_armed)
        self.assertEqual(r.power_save_bypass_reasons, ("usb_power_supplied", "recording_movies"))

    def test_76_74d_invalid_inputs_raise_stage74_error(self) -> None:
        for bad_kwargs in (
            dict(body_profile="FX30"),
            dict(fw_version="9.00"),
            dict(power_save_start_time="15 Min"),
            dict(auto_pwr_off_temp="Ultra"),
            dict(tv_system="SECAM"),
            dict(previous_tv_system="SECAM"),
            dict(factory_default_tv_system="SECAM"),
            dict(requested_tc_format="SMPTE"),
            dict(playback_clip_tv_system="SECAM"),
            dict(fx6_project_frequency="120"),
            dict(fx6_previous_frequency="120"),
        ):
            with self.assertRaises(p339.Stage74Phase339Error, msg=str(bad_kwargs)):
                p339.simulate_power_setting_9cond_dormant_monitor_ntsc_pal_hil(**bad_kwargs)

    # ------------------------------------------------------------------
    # Milestone, Determinism, CLI & Suite Stage 74 Wiring (Tests 77..96)
    # ------------------------------------------------------------------

    def test_77_milestone_probe_exact_fields(self) -> None:
        probe = p339._build_stage74_milestone_probe()
        self.assertEqual(probe["phase_number"], 339)
        self.assertEqual(probe["stage_index"], 74)
        self.assertEqual(probe["stage_total"], 74)
        self.assertEqual(probe["milestone"], "74/74")
        self.assertTrue(probe["is_74th_stage_milestone"])
        self.assertEqual(probe["wave"], "Wave-64")
        self.assertEqual(probe["fx3_target_version"], "Ver. 7.02")
        self.assertEqual(probe["fx6_comparison_version"], "Ver. 6.01")

    def test_78_pillar_results_all_passed_in_clean_room(self) -> None:
        rep = p339.run_phase339_breathing_camid_copyright_powersave_ntsc_pal_coemulation(
            force_clean_room=True
        )
        for pillar_key in (
            "pillar_a_breathing_comp_catalyst_prepare_hil",
            "pillar_b_movie_file_settings_camid_reel_sdhc_slot1_hil",
            "pillar_c_copyright_46ch_serial_camset_isolation_hil",
            "pillar_d_power_setting_9cond_dormant_monitor_ntsc_pal_hil",
        ):
            self.assertTrue(rep[pillar_key]["passed"], pillar_key)

    def test_79_deterministic_digest_identical_across_repeated_clean_room_runs(self) -> None:
        rep1 = p339.run_phase339_breathing_camid_copyright_powersave_ntsc_pal_coemulation(
            force_clean_room=True
        )
        rep2 = p339.run_phase339_breathing_camid_copyright_powersave_ntsc_pal_coemulation(
            force_clean_room=True
        )
        self.assertEqual(rep1["audit_digest_sha256"], rep2["audit_digest_sha256"])

    def test_80_deterministic_suite_digest_identical_across_repeated_fast_runs(self) -> None:
        cfg = suite.CoEmulationConfig(**_fast_suite_kwargs())
        r1 = suite.run_fx3_vm_coemulation_suite(cfg)
        r2 = suite.run_fx3_vm_coemulation_suite(cfg)
        self.assertEqual(r1["audit_digest_sha256"], r2["audit_digest_sha256"])

    def test_81_stage74_wrapper_output_schema_matches_suite_contract(self) -> None:
        s74 = suite.run_stage74_realhw_breathing_camid_copyright_powersave_ntsc_pal_hil(
            suite.CoEmulationConfig(force_clean_room=True)
        )
        self.assertEqual(
            s74["stage"],
            "stage74_realhw_breathing_camid_copyright_powersave_ntsc_pal_hil",
        )
        self.assertEqual(s74["schema"], p339.SCHEMA_ID)
        self.assertEqual(s74["phase_number"], 339)
        self.assertEqual(s74["milestone"], "74/74")
        self.assertTrue(s74["is_74th_stage_milestone"])
        self.assertTrue(s74["all_checks_passed"])
        self.assertEqual(len(s74["phase339_audit_digest_sha256"]), 64)

    def test_82_standalone_cli_help_uses_sys_executable_and_percent_escaping(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                str(
                    FX3_VM_DIR
                    / "realhw_breathing_camid_copyright_powersave_ntsc_pal_coemulator.py"
                ),
                "--help",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("100%", proc.stdout)
        self.assertIn("74/74", proc.stdout)

    def test_83_suite_cli_help_percent_escaping_and_stage74_flags(self) -> None:
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
        self.assertIn("74/74 Milestone", proc.stdout)
        self.assertIn("--include-stage74", proc.stdout)
        self.assertIn("--skip-stage74", proc.stdout)
        self.assertIn("--no-include-stage74", proc.stdout)
        self.assertIn("--skip-phase339", proc.stdout)

    def test_84_standalone_cli_summary_and_json_modes(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = p339.main(["--self-test", "--clean-room", "--summary"])
        self.assertEqual(rc, 0)
        self.assertIn("[PASS] Phase 339 Stage 74 (74/74 Milestone)", buf.getvalue())

        buf_json = io.StringIO()
        with contextlib.redirect_stdout(buf_json):
            rc2 = p339.main(["--self-test", "--clean-room", "--json"])
        self.assertEqual(rc2, 0)
        parsed = json.loads(buf_json.getvalue())
        self.assertEqual(parsed["milestone"], "74/74")
        self.assertTrue(parsed["is_74th_stage_milestone"])
        self.assertTrue(parsed["all_checks_passed"])
        self.assertNotIn("\\x7fELF", buf_json.getvalue())

    def test_85_no_hardcoded_usr_bin_python3_in_stage74_files(self) -> None:
        mod_src = (
            FX3_VM_DIR
            / "realhw_breathing_camid_copyright_powersave_ntsc_pal_coemulator.py"
        ).read_text(encoding="utf-8")
        tst_src = Path(__file__).read_text(encoding="utf-8")
        forbidden = "/usr/bin/" + "python3"
        self.assertNotIn(forbidden, mod_src)
        self.assertNotIn(forbidden, tst_src)

    def test_86_suite_default_config_enables_stage74_and_full_run_contains_74_stages(self) -> None:
        cfg = suite.CoEmulationConfig()
        self.assertTrue(
            cfg.include_phase339_realhw_breathing_camid_copyright_powersave_ntsc_pal_hil
        )
        self.assertTrue(cfg.include_stage74)
        self.assertTrue(
            cfg.stage74_realhw_breathing_camid_copyright_powersave_ntsc_pal_hil
        )

        t0 = time.monotonic()
        rep = suite.run_fx3_vm_coemulation_suite(cfg)
        elapsed = time.monotonic() - t0
        self.assertTrue(rep["all_checks_passed"])
        stage_keys = [k for k in rep if re.match(r"^stage\d+_", k)]
        self.assertGreaterEqual(len(stage_keys), 74)
        s74 = rep["stage74_realhw_breathing_camid_copyright_powersave_ntsc_pal_hil"]
        self.assertTrue(s74["all_checks_passed"])
        self.assertTrue(s74["is_74th_stage_milestone"])
        self.assertEqual(s74["milestone"], "74/74")
        self.assertEqual(s74["phase_number"], 339)
        max_elapsed = 30.0 if IS_CI else 15.0
        self.assertLess(elapsed, max_elapsed)

    def test_87_suite_skip_flags_and_summary_cli_for_stage74(self) -> None:
        for flag in ("--skip-stage74", "--no-include-stage74", "--skip-phase339"):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = suite.main([*_FAST_CLI_FLAGS, flag, "--json"])
            self.assertEqual(rc, 0)
            data = json.loads(buf.getvalue())
            self.assertNotIn(
                "stage74_realhw_breathing_camid_copyright_powersave_ntsc_pal_hil",
                data,
            )
            self.assertFalse(data["config"]["include_stage74"])

        buf_sum = io.StringIO()
        with contextlib.redirect_stdout(buf_sum):
            rc_sum = suite.main([*_FAST_CLI_FLAGS, "--include-stage74", "--summary"])
        self.assertEqual(rc_sum, 0)
        self.assertIn(
            "realhw_breathing_camid_copyright_powersave_ntsc_pal_hil=CLEAN_ROOM_SYNTHETIC("
            "m74=74/74,hfr=100.0p,title=37ch,sdhc=4GB,copy=46ch,pwr=6/9,mon_dorm=0,"
            "s1_wr=0,emmc_wr=0)",
            buf_sum.getvalue(),
        )

    def test_88_suite_tamper_74a_breathing_comp_redlines_detected(self) -> None:
        for attr, val in (
            ("BREATHING_COMP_HFR_THRESHOLD_FPS", 120.0),
            ("BREATHING_COMP_120P_RAW_SQ_BYPASS_EVENTS", 1),
            ("CATALYST_BROWSE_BREATHING_SUPPORTED", True),
            ("BREATHING_COMP_RESET_IMMUNITY_DRIFT_EVENTS", 1),
            ("FX6_ALL_SQ_BREATHING_LEAK_EVENTS", 1),
        ):
            with unittest.mock.patch.object(p339, attr, val):
                rep = suite.run_fx3_vm_coemulation_suite(
                    suite.CoEmulationConfig(**_fast_suite_kwargs())
                )
                self.assertFalse(rep["all_checks_passed"], attr)

    def test_89_suite_tamper_74b_file_settings_redlines_detected(self) -> None:
        for attr, val in (
            ("MOVIE_FILE_TITLE_MAX_CHARS", 46),
            ("SDHC_FORCED_SPLIT_GB", 8),
            ("SDHC_NONSTANDARD_FORMAT_BYPASS_EVENTS", 1),
            ("SDHC_EXFAT_SIMULT_BYPASS_EVENTS", 1),
            ("CAMID_POS_ROLLOVER_MENU_MUTATION_EVENTS", 1),
            ("SLOT1_FILE_SETTINGS_EROFS_BYPASS_EVENTS", 1),
            ("FX6_CLIP_TITLE_PREFIX_MIN_CHARS", 1),
            ("FX6_CLIP_TITLE_PREFIX_MAX_CHARS", 37),
        ):
            with unittest.mock.patch.object(p339, attr, val):
                rep = suite.run_fx3_vm_coemulation_suite(
                    suite.CoEmulationConfig(**_fast_suite_kwargs())
                )
                self.assertFalse(rep["all_checks_passed"], attr)

    def test_90_suite_tamper_74c_copyright_serial_camset_redlines_detected(self) -> None:
        for attr, val in (
            ("COPYRIGHT_MAX_CHARS", 37),
            ("COPYRIGHT_RESET_WIPE_ERRATA_EVENTS", 1),
            ("WRITE_SERIAL_NUMBER_RESET_WIPE_EVENTS", 1),
            ("CAMSET_COPYRIGHT_PII_LEAK_EVENTS", 1),
            ("PHOTOGRAPHER_COPYRIGHT_PII_LEAKED_BYTES", 1),
            ("BODY_SERIAL_NUMBER_LEAKED_BYTES", 1),
        ):
            with unittest.mock.patch.object(p339, attr, val):
                rep = suite.run_fx3_vm_coemulation_suite(
                    suite.CoEmulationConfig(**_fast_suite_kwargs())
                )
                self.assertFalse(rep["all_checks_passed"], attr)

    def test_91_suite_tamper_74d_power_save_and_ntsc_pal_redlines_detected(self) -> None:
        for attr, val in (
            ("POWER_SAVE_ACTIVE_STEPS_COUNT", 7),
            ("POWER_SAVE_BYPASS_CONDITIONS_COUNT", 8),
            ("DORMANT_POWER_SAVE_BY_MONITOR_EXPOSED_EVENTS", 1),
            ("DORMANT_POWER_SAVE_STEPS_EXPOSED_EVENTS", 1),
            ("NTSC_PAL_SLOT1_FORMAT_EROFS_BYPASS_EVENTS", 1),
            ("PAL_2398P_OR_DF_BYPASS_EVENTS", 1),
        ):
            with unittest.mock.patch.object(p339, attr, val):
                rep = suite.run_fx3_vm_coemulation_suite(
                    suite.CoEmulationConfig(**_fast_suite_kwargs())
                )
                self.assertFalse(rep["all_checks_passed"], attr)

    def test_92_suite_tamper_hard_write_rf_and_runtime_fault_redlines_detected(self) -> None:
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
            with unittest.mock.patch.object(p339, attr, val):
                rep = suite.run_fx3_vm_coemulation_suite(
                    suite.CoEmulationConfig(**_fast_suite_kwargs())
                )
                self.assertFalse(rep["all_checks_passed"], attr)

    def test_93_stage74_all_redline_zero_keys_verified(self) -> None:
        rep = p339.run_phase339_breathing_camid_copyright_powersave_ntsc_pal_coemulation(
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
            "breathing_comp_120p_raw_sq_bypass_events",
            "breathing_comp_reset_immunity_drift_events",
            "fx6_all_sq_breathing_leak_events",
            "sdhc_nonstandard_format_bypass_events",
            "sdhc_exfat_simult_bypass_events",
            "camid_pos_rollover_menu_mutation_events",
            "slot1_file_settings_erofs_bypass_events",
            "copyright_reset_wipe_errata_events",
            "write_serial_number_reset_wipe_events",
            "camset_copyright_pii_leak_events",
            "photographer_copyright_pii_leaked_bytes",
            "body_serial_number_leaked_bytes",
            "dormant_power_save_by_monitor_exposed_events",
            "dormant_power_save_steps_exposed_events",
            "ntsc_pal_slot1_format_erofs_bypass_events",
            "pal_2398p_or_df_bypass_events",
            "rsv_orphan_count",
            "wf12_00342260_hits",
            "appfw_crashes",
            "null_gpio_derefs",
            "mailbox_stalls",
            "stock_cp_fault_count",
            "raw_firmware_bytes_leaked",
        ):
            self.assertEqual(red[zero_key], 0, zero_key)

    def test_94_stage74_all_false_and_true_boolean_redlines_verified(self) -> None:
        rep = p339.run_phase339_breathing_camid_copyright_powersave_ntsc_pal_coemulation(
            force_clean_room=True
        )
        red = rep["redlines"]
        for true_key in (
            "p8_cp_mutation_forbidden",
            "cnflasha_userspace_write_blocked",
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
            "catalyst_browse_breathing_supported",
        ):
            self.assertFalse(red[false_key], false_key)

    def test_95_suite_tamper_milestone_flag_detected(self) -> None:
        with unittest.mock.patch.object(p339, "IS_74TH_STAGE_MILESTONE", False):
            rep = suite.run_fx3_vm_coemulation_suite(
                suite.CoEmulationConfig(**_fast_suite_kwargs())
            )
            self.assertFalse(rep["all_checks_passed"])

    def test_96_all_four_env_modes_pass_cleanly_including_work_root_none(self) -> None:
        clean_rep = p339.run_phase339_breathing_camid_copyright_powersave_ntsc_pal_coemulation(
            force_clean_room=True
        )
        env_rep = p339.run_phase339_breathing_camid_copyright_powersave_ntsc_pal_coemulation(
            env={p339.ENV_FORCE_CLEAN_ROOM: "1"}
        )
        self.assertEqual(
            clean_rep["audit_digest_sha256"],
            env_rep["audit_digest_sha256"],
        )

        with unittest.mock.patch.object(p339, "resolve_mac_work_root", return_value=None):
            none_rep = p339.run_phase339_breathing_camid_copyright_powersave_ntsc_pal_coemulation(
                env={}
            )
        self.assertTrue(none_rep["all_checks_passed"])
        self.assertEqual(none_rep["source_mode"], p339.SOURCE_MODE_CLEAN_ROOM)
        self.assertEqual(none_rep["redlines"]["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(none_rep["audit_digest_sha256"], clean_rep["audit_digest_sha256"])

        cr_test_rep = p339.run_phase339_breathing_camid_copyright_powersave_ntsc_pal_coemulation(
            env={p339.ENV_CLEAN_ROOM_TEST: "1"}
        )
        self.assertTrue(cr_test_rep["all_checks_passed"])
        self.assertEqual(cr_test_rep["audit_digest_sha256"], clean_rep["audit_digest_sha256"])


if __name__ == "__main__":
    unittest.main()
