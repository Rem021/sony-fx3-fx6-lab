#!/usr/bin/env python3
"""Unit tests for Phase 385 (Stage 89 — 89/89 Full-Board VM Co-Emulation Stages!):
Real-Hardware `ILME-FX3 Ver. 7.02` vs `ILME-FX6 Ver. 6.01` Wave-79 HIL:
- 89A: `Shooting -> [Zoom]` 8-Step Speed Architecture (`[Zoom Range]` & `[Zoom
  Ring Rotate]` anti-Reset vs 3 speed groups resettable; `[Custom Key Z. Speed]`
  Fixed `1..8` ONLY — NO `Variable` mode, `G149` closure; `[Remote Zoom Speed]`
  `Variable`/`Fix` via `BKID_APP_setting_fixed_zoom_speed_type`; `XLR-H1` zero
  zoom lever; 4 hard CIZ/Digital pre-lockouts + 5 active degradations; Power
  Zoom seamless handoff) vs FX6 `Technical > Zoom` (zero `Digital Zoom`),
  `Technical > Handle Zoom` (`Off`/`Low 1..8`/`High 1..8`/`Variable`), & `0..99`
  HUD `Zoom Position Display` clarification,
- 89B: `Setup -> [Dial Customize]` exact 5-item matrix (all anti-Reset) &
  physical 3-dial boundary (`Front Dial`/`Rear Dial`/`Control Wheel`, dormant
  `Dial Setup`/`Dial/Wheel Lock`/`Rear Dial L/R` blocked), `[My Dial Settings]`
  `1..3` Hold/Toggle/Cycle skipping empty banks + temp unlock of `[Lock
  Operation Parts]`, `[Function Ring(Lens)]` (`Power Focus` vs `APS-C/S35`
  respecting 4K/RAW lock, `FUNCTION_RING_INVALID` on ringless lens) vs FX6
  `Assignable Dial` (incl. `ND Filter`) vs `Multi Function Dial` (no `ND Filter`,
  menu-open lock),
- 89C: `Setup -> [Operation Customize]` exact 8-item `[Different Set for
  Still/Mv]` bitmask (`Picture Profile` resists BOTH Reset AND Initialize,
  `G99` closure; `Shutter Mode = Angle` forces split) vs independent `Fn`
  `12+12` slots (rejecting all-empty `Fn`), `[DISP (Screen Disp) Set]` exact 4
  shooting pages + 3 playback pages with 100% dormant zero-EVF firewall
  (`Graphic Display`/`For viewfinder`/`Monitor Off`/`Finder/Monitor`), `[Select
  LUT]` (`s709`/`709(800%)`/`S-Log3`/`User1..16`) + `[Display LUT]` overriding
  `[Gamma Display Assist]` in Movie Log vs Still Log `_f 0x6538` (`G132`
  closure) vs FX6 60-route `BKID_APP_SETTING_*_DISPLAY` & Cine EI Gamma lock,
- 89D: `Setup -> [External Output]` (all anti-Reset), 4-mode `[HDMI Resolution]`
  (no `720p`), Log/`PPLUT` internal rec `1080p` downshift, 6-mode `10bit 4:2:2`
  `[4K Output Set.(HDMI Only)]` (no `4:2:0`, no `24.00p 8bit`, `24.00p` reboot,
  `APS-C/S35` lock, `S&Q` locks `Rec. Media = On`), 100% dormant `24p/60p
  Output` (`0` ELF hits), `[HDMI Info. Display] = On` LCD blackout ONLY when
  `Rec. Media = On & RAW = Off`, `[REC Control]` depends on `TC Output = On`,
  `[4ch Audio Output]`, 3 Sony ELF typos (`ctrl_for_hmdi`, `outpute`,
  `4ch_output_ch`), Tier-0 `Slot 1 EROFS=30` vs FX6 25-entry `12G-SDI + HDMI`
  dual pipeline (`SDI RAW` + 4K HDMI vs `HDMI RAW` `4240x2392` locking SDI
  `1080P/i` & no `24Hz`, `S&Q > 60fps` cap `<= 1080p`, 3-mode `SDI/HDMI Rec
  Control`) (112 four-mode forward-compatible tests).
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
import time
import unittest
import unittest.mock

FX3_VM_DIR = Path(__file__).resolve().parents[1]
if str(FX3_VM_DIR) not in sys.path:
    sys.path.insert(0, str(FX3_VM_DIR))

import fx3_vm_coemulation_suite as suite  # noqa: E402
import realhw_zoomspeed_mydial3_funcring_hdmi4kout_sdi12g_coemulator as p385  # noqa: E402


def _fast_suite_kwargs(**overrides: object) -> dict:
    """Fast config skipping unrelated optional stages 4..88 for Stage 89 isolation."""
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
        include_stage87=False,
        include_stage88=False,
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
    "--skip-stage87",
    "--skip-stage88",
]


class TestPhase385Stage89ZoomSpeedMyDial3FuncRingHdmi4kOutSdi12g(unittest.TestCase):
    # =========================================================================
    # Tests 01..16: Schema, Stage 89 (89/89), Tier-0 Redlines & 4-Mode Donors
    # =========================================================================

    def test_01_schema_phase_and_stage89_constants(self) -> None:
        self.assertEqual(
            p385.SCHEMA_ID,
            "phase385_realhw_zoomspeed_mydial3_funcring_hdmi4kout_sdi12g_coemulation_v1",
        )
        self.assertEqual(p385.PHASE_NUMBER, 385)
        self.assertEqual(p385.STAGE_INDEX, 89)
        self.assertEqual(p385.STAGE_TOTAL, 89)
        self.assertEqual(p385.MILESTONE_LABEL, "89/89")
        self.assertFalse(p385.READY_FOR_LIVE_CAMERA_ATTACH)
        self.assertFalse(p385.LIVE_ATTACH_AUTHORIZED)
        self.assertFalse(p385.EMMC_WRITES_AUTHORIZED)
        self.assertFalse(p385.CROSS_MODEL_FLASH_AUTHORIZED)
        self.assertFalse(p385.HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        self.assertFalse(p385.SLOT1_WRITE_AUTHORIZED)
        self.assertEqual(p385.SLOT1_WRITES, 0)

    def test_02_orchestrator_returns_stage89_and_all_zero_redlines(self) -> None:
        rep = p385.run_phase385_realhw_zoomspeed_mydial3_funcring_hdmi4kout_sdi12g_coemulation(
            force_clean_room=True
        )
        self.assertTrue(rep["all_checks_passed"])
        self.assertEqual(rep["phase_number"], 385)
        self.assertEqual(rep["stage_index"], 89)
        self.assertEqual(rep["stage_total"], 89)
        self.assertEqual(rep["milestone"], "89/89")
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
        self.assertFalse(rep["slot1_write_authorized"])
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

    def test_03_donors_count_is_22_with_20_compact_and_2_window(self) -> None:
        self.assertEqual(len(p385.PHASE385_COMPACT_DONORS), 20)
        self.assertEqual(len(p385.PHASE385_WINDOW_DONORS), 2)
        info = p385.inspect_phase385_wave79_donors(force_clean_room=True)
        self.assertEqual(info["compact_donors_count"], 20)
        self.assertEqual(info["window_donors_count"], 2)
        self.assertEqual(info["total_donors_count"], 22)
        self.assertTrue(info["all_donors_verified"])
        self.assertEqual(info["raw_firmware_bytes_leaked"], 0)

    def test_04_donor_mode_normal_env_and_bounded_latency(self) -> None:
        t0 = time.monotonic()
        info = p385.inspect_phase385_wave79_donors()
        dt = time.monotonic() - t0
        self.assertLessEqual(dt, 2.0)
        self.assertTrue(info["all_donors_verified"])
        self.assertIn(info["source_mode"], ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"))
        self.assertEqual(info["total_donors_count"], 22)
        self.assertEqual(info["raw_firmware_bytes_leaked"], 0)

    def test_05_donor_mode_fx3_clean_room_test_env(self) -> None:
        info = p385.inspect_phase385_wave79_donors(env={"FX3_CLEAN_ROOM_TEST": "1"})
        self.assertEqual(info["source_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(info["forced_clean_room"])
        self.assertTrue(info["all_donors_verified"])

    def test_06_donor_mode_fx3_fx6_force_clean_room_env(self) -> None:
        info = p385.inspect_phase385_wave79_donors(env={"FX3_FX6_FORCE_CLEAN_ROOM": "1"})
        self.assertEqual(info["source_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(info["forced_clean_room"])
        self.assertTrue(info["all_donors_verified"])

    def test_07_donor_mode_work_root_none_and_sentinel(self) -> None:
        info_none = p385.inspect_phase385_wave79_donors(work_root=None)
        self.assertEqual(info_none["source_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertFalse(info_none["work_root_available"])
        info_sent = p385.inspect_phase385_wave79_donors(
            env={"FX3_FX6_MAC_WORK_ROOT": p385._DONOR_DISABLED_SENTINEL}
        )
        self.assertEqual(info_sent["source_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertFalse(info_sent["work_root_available"])

    def test_08_donor_mode_nonexistent_work_root_graceful_clean_room(self) -> None:
        info = p385.inspect_phase385_wave79_donors(
            work_root="/nonexistent/phase385_stage89_missing_dir",
            force_clean_room=False,
        )
        self.assertEqual(info["source_mode"], "CLEAN_ROOM_SYNTHETIC")
        self.assertTrue(info["all_donors_verified"])

    def test_09_open_flags_include_o_rdonly_nofollow_nonblock(self) -> None:
        self.assertEqual(p385._DONOR_OPEN_FLAGS & os.O_RDONLY, os.O_RDONLY)
        if hasattr(os, "O_NOFOLLOW"):
            self.assertTrue(bool(p385._DONOR_OPEN_FLAGS & os.O_NOFOLLOW))
        if hasattr(os, "O_NONBLOCK"):
            self.assertTrue(bool(p385._DONOR_OPEN_FLAGS & os.O_NONBLOCK))

    def test_10_resolve_mac_work_root_and_is_forced_clean_room_helpers(self) -> None:
        self.assertIsNone(p385.resolve_mac_work_root(work_root=None))
        self.assertIsNone(p385.resolve_mac_work_root(work_root=""))
        self.assertIsNone(p385.resolve_mac_work_root(work_root=p385._DONOR_DISABLED_SENTINEL))
        self.assertEqual(
            p385.resolve_mac_work_root(work_root="/tmp/demo_stage89"), Path("/tmp/demo_stage89")
        )
        self.assertIsNone(p385.resolve_mac_work_root(env={"FX3_FX6_MAC_WORK_ROOT": ""}))
        self.assertTrue(p385.is_forced_clean_room({"FX3_CLEAN_ROOM_TEST": "1"}))
        self.assertTrue(p385.is_forced_clean_room({"FX3_FX6_FORCE_CLEAN_ROOM": "1"}))
        self.assertFalse(p385.is_forced_clean_room({}))

    def test_11_bounded_window_rejects_oversized_read_request(self) -> None:
        with self.assertRaises(p385.Stage89Phase385Error):
            p385._read_bounded_window_o_rdonly(Path(__file__), 0, 4097)

    def test_12_compact_reader_rejects_file_over_1mib(self) -> None:
        fake_stat = unittest.mock.MagicMock(st_size=2 * 1024 * 1024)
        with unittest.mock.patch("os.open", return_value=99), \
             unittest.mock.patch("os.fstat", return_value=fake_stat), \
             unittest.mock.patch("os.close"):
            with self.assertRaises(p385.Stage89Phase385Error):
                p385._read_full_compact_o_rdonly(Path("/fake/huge.bin"))

    def test_13_fx3_appfw_window_spec_anchors_all_3_sony_elf_typos(self) -> None:
        wspec = next(w for w in p385.PHASE385_WINDOW_DONORS if w.name == "fx3_appfw")
        needles = {needle for _, _, needle in wspec.windows}
        self.assertIn(b"BKID_APP_setting_ctrl_for_hmdi", needles)
        self.assertIn(b"PRM_HAITA_hdmi_4k_outpute_apsc_restriction", needles)
        self.assertIn(b"BKID_APP_setting_4ch_output_ch", needles)

    def test_14_fx3_appfw_window_spec_forbids_dial_setup_8bit_24p60p_and_correct_spellings(self) -> None:
        wspec = next(w for w in p385.PHASE385_WINDOW_DONORS if w.name == "fx3_appfw")
        absent_needles = {needle for _, _, needle in wspec.absent_windows}
        self.assertIn(b"VAL_setting_dial_setup_", absent_needles)
        self.assertIn(b"HDMI_ONLY_4K_OUTPUT_SETTING_24_00P_8BIT", absent_needles)
        self.assertIn(b"24p/60p Output", absent_needles)
        self.assertIn(b"BKID_APP_setting_4ch_audio_output", absent_needles)
        self.assertIn(b"BKID_APP_setting_ctrl_for_hdmi", absent_needles)

    def test_15_fx6_appfw_window_spec_anchors_handle_zoom_hud_pos_and_forbids_digital_zoom(self) -> None:
        wspec = next(w for w in p385.PHASE385_WINDOW_DONORS if w.name == "fx6_appfw")
        needles = {needle for _, _, needle in wspec.windows}
        absent_needles = {needle for _, _, needle in wspec.absent_windows}
        self.assertIn(b"BKID_APP_SETTING_HANDLE_ZOOM_HIGH", needles)
        self.assertIn(b"BKID_APP_SETTING_LENS_ZOOM_POSITION_DISPLAY", needles)
        self.assertIn(b"VAL_setting_output_format_sdi_hdmi_OUTPUT_FORMAT_HDMI_4096", needles)
        self.assertIn(b"BKID_APP_SETTING_DIGITAL_ZOOM", absent_needles)

    def test_16_recursive_strip_wall_clock_removes_elapsed_seconds_and_ms(self) -> None:
        sample = {
            "a": 1,
            "elapsed_seconds": 0.456,
            "nested": {
                "elapsed_ms": 45.6,
                "items": [{"elapsed_seconds": 1.2, "keep": True}],
            },
        }
        cleaned = p385._strip_wall_clock(sample)
        self.assertEqual(cleaned, {"a": 1, "nested": {"items": [{"keep": True}]}})

    # =========================================================================
    # Tests 17..39: Sub-Model 89A — Shooting -> [Zoom] 8-Step Speed vs FX6
    # =========================================================================

    def test_17_89a_zoom_range_and_ring_rotate_resist_cam_reset_while_3_speeds_reset(self) -> None:
        res = p385.simulate_89a_zoom_8step_speed_ciz_lockouts_and_fx6_handle_zoom(
            operation="fx3_zoom_range_speeds_reset_split_and_ring_rotate",
            zoom_range="ClearImage Zoom",
            zoom_ring_rotate="Right(W)/Left(T)",
            lever_1st_stby=5,
            lever_1st_rec=6,
            lever_2nd_stby=4,
            lever_2nd_rec=4,
            custom_key_speed_stby=7,
            custom_key_speed_rec=7,
            remote_speed_type="Fix",
            remote_fixed_speed_stby=2,
            remote_fixed_speed_rec=2,
            camera_settings_reset_triggered=True,
        )
        self.assertTrue(res.allowed)
        self.assertEqual(res.zoom_range, "ClearImage Zoom")
        self.assertTrue(res.zoom_range_survived_cam_reset)
        self.assertEqual(res.zoom_ring_rotate, "Right(W)/Left(T)")
        self.assertTrue(res.zoom_ring_rotate_survived_cam_reset)
        self.assertEqual(res.lever_1st_stby, 3)
        self.assertEqual(res.lever_1st_rec, 3)
        self.assertEqual(res.lever_2nd_stby, 8)
        self.assertEqual(res.lever_2nd_rec, 8)
        self.assertEqual(res.custom_key_speed_stby, 3)
        self.assertEqual(res.custom_key_speed_rec, 3)
        self.assertEqual(res.remote_speed_type, "Variable")
        self.assertEqual(res.remote_fixed_speed_stby, 3)
        self.assertEqual(res.remote_fixed_speed_rec, 3)

    def test_18_89a_initialize_resets_zoom_range_ring_rotate_and_all_speeds(self) -> None:
        res = p385.simulate_89a_zoom_8step_speed_ciz_lockouts_and_fx6_handle_zoom(
            operation="fx3_zoom_range_speeds_reset_split_and_ring_rotate",
            zoom_range="Digital Zoom",
            zoom_ring_rotate="Right(W)/Left(T)",
            lever_1st_stby=7,
            initialize_triggered=True,
        )
        self.assertTrue(res.allowed)
        self.assertEqual(res.zoom_range, "Optical zoom only")
        self.assertEqual(res.zoom_ring_rotate, "Left(W)/Right(T)")
        self.assertEqual(res.lever_1st_stby, 3)
        self.assertEqual(res.lever_2nd_stby, 8)

    def test_19_89a_g149_custom_key_z_speed_blocks_variable_mode(self) -> None:
        res = p385.simulate_89a_zoom_8step_speed_ciz_lockouts_and_fx6_handle_zoom(
            operation="fx3_zoom_range_speeds_reset_split_and_ring_rotate",
            custom_key_speed_type="Variable",
        )
        self.assertFalse(res.allowed)
        self.assertEqual(res.errno, p385.EOPNOTSUPP_ERRNO)
        self.assertTrue(res.custom_key_variable_blocked)
        self.assertFalse(res.custom_key_has_variable_mode)
        self.assertTrue(res.g149_custom_key_no_variable_reconciled)

    def test_20_89a_remote_zoom_speed_exposes_variable_and_fix_via_elf_symbol(self) -> None:
        for stype in ("Variable", "Fix"):
            res = p385.simulate_89a_zoom_8step_speed_ciz_lockouts_and_fx6_handle_zoom(
                operation="fx3_zoom_range_speeds_reset_split_and_ring_rotate",
                remote_speed_type=stype,
                remote_fixed_speed_stby=4,
                remote_fixed_speed_rec=5,
            )
            self.assertTrue(res.allowed)
            self.assertEqual(res.remote_speed_type, stype)
            self.assertEqual(
                res.remote_speed_type_elf_symbol,
                "BKID_APP_setting_fixed_zoom_speed_type",
            )

    def test_21_89a_zoom_magnifications_movie_4k_hd_and_still_ff_apsc(self) -> None:
        r_4k = p385.simulate_89a_zoom_8step_speed_ciz_lockouts_and_fx6_handle_zoom(
            operation="fx3_zoom_range_speeds_reset_split_and_ring_rotate",
            shoot_mode="Movie",
            zoom_range="ClearImage Zoom",
            movie_resolution="4K",
        )
        self.assertAlmostEqual(r_4k.max_magnification, 1.5, places=2)

        r_hd = p385.simulate_89a_zoom_8step_speed_ciz_lockouts_and_fx6_handle_zoom(
            operation="fx3_zoom_range_speeds_reset_split_and_ring_rotate",
            shoot_mode="Movie",
            zoom_range="ClearImage Zoom",
            movie_resolution="HD",
        )
        self.assertAlmostEqual(r_hd.max_magnification, 2.0, places=2)

        r_dig = p385.simulate_89a_zoom_8step_speed_ciz_lockouts_and_fx6_handle_zoom(
            operation="fx3_zoom_range_speeds_reset_split_and_ring_rotate",
            shoot_mode="Movie",
            zoom_range="Digital Zoom",
        )
        self.assertAlmostEqual(r_dig.max_magnification, 4.0, places=2)

        r_sm = p385.simulate_89a_zoom_8step_speed_ciz_lockouts_and_fx6_handle_zoom(
            operation="fx3_zoom_range_speeds_reset_split_and_ring_rotate",
            shoot_mode="Still",
            zoom_range="Smart Zoom",
            still_image_size="S",
        )
        self.assertTrue(r_sm.allowed)
        self.assertAlmostEqual(r_sm.max_magnification, 2.0, places=2)

    def test_22_89a_smart_zoom_blocked_in_movie_sq_and_still_l(self) -> None:
        for mode, sz in (("Movie", "L"), ("S&Q", "M"), ("Still", "L")):
            res = p385.simulate_89a_zoom_8step_speed_ciz_lockouts_and_fx6_handle_zoom(
                operation="fx3_zoom_range_speeds_reset_split_and_ring_rotate",
                shoot_mode=mode,
                zoom_range="Smart Zoom",
                still_image_size=sz,
            )
            self.assertFalse(res.allowed)
            self.assertEqual(res.errno, p385.EOPNOTSUPP_ERRNO)

    def test_23_89a_xlr_h1_top_handle_has_no_zoom_lever(self) -> None:
        res = p385.simulate_89a_zoom_8step_speed_ciz_lockouts_and_fx6_handle_zoom(
            operation="fx3_zoom_range_speeds_reset_split_and_ring_rotate",
            xlr_h1_zoom_lever_requested=True,
        )
        self.assertFalse(res.allowed)
        self.assertEqual(res.errno, p385.EOPNOTSUPP_ERRNO)
        self.assertFalse(res.xlr_h1_has_zoom_lever)
        self.assertTrue(res.xlr_h1_phantom_zoom_blocked)

    def test_24_89a_zoom_speed_1_to_8_bounds_validation(self) -> None:
        for kw in (
            {"lever_1st_stby": 0},
            {"lever_2nd_rec": 9},
            {"custom_key_speed_stby": 9},
            {"remote_fixed_speed_rec": 0},
        ):
            res = p385.simulate_89a_zoom_8step_speed_ciz_lockouts_and_fx6_handle_zoom(
                operation="fx3_zoom_range_speeds_reset_split_and_ring_rotate",
                **kw,
            )
            self.assertEqual(res.errno, p385.EINVAL_ERRNO)

    def test_25_89a_ciz_prelockout_1_still_raw_formats(self) -> None:
        for fmt in ("RAW", "RAW & JPEG", "RAW & HEIF"):
            res = p385.simulate_89a_zoom_8step_speed_ciz_lockouts_and_fx6_handle_zoom(
                operation="fx3_ciz_digital_4_prelockouts_and_5_active_degradations",
                shoot_mode="Still",
                zoom_range="ClearImage Zoom",
                still_file_format=fmt,
            )
            self.assertFalse(res.allowed)
            self.assertEqual(res.errno, p385.EOPNOTSUPP_ERRNO)
            self.assertIn("STILL_RAW_FORMAT", res.pre_lockouts_triggered)

    def test_26_89a_ciz_prelockout_2_movie_119_88p_100p(self) -> None:
        for fps in ("119.88p", "100p"):
            res = p385.simulate_89a_zoom_8step_speed_ciz_lockouts_and_fx6_handle_zoom(
                operation="fx3_ciz_digital_4_prelockouts_and_5_active_degradations",
                shoot_mode="Movie",
                zoom_range="ClearImage Zoom",
                rec_frame_rate=fps,
            )
            self.assertFalse(res.allowed)
            self.assertEqual(res.errno, p385.EOPNOTSUPP_ERRNO)
            self.assertIn("MOVIE_119_88P_100P", res.pre_lockouts_triggered)

    def test_27_89a_ciz_prelockout_3_sq_ge_100fps(self) -> None:
        for fps in (100, 120, 200, 240):
            res = p385.simulate_89a_zoom_8step_speed_ciz_lockouts_and_fx6_handle_zoom(
                operation="fx3_ciz_digital_4_prelockouts_and_5_active_degradations",
                shoot_mode="S&Q",
                zoom_range="Digital Zoom",
                sq_frame_rate_fps=fps,
            )
            self.assertFalse(res.allowed)
            self.assertEqual(res.errno, p385.EOPNOTSUPP_ERRNO)
            self.assertIn("SQ_GE_100FPS", res.pre_lockouts_triggered)

    def test_28_89a_ciz_prelockout_4_hdmi_raw_output_on(self) -> None:
        res = p385.simulate_89a_zoom_8step_speed_ciz_lockouts_and_fx6_handle_zoom(
            operation="fx3_ciz_digital_4_prelockouts_and_5_active_degradations",
            shoot_mode="Movie",
            zoom_range="ClearImage Zoom",
            hdmi_raw_output_on=True,
        )
        self.assertFalse(res.allowed)
        self.assertEqual(res.errno, p385.EOPNOTSUPP_ERRNO)
        self.assertIn("HDMI_RAW_OUTPUT_ON", res.pre_lockouts_triggered)

    def test_29_89a_ciz_engaged_triggers_all_5_af_and_metering_degradations(self) -> None:
        res = p385.simulate_89a_zoom_8step_speed_ciz_lockouts_and_fx6_handle_zoom(
            operation="fx3_ciz_digital_4_prelockouts_and_5_active_degradations",
            shoot_mode="Movie",
            zoom_range="ClearImage Zoom",
            non_optical_engaged=True,
            is_power_zoom_lens=True,
        )
        self.assertTrue(res.allowed)
        self.assertTrue(res.seamless_optical_to_ciz)
        self.assertEqual(len(res.active_degradations_triggered), 5)
        self.assertEqual(res.active_degradations_triggered, p385.FX3_CIZ_5_ACTIVE_DEGRADATION_IDS)

    def test_30_89a_optical_zoom_only_has_zero_degradations_and_lockouts(self) -> None:
        res = p385.simulate_89a_zoom_8step_speed_ciz_lockouts_and_fx6_handle_zoom(
            operation="fx3_ciz_digital_4_prelockouts_and_5_active_degradations",
            shoot_mode="Movie",
            zoom_range="Optical zoom only",
            rec_frame_rate="119.88p",
            hdmi_raw_output_on=True,
            non_optical_engaged=True,
        )
        self.assertTrue(res.allowed)
        self.assertEqual(res.pre_lockouts_triggered, ())
        self.assertEqual(res.active_degradations_triggered, ())

    def test_31_89a_prime_lens_starts_directly_at_1x_electronic_zoom(self) -> None:
        res = p385.simulate_89a_zoom_8step_speed_ciz_lockouts_and_fx6_handle_zoom(
            operation="fx3_ciz_digital_4_prelockouts_and_5_active_degradations",
            shoot_mode="Movie",
            zoom_range="ClearImage Zoom",
            is_power_zoom_lens=False,
            non_optical_engaged=True,
        )
        self.assertTrue(res.allowed)
        self.assertFalse(res.is_power_zoom_lens)
        self.assertFalse(res.seamless_optical_to_ciz)

    def test_32_89a_fx6_zero_digital_zoom_blocked_eopnotsupp(self) -> None:
        res = p385.simulate_89a_zoom_8step_speed_ciz_lockouts_and_fx6_handle_zoom(
            operation="fx6_zoom_type_handle_zoom_and_0_99_hud_clarification",
            body_model=p385.BODY_MODEL_FX6,
            fx6_zoom_type="Digital Zoom",
        )
        self.assertFalse(res.allowed)
        self.assertEqual(res.errno, p385.EOPNOTSUPP_ERRNO)
        self.assertTrue(res.fx6_digital_zoom_blocked)

    def test_33_89a_fx6_speed_1_99_menu_debunked_0_99_is_hud_position(self) -> None:
        blk = p385.simulate_89a_zoom_8step_speed_ciz_lockouts_and_fx6_handle_zoom(
            operation="fx6_zoom_type_handle_zoom_and_0_99_hud_clarification",
            body_model=p385.BODY_MODEL_FX6,
            fx6_speed_1_99_menu_requested=True,
        )
        self.assertFalse(blk.allowed)
        self.assertEqual(blk.errno, p385.EOPNOTSUPP_ERRNO)
        self.assertTrue(blk.fx6_speed_1_99_debunked)

        for pos in (0, 50, 99):
            ok = p385.simulate_89a_zoom_8step_speed_ciz_lockouts_and_fx6_handle_zoom(
                operation="fx6_zoom_type_handle_zoom_and_0_99_hud_clarification",
                body_model=p385.BODY_MODEL_FX6,
                fx6_zoom_position_hud_value=pos,
            )
            self.assertTrue(ok.allowed)
            self.assertEqual(ok.fx6_zoom_position_hud_value, pos)

    def test_34_89a_fx6_handle_zoom_all_4_settings_and_low3_high8_defaults(self) -> None:
        for setting in p385.FX6_HANDLE_ZOOM_SETTINGS:
            res = p385.simulate_89a_zoom_8step_speed_ciz_lockouts_and_fx6_handle_zoom(
                operation="fx6_zoom_type_handle_zoom_and_0_99_hud_clarification",
                body_model=p385.BODY_MODEL_FX6,
                fx6_handle_zoom_setting=setting,
            )
            self.assertTrue(res.allowed)
            self.assertEqual(res.fx6_handle_zoom_low, 3)
            self.assertEqual(res.fx6_handle_zoom_high, 8)

    def test_35_89a_fx6_invalid_handle_zoom_or_hud_pos_einval(self) -> None:
        r1 = p385.simulate_89a_zoom_8step_speed_ciz_lockouts_and_fx6_handle_zoom(
            operation="fx6_zoom_type_handle_zoom_and_0_99_hud_clarification",
            body_model=p385.BODY_MODEL_FX6,
            fx6_handle_zoom_low=9,
        )
        self.assertEqual(r1.errno, p385.EINVAL_ERRNO)
        r2 = p385.simulate_89a_zoom_8step_speed_ciz_lockouts_and_fx6_handle_zoom(
            operation="fx6_zoom_type_handle_zoom_and_0_99_hud_clarification",
            body_model=p385.BODY_MODEL_FX6,
            fx6_zoom_position_hud_value=100,
        )
        self.assertEqual(r2.errno, p385.EINVAL_ERRNO)

    def test_36_89a_invalid_zoom_range_ring_or_remote_type_einval(self) -> None:
        for kw in (
            {"zoom_range": "SuperZoom"},
            {"custom_key_speed_type": "Auto"},
            {"remote_speed_type": "Smooth"},
            {"zoom_ring_rotate": "Up/Down"},
        ):
            r = p385.simulate_89a_zoom_8step_speed_ciz_lockouts_and_fx6_handle_zoom(
                operation="fx3_zoom_range_speeds_reset_split_and_ring_rotate",
                **kw,
            )
            self.assertEqual(r.errno, p385.EINVAL_ERRNO)

    def test_37_89a_invalid_operation_body_or_mode_raises(self) -> None:
        with self.assertRaises(p385.Stage89Phase385Error):
            p385.simulate_89a_zoom_8step_speed_ciz_lockouts_and_fx6_handle_zoom(operation="bad")
        with self.assertRaises(p385.Stage89Phase385Error):
            p385.simulate_89a_zoom_8step_speed_ciz_lockouts_and_fx6_handle_zoom(
                operation="fx3_zoom_range_speeds_reset_split_and_ring_rotate",
                body_model="FX9",
            )
        with self.assertRaises(p385.Stage89Phase385Error):
            p385.simulate_89a_zoom_8step_speed_ciz_lockouts_and_fx6_handle_zoom(
                operation="fx3_zoom_range_speeds_reset_split_and_ring_rotate",
                shoot_mode="Timelapse",
            )

    def test_38_89a_to_dict_serializes_cleanly(self) -> None:
        res = p385.simulate_89a_zoom_8step_speed_ciz_lockouts_and_fx6_handle_zoom(
            operation="fx3_zoom_range_speeds_reset_split_and_ring_rotate",
        )
        self.assertIn("BKID_APP_setting_fixed_zoom_speed_type", json.dumps(res.to_dict()))

    def test_39_89a_orchestrator_metrics_alignment(self) -> None:
        rep = p385.run_phase385_realhw_zoomspeed_mydial3_funcring_hdmi4kout_sdi12g_coemulation(
            work_root=None
        )
        s = rep["submodel_89a_zoom_8step_speed_ciz_lockouts_fx6_handle_zoom"]
        self.assertTrue(s["passed"])
        self.assertFalse(s["fx3_custom_key_has_variable_mode"])
        self.assertTrue(s["fx3_g149_custom_key_no_variable_reconciled"])
        self.assertEqual(s["fx3_ciz_pre_lockouts_count"], 4)
        self.assertEqual(s["fx3_ciz_active_degradations_count"], 5)
        self.assertFalse(s["fx3_xlr_h1_has_zoom_lever"])
        self.assertFalse(s["fx6_has_digital_zoom"])
        self.assertFalse(s["fx6_has_speed_1_99_menu"])

    # =========================================================================
    # Tests 40..62: Sub-Model 89B — Setup -> [Dial Customize] 5-Item vs FX6
    # =========================================================================

    def test_40_89b_all_5_dial_customize_items_exposed_and_anti_reset(self) -> None:
        self.assertEqual(len(p385.FX3_DIAL_CUSTOMIZE_EXACT_5_ITEMS), 5)
        for item in p385.FX3_DIAL_CUSTOMIZE_EXACT_5_ITEMS:
            res = p385.simulate_89b_dial_customize_5item_mydial3_funcring_and_fx6_dials(
                operation="fx3_dial_customize_5item_3dial_boundary_and_dormant_block",
                dial_customize_item=item,
                av_tv_rotate="Reverse",
                lock_operation_parts="All",
                camera_settings_reset_triggered=True,
            )
            self.assertTrue(res.allowed)
            self.assertTrue(res.survived_cam_reset)
            self.assertTrue(res.all_5_items_resist_cam_reset)
            self.assertEqual(res.exposed_dial_customize_items_count, 5)
            self.assertEqual(res.physical_dial_count, 3)

    def test_41_89b_initialize_resets_all_5_dial_customize_items(self) -> None:
        res = p385.simulate_89b_dial_customize_5item_mydial3_funcring_and_fx6_dials(
            operation="fx3_dial_customize_5item_3dial_boundary_and_dormant_block",
            av_tv_rotate="Reverse",
            lock_operation_parts="All",
            initialize_triggered=True,
        )
        self.assertTrue(res.allowed)
        self.assertTrue(res.reset_on_initialize)
        self.assertEqual(res.front_dial_func, "Aperture")
        self.assertEqual(res.rear_dial_func, "ISO/EI")
        self.assertEqual(res.control_wheel_func, "Shutter Speed")
        self.assertEqual(res.av_tv_rotate, "Normal")
        self.assertEqual(res.av_tv_rotate_coefficient, 1)
        self.assertEqual(res.lock_operation_parts, "Off")

    def test_42_89b_physical_3_dials_allowed(self) -> None:
        for dial in p385.FX3_PHYSICAL_3_DIALS:
            res = p385.simulate_89b_dial_customize_5item_mydial3_funcring_and_fx6_dials(
                operation="fx3_dial_customize_5item_3dial_boundary_and_dormant_block",
                target_dial=dial,
            )
            self.assertTrue(res.allowed)

    def test_43_89b_dormant_dial_setup_wheel_lock_and_rear_dial_lr_blocked(self) -> None:
        for dormant in ("Dial Setup", "Dial / Wheel Lock", "Dial/Wheel Lock"):
            res = p385.simulate_89b_dial_customize_5item_mydial3_funcring_and_fx6_dials(
                operation="fx3_dial_customize_5item_3dial_boundary_and_dormant_block",
                dial_customize_item=dormant,
            )
            self.assertFalse(res.allowed)
            self.assertEqual(res.errno, p385.EOPNOTSUPP_ERRNO)
            self.assertTrue(res.dormant_dial_or_rear_lr_blocked)

        for rear_lr in ("Rear Dial L", "Rear Dial R"):
            res = p385.simulate_89b_dial_customize_5item_mydial3_funcring_and_fx6_dials(
                operation="fx3_dial_customize_5item_3dial_boundary_and_dormant_block",
                target_dial=rear_lr,
            )
            self.assertFalse(res.allowed)
            self.assertEqual(res.errno, p385.EOPNOTSUPP_ERRNO)
            self.assertTrue(res.dormant_dial_or_rear_lr_blocked)

    def test_44_89b_av_tv_rotate_normal_and_reverse_coefficients(self) -> None:
        r_norm = p385.simulate_89b_dial_customize_5item_mydial3_funcring_and_fx6_dials(
            operation="fx3_dial_customize_5item_3dial_boundary_and_dormant_block",
            av_tv_rotate="Normal",
        )
        self.assertEqual(r_norm.av_tv_rotate_coefficient, 1)

        r_rev = p385.simulate_89b_dial_customize_5item_mydial3_funcring_and_fx6_dials(
            operation="fx3_dial_customize_5item_3dial_boundary_and_dormant_block",
            av_tv_rotate="Reverse",
        )
        self.assertEqual(r_rev.av_tv_rotate_coefficient, -1)

    def test_45_89b_lock_operation_parts_all_4_options(self) -> None:
        for opt in p385.FX3_LOCK_OP_PARTS_OPTIONS:
            res = p385.simulate_89b_dial_customize_5item_mydial3_funcring_and_fx6_dials(
                operation="fx3_dial_customize_5item_3dial_boundary_and_dormant_block",
                lock_operation_parts=opt,
            )
            self.assertTrue(res.allowed)
            self.assertEqual(res.lock_operation_parts, opt)

    def test_46_89b_my_dial_1_3_hold_and_toggle_temp_unlock_lock_op_parts(self) -> None:
        for recall in ("Hold", "Toggle"):
            for lock_mode in ("Dial + Wheel", "All"):
                res = p385.simulate_89b_dial_customize_5item_mydial3_funcring_and_fx6_dials(
                    operation="fx3_mydial_1_3_recall_skip_empty_and_lock_temp_unlock",
                    my_dial_bank="My Dial 1",
                    my_dial_recall_mode=recall,
                    lock_operation_parts=lock_mode,
                )
                self.assertTrue(res.allowed)
                self.assertEqual(res.my_dial_active_bank, "My Dial 1")
                self.assertTrue(res.lock_op_parts_temp_unlocked)

    def test_47_89b_my_dial_cycle_1_2_3_automatically_skips_empty_banks(self) -> None:
        res = p385.simulate_89b_dial_customize_5item_mydial3_funcring_and_fx6_dials(
            operation="fx3_mydial_1_3_recall_skip_empty_and_lock_temp_unlock",
            my_dial_bank="My Dial 1",
            my_dial_recall_mode="Cycle",
            lock_operation_parts="Dial + Wheel",
        )
        self.assertTrue(res.allowed)
        self.assertEqual(res.my_dial_active_bank, "My Dial 3")
        self.assertEqual(res.my_dial_skipped_empty_banks, ("My Dial 2",))
        self.assertTrue(res.lock_op_parts_temp_unlocked)

    def test_48_89b_my_dial_all_empty_returns_ebusy(self) -> None:
        empty = {
            "My Dial 1": ("Not set", "Not set", "Not set"),
            "My Dial 2": ("Not set", "Not set", "Not set"),
            "My Dial 3": ("Not set", "Not set", "Not set"),
        }
        res = p385.simulate_89b_dial_customize_5item_mydial3_funcring_and_fx6_dials(
            operation="fx3_mydial_1_3_recall_skip_empty_and_lock_temp_unlock",
            my_dial_bank="My Dial 1",
            my_dial_recall_mode="Cycle",
            my_dial_banks_configured=empty,
        )
        self.assertFalse(res.allowed)
        self.assertEqual(res.errno, p385.EBUSY_ERRNO)
        self.assertEqual(len(res.my_dial_skipped_empty_banks), 3)

    def test_49_89b_my_dial_rejects_dormant_rear_dial_lr(self) -> None:
        for dial in ("Rear Dial L", "Rear Dial R"):
            res = p385.simulate_89b_dial_customize_5item_mydial3_funcring_and_fx6_dials(
                operation="fx3_mydial_1_3_recall_skip_empty_and_lock_temp_unlock",
                target_dial=dial,
            )
            self.assertFalse(res.allowed)
            self.assertEqual(res.errno, p385.EOPNOTSUPP_ERRNO)
            self.assertTrue(res.dormant_dial_or_rear_lr_blocked)

    def test_50_89b_function_ring_lens_power_focus_and_apsc_s35_ok(self) -> None:
        for mode in p385.FX3_FUNCTION_RING_OPTIONS:
            res = p385.simulate_89b_dial_customize_5item_mydial3_funcring_and_fx6_dials(
                operation="fx3_function_ring_lens_power_focus_and_apsc_s35",
                function_ring_mode=mode,
                lens_has_function_ring=True,
                rec_format_forbids_apsc=False,
            )
            self.assertTrue(res.allowed)
            self.assertEqual(res.function_ring_mode, mode)

    def test_51_89b_function_ring_lens_without_ring_returns_invalid_fallback(self) -> None:
        res = p385.simulate_89b_dial_customize_5item_mydial3_funcring_and_fx6_dials(
            operation="fx3_function_ring_lens_power_focus_and_apsc_s35",
            function_ring_mode="Power Focus",
            lens_has_function_ring=False,
        )
        self.assertFalse(res.allowed)
        self.assertEqual(res.errno, p385.EOPNOTSUPP_ERRNO)
        self.assertTrue(res.function_ring_invalid_fallback)

    def test_52_89b_function_ring_apsc_s35_blocked_under_4k_or_raw_crop_lock(self) -> None:
        res = p385.simulate_89b_dial_customize_5item_mydial3_funcring_and_fx6_dials(
            operation="fx3_function_ring_lens_power_focus_and_apsc_s35",
            function_ring_mode="APS-C/Super 35 mm / Full Frame",
            lens_has_function_ring=True,
            rec_format_forbids_apsc=True,
        )
        self.assertFalse(res.allowed)
        self.assertEqual(res.errno, p385.EOPNOTSUPP_ERRNO)
        self.assertTrue(res.apsc_s35_crop_lock_blocked)

    def test_53_89b_function_ring_resists_cam_reset_resets_on_init(self) -> None:
        r_rst = p385.simulate_89b_dial_customize_5item_mydial3_funcring_and_fx6_dials(
            operation="fx3_function_ring_lens_power_focus_and_apsc_s35",
            function_ring_mode="APS-C/Super 35 mm / Full Frame",
            camera_settings_reset_triggered=True,
        )
        self.assertTrue(r_rst.allowed)
        self.assertTrue(r_rst.survived_cam_reset)

        r_init = p385.simulate_89b_dial_customize_5item_mydial3_funcring_and_fx6_dials(
            operation="fx3_function_ring_lens_power_focus_and_apsc_s35",
            function_ring_mode="APS-C/Super 35 mm / Full Frame",
            initialize_triggered=True,
        )
        self.assertTrue(r_init.allowed)
        self.assertEqual(r_init.function_ring_mode, "Power Focus")
        self.assertTrue(r_init.reset_on_initialize)

    def test_54_89b_fx6_assignable_dial_includes_nd_filter_for_grip_and_handle(self) -> None:
        for node in p385.FX6_ASSIGNABLE_DIAL_TARGETS:
            for fn in p385.FX6_ASSIGNABLE_DIAL_OPTIONS:
                res = p385.simulate_89b_dial_customize_5item_mydial3_funcring_and_fx6_dials(
                    operation="fx6_assignable_dial_nd_filter_vs_multi_function_dial",
                    body_model=p385.BODY_MODEL_FX6,
                    fx6_dial_node=node,
                    fx6_dial_function=fn,
                )
                self.assertTrue(res.allowed)
                self.assertTrue(res.fx6_nd_filter_allowed_on_node)

    def test_55_89b_fx6_multi_function_dial_excludes_nd_filter(self) -> None:
        res = p385.simulate_89b_dial_customize_5item_mydial3_funcring_and_fx6_dials(
            operation="fx6_assignable_dial_nd_filter_vs_multi_function_dial",
            body_model=p385.BODY_MODEL_FX6,
            fx6_dial_node="Multi Function Dial",
            fx6_dial_function="ND Filter",
        )
        self.assertFalse(res.allowed)
        self.assertEqual(res.errno, p385.EOPNOTSUPP_ERRNO)
        self.assertFalse(res.fx6_nd_filter_allowed_on_node)

    def test_56_89b_fx6_multi_function_dial_disabled_while_menu_open(self) -> None:
        res = p385.simulate_89b_dial_customize_5item_mydial3_funcring_and_fx6_dials(
            operation="fx6_assignable_dial_nd_filter_vs_multi_function_dial",
            body_model=p385.BODY_MODEL_FX6,
            fx6_dial_node="Multi Function Dial",
            fx6_dial_function="IRIS",
            fx6_menu_open=True,
        )
        self.assertFalse(res.allowed)
        self.assertEqual(res.errno, p385.EBUSY_ERRNO)
        self.assertTrue(res.fx6_menu_open_dial_blocked)

    def test_57_89b_fx6_multi_function_dial_all_5_valid_options(self) -> None:
        for fn in p385.FX6_MULTI_FUNCTION_DIAL_OPTIONS:
            res = p385.simulate_89b_dial_customize_5item_mydial3_funcring_and_fx6_dials(
                operation="fx6_assignable_dial_nd_filter_vs_multi_function_dial",
                body_model=p385.BODY_MODEL_FX6,
                fx6_dial_node="Multi Function Dial",
                fx6_dial_function=fn,
            )
            self.assertTrue(res.allowed)

    def test_58_89b_invalid_dial_customize_or_fx6_node_einval(self) -> None:
        r1 = p385.simulate_89b_dial_customize_5item_mydial3_funcring_and_fx6_dials(
            operation="fx3_dial_customize_5item_3dial_boundary_and_dormant_block",
            dial_customize_item="Bogus Item",
        )
        self.assertEqual(r1.errno, p385.EINVAL_ERRNO)
        r2 = p385.simulate_89b_dial_customize_5item_mydial3_funcring_and_fx6_dials(
            operation="fx6_assignable_dial_nd_filter_vs_multi_function_dial",
            body_model=p385.BODY_MODEL_FX6,
            fx6_dial_node="Unknown Dial",
        )
        self.assertEqual(r2.errno, p385.EINVAL_ERRNO)

    def test_59_89b_invalid_mydial_or_func_ring_einval(self) -> None:
        r1 = p385.simulate_89b_dial_customize_5item_mydial3_funcring_and_fx6_dials(
            operation="fx3_mydial_1_3_recall_skip_empty_and_lock_temp_unlock",
            my_dial_bank="My Dial 4",
        )
        self.assertEqual(r1.errno, p385.EINVAL_ERRNO)
        r2 = p385.simulate_89b_dial_customize_5item_mydial3_funcring_and_fx6_dials(
            operation="fx3_function_ring_lens_power_focus_and_apsc_s35",
            function_ring_mode="Zoom",
        )
        self.assertEqual(r2.errno, p385.EINVAL_ERRNO)

    def test_60_89b_invalid_operation_raises(self) -> None:
        with self.assertRaises(p385.Stage89Phase385Error):
            p385.simulate_89b_dial_customize_5item_mydial3_funcring_and_fx6_dials(operation="bad")

    def test_61_89b_to_dict_serializes_cleanly(self) -> None:
        res = p385.simulate_89b_dial_customize_5item_mydial3_funcring_and_fx6_dials(
            operation="fx3_mydial_1_3_recall_skip_empty_and_lock_temp_unlock",
            my_dial_recall_mode="Cycle",
        )
        self.assertIn("My Dial 3", json.dumps(res.to_dict()))

    def test_62_89b_orchestrator_metrics_alignment(self) -> None:
        rep = p385.run_phase385_realhw_zoomspeed_mydial3_funcring_hdmi4kout_sdi12g_coemulation(
            work_root=None
        )
        s = rep["submodel_89b_dial_customize_5item_mydial3_funcring_fx6_dials"]
        self.assertTrue(s["passed"])
        self.assertEqual(s["fx3_dial_customize_exact_items_count"], 5)
        self.assertEqual(s["fx3_physical_dials_count"], 3)
        self.assertEqual(s["fx3_my_dial_banks_count"], 3)
        self.assertEqual(s["fx3_dormant_dial_exposed_events"], 0)
        self.assertEqual(s["fx6_assignable_dial_options_count"], 7)
        self.assertEqual(s["fx6_multi_function_dial_options_count"], 5)

    # =========================================================================
    # Tests 63..84: Sub-Model 89C — [Operation Customize], Zero-EVF & LUT/GDA
    # =========================================================================

    def test_63_89c_diff_set_exact_8_items_resist_cam_reset(self) -> None:
        self.assertEqual(len(p385.FX3_DIFF_SET_EXACT_8_ITEMS), 8)
        res = p385.simulate_89c_op_customize_diffset8_disp4_zeroevf_lut_and_fx6_60disp(
            operation="fx3_diff_set_8item_bitmask_pp_anti_init_and_fn_12x2",
            diff_set_checked_items=p385.FX3_DIFF_SET_EXACT_8_ITEMS,
            camera_settings_reset_triggered=True,
        )
        self.assertTrue(res.allowed)
        self.assertTrue(res.diff_set_survived_cam_reset)
        self.assertEqual(len(res.diff_set_checked_items), 8)

    def test_64_89c_g99_picture_profile_resists_both_reset_and_initialize(self) -> None:
        res = p385.simulate_89c_op_customize_diffset8_disp4_zeroevf_lut_and_fx6_60disp(
            operation="fx3_diff_set_8item_bitmask_pp_anti_init_and_fn_12x2",
            diff_set_checked_items=p385.FX3_DIFF_SET_EXACT_8_ITEMS,
            initialize_triggered=True,
        )
        self.assertTrue(res.allowed)
        self.assertEqual(res.diff_set_checked_items, ("Picture Profile",))
        self.assertTrue(res.picture_profile_survived_initialize)
        self.assertTrue(res.g99_pp_anti_init_reconciled)

    def test_65_89c_shutter_mode_angle_forces_still_movie_shutter_split(self) -> None:
        res = p385.simulate_89c_op_customize_diffset8_disp4_zeroevf_lut_and_fx6_60disp(
            operation="fx3_diff_set_8item_bitmask_pp_anti_init_and_fn_12x2",
            diff_set_checked_items=(),
            shutter_mode="Angle",
        )
        self.assertTrue(res.allowed)
        self.assertTrue(res.shutter_angle_forces_still_movie_split)

    def test_66_89c_fn_menu_12x2_independent_and_rejects_all_not_set(self) -> None:
        ok = p385.simulate_89c_op_customize_diffset8_disp4_zeroevf_lut_and_fx6_60disp(
            operation="fx3_diff_set_8item_bitmask_pp_anti_init_and_fn_12x2",
            shoot_mode="Movie",
            fn_still_assigned_count=0,
            fn_movie_assigned_count=12,
            fn_button_pressed=True,
        )
        self.assertTrue(ok.allowed)
        self.assertEqual(ok.fn_still_slots_count, 12)
        self.assertEqual(ok.fn_movie_slots_count, 12)
        self.assertTrue(ok.fn_slots_decoupled_from_diff_set)

        emp = p385.simulate_89c_op_customize_diffset8_disp4_zeroevf_lut_and_fx6_60disp(
            operation="fx3_diff_set_8item_bitmask_pp_anti_init_and_fn_12x2",
            shoot_mode="Movie",
            fn_still_assigned_count=12,
            fn_movie_assigned_count=0,
            fn_button_pressed=True,
        )
        self.assertFalse(emp.allowed)
        self.assertEqual(emp.errno, p385.EBUSY_ERRNO)
        self.assertTrue(emp.empty_fn_menu_rejected)

    def test_67_89c_disp_exact_4_shooting_pages_and_3_playback_pages(self) -> None:
        for page in p385.FX3_DISP_SHOOT_EXACT_4_PAGES:
            r = p385.simulate_89c_op_customize_diffset8_disp4_zeroevf_lut_and_fx6_60disp(
                operation="fx3_disp_4pages_and_zero_evf_finder_monitor_dormancy",
                disp_page_requested=page,
                is_playback_mode=False,
            )
            self.assertTrue(r.allowed)
            self.assertEqual(r.disp_shoot_pages_count, 4)

        for page in p385.FX3_DISP_PLAYBACK_EXACT_3_PAGES:
            r = p385.simulate_89c_op_customize_diffset8_disp4_zeroevf_lut_and_fx6_60disp(
                operation="fx3_disp_4pages_and_zero_evf_finder_monitor_dormancy",
                disp_page_requested=page,
                is_playback_mode=True,
            )
            self.assertTrue(r.allowed)
            self.assertEqual(r.disp_playback_pages_count, 3)

    def test_68_89c_zero_evf_firewall_blocks_all_dormant_disp_and_finder_items(self) -> None:
        for item in p385.FX3_DORMANT_EVF_AND_DISP_ITEMS:
            res = p385.simulate_89c_op_customize_diffset8_disp4_zeroevf_lut_and_fx6_60disp(
                operation="fx3_disp_4pages_and_zero_evf_finder_monitor_dormancy",
                disp_page_requested=item,
            )
            self.assertFalse(res.allowed, f"Expected dormant EVF item blocked: {item}")
            self.assertEqual(res.errno, p385.EOPNOTSUPP_ERRNO)
            self.assertTrue(res.dormant_evf_or_disp_blocked)
            self.assertFalse(res.fx3_has_builtin_evf)

    def test_69_89c_disp_screen_set_resists_cam_reset(self) -> None:
        res = p385.simulate_89c_op_customize_diffset8_disp4_zeroevf_lut_and_fx6_60disp(
            operation="fx3_disp_4pages_and_zero_evf_finder_monitor_dormancy",
            disp_page_requested="Level",
            camera_settings_reset_triggered=True,
        )
        self.assertTrue(res.allowed)
        self.assertTrue(res.diff_set_survived_cam_reset)

    def test_70_89c_select_lut_3_presets_plus_16_user_slots_override_gamma_assist_in_log(self) -> None:
        self.assertEqual(len(p385.FX3_SELECT_LUT_PRESETS), 3)
        self.assertEqual(len(p385.FX3_SELECT_LUT_USER_SLOTS), 16)
        self.assertEqual(p385.FX3_SELECT_LUT_DEFAULT, "s709")
        for mode in ("Flexible ISO", "Cine EI", "Cine EI Quick"):
            for slot in ("s709", "709(800%)", "S-Log3", "User1", "User16"):
                res = p385.simulate_89c_op_customize_diffset8_disp4_zeroevf_lut_and_fx6_60disp(
                    operation="fx3_select_lut_vs_gamma_display_assist_routing",
                    shoot_mode="Movie",
                    log_shooting_mode=mode,
                    select_lut_slot=slot,
                    display_lut_on=True,
                    gamma_display_assist_on=True,
                )
                self.assertTrue(res.allowed)
                self.assertTrue(res.gamma_assist_overridden_by_select_lut)
                self.assertFalse(res.gamma_assist_active)
                self.assertTrue(res.g132_log_lut_gamma_split_reconciled)

    def test_71_89c_g132_still_log_and_non_log_pp_use_gamma_display_assist(self) -> None:
        r_still = p385.simulate_89c_op_customize_diffset8_disp4_zeroevf_lut_and_fx6_60disp(
            operation="fx3_select_lut_vs_gamma_display_assist_routing",
            shoot_mode="Still",
            log_shooting_mode="Flexible ISO",
            gamma_display_assist_on=True,
        )
        self.assertTrue(r_still.allowed)
        self.assertTrue(r_still.gamma_assist_active)
        self.assertFalse(r_still.gamma_assist_overridden_by_select_lut)

        r_pp = p385.simulate_89c_op_customize_diffset8_disp4_zeroevf_lut_and_fx6_60disp(
            operation="fx3_select_lut_vs_gamma_display_assist_routing",
            shoot_mode="Movie",
            log_shooting_mode="Off",
            picture_profile_is_log_or_hlg=True,
            gamma_display_assist_on=True,
            gamma_display_assist_type="HLG(BT.2020)",
        )
        self.assertTrue(r_pp.allowed)
        self.assertTrue(r_pp.gamma_assist_active)

    def test_72_89c_fx6_60route_display_on_off_rec_play_and_video_signal_monitor(self) -> None:
        for rmode in p385.FX6_REC_PLAY_STATUS_DISPLAY_MODES:
            for vsm in p385.FX6_VIDEO_SIGNAL_MONITORS:
                res = p385.simulate_89c_op_customize_diffset8_disp4_zeroevf_lut_and_fx6_60disp(
                    operation="fx6_60route_display_on_off_and_cine_ei_gamma_assist_lock",
                    body_model=p385.BODY_MODEL_FX6,
                    fx6_rec_play_status_mode=rmode,
                    fx6_video_signal_monitor=vsm,
                )
                self.assertTrue(res.allowed)
                self.assertEqual(res.fx6_display_elf_routes_count, 60)
                self.assertEqual(res.fx6_user_menu_display_toggles_count, 104)

    def test_73_89c_fx6_gamma_display_assist_locked_off_in_cine_ei_allowed_in_custom_hlg(self) -> None:
        blk = p385.simulate_89c_op_customize_diffset8_disp4_zeroevf_lut_and_fx6_60disp(
            operation="fx6_60route_display_on_off_and_cine_ei_gamma_assist_lock",
            body_model=p385.BODY_MODEL_FX6,
            fx6_shooting_mode="Cine EI",
            fx6_gamma_display_assist_requested=True,
        )
        self.assertFalse(blk.allowed)
        self.assertEqual(blk.errno, p385.EOPNOTSUPP_ERRNO)
        self.assertTrue(blk.fx6_cine_ei_gamma_assist_locked_off)

        ok = p385.simulate_89c_op_customize_diffset8_disp4_zeroevf_lut_and_fx6_60disp(
            operation="fx6_60route_display_on_off_and_cine_ei_gamma_assist_lock",
            body_model=p385.BODY_MODEL_FX6,
            fx6_shooting_mode="Custom",
            fx6_target_display="HDR(HLG)",
            fx6_gamma_display_assist_requested=True,
        )
        self.assertTrue(ok.allowed)

    def test_74_89c_invalid_diff_set_item_or_fn_count_einval(self) -> None:
        r1 = p385.simulate_89c_op_customize_diffset8_disp4_zeroevf_lut_and_fx6_60disp(
            operation="fx3_diff_set_8item_bitmask_pp_anti_init_and_fn_12x2",
            diff_set_checked_items=("Zoom Range",),
        )
        self.assertEqual(r1.errno, p385.EINVAL_ERRNO)
        r2 = p385.simulate_89c_op_customize_diffset8_disp4_zeroevf_lut_and_fx6_60disp(
            operation="fx3_diff_set_8item_bitmask_pp_anti_init_and_fn_12x2",
            fn_still_assigned_count=13,
        )
        self.assertEqual(r2.errno, p385.EINVAL_ERRNO)

    def test_75_89c_invalid_select_lut_or_gamma_type_einval(self) -> None:
        r1 = p385.simulate_89c_op_customize_diffset8_disp4_zeroevf_lut_and_fx6_60disp(
            operation="fx3_select_lut_vs_gamma_display_assist_routing",
            select_lut_slot="User17",
        )
        self.assertEqual(r1.errno, p385.EINVAL_ERRNO)
        r2 = p385.simulate_89c_op_customize_diffset8_disp4_zeroevf_lut_and_fx6_60disp(
            operation="fx3_select_lut_vs_gamma_display_assist_routing",
            gamma_display_assist_type="S-Log2",
        )
        self.assertEqual(r2.errno, p385.EINVAL_ERRNO)

    def test_76_89c_invalid_disp_page_or_fx6_vsm_einval(self) -> None:
        r1 = p385.simulate_89c_op_customize_diffset8_disp4_zeroevf_lut_and_fx6_60disp(
            operation="fx3_disp_4pages_and_zero_evf_finder_monitor_dormancy",
            disp_page_requested="Zebra Page",
        )
        self.assertEqual(r1.errno, p385.EINVAL_ERRNO)
        r2 = p385.simulate_89c_op_customize_diffset8_disp4_zeroevf_lut_and_fx6_60disp(
            operation="fx6_60route_display_on_off_and_cine_ei_gamma_assist_lock",
            body_model=p385.BODY_MODEL_FX6,
            fx6_video_signal_monitor="FalseColor",
        )
        self.assertEqual(r2.errno, p385.EINVAL_ERRNO)

    def test_77_89c_invalid_operation_raises(self) -> None:
        with self.assertRaises(p385.Stage89Phase385Error):
            p385.simulate_89c_op_customize_diffset8_disp4_zeroevf_lut_and_fx6_60disp(operation="bad")

    def test_78_89c_to_dict_serializes_cleanly(self) -> None:
        res = p385.simulate_89c_op_customize_diffset8_disp4_zeroevf_lut_and_fx6_60disp(
            operation="fx3_diff_set_8item_bitmask_pp_anti_init_and_fn_12x2",
            initialize_triggered=True,
        )
        self.assertIn("Picture Profile", json.dumps(res.to_dict()))

    def test_79_89c_orchestrator_metrics_alignment(self) -> None:
        rep = p385.run_phase385_realhw_zoomspeed_mydial3_funcring_hdmi4kout_sdi12g_coemulation(
            work_root=None
        )
        s = rep["submodel_89c_op_customize_diffset8_disp4_zeroevf_lut_fx6_60disp"]
        self.assertTrue(s["passed"])
        self.assertEqual(s["fx3_diff_set_items_count"], 8)
        self.assertTrue(s["fx3_g99_pp_anti_init_erratum_reconciled"])
        self.assertEqual(s["fx3_fn_menu_total_slots"], 24)
        self.assertEqual(s["fx3_disp_shoot_pages_count"], 4)
        self.assertFalse(s["fx3_has_builtin_evf"])
        self.assertEqual(s["fx3_dormant_evf_exposed_events"], 0)
        self.assertEqual(s["fx3_select_lut_total_slots"], 19)
        self.assertTrue(s["fx3_g132_log_lut_gamma_split_reconciled"])
        self.assertEqual(s["fx6_display_elf_routes_count"], 60)

    # =========================================================================
    # Tests 80..104: Sub-Model 89D — [External Output] HDMI 4K vs FX6 12G-SDI
    # =========================================================================

    def test_80_89d_hdmi_resolution_exact_4_modes_and_blocks_720p(self) -> None:
        self.assertEqual(len(p385.FX3_HDMI_RESOLUTION_EXACT_4_MODES), 4)
        for res_mode in p385.FX3_HDMI_RESOLUTION_EXACT_4_MODES:
            r = p385.simulate_89d_external_output_hdmi4k_3typos_and_fx6_12gsdi_dual(
                operation="fx3_hdmi_resolution_4modes_4k_output_set_and_dormant_block",
                hdmi_resolution=res_mode,
            )
            self.assertTrue(r.allowed)
            self.assertEqual(r.hdmi_resolution_exposed_count, 4)

        for bad in p385.FX3_DORMANT_HDMI_RESOLUTIONS:
            r = p385.simulate_89d_external_output_hdmi4k_3typos_and_fx6_12gsdi_dual(
                operation="fx3_hdmi_resolution_4modes_4k_output_set_and_dormant_block",
                hdmi_resolution=bad,
            )
            self.assertFalse(r.allowed)
            self.assertEqual(r.errno, p385.EOPNOTSUPP_ERRNO)
            self.assertTrue(r.dormant_hdmi_720p_blocked)

    def test_81_89d_4k_output_set_exact_6_10bit_422_modes_and_24_00p_reboot(self) -> None:
        self.assertEqual(len(p385.FX3_4K_OUTPUT_SET_EXACT_6_MODES), 6)
        for mode in p385.FX3_4K_OUTPUT_SET_EXACT_6_MODES:
            r = p385.simulate_89d_external_output_hdmi4k_3typos_and_fx6_12gsdi_dual(
                operation="fx3_hdmi_resolution_4modes_4k_output_set_and_dormant_block",
                rec_media_dur_hdmi_output="Off(HDMI Only)",
                hdmi_4k_output_set=mode,
            )
            self.assertTrue(r.allowed)
            self.assertEqual(r.hdmi_4k_chroma_spec, "10bit 4:2:2")
            self.assertEqual(r.reboot_required_for_24_00p, mode == "24.00p 10bit")

    def test_82_89d_4k_output_set_blocks_420_and_dormant_24_00p_8bit(self) -> None:
        r_420 = p385.simulate_89d_external_output_hdmi4k_3typos_and_fx6_12gsdi_dual(
            operation="fx3_hdmi_resolution_4modes_4k_output_set_and_dormant_block",
            rec_media_dur_hdmi_output="Off(HDMI Only)",
            chroma_requested="8bit 4:2:0",
        )
        self.assertFalse(r_420.allowed)
        self.assertEqual(r_420.errno, p385.EOPNOTSUPP_ERRNO)
        self.assertTrue(r_420.dormant_420_or_8bit_blocked)

        r_8b = p385.simulate_89d_external_output_hdmi4k_3typos_and_fx6_12gsdi_dual(
            operation="fx3_hdmi_resolution_4modes_4k_output_set_and_dormant_block",
            rec_media_dur_hdmi_output="Off(HDMI Only)",
            hdmi_4k_output_set="24.00p 8bit",
        )
        self.assertFalse(r_8b.allowed)
        self.assertEqual(r_8b.errno, p385.EOPNOTSUPP_ERRNO)
        self.assertTrue(r_8b.dormant_420_or_8bit_blocked)

    def test_83_89d_24p_60p_output_100pct_dormant_0_elf_hits(self) -> None:
        self.assertEqual(p385.FX3_DORMANT_24P_60P_OUTPUT_ELF_HITS, 0)
        res = p385.simulate_89d_external_output_hdmi4k_3typos_and_fx6_12gsdi_dual(
            operation="fx3_hdmi_resolution_4modes_4k_output_set_and_dormant_block",
            legacy_24p_60p_output_requested=True,
        )
        self.assertFalse(res.allowed)
        self.assertEqual(res.errno, p385.EOPNOTSUPP_ERRNO)
        self.assertTrue(res.dormant_24p_60p_output_blocked)

    def test_84_89d_log_or_pplut_internal_rec_downshifts_hdmi_to_1080p(self) -> None:
        for out_res in ("Auto", "2160p"):
            res = p385.simulate_89d_external_output_hdmi4k_3typos_and_fx6_12gsdi_dual(
                operation="fx3_hdmi_resolution_4modes_4k_output_set_and_dormant_block",
                rec_media_dur_hdmi_output="On",
                output_resolution=out_res,
                log_or_pplut_active=True,
            )
            self.assertTrue(res.allowed)
            self.assertEqual(res.effective_hdmi_resolution, "1080p")
            self.assertTrue(res.hdmi_log_1080_downshifted)

    def test_85_89d_apsc_s35_locks_4k_output_set_and_sq_locks_rec_media_on(self) -> None:
        r_apsc = p385.simulate_89d_external_output_hdmi4k_3typos_and_fx6_12gsdi_dual(
            operation="fx3_hdmi_resolution_4modes_4k_output_set_and_dormant_block",
            rec_media_dur_hdmi_output="Off(HDMI Only)",
            apsc_s35_on=True,
        )
        self.assertFalse(r_apsc.allowed)
        self.assertEqual(r_apsc.errno, p385.EOPNOTSUPP_ERRNO)
        self.assertTrue(r_apsc.apsc_s35_blocks_4k_output_set)

        r_sq = p385.simulate_89d_external_output_hdmi4k_3typos_and_fx6_12gsdi_dual(
            operation="fx3_hdmi_resolution_4modes_4k_output_set_and_dormant_block",
            shoot_mode="S&Q",
            rec_media_dur_hdmi_output="Off(HDMI Only)",
        )
        self.assertFalse(r_sq.allowed)
        self.assertEqual(r_sq.errno, p385.EOPNOTSUPP_ERRNO)

    def test_86_89d_external_output_resists_cam_reset_and_resets_on_init(self) -> None:
        r_rst = p385.simulate_89d_external_output_hdmi4k_3typos_and_fx6_12gsdi_dual(
            operation="fx3_hdmi_resolution_4modes_4k_output_set_and_dormant_block",
            hdmi_resolution="1080p",
            hdmi_4k_output_set="23.98p 10bit",
            camera_settings_reset_triggered=True,
        )
        self.assertTrue(r_rst.allowed)
        self.assertEqual(r_rst.hdmi_resolution, "1080p")
        self.assertTrue(r_rst.external_output_resists_cam_reset)

        r_init = p385.simulate_89d_external_output_hdmi4k_3typos_and_fx6_12gsdi_dual(
            operation="fx3_hdmi_resolution_4modes_4k_output_set_and_dormant_block",
            hdmi_resolution="1080p",
            hdmi_4k_output_set="24.00p 10bit",
            initialize_triggered=True,
        )
        self.assertTrue(r_init.allowed)
        self.assertEqual(r_init.hdmi_resolution, "Auto")
        self.assertEqual(r_init.hdmi_4k_output_set, "59.94p 10bit")

    def test_87_89d_hdmi_info_display_on_blacks_out_lcd_only_when_rec_media_on_and_raw_off(self) -> None:
        r_blk = p385.simulate_89d_external_output_hdmi4k_3typos_and_fx6_12gsdi_dual(
            operation="fx3_hdmi_info_blackout_raw_rec_ctrl_4ch_and_3_elf_typos",
            hdmi_info_display_setting="On",
            rec_media_dur_hdmi_output="On",
            hdmi_raw_output_on=False,
            target_slot="Slot 2",
        )
        self.assertTrue(r_blk.allowed)
        self.assertTrue(r_blk.internal_lcd_blacked_out)
        self.assertEqual(r_blk.effective_hdmi_info_display, "On")

        r_hdmi_only = p385.simulate_89d_external_output_hdmi4k_3typos_and_fx6_12gsdi_dual(
            operation="fx3_hdmi_info_blackout_raw_rec_ctrl_4ch_and_3_elf_typos",
            hdmi_info_display_setting="On",
            rec_media_dur_hdmi_output="Off(HDMI Only)",
            hdmi_raw_output_on=False,
        )
        self.assertTrue(r_hdmi_only.allowed)
        self.assertFalse(r_hdmi_only.internal_lcd_blacked_out)
        self.assertEqual(r_hdmi_only.effective_hdmi_info_display, "Off")

        r_raw = p385.simulate_89d_external_output_hdmi4k_3typos_and_fx6_12gsdi_dual(
            operation="fx3_hdmi_info_blackout_raw_rec_ctrl_4ch_and_3_elf_typos",
            hdmi_info_display_setting="On",
            rec_media_dur_hdmi_output="On",
            hdmi_raw_output_on=True,
            log_shooting_on=True,
            target_slot="Slot 2",
        )
        self.assertTrue(r_raw.allowed)
        self.assertFalse(r_raw.internal_lcd_blacked_out)
        self.assertEqual(r_raw.effective_hdmi_info_display, "Off")

    def test_88_89d_rec_control_depends_on_tc_output_on_and_tc_blocked_in_sq(self) -> None:
        no_tc = p385.simulate_89d_external_output_hdmi4k_3typos_and_fx6_12gsdi_dual(
            operation="fx3_hdmi_info_blackout_raw_rec_ctrl_4ch_and_3_elf_typos",
            rec_media_dur_hdmi_output="Off(HDMI Only)",
            time_code_output_on=False,
            rec_control_on=True,
        )
        self.assertFalse(no_tc.allowed)
        self.assertEqual(no_tc.errno, p385.EOPNOTSUPP_ERRNO)
        self.assertTrue(no_tc.rec_control_missing_tc_blocked)

        ok_tc = p385.simulate_89d_external_output_hdmi4k_3typos_and_fx6_12gsdi_dual(
            operation="fx3_hdmi_info_blackout_raw_rec_ctrl_4ch_and_3_elf_typos",
            rec_media_dur_hdmi_output="Off(HDMI Only)",
            time_code_output_on=True,
            rec_control_on=True,
        )
        self.assertTrue(ok_tc.allowed)

        sq_tc = p385.simulate_89d_external_output_hdmi4k_3typos_and_fx6_12gsdi_dual(
            operation="fx3_hdmi_info_blackout_raw_rec_ctrl_4ch_and_3_elf_typos",
            shoot_mode="S&Q",
            rec_media_dur_hdmi_output="On",
            time_code_output_on=True,
            target_slot="Slot 2",
        )
        self.assertFalse(sq_tc.allowed)
        self.assertEqual(sq_tc.errno, p385.EOPNOTSUPP_ERRNO)

    def test_89_89d_hdmi_raw_requires_movie_and_log_shooting(self) -> None:
        r_nolog = p385.simulate_89d_external_output_hdmi4k_3typos_and_fx6_12gsdi_dual(
            operation="fx3_hdmi_info_blackout_raw_rec_ctrl_4ch_and_3_elf_typos",
            shoot_mode="Movie",
            hdmi_raw_output_on=True,
            log_shooting_on=False,
            rec_media_dur_hdmi_output="Off(HDMI Only)",
        )
        self.assertFalse(r_nolog.allowed)
        self.assertEqual(r_nolog.errno, p385.EOPNOTSUPP_ERRNO)

        r_still = p385.simulate_89d_external_output_hdmi4k_3typos_and_fx6_12gsdi_dual(
            operation="fx3_hdmi_info_blackout_raw_rec_ctrl_4ch_and_3_elf_typos",
            shoot_mode="Still",
            hdmi_raw_output_on=True,
            log_shooting_on=True,
            rec_media_dur_hdmi_output="Off(HDMI Only)",
        )
        self.assertFalse(r_still.allowed)
        self.assertEqual(r_still.errno, p385.EOPNOTSUPP_ERRNO)

    def test_90_89d_4ch_audio_output_and_3_sony_elf_typos(self) -> None:
        for pair in p385.FX3_4CH_AUDIO_OUTPUT_OPTIONS:
            res = p385.simulate_89d_external_output_hdmi4k_3typos_and_fx6_12gsdi_dual(
                operation="fx3_hdmi_info_blackout_raw_rec_ctrl_4ch_and_3_elf_typos",
                rec_media_dur_hdmi_output="Off(HDMI Only)",
                audio_4ch_output_pair=pair,
            )
            self.assertTrue(res.allowed)
            self.assertEqual(res.audio_4ch_output_pair, pair)
            self.assertEqual(res.sony_elf_3_typos, p385.FX3_SONY_ELF_3_TYPOS)

    def test_91_89d_tier0_slot1_erofs_blocks_hdmi_rec_media_write(self) -> None:
        res = p385.simulate_89d_external_output_hdmi4k_3typos_and_fx6_12gsdi_dual(
            operation="fx3_hdmi_info_blackout_raw_rec_ctrl_4ch_and_3_elf_typos",
            rec_media_dur_hdmi_output="On",
            target_slot="Slot 1",
        )
        self.assertFalse(res.allowed)
        self.assertEqual(res.errno, p385.EROFS_ERRNO)
        self.assertTrue(res.slot1_erofs_blocked)
        self.assertEqual(res.slot1_writes, 0)
        self.assertEqual(res.slot1_sector_writes, 0)
        self.assertEqual(res.slot1_data_sector_writes, 0)

    def test_92_89d_non_sandbox_slot2_write_blocked_erofs(self) -> None:
        res = p385.simulate_89d_external_output_hdmi4k_3typos_and_fx6_12gsdi_dual(
            operation="fx3_hdmi_info_blackout_raw_rec_ctrl_4ch_and_3_elf_typos",
            rec_media_dur_hdmi_output="On",
            target_slot="Slot 2",
            simulated_sandbox=False,
        )
        self.assertFalse(res.allowed)
        self.assertEqual(res.errno, p385.EROFS_ERRNO)

    def test_93_89d_fx6_sdi_raw_plus_4k_hdmi_simultaneous_and_lcd_always_on(self) -> None:
        for codec in ("RAW", "RAW & XAVC-I", "XAVC-I", "XAVC-L"):
            res = p385.simulate_89d_external_output_hdmi4k_3typos_and_fx6_12gsdi_dual(
                operation="fx6_12gsdi_hdmi_dual_pipeline_raw_sq60_cap_and_rec_ctrl",
                body_model=p385.BODY_MODEL_FX6,
                fx6_codec=codec,
                fx6_sdi_format="4096x2160P",
                fx6_hdmi_format="4096x2160P",
                fx6_rec_control_mode="Parallel Rec",
            )
            self.assertTrue(res.allowed)
            self.assertFalse(res.internal_lcd_blacked_out)
            self.assertEqual(res.fx6_sdi_hdmi_matrix_entries_count, 25)

    def test_94_89d_fx6_hdmi_raw_4240x2392_locks_sdi_1080_and_excludes_24hz(self) -> None:
        r_4ksdi = p385.simulate_89d_external_output_hdmi4k_3typos_and_fx6_12gsdi_dual(
            operation="fx6_12gsdi_hdmi_dual_pipeline_raw_sq60_cap_and_rec_ctrl",
            body_model=p385.BODY_MODEL_FX6,
            fx6_codec="RAW(HDMI)",
            fx6_sdi_format="3840x2160P",
        )
        self.assertFalse(r_4ksdi.allowed)
        self.assertEqual(r_4ksdi.errno, p385.EOPNOTSUPP_ERRNO)
        self.assertTrue(r_4ksdi.fx6_hdmi_raw_locks_sdi_1080)

        r_24hz = p385.simulate_89d_external_output_hdmi4k_3typos_and_fx6_12gsdi_dual(
            operation="fx6_12gsdi_hdmi_dual_pipeline_raw_sq60_cap_and_rec_ctrl",
            body_model=p385.BODY_MODEL_FX6,
            fx6_codec="RAW(HDMI)",
            fx6_sdi_format="1920x1080P (Level A)",
            fx6_system_freq_hz=24.0,
        )
        self.assertFalse(r_24hz.allowed)
        self.assertEqual(r_24hz.errno, p385.EOPNOTSUPP_ERRNO)

        r_ok = p385.simulate_89d_external_output_hdmi4k_3typos_and_fx6_12gsdi_dual(
            operation="fx6_12gsdi_hdmi_dual_pipeline_raw_sq60_cap_and_rec_ctrl",
            body_model=p385.BODY_MODEL_FX6,
            fx6_codec="RAW(HDMI) & XAVC-I",
            fx6_sdi_format="1920x1080P (Level A)",
            fx6_system_freq_hz=59.94,
        )
        self.assertTrue(r_ok.allowed)
        self.assertEqual(r_ok.hdmi_raw_resolution, "4240x2392")

    def test_95_89d_fx6_hdmi_raw_blocks_sq_motion(self) -> None:
        res = p385.simulate_89d_external_output_hdmi4k_3typos_and_fx6_12gsdi_dual(
            operation="fx6_12gsdi_hdmi_dual_pipeline_raw_sq60_cap_and_rec_ctrl",
            body_model=p385.BODY_MODEL_FX6,
            fx6_codec="RAW(HDMI)",
            fx6_sdi_format="1920x1080P (Level A)",
            fx6_sq_on=True,
            fx6_sq_fps=60,
        )
        self.assertFalse(res.allowed)
        self.assertEqual(res.errno, p385.EOPNOTSUPP_ERRNO)

    def test_96_89d_fx6_sq_gt_60fps_with_sdi_or_raw_caps_hdmi_to_le_1080p(self) -> None:
        blk = p385.simulate_89d_external_output_hdmi4k_3typos_and_fx6_12gsdi_dual(
            operation="fx6_12gsdi_hdmi_dual_pipeline_raw_sq60_cap_and_rec_ctrl",
            body_model=p385.BODY_MODEL_FX6,
            fx6_codec="XAVC-I",
            fx6_sdi_enabled=True,
            fx6_sq_on=True,
            fx6_sq_fps=120,
            fx6_hdmi_format="3840x2160P",
        )
        self.assertFalse(blk.allowed)
        self.assertEqual(blk.errno, p385.EOPNOTSUPP_ERRNO)
        self.assertTrue(blk.fx6_sq_gt60_caps_hdmi_1080)

        ok = p385.simulate_89d_external_output_hdmi4k_3typos_and_fx6_12gsdi_dual(
            operation="fx6_12gsdi_hdmi_dual_pipeline_raw_sq60_cap_and_rec_ctrl",
            body_model=p385.BODY_MODEL_FX6,
            fx6_codec="XAVC-I",
            fx6_sdi_enabled=True,
            fx6_sq_on=True,
            fx6_sq_fps=120,
            fx6_hdmi_format="1920x1080P",
        )
        self.assertTrue(ok.allowed)
        self.assertTrue(ok.fx6_sq_gt60_caps_hdmi_1080)

    def test_97_89d_fx6_sdi_hdmi_rec_control_all_3_modes(self) -> None:
        self.assertEqual(len(p385.FX6_SDI_HDMI_REC_CONTROL_3_MODES), 3)
        for rc_mode in p385.FX6_SDI_HDMI_REC_CONTROL_3_MODES:
            res = p385.simulate_89d_external_output_hdmi4k_3typos_and_fx6_12gsdi_dual(
                operation="fx6_12gsdi_hdmi_dual_pipeline_raw_sq60_cap_and_rec_ctrl",
                body_model=p385.BODY_MODEL_FX6,
                fx6_rec_control_mode=rc_mode,
            )
            self.assertTrue(res.allowed)
            self.assertEqual(res.fx6_rec_control_mode, rc_mode)

    def test_98_89d_invalid_hdmi_resolution_or_4k_output_set_einval(self) -> None:
        r1 = p385.simulate_89d_external_output_hdmi4k_3typos_and_fx6_12gsdi_dual(
            operation="fx3_hdmi_resolution_4modes_4k_output_set_and_dormant_block",
            hdmi_resolution="8K",
        )
        self.assertEqual(r1.errno, p385.EINVAL_ERRNO)
        r2 = p385.simulate_89d_external_output_hdmi4k_3typos_and_fx6_12gsdi_dual(
            operation="fx3_hdmi_resolution_4modes_4k_output_set_and_dormant_block",
            hdmi_4k_output_set="120p 10bit",
        )
        self.assertEqual(r2.errno, p385.EINVAL_ERRNO)

    def test_99_89d_invalid_4ch_audio_or_hdmi_info_einval(self) -> None:
        r1 = p385.simulate_89d_external_output_hdmi4k_3typos_and_fx6_12gsdi_dual(
            operation="fx3_hdmi_info_blackout_raw_rec_ctrl_4ch_and_3_elf_typos",
            audio_4ch_output_pair="CH1..CH4",
        )
        self.assertEqual(r1.errno, p385.EINVAL_ERRNO)
        r2 = p385.simulate_89d_external_output_hdmi4k_3typos_and_fx6_12gsdi_dual(
            operation="fx3_hdmi_info_blackout_raw_rec_ctrl_4ch_and_3_elf_typos",
            hdmi_info_display_setting="Auto",
        )
        self.assertEqual(r2.errno, p385.EINVAL_ERRNO)

    def test_100_89d_invalid_fx6_codec_sdi_hdmi_or_rec_ctrl_einval(self) -> None:
        for kw in (
            {"fx6_codec": "ProRes"},
            {"fx6_sdi_format": "8K"},
            {"fx6_hdmi_format": "720P"},
            {"fx6_rec_control_mode": "LANC"},
        ):
            r = p385.simulate_89d_external_output_hdmi4k_3typos_and_fx6_12gsdi_dual(
                operation="fx6_12gsdi_hdmi_dual_pipeline_raw_sq60_cap_and_rec_ctrl",
                body_model=p385.BODY_MODEL_FX6,
                **kw,
            )
            self.assertEqual(r.errno, p385.EINVAL_ERRNO)

    def test_101_89d_hdmi_info_off_keeps_internal_lcd_active(self) -> None:
        res = p385.simulate_89d_external_output_hdmi4k_3typos_and_fx6_12gsdi_dual(
            operation="fx3_hdmi_info_blackout_raw_rec_ctrl_4ch_and_3_elf_typos",
            hdmi_info_display_setting="Off",
            rec_media_dur_hdmi_output="On",
            hdmi_raw_output_on=False,
            target_slot="Slot 2",
        )
        self.assertTrue(res.allowed)
        self.assertFalse(res.internal_lcd_blacked_out)
        self.assertEqual(res.effective_hdmi_info_display, "Off")

    def test_102_89d_invalid_operation_or_body_raises(self) -> None:
        with self.assertRaises(p385.Stage89Phase385Error):
            p385.simulate_89d_external_output_hdmi4k_3typos_and_fx6_12gsdi_dual(operation="bad")
        with self.assertRaises(p385.Stage89Phase385Error):
            p385.simulate_89d_external_output_hdmi4k_3typos_and_fx6_12gsdi_dual(
                operation="fx3_hdmi_resolution_4modes_4k_output_set_and_dormant_block",
                body_model="FX9",
            )

    def test_103_89d_to_dict_serializes_cleanly(self) -> None:
        res = p385.simulate_89d_external_output_hdmi4k_3typos_and_fx6_12gsdi_dual(
            operation="fx3_hdmi_info_blackout_raw_rec_ctrl_4ch_and_3_elf_typos",
            rec_media_dur_hdmi_output="Off(HDMI Only)",
        )
        self.assertIn("BKID_APP_setting_ctrl_for_hmdi", json.dumps(res.to_dict()))

    def test_104_89d_orchestrator_metrics_alignment(self) -> None:
        rep = p385.run_phase385_realhw_zoomspeed_mydial3_funcring_hdmi4kout_sdi12g_coemulation(
            work_root=None
        )
        s = rep["submodel_89d_external_output_hdmi4k_3typos_fx6_12gsdi_dual"]
        self.assertTrue(s["passed"])
        self.assertEqual(s["fx3_hdmi_resolution_exposed_count"], 4)
        self.assertEqual(s["fx3_4k_output_set_exposed_count"], 6)
        self.assertFalse(s["fx3_4k_output_has_420_option"])
        self.assertEqual(s["fx3_dormant_24p_60p_output_elf_hits"], 0)
        self.assertEqual(s["fx3_sony_elf_typos_count"], 3)
        self.assertEqual(s["fx6_sdi_hdmi_matrix_entries_count"], 25)
        self.assertEqual(s["fx6_sdi_hdmi_rec_control_modes_count"], 3)

    # =========================================================================
    # Tests 105..112: 4-Mode Determinism, Portability, CLI & Suite 89/89 Wiring
    # =========================================================================

    def test_105_clean_room_digest_determinism_and_source_mode_distinction(self) -> None:
        r_f1 = p385.run_phase385_realhw_zoomspeed_mydial3_funcring_hdmi4kout_sdi12g_coemulation(
            force_clean_room=True
        )
        r_f2 = p385.run_phase385_realhw_zoomspeed_mydial3_funcring_hdmi4kout_sdi12g_coemulation(
            env={"FX3_FX6_FORCE_CLEAN_ROOM": "1"}
        )
        r_f3 = p385.run_phase385_realhw_zoomspeed_mydial3_funcring_hdmi4kout_sdi12g_coemulation(
            env={"FX3_CLEAN_ROOM_TEST": "1"}
        )
        self.assertEqual(r_f1["phase385_audit_digest_sha256"], r_f2["phase385_audit_digest_sha256"])
        self.assertEqual(r_f1["phase385_audit_digest_sha256"], r_f3["phase385_audit_digest_sha256"])

        r_dl1 = p385.run_phase385_realhw_zoomspeed_mydial3_funcring_hdmi4kout_sdi12g_coemulation(
            work_root=None
        )
        r_dl2 = p385.run_phase385_realhw_zoomspeed_mydial3_funcring_hdmi4kout_sdi12g_coemulation(
            work_root="/nonexistent/phase385_stage89_test"
        )
        self.assertEqual(r_dl1["phase385_audit_digest_sha256"], r_dl2["phase385_audit_digest_sha256"])

        r_norm = p385.run_phase385_realhw_zoomspeed_mydial3_funcring_hdmi4kout_sdi12g_coemulation()
        if r_norm["source_mode"] == "LOCAL_DONOR_O_RDONLY":
            self.assertNotEqual(
                r_norm["phase385_audit_digest_sha256"],
                r_f1["phase385_audit_digest_sha256"],
            )
            self.assertNotEqual(
                r_norm["phase385_audit_digest_sha256"],
                r_dl1["phase385_audit_digest_sha256"],
            )

    def test_106_portability_no_hardcoded_usr_bin_python_and_dont_write_bytecode(self) -> None:
        forbidden = "/" + "usr/bin/" + "python"
        for src in (Path(p385.__file__).resolve(), Path(__file__).resolve()):
            txt = src.read_text(encoding="utf-8")
            self.assertNotIn(forbidden, txt)
            self.assertIn("sys.dont_write_bytecode = True", txt)

    def test_107_standalone_cli_self_test_summary_json_help_and_subprocess(self) -> None:
        buf_sum = io.StringIO()
        with contextlib.redirect_stdout(buf_sum):
            rc = p385.main(["--self-test", "--clean-room", "--summary"])
        self.assertEqual(rc, 0)
        self.assertIn("[PASS] Phase 385 Stage 89 (89/89)", buf_sum.getvalue())
        self.assertIn("CLEAN_ROOM_SYNTHETIC", buf_sum.getvalue())

        buf_json = io.StringIO()
        with contextlib.redirect_stdout(buf_json):
            rc2 = p385.main(["--self-test", "--clean-room", "--json"])
        self.assertEqual(rc2, 0)
        parsed = json.loads(buf_json.getvalue())
        self.assertEqual(parsed["milestone"], "89/89")
        self.assertTrue(parsed["all_checks_passed"])

        buf_help = io.StringIO()
        with self.assertRaises(SystemExit) as cm:
            with contextlib.redirect_stdout(buf_help):
                p385.main(["--help"])
        self.assertEqual(cm.exception.code, 0)
        self.assertIn("89/89", buf_help.getvalue())

        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["FX3_FX6_FORCE_CLEAN_ROOM"] = "1"
        proc = subprocess.run(
            [
                sys.executable,
                "-B",
                str(Path(p385.__file__).resolve()),
                "--clean-room",
                "--summary",
            ],
            env=env,
            capture_output=True,
            text=True,
            check=True,
            timeout=60,
        )
        self.assertIn("Phase 385 Stage 89 (89/89)", proc.stdout)

    def test_108_suite_default_config_and_forward_compatible_stage89_keys(self) -> None:
        default_cfg = suite.CoEmulationConfig()
        self.assertTrue(
            default_cfg.include_phase385_realhw_zoomspeed_mydial3_funcring_hdmi4kout_sdi12g_hil
        )
        self.assertTrue(default_cfg.include_stage89)
        self.assertTrue(
            default_cfg.stage89_realhw_zoomspeed_mydial3_funcring_hdmi4kout_sdi12g_hil
        )

        fast_cfg = suite.CoEmulationConfig(**_fast_suite_kwargs())
        rep = suite.run_fx3_vm_coemulation_suite(fast_cfg)
        self.assertTrue(rep["all_checks_passed"])
        s89 = rep["stage89_realhw_zoomspeed_mydial3_funcring_hdmi4kout_sdi12g_hil"]
        self.assertTrue(s89["all_checks_passed"])
        self.assertEqual(s89["phase_number"], 385)
        self.assertEqual(s89["milestone"], "89/89")
        self.assertEqual(s89["raw_firmware_bytes_leaked"], 0)
        self.assertEqual(s89["slot1_writes"], 0)
        self.assertEqual(s89["slot1_data_sector_writes"], 0)
        self.assertEqual(s89["usb_tx_packets"], 0)
        self.assertEqual(s89["rf_tx_packets"], 0)

        stage_keys = [
            f
            for f in suite.CoEmulationConfig.__dataclass_fields__
            if re.match(r"^include_phase\d+_", f)
        ]
        # Forward-compatible assertion: Base 3 stages + optional phase flags >= 89
        self.assertGreaterEqual(len(stage_keys) + 3, 89)

    def test_109_suite_cli_summary_and_skip_flags(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = suite.main([*_FAST_CLI_FLAGS, "--summary"])
        self.assertEqual(rc, 0)
        self.assertIn(
            "realhw_zoomspeed_mydial3_funcring_hdmi4kout_sdi12g_hil=",
            buf.getvalue(),
        )
        self.assertIn("m89=89/89", buf.getvalue())

        for skip_flag in ("--skip-stage89", "--no-include-stage89", "--skip-phase385"):
            buf_skip = io.StringIO()
            with contextlib.redirect_stdout(buf_skip):
                rc_skip = suite.main([*_FAST_CLI_FLAGS, skip_flag, "--json"])
            self.assertEqual(rc_skip, 0)
            rep_skip = json.loads(buf_skip.getvalue())
            self.assertNotIn(
                "stage89_realhw_zoomspeed_mydial3_funcring_hdmi4kout_sdi12g_hil",
                rep_skip,
            )

    def test_110_suite_tamper_detection_fails_on_wrong_milestone(self) -> None:
        tampered = suite.CoEmulationConfig(**_fast_suite_kwargs())
        real = p385.run_phase385_realhw_zoomspeed_mydial3_funcring_hdmi4kout_sdi12g_coemulation(
            force_clean_room=True
        )
        with unittest.mock.patch.object(
            p385,
            "run_phase385_realhw_zoomspeed_mydial3_funcring_hdmi4kout_sdi12g_coemulation",
            return_value={**real, "milestone": "88/88"},
        ):
            rep_bad = suite.run_fx3_vm_coemulation_suite(tampered)
            self.assertFalse(rep_bad["all_checks_passed"])

    def test_111_suite_tamper_detection_fails_on_redline_or_invariant_breach(self) -> None:
        tampered = suite.CoEmulationConfig(**_fast_suite_kwargs())
        real = p385.run_phase385_realhw_zoomspeed_mydial3_funcring_hdmi4kout_sdi12g_coemulation(
            force_clean_room=True
        )
        for bad_key, bad_val in (
            ("slot1_write_authorized", True),
            ("cross_model_flash_authorized", True),
            ("live_attach_authorized", True),
            ("emmc_writes_authorized", True),
            ("hardware_live_attachment_authorized", True),
            ("fx3_custom_key_has_variable_mode", True),
            ("fx3_g149_custom_key_no_variable_reconciled", False),
            ("fx6_has_digital_zoom", True),
            ("fx3_dial_customize_exact_items_count", 6),
            ("fx3_dormant_dial_exposed_events", 1),
            ("fx3_g99_pp_anti_init_erratum_reconciled", False),
            ("fx3_has_builtin_evf", True),
            ("fx3_dormant_evf_exposed_events", 1),
            ("fx3_hdmi_resolution_exposed_count", 5),
            ("fx3_4k_output_has_420_option", True),
            ("fx3_dormant_24p_60p_output_elf_hits", 1),
            ("fx3_sony_elf_typos_count", 2),
            ("raw_firmware_bytes_leaked", 1),
        ):
            with unittest.mock.patch.object(
                p385,
                "run_phase385_realhw_zoomspeed_mydial3_funcring_hdmi4kout_sdi12g_coemulation",
                return_value={**real, bad_key: bad_val},
            ):
                rep_bad = suite.run_fx3_vm_coemulation_suite(tampered)
                self.assertFalse(
                    rep_bad["all_checks_passed"],
                    f"Expected tamper fail for {bad_key}",
                )

    def test_112_run_self_test_wrapper_passes_clean_room_and_donorless(self) -> None:
        r_cr = p385.run_self_test(force_clean_room=True)
        self.assertTrue(r_cr["all_checks_passed"])
        self.assertEqual(r_cr["source_mode"], "CLEAN_ROOM_SYNTHETIC")

        r_dl = p385.run_self_test(work_root=None)
        self.assertTrue(r_dl["all_checks_passed"])
        self.assertEqual(r_dl["source_mode"], "CLEAN_ROOM_SYNTHETIC")


if __name__ == "__main__":
    unittest.main()
