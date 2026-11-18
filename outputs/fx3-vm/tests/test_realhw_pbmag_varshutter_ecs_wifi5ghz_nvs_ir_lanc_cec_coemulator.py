#!/usr/bin/env python3
"""Unit tests for Phase 357 (Stage 79 — 79/79 Full-Board VM Co-Emulation Stages!):
Real-Hardware `ILME-FX3 Ver. 7.02` vs `ILME-FX6 Ver. 6.01` Wave-69:
- 79A: `Playback -> [Magnification]` (`Enlarge Image`, `Enlarge Initial Mag.`
  `Standard. Mag.`/`Previous Mag.`, `Enlarge Initial Position` `Focused Position`
  with Center fallback/`Center`, Reset-immune, `W/T` zoom lever, pinch/double-tap
  with `Touch Operation = On` and ELF typo `playback_zoom_maginify_by_pinch`,
  front/rear dial photo stepping at preserved zoom; **movies strictly inhibited**
  `playback_zoom::is_inhibition()` -> `base 0xe572` `"Unable to magnify."`
  `EOPNOTSUPP=95`) vs `ILME-FX6 Ver. 6.01` zero Still / zero Playback Enlarge
  (`Enlarge Screen` dormant), `THUMBNAIL`, `Rec Review` (`3s`/`10s`/`full`), and
  live `Focus Magnifier x3/x6` (Ver. 6.00+ `HDMI Focus Magnifier`),
- 79B: FX3 Ver. 7.02 Still-only Mechanical-shutter `[Anti-flicker Shoot.]`
  (`100/120Hz`, Resettable, disabled in Movie/`S&Q`, `Electronic Shutter`, and
  `BULB`) vs 100%% dormant `[Anti-flicker Set.]`, `[Var. Shutter]`
  (`BKID_APP_setting_high_res_ss`), `[Var. Shutter Set.]`, and `[Anti-flicker
  Tv Scan]` (`_g 0x60a8` empty string `""`, `EOPNOTSUPP=95`) vs `ILME-FX6`
  `Shooting > Shutter > ECS` (`23.99..8000Hz`, 6 frame-rate presets) +
  `Flicker Reduce`,
- 79C: `Wi-Fi` `backup_get_wi_fi_frequency_band_dst` SKU gate (`WW728473`
  `2.4/5GHz` with outdoor forced `2.4GHz` vs `WW558244` `2.4GHz`-only),
  Ver. 7.00+ removal of `WEP`/`WPA-PSK`/`IPsec` keeping `WPA2-PSK`/`WPA3-SAE`
  + mandatory `Access Authen. = On`, `[SSID/PW Reset]` Wi-Fi Direct only,
  `[Reset Network Set.]` preserves `[Airplane Mode] = On` (`[Initialize]`-only),
  Tier-0 `/dev/nflasha12` (`p12` 40MiB) & `/dev/nflasha13` (`p13` 4MiB)
  `MS_RDONLY` (`EROFS=30`, `rf_nvs_mutation_bytes == 0`) vs `ILME-FX6`
  `Access Point Mode` / `Station Mode` (`ILME-FX6V` 5GHz vs `ILME-FX6T` 2.4GHz),
- 79D: `[IR Remote Ctrl]` front `#5` sensor (NOT `#8` AF lamp; removed on 2025
  `ILME-FX3A`; Reset-immune; bypasses `[Power Save Start Time]`; mutually
  exclusive with `[Bluetooth Rmt Ctrl] = On` `EBUSY=16`), `[CTRL FOR HDMI]`
  (`BKID_APP_setting_ctrl_for_hmdi` typo, default `On`!, Reset-immune, 41
  `EVENT_INPUT_KEY_CEC_*` vectors & zero `CEC_REC`, forced `Off` on HIL bench),
  and zero physical FX3 `2.5mm LANC` / `3.5mm Grip Remote` vs `ILME-FX6`
  `#24` `2.5mm` 3-pole `REMOTE (LANC)` & `3.5mm` 4-pole Grip Remote (zero
  exposed FX6 `IR Remote`/`CTRL FOR HDMI` menus)
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
import realhw_pbmag_varshutter_ecs_wifi5ghz_nvs_ir_lanc_cec_coemulator as p357  # noqa: E402

IS_CI = os.environ.get("GITHUB_ACTIONS", "").lower() == "true"


def _fast_suite_kwargs(**overrides: object) -> dict:
    """Fast config skipping unrelated optional stages 4..78 for Stage 79 isolation tests."""
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
        include_stage78=False,
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
    "--skip-stage78",
]


class TestRealHwStage79PbMagVarShutterEcsWifi5GhzNvsIrLancCec(unittest.TestCase):
    # ------------------------------------------------------------------
    # Donor Audit, Bounded O_RDONLY & 4-Mode Fallback Tests (Tests 01..15)
    # ------------------------------------------------------------------

    def test_01_milestone_constants_79_of_79(self) -> None:
        self.assertEqual(p357.PHASE_NUMBER, 357)
        self.assertEqual(p357.STAGE_INDEX, 79)
        self.assertEqual(p357.STAGE_TOTAL, 79)
        self.assertEqual(p357.MILESTONE_LABEL, "79/79")
        self.assertTrue(p357.IS_79TH_STAGE_MILESTONE)
        self.assertEqual(len(p357.DONOR_RELPATHS), 15)
        self.assertEqual(len(p357.EXPECTED_DONOR_BYTES), 15)
        self.assertEqual(len(p357.EXPECTED_COMPACT_DONOR_SHA256), 12)
        self.assertEqual(len(p357.EXPECTED_LARGE_HEAD4K_SHA256), 3)
        self.assertEqual(len(p357.LARGE_DONOR_WINDOWS), 3)

    def test_02_hard_safety_and_wave69_redlines_locked(self) -> None:
        self.assertTrue(p357.P8_CP_MUTATION_FORBIDDEN)
        self.assertTrue(p357.CNFLASHA_USERSPACE_WRITE_BLOCKED)
        self.assertFalse(p357.PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(p357.EMMC_WRITES_AUTHORIZED)
        self.assertFalse(p357.CROSS_MODEL_FLASH_AUTHORIZED)
        self.assertFalse(p357.HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        self.assertFalse(p357.OVERALL_READY_FOR_HARDWARE_ATTACH)
        self.assertFalse(p357.ISP_WRITE_AUTHORIZED)
        self.assertFalse(p357.SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(p357.EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        self.assertFalse(p357.SLOT1_AVF_INFO_MUTATED)
        self.assertEqual(p357.SLOT1_DATA_SECTOR_WRITES, 0)
        self.assertEqual(p357.EMMC_NFLASHA_WRITE_COUNT, 0)
        self.assertEqual(p357.RF_PACKETS_TRANSMITTED, 0)
        self.assertEqual(p357.RF_NVS_MUTATION_BYTES, 0)
        self.assertEqual(p357.RAW_FIRMWARE_BYTES_LEAKED, 0)
        self.assertEqual(p357.FX3_PLAYBACK_MAGNIFY_ITEMS_COUNT, 3)
        self.assertTrue(p357.PLAYBACK_ZOOM_MAGINIFY_TYPO_MATCHED)
        self.assertFalse(p357.MOVIE_PLAYBACK_ENLARGE_SUPPORTED)
        self.assertEqual(p357.MOVIE_PLAYBACK_ENLARGE_BYPASS_EVENTS, 0)
        self.assertEqual(p357.PLAYBACK_MAGNIFY_RESET_WIPE_EVENTS, 0)
        self.assertFalse(p357.FX6_STILL_OR_PB_ENLARGE_SUPPORTED)
        self.assertEqual(p357.FX6_DORMANT_ENLARGE_SCREEN_EXPOSED_EVENTS, 0)
        self.assertTrue(p357.FX3_ANTI_FLICKER_SHOOT_ACTIVE)
        self.assertFalse(p357.FX3_VAR_SHUTTER_EXPOSED)
        self.assertFalse(p357.FX3_ANTI_FLICKER_TV_SCAN_EXPOSED)
        self.assertTrue(p357.FX3_SC_TV_SCAN_0X60A8_EMPTY_STRING)
        self.assertEqual(p357.DORMANT_VAR_SHUTTER_OR_TV_SCAN_EXPOSED_EVENTS, 0)
        self.assertEqual(p357.FX6_ECS_FREQ_MIN_HZ, 23.99)
        self.assertEqual(p357.FX6_ECS_FREQ_MAX_HZ, 8000.0)
        self.assertEqual(p357.FX6_ECS_PRESETS_COUNT, 6)
        self.assertEqual(p357.WW558244_5GHZ_BYPASS_EVENTS, 0)
        self.assertEqual(p357.OUTDOOR_5GHZ_BYPASS_EVENTS, 0)
        self.assertEqual(p357.DEPRECATED_WEP_WPA_IPSEC_ALLOWED_EVENTS, 0)
        self.assertEqual(p357.AIRPLANE_MODE_CLEARED_BY_RESET_NETWORK_EVENTS, 0)
        self.assertTrue(p357.P12_P13_MS_RDONLY_ENFORCED)
        self.assertEqual(p357.P12_CERT_SIZE_MIB, 40)
        self.assertEqual(p357.P13_RF_NVS_SIZE_MIB, 4)
        self.assertEqual(p357.P12_P13_WRITE_BYPASS_EVENTS, 0)
        self.assertEqual(p357.FX3_IR_FRONT_SENSOR_NUM, 5)
        self.assertEqual(p357.FX3_AF_ILLUMINATOR_SENSOR_NUM, 8)
        self.assertFalse(p357.FX3A_PHYSICAL_IR_SENSOR_PRESENT)
        self.assertEqual(p357.BT_IR_MUTEX_BYPASS_EVENTS, 0)
        self.assertTrue(p357.CTRL_FOR_HMDI_TYPO_MATCHED)
        self.assertEqual(p357.FX3_CEC_KEY_EVENTS_COUNT, 41)
        self.assertEqual(len(p357.FX3_CEC_41_KEY_EVENTS), 41)
        self.assertEqual(p357.FX3_CEC_REC_EVENT_COUNT, 0)
        self.assertEqual(p357.HIL_BENCH_CEC_HIJACK_BYPASS_EVENTS, 0)
        self.assertFalse(p357.FX3_PHYSICAL_LANC_25MM_PRESENT)
        self.assertEqual(p357.FX3_ACTIVE_LANC_BKID_HITS, 0)
        self.assertEqual(p357.FX6_LANC_25MM_PORT_NUM, 24)
        self.assertEqual(p357.FX6_GRIP_REMOTE_35MM_POLES, 4)
        self.assertEqual(p357.FX6_EXPOSED_IR_OR_CEC_EVENTS, 0)

    def test_03_clean_room_test_mode_both_env_vars(self) -> None:
        self.assertFalse(p357.clean_room_test_mode(env={}))
        self.assertTrue(p357.clean_room_test_mode(env={p357.ENV_FORCE_CLEAN_ROOM: "1"}))
        self.assertTrue(p357.clean_room_test_mode(env={p357.ENV_CLEAN_ROOM_TEST: "1"}))
        self.assertTrue(p357.clean_room_test_mode(force_clean_room=True, env={}))
        self.assertFalse(
            p357.clean_room_test_mode(
                force_clean_room=False,
                env={p357.ENV_FORCE_CLEAN_ROOM: "1", p357.ENV_CLEAN_ROOM_TEST: "1"},
            )
        )

    def test_04_resolve_mac_work_root_and_donorless_fallback(self) -> None:
        self.assertIsNone(p357.resolve_mac_work_root(work_root=None, env={}))
        self.assertIsNone(
            p357.resolve_mac_work_root(work_root="/nonexistent/wave69/path", env={})
        )
        self.assertIsNone(
            p357.resolve_mac_work_root(
                env={p357.ENV_MAC_WORK_ROOT: p357.CLEAN_ROOM_SENTINEL_DIRNAME}
            )
        )
        self.assertIsNone(
            p357.resolve_mac_work_root(
                env={p357.ENV_MAC_ROOT: p357.CLEAN_ROOM_SENTINEL_DIRNAME}
            )
        )
        with tempfile.TemporaryDirectory() as td:
            self.assertIsNone(p357.resolve_mac_work_root(work_root=td, env={}))

    def test_05_clean_room_synthetic_donor_audit_15_of_15(self) -> None:
        rep = p357.inspect_phase357_wave69_donors(force_clean_room=True)
        self.assertEqual(rep.source_mode, p357.SOURCE_MODE_CLEAN_ROOM)
        self.assertEqual(rep.donor_access_mode, p357.DONOR_ACCESS_MODE)
        self.assertEqual(rep.bounded_window_max_bytes, 4096)
        self.assertEqual(rep.donors_checked, 15)
        self.assertEqual(rep.donors_verified, 15)
        self.assertTrue(rep.all_contracts_verified)
        self.assertTrue(rep.fx3_maginify_typo_verified)
        self.assertTrue(rep.fx3_ctrl_for_hmdi_typo_verified)
        self.assertTrue(rep.fx3_cec_rec_absent_verified)
        self.assertTrue(rep.fx3_lanc_bkid_absent_verified)
        self.assertTrue(rep.fx3_wifi_band_dst_verified)
        self.assertTrue(rep.fx6_ecs_and_lanc_verified)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_06_clean_room_via_env_vars_and_nonexistent_work_root(self) -> None:
        for kw in (
            dict(env={p357.ENV_CLEAN_ROOM_TEST: "1"}),
            dict(env={p357.ENV_FORCE_CLEAN_ROOM: "1"}),
            dict(work_root=None, env={}),
            dict(work_root="/nonexistent/wave69/dir", env={}),
            dict(env={p357.ENV_MAC_WORK_ROOT: p357.CLEAN_ROOM_SENTINEL_DIRNAME}),
        ):
            r = p357.run_phase357_pbmag_varshutter_ecs_wifi5ghz_nvs_ir_lanc_cec_coemulation(
                **kw
            )
            self.assertTrue(r["all_checks_passed"], str(kw))
            self.assertEqual(r["source_mode"], p357.SOURCE_MODE_CLEAN_ROOM)
            self.assertEqual(r["redlines"]["raw_firmware_bytes_leaked"], 0)

    def test_07_local_donor_o_rdonly_audit_when_present(self) -> None:
        root = p357.resolve_mac_work_root()
        if root is None:
            self.skipTest("Local Mac/work donor tree not present in CI")
        rep = p357.inspect_phase357_wave69_donors(work_root=root)
        self.assertEqual(rep.source_mode, p357.SOURCE_MODE_LOCAL_DONOR)
        self.assertEqual(rep.donors_checked, 15)
        self.assertEqual(rep.donors_verified, 15)
        self.assertTrue(rep.all_contracts_verified)
        self.assertTrue(rep.fx3_maginify_typo_verified)
        self.assertTrue(rep.fx3_ctrl_for_hmdi_typo_verified)
        self.assertTrue(rep.fx3_cec_rec_absent_verified)
        self.assertTrue(rep.fx3_lanc_bkid_absent_verified)
        self.assertTrue(rep.fx3_wifi_band_dst_verified)
        self.assertTrue(rep.fx6_ecs_and_lanc_verified)
        self.assertEqual(rep.raw_firmware_bytes_leaked, 0)

    def test_08_bounded_window_enforces_4096b_cap_and_o_rdonly(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "sample.bin"
            f.write_bytes(b"ABCD" * 2048)
            chunk = p357._read_bounded_window_o_rdonly(f, 0, 4096)
            self.assertEqual(len(chunk), 4096)
            for bad_off, bad_len in ((-1, 16), (0, 0), (0, 4097)):
                with self.assertRaises(p357.Stage79Phase357Error):
                    p357._read_bounded_window_o_rdonly(f, bad_off, bad_len)

    def test_09_compact_cap_enforcement_rejects_oversize_or_empty(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            empty_f = Path(td) / "empty.bin"
            empty_f.write_bytes(b"")
            with self.assertRaises(p357.Stage79Phase357Error):
                p357._read_full_compact_o_rdonly(empty_f)

            big_f = Path(td) / "big.bin"
            big_f.write_bytes(b"X" * 2048)
            with self.assertRaises(p357.Stage79Phase357Error):
                p357._read_full_compact_o_rdonly(big_f, expected_max=1024)

    def test_10_local_donors_available_helper_consistency(self) -> None:
        self.assertFalse(p357._local_donors_available(work_root=None, env={}))
        self.assertFalse(
            p357._local_donors_available(force_clean_room=True, env={})
        )

    def test_11_large_donor_windows_all_within_4096_cap_and_aligned(self) -> None:
        for key, wins in p357.LARGE_DONOR_WINDOWS.items():
            self.assertGreaterEqual(len(wins), 2, key)
            for off, label, needle in wins:
                self.assertGreaterEqual(off, 0, label)
                self.assertGreater(len(needle), 0, label)
                self.assertLessEqual(len(needle), p357.BOUNDED_WINDOW_MAX_BYTES, label)

    def test_12_standalone_clean_room_and_local_determinism(self) -> None:
        r1 = p357.run_phase357_pbmag_varshutter_ecs_wifi5ghz_nvs_ir_lanc_cec_coemulation(
            force_clean_room=True
        )
        r2 = p357.run_phase357_pbmag_varshutter_ecs_wifi5ghz_nvs_ir_lanc_cec_coemulation(
            force_clean_room=True
        )
        self.assertTrue(r1["all_checks_passed"])
        self.assertEqual(r1["audit_digest_sha256"], r2["audit_digest_sha256"])

    def test_13_strip_wall_clock_removes_elapsed_seconds_recursively(self) -> None:
        sample = {
            "a": 1,
            "elapsed_seconds": 0.123,
            "nested": [{"elapsed_seconds": 9.9, "ok": True}],
        }
        cleaned = p357._strip_wall_clock(sample)
        self.assertEqual(cleaned, {"a": 1, "nested": [{"ok": True}]})

    def test_14_zero_raw_firmware_bytes_leaked_in_serialized_json(self) -> None:
        r = p357.run_phase357_pbmag_varshutter_ecs_wifi5ghz_nvs_ir_lanc_cec_coemulation(
            work_root=None
        )
        dumped = json.dumps(r)
        self.assertNotIn("\\x7fELF", dumped)
        self.assertEqual(r["redlines"]["raw_firmware_bytes_leaked"], 0)

    def test_15_mocked_work_root_none_explicit_mode_passes(self) -> None:
        with unittest.mock.patch.object(p357, "resolve_mac_work_root", return_value=None):
            r = p357.run_phase357_pbmag_varshutter_ecs_wifi5ghz_nvs_ir_lanc_cec_coemulation()
            self.assertTrue(r["all_checks_passed"])
            self.assertEqual(r["source_mode"], p357.SOURCE_MODE_CLEAN_ROOM)
            self.assertEqual(r["donor_audit"]["donors_verified"], 15)

    # ------------------------------------------------------------------
    # Sub-Model 79A: Playback -> [Magnification] vs FX6 Review (Tests 16..35)
    # ------------------------------------------------------------------

    def test_16_79a_fx3_playback_magnification_has_3_items_and_typo(self) -> None:
        self.assertEqual(len(p357.FX3_PLAYBACK_MAGNIFY_ITEMS), 3)
        r = p357.simulate_playback_magnification_and_fx6_review_hil(
            operation="enlarge_image",
            media_kind="still",
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.errno_code, 0)
        self.assertEqual(r.maginify_typo_symbol, "playback_zoom_maginify_by_pinch")
        self.assertEqual(r.inhibition_uxc_token, "Unable to magnify.")

    def test_17_79a_movie_playback_enlarge_strictly_inhibited(self) -> None:
        for op in ("enlarge_image", "pinch_zoom", "double_tap", "wt_lever", "dial_step_photo"):
            r = p357.simulate_playback_magnification_and_fx6_review_hil(
                operation=op,
                media_kind="movie",
            )
            self.assertFalse(r.admitted, op)
            self.assertEqual(r.errno_code, p357.EOPNOTSUPP_ERRNO)
            self.assertTrue(r.movie_enlarge_blocked)
            self.assertEqual(r.effective_mag_factor, 1.0)

    def test_18_79a_enlarge_initial_mag_standard_vs_previous(self) -> None:
        r_std = p357.simulate_playback_magnification_and_fx6_review_hil(
            operation="enlarge_image",
            media_kind="still",
            enlarge_initial_mag="Standard. Mag.",
            requested_mag_factor=2.5,
            previous_mag_factor=5.0,
        )
        self.assertTrue(r_std.admitted)
        self.assertEqual(r_std.effective_mag_factor, 2.5)

        r_prev = p357.simulate_playback_magnification_and_fx6_review_hil(
            operation="enlarge_image",
            media_kind="still",
            enlarge_initial_mag="Previous Mag.",
            requested_mag_factor=2.0,
            previous_mag_factor=5.0,
        )
        self.assertTrue(r_prev.admitted)
        self.assertEqual(r_prev.effective_mag_factor, 5.0)

    def test_19_79a_focused_position_falls_back_to_center_when_unavailable(self) -> None:
        r_fb = p357.simulate_playback_magnification_and_fx6_review_hil(
            operation="enlarge_image",
            media_kind="still",
            enlarge_initial_pos="Focused Position",
            focus_position_available=False,
        )
        self.assertTrue(r_fb.admitted)
        self.assertTrue(r_fb.focused_fallback_to_center)
        self.assertEqual(r_fb.effective_initial_position, "Center")

        r_ok = p357.simulate_playback_magnification_and_fx6_review_hil(
            operation="enlarge_image",
            media_kind="still",
            enlarge_initial_pos="Focused Position",
            focus_position_available=True,
        )
        self.assertFalse(r_ok.focused_fallback_to_center)
        self.assertEqual(r_ok.effective_initial_position, "Focused Position")

    def test_20_79a_magnify_settings_resist_reset_and_restore_on_initialize(self) -> None:
        r_reset = p357.simulate_playback_magnification_and_fx6_review_hil(
            operation="enlarge_image",
            media_kind="still",
            enlarge_initial_mag="Previous Mag.",
            enlarge_initial_pos="Center",
            camera_settings_reset_applied=True,
        )
        self.assertTrue(r_reset.admitted)
        self.assertFalse(r_reset.playback_magnify_resettable)
        self.assertEqual(r_reset.effective_initial_mag, "Previous Mag.")
        self.assertEqual(r_reset.effective_initial_position, "Center")

        r_init = p357.simulate_playback_magnification_and_fx6_review_hil(
            operation="enlarge_image",
            media_kind="still",
            enlarge_initial_mag="Previous Mag.",
            enlarge_initial_pos="Center",
            initialize_applied=True,
        )
        self.assertTrue(r_init.admitted)
        self.assertEqual(r_init.effective_initial_mag, "Standard. Mag.")
        self.assertEqual(r_init.effective_initial_position, "Focused Position")

    def test_21_79a_pinch_and_double_tap_require_touch_operation_on(self) -> None:
        for op in ("pinch_zoom", "double_tap"):
            r_off = p357.simulate_playback_magnification_and_fx6_review_hil(
                operation=op,
                media_kind="still",
                touch_operation="Off",
            )
            self.assertFalse(r_off.admitted, op)
            self.assertEqual(r_off.errno_code, p357.EOPNOTSUPP_ERRNO)

            r_on = p357.simulate_playback_magnification_and_fx6_review_hil(
                operation=op,
                media_kind="still",
                touch_operation="On",
                requested_mag_factor=3.5,
            )
            self.assertTrue(r_on.admitted, op)
            self.assertEqual(r_on.effective_mag_factor, 3.5)

    def test_22_79a_wt_lever_works_even_with_touch_off(self) -> None:
        r = p357.simulate_playback_magnification_and_fx6_review_hil(
            operation="wt_lever",
            media_kind="still",
            touch_operation="Off",
            requested_mag_factor=4.0,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.effective_mag_factor, 4.0)

    def test_23_79a_dial_step_photo_preserves_zoom_magnification(self) -> None:
        r = p357.simulate_playback_magnification_and_fx6_review_hil(
            operation="dial_step_photo",
            media_kind="still",
            requested_mag_factor=4.5,
        )
        self.assertTrue(r.admitted)
        self.assertTrue(r.zoom_preserved_across_photo_step)
        self.assertEqual(r.effective_mag_factor, 4.5)

    def test_24_79a_fx6_zero_still_zero_playback_enlarge_and_dormant_enlarge_screen(self) -> None:
        for op in (
            "enlarge_image",
            "pinch_zoom",
            "double_tap",
            "wt_lever",
            "dial_step_photo",
            "fx6_dormant_enlarge_screen",
        ):
            r = p357.simulate_playback_magnification_and_fx6_review_hil(
                body_profile=p357.BODY_MODEL_FX6,
                fw_version=p357.FW_VER_601,
                operation=op,
            )
            self.assertFalse(r.admitted, op)
            self.assertEqual(r.errno_code, p357.EOPNOTSUPP_ERRNO)
            self.assertFalse(r.fx6_still_or_pb_enlarge_supported)

    def test_25_79a_fx6_thumbnail_and_rec_review_durations(self) -> None:
        r_th = p357.simulate_playback_magnification_and_fx6_review_hil(
            body_profile=p357.BODY_MODEL_FX6,
            fw_version=p357.FW_VER_601,
            operation="fx6_thumbnail",
        )
        self.assertTrue(r_th.admitted)
        self.assertTrue(r_th.fx6_thumbnail_active)

        for dur in p357.VALID_FX6_REC_REVIEW_DURATIONS:
            r_rr = p357.simulate_playback_magnification_and_fx6_review_hil(
                body_profile=p357.BODY_MODEL_FX6,
                fw_version=p357.FW_VER_601,
                operation="fx6_rec_review",
                fx6_rec_review_duration=dur,
            )
            self.assertTrue(r_rr.admitted, dur)
            self.assertEqual(r_rr.fx6_rec_review_duration, dur)

    def test_26_79a_fx6_live_focus_magnifier_x3_x6_and_hdmi_fw_600(self) -> None:
        for scale, expected_val in (("x3", 3.0), ("x6", 6.0)):
            r = p357.simulate_playback_magnification_and_fx6_review_hil(
                body_profile=p357.BODY_MODEL_FX6,
                fw_version=p357.FW_VER_601,
                operation="fx6_focus_magnifier",
                fx6_focus_mag_scale=scale,
                fx6_hdmi_focus_magnifier="On",
            )
            self.assertTrue(r.admitted, scale)
            self.assertEqual(r.effective_mag_factor, expected_val)
            self.assertEqual(r.fx6_focus_mag_scale, scale)
            self.assertTrue(r.fx6_hdmi_focus_magnifier_active)

    def test_27_79a_fx3_rejects_fx6_specific_operations(self) -> None:
        for op in ("fx6_thumbnail", "fx6_rec_review", "fx6_focus_magnifier", "fx6_dormant_enlarge_screen"):
            r = p357.simulate_playback_magnification_and_fx6_review_hil(
                body_profile=p357.BODY_MODEL_FX3,
                operation=op,
            )
            self.assertFalse(r.admitted, op)
            self.assertEqual(r.errno_code, p357.EOPNOTSUPP_ERRNO)

    def test_28_79a_invalid_parameters_raise_stage79_error(self) -> None:
        for bad in (
            dict(body_profile="FX30"),
            dict(fw_version="9.00"),
            dict(operation="bad_op"),
            dict(media_kind="raw"),
            dict(enlarge_initial_mag="Max Mag."),
            dict(enlarge_initial_pos="TopLeft"),
            dict(touch_operation="Maybe"),
            dict(requested_mag_factor=0.5),
            dict(previous_mag_factor=0.9),
            dict(fx6_rec_review_duration="30s"),
            dict(fx6_focus_mag_scale="x12"),
            dict(fx6_hdmi_focus_magnifier="Auto"),
        ):
            with self.assertRaises(p357.Stage79Phase357Error, msg=str(bad)):
                p357.simulate_playback_magnification_and_fx6_review_hil(**bad)

    def test_29_79a_boundary_1x_magnification_admitted(self) -> None:
        r = p357.simulate_playback_magnification_and_fx6_review_hil(
            operation="enlarge_image",
            media_kind="still",
            requested_mag_factor=1.0,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.effective_mag_factor, 1.0)

    def test_30_79a_center_position_keeps_center_without_fallback_flag(self) -> None:
        r = p357.simulate_playback_magnification_and_fx6_review_hil(
            operation="enlarge_image",
            media_kind="still",
            enlarge_initial_pos="Center",
            focus_position_available=False,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.effective_initial_position, "Center")
        self.assertFalse(r.focused_fallback_to_center)

    def test_31_79a_initialize_overrides_reset_and_previous_mag(self) -> None:
        r = p357.simulate_playback_magnification_and_fx6_review_hil(
            operation="pinch_zoom",
            media_kind="still",
            enlarge_initial_mag="Previous Mag.",
            previous_mag_factor=6.0,
            requested_mag_factor=2.0,
            initialize_applied=True,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.effective_initial_mag, "Standard. Mag.")
        self.assertEqual(r.effective_mag_factor, 2.0)

    def test_32_79a_fx6_hdmi_focus_magnifier_off_state(self) -> None:
        r = p357.simulate_playback_magnification_and_fx6_review_hil(
            body_profile=p357.BODY_MODEL_FX6,
            fw_version=p357.FW_VER_601,
            operation="fx6_focus_magnifier",
            fx6_focus_mag_scale="x3",
            fx6_hdmi_focus_magnifier="Off",
        )
        self.assertTrue(r.admitted)
        self.assertFalse(r.fx6_hdmi_focus_magnifier_active)

    def test_33_79a_movie_inhibition_checked_before_touch_gate(self) -> None:
        r = p357.simulate_playback_magnification_and_fx6_review_hil(
            operation="pinch_zoom",
            media_kind="movie",
            touch_operation="Off",
        )
        self.assertFalse(r.admitted)
        self.assertTrue(r.movie_enlarge_blocked)
        self.assertEqual(r.errno_code, p357.EOPNOTSUPP_ERRNO)

    def test_34_79a_non_dial_step_does_not_claim_photo_step_preservation(self) -> None:
        r = p357.simulate_playback_magnification_and_fx6_review_hil(
            operation="wt_lever",
            media_kind="still",
        )
        self.assertTrue(r.admitted)
        self.assertFalse(r.zoom_preserved_across_photo_step)

    def test_35_79a_pillar_a_payload_verified(self) -> None:
        rep = p357.run_phase357_pbmag_varshutter_ecs_wifi5ghz_nvs_ir_lanc_cec_coemulation(
            force_clean_room=True
        )
        pa = rep["pillar_a_playback_magnification_and_fx6_review_hil"]
        self.assertTrue(pa["passed"])
        self.assertTrue(pa["movie_enlarge_blocked"]["movie_enlarge_blocked"])
        self.assertTrue(pa["dial_step_photo_preserves_zoom"]["zoom_preserved_across_photo_step"])
        self.assertTrue(pa["fx6_focus_magnifier"]["fx6_hdmi_focus_magnifier_active"])

    # ------------------------------------------------------------------
    # Sub-Model 79B: [Anti-flicker Shoot.] vs Dormant Var. Shutter & FX6 ECS (Tests 36..55)
    # ------------------------------------------------------------------

    def test_36_79b_still_mechanical_100_120hz_active_and_effective(self) -> None:
        for hz in (100, 120):
            r = p357.simulate_antiflicker_varshutter_and_fx6_ecs_hil(
                shoot_mode=p357.SHOOT_MODE_STILL,
                shutter_type="Mechanical",
                anti_flicker_shoot="On",
                mains_hz=hz,
            )
            self.assertTrue(r.admitted, hz)
            self.assertEqual(r.effective_anti_flicker_shoot, "On")
            self.assertTrue(r.anti_flicker_effective_for_mains_hz)
            self.assertTrue(r.anti_flicker_resettable)

    def test_37_79b_led_pwm_400hz_not_suppressed_by_still_anti_flicker(self) -> None:
        r = p357.simulate_antiflicker_varshutter_and_fx6_ecs_hil(
            shoot_mode=p357.SHOOT_MODE_STILL,
            shutter_type="Mechanical",
            anti_flicker_shoot="On",
            mains_hz=400,
        )
        self.assertTrue(r.admitted)
        self.assertFalse(r.anti_flicker_effective_for_mains_hz)

    def test_38_79b_anti_flicker_shoot_is_resettable(self) -> None:
        for kw in (
            dict(camera_settings_reset_applied=True),
            dict(initialize_applied=True),
        ):
            r = p357.simulate_antiflicker_varshutter_and_fx6_ecs_hil(
                shoot_mode=p357.SHOOT_MODE_STILL,
                anti_flicker_shoot="On",
                **kw,
            )
            self.assertTrue(r.admitted, str(kw))
            self.assertEqual(r.effective_anti_flicker_shoot, "Off")

    def test_39_79b_disabled_in_movie_and_sq_modes(self) -> None:
        for sm in (p357.SHOOT_MODE_MOVIE, p357.SHOOT_MODE_SQ):
            r = p357.simulate_antiflicker_varshutter_and_fx6_ecs_hil(
                shoot_mode=sm,
                anti_flicker_shoot="On",
            )
            self.assertFalse(r.admitted, sm)
            self.assertEqual(r.errno_code, p357.EOPNOTSUPP_ERRNO)

    def test_40_79b_disabled_under_electronic_shutter_and_bulb(self) -> None:
        r_es = p357.simulate_antiflicker_varshutter_and_fx6_ecs_hil(
            shoot_mode=p357.SHOOT_MODE_STILL,
            shutter_type="Electronic",
        )
        self.assertFalse(r_es.admitted)
        self.assertEqual(r_es.errno_code, p357.EOPNOTSUPP_ERRNO)

        r_bulb = p357.simulate_antiflicker_varshutter_and_fx6_ecs_hil(
            shoot_mode=p357.SHOOT_MODE_STILL,
            bulb_mode=True,
        )
        self.assertFalse(r_bulb.admitted)
        self.assertEqual(r_bulb.errno_code, p357.EOPNOTSUPP_ERRNO)

    def test_41_79b_dormant_var_shutter_and_tv_scan_100_pct_eopnotsupp(self) -> None:
        for op in (
            "dormant_anti_flicker_set",
            "dormant_var_shutter",
            "dormant_var_shutter_set",
            "dormant_anti_flicker_tv_scan",
        ):
            r = p357.simulate_antiflicker_varshutter_and_fx6_ecs_hil(operation=op)
            self.assertFalse(r.admitted, op)
            self.assertEqual(r.errno_code, p357.EOPNOTSUPP_ERRNO)
            self.assertFalse(r.var_shutter_exposed)
            self.assertFalse(r.anti_flicker_tv_scan_exposed)
            self.assertTrue(r.sc_tv_scan_0x60a8_empty_string)

    def test_42_79b_fx6_ecs_all_6_frame_rate_presets_verified(self) -> None:
        self.assertEqual(len(p357.FX6_ECS_FRAME_RATE_PRESETS), 6)
        for fps_lbl, expected_hz in p357.FX6_ECS_FRAME_RATE_PRESETS.items():
            r = p357.simulate_antiflicker_varshutter_and_fx6_ecs_hil(
                body_profile=p357.BODY_MODEL_FX6,
                fw_version=p357.FW_VER_601,
                operation="fx6_ecs",
                fx6_frame_rate=fps_lbl,
            )
            self.assertTrue(r.admitted, fps_lbl)
            self.assertEqual(r.fx6_ecs_freq_hz, expected_hz)
            self.assertTrue(r.fx6_ecs_enabled)

    def test_43_79b_fx6_ecs_custom_range_bounds_23_99_to_8000(self) -> None:
        for ok_hz in (23.99, 100.0, 240.0, 8000.0):
            r = p357.simulate_antiflicker_varshutter_and_fx6_ecs_hil(
                body_profile=p357.BODY_MODEL_FX6,
                fw_version=p357.FW_VER_601,
                operation="fx6_ecs",
                fx6_ecs_freq_hz=ok_hz,
            )
            self.assertTrue(r.admitted, ok_hz)

        for bad_hz in (23.98, 0.0, 8000.01):
            r = p357.simulate_antiflicker_varshutter_and_fx6_ecs_hil(
                body_profile=p357.BODY_MODEL_FX6,
                fw_version=p357.FW_VER_601,
                operation="fx6_ecs",
                fx6_ecs_freq_hz=bad_hz,
            )
            self.assertFalse(r.admitted, bad_hz)
            self.assertEqual(r.errno_code, p357.EINVAL_ERRNO)

    def test_44_79b_fx6_flicker_reduce_modes_and_freqs(self) -> None:
        for mode in p357.VALID_FX6_FLICKER_REDUCE_MODES:
            for freq in p357.VALID_FX6_FLICKER_REDUCE_FREQS:
                r = p357.simulate_antiflicker_varshutter_and_fx6_ecs_hil(
                    body_profile=p357.BODY_MODEL_FX6,
                    fw_version=p357.FW_VER_601,
                    operation="fx6_flicker_reduce",
                    fx6_flicker_reduce_mode=mode,
                    fx6_flicker_reduce_freq=freq,
                )
                self.assertTrue(r.admitted, (mode, freq))
                self.assertEqual(r.fx6_flicker_reduce_mode, mode)

    def test_45_79b_cross_body_operations_rejected_eopnotsupp(self) -> None:
        for op in ("fx6_ecs", "fx6_flicker_reduce"):
            r1 = p357.simulate_antiflicker_varshutter_and_fx6_ecs_hil(
                body_profile=p357.BODY_MODEL_FX3, operation=op
            )
            self.assertFalse(r1.admitted, op)
            self.assertEqual(r1.errno_code, p357.EOPNOTSUPP_ERRNO)

        r2 = p357.simulate_antiflicker_varshutter_and_fx6_ecs_hil(
            body_profile=p357.BODY_MODEL_FX6,
            fw_version=p357.FW_VER_601,
            operation="anti_flicker_shoot",
        )
        self.assertFalse(r2.admitted)
        self.assertEqual(r2.errno_code, p357.EOPNOTSUPP_ERRNO)

    def test_46_79b_anti_flicker_off_does_not_suppress_100hz(self) -> None:
        r = p357.simulate_antiflicker_varshutter_and_fx6_ecs_hil(
            shoot_mode=p357.SHOOT_MODE_STILL,
            anti_flicker_shoot="Off",
            mains_hz=100,
        )
        self.assertTrue(r.admitted)
        self.assertFalse(r.anti_flicker_effective_for_mains_hz)

    def test_47_79b_fx6_dormant_var_shutter_also_rejected(self) -> None:
        r = p357.simulate_antiflicker_varshutter_and_fx6_ecs_hil(
            body_profile=p357.BODY_MODEL_FX6,
            fw_version=p357.FW_VER_601,
            operation="dormant_var_shutter",
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p357.EOPNOTSUPP_ERRNO)

    def test_48_79b_fx6_ecs_disabled_toggle_still_admits_config(self) -> None:
        r = p357.simulate_antiflicker_varshutter_and_fx6_ecs_hil(
            body_profile=p357.BODY_MODEL_FX6,
            fw_version=p357.FW_VER_601,
            operation="fx6_ecs",
            fx6_ecs_enabled=False,
        )
        self.assertTrue(r.admitted)
        self.assertFalse(r.fx6_ecs_enabled)

    def test_49_79b_invalid_inputs_raise_stage79_error(self) -> None:
        for bad in (
            dict(body_profile="FX30"),
            dict(fw_version="9.00"),
            dict(operation="bad_op"),
            dict(shoot_mode="Auto"),
            dict(anti_flicker_shoot="High"),
            dict(shutter_type="Global"),
            dict(mains_hz=0),
            dict(fx6_frame_rate="120P"),
            dict(fx6_flicker_reduce_mode="Always"),
            dict(fx6_flicker_reduce_freq="75Hz"),
        ):
            with self.assertRaises(p357.Stage79Phase357Error, msg=str(bad)):
                p357.simulate_antiflicker_varshutter_and_fx6_ecs_hil(**bad)

    def test_50_79b_still_120hz_effective_true(self) -> None:
        r = p357.simulate_antiflicker_varshutter_and_fx6_ecs_hil(
            shoot_mode=p357.SHOOT_MODE_STILL,
            anti_flicker_shoot="On",
            mains_hz=120,
        )
        self.assertTrue(r.admitted)
        self.assertTrue(r.anti_flicker_effective_for_mains_hz)

    def test_51_79b_still_50hz_or_60hz_raw_not_100_120hz(self) -> None:
        r = p357.simulate_antiflicker_varshutter_and_fx6_ecs_hil(
            shoot_mode=p357.SHOOT_MODE_STILL,
            anti_flicker_shoot="On",
            mains_hz=60,
        )
        self.assertTrue(r.admitted)
        self.assertFalse(r.anti_flicker_effective_for_mains_hz)

    def test_52_79b_dormant_tv_scan_reports_empty_sc_string(self) -> None:
        r = p357.simulate_antiflicker_varshutter_and_fx6_ecs_hil(
            operation="dormant_anti_flicker_tv_scan"
        )
        self.assertFalse(r.admitted)
        self.assertTrue(r.sc_tv_scan_0x60a8_empty_string)
        self.assertFalse(r.anti_flicker_tv_scan_exposed)

    def test_53_79b_fx6_ecs_24p_exact_24_02_preset(self) -> None:
        r = p357.simulate_antiflicker_varshutter_and_fx6_ecs_hil(
            body_profile=p357.BODY_MODEL_FX6,
            fw_version=p357.FW_VER_601,
            operation="fx6_ecs",
            fx6_frame_rate="24P",
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.fx6_ecs_freq_hz, 24.02)

    def test_54_79b_fx6_ecs_25p_exact_25_02_preset(self) -> None:
        r = p357.simulate_antiflicker_varshutter_and_fx6_ecs_hil(
            body_profile=p357.BODY_MODEL_FX6,
            fw_version=p357.FW_VER_601,
            operation="fx6_ecs",
            fx6_frame_rate="25P",
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.fx6_ecs_freq_hz, 25.02)

    def test_55_79b_pillar_b_payload_verified(self) -> None:
        rep = p357.run_phase357_pbmag_varshutter_ecs_wifi5ghz_nvs_ir_lanc_cec_coemulation(
            force_clean_room=True
        )
        pb = rep["pillar_b_antiflicker_varshutter_and_fx6_ecs_hil"]
        self.assertTrue(pb["passed"])
        self.assertEqual(len(pb["dormant_var_shutter_tv_scan_and_lockouts"]), 7)
        self.assertEqual(pb["fx6_ecs_2398p_preset"]["fx6_ecs_freq_hz"], 23.99)

    # ------------------------------------------------------------------
    # Sub-Model 79C: Wi-Fi SKU Gate, WPA2/WPA3, p12/p13 MS_RDONLY & Airplane (Tests 56..75)
    # ------------------------------------------------------------------

    def test_56_79c_ww728473_supports_2_4ghz_and_5ghz(self) -> None:
        for band in ("2.4GHz", "5GHz"):
            r = p357.simulate_wifi_sku_wpa3_nvs_and_airplane_hil(
                sku_code="WW728473",
                requested_band=band,
                security_protocol="WPA3-SAE",
                access_authen="On",
            )
            self.assertTrue(r.admitted, band)
            self.assertEqual(r.available_bands, ("2.4GHz", "5GHz"))
            self.assertEqual(r.effective_band, band)
            self.assertEqual(r.rf_nvs_mutation_bytes, 0)
            self.assertEqual(r.rf_packets_transmitted, 0)

    def test_57_79c_ww558244_gates_5ghz_strictly_2_4ghz_only(self) -> None:
        r_blk = p357.simulate_wifi_sku_wpa3_nvs_and_airplane_hil(
            sku_code="WW558244",
            requested_band="5GHz",
        )
        self.assertFalse(r_blk.admitted)
        self.assertEqual(r_blk.errno_code, p357.EOPNOTSUPP_ERRNO)
        self.assertEqual(r_blk.available_bands, ("2.4GHz",))

        r_ok = p357.simulate_wifi_sku_wpa3_nvs_and_airplane_hil(
            sku_code="WW558244",
            requested_band="2.4GHz",
        )
        self.assertTrue(r_ok.admitted)
        self.assertEqual(r_ok.effective_band, "2.4GHz")

    def test_58_79c_outdoor_environment_forces_2_4ghz_blocks_5ghz(self) -> None:
        r = p357.simulate_wifi_sku_wpa3_nvs_and_airplane_hil(
            sku_code="WW728473",
            requested_band="5GHz",
            outdoor_environment=True,
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p357.EPERM_ERRNO)
        self.assertTrue(r.outdoor_forced_2_4ghz)
        self.assertEqual(r.effective_band, "2.4GHz")

    def test_59_79c_ver_700_plus_removes_wep_wpa_ipsec_mandates_access_authen(self) -> None:
        for legacy in ("WEP", "WPA-PSK", "IPsec"):
            r = p357.simulate_wifi_sku_wpa3_nvs_and_airplane_hil(
                security_protocol=legacy,
            )
            self.assertFalse(r.admitted, legacy)
            self.assertEqual(r.errno_code, p357.EOPNOTSUPP_ERRNO)

        r_no_auth = p357.simulate_wifi_sku_wpa3_nvs_and_airplane_hil(
            fw_version=p357.FW_VER_702,
            access_authen="Off",
        )
        self.assertFalse(r_no_auth.admitted)
        self.assertEqual(r_no_auth.errno_code, p357.EPERM_ERRNO)
        self.assertTrue(r_no_auth.access_authen_required)

    def test_60_79c_reset_network_set_does_not_clear_airplane_mode(self) -> None:
        r = p357.simulate_wifi_sku_wpa3_nvs_and_airplane_hil(
            operation="reset_network_set",
            airplane_mode="On",
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.effective_airplane_mode, "On")
        self.assertTrue(r.airplane_mode_preserved_by_reset_network)

    def test_61_79c_initialize_clears_airplane_mode_back_to_off(self) -> None:
        r = p357.simulate_wifi_sku_wpa3_nvs_and_airplane_hil(
            operation="initialize",
            airplane_mode="On",
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.effective_airplane_mode, "Off")

    def test_62_79c_ssid_pw_reset_direct_credentials_only(self) -> None:
        r = p357.simulate_wifi_sku_wpa3_nvs_and_airplane_hil(
            operation="ssid_pw_reset",
            airplane_mode="On",
        )
        self.assertTrue(r.admitted)
        self.assertTrue(r.ssid_pw_direct_only_reset)
        self.assertEqual(r.effective_airplane_mode, "On")

    def test_63_79c_p12_and_p13_ms_rdonly_fail_closed_erofs_30_zero_mutation(self) -> None:
        for part in ("p12_cert", "p13_rfnvs"):
            r = p357.simulate_wifi_sku_wpa3_nvs_and_airplane_hil(
                operation="rf_nvs_write_attempt",
                target_partition=part,
            )
            self.assertFalse(r.admitted, part)
            self.assertEqual(r.errno_code, p357.EROFS_ERRNO)
            self.assertTrue(r.p12_p13_ms_readonly)
            self.assertEqual(r.rf_nvs_mutation_bytes, 0)

    def test_64_79c_airplane_mode_blocks_all_active_wifi_rf_ops(self) -> None:
        for op in ("wifi_band_select", "ap_connect"):
            r = p357.simulate_wifi_sku_wpa3_nvs_and_airplane_hil(
                operation=op,
                airplane_mode="On",
            )
            self.assertFalse(r.admitted, op)
            self.assertEqual(r.errno_code, p357.EPERM_ERRNO)

    def test_65_79c_ap_connect_requires_wifi_connect_on(self) -> None:
        r = p357.simulate_wifi_sku_wpa3_nvs_and_airplane_hil(
            operation="ap_connect",
            wifi_connect="Off",
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p357.EPERM_ERRNO)

    def test_66_79c_fx6_access_point_vs_station_mode_and_sku_5ghz_gate(self) -> None:
        for mode in p357.VALID_FX6_WLAN_MODES:
            r = p357.simulate_wifi_sku_wpa3_nvs_and_airplane_hil(
                body_profile=p357.BODY_MODEL_FX6,
                fw_version=p357.FW_VER_601,
                operation="fx6_wireless_lan",
                sku_code="ILME-FX6V",
                requested_band="5GHz",
                fx6_wlan_mode=mode,
            )
            self.assertTrue(r.admitted, mode)
            self.assertEqual(r.fx6_wlan_mode, mode)

        r_t = p357.simulate_wifi_sku_wpa3_nvs_and_airplane_hil(
            body_profile=p357.BODY_MODEL_FX6,
            fw_version=p357.FW_VER_601,
            operation="fx6_wireless_lan",
            sku_code="ILME-FX6T",
            requested_band="5GHz",
        )
        self.assertFalse(r_t.admitted)
        self.assertEqual(r_t.errno_code, p357.EOPNOTSUPP_ERRNO)

    def test_67_79c_fx6_wireless_lan_blocked_by_wired_lan_or_simul_rec(self) -> None:
        for kw in (dict(fx6_wired_lan_on=True), dict(fx6_simul_rec_on=True)):
            r = p357.simulate_wifi_sku_wpa3_nvs_and_airplane_hil(
                body_profile=p357.BODY_MODEL_FX6,
                fw_version=p357.FW_VER_601,
                operation="fx6_wireless_lan",
                sku_code="ILME-FX6V",
                **kw,
            )
            self.assertFalse(r.admitted, str(kw))
            self.assertEqual(r.errno_code, p357.EBUSY_ERRNO)

    def test_68_79c_fx6_rejects_legacy_wep_wpa_ipsec_and_fx3_ops(self) -> None:
        r_leg = p357.simulate_wifi_sku_wpa3_nvs_and_airplane_hil(
            body_profile=p357.BODY_MODEL_FX6,
            fw_version=p357.FW_VER_601,
            operation="fx6_wireless_lan",
            sku_code="ILME-FX6V",
            security_protocol="WEP",
        )
        self.assertFalse(r_leg.admitted)
        self.assertEqual(r_leg.errno_code, p357.EOPNOTSUPP_ERRNO)

        r_op = p357.simulate_wifi_sku_wpa3_nvs_and_airplane_hil(
            body_profile=p357.BODY_MODEL_FX6,
            fw_version=p357.FW_VER_601,
            operation="wifi_band_select",
        )
        self.assertFalse(r_op.admitted)
        self.assertEqual(r_op.errno_code, p357.EOPNOTSUPP_ERRNO)

    def test_69_79c_fx3_rejects_fx6_wireless_lan_split(self) -> None:
        r = p357.simulate_wifi_sku_wpa3_nvs_and_airplane_hil(
            body_profile=p357.BODY_MODEL_FX3,
            operation="fx6_wireless_lan",
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p357.EOPNOTSUPP_ERRNO)

    def test_70_79c_target_partition_p12_blocks_even_under_other_op(self) -> None:
        r = p357.simulate_wifi_sku_wpa3_nvs_and_airplane_hil(
            operation="wifi_band_select",
            target_partition="p12_cert",
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p357.EROFS_ERRNO)

    def test_71_79c_wpa2_psk_admitted_with_access_authen_on(self) -> None:
        r = p357.simulate_wifi_sku_wpa3_nvs_and_airplane_hil(
            sku_code="WW728473",
            requested_band="5GHz",
            security_protocol="WPA2-PSK",
            access_authen="On",
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.effective_security, "WPA2-PSK")

    def test_72_79c_invalid_inputs_raise_stage79_error(self) -> None:
        for bad in (
            dict(body_profile="FX30"),
            dict(fw_version="9.00"),
            dict(operation="bad_op"),
            dict(sku_code="WW999999"),
            dict(requested_band="6GHz"),
            dict(security_protocol="TKIP"),
            dict(access_authen="Maybe"),
            dict(airplane_mode="Auto"),
            dict(wifi_connect="Auto"),
            dict(target_partition="p1"),
            dict(fx6_wlan_mode="Mesh"),
        ):
            with self.assertRaises(p357.Stage79Phase357Error, msg=str(bad)):
                p357.simulate_wifi_sku_wpa3_nvs_and_airplane_hil(**bad)

    def test_73_79c_fx6t_2_4ghz_allowed_when_clean(self) -> None:
        r = p357.simulate_wifi_sku_wpa3_nvs_and_airplane_hil(
            body_profile=p357.BODY_MODEL_FX6,
            fw_version=p357.FW_VER_601,
            operation="fx6_wireless_lan",
            sku_code="ILME-FX6T",
            requested_band="2.4GHz",
            fx6_wlan_mode="Station Mode",
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.effective_band, "2.4GHz")
        self.assertEqual(r.fx6_wlan_mode, "Station Mode")

    def test_74_79c_outdoor_2_4ghz_allowed_on_ww728473(self) -> None:
        r = p357.simulate_wifi_sku_wpa3_nvs_and_airplane_hil(
            sku_code="WW728473",
            requested_band="2.4GHz",
            outdoor_environment=True,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.effective_band, "2.4GHz")

    def test_75_79c_pillar_c_payload_verified(self) -> None:
        rep = p357.run_phase357_pbmag_varshutter_ecs_wifi5ghz_nvs_ir_lanc_cec_coemulation(
            force_clean_room=True
        )
        pc = rep["pillar_c_wifi_sku_wpa3_nvs_and_airplane_hil"]
        self.assertTrue(pc["passed"])
        self.assertTrue(pc["reset_network_preserves_airplane_mode"]["airplane_mode_preserved_by_reset_network"])
        self.assertEqual(pc["p12_cert_ms_readonly_erofs"]["errno_code"], p357.EROFS_ERRNO)
        self.assertEqual(pc["p13_rfnvs_ms_readonly_erofs"]["rf_nvs_mutation_bytes"], 0)
        self.assertEqual(len(pc["sku_outdoor_legacy_and_airplane_blocks"]), 6)

    # ------------------------------------------------------------------
    # Sub-Model 79D: Front #5 [IR Remote Ctrl], [CTRL FOR HDMI] CEC & LANC (Tests 76..93)
    # ------------------------------------------------------------------

    def test_76_79d_fx3_ir_remote_ctrl_maps_sensor_5_bypasses_power_save_reset_immune(self) -> None:
        r = p357.simulate_ir_ctrl_for_hdmi_cec_and_fx6_lanc_hil(
            operation="ir_remote_ctrl",
            ir_remote_ctrl="On",
            bluetooth_rmt_ctrl="Off",
            camera_settings_reset_applied=True,
        )
        self.assertTrue(r.admitted)
        self.assertEqual(r.ir_front_sensor_pin, 5)
        self.assertNotEqual(r.ir_front_sensor_pin, p357.FX3_AF_ILLUMINATOR_SENSOR_NUM)
        self.assertEqual(r.effective_ir_remote_ctrl, "On")
        self.assertFalse(r.ir_resettable)
        self.assertTrue(r.power_save_bypassed_by_ir)

    def test_77_79d_ir_remote_ctrl_mutually_exclusive_with_bt_rmt_ctrl(self) -> None:
        r = p357.simulate_ir_ctrl_for_hdmi_cec_and_fx6_lanc_hil(
            operation="ir_remote_ctrl",
            ir_remote_ctrl="On",
            bluetooth_rmt_ctrl="On",
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p357.EBUSY_ERRNO)
        self.assertTrue(r.bt_ir_mutex_blocked)

    def test_78_79d_fx3a_2025_physically_removed_front_5_ir_sensor(self) -> None:
        r = p357.simulate_ir_ctrl_for_hdmi_cec_and_fx6_lanc_hil(
            body_profile=p357.BODY_MODEL_FX3A,
            operation="ir_remote_ctrl",
            ir_remote_ctrl="On",
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p357.EOPNOTSUPP_ERRNO)
        self.assertIsNone(r.ir_front_sensor_pin)

    def test_79_79d_ctrl_for_hdmi_typo_reset_immune_and_hil_bench_firewall(self) -> None:
        r_unsafe = p357.simulate_ir_ctrl_for_hdmi_cec_and_fx6_lanc_hil(
            operation="ctrl_for_hdmi",
            ctrl_for_hdmi="On",
            hil_bench_attached=True,
        )
        self.assertFalse(r_unsafe.admitted)
        self.assertEqual(r_unsafe.errno_code, p357.EPERM_ERRNO)
        self.assertTrue(r_unsafe.hil_bench_unsafe_cec_on_blocked)
        self.assertEqual(r_unsafe.ctrl_for_hmdi_typo_symbol, "BKID_APP_setting_ctrl_for_hmdi")
        self.assertFalse(r_unsafe.ctrl_for_hdmi_resettable)

        r_safe = p357.simulate_ir_ctrl_for_hdmi_cec_and_fx6_lanc_hil(
            operation="ctrl_for_hdmi",
            ctrl_for_hdmi="Off",
            hil_bench_attached=True,
            camera_settings_reset_applied=True,
        )
        self.assertTrue(r_safe.admitted)
        self.assertEqual(r_safe.effective_ctrl_for_hdmi, "Off")
        self.assertTrue(r_safe.cec_firewall_blocked_injection)

    def test_80_79d_initialize_restores_ir_off_and_ctrl_for_hdmi_on(self) -> None:
        r_ir = p357.simulate_ir_ctrl_for_hdmi_cec_and_fx6_lanc_hil(
            operation="ir_remote_ctrl",
            ir_remote_ctrl="On",
            initialize_applied=True,
        )
        self.assertTrue(r_ir.admitted)
        self.assertEqual(r_ir.effective_ir_remote_ctrl, "Off")

        r_cec = p357.simulate_ir_ctrl_for_hdmi_cec_and_fx6_lanc_hil(
            operation="ctrl_for_hdmi",
            ctrl_for_hdmi="Off",
            hil_bench_attached=False,
            initialize_applied=True,
        )
        self.assertTrue(r_cec.admitted)
        self.assertEqual(r_cec.effective_ctrl_for_hdmi, "On")

    def test_81_79d_41_cec_key_vectors_verified_and_zero_cec_rec(self) -> None:
        self.assertEqual(len(p357.FX3_CEC_41_KEY_EVENTS), 41)
        for ev in p357.FX3_CEC_41_KEY_EVENTS:
            self.assertNotIn("CEC_REC", ev)
        for bad_ev in ("EVENT_INPUT_KEY_CEC_REC", "CEC_REC", "EVENT_INPUT_KEY_CEC_NONEXISTENT"):
            r = p357.simulate_ir_ctrl_for_hdmi_cec_and_fx6_lanc_hil(
                operation="cec_event_inject",
                ctrl_for_hdmi="On",
                hil_bench_attached=False,
                cec_key_event=bad_ev,
            )
            self.assertFalse(r.admitted, bad_ev)
            self.assertEqual(r.errno_code, p357.EOPNOTSUPP_ERRNO)
            self.assertFalse(r.cec_rec_event_present)

    def test_82_79d_cec_off_firewall_blocks_all_41_vectors(self) -> None:
        for ev in (
            "EVENT_INPUT_KEY_CEC_STANDBY_ON",
            "EVENT_INPUT_KEY_CEC_ROOT_MENU_ON",
            "EVENT_INPUT_KEY_CEC_PLAY_ON",
            "EVENT_INPUT_KEY_CEC_ENTER_ON",
        ):
            r = p357.simulate_ir_ctrl_for_hdmi_cec_and_fx6_lanc_hil(
                operation="cec_event_inject",
                ctrl_for_hdmi="Off",
                hil_bench_attached=True,
                cec_key_event=ev,
            )
            self.assertFalse(r.admitted, ev)
            self.assertEqual(r.errno_code, p357.EPERM_ERRNO)
            self.assertTrue(r.cec_firewall_blocked_injection)

    def test_83_79d_hil_bench_flags_unguarded_cec_injection_when_on(self) -> None:
        r = p357.simulate_ir_ctrl_for_hdmi_cec_and_fx6_lanc_hil(
            operation="cec_event_inject",
            ctrl_for_hdmi="On",
            hil_bench_attached=True,
            cec_key_event="EVENT_INPUT_KEY_CEC_STANDBY_ON",
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p357.EPERM_ERRNO)
        self.assertTrue(r.hil_bench_unsafe_cec_on_blocked)

    def test_84_79d_fx3_has_zero_physical_25mm_lanc_and_zero_grip_remote(self) -> None:
        for op in ("lanc_25mm", "grip_remote_35mm", "fx6_dormant_ir_or_cec"):
            r = p357.simulate_ir_ctrl_for_hdmi_cec_and_fx6_lanc_hil(
                body_profile=p357.BODY_MODEL_FX3,
                operation=op,
            )
            self.assertFalse(r.admitted, op)
            self.assertEqual(r.errno_code, p357.EOPNOTSUPP_ERRNO)
            self.assertFalse(r.has_physical_25mm_lanc)
            self.assertFalse(r.has_35mm_grip_remote)

    def test_85_79d_fx6_port_24_25mm_lanc_and_35mm_grip_remote_active(self) -> None:
        r_lanc = p357.simulate_ir_ctrl_for_hdmi_cec_and_fx6_lanc_hil(
            body_profile=p357.BODY_MODEL_FX6,
            fw_version=p357.FW_VER_601,
            operation="lanc_25mm",
        )
        self.assertTrue(r_lanc.admitted)
        self.assertTrue(r_lanc.has_physical_25mm_lanc)
        self.assertEqual(r_lanc.fx6_lanc_port_num, 24)

        r_grip = p357.simulate_ir_ctrl_for_hdmi_cec_and_fx6_lanc_hil(
            body_profile=p357.BODY_MODEL_FX6,
            fw_version=p357.FW_VER_601,
            operation="grip_remote_35mm",
        )
        self.assertTrue(r_grip.admitted)
        self.assertTrue(r_grip.has_35mm_grip_remote)

    def test_86_79d_fx6_zero_exposed_ir_remote_or_ctrl_for_hdmi_menus(self) -> None:
        for op in ("ir_remote_ctrl", "ctrl_for_hdmi", "cec_event_inject", "fx6_dormant_ir_or_cec"):
            r = p357.simulate_ir_ctrl_for_hdmi_cec_and_fx6_lanc_hil(
                body_profile=p357.BODY_MODEL_FX6,
                fw_version=p357.FW_VER_601,
                operation=op,
            )
            self.assertFalse(r.admitted, op)
            self.assertEqual(r.errno_code, p357.EOPNOTSUPP_ERRNO)
            self.assertEqual(r.effective_ir_remote_ctrl, "UNSUPPORTED")
            self.assertEqual(r.effective_ctrl_for_hdmi, "UNSUPPORTED")

    def test_87_79d_ir_off_even_with_bt_on_is_admitted(self) -> None:
        r = p357.simulate_ir_ctrl_for_hdmi_cec_and_fx6_lanc_hil(
            operation="ir_remote_ctrl",
            ir_remote_ctrl="Off",
            bluetooth_rmt_ctrl="On",
        )
        self.assertTrue(r.admitted)
        self.assertFalse(r.bt_ir_mutex_blocked)
        self.assertFalse(r.power_save_bypassed_by_ir)

    def test_88_79d_non_bench_consumer_tv_cec_vector_admitted(self) -> None:
        r = p357.simulate_ir_ctrl_for_hdmi_cec_and_fx6_lanc_hil(
            operation="cec_event_inject",
            ctrl_for_hdmi="On",
            hil_bench_attached=False,
            cec_key_event="EVENT_INPUT_KEY_CEC_PLAY_ON",
        )
        self.assertTrue(r.admitted)
        self.assertFalse(r.cec_firewall_blocked_injection)

    def test_89_79d_fx3a_also_blocks_lanc_eopnotsupp(self) -> None:
        r = p357.simulate_ir_ctrl_for_hdmi_cec_and_fx6_lanc_hil(
            body_profile=p357.BODY_MODEL_FX3A,
            operation="lanc_25mm",
        )
        self.assertFalse(r.admitted)
        self.assertEqual(r.errno_code, p357.EOPNOTSUPP_ERRNO)
        self.assertFalse(r.has_physical_25mm_lanc)

    def test_90_79d_non_bench_ctrl_for_hdmi_on_admitted(self) -> None:
        r = p357.simulate_ir_ctrl_for_hdmi_cec_and_fx6_lanc_hil(
            operation="ctrl_for_hdmi",
            ctrl_for_hdmi="On",
            hil_bench_attached=False,
        )
        self.assertTrue(r.admitted)
        self.assertFalse(r.hil_bench_unsafe_cec_on_blocked)

    def test_91_79d_invalid_inputs_raise_stage79_error(self) -> None:
        for bad in (
            dict(body_profile="FX30"),
            dict(fw_version="9.00"),
            dict(operation="bad_op"),
            dict(ir_remote_ctrl="Auto"),
            dict(bluetooth_rmt_ctrl="Auto"),
            dict(ctrl_for_hdmi="Auto"),
        ):
            with self.assertRaises(p357.Stage79Phase357Error, msg=str(bad)):
                p357.simulate_ir_ctrl_for_hdmi_cec_and_fx6_lanc_hil(**bad)

    def test_92_79d_all_41_cec_vectors_blocked_when_ctrl_for_hdmi_off(self) -> None:
        for ev in p357.FX3_CEC_41_KEY_EVENTS:
            r = p357.simulate_ir_ctrl_for_hdmi_cec_and_fx6_lanc_hil(
                operation="cec_event_inject",
                ctrl_for_hdmi="Off",
                hil_bench_attached=True,
                cec_key_event=ev,
            )
            self.assertFalse(r.admitted, ev)
            self.assertEqual(r.errno_code, p357.EPERM_ERRNO)

    def test_93_79d_pillar_d_payload_verified(self) -> None:
        rep = p357.run_phase357_pbmag_varshutter_ecs_wifi5ghz_nvs_ir_lanc_cec_coemulation(
            force_clean_room=True
        )
        pd = rep["pillar_d_ir_ctrl_for_hdmi_cec_and_fx6_lanc_hil"]
        self.assertTrue(pd["passed"])
        self.assertEqual(pd["ir_sensor5_power_save_bypass_reset_immune"]["ir_front_sensor_pin"], 5)
        self.assertTrue(pd["bt_ir_mutex_blocked"]["bt_ir_mutex_blocked"])
        self.assertTrue(pd["cec_hil_bench_on_blocked"]["hil_bench_unsafe_cec_on_blocked"])
        self.assertEqual(pd["fx6_25mm_lanc_port24"]["fx6_lanc_port_num"], 24)

    # ------------------------------------------------------------------
    # Milestone, Determinism, CLI & Suite Stage 79 Wiring (Tests 94..100)
    # ------------------------------------------------------------------

    def test_94_milestone_probe_exact_fields(self) -> None:
        probe = p357._build_stage79_milestone_probe()
        self.assertEqual(probe["phase_number"], 357)
        self.assertEqual(probe["stage_index"], 79)
        self.assertEqual(probe["stage_total"], 79)
        self.assertEqual(probe["milestone"], "79/79")
        self.assertTrue(probe["is_79th_stage_milestone"])
        self.assertEqual(probe["wave"], "Wave-69")
        self.assertEqual(probe["fx3_target_version"], "Ver. 7.02")
        self.assertEqual(probe["fx6_comparison_version"], "Ver. 6.01")

    def test_95_pillar_results_all_passed_in_clean_room(self) -> None:
        rep = p357.run_phase357_pbmag_varshutter_ecs_wifi5ghz_nvs_ir_lanc_cec_coemulation(
            force_clean_room=True
        )
        for pillar_key in (
            "pillar_a_playback_magnification_and_fx6_review_hil",
            "pillar_b_antiflicker_varshutter_and_fx6_ecs_hil",
            "pillar_c_wifi_sku_wpa3_nvs_and_airplane_hil",
            "pillar_d_ir_ctrl_for_hdmi_cec_and_fx6_lanc_hil",
        ):
            self.assertTrue(rep[pillar_key]["passed"], pillar_key)

    def test_96_stage79_wrapper_and_suite_fast_determinism(self) -> None:
        s79 = suite.run_stage79_realhw_pbmag_varshutter_ecs_wifi5ghz_nvs_ir_lanc_cec_hil(
            suite.CoEmulationConfig(force_clean_room=True)
        )
        self.assertEqual(
            s79["stage"],
            "stage79_realhw_pbmag_varshutter_ecs_wifi5ghz_nvs_ir_lanc_cec_hil",
        )
        self.assertEqual(s79["schema"], p357.SCHEMA_ID)
        self.assertEqual(s79["phase_number"], 357)
        self.assertEqual(s79["milestone"], "79/79")
        self.assertTrue(s79["is_79th_stage_milestone"])
        self.assertTrue(s79["all_checks_passed"])
        self.assertEqual(len(s79["phase357_audit_digest_sha256"]), 64)

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
                    / "realhw_pbmag_varshutter_ecs_wifi5ghz_nvs_ir_lanc_cec_coemulator.py"
                ),
                "--help",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc1.returncode, 0, proc1.stderr)
        self.assertIn("100%", proc1.stdout)
        self.assertIn("79/79", proc1.stdout)

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
        self.assertIn("79/79 Full-Board Stages", proc2.stdout)
        self.assertIn("--include-stage79", proc2.stdout)
        self.assertIn("--skip-stage79", proc2.stdout)
        self.assertIn("--no-include-stage79", proc2.stdout)
        self.assertIn("--skip-phase357", proc2.stdout)

    def test_98_standalone_cli_summary_json_and_no_hardcoded_python_path(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = p357.main(["--self-test", "--clean-room", "--summary"])
        self.assertEqual(rc, 0)
        self.assertIn("[PASS] Phase 357 Stage 79 (79/79 Stages)", buf.getvalue())

        buf_json = io.StringIO()
        with contextlib.redirect_stdout(buf_json):
            rc2 = p357.main(["--self-test", "--clean-room", "--json"])
        self.assertEqual(rc2, 0)
        parsed = json.loads(buf_json.getvalue())
        self.assertEqual(parsed["milestone"], "79/79")
        self.assertTrue(parsed["is_79th_stage_milestone"])
        self.assertTrue(parsed["all_checks_passed"])
        self.assertNotIn("\\x7fELF", buf_json.getvalue())

        mod_src = (
            FX3_VM_DIR
            / "realhw_pbmag_varshutter_ecs_wifi5ghz_nvs_ir_lanc_cec_coemulator.py"
        ).read_text(encoding="utf-8")
        tst_src = Path(__file__).read_text(encoding="utf-8")
        forbidden = "/" + "usr/bin/" + "python3"
        self.assertNotIn(forbidden, mod_src)
        self.assertNotIn(forbidden, tst_src)

    def test_99_suite_default_config_enables_stage79_and_full_run_has_at_least_79_stages(self) -> None:
        cfg = suite.CoEmulationConfig()
        self.assertTrue(
            cfg.include_phase357_realhw_pbmag_varshutter_ecs_wifi5ghz_nvs_ir_lanc_cec_hil
        )
        self.assertTrue(cfg.include_stage79)
        self.assertTrue(
            cfg.stage79_realhw_pbmag_varshutter_ecs_wifi5ghz_nvs_ir_lanc_cec_hil
        )

        t0 = time.monotonic()
        rep = suite.run_fx3_vm_coemulation_suite(cfg)
        elapsed = time.monotonic() - t0
        self.assertTrue(rep["all_checks_passed"])
        stage_keys = [k for k in rep if re.match(r"^stage\d+_", k)]
        self.assertGreaterEqual(len(stage_keys), 79)
        self.assertIn(
            "stage79_realhw_pbmag_varshutter_ecs_wifi5ghz_nvs_ir_lanc_cec_hil",
            rep,
        )
        s79 = rep["stage79_realhw_pbmag_varshutter_ecs_wifi5ghz_nvs_ir_lanc_cec_hil"]
        self.assertTrue(s79["all_checks_passed"])
        self.assertTrue(s79["is_79th_stage_milestone"])
        self.assertEqual(s79["milestone"], "79/79")
        self.assertEqual(s79["phase_number"], 357)
        max_elapsed = 30.0 if IS_CI else 15.0
        self.assertLess(elapsed, max_elapsed)

    def test_100_suite_skip_flags_summary_cli_and_tamper_detection(self) -> None:
        for flag in ("--skip-stage79", "--no-include-stage79", "--skip-phase357"):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = suite.main([*_FAST_CLI_FLAGS, flag, "--json"])
            self.assertEqual(rc, 0)
            data = json.loads(buf.getvalue())
            self.assertNotIn(
                "stage79_realhw_pbmag_varshutter_ecs_wifi5ghz_nvs_ir_lanc_cec_hil",
                data,
            )
            self.assertFalse(data["config"]["include_stage79"])

        buf_sum = io.StringIO()
        with contextlib.redirect_stdout(buf_sum):
            rc_sum = suite.main([*_FAST_CLI_FLAGS, "--include-stage79", "--summary"])
        self.assertEqual(rc_sum, 0)
        self.assertIn(
            "realhw_pbmag_varshutter_ecs_wifi5ghz_nvs_ir_lanc_cec_hil=CLEAN_ROOM_SYNTHETIC("
            "m79=79/79,mv_enl=0,varsh=0,rf_mut=0,cec=41(rec=0),fx3_lanc=0,s1_wr=0,emmc_wr=0)",
            buf_sum.getvalue(),
        )

        for attr, val in (
            ("IS_79TH_STAGE_MILESTONE", False),
            ("FX3_PLAYBACK_MAGNIFY_ITEMS_COUNT", 4),
            ("MOVIE_PLAYBACK_ENLARGE_SUPPORTED", True),
            ("MOVIE_PLAYBACK_ENLARGE_BYPASS_EVENTS", 1),
            ("PLAYBACK_MAGNIFY_RESET_WIPE_EVENTS", 1),
            ("FX6_STILL_OR_PB_ENLARGE_SUPPORTED", True),
            ("FX3_VAR_SHUTTER_EXPOSED", True),
            ("FX3_ANTI_FLICKER_TV_SCAN_EXPOSED", True),
            ("DORMANT_VAR_SHUTTER_OR_TV_SCAN_EXPOSED_EVENTS", 1),
            ("WW558244_5GHZ_BYPASS_EVENTS", 1),
            ("OUTDOOR_5GHZ_BYPASS_EVENTS", 1),
            ("DEPRECATED_WEP_WPA_IPSEC_ALLOWED_EVENTS", 1),
            ("AIRPLANE_MODE_CLEARED_BY_RESET_NETWORK_EVENTS", 1),
            ("P12_P13_MS_RDONLY_ENFORCED", False),
            ("P12_P13_WRITE_BYPASS_EVENTS", 1),
            ("FX3A_PHYSICAL_IR_SENSOR_PRESENT", True),
            ("BT_IR_MUTEX_BYPASS_EVENTS", 1),
            ("FX3_CEC_REC_EVENT_COUNT", 1),
            ("HIL_BENCH_CEC_HIJACK_BYPASS_EVENTS", 1),
            ("FX3_PHYSICAL_LANC_25MM_PRESENT", True),
            ("FX3_ACTIVE_LANC_BKID_HITS", 1),
            ("RF_NVS_MUTATION_BYTES", 1),
            ("SLOT1_DATA_SECTOR_WRITES", 1),
            ("EMMC_NFLASHA_WRITE_COUNT", 1),
            ("RAW_FIRMWARE_BYTES_LEAKED", 1),
        ):
            with unittest.mock.patch.object(p357, attr, val):
                rep = p357.run_phase357_pbmag_varshutter_ecs_wifi5ghz_nvs_ir_lanc_cec_coemulation(
                    force_clean_room=True
                )
                self.assertFalse(rep["all_checks_passed"], attr)


if __name__ == "__main__":
    unittest.main()
