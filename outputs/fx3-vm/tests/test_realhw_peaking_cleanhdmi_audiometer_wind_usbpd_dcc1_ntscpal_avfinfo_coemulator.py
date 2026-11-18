#!/usr/bin/env python3
"""Unit tests for Phase 360 (Stage 80 — 80/80 Full-Board VM Co-Emulation Stages!):
Real-Hardware `ILME-FX3 Ver. 7.02` vs `ILME-FX6 Ver. 6.01` Wave-70:
- 80A: `Shooting -> [Focus]` `[Peaking Display]` (`_f 0x6280`, wheel right
  default `Peaking Display Select`), `[Peaking Level]` (`High`/`Mid`/`Low`),
  `[Peaking Color]` (`Red`/`Yellow`/`Blue`/`White`), Reset-resistant
  (`Not available`, `[Initialize]`-only), ZERO HDMI output even with
  `[HDMI Info. Display] = On` / `RAW Output = On` (`G83`), `[Focus Magnifier]`
  `x1.0`/`x4.0`/`x8.0` coexistence (0 `PRM_HAITA_peaking*focus_mag*`), dormant
  on-body `[Focus Map]` (`EOPNOTSUPP=95`, wireless `Monitor & Control` Ver.
  2.1.0+ only, unavailable over USB) vs FX6 `Monitoring > Peaking` (`B&W`/Red/
  Yellow/Blue, VF/LCD only, independent `SDI`/`HDMI` `Output Display`) &
  disproved `Peaking Type` / `Peaking Frequency` (0 `appFw.so` symbols despite
  dormant `ns2 0x4501/0x4503`),
- 80B: FX3 Ver. 2.00+..7.02 permanently removed standalone `[Audio Level Display]`
  (`_f 0x7a36` Ver. 1.x legacy; auto-rendered via `DISP`/`BIG6` `2ch`/`4ch`,
  `0ch` hidden in `S&Q`, Remote SDK `CrSDK` read-only), exact 5 `Can be reset`
  items under `Shooting -> [Audio Recording]` (`[Audio Rec Level]` `0..31`
  default `26` `adj_audio_rec_level_defult` permanent limiter, `[Audio Out Timing]`,
  `[Wind Noise Reduct.]` `Off`/`On` ONLY rejecting dormant `Auto`/`On Advanced`
  and active ONLY on internal stereo mic via `MSG_ID_INFRABB_ADF_IN_SET_LOW_CUT`,
  bypassed on `3.5mm MIC`/`XLR-H1`/`S&Q`), `3.5mm MIC > XLR-H1 DIGITAL
  (Off/100Hz/300Hz hardware LOW CUT) > Internal Mic` priority vs FX6
  `CH1..CH4 Wind Filter` (0 handle physical `LOW CUT`) & 6-step `Limiter Mode`,
- 80C: `Setup -> [USB] -> [USB Power Supply]` (`On` default, Reset-resistant,
  USB Type-C only `base 0xe931` rejecting `Multi/Micro-USB`; `9V/3A 27W+` vs
  `5V/1.5A LOW` drain), `libUsbBusPower.so` mandatory `NP-FZ100` (zero
  battery-less boot, instant power loss on hot-pull), power-ON supplies power
  ONLY without charging (`CHARGE` LED off, `Power Save` bypass `G82`) vs
  power-OFF charging (`10C..30C` window, fast-blink fault outside window),
  `DC-C1` (`>=65W` PD + `5A` cable locking monitor brightness Max) vs FX6
  `19.5V DC IN` (`18.0..20.5V`, `16.5V/15.5V` warnings, true battery-less boot,
  seamless `DC IN -> BP-U` pull-over, hot-replug reboot guard, USB-C incapable),
- 80D: `[NTSC/PAL Selector]` (`backup_get_ntsc_pal_selector_dst`: `J1` locked out,
  `U2` -> `Running on PAL.`, `CE/CEC/E33` -> `Running on NTSC.`), Ver. 7.02
  XAVC-only cold reboot without mandatory card format, cross-region playback
  block (`_g 0x61ca`/`0x644e`), `AVF_INFO` `Create?`/`Update?`/`[Recover Image DB]`
  (`<10%`/`<6400mV` refusal `EAGAIN=11`) with Tier-0 `Slot 1` enforcing hard
  `EROFS=30` (`slot1_data_sector_writes == 0`) vs FX6 `Project > Rec Format >
  Frequency` (`59.94..23.98Hz`, reboot prompt `ns2 0x40ab`, `Thumbnail` filter)
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
import realhw_peaking_cleanhdmi_audiometer_wind_usbpd_dcc1_ntscpal_avfinfo_coemulator as p360  # noqa: E402

IS_CI = os.environ.get("GITHUB_ACTIONS", "").lower() == "true"


def _fast_suite_kwargs(**overrides: object) -> dict:
    """Fast config skipping unrelated optional stages 4..79 for Stage 80 isolation tests."""
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
        include_stage79=False,
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
    "--skip-stage79",
]


class TestPhase360Stage80CoEmulator(unittest.TestCase):
    # -----------------------------------------------------------------------
    # 01..16: Schema, Redlines, 16-Donor O_RDONLY & Clean-Room Fallback
    # -----------------------------------------------------------------------

    def test_01_schema_milestone_and_hardware_redline_constants(self) -> None:
        self.assertEqual(
            p360.SCHEMA_ID,
            "phase360_realhw_peaking_cleanhdmi_audiometer_wind_usbpd_dcc1_ntscpal_avfinfo_coemulation_v1",
        )
        self.assertEqual(p360.PHASE_NUMBER, 360)
        self.assertEqual(p360.STAGE_INDEX, 80)
        self.assertEqual(p360.STAGE_TOTAL, 80)
        self.assertEqual(p360.MILESTONE_LABEL, "80/80")
        self.assertTrue(p360.IS_80TH_STAGE_MILESTONE)
        self.assertTrue(p360.P8_CP_MUTATION_FORBIDDEN)
        self.assertFalse(p360.PERSISTENT_EMMC_WRITES_AUTHORIZED)
        self.assertFalse(p360.EMMC_WRITES_AUTHORIZED)
        self.assertFalse(p360.CROSS_MODEL_FLASH_AUTHORIZED)
        self.assertFalse(p360.HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        self.assertFalse(p360.OVERALL_READY_FOR_HARDWARE_ATTACH)
        self.assertFalse(p360.ISP_WRITE_AUTHORIZED)
        self.assertFalse(p360.SPI_NOR_WRITE_AUTHORIZED)
        self.assertFalse(p360.EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        self.assertTrue(p360.CNFLASHA_USERSPACE_WRITE_BLOCKED)
        self.assertEqual(p360.SLOT1_DATA_SECTOR_WRITES, 0)
        self.assertFalse(p360.SLOT1_AVF_INFO_MUTATED)
        self.assertEqual(p360.RF_NVS_MUTATION_BYTES, 0)
        self.assertEqual(p360.EMMC_NFLASHA_WRITE_COUNT, 0)
        self.assertEqual(p360.RAW_FIRMWARE_BYTES_LEAKED, 0)

    def test_02_donor_specs_exact_13_compact_plus_3_window_equals_16(self) -> None:
        self.assertEqual(len(p360.PHASE360_COMPACT_DONORS), 13)
        self.assertEqual(len(p360.PHASE360_WINDOW_DONORS), 3)
        self.assertEqual(
            [w.name for w in p360.PHASE360_WINDOW_DONORS],
            ["fx3_appfw", "fx3_bk4", "fx6_appfw"],
        )

    def test_03_compact_donor_specs_validate_64hex_sha_and_max_1mib(self) -> None:
        for spec in p360.PHASE360_COMPACT_DONORS:
            self.assertGreater(spec.expected_size, 0)
            self.assertLessEqual(spec.expected_size, 1024 * 1024)
            self.assertRegex(spec.expected_sha256, r"^[0-9a-f]{64}$")
            self.assertGreater(len(spec.required_tokens), 0)

    def test_04_window_donor_specs_validate_head4k_and_absent_checks(self) -> None:
        for spec in p360.PHASE360_WINDOW_DONORS:
            self.assertGreater(spec.expected_size, 1024 * 1024)
            self.assertRegex(spec.head4k_sha256, r"^[0-9a-f]{64}$")
            self.assertGreater(len(spec.windows), 0)
        self.assertEqual(len(p360.PHASE360_WINDOW_DONORS[0].absent_windows), 1)
        self.assertEqual(len(p360.PHASE360_WINDOW_DONORS[2].absent_windows), 2)

    def test_05_clean_room_fallback_with_work_root_none(self) -> None:
        audit = p360.inspect_phase360_wave70_donors(work_root=None)
        self.assertEqual(audit["source_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertEqual(audit["donor_access_mode"], "SYNTHETIC_CLEAN_ROOM")
        self.assertFalse(audit["work_root_available"])
        self.assertEqual(audit["total_donors_count"], 16)
        self.assertTrue(audit["all_donors_verified"])
        self.assertEqual(audit["raw_firmware_bytes_leaked"], 0)

    def test_06_clean_room_fallback_with_nonexistent_work_root_and_sentinel(self) -> None:
        for ctrl in ("/nonexistent/wave70/missing_root", p360._DONOR_DISABLED_SENTINEL, "   "):
            audit = p360.inspect_phase360_wave70_donors(work_root=ctrl)
            self.assertEqual(audit["source_mode"], "CLEAN_ROOM_SYNTHETIC")
            self.assertTrue(audit["all_donors_verified"])
            self.assertEqual(audit["total_donors_count"], 16)

    def test_07_env_flags_force_clean_room_both_variables(self) -> None:
        for key in (p360.ENV_CLEAN_ROOM_TEST, p360.ENV_FORCE_CLEAN_ROOM):
            audit = p360.inspect_phase360_wave70_donors(env={key: "1"})
            self.assertEqual(audit["source_mode"], "CLEAN_ROOM_SYNTHETIC")
            self.assertTrue(audit["forced_clean_room"])

    def test_08_env_mac_work_root_disabled_sentinel(self) -> None:
        res = p360.resolve_mac_work_root(
            env={p360.ENV_MAC_WORK_ROOT: p360._DONOR_DISABLED_SENTINEL}
        )
        self.assertIsNone(res)

    def test_09_local_donor_o_rdonly_audit_when_real_work_present(self) -> None:
        if p360.is_forced_clean_room():
            self.skipTest("clean-room env forced")
        root = p360.resolve_mac_work_root()
        if root is None or not root.exists():
            self.skipTest("local donor Mac/work not present")
        audit = p360.inspect_phase360_wave70_donors(force_clean_room=False)
        self.assertEqual(audit["source_mode"], "LOCAL_DONOR_O_RDONLY")
        self.assertEqual(audit["donor_access_mode"], "O_RDONLY")
        self.assertEqual(audit["compact_donors_count"], 13)
        self.assertEqual(audit["window_donors_count"], 3)
        self.assertEqual(audit["total_donors_count"], 16)
        self.assertTrue(audit["all_donors_verified"])

    def test_10_bounded_window_read_rejects_oversize_request(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "dummy.bin"
            f.write_bytes(b"A" * 8192)
            with self.assertRaises(p360.Stage80Phase360Error):
                p360._read_bounded_window_o_rdonly(f, 0, size=4097)

    def test_11_compact_reader_rejects_oversize_file(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "too_big.bin"
            f.write_bytes(b"0" * (1024 * 1024 + 1))
            with self.assertRaises(p360.Stage80Phase360Error):
                p360._read_full_compact_o_rdonly(f)

    def test_12_tampered_local_compact_donor_raises_error(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for s in p360.PHASE360_COMPACT_DONORS:
                p = root / s.rel_path
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(b"\x00" * s.expected_size)
            for w in p360.PHASE360_WINDOW_DONORS:
                p = root / w.rel_path
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(b"\x00" * 4096)
            with self.assertRaises(p360.Stage80Phase360Error):
                p360.inspect_phase360_wave70_donors(work_root=root, force_clean_room=False)

    def test_13_tampered_window_donor_missing_needle_or_forbidden_needle_raises(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "mock.bin"
            p.write_bytes(b"Z" * 8192)
            sz, h4k, win = p360._read_bounded_window_o_rdonly(p, 4096, 4096)
            self.assertEqual(sz, 8192)
            self.assertEqual(len(h4k), 4096)
            self.assertEqual(len(win), 4096)

    def test_14_strip_wall_clock_recursively_strips_elapsed_seconds(self) -> None:
        nested = {
            "a": 1,
            "elapsed_seconds": 9.99,
            "b": [{"elapsed_seconds": 1.23, "ok": True}],
        }
        cleaned = p360._strip_wall_clock(nested)
        self.assertEqual(cleaned, {"a": 1, "b": [{"ok": True}]})

    def test_15_deterministic_digest_clean_room_vs_work_root_none_match(self) -> None:
        r1a = p360.run_phase360_peaking_cleanhdmi_audiometer_wind_usbpd_dcc1_ntscpal_avfinfo_coemulation(
            force_clean_room=True
        )
        r1b = p360.run_phase360_peaking_cleanhdmi_audiometer_wind_usbpd_dcc1_ntscpal_avfinfo_coemulation(
            force_clean_room=True
        )
        r2a = p360.run_phase360_peaking_cleanhdmi_audiometer_wind_usbpd_dcc1_ntscpal_avfinfo_coemulation(
            work_root=None
        )
        r2b = p360.run_phase360_peaking_cleanhdmi_audiometer_wind_usbpd_dcc1_ntscpal_avfinfo_coemulation(
            work_root="/nonexistent/wave70/missing"
        )
        self.assertTrue(r1a["all_checks_passed"])
        self.assertTrue(r2a["all_checks_passed"])
        self.assertEqual(r1a["audit_digest_sha256"], r1b["audit_digest_sha256"])
        self.assertEqual(r2a["audit_digest_sha256"], r2b["audit_digest_sha256"])

    def test_16_milestone_probe_exact_stage80_metadata(self) -> None:
        probe = p360._build_stage80_milestone_probe()
        self.assertEqual(probe["phase_number"], 360)
        self.assertEqual(probe["stage_index"], 80)
        self.assertEqual(probe["stage_total"], 80)
        self.assertEqual(probe["milestone"], "80/80")
        self.assertTrue(probe["is_80th_stage_milestone"])
        self.assertEqual(probe["wave"], "Wave-70")
        self.assertEqual(probe["fx3_target_version"], "Ver. 7.02")
        self.assertEqual(probe["fx6_comparison_version"], "Ver. 6.01")

    # -----------------------------------------------------------------------
    # 17..36: Sub-Model 80A — [Peaking Display], Clean-HDMI, Focus Mag & Map
    # -----------------------------------------------------------------------

    def test_17_80a_fx3_peaking_3_items_and_wheel_right_default(self) -> None:
        res = p360.simulate_peaking_cleanhdmi_focusmag_and_map_hil(
            peaking_display="On", peaking_level="Mid", peaking_color="White"
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.peaking_items_count, 3)
        self.assertEqual(res.wheel_right_default, "Peaking Display Select")
        self.assertTrue(res.peaking_on_body_lcd)

    def test_18_80a_fx3_peaking_all_3_items_reset_resistant(self) -> None:
        res = p360.simulate_peaking_cleanhdmi_focusmag_and_map_hil(
            peaking_display="On",
            peaking_level="High",
            peaking_color="Red",
            camera_settings_reset_applied=True,
        )
        self.assertTrue(res.admitted)
        self.assertFalse(res.peaking_resettable)
        self.assertEqual(res.effective_peaking_display, "On")
        self.assertEqual(res.effective_peaking_level, "High")
        self.assertEqual(res.effective_peaking_color, "Red")

    def test_19_80a_fx3_initialize_restores_off_mid_white(self) -> None:
        res = p360.simulate_peaking_cleanhdmi_focusmag_and_map_hil(
            peaking_display="On",
            peaking_level="High",
            peaking_color="Blue",
            initialize_applied=True,
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.effective_peaking_display, "Off")
        self.assertEqual(res.effective_peaking_level, "Mid")
        self.assertEqual(res.effective_peaking_color, "White")

    def test_20_80a_fx3_zero_hdmi_peaking_even_with_info_on_and_raw_on(self) -> None:
        for info in ("Off", "On"):
            for raw in ("Off", "On"):
                for tr in ("body_lcd", "hdmi"):
                    res = p360.simulate_peaking_cleanhdmi_focusmag_and_map_hil(
                        transport=tr,
                        peaking_display="On",
                        hdmi_info_display=info,
                        raw_output=raw,
                    )
                    self.assertTrue(res.admitted)
                    self.assertEqual(res.hdmi_peaking_leaked_pixels, 0)

    def test_21_80a_fx3_focus_magnifier_x1_x4_x8_strict_coexistence(self) -> None:
        for mag in ("x1.0", "x4.0", "x8.0"):
            res = p360.simulate_peaking_cleanhdmi_focusmag_and_map_hil(
                peaking_display="On", focus_mag_scale=mag
            )
            self.assertTrue(res.admitted)
            self.assertEqual(res.focus_mag_scale, mag)
            self.assertTrue(res.focus_mag_coexists_with_peaking)

    def test_22_80a_fx3_supports_4_peaking_colors_and_rejects_bw(self) -> None:
        for clr in ("Red", "Yellow", "Blue", "White"):
            res = p360.simulate_peaking_cleanhdmi_focusmag_and_map_hil(peaking_color=clr)
            self.assertTrue(res.admitted)
            self.assertEqual(res.effective_peaking_color, clr)
        bad = p360.simulate_peaking_cleanhdmi_focusmag_and_map_hil(peaking_color="B&W")
        self.assertFalse(bad.admitted)
        self.assertEqual(bad.errno_code, p360.EOPNOTSUPP_ERRNO)

    def test_23_80a_fx3_on_body_focus_map_dormant_eopnotsupp(self) -> None:
        res = p360.simulate_peaking_cleanhdmi_focusmag_and_map_hil(
            operation="focus_map", transport="body_lcd"
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p360.EOPNOTSUPP_ERRNO)
        self.assertFalse(res.body_focus_map_exposed)

    def test_24_80a_fx3_focus_map_unavailable_over_usb(self) -> None:
        res = p360.simulate_peaking_cleanhdmi_focusmag_and_map_hil(
            operation="focus_map", transport="usb"
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p360.EOPNOTSUPP_ERRNO)
        self.assertFalse(res.focus_map_over_usb_supported)

    def test_25_80a_fx3_focus_map_wireless_monitor_control_v210_only(self) -> None:
        ok = p360.simulate_peaking_cleanhdmi_focusmag_and_map_hil(
            operation="focus_map", transport="wifi_mc", monitor_control_version="2.1.0"
        )
        self.assertTrue(ok.admitted)
        self.assertTrue(ok.focus_map_remote_wireless_only)
        old = p360.simulate_peaking_cleanhdmi_focusmag_and_map_hil(
            operation="focus_map", transport="wifi_mc", monitor_control_version="2.0.0"
        )
        self.assertFalse(old.admitted)
        self.assertEqual(old.errno_code, p360.EOPNOTSUPP_ERRNO)

    def test_26_80a_fx3_focus_map_unsupported_over_hdmi_sdi(self) -> None:
        for tr in ("hdmi", "sdi"):
            res = p360.simulate_peaking_cleanhdmi_focusmag_and_map_hil(
                operation="focus_map", transport=tr
            )
            self.assertFalse(res.admitted)
            self.assertEqual(res.errno_code, p360.EOPNOTSUPP_ERRNO)

    def test_27_80a_fx6_monitoring_peaking_supports_bw_red_yellow_blue_rejects_white(self) -> None:
        for clr in ("B&W", "Red", "Yellow", "Blue"):
            res = p360.simulate_peaking_cleanhdmi_focusmag_and_map_hil(
                body_profile=p360.BODY_MODEL_FX6,
                fw_version=p360.FW_VER_601,
                operation="fx6_peaking",
                peaking_color=clr,
            )
            self.assertTrue(res.admitted)
            self.assertEqual(res.effective_peaking_color, clr)
            self.assertTrue(res.fx6_sdi_hdmi_output_display_independent)
        bad = p360.simulate_peaking_cleanhdmi_focusmag_and_map_hil(
            body_profile=p360.BODY_MODEL_FX6,
            fw_version=p360.FW_VER_601,
            operation="fx6_peaking",
            peaking_color="White",
        )
        self.assertFalse(bad.admitted)
        self.assertEqual(bad.errno_code, p360.EOPNOTSUPP_ERRNO)

    def test_28_80a_fx6_disproves_dormant_peaking_type_and_frequency(self) -> None:
        res = p360.simulate_peaking_cleanhdmi_focusmag_and_map_hil(
            body_profile=p360.BODY_MODEL_FX6,
            fw_version=p360.FW_VER_601,
            operation="fx6_dormant_type_freq",
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p360.EOPNOTSUPP_ERRNO)
        self.assertEqual(res.fx6_peaking_type_freq_appfw_symbols, 0)

    def test_29_80a_cross_body_operation_blocks(self) -> None:
        fx3_on_fx6 = p360.simulate_peaking_cleanhdmi_focusmag_and_map_hil(
            body_profile=p360.BODY_MODEL_FX3, operation="fx6_peaking"
        )
        fx6_on_fx3 = p360.simulate_peaking_cleanhdmi_focusmag_and_map_hil(
            body_profile=p360.BODY_MODEL_FX6, fw_version=p360.FW_VER_601, operation="peaking_setting"
        )
        self.assertFalse(fx3_on_fx6.admitted)
        self.assertEqual(fx3_on_fx6.errno_code, p360.EOPNOTSUPP_ERRNO)
        self.assertFalse(fx6_on_fx3.admitted)
        self.assertEqual(fx6_on_fx3.errno_code, p360.EOPNOTSUPP_ERRNO)

    def test_30_80a_peaking_levels_high_mid_low(self) -> None:
        for lvl in ("High", "Mid", "Low"):
            res = p360.simulate_peaking_cleanhdmi_focusmag_and_map_hil(peaking_level=lvl)
            self.assertTrue(res.admitted)
            self.assertEqual(res.effective_peaking_level, lvl)

    def test_31_80a_invalid_arguments_raise_stage80_error(self) -> None:
        for kw in (
            {"body_profile": "FX9"},
            {"fw_version": "9.99"},
            {"operation": "bad_op"},
            {"transport": "coax"},
            {"peaking_display": "Auto"},
            {"peaking_level": "Extreme"},
            {"peaking_color": "Green"},
            {"hdmi_info_display": "Maybe"},
            {"raw_output": "16bit"},
            {"focus_mag_scale": "x16.0"},
        ):
            with self.assertRaises(p360.Stage80Phase360Error):
                p360.simulate_peaking_cleanhdmi_focusmag_and_map_hil(**kw)

    def test_32_80a_fx6_initialize_turns_peaking_off(self) -> None:
        res = p360.simulate_peaking_cleanhdmi_focusmag_and_map_hil(
            body_profile=p360.BODY_MODEL_FX6,
            fw_version=p360.FW_VER_601,
            operation="fx6_peaking",
            peaking_display="On",
            peaking_color="B&W",
            initialize_applied=True,
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.effective_peaking_display, "Off")
        self.assertFalse(res.peaking_on_body_lcd)

    def test_33_80a_fx3_peaking_off_lcd_false(self) -> None:
        res = p360.simulate_peaking_cleanhdmi_focusmag_and_map_hil(peaking_display="Off")
        self.assertTrue(res.admitted)
        self.assertFalse(res.peaking_on_body_lcd)
        self.assertEqual(res.hdmi_peaking_leaked_pixels, 0)

    def test_34_80a_pillar_a_present_and_passed(self) -> None:
        rep = p360.run_phase360_peaking_cleanhdmi_audiometer_wind_usbpd_dcc1_ntscpal_avfinfo_coemulation(
            force_clean_room=True
        )
        pa = rep["pillar_a_peaking_cleanhdmi_focusmag_and_map_hil"]
        self.assertTrue(pa["passed"])
        self.assertEqual(pa["fx3_clean_hdmi_and_focusmag_x8_reset_resistant"]["hdmi_peaking_leaked_pixels"], 0)

    def test_35_80a_redline_constants_consistent(self) -> None:
        self.assertEqual(p360.FX3_PEAKING_ITEMS_COUNT, 3)
        self.assertEqual(p360.PEAKING_RESET_WIPE_EVENTS, 0)
        self.assertEqual(p360.HDMI_PEAKING_LEAKED_PIXELS, 0)
        self.assertEqual(p360.PEAKING_FOCUS_MAG_CONFLICT_EVENTS, 0)
        self.assertFalse(p360.FX3_BODY_FOCUS_MAP_EXPOSED)
        self.assertFalse(p360.FOCUS_MAP_OVER_USB_SUPPORTED)
        self.assertTrue(p360.FX6_PEAKING_COLOR_HAS_BW)
        self.assertEqual(p360.FX6_PEAKING_APPFW_TYPE_FREQ_SYMBOL_COUNT, 0)

    def test_36_80a_fx3_compact_donor_tokens_cover_peaking_and_focus_map(self) -> None:
        en_f = next(d for d in p360.PHASE360_COMPACT_DONORS if d.name == "fx3_string_en_f")
        for tok in (b"Peaking Display", b"Peaking Display Select", b"Peaking Level", b"Peaking Color", b"Focus Map"):
            self.assertIn(tok, en_f.required_tokens)

    # -----------------------------------------------------------------------
    # 37..58: Sub-Model 80B — Audio Meter Removal, Wind Reduct & XLR-H1
    # -----------------------------------------------------------------------

    def test_37_80b_v200_v702_removed_audio_level_display_vs_v101_legacy(self) -> None:
        for ver in (p360.FW_VER_200, p360.FW_VER_702):
            res = p360.simulate_audio_meter_wind_and_xlrh1_vs_fx6_hil(
                fw_version=ver, operation="legacy_audio_level_display"
            )
            self.assertFalse(res.admitted)
            self.assertEqual(res.errno_code, p360.EOPNOTSUPP_ERRNO)
            self.assertFalse(res.legacy_audio_level_display_menu_exposed)
        v1 = p360.simulate_audio_meter_wind_and_xlrh1_vs_fx6_hil(
            fw_version=p360.FW_VER_101, operation="legacy_audio_level_display"
        )
        self.assertTrue(v1.admitted)
        self.assertTrue(v1.legacy_audio_level_display_menu_exposed)

    def test_38_80b_exact_5_resettable_items_and_defult_typo(self) -> None:
        self.assertEqual(len(p360.FX3_AUDIO_RECORDING_5_ITEMS), 5)
        res = p360.simulate_audio_meter_wind_and_xlrh1_vs_fx6_hil(
            operation="audio_recording_menu",
            audio_rec_level=12,
            wind_noise_reduct="On",
            camera_settings_reset_applied=True,
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.audio_recording_items_count, 5)
        self.assertTrue(res.audio_recording_resettable)
        self.assertEqual(res.effective_audio_rec_level, 26)
        self.assertEqual(res.effective_wind_noise_reduct, "Off")
        self.assertEqual(res.rec_level_defult_typo_symbol, "adj_audio_rec_level_defult")
        self.assertTrue(res.permanent_limiter_active)

    def test_39_80b_wind_noise_reduct_rejects_dormant_auto_and_on_advanced(self) -> None:
        for opt in ("Auto", "On Advanced"):
            res = p360.simulate_audio_meter_wind_and_xlrh1_vs_fx6_hil(
                operation="wind_noise_reduct", wind_noise_reduct=opt
            )
            self.assertFalse(res.admitted)
            self.assertEqual(res.errno_code, p360.EOPNOTSUPP_ERRNO)

    def test_40_80b_wind_noise_reduct_active_only_on_internal_mic(self) -> None:
        res = p360.simulate_audio_meter_wind_and_xlrh1_vs_fx6_hil(
            operation="wind_noise_reduct", wind_noise_reduct="On"
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.active_audio_input, "Internal Mic")
        self.assertTrue(res.wind_low_cut_dsp_active)
        self.assertIsNone(res.wind_bypassed_reason)

    def test_41_80b_wind_noise_reduct_bypassed_on_35mm_xlrh1_and_sq(self) -> None:
        r_35 = p360.simulate_audio_meter_wind_and_xlrh1_vs_fx6_hil(
            operation="wind_noise_reduct", wind_noise_reduct="On", mic_35mm_plugged=True
        )
        self.assertTrue(r_35.admitted)
        self.assertEqual(r_35.active_audio_input, "3.5mm MIC")
        self.assertFalse(r_35.wind_low_cut_dsp_active)

        r_xlr = p360.simulate_audio_meter_wind_and_xlrh1_vs_fx6_hil(
            operation="wind_noise_reduct", wind_noise_reduct="On", xlrh1_attached=True
        )
        self.assertTrue(r_xlr.admitted)
        self.assertEqual(r_xlr.active_audio_input, "XLR-H1")
        self.assertFalse(r_xlr.wind_low_cut_dsp_active)

        r_sq = p360.simulate_audio_meter_wind_and_xlrh1_vs_fx6_hil(
            operation="wind_noise_reduct", wind_noise_reduct="On", sq_mode=True
        )
        self.assertTrue(r_sq.admitted)
        self.assertFalse(r_sq.wind_low_cut_dsp_active)
        self.assertEqual(r_sq.disp_big6_meter_channels, 0)

    def test_42_80b_xlrh1_hardware_low_cut_off_100hz_300hz(self) -> None:
        for lc in ("Off", "100Hz", "300Hz"):
            res = p360.simulate_audio_meter_wind_and_xlrh1_vs_fx6_hil(
                operation="xlrh1_hardware_low_cut",
                xlrh1_attached=True,
                xlrh1_hardware_low_cut=lc,
            )
            self.assertTrue(res.admitted)
            self.assertEqual(res.xlrh1_hardware_low_cut, lc)
            self.assertFalse(res.wind_low_cut_dsp_active)

    def test_43_80b_xlrh1_detached_enodev_and_35mm_preemption_ebusy(self) -> None:
        det = p360.simulate_audio_meter_wind_and_xlrh1_vs_fx6_hil(
            operation="xlrh1_hardware_low_cut", xlrh1_attached=False
        )
        self.assertFalse(det.admitted)
        self.assertEqual(det.errno_code, p360.ENODEV_ERRNO)

        pre = p360.simulate_audio_meter_wind_and_xlrh1_vs_fx6_hil(
            operation="xlrh1_hardware_low_cut",
            xlrh1_attached=True,
            mic_35mm_plugged=True,
        )
        self.assertFalse(pre.admitted)
        self.assertEqual(pre.errno_code, p360.EBUSY_ERRNO)
        self.assertEqual(pre.active_audio_input, "3.5mm MIC")

    def test_44_80b_disp_big6_meter_channels_2ch_4ch_0ch_sq_and_off(self) -> None:
        r_2ch = p360.simulate_audio_meter_wind_and_xlrh1_vs_fx6_hil(
            operation="disp_audio_meter", shoe_audio_format="48kHz/24bit 2ch"
        )
        self.assertEqual(r_2ch.disp_big6_meter_channels, 2)

        r_4ch = p360.simulate_audio_meter_wind_and_xlrh1_vs_fx6_hil(
            operation="disp_audio_meter",
            xlrh1_attached=True,
            shoe_audio_format="48kHz/24bit 4ch",
        )
        self.assertEqual(r_4ch.disp_big6_meter_channels, 4)

        r_off = p360.simulate_audio_meter_wind_and_xlrh1_vs_fx6_hil(
            operation="disp_audio_meter", audio_recording="Off"
        )
        self.assertEqual(r_off.disp_big6_meter_channels, 0)

    def test_45_80b_remote_sdk_audio_meter_strictly_read_only_eacces(self) -> None:
        res = p360.simulate_audio_meter_wind_and_xlrh1_vs_fx6_hil(
            operation="remote_sdk_audio_meter_write"
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p360.EACCES_ERRNO)
        self.assertTrue(res.remote_sdk_audio_meter_read_only)

    def test_46_80b_fx6_ch1_4_wind_filter_6step_limiter_and_zero_handle_low_cut(self) -> None:
        fx6 = p360.simulate_audio_meter_wind_and_xlrh1_vs_fx6_hil(
            body_profile=p360.BODY_MODEL_FX6,
            fw_version=p360.FW_VER_601,
            operation="fx6_audio_control",
            fx6_ch_wind_filters=("On", "Off", "On", "Off"),
            fx6_limiter_mode="-12dB",
        )
        self.assertTrue(fx6.admitted)
        self.assertEqual(fx6.fx6_ch_wind_filters_count, 4)
        self.assertEqual(fx6.fx6_limiter_mode_steps_count, 6)
        self.assertFalse(fx6.fx6_handle_physical_low_cut)

        no_lc = p360.simulate_audio_meter_wind_and_xlrh1_vs_fx6_hil(
            body_profile=p360.BODY_MODEL_FX6,
            fw_version=p360.FW_VER_601,
            operation="fx6_handle_physical_low_cut",
        )
        self.assertFalse(no_lc.admitted)
        self.assertEqual(no_lc.errno_code, p360.EOPNOTSUPP_ERRNO)

    def test_47_80b_audio_out_timing_live_and_lip_sync(self) -> None:
        for tm in ("Live", "Lip Sync"):
            res = p360.simulate_audio_meter_wind_and_xlrh1_vs_fx6_hil(audio_out_timing=tm)
            self.assertTrue(res.admitted)

    def test_48_80b_audio_rec_level_0_and_31_boundaries_ok_32_and_neg1_raise(self) -> None:
        for lvl in (0, 26, 31):
            res = p360.simulate_audio_meter_wind_and_xlrh1_vs_fx6_hil(audio_rec_level=lvl)
            self.assertEqual(res.effective_audio_rec_level, lvl)
        for bad in (-1, 32):
            with self.assertRaises(p360.Stage80Phase360Error):
                p360.simulate_audio_meter_wind_and_xlrh1_vs_fx6_hil(audio_rec_level=bad)

    def test_49_80b_cross_body_audio_operations_rejected(self) -> None:
        a = p360.simulate_audio_meter_wind_and_xlrh1_vs_fx6_hil(
            body_profile=p360.BODY_MODEL_FX3, operation="fx6_audio_control"
        )
        b = p360.simulate_audio_meter_wind_and_xlrh1_vs_fx6_hil(
            body_profile=p360.BODY_MODEL_FX6,
            fw_version=p360.FW_VER_601,
            operation="wind_noise_reduct",
        )
        self.assertFalse(a.admitted)
        self.assertEqual(a.errno_code, p360.EOPNOTSUPP_ERRNO)
        self.assertFalse(b.admitted)
        self.assertEqual(b.errno_code, p360.EOPNOTSUPP_ERRNO)

    def test_50_80b_fx6_sq_mode_0ch_meter(self) -> None:
        res = p360.simulate_audio_meter_wind_and_xlrh1_vs_fx6_hil(
            body_profile=p360.BODY_MODEL_FX6,
            fw_version=p360.FW_VER_601,
            operation="fx6_audio_control",
            sq_mode=True,
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.disp_big6_meter_channels, 0)

    def test_51_80b_fx3_initialize_resets_wind_and_level(self) -> None:
        res = p360.simulate_audio_meter_wind_and_xlrh1_vs_fx6_hil(
            audio_rec_level=5, wind_noise_reduct="On", initialize_applied=True
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.effective_audio_rec_level, 26)
        self.assertEqual(res.effective_wind_noise_reduct, "Off")
        self.assertFalse(res.wind_low_cut_dsp_active)

    def test_52_80b_wind_off_disables_dsp_low_cut(self) -> None:
        res = p360.simulate_audio_meter_wind_and_xlrh1_vs_fx6_hil(wind_noise_reduct="Off")
        self.assertTrue(res.admitted)
        self.assertFalse(res.wind_low_cut_dsp_active)

    def test_53_80b_invalid_audio_parameters_raise_stage80_error(self) -> None:
        for kw in (
            {"body_profile": "FX30"},
            {"fw_version": "0.99"},
            {"operation": "bad"},
            {"audio_recording": "Auto"},
            {"audio_out_timing": "Delay"},
            {"wind_noise_reduct": "Ultra"},
            {"xlrh1_hardware_low_cut": "500Hz"},
            {"shoe_audio_format": "96kHz"},
            {"fx6_limiter_mode": "-30dB"},
        ):
            with self.assertRaises(p360.Stage80Phase360Error):
                p360.simulate_audio_meter_wind_and_xlrh1_vs_fx6_hil(**kw)

    def test_54_80b_all_three_shoe_audio_formats_supported(self) -> None:
        for fmt in p360.VALID_SHOE_AUDIO_FORMATS:
            res = p360.simulate_audio_meter_wind_and_xlrh1_vs_fx6_hil(
                xlrh1_attached=True, shoe_audio_format=fmt
            )
            self.assertTrue(res.admitted)
            self.assertEqual(res.disp_big6_meter_channels, 4 if "4ch" in fmt else 2)

    def test_55_80b_fx6_all_6_limiter_modes_accepted(self) -> None:
        for mode in p360.FX6_6_LIMITER_MODES:
            res = p360.simulate_audio_meter_wind_and_xlrh1_vs_fx6_hil(
                body_profile=p360.BODY_MODEL_FX6,
                fw_version=p360.FW_VER_601,
                operation="fx6_audio_control",
                fx6_limiter_mode=mode,
            )
            self.assertTrue(res.admitted)
            self.assertEqual(res.permanent_limiter_active, mode != "Off")

    def test_56_80b_audio_off_bypasses_wind_low_cut(self) -> None:
        res = p360.simulate_audio_meter_wind_and_xlrh1_vs_fx6_hil(
            audio_recording="Off", wind_noise_reduct="On"
        )
        self.assertTrue(res.admitted)
        self.assertFalse(res.wind_low_cut_dsp_active)

    def test_57_80b_pillar_b_passed_in_full_report(self) -> None:
        rep = p360.run_phase360_peaking_cleanhdmi_audiometer_wind_usbpd_dcc1_ntscpal_avfinfo_coemulation(
            force_clean_room=True
        )
        self.assertTrue(rep["pillar_b_audiometer_wind_reduct_and_xlrh1_vs_fx6_hil"]["passed"])

    def test_58_80b_redline_constants_match(self) -> None:
        self.assertTrue(p360.FX3_V2_PLUS_AUDIO_LEVEL_DISPLAY_MENU_REMOVED)
        self.assertEqual(p360.AUDIO_RECORDING_MENU_ITEMS_COUNT, 5)
        self.assertEqual(p360.AUDIO_REC_LEVEL_DEFAULT, 26)
        self.assertTrue(p360.ADJ_AUDIO_REC_LEVEL_DEFULT_TYPO_MATCHED)
        self.assertFalse(p360.FX6_HANDLE_PHYSICAL_LOW_CUT_PRESENT)
        self.assertEqual(p360.FX6_CH_WIND_FILTER_COUNT, 4)
        self.assertEqual(p360.FX6_LIMITER_MODE_STEPS_COUNT, 6)

    # -----------------------------------------------------------------------
    # 59..80: Sub-Model 80C — [USB Power Supply], NP-FZ100, DC-C1 & FX6 DC IN
    # -----------------------------------------------------------------------

    def test_59_80c_usb_power_supply_reset_resistant_vs_initialize(self) -> None:
        res_rst = p360.simulate_usb_power_supply_npfz100_dcc1_vs_fx6_hil(
            usb_power_supply="Off", camera_settings_reset_applied=True
        )
        self.assertTrue(res_rst.admitted)
        self.assertFalse(res_rst.usb_power_resettable)
        self.assertEqual(res_rst.effective_usb_power_supply, "Off")

        res_init = p360.simulate_usb_power_supply_npfz100_dcc1_vs_fx6_hil(
            usb_power_supply="Off", initialize_applied=True
        )
        self.assertTrue(res_init.admitted)
        self.assertEqual(res_init.effective_usb_power_supply, "On")

    def test_60_80c_multi_micro_usb_rejected_enodev(self) -> None:
        res = p360.simulate_usb_power_supply_npfz100_dcc1_vs_fx6_hil(port="Multi/Micro-USB")
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p360.ENODEV_ERRNO)

    def test_61_80c_9v3a_power_on_no_charge_and_power_save_bypass(self) -> None:
        res = p360.simulate_usb_power_supply_npfz100_dcc1_vs_fx6_hil(
            mode="power_on", port="Type-C", power_profile="9V/3A"
        )
        self.assertTrue(res.admitted)
        self.assertTrue(res.power_on_supply_active)
        self.assertFalse(res.charging_active)
        self.assertEqual(res.charge_led_state, "Off")
        self.assertTrue(res.power_save_bypassed)
        self.assertFalse(res.battery_draining_5v15a_low)

    def test_62_80c_5v15a_low_causes_battery_drain_flag(self) -> None:
        res = p360.simulate_usb_power_supply_npfz100_dcc1_vs_fx6_hil(
            mode="power_on", port="Type-C", power_profile="5V/1.5A"
        )
        self.assertTrue(res.admitted)
        self.assertTrue(res.battery_draining_5v15a_low)
        self.assertFalse(res.charging_active)

    def test_63_80c_mandatory_np_fz100_zero_batteryless_boot(self) -> None:
        res = p360.simulate_usb_power_supply_npfz100_dcc1_vs_fx6_hil(
            mode="power_on", np_fz100_inserted=False
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p360.EIO_ERRNO)
        self.assertFalse(res.batteryless_boot_supported)

    def test_64_80c_hot_pull_np_fz100_instant_power_loss(self) -> None:
        res = p360.simulate_usb_power_supply_npfz100_dcc1_vs_fx6_hil(
            mode="power_on", np_fz100_inserted=True, battery_hot_pulled=True
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p360.EIO_ERRNO)
        self.assertTrue(res.instant_power_loss_on_hot_pull)

    def test_65_80c_power_off_charging_10c_to_30c_window_exact(self) -> None:
        for t in (10, 23, 30):
            res = p360.simulate_usb_power_supply_npfz100_dcc1_vs_fx6_hil(
                mode="power_off", ambient_temp_c=t
            )
            self.assertTrue(res.admitted)
            self.assertTrue(res.charging_active)
            self.assertEqual(res.charge_led_state, "On")

    def test_66_80c_power_off_outside_10c_to_30c_fastblink_fault(self) -> None:
        for t in (9, 31, 45):
            res = p360.simulate_usb_power_supply_npfz100_dcc1_vs_fx6_hil(
                mode="power_off", ambient_temp_c=t
            )
            self.assertFalse(res.admitted)
            self.assertEqual(res.errno_code, p360.EACCES_ERRNO)
            self.assertFalse(res.charging_active)
            self.assertEqual(res.charge_led_state, "FastBlink")

    def test_67_80c_dc_c1_65w_5a_locks_monitor_brightness_max(self) -> None:
        res = p360.simulate_usb_power_supply_npfz100_dcc1_vs_fx6_hil(
            mode="dc_c1", port="DC-C1", dc_c1_pd_watts=65, dc_c1_cable_amps=5
        )
        self.assertTrue(res.admitted)
        self.assertTrue(res.np_fz100_inserted)
        self.assertTrue(res.monitor_brightness_locked_max)
        self.assertTrue(res.power_save_bypassed)

    def test_68_80c_dc_c1_rejects_underpower_pd_or_3a_cable(self) -> None:
        low_w = p360.simulate_usb_power_supply_npfz100_dcc1_vs_fx6_hil(
            mode="dc_c1", port="DC-C1", dc_c1_pd_watts=45, dc_c1_cable_amps=5
        )
        low_a = p360.simulate_usb_power_supply_npfz100_dcc1_vs_fx6_hil(
            mode="dc_c1", port="DC-C1", dc_c1_pd_watts=65, dc_c1_cable_amps=3
        )
        self.assertFalse(low_w.admitted)
        self.assertEqual(low_w.errno_code, p360.EINVAL_ERRNO)
        self.assertFalse(low_a.admitted)
        self.assertEqual(low_a.errno_code, p360.EINVAL_ERRNO)

    def test_69_80c_fx6_19v5_batteryless_boot_supported(self) -> None:
        for v in (18.0, 19.5, 20.5):
            res = p360.simulate_usb_power_supply_npfz100_dcc1_vs_fx6_hil(
                body_profile=p360.BODY_MODEL_FX6,
                fw_version=p360.FW_VER_601,
                mode="fx6_dc_in",
                port="FX6_DC_IN",
                fx6_dc_in_volts=v,
                fx6_bpu_inserted=False,
            )
            self.assertTrue(res.admitted)
            self.assertTrue(res.batteryless_boot_supported)
            self.assertIsNone(res.fx6_dc_low_volt_warning)

    def test_70_80c_fx6_16v5_warn1_and_15v5_warn2_shutdown(self) -> None:
        w1 = p360.simulate_usb_power_supply_npfz100_dcc1_vs_fx6_hil(
            body_profile=p360.BODY_MODEL_FX6,
            fw_version=p360.FW_VER_601,
            mode="fx6_dc_in",
            port="FX6_DC_IN",
            fx6_dc_in_volts=16.5,
        )
        w2 = p360.simulate_usb_power_supply_npfz100_dcc1_vs_fx6_hil(
            body_profile=p360.BODY_MODEL_FX6,
            fw_version=p360.FW_VER_601,
            mode="fx6_dc_in",
            port="FX6_DC_IN",
            fx6_dc_in_volts=15.5,
        )
        self.assertTrue(w1.admitted)
        self.assertEqual(w1.fx6_dc_low_volt_warning, "BKID_APP_SETTING_DC_LOW_VOLT1")
        self.assertFalse(w2.admitted)
        self.assertEqual(w2.errno_code, p360.EINVAL_ERRNO)
        self.assertEqual(w2.fx6_dc_low_volt_warning, "BKID_APP_SETTING_DC_LOW_VOLT2")

    def test_71_80c_fx6_overvoltage_21v_and_17v_rejected(self) -> None:
        for v in (17.0, 21.0):
            res = p360.simulate_usb_power_supply_npfz100_dcc1_vs_fx6_hil(
                body_profile=p360.BODY_MODEL_FX6,
                fw_version=p360.FW_VER_601,
                mode="fx6_dc_in",
                port="FX6_DC_IN",
                fx6_dc_in_volts=v,
            )
            self.assertFalse(res.admitted)
            self.assertEqual(res.errno_code, p360.EINVAL_ERRNO)

    def test_72_80c_fx6_seamless_dcin_to_bpu_pullover_vs_no_bpu_loss(self) -> None:
        ok = p360.simulate_usb_power_supply_npfz100_dcc1_vs_fx6_hil(
            body_profile=p360.BODY_MODEL_FX6,
            fw_version=p360.FW_VER_601,
            mode="fx6_dc_in",
            port="FX6_DC_IN",
            fx6_bpu_inserted=True,
            fx6_dcin_unplugged_to_bpu=True,
        )
        self.assertTrue(ok.admitted)
        self.assertTrue(ok.fx6_seamless_dcin_to_bpu_pullover)

        loss = p360.simulate_usb_power_supply_npfz100_dcc1_vs_fx6_hil(
            body_profile=p360.BODY_MODEL_FX6,
            fw_version=p360.FW_VER_601,
            mode="fx6_dc_in",
            port="FX6_DC_IN",
            fx6_bpu_inserted=False,
            fx6_dcin_unplugged_to_bpu=True,
        )
        self.assertFalse(loss.admitted)
        self.assertEqual(loss.errno_code, p360.EIO_ERRNO)
        self.assertTrue(loss.instant_power_loss_on_hot_pull)

    def test_73_80c_fx6_dc_in_hot_replug_reboot_guard_eperm(self) -> None:
        res = p360.simulate_usb_power_supply_npfz100_dcc1_vs_fx6_hil(
            body_profile=p360.BODY_MODEL_FX6,
            fw_version=p360.FW_VER_601,
            mode="fx6_dc_in",
            port="FX6_DC_IN",
            fx6_bpu_inserted=True,
            fx6_dcin_hot_replug_while_running=True,
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p360.EPERM_ERRNO)
        self.assertTrue(res.fx6_hot_replug_reboot_blocked)

    def test_74_80c_fx6_usbc_incapable_of_powering_body_eopnotsupp(self) -> None:
        res = p360.simulate_usb_power_supply_npfz100_dcc1_vs_fx6_hil(
            body_profile=p360.BODY_MODEL_FX6,
            fw_version=p360.FW_VER_601,
            mode="fx6_usbc",
            port="Type-C",
        )
        self.assertFalse(res.admitted)
        self.assertEqual(res.errno_code, p360.EOPNOTSUPP_ERRNO)

    def test_75_80c_fx3_rejects_fx6_dc_in_modes(self) -> None:
        for m in ("fx6_dc_in", "fx6_usbc"):
            res = p360.simulate_usb_power_supply_npfz100_dcc1_vs_fx6_hil(mode=m)
            self.assertFalse(res.admitted)
            self.assertEqual(res.errno_code, p360.EOPNOTSUPP_ERRNO)

    def test_76_80c_fx3_usb_power_supply_off_does_not_bypass_power_save(self) -> None:
        res = p360.simulate_usb_power_supply_npfz100_dcc1_vs_fx6_hil(usb_power_supply="Off")
        self.assertTrue(res.admitted)
        self.assertFalse(res.power_on_supply_active)
        self.assertFalse(res.power_save_bypassed)

    def test_77_80c_dc_c1_100w_5a_also_accepted(self) -> None:
        res = p360.simulate_usb_power_supply_npfz100_dcc1_vs_fx6_hil(
            mode="dc_c1", port="DC-C1", dc_c1_pd_watts=100, dc_c1_cable_amps=5
        )
        self.assertTrue(res.admitted)
        self.assertTrue(res.monitor_brightness_locked_max)

    def test_78_80c_invalid_usb_power_arguments_raise(self) -> None:
        for kw in (
            {"body_profile": "FX30"},
            {"fw_version": "5.00"},
            {"mode": "wireless"},
            {"port": "Thunderbolt"},
            {"usb_power_supply": "Auto"},
            {"power_profile": "120W"},
        ):
            with self.assertRaises(p360.Stage80Phase360Error):
                p360.simulate_usb_power_supply_npfz100_dcc1_vs_fx6_hil(**kw)

    def test_79_80c_pillar_c_passed_in_full_report(self) -> None:
        rep = p360.run_phase360_peaking_cleanhdmi_audiometer_wind_usbpd_dcc1_ntscpal_avfinfo_coemulation(
            force_clean_room=True
        )
        self.assertTrue(rep["pillar_c_usb_power_supply_npfz100_dcc1_vs_fx6_dcin_hil"]["passed"])

    def test_80_80c_redline_constants_match(self) -> None:
        self.assertTrue(p360.NP_FZ100_INSERTION_MANDATORY)
        self.assertFalse(p360.FX3_BATTERYLESS_BOOT_ALLOWED)
        self.assertEqual(p360.POWER_OFF_CHARGE_TEMP_MIN_C, 10)
        self.assertEqual(p360.POWER_OFF_CHARGE_TEMP_MAX_C, 30)
        self.assertEqual(p360.DCC1_MIN_PD_WATTS, 65)
        self.assertEqual(p360.DCC1_REQUIRED_CABLE_AMPS, 5)
        self.assertTrue(p360.FX6_BATTERYLESS_BOOT_SUPPORTED)
        self.assertFalse(p360.FX6_USBC_POWER_SUPPORTED)

    # -----------------------------------------------------------------------
    # 81..96: Sub-Model 80D — [NTSC/PAL Selector], AVF_INFO & Slot 1 EROFS=30
    # -----------------------------------------------------------------------

    def test_81_80d_j1_japan_sku_locks_out_ntsc_pal_selector(self) -> None:
        pal_req = p360.simulate_ntscpal_sku_avfinfo_and_slot1_erofs_hil(
            sku_code="J1", requested_tv_system="PAL"
        )
        self.assertFalse(pal_req.admitted)
        self.assertEqual(pal_req.errno_code, p360.EOPNOTSUPP_ERRNO)
        self.assertTrue(pal_req.selector_locked_out)

        ntsc_req = p360.simulate_ntscpal_sku_avfinfo_and_slot1_erofs_hil(
            sku_code="J1", requested_tv_system="NTSC"
        )
        self.assertTrue(ntsc_req.admitted)
        self.assertEqual(ntsc_req.effective_tv_system, "NTSC")
        self.assertTrue(ntsc_req.selector_locked_out)

    def test_82_80d_u2_switches_to_pal_cold_reboot_banner_no_mandatory_format(self) -> None:
        res = p360.simulate_ntscpal_sku_avfinfo_and_slot1_erofs_hil(
            sku_code="U2", requested_tv_system="PAL"
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.default_tv_system, "NTSC")
        self.assertEqual(res.effective_tv_system, "PAL")
        self.assertEqual(res.boot_banner_msg, "Running on PAL.")
        self.assertTrue(res.requires_cold_reboot)
        self.assertFalse(res.card_format_mandatory)

    def test_83_80d_ce_cec_e33_switch_to_ntsc_running_on_ntsc_banner(self) -> None:
        for sku in ("CE", "CEC", "E33"):
            res = p360.simulate_ntscpal_sku_avfinfo_and_slot1_erofs_hil(
                sku_code=sku, requested_tv_system="NTSC"
            )
            self.assertTrue(res.admitted)
            self.assertEqual(res.default_tv_system, "PAL")
            self.assertEqual(res.boot_banner_msg, "Running on NTSC.")
            self.assertTrue(res.requires_cold_reboot)
            self.assertFalse(res.card_format_mandatory)

    def test_84_80d_cross_region_playback_blocked_vs_matched_playback_ok(self) -> None:
        blk = p360.simulate_ntscpal_sku_avfinfo_and_slot1_erofs_hil(
            operation="playback_clip", current_tv_system="PAL", clip_tv_system="NTSC"
        )
        self.assertFalse(blk.admitted)
        self.assertEqual(blk.errno_code, p360.EOPNOTSUPP_ERRNO)
        self.assertTrue(blk.cross_region_playback_blocked)

        ok = p360.simulate_ntscpal_sku_avfinfo_and_slot1_erofs_hil(
            operation="playback_clip", current_tv_system="PAL", clip_tv_system="PAL"
        )
        self.assertTrue(ok.admitted)
        self.assertFalse(ok.cross_region_playback_blocked)

    def test_85_80d_slot1_tier0_enforces_hard_erofs30_on_all_writes(self) -> None:
        for op in ("avf_info_create", "avf_info_update", "recover_image_db", "card_format"):
            res = p360.simulate_ntscpal_sku_avfinfo_and_slot1_erofs_hil(
                operation=op, target_slot="Slot 1"
            )
            self.assertFalse(res.admitted)
            self.assertEqual(res.errno_code, p360.EROFS_ERRNO)
            self.assertEqual(res.slot1_data_sector_writes, 0)
            self.assertFalse(res.slot1_avf_info_mutated)

    def test_86_80d_slot2_avf_info_create_update_prompts(self) -> None:
        c = p360.simulate_ntscpal_sku_avfinfo_and_slot1_erofs_hil(
            operation="avf_info_create", target_slot="Slot 2"
        )
        u = p360.simulate_ntscpal_sku_avfinfo_and_slot1_erofs_hil(
            operation="avf_info_update", target_slot="Slot 2"
        )
        self.assertTrue(c.admitted)
        self.assertIn("Create?", c.avf_info_prompt or "")
        self.assertTrue(u.admitted)
        self.assertIn("Update?", u.avf_info_prompt or "")

    def test_87_80d_recover_image_db_low_battery_refusal_eagain(self) -> None:
        low_pct = p360.simulate_ntscpal_sku_avfinfo_and_slot1_erofs_hil(
            operation="recover_image_db", target_slot="Slot 2", battery_pct=9, battery_mv=7200
        )
        low_mv = p360.simulate_ntscpal_sku_avfinfo_and_slot1_erofs_hil(
            operation="recover_image_db", target_slot="Slot 2", battery_pct=15, battery_mv=6399
        )
        ok = p360.simulate_ntscpal_sku_avfinfo_and_slot1_erofs_hil(
            operation="recover_image_db", target_slot="Slot 2", battery_pct=10, battery_mv=6400
        )
        self.assertFalse(low_pct.admitted)
        self.assertEqual(low_pct.errno_code, p360.EAGAIN_ERRNO)
        self.assertFalse(low_mv.admitted)
        self.assertEqual(low_mv.errno_code, p360.EAGAIN_ERRNO)
        self.assertTrue(ok.admitted)

    def test_88_80d_slot2_scratch_card_format_ok_zero_slot1_writes(self) -> None:
        res = p360.simulate_ntscpal_sku_avfinfo_and_slot1_erofs_hil(
            operation="card_format", target_slot="Slot 2"
        )
        self.assertTrue(res.admitted)
        self.assertEqual(res.slot1_data_sector_writes, 0)
        self.assertFalse(res.slot1_avf_info_mutated)

    def test_89_80d_fx6_6_system_frequencies_and_reboot_prompt(self) -> None:
        self.assertEqual(len(p360.FX6_VALID_FREQUENCIES), 6)
        for freq in p360.FX6_VALID_FREQUENCIES:
            res = p360.simulate_ntscpal_sku_avfinfo_and_slot1_erofs_hil(
                body_profile=p360.BODY_MODEL_FX6,
                fw_version=p360.FW_VER_601,
                operation="fx6_system_frequency",
                fx6_active_freq="59.94Hz",
                fx6_requested_freq=freq,
            )
            self.assertTrue(res.admitted)
            self.assertEqual(res.fx6_freq_options_count, 6)
            self.assertEqual(res.fx6_active_freq, freq)
            self.assertEqual(res.requires_cold_reboot, freq != "59.94Hz")

    def test_90_80d_fx6_thumbnail_hides_mismatched_frequency_clips(self) -> None:
        hid = p360.simulate_ntscpal_sku_avfinfo_and_slot1_erofs_hil(
            body_profile=p360.BODY_MODEL_FX6,
            fw_version=p360.FW_VER_601,
            operation="fx6_thumbnail_filter",
            fx6_active_freq="23.98Hz",
            fx6_clip_freq="50Hz",
        )
        shown = p360.simulate_ntscpal_sku_avfinfo_and_slot1_erofs_hil(
            body_profile=p360.BODY_MODEL_FX6,
            fw_version=p360.FW_VER_601,
            operation="fx6_thumbnail_filter",
            fx6_active_freq="23.98Hz",
            fx6_clip_freq="23.98Hz",
        )
        self.assertFalse(hid.admitted)
        self.assertTrue(hid.fx6_thumbnail_hides_mismatched_clips)
        self.assertTrue(shown.admitted)

    def test_91_80d_same_tv_system_no_cold_reboot_needed(self) -> None:
        res = p360.simulate_ntscpal_sku_avfinfo_and_slot1_erofs_hil(
            sku_code="U2", requested_tv_system="NTSC"
        )
        self.assertTrue(res.admitted)
        self.assertFalse(res.requires_cold_reboot)
        self.assertIsNone(res.boot_banner_msg)

    def test_92_80d_cross_body_ntscpal_operations_blocked(self) -> None:
        a = p360.simulate_ntscpal_sku_avfinfo_and_slot1_erofs_hil(
            body_profile=p360.BODY_MODEL_FX3, operation="fx6_system_frequency"
        )
        b = p360.simulate_ntscpal_sku_avfinfo_and_slot1_erofs_hil(
            body_profile=p360.BODY_MODEL_FX6,
            fw_version=p360.FW_VER_601,
            operation="ntsc_pal_select",
        )
        self.assertFalse(a.admitted)
        self.assertEqual(a.errno_code, p360.EOPNOTSUPP_ERRNO)
        self.assertFalse(b.admitted)
        self.assertEqual(b.errno_code, p360.EOPNOTSUPP_ERRNO)

    def test_93_80d_invalid_ntscpal_arguments_raise_stage80_error(self) -> None:
        for kw in (
            {"body_profile": "FX9"},
            {"fw_version": "4.00"},
            {"operation": "format_low_level"},
            {"sku_code": "JP9"},
            {"requested_tv_system": "SECAM"},
            {"clip_tv_system": "SECAM"},
            {"target_slot": "Slot 3"},
            {"fx6_active_freq": "120Hz"},
            {"fx6_clip_freq": "120Hz"},
            {"fx6_requested_freq": "120Hz"},
        ):
            with self.assertRaises(p360.Stage80Phase360Error):
                p360.simulate_ntscpal_sku_avfinfo_and_slot1_erofs_hil(**kw)

    def test_94_80d_pillar_d_passed_in_full_report(self) -> None:
        rep = p360.run_phase360_peaking_cleanhdmi_audiometer_wind_usbpd_dcc1_ntscpal_avfinfo_coemulation(
            force_clean_room=True
        )
        self.assertTrue(rep["pillar_d_ntscpal_sku_avfinfo_slot1_erofs_vs_fx6_freq_hil"]["passed"])

    def test_95_80d_redline_constants_match(self) -> None:
        self.assertEqual(p360.J1_PAL_SWITCH_BYPASS_EVENTS, 0)
        self.assertTrue(p360.NTSC_PAL_SWITCH_REQUIRES_COLD_REBOOT)
        self.assertFalse(p360.NTSC_PAL_FORMAT_MANDATORY_IN_V702)
        self.assertEqual(p360.RECOVER_DB_LOW_BATT_MIN_PCT, 10)
        self.assertEqual(p360.RECOVER_DB_LOW_BATT_MIN_MV, 6400)
        self.assertEqual(p360.FX6_FREQ_OPTIONS_COUNT, 6)

    def test_96_normal_vs_clean_room_digests_distinguishable_when_donors_present(self) -> None:
        if p360.is_forced_clean_room():
            self.skipTest("clean-room env forced")
        root = p360.resolve_mac_work_root()
        if root is None or not root.exists():
            self.skipTest("local donor Mac/work not present")
        norm = p360.run_phase360_peaking_cleanhdmi_audiometer_wind_usbpd_dcc1_ntscpal_avfinfo_coemulation(
            force_clean_room=False
        )
        cr = p360.run_phase360_peaking_cleanhdmi_audiometer_wind_usbpd_dcc1_ntscpal_avfinfo_coemulation(
            force_clean_room=True
        )
        self.assertNotEqual(norm["audit_digest_sha256"], cr["audit_digest_sha256"])

    # -----------------------------------------------------------------------
    # 97..100: CLI, Portability Guard & Suite 80/80 Integration Contract
    # -----------------------------------------------------------------------

    def test_97_standalone_cli_help_summary_and_json_modes(self) -> None:
        res_help = subprocess.run(
            [sys.executable, "-B", str(Path(p360.__file__).resolve()), "--help"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(res_help.returncode, 0)
        self.assertIn("--clean-room", res_help.stdout)

        buf_sum = io.StringIO()
        with contextlib.redirect_stdout(buf_sum):
            rc_sum = p360.main(["--self-test", "--clean-room", "--summary"])
        self.assertEqual(rc_sum, 0)
        self.assertIn("[PASS] Phase 360 Stage 80 (80/80 Stages)", buf_sum.getvalue())

        buf_json = io.StringIO()
        with contextlib.redirect_stdout(buf_json):
            rc_json = p360.main(["--clean-room", "--json"])
        self.assertEqual(rc_json, 0)
        parsed = json.loads(buf_json.getvalue())
        self.assertEqual(parsed["milestone"], "80/80")
        self.assertTrue(parsed["is_80th_stage_milestone"])

    def test_98_portability_no_hardcoded_system_python_path_in_module_or_tests(self) -> None:
        mod_src = (
            FX3_VM_DIR
            / "realhw_peaking_cleanhdmi_audiometer_wind_usbpd_dcc1_ntscpal_avfinfo_coemulator.py"
        ).read_text(encoding="utf-8")
        tst_src = Path(__file__).read_text(encoding="utf-8")
        forbidden = "/" + "usr/bin/" + "python3"
        self.assertNotIn(forbidden, mod_src)
        self.assertNotIn(forbidden, tst_src)

    def test_99_suite_default_config_enables_stage80_and_full_run_has_at_least_80_stages(self) -> None:
        cfg = suite.CoEmulationConfig()
        self.assertTrue(
            cfg.include_phase360_realhw_peaking_cleanhdmi_audiometer_wind_usbpd_dcc1_ntscpal_avfinfo_hil
        )
        self.assertTrue(cfg.include_stage80)
        self.assertTrue(
            cfg.stage80_realhw_peaking_cleanhdmi_audiometer_wind_usbpd_dcc1_ntscpal_avfinfo_hil
        )

        t0 = time.monotonic()
        rep = suite.run_fx3_vm_coemulation_suite(cfg)
        elapsed = time.monotonic() - t0
        self.assertTrue(rep["all_checks_passed"])
        stage_keys = [k for k in rep if re.match(r"^stage\d+_", k)]
        self.assertGreaterEqual(len(stage_keys), 80)
        self.assertIn(
            "stage80_realhw_peaking_cleanhdmi_audiometer_wind_usbpd_dcc1_ntscpal_avfinfo_hil",
            rep,
        )
        s80 = rep["stage80_realhw_peaking_cleanhdmi_audiometer_wind_usbpd_dcc1_ntscpal_avfinfo_hil"]
        self.assertTrue(s80["all_checks_passed"])
        self.assertTrue(s80["is_80th_stage_milestone"])
        self.assertEqual(s80["milestone"], "80/80")
        self.assertEqual(s80["phase_number"], 360)
        max_elapsed = 30.0 if IS_CI else 15.0
        self.assertLess(elapsed, max_elapsed)

    def test_100_suite_skip_flags_summary_cli_and_tamper_detection(self) -> None:
        for flag in ("--skip-stage80", "--no-include-stage80", "--skip-phase360"):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = suite.main([*_FAST_CLI_FLAGS, flag, "--json"])
            self.assertEqual(rc, 0)
            data = json.loads(buf.getvalue())
            self.assertNotIn(
                "stage80_realhw_peaking_cleanhdmi_audiometer_wind_usbpd_dcc1_ntscpal_avfinfo_hil",
                data,
            )
            self.assertFalse(data["config"]["include_stage80"])

        buf_sum = io.StringIO()
        with contextlib.redirect_stdout(buf_sum):
            rc_sum = suite.main([*_FAST_CLI_FLAGS, "--include-stage80", "--summary"])
        self.assertEqual(rc_sum, 0)
        self.assertIn(
            "realhw_peaking_cleanhdmi_audiometer_wind_usbpd_dcc1_ntscpal_avfinfo_hil="
            "CLEAN_ROOM_SYNTHETIC(m80=80/80,hdmi_pk=0,aud_it=5,fz100=1,s1_wr=0,emmc_wr=0)",
            buf_sum.getvalue(),
        )

        # Direct suite tamper detection across Stage 80 safety & Wave-70 invariants
        base_cfg = suite.CoEmulationConfig(**_fast_suite_kwargs())
        clean_rep = suite.run_fx3_vm_coemulation_suite(base_cfg)
        self.assertTrue(clean_rep["all_checks_passed"])

        for attr, val in (
            ("IS_80TH_STAGE_MILESTONE", False),
            ("FX3_PEAKING_ITEMS_COUNT", 4),
            ("PEAKING_RESET_WIPE_EVENTS", 1),
            ("HDMI_PEAKING_LEAKED_PIXELS", 1),
            ("PEAKING_FOCUS_MAG_CONFLICT_EVENTS", 1),
            ("FX3_BODY_FOCUS_MAP_EXPOSED", True),
            ("FOCUS_MAP_OVER_USB_SUPPORTED", True),
            ("FX6_PEAKING_TYPE_OR_FREQ_EXPOSED_EVENTS", 1),
            ("FX6_PEAKING_APPFW_TYPE_FREQ_SYMBOL_COUNT", 1),
            ("AUDIO_RECORDING_MENU_ITEMS_COUNT", 6),
            ("AUDIO_REC_LEVEL_DEFAULT", 20),
            ("WIND_NOISE_REDUCT_AUTO_OR_ADVANCED_EXPOSED_EVENTS", 1),
            ("EXTERNAL_MIC_WIND_REDUCT_APPLIED_FRAMES", 1),
            ("MM35_PREEMPTION_OVER_XLRH1_BYPASS_EVENTS", 1),
            ("FX6_HANDLE_PHYSICAL_LOW_CUT_PRESENT", True),
            ("USB_POWER_SUPPLY_MULTI_MICRO_BYPASS_EVENTS", 1),
            ("FX3_BATTERYLESS_BOOT_ALLOWED", True),
            ("FX3_POWER_ON_CHARGING_EVENTS", 1),
            ("DCC1_UNDERPOWER_BOOT_BYPASS_EVENTS", 1),
            ("FX6_DC_IN_HOT_REPLUG_REBOOT_UNBLOCKED_EVENTS", 1),
            ("FX6_USBC_POWER_SUPPORTED", True),
            ("J1_PAL_SWITCH_BYPASS_EVENTS", 1),
            ("CROSS_REGION_MOVIE_PLAYBACK_BYPASS_EVENTS", 1),
            ("RECOVER_DB_LOW_BATT_BYPASS_EVENTS", 1),
            ("SLOT1_AVF_INFO_OR_FORMAT_WRITE_BYPASS_EVENTS", 1),
            ("FX6_THUMBNAIL_CROSS_FREQ_LEAK_EVENTS", 1),
            ("SLOT1_DATA_SECTOR_WRITES", 1),
            ("EMMC_NFLASHA_WRITE_COUNT", 1),
            ("RAW_FIRMWARE_BYTES_LEAKED", 1),
        ):
            with unittest.mock.patch.object(p360, attr, val):
                rep = suite.run_fx3_vm_coemulation_suite(base_cfg)
                self.assertFalse(rep["all_checks_passed"], attr)


if __name__ == "__main__":
    unittest.main()
