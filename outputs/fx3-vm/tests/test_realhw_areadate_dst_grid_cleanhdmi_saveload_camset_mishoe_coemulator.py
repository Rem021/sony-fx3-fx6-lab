#!/usr/bin/env python3
"""Unit tests for Phase 353 (Stage 78 — 78/78 Full-Board VM Co-Emulation Stages!):
Real-Hardware `ILME-FX3 Ver. 7.02` vs `ILME-FX6 Ver. 6.01` Wave-68:
- 78A: `Setup -> [Area/Date] -> [Area/Date/Time Setting]` (30 `AREA_GMT_*` zones
  incl. 6 half-hour offsets, `convert_setting_daylight_saving_to_saylight_saving`
  and `BKID_APP_setting_auto_sync_sever_date_time` ELF typos, 3 Date Formats
  `Y-M-D` / `M-D-Y` / `D-M-Y`, Reset-immune, `[Initialize]` re-triggers
  `37dlg_rec203_initial_setting_controller`, internal soldered rechargeable RTC
  charged `>= 24 hours` with `NP-FZ100` while power `OFF`, zero user CR2032
  slot, `ilc/2210` does NOT state `"3 months"`) vs `ILME-FX6 Ver. 6.01`
  `Maintenance > Clock Set` (`UTC -12:00..+14:00` 30-min steps, zero DST toggle,
  hard-lock on depletion / `Backup Battery End`),
- 78B: All-Pipeline `[Grid Line Display/Type]` (`Off`/`On`, 3 types, retired
  `BKID_APP_deleted_setting_grid_line_{display,type}_movie`) HDMI Pass-Through
  vs Movie/`S&Q`-only `[Marker Display]` (`Center Marker`, 15-ratio `Aspect
  Marker`, `Safety Zone`, `[Guideframe]`; suppressed in `[Focus Magnifier]`;
  100%% monitor-only `0` HDMI pixels ALWAYS); all Reset-immune vs `ILME-FX6`
  `Monitoring > Marker` & dormant `GUIDE_FRAME_*_GRID`,
- 78C: `Setup -> [Reset/Save Settings] -> [Save/Load Settings]` (`CAMSET01..10.DAT`
  `Slot 1`-locked, `libSaveLoadSettings.so` `18,760 B`, `60` Cloud slots, zero
  `PRO/CAMERA` hits, disabled in `MR` mode, auto-reboot on Load, 20 official
  exclusions, Tier-0 `Slot 1` `EROFS=30` on Save/Delete) vs `Camera Set. Memory`
  `1..3` / `M1..M4` (`CAMPR%02d%c.DAT`, `Slot 1`/`Slot 2`) & `ILME-FX6`
  `Project > All File` (`Media(B)` max 64 `.ALL`), `Scene File`, and dormant
  `Reference File` (`0` ELF hits),
- 78D: Zero physical PC `Sync Terminal` (`SYNCHRO_TERMINAL* == 0` in `FX3 appFw.so`,
  `Flash Sync Spd. Prty.` dormant), Still-only Mechanical-shutter `[External
  Flash Set.]` (`1/250 s`, `< 250 V`, Reset-immune & excluded from `CAMSET*.DAT`),
  4-mode `[Video Light Mode]` incl. `Auto` vs `XLR-H1` physical & electrical
  MI-Shoe mutual exclusion (`EBUSY=16`, handle shoes are passive cold shoes,
  PMIC `5V <= 900 mA` guard) vs `ILME-FX6` 3-mode `Video Light Set` (zero `Auto`),
  switchable `TC IN/OUT` BNC, and zero physical `GENLOCK IN / REF OUT` BNC
  (`107` dormant `GENLOCK` ELF symbols)
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
import realhw_areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_coemulator as p353  # noqa: E402

IS_CI = os.environ.get("GITHUB_ACTIONS", "").lower() == "true"


def _fast_suite_kwargs(**overrides: object) -> dict:
    """Fast config skipping unrelated optional stages 4..77 for Stage 78 isolation tests."""
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
        include_stage77=False,
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
    "--skip-stage77",
]


class TestRealHwStage78AreaDateDstGridCleanHdmiSaveLoadCamsetMiShoe(unittest.TestCase):
    # ------------------------------------------------------------------
    # Donor Audit, Bounded O_RDONLY & 4-Mode Fallback Tests (Tests 01..15)
    # ------------------------------------------------------------------

    def test_01_milestone_constants_78_of_78(self) -> None:
        self.assertEqual(p353.PHASE_NUMBER, 353)
        self.assertEqual(p353.STAGE_INDEX, 78)
        self.assertEqual(p353.STAGE_TOTAL, 78)
        self.assertEqual(p353.MILESTONE_LABEL, "78/78")
        self.assertTrue(p353.IS_78TH_STAGE_MILESTONE)
        self.assertEqual(len(p353.DONOR_RELPATHS), 12)
        self.assertEqual(len(p353.EXPECTED_DONOR_BYTES), 12)
        self.assertEqual(len(p353.EXPECTED_COMPACT_DONOR_SHA256), 9)
        self.assertEqual(len(p353.EXPECTED_LARGE_HEAD4K_SHA256), 3)
        self.assertEqual(len(p353.LARGE_DONOR_WINDOWS), 3)

    def test_02_hard_safety_and_wave68_redlines_locked(self) -> None:
        self.assertTrue(p353.P8_CP_MUTATION_FORBIDDEN)
        self.assertTrue(p353.CNFLASHA_USERSPACE_WRITE_BLOCKED)
        self.assertFalse(p353.PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(p353.EMMC_WRITES_AUTHORIZED)
        self.assertFalse(p353.CROSS_MODEL_FLASH_AUTHORIZED)
        self.assertFalse(p353.HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        self.assertFalse(p353.OVERALL_READY_FOR_HARDWARE_ATTACH)
        self.assertFalse(p353.ISP_WRITE_AUTHORIZED)
        self.assertFalse(p353.SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(p353.EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        self.assertFalse(p353.SLOT1_AVF_INFO_MUTATED)
        self.assertEqual(p353.SLOT1_DATA_SECTOR_WRITES, 0)
        self.assertEqual(p353.EMMC_NFLASHA_WRITE_COUNT, 0)
        self.assertEqual(p353.RAW_FIRMWARE_BYTES_LEAKED, 0)
        self.assertEqual(p353.FX3_AREA_GMT_ZONES_COUNT, 30)
        self.assertEqual(p353.FX3_AREA_HALF_HOUR_ZONES_COUNT, 6)
        self.assertEqual(p353.FX3_DATE_FORMATS_COUNT, 3)
        self.assertTrue(p353.AREA_DATE_SAYLIGHT_SAVING_TYPO_MATCHED)
        self.assertTrue(p353.AREA_DATE_SEVER_TYPO_MATCHED)
        self.assertEqual(p353.AREA_DATE_RESET_WIPE_EVENTS, 0)
        self.assertFalse(p353.FX3_USER_CR2032_SLOT_PRESENT)
        self.assertEqual(p353.FX3_RTC_CHARGE_MIN_HOURS_POWER_OFF, 24)
        self.assertFalse(p353.ILC2210_STATES_3_MONTHS_RETENTION)
        self.assertFalse(p353.FX6_CLOCK_SET_DST_TOGGLE_EXPOSED)
        self.assertEqual(p353.GRID_LINE_TYPES_COUNT, 3)
        self.assertEqual(p353.ASPECT_MARKER_RATIOS_COUNT, 15)
        self.assertFalse(p353.RETIRED_MOVIE_GRID_KEYS_EXPOSED)
        self.assertEqual(p353.GRID_AND_MARKER_RESET_WIPE_EVENTS, 0)
        self.assertEqual(p353.HDMI_MARKER_INJECTED_PIXELS, 0)
        self.assertFalse(p353.FX6_NATIVE_3MODE_GRID_EXPOSED)
        self.assertEqual(p353.CAMSET_MAX_CARD_SLOTS, 10)
        self.assertEqual(p353.CAMSET_MAX_CLOUD_SLOTS, 60)
        self.assertEqual(p353.CAMSET_SLOT2_BYPASS_EVENTS, 0)
        self.assertEqual(p353.FX3_PRO_CAMERA_PATH_HITS, 0)
        self.assertEqual(p353.CAMSET_EXCLUDED_ITEMS_LEAKED_COUNT, 0)
        self.assertEqual(p353.CAMSET_SLOT1_EROFS_BYPASS_EVENTS, 0)
        self.assertEqual(p353.FX6_ALL_FILE_MAX_SLOTS, 64)
        self.assertEqual(p353.FX6_REFERENCE_FILE_ELF_HITS, 0)
        self.assertFalse(p353.FX3_PHYSICAL_SYNC_TERMINAL_PRESENT)
        self.assertEqual(p353.FX3_SYNCHRO_TERMINAL_ELF_HITS, 0)
        self.assertEqual(p353.DORMANT_FLASH_SYNC_SPD_PRTY_EXPOSED_EVENTS, 0)
        self.assertEqual(p353.FX3_VIDEO_LIGHT_MODES_COUNT, 4)
        self.assertEqual(p353.FX6_VIDEO_LIGHT_MODES_COUNT, 3)
        self.assertFalse(p353.FX6_VIDEO_LIGHT_AUTO_SUPPORTED)
        self.assertEqual(p353.XLR_H1_MISHOE_COLLISION_BYPASS_EVENTS, 0)
        self.assertEqual(p353.PMIC_5V_MAX_MA, 900)
        self.assertEqual(p353.PMIC_5V_OVERCURRENT_BYPASS_EVENTS, 0)
        self.assertFalse(p353.FX6_PHYSICAL_GENLOCK_BNC_PRESENT)
        self.assertEqual(p353.FX6_DORMANT_GENLOCK_ELF_HITS, 107)
        self.assertEqual(p353.FX6_DORMANT_GENLOCK_EXPOSED_EVENTS, 0)

    def test_03_clean_room_test_mode_both_env_vars(self) -> None:
        self.assertFalse(p353.clean_room_test_mode(env={}))
        self.assertTrue(p353.clean_room_test_mode(env={p353.ENV_FORCE_CLEAN_ROOM: "1"}))
        self.assertTrue(p353.clean_room_test_mode(env={p353.ENV_CLEAN_ROOM_TEST: "1"}))
        self.assertTrue(p353.clean_room_test_mode(force_clean_room=True, env={}))
        self.assertFalse(
            p353.clean_room_test_mode(
                force_clean_room=False,
                env={p353.ENV_FORCE_CLEAN_ROOM: "1", p353.ENV_CLEAN_ROOM_TEST: "1"},
            )
        )

    def test_04_resolve_mac_work_root_and_donorless_fallback(self) -> None:
        self.assertIsNone(p353.resolve_mac_work_root(work_root=None, env={}))
        self.assertIsNone(
            p353.resolve_mac_work_root(work_root="/nonexistent/wave68/path", env={})
        )
        self.assertIsNone(
            p353.resolve_mac_work_root(
                env={p353.ENV_MAC_WORK_ROOT: p353.CLEAN_ROOM_SENTINEL_DIRNAME}
            )
        )
        self.assertIsNone(
            p353.resolve_mac_work_root(
                env={p353.ENV_MAC_ROOT: p353.CLEAN_ROOM_SENTINEL_DIRNAME}
            )
        )
        with tempfile.TemporaryDirectory() as td:
            self.assertIsNone(p353.resolve_mac_work_root(work_root=td, env={}))

    def test_05_clean_room_synthetic_donor_audit_12_of_12(self) -> None:
        rep = p353.inspect_phase353_wave68_donors(force_clean_room=True)
        self.assertEqual(rep.source_mode, p353.SOURCE_MODE_CLEAN_ROOM)
        self.assertEqual(rep.donor_access_mode, p353.DONOR_ACCESS_MODE)
        self.assertEqual(rep.bounded_window_max_bytes, 4096)
        self.assertEqual(rep.donors_checked, 12)
        self.assertEqual(rep.donors_verified, 12)
        self.assertTrue(rep.all_contracts_verified)
        self.assertEqual(rep.fx3_area_gmt_zones_verified, 30)
        self.assertTrue(rep.fx3_synchro_terminal_absent_verified)
        self.assertTrue(rep.fx3_pro_camera_absent_verified)
        self.assertTrue(rep.fx6_reference_file_absent_verified)
        self.assertTrue(rep.fx6_video_light_no_auto_verified)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_06_clean_room_via_env_vars_and_nonexistent_work_root(self) -> None:
        for kw in (
            dict(env={p353.ENV_CLEAN_ROOM_TEST: "1"}),
            dict(env={p353.ENV_FORCE_CLEAN_ROOM: "1"}),
            dict(work_root=None, env={}),
            dict(work_root="/nonexistent/wave68/dir", env={}),
            dict(env={p353.ENV_MAC_WORK_ROOT: p353.CLEAN_ROOM_SENTINEL_DIRNAME}),
        ):
            r = p353.run_phase353_areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_coemulation(
                **kw
            )
            self.assertTrue(r["all_checks_passed"], str(kw))
            self.assertEqual(r["source_mode"], p353.SOURCE_MODE_CLEAN_ROOM)
            self.assertEqual(r["redlines"]["raw_firmware_bytes_leaked"], 0)

    def test_07_local_donor_o_rdonly_audit_when_present(self) -> None:
        root = p353.resolve_mac_work_root()
        if root is None:
            self.skipTest("Local Mac/work donor tree not present in CI")
        rep = p353.inspect_phase353_wave68_donors(work_root=root)
        self.assertEqual(rep.source_mode, p353.SOURCE_MODE_LOCAL_DONOR)
        self.assertEqual(rep.donors_checked, 12)
        self.assertEqual(rep.donors_verified, 12)
        self.assertTrue(rep.all_contracts_verified)
        self.assertEqual(rep.fx3_area_gmt_zones_verified, 30)
        self.assertTrue(rep.fx3_synchro_terminal_absent_verified)
        self.assertTrue(rep.fx3_pro_camera_absent_verified)
        self.assertTrue(rep.fx6_reference_file_absent_verified)
        self.assertTrue(rep.fx6_video_light_no_auto_verified)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_08_bounded_window_enforces_4096b_cap_and_o_rdonly(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "sample.bin"
            f.write_bytes(b"ABCD" * 2048)
            chunk = p353._read_bounded_window_o_rdonly(f, 0, 4096)
            self.assertEqual(len(chunk), 4096)
            for bad_off, bad_len in ((-1, 16), (0, 0), (0, 4097)):
                with self.assertRaises(p353.Stage78Phase353Error):
                    p353._read_bounded_window_o_rdonly(f, bad_off, bad_len)

    def test_09_compact_donor_size_cap_enforced(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "too_big.bin"
            f.write_bytes(b"X" * 2048)
            with self.assertRaises(p353.Stage78Phase353Error):
                p353._read_full_compact_o_rdonly(f, expected_max=1024)

    def test_10_clean_room_determinism_and_recursive_elapsed_seconds_strip(self) -> None:
        r1 = p353.run_phase353_areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_coemulation(
            force_clean_room=True
        )
        r2 = p353.run_phase353_areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_coemulation(
            force_clean_room=True
        )
        self.assertTrue(r1["all_checks_passed"])
        self.assertEqual(r1["audit_digest_sha256"], r2["audit_digest_sha256"])
        self.assertEqual(len(r1["audit_digest_sha256"]), 64)

        stripped = p353._strip_wall_clock(
            {
                "elapsed_seconds": 99.9,
                "nested": {"elapsed_seconds": 1.2, "keep": 7},
                "items": [{"elapsed_seconds": 0.5, "ok": True}],
            }
        )
        self.assertNotIn("elapsed_seconds", stripped)
        self.assertNotIn("elapsed_seconds", stripped["nested"])
        self.assertEqual(stripped["nested"]["keep"], 7)
        self.assertNotIn("elapsed_seconds", stripped["items"][0])
        self.assertTrue(stripped["items"][0]["ok"])

    def test_11_no_raw_firmware_bytes_leaked_in_json_payload(self) -> None:
        rep = p353.run_phase353_areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_coemulation(
            force_clean_room=True
        )
        txt = json.dumps(rep, sort_keys=True)
        self.assertNotIn("\\x7fELF", txt)
        self.assertNotIn("\x7fELF", txt)
        self.assertEqual(rep["redlines"]["raw_firmware_bytes_leaked"], 0)

    def test_12_clean_room_vs_local_donor_structural_parity(self) -> None:
        r_cr = p353.run_phase353_areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_coemulation(
            force_clean_room=True
        )
        r_ld = p353.run_phase353_areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_coemulation()
        self.assertTrue(r_cr["all_checks_passed"])
        self.assertTrue(r_ld["all_checks_passed"])
        self.assertEqual(
            r_cr["donor_audit"]["donors_verified"],
            r_ld["donor_audit"]["donors_verified"],
        )
        self.assertEqual(r_cr["redlines"], r_ld["redlines"])

    def test_13_o_rdonly_local_donors_no_write_flags_used(self) -> None:
        root = p353.resolve_mac_work_root()
        if root is None:
            self.skipTest("Local Mac/work donor tree not present in CI")
        seen_flags = []
        orig_open = os.open

        def spying_open(path, flags, *args, **kwargs):
            seen_flags.append(flags)
            return orig_open(path, flags, *args, **kwargs)

        with unittest.mock.patch("os.open", side_effect=spying_open):
            rep = p353.inspect_phase353_wave68_donors(work_root=root)
        self.assertTrue(rep.all_contracts_verified)
        self.assertGreater(len(seen_flags), 0)
        for fl in seen_flags:
            self.assertEqual(fl & os.O_ACCMODE, os.O_RDONLY)

    def test_14_local_donors_available_helper_contract(self) -> None:
        self.assertFalse(
            p353._local_donors_available(
                work_root=None, env={p353.ENV_FORCE_CLEAN_ROOM: "1"}
            )
        )
        self.assertFalse(
            p353._local_donors_available(work_root="/nonexistent/wave68", env={})
        )

    def test_15_donor_artifact_contracts_include_all_compact_and_large_specs(self) -> None:
        rep = p353.inspect_phase353_wave68_donors(force_clean_room=True)
        for key in p353.DONOR_RELPATHS:
            self.assertIn(key, rep.artifacts)
            art = rep.artifacts[key]
            self.assertEqual(art.byte_length, p353.EXPECTED_DONOR_BYTES[key])
            self.assertTrue(art.size_matched)
            self.assertTrue(art.expected_sha256_matched)
            self.assertTrue(art.all_tokens_matched)
            self.assertEqual(art.raw_firmware_bytes_leaked, 0)

    # ------------------------------------------------------------------
    # Sub-Model 78A: Setup -> [Area/Date/Time Setting] & 24h RTC vs FX6 Clock Set (16..35)
    # ------------------------------------------------------------------

    def test_16_78a_exact_30_gmt_zones_and_6_half_hour_offsets(self) -> None:
        self.assertEqual(len(p353.FX3_AREA_GMT_30_ZONES), 30)
        self.assertEqual(len(set(p353.FX3_AREA_GMT_30_ZONES)), 30)
        half_hours = [z for z in p353.FX3_AREA_GMT_30_ZONES if z.endswith("_5")]
        self.assertEqual(tuple(half_hours), p353.FX3_AREA_HALF_HOUR_ZONES)
        self.assertEqual(len(half_hours), 6)
        self.assertIn("AREA_GMT_M_03_5", half_hours)
        self.assertIn("AREA_GMT_P_05_5", half_hours)
        self.assertIn("AREA_GMT_P_09_5", half_hours)

    def test_17_78a_all_30_zones_admitted_and_24h_time_format(self) -> None:
        for z in p353.FX3_AREA_GMT_30_ZONES:
            r = p353.simulate_area_date_dst_rtc_and_fx6_clock_set_hil(area_zone=z)
            self.assertTrue(r.admitted, z)
            self.assertEqual(r.effective_area_zone, z)
            self.assertEqual(r.effective_time_format, "24h")
            self.assertEqual(r.area_gmt_zones_count, 30)
            self.assertEqual(r.half_hour_zones_count, 6)

    def test_18_78a_exact_3_date_formats_and_typos_recorded(self) -> None:
        self.assertEqual(p353.FX3_DATE_FORMATS, ("Y-M-D", "M-D-Y", "D-M-Y"))
        for fmt in p353.FX3_DATE_FORMATS:
            r = p353.simulate_area_date_dst_rtc_and_fx6_clock_set_hil(date_format=fmt)
            self.assertTrue(r.admitted, fmt)
            self.assertEqual(r.effective_date_format, fmt)
            self.assertEqual(
                r.saylight_saving_typo_symbol,
                "convert_setting_daylight_saving_to_saylight_saving",
            )
            self.assertEqual(
                r.sever_date_time_typo_symbol,
                "BKID_APP_setting_auto_sync_sever_date_time",
            )

    def test_19_78a_daylight_savings_off_default_and_on(self) -> None:
        r_def = p353.simulate_area_date_dst_rtc_and_fx6_clock_set_hil()
        self.assertTrue(r_def.admitted)
        self.assertEqual(r_def.effective_daylight_savings, "Off")

        r_on = p353.simulate_area_date_dst_rtc_and_fx6_clock_set_hil(
            daylight_savings="On"
        )
        self.assertTrue(r_on.admitted)
        self.assertEqual(r_on.effective_daylight_savings, "On")

    def test_20_78a_camera_settings_reset_immune_preserved(self) -> None:
        r = p353.simulate_area_date_dst_rtc_and_fx6_clock_set_hil(
            area_zone="AREA_GMT_P_09_5",
            daylight_savings="On",
            date_format="M-D-Y",
            camera_settings_reset_applied=True,
        )
        self.assertTrue(r.admitted)
        self.assertFalse(r.area_date_resettable)
        self.assertEqual(r.effective_area_zone, "AREA_GMT_P_09_5")
        self.assertEqual(r.effective_daylight_savings, "On")
        self.assertEqual(r.effective_date_format, "M-D-Y")
        self.assertFalse(r.initial_setting_wizard_triggered)

    def test_21_78a_initialize_clears_and_retriggers_37dlg_wizard(self) -> None:
        r = p353.simulate_area_date_dst_rtc_and_fx6_clock_set_hil(
            area_zone="AREA_GMT_P_08_0",
            daylight_savings="On",
            date_format="D-M-Y",
            initialize_applied=True,
        )
        self.assertTrue(r.admitted)
        self.assertIsNone(r.effective_area_zone)
        self.assertEqual(r.effective_daylight_savings, "Off")
        self.assertIsNone(r.effective_date_format)
        self.assertTrue(r.initial_setting_wizard_triggered)
        self.assertTrue(r.area_date_prompt_on_boot)

    def test_22_78a_rtc_backup_battery_no_cr2032_no_3_months_24h_rule(self) -> None:
        r_short = p353.simulate_area_date_dst_rtc_and_fx6_clock_set_hil(
            operation="boot_rtc_check",
            rtc_battery_depleted=True,
            rtc_charge_hours_power_off=23.9,
        )
        self.assertFalse(r_short.admitted)
        self.assertEqual(r_short.errno_code, p353.EPERM_ERRNO)
        self.assertFalse(r_short.rtc_battery_charged)
        self.assertTrue(r_short.area_date_prompt_on_boot)
        self.assertFalse(r_short.has_user_replaceable_cr2032_slot)
        self.assertFalse(r_short.ilc2210_states_3_months_retention)
        self.assertFalse(r_short.service_center_repair_required)

        r_ok = p353.simulate_area_date_dst_rtc_and_fx6_clock_set_hil(
            operation="boot_rtc_check",
            rtc_battery_depleted=True,
            rtc_charge_hours_power_off=24.0,
        )
        self.assertTrue(r_ok.admitted)
        self.assertTrue(r_ok.rtc_battery_charged)
        self.assertFalse(r_ok.has_user_replaceable_cr2032_slot)
        self.assertFalse(r_ok.ilc2210_states_3_months_retention)

    def test_23_78a_rtc_aged_dead_requires_service_center_repair(self) -> None:
        r = p353.simulate_area_date_dst_rtc_and_fx6_clock_set_hil(
            operation="boot_rtc_check",
            rtc_battery_aged_dead=True,
            rtc_charge_hours_power_off=48.0,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p353.EPERM_ERRNO)
        self.assertFalse(r.rtc_battery_charged)
        self.assertTrue(r.service_center_repair_required)
        self.assertTrue(r.area_date_prompt_on_boot)

    def test_24_78a_timestamp_dependent_action_blocked_until_date_set(self) -> None:
        r_unset = p353.simulate_area_date_dst_rtc_and_fx6_clock_set_hil(
            operation="timestamp_dependent_action",
            date_time_configured=False,
        )
        self.assertFalse(r_unset.admitted)
        self.assertEqual(r_unset.errno_code, p353.EINVAL_ERRNO)
        self.assertTrue(r_unset.area_date_prompt_on_boot)

        r_set = p353.simulate_area_date_dst_rtc_and_fx6_clock_set_hil(
            operation="timestamp_dependent_action",
            date_time_configured=True,
            rtc_battery_depleted=False,
        )
        self.assertTrue(r_set.admitted)

    def test_25_78a_unregistered_smartphone_wizard_reprompts_on_boot(self) -> None:
        r = p353.simulate_area_date_dst_rtc_and_fx6_clock_set_hil(
            smartphone_registered_in_wizard=False
        )
        self.assertTrue(r.admitted)
        self.assertTrue(r.area_date_prompt_on_boot)

    def test_26_78a_fx6_clock_set_utc_minus12_to_plus14_30min_steps(self) -> None:
        for offset in (-720, -210, 0, 330, 840):
            r = p353.simulate_area_date_dst_rtc_and_fx6_clock_set_hil(
                body_profile=p353.BODY_MODEL_FX6,
                fw_version=p353.FW_VER_601,
                operation="fx6_clock_set",
                fx6_utc_offset_minutes=offset,
                fx6_date_mode="DDMMYY",
                fx6_time_format="12h",
            )
            self.assertTrue(r.admitted, offset)
            self.assertEqual(r.effective_date_format, "DDMMYY")
            self.assertEqual(r.effective_time_format, "12h")
            self.assertFalse(r.fx6_dst_toggle_exposed)

    def test_27_78a_fx6_zero_dst_toggle_dormant_summer_time_rejected(self) -> None:
        r = p353.simulate_area_date_dst_rtc_and_fx6_clock_set_hil(
            body_profile=p353.BODY_MODEL_FX6,
            fw_version=p353.FW_VER_601,
            operation="fx6_dst_toggle",
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p353.EOPNOTSUPP_ERRNO)
        self.assertFalse(r.fx6_dst_toggle_exposed)

    def test_28_78a_fx6_depleted_hard_locks_clock_set_vs_backup_battery_end(self) -> None:
        r_dep = p353.simulate_area_date_dst_rtc_and_fx6_clock_set_hil(
            body_profile=p353.BODY_MODEL_FX6,
            fw_version=p353.FW_VER_601,
            operation="fx6_clock_set",
            fx6_backup_battery_depleted=True,
        )
        self.assertFalse(r_dep.admitted)
        self.assertEqual(r_dep.errno_code, p353.EPERM_ERRNO)
        self.assertTrue(r_dep.fx6_clock_set_hard_locked)
        self.assertFalse(r_dep.fx6_backup_battery_end_emitted)

        r_end = p353.simulate_area_date_dst_rtc_and_fx6_clock_set_hil(
            body_profile=p353.BODY_MODEL_FX6,
            fw_version=p353.FW_VER_601,
            operation="fx6_clock_set",
            fx6_backup_battery_aged_dead=True,
        )
        self.assertFalse(r_end.admitted)
        self.assertEqual(r_end.errno_code, p353.EPERM_ERRNO)
        self.assertTrue(r_end.fx6_clock_set_hard_locked)
        self.assertTrue(r_end.fx6_backup_battery_end_emitted)
        self.assertTrue(r_end.service_center_repair_required)

    def test_29_78a_cross_body_operations_rejected(self) -> None:
        for op in ("fx6_clock_set", "fx6_dst_toggle"):
            r1 = p353.simulate_area_date_dst_rtc_and_fx6_clock_set_hil(
                body_profile=p353.BODY_MODEL_FX3, operation=op
            )
            self.assertFalse(r1.admitted, op)
            self.assertEqual(r1.errno_code, p353.EOPNOTSUPP_ERRNO)

        for op in ("configure_area_date", "boot_rtc_check", "timestamp_dependent_action"):
            r2 = p353.simulate_area_date_dst_rtc_and_fx6_clock_set_hil(
                body_profile=p353.BODY_MODEL_FX6, fw_version=p353.FW_VER_601, operation=op
            )
            self.assertFalse(r2.admitted, op)
            self.assertEqual(r2.errno_code, p353.EOPNOTSUPP_ERRNO)

    def test_30_78a_invalid_inputs_raise_stage78_error(self) -> None:
        for bad in (
            dict(body_profile="FX30"),
            dict(fw_version="9.00"),
            dict(operation="bad_op"),
            dict(area_zone="AREA_GMT_P_14_0"),
            dict(daylight_savings="Auto"),
            dict(date_format="YYYY-MM-DD"),
            dict(rtc_charge_hours_power_off=-1.0),
            dict(fx6_utc_offset_minutes=-750),
            dict(fx6_utc_offset_minutes=870),
            dict(fx6_utc_offset_minutes=45),
            dict(fx6_date_mode="YYYYMMDD"),
            dict(fx6_time_format="military"),
        ):
            with self.assertRaises(p353.Stage78Phase353Error, msg=str(bad)):
                p353.simulate_area_date_dst_rtc_and_fx6_clock_set_hil(**bad)

    def test_31_78a_fx6_3_date_modes_verified(self) -> None:
        for dm in ("YYMMDD", "MMDDYY", "DDMMYY"):
            r = p353.simulate_area_date_dst_rtc_and_fx6_clock_set_hil(
                body_profile=p353.BODY_MODEL_FX6,
                fw_version=p353.FW_VER_601,
                operation="fx6_clock_set",
                fx6_date_mode=dm,
            )
            self.assertTrue(r.admitted, dm)
            self.assertEqual(r.effective_date_format, dm)

    def test_32_78a_fx3_half_hour_zones_include_all_6_expected_zones(self) -> None:
        expected = {
            "AREA_GMT_M_03_5",
            "AREA_GMT_P_03_5",
            "AREA_GMT_P_04_5",
            "AREA_GMT_P_05_5",
            "AREA_GMT_P_06_5",
            "AREA_GMT_P_09_5",
        }
        self.assertEqual(set(p353.FX3_AREA_HALF_HOUR_ZONES), expected)

    def test_33_78a_fx3_initialize_overrides_reset_and_clears_dst(self) -> None:
        r = p353.simulate_area_date_dst_rtc_and_fx6_clock_set_hil(
            area_zone="AREA_GMT_M_05_0",
            daylight_savings="On",
            date_format="M-D-Y",
            camera_settings_reset_applied=True,
            initialize_applied=True,
        )
        self.assertTrue(r.initial_setting_wizard_triggered)
        self.assertIsNone(r.effective_area_zone)
        self.assertEqual(r.effective_daylight_savings, "Off")
        self.assertIsNone(r.effective_date_format)

    def test_34_78a_fx3_rtc_check_passes_with_zero_hours_if_not_depleted(self) -> None:
        r = p353.simulate_area_date_dst_rtc_and_fx6_clock_set_hil(
            operation="boot_rtc_check",
            rtc_battery_depleted=False,
            rtc_charge_hours_power_off=0.0,
        )
        self.assertTrue(r.admitted)
        self.assertTrue(r.rtc_battery_charged)

    def test_35_78a_pillar_a_payload_verified(self) -> None:
        rep = p353.run_phase353_areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_coemulation(
            force_clean_room=True
        )
        pa = rep["pillar_a_area_date_dst_rtc_fx6_clock_set_hil"]
        self.assertTrue(pa["passed"])
        self.assertEqual(pa["reset_immune"]["effective_area_zone"], "AREA_GMT_P_05_5")
        self.assertTrue(pa["initialize_retriggers_wizard"]["initial_setting_wizard_triggered"])
        self.assertFalse(pa["rtc_short_charge_blocked"]["admitted"])
        self.assertTrue(pa["rtc_24h_charged"]["rtc_battery_charged"])
        self.assertTrue(pa["fx6_backup_battery_end"]["fx6_backup_battery_end_emitted"])

    # ------------------------------------------------------------------
    # Sub-Model 78B: Grid Line HDMI Pass-Through vs Marker Zero-HDMI (36..55)
    # ------------------------------------------------------------------

    def test_36_78b_grid_line_all_pipelines_and_3_types(self) -> None:
        self.assertEqual(len(p353.VALID_GRID_LINE_TYPES), 3)
        for mode in p353.VALID_SHOOT_MODES:
            for gtype in p353.VALID_GRID_LINE_TYPES:
                r = p353.simulate_grid_line_hdmi_vs_marker_guideframe_isolation_hil(
                    shoot_mode=mode,
                    grid_line_display="On",
                    grid_line_type=gtype,
                    hdmi_connected=True,
                    hdmi_info_display="On",
                )
                self.assertTrue(r.admitted, (mode, gtype))
                self.assertTrue(r.grid_line_available_all_pipelines)
                self.assertFalse(r.retired_movie_grid_keys_exposed)
                self.assertEqual(r.effective_grid_line_type, gtype)
                self.assertTrue(r.grid_rendered_on_monitor)
                self.assertTrue(r.grid_rendered_on_hdmi)

    def test_37_78b_opposite_hdmi_routing_marker_0_pixels_vs_grid_passthrough(self) -> None:
        r = p353.simulate_grid_line_hdmi_vs_marker_guideframe_isolation_hil(
            shoot_mode=p353.SHOOT_MODE_MOVIE,
            grid_line_display="On",
            grid_line_type="Rule of 3rds Grid",
            marker_display="On",
            center_marker="On",
            aspect_marker="2.39:1",
            safety_zone="80%",
            guideframe="On",
            hdmi_connected=True,
            hdmi_info_display="On",
            rec_media_dur_hdmi_output="On",
            raw_output="Off",
        )
        self.assertTrue(r.admitted)
        self.assertTrue(r.grid_rendered_on_monitor)
        self.assertTrue(r.grid_rendered_on_hdmi)
        self.assertTrue(r.marker_rendered_on_monitor)
        self.assertFalse(r.marker_rendered_on_hdmi)
        self.assertEqual(r.hdmi_marker_injected_pixels, 0)
        self.assertFalse(r.clean_hdmi_feed_active)

    def test_38_78b_all_3_clean_feed_triggers_strip_grid_from_hdmi(self) -> None:
        for kw in (
            dict(hdmi_info_display="Off", rec_media_dur_hdmi_output="On", raw_output="Off"),
            dict(hdmi_info_display="On", rec_media_dur_hdmi_output="Off(HDMI Only)", raw_output="Off"),
            dict(hdmi_info_display="On", rec_media_dur_hdmi_output="On", raw_output="On"),
        ):
            r = p353.simulate_grid_line_hdmi_vs_marker_guideframe_isolation_hil(
                shoot_mode=p353.SHOOT_MODE_MOVIE,
                grid_line_display="On",
                marker_display="On",
                guideframe="On",
                hdmi_connected=True,
                **kw,
            )
            self.assertTrue(r.admitted, str(kw))
            self.assertTrue(r.grid_rendered_on_monitor)
            self.assertFalse(r.grid_rendered_on_hdmi)
            self.assertFalse(r.marker_rendered_on_hdmi)
            self.assertEqual(r.hdmi_marker_injected_pixels, 0)
            self.assertTrue(r.clean_hdmi_feed_active)

    def test_39_78b_sq_mode_forces_rec_media_on_so_grid_passes_to_hdmi(self) -> None:
        r = p353.simulate_grid_line_hdmi_vs_marker_guideframe_isolation_hil(
            shoot_mode=p353.SHOOT_MODE_SQ,
            grid_line_display="On",
            marker_display="On",
            guideframe="On",
            hdmi_connected=True,
            hdmi_info_display="On",
            rec_media_dur_hdmi_output="Off(HDMI Only)",
            raw_output="Off",
        )
        self.assertTrue(r.admitted)
        self.assertTrue(r.grid_rendered_on_hdmi)
        self.assertTrue(r.marker_rendered_on_monitor)
        self.assertFalse(r.marker_rendered_on_hdmi)
        self.assertEqual(r.hdmi_marker_injected_pixels, 0)

    def test_40_78b_still_mode_rejects_marker_display_via_prm_haita(self) -> None:
        for kw in (
            dict(marker_display="On"),
            dict(center_marker="On"),
            dict(aspect_marker="16:9"),
            dict(safety_zone="90%"),
            dict(guideframe="On"),
        ):
            r = p353.simulate_grid_line_hdmi_vs_marker_guideframe_isolation_hil(
                shoot_mode=p353.SHOOT_MODE_STILL,
                grid_line_display="On",
                **kw,
            )
            self.assertFalse(r.admitted, str(kw))
            self.assertEqual(r.errno_code, p353.EOPNOTSUPP_ERRNO)
            self.assertFalse(r.marker_display_available_in_still)
            self.assertFalse(r.marker_rendered_on_monitor)
            self.assertFalse(r.marker_rendered_on_hdmi)

    def test_41_78b_all_15_aspect_marker_ratios_supported_in_movie(self) -> None:
        self.assertEqual(len(p353.ASPECT_MARKER_15_RATIOS), 15)
        for ratio in p353.ASPECT_MARKER_15_RATIOS:
            r = p353.simulate_grid_line_hdmi_vs_marker_guideframe_isolation_hil(
                shoot_mode=p353.SHOOT_MODE_MOVIE,
                marker_display="On",
                aspect_marker=ratio,
                hdmi_info_display="On",
            )
            self.assertTrue(r.admitted, ratio)
            self.assertEqual(r.effective_aspect_marker, ratio)
            self.assertTrue(r.marker_rendered_on_monitor)
            self.assertFalse(r.marker_rendered_on_hdmi)
            self.assertEqual(r.hdmi_marker_injected_pixels, 0)

    def test_42_78b_focus_magnifier_suppresses_marker_on_monitor(self) -> None:
        r = p353.simulate_grid_line_hdmi_vs_marker_guideframe_isolation_hil(
            shoot_mode=p353.SHOOT_MODE_MOVIE,
            marker_display="On",
            center_marker="On",
            guideframe="On",
            focus_magnifier_active=True,
        )
        self.assertTrue(r.admitted)
        self.assertFalse(r.marker_rendered_on_monitor)
        self.assertFalse(r.marker_rendered_on_hdmi)
        self.assertEqual(r.hdmi_marker_injected_pixels, 0)

    def test_43_78b_reset_immune_all_7_items_vs_initialize_restores(self) -> None:
        r_reset = p353.simulate_grid_line_hdmi_vs_marker_guideframe_isolation_hil(
            shoot_mode=p353.SHOOT_MODE_MOVIE,
            grid_line_display="On",
            grid_line_type="Square Grid",
            marker_display="On",
            center_marker="On",
            aspect_marker="1.85:1",
            safety_zone="80%",
            guideframe="On",
            camera_settings_reset_applied=True,
        )
        self.assertTrue(r_reset.admitted)
        self.assertFalse(r_reset.grid_and_marker_resettable)
        self.assertEqual(r_reset.effective_grid_line_display, "On")
        self.assertEqual(r_reset.effective_grid_line_type, "Square Grid")
        self.assertEqual(r_reset.effective_marker_display, "On")
        self.assertEqual(r_reset.effective_center_marker, "On")
        self.assertEqual(r_reset.effective_aspect_marker, "1.85:1")
        self.assertEqual(r_reset.effective_safety_zone, "80%")
        self.assertEqual(r_reset.effective_guideframe, "On")

        r_init = p353.simulate_grid_line_hdmi_vs_marker_guideframe_isolation_hil(
            shoot_mode=p353.SHOOT_MODE_MOVIE,
            grid_line_display="On",
            grid_line_type="Square Grid",
            marker_display="On",
            center_marker="On",
            aspect_marker="1.85:1",
            safety_zone="80%",
            guideframe="On",
            initialize_applied=True,
        )
        self.assertTrue(r_init.admitted)
        self.assertEqual(r_init.effective_grid_line_display, "Off")
        self.assertEqual(r_init.effective_grid_line_type, "Rule of 3rds Grid")
        self.assertEqual(r_init.effective_marker_display, "Off")
        self.assertEqual(r_init.effective_center_marker, "Off")
        self.assertEqual(r_init.effective_aspect_marker, "Off")
        self.assertEqual(r_init.effective_safety_zone, "Off")
        self.assertEqual(r_init.effective_guideframe, "Off")

    def test_44_78b_retired_movie_grid_keys_blocked_eopnotsupp(self) -> None:
        r = p353.simulate_grid_line_hdmi_vs_marker_guideframe_isolation_hil(
            operation="dormant_deleted_movie_grid"
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p353.EOPNOTSUPP_ERRNO)
        self.assertFalse(r.retired_movie_grid_keys_exposed)

    def test_45_78b_fx6_monitoring_marker_independent_vf_hdmi_gates(self) -> None:
        for cm in ("Off", "1", "2", "3", "4"):
            r = p353.simulate_grid_line_hdmi_vs_marker_guideframe_isolation_hil(
                body_profile=p353.BODY_MODEL_FX6,
                fw_version=p353.FW_VER_601,
                operation="fx6_marker_display",
                fx6_center_marker_mode=cm,
                fx6_guide_frame="On",
                fx6_vf_marker_on=True,
                fx6_hdmi_marker_on=False,
            )
            self.assertTrue(r.admitted, cm)
            self.assertEqual(r.fx6_center_marker_mode, cm)
            self.assertTrue(r.fx6_guide_frame_on)
            self.assertFalse(r.fx6_native_3mode_grid_exposed)
            self.assertTrue(r.marker_rendered_on_monitor)
            self.assertFalse(r.marker_rendered_on_hdmi)

        r_hdmi = p353.simulate_grid_line_hdmi_vs_marker_guideframe_isolation_hil(
            body_profile=p353.BODY_MODEL_FX6,
            fw_version=p353.FW_VER_601,
            operation="fx6_marker_display",
            fx6_center_marker_mode="2",
            hdmi_connected=True,
            fx6_hdmi_marker_on=True,
        )
        self.assertTrue(r_hdmi.admitted)
        self.assertTrue(r_hdmi.marker_rendered_on_hdmi)

    def test_46_78b_fx6_dormant_3mode_grid_blocked_eopnotsupp(self) -> None:
        r = p353.simulate_grid_line_hdmi_vs_marker_guideframe_isolation_hil(
            body_profile=p353.BODY_MODEL_FX6,
            fw_version=p353.FW_VER_601,
            operation="fx6_dormant_3mode_grid",
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p353.EOPNOTSUPP_ERRNO)
        self.assertFalse(r.fx6_native_3mode_grid_exposed)

    def test_47_78b_marker_on_without_any_sub_marker_draws_zero(self) -> None:
        r = p353.simulate_grid_line_hdmi_vs_marker_guideframe_isolation_hil(
            shoot_mode=p353.SHOOT_MODE_MOVIE,
            marker_display="On",
            center_marker="Off",
            aspect_marker="Off",
            safety_zone="Off",
            guideframe="Off",
        )
        self.assertTrue(r.admitted)
        self.assertFalse(r.marker_rendered_on_monitor)
        self.assertFalse(r.marker_rendered_on_hdmi)

    def test_48_78b_grid_off_with_hdmi_disconnected(self) -> None:
        r = p353.simulate_grid_line_hdmi_vs_marker_guideframe_isolation_hil(
            grid_line_display="On",
            hdmi_connected=False,
            hdmi_info_display="On",
        )
        self.assertTrue(r.admitted)
        self.assertTrue(r.grid_rendered_on_monitor)
        self.assertFalse(r.grid_rendered_on_hdmi)

    def test_49_78b_cross_body_operations_rejected(self) -> None:
        r1 = p353.simulate_grid_line_hdmi_vs_marker_guideframe_isolation_hil(
            body_profile=p353.BODY_MODEL_FX3,
            operation="fx6_marker_display",
        )
        self.assertFalse(r1.admitted)
        self.assertEqual(r1.errno_code, p353.EOPNOTSUPP_ERRNO)

        r2 = p353.simulate_grid_line_hdmi_vs_marker_guideframe_isolation_hil(
            body_profile=p353.BODY_MODEL_FX6,
            fw_version=p353.FW_VER_601,
            operation="render_overlays",
        )
        self.assertFalse(r2.admitted)
        self.assertEqual(r2.errno_code, p353.EOPNOTSUPP_ERRNO)

    def test_50_78b_invalid_inputs_raise_stage78_error(self) -> None:
        for bad in (
            dict(body_profile="FX30"),
            dict(fw_version="9.00"),
            dict(shoot_mode="Timelapse"),
            dict(operation="bad_op"),
            dict(grid_line_display="Auto"),
            dict(grid_line_type="Golden Ratio"),
            dict(marker_display="Auto"),
            dict(center_marker="Auto"),
            dict(aspect_marker="1.78:1"),
            dict(safety_zone="95%"),
            dict(guideframe="Auto"),
            dict(hdmi_info_display="Auto"),
            dict(rec_media_dur_hdmi_output="Never"),
            dict(raw_output="Auto"),
            dict(fx6_center_marker_mode="5"),
            dict(fx6_guide_frame="Auto"),
        ):
            with self.assertRaises(p353.Stage78Phase353Error, msg=str(bad)):
                p353.simulate_grid_line_hdmi_vs_marker_guideframe_isolation_hil(**bad)

    def test_51_78b_safety_zones_80_and_90_pct_monitored_without_hdmi(self) -> None:
        for sz in ("80%", "90%"):
            r = p353.simulate_grid_line_hdmi_vs_marker_guideframe_isolation_hil(
                shoot_mode=p353.SHOOT_MODE_MOVIE,
                marker_display="On",
                safety_zone=sz,
                hdmi_connected=True,
                hdmi_info_display="On",
            )
            self.assertTrue(r.admitted, sz)
            self.assertEqual(r.effective_safety_zone, sz)
            self.assertTrue(r.marker_rendered_on_monitor)
            self.assertFalse(r.marker_rendered_on_hdmi)
            self.assertEqual(r.hdmi_marker_injected_pixels, 0)

    def test_52_78b_still_mode_with_marker_off_allows_grid_on(self) -> None:
        r = p353.simulate_grid_line_hdmi_vs_marker_guideframe_isolation_hil(
            shoot_mode=p353.SHOOT_MODE_STILL,
            grid_line_display="On",
            marker_display="Off",
        )
        self.assertTrue(r.admitted)
        self.assertTrue(r.grid_rendered_on_monitor)
        self.assertFalse(r.marker_rendered_on_monitor)

    def test_53_78b_marker_display_off_disables_sub_markers(self) -> None:
        r = p353.simulate_grid_line_hdmi_vs_marker_guideframe_isolation_hil(
            shoot_mode=p353.SHOOT_MODE_MOVIE,
            marker_display="Off",
            center_marker="On",
            guideframe="On",
        )
        self.assertTrue(r.admitted)
        self.assertFalse(r.marker_rendered_on_monitor)
        self.assertFalse(r.marker_rendered_on_hdmi)

    def test_54_78b_raw_output_forces_clean_hdmi_even_if_grid_on(self) -> None:
        r = p353.simulate_grid_line_hdmi_vs_marker_guideframe_isolation_hil(
            shoot_mode=p353.SHOOT_MODE_MOVIE,
            grid_line_display="On",
            hdmi_connected=True,
            hdmi_info_display="On",
            rec_media_dur_hdmi_output="On",
            raw_output="On",
        )
        self.assertTrue(r.admitted)
        self.assertFalse(r.grid_rendered_on_hdmi)
        self.assertTrue(r.clean_hdmi_feed_active)

    def test_55_78b_pillar_b_payload_verified(self) -> None:
        rep = p353.run_phase353_areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_coemulation(
            force_clean_room=True
        )
        pb = rep["pillar_b_grid_line_hdmi_vs_marker_guideframe_isolation_hil"]
        self.assertTrue(pb["passed"])
        self.assertTrue(pb["hdmi_info_on_grid_passthrough_marker_isolated"]["grid_rendered_on_hdmi"])
        self.assertFalse(pb["hdmi_info_on_grid_passthrough_marker_isolated"]["marker_rendered_on_hdmi"])
        self.assertEqual(pb["hdmi_info_on_grid_passthrough_marker_isolated"]["hdmi_marker_injected_pixels"], 0)
        self.assertTrue(pb["clean_hdmi_off_strips_grid"]["clean_hdmi_feed_active"])

    # ------------------------------------------------------------------
    # Sub-Model 78C: [Save/Load Settings] CAMSET01..10.DAT Slot-1 EROFS=30 & FX6 All File (56..75)
    # ------------------------------------------------------------------

    def test_56_78c_slot1_erofs_30_blocks_camset_save_and_delete(self) -> None:
        for op in ("camset_save", "camset_delete"):
            for card in ("SDXC", "CFexpress Type A"):
                r = p353.simulate_saveload_camset_slot1_erofs_and_fx6_allfile_hil(
                    operation=op,
                    target_media="Slot 1",
                    card_type=card,
                    slot_index=1,
                    slot1_tier0_readonly=True,
                )
                self.assertFalse(r.admitted, (op, card))
                self.assertEqual(r.errno_code, p353.EROFS_ERRNO)
                self.assertTrue(r.slot1_erofs_triggered)
                self.assertEqual(r.slot1_data_sector_writes, 0)
                self.assertEqual(r.emmc_nflasha_write_count, 0)
                self.assertFalse(r.uses_pro_camera_path)

    def test_57_78c_slot1_locked_slot2_and_mediab_blocked_eopnotsupp(self) -> None:
        for op in ("camset_save", "camset_load", "camset_delete"):
            for tgt in ("Slot 2", "Media(B)"):
                r = p353.simulate_saveload_camset_slot1_erofs_and_fx6_allfile_hil(
                    operation=op,
                    target_media=tgt,
                    slot_index=1,
                )
                self.assertFalse(r.admitted, (op, tgt))
                self.assertEqual(r.errno_code, p353.EOPNOTSUPP_ERRNO)

    def test_58_78c_camset_load_sdxc_vs_cfexpress_paths_and_auto_reboot(self) -> None:
        r_sd = p353.simulate_saveload_camset_slot1_erofs_and_fx6_allfile_hil(
            operation="camset_load",
            target_media="Slot 1",
            card_type="SDXC",
            slot_index=1,
        )
        self.assertTrue(r_sd.admitted)
        self.assertEqual(r_sd.resolved_path, "/PRIVATE/SONY/SETTING/ILME-FX3/CAMSET/CAMSET01.DAT")
        self.assertFalse(r_sd.uses_pro_camera_path)
        self.assertTrue(r_sd.lib_saveload_verified)
        self.assertTrue(r_sd.auto_reboot_triggered)
        self.assertEqual(r_sd.slot1_data_sector_writes, 0)

        r_cfe = p353.simulate_saveload_camset_slot1_erofs_and_fx6_allfile_hil(
            operation="camset_load",
            target_media="Slot 1",
            card_type="CFexpress Type A",
            slot_index=10,
        )
        self.assertTrue(r_cfe.admitted)
        self.assertEqual(r_cfe.resolved_path, "/SONY/SETTING/ILME-FX3/CAMSET/CAMSET10.DAT")
        self.assertTrue(r_cfe.auto_reboot_triggered)

    def test_59_78c_card_max_10_vs_cloud_max_60_boundaries(self) -> None:
        r_11_card = p353.simulate_saveload_camset_slot1_erofs_and_fx6_allfile_hil(
            operation="camset_load", target_media="Slot 1", slot_index=11
        )
        self.assertFalse(r_11_card.admitted)
        self.assertEqual(r_11_card.errno_code, p353.EINVAL_ERRNO)

        r_60_cloud = p353.simulate_saveload_camset_slot1_erofs_and_fx6_allfile_hil(
            operation="camset_save", target_media="Cloud(Private)", slot_index=60
        )
        self.assertTrue(r_60_cloud.admitted)
        self.assertEqual(r_60_cloud.resolved_path, "cloud://Cloud(Private)/CAMSET60.DAT")

        r_61_cloud = p353.simulate_saveload_camset_slot1_erofs_and_fx6_allfile_hil(
            operation="camset_load", target_media="Cloud(Share)", slot_index=61
        )
        self.assertFalse(r_61_cloud.admitted)
        self.assertEqual(r_61_cloud.errno_code, p353.EINVAL_ERRNO)

    def test_60_78c_disabled_in_mr_recall_mode(self) -> None:
        for op in ("camset_save", "camset_load", "camset_delete"):
            r = p353.simulate_saveload_camset_slot1_erofs_and_fx6_allfile_hil(
                operation=op,
                target_media="Slot 1",
                slot_index=1,
                mr_recall_mode_active=True,
            )
            self.assertFalse(r.admitted, op)
            self.assertEqual(r.errno_code, p353.EOPNOTSUPP_ERRNO)

    def test_61_78c_cross_model_and_corrupt_checksum_blocked_by_libsaveload(self) -> None:
        for src_model in (p353.BODY_MODEL_FX6, p353.BODY_MODEL_FX30, p353.BODY_MODEL_A7S3):
            r = p353.simulate_saveload_camset_slot1_erofs_and_fx6_allfile_hil(
                operation="camset_load",
                target_media="Slot 1",
                source_body_model=src_model,
            )
            self.assertFalse(r.admitted, src_model)
            self.assertEqual(r.errno_code, p353.EINVAL_ERRNO)
            self.assertFalse(r.auto_reboot_triggered)

        r_bad_ck = p353.simulate_saveload_camset_slot1_erofs_and_fx6_allfile_hil(
            operation="camset_load",
            target_media="Slot 1",
            checksum_valid=False,
        )
        self.assertFalse(r_bad_ck.admitted)
        self.assertEqual(r_bad_ck.errno_code, p353.EINVAL_ERRNO)
        self.assertFalse(r_bad_ck.auto_reboot_triggered)

    def test_62_78c_ver_101_cannot_load_onto_ver_200_400_or_702(self) -> None:
        for dst_fw in (p353.FW_VER_200, p353.FW_VER_400, p353.FW_VER_702):
            r = p353.simulate_saveload_camset_slot1_erofs_and_fx6_allfile_hil(
                operation="camset_load",
                target_media="Slot 1",
                source_fw_version=p353.FW_VER_101,
                fw_version=dst_fw,
            )
            self.assertFalse(r.admitted, dst_fw)
            self.assertEqual(r.errno_code, p353.EINVAL_ERRNO)

        r_same = p353.simulate_saveload_camset_slot1_erofs_and_fx6_allfile_hil(
            operation="camset_load",
            target_media="Slot 1",
            source_fw_version=p353.FW_VER_400,
            fw_version=p353.FW_VER_702,
        )
        self.assertTrue(r_same.admitted)

    def test_63_78c_official_camset_exclusions_verified_non_leaked(self) -> None:
        self.assertEqual(len(p353.CAMSET_EXCLUDED_ITEMS), 20)
        for required_excl in (
            "IPTC Information",
            "Copyright Info",
            "External Flash Set.",
            "White Balance (Custom 1)",
            "Face Memory",
            "FTP Transfer Func.",
            "Language",
            "Area/Date/Time Setting",
        ):
            self.assertIn(required_excl, p353.CAMSET_EXCLUDED_ITEMS)
        r = p353.simulate_saveload_camset_slot1_erofs_and_fx6_allfile_hil(
            operation="camset_load", target_media="Slot 1", slot_index=1
        )
        self.assertEqual(r.excluded_items_count, 20)
        self.assertEqual(r.excluded_items_leaked_count, 0)

    def test_64_78c_ftpset_separate_slot1_locked_and_erofs_blocked(self) -> None:
        r_s2 = p353.simulate_saveload_camset_slot1_erofs_and_fx6_allfile_hil(
            operation="ftpset_save", target_media="Slot 2", slot_index=1
        )
        self.assertFalse(r_s2.admitted)
        self.assertEqual(r_s2.errno_code, p353.EOPNOTSUPP_ERRNO)

        r_erofs = p353.simulate_saveload_camset_slot1_erofs_and_fx6_allfile_hil(
            operation="ftpset_save", target_media="Slot 1", slot_index=1, slot1_tier0_readonly=True
        )
        self.assertFalse(r_erofs.admitted)
        self.assertEqual(r_erofs.errno_code, p353.EROFS_ERRNO)
        self.assertIn("FTPSET01.DAT", r_erofs.resolved_path)

    def test_65_78c_camera_set_memory_body_1_to_3_vs_card_m1_to_m4(self) -> None:
        for idx in (1, 2, 3):
            r = p353.simulate_saveload_camset_slot1_erofs_and_fx6_allfile_hil(
                operation="camera_set_memory_body", slot_index=idx
            )
            self.assertTrue(r.admitted, idx)
            self.assertFalse(r.auto_reboot_triggered)
            self.assertTrue(r.bundled_memory_slots_1_to_3_included)
        self.assertFalse(
            p353.simulate_saveload_camset_slot1_erofs_and_fx6_allfile_hil(
                operation="camera_set_memory_body", slot_index=4
            ).admitted
        )

        r_s1_erofs = p353.simulate_saveload_camset_slot1_erofs_and_fx6_allfile_hil(
            operation="camera_set_memory_card",
            slot_index=1,
            memory_recall_media="Slot 1",
            slot1_tier0_readonly=True,
        )
        self.assertFalse(r_s1_erofs.admitted)
        self.assertEqual(r_s1_erofs.errno_code, p353.EROFS_ERRNO)

        for m in (1, 2, 3, 4):
            r_s2 = p353.simulate_saveload_camset_slot1_erofs_and_fx6_allfile_hil(
                operation="camera_set_memory_card",
                slot_index=m,
                memory_recall_media="Slot 2",
                card_type="CFexpress Type A",
            )
            self.assertTrue(r_s2.admitted, m)
            self.assertEqual(r_s2.target_media, "Slot 2")
            self.assertEqual(r_s2.resolved_path, f"/SONY/SETTING/ILME-FX3/CAMPR{m:02d}A.DAT")

        self.assertFalse(
            p353.simulate_saveload_camset_slot1_erofs_and_fx6_allfile_hil(
                operation="camera_set_memory_card",
                slot_index=5,
                memory_recall_media="Slot 2",
            ).admitted
        )

    def test_66_78c_fx6_project_all_file_mediab_64_and_scene_file(self) -> None:
        r_ok = p353.simulate_saveload_camset_slot1_erofs_and_fx6_allfile_hil(
            body_profile=p353.BODY_MODEL_FX6,
            fw_version=p353.FW_VER_601,
            operation="fx6_all_file_load",
            target_media="Media(B)",
            card_type="CFexpress Type A",
            slot_index=64,
            fx6_all_file_load_network_data=True,
        )
        self.assertTrue(r_ok.admitted)
        self.assertEqual(r_ok.resolved_path, "/SONY/PRO/CAMERA/ILME-FX6/ALL64.ALL")
        self.assertTrue(r_ok.uses_pro_camera_path)
        self.assertTrue(r_ok.auto_reboot_triggered)
        self.assertTrue(r_ok.fx6_all_file_load_network_data)

        r_65 = p353.simulate_saveload_camset_slot1_erofs_and_fx6_allfile_hil(
            body_profile=p353.BODY_MODEL_FX6,
            fw_version=p353.FW_VER_601,
            operation="fx6_all_file_save",
            target_media="Media(B)",
            slot_index=65,
        )
        self.assertFalse(r_65.admitted)
        self.assertEqual(r_65.errno_code, p353.EINVAL_ERRNO)

        r_scn = p353.simulate_saveload_camset_slot1_erofs_and_fx6_allfile_hil(
            body_profile=p353.BODY_MODEL_FX6,
            fw_version=p353.FW_VER_601,
            operation="fx6_scene_file_save",
            target_media="Media(B)",
            card_type="CFexpress Type A",
            slot_index=1,
        )
        self.assertTrue(r_scn.admitted)
        self.assertEqual(r_scn.resolved_path, "/SONY/PRO/SCENE/SCN01.SCN")

    def test_67_78c_fx6_dormant_reference_file_blocked_eopnotsupp(self) -> None:
        r = p353.simulate_saveload_camset_slot1_erofs_and_fx6_allfile_hil(
            body_profile=p353.BODY_MODEL_FX6,
            fw_version=p353.FW_VER_601,
            operation="fx6_dormant_reference_file",
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p353.EOPNOTSUPP_ERRNO)
        self.assertFalse(r.fx6_reference_file_exposed)

    def test_68_78c_fx6_rejects_slot1_all_file_and_fx3_ops(self) -> None:
        r1 = p353.simulate_saveload_camset_slot1_erofs_and_fx6_allfile_hil(
            body_profile=p353.BODY_MODEL_FX6,
            fw_version=p353.FW_VER_601,
            operation="fx6_all_file_save",
            target_media="Slot 1",
        )
        self.assertFalse(r1.admitted)
        self.assertEqual(r1.errno_code, p353.EOPNOTSUPP_ERRNO)

        for op in ("camset_load", "camera_set_memory_body"):
            r2 = p353.simulate_saveload_camset_slot1_erofs_and_fx6_allfile_hil(
                body_profile=p353.BODY_MODEL_FX6,
                fw_version=p353.FW_VER_601,
                operation=op,
            )
            self.assertFalse(r2.admitted, op)
            self.assertEqual(r2.errno_code, p353.EOPNOTSUPP_ERRNO)

    def test_69_78c_fx3_rejects_fx6_operations(self) -> None:
        for op in ("fx6_all_file_save", "fx6_all_file_load", "fx6_scene_file_save", "fx6_dormant_reference_file"):
            r = p353.simulate_saveload_camset_slot1_erofs_and_fx6_allfile_hil(
                body_profile=p353.BODY_MODEL_FX3, operation=op
            )
            self.assertFalse(r.admitted, op)
            self.assertEqual(r.errno_code, p353.EOPNOTSUPP_ERRNO)

    def test_70_78c_slot_index_0_rejected_einval(self) -> None:
        r = p353.simulate_saveload_camset_slot1_erofs_and_fx6_allfile_hil(
            operation="camset_load", target_media="Slot 1", slot_index=0
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p353.EINVAL_ERRNO)

    def test_71_78c_cloud_share_save_succeeds_with_zero_slot1_writes(self) -> None:
        r = p353.simulate_saveload_camset_slot1_erofs_and_fx6_allfile_hil(
            operation="camset_save",
            target_media="Cloud(Share)",
            slot_index=5,
            slot1_tier0_readonly=True,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.resolved_path, "cloud://Cloud(Share)/CAMSET05.DAT")
        self.assertEqual(r.slot1_data_sector_writes, 0)
        self.assertFalse(r.slot1_erofs_triggered)

    def test_72_78c_camset_delete_cloud_succeeds_without_slot1_writes(self) -> None:
        r = p353.simulate_saveload_camset_slot1_erofs_and_fx6_allfile_hil(
            operation="camset_delete",
            target_media="Cloud(Private)",
            slot_index=1,
            slot1_tier0_readonly=True,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.slot1_data_sector_writes, 0)

    def test_73_78c_invalid_inputs_raise_stage78_error(self) -> None:
        for bad in (
            dict(body_profile="FX30"),
            dict(fw_version="9.00"),
            dict(operation="bad_op"),
            dict(target_media="USB"),
            dict(card_type="UHS-I"),
            dict(slot_index=-1),
            dict(source_body_model="FX9"),
            dict(source_fw_version="9.00"),
            dict(memory_recall_media="Cloud"),
        ):
            with self.assertRaises(p353.Stage78Phase353Error, msg=str(bad)):
                p353.simulate_saveload_camset_slot1_erofs_and_fx6_allfile_hil(**bad)

    def test_74_78c_card_memory_m1_on_slot2_sdxc_private_path(self) -> None:
        r = p353.simulate_saveload_camset_slot1_erofs_and_fx6_allfile_hil(
            operation="camera_set_memory_card",
            slot_index=1,
            memory_recall_media="Slot 2",
            card_type="SDXC",
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.resolved_path, "/PRIVATE/SONY/SETTING/ILME-FX3/CAMPR01A.DAT")

    def test_75_78c_pillar_c_payload_verified(self) -> None:
        rep = p353.run_phase353_areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_coemulation(
            force_clean_room=True
        )
        pc = rep["pillar_c_saveload_camset_slot1_erofs_and_fx6_allfile_hil"]
        self.assertTrue(pc["passed"])
        self.assertTrue(pc["slot1_save_erofs_blocked"]["slot1_erofs_triggered"])
        self.assertEqual(pc["slot1_save_erofs_blocked"]["errno_code"], p353.EROFS_ERRNO)
        self.assertTrue(pc["slot1_load_reboot_safe"]["auto_reboot_triggered"])
        self.assertEqual(len(pc["slot2_mr_crossmodel_fw_blocks"]), 4)

    # ------------------------------------------------------------------
    # Sub-Model 78D: Zero Sync Terminal, XLR-H1 vs HVL-LBPC & FX6 Zero GENLOCK (76..93)
    # ------------------------------------------------------------------

    def test_76_78d_zero_physical_pc_sync_terminal_and_dormant_spd_prty(self) -> None:
        for op in ("pc_sync_terminal", "dormant_flash_sync_spd_prty"):
            r = p353.simulate_sync_terminal_mishoe_xlrh1_and_fx6_genlock_hil(operation=op)
            self.assertFalse(r.admitted, op)
            self.assertEqual(r.errno_code, p353.EOPNOTSUPP_ERRNO)
            self.assertFalse(r.has_physical_pc_sync_terminal)
            self.assertFalse(r.dormant_sync_terminal_exposed)
            self.assertFalse(r.dormant_flash_sync_spd_prty_exposed)

    def test_77_78d_xlr_h1_mi_shoe_mutual_exclusion_and_passive_cold_shoes(self) -> None:
        for dev in ("HVL-LBPC", "MI_FLASH"):
            r = p353.simulate_sync_terminal_mishoe_xlrh1_and_fx6_genlock_hil(
                operation="video_light_mode",
                xlr_h1_attached=True,
                mi_shoe_device=dev,
            )
            self.assertFalse(r.admitted, dev)
            self.assertEqual(r.errno_code, p353.EBUSY_ERRNO)
            self.assertTrue(r.mishoe_xlr_h1_exclusion_triggered)
            self.assertTrue(r.xlr_h1_passive_cold_shoe_only)

    def test_78_78d_pmic_5v_overcurrent_guard_900ma_threshold(self) -> None:
        r_ok = p353.simulate_sync_terminal_mishoe_xlrh1_and_fx6_genlock_hil(
            operation="video_light_mode",
            mi_shoe_device="HVL-LBPC",
            pmic_5v_current_ma=900,
        )
        self.assertTrue(r_ok.admitted)
        self.assertFalse(r_ok.pmic_5v_overcurrent_blocked)

        r_over = p353.simulate_sync_terminal_mishoe_xlrh1_and_fx6_genlock_hil(
            operation="video_light_mode",
            mi_shoe_device="HVL-LBPC",
            pmic_5v_current_ma=901,
        )
        self.assertFalse(r_over.admitted)
        self.assertEqual(r_over.errno_code, p353.EPERM_ERRNO)
        self.assertTrue(r_over.pmic_5v_overcurrent_blocked)

    def test_79_78d_fx3_4_video_light_modes_incl_auto_across_all_pipelines(self) -> None:
        self.assertEqual(len(p353.FX3_VIDEO_LIGHT_MODES), 4)
        for sm in p353.VALID_SHOOT_MODES:
            for vlm in p353.FX3_VIDEO_LIGHT_MODES:
                r = p353.simulate_sync_terminal_mishoe_xlrh1_and_fx6_genlock_hil(
                    shoot_mode=sm,
                    operation="video_light_mode",
                    video_light_mode=vlm,
                    mi_shoe_device="HVL-LBPC",
                )
                self.assertTrue(r.admitted, (sm, vlm))
                self.assertEqual(r.effective_video_light_mode, vlm)

    def test_80_78d_still_only_external_flash_set_and_5_flash_modes(self) -> None:
        self.assertEqual(len(p353.FX3_FLASH_MODES), 5)
        for fm in p353.FX3_FLASH_MODES:
            r = p353.simulate_sync_terminal_mishoe_xlrh1_and_fx6_genlock_hil(
                shoot_mode=p353.SHOOT_MODE_STILL,
                operation="external_flash_set",
                flash_mode=fm,
                shutter_type="Mechanical",
                shutter_speed_denom=250,
                mi_shoe_device="MI_FLASH",
            )
            self.assertTrue(r.admitted, fm)
            self.assertEqual(r.effective_flash_mode, fm)
            self.assertFalse(r.flash_resettable)
            self.assertTrue(r.flash_excluded_from_camset)

        for sm in (p353.SHOOT_MODE_MOVIE, p353.SHOOT_MODE_SQ):
            r_blk = p353.simulate_sync_terminal_mishoe_xlrh1_and_fx6_genlock_hil(
                shoot_mode=sm,
                operation="external_flash_set",
                mi_shoe_device="MI_FLASH",
            )
            self.assertFalse(r_blk.admitted, sm)
            self.assertEqual(r_blk.errno_code, p353.EOPNOTSUPP_ERRNO)

    def test_81_78d_electronic_shutter_blocks_flash_and_xsync_cap_1_250(self) -> None:
        r_es = p353.simulate_sync_terminal_mishoe_xlrh1_and_fx6_genlock_hil(
            shoot_mode=p353.SHOOT_MODE_STILL,
            operation="external_flash_set",
            shutter_type="Electronic",
            mi_shoe_device="MI_FLASH",
        )
        self.assertFalse(r_es.admitted)
        self.assertEqual(r_es.errno_code, p353.EOPNOTSUPP_ERRNO)

        r_fast = p353.simulate_sync_terminal_mishoe_xlrh1_and_fx6_genlock_hil(
            shoot_mode=p353.SHOOT_MODE_STILL,
            operation="external_flash_set",
            shutter_type="Mechanical",
            shutter_speed_denom=500,
            mi_shoe_device="MI_FLASH",
        )
        self.assertFalse(r_fast.admitted)
        self.assertEqual(r_fast.errno_code, p353.EINVAL_ERRNO)

    def test_82_78d_mi_shoe_flash_high_voltage_and_reverse_polarity_blocked(self) -> None:
        for kw in (dict(flash_voltage_v=250.0), dict(flash_voltage_v=300.0), dict(reverse_polarity=True)):
            r = p353.simulate_sync_terminal_mishoe_xlrh1_and_fx6_genlock_hil(
                shoot_mode=p353.SHOOT_MODE_STILL,
                operation="external_flash_set",
                mi_shoe_device="MI_FLASH",
                **kw,
            )
            self.assertFalse(r.admitted, str(kw))
            self.assertEqual(r.errno_code, p353.EPERM_ERRNO)

    def test_83_78d_fx6_3_mode_video_light_set_rejects_auto(self) -> None:
        self.assertEqual(len(p353.FX6_VIDEO_LIGHT_MODES), 3)
        for vlm in p353.FX6_VIDEO_LIGHT_MODES:
            r = p353.simulate_sync_terminal_mishoe_xlrh1_and_fx6_genlock_hil(
                body_profile=p353.BODY_MODEL_FX6,
                fw_version=p353.FW_VER_601,
                operation="fx6_video_light_set",
                fx6_video_light_mode=vlm,
            )
            self.assertTrue(r.admitted, vlm)
            self.assertFalse(r.fx6_video_light_auto_supported)

        r_auto = p353.simulate_sync_terminal_mishoe_xlrh1_and_fx6_genlock_hil(
            body_profile=p353.BODY_MODEL_FX6,
            fw_version=p353.FW_VER_601,
            operation="fx6_video_light_set",
            fx6_video_light_mode="Auto",
        )
        self.assertFalse(r_auto.admitted)
        self.assertEqual(r_auto.errno_code, p353.EOPNOTSUPP_ERRNO)

    def test_84_78d_fx6_zero_physical_genlock_bnc_and_zero_still_flash(self) -> None:
        for op in ("fx6_genlock_sync", "fx6_still_flash_ui"):
            r = p353.simulate_sync_terminal_mishoe_xlrh1_and_fx6_genlock_hil(
                body_profile=p353.BODY_MODEL_FX6,
                fw_version=p353.FW_VER_601,
                operation=op,
            )
            self.assertFalse(r.admitted, op)
            self.assertEqual(r.errno_code, p353.EOPNOTSUPP_ERRNO)
            self.assertFalse(r.fx6_has_physical_genlock_bnc)
            self.assertFalse(r.fx6_dormant_genlock_exposed)
            self.assertFalse(r.fx6_still_flash_ui_exposed)

    def test_85_78d_fx6_switchable_tc_in_out_bnc(self) -> None:
        r_in = p353.simulate_sync_terminal_mishoe_xlrh1_and_fx6_genlock_hil(
            body_profile=p353.BODY_MODEL_FX6,
            fw_version=p353.FW_VER_601,
            operation="fx6_tc_bnc",
            fx6_tc_bnc_direction="IN",
        )
        self.assertTrue(r_in.admitted)
        self.assertEqual(r_in.fx6_tc_bnc_direction, "IN")
        self.assertTrue(r_in.fx6_tc_ext_lk_active)
        self.assertFalse(r_in.fx6_has_physical_genlock_bnc)

        r_out = p353.simulate_sync_terminal_mishoe_xlrh1_and_fx6_genlock_hil(
            body_profile=p353.BODY_MODEL_FX6,
            fw_version=p353.FW_VER_601,
            operation="fx6_tc_bnc",
            fx6_tc_bnc_direction="OUT",
        )
        self.assertTrue(r_out.admitted)
        self.assertEqual(r_out.fx6_tc_bnc_direction, "OUT")
        self.assertFalse(r_out.fx6_tc_ext_lk_active)

    def test_86_78d_cross_body_operations_rejected(self) -> None:
        for op in ("fx6_video_light_set", "fx6_still_flash_ui", "fx6_tc_bnc", "fx6_genlock_sync"):
            r1 = p353.simulate_sync_terminal_mishoe_xlrh1_and_fx6_genlock_hil(
                body_profile=p353.BODY_MODEL_FX3, operation=op
            )
            self.assertFalse(r1.admitted, op)
            self.assertEqual(r1.errno_code, p353.EOPNOTSUPP_ERRNO)

        for op in ("video_light_mode", "external_flash_set", "pc_sync_terminal"):
            r2 = p353.simulate_sync_terminal_mishoe_xlrh1_and_fx6_genlock_hil(
                body_profile=p353.BODY_MODEL_FX6, fw_version=p353.FW_VER_601, operation=op
            )
            self.assertFalse(r2.admitted, op)
            self.assertEqual(r2.errno_code, p353.EOPNOTSUPP_ERRNO)

    def test_87_78d_xlr_h1_alone_without_secondary_mi_shoe_device_allowed(self) -> None:
        r = p353.simulate_sync_terminal_mishoe_xlrh1_and_fx6_genlock_hil(
            operation="video_light_mode",
            xlr_h1_attached=True,
            mi_shoe_device="XLR-H1",
            pmic_5v_current_ma=400,
        )
        self.assertTrue(r.admitted)
        self.assertFalse(r.mishoe_xlr_h1_exclusion_triggered)

    def test_88_78d_overcurrent_blocked_even_with_xlr_h1_as_device(self) -> None:
        r = p353.simulate_sync_terminal_mishoe_xlrh1_and_fx6_genlock_hil(
            operation="video_light_mode",
            xlr_h1_attached=True,
            mi_shoe_device="XLR-H1",
            pmic_5v_current_ma=950,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p353.EPERM_ERRNO)
        self.assertTrue(r.pmic_5v_overcurrent_blocked)

    def test_89_78d_mi_shoe_none_ignores_pmic_current_for_passive_mode(self) -> None:
        r = p353.simulate_sync_terminal_mishoe_xlrh1_and_fx6_genlock_hil(
            operation="video_light_mode",
            mi_shoe_device="None",
            pmic_5v_current_ma=0,
        )
        self.assertTrue(r.admitted)

    def test_90_78d_still_flash_sub_250v_edge_249v_admitted(self) -> None:
        r = p353.simulate_sync_terminal_mishoe_xlrh1_and_fx6_genlock_hil(
            shoot_mode=p353.SHOOT_MODE_STILL,
            operation="external_flash_set",
            shutter_type="Mechanical",
            shutter_speed_denom=125,
            flash_voltage_v=249.9,
            reverse_polarity=False,
            mi_shoe_device="MI_FLASH",
        )
        self.assertTrue(r.admitted)

    def test_91_78d_invalid_inputs_raise_stage78_error(self) -> None:
        for bad in (
            dict(body_profile="FX30"),
            dict(fw_version="9.00"),
            dict(shoot_mode="Timelapse"),
            dict(operation="bad_op"),
            dict(video_light_mode="Strobe"),
            dict(flash_mode="High Speed"),
            dict(shutter_type="Global"),
            dict(shutter_speed_denom=0),
            dict(flash_voltage_v=-0.5),
            dict(mi_shoe_device="ColdShoeMic"),
            dict(pmic_5v_current_ma=-10),
            dict(fx6_tc_bnc_direction="BIDIR"),
        ):
            with self.assertRaises(p353.Stage78Phase353Error, msg=str(bad)):
                p353.simulate_sync_terminal_mishoe_xlrh1_and_fx6_genlock_hil(**bad)

    def test_92_78d_fx6_video_light_invalid_name_rejected_eopnotsupp(self) -> None:
        r = p353.simulate_sync_terminal_mishoe_xlrh1_and_fx6_genlock_hil(
            body_profile=p353.BODY_MODEL_FX6,
            fw_version=p353.FW_VER_601,
            operation="fx6_video_light_set",
            fx6_video_light_mode="UnknownMode",
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p353.EOPNOTSUPP_ERRNO)

    def test_93_78d_pillar_d_payload_verified(self) -> None:
        rep = p353.run_phase353_areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_coemulation(
            force_clean_room=True
        )
        pd = rep["pillar_d_sync_terminal_mishoe_xlrh1_and_fx6_genlock_hil"]
        self.assertTrue(pd["passed"])
        self.assertEqual(pd["video_light_auto_hvl_lbpc"]["effective_video_light_mode"], "Auto")
        self.assertEqual(pd["xlr_h1_mishoe_exclusion_blocked"]["errno_code"], p353.EBUSY_ERRNO)
        self.assertEqual(len(pd["dormant_sync_overvolt_fx6_genlock_blocks"]), 5)
        self.assertTrue(pd["fx6_tc_bnc_ext_lk"]["fx6_tc_ext_lk_active"])

    # ------------------------------------------------------------------
    # Milestone, Determinism, CLI & Suite Stage 78 Wiring (Tests 94..100)
    # ------------------------------------------------------------------

    def test_94_milestone_probe_exact_fields(self) -> None:
        probe = p353._build_stage78_milestone_probe()
        self.assertEqual(probe["phase_number"], 353)
        self.assertEqual(probe["stage_index"], 78)
        self.assertEqual(probe["stage_total"], 78)
        self.assertEqual(probe["milestone"], "78/78")
        self.assertTrue(probe["is_78th_stage_milestone"])
        self.assertEqual(probe["wave"], "Wave-68")
        self.assertEqual(probe["fx3_target_version"], "Ver. 7.02")
        self.assertEqual(probe["fx6_comparison_version"], "Ver. 6.01")

    def test_95_pillar_results_all_passed_in_clean_room(self) -> None:
        rep = p353.run_phase353_areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_coemulation(
            force_clean_room=True
        )
        for pillar_key in (
            "pillar_a_area_date_dst_rtc_fx6_clock_set_hil",
            "pillar_b_grid_line_hdmi_vs_marker_guideframe_isolation_hil",
            "pillar_c_saveload_camset_slot1_erofs_and_fx6_allfile_hil",
            "pillar_d_sync_terminal_mishoe_xlrh1_and_fx6_genlock_hil",
        ):
            self.assertTrue(rep[pillar_key]["passed"], pillar_key)

    def test_96_stage78_wrapper_and_suite_fast_determinism(self) -> None:
        s78 = suite.run_stage78_realhw_areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_hil(
            suite.CoEmulationConfig(force_clean_room=True)
        )
        self.assertEqual(
            s78["stage"],
            "stage78_realhw_areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_hil",
        )
        self.assertEqual(s78["schema"], p353.SCHEMA_ID)
        self.assertEqual(s78["phase_number"], 353)
        self.assertEqual(s78["milestone"], "78/78")
        self.assertTrue(s78["is_78th_stage_milestone"])
        self.assertTrue(s78["all_checks_passed"])
        self.assertEqual(len(s78["phase353_audit_digest_sha256"]), 64)

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
                    / "realhw_areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_coemulator.py"
                ),
                "--help",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc1.returncode, 0, proc1.stderr)
        self.assertIn("100%", proc1.stdout)
        self.assertIn("78/78", proc1.stdout)

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
        self.assertIn("78/78 Full-Board Stages", proc2.stdout)
        self.assertIn("--include-stage78", proc2.stdout)
        self.assertIn("--skip-stage78", proc2.stdout)
        self.assertIn("--no-include-stage78", proc2.stdout)
        self.assertIn("--skip-phase353", proc2.stdout)

    def test_98_standalone_cli_summary_json_and_no_hardcoded_python_path(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = p353.main(["--self-test", "--clean-room", "--summary"])
        self.assertEqual(rc, 0)
        self.assertIn("[PASS] Phase 353 Stage 78 (78/78 Stages)", buf.getvalue())

        buf_json = io.StringIO()
        with contextlib.redirect_stdout(buf_json):
            rc2 = p353.main(["--self-test", "--clean-room", "--json"])
        self.assertEqual(rc2, 0)
        parsed = json.loads(buf_json.getvalue())
        self.assertEqual(parsed["milestone"], "78/78")
        self.assertTrue(parsed["is_78th_stage_milestone"])
        self.assertTrue(parsed["all_checks_passed"])
        self.assertNotIn("\\x7fELF", buf_json.getvalue())

        mod_src = (
            FX3_VM_DIR
            / "realhw_areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_coemulator.py"
        ).read_text(encoding="utf-8")
        tst_src = Path(__file__).read_text(encoding="utf-8")
        forbidden = "/" + "usr/bin/" + "python3"
        self.assertNotIn(forbidden, mod_src)
        self.assertNotIn(forbidden, tst_src)

    def test_99_suite_default_config_enables_stage78_and_full_run_has_at_least_78_stages(self) -> None:
        cfg = suite.CoEmulationConfig()
        self.assertTrue(
            cfg.include_phase353_realhw_areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_hil
        )
        self.assertTrue(cfg.include_stage78)
        self.assertTrue(
            cfg.stage78_realhw_areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_hil
        )

        t0 = time.monotonic()
        rep = suite.run_fx3_vm_coemulation_suite(cfg)
        elapsed = time.monotonic() - t0
        self.assertTrue(rep["all_checks_passed"])
        stage_keys = [k for k in rep if re.match(r"^stage\d+_", k)]
        self.assertGreaterEqual(len(stage_keys), 78)
        self.assertIn(
            "stage78_realhw_areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_hil",
            rep,
        )
        s78 = rep["stage78_realhw_areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_hil"]
        self.assertTrue(s78["all_checks_passed"])
        self.assertTrue(s78["is_78th_stage_milestone"])
        self.assertEqual(s78["milestone"], "78/78")
        self.assertEqual(s78["phase_number"], 353)
        max_elapsed = 30.0 if IS_CI else 15.0
        self.assertLess(elapsed, max_elapsed)

    def test_100_suite_skip_flags_summary_cli_and_tamper_detection(self) -> None:
        for flag in ("--skip-stage78", "--no-include-stage78", "--skip-phase353"):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = suite.main([*_FAST_CLI_FLAGS, flag, "--json"])
            self.assertEqual(rc, 0)
            data = json.loads(buf.getvalue())
            self.assertNotIn(
                "stage78_realhw_areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_hil",
                data,
            )
            self.assertFalse(data["config"]["include_stage78"])

        buf_sum = io.StringIO()
        with contextlib.redirect_stdout(buf_sum):
            rc_sum = suite.main([*_FAST_CLI_FLAGS, "--include-stage78", "--summary"])
        self.assertEqual(rc_sum, 0)
        self.assertIn(
            "realhw_areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_hil=CLEAN_ROOM_SYNTHETIC("
            "m78=78/78,gmt=30,mkr_px=0,camset=10+60,sync_elf=0,genlock_bnc=0,s1_wr=0,emmc_wr=0)",
            buf_sum.getvalue(),
        )

        for attr, val in (
            ("IS_78TH_STAGE_MILESTONE", False),
            ("FX3_AREA_GMT_ZONES_COUNT", 31),
            ("FX3_AREA_HALF_HOUR_ZONES_COUNT", 5),
            ("FX3_USER_CR2032_SLOT_PRESENT", True),
            ("ILC2210_STATES_3_MONTHS_RETENTION", True),
            ("FX6_CLOCK_SET_DST_TOGGLE_EXPOSED", True),
            ("HDMI_MARKER_INJECTED_PIXELS", 1),
            ("CAMSET_SLOT2_BYPASS_EVENTS", 1),
            ("CAMSET_EXCLUDED_ITEMS_LEAKED_COUNT", 1),
            ("CAMSET_SLOT1_EROFS_BYPASS_EVENTS", 1),
            ("FX3_PHYSICAL_SYNC_TERMINAL_PRESENT", True),
            ("FX3_SYNCHRO_TERMINAL_ELF_HITS", 1),
            ("XLR_H1_MISHOE_COLLISION_BYPASS_EVENTS", 1),
            ("PMIC_5V_OVERCURRENT_BYPASS_EVENTS", 1),
            ("FX6_PHYSICAL_GENLOCK_BNC_PRESENT", True),
            ("SLOT1_DATA_SECTOR_WRITES", 1),
            ("EMMC_NFLASHA_WRITE_COUNT", 1),
            ("RAW_FIRMWARE_BYTES_LEAKED", 1),
        ):
            with unittest.mock.patch.object(p353, attr, val):
                rep = p353.run_phase353_areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_coemulation(
                    force_clean_room=True
                )
                self.assertFalse(rep["all_checks_passed"], attr)


if __name__ == "__main__":
    unittest.main()
