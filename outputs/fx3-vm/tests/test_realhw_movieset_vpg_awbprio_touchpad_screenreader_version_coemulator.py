#!/usr/bin/env python3
"""Unit tests for Phase 379 (Stage 87 — 87/87 Full-Board VM Co-Emulation Stages!):
Real-Hardware `ILME-FX3 Ver. 7.02` vs `ILME-FX6 Ver. 6.01` Wave-77 HIL:
- 87A: `[File Format]` & `[Movie Settings]` 6-Codec Matrix (`XAVC HS 4K`,
  `XAVC S 4K`, `XAVC S HD` factory default, `XAVC S-I 4K`, `XAVC S-I HD`,
  `XAVC S-I DCI 4K` Ver. 3.00+ `_f 0x7336`), dormant `8K` (`xavc_hs_8k`)
  blocked `EOPNOTSUPP=95`, `24.00p` cross-mode reboot
  (`MODEL_EVENT_REBOOT_BY_CROSS_2400P`) + playback isolation (`_g 0x6127/
  0x63d7`) + `4K Output Set.(HDMI Only)` mutex + `48fps` S&Q exclusive to
  `24.00p + DCI 4K`, 5-tier ELF transfer-rate firewall (`100/200/400/600/1350
  MBPS`), Wave-77 `G139` Erratum (`S&Q XAVC S HD 100/120fps` needs ONLY `SDXC
  V60+`; `200/240fps` needs `V90+`; `S&Q XAVC S-I DCI 4K` forbids `100/120fps`;
  `VPG400` enforces `1350MBPS` proxy-stack threshold for `S&Q XAVC S-I 4K
  1200M + Proxy`), Reset behavior vs FX6 `Project > Rec Format` (`Class300`
  max `600M VBR`, dormant `Class480` & `XAVC-L25` blocked),
- 87B: `[Priority Set in AWB]` (`Standard`/`Ambience`/`White`, `Can be reset`,
  `Flexible ISO` active, `Cine EI`/`Cine EI Quick` disables `Auto`/`Underwater
  Auto`), Still-only `[Shutter AWB Lock]` (Movie/S&Q blocked `EOPNOTSUPP=95`,
  resists Reset), `2500K..9900K` (`75` steps) + `A7..B7` (`29` steps) +
  `G7..M7` (`57` steps) `[C.Temp./Filter]` vs FX6 physical `WHT BAL`
  (`B/A/PRESET`), `Preset`, `ATW` (`2000K..15000K`, `Speed 1..5`, `ATW Hold`),
  `Tint -99..+99`, `R/B Gain -99.0..+99.0`, `Shockless White`,
- 87C: `[Touch Operation]` strictly 4 exposed items (all resist Reset) vs
  dormant EVF `[Touch Panel/Pad]`, `Touch Pad Settings/Area Set./vertical`, &
  `Touch Shutter` blocked `EOPNOTSUPP=95` on EVF-less FX3, Wave-77 `G109`
  Erratum (ALL 7 items across `[Focus Assistant]` + `[Peaking Display]` resist
  Reset, reset ONLY on `[Initialize]`; `[AF in Focus Mag.]` strictly Still-only
  with 5 lockouts; `0` HDMI peaking) vs FX6 3-item `Peaking` (dormant `Peaking
  Type`/`Frequency` blocked `EOPNOTSUPP=95`),
- 87D: `[Accessibility]`/`[Screen Reader]` SKU gate (`0` UI exposure on both
  `ILME-FX3` & `ILME-FX6`; `0` HDMI audio link), Wave-77 `G104` Erratum
  EXACTLY 2-slot `[Version]` dialog (`Body` & `Lens` shared by Mount Adaptor;
  NO 3rd mount-adaptor slot; NO MI-Shoe version), Ver. 6.00+ online update dot
  silenced in `Airplane Mode = On` (`rf_tx_packets == 0`), and `[Software
  Update]` `Slot 1 BODYDATA.DAT` hard-blocked `EROFS=30` vs FX6 `Maintenance >
  Version` (`Body`/`Lens`/`Ext. Unit`, `Slot B` + AC adapter) (108 four-mode
  forward-compatible tests).
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
import unittest
import unittest.mock

FX3_VM_DIR = Path(__file__).resolve().parents[1]
if str(FX3_VM_DIR) not in sys.path:
    sys.path.insert(0, str(FX3_VM_DIR))

import fx3_vm_coemulation_suite as suite  # noqa: E402
import realhw_movieset_vpg_awbprio_touchpad_screenreader_version_coemulator as p379  # noqa: E402


def _fast_suite_kwargs(**overrides: object) -> dict:
    """Fast config skipping unrelated optional stages 4..86 for Stage 87 isolation."""
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
        include_stage80=False,
        include_stage81=False,
        include_stage82=False,
        include_stage83=False,
        include_stage84=False,
        include_stage85=False,
        include_stage86=False,
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
    "--skip-stage80",
    "--skip-stage81",
    "--skip-stage82",
    "--skip-stage83",
    "--skip-stage84",
    "--skip-stage85",
    "--skip-stage86",
]


class TestPhase379Stage87MovieSetVpgAwbPrioTouchPadScreenReaderVersion(unittest.TestCase):
    # =========================================================================
    # Tests 01..16: Schema, Stage 87 (87/87), Tier-0 Redlines & 4-Mode Donors
    # =========================================================================

    def test_01_schema_phase_and_stage87_constants(self) -> None:
        self.assertEqual(
            p379.SCHEMA_ID,
            "phase379_realhw_movieset_vpg_awbprio_touchpad_screenreader_version_coemulation_v1",
        )
        self.assertEqual(p379.PHASE_NUMBER, 379)
        self.assertEqual(p379.STAGE_INDEX, 87)
        self.assertEqual(p379.STAGE_TOTAL, 87)
        self.assertEqual(p379.MILESTONE_LABEL, "87/87")
        self.assertFalse(p379.READY_FOR_LIVE_CAMERA_ATTACH)
        self.assertFalse(p379.LIVE_ATTACH_AUTHORIZED)
        self.assertFalse(p379.CROSS_MODEL_FLASH_AUTHORIZED)
        self.assertFalse(p379.SLOT1_BODYDATA_WRITE_AUTHORIZED)
        self.assertEqual(p379.SLOT1_WRITES, 0)

    def test_02_orchestrator_returns_stage87_and_all_zero_redlines(self) -> None:
        rep = p379.run_phase379_realhw_movieset_vpg_awbprio_touchpad_screenreader_version_coemulation(
            force_clean_room=True
        )
        self.assertTrue(rep["all_checks_passed"])
        self.assertEqual(rep["phase_number"], 379)
        self.assertEqual(rep["stage_index"], 87)
        self.assertEqual(rep["stage_total"], 87)
        self.assertEqual(rep["milestone"], "87/87")
        self.assertFalse(rep["ready_for_live_camera_attach"])
        self.assertFalse(rep["live_attach_authorized"])
        self.assertEqual(rep["nop_count"], 0)
        self.assertEqual(rep["guest_code_modification_bytes"], 0)
        self.assertEqual(rep["cp_mutation_bytes"], 0)
        self.assertEqual(rep["wbi_mutation_bytes"], 0)
        self.assertEqual(rep["calibration_mutation_bytes"], 0)
        self.assertEqual(rep["cnflasha_mutation_bytes"], 0)
        self.assertTrue(rep["cnflasha_userspace_write_blocked"])
        self.assertEqual(rep["nvram_persistent_writes"], 0)
        self.assertEqual(rep["bk4_persistent_nvram_writes"], 0)
        self.assertEqual(rep["physical_device_writes"], 0)
        self.assertFalse(rep["persistent_emmc_writes_authorized"])
        self.assertFalse(rep["emmc_writes_authorized"])
        self.assertFalse(rep["cross_model_flash_authorized"])
        self.assertFalse(rep["hardware_live_attachment_authorized"])
        self.assertFalse(rep["overall_ready_for_hardware_attach"])
        self.assertFalse(rep["isp_write_authorized"])
        self.assertEqual(rep["emmc_nflasha_write_count"], 0)
        self.assertEqual(rep["emmc_mutation_bytes"], 0)
        self.assertEqual(rep["emmc_corruptions"], 0)
        self.assertFalse(rep["spi_nor_write_authorized"])
        self.assertEqual(rep["spi_nor_mutation_bytes"], 0)
        self.assertFalse(rep["el3_payload_transmit_authorized"])
        self.assertEqual(rep["otp_fuse_touches"], 0)
        self.assertEqual(rep["rpmb_counter_increments"], 0)
        self.assertEqual(rep["usb_tx_packets"], 0)
        self.assertEqual(rep["physical_usb_packets_emitted"], 0)
        self.assertEqual(rep["passive_tx_bytes_emitted"], 0)
        self.assertFalse(rep["slot1_bodydata_write_authorized"])
        self.assertEqual(rep["slot1_writes"], 0)
        self.assertEqual(rep["slot1_sector_writes"], 0)
        self.assertEqual(rep["slot1_data_sector_writes"], 0)
        self.assertFalse(rep["slot1_avf_info_mutated"])
        self.assertEqual(rep["rf_tx_packets"], 0)
        self.assertEqual(rep["rf_packets_transmitted"], 0)
        self.assertEqual(rep["rf_nvs_mutation_bytes"], 0)
        self.assertEqual(rep["rsv_orphan_count"], 0)
        self.assertEqual(rep["wf12_00342260_hits"], 0)
        self.assertEqual(rep["appfw_crashes"], 0)
        self.assertEqual(rep["null_gpio_derefs"], 0)
        self.assertEqual(rep["mailbox_stalls"], 0)
        self.assertEqual(rep["stock_cp_fault_count"], 0)
        self.assertEqual(rep["raw_firmware_bytes_leaked"], 0)

    def test_03_donors_count_is_20_with_17_compact_and_3_window(self) -> None:
        self.assertEqual(len(p379.PHASE379_COMPACT_DONORS), 17)
        self.assertEqual(len(p379.PHASE379_WINDOW_DONORS), 3)
        info = p379.inspect_phase379_wave77_donors(force_clean_room=True)
        self.assertEqual(info["compact_donors_count"], 17)
        self.assertEqual(info["window_donors_count"], 3)
        self.assertEqual(info["total_donors_count"], 20)
        self.assertTrue(info["all_donors_verified"])
        self.assertEqual(info["raw_firmware_bytes_leaked"], 0)

    def test_04_donor_mode_normal_env(self) -> None:
        info = p379.inspect_phase379_wave77_donors()
        self.assertTrue(info["all_donors_verified"])
        self.assertIn(info["source_mode"], ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"))
        self.assertEqual(info["total_donors_count"], 20)
        self.assertEqual(info["raw_firmware_bytes_leaked"], 0)

    def test_05_donor_mode_fx3_clean_room_test_env(self) -> None:
        info = p379.inspect_phase379_wave77_donors(env={"FX3_CLEAN_ROOM_TEST": "1"})
        self.assertEqual(info["source_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(info["forced_clean_room"])
        self.assertTrue(info["all_donors_verified"])

    def test_06_donor_mode_fx3_fx6_force_clean_room_env(self) -> None:
        info = p379.inspect_phase379_wave77_donors(env={"FX3_FX6_FORCE_CLEAN_ROOM": "1"})
        self.assertEqual(info["source_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(info["forced_clean_room"])
        self.assertTrue(info["all_donors_verified"])

    def test_07_donor_mode_work_root_none_and_sentinel(self) -> None:
        info_none = p379.inspect_phase379_wave77_donors(work_root=None)
        self.assertEqual(info_none["source_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertFalse(info_none["work_root_available"])
        info_sent = p379.inspect_phase379_wave77_donors(
            env={"FX3_FX6_MAC_WORK_ROOT": p379._DONOR_DISABLED_SENTINEL}
        )
        self.assertEqual(info_sent["source_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertFalse(info_sent["work_root_available"])

    def test_08_donor_mode_nonexistent_work_root_graceful_clean_room(self) -> None:
        info = p379.inspect_phase379_wave77_donors(
            work_root="/nonexistent/phase379_stage87_missing_dir",
            force_clean_room=False,
        )
        self.assertEqual(info["source_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(info["all_donors_verified"])

    def test_09_resolve_mac_work_root_and_is_forced_clean_room_helpers(self) -> None:
        self.assertIsNone(p379.resolve_mac_work_root(work_root=None))
        self.assertIsNone(p379.resolve_mac_work_root(work_root=""))
        self.assertIsNone(p379.resolve_mac_work_root(work_root=p379._DONOR_DISABLED_SENTINEL))
        self.assertEqual(
            p379.resolve_mac_work_root(work_root="/tmp/demo"), Path("/tmp/demo")
        )
        self.assertIsNone(
            p379.resolve_mac_work_root(env={"FX3_FX6_MAC_WORK_ROOT": ""})
        )
        self.assertTrue(p379.is_forced_clean_room({"FX3_CLEAN_ROOM_TEST": "1"}))
        self.assertTrue(p379.is_forced_clean_room({"FX3_FX6_FORCE_CLEAN_ROOM": "1"}))
        self.assertFalse(p379.is_forced_clean_room({}))

    def test_10_bounded_window_rejects_oversized_read_request(self) -> None:
        with self.assertRaises(p379.Stage87Phase379Error):
            p379._read_bounded_window_o_rdonly(Path(__file__), 0, 4097)

    def test_11_compact_reader_rejects_file_over_1mib(self) -> None:
        fake_stat = unittest.mock.MagicMock(st_size=2 * 1024 * 1024)
        with unittest.mock.patch("os.open", return_value=99), \
             unittest.mock.patch("os.fstat", return_value=fake_stat), \
             unittest.mock.patch("os.close"):
            with self.assertRaises(p379.Stage87Phase379Error):
                p379._read_full_compact_o_rdonly(Path("/fake/huge.bin"))

    def test_12_lib_infra_get_version_spec_forbids_mount_shoe_ext(self) -> None:
        spec = next(
            s for s in p379.PHASE379_COMPACT_DONORS if s.name == "fx3_lib_infra_get_version"
        )
        self.assertIn(b"InfraGetVersion", spec.required_tokens)
        self.assertIn(b"InfraGetVersionLens", spec.required_tokens)
        self.assertIn(b"InfraGetVersionMount", spec.absent_tokens)
        self.assertIn(b"InfraGetVersionShoe", spec.absent_tokens)
        self.assertIn(b"InfraGetVersionExt", spec.absent_tokens)

    def test_13_fx3_appfw_window_spec_covers_all_5_transfer_tiers_and_screen_reader(self) -> None:
        w = next(w for w in p379.PHASE379_WINDOW_DONORS if w.name == "fx3_appfw")
        labels = {lbl for _, lbl, _ in w.windows}
        for tier in ("100", "200", "400", "600", "1350"):
            self.assertIn(f"RATE_UNDER_{tier}MBPS", labels)
        self.assertIn("REBOOT_CROSS_2400P", labels)
        self.assertIn("DORMANT_XAVC_HS_8K", labels)
        self.assertIn("DORMANT_TOUCH_PANEL_PAD", labels)
        self.assertIn("SUPPORT_SCREEN_READER", labels)
        self.assertIn("SCREEN_READER_CPP", labels)

    def test_14_fx6_appfw_window_spec_forbids_peaking3_frequency_type(self) -> None:
        w = next(w for w in p379.PHASE379_WINDOW_DONORS if w.name == "fx6_appfw")
        labels = {lbl for _, lbl, _ in w.windows}
        abs_labels = {lbl for _, lbl, _ in w.absent_windows}
        self.assertIn("FX6_USER_MENU_PEAKING0", labels)
        self.assertIn("FX6_USER_MENU_PEAKING1", labels)
        self.assertIn("FX6_USER_MENU_PEAKING2", labels)
        self.assertIn("FX6_NO_USER_MENU_PEAKING3", abs_labels)
        self.assertIn("FX6_NO_PEAKING_FREQUENCY", abs_labels)
        self.assertIn("FX6_NO_PEAKING_TYPE", abs_labels)

    def test_15_stage87_probe_fields_all_true(self) -> None:
        rep = p379.run_phase379_realhw_movieset_vpg_awbprio_touchpad_screenreader_version_coemulation(
            work_root=None
        )
        pr = rep["stage87_probe"]
        self.assertEqual(pr["stage_index"], 87)
        self.assertEqual(pr["stage_total"], 87)
        self.assertEqual(pr["milestone_label"], "87/87")
        self.assertTrue(pr["submodel_87a_passed"])
        self.assertTrue(pr["submodel_87b_passed"])
        self.assertTrue(pr["submodel_87c_passed"])
        self.assertTrue(pr["submodel_87d_passed"])
        self.assertFalse(pr["ready_for_live_camera_attach"])

    def test_16_audit_digest_sha256_is_valid_64_hex(self) -> None:
        rep = p379.run_phase379_realhw_movieset_vpg_awbprio_touchpad_screenreader_version_coemulation(
            force_clean_room=True
        )
        self.assertRegex(rep["phase379_audit_digest_sha256"], r"^[0-9a-f]{64}$")

    # =========================================================================
    # Tests 17..42: Sub-Model 87A — 6 Codecs, 24.00p, 5-Tier VPG & G139 Erratum
    # =========================================================================

    def test_17_87a_fx3_exact_6_codecs_and_default_xavc_s_hd(self) -> None:
        self.assertEqual(len(p379.FX3_FILE_FORMATS), 6)
        self.assertEqual(p379.FX3_FILE_FORMAT_DEFAULT, "XAVC S HD")
        for fmt in p379.FX3_FILE_FORMATS:
            spec = p379.FX3_CODEC_SPECS[fmt]
            res = p379.simulate_87a_movieset_6codec_2400p_vpg_and_fx6_recfmt(
                operation="fx3_file_format_6codec_and_dormant_8k",
                file_format=fmt,
                rec_frame_rate=spec["default_frame_rate"],
                bitrate_mbps=spec["max_movie_bitrate_mbps"],
            )
            self.assertTrue(res.allowed, fmt)
            self.assertEqual(res.errno, 0)

    def test_18_87a_fx3_xavc_hs_4k_rejects_2997p_and_25p(self) -> None:
        for bad_fps in ("29.97p", "25p"):
            res = p379.simulate_87a_movieset_6codec_2400p_vpg_and_fx6_recfmt(
                operation="fx3_file_format_6codec_and_dormant_8k",
                file_format="XAVC HS 4K",
                rec_frame_rate=bad_fps,
                bitrate_mbps=100,
            )
            self.assertFalse(res.allowed)
            self.assertEqual(res.errno, p379.EOPNOTSUPP_ERRNO)

    def test_19_87a_fx3_dormant_8k_blocked_eopnotsupp(self) -> None:
        for bad_8k in ("xavc_hs_8k", "XAVC HS 8K"):
            res = p379.simulate_87a_movieset_6codec_2400p_vpg_and_fx6_recfmt(
                operation="fx3_file_format_6codec_and_dormant_8k",
                file_format=bad_8k,
            )
            self.assertFalse(res.allowed)
            self.assertEqual(res.errno, p379.EOPNOTSUPP_ERRNO)
            self.assertTrue(res.dormant_8k_blocked)

    def test_20_87a_fx3_camera_settings_reset_restores_file_format_and_movieset(self) -> None:
        res = p379.simulate_87a_movieset_6codec_2400p_vpg_and_fx6_recfmt(
            operation="fx3_file_format_6codec_and_dormant_8k",
            file_format="XAVC S-I DCI 4K",
            rec_frame_rate="24.00p",
            bitrate_mbps=240,
            camera_settings_reset_triggered=True,
        )
        self.assertTrue(res.allowed)
        self.assertEqual(res.file_format, "XAVC S HD")
        self.assertEqual(res.rec_frame_rate, "59.94p")
        self.assertTrue(res.can_be_reset_by_cam_reset)

    def test_21_87a_fx3_2400p_exclusive_to_xavc_si_dci_4k(self) -> None:
        res = p379.simulate_87a_movieset_6codec_2400p_vpg_and_fx6_recfmt(
            operation="fx3_2400p_reboot_playback_isolation_and_sq_48fps",
            file_format="XAVC S-I 4K",
            rec_frame_rate="24.00p",
        )
        self.assertFalse(res.allowed)
        self.assertEqual(res.errno, p379.EOPNOTSUPP_ERRNO)

    def test_22_87a_fx3_cross_into_2400p_triggers_reboot_event(self) -> None:
        res = p379.simulate_87a_movieset_6codec_2400p_vpg_and_fx6_recfmt(
            operation="fx3_2400p_reboot_playback_isolation_and_sq_48fps",
            file_format="XAVC S-I DCI 4K",
            previous_frame_rate="23.98p",
            rec_frame_rate="24.00p",
        )
        self.assertTrue(res.allowed)
        self.assertTrue(res.reboot_required)
        self.assertEqual(res.reboot_event, "MODEL_EVENT_REBOOT_BY_CROSS_2400P")

    def test_23_87a_fx3_cross_out_of_2400p_triggers_reboot_event(self) -> None:
        res = p379.simulate_87a_movieset_6codec_2400p_vpg_and_fx6_recfmt(
            operation="fx3_2400p_reboot_playback_isolation_and_sq_48fps",
            file_format="XAVC S-I DCI 4K",
            previous_frame_rate="24.00p",
            rec_frame_rate="59.94p",
        )
        self.assertTrue(res.allowed)
        self.assertTrue(res.reboot_required)
        self.assertEqual(res.reboot_event, "MODEL_EVENT_REBOOT_BY_CROSS_2400P")

    def test_24_87a_fx3_2400p_playback_isolation_blocks_non_2400p(self) -> None:
        res = p379.simulate_87a_movieset_6codec_2400p_vpg_and_fx6_recfmt(
            operation="fx3_2400p_reboot_playback_isolation_and_sq_48fps",
            file_format="XAVC S-I DCI 4K",
            rec_frame_rate="24.00p",
            playback_clip_is_2400p=False,
        )
        self.assertFalse(res.allowed)
        self.assertEqual(res.errno, p379.EOPNOTSUPP_ERRNO)
        self.assertTrue(res.playback_isolation_enforced)

    def test_25_87a_fx3_non_2400p_playback_isolation_blocks_2400p_clips(self) -> None:
        res = p379.simulate_87a_movieset_6codec_2400p_vpg_and_fx6_recfmt(
            operation="fx3_2400p_reboot_playback_isolation_and_sq_48fps",
            file_format="XAVC S-I 4K",
            rec_frame_rate="23.98p",
            playback_clip_is_2400p=True,
        )
        self.assertFalse(res.allowed)
        self.assertEqual(res.errno, p379.EOPNOTSUPP_ERRNO)

    def test_26_87a_fx3_matching_2400p_playback_allowed(self) -> None:
        res = p379.simulate_87a_movieset_6codec_2400p_vpg_and_fx6_recfmt(
            operation="fx3_2400p_reboot_playback_isolation_and_sq_48fps",
            file_format="XAVC S-I DCI 4K",
            rec_frame_rate="24.00p",
            playback_clip_is_2400p=True,
        )
        self.assertTrue(res.allowed)
        self.assertTrue(res.playback_isolation_enforced)

    def test_27_87a_fx3_2400p_hdmi_only_4k_output_mutex_ebusy(self) -> None:
        res = p379.simulate_87a_movieset_6codec_2400p_vpg_and_fx6_recfmt(
            operation="fx3_2400p_reboot_playback_isolation_and_sq_48fps",
            file_format="XAVC S-I DCI 4K",
            rec_frame_rate="24.00p",
            hdmi_only_4k_output_requested=True,
        )
        self.assertFalse(res.allowed)
        self.assertEqual(res.errno, p379.EBUSY_ERRNO)

    def test_28_87a_fx3_sq_48fps_exclusive_to_2400p_dci_4k(self) -> None:
        ok = p379.simulate_87a_movieset_6codec_2400p_vpg_and_fx6_recfmt(
            operation="fx3_2400p_reboot_playback_isolation_and_sq_48fps",
            shoot_mode="S&Q",
            file_format="XAVC S-I DCI 4K",
            rec_frame_rate="24.00p",
            sq_frame_rate_fps=48,
        )
        self.assertTrue(ok.allowed)
        self.assertTrue(ok.sq_48fps_exclusive_ok)

        bad = p379.simulate_87a_movieset_6codec_2400p_vpg_and_fx6_recfmt(
            operation="fx3_2400p_reboot_playback_isolation_and_sq_48fps",
            shoot_mode="S&Q",
            file_format="XAVC S-I 4K",
            rec_frame_rate="23.98p",
            sq_frame_rate_fps=48,
        )
        self.assertFalse(bad.allowed)
        self.assertEqual(bad.errno, p379.EOPNOTSUPP_ERRNO)

    def test_29_87a_g139_sq_xavc_s_hd_100_120fps_needs_only_v60(self) -> None:
        for fps in (100, 120):
            ok_v60 = p379.simulate_87a_movieset_6codec_2400p_vpg_and_fx6_recfmt(
                operation="fx3_card_speed_5tier_vpg_and_g139_erratum",
                shoot_mode="S&Q",
                file_format="XAVC S HD",
                sq_frame_rate_fps=fps,
                card_tier="SDXC V60",
            )
            self.assertTrue(ok_v60.allowed)
            self.assertEqual(ok_v60.required_min_card_tier, "SDXC V60")
            self.assertEqual(ok_v60.required_elf_transfer_tier_mbps, 400)

            bad_v30 = p379.simulate_87a_movieset_6codec_2400p_vpg_and_fx6_recfmt(
                operation="fx3_card_speed_5tier_vpg_and_g139_erratum",
                shoot_mode="S&Q",
                file_format="XAVC S HD",
                sq_frame_rate_fps=fps,
                card_tier="SDXC U3/V30",
            )
            self.assertFalse(bad_v30.allowed)
            self.assertEqual(bad_v30.errno, p379.EAGAIN_ERRNO)

    def test_30_87a_g139_sq_xavc_s_hd_200_240fps_requires_v90(self) -> None:
        for fps in (200, 240):
            bad_v60 = p379.simulate_87a_movieset_6codec_2400p_vpg_and_fx6_recfmt(
                operation="fx3_card_speed_5tier_vpg_and_g139_erratum",
                shoot_mode="S&Q",
                file_format="XAVC S HD",
                sq_frame_rate_fps=fps,
                card_tier="SDXC V60",
            )
            self.assertFalse(bad_v60.allowed)
            self.assertEqual(bad_v60.errno, p379.EAGAIN_ERRNO)
            self.assertEqual(bad_v60.required_min_card_tier, "SDXC V90")

            ok_v90 = p379.simulate_87a_movieset_6codec_2400p_vpg_and_fx6_recfmt(
                operation="fx3_card_speed_5tier_vpg_and_g139_erratum",
                shoot_mode="S&Q",
                file_format="XAVC S HD",
                sq_frame_rate_fps=fps,
                card_tier="SDXC V90",
            )
            self.assertTrue(ok_v90.allowed)

    def test_31_87a_g139_sq_xavc_si_dci_4k_forbids_100_120fps(self) -> None:
        for fps in (100, 120):
            res = p379.simulate_87a_movieset_6codec_2400p_vpg_and_fx6_recfmt(
                operation="fx3_card_speed_5tier_vpg_and_g139_erratum",
                shoot_mode="S&Q",
                file_format="XAVC S-I DCI 4K",
                sq_frame_rate_fps=fps,
                card_tier="CFexpress Type A VPG400",
            )
            self.assertFalse(res.allowed)
            self.assertEqual(res.errno, p379.EOPNOTSUPP_ERRNO)

    def test_32_87a_sq_xavc_si_dci_4k_60fps_600m_allowed_on_v90(self) -> None:
        res = p379.simulate_87a_movieset_6codec_2400p_vpg_and_fx6_recfmt(
            operation="fx3_card_speed_5tier_vpg_and_g139_erratum",
            shoot_mode="S&Q",
            file_format="XAVC S-I DCI 4K",
            sq_frame_rate_fps=60,
            card_tier="SDXC V90",
        )
        self.assertTrue(res.allowed)
        self.assertEqual(res.required_min_card_tier, "SDXC V90")

    def test_33_87a_sq_xavc_si_hd_240fps_requires_vpg200_rejects_v90(self) -> None:
        bad = p379.simulate_87a_movieset_6codec_2400p_vpg_and_fx6_recfmt(
            operation="fx3_card_speed_5tier_vpg_and_g139_erratum",
            shoot_mode="S&Q",
            file_format="XAVC S-I HD",
            sq_frame_rate_fps=240,
            card_tier="SDXC V90",
        )
        self.assertFalse(bad.allowed)
        self.assertEqual(bad.errno, p379.EAGAIN_ERRNO)
        self.assertEqual(bad.required_min_card_tier, "CFexpress Type A VPG200")

        ok = p379.simulate_87a_movieset_6codec_2400p_vpg_and_fx6_recfmt(
            operation="fx3_card_speed_5tier_vpg_and_g139_erratum",
            shoot_mode="S&Q",
            file_format="XAVC S-I HD",
            sq_frame_rate_fps=240,
            card_tier="CFexpress Type A VPG200",
        )
        self.assertTrue(ok.allowed)

    def test_34_87a_sq_xavc_si_4k_120fps_proxy_1350mbps_requires_vpg400(self) -> None:
        bad = p379.simulate_87a_movieset_6codec_2400p_vpg_and_fx6_recfmt(
            operation="fx3_card_speed_5tier_vpg_and_g139_erratum",
            shoot_mode="S&Q",
            file_format="XAVC S-I 4K",
            sq_frame_rate_fps=120,
            proxy_recording_on=True,
            card_tier="CFexpress Type A VPG200",
        )
        self.assertFalse(bad.allowed)
        self.assertEqual(bad.errno, p379.EAGAIN_ERRNO)
        self.assertEqual(bad.required_elf_transfer_tier_mbps, 1350)
        self.assertEqual(bad.required_min_card_tier, "CFexpress Type A VPG400")

        ok_vpg400 = p379.simulate_87a_movieset_6codec_2400p_vpg_and_fx6_recfmt(
            operation="fx3_card_speed_5tier_vpg_and_g139_erratum",
            shoot_mode="S&Q",
            file_format="XAVC S-I 4K",
            sq_frame_rate_fps=120,
            proxy_recording_on=True,
            card_tier="CFexpress Type A VPG400",
        )
        self.assertTrue(ok_vpg400.allowed)

        ok_no_proxy = p379.simulate_87a_movieset_6codec_2400p_vpg_and_fx6_recfmt(
            operation="fx3_card_speed_5tier_vpg_and_g139_erratum",
            shoot_mode="S&Q",
            file_format="XAVC S-I 4K",
            sq_frame_rate_fps=120,
            proxy_recording_on=False,
            card_tier="CFexpress Type A VPG200",
        )
        self.assertTrue(ok_no_proxy.allowed)

    def test_35_87a_standard_movie_all_5_tiers_covered(self) -> None:
        self.assertEqual(p379.FX3_ELF_TRANSFER_RATE_TIERS_MBPS, (100, 200, 400, 600, 1350))
        r100 = p379.simulate_87a_movieset_6codec_2400p_vpg_and_fx6_recfmt(
            operation="fx3_card_speed_5tier_vpg_and_g139_erratum",
            shoot_mode="Movie",
            file_format="XAVC S HD",
            bitrate_mbps=50,
            card_tier="SDHC/SDXC Class 10",
        )
        self.assertTrue(r100.allowed)
        self.assertEqual(r100.required_elf_transfer_tier_mbps, 100)

        r200 = p379.simulate_87a_movieset_6codec_2400p_vpg_and_fx6_recfmt(
            operation="fx3_card_speed_5tier_vpg_and_g139_erratum",
            shoot_mode="Movie",
            file_format="XAVC S 4K",
            bitrate_mbps=150,
            card_tier="SDXC U3/V30",
        )
        self.assertTrue(r200.allowed)
        self.assertEqual(r200.required_elf_transfer_tier_mbps, 200)

        r400 = p379.simulate_87a_movieset_6codec_2400p_vpg_and_fx6_recfmt(
            operation="fx3_card_speed_5tier_vpg_and_g139_erratum",
            shoot_mode="Movie",
            file_format="XAVC HS 4K",
            bitrate_mbps=280,
            card_tier="SDXC V60",
        )
        self.assertTrue(r400.allowed)
        self.assertEqual(r400.required_elf_transfer_tier_mbps, 400)

        r600 = p379.simulate_87a_movieset_6codec_2400p_vpg_and_fx6_recfmt(
            operation="fx3_card_speed_5tier_vpg_and_g139_erratum",
            shoot_mode="Movie",
            file_format="XAVC S-I 4K",
            bitrate_mbps=600,
            card_tier="SDXC V90",
        )
        self.assertTrue(r600.allowed)
        self.assertEqual(r600.required_elf_transfer_tier_mbps, 600)

    def test_36_87a_fx6_xavci_class300_valid_and_class480_blocked(self) -> None:
        ok = p379.simulate_87a_movieset_6codec_2400p_vpg_and_fx6_recfmt(
            operation="fx6_project_rec_format_and_dormant_class480_xavcl25",
            body_model=p379.BODY_MODEL_FX6,
            fx6_codec="XAVC-I",
            fx6_video_format="4096x2160",
            fx6_bitrate_mbps=600,
        )
        self.assertTrue(ok.allowed)
        self.assertEqual(ok.fx6_xavci_class, "Class300")

        bad = p379.simulate_87a_movieset_6codec_2400p_vpg_and_fx6_recfmt(
            operation="fx6_project_rec_format_and_dormant_class480_xavcl25",
            body_model=p379.BODY_MODEL_FX6,
            fx6_codec="XAVC-I",
            fx6_class_or_variant="Class480",
        )
        self.assertFalse(bad.allowed)
        self.assertEqual(bad.errno, p379.EOPNOTSUPP_ERRNO)
        self.assertTrue(bad.fx6_dormant_format_blocked)

    def test_37_87a_fx6_raw_and_raw_hdmi_codecs_valid(self) -> None:
        for codec in ("RAW & XAVC-I", "RAW(HDMI) & XAVC-I"):
            res = p379.simulate_87a_movieset_6codec_2400p_vpg_and_fx6_recfmt(
                operation="fx6_project_rec_format_and_dormant_class480_xavcl25",
                body_model=p379.BODY_MODEL_FX6,
                fx6_codec=codec,
                fx6_video_format="4096x2160",
                fx6_bitrate_mbps=600,
            )
            self.assertTrue(res.allowed)

    def test_38_87a_fx6_xavcl_qfhd_hd_valid_and_dci4k_blocked(self) -> None:
        for fmt, br in (("3840x2160", 150), ("3840x2160", 100), ("1920x1080", 50), ("1920x1080", 35)):
            ok = p379.simulate_87a_movieset_6codec_2400p_vpg_and_fx6_recfmt(
                operation="fx6_project_rec_format_and_dormant_class480_xavcl25",
                body_model=p379.BODY_MODEL_FX6,
                fx6_codec="XAVC-L",
                fx6_video_format=fmt,
                fx6_bitrate_mbps=br,
            )
            self.assertTrue(ok.allowed)

        bad_dci = p379.simulate_87a_movieset_6codec_2400p_vpg_and_fx6_recfmt(
            operation="fx6_project_rec_format_and_dormant_class480_xavcl25",
            body_model=p379.BODY_MODEL_FX6,
            fx6_codec="XAVC-L",
            fx6_video_format="4096x2160",
            fx6_bitrate_mbps=150,
        )
        self.assertFalse(bad_dci.allowed)
        self.assertEqual(bad_dci.errno, p379.EOPNOTSUPP_ERRNO)

    def test_39_87a_fx6_dormant_xavcl25_blocked(self) -> None:
        bad1 = p379.simulate_87a_movieset_6codec_2400p_vpg_and_fx6_recfmt(
            operation="fx6_project_rec_format_and_dormant_class480_xavcl25",
            body_model=p379.BODY_MODEL_FX6,
            fx6_codec="XAVC-L",
            fx6_video_format="1920x1080",
            fx6_bitrate_mbps=25,
        )
        self.assertFalse(bad1.allowed)
        self.assertEqual(bad1.errno, p379.EOPNOTSUPP_ERRNO)
        self.assertTrue(bad1.fx6_dormant_format_blocked)

        bad2 = p379.simulate_87a_movieset_6codec_2400p_vpg_and_fx6_recfmt(
            operation="fx6_project_rec_format_and_dormant_class480_xavcl25",
            body_model=p379.BODY_MODEL_FX6,
            fx6_codec="XAVC-L25",
        )
        self.assertFalse(bad2.allowed)
        self.assertEqual(bad2.errno, p379.EOPNOTSUPP_ERRNO)

    def test_40_87a_fx6_xavci_over_600m_rejected(self) -> None:
        bad = p379.simulate_87a_movieset_6codec_2400p_vpg_and_fx6_recfmt(
            operation="fx6_project_rec_format_and_dormant_class480_xavcl25",
            body_model=p379.BODY_MODEL_FX6,
            fx6_codec="XAVC-I",
            fx6_bitrate_mbps=960,
        )
        self.assertFalse(bad.allowed)
        self.assertEqual(bad.errno, p379.EOPNOTSUPP_ERRNO)

    def test_41_87a_invalid_inputs_raise_or_einval(self) -> None:
        with self.assertRaises(p379.Stage87Phase379Error):
            p379.simulate_87a_movieset_6codec_2400p_vpg_and_fx6_recfmt(operation="bogus")
        with self.assertRaises(p379.Stage87Phase379Error):
            p379.simulate_87a_movieset_6codec_2400p_vpg_and_fx6_recfmt(
                operation="fx3_file_format_6codec_and_dormant_8k", body_model="FX9"
            )
        with self.assertRaises(p379.Stage87Phase379Error):
            p379.simulate_87a_movieset_6codec_2400p_vpg_and_fx6_recfmt(
                operation="fx3_file_format_6codec_and_dormant_8k", shoot_mode="Playback"
            )
        bad_card = p379.simulate_87a_movieset_6codec_2400p_vpg_and_fx6_recfmt(
            operation="fx3_card_speed_5tier_vpg_and_g139_erratum", card_tier="Floppy"
        )
        self.assertEqual(bad_card.errno, p379.EINVAL_ERRNO)

    def test_42_87a_orchestrator_metrics_alignment(self) -> None:
        rep = p379.run_phase379_realhw_movieset_vpg_awbprio_touchpad_screenreader_version_coemulation(
            work_root=None
        )
        s = rep["submodel_87a_movieset_6codec_2400p_vpg_fx6_recfmt"]
        self.assertTrue(s["passed"])
        self.assertEqual(s["fx3_codecs_count"], 6)
        self.assertEqual(s["fx3_elf_transfer_tiers_count"], 5)
        self.assertEqual(s["fx3_vpg400_proxy_threshold_mbps"], 1350)
        self.assertEqual(s["fx3_dormant_8k_exposed_events"], 0)
        self.assertTrue(s["fx3_g139_card_speed_erratum_reconciled"])
        self.assertEqual(s["fx6_dormant_class480_xavcl25_exposed_events"], 0)

    # =========================================================================
    # Tests 43..62: Sub-Model 87B — AWB Priority, Shutter Lock, C.Temp, FX6 ATW
    # =========================================================================

    def test_43_87b_priority_set_in_awb_active_in_still_movie_and_flexible_iso(self) -> None:
        for mode in ("Still", "Movie"):
            for log_m in ("Off", "Flexible ISO"):
                for prio in ("Standard", "Ambience", "White"):
                    res = p379.simulate_87b_awb_priority_shutter_lock_ctemp_and_fx6_atw(
                        operation="fx3_priority_set_in_awb_and_cine_ei",
                        shoot_mode=mode,
                        log_shooting_mode=log_m,
                        wb_mode="Auto",
                        priority_set_in_awb=prio,
                    )
                    self.assertTrue(res.allowed)
                    self.assertTrue(res.priority_effective)

    def test_44_87b_priority_set_in_awb_can_be_reset_to_standard(self) -> None:
        res = p379.simulate_87b_awb_priority_shutter_lock_ctemp_and_fx6_atw(
            operation="fx3_priority_set_in_awb_and_cine_ei",
            priority_set_in_awb="Ambience",
            camera_settings_reset_triggered=True,
        )
        self.assertTrue(res.allowed)
        self.assertEqual(res.priority_set_in_awb, "Standard")
        self.assertTrue(res.priority_can_be_reset)

    def test_45_87b_cine_ei_and_quick_disable_auto_and_underwater_auto(self) -> None:
        for log_m in ("Cine EI", "Cine EI Quick"):
            for wb in ("Auto", "Underwater Auto"):
                res = p379.simulate_87b_awb_priority_shutter_lock_ctemp_and_fx6_atw(
                    operation="fx3_priority_set_in_awb_and_cine_ei",
                    log_shooting_mode=log_m,
                    wb_mode=wb,
                )
                self.assertFalse(res.allowed)
                self.assertEqual(res.errno, p379.EOPNOTSUPP_ERRNO)
                self.assertFalse(res.priority_effective)

    def test_46_87b_cine_ei_preset_wb_leaves_priority_inactive(self) -> None:
        res = p379.simulate_87b_awb_priority_shutter_lock_ctemp_and_fx6_atw(
            operation="fx3_priority_set_in_awb_and_cine_ei",
            log_shooting_mode="Cine EI",
            wb_mode="Daylight",
            priority_set_in_awb="White",
        )
        self.assertTrue(res.allowed)
        self.assertFalse(res.priority_effective)

    def test_47_87b_shutter_awb_lock_strictly_still_only(self) -> None:
        for m in ("Off", "Shutter Half Press", "Cont. Shooting"):
            ok = p379.simulate_87b_awb_priority_shutter_lock_ctemp_and_fx6_atw(
                operation="fx3_shutter_awb_lock_still_only_and_reset_resistance",
                shoot_mode="Still",
                shutter_awb_lock=m,
            )
            self.assertTrue(ok.allowed)

        for bad_mode in ("Movie", "S&Q"):
            blk = p379.simulate_87b_awb_priority_shutter_lock_ctemp_and_fx6_atw(
                operation="fx3_shutter_awb_lock_still_only_and_reset_resistance",
                shoot_mode=bad_mode,
                shutter_awb_lock="Shutter Half Press",
            )
            self.assertFalse(blk.allowed)
            self.assertEqual(blk.errno, p379.EOPNOTSUPP_ERRNO)
            self.assertIn("AWB Lock Hold", blk.movie_awb_lock_alternative)

    def test_48_87b_shutter_awb_lock_resists_cam_reset_resets_only_on_init(self) -> None:
        rst = p379.simulate_87b_awb_priority_shutter_lock_ctemp_and_fx6_atw(
            operation="fx3_shutter_awb_lock_still_only_and_reset_resistance",
            shoot_mode="Still",
            shutter_awb_lock="Shutter Half Press",
            camera_settings_reset_triggered=True,
        )
        self.assertTrue(rst.allowed)
        self.assertEqual(rst.shutter_awb_lock, "Shutter Half Press")
        self.assertTrue(rst.shutter_awb_lock_survived_cam_reset)

        ini = p379.simulate_87b_awb_priority_shutter_lock_ctemp_and_fx6_atw(
            operation="fx3_shutter_awb_lock_still_only_and_reset_resistance",
            shoot_mode="Still",
            shutter_awb_lock="Shutter Half Press",
            initialize_triggered=True,
        )
        self.assertTrue(ini.allowed)
        self.assertEqual(ini.shutter_awb_lock, "Off")
        self.assertTrue(ini.shutter_awb_lock_reset_on_init)

    def test_49_87b_ctemp_2500k_to_9900k_exact_75_steps(self) -> None:
        self.assertEqual(p379.FX3_CTEMP_STEPS_COUNT, 75)
        for k in (2500, 3200, 5600, 9900):
            res = p379.simulate_87b_awb_priority_shutter_lock_ctemp_and_fx6_atw(
                operation="fx3_ctemp_filter_grid_and_custom_wb_log_warning",
                ctemp_kelvin=k,
            )
            self.assertTrue(res.allowed)

        for bad_k in (2400, 5550, 10000):
            bad = p379.simulate_87b_awb_priority_shutter_lock_ctemp_and_fx6_atw(
                operation="fx3_ctemp_filter_grid_and_custom_wb_log_warning",
                ctemp_kelvin=bad_k,
            )
            self.assertFalse(bad.allowed)
            self.assertEqual(bad.errno, p379.EINVAL_ERRNO)

    def test_50_87b_ab_filter_29_steps_and_gm_filter_57_steps(self) -> None:
        self.assertEqual(p379.FX3_AB_FILTER_STEPS_COUNT, 29)
        self.assertEqual(p379.FX3_GM_FILTER_STEPS_COUNT, 57)
        ok = p379.simulate_87b_awb_priority_shutter_lock_ctemp_and_fx6_atw(
            operation="fx3_ctemp_filter_grid_and_custom_wb_log_warning",
            ab_filter=-6.5,
            gm_filter=6.75,
        )
        self.assertTrue(ok.allowed)

        bad_ab = p379.simulate_87b_awb_priority_shutter_lock_ctemp_and_fx6_atw(
            operation="fx3_ctemp_filter_grid_and_custom_wb_log_warning",
            ab_filter=0.25,
        )
        self.assertEqual(bad_ab.errno, p379.EINVAL_ERRNO)

        bad_gm = p379.simulate_87b_awb_priority_shutter_lock_ctemp_and_fx6_atw(
            operation="fx3_ctemp_filter_grid_and_custom_wb_log_warning",
            gm_filter=0.1,
        )
        self.assertEqual(bad_gm.errno, p379.EINVAL_ERRNO)

    def test_51_87b_custom_wb_capture_warns_under_log_shooting(self) -> None:
        warn = p379.simulate_87b_awb_priority_shutter_lock_ctemp_and_fx6_atw(
            operation="fx3_ctemp_filter_grid_and_custom_wb_log_warning",
            log_shooting_mode="Flexible ISO",
            custom_wb_capture_requested=True,
        )
        self.assertTrue(warn.allowed)
        self.assertTrue(warn.custom_wb_log_warning)

        no_warn = p379.simulate_87b_awb_priority_shutter_lock_ctemp_and_fx6_atw(
            operation="fx3_ctemp_filter_grid_and_custom_wb_log_warning",
            log_shooting_mode="Off",
            custom_wb_capture_requested=True,
        )
        self.assertFalse(no_warn.custom_wb_log_warning)

    def test_52_87b_fx6_physical_whtbal_switch_and_custom_presets(self) -> None:
        for k in (3200, 4300, 5600, 6300):
            res = p379.simulate_87b_awb_priority_shutter_lock_ctemp_and_fx6_atw(
                operation="fx6_physical_whtbal_preset_atw_tint_rbgain_shockless",
                body_model=p379.BODY_MODEL_FX6,
                fx6_wht_bal_switch="PRESET",
                fx6_shooting_mode="Custom",
                fx6_preset_kelvin=k,
            )
            self.assertTrue(res.allowed)

    def test_53_87b_fx6_cine_ei_presets_3200_4300_5500_reject_5600_6300(self) -> None:
        for k in (3200, 4300, 5500):
            ok = p379.simulate_87b_awb_priority_shutter_lock_ctemp_and_fx6_atw(
                operation="fx6_physical_whtbal_preset_atw_tint_rbgain_shockless",
                body_model=p379.BODY_MODEL_FX6,
                fx6_wht_bal_switch="PRESET",
                fx6_shooting_mode="Cine EI",
                fx6_preset_kelvin=k,
            )
            self.assertTrue(ok.allowed)

        for bad_k in (5600, 6300):
            bad = p379.simulate_87b_awb_priority_shutter_lock_ctemp_and_fx6_atw(
                operation="fx6_physical_whtbal_preset_atw_tint_rbgain_shockless",
                body_model=p379.BODY_MODEL_FX6,
                fx6_wht_bal_switch="PRESET",
                fx6_shooting_mode="Cine EI",
                fx6_preset_kelvin=bad_k,
            )
            self.assertFalse(bad.allowed)
            self.assertEqual(bad.errno, p379.EINVAL_ERRNO)

    def test_54_87b_fx6_atw_2000k_15000k_speed_1_5_and_hold(self) -> None:
        for k in (2000, 5600, 15000):
            for spd in (1, 3, 5):
                ok = p379.simulate_87b_awb_priority_shutter_lock_ctemp_and_fx6_atw(
                    operation="fx6_physical_whtbal_preset_atw_tint_rbgain_shockless",
                    body_model=p379.BODY_MODEL_FX6,
                    fx6_wht_bal_switch="B",
                    fx6_shooting_mode="Custom",
                    fx6_atw_enabled=True,
                    fx6_atw_kelvin=k,
                    fx6_atw_speed=spd,
                    fx6_atw_hold_active=True,
                )
                self.assertTrue(ok.allowed)

        bad_k = p379.simulate_87b_awb_priority_shutter_lock_ctemp_and_fx6_atw(
            operation="fx6_physical_whtbal_preset_atw_tint_rbgain_shockless",
            body_model=p379.BODY_MODEL_FX6,
            fx6_atw_enabled=True,
            fx6_atw_kelvin=16000,
        )
        self.assertEqual(bad_k.errno, p379.EINVAL_ERRNO)

        bad_s = p379.simulate_87b_awb_priority_shutter_lock_ctemp_and_fx6_atw(
            operation="fx6_physical_whtbal_preset_atw_tint_rbgain_shockless",
            body_model=p379.BODY_MODEL_FX6,
            fx6_atw_enabled=True,
            fx6_atw_speed=6,
        )
        self.assertEqual(bad_s.errno, p379.EINVAL_ERRNO)

    def test_55_87b_fx6_atw_blocked_in_cine_ei(self) -> None:
        bad = p379.simulate_87b_awb_priority_shutter_lock_ctemp_and_fx6_atw(
            operation="fx6_physical_whtbal_preset_atw_tint_rbgain_shockless",
            body_model=p379.BODY_MODEL_FX6,
            fx6_shooting_mode="Cine EI",
            fx6_atw_enabled=True,
        )
        self.assertFalse(bad.allowed)
        self.assertEqual(bad.errno, p379.EOPNOTSUPP_ERRNO)

    def test_56_87b_fx6_tint_and_rb_gain_bounds(self) -> None:
        bad_t = p379.simulate_87b_awb_priority_shutter_lock_ctemp_and_fx6_atw(
            operation="fx6_physical_whtbal_preset_atw_tint_rbgain_shockless",
            body_model=p379.BODY_MODEL_FX6,
            fx6_tint=100,
        )
        self.assertEqual(bad_t.errno, p379.EINVAL_ERRNO)

        bad_g = p379.simulate_87b_awb_priority_shutter_lock_ctemp_and_fx6_atw(
            operation="fx6_physical_whtbal_preset_atw_tint_rbgain_shockless",
            body_model=p379.BODY_MODEL_FX6,
            fx6_r_gain=100.0,
        )
        self.assertEqual(bad_g.errno, p379.EINVAL_ERRNO)

    def test_57_87b_fx6_shockless_white_off_1_2_3(self) -> None:
        for sw in ("Off", "1", "2", "3"):
            ok = p379.simulate_87b_awb_priority_shutter_lock_ctemp_and_fx6_atw(
                operation="fx6_physical_whtbal_preset_atw_tint_rbgain_shockless",
                body_model=p379.BODY_MODEL_FX6,
                fx6_wht_bal_switch="A",
                fx6_shockless_white=sw,
            )
            self.assertTrue(ok.allowed)

        bad = p379.simulate_87b_awb_priority_shutter_lock_ctemp_and_fx6_atw(
            operation="fx6_physical_whtbal_preset_atw_tint_rbgain_shockless",
            body_model=p379.BODY_MODEL_FX6,
            fx6_shockless_white="4",
        )
        self.assertEqual(bad.errno, p379.EINVAL_ERRNO)

    def test_58_87b_invalid_enums_return_einval(self) -> None:
        r1 = p379.simulate_87b_awb_priority_shutter_lock_ctemp_and_fx6_atw(
            operation="fx3_priority_set_in_awb_and_cine_ei",
            priority_set_in_awb="Warm",
        )
        self.assertEqual(r1.errno, p379.EINVAL_ERRNO)
        r2 = p379.simulate_87b_awb_priority_shutter_lock_ctemp_and_fx6_atw(
            operation="fx3_shutter_awb_lock_still_only_and_reset_resistance",
            shutter_awb_lock="Always",
        )
        self.assertEqual(r2.errno, p379.EINVAL_ERRNO)
        r3 = p379.simulate_87b_awb_priority_shutter_lock_ctemp_and_fx6_atw(
            operation="fx6_physical_whtbal_preset_atw_tint_rbgain_shockless",
            body_model=p379.BODY_MODEL_FX6,
            fx6_wht_bal_switch="C",
        )
        self.assertEqual(r3.errno, p379.EINVAL_ERRNO)

    def test_59_87b_invalid_operation_or_body_raises(self) -> None:
        with self.assertRaises(p379.Stage87Phase379Error):
            p379.simulate_87b_awb_priority_shutter_lock_ctemp_and_fx6_atw(operation="bad")
        with self.assertRaises(p379.Stage87Phase379Error):
            p379.simulate_87b_awb_priority_shutter_lock_ctemp_and_fx6_atw(
                operation="fx3_priority_set_in_awb_and_cine_ei", body_model="FX9"
            )
        with self.assertRaises(p379.Stage87Phase379Error):
            p379.simulate_87b_awb_priority_shutter_lock_ctemp_and_fx6_atw(
                operation="fx3_priority_set_in_awb_and_cine_ei", shoot_mode="Playback"
            )

    def test_60_87b_non_auto_wb_in_normal_mode_leaves_priority_idle(self) -> None:
        res = p379.simulate_87b_awb_priority_shutter_lock_ctemp_and_fx6_atw(
            operation="fx3_priority_set_in_awb_and_cine_ei",
            log_shooting_mode="Off",
            wb_mode="Cloudy",
            priority_set_in_awb="White",
        )
        self.assertTrue(res.allowed)
        self.assertFalse(res.priority_effective)

    def test_61_87b_ctemp_boundary_ab_gm_extremes_pass(self) -> None:
        res = p379.simulate_87b_awb_priority_shutter_lock_ctemp_and_fx6_atw(
            operation="fx3_ctemp_filter_grid_and_custom_wb_log_warning",
            ctemp_kelvin=2500,
            ab_filter=7.0,
            gm_filter=-7.0,
        )
        self.assertTrue(res.allowed)

    def test_62_87b_orchestrator_metrics_alignment(self) -> None:
        rep = p379.run_phase379_realhw_movieset_vpg_awbprio_touchpad_screenreader_version_coemulation(
            work_root=None
        )
        s = rep["submodel_87b_awb_priority_shutter_lock_ctemp_fx6_atw"]
        self.assertTrue(s["passed"])
        self.assertEqual(s["fx3_awb_priority_modes_count"], 3)
        self.assertEqual(s["fx3_ctemp_steps_count"], 75)
        self.assertEqual(s["fx3_ab_filter_steps_count"], 29)
        self.assertEqual(s["fx3_gm_filter_steps_count"], 57)
        self.assertEqual(s["fx3_shutter_awb_lock_movie_bypass_events"], 0)
        self.assertEqual(s["fx6_atw_speed_steps_count"], 5)

    # =========================================================================
    # Tests 63..82: Sub-Model 87C — Touch 4-Item, Dormant Pad & G109 Erratum
    # =========================================================================

    def test_63_87c_fx3_touch_operation_exact_4_exposed_items(self) -> None:
        self.assertEqual(len(p379.FX3_TOUCH_EXPOSED_4_ITEMS), 4)
        self.assertFalse(p379.FX3_HAS_BUILTIN_EVF)
        res = p379.simulate_87c_touch_op_dormant_pad_focus_peaking_g109_and_fx6(
            operation="fx3_touch_operation_4item_and_dormant_evf_pad",
            touch_operation="On",
            touch_sensitivity="Sensitive",
            touch_func_in_shooting="Touch Focus",
            swipe_up="Open the Fn Menu",
        )
        self.assertTrue(res.allowed)

    def test_64_87c_fx3_touch_4_items_resist_cam_reset_and_reset_on_init(self) -> None:
        rst = p379.simulate_87c_touch_op_dormant_pad_focus_peaking_g109_and_fx6(
            operation="fx3_touch_operation_4item_and_dormant_evf_pad",
            touch_operation="Off",
            touch_sensitivity="Sensitive",
            touch_func_in_shooting="Off",
            swipe_up="Off",
            camera_settings_reset_triggered=True,
        )
        self.assertTrue(rst.allowed)
        self.assertTrue(rst.touch_4items_survived_cam_reset)
        self.assertEqual(rst.touch_operation, "Off")
        self.assertEqual(rst.swipe_up, "Off")

        ini = p379.simulate_87c_touch_op_dormant_pad_focus_peaking_g109_and_fx6(
            operation="fx3_touch_operation_4item_and_dormant_evf_pad",
            touch_operation="Off",
            touch_sensitivity="Sensitive",
            touch_func_in_shooting="Off",
            swipe_up="Off",
            initialize_triggered=True,
        )
        self.assertTrue(ini.allowed)
        self.assertEqual(ini.touch_operation, "On")
        self.assertEqual(ini.touch_sensitivity, "Standard")
        self.assertEqual(ini.touch_func_in_shooting, "Touch Tracking")
        self.assertEqual(ini.swipe_up, "Open the Fn Menu")

    def test_65_87c_dormant_evf_touch_panel_pad_items_all_blocked(self) -> None:
        for item in p379.FX3_DORMANT_EVF_TOUCH_ITEMS:
            res = p379.simulate_87c_touch_op_dormant_pad_focus_peaking_g109_and_fx6(
                operation="fx3_touch_operation_4item_and_dormant_evf_pad",
                dormant_evf_touch_item=item,
            )
            self.assertFalse(res.allowed, item)
            self.assertEqual(res.errno, p379.EOPNOTSUPP_ERRNO)
            self.assertTrue(res.dormant_evf_touch_blocked)

    def test_66_87c_dormant_touch_shutter_in_touch_func_blocked(self) -> None:
        res = p379.simulate_87c_touch_op_dormant_pad_focus_peaking_g109_and_fx6(
            operation="fx3_touch_operation_4item_and_dormant_evf_pad",
            touch_func_in_shooting="Touch Shutter",
        )
        self.assertFalse(res.allowed)
        self.assertEqual(res.errno, p379.EOPNOTSUPP_ERRNO)
        self.assertTrue(res.dormant_evf_touch_blocked)

    def test_67_87c_g109_all_7_focus_assistant_and_peaking_items_resist_cam_reset(self) -> None:
        self.assertEqual(len(p379.FX3_FOCUS_PEAKING_RESET_RESISTANT_7_ITEMS), 7)
        for item in p379.FX3_FOCUS_PEAKING_RESET_RESISTANT_7_ITEMS:
            res = p379.simulate_87c_touch_op_dormant_pad_focus_peaking_g109_and_fx6(
                operation="fx3_focus_assistant_and_peaking_g109_reset_resistance",
                focus_assistant_item=item,
                peaking_display="On",
                peaking_level="High",
                peaking_color="Yellow",
                camera_settings_reset_triggered=True,
            )
            self.assertTrue(res.allowed, item)
            self.assertTrue(res.focus_peaking_7items_survived_cam_reset)
            self.assertTrue(res.g109_erratum_reconciled)
            self.assertEqual(res.peaking_display, "On")

    def test_68_87c_g109_all_7_focus_assistant_and_peaking_items_reset_on_init(self) -> None:
        res = p379.simulate_87c_touch_op_dormant_pad_focus_peaking_g109_and_fx6(
            operation="fx3_focus_assistant_and_peaking_g109_reset_resistance",
            peaking_display="On",
            peaking_level="Low",
            peaking_color="Blue",
            initialize_triggered=True,
        )
        self.assertTrue(res.allowed)
        self.assertTrue(res.focus_peaking_7items_reset_on_init)
        self.assertEqual(res.peaking_display, "Off")
        self.assertEqual(res.peaking_level, "Mid")
        self.assertEqual(res.peaking_color, "White")

    def test_69_87c_af_in_focus_mag_allowed_in_still_afs(self) -> None:
        res = p379.simulate_87c_touch_op_dormant_pad_focus_peaking_g109_and_fx6(
            operation="fx3_focus_assistant_and_peaking_g109_reset_resistance",
            shoot_mode="Still",
            focus_mode="AF-S",
            exposure_mode="M",
            drive_mode="Single Shooting",
            mount_adaptor_attached=False,
            af_in_focus_mag_requested=True,
        )
        self.assertTrue(res.allowed)
        self.assertTrue(res.af_in_focus_mag_active)

    def test_70_87c_af_in_focus_mag_blocked_in_movie_and_sq(self) -> None:
        for mode in ("Movie", "S&Q"):
            res = p379.simulate_87c_touch_op_dormant_pad_focus_peaking_g109_and_fx6(
                operation="fx3_focus_assistant_and_peaking_g109_reset_resistance",
                shoot_mode=mode,
                af_in_focus_mag_requested=True,
            )
            self.assertFalse(res.allowed)
            self.assertEqual(res.errno, p379.EOPNOTSUPP_ERRNO)

    def test_71_87c_af_in_focus_mag_blocked_in_afc(self) -> None:
        res = p379.simulate_87c_touch_op_dormant_pad_focus_peaking_g109_and_fx6(
            operation="fx3_focus_assistant_and_peaking_g109_reset_resistance",
            shoot_mode="Still",
            focus_mode="AF-C",
            af_in_focus_mag_requested=True,
        )
        self.assertFalse(res.allowed)
        self.assertEqual(res.errno, p379.EOPNOTSUPP_ERRNO)

    def test_72_87c_af_in_focus_mag_blocked_in_non_pasm_afa(self) -> None:
        res = p379.simulate_87c_touch_op_dormant_pad_focus_peaking_g109_and_fx6(
            operation="fx3_focus_assistant_and_peaking_g109_reset_resistance",
            shoot_mode="Still",
            focus_mode="AF-A",
            exposure_mode="iAuto",
            af_in_focus_mag_requested=True,
        )
        self.assertFalse(res.allowed)
        self.assertEqual(res.errno, p379.EOPNOTSUPP_ERRNO)

    def test_73_87c_af_in_focus_mag_blocked_in_cont_shooting(self) -> None:
        res = p379.simulate_87c_touch_op_dormant_pad_focus_peaking_g109_and_fx6(
            operation="fx3_focus_assistant_and_peaking_g109_reset_resistance",
            shoot_mode="Still",
            focus_mode="AF-S",
            drive_mode="Cont. Shooting",
            af_in_focus_mag_requested=True,
        )
        self.assertFalse(res.allowed)
        self.assertEqual(res.errno, p379.EOPNOTSUPP_ERRNO)

    def test_74_87c_af_in_focus_mag_blocked_with_mount_adaptor(self) -> None:
        res = p379.simulate_87c_touch_op_dormant_pad_focus_peaking_g109_and_fx6(
            operation="fx3_focus_assistant_and_peaking_g109_reset_resistance",
            shoot_mode="Still",
            focus_mode="AF-S",
            mount_adaptor_attached=True,
            af_in_focus_mag_requested=True,
        )
        self.assertFalse(res.allowed)
        self.assertEqual(res.errno, p379.EOPNOTSUPP_ERRNO)

    def test_75_87c_fx3_peaking_zero_hdmi_output(self) -> None:
        res = p379.simulate_87c_touch_op_dormant_pad_focus_peaking_g109_and_fx6(
            operation="fx3_focus_assistant_and_peaking_g109_reset_resistance",
            peaking_display="On",
            hdmi_peaking_requested=True,
        )
        self.assertFalse(res.allowed)
        self.assertEqual(res.errno, p379.EOPNOTSUPP_ERRNO)
        self.assertEqual(res.hdmi_peaking_leaked_pixels, 0)

    def test_76_87c_fx6_peaking_strictly_3_items_and_4_colors(self) -> None:
        self.assertEqual(len(p379.FX6_PEAKING_3_ITEMS), 3)
        for col in ("B&W", "Red", "Yellow", "Blue"):
            res = p379.simulate_87c_touch_op_dormant_pad_focus_peaking_g109_and_fx6(
                operation="fx6_touch_mf_focus_mag_and_3item_peaking_dormant_block",
                body_model=p379.BODY_MODEL_FX6,
                fx6_peaking_color=col,
            )
            self.assertTrue(res.allowed)
            self.assertEqual(res.fx6_peaking_elf_items_count, 3)

    def test_77_87c_fx6_dormant_peaking_type_and_frequency_blocked(self) -> None:
        for item in p379.FX6_DORMANT_PEAKING_ITEMS:
            res = p379.simulate_87c_touch_op_dormant_pad_focus_peaking_g109_and_fx6(
                operation="fx6_touch_mf_focus_mag_and_3item_peaking_dormant_block",
                body_model=p379.BODY_MODEL_FX6,
                fx6_dormant_peaking_item=item,
            )
            self.assertFalse(res.allowed, item)
            self.assertEqual(res.errno, p379.EOPNOTSUPP_ERRNO)
            self.assertTrue(res.fx6_dormant_peaking_blocked)

    def test_78_87c_fx6_touch_mf_options_valid(self) -> None:
        for mode in ("Tracking AF", "Spot Focus"):
            res = p379.simulate_87c_touch_op_dormant_pad_focus_peaking_g109_and_fx6(
                operation="fx6_touch_mf_focus_mag_and_3item_peaking_dormant_block",
                body_model=p379.BODY_MODEL_FX6,
                fx6_touch_mf_mode=mode,
            )
            self.assertTrue(res.allowed)

    def test_79_87c_fx3_focus_mag_constants_movie_vs_still_split(self) -> None:
        self.assertEqual(p379.FX3_INIT_FOCUS_MAG_MOVIE_OPTIONS, ("x1.0", "x4.0"))
        self.assertEqual(p379.FX3_INIT_FOCUS_MAG_STILL_FF_OPTIONS, ("x1.0", "x2.1"))
        self.assertEqual(p379.FX3_INIT_FOCUS_MAG_STILL_APSC_OPTIONS, ("x1.0", "x1.5"))

    def test_80_87c_invalid_enums_return_einval(self) -> None:
        r1 = p379.simulate_87c_touch_op_dormant_pad_focus_peaking_g109_and_fx6(
            operation="fx3_touch_operation_4item_and_dormant_evf_pad",
            touch_operation="Always",
        )
        self.assertEqual(r1.errno, p379.EINVAL_ERRNO)
        r2 = p379.simulate_87c_touch_op_dormant_pad_focus_peaking_g109_and_fx6(
            operation="fx3_focus_assistant_and_peaking_g109_reset_resistance",
            peaking_color="Green",
        )
        self.assertEqual(r2.errno, p379.EINVAL_ERRNO)
        r3 = p379.simulate_87c_touch_op_dormant_pad_focus_peaking_g109_and_fx6(
            operation="fx6_touch_mf_focus_mag_and_3item_peaking_dormant_block",
            body_model=p379.BODY_MODEL_FX6,
            fx6_peaking_color="White",
        )
        self.assertEqual(r3.errno, p379.EINVAL_ERRNO)

    def test_81_87c_invalid_operation_or_body_raises(self) -> None:
        with self.assertRaises(p379.Stage87Phase379Error):
            p379.simulate_87c_touch_op_dormant_pad_focus_peaking_g109_and_fx6(operation="bad")
        with self.assertRaises(p379.Stage87Phase379Error):
            p379.simulate_87c_touch_op_dormant_pad_focus_peaking_g109_and_fx6(
                operation="fx3_touch_operation_4item_and_dormant_evf_pad", body_model="FX9"
            )

    def test_82_87c_orchestrator_metrics_alignment(self) -> None:
        rep = p379.run_phase379_realhw_movieset_vpg_awbprio_touchpad_screenreader_version_coemulation(
            work_root=None
        )
        s = rep["submodel_87c_touch_pad_focus_peaking_g109_fx6"]
        self.assertTrue(s["passed"])
        self.assertFalse(s["fx3_has_builtin_evf"])
        self.assertEqual(s["fx3_touch_exposed_items_count"], 4)
        self.assertEqual(s["fx3_dormant_evf_touch_pad_exposed_events"], 0)
        self.assertEqual(s["fx3_focus_peaking_reset_resistant_items_count"], 7)
        self.assertTrue(s["fx3_g109_focus_peaking_reset_erratum_reconciled"])
        self.assertEqual(s["fx3_hdmi_peaking_leaked_pixels"], 0)
        self.assertEqual(s["fx6_peaking_elf_items_count"], 3)
        self.assertEqual(s["fx6_dormant_peaking_frequency_exposed_events"], 0)

    # =========================================================================
    # Tests 83..100: Sub-Model 87D — Screen Reader, 2-Slot Version (G104), EROFS
    # =========================================================================

    def test_83_87d_screen_reader_zero_ui_exposure_on_fx3_and_fx6(self) -> None:
        self.assertEqual(p379.FX3_SCREEN_READER_UI_EXPOSED_ITEMS, 0)
        self.assertEqual(p379.FX6_SCREEN_READER_UI_EXPOSED_ITEMS, 0)
        for model in (p379.BODY_MODEL_FX3, p379.BODY_MODEL_FX6):
            res = p379.simulate_87d_screen_reader_version_2slot_g104_and_erofs(
                operation="fx3_screen_reader_sku_gate_and_zero_hdmi_audio",
                body_model=model,
                sku_screen_reader_authorized=False,
            )
            self.assertFalse(res.allowed)
            self.assertEqual(res.errno, p379.EOPNOTSUPP_ERRNO)
            self.assertFalse(res.screen_reader_ui_exposed)

    def test_84_87d_screen_reader_authorized_sku_speeds_and_volumes(self) -> None:
        self.assertEqual(len(p379.FX3_SCREEN_READER_SPEEDS), 7)
        for spd in p379.FX3_SCREEN_READER_SPEEDS:
            res = p379.simulate_87d_screen_reader_version_2slot_g104_and_erofs(
                operation="fx3_screen_reader_sku_gate_and_zero_hdmi_audio",
                body_model=p379.BODY_MODEL_FX30_AUTH,
                sku_screen_reader_authorized=True,
                screen_reader_speed=spd,
                screen_reader_volume=15,
            )
            self.assertTrue(res.allowed)
            self.assertTrue(res.screen_reader_ui_exposed)
            self.assertEqual(res.screen_reader_hdmi_audio_links, 0)

    def test_85_87d_screen_reader_non_english_prompts_language_switch(self) -> None:
        res = p379.simulate_87d_screen_reader_version_2slot_g104_and_erofs(
            operation="fx3_screen_reader_sku_gate_and_zero_hdmi_audio",
            body_model=p379.BODY_MODEL_FX30_AUTH,
            sku_screen_reader_authorized=True,
            screen_reader_language="Simplified Chinese",
        )
        self.assertTrue(res.allowed)
        self.assertTrue(res.screen_reader_language_prompt)

    def test_86_87d_screen_reader_zero_hdmi_audio_link_blocked(self) -> None:
        res = p379.simulate_87d_screen_reader_version_2slot_g104_and_erofs(
            operation="fx3_screen_reader_sku_gate_and_zero_hdmi_audio",
            body_model=p379.BODY_MODEL_FX30_AUTH,
            sku_screen_reader_authorized=True,
            screen_reader_hdmi_audio_requested=True,
        )
        self.assertFalse(res.allowed)
        self.assertEqual(res.errno, p379.EOPNOTSUPP_ERRNO)
        self.assertEqual(res.screen_reader_hdmi_audio_links, 0)

    def test_87_87d_screen_reader_resists_cam_reset_resets_on_init(self) -> None:
        rst = p379.simulate_87d_screen_reader_version_2slot_g104_and_erofs(
            operation="fx3_screen_reader_sku_gate_and_zero_hdmi_audio",
            body_model=p379.BODY_MODEL_FX30_AUTH,
            sku_screen_reader_authorized=True,
            screen_reader_speed="FAST_4",
            screen_reader_volume=12,
            camera_settings_reset_triggered=True,
        )
        self.assertTrue(rst.allowed)
        self.assertTrue(rst.screen_reader_survived_cam_reset)
        self.assertEqual(rst.screen_reader_speed, "FAST_4")
        self.assertEqual(rst.screen_reader_volume, 12)

        ini = p379.simulate_87d_screen_reader_version_2slot_g104_and_erofs(
            operation="fx3_screen_reader_sku_gate_and_zero_hdmi_audio",
            body_model=p379.BODY_MODEL_FX30_AUTH,
            sku_screen_reader_authorized=True,
            screen_reader_speed="FAST_4",
            screen_reader_volume=12,
            initialize_triggered=True,
        )
        self.assertTrue(ini.allowed)
        self.assertEqual(ini.screen_reader_speed, "NORMAL")
        self.assertEqual(ini.screen_reader_volume, 7)

    def test_88_87d_g104_version_dialog_exactly_2_slots_body_and_lens(self) -> None:
        res = p379.simulate_87d_screen_reader_version_2slot_g104_and_erofs(
            operation="fx3_version_2slot_g104_erratum_and_airplane_dot",
            mount_adaptor_attached=True,
            airplane_mode_on=True,
        )
        self.assertTrue(res.allowed)
        self.assertEqual(res.version_slots, ("Body", "Lens"))
        self.assertEqual(res.version_slots_count, 2)
        self.assertTrue(res.mount_adaptor_shares_lens_slot)
        self.assertFalse(res.mi_shoe_version_displayed)
        self.assertTrue(res.g104_erratum_reconciled)

    def test_89_87d_g104_rejects_separate_3rd_mount_adaptor_slot(self) -> None:
        res = p379.simulate_87d_screen_reader_version_2slot_g104_and_erofs(
            operation="fx3_version_2slot_g104_erratum_and_airplane_dot",
            request_separate_mount_adaptor_slot=True,
        )
        self.assertFalse(res.allowed)
        self.assertEqual(res.errno, p379.EOPNOTSUPP_ERRNO)
        self.assertEqual(res.version_slots_count, 2)

    def test_90_87d_g104_rejects_mi_shoe_accessory_version(self) -> None:
        res = p379.simulate_87d_screen_reader_version_2slot_g104_and_erofs(
            operation="fx3_version_2slot_g104_erratum_and_airplane_dot",
            request_mi_shoe_version=True,
        )
        self.assertFalse(res.allowed)
        self.assertEqual(res.errno, p379.EOPNOTSUPP_ERRNO)
        self.assertFalse(res.mi_shoe_version_displayed)

    def test_91_87d_airplane_mode_silences_v600_online_update_dot_zero_rf(self) -> None:
        air_on = p379.simulate_87d_screen_reader_version_2slot_g104_and_erofs(
            operation="fx3_version_2slot_g104_erratum_and_airplane_dot",
            airplane_mode_on=True,
            online_newer_fw_available=True,
        )
        self.assertTrue(air_on.allowed)
        self.assertFalse(air_on.online_update_dot_shown)
        self.assertEqual(air_on.rf_tx_packets, 0)

        air_off = p379.simulate_87d_screen_reader_version_2slot_g104_and_erofs(
            operation="fx3_version_2slot_g104_erratum_and_airplane_dot",
            airplane_mode_on=False,
            online_newer_fw_available=True,
        )
        self.assertTrue(air_off.allowed)
        self.assertTrue(air_off.online_update_dot_shown)
        self.assertEqual(air_off.rf_tx_packets, 0)

    def test_92_87d_software_update_slot1_bodydata_hard_blocked_erofs(self) -> None:
        for sw_req, s1_req in ((True, False), (False, True), (True, True)):
            res = p379.simulate_87d_screen_reader_version_2slot_g104_and_erofs(
                operation="fx3_software_update_slot1_bodydata_erofs_firewall",
                software_update_execute_requested=sw_req,
                slot1_bodydata_write_requested=s1_req,
            )
            self.assertFalse(res.allowed)
            self.assertEqual(res.errno, p379.EROFS_ERRNO)
            self.assertTrue(res.software_update_blocked_erofs)
            self.assertFalse(res.slot1_bodydata_write_authorized)
            self.assertFalse(res.cross_model_flash_authorized)
            self.assertFalse(res.live_attach_authorized)
            self.assertEqual(res.slot1_writes, 0)
            self.assertEqual(res.slot1_sector_writes, 0)
            self.assertEqual(res.slot1_data_sector_writes, 0)

    def test_93_87d_software_update_readonly_precheck_and_51pct_battery_gate(self) -> None:
        ok = p379.simulate_87d_screen_reader_version_2slot_g104_and_erofs(
            operation="fx3_software_update_slot1_bodydata_erofs_firewall",
            battery_pct=51,
        )
        self.assertTrue(ok.allowed)
        self.assertEqual(ok.slot1_writes, 0)

        low = p379.simulate_87d_screen_reader_version_2slot_g104_and_erofs(
            operation="fx3_software_update_slot1_bodydata_erofs_firewall",
            battery_pct=50,
        )
        self.assertFalse(low.allowed)
        self.assertEqual(low.errno, p379.EAGAIN_ERRNO)

    def test_94_87d_fx6_maintenance_version_3_domains_readonly(self) -> None:
        res = p379.simulate_87d_screen_reader_version_2slot_g104_and_erofs(
            operation="fx6_screen_reader_dormant_and_version_up_slotb_ac",
            body_model=p379.BODY_MODEL_FX6,
        )
        self.assertTrue(res.allowed)
        self.assertEqual(res.fx6_version_domains, ("Body", "Lens", "Ext. Unit"))
        self.assertTrue(res.fx6_slot_b_and_ac_required)
        self.assertFalse(res.screen_reader_ui_exposed)

    def test_95_87d_fx6_version_up_requires_slot_b_and_ac_and_blocks_erofs(self) -> None:
        bad_slot = p379.simulate_87d_screen_reader_version_2slot_g104_and_erofs(
            operation="fx6_screen_reader_dormant_and_version_up_slotb_ac",
            body_model=p379.BODY_MODEL_FX6,
            fx6_update_slot="Slot A",
            fx6_ac_adapter_connected=True,
            fx6_version_up_execute_requested=True,
        )
        self.assertEqual(bad_slot.errno, p379.EINVAL_ERRNO)

        bad_ac = p379.simulate_87d_screen_reader_version_2slot_g104_and_erofs(
            operation="fx6_screen_reader_dormant_and_version_up_slotb_ac",
            body_model=p379.BODY_MODEL_FX6,
            fx6_update_slot="Slot B",
            fx6_ac_adapter_connected=False,
            fx6_version_up_execute_requested=True,
        )
        self.assertEqual(bad_ac.errno, p379.EAGAIN_ERRNO)

        erofs = p379.simulate_87d_screen_reader_version_2slot_g104_and_erofs(
            operation="fx6_screen_reader_dormant_and_version_up_slotb_ac",
            body_model=p379.BODY_MODEL_FX6,
            fx6_update_slot="Slot B",
            fx6_ac_adapter_connected=True,
            fx6_version_up_execute_requested=True,
        )
        self.assertEqual(erofs.errno, p379.EROFS_ERRNO)

    def test_96_87d_invalid_screen_reader_speed_or_volume_einval(self) -> None:
        bad_spd = p379.simulate_87d_screen_reader_version_2slot_g104_and_erofs(
            operation="fx3_screen_reader_sku_gate_and_zero_hdmi_audio",
            body_model=p379.BODY_MODEL_FX30_AUTH,
            sku_screen_reader_authorized=True,
            screen_reader_speed="FAST_5",
        )
        self.assertEqual(bad_spd.errno, p379.EINVAL_ERRNO)

        bad_vol = p379.simulate_87d_screen_reader_version_2slot_g104_and_erofs(
            operation="fx3_screen_reader_sku_gate_and_zero_hdmi_audio",
            body_model=p379.BODY_MODEL_FX30_AUTH,
            sku_screen_reader_authorized=True,
            screen_reader_volume=16,
        )
        self.assertEqual(bad_vol.errno, p379.EINVAL_ERRNO)

    def test_97_87d_invalid_operation_or_body_raises(self) -> None:
        with self.assertRaises(p379.Stage87Phase379Error):
            p379.simulate_87d_screen_reader_version_2slot_g104_and_erofs(operation="bad")
        with self.assertRaises(p379.Stage87Phase379Error):
            p379.simulate_87d_screen_reader_version_2slot_g104_and_erofs(
                operation="fx3_version_2slot_g104_erratum_and_airplane_dot",
                body_model="FX9",
            )

    def test_98_87d_version_up_to_date_offline_dot_false(self) -> None:
        res = p379.simulate_87d_screen_reader_version_2slot_g104_and_erofs(
            operation="fx3_version_2slot_g104_erratum_and_airplane_dot",
            airplane_mode_on=False,
            online_newer_fw_available=False,
        )
        self.assertTrue(res.allowed)
        self.assertFalse(res.online_update_dot_shown)

    def test_99_87d_to_dict_serializes_cleanly_to_json(self) -> None:
        res = p379.simulate_87d_screen_reader_version_2slot_g104_and_erofs(
            operation="fx3_software_update_slot1_bodydata_erofs_firewall",
            slot1_bodydata_write_requested=True,
        )
        encoded = json.dumps(res.to_dict())
        self.assertIn("TIER0_SLOT1_BODYDATA_SOFTWARE_UPDATE_HARD_BLOCKED_EROFS", encoded)

    def test_100_87d_orchestrator_metrics_alignment(self) -> None:
        rep = p379.run_phase379_realhw_movieset_vpg_awbprio_touchpad_screenreader_version_coemulation(
            work_root=None
        )
        s = rep["submodel_87d_screen_reader_version_2slot_g104_erofs"]
        self.assertTrue(s["passed"])
        self.assertEqual(s["fx3_screen_reader_ui_exposed_items"], 0)
        self.assertEqual(s["fx6_screen_reader_ui_exposed_items"], 0)
        self.assertEqual(s["fx3_screen_reader_hdmi_audio_links"], 0)
        self.assertEqual(s["fx3_version_slots_count"], 2)
        self.assertTrue(s["fx3_g104_version_2slot_erratum_reconciled"])
        self.assertFalse(s["fx3_mi_shoe_version_displayed"])
        self.assertFalse(s["slot1_bodydata_write_authorized"])
        self.assertEqual(s["fx6_version_domains_count"], 3)

    # =========================================================================
    # Tests 101..108: 4-Mode Determinism, Portability, CLI & Suite 87/87 Wiring
    # =========================================================================

    def test_101_clean_room_digest_determinism_and_source_mode_distinction(self) -> None:
        r_f1 = p379.run_phase379_realhw_movieset_vpg_awbprio_touchpad_screenreader_version_coemulation(
            force_clean_room=True
        )
        r_f2 = p379.run_phase379_realhw_movieset_vpg_awbprio_touchpad_screenreader_version_coemulation(
            env={"FX3_FX6_FORCE_CLEAN_ROOM": "1"}
        )
        r_f3 = p379.run_phase379_realhw_movieset_vpg_awbprio_touchpad_screenreader_version_coemulation(
            env={"FX3_CLEAN_ROOM_TEST": "1"}
        )
        self.assertEqual(r_f1["phase379_audit_digest_sha256"], r_f2["phase379_audit_digest_sha256"])
        self.assertEqual(r_f1["phase379_audit_digest_sha256"], r_f3["phase379_audit_digest_sha256"])

        r_dl1 = p379.run_phase379_realhw_movieset_vpg_awbprio_touchpad_screenreader_version_coemulation(
            work_root=None
        )
        r_dl2 = p379.run_phase379_realhw_movieset_vpg_awbprio_touchpad_screenreader_version_coemulation(
            work_root="/nonexistent/phase379_stage87_test"
        )
        self.assertEqual(r_dl1["phase379_audit_digest_sha256"], r_dl2["phase379_audit_digest_sha256"])

        r_norm = p379.run_phase379_realhw_movieset_vpg_awbprio_touchpad_screenreader_version_coemulation()
        if r_norm["source_mode"] == "LOCAL_DONOR_O_RDONLY":
            self.assertNotEqual(
                r_norm["phase379_audit_digest_sha256"],
                r_f1["phase379_audit_digest_sha256"],
            )
            self.assertNotEqual(
                r_norm["phase379_audit_digest_sha256"],
                r_dl1["phase379_audit_digest_sha256"],
            )

    def test_102_portability_no_hardcoded_usr_bin_python_and_dont_write_bytecode(self) -> None:
        forbidden = "/" + "usr/bin/" + "python"
        for src in (Path(p379.__file__).resolve(), Path(__file__).resolve()):
            txt = src.read_text(encoding="utf-8")
            self.assertNotIn(forbidden, txt)
            self.assertIn("sys.dont_write_bytecode = True", txt)

    def test_103_standalone_cli_self_test_summary_json_help_and_subprocess(self) -> None:
        buf_sum = io.StringIO()
        with contextlib.redirect_stdout(buf_sum):
            rc = p379.main(["--self-test", "--clean-room", "--summary"])
        self.assertEqual(rc, 0)
        self.assertIn("[PASS] Phase 379 Stage 87 (87/87)", buf_sum.getvalue())
        self.assertIn("CLEAN_ROOM_SYNTHETIC", buf_sum.getvalue())

        buf_json = io.StringIO()
        with contextlib.redirect_stdout(buf_json):
            rc2 = p379.main(["--self-test", "--clean-room", "--json"])
        self.assertEqual(rc2, 0)
        parsed = json.loads(buf_json.getvalue())
        self.assertEqual(parsed["milestone"], "87/87")
        self.assertTrue(parsed["all_checks_passed"])

        buf_help = io.StringIO()
        with self.assertRaises(SystemExit) as cm:
            with contextlib.redirect_stdout(buf_help):
                p379.main(["--help"])
        self.assertEqual(cm.exception.code, 0)
        self.assertIn("87/87", buf_help.getvalue())

        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["FX3_FX6_FORCE_CLEAN_ROOM"] = "1"
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                str(Path(p379.__file__).resolve()),
                "--clean-room",
                "--summary",
            ],
            env=env,
            capture_output=True,
            text=True,
            check=True,
            timeout=60,
        )
        self.assertIn("Phase 379 Stage 87 (87/87)", proc.stdout)

    def test_104_suite_default_config_and_forward_compatible_stage87_keys(self) -> None:
        default_cfg = suite.CoEmulationConfig()
        self.assertTrue(
            default_cfg.include_phase379_realhw_movieset_vpg_awbprio_touchpad_screenreader_version_hil
        )
        self.assertTrue(default_cfg.include_stage87)
        self.assertTrue(
            default_cfg.stage87_realhw_movieset_vpg_awbprio_touchpad_screenreader_version_hil
        )

        fast_cfg = suite.CoEmulationConfig(**_fast_suite_kwargs())
        rep = suite.run_fx3_vm_coemulation_suite(fast_cfg)
        self.assertTrue(rep["all_checks_passed"])
        s87 = rep["stage87_realhw_movieset_vpg_awbprio_touchpad_screenreader_version_hil"]
        self.assertTrue(s87["all_checks_passed"])
        self.assertEqual(s87["phase_number"], 379)
        self.assertEqual(s87["milestone"], "87/87")
        self.assertEqual(s87["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(s87["slot1_writes"], 0)
        self.assertEqual(s87["slot1_data_sector_writes"], 0)
        self.assertEqual(s87["usb_tx_packets"], 0)
        self.assertEqual(s87["rf_tx_packets"], 0)

        stage_keys = [
            f
            for f in suite.CoEmulationConfig.__dataclass_fields__
            if re.match(r"^include_phase\d+_", f)
        ]
        # Forward-compatible assertion: Base 3 stages + optional phase flags >= 87
        self.assertGreaterEqual(len(stage_keys) + 3, 87)

    def test_105_suite_cli_summary_and_skip_flags(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = suite.main([*_FAST_CLI_FLAGS, "--summary"])
        self.assertEqual(rc, 0)
        self.assertIn(
            "realhw_movieset_vpg_awbprio_touchpad_screenreader_version_hil=",
            buf.getvalue(),
        )
        self.assertIn("m87=87/87", buf.getvalue())

        for skip_flag in ("--skip-stage87", "--no-include-stage87", "--skip-phase379"):
            buf_skip = io.StringIO()
            with contextlib.redirect_stdout(buf_skip):
                rc_skip = suite.main([*_FAST_CLI_FLAGS, skip_flag, "--json"])
            self.assertEqual(rc_skip, 0)
            rep_skip = json.loads(buf_skip.getvalue())
            self.assertNotIn(
                "stage87_realhw_movieset_vpg_awbprio_touchpad_screenreader_version_hil",
                rep_skip,
            )

    def test_106_suite_tamper_detection_fails_on_wrong_milestone(self) -> None:
        tampered = suite.CoEmulationConfig(**_fast_suite_kwargs())
        real = p379.run_phase379_realhw_movieset_vpg_awbprio_touchpad_screenreader_version_coemulation(
            force_clean_room=True
        )
        with unittest.mock.patch.object(
            p379,
            "run_phase379_realhw_movieset_vpg_awbprio_touchpad_screenreader_version_coemulation",
            return_value={**real, "milestone": "86/86"},
        ):
            rep_bad = suite.run_fx3_vm_coemulation_suite(tampered)
            self.assertFalse(rep_bad["all_checks_passed"])

    def test_107_suite_tamper_detection_fails_on_redline_or_invariant_breach(self) -> None:
        tampered = suite.CoEmulationConfig(**_fast_suite_kwargs())
        real = p379.run_phase379_realhw_movieset_vpg_awbprio_touchpad_screenreader_version_coemulation(
            force_clean_room=True
        )
        for bad_key, bad_val in (
            ("slot1_bodydata_write_authorized", True),
            ("cross_model_flash_authorized", True),
            ("live_attach_authorized", True),
            ("fx3_dormant_8k_exposed_events", 1),
            ("fx3_dormant_evf_touch_pad_exposed_events", 1),
            ("fx3_screen_reader_ui_exposed_items", 1),
            ("fx3_version_slots_count", 3),
            ("rf_tx_packets", 1),
            ("usb_tx_packets", 1),
        ):
            with unittest.mock.patch.object(
                p379,
                "run_phase379_realhw_movieset_vpg_awbprio_touchpad_screenreader_version_coemulation",
                return_value={**real, bad_key: bad_val},
            ):
                rep_bad = suite.run_fx3_vm_coemulation_suite(tampered)
                self.assertFalse(
                    rep_bad["all_checks_passed"],
                    f"Expected tamper fail for {bad_key}",
                )

    def test_108_run_self_test_wrapper_passes_clean_room_and_donorless(self) -> None:
        r_cr = p379.run_self_test(force_clean_room=True)
        self.assertTrue(r_cr["all_checks_passed"])
        self.assertEqual(r_cr["source_mode"], "CLEAN_ROOM_SYNTHETIC")

        r_dl = p379.run_self_test(work_root=None)
        self.assertTrue(r_dl["all_checks_passed"])
        self.assertEqual(r_dl["source_mode"], "CLEAN_ROOM_SYNTHETIC")


if __name__ == "__main__":
    unittest.main()
